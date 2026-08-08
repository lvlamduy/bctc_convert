from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import cv2
import pytest

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.tables.tm_note_page44 import load_tm_page44_policy, parse_tm_page44
from bctc_ai.tables.tm_note_word_box import TMNoteWordBoxError

_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0044-ppocrv6-word-box.json")
_FIXTURE_SHA256 = "cff4951371851eb88a3f33a5531a46075c01f0159df752bc52920fe8bafa74f8"
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")


def _policy(project_root: Path):
    return load_tm_page44_policy(project_root / "config/tables/tm-note-page44-v1.yaml")


def _render(project_root: Path, tmp_path: Path) -> Path:
    return Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={44},
        )[0].path
    )


def _parsed(project_root: Path, tmp_path: Path):
    return parse_tm_page44(
        project_root / _FIXTURE,
        _render(project_root, tmp_path),
        _policy(project_root),
    )


def test_real_page44_reconstructs_exact_mixed_grid_denominators(
    project_root: Path, tmp_path: Path
) -> None:
    fixture = project_root / _FIXTURE
    assert sha256_file(fixture) == _FIXTURE_SHA256

    parsed = _parsed(project_root, tmp_path)

    assert parsed.source_sha256 == _FIXTURE_SHA256
    assert parsed.source_render_sha256 == (
        "81b5bfecd4c1b50895e0ac6e6e71707bc90a9646f21a4e92f8f7695c6c557152"
    )
    assert parsed.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert parsed.scope == "CONSOLIDATED"
    assert [table.table_key for table in parsed.tables] == [
        "PAPER_ISSUANCE",
        "OTHER_PAYABLES",
        "EQUITY_MOVEMENT",
    ]
    assert [len(table.rows) for table in parsed.tables] == [8, 4, 12]
    assert len(parsed.rows) == 24
    assert parsed.numeric_row_count == 20
    assert parsed.label_only_row_count == 4
    assert parsed.financial_slot_count == 60
    assert parsed.observation_count(ObservationKind.VALUE) == 51
    assert parsed.observation_count(ObservationKind.DASH) == 9
    assert parsed.unassigned_numeric_line_indices == ()
    assert parsed.excluded_footer_numeric_line_indices == (98,)
    assert parsed.mapping_authority is False


def test_snapshot_and_equity_axes_bind_period_unit_and_semantic_roles(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)

    for table in parsed.tables[:2]:
        assert [axis.semantic_role for axis in table.axes] == ["CURRENT", "COMPARATIVE"]
        assert [axis.period_end for axis in table.axes] == [
            date(2026, 3, 31),
            date(2025, 12, 31),
        ]
        assert {axis.period_type for axis in table.axes} == {"SNAPSHOT"}
        assert {axis.canonical_unit for axis in table.axes} == {"VND"}
        assert {axis.unit_multiplier for axis in table.axes} == {1_000_000}
    equity = parsed.tables[2]
    assert [axis.semantic_role for axis in equity.axes] == [
        "BEGINNING_BALANCE",
        "INCREASE",
        "DECREASE",
        "ENDING_BALANCE",
    ]
    assert [axis.period_type for axis in equity.axes] == ["SNAPSHOT", "FLOW", "FLOW", "SNAPSHOT"]
    assert [axis.period_end for axis in equity.axes] == [
        date(2025, 12, 31),
        date(2026, 3, 31),
        date(2026, 3, 31),
        date(2026, 3, 31),
    ]


def test_all_nine_dashes_have_exact_render_pixel_evidence_and_are_not_zero(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    dash_cells = [
        (cell, evidence)
        for row in parsed.rows
        for cell, evidence in zip(row.row.cells, row.visual_cell_evidence, strict=True)
        if cell.observation is ObservationKind.DASH
    ]

    assert [evidence.component_box for _cell, evidence in dash_cells if evidence] == [
        (1638, 2163, 1650, 2167),
        (1929, 2163, 1941, 2167),
        (1638, 2212, 1650, 2217),
        (1929, 2212, 1941, 2217),
        (1637, 2262, 1650, 2266),
        (1928, 2262, 1940, 2266),
        (1928, 2386, 1940, 2391),
        (1635, 2449, 1649, 2454),
        (1926, 2574, 1938, 2578),
    ]
    assert all(
        cell.value is None
        and evidence is not None
        and evidence.observation == "DASH"
        and evidence.foreground_contrast > 140
        for cell, evidence in dash_cells
    )


def test_missing_dash_pixel_fails_closed_instead_of_using_missing_ocr(
    project_root: Path, tmp_path: Path
) -> None:
    render = _render(project_root, tmp_path)
    image = cv2.imread(str(render), cv2.IMREAD_COLOR)
    assert image is not None
    image[2140:2190, 1610:1670] = 255
    mutated = tmp_path / "missing-equity-dash.png"
    assert cv2.imwrite(str(mutated), image)
    policy = replace(_policy(project_root), source_render_sha256=sha256_file(mutated))

    with pytest.raises(TMNoteWordBoxError, match="lacks dash pixel evidence"):
        parse_tm_page44(project_root / _FIXTURE, mutated, policy)


def test_five_narrative_facts_and_seven_values_remain_source_only(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    facts = {fact.fact_id: fact for fact in parsed.narrative_facts}

    assert len(facts) == 5
    assert parsed.narrative_value_count == 7
    assert facts["BANK_BOND_INTEREST_RATE_RANGE"].values == (
        Decimal("5.00"),
        Decimal("8.80"),
    )
    assert facts["CERTIFICATE_INTEREST_RATE_RANGE"].values == (
        Decimal("4.40"),
        Decimal("11.18"),
    )
    assert facts["ISSUED_SHARE_COUNT"].values == (8_054_999_909,)
    assert facts["PAR_VALUE"].values == (10_000,)
    assert facts["STATED_CHARTER_CAPITAL"].values == (80_549_999,)
    assert all(fact.status == "SOURCE_ONLY_PROVENANCE" for fact in facts.values())


def test_page44_policy_forbids_missing_ocr_dash_inference_and_semantic_leakage(
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
