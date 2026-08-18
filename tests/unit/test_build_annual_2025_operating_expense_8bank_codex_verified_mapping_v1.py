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
    / "scripts/experiments/build_annual_2025_operating_expense_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_operating_expense_8bank_codex_verified_mapping_v1",
    _PATH,
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def result() -> dict[str, object]:
    built = builder.build_live_annual_2025_operating_expense_8bank_codex_verified_mapping_v1()
    persisted = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())
    assert builder.same_typed_json_v1(built, persisted)
    return built


def test_exact_annual_denominator_and_unique_pages(result: dict[str, object]) -> None:
    assert result["metrics"] == builder._EXPECTED_METRICS
    assert [trial["document_provenance"] for trial in result["trials"]] == list(
        builder.EXPECTED_DOCUMENT_ORDER
    )
    assert [trial["page_span"] for trial in result["trials"]] == list(
        builder._EXPECTED_PAGES.values()
    )
    assert [len(trial["verified_mappings"]) for trial in result["trials"]] == list(
        builder._EXPECTED_MAPPING_COUNTS.values()
    )
    assert [len(trial["verified_source_only_rows"]) for trial in result["trials"]] == list(
        builder._EXPECTED_SOURCE_ONLY_COUNTS.values()
    )
    assert all(
        trial["whole_document_uniqueness"]
        == {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
        for trial in result["trials"]
    )


def test_source_only_rows_are_retained_not_forced_into_schema(
    result: dict[str, object],
) -> None:
    rows = [row for trial in result["trials"] for row in trial["verified_source_only_rows"]]
    assert [row["row_id"] for row in rows] == [
        f"OE-A2025-{ordinal:03d}" for ordinal in range(1, 15)
    ]
    assert all(row["status"] == "UNRESOLVED_SCHEMA_GAP_SOURCE_ROW_RETAINED" for row in rows)
    assert sum(len(row["values"]) for row in rows) == 28


def test_source_numeric_challenger_overrides_four_fresh_vietocr_digit_errors(
    result: dict[str, object],
) -> None:
    disagreements = [
        (
            trial["document_provenance"],
            mapping["role"],
            value["axis_role"],
            value["pixel_transcription"],
            value["fresh_vietocr_numeric_proposal"],
            value["normalized_value"],
        )
        for trial in result["trials"]
        for collection in (
            trial["verified_mappings"],
            trial["verified_source_only_rows"],
        )
        for mapping in collection
        for value in mapping["values"]
        if value["fresh_vietocr_numeric_status"] == "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
    ]
    assert disagreements == [
        ("HDB", "TOTAL", "COMPARATIVE_PERIOD", "11.980.755", "11.960.755", 11980755),
        ("CTG", "PAYROLL", "CURRENT_PERIOD", "1.127.165", "7.127.165", 1127165),
        ("CTG", "BENEFIT", "CURRENT_PERIOD", "15.588", "75.588", 15588),
        ("VIB", "ADMIN", "COMPARATIVE_PERIOD", "804.696", "804 696", 804696),
    ]


def test_all_printed_accounting_equations_close_and_dash_is_zero(
    result: dict[str, object],
) -> None:
    equations = [
        equation
        for trial in result["trials"]
        for equation in trial["verified_accounting_equations"]
    ]
    assert len(equations) == 42
    assert all(
        equation["status"] == "VERIFIED_EXACT"
        and equation["computed_value"] == equation["visible_total"]
        for equation in equations
    )
    vcb = next(trial for trial in result["trials"] if trial["document_provenance"] == "VCB")
    provision = next(
        mapping for mapping in vcb["verified_mappings"] if mapping["role"] == "LONG_TERM_PROVISION"
    )
    current = next(value for value in provision["values"] if value["axis_role"] == "CURRENT_PERIOD")
    assert current["pixel_transcription"] == "-"
    assert current["normalized_value"] == 0


def test_schema_bindings_use_live_1205_1220_family_positions(
    result: dict[str, object],
) -> None:
    bindings = {
        mapping["schema_binding"]["report_norm_id"]: mapping["schema_binding"]
        for trial in result["trials"]
        for mapping in trial["verified_mappings"]
    }
    assert bindings[1205]["display_order"] == 765
    assert bindings[1220]["display_order"] == 780
    assert all(
        bindings[report_norm_id]["schema_parent_report_norm_id"] == 1205
        for report_norm_id in bindings
        if report_norm_id != 1205
    )


def test_public_validator_rejects_coordinated_result_tamper(
    result: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    forged = copy.deepcopy(result)
    forged["trials"][0]["verified_mappings"][0]["values"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + builder.base.canonical_json_sha256_v1(material)
    monkeypatch.setattr(
        builder,
        "build_live_annual_2025_operating_expense_8bank_codex_verified_mapping_v1",
        lambda: result,
    )
    with pytest.raises(
        builder.Annual2025OperatingExpense8BankError,
        match="does not replay exactly",
    ):
        builder.validate_live_annual_2025_operating_expense_8bank_codex_verified_mapping_v1(forged)
