from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import cv2
import pytest

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.tables.tm_note_page50 import load_tm_page50_policy, parse_tm_page50
from bctc_ai.tables.tm_note_word_box import TMNoteWordBoxError

_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0050-ppocrv6-word-box.json")
_FIXTURE_SHA256 = "8f114bc6f6e20941d0db761f039f516252541341de7b12f2af69efa6f61f586e"
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")


def _policy(project_root: Path):
    return load_tm_page50_policy(project_root / "config/tables/tm-note-page50-v1.yaml")


def _render(project_root: Path, tmp_path: Path) -> Path:
    return Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={50},
        )[0].path
    )


def _parsed(project_root: Path, tmp_path: Path):
    return parse_tm_page50(
        project_root / _FIXTURE,
        _render(project_root, tmp_path),
        _policy(project_root),
    )


def test_real_page50_reconstructs_three_complete_notes_and_exact_denominator(
    project_root: Path, tmp_path: Path
) -> None:
    assert sha256_file(project_root / _FIXTURE) == _FIXTURE_SHA256

    parsed = _parsed(project_root, tmp_path)

    assert parsed.source_render_sha256 == (
        "e77b80f11ca9b153211a3b7ef8b23c35780cd120858c5b18cc00fcbb7b4fcfb9"
    )
    assert parsed.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert parsed.scope == "CONSOLIDATED"
    assert [table.table_key for table in parsed.tables] == [
        "TAX_EXPENSE",
        "TAX_RECONCILIATION",
        "CASH_EQUIVALENTS",
    ]
    assert [len(table.rows) for table in parsed.tables] == [6, 12, 5]
    assert len(parsed.rows) == 23
    assert parsed.numeric_row_count == 19
    assert parsed.label_only_row_count == 4
    assert parsed.financial_slot_count == 38
    assert parsed.observation_count(ObservationKind.VALUE) == 37
    assert parsed.observation_count(ObservationKind.DASH) == 1
    assert parsed.unassigned_numeric_line_indices == ()
    assert parsed.excluded_artifact_line_indices == ()
    assert parsed.excluded_footer_numeric_line_indices == (85,)
    assert [record.semantic_role for record in parsed.narratives] == [
        "NOTE_11_SECTION_TITLE",
        "STATUTORY_TAX_RATE",
        "CASH_EQUIVALENT_DEFINITION",
    ]
    assert parsed.narrative_quantity_count == 1
    assert not parsed.mapping_authority


def test_local_headers_bind_two_duration_tables_and_one_snapshot_table(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    tax_expense, reconciliation, cash = parsed.tables

    for table in (tax_expense, reconciliation):
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

    assert [axis.period_start for axis in cash.axes] == [
        date(2026, 3, 31),
        date(2025, 12, 31),
    ]
    assert [axis.period_end for axis in cash.axes] == [
        date(2026, 3, 31),
        date(2025, 12, 31),
    ]
    assert {axis.period_type for axis in cash.axes} == {"SNAPSHOT"}


def test_values_dash_and_unlabeled_cash_total_remain_source_preserving(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    tax_expense, reconciliation, cash = parsed.tables

    assert [[cell.value for cell in row.row.cells] for row in tax_expense.rows[1:]] == [
        [1_929_120, 1_708_859],
        [1_929_120, 1_708_859],
        [-3_454, 2_587],
        [-3_454, 2_587],
        [1_925_666, 1_711_446],
    ]
    foreign_branch = reconciliation.rows[8]
    assert [cell.observation for cell in foreign_branch.row.cells] == [
        ObservationKind.DASH,
        ObservationKind.VALUE,
    ]
    assert [cell.value for cell in foreign_branch.row.cells] == [None, 1_854]
    assert foreign_branch.visual_cell_evidence[0] is not None
    assert foreign_branch.visual_cell_evidence[0].component_box == (1844, 1933, 1856, 1938)
    assert foreign_branch.visual_cell_evidence[1] is None

    assert [[cell.value for cell in row.row.cells] for row in cash.rows[1:]] == [
        [5_741_287, 4_965_786],
        [15_106_404, 68_475_175],
        [149_138_239, 165_819_028],
        [169_985_930, 239_259_989],
    ]
    assert cash.rows[-1].source_role == "TOTAL"
    assert cash.rows[-1].row.label == ""
    assert all("20%" not in row.row.label for row in parsed.rows)
    tax_rate = parsed.narratives[1]
    assert tax_rate.quantities == (20,)
    assert tax_rate.quantity_units == ("PERCENT",)
    assert not tax_rate.mapping_approved


def test_missing_dash_pixels_fail_closed_and_policy_forbids_tax_rate_promotion(
    project_root: Path, tmp_path: Path
) -> None:
    render = _render(project_root, tmp_path)
    image = cv2.imread(str(render), cv2.IMREAD_COLOR)
    assert image is not None
    image[1890:1980, 1800:1910] = 255
    mutated = tmp_path / "missing-page50-dash.png"
    assert cv2.imwrite(str(mutated), image)
    policy = replace(_policy(project_root), source_render_sha256=sha256_file(mutated))

    with pytest.raises(TMNoteWordBoxError, match="visible dash lacks constrained pixel evidence"):
        parse_tm_page50(project_root / _FIXTURE, mutated, policy)

    assert {
        "narrative_tax_rate_as_financial_statement_value",
        "dash_as_zero",
        "human_review_answers",
        "accounting_equations_as_value_imputation",
    } <= set(_policy(project_root).forbidden_semantic_inputs)
