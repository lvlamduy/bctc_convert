"""Hash-bound mixed-axis TM reconstruction for MBB consolidated PDF page 49."""

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
class TMPage49TableSpec:
    table_key: str
    note_number: str
    title_anchors: tuple[str, ...]
    body_end_anchors: tuple[str, ...]
    axis_kind: str
    expected_numeric_rows: int
    expected_label_only_rows: int
    detail_label_groups: tuple[tuple[tuple[str, ...], ...], ...]
    dash_row_ordinal: int | None


@dataclass(frozen=True)
class TMPage49Policy:
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
    period_start: date
    period_end: date
    comparative_start: date
    comparative_end: date
    row_anchor_cluster_line_heights: float
    label_direct_attach_line_heights: float
    artifact_minimum_x_ratio: float
    page_footer_top_ratio: float
    dash_config: dict[str, float | int]
    dash_config_path: Path
    tables: tuple[TMPage49TableSpec, ...]
    forbidden_semantic_inputs: tuple[str, ...]


@dataclass(frozen=True)
class TMPage49AxisBinding:
    ordinal: int
    axis_id: str
    axis_role: str
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
class TMPage49LogicalRow:
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
class TMPage49Table:
    ordinal: int
    table_key: str
    note_number: str
    title: str
    title_line_indices: tuple[int, ...]
    axes: tuple[TMPage49AxisBinding, ...]
    rows: tuple[TMPage49LogicalRow, ...]
    bbox: BoundingBox


@dataclass(frozen=True)
class ParsedTMPage49:
    input_path: str
    source_sha256: str
    source_render_sha256: str
    source_pdf_sha256: str
    page_tag: str
    scope: str
    scope_binding: str
    axes: tuple[TMPage49AxisBinding, ...]
    tables: tuple[TMPage49Table, ...]
    rows: tuple[TMPage49LogicalRow, ...]
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
        raise TMNoteWordBoxError(f"TM page-49 {field} anchors are invalid")
    result = tuple(retrieval_key(str(value)) for value in payload)
    if any(not value for value in result):
        raise TMNoteWordBoxError(f"TM page-49 {field} contains an empty anchor")
    return result


def _anchor_groups(payload: Any, field: str) -> tuple[tuple[tuple[str, ...], ...], ...]:
    if not isinstance(payload, list) or not payload:
        raise TMNoteWordBoxError(f"TM page-49 {field} label groups are invalid")
    groups = []
    for group in payload:
        if not isinstance(group, list) or not group:
            raise TMNoteWordBoxError(f"TM page-49 {field} label group is invalid")
        groups.append(tuple(_anchors(line, f"{field} label line") for line in group))
    return tuple(groups)


def _bounded_float(payload: dict[str, Any], field: str, *, upper: float | None = None) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise TMNoteWordBoxError(f"invalid positive TM page-49 setting: {field}")
    result = float(value)
    if upper is not None and result >= upper:
        raise TMNoteWordBoxError(f"TM page-49 {field} exceeds its upper bound")
    return result


def _date_value(payload: dict[str, Any], field: str) -> date:
    value = payload.get(field)
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise TMNoteWordBoxError(f"invalid TM page-49 {field}") from exc
    raise TMNoteWordBoxError(f"invalid TM page-49 {field}")


def load_tm_page49_policy(path: Path) -> TMPage49Policy:
    """Load the exact source-scoped page-49 reconstruction contract."""

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMNoteWordBoxError(f"cannot load TM page-49 policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE49_MIXED_AXIS_FIXED_GRID_DASH_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 49
        or payload.get("page_tag") != "page-0049"
        or payload.get("scope") != "CONSOLIDATED"
    ):
        raise TMNoteWordBoxError("TM page-49 policy identity drifted")
    hashes = (
        payload.get("source_pdf_sha256"),
        payload.get("source_render_sha256"),
        payload.get("source_ocr_sha256"),
    )
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMNoteWordBoxError("TM page-49 source hashes are invalid")
    thresholds = (
        payload.get("minimum_line_score"),
        payload.get("minimum_anchor_similarity"),
        payload.get("minimum_unit_similarity"),
    )
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= float(value) <= 1
        for value in thresholds
    ):
        raise TMNoteWordBoxError("TM page-49 similarity thresholds are invalid")
    unit = payload.get("unit")
    reporting = payload.get("reporting_period")
    geometry = payload.get("table_geometry")
    if not all(isinstance(value, dict) for value in (unit, reporting, geometry)):
        raise TMNoteWordBoxError("TM page-49 period/unit/geometry policy is incomplete")
    multiplier = unit.get("multiplier")
    canonical = unit.get("canonical")
    if (
        isinstance(multiplier, bool)
        or not isinstance(multiplier, int)
        or multiplier <= 0
        or not isinstance(canonical, str)
        or not canonical
    ):
        raise TMNoteWordBoxError("TM page-49 unit binding is invalid")
    dash_name = payload.get("dash_detector_config")
    if not isinstance(dash_name, str) or Path(dash_name).name != dash_name:
        raise TMNoteWordBoxError("TM page-49 dash-detector path is invalid")
    dash_path = (path.parent / dash_name).resolve()
    if not dash_path.is_file() or sha256_file(dash_path) != payload.get(
        "dash_detector_config_sha256"
    ):
        raise TMNoteWordBoxError("TM page-49 dash detector is absent or drifted")
    dash_config = load_word_box_reconstruction_v3_config(dash_path).base.base
    raw_tables = payload.get("tables")
    if not isinstance(raw_tables, list) or len(raw_tables) != 2:
        raise TMNoteWordBoxError("TM page-49 must define two complete visible notes")
    tables = []
    for record in raw_tables:
        if not isinstance(record, dict):
            raise TMNoteWordBoxError("TM page-49 table record is invalid")
        table_key = record.get("table_key")
        note_number = record.get("note_number")
        axis_kind = record.get("axis_kind")
        numeric_rows = record.get("expected_numeric_rows")
        label_rows = record.get("expected_label_only_rows")
        dash_ordinal = record.get("dash_row_ordinal")
        if (
            not isinstance(table_key, str)
            or not table_key
            or not isinstance(note_number, str)
            or not note_number
            or axis_kind not in {"DUAL_DURATION", "OPENING_ACTIVITY_ACTIVITY_CLOSING"}
            or isinstance(numeric_rows, bool)
            or not isinstance(numeric_rows, int)
            or numeric_rows <= 0
            or label_rows != 1
            or (
                dash_ordinal is not None
                and (
                    isinstance(dash_ordinal, bool)
                    or not isinstance(dash_ordinal, int)
                    or not 1 <= dash_ordinal <= numeric_rows
                )
            )
        ):
            raise TMNoteWordBoxError("TM page-49 table denominator is invalid")
        tables.append(
            TMPage49TableSpec(
                table_key=table_key,
                note_number=note_number,
                title_anchors=_anchors(record.get("title_anchors"), f"{table_key} title"),
                body_end_anchors=_anchors(
                    record.get("body_end_anchors", []),
                    f"{table_key} body end",
                    allow_empty=True,
                ),
                axis_kind=axis_kind,
                expected_numeric_rows=numeric_rows,
                expected_label_only_rows=label_rows,
                detail_label_groups=_anchor_groups(
                    record.get("detail_label_groups"), f"{table_key} detail"
                ),
                dash_row_ordinal=dash_ordinal,
            )
        )
    if [table.table_key for table in tables] != [
        "RISK_PROVISION_EXPENSE",
        "STATE_BUDGET_OBLIGATIONS",
    ] or [len(table.detail_label_groups) for table in tables] != [5, 3]:
        raise TMNoteWordBoxError("TM page-49 table order or row labels drifted")
    forbidden = payload.get("forbidden_semantic_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMNoteWordBoxError("TM page-49 forbidden semantic inputs drifted")
    return TMPage49Policy(
        source_path=path,
        document=str(payload.get("document", "")),
        page_number=49,
        page_tag="page-0049",
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
        period_start=_date_value(reporting, "period_start"),
        period_end=_date_value(reporting, "period_end"),
        comparative_start=_date_value(reporting, "comparative_start"),
        comparative_end=_date_value(reporting, "comparative_end"),
        row_anchor_cluster_line_heights=_bounded_float(geometry, "row_anchor_cluster_line_heights"),
        label_direct_attach_line_heights=_bounded_float(
            geometry, "label_direct_attach_line_heights"
        ),
        artifact_minimum_x_ratio=_bounded_float(geometry, "artifact_minimum_x_ratio", upper=1),
        page_footer_top_ratio=_bounded_float(geometry, "page_footer_top_ratio", upper=1),
        dash_config={str(key): value for key, value in dash_config.items()},
        dash_config_path=dash_path,
        tables=tuple(tables),
        forbidden_semantic_inputs=tuple(str(value) for value in forbidden),
    )


def _find_anchor_line(
    lines: tuple[_Line, ...],
    anchors: tuple[str, ...],
    policy: TMPage49Policy,
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
        key=lambda record: (-record[0], record[1].y_center, record[1].index),
    )
    if not candidates or candidates[0][0] < policy.minimum_anchor_similarity:
        raise TMNoteWordBoxError(f"TM page-49 anchor is unresolved: {anchors}")
    return candidates[0][1]


def _find_anchor_group(
    lines: tuple[_Line, ...],
    anchors: tuple[tuple[str, ...], ...],
    policy: TMPage49Policy,
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
        raise TMNoteWordBoxError("TM page-49 wrapped label anchor is unresolved")
    candidates = []
    for combination in itertools.product(*choices):
        group = tuple(record[0] for record in combination)
        if len({line.index for line in group}) != len(group):
            continue
        if tuple(line.y_center for line in group) != tuple(sorted(line.y_center for line in group)):
            continue
        if any(
            right.y_center - left.y_center > line_height * 1.6
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
        raise TMNoteWordBoxError("TM page-49 wrapped label lines are not locally adjacent")
    return min(candidates, key=lambda record: record[:3])[3]


def _title_source_lines(
    lines: tuple[_Line, ...], title: _Line, note_number: str, line_height: float
) -> tuple[_Line, ...]:
    if retrieval_key(title.text).startswith(note_number):
        return (title,)
    numbers = tuple(
        line
        for line in lines
        if retrieval_key(line.text).rstrip(".") == note_number
        and line.bbox.x1 < title.bbox.x0
        and abs(line.y_center - title.y_center) <= line_height
    )
    if len(numbers) != 1:
        raise TMNoteWordBoxError(f"TM page-49 note {note_number} number anchor drifted")
    return (numbers[0], title)


def _duration_axes(
    lines: tuple[_Line, ...],
    title: _Line,
    first_detail: tuple[_Line, ...],
    policy: TMPage49Policy,
) -> tuple[TMPage49AxisBinding, ...]:
    body_top = min(line.bbox.y0 for line in first_detail)
    candidates = tuple(line for line in lines if title.y_center < line.y_center < body_top)
    dates = tuple(line for line in candidates if parse_vietnamese_date(line.text) is not None)
    units = tuple(
        line
        for line in candidates
        if _best_anchor_similarity(line.text, policy.unit_anchors) >= policy.minimum_unit_similarity
    )
    if len(dates) != 4 or len(units) != 2:
        raise TMNoteWordBoxError("TM page-49 note 9 must expose four dates and two units")
    ordered_units = tuple(sorted(units, key=lambda line: line.x_right))
    assignments: dict[int, list[_Line]] = {line.index: [] for line in ordered_units}
    for date_line in dates:
        unit = min(ordered_units, key=lambda line: abs(line.x_center - date_line.x_center))
        assignments[unit.index].append(date_line)
    expected = (
        ("CURRENT", policy.period_start, policy.period_end),
        ("COMPARATIVE", policy.comparative_start, policy.comparative_end),
    )
    result = []
    for ordinal, (unit, (role, expected_start, expected_end)) in enumerate(
        zip(ordered_units, expected, strict=True), start=1
    ):
        local_dates = tuple(sorted(assignments[unit.index], key=lambda line: line.y_center))
        parsed_dates = tuple(parse_vietnamese_date(line.text) for line in local_dates)
        if len(local_dates) != 2 or None in parsed_dates:
            raise TMNoteWordBoxError("TM page-49 note 9 date/unit pairing drifted")
        start = min(value for value in parsed_dates if value is not None)
        end = max(value for value in parsed_dates if value is not None)
        if (start, end) != (expected_start, expected_end):
            raise TMNoteWordBoxError("TM page-49 note 9 visible duration drifted")
        header_lines = (*local_dates, unit)
        result.append(
            TMPage49AxisBinding(
                ordinal=ordinal,
                axis_id=f"risk-provision-{role.lower()}",
                axis_role=role,
                axis_right_edge=unit.x_right,
                raw_header_text=normalize_text(" | ".join(line.text for line in header_lines)),
                header_line_indices=tuple(line.index for line in header_lines),
                current_or_comparative=role,
                canonical_unit=policy.canonical_unit,
                unit_multiplier=policy.unit_multiplier,
                period_start=start,
                period_end=end,
                period_type="DURATION",
                header_bbox=_union(list(header_lines)),
                unit_bbox=unit.bbox,
                evidence=(
                    "period start/end parsed from the visible note-9 local header",
                    "current/comparative bound by visible horizontal order",
                    "VND million unit matched independently on this axis",
                ),
            )
        )
    return tuple(result)


def _mixed_axes(
    lines: tuple[_Line, ...],
    title: _Line,
    first_detail: tuple[_Line, ...],
    numeric_groups: tuple[tuple[_Line, ...], ...],
    policy: TMPage49Policy,
    line_height: float,
) -> tuple[TMPage49AxisBinding, ...]:
    body_top = min(line.bbox.y0 for line in first_detail)
    header_candidates = tuple(line for line in lines if title.y_center < line.y_center < body_top)
    unit = _find_anchor_line(
        header_candidates,
        policy.unit_anchors,
        policy,
        minimum_y=title.y_center,
        maximum_y=body_top,
    )
    header_groups = (
        _find_anchor_group(
            header_candidates,
            (("so du",), ("dau ky",)),
            policy,
            line_height,
            minimum_y=title.y_center,
            maximum_y=body_top,
        ),
        (
            _find_anchor_line(
                header_candidates,
                ("phat sinh trong ky",),
                policy,
                minimum_y=title.y_center,
                maximum_y=body_top,
            ),
            _find_anchor_line(
                header_candidates,
                ("so phai nop",),
                policy,
                minimum_y=title.y_center,
                maximum_y=body_top,
            ),
        ),
        (
            _find_anchor_line(
                header_candidates,
                ("phat sinh trong ky",),
                policy,
                minimum_y=title.y_center,
                maximum_y=body_top,
            ),
            _find_anchor_line(
                header_candidates,
                ("so da nop",),
                policy,
                minimum_y=title.y_center,
                maximum_y=body_top,
            ),
        ),
        (
            _find_anchor_line(
                header_candidates,
                ("so du cuoi ky",),
                policy,
                minimum_y=title.y_center,
                maximum_y=body_top,
            ),
        ),
    )
    if any(len(group) != 4 for group in numeric_groups):
        raise TMNoteWordBoxError("TM page-49 note 10 must expose four numeric axes per row")
    ordered_numeric = tuple(
        tuple(sorted(group, key=lambda line: line.x_right)) for group in numeric_groups
    )
    right_edges = tuple(
        float(statistics.median(group[index].x_right for group in ordered_numeric))
        for index in range(4)
    )
    if tuple(sorted(right_edges)) != right_edges:
        raise TMNoteWordBoxError("TM page-49 note 10 numeric axes are not ordered")
    definitions = (
        ("OPENING_BALANCE", policy.period_start, policy.period_start, "SNAPSHOT"),
        ("PAYABLE_ACTIVITY", policy.period_start, policy.period_end, "DURATION"),
        ("PAID_ACTIVITY", policy.period_start, policy.period_end, "DURATION"),
        ("CLOSING_BALANCE", policy.period_end, policy.period_end, "SNAPSHOT"),
    )
    result = []
    for ordinal, (group, edge, (role, start, end, period_type)) in enumerate(
        zip(header_groups, right_edges, definitions, strict=True), start=1
    ):
        header_lines = tuple(dict.fromkeys(group))
        result.append(
            TMPage49AxisBinding(
                ordinal=ordinal,
                axis_id=f"state-budget-{role.lower()}",
                axis_role=role,
                axis_right_edge=edge,
                raw_header_text=normalize_text(" | ".join(line.text for line in header_lines)),
                header_line_indices=tuple(line.index for line in header_lines),
                current_or_comparative="CURRENT",
                canonical_unit=policy.canonical_unit,
                unit_multiplier=policy.unit_multiplier,
                period_start=start,
                period_end=end,
                period_type=period_type,
                header_bbox=_union(list(header_lines)),
                unit_bbox=unit.bbox,
                evidence=(
                    "axis role read from the visible opening/activity/closing header",
                    "Q1/2026 dates inherited from the immutable consolidated report context",
                    "VND million unit matched from the visible note-10 table-level unit",
                ),
            )
        )
    return tuple(result)


def _numeric_groups(
    lines: tuple[_Line, ...],
    *,
    minimum_y: float,
    maximum_y: float,
    line_height: float,
    expected_rows: int,
) -> tuple[tuple[_Line, ...], ...]:
    candidates = [
        line for line in lines if minimum_y < line.y_center < maximum_y and _numeric_only(line.text)
    ]
    groups = tuple(tuple(group) for group in _clusters(candidates, line_height * 0.35))
    if len(groups) != expected_rows:
        raise TMNoteWordBoxError(
            f"TM page-49 numeric row denominator drifted: {len(groups)} != {expected_rows}"
        )
    return groups


def _title_row(
    *,
    page_tag: str,
    table_key: str,
    note_number: str,
    title: _Line,
    title_source_lines: tuple[_Line, ...],
    axis_count: int,
) -> TMPage49LogicalRow:
    return TMPage49LogicalRow(
        row_id="",
        table_key=table_key,
        note_number=note_number,
        ordinal=0,
        row=ReaderRow(
            source_row_ids=_source_ids(page_tag, list(title_source_lines)),
            label=title.text,
            note_reference=note_number,
            cells=tuple(parse_financial_number(None) for _ in range(axis_count)),
        ),
        row_kind=TMNoteRowKind.LABEL_ONLY,
        source_role="NOTE_TITLE",
        y_anchor=title.y_center,
        label_bbox=_union(list(title_source_lines)),
        value_bboxes=tuple(None for _ in range(axis_count)),
        label_line_indices=tuple(line.index for line in title_source_lines),
        value_line_indices=tuple(() for _ in range(axis_count)),
        visual_cell_evidence=tuple(None for _ in range(axis_count)),
        cell_period_starts=tuple(None for _ in range(axis_count)),
        cell_period_ends=tuple(None for _ in range(axis_count)),
        cell_period_roles=tuple(None for _ in range(axis_count)),
        mapping_approved=False,
    )


def _renumber(
    rows: list[TMPage49LogicalRow], *, page_tag: str, table_key: str
) -> tuple[TMPage49LogicalRow, ...]:
    result = []
    for ordinal, row in enumerate(sorted(rows, key=lambda item: item.y_anchor), start=1):
        result.append(
            TMPage49LogicalRow(
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
    spec: TMPage49TableSpec,
    title: _Line,
    body_end: float,
    policy: TMPage49Policy,
    line_height: float,
    source_image: Any,
    source_image_path: Path,
    *,
    page_tag: str,
    table_ordinal: int,
) -> tuple[TMPage49Table, tuple[int, ...]]:
    labels = tuple(
        _find_anchor_group(
            lines,
            anchors,
            policy,
            line_height,
            minimum_y=title.y_center,
            maximum_y=body_end,
        )
        for anchors in spec.detail_label_groups
    )
    if tuple(group[0].y_center for group in labels) != tuple(
        sorted(group[0].y_center for group in labels)
    ):
        raise TMNoteWordBoxError(f"TM page-49 {spec.table_key} label order drifted")
    first_label_y = min(line.bbox.y0 for line in labels[0])
    groups = _numeric_groups(
        lines,
        minimum_y=first_label_y,
        maximum_y=body_end,
        line_height=line_height,
        expected_rows=spec.expected_numeric_rows,
    )
    if spec.axis_kind == "DUAL_DURATION":
        axes = _duration_axes(lines, title, labels[0], policy)
    else:
        axes = _mixed_axes(lines, title, labels[0], groups, policy, line_height)
    rows = [
        _title_row(
            page_tag=page_tag,
            table_key=spec.table_key,
            note_number=spec.note_number,
            title=title,
            title_source_lines=_title_source_lines(lines, title, spec.note_number, line_height),
            axis_count=len(axes),
        )
    ]
    used_numeric: set[int] = set()
    for numeric_ordinal, group in enumerate(groups, start=1):
        center = statistics.fmean(line.y_center for line in group)
        label_lines = labels[numeric_ordinal - 1] if numeric_ordinal <= len(labels) else ()
        per_axis: list[list[_Line]] = [[] for _ in axes]
        for line in group:
            axis_index = min(
                range(len(axes)),
                key=lambda index: abs(axes[index].axis_right_edge - line.x_right),
            )
            per_axis[axis_index].append(line)
            used_numeric.add(line.index)
        if any(len(axis_lines) > 1 for axis_lines in per_axis):
            raise TMNoteWordBoxError(f"TM page-49 {spec.table_key} has a split numeric cell")
        visual: list[VisualCellEvidence | None] = []
        cells = []
        for axis_index, (axis, axis_lines) in enumerate(zip(axes, per_axis, strict=True), start=1):
            evidence = None
            raw = " ".join(line.text for line in axis_lines)
            if not axis_lines and spec.dash_row_ordinal == numeric_ordinal:
                evidence = _detect_visible_dash_v3(
                    source_image,
                    source_image_path=source_image_path,
                    axis_right_edge=axis.axis_right_edge,
                    anchor_center=center,
                    line_height=line_height,
                    config=policy.dash_config,
                )
                if evidence is not None:
                    raw = "-"
                else:
                    raise TMNoteWordBoxError(
                        f"TM page-49 visible dash lacks constrained pixel evidence: "
                        f"{spec.table_key}"
                    )
            cell = parse_financial_number(raw)
            if cell.observation not in {
                ObservationKind.VALUE,
                ObservationKind.ZERO,
                ObservationKind.DASH,
            }:
                raise TMNoteWordBoxError(
                    f"TM page-49 {spec.table_key} row {numeric_ordinal} axis {axis_index} "
                    "has no finite or pixel-backed observation"
                )
            cells.append(cell)
            visual.append(evidence)
        if (
            spec.dash_row_ordinal == numeric_ordinal
            and sum(cell.observation is ObservationKind.DASH for cell in cells) != 1
        ):
            raise TMNoteWordBoxError(
                f"TM page-49 visible dash lacks constrained pixel evidence: {spec.table_key}"
            )
        source_lines = [*label_lines, *group]
        rows.append(
            TMPage49LogicalRow(
                row_id="",
                table_key=spec.table_key,
                note_number=spec.note_number,
                ordinal=0,
                row=ReaderRow(
                    source_row_ids=_source_ids(page_tag, source_lines),
                    label=normalize_text(" ".join(line.text for line in label_lines)),
                    note_reference=spec.note_number,
                    cells=tuple(cells),
                ),
                row_kind=TMNoteRowKind.NUMERIC,
                source_role="DETAIL" if label_lines else "UNLABELED_TOTAL",
                y_anchor=center,
                label_bbox=_union(list(label_lines)) if label_lines else None,
                value_bboxes=tuple(
                    _union(axis_lines)
                    if axis_lines
                    else BoundingBox(*evidence.component_box)
                    if evidence is not None
                    else None
                    for axis_lines, evidence in zip(per_axis, visual, strict=True)
                ),
                label_line_indices=tuple(line.index for line in label_lines),
                value_line_indices=tuple(
                    tuple(line.index for line in axis_lines) for axis_lines in per_axis
                ),
                visual_cell_evidence=tuple(visual),
                cell_period_starts=tuple(axis.period_start for axis in axes),
                cell_period_ends=tuple(axis.period_end for axis in axes),
                cell_period_roles=tuple(axis.axis_role for axis in axes),
                mapping_approved=False,
            )
        )
    final_rows = _renumber(rows, page_tag=page_tag, table_key=spec.table_key)
    counts = (
        sum(row.row_kind is TMNoteRowKind.NUMERIC for row in final_rows),
        sum(row.row_kind is TMNoteRowKind.LABEL_ONLY for row in final_rows),
    )
    if counts != (spec.expected_numeric_rows, spec.expected_label_only_rows):
        raise TMNoteWordBoxError(f"TM page-49 {spec.table_key} row denominator drifted")
    title_sources = _title_source_lines(lines, title, spec.note_number, line_height)
    table_indices = {
        *(line.index for line in title_sources),
        *(line.index for group in labels for line in group),
        *used_numeric,
        *(index for axis in axes for index in axis.header_line_indices),
    }
    unit_indices = {
        line.index for line in lines if any(line.bbox == axis.unit_bbox for axis in axes)
    }
    table_indices |= unit_indices
    table_lines = [line for line in lines if line.index in table_indices]
    return (
        TMPage49Table(
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
    )


def parse_tm_page49(
    result_path: Path,
    source_image_path: Path,
    policy: TMPage49Policy,
    *,
    page_tag: str = "page-0049",
) -> ParsedTMPage49:
    """Reconstruct both complete notes without granting schema mapping authority."""

    if page_tag != policy.page_tag:
        raise TMNoteWordBoxError("TM page-49 page tag drifted")
    if sha256_file(result_path) != policy.source_ocr_sha256:
        raise TMNoteWordBoxError("TM page-49 OCR artifact hash drifted")
    if sha256_file(source_image_path) != policy.source_render_sha256:
        raise TMNoteWordBoxError("TM page-49 source render hash drifted")
    source_image = cv2.imread(str(source_image_path), cv2.IMREAD_GRAYSCALE)
    if source_image is None:
        raise TMNoteWordBoxError("TM page-49 source render cannot be decoded")
    input_path, lines, _metadata = _load_lines(result_path, policy.minimum_line_score)
    line_height = float(statistics.median(line.height for line in lines))
    if line_height <= 0:
        raise TMNoteWordBoxError("TM page-49 line height is invalid")
    source_bbox = _union(lines)
    footer_top = source_bbox.y1 * policy.page_footer_top_ratio
    titles = tuple(_find_anchor_line(lines, spec.title_anchors, policy) for spec in policy.tables)
    if tuple(title.y_center for title in titles) != tuple(
        sorted(title.y_center for title in titles)
    ):
        raise TMNoteWordBoxError("TM page-49 note order drifted")
    tables = []
    used_numeric: set[int] = set()
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
        table, numeric_indices = _reconstruct_table(
            lines,
            spec,
            title,
            body_end,
            policy,
            line_height,
            source_image,
            source_image_path,
            page_tag=page_tag,
            table_ordinal=ordinal,
        )
        tables.append(table)
        used_numeric.update(numeric_indices)
    table_numeric = {
        line.index
        for line in lines
        if titles[0].y_center < line.y_center < footer_top and _numeric_only(line.text)
    }
    table_numeric -= {line_index for table in tables for line_index in table.title_line_indices}
    footer = tuple(
        sorted(
            line.index for line in lines if line.y_center >= footer_top and _numeric_only(line.text)
        )
    )
    artifacts = tuple(
        sorted(
            line.index
            for line in lines
            if line.bbox.x0 / source_bbox.x1 >= policy.artifact_minimum_x_ratio
            and line.y_center < footer_top
        )
    )
    unassigned = tuple(sorted(table_numeric - used_numeric))
    rows = tuple(row for table in tables for row in table.rows)
    axes = tuple(axis for table in tables for axis in table.axes)
    result = ParsedTMPage49(
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
        line_height=line_height,
        source_ocr_bbox=source_bbox,
        table_bbox=BoundingBox(
            min(table.bbox.x0 for table in tables),
            min(table.bbox.y0 for table in tables),
            max(table.bbox.x1 for table in tables),
            max(table.bbox.y1 for table in tables),
        ),
        unassigned_numeric_line_indices=unassigned,
        excluded_artifact_line_indices=artifacts,
        excluded_footer_numeric_line_indices=footer,
        mapping_authority=False,
        evidence=(
            "notes 9 and 10 are complete, independent sections on immutable PDF page 49",
            "note 9 binds two visible duration axes; note 10 retains four mixed balance/activity axes",
            "10 numeric rows reconstructed from PP-OCRv6 word boxes plus one pixel-backed DASH",
            "schema identifiers are absent from parser inputs and mapping authority remains false",
        ),
    )
    if (
        len(result.rows) != 12
        or result.numeric_row_count != 10
        or result.label_only_row_count != 2
        or result.financial_slot_count != 28
        or result.observation_count(ObservationKind.VALUE) != 27
        or result.observation_count(ObservationKind.DASH) != 1
        or result.unassigned_numeric_line_indices
        or result.excluded_artifact_line_indices != (55,)
        or result.excluded_footer_numeric_line_indices != (56,)
    ):
        raise TMNoteWordBoxError(
            "TM page-49 exact source denominator drifted: "
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
    "ParsedTMPage49",
    "TMPage49AxisBinding",
    "TMPage49LogicalRow",
    "TMPage49Policy",
    "TMPage49Table",
    "load_tm_page49_policy",
    "parse_tm_page49",
]
