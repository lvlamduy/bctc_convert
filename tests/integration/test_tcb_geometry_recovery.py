from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file


def test_frozen_tcb_targeted_geometry_recovery(project_root):
    artifact_path = project_root / "docs/experiments/E-0011-tcb-geometry-recovery.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact["format_version"] == 1
    assert artifact["experiment_id"] == "E-0011"
    assert artifact["dataset_role"] == "CALIBRATION"
    assert artifact["design"] == "TARGETED_POST_FAILURE_ANALYSIS"
    assert artifact["content_inspected_before_design"] is True
    assert artifact["status"] == "PASS_TARGETED_GEOMETRY_RECOVERY_CALIBRATION"
    assert "post-failure calibration" in artifact["claim_boundary"]
    assert "not human-gold" in artifact["claim_boundary"]
    assert "production accuracy" in artifact["claim_boundary"]
    assert "/workspace/" not in json.dumps(artifact)

    for config_key in ("experiment_config", "suite_config", "reconstruction_config"):
        record = artifact[config_key]
        assert sha256_file(project_root / record["path"]) == record["sha256"]
    for relative_path, digest in artifact["algorithm_files_sha256"].items():
        assert sha256_file(project_root / relative_path) == digest

    assert artifact["metrics"] == {
        "alignment_actions": {"MATCH": 140},
        "candidate_invalid_cells": 0,
        "candidate_rows": 140,
        "compared_reference_financial_cells": 264,
        "conditional_exact_cell_agreement_rate": 1.0,
        "conditional_exact_financial_row_agreement_rate": 1.0,
        "covered_reference_financial_rows": 132,
        "escalations": {
            "CORROBORATED_NO_CONFIDENCE_PROMOTION": 3,
            "LABEL_REREAD_OR_STRUCTURAL_REVIEW": 137,
        },
        "exact_note_references": 50,
        "exact_reference_financial_cells": 264,
        "exact_reference_financial_rows": 132,
        "note_rows": 50,
        "reference_financial_cell_coverage_rate": 1.0,
        "reference_financial_cells": 264,
        "reference_financial_row_coverage_rate": 1.0,
        "reference_financial_rows": 132,
        "reference_rows": 140,
        "scope_allowed_candidate_rows": 120,
        "scope_excluded_candidate_rows": 20,
        "semantic_key_exact_label_rate": 0.1,
        "semantic_key_exact_labels": 14,
        "source_exact_label_rate": 0.021429,
        "source_exact_labels": 3,
        "strict_exact_reference_cell_agreement_rate": 1.0,
        "strict_exact_reference_financial_row_agreement_rate": 1.0,
        "structurally_comparable_rows": 140,
    }
    assert artifact["acceptance"]["configured"] == artifact["acceptance"]["observed"]
    assert artifact["acceptance"]["auto_verified_high"] == 0
    assert artifact["acceptance"]["agreement_promotes_pdf_confidence"] is False
    assert artifact["acceptance"]["geometry_reader_can_override_label_or_schema_identity"] is False

    recovery = artifact["recovery_evidence"]
    assert len(recovery["pixel_dash_recoveries"]) == 3
    assert len(recovery["ocr_dash_alias_recoveries"]) == 1
    assert recovery["trailing_context_rows_preserved_but_mapping_ineligible"] == 14
    assert recovery["automatic_confidence_effect"] == "NONE"
    assert {
        (record["page"], record["row_index"], record["axis_index"])
        for record in recovery["pixel_dash_recoveries"]
    } == {(10, 18, 1), (11, 7, 1), (15, 2, 1)}
    assert all(
        record["evidence"]["observation"] == "DASH"
        and record["confidence_effect"] == "NO_PROMOTION"
        for record in recovery["pixel_dash_recoveries"]
    )
    assert recovery["ocr_dash_alias_recoveries"][0]["raw_ocr_tokens"] == ["一"]
    assert recovery["ocr_dash_alias_recoveries"][0]["normalized_observation"] == "DASH"

    arithmetic = artifact["arithmetic_validation"]
    assert arithmetic["counts"] == {"NOT_TESTABLE": 1, "PASS": 11}
    assert arithmetic["value_generation_or_overwrite"] is False
    assert all(finding["may_generate_value"] is False for finding in arithmetic["findings"])
    not_testable = [
        finding for finding in arithmetic["findings"] if finding["result"] == "NOT_TESTABLE"
    ]
    assert len(not_testable) == 1
    assert not_testable[0]["equation_id"] == "financing_cash_flow"
    assert not_testable[0]["period_index"] == 1

    assert artifact["off_balance_gate"] == {
        "eligible_rows_on_off_balance_pages": 0,
        "excluded_rows_on_off_balance_pages": 20,
        "status": "PASS_ZERO_CDKT_ELIGIBLE_ROWS",
    }
    assert len(artifact["continuation"]) == 1
    assert artifact["continuation"][0]["accepted"] is True
    assert artifact["cash_flow"]["role_b_label_reader"]["method"] == "DIRECT"
    assert artifact["cash_flow"]["role_c_geometry_reader"]["method"] == "UNKNOWN"
    assert artifact["cash_flow"]["schema_branch_assignment_permitted"] is False
    assert artifact["cash_flow"]["role_b_label_reader"][
        "semantic_high_confidence_allowed"
    ] is False

    page_counts = {
        page["candidate_page"]: (
            len(page["geometry"]["rows"]),
            len(page["geometry"]["trailing_context_rows"]),
        )
        for page in artifact["pages"]
    }
    assert page_counts == {
        10: (38, 0),
        11: (21, 0),
        12: (20, 0),
        13: (22, 14),
        14: (32, 0),
        15: (7, 0),
    }
    assert artifact["historical_weak_reference"]["invoked"] is False
    assert artifact["report_norm_id"]["ids_proposed_or_added"] == 0
    assert artifact["ytd_derivation"]["invoked"] is False
    assert artifact["sealed_inputs"]["role_b_seal"][
        "historical_seal_implementation_matches_current_tree"
    ] is False

    for sealed in artifact["sealed_inputs"].values():
        local_path = project_root / sealed["path"]
        if local_path.is_file():
            assert sha256_file(local_path) == sealed["sha256"]
