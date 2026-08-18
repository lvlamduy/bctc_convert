from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT / "scripts/experiments/"
    "build_annual_2025_trading_securities_activity_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_trading_securities_activity_8bank_codex_verified_mapping_v1",
    _PATH,
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)

_ORDER = ["ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB"]
_PAGES = [[68, 68], [73, 73], [70, 70], [50, 50], [59, 59], [58, 58], [56, 56], None]


def _persisted() -> dict[str, object]:
    return json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())


def _review() -> dict[str, object]:
    return json.loads((builder.PROJECT_ROOT / builder.REVIEW_PATH).read_text())


def _trial(code: str) -> dict[str, object]:
    return next(item for item in _persisted()["trials"] if item["document_provenance"] == code)


def test_review_covers_seven_unique_regions_and_one_bounded_absence() -> None:
    review = _review()
    assert review["scan_id"] == builder.EXPECTED_SCAN_ID
    assert [item["bank_code"] for item in review["documents"]] == _ORDER
    assert [item["page_span"] for item in review["documents"]] == _PAGES
    assert all(
        item["source_period"] == "2025-12-31"
        for item in review["documents"]
        if item["page_span"] is not None
    )
    absence = review["documents"][-1]["absence_evidence"]
    assert absence["complete_pdf_pages_scanned"] is True
    assert absence["source_scope_absence_only"] is True
    assert "investment" in absence["reason"]


def test_persisted_result_has_exact_denominators_and_schema_bindings() -> None:
    result = _persisted()
    assert result["metrics"] == builder._EXPECTED_METRICS
    assert [item["document_provenance"] for item in result["trials"]] == _ORDER
    assert [item["page_span"] for item in result["trials"]] == _PAGES
    for trial in result["trials"]:
        code = trial["document_provenance"]
        assert {
            row["schema_binding"]["report_norm_id"] for row in trial["verified_mappings"]
        } == builder._EXPECTED_REPORT_NORM_IDS[code]


def test_hdb_optional_provision_variant_closes_without_inventing_a_row() -> None:
    hdb = _trial("HDB")
    assert {row["role"] for row in hdb["verified_mappings"]} == {
        "NET_TRADING_SECURITIES",
        "INCOME_TRADING_SECURITIES",
        "EXPENSE_TRADING_SECURITIES",
    }
    assert all(
        item["equation"] == "INCOME_PLUS_EXPENSE_EQUALS_NET_TRADING_ACTIVITY"
        and item["term_report_norm_ids"] == [1189, 1190]
        for item in hdb["verified_accounting_equations"]
    )
    assert [item["computed_value"] for item in hdb["verified_accounting_equations"]] == [
        639_460,
        68_929,
    ]


def test_every_printed_provision_variant_closes_the_four_row_equation() -> None:
    for trial in _persisted()["trials"]:
        if trial["document_provenance"] in {"HDB", "VIB"}:
            continue
        assert {row["role"] for row in trial["verified_mappings"]} == {
            "NET_TRADING_SECURITIES",
            "INCOME_TRADING_SECURITIES",
            "EXPENSE_TRADING_SECURITIES",
            "PROVISION_TRADING_SECURITIES",
        }
        assert all(
            item["equation"] == "INCOME_PLUS_EXPENSE_PLUS_PROVISION_EQUALS_NET_TRADING_ACTIVITY"
            and item["term_report_norm_ids"] == [1189, 1190, 1191]
            for item in trial["verified_accounting_equations"]
        )


def test_all_54_values_match_the_independent_source_numeric_axis() -> None:
    values = [
        value
        for trial in _persisted()["trials"]
        for mapping in trial["verified_mappings"]
        for value in mapping["values"]
    ]
    assert len(values) == 54
    assert all(
        value["fresh_vietocr_numeric_status"] == "MATCHES_SOURCE_NUMERIC_CHALLENGER"
        and value["source_numeric_challenger_status"] == "MATCHED_VISIBLE_PIXEL_TRANSCRIPTION"
        for value in values
    )


def test_vib_is_absent_only_from_the_bound_report_and_not_relabelled() -> None:
    vib = _trial("VIB")
    assert vib["status"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT"
    assert vib["verified_mappings"] == []
    assert vib["verified_accounting_equations"] == []
    assert vib["absence_evidence"]["source_scope_absence_only"] is True
    assert (
        _persisted()["authority"]["investment_securities_activity_relabelled_as_trading_activity"]
        is False
    )


def test_exact_pins_reject_metric_or_optional_role_drift() -> None:
    tampered = copy.deepcopy(_persisted())
    tampered["metrics"]["mapping_verified_count"] += 1
    with pytest.raises(builder.Annual2025TradingSecuritiesActivity8BankError):
        builder._assert_result(tampered)

    tampered = copy.deepcopy(_persisted())
    hdb = next(item for item in tampered["trials"] if item["document_provenance"] == "HDB")
    hdb["verified_mappings"][0]["schema_binding"]["report_norm_id"] = 1191
    with pytest.raises(builder.Annual2025TradingSecuritiesActivity8BankError):
        builder._assert_result(tampered)


def test_persisted_result_exactly_live_replays() -> None:
    rebuilt = (
        builder.build_live_annual_2025_trading_securities_activity_8bank_codex_verified_mapping_v1()
    )
    assert rebuilt == _persisted()
    assert rebuilt["result_id"] == (
        "annual2025tsa8bcv1:result:af5fb729ce2fada04d6f759d4cc7b5ec13e6b23a28807ebee0740b77b4fcdbd8"
    )
