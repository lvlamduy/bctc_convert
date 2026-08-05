from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file


def test_frozen_tcb_cross_reader_calibration(project_root):
    artifact_path = (
        project_root / "docs/experiments/E-0010-tcb-cross-reader-calibration.json"
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact["format_version"] == 2
    assert artifact["experiment_id"] == "E-0010"
    assert artifact["dataset_role"] == "CALIBRATION"
    assert artifact["status"] == "PASS_CALIBRATION_WITH_REQUIRED_ESCALATIONS"
    assert "not human-gold" in artifact["claim_boundary"]
    assert "not" in artifact["claim_boundary"] and "production accuracy" in artifact[
        "claim_boundary"
    ]

    suite_config = project_root / artifact["suite_config"]["path"]
    assert sha256_file(suite_config) == artifact["suite_config"]["sha256"]
    for relative_path, digest in artifact["algorithm_files_sha256"].items():
        assert sha256_file(project_root / relative_path) == digest

    assert artifact["metrics"] == {
        "alignment_actions": {
            "EXTRA_CANDIDATE": 2,
            "MATCH": 131,
            "MERGE_CANDIDATE": 1,
            "MERGE_REFERENCE": 4,
        },
        "candidate_invalid_cells": 1,
        "candidate_rows": 139,
        "compared_reference_financial_cells": 250,
        "conditional_exact_cell_agreement_rate": 0.976,
        "conditional_exact_financial_row_agreement_rate": 0.968,
        "covered_reference_financial_rows": 125,
        "escalations": {
            "CELL_AXIS_RECONSTRUCTION_AND_REREAD": 1,
            "CORROBORATED_NO_CONFIDENCE_PROMOTION": 94,
            "LABEL_REREAD_OR_STRUCTURAL_REVIEW": 32,
            "NOTE_REFERENCE_REREAD": 1,
            "TABLE_RECONSTRUCTION_REVIEW": 6,
            "TARGETED_NUMERIC_REREAD_DISAGREEMENT": 3,
            "TARGETED_NUMERIC_REREAD_INVALID_CELL": 1,
        },
        "exact_note_references": 47,
        "exact_reference_financial_cells": 244,
        "exact_reference_financial_rows": 121,
        "note_rows": 48,
        "reference_financial_cell_coverage_rate": 0.94697,
        "reference_financial_cells": 264,
        "reference_financial_row_coverage_rate": 0.94697,
        "reference_financial_rows": 132,
        "reference_rows": 140,
        "scope_allowed_candidate_rows": 119,
        "scope_excluded_candidate_rows": 20,
        "semantic_key_exact_label_rate": 0.969697,
        "semantic_key_exact_labels": 128,
        "source_exact_label_rate": 0.742424,
        "source_exact_labels": 98,
        "strict_exact_reference_cell_agreement_rate": 0.924242,
        "strict_exact_reference_financial_row_agreement_rate": 0.916667,
        "structurally_comparable_rows": 132,
    }
    assert artifact["acceptance"] == {
        "agreement_promotes_pdf_confidence": False,
        "auto_verified_high": 0,
        "disagreements_trigger_reread_or_review": True,
        "reason": (
            "PaddleOCR-VL exposes table-level but not independently verified cell "
            "geometry; reader agreement alone cannot satisfy the high-confidence gate."
        ),
    }
    assert artifact["historical_weak_reference"]["invoked"] is False
    assert (
        artifact["historical_weak_reference"]["mapping_or_confidence_effect"]
        == "NONE"
    )
    assert artifact["off_balance_gate"] == {
        "eligible_rows_on_off_balance_pages": 0,
        "status": "PASS_ZERO_CDKT_ELIGIBLE_ROWS",
    }
    assert artifact["cash_flow"]["method"] == "DIRECT"
    assert artifact["cash_flow"]["semantic_high_confidence_allowed"] is False
    assert len(artifact["continuation"]) == 1
    assert artifact["continuation"][0]["accepted"] is True

    page_14 = next(page for page in artifact["pages"] if page["candidate_page"] == 14)
    merged = [
        record
        for record in page_14["comparison"]["alignment"]
        if record["action"] == "MERGE_REFERENCE"
    ]
    assert len(merged) == 4
    assert all(record["escalation"] == "TABLE_RECONSTRUCTION_REVIEW" for record in merged)

    page_15 = next(page for page in artifact["pages"] if page["candidate_page"] == 15)
    invalid_cells = [
        cell
        for record in page_15["comparison"]["alignment"]
        for cell in record.get("cells", [])
        if cell["candidate_observation"] == "INVALID"
    ]
    assert len(invalid_cells) == 1
    assert invalid_cells[0]["candidate_raw"] == "198.242 (5.140.484)"
    assert invalid_cells[0]["candidate_reason"] == (
        "multiple financial numbers in one cell"
    )

    for sealed in artifact["sealed_inputs"].values():
        local_path = project_root / sealed["path"]
        if local_path.is_file():
            assert sha256_file(local_path) == sealed["sha256"]
