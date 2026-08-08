from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import cv2
import pytest

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.tables.tm_note_page47 import load_tm_page47_policy, parse_tm_page47
from bctc_ai.tables.tm_note_word_box import TMNoteRowKind, TMNoteWordBoxError

_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0047-ppocrv6-word-box.json")
_FIXTURE_SHA256 = "6dd245762d418b0ab85e28f6fdf50423a8411436afe0a3391a822c18e71f790d"
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")


def _policy(project_root: Path):
    return load_tm_page47_policy(project_root / "config/tables/tm-note-page47-v1.yaml")


def _render(project_root: Path, tmp_path: Path) -> Path:
    return Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={47},
        )[0].path
    )


def _parsed(project_root: Path, tmp_path: Path):
    return parse_tm_page47(
        project_root / _FIXTURE,
        _render(project_root, tmp_path),
        _policy(project_root),
    )


def test_real_page47_reconstructs_three_complete_notes_and_exact_denominator(
    project_root: Path, tmp_path: Path
) -> None:
    assert sha256_file(project_root / _FIXTURE) == _FIXTURE_SHA256

    parsed = _parsed(project_root, tmp_path)

    assert parsed.source_sha256 == _FIXTURE_SHA256
    assert parsed.source_render_sha256 == (
        "42201a9afdec2297c43adfe0c8e504b3fdab911bab19bc4362bb8b048658e211"
    )
    assert parsed.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert parsed.scope == "CONSOLIDATED"
    assert [table.table_key for table in parsed.tables] == [
        "NET_FX",
        "NET_SECURITIES",
        "NET_OTHER",
    ]
    assert [len(table.rows) for table in parsed.tables] == [10, 13, 5]
    assert len(parsed.rows) == 28
    assert parsed.numeric_row_count == 21
    assert parsed.label_only_row_count == 7
    assert parsed.financial_slot_count == 42
    assert parsed.observation_count(ObservationKind.VALUE) == 41
    assert parsed.observation_count(ObservationKind.DASH) == 1
    assert parsed.unassigned_numeric_line_indices == ()
    assert parsed.excluded_artifact_line_indices == ()
    assert parsed.excluded_footer_numeric_line_indices == (90,)
    assert parsed.mapping_authority is False


def test_three_local_headers_bind_duration_period_unit_and_scope(
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


def test_wrapped_labels_totals_and_mixed_dash_value_stay_distinct(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    fx, securities, other = parsed.tables

    assert [row.row_kind for row in fx.rows[:3]] == [
        TMNoteRowKind.LABEL_ONLY,
        TMNoteRowKind.LABEL_ONLY,
        TMNoteRowKind.NUMERIC,
    ]
    assert [[cell.value for cell in row.row.cells] for row in fx.rows[4:10]] == [
        [2_305_327, 1_270_013],
        [None, None],
        [-486_848, -221_138],
        [-1_850_185, -511_075],
        [-2_337_033, -732_213],
        [-31_706, 537_800],
    ]
    assert securities.rows[1].row.label.endswith("kinh doanh")
    assert securities.rows[8].row.label == "Chi vè chng khoán đu tư"
    assert securities.rows[9].row.label.endswith("khoán đu tư")
    mixed = securities.rows[10]
    assert [cell.observation for cell in mixed.row.cells] == [
        ObservationKind.DASH,
        ObservationKind.VALUE,
    ]
    assert [cell.value for cell in mixed.row.cells] == [None, 20_861]
    assert mixed.visual_cell_evidence[0] is not None
    assert mixed.visual_cell_evidence[0].component_box == (1851, 2022, 1863, 2026)
    assert mixed.visual_cell_evidence[1] is None
    assert [[cell.value for cell in row.row.cells] for row in other.rows[1:]] == [
        [733_893, 1_003_397],
        [104_566, 62_557],
        [252_019, 113_256],
        [1_090_478, 1_179_210],
    ]


def test_missing_mixed_dash_pixels_fail_closed_and_policy_forbids_dash_to_zero(
    project_root: Path, tmp_path: Path
) -> None:
    render = _render(project_root, tmp_path)
    image = cv2.imread(str(render), cv2.IMREAD_COLOR)
    assert image is not None
    image[1980:2060, 1800:1910] = 255
    mutated = tmp_path / "missing-page47-dash.png"
    assert cv2.imwrite(str(mutated), image)
    policy = replace(_policy(project_root), source_render_sha256=sha256_file(mutated))

    with pytest.raises(TMNoteWordBoxError, match="lacks constrained pixel evidence"):
        parse_tm_page47(project_root / _FIXTURE, mutated, policy)

    assert set(_policy(project_root).forbidden_semantic_inputs) == {
        "missing_ocr_cell_as_dash_without_pixel_evidence",
        "template_labels_as_row_reconstruction_input",
        "approved_report_norm_id_assignment",
        "historical_or_mongodb_values",
        "human_review_answers",
        "dash_as_zero",
        "accounting_equations_as_value_imputation",
    }
