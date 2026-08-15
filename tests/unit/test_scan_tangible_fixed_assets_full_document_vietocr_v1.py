from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/scan_tangible_fixed_assets_full_document_vietocr_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "scan_tangible_fixed_assets_full_document_vietocr_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
scanner = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scanner
_SPEC.loader.exec_module(scanner)


def _page() -> dict[str, object]:
    texts = [
        "Tài sản cố định hữu hình",
        "Biến động cho kỳ kết thúc ngày 30 tháng 06 năm 2026",
        "Triệu đồng",
        "Nguyên giá",
        "Số dư đầu kỳ",
        "1.000",
        "Mua trong kỳ",
        "100",
        "Thanh lý",
        "(20)",
        "Số dư cuối kỳ",
        "1.080",
        "Hao mòn lũy kế",
        "Số dư đầu kỳ",
        "400",
        "Khấu hao trong kỳ",
        "50",
        "Thanh lý",
        "(10)",
        "Số dư cuối kỳ",
        "440",
        "Giá trị còn lại",
        "Tại ngày đầu kỳ",
        "600",
        "Tại ngày cuối kỳ",
        "640",
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
    result = scanner.build_tangible_fixed_assets_full_document_scan_v1({})

    assert result["metrics"] == {
        "accepted_numeric_graph_count": 0,
        "complete_region_count": 8,
        "document_count": 8,
        "document_unique_structural_match_count": 8,
        "mapping_verified_count": 0,
        "near_region_count": 0,
        "rotated_rescue_line_count": 0,
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
    result = scanner.build_tangible_fixed_assets_full_document_scan_v1({})
    forged = copy.deepcopy(result)
    forged["trials"][0]["matcher_result"]["regions"][0]["numeric_line_count"] = 999
    material = copy.deepcopy(forged)
    material.pop("scan_id")
    forged["scan_id"] = "tfafdsv1:scan:" + scanner.canonical_json_sha256_v1(material)

    with pytest.raises(scanner.TangibleFixedAssetsFullDocumentScanV1Error, match="replay exactly"):
        scanner.validate_tangible_fixed_assets_full_document_scan_replay_v1(forged, {})


def test_rotated_rescue_has_fixed_external_selection_and_exact_same_model() -> None:
    semantic_index, _ = scanner._fixed_json(scanner.DEFAULT_INPUT)
    rescue = scanner.authenticate_rotated_vietocr_semantic_rescue_v1(semantic_index)

    assert rescue["line_count"] == 100
    assert rescue["samples"][42]["semantic_text"].startswith("Biến động tài sản cố định hữu hình")
    assert rescue["samples"][85]["semantic_text"] == "TÀI SẢN CỐ ĐỊNH HỮU HÌNH"
    assert rescue["authority"] == {
        "bank_or_page_used_as_matching_rule": False,
        "mapping_or_numeric_authority": False,
        "reference_text_available_to_reader": False,
        "rotation_only_same_transformer_semantic_rescue": True,
    }


def test_rotated_rescue_coherent_result_rehash_cannot_replace_fixed_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    semantic_index, _ = scanner._fixed_json(scanner.DEFAULT_INPUT)
    poisoned = dict(scanner._EXPECTED_RESCUE_REFS)
    poisoned["reader-output/ocr_result.json"] = ("0" * 64, 49719)
    monkeypatch.setattr(scanner, "_EXPECTED_RESCUE_REFS", poisoned)

    with pytest.raises(
        scanner.TangibleFixedAssetsFullDocumentScanV1Error,
        match="artifact identity drifted",
    ):
        scanner.authenticate_rotated_vietocr_semantic_rescue_v1(semantic_index)


def test_current_eight_pdf_scan_finds_only_three_unique_regions() -> None:
    result = scanner.build_live_tangible_fixed_assets_full_document_scan_v1()

    assert result["scan_id"] == (
        "tfafdsv1:scan:e301c4f490fb8231475e41676653d1c37b663f68364fc22e9dac58f9fd5f7a1f"
    )
    assert result["metrics"] == {
        "accepted_numeric_graph_count": 0,
        "complete_region_count": 3,
        "document_count": 8,
        "document_unique_structural_match_count": 3,
        "mapping_verified_count": 0,
        "near_region_count": 14,
        "rotated_rescue_line_count": 100,
        "unresolved_document_count": 5,
    }
    assert [
        (
            trial["document_provenance"],
            trial["matcher_result"]["regions"][0]["owner"]["page_sequence"],
        )
        for trial in result["trials"]
        if trial["matcher_result"]["regions"]
    ] == [("MBB", 37), ("VPB", 49), ("VIB", 37)]
    assert result["trials"][7]["rotated_rescue_line_count"] == 100
