from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/experiments/build_currency_risk_8bank_codex_verified_mapping_v1.py"


def _module():
    name = "build_currency_risk_8bank_codex_verified_mapping_v1_test_target"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _result(module):
    return json.loads((ROOT / module.RESULT_PATH).read_text())


def test_live_result_maps_six_unique_tables_and_bounds_two_absences() -> None:
    module = _module()
    result = module.build_live_currency_risk_8bank_codex_verified_mapping_v1()
    assert result["metrics"] == {
        "accounting_equation_verified_count": 48,
        "detailed_table_not_present_document_count": 2,
        "document_count": 8,
        "document_unique_region_count": 6,
        "fresh_vietocr_numeric_disagreement_count": 1,
        "mapping_verified_count": 103,
        "open_source_group_count": 11,
        "open_source_value_cell_count": 25,
        "q1_source_period_caveat_document_count": 1,
        "source_presentation_residual_count": 2,
        "verified_value_cell_count": 119,
    }
    assert [trial["document_provenance"] for trial in result["trials"]] == [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert [
        trial["status"] == "CONFIRMED_DETAILED_TABLE_NOT_PRESENT_IN_BOUND_REPORT"
        for trial in result["trials"]
    ] == [True, False, False, False, False, False, True, False]


def test_all_promoted_values_participate_in_exact_accounting_equations() -> None:
    module = _module()
    result = _result(module)
    assert all(
        equation["computed_value"] == equation["visible_value"]
        and equation["residual"] == 0
        and equation["status"] == "VERIFIED_EXACT"
        for trial in result["trials"]
        for equation in trial["verified_accounting_equations"]
    )
    assert all(
        value["source_numeric_challenger_status"] == "MATCHED_VISIBLE_PIXEL_TRANSCRIPTION"
        for trial in result["trials"]
        for mapping in trial["verified_mappings"]
        for value in mapping["values"]
    )


def test_gold_residual_missing_closure_and_vnd_scope_stay_open() -> None:
    module = _module()
    result = _result(module)
    gaps = [
        (trial["document_provenance"], row["gap_id"], row["axis_role"], row["reason"])
        for trial in result["trials"]
        for row in trial["verified_source_only_rows"]
    ]
    assert gaps == [
        ("VPB", "CRISK-001", "EUR", "SOURCE_PRESENTATION_ARITHMETIC_RESIDUAL"),
        ("VPB", "CRISK-002", "GOLD", "NO_GOLD_CURRENCY_AXIS_SCHEMA_BRANCH"),
        ("VPB", "CRISK-003", "OTHER", "NO_EXACT_ACCOUNTING_CLOSURE_FOR_THIS_VISIBLE_CELL"),
        ("VPB", "CRISK-004", "TOTAL", "SOURCE_PRESENTATION_ARITHMETIC_RESIDUAL"),
        ("VPB", "CRISK-005", "USD", "NO_EXACT_ACCOUNTING_CLOSURE_FOR_THIS_VISIBLE_CELL"),
        ("HDB", "CRISK-006", "EUR", "NO_EXACT_ACCOUNTING_CLOSURE_FOR_THIS_VISIBLE_CELL"),
        ("HDB", "CRISK-007", "GOLD", "NO_GOLD_CURRENCY_AXIS_SCHEMA_BRANCH"),
        ("VCB", "CRISK-008", "VND", "VND_SOURCE_TOTAL_EXCLUDES_SCHEMA_PARENT_EQUITY_SCOPE"),
        ("CTG", "CRISK-009", "GOLD", "NO_GOLD_CURRENCY_AXIS_SCHEMA_BRANCH"),
        ("VIB", "CRISK-010", "EUR", "NO_EXACT_ACCOUNTING_CLOSURE_FOR_THIS_VISIBLE_CELL"),
        ("VIB", "CRISK-011", "USD", "NO_EXACT_ACCOUNTING_CLOSURE_FOR_THIS_VISIBLE_CELL"),
    ]
    assert (
        sum(
            len(row["values"])
            for trial in result["trials"]
            for row in trial["verified_source_only_rows"]
        )
        == 25
    )


def test_first_monetary_column_is_not_lost_in_wide_vcb_and_ctg_tables() -> None:
    module = _module()
    result = _result(module)
    vcb = result["trials"][4]
    ctg = result["trials"][5]
    assert sum(len(row["values"]) for row in vcb["verified_mappings"]) == 14
    assert sum(len(row["values"]) for row in ctg["verified_mappings"]) == 25
    assert {equation["axis_role"] for equation in vcb["verified_accounting_equations"]} == {
        "EUR",
        "OTHER",
        "TOTAL",
        "USD",
        "VND",
    }
    assert {equation["axis_role"] for equation in ctg["verified_accounting_equations"]} == {
        "EUR",
        "OTHER",
        "TOTAL",
        "USD",
        "VND",
    }


def test_public_exact_replay_rejects_coordinated_value_tamper() -> None:
    module = _module()
    forged = copy.deepcopy(_result(module))
    forged["trials"][1]["verified_mappings"][0]["values"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0101:result:" + module.canonical_json_sha256_v1(material)
    with pytest.raises(
        module.CurrencyRisk8BankCodexVerifiedMappingV1Error,
        match="replay exactly",
    ):
        module.validate_live_currency_risk_8bank_codex_verified_mapping_v1(forged)


def test_typed_metric_and_authority_substitution_rejects() -> None:
    module = _module()
    result = _result(module)
    forged = copy.deepcopy(result)
    forged["metrics"]["verified_value_cell_count"] = 119.0
    with pytest.raises(module.CurrencyRisk8BankCodexVerifiedMappingV1Error):
        module._validate_result(forged)
    forged = copy.deepcopy(result)
    forged["authority"]["blank_cell_interpreted_as_zero"] = 0
    with pytest.raises(module.CurrencyRisk8BankCodexVerifiedMappingV1Error):
        module._validate_result(forged)
