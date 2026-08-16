from __future__ import annotations

from scripts.experiments.adaptive_accounting_table_geometry_v1 import (
    assign_numeric_row_v1,
    build_multilevel_header_graph_v1,
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


def test_multilevel_header_graph_recovers_parent_spans_and_leaf_columns() -> None:
    headers = [
        _line(0, "31/12/2025", [550, 20, 770, 48]),
        _line(1, "31/12/2024", [850, 20, 1070, 48]),
        _line(2, "VND", [555, 58, 645, 86]),
        _line(3, "Ngoại tệ", [675, 58, 765, 86]),
        _line(4, "VND", [855, 58, 945, 86]),
        _line(5, "Ngoại tệ", [975, 58, 1065, 86]),
    ]
    graph = build_multilevel_header_graph_v1(
        headers,
        column_centers=[600.0, 720.0, 900.0, 1020.0],
        page_width=1200,
    )

    assert graph["status"] == "RESOLVED_GEOMETRY_GRAPH"
    by_text = {}
    for cell in graph["cells"]:
        by_text.setdefault(cell["text"], []).append(
            (cell["level_start"], cell["column_start"], cell["column_stop"])
        )
    assert by_text["31/12/2025"] == [(0, 0, 2)]
    assert by_text["31/12/2024"] == [(0, 2, 4)]
    assert by_text["VND"] == [(1, 0, 1), (1, 2, 3)]
    assert by_text["Ngoại tệ"] == [(1, 1, 2), (1, 3, 4)]
    assert len(graph["edges"]) == 4


def test_multilevel_header_graph_is_scale_invariant() -> None:
    headers = [
        _line(0, "Kỳ hiện tại", [550, 20, 770, 48]),
        _line(1, "Kỳ so sánh", [850, 20, 1070, 48]),
        _line(2, "Số tiền", [555, 58, 645, 86]),
        _line(3, "%", [675, 58, 765, 86]),
        _line(4, "Số tiền", [855, 58, 945, 86]),
        _line(5, "%", [975, 58, 1065, 86]),
    ]
    expected = [(0, 2), (2, 4), (0, 1), (1, 2), (2, 3), (3, 4)]
    for factor in (1, 3):
        graph = build_multilevel_header_graph_v1(
            _scaled(headers, factor),
            column_centers=[value * factor for value in (600.0, 720.0, 900.0, 1020.0)],
            page_width=1200 * factor,
        )
        assert [(cell["column_start"], cell["column_stop"]) for cell in graph["cells"]] == expected


def test_multilevel_header_without_word_boxes_is_never_silently_split() -> None:
    graph = build_multilevel_header_graph_v1(
        [
            {
                **_line(0, "merged provider text", [500, 20, 1100, 60]),
                "tokens": ["31/12/2025", "31/12/2024"],
            }
        ],
        column_centers=[650.0, 950.0],
        page_width=1200,
    )

    assert graph["status"] == "GEOMETRY_GRAPH_WITH_REPLAY_REQUIRED"
    assert [cell["text"] for cell in graph["cells"]] == ["31/12/2025", "31/12/2024"]
    assert [cell["column_start"] for cell in graph["cells"]] == [0, 1]
    assert graph["ambiguities"] == [
        {"kind": "MERGED_HEADER_ORDER_ONLY_WITHOUT_WORD_BOXES", "source_line_index": 0}
    ]


def test_stacked_same_span_is_exposed_not_forced_to_be_wrap_or_new_level() -> None:
    graph = build_multilevel_header_graph_v1(
        [
            _line(0, "Cho kỳ kết thúc", [580, 20, 760, 46]),
            _line(1, "31 tháng 12 năm 2025", [570, 52, 770, 78]),
        ],
        column_centers=[670.0],
        page_width=1000,
    )

    assert graph["status"] == "RESOLVED_GEOMETRY_GRAPH"
    assert graph["continuation_candidates"] == [
        {
            "lower_cell_id": "header-cell-0002-01",
            "relation": "STACKED_SAME_SPAN_TEXT_REQUIRES_SEMANTIC_DECISION",
            "upper_cell_id": "header-cell-0001-01",
        }
    ]


def test_real_mbb_four_lane_period_amount_percent_header_is_resolved() -> None:
    # Annual-2025 MBB p65: two period parents, each spanning amount and %.
    headers = [
        _line(73, "31/12/2025", [812, 1395, 959, 1427]),
        _line(74, "31/12/2024", [1215, 1395, 1365, 1433]),
        _line(75, "triệu đồng", [782, 1431, 916, 1470]),
        _line(76, "%", [1039, 1431, 1075, 1468]),
        _line(77, "triệu đồng", [1179, 1431, 1314, 1473]),
        _line(78, "%", [1455, 1435, 1490, 1471]),
    ]

    graph = build_multilevel_header_graph_v1(
        headers,
        column_centers=[833.0, 1035.0, 1232.0, 1450.0],
        page_width=1654,
    )

    assert graph["status"] == "RESOLVED_GEOMETRY_GRAPH"
    assert [
        (cell["text"], cell["column_start"], cell["column_stop"]) for cell in graph["cells"]
    ] == [
        ("31/12/2025", 0, 2),
        ("31/12/2024", 2, 4),
        ("triệu đồng", 0, 1),
        ("%", 1, 2),
        ("triệu đồng", 2, 3),
        ("%", 3, 4),
    ]
    assert len(graph["edges"]) == 4
