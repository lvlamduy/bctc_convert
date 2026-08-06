from __future__ import annotations

import base64
import json
import os
import stat
import subprocess
import tempfile
import tomllib
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.storage.backup import create_backup, restore_test


class S3SnapshotError(RuntimeError):
    """Raised when a backup invariant or remote verification fails."""


@dataclass(frozen=True)
class S3SnapshotSettings:
    config_path: Path
    bucket: str
    prefix: str
    profile: str
    region: str
    server_side_encryption: str
    retry_mode: str
    max_attempts: int
    workers: int
    require_public_access_block: bool
    require_default_encryption: bool
    production_requires_versioning: bool
    production_requires_full_content_restore: bool
    allow_unversioned_immutable_snapshot: bool
    content_prefix: str
    snapshot_prefix: str
    run_prefix: str
    put_if_none_match: str
    include_sha256_checksum: bool
    delete_operations_enabled: bool
    overwrite_operations_enabled: bool
    source_root: str
    source_registry: str
    generated_output_root: str
    mongodb_dump_registry: str
    historical_reference_registry: str
    include_control_plane_archive: bool
    include_git_bundle: bool
    sample_one_per_asset_class: bool
    restore_all_control_plane_objects: bool
    restore_all_singleton_critical_objects: bool
    catalog_head_verification: bool
    full_content_stream_restore_default: bool
    excluded_reconstructable_paths: tuple[str, ...]
    excluded_reconstructable_reason: str


@dataclass(frozen=True)
class SnapshotAsset:
    logical_path: str
    local_path: Path
    asset_class: str
    size_bytes: int
    sha256: str
    object_key: str

    def manifest_record(self) -> dict[str, Any]:
        return {
            "asset_class": self.asset_class,
            "logical_path": self.logical_path,
            "object_key": self.object_key,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True)
class UploadResult:
    object_key: str
    sha256: str
    size_bytes: int
    disposition: str
    version_id: str | None


@dataclass(frozen=True)
class RestoreResult:
    manifest_download_verified: bool
    catalog_head_verified_count: int
    sampled_object_count: int
    sampled_asset_classes: tuple[str, ...]
    control_plane_restore_verified: bool
    git_bundle_verified: bool
    sample_pdf_opened: bool
    full_content_stream_verified: bool

    @property
    def passed(self) -> bool:
        return all(
            (
                self.manifest_download_verified,
                self.catalog_head_verified_count > 0,
                self.sampled_object_count > 0,
                self.control_plane_restore_verified,
                self.git_bundle_verified,
                self.sample_pdf_opened,
            )
        )


@dataclass(frozen=True)
class SnapshotResult:
    snapshot_id: str
    manifest_path: str
    manifest_key: str
    manifest_sha256: str
    run_record_path: str
    run_record_key: str
    run_record_sha256: str
    logical_file_count: int
    unique_object_count: int
    uploaded_object_count: int
    reused_object_count: int
    logical_bytes: int
    unique_bytes: int
    bucket_versioning_status: str
    off_machine_status: str
    restore_status: str
    production_status: str


@dataclass(frozen=True)
class OffloadResult:
    record_path: str
    record_key: str
    record_sha256: str
    removed_file_count: int
    removed_bytes: int
    asset_classes: tuple[str, ...]


@dataclass(frozen=True)
class HydrationResult:
    restored_file_count: int
    reused_file_count: int
    restored_bytes: int


CommandRunner = Callable[[Sequence[str], Mapping[str, str]], subprocess.CompletedProcess[str]]
ProgressCallback = Callable[[str], None]
MAX_SINGLE_PUT_BYTES = 5 * 1024**3


def _clean_prefix(value: str, *, field: str) -> str:
    cleaned = value.strip("/")
    path = PurePosixPath(cleaned)
    if not cleaned or path.is_absolute() or ".." in path.parts:
        raise S3SnapshotError(f"invalid {field}: {value!r}")
    return cleaned


def load_settings(path: Path) -> S3SnapshotSettings:
    path = path.resolve()
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    if payload.get("format_version") != 1:
        raise S3SnapshotError("unsupported S3 snapshot config format")
    aws = payload["aws"]
    gate = payload["bucket_gate"]
    layout = payload["object_layout"]
    inventory = payload["inventory"]
    restore = payload["restore"]
    excluded = payload["excluded_reconstructable"]
    settings = S3SnapshotSettings(
        config_path=path,
        bucket=str(aws["bucket"]),
        prefix=_clean_prefix(str(aws["prefix"]), field="S3 prefix"),
        profile=str(aws["profile"]),
        region=str(aws["region"]),
        server_side_encryption=str(aws["server_side_encryption"]),
        retry_mode=str(aws["retry_mode"]),
        max_attempts=int(aws["max_attempts"]),
        workers=int(aws["workers"]),
        require_public_access_block=bool(gate["require_public_access_block"]),
        require_default_encryption=bool(gate["require_default_encryption"]),
        production_requires_versioning=bool(gate["production_requires_versioning"]),
        production_requires_full_content_restore=bool(
            gate["production_requires_full_content_restore"]
        ),
        allow_unversioned_immutable_snapshot=bool(gate["allow_unversioned_immutable_snapshot"]),
        content_prefix=_clean_prefix(str(layout["content_prefix"]), field="content prefix"),
        snapshot_prefix=_clean_prefix(str(layout["snapshot_prefix"]), field="snapshot prefix"),
        run_prefix=_clean_prefix(str(layout["run_prefix"]), field="run prefix"),
        put_if_none_match=str(layout["put_if_none_match"]),
        include_sha256_checksum=bool(layout["include_sha256_checksum"]),
        delete_operations_enabled=bool(layout["delete_operations_enabled"]),
        overwrite_operations_enabled=bool(layout["overwrite_operations_enabled"]),
        source_root=str(inventory["source_root"]),
        source_registry=str(inventory["source_registry"]),
        generated_output_root=str(inventory["generated_output_root"]),
        mongodb_dump_registry=str(inventory["mongodb_dump_registry"]),
        historical_reference_registry=str(inventory["historical_reference_registry"]),
        include_control_plane_archive=bool(inventory["include_control_plane_archive"]),
        include_git_bundle=bool(inventory["include_git_bundle"]),
        sample_one_per_asset_class=bool(restore["sample_one_per_asset_class"]),
        restore_all_control_plane_objects=bool(restore["restore_all_control_plane_objects"]),
        restore_all_singleton_critical_objects=bool(
            restore["restore_all_singleton_critical_objects"]
        ),
        catalog_head_verification=bool(restore["catalog_head_verification"]),
        full_content_stream_restore_default=bool(restore["full_content_stream_restore_default"]),
        excluded_reconstructable_paths=tuple(str(item) for item in excluded["paths"]),
        excluded_reconstructable_reason=str(excluded["reason"]),
    )
    if settings.workers < 1 or settings.max_attempts < 1:
        raise S3SnapshotError("workers and max_attempts must be positive")
    if settings.put_if_none_match != "*":
        raise S3SnapshotError("S3 writes must use If-None-Match: *")
    if settings.delete_operations_enabled or settings.overwrite_operations_enabled:
        raise S3SnapshotError("delete and overwrite operations must remain disabled")
    if not settings.include_sha256_checksum:
        raise S3SnapshotError("S3 SHA-256 checksum verification must remain enabled")
    if not all(
        (
            settings.sample_one_per_asset_class,
            settings.restore_all_control_plane_objects,
            settings.restore_all_singleton_critical_objects,
            settings.catalog_head_verification,
        )
    ):
        raise S3SnapshotError("sample/catalog restore safety gates must remain enabled")
    return settings


def _safe_project_file(project_root: Path, relative_path: str) -> Path:
    relative = PurePosixPath(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise S3SnapshotError(f"unsafe project-relative path: {relative_path!r}")
    path = (project_root / Path(*relative.parts)).resolve(strict=True)
    if not path.is_relative_to(project_root):
        raise S3SnapshotError(f"path escapes project root: {relative_path!r}")
    return path


def _safe_project_destination(project_root: Path, relative_path: str) -> Path:
    relative = PurePosixPath(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise S3SnapshotError(f"unsafe project-relative path: {relative_path!r}")
    destination = project_root / Path(*relative.parts)
    resolved_parent = destination.parent.resolve(strict=False)
    if not resolved_parent.is_relative_to(project_root):
        raise S3SnapshotError(f"path escapes project root: {relative_path!r}")
    return destination


def _stable_file_identity(path: Path) -> tuple[int, str]:
    before = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(before.st_mode):
        raise S3SnapshotError(f"backup accepts regular files only: {path}")
    digest = sha256_file(path)
    after = path.lstat()
    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if identity_before != identity_after:
        raise S3SnapshotError(f"file changed while hashing: {path}")
    return before.st_size, digest


def _object_key(settings: S3SnapshotSettings, digest: str) -> str:
    return f"{settings.prefix}/{settings.content_prefix}/{digest[:2]}/{digest}"


def _asset(
    *,
    logical_path: str,
    local_path: Path,
    asset_class: str,
    settings: S3SnapshotSettings,
    expected_size: int | None = None,
    expected_sha256: str | None = None,
) -> SnapshotAsset:
    logical = PurePosixPath(logical_path)
    if logical.is_absolute() or ".." in logical.parts:
        raise S3SnapshotError(f"unsafe logical path: {logical_path!r}")
    size, digest = _stable_file_identity(local_path)
    if expected_size is not None and size != expected_size:
        raise S3SnapshotError(
            f"registered size drift for {logical_path}: {size} != {expected_size}"
        )
    if expected_sha256 is not None and digest != expected_sha256:
        raise S3SnapshotError(
            f"registered SHA-256 drift for {logical_path}: {digest} != {expected_sha256}"
        )
    return SnapshotAsset(
        logical_path=logical.as_posix(),
        local_path=local_path,
        asset_class=asset_class,
        size_bytes=size,
        sha256=digest,
        object_key=_object_key(settings, digest),
    )


def _load_source_registry(path: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        record = json.loads(line)
        relative = str(record["relative_path"])
        if relative in records:
            raise S3SnapshotError(
                f"duplicate source-registry path at line {line_number}: {relative}"
            )
        if record.get("kind") != "PDF" or record.get("state") != "REGISTERED":
            raise S3SnapshotError(f"source registry contains an unaccepted row: {relative}")
        if record.get("hash_verified_stable") is not True:
            raise S3SnapshotError(f"source registry has an unstable row: {relative}")
        records[relative] = record
    if not records:
        raise S3SnapshotError("source registry is empty")
    return records


def _registered_single_file(
    project_root: Path,
    registry_relative_path: str,
    record_key: str,
    asset_class: str,
    settings: S3SnapshotSettings,
) -> SnapshotAsset:
    registry_path = _safe_project_file(project_root, registry_relative_path)
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    record = registry[record_key]
    relative_path = str(record["path"])
    local_path = _safe_project_file(project_root, relative_path)
    return _asset(
        logical_path=relative_path,
        local_path=local_path,
        asset_class=asset_class,
        settings=settings,
        expected_size=int(record["size_bytes"]),
        expected_sha256=str(record["sha256"]),
    )


def collect_inventory(
    project_root: Path,
    settings: S3SnapshotSettings,
    extra_assets: Iterable[tuple[str, Path, str]] = (),
    *,
    progress: ProgressCallback | None = None,
) -> list[SnapshotAsset]:
    project_root = project_root.resolve()
    source_registry_path = _safe_project_file(project_root, settings.source_registry)
    source_records = _load_source_registry(source_registry_path)
    source_root = _safe_project_file(project_root, settings.source_root)
    assets: list[SnapshotAsset] = []
    seen_registered_pdfs: set[str] = set()

    source_files = sorted(path for path in source_root.rglob("*") if path.is_file())
    for index, path in enumerate(source_files, 1):
        relative = path.relative_to(project_root).as_posix()
        if path.suffix.casefold() == ".pdf":
            record = source_records.get(relative)
            if record is None:
                raise S3SnapshotError(f"unregistered PDF in source tree: {relative}")
            seen_registered_pdfs.add(relative)
            item = _asset(
                logical_path=relative,
                local_path=path,
                asset_class="source_pdf",
                settings=settings,
                expected_size=int(record["size_bytes"]),
                expected_sha256=str(record["sha256"]),
            )
        else:
            item = _asset(
                logical_path=relative,
                local_path=path,
                asset_class="source_acquisition_metadata",
                settings=settings,
            )
        assets.append(item)
        if progress and index % 250 == 0:
            progress(f"INVENTORY_SOURCE_HASHED={index}/{len(source_files)}")
    missing = sorted(set(source_records) - seen_registered_pdfs)
    if missing:
        raise S3SnapshotError(
            f"{len(missing)} registered source PDFs are absent; first={missing[0]!r}"
        )

    output_root = _safe_project_file(project_root, settings.generated_output_root)
    for path in sorted(item for item in output_root.rglob("*") if item.is_file()):
        relative = path.relative_to(project_root).as_posix()
        assets.append(
            _asset(
                logical_path=relative,
                local_path=path,
                asset_class="generated_output",
                settings=settings,
            )
        )

    assets.append(
        _registered_single_file(
            project_root,
            settings.mongodb_dump_registry,
            "archive",
            "mongodb_dump",
            settings,
        )
    )
    assets.append(
        _registered_single_file(
            project_root,
            settings.historical_reference_registry,
            "database",
            "historical_weak_reference",
            settings,
        )
    )
    for logical_path, local_path, asset_class in extra_assets:
        assets.append(
            _asset(
                logical_path=logical_path,
                local_path=local_path.resolve(strict=True),
                asset_class=asset_class,
                settings=settings,
            )
        )

    logical_paths = [item.logical_path for item in assets]
    duplicates = sorted(path for path, count in Counter(logical_paths).items() if count > 1)
    if duplicates:
        raise S3SnapshotError(f"duplicate logical path in snapshot: {duplicates[0]!r}")
    return sorted(assets, key=lambda item: item.logical_path)


def _default_command_runner(
    command: Sequence[str], environment: Mapping[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        check=False,
        capture_output=True,
        text=True,
        env=dict(environment),
    )


class AwsCli:
    def __init__(
        self,
        settings: S3SnapshotSettings,
        *,
        runner: CommandRunner = _default_command_runner,
    ) -> None:
        self.settings = settings
        self.runner = runner
        self.expected_bucket_owner: str | None = None

    def _run(self, arguments: Sequence[str]) -> subprocess.CompletedProcess[str]:
        command = [
            "aws",
            *arguments,
            "--profile",
            self.settings.profile,
            "--region",
            self.settings.region,
            "--no-cli-pager",
        ]
        environment = dict(os.environ)
        environment.update(
            {
                "AWS_PAGER": "",
                "AWS_RETRY_MODE": self.settings.retry_mode,
                "AWS_MAX_ATTEMPTS": str(self.settings.max_attempts),
            }
        )
        return self.runner(command, environment)

    def _json(self, arguments: Sequence[str], *, allow_empty: bool = False) -> dict[str, Any]:
        completed = self._run([*arguments, "--output", "json"])
        if completed.returncode != 0:
            raise S3SnapshotError(
                f"AWS command failed ({' '.join(arguments[:2])}): {completed.stderr.strip()}"
            )
        if not completed.stdout.strip():
            if allow_empty:
                return {}
            raise S3SnapshotError(f"AWS command returned no JSON: {' '.join(arguments[:2])}")
        value = json.loads(completed.stdout)
        if not isinstance(value, dict):
            raise S3SnapshotError("AWS command returned a non-object JSON payload")
        return value

    def _owner_arguments(self) -> list[str]:
        if self.expected_bucket_owner is None:
            raise S3SnapshotError("AWS bucket owner has not been established")
        return ["--expected-bucket-owner", self.expected_bucket_owner]

    def preflight(self) -> dict[str, Any]:
        identity = self._json(["sts", "get-caller-identity"])
        account = str(identity["Account"])
        self.expected_bucket_owner = account
        owner = self._owner_arguments()
        bucket = ["--bucket", self.settings.bucket, *owner]
        head = self._json(["s3api", "head-bucket", *bucket], allow_empty=True)
        bucket_region = str(head.get("BucketRegion") or self.settings.region)
        if bucket_region != self.settings.region:
            raise S3SnapshotError(
                f"bucket region drifted: {bucket_region} != {self.settings.region}"
            )
        versioning = self._json(["s3api", "get-bucket-versioning", *bucket], allow_empty=True)
        versioning_status = str(versioning.get("Status") or "UNVERSIONED")
        if (
            versioning_status != "Enabled"
            and not self.settings.allow_unversioned_immutable_snapshot
        ):
            raise S3SnapshotError("bucket versioning is not enabled")
        encryption = self._json(["s3api", "get-bucket-encryption", *bucket])
        encryption_rules = encryption.get("ServerSideEncryptionConfiguration", {}).get("Rules", [])
        algorithms = {
            rule.get("ApplyServerSideEncryptionByDefault", {}).get("SSEAlgorithm")
            for rule in encryption_rules
        }
        if (
            self.settings.require_default_encryption
            and self.settings.server_side_encryption not in algorithms
        ):
            raise S3SnapshotError(
                f"bucket default encryption drifted: {sorted(str(x) for x in algorithms)}"
            )
        public_access = self._json(["s3api", "get-public-access-block", *bucket])
        public_flags = public_access.get("PublicAccessBlockConfiguration", {})
        required_flags = (
            "BlockPublicAcls",
            "IgnorePublicAcls",
            "BlockPublicPolicy",
            "RestrictPublicBuckets",
        )
        if self.settings.require_public_access_block and not all(
            public_flags.get(name) is True for name in required_flags
        ):
            raise S3SnapshotError("bucket public-access block is incomplete")
        version = self._run(["--version"])
        if version.returncode != 0:
            raise S3SnapshotError(f"cannot identify AWS CLI: {version.stderr.strip()}")
        return {
            "authenticated_principal": str(identity["Arn"]),
            "bucket": self.settings.bucket,
            "bucket_region": bucket_region,
            "default_encryption": sorted(str(item) for item in algorithms),
            "public_access_block": {name: public_flags.get(name) for name in required_flags},
            "versioning_status": versioning_status,
            "aws_cli": (version.stdout or version.stderr).strip(),
        }

    def head_object(self, key: str) -> dict[str, Any] | None:
        completed = self._run(
            [
                "s3api",
                "head-object",
                "--bucket",
                self.settings.bucket,
                "--key",
                key,
                "--checksum-mode",
                "ENABLED",
                *self._owner_arguments(),
                "--output",
                "json",
            ]
        )
        if completed.returncode != 0:
            message = completed.stderr
            if "404" in message or "Not Found" in message or "NoSuchKey" in message:
                return None
            raise S3SnapshotError(f"S3 HEAD failed for {key}: {message.strip()}")
        value = json.loads(completed.stdout)
        if not isinstance(value, dict):
            raise S3SnapshotError(f"S3 HEAD returned invalid JSON for {key}")
        return value

    @staticmethod
    def _checksum_base64(digest: str) -> str:
        return base64.b64encode(bytes.fromhex(digest)).decode("ascii")

    def verify_head(
        self, *, key: str, digest: str, size_bytes: int, payload: Mapping[str, Any]
    ) -> None:
        metadata = {str(k).casefold(): str(v) for k, v in payload.get("Metadata", {}).items()}
        expected_checksum = self._checksum_base64(digest)
        if int(payload.get("ContentLength", -1)) != size_bytes:
            raise S3SnapshotError(f"S3 object size mismatch: {key}")
        if metadata.get("sha256") != digest:
            raise S3SnapshotError(f"S3 object metadata SHA-256 mismatch: {key}")
        if payload.get("ChecksumSHA256") != expected_checksum:
            raise S3SnapshotError(f"S3 object checksum mismatch: {key}")
        if payload.get("ServerSideEncryption") != self.settings.server_side_encryption:
            raise S3SnapshotError(f"S3 object encryption mismatch: {key}")

    def put_content(self, path: Path, *, key: str, digest: str) -> UploadResult:
        size_bytes = path.stat().st_size
        if size_bytes > MAX_SINGLE_PUT_BYTES:
            raise S3SnapshotError(f"single PUT object exceeds the 5 GiB safety limit: {key}")
        existing = self.head_object(key)
        if existing is not None:
            self.verify_head(key=key, digest=digest, size_bytes=size_bytes, payload=existing)
            return UploadResult(
                object_key=key,
                sha256=digest,
                size_bytes=size_bytes,
                disposition="REUSED_VERIFIED",
                version_id=existing.get("VersionId"),
            )
        completed = self._run(
            [
                "s3api",
                "put-object",
                "--bucket",
                self.settings.bucket,
                "--key",
                key,
                "--body",
                str(path),
                "--metadata",
                json.dumps({"sha256": digest, "format": "raw-v1"}),
                "--checksum-algorithm",
                "SHA256",
                "--checksum-sha256",
                self._checksum_base64(digest),
                "--server-side-encryption",
                self.settings.server_side_encryption,
                "--if-none-match",
                self.settings.put_if_none_match,
                *self._owner_arguments(),
                "--output",
                "json",
            ]
        )
        if completed.returncode != 0 and not (
            "412" in completed.stderr or "PreconditionFailed" in completed.stderr
        ):
            raise S3SnapshotError(f"S3 PUT failed for {key}: {completed.stderr.strip()}")
        verified = self.head_object(key)
        if verified is None:
            raise S3SnapshotError(f"S3 object absent after PUT: {key}")
        self.verify_head(key=key, digest=digest, size_bytes=size_bytes, payload=verified)
        return UploadResult(
            object_key=key,
            sha256=digest,
            size_bytes=size_bytes,
            disposition="UPLOADED" if completed.returncode == 0 else "RACE_REUSED_VERIFIED",
            version_id=verified.get("VersionId"),
        )

    def download_content(self, *, key: str, destination: Path, digest: str) -> None:
        if destination.exists():
            raise S3SnapshotError(f"restore destination already exists: {destination}")
        completed = self._run(
            [
                "s3api",
                "get-object",
                "--bucket",
                self.settings.bucket,
                "--key",
                key,
                "--checksum-mode",
                "ENABLED",
                *self._owner_arguments(),
                str(destination),
                "--output",
                "json",
            ]
        )
        if completed.returncode != 0:
            destination.unlink(missing_ok=True)
            raise S3SnapshotError(f"S3 GET failed for {key}: {completed.stderr.strip()}")
        if sha256_file(destination) != digest:
            destination.unlink(missing_ok=True)
            raise S3SnapshotError(f"restored object SHA-256 mismatch: {key}")


def _git(
    project_root: Path, arguments: Sequence[str], *, capture: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=project_root,
        check=False,
        capture_output=capture,
        text=True,
    )


def clean_git_identity(project_root: Path) -> dict[str, str]:
    status_result = _git(project_root, ["status", "--porcelain"])
    if status_result.returncode != 0 or status_result.stdout.strip():
        raise S3SnapshotError("S3 snapshot requires a clean Git worktree")
    commit = _git(project_root, ["rev-parse", "HEAD"])
    branch = _git(project_root, ["branch", "--show-current"])
    remote = _git(project_root, ["remote", "get-url", "origin"])
    if any(item.returncode != 0 for item in (commit, branch, remote)):
        raise S3SnapshotError("cannot resolve the Git snapshot identity")
    return {
        "commit": commit.stdout.strip(),
        "branch": branch.stdout.strip(),
        "remote": remote.stdout.strip(),
    }


def create_git_bundle(project_root: Path, destination: Path) -> None:
    if destination.exists():
        raise S3SnapshotError(f"Git bundle destination exists: {destination}")
    completed = _git(project_root, ["bundle", "create", str(destination), "--all"])
    if completed.returncode != 0:
        destination.unlink(missing_ok=True)
        raise S3SnapshotError(f"Git bundle creation failed: {completed.stderr.strip()}")
    verification = _git(project_root, ["bundle", "verify", str(destination)])
    if verification.returncode != 0:
        destination.unlink(missing_ok=True)
        raise S3SnapshotError(f"Git bundle verification failed: {verification.stderr.strip()}")


def _unique_assets(assets: Iterable[SnapshotAsset]) -> dict[str, SnapshotAsset]:
    unique: dict[str, SnapshotAsset] = {}
    for asset in assets:
        existing = unique.get(asset.sha256)
        if existing is not None and existing.size_bytes != asset.size_bytes:
            raise S3SnapshotError(f"same SHA-256 has conflicting sizes: {asset.sha256}")
        unique.setdefault(asset.sha256, asset)
    return unique


def _upload_assets(
    client: AwsCli,
    assets: Iterable[SnapshotAsset],
    *,
    workers: int,
    progress: ProgressCallback | None,
) -> list[UploadResult]:
    unique = _unique_assets(assets)
    results: list[UploadResult] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                client.put_content,
                asset.local_path,
                key=asset.object_key,
                digest=asset.sha256,
            ): asset
            for asset in unique.values()
        }
        for index, future in enumerate(as_completed(futures), 1):
            results.append(future.result())
            if progress and (index % 25 == 0 or index == len(futures)):
                progress(f"S3_OBJECTS_VERIFIED={index}/{len(futures)}")
    return sorted(results, key=lambda item: item.object_key)


def _class_counts(assets: Iterable[SnapshotAsset]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for asset in assets:
        record = result.setdefault(asset.asset_class, {"file_count": 0, "bytes": 0})
        record["file_count"] += 1
        record["bytes"] += asset.size_bytes
    return dict(sorted(result.items()))


def build_manifest(
    *,
    snapshot_id: str,
    settings: S3SnapshotSettings,
    bucket_facts: Mapping[str, Any],
    git_identity: Mapping[str, str],
    assets: Sequence[SnapshotAsset],
    uploads: Sequence[UploadResult],
) -> dict[str, Any]:
    unique_assets = _unique_assets(assets)
    uploaded = {item.sha256: item for item in uploads}
    if set(uploaded) != set(unique_assets):
        raise S3SnapshotError("uploaded-object catalog does not match local inventory")
    return {
        "format_version": 1,
        "policy_id": "S3_CONTENT_ADDRESSED_SNAPSHOT_V1",
        "snapshot_id": snapshot_id,
        "created_at": datetime.now(UTC).isoformat(),
        "source_git": dict(git_identity),
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
            "logical_file_count": len(assets),
            "unique_object_count": len(unique_assets),
            "logical_bytes": sum(item.size_bytes for item in assets),
            "unique_bytes": sum(item.size_bytes for item in unique_assets.values()),
            "by_asset_class": _class_counts(assets),
            "excluded_reconstructable_paths": list(settings.excluded_reconstructable_paths),
            "excluded_reconstructable_reason": settings.excluded_reconstructable_reason,
        },
        "files": [item.manifest_record() for item in assets],
        "objects": [asdict(uploaded[digest]) for digest in sorted(uploaded)],
        "restore_gate": {
            "catalog_head_verification_required": settings.catalog_head_verification,
            "production_requires_versioning": settings.production_requires_versioning,
            "production_requires_full_content_restore": (
                settings.production_requires_full_content_restore
            ),
            "state": "PENDING_INDEPENDENT_DOWNLOAD_TEST",
        },
    }


def _manifest_asset(record: Mapping[str, Any], local_path: Path) -> SnapshotAsset:
    return SnapshotAsset(
        logical_path=str(record["logical_path"]),
        local_path=local_path,
        asset_class=str(record["asset_class"]),
        size_bytes=int(record["size_bytes"]),
        sha256=str(record["sha256"]),
        object_key=str(record["object_key"]),
    )


def _restore_selection(files: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    by_class: dict[str, list[Mapping[str, Any]]] = {}
    for record in sorted(files, key=lambda item: str(item["logical_path"])):
        by_class.setdefault(str(record["asset_class"]), []).append(record)
    selected: list[Mapping[str, Any]] = []
    for asset_class, records in by_class.items():
        if asset_class in {
            "control_plane",
            "git_bundle",
            "mongodb_dump",
            "historical_weak_reference",
        }:
            selected.extend(records)
        else:
            selected.append(
                max(
                    records,
                    key=lambda item: (int(item["size_bytes"]), str(item["logical_path"])),
                )
            )
    deduplicated: dict[str, Mapping[str, Any]] = {}
    for record in selected:
        deduplicated.setdefault(str(record["sha256"]), record)
    return list(deduplicated.values())


def restore_snapshot_sample(
    *,
    project_root: Path,
    client: AwsCli,
    manifest_key: str,
    manifest_sha256: str,
    restore_root: Path,
    workers: int,
    full_content_stream: bool = False,
    progress: ProgressCallback | None = None,
) -> RestoreResult:
    restore_root.mkdir(parents=True, exist_ok=False)
    manifest_path = restore_root / "downloaded-manifest.json"
    client.download_content(key=manifest_key, destination=manifest_path, digest=manifest_sha256)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest["files"]
    objects = manifest["objects"]

    def verify_catalog(record: Mapping[str, Any]) -> None:
        payload = client.head_object(str(record["object_key"]))
        if payload is None:
            raise S3SnapshotError(f"snapshot object is absent: {record['object_key']}")
        client.verify_head(
            key=str(record["object_key"]),
            digest=str(record["sha256"]),
            size_bytes=int(record["size_bytes"]),
            payload=payload,
        )

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(verify_catalog, record) for record in objects]
        for index, future in enumerate(as_completed(futures), 1):
            future.result()
            if progress and (index % 100 == 0 or index == len(futures)):
                progress(f"RESTORE_CATALOG_HEAD_VERIFIED={index}/{len(futures)}")

    selection = _restore_selection(files)
    restored_by_logical: dict[str, Path] = {}
    restored_by_digest: dict[str, Path] = {}
    for index, record in enumerate(selection, 1):
        digest = str(record["sha256"])
        destination = restored_by_digest.get(digest)
        if destination is None:
            destination = restore_root / "objects" / digest[:2] / digest
            destination.parent.mkdir(parents=True, exist_ok=True)
            client.download_content(
                key=str(record["object_key"]), destination=destination, digest=digest
            )
            restored_by_digest[digest] = destination
        restored_by_logical[str(record["logical_path"])] = destination
        if progress:
            progress(f"RESTORE_SAMPLES_VERIFIED={index}/{len(selection)}")

    if full_content_stream:
        remaining = [
            record for record in objects if str(record["sha256"]) not in restored_by_digest
        ]
        stream_path = restore_root / "stream-verification-object"
        for index, record in enumerate(remaining, 1):
            client.download_content(
                key=str(record["object_key"]),
                destination=stream_path,
                digest=str(record["sha256"]),
            )
            if stream_path.stat().st_size != int(record["size_bytes"]):
                raise S3SnapshotError(f"full restore size mismatch: {record['object_key']}")
            stream_path.unlink()
            if progress and (index % 25 == 0 or index == len(remaining)):
                progress(f"RESTORE_FULL_CONTENT_VERIFIED={index}/{len(remaining)}")

    control = {
        logical: path
        for logical, path in restored_by_logical.items()
        if next(item for item in files if str(item["logical_path"]) == logical)["asset_class"]
        == "control_plane"
    }
    control_archive = next(
        (path for logical, path in control.items() if logical.endswith(".tar.gz")), None
    )
    control_manifest = next(
        (path for logical, path in control.items() if logical.endswith(".manifest.json")),
        None,
    )
    control_verified = bool(
        control_archive and control_manifest and restore_test(control_archive, control_manifest)
    )
    bundle_path = next(
        (path for logical, path in restored_by_logical.items() if logical.endswith(".bundle")),
        None,
    )
    bundle_verified = False
    if bundle_path is not None:
        verification = _git(project_root, ["bundle", "verify", str(bundle_path)])
        bundle_verified = verification.returncode == 0

    pdf_path = next(
        (
            restored_by_logical[str(record["logical_path"])]
            for record in selection
            if record["asset_class"] == "source_pdf"
        ),
        None,
    )
    pdf_opened = False
    if pdf_path is not None:
        import fitz

        with fitz.open(pdf_path) as document:
            pdf_opened = document.page_count > 0

    return RestoreResult(
        manifest_download_verified=True,
        catalog_head_verified_count=len(objects),
        sampled_object_count=len(restored_by_digest),
        sampled_asset_classes=tuple(sorted({str(record["asset_class"]) for record in selection})),
        control_plane_restore_verified=control_verified,
        git_bundle_verified=bundle_verified,
        sample_pdf_opened=pdf_opened,
        full_content_stream_verified=full_content_stream,
    )


def _write_payload(path: Path, payload: Mapping[str, Any]) -> str:
    atomic_write_json(path, payload)
    return sha256_file(path)


def _load_local_snapshot_documents(
    manifest_path: Path,
    run_record_path: Path,
    settings: S3SnapshotSettings,
) -> tuple[dict[str, Any], dict[str, Any], str, str]:
    manifest_path = manifest_path.resolve(strict=True)
    run_record_path = run_record_path.resolve(strict=True)
    manifest_sha256 = sha256_file(manifest_path)
    run_record_sha256 = sha256_file(run_record_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_record = json.loads(run_record_path.read_text(encoding="utf-8"))
    if run_record.get("manifest") != {
        "key": (
            f"{manifest['s3']['prefix']}/{settings.snapshot_prefix}/"
            f"{manifest['snapshot_id']}/"
            f"manifest-{manifest_sha256}.json"
        ),
        "sha256": manifest_sha256,
    }:
        raise S3SnapshotError("run record does not bind the supplied snapshot manifest")
    if run_record.get("off_machine_status") != "PASS":
        raise S3SnapshotError("offload requires a passing off-machine restore record")
    if run_record.get("restore_status") != "PASS":
        raise S3SnapshotError("offload requires a passing sampled restore test")
    if run_record.get("snapshot_id") != manifest.get("snapshot_id"):
        raise S3SnapshotError("run record snapshot identity differs from the manifest")
    return manifest, run_record, manifest_sha256, run_record_sha256


def offload_local_assets(
    project_root: Path,
    *,
    config_path: Path,
    manifest_path: Path,
    run_record_path: Path,
    asset_classes: Iterable[str],
    apply: bool,
    progress: ProgressCallback | None = None,
    runner: CommandRunner = _default_command_runner,
) -> OffloadResult | dict[str, Any]:
    """Delete exact local files only after their immutable S3 objects are verified.

    The default is a non-mutating plan. The apply path writes an fsynced journal
    before and during deletion and never removes directories or uses globs.
    """

    project_root = project_root.resolve()
    settings = load_settings(config_path)
    manifest, run_record, manifest_sha256, run_record_sha256 = _load_local_snapshot_documents(
        manifest_path, run_record_path, settings
    )
    selected_classes = tuple(sorted(set(asset_classes)))
    if not selected_classes:
        raise S3SnapshotError("at least one asset class is required for offload")
    allowed_classes = {"source_pdf", "mongodb_dump"}
    if not set(selected_classes).issubset(allowed_classes):
        raise S3SnapshotError(
            f"offload class is outside the approved large-input set: {selected_classes}"
        )
    selected_records = [
        record for record in manifest["files"] if str(record["asset_class"]) in selected_classes
    ]
    if not selected_records:
        raise S3SnapshotError("no snapshot files match the requested offload classes")
    client = AwsCli(settings, runner=runner)
    bucket_facts = client.preflight()
    if bucket_facts["bucket"] != manifest["s3"]["bucket"]:
        raise S3SnapshotError("configured bucket differs from snapshot manifest")

    remote_manifest_key = str(run_record["manifest"]["key"])
    remote_run_record_key = (
        f"{settings.prefix}/{settings.run_prefix}/{manifest['snapshot_id']}/"
        f"run-{run_record_sha256}.json"
    )
    with tempfile.TemporaryDirectory(prefix="bctc-ai-offload-manifest-") as temp_name:
        downloaded_manifest = Path(temp_name) / "manifest.json"
        downloaded_run_record = Path(temp_name) / "run.json"
        client.download_content(
            key=remote_manifest_key,
            destination=downloaded_manifest,
            digest=manifest_sha256,
        )
        if downloaded_manifest.read_bytes() != manifest_path.resolve().read_bytes():
            raise S3SnapshotError("remote manifest bytes differ from the supplied local manifest")
        client.download_content(
            key=remote_run_record_key,
            destination=downloaded_run_record,
            digest=run_record_sha256,
        )
        if downloaded_run_record.read_bytes() != run_record_path.resolve().read_bytes():
            raise S3SnapshotError("remote run-record bytes differ from the supplied local record")

    guards: dict[str, tuple[int, int, int, int]] = {}
    for index, record in enumerate(selected_records, 1):
        logical_path = str(record["logical_path"])
        local_path = _safe_project_file(project_root, logical_path)
        size, digest = _stable_file_identity(local_path)
        if size != int(record["size_bytes"]) or digest != str(record["sha256"]):
            raise S3SnapshotError(f"local offload identity drifted: {logical_path}")
        payload = client.head_object(str(record["object_key"]))
        if payload is None:
            raise S3SnapshotError(f"remote offload object is absent: {logical_path}")
        client.verify_head(
            key=str(record["object_key"]),
            digest=digest,
            size_bytes=size,
            payload=payload,
        )
        local_stat = local_path.lstat()
        guards[logical_path] = (
            local_stat.st_dev,
            local_stat.st_ino,
            local_stat.st_size,
            local_stat.st_mtime_ns,
        )
        if progress and (index % 100 == 0 or index == len(selected_records)):
            progress(f"OFFLOAD_PREFLIGHT_VERIFIED={index}/{len(selected_records)}")

    plan = {
        "format_version": 1,
        "snapshot_id": manifest["snapshot_id"],
        "manifest": {"key": remote_manifest_key, "sha256": manifest_sha256},
        "run_record": {
            "key": remote_run_record_key,
            "sha256": run_record_sha256,
        },
        "asset_classes": list(selected_classes),
        "file_count": len(selected_records),
        "bytes": sum(int(record["size_bytes"]) for record in selected_records),
        "remote_catalog_verified": True,
        "apply": apply,
    }
    if not apply:
        return plan

    record_directory = manifest_path.resolve().parent
    journal_path = record_directory / "local-offload-journal.jsonl"
    if journal_path.exists():
        raise S3SnapshotError(f"offload journal already exists: {journal_path}")
    descriptor = os.open(journal_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    removed_count = 0
    removed_bytes = 0
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as journal:
            journal.write(json.dumps({"event": "OFFLOAD_STARTED", **plan}) + "\n")
            journal.flush()
            os.fsync(journal.fileno())
            for index, record in enumerate(selected_records, 1):
                logical_path = str(record["logical_path"])
                local_path = _safe_project_file(project_root, logical_path)
                current = local_path.lstat()
                current_guard = (
                    current.st_dev,
                    current.st_ino,
                    current.st_size,
                    current.st_mtime_ns,
                )
                if current_guard != guards[logical_path]:
                    raise S3SnapshotError(
                        f"local file changed after offload preflight: {logical_path}"
                    )
                local_path.unlink()
                if local_path.exists():
                    raise S3SnapshotError(f"local offload unlink did not complete: {logical_path}")
                removed_count += 1
                removed_bytes += int(record["size_bytes"])
                journal.write(
                    json.dumps(
                        {
                            "event": "LOCAL_FILE_REMOVED",
                            "logical_path": logical_path,
                            "object_key": record["object_key"],
                            "sha256": record["sha256"],
                            "size_bytes": record["size_bytes"],
                            "removed_at": datetime.now(UTC).isoformat(),
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    + "\n"
                )
                journal.flush()
                os.fsync(journal.fileno())
                if progress and (index % 100 == 0 or index == len(selected_records)):
                    progress(f"OFFLOAD_LOCAL_FILES_REMOVED={index}/{len(selected_records)}")
            journal.write(
                json.dumps(
                    {
                        "event": "OFFLOAD_COMPLETE",
                        "removed_file_count": removed_count,
                        "removed_bytes": removed_bytes,
                        "completed_at": datetime.now(UTC).isoformat(),
                    },
                    sort_keys=True,
                )
                + "\n"
            )
            journal.flush()
            os.fsync(journal.fileno())
    except BaseException:
        if progress:
            progress(
                f"OFFLOAD_INTERRUPTED_REMOVED={removed_count}/{len(selected_records)} "
                f"JOURNAL={journal_path}"
            )
        raise

    offload_record = {
        **plan,
        "completed_at": datetime.now(UTC).isoformat(),
        "removed_file_count": removed_count,
        "removed_bytes": removed_bytes,
        "journal": {
            "name": journal_path.name,
            "sha256": sha256_file(journal_path),
        },
        "restore_command_contract": {
            "overwrite_existing_files": False,
            "selection": "logical_path_or_asset_class",
            "source": "immutable_snapshot_manifest",
        },
        "status": "PASS",
    }
    offload_record_path = record_directory / "local-offload-record.json"
    offload_record_sha256 = _write_payload(offload_record_path, offload_record)
    offload_record_key = (
        f"{settings.prefix}/{settings.run_prefix}/{manifest['snapshot_id']}/"
        f"offload-{offload_record_sha256}.json"
    )
    client.put_content(
        offload_record_path,
        key=offload_record_key,
        digest=offload_record_sha256,
    )
    return OffloadResult(
        record_path=str(offload_record_path),
        record_key=offload_record_key,
        record_sha256=offload_record_sha256,
        removed_file_count=removed_count,
        removed_bytes=removed_bytes,
        asset_classes=selected_classes,
    )


def hydrate_from_snapshot(
    project_root: Path,
    *,
    config_path: Path,
    manifest_key: str,
    manifest_sha256: str,
    logical_paths: Iterable[str] = (),
    asset_classes: Iterable[str] = (),
    progress: ProgressCallback | None = None,
    runner: CommandRunner = _default_command_runner,
) -> HydrationResult:
    """Restore selected files atomically; existing mismatched files are never overwritten."""

    project_root = project_root.resolve()
    settings = load_settings(config_path)
    client = AwsCli(settings, runner=runner)
    client.preflight()
    with tempfile.TemporaryDirectory(prefix="bctc-ai-hydrate-manifest-") as temp_name:
        manifest_path = Path(temp_name) / "manifest.json"
        client.download_content(key=manifest_key, destination=manifest_path, digest=manifest_sha256)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("s3", {}).get("bucket") != settings.bucket:
        raise S3SnapshotError("snapshot manifest belongs to a different S3 bucket")
    if manifest.get("s3", {}).get("prefix") != settings.prefix:
        raise S3SnapshotError("snapshot manifest belongs to a different S3 prefix")
    requested_paths = set(logical_paths)
    requested_classes = set(asset_classes)
    if not requested_paths and not requested_classes:
        raise S3SnapshotError("hydrate requires a logical path or asset class")
    selected = [
        record
        for record in manifest["files"]
        if str(record["logical_path"]) in requested_paths
        or str(record["asset_class"]) in requested_classes
    ]
    found_paths = {str(record["logical_path"]) for record in selected}
    missing_requests = sorted(requested_paths - found_paths)
    if missing_requests:
        raise S3SnapshotError(
            f"requested logical path is absent from snapshot: {missing_requests[0]!r}"
        )
    if not selected:
        raise S3SnapshotError("hydrate selection matched no snapshot files")

    restored_count = 0
    reused_count = 0
    restored_bytes = 0
    for index, record in enumerate(selected, 1):
        logical_path = str(record["logical_path"])
        destination = _safe_project_destination(project_root, logical_path)
        expected_digest = str(record["sha256"])
        expected_size = int(record["size_bytes"])
        if destination.exists():
            size, digest = _stable_file_identity(destination)
            if size != expected_size or digest != expected_digest:
                raise S3SnapshotError(
                    f"hydrate refuses to overwrite a mismatched file: {logical_path}"
                )
            reused_count += 1
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{destination.name}.", dir=destination.parent
            )
            os.close(descriptor)
            temporary = Path(temporary_name)
            temporary.unlink()
            try:
                client.download_content(
                    key=str(record["object_key"]),
                    destination=temporary,
                    digest=expected_digest,
                )
                if temporary.stat().st_size != expected_size:
                    raise S3SnapshotError(f"hydrated size mismatch for {logical_path}")
                with temporary.open("rb") as stream:
                    os.fsync(stream.fileno())
                try:
                    os.link(temporary, destination)
                except FileExistsError:
                    size, digest = _stable_file_identity(destination)
                    if size != expected_size or digest != expected_digest:
                        raise S3SnapshotError(
                            f"concurrent hydrate conflict: {logical_path}"
                        ) from None
                destination.chmod(0o644)
                restored_count += 1
                restored_bytes += expected_size
            finally:
                temporary.unlink(missing_ok=True)
        if progress and (index % 100 == 0 or index == len(selected)):
            progress(f"HYDRATE_FILES_VERIFIED={index}/{len(selected)}")
    return HydrationResult(
        restored_file_count=restored_count,
        reused_file_count=reused_count,
        restored_bytes=restored_bytes,
    )


def create_s3_snapshot(
    project_root: Path,
    *,
    config_path: Path,
    staging_root: Path,
    restore_temp_root: Path | None = None,
    full_content_stream_restore: bool | None = None,
    workers: int | None = None,
    progress: ProgressCallback | None = None,
    runner: CommandRunner = _default_command_runner,
) -> SnapshotResult:
    project_root = project_root.resolve()
    settings = load_settings(config_path)
    selected_workers = int(workers or settings.workers)
    if selected_workers < 1:
        raise S3SnapshotError("workers must be positive")
    git_identity = clean_git_identity(project_root)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    snapshot_id = f"{timestamp}-{git_identity['commit'][:12]}"
    staging_root = staging_root.resolve()
    if staging_root == project_root or staging_root.is_relative_to(project_root):
        raise S3SnapshotError("S3 staging root must be outside the repository")
    run_directory = staging_root / snapshot_id
    run_directory.mkdir(parents=True, exist_ok=False)

    extras: list[tuple[str, Path, str]] = []
    if settings.include_control_plane_archive:
        control = create_backup(project_root, run_directory, off_machine=False)
        if not control.restored_and_verified:
            raise S3SnapshotError("local control-plane restore test failed")
        extras.extend(
            [
                (f"control/{Path(control.archive).name}", Path(control.archive), "control_plane"),
                (
                    f"control/{Path(control.manifest).name}",
                    Path(control.manifest),
                    "control_plane",
                ),
            ]
        )
    if settings.include_git_bundle:
        bundle_path = run_directory / f"bctc-ai-{snapshot_id}.bundle"
        create_git_bundle(project_root, bundle_path)
        extras.append((f"git/{bundle_path.name}", bundle_path, "git_bundle"))

    if progress:
        progress("INVENTORY_HASHING_STARTED")
    assets = collect_inventory(project_root, settings, extras, progress=progress)
    if clean_git_identity(project_root) != git_identity:
        raise S3SnapshotError("Git identity changed during snapshot inventory")
    if progress:
        progress(
            f"INVENTORY_COMPLETE_FILES={len(assets)} UNIQUE_OBJECTS={len(_unique_assets(assets))}"
        )

    client = AwsCli(settings, runner=runner)
    bucket_facts = client.preflight()
    if progress:
        progress(f"S3_PREFLIGHT_PASS_VERSIONING={bucket_facts['versioning_status']}")
    uploads = _upload_assets(client, assets, workers=selected_workers, progress=progress)
    manifest = build_manifest(
        snapshot_id=snapshot_id,
        settings=settings,
        bucket_facts=bucket_facts,
        git_identity=git_identity,
        assets=assets,
        uploads=uploads,
    )
    manifest_path = run_directory / "snapshot-manifest.json"
    manifest_sha256 = _write_payload(manifest_path, manifest)
    manifest_key = (
        f"{settings.prefix}/{settings.snapshot_prefix}/{snapshot_id}/"
        f"manifest-{manifest_sha256}.json"
    )
    client.put_content(manifest_path, key=manifest_key, digest=manifest_sha256)
    if progress:
        progress(f"SNAPSHOT_MANIFEST_PUBLISHED={manifest_key}")

    restore_root_parent = (restore_temp_root or Path(tempfile.gettempdir())).resolve()
    restore_root_parent.mkdir(parents=True, exist_ok=True)
    full_restore = (
        settings.full_content_stream_restore_default
        if full_content_stream_restore is None
        else full_content_stream_restore
    )
    with tempfile.TemporaryDirectory(
        prefix=f"bctc-ai-s3-restore-{snapshot_id}-", dir=restore_root_parent
    ) as restore_name:
        restore_result = restore_snapshot_sample(
            project_root=project_root,
            client=client,
            manifest_key=manifest_key,
            manifest_sha256=manifest_sha256,
            restore_root=Path(restore_name) / "restore",
            workers=selected_workers,
            full_content_stream=full_restore,
            progress=progress,
        )
    restore_status = "PASS" if restore_result.passed else "FAIL"
    versioning_pass = bucket_facts["versioning_status"] == "Enabled"
    full_restore_pass = restore_result.full_content_stream_verified
    if not restore_result.passed:
        production_status = "FAIL_RESTORE_TEST"
    elif settings.production_requires_versioning and not versioning_pass:
        production_status = "FAIL_BUCKET_VERSIONING_DISABLED"
    elif settings.production_requires_full_content_restore and not full_restore_pass:
        production_status = "FAIL_FULL_CONTENT_RESTORE_NOT_RUN"
    else:
        production_status = "PASS"
    run_record = {
        "format_version": 1,
        "snapshot_id": snapshot_id,
        "completed_at": datetime.now(UTC).isoformat(),
        "manifest": {
            "key": manifest_key,
            "sha256": manifest_sha256,
        },
        "upload": {
            "logical_file_count": len(assets),
            "unique_object_count": len(uploads),
            "uploaded_object_count": sum(item.disposition == "UPLOADED" for item in uploads),
            "reused_object_count": sum(item.disposition != "UPLOADED" for item in uploads),
            "logical_bytes": sum(item.size_bytes for item in assets),
            "unique_bytes": sum(item.size_bytes for item in _unique_assets(assets).values()),
        },
        "restore": asdict(restore_result),
        "off_machine_status": "PASS" if restore_result.passed else "FAIL",
        "restore_status": restore_status,
        "production_status": production_status,
    }
    run_record_path = run_directory / "s3-backup-run.json"
    run_record_sha256 = _write_payload(run_record_path, run_record)
    run_record_key = (
        f"{settings.prefix}/{settings.run_prefix}/{snapshot_id}/run-{run_record_sha256}.json"
    )
    client.put_content(run_record_path, key=run_record_key, digest=run_record_sha256)
    if progress:
        progress(f"S3_BACKUP_RUN_PUBLISHED={run_record_key}")
    return SnapshotResult(
        snapshot_id=snapshot_id,
        manifest_path=str(manifest_path),
        manifest_key=manifest_key,
        manifest_sha256=manifest_sha256,
        run_record_path=str(run_record_path),
        run_record_key=run_record_key,
        run_record_sha256=run_record_sha256,
        logical_file_count=len(assets),
        unique_object_count=len(uploads),
        uploaded_object_count=sum(item.disposition == "UPLOADED" for item in uploads),
        reused_object_count=sum(item.disposition != "UPLOADED" for item in uploads),
        logical_bytes=sum(item.size_bytes for item in assets),
        unique_bytes=sum(item.size_bytes for item in _unique_assets(assets).values()),
        bucket_versioning_status=str(bucket_facts["versioning_status"]),
        off_machine_status="PASS" if restore_result.passed else "FAIL",
        restore_status=restore_status,
        production_status=production_status,
    )
