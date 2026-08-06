from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file


def test_e0034_numeric_verification_is_hash_locked(project_root):
    path = (
        project_root
        / "docs/experiments/E-0034-mbb-cdkt-numeric-verification-v2.json"
    )
    assert sha256_file(path) == (
        "08ecf8823154df415cc4f5bcbe65c5697412605eadc1a41f22315990ea20cc70"
    )
    artifact = json.loads(path.read_text(encoding="utf-8"))

    assert artifact["experiment_id"] == "E-0034"
    assert artifact["status"] == "PASS_REFERENCE_BLIND_INDEPENDENT_NUMERIC_VERIFICATION"
    assert artifact["capture_git_commit"] == (
        "278e1ed3d4db5cc46ae9cc21af55747c9a1713b7"
    )
    metrics = artifact["after"]["metrics"]
    assert metrics["cell_count"] == 128
    assert metrics["observed_cell_count"] == 119
    assert metrics["verified_observed_cell_count"] == 118
    assert metrics["observed_exact_agreement_rate"] == 0.991597
    assert metrics["verification_status_counts"] == {
        "UNRESOLVED_BLANK_PENDING_ROW_SEMANTICS": 9,
        "UNRESOLVED_READER_DISAGREEMENT": 1,
        "VERIFIED_OBSERVED_DASH": 5,
        "VERIFIED_OBSERVED_VALUE": 113,
    }
    assert metrics["blank_to_zero_or_value_promotion_count"] == 0
    assert metrics["automatic_reader_overwrite_count"] == 0
    assert metrics["reader_score_decision_use_count"] == 0
    assert all(artifact["gates"].values())
    assert artifact["reference_isolation"]["human_review_loaded"] is False
    assert artifact["reference_isolation"]["schema_mapping_invoked"] is False
    assert artifact["reference_isolation"]["excluded_off_balance_pages_loaded"] is False

    disagreements = [
        cell
        for cell in artifact["after"]["cells"]
        if cell["verification_status"] == "UNRESOLVED_READER_DISAGREEMENT"
    ]
    assert len(disagreements) == 1
    assert disagreements[0]["cell_id"] == "page-0004-row-011-axis-1"
    assert disagreements[0]["selected_raw_value"] is None
    assert disagreements[0]["normalized_numeric_value"] is None
    assert disagreements[0]["decision"] == "ABSTAIN_AND_RETAIN_BOTH_READER_PROPOSALS"
