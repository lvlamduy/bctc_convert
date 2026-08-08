"""Fixed-source multi-axis TM reconstruction for MBB consolidated PDF page 43."""

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
    _bind_page31_axes,
    _clusters,
    _Line,
    _load_lines,
    _numeric_only,
    _source_ids,
    _union,
)
from bctc_ai.validation.reader_agreement import ReaderRow

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_FORBIDDEN = {
    "missing_ocr_cell_as_dash_without_pixel_evidence",
    "template_labels_as_row_reconstruction_input",
    "approved_report_norm_id_assignment",
    "historical_or_mongodb_values",
    "human_review_answers",
    "dash_as_zero",
    "accounting_equations_as_value_imputation",
}


@dataclass(frozen=True)
class TMPage43TableSpec:
    table_key: str
    note_number: str
    title_anchors: tuple[str, ...]
    note_title_anchors: tuple[str, ...]
    body_end_anchors: tuple[str, ...]
    expected_numeric_rows: int
    expected_label_only_rows: int


@dataclass(frozen=True)
class TMPage43MeasureSpec:
    column_role: str
    anchors: tuple[str, ...]


@dataclass(frozen=True)
class TMPage43Policy:
    source_path: Path
    document: str
    page_number: int
    page_tag: str
    scope: str
    scope_binding: str
    source_pdf_sha256: str
    source_render_sha256: str
    source_ocr_sha256: str
    minimum_line_score: float
    minimum_anchor_similarity: float
    minimum_unit_similarity: float
    unit_anchors: tuple[str, ...]
    canonical_unit: str
    unit_multiplier: int
    maximum_date_to_unit_center_distance_line_heights: float
    minimum_axis_separation_line_heights: float
    numeric_axis_max_distance_ratio: float
    numeric_axis_right_overrun_line_heights: float
    row_anchor_cluster_line_heights: float
    label_direct_attach_line_heights: float
    note_reference_left_gap_axis_widths: float
    page_footer_top_ratio: float
    dash_config: dict[str, float | int]
    dash_config_path: Path
    tables: tuple[TMPage43TableSpec, ...]
    measure_specs: tuple[TMPage43MeasureSpec, ...]
    current_period_anchors: tuple[str, ...]
    comparative_period_anchors: tuple[str, ...]
    expected_current_period: date
    expected_comparative_period: date
    forbidden_semantic_inputs: tuple[str, ...]


@dataclass(frozen=True)
class TMPage43AxisBinding:
    ordinal: int
    axis_id: str
    column_role: str
    measure_role: str
    axis_right_edge: float
    raw_period_text: str
    date_line_index: int | None
    raw_unit_text: str
    unit_line_index: int
    current_or_comparative: str | None
    canonical_unit: str
    unit_multiplier: int
    period_start: date | None
    period_end: date | None
    period_type: str
    header_bbox: BoundingBox
    unit_bbox: BoundingBox
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class TMPage43LogicalRow:
    row_id: str
    table_key: str
    note_number: str
    ordinal: int
    row: ReaderRow
    row_kind: TMNoteRowKind
    source_role: str
    y_anchor: float
    label_bbox: BoundingBox | None
    value_bboxes: tuple[BoundingBox | None, ...]
    label_line_indices: tuple[int, ...]
    value_line_indices: tuple[tuple[int, ...], ...]
    visual_cell_evidence: tuple[VisualCellEvidence | None, ...]
    cell_period_ends: tuple[date | None, ...]
    cell_period_roles: tuple[str | None, ...]
    cell_measure_roles: tuple[str, ...]
    mapping_approved: bool

    @property
    def financial_slot_count(self) -> int:
        return len(self.row.cells) if self.row_kind is TMNoteRowKind.NUMERIC else 0


@dataclass(frozen=True)
class TMPage43Table:
    ordinal: int
    table_key: str
    note_number: str
    title: str
    title_line_indices: tuple[int, ...]
    axes: tuple[TMPage43AxisBinding, ...]
    rows: tuple[TMPage43LogicalRow, ...]
    bbox: BoundingBox


@dataclass(frozen=True)
class ParsedTMPage43:
    input_path: str
    source_sha256: str
    source_render_sha256: str
    source_pdf_sha256: str
    page_tag: str
    scope: str
    scope_binding: str
    axes: tuple[TMPage43AxisBinding, ...]
    tables: tuple[TMPage43Table, ...]
    rows: tuple[TMPage43LogicalRow, ...]
    line_height: float
    source_ocr_bbox: BoundingBox
    table_bbox: BoundingBox
    unassigned_numeric_line_indices: tuple[int, ...]
    excluded_footer_numeric_line_indices: tuple[int, ...]
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


def _anchors(payload: Any, field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(payload, list) or (not payload and not allow_empty):
        raise TMNoteWordBoxError(f"TM page-43 {field} anchors are invalid")
    result = tuple(retrieval_key(str(value)) for value in payload)
    if any(not value for value in result):
        raise TMNoteWordBoxError(f"TM page-43 {field} contains an empty anchor")
    return result


def _positive(payload: dict[str, Any], field: str) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise TMNoteWordBoxError(f"invalid positive TM page-43 setting: {field}")
    return float(value)


def load_tm_page43_policy(path: Path) -> TMPage43Policy:
    """Load the hash-bound page-43 geometry and status policy."""

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMNoteWordBoxError(f"cannot load TM page-43 policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE43_MULTI_AXIS_FIXED_GRID_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 43
        or payload.get("page_tag") != "page-0043"
        or payload.get("scope") != "CONSOLIDATED"
    ):
        raise TMNoteWordBoxError("TM page-43 policy identity drifted")
    hashes = (
        payload.get("source_pdf_sha256"),
        payload.get("source_render_sha256"),
        payload.get("source_ocr_sha256"),
    )
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMNoteWordBoxError("TM page-43 source hashes are invalid")
    thresholds = (
        payload.get("minimum_line_score"),
        payload.get("minimum_anchor_similarity"),
        payload.get("minimum_unit_similarity"),
    )
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= float(value) <= 1
        for value in thresholds
    ):
        raise TMNoteWordBoxError("TM page-43 similarity thresholds are invalid")
    unit = payload.get("unit")
    header = payload.get("header_geometry")
    geometry = payload.get("table_geometry")
    derivative = payload.get("derivative_geometry")
    if not all(isinstance(value, dict) for value in (unit, header, geometry, derivative)):
        raise TMNoteWordBoxError("TM page-43 geometry policy is incomplete")
    multiplier = unit.get("multiplier")
    canonical_unit = unit.get("canonical")
    if (
        isinstance(multiplier, bool)
        or not isinstance(multiplier, int)
        or multiplier <= 0
        or not isinstance(canonical_unit, str)
        or not canonical_unit
    ):
        raise TMNoteWordBoxError("TM page-43 unit binding is invalid")
    dash_name = payload.get("dash_detector_config")
    if not isinstance(dash_name, str) or Path(dash_name).name != dash_name:
        raise TMNoteWordBoxError("TM page-43 dash detector path is invalid")
    dash_path = (path.parent / dash_name).resolve()
    if not dash_path.is_file() or sha256_file(dash_path) != payload.get(
        "dash_detector_config_sha256"
    ):
        raise TMNoteWordBoxError("TM page-43 dash detector is absent or drifted")
    dash_config = load_word_box_reconstruction_v3_config(dash_path).base.base

    raw_tables = payload.get("tables")
    if not isinstance(raw_tables, list) or len(raw_tables) != 4:
        raise TMNoteWordBoxError("TM page-43 must define four visible tables")
    tables = []
    for record in raw_tables:
        if not isinstance(record, dict):
            raise TMNoteWordBoxError("TM page-43 table record is invalid")
        numeric_rows = record.get("expected_numeric_rows")
        label_rows = record.get("expected_label_only_rows")
        table_key = record.get("table_key")
        note_number = record.get("note_number")
        if (
            not isinstance(table_key, str)
            or not table_key
            or not isinstance(note_number, str)
            or not note_number
            or isinstance(numeric_rows, bool)
            or not isinstance(numeric_rows, int)
            or numeric_rows <= 0
            or isinstance(label_rows, bool)
            or not isinstance(label_rows, int)
            or label_rows <= 0
        ):
            raise TMNoteWordBoxError("TM page-43 table denominator is invalid")
        tables.append(
            TMPage43TableSpec(
                table_key=table_key,
                note_number=note_number,
                title_anchors=_anchors(record.get("title_anchors"), f"{table_key} title"),
                note_title_anchors=_anchors(
                    record.get("note_title_anchors", []),
                    f"{table_key} note title",
                    allow_empty=True,
                ),
                body_end_anchors=_anchors(
                    record.get("body_end_anchors", []),
                    f"{table_key} body end",
                    allow_empty=True,
                ),
                expected_numeric_rows=numeric_rows,
                expected_label_only_rows=label_rows,
            )
        )
    expected_keys = ("DEPOSIT_TYPE", "DEPOSIT_CUSTOMER", "DERIVATIVES", "TRUST_FUNDING")
    if tuple(table.table_key for table in tables) != expected_keys:
        raise TMNoteWordBoxError("TM page-43 table order drifted")

    raw_measures = derivative.get("measure_header_anchors")
    if not isinstance(raw_measures, list) or len(raw_measures) != 3:
        raise TMNoteWordBoxError("TM page-43 derivative measures are invalid")
    measures = []
    for record in raw_measures:
        if not isinstance(record, dict) or not isinstance(record.get("column_role"), str):
            raise TMNoteWordBoxError("TM page-43 derivative measure record is invalid")
        measures.append(
            TMPage43MeasureSpec(
                column_role=record["column_role"],
                anchors=_anchors(record.get("anchors"), "derivative measure"),
            )
        )
    if tuple(item.column_role for item in measures) != (
        "ASSET_CARRYING",
        "LIABILITY_CARRYING",
        "NET_CARRYING",
    ):
        raise TMNoteWordBoxError("TM page-43 derivative measure order drifted")
    try:
        expected_current = date.fromisoformat(str(derivative.get("expected_current_period")))
        expected_comparative = date.fromisoformat(
            str(derivative.get("expected_comparative_period"))
        )
    except ValueError as exc:
        raise TMNoteWordBoxError("TM page-43 derivative periods are invalid") from exc
    forbidden = payload.get("forbidden_semantic_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMNoteWordBoxError("TM page-43 forbidden semantic inputs drifted")
    footer_ratio = _positive(geometry, "page_footer_top_ratio")
    if footer_ratio >= 1:
        raise TMNoteWordBoxError("TM page-43 footer ratio must be below one")
    return TMPage43Policy(
        source_path=path,
        document=str(payload.get("document", "")),
        page_number=43,
        page_tag="page-0043",
        scope="CONSOLIDATED",
        scope_binding=str(payload.get("scope_binding", "")),
        source_pdf_sha256=hashes[0],
        source_render_sha256=hashes[1],
        source_ocr_sha256=hashes[2],
        minimum_line_score=float(thresholds[0]),
        minimum_anchor_similarity=float(thresholds[1]),
        minimum_unit_similarity=float(thresholds[2]),
        unit_anchors=_anchors(unit.get("anchors"), "unit"),
        canonical_unit=canonical_unit,
        unit_multiplier=multiplier,
        maximum_date_to_unit_center_distance_line_heights=_positive(
            header, "maximum_date_to_unit_center_distance_line_heights"
        ),
        minimum_axis_separation_line_heights=_positive(
            header, "minimum_axis_separation_line_heights"
        ),
        numeric_axis_max_distance_ratio=_positive(geometry, "numeric_axis_max_distance_ratio"),
        numeric_axis_right_overrun_line_heights=_positive(
            geometry, "numeric_axis_right_overrun_line_heights"
        ),
        row_anchor_cluster_line_heights=_positive(geometry, "row_anchor_cluster_line_heights"),
        label_direct_attach_line_heights=_positive(geometry, "label_direct_attach_line_heights"),
        note_reference_left_gap_axis_widths=_positive(
            geometry, "note_reference_left_gap_axis_widths"
        ),
        page_footer_top_ratio=footer_ratio,
        dash_config={str(key): value for key, value in dash_config.items()},
        dash_config_path=dash_path,
        tables=tuple(tables),
        measure_specs=tuple(measures),
        current_period_anchors=_anchors(
            derivative.get("current_period_anchors"), "current derivative period"
        ),
        comparative_period_anchors=_anchors(
            derivative.get("comparative_period_anchors"), "comparative derivative period"
        ),
        expected_current_period=expected_current,
        expected_comparative_period=expected_comparative,
        forbidden_semantic_inputs=tuple(str(value) for value in forbidden),
    )


def _find_anchor_line(
    lines: tuple[_Line, ...],
    anchors: tuple[str, ...],
    policy: TMPage43Policy,
    *,
    y0: float = float("-inf"),
    y1: float = float("inf"),
    used: set[int] | None = None,
) -> _Line:
    candidates = sorted(
        (
            (_best_anchor_similarity(line.text, anchors), line)
            for line in lines
            if y0 < line.y_center < y1 and (used is None or line.index not in used)
        ),
        key=lambda item: (-item[0], item[1].y_center, item[1].index),
    )
    if not candidates or candidates[0][0] < policy.minimum_anchor_similarity:
        raise TMNoteWordBoxError(f"TM page-43 anchor is unresolved: {anchors}")
    return candidates[0][1]


def _note_number_line(
    lines: tuple[_Line, ...], note_number: str, title: _Line, line_height: float
) -> _Line:
    candidates = [
        line
        for line in lines
        if retrieval_key(line.text) == note_number
        and line.bbox.x1 < title.bbox.x0
        and abs(line.y_center - title.y_center) <= line_height
    ]
    if len(candidates) != 1:
        raise TMNoteWordBoxError(f"TM page-43 note {note_number} number anchor drifted")
    return candidates[0]


def _body_end(
    lines: tuple[_Line, ...],
    spec: TMPage43TableSpec,
    source_bbox: BoundingBox,
    policy: TMPage43Policy,
) -> float:
    if not spec.body_end_anchors:
        return source_bbox.y1 * policy.page_footer_top_ratio
    return _find_anchor_line(lines, spec.body_end_anchors, policy).bbox.y0


def _axis_from_period_axis(axis: Any) -> TMPage43AxisBinding:
    return TMPage43AxisBinding(
        ordinal=axis.ordinal,
        axis_id=axis.axis_id,
        column_role=axis.current_or_comparative,
        measure_role="BALANCE",
        axis_right_edge=axis.axis_right_edge,
        raw_period_text=axis.raw_date_text,
        date_line_index=axis.date_line_index,
        raw_unit_text=axis.raw_unit_text,
        unit_line_index=axis.unit_line_index,
        current_or_comparative=axis.current_or_comparative,
        canonical_unit=axis.canonical_unit,
        unit_multiplier=axis.unit_multiplier,
        period_start=axis.period_start,
        period_end=axis.period_end,
        period_type=axis.period_type,
        header_bbox=axis.header_bbox,
        unit_bbox=axis.unit_bbox,
        evidence=axis.evidence,
    )


def _structural_row(
    *,
    page_tag: str,
    table_key: str,
    note_number: str,
    label_lines: tuple[_Line, ...],
    source_lines: tuple[_Line, ...],
    width: int,
    source_role: str,
) -> TMPage43LogicalRow:
    center = statistics.fmean(line.y_center for line in label_lines)
    return TMPage43LogicalRow(
        row_id="",
        table_key=table_key,
        note_number=note_number,
        ordinal=0,
        row=ReaderRow(
            source_row_ids=_source_ids(page_tag, list(source_lines)),
            label=normalize_text(" ".join(line.text for line in label_lines)),
            note_reference=note_number,
            cells=tuple(parse_financial_number(None) for _ in range(width)),
        ),
        row_kind=TMNoteRowKind.LABEL_ONLY,
        source_role=source_role,
        y_anchor=center,
        label_bbox=_union(list(source_lines)),
        value_bboxes=tuple(None for _ in range(width)),
        label_line_indices=tuple(line.index for line in label_lines),
        value_line_indices=tuple(() for _ in range(width)),
        visual_cell_evidence=tuple(None for _ in range(width)),
        cell_period_ends=tuple(None for _ in range(width)),
        cell_period_roles=tuple(None for _ in range(width)),
        cell_measure_roles=tuple("STRUCTURAL" for _ in range(width)),
        mapping_approved=False,
    )


def _renumber_rows(
    rows: list[TMPage43LogicalRow], *, page_tag: str, table_key: str
) -> tuple[TMPage43LogicalRow, ...]:
    result = []
    for ordinal, row in enumerate(sorted(rows, key=lambda item: item.y_anchor), start=1):
        result.append(
            TMPage43LogicalRow(
                row_id=f"{page_tag}:{table_key.lower()}:row-{ordinal:04d}",
                table_key=row.table_key,
                note_number=row.note_number,
                ordinal=ordinal,
                row=row.row,
                row_kind=row.row_kind,
                source_role=row.source_role,
                y_anchor=row.y_anchor,
                label_bbox=row.label_bbox,
                value_bboxes=row.value_bboxes,
                label_line_indices=row.label_line_indices,
                value_line_indices=row.value_line_indices,
                visual_cell_evidence=row.visual_cell_evidence,
                cell_period_ends=row.cell_period_ends,
                cell_period_roles=row.cell_period_roles,
                cell_measure_roles=row.cell_measure_roles,
                mapping_approved=False,
            )
        )
    return tuple(result)


def _regular_numeric_rows(
    lines: tuple[_Line, ...],
    spec: TMPage43TableSpec,
    axes: tuple[TMPage43AxisBinding, ...],
    body_end: float,
    policy: TMPage43Policy,
    line_height: float,
    *,
    page_tag: str,
) -> tuple[list[TMPage43LogicalRow], tuple[int, ...]]:
    body_start = max(axis.unit_bbox.y1 for axis in axes)
    body = [line for line in lines if body_start < line.y_center < body_end]
    axis_edges = [axis.axis_right_edge for axis in axes]
    typical_gap = abs(axis_edges[1] - axis_edges[0])
    maximum_distance = typical_gap * policy.numeric_axis_max_distance_ratio
    per_axis: list[list[_Line]] = [[] for _ in axes]
    unassigned = []
    for line in (item for item in body if _numeric_only(item.text)):
        distances = [abs(line.x_right - edge) for edge in axis_edges]
        closest = min(range(len(distances)), key=distances.__getitem__)
        if (
            distances[closest] <= maximum_distance
            and line.x_right
            <= axis_edges[closest] + line_height * policy.numeric_axis_right_overrun_line_heights
        ):
            per_axis[closest].append(line)
        else:
            unassigned.append(line)
    assigned = [line for axis_lines in per_axis for line in axis_lines]
    numeric_groups = _clusters(assigned, line_height * policy.row_anchor_cluster_line_heights)
    if not numeric_groups or any(len(group) != len(axes) for group in numeric_groups):
        raise TMNoteWordBoxError(f"TM page-43 {spec.table_key} has incomplete numeric rows")
    used = {line.index for line in assigned + unassigned}
    label_boundary = axes[0].axis_right_edge - typical_gap * 0.35
    note_reference_left = (
        axes[0].axis_right_edge - typical_gap * policy.note_reference_left_gap_axis_widths
    )
    labels = [
        line
        for line in body
        if line.index not in used
        and line.x_right < label_boundary
        and line.bbox.x0 < note_reference_left
        and not _numeric_only(line.text)
    ]
    centers = [statistics.fmean(line.y_center for line in group) for group in numeric_groups]
    assignments: dict[int, int] = {}
    for label in labels:
        distances = [abs(label.y_center - center) for center in centers]
        closest = min(range(len(distances)), key=distances.__getitem__)
        if distances[closest] <= line_height * policy.label_direct_attach_line_heights:
            assignments[label.index] = closest
    rows = []
    for index, (center, group) in enumerate(zip(centers, numeric_groups, strict=True)):
        row_labels = sorted(
            (line for line in labels if assignments.get(line.index) == index),
            key=lambda line: (line.y_center, line.bbox.x0),
        )
        values = [
            sorted((line for line in axis_lines if line in group), key=lambda line: line.bbox.x0)
            for axis_lines in per_axis
        ]
        cells = tuple(
            parse_financial_number(" ".join(line.text for line in axis_lines))
            for axis_lines in values
        )
        if any(
            cell.observation not in {ObservationKind.VALUE, ObservationKind.ZERO} for cell in cells
        ):
            raise TMNoteWordBoxError(f"TM page-43 {spec.table_key} has an unresolved value")
        source_lines = row_labels + [line for axis_lines in values for line in axis_lines]
        rows.append(
            TMPage43LogicalRow(
                row_id="",
                table_key=spec.table_key,
                note_number=spec.note_number,
                ordinal=0,
                row=ReaderRow(
                    source_row_ids=_source_ids(page_tag, source_lines),
                    label=normalize_text(" ".join(line.text for line in row_labels)),
                    note_reference=spec.note_number,
                    cells=cells,
                ),
                row_kind=TMNoteRowKind.NUMERIC,
                source_role="DETAIL" if row_labels else "UNLABELED_TOTAL",
                y_anchor=center,
                label_bbox=_union(row_labels) if row_labels else None,
                value_bboxes=tuple(_union(axis_lines) for axis_lines in values),
                label_line_indices=tuple(line.index for line in row_labels),
                value_line_indices=tuple(
                    tuple(line.index for line in axis_lines) for axis_lines in values
                ),
                visual_cell_evidence=tuple(None for _ in axes),
                cell_period_ends=tuple(axis.period_end for axis in axes),
                cell_period_roles=tuple(axis.current_or_comparative for axis in axes),
                cell_measure_roles=tuple(axis.measure_role for axis in axes),
                mapping_approved=False,
            )
        )
    return rows, tuple(sorted(line.index for line in unassigned))


def _regular_table(
    lines: tuple[_Line, ...],
    spec: TMPage43TableSpec,
    source_bbox: BoundingBox,
    policy: TMPage43Policy,
    line_height: float,
    *,
    page_tag: str,
    table_ordinal: int,
) -> tuple[TMPage43Table, tuple[int, ...]]:
    title = _find_anchor_line(lines, spec.title_anchors, policy)
    body_end = _body_end(lines, spec, source_bbox, policy)
    native_axes = _bind_page31_axes(lines, title, None, body_end, policy, line_height)
    axes = tuple(_axis_from_period_axis(axis) for axis in native_axes)
    rows, unassigned = _regular_numeric_rows(
        lines,
        spec,
        axes,
        body_end,
        policy,
        line_height,
        page_tag=page_tag,
    )
    title_sources: tuple[_Line, ...]
    if spec.note_title_anchors:
        note_title = _find_anchor_line(lines, spec.note_title_anchors, policy, y1=title.y_center)
        note_number = _note_number_line(lines, spec.note_number, note_title, line_height)
        rows.extend(
            [
                _structural_row(
                    page_tag=page_tag,
                    table_key=spec.table_key,
                    note_number=spec.note_number,
                    label_lines=(note_title,),
                    source_lines=(note_number, note_title),
                    width=len(axes),
                    source_role="NOTE_TITLE",
                ),
                _structural_row(
                    page_tag=page_tag,
                    table_key=spec.table_key,
                    note_number=spec.note_number,
                    label_lines=(title,),
                    source_lines=(title,),
                    width=len(axes),
                    source_role="ANALYSIS_HEADING",
                ),
            ]
        )
        title_sources = (note_number, note_title, title)
    else:
        note_number_candidates = [
            line
            for line in lines
            if retrieval_key(line.text) == spec.note_number
            and line.bbox.x1 < title.bbox.x0
            and abs(line.y_center - title.y_center) <= line_height
        ]
        source_lines = (title,)
        source_role = "ANALYSIS_HEADING"
        if len(note_number_candidates) == 1:
            source_lines = (note_number_candidates[0], title)
            source_role = "NOTE_TITLE"
        rows.append(
            _structural_row(
                page_tag=page_tag,
                table_key=spec.table_key,
                note_number=spec.note_number,
                label_lines=(title,),
                source_lines=source_lines,
                width=len(axes),
                source_role=source_role,
            )
        )
        title_sources = source_lines
    final_rows = _renumber_rows(rows, page_tag=page_tag, table_key=spec.table_key)
    counts = (
        sum(row.row_kind is TMNoteRowKind.NUMERIC for row in final_rows),
        sum(row.row_kind is TMNoteRowKind.LABEL_ONLY for row in final_rows),
    )
    if counts != (spec.expected_numeric_rows, spec.expected_label_only_rows):
        raise TMNoteWordBoxError(
            f"TM page-43 {spec.table_key} denominator drifted: {counts[0]} numeric + "
            f"{counts[1]} label-only"
        )
    used_indices = {
        int(source_id.rsplit("-", 1)[-1])
        for row in final_rows
        for source_id in row.row.source_row_ids
    }
    table_lines = list(title_sources)
    table_lines.extend(
        line
        for axis in axes
        for line in lines
        if line.index in {axis.date_line_index, axis.unit_line_index}
    )
    table_lines.extend(line for line in lines if line.index in used_indices)
    return (
        TMPage43Table(
            ordinal=table_ordinal,
            table_key=spec.table_key,
            note_number=spec.note_number,
            title=title.text,
            title_line_indices=tuple(line.index for line in title_sources),
            axes=axes,
            rows=final_rows,
            bbox=_union(table_lines),
        ),
        unassigned,
    )


def _derivative_axes(
    lines: tuple[_Line, ...],
    title: _Line,
    current_period: _Line,
    policy: TMPage43Policy,
) -> tuple[TMPage43AxisBinding, ...]:
    headers = []
    used: set[int] = set()
    for spec in policy.measure_specs:
        line = _find_anchor_line(
            lines,
            spec.anchors,
            policy,
            y0=title.y_center,
            y1=current_period.y_center,
            used=used,
        )
        used.add(line.index)
        headers.append((spec, line))
    unit_candidates = sorted(
        (
            line
            for line in lines
            if title.y_center < line.y_center < current_period.y_center
            and _best_anchor_similarity(line.text, policy.unit_anchors)
            >= policy.minimum_unit_similarity
        ),
        key=lambda line: line.x_right,
    )
    if len(unit_candidates) != 3:
        raise TMNoteWordBoxError("TM page-43 derivative unit axes drifted")
    headers = sorted(headers, key=lambda item: item[1].x_right)
    if tuple(spec.column_role for spec, _line in headers) != tuple(
        spec.column_role for spec in policy.measure_specs
    ):
        raise TMNoteWordBoxError("TM page-43 derivative measure geometry drifted")
    axes = []
    for ordinal, ((spec, header), unit) in enumerate(
        zip(headers, unit_candidates, strict=True), start=1
    ):
        if (
            abs(header.x_right - unit.x_right)
            > (unit_candidates[-1].x_right - unit_candidates[0].x_right) * 0.3
        ):
            raise TMNoteWordBoxError("TM page-43 derivative header/unit pairing drifted")
        axes.append(
            TMPage43AxisBinding(
                ordinal=ordinal,
                axis_id=f"derivative-{spec.column_role.lower()}",
                column_role=spec.column_role,
                measure_role=spec.column_role,
                axis_right_edge=unit.x_right,
                raw_period_text="ROW_BOUND_VISIBLE_PERIOD",
                date_line_index=None,
                raw_unit_text=unit.text,
                unit_line_index=unit.index,
                current_or_comparative=None,
                canonical_unit=policy.canonical_unit,
                unit_multiplier=policy.unit_multiplier,
                period_start=None,
                period_end=None,
                period_type="SNAPSHOT",
                header_bbox=header.bbox,
                unit_bbox=unit.bbox,
                evidence=(
                    "measure role bound from the visible derivative column header",
                    "period is bound independently on each visible date row group",
                    "unit and multiplier matched from the visible column-local unit",
                ),
            )
        )
    return tuple(axes)


def _derivative_group_rows(
    lines: tuple[_Line, ...],
    spec: TMPage43TableSpec,
    axes: tuple[TMPage43AxisBinding, ...],
    period_line: _Line,
    group_end: float,
    period: date,
    period_role: str,
    policy: TMPage43Policy,
    line_height: float,
    source_image: Any,
    source_image_path: Path,
    *,
    page_tag: str,
) -> tuple[list[TMPage43LogicalRow], set[int]]:
    body = [line for line in lines if period_line.bbox.y1 < line.y_center < group_end]
    edges = [axis.axis_right_edge for axis in axes]
    gaps = [right - left for left, right in zip(edges, edges[1:], strict=False)]
    typical_gap = statistics.median(gaps)
    maximum_distance = typical_gap * policy.numeric_axis_max_distance_ratio
    per_axis: list[list[_Line]] = [[] for _ in axes]
    unassigned: set[int] = set()
    for line in (item for item in body if _numeric_only(item.text)):
        distances = [abs(line.x_right - edge) for edge in edges]
        closest = min(range(len(distances)), key=distances.__getitem__)
        if (
            distances[closest] <= maximum_distance
            and line.x_right
            <= edges[closest] + line_height * policy.numeric_axis_right_overrun_line_heights
        ):
            per_axis[closest].append(line)
        else:
            unassigned.add(line.index)
    assigned = [line for axis_lines in per_axis for line in axis_lines]
    groups = _clusters(assigned, line_height * policy.row_anchor_cluster_line_heights)
    if len(groups) != 3 or any(len(group) != 2 for group in groups):
        raise TMNoteWordBoxError("TM page-43 derivative numeric grid drifted")
    labels = [
        line
        for line in body
        if line.index not in {item.index for item in assigned}
        and not _numeric_only(line.text)
        and line.x_right < edges[0] - typical_gap * 0.35
    ]
    centers = [statistics.fmean(line.y_center for line in group) for group in groups]
    assignments: dict[int, int] = {}
    for label in labels:
        distances = [abs(label.y_center - center) for center in centers]
        closest = min(range(len(distances)), key=distances.__getitem__)
        if distances[closest] <= line_height * policy.label_direct_attach_line_heights:
            assignments[label.index] = closest
    rows = []
    for index, (center, group) in enumerate(zip(centers, groups, strict=True)):
        row_labels = sorted(
            (line for line in labels if assignments.get(line.index) == index),
            key=lambda line: (line.y_center, line.bbox.x0),
        )
        if len(row_labels) != 1:
            raise TMNoteWordBoxError("TM page-43 derivative row label drifted")
        values = [
            sorted((line for line in axis_lines if line in group), key=lambda line: line.bbox.x0)
            for axis_lines in per_axis
        ]
        visual: list[VisualCellEvidence | None] = []
        cells = []
        value_bboxes = []
        for axis_index, (axis, axis_lines) in enumerate(zip(axes, values, strict=True)):
            evidence = None
            if not axis_lines:
                evidence = _detect_visible_dash_v3(
                    source_image,
                    source_image_path=source_image_path,
                    axis_right_edge=axis.axis_right_edge,
                    anchor_center=center,
                    line_height=line_height,
                    config=policy.dash_config,
                )
                if evidence is None or axis_index != 0:
                    raise TMNoteWordBoxError(
                        "TM page-43 derivative missing cell lacks unique asset-dash pixels"
                    )
            cell = parse_financial_number(
                "-" if evidence is not None else " ".join(line.text for line in axis_lines)
            )
            cells.append(cell)
            visual.append(evidence)
            value_bboxes.append(
                _union(axis_lines)
                if axis_lines
                else BoundingBox(*evidence.component_box)
                if evidence is not None
                else None
            )
        if tuple(cell.observation for cell in cells) != (
            ObservationKind.DASH,
            ObservationKind.VALUE,
            ObservationKind.VALUE,
        ):
            raise TMNoteWordBoxError("TM page-43 derivative observation contract drifted")
        source_lines = row_labels + [line for axis_lines in values for line in axis_lines]
        rows.append(
            TMPage43LogicalRow(
                row_id="",
                table_key=spec.table_key,
                note_number=spec.note_number,
                ordinal=0,
                row=ReaderRow(
                    source_row_ids=_source_ids(page_tag, source_lines),
                    label=normalize_text(row_labels[0].text),
                    note_reference=spec.note_number,
                    cells=tuple(cells),
                ),
                row_kind=TMNoteRowKind.NUMERIC,
                source_role="DERIVATIVE_MEASURE_ROW",
                y_anchor=center,
                label_bbox=row_labels[0].bbox,
                value_bboxes=tuple(value_bboxes),
                label_line_indices=(row_labels[0].index,),
                value_line_indices=tuple(
                    tuple(line.index for line in axis_lines) for axis_lines in values
                ),
                visual_cell_evidence=tuple(visual),
                cell_period_ends=tuple(period for _ in axes),
                cell_period_roles=tuple(period_role for _ in axes),
                cell_measure_roles=tuple(axis.measure_role for axis in axes),
                mapping_approved=False,
            )
        )
    return rows, unassigned


def _derivative_table(
    lines: tuple[_Line, ...],
    spec: TMPage43TableSpec,
    source_bbox: BoundingBox,
    policy: TMPage43Policy,
    line_height: float,
    source_image: Any,
    source_image_path: Path,
    *,
    page_tag: str,
    table_ordinal: int,
) -> tuple[TMPage43Table, tuple[int, ...]]:
    title = _find_anchor_line(lines, spec.title_anchors, policy)
    note_number = _note_number_line(lines, spec.note_number, title, line_height)
    body_end = _body_end(lines, spec, source_bbox, policy)
    current_line = _find_anchor_line(
        lines, policy.current_period_anchors, policy, y0=title.y_center, y1=body_end
    )
    comparative_line = _find_anchor_line(
        lines,
        policy.comparative_period_anchors,
        policy,
        y0=current_line.y_center,
        y1=body_end,
    )
    current_period = parse_vietnamese_date(current_line.text)
    comparative_period = parse_vietnamese_date(comparative_line.text)
    if (
        current_period != policy.expected_current_period
        or comparative_period != policy.expected_comparative_period
    ):
        raise TMNoteWordBoxError("TM page-43 derivative visible periods drifted")
    axes = _derivative_axes(lines, title, current_line, policy)
    current_rows, current_unassigned = _derivative_group_rows(
        lines,
        spec,
        axes,
        current_line,
        comparative_line.bbox.y0,
        current_period,
        "CURRENT",
        policy,
        line_height,
        source_image,
        source_image_path,
        page_tag=page_tag,
    )
    comparative_rows, comparative_unassigned = _derivative_group_rows(
        lines,
        spec,
        axes,
        comparative_line,
        body_end,
        comparative_period,
        "COMPARATIVE",
        policy,
        line_height,
        source_image,
        source_image_path,
        page_tag=page_tag,
    )
    rows = [
        _structural_row(
            page_tag=page_tag,
            table_key=spec.table_key,
            note_number=spec.note_number,
            label_lines=(title,),
            source_lines=(note_number, title),
            width=len(axes),
            source_role="NOTE_TITLE",
        ),
        _structural_row(
            page_tag=page_tag,
            table_key=spec.table_key,
            note_number=spec.note_number,
            label_lines=(current_line,),
            source_lines=(current_line,),
            width=len(axes),
            source_role="PERIOD_GROUP",
        ),
        *current_rows,
        _structural_row(
            page_tag=page_tag,
            table_key=spec.table_key,
            note_number=spec.note_number,
            label_lines=(comparative_line,),
            source_lines=(comparative_line,),
            width=len(axes),
            source_role="PERIOD_GROUP",
        ),
        *comparative_rows,
    ]
    final_rows = _renumber_rows(rows, page_tag=page_tag, table_key=spec.table_key)
    counts = (
        sum(row.row_kind is TMNoteRowKind.NUMERIC for row in final_rows),
        sum(row.row_kind is TMNoteRowKind.LABEL_ONLY for row in final_rows),
    )
    if counts != (spec.expected_numeric_rows, spec.expected_label_only_rows):
        raise TMNoteWordBoxError("TM page-43 derivative denominator drifted")
    used_indices = {
        int(source_id.rsplit("-", 1)[-1])
        for row in final_rows
        for source_id in row.row.source_row_ids
    }
    table_lines = [note_number, title]
    table_lines.extend(
        line
        for axis in axes
        for line in lines
        if line.index in {axis.unit_line_index} or line.bbox == axis.header_bbox
    )
    table_lines.extend(line for line in lines if line.index in used_indices)
    return (
        TMPage43Table(
            ordinal=table_ordinal,
            table_key=spec.table_key,
            note_number=spec.note_number,
            title=title.text,
            title_line_indices=(note_number.index, title.index),
            axes=axes,
            rows=final_rows,
            bbox=_union(table_lines),
        ),
        tuple(sorted(current_unassigned | comparative_unassigned)),
    )


def parse_tm_page43(
    result_path: Path,
    source_image_path: Path,
    policy: TMPage43Policy,
    *,
    page_tag: str = "page-0043",
) -> ParsedTMPage43:
    """Reconstruct page 43 without granting any ReportNormId authority."""

    if page_tag != policy.page_tag:
        raise TMNoteWordBoxError("TM page-43 page tag drifted")
    if sha256_file(result_path) != policy.source_ocr_sha256:
        raise TMNoteWordBoxError("TM page-43 OCR artifact hash drifted")
    if sha256_file(source_image_path) != policy.source_render_sha256:
        raise TMNoteWordBoxError("TM page-43 source render hash drifted")
    source_image = cv2.imread(str(source_image_path), cv2.IMREAD_GRAYSCALE)
    if source_image is None:
        raise TMNoteWordBoxError("TM page-43 source render cannot be decoded")
    input_path, lines, _metadata = _load_lines(result_path, policy.minimum_line_score)
    line_height = float(statistics.median(line.height for line in lines))
    if line_height <= 0:
        raise TMNoteWordBoxError("TM page-43 line height is invalid")
    source_bbox = _union(lines)
    tables = []
    unassigned = []
    for index, spec in enumerate(policy.tables, start=1):
        if spec.table_key == "DERIVATIVES":
            table, table_unassigned = _derivative_table(
                lines,
                spec,
                source_bbox,
                policy,
                line_height,
                source_image,
                source_image_path,
                page_tag=page_tag,
                table_ordinal=index,
            )
        else:
            table, table_unassigned = _regular_table(
                lines,
                spec,
                source_bbox,
                policy,
                line_height,
                page_tag=page_tag,
                table_ordinal=index,
            )
        tables.append(table)
        unassigned.extend(table_unassigned)
    if [table.bbox.y0 for table in tables] != sorted(table.bbox.y0 for table in tables):
        raise TMNoteWordBoxError("TM page-43 table order drifted")
    rows = tuple(row for table in tables for row in table.rows)
    last_body_end = _body_end(lines, policy.tables[-1], source_bbox, policy)
    footer = tuple(
        sorted(
            line.index
            for line in lines
            if line.y_center >= last_body_end and _numeric_only(line.text)
        )
    )
    result = ParsedTMPage43(
        input_path=input_path,
        source_sha256=policy.source_ocr_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_pdf_sha256=policy.source_pdf_sha256,
        page_tag=page_tag,
        scope=policy.scope,
        scope_binding=policy.scope_binding,
        axes=tuple(axis for table in tables for axis in table.axes),
        tables=tuple(tables),
        rows=rows,
        line_height=line_height,
        source_ocr_bbox=source_bbox,
        table_bbox=BoundingBox(
            min(table.bbox.x0 for table in tables),
            min(table.bbox.y0 for table in tables),
            max(table.bbox.x1 for table in tables),
            max(table.bbox.y1 for table in tables),
        ),
        unassigned_numeric_line_indices=tuple(sorted(set(unassigned))),
        excluded_footer_numeric_line_indices=footer,
        mapping_authority=False,
        evidence=(
            "four page-local tables located from visible note and analysis headings",
            "three repeated two-period tables bind dates and units from local headers",
            "the derivative table binds three visible measure columns and two visible row periods",
            "six OCR-missing asset dashes require constrained render-pixel components",
            "dash observations remain distinct from numeric zero",
            "this parser grants no ReportNormId authority",
        ),
    )
    if (
        len(result.rows) != 29
        or result.numeric_row_count != 22
        or result.label_only_row_count != 7
        or result.financial_slot_count != 50
        or result.observation_count(ObservationKind.VALUE) != 44
        or result.observation_count(ObservationKind.DASH) != 6
        or result.unassigned_numeric_line_indices
        or result.excluded_footer_numeric_line_indices != (92,)
    ):
        raise TMNoteWordBoxError("TM page-43 page denominator drifted")
    return result


__all__ = [
    "ParsedTMPage43",
    "TMPage43AxisBinding",
    "TMPage43LogicalRow",
    "TMPage43Policy",
    "TMPage43Table",
    "TMPage43TableSpec",
    "load_tm_page43_policy",
    "parse_tm_page43",
]
