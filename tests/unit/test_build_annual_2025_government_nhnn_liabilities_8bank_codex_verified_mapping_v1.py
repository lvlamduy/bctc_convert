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
    / "scripts/experiments/build_annual_2025_government_nhnn_liabilities_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "build_annual_2025_government_nhnn_liabilities_8bank_codex_verified_mapping_v1",
    _PATH,
)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def live() -> dict[str, object]:
    return (
        builder.build_live_annual_2025_government_nhnn_liabilities_8bank_codex_verified_mapping_v1()
    )


def test_all_eight_reports_have_one_unique_annual_region(live: dict[str, object]) -> None:
    assert live["metrics"] == builder._EXPECTED_METRICS
    assert [trial["document_provenance"] for trial in live["trials"]] == [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert all(
        trial["source_period"] == "2025-12-31"
        and trial["source_period_status"]
        == "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
        and trial["whole_document_uniqueness"]
        == {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
        for trial in live["trials"]
    )


def test_exact_schema_coverage_and_accounting(live: dict[str, object]) -> None:
    for trial in live["trials"]:
        actual = {
            mapping["schema_binding"]["report_norm_id"] for mapping in trial["verified_mappings"]
        }
        assert actual == builder._EXPECTED_IDS[trial["document_provenance"]]
        assert all(
            equation["status"] == "VERIFIED_EXACT"
            and equation["computed_total"] == equation["visible_total"]
            for equation in trial["verified_accounting_equations"]
        )


def test_bound_dashes_and_small_hdb_number_close_all_reviewed_rows(
    live: dict[str, object],
) -> None:
    assert all(not trial["unmapped_source_rows"] for trial in live["trials"])
    by_bank = {trial["document_provenance"]: trial for trial in live["trials"]}

    hdb = by_bank["HDB"]
    treasury = next(
        mapping
        for mapping in hdb["verified_mappings"]
        if mapping["schema_binding"]["report_norm_id"] == 1035
    )
    assert treasury["values"][1]["normalized_value"] == 1
    assert treasury["values"][1]["components"][0]["source_numeric_challenger_status"] == (
        "VISIBLE_AUTHENTICATED_PIXEL_NUMBER_NOT_DETECTED_AS_SOURCE_LINE"
    )

    zero_cells = [
        component
        for trial in live["trials"]
        for mapping in trial["verified_mappings"]
        for value in mapping["values"]
        for component in value["components"]
        if component["source_numeric_challenger_status"]
        == "VISIBLE_AUTHENTICATED_PIXEL_DASH_NOT_DETECTED_AS_SOURCE_LINE"
    ]
    assert len(zero_cells) == 6
    assert all(cell["normalized_value"] == 0 for cell in zero_cells)


def test_user_approved_other_bucket_preserves_source_components(
    live: dict[str, object],
) -> None:
    by_bank = {trial["document_provenance"]: trial for trial in live["trials"]}
    expected = {
        "ACB": (1_805_161, 0),
        "CTG": (2_972_159, 6_958),
        "BID": (149_500, 161_178),
    }
    for bank, values in expected.items():
        mapping = next(
            item
            for item in by_bank[bank]["verified_mappings"]
            if item["schema_binding"]["report_norm_id"] == 1033
        )
        assert tuple(value["normalized_value"] for value in mapping["values"]) == values


def test_exact_replay_rejects_coordinated_mapping_rehash(live: dict[str, object]) -> None:
    forged = copy.deepcopy(live)
    forged["trials"][0]["verified_mappings"][0]["values"][0]["normalized_value"] += 1
    base = builder._configure_base()
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + base.canonical_json_sha256_v1(material)

    with pytest.raises(builder.Annual2025GovernmentNHNNLiabilities8BankError):
        builder.validate_annual_2025_government_nhnn_liabilities_8bank_codex_verified_mapping_replay_v1(
            forged
        )


def test_persisted_review_and_result_equal_live_bytes(live: dict[str, object]) -> None:
    persisted_review = json.loads((builder.PROJECT_ROOT / builder.REVIEW_PATH).read_text("utf-8"))
    persisted_result = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text("utf-8"))

    assert persisted_review == (
        builder.build_annual_2025_government_nhnn_liabilities_pixel_review_blueprint_v1()
    )
    assert persisted_result == live
