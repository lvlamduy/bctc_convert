from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _ROOT / "scripts/experiments/scan_loan_maturity_full_document_vietocr_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "scan_loan_maturity_full_document_vietocr_v1", _MODULE_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
scanner = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scanner
_SPEC.loader.exec_module(scanner)


def _surfaces() -> list[tuple[str, int]]:
    return [
        ("5. Cho vay khách hàng", 0),
        ("Phân tích dư nợ theo thời gian", 0),
        ("30/06/2026", 100),
        ("31/12/2025", 300),
        ("Triệu đồng", 100),
        ("Triệu đồng", 300),
        ("Dư nợ cho vay", 0),
        ("Nợ ngắn hạn", 0),
        ("10", 100),
        ("11", 300),
        ("Nợ trung hạn", 0),
        ("20", 100),
        ("21", 300),
        ("Nợ dài hạn", 0),
        ("30", 100),
        ("31", 300),
        ("60", 100),
        ("63", 300),
    ]


def _page(physical_page: int = 1) -> dict[str, object]:
    lines = []
    for line_index, (text, x) in enumerate(_surfaces()):
        lines.append(
            {
                "crop_ref": {
                    "path": f"opaque/sample-{physical_page:04d}-{line_index:04d}.png",
                    "sha256": f"{line_index + 1:064x}",
                    "size_bytes": 1,
                },
                "line_axis_role": "PRIMARY_AUTHENTICATED_LINE",
                "mean_decoded_character_probability": 0.9,
                "padded_source_bbox_raw_pixels": [x, line_index * 20, x + 80, line_index * 20 + 14],
                "processed_height": 32,
                "processed_width": 100,
                "sample_id": f"sample-{physical_page:04d}-{line_index:04d}",
                "source_bbox_raw_pixels": [x, line_index * 20, x + 80, line_index * 20 + 14],
                "source_line_index": line_index,
                "vietocr_text": text,
            }
        )
    return {
        "geometry_mode": "AUTHENTICATED_RASTER_RAW_PIXEL_PRIMARY_LINE_V2",
        "line_count": len(lines),
        "lines": lines,
        "physical_page": physical_page,
        "route": "OCR_WORD_BOX",
        "source_projection": {"sha256": "1" * 64},
        "terminal_status_preserved": False,
        "upstream_status": "OCR_WORD_BOX_READ_COMPLETE",
    }


def _index() -> dict[str, object]:
    documents = []
    line_vector = []
    page_vector = []
    for ordinal, bank in enumerate(scanner.EXPECTED_BANK_ORDER, 1):
        page = _page()
        documents.append(
            {
                "bank_code": bank,
                "document_ordinal": ordinal,
                "page_count": 1,
                "pages": [page],
                "source_pdf": {
                    "path": f"opaque/document-{ordinal:04d}.pdf",
                    "sha256": f"{ordinal:064x}",
                    "size_bytes": 1,
                },
            }
        )
        line_vector.append(page["line_count"])
        page_vector.append(1)
    return {
        "authority": {
            "all_empty_predictions_preserved": True,
            "geometry_authority": False,
            "mapping_authority": False,
            "numeric_authority": False,
            "old_ppocr_or_native_transcript_used_as_semantic_text": False,
            "ordered_semantic_proposal_authority": True,
            "semantic_text_source": "FRESH_VIETOCR_VGG_TRANSFORMER_0_3_13",
        },
        "documents": documents,
        "format_version": "WAVE1_8DOCUMENT_VIETOCR_TRANSFORMER_SEMANTIC_INDEX_V1",
        "input_refs": {},
        "metrics": {
            "document_count": 8,
            "empty_prediction_count": 0,
            "line_count_vector": line_vector,
            "page_count": sum(page_vector),
            "page_count_vector": page_vector,
            "sample_count": sum(line_vector),
            "semantic_axis_sha256": "a" * 64,
            "terminal_page_count": 0,
        },
        "reader": {},
        "state": "VERIFIED_COMPLETE_ORDERED_VIETOCR_TRANSFORMER_PROPOSALS",
    }


def test_eight_documents_use_one_common_matcher_and_remain_structure_only():
    value = scanner.build_loan_maturity_full_document_scan_v1(_index())

    assert value["state"] == "FULL_DOCUMENT_STRUCTURE_SCAN_COMPLETE"
    assert value["metrics"] == {
        "accepted_numeric_graph_count": 0,
        "complete_context_region_count": 8,
        "document_count": 8,
        "document_multiple_complete_context_region_count": 0,
        "document_unique_candidate_count": 8,
        "mapping_verified_count": 0,
        "near_region_count": 0,
        "ordered_anchor_region_count": 8,
        "structure_resolved_numeric_unresolved_count": 8,
        "total_document_candidate_count": 8,
        "unresolved_document_count": 0,
    }
    assert [trial["bank_provenance"] for trial in value["trials"]] == list(
        scanner.EXPECTED_BANK_ORDER
    )
    assert all(
        trial["matcher_result"]["status"] == "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"
        for trial in value["trials"]
    )
    assert value["authority"]["bank_identity_used_for_matching_or_routing"] is False
    assert value["authority"]["numeric_authority"] is False
    assert value["authority"]["mapping_authority"] is False
    assert all(
        trial["region_scan"]["metrics"]["complete_context_region_count"] == 1
        for trial in value["trials"]
    )


def test_second_complete_region_is_preserved_as_ambiguity_not_silently_selected():
    index = _index()
    duplicate = copy.deepcopy(index["documents"][0]["pages"][0])
    duplicate["physical_page"] = 2
    for line in duplicate["lines"]:
        line["sample_id"] = "duplicate-" + line["sample_id"]
    index["documents"][0]["pages"].append(duplicate)
    index["documents"][0]["page_count"] = 2
    index["metrics"]["page_count_vector"][0] = 2
    index["metrics"]["page_count"] += 1
    index["metrics"]["line_count_vector"][0] *= 2
    index["metrics"]["sample_count"] += duplicate["line_count"]

    value = scanner.build_loan_maturity_full_document_scan_v1(index)

    assert value["trials"][0]["matcher_result"]["status"] == "UNRESOLVED"
    assert value["trials"][0]["matcher_result"]["document_candidate_count"] == 2
    assert value["trials"][0]["region_scan"]["metrics"]["complete_context_region_count"] == 2
    assert value["metrics"]["document_multiple_complete_context_region_count"] == 1
    assert value["metrics"]["structure_resolved_numeric_unresolved_count"] == 7
    assert value["metrics"]["total_document_candidate_count"] == 9


def test_old_ocr_authority_and_coordinated_result_rehash_fail_closed():
    index = _index()
    index["authority"]["old_ppocr_or_native_transcript_used_as_semantic_text"] = True
    with pytest.raises(scanner.LoanMaturityFullDocumentScanV1Error):
        scanner.build_loan_maturity_full_document_scan_v1(index)

    clean_index = _index()
    value = scanner.build_loan_maturity_full_document_scan_v1(clean_index)
    tampered = copy.deepcopy(value)
    tampered["trials"][0]["matcher_result"]["status"] = "UNRESOLVED"
    material = copy.deepcopy(tampered)
    material.pop("scan_id")
    tampered["scan_id"] = "lmfdsv1:scan:" + canonical_json_sha256_v1(material)
    with pytest.raises(scanner.LoanMaturityFullDocumentScanV1Error):
        scanner.validate_loan_maturity_full_document_scan_replay_v1(tampered, clean_index)
