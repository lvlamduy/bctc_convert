from __future__ import annotations

from pathlib import Path

import pytest

from bctc_ai.evaluation import ordered_anchor_locator_benchmark
from bctc_ai.evaluation.ordered_anchor_locator_benchmark import (
    OrderedAnchorLocatorBenchmarkError,
    _json_canonical,
    capture_e0028_ordered_anchor_benchmark,
    structural_statement_summary,
)


def test_structural_summary_excludes_text_and_numeric_content():
    result = {
        "status": "ACCEPTED_MULTI_SIGNAL_STATEMENT_BLOCK",
        "runner_up_margin": 8.5,
        "block": {
            "mapping_eligible_pages_by_statement_type": {
                "CDKT": [3, 4],
                "KQKD": [6],
                "LCTT": [7, 8],
            },
            "off_balance_excluded_pages": [5],
            "notes_boundary_page": 9,
            "unrelated_values": [123, 456],
        },
        "cash_flow": {"method": "DIRECT", "ordered_anchors": ["secret"]},
    }

    assert structural_statement_summary(result) == {
        "status": "ACCEPTED_MULTI_SIGNAL_STATEMENT_BLOCK",
        "mapping_eligible_pages_by_statement_type": {
            "CDKT": [3, 4],
            "KQKD": [6],
            "LCTT": [7, 8],
        },
        "off_balance_excluded_pages": [5],
        "notes_boundary_page": 9,
        "runner_up_margin": 8.5,
        "cash_flow_method": "DIRECT",
    }


def test_json_canonical_normalizes_tuple_to_sealed_list_representation():
    assert _json_canonical({"period": ("2026", "2025")}) == {"period": ["2026", "2025"]}


def test_e0028_capture_rejects_dirty_worktree(project_root, monkeypatch):
    monkeypatch.setattr(ordered_anchor_locator_benchmark, "_git", lambda *_args: " M file")

    with pytest.raises(OrderedAnchorLocatorBenchmarkError, match="requires clean Git code"):
        capture_e0028_ordered_anchor_benchmark(
            project_root,
            experiment_config_path=Path(
                "config/experiments/e0028-bounded-ordered-anchor-locator.yaml"
            ),
            batch_root=Path("unused"),
            output_path=Path("docs/experiments/unused-e0028.json"),
        )


def test_e0028_capture_refuses_existing_output(project_root, monkeypatch):
    monkeypatch.setattr(ordered_anchor_locator_benchmark, "_git", lambda *_args: "")

    with pytest.raises(OrderedAnchorLocatorBenchmarkError, match="refusing to overwrite"):
        capture_e0028_ordered_anchor_benchmark(
            project_root,
            experiment_config_path=Path(
                "config/experiments/e0028-bounded-ordered-anchor-locator.yaml"
            ),
            batch_root=Path("unused"),
            output_path=Path("docs/experiments/E-0026-REPLAY.md"),
        )
