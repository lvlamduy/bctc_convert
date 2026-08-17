from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/tangible_fixed_assets_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("tangible_fixed_assets_variant_graph_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
matcher = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = matcher
_SPEC.loader.exec_module(matcher)


def _page(
    texts: list[str],
    *,
    page_sequence: int = 1,
    rotated: bool = False,
) -> dict[str, object]:
    lines = []
    for index, text in enumerate(texts):
        if rotated:
            bbox = [100 + index * 30, 20, 120 + index * 30, 500]
            source = "ROTATED_FRESH_VIETOCR_TRANSFORMER_RESCUE"
        else:
            bbox = [20, index * 30, 500, index * 30 + 20]
            source = "FULL_DOCUMENT_FRESH_VIETOCR_TRANSFORMER"
        lines.append(
            {
                "bbox": bbox,
                "semantic_text": text,
                "semantic_text_source": source,
                "source_line_index": index,
                "source_text": None,
                "vietocr_text": text if not rotated else "1",
            }
        )
    return {
        "lines": lines,
        "page_sequence": page_sequence,
        "primary_numeric_authority": False,
    }


def _variant(*, optional_other: bool = True) -> list[str]:
    result = [
        "TÀI SẢN CỐ ĐỊNH HỮU HÌNH",
        "Biến động cho kỳ kết thúc ngày 30 tháng 06 năm 2026",
        "Triệu đồng",
        "Nguyên giá",
        "Số dư đầu kỳ",
        "1.000",
        "Mua trong kỳ",
        "100",
        "Thanh lý, nhượng bán",
        "(20)",
    ]
    if optional_other:
        result.extend(["Tăng/(Giảm) khác trong kỳ", "5"])
    result.extend(
        [
            "Số dư cuối kỳ",
            "1.085",
            "Hao mòn lũy kế",
            "Số dư đầu kỳ",
            "400",
            "Khấu hao trong kỳ",
            "50",
            "Thanh lý",
            "(10)",
            "Số dư cuối kỳ",
            "440",
            "Giá trị còn lại",
            "Tại ngày đầu kỳ",
            "600",
            "Tại ngày cuối kỳ",
            "645",
        ]
    )
    return result


def _annual_variant(year: int) -> list[str]:
    return [
        "TÀI SẢN CỐ ĐỊNH HỮU HÌNH",
        f"Biến động trong năm kết thúc ngày 31 tháng 12 năm {year}",
        "Triệu đồng",
        "Nguyên giá",
        "Số dư đầu năm",
        "1.000",
        "Mua trong năm",
        "100",
        "Thanh lý, nhượng bán",
        "(20)",
        "Số dư cuối năm",
        "1.080",
        "Giá trị hao mòn lũy kế",
        "Số đầu năm",
        "400",
        "Khấu hao trong năm",
        "50",
        "Thanh lý",
        "(10)",
        "Số cuối năm",
        "440",
        "Giá trị còn lại",
        "Số dư đầu năm",
        "600",
        "Số dư cuối năm",
        "640",
    ]


@pytest.mark.parametrize("optional_other", [False, True])
def test_one_generic_graph_accepts_optional_movements(optional_other: bool) -> None:
    result = matcher.build_tangible_fixed_assets_variant_graph_document_v1(
        [_page(_variant(optional_other=optional_other))]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    region = result["regions"][0]
    assert region["layout"]["branch_roles"] == [
        "ACCUMULATED_DEPRECIATION",
        "CARRYING_VALUE",
        "COST",
    ]
    assert region["layout"]["branch_order_verified"] is True
    assert region["pair_anchor_combinations"][0] == ["OWNER", "COST"]
    assert result["safety"]["bank_filename_note_or_page_used_as_matching_or_routing"] is False


def test_comparative_continuation_is_one_region_not_a_second_match() -> None:
    first = _page(_variant(), page_sequence=1)
    second = _page(
        [
            "Biến động cho kỳ kết thúc ngày 31 tháng 12 năm 2025",
            "Triệu đồng",
            "Nguyên giá",
            "Số dư đầu kỳ",
            "900",
            "Số dư cuối kỳ",
            "1.000",
            "Hao mòn lũy kế",
            "Số dư đầu kỳ",
            "300",
            "Số dư cuối kỳ",
            "400",
            "Giá trị còn lại",
            "Tại ngày đầu kỳ",
            "600",
            "Tại ngày cuối kỳ",
            "600",
        ],
        page_sequence=2,
    )
    result = matcher.build_tangible_fixed_assets_variant_graph_document_v1([first, second])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["page_span"] == [1, 2]
    assert (
        result["regions"][0]["layout"]["presentation"]
        == "CURRENT_TABLE_WITH_COMPARATIVE_CONTINUATION"
    )


def test_reporting_period_general_profile_accepts_annual_balance_labels() -> None:
    result = matcher.build_tangible_fixed_assets_variant_graph_document_v1(
        [
            _page(
                [
                    *_annual_variant(2025),
                    "Nguyên giá TSCĐ hữu hình đã khấu hao hết nhưng vẫn còn sử dụng",
                    "99",
                ]
            )
        ],
        variant_profile=matcher.REPORTING_PERIOD_GENERAL_VARIANT_PROFILE,
    )

    assert result["format_version"] == matcher.REPORTING_PERIOD_GENERAL_FORMAT_VERSION
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert {"OPENING", "ENDING", "PURCHASE", "DEPRECIATION"}.issubset(
        result["regions"][0]["layout"]["movement_roles"]
    )


def test_reporting_period_general_profile_derives_arbitrary_dates_chronologically() -> None:
    texts = [
        text.replace("30 tháng 06 năm 2026", "30 tháng 09 năm 2027")
        .replace("Số dư đầu kỳ", "Tại ngày 01/01/2027")
        .replace("Số dư cuối kỳ", "Tại ngày 30/09/2027")
        .replace("Tại ngày đầu kỳ", "Tại ngày 01/01/2027")
        .replace("Tại ngày cuối kỳ", "Tại ngày 30/09/2027")
        for text in _variant()
    ]
    result = matcher.build_tangible_fixed_assets_variant_graph_document_v1(
        [_page(texts)],
        variant_profile=matcher.REPORTING_PERIOD_GENERAL_VARIANT_PROFILE,
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert {"OPENING", "ENDING"}.issubset(result["regions"][0]["layout"]["movement_roles"])


def test_reporting_period_general_profile_selects_latest_local_table() -> None:
    result = matcher.build_tangible_fixed_assets_variant_graph_document_v1(
        [
            _page(_annual_variant(2025), page_sequence=1),
            _page(_annual_variant(2024), page_sequence=2),
        ],
        variant_profile=matcher.REPORTING_PERIOD_GENERAL_VARIANT_PROFILE,
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["owner"]["page_sequence"] == 1
    assert result["regions"][0]["layout"]["selected_as_latest_explicit_period"] is True
    comparison = next(
        region
        for region in result["near_regions"]
        if region["layout"].get("comparison_period_control") is True
    )
    assert comparison["owner"]["page_sequence"] == 2
    assert comparison["complete"] is False


def test_rotated_source_axis_uses_coordinates_not_broken_source_order() -> None:
    logical = _variant()
    # Raster provider order may put numbers first and the owner near the end.
    rotated_order = logical[5:14] + logical[:5] + logical[14:]
    page = _page(rotated_order, rotated=True)
    # Put the owner before branches in the rotated x-axis even though its source
    # line index follows the first numeric cells.
    owner_index = rotated_order.index("TÀI SẢN CỐ ĐỊNH HỮU HÌNH")
    cost_index = rotated_order.index("Nguyên giá")
    accumulated_index = rotated_order.index("Hao mòn lũy kế")
    carrying_index = rotated_order.index("Giá trị còn lại")
    page["lines"][owner_index]["bbox"] = [100, 20, 120, 500]
    page["lines"][cost_index]["bbox"] = [300, 20, 320, 500]
    page["lines"][accumulated_index]["bbox"] = [600, 20, 620, 500]
    page["lines"][carrying_index]["bbox"] = [900, 20, 920, 500]

    result = matcher.build_tangible_fixed_assets_variant_graph_document_v1([page])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    region = result["regions"][0]
    assert region["layout"]["rotated_source_axis"] is True
    assert region["layout"]["presentation"] == "ROTATED_VERTICAL_SOURCE_AXIS_MOVEMENT_GRID"


def test_narrative_main_statement_and_next_families_are_negative_controls() -> None:
    result = matcher.build_tangible_fixed_assets_variant_graph_document_v1(
        [
            _page(
                [
                    "Tài sản cố định hữu hình",
                    "Tài sản cố định hữu hình được ghi nhận theo nguyên giá",
                    "Tài sản cố định vô hình",
                    "Nguyên giá",
                    "Số dư đầu kỳ",
                    "100",
                    "Số dư cuối kỳ",
                    "100",
                    "Giá trị còn lại",
                    "100",
                ]
            )
        ]
    )

    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert result["metrics"]["complete_region_count"] == 0
    assert result["metrics"]["near_region_count"] == 1


def test_exact_replay_and_exact_types_fail_closed() -> None:
    pages = [_page(_variant())]
    result = matcher.build_tangible_fixed_assets_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["layout"]["period_axis_line_count"] = 99
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "tfavgv1:result:" + matcher.canonical_json_sha256_v1(material)
    with pytest.raises(matcher.TangibleFixedAssetsVariantGraphV1Error, match="replay exactly"):
        matcher.validate_tangible_fixed_assets_variant_graph_replay_v1(forged, pages)

    poisoned = _page(_variant())
    poisoned["primary_numeric_authority"] = 0
    with pytest.raises(matcher.TangibleFixedAssetsVariantGraphV1Error, match="exact bool"):
        matcher.build_tangible_fixed_assets_variant_graph_document_v1([poisoned])
