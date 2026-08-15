from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/scan_investment_property_full_document_vietocr_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "scan_investment_property_full_document_vietocr_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
scanner = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scanner
_SPEC.loader.exec_module(scanner)


def _page() -> dict[str, object]:
    texts = [
        "Bất động sản đầu tư",
        "Tình hình cho kỳ kết thúc ngày 30 tháng 06 năm 2026",
        "Triệu đồng",
        "Nguyên giá",
        "Số dư đầu kỳ",
        "100",
        "Tăng trong kỳ",
        "10",
        "Số dư cuối kỳ",
        "110",
        "Giá trị hao mòn",
        "Số dư đầu kỳ",
        "40",
        "Tăng trong kỳ",
        "5",
        "Số dư cuối kỳ",
        "45",
        "Giá trị còn lại",
        "Số dư đầu kỳ",
        "60",
        "Số dư cuối kỳ",
        "65",
    ]
    return {
        "lines": [
            {
                "bbox": [10, index * 25, 400, index * 25 + 20],
                "source_line_index": index,
                "source_text": None,
                "vietocr_text": text,
            }
            for index, text in enumerate(texts)
        ],
        "page_sequence": 1,
        "primary_numeric_authority": False,
    }


def _axis() -> dict[str, object]:
    return {
        "documents": [
            {
                "document_ordinal": ordinal,
                "document_provenance": code,
                "pages": [_page()],
                "source_pdf": {
                    "path": f"corpus/{ordinal}/report.pdf",
                    "sha256": f"{ordinal:064x}",
                    "size_bytes": ordinal,
                },
            }
            for ordinal, code in enumerate(scanner.EXPECTED_DOCUMENT_ORDER, 1)
        ],
        "projection_id": "fdvaav1:projection:" + "1" * 64,
        "semantic_axis_sha256": "2" * 64,
    }


def test_bank_blind_scanner_covers_all_eight_documents(monkeypatch: pytest.MonkeyPatch) -> None:
    axis = _axis()
    monkeypatch.setattr(scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _: axis)
    result = scanner.build_investment_property_full_document_scan_v1({})

    assert result["metrics"]["document_count"] == 8
    assert result["metrics"]["complete_region_count"] == 8
    assert result["metrics"]["document_unique_structural_match_count"] == 8
    assert [trial["document_provenance"] for trial in result["trials"]] == list(
        scanner.EXPECTED_DOCUMENT_ORDER
    )


def test_scan_exact_replay_rejects_coordinated_match_tamper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    axis = _axis()
    monkeypatch.setattr(scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _: axis)
    result = scanner.build_investment_property_full_document_scan_v1({})
    forged = copy.deepcopy(result)
    forged["trials"][0]["matcher_result"]["regions"][0]["period_end"] = [2025, 12, 31]
    material = copy.deepcopy(forged)
    material.pop("scan_id")
    forged["scan_id"] = "ipfdsv1:scan:" + scanner.canonical_json_sha256_v1(material)

    with pytest.raises(scanner.InvestmentPropertyFullDocumentScanV1Error, match="replay exactly"):
        scanner.validate_investment_property_full_document_scan_replay_v1(forged, {})


def test_current_eight_pdf_scan_finds_only_mbb_current_region() -> None:
    result = scanner.build_live_investment_property_full_document_scan_v1()

    assert result["scan_id"] == (
        "ipfdsv1:scan:620f1f6c9d376020dc1b21632a9fd8f6b6641582f8083cb35ef31b086c31f29f"
    )
    assert result["metrics"] == {
        "comparison_region_count": 1,
        "complete_region_count": 1,
        "document_count": 8,
        "document_multiple_complete_region_count": 0,
        "document_unique_structural_match_count": 1,
        "mapping_verified_count": 0,
        "near_region_count": 12,
        "unresolved_document_count": 8,
    }
    assert [
        (
            trial["document_provenance"],
            trial["matcher_result"]["regions"][0]["owner"]["page_sequence"],
            trial["matcher_result"]["regions"][0]["period_end"],
        )
        for trial in result["trials"]
        if trial["matcher_result"]["regions"]
    ] == [("MBB", 41, [2026, 6, 30])]
