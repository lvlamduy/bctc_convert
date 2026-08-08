from __future__ import annotations

import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.tables.tm_note_word_box import (
    TMNoteRowKind,
    TMNoteWordBoxError,
    load_tm_page31_policy,
    parse_tm_page31,
)

_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0031-ppocrv6-word-box.json")
_FIXTURE_SHA256 = "36f9e80e02a30db520a4c4bb201671b97b6073303326e8ffd5c18059153ba0a1"


def _policy(project_root: Path):
    return load_tm_page31_policy(project_root / "config/tables/tm-note-page31-v1.yaml")


def _parsed(project_root: Path):
    return parse_tm_page31(project_root / _FIXTURE, _policy(project_root))


def test_real_page31_reconstructs_four_tables_and_exact_item_denominators(
    project_root: Path,
) -> None:
    fixture = project_root / _FIXTURE
    assert sha256_file(fixture) == _FIXTURE_SHA256

    parsed = _parsed(project_root)

    assert parsed.source_sha256 == _FIXTURE_SHA256
    assert parsed.source_render_sha256 == (
        "194f13111ddce2fbcf5e1400a4925f4b0beb3774d572ad40ff9cea6453c114e7"
    )
    assert parsed.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert parsed.scope == "CONSOLIDATED"
    assert parsed.scope_binding == "PREDECESSOR_TM_SECTION_ON_PAGE_30"
    assert [table.table_key for table in parsed.tables] == [
        "SECURITIES",
        "LOAN_TYPE",
        "LOAN_QUALITY",
        "LOAN_MATURITY",
    ]
    assert [len(table.rows) for table in parsed.tables] == [9, 9, 8, 7]
    assert len(parsed.rows) == 33
    assert parsed.numeric_row_count == 28
    assert parsed.label_only_row_count == 5
    assert parsed.numeric_cell_count == 56
    assert parsed.unassigned_numeric_line_indices == ()
    assert parsed.excluded_footer_numeric_line_indices == (108,)
    assert parsed.mapping_authority is False


def test_all_four_headers_bind_snapshot_period_unit_and_scope_without_x_role_inference(
    project_root: Path,
) -> None:
    parsed = _parsed(project_root)

    for table in parsed.tables:
        assert [axis.current_or_comparative for axis in table.axes] == [
            "CURRENT",
            "COMPARATIVE",
        ]
        assert [axis.period_end for axis in table.axes] == [
            date(2026, 3, 31),
            date(2025, 12, 31),
        ]
        assert {axis.period_type for axis in table.axes} == {"SNAPSHOT"}
        assert {axis.canonical_unit for axis in table.axes} == {"VND"}
        assert {axis.unit_multiplier for axis in table.axes} == {1_000_000}


def test_visible_securities_loan_totals_and_negative_provision_are_kept_distinct(
    project_root: Path,
) -> None:
    parsed = _parsed(project_root)
    securities, loan_type, loan_quality, loan_maturity = parsed.tables

    assert [row.row_kind for row in securities.rows] == [
        TMNoteRowKind.LABEL_ONLY,
        TMNoteRowKind.NUMERIC,
        TMNoteRowKind.NUMERIC,
        TMNoteRowKind.LABEL_ONLY,
        TMNoteRowKind.NUMERIC,
        TMNoteRowKind.NUMERIC,
        TMNoteRowKind.NUMERIC,
        TMNoteRowKind.NUMERIC,
        TMNoteRowKind.NUMERIC,
    ]
    assert [[cell.value for cell in row.row.cells] for row in securities.rows[6:]] == [
        [5_093_432, 4_692_622],
        [-34_663, -39_393],
        [5_058_769, 4_653_229],
    ]
    assert all(cell.sign_evidence == "parentheses" for cell in securities.rows[7].row.cells)
    assert [[cell.value for cell in table.rows[-1].row.cells] for table in parsed.tables[1:]] == [
        [1_120_562_481, 1_084_019_370],
        [1_120_562_481, 1_084_019_370],
        [1_120_562_481, 1_084_019_370],
    ]
    assert [cell.value for cell in loan_type.rows[7].row.cells] == [15_520_372, 15_040_585]
    assert [cell.value for cell in loan_quality.rows[2].row.cells] == [
        15_520_372,
        15_040_585,
    ]
    assert [cell.value for cell in loan_maturity.rows[5].row.cells] == [
        15_520_372,
        15_040_585,
    ]
    assert all(
        cell.observation is ObservationKind.BLANK
        for table in parsed.tables
        for row in table.rows
        if row.row_kind is TMNoteRowKind.LABEL_ONLY
        for cell in row.row.cells
    )


def test_missing_local_unit_fails_closed_after_binding_mutated_fixture(
    project_root: Path, tmp_path: Path
) -> None:
    payload = json.loads((project_root / _FIXTURE).read_text(encoding="utf-8"))
    payload["rec_texts"][5] = "unknown"
    fixture = tmp_path / "page31-missing-unit.json"
    fixture.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    policy = replace(_policy(project_root), source_ocr_sha256=sha256_file(fixture))

    with pytest.raises(TMNoteWordBoxError, match="two dates and two units"):
        parse_tm_page31(fixture, policy)


def test_page31_policy_forbids_mapping_history_review_and_value_imputation(
    project_root: Path,
) -> None:
    assert set(_policy(project_root).forbidden_semantic_inputs) == {
        "template_labels_as_row_reconstruction_input",
        "approved_report_norm_id_assignment",
        "historical_or_mongodb_values",
        "human_review_answers",
        "accounting_equations_as_value_imputation",
    }
