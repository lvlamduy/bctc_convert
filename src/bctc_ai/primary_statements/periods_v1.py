"""Printed period evidence for PRIMARY statement value lanes.

A lane period is built only from printed tokens: the column header path and,
for relative headers ("Kỳ này", "Số cuối kỳ", "Năm nay"), the statement's own
printed context (title/narratives such as "tại ngày 30 tháng 6 năm 2025" or
"cho kỳ sáu tháng kết thúc ngày 30/6/2025"). Nothing is inferred from file
names, bank codes, page positions or magnitudes. A prior-year relative label is
kept as a relation (``PRIOR_YEAR_OF``) instead of subtracting one from the
current year. Conflicting printed evidence is a veto, never a vote.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from bctc_ai.primary_statements.text_v1 import fold_vietnamese

PERIOD_PARSER_VERSION = "PRIMARY_PERIOD_EVIDENCE_V1"

INSTANT = "INSTANT"
DURATION = "DURATION"
CURRENT = "CURRENT"
COMPARATIVE = "COMPARATIVE"

_ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4}
_MONTH_WORDS = {
    "mot": 1, "ba": 3, "sau": 6, "chin": 9, "muoi hai": 12,
    "1": 1, "3": 3, "6": 6, "9": 9, "12": 12, "03": 3, "06": 6, "09": 9,
}
_DATE_NUMERIC = re.compile(r"(?<!\d)(\d{1,2})\s*[/.\-]{1,2}\s*(\d{1,2})\s*[/.\-]{1,2}\s*((?:19|20)\d{2})(?!\d)")
_DATE_WORDS = re.compile(r"(?:ngay\s+)?(\d{1,2})\s+thang\s+(\d{1,2})\s+nam\s+((?:19|20)\d{2})")
_RANGE = re.compile(
    r"tu\s+(?:ngay\s+)?(?P<a>\d{1,2}\s+thang\s+\d{1,2}\s+nam\s+\d{4}|[\d/.\-]+)\s+den\s+(?:ngay\s+)?"
    r"(?P<b>\d{1,2}\s+thang\s+\d{1,2}\s+nam\s+\d{4}|[\d/.\-]+)"
)
_QUARTER = re.compile(r"\bquy\s*(?P<q>iv|iii|ii|i|[1-4])\b(?:\s*[/.\-]?\s*(?:nam\s*)?(?P<y>(?:19|20)\d{2}))?")
_Q_SHORT = re.compile(r"\bq(?P<q>[1-4])\s*[/.\-]?\s*(?P<y>(?:19|20)\d{2})\b")
_MONTHS_ENDED = re.compile(
    r"\b(?P<m>mot|ba|sau|chin|muoi hai|1|3|6|9|12|03|06|09)\s+thang\s+(?:da\s+)?ket\s+thuc\b"
)
_FIRST_MONTHS_OF_FY = re.compile(
    r"\b(?P<m>ba|sau|chin|3|6|9|03|06|09)\s+thang\s+dau(?:\s+cua)?(?:\s+nam(?:\s+tai\s+chinh)?)?"
)
_DATE_TEXT = r"(\d{1,2}\s+thang\s+\d{1,2}\s+nam\s+\d{4}|[\d/.\-]+)"
_FISCAL_YEAR_END = re.compile(rf"\bnam\s+tai\s+chinh\s+ket\s+thuc\s+(?:vao\s+)?ngay\s+{_DATE_TEXT}")
_YEAR = re.compile(r"\bnam\s+(?:tai chinh\s+)?(?P<y>(?:19|20)\d{2})\b|^(?P<bare>(?:19|20)\d{2})$")
_YTD = re.compile(r"\bluy ke\b|\btu dau nam\b")
_CURRENT_WORDS = re.compile(r"\b(?:nam nay|ky nay)\b|(?<!cuoi )\bquy nay\b")
_PRIOR_WORDS = re.compile(r"\b(?:nam truoc|ky truoc|quy truoc|cung ky nam truoc)\b")
_CLOSING = re.compile(r"\b(?:so\s+)?(?:du\s+)?cuoi\s+(?:ky|quy|nam)\b|\bso\s+cuoi\b")
_OPENING_YEAR = re.compile(r"\b(?:so\s+)?(?:du\s+)?dau\s+nam\b")
_OPENING_PERIOD = re.compile(r"\b(?:so\s+)?(?:du\s+)?dau\s+ky\b")


class PeriodEvidenceError(ValueError):
    """Printed period evidence is contradictory."""


@dataclass(frozen=True)
class PeriodDescriptor:
    """Structured, printed-evidence-only period of one value lane."""

    basis: str  # INSTANT | DURATION | UNRESOLVED
    role: str | None
    key: str | None
    resolution: str  # EXPLICIT | CONTEXT_BOUND | RELATIVE_PRINTED | UNRESOLVED
    fields: tuple[tuple[str, object], ...]
    evidence: tuple[str, ...]
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "basis": self.basis,
            "role": self.role,
            "key": self.key,
            "resolution": self.resolution,
            "fields": dict(self.fields),
            "evidence": list(self.evidence),
            "reason": self.reason,
        }


def _iso(day: int, month: int, year: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def printed_dates_v1(text: str) -> list[str]:
    folded = fold_vietnamese(text)
    found = []
    for pattern in (_DATE_NUMERIC, _DATE_WORDS):
        for match in pattern.finditer(folded):
            iso = _iso(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            if iso and iso not in found:
                found.append(iso)
    return found


def _one_date(text: str) -> str | None:
    dates = printed_dates_v1(text)
    return dates[0] if len(dates) == 1 else None


@dataclass(frozen=True)
class StatementPeriodContext:
    """Reporting date/period printed by the statement itself (title/narratives)."""

    reporting_date: str | None
    months: int | None
    quarter: int | None
    year: int | None
    annual: bool
    range_start: str | None
    evidence: tuple[str, ...]
    conflict: str | None
    fiscal_year_end: str | None = None
    first_months_of_fiscal_year: int | None = None


def _blank_spans(text: str, spans: list[tuple[int, int]]) -> str:
    chars = list(text)
    for start, end in spans:
        for index in range(start, end):
            chars[index] = " "
    return "".join(chars)


def statement_period_context_v1(texts: list[str]) -> StatementPeriodContext:
    """Collect the reporting date/period from the statement's printed context.

    "Năm tài chính kết thúc ngày D" names the fiscal-year end, not the
    reporting date, and "N tháng đầu của năm tài chính" is not "N tháng kết
    thúc"; both are recognized first and removed before reporting dates are
    read, so "6 tháng đầu của năm tài chính kết thúc ngày 31/12/2025" can
    never become a six-month period ending 31/12/2025.
    """

    dates: set[str] = set()
    months: set[int] = set()
    quarters: set[tuple[int, int | None]] = set()
    starts: set[str] = set()
    fiscal_ends: set[str] = set()
    first_months: set[int] = set()
    annual = False
    evidence = []
    for text in texts:
        if not text:
            continue
        folded = fold_vietnamese(text)
        used = False
        spans = []
        for match in _FISCAL_YEAR_END.finditer(folded):
            iso = _one_date(match.group(1))
            if iso:
                fiscal_ends.add(iso)
                spans.append(match.span())
                used = True
        for match in _FIRST_MONTHS_OF_FY.finditer(folded):
            first_months.add(_MONTH_WORDS[match.group("m")])
            spans.append(match.span())
            used = True
        for match in _RANGE.finditer(folded):
            start, end = _one_date(match.group("a")), _one_date(match.group("b"))
            if start and end:
                starts.add(start)
                dates.add(end)
                spans.append(match.span())
                used = True
        remaining = _blank_spans(folded, spans)
        # A plain "ngày" after a comma is a signing line ("Hà Nội, ngày ..."), not a period.
        for keyword in ("tai ngay", "ket thuc ngay", "den ngay", "ket thuc vao ngay", r"(?<!,\s)(?<!,)\bngay"):
            for match in re.finditer(rf"{keyword}\b\s*{_DATE_TEXT}", remaining):
                iso = _one_date(match.group(1))
                if iso:
                    dates.add(iso)
                    used = True
        for match in _MONTHS_ENDED.finditer(remaining):
            months.add(_MONTH_WORDS[match.group("m")])
            used = True
        for match in list(_QUARTER.finditer(remaining)) + list(_Q_SHORT.finditer(remaining)):
            q = match.group("q")
            quarters.add((_ROMAN.get(q) or int(q), int(match.group("y")) if match.group("y") else None))
            used = True
        if re.search(r"\bcho nam(?: tai chinh)?\b|\bnam ket thuc\b", remaining) or (
            fiscal_ends and not first_months and not quarters
        ):
            annual = True
            used = True
        if used:
            evidence.append(text)
    conflict = None
    if len(dates) > 1:
        conflict = "MULTIPLE_PRINTED_REPORTING_DATES"
    elif len(months) > 1 or len({q for q, _ in quarters}) > 1 or len(starts) > 1 or len(first_months) > 1:
        conflict = "MULTIPLE_PRINTED_REPORTING_PERIODS"
    quarter = next(iter(quarters))[0] if len({q for q, _ in quarters}) == 1 else None
    q_years = {y for _, y in quarters if y}
    year = None
    if len(q_years) == 1:
        year = next(iter(q_years))
    elif len(dates) == 1:
        year = int(next(iter(dates))[:4])
    elif len(fiscal_ends) == 1:
        year = int(next(iter(fiscal_ends))[:4])
    return StatementPeriodContext(
        reporting_date=next(iter(dates)) if len(dates) == 1 else None,
        months=next(iter(months)) if len(months) == 1 else None,
        quarter=quarter,
        year=year,
        annual=annual,
        range_start=next(iter(starts)) if len(starts) == 1 else None,
        evidence=tuple(evidence),
        conflict=conflict,
        fiscal_year_end=next(iter(fiscal_ends)) if len(fiscal_ends) == 1 else None,
        first_months_of_fiscal_year=next(iter(first_months)) if len(first_months) == 1 else None,
    )


def _unresolved(reason: str, evidence: tuple[str, ...]) -> PeriodDescriptor:
    return PeriodDescriptor("UNRESOLVED", None, None, "UNRESOLVED", (), evidence, reason)


def instant_lane_period_v1(header: str, context: StatementPeriodContext) -> PeriodDescriptor:
    """Balance-sheet lane: an instant date or a printed relative instant."""

    evidence = (header,)
    folded = fold_vietnamese(header)
    if _RANGE.search(folded) or _YTD.search(folded) or _QUARTER.search(folded):
        return _unresolved("DURATION_HEADER_IN_INSTANT_STATEMENT", evidence)
    dates = printed_dates_v1(header)
    if len(dates) > 1:
        return _unresolved("MULTIPLE_DATES_IN_ONE_HEADER", evidence)
    if dates:
        iso = dates[0]
        role = None
        if context.reporting_date and not context.conflict:
            role = CURRENT if iso == context.reporting_date else (COMPARATIVE if iso < context.reporting_date else None)
        return PeriodDescriptor(INSTANT, role, f"INSTANT:{iso}", "EXPLICIT", (("date", iso),), evidence)
    quarter_anchor = (
        f"Q{context.quarter}:{context.year}" if context.quarter and context.year and not context.conflict else None
    )
    if _CLOSING.search(folded) and not _OPENING_YEAR.search(folded):
        if not context.conflict and context.reporting_date:
            iso = context.reporting_date
            return PeriodDescriptor(
                INSTANT, CURRENT, f"INSTANT:{iso}", "CONTEXT_BOUND", (("date", iso),), evidence + context.evidence
            )
        if quarter_anchor and re.search(r"\bcuoi\s+(?:ky|quy)\b", folded):
            # "Số dư cuối quý" under a printed "Quý I/2025" title: the end of that
            # printed quarter, kept symbolic (no calendar date is computed).
            return PeriodDescriptor(
                INSTANT, CURRENT, f"INSTANT:END_OF_QUARTER({quarter_anchor})", "CONTEXT_BOUND",
                (("relation", "END_OF_PRINTED_QUARTER"), ("anchor_quarter", quarter_anchor)), evidence + context.evidence,
            )
        return _unresolved("CLOSING_LABEL_WITHOUT_UNIQUE_PRINTED_REPORTING_DATE", evidence + context.evidence)
    if _OPENING_YEAR.search(folded) or _OPENING_PERIOD.search(folded):
        relation = "OPENING_OF_FISCAL_YEAR" if _OPENING_YEAR.search(folded) else "OPENING_OF_REPORTING_PERIOD"
        anchor = context.reporting_date if not context.conflict else None
        if anchor is None and quarter_anchor:
            anchor = quarter_anchor
        if anchor is None:
            return _unresolved("OPENING_LABEL_WITHOUT_UNIQUE_PRINTED_REPORTING_DATE", evidence + context.evidence)
        return PeriodDescriptor(
            INSTANT, COMPARATIVE, f"INSTANT:{relation}({anchor})", "RELATIVE_PRINTED",
            (("relation", relation), ("anchor_reporting_date", anchor)), evidence + context.evidence,
        )
    return _unresolved("NO_PRINTED_INSTANT", evidence)


def duration_lane_period_v1(header: str, context: StatementPeriodContext) -> PeriodDescriptor:
    """Income/cash-flow lane: quarter, year-to-date, months-ended, year or range."""

    evidence = (header,)
    # "Lũy kế từ đầu năm nay đến cuối quý này" names the accumulation start, not a role.
    folded = re.sub(r"\btu dau nam nay\b", "tu dau nam", fold_vietnamese(header))
    # "Quý này năm trước" = this quarter of the prior year: the year word decides the role.
    year_current = bool(re.search(r"\bnam nay\b", folded))
    year_prior = bool(re.search(r"\bnam truoc\b|\bcung ky nam truoc\b", folded))
    if year_current and year_prior:
        return _unresolved("CURRENT_AND_PRIOR_WORDS_IN_ONE_HEADER", evidence)
    prior = year_prior or (not year_current and bool(_PRIOR_WORDS.search(folded)))
    current = not prior and bool(_CURRENT_WORDS.search(folded))
    durational = _RANGE.search(folded) or _YTD.search(folded) or _QUARTER.search(folded) or _Q_SHORT.search(folded)
    if not durational and (_CLOSING.search(folded) or _OPENING_YEAR.search(folded)):
        return _unresolved("INSTANT_HEADER_IN_DURATION_STATEMENT", evidence)
    range_match = _RANGE.search(folded)
    if range_match:
        start, end = _one_date(range_match.group("a")), _one_date(range_match.group("b"))
        if not (start and end and start < end):
            return _unresolved("INVALID_PRINTED_RANGE", evidence)
        return PeriodDescriptor(
            DURATION, _role_from_end(end, context), f"DURATION:RANGE:{start}..{end}", "EXPLICIT",
            (("grain", "RANGE"), ("start", start), ("end", end)), evidence,
        )
    quarter_match = _QUARTER.search(folded) or _Q_SHORT.search(folded)
    ytd = bool(_YTD.search(folded))
    years = [int(m.group("y") or m.group("bare")) for m in _YEAR.finditer(folded.strip())]
    bare_years = re.findall(r"(?<![\d/.\-])((?:19|20)\d{2})(?![\d/.\-])", folded)
    dates = printed_dates_v1(header)
    explicit_year = None
    candidate_years = set(years) | {int(y) for y in bare_years}
    if quarter_match and quarter_match.group("y"):
        candidate_years.add(int(quarter_match.group("y")))
    if len(candidate_years) > 1:
        return _unresolved("MULTIPLE_YEARS_IN_ONE_HEADER", evidence)
    if candidate_years:
        explicit_year = next(iter(candidate_years))
    if dates:
        if len(dates) > 1:
            return _unresolved("MULTIPLE_DATES_IN_ONE_HEADER", evidence)
        end = dates[0]
        if ytd and not _header_months(folded):
            # "Lũy kế từ đầu kỳ/năm đến ngày D": cumulative to a printed date; the
            # start is kept as printed wording, never computed.
            start_word = "YEAR" if re.search(r"\btu dau nam\b", folded) else "PERIOD"
            return PeriodDescriptor(
                DURATION, _role_from_end(end, context), f"DURATION:CUMULATIVE_FROM_START_OF_{start_word}_TO:{end}",
                "EXPLICIT", (("grain", f"CUMULATIVE_FROM_START_OF_{start_word}"), ("end", end)), evidence,
            )
        months = _header_months(folded) or context.months
        if months is None:
            return _unresolved("PERIOD_END_WITHOUT_PRINTED_DURATION", evidence + context.evidence)
        resolution = "EXPLICIT" if _header_months(folded) else "CONTEXT_BOUND"
        return PeriodDescriptor(
            DURATION, _role_from_end(end, context), f"DURATION:MONTHS_ENDED:{months}:{end}", resolution,
            (("grain", "MONTHS_ENDED"), ("months", months), ("end", end)), evidence + (() if resolution == "EXPLICIT" else context.evidence),
        )
    if explicit_year is not None and prior:
        # "Quý I/2025" spanning "Năm nay | Năm trước": the printed year belongs to
        # the spanning header; the prior column is that year's prior year only
        # when the statement context prints the same year.
        if context.year is None or context.conflict:
            return _unresolved("PRIOR_WORD_WITH_YEAR_WITHOUT_CONTEXT_YEAR", evidence + context.evidence)
        if explicit_year == context.year:
            explicit_year = None
    year_ref, year_resolution, role = _year_reference(explicit_year, current, prior, context)
    if year_ref is None:
        return _unresolved("NO_PRINTED_OR_CONTEXT_YEAR", evidence + context.evidence)
    if quarter_match and not ytd:
        quarter = _ROMAN.get(quarter_match.group("q")) or int(quarter_match.group("q"))
        return PeriodDescriptor(
            DURATION, role, f"DURATION:QUARTER:{quarter}:{year_ref}", year_resolution,
            (("grain", "QUARTER"), ("quarter", quarter), ("year", year_ref)), _ev(evidence, context, year_resolution),
        )
    if ytd:
        through = None
        if quarter_match:
            through = _ROMAN.get(quarter_match.group("q")) or int(quarter_match.group("q"))
        elif re.search(r"\bquy nay\b|\bcuoi quy\b", folded):
            through = context.quarter
            if through is None:
                return _unresolved("YTD_THROUGH_THIS_QUARTER_WITHOUT_PRINTED_QUARTER", evidence + context.evidence)
        elif context.quarter is not None and not context.conflict:
            through = context.quarter
        through_text = f"Q{through}" if through else (
            f"{context.months}M" if context.months else (
                f"FIRST_{context.first_months_of_fiscal_year}M_OF_FY" if context.first_months_of_fiscal_year else None
            )
        )
        if through_text is None:
            return _unresolved("YTD_WITHOUT_PRINTED_END", evidence + context.evidence)
        return PeriodDescriptor(
            DURATION, role, f"DURATION:YTD:{through_text}:{year_ref}", "CONTEXT_BOUND" if through and not quarter_match else year_resolution,
            (("grain", "YTD"), ("through", through_text), ("year", year_ref)), evidence + context.evidence,
        )
    if re.search(r"\bquy nay\b|\bquy truoc\b", folded):
        if context.quarter is None:
            return _unresolved("THIS_QUARTER_WITHOUT_PRINTED_QUARTER", evidence + context.evidence)
        return PeriodDescriptor(
            DURATION, role, f"DURATION:QUARTER:{context.quarter}:{year_ref}", "CONTEXT_BOUND",
            (("grain", "QUARTER"), ("quarter", context.quarter), ("year", year_ref)), evidence + context.evidence,
        )
    if re.search(r"\bky nay\b|\bky truoc\b", folded) or (explicit_year is None and (current or prior)):
        return _context_period(year_ref, role, evidence, context)
    if explicit_year is not None:
        # "Năm 2025" literally prints a year; a bare "2025" needs an annual context.
        if re.search(rf"\bnam\s+{explicit_year}\b", folded) and not context.quarter and not context.months \
                and not context.first_months_of_fiscal_year:
            return PeriodDescriptor(
                DURATION, role, f"DURATION:YEAR:{year_ref}", "EXPLICIT",
                (("grain", "YEAR"), ("year", year_ref)), evidence,
            )
        if context.annual or (context.months == 12):
            return PeriodDescriptor(
                DURATION, role, f"DURATION:YEAR:{year_ref}", "EXPLICIT",
                (("grain", "YEAR"), ("year", year_ref)), evidence + context.evidence,
            )
        return _context_period(year_ref, role, evidence, context)
    return _unresolved("NO_PRINTED_DURATION", evidence)


def _ev(evidence: tuple[str, ...], context: StatementPeriodContext, resolution: str) -> tuple[str, ...]:
    return evidence if resolution == "EXPLICIT" else evidence + context.evidence


def _header_months(folded: str) -> int | None:
    found = {_MONTH_WORDS[m.group("m")] for m in _MONTHS_ENDED.finditer(folded)}
    return next(iter(found)) if len(found) == 1 else None


def _role_from_end(end: str, context: StatementPeriodContext) -> str | None:
    if context.reporting_date and not context.conflict:
        if end == context.reporting_date:
            return CURRENT
        if end < context.reporting_date:
            return COMPARATIVE
    return None


def _year_reference(
    explicit_year: int | None, current: bool, prior: bool, context: StatementPeriodContext
) -> tuple[str | None, str, str | None]:
    if explicit_year is not None:
        role = None
        if context.year is not None and not context.conflict:
            role = CURRENT if explicit_year == context.year else (COMPARATIVE if explicit_year < context.year else None)
        return str(explicit_year), "EXPLICIT", role
    if context.conflict or context.year is None:
        return None, "UNRESOLVED", None
    if prior:
        return f"PRIOR_YEAR_OF({context.year})", "RELATIVE_PRINTED", COMPARATIVE
    if current:
        return str(context.year), "CONTEXT_BOUND", CURRENT
    return str(context.year), "CONTEXT_BOUND", CURRENT


def _context_period(
    year_ref: str, role: str | None, evidence: tuple[str, ...], context: StatementPeriodContext
) -> PeriodDescriptor:
    """Bind a relative lane to the statement's printed period ("Kỳ này", "Năm nay")."""

    if context.conflict:
        return _unresolved(context.conflict, evidence + context.evidence)
    if context.range_start and context.reporting_date:
        end = context.reporting_date
        if year_ref.startswith("PRIOR_YEAR_OF"):
            return PeriodDescriptor(
                DURATION, role, f"DURATION:CORRESPONDING_PRIOR_YEAR_RANGE:{context.range_start}..{end}",
                "RELATIVE_PRINTED", (("grain", "CORRESPONDING_PRIOR_YEAR_RANGE"), ("anchor_start", context.range_start), ("anchor_end", end)),
                evidence + context.evidence,
            )
        return PeriodDescriptor(
            DURATION, role, f"DURATION:RANGE:{context.range_start}..{end}", "CONTEXT_BOUND",
            (("grain", "RANGE"), ("start", context.range_start), ("end", end)), evidence + context.evidence,
        )
    if context.months and context.reporting_date:
        end = context.reporting_date
        if year_ref.startswith("PRIOR_YEAR_OF"):
            return PeriodDescriptor(
                DURATION, role, f"DURATION:CORRESPONDING_PRIOR_YEAR_MONTHS_ENDED:{context.months}:{end}",
                "RELATIVE_PRINTED", (("grain", "CORRESPONDING_PRIOR_YEAR_MONTHS_ENDED"), ("months", context.months), ("anchor_end", end)),
                evidence + context.evidence,
            )
        return PeriodDescriptor(
            DURATION, role, f"DURATION:MONTHS_ENDED:{context.months}:{end}", "CONTEXT_BOUND",
            (("grain", "MONTHS_ENDED"), ("months", context.months), ("end", end)), evidence + context.evidence,
        )
    if context.annual and context.quarter is None:
        return PeriodDescriptor(
            DURATION, role, f"DURATION:YEAR:{year_ref}", "CONTEXT_BOUND" if not year_ref.startswith("PRIOR") else "RELATIVE_PRINTED",
            (("grain", "YEAR"), ("year", year_ref)), evidence + context.evidence,
        )
    # A quarterly title with "Kỳ này" does not prove quarter-only versus year-to-date.
    return _unresolved("RELATIVE_HEADER_WITHOUT_PRINTED_DURATION_GRAIN", evidence + context.evidence)
