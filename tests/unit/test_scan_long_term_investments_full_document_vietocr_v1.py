from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/scan_long_term_investments_full_document_vietocr_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "scan_long_term_investments_full_document_vietocr_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
scanner = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scanner
_SPEC.loader.exec_module(scanner)


def _page() -> dict[str, object]:
    texts = [
        "Góp vốn, đầu tư dài hạn",
        "30/06/2026",
        "31/12/2025",
        "Triệu đồng",
        "Đầu tư dài hạn khác",
        "100",
        "90",
        "Dự phòng giảm giá đầu tư dài hạn",
        "(10)",
        "90",
        "Tài sản cố định hữu hình",
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
    result = scanner.build_long_term_investments_full_document_scan_v1({})

    assert result["metrics"] == {
        "accepted_numeric_graph_count": 0,
        "complete_region_count": 8,
        "document_count": 8,
        "document_unique_structural_match_count": 8,
        "mapping_verified_count": 0,
        "near_region_count": 0,
        "unresolved_document_count": 0,
    }
    assert [trial["document_provenance"] for trial in result["trials"]] == list(
        scanner.EXPECTED_DOCUMENT_ORDER
    )


def test_scan_exact_replay_rejects_coordinated_match_tamper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    axis = _axis()
    monkeypatch.setattr(scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _: axis)
    result = scanner.build_long_term_investments_full_document_scan_v1({})
    forged = copy.deepcopy(result)
    forged["trials"][0]["matcher_result"]["regions"][0]["numeric_line_count"] = 999
    material = copy.deepcopy(forged)
    material.pop("scan_id")
    forged["scan_id"] = "ltifdsv1:scan:" + scanner.canonical_json_sha256_v1(material)

    with pytest.raises(scanner.LongTermInvestmentsFullDocumentScanV1Error, match="replay exactly"):
        scanner.validate_long_term_investments_full_document_scan_replay_v1(forged, {})


def test_current_eight_pdf_scan_has_one_unique_region_per_document() -> None:
    semantic_index = json.loads((scanner.PROJECT_ROOT / scanner.DEFAULT_INPUT).read_text("utf-8"))
    result = scanner.build_long_term_investments_full_document_scan_v1(semantic_index)

    assert result["scan_id"] == (
        "ltifdsv1:scan:6889236ce0183b78f765e88fcb1657c0ac6832e57c04f8813fac577d20926284"
    )
    assert result["metrics"] == {
        "accepted_numeric_graph_count": 0,
        "complete_region_count": 8,
        "document_count": 8,
        "document_unique_structural_match_count": 8,
        "mapping_verified_count": 0,
        "near_region_count": 27,
        "unresolved_document_count": 0,
    }
    assert [
        trial["matcher_result"]["regions"][0]["owner"]["page_sequence"]
        for trial in result["trials"]
    ] == [19, 36, 48, 30, 33, 40, 24, 36]
