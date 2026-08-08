from __future__ import annotations

import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.tables.tm_note_page52 import load_tm_page52_policy, parse_tm_page52
from bctc_ai.tables.tm_note_word_box import TMNoteRowKind, TMNoteWordBoxError

_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0052-ppocrv6-word-box.json")
_FIXTURE_SHA256 = "3c5563f8f91d673f2f5301da9efae79a906927608d8de68b5a471d33e0a164b7"
_UPSTREAM_OCR_SHA256 = "1f9062e3822277325acf91ac1e21c4bcf28ee54f4f537e77e9e18b8e0774636c"
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")


def _policy(project_root: Path):
    return load_tm_page52_policy(project_root / "config/tables/tm-note-page52-v1.yaml")


def _render(project_root: Path, tmp_path: Path) -> Path:
    return Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={52},
        )[0].path
    )


def _parsed(project_root: Path, tmp_path: Path):
    return parse_tm_page52(
        project_root / _FIXTURE,
        _render(project_root, tmp_path),
        _policy(project_root),
    )


def test_real_page52_has_two_complete_tables_and_exact_financial_denominator(
    project_root: Path, tmp_path: Path
) -> None:
    fixture = project_root / _FIXTURE
    assert sha256_file(fixture) == _FIXTURE_SHA256
    assert fixture.stat().st_size < 6_000

    parsed = _parsed(project_root, tmp_path)

    assert parsed.source_sha256 == _FIXTURE_SHA256
    assert parsed.upstream_ocr_sha256 == _UPSTREAM_OCR_SHA256
    assert parsed.source_render_sha256 == (
        "f19fa64041c6df54f6b319ea9166902ee0c9325116fea6e52854a4fe1e09dc59"
    )
    assert parsed.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert [table.table_key for table in parsed.tables] == [
        "RELATED_PARTY_BALANCES",
        "GEOGRAPHIC_CONCENTRATION",
    ]
    assert len(parsed.rows) == 6
    assert parsed.numeric_row_count == 4
    assert parsed.label_only_row_count == 2
    assert parsed.financial_slot_count == 12
    assert parsed.observation_count(ObservationKind.VALUE) == 12
    assert parsed.observation_count(ObservationKind.DASH) == 0
    assert parsed.observation_count(ObservationKind.BLANK) == 0
    assert parsed.unassigned_numeric_line_indices == ()
    assert parsed.excluded_artifact_line_indices == (36,)
    assert parsed.excluded_footer_numeric_line_indices == (63,)
    assert parsed.mapping_authority is False


def test_page52_binds_exact_snapshot_axes_unit_scope_and_continuation(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    related, geographic = parsed.tables

    assert [axis.current_or_comparative for axis in related.axes] == [
        "CURRENT",
        "COMPARATIVE",
    ]
    assert [axis.period_start for axis in related.axes] == [
        date(2026, 3, 31),
        date(2025, 12, 31),
    ]
    assert {axis.period_type for axis in related.axes} == {"SNAPSHOT"}
    assert [axis.axis_id for axis in geographic.axes] == [
        "snapshot-current-customer_loans",
        "snapshot-current-customer_deposits",
        "snapshot-current-lc_commitments",
        "snapshot-current-securities",
    ]
    assert {axis.period_start for axis in geographic.axes} == {date(2026, 3, 31)}
    assert {axis.current_or_comparative for axis in geographic.axes} == {"CURRENT"}
    assert {axis.canonical_unit for table in parsed.tables for axis in table.axes} == {"VND"}
    assert {axis.unit_multiplier for table in parsed.tables for axis in table.axes} == {1_000_000}
    assert parsed.scope == "CONSOLIDATED"
    assert not parsed.continues_to_page_53
    assert parsed.next_page_note_number == "4"


def test_page52_preserves_related_party_total_and_geographic_matrix_values(
    project_root: Path, tmp_path: Path
) -> None:
    related, geographic = _parsed(project_root, tmp_path).tables

    assert [row.row_kind for row in related.rows] == [
        TMNoteRowKind.LABEL_ONLY,
        TMNoteRowKind.NUMERIC,
        TMNoteRowKind.NUMERIC,
    ]
    assert [row.source_role for row in related.rows] == [
        "NOTE_TITLE",
        "DETAIL",
        "PRINTED_TOTAL_UNLABELED",
    ]
    assert [[cell.value for cell in row.row.cells] for row in related.rows[1:]] == [
        [37_248_180, 40_201_646],
        [37_248_180, 40_201_646],
    ]
    assert [row.source_role for row in geographic.rows] == [
        "NOTE_TITLE",
        "DOMESTIC",
        "FOREIGN",
    ]
    assert [[cell.value for cell in row.row.cells] for row in geographic.rows[1:]] == [
        [1_111_746_709, 901_132_249, 71_244_194, 268_437_816],
        [8_815_772, 4_786_083, 519_171, 46_914],
    ]


def test_page52_narrative_percentages_are_provenance_not_financial_slots(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)

    assert [record.semantic_role for record in parsed.narratives] == [
        "RELATED_PARTY_DEFINITION",
        "GOVERNANCE_COMPENSATION_POLICY",
        "GEOGRAPHIC_CONCENTRATION_INTRODUCTION",
    ]
    assert [len(record.source_line_indices) for record in parsed.narratives] == [23, 4, 2]
    assert parsed.narratives[0].quantities == (5, 11, 5)
    assert parsed.narrative_quantity_count == 3
    assert all(not record.mapping_approved for record in parsed.narratives)
    assert {
        "narrative_quantity_as_schema_mapping_input",
        "accounting_equations_as_value_imputation",
        "inherited_unit_or_period_as_item_selector",
    } <= set(_policy(project_root).forbidden_semantic_inputs)


def test_page52_compact_fixture_and_visible_period_drift_fail_closed(
    project_root: Path, tmp_path: Path
) -> None:
    fixture = project_root / _FIXTURE
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    payload["rec_texts"][25] = "30/03/2026"
    mutated = tmp_path / "page52-period-drift.json"
    mutated.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    policy = replace(_policy(project_root), source_ocr_sha256=sha256_file(mutated))

    with pytest.raises(TMNoteWordBoxError, match="visible snapshot date drifted"):
        parse_tm_page52(mutated, _render(project_root, tmp_path), policy)
