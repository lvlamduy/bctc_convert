from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "scripts/experiments/scan_annual_2025_liquidity_risk_full_document_vietocr_v1.py"
SPEC = importlib.util.spec_from_file_location("annual_2025_liquidity_scan_test", PATH)
assert SPEC is not None and SPEC.loader is not None
scan = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = scan
SPEC.loader.exec_module(scan)


@pytest.fixture(scope="module")
def live_scan() -> dict[str, object]:
    return scan.build_annual_2025_liquidity_risk_full_document_scan_v1()


def test_complete_pdf_scan_finds_one_unique_liquidity_region_per_document(
    live_scan: dict[str, object],
) -> None:
    assert live_scan["scan_id"] == (
        "a2025lrrfdsv1:scan:912637b03ea6eec9fbdbbf8bfe11acdbf0eb39f850697220c6bc5a1043b62990"
    )
    assert live_scan["metrics"] == {
        "bounded_detailed_table_absence_count": 0,
        "complete_region_count": 8,
        "complete_table_page_count": 12,
        "document_count": 8,
        "document_unique_structural_match_count": 8,
        "mapping_verified_count": 0,
        "near_region_count": 35,
        "rotated_rescue_line_count": 3338,
    }
    trials = live_scan["trials"]
    assert [trial["document_provenance"] for trial in trials] == list(scan.EXPECTED_DOCUMENT_ORDER)
    assert [trial["matcher_result"]["regions"][0]["table_page_sequences"] for trial in trials] == [
        [92, 93],
        [100, 101],
        [90],
        [67],
        [82],
        [79, 80],
        [69],
        [74, 75],
    ]


def test_generic_header_composition_recovers_all_eight_accounting_axes(
    live_scan: dict[str, object],
) -> None:
    expected = {
        "OVERDUE_GT3M",
        "OVERDUE_LE3M",
        "TOTAL",
        "WITHIN_1_3M",
        "WITHIN_1_5Y",
        "WITHIN_3_12M",
        "WITHIN_GT5Y",
        "WITHIN_LE1M",
    }
    for trial in live_scan["trials"]:
        region = trial["matcher_result"]["regions"][0]
        assert set(region["layout"]["maturity_axes_observed"]) == expected
        assert "ASSET_TOTAL" in region["layout"]["observed_source_roles"]
        assert "LIABILITY_TOTAL" in region["layout"]["observed_source_roles"]
        assert "NET_LIQUIDITY_GAP" in region["layout"]["observed_source_roles"]
    assert live_scan["authority"]["merged_header_may_represent_multiple_physical_axes"] is True
    assert live_scan["authority"]["text_similarity_alone_can_accept"] is False


def test_typed_tamper_and_coordinated_rehash_require_live_replay(
    live_scan: dict[str, object],
) -> None:
    forged = copy.deepcopy(live_scan)
    forged["metrics"]["complete_region_count"] = 8.0
    with pytest.raises(scan.Annual2025LiquidityRiskFullDocumentScanV1Error):
        scan.validate_annual_2025_liquidity_risk_full_document_scan_v1(forged)

    forged = copy.deepcopy(live_scan)
    forged["trials"][0]["matcher_result"]["regions"][0]["table_page_sequences"] = [1]
    material = copy.deepcopy(forged)
    material.pop("scan_id")
    forged["scan_id"] = "a2025lrrfdsv1:scan:" + scan.canonical_json_sha256_v1(material)
    with pytest.raises(scan.Annual2025LiquidityRiskFullDocumentScanV1Error):
        scan.validate_annual_2025_liquidity_risk_full_document_scan_v1(forged)
