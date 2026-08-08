from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from bctc_ai.reconciliation.kqkd_numeric import (
    KQKDNumericVerificationError,
    normalize_pdf_text_reported_integer,
    verify_kqkd_numeric_page,
)
from bctc_ai.tables.kqkd_word_box import (
    load_kqkd_word_box_policy,
    parse_kqkd_word_box_page,
)

_OCR_FIXTURE = Path("tests/golden/kqkd/mbb-q1-2026-page-0006-ppocrv6-word-box.json")
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")


def _parsed(project_root: Path):
    return parse_kqkd_word_box_page(
        project_root / _OCR_FIXTURE,
        load_kqkd_word_box_policy(project_root / "config/tables/kqkd-word-box-v1.yaml"),
        page_tag="page-0006",
    )


def test_mbb_page6_pdf_text_layer_verifies_all_numbers_and_equations(project_root: Path):
    result = verify_kqkd_numeric_page(
        _parsed(project_root),
        project_root / _SOURCE_PDF,
        page_number=6,
    )

    assert result.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert result.source_render_sha256 == (
        "a180b79f80a106ff389410b96dd57f13687b99f21d5d3afb4b7f4b4e6b3e5e05"
    )
    assert result.source_ocr_sha256 == (
        "2ca7b17dc07834c6a2cfbbe80681e4e58ad96c3c8b4096c7f8ea0417e29a8f44"
    )
    assert result.assigned_pdf_text_token_count == 91
    assert result.cell_count == 88
    assert result.observed_cell_count == 88
    assert result.numeric_verified_cell_count == 88
    assert result.numeric_verified is True
    assert len(result.cell_by_key()) == 88
    assert result.accounting_equation_count == 8
    assert result.accounting_check_count == 32
    assert result.accounting_passed_check_count == 32
    assert result.accounting_verified is True
    assert result.mapping_authority is False
    assert result.fully_verified is False
    assert all(cell.mapping_authority is False for cell in result.cells)
    assert all(cell.fully_verified is False for cell in result.cells)
    assert result.verification_payload_sha256 == (
        "413e6769de42f41917c2bc5fed23b9b4a4eb64b69a56c7d9d4e5301ea7cac113"
    )
    assert result.accounting_payload_sha256 == (
        "4dc70f7eb6de6cd310291b5c8715c93042ae140e55ea042644e010e6e5d17205"
    )
    assert all(
        equation.residuals_by_axis == ("0", "0", "0", "0")
        for equation in result.accounting_equations
    )
    operating_income = next(
        equation
        for equation in result.accounting_equations
        if equation.equation_id == "TOTAL_OPERATING_INCOME"
    )
    assert operating_income.target_row_ordinal == 12
    assert [operand.row_ordinal for operand in operating_income.operands] == [
        3,
        6,
        7,
        8,
        9,
        10,
        11,
    ]
    assert operating_income.residuals_by_axis == ("0", "0", "0", "0")

    exceptional_groups = {
        (cell.row_ordinal, cell.axis_ordinal): tuple(token.text for token in cell.pdf_text_tokens)
        for cell in result.cells
        if len(cell.pdf_text_tokens) > 1 or "," in cell.pdf_text_joined
    }
    assert exceptional_groups == {
        (13, 2): ("(3,949.958)",),
        (15, 2): ("(2,986.414)",),
        (17, 4): ("(1.", "708.859)"),
        (19, 2): ("(1.", "711.446)"),
        (19, 3): ("(1,925.666)",),
        (19, 4): ("(1.", "711.446)"),
    }


def test_pdf_text_integer_normalizer_preserves_split_and_mixed_separator_evidence():
    assert normalize_pdf_text_reported_integer(("(3,949.958)",)) == Decimal(-3_949_958)
    assert normalize_pdf_text_reported_integer(("(1.", "708.859)")) == Decimal(-1_708_859)
    assert normalize_pdf_text_reported_integer(("30",)) == Decimal(30)

    with pytest.raises(KQKDNumericVerificationError, match="grouped integer"):
        normalize_pdf_text_reported_integer(("1.23",))


def test_pdf_text_disagreement_fails_closed(project_root: Path):
    parsed = _parsed(project_root)
    first_row = parsed.rows[0]
    first_cell = first_row.row.cells[0]
    altered_cell = replace(first_cell, value=first_cell.value + 1)
    altered_reader_row = replace(
        first_row.row,
        cells=(altered_cell, *first_row.row.cells[1:]),
    )
    altered_row = replace(first_row, row=altered_reader_row)
    altered = replace(parsed, rows=(altered_row, *parsed.rows[1:]))

    with pytest.raises(KQKDNumericVerificationError, match="independent numeric disagreement"):
        verify_kqkd_numeric_page(
            altered,
            project_root / _SOURCE_PDF,
            page_number=6,
        )
