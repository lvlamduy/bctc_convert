from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file


def test_e0018_targeted_semantic_reader_is_hash_locked_and_fail_closed(project_root):
    artifact_path = project_root / "docs/experiments/E-0018-deepseek-ocr2-tcb-lctt.json"
    assert sha256_file(artifact_path) == (
        "1b09f40f379bc84797e21f2f5f81f00369deacb1f322e0fdfd044cb93e626a64"
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact["format_version"] == 1
    assert artifact["experiment_id"] == "E-0018"
    assert artifact["dataset_role"] == "CALIBRATION"
    assert artifact["status"] == ("PASS_CALIBRATION_TARGETED_READER_WITH_NO_CONFIDENCE_PROMOTION")
    assert artifact["code"] == {
        "git_commit": "254bf5d20cc20cf983eeb740805cfbb3fe277090",
        "git_dirty": False,
    }
    assert "not human gold" in artifact["claim_boundary"]

    before = artifact["before"]["metrics"]
    after = artifact["after"]["metrics"]
    assert before["candidate_invalid_cells"] == 12
    assert before["exact_reference_financial_cells"] == 21
    assert before["strict_exact_reference_cell_agreement_rate"] == 0.362069
    assert after["candidate_invalid_cells"] == 0
    assert after["reference_financial_cells"] == 58
    assert after["exact_reference_financial_cells"] == 58
    assert after["strict_exact_reference_cell_agreement_rate"] == 1.0
    assert after["strict_exact_reference_financial_row_agreement_rate"] == 1.0
    assert artifact["delta"]["structural_error_impact"] == -41

    table = artifact["table_reconstruction"]
    assert table["raw_grid_row_count"] == 35
    assert table["canonical_row_count"] == 33
    assert len(table["fragment_merges"]) == 1
    assert table["fragment_merges"][0]["value_cells_unmodified"] is True
    assert table["fragment_merges"][0]["rule"] == ("ADJACENT_LABEL_ONLY_THEN_VALUE_ONLY_SAME_WIDTH")

    assert artifact["cash_flow"]["baseline_method"] == "UNKNOWN"
    assert artifact["cash_flow"]["targeted_reader_method"] == "DIRECT"
    assert artifact["cash_flow"]["direct_anchor_positions"] == [1, 2]
    assert artifact["cash_flow"]["semantic_high_confidence_allowed"] is False
    assert all(
        value is False
        for key, value in artifact["acceptance"].items()
        if key != "targeted_reader_eligible_for_geometry_fusion"
    )

    for relative_path, digest in artifact["algorithm_files_sha256"].items():
        assert sha256_file(project_root / relative_path) == digest
