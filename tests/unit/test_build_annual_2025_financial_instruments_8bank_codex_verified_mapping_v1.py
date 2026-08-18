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
    "build_annual_2025_financial_instruments_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_financial_instruments_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def result() -> dict[str, object]:
    built = builder.build_live_annual_2025_financial_instruments_8bank_codex_verified_mapping_v1()
    persisted = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())
    assert builder._base().same_typed_json_v1(built, persisted)
    return built


def _trial(result: dict[str, object], code: str) -> dict[str, object]:
    return next(item for item in result["trials"] if item["document_provenance"] == code)


def test_two_unique_regions_six_bounded_absences_and_exact_schema_union(
    result: dict[str, object],
) -> None:
    assert result["result_id"] == builder.EXPECTED_RESULT_ID
    assert result["metrics"] == {
        "accounting_equation_verified_count": 9,
        "authenticated_pixel_dash_zero_count": 0,
        "bound_report_detailed_table_absence_count": 6,
        "document_count": 8,
        "document_unique_region_count": 2,
        "mapping_verified_count": 41,
        "open_fair_value_group_count": 2,
        "q1_source_period_caveat_document_count": 0,
        "source_only_control_row_count": 3,
        "verified_value_cell_count": 35,
    }
    assert [trial["page_span"] for trial in result["trials"]] == [
        None,
        None,
        [94, 94],
        None,
        [73, 74],
        None,
        None,
        None,
    ]
    assert result["schema_family"]["mapped_report_norm_ids"] == [
        1305,
        1306,
        1307,
        1308,
        1309,
        1310,
        1311,
        1312,
        1313,
        1314,
        1315,
        1318,
        1319,
        1320,
        1321,
        1322,
        1323,
        1324,
        1325,
        1326,
        1328,
        1329,
        1331,
        1332,
    ]


def test_landscape_tables_use_upright_canonical_geometry_and_exact_annual_period(
    result: dict[str, object],
) -> None:
    assert result["authority"]["landscape_page_coordinates_kept_upright_and_canonical"] is True
    for code in ("VPB", "VCB"):
        trial = _trial(result, code)
        assert trial["source_period"] == "2025-12-31"
        assert (
            trial["source_period_status"]
            == "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
        )
        assert trial["whole_document_uniqueness"] == {
            "complete_region_count": 1,
            "status": "UNIQUE_FULL_MATCH",
        }


def test_visible_book_totals_and_numeric_fair_values_close(result: dict[str, object]) -> None:
    for code in ("VPB", "VCB"):
        trial = _trial(result, code)
        assert all(
            equation["computed_value"] == equation["visible_value"]
            for equation in trial["verified_accounting_equations"]
        )
    assert {
        equation["name"] for equation in _trial(result, "VPB")["verified_accounting_equations"]
    } == {
        "VISIBLE_BOOK_ASSET_ROWS_EQUAL_TOTAL_FINANCIAL_ASSETS",
        "VISIBLE_BOOK_LIABILITY_ROWS_EQUAL_TOTAL_FINANCIAL_LIABILITIES",
        "EXPLICIT_CASH_FAIR_VALUE_EQUALS_CASH_CARRYING_VALUE",
        "ONLY_EXPLICIT_NUMERIC_FAIR_VALUE_EQUALS_CASH_FAIR_VALUE",
    }


def test_unavailable_fair_values_remain_open_not_zero(result: dict[str, object]) -> None:
    for code in ("VPB", "VCB"):
        rows = [
            row for row in _trial(result, code)["verified_source_only_rows"] if row["open_mapping"]
        ]
        assert len(rows) == 1
        assert rows[0]["status"] == "OPEN_UNAVAILABLE_FAIR_VALUE_NOT_ZERO"
        assert rows[0]["values"] == []
        assert rows[0]["affected_source_labels"]


def test_six_absences_do_not_promote_risk_or_derivative_tables(
    result: dict[str, object],
) -> None:
    for code in ("ACB", "MBB", "HDB", "CTG", "BID", "VIB"):
        trial = _trial(result, code)
        assert trial["status"] == "CONFIRMED_DETAILED_TABLE_NOT_PRESENT_IN_BOUND_REPORT"
        assert trial["absence_evidence"]["complete_pdf_pages_scanned"] is True
        assert trial["absence_evidence"]["source_scope_absence_only"] is True
        assert trial["verified_mappings"] == []


def test_public_replay_rejects_coordinated_asterisk_promotion(
    result: dict[str, object],
) -> None:
    forged = copy.deepcopy(result)
    row = next(
        row for row in _trial(forged, "VPB")["verified_source_only_rows"] if row["open_mapping"]
    )
    row["open_mapping"] = False
    row["status"] = "VERIFIED_SOURCE_ONLY_ACCOUNTING_CONTROL"
    forged["metrics"]["open_fair_value_group_count"] -= 1
    forged["metrics"]["source_only_control_row_count"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + builder._base().canonical_json_sha256_v1(
        material
    )
    with pytest.raises(
        builder.Annual2025FinancialInstruments8BankError,
        match="replay exactly",
    ):
        builder.validate_annual_2025_financial_instruments_8bank_codex_verified_mapping_replay_v1(
            forged
        )
