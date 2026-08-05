from __future__ import annotations

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
