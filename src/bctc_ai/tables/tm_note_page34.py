"""Fixed-source reconstruction of MBB Note 6 provision movements on PDF page 34."""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from datetime import date
from functools import cache
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
    _clusters,
    _Line,
    _load_lines,
    _numeric_only,
    _source_ids,
    _union,
)
from bctc_ai.validation.reader_agreement import ReaderRow

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GEOGRAPHY_ROLES = ("DOMESTIC", "FOREIGN", "OVERALL")
_MEASURE_ROLES = ("SPECIFIC", "GENERAL", "COMBINED")
_AXIS_ROLES = tuple(
    f"{geography}_{measure}" for geography in _GEOGRAPHY_ROLES for measure in _MEASURE_ROLES
)
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
class TMPage34HeaderSpec:
    role: str
    anchors: tuple[str, ...]


@dataclass(frozen=True)
class TMPage34RowSpec:
    row_role: str
    label_anchors: tuple[str, ...]
    period_role: str
    expected_observations: tuple[str, ...]


@dataclass(frozen=True)
class TMPage34PanelSpec:
    panel_key: str
    period_role: str
    introduction_anchors: tuple[str, ...]
    expected_period_start: date
    expected_period_end: date
    expected_opening_date: date
    expected_numeric_rows: int
    expected_value_count: int
    expected_dash_count: int
    rows: tuple[TMPage34RowSpec, ...]


@dataclass(frozen=True)
class TMPage34Policy:
    source_path: Path
    document: str
    page_number: int
    page_tag: str
    note_number: str
    scope: str
    scope_binding: str
    source_pdf_sha256: str
    source_render_sha256: str
    source_ocr_sha256: str
    minimum_line_score: float
    minimum_anchor_similarity: float
    minimum_unit_similarity: float
    note_title_anchors: tuple[str, ...]
    unit_anchors: tuple[str, ...]
    canonical_unit: str
    unit_multiplier: int
    minimum_axis_separation_line_heights: float
    numeric_axis_max_center_distance_ratio: float
    numeric_row_cluster_line_heights: float
    dash_ocr_max_width_line_heights: float
    dash_ocr_max_height_line_heights: float
    page_footer_top_ratio: float
    dash_config: dict[str, float | int]
    dash_config_path: Path
    geography_headers: tuple[TMPage34HeaderSpec, ...]
    measure_headers: tuple[TMPage34HeaderSpec, ...]
    panels: tuple[TMPage34PanelSpec, ...]
    forbidden_semantic_inputs: tuple[str, ...]


@dataclass(frozen=True)
class TMPage34AxisBinding:
    ordinal: int
    axis_role: str
    geography_role: str
    measure_role: str
    raw_geography_text: str
    raw_measure_text: str
    geography_line_indices: tuple[int, ...]
    measure_line_indices: tuple[int, ...]
    axis_center: float
    axis_right_edge: float
    raw_unit_text: str
    unit_line_index: int
    canonical_unit: str
    unit_multiplier: int
    header_bbox: BoundingBox
    unit_bbox: BoundingBox
    mapping_axis_authority: bool
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class TMPage34LogicalRow:
    row_id: str
    panel_key: str
    ordinal: int
    row_role: str
    row: ReaderRow
    row_kind: TMNoteRowKind
    source_role: str
    y_anchor: float
    label_bbox: BoundingBox
    value_bboxes: tuple[BoundingBox | None, ...]
    raw_ocr_value_bboxes: tuple[tuple[BoundingBox, ...], ...]
    label_line_indices: tuple[int, ...]
    value_line_indices: tuple[tuple[int, ...], ...]
    cell_raw_ocr_texts: tuple[tuple[str, ...], ...]
    visual_cell_evidence: tuple[VisualCellEvidence | None, ...]
    cell_axis_roles: tuple[str, ...]
    period_start: date
    period_end: date
    period_type: str
    period_role: str
    mapping_approved: bool

    @property
    def financial_slot_count(self) -> int:
        return len(self.row.cells)


@dataclass(frozen=True)
class TMPage34Panel:
    panel_key: str
    period_role: str
    period_start: date
    period_end: date
    opening_date: date
    introduction_text: str
    introduction_line_indices: tuple[int, ...]
    unit_text: str
    unit_line_index: int
    axes: tuple[TMPage34AxisBinding, ...]
    rows: tuple[TMPage34LogicalRow, ...]
    bbox: BoundingBox
    ocr_misread_dash_line_indices: tuple[int, ...]
    unassigned_numeric_line_indices: tuple[int, ...]

    @property
    def financial_slot_count(self) -> int:
        return sum(row.financial_slot_count for row in self.rows)

    def observation_count(self, observation: ObservationKind) -> int:
        return sum(cell.observation is observation for row in self.rows for cell in row.row.cells)


@dataclass(frozen=True)
class ParsedTMPage34:
    input_path: str
    source_sha256: str
    source_render_sha256: str
    source_pdf_sha256: str
    page_number: int
    page_tag: str
    note_number: str
    scope: str
    scope_binding: str
    note_title_text: str
    note_title_line_indices: tuple[int, ...]
    note_title_bbox: BoundingBox
    panels: tuple[TMPage34Panel, ...]
    rows: tuple[TMPage34LogicalRow, ...]
    line_height: float
    source_ocr_bbox: BoundingBox
    table_bbox: BoundingBox
    excluded_footer_numeric_line_indices: tuple[int, ...]
    mapping_authority: bool
    evidence: tuple[str, ...]

    @property
    def numeric_row_count(self) -> int:
        return len(self.rows)

    @property
    def financial_slot_count(self) -> int:
        return sum(panel.financial_slot_count for panel in self.panels)

    def observation_count(self, observation: ObservationKind) -> int:
        return sum(panel.observation_count(observation) for panel in self.panels)


def _anchors(payload: Any, field: str) -> tuple[str, ...]:
    if not isinstance(payload, list) or not payload:
        raise TMNoteWordBoxError(f"TM page34 {field} anchors are invalid")
    result = tuple(retrieval_key(str(value)) for value in payload)
    if any(not value for value in result):
        raise TMNoteWordBoxError(f"TM page34 {field} contains an empty anchor")
    return result


def _positive(payload: dict[str, Any], field: str) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise TMNoteWordBoxError(f"invalid positive TM page34 setting: {field}")
    return float(value)


def _positive_int(payload: dict[str, Any], field: str) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise TMNoteWordBoxError(f"invalid positive TM page34 denominator: {field}")
    return value


def _iso_date(payload: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(payload))
    except ValueError as exc:
        raise TMNoteWordBoxError(f"invalid TM page34 date: {field}") from exc


def load_tm_page34_policy(path: Path) -> TMPage34Policy:
    """Load the hash-bound, source-visible Note 6 reconstruction policy."""

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise TMNoteWordBoxError(f"cannot load TM page34 policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "TM_NOTE_PAGE34_PROVISION_MOVEMENT_V1"
        or payload.get("statement_type") != "TM"
        or payload.get("page_number") != 34
        or payload.get("page_tag") != "page-0034"
        or payload.get("note_number") != "6"
        or payload.get("scope") != "CONSOLIDATED"
    ):
        raise TMNoteWordBoxError("TM page34 policy identity drifted")
    hashes = (
        payload.get("source_pdf_sha256"),
        payload.get("source_render_sha256"),
        payload.get("source_ocr_sha256"),
    )
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in hashes):
        raise TMNoteWordBoxError("TM page34 source hashes are invalid")
    thresholds = (
        payload.get("minimum_line_score"),
        payload.get("minimum_anchor_similarity"),
        payload.get("minimum_unit_similarity"),
    )
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1
        for value in thresholds
    ):
        raise TMNoteWordBoxError("TM page34 similarity thresholds are invalid")
    unit = payload.get("unit")
    geometry = payload.get("geometry")
    if not isinstance(unit, dict) or not isinstance(geometry, dict):
        raise TMNoteWordBoxError("TM page34 unit/geometry policy is incomplete")
    canonical = unit.get("canonical")
    multiplier = unit.get("multiplier")
    if (
        not isinstance(canonical, str)
        or not canonical
        or isinstance(multiplier, bool)
        or not isinstance(multiplier, int)
        or multiplier <= 0
    ):
        raise TMNoteWordBoxError("TM page34 unit binding is invalid")
    footer_ratio = _positive(geometry, "page_footer_top_ratio")
    if footer_ratio >= 1:
        raise TMNoteWordBoxError("TM page34 footer ratio must be below one")
    dash_name = payload.get("dash_detector_config")
    if not isinstance(dash_name, str) or Path(dash_name).name != dash_name:
        raise TMNoteWordBoxError("TM page34 dash detector path is invalid")
    dash_path = (path.parent / dash_name).resolve()
    if not dash_path.is_file() or sha256_file(dash_path) != payload.get(
        "dash_detector_config_sha256"
    ):
        raise TMNoteWordBoxError("TM page34 dash detector is absent or drifted")
    dash_config = load_word_box_reconstruction_v3_config(dash_path).base.base

    def header_specs(field: str, role_field: str, expected: tuple[str, ...]):
        raw = payload.get(field)
        if not isinstance(raw, list) or len(raw) != 3:
            raise TMNoteWordBoxError(f"TM page34 {field} is incomplete")
        result = tuple(
            TMPage34HeaderSpec(
                role=str(record.get(role_field, "")),
                anchors=_anchors(record.get("anchors"), f"{field} header"),
            )
            for record in raw
            if isinstance(record, dict)
        )
        if len(result) != 3 or tuple(item.role for item in result) != expected:
            raise TMNoteWordBoxError(f"TM page34 {field} roles drifted")
        return result

    geography = header_specs("geography_headers", "geography_role", _GEOGRAPHY_ROLES)
    measures = header_specs("measure_headers", "measure_role", _MEASURE_ROLES)
    raw_panels = payload.get("panels")
    if not isinstance(raw_panels, list) or len(raw_panels) != 2:
        raise TMNoteWordBoxError("TM page34 must define two visible panels")
    panels = []
    valid_observations = {ObservationKind.VALUE.value, ObservationKind.DASH.value}
    for record in raw_panels:
        if not isinstance(record, dict):
            raise TMNoteWordBoxError("TM page34 panel record is invalid")
        raw_rows = record.get("rows")
        if not isinstance(raw_rows, list) or not raw_rows:
            raise TMNoteWordBoxError("TM page34 panel has no row contract")
        rows = []
        for raw_row in raw_rows:
            if not isinstance(raw_row, dict) or not isinstance(raw_row.get("row_role"), str):
                raise TMNoteWordBoxError("TM page34 row record is invalid")
            observations = raw_row.get("expected_observations")
            if (
                not isinstance(observations, list)
                or len(observations) != 9
                or any(value not in valid_observations for value in observations)
                or raw_row.get("period_role") not in _PERIOD_ROLES
            ):
                raise TMNoteWordBoxError("TM page34 row observation/period contract drifted")
            rows.append(
                TMPage34RowSpec(
                    row_role=raw_row["row_role"],
                    label_anchors=_anchors(
                        raw_row.get("label_anchors"), f"row {raw_row['row_role']}"
                    ),
                    period_role=raw_row["period_role"],
                    expected_observations=tuple(str(value) for value in observations),
                )
            )
        panels.append(
            TMPage34PanelSpec(
                panel_key=str(record.get("panel_key", "")),
                period_role=str(record.get("period_role", "")),
                introduction_anchors=_anchors(
                    record.get("introduction_anchors"), "panel introduction"
                ),
                expected_period_start=_iso_date(record.get("expected_period_start"), "start"),
                expected_period_end=_iso_date(record.get("expected_period_end"), "end"),
                expected_opening_date=_iso_date(record.get("expected_opening_date"), "opening"),
                expected_numeric_rows=_positive_int(record, "expected_numeric_rows"),
                expected_value_count=_positive_int(record, "expected_value_count"),
                expected_dash_count=_positive_int(record, "expected_dash_count"),
                rows=tuple(rows),
            )
        )
    if (
        tuple((panel.panel_key, panel.period_role) for panel in panels)
        != (("Q1_2026", "CURRENT"), ("FY_2025", "COMPARATIVE"))
        or tuple(panel.expected_numeric_rows for panel in panels) != (5, 6)
        or tuple(panel.expected_value_count for panel in panels) != (37, 43)
        or tuple(panel.expected_dash_count for panel in panels) != (8, 11)
        or any(len(panel.rows) != panel.expected_numeric_rows for panel in panels)
    ):
        raise TMNoteWordBoxError("TM page34 panel denominators drifted")
    forbidden = payload.get("forbidden_semantic_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise TMNoteWordBoxError("TM page34 forbidden semantic inputs drifted")
    return TMPage34Policy(
        source_path=path,
        document=str(payload.get("document", "")),
        page_number=34,
        page_tag="page-0034",
        note_number="6",
        scope="CONSOLIDATED",
        scope_binding=str(payload.get("scope_binding", "")),
        source_pdf_sha256=hashes[0],
        source_render_sha256=hashes[1],
        source_ocr_sha256=hashes[2],
        minimum_line_score=float(thresholds[0]),
        minimum_anchor_similarity=float(thresholds[1]),
        minimum_unit_similarity=float(thresholds[2]),
        note_title_anchors=_anchors(payload.get("note_title_anchors"), "note title"),
        unit_anchors=_anchors(unit.get("anchors"), "unit"),
        canonical_unit=canonical,
        unit_multiplier=multiplier,
        minimum_axis_separation_line_heights=_positive(
            geometry, "minimum_axis_separation_line_heights"
        ),
        numeric_axis_max_center_distance_ratio=_positive(
            geometry, "numeric_axis_max_center_distance_ratio"
        ),
        numeric_row_cluster_line_heights=_positive(geometry, "numeric_row_cluster_line_heights"),
        dash_ocr_max_width_line_heights=_positive(geometry, "dash_ocr_max_width_line_heights"),
        dash_ocr_max_height_line_heights=_positive(geometry, "dash_ocr_max_height_line_heights"),
        page_footer_top_ratio=footer_ratio,
        dash_config={str(key): value for key, value in dash_config.items()},
        dash_config_path=dash_path,
        geography_headers=geography,
        measure_headers=measures,
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
    scored = sorted(
        (
            (_best_anchor_similarity(line.text, anchors), line)
            for line in lines
            if lower_y < line.y_center < upper_y and line.bbox.x1 < maximum_x
        ),
        key=lambda item: (item[0], -item[1].y_center),
        reverse=True,
    )
    if not scored or scored[0][0] < minimum:
        raise TMNoteWordBoxError(f"TM page34 visible anchor is absent: {anchors}")
    return scored[0][1]


def _label_windows(
    labels: tuple[_Line, ...],
    rows: tuple[TMPage34RowSpec, ...],
    minimum_similarity: float,
) -> tuple[tuple[_Line, ...], ...]:
    @cache
    def solve(label_index: int, row_index: int):
        if row_index == len(rows):
            return (0.0, ()) if label_index == len(labels) else None
        remaining_rows = len(rows) - row_index - 1
        best = None
        for width in range(1, 4):
            end = label_index + width
            remaining_labels = len(labels) - end
            if end > len(labels) or not remaining_rows <= remaining_labels <= remaining_rows * 3:
                continue
            window = labels[label_index:end]
            similarity = _best_anchor_similarity(
                " ".join(line.text for line in window), rows[row_index].label_anchors
            )
            if similarity < minimum_similarity:
                continue
            tail = solve(end, row_index + 1)
            if tail is None:
                continue
            proposal = (similarity + tail[0], (window, *tail[1]))
            if best is None or proposal[0] > best[0]:
                best = proposal
        return best

    result = solve(0, 0)
    if result is None:
        raise TMNoteWordBoxError("TM page34 visible wrapped row labels cannot be partitioned")
    return tuple(tuple(window) for window in result[1])


def _row_period(panel: TMPage34PanelSpec, role: str) -> tuple[date, date, str]:
    if role == "OPENING_SNAPSHOT":
        return panel.expected_opening_date, panel.expected_opening_date, "SNAPSHOT"
    if role == "CLOSING_SNAPSHOT":
        return panel.expected_period_end, panel.expected_period_end, "SNAPSHOT"
    if role == "MOVEMENT_DURATION":
        return panel.expected_period_start, panel.expected_period_end, "DURATION"
    raise TMNoteWordBoxError(f"unsupported TM page34 period role: {role}")


@dataclass(frozen=True)
class _HeaderAxis:
    geography_role: str
    measure_role: str
    geography_line: _Line
    measure_line: _Line
    header_lines: tuple[_Line, ...]
    center: float


def _bind_header_axes(
    lines: tuple[_Line, ...],
    intro: _Line,
    first_row: _Line,
    policy: TMPage34Policy,
    line_height: float,
) -> tuple[tuple[_HeaderAxis, ...], _Line]:
    header_lines = tuple(
        line for line in lines if intro.y_center < line.y_center < first_row.y_center
    )
    units = tuple(
        line
        for line in header_lines
        if _best_anchor_similarity(line.text, policy.unit_anchors) >= policy.minimum_unit_similarity
    )
    if len(units) != 1:
        raise TMNoteWordBoxError("TM page34 panel must expose one visible unit label")
    geography_lines = []
    geography_upper = intro.y_center + line_height * 3.2
    for spec in policy.geography_headers:
        geography_lines.append(
            _best_line(
                header_lines,
                spec.anchors,
                policy.minimum_anchor_similarity,
                lower_y=intro.y_center,
                upper_y=geography_upper,
            )
        )
    if len({line.index for line in geography_lines}) != 3:
        raise TMNoteWordBoxError("TM page34 geography header lines are not unique")
    geography_lines = sorted(geography_lines, key=lambda line: line.x_center)
    measure_lower = max(line.y_center for line in geography_lines) + line_height * 0.35
    measure_candidates = []
    for line in header_lines:
        if not measure_lower < line.y_center < first_row.y_center:
            continue
        scores = [
            _best_anchor_similarity(line.text, spec.anchors) for spec in policy.measure_headers
        ]
        best = max(range(len(scores)), key=scores.__getitem__)
        if scores[best] >= policy.minimum_anchor_similarity:
            measure_candidates.append((line, policy.measure_headers[best].role))
    measure_candidates.sort(key=lambda item: item[0].x_center)
    expected_roles = _MEASURE_ROLES * 3
    if (
        len(measure_candidates) != 9
        or tuple(role for _line, role in measure_candidates) != expected_roles
    ):
        raise TMNoteWordBoxError("TM page34 nine visible measure headers are incomplete")
    centers = [line.x_center for line, _role in measure_candidates]
    gaps = [right - left for left, right in zip(centers, centers[1:], strict=False)]
    if min(gaps) < line_height * policy.minimum_axis_separation_line_heights:
        raise TMNoteWordBoxError("TM page34 nine value axes are not distinctly separated")
    typical_gap = statistics.median(gaps)
    result = []
    for index, (measure_line, measure_role) in enumerate(measure_candidates):
        geography_index = index // 3
        geography_line = geography_lines[geography_index]
        upper_components = tuple(
            line
            for line in header_lines
            if line.index not in {measure_line.index, units[0].index}
            and abs(line.x_center - measure_line.x_center) <= typical_gap * 0.45
            and line.y_center < measure_line.y_center
            and line.y_center > geography_line.y_center
        )
        result.append(
            _HeaderAxis(
                geography_role=policy.geography_headers[geography_index].role,
                measure_role=measure_role,
                geography_line=geography_line,
                measure_line=measure_line,
                header_lines=tuple(
                    sorted((*upper_components, measure_line), key=lambda line: line.y_center)
                ),
                center=measure_line.x_center,
            )
        )
    return tuple(result), units[0]


def _parse_panel(
    lines: tuple[_Line, ...],
    source_image: Any,
    source_image_path: Path,
    policy: TMPage34Policy,
    panel_spec: TMPage34PanelSpec,
    intro: _Line,
    upper_y: float,
    line_height: float,
) -> TMPage34Panel:
    first_row = _best_line(
        lines,
        panel_spec.rows[0].label_anchors,
        policy.minimum_anchor_similarity,
        lower_y=intro.y_center,
        upper_y=upper_y,
        maximum_x=700,
    )
    header_axes, unit_line = _bind_header_axes(lines, intro, first_row, policy, line_height)
    header_bottom = max(axis.measure_line.bbox.y1 for axis in header_axes)
    label_candidates = tuple(
        sorted(
            (
                line
                for line in lines
                if header_bottom < line.y_center < upper_y
                and line.bbox.x1 < 700
                and not _numeric_only(line.text)
            ),
            key=lambda line: (line.y_center, line.bbox.x0),
        )
    )
    label_windows = _label_windows(
        label_candidates, panel_spec.rows, policy.minimum_anchor_similarity
    )
    numeric_candidates = [
        line
        for line in lines
        if header_bottom < line.y_center < upper_y
        and line.bbox.x0 > 700
        and _numeric_only(line.text)
    ]
    numeric_groups = _clusters(
        numeric_candidates, line_height * policy.numeric_row_cluster_line_heights
    )
    if len(numeric_groups) != panel_spec.expected_numeric_rows:
        raise TMNoteWordBoxError("TM page34 numeric row group denominator drifted")
    centers = tuple(axis.center for axis in header_axes)
    typical_gap = statistics.median(
        right - left for left, right in zip(centers, centers[1:], strict=False)
    )
    assigned: dict[tuple[int, int], list[_Line]] = {}
    unassigned = []
    for row_index, group in enumerate(numeric_groups):
        for line in group:
            axis_index = min(
                range(len(centers)), key=lambda index: abs(line.x_center - centers[index])
            )
            if (
                abs(line.x_center - centers[axis_index])
                > typical_gap * policy.numeric_axis_max_center_distance_ratio
            ):
                unassigned.append(line)
            else:
                assigned.setdefault((row_index, axis_index), []).append(line)
    if unassigned or any(len(value) > 1 for value in assigned.values()):
        raise TMNoteWordBoxError("TM page34 contains unassigned or duplicate numeric boxes")
    axis_right_edges = tuple(
        statistics.median(
            line.x_right
            for (row_index, cell_index), cell_lines in assigned.items()
            if cell_index == axis_index
            for line in cell_lines
        )
        for axis_index in range(9)
    )
    axes = tuple(
        TMPage34AxisBinding(
            ordinal=index + 1,
            axis_role=f"{header.geography_role}_{header.measure_role}",
            geography_role=header.geography_role,
            measure_role=header.measure_role,
            raw_geography_text=header.geography_line.text,
            raw_measure_text=" ".join(line.text for line in header.header_lines),
            geography_line_indices=(header.geography_line.index,),
            measure_line_indices=tuple(line.index for line in header.header_lines),
            axis_center=header.center,
            axis_right_edge=axis_right_edges[index],
            raw_unit_text=unit_line.text,
            unit_line_index=unit_line.index,
            canonical_unit=policy.canonical_unit,
            unit_multiplier=policy.unit_multiplier,
            header_bbox=_union([header.geography_line, *header.header_lines, unit_line]),
            unit_bbox=unit_line.bbox,
            mapping_axis_authority=(
                header.geography_role == "OVERALL"
                and header.measure_role in {"SPECIFIC", "GENERAL"}
            ),
            evidence=(
                "geography and provision-measure roles matched from visible local headers",
                "numeric axis right edge estimated from repeated source-cell geometry only",
                "single panel-local visible unit binds VND million to all nine axes",
            ),
        )
        for index, header in enumerate(header_axes)
    )
    if tuple(axis.axis_role for axis in axes) != _AXIS_ROLES:
        raise TMNoteWordBoxError("TM page34 axis semantic order drifted")

    rows = []
    misread_dashes = []
    for row_index, (row_spec, labels, numeric_group) in enumerate(
        zip(panel_spec.rows, label_windows, numeric_groups, strict=True), start=1
    ):
        anchor_center = statistics.fmean(line.y_center for line in numeric_group)
        cells = []
        value_bboxes = []
        raw_ocr_bboxes = []
        value_line_indices = []
        cell_raw_texts = []
        visual = []
        source_lines = list(labels)
        for axis_index, expected in enumerate(row_spec.expected_observations):
            cell_lines = assigned.get((row_index - 1, axis_index), [])
            raw_ocr_bboxes.append(tuple(line.bbox for line in cell_lines))
            value_line_indices.append(tuple(line.index for line in cell_lines))
            cell_raw_texts.append(tuple(line.text for line in cell_lines))
            source_lines.extend(cell_lines)
            evidence = None
            if expected == ObservationKind.DASH.value:
                if len(cell_lines) == 1:
                    glyph = cell_lines[0]
                    if (
                        glyph.bbox.x1 - glyph.bbox.x0
                        > line_height * policy.dash_ocr_max_width_line_heights
                        or glyph.bbox.y1 - glyph.bbox.y0
                        > line_height * policy.dash_ocr_max_height_line_heights
                    ):
                        raise TMNoteWordBoxError(
                            "TM page34 expected DASH contains a non-dash-sized OCR glyph"
                        )
                    if parse_financial_number(glyph.text).observation is not ObservationKind.DASH:
                        misread_dashes.append(glyph.index)
                elif cell_lines:
                    raise TMNoteWordBoxError("TM page34 expected DASH contains multiple OCR glyphs")
                evidence = _detect_visible_dash_v3(
                    source_image,
                    source_image_path=source_image_path,
                    axis_right_edge=axes[axis_index].axis_right_edge,
                    anchor_center=anchor_center,
                    line_height=line_height,
                    config=policy.dash_config,
                )
                if evidence is None:
                    raise TMNoteWordBoxError(
                        "TM page34 OCR-missing DASH lacks constrained pixel evidence"
                    )
                cell = parse_financial_number("-")
                value_bbox = BoundingBox(*evidence.component_box)
            else:
                if len(cell_lines) != 1:
                    raise TMNoteWordBoxError("TM page34 VALUE cell lacks one OCR number")
                cell = parse_financial_number(cell_lines[0].text)
                if cell.observation is not ObservationKind.VALUE or cell.value is None:
                    raise TMNoteWordBoxError("TM page34 VALUE cell failed numeric parsing")
                value_bbox = cell_lines[0].bbox
            cells.append(cell)
            value_bboxes.append(value_bbox)
            visual.append(evidence)
        period_start, period_end, period_type = _row_period(panel_spec, row_spec.period_role)
        rows.append(
            TMPage34LogicalRow(
                row_id=f"{policy.page_tag}:{panel_spec.panel_key.casefold()}:row-{row_index:04d}",
                panel_key=panel_spec.panel_key,
                ordinal=row_index,
                row_role=row_spec.row_role,
                row=ReaderRow(
                    source_row_ids=_source_ids(policy.page_tag, source_lines),
                    label=" ".join(line.text for line in labels),
                    note_reference=None,
                    cells=tuple(cells),
                ),
                row_kind=TMNoteRowKind.NUMERIC,
                source_role=row_spec.row_role,
                y_anchor=anchor_center,
                label_bbox=_union(labels),
                value_bboxes=tuple(value_bboxes),
                raw_ocr_value_bboxes=tuple(raw_ocr_bboxes),
                label_line_indices=tuple(line.index for line in labels),
                value_line_indices=tuple(value_line_indices),
                cell_raw_ocr_texts=tuple(cell_raw_texts),
                visual_cell_evidence=tuple(visual),
                cell_axis_roles=_AXIS_ROLES,
                period_start=period_start,
                period_end=period_end,
                period_type=period_type,
                period_role=panel_spec.period_role,
                mapping_approved=False,
            )
        )
    panel = TMPage34Panel(
        panel_key=panel_spec.panel_key,
        period_role=panel_spec.period_role,
        period_start=panel_spec.expected_period_start,
        period_end=panel_spec.expected_period_end,
        opening_date=panel_spec.expected_opening_date,
        introduction_text=intro.text,
        introduction_line_indices=(intro.index,),
        unit_text=unit_line.text,
        unit_line_index=unit_line.index,
        axes=axes,
        rows=tuple(rows),
        bbox=BoundingBox(
            min(row.label_bbox.x0 for row in rows),
            min(axis.header_bbox.y0 for axis in axes),
            max(axis.axis_right_edge for axis in axes),
            max(bbox.y1 for row in rows for bbox in (row.label_bbox, *row.value_bboxes)),
        ),
        ocr_misread_dash_line_indices=tuple(sorted(misread_dashes)),
        unassigned_numeric_line_indices=(),
    )
    if (
        len(panel.rows) != panel_spec.expected_numeric_rows
        or panel.financial_slot_count != panel_spec.expected_numeric_rows * 9
        or panel.observation_count(ObservationKind.VALUE) != panel_spec.expected_value_count
        or panel.observation_count(ObservationKind.DASH) != panel_spec.expected_dash_count
    ):
        raise TMNoteWordBoxError(f"TM page34 {panel_spec.panel_key} denominator drifted")
    return panel


def parse_tm_page34(
    result_path: Path,
    source_image_path: Path,
    policy: TMPage34Policy,
    *,
    page_tag: str = "page-0034",
) -> ParsedTMPage34:
    """Reconstruct all 11 visible movement rows without granting mapping authority."""

    if page_tag != policy.page_tag:
        raise TMNoteWordBoxError("TM page34 page tag drifted")
    if sha256_file(result_path) != policy.source_ocr_sha256:
        raise TMNoteWordBoxError("TM page34 OCR artifact hash drifted")
    if sha256_file(source_image_path) != policy.source_render_sha256:
        raise TMNoteWordBoxError("TM page34 source render hash drifted")
    source_image = cv2.imread(str(source_image_path), cv2.IMREAD_GRAYSCALE)
    if source_image is None:
        raise TMNoteWordBoxError("TM page34 source render cannot be decoded")
    input_path, lines, _metadata = _load_lines(result_path, policy.minimum_line_score)
    line_height = float(statistics.median(line.height for line in lines))
    source_bbox = _union(lines)
    title = _best_line(
        lines,
        policy.note_title_anchors,
        policy.minimum_anchor_similarity,
        maximum_x=source_bbox.x1 * 0.55,
    )
    intros = []
    lower = title.y_center
    for panel in policy.panels:
        intro = _best_line(
            lines,
            panel.introduction_anchors,
            policy.minimum_anchor_similarity,
            lower_y=lower,
            maximum_x=source_bbox.x1 * 0.75,
        )
        intros.append(intro)
        lower = intro.y_center
    if parse_vietnamese_date(intros[0].text) != policy.panels[0].expected_period_end:
        raise TMNoteWordBoxError("TM page34 Q1 visible period date drifted")
    if "2025" not in retrieval_key(intros[1].text):
        raise TMNoteWordBoxError("TM page34 FY2025 visible duration drifted")
    footer_top = source_bbox.y1 * policy.page_footer_top_ratio
    panels = tuple(
        _parse_panel(
            lines,
            source_image,
            source_image_path,
            policy,
            panel_spec,
            intros[index],
            intros[index + 1].bbox.y0 if index + 1 < len(intros) else footer_top,
            line_height,
        )
        for index, panel_spec in enumerate(policy.panels)
    )
    rows = tuple(row for panel in panels for row in panel.rows)
    result = ParsedTMPage34(
        input_path=input_path,
        source_sha256=policy.source_ocr_sha256,
        source_render_sha256=policy.source_render_sha256,
        source_pdf_sha256=policy.source_pdf_sha256,
        page_number=34,
        page_tag=policy.page_tag,
        note_number=policy.note_number,
        scope=policy.scope,
        scope_binding=policy.scope_binding,
        note_title_text=title.text,
        note_title_line_indices=(title.index,),
        note_title_bbox=title.bbox,
        panels=panels,
        rows=rows,
        line_height=line_height,
        source_ocr_bbox=source_bbox,
        table_bbox=BoundingBox(
            min(panel.bbox.x0 for panel in panels),
            min(panel.bbox.y0 for panel in panels),
            max(panel.bbox.x1 for panel in panels),
            max(panel.bbox.y1 for panel in panels),
        ),
        excluded_footer_numeric_line_indices=tuple(
            sorted(
                line.index
                for line in lines
                if line.y_center >= footer_top and _numeric_only(line.text)
            )
        ),
        mapping_authority=False,
        evidence=(
            "two visible provision-movement panels bound from their dated introductions",
            "nine axes preserve domestic/foreign/overall by specific/general/combined dimensions",
            "11 logical rows reconstruct 99 status slots from PP-OCRv6 and render geometry",
            "80 values are parsed and 19 dashes retain constrained pixel evidence",
            "four thin dash glyphs misrecognized by OCR as numeric one remain traceable",
            "DASH remains semantically distinct from numeric zero",
            "this parser grants no ReportNormId authority",
        ),
    )
    if (
        len(result.rows) != 11
        or result.numeric_row_count != 11
        or result.financial_slot_count != 99
        or result.observation_count(ObservationKind.VALUE) != 80
        or result.observation_count(ObservationKind.DASH) != 19
        or tuple(
            line_index for panel in panels for line_index in panel.ocr_misread_dash_line_indices
        )
        != (57, 58, 116, 132)
    ):
        raise TMNoteWordBoxError("TM page34 combined source denominator drifted")
    return result


__all__ = [
    "ParsedTMPage34",
    "TMPage34AxisBinding",
    "TMPage34LogicalRow",
    "TMPage34Panel",
    "TMPage34Policy",
    "load_tm_page34_policy",
    "parse_tm_page34",
]
