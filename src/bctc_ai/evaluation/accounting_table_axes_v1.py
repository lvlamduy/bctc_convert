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
    "infer_document_reporting_period_context_v1",
    "extract_period_axis_v1",
    "extract_reporting_year_axis_v1",
    "extract_typed_value_vector_v1",
    "is_number_like_v1",
    "money_integer_v1",
    "money_values_v1",
    "percentage_values_v1",
    "unit_kind_v1",
]


_NUMBER = re.compile(r"^[()]*[+-]?[0-9][0-9., ]*%?[()]*$")
_FULL_DATE = re.compile(r"(?<!\d)(\d{1,2})[./-](\d{1,2})[./-](\d{4})(?!\d)")
_DAY_MONTH = re.compile(r"\b(?:ngay\s+)?(\d{1,2})\s+thang\s+(\d{1,2})\b")
_YEAR = re.compile(r"\bnam\s+(\d{4})\b")
_REPORTING_YEAR = re.compile(r"(?<!\d)(20\d{2})(?!\d)")
_REPORTING_PERIOD_ENDS = {(3, 31), (6, 30), (9, 30), (12, 31)}
_MAX_DOCUMENT_DATE_EVIDENCE = 8


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
            day = int(matched.group(1))
            month = int(matched.group(2))
            if year_match := _YEAR.search(normalized):
                surface = _date_surface(day, month, int(year_match.group(1)))
                if surface is not None:
                    full.append(
                        {
                            "evidence_source_line_indices": [
                                _source_line_index(line, "Vietnamese full period header")
                            ],
                            "period": surface,
                            "x_center_x2": center_x2_v1(line),
                        }
                    )
                continue
            partial.append((line, day, month))
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


def extract_reporting_year_axis_v1(
    lines: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    """Resolve a current/comparative axis from exactly two visible years.

    The later year is the current reporting axis and the earlier year is the
    comparative axis.  More or fewer than two visible years fail closed so a
    narrative year or a second table cannot silently choose the period.
    """

    by_year: dict[int, list[Mapping[str, Any]]] = {}
    for line in lines:
        text = _text(line, "reporting-year header")
        for matched in _REPORTING_YEAR.finditer(text):
            by_year.setdefault(int(matched.group(1)), []).append(line)
    if len(by_year) != 2:
        return [], "UNRESOLVED"
    comparative_year, current_year = sorted(by_year)
    records = []
    for role, year in (
        ("COMPARATIVE_PERIOD", comparative_year),
        ("CURRENT_PERIOD", current_year),
    ):
        line = by_year[year][0]
        records.append(
            {
                "evidence_source_line_indices": [_source_line_index(line, "reporting-year header")],
                "role": role,
                "x_center_x2": center_x2_v1(line),
                "year": year,
            }
        )
    return records, "VISIBLE_TWO_YEAR_REPORTING_AXIS"


def _document_date_observations(
    pages: Sequence[Mapping[str, Any]],
) -> dict[date, list[dict[str, Any]]]:
    if not isinstance(pages, Sequence) or isinstance(pages, (str, bytes)):
        raise _error("document pages must be one sequence of page records")
    observations: dict[date, list[dict[str, Any]]] = {}
    for expected_page_sequence, raw_page in enumerate(pages, 1):
        if not isinstance(raw_page, Mapping):
            raise _error("document period page must be one mapping")
        page_sequence = raw_page.get("page_sequence")
        lines = raw_page.get("lines")
        if (
            type(page_sequence) is not int
            or page_sequence != expected_page_sequence
            or type(lines) is not list
        ):
            raise _error("document period page identity or line axis drifted")
        partial: list[tuple[Mapping[str, Any], int, int]] = []
        year_only: list[tuple[Mapping[str, Any], int]] = []
        page_observations: set[tuple[date, tuple[int, ...]]] = set()
        seen_line_indices: set[int] = set()
        for line in lines:
            if not isinstance(line, Mapping):
                raise _error("document period line must be one mapping")
            text = _text(line, "document period line")
            source_line_index = _source_line_index(line, "document period line")
            if source_line_index in seen_line_indices:
                raise _error("document period source line axis repeats")
            seen_line_indices.add(source_line_index)
            _bbox(line, "document period line")
            normalized = normalize_vietnamese_anchor_v1(text)
            found_full = False
            for matched in _FULL_DATE.finditer(text):
                day, month, year = map(int, matched.groups())
                surface = _date_surface(day, month, year)
                if surface is None:
                    continue
                parsed = date(year, month, day)
                page_observations.add((parsed, (source_line_index,)))
                found_full = True
            if found_full:
                continue
            day_month_match = _DAY_MONTH.search(normalized)
            year_match = _YEAR.search(normalized)
            if day_month_match is not None and year_match is not None:
                day = int(day_month_match.group(1))
                month = int(day_month_match.group(2))
                year = int(year_match.group(1))
                surface = _date_surface(day, month, year)
                if surface is not None:
                    page_observations.add((date(year, month, day), (source_line_index,)))
                continue
            if day_month_match is not None:
                partial.append((line, int(day_month_match.group(1)), int(day_month_match.group(2))))
                continue
            if year_match is not None:
                year_only.append((line, int(year_match.group(1))))

        remaining_years = list(year_only)
        for line, day, month in partial:
            line_index = _source_line_index(line, "split document period")
            candidates = [
                item
                for item in remaining_years
                if abs(_source_line_index(item[0], "split document period year") - line_index) <= 3
            ]
            if not candidates:
                continue
            year_line, year = min(
                candidates,
                key=lambda item: (
                    abs(_source_line_index(item[0], "split document period year") - line_index),
                    abs(center_x2_v1(item[0]) - center_x2_v1(line)),
                ),
            )
            remaining_years.remove((year_line, year))
            surface = _date_surface(day, month, year)
            if surface is None:
                continue
            indices = tuple(
                sorted(
                    (
                        line_index,
                        _source_line_index(year_line, "split document period year"),
                    )
                )
            )
            page_observations.add((date(year, month, day), indices))

        for parsed, indices in sorted(page_observations):
            observations.setdefault(parsed, []).append(
                {
                    "page_sequence": page_sequence,
                    "source_line_indices": list(indices),
                }
            )
    return observations


def infer_document_reporting_period_context_v1(
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Infer a document-wide period context from repeated visible full dates.

    This is a bank-, filename-, note- and family-blind context proposal.  A
    family must still bind the applicable local table headers and must not use
    this record alone as numeric, mapping, or schema authority.
    """

    observations = _document_date_observations(pages)
    summaries: list[dict[str, Any]] = []
    for parsed in sorted(observations):
        evidence = sorted(
            observations[parsed],
            key=lambda item: (item["page_sequence"], item["source_line_indices"]),
        )
        page_count = len({item["page_sequence"] for item in evidence})
        summaries.append(
            {
                "date": parsed.strftime("%d/%m/%Y"),
                "evidence": evidence[:_MAX_DOCUMENT_DATE_EVIDENCE],
                "evidence_truncated": len(evidence) > _MAX_DOCUMENT_DATE_EVIDENCE,
                "occurrence_count": len(evidence),
                "page_count": page_count,
            }
        )

    candidates = [
        (parsed, evidence)
        for parsed, evidence in observations.items()
        if (parsed.month, parsed.day) in _REPORTING_PERIOD_ENDS
        and len({item["page_sequence"] for item in evidence}) >= 2
    ]
    if not candidates:
        return {
            "balance_comparative_period_end": None,
            "current_period_end": None,
            "current_period_start": None,
            "flow_comparative_period_end": None,
            "flow_comparative_period_start": None,
            "observed_dates": summaries,
            "period_kind": None,
            "reporting_year": None,
            "resolution": "UNRESOLVED_NO_REPEATED_REPORTING_END_DATE",
            "supporting_page_count": 0,
        }

    maximum_page_support = max(
        len({evidence["page_sequence"] for evidence in candidate_evidence})
        for _candidate, candidate_evidence in candidates
    )
    dominant_candidates = [
        (candidate, candidate_evidence)
        for candidate, candidate_evidence in candidates
        if len({evidence["page_sequence"] for evidence in candidate_evidence}) * 4
        >= maximum_page_support
    ]
    current, current_evidence = max(
        dominant_candidates,
        key=lambda item: (
            item[0],
            len({evidence["page_sequence"] for evidence in item[1]}),
            len(item[1]),
        ),
    )
    previous_year = current.year - 1

    def observed_surface(day: int, month: int, year: int) -> str | None:
        try:
            candidate = date(year, month, day)
        except ValueError:
            return None
        return candidate.strftime("%d/%m/%Y") if candidate in observations else None

    balance_comparative = observed_surface(31, 12, previous_year)
    flow_comparative = observed_surface(current.day, current.month, previous_year)
    current_start = observed_surface(1, 1, current.year)
    flow_comparative_start = observed_surface(1, 1, previous_year)
    period_kind = {
        (3, 31): "FIRST_QUARTER",
        (6, 30): "HALF_YEAR_OR_SECOND_QUARTER",
        (9, 30): "NINE_MONTH_OR_THIRD_QUARTER",
        (12, 31): "ANNUAL",
    }[(current.month, current.day)]
    return {
        "balance_comparative_period_end": balance_comparative,
        "current_period_end": current.strftime("%d/%m/%Y"),
        "current_period_start": current_start,
        "flow_comparative_period_end": flow_comparative,
        "flow_comparative_period_start": flow_comparative_start,
        "observed_dates": summaries,
        "period_kind": period_kind,
        "reporting_year": current.year,
        "resolution": "DOMINANT_REPEATED_FULL_DATE_CONSENSUS",
        "supporting_page_count": len({evidence["page_sequence"] for evidence in current_evidence}),
    }


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
