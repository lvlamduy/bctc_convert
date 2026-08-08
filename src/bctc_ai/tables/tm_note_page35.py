"""Fixed-source TM table reconstruction for MBB consolidated PDF page 35."""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import yaml

from bctc_ai.core.contracts import BoundingBox, ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import normalize_text, parse_financial_number, retrieval_key
from bctc_ai.evaluation.word_box_rows import VisualCellEvidence
from bctc_ai.evaluation.word_box_rows_v3 import (
    _detect_visible_dash_v3,
    load_word_box_reconstruction_v3_config,
)
from bctc_ai.tables.tm_note_word_box import (
    TMNoteAxisBinding,
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
class TMPage35TableSpec:
    table_key: str
    note_number: str
    title_anchors: tuple[str, ...]
    body_end_anchors: tuple[str, ...]
    structural_label_anchors: tuple[str, ...]
    dash_label_anchors: tuple[str, ...]
    expected_numeric_rows: int
    expected_label_only_rows: int


@dataclass(frozen=True)
class TMPage35Policy:
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
    tables: tuple[TMPage35TableSpec, ...]
    forbidden_semantic_inputs: tuple[str, ...]


@dataclass(frozen=True)
class TMPage35LogicalRow:
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
    mapping_approved: bool

    @property
    def financial_slot_count(self) -> int:
        return len(self.row.cells) if self.row_kind is TMNoteRowKind.NUMERIC else 0


@dataclass(frozen=True)
class TMPage35Table:
    ordinal: int
    table_key: str
    note_number: str
    title: str
    title_line_indices: tuple[int, ...]
    axes: tuple[TMNoteAxisBinding, ...]
    rows: tuple[TMPage35LogicalRow, ...]
    bbox: BoundingBox


@dataclass(frozen=True)
class ParsedTMPage35:
    input_path: str
    source_sha256: str
    source_render_sha256: str
    source_pdf_sha256: str
    page_tag: str
    scope: str
    scope_binding: str
    axes: tuple[TMNoteAxisBinding, ...]
    tables: tuple[TMPage35Table, ...]
    rows: tuple[TMPage35LogicalRow, ...]
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
        raise TMNoteWordBoxError(f"TM page-35 {field} anchors are invalid")
    result = tuple(retrieval_key(str(value)) for value in payload)
    if any(not value for value in result):
        raise TMNoteWordBoxError(f"TM page-35 {field} contains an empty anchor")
    return result


def _positive(payload: dict[str, Any], field: str) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise TMNoteWordBoxError(f"invalid positive TM page-35 setting: {field}")
    return float(value)


def load_tm_page35_policy(path: Path) -> TMPage35Policy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMNoteWordBoxError(f"cannot load TM page-35 policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE35_FIXED_GRID_DASH_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 35
        or payload.get("page_tag") != "page-0035"
        or payload.get("scope") != "CONSOLIDATED"
    ):
        raise TMNoteWordBoxError("TM page-35 policy identity drifted")
    hashes = (
        payload.get("source_pdf_sha256"),
        payload.get("source_render_sha256"),
        payload.get("source_ocr_sha256"),
    )
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMNoteWordBoxError("TM page-35 source hashes are invalid")
    thresholds = (
        payload.get("minimum_line_score"),
        payload.get("minimum_anchor_similarity"),
        payload.get("minimum_unit_similarity"),
    )
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= float(value) <= 1
        for value in thresholds
    ):
        raise TMNoteWordBoxError("TM page-35 similarity thresholds are invalid")
    unit = payload.get("unit")
    header = payload.get("header_geometry")
    geometry = payload.get("table_geometry")
    if not all(isinstance(value, dict) for value in (unit, header, geometry)):
        raise TMNoteWordBoxError("TM page-35 geometry policy is incomplete")
    multiplier = unit.get("multiplier")
    canonical_unit = unit.get("canonical")
    if (
        isinstance(multiplier, bool)
        or not isinstance(multiplier, int)
        or multiplier <= 0
        or not isinstance(canonical_unit, str)
        or not canonical_unit
    ):
        raise TMNoteWordBoxError("TM page-35 unit binding is invalid")
    dash_name = payload.get("dash_detector_config")
    if not isinstance(dash_name, str) or Path(dash_name).name != dash_name:
        raise TMNoteWordBoxError("TM page-35 dash detector path is invalid")
    dash_path = (path.parent / dash_name).resolve()
    if not dash_path.is_file() or sha256_file(dash_path) != payload.get(
        "dash_detector_config_sha256"
    ):
        raise TMNoteWordBoxError("TM page-35 dash detector is absent or drifted")
    dash_config = load_word_box_reconstruction_v3_config(dash_path).base.base
    raw_tables = payload.get("tables")
    if not isinstance(raw_tables, list) or len(raw_tables) != 3:
        raise TMNoteWordBoxError("TM page-35 must define three visible tables")
    tables = []
    for record in raw_tables:
        if not isinstance(record, dict):
            raise TMNoteWordBoxError("TM page-35 table record is invalid")
        table_key = record.get("table_key")
        note_number = record.get("note_number")
        numeric_rows = record.get("expected_numeric_rows")
        label_rows = record.get("expected_label_only_rows")
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
            or label_rows < 0
        ):
            raise TMNoteWordBoxError("TM page-35 table denominator is invalid")
        tables.append(
            TMPage35TableSpec(
                table_key=table_key,
                note_number=note_number,
                title_anchors=_anchors(record.get("title_anchors"), f"{table_key} title"),
                body_end_anchors=_anchors(
                    record.get("body_end_anchors", []),
                    f"{table_key} body end",
                    allow_empty=True,
                ),
                structural_label_anchors=_anchors(
                    record.get("structural_label_anchors"),
                    f"{table_key} structural label",
                    allow_empty=True,
                ),
                dash_label_anchors=_anchors(
                    record.get("dash_label_anchors"),
                    f"{table_key} dash label",
                    allow_empty=True,
                ),
                expected_numeric_rows=numeric_rows,
                expected_label_only_rows=label_rows,
            )
        )
    if len({table.table_key for table in tables}) != len(tables):
        raise TMNoteWordBoxError("TM page-35 table keys are duplicated")
    forbidden = payload.get("forbidden_semantic_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMNoteWordBoxError("TM page-35 forbidden semantic inputs drifted")
    footer_ratio = _positive(geometry, "page_footer_top_ratio")
    if footer_ratio >= 1:
        raise TMNoteWordBoxError("TM page-35 footer ratio must be below one")
    return TMPage35Policy(
        source_path=path,
        document=str(payload.get("document", "")),
        page_number=35,
        page_tag="page-0035",
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
        forbidden_semantic_inputs=tuple(str(value) for value in forbidden),
    )


def _find_titles(
    lines: tuple[_Line, ...], policy: TMPage35Policy
) -> tuple[tuple[TMPage35TableSpec, _Line], ...]:
    result = []
    used: set[int] = set()
    for spec in policy.tables:
        candidates = sorted(
            (
                (_best_anchor_similarity(line.text, spec.title_anchors), line)
                for line in lines
                if line.index not in used
            ),
            key=lambda item: (-item[0], item[1].y_center, item[1].index),
        )
        if not candidates or candidates[0][0] < policy.minimum_anchor_similarity:
            raise TMNoteWordBoxError(f"TM page-35 title is unresolved: {spec.table_key}")
        title = candidates[0][1]
        used.add(title.index)
        result.append((spec, title))
    if [title.y_center for _spec, title in result] != sorted(
        title.y_center for _spec, title in result
    ):
        raise TMNoteWordBoxError("TM page-35 table-title order drifted")
    return tuple(result)


def _body_end(
    lines: tuple[_Line, ...],
    spec: TMPage35TableSpec,
    title: _Line,
    next_title: _Line | None,
    footer_top: float,
    policy: TMPage35Policy,
) -> float:
    if spec.body_end_anchors:
        candidates = [
            line
            for line in lines
            if line.y_center > title.y_center
            and _best_anchor_similarity(line.text, spec.body_end_anchors)
            >= policy.minimum_anchor_similarity
        ]
        if not candidates:
            raise TMNoteWordBoxError(f"TM page-35 body end is unresolved: {spec.table_key}")
        return min(candidates, key=lambda line: (line.y_center, line.index)).bbox.y0
    return next_title.bbox.y0 if next_title is not None else footer_top


def _reconstruct_table(
    lines: tuple[_Line, ...],
    spec: TMPage35TableSpec,
    title: _Line,
    axes: tuple[TMNoteAxisBinding, ...],
    body_end: float,
    policy: TMPage35Policy,
    line_height: float,
    source_image: Any,
    source_image_path: Path,
    *,
    page_tag: str,
    table_ordinal: int,
) -> tuple[TMPage35Table, tuple[int, ...]]:
    body_start = max(axis.unit_bbox.y1 for axis in axes)
    body = [line for line in lines if body_start < line.y_center < body_end]
    axis_edges = [axis.axis_right_edge for axis in axes]
    typical_gap = abs(axis_edges[1] - axis_edges[0])
    maximum_distance = typical_gap * policy.numeric_axis_max_distance_ratio
    per_axis: list[list[_Line]] = [[] for _axis in axes]
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
        raise TMNoteWordBoxError(f"TM page-35 {spec.table_key} has incomplete numeric rows")
    numeric_centers = [
        statistics.fmean(line.y_center for line in group) for group in numeric_groups
    ]
    used = {line.index for line in assigned + unassigned}
    label_boundary = axes[0].axis_right_edge - typical_gap * 0.35
    note_reference_left = (
        axes[0].axis_right_edge - typical_gap * policy.note_reference_left_gap_axis_widths
    )
    label_candidates = [
        line
        for line in body
        if line.index not in used
        and line.x_right < label_boundary
        and line.bbox.x0 < note_reference_left
        and not _numeric_only(line.text)
    ]
    structural = [
        line
        for line in label_candidates
        if _best_anchor_similarity(line.text, spec.structural_label_anchors)
        >= policy.minimum_anchor_similarity
    ]
    dash_lines = [
        line
        for line in label_candidates
        if _best_anchor_similarity(line.text, spec.dash_label_anchors)
        >= policy.minimum_anchor_similarity
    ]
    dash_by_center: dict[float, tuple[VisualCellEvidence, ...]] = {}
    for label in dash_lines:
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
        if any(record is None for record in evidence):
            raise TMNoteWordBoxError(
                f"TM page-35 visible dash pair lacks constrained pixel evidence: {spec.table_key}"
            )
        dash_by_center[label.y_center] = tuple(record for record in evidence if record is not None)
    centers = sorted([*numeric_centers, *dash_by_center])
    assignments: dict[int, int] = {}
    for label in label_candidates:
        if label in structural:
            continue
        distances = [abs(label.y_center - center) for center in centers]
        closest = min(range(len(distances)), key=distances.__getitem__)
        if distances[closest] <= line_height * policy.label_direct_attach_line_heights:
            assignments[label.index] = closest
    proposals: list[tuple[float, TMPage35LogicalRow]] = []
    for center_index, center in enumerate(centers):
        labels = sorted(
            (line for line in label_candidates if assignments.get(line.index) == center_index),
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
        visual = tuple(dash_by_center.get(center, (None, None)))
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
            raise TMNoteWordBoxError(f"TM page-35 {spec.table_key} has an unresolved cell")
        source_lines = labels + [line for axis_lines in values for line in axis_lines]
        value_bboxes = tuple(
            _union(axis_lines)
            if axis_lines
            else BoundingBox(*evidence.component_box)
            if evidence is not None
            else None
            for axis_lines, evidence in zip(values, visual, strict=True)
        )
        proposals.append(
            (
                center,
                TMPage35LogicalRow(
                    row_id="",
                    table_key=spec.table_key,
                    note_number=spec.note_number,
                    ordinal=0,
                    row=ReaderRow(
                        source_row_ids=_source_ids(page_tag, source_lines),
                        label=normalize_text(" ".join(line.text for line in labels)),
                        note_reference=spec.note_number,
                        cells=cells,
                    ),
                    row_kind=TMNoteRowKind.NUMERIC,
                    source_role="DETAIL" if labels else "UNLABELED_TOTAL",
                    y_anchor=center,
                    label_bbox=_union(labels) if labels else None,
                    value_bboxes=value_bboxes,
                    label_line_indices=tuple(line.index for line in labels),
                    value_line_indices=tuple(
                        tuple(line.index for line in axis_lines) for axis_lines in values
                    ),
                    visual_cell_evidence=visual,
                    mapping_approved=False,
                ),
            )
        )
    for label in structural:
        proposals.append(
            (
                label.y_center,
                TMPage35LogicalRow(
                    row_id="",
                    table_key=spec.table_key,
                    note_number=spec.note_number,
                    ordinal=0,
                    row=ReaderRow(
                        source_row_ids=_source_ids(page_tag, [label]),
                        label=label.text,
                        note_reference=spec.note_number,
                        cells=tuple(parse_financial_number(None) for _axis in axes),
                    ),
                    row_kind=TMNoteRowKind.LABEL_ONLY,
                    source_role="GROUP_LABEL",
                    y_anchor=label.y_center,
                    label_bbox=label.bbox,
                    value_bboxes=tuple(None for _axis in axes),
                    label_line_indices=(label.index,),
                    value_line_indices=tuple(() for _axis in axes),
                    visual_cell_evidence=tuple(None for _axis in axes),
                    mapping_approved=False,
                ),
            )
        )
    rows = []
    for ordinal, (_center, row) in enumerate(sorted(proposals, key=lambda item: item[0]), start=1):
        rows.append(
            TMPage35LogicalRow(
                row_id=f"{page_tag}:{spec.table_key.lower()}:row-{ordinal:04d}",
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
                mapping_approved=False,
            )
        )
    counts = (
        sum(row.row_kind is TMNoteRowKind.NUMERIC for row in rows),
        sum(row.row_kind is TMNoteRowKind.LABEL_ONLY for row in rows),
    )
    if counts != (spec.expected_numeric_rows, spec.expected_label_only_rows):
        raise TMNoteWordBoxError(
            f"TM page-35 {spec.table_key} denominator drifted: {counts[0]} numeric + "
            f"{counts[1]} label-only"
        )
    table_lines = [title]
    table_lines.extend(
        line
        for axis in axes
        for line in lines
        if line.index in {axis.date_line_index, axis.unit_line_index}
    )
    used_indices = {
        int(source_id.rsplit("-", 1)[-1]) for row in rows for source_id in row.row.source_row_ids
    }
    table_lines.extend(line for line in lines if line.index in used_indices)
    return (
        TMPage35Table(
            ordinal=table_ordinal,
            table_key=spec.table_key,
            note_number=spec.note_number,
            title=title.text,
            title_line_indices=(title.index,),
            axes=axes,
            rows=tuple(rows),
            bbox=_union(table_lines),
        ),
        tuple(sorted(line.index for line in unassigned)),
    )


def parse_tm_page35(
    result_path: Path,
    source_image_path: Path,
    policy: TMPage35Policy,
    *,
    page_tag: str = "page-0035",
) -> ParsedTMPage35:
    if page_tag != policy.page_tag:
        raise TMNoteWordBoxError("TM page-35 page tag drifted")
    if sha256_file(result_path) != policy.source_ocr_sha256:
        raise TMNoteWordBoxError("TM page-35 OCR artifact hash drifted")
    if sha256_file(source_image_path) != policy.source_render_sha256:
        raise TMNoteWordBoxError("TM page-35 source render hash drifted")
    source_image = cv2.imread(str(source_image_path), cv2.IMREAD_GRAYSCALE)
    if source_image is None:
        raise TMNoteWordBoxError("TM page-35 source render cannot be decoded")
    input_path, lines, _metadata = _load_lines(result_path, policy.minimum_line_score)
    line_height = float(statistics.median(line.height for line in lines))
    if line_height <= 0:
        raise TMNoteWordBoxError("TM page-35 line height is invalid")
    source_bbox = _union(lines)
    titles = _find_titles(lines, policy)
    footer_top = source_bbox.y1 * policy.page_footer_top_ratio
    tables = []
    unassigned = []
    body_ends = []
    for index, (spec, title) in enumerate(titles):
        next_title = titles[index + 1][1] if index + 1 < len(titles) else None
        table_body_end = _body_end(lines, spec, title, next_title, footer_top, policy)
        body_ends.append(table_body_end)
        axes = _bind_page31_axes(
            lines,
            title,
            None,
            table_body_end,
            policy,
            line_height,
        )
        table, table_unassigned = _reconstruct_table(
            lines,
            spec,
            title,
            axes,
            table_body_end,
            policy,
            line_height,
            source_image,
            source_image_path,
            page_tag=page_tag,
            table_ordinal=index + 1,
        )
        tables.append(table)
        unassigned.extend(table_unassigned)
    canonical_axes = tables[0].axes
    semantic_axes = tuple(
        (
            axis.current_or_comparative,
            axis.period_end,
            axis.period_type,
            axis.canonical_unit,
            axis.unit_multiplier,
        )
        for axis in canonical_axes
    )
    if any(
        tuple(
            (
                axis.current_or_comparative,
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
        raise TMNoteWordBoxError("TM page-35 repeated headers disagree semantically")
    rows = tuple(row for table in tables for row in table.rows)
    footer = tuple(
        sorted(
            line.index
            for line in lines
            if line.y_center >= body_ends[-1] and _numeric_only(line.text)
        )
    )
    result = ParsedTMPage35(
        input_path=input_path,
        source_sha256=policy.source_ocr_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_pdf_sha256=policy.source_pdf_sha256,
        page_tag=page_tag,
        scope=policy.scope,
        scope_binding=policy.scope_binding,
        axes=canonical_axes,
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
        unassigned_numeric_line_indices=tuple(sorted(unassigned)),
        excluded_footer_numeric_line_indices=footer,
        mapping_authority=False,
        evidence=(
            "three local tables located from visible page-35 titles in source order",
            "two snapshot axes bound independently from every visible local header",
            "24 values reconstructed from PP-OCRv6 geometry",
            "two OCR-missing dash cells accepted only from constrained render-pixel components",
            "dash observations remain semantically distinct from numeric zero",
            "this parser grants no ReportNormId authority",
        ),
    )
    if (
        len(result.rows) != 14
        or result.numeric_row_count != 13
        or result.label_only_row_count != 1
        or result.financial_slot_count != 26
        or result.observation_count(ObservationKind.VALUE) != 24
        or result.observation_count(ObservationKind.DASH) != 2
    ):
        raise TMNoteWordBoxError("TM page-35 page denominator drifted")
    return result


__all__ = [
    "ParsedTMPage35",
    "TMPage35LogicalRow",
    "TMPage35Policy",
    "TMPage35Table",
    "TMPage35TableSpec",
    "load_tm_page35_policy",
    "parse_tm_page35",
]
