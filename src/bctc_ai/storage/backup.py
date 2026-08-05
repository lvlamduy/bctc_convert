from __future__ import annotations

import json
import os
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file

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


def _included_files(project_root: Path) -> list[Path]:
    result = []
    for path in project_root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(project_root).as_posix()
        if any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        if relative in BACKUP_FILE_NAMES or relative.startswith(BACKUP_PREFIXES):
            result.append(path)
    return sorted(result)


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
            bundle.extractall(destination, members=members)
        for record in manifest["files"]:
            restored = destination / record["path"]
            if not restored.is_file() or sha256_file(restored) != record["sha256"]:
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
    try:
        with tarfile.open(temporary, "w:gz") as bundle:
            for path in files:
                bundle.add(path, arcname=path.relative_to(project_root).as_posix(), recursive=False)
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
        "files": [
            {
                "path": path.relative_to(project_root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in files
        ],
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
