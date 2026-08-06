from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file


def test_e0017_tcb_consolidated_native_role_ab_baseline(project_root):
    artifact_path = (
        project_root / "docs/experiments/E-0017-tcb-consolidated-native-role-ab.json"
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact["format_version"] == 3
    assert artifact["experiment_id"] == "E-0017"
    assert artifact["dataset_role"] == "CALIBRATION"
    assert artifact["status"] == "PASS_CALIBRATION_WITH_REQUIRED_ESCALATIONS"
    assert "not human-gold" in artifact["claim_boundary"]
    assert sha256_file(project_root / artifact["suite_config"]["path"]) == artifact[
        "suite_config"
    ]["sha256"]
    for relative_path, digest in artifact["algorithm_files_sha256"].items():
        assert sha256_file(project_root / relative_path) == digest

    metrics = artifact["metrics"]
    assert metrics["reference_rows"] == 147
    assert metrics["candidate_rows"] == 146
    assert metrics["reference_financial_rows"] == 139
    assert metrics["reference_financial_cells"] == 278
    assert metrics["reference_financial_row_coverage_rate"] == 0.94964
    assert metrics["reference_financial_cell_coverage_rate"] == 0.94964
    assert metrics["conditional_exact_financial_row_agreement_rate"] == 0.909091
    assert metrics["conditional_exact_cell_agreement_rate"] == 0.912879
    assert metrics["strict_exact_reference_financial_row_agreement_rate"] == 0.863309
    assert metrics["strict_exact_reference_cell_agreement_rate"] == 0.866906
    assert metrics["candidate_invalid_cells"] == 12
    assert metrics["alignment_actions"] == {
        "MATCH": 137,
        "MERGE_CANDIDATE": 3,
        "MERGE_REFERENCE": 3,
        "MISSING_CANDIDATE": 1,
    }

    analysis = artifact["error_analysis"]
    assert analysis["root_cause_mode"] == "CELL_AND_ALIGNMENT_EVIDENCE"
    assert analysis["main_error_class"] == "STRUCTURAL_ROW_CELL_RECONSTRUCTION"
    assert analysis["classes"]["STRUCTURAL_ROW_CELL_RECONSTRUCTION"] == {
        "impact_count": 42,
        "missing_reference_cells": 14,
        "multi_number_candidate_cells": 12,
        "structural_alignment_units": 7,
        "structural_compared_cell_disagreements": 21,
    }
    assert analysis["classes"]["NUMERIC_SIGN_OCR"]["impact_count"] == 2
    assert analysis["classes"]["LABEL_SEMANTICS"]["impact_count"] == 3
    assert analysis["classes"]["NOTE_REFERENCE"]["impact_count"] == 1

    exact_prefix_pages = [
        page for page in artifact["pages"] if page["candidate_page"] in {9, 10, 11, 12}
    ]
    assert sum(
        page["comparison"]["counts"]["reference_financial_cells"]
        for page in exact_prefix_pages
    ) == 206
    assert sum(
        page["comparison"]["counts"]["exact_reference_financial_cells"]
        for page in exact_prefix_pages
    ) == 206
    assert artifact["off_balance_gate"] == {
        "eligible_rows_on_off_balance_pages": 0,
        "status": "PASS_ZERO_CDKT_ELIGIBLE_ROWS",
    }
    assert len(artifact["continuation"]) == 1
    assert artifact["continuation"][0]["accepted"] is True
    assert artifact["cash_flow"]["method"] == "UNKNOWN"

    for sealed in artifact["sealed_inputs"].values():
        local_path = project_root / sealed["path"]
        if local_path.is_file():
            assert sha256_file(local_path) == sealed["sha256"]
