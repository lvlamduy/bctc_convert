from __future__ import annotations

import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.tables.tm_note_page51 import load_tm_page51_policy, parse_tm_page51
from bctc_ai.tables.tm_note_word_box import TMNoteRowKind, TMNoteWordBoxError

_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0051-ppocrv6-word-box.json")
_FIXTURE_SHA256 = "786028061957f467d579de3812c98061a9b5009c2a5de7a6ff79cd5ea4462298"
_UPSTREAM_OCR_SHA256 = "bc4cde1281abfc6238d29ae8b065f828f762ee708e7f3a05cc0c9728e143d7f0"
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")


def _policy(project_root: Path):
    return load_tm_page51_policy(project_root / "config/tables/tm-note-page51-v1.yaml")


def _render(project_root: Path, tmp_path: Path) -> Path:
    return Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={51},
        )[0].path
    )


def _parsed(project_root: Path, tmp_path: Path):
    return parse_tm_page51(
        project_root / _FIXTURE,
        _render(project_root, tmp_path),
        _policy(project_root),
    )


def test_real_page51_is_one_complete_note_with_exact_financial_denominator(
    project_root: Path, tmp_path: Path
) -> None:
    fixture = project_root / _FIXTURE
    assert sha256_file(fixture) == _FIXTURE_SHA256
    assert fixture.stat().st_size < 6_000

    parsed = _parsed(project_root, tmp_path)

    assert parsed.source_sha256 == _FIXTURE_SHA256
    assert parsed.upstream_ocr_sha256 == _UPSTREAM_OCR_SHA256
    assert parsed.source_render_sha256 == (
        "1d72c1bc3c7f6e05287f2658f286f35eded2d5024d20e92856c35b558a9741b7"
    )
    assert parsed.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert parsed.scope == "CONSOLIDATED"
    assert [table.table_key for table in parsed.tables] == ["OFF_BALANCE_COMMITMENTS"]
    assert len(parsed.rows) == 11
    assert parsed.numeric_row_count == 9
    assert parsed.label_only_row_count == 2
    assert parsed.financial_slot_count == 18
    assert parsed.observation_count(ObservationKind.VALUE) == 18
    assert parsed.observation_count(ObservationKind.DASH) == 0
    assert parsed.observation_count(ObservationKind.BLANK) == 0
    assert parsed.unassigned_numeric_line_indices == ()
    assert parsed.excluded_artifact_line_indices == ()
    assert parsed.excluded_footer_numeric_line_indices == (60,)
    assert parsed.mapping_authority is False


def test_page51_binds_two_exact_snapshot_axes_unit_and_period_roles(
    project_root: Path, tmp_path: Path
) -> None:
    axes = _parsed(project_root, tmp_path).axes

    assert [axis.current_or_comparative for axis in axes] == ["CURRENT", "COMPARATIVE"]
    assert [axis.period_start for axis in axes] == [date(2026, 3, 31), date(2025, 12, 31)]
    assert [axis.period_end for axis in axes] == [date(2026, 3, 31), date(2025, 12, 31)]
    assert {axis.period_type for axis in axes} == {"SNAPSHOT"}
    assert {axis.canonical_unit for axis in axes} == {"VND"}
    assert {axis.unit_multiplier for axis in axes} == {1_000_000}


def test_page51_preserves_all_nine_visible_rows_and_eighteen_values(
    project_root: Path, tmp_path: Path
) -> None:
    rows = _parsed(project_root, tmp_path).rows

    assert [row.row_kind for row in rows[:2]] == [
        TMNoteRowKind.LABEL_ONLY,
        TMNoteRowKind.LABEL_ONLY,
    ]
    assert [row.source_role for row in rows[:2]] == [
        "STATEMENT_SECTION_TITLE",
        "NOTE_TITLE",
    ]
    assert [[cell.value for cell in row.row.cells] for row in rows[2:]] == [
        [1_681_823, 1_684_717],
        [723_980_330, 618_888_427],
        [1_302_737, 9_738_358],
        [2_160_046, 8_752_345],
        [359_933_489, 299_830_234],
        [360_584_058, 300_567_490],
        [71_763_365, 59_728_018],
        [186_098_713, 190_317_517],
        [117_681_586, 127_878_633],
    ]
    assert all(row.cell_period_roles == ("CURRENT", "COMPARATIVE") for row in rows[2:])


def test_page51_retains_seven_narratives_but_excludes_percentages_from_financial_slots(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)

    assert [record.semantic_role for record in parsed.narratives] == [
        "CONTINGENT_LIABILITIES_HEADING",
        "OFF_BALANCE_OVERVIEW",
        "CREDIT_RISK_DEFINITION",
        "FINANCIAL_GUARANTEE_DEFINITION",
        "SIGHT_LC_RISK",
        "DEFERRED_LC_RISK",
        "COLLATERAL_RANGE",
    ]
    assert [len(record.source_line_indices) for record in parsed.narratives] == [
        1,
        4,
        3,
        4,
        4,
        5,
        3,
    ]
    assert parsed.narrative_quantity_count == 2
    assert parsed.narratives[-1].quantities == (0, 100)
    assert parsed.narratives[-1].quantity_units == ("PERCENT", "PERCENT")
    assert all(not record.mapping_approved for record in parsed.narratives)
    assert {
        "narrative_text_as_financial_statement_value",
        "narrative_quantity_as_schema_mapping_input",
        "accounting_equations_as_value_imputation",
        "human_review_answers",
    } <= set(_policy(project_root).forbidden_semantic_inputs)


def test_page51_compact_fixture_and_visible_date_drift_fail_closed(
    project_root: Path, tmp_path: Path
) -> None:
    fixture = project_root / _FIXTURE
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    payload["rec_texts"][4] = "30/03/2026"
    mutated = tmp_path / "page51-date-drift.json"
    mutated.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    policy = replace(_policy(project_root), source_ocr_sha256=sha256_file(mutated))

    with pytest.raises(TMNoteWordBoxError, match="visible snapshot date drifted"):
        parse_tm_page51(mutated, _render(project_root, tmp_path), policy)
