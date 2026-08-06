from __future__ import annotations

from pathlib import Path

import pytest

from bctc_ai.evaluation import table_metadata_benchmark
from bctc_ai.evaluation.table_metadata_benchmark import (
    TableMetadataBenchmarkError,
    capture_e0030_table_metadata_benchmark,
)


def test_e0030_capture_rejects_dirty_worktree(project_root, monkeypatch):
    monkeypatch.setattr(table_metadata_benchmark, "_git", lambda *_args: " M file")

    with pytest.raises(TableMetadataBenchmarkError, match="requires clean Git code"):
        capture_e0030_table_metadata_benchmark(
            project_root,
            experiment_config_path=Path("config/experiments/e0030-mbb-cdkt-table-metadata.yaml"),
            batch_root=Path("unused"),
            output_path=Path("docs/experiments/unused-e0030.json"),
        )


def test_e0030_capture_refuses_existing_output(project_root, monkeypatch):
    monkeypatch.setattr(table_metadata_benchmark, "_git", lambda *_args: "")

    with pytest.raises(TableMetadataBenchmarkError, match="refusing to overwrite"):
        capture_e0030_table_metadata_benchmark(
            project_root,
            experiment_config_path=Path("config/experiments/e0030-mbb-cdkt-table-metadata.yaml"),
            batch_root=Path("unused"),
            output_path=Path("docs/experiments/E-0026-REPLAY.md"),
        )
