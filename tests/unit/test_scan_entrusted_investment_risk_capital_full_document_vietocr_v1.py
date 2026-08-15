from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT / "scripts/experiments/scan_entrusted_investment_risk_capital_full_document_vietocr_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "scan_entrusted_investment_risk_capital_full_document_vietocr_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
scanner = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scanner
_SPEC.loader.exec_module(scanner)


def _page() -> dict[str, object]:
    texts = [
        "20",
        "Vốn tài trợ, ủy thác đầu tư, cho vay TCTD chịu rủi ro",
        "30/06/2026",
        "31/12/2025",
        "Triệu đồng",
        "Triệu đồng",
        "Vốn nhận của tổ chức, cá nhân khác",
        "100",
        "90",
        "100",
        "90",
    ]
    lines = []
    y = 0
    for index, text in enumerate(texts):
        if index == 0:
            bbox = [10, 0, 40, 20]
        elif index == 1:
            bbox = [60, 0, 700, 20]
            y = 25
        else:
            bbox = [60, y, 700, y + 20]
            y += 25
        lines.append(
            {
                "bbox": bbox,
                "semantic_text": text,
                "semantic_text_source": "FULL_DOCUMENT_FRESH_VIETOCR_TRANSFORMER",
                "source_line_index": index,
                "source_text": None,
                "vietocr_text": text,
            }
        )
    return {"lines": lines, "page_sequence": 1, "primary_numeric_authority": True}


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
    result = scanner.build_entrusted_investment_risk_capital_full_document_scan_v1({})
    assert result["metrics"]["document_count"] == 8
    assert result["metrics"]["complete_region_count"] == 8
    assert result["metrics"]["document_unique_structural_match_count"] == 8


def test_scanner_exact_replay_rejects_coordinated_tamper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_axis(monkeypatch)
    result = scanner.build_entrusted_investment_risk_capital_full_document_scan_v1({})
    forged = copy.deepcopy(result)
    forged["trials"][0]["matcher_result"]["regions"][0]["page_span"] = [2, 2]
    material = copy.deepcopy(forged)
    material.pop("scan_id")
    forged["scan_id"] = "eircfds1:scan:" + scanner.canonical_json_sha256_v1(material)
    with pytest.raises(
        scanner.EntrustedInvestmentRiskCapitalFullDocumentScanV1Error,
        match="replay exactly",
    ):
        scanner.validate_entrusted_investment_risk_capital_full_document_scan_replay_v1(forged, {})
