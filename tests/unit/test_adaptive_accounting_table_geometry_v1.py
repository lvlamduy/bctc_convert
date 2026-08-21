from __future__ import annotations

import pytest

from scripts.experiments.adaptive_accounting_table_geometry_v1 import (
    AdaptiveAccountingTableGeometryV1Error,
    assign_numeric_row_v1,
    assign_value_row_lanes_v1,
    build_multilevel_header_graph_v1,
    cluster_numeric_rows_v1,
    infer_numeric_column_centers_v1,
    median_text_height_v1,
    project_merged_header_tokens_v1,
    propose_missing_value_lane_regions_v1,
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


def test_missing_lane_does_not_borrow_a_touching_next_row_cell() -> None:
    lines = [
        _line(0, "A", [20, 60, 100, 94]),
        _line(1, "10", [650, 60, 720, 94]),
        _line(2, "9", [850, 60, 920, 94]),
        _line(3, "Target", [20, 100, 180, 134]),
        _line(4, "8", [850, 100, 920, 134]),
        _line(5, "Following", [20, 132, 180, 166]),
        _line(6, "7", [650, 130, 720, 164]),
        _line(7, "6", [850, 132, 920, 166]),
    ]

    values = assign_numeric_row_v1(
        lines,
        label_boxes=[lines[3]["bbox"]],
        is_numeric=_numeric,
        page_width=1000,
    )

    assert [line["source_line_index"] for line in values] == [4]

    bound = assign_value_row_lanes_v1(
        lines,
        label_boxes=[lines[3]["bbox"]],
        is_numeric=_numeric,
        page_width=1000,
    )
    assert [(item["column_ordinal"], item["line"]["source_line_index"]) for item in bound] == [
        (1, 4)
    ]

    proposals = propose_missing_value_lane_regions_v1(
        lines,
        label_boxes=[lines[3]["bbox"]],
        is_numeric=_numeric,
        page_width=1000,
        page_height=300,
    )
    assert len(proposals) == 1
    assert proposals[0]["column_ordinal"] == 0
    assert proposals[0]["visible_lane_ordinals"] == [1]
    assert proposals[0]["row_band_evidence"] == "VISIBLE_SIBLING_CELL_ROW_BAND"
    assert proposals[0]["geometry_status"] == (
        "BODY_GRID_MISSING_DETECTOR_CELL_PROPOSAL_REQUIRES_PIXEL_RECOGNITION"
    )
    left, top, right, bottom = proposals[0]["raw_pixel_bbox"]
    assert left < 685 < right
    assert 95 <= top < bottom <= 133
    # The proposed current-lane crop must not reach the following-row bbox.
    assert bottom < lines[6]["bbox"][3]


def test_complete_row_does_not_propose_detector_independent_regions() -> None:
    lines = [
        _line(0, "A", [20, 60, 100, 94]),
        _line(1, "10", [650, 60, 720, 94]),
        _line(2, "9", [850, 60, 920, 94]),
        _line(3, "B", [20, 110, 100, 144]),
        _line(4, "8", [650, 110, 720, 144]),
        _line(5, "7", [850, 110, 920, 144]),
    ]
    assert (
        propose_missing_value_lane_regions_v1(
            lines,
            label_boxes=[lines[3]["bbox"]],
            is_numeric=_numeric,
            page_width=1000,
            page_height=300,
        )
        == []
    )


def test_real_ctg_visible_dash_without_detector_box_is_recovered_from_grid() -> None:
    # Annual-2025 CTG p39.  The current-period dash at [1258,1413,1292,1447]
    # is visible on the page render but absent from the detector line axis.
    lines = [
        _line(36, "Tiền mặt bằng VND", [319, 1318, 570, 1349]),
        _line(37, "11.206.287", [1142, 1316, 1285, 1349]),
        _line(38, "9.605.071", [1386, 1317, 1513, 1345]),
        _line(39, "Tiền mặt bằng ngoại tệ", [317, 1347, 610, 1383]),
        _line(40, "1.349.621", [1157, 1349, 1284, 1379]),
        _line(41, "1.501.440", [1387, 1349, 1515, 1377]),
        _line(42, "Vàng tiền tệ", [318, 1381, 476, 1415]),
        _line(43, "12.488", [1196, 1379, 1290, 1415]),
        _line(44, "22.581", [1423, 1380, 1517, 1412]),
        _line(45, "Vàng phi tiền tệ", [319, 1413, 521, 1447]),
        _line(46, "17", [1476, 1411, 1520, 1445]),
        _line(47, "Kim loại quý, đá quý khác", [318, 1445, 642, 1477]),
        _line(48, "15.088", [1196, 1441, 1289, 1477]),
        _line(49, "18.440", [1424, 1443, 1518, 1476]),
        _line(50, "12.583.484", [1143, 1508, 1287, 1539]),
        _line(51, "11.147.549", [1371, 1507, 1516, 1538]),
    ]
    target = next(line for line in lines if line["source_line_index"] == 45)
    proposals = propose_missing_value_lane_regions_v1(
        lines,
        label_boxes=[target["bbox"]],
        is_numeric=_numeric,
        page_width=1654,
        page_height=2339,
        retain_singleton_columns=True,
    )
    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal["column_ordinal"] == 0
    assert proposal["visible_lane_ordinals"] == [1]
    left, top, right, bottom = proposal["raw_pixel_bbox"]
    assert left <= 1258 < 1292 <= right
    assert top <= 1413 < bottom
    assert bottom <= 1445


def test_resolved_exclusive_grid_does_not_reborrow_an_adjacent_row_cell() -> None:
    # The target row's current-period dash has no detector cell.  The next
    # row's current-period number slightly overlaps the target label band, so
    # an independent affinity pass incorrectly considers both lanes visible.
    lines = [
        _line(0, "Tiền mặt bằng VND", [319, 1308, 570, 1350]),
        _line(1, "11.206.287", [1139, 1308, 1288, 1350]),
        _line(2, "9.605.071", [1383, 1313, 1516, 1347]),
        _line(3, "Vàng phi tiền tệ", [319, 1413, 521, 1447]),
        _line(4, "17", [1477, 1411, 1519, 1445]),
        _line(5, "Kim loại quý, đá quý khác", [318, 1440, 642, 1476]),
        _line(6, "15.088", [1194, 1440, 1290, 1476]),
        _line(7, "18.440", [1423, 1440, 1519, 1476]),
    ]
    target = lines[3]

    assert (
        propose_missing_value_lane_regions_v1(
            lines,
            label_boxes=[target["bbox"]],
            is_numeric=_numeric,
            page_width=1654,
            page_height=2339,
        )
        == []
    )

    proposals = propose_missing_value_lane_regions_v1(
        lines,
        label_boxes=[target["bbox"]],
        is_numeric=_numeric,
        page_width=1654,
        page_height=2339,
        resolved_column_centers=(1220.5, 1461.0),
        resolved_visible_value_cells=({"bbox": lines[4]["bbox"], "column_ordinal": 1},),
    )

    assert len(proposals) == 1
    assert proposals[0]["column_ordinal"] == 0
    assert proposals[0]["visible_lane_ordinals"] == [1]
    left, top, right, bottom = proposals[0]["raw_pixel_bbox"]
    assert left <= 1258 < 1292 <= right
    assert top <= 1413 < bottom <= 1445


def test_resolved_missing_lane_grid_rejects_partial_or_typed_forgery() -> None:
    lines = [
        _line(0, "Target", [20, 100, 180, 134]),
        _line(1, "8", [850, 100, 920, 134]),
    ]
    with pytest.raises(
        AdaptiveAccountingTableGeometryV1Error,
        match="requires both centers and visible cells",
    ):
        propose_missing_value_lane_regions_v1(
            lines,
            label_boxes=[lines[0]["bbox"]],
            is_numeric=_numeric,
            page_width=1000,
            page_height=300,
            resolved_column_centers=(685.0, 885.0),
        )
    with pytest.raises(
        AdaptiveAccountingTableGeometryV1Error,
        match="visible value-cell binding",
    ):
        propose_missing_value_lane_regions_v1(
            lines,
            label_boxes=[lines[0]["bbox"]],
            is_numeric=_numeric,
            page_width=1000,
            page_height=300,
            resolved_column_centers=(685.0, 885.0),
            resolved_visible_value_cells=({"bbox": lines[1]["bbox"], "column_ordinal": True},),
        )


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
