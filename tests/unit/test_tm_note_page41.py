from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import cv2
import pytest

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.tables.tm_note_page41 import load_tm_page41_policy, parse_tm_page41
from bctc_ai.tables.tm_note_word_box import TMNoteWordBoxError

_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0041-ppocrv6-word-box.json")
_FIXTURE_SHA256 = "d3de94f929abe7580fe856e63eb7ac877d9c4380c6ed4eec00dc04e298bf145f"
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")


def _policy(project_root: Path):
    return load_tm_page41_policy(project_root / "config/tables/tm-note-page41-v1.yaml")


def _render(project_root: Path, tmp_path: Path) -> Path:
    return Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={41},
        )[0].path
    )


def _parsed(project_root: Path, tmp_path: Path):
    return parse_tm_page41(
        project_root / _FIXTURE,
        _render(project_root, tmp_path),
        _policy(project_root),
    )


def test_real_page41_reconstructs_exact_dual_panel_denominators(
    project_root: Path, tmp_path: Path
) -> None:
    fixture = project_root / _FIXTURE
    assert sha256_file(fixture) == _FIXTURE_SHA256

    parsed = _parsed(project_root, tmp_path)

    assert parsed.source_sha256 == _FIXTURE_SHA256
    assert parsed.source_render_sha256 == (
        "6fadb4e5b2389872247686ccb7fe1829ec1f4ead25c14d87e3d9198c1b35db5b"
    )
    assert parsed.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert parsed.scope == "CONSOLIDATED"
    assert [panel.panel_key for panel in parsed.panels] == ["Q1_2026", "FY_2025"]
    assert [len(panel.rows) for panel in parsed.panels] == [12, 13]
    assert len(parsed.rows) == 25
    assert parsed.numeric_row_count == 19
    assert parsed.label_only_row_count == 6
    assert parsed.financial_slot_count == 57
    assert parsed.observation_count(ObservationKind.VALUE) == 51
    assert parsed.observation_count(ObservationKind.DASH) == 6
    assert parsed.unassigned_numeric_line_indices == ()
    assert parsed.excluded_footer_numeric_line_indices == (96,)
    assert parsed.mapping_authority is False


def test_panel_axes_bind_class_period_unit_and_scope_from_visible_headers(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)

    assert [axis.semantic_role for axis in parsed.panels[0].axes] == [
        "BUILDINGS_AND_STRUCTURES",
        "TERM_LAND_USE_RIGHTS",
        "TOTAL",
    ]
    assert [axis.axis_right_edge for axis in parsed.panels[0].axes] == [1542.0, 1900.0, 2247.0]
    assert [axis.axis_right_edge for axis in parsed.panels[1].axes] == [1536.0, 1891.0, 2239.0]
    assert {(axis.period_start, axis.period_end) for axis in parsed.panels[0].axes} == {
        (date(2026, 1, 1), date(2026, 3, 31))
    }
    assert {(axis.period_start, axis.period_end) for axis in parsed.panels[1].axes} == {
        (date(2025, 1, 1), date(2025, 12, 31))
    }
    assert {axis.period_type for panel in parsed.panels for axis in panel.axes} == {
        "DURATION_PANEL"
    }
    assert {axis.canonical_unit for panel in parsed.panels for axis in panel.axes} == {"VND"}
    assert {axis.unit_multiplier for panel in parsed.panels for axis in panel.axes} == {1_000_000}


def test_visible_totals_and_cross_panel_continuity_are_preserved_exactly(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    rows = {(row.panel_key, row.row_key): row for row in parsed.rows}

    expected = {
        ("Q1_2026", "GROSS_OPENING"): (55_806, 199_320, 255_126),
        ("Q1_2026", "GROSS_CLOSING"): (50_835, 199_320, 250_155),
        ("Q1_2026", "DEPRECIATION_OPENING"): (7_825, 24_488, 32_313),
        ("Q1_2026", "DEPRECIATION_CLOSING"): (8_075, 25_766, 33_841),
        ("Q1_2026", "NET_OPENING"): (47_981, 174_832, 222_813),
        ("Q1_2026", "NET_CLOSING"): (42_760, 173_554, 216_314),
        ("FY_2025", "GROSS_OPENING"): (51_835, 208_580, 260_415),
        ("FY_2025", "GROSS_CLOSING"): (55_806, 199_320, 255_126),
        ("FY_2025", "DEPRECIATION_OPENING"): (6_923, 19_377, 26_300),
        ("FY_2025", "DEPRECIATION_CLOSING"): (7_825, 24_488, 32_313),
        ("FY_2025", "NET_OPENING"): (44_912, 189_203, 234_115),
        ("FY_2025", "NET_CLOSING"): (47_981, 174_832, 222_813),
    }
    for identity, values in expected.items():
        assert tuple(cell.value for cell in rows[identity].row.cells) == tuple(
            Decimal(value) for value in values
        )


def test_all_six_dashes_have_exact_render_pixel_evidence_and_are_not_zero(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    dash_cells = [
        (row.panel_key, row.row_key, index, cell, evidence)
        for row in parsed.rows
        for index, (cell, evidence) in enumerate(
            zip(row.row.cells, row.visual_cell_evidence, strict=True)
        )
        if cell.observation is ObservationKind.DASH
    ]

    assert [item[0:3] for item in dash_cells] == [
        ("Q1_2026", "GROSS_INCREASE", 0),
        ("Q1_2026", "GROSS_INCREASE", 1),
        ("Q1_2026", "GROSS_INCREASE", 2),
        ("Q1_2026", "GROSS_OTHER", 1),
        ("FY_2025", "GROSS_INCREASE", 1),
        ("FY_2025", "DEPRECIATION_OTHER", 1),
    ]
    assert [item[4].component_box for item in dash_cells if item[4]] == [
        (1529, 788, 1541, 793),
        (1884, 787, 1896, 791),
        (2232, 785, 2245, 790),
        (1884, 835, 1896, 839),
        (1877, 2001, 1889, 2005),
        (1875, 2374, 1887, 2379),
    ]
    assert all(
        cell.value is None
        and evidence is not None
        and evidence.observation == "DASH"
        and evidence.foreground_contrast > 100
        for _panel, _row, _index, cell, evidence in dash_cells
    )


def test_missing_dash_pixel_fails_closed_instead_of_using_missing_ocr(
    project_root: Path, tmp_path: Path
) -> None:
    render = _render(project_root, tmp_path)
    image = cv2.imread(str(render), cv2.IMREAD_COLOR)
    assert image is not None
    image[770:810, 1500:1560] = 255
    mutated = tmp_path / "missing-investment-property-dash.png"
    assert cv2.imwrite(str(mutated), image)
    policy = replace(_policy(project_root), source_render_sha256=sha256_file(mutated))

    with pytest.raises(TMNoteWordBoxError, match="lacks dash pixel evidence"):
        parse_tm_page41(project_root / _FIXTURE, mutated, policy)


def test_page41_policy_forbids_semantic_leakage_dash_zero_and_cross_panel_imputation(
    project_root: Path,
) -> None:
    assert set(_policy(project_root).forbidden_semantic_inputs) == {
        "missing_ocr_cell_as_dash_without_pixel_evidence",
        "template_labels_as_row_reconstruction_input",
        "approved_report_norm_id_assignment",
        "historical_or_mongodb_values",
        "human_review_answers",
        "dash_as_zero",
        "accounting_equations_as_value_imputation",
        "cross_panel_values_as_value_imputation",
    }
