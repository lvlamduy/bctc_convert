from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/experiments/build_owner_adjudicated_catchall_average_closure_v1.py"


def _module():
    name = "owner_adjudicated_catchall_average_closure_v1_test_target"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_live_closure_exactly_closes_ten_rows_without_double_mapping() -> None:
    module = _module()
    result = module.build_live_owner_adjudicated_catchall_average_closure_v1()
    assert result["metrics"] == {
        "accounting_equation_verified_count": 10,
        "catchall_aggregate_output_count": 4,
        "closed_open_source_row_count": 10,
        "derived_monthly_mapping_count": 2,
        "direct_catchall_mapping_count": 2,
        "output_mapping_count": 8,
        "source_value_component_count": 23,
    }
    assert result["closed_source_row_ids"] == [
        "CRPE-001",
        "CRPE-002",
        "OACT-001",
        "EI-001",
        "EI-002",
        "SBO-001",
        "CC-001",
        "CC-002",
        "CC-003",
        "CC-004",
    ]
    assert [row["schema_binding"]["report_norm_id"] for row in result["verified_mappings"]] == [
        1228,
        1228,
        1239,
        1267,
        1268,
        1279,
        1288,
        1288,
    ]


def test_catchall_aggregations_and_accounting_totals_are_exact() -> None:
    module = _module()
    result = module.build_live_owner_adjudicated_catchall_average_closure_v1()
    rows = result["verified_mappings"]
    assert rows[2]["values"] == {
        "COMPARATIVE_PERIOD": 230643,
        "CURRENT_PERIOD": 584150,
    }
    assert rows[5]["values"] == {
        "BUSINESS_COMBINATION_INCREASE": 0,
        "CLOSING": 0,
        "OPENING": 0,
        "PAID_DECREASE": -2500,
        "PAYABLE_INCREASE": 2500,
    }
    assert rows[6]["values"] == {"COMPARATIVE": 687893688, "CURRENT": 688039608}
    assert rows[7]["values"] == {"COMPARATIVE": 153501606, "CURRENT": 204865534}
    assert all(
        equation["computed_value"] == equation["visible_value"]
        and equation["status"] == "VERIFIED_EXACT"
        for equation in result["verified_accounting_equations"]
    )


def test_acb_six_month_values_are_divided_by_six_as_exact_rationals() -> None:
    module = _module()
    result = module.build_live_owner_adjudicated_catchall_average_closure_v1()
    salary, income = result["verified_mappings"][3:5]
    assert salary["values"]["CURRENT_PERIOD"]["derived_exact_rational"] == {
        "denominator": 1,
        "numerator": 15,
    }
    assert salary["values"]["COMPARATIVE_PERIOD"]["derived_exact_rational"] == {
        "denominator": 3,
        "numerator": 43,
    }
    assert income["values"]["CURRENT_PERIOD"]["derived_exact_rational"] == {
        "denominator": 2,
        "numerator": 81,
    }
    assert income["values"]["COMPARATIVE_PERIOD"]["derived_exact_rational"] == {
        "denominator": 6,
        "numerator": 247,
    }
    assert all(
        value["months_in_source_period"] == 6
        for row in (salary, income)
        for value in row["values"].values()
    )


def test_persisted_closure_exact_replays_and_coordinated_tamper_rejects() -> None:
    module = _module()
    payload = module._strict_json(
        module._stable_bytes(module.OUTPUT_PATH), module.OUTPUT_PATH.as_posix()
    )
    assert (
        module.validate_owner_adjudicated_catchall_average_closure_replay_v1(payload)["result_id"]
        == payload["result_id"]
    )

    tampered = copy.deepcopy(payload)
    tampered["verified_mappings"][7]["values"]["CURRENT"] += 1
    material = copy.deepcopy(tampered)
    material.pop("result_id")
    tampered["result_id"] = "e0100:result:" + module.canonical_json_sha256_v1(material)
    with pytest.raises(module.OwnerAdjudicatedClosureV1Error):
        module.validate_owner_adjudicated_catchall_average_closure_replay_v1(tampered)


def test_bool_or_float_substitution_rejects() -> None:
    module = _module()
    result = module.build_live_owner_adjudicated_catchall_average_closure_v1()
    tampered = copy.deepcopy(result)
    tampered["metrics"]["closed_open_source_row_count"] = 10.0
    with pytest.raises(module.OwnerAdjudicatedClosureV1Error):
        module.validate_owner_adjudicated_catchall_average_closure_replay_v1(tampered)

    tampered = copy.deepcopy(result)
    tampered["authority"]["catchall_rows_double_mapped"] = 0
    with pytest.raises(module.OwnerAdjudicatedClosureV1Error):
        module.validate_owner_adjudicated_catchall_average_closure_replay_v1(tampered)
