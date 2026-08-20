from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1

ROOT = Path(__file__).resolve().parents[2]
PATH = (
    ROOT / "scripts/experiments/build_annual_2025_exchange_rate_8bank_codex_verified_mapping_v1.py"
)
SPEC = importlib.util.spec_from_file_location("annual_2025_exchange_rate_mapping_test", PATH)
assert SPEC is not None and SPEC.loader is not None
builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def live() -> dict:
    return builder.build_live_annual_2025_exchange_rate_8bank_codex_verified_mapping_v1()


def _trial(result: dict, bank: str) -> dict:
    return next(item for item in result["trials"] if item["document_provenance"] == bank)


def test_six_unique_regions_and_two_bounded_absences(live: dict) -> None:
    assert live["metrics"] == {
        "bounded_detailed_table_absence_count": 2,
        "document_count": 8,
        "document_unique_region_count": 6,
        "gemma4_bounded_numeric_conflict_rescue_count": 1,
        "mapping_verified_count": 55,
        "out_of_schema_source_row_count": 19,
        "relative_period_header_document_count": 1,
        "verified_source_value_cell_count": 148,
        "verified_value_cell_count": 110,
    }
    assert [trial["document_provenance"] for trial in live["trials"]] == list(
        builder.EXPECTED_DOCUMENT_ORDER
    )
    assert {
        trial["document_provenance"] for trial in live["trials"] if trial["selected_region"] is None
    } == {"ACB", "VCB"}


def test_relative_end_start_year_headers_bind_hdb_document_period(live: dict) -> None:
    hdb = _trial(live, "HDB")
    assert hdb["selected_region"]["page_sequence"] == 69
    assert hdb["period_binding_status"] == (
        "DOCUMENT_PERIOD_CONTEXT_PLUS_RELATIVE_END_START_YEAR_HEADERS"
    )
    assert hdb["selected_region"]["current_period"] == [
        {"day": 31, "line_index": 9, "month": 12, "raw_text": "Số cuối năm", "year": 2025}
    ]
    assert hdb["selected_region"]["comparative_period"] == [
        {"day": 31, "line_index": 10, "month": 12, "raw_text": "Số đầu năm", "year": 2024}
    ]


def test_only_declared_schema_currency_gaps_remain_open(live: dict) -> None:
    gaps = {
        trial["document_provenance"]: {row["code"] for row in trial["verified_source_only_rows"]}
        for trial in live["trials"]
        if trial["verified_source_only_rows"]
    }
    assert gaps == {
        "VPB": {"CNY", "DKK", "NZD", "XAU"},
        "HDB": {"CNY", "HKD", "KRW", "NZD"},
        "CTG": {"CNY", "DKK", "HKD", "KRW", "LAK", "NOK", "NZD"},
        "VIB": {"DKK", "HKD", "NOK", "XAU"},
    }


def test_one_bounded_gemma_rescue_does_not_replace_numeric_authority(live: dict) -> None:
    rescues = [
        value
        for trial in live["trials"]
        for group in (trial["verified_mappings"], trial["verified_source_only_rows"])
        for row in group
        for value in row["values"]
        if value["gemma4_text_rescue"] is not None
    ]
    assert len(rescues) == 1
    value = rescues[0]
    assert value["axis"] == "COMPARATIVE_PERIOD"
    assert value["normalized_decimal"] == "14362.00"
    assert value["fresh_vietocr_numeric_proposal"] == "14.382"
    assert value["source_numeric_challenger"] == "14.362"
    assert value["gemma4_text_rescue"]["gemma4_text"] == "14.362"
    assert live["authority"]["gemma4_used_as_numeric_truth"] is False


def test_persisted_result_and_review_equal_live_rebuild(live: dict) -> None:
    assert (ROOT / builder.RESULT_PATH).read_bytes() == canonical_json_bytes_v1(live) + b"\n"
    assert (ROOT / builder.REVIEW_PATH).read_bytes() == (
        canonical_json_bytes_v1(builder._review(live)) + b"\n"
    )


def test_coordinated_rehash_cannot_pass_public_replay(
    live: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    forged = copy.deepcopy(live)
    forged["trials"][1]["verified_mappings"][0]["values"][0]["normalized_value_cents"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + builder.canonical_json_sha256_v1(material)
    monkeypatch.setattr(
        builder,
        "build_live_annual_2025_exchange_rate_8bank_codex_verified_mapping_v1",
        lambda: live,
    )
    with pytest.raises(Exception, match="replay exactly"):
        builder.validate_annual_2025_exchange_rate_8bank_codex_verified_mapping_replay_v1(forged)
