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
    "build_annual_2025_capital_contribution_dividend_income_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_capital_contribution_dividend_income_8bank_codex_verified_mapping_v1",
    _PATH,
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def result() -> dict[str, object]:
    built = builder.build_live_annual_2025_capital_contribution_dividend_income_8bank_codex_verified_mapping_v1()
    persisted = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())
    assert builder.same_typed_json_v1(built, persisted)
    return built


def test_exact_annual_denominator_mapping_and_equation_closure(
    result: dict[str, object],
) -> None:
    assert result["metrics"] == builder._EXPECTED_METRICS
    assert [trial["status"] for trial in result["trials"]] == [
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX",
        "VERIFIED_BY_CODEX_WITH_SOURCE_SCHEMA_GAPS",
        "VERIFIED_BY_CODEX",
        "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT",
    ]
    assert [trial["page_span"] for trial in result["trials"]] == [
        [69, 69],
        [74, 74],
        [71, 71],
        [51, 51],
        [60, 60],
        [59, 59],
        [56, 56],
        None,
    ]


def test_four_visible_dashes_are_authenticated_and_normalized_to_zero(
    result: dict[str, object],
) -> None:
    dashes = [
        value
        for trial in result["trials"]
        for mapping in trial["verified_mappings"]
        for value in mapping["values"]
        if value.get("pixel_transcription") == "-"
    ]
    assert len(dashes) == 4
    assert all(value["normalized_value"] == 0 for value in dashes)
    assert all(
        value["source_numeric_challenger_status"]
        == "VISIBLE_AUTHENTICATED_PIXEL_DASH_NOT_DETECTED_AS_SOURCE_LINE"
        for value in dashes
    )


def test_ctg_combined_securities_row_is_source_only_and_closes_parent(
    result: dict[str, object],
) -> None:
    ctg = next(trial for trial in result["trials"] if trial["document_provenance"] == "CTG")
    assert len(ctg["verified_source_only_rows"]) == 1
    row = ctg["verified_source_only_rows"][0]
    assert row["gap_id"] == "CCDI-CTG-001"
    assert row["report_norm_id"] is None
    assert [value["normalized_value"] for value in row["values"]] == [13284, 15823]
    equations = [
        item
        for item in ctg["verified_accounting_equations"]
        if item["equation"] == "COMBINED_SECURITIES_AND_LONG_TERM_EQUAL_DIRECT_DIVIDEND"
    ]
    assert len(equations) == 2
    assert all(
        item["source_only_term_roles"] == ["COMBINED_EQUITY_SECURITIES_DIVIDEND_SOURCE_ONLY"]
        for item in equations
    )


def test_vib_statement_aggregate_is_not_relabelled_as_detailed_note(
    result: dict[str, object],
) -> None:
    vib = next(trial for trial in result["trials"] if trial["document_provenance"] == "VIB")
    assert vib["whole_document_uniqueness"] == {
        "complete_region_count": 0,
        "status": "NOT_UNIQUE_FULL_MATCH",
    }
    assert vib["absence_evidence"]["negative_control_pages"] == [11]
    assert vib["verified_mappings"] == []


def test_public_validator_rejects_coordinated_result_tamper(
    result: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    forged = copy.deepcopy(result)
    forged["trials"][0]["verified_mappings"][0]["values"][0]["normalized_value"] += 1
    monkeypatch.setattr(
        builder,
        "build_live_annual_2025_capital_contribution_dividend_income_8bank_codex_verified_mapping_v1",
        lambda: result,
    )
    with pytest.raises(
        builder.Annual2025CapitalContributionDividendIncome8BankError,
        match="does not replay exactly",
    ):
        builder.validate_live_annual_2025_capital_contribution_dividend_income_8bank_codex_verified_mapping_v1(
            forged
        )
