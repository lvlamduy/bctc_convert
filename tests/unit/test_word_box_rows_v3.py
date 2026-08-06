from __future__ import annotations

import json

import cv2
import numpy as np
import pytest

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.evaluation.word_box_rows import WordBoxReconstructionError
from bctc_ai.evaluation.word_box_rows_v2 import (
    load_word_box_reconstruction_v2_config,
    parse_ppocrv6_word_box_page_v2,
)
from bctc_ai.evaluation.word_box_rows_v3 import (
    load_word_box_reconstruction_v3_config,
    parse_ppocrv6_word_box_page_v3,
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


def _v2_config(project_root):
    return load_word_box_reconstruction_v2_config(
        project_root / "config/tables/word-box-reconstruction-v2.yaml"
    )


def _v3_config(project_root):
    return load_word_box_reconstruction_v3_config(
        project_root / "config/tables/word-box-reconstruction-v3.yaml"
    )


def _staggered_fixture():
    return [
        ("31/12/2025", 1.0, [530, 10, 600, 22]),
        ("31/03/2026", 1.0, [330, 22, 400, 34]),
        ("Thuyết", 0.99, [180, 22, 220, 34]),
        ("đã kiểm toán", 0.99, [520, 22, 600, 34]),
        ("minh", 0.99, [185, 34, 220, 46]),
        ("triệu đồng", 0.99, [330, 34, 400, 46]),
        ("triệu đồng", 0.99, [530, 34, 600, 46]),
        ("TÀI SẢN", 0.99, [20, 60, 130, 72]),
        ("Khoản mục", 0.99, [20, 82, 150, 94]),
        ("III.1", 0.99, [180, 82, 220, 94]),
        ("100", 1.0, [375, 82, 400, 94]),
        ("90", 1.0, [580, 82, 600, 94]),
    ]


def test_v3_accepts_bounded_staggered_headers_and_excludes_header_companions(
    project_root, tmp_path
):
    result = tmp_path / "ocr.json"
    _write_result(result, _staggered_fixture())

    with pytest.raises(WordBoxReconstructionError, match="period header axes"):
        parse_ppocrv6_word_box_page_v2(result, _v2_config(project_root), page_tag="page-0001")
    parsed = parse_ppocrv6_word_box_page_v3(result, _v3_config(project_root), page_tag="page-0001")

    assert [axis.raw_header for axis in parsed.axes] == ["31/03/2026", "31/12/2025"]
    assert [row.row.label for row in parsed.rows] == ["TÀI SẢN", "Khoản mục"]
    assert parsed.rows[1].row.note_reference == "III.1"
    assert [cell.value for cell in parsed.rows[1].row.cells] == [100, 90]
    assert all("minh" not in row.row.label for row in parsed.rows)


def test_v3_roman_note_anchor_prevents_blank_row_from_merging_into_next_row(project_root, tmp_path):
    lines = _staggered_fixture()[:7] + [
        ("Dòng có dấu gạch", 0.99, [20, 60, 150, 72]),
        ("III.18", 0.99, [180, 60, 220, 72]),
        ("Dòng sau", 0.99, [20, 82, 130, 94]),
        ("10", 1.0, [385, 82, 400, 94]),
        ("9", 1.0, [590, 82, 600, 94]),
    ]
    result = tmp_path / "ocr.json"
    _write_result(result, lines)
    image_path = tmp_path / "page.png"
    image = np.full((120, 650), 255, dtype=np.uint8)
    cv2.line(image, (399, 50), (399, 105), 0, thickness=2, lineType=cv2.LINE_8)
    cv2.line(image, (599, 50), (599, 105), 0, thickness=2, lineType=cv2.LINE_8)
    cv2.line(image, (392, 66), (395, 66), 0, thickness=2, lineType=cv2.LINE_8)
    cv2.line(image, (592, 66), (595, 66), 0, thickness=2, lineType=cv2.LINE_8)
    assert cv2.imwrite(str(image_path), image)

    parsed = parse_ppocrv6_word_box_page_v3(
        result,
        _v3_config(project_root),
        page_tag="page-0001",
        source_image_path=image_path,
    )

    assert [row.row.label for row in parsed.rows] == ["Dòng có dấu gạch", "Dòng sau"]
    first = parsed.rows[0]
    assert first.row.note_reference == "III.18"
    assert [cell.observation for cell in first.row.cells] == [
        ObservationKind.DASH,
        ObservationKind.DASH,
    ]
    assert all(evidence is not None for evidence in first.visual_cell_evidence)


def test_v3_still_rejects_unbounded_period_header_stagger(project_root, tmp_path):
    lines = _staggered_fixture()
    lines[1] = ("31/03/2026", 1.0, [330, 42, 400, 54])
    result = tmp_path / "ocr.json"
    _write_result(result, lines)

    with pytest.raises(WordBoxReconstructionError, match="period header axes"):
        parse_ppocrv6_word_box_page_v3(result, _v3_config(project_root), page_tag="page-0001")


def test_v3_config_is_hash_bound_to_v2(project_root, tmp_path):
    source = project_root / "config/tables/word-box-reconstruction-v3.yaml"
    drifted = tmp_path / source.name
    drifted.write_text(
        source.read_text(encoding="utf-8").replace(
            "3dc1ccb331c6601b8c23e59966feb84429f04e372c6961672949e6f9565e64ee",
            "0" * 64,
        ),
        encoding="utf-8",
    )
    base = project_root / "config/tables/word-box-reconstruction-v2.yaml"
    (tmp_path / base.name).write_bytes(base.read_bytes())

    with pytest.raises(WordBoxReconstructionError, match="base_config hash drifted"):
        load_word_box_reconstruction_v3_config(drifted)
