from __future__ import annotations

import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import cv2
import pytest

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.tables.tm_note_page35 import load_tm_page35_policy, parse_tm_page35
from bctc_ai.tables.tm_note_word_box import TMNoteRowKind, TMNoteWordBoxError

_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0035-ppocrv6-word-box.json")
_FIXTURE_SHA256 = "e1afe9756a3a7bd870b2da2b13fa195f7ba669fd4e9f4d4ce30c41de1d3ceb31"
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")


def _policy(project_root: Path):
    return load_tm_page35_policy(project_root / "config/tables/tm-note-page35-v1.yaml")


def _render(project_root: Path, tmp_path: Path) -> Path:
    return Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={35},
        )[0].path
    )


def _parsed(project_root: Path, tmp_path: Path):
    return parse_tm_page35(
        project_root / _FIXTURE,
        _render(project_root, tmp_path),
        _policy(project_root),
    )


def test_real_page35_reconstructs_three_tables_and_exact_source_denominator(
    project_root: Path, tmp_path: Path
) -> None:
    fixture = project_root / _FIXTURE
    assert sha256_file(fixture) == _FIXTURE_SHA256

    parsed = _parsed(project_root, tmp_path)

    assert parsed.source_sha256 == _FIXTURE_SHA256
    assert parsed.source_render_sha256 == (
        "941d1d46d4d6f55451ef98d0bad4d46638f01cc8b0dac428b7253209933a6496"
    )
    assert parsed.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert parsed.scope == "CONSOLIDATED"
    assert [table.table_key for table in parsed.tables] == [
        "PURCHASED_NET",
        "PURCHASED_DETAIL",
        "AFS_SECURITIES",
    ]
    assert [len(table.rows) for table in parsed.tables] == [3, 3, 8]
    assert len(parsed.rows) == 14
    assert parsed.numeric_row_count == 13
    assert parsed.label_only_row_count == 1
    assert parsed.financial_slot_count == 26
    assert parsed.observation_count(ObservationKind.VALUE) == 24
    assert parsed.observation_count(ObservationKind.DASH) == 2
    assert parsed.unassigned_numeric_line_indices == ()
    assert parsed.excluded_footer_numeric_line_indices == (70,)
    assert parsed.mapping_authority is False


def test_all_local_headers_bind_snapshot_period_unit_and_scope(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)

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


def test_ocr_missing_interest_cells_are_dash_only_with_exact_pixel_components(
    project_root: Path, tmp_path: Path
) -> None:
    payload = json.loads((project_root / _FIXTURE).read_text(encoding="utf-8"))
    assert "-" not in payload["rec_texts"]
    parsed = _parsed(project_root, tmp_path)
    interest = parsed.tables[1].rows[1]

    assert interest.row_kind is TMNoteRowKind.NUMERIC
    assert interest.row.label == "Lãi ca khon n đã mua"
    assert interest.value_line_indices == ((), ())
    assert [cell.observation for cell in interest.row.cells] == [
        ObservationKind.DASH,
        ObservationKind.DASH,
    ]
    assert [cell.value for cell in interest.row.cells] == [None, None]
    assert [evidence.component_box for evidence in interest.visual_cell_evidence if evidence] == [
        (1838, 1021, 1850, 1026),
        (2193, 1018, 2206, 1023),
    ]
    assert all(
        evidence is not None
        and evidence.observation == "DASH"
        and evidence.foreground_contrast > 150
        and evidence.aspect_ratio >= 2.4
        for evidence in interest.visual_cell_evidence
    )


def test_missing_dash_pixels_fail_closed_instead_of_coercing_missing_ocr_to_dash(
    project_root: Path, tmp_path: Path
) -> None:
    render = _render(project_root, tmp_path)
    image = cv2.imread(str(render), cv2.IMREAD_COLOR)
    assert image is not None
    image[995:1070, 1770:1875] = 255
    image[995:1070, 2125:2230] = 255
    mutated = tmp_path / "missing-dashes.png"
    assert cv2.imwrite(str(mutated), image)
    policy = replace(_policy(project_root), source_render_sha256=sha256_file(mutated))

    with pytest.raises(TMNoteWordBoxError, match="lacks constrained pixel evidence"):
        parse_tm_page35(project_root / _FIXTURE, mutated, policy)


def test_visible_values_provisions_totals_and_structural_row_remain_distinct(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    purchased, detail, afs = parsed.tables

    assert [[cell.value for cell in row.row.cells] for row in purchased.rows] == [
        [2_287_269, 2_465_314],
        [-23_194, -21_419],
        [2_264_075, 2_443_895],
    ]
    assert [[cell.value for cell in row.row.cells] for row in detail.rows] == [
        [2_287_269, 2_465_314],
        [None, None],
        [2_287_269, 2_465_314],
    ]
    assert afs.rows[0].row_kind is TMNoteRowKind.LABEL_ONLY
    assert all(cell.observation is ObservationKind.BLANK for cell in afs.rows[0].row.cells)
    assert [[cell.value for cell in row.row.cells] for row in afs.rows[-3:]] == [
        [259_054_739, 221_512_464],
        [-498_572, -163_351],
        [258_556_167, 221_349_113],
    ]


def test_page35_policy_forbids_missing_ocr_dash_inference_and_dash_as_zero(
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
    }
