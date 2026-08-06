from __future__ import annotations

import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.deepseek_output import (
    DeepSeekOutputV2Error,
    parse_deepseek_ocr2_result_v2,
)
from bctc_ai.evaluation.reader_outputs_v2 import load_vlm_table_parser_config


def _config(project_root: Path):
    return load_vlm_table_parser_config(project_root / "config/tables/vlm-table-parser-v2.yaml")


def _result(raw_output: str) -> dict:
    return {
        "schema_version": 1,
        "state": "SEMANTIC_OCR_PROPOSAL_COMPLETE",
        "evidence_role": "SEMANTIC_AND_READING_ORDER_PROPOSAL_ONLY",
        "authority": {
            "mapping": False,
            "value": False,
            "period": False,
            "scope": False,
            "geometry": False,
            "confidence_promotion": False,
        },
        "raw_output": raw_output,
        "layout_references": [
            {
                "label": "table",
                "normalized_0_999_boxes": [[100.0, 200.0, 900.0, 800.0]],
                "status": "PROPOSAL_ONLY",
                "authority": "NONE_GEOMETRY_PROPOSAL_ONLY",
            }
        ],
    }


def test_deepseek_parser_reassembles_only_adjacent_label_then_value_fragment(
    project_root: Path, tmp_path: Path
):
    raw = (
        "<|ref|>table<|/ref|><|det|>[[100,200,900,800]]<|/det|>"
        "<table><tr><td></td><td>Thuyết minh</td><td>2024 triệu đồng</td>"
        "<td>2023 triệu đồng</td></tr>"
        "<tr><td>Một chỉ tiêu</td><td></td><td>1.234</td><td>(5.678)</td></tr>"
        "<tr><td colspan='4'>Tổng cộng</td></tr>"
        "<tr><td></td><td></td><td>9.999</td><td>8.888</td></tr></table>"
    )
    result_path = tmp_path / "ocr_result.json"
    result_path.write_text(json.dumps(_result(raw)), encoding="utf-8")

    parsed = parse_deepseek_ocr2_result_v2(
        result_path,
        _config(project_root),
        page_tag="deepseek-test",
    )

    assert parsed.table_bboxes_normalized_0_999 == ((100, 200, 900, 800),)
    assert [row.label for row in parsed.reader_rows] == ["Một chỉ tiêu", "Tổng cộng"]
    assert [[cell.raw_text for cell in row.cells] for row in parsed.reader_rows] == [
        ["1.234", "(5.678)"],
        ["9.999", "8.888"],
    ]
    assert len(parsed.fragment_merges) == 1
    assert parsed.fragment_merges[0].value_cells_unmodified is True
    assert parsed.fragment_merges[0].rule == ("ADJACENT_LABEL_ONLY_THEN_VALUE_ONLY_SAME_WIDTH")


def test_deepseek_parser_keeps_labeled_rows_separate(project_root: Path, tmp_path: Path):
    raw = (
        "<table><tr><td>Chỉ tiêu</td><td>Thuyết minh</td><td>2024</td><td>2023</td></tr>"
        "<tr><td>PHẦN A</td><td></td><td></td><td></td></tr>"
        "<tr><td>Dòng có nhãn</td><td></td><td>100</td><td>90</td></tr></table>"
    )
    result_path = tmp_path / "ocr_result.json"
    result_path.write_text(json.dumps(_result(raw)), encoding="utf-8")

    parsed = parse_deepseek_ocr2_result_v2(
        result_path,
        _config(project_root),
        page_tag="deepseek-test",
    )

    assert [row.label for row in parsed.reader_rows] == ["PHẦN A", "Dòng có nhãn"]
    assert parsed.fragment_merges == ()


def test_deepseek_parser_rejects_any_claimed_pipeline_authority(project_root: Path, tmp_path: Path):
    payload = _result(
        "<table><tr><td>Chỉ tiêu</td><td>TM</td><td>2024</td><td>2023</td></tr>"
        "<tr><td>Dòng</td><td></td><td>1</td><td>2</td></tr></table>"
    )
    payload["authority"]["value"] = True
    result_path = tmp_path / "ocr_result.json"
    result_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(DeepSeekOutputV2Error, match="forbidden authority"):
        parse_deepseek_ocr2_result_v2(
            result_path,
            _config(project_root),
            page_tag="deepseek-test",
        )
