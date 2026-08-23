from __future__ import annotations

import io
import json
import os
import stat
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.storage.credential_scan import (
    SECRET_DETECTOR_NAMES,
    SECRET_SCAN_POLICY,
    scan_stream,
)


class ControlPlaneBackupError(RuntimeError):
    """Raised when a control-plane backup cannot be created safely."""


BACKUP_FILE_NAMES = {
    ".gitignore",
    "README.md",
    "pyproject.toml",
    "uv.lock",
    "Dockerfile",
    "docker-compose.yml",
    "RECOVERY_AUDIT.md",
    "HARDWARE_AUDIT.md",
    "BOOTSTRAP_MANIFEST.json",
    "PROJECT_GOAL.md",
    "ARCHITECTURE.md",
    "questions_for_user.md",
    "questions_for_user.csv",
    "questions_for_user.jsonl",
    "proposed_schema_additions.jsonl",
    "PROGRESS_REPORT.md",
    "BACKUP_AND_RESTORE_RUNBOOK.md",
    "ACCURACY_REQUIREMENTS.md",
    "PROJECT_MEMORY.md",
    "Bank_list_id.xlsx",
}
BACKUP_PREFIXES = (
    "src/",
    "tests/",
    "config/",
    "reference/",
    "scripts/",
    "docs/",
    "template/",
    "vst_level/",
    "data/registered/",
)
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".ruff_cache"}
SELECTION_POLICY = "GIT_TRACKED_CONTROL_PLANE_ALLOWLIST_V1"


@dataclass(frozen=True)
class BackupResult:
    archive: str
    manifest: str
    archive_sha256: str
    file_count: int
    restored_and_verified: bool
    off_machine: bool

    @property
    def development_status(self) -> str:
        return "PASS" if self.restored_and_verified else "FAIL"

    @property
    def production_status(self) -> str:
        return "PASS" if self.restored_and_verified and self.off_machine else "FAIL"


def _tracked_paths(project_root: Path) -> tuple[PurePosixPath, ...]:
    completed = subprocess.run(
        ["git", "ls-files", "--cached", "-z"],
        cwd=project_root,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise ControlPlaneBackupError(
            "control-plane backup requires a readable Git tracked-file index"
        )
    paths: list[PurePosixPath] = []
    for encoded in completed.stdout.split(b"\0"):
        if not encoded:
            continue
        try:
            value = os.fsdecode(encoded)
        except UnicodeDecodeError as error:
            raise ControlPlaneBackupError(
                "control-plane Git path is not representable on this filesystem"
            ) from error
        path = PurePosixPath(value)
        if (
            not value
            or "\\" in value
            or path.is_absolute()
            or ".." in path.parts
            or path.as_posix() != value
        ):
            raise ControlPlaneBackupError("control-plane Git path is unsafe")
        paths.append(path)
    if len(paths) != len(set(paths)):
        raise ControlPlaneBackupError("control-plane Git path inventory repeats")
    return tuple(sorted(paths))


def _included_files(project_root: Path) -> list[Path]:
    result = []
    for relative_path in _tracked_paths(project_root):
        relative = relative_path.as_posix()
        if any(part in EXCLUDED_PARTS for part in relative_path.parts):
            continue
        if relative not in BACKUP_FILE_NAMES and not relative.startswith(BACKUP_PREFIXES):
            continue
        path = project_root / Path(*relative_path.parts)
        try:
            metadata = path.lstat()
        except OSError as error:
            raise ControlPlaneBackupError(
                "tracked control-plane file is absent or unreadable"
            ) from error
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise ControlPlaneBackupError(
                "tracked control-plane member must be one regular nofollow file"
            )
        result.append(path)
    if not result:
        raise ControlPlaneBackupError("tracked control-plane allowlist is empty")
    return sorted(result)


def _member_material(project_root: Path, path: Path) -> tuple[dict[str, object], bytes]:
    relative = path.relative_to(project_root).as_posix()
    before = path.lstat()
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise ControlPlaneBackupError("control-plane member changed into a non-regular file")
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise ControlPlaneBackupError("cannot read tracked control-plane member") from error
    after = path.lstat()
    before_identity = (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    after_identity = (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )
    if before_identity != after_identity or len(payload) != before.st_size:
        raise ControlPlaneBackupError("control-plane member changed while being read")
    scan = scan_stream(io.BytesIO(payload))
    if scan.counts:
        raise ControlPlaneBackupError(
            "control-plane credential scan rejected tracked content: "
            f"detectors={','.join(sorted(scan.counts))}"
        )
    return (
        {
            "path": relative,
            "size_bytes": scan.size_bytes,
            "sha256": scan.sha256,
            "mode": stat.S_IMODE(before.st_mode),
            "mtime": before.st_mtime,
        },
        payload,
    )


def _safe_member(member: tarfile.TarInfo) -> bool:
    path = PurePosixPath(member.name)
    return (
        not path.is_absolute()
        and ".." not in path.parts
        and not member.issym()
        and not member.islnk()
    )


def restore_test(archive: Path, manifest_path: Path) -> bool:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if sha256_file(archive) != manifest["archive_sha256"]:
        return False
    with tempfile.TemporaryDirectory(prefix="bctc-ai-restore-") as temp_name:
        destination = Path(temp_name)
        with tarfile.open(archive, "r:gz") as bundle:
            members = bundle.getmembers()
            if not all(_safe_member(member) for member in members):
                return False
            expected = [record["path"] for record in manifest["files"]]
            observed = [member.name for member in members]
            if (
                len(expected) != len(set(expected))
                or len(observed) != len(set(observed))
                or observed != expected
                or any(not member.isfile() for member in members)
            ):
                return False
            bundle.extractall(destination, members=members)
        for record in manifest["files"]:
            restored = destination / record["path"]
            if (
                not restored.is_file()
                or restored.stat().st_size != record["size_bytes"]
                or sha256_file(restored) != record["sha256"]
            ):
                return False
    return True


def create_backup(
    project_root: Path, destination: Path, *, off_machine: bool = False
) -> BackupResult:
    project_root = project_root.resolve()
    destination = destination.resolve()
    if destination == project_root or project_root in destination.parents:
        raise ValueError("backup destination must be outside the repository")
    destination.mkdir(parents=True, exist_ok=True)
    files = _included_files(project_root)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    archive = destination / f"bctc-ai-control-plane-{timestamp}.tar.gz"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".bctc-ai-backup-", suffix=".tar.gz", dir=destination
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    records: list[dict[str, object]] = []
    scanned_bytes = 0
    try:
        with tarfile.open(temporary, "w:gz") as bundle:
            for path in files:
                record, payload = _member_material(project_root, path)
                member = tarfile.TarInfo(str(record["path"]))
                member.size = int(record["size_bytes"])
                member.mode = int(record["mode"])
                member.mtime = float(record["mtime"])
                member.type = tarfile.REGTYPE
                bundle.addfile(member, io.BytesIO(payload))
                records.append(
                    {
                        "path": record["path"],
                        "size_bytes": record["size_bytes"],
                        "sha256": record["sha256"],
                    }
                )
                scanned_bytes += int(record["size_bytes"])
        with temporary.open("rb") as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, archive)
    finally:
        temporary.unlink(missing_ok=True)
    archive_hash = sha256_file(archive)
    manifest_path = archive.with_suffix(archive.suffix + ".manifest.json")
    manifest = {
        "format_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "archive": archive.name,
        "archive_sha256": archive_hash,
        "off_machine": off_machine,
        "selection": {
            "policy": SELECTION_POLICY,
            "tracked_allowlisted_file_count": len(records),
        },
        "credential_scan": {
            "detectors": list(SECRET_DETECTOR_NAMES),
            "policy": SECRET_SCAN_POLICY,
            "scanned_bytes": scanned_bytes,
            "scanned_file_count": len(records),
            "status": "PASS",
        },
        "files": records,
    }
    atomic_write_json(manifest_path, manifest)
    verified = restore_test(archive, manifest_path)
    return BackupResult(
        archive=str(archive),
        manifest=str(manifest_path),
        archive_sha256=archive_hash,
        file_count=len(files),
        restored_and_verified=verified,
        off_machine=off_machine,
    )
