from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/tangible_fixed_assets_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("intangible_fixed_assets_variant_graph_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
matcher = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = matcher
_SPEC.loader.exec_module(matcher)


def _page(texts: list[str], page_sequence: int = 1) -> dict[str, object]:
    return {
        "lines": [
            {
                "bbox": [20, index * 30, 600, index * 30 + 20],
                "semantic_text": text,
                "semantic_text_source": "FULL_DOCUMENT_FRESH_VIETOCR_TRANSFORMER",
                "source_line_index": index,
                "source_text": None,
                "vietocr_text": text,
            }
            for index, text in enumerate(texts)
        ],
        "page_sequence": page_sequence,
        "primary_numeric_authority": False,
    }


def _variant(
    owner: str = "TÀI SẢN CỐ ĐỊNH VÔ HÌNH", *, period: str = "30 tháng 06 năm 2026"
) -> list[str]:
    return [
        owner,
        f"Biến động trong kỳ kết thúc ngày {period}",
        "Triệu đồng",
        "Nguyên giá",
        "Số dư đầu kỳ",
        "1.000",
        "Mua trong kỳ",
        "100",
        "Thanh lý trong kỳ",
        "(20)",
        "Số dư cuối kỳ",
        "1.080",
        "Giá trị hao mòn lũy kế",
        "Số dư đầu kỳ",
        "400",
        "Khấu hao trong kỳ",
        "50",
        "Số dư cuối kỳ",
        "450",
        "Giá trị còn lại",
        "Tại ngày đầu kỳ",
        "600",
        "Tại ngày cuối kỳ",
        "630",
    ]


@pytest.mark.parametrize("owner", ["TÀI SẢN CỐ ĐỊNH VÔ HÌNH", "TSCĐ VÔ HÌNH"])
def test_shared_engine_accepts_intangible_owner_variants(owner: str) -> None:
    result = matcher.build_intangible_fixed_assets_variant_graph_document_v1(
        [_page(_variant(owner))]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["family_id"] == "INTANGIBLE_FIXED_ASSET_MOVEMENT"
    assert result["regions"][0]["layout"]["branch_roles"] == [
        "ACCUMULATED_DEPRECIATION",
        "CARRYING_VALUE",
        "COST",
    ]
    assert result["safety"]["bank_filename_note_or_page_used_as_matching_or_routing"] is False


def test_current_and_comparative_tables_remain_two_candidates_for_period_adjudication() -> None:
    result = matcher.build_intangible_fixed_assets_variant_graph_document_v1(
        [
            _page(_variant(period="30 tháng 06 năm 2026"), 1),
            _page(_variant(period="31 tháng 12 năm 2025"), 2),
        ]
    )

    assert result["status"] == "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
    assert result["metrics"]["complete_region_count"] == 2
    assert [region["owner"]["page_sequence"] for region in result["regions"]] == [1, 2]


def test_accounting_policy_and_other_information_are_negative_controls() -> None:
    result = matcher.build_intangible_fixed_assets_variant_graph_document_v1(
        [
            _page(
                [
                    "Tài sản cố định vô hình",
                    "Tài sản cố định vô hình được ghi nhận theo nguyên giá trừ hao mòn lũy kế",
                    "Các thông tin khác về tài sản cố định vô hình",
                    "Nguyên giá tài sản cố định vô hình đã hao mòn hết nhưng vẫn còn sử dụng",
                ]
            )
        ]
    )

    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert result["metrics"]["complete_region_count"] == 0
    assert result["metrics"]["near_region_count"] == 1


def test_reporting_period_profile_accepts_annual_and_split_headers() -> None:
    texts = [
        "TÀI SẢN CỐ ĐỊNH VÔ",
        "HÌNH",
        "Cho năm kết thúc ngày 31 tháng 12 năm 2025",
        "Triệu đồng",
        "Nguyên",
        "giá",
        "Số dư đầu năm",
        "1.000",
        "Mua trong năm",
        "100",
        "Số dư cuối năm",
        "1.100",
        "Giá trị hao mòn",
        "lũy kế",
        "Số dư đầu năm",
        "400",
        "Khấu hao trong năm",
        "50",
        "Số dư cuối năm",
        "450",
        "Giá trị còn",
        "lại",
        "Số dư đầu năm",
        "600",
        "Số dư cuối năm",
        "650",
    ]

    current = matcher.build_intangible_fixed_assets_variant_graph_document_v1([_page(texts)])
    annual = matcher.build_intangible_fixed_assets_variant_graph_document_v1(
        [_page(texts)],
        variant_profile=matcher.INTANGIBLE_REPORTING_PERIOD_GENERAL_VARIANT_PROFILE,
    )

    assert current["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert annual["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert annual["format_version"] == "INTANGIBLE_FIXED_ASSETS_VARIANT_GRAPH_DOCUMENT_V2"


@pytest.mark.parametrize(
    "period",
    [
        "31/12/2024",
        "31.12.2025",
        "30 tháng 06 năm 2027",
        "30-09-2028",
    ],
)
def test_reporting_period_profile_is_not_bound_to_one_year_or_date_spelling(
    period: str,
) -> None:
    result = matcher.build_intangible_fixed_assets_variant_graph_document_v1(
        [_page(_variant(period=period))],
        variant_profile=matcher.INTANGIBLE_REPORTING_PERIOD_GENERAL_VARIANT_PROFILE,
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"


def test_reporting_period_profile_accepts_core_continuation_on_the_next_page() -> None:
    first_page = _page(
        [
            "TÀI SẢN CỐ ĐỊNH VÔ HÌNH",
            "Cho kỳ sáu tháng kết thúc ngày 30/09/2027",
            "Triệu đồng",
            "Nguyên giá",
            "Số dư đầu kỳ",
            "1.000",
            "Mua trong kỳ",
            "100",
            "Số dư cuối kỳ",
            "1.100",
        ],
        1,
    )
    continuation = _page(
        [
            "Giá trị hao mòn lũy kế",
            "Số dư đầu kỳ",
            "400",
            "Khấu hao trong kỳ",
            "50",
            "Số dư cuối kỳ",
            "450",
            "Giá trị còn lại",
            "Số dư đầu kỳ",
            "600",
            "Số dư cuối kỳ",
            "650",
        ],
        2,
    )

    result = matcher.build_intangible_fixed_assets_variant_graph_document_v1(
        [first_page, continuation],
        variant_profile=matcher.INTANGIBLE_REPORTING_PERIOD_GENERAL_VARIANT_PROFILE,
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["page_span"] == [1, 2]
    assert result["regions"][0]["layout"]["branch_order_verified"] is True


def test_reporting_period_profile_rejects_asset_class_column_as_owner() -> None:
    texts = [
        "TÀI SẢN CỐ ĐỊNH VÔ HÌNH",
        "Cho năm kết thúc ngày 31 tháng 12 năm 2025",
        "Triệu đồng",
        "Phần mềm",
        "Tài sản cố định",
        "vi tính",
        "vô hình khác",
        "Tổng cộng",
        "Nguyên giá",
        "Số dư đầu năm",
        "1.000",
        "Số dư cuối năm",
        "1.100",
        "Giá trị hao mòn lũy kế",
        "Số dư đầu năm",
        "400",
        "Số dư cuối năm",
        "450",
        "Giá trị còn lại",
        "Số dư đầu năm",
        "600",
        "Số dư cuối năm",
        "650",
    ]

    page = _page(texts)
    for index in range(3, 8):
        page["lines"][index]["bbox"] = [500, index * 30, 650, index * 30 + 20]
    result = matcher.build_intangible_fixed_assets_variant_graph_document_v1(
        [page],
        variant_profile=matcher.INTANGIBLE_REPORTING_PERIOD_GENERAL_VARIANT_PROFILE,
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["metrics"]["owner_candidate_count"] == 1
    assert result["regions"][0]["owner"]["source_line_index"] == 0


def test_intangible_exact_replay_rejects_coordinated_rehash() -> None:
    pages = [_page(_variant())]
    result = matcher.build_intangible_fixed_assets_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["layout"]["period_axis_line_count"] = 99
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "ifavgv1:result:" + matcher.canonical_json_sha256_v1(material)

    with pytest.raises(matcher.TangibleFixedAssetsVariantGraphV1Error, match="replay exactly"):
        matcher.validate_intangible_fixed_assets_variant_graph_replay_v1(forged, pages)
