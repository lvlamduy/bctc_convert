"""Hash-bound fixed-grid reconstruction for MBB consolidated TM page 57.

The page contains one interest-rate-risk table with eight repricing axes.  Printed
dashes are retained only when constrained pixel evidence exists; tiny OCR glyphs
at dash locations are rejected by geometry and never promoted to numeric values.
"""

from __future__ import annotations

import itertools
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
    "OVERDUE",
    "NOT_REPRICED",
    "WITHIN_1M",
    "FROM_1_TO_3M",
    "FROM_3_TO_6M",
    "FROM_6_TO_12M",
    "OVER_1Y",
    "TOTAL",
)
_AXIS_RIGHT_EDGES = (1265.0, 1540.0, 1804.0, 2090.0, 2368.0, 2657.0, 2954.0, 3242.0)
_EXPECTED_METRIC_KEYS = (
    "CASH_AND_PRECIOUS_METALS",
    "SBV_DEPOSITS",
    "INTERBANK_ASSETS",
    "TRADING_SECURITIES",
    "DERIVATIVE_ASSETS",
    "CUSTOMER_LOANS_AND_PURCHASED_DEBT",
    "INVESTMENT_SECURITIES",
    "LONG_TERM_INVESTMENTS",
    "FIXED_ASSETS_AND_INVESTMENT_PROPERTY",
    "OTHER_ASSETS",
    "TOTAL_ASSETS",
    "GOVERNMENT_SBV_LIABILITIES",
    "INTERBANK_LIABILITIES",
    "CUSTOMER_DEPOSITS",
    "DERIVATIVE_LIABILITIES",
    "ENTRUSTED_FUNDS",
    "ISSUED_VALUABLE_PAPERS",
    "OTHER_LIABILITIES",
    "TOTAL_LIABILITIES",
    "ON_BALANCE_INTEREST_SENSITIVITY_GAP",
)
_EXPECTED_NUMERIC_GROUP_SIZES = (2, 2, 6, 3, 7, 7, 2, 2, 3, 8, 3, 6, 6, 6, 6, 6, 2, 7, 8)
_EXPECTED_ARTIFACT_INDICES = (31, 32, 33, 98, 114)
_REQUIRED_FORBIDDEN = {
    "missing_ocr_cell_as_dash_without_pixel_evidence",
    "template_labels_as_row_reconstruction_input",
    "approved_report_norm_id_assignment",
    "historical_or_mongodb_values",
    "human_review_answers",
    "dash_as_zero",
    "accounting_equations_as_value_imputation",
    "tiny_ocr_glyph_as_numeric_without_full_height_geometry",
    "page58_values_as_page57_mapping_or_imputation",
}


@dataclass(frozen=True)
class TMPage57AxisSpec:
    axis_key: str
    canonical_label: str
    header_lines: tuple[tuple[str, ...], ...]
    right_edge: float


@dataclass(frozen=True)
class TMPage57RowSpec:
    source_role: str
    metric_key: str | None
    row_kind: TMNoteRowKind
    label_lines: tuple[tuple[str, ...], ...]
    dash_axes: tuple[str, ...]
    dash_anchor_offset_line_heights: float


@dataclass(frozen=True)
class TMPage57Policy:
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
    period_role: str
    period_type: str
    visible_date: date
    period_start: date
    period_end: date
    table_key: str
    title_anchors: tuple[str, ...]
    super_header_anchors: tuple[str, ...]
    axes: tuple[TMPage57AxisSpec, ...]
    rows: tuple[TMPage57RowSpec, ...]
    numeric_cluster_line_heights: float
    wrapped_label_max_gap_line_heights: float
    tiny_glyph_max_height_line_heights: float
    page_footer_top_ratio: float
    dash_config: dict[str, float | int]
    dash_config_path: Path
    page_57_closes_interest_rate_table: bool
    page_58_starts_topic: str
    forbidden_semantic_inputs: tuple[str, ...]


@dataclass(frozen=True)
class TMPage57AxisBinding:
    ordinal: int
    axis_key: str
    canonical_label: str
    axis_right_edge: float
    raw_header_text: str
    header_line_indices: tuple[int, ...]
    canonical_unit: str
    unit_multiplier: int
    period_role: str
    period_type: str
    period_start: date
    period_end: date
    header_bbox: BoundingBox
    unit_bbox: BoundingBox
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class TMPage57LogicalRow:
    row_id: str
    table_key: str
    ordinal: int
    row: ReaderRow
    row_kind: TMNoteRowKind
    source_role: str
    metric_key: str | None
    y_anchor: float
    label_bbox: BoundingBox
    value_bboxes: tuple[BoundingBox | None, ...]
    label_line_indices: tuple[int, ...]
    value_line_indices: tuple[tuple[int, ...], ...]
    visual_cell_evidence: tuple[VisualCellEvidence | None, ...]
    cell_period_starts: tuple[date | None, ...]
    cell_period_ends: tuple[date | None, ...]
    cell_period_roles: tuple[str | None, ...]
    cell_period_types: tuple[str | None, ...]
    mapping_approved: bool

    @property
    def financial_slot_count(self) -> int:
        return len(self.row.cells) if self.row_kind is TMNoteRowKind.NUMERIC else 0


@dataclass(frozen=True)
class TMPage57Table:
    ordinal: int
    table_key: str
    title: str
    title_line_indices: tuple[int, ...]
    axes: tuple[TMPage57AxisBinding, ...]
    rows: tuple[TMPage57LogicalRow, ...]
    bbox: BoundingBox


@dataclass(frozen=True)
class ParsedTMPage57:
    input_path: str
    source_sha256: str
    upstream_ocr_sha256: str
    source_render_sha256: str
    source_pdf_sha256: str
    page_tag: str
    scope: str
    scope_binding: str
    table: TMPage57Table
    tables: tuple[TMPage57Table, ...]
    axes: tuple[TMPage57AxisBinding, ...]
    rows: tuple[TMPage57LogicalRow, ...]
    line_height: float
    source_ocr_bbox: BoundingBox
    table_bbox: BoundingBox
    unassigned_numeric_line_indices: tuple[int, ...]
    excluded_artifact_line_indices: tuple[int, ...]
    excluded_footer_numeric_line_indices: tuple[int, ...]
    continues_to_page_58: bool
    next_page_topic: str
    mapping_authority: bool
    evidence: tuple[str, ...]

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


def _anchors(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise TMNoteWordBoxError(f"TM page-57 {field} anchors are invalid")
    result = tuple(retrieval_key(str(item)) for item in value)
    if any(not item for item in result):
        raise TMNoteWordBoxError(f"TM page-57 {field} contains an empty anchor")
    return result


def _anchor_groups(value: Any, field: str) -> tuple[tuple[str, ...], ...]:
    if not isinstance(value, list) or not value:
        raise TMNoteWordBoxError(f"TM page-57 {field} groups are invalid")
    return tuple(_anchors(group, f"{field} line") for group in value)


def _date_value(payload: dict[str, Any], field: str) -> date:
    value = payload.get(field)
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise TMNoteWordBoxError(f"invalid TM page-57 {field}") from exc
    raise TMNoteWordBoxError(f"invalid TM page-57 {field}")


def _positive(payload: dict[str, Any], field: str, *, upper: float | None = None) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise TMNoteWordBoxError(f"invalid positive TM page-57 setting: {field}")
    result = float(value)
    if upper is not None and result >= upper:
        raise TMNoteWordBoxError(f"TM page-57 {field} must be below {upper}")
    return result


def load_tm_page57_policy(path: Path) -> TMPage57Policy:
    """Load the immutable source-scoped page-57 reconstruction contract."""

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMNoteWordBoxError(f"cannot load TM page-57 policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE57_INTEREST_RATE_RISK_FIXED_GRID_DASH_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 57
        or payload.get("page_tag") != "page-0057"
        or payload.get("scope") != "CONSOLIDATED"
    ):
        raise TMNoteWordBoxError("TM page-57 policy identity drifted")
    hash_fields = (
        "source_pdf_sha256",
        "source_render_sha256",
        "source_ocr_sha256",
        "upstream_ocr_sha256",
    )
    hashes = tuple(payload.get(field) for field in hash_fields)
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMNoteWordBoxError("TM page-57 source hashes are invalid")
    thresholds = tuple(
        payload.get(field)
        for field in ("minimum_line_score", "minimum_anchor_similarity", "minimum_unit_similarity")
    )
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1
        for value in thresholds
    ):
        raise TMNoteWordBoxError("TM page-57 similarity thresholds are invalid")
    unit = payload.get("unit")
    reporting = payload.get("reporting_period")
    table = payload.get("table")
    geometry = payload.get("geometry")
    continuation = payload.get("continuation")
    if not all(isinstance(item, dict) for item in (unit, reporting, table, geometry, continuation)):
        raise TMNoteWordBoxError("TM page-57 unit/period/table policy is incomplete")
    canonical_unit = unit.get("canonical")
    multiplier = unit.get("multiplier")
    if (
        not isinstance(canonical_unit, str)
        or not canonical_unit
        or isinstance(multiplier, bool)
        or not isinstance(multiplier, int)
        or multiplier <= 0
    ):
        raise TMNoteWordBoxError("TM page-57 unit binding is invalid")
    if reporting.get("period_role") != "CURRENT" or reporting.get("period_type") != "SNAPSHOT":
        raise TMNoteWordBoxError("TM page-57 period role/type drifted")
    visible_date = _date_value(reporting, "visible_date")
    period_start = _date_value(reporting, "period_start")
    period_end = _date_value(reporting, "period_end")
    if (
        visible_date != period_start
        or visible_date != period_end
        or visible_date != date(2026, 3, 31)
    ):
        raise TMNoteWordBoxError("TM page-57 snapshot date drifted")

    raw_axes = payload.get("axes")
    if not isinstance(raw_axes, list) or len(raw_axes) != 8:
        raise TMNoteWordBoxError("TM page-57 must define eight axes")
    axes = []
    for record in raw_axes:
        if not isinstance(record, dict):
            raise TMNoteWordBoxError("TM page-57 axis is invalid")
        right_edge = record.get("right_edge")
        if isinstance(right_edge, bool) or not isinstance(right_edge, (int, float)):
            raise TMNoteWordBoxError("TM page-57 axis edge is invalid")
        axes.append(
            TMPage57AxisSpec(
                axis_key=str(record.get("axis_key", "")),
                canonical_label=str(record.get("canonical_label", "")),
                header_lines=_anchor_groups(record.get("header_lines"), "axis header"),
                right_edge=float(right_edge),
            )
        )
    if (
        tuple(item.axis_key for item in axes) != _AXIS_KEYS
        or tuple(item.right_edge for item in axes) != _AXIS_RIGHT_EDGES
    ):
        raise TMNoteWordBoxError("TM page-57 axis order/geometry drifted")

    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, list) or len(raw_rows) != 22:
        raise TMNoteWordBoxError("TM page-57 row policy denominator drifted")
    rows = []
    for record in raw_rows:
        if not isinstance(record, dict):
            raise TMNoteWordBoxError("TM page-57 row policy is invalid")
        try:
            row_kind = TMNoteRowKind(str(record.get("row_kind")))
        except ValueError as exc:
            raise TMNoteWordBoxError("TM page-57 row kind is invalid") from exc
        metric_key = record.get("metric_key")
        dash_axes = record.get("dash_axes")
        offset = record.get("dash_anchor_offset_line_heights", 0.0)
        if (
            metric_key is not None
            and (not isinstance(metric_key, str) or not metric_key)
            or not isinstance(dash_axes, list)
            or any(item not in _AXIS_KEYS for item in dash_axes)
            or len(set(dash_axes)) != len(dash_axes)
            or isinstance(offset, bool)
            or not isinstance(offset, (int, float))
            or offset < 0
        ):
            raise TMNoteWordBoxError("TM page-57 row fields are invalid")
        rows.append(
            TMPage57RowSpec(
                source_role=str(record.get("source_role", "")),
                metric_key=metric_key,
                row_kind=row_kind,
                label_lines=_anchor_groups(record.get("label_lines"), "row label"),
                dash_axes=tuple(str(item) for item in dash_axes),
                dash_anchor_offset_line_heights=float(offset),
            )
        )
    if (
        tuple(row.metric_key for row in rows if row.metric_key is not None)
        != (_EXPECTED_METRIC_KEYS)
        or sum(row.row_kind is TMNoteRowKind.LABEL_ONLY for row in rows) != 2
    ):
        raise TMNoteWordBoxError("TM page-57 metric/structural row order drifted")
    if sum(len(row.dash_axes) for row in rows) != 68:
        raise TMNoteWordBoxError("TM page-57 dash denominator drifted")

    dash_name = payload.get("dash_detector_config")
    if not isinstance(dash_name, str) or Path(dash_name).name != dash_name:
        raise TMNoteWordBoxError("TM page-57 dash-detector path is invalid")
    dash_path = (path.parent / dash_name).resolve()
    if not dash_path.is_file() or sha256_file(dash_path) != payload.get(
        "dash_detector_config_sha256"
    ):
        raise TMNoteWordBoxError("TM page-57 dash detector is absent or drifted")
    forbidden = payload.get("forbidden_semantic_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMNoteWordBoxError("TM page-57 forbidden semantic inputs drifted")
    if (
        table.get("table_key") != "INTEREST_RATE_RISK"
        or table.get("expected_structural_rows") != 2
        or table.get("expected_numeric_rows") != 20
        or continuation.get("page_57_closes_interest_rate_table") is not True
        or continuation.get("page_58_starts_topic") != "CURRENCY_RISK"
    ):
        raise TMNoteWordBoxError("TM page-57 table/continuation contract drifted")
    return TMPage57Policy(
        source_path=path,
        document=str(payload.get("document", "")),
        page_number=57,
        page_tag="page-0057",
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
        period_role="CURRENT",
        period_type="SNAPSHOT",
        visible_date=visible_date,
        period_start=period_start,
        period_end=period_end,
        table_key="INTEREST_RATE_RISK",
        title_anchors=_anchors(table.get("title_anchors"), "title"),
        super_header_anchors=_anchors(table.get("super_header_anchors"), "super header"),
        axes=tuple(axes),
        rows=tuple(rows),
        numeric_cluster_line_heights=_positive(geometry, "numeric_cluster_line_heights"),
        wrapped_label_max_gap_line_heights=_positive(
            geometry, "wrapped_label_max_gap_line_heights"
        ),
        tiny_glyph_max_height_line_heights=_positive(
            geometry, "tiny_glyph_max_height_line_heights", upper=1
        ),
        page_footer_top_ratio=_positive(geometry, "page_footer_top_ratio", upper=1),
        dash_config={
            str(key): value
            for key, value in load_word_box_reconstruction_v3_config(dash_path).base.base.items()
        },
        dash_config_path=dash_path,
        page_57_closes_interest_rate_table=True,
        page_58_starts_topic="CURRENCY_RISK",
        forbidden_semantic_inputs=tuple(str(item) for item in forbidden),
    )


def _find_anchor_line(
    lines: tuple[_Line, ...],
    anchors: tuple[str, ...],
    policy: TMPage57Policy,
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
        raise TMNoteWordBoxError(f"TM page-57 anchor is unresolved: {anchors}")
    return candidates[0][1]


def _find_anchor_group(
    lines: tuple[_Line, ...],
    anchors: tuple[tuple[str, ...], ...],
    policy: TMPage57Policy,
    line_height: float,
    *,
    minimum_y: float,
    maximum_y: float,
) -> tuple[_Line, ...]:
    choices = tuple(
        tuple(
            (line, _best_anchor_similarity(line.text, group))
            for line in lines
            if minimum_y < line.y_center < maximum_y
            and _best_anchor_similarity(line.text, group) >= policy.minimum_anchor_similarity
        )
        for group in anchors
    )
    if any(not group for group in choices):
        raise TMNoteWordBoxError(f"TM page-57 wrapped label is unresolved: {anchors}")
    candidates = []
    for combination in itertools.product(*choices):
        group = tuple(record[0] for record in combination)
        if len({line.index for line in group}) != len(group):
            continue
        if tuple(line.y_center for line in group) != tuple(sorted(line.y_center for line in group)):
            continue
        if any(
            right.y_center - left.y_center > line_height * policy.wrapped_label_max_gap_line_heights
            for left, right in zip(group[:-1], group[1:], strict=True)
        ):
            continue
        candidates.append(
            (
                -sum(record[1] for record in combination),
                group[-1].y_center - group[0].y_center,
                group[0].y_center,
                group,
            )
        )
    if not candidates:
        raise TMNoteWordBoxError("TM page-57 wrapped label lines are not locally adjacent")
    return min(candidates, key=lambda record: record[:3])[3]


def _axis_bindings(
    lines: tuple[_Line, ...],
    title: _Line,
    super_header: _Line,
    unit: _Line,
    first_body_y: float,
    policy: TMPage57Policy,
    line_height: float,
) -> tuple[TMPage57AxisBinding, ...]:
    results = []
    for ordinal, spec in enumerate(policy.axes, start=1):
        header = _find_anchor_group(
            lines,
            spec.header_lines,
            policy,
            line_height,
            minimum_y=title.y_center,
            maximum_y=first_body_y,
        )
        if abs(header[-1].x_right - spec.right_edge) > line_height * 3.0:
            raise TMNoteWordBoxError(f"TM page-57 header/grid edge drifted: {spec.axis_key}")
        results.append(
            TMPage57AxisBinding(
                ordinal=ordinal,
                axis_key=spec.axis_key,
                canonical_label=spec.canonical_label,
                axis_right_edge=spec.right_edge,
                raw_header_text=normalize_text(" ".join(line.text for line in header)),
                header_line_indices=tuple(line.index for line in header),
                canonical_unit=policy.canonical_unit,
                unit_multiplier=policy.unit_multiplier,
                period_role=policy.period_role,
                period_type=policy.period_type,
                period_start=policy.period_start,
                period_end=policy.period_end,
                header_bbox=_union(list(header)),
                unit_bbox=unit.bbox,
                evidence=(
                    "axis label matched only from the visible page-57 table header",
                    "right edge is the fixed visible eight-column numeric grid",
                    "snapshot date parsed from the visible introductory sentence",
                    "VND million multiplier matched from the visible table-local unit",
                    f"table super-header source line {super_header.index}",
                ),
            )
        )
    return tuple(results)


def _logical_row(
    *,
    page_tag: str,
    table_key: str,
    ordinal: int,
    spec: TMPage57RowSpec,
    label_lines: tuple[_Line, ...],
    value_lines: tuple[tuple[_Line, ...], ...],
    visual: tuple[VisualCellEvidence | None, ...],
    axes: tuple[TMPage57AxisBinding, ...],
    y_anchor: float,
) -> TMPage57LogicalRow:
    cells = tuple(
        parse_financial_number(
            "-" if evidence is not None and not items else " ".join(line.text for line in items)
        )
        for items, evidence in zip(value_lines, visual, strict=True)
    )
    sources = [*label_lines, *(line for group in value_lines for line in group)]
    numeric = spec.row_kind is TMNoteRowKind.NUMERIC
    return TMPage57LogicalRow(
        row_id=f"{page_tag}:{table_key.lower()}:row-{ordinal:04d}",
        table_key=table_key,
        ordinal=ordinal,
        row=ReaderRow(
            source_row_ids=_source_ids(page_tag, sources),
            label=normalize_text(" ".join(line.text for line in label_lines)),
            note_reference="",
            cells=cells,
        ),
        row_kind=spec.row_kind,
        source_role=spec.source_role,
        metric_key=spec.metric_key,
        y_anchor=y_anchor,
        label_bbox=_union(list(label_lines)),
        value_bboxes=tuple(
            _union(list(items))
            if items
            else BoundingBox(*evidence.component_box)
            if evidence is not None
            else None
            for items, evidence in zip(value_lines, visual, strict=True)
        ),
        label_line_indices=tuple(line.index for line in label_lines),
        value_line_indices=tuple(tuple(line.index for line in items) for items in value_lines),
        visual_cell_evidence=visual,
        cell_period_starts=tuple(axis.period_start if numeric else None for axis in axes),
        cell_period_ends=tuple(axis.period_end if numeric else None for axis in axes),
        cell_period_roles=tuple(axis.period_role if numeric else None for axis in axes),
        cell_period_types=tuple(axis.period_type if numeric else None for axis in axes),
        mapping_approved=False,
    )


def parse_tm_page57(
    result_path: Path,
    source_image_path: Path,
    policy: TMPage57Policy,
    *,
    page_tag: str = "page-0057",
) -> ParsedTMPage57:
    """Reconstruct the complete page-57 table with mapping authority disabled."""

    if page_tag != policy.page_tag:
        raise TMNoteWordBoxError("TM page-57 page tag drifted")
    if sha256_file(result_path) != policy.source_ocr_sha256:
        raise TMNoteWordBoxError("TM page-57 compact OCR fixture hash drifted")
    if sha256_file(source_image_path) != policy.source_render_sha256:
        raise TMNoteWordBoxError("TM page-57 source render hash drifted")
    source_image = cv2.imread(str(source_image_path), cv2.IMREAD_GRAYSCALE)
    if source_image is None:
        raise TMNoteWordBoxError("TM page-57 source render cannot be decoded")
    input_path, lines, metadata = _load_lines(result_path, policy.minimum_line_score)
    if metadata != {
        "upstream_ocr_sha256": policy.upstream_ocr_sha256,
        "source_render_sha256": policy.source_render_sha256,
        "source_pdf_sha256": policy.source_pdf_sha256,
    }:
        raise TMNoteWordBoxError("TM page-57 compact OCR provenance drifted")
    line_height = float(statistics.median(line.height for line in lines))
    if line_height <= 0:
        raise TMNoteWordBoxError("TM page-57 line height is invalid")
    source_bbox = _union(lines)
    footer_top = source_bbox.y1 * policy.page_footer_top_ratio

    title = _find_anchor_line(lines, policy.title_anchors, policy, maximum_y=footer_top)
    super_header = _find_anchor_line(
        lines,
        policy.super_header_anchors,
        policy,
        minimum_y=title.y_center,
        maximum_y=footer_top,
    )
    if parse_vietnamese_date(title.text) != policy.visible_date:
        raise TMNoteWordBoxError("TM page-57 visible snapshot date drifted")
    unit_candidates = tuple(
        line
        for line in lines
        if title.y_center < line.y_center < 500
        and _best_anchor_similarity(line.text, policy.unit_anchors)
        >= policy.minimum_unit_similarity
    )
    if len(unit_candidates) != 1:
        raise TMNoteWordBoxError("TM page-57 visible unit denominator drifted")
    unit = unit_candidates[0]

    labels = []
    minimum_y = super_header.y_center
    for spec in policy.rows:
        group = _find_anchor_group(
            lines,
            spec.label_lines,
            policy,
            line_height,
            minimum_y=minimum_y,
            maximum_y=footer_top,
        )
        labels.append(group)
        minimum_y = max(line.y_center for line in group)
    if tuple(min(line.y_center for line in group) for group in labels) != tuple(
        sorted(min(line.y_center for line in group) for group in labels)
    ):
        raise TMNoteWordBoxError("TM page-57 source row order drifted")
    axes = _axis_bindings(
        lines,
        title,
        super_header,
        unit,
        min(line.bbox.y0 for line in labels[0]),
        policy,
        line_height,
    )

    artifact_lines = tuple(
        line
        for line in lines
        if len(retrieval_key(line.text)) <= 1
        and line.height < line_height * policy.tiny_glyph_max_height_line_heights
    )
    artifact_indices = tuple(sorted(line.index for line in artifact_lines))
    if artifact_indices != _EXPECTED_ARTIFACT_INDICES:
        raise TMNoteWordBoxError(f"TM page-57 tiny OCR artifact set drifted: {artifact_indices}")
    first_numeric_y = min(line.y_center for line in labels[1]) - line_height
    last_numeric_y = max(line.y_center for line in labels[-1]) + line_height
    numeric_lines = tuple(
        line
        for line in lines
        if first_numeric_y < line.y_center < last_numeric_y
        and line.index not in artifact_indices
        and _numeric_only(line.text)
    )
    numeric_groups = tuple(
        tuple(group)
        for group in _clusters(
            numeric_lines,
            line_height * policy.numeric_cluster_line_heights,
        )
    )
    if len(numeric_groups) != 19 or tuple(len(group) for group in numeric_groups) != (
        _EXPECTED_NUMERIC_GROUP_SIZES
    ):
        raise TMNoteWordBoxError(
            "TM page-57 numeric group denominator drifted: "
            f"{tuple(len(group) for group in numeric_groups)}"
        )

    rows = []
    group_index = 0
    used_numeric: set[int] = set()
    for ordinal, (spec, label_lines) in enumerate(zip(policy.rows, labels, strict=True), start=1):
        if spec.row_kind is TMNoteRowKind.LABEL_ONLY:
            value_lines = tuple(() for _ in axes)
            visual = tuple(None for _ in axes)
            y_anchor = statistics.fmean(line.y_center for line in label_lines)
        else:
            all_dash = len(spec.dash_axes) == len(axes)
            if all_dash:
                group: tuple[_Line, ...] = ()
                y_anchor = statistics.fmean(line.y_center for line in label_lines) + (
                    line_height * spec.dash_anchor_offset_line_heights
                )
            else:
                group = numeric_groups[group_index]
                group_index += 1
                y_anchor = statistics.fmean(line.y_center for line in group)
            per_axis: list[list[_Line]] = [[] for _ in axes]
            for line in group:
                distances = [abs(axis.axis_right_edge - line.x_right) for axis in axes]
                axis_index = min(range(len(axes)), key=distances.__getitem__)
                if distances[axis_index] > line_height * 1.5 or per_axis[axis_index]:
                    raise TMNoteWordBoxError("TM page-57 numeric cell geometry drifted")
                per_axis[axis_index].append(line)
                used_numeric.add(line.index)
            expected_value_axes = {
                axis.axis_key for axis in axes if axis.axis_key not in spec.dash_axes
            }
            observed_value_axes = {
                axes[index].axis_key for index, items in enumerate(per_axis) if items
            }
            if observed_value_axes != expected_value_axes:
                raise TMNoteWordBoxError(
                    f"TM page-57 row value/dash partition drifted: {spec.metric_key}"
                )
            visual_list: list[VisualCellEvidence | None] = [None for _ in axes]
            for index, axis in enumerate(axes):
                if axis.axis_key not in spec.dash_axes:
                    continue
                evidence = _detect_visible_dash_v3(
                    source_image,
                    source_image_path=source_image_path,
                    axis_right_edge=axis.axis_right_edge,
                    anchor_center=y_anchor,
                    line_height=line_height,
                    config=policy.dash_config,
                )
                if evidence is None:
                    raise TMNoteWordBoxError(
                        "TM page-57 visible dash lacks constrained pixel evidence: "
                        f"{spec.metric_key}/{axis.axis_key}"
                    )
                visual_list[index] = evidence
            value_lines = tuple(tuple(items) for items in per_axis)
            visual = tuple(visual_list)
        logical = _logical_row(
            page_tag=page_tag,
            table_key=policy.table_key,
            ordinal=ordinal,
            spec=spec,
            label_lines=label_lines,
            value_lines=value_lines,
            visual=visual,
            axes=axes,
            y_anchor=y_anchor,
        )
        if spec.row_kind is TMNoteRowKind.NUMERIC and any(
            cell.observation
            not in {ObservationKind.VALUE, ObservationKind.ZERO, ObservationKind.DASH}
            for cell in logical.row.cells
        ):
            raise TMNoteWordBoxError(
                f"TM page-57 row contains an unresolved cell: {spec.metric_key}"
            )
        rows.append(logical)
    if group_index != len(numeric_groups):
        raise TMNoteWordBoxError("TM page-57 numeric groups were not consumed exactly once")

    rows_tuple = tuple(rows)
    relevant_numeric = {line.index for line in numeric_lines}
    footer_numeric = tuple(
        sorted(
            line.index for line in lines if line.y_center >= footer_top and _numeric_only(line.text)
        )
    )
    table_source_lines = tuple(
        line for line in lines if title.bbox.y0 <= line.y_center <= rows_tuple[-1].label_bbox.y1
    )
    title_indices = tuple(
        dict.fromkeys(
            (
                title.index,
                super_header.index,
                unit.index,
                *(index for axis in axes for index in axis.header_line_indices),
            )
        )
    )
    table = TMPage57Table(
        ordinal=1,
        table_key=policy.table_key,
        title=normalize_text(title.text),
        title_line_indices=title_indices,
        axes=axes,
        rows=rows_tuple,
        bbox=_union(table_source_lines),
    )
    result = ParsedTMPage57(
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
        axes=axes,
        rows=rows_tuple,
        line_height=line_height,
        source_ocr_bbox=source_bbox,
        table_bbox=table.bbox,
        unassigned_numeric_line_indices=tuple(sorted(relevant_numeric - used_numeric)),
        excluded_artifact_line_indices=artifact_indices,
        excluded_footer_numeric_line_indices=footer_numeric,
        continues_to_page_58=not policy.page_57_closes_interest_rate_table,
        next_page_topic=policy.page_58_starts_topic,
        mapping_authority=False,
        evidence=(
            "one complete page-57 interest-rate-risk table reconstructed from immutable PP-OCRv6 geometry",
            "eight visible repricing axes use one fixed source-derived numeric grid",
            "20 numeric rows and two structural rows preserve source order and hierarchy",
            "92 finite values and 68 pixel-backed dashes preserve all 160 financial slots",
            "five tiny OCR glyph artifacts at printed dash locations are rejected by height geometry",
            "all cells bind to the 2026-03-31 consolidated VND-million snapshot",
            "equations are reserved for post-mapping validation and mapping authority remains false",
            "page 57 closes the table; page 58 begins independently owned currency-risk content",
        ),
    )
    if (
        len(result.rows) != 22
        or result.numeric_row_count != 20
        or result.label_only_row_count != 2
        or result.financial_slot_count != 160
        or result.observation_count(ObservationKind.VALUE) != 92
        or result.observation_count(ObservationKind.ZERO) != 0
        or result.observation_count(ObservationKind.DASH) != 68
        or result.observation_count(ObservationKind.BLANK) != 0
        or result.unassigned_numeric_line_indices
        or result.excluded_artifact_line_indices != _EXPECTED_ARTIFACT_INDICES
        or result.excluded_footer_numeric_line_indices != (137,)
        or result.continues_to_page_58
        or result.next_page_topic != "CURRENCY_RISK"
    ):
        raise TMNoteWordBoxError(
            "TM page-57 exact source denominator drifted: "
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
    "ParsedTMPage57",
    "TMPage57AxisBinding",
    "TMPage57LogicalRow",
    "TMPage57Policy",
    "TMPage57Table",
    "load_tm_page57_policy",
    "parse_tm_page57",
]
