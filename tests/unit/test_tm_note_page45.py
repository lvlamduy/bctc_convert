from __future__ import annotations

import json
from dataclasses import replace
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import cv2
import pytest

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.tables.tm_note_page45 import (
    TMPage45BlankEvidence,
    TMPage45LogicalRow,
    load_tm_page45_policy,
    parse_tm_page45,
)
from bctc_ai.tables.tm_note_word_box import TMNoteWordBoxError

_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0045-ppocrv6-word-box.json")
_FIXTURE_SHA256 = "8179a3e487d77018b17cec1019b6080f0c7a86e8bc621b94ff2324b6438b091e"
_UPSTREAM_OCR_SHA256 = "dbb9e1ac37d3cd27f949aa93d2622cb02c8fff80b8ec3a55ffde009c6159e36c"
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")


def _policy(project_root: Path):
    return load_tm_page45_policy(project_root / "config/tables/tm-note-page45-v1.yaml")


def _render(project_root: Path, tmp_path: Path) -> Path:
    return Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={45},
        )[0].path
    )


def _parsed(project_root: Path, tmp_path: Path):
    return parse_tm_page45(
        project_root / _FIXTURE,
        _render(project_root, tmp_path),
        _policy(project_root),
    )


def test_real_page45_reconstructs_exact_eps_and_share_denominators(
    project_root: Path, tmp_path: Path
) -> None:
    fixture = project_root / _FIXTURE
    assert sha256_file(fixture) == _FIXTURE_SHA256
    assert fixture.stat().st_size < 3_000

    parsed = _parsed(project_root, tmp_path)

    assert parsed.source_sha256 == _FIXTURE_SHA256
    assert parsed.upstream_ocr_sha256 == _UPSTREAM_OCR_SHA256
    assert parsed.source_render_sha256 == (
        "a627fbf5e24cad4b44c536a77b6c6219d9e9b73f5edb2610ccb4812258caf118"
    )
    assert parsed.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert parsed.scope == "CONSOLIDATED"
    assert [table.table_key for table in parsed.tables] == [
        "EARNINGS_PER_SHARE",
        "SHARE_COUNTS",
    ]
    assert [len(table.rows) for table in parsed.tables] == [4, 10]
    assert len(parsed.rows) == 14
    assert parsed.numeric_row_count == 12
    assert parsed.label_only_row_count == 2
    assert parsed.financial_slot_count == 24
    assert parsed.observation_count(ObservationKind.VALUE) == 14
    assert parsed.observation_count(ObservationKind.DASH) == 8
    assert parsed.observation_count(ObservationKind.BLANK) == 2
    assert parsed.observation_count(ObservationKind.ZERO) == 0
    assert parsed.observation_count(ObservationKind.INVALID) == 0
    assert parsed.unassigned_numeric_line_indices == ()
    assert parsed.excluded_footer_numeric_line_indices == (40,)
    assert parsed.mapping_authority is False


def test_page45_binds_duration_snapshot_periods_and_row_local_units(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    eps_axes = parsed.tables[0].axes
    share_axes = parsed.tables[1].axes

    assert [axis.semantic_role for axis in eps_axes] == ["CURRENT", "COMPARATIVE"]
    assert [axis.period_start for axis in eps_axes] == [
        date(2026, 1, 1),
        date(2025, 1, 1),
    ]
    assert [axis.period_end for axis in eps_axes] == [
        date(2026, 3, 31),
        date(2025, 3, 31),
    ]
    assert {axis.period_type for axis in eps_axes} == {"DURATION"}
    assert [axis.unit_line_index for axis in eps_axes] == [5, 6]
    assert [axis.period_start for axis in share_axes] == [
        date(2026, 3, 31),
        date(2025, 12, 31),
    ]
    assert [axis.period_end for axis in share_axes] == [
        date(2026, 3, 31),
        date(2025, 12, 31),
    ]
    assert {axis.period_type for axis in share_axes} == {"SNAPSHOT"}
    assert [axis.unit_line_index for axis in share_axes] == [None, None]

    rows = [row for row in parsed.rows if isinstance(row, TMPage45LogicalRow)]
    assert [(row.canonical_unit, row.unit_multiplier) for row in rows[:3]] == [
        ("VND", 1_000_000),
        ("SHARE", 1),
        ("VND_PER_SHARE", 1),
    ]
    assert {(row.canonical_unit, row.unit_multiplier) for row in rows[3:]} == {("SHARE", 1)}
    assert rows[0].unit_evidence == "TABLE_LOCAL_HEADER"
    assert rows[0].unit_source_line_indices == (5, 6)
    assert all(row.unit_evidence == "ROW_LOCAL_LABEL" for row in rows[1:])
    assert all(row.cell_period_roles == ("CURRENT", "COMPARATIVE") for row in rows)


def test_page45_preserves_source_values_and_eps_consistency_without_imputation(
    project_root: Path, tmp_path: Path
) -> None:
    rows = {
        row.semantic_role: row
        for row in _parsed(project_root, tmp_path).rows
        if isinstance(row, TMPage45LogicalRow)
    }

    assert [
        [cell.value for cell in rows[role].row.cells]
        for role in (
            "PROFIT_ATTRIBUTABLE_TO_BANK_SHAREHOLDERS",
            "WEIGHTED_AVERAGE_ORDINARY_SHARES",
            "BASIC_EARNINGS_PER_SHARE",
        )
    ] == [
        [7_515_513, 6_567_740],
        [8_054_999_909, 8_054_999_909],
        [933, 815],
    ]
    share_values = [
        [cell.value for cell in row.row.cells]
        for row in rows.values()
        if row.table_key == "SHARE_COUNTS"
        and all(cell.observation is ObservationKind.VALUE for cell in row.row.cells)
    ]
    assert share_values == [[8_054_999_909, 8_054_999_909]] * 4

    profit = rows["PROFIT_ATTRIBUTABLE_TO_BANK_SHAREHOLDERS"].row.cells
    weighted = rows["WEIGHTED_AVERAGE_ORDINARY_SHARES"].row.cells
    eps = rows["BASIC_EARNINGS_PER_SHARE"].row.cells
    independently_checked = [
        (profit[index].value * 1_000_000 / weighted[index].value).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        for index in range(2)
    ]
    assert independently_checked == [cell.value for cell in eps]
    assert all(not row.mapping_approved for row in rows.values())


def test_eight_dashes_and_two_blanks_have_distinct_render_evidence(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    dash_evidence = []
    blank_evidence = []
    for row in parsed.rows:
        if not isinstance(row, TMPage45LogicalRow):
            continue
        for cell, evidence in zip(row.row.cells, row.visual_cell_evidence, strict=True):
            if cell.observation is ObservationKind.DASH:
                dash_evidence.append(evidence)
            elif cell.observation is ObservationKind.BLANK:
                blank_evidence.append(evidence)

    assert [evidence.component_box for evidence in dash_evidence if evidence] == [
        (1835, 1307, 1847, 1312),
        (2250, 1307, 2263, 1312),
        (1835, 1354, 1847, 1359),
        (2249, 1355, 2263, 1360),
        (1833, 1403, 1845, 1408),
        (2249, 1403, 2261, 1408),
        (1832, 1565, 1845, 1570),
        (2247, 1565, 2260, 1570),
    ]
    assert all(
        evidence is not None
        and evidence.observation == "DASH"
        and evidence.foreground_contrast > 130
        for evidence in dash_evidence
    )
    assert [evidence.crop_box for evidence in blank_evidence if evidence] == [
        (1595, 1085, 1868, 1142),
        (2008, 1085, 2281, 1142),
    ]
    assert all(
        isinstance(evidence, TMPage45BlankEvidence)
        and evidence.observation == "BLANK"
        and evidence.minimum_intensity == 255
        and evidence.foreground_pixel_count == 0
        for evidence in blank_evidence
    )


def test_missing_dash_pixel_fails_closed_instead_of_using_missing_ocr(
    project_root: Path, tmp_path: Path
) -> None:
    render = _render(project_root, tmp_path)
    image = cv2.imread(str(render), cv2.IMREAD_COLOR)
    assert image is not None
    image[1295:1320, 1825:1855] = 255
    mutated = tmp_path / "missing-share-dash.png"
    assert cv2.imwrite(str(mutated), image)
    mutated_render_sha256 = sha256_file(mutated)
    payload = json.loads((project_root / _FIXTURE).read_text(encoding="utf-8"))
    payload["source_render_sha256"] = mutated_render_sha256
    mutated_fixture = tmp_path / "missing-share-dash.json"
    mutated_fixture.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    policy = replace(
        _policy(project_root),
        source_render_sha256=mutated_render_sha256,
        source_ocr_sha256=sha256_file(mutated_fixture),
    )

    with pytest.raises(TMNoteWordBoxError, match="lacks dash pixel evidence"):
        parse_tm_page45(mutated_fixture, mutated, policy)


def test_nonwhite_registered_share_cell_fails_closed_instead_of_becoming_blank(
    project_root: Path, tmp_path: Path
) -> None:
    render = _render(project_root, tmp_path)
    image = cv2.imread(str(render), cv2.IMREAD_COLOR)
    assert image is not None
    image[1100:1110, 1800:1810] = 0
    mutated = tmp_path / "nonblank-registered-share.png"
    assert cv2.imwrite(str(mutated), image)
    mutated_render_sha256 = sha256_file(mutated)
    payload = json.loads((project_root / _FIXTURE).read_text(encoding="utf-8"))
    payload["source_render_sha256"] = mutated_render_sha256
    mutated_fixture = tmp_path / "nonblank-registered-share.json"
    mutated_fixture.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    policy = replace(
        _policy(project_root),
        source_render_sha256=mutated_render_sha256,
        source_ocr_sha256=sha256_file(mutated_fixture),
    )

    with pytest.raises(TMNoteWordBoxError, match="lacks all-white blank pixel evidence"):
        parse_tm_page45(mutated_fixture, mutated, policy)


def test_visible_period_and_header_unit_drift_fail_closed(
    project_root: Path, tmp_path: Path
) -> None:
    fixture = project_root / _FIXTURE
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    payload["rec_texts"][1] = "Từ 02/01/2026"
    period_fixture = tmp_path / "page45-period-drift.json"
    period_fixture.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    render = _render(project_root, tmp_path)
    with pytest.raises(TMNoteWordBoxError, match="visible period drifted"):
        parse_tm_page45(
            period_fixture,
            render,
            replace(_policy(project_root), source_ocr_sha256=sha256_file(period_fixture)),
        )

    payload = json.loads(fixture.read_text(encoding="utf-8"))
    payload["rec_texts"][5] = "Nghìn đồng"
    unit_fixture = tmp_path / "page45-unit-drift.json"
    unit_fixture.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(TMNoteWordBoxError, match="unit denominator drifted"):
        parse_tm_page45(
            unit_fixture,
            render,
            replace(_policy(project_root), source_ocr_sha256=sha256_file(unit_fixture)),
        )


def test_page45_policy_forbids_blank_dash_zero_and_schema_semantic_leakage(
    project_root: Path,
) -> None:
    assert set(_policy(project_root).forbidden_semantic_inputs) == {
        "missing_ocr_cell_as_dash_without_pixel_evidence",
        "missing_ocr_cell_as_blank_without_pixel_evidence",
        "header_trieu_dong_as_unit_for_share_or_eps_rows",
        "template_labels_as_row_reconstruction_input",
        "approved_report_norm_id_assignment",
        "historical_or_mongodb_values",
        "human_review_answers",
        "dash_as_zero",
        "blank_as_zero",
        "accounting_equations_as_value_imputation",
    }
