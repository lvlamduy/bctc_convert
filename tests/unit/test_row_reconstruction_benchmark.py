from __future__ import annotations

from pathlib import Path

import pytest

from bctc_ai.evaluation import row_reconstruction_benchmark
from bctc_ai.evaluation.row_reconstruction_benchmark import (
    RowReconstructionBenchmarkError,
    capture_e0029_row_reconstruction_benchmark,
    summarize_reconstructed_page,
)


def test_page_summary_keeps_blank_dash_invalid_and_provenance_distinct():
    rows = [
        {
            "source_row_ids": ["p3:line-1", "p3:line-2"],
            "label": "Khoản mục",
            "note_reference": "III.1",
            "cells": [{"observation": "VALUE"}, {"observation": "DASH"}],
        },
        {
            "source_row_ids": ["p3:line-2", "p3:line-3"],
            "label": "minh",
            "note_reference": None,
            "cells": [{"observation": "BLANK"}, {"observation": "INVALID"}],
        },
    ]

    summary = summarize_reconstructed_page(
        page=3,
        axes=[{"raw_header": "31/03/2026"}, {"raw_header": "31/12/2025"}],
        rows=rows,
        trailing_row_count=0,
        unassigned_numeric_line_indices=[99],
    )

    assert summary["observation_counts"] == {
        "BLANK": 1,
        "DASH": 1,
        "INVALID": 1,
        "VALUE": 1,
    }
    assert summary["duplicate_source_line_assignment_count"] == 1
    assert summary["header_companion_leak_count"] == 1
    assert summary["note_reference_count"] == 1
    assert summary["unassigned_numeric_line_count"] == 1


def test_e0029_capture_rejects_dirty_worktree(project_root, monkeypatch):
    monkeypatch.setattr(row_reconstruction_benchmark, "_git", lambda *_args: " M file")

    with pytest.raises(RowReconstructionBenchmarkError, match="requires clean Git code"):
        capture_e0029_row_reconstruction_benchmark(
            project_root,
            experiment_config_path=Path(
                "config/experiments/e0029-mbb-cdkt-row-reconstruction.yaml"
            ),
            batch_root=Path("unused"),
            output_path=Path("docs/experiments/unused-e0029.json"),
        )


def test_e0029_capture_refuses_existing_output(project_root, monkeypatch):
    monkeypatch.setattr(row_reconstruction_benchmark, "_git", lambda *_args: "")

    with pytest.raises(RowReconstructionBenchmarkError, match="refusing to overwrite"):
        capture_e0029_row_reconstruction_benchmark(
            project_root,
            experiment_config_path=Path(
                "config/experiments/e0029-mbb-cdkt-row-reconstruction.yaml"
            ),
            batch_root=Path("unused"),
            output_path=Path("docs/experiments/E-0026-REPLAY.md"),
        )
