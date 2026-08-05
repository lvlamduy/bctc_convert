from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.text import (
    normalize_text,
    parse_financial_number,
    parse_unit,
    parse_vietnamese_date,
    parse_vietnamese_dates,
    retrieval_key,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Ngày 30 tháng 06 năm 2026", date(2026, 6, 30)),
        ("Tại ngày 31 tháng 12 năm 2025", date(2025, 12, 31)),
        ("30/06/2026", date(2026, 6, 30)),
        ("31.12.2025", date(2025, 12, 31)),
        ("31/02/2025", None),
    ],
)
def test_vietnamese_date_parser(raw, expected):
    assert parse_vietnamese_date(raw) == expected


def test_vietnamese_date_parser_preserves_explicit_range_order():
    assert parse_vietnamese_dates("Từ ngày 1 tháng 1 năm 2026 đến ngày 31 tháng 3 năm 2026") == (
        date(2026, 1, 1),
        date(2026, 3, 31),
    )


@pytest.mark.parametrize(
    ("raw", "value", "observation", "sign"),
    [
        ("", None, ObservationKind.BLANK, None),
        ("–", None, ObservationKind.DASH, "dash"),
        ("0", Decimal("0"), ObservationKind.ZERO, None),
        ("(1.234)", Decimal("-1234"), ObservationKind.VALUE, "parentheses"),
        ("12 345-", Decimal("-12345"), ObservationKind.VALUE, "trailing_minus"),
        ("1.234,56", Decimal("1234.56"), ObservationKind.VALUE, None),
        ("N/A", None, ObservationKind.NOT_APPLICABLE, None),
    ],
)
def test_financial_number_preserves_observation_and_sign(raw, value, observation, sign):
    parsed = parse_financial_number(raw)
    assert parsed.value == value
    assert parsed.observation is observation
    assert parsed.sign_evidence == sign


def test_invalid_numeric_is_not_guessed():
    parsed = parse_financial_number("1O0")
    assert parsed.value is None
    assert parsed.observation is ObservationKind.INVALID


def test_multiple_financial_numbers_in_one_cell_are_rejected_explicitly():
    parsed = parse_financial_number("198.242 (5.140.484)")

    assert parsed.value is None
    assert parsed.observation is ObservationKind.INVALID
    assert parsed.reason == "multiple financial numbers in one cell"


def test_unicode_normalization_and_retrieval_are_separate():
    assert normalize_text("  Vốn\u200b  chủ  sở hữu … ") == "Vốn chủ sở hữu ..."
    assert retrieval_key("Vốn chủ sở hữu") == "von chu so huu"


def test_unit_parser():
    assert parse_unit("Đơn vị tính: triệu VND").multiplier == 1_000_000
    assert parse_unit("Đơn vị: nghìn đồng").multiplier == 1_000
    assert parse_unit("USD").canonical is None
