from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT
    / "scripts/experiments/build_annual_2025_other_payables_liabilities_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location("annual_2025_other_payables_builder", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def test_review_covers_one_unique_annual_region_per_bank() -> None:
    review = builder.build_annual_2025_other_payables_liabilities_pixel_review_blueprint_v1()
    assert [item["bank_code"] for item in review["documents"]] == [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert [item["page_span"] for item in review["documents"]] == [
        [64, 64],
        [67, 67],
        [63, 63],
        [47, 47],
        [54, 54],
        [54, 54],
        [52, 52],
        [48, 48],
    ]
    assert all(item["source_period"] == "2025-12-31" for item in review["documents"])
    assert all(item["disposition"] == "VERIFIED_BY_CODEX" for item in review["documents"])


def test_all_source_rows_without_dedicated_leaves_are_bounded_to_other() -> None:
    review = builder.build_annual_2025_other_payables_liabilities_pixel_review_blueprint_v1()
    expected_other_component_counts = {
        "ACB": 10,
        "MBB": 18,
        "VPB": 16,
        "HDB": 6,
        "CTG": 18,
        "BID": 8,
        "VIB": 14,
    }
    for item in review["documents"]:
        other = [mapping for mapping in item["mappings"] if mapping["report_norm_id"] == 1127]
        if item["bank_code"] == "VCB":
            assert other == []
            continue
        assert len(other) == 1
        assert (
            sum(len(values) for values in other[0]["values"].values())
            == (expected_other_component_counts[item["bank_code"]])
        )
        assert "NOT_ADDED_TO_" in other[0]["topology"]


def test_three_visible_dashes_are_pixel_bound_before_zero_normalization() -> None:
    persisted = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())
    dash_components = [
        component
        for trial in persisted["trials"]
        for mapping in trial["verified_mappings"]
        for value in mapping["values"]
        for component in value["components"]
        if component["source_numeric_challenger_status"]
        == "VISIBLE_AUTHENTICATED_PIXEL_DASH_NOT_DETECTED_AS_SOURCE_LINE"
    ]
    assert len(dash_components) == 3
    assert {component["normalized_value"] for component in dash_components} == {0}
    assert {component["pixel_transcription"] for component in dash_components} == {"-"}


def test_hdb_transformer_digit_insertion_is_vetoed_by_source_and_accounting() -> None:
    persisted = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())
    hdb = next(item for item in persisted["trials"] if item["document_provenance"] == "HDB")
    component = next(
        component
        for mapping in hdb["verified_mappings"]
        for value in mapping["values"]
        for component in value["components"]
        if component.get("source_line_index") == 48
    )
    assert component["fresh_vietocr_numeric_proposal"] == "14.169.816"
    assert component["pixel_transcription"] == "4.169.816"
    assert component["source_numeric_challenger"] == "4.169.816"
    assert component["normalized_value"] == 4_169_816
    equation = next(
        item
        for item in hdb["verified_accounting_equations"]
        if item["name"] == "EXTERNAL_DETAILS_TO_EXTERNAL_PARENT"
        and item["period_role"] == "CURRENT"
    )
    assert equation["computed_total"] == equation["visible_total"] == 9_475_505


def test_persisted_result_matches_exact_live_replay() -> None:
    persisted = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())
    rebuilt = (
        builder.build_live_annual_2025_other_payables_liabilities_8bank_codex_verified_mapping_v1()
    )
    assert rebuilt == persisted
    assert rebuilt["result_id"] == (
        "annual2025opl8bcv1:result:10aaf6c4e18a947da792441aec9639bb5016f2a8dd1b0909a739928c8043347e"
    )
    assert rebuilt["metrics"] == builder._EXPECTED_METRICS
    assert all(not item["unmapped_source_rows"] for item in rebuilt["trials"])
