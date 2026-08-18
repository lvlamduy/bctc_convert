from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT / "scripts/experiments/build_annual_2025_income_tax_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_income_tax_8bank_codex_verified_mapping_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def result() -> dict[str, object]:
    built = builder.build_live_annual_2025_income_tax_8bank_codex_verified_mapping_v1()
    persisted = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())
    assert builder._base().same_typed_json_v1(built, persisted)
    return built


def test_all_eight_annual_reports_have_one_unique_income_tax_region(
    result: dict[str, object],
) -> None:
    assert result["result_id"] == builder.EXPECTED_RESULT_ID
    assert result["metrics"] == {
        "accounting_equation_verified_count": 32,
        "detailed_note_not_present_document_count": 0,
        "document_count": 8,
        "document_unique_region_count": 8,
        "fresh_vietocr_numeric_disagreement_count": 2,
        "mapping_verified_count": 61,
        "open_source_row_count": 7,
        "q1_source_period_caveat_document_count": 0,
        "verified_value_cell_count": 120,
        "visible_source_dash_zero_component_count": 0,
    }
    assert [trial["page_span"] for trial in result["trials"]] == list(
        builder._EXPECTED_PAGES.values()
    )
    assert all(
        trial["whole_document_uniqueness"]
        == {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
        and trial["source_period_status"]
        == "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
        for trial in result["trials"]
    )


def test_every_accounting_equation_closes_exactly(result: dict[str, object]) -> None:
    equations = [
        equation
        for trial in result["trials"]
        for equation in trial["verified_accounting_equations"]
    ]
    assert len(equations) == 32
    assert all(
        equation["status"] == "VERIFIED_EXACT"
        and equation["computed_value"] == equation["visible_total"]
        for equation in equations
    )


def test_malformed_vietocr_numbers_are_retained_but_not_numeric_truth(
    result: dict[str, object],
) -> None:
    expected = {
        "CTG": ("(20.539) + (891.368) + (370.109) + (161.384) + 188.471", -1_254_929),
        "VIB": ("(3.746) + 2.401", -1_345),
    }
    for code, (challenger, normalized) in expected.items():
        trial = next(item for item in result["trials"] if item["document_provenance"] == code)
        mapping = next(
            item for item in trial["verified_mappings"] if item["role"] == "NON_TAXABLE_AGGREGATE"
        )
        value = next(
            item for item in mapping["values"] if item["axis_role"] == "COMPARATIVE_PERIOD"
        )
        assert value["fresh_vietocr_numeric_proposal"] is None
        assert value["fresh_vietocr_numeric_status"] == "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
        assert value["source_numeric_challenger"] == challenger
        assert value["normalized_value"] == normalized


def test_visible_blank_comparatives_are_not_coerced_to_zero(result: dict[str, object]) -> None:
    expected = {
        ("MBB", "DIVESTMENT_CURRENT_TAX"),
        ("VPB", "OTHER_PAYABLE_ADJUSTMENT"),
    }
    found = set()
    for trial in result["trials"]:
        for row in trial["verified_source_only_rows"]:
            key = (trial["document_provenance"], row["role"])
            if key in expected:
                found.add(key)
                assert row["blank_axes"] == ["COMPARATIVE_PERIOD"]
                assert [item["axis_role"] for item in row["values"]] == ["CURRENT_PERIOD"]
    assert found == expected
    for code in ("VCB", "CTG"):
        trial = next(item for item in result["trials"] if item["document_provenance"] == code)
        foreign = next(
            item for item in trial["verified_mappings"] if item["role"] == "FOREIGN_BRANCH_TAX"
        )
        assert [item["axis_role"] for item in foreign["values"]] == ["CURRENT_PERIOD"]


def test_schema_binding_uses_current_live_family_positions(result: dict[str, object]) -> None:
    bindings = {
        mapping["schema_binding"]["report_norm_id"]: mapping["schema_binding"]
        for trial in result["trials"]
        for mapping in trial["verified_mappings"]
    }
    assert bindings[5723]["display_order"] == 812
    assert bindings[5728]["display_order"] == 817
    assert bindings[5735]["display_order"] == 824
    assert result["schema_family"]["family_end_display_order"] == 826


def test_public_validator_rejects_coordinated_numeric_tamper(
    result: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    forged = copy.deepcopy(result)
    forged["trials"][0]["verified_mappings"][0]["values"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + builder._base().canonical_json_sha256_v1(
        material
    )
    monkeypatch.setattr(
        builder,
        "build_live_annual_2025_income_tax_8bank_codex_verified_mapping_v1",
        lambda: result,
    )
    with pytest.raises(builder.Annual2025IncomeTax8BankError, match="does not replay exactly"):
        builder.validate_annual_2025_income_tax_8bank_codex_verified_mapping_replay_v1(forged)
