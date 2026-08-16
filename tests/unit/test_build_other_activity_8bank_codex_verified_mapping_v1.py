from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_other_activity_8bank_codex_verified_mapping_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_other_activity_8bank_codex_verified_mapping_v1", _PATH
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
        [47, 47],
        [64, 64],
        None,
        None,
        None,
        None,
        [46, 46],
    ]


def test_persisted_result_has_exact_verified_denominator() -> None:
    result = builder._validate_result(_result())
    assert result["metrics"] == {
        "accounting_equation_verified_count": 14,
        "authenticated_pixel_dash_zero_count": 0,
        "detailed_note_not_present_document_count": 5,
        "document_count": 8,
        "document_unique_region_count": 3,
        "fresh_vietocr_numeric_disagreement_count": 0,
        "mapping_verified_count": 23,
        "open_source_row_count": 1,
        "q1_source_period_caveat_document_count": 1,
        "verified_value_cell_count": 46,
    }
    assert result["schema_family"]["mapped_report_norm_ids"] == [
        1229,
        1231,
        1232,
        1234,
        1237,
        1239,
        1240,
        1241,
        1242,
        1246,
        6029,
        6030,
    ]


def test_two_asset_disposal_rows_are_controlled_sum_not_silent_drop() -> None:
    result = _result()
    vpb = result["trials"][2]
    disposal = next(
        item for item in vpb["verified_mappings"] if item["role"] == "INCOME_ASSET_DISPOSAL"
    )
    current = next(v for v in disposal["values"] if v["axis_role"] == "CURRENT_PERIOD")
    comparative = next(v for v in disposal["values"] if v["axis_role"] == "COMPARATIVE_PERIOD")
    assert current["normalized_value"] == 8_020
    assert comparative["normalized_value"] == 45_745
    assert current["source_line_index"] is None
    assert len(current["component_evidence"]) == 2
    assert current["source_numeric_challenger_status"] == (
        "CONTROLLED_SUM_OF_AUTHENTICATED_SOURCE_NUMERIC_LINES"
    )


def test_only_true_schema_gaps_remain_open() -> None:
    result = _result()
    assert [item["row_id"] for item in result["trials"][2]["verified_source_only_rows"]] == [
        "OACT-001"
    ]
    assert result["trials"][7]["verified_source_only_rows"] == []
    assert result["trials"][2]["source_period_status"] == ("VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2")


def test_public_replay_rejects_coordinated_value_tamper() -> None:
    forged = copy.deepcopy(_result())
    forged["trials"][1]["verified_mappings"][0]["values"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0090:result:" + builder.canonical_json_sha256_v1(material)
    with pytest.raises(
        builder.OtherActivity8BankCodexVerifiedMappingV1Error,
        match="replay exactly",
    ):
        builder.validate_live_other_activity_8bank_codex_verified_mapping_v1(forged)
