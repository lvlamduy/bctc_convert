from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.tables.tm_note_pages32_33 import (
    load_tm_note_pages32_33_policy,
    parse_tm_note_pages32_33,
)
from bctc_ai.tables.tm_note_word_box import TMNoteWordBoxError

_POLICY = Path("config/tables/tm-note-pages32-33-v1.yaml")
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_FIXTURES = {
    32: Path("tests/golden/tm/mbb-q1-2026-page-0032-ppocrv6-word-box.json"),
    33: Path("tests/golden/tm/mbb-q1-2026-page-0033-ppocrv6-word-box.json"),
}
_FIXTURE_HASHES = {
    32: "823f52c0473ff095886952c3438b5a1ca92703ae6dc7b906834ee85db772a21a",
    33: "0f27707f8a38ef3552498df3fbdf469529259f3b23065ff03756985a94cee155",
}


def _parsed(project_root: Path, tmp_path: Path):
    renders = {
        item.page: Path(item.path)
        for item in render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={32, 33},
        )
    }
    return parse_tm_note_pages32_33(
        {page: (project_root / fixture, renders[page]) for page, fixture in _FIXTURES.items()},
        load_tm_note_pages32_33_policy(project_root / _POLICY),
    )


def test_real_pages32_33_reconstruct_exact_source_denominator(
    project_root: Path, tmp_path: Path
) -> None:
    for page, fixture in _FIXTURES.items():
        assert sha256_file(project_root / fixture) == _FIXTURE_HASHES[page]
    parsed = _parsed(project_root, tmp_path)

    assert parsed.scope == "CONSOLIDATED"
    assert parsed.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert [page.page_number for page in parsed.pages] == [32, 33]
    assert [len(page.rows) for page in parsed.pages] == [22, 24]
    assert [page.numeric_row_count for page in parsed.pages] == [21, 23]
    assert [page.label_only_row_count for page in parsed.pages] == [1, 1]
    assert [page.financial_slot_count for page in parsed.pages] == [84, 92]
    assert len(parsed.rows) == 46
    assert parsed.numeric_row_count == 44
    assert parsed.label_only_row_count == 2
    assert parsed.financial_slot_count == 176
    assert parsed.observation_count(ObservationKind.VALUE) == 174
    assert parsed.observation_count(ObservationKind.ZERO) == 2
    assert parsed.mapping_authority is False


def test_mixed_axes_bind_period_unit_measure_and_scope_locally(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    expected = [
        ("AMOUNT", "CURRENT", date(2026, 3, 31), "VND", 1_000_000),
        ("PERCENTAGE", "CURRENT", date(2026, 3, 31), "PERCENT", 1),
        ("AMOUNT", "COMPARATIVE", date(2025, 12, 31), "VND", 1_000_000),
        ("PERCENTAGE", "COMPARATIVE", date(2025, 12, 31), "PERCENT", 1),
    ]
    for page in parsed.pages:
        assert [
            (
                axis.measure_role,
                axis.period_role,
                axis.period_end,
                axis.canonical_unit,
                axis.unit_multiplier,
            )
            for axis in page.axes
        ] == expected
        assert all(axis.period_type == "SNAPSHOT" for axis in page.axes)
        assert page.scope == "CONSOLIDATED"


def test_multiline_unlabelled_and_zero_rows_preserve_exact_source_values(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    by_key = {(row.page_tag, row.row_key): row for row in parsed.rows}

    assert [cell.value for cell in by_key[("page-0032", "STATE_OWNED_OVER_50")].row.cells] == [
        Decimal("4853278"),
        Decimal("0.43"),
        Decimal("4337893"),
        Decimal("0.40"),
    ]
    partnership = by_key[("page-0032", "PARTNERSHIP")]
    assert [cell.value for cell in partnership.row.cells] == [
        Decimal("303"),
        Decimal("0.00"),
        Decimal("319"),
        Decimal("0.00"),
    ]
    assert [cell.observation for cell in partnership.row.cells] == [
        ObservationKind.VALUE,
        ObservationKind.ZERO,
        ObservationKind.VALUE,
        ObservationKind.ZERO,
    ]
    assert len(by_key[("page-0033", "HOUSEHOLD_EMPLOYMENT")].label_line_indices) == 4
    assert [cell.value for cell in by_key[("page-0033", "HOUSEHOLD_EMPLOYMENT")].row.cells] == [
        Decimal("264294420"),
        Decimal("23.58"),
        Decimal("239172416"),
        Decimal("22.05"),
    ]
    assert by_key[("page-0032", "BANK_SUBTOTAL")].row.label == ""
    assert by_key[("page-0033", "GRAND_TOTAL")].row.label == ""


def test_all_visible_table_tokens_are_accounted_for_without_artifact_imputation(
    project_root: Path, tmp_path: Path
) -> None:
    parsed = _parsed(project_root, tmp_path)
    for page, footer_index in zip(parsed.pages, (117, 134), strict=True):
        assert page.unassigned_numeric_line_indices == ()
        assert page.unassigned_label_line_indices == ()
        assert page.excluded_artifact_numeric_line_indices == ()
        assert page.excluded_footer_numeric_line_indices == (footer_index,)
        assert all(
            bbox is not None
            for row in page.rows
            if row.financial_slot_count
            for bbox in row.value_bboxes
        )


def test_policy_and_input_identity_fail_closed(project_root: Path, tmp_path: Path) -> None:
    policy = load_tm_note_pages32_33_policy(project_root / _POLICY)
    with pytest.raises(TMNoteWordBoxError, match="exactly pages 32 and 33"):
        parse_tm_note_pages32_33({}, policy)

    text = (project_root / _POLICY).read_text(encoding="utf-8")
    tampered = tmp_path / "tampered.yaml"
    tampered.write_text(
        text.replace("TM_NOTE_PAGES32_33_LOAN_ANALYSIS_GRID_V1", "INVALID", 1),
        encoding="utf-8",
    )
    with pytest.raises(TMNoteWordBoxError, match="policy identity"):
        load_tm_note_pages32_33_policy(tampered)
