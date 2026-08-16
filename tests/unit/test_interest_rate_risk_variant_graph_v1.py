from __future__ import annotations

import copy
import importlib.util
import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/interest_rate_risk_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("interest_rate_risk_variant_graph_v1", _PATH)
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


def _numbered_rows(labels: list[str]) -> list[str]:
    rows = []
    for ordinal, label in enumerate(labels, 1):
        rows.extend([label, str(ordinal * 10), str(ordinal * 20), str(ordinal * 30)])
    return rows


def _table(*, owner: bool = True, reverse_children: bool = False) -> list[str]:
    axes = [
        "Không chịu lãi suất",
        "Quá hạn",
        "Đến 1 tháng",
        "Từ 1 đến 3 tháng",
        "Từ 3 đến 6 tháng",
        "Từ 6 đến 12 tháng",
        "Từ 1 đến 5 năm",
        "Trên 5 năm",
        "Tổng cộng",
        "Đơn vị: Triệu đồng",
    ]
    asset_children = [
        "Tiền mặt, vàng bạc, đá quý",
        "Tiền gửi tại NHNN",
        "Tiền gửi tại và cho vay các TCTD khác",
        "Chứng khoán kinh doanh",
        "Công cụ tài chính phái sinh và các tài sản tài chính khác",
        "Cho vay khách hàng",
        "Chứng khoán đầu tư",
        "Các tài sản Có khác",
    ]
    liability_children = [
        "Tiền gửi và vay từ NHNN và các TCTD khác",
        "Tiền gửi của khách hàng",
        "Phát hành giấy tờ có giá",
        "Các khoản nợ khác",
    ]
    if reverse_children:
        asset_children.reverse()
        liability_children.reverse()
    rows = [
        "Tài sản",
        *asset_children,
        "Tổng tài sản",
        "Nợ phải trả",
        *liability_children,
        "Tổng nợ phải trả",
        "Mức chênh nhạy cảm với lãi suất nội bảng",
        "Mức chênh nhạy cảm với lãi suất ngoại bảng",
        "Mức chênh nhạy cảm với lãi suất nội, ngoại bảng",
    ]
    return [
        *(["Rủi ro lãi suất"] if owner else []),
        *axes,
        *_numbered_rows(rows),
    ]


def test_pair_first_core_accepts_flexible_rows_and_optional_axis_variants() -> None:
    for reverse in (False, True):
        result = matcher.build_interest_rate_risk_variant_graph_document_v1(
            [_page(_table(reverse_children=reverse))]
        )
        assert result["uniqueness"] == {
            "complete_region_count": 1,
            "status": "UNIQUE_FULL_MATCH",
        }
        region = result["regions"][0]
        assert {"NO_INTEREST", "OVERDUE", "WITHIN_LE1M", "TOTAL"} <= set(
            region["layout"]["repricing_axes_observed"]
        )
        assert region["layout"]["row_and_axis_order_is_semantic"] is False
        assert all(len(pair) == 2 for pair in region["pair_anchor_combinations"])


def test_split_headers_and_split_state_label_join_by_geometry() -> None:
    texts = _table()
    texts[texts.index("Không chịu lãi suất")] = "Không chịu"
    texts.insert(texts.index("Không chịu") + 1, "lãi suất")
    texts[texts.index("Mức chênh nhạy cảm với lãi suất nội bảng")] = (
        "Mức chênh nhạy cảm với lãi suất nội"
    )
    texts.insert(texts.index("Mức chênh nhạy cảm với lãi suất nội") + 1, "bảng")
    result = matcher.build_interest_rate_risk_variant_graph_document_v1([_page(texts)])
    assert result["uniqueness"]["status"] == "UNIQUE_FULL_MATCH"
    assert "STATE_INTERNAL" in result["regions"][0]["layout"]["state_roles_observed"]


def test_owner_on_previous_page_and_comparative_continuation_merge() -> None:
    result = matcher.build_interest_rate_risk_variant_graph_document_v1(
        [
            _page(["Rủi ro lãi suất"], 1),
            _page(_table(owner=False), 2),
            _page(["Rủi ro lãi suất (tiếp theo)", *_table(owner=False)], 3),
        ]
    )
    assert result["regions"][0]["page_span"] == [1, 3]
    assert result["regions"][0]["table_page_sequences"] == [2, 3]
    assert result["regions"][0]["layout"]["period_table_count"] == 2


def test_complete_table_without_owner_is_only_near() -> None:
    result = matcher.build_interest_rate_risk_variant_graph_document_v1(
        [_page(_table(owner=False))]
    )
    assert result["metrics"]["complete_region_count"] == 0
    assert result["near_regions"][0]["reason"] == (
        "COMPLETE_REPRICING_LIKE_TABLE_WITHOUT_BOUND_FAMILY_OWNER"
    )


def test_currency_liquidity_and_fair_value_controls_cannot_accept() -> None:
    for negative in ("Rủi ro tiền tệ", "Rủi ro thanh khoản", "Giá trị hợp lý"):
        result = matcher.build_interest_rate_risk_variant_graph_document_v1(
            [_page([negative, *_table()])]
        )
        assert result["metrics"]["complete_region_count"] == 0


def test_missing_core_axis_parent_total_or_gap_rejects() -> None:
    for missing in (
        "Không chịu lãi suất",
        "Tổng tài sản",
        "Tổng nợ phải trả",
        "Mức chênh nhạy cảm với lãi suất nội bảng",
    ):
        result = matcher.build_interest_rate_risk_variant_graph_document_v1(
            [_page([text for text in _table() if text != missing])]
        )
        assert result["metrics"]["complete_region_count"] == 0


def test_two_separated_complete_regions_are_not_unique() -> None:
    result = matcher.build_interest_rate_risk_variant_graph_document_v1(
        [_page(_table(), 1), _page(["Trang đối chứng"], 2), _page(_table(), 3)]
    )
    assert result["uniqueness"] == {
        "complete_region_count": 2,
        "status": "NOT_UNIQUE_FULL_MATCH",
    }


def test_typed_tamper_rejects() -> None:
    result = matcher.build_interest_rate_risk_variant_graph_document_v1([_page(_table())])
    tampered = copy.deepcopy(result)
    tampered["metrics"]["complete_region_count"] = 1.0
    with pytest.raises(matcher.InterestRateRiskVariantGraphV1Error):
        matcher.validate_interest_rate_risk_variant_graph_document_v1(tampered)
