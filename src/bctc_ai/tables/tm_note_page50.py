"""Hash-bound mixed-period TM reconstruction for MBB consolidated PDF page 50.

The page contains two income-tax notes with duration axes and one cash-equivalent
note with snapshot axes.  The tax-rate sentence is retained outside the financial
cell denominator.  A visibly printed dash is accepted only with pixel evidence.
"""

from __future__ import annotations

import itertools
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
_PERCENTAGE = re.compile(r"(?<!\d)(\d{1,3}(?:[,.]\d+)?)%(?!\d)")
_REQUIRED_FORBIDDEN = {
    "missing_ocr_cell_as_dash_without_pixel_evidence",
    "template_labels_as_row_reconstruction_input",
    "approved_report_norm_id_assignment",
    "historical_or_mongodb_values",
    "human_review_answers",
    "dash_as_zero",
    "accounting_equations_as_value_imputation",
    "narrative_tax_rate_as_financial_statement_value",
}


@dataclass(frozen=True)
class TMPage50RowSpec:
    label_lines: tuple[tuple[str, ...], ...]
    source_role: str
    dash_axis: int | None


@dataclass(frozen=True)
class TMPage50StructuralSpec:
    source_role: str
    label_lines: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class TMPage50NarrativeSpec:
    semantic_role: str
    label_lines: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class TMPage50TableSpec:
    table_key: str
    note_number: str
    title_anchors: tuple[str, ...]
    body_end_anchors: tuple[str, ...]
    axis_kind: str
    expected_numeric_rows: int
    expected_label_only_rows: int
    structural_rows: tuple[TMPage50StructuralSpec, ...]
    rows: tuple[TMPage50RowSpec, ...]


@dataclass(frozen=True)
class TMPage50Policy:
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
    duration_current_start: date
    duration_current_end: date
    duration_comparative_start: date
    duration_comparative_end: date
    snapshot_current: date
    snapshot_comparative: date
    row_anchor_cluster_line_heights: float
    wrapped_label_max_gap_line_heights: float
    artifact_minimum_x_ratio: float
    page_footer_top_ratio: float
    dash_config: dict[str, float | int]
    dash_config_path: Path
    tables: tuple[TMPage50TableSpec, ...]
    narratives: tuple[TMPage50NarrativeSpec, ...]
    forbidden_semantic_inputs: tuple[str, ...]


@dataclass(frozen=True)
class TMPage50AxisBinding:
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
class TMPage50LogicalRow:
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
class TMPage50Table:
    ordinal: int
    table_key: str
    note_number: str
    title: str
    title_line_indices: tuple[int, ...]
    axes: tuple[TMPage50AxisBinding, ...]
    rows: tuple[TMPage50LogicalRow, ...]
    bbox: BoundingBox


@dataclass(frozen=True)
class TMPage50NarrativeRecord:
    narrative_id: str
    semantic_role: str
    raw_text: str
    source_line_indices: tuple[int, ...]
    source_bbox: BoundingBox
    quantities: tuple[Decimal, ...]
    quantity_units: tuple[str, ...]
    mapping_approved: bool


@dataclass(frozen=True)
class ParsedTMPage50:
    input_path: str
    source_sha256: str
    source_render_sha256: str
    source_pdf_sha256: str
    page_tag: str
    scope: str
    scope_binding: str
    axes: tuple[TMPage50AxisBinding, ...]
    tables: tuple[TMPage50Table, ...]
    rows: tuple[TMPage50LogicalRow, ...]
    narratives: tuple[TMPage50NarrativeRecord, ...]
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

    @property
    def narrative_quantity_count(self) -> int:
        return sum(len(record.quantities) for record in self.narratives)


def _anchors(payload: Any, field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(payload, list) or (not payload and not allow_empty):
        raise TMNoteWordBoxError(f"TM page-50 {field} anchors are invalid")
    result = tuple(retrieval_key(str(value)) for value in payload)
    if any(not value for value in result):
        raise TMNoteWordBoxError(f"TM page-50 {field} contains an empty anchor")
    return result


def _anchor_groups(
    payload: Any, field: str, *, allow_empty: bool = False
) -> tuple[tuple[str, ...], ...]:
    if not isinstance(payload, list) or (not payload and not allow_empty):
        raise TMNoteWordBoxError(f"TM page-50 {field} label groups are invalid")
    return tuple(_anchors(group, f"{field} line") for group in payload)


def _date_value(payload: dict[str, Any], field: str) -> date:
    value = payload.get(field)
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise TMNoteWordBoxError(f"invalid TM page-50 {field}") from exc
    raise TMNoteWordBoxError(f"invalid TM page-50 {field}")


def _positive(payload: dict[str, Any], field: str, *, below_one: bool = False) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise TMNoteWordBoxError(f"invalid positive TM page-50 setting: {field}")
    result = float(value)
    if below_one and result >= 1:
        raise TMNoteWordBoxError(f"TM page-50 {field} must be below one")
    return result


def load_tm_page50_policy(path: Path) -> TMPage50Policy:
    """Load the source-scoped reconstruction contract for PDF page 50."""

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMNoteWordBoxError(f"cannot load TM page-50 policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE50_MIXED_PERIOD_FIXED_GRID_DASH_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 50
        or payload.get("page_tag") != "page-0050"
        or payload.get("scope") != "CONSOLIDATED"
    ):
        raise TMNoteWordBoxError("TM page-50 policy identity drifted")
    hashes = tuple(
        payload.get(field)
        for field in ("source_pdf_sha256", "source_render_sha256", "source_ocr_sha256")
    )
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMNoteWordBoxError("TM page-50 source hashes are invalid")
    thresholds = tuple(
        payload.get(field)
        for field in ("minimum_line_score", "minimum_anchor_similarity", "minimum_unit_similarity")
    )
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1
        for value in thresholds
    ):
        raise TMNoteWordBoxError("TM page-50 similarity thresholds are invalid")
    unit = payload.get("unit")
    reporting = payload.get("reporting_period")
    geometry = payload.get("table_geometry")
    if not all(isinstance(value, dict) for value in (unit, reporting, geometry)):
        raise TMNoteWordBoxError("TM page-50 period/unit/geometry policy is incomplete")
    multiplier = unit.get("multiplier")
    canonical = unit.get("canonical")
    if (
        isinstance(multiplier, bool)
        or not isinstance(multiplier, int)
        or multiplier <= 0
        or not isinstance(canonical, str)
        or not canonical
    ):
        raise TMNoteWordBoxError("TM page-50 unit binding is invalid")
    dash_name = payload.get("dash_detector_config")
    if not isinstance(dash_name, str) or Path(dash_name).name != dash_name:
        raise TMNoteWordBoxError("TM page-50 dash-detector path is invalid")
    dash_path = (path.parent / dash_name).resolve()
    if not dash_path.is_file() or sha256_file(dash_path) != payload.get(
        "dash_detector_config_sha256"
    ):
        raise TMNoteWordBoxError("TM page-50 dash detector is absent or drifted")
    raw_tables = payload.get("tables")
    if not isinstance(raw_tables, list) or len(raw_tables) != 3:
        raise TMNoteWordBoxError("TM page-50 must define three complete visible notes")
    tables = []
    for record in raw_tables:
        if not isinstance(record, dict):
            raise TMNoteWordBoxError("TM page-50 table record is invalid")
        table_key = record.get("table_key")
        note_number = record.get("note_number")
        axis_kind = record.get("axis_kind")
        numeric_rows = record.get("expected_numeric_rows")
        label_rows = record.get("expected_label_only_rows")
        raw_rows = record.get("rows")
        raw_structural = record.get("structural_rows", [])
        if (
            not isinstance(table_key, str)
            or not table_key
            or not isinstance(note_number, str)
            or not note_number
            or axis_kind not in {"VISIBLE_DURATION", "END_DATE_DURATION", "SNAPSHOT"}
            or isinstance(numeric_rows, bool)
            or not isinstance(numeric_rows, int)
            or numeric_rows <= 0
            or isinstance(label_rows, bool)
            or not isinstance(label_rows, int)
            or label_rows <= 0
            or not isinstance(raw_rows, list)
            or len(raw_rows) != numeric_rows
            or not isinstance(raw_structural, list)
        ):
            raise TMNoteWordBoxError("TM page-50 table denominator is invalid")
        rows = []
        for row in raw_rows:
            if not isinstance(row, dict) or not isinstance(row.get("source_role"), str):
                raise TMNoteWordBoxError("TM page-50 numeric-row record is invalid")
            dash_axis = row.get("dash_axis")
            if dash_axis is not None and dash_axis not in {1, 2}:
                raise TMNoteWordBoxError("TM page-50 dash axis is invalid")
            rows.append(
                TMPage50RowSpec(
                    label_lines=_anchor_groups(
                        row.get("label_lines"), "numeric row", allow_empty=True
                    ),
                    source_role=row["source_role"],
                    dash_axis=dash_axis,
                )
            )
        structural = []
        for row in raw_structural:
            if not isinstance(row, dict) or not isinstance(row.get("source_role"), str):
                raise TMNoteWordBoxError("TM page-50 structural-row record is invalid")
            structural.append(
                TMPage50StructuralSpec(
                    source_role=row["source_role"],
                    label_lines=_anchor_groups(row.get("label_lines"), "structural row"),
                )
            )
        if label_rows != len(structural) + 1:
            raise TMNoteWordBoxError("TM page-50 label-only denominator drifted")
        tables.append(
            TMPage50TableSpec(
                table_key=table_key,
                note_number=note_number,
                title_anchors=_anchors(record.get("title_anchors"), "table title"),
                body_end_anchors=_anchors(
                    record.get("body_end_anchors", []), "body end", allow_empty=True
                ),
                axis_kind=axis_kind,
                expected_numeric_rows=numeric_rows,
                expected_label_only_rows=label_rows,
                structural_rows=tuple(structural),
                rows=tuple(rows),
            )
        )
    if [table.table_key for table in tables] != [
        "TAX_EXPENSE",
        "TAX_RECONCILIATION",
        "CASH_EQUIVALENTS",
    ] or [table.expected_numeric_rows for table in tables] != [5, 10, 4]:
        raise TMNoteWordBoxError("TM page-50 table order or denominator drifted")
    raw_narratives = payload.get("narratives")
    if not isinstance(raw_narratives, list) or len(raw_narratives) != 3:
        raise TMNoteWordBoxError("TM page-50 narrative provenance is incomplete")
    narratives = []
    for record in raw_narratives:
        if not isinstance(record, dict) or not isinstance(record.get("semantic_role"), str):
            raise TMNoteWordBoxError("TM page-50 narrative record is invalid")
        narratives.append(
            TMPage50NarrativeSpec(
                semantic_role=record["semantic_role"],
                label_lines=_anchor_groups(record.get("label_lines"), "narrative"),
            )
        )
    if [record.semantic_role for record in narratives] != [
        "NOTE_11_SECTION_TITLE",
        "STATUTORY_TAX_RATE",
        "CASH_EQUIVALENT_DEFINITION",
    ]:
        raise TMNoteWordBoxError("TM page-50 narrative roles drifted")
    forbidden = payload.get("forbidden_semantic_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMNoteWordBoxError("TM page-50 forbidden semantic inputs drifted")
    dash_config = load_word_box_reconstruction_v3_config(dash_path).base.base
    return TMPage50Policy(
        source_path=path,
        document=str(payload.get("document", "")),
        page_number=50,
        page_tag="page-0050",
        scope="CONSOLIDATED",
        scope_binding=str(payload.get("scope_binding", "")),
        source_pdf_sha256=hashes[0],
        source_render_sha256=hashes[1],
        source_ocr_sha256=hashes[2],
        minimum_line_score=float(thresholds[0]),
        minimum_anchor_similarity=float(thresholds[1]),
        minimum_unit_similarity=float(thresholds[2]),
        unit_anchors=_anchors(unit.get("anchors"), "unit"),
        canonical_unit=canonical,
        unit_multiplier=multiplier,
        duration_current_start=_date_value(reporting, "duration_current_start"),
        duration_current_end=_date_value(reporting, "duration_current_end"),
        duration_comparative_start=_date_value(reporting, "duration_comparative_start"),
        duration_comparative_end=_date_value(reporting, "duration_comparative_end"),
        snapshot_current=_date_value(reporting, "snapshot_current"),
        snapshot_comparative=_date_value(reporting, "snapshot_comparative"),
        row_anchor_cluster_line_heights=_positive(geometry, "row_anchor_cluster_line_heights"),
        wrapped_label_max_gap_line_heights=_positive(
            geometry, "wrapped_label_max_gap_line_heights"
        ),
        artifact_minimum_x_ratio=_positive(geometry, "artifact_minimum_x_ratio", below_one=True),
        page_footer_top_ratio=_positive(geometry, "page_footer_top_ratio", below_one=True),
        dash_config={str(key): value for key, value in dash_config.items()},
        dash_config_path=dash_path,
        tables=tuple(tables),
        narratives=tuple(narratives),
        forbidden_semantic_inputs=tuple(str(value) for value in forbidden),
    )


def _find_title(
    lines: tuple[_Line, ...], spec: TMPage50TableSpec, policy: TMPage50Policy
) -> tuple[_Line, tuple[_Line, ...]]:
    number_key = retrieval_key(spec.note_number)
    candidates: list[tuple[float, float, _Line, tuple[_Line, ...]]] = []
    for line in lines:
        similarity = _best_anchor_similarity(line.text, spec.title_anchors)
        if similarity < policy.minimum_anchor_similarity:
            continue
        key = retrieval_key(line.text)
        if key.startswith(number_key):
            candidates.append((-similarity, line.y_center, line, (line,)))
            continue
        number_lines = tuple(
            number
            for number in lines
            if retrieval_key(number.text).rstrip(".") == number_key
            and number.bbox.x1 < line.bbox.x0
            and abs(number.y_center - line.y_center) <= line.height
        )
        if len(number_lines) == 1:
            candidates.append((-similarity, line.y_center, line, (number_lines[0], line)))
    if not candidates:
        raise TMNoteWordBoxError(f"TM page-50 note title is unresolved: {spec.note_number}")
    _score, _y, title, sources = min(candidates, key=lambda record: record[:2])
    return title, sources


def _find_anchor_group(
    lines: tuple[_Line, ...],
    anchors: tuple[tuple[str, ...], ...],
    policy: TMPage50Policy,
    line_height: float,
    *,
    minimum_y: float,
    maximum_y: float,
) -> tuple[_Line, ...]:
    if not anchors:
        return ()
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
        raise TMNoteWordBoxError(f"TM page-50 wrapped label is unresolved: {anchors}")
    candidates = []
    for combination in itertools.product(*choices):
        group = tuple(record[0] for record in combination)
        if len({line.index for line in group}) != len(group):
            continue
        if tuple(line.y_center for line in group) != tuple(sorted(line.y_center for line in group)):
            continue
        if any(
            right.y_center - left.y_center > line_height * policy.wrapped_label_max_gap_line_heights
            for left, right in zip(group, group[1:], strict=False)
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
        raise TMNoteWordBoxError("TM page-50 wrapped label lines are not locally adjacent")
    return min(candidates, key=lambda record: record[:3])[3]


def _axes(
    lines: tuple[_Line, ...],
    title: _Line,
    first_label: tuple[_Line, ...],
    spec: TMPage50TableSpec,
    policy: TMPage50Policy,
) -> tuple[TMPage50AxisBinding, ...]:
    body_top = min(line.bbox.y0 for line in first_label)
    candidates = tuple(line for line in lines if title.y_center < line.y_center < body_top)
    dates = tuple(line for line in candidates if parse_vietnamese_date(line.text) is not None)
    units = tuple(
        line
        for line in candidates
        if _best_anchor_similarity(line.text, policy.unit_anchors) >= policy.minimum_unit_similarity
    )
    if len(units) != 2:
        raise TMNoteWordBoxError(f"TM page-50 {spec.table_key} must expose two units")
    ordered_units = tuple(sorted(units, key=lambda line: line.x_right))
    assignments: dict[int, list[_Line]] = {line.index: [] for line in ordered_units}
    for date_line in dates:
        unit = min(ordered_units, key=lambda line: abs(line.x_center - date_line.x_center))
        assignments[unit.index].append(date_line)
    expected = (
        (
            "CURRENT",
            policy.duration_current_start,
            policy.duration_current_end,
            policy.snapshot_current,
        ),
        (
            "COMPARATIVE",
            policy.duration_comparative_start,
            policy.duration_comparative_end,
            policy.snapshot_comparative,
        ),
    )
    result = []
    for ordinal, (unit, (role, duration_start, duration_end, snapshot)) in enumerate(
        zip(ordered_units, expected, strict=True), start=1
    ):
        local_dates = tuple(sorted(assignments[unit.index], key=lambda line: line.y_center))
        parsed = tuple(parse_vietnamese_date(line.text) for line in local_dates)
        if None in parsed:
            raise TMNoteWordBoxError(f"TM page-50 {spec.table_key} has an invalid date")
        visible_dates = tuple(value for value in parsed if value is not None)
        if spec.axis_kind == "VISIBLE_DURATION":
            if len(visible_dates) != 2 or (min(visible_dates), max(visible_dates)) != (
                duration_start,
                duration_end,
            ):
                raise TMNoteWordBoxError("TM page-50 visible duration header drifted")
            start, end, period_type = duration_start, duration_end, "DURATION"
            period_evidence = "duration start/end parsed from the visible table-local header"
        elif spec.axis_kind == "END_DATE_DURATION":
            if visible_dates != (duration_end,):
                raise TMNoteWordBoxError("TM page-50 duration end-date header drifted")
            start, end, period_type = duration_start, duration_end, "DURATION"
            period_evidence = (
                "visible duration end date bound to the Q1 start date from immutable report context"
            )
        else:
            if visible_dates != (snapshot,):
                raise TMNoteWordBoxError("TM page-50 snapshot header drifted")
            start, end, period_type = snapshot, snapshot, "SNAPSHOT"
            period_evidence = "snapshot date parsed from the visible table-local header"
        header_lines = (*local_dates, unit)
        result.append(
            TMPage50AxisBinding(
                ordinal=ordinal,
                axis_id=f"{spec.table_key.lower()}-{role.lower()}",
                axis_right_edge=unit.x_right,
                raw_header_text=normalize_text(" | ".join(line.text for line in header_lines)),
                header_line_indices=tuple(line.index for line in header_lines),
                current_or_comparative=role,
                canonical_unit=policy.canonical_unit,
                unit_multiplier=policy.unit_multiplier,
                period_start=start,
                period_end=end,
                period_type=period_type,
                header_bbox=_union(list(header_lines)),
                unit_bbox=unit.bbox,
                evidence=(
                    period_evidence,
                    "current/comparative role bound by visible horizontal order",
                    "VND million multiplier matched from the visible table-local unit",
                ),
            )
        )
    return tuple(result)


def _logical_row(
    *,
    page_tag: str,
    table_key: str,
    note_number: str,
    source_role: str,
    label_lines: tuple[_Line, ...],
    value_lines: tuple[tuple[_Line, ...], ...],
    visual: tuple[VisualCellEvidence | None, ...],
    axes: tuple[TMPage50AxisBinding, ...],
    y_anchor: float,
    row_kind: TMNoteRowKind,
) -> TMPage50LogicalRow:
    cells = tuple(
        parse_financial_number(
            "-" if evidence is not None and not lines else " ".join(line.text for line in lines)
        )
        for lines, evidence in zip(value_lines, visual, strict=True)
    )
    sources = [*label_lines, *(line for group in value_lines for line in group)]
    return TMPage50LogicalRow(
        row_id="",
        table_key=table_key,
        note_number=note_number,
        ordinal=0,
        row=ReaderRow(
            source_row_ids=_source_ids(page_tag, sources),
            label=normalize_text(" ".join(line.text for line in label_lines)),
            note_reference=note_number,
            cells=cells,
        ),
        row_kind=row_kind,
        source_role=source_role,
        y_anchor=y_anchor,
        label_bbox=_union(list(label_lines)) if label_lines else None,
        value_bboxes=tuple(
            _union(list(lines))
            if lines
            else BoundingBox(*evidence.component_box)
            if evidence is not None
            else None
            for lines, evidence in zip(value_lines, visual, strict=True)
        ),
        label_line_indices=tuple(line.index for line in label_lines),
        value_line_indices=tuple(tuple(line.index for line in group) for group in value_lines),
        visual_cell_evidence=visual,
        cell_period_starts=tuple(
            axis.period_start if row_kind is TMNoteRowKind.NUMERIC else None for axis in axes
        ),
        cell_period_ends=tuple(
            axis.period_end if row_kind is TMNoteRowKind.NUMERIC else None for axis in axes
        ),
        cell_period_roles=tuple(
            axis.current_or_comparative if row_kind is TMNoteRowKind.NUMERIC else None
            for axis in axes
        ),
        mapping_approved=False,
    )


def _renumber(
    rows: list[TMPage50LogicalRow], *, page_tag: str, table_key: str
) -> tuple[TMPage50LogicalRow, ...]:
    result = []
    for ordinal, row in enumerate(sorted(rows, key=lambda item: item.y_anchor), start=1):
        result.append(
            TMPage50LogicalRow(
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


def _narrative_records(
    lines: tuple[_Line, ...], policy: TMPage50Policy, line_height: float, footer_top: float
) -> tuple[TMPage50NarrativeRecord, ...]:
    result = []
    for ordinal, spec in enumerate(policy.narratives, start=1):
        group = _find_anchor_group(
            lines,
            spec.label_lines,
            policy,
            line_height,
            minimum_y=float("-inf"),
            maximum_y=footer_top,
        )
        raw_text = normalize_text(" ".join(line.text for line in group))
        quantities: tuple[Decimal, ...] = ()
        units: tuple[str, ...] = ()
        if spec.semantic_role == "STATUTORY_TAX_RATE":
            matches = _PERCENTAGE.findall(raw_text)
            if len(matches) != 1:
                raise TMNoteWordBoxError("TM page-50 statutory tax rate drifted")
            quantities = (Decimal(matches[0].replace(",", ".")),)
            units = ("PERCENT",)
        result.append(
            TMPage50NarrativeRecord(
                narrative_id=f"{policy.page_tag}:narrative-{ordinal:04d}",
                semantic_role=spec.semantic_role,
                raw_text=raw_text,
                source_line_indices=tuple(line.index for line in group),
                source_bbox=_union(list(group)),
                quantities=quantities,
                quantity_units=units,
                mapping_approved=False,
            )
        )
    return tuple(result)


def _reconstruct_table(
    lines: tuple[_Line, ...],
    spec: TMPage50TableSpec,
    title: _Line,
    title_sources: tuple[_Line, ...],
    body_end: float,
    policy: TMPage50Policy,
    line_height: float,
    source_image: Any,
    source_image_path: Path,
    *,
    page_tag: str,
    table_ordinal: int,
) -> tuple[TMPage50Table, tuple[int, ...], tuple[int, ...]]:
    ordered_labels: list[tuple[_Line, ...]] = []
    minimum_label_y = title.y_center
    for row in spec.rows:
        group = _find_anchor_group(
            lines,
            row.label_lines,
            policy,
            line_height,
            minimum_y=minimum_label_y,
            maximum_y=body_end,
        )
        ordered_labels.append(group)
        if group:
            minimum_label_y = max(line.y_center for line in group)
    labels = tuple(ordered_labels)
    first_label = next(group for group in labels if group)
    axes = _axes(lines, title, first_label, spec, policy)
    body_start = max(axis.unit_bbox.y1 for axis in axes)
    numeric_lines = [
        line for line in lines if body_start < line.y_center < body_end and _numeric_only(line.text)
    ]
    groups = tuple(
        tuple(sorted(group, key=lambda line: line.x_right))
        for group in _clusters(numeric_lines, line_height * policy.row_anchor_cluster_line_heights)
    )
    if len(groups) != spec.expected_numeric_rows:
        raise TMNoteWordBoxError(
            f"TM page-50 {spec.table_key} numeric denominator drifted: "
            f"{len(groups)} != {spec.expected_numeric_rows}"
        )
    rows: list[TMPage50LogicalRow] = []
    used_numeric: set[int] = set()
    for numeric_ordinal, (row_spec, label_lines, group) in enumerate(
        zip(spec.rows, labels, groups, strict=True), start=1
    ):
        center = statistics.fmean(line.y_center for line in group)
        per_axis: list[list[_Line]] = [[], []]
        for line in group:
            axis_index = min(
                range(2), key=lambda index: abs(axes[index].axis_right_edge - line.x_right)
            )
            per_axis[axis_index].append(line)
            used_numeric.add(line.index)
        if any(len(grouped) > 1 for grouped in per_axis):
            raise TMNoteWordBoxError(f"TM page-50 {spec.table_key} has a split numeric cell")
        visual: list[VisualCellEvidence | None] = [None, None]
        if row_spec.dash_axis is not None:
            dash_index = row_spec.dash_axis - 1
            if per_axis[dash_index]:
                raise TMNoteWordBoxError(f"TM page-50 {spec.table_key} dash axis contains OCR text")
            evidence = _detect_visible_dash_v3(
                source_image,
                source_image_path=source_image_path,
                axis_right_edge=axes[dash_index].axis_right_edge,
                anchor_center=center,
                line_height=line_height,
                config=policy.dash_config,
            )
            if evidence is None:
                raise TMNoteWordBoxError(
                    f"TM page-50 visible dash lacks constrained pixel evidence: {spec.table_key}"
                )
            visual[dash_index] = evidence
        logical = _logical_row(
            page_tag=page_tag,
            table_key=spec.table_key,
            note_number=spec.note_number,
            source_role=row_spec.source_role,
            label_lines=label_lines,
            value_lines=tuple(tuple(grouped) for grouped in per_axis),
            visual=tuple(visual),
            axes=axes,
            y_anchor=center,
            row_kind=TMNoteRowKind.NUMERIC,
        )
        if any(
            cell.observation
            not in {ObservationKind.VALUE, ObservationKind.ZERO, ObservationKind.DASH}
            for cell in logical.row.cells
        ):
            raise TMNoteWordBoxError(
                f"TM page-50 {spec.table_key} row {numeric_ordinal} has an unresolved cell"
            )
        rows.append(logical)
    rows.append(
        _logical_row(
            page_tag=page_tag,
            table_key=spec.table_key,
            note_number=spec.note_number,
            source_role="NOTE_TITLE",
            label_lines=title_sources,
            value_lines=((), ()),
            visual=(None, None),
            axes=axes,
            y_anchor=title.y_center,
            row_kind=TMNoteRowKind.LABEL_ONLY,
        )
    )
    for structural in spec.structural_rows:
        label_lines = _find_anchor_group(
            lines,
            structural.label_lines,
            policy,
            line_height,
            minimum_y=body_start,
            maximum_y=body_end,
        )
        rows.append(
            _logical_row(
                page_tag=page_tag,
                table_key=spec.table_key,
                note_number=spec.note_number,
                source_role=structural.source_role,
                label_lines=label_lines,
                value_lines=((), ()),
                visual=(None, None),
                axes=axes,
                y_anchor=statistics.fmean(line.y_center for line in label_lines),
                row_kind=TMNoteRowKind.LABEL_ONLY,
            )
        )
    final_rows = _renumber(rows, page_tag=page_tag, table_key=spec.table_key)
    counts = (
        sum(row.row_kind is TMNoteRowKind.NUMERIC for row in final_rows),
        sum(row.row_kind is TMNoteRowKind.LABEL_ONLY for row in final_rows),
    )
    if counts != (spec.expected_numeric_rows, spec.expected_label_only_rows):
        raise TMNoteWordBoxError(f"TM page-50 {spec.table_key} row denominator drifted")
    used_indices = {
        *(line.index for line in title_sources),
        *(index for axis in axes for index in axis.header_line_indices),
        *(
            int(source_id.rsplit("-", 1)[-1])
            for row in final_rows
            for source_id in row.row.source_row_ids
        ),
    }
    table_lines = [line for line in lines if line.index in used_indices]
    artifacts = tuple(
        sorted(
            line.index
            for line in lines
            if body_start < line.y_center < body_end
            and not _numeric_only(line.text)
            and line.bbox.x0 / _union(lines).x1 >= policy.artifact_minimum_x_ratio
        )
    )
    return (
        TMPage50Table(
            ordinal=table_ordinal,
            table_key=spec.table_key,
            note_number=spec.note_number,
            title=title.text,
            title_line_indices=tuple(line.index for line in title_sources),
            axes=axes,
            rows=final_rows,
            bbox=_union(table_lines),
        ),
        tuple(sorted(used_numeric)),
        artifacts,
    )


def parse_tm_page50(
    result_path: Path,
    source_image_path: Path,
    policy: TMPage50Policy,
    *,
    page_tag: str = "page-0050",
) -> ParsedTMPage50:
    """Reconstruct page 50 without granting schema mapping authority."""

    if page_tag != policy.page_tag:
        raise TMNoteWordBoxError("TM page-50 page tag drifted")
    if sha256_file(result_path) != policy.source_ocr_sha256:
        raise TMNoteWordBoxError("TM page-50 OCR artifact hash drifted")
    if sha256_file(source_image_path) != policy.source_render_sha256:
        raise TMNoteWordBoxError("TM page-50 source render hash drifted")
    source_image = cv2.imread(str(source_image_path), cv2.IMREAD_GRAYSCALE)
    if source_image is None:
        raise TMNoteWordBoxError("TM page-50 source render cannot be decoded")
    input_path, lines, _metadata = _load_lines(result_path, policy.minimum_line_score)
    line_height = float(statistics.median(line.height for line in lines))
    if line_height <= 0:
        raise TMNoteWordBoxError("TM page-50 line height is invalid")
    source_bbox = _union(lines)
    footer_top = source_bbox.y1 * policy.page_footer_top_ratio
    title_records = tuple(_find_title(lines, spec, policy) for spec in policy.tables)
    titles = tuple(record[0] for record in title_records)
    if tuple(title.y_center for title in titles) != tuple(
        sorted(title.y_center for title in titles)
    ):
        raise TMNoteWordBoxError("TM page-50 note-title order drifted")
    tables = []
    used_numeric: set[int] = set()
    artifacts: set[int] = set()
    numeric_candidates: set[int] = set()
    for ordinal, (spec, (title, title_sources)) in enumerate(
        zip(policy.tables, title_records, strict=True), start=1
    ):
        body_end = titles[ordinal].bbox.y0 if ordinal < len(titles) else footer_top
        if spec.body_end_anchors:
            next_title = titles[ordinal]
            if (
                _best_anchor_similarity(next_title.text, spec.body_end_anchors)
                < policy.minimum_anchor_similarity
            ):
                raise TMNoteWordBoxError(f"TM page-50 {spec.table_key} body end drifted")
        table, table_numeric, table_artifacts = _reconstruct_table(
            lines,
            spec,
            title,
            title_sources,
            body_end,
            policy,
            line_height,
            source_image,
            source_image_path,
            page_tag=page_tag,
            table_ordinal=ordinal,
        )
        tables.append(table)
        used_numeric.update(table_numeric)
        artifacts.update(table_artifacts)
        body_start = max(axis.unit_bbox.y1 for axis in table.axes)
        numeric_candidates.update(
            line.index
            for line in lines
            if body_start < line.y_center < body_end and _numeric_only(line.text)
        )
    footer = tuple(
        sorted(
            line.index for line in lines if line.y_center >= footer_top and _numeric_only(line.text)
        )
    )
    unassigned = tuple(sorted(numeric_candidates - used_numeric - artifacts))
    rows = tuple(row for table in tables for row in table.rows)
    axes = tuple(axis for table in tables for axis in table.axes)
    narratives = _narrative_records(lines, policy, line_height, footer_top)
    result = ParsedTMPage50(
        input_path=input_path,
        source_sha256=policy.source_ocr_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_pdf_sha256=policy.source_pdf_sha256,
        page_tag=page_tag,
        scope=policy.scope,
        scope_binding=policy.scope_binding,
        axes=axes,
        tables=tuple(tables),
        rows=rows,
        narratives=narratives,
        line_height=line_height,
        source_ocr_bbox=source_bbox,
        table_bbox=BoundingBox(
            min(table.bbox.x0 for table in tables),
            min(table.bbox.y0 for table in tables),
            max(table.bbox.x1 for table in tables),
            max(table.bbox.y1 for table in tables),
        ),
        unassigned_numeric_line_indices=unassigned,
        excluded_artifact_line_indices=tuple(sorted(artifacts)),
        excluded_footer_numeric_line_indices=footer,
        mapping_authority=False,
        evidence=(
            "notes 11.1, 11.2 and 12 are complete independent sections on immutable PDF page 50",
            "two duration tables and one snapshot table bind their visible local axes independently",
            "19 numeric rows retain 37 OCR values plus one pixel-backed DASH",
            "the narrative 20% tax rate is not promoted to a financial statement value",
            "schema identifiers are absent from parser inputs and mapping authority remains false",
        ),
    )
    if (
        len(result.rows) != 23
        or result.numeric_row_count != 19
        or result.label_only_row_count != 4
        or result.financial_slot_count != 38
        or result.observation_count(ObservationKind.VALUE) != 37
        or result.observation_count(ObservationKind.DASH) != 1
        or result.unassigned_numeric_line_indices
        or result.excluded_artifact_line_indices
        or result.excluded_footer_numeric_line_indices != (85,)
        or len(result.narratives) != 3
        or result.narrative_quantity_count != 1
    ):
        raise TMNoteWordBoxError(
            "TM page-50 exact source denominator drifted: "
            f"rows={len(result.rows)}, numeric={result.numeric_row_count}, "
            f"structural={result.label_only_row_count}, slots={result.financial_slot_count}, "
            f"value={result.observation_count(ObservationKind.VALUE)}, "
            f"dash={result.observation_count(ObservationKind.DASH)}, "
            f"unassigned={result.unassigned_numeric_line_indices}, "
            f"artifacts={result.excluded_artifact_line_indices}, footer={result.excluded_footer_numeric_line_indices}"
        )
    return result


__all__ = [
    "ParsedTMPage50",
    "TMPage50AxisBinding",
    "TMPage50LogicalRow",
    "TMPage50NarrativeRecord",
    "TMPage50Policy",
    "TMPage50Table",
    "load_tm_page50_policy",
    "parse_tm_page50",
]
