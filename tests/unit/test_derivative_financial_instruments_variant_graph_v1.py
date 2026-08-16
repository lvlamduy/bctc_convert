from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/derivative_financial_instruments_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "derivative_financial_instruments_variant_graph_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
graph = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = graph
_SPEC.loader.exec_module(graph)


def _page(
    surfaces: list[tuple[str, int, int]], *, primary_numeric_authority: bool = True
) -> dict[str, object]:
    return {
        "lines": [
            {
                "bbox": [x, y, x + (430 if x < 500 else 110), y + 24],
                "source_line_index": index,
                "source_text": text,
                "vietocr_text": text,
            }
            for index, (text, x, y) in enumerate(surfaces)
        ],
        "page_sequence": 1,
        "primary_numeric_authority": primary_numeric_authority,
    }


def _row(
    surfaces: list[tuple[str, int, int]],
    label: str,
    values: list[str],
    xs: list[int],
    y: int,
) -> None:
    surfaces.append((label, 0, y))
    surfaces.extend((value, x, y) for value, x in zip(values, xs, strict=True))


def _table(mode: str) -> list[tuple[str, int, int]]:
    modes = {
        "CONTRACT_ASSET_LIABILITY": (
            [
                ("Tổng giá trị của hợp đồng", 650, 35),
                ("Tài sản", 820, 60),
                ("Công nợ", 990, 60),
            ],
            [650, 820, 990],
        ),
        "ASSET_LIABILITY_NET": (
            [("Tài sản", 650, 60), ("Công nợ", 820, 60), ("Giá trị ròng", 990, 60)],
            [650, 820, 990],
        ),
        "CONTRACT_INFLOW_OUTFLOW_NET": (
            [
                ("Tổng giá trị hợp đồng", 570, 35),
                ("Dòng tiền vào", 710, 60),
                ("Dòng tiền ra", 850, 60),
                ("Giá trị thuần", 990, 60),
            ],
            [570, 710, 850, 990],
        ),
        "ASSET_LIABILITY": (
            [("Tài sản", 820, 60), ("Công nợ", 990, 60)],
            [820, 990],
        ),
        "CONTRACT_NET": (
            [("Tổng giá trị của hợp đồng", 740, 35), ("Sổ kế toán", 990, 60)],
            [740, 990],
        ),
    }
    headers, xs = modes[mode]
    surfaces = [
        ("CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÁC TÀI SẢN/CÔNG NỢ TÀI CHÍNH KHÁC", 0, 0),
        *headers,
        ("Tại ngày 30 tháng 06 năm 2026", 0, 95),
    ]
    values = [str(100 + index * 10) for index in range(len(xs))]
    _row(surfaces, "Công cụ tài chính phái sinh tiền tệ", values, xs, 130)
    _row(surfaces, "Giao dịch kỳ hạn tiền tệ", values, xs, 165)
    _row(surfaces, "Giao dịch hoán đổi tiền tệ", values, xs, 200)
    _row(surfaces, "Công cụ tài chính phái sinh khác", values, xs, 235)
    _row(surfaces, "Giao dịch hoán đổi lãi suất", values, xs, 270)
    surfaces.append(("Tại ngày 31 tháng 12 năm 2025", 0, 315))
    _row(surfaces, "Công cụ tài chính phái sinh tiền tệ", values, xs, 350)
    _row(surfaces, "Giao dịch kỳ hạn tiền tệ", values, xs, 385)
    _row(surfaces, "Giao dịch hoán đổi tiền tệ", values, xs, 420)
    _row(surfaces, "Công cụ tài chính phái sinh khác", values, xs, 455)
    _row(surfaces, "Giao dịch hoán đổi lãi suất", values, xs, 490)
    surfaces.append(("CHO VAY KHÁCH HÀNG", 0, 540))
    return surfaces


@pytest.mark.parametrize(
    "mode",
    [
        "CONTRACT_ASSET_LIABILITY",
        "ASSET_LIABILITY_NET",
        "CONTRACT_INFLOW_OUTFLOW_NET",
        "ASSET_LIABILITY",
        "CONTRACT_NET",
    ],
)
def test_shared_layout_variants_bind_boundary_periods_and_lanes(mode: str) -> None:
    result = graph.build_derivative_financial_instruments_variant_graph_document_v1(
        [_page(_table(mode))]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    region = result["regions"][0]
    assert region["layout"]["presentation_mode"] == mode
    assert len(region["layout"]["period_headings"]) == 2
    assert region["minimal_anchor"]["combination_size"] == 2
    assert region["cluster_boundary"]["first_item_role"] == (
        "DERIVATIVE_FINANCIAL_INSTRUMENTS_OWNER"
    )
    assert region["cluster_boundary"]["last_source_line_index"] < len(_table(mode)) - 1
    assert all(
        "lane_role" in value for event in region["events"] for value in event["value_proposals"]
    )


def test_policy_prose_and_one_period_surface_are_negative_controls() -> None:
    surfaces = [
        ("Các công cụ tài chính phái sinh và các tài sản tài chính khác", 0, 0),
        ("Các hợp đồng kỳ hạn tiền tệ được ghi nhận theo giá trị cam kết", 0, 40),
        ("Các hợp đồng hoán đổi tiền tệ là các cam kết mua và bán", 0, 80),
    ]
    result = graph.build_derivative_financial_instruments_variant_graph_document_v1(
        [_page(surfaces)]
    )

    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert result["regions"] == []


def test_latest_two_visible_dates_define_annual_current_and_comparative_axes() -> None:
    surfaces = [
        (
            "Tại ngày 31 tháng 12 năm 2025"
            if text == "Tại ngày 30 tháng 06 năm 2026"
            else "Tại ngày 31 tháng 12 năm 2024"
            if text == "Tại ngày 31 tháng 12 năm 2025"
            else text,
            x,
            y,
        )
        for text, x, y in _table("ASSET_LIABILITY")
    ]
    result = graph.build_derivative_financial_instruments_variant_graph_document_v1(
        [_page(surfaces)]
    )
    headings = result["regions"][0]["layout"]["period_headings"]
    assert [item["period_role"] for item in headings] == [
        "CURRENT_PERIOD",
        "COMPARATIVE_PERIOD",
    ]


def test_numbered_parent_and_numeric_looking_crop_are_retained_without_text_correction() -> None:
    surfaces = _table("ASSET_LIABILITY")
    parent_index = next(
        index
        for index, surface in enumerate(surfaces)
        if surface[0] == "Công cụ tài chính phái sinh khác"
    )
    surfaces[parent_index] = (
        "2 - Công cụ tài chính phái sinh lãi suất",
        surfaces[parent_index][1],
        surfaces[parent_index][2],
    )
    forward_index = next(
        index for index, surface in enumerate(surfaces) if surface[0] == "Giao dịch kỳ hạn tiền tệ"
    )
    forward_y = surfaces[forward_index][2]
    value_index = next(
        index
        for index, surface in enumerate(surfaces)
        if surface[1] >= 650 and surface[2] == forward_y
    )
    surfaces[value_index] = ("6,270,0ss", surfaces[value_index][1], forward_y)

    result = graph.build_derivative_financial_instruments_variant_graph_document_v1(
        [_page(surfaces)]
    )

    region = result["regions"][0]
    assert any(event["role"] == "OTHER_DERIVATIVE_PARENT" for event in region["events"])
    forward = next(event for event in region["events"] if event["role"] == "FORWARD_CURRENCY")
    assert forward["value_proposals"][0]["vietocr_text"] == "6,270,0ss"


def test_exact_replay_and_exact_bool_reject_coordinated_tamper() -> None:
    pages = [_page(_table("ASSET_LIABILITY"))]
    result = graph.build_derivative_financial_instruments_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["layout"]["presentation_mode"] = "CONTRACT_NET"
    region_material = copy.deepcopy(forged["regions"][0])
    region_material.pop("region_id")
    forged["regions"][0]["region_id"] = "dfigv1:region:" + (
        graph.canonical_json_sha256_v1(region_material)
    )
    result_material = copy.deepcopy(forged)
    result_material.pop("result_id")
    forged["result_id"] = "dfigv1:result:" + graph.canonical_json_sha256_v1(result_material)
    with pytest.raises(
        graph.DerivativeFinancialInstrumentsVariantGraphV1Error, match="replay exactly"
    ):
        graph.validate_derivative_financial_instruments_variant_graph_replay_v1(forged, pages)

    poisoned = _page(_table("ASSET_LIABILITY"), primary_numeric_authority=True)
    poisoned["primary_numeric_authority"] = 1
    with pytest.raises(graph.DerivativeFinancialInstrumentsVariantGraphV1Error, match="exact bool"):
        graph.build_derivative_financial_instruments_variant_graph_document_v1([poisoned])
