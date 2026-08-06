from __future__ import annotations

import json

from bctc_ai.evaluation.reader_outputs_v2 import (
    load_vlm_table_parser_config,
    parse_paddle_vl_page_v2,
)


def _write_page(tmp_path, blocks):
    path = tmp_path / "result.json"
    path.write_text(
        json.dumps({"input_path": "scan.png", "parsing_res_list": blocks}),
        encoding="utf-8",
    )
    return path


def _config(project_root):
    return load_vlm_table_parser_config(project_root / "config/tables/vlm-table-parser-v2.yaml")


def test_v2_parser_infers_optional_index_label_note_and_value_columns(project_root, tmp_path):
    path = _write_page(
        tmp_path,
        [
            {
                "block_label": "table",
                "block_bbox": [10, 20, 500, 600],
                "block_content": (
                    "<table><tr><td>STT</td><td>Chỉ tiêu</td><td>Thuyết minh</td>"
                    "<td>31/12/2025 Triệu VND</td><td>31/12/2024 Triệu VND</td></tr>"
                    "<tr><td>I</td><td>Tiền mặt, vàng bạc</td><td>4</td>"
                    "<td>15.542.769</td><td>14.268.064</td></tr></table>"
                ),
            }
        ],
    )

    page = parse_paddle_vl_page_v2(path, _config(project_root), page_tag="page-0001")

    table = page.tables[0]
    assert table.status == "PARSED"
    assert table.roles is not None
    assert table.roles.index_column == 0
    assert table.roles.label_column == 1
    assert table.roles.note_column == 2
    assert table.roles.value_columns == (3, 4)
    assert table.rows[0].row_code == "I"
    assert table.rows[0].row.label == "Tiền mặt, vàng bạc"
    assert table.rows[0].row.note_reference == "4"
    assert table.rows[0].row.source_row_ids == ("page-0001:table-1:grid-row-0001",)
    assert [cell.value for cell in table.rows[0].row.cells] == [15542769, 14268064]


def test_v2_parser_retains_header_only_block_and_inherits_roles_for_next_table(
    project_root, tmp_path
):
    path = _write_page(
        tmp_path,
        [
            {
                "block_label": "table",
                "block_bbox": [10, 20, 500, 70],
                "block_content": (
                    "<table><tr><td>STT</td><td>Chỉ tiêu</td><td>Thuyết minh</td>"
                    "<td>31/12/2025 Triệu VND</td><td>31/12/2024 Triệu VND</td>"
                    "</tr></table>"
                ),
            },
            {"block_label": "text", "block_content": "Các chỉ tiêu ngoài bảng"},
            {
                "block_label": "table",
                "block_bbox": [10, 100, 500, 300],
                "block_content": (
                    "<table><tr><td>1</td><td>Bảo lãnh vay vốn</td><td></td>"
                    "<td>5.884.776</td><td>286.899</td></tr></table>"
                ),
            },
        ],
    )

    page = parse_paddle_vl_page_v2(path, _config(project_root))

    assert [table.status for table in page.tables] == ["HEADER_ONLY", "PARSED"]
    assert page.tables[1].roles is not None
    assert page.tables[1].roles.inherited_from_table == 1
    assert page.tables[1].rows[0].row_code == "1"
    assert page.tables[1].rows[0].row.label == "Bảo lãnh vay vốn"
    assert "ngoài bảng" in page.context_text


def test_v2_parser_scans_past_colspan_context_and_does_not_duplicate_text(project_root, tmp_path):
    path = _write_page(
        tmp_path,
        [
            {
                "block_label": "table",
                "block_bbox": [10, 20, 500, 600],
                "block_content": (
                    "<table><tr><td colspan='5'>Ngân hàng thử nghiệm</td></tr>"
                    "<tr><td colspan='5'>Báo cáo tình hình tài chính (tiếp theo)</td></tr>"
                    "<tr><td>STT</td><td>Chỉ tiêu</td><td>Thuyết minh</td>"
                    "<td>31/12/2025 Triệu VND</td><td>31/12/2024 Triệu VND</td></tr>"
                    "<tr><td>B</td><td>NỢ PHẢI TRẢ</td><td></td><td></td><td></td>"
                    "</tr></table>"
                ),
            }
        ],
    )

    page = parse_paddle_vl_page_v2(path, _config(project_root))

    table = page.tables[0]
    assert table.roles is not None and table.roles.header_row_index == 2
    assert len(table.context_rows) == 2
    assert table.raw_grid[0] == ("Ngân hàng thử nghiệm", "", "", "", "")
    assert table.rows[0].row_code == "B"
    assert table.rows[0].row.label == "NỢ PHẢI TRẢ"


def test_v2_parser_uses_title_period_row_for_three_column_cash_flow(project_root, tmp_path):
    path = _write_page(
        tmp_path,
        [
            {
                "block_label": "table",
                "block_bbox": [10, 20, 500, 600],
                "block_content": (
                    "<table><tr><td>BÁO CÁO LƯU CHUYỂN TIỀN TỆ</td>"
                    "<td>Năm 2025 triệu đồng</td><td>Năm 2024 triệu đồng</td></tr>"
                    "<tr><td>Thu nhập lãi nhận được</td><td>100</td><td>90</td>"
                    "</tr></table>"
                ),
            }
        ],
    )

    page = parse_paddle_vl_page_v2(path, _config(project_root))

    table = page.tables[0]
    assert table.roles is not None
    assert table.roles.label_column == 0
    assert table.roles.value_columns == (1, 2)
    assert table.rows[0].row.label == "Thu nhập lãi nhận được"
    assert "BÁO CÁO LƯU CHUYỂN" in page.context_text


def test_v2_parser_rejects_concatenated_grouped_values(project_root, tmp_path):
    path = _write_page(
        tmp_path,
        [
            {
                "block_label": "table",
                "block_bbox": [10, 20, 500, 600],
                "block_content": (
                    "<table><tr><td>Chỉ tiêu</td><td>2025</td><td>2024</td></tr>"
                    "<tr><td>Dòng bị dính</td><td>3.645.303941.493</td><td>100</td>"
                    "</tr></table>"
                ),
            }
        ],
    )

    page = parse_paddle_vl_page_v2(path, _config(project_root))

    cell = page.tables[0].rows[0].row.cells[0]
    assert cell.observation.value == "INVALID"
    assert cell.reason == "inconsistent grouped-digit widths; possible concatenated values"


def test_v2_parser_expands_rowspan_as_traceable_rows_without_splitting_values(
    project_root, tmp_path
):
    path = _write_page(
        tmp_path,
        [
            {
                "block_label": "table",
                "block_bbox": [10, 20, 500, 600],
                "block_content": (
                    "<table><tr><td>STT</td><td>Chỉ tiêu</td><td>Thuyết minh</td>"
                    "<td>2025</td><td>2024</td></tr>"
                    "<tr><td rowspan='2'>12</td><td rowspan='2'>Chi phí thuế</td>"
                    "<td>33(a)</td><td>(7.842.997)</td><td>(8.526.496)</td></tr>"
                    "<tr><td>33(b)</td><td>(978.700)</td><td>143.478</td></tr>"
                    "</table>"
                ),
            }
        ],
    )

    page = parse_paddle_vl_page_v2(path, _config(project_root))

    table = page.tables[0]
    assert table.span_expansion_count == 2
    assert [row.row.label for row in table.rows] == ["Chi phí thuế", "Chi phí thuế"]
    assert [row.row.note_reference for row in table.rows] == ["33(a)", "33(b)"]
    assert [row.row.cells[0].value for row in table.rows] == [-7842997, -978700]


def test_v2_parser_retains_unresolved_table_instead_of_aborting_page(project_root, tmp_path):
    path = _write_page(
        tmp_path,
        [
            {
                "block_label": "table",
                "block_bbox": [10, 20, 500, 60],
                "block_content": "<table><tr><td>Heading without a body</td></tr></table>",
            }
        ],
    )

    page = parse_paddle_vl_page_v2(path, _config(project_root))

    assert page.unresolved_table_count == 1
    assert page.tables[0].status == "UNRESOLVED_COLUMN_ROLES"
    assert page.tables[0].raw_grid == (("Heading without a body",),)
