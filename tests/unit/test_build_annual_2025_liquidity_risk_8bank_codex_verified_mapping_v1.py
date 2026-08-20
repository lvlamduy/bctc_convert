from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1

ROOT = Path(__file__).resolve().parents[2]
PATH = (
    ROOT / "scripts/experiments/build_annual_2025_liquidity_risk_8bank_codex_verified_mapping_v1.py"
)
SPEC = importlib.util.spec_from_file_location("annual_2025_liquidity_risk_mapping_test", PATH)
assert SPEC is not None and SPEC.loader is not None
builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)


@pytest.fixture(scope="module")
def live() -> dict:
    return builder.build_live_annual_2025_liquidity_risk_8bank_codex_verified_mapping_v1()


def _trial(result: dict, bank: str) -> dict:
    return next(item for item in result["trials"] if item["document_provenance"] == bank)


def test_eight_unique_annual_regions_verify_the_exact_core(live: dict) -> None:
    assert live["metrics"] == {
        "accounting_equation_verified_count": 54,
        "authenticated_pixel_dash_zero_count": 9,
        "comparative_table_excluded_count": 4,
        "document_count": 8,
        "document_unique_region_count": 8,
        "mapping_verified_count": 181,
        "open_source_group_count": 0,
        "open_source_value_cell_count": 0,
        "rotated_ppocrv6_document_count": 3,
        "source_presentation_residual_count": 0,
        "verified_value_cell_count": 181,
    }
    assert [trial["document_provenance"] for trial in live["trials"]] == list(
        builder.EXPECTED_DOCUMENT_ORDER
    )
    assert all(trial["status"] == "VERIFIED_BY_CODEX" for trial in live["trials"])
    assert all(trial["verified_source_only_rows"] == [] for trial in live["trials"])
    assert all(trial["source_presentation_residuals"] == [] for trial in live["trials"])


def test_every_filing_keeps_all_eight_axes_and_three_core_roles(live: dict) -> None:
    expected_axes = {
        "OVERDUE_GT3M",
        "OVERDUE_LE3M",
        "WITHIN_LE1M",
        "WITHIN_1_3M",
        "WITHIN_3_12M",
        "WITHIN_1_5Y",
        "WITHIN_GT5Y",
        "TOTAL",
    }
    expected_roles = {"ASSET_TOTAL", "LIABILITY_TOTAL", "NET_LIQUIDITY_GAP"}
    for trial in live["trials"]:
        assert {row["maturity_axis"] for row in trial["verified_mappings"]} == expected_axes
        assert {row["source_role"] for row in trial["verified_mappings"]} == expected_roles
        assert all(
            equation["status"] == "VERIFIED_EXACT" and equation["residual"] == 0
            for equation in trial["verified_accounting_equations"]
        )


def test_rotated_header_ocr_noise_is_normalized_without_bank_routing() -> None:
    assert builder._liquidity_axis_role("Tùrtrên 1tháng dn3tháng") == "WITHIN_1_3M"
    assert builder._liquidity_axis_role("Türtrên 1nām đén5năm") == "WITHIN_1_5Y"
    assert builder._liquidity_axis_role("Tù 1 - 3tháng") == "WITHIN_1_3M"
    assert builder._liquidity_axis_role("Tù 1-5năm") == "WITHIN_1_5Y"
    assert builder._liquidity_axis_role("Quá hn Đn3tháng") == "OVERDUE_LE3M"
    assert builder._liquidity_axis_role("Đn1tháng") == "WITHIN_LE1M"
    assert builder._liquidity_core_role("Mc chênh thanh khon ròng") == "NET_LIQUIDITY_GAP"


def test_rotated_and_comparative_pages_remain_explicit(live: dict) -> None:
    assert live["metrics"]["rotated_ppocrv6_document_count"] == 3
    assert {
        trial["document_provenance"]
        for trial in live["trials"]
        if any(
            "source_bbox_upright_pixels" in value
            for row in trial["verified_mappings"]
            for value in row["values"]
        )
    } == {"CTG", "BID", "VIB"}
    comparative = {
        trial["document_provenance"]: [
            item["page_sequence"] for item in trial["comparative_tables_excluded"]
        ]
        for trial in live["trials"]
        if trial["comparative_tables_excluded"]
    }
    assert comparative == {"ACB": [93], "MBB": [101], "CTG": [80], "VIB": [75]}
    assert all(
        item["source_period_date"] == "2024-12-31"
        for trial in live["trials"]
        for item in trial["comparative_tables_excluded"]
    )


def test_visible_dashes_are_zero_only_with_authenticated_components(live: dict) -> None:
    zeroes = [
        value
        for trial in live["trials"]
        for row in trial["verified_mappings"]
        for value in row["values"]
        if value.get("source_numeric_challenger_status") == "AUTHENTICATED_UNIQUE_VISIBLE_DASH_ZERO"
    ]
    assert len(zeroes) == 9
    assert all(value["normalized_value"] == 0 for value in zeroes)
    assert all(value["pixel_transcription"] == "-" for value in zeroes)
    assert all(value["visual_dash_evidence"]["observation"] == "DASH" for value in zeroes)


def test_persisted_result_and_review_equal_live_rebuild(live: dict) -> None:
    assert (ROOT / builder.RESULT_PATH).read_bytes() == canonical_json_bytes_v1(live) + b"\n"
    assert (ROOT / builder.REVIEW_PATH).read_bytes() == (
        canonical_json_bytes_v1(builder._review(live)) + b"\n"
    )


def test_coordinated_rehash_cannot_pass_public_replay(
    live: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    forged = copy.deepcopy(live)
    forged["trials"][7]["verified_mappings"][0]["values"][0]["normalized_value"] += 1
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = builder.RESULT_ID_PREFIX + builder.canonical_json_sha256_v1(material)
    monkeypatch.setattr(
        builder,
        "build_live_annual_2025_liquidity_risk_8bank_codex_verified_mapping_v1",
        lambda: live,
    )
    with pytest.raises(Exception, match="replay exactly"):
        builder.validate_annual_2025_liquidity_risk_8bank_codex_verified_mapping_replay_v1(forged)
