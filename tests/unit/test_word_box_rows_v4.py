from __future__ import annotations

import json

import pytest

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.evaluation.word_box_rows import WordBoxReconstructionError
from bctc_ai.evaluation.word_box_rows_v3 import parse_ppocrv6_word_box_page_v3
from bctc_ai.evaluation.word_box_rows_v4 import (
    load_word_box_reconstruction_v4_config,
    parse_ppocrv6_word_box_page_v4,
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
    return load_word_box_reconstruction_v4_config(
        project_root / "config/tables/word-box-reconstruction-v4.yaml"
    )


def _distant_note_fixture():
    return [
        ("31/03/2026", 1.0, [330, 10, 400, 22]),
        ("31/12/2025", 1.0, [530, 10, 600, 22]),
        ("Thuyết minh", 0.99, [180, 22, 220, 34]),
        ("triệu đồng", 0.99, [330, 22, 400, 34]),
        ("triệu đồng", 0.99, [530, 22, 600, 34]),
        ("Công cụ tài chính phái sinh", 0.99, [20, 61, 220, 73]),
        ("III.18", 0.99, [180, 60, 220, 72]),
        ("Cho vay khách hàng", 0.99, [20, 74, 160, 86]),
        ("100", 1.0, [375, 74, 400, 86]),
        ("90", 1.0, [580, 74, 600, 86]),
    ]


def test_v4_splits_distant_note_row_from_following_value_row(project_root, tmp_path):
    result = tmp_path / "ocr.json"
    _write_result(result, _distant_note_fixture())
    config = _config(project_root)

    v3 = parse_ppocrv6_word_box_page_v3(
        result, config.base, page_tag="page-0001"
    )
    v4 = parse_ppocrv6_word_box_page_v4(result, config, page_tag="page-0001")

    assert len(v3.rows) == 1
    assert v3.rows[0].row.label == (
        "Công cụ tài chính phái sinh Cho vay khách hàng"
    )
    assert [row.row.label for row in v4.rows] == [
        "Công cụ tài chính phái sinh",
        "Cho vay khách hàng",
    ]
    assert v4.rows[0].row.note_reference == "III.18"
    assert [cell.observation for cell in v4.rows[0].row.cells] == [
        ObservationKind.BLANK,
        ObservationKind.BLANK,
    ]
    assert [cell.value for cell in v4.rows[1].row.cells] == [100, 90]


def test_v4_preserves_same_line_note_value_attachment(project_root, tmp_path):
    lines = _distant_note_fixture()
    lines[5] = ("Cho vay khách hàng", 0.99, [20, 74, 160, 86])
    lines[6] = ("III.18", 0.99, [180, 74, 220, 86])
    del lines[7]
    result = tmp_path / "ocr.json"
    _write_result(result, lines)

    parsed = parse_ppocrv6_word_box_page_v4(
        result, _config(project_root), page_tag="page-0001"
    )

    assert len(parsed.rows) == 1
    assert parsed.rows[0].row.label == "Cho vay khách hàng"
    assert parsed.rows[0].row.note_reference == "III.18"
    assert [cell.value for cell in parsed.rows[0].row.cells] == [100, 90]


def test_v4_config_is_hash_bound_to_v3(project_root, tmp_path):
    source = project_root / "config/tables/word-box-reconstruction-v4.yaml"
    drifted = tmp_path / source.name
    drifted.write_text(
        source.read_text(encoding="utf-8").replace(
            "c1cf55a6187a1b2a6f54b74b1566619d046446bc3ad7e628473004103c5d0f7e",
            "0" * 64,
        ),
        encoding="utf-8",
    )
    base = project_root / "config/tables/word-box-reconstruction-v3.yaml"
    (tmp_path / base.name).write_bytes(base.read_bytes())

    with pytest.raises(WordBoxReconstructionError, match="base_config hash drifted"):
        load_word_box_reconstruction_v4_config(drifted)
