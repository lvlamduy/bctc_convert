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
    / "scripts/experiments/build_trading_securities_activity_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_trading_securities_activity_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def _result() -> dict[str, object]:
    return json.loads((_ROOT / builder.RESULT_PATH).read_text())


def test_review_covers_seven_unique_regions_and_one_distinct_family_control() -> None:
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
        [24, 24],
        [47, 47],
        [63, 63],
        [34, 34],
        [39, 39],
        [45, 45],
        [29, 29],
        None,
    ]
    assert "investment-securities" in documents[-1]["absence_evidence"]["reason"]


def test_persisted_result_has_exact_verified_denominator() -> None:
    result = builder._validate_result(_result())
    assert result["metrics"] == {
        "accounting_equation_verified_count": 14,
        "authenticated_pixel_dash_zero_count": 1,
        "detailed_note_not_present_document_count": 1,
        "document_count": 8,
        "document_unique_region_count": 7,
        "fresh_vietocr_numeric_disagreement_count": 0,
        "mapping_verified_count": 28,
        "open_source_row_count": 0,
        "q1_source_period_caveat_document_count": 1,
        "source_label_caveat_mapping_count": 1,
        "verified_value_cell_count": 56,
    }


def test_every_present_bank_maps_only_the_four_observed_schema_rows() -> None:
    for trial in _result()["trials"][:-1]:
        assert {
            mapping["schema_binding"]["report_norm_id"] for mapping in trial["verified_mappings"]
        } == {1188, 1189, 1190, 1191}
    assert _result()["schema_family"]["unobserved_optional_report_norm_ids"] == [1192]


def test_hdb_visible_dash_and_source_label_caveat_are_preserved() -> None:
    hdb = next(trial for trial in _result()["trials"] if trial["document_provenance"] == "HDB")
    provision = next(
        mapping
        for mapping in hdb["verified_mappings"]
        if mapping["role"] == "PROVISION_TRADING_SECURITIES"
    )
    comparative = next(
        value for value in provision["values"] if value["axis_role"] == "COMPARATIVE_PERIOD"
    )
    assert hdb["source_label_caveat"] is not None
    assert "investment securities" in hdb["source_label_caveat"]
    assert comparative["normalized_value"] == 0
    assert comparative["pixel_transcription"] == "-"
    assert comparative["source_numeric_challenger_status"] == (
        "VISIBLE_AUTHENTICATED_PIXEL_DASH_NOT_DETECTED_AS_SOURCE_LINE"
    )
    assert [equation["computed_value"] for equation in hdb["verified_accounting_equations"]] == [
        -63114,
        630635,
    ]


def test_every_non_dash_value_matches_the_independent_numeric_axis() -> None:
    values = [
        value
        for trial in _result()["trials"]
        for mapping in trial["verified_mappings"]
        for value in mapping["values"]
    ]
    assert len(values) == 56
    lines = [value for value in values if value["source_line_index"] is not None]
    assert len(lines) == 55
    assert all(
        value["fresh_vietocr_numeric_status"] == "MATCHES_SOURCE_NUMERIC_CHALLENGER"
        and value["source_numeric_challenger_status"] == "MATCHED_VISIBLE_PIXEL_TRANSCRIPTION"
        for value in lines
    )


def test_public_replay_rejects_coordinated_value_tamper() -> None:
    forged = copy.deepcopy(_result())
    forged["trials"][0]["verified_mappings"][0]["values"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "e0084:result:" + builder.canonical_json_sha256_v1(material)
    with pytest.raises(
        builder.TradingSecuritiesActivity8BankCodexVerifiedMappingV1Error,
        match="replay exactly",
    ):
        builder.validate_live_trading_securities_activity_8bank_codex_verified_mapping_v1(forged)
