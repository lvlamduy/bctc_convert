from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts/experiments/export_shb_maturity_review_workbook_v1.py"
)
_SPEC = importlib.util.spec_from_file_location("export_shb_maturity_review_workbook_v1", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
cli = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cli)


def _payloads() -> tuple[bytes, bytes]:
    return b"review-workbook", b'{"artifact_role":"review-only"}\n'


def test_publish_is_exclusive_and_preserves_first_pair(tmp_path: Path) -> None:
    directory = tmp_path / "pair"
    workbook, provenance = _payloads()
    workbook_path, provenance_path = cli._publish(directory, workbook, provenance)

    assert workbook_path.read_bytes() == workbook
    assert provenance_path.read_bytes() == provenance
    first_hashes = (
        hashlib.sha256(workbook_path.read_bytes()).hexdigest(),
        hashlib.sha256(provenance_path.read_bytes()).hexdigest(),
    )
    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        cli._publish(directory, b"changed", b"changed")
    assert first_hashes == (
        hashlib.sha256(workbook_path.read_bytes()).hexdigest(),
        hashlib.sha256(provenance_path.read_bytes()).hexdigest(),
    )


def test_output_path_rejects_outside_parent_traversal_and_symlink(
    tmp_path: Path, monkeypatch
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.setattr(cli, "PROJECT_ROOT", project)

    assert cli._safe_project_output_directory(Path("output/review")) == (project / "output/review")
    with pytest.raises(RuntimeError, match="parent traversal"):
        cli._safe_project_output_directory(Path("../outside/review"))
    with pytest.raises(RuntimeError, match="parent traversal"):
        cli._safe_project_output_directory(project / "../outside-audit-do-not-create/review")
    with pytest.raises(RuntimeError, match="inside the project"):
        cli._safe_project_output_directory(outside / "review")

    (project / "output").symlink_to(outside, target_is_directory=True)
    with pytest.raises(RuntimeError, match="not a real directory"):
        cli._safe_project_output_directory(Path("output/review"))
