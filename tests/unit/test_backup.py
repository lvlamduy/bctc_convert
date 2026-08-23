from __future__ import annotations

import json
import subprocess
import tarfile
from pathlib import Path

import pytest

from bctc_ai.storage.backup import (
    SELECTION_POLICY,
    ControlPlaneBackupError,
    create_backup,
    restore_test,
)


def _git(project: Path, *arguments: str) -> None:
    subprocess.run(["git", *arguments], cwd=project, check=True, capture_output=True)


def _commit_control_plane(project: Path) -> None:
    _git(project, "init")
    _git(project, "config", "user.name", "test")
    _git(project, "config", "user.email", "test@example.com")
    _git(project, "add", ".")
    _git(project, "commit", "-m", "control")


def test_local_restore_passes_development_but_not_off_machine_production_gate(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "README.md").write_text("evidence\n", encoding="utf-8")
    source = project / "src" / "example.py"
    source.parent.mkdir()
    source.write_text("VALUE = 1\n", encoding="utf-8")
    _commit_control_plane(project)
    destination = tmp_path / "backups"
    result = create_backup(project, destination, off_machine=False)
    assert result.restored_and_verified
    assert result.development_status == "PASS"
    assert result.production_status == "FAIL"
    assert restore_test(Path(result.archive), Path(result.manifest))


def test_control_plane_backup_excludes_reconstructable_and_large_local_assets(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "README.md").write_text("control plane\n", encoding="utf-8")
    included = project / "config" / "runtime.toml"
    included.parent.mkdir()
    included.write_text("version = 1\n", encoding="utf-8")
    excluded_paths = [
        project / ".gpu-venv/lib/package.bin",
        project / ".venv/lib/control.bin",
        project / ".local-mongodb/data.wt",
        project / ".tools/tool.bin",
        project / ".model-cache/weights.bin",
        project / "data/local/historical_weak_reference.duckdb",
        project / "vietstock_bctc/BANK/report.pdf",
        project / "output/run/result.json",
    ]
    for path in excluded_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"excluded")
    _commit_control_plane(project)

    result = create_backup(project, tmp_path / "backups", off_machine=False)
    manifest = json.loads(Path(result.manifest).read_text(encoding="utf-8"))
    archived_paths = [record["path"] for record in manifest["files"]]

    assert archived_paths == ["README.md", "config/runtime.toml"]
    assert manifest["selection"] == {
        "policy": SELECTION_POLICY,
        "tracked_allowlisted_file_count": 2,
    }
    assert manifest["credential_scan"]["status"] == "PASS"
    assert manifest["credential_scan"]["scanned_file_count"] == 2
    assert manifest["credential_scan"]["scanned_bytes"] == sum(
        record["size_bytes"] for record in manifest["files"]
    )
    with tarfile.open(result.archive, "r:gz") as archive:
        assert archive.getnames() == archived_paths
        assert all(member.isfile() for member in archive.getmembers())
    assert result.file_count == 2


def test_control_plane_backup_excludes_ignored_untracked_docs_secret(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "README.md").write_text("control plane\n", encoding="utf-8")
    _commit_control_plane(project)
    exclude = project / ".git" / "info" / "exclude"
    exclude.write_text("/docs/experiments/gemma.txt\n", encoding="utf-8")
    secret = project / "docs" / "experiments" / "gemma.txt"
    secret.parent.mkdir(parents=True)
    secret.write_text("AIza" + "A" * 35 + "\n", encoding="utf-8")
    assert (
        subprocess.run(
            ["git", "check-ignore", "--quiet", "docs/experiments/gemma.txt"],
            cwd=project,
            check=False,
        ).returncode
        == 0
    )

    result = create_backup(project, tmp_path / "backups", off_machine=False)
    manifest = json.loads(Path(result.manifest).read_text(encoding="utf-8"))

    assert [record["path"] for record in manifest["files"]] == ["README.md"]
    with tarfile.open(result.archive, "r:gz") as archive:
        assert archive.getnames() == ["README.md"]


def test_control_plane_backup_rejects_credential_in_tracked_allowlisted_member(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "README.md").write_text("control plane\n", encoding="utf-8")
    secret_value = "AIza" + "B" * 35
    secret = project / "docs" / "security-fixture.txt"
    secret.parent.mkdir()
    secret.write_text(secret_value + "\n", encoding="utf-8")
    _commit_control_plane(project)

    with pytest.raises(ControlPlaneBackupError) as captured:
        create_backup(project, tmp_path / "backups", off_machine=False)

    assert "credential scan rejected" in str(captured.value)
    assert "google_api_key" in str(captured.value)
    assert secret_value not in str(captured.value)
    assert not list((tmp_path / "backups").glob("*.tar.gz"))
