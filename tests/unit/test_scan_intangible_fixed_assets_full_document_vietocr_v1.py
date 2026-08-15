from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/scan_intangible_fixed_assets_full_document_vietocr_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "scan_intangible_fixed_assets_full_document_vietocr_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
scanner = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scanner
_SPEC.loader.exec_module(scanner)


def _page() -> dict[str, object]:
    texts = [
        "Tài sản cố định vô hình",
        "Biến động cho kỳ kết thúc ngày 30 tháng 06 năm 2026",
        "Triệu đồng",
        "Nguyên giá",
        "Số dư đầu kỳ",
        "1.000",
        "Mua trong kỳ",
        "100",
        "Số dư cuối kỳ",
        "1.100",
        "Hao mòn lũy kế",
        "Số dư đầu kỳ",
        "400",
        "Khấu hao trong kỳ",
        "50",
        "Số dư cuối kỳ",
        "450",
        "Giá trị còn lại",
        "Tại ngày đầu kỳ",
        "600",
        "Tại ngày cuối kỳ",
        "650",
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
    result = scanner.build_intangible_fixed_assets_full_document_scan_v1({})

    assert result["metrics"] == {
        "complete_region_count": 8,
        "document_count": 8,
        "document_multiple_complete_region_count": 0,
        "document_unique_structural_match_count": 8,
        "mapping_verified_count": 0,
        "near_region_count": 0,
        "unresolved_document_count": 8,
    }
    assert [trial["document_provenance"] for trial in result["trials"]] == list(
        scanner.EXPECTED_DOCUMENT_ORDER
    )


def test_scan_exact_replay_rejects_coordinated_match_tamper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    axis = _axis()
    monkeypatch.setattr(scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _: axis)
    result = scanner.build_intangible_fixed_assets_full_document_scan_v1({})
    forged = copy.deepcopy(result)
    forged["trials"][0]["matcher_result"]["regions"][0]["numeric_line_count"] = 999
    material = copy.deepcopy(forged)
    material.pop("scan_id")
    forged["scan_id"] = "ifafdsv1:scan:" + scanner.canonical_json_sha256_v1(material)

    with pytest.raises(
        scanner.IntangibleFixedAssetsFullDocumentScanV1Error, match="replay exactly"
    ):
        scanner.validate_intangible_fixed_assets_full_document_scan_replay_v1(forged, {})


def test_current_eight_pdf_scan_finds_three_unique_current_family_regions() -> None:
    result = scanner.build_live_intangible_fixed_assets_full_document_scan_v1()

    assert result["scan_id"] == (
        "ifafdsv1:scan:8f3ecf325f3d0496a3cd29648eea33be4d7ab7c27308e1f1955a189a88754980"
    )
    assert result["metrics"] == {
        "complete_region_count": 3,
        "document_count": 8,
        "document_multiple_complete_region_count": 0,
        "document_unique_structural_match_count": 3,
        "mapping_verified_count": 0,
        "near_region_count": 13,
        "unresolved_document_count": 8,
    }
    assert [
        (
            trial["document_provenance"],
            trial["matcher_result"]["regions"][0]["owner"]["page_sequence"],
            trial["matcher_result"]["regions"][0]["page_span"],
        )
        for trial in result["trials"]
        if trial["matcher_result"]["regions"]
    ] == [("MBB", 39, [39, 40]), ("VPB", 50, [50, 50]), ("VIB", 38, [38, 38])]
