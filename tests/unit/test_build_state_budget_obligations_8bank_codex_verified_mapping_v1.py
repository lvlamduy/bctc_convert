from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT / "scripts/experiments/build_state_budget_obligations_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_state_budget_obligations_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _result() -> dict[str, object]:
    return json.loads((_ROOT / builder.RESULT_PATH).read_text())


def _trial(result: dict[str, object], bank_code: str) -> dict[str, object]:
    return next(item for item in result["trials"] if item["document_provenance"] == bank_code)


def _mapping(trial: dict[str, object], role: str) -> dict[str, object]:
    return next(item for item in trial["verified_mappings"] if item["role"] == role)


def test_review_covers_seven_unique_regions_and_one_bounded_absence() -> None:
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
        [22, 22],
        [49, 49],
        [58, 58],
        [32, 32],
        None,
        [43, 43],
        [26, 26],
        [47, 47],
    ]


def test_persisted_result_has_exact_denominator() -> None:
    result = builder._validate_result(_result())
    assert result["metrics"] == {
        "accounting_equation_verified_count": 37,
        "bound_report_detailed_note_absence_count": 1,
        "document_count": 8,
        "document_unique_region_count": 7,
        "mapping_verified_count": 33,
        "open_source_row_count": 1,
        "q1_source_period_caveat_document_count": 1,
        "verified_value_cell_count": 147,
        "visible_dash_zero_count": 13,
    }
    assert result["schema_family"]["mapped_report_norm_ids"] == [
        1269,
        1270,
        1271,
        1272,
        1277,
        1278,
        1279,
    ]


def test_hdb_five_axis_variant_and_land_rent_are_preserved() -> None:
    hdb = _trial(_result(), "HDB")
    vat = _mapping(hdb, "VAT")
    assert [item["axis_role"] for item in vat["values"]] == [
        "OPENING",
        "BUSINESS_COMBINATION_INCREASE",
        "PAYABLE_INCREASE",
        "PAID_DECREASE",
        "CLOSING",
    ]
    merger = vat["values"][1]
    assert merger["source_line_index"] == 28
    assert merger["normalized_value"] == 26_503
    assert hdb["verified_source_only_rows"] == [
        {
            **hdb["verified_source_only_rows"][0],
            "reason": "LAND_RENT_IS_NOT_IDENTICAL_TO_HOUSE_LAND_TAX_AND_HAS_NO_EXACT_SCHEMA_LEAF",
            "row_id": "SBO-001",
            "status": "UNRESOLVED_SCHEMA_SEMANTICS_SOURCE_ROW_RETAINED",
        }
    ]


def test_ctg_payable_receivable_net_variant_closes_twice() -> None:
    ctg = _trial(_result(), "CTG")
    assert len(ctg["verified_mappings"]) == 4
    assert len(ctg["verified_accounting_equations"]) == 8
    assert {item["name"] for item in ctg["verified_accounting_equations"]} == {
        "OPENING_PLUS_INCREASE_PLUS_PAYABLE_MINUS_PAID_EQUALS_CLOSING",
        "CLOSING_PAYABLE_PLUS_RECEIVABLE_EQUALS_CLOSING_NET",
    }
    assert [item["normalized_value"] for item in _mapping(ctg, "FAMILY_TOTAL")["values"][-3:]] == [
        3_190_608,
        -6_296,
        3_184_312,
    ]


def test_public_replay_rejects_coordinated_dash_promotion() -> None:
    forged = copy.deepcopy(_result())
    acb = _trial(forged, "ACB")
    dash = _mapping(acb, "HOUSE_LAND_TAX")["values"][0]
    dash["normalized_value"] = 1
    dash["source_numeric_challenger"] = "1"
    dash["source_numeric_challenger_status"] = "FORGED_NUMERIC_VALUE"
    forged["metrics"]["visible_dash_zero_count"] -= 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0095:result:" + builder.canonical_json_sha256_v1(material)
    with pytest.raises(
        builder.StateBudgetObligations8BankCodexVerifiedMappingV1Error,
        match="replay exactly",
    ):
        builder.validate_live_state_budget_obligations_8bank_codex_verified_mapping_v1(forged)
