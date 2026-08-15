from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/scan_fx_gold_activity_full_document_vietocr_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "scan_fx_gold_activity_full_document_vietocr_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
scanner = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scanner
_SPEC.loader.exec_module(scanner)


def _page() -> dict[str, object]:
    texts = [
        "Lãi thuần từ hoạt động kinh doanh ngoại hối",
        "6 tháng đầu năm 2026",
        "6 tháng đầu năm 2025",
        "Triệu đồng",
        "Thu nhập từ hoạt động kinh doanh ngoại hối",
        "100",
        "90",
        "Thu từ kinh doanh ngoại tệ giao ngay",
        "80",
        "70",
        "Thu từ các công cụ tài chính phái sinh tiền tệ",
        "20",
        "20",
        "Chi phí hoạt động kinh doanh ngoại hối",
        "(30)",
        "(20)",
        "Chi về kinh doanh ngoại tệ giao ngay",
        "(20)",
        "(10)",
        "Chi về các công cụ tài chính phái sinh tiền tệ",
        "(10)",
        "(10)",
        "Lãi thuần từ hoạt động kinh doanh ngoại hối",
        "70",
        "70",
    ]
    return {
        "lines": [
            {
                "bbox": [50, index * 25, 750, index * 25 + 20],
                "source_line_index": index,
                "source_text": None,
                "vietocr_text": text,
            }
            for index, text in enumerate(texts)
        ],
        "page_sequence": 1,
        "primary_numeric_authority": True,
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


def test_scanner_covers_all_eight_documents(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _: _axis()
    )
    result = scanner.build_fx_gold_activity_full_document_scan_v1({})
    assert result["metrics"]["document_count"] == 8
    assert result["metrics"]["document_unique_structural_match_count"] == 8


def test_scanner_exact_replay_rejects_coordinated_tamper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _: _axis()
    )
    result = scanner.build_fx_gold_activity_full_document_scan_v1({})
    forged = copy.deepcopy(result)
    forged["trials"][0]["matcher_result"]["regions"][0]["owner"]["page_sequence"] = 2
    material = copy.deepcopy(forged)
    material.pop("scan_id")
    forged["scan_id"] = "fxgfdsv1:scan:" + scanner.canonical_json_sha256_v1(material)
    with pytest.raises(scanner.FxGoldActivityFullDocumentScanV1Error, match="replay exactly"):
        scanner.validate_fx_gold_activity_full_document_scan_replay_v1(forged, {})
