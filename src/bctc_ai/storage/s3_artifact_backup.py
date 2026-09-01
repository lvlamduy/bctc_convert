from __future__ import annotations

import json
import re
import stat
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.storage.s3_snapshot import (
    AwsCli,
    S3SnapshotSettings,
    UploadResult,
    clean_git_identity,
)


class S3ArtifactBackupError(RuntimeError):
    """Raised when a bounded project-artifact backup cannot be proven restorable."""


@dataclass(frozen=True)
class ArtifactFile:
    logical_path: str
    local_path: Path
    size_bytes: int
    sha256: str
    object_key: str

    def manifest_record(self) -> dict[str, Any]:
        return {
            "asset_class": "generated_output",
            "logical_path": self.logical_path,
            "object_key": self.object_key,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True)
class ArtifactBackupResult:
    artifact_snapshot_id: str
    manifest_key: str
    manifest_sha256: str
    run_record_key: str
    run_record_sha256: str
    file_count: int
    total_bytes: int
    uploaded_object_count: int
    reused_object_count: int
    restore_verified: bool


_SAFE_ID = re.compile(r"[^A-Za-z0-9._-]+")


def _stable_file(path: Path) -> tuple[int, str]:
    before = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(before.st_mode):
        raise S3ArtifactBackupError(f"artifact backup accepts regular files only: {path}")
    digest = sha256_file(path)
    after = path.lstat()
    before_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if before_identity != after_identity:
        raise S3ArtifactBackupError(f"artifact changed while being hashed: {path}")
    return before.st_size, digest


def _resolve_selected_path(project_root: Path, value: str | Path) -> Path:
    raw = Path(value)
    path = (project_root / raw).resolve() if not raw.is_absolute() else raw.resolve()
    output_root = (project_root / "output").resolve()
    if path != output_root and not path.is_relative_to(output_root):
        raise S3ArtifactBackupError(f"bounded artifact backup accepts output/ paths only: {value}")
    if not path.exists():
        raise S3ArtifactBackupError(f"selected artifact path is absent: {value}")
    return path


def collect_artifacts(
    project_root: Path,
    selected_paths: Iterable[str | Path],
    settings: S3SnapshotSettings,
) -> tuple[ArtifactFile, ...]:
    project_root = project_root.resolve()
    candidates: dict[str, Path] = {}
    for selected in selected_paths:
        path = _resolve_selected_path(project_root, selected)
        if path.is_symlink():
            raise S3ArtifactBackupError(f"symlink selections are forbidden: {selected}")
        descendants = (path,) if path.is_file() else tuple(sorted(path.rglob("*")))
        for candidate in descendants:
            if candidate.is_symlink():
                raise S3ArtifactBackupError(f"symlinks are forbidden: {candidate}")
            if candidate.is_dir():
                continue
            if not candidate.is_file():
                raise S3ArtifactBackupError(f"special artifact file is forbidden: {candidate}")
            logical_path = candidate.relative_to(project_root).as_posix()
            candidates.setdefault(logical_path, candidate)
    if not candidates:
        raise S3ArtifactBackupError("bounded artifact selection contains no files")
    records: list[ArtifactFile] = []
    for logical_path, path in sorted(candidates.items()):
        size_bytes, digest = _stable_file(path)
        object_key = f"{settings.prefix}/{settings.content_prefix}/{digest[:2]}/{digest}"
        records.append(
            ArtifactFile(
                logical_path=logical_path,
                local_path=path,
                size_bytes=size_bytes,
                sha256=digest,
                object_key=object_key,
            )
        )
    return tuple(records)


def _load_downloaded_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise S3ArtifactBackupError(f"cannot load {label}") from error
    if not isinstance(payload, dict):
        raise S3ArtifactBackupError(f"{label} must be a JSON object")
    return payload


def _verify_parent(
    client: AwsCli,
    temporary_root: Path,
    *,
    manifest_key: str,
    manifest_sha256: str,
    run_record_key: str,
    run_record_sha256: str,
) -> dict[str, Any]:
    parent_manifest_path = temporary_root / "parent-manifest.json"
    parent_run_path = temporary_root / "parent-run.json"
    client.download_content(
        key=manifest_key,
        destination=parent_manifest_path,
        digest=manifest_sha256,
    )
    client.download_content(
        key=run_record_key,
        destination=parent_run_path,
        digest=run_record_sha256,
    )
    manifest = _load_downloaded_object(parent_manifest_path, label="parent manifest")
    run = _load_downloaded_object(parent_run_path, label="parent run record")
    if manifest.get("format_version") != 1 or manifest.get("snapshot_id") != run.get("snapshot_id"):
        raise S3ArtifactBackupError("parent snapshot identity drifted")
    if run.get("manifest") != {"key": manifest_key, "sha256": manifest_sha256}:
        raise S3ArtifactBackupError("parent run record does not bind the supplied manifest")
    if (
        run.get("production_status") != "PASS"
        or run.get("restore_status") != "PASS"
        or run.get("restore", {}).get("full_content_stream_verified") is not True
    ):
        raise S3ArtifactBackupError("parent full snapshot lacks a passing restore gate")
    if manifest.get("s3", {}).get("bucket") != client.settings.bucket:
        raise S3ArtifactBackupError("parent snapshot belongs to a different bucket")
    if manifest.get("s3", {}).get("prefix") != client.settings.prefix:
        raise S3ArtifactBackupError("parent snapshot belongs to a different prefix")
    return {
        "snapshot_id": manifest["snapshot_id"],
        "manifest": {"key": manifest_key, "sha256": manifest_sha256},
        "run_record": {"key": run_record_key, "sha256": run_record_sha256},
        "production_status": run["production_status"],
        "restore_status": run["restore_status"],
        "full_content_stream_verified": run.get("restore", {}).get("full_content_stream_verified"),
    }


def _upload_files(
    client: AwsCli,
    files: Sequence[ArtifactFile],
    *,
    workers: int,
) -> tuple[UploadResult, ...]:
    unique: dict[str, ArtifactFile] = {}
    for item in files:
        unique.setdefault(item.sha256, item)
    results: list[UploadResult] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                client.put_content,
                item.local_path,
                key=item.object_key,
                digest=item.sha256,
            ): item
            for item in unique.values()
        }
        for future in as_completed(futures):
            results.append(future.result())
    return tuple(sorted(results, key=lambda item: item.object_key))


def _safe_snapshot_id(value: str) -> str:
    cleaned = _SAFE_ID.sub("-", value.strip()).strip("-.")
    if not cleaned:
        raise S3ArtifactBackupError(f"invalid artifact snapshot label: {value!r}")
    return cleaned


def _restore_all(
    client: AwsCli,
    temporary_root: Path,
    *,
    manifest_key: str,
    manifest_sha256: str,
) -> bool:
    temporary_root.mkdir(parents=True, exist_ok=False)
    restored_manifest = temporary_root / "restored-manifest.json"
    client.download_content(
        key=manifest_key,
        destination=restored_manifest,
        digest=manifest_sha256,
    )
    manifest = _load_downloaded_object(restored_manifest, label="artifact manifest")
    records_by_digest: dict[str, dict[str, Any]] = {}
    for record in manifest.get("files", []):
        if not isinstance(record, dict):
            raise S3ArtifactBackupError("artifact manifest file record is invalid")
        digest = str(record["sha256"])
        prior = records_by_digest.setdefault(digest, record)
        if str(prior["object_key"]) != str(record["object_key"]) or int(prior["size_bytes"]) != int(
            record["size_bytes"]
        ):
            raise S3ArtifactBackupError(
                f"artifact digest metadata conflicts: {record['logical_path']}"
            )

    def restore_one(record: dict[str, Any]) -> tuple[str, Path]:
        digest = str(record["sha256"])
        restored = temporary_root / "objects" / digest[:2] / digest
        restored.parent.mkdir(parents=True, exist_ok=True)
        client.download_content(
            key=str(record["object_key"]),
            destination=restored,
            digest=digest,
        )
        if restored.stat().st_size != int(record["size_bytes"]):
            raise S3ArtifactBackupError(
                f"restored artifact size mismatch: {record['logical_path']}"
            )
        return digest, restored

    restored_by_digest: dict[str, Path] = {}
    with ThreadPoolExecutor(max_workers=client.settings.workers) as executor:
        futures = [executor.submit(restore_one, record) for record in records_by_digest.values()]
        for future in as_completed(futures):
            digest, restored = future.result()
            restored_by_digest[digest] = restored
    expected = {str(record["sha256"]) for record in manifest["files"]}
    if set(restored_by_digest) != expected:
        raise S3ArtifactBackupError("restored artifact digest inventory mismatch")
    return True


def backup_artifacts_to_s3(
    project_root: Path,
    *,
    settings: S3SnapshotSettings,
    selected_paths: Iterable[str | Path],
    parent_manifest_key: str,
    parent_manifest_sha256: str,
    parent_run_record_key: str,
    parent_run_record_sha256: str,
    label: str,
    client: AwsCli | None = None,
    created_at: datetime | None = None,
) -> ArtifactBackupResult:
    project_root = project_root.resolve()
    selected_paths = tuple(selected_paths)
    git_identity = clean_git_identity(project_root)
    files = collect_artifacts(project_root, selected_paths, settings)
    client = client or AwsCli(settings)
    bucket_facts = client.preflight()
    created_at = created_at or datetime.now(UTC)
    timestamp = created_at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    with tempfile.TemporaryDirectory(prefix="bctc-artifact-backup-") as temporary:
        temporary_root = Path(temporary)
        parent = _verify_parent(
            client,
            temporary_root,
            manifest_key=parent_manifest_key,
            manifest_sha256=parent_manifest_sha256,
            run_record_key=parent_run_record_key,
            run_record_sha256=parent_run_record_sha256,
        )
        if clean_git_identity(project_root) != git_identity:
            raise S3ArtifactBackupError("Git identity changed during artifact inventory")
        uploads = _upload_files(client, files, workers=settings.workers)
        logical_hash = sha256_file(files[0].local_path)[:12]
        snapshot_id = f"{timestamp}-{_safe_snapshot_id(label)}-{logical_hash}"
        manifest = {
            "format_version": 1,
            "policy_id": "S3_BOUNDED_ARTIFACT_SNAPSHOT_V1",
            "artifact_snapshot_id": snapshot_id,
            "created_at": created_at.astimezone(UTC).isoformat(),
            "source_git": git_identity,
            "parent_full_snapshot": parent,
            "configuration": {
                "path": settings.config_path.name,
                "sha256": sha256_file(settings.config_path),
            },
            "s3": {
                **dict(bucket_facts),
                "prefix": settings.prefix,
                "content_addressing": "SHA256",
                "put_precondition": "If-None-Match: *",
                "server_side_checksum": "SHA256",
                "delete_operations_enabled": False,
                "overwrite_operations_enabled": False,
            },
            "inventory": {
                "logical_file_count": len(files),
                "unique_object_count": len(uploads),
                "logical_bytes": sum(item.size_bytes for item in files),
                "unique_bytes": sum(
                    item.size_bytes for item in {x.sha256: x for x in files}.values()
                ),
                "selection": [str(path) for path in selected_paths],
            },
            "files": [item.manifest_record() for item in files],
            "objects": [asdict(item) for item in uploads],
            "restore_gate": {
                "all_incremental_objects_download_required": True,
                "parent_full_content_restore_required": True,
                "state": "PENDING_INDEPENDENT_DOWNLOAD_TEST",
            },
        }
        manifest_path = temporary_root / "artifact-manifest.json"
        manifest_sha256 = atomic_write_json(manifest_path, manifest)
        key_root = f"{settings.prefix}/artifact-snapshots/{snapshot_id}"
        manifest_key = f"{key_root}/manifest-{manifest_sha256}.json"
        client.put_content(manifest_path, key=manifest_key, digest=manifest_sha256)
        restore_verified = _restore_all(
            client,
            temporary_root / "restore",
            manifest_key=manifest_key,
            manifest_sha256=manifest_sha256,
        )
        run_record = {
            "format_version": 1,
            "policy_id": "S3_BOUNDED_ARTIFACT_SNAPSHOT_V1",
            "artifact_snapshot_id": snapshot_id,
            "completed_at": datetime.now(UTC).isoformat(),
            "manifest": {"key": manifest_key, "sha256": manifest_sha256},
            "parent_full_snapshot": parent,
            "upload": {
                "logical_file_count": len(files),
                "unique_object_count": len(uploads),
                "uploaded_object_count": sum(x.disposition == "UPLOADED" for x in uploads),
                "reused_object_count": sum(x.disposition != "UPLOADED" for x in uploads),
            },
            "all_incremental_objects_restore_verified": restore_verified,
            "status": "PASS" if restore_verified else "FAIL",
        }
        run_path = temporary_root / "artifact-run.json"
        run_sha256 = atomic_write_json(run_path, run_record)
        run_key = f"{settings.prefix}/artifact-runs/{snapshot_id}/run-{run_sha256}.json"
        client.put_content(run_path, key=run_key, digest=run_sha256)
        return ArtifactBackupResult(
            artifact_snapshot_id=snapshot_id,
            manifest_key=manifest_key,
            manifest_sha256=manifest_sha256,
            run_record_key=run_key,
            run_record_sha256=run_sha256,
            file_count=len(files),
            total_bytes=sum(item.size_bytes for item in files),
            uploaded_object_count=sum(x.disposition == "UPLOADED" for x in uploads),
            reused_object_count=sum(x.disposition != "UPLOADED" for x in uploads),
            restore_verified=restore_verified,
        )


def validate_manifest_selection(manifest: Mapping[str, Any]) -> tuple[str, ...]:
    files = manifest.get("files")
    if not isinstance(files, list):
        raise S3ArtifactBackupError("artifact manifest has no file inventory")
    paths: list[str] = []
    for record in files:
        if not isinstance(record, dict):
            raise S3ArtifactBackupError("artifact manifest contains a non-object record")
        path = PurePosixPath(str(record.get("logical_path", "")))
        if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != "output":
            raise S3ArtifactBackupError("artifact manifest contains a path outside output/")
        paths.append(path.as_posix())
    return tuple(paths)
