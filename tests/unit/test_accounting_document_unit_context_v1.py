from __future__ import annotations

import copy

import pytest

from bctc_ai.evaluation.accounting_document_unit_context_v1 import (
    AccountingDocumentUnitContextV1Error,
    build_accounting_document_unit_context_v1,
    validate_accounting_document_unit_context_replay_v1,
)


def _line(text: str, page: int, ordinal: int) -> dict[str, object]:
    return {
        "bbox": [10, 20 + ordinal * 20, 300, 35 + ordinal * 20],
        "crop_ref": {
            "path": f"crop/{page}-{ordinal}.png",
            "sha256": f"{page * 100 + ordinal + 1:064x}",
            "size_bytes": 1,
        },
        "line_ordinal": ordinal,
        "numeric_recognition": {"raw_prediction": text, "reader_score": 0.9},
        "sample_id": f"sample-{page}-{ordinal}",
        "vietocr_text": text,
    }


def _pages(local_unit: bool) -> list[dict[str, object]]:
    return [
        {"lines": [_line("Đơn vị: Triệu VND", 1, 0)], "page_sequence": 1, "page_width": None},
        {
            "lines": [
                _line("Công cụ tài chính phái sinh", 2, 0),
                _line("Triệu đồng" if local_unit else "Tổng giá trị hợp đồng", 2, 1),
                _line("Giao dịch kỳ hạn", 2, 2),
            ],
            "page_sequence": 2,
            "page_width": 1000,
        },
        {"lines": [_line("Triệu đồng", 3, 0)], "page_sequence": 3, "page_width": None},
    ]


REGION = {
    "cluster_end_page_sequence_inclusive": 2,
    "cluster_end_source_line_index_exclusive": 3,
    "cluster_start_source_line_index": 0,
    "page_sequence": 2,
}


def test_local_unit_precedes_document_inheritance_and_replays() -> None:
    pages = _pages(True)
    context = build_accounting_document_unit_context_v1(pages, REGION)
    assert context["evidence_mode"] == "LOCAL_SELECTED_REGION_EXPLICIT_UNIT"
    assert context["resolved_unit"] == {
        "currency": "VND",
        "magnitude_power10": 6,
        "unit_kind": "MONEY",
    }
    assert validate_accounting_document_unit_context_replay_v1(context, pages, REGION) == context


def test_document_unit_inheritance_requires_two_distinct_pages() -> None:
    pages = _pages(False)
    context = build_accounting_document_unit_context_v1(pages, REGION)
    assert context["evidence_mode"] == "REPEATED_DOCUMENT_EXPLICIT_UNIT_INHERITANCE"
    assert context["evidence_page_count"] == 2

    pages[2]["lines"][0]["vietocr_text"] = "không có đơn vị"
    with pytest.raises(AccountingDocumentUnitContextV1Error):
        build_accounting_document_unit_context_v1(pages, REGION)


def test_exchange_rate_phrase_is_not_promoted_to_billion_unit() -> None:
    pages = _pages(False)
    pages[0]["lines"][0]["vietocr_text"] = "Tổng giá trị hợp đồng theo tỷ giá"
    pages[2]["lines"][0]["vietocr_text"] = "Tổng giá trị hợp đồng theo tỷ giá"
    with pytest.raises(AccountingDocumentUnitContextV1Error):
        build_accounting_document_unit_context_v1(
            pages,
            REGION,
            expected_magnitude_power10=9,
        )


def test_unit_context_mutation_is_rejected() -> None:
    pages = _pages(True)
    context = build_accounting_document_unit_context_v1(pages, REGION)
    forged = copy.deepcopy(context)
    forged["evidence_count"] += 1
    with pytest.raises(AccountingDocumentUnitContextV1Error):
        validate_accounting_document_unit_context_replay_v1(forged, pages, REGION)


def test_open_ended_single_page_region_uses_the_rest_of_the_page() -> None:
    pages = _pages(True)
    region = {**REGION, "cluster_end_source_line_index_exclusive": None}
    context = build_accounting_document_unit_context_v1(pages, region)
    assert context["evidence_mode"] == "LOCAL_SELECTED_REGION_EXPLICIT_UNIT"
    assert context["evidence_count"] == 1
