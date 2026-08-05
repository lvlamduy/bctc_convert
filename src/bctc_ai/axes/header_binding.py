from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from bctc_ai.core.contracts import BoundingBox
from bctc_ai.core.text import (
    ParsedUnit,
    normalize_text,
    parse_unit,
    parse_vietnamese_dates,
    retrieval_key,
)
from bctc_ai.tables.geometry import ColumnAxis, ColumnRole, GeometryConfig, PageGeometry, TextRun

_DURATION_WORDS = {
    "mot": 1,
    "one": 1,
    "hai": 2,
    "two": 2,
    "ba": 3,
    "three": 3,
    "sau": 6,
    "six": 6,
    "chin": 9,
    "nine": 9,
    "muoi hai": 12,
    "twelve": 12,
}


@dataclass(frozen=True)
class HeaderBinding:
    axis_id: str
    raw_header: str
    header_bbox: BoundingBox | None
    unit: str | None
    unit_multiplier: int | None
    unit_bbox: BoundingBox | None
    period_start: date | None
    period_end: date | None
    period_type: str | None
    duration_months: int | None
    current_or_comparative: str | None
    restated: bool
    confidence: float
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class _HeaderCandidate:
    axis: ColumnAxis
    raw_header: str
    header_bbox: BoundingBox | None
    unit: ParsedUnit
    unit_bbox: BoundingBox | None
    period_start: date | None
    period_end: date | None
    period_type: str | None
    duration_months: int | None
    restated: bool
    evidence: tuple[str, ...]


def _union(boxes: list[BoundingBox]) -> BoundingBox:
    return BoundingBox(
        min(box.x0 for box in boxes),
        min(box.y0 for box in boxes),
        max(box.x1 for box in boxes),
        max(box.y1 for box in boxes),
    )


def _duration_start(period_end: date, months: int) -> date:
    month_index = period_end.year * 12 + period_end.month - months
    return date(month_index // 12, month_index % 12 + 1, 1)


def _inclusive_months(period_start: date, period_end: date) -> int | None:
    if period_start > period_end:
        return None
    months = (period_end.year - period_start.year) * 12 + period_end.month - period_start.month + 1
    return months if 1 <= months <= 120 else None


def _duration_months(header_key: str) -> int | None:
    numeric = re.search(
        r"\b(?:ky(?: ke toan| bao cao)?|giai doan|period(?: of)?|for the period(?: of)?)\s+"
        r"(?P<months>\d{1,2})\s+(?:thang|months?)\b",
        header_key,
    )
    if numeric is None:
        numeric = re.search(
            r"\bfor the (?P<months>\d{1,2})\s+months?\s+period\b",
            header_key,
        )
    if numeric:
        months = int(numeric.group("months"))
        return months if 1 <= months <= 12 else None
    word_pattern = "|".join(sorted(_DURATION_WORDS, key=len, reverse=True))
    words = re.search(
        rf"\b(?:ky(?: ke toan| bao cao)?|giai doan)\s+"
        rf"(?P<months>{word_pattern})\s+thang\b",
        header_key,
    )
    if words is None:
        words = re.search(
            rf"\bfor the (?P<months>{word_pattern})\s+months?\s+period\b",
            header_key,
        )
    if words:
        return _DURATION_WORDS[words.group("months")]
    if re.search(r"\b(?:cho )?(?:nam tai chinh|nam)\s+ket thuc\b", header_key):
        return 12
    if re.search(r"\b(?:cho )?quy\s+(?:[1-4]|i{1,3}|iv)\b", header_key):
        return 3
    return None


def _header_runs_for_axis(
    geometry: PageGeometry,
    axis: ColumnAxis,
    value_axes: list[ColumnAxis],
    config: GeometryConfig,
) -> list[TextRun]:
    left_limit = min(value_axis.left_edge for value_axis in value_axes) - (
        geometry.width_points * config.header_left_margin_from_value_ratio
    )
    candidates = [
        run
        for run in geometry.runs
        if run.bbox.y1 < geometry.data_start_y
        and run.bbox.x0 >= left_limit
        and run.bbox.y0 >= geometry.height_points * 0.08
    ]
    return sorted(
        [
            run
            for run in candidates
            if min(value_axes, key=lambda item: abs(item.center - run.x_center)).axis_id
            == axis.axis_id
        ],
        key=lambda run: (run.bbox.y0, run.bbox.x0),
    )


def bind_value_headers(
    geometry: PageGeometry,
    config: GeometryConfig,
) -> list[HeaderBinding]:
    value_axes = [axis for axis in geometry.axes if axis.role is ColumnRole.VALUE]
    page_units = [
        (run, parse_unit(run.normalized_text))
        for run in geometry.runs
        if run.run_id in geometry.unit_run_ids
        and parse_unit(run.normalized_text).canonical is not None
    ]
    page_unit_keys = {(parsed.canonical, parsed.multiplier) for _, parsed in page_units}
    shared_unit = (
        page_units[-1] if page_units and len(page_unit_keys) == 1 else (None, parse_unit(""))
    )
    provisional: list[_HeaderCandidate] = []
    for axis in value_axes:
        runs = _header_runs_for_axis(geometry, axis, value_axes, config)
        header_text = normalize_text(" ".join(run.normalized_text for run in runs))
        parsed_dates = parse_vietnamese_dates(header_text)
        parsed_date = parsed_dates[-1] if parsed_dates else None
        parsed_units = [
            (run, parse_unit(run.normalized_text))
            for run in runs
            if parse_unit(run.normalized_text).canonical is not None
        ]
        unit_is_shared = not parsed_units and shared_unit[0] is not None
        unit_run, parsed_unit = parsed_units[-1] if parsed_units else shared_unit
        key = retrieval_key(header_text)
        duration_months = _duration_months(key)
        has_explicit_range = len(parsed_dates) >= 2 and bool(
            re.search(r"\b(?:tu(?: ngay)?|from)\b.*\b(?:den(?: ngay)?|to)\b", key)
        )
        is_ytd = "luy ke" in key or "tu dau nam" in key or "year to date" in key
        if has_explicit_range:
            period_start = parsed_dates[0]
            period_type = "YTD" if is_ytd else "DURATION"
            duration_months = _inclusive_months(period_start, parsed_date)
        elif is_ytd and parsed_date:
            period_type = "YTD"
            period_start = date(parsed_date.year, 1, 1)
            duration_months = parsed_date.month
        elif duration_months and parsed_date:
            period_type = "DURATION"
            period_start = _duration_start(parsed_date, duration_months)
        elif parsed_date:
            period_type = "SNAPSHOT"
            period_start = parsed_date
        else:
            period_type = None
            period_start = None
        evidence = []
        if parsed_date:
            evidence.append("period end parsed from axis-local header")
        if has_explicit_range:
            evidence.append("period start parsed from explicit axis-local date range")
        if parsed_unit.canonical:
            evidence.append(
                "unit parsed from shared page header"
                if unit_is_shared
                else "unit parsed from axis-local header"
            )
        if duration_months:
            evidence.append("duration parsed from axis-local header")
        provisional.append(
            _HeaderCandidate(
                axis=axis,
                raw_header=header_text,
                header_bbox=_union([run.bbox for run in runs]) if runs else None,
                unit=parsed_unit,
                unit_bbox=unit_run.bbox if unit_run else None,
                period_start=period_start,
                period_end=parsed_date,
                period_type=period_type,
                duration_months=duration_months,
                restated="trinh bay lai" in key or "restated" in key,
                evidence=tuple(evidence),
            )
        )

    dated = sorted(
        [record for record in provisional if record.period_end is not None],
        key=lambda record: record.period_end or date.min,
        reverse=True,
    )
    roles: dict[str, str] = {}
    if dated:
        latest = dated[0].period_end
        for record in dated:
            roles[record.axis.axis_id] = "CURRENT" if record.period_end == latest else "COMPARATIVE"

    bindings = []
    for record in provisional:
        axis = record.axis
        evidence = list(record.evidence)
        role = roles.get(axis.axis_id)
        if role:
            evidence.append("current/comparative role assigned by parsed date, not x-order")
        confidence = (
            0.45 * float(record.period_end is not None)
            + 0.20 * float(record.unit.canonical is not None)
            + 0.20 * float(record.period_type is not None)
            + 0.15 * float(role is not None)
        )
        bindings.append(
            HeaderBinding(
                axis_id=axis.axis_id,
                raw_header=record.raw_header,
                header_bbox=record.header_bbox,
                unit=record.unit.canonical,
                unit_multiplier=record.unit.multiplier,
                unit_bbox=record.unit_bbox,
                period_start=record.period_start,
                period_end=record.period_end,
                period_type=record.period_type,
                duration_months=record.duration_months,
                current_or_comparative=role,
                restated=record.restated,
                confidence=round(confidence, 6),
                evidence=tuple(evidence),
            )
        )
    return bindings
