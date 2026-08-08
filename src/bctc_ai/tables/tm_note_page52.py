"""Hash-bound TM reconstruction for MBB consolidated PDF page 52.

The page contains a two-snapshot related-party balance table and a current-
snapshot geographic concentration matrix.  Qualitative definitions and
percentages are retained as provenance and never become financial cells.
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
from bctc_ai.tables.tm_note_page47 import (
    TMPage47AxisBinding,
    TMPage47LogicalRow,
    TMPage47Table,
    _find_anchor_group,
    _find_anchor_line,
    _number_line,
)
from bctc_ai.tables.tm_note_page51 import TMPage51ExpectedAxis, _snapshot_axes
from bctc_ai.tables.tm_note_word_box import (
    TMNoteRowKind,
    TMNoteWordBoxError,
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
    "narrative_quantity_as_schema_mapping_input",
    "inherited_unit_or_period_as_item_selector",
}
_NARRATIVE_ROLES = (
    "RELATED_PARTY_DEFINITION",
    "GOVERNANCE_COMPENSATION_POLICY",
    "GEOGRAPHIC_CONCENTRATION_INTRODUCTION",
)


@dataclass(frozen=True)
class TMPage52RelatedTableSpec:
    table_key: str
    note_number: str
    title_anchors: tuple[str, ...]
    first_body_anchors: tuple[str, ...]
    header_label_anchors: tuple[str, ...]
    expected_numeric_rows: int
    expected_label_only_rows: int


@dataclass(frozen=True)
class TMPage52GeographicAxisSpec:
    axis_key: str
    header_line_anchors: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class TMPage52GeographicRowSpec:
    row_key: str
    label_anchors: tuple[str, ...]


@dataclass(frozen=True)
class TMPage52GeographicTableSpec:
    table_key: str
    note_number: str
    title_line_anchors: tuple[tuple[str, ...], ...]
    introduction_line_anchors: tuple[tuple[str, ...], ...]
    axes: tuple[TMPage52GeographicAxisSpec, ...]
    rows: tuple[TMPage52GeographicRowSpec, ...]
    snapshot_date: date
    period_role: str
    period_type: str
    unit_binding: str
    expected_numeric_rows: int
    expected_label_only_rows: int


@dataclass(frozen=True)
class TMPage52NarrativeSpec:
    semantic_role: str
    start_anchors: tuple[str, ...]
    end_before_anchors: tuple[str, ...]
    expected_line_count: int


@dataclass(frozen=True)
class TMPage52Policy:
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
    maximum_date_to_unit_center_distance_line_heights: float
    minimum_axis_separation_line_heights: float
    numeric_cluster_line_heights: float
    label_attach_line_heights: float
    page_footer_top_ratio: float
    related_expected_axes: tuple[TMPage51ExpectedAxis, ...]
    related_table: TMPage52RelatedTableSpec
    geographic_table: TMPage52GeographicTableSpec
    narratives: tuple[TMPage52NarrativeSpec, ...]
    page_52_closes_note_3: bool
    page_53_starts_note_number: str
    page_53_start_anchors: tuple[str, ...]
    forbidden_semantic_inputs: tuple[str, ...]

    @property
    def expected_axes(self) -> tuple[TMPage51ExpectedAxis, ...]:
        """Compatibility view used by the shared visible snapshot binder."""

        return self.related_expected_axes


@dataclass(frozen=True)
class TMPage52NarrativeRecord:
    narrative_id: str
    semantic_role: str
    raw_text: str
    source_line_indices: tuple[int, ...]
    source_bbox: BoundingBox
    quantities: tuple[Decimal, ...]
    quantity_units: tuple[str, ...]
    mapping_approved: bool


@dataclass(frozen=True)
class ParsedTMPage52:
    input_path: str
    source_sha256: str
    upstream_ocr_sha256: str
    source_render_sha256: str
    source_pdf_sha256: str
    page_tag: str
    scope: str
    scope_binding: str
    tables: tuple[TMPage47Table, ...]
    rows: tuple[TMPage47LogicalRow, ...]
    narratives: tuple[TMPage52NarrativeRecord, ...]
    line_height: float
    source_ocr_bbox: BoundingBox
    table_bbox: BoundingBox
    narrative_bbox: BoundingBox
    unassigned_numeric_line_indices: tuple[int, ...]
    excluded_artifact_line_indices: tuple[int, ...]
    excluded_footer_numeric_line_indices: tuple[int, ...]
    continues_to_page_53: bool
    next_page_note_number: str
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


def _anchors(payload: Any, field: str) -> tuple[str, ...]:
    if not isinstance(payload, list) or not payload:
        raise TMNoteWordBoxError(f"TM page-52 {field} anchors are invalid")
    result = tuple(retrieval_key(str(value)) for value in payload)
    if any(not value for value in result):
        raise TMNoteWordBoxError(f"TM page-52 {field} contains an empty anchor")
    return result


def _anchor_groups(payload: Any, field: str) -> tuple[tuple[str, ...], ...]:
    if not isinstance(payload, list) or not payload:
        raise TMNoteWordBoxError(f"TM page-52 {field} groups are invalid")
    return tuple(_anchors(group, f"{field} line") for group in payload)


def _positive(payload: dict[str, Any], field: str) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise TMNoteWordBoxError(f"invalid positive TM page-52 setting: {field}")
    return float(value)


def _date_value(value: Any, field: str) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise TMNoteWordBoxError(f"invalid TM page-52 {field}") from exc
    raise TMNoteWordBoxError(f"invalid TM page-52 {field}")


def load_tm_page52_policy(path: Path) -> TMPage52Policy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMNoteWordBoxError(f"cannot load TM page-52 policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE52_RELATED_PARTY_AND_GEOGRAPHIC_CONCENTRATION_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 52
        or payload.get("page_tag") != "page-0052"
        or payload.get("scope") != "CONSOLIDATED"
    ):
        raise TMNoteWordBoxError("TM page-52 policy identity drifted")
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
        raise TMNoteWordBoxError("TM page-52 source hashes are invalid")
    thresholds = tuple(
        payload.get(field)
        for field in ("minimum_line_score", "minimum_anchor_similarity", "minimum_unit_similarity")
    )
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1
        for value in thresholds
    ):
        raise TMNoteWordBoxError("TM page-52 similarity thresholds are invalid")
    unit = payload.get("unit")
    related = payload.get("related_party_table")
    geographic = payload.get("geographic_table")
    geometry = payload.get("geometry")
    continuation = payload.get("continuation")
    if not all(
        isinstance(value, dict) for value in (unit, related, geographic, geometry, continuation)
    ):
        raise TMNoteWordBoxError("TM page-52 policy sections are incomplete")
    multiplier = unit.get("multiplier")
    canonical = unit.get("canonical")
    if (
        isinstance(multiplier, bool)
        or not isinstance(multiplier, int)
        or multiplier <= 0
        or not isinstance(canonical, str)
        or not canonical
    ):
        raise TMNoteWordBoxError("TM page-52 unit binding is invalid")

    raw_expected_axes = related.get("expected_axes")
    if not isinstance(raw_expected_axes, list) or len(raw_expected_axes) != 2:
        raise TMNoteWordBoxError("TM page-52 related-party axes are invalid")
    related_expected_axes = tuple(
        TMPage51ExpectedAxis(
            role=str(record.get("role")),
            snapshot_date=_date_value(record.get("date"), "related snapshot date"),
        )
        for record in raw_expected_axes
        if isinstance(record, dict)
    )
    if tuple(axis.role for axis in related_expected_axes) != ("CURRENT", "COMPARATIVE"):
        raise TMNoteWordBoxError("TM page-52 related-party axis order drifted")
    if (
        related.get("table_key") != "RELATED_PARTY_BALANCES"
        or related.get("note_number") != "2"
        or related.get("expected_numeric_rows") != 2
        or related.get("expected_label_only_rows") != 1
    ):
        raise TMNoteWordBoxError("TM page-52 related-party denominator drifted")
    related_spec = TMPage52RelatedTableSpec(
        table_key="RELATED_PARTY_BALANCES",
        note_number="2",
        title_anchors=_anchors(related.get("title_anchors"), "related-party title"),
        first_body_anchors=_anchors(related.get("first_body_anchors"), "related first body"),
        header_label_anchors=_anchors(related.get("header_label_anchors"), "related header"),
        expected_numeric_rows=2,
        expected_label_only_rows=1,
    )

    raw_geo_axes = geographic.get("axes")
    raw_geo_rows = geographic.get("row_anchors")
    if not isinstance(raw_geo_axes, list) or len(raw_geo_axes) != 4:
        raise TMNoteWordBoxError("TM page-52 geographic axes are invalid")
    if not isinstance(raw_geo_rows, list) or len(raw_geo_rows) != 2:
        raise TMNoteWordBoxError("TM page-52 geographic rows are invalid")
    geo_axes = tuple(
        TMPage52GeographicAxisSpec(
            axis_key=str(record.get("axis_key")),
            header_line_anchors=_anchor_groups(
                record.get("header_line_anchors"), "geographic axis header"
            ),
        )
        for record in raw_geo_axes
        if isinstance(record, dict)
    )
    geo_rows = tuple(
        TMPage52GeographicRowSpec(
            row_key=str(record.get("row_key")),
            label_anchors=_anchors(record.get("label_anchors"), "geographic row"),
        )
        for record in raw_geo_rows
        if isinstance(record, dict)
    )
    if tuple(axis.axis_key for axis in geo_axes) != (
        "CUSTOMER_LOANS",
        "CUSTOMER_DEPOSITS",
        "LC_COMMITMENTS",
        "SECURITIES",
    ) or tuple(row.row_key for row in geo_rows) != ("DOMESTIC", "FOREIGN"):
        raise TMNoteWordBoxError("TM page-52 geographic axis/row identity drifted")
    if (
        geographic.get("table_key") != "GEOGRAPHIC_CONCENTRATION"
        or geographic.get("note_number") != "3"
        or geographic.get("period_role") != "CURRENT"
        or geographic.get("period_type") != "SNAPSHOT"
        or geographic.get("expected_numeric_rows") != 2
        or geographic.get("expected_label_only_rows") != 1
    ):
        raise TMNoteWordBoxError("TM page-52 geographic denominator drifted")
    geographic_spec = TMPage52GeographicTableSpec(
        table_key="GEOGRAPHIC_CONCENTRATION",
        note_number="3",
        title_line_anchors=_anchor_groups(geographic.get("title_line_anchors"), "geographic title"),
        introduction_line_anchors=_anchor_groups(
            geographic.get("introduction_line_anchors"), "geographic introduction"
        ),
        axes=geo_axes,
        rows=geo_rows,
        snapshot_date=_date_value(geographic.get("snapshot_date"), "geographic snapshot"),
        period_role="CURRENT",
        period_type="SNAPSHOT",
        unit_binding=str(geographic.get("unit_binding", "")),
        expected_numeric_rows=2,
        expected_label_only_rows=1,
    )

    raw_narratives = payload.get("narratives")
    if not isinstance(raw_narratives, list) or len(raw_narratives) != 3:
        raise TMNoteWordBoxError("TM page-52 narrative list is incomplete")
    narratives = tuple(
        TMPage52NarrativeSpec(
            semantic_role=str(record.get("semantic_role")),
            start_anchors=_anchors(record.get("start_anchors"), "narrative start"),
            end_before_anchors=_anchors(record.get("end_before_anchors"), "narrative end"),
            expected_line_count=int(record.get("expected_line_count", 0)),
        )
        for record in raw_narratives
        if isinstance(record, dict)
    )
    if tuple(record.semantic_role for record in narratives) != _NARRATIVE_ROLES or any(
        record.expected_line_count <= 0 for record in narratives
    ):
        raise TMNoteWordBoxError("TM page-52 narrative identity drifted")
    if (
        continuation.get("page_52_closes_note_3") is not True
        or continuation.get("page_53_starts_note_number") != "4"
    ):
        raise TMNoteWordBoxError("TM page-52 continuation boundary drifted")
    forbidden = payload.get("forbidden_semantic_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMNoteWordBoxError("TM page-52 forbidden semantic inputs drifted")
    footer_ratio = _positive(geometry, "page_footer_top_ratio")
    if footer_ratio >= 1:
        raise TMNoteWordBoxError("TM page-52 footer ratio must be below one")
    return TMPage52Policy(
        source_path=path,
        document=str(payload.get("document", "")),
        page_number=52,
        page_tag="page-0052",
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
        canonical_unit=canonical,
        unit_multiplier=multiplier,
        maximum_date_to_unit_center_distance_line_heights=_positive(
            geometry, "maximum_date_to_unit_center_distance_line_heights"
        ),
        minimum_axis_separation_line_heights=_positive(
            geometry, "minimum_axis_separation_line_heights"
        ),
        numeric_cluster_line_heights=_positive(geometry, "numeric_cluster_line_heights"),
        label_attach_line_heights=_positive(geometry, "label_attach_line_heights"),
        page_footer_top_ratio=footer_ratio,
        related_expected_axes=related_expected_axes,
        related_table=related_spec,
        geographic_table=geographic_spec,
        narratives=narratives,
        page_52_closes_note_3=True,
        page_53_starts_note_number="4",
        page_53_start_anchors=_anchors(continuation.get("page_53_start_anchors"), "page-53 start"),
        forbidden_semantic_inputs=tuple(str(value) for value in forbidden),
    )


def _structural_row(
    *,
    page_tag: str,
    table_key: str,
    note_number: str,
    label_lines: tuple[_Line, ...],
    source_lines: tuple[_Line, ...],
    axis_count: int,
) -> TMPage47LogicalRow:
    return TMPage47LogicalRow(
        row_id="",
        table_key=table_key,
        note_number=note_number,
        ordinal=0,
        row=ReaderRow(
            source_row_ids=_source_ids(page_tag, list(source_lines)),
            label=normalize_text(" ".join(line.text for line in label_lines)),
            note_reference=note_number,
            cells=tuple(parse_financial_number(None) for _ in range(axis_count)),
        ),
        row_kind=TMNoteRowKind.LABEL_ONLY,
        source_role="NOTE_TITLE",
        y_anchor=statistics.fmean(line.y_center for line in label_lines),
        label_bbox=_union(label_lines),
        value_bboxes=tuple(None for _ in range(axis_count)),
        label_line_indices=tuple(line.index for line in label_lines),
        value_line_indices=tuple(() for _ in range(axis_count)),
        visual_cell_evidence=tuple(None for _ in range(axis_count)),
        cell_period_starts=tuple(None for _ in range(axis_count)),
        cell_period_ends=tuple(None for _ in range(axis_count)),
        cell_period_roles=tuple(None for _ in range(axis_count)),
        mapping_approved=False,
    )


def _numeric_row(
    *,
    page_tag: str,
    table_key: str,
    note_number: str,
    label_line: _Line | None,
    value_lines: tuple[_Line, ...],
    axes: tuple[TMPage47AxisBinding, ...],
    source_role: str,
) -> TMPage47LogicalRow:
    per_axis: list[list[_Line]] = [[] for _ in axes]
    for line in value_lines:
        target = min(
            range(len(axes)), key=lambda index: abs(axes[index].axis_right_edge - line.x_right)
        )
        per_axis[target].append(line)
    if any(len(lines) != 1 for lines in per_axis):
        raise TMNoteWordBoxError(f"TM page-52 {table_key} numeric axis assignment drifted")
    cells = tuple(parse_financial_number(lines[0].text) for lines in per_axis)
    if any(cell.observation not in {ObservationKind.VALUE, ObservationKind.ZERO} for cell in cells):
        raise TMNoteWordBoxError(f"TM page-52 {table_key} has a non-value numeric cell")
    source_lines = [*([] if label_line is None else [label_line]), *value_lines]
    return TMPage47LogicalRow(
        row_id="",
        table_key=table_key,
        note_number=note_number,
        ordinal=0,
        row=ReaderRow(
            source_row_ids=_source_ids(page_tag, source_lines),
            label="" if label_line is None else normalize_text(label_line.text),
            note_reference=note_number,
            cells=cells,
        ),
        row_kind=TMNoteRowKind.NUMERIC,
        source_role=source_role,
        y_anchor=statistics.fmean(line.y_center for line in value_lines),
        label_bbox=None if label_line is None else label_line.bbox,
        value_bboxes=tuple(_union(lines) for lines in per_axis),
        label_line_indices=() if label_line is None else (label_line.index,),
        value_line_indices=tuple(tuple(line.index for line in lines) for lines in per_axis),
        visual_cell_evidence=tuple(None for _ in axes),
        cell_period_starts=tuple(axis.period_start for axis in axes),
        cell_period_ends=tuple(axis.period_end for axis in axes),
        cell_period_roles=tuple(axis.current_or_comparative for axis in axes),
        mapping_approved=False,
    )


def _renumber(
    rows: tuple[TMPage47LogicalRow, ...], *, page_tag: str, table_key: str
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


def _geographic_axes(
    lines: tuple[_Line, ...],
    policy: TMPage52Policy,
    line_height: float,
    *,
    minimum_y: float,
    maximum_y: float,
) -> tuple[TMPage47AxisBinding, ...]:
    result = []
    previous_right = float("-inf")
    for ordinal, spec in enumerate(policy.geographic_table.axes, start=1):
        group = _find_anchor_group(
            lines,
            spec.header_line_anchors,
            policy,
            line_height,
            minimum_y=minimum_y,
            maximum_y=maximum_y,
        )
        right_edge = max(line.x_right for line in group)
        if right_edge <= previous_right:
            raise TMNoteWordBoxError("TM page-52 geographic header order drifted")
        previous_right = right_edge
        result.append(
            TMPage47AxisBinding(
                ordinal=ordinal,
                axis_id=f"snapshot-current-{spec.axis_key.lower()}",
                axis_right_edge=right_edge,
                raw_header_text=normalize_text(" ".join(line.text for line in group)),
                header_line_indices=tuple(line.index for line in group),
                current_or_comparative=policy.geographic_table.period_role,
                canonical_unit=policy.canonical_unit,
                unit_multiplier=policy.unit_multiplier,
                period_start=policy.geographic_table.snapshot_date,
                period_end=policy.geographic_table.snapshot_date,
                period_type=policy.geographic_table.period_type,
                header_bbox=_union(group),
                unit_bbox=_union(group),
                evidence=(
                    "financial concept bound from the visible matrix column header",
                    "current snapshot bound from the page-52 note and report date context",
                    "VND-million unit inherited from the explicit page-local unit context",
                ),
            )
        )
    return tuple(result)


def _narratives(
    lines: tuple[_Line, ...], policy: TMPage52Policy
) -> tuple[TMPage52NarrativeRecord, ...]:
    records = []
    for ordinal, spec in enumerate(policy.narratives, start=1):
        start = _find_anchor_line(lines, spec.start_anchors, policy)
        end = _find_anchor_line(lines, spec.end_before_anchors, policy, minimum_y=start.y_center)
        group = tuple(
            sorted(
                (
                    line
                    for line in lines
                    if start.y_center <= line.y_center < end.y_center
                    and normalize_text(line.text)
                    and not _numeric_only(line.text)
                ),
                key=lambda line: (line.y_center, line.bbox.x0, line.index),
            )
        )
        if len(group) != spec.expected_line_count or group[0].index != start.index:
            raise TMNoteWordBoxError(
                f"TM page-52 narrative denominator drifted: {spec.semantic_role}"
            )
        raw_text = normalize_text(" ".join(line.text for line in group))
        quantities = tuple(
            Decimal(token.replace(",", ".")) for token in _PERCENTAGE.findall(raw_text)
        )
        records.append(
            TMPage52NarrativeRecord(
                narrative_id=f"page-0052:narrative-{ordinal:04d}",
                semantic_role=spec.semantic_role,
                raw_text=raw_text,
                source_line_indices=tuple(line.index for line in group),
                source_bbox=_union(group),
                quantities=quantities,
                quantity_units=tuple("PERCENT" for _ in quantities),
                mapping_approved=False,
            )
        )
    return tuple(records)


def parse_tm_page52(
    result_path: Path,
    source_image_path: Path,
    policy: TMPage52Policy,
    *,
    page_tag: str = "page-0052",
) -> ParsedTMPage52:
    """Reconstruct page 52 while keeping schema authority disabled."""

    if page_tag != policy.page_tag:
        raise TMNoteWordBoxError("TM page-52 page tag drifted")
    if sha256_file(result_path) != policy.source_ocr_sha256:
        raise TMNoteWordBoxError("TM page-52 compact OCR fixture hash drifted")
    if sha256_file(source_image_path) != policy.source_render_sha256:
        raise TMNoteWordBoxError("TM page-52 source render hash drifted")
    if cv2.imread(str(source_image_path), cv2.IMREAD_GRAYSCALE) is None:
        raise TMNoteWordBoxError("TM page-52 source render cannot be decoded")
    input_path, lines, metadata = _load_lines(result_path, policy.minimum_line_score)
    if metadata != {
        "upstream_ocr_sha256": policy.upstream_ocr_sha256,
        "source_render_sha256": policy.source_render_sha256,
        "source_pdf_sha256": policy.source_pdf_sha256,
    }:
        raise TMNoteWordBoxError("TM page-52 compact OCR provenance drifted")
    nonempty = tuple(line for line in lines if normalize_text(line.text))
    line_height = float(statistics.median(line.height for line in nonempty))
    if line_height <= 0:
        raise TMNoteWordBoxError("TM page-52 line height is invalid")
    source_bbox = _union(lines)
    footer_top = source_bbox.y1 * policy.page_footer_top_ratio

    related_title = _find_anchor_line(lines, policy.related_table.title_anchors, policy)
    related_number = _number_line(
        lines, policy.related_table.note_number, related_title, line_height
    )
    related_first_body = _find_anchor_line(
        lines,
        policy.related_table.first_body_anchors,
        policy,
        minimum_y=related_title.y_center,
    )
    related_header = _find_anchor_line(
        lines,
        policy.related_table.header_label_anchors,
        policy,
        minimum_y=related_title.y_center,
        maximum_y=related_first_body.y_center,
    )
    related_axes = _snapshot_axes(lines, related_title, related_first_body, policy, line_height)
    geographic_title_group = _find_anchor_group(
        lines,
        policy.geographic_table.title_line_anchors,
        policy,
        line_height,
        minimum_y=related_first_body.y_center,
        maximum_y=footer_top,
    )
    geographic_number = _number_line(
        lines,
        policy.geographic_table.note_number,
        geographic_title_group[0],
        line_height,
    )
    related_numeric = [
        line
        for line in lines
        if related_header.bbox.y1 < line.y_center < geographic_title_group[0].bbox.y0
        and _numeric_only(line.text)
    ]
    related_groups = _clusters(related_numeric, line_height * policy.numeric_cluster_line_heights)
    if len(related_groups) != 2 or any(len(group) != 2 for group in related_groups):
        raise TMNoteWordBoxError("TM page-52 related-party numeric grid drifted")
    related_rows = _renumber(
        (
            _structural_row(
                page_tag=page_tag,
                table_key=policy.related_table.table_key,
                note_number=policy.related_table.note_number,
                label_lines=(related_title,),
                source_lines=(related_number, related_title),
                axis_count=2,
            ),
            _numeric_row(
                page_tag=page_tag,
                table_key=policy.related_table.table_key,
                note_number=policy.related_table.note_number,
                label_line=related_first_body,
                value_lines=tuple(related_groups[0]),
                axes=related_axes,
                source_role="DETAIL",
            ),
            _numeric_row(
                page_tag=page_tag,
                table_key=policy.related_table.table_key,
                note_number=policy.related_table.note_number,
                label_line=None,
                value_lines=tuple(related_groups[1]),
                axes=related_axes,
                source_role="PRINTED_TOTAL_UNLABELED",
            ),
        ),
        page_tag=page_tag,
        table_key=policy.related_table.table_key,
    )
    related_table = TMPage47Table(
        ordinal=1,
        table_key=policy.related_table.table_key,
        note_number=policy.related_table.note_number,
        title=normalize_text(related_title.text),
        title_line_indices=(related_title.index,),
        axes=related_axes,
        rows=related_rows,
        bbox=_union(
            tuple(
                line
                for line in lines
                if related_title.bbox.y0 <= line.y_center < geographic_title_group[0].bbox.y0
            )
        ),
    )

    geographic_intro = _find_anchor_group(
        lines,
        policy.geographic_table.introduction_line_anchors,
        policy,
        line_height,
        minimum_y=geographic_title_group[-1].y_center,
        maximum_y=footer_top,
    )
    first_geo_label = _find_anchor_line(
        lines,
        policy.geographic_table.rows[0].label_anchors,
        policy,
        minimum_y=geographic_intro[-1].y_center,
        maximum_y=footer_top,
    )
    geo_axes = _geographic_axes(
        lines,
        policy,
        line_height,
        minimum_y=geographic_intro[-1].y_center,
        maximum_y=first_geo_label.y_center,
    )
    geo_labels = tuple(
        _find_anchor_line(
            lines,
            spec.label_anchors,
            policy,
            minimum_y=geographic_intro[-1].y_center,
            maximum_y=footer_top,
        )
        for spec in policy.geographic_table.rows
    )
    if tuple(label.y_center for label in geo_labels) != tuple(
        sorted(label.y_center for label in geo_labels)
    ):
        raise TMNoteWordBoxError("TM page-52 geographic row order drifted")
    geo_header_bottom = max(axis.header_bbox.y1 for axis in geo_axes)
    geo_numeric = [
        line
        for line in lines
        if geo_header_bottom < line.y_center < footer_top and _numeric_only(line.text)
    ]
    geo_groups = _clusters(geo_numeric, line_height * policy.numeric_cluster_line_heights)
    if len(geo_groups) != 2 or any(len(group) != 4 for group in geo_groups):
        raise TMNoteWordBoxError("TM page-52 geographic numeric grid drifted")
    for label, group in zip(geo_labels, geo_groups, strict=True):
        if (
            abs(label.y_center - statistics.fmean(line.y_center for line in group))
            > line_height * policy.label_attach_line_heights
        ):
            raise TMNoteWordBoxError("TM page-52 geographic label attachment drifted")
    geo_rows = _renumber(
        (
            _structural_row(
                page_tag=page_tag,
                table_key=policy.geographic_table.table_key,
                note_number=policy.geographic_table.note_number,
                label_lines=geographic_title_group,
                source_lines=(geographic_number, *geographic_title_group),
                axis_count=4,
            ),
            *(
                _numeric_row(
                    page_tag=page_tag,
                    table_key=policy.geographic_table.table_key,
                    note_number=policy.geographic_table.note_number,
                    label_line=label,
                    value_lines=tuple(group),
                    axes=geo_axes,
                    source_role=spec.row_key,
                )
                for spec, label, group in zip(
                    policy.geographic_table.rows, geo_labels, geo_groups, strict=True
                )
            ),
        ),
        page_tag=page_tag,
        table_key=policy.geographic_table.table_key,
    )
    geographic_table = TMPage47Table(
        ordinal=2,
        table_key=policy.geographic_table.table_key,
        note_number=policy.geographic_table.note_number,
        title=normalize_text(" ".join(line.text for line in geographic_title_group)),
        title_line_indices=tuple(line.index for line in geographic_title_group),
        axes=geo_axes,
        rows=geo_rows,
        bbox=_union(
            tuple(
                line
                for line in lines
                if geographic_title_group[0].bbox.y0 <= line.y_center < footer_top
            )
        ),
    )
    narratives = _narratives(lines, policy)
    rows = (*related_rows, *geo_rows)
    footer = tuple(
        sorted(
            line.index for line in lines if line.y_center >= footer_top and _numeric_only(line.text)
        )
    )
    artifacts = tuple(sorted(line.index for line in lines if not normalize_text(line.text)))
    used_numeric = {
        index for row in rows for indices in row.value_line_indices for index in indices
    }
    relevant_numeric = {line.index for line in (*related_numeric, *geo_numeric)}
    unassigned = tuple(sorted(relevant_numeric - used_numeric))
    result = ParsedTMPage52(
        input_path=input_path,
        source_sha256=policy.source_ocr_sha256,
        upstream_ocr_sha256=policy.upstream_ocr_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_pdf_sha256=policy.source_pdf_sha256,
        page_tag=page_tag,
        scope=policy.scope,
        scope_binding=policy.scope_binding,
        tables=(related_table, geographic_table),
        rows=rows,
        narratives=narratives,
        line_height=line_height,
        source_ocr_bbox=source_bbox,
        table_bbox=BoundingBox(
            min(table.bbox.x0 for table in (related_table, geographic_table)),
            min(table.bbox.y0 for table in (related_table, geographic_table)),
            max(table.bbox.x1 for table in (related_table, geographic_table)),
            max(table.bbox.y1 for table in (related_table, geographic_table)),
        ),
        narrative_bbox=BoundingBox(
            min(record.source_bbox.x0 for record in narratives),
            min(record.source_bbox.y0 for record in narratives),
            max(record.source_bbox.x1 for record in narratives),
            max(record.source_bbox.y1 for record in narratives),
        ),
        unassigned_numeric_line_indices=unassigned,
        excluded_artifact_line_indices=artifacts,
        excluded_footer_numeric_line_indices=footer,
        continues_to_page_53=not policy.page_52_closes_note_3,
        next_page_note_number=policy.page_53_starts_note_number,
        mapping_authority=False,
        evidence=(
            "two independent page-52 source tables reconstructed from immutable PP-OCR boxes",
            "related-party current/comparative snapshots use visible dates and local units",
            "geographic matrix retains four concept axes and two geography rows",
            "the geographic snapshot and VND-million unit are context-bound, never item selectors",
            "all narrative percentages remain non-financial provenance",
            "page 52 closes note V.3; immutable page 53 starts independent note V.4",
            "schema identifiers are absent from parser inputs and mapping authority remains false",
        ),
    )
    if (
        len(result.rows) != 6
        or result.numeric_row_count != 4
        or result.label_only_row_count != 2
        or result.financial_slot_count != 12
        or result.observation_count(ObservationKind.VALUE) != 12
        or result.observation_count(ObservationKind.DASH) != 0
        or result.observation_count(ObservationKind.BLANK) != 0
        or len(result.narratives) != 3
        or result.narrative_quantity_count != 3
        or result.unassigned_numeric_line_indices
        or result.excluded_artifact_line_indices != (36,)
        or result.excluded_footer_numeric_line_indices != (63,)
        or result.continues_to_page_53
        or result.next_page_note_number != "4"
    ):
        raise TMNoteWordBoxError(
            "TM page-52 exact source denominator drifted: "
            f"rows={len(result.rows)}, numeric={result.numeric_row_count}, "
            f"structural={result.label_only_row_count}, slots={result.financial_slot_count}, "
            f"value={result.observation_count(ObservationKind.VALUE)}, "
            f"dash={result.observation_count(ObservationKind.DASH)}, "
            f"blank={result.observation_count(ObservationKind.BLANK)}, "
            f"narratives={len(result.narratives)}, quantities={result.narrative_quantity_count}, "
            f"unassigned={result.unassigned_numeric_line_indices}, "
            f"artifacts={result.excluded_artifact_line_indices}, "
            f"footer={result.excluded_footer_numeric_line_indices}"
        )
    return result


__all__ = [
    "ParsedTMPage52",
    "TMPage52NarrativeRecord",
    "TMPage52Policy",
    "load_tm_page52_policy",
    "parse_tm_page52",
]
