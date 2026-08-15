from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/tangible_fixed_assets_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("investment_property_variant_graph_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
matcher = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = matcher
_SPEC.loader.exec_module(matcher)


def _page(texts: list[str]) -> dict[str, object]:
    return {
        "lines": [
            {
                "bbox": [20, index * 25, 600, index * 25 + 20],
                "semantic_text": text,
                "semantic_text_source": "FULL_DOCUMENT_FRESH_VIETOCR_TRANSFORMER",
                "source_line_index": index,
                "source_text": None,
                "vietocr_text": text,
            }
            for index, text in enumerate(texts)
        ],
        "page_sequence": 1,
        "primary_numeric_authority": False,
    }


def _section(period: str) -> list[str]:
    return [
        f"Tình hình về bất động sản đầu tư cho kỳ kết thúc ngày {period} như sau",
        "Nhà cửa, vật kiến trúc",
        "Quyền sử dụng đất có thời hạn",
        "Tổng cộng",
        "Triệu đồng",
        "Nguyên giá",
        "Số dư đầu kỳ",
        "100",
        "200",
        "300",
        "Tăng trong kỳ",
        "10",
        "20",
        "30",
        "Số dư cuối kỳ",
        "110",
        "220",
        "330",
        "Giá trị hao mòn",
        "Số dư đầu kỳ",
        "40",
        "50",
        "90",
        "Tăng trong kỳ",
        "4",
        "5",
        "9",
        "Số dư cuối kỳ",
        "44",
        "55",
        "99",
        "Giá trị còn lại",
        "Số dư đầu kỳ",
        "60",
        "150",
        "210",
        "Số dư cuối kỳ",
        "66",
        "165",
        "231",
    ]


def test_same_page_period_partition_selects_latest_and_retains_comparison() -> None:
    result = matcher.build_investment_property_variant_graph_document_v1(
        [
            _page(
                [
                    "BẤT ĐỘNG SẢN ĐẦU TƯ",
                    *_section("30 tháng 06 năm 2026"),
                    *_section("31 tháng 12 năm 2025"),
                ]
            )
        ]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["metrics"] == {
        "comparison_region_count": 1,
        "complete_region_count": 1,
        "near_region_count": 0,
        "owner_candidate_count": 1,
    }
    region = result["regions"][0]
    assert region["period_end"] == [2026, 6, 30]
    assert region["comparison_controls"][0]["period_end"] == [2025, 12, 31]
    assert region["layout"]["branch_roles"] == [
        "ACCUMULATED_DEPRECIATION",
        "CARRYING_VALUE",
        "COST",
    ]


@pytest.mark.parametrize(
    "texts",
    [
        [
            "Bất động sản đầu tư",
            "Bất động sản đầu tư cho thuê được thể hiện theo nguyên giá trừ hao mòn lũy kế",
            "Nguyên giá ban đầu bao gồm giá mua và chi phí trực tiếp",
        ],
        [
            "Tài sản cố định và bất động sản đầu tư",
            "Khấu hao TSCĐ, bất động sản đầu tư",
            "30 tháng 06 năm 2026",
            "Triệu đồng",
            "100",
        ],
    ],
)
def test_accounting_policy_and_combined_expense_regions_are_negative_controls(
    texts: list[str],
) -> None:
    result = matcher.build_investment_property_variant_graph_document_v1([_page(texts)])

    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert result["metrics"]["complete_region_count"] == 0


def test_exact_replay_rejects_coordinated_period_rehash() -> None:
    pages = [_page(["Bất động sản đầu tư", *_section("30 tháng 06 năm 2026")])]
    result = matcher.build_investment_property_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["period_end"] = [2025, 12, 31]
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "ipavgv1:result:" + matcher.canonical_json_sha256_v1(material)

    with pytest.raises(matcher.TangibleFixedAssetsVariantGraphV1Error, match="replay exactly"):
        matcher.validate_investment_property_variant_graph_replay_v1(forged, pages)
