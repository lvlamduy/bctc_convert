"""Hash-bound snapshot TM reconstruction for MBB consolidated PDF page 51.

The page contains one complete off-balance commitment table followed by
qualitative risk explanations.  Narrative percentages are retained as
provenance, but are excluded from the financial row/cell denominator.
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
from bctc_ai.core.text import normalize_text, parse_vietnamese_date, retrieval_key
from bctc_ai.evaluation.word_box_rows_v3 import load_word_box_reconstruction_v3_config
from bctc_ai.tables.tm_note_page47 import (
    TMPage47AxisBinding,
    TMPage47LogicalRow,
    TMPage47Table,
    TMPage47TableSpec,
    _find_anchor_line,
    _reconstruct_table,
)
from bctc_ai.tables.tm_note_word_box import (
    TMNoteRowKind,
    TMNoteWordBoxError,
    _best_anchor_similarity,
    _Line,
    _load_lines,
    _numeric_only,
    _union,
)

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
    "narrative_text_as_financial_statement_value",
    "narrative_quantity_as_schema_mapping_input",
}
_NARRATIVE_ROLES = (
    "CONTINGENT_LIABILITIES_HEADING",
    "OFF_BALANCE_OVERVIEW",
    "CREDIT_RISK_DEFINITION",
    "FINANCIAL_GUARANTEE_DEFINITION",
    "SIGHT_LC_RISK",
    "DEFERRED_LC_RISK",
    "COLLATERAL_RANGE",
)


@dataclass(frozen=True)
class TMPage51ExpectedAxis:
    role: str
    snapshot_date: date


@dataclass(frozen=True)
class TMPage51NarrativeSpec:
    semantic_role: str
    start_anchors: tuple[str, ...]
    expected_line_count: int


@dataclass(frozen=True)
class TMPage51Policy:
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
    expected_axes: tuple[TMPage51ExpectedAxis, ...]
    numeric_axis_max_distance_ratio: float
    numeric_axis_right_overrun_line_heights: float
    row_anchor_cluster_line_heights: float
    label_direct_attach_line_heights: float
    note_reference_left_gap_axis_widths: float
    artifact_minimum_x_ratio: float
    page_footer_top_ratio: float
    dash_config: dict[str, float | int]
    dash_config_path: Path
    table: TMPage47TableSpec
    narratives: tuple[TMPage51NarrativeSpec, ...]
    forbidden_semantic_inputs: tuple[str, ...]


@dataclass(frozen=True)
class TMPage51NarrativeRecord:
    narrative_id: str
    semantic_role: str
    raw_text: str
    source_line_indices: tuple[int, ...]
    source_bbox: BoundingBox
    quantities: tuple[Decimal, ...]
    quantity_units: tuple[str, ...]
    mapping_approved: bool


@dataclass(frozen=True)
class ParsedTMPage51:
    input_path: str
    source_sha256: str
    upstream_ocr_sha256: str
    source_render_sha256: str
    source_pdf_sha256: str
    page_tag: str
    scope: str
    scope_binding: str
    axes: tuple[TMPage47AxisBinding, ...]
    tables: tuple[TMPage47Table, ...]
    rows: tuple[TMPage47LogicalRow, ...]
    narratives: tuple[TMPage51NarrativeRecord, ...]
    line_height: float
    source_ocr_bbox: BoundingBox
    table_bbox: BoundingBox
    narrative_bbox: BoundingBox
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
        raise TMNoteWordBoxError(f"TM page-51 {field} anchors are invalid")
    result = tuple(retrieval_key(str(value)) for value in payload)
    if any(not value for value in result):
        raise TMNoteWordBoxError(f"TM page-51 {field} contains an empty anchor")
    return result


def _positive(payload: dict[str, Any], field: str) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise TMNoteWordBoxError(f"invalid positive TM page-51 setting: {field}")
    return float(value)


def _date_value(value: Any, field: str) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise TMNoteWordBoxError(f"invalid TM page-51 {field}") from exc
    raise TMNoteWordBoxError(f"invalid TM page-51 {field}")


def load_tm_page51_policy(path: Path) -> TMPage51Policy:
    """Load the source-scoped reconstruction contract for PDF page 51."""

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMNoteWordBoxError(f"cannot load TM page-51 policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE51_SNAPSHOT_OFF_BALANCE_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 51
        or payload.get("page_tag") != "page-0051"
        or payload.get("scope") != "CONSOLIDATED"
    ):
        raise TMNoteWordBoxError("TM page-51 policy identity drifted")
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
        raise TMNoteWordBoxError("TM page-51 source hashes are invalid")
    thresholds = tuple(
        payload.get(field)
        for field in ("minimum_line_score", "minimum_anchor_similarity", "minimum_unit_similarity")
    )
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1
        for value in thresholds
    ):
        raise TMNoteWordBoxError("TM page-51 similarity thresholds are invalid")
    unit = payload.get("unit")
    header = payload.get("header_geometry")
    geometry = payload.get("table_geometry")
    table = payload.get("table")
    if not all(isinstance(value, dict) for value in (unit, header, geometry, table)):
        raise TMNoteWordBoxError("TM page-51 unit/header/table geometry is incomplete")
    multiplier = unit.get("multiplier")
    canonical = unit.get("canonical")
    if (
        isinstance(multiplier, bool)
        or not isinstance(multiplier, int)
        or multiplier <= 0
        or not isinstance(canonical, str)
        or not canonical
    ):
        raise TMNoteWordBoxError("TM page-51 unit binding is invalid")
    raw_axes = header.get("expected_axes")
    if not isinstance(raw_axes, list) or len(raw_axes) != 2:
        raise TMNoteWordBoxError("TM page-51 must define two snapshot axes")
    expected_axes = []
    for record in raw_axes:
        if not isinstance(record, dict) or record.get("role") not in {"CURRENT", "COMPARATIVE"}:
            raise TMNoteWordBoxError("TM page-51 snapshot-axis record is invalid")
        expected_axes.append(
            TMPage51ExpectedAxis(
                role=str(record["role"]),
                snapshot_date=_date_value(record.get("date"), "snapshot date"),
            )
        )
    if tuple(axis.role for axis in expected_axes) != ("CURRENT", "COMPARATIVE"):
        raise TMNoteWordBoxError("TM page-51 snapshot-axis order drifted")
    dash_name = payload.get("dash_detector_config")
    if not isinstance(dash_name, str) or Path(dash_name).name != dash_name:
        raise TMNoteWordBoxError("TM page-51 dash detector path is invalid")
    dash_path = (path.parent / dash_name).resolve()
    if not dash_path.is_file() or sha256_file(dash_path) != payload.get(
        "dash_detector_config_sha256"
    ):
        raise TMNoteWordBoxError("TM page-51 dash detector is absent or drifted")
    numeric_rows = table.get("expected_numeric_rows")
    label_rows = table.get("expected_label_only_rows")
    if (
        table.get("table_key") != "OFF_BALANCE_COMMITMENTS"
        or table.get("note_number") != "1"
        or numeric_rows != 9
        or label_rows != 2
    ):
        raise TMNoteWordBoxError("TM page-51 exact table denominator drifted")
    table_spec = TMPage47TableSpec(
        table_key="OFF_BALANCE_COMMITMENTS",
        note_number="1",
        title_anchors=_anchors(table.get("title_anchors"), "table title"),
        body_end_anchors=_anchors(table.get("body_end_anchors"), "body end"),
        first_body_anchors=_anchors(table.get("first_body_anchors"), "first body"),
        section_title_anchors=_anchors(table.get("section_title_anchors"), "section title"),
        structural_rows=(),
        wrapped_label_rows=(),
        dash_label_anchors=(),
        expected_numeric_rows=9,
        expected_label_only_rows=2,
    )
    raw_narratives = payload.get("narratives")
    if not isinstance(raw_narratives, list) or len(raw_narratives) != len(_NARRATIVE_ROLES):
        raise TMNoteWordBoxError("TM page-51 narrative list is incomplete")
    narratives = []
    for record in raw_narratives:
        if not isinstance(record, dict):
            raise TMNoteWordBoxError("TM page-51 narrative record is invalid")
        role = record.get("semantic_role")
        line_count = record.get("expected_line_count")
        if (
            not isinstance(role, str)
            or isinstance(line_count, bool)
            or not isinstance(line_count, int)
            or line_count <= 0
        ):
            raise TMNoteWordBoxError("TM page-51 narrative fields are invalid")
        narratives.append(
            TMPage51NarrativeSpec(
                semantic_role=role,
                start_anchors=_anchors(record.get("start_anchors"), "narrative start"),
                expected_line_count=line_count,
            )
        )
    if tuple(record.semantic_role for record in narratives) != _NARRATIVE_ROLES:
        raise TMNoteWordBoxError("TM page-51 narrative order drifted")
    forbidden = payload.get("forbidden_semantic_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMNoteWordBoxError("TM page-51 forbidden semantic inputs drifted")
    footer_ratio = _positive(geometry, "page_footer_top_ratio")
    artifact_ratio = _positive(geometry, "artifact_minimum_x_ratio")
    if footer_ratio >= 1 or artifact_ratio >= 1:
        raise TMNoteWordBoxError("TM page-51 page ratios must be below one")
    dash_config = load_word_box_reconstruction_v3_config(dash_path).base.base
    return TMPage51Policy(
        source_path=path,
        document=str(payload.get("document", "")),
        page_number=51,
        page_tag="page-0051",
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
        table=table_spec,
        narratives=tuple(narratives),
        forbidden_semantic_inputs=tuple(str(value) for value in forbidden),
    )


def _snapshot_axes(
    lines: tuple[_Line, ...],
    title: _Line,
    first_body: _Line,
    policy: TMPage51Policy,
    line_height: float,
) -> tuple[TMPage47AxisBinding, ...]:
    candidates = tuple(
        line for line in lines if title.y_center < line.y_center < first_body.y_center
    )
    date_lines = tuple(line for line in candidates if parse_vietnamese_date(line.text) is not None)
    unit_lines = tuple(
        line
        for line in candidates
        if not any(character.isdigit() for character in retrieval_key(line.text))
        and _best_anchor_similarity(line.text, policy.unit_anchors)
        >= policy.minimum_unit_similarity
    )
    if len(date_lines) != 2 or len(unit_lines) != 2:
        raise TMNoteWordBoxError("TM page-51 snapshot header must expose two dates and two units")
    ordered_units = tuple(sorted(unit_lines, key=lambda line: line.x_right))
    if (
        ordered_units[1].x_right - ordered_units[0].x_right
        < line_height * policy.minimum_axis_separation_line_heights
    ):
        raise TMNoteWordBoxError("TM page-51 snapshot axes are not distinctly separated")
    result = []
    unused_dates = set(date_lines)
    for ordinal, (unit_line, expected) in enumerate(
        zip(ordered_units, policy.expected_axes, strict=True), start=1
    ):
        date_line = min(unused_dates, key=lambda line: abs(line.x_center - unit_line.x_center))
        if (
            abs(unit_line.x_center - date_line.x_center)
            > line_height * policy.maximum_date_to_unit_center_distance_line_heights
        ):
            raise TMNoteWordBoxError("TM page-51 date/unit geometry is not locally bounded")
        unused_dates.remove(date_line)
        visible_date = parse_vietnamese_date(date_line.text)
        if visible_date != expected.snapshot_date:
            raise TMNoteWordBoxError("TM page-51 visible snapshot date drifted from policy")
        result.append(
            TMPage47AxisBinding(
                ordinal=ordinal,
                axis_id=f"snapshot-{expected.role.lower()}",
                axis_right_edge=unit_line.x_right,
                raw_header_text=normalize_text(f"{date_line.text} | {unit_line.text}"),
                header_line_indices=(date_line.index, unit_line.index),
                current_or_comparative=expected.role,
                canonical_unit=policy.canonical_unit,
                unit_multiplier=policy.unit_multiplier,
                period_start=visible_date,
                period_end=visible_date,
                period_type="SNAPSHOT",
                header_bbox=_union((date_line, unit_line)),
                unit_bbox=unit_line.bbox,
                evidence=(
                    "snapshot date parsed from the visible table-local header",
                    "current/comparative role bound by visible horizontal order",
                    "VND million multiplier matched from the visible table-local unit",
                ),
            )
        )
    if unused_dates:
        raise TMNoteWordBoxError("TM page-51 snapshot date pairing is not bijective")
    return tuple(result)


def _narrative_records(
    lines: tuple[_Line, ...],
    policy: TMPage51Policy,
    *,
    footer_top: float,
) -> tuple[TMPage51NarrativeRecord, ...]:
    starts = tuple(
        _find_anchor_line(lines, spec.start_anchors, policy, maximum_y=footer_top)
        for spec in policy.narratives
    )
    if tuple(line.y_center for line in starts) != tuple(sorted(line.y_center for line in starts)):
        raise TMNoteWordBoxError("TM page-51 narrative order drifted")
    records = []
    for ordinal, (spec, start) in enumerate(zip(policy.narratives, starts, strict=True), start=1):
        upper = starts[ordinal].y_center if ordinal < len(starts) else footer_top
        group = tuple(
            sorted(
                (
                    line
                    for line in lines
                    if start.y_center <= line.y_center < upper
                    and not _numeric_only(line.text)
                    and retrieval_key(line.text)
                ),
                key=lambda line: (line.y_center, line.bbox.x0, line.index),
            )
        )
        if len(group) != spec.expected_line_count or group[0].index != start.index:
            raise TMNoteWordBoxError(
                f"TM page-51 narrative denominator drifted: {spec.semantic_role}"
            )
        raw_text = normalize_text(" ".join(line.text for line in group))
        quantities = tuple(
            Decimal(token.replace(",", ".")) for token in _PERCENTAGE.findall(raw_text)
        )
        records.append(
            TMPage51NarrativeRecord(
                narrative_id=f"page-0051:narrative-{ordinal:04d}",
                semantic_role=spec.semantic_role,
                raw_text=raw_text,
                source_line_indices=tuple(line.index for line in group),
                source_bbox=_union(group),
                quantities=quantities,
                quantity_units=tuple("PERCENT" for _quantity in quantities),
                mapping_approved=False,
            )
        )
    return tuple(records)


def parse_tm_page51(
    result_path: Path,
    source_image_path: Path,
    policy: TMPage51Policy,
    *,
    page_tag: str = "page-0051",
) -> ParsedTMPage51:
    """Reconstruct page 51 without granting schema-mapping authority."""

    if page_tag != policy.page_tag:
        raise TMNoteWordBoxError("TM page-51 page tag drifted")
    if sha256_file(result_path) != policy.source_ocr_sha256:
        raise TMNoteWordBoxError("TM page-51 compact OCR fixture hash drifted")
    if sha256_file(source_image_path) != policy.source_render_sha256:
        raise TMNoteWordBoxError("TM page-51 source render hash drifted")
    source_image = cv2.imread(str(source_image_path), cv2.IMREAD_GRAYSCALE)
    if source_image is None:
        raise TMNoteWordBoxError("TM page-51 source render cannot be decoded")
    input_path, lines, metadata = _load_lines(result_path, policy.minimum_line_score)
    if metadata != {
        "upstream_ocr_sha256": policy.upstream_ocr_sha256,
        "source_render_sha256": policy.source_render_sha256,
        "source_pdf_sha256": policy.source_pdf_sha256,
    }:
        raise TMNoteWordBoxError("TM page-51 compact OCR provenance drifted")
    line_height = float(statistics.median(line.height for line in lines))
    if line_height <= 0:
        raise TMNoteWordBoxError("TM page-51 line height is invalid")
    source_bbox = _union(lines)
    footer_top = source_bbox.y1 * policy.page_footer_top_ratio
    title = _find_anchor_line(lines, policy.table.title_anchors, policy)
    body_end_line = _find_anchor_line(
        lines,
        policy.table.body_end_anchors,
        policy,
        minimum_y=title.y_center,
    )
    first_body = _find_anchor_line(
        lines,
        policy.table.first_body_anchors,
        policy,
        minimum_y=title.y_center,
        maximum_y=body_end_line.y_center,
    )
    section_title = _find_anchor_line(
        lines,
        policy.table.section_title_anchors,
        policy,
        maximum_y=title.y_center,
    )
    axes = _snapshot_axes(lines, title, first_body, policy, line_height)
    table, unassigned, artifacts = _reconstruct_table(
        lines,
        policy.table,
        title,
        axes,
        (),
        (),
        body_end_line.bbox.y0,
        policy,
        line_height,
        source_image,
        source_image_path,
        page_tag=page_tag,
        table_ordinal=1,
        section_title=section_title,
    )
    narratives = _narrative_records(lines, policy, footer_top=footer_top)
    footer = tuple(
        sorted(
            line.index for line in lines if line.y_center >= footer_top and _numeric_only(line.text)
        )
    )
    result = ParsedTMPage51(
        input_path=input_path,
        source_sha256=policy.source_ocr_sha256,
        upstream_ocr_sha256=policy.upstream_ocr_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_pdf_sha256=policy.source_pdf_sha256,
        page_tag=page_tag,
        scope=policy.scope,
        scope_binding=policy.scope_binding,
        axes=axes,
        tables=(table,),
        rows=table.rows,
        narratives=narratives,
        line_height=line_height,
        source_ocr_bbox=source_bbox,
        table_bbox=table.bbox,
        narrative_bbox=BoundingBox(
            min(record.source_bbox.x0 for record in narratives),
            min(record.source_bbox.y0 for record in narratives),
            max(record.source_bbox.x1 for record in narratives),
            max(record.source_bbox.y1 for record in narratives),
        ),
        unassigned_numeric_line_indices=unassigned,
        excluded_artifact_line_indices=artifacts,
        excluded_footer_numeric_line_indices=footer,
        mapping_authority=False,
        evidence=(
            "one complete source table bounded on immutable PDF page 51",
            "two snapshot axes bound from visible dates and local VND-million units",
            "nine financial rows remain distinct from seven qualitative narrative records",
            "compact golden retains exact raw PP-OCRv6 and source hash provenance",
            "schema identifiers are absent from parser inputs and mapping authority remains false",
        ),
    )
    if (
        len(result.rows) != 11
        or result.numeric_row_count != 9
        or result.label_only_row_count != 2
        or result.financial_slot_count != 18
        or result.observation_count(ObservationKind.VALUE) != 18
        or result.observation_count(ObservationKind.DASH) != 0
        or result.observation_count(ObservationKind.BLANK) != 0
        or len(result.narratives) != 7
        or result.narrative_quantity_count != 2
        or result.unassigned_numeric_line_indices
        or result.excluded_artifact_line_indices
        or result.excluded_footer_numeric_line_indices != (60,)
    ):
        raise TMNoteWordBoxError(
            "TM page-51 exact source denominator drifted: "
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
    "ParsedTMPage51",
    "TMPage51NarrativeRecord",
    "TMPage51Policy",
    "load_tm_page51_policy",
    "parse_tm_page51",
]
