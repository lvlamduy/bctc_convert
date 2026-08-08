"""Hash-bound reconstruction of MBB consolidated TM page 61 exchange rates.

The table reports VND for one unit of each row currency. Its European decimal
comma is retained as decimal precision and must never receive a million-unit
multiplier.
"""

from __future__ import annotations

import json
import re
import statistics
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.contracts import BoundingBox, ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import (
    normalize_text,
    parse_financial_number,
    parse_vietnamese_date,
    retrieval_key,
)
from bctc_ai.tables.tm_note_word_box import (
    TMNoteWordBoxError,
    _best_anchor_similarity,
    _clusters,
    _Line,
    _load_lines,
    _numeric_only,
    _source_ids,
    _union,
)
from bctc_ai.validation.reader_agreement import ReaderRow

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_RATE_TEXT = re.compile(r"^(?:\d{1,3}(?:\.\d{3})*|\d+),\d{2}$")
_PERIOD_ROLES = ("CURRENT", "PRIOR")
_PERIOD_DATES = (date(2026, 3, 31), date(2025, 12, 31))
_PERIOD_RIGHT_EDGES = (1431.0, 1979.0)
_CURRENCY_CODES = ("USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "SGD", "THB", "SEK")
_EXPECTED_LOW_SCORE_INDICES = (52,)
_EXPECTED_POST_TABLE_NUMERIC_INDICES = (40,)
_EXPECTED_FOOTER_NUMERIC_INDICES = (53,)
_REQUIRED_FORBIDDEN = {
    "template_labels_as_row_reconstruction_input",
    "approved_report_norm_id_assignment",
    "historical_or_mongodb_values",
    "human_review_answers",
    "vnd_million_multiplier",
    "decimal_comma_loss_or_integer_rounding",
    "period_axis_swapping",
    "page60_values_as_page61_mapping_or_imputation",
    "signatures_stamps_or_approval_text_as_financial_rows",
}


@dataclass(frozen=True)
class TMPage61PeriodSpec:
    period_role: str
    visible_date: date
    header_anchors: tuple[str, ...]
    right_edge: float


@dataclass(frozen=True)
class TMPage61CurrencySpec:
    currency_code: str
    canonical_label: str
    label_anchors: tuple[str, ...]


@dataclass(frozen=True)
class TMPage61Policy:
    source_path: Path
    document: str
    page_number: int
    page_tag: str
    scope: str
    scope_binding: str
    source_pdf_sha256: str
    source_render_sha256: str
    source_ocr_sha256: str
    upstream_ocr_sha256: str
    minimum_line_score: float
    minimum_anchor_similarity: float
    minimum_unit_similarity: float
    unit_anchors: tuple[str, ...]
    canonical_unit: str
    unit_multiplier: int
    unit_denominator: str
    table_key: str
    note_number: str
    title_anchors: tuple[str, ...]
    periods: tuple[TMPage61PeriodSpec, ...]
    currencies: tuple[TMPage61CurrencySpec, ...]
    numeric_cluster_line_heights: float
    row_attach_line_heights: float
    axis_max_distance_line_heights: float
    page_footer_top_ratio: float
    page_61_closes_note_6: bool
    page_61_is_document_final_page: bool
    forbidden_semantic_inputs: tuple[str, ...]


@dataclass(frozen=True)
class TMPage61PeriodBinding:
    ordinal: int
    period_role: str
    visible_date: date
    period_type: str
    period_start: date
    period_end: date
    axis_right_edge: float
    raw_header_text: str
    date_line_index: int
    date_bbox: BoundingBox
    raw_unit_text: str
    unit_line_index: int
    unit_bbox: BoundingBox
    canonical_unit: str
    unit_multiplier: int
    unit_denominator: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class TMPage61LogicalRow:
    row_id: str
    table_key: str
    ordinal: int
    currency_code: str
    canonical_label: str
    row: ReaderRow
    label_bbox: BoundingBox
    value_bboxes: tuple[BoundingBox, ...]
    label_line_index: int
    value_line_indices: tuple[int, ...]
    cell_period_starts: tuple[date, ...]
    cell_period_ends: tuple[date, ...]
    cell_period_roles: tuple[str, ...]
    cell_period_types: tuple[str, ...]
    cell_unit_denominators: tuple[str, ...]
    mapping_approved: bool

    @property
    def financial_slot_count(self) -> int:
        return len(self.row.cells)


@dataclass(frozen=True)
class TMPage61Table:
    ordinal: int
    table_key: str
    note_number: str
    title: str
    title_line_index: int
    periods: tuple[TMPage61PeriodBinding, ...]
    rows: tuple[TMPage61LogicalRow, ...]
    bbox: BoundingBox


@dataclass(frozen=True)
class ParsedTMPage61:
    input_path: str
    source_sha256: str
    upstream_ocr_sha256: str
    source_render_sha256: str
    source_pdf_sha256: str
    page_tag: str
    scope: str
    scope_binding: str
    table: TMPage61Table
    tables: tuple[TMPage61Table, ...]
    periods: tuple[TMPage61PeriodBinding, ...]
    rows: tuple[TMPage61LogicalRow, ...]
    line_height: float
    source_ocr_bbox: BoundingBox
    table_bbox: BoundingBox
    unassigned_numeric_line_indices: tuple[int, ...]
    excluded_low_confidence_line_indices: tuple[int, ...]
    excluded_post_table_numeric_line_indices: tuple[int, ...]
    excluded_footer_numeric_line_indices: tuple[int, ...]
    continues_after_page_61: bool
    mapping_authority: bool
    evidence: tuple[str, ...]

    @property
    def numeric_row_count(self) -> int:
        return len(self.rows)

    @property
    def financial_slot_count(self) -> int:
        return sum(row.financial_slot_count for row in self.rows)

    def observation_count(self, observation: ObservationKind) -> int:
        return sum(cell.observation is observation for row in self.rows for cell in row.row.cells)


def _anchors(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise TMNoteWordBoxError(f"TM page-61 {field} anchors are invalid")
    result = tuple(retrieval_key(str(item)) for item in value)
    if any(not item for item in result):
        raise TMNoteWordBoxError(f"TM page-61 {field} contains an empty anchor")
    return result


def _date_value(payload: dict[str, Any], field: str) -> date:
    value = payload.get(field)
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise TMNoteWordBoxError(f"invalid TM page-61 {field}") from exc
    raise TMNoteWordBoxError(f"invalid TM page-61 {field}")


def _positive(payload: dict[str, Any], field: str, *, upper: float | None = None) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise TMNoteWordBoxError(f"invalid positive TM page-61 setting: {field}")
    result = float(value)
    if upper is not None and result >= upper:
        raise TMNoteWordBoxError(f"TM page-61 {field} must be below {upper}")
    return result


def load_tm_page61_policy(path: Path) -> TMPage61Policy:
    """Load the immutable source-scoped page-61 reconstruction contract."""

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMNoteWordBoxError(f"cannot load TM page-61 policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE61_EXCHANGE_RATE_FIXED_GRID_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 61
        or payload.get("page_tag") != "page-0061"
        or payload.get("scope") != "CONSOLIDATED"
    ):
        raise TMNoteWordBoxError("TM page-61 policy identity drifted")
    hash_fields = (
        "source_pdf_sha256",
        "source_render_sha256",
        "source_ocr_sha256",
        "upstream_ocr_sha256",
    )
    hashes = tuple(payload.get(field) for field in hash_fields)
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMNoteWordBoxError("TM page-61 source hashes are invalid")
    thresholds = tuple(
        payload.get(field)
        for field in ("minimum_line_score", "minimum_anchor_similarity", "minimum_unit_similarity")
    )
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1
        for value in thresholds
    ):
        raise TMNoteWordBoxError("TM page-61 similarity thresholds are invalid")
    unit = payload.get("unit")
    table = payload.get("table")
    geometry = payload.get("geometry")
    continuation = payload.get("continuation")
    if not all(isinstance(item, dict) for item in (unit, table, geometry, continuation)):
        raise TMNoteWordBoxError("TM page-61 unit/table policy is incomplete")
    if (
        unit.get("canonical") != "VND"
        or unit.get("multiplier") != 1
        or unit.get("denominator") != "ONE_UNIT_OF_ROW_CURRENCY"
    ):
        raise TMNoteWordBoxError("TM page-61 native currency-rate unit drifted")
    if (
        table.get("table_key") != "EXCHANGE_RATE"
        or str(table.get("note_number")) != "6"
        or table.get("expected_numeric_rows") != 10
    ):
        raise TMNoteWordBoxError("TM page-61 table contract drifted")

    raw_periods = payload.get("periods")
    if not isinstance(raw_periods, list) or len(raw_periods) != 2:
        raise TMNoteWordBoxError("TM page-61 must define two period axes")
    periods = []
    for record in raw_periods:
        if not isinstance(record, dict):
            raise TMNoteWordBoxError("TM page-61 period is invalid")
        right_edge = record.get("right_edge")
        if isinstance(right_edge, bool) or not isinstance(right_edge, (int, float)):
            raise TMNoteWordBoxError("TM page-61 period edge is invalid")
        periods.append(
            TMPage61PeriodSpec(
                period_role=str(record.get("period_role", "")),
                visible_date=_date_value(record, "visible_date"),
                header_anchors=_anchors(record.get("header_anchors"), "period header"),
                right_edge=float(right_edge),
            )
        )
    if (
        tuple(item.period_role for item in periods) != _PERIOD_ROLES
        or tuple(item.visible_date for item in periods) != _PERIOD_DATES
        or tuple(item.right_edge for item in periods) != _PERIOD_RIGHT_EDGES
    ):
        raise TMNoteWordBoxError("TM page-61 period order/date/geometry drifted")

    raw_currencies = payload.get("currencies")
    if not isinstance(raw_currencies, list) or len(raw_currencies) != 10:
        raise TMNoteWordBoxError("TM page-61 currency denominator drifted")
    currencies = []
    for record in raw_currencies:
        if not isinstance(record, dict):
            raise TMNoteWordBoxError("TM page-61 currency row is invalid")
        code = str(record.get("currency_code", ""))
        label = str(record.get("canonical_label", ""))
        if not code or not label:
            raise TMNoteWordBoxError("TM page-61 currency fields are invalid")
        currencies.append(
            TMPage61CurrencySpec(
                currency_code=code,
                canonical_label=label,
                label_anchors=_anchors(record.get("label_anchors"), "currency label"),
            )
        )
    if tuple(item.currency_code for item in currencies) != _CURRENCY_CODES:
        raise TMNoteWordBoxError("TM page-61 currency order drifted")

    forbidden = payload.get("forbidden_semantic_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMNoteWordBoxError("TM page-61 forbidden semantic inputs drifted")
    if (
        continuation.get("page_61_closes_note_6") is not True
        or continuation.get("page_61_is_document_final_page") is not True
    ):
        raise TMNoteWordBoxError("TM page-61 closure contract drifted")
    return TMPage61Policy(
        source_path=path,
        document=str(payload.get("document", "")),
        page_number=61,
        page_tag="page-0061",
        scope="CONSOLIDATED",
        scope_binding=str(payload.get("scope_binding", "")),
        source_pdf_sha256=str(hashes[0]),
        source_render_sha256=str(hashes[1]),
        source_ocr_sha256=str(hashes[2]),
        upstream_ocr_sha256=str(hashes[3]),
        minimum_line_score=float(thresholds[0]),
        minimum_anchor_similarity=float(thresholds[1]),
        minimum_unit_similarity=float(thresholds[2]),
        unit_anchors=_anchors(unit.get("anchors"), "unit"),
        canonical_unit="VND",
        unit_multiplier=1,
        unit_denominator="ONE_UNIT_OF_ROW_CURRENCY",
        table_key="EXCHANGE_RATE",
        note_number="6",
        title_anchors=_anchors(table.get("title_anchors"), "title"),
        periods=tuple(periods),
        currencies=tuple(currencies),
        numeric_cluster_line_heights=_positive(geometry, "numeric_cluster_line_heights"),
        row_attach_line_heights=_positive(geometry, "row_attach_line_heights"),
        axis_max_distance_line_heights=_positive(geometry, "axis_max_distance_line_heights"),
        page_footer_top_ratio=_positive(geometry, "page_footer_top_ratio", upper=1),
        page_61_closes_note_6=True,
        page_61_is_document_final_page=True,
        forbidden_semantic_inputs=tuple(str(item) for item in forbidden),
    )


def _find_anchor_line(
    lines: tuple[_Line, ...],
    anchors: tuple[str, ...],
    policy: TMPage61Policy,
    *,
    minimum_y: float = float("-inf"),
    maximum_y: float = float("inf"),
) -> _Line:
    candidates = sorted(
        (
            (_best_anchor_similarity(line.text, anchors), line)
            for line in lines
            if minimum_y < line.y_center < maximum_y
        ),
        key=lambda item: (-item[0], item[1].y_center, item[1].index),
    )
    if not candidates or candidates[0][0] < policy.minimum_anchor_similarity:
        raise TMNoteWordBoxError(f"TM page-61 anchor is unresolved: {anchors}")
    return candidates[0][1]


def parse_tm_page61(
    result_path: Path,
    source_image_path: Path,
    policy: TMPage61Policy,
    *,
    page_tag: str = "page-0061",
) -> ParsedTMPage61:
    """Reconstruct all ten currency rows with schema mapping authority disabled."""

    if page_tag != policy.page_tag:
        raise TMNoteWordBoxError("TM page-61 page tag drifted")
    if sha256_file(result_path) != policy.source_ocr_sha256:
        raise TMNoteWordBoxError("TM page-61 compact OCR fixture hash drifted")
    if sha256_file(source_image_path) != policy.source_render_sha256:
        raise TMNoteWordBoxError("TM page-61 source render hash drifted")
    input_path, lines, metadata = _load_lines(result_path, policy.minimum_line_score)
    if metadata != {
        "upstream_ocr_sha256": policy.upstream_ocr_sha256,
        "source_render_sha256": policy.source_render_sha256,
        "source_pdf_sha256": policy.source_pdf_sha256,
    }:
        raise TMNoteWordBoxError("TM page-61 compact OCR provenance drifted")
    line_height = float(statistics.median(line.height for line in lines))
    if line_height <= 0:
        raise TMNoteWordBoxError("TM page-61 line height is invalid")
    source_bbox = _union(lines)
    footer_top = source_bbox.y1 * policy.page_footer_top_ratio
    try:
        compact_payload = json.loads(result_path.read_text(encoding="utf-8"))
        raw_scores = compact_payload["rec_scores"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise TMNoteWordBoxError("TM page-61 compact OCR scores are unreadable") from exc
    rejected_low_score_indices = tuple(
        index for index, score in enumerate(raw_scores) if float(score) < policy.minimum_line_score
    )
    if rejected_low_score_indices != _EXPECTED_LOW_SCORE_INDICES:
        raise TMNoteWordBoxError(
            f"TM page-61 rejected low-confidence line set drifted: {rejected_low_score_indices}"
        )

    title = _find_anchor_line(lines, policy.title_anchors, policy, maximum_y=footer_top)
    labels = tuple(
        _find_anchor_line(
            lines,
            spec.label_anchors,
            policy,
            minimum_y=title.y_center,
            maximum_y=footer_top,
        )
        for spec in policy.currencies
    )
    if len({line.index for line in labels}) != 10 or tuple(
        line.y_center for line in labels
    ) != tuple(sorted(line.y_center for line in labels)):
        raise TMNoteWordBoxError("TM page-61 currency row order drifted")
    first_row_y = labels[0].bbox.y0

    date_lines = tuple(
        _find_anchor_line(
            lines,
            spec.header_anchors,
            policy,
            minimum_y=title.y_center,
            maximum_y=first_row_y,
        )
        for spec in policy.periods
    )
    if len({line.index for line in date_lines}) != 2:
        raise TMNoteWordBoxError("TM page-61 period headers are not unique")
    unit_lines = tuple(
        sorted(
            (
                line
                for line in lines
                if max(item.y_center for item in date_lines) < line.y_center < first_row_y
                and _best_anchor_similarity(line.text, policy.unit_anchors)
                >= policy.minimum_unit_similarity
            ),
            key=lambda line: line.x_center,
        )
    )
    if len(unit_lines) != 2:
        raise TMNoteWordBoxError("TM page-61 visible native-unit denominator drifted")

    periods = []
    for ordinal, (spec, date_line, unit_line) in enumerate(
        zip(policy.periods, date_lines, unit_lines, strict=True), start=1
    ):
        if (
            parse_vietnamese_date(date_line.text) != spec.visible_date
            or abs(date_line.x_right - spec.right_edge) > line_height * 1.5
            or abs(unit_line.x_right - spec.right_edge) > line_height * 1.5
            or retrieval_key(unit_line.text) != "dong"
        ):
            raise TMNoteWordBoxError(
                f"TM page-61 visible period/unit geometry drifted: {spec.period_role}"
            )
        periods.append(
            TMPage61PeriodBinding(
                ordinal=ordinal,
                period_role=spec.period_role,
                visible_date=spec.visible_date,
                period_type="SNAPSHOT",
                period_start=spec.visible_date,
                period_end=spec.visible_date,
                axis_right_edge=spec.right_edge,
                raw_header_text=normalize_text(date_line.text),
                date_line_index=date_line.index,
                date_bbox=date_line.bbox,
                raw_unit_text=normalize_text(unit_line.text),
                unit_line_index=unit_line.index,
                unit_bbox=unit_line.bbox,
                canonical_unit=policy.canonical_unit,
                unit_multiplier=policy.unit_multiplier,
                unit_denominator=policy.unit_denominator,
                evidence=(
                    "snapshot date parsed from the visible page-61 column header",
                    "VND unit matched from the visible per-column đồng header",
                    "unit denominator is one unit of the currency named by the source row",
                    "European decimal comma remains decimal precision",
                ),
            )
        )
    periods_tuple = tuple(periods)

    relevant_numeric = tuple(
        line
        for line in lines
        if labels[0].y_center - line_height * policy.row_attach_line_heights
        < line.y_center
        < labels[-1].y_center + line_height * policy.row_attach_line_heights
        and _numeric_only(line.text)
    )
    numeric_groups = tuple(
        tuple(group)
        for group in _clusters(
            relevant_numeric,
            line_height * policy.numeric_cluster_line_heights,
        )
    )
    if len(numeric_groups) != 10 or any(len(group) != 2 for group in numeric_groups):
        raise TMNoteWordBoxError(
            "TM page-61 numeric group denominator drifted: "
            f"{tuple(len(group) for group in numeric_groups)}"
        )

    rows = []
    used_numeric: set[int] = set()
    for ordinal, (spec, label, group) in enumerate(
        zip(policy.currencies, labels, numeric_groups, strict=True), start=1
    ):
        if abs(statistics.fmean(line.y_center for line in group) - label.y_center) > (
            line_height * policy.row_attach_line_heights
        ):
            raise TMNoteWordBoxError(f"TM page-61 row attachment drifted: {spec.currency_code}")
        per_axis: list[_Line | None] = [None, None]
        for line in group:
            distances = [abs(period.axis_right_edge - line.x_right) for period in periods_tuple]
            index = min(range(2), key=distances.__getitem__)
            if (
                distances[index] > line_height * policy.axis_max_distance_line_heights
                or per_axis[index] is not None
            ):
                raise TMNoteWordBoxError(
                    f"TM page-61 numeric cell geometry drifted: {spec.currency_code}"
                )
            per_axis[index] = line
            used_numeric.add(line.index)
        if any(line is None for line in per_axis):
            raise TMNoteWordBoxError(f"TM page-61 period cell is missing: {spec.currency_code}")
        value_lines = tuple(line for line in per_axis if line is not None)
        cells = tuple(parse_financial_number(line.text) for line in value_lines)
        if any(cell.observation is not ObservationKind.VALUE for cell in cells):
            raise TMNoteWordBoxError(f"TM page-61 non-value rate cell: {spec.currency_code}")
        if any(
            not _RATE_TEXT.fullmatch(cell.raw_text) or cell.value.as_tuple().exponent != -2
            for cell in cells
            if cell.value is not None
        ):
            raise TMNoteWordBoxError(
                f"TM page-61 decimal-comma precision drifted: {spec.currency_code}"
            )
        rows.append(
            TMPage61LogicalRow(
                row_id=f"{page_tag}:{policy.table_key.lower()}:row-{ordinal:04d}",
                table_key=policy.table_key,
                ordinal=ordinal,
                currency_code=spec.currency_code,
                canonical_label=spec.canonical_label,
                row=ReaderRow(
                    source_row_ids=_source_ids(page_tag, (label, *value_lines)),
                    label=normalize_text(label.text),
                    note_reference=policy.note_number,
                    cells=cells,
                ),
                label_bbox=label.bbox,
                value_bboxes=tuple(line.bbox for line in value_lines),
                label_line_index=label.index,
                value_line_indices=tuple(line.index for line in value_lines),
                cell_period_starts=tuple(period.period_start for period in periods_tuple),
                cell_period_ends=tuple(period.period_end for period in periods_tuple),
                cell_period_roles=tuple(period.period_role for period in periods_tuple),
                cell_period_types=tuple(period.period_type for period in periods_tuple),
                cell_unit_denominators=tuple(period.unit_denominator for period in periods_tuple),
                mapping_approved=False,
            )
        )
    rows_tuple = tuple(rows)
    post_table_numeric = tuple(
        sorted(
            line.index
            for line in lines
            if rows_tuple[-1].label_bbox.y1 < line.y_center < footer_top
            and _numeric_only(line.text)
        )
    )
    footer_numeric = tuple(
        sorted(
            line.index for line in lines if line.y_center >= footer_top and _numeric_only(line.text)
        )
    )
    table_lines = (
        title,
        *date_lines,
        *unit_lines,
        *labels,
        *(line for group in numeric_groups for line in group),
    )
    table = TMPage61Table(
        ordinal=1,
        table_key=policy.table_key,
        note_number=policy.note_number,
        title=normalize_text(title.text),
        title_line_index=title.index,
        periods=periods_tuple,
        rows=rows_tuple,
        bbox=_union(table_lines),
    )
    result = ParsedTMPage61(
        input_path=input_path,
        source_sha256=policy.source_ocr_sha256,
        upstream_ocr_sha256=policy.upstream_ocr_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_pdf_sha256=policy.source_pdf_sha256,
        page_tag=page_tag,
        scope=policy.scope,
        scope_binding=policy.scope_binding,
        table=table,
        tables=(table,),
        periods=periods_tuple,
        rows=rows_tuple,
        line_height=line_height,
        source_ocr_bbox=source_bbox,
        table_bbox=table.bbox,
        unassigned_numeric_line_indices=tuple(
            sorted({line.index for line in relevant_numeric} - used_numeric)
        ),
        excluded_low_confidence_line_indices=rejected_low_score_indices,
        excluded_post_table_numeric_line_indices=post_table_numeric,
        excluded_footer_numeric_line_indices=footer_numeric,
        continues_after_page_61=not policy.page_61_is_document_final_page,
        mapping_authority=False,
        evidence=(
            "one complete page-61 exchange-rate table reconstructed from immutable PP-OCRv6 geometry",
            "ten currency rows preserve source order and all 20 finite values",
            "current and prior snapshot columns bind to their visible dates without axis swapping",
            "each value is VND per one unit of the row currency with multiplier one",
            "decimal-comma precision is preserved exactly and no integer rounding is applied",
            "signature, stamp, approval and footer evidence remains outside financial rows",
            "schema mapping authority remains false pending the coordinated schema freeze",
        ),
    )
    if (
        len(result.rows) != 10
        or result.numeric_row_count != 10
        or result.financial_slot_count != 20
        or result.observation_count(ObservationKind.VALUE) != 20
        or result.observation_count(ObservationKind.ZERO) != 0
        or result.observation_count(ObservationKind.DASH) != 0
        or result.observation_count(ObservationKind.BLANK) != 0
        or result.unassigned_numeric_line_indices
        or result.excluded_low_confidence_line_indices != _EXPECTED_LOW_SCORE_INDICES
        or result.excluded_post_table_numeric_line_indices != _EXPECTED_POST_TABLE_NUMERIC_INDICES
        or result.excluded_footer_numeric_line_indices != _EXPECTED_FOOTER_NUMERIC_INDICES
        or result.continues_after_page_61
    ):
        raise TMNoteWordBoxError(
            "TM page-61 exact source denominator drifted: "
            f"rows={len(result.rows)}, slots={result.financial_slot_count}, "
            f"value={result.observation_count(ObservationKind.VALUE)}, "
            f"unassigned={result.unassigned_numeric_line_indices}, "
            f"post_table={result.excluded_post_table_numeric_line_indices}, "
            f"footer={result.excluded_footer_numeric_line_indices}"
        )
    return result


__all__ = [
    "ParsedTMPage61",
    "TMPage61CurrencySpec",
    "TMPage61LogicalRow",
    "TMPage61PeriodBinding",
    "TMPage61Policy",
    "TMPage61Table",
    "load_tm_page61_policy",
    "parse_tm_page61",
]
