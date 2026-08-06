from __future__ import annotations

import json

import cv2
import numpy as np

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.evaluation.word_box_rows_v2 import (
    load_word_box_reconstruction_v2_config,
    parse_ppocrv6_word_box_page_v2,
)


def _write_result(path, lines):
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


def _config(project_root):
    return load_word_box_reconstruction_v2_config(
        project_root / "config/tables/word-box-reconstruction-v2.yaml"
    )


def test_v2_geometry_accepts_worded_period_headers_and_separates_index_band(project_root, tmp_path):
    lines = [
        ("STT Chỉ tiêu", 0.99, [10, 10, 100, 22]),
        ("Thuyết minh", 0.99, [160, 10, 200, 22]),
        ("Năm 2025", 0.99, [330, 10, 400, 22]),
        ("Năm 2024", 0.99, [530, 10, 600, 22]),
        ("A", 0.99, [10, 38, 20, 50]),
        ("TÀI SẢN", 0.99, [60, 38, 130, 50]),
        ("I", 0.99, [10, 60, 20, 72]),
        ("Tiền mặt, vàng bạc", 0.99, [60, 60, 145, 72]),
        ("15(d)", 0.99, [170, 68, 200, 80]),
        ("100", 1.0, [375, 68, 400, 80]),
        ("90", 1.0, [580, 68, 600, 80]),
        ("1", 0.99, [10, 82, 20, 94]),
        ("Khoản mục con", 0.99, [60, 82, 150, 94]),
        ("50", 1.0, [380, 94, 400, 106]),
        ("40", 1.0, [580, 94, 600, 106]),
        ("111", 0.70, [625, 94, 650, 106]),
    ]
    result = tmp_path / "ocr.json"
    _write_result(result, lines)

    parsed = parse_ppocrv6_word_box_page_v2(
        result,
        _config(project_root),
        page_tag="page-0001",
    )

    assert [axis.raw_header for axis in parsed.axes] == ["Năm 2025", "Năm 2024"]
    assert parsed.index_band is not None
    assert [row.row_code for row in parsed.rows] == ["A", "I", "1"]
    assert [row.row.label for row in parsed.rows] == [
        "TÀI SẢN",
        "Tiền mặt, vàng bạc",
        "Khoản mục con",
    ]
    assert parsed.rows[1].row.note_reference == "15(d)"
    assert [cell.value for cell in parsed.rows[1].row.cells] == [100, 90]
    assert parsed.unassigned_numeric_line_indices == (15,)
    assert [cell.value for cell in parsed.rows[2].row.cells] == [50, 40]


def test_v2_geometry_prefers_compact_period_axis_pair_over_report_metadata_dates(
    project_root, tmp_path
):
    lines = [
        ("tại ngày 31 tháng 12 năm 2025", 0.99, [20, 10, 180, 22]),
        ("ngày 31 tháng 12 năm 2014", 0.99, [400, 10, 600, 22]),
        ("31/12/2025", 0.99, [330, 32, 400, 44]),
        ("31/12/2024", 0.99, [530, 32, 600, 44]),
        ("Khoản mục", 0.99, [60, 60, 150, 72]),
        ("100", 1.0, [375, 60, 400, 72]),
        ("90", 1.0, [580, 60, 600, 72]),
    ]
    result = tmp_path / "ocr.json"
    _write_result(result, lines)

    parsed = parse_ppocrv6_word_box_page_v2(
        result,
        _config(project_root),
        page_tag="page-0001",
    )

    assert [axis.raw_header for axis in parsed.axes] == ["31/12/2025", "31/12/2024"]
    assert [cell.value for cell in parsed.rows[0].row.cells] == [100, 90]


def test_v2_geometry_uses_structural_anchor_to_check_two_ocr_blank_cells(project_root, tmp_path):
    lines = [
        ("STT Chỉ tiêu", 0.99, [10, 10, 100, 22]),
        ("Năm 2025", 0.99, [330, 10, 400, 22]),
        ("Năm 2024", 0.99, [530, 10, 600, 22]),
        ("A", 0.99, [10, 38, 20, 50]),
        ("TÀI SẢN", 0.99, [60, 38, 130, 50]),
        ("I", 0.99, [10, 60, 20, 72]),
        ("Dòng có hai dấu gạch", 0.99, [60, 60, 180, 72]),
        ("II", 0.99, [10, 82, 22, 94]),
        ("Dòng sau", 0.99, [60, 82, 130, 94]),
        ("10", 1.0, [385, 82, 400, 94]),
        ("9", 1.0, [590, 82, 600, 94]),
    ]
    result = tmp_path / "ocr.json"
    _write_result(result, lines)
    image_path = tmp_path / "page.png"
    image = np.full((130, 650), 255, dtype=np.uint8)
    cv2.line(image, (396, 66), (399, 66), 0, thickness=2, lineType=cv2.LINE_8)
    cv2.line(image, (596, 66), (599, 66), 0, thickness=2, lineType=cv2.LINE_8)
    assert cv2.imwrite(str(image_path), image)

    parsed = parse_ppocrv6_word_box_page_v2(
        result,
        _config(project_root),
        page_tag="page-0001",
        source_image_path=image_path,
    )

    row = next(item for item in parsed.rows if item.row_code == "I")
    assert [cell.observation for cell in row.row.cells] == [
        ObservationKind.DASH,
        ObservationKind.DASH,
    ]
    assert all(evidence is not None for evidence in row.visual_cell_evidence)


def test_v2_geometry_rejects_one_line_concatenated_grouped_value(project_root, tmp_path):
    lines = [
        ("Năm 2025", 0.99, [330, 10, 400, 22]),
        ("Năm 2024", 0.99, [530, 10, 600, 22]),
        ("Dòng bị dính", 0.99, [60, 40, 150, 52]),
        ("3.645.303941.493", 1.0, [300, 40, 400, 52]),
        ("100", 1.0, [575, 40, 600, 52]),
    ]
    result = tmp_path / "ocr.json"
    _write_result(result, lines)

    parsed = parse_ppocrv6_word_box_page_v2(
        result,
        _config(project_root),
        page_tag="page-0001",
    )

    cell = parsed.rows[0].row.cells[0]
    assert cell.observation is ObservationKind.INVALID
    assert cell.reason == "inconsistent grouped-digit widths; possible concatenated values"
