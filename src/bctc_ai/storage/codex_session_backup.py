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
from bctc_ai.storage.credential_scan import (
    SECRET_DETECTOR_NAMES as _SECRET_DETECTOR_NAMES,
)
from bctc_ai.storage.credential_scan import (
    SECRET_DETECTORS as _SECRET_DETECTORS,
)
from bctc_ai.storage.credential_scan import (
    SECRET_SCAN_BLOCK_BYTES as _SECRET_SCAN_BLOCK_BYTES,
)
from bctc_ai.storage.credential_scan import (
    SECRET_SCAN_POLICY as _SECRET_SCAN_POLICY,
)
from bctc_ai.storage.credential_scan import (
    scan_stream as _scan_stream,
)
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


@dataclass(frozen=True)
class _SecretFinding:
    detector: str
    item_id: int
    match_count: int


_MANIFEST_FORMAT_VERSION = 2
_BACKUP_POLICY_V1 = "CODEX_SESSION_DATA_ONLY_IMMUTABLE_S3_V1"
_BACKUP_POLICY_V2 = "CODEX_SESSION_DATA_ONLY_IMMUTABLE_S3_V2"
_SAFE_KEY_COMPONENT = re.compile(r"[^A-Za-z0-9._-]+")
_SHA256_HEX = re.compile(r"[0-9a-f]{64}")


def _finding_records(counts: dict[str, int], *, item_id: int) -> list[_SecretFinding]:
    return [
        _SecretFinding(detector=name, item_id=item_id, match_count=count)
        for name, count in sorted(counts.items())
        if count
    ]


def _raise_for_secret_findings(findings: list[_SecretFinding]) -> None:
    if not findings:
        return
    affected_items = len({finding.item_id for finding in findings})
    match_count = sum(finding.match_count for finding in findings)
    detectors = ",".join(sorted({finding.detector for finding in findings}))
    raise CodexSessionBackupError(
        "session secret scan rejected data: "
        f"affected_items={affected_items}, matches={match_count}, detectors={detectors}"
    )


def _scan_payload(payload: bytes) -> dict[str, int]:
    return {
        name: len(pattern.findall(payload))
        for name, pattern in _SECRET_DETECTORS
        if pattern.search(payload)
    }


def _scan_text(value: str) -> dict[str, int]:
    try:
        return _scan_payload(value.encode("utf-8"))
    except UnicodeEncodeError:
        raise CodexSessionBackupError(
            "session text is not valid UTF-8 during secret scan"
        ) from None


def _reject_secret_text(value: str) -> None:
    _raise_for_secret_findings(_finding_records(_scan_text(value), item_id=0))


def _safe_relative_path(path: Path, root: Path) -> str:
    relative = PurePosixPath(path.relative_to(root).as_posix())
    value = relative.as_posix()
    if relative.is_absolute() or not relative.parts or ".." in relative.parts or "\\" in value:
        raise CodexSessionBackupError("unsafe session path")
    return value


def _validated_relative(value: Any) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise CodexSessionBackupError("unsafe session path in manifest")
    relative = PurePosixPath(value)
    if (
        relative.is_absolute()
        or not relative.parts
        or ".." in relative.parts
        or relative.as_posix() != value
    ):
        raise CodexSessionBackupError("unsafe session path in manifest")
    return relative


def _copy_stable_file(source: Path, destination: Path, relative: str) -> SessionFile:
    before = source.lstat()
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise CodexSessionBackupError("session backup accepts regular files only")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as input_stream, destination.open("xb") as output_stream:
        shutil.copyfileobj(input_stream, output_stream, length=1024 * 1024)
        output_stream.flush()
        os.fsync(output_stream.fileno())
    after = source.lstat()
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
        raise CodexSessionBackupError("session file changed while being copied")
    source_digest = sha256_file(source)
    final = source.lstat()
    final_identity = (
        final.st_dev,
        final.st_ino,
        final.st_size,
        final.st_mtime_ns,
        final.st_ctime_ns,
    )
    if before_identity != final_identity:
        raise CodexSessionBackupError("session file changed while being hashed")
    if source_digest != sha256_file(destination):
        raise CodexSessionBackupError("staged session hash mismatch")
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
        raise CodexSessionBackupError("Codex sessions source is not a directory")
    records: list[SessionFile] = []
    for source in sorted(source_root.rglob("*")):
        relative = _safe_relative_path(source, source_root)
        _reject_secret_text(relative)
        source_stat = source.lstat()
        if stat.S_ISLNK(source_stat.st_mode):
            raise CodexSessionBackupError("symlinks are forbidden in session backup")
        if stat.S_ISDIR(source_stat.st_mode):
            continue
        if not stat.S_ISREG(source_stat.st_mode):
            raise CodexSessionBackupError("special files are forbidden in session backup")
        records.append(_copy_stable_file(source, snapshot_root / relative, relative))
    if not records:
        raise CodexSessionBackupError("Codex sessions source contains no regular files")
    return tuple(records)


def _resolved_staged_file(snapshot_root: Path, relative: str) -> Path:
    resolved_root = snapshot_root.resolve(strict=True)
    staged = snapshot_root / Path(*PurePosixPath(relative).parts)
    staged_mode = staged.lstat().st_mode
    resolved = staged.resolve(strict=True)
    if (
        stat.S_ISLNK(staged_mode)
        or not stat.S_ISREG(staged_mode)
        or not resolved.is_relative_to(resolved_root)
    ):
        raise CodexSessionBackupError("unsafe staged session file")
    return resolved


def _scan_staged_session_secrets(
    snapshot_root: Path,
    records: tuple[SessionFile, ...],
) -> int:
    findings: list[_SecretFinding] = []
    scanned_bytes = 0
    for item_id, record in enumerate(records):
        findings.extend(_finding_records(_scan_text(record.path), item_id=item_id))
        path = _resolved_staged_file(snapshot_root, record.path)
        before = path.lstat()
        with path.open("rb") as stream:
            scanned = _scan_stream(stream)
        after = path.lstat()
        identity_before = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        identity_after = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        if identity_before != identity_after:
            raise CodexSessionBackupError("staged session file changed during secret scan")
        if scanned.size_bytes != record.size_bytes or scanned.sha256 != record.sha256:
            raise CodexSessionBackupError("staged session identity drifted during secret scan")
        scanned_bytes += scanned.size_bytes
        findings.extend(_finding_records(scanned.counts, item_id=item_id))
    _raise_for_secret_findings(findings)
    return scanned_bytes


def _expected_archive_inventory(
    records: tuple[SessionFile, ...],
) -> tuple[set[str], dict[str, SessionFile]]:
    directories = {"sessions"}
    files: dict[str, SessionFile] = {}
    for record in records:
        relative = PurePosixPath(record.path)
        for depth in range(1, len(relative.parts)):
            directories.add(PurePosixPath("sessions", *relative.parts[:depth]).as_posix())
        files[PurePosixPath("sessions", *relative.parts).as_posix()] = record
    return directories, files


def _write_archive(
    snapshot_root: Path,
    archive_path: Path,
    records: tuple[SessionFile, ...],
) -> None:
    directories, _files = _expected_archive_inventory(records)
    with tarfile.open(archive_path, "w:gz", format=tarfile.PAX_FORMAT) as archive:
        archive.add(snapshot_root, arcname="sessions", recursive=False)
        for member_name in sorted(
            directories - {"sessions"},
            key=lambda value: (len(PurePosixPath(value).parts), value),
        ):
            relative_parts = PurePosixPath(member_name).parts[1:]
            directory = snapshot_root / Path(*relative_parts)
            directory_mode = directory.lstat().st_mode
            resolved_directory = directory.resolve(strict=True)
            if (
                stat.S_ISLNK(directory_mode)
                or not stat.S_ISDIR(directory_mode)
                or not resolved_directory.is_relative_to(snapshot_root.resolve(strict=True))
            ):
                raise CodexSessionBackupError("unsafe staged session directory")
            archive.add(directory, arcname=member_name, recursive=False)
        for record in records:
            staged = _resolved_staged_file(snapshot_root, record.path)
            before = staged.lstat()
            if before.st_size != record.size_bytes or sha256_file(staged) != record.sha256:
                raise CodexSessionBackupError("staged session identity drifted before archiving")
            after = staged.lstat()
            if (
                before.st_dev,
                before.st_ino,
                before.st_size,
                before.st_mtime_ns,
                before.st_ctime_ns,
            ) != (
                after.st_dev,
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
                after.st_ctime_ns,
            ):
                raise CodexSessionBackupError("staged session file changed before archiving")
            member_name = PurePosixPath("sessions", *PurePosixPath(record.path).parts).as_posix()
            archive.add(staged, arcname=member_name, recursive=False)
    with archive_path.open("rb") as stream:
        os.fsync(stream.fileno())


def _require_manifest_integer(value: Any, *, field: str, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CodexSessionBackupError(f"invalid Codex session manifest integer: {field}")
    if minimum is not None and value < minimum:
        raise CodexSessionBackupError(f"invalid Codex session manifest integer: {field}")
    return value


def _require_sha256(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or _SHA256_HEX.fullmatch(value) is None:
        raise CodexSessionBackupError(f"invalid Codex session manifest SHA-256: {field}")
    return value


def _manifest_records(files: list[Any]) -> tuple[SessionFile, ...]:
    if not files:
        raise CodexSessionBackupError("Codex session manifest file inventory is empty")
    records: list[SessionFile] = []
    seen_paths: set[str] = set()
    findings: list[_SecretFinding] = []
    for item_id, item in enumerate(files):
        if not isinstance(item, dict):
            raise CodexSessionBackupError("invalid session-file manifest record")
        relative = _validated_relative(item.get("path"))
        relative_text = relative.as_posix()
        if relative_text in seen_paths:
            raise CodexSessionBackupError("duplicate session-file manifest record")
        seen_paths.add(relative_text)
        findings.extend(_finding_records(_scan_text(relative_text), item_id=item_id))
        mode = _require_manifest_integer(item.get("mode"), field="files.mode", minimum=0)
        if mode > 0o7777:
            raise CodexSessionBackupError("invalid Codex session manifest mode")
        records.append(
            SessionFile(
                path=relative_text,
                size_bytes=_require_manifest_integer(
                    item.get("size_bytes"), field="files.size_bytes", minimum=0
                ),
                sha256=_require_sha256(item.get("sha256"), field="files.sha256"),
                mode=mode,
                mtime_ns=_require_manifest_integer(item.get("mtime_ns"), field="files.mtime_ns"),
            )
        )
    for relative_text in seen_paths:
        parents = PurePosixPath(relative_text).parents
        if any(
            parent.as_posix() in seen_paths for parent in parents if parent != PurePosixPath(".")
        ):
            raise CodexSessionBackupError("conflicting session-file manifest records")
    _raise_for_secret_findings(findings)
    return tuple(records)


def _validate_manifest_summary(payload: dict[str, Any], records: tuple[SessionFile, ...]) -> None:
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise CodexSessionBackupError("Codex session manifest summary is incomplete")
    file_count = len(records)
    total_bytes = sum(record.size_bytes for record in records)
    if (
        _require_manifest_integer(summary.get("file_count"), field="summary.file_count", minimum=0)
        != file_count
        or _require_manifest_integer(
            summary.get("total_bytes"), field="summary.total_bytes", minimum=0
        )
        != total_bytes
    ):
        raise CodexSessionBackupError("Codex session manifest summary counts drifted")


def _validate_manifest_secret_scan(
    payload: dict[str, Any], records: tuple[SessionFile, ...]
) -> None:
    secret_scan = payload.get("secret_scan")
    if not isinstance(secret_scan, dict):
        raise CodexSessionBackupError("Codex session V2 manifest lacks a passing secret scan")
    if (
        secret_scan.get("policy") != _SECRET_SCAN_POLICY
        or secret_scan.get("status") != "PASS"
        or secret_scan.get("detectors") != list(_SECRET_DETECTOR_NAMES)
        or _require_manifest_integer(
            secret_scan.get("scanned_file_count"),
            field="secret_scan.scanned_file_count",
            minimum=0,
        )
        != len(records)
        or _require_manifest_integer(
            secret_scan.get("scanned_bytes"),
            field="secret_scan.scanned_bytes",
            minimum=0,
        )
        != sum(record.size_bytes for record in records)
    ):
        raise CodexSessionBackupError("Codex session V2 manifest secret scan drifted")


def _validated_manifest(
    payload: Any,
) -> tuple[int, dict[str, Any], tuple[SessionFile, ...]]:
    if not isinstance(payload, dict):
        raise CodexSessionBackupError("Codex session manifest is incomplete")
    version = _require_manifest_integer(payload.get("format_version"), field="format_version")
    policy = payload.get("policy")
    if version == 1:
        if policy != _BACKUP_POLICY_V1:
            raise CodexSessionBackupError("legacy Codex session manifest is quarantined")
    elif version == _MANIFEST_FORMAT_VERSION:
        if policy != _BACKUP_POLICY_V2:
            raise CodexSessionBackupError("unexpected Codex session V2 backup policy")
    else:
        raise CodexSessionBackupError("unsupported Codex session manifest format")
    archive_record = payload.get("archive")
    files = payload.get("files")
    if not isinstance(archive_record, dict) or not isinstance(files, list):
        raise CodexSessionBackupError("Codex session manifest is incomplete")
    records = _manifest_records(files)
    _validate_manifest_summary(payload, records)
    if version == _MANIFEST_FORMAT_VERSION:
        _validate_manifest_secret_scan(payload, records)
    return version, archive_record, records


def _canonical_archive_member_name(name: str, *, is_directory: bool) -> str:
    if not name or "\\" in name:
        raise CodexSessionBackupError("unsafe archive member")
    path = PurePosixPath(name)
    canonical = path.as_posix()
    comparable = name[:-1] if is_directory and name.endswith("/") else name
    if (
        path.is_absolute()
        or not path.parts
        or ".." in path.parts
        or path.parts[0] != "sessions"
        or comparable != canonical
    ):
        raise CodexSessionBackupError("unsafe archive member")
    return canonical


def _validated_members(
    archive: tarfile.TarFile,
    records: tuple[SessionFile, ...],
) -> list[tarfile.TarInfo]:
    expected_directories, expected_files = _expected_archive_inventory(records)
    expected_names = expected_directories | set(expected_files)
    members = archive.getmembers()
    seen_names: set[str] = set()
    findings: list[_SecretFinding] = []
    invalid_inventory = not members
    for item_id, member in enumerate(members):
        findings.extend(_finding_records(_scan_text(member.name), item_id=item_id))
        try:
            canonical = _canonical_archive_member_name(member.name, is_directory=member.isdir())
        except CodexSessionBackupError:
            invalid_inventory = True
            canonical = ""
        if canonical in seen_names:
            invalid_inventory = True
        seen_names.add(canonical)
        if member.isdir():
            if canonical not in expected_directories or member.size != 0:
                invalid_inventory = True
            continue
        if not member.isfile():
            invalid_inventory = True
            continue
        stream = archive.extractfile(member)
        if stream is None:
            invalid_inventory = True
            continue
        with stream:
            scanned = _scan_stream(stream)
        findings.extend(_finding_records(scanned.counts, item_id=item_id))
        expected = expected_files.get(canonical)
        if (
            expected is None
            or member.size != expected.size_bytes
            or scanned.size_bytes != expected.size_bytes
            or scanned.sha256 != expected.sha256
        ):
            invalid_inventory = True
    _raise_for_secret_findings(findings)
    if invalid_inventory or seen_names != expected_names:
        raise CodexSessionBackupError("Codex session archive inventory is quarantined")
    return members


def _remove_generated_tree(path: Path) -> None:
    if path.is_symlink():
        path.unlink(missing_ok=True)
    elif path.exists():
        shutil.rmtree(path)


def _best_effort_remove_tree(path: Path) -> None:
    try:
        _remove_generated_tree(path)
    except OSError:
        pass


def _best_effort_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def _extract_validated_members(
    archive: tarfile.TarFile,
    members: list[tarfile.TarInfo],
    restore_root: Path,
    records: tuple[SessionFile, ...],
) -> None:
    expected_directories, _expected_files = _expected_archive_inventory(records)
    file_members = {
        _canonical_archive_member_name(member.name, is_directory=False): member
        for member in members
        if member.isfile()
    }
    restored_sessions = restore_root / "sessions"
    restored_sessions.mkdir(mode=0o700)
    for member_name in sorted(
        expected_directories - {"sessions"},
        key=lambda value: (len(PurePosixPath(value).parts), value),
    ):
        relative_parts = PurePosixPath(member_name).parts[1:]
        (restored_sessions / Path(*relative_parts)).mkdir(mode=0o700)
    for record in records:
        member_name = PurePosixPath("sessions", *PurePosixPath(record.path).parts).as_posix()
        member = file_members[member_name]
        stream = archive.extractfile(member)
        if stream is None:
            raise CodexSessionBackupError("validated archive member body is unavailable")
        destination = restored_sessions / Path(*PurePosixPath(record.path).parts)
        with stream, destination.open("xb") as output:
            shutil.copyfileobj(stream, output, length=_SECRET_SCAN_BLOCK_BYTES)
            output.flush()
            os.fsync(output.fileno())


def _verify_restored_tree(
    restored_sessions: Path,
    records: tuple[SessionFile, ...],
) -> None:
    root_mode = restored_sessions.lstat().st_mode
    if stat.S_ISLNK(root_mode) or not stat.S_ISDIR(root_mode):
        raise CodexSessionBackupError("restored session root is unsafe")
    expected_directories, expected_files = _expected_archive_inventory(records)
    expected_relative_directories = {
        PurePosixPath(*PurePosixPath(name).parts[1:]).as_posix()
        for name in expected_directories - {"sessions"}
    }
    expected_relative_files = {record.path for record in records}
    actual_directories: set[str] = set()
    actual_files: set[str] = set()
    for path in restored_sessions.rglob("*"):
        relative = _safe_relative_path(path, restored_sessions)
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise CodexSessionBackupError("restored session tree contains a symlink")
        if stat.S_ISDIR(mode):
            actual_directories.add(relative)
        elif stat.S_ISREG(mode):
            actual_files.add(relative)
        else:
            raise CodexSessionBackupError("restored session tree contains a special file")
    if (
        actual_directories != expected_relative_directories
        or actual_files != expected_relative_files
        or set(expected_files)
        != {
            PurePosixPath("sessions", *PurePosixPath(path).parts).as_posix()
            for path in actual_files
        }
    ):
        raise CodexSessionBackupError("restored session inventory mismatch")
    scanned_bytes = _scan_staged_session_secrets(restored_sessions, records)
    if scanned_bytes != sum(record.size_bytes for record in records):
        raise CodexSessionBackupError("restored session scan byte count drifted")
    for record in records:
        restored = _resolved_staged_file(restored_sessions, record.path)
        os.chmod(restored, record.mode)
        os.utime(restored, ns=(record.mtime_ns, record.mtime_ns))
        final = restored.stat()
        if stat.S_IMODE(final.st_mode) != record.mode or final.st_mtime_ns != record.mtime_ns:
            raise CodexSessionBackupError("restored session metadata mismatch")


def verify_session_archive(archive_path: Path, manifest_path: Path, restore_root: Path) -> bool:
    created_restore_root = False
    resolved_restore_root: Path | None = None
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        _version, archive_record, records = _validated_manifest(payload)
        expected_archive_sha256 = _require_sha256(
            archive_record.get("sha256"), field="archive.sha256"
        )
        expected_archive_size = _require_manifest_integer(
            archive_record.get("size_bytes"), field="archive.size_bytes", minimum=0
        )
        if sha256_file(archive_path) != expected_archive_sha256:
            raise CodexSessionBackupError("Codex session archive SHA-256 mismatch")
        if archive_path.stat().st_size != expected_archive_size:
            raise CodexSessionBackupError("Codex session archive size mismatch")
        resolved_restore_root = restore_root.resolve()
        if resolved_restore_root.exists():
            raise CodexSessionBackupError("session restore destination already exists")
        resolved_restore_root.mkdir(parents=True)
        created_restore_root = True
        with tarfile.open(archive_path, "r:gz") as archive:
            members = _validated_members(archive, records)
            if sha256_file(archive_path) != expected_archive_sha256:
                raise CodexSessionBackupError("Codex session archive changed during verification")
            _extract_validated_members(archive, members, resolved_restore_root, records)
        if sha256_file(archive_path) != expected_archive_sha256:
            raise CodexSessionBackupError("Codex session archive changed during extraction")
        _verify_restored_tree(resolved_restore_root / "sessions", records)
        return True
    except CodexSessionBackupError:
        if created_restore_root and resolved_restore_root is not None:
            _best_effort_remove_tree(resolved_restore_root)
        raise
    except Exception:
        if created_restore_root and resolved_restore_root is not None:
            _best_effort_remove_tree(resolved_restore_root)
        raise CodexSessionBackupError("Codex session archive verification failed safely") from None


def create_session_archive(
    source_root: Path,
    staging_root: Path,
    *,
    host: str,
    created_at: datetime,
) -> SessionArchive:
    snapshot_created = False
    archive_created = False
    manifest_created = False
    snapshot_root: Path | None = None
    archive_path: Path | None = None
    manifest_path: Path | None = None
    local_verify_root: Path | None = None
    try:
        _reject_secret_text(host)
        staging_root = staging_root.resolve()
        staging_root.mkdir(parents=True, exist_ok=True)
        snapshot_root = staging_root / "session-snapshot"
        archive_path = staging_root / "codex-sessions.tar.gz"
        manifest_path = staging_root / "codex-sessions.manifest.json"
        local_verify_root = staging_root / "local-verified-restore"
        if any(
            path.exists() or path.is_symlink()
            for path in (snapshot_root, archive_path, manifest_path, local_verify_root)
        ):
            raise CodexSessionBackupError("session staging destination is not empty")
        snapshot_root.mkdir(mode=0o700)
        snapshot_created = True
        records = _stage_session_tree(source_root, snapshot_root)
        scanned_bytes = _scan_staged_session_secrets(snapshot_root, records)
        if scanned_bytes != sum(record.size_bytes for record in records):
            raise CodexSessionBackupError("session secret scan byte count drifted")
        archive_created = True
        _write_archive(snapshot_root, archive_path, records)
        archive_sha256 = sha256_file(archive_path)
        payload = {
            "format_version": _MANIFEST_FORMAT_VERSION,
            "policy": _BACKUP_POLICY_V2,
            "created_at": created_at.astimezone(UTC).isoformat(),
            "host": host,
            "source_scope": "~/.codex/sessions/ only",
            "secret_scan": {
                "policy": _SECRET_SCAN_POLICY,
                "status": "PASS",
                "detectors": list(_SECRET_DETECTOR_NAMES),
                "scanned_file_count": len(records),
                "scanned_bytes": scanned_bytes,
            },
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
        manifest_created = True
        manifest_sha256 = atomic_write_json(manifest_path, payload)
        if not verify_session_archive(archive_path, manifest_path, local_verify_root):
            raise CodexSessionBackupError("local Codex session archive verification failed")
        _remove_generated_tree(local_verify_root)
        _remove_generated_tree(snapshot_root)
        snapshot_created = False
        return SessionArchive(
            archive_path=archive_path,
            manifest_path=manifest_path,
            archive_sha256=archive_sha256,
            manifest_sha256=manifest_sha256,
            file_count=len(records),
            total_bytes=sum(record.size_bytes for record in records),
        )
    except CodexSessionBackupError:
        if local_verify_root is not None:
            _best_effort_remove_tree(local_verify_root)
        if snapshot_created and snapshot_root is not None:
            _best_effort_remove_tree(snapshot_root)
        if manifest_created and manifest_path is not None:
            _best_effort_unlink(manifest_path)
        if archive_created and archive_path is not None:
            _best_effort_unlink(archive_path)
        raise
    except Exception:
        if local_verify_root is not None:
            _best_effort_remove_tree(local_verify_root)
        if snapshot_created and snapshot_root is not None:
            _best_effort_remove_tree(snapshot_root)
        if manifest_created and manifest_path is not None:
            _best_effort_unlink(manifest_path)
        if archive_created and archive_path is not None:
            _best_effort_unlink(archive_path)
        raise CodexSessionBackupError("Codex session archive creation failed safely") from None


def _safe_key_component(value: str, *, field: str) -> str:
    _reject_secret_text(value)
    cleaned = _SAFE_KEY_COMPONENT.sub("-", value.strip()).strip("-.")
    if not cleaned:
        raise CodexSessionBackupError(f"invalid {field}")
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
    _reject_secret_text(prefix)
    clean_prefix = PurePosixPath(prefix.strip("/"))
    if clean_prefix.is_absolute() or not clean_prefix.parts or ".." in clean_prefix.parts:
        raise CodexSessionBackupError("invalid S3 session prefix")
    with tempfile.TemporaryDirectory(prefix="bctc-codex-session-backup-") as temporary:
        temporary_root = Path(temporary)
        local = create_session_archive(
            source_root,
            temporary_root / "create",
            host=safe_host,
            created_at=created_at,
        )
        client.preflight()
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
