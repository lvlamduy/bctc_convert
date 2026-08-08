"""Hash-bound fixed-grid reconstruction for MBB consolidated TM page 54.

Page 54 is the independently owned note 4.2 business-segment matrix.  Its
balance-sheet metrics use snapshot periods, income metrics use duration
periods, and four visibly printed dashes remain DASH observations.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import cv2
import yaml

from bctc_ai.core.contracts import BoundingBox, ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import (
    normalize_text,
    parse_financial_number,
    parse_vietnamese_date,
    retrieval_key,
)
from bctc_ai.evaluation.word_box_rows import VisualCellEvidence
from bctc_ai.evaluation.word_box_rows_v3 import (
    _detect_visible_dash_v3,
    load_word_box_reconstruction_v3_config,
)
from bctc_ai.tables.tm_note_word_box import (
    TMNoteRowKind,
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
_AXIS_KEYS = (
    "FINANCE_BANKING",
    "SECURITIES_FUND_MANAGEMENT",
    "INSURANCE",
    "DEBT_AND_ASSET_MANAGEMENT",
    "ELIMINATION",
    "TOTAL",
)
_METRIC_KEYS = (
    "ASSETS",
    "LIABILITIES",
    "FIXED_ASSETS",
    "REVENUE",
    "EXPENSE",
    "PROFIT_BEFORE_TAX",
)
_REQUIRED_FORBIDDEN = {
    "missing_ocr_cell_as_dash_without_pixel_evidence",
    "template_labels_as_row_reconstruction_input",
    "approved_report_norm_id_assignment",
    "historical_or_mongodb_values",
    "human_review_answers",
    "dash_as_zero",
    "accounting_equations_as_value_imputation",
    "flat_period_type_across_mixed_metric_rows",
    "page53_values_as_page54_mapping_or_imputation",
}


@dataclass(frozen=True)
class TMPage54PeriodSpec:
    period_role: str
    visible_date: date
    snapshot_start: date
    snapshot_end: date
    duration_start: date
    duration_end: date


@dataclass(frozen=True)
class TMPage54AxisSpec:
    axis_key: str
    canonical_label: str
    current_header_line_anchors: tuple[tuple[str, ...], ...]
    comparative_header_line_anchors: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class TMPage54MetricSpec:
    metric_key: str
    canonical_label: str
    label_anchors: tuple[str, ...]
    period_type: str
    expected_dash_axes: tuple[str, ...]


@dataclass(frozen=True)
class TMPage54TableSpec:
    table_key: str
    note_number: str
    title_anchors: tuple[str, ...]
    expected_structural_rows: int
    expected_numeric_rows_per_period: int


@dataclass(frozen=True)
class TMPage54Policy:
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
    periods: tuple[TMPage54PeriodSpec, ...]
    table: TMPage54TableSpec
    axes: tuple[TMPage54AxisSpec, ...]
    metrics: tuple[TMPage54MetricSpec, ...]
    numeric_cluster_line_heights: float
    label_attach_line_heights: float
    page_footer_top_ratio: float
    dash_config: dict[str, float | int]
    dash_config_path: Path
    page_54_closes_note_4_2: bool
    page_55_starts_note_number: str
    forbidden_semantic_inputs: tuple[str, ...]


@dataclass(frozen=True)
class TMPage54PeriodBinding:
    period_role: str
    visible_date: date
    date_line_index: int
    date_bbox: BoundingBox
    snapshot_start: date
    snapshot_end: date
    duration_start: date
    duration_end: date


@dataclass(frozen=True)
class TMPage54AxisBinding:
    ordinal: int
    axis_key: str
    canonical_label: str
    axis_right_edge: float
    current_header_text: str
    comparative_header_text: str
    current_header_line_indices: tuple[int, ...]
    comparative_header_line_indices: tuple[int, ...]
    current_header_bbox: BoundingBox
    comparative_header_bbox: BoundingBox
    current_unit_bbox: BoundingBox
    comparative_unit_bbox: BoundingBox
    canonical_unit: str
    unit_multiplier: int
    evidence: tuple[str, ...]

    @property
    def header_line_indices(self) -> tuple[int, ...]:
        return (*self.current_header_line_indices, *self.comparative_header_line_indices)


@dataclass(frozen=True)
class TMPage54LogicalRow:
    row_id: str
    table_key: str
    note_number: str
    ordinal: int
    row: ReaderRow
    row_kind: TMNoteRowKind
    source_role: str
    metric_key: str | None
    period_role: str | None
    period_type: str | None
    y_anchor: float
    label_bbox: BoundingBox | None
    value_bboxes: tuple[BoundingBox | None, ...]
    label_line_indices: tuple[int, ...]
    value_line_indices: tuple[tuple[int, ...], ...]
    visual_cell_evidence: tuple[VisualCellEvidence | None, ...]
    period_source_line_indices: tuple[int, ...]
    cell_period_starts: tuple[date | None, ...]
    cell_period_ends: tuple[date | None, ...]
    cell_period_roles: tuple[str | None, ...]
    cell_period_types: tuple[str | None, ...]
    mapping_approved: bool

    @property
    def financial_slot_count(self) -> int:
        return len(self.row.cells) if self.row_kind is TMNoteRowKind.NUMERIC else 0


@dataclass(frozen=True)
class TMPage54Table:
    ordinal: int
    table_key: str
    note_number: str
    title: str
    title_line_indices: tuple[int, ...]
    axes: tuple[TMPage54AxisBinding, ...]
    period_bindings: tuple[TMPage54PeriodBinding, ...]
    rows: tuple[TMPage54LogicalRow, ...]
    bbox: BoundingBox


@dataclass(frozen=True)
class ParsedTMPage54:
    input_path: str
    source_sha256: str
    upstream_ocr_sha256: str
    source_render_sha256: str
    source_pdf_sha256: str
    page_tag: str
    scope: str
    scope_binding: str
    table: TMPage54Table
    axes: tuple[TMPage54AxisBinding, ...]
    period_bindings: tuple[TMPage54PeriodBinding, ...]
    rows: tuple[TMPage54LogicalRow, ...]
    line_height: float
    source_ocr_bbox: BoundingBox
    table_bbox: BoundingBox
    unassigned_numeric_line_indices: tuple[int, ...]
    excluded_artifact_line_indices: tuple[int, ...]
    excluded_footer_numeric_line_indices: tuple[int, ...]
    continues_to_page_55: bool
    next_page_note_number: str
    mapping_authority: bool
    evidence: tuple[str, ...]

    @property
    def tables(self) -> tuple[TMPage54Table, ...]:
        return (self.table,)

    @property
    def numeric_row_count(self) -> int:
        return sum(row.row_kind is TMNoteRowKind.NUMERIC for row in self.rows)

    @property
    def label_only_row_count(self) -> int:
        return sum(row.row_kind is TMNoteRowKind.LABEL_ONLY for row in self.rows)

    @property
    def financial_slot_count(self) -> int:
        return sum(row.financial_slot_count for row in self.rows)

    def observation_count(self, observation: ObservationKind) -> int:
        return sum(
            cell.observation is observation
            for row in self.rows
            if row.row_kind is TMNoteRowKind.NUMERIC
            for cell in row.row.cells
        )


def _anchors(payload: Any, field: str) -> tuple[str, ...]:
    if not isinstance(payload, list) or not payload:
        raise TMNoteWordBoxError(f"TM page-54 {field} anchors are invalid")
    result = tuple(retrieval_key(str(value)) for value in payload)
    if any(not value for value in result):
        raise TMNoteWordBoxError(f"TM page-54 {field} contains an empty anchor")
    return result


def _anchor_groups(payload: Any, field: str) -> tuple[tuple[str, ...], ...]:
    if not isinstance(payload, list) or not payload:
        raise TMNoteWordBoxError(f"TM page-54 {field} groups are invalid")
    return tuple(_anchors(group, f"{field} line") for group in payload)


def _date_value(value: Any, field: str) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise TMNoteWordBoxError(f"invalid TM page-54 {field}") from exc
    raise TMNoteWordBoxError(f"invalid TM page-54 {field}")


def _positive(payload: dict[str, Any], field: str, *, upper: float | None = None) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise TMNoteWordBoxError(f"invalid positive TM page-54 setting: {field}")
    result = float(value)
    if upper is not None and result >= upper:
        raise TMNoteWordBoxError(f"TM page-54 {field} exceeds its upper bound")
    return result


def load_tm_page54_policy(path: Path) -> TMPage54Policy:
    """Load the immutable page-54 reconstruction contract."""

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMNoteWordBoxError(f"cannot load TM page-54 policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE54_BUSINESS_SEGMENT_FIXED_GRID_DASH_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 54
        or payload.get("page_tag") != "page-0054"
        or payload.get("scope") != "CONSOLIDATED"
    ):
        raise TMNoteWordBoxError("TM page-54 policy identity drifted")
    hashes = tuple(
        payload.get(field)
        for field in (
            "source_pdf_sha256",
            "source_render_sha256",
            "source_ocr_sha256",
            "upstream_ocr_sha256",
        )
    )
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMNoteWordBoxError("TM page-54 source hashes are invalid")
    thresholds = tuple(
        payload.get(field)
        for field in ("minimum_line_score", "minimum_anchor_similarity", "minimum_unit_similarity")
    )
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1
        for value in thresholds
    ):
        raise TMNoteWordBoxError("TM page-54 thresholds are invalid")
    unit = payload.get("unit")
    table = payload.get("table")
    geometry = payload.get("geometry")
    continuation = payload.get("continuation")
    if not all(isinstance(value, dict) for value in (unit, table, geometry, continuation)):
        raise TMNoteWordBoxError("TM page-54 policy sections are incomplete")
    multiplier = unit.get("multiplier")
    canonical_unit = unit.get("canonical")
    if (
        isinstance(multiplier, bool)
        or not isinstance(multiplier, int)
        or multiplier <= 0
        or not isinstance(canonical_unit, str)
        or not canonical_unit
    ):
        raise TMNoteWordBoxError("TM page-54 unit binding is invalid")

    raw_periods = payload.get("period_blocks")
    if not isinstance(raw_periods, list) or len(raw_periods) != 2:
        raise TMNoteWordBoxError("TM page-54 period blocks are invalid")
    periods = tuple(
        TMPage54PeriodSpec(
            period_role=str(record.get("period_role")),
            visible_date=_date_value(record.get("visible_date"), "visible date"),
            snapshot_start=_date_value(record.get("snapshot_start"), "snapshot start"),
            snapshot_end=_date_value(record.get("snapshot_end"), "snapshot end"),
            duration_start=_date_value(record.get("duration_start"), "duration start"),
            duration_end=_date_value(record.get("duration_end"), "duration end"),
        )
        for record in raw_periods
        if isinstance(record, dict)
    )
    if (
        tuple(period.period_role for period in periods) != ("CURRENT", "COMPARATIVE")
        or tuple(period.visible_date for period in periods)
        != (date(2026, 3, 31), date(2025, 12, 31))
        or any(period.snapshot_start != period.snapshot_end for period in periods)
        or periods[0].duration_start != date(2026, 1, 1)
        or periods[0].duration_end != date(2026, 3, 31)
        or periods[1].duration_start != date(2025, 1, 1)
        or periods[1].duration_end != date(2025, 12, 31)
    ):
        raise TMNoteWordBoxError("TM page-54 period semantics drifted")
    if (
        table.get("table_key") != "BUSINESS_SEGMENT"
        or table.get("note_number") != "4.2"
        or table.get("expected_structural_rows") != 1
        or table.get("expected_numeric_rows_per_period") != 6
    ):
        raise TMNoteWordBoxError("TM page-54 table denominator drifted")
    table_spec = TMPage54TableSpec(
        table_key="BUSINESS_SEGMENT",
        note_number="4.2",
        title_anchors=_anchors(table.get("title_anchors"), "title"),
        expected_structural_rows=1,
        expected_numeric_rows_per_period=6,
    )

    raw_axes = payload.get("axes")
    if not isinstance(raw_axes, list) or len(raw_axes) != 6:
        raise TMNoteWordBoxError("TM page-54 axes are invalid")
    axes = tuple(
        TMPage54AxisSpec(
            axis_key=str(record.get("axis_key")),
            canonical_label=str(record.get("canonical_label", "")),
            current_header_line_anchors=_anchor_groups(
                record.get("current_header_line_anchors"), "current axis header"
            ),
            comparative_header_line_anchors=_anchor_groups(
                record.get("comparative_header_line_anchors"), "comparative axis header"
            ),
        )
        for record in raw_axes
        if isinstance(record, dict)
    )
    if tuple(axis.axis_key for axis in axes) != _AXIS_KEYS or any(
        not axis.canonical_label for axis in axes
    ):
        raise TMNoteWordBoxError("TM page-54 axis order drifted")
    debt_axis = axes[3]
    if (
        debt_axis.current_header_line_anchors == debt_axis.comparative_header_line_anchors
        or len(debt_axis.current_header_line_anchors) != 2
        or len(debt_axis.comparative_header_line_anchors) != 2
    ):
        raise TMNoteWordBoxError("TM page-54 debt/asset header variants drifted")

    raw_metrics = payload.get("metrics")
    if not isinstance(raw_metrics, list) or len(raw_metrics) != 6:
        raise TMNoteWordBoxError("TM page-54 metrics are invalid")
    metrics = tuple(
        TMPage54MetricSpec(
            metric_key=str(record.get("metric_key")),
            canonical_label=str(record.get("canonical_label", "")),
            label_anchors=_anchors(record.get("label_anchors"), "metric label"),
            period_type=str(record.get("period_type")),
            expected_dash_axes=tuple(str(value) for value in record.get("expected_dash_axes", ())),
        )
        for record in raw_metrics
        if isinstance(record, dict)
    )
    if (
        tuple(metric.metric_key for metric in metrics) != _METRIC_KEYS
        or tuple(metric.period_type for metric in metrics)
        != ("SNAPSHOT", "SNAPSHOT", "SNAPSHOT", "DURATION", "DURATION", "DURATION")
        or {
            metric.metric_key: metric.expected_dash_axes
            for metric in metrics
            if metric.expected_dash_axes
        }
        != {
            "FIXED_ASSETS": ("ELIMINATION",),
            "PROFIT_BEFORE_TAX": ("ELIMINATION",),
        }
        or any(not metric.canonical_label for metric in metrics)
    ):
        raise TMNoteWordBoxError("TM page-54 metric semantics drifted")

    dash_name = payload.get("dash_detector_config")
    if not isinstance(dash_name, str) or Path(dash_name).name != dash_name:
        raise TMNoteWordBoxError("TM page-54 dash-detector path is invalid")
    dash_path = (path.parent / dash_name).resolve()
    if not dash_path.is_file() or sha256_file(dash_path) != payload.get(
        "dash_detector_config_sha256"
    ):
        raise TMNoteWordBoxError("TM page-54 dash detector is absent or drifted")
    dash_config = load_word_box_reconstruction_v3_config(dash_path).base.base
    if (
        continuation.get("page_54_closes_note_4_2") is not True
        or continuation.get("page_55_starts_note_number") != "5"
    ):
        raise TMNoteWordBoxError("TM page-54 continuation boundary drifted")
    forbidden = payload.get("forbidden_semantic_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMNoteWordBoxError("TM page-54 forbidden inputs drifted")
    return TMPage54Policy(
        source_path=path,
        document=str(payload.get("document", "")),
        page_number=54,
        page_tag="page-0054",
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
        canonical_unit=canonical_unit,
        unit_multiplier=multiplier,
        periods=periods,
        table=table_spec,
        axes=axes,
        metrics=metrics,
        numeric_cluster_line_heights=_positive(geometry, "numeric_cluster_line_heights"),
        label_attach_line_heights=_positive(geometry, "label_attach_line_heights"),
        page_footer_top_ratio=_positive(geometry, "page_footer_top_ratio", upper=1.0),
        dash_config=dash_config,
        dash_config_path=dash_path,
        page_54_closes_note_4_2=True,
        page_55_starts_note_number="5",
        forbidden_semantic_inputs=tuple(str(value) for value in forbidden),
    )


def _find_anchor_line(
    lines: tuple[_Line, ...],
    anchors: tuple[str, ...],
    policy: TMPage54Policy,
    *,
    minimum_y: float = float("-inf"),
    maximum_y: float = float("inf"),
    minimum_x: float = float("-inf"),
    maximum_x: float = float("inf"),
    excluded_indices: frozenset[int] = frozenset(),
) -> _Line:
    candidates = sorted(
        (
            (_best_anchor_similarity(line.text, anchors), line)
            for line in lines
            if minimum_y < line.y_center < maximum_y
            and minimum_x < line.x_center < maximum_x
            and line.index not in excluded_indices
        ),
        key=lambda item: (-item[0], item[1].y_center, item[1].index),
    )
    if not candidates or candidates[0][0] < policy.minimum_anchor_similarity:
        raise TMNoteWordBoxError(f"TM page-54 anchor is unresolved: {anchors}")
    return candidates[0][1]


def _period_bindings(
    lines: tuple[_Line, ...], policy: TMPage54Policy
) -> tuple[TMPage54PeriodBinding, ...]:
    date_lines = tuple(
        sorted(
            (line for line in lines if parse_vietnamese_date(line.text) is not None),
            key=lambda line: line.y_center,
        )
    )
    if len(date_lines) != 2:
        raise TMNoteWordBoxError("TM page-54 visible date denominator drifted")
    bindings = []
    for spec, line in zip(policy.periods, date_lines, strict=True):
        if parse_vietnamese_date(line.text) != spec.visible_date:
            raise TMNoteWordBoxError("TM page-54 visible date drifted")
        bindings.append(
            TMPage54PeriodBinding(
                period_role=spec.period_role,
                visible_date=spec.visible_date,
                date_line_index=line.index,
                date_bbox=line.bbox,
                snapshot_start=spec.snapshot_start,
                snapshot_end=spec.snapshot_end,
                duration_start=spec.duration_start,
                duration_end=spec.duration_end,
            )
        )
    return tuple(bindings)


def _header_group(
    lines: tuple[_Line, ...],
    anchors: tuple[tuple[str, ...], ...],
    policy: TMPage54Policy,
    *,
    minimum_y: float,
    maximum_y: float,
    minimum_x: float,
    maximum_x: float,
) -> tuple[_Line, ...]:
    selected: list[_Line] = []
    for line_anchors in anchors:
        selected.append(
            _find_anchor_line(
                lines,
                line_anchors,
                policy,
                minimum_y=minimum_y,
                maximum_y=maximum_y,
                minimum_x=minimum_x,
                maximum_x=maximum_x,
                excluded_indices=frozenset(line.index for line in selected),
            )
        )
    if tuple(line.y_center for line in selected) != tuple(
        sorted(line.y_center for line in selected)
    ):
        raise TMNoteWordBoxError("TM page-54 multi-line header order drifted")
    return tuple(selected)


def _axis_bindings(
    lines: tuple[_Line, ...],
    periods: tuple[TMPage54PeriodBinding, ...],
    first_labels: tuple[_Line, ...],
    numeric_groups: tuple[tuple[_Line, ...], ...],
    policy: TMPage54Policy,
    line_height: float,
) -> tuple[TMPage54AxisBinding, ...]:
    line_by_index = {line.index: line for line in lines}
    block_headers: list[list[tuple[tuple[_Line, ...], _Line]]] = []
    for period, first_label in zip(periods, first_labels, strict=True):
        date_line = line_by_index[period.date_line_index]
        lower = date_line.y_center - line_height * 1.75
        upper = first_label.bbox.y0
        units = tuple(
            sorted(
                (
                    line
                    for line in lines
                    if lower < line.y_center < upper
                    and _best_anchor_similarity(line.text, policy.unit_anchors)
                    >= policy.minimum_unit_similarity
                ),
                key=lambda line: line.x_center,
            )
        )
        if len(units) != 6:
            raise TMNoteWordBoxError(f"TM page-54 {period.period_role} unit denominator drifted")
        centers = tuple(unit.x_center for unit in units)
        boundaries = (
            float("-inf"),
            *((left + right) / 2 for left, right in zip(centers[:-1], centers[1:], strict=True)),
            float("inf"),
        )
        records = []
        for ordinal, (axis, unit) in enumerate(zip(policy.axes, units, strict=True)):
            anchors = (
                axis.current_header_line_anchors
                if period.period_role == "CURRENT"
                else axis.comparative_header_line_anchors
            )
            header = _header_group(
                lines,
                anchors,
                policy,
                minimum_y=lower,
                maximum_y=unit.bbox.y0,
                minimum_x=boundaries[ordinal],
                maximum_x=boundaries[ordinal + 1],
            )
            records.append((header, unit))
        block_headers.append(records)

    full_rows = tuple(
        tuple(sorted(group, key=lambda line: line.x_right))
        for group in numeric_groups
        if len(group) == len(policy.axes)
    )
    if len(full_rows) != 8:
        raise TMNoteWordBoxError("TM page-54 full-row axis geometry drifted")
    results = []
    for ordinal, spec in enumerate(policy.axes, start=1):
        current_headers, current_unit = block_headers[0][ordinal - 1]
        comparative_headers, comparative_unit = block_headers[1][ordinal - 1]
        results.append(
            TMPage54AxisBinding(
                ordinal=ordinal,
                axis_key=spec.axis_key,
                canonical_label=spec.canonical_label,
                axis_right_edge=float(
                    statistics.median(row[ordinal - 1].x_right for row in full_rows)
                ),
                current_header_text=" ".join(normalize_text(line.text) for line in current_headers),
                comparative_header_text=" ".join(
                    normalize_text(line.text) for line in comparative_headers
                ),
                current_header_line_indices=(
                    *(line.index for line in current_headers),
                    current_unit.index,
                ),
                comparative_header_line_indices=(
                    *(line.index for line in comparative_headers),
                    comparative_unit.index,
                ),
                current_header_bbox=_union([*current_headers, current_unit]),
                comparative_header_bbox=_union([*comparative_headers, comparative_unit]),
                current_unit_bbox=current_unit.bbox,
                comparative_unit_bbox=comparative_unit.bbox,
                canonical_unit=policy.canonical_unit,
                unit_multiplier=policy.unit_multiplier,
                evidence=(
                    "business axis matched independently in both visible period blocks",
                    "the current and comparative debt/asset labels retain their raw variants",
                    "axis geometry is derived from eight complete numeric rows",
                    "axis identity is never selected from numeric magnitudes",
                ),
            )
        )
    if tuple(axis.axis_right_edge for axis in results) != tuple(
        sorted(axis.axis_right_edge for axis in results)
    ):
        raise TMNoteWordBoxError("TM page-54 axis order drifted")
    return tuple(results)


def _structural_row(
    *,
    page_tag: str,
    table_key: str,
    note_number: str,
    note_marker: _Line,
    title: _Line,
    axis_count: int,
) -> TMPage54LogicalRow:
    source_lines = [note_marker, title]
    return TMPage54LogicalRow(
        row_id=f"{page_tag}:{table_key.lower()}:row-0001",
        table_key=table_key,
        note_number=note_number,
        ordinal=1,
        row=ReaderRow(
            source_row_ids=_source_ids(page_tag, source_lines),
            label=normalize_text(f"{note_marker.text} {title.text}"),
            note_reference=note_number,
            cells=tuple(parse_financial_number(None) for _ in range(axis_count)),
        ),
        row_kind=TMNoteRowKind.LABEL_ONLY,
        source_role="BUSINESS_SEGMENT_TITLE",
        metric_key=None,
        period_role=None,
        period_type=None,
        y_anchor=statistics.fmean(line.y_center for line in source_lines),
        label_bbox=_union(source_lines),
        value_bboxes=tuple(None for _ in range(axis_count)),
        label_line_indices=(note_marker.index, title.index),
        value_line_indices=tuple(() for _ in range(axis_count)),
        visual_cell_evidence=tuple(None for _ in range(axis_count)),
        period_source_line_indices=(),
        cell_period_starts=tuple(None for _ in range(axis_count)),
        cell_period_ends=tuple(None for _ in range(axis_count)),
        cell_period_roles=tuple(None for _ in range(axis_count)),
        cell_period_types=tuple(None for _ in range(axis_count)),
        mapping_approved=False,
    )


def _numeric_row(
    *,
    page_tag: str,
    table_key: str,
    note_number: str,
    ordinal: int,
    label: _Line,
    group: tuple[_Line, ...],
    metric: TMPage54MetricSpec,
    period: TMPage54PeriodBinding,
    axes: tuple[TMPage54AxisBinding, ...],
    source_image: Any,
    source_image_path: Path,
    line_height: float,
    policy: TMPage54Policy,
) -> TMPage54LogicalRow:
    center = statistics.fmean(line.y_center for line in group)
    if abs(label.y_center - center) > line_height * policy.label_attach_line_heights:
        raise TMNoteWordBoxError(f"TM page-54 label attachment drifted: {metric.metric_key}")
    per_axis: list[list[_Line]] = [[] for _ in axes]
    for line in group:
        axis_index = min(
            range(len(axes)), key=lambda index: abs(axes[index].axis_right_edge - line.x_right)
        )
        per_axis[axis_index].append(line)
    if any(len(axis_lines) > 1 for axis_lines in per_axis):
        raise TMNoteWordBoxError(f"TM page-54 split numeric cell: {metric.metric_key}")

    cells = []
    visual = []
    value_bboxes = []
    for axis, axis_lines in zip(axes, per_axis, strict=True):
        evidence = None
        if axis_lines:
            if axis.axis_key in metric.expected_dash_axes:
                raise TMNoteWordBoxError(
                    f"TM page-54 expected printed dash became OCR value: {metric.metric_key}"
                )
            raw = " ".join(line.text for line in axis_lines)
            bbox = _union(axis_lines)
        else:
            if axis.axis_key not in metric.expected_dash_axes:
                raise TMNoteWordBoxError(
                    f"TM page-54 cell lacks OCR or declared dash: "
                    f"{metric.metric_key}/{axis.axis_key}"
                )
            evidence = _detect_visible_dash_v3(
                source_image,
                source_image_path=source_image_path,
                axis_right_edge=axis.axis_right_edge,
                anchor_center=center,
                line_height=line_height,
                config=policy.dash_config,
            )
            if evidence is None:
                raise TMNoteWordBoxError(
                    f"TM page-54 visible dash lacks constrained pixel evidence: "
                    f"{period.period_role}/{metric.metric_key}"
                )
            raw = "-"
            bbox = BoundingBox(*evidence.component_box)
        cell = parse_financial_number(raw)
        if cell.observation not in {
            ObservationKind.VALUE,
            ObservationKind.ZERO,
            ObservationKind.DASH,
        }:
            raise TMNoteWordBoxError("TM page-54 financial observation drifted")
        cells.append(cell)
        visual.append(evidence)
        value_bboxes.append(bbox)
    if sum(cell.observation is ObservationKind.DASH for cell in cells) != len(
        metric.expected_dash_axes
    ):
        raise TMNoteWordBoxError(f"TM page-54 dash denominator drifted: {metric.metric_key}")
    if metric.period_type == "SNAPSHOT":
        period_start, period_end = period.snapshot_start, period.snapshot_end
    else:
        period_start, period_end = period.duration_start, period.duration_end
    source_lines = [label, *group]
    return TMPage54LogicalRow(
        row_id=f"{page_tag}:{table_key.lower()}:row-{ordinal:04d}",
        table_key=table_key,
        note_number=note_number,
        ordinal=ordinal,
        row=ReaderRow(
            source_row_ids=_source_ids(page_tag, source_lines),
            label=normalize_text(label.text),
            note_reference=note_number,
            cells=tuple(cells),
        ),
        row_kind=TMNoteRowKind.NUMERIC,
        source_role=f"{period.period_role}_{metric.metric_key}",
        metric_key=metric.metric_key,
        period_role=period.period_role,
        period_type=metric.period_type,
        y_anchor=center,
        label_bbox=label.bbox,
        value_bboxes=tuple(value_bboxes),
        label_line_indices=(label.index,),
        value_line_indices=tuple(tuple(line.index for line in lines) for lines in per_axis),
        visual_cell_evidence=tuple(visual),
        period_source_line_indices=(period.date_line_index,),
        cell_period_starts=tuple(period_start for _ in axes),
        cell_period_ends=tuple(period_end for _ in axes),
        cell_period_roles=tuple(period.period_role for _ in axes),
        cell_period_types=tuple(metric.period_type for _ in axes),
        mapping_approved=False,
    )


def parse_tm_page54(
    result_path: Path,
    source_image_path: Path,
    policy: TMPage54Policy,
    *,
    page_tag: str = "page-0054",
) -> ParsedTMPage54:
    """Reconstruct page 54 with schema and mapping authority disabled."""

    if page_tag != policy.page_tag:
        raise TMNoteWordBoxError("TM page-54 page tag drifted")
    if sha256_file(result_path) != policy.source_ocr_sha256:
        raise TMNoteWordBoxError("TM page-54 compact OCR fixture hash drifted")
    if sha256_file(source_image_path) != policy.source_render_sha256:
        raise TMNoteWordBoxError("TM page-54 source render hash drifted")
    source_image = cv2.imread(str(source_image_path), cv2.IMREAD_GRAYSCALE)
    if source_image is None:
        raise TMNoteWordBoxError("TM page-54 source render cannot be decoded")
    input_path, lines, metadata = _load_lines(result_path, policy.minimum_line_score)
    if metadata != {
        "upstream_ocr_sha256": policy.upstream_ocr_sha256,
        "source_render_sha256": policy.source_render_sha256,
        "source_pdf_sha256": policy.source_pdf_sha256,
    }:
        raise TMNoteWordBoxError("TM page-54 compact OCR provenance drifted")
    if not lines:
        raise TMNoteWordBoxError("TM page-54 compact OCR is empty")
    line_height = float(statistics.median(line.height for line in lines))
    if line_height <= 0:
        raise TMNoteWordBoxError("TM page-54 line height is invalid")
    source_bbox = _union(lines)
    footer_top = source_bbox.y1 * policy.page_footer_top_ratio

    title = _find_anchor_line(lines, policy.table.title_anchors, policy)
    note_candidates = tuple(
        line
        for line in lines
        if retrieval_key(line.text) == retrieval_key(policy.table.note_number)
        and abs(line.y_center - title.y_center) <= line_height
        and line.x_right < title.bbox.x0
    )
    if len(note_candidates) != 1:
        raise TMNoteWordBoxError("TM page-54 visible note marker drifted")
    note_marker = note_candidates[0]
    period_bindings = _period_bindings(lines, policy)
    line_by_index = {line.index: line for line in lines}
    current_date = line_by_index[period_bindings[0].date_line_index]
    comparative_date = line_by_index[period_bindings[1].date_line_index]

    labels_by_period = []
    period_bounds = (
        (current_date.y_center, comparative_date.y_center - line_height * 1.5),
        (comparative_date.y_center, footer_top),
    )
    for minimum_y, maximum_y in period_bounds:
        labels = tuple(
            _find_anchor_line(
                lines,
                metric.label_anchors,
                policy,
                minimum_y=minimum_y,
                maximum_y=maximum_y,
                maximum_x=1_000,
            )
            for metric in policy.metrics
        )
        if tuple(label.y_center for label in labels) != tuple(
            sorted(label.y_center for label in labels)
        ):
            raise TMNoteWordBoxError("TM page-54 metric row order drifted")
        if len({label.index for label in labels}) != 6:
            raise TMNoteWordBoxError("TM page-54 metric labels are not unique")
        labels_by_period.append(labels)

    numeric_lines = tuple(
        line
        for line in lines
        if labels_by_period[0][0].y_center - line_height <= line.y_center < footer_top
        and _numeric_only(line.text)
    )
    numeric_groups = tuple(
        tuple(group)
        for group in _clusters(numeric_lines, line_height * policy.numeric_cluster_line_heights)
    )
    if len(numeric_groups) != 12 or tuple(len(group) for group in numeric_groups) != (
        6,
        6,
        5,
        6,
        6,
        5,
        6,
        6,
        5,
        6,
        6,
        5,
    ):
        raise TMNoteWordBoxError("TM page-54 numeric grid denominator drifted")
    axes = _axis_bindings(
        lines,
        period_bindings,
        (labels_by_period[0][0], labels_by_period[1][0]),
        numeric_groups,
        policy,
        line_height,
    )

    rows = [
        _structural_row(
            page_tag=page_tag,
            table_key=policy.table.table_key,
            note_number=policy.table.note_number,
            note_marker=note_marker,
            title=title,
            axis_count=6,
        )
    ]
    ordinal = 2
    group_index = 0
    for period, labels in zip(period_bindings, labels_by_period, strict=True):
        for metric, label in zip(policy.metrics, labels, strict=True):
            rows.append(
                _numeric_row(
                    page_tag=page_tag,
                    table_key=policy.table.table_key,
                    note_number=policy.table.note_number,
                    ordinal=ordinal,
                    label=label,
                    group=numeric_groups[group_index],
                    metric=metric,
                    period=period,
                    axes=axes,
                    source_image=source_image,
                    source_image_path=source_image_path,
                    line_height=line_height,
                    policy=policy,
                )
            )
            ordinal += 1
            group_index += 1
    rows_tuple = tuple(rows)
    used_numeric = {
        index for row in rows_tuple for indices in row.value_line_indices for index in indices
    }
    relevant_numeric = {line.index for line in numeric_lines}
    footer = tuple(
        sorted(
            line.index for line in lines if line.y_center >= footer_top and _numeric_only(line.text)
        )
    )
    artifacts = tuple(sorted(line.index for line in lines if not normalize_text(line.text)))
    table_lines = tuple(line for line in lines if title.bbox.y0 <= line.y_center < footer_top)
    table = TMPage54Table(
        ordinal=1,
        table_key=policy.table.table_key,
        note_number=policy.table.note_number,
        title=rows_tuple[0].row.label,
        title_line_indices=(note_marker.index, title.index),
        axes=axes,
        period_bindings=period_bindings,
        rows=rows_tuple,
        bbox=_union(table_lines),
    )
    result = ParsedTMPage54(
        input_path=input_path,
        source_sha256=policy.source_ocr_sha256,
        upstream_ocr_sha256=policy.upstream_ocr_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_pdf_sha256=policy.source_pdf_sha256,
        page_tag=page_tag,
        scope=policy.scope,
        scope_binding=policy.scope_binding,
        table=table,
        axes=axes,
        period_bindings=period_bindings,
        rows=rows_tuple,
        line_height=line_height,
        source_ocr_bbox=source_bbox,
        table_bbox=table.bbox,
        unassigned_numeric_line_indices=tuple(sorted(relevant_numeric - used_numeric)),
        excluded_artifact_line_indices=artifacts,
        excluded_footer_numeric_line_indices=footer,
        continues_to_page_55=not policy.page_54_closes_note_4_2,
        next_page_note_number=policy.page_55_starts_note_number,
        mapping_authority=False,
        evidence=(
            "note 4.2 is reconstructed from immutable PP-OCRv6 word-box geometry",
            "six business axes are independently bound in both visible period blocks",
            "the debt/asset-management axis preserves its two visible label variants",
            "balance-sheet rows retain snapshot semantics and income rows retain duration semantics",
            "68 finite values and four pixel-backed dashes preserve all 72 printed financial slots",
            "equations and page-53 totals are reserved for post-mapping validation only",
            "page 54 closes note 4.2; page 55 begins an independently owned narrative note 5",
            "schema identifiers are absent from parser inputs and mapping authority remains false",
        ),
    )
    if (
        len(result.rows) != 13
        or result.numeric_row_count != 12
        or result.label_only_row_count != 1
        or result.financial_slot_count != 72
        or result.observation_count(ObservationKind.VALUE) != 68
        or result.observation_count(ObservationKind.ZERO) != 0
        or result.observation_count(ObservationKind.DASH) != 4
        or result.observation_count(ObservationKind.BLANK) != 0
        or result.unassigned_numeric_line_indices
        or result.excluded_artifact_line_indices
        or result.excluded_footer_numeric_line_indices != (116,)
        or result.continues_to_page_55
        or result.next_page_note_number != "5"
    ):
        raise TMNoteWordBoxError(
            "TM page-54 exact source denominator drifted: "
            f"rows={len(result.rows)}, numeric={result.numeric_row_count}, "
            f"structural={result.label_only_row_count}, slots={result.financial_slot_count}, "
            f"value={result.observation_count(ObservationKind.VALUE)}, "
            f"dash={result.observation_count(ObservationKind.DASH)}, "
            f"unassigned={result.unassigned_numeric_line_indices}, "
            f"artifacts={result.excluded_artifact_line_indices}, "
            f"footer={result.excluded_footer_numeric_line_indices}"
        )
    return result


__all__ = [
    "ParsedTMPage54",
    "TMPage54AxisBinding",
    "TMPage54LogicalRow",
    "TMPage54PeriodBinding",
    "TMPage54Policy",
    "TMPage54Table",
    "load_tm_page54_policy",
    "parse_tm_page54",
]
