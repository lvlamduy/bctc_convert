"""Mixed snapshot/equity-grid TM reconstruction for MBB consolidated PDF page 44."""

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
from rapidfuzz.fuzz import partial_ratio, ratio

from bctc_ai.core.contracts import BoundingBox, ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import normalize_text, parse_financial_number, retrieval_key
from bctc_ai.evaluation.word_box_rows import VisualCellEvidence
from bctc_ai.evaluation.word_box_rows_v3 import (
    _detect_visible_dash_v3,
    load_word_box_reconstruction_v3_config,
)
from bctc_ai.tables.tm_note_page35 import (
    TMPage35Policy,
    TMPage35TableSpec,
    _body_end,
    _find_titles,
    _reconstruct_table,
)
from bctc_ai.tables.tm_note_word_box import (
    TMNoteRowKind,
    TMNoteWordBoxError,
    _bind_page31_axes,
    _Line,
    _load_lines,
    _numeric_only,
    _source_ids,
    _union,
)
from bctc_ai.validation.reader_agreement import ReaderRow

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DOTTED_INTEGER = re.compile(r"(?<!\d)(\d{1,3}(?:\.\d{3})+)(?!\d)")
_PERCENT = re.compile(r"(?<!\d)(\d{1,2},\d{2})\s*%")
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
class TMPage44EquityAxisSpec:
    role: str
    anchors: tuple[str, ...]


@dataclass(frozen=True)
class TMPage44EquityRowSpec:
    label_anchors: tuple[str, ...]
    expected_observations: tuple[str, ...]


@dataclass(frozen=True)
class TMPage44EquitySpec:
    table_key: str
    note_number: str
    section_title_anchors: tuple[str, ...]
    report_title_anchors: tuple[str, ...]
    unit_anchors: tuple[str, ...]
    axes: tuple[TMPage44EquityAxisSpec, ...]
    rows: tuple[TMPage44EquityRowSpec, ...]


@dataclass(frozen=True)
class TMPage44NarrativeSpec:
    fact_id: str
    anchors: tuple[str, ...]
    value_count: int


@dataclass(frozen=True)
class TMPage44Policy:
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
    canonical_unit: str
    unit_multiplier: int
    page_footer_top_ratio: float
    dash_config: dict[str, float | int]
    dash_config_path: Path
    snapshot_policy: TMPage35Policy
    equity: TMPage44EquitySpec
    narrative_facts: tuple[TMPage44NarrativeSpec, ...]
    forbidden_semantic_inputs: tuple[str, ...]


@dataclass(frozen=True)
class TMPage44AxisBinding:
    ordinal: int
    axis_id: str
    axis_right_edge: float
    raw_header_text: str
    header_line_indices: tuple[int, ...]
    semantic_role: str
    canonical_unit: str
    unit_multiplier: int
    period_start: date
    period_end: date
    period_type: str
    header_bbox: BoundingBox
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class TMPage44LogicalRow:
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
class TMPage44Table:
    ordinal: int
    table_key: str
    note_number: str
    title: str
    title_line_indices: tuple[int, ...]
    axes: tuple[TMPage44AxisBinding, ...]
    rows: tuple[TMPage44LogicalRow, ...]
    bbox: BoundingBox


@dataclass(frozen=True)
class TMPage44NarrativeFact:
    fact_id: str
    raw_text: str
    source_line_indices: tuple[int, ...]
    source_row_ids: tuple[str, ...]
    bbox: BoundingBox
    values: tuple[Decimal, ...]
    units: tuple[str, ...]
    period_end: date
    status: str


@dataclass(frozen=True)
class ParsedTMPage44:
    input_path: str
    source_sha256: str
    source_render_sha256: str
    source_pdf_sha256: str
    page_tag: str
    scope: str
    scope_binding: str
    tables: tuple[TMPage44Table, ...]
    rows: tuple[TMPage44LogicalRow, ...]
    narrative_facts: tuple[TMPage44NarrativeFact, ...]
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

    @property
    def narrative_value_count(self) -> int:
        return sum(len(fact.values) for fact in self.narrative_facts)

    def observation_count(self, observation: ObservationKind) -> int:
        return sum(
            cell.observation is observation
            for row in self.rows
            if row.row_kind is TMNoteRowKind.NUMERIC
            for cell in row.row.cells
        )


def _anchors(payload: Any, field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(payload, list) or (not payload and not allow_empty):
        raise TMNoteWordBoxError(f"TM page-44 {field} anchors are invalid")
    result = tuple(retrieval_key(str(value)) for value in payload)
    if any(not value for value in result):
        raise TMNoteWordBoxError(f"TM page-44 {field} contains an empty anchor")
    return result


def _positive(payload: dict[str, Any], field: str) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise TMNoteWordBoxError(f"invalid positive TM page-44 setting: {field}")
    return float(value)


def load_tm_page44_policy(path: Path) -> TMPage44Policy:
    """Load the immutable mixed-grid page-44 reconstruction policy."""

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMNoteWordBoxError(f"cannot load TM page-44 policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE44_MIXED_GRID_DASH_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 44
        or payload.get("page_tag") != "page-0044"
        or payload.get("scope") != "CONSOLIDATED"
    ):
        raise TMNoteWordBoxError("TM page-44 policy identity drifted")
    hashes = (
        payload.get("source_pdf_sha256"),
        payload.get("source_render_sha256"),
        payload.get("source_ocr_sha256"),
    )
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMNoteWordBoxError("TM page-44 source hashes are invalid")
    unit = payload.get("unit")
    header = payload.get("header_geometry")
    geometry = payload.get("table_geometry")
    if not all(isinstance(value, dict) for value in (unit, header, geometry)):
        raise TMNoteWordBoxError("TM page-44 geometry policy is incomplete")
    multiplier = unit.get("multiplier")
    canonical_unit = unit.get("canonical")
    if (
        isinstance(multiplier, bool)
        or not isinstance(multiplier, int)
        or multiplier <= 0
        or not isinstance(canonical_unit, str)
        or not canonical_unit
    ):
        raise TMNoteWordBoxError("TM page-44 unit binding is invalid")
    minimum_line_score = float(payload.get("minimum_line_score", -1))
    minimum_anchor_similarity = float(payload.get("minimum_anchor_similarity", -1))
    minimum_unit_similarity = float(payload.get("minimum_unit_similarity", -1))
    if any(
        not 0 <= value <= 1
        for value in (minimum_line_score, minimum_anchor_similarity, minimum_unit_similarity)
    ):
        raise TMNoteWordBoxError("TM page-44 similarity thresholds are invalid")
    dash_name = payload.get("dash_detector_config")
    if not isinstance(dash_name, str) or Path(dash_name).name != dash_name:
        raise TMNoteWordBoxError("TM page-44 dash detector path is invalid")
    dash_path = (path.parent / dash_name).resolve()
    if not dash_path.is_file() or sha256_file(dash_path) != payload.get(
        "dash_detector_config_sha256"
    ):
        raise TMNoteWordBoxError("TM page-44 dash detector is absent or drifted")
    dash_config = load_word_box_reconstruction_v3_config(dash_path).base.base
    raw_snapshot = payload.get("snapshot_tables")
    if not isinstance(raw_snapshot, list) or len(raw_snapshot) != 2:
        raise TMNoteWordBoxError("TM page-44 must define two snapshot tables")
    snapshot_specs = []
    for record in raw_snapshot:
        if not isinstance(record, dict):
            raise TMNoteWordBoxError("TM page-44 snapshot-table record is invalid")
        snapshot_specs.append(
            TMPage35TableSpec(
                table_key=str(record.get("table_key", "")),
                note_number=str(record.get("note_number", "")),
                title_anchors=_anchors(record.get("title_anchors"), "snapshot title"),
                body_end_anchors=_anchors(
                    record.get("body_end_anchors", []), "snapshot body end", allow_empty=True
                ),
                structural_label_anchors=_anchors(
                    record.get("structural_label_anchors", []),
                    "snapshot structural label",
                    allow_empty=True,
                ),
                dash_label_anchors=_anchors(
                    record.get("dash_label_anchors", []),
                    "snapshot dash label",
                    allow_empty=True,
                ),
                expected_numeric_rows=int(record.get("expected_numeric_rows", 0)),
                expected_label_only_rows=int(record.get("expected_label_only_rows", -1)),
            )
        )
    equity_raw = payload.get("equity_table")
    if not isinstance(equity_raw, dict):
        raise TMNoteWordBoxError("TM page-44 equity policy is absent")
    raw_axes = equity_raw.get("axis_header_anchors")
    raw_rows = equity_raw.get("rows")
    if not isinstance(raw_axes, list) or len(raw_axes) != 4:
        raise TMNoteWordBoxError("TM page-44 equity axes drifted")
    if not isinstance(raw_rows, list) or len(raw_rows) != 10:
        raise TMNoteWordBoxError("TM page-44 equity row denominator drifted")
    axes = tuple(
        TMPage44EquityAxisSpec(
            role=str(record.get("role", "")),
            anchors=_anchors(record.get("anchors"), "equity axis"),
        )
        for record in raw_axes
        if isinstance(record, dict)
    )
    if len(axes) != 4 or tuple(axis.role for axis in axes) != (
        "BEGINNING_BALANCE",
        "INCREASE",
        "DECREASE",
        "ENDING_BALANCE",
    ):
        raise TMNoteWordBoxError("TM page-44 equity axis roles drifted")
    valid_observations = {item.value for item in ObservationKind}
    equity_rows = []
    for record in raw_rows:
        if not isinstance(record, dict):
            raise TMNoteWordBoxError("TM page-44 equity row is invalid")
        observations = record.get("expected_observations")
        if (
            not isinstance(observations, list)
            or len(observations) != 4
            or any(item not in valid_observations for item in observations)
        ):
            raise TMNoteWordBoxError("TM page-44 equity observations drifted")
        equity_rows.append(
            TMPage44EquityRowSpec(
                label_anchors=_anchors(record.get("label_anchors"), "equity row"),
                expected_observations=tuple(observations),
            )
        )
    narrative_raw = payload.get("narrative_facts")
    if not isinstance(narrative_raw, list) or len(narrative_raw) != 5:
        raise TMNoteWordBoxError("TM page-44 narrative-fact denominator drifted")
    narrative = []
    for record in narrative_raw:
        if not isinstance(record, dict):
            raise TMNoteWordBoxError("TM page-44 narrative fact is invalid")
        count = record.get("value_count")
        fact_id = record.get("fact_id")
        if (
            not isinstance(fact_id, str)
            or not fact_id
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count <= 0
        ):
            raise TMNoteWordBoxError("TM page-44 narrative fact identity drifted")
        narrative.append(
            TMPage44NarrativeSpec(
                fact_id=fact_id,
                anchors=_anchors(record.get("anchors"), "narrative fact"),
                value_count=count,
            )
        )
    forbidden = payload.get("forbidden_semantic_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMNoteWordBoxError("TM page-44 forbidden semantic inputs drifted")
    footer_ratio = _positive(geometry, "page_footer_top_ratio")
    if footer_ratio >= 1:
        raise TMNoteWordBoxError("TM page-44 footer ratio must be below one")
    snapshot_policy = TMPage35Policy(
        source_path=path,
        document=str(payload.get("document", "")),
        page_number=44,
        page_tag="page-0044",
        scope="CONSOLIDATED",
        scope_binding=str(payload.get("scope_binding", "")),
        source_pdf_sha256=hashes[0],
        source_render_sha256=hashes[1],
        source_ocr_sha256=hashes[2],
        minimum_line_score=minimum_line_score,
        minimum_anchor_similarity=minimum_anchor_similarity,
        minimum_unit_similarity=minimum_unit_similarity,
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
        structural_continuation_line_heights=float(
            geometry.get("structural_continuation_line_heights", 0.0)
        ),
        note_reference_left_gap_axis_widths=_positive(
            geometry, "note_reference_left_gap_axis_widths"
        ),
        page_footer_top_ratio=footer_ratio,
        dash_config={str(key): value for key, value in dash_config.items()},
        dash_config_path=dash_path,
        tables=tuple(snapshot_specs),
        forbidden_semantic_inputs=tuple(str(item) for item in forbidden),
    )
    return TMPage44Policy(
        source_path=path,
        document=snapshot_policy.document,
        page_number=44,
        page_tag="page-0044",
        scope="CONSOLIDATED",
        scope_binding=snapshot_policy.scope_binding,
        source_pdf_sha256=hashes[0],
        source_render_sha256=hashes[1],
        source_ocr_sha256=hashes[2],
        minimum_line_score=minimum_line_score,
        minimum_anchor_similarity=minimum_anchor_similarity,
        canonical_unit=canonical_unit,
        unit_multiplier=multiplier,
        page_footer_top_ratio=footer_ratio,
        dash_config={str(key): value for key, value in dash_config.items()},
        dash_config_path=dash_path,
        snapshot_policy=snapshot_policy,
        equity=TMPage44EquitySpec(
            table_key=str(equity_raw.get("table_key", "")),
            note_number=str(equity_raw.get("note_number", "")),
            section_title_anchors=_anchors(
                equity_raw.get("section_title_anchors"), "equity section title"
            ),
            report_title_anchors=_anchors(
                equity_raw.get("report_title_anchors"), "equity report title"
            ),
            unit_anchors=_anchors(equity_raw.get("unit_anchors"), "equity unit"),
            axes=axes,
            rows=tuple(equity_rows),
        ),
        narrative_facts=tuple(narrative),
        forbidden_semantic_inputs=tuple(str(item) for item in forbidden),
    )


def _text_similarity(text: str, anchors: tuple[str, ...]) -> float:
    key = retrieval_key(text)
    return max((ratio(key, anchor) / 100 for anchor in anchors), default=0.0)


def _select_text_group(
    lines: tuple[_Line, ...],
    anchors: tuple[str, ...],
    *,
    minimum_y: float,
    maximum_y: float,
    line_height: float,
    threshold: float,
    excluded: set[int] | None = None,
) -> tuple[_Line, ...]:
    excluded = excluded or set()
    candidates = [
        line
        for line in lines
        if minimum_y < line.y_center < maximum_y
        and line.index not in excluded
        and not _numeric_only(line.text)
    ]
    proposals: list[tuple[float, tuple[_Line, ...]]] = []
    for line in candidates:
        proposals.append((_text_similarity(line.text, anchors), (line,)))
        for other in candidates:
            if (
                line.index != other.index
                and 0 < other.y_center - line.y_center <= line_height * 1.8
                and abs(other.bbox.x0 - line.bbox.x0) <= line_height * 1.5
            ):
                group = (line, other)
                proposals.append(
                    (_text_similarity(" ".join(item.text for item in group), anchors), group)
                )
    score, group = max(
        proposals,
        key=lambda item: (item[0], -len(item[1]), -item[1][0].y_center),
        default=(0.0, ()),
    )
    if score < threshold or not group:
        raise TMNoteWordBoxError(f"TM page-44 text group is unresolved: {anchors}")
    return group


def _axis_from_snapshot(axis: Any) -> TMPage44AxisBinding:
    return TMPage44AxisBinding(
        ordinal=axis.ordinal,
        axis_id=axis.axis_id,
        axis_right_edge=axis.axis_right_edge,
        raw_header_text=normalize_text(f"{axis.raw_date_text} | {axis.raw_unit_text}"),
        header_line_indices=(axis.date_line_index, axis.unit_line_index),
        semantic_role=axis.current_or_comparative,
        canonical_unit=axis.canonical_unit,
        unit_multiplier=axis.unit_multiplier,
        period_start=axis.period_start,
        period_end=axis.period_end,
        period_type=axis.period_type,
        header_bbox=axis.header_bbox,
        evidence=axis.evidence,
    )


def _structural_row(
    *,
    page_tag: str,
    table_key: str,
    note_number: str,
    ordinal: int,
    lines: tuple[_Line, ...],
    axis_count: int,
    source_role: str,
) -> TMPage44LogicalRow:
    return TMPage44LogicalRow(
        row_id=f"{page_tag}:{table_key.lower()}:row-{ordinal:04d}",
        table_key=table_key,
        note_number=note_number,
        ordinal=ordinal,
        row=ReaderRow(
            source_row_ids=_source_ids(page_tag, list(lines)),
            label=normalize_text(" ".join(line.text for line in lines)),
            note_reference=note_number,
            cells=tuple(parse_financial_number(None) for _axis in range(axis_count)),
        ),
        row_kind=TMNoteRowKind.LABEL_ONLY,
        source_role=source_role,
        y_anchor=statistics.fmean(line.y_center for line in lines),
        label_bbox=_union(lines),
        value_bboxes=tuple(None for _axis in range(axis_count)),
        label_line_indices=tuple(line.index for line in lines),
        value_line_indices=tuple(() for _axis in range(axis_count)),
        visual_cell_evidence=tuple(None for _axis in range(axis_count)),
        mapping_approved=False,
    )


def _snapshot_table(
    lines: tuple[_Line, ...],
    spec: TMPage35TableSpec,
    title: _Line,
    next_title: _Line | None,
    policy: TMPage44Policy,
    line_height: float,
    source_image: Any,
    source_image_path: Path,
    *,
    ordinal: int,
) -> tuple[TMPage44Table, tuple[int, ...]]:
    footer_top = _union(lines).y1 * policy.page_footer_top_ratio
    body_end = _body_end(lines, spec, title, next_title, footer_top, policy.snapshot_policy)
    axes = _bind_page31_axes(lines, title, None, body_end, policy.snapshot_policy, line_height)
    shared, unassigned = _reconstruct_table(
        lines,
        spec,
        title,
        axes,
        body_end,
        policy.snapshot_policy,
        line_height,
        source_image,
        source_image_path,
        page_tag=policy.page_tag,
        table_ordinal=ordinal,
    )
    converted_axes = tuple(_axis_from_snapshot(axis) for axis in axes)
    rows = [
        _structural_row(
            page_tag=policy.page_tag,
            table_key=spec.table_key,
            note_number=spec.note_number,
            ordinal=1,
            lines=(title,),
            axis_count=2,
            source_role="NOTE_TITLE",
        )
    ]
    for row_ordinal, row in enumerate(shared.rows, start=2):
        rows.append(
            TMPage44LogicalRow(
                row_id=f"{policy.page_tag}:{spec.table_key.lower()}:row-{row_ordinal:04d}",
                table_key=spec.table_key,
                note_number=spec.note_number,
                ordinal=row_ordinal,
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
    return (
        TMPage44Table(
            ordinal=ordinal,
            table_key=spec.table_key,
            note_number=spec.note_number,
            title=title.text,
            title_line_indices=(title.index,),
            axes=converted_axes,
            rows=tuple(rows),
            bbox=shared.bbox,
        ),
        unassigned,
    )


def _equity_axes(
    lines: tuple[_Line, ...],
    policy: TMPage44Policy,
    report_title: tuple[_Line, ...],
    unit_line: tuple[_Line, ...],
    line_height: float,
    footer_top: float,
) -> tuple[TMPage44AxisBinding, ...]:
    header_groups = tuple(
        _select_text_group(
            lines,
            spec.anchors,
            minimum_y=max(line.y_center for line in report_title),
            maximum_y=2_120,
            line_height=line_height,
            threshold=policy.minimum_anchor_similarity,
        )
        for spec in policy.equity.axes
    )
    header_end = max(line.y_center for group in header_groups for line in group)
    numeric = sorted(
        (
            line
            for line in lines
            if header_end < line.y_center < footer_top and _numeric_only(line.text)
        ),
        key=lambda line: line.x_right,
    )
    clusters: list[list[_Line]] = []
    for line in numeric:
        if (
            not clusters
            or line.x_right - statistics.fmean(item.x_right for item in clusters[-1])
            > line_height * 2
        ):
            clusters.append([line])
        else:
            clusters[-1].append(line)
    if len(clusters) != 4 or [len(cluster) for cluster in clusters] != [10, 6, 5, 10]:
        raise TMNoteWordBoxError("TM page-44 equity numeric-axis clusters drifted")
    periods = (
        (date(2025, 12, 31), date(2025, 12, 31), "SNAPSHOT"),
        (date(2026, 1, 1), date(2026, 3, 31), "FLOW"),
        (date(2026, 1, 1), date(2026, 3, 31), "FLOW"),
        (date(2026, 3, 31), date(2026, 3, 31), "SNAPSHOT"),
    )
    result = []
    for index, (spec, header_group, cluster, period) in enumerate(
        zip(policy.equity.axes, header_groups, clusters, periods, strict=True), start=1
    ):
        result.append(
            TMPage44AxisBinding(
                ordinal=index,
                axis_id=f"equity-axis-{index}",
                axis_right_edge=float(statistics.median(line.x_right for line in cluster)),
                raw_header_text=normalize_text(" ".join(line.text for line in header_group)),
                header_line_indices=tuple(line.index for line in header_group),
                semantic_role=spec.role,
                canonical_unit=policy.canonical_unit,
                unit_multiplier=policy.unit_multiplier,
                period_start=period[0],
                period_end=period[1],
                period_type=period[2],
                header_bbox=_union([*header_group, *unit_line]),
                evidence=(
                    "visible equity-grid header",
                    "axis right edge inferred from the source numeric x-cluster",
                    "visible page-44 unit line",
                ),
            )
        )
    return tuple(result)


def _equity_table(
    lines: tuple[_Line, ...],
    policy: TMPage44Policy,
    line_height: float,
    source_image: Any,
    source_image_path: Path,
) -> tuple[TMPage44Table, tuple[int, ...]]:
    source_bbox = _union(lines)
    footer_top = source_bbox.y1 * policy.page_footer_top_ratio
    section = _select_text_group(
        lines,
        policy.equity.section_title_anchors,
        minimum_y=1_500,
        maximum_y=1_700,
        line_height=line_height,
        threshold=policy.minimum_anchor_similarity,
    )
    report = _select_text_group(
        lines,
        policy.equity.report_title_anchors,
        minimum_y=1_650,
        maximum_y=1_800,
        line_height=line_height,
        threshold=policy.minimum_anchor_similarity,
    )
    unit_line = _select_text_group(
        lines,
        policy.equity.unit_anchors,
        minimum_y=1_900,
        maximum_y=2_020,
        line_height=line_height,
        threshold=policy.minimum_anchor_similarity,
    )
    axes = _equity_axes(lines, policy, report, unit_line, line_height, footer_top)
    numeric_lines = [
        line for line in lines if 2_100 < line.y_center < footer_top and _numeric_only(line.text)
    ]
    axis_gap = statistics.median(
        axes[index + 1].axis_right_edge - axes[index].axis_right_edge
        for index in range(len(axes) - 1)
    )
    used_labels: set[int] = set()
    used_numeric: set[int] = set()
    rows = [
        _structural_row(
            page_tag=policy.page_tag,
            table_key=policy.equity.table_key,
            note_number="22",
            ordinal=1,
            lines=section,
            axis_count=4,
            source_role="SECTION_TITLE",
        ),
        _structural_row(
            page_tag=policy.page_tag,
            table_key=policy.equity.table_key,
            note_number=policy.equity.note_number,
            ordinal=2,
            lines=report,
            axis_count=4,
            source_role="NOTE_TITLE",
        ),
    ]
    for ordinal, spec in enumerate(policy.equity.rows, start=3):
        labels = _select_text_group(
            lines,
            spec.label_anchors,
            minimum_y=2_100,
            maximum_y=footer_top,
            line_height=line_height,
            threshold=policy.minimum_anchor_similarity,
            excluded=used_labels,
        )
        used_labels.update(line.index for line in labels)
        label_anchor = max(line.y_center for line in labels)
        nearby = [
            line
            for line in numeric_lines
            if line.index not in used_numeric
            and abs(line.y_center - label_anchor) <= line_height * 0.75
        ]
        per_axis: list[list[_Line]] = [[] for _axis in axes]
        for line in nearby:
            distances = [abs(line.x_right - axis.axis_right_edge) for axis in axes]
            closest = min(range(len(axes)), key=distances.__getitem__)
            if distances[closest] <= axis_gap * 0.35:
                per_axis[closest].append(line)
                used_numeric.add(line.index)
        if any(len(group) > 1 for group in per_axis):
            raise TMNoteWordBoxError("TM page-44 equity cell has multiple numeric OCR lines")
        numeric_centers = [line.y_center for group in per_axis for line in group]
        row_center = statistics.fmean(numeric_centers) if numeric_centers else label_anchor
        visual: list[VisualCellEvidence | None] = []
        cells = []
        value_bboxes = []
        for axis, group in zip(axes, per_axis, strict=True):
            evidence = None
            if not group:
                evidence = _detect_visible_dash_v3(
                    source_image,
                    source_image_path=source_image_path,
                    axis_right_edge=axis.axis_right_edge,
                    anchor_center=row_center,
                    line_height=line_height,
                    config=policy.dash_config,
                )
                if evidence is None:
                    raise TMNoteWordBoxError(
                        f"TM page-44 missing equity cell lacks dash pixel evidence: row {ordinal}"
                    )
            visual.append(evidence)
            cells.append(parse_financial_number("-" if evidence is not None else group[0].text))
            value_bboxes.append(
                BoundingBox(*evidence.component_box) if evidence is not None else group[0].bbox
            )
        observations = tuple(cell.observation.value for cell in cells)
        if observations != spec.expected_observations:
            raise TMNoteWordBoxError(
                f"TM page-44 equity observation pattern drifted: row {ordinal} {observations}"
            )
        source_lines = [*labels, *(line for group in per_axis for line in group)]
        rows.append(
            TMPage44LogicalRow(
                row_id=(f"{policy.page_tag}:{policy.equity.table_key.lower()}:row-{ordinal:04d}"),
                table_key=policy.equity.table_key,
                note_number=policy.equity.note_number,
                ordinal=ordinal,
                row=ReaderRow(
                    source_row_ids=_source_ids(policy.page_tag, source_lines),
                    label=normalize_text(" ".join(line.text for line in labels)),
                    note_reference=policy.equity.note_number,
                    cells=tuple(cells),
                ),
                row_kind=TMNoteRowKind.NUMERIC,
                source_role="TOTAL" if ordinal == 12 else "EQUITY_COMPONENT",
                y_anchor=row_center,
                label_bbox=_union(labels),
                value_bboxes=tuple(value_bboxes),
                label_line_indices=tuple(line.index for line in labels),
                value_line_indices=tuple(tuple(line.index for line in group) for group in per_axis),
                visual_cell_evidence=tuple(visual),
                mapping_approved=False,
            )
        )
    if len(used_numeric) != len(numeric_lines):
        unassigned = tuple(
            sorted(line.index for line in numeric_lines if line.index not in used_numeric)
        )
    else:
        unassigned = ()
    table_lines = [*section, *report, *unit_line]
    used_indices = {
        int(source_id.rsplit("-", 1)[-1]) for row in rows for source_id in row.row.source_row_ids
    }
    table_lines.extend(line for line in lines if line.index in used_indices)
    return (
        TMPage44Table(
            ordinal=3,
            table_key=policy.equity.table_key,
            note_number=policy.equity.note_number,
            title=normalize_text(" ".join(line.text for line in report)),
            title_line_indices=tuple(line.index for line in report),
            axes=axes,
            rows=tuple(rows),
            bbox=_union(table_lines),
        ),
        unassigned,
    )


def _narrative_facts(
    lines: tuple[_Line, ...], policy: TMPage44Policy, line_height: float
) -> tuple[TMPage44NarrativeFact, ...]:
    facts = []
    for spec in policy.narrative_facts:
        candidates = [
            line for line in lines if 850 < line.y_center < 1_950 and not _numeric_only(line.text)
        ]
        score, anchor_line = max(
            (
                (
                    max(
                        partial_ratio(retrieval_key(line.text), anchor) / 100
                        for anchor in spec.anchors
                    ),
                    line,
                )
                for line in candidates
            ),
            key=lambda item: (item[0], -item[1].y_center),
        )
        if score < policy.minimum_anchor_similarity:
            raise TMNoteWordBoxError(f"TM page-44 narrative anchor is unresolved: {spec.fact_id}")
        group = (anchor_line,)
        if spec.fact_id == "ISSUED_SHARE_COUNT":
            followers = [
                line
                for line in candidates
                if 0 < line.y_center - anchor_line.y_center <= line_height * 1.5
                and abs(line.bbox.x0 - anchor_line.bbox.x0) <= line_height
            ]
            if len(followers) != 1:
                raise TMNoteWordBoxError("TM page-44 issued-share narrative continuation drifted")
            group = (anchor_line, followers[0])
        raw = normalize_text(" ".join(line.text for line in group))
        if spec.fact_id.endswith("INTEREST_RATE_RANGE"):
            values = tuple(Decimal(value.replace(",", ".")) for value in _PERCENT.findall(raw))
            units = tuple("PERCENT_PER_YEAR" for _value in values)
        else:
            integers = tuple(
                Decimal(value.replace(".", "")) for value in _DOTTED_INTEGER.findall(raw)
            )
            selector = {
                "ISSUED_SHARE_COUNT": (0, "SHARE"),
                "PAR_VALUE": (1, "VND_PER_SHARE"),
                "STATED_CHARTER_CAPITAL": (2, "VND_MILLION"),
            }.get(spec.fact_id)
            if selector is None or len(integers) != 3:
                raise TMNoteWordBoxError(f"TM page-44 narrative integers drifted: {spec.fact_id}")
            values = (integers[selector[0]],)
            units = (selector[1],)
        if len(values) != spec.value_count:
            raise TMNoteWordBoxError(f"TM page-44 narrative value count drifted: {spec.fact_id}")
        facts.append(
            TMPage44NarrativeFact(
                fact_id=spec.fact_id,
                raw_text=raw,
                source_line_indices=tuple(line.index for line in group),
                source_row_ids=_source_ids(policy.page_tag, list(group)),
                bbox=_union(group),
                values=values,
                units=units,
                period_end=date(2026, 3, 31),
                status="SOURCE_ONLY_PROVENANCE",
            )
        )
    return tuple(facts)


def parse_tm_page44(
    result_path: Path,
    source_image_path: Path,
    policy: TMPage44Policy,
    *,
    page_tag: str = "page-0044",
) -> ParsedTMPage44:
    """Reconstruct page-44 tables and narrative facts without mapping authority."""

    if page_tag != policy.page_tag:
        raise TMNoteWordBoxError("TM page-44 page tag drifted")
    if sha256_file(result_path) != policy.source_ocr_sha256:
        raise TMNoteWordBoxError("TM page-44 OCR artifact hash drifted")
    if sha256_file(source_image_path) != policy.source_render_sha256:
        raise TMNoteWordBoxError("TM page-44 source render hash drifted")
    source_image = cv2.imread(str(source_image_path), cv2.IMREAD_GRAYSCALE)
    if source_image is None:
        raise TMNoteWordBoxError("TM page-44 source render cannot be decoded")
    input_path, lines, _metadata = _load_lines(result_path, policy.minimum_line_score)
    line_height = float(statistics.median(line.height for line in lines))
    if line_height <= 0:
        raise TMNoteWordBoxError("TM page-44 line height is invalid")
    titles = _find_titles(lines, policy.snapshot_policy)
    snapshot_tables = []
    unassigned = []
    for index, (spec, title) in enumerate(titles):
        next_title = titles[index + 1][1] if index + 1 < len(titles) else None
        table, table_unassigned = _snapshot_table(
            lines,
            spec,
            title,
            next_title,
            policy,
            line_height,
            source_image,
            source_image_path,
            ordinal=index + 1,
        )
        snapshot_tables.append(table)
        unassigned.extend(table_unassigned)
    equity, equity_unassigned = _equity_table(
        lines, policy, line_height, source_image, source_image_path
    )
    unassigned.extend(equity_unassigned)
    tables = tuple([*snapshot_tables, equity])
    rows = tuple(row for table in tables for row in table.rows)
    facts = _narrative_facts(lines, policy, line_height)
    source_bbox = _union(lines)
    footer = tuple(
        sorted(
            line.index
            for line in lines
            if line.y_center >= source_bbox.y1 * policy.page_footer_top_ratio
            and _numeric_only(line.text)
        )
    )
    result = ParsedTMPage44(
        input_path=input_path,
        source_sha256=policy.source_ocr_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_pdf_sha256=policy.source_pdf_sha256,
        page_tag=page_tag,
        scope=policy.scope,
        scope_binding=policy.scope_binding,
        tables=tables,
        rows=rows,
        narrative_facts=facts,
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
            "two visible snapshot tables and one four-axis equity movement grid",
            "51 finite values reconstructed from PP-OCRv6 geometry",
            "nine OCR-missing dash cells accepted only from constrained render pixels",
            "five quantitative narrative facts retained as source-only provenance",
            "this parser grants no ReportNormId authority",
        ),
    )
    if (
        len(result.rows) != 24
        or result.numeric_row_count != 20
        or result.label_only_row_count != 4
        or result.financial_slot_count != 60
        or result.observation_count(ObservationKind.VALUE) != 51
        or result.observation_count(ObservationKind.DASH) != 9
        or len(result.narrative_facts) != 5
        or result.narrative_value_count != 7
    ):
        raise TMNoteWordBoxError("TM page-44 page denominator drifted")
    return result


__all__ = [
    "ParsedTMPage44",
    "TMPage44AxisBinding",
    "TMPage44LogicalRow",
    "TMPage44NarrativeFact",
    "TMPage44Policy",
    "TMPage44Table",
    "load_tm_page44_policy",
    "parse_tm_page44",
]
