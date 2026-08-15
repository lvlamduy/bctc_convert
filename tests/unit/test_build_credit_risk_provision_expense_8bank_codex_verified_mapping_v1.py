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
    / "scripts/experiments/build_credit_risk_provision_expense_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_credit_risk_provision_expense_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _result() -> dict[str, object]:
    return json.loads((_ROOT / builder.RESULT_PATH).read_text())


def test_review_distinguishes_three_detailed_notes_and_five_bounded_absences() -> None:
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
        None,
        [49, 49],
        [66, 66],
        None,
        None,
        None,
        None,
        [47, 47],
    ]


def test_persisted_result_has_exact_verified_denominator() -> None:
    result = builder._validate_result(_result())
    assert result["metrics"] == {
        "accounting_equation_verified_count": 8,
        "authenticated_pixel_dash_zero_count": 2,
        "detailed_note_not_present_document_count": 5,
        "document_count": 8,
        "document_unique_region_count": 3,
        "fresh_vietocr_numeric_disagreement_count": 2,
        "mapping_verified_count": 15,
        "open_source_row_count": 2,
        "q1_source_period_caveat_document_count": 1,
        "verified_value_cell_count": 30,
    }
    assert result["schema_family"]["mapped_report_norm_ids"] == [
        1221,
        1224,
        1225,
        1226,
        1227,
        1228,
        6031,
        6032,
        6033,
    ]


def test_visible_dashes_are_zero_without_silent_blank_inference() -> None:
    result = _result()
    mbb = result["trials"][1]
    other = next(item for item in mbb["verified_mappings"] if item["role"] == "OTHER_RISK")
    current = next(v for v in other["values"] if v["axis_role"] == "CURRENT_PERIOD")
    assert current["normalized_value"] == 0
    assert current["pixel_transcription"] == "-"
    assert current["source_line_index"] is None
    vpb = result["trials"][2]
    vamc = next(item for item in vpb["verified_mappings"] if item["role"] == "VAMC")
    current = next(v for v in vamc["values"] if v["axis_role"] == "CURRENT_PERIOD")
    assert current["fresh_vietocr_numeric_proposal"] == "1"
    assert current["source_numeric_challenger"] == "-"
    assert current["normalized_value"] == 0


def test_only_true_schema_gaps_remain_open() -> None:
    result = _result()
    assert [item["row_id"] for item in result["trials"][2]["verified_source_only_rows"]] == [
        "CRPE-001"
    ]
    assert [item["row_id"] for item in result["trials"][7]["verified_source_only_rows"]] == [
        "CRPE-002"
    ]
    assert result["trials"][2]["source_period_status"] == ("VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2")


def test_public_replay_rejects_coordinated_value_tamper() -> None:
    forged = copy.deepcopy(_result())
    forged["trials"][1]["verified_mappings"][0]["values"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0089:result:" + builder.canonical_json_sha256_v1(material)
    with pytest.raises(
        builder.CreditRiskProvisionExpense8BankCodexVerifiedMappingV1Error,
        match="replay exactly",
    ):
        builder.validate_live_credit_risk_provision_expense_8bank_codex_verified_mapping_v1(forged)
