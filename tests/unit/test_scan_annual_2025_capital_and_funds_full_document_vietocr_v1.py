from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/scan_annual_2025_capital_and_funds_full_document_vietocr_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "scan_annual_2025_capital_and_funds_full_document_vietocr_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
scanner = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scanner
_SPEC.loader.exec_module(scanner)


@pytest.fixture(scope="module")
def live_scan() -> dict[str, object]:
    return scanner.build_annual_2025_capital_and_funds_full_document_scan_v1()


def test_reporting_boundaries_are_inferred_from_visible_text_not_fixed_period() -> None:
    assert scanner._balance_boundary_key("Tại ngày 1 tháng 1 năm 2025") == "2025-01-01"
    assert scanner._balance_boundary_key("Số dư tại ngày 31/12/2025") == "2025-12-31"
    assert scanner._balance_boundary_key("Tại ngày 31 tháng 12 năm 202s") == "2025-12-31"
    assert scanner._balance_boundary_key("Số dư đầu năm") == "OPENING_YEAR"
    assert scanner._balance_boundary_key("Số dư cuối năm") == "CLOSING_YEAR"
    assert scanner._balance_boundary_key("Lợi nhuận chưa phân phối") is None


def test_annual_scan_finds_one_unique_region_in_every_complete_pdf(
    live_scan: dict[str, object],
) -> None:
    assert live_scan["metrics"] == {
        "complete_region_count": 8,
        "document_count": 8,
        "document_multiple_complete_region_count": 0,
        "document_unique_structural_match_count": 8,
        "mapping_verified_count": 0,
        "negative_control_region_count": 23,
        "rotated_rescue_line_count": 3_338,
        "unresolved_document_count": 0,
    }
    assert [trial["selected_region"]["page_span"] for trial in live_scan["trials"]] == [
        [65, 66],
        [69, 70],
        [66, 67],
        [48, 49],
        [56, 57],
        [55, 56],
        [53, 54],
        [49, 50],
    ]
    assert all(trial["selected_region"]["annual_complete"] is True for trial in live_scan["trials"])
    assert all(
        trial["selected_region"]["annual_completion_evidence"]["distinct_balance_boundary_count"]
        >= 2
        for trial in live_scan["trials"]
    )


def test_main_statement_and_continuation_regions_remain_negative_controls(
    live_scan: dict[str, object],
) -> None:
    for trial in live_scan["trials"]:
        selected = trial["selected_region"]
        assert "tiep theo" not in scanner.normalize_vietnamese_anchor_v1(
            selected["owner"]["vietocr_text"]
        )
        assert selected["layout"]["change_heading_count"] >= 1
        assert trial["negative_control_region_count"] >= 1


def test_public_replay_rejects_a_coordinated_persisted_tamper(
    live_scan: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    forged = copy.deepcopy(live_scan)
    forged["trials"][0]["selected_region"]["page_span"] = [1, 1]
    material = copy.deepcopy(forged)
    material.pop("scan_id")
    forged["scan_id"] = "a2025caffdsv1:scan:" + scanner.canonical_json_sha256_v1(material)
    monkeypatch.setattr(
        scanner,
        "build_annual_2025_capital_and_funds_full_document_scan_v1",
        lambda: live_scan,
    )
    with pytest.raises(
        scanner.Annual2025CapitalAndFundsFullDocumentScanV1Error,
        match="does not replay exactly",
    ):
        scanner.validate_annual_2025_capital_and_funds_full_document_scan_replay_v1(forged)
