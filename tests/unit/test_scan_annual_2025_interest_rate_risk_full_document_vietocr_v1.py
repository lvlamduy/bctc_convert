from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT / "scripts/experiments/scan_annual_2025_interest_rate_risk_full_document_vietocr_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "scan_annual_2025_interest_rate_risk_full_document_vietocr_v1_test_target", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
scan = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scan
_SPEC.loader.exec_module(scan)


@pytest.fixture(scope="module")
def live_scan() -> dict[str, object]:
    return scan.build_annual_2025_interest_rate_risk_full_document_scan_v1()


def test_live_scan_finds_one_bank_blind_region_in_every_complete_pdf(
    live_scan: dict[str, object],
) -> None:
    assert live_scan["scan_id"] == (
        "a2025irrfdsv1:scan:5b48aafdeafa7a1c106efb640dc502c03ef04d3f286e0df2ec10125d1a0a71c0"
    )
    assert live_scan["metrics"] == {
        "bounded_detailed_table_absence_count": 0,
        "complete_region_count": 8,
        "complete_table_page_count": 12,
        "document_count": 8,
        "document_unique_structural_match_count": 8,
        "mapping_verified_count": 0,
        "near_region_count": 33,
        "rotated_rescue_line_count": 3338,
    }
    trials = live_scan["trials"]
    assert isinstance(trials, list)
    assert [trial["document_provenance"] for trial in trials] == list(scan.EXPECTED_DOCUMENT_ORDER)
    assert [trial["matcher_result"]["regions"][0]["table_page_sequences"] for trial in trials] == [
        [87, 88],
        [95, 96],
        [85],
        [65],
        [78],
        [75, 76],
        [67],
        [68, 69],
    ]


def test_generic_variants_cover_split_merged_fuzzy_and_optional_rows(
    live_scan: dict[str, object],
) -> None:
    trials = live_scan["trials"]
    assert isinstance(trials, list)
    by_document = {trial["document_provenance"]: trial for trial in trials}
    layouts = {
        code: trial["matcher_result"]["regions"][0]["layout"] for code, trial in by_document.items()
    }

    # MBB's four-line ``Không ảnh hưởng thay đổi lãi suất`` column is one
    # generic vertically composed header, not a page/bank alias.
    assert {"OVERDUE", "NO_INTEREST", "WITHIN_1_5Y", "TOTAL"} <= set(
        layouts["MBB"]["repricing_axes_observed"]
    )
    # CTG's detector merged ``Quá hạn, Không chịu lãi`` into one text line,
    # but the source table and the numeric rows retain two physical columns.
    # The generic structural graph therefore retains two ordered roles; the
    # downstream geometry stage binds each to its own numeric column centre.
    assert {
        "OVERDUE",
        "NO_INTEREST",
        "WITHIN_1_3M",
        "WITHIN_3_6M",
        "WITHIN_6_12M",
        "WITHIN_1_5Y",
    } <= set(layouts["CTG"]["repricing_axes_observed"])
    assert "WITHIN_GT1Y" not in layouts["CTG"]["repricing_axes_observed"]
    # BID truly has no separately printed external-state row.  The complete
    # topology is admitted without inventing an implicit zero or mapping.
    assert layouts["BID"]["state_roles_observed"] == ["STATE_INTERNAL", "STATE_COMBINED"]
    assert "STATE_EXTERNAL" not in layouts["BID"]["observed_source_roles"]
    # Fuzzy text remains only an anchor: all complete numeric/table topology
    # gates and the family owner were still required to reach this result.
    assert "LIABILITY_TOTAL" in layouts["VIB"]["observed_source_roles"]
    assert live_scan["authority"]["text_similarity_alone_can_accept"] is False
    assert live_scan["authority"]["rotated_rescue_selected_by_geometry_not_bank_or_page"] is True


def test_typed_tamper_and_coordinated_rehash_still_require_live_replay(
    live_scan: dict[str, object],
) -> None:
    forged = copy.deepcopy(live_scan)
    forged["metrics"]["complete_region_count"] = 8.0
    with pytest.raises(scan.Annual2025InterestRateRiskFullDocumentScanV1Error):
        scan.validate_annual_2025_interest_rate_risk_full_document_scan_v1(forged)

    forged = copy.deepcopy(live_scan)
    forged["trials"][0]["matcher_result"]["regions"][0]["table_page_sequences"] = [1]
    material = copy.deepcopy(forged)
    material.pop("scan_id")
    forged["scan_id"] = "a2025irrfdsv1:scan:" + scan.canonical_json_sha256_v1(material)
    with pytest.raises(scan.Annual2025InterestRateRiskFullDocumentScanV1Error):
        scan.validate_annual_2025_interest_rate_risk_full_document_scan_v1(forged)
