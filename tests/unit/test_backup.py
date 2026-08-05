from __future__ import annotations

import json
from pathlib import Path

from bctc_ai.storage.backup import create_backup, restore_test


def test_local_restore_passes_development_but_not_off_machine_production_gate(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "README.md").write_text("evidence\n", encoding="utf-8")
    source = project / "src" / "example.py"
    source.parent.mkdir()
    source.write_text("VALUE = 1\n", encoding="utf-8")
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
        project / "vietstock_bctc/BANK/report.pdf",
        project / "output/run/result.json",
    ]
    for path in excluded_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"excluded")

    result = create_backup(project, tmp_path / "backups", off_machine=False)
    manifest = json.loads(Path(result.manifest).read_text(encoding="utf-8"))
    archived_paths = {record["path"] for record in manifest["files"]}

    assert archived_paths == {"README.md", "config/runtime.toml"}
    assert result.file_count == 2
