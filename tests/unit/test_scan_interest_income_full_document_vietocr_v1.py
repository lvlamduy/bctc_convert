from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/scan_interest_income_full_document_vietocr_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "scan_interest_income_full_document_vietocr_v1", _PATH
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
        "Thu nhập lãi và các khoản thu nhập tương tự",
        "Thu lãi tiền gửi",
        "100",
        "90",
        "Thu lãi cho vay khách hàng",
        "500",
        "450",
        "Thu lãi từ kinh doanh, đầu tư chứng khoán",
        "80",
        "70",
        "Thu phí từ nghiệp vụ bảo lãnh",
        "20",
        "10",
        "700",
        "620",
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
    result = scanner.build_interest_income_full_document_scan_v1({})
    assert result["metrics"]["document_count"] == 8
    assert result["metrics"]["document_unique_structural_match_count"] == 8


def test_scanner_exact_replay_rejects_coordinated_tamper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _: _axis()
    )
    result = scanner.build_interest_income_full_document_scan_v1({})
    forged = copy.deepcopy(result)
    forged["trials"][0]["matcher_result"]["regions"][0]["page_span"] = [2, 2]
    material = copy.deepcopy(forged)
    material.pop("scan_id")
    forged["scan_id"] = "iifdsv1:scan:" + scanner.canonical_json_sha256_v1(material)
    with pytest.raises(scanner.InterestIncomeFullDocumentScanV1Error, match="replay exactly"):
        scanner.validate_interest_income_full_document_scan_replay_v1(forged, {})


def test_live_scan_finds_one_unique_region_in_every_pdf() -> None:
    result = scanner.build_live_interest_income_full_document_scan_v1()
    assert result["metrics"] == {
        "complete_region_count": 8,
        "document_count": 8,
        "document_unique_structural_match_count": 8,
        "leading_total_variant_count": 1,
        "mapping_verified_count": 0,
        "near_region_count": 7,
        "trailing_total_variant_count": 7,
        "unresolved_document_count": 0,
    }
    assert [
        trial["matcher_result"]["regions"][0]["owner"]["page_sequence"]
        for trial in result["trials"]
    ] == [24, 46, 62, 34, 38, 45, 28, 45]


def test_live_loader_is_only_a_fixed_input_reader(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        scanner, "_support", lambda: SimpleNamespace(_fixed_json=lambda _: ({}, {}))
    )
    monkeypatch.setattr(
        scanner, "build_interest_income_full_document_scan_v1", lambda _: {"ok": True}
    )
    assert scanner.build_live_interest_income_full_document_scan_v1() == {"ok": True}
