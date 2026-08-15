from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/scan_other_payables_liabilities_full_document_vietocr_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "scan_other_payables_liabilities_full_document_vietocr_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
scanner = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scanner
_SPEC.loader.exec_module(scanner)


def _page() -> dict[str, object]:
    texts = [
        "Các khoản nợ khác",
        "30/06/2026",
        "31/12/2025",
        "Triệu đồng",
        "Các khoản phải trả nội bộ",
        "100",
        "90",
        "Các khoản phải trả bên ngoài",
        "200",
        "180",
        "300",
        "270",
    ]
    return {
        "lines": [
            {
                "bbox": [50, index * 25, 750, index * 25 + 20],
                "semantic_text": text,
                "semantic_text_source": "FULL_DOCUMENT_FRESH_VIETOCR_TRANSFORMER",
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


def _patch_axis(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _: _axis()
    )
    monkeypatch.setattr(
        scanner,
        "_support",
        lambda: SimpleNamespace(_matcher_pages=lambda document, rescue: (document["pages"], 0)),
    )


def test_scanner_covers_all_eight_documents_without_bank_routing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_axis(monkeypatch)
    result = scanner.build_other_payables_liabilities_full_document_scan_v1({})
    assert result["metrics"]["document_count"] == 8
    assert result["metrics"]["complete_region_count"] == 8
    assert result["metrics"]["document_unique_structural_match_count"] == 8


def test_scanner_exact_replay_rejects_coordinated_tamper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_axis(monkeypatch)
    result = scanner.build_other_payables_liabilities_full_document_scan_v1({})
    forged = copy.deepcopy(result)
    forged["trials"][0]["matcher_result"]["regions"][0]["page_span"] = [2, 2]
    material = copy.deepcopy(forged)
    material.pop("scan_id")
    forged["scan_id"] = "oplifdsv1:scan:" + scanner.canonical_json_sha256_v1(material)
    with pytest.raises(
        scanner.OtherPayablesLiabilitiesFullDocumentScanV1Error, match="replay exactly"
    ):
        scanner.validate_other_payables_liabilities_full_document_scan_replay_v1(forged, {})
