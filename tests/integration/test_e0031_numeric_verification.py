from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file


def test_e0031_numeric_verification_is_hash_locked(project_root):
    path = project_root / "docs/experiments/E-0031-mbb-cdkt-numeric-verification.json"
    assert sha256_file(path) == (
        "27561d0975d6e9d1e59b61f3b7dbd838ef1a91864f9f5955f87a6807033b6d9a"
    )
    artifact = json.loads(path.read_text(encoding="utf-8"))

    assert artifact["experiment_id"] == "E-0031"
    assert artifact["status"] == "PASS_REFERENCE_BLIND_INDEPENDENT_NUMERIC_VERIFICATION"
    assert artifact["capture_git_commit"] == (
        "665454df1d0b0f855d246343bd5d8eada6035d77"
    )
    metrics = artifact["after"]["metrics"]
    assert metrics["cell_count"] == 126
    assert metrics["observed_cell_count"] == 117
    assert metrics["verified_observed_cell_count"] == 114
    assert metrics["observed_exact_agreement_rate"] == 0.974359
    assert metrics["verification_status_counts"] == {
        "UNRESOLVED_BLANK_PENDING_ROW_SEMANTICS": 9,
        "UNRESOLVED_READER_DISAGREEMENT": 3,
        "VERIFIED_OBSERVED_DASH": 3,
        "VERIFIED_OBSERVED_VALUE": 111,
    }
    assert metrics["blank_to_zero_or_value_promotion_count"] == 0
    assert metrics["automatic_reader_overwrite_count"] == 0
    assert metrics["reader_score_decision_use_count"] == 0
    assert all(artifact["gates"].values())
    assert artifact["reference_isolation"]["human_review_loaded"] is False
    assert artifact["reference_isolation"]["schema_mapping_invoked"] is False
    assert artifact["reference_isolation"]["off_balance_page_5_loaded"] is False

    unresolved = [
        cell
        for cell in artifact["after"]["cells"]
        if cell["verification_status"] == "UNRESOLVED_READER_DISAGREEMENT"
    ]
    assert len(unresolved) == 3
    assert all(cell["normalized_numeric_value"] is None for cell in unresolved)
    assert all(cell["final_value_status"] is None for cell in unresolved)
