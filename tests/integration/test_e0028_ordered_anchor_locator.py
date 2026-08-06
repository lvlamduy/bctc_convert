from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file


def test_e0028_bounded_ordered_anchor_result_is_hash_locked(project_root):
    artifact_path = project_root / "docs/experiments/E-0028-bounded-ordered-anchor-locator.json"
    assert sha256_file(artifact_path) == (
        "4c6e644f4f764d08b4c4dae580e49bfee50b3efeadedede668436e3b8d6d396a"
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact["experiment_id"] == "E-0028"
    assert artifact["status"] == "PASS_BOUNDED_ORDERED_ANCHOR_LOCATOR"
    assert artifact["dataset_role"] == "CALIBRATION"
    assert artifact["capture_git_commit"] == ("6e07119f6fad2274d43394cadc5dfd58d4ab45ab")
    assert artifact["before"] == {
        "cash_flow_method": None,
        "mapping_eligible_pages_by_statement_type": None,
        "notes_boundary_page": None,
        "off_balance_excluded_pages": None,
        "runner_up_margin": None,
        "status": "UNRESOLVED",
    }
    assert artifact["after"] == {
        "cash_flow_method": "DIRECT",
        "mapping_eligible_pages_by_statement_type": {
            "CDKT": [3, 4],
            "KQKD": [6],
            "LCTT": [7, 8],
        },
        "notes_boundary_page": 9,
        "off_balance_excluded_pages": [5],
        "runner_up_margin": 8.5,
        "status": "ACCEPTED_MULTI_SIGNAL_STATEMENT_BLOCK",
    }
    assert all(artifact["target_gates"].values())
    added = artifact["page_9_tm_incremental_evidence"]
    assert added["baseline_hit_count"] == 1
    assert added["extended_hit_count"] == 2
    assert added["added_hits"][0]["anchor"] == "thành lập và hoạt động"
    assert added["added_hits"][0]["similarity"] == 0.926829
    assert all(item["structural_exact_match"] for item in artifact["cross_document_no_regression"])
    assert artifact["reference_isolation"] == {
        "e0022_evidence_loaded": False,
        "excel_export_invoked": False,
        "historical_values_loaded": False,
        "human_review_loaded": False,
        "mapping_invoked": False,
        "numeric_extraction_invoked": False,
        "semantic_reader_invoked": False,
    }
