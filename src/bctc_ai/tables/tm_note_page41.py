"""Dual-duration investment-property roll-forward reconstruction for TM page 41."""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import cv2
import yaml
from rapidfuzz.fuzz import ratio

from bctc_ai.core.contracts import BoundingBox, ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import normalize_text, parse_financial_number, retrieval_key
from bctc_ai.evaluation.word_box_rows import VisualCellEvidence
from bctc_ai.evaluation.word_box_rows_v3 import (
    _detect_visible_dash_v3,
    load_word_box_reconstruction_v3_config,
)
from bctc_ai.tables.tm_note_word_box import (
    TMNoteRowKind,
    TMNoteWordBoxError,
    _Line,
    _load_lines,
    _numeric_only,
    _source_ids,
    _union,
)
from bctc_ai.validation.reader_agreement import ReaderRow

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_AXIS_ROLES = ("BUILDINGS_AND_STRUCTURES", "TERM_LAND_USE_RIGHTS", "TOTAL")
_REQUIRED_FORBIDDEN = {
    "missing_ocr_cell_as_dash_without_pixel_evidence",
    "template_labels_as_row_reconstruction_input",
    "approved_report_norm_id_assignment",
    "historical_or_mongodb_values",
    "human_review_answers",
    "dash_as_zero",
    "accounting_equations_as_value_imputation",
    "cross_panel_values_as_value_imputation",
}


@dataclass(frozen=True)
class TMPage41AxisSpec:
    role: str
    anchors: tuple[str, ...]


@dataclass(frozen=True)
class TMPage41RowSpec:
    row_key: str
    label_anchors: tuple[str, ...]
    expected_observations: tuple[str, ...]


@dataclass(frozen=True)
class TMPage41SectionSpec:
    section_key: str
    title_anchors: tuple[str, ...]
    rows: tuple[TMPage41RowSpec, ...]


@dataclass(frozen=True)
class TMPage41PanelSpec:
    panel_key: str
    period_intro_anchors: tuple[str, ...]
    period_start: date
    period_end: date
    expected_axis_numeric_counts: tuple[int, ...]
    sections: tuple[TMPage41SectionSpec, ...]


@dataclass(frozen=True)
class TMPage41Policy:
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
    page_footer_top_ratio: float
    note_title_anchors: tuple[str, ...]
    canonical_unit: str
    unit_multiplier: int
    unit_anchors: tuple[str, ...]
    axes: tuple[TMPage41AxisSpec, ...]
    panels: tuple[TMPage41PanelSpec, ...]
    dash_config: dict[str, float | int]
    dash_config_path: Path
    forbidden_semantic_inputs: tuple[str, ...]


@dataclass(frozen=True)
class TMPage41AxisBinding:
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
class TMPage41LogicalRow:
    row_id: str
    panel_key: str
    section_key: str
    row_key: str
    ordinal: int
    row: ReaderRow
    row_kind: TMNoteRowKind
    source_role: str
    y_anchor: float
    label_bbox: BoundingBox
    value_bboxes: tuple[BoundingBox | None, ...]
    label_line_indices: tuple[int, ...]
    value_line_indices: tuple[tuple[int, ...], ...]
    visual_cell_evidence: tuple[VisualCellEvidence | None, ...]
    mapping_approved: bool

    @property
    def financial_slot_count(self) -> int:
        return len(self.row.cells) if self.row_kind is TMNoteRowKind.NUMERIC else 0


@dataclass(frozen=True)
class TMPage41Panel:
    ordinal: int
    panel_key: str
    period_intro: str
    period_intro_line_indices: tuple[int, ...]
    period_start: date
    period_end: date
    axes: tuple[TMPage41AxisBinding, ...]
    rows: tuple[TMPage41LogicalRow, ...]
    bbox: BoundingBox


@dataclass(frozen=True)
class ParsedTMPage41:
    input_path: str
    source_sha256: str
    source_render_sha256: str
    source_pdf_sha256: str
    page_tag: str
    scope: str
    scope_binding: str
    note_title: str
    note_title_line_indices: tuple[int, ...]
    panels: tuple[TMPage41Panel, ...]
    rows: tuple[TMPage41LogicalRow, ...]
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


def _anchors(payload: Any, field: str) -> tuple[str, ...]:
    if not isinstance(payload, list) or not payload:
        raise TMNoteWordBoxError(f"TM page-41 {field} anchors are invalid")
    result = tuple(retrieval_key(str(value)) for value in payload)
    if any(not value for value in result):
        raise TMNoteWordBoxError(f"TM page-41 {field} contains an empty anchor")
    return result


def _date_value(value: Any, field: str) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise TMNoteWordBoxError(f"TM page-41 {field} is invalid") from exc
    raise TMNoteWordBoxError(f"TM page-41 {field} is invalid")


def load_tm_page41_policy(path: Path) -> TMPage41Policy:
    """Load the immutable source-only reconstruction policy for page 41."""

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMNoteWordBoxError(f"cannot load TM page-41 policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE41_DUAL_DURATION_ROLLFORWARD_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 41
        or payload.get("page_tag") != "page-0041"
        or payload.get("scope") != "CONSOLIDATED"
    ):
        raise TMNoteWordBoxError("TM page-41 policy identity drifted")
    hashes = (
        payload.get("source_pdf_sha256"),
        payload.get("source_render_sha256"),
        payload.get("source_ocr_sha256"),
    )
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMNoteWordBoxError("TM page-41 source hashes are invalid")
    minimum_line_score = payload.get("minimum_line_score")
    minimum_similarity = payload.get("minimum_anchor_similarity")
    footer_ratio = payload.get("page_footer_top_ratio")
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= float(value) <= 1
        for value in (minimum_line_score, minimum_similarity)
    ) or (
        isinstance(footer_ratio, bool)
        or not isinstance(footer_ratio, (int, float))
        or not 0 < float(footer_ratio) < 1
    ):
        raise TMNoteWordBoxError("TM page-41 thresholds are invalid")
    unit = payload.get("unit")
    if not isinstance(unit, dict):
        raise TMNoteWordBoxError("TM page-41 unit policy is absent")
    multiplier = unit.get("multiplier")
    canonical_unit = unit.get("canonical")
    if (
        isinstance(multiplier, bool)
        or not isinstance(multiplier, int)
        or multiplier <= 0
        or not isinstance(canonical_unit, str)
        or not canonical_unit
    ):
        raise TMNoteWordBoxError("TM page-41 unit binding is invalid")
    raw_axes = payload.get("axis_header_anchors")
    if not isinstance(raw_axes, list) or len(raw_axes) != 3:
        raise TMNoteWordBoxError("TM page-41 axis denominator drifted")
    axes = tuple(
        TMPage41AxisSpec(
            role=str(record.get("role", "")),
            anchors=_anchors(record.get("anchors"), "axis"),
        )
        for record in raw_axes
        if isinstance(record, dict)
    )
    if len(axes) != 3 or tuple(axis.role for axis in axes) != _AXIS_ROLES:
        raise TMNoteWordBoxError("TM page-41 axis roles drifted")
    raw_panels = payload.get("panels")
    if not isinstance(raw_panels, list) or len(raw_panels) != 2:
        raise TMNoteWordBoxError("TM page-41 panel denominator drifted")
    valid_observations = {item.value for item in ObservationKind}
    panels = []
    for raw_panel in raw_panels:
        if not isinstance(raw_panel, dict):
            raise TMNoteWordBoxError("TM page-41 panel is invalid")
        counts = raw_panel.get("expected_axis_numeric_counts")
        raw_sections = raw_panel.get("sections")
        if (
            not isinstance(counts, list)
            or len(counts) != 3
            or any(
                isinstance(value, bool) or not isinstance(value, int) or value <= 0
                for value in counts
            )
            or not isinstance(raw_sections, list)
            or len(raw_sections) != 3
        ):
            raise TMNoteWordBoxError("TM page-41 panel geometry is invalid")
        sections = []
        for raw_section in raw_sections:
            if not isinstance(raw_section, dict):
                raise TMNoteWordBoxError("TM page-41 section is invalid")
            raw_rows = raw_section.get("rows")
            if not isinstance(raw_rows, list) or not raw_rows:
                raise TMNoteWordBoxError("TM page-41 section rows are invalid")
            rows = []
            for raw_row in raw_rows:
                if not isinstance(raw_row, dict):
                    raise TMNoteWordBoxError("TM page-41 row is invalid")
                observations = raw_row.get("expected_observations")
                row_key = raw_row.get("row_key")
                if (
                    not isinstance(row_key, str)
                    or not row_key
                    or not isinstance(observations, list)
                    or len(observations) != 3
                    or any(item not in valid_observations for item in observations)
                ):
                    raise TMNoteWordBoxError("TM page-41 row identity drifted")
                rows.append(
                    TMPage41RowSpec(
                        row_key=row_key,
                        label_anchors=_anchors(raw_row.get("label_anchors"), "row label"),
                        expected_observations=tuple(observations),
                    )
                )
            sections.append(
                TMPage41SectionSpec(
                    section_key=str(raw_section.get("section_key", "")),
                    title_anchors=_anchors(raw_section.get("title_anchors"), "section title"),
                    rows=tuple(rows),
                )
            )
        panels.append(
            TMPage41PanelSpec(
                panel_key=str(raw_panel.get("panel_key", "")),
                period_intro_anchors=_anchors(
                    raw_panel.get("period_intro_anchors"), "period intro"
                ),
                period_start=_date_value(raw_panel.get("period_start"), "period start"),
                period_end=_date_value(raw_panel.get("period_end"), "period end"),
                expected_axis_numeric_counts=tuple(counts),
                sections=tuple(sections),
            )
        )
    if (
        tuple(panel.panel_key for panel in panels) != ("Q1_2026", "FY_2025")
        or [sum(len(section.rows) for section in panel.sections) for panel in panels] != [9, 10]
        or any(
            tuple(section.section_key for section in panel.sections)
            != ("GROSS_COST", "ACCUMULATED_DEPRECIATION", "NET_BOOK_VALUE")
            for panel in panels
        )
    ):
        raise TMNoteWordBoxError("TM page-41 panel contract drifted")
    dash_name = payload.get("dash_detector_config")
    if not isinstance(dash_name, str) or Path(dash_name).name != dash_name:
        raise TMNoteWordBoxError("TM page-41 dash detector path is invalid")
    dash_path = (path.parent / dash_name).resolve()
    if not dash_path.is_file() or sha256_file(dash_path) != payload.get(
        "dash_detector_config_sha256"
    ):
        raise TMNoteWordBoxError("TM page-41 dash detector is absent or drifted")
    dash_config = load_word_box_reconstruction_v3_config(dash_path).base.base
    forbidden = payload.get("forbidden_semantic_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMNoteWordBoxError("TM page-41 forbidden semantic inputs drifted")
    return TMPage41Policy(
        source_path=path,
        document=str(payload.get("document", "")),
        page_number=41,
        page_tag="page-0041",
        scope="CONSOLIDATED",
        scope_binding=str(payload.get("scope_binding", "")),
        source_pdf_sha256=hashes[0],
        source_render_sha256=hashes[1],
        source_ocr_sha256=hashes[2],
        minimum_line_score=float(minimum_line_score),
        minimum_anchor_similarity=float(minimum_similarity),
        page_footer_top_ratio=float(footer_ratio),
        note_title_anchors=_anchors(payload.get("note_title_anchors"), "note title"),
        canonical_unit=canonical_unit,
        unit_multiplier=multiplier,
        unit_anchors=_anchors(unit.get("anchors"), "unit"),
        axes=axes,
        panels=tuple(panels),
        dash_config={str(key): value for key, value in dash_config.items()},
        dash_config_path=dash_path,
        forbidden_semantic_inputs=tuple(str(value) for value in forbidden),
    )


def _similarity(text: str, anchors: tuple[str, ...]) -> float:
    key = retrieval_key(text)
    return max((ratio(key, anchor) / 100 for anchor in anchors), default=0.0)


def _select_line(
    lines: tuple[_Line, ...],
    anchors: tuple[str, ...],
    *,
    minimum_y: float,
    maximum_y: float,
    threshold: float,
    excluded: set[int] | None = None,
) -> _Line:
    excluded = excluded or set()
    score, line = max(
        (
            (_similarity(candidate.text, anchors), candidate)
            for candidate in lines
            if minimum_y < candidate.y_center < maximum_y
            and candidate.index not in excluded
            and not _numeric_only(candidate.text)
        ),
        key=lambda item: (item[0], -item[1].y_center),
        default=(0.0, None),
    )
    if score < threshold or line is None:
        raise TMNoteWordBoxError(f"TM page-41 line anchor is unresolved: {anchors}")
    return line


def _select_group(
    lines: tuple[_Line, ...],
    anchors: tuple[str, ...],
    *,
    minimum_y: float,
    maximum_y: float,
    line_height: float,
    threshold: float,
) -> tuple[_Line, ...]:
    candidates = [
        line
        for line in lines
        if minimum_y < line.y_center < maximum_y and not _numeric_only(line.text)
    ]
    proposals: list[tuple[float, tuple[_Line, ...]]] = []
    for line in candidates:
        proposals.append((_similarity(line.text, anchors), (line,)))
        for other in candidates:
            if (
                line.index != other.index
                and 0 < other.y_center - line.y_center <= line_height * 1.3
                and abs(other.bbox.x0 - line.bbox.x0) <= line_height * 1.5
            ):
                group = (line, other)
                proposals.append(
                    (_similarity(" ".join(item.text for item in group), anchors), group)
                )
    score, group = max(
        proposals,
        key=lambda item: (item[0], len(item[1]), -item[1][0].y_center),
        default=(0.0, ()),
    )
    if score < threshold or not group:
        raise TMNoteWordBoxError(f"TM page-41 group anchor is unresolved: {anchors}")
    return group


def _source_role(row_key: str) -> str:
    if row_key.endswith("OPENING"):
        return "OPENING_BALANCE"
    if row_key.endswith("CLOSING"):
        return "CLOSING_BALANCE"
    if row_key.startswith("NET_"):
        return "NET_BOOK_VALUE_VALIDATION"
    return "MOVEMENT_AGGREGATE"


def _structural_row(
    *,
    policy: TMPage41Policy,
    panel_key: str,
    section_key: str,
    ordinal: int,
    line: _Line,
) -> TMPage41LogicalRow:
    return TMPage41LogicalRow(
        row_id=(f"{policy.page_tag}:{panel_key.lower()}:{section_key.lower()}:row-{ordinal:04d}"),
        panel_key=panel_key,
        section_key=section_key,
        row_key=f"{section_key}_SECTION",
        ordinal=ordinal,
        row=ReaderRow(
            source_row_ids=_source_ids(policy.page_tag, [line]),
            label=normalize_text(line.text),
            note_reference="12",
            cells=tuple(parse_financial_number(None) for _axis in range(3)),
        ),
        row_kind=TMNoteRowKind.LABEL_ONLY,
        source_role="SECTION_TITLE",
        y_anchor=line.y_center,
        label_bbox=line.bbox,
        value_bboxes=(None, None, None),
        label_line_indices=(line.index,),
        value_line_indices=((), (), ()),
        visual_cell_evidence=(None, None, None),
        mapping_approved=False,
    )


def _panel(
    lines: tuple[_Line, ...],
    spec: TMPage41PanelSpec,
    intro: _Line,
    next_intro: _Line | None,
    policy: TMPage41Policy,
    line_height: float,
    source_image: Any,
    source_image_path: Path,
    source_bbox: BoundingBox,
    *,
    ordinal: int,
) -> tuple[TMPage41Panel, tuple[int, ...]]:
    panel_end = (
        next_intro.y_center
        if next_intro is not None
        else source_bbox.y1 * policy.page_footer_top_ratio
    )
    section_lines = []
    minimum_section_y = intro.y_center
    for section in spec.sections:
        selected = _select_line(
            lines,
            section.title_anchors,
            minimum_y=minimum_section_y,
            maximum_y=panel_end,
            threshold=policy.minimum_anchor_similarity,
        )
        section_lines.append(selected)
        minimum_section_y = selected.y_center + 1
    first_section_y = section_lines[0].y_center
    numeric = [
        line
        for line in lines
        if intro.y_center < line.y_center < panel_end and _numeric_only(line.text)
    ]
    by_right = sorted(numeric, key=lambda line: line.x_right)
    clusters: list[list[_Line]] = []
    for line in by_right:
        if (
            not clusters
            or line.x_right - statistics.fmean(item.x_right for item in clusters[-1])
            > line_height * 2.5
        ):
            clusters.append([line])
        else:
            clusters[-1].append(line)
    if len(clusters) != 3 or tuple(len(cluster) for cluster in clusters) != (
        spec.expected_axis_numeric_counts
    ):
        raise TMNoteWordBoxError(
            f"TM page-41 numeric axis clusters drifted: {spec.panel_key} "
            f"{[len(cluster) for cluster in clusters]}"
        )
    axis_right_edges = tuple(
        float(statistics.median(line.x_right for line in cluster)) for cluster in clusters
    )
    axis_gap = statistics.median(
        axis_right_edges[index + 1] - axis_right_edges[index] for index in range(2)
    )
    header_groups = tuple(
        _select_group(
            lines,
            axis_spec.anchors,
            minimum_y=intro.y_center,
            maximum_y=first_section_y,
            line_height=line_height,
            threshold=policy.minimum_anchor_similarity,
        )
        for axis_spec in policy.axes
    )
    unit_lines = sorted(
        (
            line
            for line in lines
            if intro.y_center < line.y_center < first_section_y
            and _similarity(line.text, policy.unit_anchors) >= policy.minimum_anchor_similarity
        ),
        key=lambda line: line.x_right,
    )
    if len(unit_lines) != 3:
        raise TMNoteWordBoxError(f"TM page-41 unit denominator drifted: {spec.panel_key}")
    axes = tuple(
        TMPage41AxisBinding(
            ordinal=index,
            axis_id=f"{spec.panel_key.lower()}-axis-{index}",
            axis_right_edge=right_edge,
            raw_header_text=normalize_text(
                " ".join([*(line.text for line in header_group), unit_line.text])
            ),
            header_line_indices=tuple([*(line.index for line in header_group), unit_line.index]),
            semantic_role=axis_spec.role,
            canonical_unit=policy.canonical_unit,
            unit_multiplier=policy.unit_multiplier,
            period_start=spec.period_start,
            period_end=spec.period_end,
            period_type="DURATION_PANEL",
            header_bbox=_union([*header_group, unit_line]),
            evidence=(
                "visible asset-class column header",
                "visible page-41 unit line",
                "duration bound from visible panel introduction",
                "axis right edge inferred from source numeric geometry",
            ),
        )
        for index, (axis_spec, header_group, unit_line, right_edge) in enumerate(
            zip(policy.axes, header_groups, unit_lines, axis_right_edges, strict=True), start=1
        )
    )
    used_numeric: set[int] = set()
    used_labels: set[int] = {line.index for line in section_lines}
    rows = []
    row_ordinal = 0
    for section_index, (section_spec, section_line) in enumerate(
        zip(spec.sections, section_lines, strict=True)
    ):
        section_end = (
            section_lines[section_index + 1].y_center
            if section_index + 1 < len(section_lines)
            else panel_end
        )
        row_ordinal += 1
        rows.append(
            _structural_row(
                policy=policy,
                panel_key=spec.panel_key,
                section_key=section_spec.section_key,
                ordinal=row_ordinal,
                line=section_line,
            )
        )
        minimum_row_y = section_line.y_center
        for row_spec in section_spec.rows:
            label = _select_line(
                lines,
                row_spec.label_anchors,
                minimum_y=minimum_row_y,
                maximum_y=section_end,
                threshold=policy.minimum_anchor_similarity,
                excluded=used_labels,
            )
            used_labels.add(label.index)
            minimum_row_y = label.y_center + 1
            nearby = [
                line
                for line in numeric
                if line.index not in used_numeric
                and abs(line.y_center - label.y_center) <= line_height * 0.75
            ]
            per_axis: list[list[_Line]] = [[] for _axis in axes]
            for line in nearby:
                distances = [abs(line.x_right - axis.axis_right_edge) for axis in axes]
                closest = min(range(len(axes)), key=distances.__getitem__)
                if distances[closest] <= axis_gap * 0.35:
                    per_axis[closest].append(line)
                    used_numeric.add(line.index)
            if any(len(group) > 1 for group in per_axis):
                raise TMNoteWordBoxError(
                    f"TM page-41 cell has multiple numeric OCR lines: {spec.panel_key} "
                    f"{row_spec.row_key}"
                )
            numeric_centers = [line.y_center for group in per_axis for line in group]
            row_center = statistics.fmean(numeric_centers) if numeric_centers else label.y_center
            cells = []
            value_bboxes = []
            visual = []
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
                            f"TM page-41 missing cell lacks dash pixel evidence: "
                            f"{spec.panel_key} {row_spec.row_key} {axis.semantic_role}"
                        )
                visual.append(evidence)
                cells.append(parse_financial_number("-" if evidence is not None else group[0].text))
                value_bboxes.append(
                    BoundingBox(*evidence.component_box) if evidence is not None else group[0].bbox
                )
            observations = tuple(cell.observation.value for cell in cells)
            if observations != row_spec.expected_observations:
                raise TMNoteWordBoxError(
                    f"TM page-41 observation pattern drifted: {spec.panel_key} "
                    f"{row_spec.row_key} {observations}"
                )
            row_ordinal += 1
            source_lines = [label, *(line for group in per_axis for line in group)]
            rows.append(
                TMPage41LogicalRow(
                    row_id=(
                        f"{policy.page_tag}:{spec.panel_key.lower()}:"
                        f"{section_spec.section_key.lower()}:row-{row_ordinal:04d}"
                    ),
                    panel_key=spec.panel_key,
                    section_key=section_spec.section_key,
                    row_key=row_spec.row_key,
                    ordinal=row_ordinal,
                    row=ReaderRow(
                        source_row_ids=_source_ids(policy.page_tag, source_lines),
                        label=normalize_text(label.text),
                        note_reference="12",
                        cells=tuple(cells),
                    ),
                    row_kind=TMNoteRowKind.NUMERIC,
                    source_role=_source_role(row_spec.row_key),
                    y_anchor=row_center,
                    label_bbox=label.bbox,
                    value_bboxes=tuple(value_bboxes),
                    label_line_indices=(label.index,),
                    value_line_indices=tuple(
                        tuple(line.index for line in group) for group in per_axis
                    ),
                    visual_cell_evidence=tuple(visual),
                    mapping_approved=False,
                )
            )
    unassigned = tuple(sorted(line.index for line in numeric if line.index not in used_numeric))
    used_indices = {
        int(source_id.rsplit("-", 1)[-1]) for row in rows for source_id in row.row.source_row_ids
    }
    panel_lines = [intro, *unit_lines, *(line for group in header_groups for line in group)]
    panel_lines.extend(line for line in lines if line.index in used_indices)
    return (
        TMPage41Panel(
            ordinal=ordinal,
            panel_key=spec.panel_key,
            period_intro=normalize_text(intro.text),
            period_intro_line_indices=(intro.index,),
            period_start=spec.period_start,
            period_end=spec.period_end,
            axes=axes,
            rows=tuple(rows),
            bbox=_union(panel_lines),
        ),
        unassigned,
    )


def parse_tm_page41(
    result_path: Path,
    source_image_path: Path,
    policy: TMPage41Policy,
    *,
    page_tag: str = "page-0041",
) -> ParsedTMPage41:
    """Reconstruct both visible page-41 duration panels without mapping authority."""

    if page_tag != policy.page_tag:
        raise TMNoteWordBoxError("TM page-41 page tag drifted")
    if sha256_file(result_path) != policy.source_ocr_sha256:
        raise TMNoteWordBoxError("TM page-41 OCR artifact hash drifted")
    if sha256_file(source_image_path) != policy.source_render_sha256:
        raise TMNoteWordBoxError("TM page-41 source render hash drifted")
    source_image = cv2.imread(str(source_image_path), cv2.IMREAD_GRAYSCALE)
    if source_image is None:
        raise TMNoteWordBoxError("TM page-41 source render cannot be decoded")
    input_path, lines, _metadata = _load_lines(result_path, policy.minimum_line_score)
    line_height = float(statistics.median(line.height for line in lines))
    if line_height <= 0:
        raise TMNoteWordBoxError("TM page-41 line height is invalid")
    source_bbox = _union(lines)
    title = _select_line(
        lines,
        policy.note_title_anchors,
        minimum_y=0,
        maximum_y=300,
        threshold=policy.minimum_anchor_similarity,
    )
    title_number = [
        line
        for line in lines
        if line.y_center < 300
        and line.x_right < title.bbox.x0
        and abs(line.y_center - title.y_center) <= line_height
    ]
    title_group = tuple([*title_number, title])
    intros = tuple(
        _select_line(
            lines,
            spec.period_intro_anchors,
            minimum_y=title.y_center,
            maximum_y=source_bbox.y1 * policy.page_footer_top_ratio,
            threshold=policy.minimum_anchor_similarity,
        )
        for spec in policy.panels
    )
    if not intros[0].y_center < intros[1].y_center:
        raise TMNoteWordBoxError("TM page-41 panel order drifted")
    panels = []
    unassigned = []
    for index, (spec, intro) in enumerate(zip(policy.panels, intros, strict=True)):
        next_intro = intros[index + 1] if index + 1 < len(intros) else None
        panel, panel_unassigned = _panel(
            lines,
            spec,
            intro,
            next_intro,
            policy,
            line_height,
            source_image,
            source_image_path,
            source_bbox,
            ordinal=index + 1,
        )
        panels.append(panel)
        unassigned.extend(panel_unassigned)
    panel_tuple = tuple(panels)
    rows = tuple(row for panel in panel_tuple for row in panel.rows)
    footer = tuple(
        sorted(
            line.index
            for line in lines
            if line.y_center >= source_bbox.y1 * policy.page_footer_top_ratio
            and _numeric_only(line.text)
        )
    )
    result = ParsedTMPage41(
        input_path=input_path,
        source_sha256=policy.source_ocr_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_pdf_sha256=policy.source_pdf_sha256,
        page_tag=policy.page_tag,
        scope=policy.scope,
        scope_binding=policy.scope_binding,
        note_title=normalize_text(" ".join(line.text for line in title_group)),
        note_title_line_indices=tuple(line.index for line in title_group),
        panels=panel_tuple,
        rows=rows,
        line_height=line_height,
        source_ocr_bbox=source_bbox,
        table_bbox=BoundingBox(
            min(panel.bbox.x0 for panel in panel_tuple),
            min(panel.bbox.y0 for panel in panel_tuple),
            max(panel.bbox.x1 for panel in panel_tuple),
            max(panel.bbox.y1 for panel in panel_tuple),
        ),
        unassigned_numeric_line_indices=tuple(sorted(unassigned)),
        excluded_footer_numeric_line_indices=footer,
        mapping_authority=False,
        evidence=(
            "two visible duration panels reconstructed independently from one immutable page",
            "three visible asset-class axes with TOTAL retained as the only schema-value axis",
            "51 finite values reconstructed from PP-OCRv6 word-box geometry",
            "six OCR-missing dash cells accepted only from constrained render pixels",
            "this parser grants no ReportNormId authority",
        ),
    )
    if (
        len(result.panels) != 2
        or [len(panel.rows) for panel in result.panels] != [12, 13]
        or len(result.rows) != 25
        or result.numeric_row_count != 19
        or result.label_only_row_count != 6
        or result.financial_slot_count != 57
        or result.observation_count(ObservationKind.VALUE) != 51
        or result.observation_count(ObservationKind.DASH) != 6
        or result.unassigned_numeric_line_indices
    ):
        raise TMNoteWordBoxError("TM page-41 page denominator drifted")
    return result


__all__ = [
    "ParsedTMPage41",
    "TMPage41AxisBinding",
    "TMPage41LogicalRow",
    "TMPage41Panel",
    "TMPage41Policy",
    "load_tm_page41_policy",
    "parse_tm_page41",
]
