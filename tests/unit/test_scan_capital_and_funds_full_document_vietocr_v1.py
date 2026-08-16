from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/scan_capital_and_funds_full_document_vietocr_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "scan_capital_and_funds_full_document_vietocr_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
scanner = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scanner
_SPEC.loader.exec_module(scanner)


def _page() -> dict[str, object]:
    texts = [
        "Vốn và các quỹ",
        "Báo cáo tình hình thay đổi vốn chủ sở hữu",
        "Triệu đồng",
        "Số dư đầu kỳ",
        "Số dư cuối kỳ",
        "Vốn điều lệ",
        "100",
        "100",
        "Thặng dư vốn cổ phần",
        "20",
        "20",
        "Quỹ dự phòng tài chính",
        "10",
        "10",
        "Lợi nhuận chưa phân phối",
        "30",
        "35",
        "160",
        "165",
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
    result = scanner.build_capital_and_funds_full_document_scan_v1({})
    assert result["metrics"]["document_count"] == 8
    assert result["metrics"]["complete_region_count"] == 8
    assert result["metrics"]["document_unique_structural_match_count"] == 8


def test_scanner_exact_replay_rejects_coordinated_tamper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_axis(monkeypatch)
    result = scanner.build_capital_and_funds_full_document_scan_v1({})
    forged = copy.deepcopy(result)
    forged["trials"][0]["matcher_result"]["regions"][0]["page_span"] = [2, 2]
    material = copy.deepcopy(forged)
    material.pop("scan_id")
    forged["scan_id"] = "caffdsv1:scan:" + scanner.canonical_json_sha256_v1(material)
    with pytest.raises(scanner.CapitalAndFundsFullDocumentScanV1Error, match="replay exactly"):
        scanner.validate_capital_and_funds_full_document_scan_replay_v1(forged, {})


def test_rotated_page_reading_order_is_derived_from_geometry() -> None:
    document = {
        "document_ordinal": 1,
        "pages": [
            {
                "lines": [
                    {
                        "bbox": bbox,
                        "source_line_index": index,
                        "source_text": None,
                        "vietocr_text": "old",
                    }
                    for index, bbox in enumerate(
                        ([300, 20, 310, 80], [100, 20, 110, 80], [200, 20, 210, 80])
                    )
                ],
                "page_sequence": 1,
                "primary_numeric_authority": False,
            }
        ],
    }
    rescue_by_locator = {(1, 1, index): {"semantic_text": f"new-{index}"} for index in range(3)}
    pages, count = scanner._matcher_pages(document, rescue_by_locator)
    assert count == 3
    assert [line["source_line_index"] for line in pages[0]["lines"]] == [1, 2, 0]
    assert [line["semantic_text"] for line in pages[0]["lines"]] == [
        "new-1",
        "new-2",
        "new-0",
    ]
    assert [line["vietocr_text"] for line in pages[0]["lines"]] == [
        "new-1",
        "new-2",
        "new-0",
    ]


def test_rotated_rescue_is_bound_only_to_its_exact_semantic_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = object()
    monkeypatch.setattr(
        scanner,
        "_rescue_builder",
        lambda: SimpleNamespace(
            read_verified_full_document_rotated_vietocr_rescue_v1=lambda: sentinel
        ),
    )

    assert (
        scanner._profile_rescue(
            {"metrics": {"semantic_axis_sha256": scanner._EXPECTED_SEMANTIC_AXIS_SHA256}}
        )
        is sentinel
    )
    assert scanner._profile_rescue({"metrics": {"semantic_axis_sha256": "3" * 64}}) is None


def test_current_eight_pdf_scan_is_unique_for_every_document() -> None:
    result = scanner.build_live_capital_and_funds_full_document_scan_v1()

    assert result["metrics"] == {
        "complete_region_count": 8,
        "document_count": 8,
        "document_multiple_complete_region_count": 0,
        "document_unique_structural_match_count": 8,
        "mapping_verified_count": 0,
        "near_region_count": 19,
        "rotated_rescue_line_count": 1_863,
        "unresolved_document_count": 0,
    }
    assert [
        trial["matcher_result"]["regions"][0]["owner"]["page_sequence"]
        for trial in result["trials"]
    ] == [23, 44, 60, 33, 36, 43, 27, 44]
