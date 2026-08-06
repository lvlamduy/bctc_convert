from __future__ import annotations

import pytest

from bctc_ai.evaluation.holdout_statement_diagnosis import (
    HoldoutStatementDiagnosisError,
    NativeLine,
    _classify_native_page,
    _validate_reference_sequence,
)
from bctc_ai.ocr.pdf_text import PDFTextPage


def _page(page: int = 1) -> PDFTextPage:
    return PDFTextPage(
        page=page,
        width_points=595,
        height_points=842,
        rotation=0,
        words=[],
        text_quality="CORRUPT_TEXT_LAYER",
        corruption_markers=("Â",),
    )


def _line(text: str, y: float) -> NativeLine:
    from bctc_ai.core.text import retrieval_key

    return NativeLine(text=text, key=retrieval_key(text), bbox=(40, y, 550, y + 12))


def _policy() -> dict:
    return {
        "title_cores": {
            "CDKT": ["báo cáo tình hình tài chính"],
            "KQKD": ["báo cáo kết quả hoạt động"],
            "LCTT": ["báo cáo lưu chuyển tiền tệ"],
            "TM": ["thuyết minh báo cáo tài chính"],
        },
        "table_of_contents_cores": ["mục lục"],
        "off_balance_cores": ["các chỉ tiêu ngoài báo cáo tình hình tài chính"],
        "cash_flow_method_cores": {
            "DIRECT": ["theo phương pháp trực tiếp"],
            "INDIRECT": ["theo phương pháp gián tiếp"],
        },
    }


def test_native_reference_uses_title_containment_and_form_family_normalization():
    result = _classify_native_page(
        _page(),
        (
            _line("Mẫu B02a/TCTD-HN", 20),
            _line("BÁO CÁO TÌNH HÌNH TÀI CHÍNH HỢP NHẤT GIỮA NIÊN ĐỘ", 40),
        ),
        _policy(),
    )

    assert result["page_type"] == "CDKT"
    assert result["scope"] == "MAIN_STATEMENT"
    assert result["form"]["normalized_family"] == "B02"
    assert result["form"]["suffix"] == "a"


def test_native_reference_excludes_off_balance_and_identifies_direct_lctt():
    off_balance = _classify_native_page(
        _page(),
        (
            _line("BÁO CÁO TÌNH HÌNH TÀI CHÍNH HỢP NHẤT", 20),
            _line("CÁC CHỈ TIÊU NGOÀI BÁO CÁO TÌNH HÌNH TÀI CHÍNH", 40),
        ),
        _policy(),
    )
    direct = _classify_native_page(
        _page(2),
        (
            _line("BÁO CÁO LƯU CHUYỂN TIỀN TỆ HỢP NHẤT GIỮA NIÊN ĐỘ", 20),
            _line("(Theo phương pháp trực tiếp)", 40),
        ),
        _policy(),
    )

    assert off_balance["scope"] == "OUT_OF_SCOPE_FOR_TARGET_TEMPLATE"
    assert direct["page_type"] == "LCTT"
    assert direct["scope"] == "MAIN_STATEMENT"
    assert direct["cash_flow_method"] == "DIRECT"


def test_native_reference_sequence_fails_closed_on_wrong_statement_order():
    decisions = [
        {"page": 1, "page_type": "KQKD", "scope": "MAIN_STATEMENT"},
        {
            "page": 2,
            "page_type": "LCTT",
            "scope": "MAIN_STATEMENT",
            "cash_flow_method": "DIRECT",
        },
    ]

    with pytest.raises(HoldoutStatementDiagnosisError, match="not CDKT->KQKD->LCTT"):
        _validate_reference_sequence(decisions)
