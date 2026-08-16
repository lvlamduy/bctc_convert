from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_employee_income_8bank_codex_verified_mapping_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_employee_income_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _result() -> dict[str, object]:
    return json.loads((_ROOT / builder.RESULT_PATH).read_text())


def _mapping(trial: dict[str, object], role: str) -> dict[str, object]:
    return next(item for item in trial["verified_mappings"] if item["role"] == role)


def test_review_finds_three_unique_regions_and_five_bounded_absences() -> None:
    documents = builder._review_blueprint()["documents"]
    assert [item["bank_code"] for item in documents] == [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert [item["page_span"] for item in documents] == [
        [26, 26],
        None,
        [66, 66],
        None,
        None,
        None,
        None,
        [49, 49],
    ]


def test_persisted_result_has_exact_denominator() -> None:
    result = builder._validate_result(_result())
    assert result["metrics"] == {
        "accounting_equation_verified_count": 14,
        "detailed_note_not_present_document_count": 5,
        "document_count": 8,
        "document_unique_region_count": 3,
        "mapping_verified_count": 13,
        "open_source_row_count": 2,
        "q1_source_period_caveat_document_count": 1,
        "verified_value_cell_count": 26,
    }
    assert result["schema_family"]["mapped_report_norm_ids"] == [
        1261,
        1262,
        1263,
        1265,
        1266,
        1267,
        1268,
    ]


def test_acb_period_averages_are_not_forced_into_monthly_schema() -> None:
    acb = _result()["trials"][0]
    assert acb["mapped_report_norm_ids"] == [1261, 1263, 1265, 1266]
    assert [item["row_id"] for item in acb["verified_source_only_rows"]] == [
        "EI-001",
        "EI-002",
    ]
    assert all(
        item["status"] == "UNRESOLVED_SCHEMA_PERIOD_SEMANTICS_SOURCE_ROW_RETAINED"
        for item in acb["verified_source_only_rows"]
    )
    assert len(acb["verified_accounting_equations"]) == 6


def test_monthly_averages_close_for_vpb_and_vib() -> None:
    result = _result()
    vpb = result["trials"][2]
    vib = result["trials"][7]
    assert [
        value["normalized_decimal_value"]
        for value in _mapping(vpb, "AVERAGE_SALARY_MONTH")["values"]
    ] == ["30.30", "28.15"]
    assert [
        value["normalized_decimal_value"]
        for value in _mapping(vib, "AVERAGE_INCOME_MONTH")["values"]
    ] == ["35.00", "36.19"]
    assert {
        item["months_in_source_period"]
        for item in vpb["verified_accounting_equations"]
        if "months_in_source_period" in item
    } == {3}
    assert {item["months_in_source_period"] for item in vib["verified_accounting_equations"]} == {6}


def test_public_replay_rejects_coordinated_period_semantics_promotion() -> None:
    forged = copy.deepcopy(_result())
    row = forged["trials"][0]["verified_source_only_rows"].pop()
    row["schema_binding"] = {"report_norm_id": 1268}
    row["status"] = "VERIFIED_BY_CODEX"
    forged["trials"][0]["verified_mappings"].append(row)
    forged["metrics"]["mapping_verified_count"] += 1
    forged["metrics"]["open_source_row_count"] -= 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0094:result:" + builder.canonical_json_sha256_v1(material)
    with pytest.raises(
        builder.EmployeeIncome8BankCodexVerifiedMappingV1Error,
        match="identity drifted|replay exactly",
    ):
        builder.validate_live_employee_income_8bank_codex_verified_mapping_v1(forged)
