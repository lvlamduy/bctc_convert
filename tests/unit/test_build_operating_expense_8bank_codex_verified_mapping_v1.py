from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_operating_expense_8bank_codex_verified_mapping_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_operating_expense_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _result() -> dict[str, object]:
    return json.loads((_ROOT / builder.RESULT_PATH).read_text())


def test_review_covers_one_unique_region_in_each_document() -> None:
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
        [25, 25],
        [48, 48],
        [65, 65],
        [35, 35],
        [40, 40],
        [47, 47],
        [30, 30],
        [46, 46],
    ]


def test_persisted_result_has_exact_verified_denominator() -> None:
    result = builder._validate_result(_result())
    assert result["metrics"] == {
        "accounting_equation_verified_count": 30,
        "document_count": 8,
        "document_unique_region_count": 8,
        "fresh_vietocr_numeric_disagreement_count": 1,
        "mapping_verified_count": 99,
        "open_source_row_count": 4,
        "q1_source_period_caveat_document_count": 1,
        "verified_value_cell_count": 198,
    }
    assert result["schema_family"]["mapped_report_norm_ids"] == list(range(1205, 1221))


def test_vcb_missing_vietocr_digit_is_vetoed_by_pixel_and_source_axis() -> None:
    vcb = _result()["trials"][4]
    asset = next(mapping for mapping in vcb["verified_mappings"] if mapping["role"] == "ASSET")
    current = next(value for value in asset["values"] if value["axis_role"] == "CURRENT_PERIOD")
    assert current["fresh_vietocr_numeric_proposal"] == "1.771.726"
    assert current["source_numeric_challenger"] == "1.777.726"
    assert current["pixel_transcription"] == "1.777.726"
    assert current["normalized_value"] == 1_777_726
    assert current["fresh_vietocr_numeric_status"] == ("DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER")


def test_schema_gaps_are_retained_while_other_rows_verify() -> None:
    result = _result()
    vpb = result["trials"][2]
    ctg = result["trials"][5]
    assert [row["row_id"] for row in vpb["verified_source_only_rows"]] == [
        "OE-001",
        "OE-002",
        "OE-003",
    ]
    assert [row["row_id"] for row in ctg["verified_source_only_rows"]] == ["OE-004"]
    assert vpb["status"] == ("VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT_AND_UNRESOLVED_SCHEMA_ROWS")
    assert ctg["status"] == "VERIFIED_BY_CODEX_WITH_UNRESOLVED_SCHEMA_ROWS"


def test_bid_unit_inheritance_is_explicit() -> None:
    bid = _result()["trials"][6]
    assert bid["unit_authority"] == "DOCUMENT_SECTION_MILLION_VND_INHERITED_AFTER_BOUND_TABLE"
    assert bid["unit_evidence"][0]["pixel_transcription"] == "Đơn vị: Triệu VND"


def test_public_replay_rejects_coordinated_value_tamper() -> None:
    forged = copy.deepcopy(_result())
    forged["trials"][0]["verified_mappings"][0]["values"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0088:result:" + builder.canonical_json_sha256_v1(material)
    with pytest.raises(
        builder.OperatingExpense8BankCodexVerifiedMappingV1Error,
        match="replay exactly",
    ):
        builder.validate_live_operating_expense_8bank_codex_verified_mapping_v1(forged)
