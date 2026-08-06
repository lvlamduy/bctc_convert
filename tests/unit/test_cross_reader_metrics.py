from __future__ import annotations

import json

from bctc_ai.evaluation.cross_reader_metrics import (
    aggregate_cross_reader_metrics,
    classify_cross_reader_error_classes,
)


def test_aggregate_metrics_replays_e0010_without_changing_denominators(project_root):
    artifact = json.loads(
        (
            project_root / "docs/experiments/E-0010-tcb-cross-reader-calibration.json"
        ).read_text(encoding="utf-8")
    )
    metrics = aggregate_cross_reader_metrics(
        page["comparison"] for page in artifact["pages"]
    )

    assert metrics == artifact["metrics"]


def test_error_taxonomy_identifies_structural_loss_in_e0010(project_root):
    artifact = json.loads(
        (
            project_root / "docs/experiments/E-0010-tcb-cross-reader-calibration.json"
        ).read_text(encoding="utf-8")
    )
    result = classify_cross_reader_error_classes(artifact["metrics"])

    assert result["main_error_class"] == "STRUCTURAL_ROW_CELL_RECONSTRUCTION"
    assert result["classes"]["STRUCTURAL_ROW_CELL_RECONSTRUCTION"] == {
        "impact_count": 21,
        "structural_alignment_units": 7,
        "missing_reference_cells": 14,
    }
    assert result["classes"]["NUMERIC_SIGN_OCR"]["impact_count"] == 6
    assert result["classes"]["LABEL_SEMANTICS"]["impact_count"] == 4
    assert result["classes"]["NOTE_REFERENCE"]["impact_count"] == 1


def test_error_taxonomy_has_deterministic_tie_break():
    metrics = {
        "alignment_actions": {"MATCH": 3},
        "reference_financial_cells": 4,
        "compared_reference_financial_cells": 4,
        "exact_reference_financial_cells": 4,
        "structurally_comparable_rows": 3,
        "semantic_key_exact_labels": 3,
        "note_rows": 0,
        "exact_note_references": 0,
        "candidate_invalid_cells": 0,
    }

    result = classify_cross_reader_error_classes(metrics)

    assert result["main_error_class"] == "STRUCTURAL_ROW_CELL_RECONSTRUCTION"
