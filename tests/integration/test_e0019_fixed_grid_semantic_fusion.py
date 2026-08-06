from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file


def test_e0019_fixed_grid_fusion_is_hash_locked_and_preserves_geometry(project_root):
    artifact_path = (
        project_root / "docs/experiments/E-0019-fixed-grid-semantic-fusion-tcb-lctt.json"
    )
    assert sha256_file(artifact_path) == (
        "f670de2d7e5a84574ba7e7965a79ccb4e9adb6c8643c84ce190c2ec84ed4a6f1"
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact["format_version"] == 1
    assert artifact["experiment_id"] == "E-0019"
    assert artifact["dataset_role"] == "CALIBRATION"
    assert artifact["status"] == ("PASS_CALIBRATION_FIXED_GRID_FUSION_NO_CONFIDENCE_PROMOTION")
    assert artifact["code"] == {
        "git_commit": "1a23b7b437e7d95a652c69e8748a037ad6d2224a",
        "git_dirty": False,
    }
    assert "not human gold" in artifact["claim_boundary"]

    before = artifact["before"]
    after = artifact["after"]
    assert before["error_analysis"]["main_error_class"] == ("STRUCTURAL_ROW_CELL_RECONSTRUCTION")
    assert before["metrics"]["candidate_invalid_cells"] == 12
    assert before["metrics"]["strict_exact_reference_cell_agreement_rate"] == 0.486111
    assert after["error_analysis"]["main_error_class"] == "LABEL_SEMANTICS"
    assert after["metrics"]["candidate_invalid_cells"] == 0
    assert after["metrics"]["alignment_actions"] == {"MATCH": 41}
    assert after["metrics"]["reference_financial_cells"] == 72
    assert after["metrics"]["exact_reference_financial_cells"] == 72
    assert after["metrics"]["strict_exact_reference_cell_agreement_rate"] == 1.0
    assert after["metrics"]["strict_exact_reference_financial_row_agreement_rate"] == 1.0
    assert after["metrics"]["semantic_key_exact_labels"] == 40
    assert after["error_analysis"]["classes"]["LABEL_SEMANTICS"]["impact_count"] == 1
    assert artifact["delta"]["structural_error_impact"] == -42

    summary = artifact["fusion_summary"]
    assert summary == {
        "exact_semantic_numeric_fingerprints": 41,
        "fused_rows": 41,
        "geometry_cells_unmodified": True,
        "geometry_rows": 41,
        "overflow_repairs": 1,
        "semantic_rows_before_fusion": 42,
    }
    assert [(page["candidate_page"], page["geometry_row_count"]) for page in artifact["pages"]] == [
        (13, 33),
        (14, 8),
    ]
    assert artifact["pages"][0]["fusion"]["overflow_repairs"] == []
    repair = artifact["pages"][1]["fusion"]["overflow_repairs"]
    assert len(repair) == 1
    assert repair[0]["geometry_indices"] == [2, 3]
    assert repair[0]["semantic_indices"] == [2, 3, 4]
    assert repair[0]["score_gain"] == 0.392032
    assert repair[0]["first_numeric_fingerprint_exact"] is True
    assert repair[0]["second_numeric_fingerprint_exact"] is True
    assert repair[0]["third_semantic_row_cells_blank"] is True
    assert all(
        row["geometry_cells_unmodified"] is True
        for page in artifact["pages"]
        for row in page["fusion"]["rows"]
    )

    assert artifact["cash_flow"]["baseline_method"] == "UNKNOWN"
    assert artifact["cash_flow"]["fused_method"] == "DIRECT"
    assert artifact["cash_flow"]["direct_anchor_positions"] == [1, 2]
    assert artifact["cash_flow"]["semantic_high_confidence_allowed"] is False
    assert all(
        value is False
        for key, value in artifact["acceptance"].items()
        if key != "fixed_grid_fusion_replay_complete"
    )
    for relative_path, digest in artifact["algorithm_files_sha256"].items():
        assert sha256_file(project_root / relative_path) == digest
