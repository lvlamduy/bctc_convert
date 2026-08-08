"""Hash-bound TM reconstruction for MBB consolidated PDF page 48.

The page contains two ordinary dual-duration notes and one single-axis
variance explanation.  Only the first two notes expose financial-statement
slots.  The variance table and the quantities in its narrative introduction
are retained as auxiliary provenance and never promoted to schema values.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import cv2
import yaml

from bctc_ai.core.contracts import BoundingBox, ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import normalize_text, parse_financial_number, retrieval_key
from bctc_ai.evaluation.word_box_rows_v3 import load_word_box_reconstruction_v3_config
from bctc_ai.tables.tm_note_page47 import (
    TMPage47AxisBinding,
    TMPage47ExpectedAxis,
    TMPage47LogicalRow,
    TMPage47StructuralSpec,
    TMPage47Table,
    TMPage47TableSpec,
    TMPage47WrappedLabelSpec,
    _duration_axes,
    _find_anchor_group,
    _find_anchor_line,
    _number_line,
    _reconstruct_table,
)
from bctc_ai.tables.tm_note_word_box import (
    TMNoteWordBoxError,
    _clusters,
    _load_lines,
    _numeric_only,
    _source_ids,
    _union,
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GROUPED_NUMBER = re.compile(r"(?<!\d)\d{1,3}(?:[.]\d{3})+(?!\d)")
_PERCENTAGE = re.compile(r"(?<!\d)\d{1,3}[,]\d+%(?!\d)")
_REQUIRED_FORBIDDEN = {
    "missing_ocr_cell_as_dash_without_pixel_evidence",
    "template_labels_as_row_reconstruction_input",
    "approved_report_norm_id_assignment",
    "historical_or_mongodb_values",
    "human_review_answers",
    "dash_as_zero",
    "accounting_equations_as_value_imputation",
    "auxiliary_variance_as_financial_statement_value",
    "narrative_quantity_as_schema_mapping_input",
}


@dataclass(frozen=True)
class TMPage48AuxiliarySpec:
    title_anchors: tuple[str, ...]
    axis_label_anchors: tuple[str, ...]
    unit_anchors: tuple[str, ...]
    first_row_anchors: tuple[str, ...]
    total_row_anchors: tuple[str, ...]
    expected_driver_rows: int
    expected_total_rows: int
    numeric_axis_max_distance_line_heights: float
    label_attach_line_heights: float


@dataclass(frozen=True)
class TMPage48Policy:
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
    auxiliary: TMPage48AuxiliarySpec
    forbidden_semantic_inputs: tuple[str, ...]


@dataclass(frozen=True)
class TMPage48AuxiliaryAxis:
    axis_id: str
    semantic_role: str
    raw_header_text: str
    header_line_indices: tuple[int, ...]
    canonical_unit: str
    unit_multiplier: int
    header_bbox: BoundingBox
    unit_bbox: BoundingBox
    comparison_basis: str
    mapping_approved: bool


@dataclass(frozen=True)
class TMPage48AuxiliaryRow:
    row_id: str
    ordinal: int
    label: str
    value: Decimal
    observation: ObservationKind
    source_role: str
    label_bbox: BoundingBox
    value_bbox: BoundingBox
    label_line_indices: tuple[int, ...]
    value_line_indices: tuple[int, ...]
    source_row_ids: tuple[str, ...]
    mapping_approved: bool


@dataclass(frozen=True)
class TMPage48NarrativeQuantity:
    quantity_id: str
    semantic_role: str
    raw_text: str
    value: Decimal
    canonical_unit: str
    unit_multiplier: int
    source_line_indices: tuple[int, ...]
    source_bbox: BoundingBox
    mapping_approved: bool


@dataclass(frozen=True)
class ParsedTMPage48:
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
    auxiliary_axis: TMPage48AuxiliaryAxis
    auxiliary_rows: tuple[TMPage48AuxiliaryRow, ...]
    narrative_quantities: tuple[TMPage48NarrativeQuantity, ...]
    line_height: float
    source_ocr_bbox: BoundingBox
    table_bbox: BoundingBox
    auxiliary_bbox: BoundingBox
    unassigned_numeric_line_indices: tuple[int, ...]
    excluded_artifact_line_indices: tuple[int, ...]
    excluded_footer_numeric_line_indices: tuple[int, ...]
    mapping_authority: bool
    evidence: tuple[str, ...]

    @property
    def numeric_row_count(self) -> int:
        return sum(row.financial_slot_count > 0 for row in self.rows)

    @property
    def label_only_row_count(self) -> int:
        return len(self.rows) - self.numeric_row_count

    @property
    def financial_slot_count(self) -> int:
        return sum(row.financial_slot_count for row in self.rows)

    @property
    def total_logical_row_count(self) -> int:
        return len(self.rows) + len(self.auxiliary_rows)

    def observation_count(self, observation: ObservationKind) -> int:
        return sum(
            cell.observation is observation
            for row in self.rows
            if row.financial_slot_count
            for cell in row.row.cells
        )


def _anchors(payload: Any, field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(payload, list) or (not payload and not allow_empty):
        raise TMNoteWordBoxError(f"TM page-48 {field} anchors are invalid")
    result = tuple(retrieval_key(str(value)) for value in payload)
    if any(not value for value in result):
        raise TMNoteWordBoxError(f"TM page-48 {field} contains an empty anchor")
    return result


def _anchor_groups(payload: Any, field: str) -> tuple[tuple[str, ...], ...]:
    if not isinstance(payload, list) or not payload:
        raise TMNoteWordBoxError(f"TM page-48 {field} line-anchor groups are invalid")
    return tuple(_anchors(group, f"{field} line") for group in payload)


def _positive(payload: dict[str, Any], field: str) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise TMNoteWordBoxError(f"invalid positive TM page-48 setting: {field}")
    return float(value)


def _date_value(value: Any, field: str) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise TMNoteWordBoxError(f"invalid TM page-48 {field}") from exc
    raise TMNoteWordBoxError(f"invalid TM page-48 {field}")


def load_tm_page48_policy(path: Path) -> TMPage48Policy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMNoteWordBoxError(f"cannot load TM page-48 policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE48_DURATION_AND_AUXILIARY_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 48
        or payload.get("page_tag") != "page-0048"
        or payload.get("scope") != "CONSOLIDATED"
    ):
        raise TMNoteWordBoxError("TM page-48 policy identity drifted")
    hashes = tuple(
        payload.get(field)
        for field in ("source_pdf_sha256", "source_render_sha256", "source_ocr_sha256")
    )
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMNoteWordBoxError("TM page-48 source hashes are invalid")
    thresholds = tuple(
        payload.get(field)
        for field in ("minimum_line_score", "minimum_anchor_similarity", "minimum_unit_similarity")
    )
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1
        for value in thresholds
    ):
        raise TMNoteWordBoxError("TM page-48 similarity thresholds are invalid")
    unit = payload.get("unit")
    header = payload.get("header_geometry")
    geometry = payload.get("table_geometry")
    auxiliary = payload.get("auxiliary_variance")
    if not all(isinstance(value, dict) for value in (unit, header, geometry, auxiliary)):
        raise TMNoteWordBoxError("TM page-48 geometry policy is incomplete")
    multiplier = unit.get("multiplier")
    canonical = unit.get("canonical")
    if (
        isinstance(multiplier, bool)
        or not isinstance(multiplier, int)
        or multiplier <= 0
        or not isinstance(canonical, str)
        or not canonical
    ):
        raise TMNoteWordBoxError("TM page-48 unit binding is invalid")
    expected_axes = []
    raw_axes = header.get("expected_axes")
    if not isinstance(raw_axes, list) or len(raw_axes) != 2:
        raise TMNoteWordBoxError("TM page-48 expected axes are invalid")
    for record in raw_axes:
        if not isinstance(record, dict) or record.get("role") not in {"CURRENT", "COMPARATIVE"}:
            raise TMNoteWordBoxError("TM page-48 expected axis record is invalid")
        expected_axes.append(
            TMPage47ExpectedAxis(
                role=str(record["role"]),
                period_start=_date_value(record.get("period_start"), "period_start"),
                period_end=_date_value(record.get("period_end"), "period_end"),
            )
        )
    raw_tables = payload.get("tables")
    if not isinstance(raw_tables, list) or len(raw_tables) != 2:
        raise TMNoteWordBoxError("TM page-48 must define two financial tables")
    tables = []
    for record in raw_tables:
        if not isinstance(record, dict):
            raise TMNoteWordBoxError("TM page-48 table record is invalid")
        structural = []
        for structural_record in record.get("structural_rows", []):
            if not isinstance(structural_record, dict):
                raise TMNoteWordBoxError("TM page-48 structural row is invalid")
            structural.append(
                TMPage47StructuralSpec(
                    source_role=str(structural_record.get("source_role", "")),
                    line_anchors=_anchor_groups(
                        structural_record.get("line_anchors"), "structural"
                    ),
                )
            )
        wrapped = []
        for wrapped_record in record.get("wrapped_label_rows", []):
            if not isinstance(wrapped_record, dict):
                raise TMNoteWordBoxError("TM page-48 wrapped row is invalid")
            wrapped.append(
                TMPage47WrappedLabelSpec(
                    line_anchors=_anchor_groups(wrapped_record.get("line_anchors"), "wrapped label")
                )
            )
        numeric = record.get("expected_numeric_rows")
        label_only = record.get("expected_label_only_rows")
        if (
            isinstance(numeric, bool)
            or not isinstance(numeric, int)
            or numeric <= 0
            or isinstance(label_only, bool)
            or not isinstance(label_only, int)
            or label_only < 0
        ):
            raise TMNoteWordBoxError("TM page-48 table denominator is invalid")
        tables.append(
            TMPage47TableSpec(
                table_key=str(record.get("table_key", "")),
                note_number=str(record.get("note_number", "")),
                title_anchors=_anchors(record.get("title_anchors"), "table title"),
                body_end_anchors=_anchors(
                    record.get("body_end_anchors", []), "table end", allow_empty=True
                ),
                first_body_anchors=_anchors(record.get("first_body_anchors"), "first body"),
                section_title_anchors=(),
                structural_rows=tuple(structural),
                wrapped_label_rows=tuple(wrapped),
                dash_label_anchors=_anchors(
                    record.get("dash_label_anchors", []), "dash label", allow_empty=True
                ),
                expected_numeric_rows=numeric,
                expected_label_only_rows=label_only,
            )
        )
    driver_rows = auxiliary.get("expected_driver_rows")
    total_rows = auxiliary.get("expected_total_rows")
    if (
        isinstance(driver_rows, bool)
        or not isinstance(driver_rows, int)
        or driver_rows <= 0
        or isinstance(total_rows, bool)
        or not isinstance(total_rows, int)
        or total_rows <= 0
    ):
        raise TMNoteWordBoxError("TM page-48 auxiliary denominator is invalid")
    dash_name = payload.get("dash_detector_config")
    if not isinstance(dash_name, str) or Path(dash_name).name != dash_name:
        raise TMNoteWordBoxError("TM page-48 dash detector path is invalid")
    dash_path = (path.parent / dash_name).resolve()
    if not dash_path.is_file() or sha256_file(dash_path) != payload.get(
        "dash_detector_config_sha256"
    ):
        raise TMNoteWordBoxError("TM page-48 dash detector is absent or drifted")
    dash_config = load_word_box_reconstruction_v3_config(dash_path).base.base
    forbidden = payload.get("forbidden_semantic_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMNoteWordBoxError("TM page-48 forbidden semantic inputs drifted")
    footer_ratio = _positive(geometry, "page_footer_top_ratio")
    if footer_ratio >= 1:
        raise TMNoteWordBoxError("TM page-48 footer ratio must be below one")
    return TMPage48Policy(
        source_path=path,
        document=str(payload.get("document", "")),
        page_number=48,
        page_tag="page-0048",
        scope="CONSOLIDATED",
        scope_binding=str(payload.get("scope_binding", "")),
        source_pdf_sha256=str(hashes[0]),
        source_render_sha256=str(hashes[1]),
        source_ocr_sha256=str(hashes[2]),
        minimum_line_score=float(thresholds[0]),
        minimum_anchor_similarity=float(thresholds[1]),
        minimum_unit_similarity=float(thresholds[2]),
        unit_anchors=_anchors(unit.get("anchors"), "unit"),
        canonical_unit=canonical,
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
        artifact_minimum_x_ratio=_positive(geometry, "artifact_minimum_x_ratio"),
        page_footer_top_ratio=footer_ratio,
        dash_config={str(key): value for key, value in dash_config.items()},
        dash_config_path=dash_path,
        tables=tuple(tables),
        auxiliary=TMPage48AuxiliarySpec(
            title_anchors=_anchors(auxiliary.get("title_anchors"), "auxiliary title"),
            axis_label_anchors=_anchors(auxiliary.get("axis_label_anchors"), "auxiliary axis"),
            unit_anchors=_anchors(auxiliary.get("unit_anchors"), "auxiliary unit"),
            first_row_anchors=_anchors(auxiliary.get("first_row_anchors"), "auxiliary first row"),
            total_row_anchors=_anchors(auxiliary.get("total_row_anchors"), "auxiliary total"),
            expected_driver_rows=driver_rows,
            expected_total_rows=total_rows,
            numeric_axis_max_distance_line_heights=_positive(
                auxiliary, "numeric_axis_max_distance_line_heights"
            ),
            label_attach_line_heights=_positive(auxiliary, "label_attach_line_heights"),
        ),
        forbidden_semantic_inputs=tuple(str(value) for value in forbidden),
    )


def _parse_narrative_quantities(
    lines: tuple[Any, ...],
    title: Any,
    header: Any,
    policy: TMPage48Policy,
) -> tuple[TMPage48NarrativeQuantity, ...]:
    narrative = tuple(line for line in lines if title.y_center < line.y_center < header.y_center)
    joined = normalize_text(" ".join(line.text for line in narrative))
    grouped = _GROUPED_NUMBER.findall(joined)
    percentages = _PERCENTAGE.findall(joined)
    if grouped != ["1.027.841"] or percentages != ["15,40%"]:
        raise TMNoteWordBoxError("TM page-48 narrative quantities drifted")
    amount = parse_financial_number(grouped[0])
    if amount.observation is not ObservationKind.VALUE or amount.value is None:
        raise TMNoteWordBoxError("TM page-48 narrative amount is invalid")
    source_indices = tuple(line.index for line in narrative)
    source_bbox = _union(list(narrative))
    return (
        TMPage48NarrativeQuantity(
            quantity_id="page-0048:variance:narrative-change",
            semantic_role="DISCLOSED_PROFIT_AFTER_TAX_CHANGE",
            raw_text=grouped[0],
            value=amount.value,
            canonical_unit=policy.canonical_unit,
            unit_multiplier=policy.unit_multiplier,
            source_line_indices=source_indices,
            source_bbox=source_bbox,
            mapping_approved=False,
        ),
        TMPage48NarrativeQuantity(
            quantity_id="page-0048:variance:narrative-percentage",
            semantic_role="DISCLOSED_CHANGE_PERCENTAGE",
            raw_text=percentages[0],
            value=Decimal(percentages[0][:-1].replace(",", ".")),
            canonical_unit="PERCENT",
            unit_multiplier=1,
            source_line_indices=source_indices,
            source_bbox=source_bbox,
            mapping_approved=False,
        ),
    )


def _parse_auxiliary(
    lines: tuple[Any, ...],
    policy: TMPage48Policy,
    line_height: float,
    footer_top: float,
) -> tuple[
    TMPage48AuxiliaryAxis,
    tuple[TMPage48AuxiliaryRow, ...],
    tuple[TMPage48NarrativeQuantity, ...],
    BoundingBox,
    tuple[int, ...],
]:
    spec = policy.auxiliary
    title = _find_anchor_line(lines, spec.title_anchors, policy)
    number = _number_line(lines, "8", title, line_height)
    axis_label = _find_anchor_line(lines, spec.axis_label_anchors, policy, minimum_y=title.y_center)
    unit = _find_anchor_line(lines, spec.unit_anchors, policy, minimum_y=axis_label.y_center)
    first_row = _find_anchor_line(lines, spec.first_row_anchors, policy, minimum_y=unit.y_center)
    total_row = _find_anchor_line(
        lines, spec.total_row_anchors, policy, minimum_y=first_row.y_center
    )
    header_lines = tuple(
        line
        for line in lines
        if title.y_center < line.y_center <= unit.y_center
        and line.bbox.x0 > axis_label.bbox.x0 - line_height
        and line.bbox.x1 <= unit.bbox.x1 + line_height
        and line.y_center >= axis_label.y_center - line_height
    )
    if {axis_label.index, unit.index} - {line.index for line in header_lines}:
        raise TMNoteWordBoxError("TM page-48 auxiliary header is incomplete")
    axis = TMPage48AuxiliaryAxis(
        axis_id="profit-after-tax-variance",
        semantic_role="AUXILIARY_CURRENT_MINUS_COMPARATIVE_EFFECT",
        raw_header_text=normalize_text(" | ".join(line.text for line in header_lines)),
        header_line_indices=tuple(line.index for line in header_lines),
        canonical_unit=policy.canonical_unit,
        unit_multiplier=policy.unit_multiplier,
        header_bbox=_union(list(header_lines)),
        unit_bbox=unit.bbox,
        comparison_basis="VISIBLE_NARRATIVE_Q1_2026_VERSUS_Q1_2025",
        mapping_approved=False,
    )
    body = tuple(line for line in lines if unit.bbox.y1 < line.y_center < footer_top)
    numeric = tuple(
        line
        for line in body
        if _numeric_only(line.text)
        and abs(line.x_right - unit.x_right)
        <= line_height * spec.numeric_axis_max_distance_line_heights
    )
    groups = _clusters(list(numeric), line_height * 0.30)
    expected_rows = spec.expected_driver_rows + spec.expected_total_rows
    if len(groups) != expected_rows or any(len(group) != 1 for group in groups):
        raise TMNoteWordBoxError("TM page-48 auxiliary numeric denominator drifted")
    centers = [statistics.fmean(line.y_center for line in group) for group in groups]
    labels = tuple(
        line
        for line in body
        if not _numeric_only(line.text)
        and line.x_right < axis_label.bbox.x0
        and first_row.y_center - line_height <= line.y_center <= total_row.y_center + line_height
    )
    assignments: dict[int, int] = {}
    for label in labels:
        forward = [
            index
            for index, center in enumerate(centers)
            if center >= label.y_center - line_height * 0.35
        ]
        closest = forward[0] if forward else len(centers) - 1
        if abs(label.y_center - centers[closest]) <= line_height * spec.label_attach_line_heights:
            assignments[label.index] = closest
    rows = []
    for ordinal, (group, _center) in enumerate(zip(groups, centers, strict=True), start=1):
        row_labels = tuple(
            sorted(
                (line for line in labels if assignments.get(line.index) == ordinal - 1),
                key=lambda line: (line.y_center, line.bbox.x0),
            )
        )
        if not row_labels:
            raise TMNoteWordBoxError("TM page-48 auxiliary row label is detached")
        parsed = parse_financial_number(group[0].text)
        if (
            parsed.observation not in {ObservationKind.VALUE, ObservationKind.ZERO}
            or parsed.value is None
        ):
            raise TMNoteWordBoxError("TM page-48 auxiliary numeric value is invalid")
        role = "TOTAL" if total_row.index in {line.index for line in row_labels} else "DRIVER"
        source_lines = [*row_labels, *group]
        rows.append(
            TMPage48AuxiliaryRow(
                row_id=f"page-0048:variance:row-{ordinal:04d}",
                ordinal=ordinal,
                label=normalize_text(" ".join(line.text for line in row_labels)),
                value=parsed.value,
                observation=parsed.observation,
                source_role=role,
                label_bbox=_union(list(row_labels)),
                value_bbox=group[0].bbox,
                label_line_indices=tuple(line.index for line in row_labels),
                value_line_indices=(group[0].index,),
                source_row_ids=_source_ids("page-0048", source_lines),
                mapping_approved=False,
            )
        )
    if (
        sum(row.source_role == "DRIVER" for row in rows) != spec.expected_driver_rows
        or sum(row.source_role == "TOTAL" for row in rows) != spec.expected_total_rows
    ):
        raise TMNoteWordBoxError("TM page-48 auxiliary row roles drifted")
    narrative = _parse_narrative_quantities(lines, title, axis_label, policy)
    used_numeric = {line.index for group in groups for line in group}
    unassigned = tuple(
        sorted(
            line.index
            for line in body
            if _numeric_only(line.text) and line.index not in used_numeric
        )
    )
    bbox = _union([number, title, *header_lines, *body])
    return axis, tuple(rows), narrative, bbox, unassigned


def parse_tm_page48(
    result_path: Path,
    source_image_path: Path,
    policy: TMPage48Policy,
    *,
    page_tag: str = "page-0048",
) -> ParsedTMPage48:
    if page_tag != policy.page_tag:
        raise TMNoteWordBoxError("TM page-48 page tag drifted")
    if sha256_file(result_path) != policy.source_ocr_sha256:
        raise TMNoteWordBoxError("TM page-48 OCR artifact hash drifted")
    if sha256_file(source_image_path) != policy.source_render_sha256:
        raise TMNoteWordBoxError("TM page-48 source render hash drifted")
    source_image = cv2.imread(str(source_image_path), cv2.IMREAD_GRAYSCALE)
    if source_image is None:
        raise TMNoteWordBoxError("TM page-48 source render cannot be decoded")
    input_path, lines, _metadata = _load_lines(result_path, policy.minimum_line_score)
    line_height = float(statistics.median(line.height for line in lines))
    if line_height <= 0:
        raise TMNoteWordBoxError("TM page-48 line height is invalid")
    source_bbox = _union(lines)
    footer_top = source_bbox.y1 * policy.page_footer_top_ratio
    titles = tuple(_find_anchor_line(lines, spec.title_anchors, policy) for spec in policy.tables)
    if tuple(title.y_center for title in titles) != tuple(
        sorted(title.y_center for title in titles)
    ):
        raise TMNoteWordBoxError("TM page-48 financial note order drifted")
    tables = []
    unassigned = []
    artifacts = []
    for ordinal, (spec, title) in enumerate(zip(policy.tables, titles, strict=True), start=1):
        body_end = _find_anchor_line(
            lines, spec.body_end_anchors, policy, minimum_y=title.y_center
        ).bbox.y0
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
        wrapped = tuple(
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
        table, table_unassigned, table_artifacts = _reconstruct_table(
            lines,
            spec,
            title,
            axes,
            headings,
            wrapped,
            body_end,
            policy,
            line_height,
            source_image,
            source_image_path,
            page_tag=page_tag,
            table_ordinal=ordinal,
            section_title=None,
        )
        tables.append(table)
        unassigned.extend(table_unassigned)
        artifacts.extend(table_artifacts)
    axis_semantics = tuple(
        (
            axis.current_or_comparative,
            axis.period_start,
            axis.period_end,
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
                axis.canonical_unit,
                axis.unit_multiplier,
            )
            for axis in table.axes
        )
        != axis_semantics
        for table in tables[1:]
    ):
        raise TMNoteWordBoxError("TM page-48 duration headers disagree semantically")
    auxiliary_axis, auxiliary_rows, narrative, auxiliary_bbox, aux_unassigned = _parse_auxiliary(
        lines, policy, line_height, footer_top
    )
    rows = tuple(row for table in tables for row in table.rows)
    footer = tuple(
        sorted(
            line.index for line in lines if line.y_center >= footer_top and _numeric_only(line.text)
        )
    )
    result = ParsedTMPage48(
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
        auxiliary_axis=auxiliary_axis,
        auxiliary_rows=auxiliary_rows,
        narrative_quantities=narrative,
        line_height=line_height,
        source_ocr_bbox=source_bbox,
        table_bbox=BoundingBox(
            min(table.bbox.x0 for table in tables),
            min(table.bbox.y0 for table in tables),
            max(table.bbox.x1 for table in tables),
            max(table.bbox.y1 for table in tables),
        ),
        auxiliary_bbox=auxiliary_bbox,
        unassigned_numeric_line_indices=tuple(sorted(set(unassigned) | set(aux_unassigned))),
        excluded_artifact_line_indices=tuple(sorted(set(artifacts))),
        excluded_footer_numeric_line_indices=footer,
        mapping_authority=False,
        evidence=(
            "notes 6 and 7 reconstructed as two complete dual-duration financial tables",
            "19 VALUE cells plus one pixel-backed DASH preserved without value imputation",
            "note 8 retained separately as 11 auxiliary variance values and two narrative quantities",
            "auxiliary and narrative quantities grant no ReportNormId mapping authority",
        ),
    )
    if (
        len(result.rows) != 13
        or result.numeric_row_count != 10
        or result.label_only_row_count != 3
        or result.financial_slot_count != 20
        or result.observation_count(ObservationKind.VALUE) != 19
        or result.observation_count(ObservationKind.DASH) != 1
        or len(result.auxiliary_rows) != 11
        or len(result.narrative_quantities) != 2
        or result.total_logical_row_count != 24
        or result.unassigned_numeric_line_indices
        or result.excluded_artifact_line_indices
        or result.excluded_footer_numeric_line_indices != (78,)
    ):
        raise TMNoteWordBoxError("TM page-48 exact source denominator drifted")
    return result


__all__ = [
    "ParsedTMPage48",
    "TMPage48AuxiliaryAxis",
    "TMPage48AuxiliaryRow",
    "TMPage48NarrativeQuantity",
    "TMPage48Policy",
    "load_tm_page48_policy",
    "parse_tm_page48",
]
