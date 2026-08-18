from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT
    / "scripts/experiments/build_annual_2025_employee_income_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_employee_income_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def result() -> dict[str, object]:
    built = builder.build_live_annual_2025_employee_income_8bank_codex_verified_mapping_v1()
    persisted = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())
    assert builder._base().same_typed_json_v1(built, persisted)
    return built


def _trial(result: dict[str, object], code: str) -> dict[str, object]:
    return next(item for item in result["trials"] if item["document_provenance"] == code)


def _mapping(trial: dict[str, object], role: str) -> dict[str, object]:
    return next(item for item in trial["verified_mappings"] if item["role"] == role)


def test_four_unique_regions_and_four_bounded_absences(result: dict[str, object]) -> None:
    assert result["result_id"] == builder.EXPECTED_RESULT_ID
    assert result["metrics"] == {
        "accounting_equation_verified_count": 16,
        "detailed_note_not_present_document_count": 4,
        "document_count": 8,
        "document_unique_region_count": 4,
        "mapping_verified_count": 18,
        "open_source_row_count": 0,
        "q1_source_period_caveat_document_count": 0,
        "verified_value_cell_count": 36,
    }
    assert [trial["page_span"] for trial in result["trials"]] == [
        [73, 73],
        None,
        [73, 73],
        None,
        None,
        None,
        [58, 58],
        [54, 54],
    ]


def test_acb_annual_values_are_corroborated_then_derived_monthly(
    result: dict[str, object],
) -> None:
    acb = _trial(result, "ACB")
    assert [
        value["normalized_decimal_value"]
        for value in _mapping(acb, "AVERAGE_SALARY_MONTH")["values"]
    ] == ["13.94", "14.16"]
    assert [
        value["normalized_decimal_value"]
        for value in _mapping(acb, "AVERAGE_INCOME_MONTH")["values"]
    ] == ["38.10", "37.57"]
    for role in ("AVERAGE_SALARY_MONTH", "AVERAGE_INCOME_MONTH"):
        assert all(
            value["derivation"]["printed_annual_average_corroborated"] is True
            and value["derivation"]["months_in_source_period"] == 12
            for value in _mapping(acb, role)["values"]
        )


def test_bid_wrapped_staff_label_and_vib_trailing_label_are_verified(
    result: dict[str, object],
) -> None:
    bid = _trial(result, "BID")
    vib = _trial(result, "VIB")
    assert _mapping(bid, "EMPLOYEE_COUNT")["topology"] == ("WRAPPED_LABEL_TWO_ANNUAL_PERIOD_LANES")
    assert _mapping(vib, "AVERAGE_INCOME_MONTH")["topology"] == (
        "VALUES_PRECEDE_TRAILING_LABEL_TWO_ANNUAL_PERIOD_LANES"
    )
    assert _mapping(bid, "AVERAGE_INCOME_MONTH")["values"][1]["normalized_decimal_value"] == "40.94"
    assert _mapping(vib, "AVERAGE_INCOME_MONTH")["values"][1]["normalized_decimal_value"] == "36.76"


def test_live_schema_binding_and_zero_open_rows(result: dict[str, object]) -> None:
    assert result["schema_family"]["mapped_report_norm_ids"] == [
        1261,
        1262,
        1263,
        1265,
        1266,
        1267,
        1268,
    ]
    assert result["schema_family"]["family_end_display_order"] == 848
    assert all(not trial["verified_source_only_rows"] for trial in result["trials"])


def test_public_replay_rejects_coordinated_derived_value_tamper(
    result: dict[str, object],
) -> None:
    forged = copy.deepcopy(result)
    value = _mapping(forged["trials"][0], "AVERAGE_INCOME_MONTH")["values"][0]
    value["normalized_decimal_value"] = "999.99"
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + builder._base().canonical_json_sha256_v1(
        material
    )
    with pytest.raises(
        builder.Annual2025EmployeeIncome8BankError,
        match="employee-income result ID drifted",
    ):
        builder.validate_annual_2025_employee_income_8bank_codex_verified_mapping_replay_v1(forged)
