from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/capital_and_funds_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("capital_and_funds_variant_graph_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
matcher = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = matcher
_SPEC.loader.exec_module(matcher)


def _page(texts: list[str], page_sequence: int = 1, *, rotated: bool = False) -> dict[str, object]:
    source = (
        "ROTATED_FRESH_VIETOCR_TRANSFORMER_RESCUE"
        if rotated
        else "FULL_DOCUMENT_FRESH_VIETOCR_TRANSFORMER"
    )
    return {
        "lines": [
            {
                "bbox": [50, index * 25, 750, index * 25 + 20],
                "semantic_text": text,
                "semantic_text_source": source,
                "source_line_index": index,
                "source_text": None,
                "vietocr_text": text,
            }
            for index, text in enumerate(texts)
        ],
        "page_sequence": page_sequence,
        "primary_numeric_authority": True,
    }


@pytest.mark.parametrize(
    "owner,heading,movements",
    [
        (
            "Vốn và các quỹ",
            "Báo cáo tình hình thay đổi vốn chủ sở hữu",
            ["Số dư đầu kỳ", "Tăng", "Giảm", "Số dư cuối kỳ"],
        ),
        (
            "Vốn và quỹ của Tổ chức tín dụng",
            "Báo cáo thay đổi vốn và các quỹ hợp nhất",
            ["Dư đầu", "Trích lập/Tăng", "Sử dụng/Giảm", "Dư cuối"],
        ),
    ],
)
def test_observed_layouts_share_one_generic_graph(
    owner: str, heading: str, movements: list[str]
) -> None:
    texts = [
        owner,
        heading,
        "Đơn vị: Triệu đồng",
        *movements,
        "Vốn điều lệ",
        "100",
        "100",
        "Thặng dư vốn cổ phần",
        "20",
        "20",
        "Quỹ dự phòng tài chính",
        "10",
        "2",
        "1",
        "11",
        "Lợi nhuận chưa phân phối",
        "30",
        "5",
        "4",
        "31",
        "Tổng cộng",
        "160",
        "7",
        "5",
        "162",
    ]
    result = matcher.build_capital_and_funds_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    roles = result["regions"][0]["layout"]["child_roles"]
    assert {"CAPITAL", "SHARE_PREMIUM", "FINANCIAL_RESERVE"}.issubset(roles)
    assert result["regions"][0]["pair_anchor_combinations"]


def test_optional_stock_and_eps_continue_on_next_page() -> None:
    first = _page(
        [
            "Vốn chủ sở hữu",
            "Tình hình thay đổi vốn chủ sở hữu",
            "Triệu VND",
            "Tại ngày 1 tháng 1 năm 2026",
            "Vốn điều lệ",
            "100",
            "Thặng dư vốn cổ phần",
            "20",
            "Quỹ dự trữ bổ sung vốn điều lệ",
            "10",
            "Lợi nhuận chưa phân phối",
            "30",
            "Lợi nhuận trong kỳ",
            "5",
            "Tại ngày 30 tháng 6 năm 2026",
            "100",
            "20",
            "10",
            "35",
            "165",
        ]
    )
    second = _page(
        [
            "Cổ phiếu",
            "Số lượng cổ phiếu đăng ký phát hành",
            "1.000",
            "1.000",
            "Lãi trên mỗi cổ phiếu",
            "500",
            "400",
        ],
        2,
    )
    result = matcher.build_capital_and_funds_variant_graph_document_v1([first, second])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["page_span"] == [1, 2]
    assert "SHARE_DETAIL_BRANCH" in result["regions"][0]["layout"]["child_roles"]


def test_same_transformer_rotation_is_a_layout_variant() -> None:
    texts = [
        "Vốn và quỹ",
        "Báo cáo tình hình thay đổi vốn chủ sở hữu",
        "Đơn vị: triệu đồng",
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
    result = matcher.build_capital_and_funds_variant_graph_document_v1([_page(texts, rotated=True)])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["metrics"]["rotated_rescue_line_count_in_complete_regions"] == len(texts)


def test_rotated_layout_may_reorder_complete_source_line_denominator() -> None:
    page = _page(
        [
            "Vốn và quỹ",
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
        ],
        rotated=True,
    )
    page["lines"] = [page["lines"][index] for index in [0, 1, *range(4, 19), 2, 3]]
    result = matcher.build_capital_and_funds_variant_graph_document_v1([page])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert sorted(event["source_line_index"] for event in result["regions"][0]["events"])


@pytest.mark.parametrize(
    "texts",
    [
        ["Vốn chủ sở hữu", "Vốn điều lệ", "100", "Lợi nhuận chưa phân phối", "20"],
        [
            "Vốn và các quỹ",
            "Báo cáo tình hình thay đổi vốn chủ sở hữu",
            "Triệu đồng",
            "Vốn điều lệ",
            "100",
            "100",
            "Thặng dư vốn cổ phần",
            "20",
            "20",
        ],
    ],
)
def test_policy_or_incomplete_table_is_negative_control(texts: list[str]) -> None:
    result = matcher.build_capital_and_funds_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"


def test_exact_replay_rejects_coordinated_tamper() -> None:
    pages = [
        _page(
            [
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
        )
    ]
    result = matcher.build_capital_and_funds_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["owner"]["page_sequence"] = 2
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "cafvgv1:graph:" + matcher.canonical_json_sha256_v1(material)
    with pytest.raises(matcher.CapitalAndFundsVariantGraphV1Error, match="replay exactly"):
        matcher.validate_capital_and_funds_variant_graph_replay_v1(forged, pages)
