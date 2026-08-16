from __future__ import annotations

from scripts.experiments.adaptive_accounting_table_geometry_v1 import (
    assign_numeric_row_v1,
    cluster_numeric_rows_v1,
    infer_numeric_column_centers_v1,
    median_text_height_v1,
    project_merged_header_tokens_v1,
    row_affinity_v1,
)


def _line(index: int, text: str, bbox: list[int]) -> dict[str, object]:
    return {"bbox": bbox, "source_line_index": index, "vietocr_text": text}


def _numeric(line: dict[str, object]) -> bool:
    return str(line["vietocr_text"]).replace(".", "").isdigit()


def _scaled(lines: list[dict[str, object]], factor: int) -> list[dict[str, object]]:
    return [
        {
            **line,
            "bbox": [coordinate * factor for coordinate in line["bbox"]],
        }
        for line in lines
    ]


def test_row_assignment_is_scale_invariant_and_uses_body_derived_lanes() -> None:
    lines = [
        _line(0, "31/12/2025", [620, 10, 750, 34]),
        _line(1, "31/12/2024", [820, 10, 950, 34]),
        _line(2, "Tiền gửi không kỳ hạn", [20, 100, 360, 132]),
        _line(3, "100", [650, 127, 750, 153]),
        _line(4, "90", [850, 126, 950, 152]),
        _line(5, "Tiền gửi có kỳ hạn", [20, 175, 340, 207]),
        _line(6, "200", [650, 177, 750, 203]),
        _line(7, "180", [850, 176, 950, 202]),
    ]
    for factor in (1, 2, 4):
        page = _scaled(lines, factor)
        values = assign_numeric_row_v1(
            page,
            label_boxes=[page[2]["bbox"]],
            is_numeric=_numeric,
            page_width=1000 * factor,
        )
        assert [line["source_line_index"] for line in values] == [3, 4]
        assert (
            len(
                infer_numeric_column_centers_v1(
                    page,
                    is_numeric=_numeric,
                    page_width=1000 * factor,
                )
            )
            == 2
        )


def test_wrapped_or_merged_label_boxes_form_one_row_band() -> None:
    lines = [
        _line(0, "Trái phiếu và chứng chỉ tiền gửi do", [20, 100, 430, 128]),
        _line(1, "các TCTD khác trong nước phát hành", [20, 127, 490, 155]),
        _line(2, "10.000", [650, 132, 750, 158]),
        _line(3, "9.000", [850, 131, 950, 157]),
        _line(4, "Hàng kế tiếp", [20, 190, 250, 218]),
        _line(5, "8.000", [650, 191, 750, 217]),
        _line(6, "7.000", [850, 190, 950, 216]),
    ]
    values = assign_numeric_row_v1(
        lines,
        label_boxes=[lines[0]["bbox"], lines[1]["bbox"]],
        is_numeric=_numeric,
        page_width=1000,
    )
    assert [line["source_line_index"] for line in values] == [2, 3]
    assert (
        row_affinity_v1(
            [lines[0]["bbox"], lines[1]["bbox"]],
            lines[5]["bbox"],
            median_text_height=median_text_height_v1(lines),
        )
        is None
    )


def test_adjacent_numeric_rows_do_not_collapse_under_dpi_scaling() -> None:
    lines = [
        _line(0, "A", [20, 100, 100, 124]),
        _line(1, "10", [650, 100, 720, 124]),
        _line(2, "9", [850, 101, 920, 125]),
        _line(3, "B", [20, 142, 100, 166]),
        _line(4, "20", [650, 142, 720, 166]),
        _line(5, "19", [850, 143, 920, 167]),
    ]
    for factor in (1, 3):
        page = _scaled(lines, factor)
        rows = cluster_numeric_rows_v1(
            page,
            is_numeric=_numeric,
            start_index=-1,
            stop_index=6,
            page_width=1000 * factor,
        )
        assert [[line["source_line_index"] for line in row] for row in rows] == [
            [1, 2],
            [4, 5],
        ]


def test_merged_header_prefers_word_boxes_and_has_explicit_order_only_fallback() -> None:
    word_bound = project_merged_header_tokens_v1(
        header_bbox=[600, 20, 980, 70],
        tokens=["31/12/2025", "31/12/2024"],
        column_centers=[700.0, 900.0],
        token_bboxes=[[620, 25, 760, 55], [820, 25, 960, 55]],
    )
    assert [item["column_ordinal"] for item in word_bound] == [0, 1]
    assert {item["geometry_status"] for item in word_bound} == {"WORD_BOX_PROJECTED_TO_BODY_COLUMN"}

    order_only = project_merged_header_tokens_v1(
        header_bbox=[600, 20, 980, 70],
        tokens=["Số cuối năm", "Số đầu năm"],
        column_centers=[700.0, 900.0],
    )
    assert [item["token"] for item in order_only] == ["Số cuối năm", "Số đầu năm"]
    assert {item["geometry_status"] for item in order_only} == {
        "ORDER_ONLY_PROJECTED_TO_BODY_COLUMN_REQUIRES_REPLAY"
    }
