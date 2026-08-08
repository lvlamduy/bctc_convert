from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import tempfile
import zipfile
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from PIL import Image

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.storage.backup import create_backup, restore_test
from bctc_ai.storage.codex_session_backup import _scan_stream
from bctc_ai.storage.s3_artifact_backup import (
    S3ArtifactBackupError,
    _verify_parent,
    collect_artifacts,
)
from bctc_ai.storage.s3_snapshot import (
    AwsCli,
    ProgressCallback,
    S3SnapshotSettings,
    SnapshotAsset,
    _asset,
    _upload_assets,
    clean_git_identity,
    create_git_bundle,
)


class S3IncrementalCheckpointError(RuntimeError):
    """Raised when an incremental project checkpoint cannot be proven safe."""


@dataclass(frozen=True)
class IncrementalCheckpointRestoreResult:
    manifest_download_verified: bool
    catalog_head_verified_count: int
    unique_object_download_count: int
    logical_file_restore_count: int
    generated_output_restore_count: int
    control_plane_restore_verified: bool
    git_bundle_verified: bool
    sampled_output_paths: tuple[str, ...]
    sample_validations: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return all(
            (
                self.manifest_download_verified,
                self.catalog_head_verified_count > 0,
                self.unique_object_download_count > 0,
                self.logical_file_restore_count > 0,
                self.generated_output_restore_count > 0,
                self.control_plane_restore_verified,
                self.git_bundle_verified,
                bool(self.sampled_output_paths),
                len(self.sample_validations) == len(self.sampled_output_paths),
            )
        )


@dataclass(frozen=True)
class IncrementalCheckpointResult:
    checkpoint_id: str
    manifest_key: str
    manifest_sha256: str
    run_record_key: str
    run_record_sha256: str
    logical_file_count: int
    generated_output_file_count: int
    logical_bytes: int
    uploaded_object_count: int
    reused_object_count: int
    control_archive_sha256: str
    control_manifest_sha256: str
    git_bundle_sha256: str
    restore_verified: bool
    run_record_verified: bool


POLICY_ID = "S3_INCREMENTAL_PROJECT_CHECKPOINT_V1"
CHECKPOINT_PREFIX = "project-checkpoints"
RUN_PREFIX = "project-checkpoint-runs"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_SENSITIVE_DIRECTORY_NAMES = {".aws", ".codex", ".ssh"}
_SENSITIVE_FILE_NAMES = {
    ".env",
    ".git-credentials",
    "auth.json",
    "credentials",
    "credentials.json",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
}
_SENSITIVE_SUFFIXES = {".key", ".p12", ".pem", ".pfx"}
_ALLOWED_ASSET_CLASSES = {"control_plane", "generated_output", "git_bundle"}


def _raise(message: str) -> S3IncrementalCheckpointError:
    return S3IncrementalCheckpointError(message)


def _safe_relative_path(value: str, *, required_root: str | None = None) -> PurePosixPath:
    if not value or "\\" in value:
        raise _raise("checkpoint contains an unsafe logical path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise _raise("checkpoint contains an unsafe logical path")
    if required_root is not None and (not path.parts or path.parts[0] != required_root):
        raise _raise(f"checkpoint path is outside {required_root}/")
    return path


def _reject_sensitive_path(value: str) -> None:
    path = _safe_relative_path(value, required_root="output")
    lowered = [part.casefold() for part in path.parts]
    basename = lowered[-1]
    if (
        any(part in _SENSITIVE_DIRECTORY_NAMES for part in lowered)
        or basename in _SENSITIVE_FILE_NAMES
        or basename.startswith(".env.")
        or Path(basename).suffix in _SENSITIVE_SUFFIXES
    ):
        raise _raise("selected output contains a forbidden credential-path pattern")


def _validate_remote(remote: str) -> None:
    split = urlsplit(remote)
    if split.scheme in {"http", "https"} and (split.username or split.password):
        raise _raise("Git remote contains embedded credentials")


def _scan_outputs(files: Sequence[SnapshotAsset]) -> int:
    findings: Counter[str] = Counter()
    affected_files = 0
    scanned_bytes = 0
    for item in files:
        _reject_sensitive_path(item.logical_path)
        before = item.local_path.lstat()
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise _raise("selected output changed into a non-regular file")
        with item.local_path.open("rb") as stream:
            scan = _scan_stream(stream)
        after = item.local_path.lstat()
        before_identity = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        if before_identity != after_identity:
            raise _raise("selected output changed during credential scan")
        if scan.size_bytes != item.size_bytes or scan.sha256 != item.sha256:
            raise _raise("selected output identity drifted during credential scan")
        scanned_bytes += scan.size_bytes
        if scan.counts:
            affected_files += 1
            findings.update(scan.counts)
    if findings:
        raise _raise(
            "selected output credential scan rejected data: "
            f"affected_files={affected_files}, matches={sum(findings.values())}, "
            f"detectors={','.join(sorted(findings))}"
        )
    return scanned_bytes


def _canonical_selections(
    project_root: Path, selected_paths: Iterable[str | Path]
) -> tuple[str, ...]:
    output_root = (project_root / "output").resolve()
    selections: set[str] = set()
    for value in selected_paths:
        raw = Path(value)
        resolved = (project_root / raw).resolve() if not raw.is_absolute() else raw.resolve()
        if resolved != output_root and not resolved.is_relative_to(output_root):
            raise _raise("incremental checkpoint accepts selected output/ paths only")
        selections.add(resolved.relative_to(project_root).as_posix())
    if not selections:
        raise _raise("incremental checkpoint requires at least one output selection")
    return tuple(sorted(selections))


def _output_assets(
    project_root: Path,
    selected_paths: Sequence[str | Path],
    settings: S3SnapshotSettings,
) -> tuple[SnapshotAsset, ...]:
    try:
        artifacts = collect_artifacts(project_root, selected_paths, settings)
    except S3ArtifactBackupError as error:
        raise _raise(str(error)) from None
    return tuple(
        SnapshotAsset(
            logical_path=item.logical_path,
            local_path=item.local_path,
            asset_class="generated_output",
            size_bytes=item.size_bytes,
            sha256=item.sha256,
            object_key=item.object_key,
        )
        for item in artifacts
    )


def _validate_control_manifest(path: Path) -> None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise _raise("cannot read generated control-plane manifest") from error
    records = payload.get("files")
    if not isinstance(records, list) or not records:
        raise _raise("generated control-plane manifest is empty")
    for record in records:
        if not isinstance(record, dict):
            raise _raise("generated control-plane manifest is malformed")
        logical = _safe_relative_path(str(record.get("path", "")))
        lowered_parts = [part.casefold() for part in logical.parts]
        basename = lowered_parts[-1]
        if set(lowered_parts) & _SENSITIVE_DIRECTORY_NAMES:
            raise _raise("control-plane manifest includes a forbidden credential directory")
        if (
            basename in _SENSITIVE_FILE_NAMES
            or basename.startswith(".env.")
            or Path(basename).suffix in _SENSITIVE_SUFFIXES
        ):
            raise _raise("control-plane manifest includes a forbidden credential file")
        if logical.parts[0] in {"output", "vietstock_bctc"}:
            raise _raise("control-plane manifest crossed its allowlisted boundary")


def _unique_assets(assets: Sequence[SnapshotAsset]) -> dict[str, SnapshotAsset]:
    result: dict[str, SnapshotAsset] = {}
    seen_paths: set[str] = set()
    for item in assets:
        if item.logical_path in seen_paths:
            raise _raise("incremental checkpoint contains a duplicate logical path")
        seen_paths.add(item.logical_path)
        previous = result.get(item.sha256)
        if previous is not None and previous.size_bytes != item.size_bytes:
            raise _raise("same checkpoint digest has conflicting byte sizes")
        result.setdefault(item.sha256, item)
    return result


def _validate_manifest(
    manifest: object,
    *,
    settings: S3SnapshotSettings,
) -> tuple[dict[str, object], tuple[dict[str, object], ...]]:
    if not isinstance(manifest, dict):
        raise _raise("incremental checkpoint manifest is not a JSON object")
    if manifest.get("format_version") != 1 or manifest.get("policy_id") != POLICY_ID:
        raise _raise("incremental checkpoint manifest policy drifted")
    s3 = manifest.get("s3")
    if not isinstance(s3, dict):
        raise _raise("incremental checkpoint manifest lacks S3 identity")
    if s3.get("bucket") != settings.bucket or s3.get("prefix") != settings.prefix:
        raise _raise("incremental checkpoint manifest belongs to another S3 target")
    files = manifest.get("files")
    objects = manifest.get("objects")
    inventory = manifest.get("inventory")
    if not isinstance(files, list) or not files or not isinstance(objects, list):
        raise _raise("incremental checkpoint manifest inventory is incomplete")
    if not isinstance(inventory, dict):
        raise _raise("incremental checkpoint manifest summary is incomplete")
    normalized: list[dict[str, object]] = []
    logical_paths: set[str] = set()
    class_counts: Counter[str] = Counter()
    unique_sizes: dict[str, int] = {}
    for record in files:
        if not isinstance(record, dict):
            raise _raise("incremental checkpoint contains a malformed file record")
        logical_path = str(record.get("logical_path", ""))
        asset_class = str(record.get("asset_class", ""))
        expected_root = {
            "control_plane": "control",
            "generated_output": "output",
            "git_bundle": "git",
        }.get(asset_class)
        if expected_root is None:
            raise _raise("incremental checkpoint contains a forbidden asset class")
        _safe_relative_path(logical_path, required_root=expected_root)
        if logical_path in logical_paths:
            raise _raise("incremental checkpoint repeats a logical path")
        logical_paths.add(logical_path)
        digest = str(record.get("sha256", ""))
        size = record.get("size_bytes")
        if _SHA256.fullmatch(digest) is None or isinstance(size, bool) or not isinstance(size, int):
            raise _raise("incremental checkpoint contains an invalid object identity")
        if size < 0:
            raise _raise("incremental checkpoint contains a negative byte size")
        expected_key = f"{settings.prefix}/{settings.content_prefix}/{digest[:2]}/{digest}"
        if record.get("object_key") != expected_key:
            raise _raise("incremental checkpoint object key is not content-addressed")
        previous_size = unique_sizes.setdefault(digest, size)
        if previous_size != size:
            raise _raise("incremental checkpoint digest has conflicting sizes")
        class_counts[asset_class] += 1
        normalized.append(dict(record))
    if (
        class_counts
        != Counter(
            {
                "control_plane": 2,
                "git_bundle": 1,
                "generated_output": class_counts["generated_output"],
            }
        )
        or class_counts["generated_output"] < 1
    ):
        raise _raise("incremental checkpoint lacks a required asset class")
    object_digests: set[str] = set()
    for record in objects:
        if not isinstance(record, dict):
            raise _raise("incremental checkpoint object catalog is malformed")
        digest = str(record.get("sha256", ""))
        if digest in object_digests or digest not in unique_sizes:
            raise _raise("incremental checkpoint object catalog drifted")
        if record.get("object_key") != (
            f"{settings.prefix}/{settings.content_prefix}/{digest[:2]}/{digest}"
        ):
            raise _raise("incremental checkpoint catalog key drifted")
        if record.get("size_bytes") != unique_sizes[digest]:
            raise _raise("incremental checkpoint catalog size drifted")
        object_digests.add(digest)
    if object_digests != set(unique_sizes):
        raise _raise("incremental checkpoint object catalog is incomplete")
    if (
        inventory.get("logical_file_count") != len(normalized)
        or inventory.get("unique_object_count") != len(unique_sizes)
        or inventory.get("logical_bytes") != sum(int(record["size_bytes"]) for record in normalized)
        or inventory.get("unique_bytes") != sum(unique_sizes.values())
    ):
        raise _raise("incremental checkpoint summary counts drifted")
    return manifest, tuple(normalized)


def _sample_output_paths(records: Sequence[Mapping[str, object]]) -> tuple[str, ...]:
    paths = sorted(
        str(record["logical_path"])
        for record in records
        if record["asset_class"] == "generated_output"
    )
    chosen: list[str] = []
    for suffix in (".xlsx", ".json", ".png"):
        match = next((path for path in paths if path.casefold().endswith(suffix)), None)
        if match is not None and match not in chosen:
            chosen.append(match)
    for path in paths:
        if len(chosen) == 3:
            break
        if path not in chosen:
            chosen.append(path)
    return tuple(chosen)


def _validate_output_samples(logical_root: Path, sampled_paths: Sequence[str]) -> tuple[str, ...]:
    validations: list[str] = []
    for logical_path in sampled_paths:
        relative = _safe_relative_path(logical_path, required_root="output")
        path = logical_root / Path(*relative.parts)
        suffix = path.suffix.casefold()
        try:
            if suffix == ".json":
                json.loads(path.read_text(encoding="utf-8"))
                status = "JSON_PARSE_PASS"
            elif suffix == ".xlsx":
                with zipfile.ZipFile(path) as workbook:
                    if workbook.testzip() is not None:
                        raise _raise("restored XLSX sample contains a corrupt ZIP member")
                    names = set(workbook.namelist())
                    if not {"[Content_Types].xml", "xl/workbook.xml"}.issubset(names):
                        raise _raise("restored XLSX sample lacks required workbook members")
                status = "XLSX_ZIP_STRUCTURE_PASS"
            elif suffix == ".png":
                with Image.open(path) as image:
                    if image.format != "PNG" or image.width < 1 or image.height < 1:
                        raise _raise("restored PNG sample has invalid image metadata")
                    image.verify()
                status = "PNG_DECODE_VERIFY_PASS"
            else:
                with path.open("rb") as stream:
                    stream.read(1)
                status = "BYTE_READ_PASS"
        except S3IncrementalCheckpointError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError, zipfile.BadZipFile) as error:
            raise _raise("restored output sample failed semantic validation") from error
        validations.append(f"{logical_path}::{status}")
    return tuple(validations)


def restore_incremental_checkpoint(
    project_root: Path,
    *,
    client: AwsCli,
    manifest_key: str,
    manifest_sha256: str,
    restore_root: Path,
    workers: int,
) -> IncrementalCheckpointRestoreResult:
    if workers < 1:
        raise _raise("restore workers must be positive")
    restore_root.mkdir(parents=True, exist_ok=False)
    manifest_path = restore_root / "downloaded-manifest.json"
    client.download_content(
        key=manifest_key,
        destination=manifest_path,
        digest=manifest_sha256,
    )
    manifest_head = client.head_object(manifest_key)
    if manifest_head is None:
        raise _raise("published incremental checkpoint manifest is absent")
    client.verify_head(
        key=manifest_key,
        digest=manifest_sha256,
        size_bytes=manifest_path.stat().st_size,
        payload=manifest_head,
    )
    try:
        manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise _raise("cannot load downloaded incremental checkpoint manifest") from error
    _manifest, records = _validate_manifest(manifest_payload, settings=client.settings)
    unique_records: dict[str, Mapping[str, object]] = {}
    for record in records:
        unique_records.setdefault(str(record["sha256"]), record)

    def restore_object(record: Mapping[str, object]) -> tuple[str, Path]:
        digest = str(record["sha256"])
        key = str(record["object_key"])
        size = int(record["size_bytes"])
        head = client.head_object(key)
        if head is None:
            raise _raise("incremental checkpoint object is absent")
        client.verify_head(key=key, digest=digest, size_bytes=size, payload=head)
        destination = restore_root / "objects" / digest[:2] / digest
        destination.parent.mkdir(parents=True, exist_ok=True)
        client.download_content(key=key, destination=destination, digest=digest)
        if destination.stat().st_size != size:
            raise _raise("downloaded checkpoint object size drifted")
        return digest, destination

    restored_objects: dict[str, Path] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(restore_object, record) for record in unique_records.values()]
        for future in as_completed(futures):
            digest, path = future.result()
            restored_objects[digest] = path
    logical_root = restore_root / "logical"
    for record in records:
        logical_path = str(record["logical_path"])
        destination = logical_root / Path(*PurePosixPath(logical_path).parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.link(restored_objects[str(record["sha256"])], destination)
        if (
            destination.stat().st_size != int(record["size_bytes"])
            or sha256_file(destination) != record["sha256"]
        ):
            raise _raise("logical checkpoint restore identity drifted")
    restored_files = [path for path in logical_root.rglob("*") if path.is_file()]
    if len(restored_files) != len(records):
        raise _raise("logical checkpoint restore inventory drifted")
    control_records = [record for record in records if record["asset_class"] == "control_plane"]
    control_archive = next(
        (
            logical_root / Path(*PurePosixPath(str(record["logical_path"])).parts)
            for record in control_records
            if str(record["logical_path"]).endswith(".tar.gz")
        ),
        None,
    )
    control_manifest = next(
        (
            logical_root / Path(*PurePosixPath(str(record["logical_path"])).parts)
            for record in control_records
            if str(record["logical_path"]).endswith(".manifest.json")
        ),
        None,
    )
    control_verified = bool(
        control_archive and control_manifest and restore_test(control_archive, control_manifest)
    )
    bundle_record = next(record for record in records if record["asset_class"] == "git_bundle")
    bundle_path = logical_root / Path(*PurePosixPath(str(bundle_record["logical_path"])).parts)
    bundle = subprocess.run(
        ["git", "bundle", "verify", str(bundle_path)],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
    )
    output_count = sum(record["asset_class"] == "generated_output" for record in records)
    samples = _sample_output_paths(records)
    sample_validations = _validate_output_samples(logical_root, samples)
    return IncrementalCheckpointRestoreResult(
        manifest_download_verified=True,
        catalog_head_verified_count=len(unique_records),
        unique_object_download_count=len(restored_objects),
        logical_file_restore_count=len(restored_files),
        generated_output_restore_count=output_count,
        control_plane_restore_verified=control_verified,
        git_bundle_verified=bundle.returncode == 0,
        sampled_output_paths=samples,
        sample_validations=sample_validations,
    )


def create_incremental_project_checkpoint(
    project_root: Path,
    *,
    settings: S3SnapshotSettings,
    selected_paths: Iterable[str | Path],
    parent_manifest_key: str,
    parent_manifest_sha256: str,
    parent_run_record_key: str,
    parent_run_record_sha256: str,
    client: AwsCli | None = None,
    created_at: datetime | None = None,
    workers: int | None = None,
    progress: ProgressCallback | None = None,
) -> IncrementalCheckpointResult:
    project_root = project_root.resolve()
    selected_paths = tuple(selected_paths)
    selected_workers = int(workers or settings.workers)
    if selected_workers < 1:
        raise _raise("checkpoint workers must be positive")
    git_identity = clean_git_identity(project_root)
    _validate_remote(git_identity["remote"])
    selections = _canonical_selections(project_root, selected_paths)
    output_assets = _output_assets(project_root, selected_paths, settings)
    scanned_output_bytes = _scan_outputs(output_assets)
    if progress:
        progress(f"CHECKPOINT_OUTPUT_SCAN_PASS_FILES={len(output_assets)}")
    created_at = created_at or datetime.now(UTC)
    timestamp = created_at.astimezone(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    checkpoint_id = f"{timestamp}-{git_identity['commit'][:12]}"
    client = client or AwsCli(settings)
    with tempfile.TemporaryDirectory(prefix="bctc-incremental-project-checkpoint-") as temporary:
        temporary_root = Path(temporary)
        control = create_backup(project_root, temporary_root / "control", off_machine=False)
        if not control.restored_and_verified:
            raise _raise("local control-plane restore test failed")
        control_archive_path = Path(control.archive)
        control_manifest_path = Path(control.manifest)
        _validate_control_manifest(control_manifest_path)
        bundle_path = temporary_root / "git" / f"bctc-ai-{checkpoint_id}.bundle"
        bundle_path.parent.mkdir()
        create_git_bundle(project_root, bundle_path)
        if progress:
            progress("CHECKPOINT_LOCAL_CONTROL_AND_GIT_VERIFY=PASS")
        assets = tuple(
            sorted(
                (
                    *output_assets,
                    _asset(
                        logical_path=f"control/{control_archive_path.name}",
                        local_path=control_archive_path,
                        asset_class="control_plane",
                        settings=settings,
                    ),
                    _asset(
                        logical_path=f"control/{control_manifest_path.name}",
                        local_path=control_manifest_path,
                        asset_class="control_plane",
                        settings=settings,
                    ),
                    _asset(
                        logical_path=f"git/{bundle_path.name}",
                        local_path=bundle_path,
                        asset_class="git_bundle",
                        settings=settings,
                    ),
                ),
                key=lambda item: item.logical_path,
            )
        )
        unique_assets = _unique_assets(assets)
        if clean_git_identity(project_root) != git_identity:
            raise _raise("Git identity changed during checkpoint inventory")
        bucket_facts = client.preflight()
        try:
            parent = _verify_parent(
                client,
                temporary_root,
                manifest_key=parent_manifest_key,
                manifest_sha256=parent_manifest_sha256,
                run_record_key=parent_run_record_key,
                run_record_sha256=parent_run_record_sha256,
            )
        except S3ArtifactBackupError as error:
            raise _raise(str(error)) from None
        if progress:
            progress(f"CHECKPOINT_PARENT_VERIFY=PASS:{parent['snapshot_id']}")
        if clean_git_identity(project_root) != git_identity:
            raise _raise("Git identity changed before checkpoint upload")
        uploads = tuple(
            _upload_assets(
                client,
                assets,
                workers=selected_workers,
                progress=None,
            )
        )
        if progress:
            progress(f"CHECKPOINT_CONTENT_OBJECTS_VERIFIED={len(uploads)}")
        manifest = {
            "format_version": 1,
            "policy_id": POLICY_ID,
            "checkpoint_id": checkpoint_id,
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
            "scope": {
                "selected_output_paths": list(selections),
                "included_asset_classes": sorted(_ALLOWED_ASSET_CLASSES),
                "excluded": [
                    "source_pdf_corpus",
                    "codex_sessions",
                    "authentication_and_credentials",
                    "virtual_environments",
                    "model_weights_and_caches",
                    "mongodb_runtime_data",
                ],
                "selected_output_credential_scan": {
                    "policy": "FAIL_CLOSED_KNOWN_CREDENTIAL_FORMATS_V2",
                    "status": "PASS",
                    "scanned_file_count": len(output_assets),
                    "scanned_bytes": scanned_output_bytes,
                },
            },
            "inventory": {
                "logical_file_count": len(assets),
                "generated_output_file_count": len(output_assets),
                "unique_object_count": len(unique_assets),
                "logical_bytes": sum(item.size_bytes for item in assets),
                "unique_bytes": sum(item.size_bytes for item in unique_assets.values()),
            },
            "files": [item.manifest_record() for item in assets],
            "objects": [asdict(item) for item in uploads],
            "restore_gate": {
                "all_incremental_objects_download_required": True,
                "all_logical_paths_restore_required": True,
                "control_plane_restore_test_required": True,
                "git_bundle_verify_required": True,
                "parent_full_content_restore_required": True,
                "state": "PENDING_INDEPENDENT_DOWNLOAD_TEST",
            },
            "publication_order": [
                "content_objects",
                "manifest",
                "independent_full_restore",
                "passing_run_record",
            ],
        }
        manifest_path = temporary_root / "incremental-project-checkpoint-manifest.json"
        manifest_sha256 = atomic_write_json(manifest_path, manifest)
        manifest_key = (
            f"{settings.prefix}/{CHECKPOINT_PREFIX}/{checkpoint_id}/manifest-{manifest_sha256}.json"
        )
        client.put_content(manifest_path, key=manifest_key, digest=manifest_sha256)
        if progress:
            progress(f"CHECKPOINT_MANIFEST_PUBLISHED={manifest_key}")
        restore_result = restore_incremental_checkpoint(
            project_root,
            client=client,
            manifest_key=manifest_key,
            manifest_sha256=manifest_sha256,
            restore_root=temporary_root / "restore",
            workers=selected_workers,
        )
        if not restore_result.passed:
            raise _raise("incremental checkpoint restore gate failed")
        if progress:
            progress(
                "CHECKPOINT_FULL_INCREMENTAL_RESTORE=PASS:"
                f"{restore_result.logical_file_restore_count}"
            )
        run_record = {
            "format_version": 1,
            "policy_id": POLICY_ID,
            "checkpoint_id": checkpoint_id,
            "completed_at": datetime.now(UTC).isoformat(),
            "source_git": git_identity,
            "manifest": {"key": manifest_key, "sha256": manifest_sha256},
            "parent_full_snapshot": parent,
            "upload": {
                "logical_file_count": len(assets),
                "unique_object_count": len(uploads),
                "uploaded_object_count": sum(item.disposition == "UPLOADED" for item in uploads),
                "reused_object_count": sum(item.disposition != "UPLOADED" for item in uploads),
                "logical_bytes": sum(item.size_bytes for item in assets),
            },
            "restore": asdict(restore_result),
            "status": "PASS",
        }
        run_path = temporary_root / "incremental-project-checkpoint-run.json"
        run_sha256 = atomic_write_json(run_path, run_record)
        run_key = f"{settings.prefix}/{RUN_PREFIX}/{checkpoint_id}/run-{run_sha256}.json"
        client.put_content(run_path, key=run_key, digest=run_sha256)
        run_head = client.head_object(run_key)
        if run_head is None:
            raise _raise("published incremental checkpoint run record is absent")
        client.verify_head(
            key=run_key,
            digest=run_sha256,
            size_bytes=run_path.stat().st_size,
            payload=run_head,
        )
        downloaded_run = temporary_root / "verified-run-record.json"
        client.download_content(
            key=run_key,
            destination=downloaded_run,
            digest=run_sha256,
        )
        if downloaded_run.read_bytes() != run_path.read_bytes():
            raise _raise("downloaded incremental checkpoint run record bytes drifted")
        if progress:
            progress(f"CHECKPOINT_RUN_RECORD_VERIFIED={run_key}")
        return IncrementalCheckpointResult(
            checkpoint_id=checkpoint_id,
            manifest_key=manifest_key,
            manifest_sha256=manifest_sha256,
            run_record_key=run_key,
            run_record_sha256=run_sha256,
            logical_file_count=len(assets),
            generated_output_file_count=len(output_assets),
            logical_bytes=sum(item.size_bytes for item in assets),
            uploaded_object_count=sum(item.disposition == "UPLOADED" for item in uploads),
            reused_object_count=sum(item.disposition != "UPLOADED" for item in uploads),
            control_archive_sha256=control.archive_sha256,
            control_manifest_sha256=sha256_file(control_manifest_path),
            git_bundle_sha256=sha256_file(bundle_path),
            restore_verified=True,
            run_record_verified=True,
        )
