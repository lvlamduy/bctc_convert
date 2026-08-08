from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.tables.tm_note_pages39_40 import (
    load_tm_note_pages39_40_policy,
    parse_tm_note_pages39_40,
)
from bctc_ai.tables.tm_note_word_box import TMNoteWordBoxError

_POLICY = Path("config/tables/tm-note-pages39-40-v1.yaml")
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_FIXTURES = {
    39: Path("tests/golden/tm/mbb-q1-2026-page-0039-ppocrv6-word-box.json"),
    40: Path("tests/golden/tm/mbb-q1-2026-page-0040-ppocrv6-word-box.json"),
}
_FIXTURE_HASHES = {
    39: "8b7e78de01c0ff0d7fe43fbb296891e2fabd6ea7b7fa29244bf39c1d8cd56961",
    40: "120160a25446b66ae64697135da83f9dd9092bb0401f3b2e4a90b821c5268670",
}


def _parsed(project_root: Path, tmp_path: Path):
    renders = {
        item.page: Path(item.path)
        for item in render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={39, 40},
        )
    }
    return parse_tm_note_pages39_40(
        {page: (project_root / fixture, renders[page]) for page, fixture in _FIXTURES.items()},
        load_tm_note_pages39_40_policy(project_root / _POLICY),
    )


def test_real_pages39_40_reconstruct_exact_source_denominator(
    project_root: Path, tmp_path: Path
) -> None:
    for page, fixture in _FIXTURES.items():
        assert sha256_file(project_root / fixture) == _FIXTURE_HASHES[page]
    parsed = _parsed(project_root, tmp_path)

    assert parsed.scope == "CONSOLIDATED"
    assert parsed.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert [page.page_number for page in parsed.pages] == [39, 40]
    assert [len(page.rows) for page in parsed.pages] == [13, 17]
    assert [page.numeric_row_count for page in parsed.pages] == [10, 14]
    assert [page.label_only_row_count for page in parsed.pages] == [3, 3]
    assert [page.financial_slot_count for page in parsed.pages] == [40, 56]
    assert len(parsed.rows) == 30
    assert parsed.numeric_row_count == 24
    assert parsed.label_only_row_count == 6
    assert parsed.financial_slot_count == 96
    assert parsed.observation_count(ObservationKind.VALUE) == 79
    assert parsed.observation_count(ObservationKind.DASH) == 17
    assert parsed.mapping_authority is False


def test_four_asset_axes_bind_period_unit_and_scope_locally(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    expected_roles = [
        "FINITE_LAND_USE_RIGHTS",
        "COMPUTER_SOFTWARE",
        "OTHER_INTANGIBLE_ASSETS",
        "TOTAL",
    ]
    expected_periods = [
        ("CURRENT", date(2026, 1, 1), date(2026, 3, 31)),
        ("COMPARATIVE", date(2025, 1, 1), date(2025, 12, 31)),
    ]
    for page, period in zip(parsed.pages, expected_periods, strict=True):
        assert [axis.semantic_role for axis in page.axes] == expected_roles
        assert all(axis.canonical_unit == "VND" for axis in page.axes)
        assert all(axis.unit_multiplier == 1_000_000 for axis in page.axes)
        assert all(axis.period_type == "DURATION" for axis in page.axes)
        assert all(
            (axis.period_role, axis.period_start, axis.period_end) == period for axis in page.axes
        )
        assert page.scope == "CONSOLIDATED"


def test_all_visible_values_and_statuses_are_preserved_exactly(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    by_key = {(row.page_tag, row.row_key): row for row in parsed.rows}

    assert [cell.value for cell in by_key[("page-0039", "GROSS_INCREASE")].row.cells] == [
        None,
        74_774,
        2_323,
        77_097,
    ]
    assert [cell.value for cell in by_key[("page-0039", "NET_CLOSE")].row.cells] == [
        899_880,
        875_252,
        8_502,
        1_783_634,
    ]
    assert [cell.value for cell in by_key[("page-0040", "GROSS_LIQUIDATION")].row.cells] == [
        None,
        -105_478,
        None,
        -105_478,
    ]
    assert [cell.value for cell in by_key[("page-0040", "ACCUM_OTHER")].row.cells] == [
        None,
        -3_348,
        None,
        -3_348,
    ]
    assert [cell.value for cell in by_key[("page-0040", "NET_OPEN")].row.cells] == [
        893_797,
        778_480,
        7_443,
        1_679_720,
    ]


def test_dashes_require_pixel_evidence_and_tiny_ocr_artifact_is_excluded(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    page39, page40 = parsed.pages

    assert page39.unassigned_numeric_line_indices == ()
    assert page39.excluded_artifact_numeric_line_indices == ()
    assert page39.excluded_footer_numeric_line_indices == (60, 61)
    assert page40.unassigned_numeric_line_indices == ()
    assert page40.excluded_artifact_numeric_line_indices == (54,)
    assert page40.excluded_footer_numeric_line_indices == (74, 75)
    dash_cells = [
        (cell, evidence)
        for row in parsed.rows
        for cell, evidence in zip(row.row.cells, row.visual_cell_evidence, strict=True)
        if cell.observation is ObservationKind.DASH
    ]
    assert len(dash_cells) == 17
    assert all(cell.value is None and evidence is not None for cell, evidence in dash_cells)


def test_policy_and_input_identity_fail_closed(project_root: Path, tmp_path: Path) -> None:
    policy = load_tm_note_pages39_40_policy(project_root / _POLICY)
    with pytest.raises(TMNoteWordBoxError, match="exactly pages 39 and 40"):
        parse_tm_note_pages39_40({}, policy)

    text = (project_root / _POLICY).read_text(encoding="utf-8")
    tampered = tmp_path / "tampered.yaml"
    tampered.write_text(
        text.replace("TM_NOTE_PAGES39_40_INTANGIBLE_FIXED_GRID_V1", "INVALID", 1),
        encoding="utf-8",
    )
    with pytest.raises(TMNoteWordBoxError, match="policy identity"):
        load_tm_note_pages39_40_policy(tampered)
