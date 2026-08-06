from __future__ import annotations

import yaml

from bctc_ai.core.hashing import sha256_file


def test_e0028_control_freezes_one_reference_blind_locator_change(project_root):
    path = project_root / "config/experiments/e0028-bounded-ordered-anchor-locator.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert payload["version"] == 1
    assert payload["experiment_id"] == "E-0028"
    assert payload["dataset_role"] == "CALIBRATION"
    for record in payload["frozen_inputs"].values():
        assert sha256_file(project_root / record["path"]) == record["sha256"]
    candidate = payload["candidate"]
    assert candidate["git_commit"] == "7250d022dbfd8ddc020c1028fb17de1017b015d0"
    assert candidate["only_change"] == "ACCOUNTING_ROW_ANCHOR_SCORER_ONLY"
    for name in ("base_config", "config", "algorithm"):
        record = candidate[name]
        assert sha256_file(project_root / record["path"]) == record["sha256"]

    forbidden = set(payload["forbidden_inputs"])
    assert "human_review_pages_labels_ids_values_or_period_answers" in forbidden
    assert "mongodb_or_historical_values" in forbidden
    assert "report_norm_id_numeric_order" in forbidden
    assert "E-0022_source_artifacts_output_or_diagnosis" in forbidden
    acceptance = payload["acceptance_policy"]
    assert acceptance["v3_baseline_replay_must_equal_sealed_result"] is True
    assert acceptance["e0013_mbb_vcb_structural_no_regression"] is True
    assert acceptance["one_phrase_never_classifies_a_page"] is True
    assert acceptance["human_gold_or_production_accuracy_claim"] is False
