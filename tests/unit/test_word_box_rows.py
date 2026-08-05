from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.evaluation.word_box_rows import parse_ppocrv6_word_box_page


def _line(text, score, box):
    return text, score, box


def _payload(path: Path):
    lines = [
        _line("Thuyết minh", 0.99, [120, 10, 200, 20]),
        _line("2024", 1.0, [260, 10, 300, 20]),
        _line("2023", 1.0, [360, 10, 400, 20]),
        _line("triệu đồng", 0.99, [250, 18, 300, 28]),
        _line("triệu đồng", 0.99, [350, 18, 400, 28]),
        _line("SECTION", 0.99, [10, 40, 90, 52]),
        _line("Adjacent row one", 0.99, [10, 70, 140, 82]),
        _line("100", 1.0, [275, 72, 300, 84]),
        _line("90", 1.0, [380, 72, 400, 84]),
        _line("Adjacent row two", 0.99, [10, 80, 140, 92]),
        _line("200", 1.0, [275, 86, 300, 98]),
        _line("190", 1.0, [375, 86, 400, 98]),
        _line("PARENT HEADING", 0.99, [10, 108, 120, 120]),
        _line("A wrapped financial label", 0.99, [10, 132, 180, 144]),
        _line("continued text", 0.99, [10, 141, 100, 153]),
        _line("30", 1.0, [185, 142, 200, 154]),
        _line("(", 0.95, [265, 142, 270, 154]),
        _line("5.140.484", 1.0, [270, 142, 295, 154]),
        _line(")", 0.95, [295, 142, 300, 154]),
        _line("52.664", 1.0, [370, 142, 400, 154]),
        _line("Prepared by", 0.99, [10, 165, 100, 177]),
        _line("0100230800", 1.0, [250, 260, 300, 272]),
        _line("Signatory", 0.99, [10, 260, 100, 272]),
    ]
    path.write_text(
        json.dumps(
            {
                "input_path": "page.png",
                "rec_texts": [line[0] for line in lines],
                "rec_scores": [line[1] for line in lines],
                "rec_boxes": [line[2] for line in lines],
            }
        ),
        encoding="utf-8",
    )


def _config():
    return {
        "version": 1,
        "minimum_period_headers": 2,
        "body_start_line_heights_after_period_header": 0.75,
        "table_block_gap_line_heights": 1.8,
        "axis_right_edge_max_distance_ratio": 0.65,
        "row_anchor_cluster_line_heights": 0.55,
        "label_direct_attach_line_heights": 1.1,
        "label_below_anchor_tolerance_line_heights": 0.35,
        "wrapped_label_center_gap_line_heights": 0.95,
        "note_attach_line_heights": 1.1,
        "dash_search_width_line_heights": 1.5,
        "dash_search_right_padding_line_heights": 0.25,
        "dash_search_half_height_line_heights": 0.55,
        "dash_component_center_tolerance_line_heights": 0.40,
        "dash_min_width_line_heights": 0.12,
        "dash_max_width_line_heights": 0.60,
        "dash_min_height_line_heights": 0.04,
        "dash_max_height_line_heights": 0.30,
        "dash_min_aspect_ratio": 1.40,
        "dash_min_fill_ratio": 0.25,
        "dash_min_component_area_line_heights_squared": 0.004,
        "dash_min_foreground_contrast": 25,
        "minimum_line_score": 0.0,
    }


def test_geometry_reconstruction_separates_adjacent_rows_and_keeps_parent_context(tmp_path):
    result = tmp_path / "result.json"
    _payload(result)

    parsed = parse_ppocrv6_word_box_page(result, _config(), page_tag="page-0001")

    assert [proposal.row.label for proposal in parsed.rows] == [
        "SECTION",
        "Adjacent row one",
        "Adjacent row two",
        "PARENT HEADING",
        "A wrapped financial label continued text",
    ]
    assert [cell.value for cell in parsed.rows[1].row.cells] == [100, 90]
    assert [cell.value for cell in parsed.rows[2].row.cells] == [200, 190]
    assert parsed.rows[4].row.note_reference == "30"
    assert [cell.value for cell in parsed.rows[4].row.cells] == [-5140484, 52664]
    assert [row.row.label for row in parsed.trailing_context_rows] == ["Prepared by"]
    assert parsed.excluded_after_table_line_indices == (21, 22)


def test_geometry_reconstruction_retains_multiple_numeric_tokens_as_invalid(tmp_path):
    result = tmp_path / "result.json"
    _payload(result)
    payload = json.loads(result.read_text())
    payload["rec_texts"][16:19] = ["198.242", "5.140.484", ""]
    result.write_text(json.dumps(payload), encoding="utf-8")

    parsed = parse_ppocrv6_word_box_page(result, _config(), page_tag="page-0001")

    cell = parsed.rows[-1].row.cells[0]
    assert cell.observation.value == "INVALID"
    assert cell.reason == "multiple financial numbers in one cell"


def test_geometry_reconstruction_normalizes_ocr_dash_alias(tmp_path):
    result = tmp_path / "result.json"
    _payload(result)
    payload = json.loads(result.read_text())
    payload["rec_texts"][7] = "一"
    result.write_text(json.dumps(payload), encoding="utf-8")

    parsed = parse_ppocrv6_word_box_page(result, _config(), page_tag="page-0001")

    assert parsed.rows[1].row.cells[0].observation is ObservationKind.DASH
    assert parsed.rows[1].row.label == "Adjacent row one"


def test_geometry_reconstruction_recovers_only_visibly_supported_dash(tmp_path):
    result = tmp_path / "result.json"
    _payload(result)
    payload = json.loads(result.read_text())
    payload["rec_texts"][7] = ""
    result.write_text(json.dumps(payload), encoding="utf-8")
    image_path = tmp_path / "page.png"
    image = np.full((300, 450), 255, dtype=np.uint8)
    cv2.line(image, (292, 78), (295, 78), 0, thickness=2, lineType=cv2.LINE_8)
    assert cv2.imwrite(str(image_path), image)

    parsed = parse_ppocrv6_word_box_page(
        result,
        _config(),
        page_tag="page-0001",
        source_image_path=image_path,
    )

    row = parsed.rows[1]
    assert row.row.cells[0].observation is ObservationKind.DASH
    assert row.visual_cell_evidence[0] is not None
    assert row.visual_cell_evidence[0].observation == "DASH"
    assert "constrained pixel evidence" in row.warnings[-1]


def test_geometry_reconstruction_does_not_invent_dash_in_empty_crop(tmp_path):
    result = tmp_path / "result.json"
    _payload(result)
    payload = json.loads(result.read_text())
    payload["rec_texts"][7] = ""
    result.write_text(json.dumps(payload), encoding="utf-8")
    image_path = tmp_path / "page.png"
    image = np.full((300, 450), 255, dtype=np.uint8)
    assert cv2.imwrite(str(image_path), image)

    parsed = parse_ppocrv6_word_box_page(
        result,
        _config(),
        page_tag="page-0001",
        source_image_path=image_path,
    )

    row = parsed.rows[1]
    assert row.row.cells[0].observation is ObservationKind.BLANK
    assert row.visual_cell_evidence[0] is None


def test_geometry_reconstruction_does_not_misread_digit_or_rule_as_dash(tmp_path):
    result = tmp_path / "result.json"
    _payload(result)
    payload = json.loads(result.read_text())
    payload["rec_texts"][7] = ""
    payload["rec_texts"][11] = ""
    result.write_text(json.dumps(payload), encoding="utf-8")
    image_path = tmp_path / "page.png"
    image = np.full((300, 450), 255, dtype=np.uint8)
    cv2.line(image, (294, 73), (294, 82), 0, thickness=2, lineType=cv2.LINE_8)
    cv2.line(image, (360, 92), (399, 92), 0, thickness=2, lineType=cv2.LINE_8)
    assert cv2.imwrite(str(image_path), image)

    parsed = parse_ppocrv6_word_box_page(
        result,
        _config(),
        page_tag="page-0001",
        source_image_path=image_path,
    )

    first_row = parsed.rows[1]
    second_row = parsed.rows[2]
    assert first_row.row.cells[0].observation is ObservationKind.BLANK
    assert second_row.row.cells[1].observation is ObservationKind.BLANK
    assert first_row.visual_cell_evidence[0] is None
    assert second_row.visual_cell_evidence[1] is None
