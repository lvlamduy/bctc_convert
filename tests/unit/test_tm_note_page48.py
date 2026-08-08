from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import cv2
import pytest

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.tables.tm_note_page48 import load_tm_page48_policy, parse_tm_page48
from bctc_ai.tables.tm_note_word_box import TMNoteWordBoxError

_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0048-ppocrv6-word-box.json")
_FIXTURE_SHA256 = "4f1ec95810a4c4563c2259579ddfff01a5332f540fc1fecc789718ce8396a020"
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")


def _policy(project_root: Path):
    return load_tm_page48_policy(project_root / "config/tables/tm-note-page48-v1.yaml")


def _render(project_root: Path, tmp_path: Path) -> Path:
    return Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={48},
        )[0].path
    )


def _parsed(project_root: Path, tmp_path: Path):
    return parse_tm_page48(
        project_root / _FIXTURE,
        _render(project_root, tmp_path),
        _policy(project_root),
    )


def test_real_page48_reconstructs_exact_financial_and_auxiliary_denominators(
    project_root: Path, tmp_path: Path
) -> None:
    assert sha256_file(project_root / _FIXTURE) == _FIXTURE_SHA256

    parsed = _parsed(project_root, tmp_path)

    assert parsed.source_render_sha256 == (
        "f9d8489a6d4041bd68bcea2e1b165b10aaa6e3c0810d0e10a0c8e23d17af27b2"
    )
    assert parsed.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert parsed.scope == "CONSOLIDATED"
    assert [table.table_key for table in parsed.tables] == [
        "CONTRIBUTION_INCOME",
        "OPERATING_EXPENSE",
    ]
    assert [len(table.rows) for table in parsed.tables] == [3, 10]
    assert len(parsed.rows) == 13
    assert parsed.numeric_row_count == 10
    assert parsed.label_only_row_count == 3
    assert parsed.financial_slot_count == 20
    assert parsed.observation_count(ObservationKind.VALUE) == 19
    assert parsed.observation_count(ObservationKind.DASH) == 1
    assert len(parsed.auxiliary_rows) == 11
    assert parsed.total_logical_row_count == 24
    assert len(parsed.narrative_quantities) == 2
    assert parsed.unassigned_numeric_line_indices == ()
    assert parsed.excluded_artifact_line_indices == ()
    assert parsed.excluded_footer_numeric_line_indices == (78,)
    assert not parsed.mapping_authority


def test_two_financial_headers_bind_exact_duration_unit_scope_and_roles(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)

    for table in parsed.tables:
        assert [axis.current_or_comparative for axis in table.axes] == [
            "CURRENT",
            "COMPARATIVE",
        ]
        assert [axis.period_start for axis in table.axes] == [
            date(2026, 1, 1),
            date(2025, 1, 1),
        ]
        assert [axis.period_end for axis in table.axes] == [
            date(2026, 3, 31),
            date(2025, 3, 31),
        ]
        assert {axis.period_type for axis in table.axes} == {"DURATION"}
        assert {axis.canonical_unit for axis in table.axes} == {"VND"}
        assert {axis.unit_multiplier for axis in table.axes} == {1_000_000}


def test_financial_values_dash_and_auxiliary_quantities_remain_distinct(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    contribution, operating = parsed.tables

    assert [[cell.value for cell in row.row.cells] for row in contribution.rows[1:]] == [
        [30, 40],
        [30, 40],
    ]
    assert [[cell.value for cell in row.row.cells] for row in operating.rows[1:]] == [
        [66_382, 37_958],
        [2_665_658, 2_522_157],
        [711_320, 610_685],
        [None, None],
        [250_707, 233_592],
        [761_925, 623_910],
        [143_750, 155_248],
        [-2_033, None],
        [4_347_002, 3_949_958],
    ]
    provision = operating.rows[8]
    assert [cell.observation for cell in provision.row.cells] == [
        ObservationKind.VALUE,
        ObservationKind.DASH,
    ]
    assert provision.visual_cell_evidence[0] is None
    assert provision.visual_cell_evidence[1] is not None
    assert provision.visual_cell_evidence[1].component_box == (2241, 1594, 2254, 1599)

    assert [row.value for row in parsed.auxiliary_rows] == [
        3_220_933,
        473_328,
        -569_506,
        -87_905,
        -840_599,
        -88_732,
        -10,
        -397_044,
        -468_404,
        -214_220,
        1_027_841,
    ]
    assert [row.source_role for row in parsed.auxiliary_rows] == ["DRIVER"] * 10 + ["TOTAL"]
    assert [quantity.raw_text for quantity in parsed.narrative_quantities] == [
        "1.027.841",
        "15,40%",
    ]
    assert all(not row.mapping_approved for row in parsed.auxiliary_rows)
    assert all(not quantity.mapping_approved for quantity in parsed.narrative_quantities)


def test_missing_comparative_dash_pixels_fail_closed_and_policy_forbids_auxiliary_promotion(
    project_root: Path, tmp_path: Path
) -> None:
    render = _render(project_root, tmp_path)
    image = cv2.imread(str(render), cv2.IMREAD_COLOR)
    assert image is not None
    image[1540:1640, 2180:2300] = 255
    mutated = tmp_path / "missing-page48-dash.png"
    assert cv2.imwrite(str(mutated), image)
    policy = replace(_policy(project_root), source_render_sha256=sha256_file(mutated))

    with pytest.raises(TMNoteWordBoxError, match="visible dash lacks constrained pixel evidence"):
        parse_tm_page48(project_root / _FIXTURE, mutated, policy)

    assert {
        "auxiliary_variance_as_financial_statement_value",
        "narrative_quantity_as_schema_mapping_input",
        "dash_as_zero",
        "human_review_answers",
    } <= set(_policy(project_root).forbidden_semantic_inputs)
