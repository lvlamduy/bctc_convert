from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import cv2
import pytest

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.tables.tm_note_page49 import load_tm_page49_policy, parse_tm_page49
from bctc_ai.tables.tm_note_word_box import TMNoteRowKind, TMNoteWordBoxError

_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0049-ppocrv6-word-box.json")
_FIXTURE_SHA256 = "629d0fc832c0aa6378b78d9b97dbe95ba487b38fa511ffa1f7412eceea6704bb"
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")


def _policy(project_root: Path):
    return load_tm_page49_policy(project_root / "config/tables/tm-note-page49-v1.yaml")


def _render(project_root: Path, tmp_path: Path) -> Path:
    return Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={49},
        )[0].path
    )


def _parsed(project_root: Path, tmp_path: Path):
    return parse_tm_page49(
        project_root / _FIXTURE,
        _render(project_root, tmp_path),
        _policy(project_root),
    )


def test_real_page49_reconstructs_two_complete_notes_and_exact_denominator(
    project_root: Path, tmp_path: Path
) -> None:
    assert sha256_file(project_root / _FIXTURE) == _FIXTURE_SHA256

    parsed = _parsed(project_root, tmp_path)

    assert parsed.source_sha256 == _FIXTURE_SHA256
    assert parsed.source_render_sha256 == (
        "e806551562241d3abf6940e8734a1292faee25a6aea7db08122ee160b05ad281"
    )
    assert parsed.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert parsed.scope == "CONSOLIDATED"
    assert [table.table_key for table in parsed.tables] == [
        "RISK_PROVISION_EXPENSE",
        "STATE_BUDGET_OBLIGATIONS",
    ]
    assert [len(table.rows) for table in parsed.tables] == [7, 5]
    assert len(parsed.rows) == 12
    assert parsed.numeric_row_count == 10
    assert parsed.label_only_row_count == 2
    assert parsed.financial_slot_count == 28
    assert parsed.observation_count(ObservationKind.VALUE) == 27
    assert parsed.observation_count(ObservationKind.DASH) == 1
    assert parsed.unassigned_numeric_line_indices == ()
    assert parsed.excluded_artifact_line_indices == (55,)
    assert parsed.excluded_footer_numeric_line_indices == (56,)
    assert parsed.mapping_authority is False


def test_page49_retains_two_duration_axes_and_four_mixed_obligation_axes(
    project_root: Path, tmp_path: Path
) -> None:
    provision, obligations = _parsed(project_root, tmp_path).tables

    assert [axis.axis_role for axis in provision.axes] == ["CURRENT", "COMPARATIVE"]
    assert [axis.period_start for axis in provision.axes] == [
        date(2026, 1, 1),
        date(2025, 1, 1),
    ]
    assert [axis.period_end for axis in provision.axes] == [
        date(2026, 3, 31),
        date(2025, 3, 31),
    ]
    assert {axis.period_type for axis in provision.axes} == {"DURATION"}
    assert [axis.axis_role for axis in obligations.axes] == [
        "OPENING_BALANCE",
        "PAYABLE_ACTIVITY",
        "PAID_ACTIVITY",
        "CLOSING_BALANCE",
    ]
    assert [axis.period_type for axis in obligations.axes] == [
        "SNAPSHOT",
        "DURATION",
        "DURATION",
        "SNAPSHOT",
    ]
    assert {axis.canonical_unit for axis in (*provision.axes, *obligations.axes)} == {"VND"}
    assert {axis.unit_multiplier for axis in (*provision.axes, *obligations.axes)} == {1_000_000}


def test_page49_preserves_values_unlabeled_totals_and_pixel_backed_dash(
    project_root: Path, tmp_path: Path
) -> None:
    provision, obligations = _parsed(project_root, tmp_path).tables

    assert provision.rows[0].row_kind is TMNoteRowKind.LABEL_ONLY
    assert [[cell.value for cell in row.row.cells] for row in provision.rows[1:]] == [
        [3_451_261, 2_973_316],
        [1_648, 76],
        [1_775, 24_681],
        [None, -11_763],
        [134, 104],
        [3_454_818, 2_986_414],
    ]
    dash = provision.rows[4]
    assert [cell.observation for cell in dash.row.cells] == [
        ObservationKind.DASH,
        ObservationKind.VALUE,
    ]
    assert dash.visual_cell_evidence[0] is not None
    assert dash.visual_cell_evidence[0].component_box == (1830, 874, 1842, 878)
    assert provision.rows[-1].row.label == ""
    assert obligations.rows[0].row_kind is TMNoteRowKind.LABEL_ONLY
    assert [[cell.value for cell in row.row.cells] for row in obligations.rows[1:]] == [
        [175_047, 289_454, -349_300, 115_201],
        [3_897_818, 1_919_809, -3_908_383, 1_909_244],
        [145_394, 951_670, -982_207, 114_857],
        [4_218_259, 3_160_933, -5_239_890, 2_139_302],
    ]
    assert obligations.rows[-1].row.label == ""


def test_page49_missing_dash_pixels_fail_closed_and_dash_cannot_be_zero(
    project_root: Path, tmp_path: Path
) -> None:
    render = _render(project_root, tmp_path)
    image = cv2.imread(str(render), cv2.IMREAD_COLOR)
    assert image is not None
    image[820:930, 1770:1900] = 255
    mutated = tmp_path / "missing-page49-dash.png"
    assert cv2.imwrite(str(mutated), image)
    policy = replace(_policy(project_root), source_render_sha256=sha256_file(mutated))

    with pytest.raises(TMNoteWordBoxError, match="lacks constrained pixel evidence"):
        parse_tm_page49(project_root / _FIXTURE, mutated, policy)

    assert "dash_as_zero" in policy.forbidden_semantic_inputs
    assert "accounting_equations_as_value_imputation" in policy.forbidden_semantic_inputs
