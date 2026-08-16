from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/financial_instruments_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("financial_instruments_variant_graph_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
matcher = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = matcher
_SPEC.loader.exec_module(matcher)


def _page(texts: list[str], page: int = 1) -> dict[str, object]:
    lines = []
    for index, text in enumerate(texts):
        numeric = re.fullmatch(r"\(?[0-9][0-9.,]*\)?", text) is not None
        lines.append(
            {
                "bbox": [750 if numeric else 60, index * 25, 920, index * 25 + 20],
                "semantic_text": text,
                "semantic_text_source": "FULL_DOCUMENT_FRESH_VIETOCR_TRANSFORMER",
                "source_line_index": index,
                "source_text": None,
                "vietocr_text": text,
            }
        )
    return {"lines": lines, "page_sequence": page, "primary_numeric_authority": True}


def _table_rows(*, reverse: bool = False) -> list[str]:
    rows = [
        "Tiền mặt, vàng bạc, đá quý",
        "100",
        "Tiền gửi tại NHNN",
        "200",
        "Tiền gửi tại và cho vay các TCTD khác",
        "300",
        "Chứng khoán kinh doanh",
        "400",
        "Cho vay khách hàng",
        "500",
        "Chứng khoán đầu tư",
        "600",
        "Đầu tư dài hạn khác",
        "700",
        "Tài sản tài chính khác",
        "800",
        "Các khoản nợ Chính phủ và NHNN",
        "900",
        "Tiền gửi và vay các TCTD khác",
        "1000",
        "Tiền gửi của khách hàng",
        "1100",
        "Phát hành giấy tờ có giá",
        "1200",
        "Các khoản nợ tài chính khác",
        "1300",
    ]
    return list(reversed(rows)) if reverse else rows


def _same_page(*, reverse: bool = False) -> list[str]:
    return [
        "Tài sản tài chính và nợ phải trả tài chính",
        "Giá trị ghi sổ",
        "Giá trị hợp lý",
        "Triệu đồng",
        *_table_rows(reverse=reverse),
    ]


def test_same_page_pair_first_graph_is_unique_and_row_order_flexible() -> None:
    for reverse in (False, True):
        result = matcher.build_financial_instruments_variant_graph_document_v1(
            [_page(_same_page(reverse=reverse))]
        )
        assert result["uniqueness"] == {
            "complete_region_count": 1,
            "status": "UNIQUE_FULL_MATCH",
        }
        region = result["regions"][0]
        assert region["layout"]["asset_role_count"] >= 6
        assert region["layout"]["liability_role_count"] >= 4
        assert all(len(pair) == 2 for pair in region["pair_anchor_combinations"])


def test_owner_on_previous_page_binds_one_continuation_page() -> None:
    owner = _page(
        [
            "24. Thuyết minh công cụ tài chính",
            "Bảng sau trình bày giá trị ghi sổ và giá trị hợp lý",
        ],
        1,
    )
    table = _page(["Giá trị ghi sổ", "Giá trị hợp lý", "Triệu VND", *_table_rows()], 2)
    result = matcher.build_financial_instruments_variant_graph_document_v1([owner, table])
    assert result["regions"][0]["page_span"] == [1, 2]
    assert result["regions"][0]["layout"]["table_continues_from_previous_page"] is True


def test_currency_risk_table_with_same_rows_is_rejected_without_fair_header() -> None:
    result = matcher.build_financial_instruments_variant_graph_document_v1(
        [
            _page(
                [
                    "Chính sách quản lý rủi ro liên quan đến các công cụ tài chính",
                    "Rủi ro tiền tệ",
                    "USD được quy đổi",
                    "Triệu đồng",
                    *_table_rows(),
                ]
            )
        ]
    )
    assert result["metrics"]["complete_region_count"] == 0


def test_interest_rate_risk_table_with_same_rows_is_rejected_without_book_header() -> None:
    result = matcher.build_financial_instruments_variant_graph_document_v1(
        [
            _page(
                [
                    "Các công cụ tài chính của Ngân hàng được trình bày chi tiết theo bảng dưới đây",
                    "Rủi ro lãi suất",
                    "Lãi suất được định giá lại trong vòng",
                    "Giá trị hợp lý",
                    "Triệu đồng",
                    *_table_rows(),
                ]
            )
        ]
    )
    assert result["metrics"]["complete_region_count"] == 0


def test_two_complete_regions_are_not_unique() -> None:
    result = matcher.build_financial_instruments_variant_graph_document_v1(
        [_page(_same_page(), 1), _page(_same_page(reverse=True), 2)]
    )
    assert result["uniqueness"] == {
        "complete_region_count": 2,
        "status": "NOT_UNIQUE_FULL_MATCH",
    }
