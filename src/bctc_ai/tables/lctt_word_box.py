from __future__ import annotations

import itertools
import json
import re
import statistics
from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from rapidfuzz.fuzz import ratio

from bctc_ai.axes.header_binding import HeaderBinding
from bctc_ai.core.contracts import BoundingBox, ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import ParsedNumber, normalize_text, retrieval_key
from bctc_ai.evaluation.financial_cells_v2 import parse_financial_number_strict_grouping
from bctc_ai.evaluation.word_box_rows import VisualCellEvidence, _read_source_image
from bctc_ai.evaluation.word_box_rows_v3 import _detect_visible_dash_v3
from bctc_ai.mapping.lctt import CashFlowMethod
from bctc_ai.validation.reader_agreement import ReaderRow


class LCTTWordBoxError(RuntimeError):
    pass


@dataclass(frozen=True)
class LCTTUnitAnchor:
    text: str
    canonical: str
    multiplier: int

    @property
    def key(self) -> str:
        return retrieval_key(self.text)


@dataclass(frozen=True)
class LCTTWordBoxPolicy:
    source_path: Path
    minimum_line_score: float
    minimum_title_similarity: float
    minimum_header_similarity: float
    minimum_distinct_semantics_margin: float
    statement_title_anchors: tuple[str, ...]
    scope_anchors: dict[str, tuple[str, ...]]
    method_title_anchors: dict[str, tuple[str, ...]]
    method_form_anchors: dict[str, tuple[str, ...]]
    continuation_anchors: tuple[str, ...]
    unit_anchors: tuple[LCTTUnitAnchor, ...]
    maximum_range_to_unit_center_distance_line_heights: float
    maximum_start_to_end_center_distance_line_heights: float
    minimum_axis_separation_line_heights: float
    numeric_axis_max_distance_ratio: float
    numeric_axis_right_overrun_line_heights: float
    row_anchor_cluster_line_heights: float
    label_direct_attach_line_heights: float
    wrapped_label_gap_line_heights: float
    note_attach_line_heights: float
    label_boundary_axis_gap_ratio: float
    body_tail_line_heights: float
    dash_config: dict[str, float | int]
    dash_config_path: Path
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
class _PeriodRange:
    start_line: _Line
    end_line: _Line
    period_start: date
    period_end: date

    @property
    def x_center(self) -> float:
        return statistics.fmean((self.start_line.x_center, self.end_line.x_center))


@dataclass(frozen=True)
class LCTTAxisBinding:
    ordinal: int
    axis_id: str
    axis_right_edge: float
    raw_start_header: str
    start_header_line_index: int
    raw_end_header: str
    end_header_line_index: int
    current_or_comparative: str
    raw_unit_text: str
    unit_line_index: int
    canonical_unit: str
    unit_multiplier: int
    period_start: date
    period_end: date
    period_type: str
    duration_months: int
    header_bbox: BoundingBox
    unit_bbox: BoundingBox
    evidence: tuple[str, ...]

    @property
    def right_edge(self) -> float:
        """Compatibility alias for the sealed visible-dash detector."""

        return self.axis_right_edge

    @property
    def header_binding(self) -> HeaderBinding:
        return HeaderBinding(
            axis_id=self.axis_id,
            raw_header=normalize_text(f"{self.raw_start_header} | {self.raw_end_header}"),
            header_bbox=self.header_bbox,
            unit=self.canonical_unit,
            unit_multiplier=self.unit_multiplier,
            unit_bbox=self.unit_bbox,
            period_start=self.period_start,
            period_end=self.period_end,
            period_type=self.period_type,
            duration_months=self.duration_months,
            current_or_comparative=self.current_or_comparative,
            restated=False,
            confidence=1.0,
            evidence=self.evidence,
        )


@dataclass(frozen=True)
class LCTTLogicalRow:
    row_id: str
    ordinal: int
    page_tag: str
    row: ReaderRow
    normalized_y_anchor: float
    label_bbox: BoundingBox
    note_bbox: BoundingBox | None
    value_bboxes: tuple[BoundingBox | None, ...]
    label_line_indices: tuple[int, ...]
    note_line_indices: tuple[int, ...]
    value_line_indices: tuple[tuple[int, ...], ...]
    visual_cell_evidence: tuple[VisualCellEvidence | None, ...]
    structural_only: bool
    warnings: tuple[str, ...]

    @property
    def cell_slot_count(self) -> int:
        return len(self.row.cells)


@dataclass(frozen=True)
class ParsedLCTTWordBoxPage:
    input_path: str
    source_sha256: str
    source_image_path: str
    source_image_sha256: str
    page_tag: str
    statement_title: str
    statement_title_line_index: int
    report_period_text: str
    report_period_line_index: int
    form_text: str
    form_line_index: int
    scope: str
    method: CashFlowMethod
    continuation: bool
    axes: tuple[LCTTAxisBinding, ...]
    rows: tuple[LCTTLogicalRow, ...]
    line_height: float
    normalized_y_slope: float
    source_ocr_bbox: BoundingBox
    table_bbox: BoundingBox
    unassigned_numeric_line_indices: tuple[int, ...]
    excluded_after_table_line_indices: tuple[int, ...]
    evidence: tuple[str, ...]

    @property
    def cell_slot_count(self) -> int:
        return sum(row.cell_slot_count for row in self.rows)

    def observation_count(self, observation: ObservationKind) -> int:
        return sum(cell.observation is observation for row in self.rows for cell in row.row.cells)

    @property
    def value_cell_count(self) -> int:
        return self.observation_count(ObservationKind.VALUE)

    @property
    def dash_cell_count(self) -> int:
        return self.observation_count(ObservationKind.DASH)

    @property
    def blank_cell_count(self) -> int:
        return self.observation_count(ObservationKind.BLANK)


@dataclass(frozen=True)
class LCTTPageInput:
    result_path: Path
    source_image_path: Path
    page_tag: str


@dataclass(frozen=True)
class ParsedLCTTWordBoxDocument:
    pages: tuple[ParsedLCTTWordBoxPage, ...]
    rows: tuple[LCTTLogicalRow, ...]
    scope: str
    method: CashFlowMethod
    axes: tuple[LCTTAxisBinding, ...]
    evidence: tuple[str, ...]

    @property
    def cell_slot_count(self) -> int:
        return sum(page.cell_slot_count for page in self.pages)

    def observation_count(self, observation: ObservationKind) -> int:
        return sum(page.observation_count(observation) for page in self.pages)

    @property
    def value_cell_count(self) -> int:
        return self.observation_count(ObservationKind.VALUE)

    @property
    def dash_cell_count(self) -> int:
        return self.observation_count(ObservationKind.DASH)

    @property
    def blank_cell_count(self) -> int:
        return self.observation_count(ObservationKind.BLANK)


_DATE = re.compile(r"(?<!\d)(?P<day>\d{2})/(?P<month>\d{2})/(?P<year>20\d{2})(?!\d)")
_NOTE_REFERENCE = re.compile(
    r"^(?:\d+|[ijvlxcdm1|/]+)(?:[.]\d+)+(?:[(][0-9a-z]+[)])?$",
    re.IGNORECASE,
)
_REQUIRED_FORBIDDEN = {
    "numeric_cell_text_or_value_as_period_feature",
    "numeric_value_magnitude_as_method_feature",
    "template_labels_or_report_norm_ids",
    "historical_or_mongodb_values",
    "human_review_period_scope_or_method_answers",
    "horizontal_position_as_current_or_comparative_role",
    "cross_branch_schema_mapping",
}


def _positive_float(payload: dict[str, Any], name: str) -> float:
    value = payload.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise LCTTWordBoxError(f"invalid positive LCTT setting: {name}")
    return float(value)


def _anchor_map(payload: Any, *, expected: set[str], field: str) -> dict[str, tuple[str, ...]]:
    if not isinstance(payload, dict) or set(payload) != expected:
        raise LCTTWordBoxError(f"LCTT {field} semantics drifted")
    result = {}
    for semantic, raw_anchors in payload.items():
        if not isinstance(raw_anchors, list) or not raw_anchors:
            raise LCTTWordBoxError(f"LCTT {field} anchor list is empty")
        anchors = tuple(retrieval_key(str(anchor)) for anchor in raw_anchors)
        if any(not anchor for anchor in anchors):
            raise LCTTWordBoxError(f"LCTT {field} contains an empty anchor")
        result[str(semantic)] = anchors
    return result


def load_lctt_word_box_policy(path: Path) -> LCTTWordBoxPolicy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise LCTTWordBoxError(f"cannot load LCTT word-box policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "CONTINUATION_LCTT_WORD_BOX_V1"
        or payload.get("geometry_authority") != "PP_OCRV6_WORD_BOXES"
        or payload.get("statement_type") != "LCTT"
    ):
        raise LCTTWordBoxError("LCTT word-box policy identity drifted")
    semantic = payload.get("semantic_matching")
    header = payload.get("header_geometry")
    table = payload.get("table_geometry")
    if not all(isinstance(item, dict) for item in (semantic, header, table)):
        raise LCTTWordBoxError("LCTT word-box policy is incomplete")
    minimum_score = payload.get("minimum_line_score")
    if (
        isinstance(minimum_score, bool)
        or not isinstance(minimum_score, (int, float))
        or not 0 <= float(minimum_score) <= 1
    ):
        raise LCTTWordBoxError("LCTT minimum_line_score must be between zero and one")
    raw_title_anchors = semantic.get("statement_title_anchors")
    raw_continuation = semantic.get("continuation_anchors")
    if not isinstance(raw_title_anchors, list) or not raw_title_anchors:
        raise LCTTWordBoxError("LCTT statement-title anchors are empty")
    if not isinstance(raw_continuation, list) or not raw_continuation:
        raise LCTTWordBoxError("LCTT continuation anchors are empty")
    raw_units = semantic.get("unit_anchors")
    if not isinstance(raw_units, list) or not raw_units:
        raise LCTTWordBoxError("LCTT unit anchors are empty")
    units = []
    for raw in raw_units:
        if not isinstance(raw, dict):
            raise LCTTWordBoxError("LCTT unit anchor is invalid")
        text = raw.get("text")
        canonical = raw.get("canonical")
        multiplier = raw.get("multiplier")
        if (
            not isinstance(text, str)
            or not retrieval_key(text)
            or not isinstance(canonical, str)
            or not canonical
            or isinstance(multiplier, bool)
            or not isinstance(multiplier, int)
            or multiplier <= 0
        ):
            raise LCTTWordBoxError("LCTT unit anchor is invalid")
        units.append(LCTTUnitAnchor(text, canonical, multiplier))
    dash_name = payload.get("dash_detector_config")
    if not isinstance(dash_name, str) or Path(dash_name).name != dash_name:
        raise LCTTWordBoxError("LCTT dash detector config path is invalid")
    dash_path = (path.parent / dash_name).resolve()
    if not dash_path.is_file() or dash_path.parent != path.parent.resolve():
        raise LCTTWordBoxError("LCTT dash detector config is absent or escapes")
    if sha256_file(dash_path) != payload.get("dash_detector_config_sha256"):
        raise LCTTWordBoxError("LCTT dash detector config hash drifted")
    dash_payload = yaml.safe_load(dash_path.read_text(encoding="utf-8"))
    if not isinstance(dash_payload, dict):
        raise LCTTWordBoxError("LCTT dash detector config is invalid")
    forbidden = payload.get("forbidden_semantic_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise LCTTWordBoxError("LCTT forbidden semantic inputs drifted")
    return LCTTWordBoxPolicy(
        source_path=path.resolve(),
        minimum_line_score=float(minimum_score),
        minimum_title_similarity=_positive_float(semantic, "minimum_title_similarity"),
        minimum_header_similarity=_positive_float(semantic, "minimum_header_similarity"),
        minimum_distinct_semantics_margin=_positive_float(
            semantic, "minimum_distinct_semantics_margin"
        ),
        statement_title_anchors=tuple(retrieval_key(str(anchor)) for anchor in raw_title_anchors),
        scope_anchors=_anchor_map(
            semantic.get("scope_anchors"),
            expected={"CONSOLIDATED", "SEPARATE"},
            field="scope",
        ),
        method_title_anchors=_anchor_map(
            semantic.get("method_title_anchors"),
            expected={"DIRECT", "INDIRECT"},
            field="method-title",
        ),
        method_form_anchors=_anchor_map(
            semantic.get("method_form_anchors"),
            expected={"DIRECT", "INDIRECT"},
            field="method-form",
        ),
        continuation_anchors=tuple(retrieval_key(str(anchor)) for anchor in raw_continuation),
        unit_anchors=tuple(units),
        maximum_range_to_unit_center_distance_line_heights=_positive_float(
            header, "maximum_range_to_unit_center_distance_line_heights"
        ),
        maximum_start_to_end_center_distance_line_heights=_positive_float(
            header, "maximum_start_to_end_center_distance_line_heights"
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
        wrapped_label_gap_line_heights=_positive_float(table, "wrapped_label_gap_line_heights"),
        note_attach_line_heights=_positive_float(table, "note_attach_line_heights"),
        label_boundary_axis_gap_ratio=_positive_float(table, "label_boundary_axis_gap_ratio"),
        body_tail_line_heights=_positive_float(table, "body_tail_line_heights"),
        dash_config={str(key): value for key, value in dash_payload.items()},
        dash_config_path=dash_path,
        forbidden_semantic_inputs=tuple(str(item) for item in forbidden),
    )


def _load_lines(path: Path, minimum_score: float) -> tuple[str, tuple[_Line, ...]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LCTTWordBoxError(f"cannot read PP-OCRv6 result: {path}") from exc
    texts = payload.get("rec_texts")
    scores = payload.get("rec_scores")
    boxes = payload.get("rec_boxes")
    if (
        not all(isinstance(axis, list) for axis in (texts, scores, boxes))
        or len({len(texts), len(scores), len(boxes)}) != 1
    ):
        raise LCTTWordBoxError("PP-OCRv6 result axes are incomplete")
    lines = []
    for index, (text, score, box) in enumerate(zip(texts, scores, boxes, strict=True)):
        if not isinstance(box, list) or len(box) != 4:
            raise LCTTWordBoxError(f"line {index} has no four-coordinate box")
        bbox = BoundingBox(*(float(value) for value in box))
        if bbox.x1 <= bbox.x0 or bbox.y1 <= bbox.y0:
            raise LCTTWordBoxError(f"line {index} has a degenerate box")
        if float(score) >= minimum_score:
            lines.append(_Line(index, normalize_text(str(text)), float(score), bbox))
    if not lines:
        raise LCTTWordBoxError("PP-OCRv6 result contains no accepted lines")
    return str(payload.get("input_path", "")), tuple(lines)


def _similarity(text_key: str, anchor: str) -> float:
    if anchor in text_key:
        return 1.0
    return ratio(text_key, anchor) / 100


def _best_anchor(text: str, anchors: Iterable[str]) -> float:
    key = retrieval_key(text)
    return max((_similarity(key, anchor) for anchor in anchors), default=0.0)


def _best_semantic(
    text: str,
    anchors: dict[str, tuple[str, ...]],
    *,
    minimum_similarity: float,
    minimum_margin: float,
) -> str | None:
    scores = sorted(
        (
            (_best_anchor(text, semantic_anchors), semantic)
            for semantic, semantic_anchors in anchors.items()
        ),
        key=lambda item: (-item[0], item[1]),
    )
    if scores[0][0] < minimum_similarity or scores[0][0] - scores[1][0] < minimum_margin:
        return None
    return scores[0][1]


def _union(lines: Iterable[_Line]) -> BoundingBox:
    materialized = tuple(lines)
    if not materialized:
        raise LCTTWordBoxError("cannot construct an empty LCTT bounding box")
    return BoundingBox(
        min(line.bbox.x0 for line in materialized),
        min(line.bbox.y0 for line in materialized),
        max(line.bbox.x1 for line in materialized),
        max(line.bbox.y1 for line in materialized),
    )


def _minimum_bijection(
    left: tuple[Any, ...], right: tuple[Any, ...]
) -> tuple[tuple[Any, Any], ...]:
    if len(left) != len(right):
        raise LCTTWordBoxError("LCTT header axes cannot be paired bijectively")

    def x_center(item: Any) -> float:
        candidate = item[0] if isinstance(item, tuple) else item
        return float(candidate.x_center)

    best: tuple[float, tuple[int, ...]] | None = None
    for permutation in itertools.permutations(range(len(right))):
        cost = sum(
            abs(x_center(left[index]) - x_center(right[target]))
            for index, target in enumerate(permutation)
        )
        candidate = (cost, permutation)
        if best is None or candidate < best:
            best = candidate
    assert best is not None
    return tuple((item, right[target]) for item, target in zip(left, best[1], strict=True))


def _parse_date(text: str) -> date | None:
    match = _DATE.search(text)
    if match is None:
        return None
    try:
        return datetime.strptime(match.group(0), "%d/%m/%Y").date()
    except ValueError:
        return None


def _period_ranges(
    lines: tuple[_Line, ...], line_height: float, policy: LCTTWordBoxPolicy
) -> tuple[_PeriodRange, ...]:
    dated = [(line, parsed) for line in lines if (parsed := _parse_date(line.text)) is not None]
    starts = [(line, parsed) for line, parsed in dated if parsed.day == 1 and parsed.month == 1]
    if len(starts) != 2:
        raise LCTTWordBoxError("LCTT must expose two visible 01/01 duration starts")
    used: set[int] = set()
    ranges = []
    for start_line, period_start in sorted(starts, key=lambda item: item[0].x_center):
        candidates = [
            (line, parsed)
            for line, parsed in dated
            if line.index != start_line.index
            and line.index not in used
            and parsed.year == period_start.year
            and parsed >= period_start
            and line.y_center >= start_line.y_center
            and abs(line.x_center - start_line.x_center)
            <= line_height * policy.maximum_start_to_end_center_distance_line_heights
        ]
        if not candidates:
            raise LCTTWordBoxError("visible LCTT duration end cannot be paired to its start")
        end_line, period_end = min(
            candidates,
            key=lambda item: (
                abs(item[0].x_center - start_line.x_center),
                item[0].y_center,
                item[0].index,
            ),
        )
        used.add(end_line.index)
        ranges.append(_PeriodRange(start_line, end_line, period_start, period_end))
    return tuple(ranges)


def _unit_matches(
    lines: tuple[_Line, ...], policy: LCTTWordBoxPolicy
) -> tuple[tuple[_Line, LCTTUnitAnchor, float], ...]:
    matches = []
    for line in lines:
        key = retrieval_key(line.text)
        if not key or any(character.isdigit() for character in key):
            continue
        scores = sorted(
            ((_similarity(key, anchor.key), anchor) for anchor in policy.unit_anchors),
            key=lambda item: (-item[0], item[1].text),
        )
        similarity, anchor = scores[0]
        competing = [
            score
            for score, candidate in scores[1:]
            if (candidate.canonical, candidate.multiplier) != (anchor.canonical, anchor.multiplier)
        ]
        if (
            similarity >= policy.minimum_header_similarity
            and similarity - max(competing, default=0.0) >= policy.minimum_distinct_semantics_margin
        ):
            matches.append((line, anchor, similarity))
    return tuple(matches)


def _bind_headers(
    lines: tuple[_Line, ...], policy: LCTTWordBoxPolicy, line_height: float
) -> tuple[str, CashFlowMethod, bool, _Line, _Line, tuple[LCTTAxisBinding, ...]]:
    title_similarity, title = max(
        (
            _best_anchor(line.text, policy.statement_title_anchors),
            line,
        )
        for line in lines
    )
    if title_similarity < policy.minimum_title_similarity:
        raise LCTTWordBoxError("visible LCTT statement title is absent")
    scope = _best_semantic(
        title.text,
        policy.scope_anchors,
        minimum_similarity=policy.minimum_header_similarity,
        minimum_margin=policy.minimum_distinct_semantics_margin,
    )
    if scope is None:
        raise LCTTWordBoxError("visible LCTT consolidated/separate scope is unresolved")

    method_scores = {}
    form_by_method: dict[str, _Line] = {}
    for semantic in (CashFlowMethod.DIRECT.value, CashFlowMethod.INDIRECT.value):
        title_score = _best_anchor(title.text, policy.method_title_anchors[semantic])
        form_score, form_line = max(
            (_best_anchor(line.text, policy.method_form_anchors[semantic]), line) for line in lines
        )
        method_scores[semantic] = max(title_score, form_score)
        form_by_method[semantic] = form_line
    ranked_methods = sorted(method_scores.items(), key=lambda item: (-item[1], item[0]))
    if (
        ranked_methods[0][1] < policy.minimum_header_similarity
        or ranked_methods[0][1] - ranked_methods[1][1] < policy.minimum_distinct_semantics_margin
    ):
        raise LCTTWordBoxError("visible LCTT direct/indirect method is unresolved")
    method = CashFlowMethod(ranked_methods[0][0])
    form_line = form_by_method[method.value]
    continuation = (
        _best_anchor(title.text, policy.continuation_anchors) >= policy.minimum_header_similarity
    )

    ranges = _period_ranges(lines, line_height, policy)
    units = _unit_matches(lines, policy)
    if len(units) != 2:
        raise LCTTWordBoxError("LCTT must expose two visible axis-local units")
    unit_lines = tuple(record[0] for record in sorted(units, key=lambda item: item[0].x_center))
    if unit_lines[1].x_right - unit_lines[0].x_right < (
        line_height * policy.minimum_axis_separation_line_heights
    ):
        raise LCTTWordBoxError("LCTT unit-derived axes are not distinctly separated")
    paired = _minimum_bijection(ranges, tuple(sorted(units, key=lambda item: item[0].x_center)))
    report_end = max(period_range.period_end for period_range in ranges)
    bound = []
    for ordinal, (period_range, unit_record) in enumerate(paired, start=1):
        unit_line, unit_anchor, _similarity_score = unit_record
        if abs(period_range.x_center - unit_line.x_center) > (
            line_height * policy.maximum_range_to_unit_center_distance_line_heights
        ):
            raise LCTTWordBoxError("LCTT range/unit header geometry is not locally bounded")
        role = "CURRENT" if period_range.period_end == report_end else "COMPARATIVE"
        duration_months = (
            (period_range.period_end.year - period_range.period_start.year) * 12
            + period_range.period_end.month
            - period_range.period_start.month
            + 1
        )
        bound.append(
            LCTTAxisBinding(
                ordinal=ordinal,
                axis_id=f"value-{ordinal}",
                axis_right_edge=unit_line.x_right,
                raw_start_header=period_range.start_line.text,
                start_header_line_index=period_range.start_line.index,
                raw_end_header=period_range.end_line.text,
                end_header_line_index=period_range.end_line.index,
                current_or_comparative=role,
                raw_unit_text=unit_line.text,
                unit_line_index=unit_line.index,
                canonical_unit=unit_anchor.canonical,
                unit_multiplier=unit_anchor.multiplier,
                period_start=period_range.period_start,
                period_end=period_range.period_end,
                period_type="DURATION",
                duration_months=duration_months,
                header_bbox=_union((period_range.start_line, period_range.end_line, unit_line)),
                unit_bbox=unit_line.bbox,
                evidence=(
                    "duration start/end parsed from the visible axis-local range header",
                    "current/comparative role derived from the visible dates, not x-order",
                    "unit and multiplier bound from the visible axis-local unit word box",
                    "numeric values were not read while period, role, scope, and method were bound",
                ),
            )
        )
    if {axis.current_or_comparative for axis in bound} != {"CURRENT", "COMPARATIVE"}:
        raise LCTTWordBoxError("LCTT must expose one current and one comparative duration axis")
    report_lines = [
        line
        for line in lines
        if (parsed := _parse_date(line.text)) is not None and parsed == report_end
    ]
    report_line = min(report_lines, key=lambda line: (line.x_center, line.index))
    return scope, method, continuation, title, report_line, form_line, tuple(bound)


def _financial_token(line: _Line) -> bool:
    normalized = normalize_text(line.text)
    if not normalized or any(character.isalpha() for character in normalized):
        return False
    return parse_financial_number_strict_grouping(normalized).observation in {
        ObservationKind.VALUE,
        ObservationKind.ZERO,
        ObservationKind.DASH,
    }


def _note_like(text: str) -> bool:
    compact = normalize_text(text).replace(" ", "").strip(". ")
    return bool(_NOTE_REFERENCE.fullmatch(compact))


def _clusters(lines: list[_Line], *, y_value: Any, tolerance: float) -> list[list[_Line]]:
    groups: list[list[_Line]] = []
    for line in sorted(lines, key=lambda item: (y_value(item), item.bbox.x0)):
        if (
            groups
            and abs(y_value(line) - statistics.fmean(y_value(item) for item in groups[-1]))
            <= tolerance
        ):
            groups[-1].append(line)
        else:
            groups.append([line])
    return groups


def _source_ids(page_tag: str, lines: Iterable[_Line]) -> tuple[str, ...]:
    return tuple(
        f"{page_tag}:line-{line.index:04d}"
        for line in sorted(set(lines), key=lambda item: item.index)
    )


def _join_financial_tokens(lines: Iterable[_Line]) -> str | None:
    ordered = sorted(lines, key=lambda line: line.bbox.x0)
    return " ".join(line.text for line in ordered) if ordered else None


@dataclass
class _RowRecord:
    y_anchor: float
    labels: list[_Line]
    notes: list[_Line]
    values: list[list[_Line]]
    visual: tuple[VisualCellEvidence | None, ...]
    structural_only: bool


def _reconstruct_rows(
    lines: tuple[_Line, ...],
    axes: tuple[LCTTAxisBinding, ...],
    policy: LCTTWordBoxPolicy,
    line_height: float,
    *,
    page_tag: str,
    source_image_path: Path,
) -> tuple[
    tuple[LCTTLogicalRow, ...],
    tuple[LCTTAxisBinding, ...],
    float,
    tuple[int, ...],
    tuple[int, ...],
    BoundingBox,
]:
    source_image = _read_source_image(source_image_path)
    if source_image is None:
        raise LCTTWordBoxError("LCTT source image is required for visible dash/blank status")
    unit_lines = [
        next(line for line in lines if line.index == axis.unit_line_index) for axis in axes
    ]
    body_start = max(line.bbox.y1 for line in unit_lines)
    numeric_candidates = [
        line for line in lines if line.y_center > body_start and _financial_token(line)
    ]
    initial_edges = [axis.axis_right_edge for axis in axes]
    initial_gap = initial_edges[1] - initial_edges[0]
    per_axis: list[list[_Line]] = [[] for _axis in axes]
    unassigned = []
    for line in numeric_candidates:
        distances = [abs(line.x_right - edge) for edge in initial_edges]
        closest = min(range(len(distances)), key=distances.__getitem__)
        if (
            distances[closest] <= initial_gap * policy.numeric_axis_max_distance_ratio
            and line.x_right
            <= initial_edges[closest] + line_height * policy.numeric_axis_right_overrun_line_heights
        ):
            per_axis[closest].append(line)
        else:
            unassigned.append(line)
    if any(not axis_lines for axis_lines in per_axis):
        raise LCTTWordBoxError("LCTT body does not expose numeric geometry on both axes")
    refined_axes = tuple(
        replace(axis, axis_right_edge=statistics.median(line.x_right for line in axis_lines))
        for axis, axis_lines in zip(axes, per_axis, strict=True)
    )
    left_unit, right_unit = sorted(unit_lines, key=lambda line: line.x_center)
    normalized_y_slope = (right_unit.y_center - left_unit.y_center) / (
        right_unit.x_center - left_unit.x_center
    )

    def normalized_y(line: _Line) -> float:
        return line.y_center - normalized_y_slope * line.x_center

    assigned_numeric = [line for axis_lines in per_axis for line in axis_lines]
    numeric_groups = _clusters(
        assigned_numeric,
        y_value=normalized_y,
        tolerance=line_height * policy.row_anchor_cluster_line_heights,
    )
    numeric_centers = [
        statistics.fmean(normalized_y(line) for line in group) for group in numeric_groups
    ]
    if not numeric_centers:
        raise LCTTWordBoxError("LCTT body contains no reconstructed numeric row anchors")
    body_end = numeric_centers[-1] + line_height * policy.body_tail_line_heights
    axis_gap = refined_axes[1].axis_right_edge - refined_axes[0].axis_right_edge
    label_boundary = (
        refined_axes[0].axis_right_edge - axis_gap * policy.label_boundary_axis_gap_ratio
    )
    numeric_indices = {line.index for line in assigned_numeric + unassigned}
    body_text = [
        line
        for line in lines
        if line.y_center > body_start
        and normalized_y(line) <= body_end
        and line.x_right < label_boundary
        and line.index not in numeric_indices
        and not _financial_token(line)
    ]
    note_lines = [line for line in body_text if _note_like(line.text)]
    label_lines = [line for line in body_text if line not in note_lines]

    def dash_evidence(axis: LCTTAxisBinding, y_anchor: float) -> VisualCellEvidence | None:
        raw_y = y_anchor + normalized_y_slope * axis.axis_right_edge
        return _detect_visible_dash_v3(
            source_image,
            source_image_path=source_image_path,
            axis_right_edge=axis.axis_right_edge,
            anchor_center=raw_y,
            line_height=line_height,
            config=policy.dash_config,
        )

    dash_only = []
    for line in label_lines:
        y_anchor = normalized_y(line)
        evidence = tuple(dash_evidence(axis, y_anchor) for axis in refined_axes)
        if all(record is not None for record in evidence):
            dash_only.append((y_anchor, evidence))
    anchor_centers = list(numeric_centers)
    dash_by_center: dict[float, tuple[VisualCellEvidence | None, ...]] = {}
    for y_anchor, evidence in dash_only:
        if min((abs(y_anchor - center) for center in anchor_centers), default=float("inf")) <= (
            line_height * policy.row_anchor_cluster_line_heights
        ):
            continue
        anchor_centers.append(y_anchor)
        dash_by_center[y_anchor] = evidence
    anchor_centers.sort()

    label_assignment: dict[int, int] = {}
    direct_tolerance = line_height * policy.label_direct_attach_line_heights
    for line in label_lines:
        distances = [abs(normalized_y(line) - center) for center in anchor_centers]
        target = min(range(len(distances)), key=distances.__getitem__)
        if distances[target] <= direct_tolerance:
            label_assignment[line.index] = target
    ordered_labels = sorted(label_lines, key=lambda line: (normalized_y(line), line.bbox.x0))
    wrap_tolerance = line_height * policy.wrapped_label_gap_line_heights
    for position in range(len(ordered_labels) - 2, -1, -1):
        line = ordered_labels[position]
        following = ordered_labels[position + 1]
        if (
            line.index not in label_assignment
            and following.index in label_assignment
            and normalized_y(following) - normalized_y(line) <= wrap_tolerance
        ):
            label_assignment[line.index] = label_assignment[following.index]

    note_assignment: dict[int, int] = {}
    note_tolerance = line_height * policy.note_attach_line_heights
    for line in note_lines:
        distances = [abs(normalized_y(line) - center) for center in anchor_centers]
        target = min(range(len(distances)), key=distances.__getitem__)
        if distances[target] <= note_tolerance:
            note_assignment[line.index] = target

    records: list[_RowRecord] = []
    for anchor_index, center in enumerate(anchor_centers):
        labels = sorted(
            (line for line in label_lines if label_assignment.get(line.index) == anchor_index),
            key=lambda line: (normalized_y(line), line.bbox.x0),
        )
        notes = sorted(
            (line for line in note_lines if note_assignment.get(line.index) == anchor_index),
            key=lambda line: line.bbox.x0,
        )
        group = min(
            numeric_groups,
            key=lambda lines_: abs(
                statistics.fmean(normalized_y(line) for line in lines_) - center
            ),
        )
        group_center = statistics.fmean(normalized_y(line) for line in group)
        if abs(group_center - center) > (line_height * policy.row_anchor_cluster_line_heights):
            group = []
        values = [
            sorted((line for line in axis_lines if line in group), key=lambda line: line.bbox.x0)
            for axis_lines in per_axis
        ]
        visual = tuple(
            None if axis_lines else dash_evidence(axis, center)
            for axis, axis_lines in zip(refined_axes, values, strict=True)
        )
        if not labels:
            raise LCTTWordBoxError("reconstructed LCTT financial anchor has no visible label")
        records.append(_RowRecord(center, labels, notes, values, visual, False))
    for line in label_lines:
        if line.index in label_assignment:
            continue
        records.append(
            _RowRecord(
                normalized_y(line),
                [line],
                [],
                [[] for _axis in refined_axes],
                tuple(None for _axis in refined_axes),
                True,
            )
        )
    records.sort(key=lambda record: record.y_anchor)

    rows = []
    for ordinal, record in enumerate(records, start=1):
        cells: tuple[ParsedNumber, ...] = tuple(
            parse_financial_number_strict_grouping(
                "-"
                if evidence is not None and not axis_lines
                else _join_financial_tokens(axis_lines)
            )
            for axis_lines, evidence in zip(record.values, record.visual, strict=True)
        )
        warnings = []
        if any(len(axis_lines) > 1 for axis_lines in record.values):
            warnings.append("multiple OCR tokens reconstructed in one LCTT financial cell")
        if any(cell.observation is ObservationKind.INVALID for cell in cells):
            warnings.append("one or more LCTT financial cells are invalid")
        if any(evidence is not None for evidence in record.visual):
            warnings.append("OCR-blank cell recovered as DASH from constrained pixel evidence")
        if record.structural_only:
            warnings.append("visible structural LCTT row retained with BLANK cells")
        source_lines = [
            *record.labels,
            *record.notes,
            *(line for axis_lines in record.values for line in axis_lines),
        ]
        rows.append(
            LCTTLogicalRow(
                row_id=f"{page_tag}:row-{ordinal:04d}",
                ordinal=ordinal,
                page_tag=page_tag,
                row=ReaderRow(
                    source_row_ids=_source_ids(page_tag, source_lines),
                    label=normalize_text(" ".join(line.text for line in record.labels)),
                    note_reference=normalize_text(" ".join(line.text for line in record.notes))
                    or None,
                    cells=cells,
                ),
                normalized_y_anchor=record.y_anchor,
                label_bbox=_union(record.labels),
                note_bbox=_union(record.notes) if record.notes else None,
                value_bboxes=tuple(
                    _union(axis_lines) if axis_lines else None for axis_lines in record.values
                ),
                label_line_indices=tuple(line.index for line in record.labels),
                note_line_indices=tuple(line.index for line in record.notes),
                value_line_indices=tuple(
                    tuple(line.index for line in axis_lines) for axis_lines in record.values
                ),
                visual_cell_evidence=record.visual,
                structural_only=record.structural_only,
                warnings=tuple(warnings),
            )
        )
    table_lines = {
        line.index: line
        for row in rows
        for source_id in row.row.source_row_ids
        for line in lines
        if line.index == int(source_id.rsplit("-", 1)[-1])
    }
    excluded_after = tuple(
        line.index for line in lines if line.y_center > body_start and normalized_y(line) > body_end
    )
    return (
        tuple(rows),
        refined_axes,
        normalized_y_slope,
        tuple(line.index for line in sorted(unassigned, key=lambda item: item.index)),
        excluded_after,
        _union(table_lines.values()),
    )


def parse_lctt_word_box_page(
    result_path: Path,
    policy: LCTTWordBoxPolicy,
    *,
    page_tag: str,
    source_image_path: Path,
) -> ParsedLCTTWordBoxPage:
    """Reconstruct one visible two-axis direct/indirect LCTT page."""

    input_path, lines = _load_lines(result_path, policy.minimum_line_score)
    line_height = float(statistics.median(line.height for line in lines))
    if line_height <= 0:
        raise LCTTWordBoxError("LCTT word-box line height is invalid")
    scope, method, continuation, title, report_line, form_line, axes = _bind_headers(
        lines, policy, line_height
    )
    rows, axes, y_slope, unassigned, excluded_after, table_bbox = _reconstruct_rows(
        lines,
        axes,
        policy,
        line_height,
        page_tag=page_tag,
        source_image_path=source_image_path,
    )
    return ParsedLCTTWordBoxPage(
        input_path=input_path,
        source_sha256=sha256_file(result_path),
        source_image_path=str(source_image_path),
        source_image_sha256=sha256_file(source_image_path),
        page_tag=page_tag,
        statement_title=title.text,
        statement_title_line_index=title.index,
        report_period_text=report_line.text,
        report_period_line_index=report_line.index,
        form_text=form_line.text,
        form_line_index=form_line.index,
        scope=scope,
        method=method,
        continuation=continuation,
        axes=axes,
        rows=rows,
        line_height=line_height,
        normalized_y_slope=y_slope,
        source_ocr_bbox=_union(lines),
        table_bbox=table_bbox,
        unassigned_numeric_line_indices=unassigned,
        excluded_after_table_line_indices=excluded_after,
        evidence=(
            "scope bound from the visible statement title",
            "method bound from visible title/form evidence before schema selection",
            "two DURATION axes bound from visible start/end/unit headers before body values",
            "axis-local right-edge geometry refined only after current/comparative roles were sealed",
            "missing OCR tokens classified as DASH only with constrained source pixels",
        ),
    )


def _axis_signature(axis: LCTTAxisBinding) -> tuple[object, ...]:
    return (
        axis.current_or_comparative,
        axis.period_start,
        axis.period_end,
        axis.period_type,
        axis.duration_months,
        axis.canonical_unit,
        axis.unit_multiplier,
    )


def parse_lctt_word_box_document(
    page_inputs: tuple[LCTTPageInput, ...], policy: LCTTWordBoxPolicy
) -> ParsedLCTTWordBoxDocument:
    if len(page_inputs) < 2:
        raise LCTTWordBoxError("continued LCTT document requires at least two visible pages")
    pages = tuple(
        parse_lctt_word_box_page(
            page.result_path,
            policy,
            page_tag=page.page_tag,
            source_image_path=page.source_image_path,
        )
        for page in page_inputs
    )
    if pages[0].continuation or any(not page.continuation for page in pages[1:]):
        raise LCTTWordBoxError("LCTT continuation markers do not match page order")
    if len({page.scope for page in pages}) != 1:
        raise LCTTWordBoxError("LCTT scope conflicts across continuation pages")
    if len({page.method for page in pages}) != 1:
        raise LCTTWordBoxError("LCTT method conflicts across continuation pages")
    reference_axes = tuple(_axis_signature(axis) for axis in pages[0].axes)
    if any(
        tuple(_axis_signature(axis) for axis in page.axes) != reference_axes for page in pages[1:]
    ):
        raise LCTTWordBoxError("LCTT duration/unit axes conflict across continuation pages")
    return ParsedLCTTWordBoxDocument(
        pages=pages,
        rows=tuple(row for page in pages for row in page.rows),
        scope=pages[0].scope,
        method=pages[0].method,
        axes=pages[0].axes,
        evidence=(
            "first page is unmarked and every following page exposes a continuation title",
            "scope, method, period roles, dates, duration, unit, and multiplier agree across pages",
            "logical rows retain source page identity and document order",
        ),
    )


__all__ = [
    "LCTTAxisBinding",
    "LCTTLogicalRow",
    "LCTTPageInput",
    "LCTTWordBoxError",
    "LCTTWordBoxPolicy",
    "ParsedLCTTWordBoxDocument",
    "ParsedLCTTWordBoxPage",
    "load_lctt_word_box_policy",
    "parse_lctt_word_box_document",
    "parse_lctt_word_box_page",
]
