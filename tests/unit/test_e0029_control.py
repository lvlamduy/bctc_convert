from __future__ import annotations

import yaml

from bctc_ai.core.hashing import sha256_file
from bctc_ai.recovery.artifact_registry import verify_frozen_artifact


def test_e0029_control_is_reference_blind_and_hash_locked(project_root):
    path = project_root / "config/experiments/e0029-mbb-cdkt-row-reconstruction.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert payload["version"] == 1
    assert payload["experiment_id"] == "E-0029"
    assert payload["source"]["target_pages"] == [3, 4]
    assert payload["source"]["excluded_off_balance_pages"] == [5]
    for record in payload["frozen_inputs"].values():
        verify_frozen_artifact(project_root, record)
    candidate = payload["candidate"]
    assert candidate["git_commit"] == "88a28cfb04151b9c13d1631a1cff44effa1cfd90"
    for name in ("config", "algorithm"):
        record = candidate[name]
        assert sha256_file(project_root / record["path"]) == record["sha256"]
    forbidden = set(payload["forbidden_inputs"])
    assert "human_review_pages_labels_ids_values_or_period_answers" in forbidden
    assert "template_labels_or_report_norm_ids" in forbidden
    assert "numeric_value_plausibility" in forbidden
    assert "off_balance_page_5_rows" in forbidden
