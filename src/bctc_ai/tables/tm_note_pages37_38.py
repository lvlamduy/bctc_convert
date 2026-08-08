"""Source-scoped reconstruction of MBB Note 10 on PDF pages 37 and 38."""

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
from bctc_ai.core.text import parse_financial_number, parse_vietnamese_date, retrieval_key
from bctc_ai.evaluation.word_box_rows import VisualCellEvidence
from bctc_ai.evaluation.word_box_rows_v3 import (
    _detect_visible_dash_v3,
    load_word_box_reconstruction_v3_config,
)
from bctc_ai.tables.tm_note_word_box import (
    TMNoteRowKind,
    TMNoteWordBoxError,
    _best_anchor_similarity,
    _Line,
    _load_lines,
    _numeric_only,
    _source_ids,
    _union,
)
from bctc_ai.validation.reader_agreement import ReaderRow

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_AXIS_ROLES = ("BUILDINGS", "MACHINERY", "TRANSPORT", "OTHER_TANGIBLE", "TOTAL")
_PERIOD_ROLES = {"OPENING_SNAPSHOT", "CLOSING_SNAPSHOT", "MOVEMENT_DURATION"}
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
class TMFixedAssetAxisSpec:
    axis_role: str
    anchors: tuple[str, ...]


@dataclass(frozen=True)
class TMFixedAssetRowSpec:
    row_role: str
    label_anchors: tuple[str, ...]
    period_role: str
    expected_observations: tuple[str, ...]


@dataclass(frozen=True)
class TMFixedAssetSectionSpec:
    section_key: str
    title_anchors: tuple[str, ...]
    rows: tuple[TMFixedAssetRowSpec, ...]


@dataclass(frozen=True)
class TMFixedAssetPanelSpec:
    panel_key: str
    page_number: int
    page_tag: str
    source_render_sha256: str
    source_ocr_sha256: str
    note_title_anchors: tuple[str, ...]
    introduction_anchors: tuple[str, ...]
    expected_period_start: date
    expected_period_end: date
    expected_opening_date: date
    period_role: str
    expected_numeric_rows: int
    expected_label_only_rows: int
    expected_value_count: int
    expected_dash_count: int
    sections: tuple[TMFixedAssetSectionSpec, ...]


@dataclass(frozen=True)
class TMFixedAssetPolicy:
    source_path: Path
    document: str
    note_number: str
    scope: str
    scope_binding: str
    source_pdf_sha256: str
    minimum_line_score: float
    minimum_anchor_similarity: float
    minimum_unit_similarity: float
    unit_anchors: tuple[str, ...]
    canonical_unit: str
    unit_multiplier: int
    minimum_axis_separation_line_heights: float
    numeric_axis_max_distance_ratio: float
    numeric_axis_right_overrun_line_heights: float
    row_numeric_attach_line_heights: float
    page_footer_top_ratio: float
    dash_config: dict[str, float | int]
    dash_config_path: Path
    axes: tuple[TMFixedAssetAxisSpec, ...]
    panels: tuple[TMFixedAssetPanelSpec, ...]
    forbidden_semantic_inputs: tuple[str, ...]


@dataclass(frozen=True)
class TMFixedAssetAxisBinding:
    ordinal: int
    axis_role: str
    raw_header_text: str
    header_line_indices: tuple[int, ...]
    raw_unit_text: str
    unit_line_index: int
    axis_right_edge: float
    canonical_unit: str
    unit_multiplier: int
    header_bbox: BoundingBox
    unit_bbox: BoundingBox
    is_total: bool
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class TMFixedAssetLogicalRow:
    row_id: str
    panel_key: str
    page_number: int
    page_tag: str
    section_key: str
    section_ordinal: int
    ordinal: int
    row_role: str
    row: ReaderRow
    row_kind: TMNoteRowKind
    source_role: str
    y_anchor: float
    label_bbox: BoundingBox
    value_bboxes: tuple[BoundingBox | None, ...]
    label_line_indices: tuple[int, ...]
    value_line_indices: tuple[tuple[int, ...], ...]
    visual_cell_evidence: tuple[VisualCellEvidence | None, ...]
    cell_axis_roles: tuple[str, ...]
    period_start: date | None
    period_end: date | None
    period_type: str | None
    period_role: str | None
    mapping_approved: bool

    @property
    def financial_slot_count(self) -> int:
        return len(self.row.cells) if self.row_kind is TMNoteRowKind.NUMERIC else 0


@dataclass(frozen=True)
class TMFixedAssetPanel:
    panel_key: str
    page_number: int
    page_tag: str
    period_role: str
    period_start: date
    period_end: date
    opening_date: date
    introduction_text: str
    introduction_line_indices: tuple[int, ...]
    note_title_text: str | None
    note_title_line_indices: tuple[int, ...]
    note_title_bbox: BoundingBox | None
    axes: tuple[TMFixedAssetAxisBinding, ...]
    rows: tuple[TMFixedAssetLogicalRow, ...]
    line_height: float
    source_ocr_bbox: BoundingBox
    table_bbox: BoundingBox
    unassigned_numeric_line_indices: tuple[int, ...]
    excluded_footer_numeric_line_indices: tuple[int, ...]
    source_render_sha256: str
    source_ocr_sha256: str

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


@dataclass(frozen=True)
class ParsedTMFixedAssetPages37_38:
    document: str
    note_number: str
    scope: str
    scope_binding: str
    source_pdf_sha256: str
    panels: tuple[TMFixedAssetPanel, ...]
    rows: tuple[TMFixedAssetLogicalRow, ...]
    mapping_authority: bool
    evidence: tuple[str, ...]

    @property
    def numeric_row_count(self) -> int:
        return sum(panel.numeric_row_count for panel in self.panels)

    @property
    def label_only_row_count(self) -> int:
        return sum(panel.label_only_row_count for panel in self.panels)

    @property
    def financial_slot_count(self) -> int:
        return sum(panel.financial_slot_count for panel in self.panels)

    def observation_count(self, observation: ObservationKind) -> int:
        return sum(panel.observation_count(observation) for panel in self.panels)


def _anchors(payload: Any, field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(payload, list) or (not payload and not allow_empty):
        raise TMNoteWordBoxError(f"TM pages37-38 {field} anchors are invalid")
    result = tuple(retrieval_key(str(value)) for value in payload)
    if any(not value for value in result):
        raise TMNoteWordBoxError(f"TM pages37-38 {field} has an empty anchor")
    return result


def _positive(payload: dict[str, Any], field: str) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise TMNoteWordBoxError(f"invalid positive TM pages37-38 setting: {field}")
    return float(value)


def _iso_date(payload: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(payload))
    except ValueError as exc:
        raise TMNoteWordBoxError(f"invalid TM pages37-38 date: {field}") from exc


def _positive_int(payload: dict[str, Any], field: str) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise TMNoteWordBoxError(f"invalid positive TM pages37-38 denominator: {field}")
    return value


def load_tm_fixed_asset_pages37_38_policy(path: Path) -> TMFixedAssetPolicy:
    """Load the immutable geometry/status contract for visible Note 10 panels."""

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMNoteWordBoxError(f"cannot load TM pages37-38 policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGES37_38_TANGIBLE_FIXED_ASSETS_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("scope") != "CONSOLIDATED"
        or payload.get("note_number") != "10"
    ):
        raise TMNoteWordBoxError("TM pages37-38 policy identity drifted")
    source_pdf_hash = payload.get("source_pdf_sha256")
    if not isinstance(source_pdf_hash, str) or not _SHA256.fullmatch(source_pdf_hash):
        raise TMNoteWordBoxError("TM pages37-38 source PDF hash is invalid")
    thresholds = (
        payload.get("minimum_line_score"),
        payload.get("minimum_anchor_similarity"),
        payload.get("minimum_unit_similarity"),
    )
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1
        for value in thresholds
    ):
        raise TMNoteWordBoxError("TM pages37-38 similarity thresholds are invalid")
    unit = payload.get("unit")
    geometry = payload.get("geometry")
    if not isinstance(unit, dict) or not isinstance(geometry, dict):
        raise TMNoteWordBoxError("TM pages37-38 geometry or unit policy is incomplete")
    multiplier = unit.get("multiplier")
    canonical = unit.get("canonical")
    if (
        isinstance(multiplier, bool)
        or not isinstance(multiplier, int)
        or multiplier <= 0
        or not isinstance(canonical, str)
        or not canonical
    ):
        raise TMNoteWordBoxError("TM pages37-38 unit binding is invalid")
    footer_ratio = _positive(geometry, "page_footer_top_ratio")
    if footer_ratio >= 1:
        raise TMNoteWordBoxError("TM pages37-38 footer ratio must be below one")
    dash_name = payload.get("dash_detector_config")
    if not isinstance(dash_name, str) or Path(dash_name).name != dash_name:
        raise TMNoteWordBoxError("TM pages37-38 dash detector path is invalid")
    dash_path = (path.parent / dash_name).resolve()
    if not dash_path.is_file() or sha256_file(dash_path) != payload.get(
        "dash_detector_config_sha256"
    ):
        raise TMNoteWordBoxError("TM pages37-38 dash detector is absent or drifted")
    dash_config = load_word_box_reconstruction_v3_config(dash_path).base.base

    raw_axes = payload.get("axes")
    if not isinstance(raw_axes, list) or len(raw_axes) != 5:
        raise TMNoteWordBoxError("TM pages37-38 must define four classes plus TOTAL")
    axes = []
    for record in raw_axes:
        if not isinstance(record, dict) or not isinstance(record.get("axis_role"), str):
            raise TMNoteWordBoxError("TM pages37-38 axis record is invalid")
        axes.append(
            TMFixedAssetAxisSpec(
                axis_role=record["axis_role"],
                anchors=_anchors(record.get("anchors"), f"axis {record['axis_role']}"),
            )
        )
    if tuple(axis.axis_role for axis in axes) != _AXIS_ROLES:
        raise TMNoteWordBoxError("TM pages37-38 axis roles drifted from visible source order")

    raw_panels = payload.get("panels")
    if not isinstance(raw_panels, list) or len(raw_panels) != 2:
        raise TMNoteWordBoxError("TM pages37-38 must define two visible rollforward panels")
    panels = []
    valid_observations = {ObservationKind.VALUE.value, ObservationKind.DASH.value}
    for record in raw_panels:
        if not isinstance(record, dict):
            raise TMNoteWordBoxError("TM pages37-38 panel record is invalid")
        hashes = (record.get("source_render_sha256"), record.get("source_ocr_sha256"))
        if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
            raise TMNoteWordBoxError("TM pages37-38 panel hashes are invalid")
        raw_sections = record.get("sections")
        if not isinstance(raw_sections, list) or len(raw_sections) != 3:
            raise TMNoteWordBoxError("each TM fixed-asset panel must define three sections")
        sections = []
        for raw_section in raw_sections:
            if not isinstance(raw_section, dict) or not isinstance(
                raw_section.get("section_key"), str
            ):
                raise TMNoteWordBoxError("TM fixed-asset section record is invalid")
            raw_rows = raw_section.get("rows")
            if not isinstance(raw_rows, list) or not raw_rows:
                raise TMNoteWordBoxError("TM fixed-asset section has no numeric rows")
            rows = []
            for raw_row in raw_rows:
                if not isinstance(raw_row, dict) or not isinstance(raw_row.get("row_role"), str):
                    raise TMNoteWordBoxError("TM fixed-asset row record is invalid")
                observations = raw_row.get("expected_observations")
                if (
                    not isinstance(observations, list)
                    or len(observations) != 5
                    or any(value not in valid_observations for value in observations)
                    or raw_row.get("period_role") not in _PERIOD_ROLES
                ):
                    raise TMNoteWordBoxError(
                        "TM fixed-asset row observation/period contract drifted"
                    )
                rows.append(
                    TMFixedAssetRowSpec(
                        row_role=raw_row["row_role"],
                        label_anchors=_anchors(
                            raw_row.get("label_anchors"), f"row {raw_row['row_role']}"
                        ),
                        period_role=raw_row["period_role"],
                        expected_observations=tuple(str(value) for value in observations),
                    )
                )
            sections.append(
                TMFixedAssetSectionSpec(
                    section_key=raw_section["section_key"],
                    title_anchors=_anchors(
                        raw_section.get("title_anchors"),
                        f"section {raw_section['section_key']}",
                    ),
                    rows=tuple(rows),
                )
            )
        panel = TMFixedAssetPanelSpec(
            panel_key=str(record.get("panel_key", "")),
            page_number=_positive_int(record, "page_number"),
            page_tag=str(record.get("page_tag", "")),
            source_render_sha256=hashes[0],
            source_ocr_sha256=hashes[1],
            note_title_anchors=_anchors(
                record.get("note_title_anchors", []), "note title", allow_empty=True
            ),
            introduction_anchors=_anchors(record.get("introduction_anchors"), "introduction"),
            expected_period_start=_iso_date(record.get("expected_period_start"), "period start"),
            expected_period_end=_iso_date(record.get("expected_period_end"), "period end"),
            expected_opening_date=_iso_date(record.get("expected_opening_date"), "opening date"),
            period_role=str(record.get("period_role", "")),
            expected_numeric_rows=_positive_int(record, "expected_numeric_rows"),
            expected_label_only_rows=_positive_int(record, "expected_label_only_rows"),
            expected_value_count=_positive_int(record, "expected_value_count"),
            expected_dash_count=_positive_int(record, "expected_dash_count"),
            sections=tuple(sections),
        )
        if panel.page_tag != f"page-{panel.page_number:04d}":
            raise TMNoteWordBoxError("TM pages37-38 page tag drifted")
        if panel.period_role not in {"CURRENT", "COMPARATIVE"}:
            raise TMNoteWordBoxError("TM pages37-38 panel period role is invalid")
        panels.append(panel)
    if (
        tuple(panel.page_number for panel in panels) != (37, 38)
        or tuple(panel.expected_numeric_rows for panel in panels) != (14, 15)
        or tuple(panel.expected_label_only_rows for panel in panels) != (3, 3)
        or tuple(panel.expected_value_count for panel in panels) != (60, 70)
        or tuple(panel.expected_dash_count for panel in panels) != (10, 5)
    ):
        raise TMNoteWordBoxError("TM pages37-38 source denominators drifted")
    forbidden = payload.get("forbidden_semantic_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMNoteWordBoxError("TM pages37-38 forbidden semantic inputs drifted")
    return TMFixedAssetPolicy(
        source_path=path,
        document=str(payload.get("document", "")),
        note_number="10",
        scope="CONSOLIDATED",
        scope_binding=str(payload.get("scope_binding", "")),
        source_pdf_sha256=source_pdf_hash,
        minimum_line_score=float(thresholds[0]),
        minimum_anchor_similarity=float(thresholds[1]),
        minimum_unit_similarity=float(thresholds[2]),
        unit_anchors=_anchors(unit.get("anchors"), "unit"),
        canonical_unit=canonical,
        unit_multiplier=multiplier,
        minimum_axis_separation_line_heights=_positive(
            geometry, "minimum_axis_separation_line_heights"
        ),
        numeric_axis_max_distance_ratio=_positive(geometry, "numeric_axis_max_distance_ratio"),
        numeric_axis_right_overrun_line_heights=_positive(
            geometry, "numeric_axis_right_overrun_line_heights"
        ),
        row_numeric_attach_line_heights=_positive(geometry, "row_numeric_attach_line_heights"),
        page_footer_top_ratio=footer_ratio,
        dash_config={str(key): value for key, value in dash_config.items()},
        dash_config_path=dash_path,
        axes=tuple(axes),
        panels=tuple(panels),
        forbidden_semantic_inputs=tuple(str(value) for value in forbidden),
    )


def _best_line(
    lines: tuple[_Line, ...],
    anchors: tuple[str, ...],
    minimum: float,
    *,
    lower_y: float = float("-inf"),
    upper_y: float = float("inf"),
    maximum_x: float = float("inf"),
) -> _Line:
    candidates = [
        line for line in lines if lower_y < line.y_center < upper_y and line.bbox.x1 < maximum_x
    ]
    scored = sorted(
        ((_best_anchor_similarity(line.text, anchors), line) for line in candidates),
        key=lambda item: (item[0], -item[1].y_center),
        reverse=True,
    )
    if not scored or scored[0][0] < minimum:
        raise TMNoteWordBoxError(f"visible TM pages37-38 anchor is absent: {anchors}")
    return scored[0][1]


def _bind_axes(
    lines: tuple[_Line, ...],
    intro: _Line,
    first_section: _Line,
    policy: TMFixedAssetPolicy,
    line_height: float,
) -> tuple[TMFixedAssetAxisBinding, ...]:
    units = tuple(
        sorted(
            (
                line
                for line in lines
                if intro.y_center < line.y_center < first_section.y_center
                and not any(character.isdigit() for character in retrieval_key(line.text))
                and _best_anchor_similarity(line.text, policy.unit_anchors)
                >= policy.minimum_unit_similarity
            ),
            key=lambda line: line.x_right,
        )
    )
    if len(units) != 5:
        raise TMNoteWordBoxError("TM pages37-38 must expose four class units plus TOTAL unit")
    gaps = [right.x_right - left.x_right for left, right in zip(units, units[1:], strict=False)]
    if min(gaps) < line_height * policy.minimum_axis_separation_line_heights:
        raise TMNoteWordBoxError("TM pages37-38 visible axes are not distinctly separated")
    median_gap = statistics.median(gaps)
    boundaries = [units[0].x_right - median_gap * 0.8]
    boundaries.extend(
        (left.x_right + right.x_right) / 2 for left, right in zip(units, units[1:], strict=False)
    )
    boundaries.append(units[-1].x_right + median_gap * 0.8)
    result = []
    unit_ids = {line.index for line in units}
    for ordinal, (spec, unit_line) in enumerate(zip(policy.axes, units, strict=True), start=1):
        header_lines = tuple(
            sorted(
                (
                    line
                    for line in lines
                    if intro.bbox.y1 < line.y_center <= unit_line.y_center
                    and line.index not in unit_ids
                    and boundaries[ordinal - 1] < line.x_center < boundaries[ordinal]
                    and not _numeric_only(line.text)
                ),
                key=lambda line: (line.y_center, line.bbox.x0),
            )
        )
        raw_header = " ".join(line.text for line in header_lines)
        if (
            not header_lines
            or _best_anchor_similarity(raw_header, spec.anchors) < policy.minimum_anchor_similarity
        ):
            raise TMNoteWordBoxError(f"TM pages37-38 axis header unresolved: {spec.axis_role}")
        result.append(
            TMFixedAssetAxisBinding(
                ordinal=ordinal,
                axis_role=spec.axis_role,
                raw_header_text=raw_header,
                header_line_indices=tuple(line.index for line in header_lines),
                raw_unit_text=unit_line.text,
                unit_line_index=unit_line.index,
                axis_right_edge=unit_line.x_right,
                canonical_unit=policy.canonical_unit,
                unit_multiplier=policy.unit_multiplier,
                header_bbox=_union([*header_lines, unit_line]),
                unit_bbox=unit_line.bbox,
                is_total=spec.axis_role == "TOTAL",
                evidence=(
                    "asset-class role matched from the visible local multi-line header",
                    "numeric axis uses the right edge of its own visible unit label",
                    "unit is VND million from the repeated visible local unit",
                ),
            )
        )
    return tuple(result)


def _row_period(panel: TMFixedAssetPanelSpec, period_role: str) -> tuple[date, date, str]:
    if period_role == "OPENING_SNAPSHOT":
        return panel.expected_opening_date, panel.expected_opening_date, "SNAPSHOT"
    if period_role == "CLOSING_SNAPSHOT":
        return panel.expected_period_end, panel.expected_period_end, "SNAPSHOT"
    if period_role == "MOVEMENT_DURATION":
        return panel.expected_period_start, panel.expected_period_end, "DURATION"
    raise TMNoteWordBoxError(f"unsupported TM fixed-asset period role: {period_role}")


def _parse_panel(
    result_path: Path,
    source_image_path: Path,
    panel_spec: TMFixedAssetPanelSpec,
    policy: TMFixedAssetPolicy,
) -> TMFixedAssetPanel:
    if sha256_file(result_path) != panel_spec.source_ocr_sha256:
        raise TMNoteWordBoxError(f"TM page {panel_spec.page_number} OCR artifact hash drifted")
    if sha256_file(source_image_path) != panel_spec.source_render_sha256:
        raise TMNoteWordBoxError(f"TM page {panel_spec.page_number} source render hash drifted")
    source_image = cv2.imread(str(source_image_path), cv2.IMREAD_GRAYSCALE)
    if source_image is None:
        raise TMNoteWordBoxError(f"TM page {panel_spec.page_number} render cannot be decoded")
    _input_path, lines, _metadata = _load_lines(result_path, policy.minimum_line_score)
    line_height = float(statistics.median(line.height for line in lines))
    if line_height <= 0:
        raise TMNoteWordBoxError("TM pages37-38 median line height is invalid")
    source_bbox = _union(lines)
    intro = _best_line(
        lines,
        panel_spec.introduction_anchors,
        policy.minimum_anchor_similarity,
        maximum_x=source_bbox.x1 * 0.75,
    )
    parsed_end = parse_vietnamese_date(intro.text)
    if parsed_end != panel_spec.expected_period_end:
        raise TMNoteWordBoxError("TM fixed-asset visible panel date drifted")
    note_title: _Line | None = None
    if panel_spec.note_title_anchors:
        note_title = _best_line(
            lines,
            panel_spec.note_title_anchors,
            policy.minimum_anchor_similarity,
            upper_y=intro.y_center,
            maximum_x=source_bbox.x1 * 0.45,
        )
    section_titles = []
    lower_y = intro.y_center
    for section in panel_spec.sections:
        title = _best_line(
            lines,
            section.title_anchors,
            policy.minimum_anchor_similarity,
            lower_y=lower_y,
            maximum_x=source_bbox.x1 * 0.45,
        )
        section_titles.append(title)
        lower_y = title.y_center
    axes = _bind_axes(lines, intro, section_titles[0], policy, line_height)

    skeletons: list[tuple[TMFixedAssetSectionSpec, int, int, TMFixedAssetRowSpec, _Line]] = []
    global_ordinal = 0
    for section_index, (section, title) in enumerate(
        zip(panel_spec.sections, section_titles, strict=True), start=1
    ):
        global_ordinal += 1
        lower = title.y_center
        upper = (
            section_titles[section_index].y_center
            if section_index < len(section_titles)
            else source_bbox.y1 * policy.page_footer_top_ratio
        )
        candidates = tuple(
            line
            for line in lines
            if lower < line.y_center < upper
            and line.bbox.x1
            < axes[0].axis_right_edge
            - statistics.median(
                right.axis_right_edge - left.axis_right_edge
                for left, right in zip(axes, axes[1:], strict=False)
            )
            * 0.25
            and not _numeric_only(line.text)
        )
        prior_y = lower
        for row_index, row_spec in enumerate(section.rows, start=2):
            label = _best_line(
                candidates,
                row_spec.label_anchors,
                policy.minimum_anchor_similarity,
                lower_y=prior_y,
                upper_y=upper,
            )
            prior_y = label.y_center
            global_ordinal += 1
            skeletons.append((section, row_index, global_ordinal, row_spec, label))

    axis_edges = tuple(axis.axis_right_edge for axis in axes)
    typical_gap = statistics.median(
        right - left for left, right in zip(axis_edges, axis_edges[1:], strict=False)
    )
    maximum_axis_distance = typical_gap * policy.numeric_axis_max_distance_ratio
    numeric_rows = [item[4] for item in skeletons]
    footer_top = source_bbox.y1 * policy.page_footer_top_ratio
    body_start = max(axis.unit_bbox.y1 for axis in axes)
    numeric_candidates = [
        line
        for line in lines
        if body_start < line.y_center < footer_top
        and line.x_right > axis_edges[0] - typical_gap * 0.65
        and line.x_right
        <= axis_edges[-1] + line_height * policy.numeric_axis_right_overrun_line_heights
        and _numeric_only(line.text)
    ]
    assigned: dict[tuple[int, int], list[_Line]] = {}
    unassigned = []
    for line in numeric_candidates:
        row_index = min(
            range(len(numeric_rows)),
            key=lambda index: abs(line.y_center - numeric_rows[index].y_center),
        )
        axis_index = min(
            range(len(axis_edges)), key=lambda index: abs(line.x_right - axis_edges[index])
        )
        if (
            abs(line.y_center - numeric_rows[row_index].y_center)
            > line_height * policy.row_numeric_attach_line_heights
            or abs(line.x_right - axis_edges[axis_index]) > maximum_axis_distance
        ):
            unassigned.append(line)
        else:
            assigned.setdefault((row_index, axis_index), []).append(line)
    if unassigned:
        raise TMNoteWordBoxError(
            f"TM page {panel_spec.page_number} has unassigned table numeric lines"
        )

    rows: list[TMFixedAssetLogicalRow] = []
    skeleton_offset = 0
    global_ordinal = 0
    for _section_index, (section, title) in enumerate(
        zip(panel_spec.sections, section_titles, strict=True), start=1
    ):
        global_ordinal += 1
        rows.append(
            TMFixedAssetLogicalRow(
                row_id=(f"{panel_spec.page_tag}:{section.section_key.casefold()}:row-0001"),
                panel_key=panel_spec.panel_key,
                page_number=panel_spec.page_number,
                page_tag=panel_spec.page_tag,
                section_key=section.section_key,
                section_ordinal=1,
                ordinal=global_ordinal,
                row_role="SECTION_HEADER",
                row=ReaderRow(
                    source_row_ids=_source_ids(panel_spec.page_tag, [title]),
                    label=title.text,
                    note_reference=None,
                    cells=(),
                ),
                row_kind=TMNoteRowKind.LABEL_ONLY,
                source_role="SECTION_HEADER",
                y_anchor=title.y_center,
                label_bbox=title.bbox,
                value_bboxes=(),
                label_line_indices=(title.index,),
                value_line_indices=(),
                visual_cell_evidence=(),
                cell_axis_roles=(),
                period_start=None,
                period_end=None,
                period_type=None,
                period_role=None,
                mapping_approved=False,
            )
        )
        for section_row_index, row_spec in enumerate(section.rows, start=2):
            _, _, _, _, label = skeletons[skeleton_offset]
            numeric_index = skeleton_offset
            skeleton_offset += 1
            global_ordinal += 1
            cells = []
            value_bboxes = []
            value_line_indices = []
            visual_evidence = []
            source_lines = [label]
            for axis_index, expected in enumerate(row_spec.expected_observations):
                cell_lines = sorted(
                    assigned.get((numeric_index, axis_index), []), key=lambda line: line.bbox.x0
                )
                if len(cell_lines) > 1:
                    raise TMNoteWordBoxError(
                        f"TM page {panel_spec.page_number} cell contains multiple OCR numbers"
                    )
                parsed_cell = parse_financial_number(
                    " ".join(line.text for line in cell_lines) if cell_lines else "-"
                )
                evidence = None
                if expected == ObservationKind.DASH.value:
                    if cell_lines and parsed_cell.observation is not ObservationKind.DASH:
                        raise TMNoteWordBoxError("visible DASH contract contains an OCR number")
                    evidence = _detect_visible_dash_v3(
                        source_image,
                        source_image_path=source_image_path,
                        axis_right_edge=axis_edges[axis_index],
                        anchor_center=label.y_center,
                        line_height=line_height,
                        config=policy.dash_config,
                    )
                    if evidence is None:
                        raise TMNoteWordBoxError(
                            "OCR-missing DASH lacks constrained render-pixel evidence"
                        )
                    parsed_cell = parse_financial_number("-")
                elif (
                    not cell_lines
                    or parsed_cell.observation.value != expected
                    or parsed_cell.value is None
                ):
                    raise TMNoteWordBoxError("TM fixed-asset numeric cell status drifted")
                cells.append(parsed_cell)
                value_bboxes.append(
                    _union(cell_lines)
                    if cell_lines
                    else BoundingBox(*evidence.component_box)
                    if evidence is not None
                    else None
                )
                value_line_indices.append(tuple(line.index for line in cell_lines))
                visual_evidence.append(evidence)
                source_lines.extend(cell_lines)
            period_start, period_end, period_type = _row_period(panel_spec, row_spec.period_role)
            rows.append(
                TMFixedAssetLogicalRow(
                    row_id=(
                        f"{panel_spec.page_tag}:{section.section_key.casefold()}:"
                        f"row-{section_row_index:04d}"
                    ),
                    panel_key=panel_spec.panel_key,
                    page_number=panel_spec.page_number,
                    page_tag=panel_spec.page_tag,
                    section_key=section.section_key,
                    section_ordinal=section_row_index,
                    ordinal=global_ordinal,
                    row_role=row_spec.row_role,
                    row=ReaderRow(
                        source_row_ids=_source_ids(panel_spec.page_tag, source_lines),
                        label=label.text,
                        note_reference=None,
                        cells=tuple(cells),
                    ),
                    row_kind=TMNoteRowKind.NUMERIC,
                    source_role=row_spec.row_role,
                    y_anchor=label.y_center,
                    label_bbox=label.bbox,
                    value_bboxes=tuple(value_bboxes),
                    label_line_indices=(label.index,),
                    value_line_indices=tuple(value_line_indices),
                    visual_cell_evidence=tuple(visual_evidence),
                    cell_axis_roles=_AXIS_ROLES,
                    period_start=period_start,
                    period_end=period_end,
                    period_type=period_type,
                    period_role=panel_spec.period_role,
                    mapping_approved=False,
                )
            )
    footer = tuple(
        sorted(
            line.index for line in lines if line.y_center >= footer_top and _numeric_only(line.text)
        )
    )
    panel = TMFixedAssetPanel(
        panel_key=panel_spec.panel_key,
        page_number=panel_spec.page_number,
        page_tag=panel_spec.page_tag,
        period_role=panel_spec.period_role,
        period_start=panel_spec.expected_period_start,
        period_end=panel_spec.expected_period_end,
        opening_date=panel_spec.expected_opening_date,
        introduction_text=intro.text,
        introduction_line_indices=(intro.index,),
        note_title_text=note_title.text if note_title is not None else None,
        note_title_line_indices=(note_title.index,) if note_title is not None else (),
        note_title_bbox=note_title.bbox if note_title is not None else None,
        axes=axes,
        rows=tuple(rows),
        line_height=line_height,
        source_ocr_bbox=source_bbox,
        table_bbox=BoundingBox(
            min(row.label_bbox.x0 for row in rows),
            min(axis.header_bbox.y0 for axis in axes),
            max(axis.unit_bbox.x1 for axis in axes),
            max(
                bbox.y1
                for row in rows
                for bbox in (row.label_bbox, *[item for item in row.value_bboxes if item])
            ),
        ),
        unassigned_numeric_line_indices=(),
        excluded_footer_numeric_line_indices=footer,
        source_render_sha256=panel_spec.source_render_sha256,
        source_ocr_sha256=panel_spec.source_ocr_sha256,
    )
    if (
        panel.numeric_row_count != panel_spec.expected_numeric_rows
        or panel.label_only_row_count != panel_spec.expected_label_only_rows
        or panel.financial_slot_count != panel_spec.expected_numeric_rows * 5
        or panel.observation_count(ObservationKind.VALUE) != panel_spec.expected_value_count
        or panel.observation_count(ObservationKind.DASH) != panel_spec.expected_dash_count
    ):
        raise TMNoteWordBoxError(
            f"TM page {panel_spec.page_number} fixed-asset denominator drifted"
        )
    return panel


def parse_tm_fixed_asset_pages37_38(
    result_paths: dict[int, Path],
    source_image_paths: dict[int, Path],
    policy: TMFixedAssetPolicy,
) -> ParsedTMFixedAssetPages37_38:
    """Reconstruct both visible panels without granting ReportNormId authority."""

    if set(result_paths) != {37, 38} or set(source_image_paths) != {37, 38}:
        raise TMNoteWordBoxError("TM pages37-38 inputs must contain exactly pages 37 and 38")
    panels = tuple(
        _parse_panel(
            result_paths[panel.page_number],
            source_image_paths[panel.page_number],
            panel,
            policy,
        )
        for panel in policy.panels
    )
    result = ParsedTMFixedAssetPages37_38(
        document=policy.document,
        note_number=policy.note_number,
        scope=policy.scope,
        scope_binding=policy.scope_binding,
        source_pdf_sha256=policy.source_pdf_sha256,
        panels=panels,
        rows=tuple(row for panel in panels for row in panel.rows),
        mapping_authority=False,
        evidence=(
            "two visible Note 10 rollforward panels located from their own dated introductions",
            "each panel exposes four asset-class axes plus one TOTAL axis",
            "29 numeric rows and six structural section rows reconstructed from source order",
            "130 values parsed from PP-OCRv6 word boxes",
            "15 OCR-missing dashes accepted only with constrained render-pixel evidence",
            "DASH remains semantically distinct from numeric zero",
            "this parser grants no ReportNormId authority",
        ),
    )
    if (
        len(result.rows) != 35
        or result.numeric_row_count != 29
        or result.label_only_row_count != 6
        or result.financial_slot_count != 145
        or result.observation_count(ObservationKind.VALUE) != 130
        or result.observation_count(ObservationKind.DASH) != 15
    ):
        raise TMNoteWordBoxError("TM pages37-38 combined source denominator drifted")
    return result


__all__ = [
    "ParsedTMFixedAssetPages37_38",
    "TMFixedAssetAxisBinding",
    "TMFixedAssetLogicalRow",
    "TMFixedAssetPanel",
    "TMFixedAssetPolicy",
    "load_tm_fixed_asset_pages37_38_policy",
    "parse_tm_fixed_asset_pages37_38",
]
