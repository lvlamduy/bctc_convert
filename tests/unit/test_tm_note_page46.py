from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import cv2
import pytest

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.tables.tm_note_page46 import load_tm_page46_policy, parse_tm_page46
from bctc_ai.tables.tm_note_word_box import TMNoteRowKind, TMNoteWordBoxError

_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0046-ppocrv6-word-box.json")
_FIXTURE_SHA256 = "36b3dd7e53f1cb4fb71af045796df646258c0e6fcb93677c0f360174dcdb2a19"
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")


def _policy(project_root: Path):
    return load_tm_page46_policy(project_root / "config/tables/tm-note-page46-v1.yaml")


def _render(project_root: Path, tmp_path: Path) -> Path:
    return Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={46},
        )[0].path
    )


def _parsed(project_root: Path, tmp_path: Path):
    return parse_tm_page46(
        project_root / _FIXTURE,
        _render(project_root, tmp_path),
        _policy(project_root),
    )


def test_real_page46_reconstructs_two_complete_notes_and_exact_source_denominator(
    project_root: Path, tmp_path: Path
) -> None:
    assert sha256_file(project_root / _FIXTURE) == _FIXTURE_SHA256

    parsed = _parsed(project_root, tmp_path)

    assert parsed.source_sha256 == _FIXTURE_SHA256
    assert parsed.source_render_sha256 == (
        "0eba425a417160736c707077dd9965265d5fe131e63cb2ad8cdef1018f71577d"
    )
    assert parsed.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert parsed.scope == "CONSOLIDATED"
    assert [table.table_key for table in parsed.tables] == ["NET_INTEREST", "NET_SERVICE"]
    assert [len(table.rows) for table in parsed.tables] == [17, 21]
    assert len(parsed.rows) == 38
    assert parsed.numeric_row_count == 31
    assert parsed.label_only_row_count == 7
    assert parsed.financial_slot_count == 62
    assert parsed.observation_count(ObservationKind.VALUE) == 60
    assert parsed.observation_count(ObservationKind.DASH) == 2
    assert parsed.unassigned_numeric_line_indices == ()
    assert parsed.excluded_artifact_line_indices == (77, 93)
    assert parsed.excluded_footer_numeric_line_indices == (113,)
    assert parsed.mapping_authority is False


def test_both_local_headers_bind_duration_period_unit_and_scope(
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


def test_values_totals_structural_rows_and_pixel_backed_dash_stay_distinct(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    interest, service = parsed.tables

    assert [row.row_kind for row in interest.rows[:4]] == [
        TMNoteRowKind.LABEL_ONLY,
        TMNoteRowKind.LABEL_ONLY,
        TMNoteRowKind.LABEL_ONLY,
        TMNoteRowKind.NUMERIC,
    ]
    assert [[cell.value for cell in row.row.cells] for row in interest.rows[9:17]] == [
        [28_982_071, 19_590_312],
        [None, None],
        [-10_006_884, -5_509_757],
        [-1_243_975, -453_089],
        [-2_812_704, -1_858_864],
        [-5_391, -76_418],
        [-14_068_954, -7_898_128],
        [14_913_117, 11_692_184],
    ]
    consulting = service.rows[13]
    assert consulting.row.label == "Chi v dch v tư vn"
    assert consulting.value_line_indices == ((), ())
    assert [cell.observation for cell in consulting.row.cells] == [
        ObservationKind.DASH,
        ObservationKind.DASH,
    ]
    assert [cell.value for cell in consulting.row.cells] == [None, None]
    assert [evidence.component_box for evidence in consulting.visual_cell_evidence if evidence] == [
        (1827, 2475, 1841, 2479),
        (2240, 2475, 2252, 2479),
    ]
    assert [[cell.value for cell in row.row.cells] for row in service.rows[-2:]] == [
        [-2_875_070, -2_376_545],
        [1_708_744, 1_235_416],
    ]


def test_missing_dash_pixels_fail_closed_and_policy_forbids_dash_to_zero(
    project_root: Path, tmp_path: Path
) -> None:
    render = _render(project_root, tmp_path)
    image = cv2.imread(str(render), cv2.IMREAD_COLOR)
    assert image is not None
    image[2420:2510, 1770:1870] = 255
    image[2420:2510, 2180:2280] = 255
    mutated = tmp_path / "missing-page46-dashes.png"
    assert cv2.imwrite(str(mutated), image)
    policy = replace(_policy(project_root), source_render_sha256=sha256_file(mutated))

    with pytest.raises(TMNoteWordBoxError, match="lacks constrained pixel evidence"):
        parse_tm_page46(project_root / _FIXTURE, mutated, policy)

    assert set(_policy(project_root).forbidden_semantic_inputs) == {
        "missing_ocr_cell_as_dash_without_pixel_evidence",
        "template_labels_as_row_reconstruction_input",
        "approved_report_norm_id_assignment",
        "historical_or_mongodb_values",
        "human_review_answers",
        "dash_as_zero",
        "accounting_equations_as_value_imputation",
    }
