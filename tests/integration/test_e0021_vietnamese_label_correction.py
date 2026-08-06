from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file


def test_e0021_vietnamese_label_correction_is_hash_locked_and_fail_closed(project_root):
    artifact_path = project_root / "docs/experiments/E-0021-vietnamese-label-correction-tcb.json"
    assert sha256_file(artifact_path) == (
        "accefa38db2131ebf5b0aa9fa37394d382fe0c98cbcfa6358ef304c0d626ba9a"
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact["format_version"] == 1
    assert artifact["experiment_id"] == "E-0021"
    assert artifact["dataset_role"] == "CALIBRATION"
    assert artifact["status"] == (
        "PASS_CALIBRATION_VIETNAMESE_LABEL_CORRECTION_NO_CONFIDENCE_PROMOTION"
    )
    assert artifact["code"] == {
        "git_commit": "c32741a217ca16e7224d416b2c14245f580e610d",
        "git_dirty": False,
    }
    assert "not human gold" in artifact["claim_boundary"]
    assert "Reference labels are used only after proposal generation" in artifact["claim_boundary"]

    assert artifact["metrics"] == {
        "corrected_casefold_exact_labels": 108,
        "corrected_semantic_key_exact_labels": 140,
        "non_improving_proposals": 0,
        "proposal_casefold_precision": 1.0,
        "proposed_rows": 4,
        "raw_casefold_exact_labels": 104,
        "raw_semantic_key_exact_labels": 136,
        "rows": 140,
        "semantic_key_regressions": 0,
        "unchanged_rows": 136,
    }
    assert artifact["delta"] == {
        "casefold_exact_labels": 4,
        "semantic_key_exact_labels": 4,
    }
    assert [
        (item["candidate_page"], item["alignment_index"]) for item in artifact["corrections"]
    ] == [
        (14, 0),
        (14, 11),
        (14, 18),
        (14, 25),
    ]
    assert all(item["after_casefold_exact"] for item in artifact["corrections"])
    assert all(item["after_semantic_key_exact"] for item in artifact["corrections"])
    assert all(
        item["proposal"]["raw_label"] != item["proposal"]["corrected_label"]
        for item in artifact["corrections"]
    )
    assert sum(len(item["proposal"]["replacements"]) for item in artifact["corrections"]) == 5
    assert all(
        replacement["damerau_distance"] == 1
        for item in artifact["corrections"]
        for replacement in item["proposal"]["replacements"]
    )

    assert artifact["safety"] == {
        "automatic_output_authority": False,
        "automatic_schema_mapping_authority": False,
        "confidence_promoted": False,
        "numeric_or_note_fields_present": False,
        "period_or_scope_fields_present": False,
        "raw_labels_preserved": True,
        "role_a_labels_used_as_correction_features": False,
        "row_order_preserved": True,
    }
    assert artifact["upstream_numeric_structure"] == {
        "candidate_invalid_cells": 0,
        "correction_layer_received_numeric_or_note_fields": False,
        "e0020_after_metrics_sha256": (
            "c05ffb9ecfdf04008a9497bde135712d9aa7a3f5aa656fab599c919345d3382c"
        ),
        "exact_financial_cells": 264,
        "financial_cells": 264,
    }
    assert artifact["schema_vocabulary"]["item_count"] == 1593
    assert artifact["schema_vocabulary"]["workbook_display_order_preserved"] is True
    assert artifact["schema_vocabulary"]["numeric_report_norm_id_sort_used"] is False
    assert artifact["schema_vocabulary"]["tm_1944_present"] is True
    assert artifact["schema_vocabulary"]["tm_1944_name"] == (
        "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán"
    )
    assert artifact["schema_vocabulary"]["report_norm_id_output_or_mapping_emitted"] is False
    assert artifact["acceptance"]["all_140_rows_replayed"] is True
    assert artifact["acceptance"]["all_four_semantic_residuals_corrected"] is True
    assert artifact["acceptance"]["non_target_proposal_count"] == 0
    assert all(
        value is False
        for key, value in artifact["acceptance"].items()
        if key
        not in {
            "all_140_rows_replayed",
            "all_four_semantic_residuals_corrected",
            "non_target_proposal_count",
        }
    )
    for relative_path, digest in artifact["algorithm_files_sha256"].items():
        assert sha256_file(project_root / relative_path) == digest
