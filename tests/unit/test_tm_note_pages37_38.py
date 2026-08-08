from __future__ import annotations

from datetime import date
from pathlib import Path

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.tables.tm_note_pages37_38 import (
    load_tm_fixed_asset_pages37_38_policy,
    parse_tm_fixed_asset_pages37_38,
)
from bctc_ai.tables.tm_note_word_box import TMNoteRowKind

_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_FIXTURES = {
    37: Path("tests/golden/tm/mbb-q1-2026-page-0037-ppocrv6-word-box.json"),
    38: Path("tests/golden/tm/mbb-q1-2026-page-0038-ppocrv6-word-box.json"),
}
_FIXTURE_HASHES = {
    37: "7f4102e6615284d5f7928a0cd4cde660781de9cdeb7e7830fd31b16c6ed33dd4",
    38: "b89286ba9a58056adf8703cb4feda569e0d064c0ef6b7970d82301a81d673c30",
}


def _parsed(project_root: Path, tmp_path: Path):
    renders = render_pages(
        project_root / _SOURCE_PDF,
        tmp_path / "render",
        dpi=300,
        page_numbers={37, 38},
    )
    return parse_tm_fixed_asset_pages37_38(
        {page: project_root / path for page, path in _FIXTURES.items()},
        {record.page: Path(record.path) for record in renders},
        load_tm_fixed_asset_pages37_38_policy(
            project_root / "config/tables/tm-note-pages37-38-v1.yaml"
        ),
    )


def test_real_pages37_38_reconstruct_exact_source_denominators(
    project_root: Path, tmp_path: Path
) -> None:
    assert {
        page: sha256_file(project_root / path) for page, path in _FIXTURES.items()
    } == _FIXTURE_HASHES

    parsed = _parsed(project_root, tmp_path)

    assert parsed.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert parsed.scope == "CONSOLIDATED"
    assert len(parsed.rows) == 35
    assert parsed.numeric_row_count == 29
    assert parsed.label_only_row_count == 6
    assert parsed.financial_slot_count == 145
    assert parsed.observation_count(ObservationKind.VALUE) == 130
    assert parsed.observation_count(ObservationKind.DASH) == 15
    assert parsed.mapping_authority is False

    q1, fy = parsed.panels
    assert (len(q1.rows), q1.numeric_row_count, q1.label_only_row_count) == (17, 14, 3)
    assert (q1.financial_slot_count, q1.observation_count(ObservationKind.VALUE)) == (70, 60)
    assert q1.observation_count(ObservationKind.DASH) == 10
    assert (len(fy.rows), fy.numeric_row_count, fy.label_only_row_count) == (18, 15, 3)
    assert (fy.financial_slot_count, fy.observation_count(ObservationKind.VALUE)) == (75, 70)
    assert fy.observation_count(ObservationKind.DASH) == 5
    assert q1.unassigned_numeric_line_indices == fy.unassigned_numeric_line_indices == ()
    assert q1.excluded_footer_numeric_line_indices == (95, 96, 97)
    assert fy.excluded_footer_numeric_line_indices == (104,)


def test_visible_four_class_axes_plus_total_bind_with_local_unit_and_panel_dates(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)

    for panel in parsed.panels:
        assert [axis.axis_role for axis in panel.axes] == [
            "BUILDINGS",
            "MACHINERY",
            "TRANSPORT",
            "OTHER_TANGIBLE",
            "TOTAL",
        ]
        assert [axis.is_total for axis in panel.axes] == [False, False, False, False, True]
        assert {axis.canonical_unit for axis in panel.axes} == {"VND"}
        assert {axis.unit_multiplier for axis in panel.axes} == {1_000_000}
        assert all(axis.header_line_indices and axis.unit_line_index >= 0 for axis in panel.axes)

    q1, fy = parsed.panels
    assert (q1.period_start, q1.period_end, q1.opening_date, q1.period_role) == (
        date(2026, 1, 1),
        date(2026, 3, 31),
        date(2025, 12, 31),
        "CURRENT",
    )
    assert (fy.period_start, fy.period_end, fy.opening_date, fy.period_role) == (
        date(2025, 1, 1),
        date(2025, 12, 31),
        date(2024, 12, 31),
        "COMPARATIVE",
    )
    assert q1.note_title_text is not None and q1.note_title_bbox is not None
    assert fy.note_title_text is None and fy.note_title_bbox is None


def test_values_periods_and_cross_panel_close_open_evidence_are_preserved(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)

    def row(panel_key: str, section: str, role: str):
        return next(
            item
            for item in parsed.rows
            if item.panel_key == panel_key and item.section_key == section and item.row_role == role
        )

    q1_gross_open = row("Q1_2026", "GROSS_COST", "OPENING")
    fy_gross_close = row("FY_2025", "GROSS_COST", "CLOSING")
    assert [cell.value for cell in q1_gross_open.row.cells] == [
        2_620_738,
        5_274_315,
        1_515_019,
        13_164,
        9_423_236,
    ]
    assert q1_gross_open.row.cells == fy_gross_close.row.cells
    assert (q1_gross_open.period_start, q1_gross_open.period_end) == (
        date(2025, 12, 31),
        date(2025, 12, 31),
    )
    assert (fy_gross_close.period_start, fy_gross_close.period_end) == (
        date(2025, 12, 31),
        date(2025, 12, 31),
    )

    q1_increase = row("Q1_2026", "GROSS_COST", "INCREASE")
    assert [cell.value for cell in q1_increase.row.cells] == [284, 33_312, 22_396, 395, 56_387]
    assert q1_increase.period_type == "DURATION"
    assert (q1_increase.period_start, q1_increase.period_end) == (
        date(2026, 1, 1),
        date(2026, 3, 31),
    )


def test_all_fifteen_visible_dashes_remain_nonzero_status_with_pixel_provenance(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    dash_cells = [
        (row, index, cell)
        for row in parsed.rows
        if row.row_kind is TMNoteRowKind.NUMERIC
        for index, cell in enumerate(row.row.cells)
        if cell.observation is ObservationKind.DASH
    ]

    assert len(dash_cells) == 15
    for row, index, cell in dash_cells:
        assert cell.value is None
        assert cell.normalized_text == "-"
        assert row.value_line_indices[index] == ()
        assert row.value_bboxes[index] is not None
        assert row.visual_cell_evidence[index] is not None
        assert row.visual_cell_evidence[index].observation == "DASH"


def test_table_policy_forbids_mapping_history_review_imputation_and_dash_zero(
    project_root: Path,
) -> None:
    policy = load_tm_fixed_asset_pages37_38_policy(
        project_root / "config/tables/tm-note-pages37-38-v1.yaml"
    )
    assert set(policy.forbidden_semantic_inputs) == {
        "missing_ocr_cell_as_dash_without_pixel_evidence",
        "template_labels_as_row_reconstruction_input",
        "approved_report_norm_id_assignment",
        "historical_or_mongodb_values",
        "human_review_answers",
        "dash_as_zero",
        "accounting_equations_as_value_imputation",
    }
