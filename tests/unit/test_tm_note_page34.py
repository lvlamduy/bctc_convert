from __future__ import annotations

from datetime import date
from pathlib import Path

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.tables.tm_note_page34 import load_tm_page34_policy, parse_tm_page34

_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0034-ppocrv6-word-box.json")
_FIXTURE_SHA256 = "9027f65ff1b8df868fbf726205fb05506f71dd39361ba8c01dc73b42b1d5bebb"
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")


def _parsed(project_root: Path, tmp_path: Path):
    render = Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={34},
        )[0].path
    )
    return parse_tm_page34(
        project_root / _FIXTURE,
        render,
        load_tm_page34_policy(project_root / "config/tables/tm-note-page34-v1.yaml"),
    )


def test_real_page34_reconstructs_exact_eleven_row_nine_axis_source_denominator(
    project_root: Path, tmp_path: Path
) -> None:
    assert sha256_file(project_root / _FIXTURE) == _FIXTURE_SHA256

    parsed = _parsed(project_root, tmp_path)

    assert parsed.source_sha256 == _FIXTURE_SHA256
    assert parsed.source_render_sha256 == (
        "b6f470789dcf3c342d8011c4f6faaeca159dc7df49afba07d076860ec03ed7fe"
    )
    assert parsed.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert parsed.scope == "CONSOLIDATED"
    assert parsed.note_number == "6"
    assert len(parsed.rows) == parsed.numeric_row_count == 11
    assert parsed.financial_slot_count == 99
    assert parsed.observation_count(ObservationKind.VALUE) == 80
    assert parsed.observation_count(ObservationKind.DASH) == 19
    assert parsed.excluded_footer_numeric_line_indices == (143,)
    assert parsed.mapping_authority is False

    q1, fy = parsed.panels
    assert (len(q1.rows), q1.financial_slot_count) == (5, 45)
    assert q1.observation_count(ObservationKind.VALUE) == 37
    assert q1.observation_count(ObservationKind.DASH) == 8
    assert (len(fy.rows), fy.financial_slot_count) == (6, 54)
    assert fy.observation_count(ObservationKind.VALUE) == 43
    assert fy.observation_count(ObservationKind.DASH) == 11
    assert q1.unassigned_numeric_line_indices == fy.unassigned_numeric_line_indices == ()


def test_each_panel_binds_exact_geography_measure_axes_unit_and_period(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    expected_axes = [
        "DOMESTIC_SPECIFIC",
        "DOMESTIC_GENERAL",
        "DOMESTIC_COMBINED",
        "FOREIGN_SPECIFIC",
        "FOREIGN_GENERAL",
        "FOREIGN_COMBINED",
        "OVERALL_SPECIFIC",
        "OVERALL_GENERAL",
        "OVERALL_COMBINED",
    ]

    for panel in parsed.panels:
        assert [axis.axis_role for axis in panel.axes] == expected_axes
        assert [axis.mapping_axis_authority for axis in panel.axes] == [
            False,
            False,
            False,
            False,
            False,
            False,
            True,
            True,
            False,
        ]
        assert {axis.canonical_unit for axis in panel.axes} == {"VND"}
        assert {axis.unit_multiplier for axis in panel.axes} == {1_000_000}
        assert all(
            axis.header_bbox is not None and axis.unit_bbox is not None for axis in panel.axes
        )

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


def test_visible_values_wrapped_labels_and_close_open_continuity_are_preserved(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)

    def row(panel_key: str, role: str):
        return next(
            item for item in parsed.rows if item.panel_key == panel_key and item.row_role == role
        )

    q1_open = row("Q1_2026", "OPENING")
    fy_close = row("FY_2025", "CLOSING")
    assert [cell.value for cell in q1_open.row.cells] == [
        5_014_394,
        8_012_012,
        13_026_406,
        38_054,
        86_133,
        124_187,
        5_052_448,
        8_098_145,
        13_150_593,
    ]
    assert q1_open.row.cells == fy_close.row.cells
    assert len(row("Q1_2026", "PROVISION").label_line_indices) == 3
    assert len(row("FY_2025", "PROVISION").label_line_indices) == 3
    assert len(row("FY_2025", "AUDIT_ADJUSTMENT").label_line_indices) == 2

    audit = row("FY_2025", "AUDIT_ADJUSTMENT")
    assert [cell.value for cell in audit.row.cells] == [
        33_942,
        -1_444,
        32_498,
        None,
        None,
        None,
        33_942,
        -1_444,
        32_498,
    ]
    assert (audit.period_start, audit.period_end, audit.period_type) == (
        date(2025, 1, 1),
        date(2025, 12, 31),
        "DURATION",
    )


def test_nineteen_dashes_keep_pixel_evidence_and_four_ocr_misreads_keep_raw_provenance(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    assert [panel.ocr_misread_dash_line_indices for panel in parsed.panels] == [
        (57, 58),
        (116, 132),
    ]
    dash_cells = [
        (row, index, cell)
        for row in parsed.rows
        for index, cell in enumerate(row.row.cells)
        if cell.observation is ObservationKind.DASH
    ]
    assert len(dash_cells) == 19
    assert sum(bool(row.value_line_indices[index]) for row, index, _cell in dash_cells) == 4
    for row, index, cell in dash_cells:
        assert cell.value is None
        assert row.value_bboxes[index] is not None
        assert row.visual_cell_evidence[index] is not None
        assert row.visual_cell_evidence[index].observation == "DASH"
        if row.value_line_indices[index]:
            assert row.cell_raw_ocr_texts[index] == ("1",)
            assert row.raw_ocr_value_bboxes[index]


def test_page34_policy_forbids_mapping_history_review_imputation_and_dash_zero(
    project_root: Path,
) -> None:
    policy = load_tm_page34_policy(project_root / "config/tables/tm-note-page34-v1.yaml")
    assert set(policy.forbidden_semantic_inputs) == {
        "missing_ocr_cell_as_dash_without_pixel_evidence",
        "template_labels_as_row_reconstruction_input",
        "approved_report_norm_id_assignment",
        "historical_or_mongodb_values",
        "human_review_answers",
        "dash_as_zero",
        "accounting_equations_as_value_imputation",
    }
