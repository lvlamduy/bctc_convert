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
        "structural_compared_cell_disagreements": 0,
        "multi_number_candidate_cells": 0,
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


def test_cell_evidence_attributes_multi_number_and_blank_failures_to_structure():
    metrics = {
        "alignment_actions": {"MATCH": 2},
        "reference_financial_cells": 4,
        "compared_reference_financial_cells": 4,
        "exact_reference_financial_cells": 1,
        "structurally_comparable_rows": 2,
        "semantic_key_exact_labels": 2,
        "note_rows": 0,
        "exact_note_references": 0,
        "candidate_invalid_cells": 1,
    }
    comparisons = (
        {
            "alignment": [
                {
                    "action": "MATCH",
                    "cells": [
                        {
                            "exact": False,
                            "reference_present": True,
                            "candidate_present": True,
                            "reference_observation": "VALUE",
                            "candidate_observation": "INVALID",
                            "candidate_reason": "multiple financial numbers in one cell",
                        },
                        {
                            "exact": False,
                            "reference_present": True,
                            "candidate_present": True,
                            "reference_observation": "VALUE",
                            "candidate_observation": "BLANK",
                            "candidate_reason": None,
                        },
                        {
                            "exact": False,
                            "reference_present": True,
                            "candidate_present": True,
                            "reference_observation": "VALUE",
                            "candidate_observation": "VALUE",
                            "candidate_reason": None,
                        },
                        {
                            "exact": True,
                            "reference_present": True,
                            "candidate_present": True,
                            "reference_observation": "VALUE",
                            "candidate_observation": "VALUE",
                            "candidate_reason": None,
                        },
                    ],
                }
            ]
        },
    )

    result = classify_cross_reader_error_classes(metrics, comparisons)

    assert result["root_cause_mode"] == "CELL_AND_ALIGNMENT_EVIDENCE"
    assert result["classes"]["STRUCTURAL_ROW_CELL_RECONSTRUCTION"][
        "structural_compared_cell_disagreements"
    ] == 2
    assert result["classes"]["NUMERIC_SIGN_OCR"]["impact_count"] == 1
