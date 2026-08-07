from __future__ import annotations

import json
import os
import re
import shutil
import stat
import tarfile
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.storage.s3_snapshot import AwsCli


class CodexSessionBackupError(RuntimeError):
    """Raised when a Codex session backup cannot be proven safe and restorable."""


@dataclass(frozen=True)
class SessionFile:
    path: str
    size_bytes: int
    sha256: str
    mode: int
    mtime_ns: int


@dataclass(frozen=True)
class SessionArchive:
    archive_path: Path
    manifest_path: Path
    archive_sha256: str
    manifest_sha256: str
    file_count: int
    total_bytes: int


@dataclass(frozen=True)
class SessionBackupResult:
    backup_id: str
    archive_key: str
    manifest_key: str
    archive_sha256: str
    manifest_sha256: str
    file_count: int
    total_bytes: int
    archive_disposition: str
    manifest_disposition: str
    restore_verified: bool


_SAFE_KEY_COMPONENT = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_relative_path(path: Path, root: Path) -> str:
    relative = PurePosixPath(path.relative_to(root).as_posix())
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise CodexSessionBackupError(f"unsafe session path: {relative.as_posix()!r}")
    return relative.as_posix()


def _copy_stable_file(source: Path, destination: Path, relative: str) -> SessionFile:
    before = source.lstat()
    if source.is_symlink() or not stat.S_ISREG(before.st_mode):
        raise CodexSessionBackupError(f"session backup accepts regular files only: {relative}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as input_stream, destination.open("xb") as output_stream:
        shutil.copyfileobj(input_stream, output_stream, length=1024 * 1024)
        output_stream.flush()
        os.fsync(output_stream.fileno())
    after = source.lstat()
    before_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if before_identity != after_identity:
        raise CodexSessionBackupError(f"session file changed while being copied: {relative}")
    source_digest = sha256_file(source)
    final = source.lstat()
    final_identity = (final.st_dev, final.st_ino, final.st_size, final.st_mtime_ns)
    if before_identity != final_identity:
        raise CodexSessionBackupError(f"session file changed while being hashed: {relative}")
    destination_digest = sha256_file(destination)
    if source_digest != destination_digest:
        raise CodexSessionBackupError(f"staged session hash mismatch: {relative}")
    mode = stat.S_IMODE(before.st_mode)
    os.chmod(destination, mode)
    os.utime(destination, ns=(before.st_atime_ns, before.st_mtime_ns))
    return SessionFile(
        path=relative,
        size_bytes=before.st_size,
        sha256=source_digest,
        mode=mode,
        mtime_ns=before.st_mtime_ns,
    )


def _stage_session_tree(source_root: Path, snapshot_root: Path) -> tuple[SessionFile, ...]:
    source_root = source_root.resolve(strict=True)
    if not source_root.is_dir():
        raise CodexSessionBackupError(f"Codex sessions source is not a directory: {source_root}")
    records: list[SessionFile] = []
    for source in sorted(source_root.rglob("*")):
        relative = _safe_relative_path(source, source_root)
        if source.is_symlink():
            raise CodexSessionBackupError(f"symlinks are forbidden in session backup: {relative}")
        if source.is_dir():
            continue
        if not source.is_file():
            raise CodexSessionBackupError(f"special files are forbidden in session backup: {relative}")
        records.append(_copy_stable_file(source, snapshot_root / relative, relative))
    if not records:
        raise CodexSessionBackupError("Codex sessions source contains no regular files")
    return tuple(records)


def _write_archive(snapshot_root: Path, archive_path: Path) -> None:
    with tarfile.open(archive_path, "w:gz", format=tarfile.PAX_FORMAT) as archive:
        archive.add(snapshot_root, arcname="sessions", recursive=True)
    with archive_path.open("rb") as stream:
        os.fsync(stream.fileno())


def create_session_archive(
    source_root: Path,
    staging_root: Path,
    *,
    host: str,
    created_at: datetime,
) -> SessionArchive:
    staging_root = staging_root.resolve()
    staging_root.mkdir(parents=True, exist_ok=True)
    snapshot_root = staging_root / "session-snapshot"
    if snapshot_root.exists():
        raise CodexSessionBackupError(f"session staging path already exists: {snapshot_root}")
    snapshot_root.mkdir()
    records = _stage_session_tree(source_root, snapshot_root)
    archive_path = staging_root / "codex-sessions.tar.gz"
    if archive_path.exists():
        raise CodexSessionBackupError(f"session archive already exists: {archive_path}")
    _write_archive(snapshot_root, archive_path)
    archive_sha256 = sha256_file(archive_path)
    manifest_path = staging_root / "codex-sessions.manifest.json"
    payload = {
        "format_version": 1,
        "policy": "CODEX_SESSION_DATA_ONLY_IMMUTABLE_S3_V1",
        "created_at": created_at.astimezone(UTC).isoformat(),
        "host": host,
        "source_scope": "~/.codex/sessions/ only",
        "secret_file_exclusions": [
            "~/.codex/auth*",
            "~/.aws/credentials",
            "~/.ssh/",
            "~/.git-credentials",
            ".env",
            "API keys, tokens and private-key files outside the session tree",
        ],
        "archive": {
            "filename": archive_path.name,
            "sha256": archive_sha256,
            "size_bytes": archive_path.stat().st_size,
        },
        "files": [asdict(record) for record in records],
        "summary": {
            "file_count": len(records),
            "total_bytes": sum(record.size_bytes for record in records),
        },
    }
    manifest_sha256 = atomic_write_json(manifest_path, payload)
    return SessionArchive(
        archive_path=archive_path,
        manifest_path=manifest_path,
        archive_sha256=archive_sha256,
        manifest_sha256=manifest_sha256,
        file_count=len(records),
        total_bytes=sum(record.size_bytes for record in records),
    )


def _validated_members(archive: tarfile.TarFile) -> list[tarfile.TarInfo]:
    members = archive.getmembers()
    for member in members:
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise CodexSessionBackupError(f"unsafe archive member: {member.name!r}")
        if path.parts[0] != "sessions":
            raise CodexSessionBackupError(f"archive member is outside sessions/: {member.name!r}")
        if not (member.isdir() or member.isfile()):
            raise CodexSessionBackupError(f"non-regular archive member: {member.name!r}")
    return members


def verify_session_archive(archive_path: Path, manifest_path: Path, restore_root: Path) -> bool:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("format_version") != 1:
        raise CodexSessionBackupError("unsupported Codex session manifest format")
    if payload.get("policy") != "CODEX_SESSION_DATA_ONLY_IMMUTABLE_S3_V1":
        raise CodexSessionBackupError("unexpected Codex session backup policy")
    archive_record = payload.get("archive")
    files = payload.get("files")
    if not isinstance(archive_record, dict) or not isinstance(files, list):
        raise CodexSessionBackupError("Codex session manifest is incomplete")
    if sha256_file(archive_path) != archive_record.get("sha256"):
        raise CodexSessionBackupError("Codex session archive SHA-256 mismatch")
    if archive_path.stat().st_size != int(archive_record.get("size_bytes", -1)):
        raise CodexSessionBackupError("Codex session archive size mismatch")
    restore_root = restore_root.resolve()
    if restore_root.exists():
        raise CodexSessionBackupError(f"session restore destination exists: {restore_root}")
    restore_root.mkdir(parents=True)
    with tarfile.open(archive_path, "r:gz") as archive:
        members = _validated_members(archive)
        archive.extractall(restore_root, members=members)
    restored_sessions = restore_root / "sessions"
    expected_paths: set[str] = set()
    for item in files:
        if not isinstance(item, dict):
            raise CodexSessionBackupError("invalid session-file manifest record")
        relative = PurePosixPath(str(item.get("path", "")))
        if relative.is_absolute() or not relative.parts or ".." in relative.parts:
            raise CodexSessionBackupError("unsafe path in session-file manifest")
        restored = restored_sessions / Path(*relative.parts)
        if not restored.is_file() or restored.is_symlink():
            raise CodexSessionBackupError(f"restored session file is absent: {relative}")
        if restored.stat().st_size != int(item.get("size_bytes", -1)):
            raise CodexSessionBackupError(f"restored session size mismatch: {relative}")
        if sha256_file(restored) != item.get("sha256"):
            raise CodexSessionBackupError(f"restored session hash mismatch: {relative}")
        os.chmod(restored, int(item["mode"]))
        mtime_ns = int(item["mtime_ns"])
        os.utime(restored, ns=(mtime_ns, mtime_ns))
        if restored.stat().st_mtime_ns != mtime_ns:
            raise CodexSessionBackupError(f"restored session timestamp mismatch: {relative}")
        expected_paths.add(relative.as_posix())
    actual_paths = {
        path.relative_to(restored_sessions).as_posix()
        for path in restored_sessions.rglob("*")
        if path.is_file()
    }
    if actual_paths != expected_paths:
        raise CodexSessionBackupError("restored session file inventory mismatch")
    return True


def _safe_key_component(value: str, *, field: str) -> str:
    cleaned = _SAFE_KEY_COMPONENT.sub("-", value.strip()).strip("-.")
    if not cleaned:
        raise CodexSessionBackupError(f"invalid {field}: {value!r}")
    return cleaned


def backup_sessions_to_s3(
    *,
    source_root: Path,
    client: AwsCli,
    prefix: str,
    host: str,
    created_at: datetime | None = None,
) -> SessionBackupResult:
    created_at = created_at or datetime.now(UTC)
    timestamp = created_at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    safe_host = _safe_key_component(host, field="host")
    clean_prefix = PurePosixPath(prefix.strip("/"))
    if clean_prefix.is_absolute() or not clean_prefix.parts or ".." in clean_prefix.parts:
        raise CodexSessionBackupError(f"invalid S3 session prefix: {prefix!r}")
    client.preflight()
    with tempfile.TemporaryDirectory(prefix="bctc-codex-session-backup-") as temporary:
        temporary_root = Path(temporary)
        local = create_session_archive(
            source_root,
            temporary_root / "create",
            host=safe_host,
            created_at=created_at,
        )
        backup_id = f"{timestamp}-{local.archive_sha256[:12]}"
        key_root = f"{clean_prefix.as_posix()}/{safe_host}/{backup_id}"
        archive_key = f"{key_root}/sessions-{local.archive_sha256}.tar.gz"
        manifest_key = f"{key_root}/manifest-{local.manifest_sha256}.json"
        archive_upload = client.put_content(
            local.archive_path,
            key=archive_key,
            digest=local.archive_sha256,
        )
        manifest_upload = client.put_content(
            local.manifest_path,
            key=manifest_key,
            digest=local.manifest_sha256,
        )
        restored_archive = temporary_root / "restore" / local.archive_path.name
        restored_manifest = temporary_root / "restore" / local.manifest_path.name
        restored_archive.parent.mkdir()
        client.download_content(
            key=archive_key,
            destination=restored_archive,
            digest=local.archive_sha256,
        )
        client.download_content(
            key=manifest_key,
            destination=restored_manifest,
            digest=local.manifest_sha256,
        )
        restore_verified = verify_session_archive(
            restored_archive,
            restored_manifest,
            temporary_root / "verified-restore",
        )
        return SessionBackupResult(
            backup_id=backup_id,
            archive_key=archive_key,
            manifest_key=manifest_key,
            archive_sha256=local.archive_sha256,
            manifest_sha256=local.manifest_sha256,
            file_count=local.file_count,
            total_bytes=local.total_bytes,
            archive_disposition=archive_upload.disposition,
            manifest_disposition=manifest_upload.disposition,
            restore_verified=restore_verified,
        )


def result_payload(result: SessionBackupResult) -> dict[str, Any]:
    return asdict(result)
