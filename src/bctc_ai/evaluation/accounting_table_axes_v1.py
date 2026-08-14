"""Bank-blind helpers for accounting-table period, unit, and value axes.

The helpers consume only fresh semantic proposals plus bound geometry/source
text supplied by a family wrapper.  They do not know a bank, file, page, note,
family, or schema ID and grant no structural, numeric, or mapping authority on
their own.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)

__all__ = [
    "AccountingTableAxesV1Error",
    "center_x2_v1",
    "extract_period_axis_v1",
    "extract_typed_value_vector_v1",
    "is_number_like_v1",
    "money_integer_v1",
    "money_values_v1",
    "percentage_values_v1",
    "unit_kind_v1",
]


_NUMBER = re.compile(r"^[()]*[+-]?[0-9][0-9., ]*%?[()]*$")
_FULL_DATE = re.compile(r"(?<!\d)(\d{1,2})[./-](\d{1,2})[./-](\d{4})(?!\d)")
_DAY_MONTH = re.compile(r"\bngay\s+(\d{1,2})\s+thang\s+(\d{1,2})\b")
_YEAR = re.compile(r"\bnam\s+(\d{4})\b")


class AccountingTableAxesV1Error(ValueError):
    """A semantic line, geometry, or typed numeric surface drifted."""


def _error(message: str) -> AccountingTableAxesV1Error:
    return AccountingTableAxesV1Error(message)


def _bbox(line: Mapping[str, Any], label: str) -> list[int]:
    value = line.get("bbox")
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or value[0] < 0
        or value[1] < 0
        or value[0] >= value[2]
        or value[1] >= value[3]
    ):
        raise _error(f"{label} bbox drifted")
    return list(value)


def _text(line: Mapping[str, Any], label: str) -> str:
    value = line.get("vietocr_text")
    if type(value) is not str:
        raise _error(f"{label} VietOCR text drifted")
    return value


def _source_line_index(line: Mapping[str, Any], label: str) -> int:
    value = line.get("source_line_index")
    if type(value) is not int or value < 0:
        raise _error(f"{label} source line index drifted")
    return value


def _date_surface(day: int, month: int, year: int) -> str | None:
    try:
        date(year, month, day)
    except ValueError:
        return None
    return f"{day:02d}/{month:02d}/{year:04d}"


def center_x2_v1(line: Mapping[str, Any]) -> int:
    """Return twice the horizontal center without floating-point rounding."""

    box = _bbox(line, "semantic line")
    return box[0] + box[2]


def is_number_like_v1(value: str) -> bool:
    if type(value) is not str:
        raise _error("numeric surface must be one exact string")
    compact = value.strip().replace("\u00a0", " ").replace("\u202f", " ")
    return bool(compact and _NUMBER.fullmatch(compact) and any(char.isdigit() for char in compact))


def money_integer_v1(value: str) -> int | None:
    if type(value) is not str:
        raise _error("money surface must be one exact string")
    compact = value.strip().replace(" ", "")
    negative = compact.startswith("(") and compact.endswith(")")
    compact = compact.strip("()").lstrip("+")
    if compact.startswith("-"):
        negative = True
        compact = compact[1:]
    if (
        compact.endswith("%")
        or not compact
        or not all(char.isdigit() or char in ".," for char in compact)
    ):
        return None
    digits = compact.replace(".", "").replace(",", "")
    if not digits.isdigit():
        return None
    result = int(digits)
    return -result if negative else result


def _percentage(value: str) -> Decimal | None:
    compact = value.strip().replace(" ", "").rstrip("%").replace(",", ".")
    try:
        result = Decimal(compact)
    except InvalidOperation:
        return None
    return result if result.is_finite() else None


def unit_kind_v1(value: str) -> str | None:
    normalized = normalize_vietnamese_anchor_v1(value)
    if "%" in normalized:
        return "PERCENT"
    if "trieu" in normalized and ("vnd" in normalized or "dong" in normalized):
        return "MONEY"
    return None


def extract_period_axis_v1(
    lines: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    """Resolve exact, split, or relative two-period headers."""

    full: list[dict[str, Any]] = []
    partial: list[tuple[Mapping[str, Any], int, int]] = []
    years: list[tuple[Mapping[str, Any], int]] = []
    relative: list[dict[str, Any]] = []
    for line in lines:
        text = _text(line, "period header")
        normalized = normalize_vietnamese_anchor_v1(text)
        if matched := _FULL_DATE.search(text):
            day, month, year = map(int, matched.groups())
            surface = _date_surface(day, month, year)
            if surface is None:
                continue
            full.append(
                {
                    "evidence_source_line_indices": [
                        _source_line_index(line, "exact period header")
                    ],
                    "period": surface,
                    "x_center_x2": center_x2_v1(line),
                }
            )
            continue
        if matched := _DAY_MONTH.search(normalized):
            partial.append((line, int(matched.group(1)), int(matched.group(2))))
            continue
        if matched := _YEAR.search(normalized):
            years.append((line, int(matched.group(1))))
            continue
        if normalized == "so cuoi ky":
            relative.append(
                {
                    "evidence_source_line_indices": [
                        _source_line_index(line, "relative period header")
                    ],
                    "period": "CURRENT_PERIOD_END",
                    "x_center_x2": center_x2_v1(line),
                }
            )
        elif normalized == "so dau ky":
            relative.append(
                {
                    "evidence_source_line_indices": [
                        _source_line_index(line, "relative period header")
                    ],
                    "period": "COMPARATIVE_PERIOD_START",
                    "x_center_x2": center_x2_v1(line),
                }
            )
    if len(full) == 2:
        return sorted(full, key=lambda item: item["x_center_x2"]), "LOCAL_EXACT_DATES"
    if len(partial) == 2 and len(years) == 2:
        combined: list[dict[str, Any]] = []
        remaining = list(years)
        for line, day, month in sorted(partial, key=lambda item: center_x2_v1(item[0])):
            year_line, year = min(
                remaining, key=lambda item: abs(center_x2_v1(item[0]) - center_x2_v1(line))
            )
            remaining.remove((year_line, year))
            surface = _date_surface(day, month, year)
            if surface is None:
                return [], "UNRESOLVED"
            combined.append(
                {
                    "evidence_source_line_indices": [
                        _source_line_index(line, "split period header"),
                        _source_line_index(year_line, "split period year"),
                    ],
                    "period": surface,
                    "x_center_x2": center_x2_v1(line),
                }
            )
        return sorted(combined, key=lambda item: item["x_center_x2"]), "LOCAL_SPLIT_DATES"
    if len(relative) == 2:
        return sorted(relative, key=lambda item: item["x_center_x2"]), "LOCAL_RELATIVE_PERIOD_ROLES"
    return [], "UNRESOLVED"


def extract_typed_value_vector_v1(
    lines: Sequence[Mapping[str, Any]],
    lane_types: Sequence[str],
    *,
    primary_numeric_authority: bool,
) -> list[dict[str, Any]] | None:
    """Take the first ordered numeric surface for each declared lane."""

    if type(primary_numeric_authority) is not bool:
        raise _error("primary numeric authority flag drifted")
    if (
        isinstance(lane_types, (str, bytes))
        or not lane_types
        or any(type(item) is not str or item not in {"MONEY", "PERCENT"} for item in lane_types)
    ):
        raise _error("typed lane declaration drifted")
    numeric = sorted(
        (line for line in lines if is_number_like_v1(_text(line, "value line"))),
        key=center_x2_v1,
    )
    if len(numeric) != len(lane_types):
        return None
    result: list[dict[str, Any]] = []
    for lane_index, (line, lane_type) in enumerate(
        zip(numeric[: len(lane_types)], lane_types, strict=True)
    ):
        semantic_surface = _text(line, "value line")
        source = line.get("source_text")
        source_authoritative = (
            primary_numeric_authority and type(source) is str and is_number_like_v1(source)
        )
        result.append(
            {
                "lane_index": lane_index,
                "lane_type": lane_type,
                "semantic_surface": semantic_surface,
                "source_authoritative": source_authoritative,
                "source_line_index": _source_line_index(line, "value line"),
                "surface": source if source_authoritative else semantic_surface,
                "x_center_x2": center_x2_v1(line),
            }
        )
    return result


def money_values_v1(vector: Sequence[Mapping[str, Any]]) -> list[int] | None:
    result: list[int] = []
    for item in vector:
        if item.get("lane_type") != "MONEY":
            continue
        value = money_integer_v1(item.get("surface"))
        if value is None or item.get("source_authoritative") is not True:
            return None
        result.append(value)
    return result


def percentage_values_v1(vector: Sequence[Mapping[str, Any]]) -> list[Decimal] | None:
    result: list[Decimal] = []
    for item in vector:
        if item.get("lane_type") != "PERCENT":
            continue
        surface = item.get("surface")
        if type(surface) is not str or item.get("source_authoritative") is not True:
            return None
        value = _percentage(surface)
        if value is None:
            return None
        result.append(value)
    return result
