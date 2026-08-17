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
    / "scripts/experiments/build_annual_2025_investment_property_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_investment_property_8bank_codex_verified_mapping_v1",
    _PATH,
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def live() -> dict[str, object]:
    return builder.build_live_annual_2025_investment_property_8bank_codex_verified_mapping_v1()


def test_two_unique_regions_and_six_bound_absences(live: dict[str, object]) -> None:
    assert live["metrics"] == {
        "accounting_equation_count": 27,
        "confirmed_bound_report_absence_count": 6,
        "controlled_aggregate_mapping_count": 5,
        "document_count": 8,
        "mapping_verified_count": 18,
        "open_review_item_count": 0,
        "verified_present_document_count": 2,
        "visible_dash_zero_mapping_count": 1,
    }
    assert [
        (trial["document_provenance"], trial.get("page_sequence"))
        for trial in live["trials"]
        if trial["mappings"]
    ] == [("ACB", 57), ("MBB", 61)]
    assert all(
        trial["disposition"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT"
        for trial in live["trials"][2:]
    )


def test_acb_sibling_tables_are_aggregated_once_and_close(live: dict[str, object]) -> None:
    acb = live["trials"][0]
    values = {
        mapping["report_norm_id"]: mapping["value"]["normalized_value"]
        for mapping in acb["mappings"]
    }
    assert values == {
        944: 177_005,
        948: 87_382,
        952: -114_695,
        955: 149_692,
        957: 0,
        958: 19,
        965: 19,
        5973: 177_005,
        5974: 149_673,
    }
    assert (
        sum(
            mapping["value"]["semantic_text_source"] == "CONTROLLED_SUM_OF_VISIBLE_SOURCE_CELLS"
            for mapping in acb["mappings"]
        )
        == 5
    )
    opening_depreciation = next(
        mapping for mapping in acb["mappings"] if mapping["report_norm_id"] == 957
    )
    assert opening_depreciation["value"]["normalized_pixel_transcription"] == "-"
    assert opening_depreciation["value"]["normalized_value"] == 0


def test_mbb_current_region_retains_2024_comparison_as_control(
    live: dict[str, object],
) -> None:
    mbb = live["trials"][1]
    values = {
        mapping["report_norm_id"]: mapping["value"]["normalized_value"]
        for mapping in mbb["mappings"]
    }
    assert values == {
        944: 260_415,
        6002: 4_971,
        6003: -10_260,
        955: 255_126,
        957: 26_300,
        6005: 6_145,
        965: 32_313,
        5973: 234_115,
        5974: 222_813,
    }
    assert mbb["source_period"] == "2025-12-31"
    assert mbb["comparative_control"]["source_period"] == "2024-12-31"


def test_all_equations_and_schema_bindings_are_exact(live: dict[str, object]) -> None:
    equations = [equation for trial in live["trials"] for equation in trial["equations"]]
    mappings = [mapping for trial in live["trials"] for mapping in trial["mappings"]]
    assert len(equations) == 27
    assert all(
        equation["status"] == "CORROBORATED_EXACT"
        and equation["computed_total"] == equation["visible_total"]
        for equation in equations
    )
    assert all(
        mapping["final_status"] == "VERIFIED_BY_CODEX"
        and mapping["schema_binding"]["report_norm_id"] == mapping["report_norm_id"]
        for mapping in mappings
    )


def test_exact_replay_rejects_coordinated_aggregate_rehash(
    live: dict[str, object],
) -> None:
    forged = copy.deepcopy(live)
    aggregate = forged["trials"][0]["mappings"][0]["value"]
    aggregate["normalized_value"] += 1
    base = builder._configure_base()
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + base.canonical_json_sha256_v1(material)

    with pytest.raises(builder.Annual2025InvestmentProperty8BankError):
        builder.validate_annual_2025_investment_property_8bank_codex_verified_mapping_replay_v1(
            forged
        )


def test_persisted_review_and_result_equal_live_bytes(live: dict[str, object]) -> None:
    persisted_review = json.loads((builder.PROJECT_ROOT / builder.REVIEW_PATH).read_text("utf-8"))
    persisted_result = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text("utf-8"))

    assert (
        persisted_review
        == builder.build_annual_2025_investment_property_pixel_review_blueprint_v1()
    )
    assert persisted_result == live
