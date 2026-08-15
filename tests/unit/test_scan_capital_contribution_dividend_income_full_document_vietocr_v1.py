from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT
    / "scripts/experiments/scan_capital_contribution_dividend_income_full_document_vietocr_v1.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "scan_capital_contribution_dividend_income_full_document_vietocr_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
scanner = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scanner
_SPEC.loader.exec_module(scanner)


def _axis() -> dict[str, object]:
    documents = []
    complete_texts = [
        "18.",
        "Thu nhập từ góp vốn, mua cổ phần",
        "Kỳ này",
        "Kỳ trước",
        "Triệu VND",
        "Triệu VND",
        "Cổ tức nhận được từ góp vốn, mua cổ phần",
        "10",
        "20",
        "10",
        "20",
    ]
    for ordinal, code in enumerate(scanner.EXPECTED_DOCUMENT_ORDER, 1):
        texts = ["Thu nhập từ góp vốn, mua cổ phần", "200", "100", "200", "100"]
        if code != "VIB":
            texts = complete_texts
        documents.append(
            {
                "document_ordinal": ordinal,
                "document_provenance": code,
                "pages": [
                    {
                        "lines": [
                            {
                                "bbox": (
                                    [10, 0, 35, 20]
                                    if i == 0
                                    else [
                                        60,
                                        0 if i == 1 else i * 25,
                                        700,
                                        20 if i == 1 else i * 25 + 20,
                                    ]
                                ),
                                "semantic_text": text,
                                "semantic_text_source": "FULL_DOCUMENT_FRESH_VIETOCR_TRANSFORMER",
                                "source_line_index": i,
                                "source_text": None,
                                "vietocr_text": text,
                            }
                            for i, text in enumerate(texts)
                        ],
                        "page_sequence": 1,
                        "primary_numeric_authority": True,
                    }
                ],
                "source_pdf": {"sha256": f"{ordinal:064x}"},
            }
        )
    return {
        "documents": documents,
        "projection_id": "axis:test",
        "semantic_axis_sha256": "1" * 64,
    }


def test_scan_finds_seven_detailed_notes_and_one_statement_control(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    axis = _axis()
    monkeypatch.setattr(scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _: axis)
    result = scanner.build_capital_contribution_dividend_income_full_document_scan_v1({})
    assert result["metrics"]["complete_region_count"] == 7
    assert result["metrics"]["document_unique_structural_match_count"] == 7
    assert result["metrics"]["unresolved_document_count"] == 1


def test_scan_replay_rejects_coordinated_tamper(monkeypatch: pytest.MonkeyPatch) -> None:
    axis = _axis()
    monkeypatch.setattr(scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _: axis)
    result = scanner.build_capital_contribution_dividend_income_full_document_scan_v1({})
    forged = copy.deepcopy(result)
    forged["trials"][0]["document_provenance"] = "MBB"
    material = copy.deepcopy(forged)
    material.pop("scan_id")
    forged["scan_id"] = "ccdifdsv1:scan:" + scanner.canonical_json_sha256_v1(material)
    with pytest.raises(
        scanner.CapitalContributionDividendIncomeFullDocumentScanV1Error,
        match="trial identity",
    ):
        scanner.validate_capital_contribution_dividend_income_full_document_scan_replay_v1(
            forged, {}
        )
