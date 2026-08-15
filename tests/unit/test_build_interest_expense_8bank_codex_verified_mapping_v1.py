from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_interest_expense_8bank_codex_verified_mapping_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_interest_expense_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _result() -> dict[str, object]:
    return json.loads((_ROOT / builder.RESULT_PATH).read_text())


def test_review_covers_the_unique_region_in_all_eight_documents() -> None:
    review = builder._review_blueprint()
    assert [document["bank_code"] for document in review["documents"]] == [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert [document["page_span"] for document in review["documents"]] == [
        [24, 24],
        [46, 46],
        [62, 62],
        [34, 34],
        [39, 39],
        [45, 45],
        [29, 29],
        [45, 45],
    ]
    assert review["documents"][-1]["presentation"] == ("LEADING_PARENT_TOTAL_BEFORE_CHILDREN")


def test_persisted_result_has_exact_verified_denominator() -> None:
    result = builder._validate_result(_result())
    assert result["metrics"] == {
        "accounting_equation_verified_count": 16,
        "document_count": 8,
        "document_unique_region_count": 8,
        "fresh_vietocr_numeric_disagreement_count": 1,
        "mapping_verified_count": 40,
        "open_source_row_count": 0,
        "q1_source_period_caveat_document_count": 1,
        "verified_value_cell_count": 80,
    }
    assert result["schema_family"]["mapped_report_norm_ids"] == [1151, 1152, 1153, 1154, 1156]
    assert result["schema_family"]["not_observed_report_norm_ids"] == [1155]


def test_mbb_vietocr_punctuation_error_is_not_numeric_truth() -> None:
    mbb = _result()["trials"][1]
    issued = next(
        mapping
        for mapping in mbb["verified_mappings"]
        if mapping["schema_binding"]["report_norm_id"] == 1154
    )
    comparative = next(
        value for value in issued["values"] if value["axis_role"] == "COMPARATIVE_PERIOD"
    )
    assert comparative["fresh_vietocr_numeric_proposal"] == "(3:975.549)"
    assert comparative["source_numeric_challenger"] == "(3.975.549)"
    assert comparative["normalized_value"] == -3_975_549
    assert comparative["fresh_vietocr_numeric_status"] == (
        "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
    )


def test_vcb_combined_deposit_and_borrowing_row_maps_to_borrowing() -> None:
    vcb = _result()["trials"][4]
    borrowing = next(
        mapping
        for mapping in vcb["verified_mappings"]
        if mapping["schema_binding"]["report_norm_id"] == 1153
    )
    assert borrowing["label_evidence"]["pixel_transcription"] == (
        "Trả lãi tiền gửi và vay các tổ chức tín dụng khác"
    )
    assert borrowing["role"] == "BORROWING_INTEREST"


def test_public_replay_rejects_coordinated_value_tamper() -> None:
    forged = copy.deepcopy(_result())
    forged["trials"][0]["verified_mappings"][0]["values"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0081:result:" + builder.canonical_json_sha256_v1(material)
    with pytest.raises(
        builder.InterestExpense8BankCodexVerifiedMappingV1Error,
        match="replay exactly",
    ):
        builder.validate_live_interest_expense_8bank_codex_verified_mapping_v1(forged)
