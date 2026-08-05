from __future__ import annotations

from datetime import date

from bctc_ai.axes.header_binding import bind_value_headers
from bctc_ai.core.contracts import BoundingBox, ObservationKind, RowType
from bctc_ai.core.text import normalize_text
from bctc_ai.ocr.pdf_text import PDFTextPage, PDFWord
from bctc_ai.rows.pdf_statement import financial_table_span, reconstruct_statement_rows
from bctc_ai.tables.geometry import (
    ColumnAxis,
    ColumnRole,
    GeometryConfig,
    PageGeometry,
    TextRun,
    analyze_page_geometry,
    build_text_runs,
    load_geometry_config,
)


def _word(
    text: str,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    block: int,
    line: int,
    number: int = 0,
) -> PDFWord:
    return PDFWord(
        raw_text=text,
        normalized_text=normalize_text(text),
        bbox_points=BoundingBox(x0, y0, x1, y1),
        block_number=block,
        line_number=line,
        word_number=number,
    )


def _page(words: list[PDFWord]) -> PDFTextPage:
    return PDFTextPage(
        page=1,
        width_points=600,
        height_points=800,
        rotation=0,
        words=words,
        text_quality="USABLE_TEXT_LAYER",
        corruption_markers=(),
    )


def _config(project_root) -> GeometryConfig:
    return load_geometry_config(project_root / "config/tables/geometry-v2.yaml")


def _single_axis_header_geometry(header: str) -> PageGeometry:
    run = TextRun(
        run_id="period-unit-header",
        raw_text=header,
        normalized_text=header,
        bbox=BoundingBox(480, 80, 550, 110),
        word_indices=(0,),
        block_number=1,
        line_number=0,
    )
    return PageGeometry(
        page=1,
        width_points=600,
        height_points=800,
        data_start_y=130,
        data_end_y=752,
        label_right_boundary=350,
        edge_tolerance=7.2,
        runs=(run,),
        axes=(ColumnAxis("value-1", ColumnRole.VALUE, 550, 500, 2, "test"),),
        unit_run_ids=(run.run_id,),
        warnings=(),
    )


def test_text_run_segmentation_separates_cells_inside_one_pdf_line():
    words = [
        _word("Tiền", 50, 200, 75, 210, 1, 0, 0),
        _word("mặt", 80, 200, 100, 210, 1, 0, 1),
        _word("5", 345, 200, 350, 210, 1, 0, 2),
        _word("1.000", 420, 200, 450, 210, 1, 0, 3),
        _word("900", 530, 200, 550, 210, 1, 0, 4),
    ]

    runs = build_text_runs(words, gap_height_factor=2.0)

    assert [run.raw_text for run in runs] == ["Tiền mặt", "5", "1.000", "900"]
    assert len({run.run_id for run in runs}) == 4


def test_close_financial_tokens_split_but_tight_digit_groups_stay_together():
    separate_columns = [
        _word("(28.930.618)", 390, 200, 447, 214, 1, 0, 0),
        _word("(14.449.250)", 467, 200, 524, 214, 1, 0, 1),
    ]
    spaced_thousands = [
        _word("12", 420, 220, 432, 234, 2, 0, 0),
        _word("345", 435, 220, 452, 234, 2, 0, 1),
    ]

    runs = build_text_runs(
        separate_columns + spaced_thousands,
        gap_height_factor=2.0,
        financial_gap_height_factor=0.5,
    )

    assert [run.raw_text for run in runs] == [
        "(28.930.618)",
        "(14.449.250)",
        "12 345",
    ]


def test_short_parenthetical_wrap_and_trailing_signatures_are_handled(project_root):
    words = [
        _word("31/12/2024", 400, 90, 450, 100, 1, 0),
        _word("31/12/2023", 500, 90, 550, 100, 2, 0),
        _word("Thuyết minh", 325, 115, 360, 125, 3, 0),
        _word("Triệu đồng", 405, 115, 450, 125, 4, 0),
        _word("Triệu đồng", 505, 115, 550, 125, 5, 0),
        _word("Tiền gửi tại Ngân hàng Nhà nước Việt Nam", 50, 165, 285, 175, 6, 0),
        _word('(“NHNN”)', 50, 178, 105, 188, 6, 1),
        _word("6", 345, 178, 350, 188, 7, 0),
        _word("54.353.153", 400, 178, 450, 188, 8, 0),
        _word("27.140.592", 500, 178, 550, 188, 9, 0),
        _word("Khoản mục tiếp theo", 50, 205, 160, 215, 10, 0),
        _word("1", 449, 205, 450, 215, 11, 0),
        _word("2", 549, 205, 550, 215, 12, 0),
        _word("Người lập", 50, 240, 100, 250, 13, 0),
        _word("Ông A", 515, 240, 550, 250, 14, 0),
    ]
    config = _config(project_root)

    rows = reconstruct_statement_rows(
        analyze_page_geometry(_page(words), config),
        config,
        table_id="parenthetical-wrap",
    )

    assert rows[0].label == 'Tiền gửi tại Ngân hàng Nhà nước Việt Nam ("NHNN")'
    assert len(rows[0].label_boxes) == 2
    assert rows[-1].cells[0].parsed.observation is ObservationKind.INVALID
    assert [row.label for row in financial_table_span(rows)] == [
        'Tiền gửi tại Ngân hàng Nhà nước Việt Nam ("NHNN")',
        "Khoản mục tiếp theo",
    ]


def test_geometry_reconstructs_note_values_wraps_and_section_rows(project_root):
    words = [
        _word("Ngày 31 tháng 12 năm 2025", 400, 90, 455, 100, 1, 0),
        _word("Ngày 31 tháng 3 năm 2026", 495, 90, 555, 100, 2, 0),
        _word("Thuyết minh", 325, 115, 360, 125, 3, 0),
        _word("Triệu đồng", 405, 115, 450, 125, 4, 0),
        _word("Triệu đồng", 505, 115, 550, 125, 5, 0),
        _word("TÀI SẢN", 50, 145, 110, 155, 6, 0),
        _word("Khoản mục rất dài phủ gần hết chiều rộng", 50, 170, 300, 180, 7, 0),
        _word("và xuống dòng", 50, 183, 135, 193, 7, 1),
        _word("12.1", 335, 183, 350, 193, 8, 0),
        _word("1.000", 420, 183, 450, 193, 9, 0),
        _word("900", 530, 183, 550, 193, 10, 0),
        _word("Khoản mục thứ hai", 50, 205, 145, 215, 11, 0),
        _word("2.000", 420, 205, 450, 215, 12, 0),
        _word("-", 545, 205, 550, 215, 13, 0),
        _word("Những thay đổi về tài sản", 50, 225, 245, 235, 14, 0),
        _word("Tăng khoản phải thu", 50, 238, 155, 248, 14, 1),
        _word("3.000", 420, 238, 450, 248, 15, 0),
        _word("1.500", 520, 238, 550, 248, 16, 0),
        _word("Ô cần đọc lại", 50, 260, 130, 270, 17, 0),
        _word("1O0", 430, 260, 450, 270, 18, 0),
        _word("100", 530, 260, 550, 270, 19, 0),
    ]
    config = _config(project_root)

    geometry = analyze_page_geometry(_page(words), config)
    rows = reconstruct_statement_rows(geometry, config, table_id="synthetic")

    assert [(axis.role, round(axis.right_edge)) for axis in geometry.axes] == [
        (ColumnRole.NOTE_REFERENCE, 350),
        (ColumnRole.VALUE, 450),
        (ColumnRole.VALUE, 550),
    ]
    assert rows[0].row_type is RowType.SECTION_HEADER
    assert rows[0].label == "TÀI SẢN"
    assert rows[1].label.endswith("và xuống dòng")
    assert len(rows[1].label_boxes) == 2
    assert rows[1].note_reference == "12.1"
    assert [cell.parsed.value for cell in rows[1].cells] == [1000, 900]
    assert rows[2].cells[1].parsed.observation is ObservationKind.DASH
    assert rows[3].row_type is RowType.SECTION_HEADER
    assert rows[3].label == "Những thay đổi về tài sản"
    assert rows[4].label == "Tăng khoản phải thu"
    assert rows[5].cells[0].raw_text == "1O0"
    assert rows[5].cells[0].parsed.observation is ObservationKind.INVALID
    assert rows[5].warnings == ("axis-aligned cell text is not a valid financial number",)


def test_header_binding_uses_semantics_and_dates_not_horizontal_order(project_root):
    config = _config(project_root)
    words = [
        _word("Ngày 31 tháng 12 năm 2025", 400, 90, 455, 100, 1, 0),
        _word("Ngày 31 tháng 3 năm 2026", 495, 90, 555, 100, 2, 0),
        _word("Triệu đồng", 405, 115, 450, 125, 3, 0),
        _word("Triệu đồng", 505, 115, 550, 125, 4, 0),
        _word("A", 50, 150, 60, 160, 5, 0),
        _word("1", 445, 150, 450, 160, 6, 0),
        _word("2", 545, 150, 550, 160, 7, 0),
        _word("B", 50, 170, 60, 180, 8, 0),
        _word("3", 445, 170, 450, 180, 9, 0),
        _word("4", 545, 170, 550, 180, 10, 0),
    ]

    bindings = bind_value_headers(analyze_page_geometry(_page(words), config), config)

    assert [binding.period_type for binding in bindings] == ["SNAPSHOT", "SNAPSHOT"]
    assert [binding.duration_months for binding in bindings] == [None, None]
    assert [binding.period_end for binding in bindings] == [
        date(2025, 12, 31),
        date(2026, 3, 31),
    ]
    assert [binding.current_or_comparative for binding in bindings] == [
        "COMPARATIVE",
        "CURRENT",
    ]


def test_duration_header_does_not_confuse_day_number_with_month_count(project_root):
    config = _config(project_root)
    geometry = _single_axis_header_geometry(
        "Cho kỳ kế toán 3 tháng kết thúc ngày 31 tháng 3 năm 2026 Triệu đồng"
    )

    binding = bind_value_headers(geometry, config)[0]

    assert binding.period_type == "DURATION"
    assert binding.duration_months == 3
    assert binding.period_start == date(2026, 1, 1)
    assert binding.period_end == date(2026, 3, 31)


def test_ytd_and_explicit_date_range_bind_period_start(project_root):
    config = _config(project_root)
    ytd = bind_value_headers(
        _single_axis_header_geometry("Lũy kế từ đầu năm đến ngày 30 tháng 9 năm 2026 Triệu đồng"),
        config,
    )[0]
    explicit = bind_value_headers(
        _single_axis_header_geometry(
            "Từ ngày 1 tháng 4 năm 2026 đến ngày 30 tháng 6 năm 2026 Triệu đồng"
        ),
        config,
    )[0]

    assert (ytd.period_type, ytd.period_start, ytd.period_end, ytd.duration_months) == (
        "YTD",
        date(2026, 1, 1),
        date(2026, 9, 30),
        9,
    )
    assert (
        explicit.period_type,
        explicit.period_start,
        explicit.period_end,
        explicit.duration_months,
    ) == ("DURATION", date(2026, 4, 1), date(2026, 6, 30), 3)
