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
    / "scripts/experiments/build_annual_2025_cash_equivalents_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_cash_equivalents_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def result() -> dict[str, object]:
    built = builder.build_live_annual_2025_cash_equivalents_8bank_codex_verified_mapping_v1()
    persisted = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())
    assert builder._base().same_typed_json_v1(built, persisted)
    return built


def _trial(result: dict[str, object], code: str) -> dict[str, object]:
    return next(item for item in result["trials"] if item["document_provenance"] == code)


def _mapping(trial: dict[str, object], role: str) -> dict[str, object]:
    return next(item for item in trial["verified_mappings"] if item["role"] == role)


def test_all_eight_annual_reports_have_one_unique_cash_equivalents_region(
    result: dict[str, object],
) -> None:
    assert result["result_id"] == builder.EXPECTED_RESULT_ID
    assert result["metrics"] == {
        "accounting_equation_verified_count": 18,
        "blank_optional_axis_count": 0,
        "detailed_note_not_present_document_count": 0,
        "document_count": 8,
        "document_unique_region_count": 8,
        "fresh_vietocr_numeric_disagreement_count": 0,
        "mapping_verified_count": 43,
        "open_source_row_count": 0,
        "q1_source_period_caveat_document_count": 0,
        "verified_value_cell_count": 86,
    }
    assert [trial["page_span"] for trial in result["trials"]] == list(
        builder._EXPECTED_PAGES.values()
    )
    assert all(
        trial["whole_document_uniqueness"]
        == {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
        for trial in result["trials"]
    )


def test_visible_securities_dashes_are_authenticated_zero_not_blank(
    result: dict[str, object],
) -> None:
    expected = {
        ("ACB", "CURRENT_PERIOD"),
        ("VPB", "COMPARATIVE_PERIOD"),
        ("HDB", "CURRENT_PERIOD"),
    }
    actual = set()
    for code, axis_role in expected:
        value = next(
            item
            for item in _mapping(_trial(result, code), "SECURITIES")["values"]
            if item["axis_role"] == axis_role
        )
        assert value["normalized_value"] == 0
        assert value["pixel_transcription"] == "-"
        assert value["source_numeric_challenger_status"] == (
            "VISIBLE_AUTHENTICATED_PIXEL_DASH_NOT_DETECTED_AS_SOURCE_LINE"
        )
        actual.add((code, axis_role))
    assert actual == expected


def test_bid_central_bank_synonym_and_interbank_children_close_exactly(
    result: dict[str, object],
) -> None:
    bid = _trial(result, "BID")
    central = _mapping(bid, "CENTRAL_BANK")
    assert central["label_evidence"][0]["pixel_transcription"] == (
        "Tiền gửi tại Ngân hàng Trung ương"
    )
    equations = {item["name"]: item for item in bid["verified_accounting_equations"]}
    assert {
        item["axis_role"]
        for item in bid["verified_accounting_equations"]
        if item["name"] == "INTERBANK_CHILDREN_EQUAL_INTERBANK_PARENT"
    } == {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"}
    assert all(item["computed_value"] == item["visible_total"] for item in equations.values())


def test_live_schema_binding_covers_the_complete_family(result: dict[str, object]) -> None:
    assert result["schema_family"]["mapped_report_norm_ids"] == list(range(1248, 1255))
    assert result["schema_family"]["family_root"]["display_order"] == 828
    assert result["schema_family"]["family_end_display_order"] == 834


def test_public_validator_rejects_coordinated_numeric_tamper(
    result: dict[str, object],
) -> None:
    forged = copy.deepcopy(result)
    forged["trials"][0]["verified_mappings"][0]["values"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + builder._base().canonical_json_sha256_v1(
        material
    )
    with pytest.raises(
        builder.Annual2025CashEquivalents8BankError, match="result identity drifted"
    ):
        builder.validate_annual_2025_cash_equivalents_8bank_codex_verified_mapping_replay_v1(forged)
