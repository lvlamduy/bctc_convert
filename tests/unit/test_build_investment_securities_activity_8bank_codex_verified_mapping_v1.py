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
    / "scripts/experiments/build_investment_securities_activity_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_investment_securities_activity_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _result() -> dict[str, object]:
    return json.loads((_ROOT / builder.RESULT_PATH).read_text())


def test_review_covers_seven_unique_regions_and_one_segment_control() -> None:
    documents = builder._review_blueprint()["documents"]
    assert [document["bank_code"] for document in documents] == [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert [document["page_span"] for document in documents] == [
        [25, 25],
        [47, 47],
        [63, 63],
        [35, 35],
        None,
        [46, 46],
        [29, 29],
        [46, 46],
    ]
    assert "segment-report" in documents[4]["absence_evidence"]["reason"]


def test_persisted_result_has_exact_verified_denominator() -> None:
    result = builder._validate_result(_result())
    assert result["metrics"] == {
        "accounting_equation_verified_count": 14,
        "authenticated_pixel_dash_zero_count": 4,
        "detailed_note_not_present_document_count": 1,
        "document_count": 8,
        "document_unique_region_count": 7,
        "fresh_vietocr_numeric_disagreement_count": 0,
        "mapping_verified_count": 28,
        "open_source_row_count": 0,
        "q1_source_period_caveat_document_count": 1,
        "verified_value_cell_count": 56,
    }


def test_optional_rows_follow_visible_source_without_forcing_one_shape() -> None:
    result = _result()
    by_bank = {trial["document_provenance"]: trial for trial in result["trials"]}
    assert {
        mapping["schema_binding"]["report_norm_id"]
        for mapping in by_bank["MBB"]["verified_mappings"]
    } == {1193, 1194, 1195, 1196, 6028}
    assert {
        mapping["schema_binding"]["report_norm_id"]
        for mapping in by_bank["VIB"]["verified_mappings"]
    } == {1193, 1194, 1195}
    assert result["schema_family"]["unobserved_optional_report_norm_ids"] == [1197]


def test_visible_dashes_are_zero_and_every_equation_closes() -> None:
    result = _result()
    dash_values = [
        value
        for trial in result["trials"]
        for mapping in trial["verified_mappings"]
        for value in mapping["values"]
        if value["source_line_index"] is None
    ]
    assert len(dash_values) == 4
    assert all(
        value["normalized_value"] == 0
        and value["pixel_transcription"] == "-"
        and value["source_numeric_challenger_status"]
        == "VISIBLE_AUTHENTICATED_PIXEL_DASH_NOT_DETECTED_AS_SOURCE_LINE"
        for value in dash_values
    )
    assert sum(len(trial["verified_accounting_equations"]) for trial in result["trials"]) == 14


def test_public_replay_rejects_coordinated_value_tamper() -> None:
    forged = copy.deepcopy(_result())
    forged["trials"][0]["verified_mappings"][0]["values"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0085:result:" + builder.canonical_json_sha256_v1(material)
    with pytest.raises(
        builder.InvestmentSecuritiesActivity8BankCodexVerifiedMappingV1Error,
        match="replay exactly",
    ):
        builder.validate_live_investment_securities_activity_8bank_codex_verified_mapping_v1(forged)
