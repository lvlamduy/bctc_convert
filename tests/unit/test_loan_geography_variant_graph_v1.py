from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/loan_geography_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("loan_geography_variant_graph_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
graph = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = graph
_SPEC.loader.exec_module(graph)


def _page(
    rows: list[tuple[str, list[int]]],
    *,
    page_sequence: int = 1,
    primary_numeric_authority: bool = True,
) -> dict[str, object]:
    return {
        "lines": [
            {
                "bbox": bbox,
                "source_line_index": index,
                "source_text": None,
                "vietocr_text": text,
            }
            for index, (text, bbox) in enumerate(rows)
        ],
        "page_sequence": page_sequence,
        "primary_numeric_authority": primary_numeric_authority,
    }


def _row_layout(*, broad: bool = False) -> list[tuple[str, list[int]]]:
    loan = "Tổng dư nợ cho vay" if broad else "Tổng dư nợ cho vay khách hàng"
    return [
        (
            "MỨC ĐỘ TẬP TRUNG CỦA TÀI SẢN, CÔNG NỢ THEO KHU VỰC ĐỊA LÝ",
            [100, 100, 900, 130],
        ),
        ("30/06/2026", [500, 150, 620, 175]),
        ("Triệu đồng", [500, 175, 620, 200]),
        (loan, [500, 215, 720, 245]),
        ("Trong nước", [100, 270, 250, 300]),
        ("1.218.258.773", [510, 270, 690, 300]),
        ("Nước ngoài", [100, 320, 250, 350]),
        ("9.295.704", [530, 320, 680, 350]),
        ("4. Báo cáo bộ phận", [100, 410, 420, 440]),
    ]


def _column_layout(period: str, *, continued: bool = False) -> list[tuple[str, list[int]]]:
    suffix = " (tiếp theo)" if continued else ""
    return [
        (
            f"MỨC ĐỘ TẬP TRUNG CỦA TÀI SẢN, NỢ PHẢI TRẢ THEO KHU VỰC ĐỊA LÝ{suffix}",
            [100, 100, 900, 130],
        ),
        ("Trong nước", [550, 170, 680, 200]),
        ("Nước ngoài", [760, 170, 890, 200]),
        (period, [100, 210, 400, 240]),
        ("Triệu đồng", [550, 210, 680, 240]),
        ("Triệu đồng", [760, 210, 890, 240]),
        ("Cho vay khách hàng", [100, 290, 360, 320]),
        ("397.083.447", [550, 290, 680, 320]),
        ("-", [800, 290, 820, 320]),
    ]


def test_row_layout_split_axis_and_family_boundary_are_bound() -> None:
    rows = _row_layout()
    rows[3:4] = [
        ("Tổng dư nợ cho", [500, 205, 720, 230]),
        ("vay khách hàng", [500, 235, 720, 260]),
    ]
    result = graph.build_loan_geography_variant_graph_document_v1([_page(rows)])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    region = result["regions"][0]
    segment = region["segments"][0]
    assert segment["layout"] == "GEOGRAPHY_ROWS_ACCOUNTING_FAMILY_COLUMNS"
    assert segment["loan_axis"]["surface"] == "Tổng dư nợ cho vay khách hàng"
    assert segment["domestic"]["value_proposal"]["vietocr_text"] == "1.218.258.773"
    assert segment["foreign"]["value_proposal"]["vietocr_text"] == "9.295.704"
    assert region["cluster_boundary"]["next_numbered_boundary"]["surface"] == ("4. Báo cáo bộ phận")
    assert region["minimal_anchor"]["combination_size"] == 2


def test_column_layout_and_consecutive_period_continuation_are_one_region() -> None:
    pages = [
        _page(_column_layout("Tại ngày 30 tháng 06 năm 2026")),
        _page(
            _column_layout("Tại ngày 31 tháng 12 năm 2025", continued=True),
            page_sequence=2,
        ),
    ]
    result = graph.build_loan_geography_variant_graph_document_v1(pages)

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    region = result["regions"][0]
    assert len(region["segments"]) == 2
    assert region["cluster_boundary"]["first_page_sequence"] == 1
    assert region["cluster_boundary"]["last_page_sequence"] == 2
    for segment in region["segments"]:
        assert segment["layout"] == "GEOGRAPHY_COLUMNS_ACCOUNTING_FAMILY_ROWS"
        assert segment["domestic"]["value_proposal"]["vietocr_text"] == "397.083.447"
        assert segment["foreign"]["value_proposal"]["vietocr_text"] == "-"


def test_broad_total_loan_scope_and_segment_report_are_not_promoted() -> None:
    broad = _row_layout(broad=True)
    broad.extend(
        [
            (
                "(*) Tổng dư nợ cho vay bao gồm dư nợ cho vay khách hàng và dư nợ "
                "cho vay tổ chức tín dụng khác",
                [100, 470, 900, 500],
            )
        ]
    )
    segment = _page(
        [
            ("Báo cáo bộ phận theo khu vực địa lý", [100, 100, 700, 130]),
            ("Doanh thu", [100, 180, 300, 210]),
        ],
        page_sequence=2,
    )
    result = graph.build_loan_geography_variant_graph_document_v1([_page(broad), segment])

    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert result["metrics"]["near_region_count"] == 1
    assert result["near_regions"][0]["axis_scope"] == "BROAD_TOTAL_LOANS"
    assert result["near_regions"][0]["unresolved_reasons"] == [
        "LOAN_AXIS_SCOPE_BROADER_THAN_CUSTOMER_LOANS"
    ]
    assert result["metrics"]["segment_report_negative_control_count"] == 1


def test_missing_geography_child_and_multiple_regions_remain_unresolved() -> None:
    missing = _row_layout()
    missing = [row for row in missing if row[0] not in {"Nước ngoài", "9.295.704"}]
    result = graph.build_loan_geography_variant_graph_document_v1([_page(missing)])
    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert "MISSING_FOREIGN_GEOGRAPHY_CHILD" in result["near_regions"][0]["unresolved_reasons"]

    second = _row_layout()
    second[0] = (
        "MỨC ĐỘ TẬP TRUNG CỦA TÀI SẢN, CÔNG NỢ THEO VÙNG",
        second[0][1],
    )
    result = graph.build_loan_geography_variant_graph_document_v1(
        [_page(_row_layout()), _page(second, page_sequence=2)]
    )
    assert result["status"] == "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
    assert result["uniqueness"]["complete_region_count"] == 2


def test_exact_replay_and_bool_typing_reject_coordinated_tamper() -> None:
    pages = [_page(_row_layout())]
    result = graph.build_loan_geography_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["segments"][0]["layout"] = "FORGED"
    result_material = copy.deepcopy(forged)
    result_material.pop("result_id")
    forged["result_id"] = "lgvgv1:result:" + graph.canonical_json_sha256_v1(result_material)
    with pytest.raises(graph.LoanGeographyVariantGraphV1Error, match="replay exactly"):
        graph.validate_loan_geography_variant_graph_replay_v1(forged, pages)

    poisoned = _page(_row_layout())
    poisoned["primary_numeric_authority"] = 1
    with pytest.raises(graph.LoanGeographyVariantGraphV1Error, match="exact bool"):
        graph.build_loan_geography_variant_graph_document_v1([poisoned])
