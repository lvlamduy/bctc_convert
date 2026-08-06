from __future__ import annotations

import yaml

from bctc_ai.core.hashing import sha256_file


def test_e0027_control_is_reference_blind_and_end_to_end(project_root):
    path = project_root / "config/experiments/e0027-mbb-q1-2026-end-to-end.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert payload["version"] == 1
    assert payload["experiment_id"] == "E-0027"
    assert payload["dataset_role"] == "CALIBRATION"
    assert payload["source"]["input_page_window"] == {
        "start": 1,
        "end": 9,
        "dpi": 300,
    }
    assert sha256_file(project_root / payload["source"]["path"]) == (
        payload["source"]["sha256"]
    )
    for component in payload["frozen_components"].values():
        assert sha256_file(project_root / component["path"]) == component["sha256"]

    role_b = payload["role_b_contract"]
    assert role_b["reference_fields_available_to_reader"] is False
    assert role_b["values_allowed_as_schema_mapping_features"] is False
    assert role_b["history_allowed_as_schema_mapping_features"] is False
    assert role_b["deepseek_numeric_period_unit_sign_scope_mapping_authority"] is False
    assert role_b["automatic_confidence_promotion"] is False
    assert not any("human-review" in value for value in role_b["allowed_inputs"])
    assert any("human-review" in value for value in role_b["forbidden_inputs"])
    assert any("E-0022" in value for value in role_b["forbidden_inputs"])

    evaluation = payload["evaluation_only_after_role_b_seal"]
    assert evaluation["reviewed_pages_are_not_routing_inputs"] is True
    assert evaluation["reviewed_schema_row_count"] == 6
    assert evaluation["reviewed_value_cell_count"] == 12
    assert sha256_file(project_root / evaluation["dataset_path"]) == (
        evaluation["dataset_sha256"]
    )

    required = set(payload["required_metrics"])
    assert {
        "statement_page_exactness_on_reviewed_scope",
        "logical_row_coverage",
        "reviewed_schema_id_exactness",
        "period_role_and_date_exactness",
        "raw_and_normalized_numeric_exactness",
        "value_status_exactness",
        "full_tuple_exactness",
        "workbook_cell_exactness",
        "arithmetic_pass_fail_not_testable_count",
    } <= required
    acceptance = payload["acceptance_policy"]
    assert acceptance["role_b_must_be_sealed_before_reference_access"] is True
    assert acceptance["duplicate_schema_assignment_count"] == 0
    assert acceptance["human_gold_or_production_accuracy_claim"] is False
