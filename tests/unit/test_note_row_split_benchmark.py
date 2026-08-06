from __future__ import annotations

from pathlib import Path

import pytest

from bctc_ai.evaluation import note_row_split_benchmark
from bctc_ai.evaluation.note_row_split_benchmark import (
    NoteRowSplitBenchmarkError,
    capture_e0032_note_row_split_benchmark,
    compare_row_contracts,
)


def _row(ids, label, cells):
    return {"source_row_ids": ids, "label": label, "cells": cells}


def test_row_contract_delta_requires_exact_partition_and_preserves_cells():
    values = [{"raw_text": "100", "observation": "VALUE", "value": "100"}]
    dashes = [{"raw_text": "-", "observation": "DASH", "value": None}]
    before = [
        {
            "page": 3,
            "rows": [_row(["p:l1", "p:l2", "p:l3"], "A B", values)],
        }
    ]
    after = [
        {
            "page": 3,
            "rows": [
                _row(["p:l1"], "A", dashes),
                _row(["p:l2", "p:l3"], "B", values),
            ],
        }
    ]

    result = compare_row_contracts(before, after)

    assert result["removed_composite_row_count"] == 1
    assert result["replacement_row_count"] == 2
    assert result["partitioned_split_count"] == 1
    assert result["preserved_value_cell_split_count"] == 1
    assert result["source_line_coverage_delta_count"] == 0


def test_e0032_capture_rejects_dirty_worktree(project_root, monkeypatch):
    monkeypatch.setattr(note_row_split_benchmark, "_git", lambda *_args: " M file")

    with pytest.raises(NoteRowSplitBenchmarkError, match="requires clean Git code"):
        capture_e0032_note_row_split_benchmark(
            project_root,
            experiment_config_path=Path(
                "config/experiments/e0032-mbb-cdkt-note-row-split.yaml"
            ),
            batch_root=Path("unused"),
            output_path=Path("docs/experiments/unused-e0032.json"),
        )


def test_e0032_capture_refuses_existing_output(project_root, monkeypatch):
    monkeypatch.setattr(note_row_split_benchmark, "_git", lambda *_args: "")

    with pytest.raises(NoteRowSplitBenchmarkError, match="refusing to overwrite"):
        capture_e0032_note_row_split_benchmark(
            project_root,
            experiment_config_path=Path(
                "config/experiments/e0032-mbb-cdkt-note-row-split.yaml"
            ),
            batch_root=Path("unused"),
            output_path=Path("docs/experiments/E-0031-mbb-cdkt-numeric-verification.json"),
        )
