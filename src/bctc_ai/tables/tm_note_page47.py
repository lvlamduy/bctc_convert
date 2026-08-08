"""Hash-bound dual-duration TM reconstruction for MBB consolidated PDF page 47."""

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
class TMPage47ExpectedAxis:
    role: str
    period_start: date
    period_end: date


@dataclass(frozen=True)
class TMPage47StructuralSpec:
    source_role: str
    line_anchors: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class TMPage47WrappedLabelSpec:
    line_anchors: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class TMPage47TableSpec:
    table_key: str
    note_number: str
    title_anchors: tuple[str, ...]
    body_end_anchors: tuple[str, ...]
    first_body_anchors: tuple[str, ...]
    section_title_anchors: tuple[str, ...]
    structural_rows: tuple[TMPage47StructuralSpec, ...]
    wrapped_label_rows: tuple[TMPage47WrappedLabelSpec, ...]
    dash_label_anchors: tuple[str, ...]
    expected_numeric_rows: int
    expected_label_only_rows: int


@dataclass(frozen=True)
class TMPage47Policy:
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
    expected_axes: tuple[TMPage47ExpectedAxis, ...]
    numeric_axis_max_distance_ratio: float
    numeric_axis_right_overrun_line_heights: float
    row_anchor_cluster_line_heights: float
    label_direct_attach_line_heights: float
    note_reference_left_gap_axis_widths: float
    artifact_minimum_x_ratio: float
    page_footer_top_ratio: float
    dash_config: dict[str, float | int]
    dash_config_path: Path
    tables: tuple[TMPage47TableSpec, ...]
    forbidden_semantic_inputs: tuple[str, ...]


@dataclass(frozen=True)
class TMPage47AxisBinding:
    ordinal: int
    axis_id: str
    axis_right_edge: float
    raw_header_text: str
    header_line_indices: tuple[int, ...]
    current_or_comparative: str
    canonical_unit: str
    unit_multiplier: int
    period_start: date
    period_end: date
    period_type: str
    header_bbox: BoundingBox
    unit_bbox: BoundingBox
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class TMPage47LogicalRow:
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
    cell_period_starts: tuple[date | None, ...]
    cell_period_ends: tuple[date | None, ...]
    cell_period_roles: tuple[str | None, ...]
    mapping_approved: bool

    @property
    def financial_slot_count(self) -> int:
        return len(self.row.cells) if self.row_kind is TMNoteRowKind.NUMERIC else 0


@dataclass(frozen=True)
class TMPage47Table:
    ordinal: int
    table_key: str
    note_number: str
    title: str
    title_line_indices: tuple[int, ...]
    axes: tuple[TMPage47AxisBinding, ...]
    rows: tuple[TMPage47LogicalRow, ...]
    bbox: BoundingBox


@dataclass(frozen=True)
class ParsedTMPage47:
    input_path: str
    source_sha256: str
    source_render_sha256: str
    source_pdf_sha256: str
    page_tag: str
    scope: str
    scope_binding: str
    axes: tuple[TMPage47AxisBinding, ...]
    tables: tuple[TMPage47Table, ...]
    rows: tuple[TMPage47LogicalRow, ...]
    line_height: float
    source_ocr_bbox: BoundingBox
    table_bbox: BoundingBox
    unassigned_numeric_line_indices: tuple[int, ...]
    excluded_artifact_line_indices: tuple[int, ...]
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
        raise TMNoteWordBoxError(f"TM page-47 {field} anchors are invalid")
    result = tuple(retrieval_key(str(value)) for value in payload)
    if any(not value for value in result):
        raise TMNoteWordBoxError(f"TM page-47 {field} contains an empty anchor")
    return result


def _anchor_groups(payload: Any, field: str) -> tuple[tuple[str, ...], ...]:
    if not isinstance(payload, list) or not payload:
        raise TMNoteWordBoxError(f"TM page-47 {field} line-anchor groups are invalid")
    return tuple(_anchors(group, f"{field} line") for group in payload)


def _positive(payload: dict[str, Any], field: str) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise TMNoteWordBoxError(f"invalid positive TM page-47 setting: {field}")
    return float(value)


def _date_value(value: Any, field: str) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise TMNoteWordBoxError(f"invalid TM page-47 {field}") from exc
    raise TMNoteWordBoxError(f"invalid TM page-47 {field}")


def load_tm_page47_policy(path: Path) -> TMPage47Policy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMNoteWordBoxError(f"cannot load TM page-47 policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE47_DUAL_DURATION_FIXED_GRID_DASH_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 47
        or payload.get("page_tag") != "page-0047"
        or payload.get("scope") != "CONSOLIDATED"
    ):
        raise TMNoteWordBoxError("TM page-47 policy identity drifted")
    hashes = (
        payload.get("source_pdf_sha256"),
        payload.get("source_render_sha256"),
        payload.get("source_ocr_sha256"),
    )
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMNoteWordBoxError("TM page-47 source hashes are invalid")
    thresholds = (
        payload.get("minimum_line_score"),
        payload.get("minimum_anchor_similarity"),
        payload.get("minimum_unit_similarity"),
    )
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1
        for value in thresholds
    ):
        raise TMNoteWordBoxError("TM page-47 similarity thresholds are invalid")
    unit = payload.get("unit")
    header = payload.get("header_geometry")
    geometry = payload.get("table_geometry")
    if not all(isinstance(value, dict) for value in (unit, header, geometry)):
        raise TMNoteWordBoxError("TM page-47 geometry policy is incomplete")
    multiplier = unit.get("multiplier")
    canonical_unit = unit.get("canonical")
    if (
        isinstance(multiplier, bool)
        or not isinstance(multiplier, int)
        or multiplier <= 0
        or not isinstance(canonical_unit, str)
        or not canonical_unit
    ):
        raise TMNoteWordBoxError("TM page-47 unit binding is invalid")
    raw_axes = header.get("expected_axes")
    if not isinstance(raw_axes, list) or len(raw_axes) != 2:
        raise TMNoteWordBoxError("TM page-47 must define two duration axes")
    expected_axes = []
    for record in raw_axes:
        if not isinstance(record, dict) or record.get("role") not in {
            "CURRENT",
            "COMPARATIVE",
        }:
            raise TMNoteWordBoxError("TM page-47 duration-axis record is invalid")
        expected_axes.append(
            TMPage47ExpectedAxis(
                role=str(record["role"]),
                period_start=_date_value(record.get("period_start"), "period start"),
                period_end=_date_value(record.get("period_end"), "period end"),
            )
        )
    if tuple(axis.role for axis in expected_axes) != ("CURRENT", "COMPARATIVE"):
        raise TMNoteWordBoxError("TM page-47 duration-axis order drifted")
    dash_name = payload.get("dash_detector_config")
    if not isinstance(dash_name, str) or Path(dash_name).name != dash_name:
        raise TMNoteWordBoxError("TM page-47 dash detector path is invalid")
    dash_path = (path.parent / dash_name).resolve()
    if not dash_path.is_file() or sha256_file(dash_path) != payload.get(
        "dash_detector_config_sha256"
    ):
        raise TMNoteWordBoxError("TM page-47 dash detector is absent or drifted")
    raw_tables = payload.get("tables")
    if not isinstance(raw_tables, list) or len(raw_tables) != 3:
        raise TMNoteWordBoxError("TM page-47 must define three visible notes")
    tables = []
    for record in raw_tables:
        if not isinstance(record, dict):
            raise TMNoteWordBoxError("TM page-47 table record is invalid")
        raw_structural = record.get("structural_rows")
        if not isinstance(raw_structural, list):
            raise TMNoteWordBoxError("TM page-47 structural-row list is invalid")
        structural = []
        for item in raw_structural:
            if not isinstance(item, dict) or not isinstance(item.get("source_role"), str):
                raise TMNoteWordBoxError("TM page-47 structural row is invalid")
            structural.append(
                TMPage47StructuralSpec(
                    source_role=item["source_role"],
                    line_anchors=_anchor_groups(item.get("line_anchors"), "structural row"),
                )
            )
        raw_wrapped = record.get("wrapped_label_rows")
        if not isinstance(raw_wrapped, list):
            raise TMNoteWordBoxError("TM page-47 wrapped-label list is invalid")
        wrapped = []
        for item in raw_wrapped:
            if not isinstance(item, dict):
                raise TMNoteWordBoxError("TM page-47 wrapped-label row is invalid")
            wrapped.append(
                TMPage47WrappedLabelSpec(
                    line_anchors=_anchor_groups(item.get("line_anchors"), "wrapped label")
                )
            )
        numeric_rows = record.get("expected_numeric_rows")
        label_rows = record.get("expected_label_only_rows")
        table_key = record.get("table_key")
        note_number = record.get("note_number")
        if (
            not isinstance(table_key, str)
            or not table_key
            or not isinstance(note_number, str)
            or not note_number.isdigit()
            or isinstance(numeric_rows, bool)
            or not isinstance(numeric_rows, int)
            or numeric_rows <= 0
            or isinstance(label_rows, bool)
            or not isinstance(label_rows, int)
            or label_rows < 0
        ):
            raise TMNoteWordBoxError("TM page-47 table identity or denominator is invalid")
        tables.append(
            TMPage47TableSpec(
                table_key=table_key,
                note_number=note_number,
                title_anchors=_anchors(record.get("title_anchors"), "table title"),
                body_end_anchors=_anchors(
                    record.get("body_end_anchors"), "body end", allow_empty=True
                ),
                first_body_anchors=_anchors(record.get("first_body_anchors"), "first body"),
                section_title_anchors=_anchors(
                    record.get("section_title_anchors"), "section title", allow_empty=True
                ),
                structural_rows=tuple(structural),
                wrapped_label_rows=tuple(wrapped),
                dash_label_anchors=_anchors(
                    record.get("dash_label_anchors"), "dash label", allow_empty=True
                ),
                expected_numeric_rows=numeric_rows,
                expected_label_only_rows=label_rows,
            )
        )
    if [table.table_key for table in tables] != [
        "NET_FX",
        "NET_SECURITIES",
        "NET_OTHER",
    ]:
        raise TMNoteWordBoxError("TM page-47 note order drifted")
    forbidden = payload.get("forbidden_semantic_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMNoteWordBoxError("TM page-47 forbidden semantic inputs drifted")
    footer_ratio = _positive(geometry, "page_footer_top_ratio")
    artifact_ratio = _positive(geometry, "artifact_minimum_x_ratio")
    if footer_ratio >= 1 or artifact_ratio >= 1:
        raise TMNoteWordBoxError("TM page-47 page ratios must be below one")
    dash_config = load_word_box_reconstruction_v3_config(dash_path).base.base
    return TMPage47Policy(
        source_path=path,
        document=str(payload.get("document", "")),
        page_number=47,
        page_tag="page-0047",
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
        expected_axes=tuple(expected_axes),
        numeric_axis_max_distance_ratio=_positive(geometry, "numeric_axis_max_distance_ratio"),
        numeric_axis_right_overrun_line_heights=_positive(
            geometry, "numeric_axis_right_overrun_line_heights"
        ),
        row_anchor_cluster_line_heights=_positive(geometry, "row_anchor_cluster_line_heights"),
        label_direct_attach_line_heights=_positive(geometry, "label_direct_attach_line_heights"),
        note_reference_left_gap_axis_widths=_positive(
            geometry, "note_reference_left_gap_axis_widths"
        ),
        artifact_minimum_x_ratio=artifact_ratio,
        page_footer_top_ratio=footer_ratio,
        dash_config={str(key): value for key, value in dash_config.items()},
        dash_config_path=dash_path,
        tables=tuple(tables),
        forbidden_semantic_inputs=tuple(str(value) for value in forbidden),
    )


def _find_anchor_line(
    lines: tuple[_Line, ...],
    anchors: tuple[str, ...],
    policy: TMPage47Policy,
    *,
    minimum_y: float = float("-inf"),
    maximum_y: float = float("inf"),
    used: set[int] | None = None,
) -> _Line:
    excluded = used or set()
    candidates = sorted(
        (
            (_best_anchor_similarity(line.text, anchors), line)
            for line in lines
            if minimum_y < line.y_center < maximum_y and line.index not in excluded
        ),
        key=lambda item: (-item[0], item[1].y_center, item[1].index),
    )
    if not candidates or candidates[0][0] < policy.minimum_anchor_similarity:
        raise TMNoteWordBoxError(f"TM page-47 anchor is unresolved: {anchors}")
    return candidates[0][1]


def _find_anchor_group(
    lines: tuple[_Line, ...],
    line_anchors: tuple[tuple[str, ...], ...],
    policy: TMPage47Policy,
    line_height: float,
    *,
    minimum_y: float,
    maximum_y: float,
) -> tuple[_Line, ...]:
    candidates = tuple(
        tuple(
            (line, _best_anchor_similarity(line.text, anchors))
            for line in lines
            if minimum_y < line.y_center < maximum_y
            and _best_anchor_similarity(line.text, anchors) >= policy.minimum_anchor_similarity
        )
        for anchors in line_anchors
    )
    if any(not group for group in candidates):
        raise TMNoteWordBoxError("TM page-47 wrapped label anchor is unresolved")
    combinations = []
    for combination in itertools.product(*candidates):
        group = tuple(record[0] for record in combination)
        if len({line.index for line in group}) != len(group) or tuple(
            line.y_center for line in group
        ) != tuple(sorted(line.y_center for line in group)):
            continue
        if any(
            right.y_center - left.y_center > line_height * 1.6
            for left, right in zip(group, group[1:], strict=False)
        ):
            continue
        combinations.append(
            (
                -sum(record[1] for record in combination),
                group[-1].y_center - group[0].y_center,
                group[0].y_center,
                group,
            )
        )
    if not combinations:
        raise TMNoteWordBoxError("TM page-47 wrapped label lines are not locally adjacent")
    return min(combinations, key=lambda record: record[:3])[3]


def _number_line(lines: tuple[_Line, ...], number: str, title: _Line, line_height: float) -> _Line:
    candidates = [
        line
        for line in lines
        if retrieval_key(line.text).rstrip(".") == number
        and line.bbox.x1 < title.bbox.x0
        and abs(line.y_center - title.y_center) <= line_height
    ]
    if len(candidates) != 1:
        raise TMNoteWordBoxError(f"TM page-47 note {number} number anchor drifted")
    return candidates[0]


def _duration_axes(
    lines: tuple[_Line, ...],
    title: _Line,
    first_heading: _Line,
    policy: TMPage47Policy,
    line_height: float,
) -> tuple[TMPage47AxisBinding, ...]:
    candidates = tuple(
        line for line in lines if title.y_center < line.y_center < first_heading.y_center
    )
    date_lines = tuple(line for line in candidates if parse_vietnamese_date(line.text) is not None)
    unit_lines = tuple(
        line
        for line in candidates
        if not any(character.isdigit() for character in retrieval_key(line.text))
        and _best_anchor_similarity(line.text, policy.unit_anchors)
        >= policy.minimum_unit_similarity
    )
    if len(date_lines) != 4 or len(unit_lines) != 2:
        raise TMNoteWordBoxError("TM page-47 duration header must expose four dates and two units")
    ordered_units = tuple(sorted(unit_lines, key=lambda line: line.x_right))
    if (
        ordered_units[1].x_right - ordered_units[0].x_right
        < line_height * policy.minimum_axis_separation_line_heights
    ):
        raise TMNoteWordBoxError("TM page-47 duration axes are not distinctly separated")
    assigned: dict[int, list[_Line]] = {line.index: [] for line in ordered_units}
    for date_line in date_lines:
        unit_line = min(ordered_units, key=lambda line: abs(line.x_center - date_line.x_center))
        if (
            abs(unit_line.x_center - date_line.x_center)
            > line_height * policy.maximum_date_to_unit_center_distance_line_heights
        ):
            raise TMNoteWordBoxError("TM page-47 date/unit geometry is not locally bounded")
        assigned[unit_line.index].append(date_line)
    if any(len(group) != 2 for group in assigned.values()):
        raise TMNoteWordBoxError("TM page-47 duration date pairing drifted")
    result = []
    for ordinal, (unit_line, expected) in enumerate(
        zip(ordered_units, policy.expected_axes, strict=True), start=1
    ):
        local_dates = sorted(assigned[unit_line.index], key=lambda line: line.y_center)
        parsed_dates = [parse_vietnamese_date(line.text) for line in local_dates]
        if any(value is None for value in parsed_dates):
            raise TMNoteWordBoxError("TM page-47 duration date parsing failed")
        visible_start = min(value for value in parsed_dates if value is not None)
        visible_end = max(value for value in parsed_dates if value is not None)
        if (visible_start, visible_end) != (expected.period_start, expected.period_end):
            raise TMNoteWordBoxError("TM page-47 visible duration drifted from policy")
        header_lines = (*local_dates, unit_line)
        result.append(
            TMPage47AxisBinding(
                ordinal=ordinal,
                axis_id=f"duration-{expected.role.lower()}",
                axis_right_edge=unit_line.x_right,
                raw_header_text=normalize_text(" | ".join(line.text for line in header_lines)),
                header_line_indices=tuple(line.index for line in header_lines),
                current_or_comparative=expected.role,
                canonical_unit=policy.canonical_unit,
                unit_multiplier=policy.unit_multiplier,
                period_start=visible_start,
                period_end=visible_end,
                period_type="DURATION",
                header_bbox=_union(list(header_lines)),
                unit_bbox=unit_line.bbox,
                evidence=(
                    "period start and end parsed from the visible table-local duration header",
                    "current/comparative role bound by the visible horizontal period order",
                    "VND million multiplier matched from the visible table-local unit",
                ),
            )
        )
    return tuple(result)


def _structural_row(
    *,
    page_tag: str,
    table_key: str,
    note_number: str,
    label_lines: tuple[_Line, ...],
    source_lines: tuple[_Line, ...],
    source_role: str,
) -> TMPage47LogicalRow:
    center = statistics.fmean(line.y_center for line in label_lines)
    return TMPage47LogicalRow(
        row_id="",
        table_key=table_key,
        note_number=note_number,
        ordinal=0,
        row=ReaderRow(
            source_row_ids=_source_ids(page_tag, list(source_lines)),
            label=normalize_text(" ".join(line.text for line in label_lines)),
            note_reference=note_number,
            cells=tuple(parse_financial_number(None) for _axis in range(2)),
        ),
        row_kind=TMNoteRowKind.LABEL_ONLY,
        source_role=source_role,
        y_anchor=center,
        label_bbox=_union(list(source_lines)),
        value_bboxes=(None, None),
        label_line_indices=tuple(line.index for line in label_lines),
        value_line_indices=((), ()),
        visual_cell_evidence=(None, None),
        cell_period_starts=(None, None),
        cell_period_ends=(None, None),
        cell_period_roles=(None, None),
        mapping_approved=False,
    )


def _renumber(
    rows: list[TMPage47LogicalRow], *, page_tag: str, table_key: str
) -> tuple[TMPage47LogicalRow, ...]:
    result = []
    for ordinal, row in enumerate(sorted(rows, key=lambda item: item.y_anchor), start=1):
        result.append(
            TMPage47LogicalRow(
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
                cell_period_starts=row.cell_period_starts,
                cell_period_ends=row.cell_period_ends,
                cell_period_roles=row.cell_period_roles,
                mapping_approved=False,
            )
        )
    return tuple(result)


def _reconstruct_table(
    lines: tuple[_Line, ...],
    spec: TMPage47TableSpec,
    title: _Line,
    axes: tuple[TMPage47AxisBinding, ...],
    headings: tuple[tuple[TMPage47StructuralSpec, tuple[_Line, ...]], ...],
    wrapped_labels: tuple[tuple[_Line, ...], ...],
    body_end: float,
    policy: TMPage47Policy,
    line_height: float,
    source_image: Any,
    source_image_path: Path,
    *,
    page_tag: str,
    table_ordinal: int,
    section_title: _Line | None,
) -> tuple[TMPage47Table, tuple[int, ...], tuple[int, ...]]:
    body_start = max(axis.unit_bbox.y1 for axis in axes)
    body = [line for line in lines if body_start < line.y_center < body_end]
    image_width = int(source_image.shape[1])
    artifacts = tuple(
        line for line in body if line.bbox.x0 >= image_width * policy.artifact_minimum_x_ratio
    )
    artifact_indices = {line.index for line in artifacts}
    axis_edges = [axis.axis_right_edge for axis in axes]
    typical_gap = abs(axis_edges[1] - axis_edges[0])
    maximum_distance = typical_gap * policy.numeric_axis_max_distance_ratio
    per_axis: list[list[_Line]] = [[], []]
    unassigned = []
    for line in (
        item for item in body if _numeric_only(item.text) and item.index not in artifact_indices
    ):
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
    if not numeric_groups or any(len(group) > 2 for group in numeric_groups):
        raise TMNoteWordBoxError(f"TM page-47 {spec.table_key} has incomplete numeric rows")
    numeric_centers = [
        statistics.fmean(line.y_center for line in group) for group in numeric_groups
    ]
    used = {line.index for line in assigned + unassigned + list(artifacts)}
    used.update(line.index for _record, group in headings for line in group)
    used.update(line.index for group in wrapped_labels for line in group)
    used.update(index for axis in axes for index in axis.header_line_indices)
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
        and retrieval_key(line.text)
    ]
    dash_candidates = [*labels, *(line for group in wrapped_labels for line in group)]
    dash_labels = [
        line
        for line in dash_candidates
        if _best_anchor_similarity(line.text, spec.dash_label_anchors)
        >= policy.minimum_anchor_similarity
    ]
    dash_by_center: dict[float, tuple[VisualCellEvidence | None, ...]] = {}
    for label in dash_labels:
        evidence = tuple(
            _detect_visible_dash_v3(
                source_image,
                source_image_path=source_image_path,
                axis_right_edge=axis.axis_right_edge,
                anchor_center=label.y_center,
                line_height=line_height,
                config=policy.dash_config,
            )
            for axis in axes
        )
        if all(record is None for record in evidence):
            raise TMNoteWordBoxError(
                f"TM page-47 visible dash lacks constrained pixel evidence: {spec.table_key}"
            )
        nearby = [
            center
            for center in numeric_centers
            if abs(center - label.y_center) <= line_height * policy.row_anchor_cluster_line_heights
        ]
        center = (
            min(nearby, key=lambda value: abs(value - label.y_center)) if nearby else label.y_center
        )
        if center in dash_by_center:
            raise TMNoteWordBoxError(f"TM page-47 duplicate dash row: {spec.table_key}")
        dash_by_center[center] = evidence
    centers = sorted(set(numeric_centers) | set(dash_by_center))
    if len(centers) != spec.expected_numeric_rows:
        raise TMNoteWordBoxError(f"TM page-47 {spec.table_key} numeric denominator drifted")
    assignments: dict[int, int] = {}
    for label in labels:
        distances = [abs(label.y_center - center) for center in centers]
        closest = min(range(len(distances)), key=distances.__getitem__)
        if distances[closest] <= line_height * policy.label_direct_attach_line_heights:
            assignments[label.index] = closest
    wrapped_assignments: dict[int, list[_Line]] = {}
    for group in wrapped_labels:
        group_center = statistics.fmean(line.y_center for line in group)
        distances = [abs(group_center - center) for center in centers]
        closest = min(range(len(distances)), key=distances.__getitem__)
        if distances[closest] > line_height * policy.label_direct_attach_line_heights:
            raise TMNoteWordBoxError(
                f"TM page-47 wrapped label is detached from its numeric row: {spec.table_key}"
            )
        wrapped_assignments.setdefault(closest, []).extend(group)
    rows: list[TMPage47LogicalRow] = []
    for center_index, center in enumerate(centers):
        row_labels = sorted(
            (
                *(line for line in labels if assignments.get(line.index) == center_index),
                *wrapped_assignments.get(center_index, []),
            ),
            key=lambda line: (line.y_center, line.bbox.x0),
        )
        nearest_group = min(
            numeric_groups,
            key=lambda group: abs(statistics.fmean(line.y_center for line in group) - center),
        )
        group_center = statistics.fmean(line.y_center for line in nearest_group)
        group = (
            nearest_group
            if abs(group_center - center) <= line_height * policy.row_anchor_cluster_line_heights
            else []
        )
        values = [
            sorted((line for line in axis_lines if line in group), key=lambda line: line.bbox.x0)
            for axis_lines in per_axis
        ]
        visual = tuple(
            None if axis_lines else evidence
            for axis_lines, evidence in zip(
                values,
                dash_by_center.get(center, (None, None)),
                strict=True,
            )
        )
        cells = tuple(
            parse_financial_number(
                "-"
                if evidence is not None and not axis_lines
                else " ".join(line.text for line in axis_lines)
            )
            for axis_lines, evidence in zip(values, visual, strict=True)
        )
        if any(
            cell.observation
            not in {ObservationKind.VALUE, ObservationKind.ZERO, ObservationKind.DASH}
            for cell in cells
        ):
            raise TMNoteWordBoxError(f"TM page-47 {spec.table_key} has an unresolved cell")
        source_lines = row_labels + [line for axis_lines in values for line in axis_lines]
        value_bboxes = tuple(
            _union(axis_lines)
            if axis_lines
            else BoundingBox(*evidence.component_box)
            if evidence is not None
            else None
            for axis_lines, evidence in zip(values, visual, strict=True)
        )
        rows.append(
            TMPage47LogicalRow(
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
                value_bboxes=value_bboxes,
                label_line_indices=tuple(line.index for line in row_labels),
                value_line_indices=tuple(
                    tuple(line.index for line in axis_lines) for axis_lines in values
                ),
                visual_cell_evidence=visual,
                cell_period_starts=tuple(axis.period_start for axis in axes),
                cell_period_ends=tuple(axis.period_end for axis in axes),
                cell_period_roles=tuple(axis.current_or_comparative for axis in axes),
                mapping_approved=False,
            )
        )
    title_number = _number_line(lines, spec.note_number, title, line_height)
    rows.append(
        _structural_row(
            page_tag=page_tag,
            table_key=spec.table_key,
            note_number=spec.note_number,
            label_lines=(title,),
            source_lines=(title_number, title),
            source_role="NOTE_TITLE",
        )
    )
    if section_title is not None:
        neighbors = tuple(
            line
            for line in lines
            if line.bbox.x1 < section_title.bbox.x0
            and abs(line.y_center - section_title.y_center) <= line_height
        )
        rows.append(
            _structural_row(
                page_tag=page_tag,
                table_key=spec.table_key,
                note_number=spec.note_number,
                label_lines=(section_title,),
                source_lines=(*neighbors, section_title),
                source_role="STATEMENT_SECTION_TITLE",
            )
        )
    for structural_spec, group in headings:
        rows.append(
            _structural_row(
                page_tag=page_tag,
                table_key=spec.table_key,
                note_number=spec.note_number,
                label_lines=group,
                source_lines=group,
                source_role=structural_spec.source_role,
            )
        )
    final_rows = _renumber(rows, page_tag=page_tag, table_key=spec.table_key)
    counts = (
        sum(row.row_kind is TMNoteRowKind.NUMERIC for row in final_rows),
        sum(row.row_kind is TMNoteRowKind.LABEL_ONLY for row in final_rows),
    )
    if counts != (spec.expected_numeric_rows, spec.expected_label_only_rows):
        raise TMNoteWordBoxError(
            f"TM page-47 {spec.table_key} denominator drifted: {counts[0]} numeric + "
            f"{counts[1]} label-only"
        )
    used_indices = {
        int(source_id.rsplit("-", 1)[-1])
        for row in final_rows
        for source_id in row.row.source_row_ids
    }
    table_lines = [line for line in lines if line.index in used_indices]
    table_lines.extend(
        line for axis in axes for line in lines if line.index in axis.header_line_indices
    )
    return (
        TMPage47Table(
            ordinal=table_ordinal,
            table_key=spec.table_key,
            note_number=spec.note_number,
            title=title.text,
            title_line_indices=(title_number.index, title.index),
            axes=axes,
            rows=final_rows,
            bbox=_union(table_lines),
        ),
        tuple(sorted(line.index for line in unassigned)),
        tuple(sorted(artifact_indices)),
    )


def parse_tm_page47(
    result_path: Path,
    source_image_path: Path,
    policy: TMPage47Policy,
    *,
    page_tag: str = "page-0047",
) -> ParsedTMPage47:
    if page_tag != policy.page_tag:
        raise TMNoteWordBoxError("TM page-47 page tag drifted")
    if sha256_file(result_path) != policy.source_ocr_sha256:
        raise TMNoteWordBoxError("TM page-47 OCR artifact hash drifted")
    if sha256_file(source_image_path) != policy.source_render_sha256:
        raise TMNoteWordBoxError("TM page-47 source render hash drifted")
    source_image = cv2.imread(str(source_image_path), cv2.IMREAD_GRAYSCALE)
    if source_image is None:
        raise TMNoteWordBoxError("TM page-47 source render cannot be decoded")
    input_path, lines, _metadata = _load_lines(result_path, policy.minimum_line_score)
    line_height = float(statistics.median(line.height for line in lines))
    if line_height <= 0:
        raise TMNoteWordBoxError("TM page-47 line height is invalid")
    source_bbox = _union(lines)
    footer_top = source_bbox.y1 * policy.page_footer_top_ratio
    titles = tuple(_find_anchor_line(lines, spec.title_anchors, policy) for spec in policy.tables)
    if tuple(title.y_center for title in titles) != tuple(
        sorted(title.y_center for title in titles)
    ):
        raise TMNoteWordBoxError("TM page-47 note-title order drifted")
    tables = []
    unassigned = []
    artifacts = []
    for ordinal, (spec, title) in enumerate(zip(policy.tables, titles, strict=True), start=1):
        body_end = (
            _find_anchor_line(
                lines,
                spec.body_end_anchors,
                policy,
                minimum_y=title.y_center,
            ).bbox.y0
            if spec.body_end_anchors
            else footer_top
        )
        headings = tuple(
            (
                record,
                _find_anchor_group(
                    lines,
                    record.line_anchors,
                    policy,
                    line_height,
                    minimum_y=title.y_center,
                    maximum_y=body_end,
                ),
            )
            for record in spec.structural_rows
        )
        if tuple(group[0].y_center for _record, group in headings) != tuple(
            sorted(group[0].y_center for _record, group in headings)
        ):
            raise TMNoteWordBoxError(f"TM page-47 {spec.table_key} heading order drifted")
        wrapped_labels = tuple(
            _find_anchor_group(
                lines,
                record.line_anchors,
                policy,
                line_height,
                minimum_y=title.y_center,
                maximum_y=body_end,
            )
            for record in spec.wrapped_label_rows
        )
        first_body = _find_anchor_line(
            lines,
            spec.first_body_anchors,
            policy,
            minimum_y=title.y_center,
            maximum_y=body_end,
        )
        axes = _duration_axes(lines, title, first_body, policy, line_height)
        section_title = (
            _find_anchor_line(
                lines,
                spec.section_title_anchors,
                policy,
                maximum_y=title.y_center,
            )
            if spec.section_title_anchors
            else None
        )
        table, table_unassigned, table_artifacts = _reconstruct_table(
            lines,
            spec,
            title,
            axes,
            headings,
            wrapped_labels,
            body_end,
            policy,
            line_height,
            source_image,
            source_image_path,
            page_tag=page_tag,
            table_ordinal=ordinal,
            section_title=section_title,
        )
        tables.append(table)
        unassigned.extend(table_unassigned)
        artifacts.extend(table_artifacts)
    semantic_axes = tuple(
        (
            axis.current_or_comparative,
            axis.period_start,
            axis.period_end,
            axis.period_type,
            axis.canonical_unit,
            axis.unit_multiplier,
        )
        for axis in tables[0].axes
    )
    if any(
        tuple(
            (
                axis.current_or_comparative,
                axis.period_start,
                axis.period_end,
                axis.period_type,
                axis.canonical_unit,
                axis.unit_multiplier,
            )
            for axis in table.axes
        )
        != semantic_axes
        for table in tables[1:]
    ):
        raise TMNoteWordBoxError("TM page-47 repeated duration headers disagree semantically")
    rows = tuple(row for table in tables for row in table.rows)
    footer = tuple(
        sorted(
            line.index for line in lines if line.y_center >= footer_top and _numeric_only(line.text)
        )
    )
    result = ParsedTMPage47(
        input_path=input_path,
        source_sha256=policy.source_ocr_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_pdf_sha256=policy.source_pdf_sha256,
        page_tag=page_tag,
        scope=policy.scope,
        scope_binding=policy.scope_binding,
        axes=tables[0].axes,
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
        excluded_artifact_line_indices=tuple(sorted(set(artifacts))),
        excluded_footer_numeric_line_indices=footer,
        mapping_authority=False,
        evidence=(
            "three complete source notes bounded on immutable PDF page 47",
            "three repeated duration-axis pairs bound independently from visible dates and units",
            "21 numeric rows reconstructed from PP-OCRv6 geometry plus pixel-backed DASH",
            "schema identifiers are absent from parser inputs and mapping authority remains false",
        ),
    )
    if (
        len(result.rows) != 28
        or result.numeric_row_count != 21
        or result.label_only_row_count != 7
        or result.financial_slot_count != 42
        or result.observation_count(ObservationKind.VALUE) != 41
        or result.observation_count(ObservationKind.DASH) != 1
        or result.unassigned_numeric_line_indices
        or result.excluded_artifact_line_indices
        or result.excluded_footer_numeric_line_indices != (90,)
    ):
        raise TMNoteWordBoxError(
            "TM page-47 exact source denominator drifted: "
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
    "ParsedTMPage47",
    "TMPage47AxisBinding",
    "TMPage47LogicalRow",
    "TMPage47Policy",
    "TMPage47Table",
    "load_tm_page47_policy",
    "parse_tm_page47",
]
