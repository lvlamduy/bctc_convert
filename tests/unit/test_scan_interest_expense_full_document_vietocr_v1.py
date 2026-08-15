from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/scan_interest_expense_full_document_vietocr_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "scan_interest_expense_full_document_vietocr_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
scanner = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scanner
_SPEC.loader.exec_module(scanner)


def _page() -> dict[str, object]:
    texts = [
        "30.6.2026",
        "30.6.2025",
        "Triệu đồng",
        "Chi phí lãi và các khoản chi phí tương tự",
        "Trả lãi tiền gửi",
        "100",
        "90",
        "Trả lãi tiền vay",
        "20",
        "10",
        "Trả lãi phát hành giấy tờ có giá",
        "30",
        "25",
        "Chi phí hoạt động tín dụng khác",
        "5",
        "4",
        "155",
        "129",
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
    result = scanner.build_interest_expense_full_document_scan_v1({})
    assert result["metrics"]["document_count"] == 8
    assert result["metrics"]["document_unique_structural_match_count"] == 8


def test_scanner_exact_replay_rejects_coordinated_tamper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _: _axis()
    )
    result = scanner.build_interest_expense_full_document_scan_v1({})
    forged = copy.deepcopy(result)
    forged["trials"][0]["matcher_result"]["regions"][0]["owner"]["page_sequence"] = 2
    material = copy.deepcopy(forged)
    material.pop("scan_id")
    forged["scan_id"] = "iefdsv1:scan:" + scanner.canonical_json_sha256_v1(material)
    with pytest.raises(scanner.InterestExpenseFullDocumentScanV1Error, match="replay exactly"):
        scanner.validate_interest_expense_full_document_scan_replay_v1(forged, {})
