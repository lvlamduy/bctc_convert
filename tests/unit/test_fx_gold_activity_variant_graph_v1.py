from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/fx_gold_activity_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("fx_gold_activity_variant_graph_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
matcher = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = matcher
_SPEC.loader.exec_module(matcher)


def _page(texts: list[str]) -> dict[str, object]:
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


def _split_gold_leading() -> list[str]:
    return [
        "(Lỗ)/Lãi thuần từ hoạt động kinh doanh ngoại hối",
        "3 tháng kết thúc ngày 31 tháng 3 năm 2026",
        "3 tháng kết thúc ngày 31 tháng 3 năm 2025",
        "Triệu đồng",
        "Thu nhập từ hoạt động kinh doanh ngoại hối",
        "106",
        "116",
        "Thu từ kinh doanh ngoại tệ giao ngay",
        "44",
        "93",
        "Thu từ kinh doanh vàng",
        "1",
        "2",
        "Thu từ các công cụ tài chính phái sinh tiền tệ",
        "61",
        "21",
        "Chi phí từ hoạt động kinh doanh ngoại hối",
        "(148)",
        "(104)",
        "Chi từ kinh doanh ngoại tệ giao ngay",
        "(38)",
        "(27)",
        "Chi về kinh doanh vàng",
        "(1)",
        "(1)",
        "Chi về các công cụ tài chính phái sinh tiền tệ",
        "(109)",
        "(76)",
        "(42)",
        "12",
        "Lãi thuần từ mua bán chứng khoán kinh doanh",
    ]


def test_split_gold_and_leading_parent_totals_form_one_graph() -> None:
    result = matcher.build_fx_gold_activity_variant_graph_document_v1(
        [_page(_split_gold_leading())]
    )
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    layout = result["regions"][0]["layout"]
    assert layout["income_parent_total_position"] == "LEADING_PARENT_TOTAL_BEFORE_CHILDREN"
    assert layout["expense_parent_total_position"] == "LEADING_PARENT_TOTAL_BEFORE_CHILDREN"
    assert "INCOME_GOLD" in layout["income_child_roles"]
    assert result["regions"][0]["pair_anchor_combinations"]


def test_combined_spot_gold_and_trailing_totals_use_same_graph() -> None:
    texts = [
        "Lãi thuần từ hoạt động kinh doanh ngoại hối",
        "Từ 01/01/2026 đến 30/06/2026",
        "Từ 01/01/2025 đến 30/06/2025",
        "Triệu đồng",
        "Thu nhập từ hoạt động kinh doanh ngoại hối",
        "Thu từ kinh doanh ngoại tệ giao ngay và vàng",
        "126",
        "195",
        "Thu từ các công cụ tài chính phái sinh tiền tệ",
        "302",
        "47",
        "428",
        "242",
        "Chi phí hoạt động kinh doanh ngoại hối",
        "Chi về kinh doanh ngoại tệ giao ngay và vàng",
        "(49)",
        "(38)",
        "Chi về các công cụ tài chính phái sinh tiền tệ",
        "(368)",
        "(97)",
        "(417)",
        "(135)",
        "Lãi thuần từ hoạt động kinh doanh ngoại hối",
        "11",
        "107",
        "Lãi thuần từ chứng khoán kinh doanh, chứng khoán đầu tư",
    ]
    result = matcher.build_fx_gold_activity_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    layout = result["regions"][0]["layout"]
    assert layout["income_parent_total_position"] == "TRAILING_UNLABELED_TOTAL_AFTER_CHILDREN"
    assert layout["expense_parent_total_position"] == "TRAILING_UNLABELED_TOTAL_AFTER_CHILDREN"
    assert "INCOME_SPOT_FX_AND_GOLD" in layout["income_child_roles"]


@pytest.mark.parametrize(
    "texts",
    [
        [
            "Lãi thuần từ hoạt động kinh doanh ngoại hối",
            "100",
            "90",
            "Lãi thuần từ mua bán chứng khoán kinh doanh",
        ],
        [
            "Các nghiệp vụ bằng ngoại tệ",
            "Chênh lệch tỷ giá hối đoái",
            "Tỷ giá một số ngoại tệ vào thời điểm cuối kỳ",
        ],
        [
            "Lãi thuần từ hoạt động kinh doanh ngoại hối",
            "Thu nhập từ hoạt động kinh doanh ngoại hối",
            "100",
            "Chi phí hoạt động kinh doanh ngoại hối",
            "(20)",
        ],
    ],
)
def test_statement_policy_and_incomplete_totals_are_negative_controls(
    texts: list[str],
) -> None:
    result = matcher.build_fx_gold_activity_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"


def test_exact_replay_rejects_coordinated_tamper() -> None:
    pages = [_page(_split_gold_leading())]
    value = matcher.build_fx_gold_activity_variant_graph_document_v1(pages)
    forged = copy.deepcopy(value)
    forged["regions"][0]["owner"]["page_sequence"] = 2
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "fxgav1:graph:" + matcher.canonical_json_sha256_v1(material)
    with pytest.raises(matcher.FxGoldActivityVariantGraphV1Error, match="replay exactly"):
        matcher.validate_fx_gold_activity_variant_graph_replay_v1(forged, pages)
