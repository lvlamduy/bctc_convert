from __future__ import annotations

import yaml

from bctc_ai.core.hashing import sha256_file


def test_e0031_control_is_reference_blind_and_fail_closed(project_root):
    path = project_root / "config/experiments/e0031-mbb-cdkt-numeric-verification.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert payload["experiment_id"] == "E-0031"
    assert payload["dataset_role"] == "CALIBRATION"
    assert payload["source"]["target_pages"] == [3, 4]
    assert payload["source"]["excluded_off_balance_pages"] == [5]
    assert payload["candidate"]["git_commit"] == (
        "686a73137474ffff5a2d738da31e74d7719aa2bc"
    )
    for record in payload["frozen_inputs"].values():
        assert sha256_file(project_root / record["path"]) == record["sha256"]
    for key in (
        "crop_policy",
        "model_config",
        "crop_algorithm",
        "reader_algorithm",
        "verification_algorithm",
    ):
        record = payload["candidate"][key]
        assert sha256_file(project_root / record["path"]) == record["sha256"]
    assert payload["acceptance_policy"]["minimum_observed_exact_agreement_rate"] == 0.95
    assert "human_review_labels_ids_or_values" in payload["forbidden_inputs"]
    assert "automatic_repair_or_overwrite_on_reader_disagreement" in payload[
        "forbidden_inputs"
    ]
    assert "dirty development smoke" in payload["development_note"]
