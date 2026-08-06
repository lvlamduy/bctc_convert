from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file


def test_e0020_ordered_segmentation_is_hash_locked_and_fail_closed(project_root):
    artifact_path = project_root / "docs/experiments/E-0020-ordered-label-segmentation-tcb.json"
    assert sha256_file(artifact_path) == (
        "2879361149a50c068f0d7590c6454535f4abae4002963f2f7defd471176d1ffb"
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact["format_version"] == 1
    assert artifact["experiment_id"] == "E-0020"
    assert artifact["dataset_role"] == "CALIBRATION"
    assert artifact["status"] == (
        "PASS_CALIBRATION_ORDERED_LABEL_SEGMENTATION_NO_CONFIDENCE_PROMOTION"
    )
    assert artifact["code"] == {
        "git_commit": "21d39cc5fbcb0d0411e08d8d61cd0b8df5aecaf3",
        "git_dirty": False,
    }
    assert "not human gold" in artifact["claim_boundary"]

    before = artifact["before"]
    after = artifact["after"]
    assert before["error_analysis"]["main_error_class"] == ("STRUCTURAL_ROW_CELL_RECONSTRUCTION")
    assert before["metrics"]["candidate_rows"] == 139
    assert before["metrics"]["candidate_invalid_cells"] == 1
    assert before["metrics"]["strict_exact_reference_cell_agreement_rate"] == 0.924242
    assert after["error_analysis"]["main_error_class"] == "LABEL_SEMANTICS"
    assert after["metrics"]["alignment_actions"] == {"MATCH": 140}
    assert after["metrics"]["candidate_invalid_cells"] == 0
    assert after["metrics"]["reference_financial_cells"] == 264
    assert after["metrics"]["exact_reference_financial_cells"] == 264
    assert after["metrics"]["strict_exact_reference_cell_agreement_rate"] == 1.0
    assert after["metrics"]["strict_exact_reference_financial_row_agreement_rate"] == 1.0
    assert after["metrics"]["semantic_key_exact_labels"] == 136
    assert after["error_analysis"]["classes"]["LABEL_SEMANTICS"]["impact_count"] == 4

    assert artifact["fusion_summary"] == {
        "fused_rows": 140,
        "geometry_cells_unmodified": True,
        "geometry_rows": 140,
        "ignored_blank_label_semantic_rows": 2,
        "rows_with_semantic_numeric_fingerprint": 130,
        "segmentation_actions": {
            "MERGE_ADJACENT_SEMANTIC_LABEL_FRAGMENTS": 1,
            "SPLIT_COLLAPSED_SEMANTIC_LABEL_1_TO_2": 4,
            "TRIM_DUPLICATE_EDGE_TOKENS": 1,
        },
        "semantic_rows": 139,
    }
    page_14 = next(page for page in artifact["pages"] if page["candidate_page"] == 14)
    assert page_14["fusion"]["alignment_action_counts"] == {
        "EXTRA_CANDIDATE": 2,
        "MATCH": 23,
        "MERGE_CANDIDATE": 1,
        "MERGE_REFERENCE": 4,
    }
    assert len(page_14["fusion"]["segmentations"]) == 6
    assert len(page_14["fusion"]["ignored_semantic_rows"]) == 2
    assert all(
        row["geometry_cells_unmodified"] is True
        for page in artifact["pages"]
        for row in page["fusion"]["rows"]
    )

    assert artifact["cash_flow"]["fused_method"] == "DIRECT"
    assert artifact["cash_flow"]["direct_anchor_positions"] == [1, 2]
    assert artifact["cash_flow"]["semantic_high_confidence_allowed"] is False
    assert artifact["off_balance_gate"] == {
        "candidate_page": 12,
        "expected_excluded_rows": 20,
        "mapping_eligible": False,
        "observed_excluded_rows": 20,
    }
    assert all(
        value is False
        for key, value in artifact["acceptance"].items()
        if key != "ordered_segmentation_replay_complete"
    )
    for relative_path, digest in artifact["algorithm_files_sha256"].items():
        assert sha256_file(project_root / relative_path) == digest
