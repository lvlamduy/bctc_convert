from __future__ import annotations

import itertools
import json
import re
import statistics
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from rapidfuzz.fuzz import ratio

from bctc_ai.axes.header_binding import HeaderBinding
from bctc_ai.core.contracts import BoundingBox, ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import (
    ParsedNumber,
    normalize_text,
    parse_financial_number,
    parse_vietnamese_date,
    retrieval_key,
)
from bctc_ai.validation.reader_agreement import ReaderRow


class TMNoteWordBoxError(RuntimeError):
    pass


class TMNoteRowKind(StrEnum):
    NUMERIC = "NUMERIC"
    LABEL_ONLY = "LABEL_ONLY"


class TMSchemaDisposition(StrEnum):
    UNMAPPED = "UNMAPPED"
    ROOT_CANDIDATE = "ROOT_CANDIDATE"
    SOURCE_ONLY_CANDIDATE = "SOURCE_ONLY_CANDIDATE"
    AMBIGUOUS_MAPPING_CANDIDATE = "AMBIGUOUS_MAPPING_CANDIDATE"


@dataclass(frozen=True)
class TMUnitAnchor:
    text: str
    canonical: str
    multiplier: int

    @property
    def key(self) -> str:
        return retrieval_key(self.text)


@dataclass(frozen=True)
class TMNoteSpec:
    note_number: str
    title_anchors: tuple[str, ...]
    root_candidate_report_norm_ids: tuple[int, ...]


@dataclass(frozen=True)
class TMAmbiguousLabelSpec:
    label_anchors: tuple[str, ...]
    candidate_report_norm_ids: tuple[int, ...]


@dataclass(frozen=True)
class TMNoteWordBoxPolicy:
    source_path: Path
    minimum_line_score: float
    minimum_section_title_similarity: float
    minimum_note_title_similarity: float
    minimum_header_similarity: float
    minimum_label_classification_similarity: float
    section_title_anchors: tuple[str, ...]
    scope_anchors: dict[str, tuple[str, ...]]
    unit_anchors: tuple[TMUnitAnchor, ...]
    notes: tuple[TMNoteSpec, ...]
    structural_label_anchors: tuple[str, ...]
    source_only_label_anchors: tuple[str, ...]
    ambiguous_labels: tuple[TMAmbiguousLabelSpec, ...]
    note_anchor_max_x_ratio: float
    note_title_vertical_tolerance_line_heights: float
    maximum_date_to_unit_center_distance_line_heights: float
    minimum_axis_separation_line_heights: float
    numeric_axis_max_distance_ratio: float
    numeric_axis_right_overrun_line_heights: float
    row_anchor_cluster_line_heights: float
    label_direct_attach_line_heights: float
    label_boundary_axis_gap_ratio: float
    page_footer_top_ratio: float
    forbidden_semantic_inputs: tuple[str, ...]


@dataclass(frozen=True)
class _Line:
    index: int
    text: str
    score: float
    bbox: BoundingBox

    @property
    def x_center(self) -> float:
        return (self.bbox.x0 + self.bbox.x1) / 2

    @property
    def x_right(self) -> float:
        return self.bbox.x1

    @property
    def y_center(self) -> float:
        return (self.bbox.y0 + self.bbox.y1) / 2

    @property
    def height(self) -> float:
        return self.bbox.y1 - self.bbox.y0


@dataclass(frozen=True)
class TMNoteAxisBinding:
    ordinal: int
    axis_id: str
    axis_right_edge: float
    raw_date_text: str
    date_line_index: int
    raw_unit_text: str
    unit_line_index: int
    current_or_comparative: str
    canonical_unit: str
    unit_multiplier: int
    period_start: date
    period_end: date
    period_type: str
    header_bbox: BoundingBox
    unit_bbox: BoundingBox
    evidence: tuple[str, ...]

    @property
    def header_binding(self) -> HeaderBinding:
        return HeaderBinding(
            axis_id=self.axis_id,
            raw_header=normalize_text(f"{self.raw_date_text} | {self.raw_unit_text}"),
            header_bbox=self.header_bbox,
            unit=self.canonical_unit,
            unit_multiplier=self.unit_multiplier,
            unit_bbox=self.unit_bbox,
            period_start=self.period_start,
            period_end=self.period_end,
            period_type=self.period_type,
            duration_months=None,
            current_or_comparative=self.current_or_comparative,
            restated=False,
            confidence=1.0,
            evidence=self.evidence,
        )


@dataclass(frozen=True)
class TMNoteLogicalRow:
    row_id: str
    ordinal: int
    note_number: str
    row: ReaderRow
    row_kind: TMNoteRowKind
    source_role: str
    y_anchor: float
    label_bbox: BoundingBox
    value_bboxes: tuple[BoundingBox | None, ...]
    label_line_indices: tuple[int, ...]
    value_line_indices: tuple[tuple[int, ...], ...]
    schema_disposition: TMSchemaDisposition
    candidate_report_norm_ids: tuple[int, ...]
    mapping_approved: bool
    warnings: tuple[str, ...]

    @property
    def numeric_cell_count(self) -> int:
        return sum(
            cell.observation in {ObservationKind.VALUE, ObservationKind.ZERO, ObservationKind.DASH}
            for cell in self.row.cells
        )


@dataclass(frozen=True)
class TMNoteTable:
    ordinal: int
    note_number: str
    title: str
    note_anchor_line_index: int
    title_line_indices: tuple[int, ...]
    root_candidate_report_norm_ids: tuple[int, ...]
    axes: tuple[TMNoteAxisBinding, ...]
    rows: tuple[TMNoteLogicalRow, ...]
    bbox: BoundingBox

    @property
    def root_row(self) -> TMNoteLogicalRow:
        roots = tuple(row for row in self.rows if row.source_role == "TABLE_TOTAL")
        if len(roots) != 1:
            raise TMNoteWordBoxError(f"note {self.note_number} has no unique total row")
        return roots[0]


@dataclass(frozen=True)
class ParsedTMNoteWordBoxPage:
    input_path: str
    source_sha256: str
    upstream_ocr_sha256: str | None
    source_render_sha256: str | None
    source_pdf_sha256: str | None
    page_tag: str
    section_title: str
    section_title_line_indices: tuple[int, ...]
    scope: str
    axes: tuple[TMNoteAxisBinding, ...]
    tables: tuple[TMNoteTable, ...]
    rows: tuple[TMNoteLogicalRow, ...]
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
    def numeric_cell_count(self) -> int:
        return sum(row.numeric_cell_count for row in self.rows)

    @property
    def source_only_row_count(self) -> int:
        return sum(
            row.schema_disposition is TMSchemaDisposition.SOURCE_ONLY_CANDIDATE for row in self.rows
        )

    @property
    def ambiguous_row_count(self) -> int:
        return sum(
            row.schema_disposition is TMSchemaDisposition.AMBIGUOUS_MAPPING_CANDIDATE
            for row in self.rows
        )


@dataclass(frozen=True)
class TMPage31TableSpec:
    table_key: str
    note_number: str
    title_anchors: tuple[str, ...]
    structural_label_anchors: tuple[str, ...]
    expected_numeric_rows: int
    expected_label_only_rows: int


@dataclass(frozen=True)
class TMPage31Policy:
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
    page_footer_top_ratio: float
    tables: tuple[TMPage31TableSpec, ...]
    forbidden_semantic_inputs: tuple[str, ...]


@dataclass(frozen=True)
class TMPage31LogicalRow:
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
    mapping_approved: bool

    @property
    def numeric_cell_count(self) -> int:
        return sum(
            cell.observation in {ObservationKind.VALUE, ObservationKind.ZERO, ObservationKind.DASH}
            for cell in self.row.cells
        )


@dataclass(frozen=True)
class TMPage31Table:
    ordinal: int
    table_key: str
    note_number: str
    title: str
    title_line_indices: tuple[int, ...]
    axes: tuple[TMNoteAxisBinding, ...]
    rows: tuple[TMPage31LogicalRow, ...]
    bbox: BoundingBox


@dataclass(frozen=True)
class ParsedTMPage31:
    input_path: str
    source_sha256: str
    source_render_sha256: str
    source_pdf_sha256: str
    page_tag: str
    scope: str
    scope_binding: str
    axes: tuple[TMNoteAxisBinding, ...]
    tables: tuple[TMPage31Table, ...]
    rows: tuple[TMPage31LogicalRow, ...]
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
    def numeric_cell_count(self) -> int:
        return sum(row.numeric_cell_count for row in self.rows)


_DATE = re.compile(r"^(?P<day>\d{2})/(?P<month>\d{2})/(?P<year>20\d{2})$")
_NOTE_NUMBER = re.compile(r"^(?P<number>\d+)[.]$")
_NUMERIC = re.compile(r"^[\d\s.,()\-–—+]+$")
_REQUIRED_FORBIDDEN = {
    "numeric_value_as_period_or_scope_feature",
    "horizontal_position_as_current_or_comparative_role",
    "template_labels_as_row_reconstruction_input",
    "approved_report_norm_id_assignment",
    "historical_or_mongodb_values",
    "human_review_answers",
    "accounting_equations_as_value_imputation",
}
_PAGE31_REQUIRED_FORBIDDEN = {
    "template_labels_as_row_reconstruction_input",
    "approved_report_norm_id_assignment",
    "historical_or_mongodb_values",
    "human_review_answers",
    "accounting_equations_as_value_imputation",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _positive_float(payload: dict[str, Any], name: str) -> float:
    value = payload.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise TMNoteWordBoxError(f"invalid positive TM setting: {name}")
    return float(value)


def _anchors(payload: Any, field: str) -> tuple[str, ...]:
    if not isinstance(payload, list) or not payload:
        raise TMNoteWordBoxError(f"TM {field} anchors are empty")
    result = tuple(retrieval_key(str(item)) for item in payload)
    if any(not item for item in result):
        raise TMNoteWordBoxError(f"TM {field} contains an empty anchor")
    return result


def load_tm_note_word_box_policy(path: Path) -> TMNoteWordBoxPolicy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMNoteWordBoxError(f"cannot load TM note word-box policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "REPEATED_TM_NOTE_WORD_BOX_V1"
        or payload.get("geometry_authority") != "PP_OCRV6_WORD_BOXES"
        or payload.get("statement_type") != "TM"
        or payload.get("mapping_authority") is not False
    ):
        raise TMNoteWordBoxError("TM note word-box policy identity drifted")
    semantic = payload.get("semantic_matching")
    header = payload.get("header_geometry")
    table = payload.get("table_geometry")
    if not all(isinstance(item, dict) for item in (semantic, header, table)):
        raise TMNoteWordBoxError("TM note word-box policy is incomplete")

    minimum_line_score = payload.get("minimum_line_score")
    if (
        isinstance(minimum_line_score, bool)
        or not isinstance(minimum_line_score, (int, float))
        or not 0 <= float(minimum_line_score) <= 1
    ):
        raise TMNoteWordBoxError("TM minimum_line_score must be between zero and one")

    raw_scopes = semantic.get("scope_anchors")
    if not isinstance(raw_scopes, dict) or set(raw_scopes) != {"CONSOLIDATED", "SEPARATE"}:
        raise TMNoteWordBoxError("TM scope semantics drifted")
    scope_anchors = {str(key): _anchors(value, f"scope {key}") for key, value in raw_scopes.items()}

    raw_units = semantic.get("unit_anchors")
    if not isinstance(raw_units, list) or not raw_units:
        raise TMNoteWordBoxError("TM unit anchors are empty")
    units = []
    for item in raw_units:
        if not isinstance(item, dict):
            raise TMNoteWordBoxError("TM unit anchor is invalid")
        text = item.get("text")
        canonical = item.get("canonical")
        multiplier = item.get("multiplier")
        if (
            not isinstance(text, str)
            or not isinstance(canonical, str)
            or isinstance(multiplier, bool)
            or not isinstance(multiplier, int)
            or multiplier <= 0
        ):
            raise TMNoteWordBoxError("TM unit anchor is incomplete")
        units.append(TMUnitAnchor(text, canonical, multiplier))

    raw_notes = semantic.get("notes")
    if not isinstance(raw_notes, list) or not raw_notes:
        raise TMNoteWordBoxError("TM note specifications are empty")
    notes = []
    for item in raw_notes:
        if not isinstance(item, dict):
            raise TMNoteWordBoxError("TM note specification is invalid")
        note_number = str(item.get("note_number", ""))
        candidates = item.get("root_candidate_report_norm_ids")
        if (
            not note_number.isdigit()
            or not isinstance(candidates, list)
            or not candidates
            or any(isinstance(value, bool) or not isinstance(value, int) for value in candidates)
        ):
            raise TMNoteWordBoxError("TM note candidate identity is invalid")
        notes.append(
            TMNoteSpec(
                note_number,
                _anchors(item.get("title_anchors"), f"note {note_number} title"),
                tuple(candidates),
            )
        )
    if len({note.note_number for note in notes}) != len(notes):
        raise TMNoteWordBoxError("TM note numbers are duplicated")

    ambiguous = []
    raw_ambiguous = semantic.get("ambiguous_labels")
    if not isinstance(raw_ambiguous, list):
        raise TMNoteWordBoxError("TM ambiguous-label specifications are invalid")
    for item in raw_ambiguous:
        if not isinstance(item, dict):
            raise TMNoteWordBoxError("TM ambiguous-label specification is invalid")
        candidates = item.get("candidate_report_norm_ids")
        if (
            not isinstance(candidates, list)
            or len(candidates) < 2
            or any(isinstance(value, bool) or not isinstance(value, int) for value in candidates)
        ):
            raise TMNoteWordBoxError("TM ambiguous candidates are invalid")
        ambiguous.append(
            TMAmbiguousLabelSpec(
                _anchors(item.get("label_anchors"), "ambiguous label"), tuple(candidates)
            )
        )

    forbidden = payload.get("forbidden_semantic_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMNoteWordBoxError("TM forbidden semantic inputs drifted")
    footer_ratio = _positive_float(table, "page_footer_top_ratio")
    if footer_ratio >= 1:
        raise TMNoteWordBoxError("TM footer ratio must be below one")
    return TMNoteWordBoxPolicy(
        source_path=path,
        minimum_line_score=float(minimum_line_score),
        minimum_section_title_similarity=_positive_float(
            semantic, "minimum_section_title_similarity"
        ),
        minimum_note_title_similarity=_positive_float(semantic, "minimum_note_title_similarity"),
        minimum_header_similarity=_positive_float(semantic, "minimum_header_similarity"),
        minimum_label_classification_similarity=_positive_float(
            semantic, "minimum_label_classification_similarity"
        ),
        section_title_anchors=_anchors(semantic.get("section_title_anchors"), "section title"),
        scope_anchors=scope_anchors,
        unit_anchors=tuple(units),
        notes=tuple(notes),
        structural_label_anchors=_anchors(
            semantic.get("structural_label_anchors"), "structural label"
        ),
        source_only_label_anchors=_anchors(
            semantic.get("source_only_label_anchors"), "source-only label"
        ),
        ambiguous_labels=tuple(ambiguous),
        note_anchor_max_x_ratio=_positive_float(table, "note_anchor_max_x_ratio"),
        note_title_vertical_tolerance_line_heights=_positive_float(
            table, "note_title_vertical_tolerance_line_heights"
        ),
        maximum_date_to_unit_center_distance_line_heights=_positive_float(
            header, "maximum_date_to_unit_center_distance_line_heights"
        ),
        minimum_axis_separation_line_heights=_positive_float(
            header, "minimum_axis_separation_line_heights"
        ),
        numeric_axis_max_distance_ratio=_positive_float(table, "numeric_axis_max_distance_ratio"),
        numeric_axis_right_overrun_line_heights=_positive_float(
            table, "numeric_axis_right_overrun_line_heights"
        ),
        row_anchor_cluster_line_heights=_positive_float(table, "row_anchor_cluster_line_heights"),
        label_direct_attach_line_heights=_positive_float(table, "label_direct_attach_line_heights"),
        label_boundary_axis_gap_ratio=_positive_float(table, "label_boundary_axis_gap_ratio"),
        page_footer_top_ratio=footer_ratio,
        forbidden_semantic_inputs=tuple(str(item) for item in forbidden),
    )


def load_tm_page31_policy(path: Path) -> TMPage31Policy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMNoteWordBoxError(f"cannot load TM page-31 policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE31_FIXED_GRID_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 31
        or payload.get("page_tag") != "page-0031"
        or payload.get("scope") != "CONSOLIDATED"
        or payload.get("scope_binding") != "PREDECESSOR_TM_SECTION_ON_PAGE_30"
    ):
        raise TMNoteWordBoxError("TM page-31 policy identity drifted")
    hashes = (
        payload.get("source_pdf_sha256"),
        payload.get("source_render_sha256"),
        payload.get("source_ocr_sha256"),
    )
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMNoteWordBoxError("TM page-31 source hashes are invalid")
    minimum_line_score = payload.get("minimum_line_score")
    minimum_anchor_similarity = payload.get("minimum_anchor_similarity")
    minimum_unit_similarity = payload.get("minimum_unit_similarity")
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= float(value) <= 1
        for value in (minimum_line_score, minimum_anchor_similarity, minimum_unit_similarity)
    ):
        raise TMNoteWordBoxError("TM page-31 similarity thresholds are invalid")
    unit = payload.get("unit")
    header = payload.get("header_geometry")
    table_geometry = payload.get("table_geometry")
    if not all(isinstance(value, dict) for value in (unit, header, table_geometry)):
        raise TMNoteWordBoxError("TM page-31 geometry configuration is incomplete")
    canonical_unit = unit.get("canonical")
    unit_multiplier = unit.get("multiplier")
    if (
        not isinstance(canonical_unit, str)
        or not canonical_unit
        or isinstance(unit_multiplier, bool)
        or not isinstance(unit_multiplier, int)
        or unit_multiplier <= 0
    ):
        raise TMNoteWordBoxError("TM page-31 unit binding is invalid")
    raw_tables = payload.get("tables")
    if not isinstance(raw_tables, list) or len(raw_tables) != 4:
        raise TMNoteWordBoxError("TM page-31 must define four visible tables")
    tables = []
    for record in raw_tables:
        if not isinstance(record, dict):
            raise TMNoteWordBoxError("TM page-31 table record is invalid")
        table_key = record.get("table_key")
        note_number = record.get("note_number")
        numeric_rows = record.get("expected_numeric_rows")
        label_rows = record.get("expected_label_only_rows")
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
            raise TMNoteWordBoxError("TM page-31 table identity or denominator is invalid")
        tables.append(
            TMPage31TableSpec(
                table_key=table_key,
                note_number=note_number,
                title_anchors=_anchors(record.get("title_anchors"), f"{table_key} title"),
                structural_label_anchors=_anchors(
                    record.get("structural_label_anchors"), f"{table_key} structural label"
                ),
                expected_numeric_rows=numeric_rows,
                expected_label_only_rows=label_rows,
            )
        )
    if len({table.table_key for table in tables}) != len(tables):
        raise TMNoteWordBoxError("TM page-31 table keys are duplicated")
    forbidden = payload.get("forbidden_semantic_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _PAGE31_REQUIRED_FORBIDDEN:
        raise TMNoteWordBoxError("TM page-31 forbidden semantic inputs drifted")
    footer_ratio = _positive_float(table_geometry, "page_footer_top_ratio")
    if footer_ratio >= 1:
        raise TMNoteWordBoxError("TM page-31 footer ratio must be below one")
    return TMPage31Policy(
        source_path=path,
        document=str(payload.get("document", "")),
        page_number=31,
        page_tag="page-0031",
        scope="CONSOLIDATED",
        scope_binding="PREDECESSOR_TM_SECTION_ON_PAGE_30",
        source_pdf_sha256=hashes[0],
        source_render_sha256=hashes[1],
        source_ocr_sha256=hashes[2],
        minimum_line_score=float(minimum_line_score),
        minimum_anchor_similarity=float(minimum_anchor_similarity),
        minimum_unit_similarity=float(minimum_unit_similarity),
        unit_anchors=_anchors(unit.get("anchors"), "page-31 unit"),
        canonical_unit=canonical_unit,
        unit_multiplier=unit_multiplier,
        maximum_date_to_unit_center_distance_line_heights=_positive_float(
            header, "maximum_date_to_unit_center_distance_line_heights"
        ),
        minimum_axis_separation_line_heights=_positive_float(
            header, "minimum_axis_separation_line_heights"
        ),
        numeric_axis_max_distance_ratio=_positive_float(
            table_geometry, "numeric_axis_max_distance_ratio"
        ),
        numeric_axis_right_overrun_line_heights=_positive_float(
            table_geometry, "numeric_axis_right_overrun_line_heights"
        ),
        row_anchor_cluster_line_heights=_positive_float(
            table_geometry, "row_anchor_cluster_line_heights"
        ),
        label_direct_attach_line_heights=_positive_float(
            table_geometry, "label_direct_attach_line_heights"
        ),
        page_footer_top_ratio=footer_ratio,
        tables=tuple(tables),
        forbidden_semantic_inputs=tuple(str(item) for item in forbidden),
    )


def _load_lines(
    path: Path, minimum_score: float
) -> tuple[str, tuple[_Line, ...], dict[str, str | None]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TMNoteWordBoxError(f"cannot read PP-OCRv6 result: {path}") from exc
    texts = payload.get("rec_texts")
    scores = payload.get("rec_scores")
    boxes = payload.get("rec_boxes")
    if (
        not all(isinstance(axis, list) for axis in (texts, scores, boxes))
        or len({len(texts), len(scores), len(boxes)}) != 1
    ):
        raise TMNoteWordBoxError("PP-OCRv6 result axes are incomplete")
    lines = []
    for index, (text, score, box) in enumerate(zip(texts, scores, boxes, strict=True)):
        if not isinstance(box, list) or len(box) != 4:
            raise TMNoteWordBoxError(f"line {index} has no four-coordinate box")
        bbox = BoundingBox(*(float(value) for value in box))
        if bbox.x1 <= bbox.x0 or bbox.y1 <= bbox.y0:
            raise TMNoteWordBoxError(f"line {index} has a degenerate box")
        if float(score) >= minimum_score:
            lines.append(_Line(index, normalize_text(str(text)), float(score), bbox))
    if not lines:
        raise TMNoteWordBoxError("PP-OCRv6 result contains no accepted lines")
    metadata = {
        "upstream_ocr_sha256": (
            str(payload["source_ocr_sha256"])
            if isinstance(payload.get("source_ocr_sha256"), str)
            else None
        ),
        "source_render_sha256": (
            str(payload["source_render_sha256"])
            if isinstance(payload.get("source_render_sha256"), str)
            else None
        ),
        "source_pdf_sha256": (
            str(payload["source_pdf_sha256"])
            if isinstance(payload.get("source_pdf_sha256"), str)
            else None
        ),
    }
    return str(payload.get("input_path", "")), tuple(lines), metadata


def _similarity(text: str, anchor: str) -> float:
    key = retrieval_key(text)
    if anchor in key:
        return 1.0
    return ratio(key, anchor) / 100


def _best_anchor_similarity(text: str, anchors: tuple[str, ...]) -> float:
    return max((_similarity(text, anchor) for anchor in anchors), default=0.0)


def _union(lines: list[_Line] | tuple[_Line, ...]) -> BoundingBox:
    if not lines:
        raise TMNoteWordBoxError("cannot union an empty TM evidence set")
    return BoundingBox(
        min(line.bbox.x0 for line in lines),
        min(line.bbox.y0 for line in lines),
        max(line.bbox.x1 for line in lines),
        max(line.bbox.y1 for line in lines),
    )


def _minimum_bijection(
    left: tuple[_Line, ...], right: tuple[_Line, ...]
) -> tuple[tuple[_Line, _Line], ...]:
    if len(left) != len(right):
        raise TMNoteWordBoxError("TM header axes cannot be paired bijectively")
    best: tuple[float, tuple[int, ...]] | None = None
    for permutation in itertools.permutations(range(len(right))):
        candidate = (
            sum(
                abs(left[index].x_center - right[target].x_center)
                for index, target in enumerate(permutation)
            ),
            permutation,
        )
        if best is None or candidate < best:
            best = candidate
    assert best is not None
    return tuple((line, right[index]) for line, index in zip(left, best[1], strict=True))


def _numeric_only(text: str) -> bool:
    normalized = normalize_text(text)
    return bool(
        normalized
        and not any(character.isalpha() for character in normalized)
        and _NUMERIC.fullmatch(normalized)
    )


def _clusters(lines: list[_Line], tolerance: float) -> list[list[_Line]]:
    groups: list[list[_Line]] = []
    for line in sorted(lines, key=lambda item: (item.y_center, item.bbox.x0)):
        if (
            groups
            and abs(line.y_center - statistics.fmean(item.y_center for item in groups[-1]))
            <= tolerance
        ):
            groups[-1].append(line)
        else:
            groups.append([line])
    return groups


def _source_ids(page_tag: str, lines: list[_Line]) -> tuple[str, ...]:
    return tuple(
        f"{page_tag}:line-{line.index:04d}" for line in sorted(lines, key=lambda item: item.index)
    )


def _find_section_and_scope(
    lines: tuple[_Line, ...],
    first_note: _Line,
    policy: TMNoteWordBoxPolicy,
) -> tuple[str, tuple[_Line, ...]]:
    candidates = tuple(line for line in lines if line.y_center < first_note.y_center)
    if not candidates:
        raise TMNoteWordBoxError("visible TM section title is absent")
    joined = normalize_text(" ".join(line.text for line in candidates))
    if (
        _best_anchor_similarity(joined, policy.section_title_anchors)
        < policy.minimum_section_title_similarity
    ):
        raise TMNoteWordBoxError("visible TM quantitative-note section title is unresolved")
    scope_scores = {
        semantic: _best_anchor_similarity(joined, anchors)
        for semantic, anchors in policy.scope_anchors.items()
    }
    ordered = sorted(scope_scores.items(), key=lambda item: (-item[1], item[0]))
    if ordered[0][1] < policy.minimum_header_similarity or ordered[0][1] - ordered[1][1] < 0.05:
        raise TMNoteWordBoxError("visible TM consolidated/separate scope is unresolved")
    return ordered[0][0], candidates


def _find_note_anchors(
    lines: tuple[_Line, ...], policy: TMNoteWordBoxPolicy, page_width: float
) -> tuple[tuple[TMNoteSpec, _Line, _Line], ...]:
    numbered = {}
    for line in lines:
        match = _NOTE_NUMBER.fullmatch(line.text)
        if match and line.x_center <= page_width * policy.note_anchor_max_x_ratio:
            number = match.group("number")
            if number in numbered:
                raise TMNoteWordBoxError(f"visible TM note number is duplicated: {number}")
            numbered[number] = line
    if set(numbered) != {spec.note_number for spec in policy.notes}:
        raise TMNoteWordBoxError("visible TM note-number set drifted")
    result = []
    for spec in policy.notes:
        anchor = numbered[spec.note_number]
        nearby = [
            line
            for line in lines
            if line.index != anchor.index
            and line.bbox.x0 > anchor.bbox.x1
            and abs(line.y_center - anchor.y_center)
            <= statistics.median(item.height for item in lines)
            * policy.note_title_vertical_tolerance_line_heights
        ]
        if not nearby:
            raise TMNoteWordBoxError(f"visible TM note {spec.note_number} title is absent")
        title = max(
            nearby,
            key=lambda line: (
                _best_anchor_similarity(line.text, spec.title_anchors),
                -abs(line.y_center - anchor.y_center),
                -line.index,
            ),
        )
        if (
            _best_anchor_similarity(title.text, spec.title_anchors)
            < policy.minimum_note_title_similarity
        ):
            raise TMNoteWordBoxError(f"visible TM note {spec.note_number} title is unresolved")
        result.append((spec, anchor, title))
    result.sort(key=lambda item: item[1].y_center)
    return tuple(result)


def _unit_match(line: _Line, policy: TMNoteWordBoxPolicy) -> tuple[TMUnitAnchor, float] | None:
    if any(character.isdigit() for character in retrieval_key(line.text)):
        return None
    scored = sorted(
        ((_similarity(line.text, anchor.key), anchor) for anchor in policy.unit_anchors),
        key=lambda item: (-item[0], item[1].text),
    )
    similarity, anchor = scored[0]
    return (anchor, similarity) if similarity >= policy.minimum_header_similarity else None


def _bind_table_axes(
    lines: tuple[_Line, ...],
    title: _Line,
    next_anchor: _Line | None,
    policy: TMNoteWordBoxPolicy,
    line_height: float,
) -> tuple[TMNoteAxisBinding, ...]:
    upper = next_anchor.bbox.y0 if next_anchor is not None else float("inf")
    candidates = tuple(
        line for line in lines if line.y_center > title.y_center and line.y_center < upper
    )
    dates = tuple(line for line in candidates if _DATE.fullmatch(line.text))
    units_with_anchor = tuple(
        (line, match) for line in candidates if (match := _unit_match(line, policy)) is not None
    )
    if len(dates) != 2 or len(units_with_anchor) != 2:
        raise TMNoteWordBoxError("each TM note table must expose two dates and two local units")
    units = tuple(item[0] for item in units_with_anchor)
    pairs = _minimum_bijection(tuple(sorted(dates, key=lambda item: item.x_right)), units)
    unit_by_index = {line.index: record for line, record in units_with_anchor}
    if any(
        abs(date_line.x_center - unit_line.x_center)
        > line_height * policy.maximum_date_to_unit_center_distance_line_heights
        for date_line, unit_line in pairs
    ):
        raise TMNoteWordBoxError("TM date/unit header geometry is not locally bounded")
    ordered_pairs = tuple(sorted(pairs, key=lambda item: item[1].x_right))
    gaps = [
        right[1].x_right - left[1].x_right
        for left, right in zip(ordered_pairs, ordered_pairs[1:], strict=False)
    ]
    if min(gaps, default=0) < line_height * policy.minimum_axis_separation_line_heights:
        raise TMNoteWordBoxError("TM value axes are not distinctly separated")
    parsed_dates = [parse_vietnamese_date(date_line.text) for date_line, _unit in ordered_pairs]
    if any(value is None for value in parsed_dates) or len(set(parsed_dates)) != 2:
        raise TMNoteWordBoxError("TM visible snapshot dates are invalid or duplicated")
    latest = max(value for value in parsed_dates if value is not None)
    bound = []
    for ordinal, ((date_line, unit_line), parsed_date) in enumerate(
        zip(ordered_pairs, parsed_dates, strict=True), start=1
    ):
        assert parsed_date is not None
        unit_anchor = unit_by_index[unit_line.index][0]
        role = "CURRENT" if parsed_date == latest else "COMPARATIVE"
        bound.append(
            TMNoteAxisBinding(
                ordinal=ordinal,
                axis_id=f"value-{ordinal}",
                axis_right_edge=unit_line.x_right,
                raw_date_text=date_line.text,
                date_line_index=date_line.index,
                raw_unit_text=unit_line.text,
                unit_line_index=unit_line.index,
                current_or_comparative=role,
                canonical_unit=unit_anchor.canonical,
                unit_multiplier=unit_anchor.multiplier,
                period_start=parsed_date,
                period_end=parsed_date,
                period_type="SNAPSHOT",
                header_bbox=_union([date_line, unit_line]),
                unit_bbox=unit_line.bbox,
                evidence=(
                    "snapshot date parsed from the visible axis-local date header",
                    "current/comparative role derived from visible date chronology, not x-order",
                    "unit and multiplier matched from the visible axis-local unit word box",
                ),
            )
        )
    if {axis.current_or_comparative for axis in bound} != {"CURRENT", "COMPARATIVE"}:
        raise TMNoteWordBoxError("TM table does not expose current and comparative snapshots")
    return tuple(bound)


def _label_disposition(
    label: str, policy: TMNoteWordBoxPolicy
) -> tuple[TMSchemaDisposition, tuple[int, ...]]:
    if (
        _best_anchor_similarity(label, policy.source_only_label_anchors)
        >= policy.minimum_label_classification_similarity
    ):
        return TMSchemaDisposition.SOURCE_ONLY_CANDIDATE, ()
    matches = [
        spec
        for spec in policy.ambiguous_labels
        if _best_anchor_similarity(label, spec.label_anchors)
        >= policy.minimum_label_classification_similarity
    ]
    if len(matches) > 1:
        raise TMNoteWordBoxError("TM row matches more than one ambiguity specification")
    if matches:
        return TMSchemaDisposition.AMBIGUOUS_MAPPING_CANDIDATE, matches[0].candidate_report_norm_ids
    return TMSchemaDisposition.UNMAPPED, ()


def _reconstruct_table(
    lines: tuple[_Line, ...],
    spec: TMNoteSpec,
    anchor: _Line,
    title: _Line,
    next_anchor: _Line | None,
    axes: tuple[TMNoteAxisBinding, ...],
    policy: TMNoteWordBoxPolicy,
    line_height: float,
    page_height: float,
    *,
    page_tag: str,
    table_ordinal: int,
) -> tuple[TMNoteTable, tuple[int, ...], tuple[int, ...]]:
    body_start = max(axis.unit_bbox.y1 for axis in axes)
    body_end = (
        next_anchor.bbox.y0
        if next_anchor is not None
        else page_height * policy.page_footer_top_ratio
    )
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
    if not assigned:
        raise TMNoteWordBoxError(f"TM note {spec.note_number} has no assigned numeric cells")
    groups = _clusters(assigned, line_height * policy.row_anchor_cluster_line_heights)
    centers = [statistics.fmean(line.y_center for line in group) for group in groups]
    if any(len(group) != len(axes) for group in groups):
        raise TMNoteWordBoxError(f"TM note {spec.note_number} has an incomplete numeric row")

    label_boundary = axes[0].axis_right_edge - typical_gap * policy.label_boundary_axis_gap_ratio
    used = {line.index for line in assigned + unassigned}
    label_candidates = [
        line
        for line in body
        if line.index not in used
        and line.x_right < label_boundary
        and not _numeric_only(line.text)
        and _best_anchor_similarity(line.text, policy.structural_label_anchors)
        < policy.minimum_label_classification_similarity
    ]
    assignments: dict[int, int] = {}
    direct = line_height * policy.label_direct_attach_line_heights
    for label in label_candidates:
        distances = [abs(label.y_center - center) for center in centers]
        closest = min(range(len(distances)), key=distances.__getitem__)
        if distances[closest] <= direct:
            assignments[label.index] = closest

    root_groups = [
        index
        for index in range(len(groups))
        if not any(target == index for target in assignments.values())
    ]
    if root_groups != [len(groups) - 1]:
        raise TMNoteWordBoxError(
            f"TM note {spec.note_number} does not expose one trailing unlabeled total"
        )

    proposals: list[tuple[float, TMNoteLogicalRow]] = []
    ordinal = 0
    for group_index, (group, center) in enumerate(zip(groups, centers, strict=True)):
        ordinal += 1
        labels = sorted(
            (line for line in label_candidates if assignments.get(line.index) == group_index),
            key=lambda item: (item.y_center, item.bbox.x0),
        )
        is_root = group_index == root_groups[0]
        if is_root:
            labels = [title]
        value_lines = [
            sorted((line for line in axis_lines if line in group), key=lambda item: item.bbox.x0)
            for axis_lines in per_axis
        ]
        cells: tuple[ParsedNumber, ...] = tuple(
            parse_financial_number(" ".join(line.text for line in axis_lines))
            for axis_lines in value_lines
        )
        if any(
            cell.observation not in {ObservationKind.VALUE, ObservationKind.ZERO} for cell in cells
        ):
            raise TMNoteWordBoxError(f"TM note {spec.note_number} contains an invalid numeric cell")
        label = normalize_text(" ".join(line.text for line in labels))
        if is_root:
            disposition = TMSchemaDisposition.ROOT_CANDIDATE
            candidate_ids = spec.root_candidate_report_norm_ids
            source_role = "TABLE_TOTAL"
        else:
            disposition, candidate_ids = _label_disposition(label, policy)
            source_role = "DETAIL"
        source_lines = labels + [line for axis_lines in value_lines for line in axis_lines]
        proposals.append(
            (
                center,
                TMNoteLogicalRow(
                    row_id=f"{page_tag}:note-{spec.note_number}:row-{ordinal:04d}",
                    ordinal=ordinal,
                    note_number=spec.note_number,
                    row=ReaderRow(
                        source_row_ids=_source_ids(page_tag, source_lines),
                        label=label,
                        note_reference=spec.note_number,
                        cells=cells,
                    ),
                    row_kind=TMNoteRowKind.NUMERIC,
                    source_role=source_role,
                    y_anchor=center,
                    label_bbox=_union(labels),
                    value_bboxes=tuple(_union(axis_lines) for axis_lines in value_lines),
                    label_line_indices=tuple(line.index for line in labels),
                    value_line_indices=tuple(
                        tuple(line.index for line in axis_lines) for axis_lines in value_lines
                    ),
                    schema_disposition=disposition,
                    candidate_report_norm_ids=candidate_ids,
                    mapping_approved=False,
                    warnings=(
                        ("candidate classification only; no ReportNormId mapping is approved",)
                        if candidate_ids or disposition is TMSchemaDisposition.SOURCE_ONLY_CANDIDATE
                        else ()
                    ),
                ),
            )
        )

    label_only = [line for line in label_candidates if line.index not in assignments]
    for label in label_only:
        ordinal += 1
        disposition, candidate_ids = _label_disposition(label.text, policy)
        proposals.append(
            (
                label.y_center,
                TMNoteLogicalRow(
                    row_id=f"{page_tag}:note-{spec.note_number}:row-{ordinal:04d}",
                    ordinal=ordinal,
                    note_number=spec.note_number,
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
                    schema_disposition=disposition,
                    candidate_report_norm_ids=candidate_ids,
                    mapping_approved=False,
                    warnings=("visible group label has no directly reported value",),
                ),
            )
        )
    ordered_rows = []
    for row_ordinal, (_center, row) in enumerate(
        sorted(proposals, key=lambda item: item[0]), start=1
    ):
        ordered_rows.append(
            TMNoteLogicalRow(
                row_id=f"{page_tag}:note-{spec.note_number}:row-{row_ordinal:04d}",
                ordinal=row_ordinal,
                note_number=row.note_number,
                row=row.row,
                row_kind=row.row_kind,
                source_role=row.source_role,
                y_anchor=row.y_anchor,
                label_bbox=row.label_bbox,
                value_bboxes=row.value_bboxes,
                label_line_indices=row.label_line_indices,
                value_line_indices=row.value_line_indices,
                schema_disposition=row.schema_disposition,
                candidate_report_norm_ids=row.candidate_report_norm_ids,
                mapping_approved=False,
                warnings=row.warnings,
            )
        )
    table_lines = [anchor, title]
    table_lines.extend(
        line
        for axis in axes
        for line in lines
        if line.index in {axis.date_line_index, axis.unit_line_index}
    )
    table_lines.extend(
        line
        for row in ordered_rows
        for source_id in row.row.source_row_ids
        for line in lines
        if line.index == int(source_id.rsplit("-", 1)[-1])
    )
    footer_numeric = tuple(
        line.index
        for line in lines
        if next_anchor is None and line.y_center >= body_end and _numeric_only(line.text)
    )
    return (
        TMNoteTable(
            ordinal=table_ordinal,
            note_number=spec.note_number,
            title=title.text,
            note_anchor_line_index=anchor.index,
            title_line_indices=(title.index,),
            root_candidate_report_norm_ids=spec.root_candidate_report_norm_ids,
            axes=axes,
            rows=tuple(ordered_rows),
            bbox=_union(table_lines),
        ),
        tuple(sorted(line.index for line in unassigned)),
        footer_numeric,
    )


def parse_tm_note_word_box_page(
    result_path: Path,
    policy: TMNoteWordBoxPolicy,
    *,
    page_tag: str,
) -> ParsedTMNoteWordBoxPage:
    """Parse repeated two-axis quantitative TM tables without approving mapping."""

    input_path, lines, metadata = _load_lines(result_path, policy.minimum_line_score)
    line_height = float(statistics.median(line.height for line in lines))
    if line_height <= 0:
        raise TMNoteWordBoxError("TM word-box line height is invalid")
    source_bbox = _union(lines)
    note_records = _find_note_anchors(lines, policy, source_bbox.x1)
    scope, section_lines = _find_section_and_scope(lines, note_records[0][1], policy)
    tables = []
    unassigned = []
    footer = []
    for index, (spec, anchor, title) in enumerate(note_records):
        next_anchor = note_records[index + 1][1] if index + 1 < len(note_records) else None
        axes = _bind_table_axes(lines, title, next_anchor, policy, line_height)
        table, table_unassigned, table_footer = _reconstruct_table(
            lines,
            spec,
            anchor,
            title,
            next_anchor,
            axes,
            policy,
            line_height,
            source_bbox.y1,
            page_tag=page_tag,
            table_ordinal=index + 1,
        )
        tables.append(table)
        unassigned.extend(table_unassigned)
        footer.extend(table_footer)
    canonical_axes = tables[0].axes
    semantic_axes = tuple(
        (
            axis.current_or_comparative,
            axis.period_start,
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
        raise TMNoteWordBoxError("repeated TM table headers disagree semantically")
    rows = tuple(row for table in tables for row in table.rows)
    return ParsedTMNoteWordBoxPage(
        input_path=input_path,
        source_sha256=sha256_file(result_path),
        upstream_ocr_sha256=metadata["upstream_ocr_sha256"],
        source_render_sha256=metadata["source_render_sha256"],
        source_pdf_sha256=metadata["source_pdf_sha256"],
        page_tag=page_tag,
        section_title=normalize_text(" ".join(line.text for line in section_lines)),
        section_title_line_indices=tuple(line.index for line in section_lines),
        scope=scope,
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
        excluded_footer_numeric_line_indices=tuple(sorted(set(footer))),
        mapping_authority=False,
        evidence=(
            "scope matched from the visible quantitative-note section title",
            "three note tables located from visible numbered anchors and titles",
            "two SNAPSHOT axes bound independently in every repeated local header",
            "numeric cells reconstructed from PP-OCRv6 word-box geometry",
            "schema identifiers remain candidates; this parser grants no mapping authority",
        ),
    )


def _find_page31_titles(
    lines: tuple[_Line, ...], policy: TMPage31Policy
) -> tuple[tuple[TMPage31TableSpec, _Line], ...]:
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
            raise TMNoteWordBoxError(f"TM page-31 table title is unresolved: {spec.table_key}")
        title = candidates[0][1]
        used.add(title.index)
        result.append((spec, title))
    if [title.y_center for _spec, title in result] != sorted(
        title.y_center for _spec, title in result
    ):
        raise TMNoteWordBoxError("TM page-31 table-title order drifted")
    visible_note_numbers = {
        match.group("number")
        for line in lines
        if (match := _NOTE_NUMBER.fullmatch(line.text)) is not None
    }
    if not {"4", "5"} <= visible_note_numbers:
        raise TMNoteWordBoxError("TM page-31 visible note anchors 4 and 5 are incomplete")
    return tuple(result)


def _bind_page31_axes(
    lines: tuple[_Line, ...],
    title: _Line,
    next_title: _Line | None,
    body_end: float,
    policy: TMPage31Policy,
    line_height: float,
) -> tuple[TMNoteAxisBinding, ...]:
    upper = next_title.bbox.y0 if next_title is not None else body_end
    candidates = tuple(line for line in lines if title.y_center < line.y_center < upper)
    dates = tuple(line for line in candidates if _DATE.fullmatch(line.text))
    units = tuple(
        line
        for line in candidates
        if not any(character.isdigit() for character in retrieval_key(line.text))
        and _best_anchor_similarity(line.text, policy.unit_anchors)
        >= policy.minimum_unit_similarity
    )
    if len(dates) != 2 or len(units) != 2:
        raise TMNoteWordBoxError("each TM page-31 table must expose two dates and two units")
    pairs = _minimum_bijection(tuple(sorted(dates, key=lambda item: item.x_right)), units)
    if any(
        abs(date_line.x_center - unit_line.x_center)
        > line_height * policy.maximum_date_to_unit_center_distance_line_heights
        for date_line, unit_line in pairs
    ):
        raise TMNoteWordBoxError("TM page-31 date/unit geometry is not locally bounded")
    ordered_pairs = tuple(sorted(pairs, key=lambda item: item[1].x_right))
    gaps = [
        right[1].x_right - left[1].x_right
        for left, right in zip(ordered_pairs, ordered_pairs[1:], strict=False)
    ]
    if min(gaps, default=0) < line_height * policy.minimum_axis_separation_line_heights:
        raise TMNoteWordBoxError("TM page-31 value axes are not distinctly separated")
    parsed_dates = [parse_vietnamese_date(date_line.text) for date_line, _unit in ordered_pairs]
    if any(value is None for value in parsed_dates) or len(set(parsed_dates)) != 2:
        raise TMNoteWordBoxError("TM page-31 visible snapshot dates are invalid or duplicated")
    latest = max(value for value in parsed_dates if value is not None)
    result = []
    for ordinal, ((date_line, unit_line), parsed_date) in enumerate(
        zip(ordered_pairs, parsed_dates, strict=True), start=1
    ):
        assert parsed_date is not None
        result.append(
            TMNoteAxisBinding(
                ordinal=ordinal,
                axis_id=f"value-{ordinal}",
                axis_right_edge=unit_line.x_right,
                raw_date_text=date_line.text,
                date_line_index=date_line.index,
                raw_unit_text=unit_line.text,
                unit_line_index=unit_line.index,
                current_or_comparative="CURRENT" if parsed_date == latest else "COMPARATIVE",
                canonical_unit=policy.canonical_unit,
                unit_multiplier=policy.unit_multiplier,
                period_start=parsed_date,
                period_end=parsed_date,
                period_type="SNAPSHOT",
                header_bbox=_union([date_line, unit_line]),
                unit_bbox=unit_line.bbox,
                evidence=(
                    "snapshot date parsed from the visible table-local date header",
                    "current/comparative role derived from visible date chronology",
                    "VND million multiplier matched from the visible table-local unit",
                ),
            )
        )
    return tuple(result)


def _reconstruct_page31_table(
    lines: tuple[_Line, ...],
    spec: TMPage31TableSpec,
    title: _Line,
    axes: tuple[TMNoteAxisBinding, ...],
    body_end: float,
    policy: TMPage31Policy,
    line_height: float,
    *,
    page_tag: str,
    table_ordinal: int,
) -> tuple[TMPage31Table, tuple[int, ...]]:
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
    groups = _clusters(assigned, line_height * policy.row_anchor_cluster_line_heights)
    if not groups or any(len(group) != len(axes) for group in groups):
        raise TMNoteWordBoxError(f"TM page-31 {spec.table_key} has incomplete numeric rows")
    centers = [statistics.fmean(line.y_center for line in group) for group in groups]
    used = {line.index for line in assigned + unassigned}
    label_boundary = axes[0].axis_right_edge - typical_gap * 0.35
    label_candidates = [
        line
        for line in body
        if line.index not in used and line.x_right < label_boundary and not _numeric_only(line.text)
    ]
    structural = [
        line
        for line in label_candidates
        if _best_anchor_similarity(line.text, spec.structural_label_anchors)
        >= policy.minimum_anchor_similarity
    ]
    assignments: dict[int, int] = {}
    for label in label_candidates:
        if label in structural:
            continue
        distances = [abs(label.y_center - center) for center in centers]
        closest = min(range(len(distances)), key=distances.__getitem__)
        if distances[closest] <= line_height * policy.label_direct_attach_line_heights:
            assignments[label.index] = closest

    proposals: list[tuple[float, TMPage31LogicalRow]] = []
    for group_index, (group, center) in enumerate(zip(groups, centers, strict=True)):
        labels = sorted(
            (line for line in label_candidates if assignments.get(line.index) == group_index),
            key=lambda item: (item.y_center, item.bbox.x0),
        )
        value_lines = [
            sorted((line for line in axis_lines if line in group), key=lambda item: item.bbox.x0)
            for axis_lines in per_axis
        ]
        cells = tuple(
            parse_financial_number(" ".join(line.text for line in axis_lines))
            for axis_lines in value_lines
        )
        if any(
            cell.observation not in {ObservationKind.VALUE, ObservationKind.ZERO} for cell in cells
        ):
            raise TMNoteWordBoxError(f"TM page-31 {spec.table_key} has an invalid numeric cell")
        label = normalize_text(" ".join(line.text for line in labels))
        source_lines = labels + [line for axis_lines in value_lines for line in axis_lines]
        proposals.append(
            (
                center,
                TMPage31LogicalRow(
                    row_id="",
                    table_key=spec.table_key,
                    note_number=spec.note_number,
                    ordinal=0,
                    row=ReaderRow(
                        source_row_ids=_source_ids(page_tag, source_lines),
                        label=label,
                        note_reference=spec.note_number,
                        cells=cells,
                    ),
                    row_kind=TMNoteRowKind.NUMERIC,
                    source_role="DETAIL" if labels else "UNLABELED_TOTAL",
                    y_anchor=center,
                    label_bbox=_union(labels) if labels else None,
                    value_bboxes=tuple(_union(axis_lines) for axis_lines in value_lines),
                    label_line_indices=tuple(line.index for line in labels),
                    value_line_indices=tuple(
                        tuple(line.index for line in axis_lines) for axis_lines in value_lines
                    ),
                    mapping_approved=False,
                ),
            )
        )
    for label in structural:
        proposals.append(
            (
                label.y_center,
                TMPage31LogicalRow(
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
                    mapping_approved=False,
                ),
            )
        )
    rows = []
    for ordinal, (_center, row) in enumerate(sorted(proposals, key=lambda item: item[0]), start=1):
        rows.append(
            TMPage31LogicalRow(
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
                mapping_approved=False,
            )
        )
    numeric_count = sum(row.row_kind is TMNoteRowKind.NUMERIC for row in rows)
    label_count = sum(row.row_kind is TMNoteRowKind.LABEL_ONLY for row in rows)
    if (numeric_count, label_count) != (
        spec.expected_numeric_rows,
        spec.expected_label_only_rows,
    ):
        raise TMNoteWordBoxError(
            f"TM page-31 {spec.table_key} row denominator drifted: "
            f"{numeric_count} numeric + {label_count} label-only"
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
        TMPage31Table(
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


def parse_tm_page31(
    result_path: Path,
    policy: TMPage31Policy,
    *,
    page_tag: str = "page-0031",
) -> ParsedTMPage31:
    """Reconstruct the four visible page-31 TM tables without mapping authority."""

    if page_tag != policy.page_tag:
        raise TMNoteWordBoxError("TM page-31 page tag drifted")
    source_sha256 = sha256_file(result_path)
    if source_sha256 != policy.source_ocr_sha256:
        raise TMNoteWordBoxError("TM page-31 OCR artifact hash drifted")
    input_path, lines, _metadata = _load_lines(result_path, policy.minimum_line_score)
    line_height = float(statistics.median(line.height for line in lines))
    if line_height <= 0:
        raise TMNoteWordBoxError("TM page-31 word-box line height is invalid")
    source_bbox = _union(lines)
    title_records = _find_page31_titles(lines, policy)
    footer_top = source_bbox.y1 * policy.page_footer_top_ratio
    tables = []
    unassigned = []
    for index, (spec, title) in enumerate(title_records):
        next_title = title_records[index + 1][1] if index + 1 < len(title_records) else None
        body_end = next_title.bbox.y0 if next_title is not None else footer_top
        axes = _bind_page31_axes(
            lines,
            title,
            next_title,
            body_end,
            policy,
            line_height,
        )
        table, table_unassigned = _reconstruct_page31_table(
            lines,
            spec,
            title,
            axes,
            body_end,
            policy,
            line_height,
            page_tag=page_tag,
            table_ordinal=index + 1,
        )
        tables.append(table)
        unassigned.extend(table_unassigned)
    canonical_axes = tables[0].axes
    semantic_axes = tuple(
        (
            axis.current_or_comparative,
            axis.period_start,
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
        raise TMNoteWordBoxError("TM page-31 repeated headers disagree semantically")
    rows = tuple(row for table in tables for row in table.rows)
    footer = tuple(
        sorted(
            line.index for line in lines if line.y_center >= footer_top and _numeric_only(line.text)
        )
    )
    return ParsedTMPage31(
        input_path=input_path,
        source_sha256=source_sha256,
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
            "four local tables located from visible page-31 titles in source order",
            "two SNAPSHOT axes bound independently from every local date/unit header",
            "scope inherited from the immediately preceding TM quantitative section page",
            "33 logical rows and 56 numeric cells reconstructed from PP-OCRv6 geometry",
            "this parser grants no ReportNormId authority",
        ),
    )


__all__ = [
    "ParsedTMNoteWordBoxPage",
    "ParsedTMPage31",
    "TMAmbiguousLabelSpec",
    "TMNoteAxisBinding",
    "TMNoteLogicalRow",
    "TMNoteRowKind",
    "TMNoteSpec",
    "TMNoteTable",
    "TMNoteWordBoxError",
    "TMNoteWordBoxPolicy",
    "TMPage31LogicalRow",
    "TMPage31Policy",
    "TMPage31Table",
    "TMPage31TableSpec",
    "TMSchemaDisposition",
    "load_tm_note_word_box_policy",
    "load_tm_page31_policy",
    "parse_tm_page31",
    "parse_tm_note_word_box_page",
]
