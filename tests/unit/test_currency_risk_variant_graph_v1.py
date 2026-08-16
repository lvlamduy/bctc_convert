from __future__ import annotations

import copy
import importlib.util
import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/currency_risk_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("currency_risk_variant_graph_v1", _PATH)
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


def _numbered_rows(labels: list[str], *, reverse: bool = False) -> list[str]:
    rows = []
    for ordinal, label in enumerate(labels, 1):
        rows.extend(
            [label, str(ordinal * 10), str(ordinal * 20), str(ordinal * 30), str(ordinal * 60)]
        )
    return list(reversed(rows)) if reverse else rows


def _table(*, reverse_children: bool = False, owner: bool = True) -> list[str]:
    rows = [
        "Tài sản",
        "Tiền mặt, vàng bạc, đá quý",
        "Tiền gửi tại NHNN",
        "Tiền gửi tại và cho vay các TCTD khác",
        "Công cụ tài chính phái sinh và các tài sản tài chính khác",
        "Cho vay khách hàng",
        "Các tài sản Có khác",
        "Tổng tài sản",
        "Nợ phải trả",
        "Tiền gửi và vay từ NHNN và các TCTD khác",
        "Tiền gửi của khách hàng",
        "Phát hành giấy tờ có giá",
        "Các khoản nợ khác",
        "Tổng nợ phải trả",
        "Trạng thái tiền tệ nội bảng",
        "Trạng thái tiền tệ ngoại bảng",
        "Trạng thái tiền tệ nội, ngoại bảng",
    ]
    return [
        *(["Rủi ro tiền tệ"] if owner else []),
        "USD được quy đổi",
        "EUR được quy đổi",
        "Các ngoại tệ khác được quy đổi",
        "Tổng cộng",
        "Đơn vị: Triệu đồng",
        *_numbered_rows(rows, reverse=reverse_children),
    ]


def test_pair_first_core_accepts_flexible_child_order_and_optional_axes() -> None:
    for reverse in (False, True):
        result = matcher.build_currency_risk_variant_graph_document_v1(
            [_page(["VND", "Vàng được quy đổi", *_table(reverse_children=reverse)])]
        )
        assert result["uniqueness"] == {
            "complete_region_count": 1,
            "status": "UNIQUE_FULL_MATCH",
        }
        region = result["regions"][0]
        assert {"USD", "EUR", "VND", "GOLD", "OTHER", "TOTAL"} == set(
            region["layout"]["currency_axes_observed"]
        )
        assert region["layout"]["row_and_axis_order_is_semantic"] is False
        assert all(len(pair) == 2 for pair in region["pair_anchor_combinations"])


def test_owner_on_previous_page_binds_table_continuation() -> None:
    owner = _page(["24. Rủi ro thị trường", "Rủi ro tiền tệ"], 1)
    table = _page(_table(owner=False), 2)
    result = matcher.build_currency_risk_variant_graph_document_v1([owner, table])
    assert result["regions"][0]["page_span"] == [1, 2]
    assert result["regions"][0]["layout"]["table_continues_from_previous_page"] is True


def test_adjacent_current_and_comparative_tables_merge_into_one_region() -> None:
    current = _page(_table(), 1)
    comparative = _page(["Rủi ro tiền tệ (tiếp theo)", *_table(owner=False)], 2)
    result = matcher.build_currency_risk_variant_graph_document_v1([current, comparative])
    assert result["uniqueness"] == {
        "complete_region_count": 1,
        "status": "UNIQUE_FULL_MATCH",
    }
    assert result["regions"][0]["table_page_sequences"] == [1, 2]
    assert result["regions"][0]["layout"]["period_table_count"] == 2


def test_complete_currency_like_table_without_owner_is_only_near() -> None:
    result = matcher.build_currency_risk_variant_graph_document_v1([_page(_table(owner=False))])
    assert result["metrics"]["complete_region_count"] == 0
    assert result["near_regions"][0]["reason"] == (
        "COMPLETE_CURRENCY_LIKE_TABLE_WITHOUT_BOUND_FAMILY_OWNER"
    )


def test_interest_liquidity_and_fair_value_controls_cannot_accept() -> None:
    for negative in ("Rủi ro lãi suất", "Rủi ro thanh khoản", "Giá trị hợp lý"):
        result = matcher.build_currency_risk_variant_graph_document_v1(
            [_page([negative, *_table()])]
        )
        assert result["metrics"]["complete_region_count"] == 0


def test_missing_core_parent_total_or_state_rejects() -> None:
    for missing in ("Tổng tài sản", "Tổng nợ phải trả", "Trạng thái tiền tệ nội bảng"):
        result = matcher.build_currency_risk_variant_graph_document_v1(
            [_page([text for text in _table() if text != missing])]
        )
        assert result["metrics"]["complete_region_count"] == 0


def test_two_separated_complete_regions_are_not_unique() -> None:
    result = matcher.build_currency_risk_variant_graph_document_v1(
        [_page(_table(), 1), _page(["Trang đối chứng"], 2), _page(_table(), 3)]
    )
    assert result["uniqueness"] == {
        "complete_region_count": 2,
        "status": "NOT_UNIQUE_FULL_MATCH",
    }


def test_typed_tamper_rejects() -> None:
    result = matcher.build_currency_risk_variant_graph_document_v1([_page(_table())])
    tampered = copy.deepcopy(result)
    tampered["metrics"]["complete_region_count"] = 1.0
    with pytest.raises(matcher.CurrencyRiskVariantGraphV1Error):
        matcher.validate_currency_risk_variant_graph_document_v1(tampered)
