from __future__ import annotations

import yaml

from bctc_ai.core.hashing import sha256_file
from bctc_ai.recovery.artifact_registry import verify_frozen_artifact


def test_e0030_control_is_reference_blind_and_hash_locked(project_root):
    path = project_root / "config/experiments/e0030-mbb-cdkt-table-metadata.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert payload["version"] == 1
    assert payload["experiment_id"] == "E-0030"
    assert payload["source"]["target_pages"] == [3, 4]
    assert payload["source"]["excluded_off_balance_pages"] == [5]
    assert payload["source"]["scope"] == "UNKNOWN"
    for record in payload["frozen_inputs"].values():
        verify_frozen_artifact(project_root, record)
    candidate = payload["candidate"]
    assert candidate["git_commit"] == "480f0eb51e909fcd0b52d448792aa51f82e70534"
    for name in ("config", "algorithm"):
        record = candidate[name]
        assert sha256_file(project_root / record["path"]) == record["sha256"]
    forbidden = set(payload["forbidden_inputs"])
    assert "human_review_period_answers_labels_ids_or_values" in forbidden
    assert "mongodb_or_historical_values" in forbidden
    assert "template_labels_or_report_norm_ids" in forbidden
    assert "numeric_cell_text_or_value_as_period_unit_feature" in forbidden
    assert "horizontal_position_as_period_role" in forbidden
    assert "off_balance_page_5" in forbidden
