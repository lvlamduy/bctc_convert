from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/scan_annual_2025_currency_risk_full_document_vietocr_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "scan_annual_2025_currency_risk_full_document_vietocr_v1_test_target", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
scan = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scan
_SPEC.loader.exec_module(scan)


@pytest.fixture(scope="module")
def live_scan() -> dict[str, object]:
    return scan.build_annual_2025_currency_risk_full_document_scan_v1()


def test_live_scan_finds_one_bank_blind_region_in_every_complete_pdf(
    live_scan: dict[str, object],
) -> None:
    assert live_scan["scan_id"] == (
        "a2025crfdsv1:scan:3423250f79d91c015bd36031c6eb20bfe4aebbb096be25d4c47faa040c0b3ec8"
    )
    assert live_scan["metrics"] == {
        "bounded_detailed_table_absence_count": 0,
        "complete_region_count": 8,
        "complete_table_page_count": 12,
        "document_count": 8,
        "document_unique_structural_match_count": 8,
        "mapping_verified_count": 0,
        "near_region_count": 11,
        "rotated_rescue_line_count": 3338,
    }
    trials = live_scan["trials"]
    assert isinstance(trials, list)
    assert [trial["document_provenance"] for trial in trials] == list(scan.EXPECTED_DOCUMENT_ORDER)
    assert [trial["matcher_result"]["regions"][0]["table_page_sequences"] for trial in trials] == [
        [84, 85],
        [97, 98],
        [88],
        [63],
        [80],
        [71, 72],
        [65],
        [71, 72],
    ]


def test_annual_variants_are_generic_and_typed_replay_rejects_tamper(
    live_scan: dict[str, object],
) -> None:
    trials = live_scan["trials"]
    assert isinstance(trials, list)
    axes = {
        trial["document_provenance"]: trial["matcher_result"]["regions"][0]["layout"][
            "currency_axes_observed"
        ]
        for trial in trials
    }
    assert axes["ACB"] == ["USD", "GOLD", "EUR", "JPY", "AUD", "CAD", "OTHER", "TOTAL"]
    assert axes["MBB"] == ["USD", "EUR", "OTHER", "TOTAL"]
    assert axes["VPB"] == ["EUR", "USD", "GOLD", "OTHER", "TOTAL"]
    assert axes["BID"] == ["EUR", "USD", "OTHER", "TOTAL"]
    assert live_scan["authority"]["rotated_rescue_selected_by_geometry_not_bank_or_page"] is True

    forged = copy.deepcopy(live_scan)
    forged["metrics"]["complete_region_count"] = 8.0
    with pytest.raises(scan.Annual2025CurrencyRiskFullDocumentScanV1Error):
        scan.validate_annual_2025_currency_risk_full_document_scan_v1(forged)
