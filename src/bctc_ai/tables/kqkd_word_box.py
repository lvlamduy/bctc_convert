from __future__ import annotations

import calendar
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
from bctc_ai.core.text import ParsedNumber, normalize_text, parse_financial_number, retrieval_key
from bctc_ai.validation.reader_agreement import ReaderRow


class KQKDWordBoxError(RuntimeError):
    pass


class KQKDAxisGroup(StrEnum):
    QUARTER = "QUARTER"
    YTD = "YTD"


@dataclass(frozen=True)
class KQKDUnitAnchor:
    text: str
    canonical: str
    multiplier: int

    @property
    def key(self) -> str:
        return retrieval_key(self.text)


@dataclass(frozen=True)
class KQKDWordBoxPolicy:
    source_path: Path
    minimum_line_score: float
    minimum_title_similarity: float
    minimum_header_similarity: float
    minimum_distinct_semantics_margin: float
    statement_title_anchors: tuple[str, ...]
    scope_anchors: dict[str, tuple[str, ...]]
    group_anchors: dict[str, tuple[str, ...]]
    role_anchors: dict[str, tuple[str, ...]]
    unit_anchors: tuple[KQKDUnitAnchor, ...]
    maximum_role_to_unit_center_distance_line_heights: float
    maximum_group_to_axis_center_distance_line_heights: float
    minimum_axis_separation_line_heights: float
    axis_right_edge_max_distance_ratio: float
    axis_right_overrun_line_heights: float
    row_anchor_cluster_line_heights: float
    label_direct_attach_line_heights: float
    label_below_anchor_tolerance_line_heights: float
    wrapped_label_center_gap_line_heights: float
    note_attach_line_heights: float
    label_boundary_axis_gap_ratio: float
    forbidden_header_inputs: tuple[str, ...]


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
class _SemanticLine:
    line: _Line
    semantic: str
    similarity: float
    distinct_semantics_margin: float


@dataclass(frozen=True)
class KQKDAxisBinding:
    ordinal: int
    axis_id: str
    axis_right_edge: float
    group: KQKDAxisGroup
    raw_group_header: str
    group_header_line_index: int
    raw_role_header: str
    role_header_line_index: int
    current_or_comparative: str
    raw_unit_text: str
    unit_line_index: int
    canonical_unit: str
    unit_multiplier: int
    period_start: date
    period_end: date
    period_type: str
    duration_months: int
    schema_export_candidate: bool
    header_bbox: BoundingBox
    unit_bbox: BoundingBox
    evidence: tuple[str, ...]

    @property
    def header_binding(self) -> HeaderBinding:
        return HeaderBinding(
            axis_id=self.axis_id,
            raw_header=normalize_text(f"{self.raw_group_header} | {self.raw_role_header}"),
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
class KQKDLogicalRow:
    row_id: str
    ordinal: int
    row: ReaderRow
    y_anchor: float
    label_bbox: BoundingBox | None
    note_bbox: BoundingBox | None
    value_bboxes: tuple[BoundingBox | None, ...]
    label_line_indices: tuple[int, ...]
    note_line_indices: tuple[int, ...]
    value_line_indices: tuple[tuple[int, ...], ...]
    warnings: tuple[str, ...]

    @property
    def observed_cell_count(self) -> int:
        return sum(
            cell.observation in {ObservationKind.VALUE, ObservationKind.ZERO, ObservationKind.DASH}
            for cell in self.row.cells
        )


@dataclass(frozen=True)
class ParsedKQKDWordBoxPage:
    input_path: str
    source_sha256: str
    page_tag: str
    statement_title: str
    statement_title_line_index: int
    report_period_text: str
    report_period_line_index: int
    scope: str
    axes: tuple[KQKDAxisBinding, ...]
    rows: tuple[KQKDLogicalRow, ...]
    line_height: float
    source_ocr_bbox: BoundingBox
    table_bbox: BoundingBox
    unassigned_numeric_line_indices: tuple[int, ...]
    orphan_label_line_indices: tuple[int, ...]
    evidence: tuple[str, ...]

    @property
    def schema_export_axes(self) -> tuple[KQKDAxisBinding, ...]:
        return tuple(axis for axis in self.axes if axis.schema_export_candidate)

    @property
    def provenance_only_axes(self) -> tuple[KQKDAxisBinding, ...]:
        return tuple(axis for axis in self.axes if not axis.schema_export_candidate)

    @property
    def assigned_numeric_line_count(self) -> int:
        return sum(len(indices) for row in self.rows for indices in row.value_line_indices)

    @property
    def observed_cell_count(self) -> int:
        return sum(row.observed_cell_count for row in self.rows)


_REQUIRED_FORBIDDEN = {
    "numeric_cell_text_or_value_as_period_feature",
    "numeric_value_equality_between_quarter_and_ytd",
    "numeric_value_magnitude",
    "template_labels_or_report_norm_ids",
    "historical_or_mongodb_values",
    "human_review_period_or_scope_answers",
    "horizontal_position_as_current_or_comparative_role",
}
_NUMERIC = re.compile(r"^[\d\s.,()\-–—+]+$")
_NOTE_REFERENCE = re.compile(
    r"^(?:\d+|[ijvlxcdm1|/]+)(?:[.]\d+)+(?:[(][0-9a-z]+[)])?$",
    re.IGNORECASE,
)
_QUARTER = re.compile(r"\bquy\s+(?P<quarter>[1-4]|i{1,3}|iv|l)\s+(?P<year>20\d{2})\b")


def _positive_float(payload: dict[str, Any], name: str) -> float:
    value = payload.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise KQKDWordBoxError(f"invalid positive KQKD setting: {name}")
    return float(value)


def _anchor_map(payload: Any, *, expected: set[str], field: str) -> dict[str, tuple[str, ...]]:
    if not isinstance(payload, dict) or set(payload) != expected:
        raise KQKDWordBoxError(f"KQKD {field} semantics drifted")
    result: dict[str, tuple[str, ...]] = {}
    for semantic, raw_anchors in payload.items():
        if not isinstance(raw_anchors, list) or not raw_anchors:
            raise KQKDWordBoxError(f"KQKD {field} anchor list is empty")
        anchors = tuple(retrieval_key(str(anchor)) for anchor in raw_anchors)
        if any(not anchor for anchor in anchors):
            raise KQKDWordBoxError(f"KQKD {field} contains an empty anchor")
        result[str(semantic)] = anchors
    return result


def load_kqkd_word_box_policy(path: Path) -> KQKDWordBoxPolicy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise KQKDWordBoxError(f"cannot load KQKD word-box policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "HIERARCHICAL_KQKD_WORD_BOX_V1"
        or payload.get("geometry_authority") != "PP_OCRV6_WORD_BOXES"
        or payload.get("statement_type") != "KQKD"
    ):
        raise KQKDWordBoxError("KQKD word-box policy identity drifted")
    semantic = payload.get("semantic_matching")
    header = payload.get("header_geometry")
    table = payload.get("table_geometry")
    if not all(isinstance(item, dict) for item in (semantic, header, table)):
        raise KQKDWordBoxError("KQKD word-box policy is incomplete")
    minimum_score = payload.get("minimum_line_score")
    if (
        isinstance(minimum_score, bool)
        or not isinstance(minimum_score, (int, float))
        or not 0 <= float(minimum_score) <= 1
    ):
        raise KQKDWordBoxError("KQKD minimum_line_score must be between zero and one")
    title_anchors = semantic.get("statement_title_anchors")
    if not isinstance(title_anchors, list) or not title_anchors:
        raise KQKDWordBoxError("KQKD statement-title anchors are empty")
    unit_anchors = []
    raw_units = semantic.get("unit_anchors")
    if not isinstance(raw_units, list) or not raw_units:
        raise KQKDWordBoxError("KQKD unit anchors are empty")
    for raw in raw_units:
        if not isinstance(raw, dict):
            raise KQKDWordBoxError("KQKD unit anchor is invalid")
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
            raise KQKDWordBoxError("KQKD unit anchor is invalid")
        unit_anchors.append(KQKDUnitAnchor(text, canonical, multiplier))
    forbidden = payload.get("forbidden_header_inputs")
    if not isinstance(forbidden, list) or set(forbidden) != _REQUIRED_FORBIDDEN:
        raise KQKDWordBoxError("KQKD forbidden header inputs drifted")
    return KQKDWordBoxPolicy(
        source_path=path.resolve(),
        minimum_line_score=float(minimum_score),
        minimum_title_similarity=_positive_float(semantic, "minimum_title_similarity"),
        minimum_header_similarity=_positive_float(semantic, "minimum_header_similarity"),
        minimum_distinct_semantics_margin=_positive_float(
            semantic, "minimum_distinct_semantics_margin"
        ),
        statement_title_anchors=tuple(retrieval_key(str(anchor)) for anchor in title_anchors),
        scope_anchors=_anchor_map(
            semantic.get("scope_anchors"),
            expected={"CONSOLIDATED", "SEPARATE"},
            field="scope",
        ),
        group_anchors=_anchor_map(
            semantic.get("group_anchors"),
            expected={"QUARTER", "YTD"},
            field="group",
        ),
        role_anchors=_anchor_map(
            semantic.get("role_anchors"),
            expected={"CURRENT", "COMPARATIVE"},
            field="role",
        ),
        unit_anchors=tuple(unit_anchors),
        maximum_role_to_unit_center_distance_line_heights=_positive_float(
            header, "maximum_role_to_unit_center_distance_line_heights"
        ),
        maximum_group_to_axis_center_distance_line_heights=_positive_float(
            header, "maximum_group_to_axis_center_distance_line_heights"
        ),
        minimum_axis_separation_line_heights=_positive_float(
            header, "minimum_axis_separation_line_heights"
        ),
        axis_right_edge_max_distance_ratio=_positive_float(
            table, "axis_right_edge_max_distance_ratio"
        ),
        axis_right_overrun_line_heights=_positive_float(table, "axis_right_overrun_line_heights"),
        row_anchor_cluster_line_heights=_positive_float(table, "row_anchor_cluster_line_heights"),
        label_direct_attach_line_heights=_positive_float(table, "label_direct_attach_line_heights"),
        label_below_anchor_tolerance_line_heights=_positive_float(
            table, "label_below_anchor_tolerance_line_heights"
        ),
        wrapped_label_center_gap_line_heights=_positive_float(
            table, "wrapped_label_center_gap_line_heights"
        ),
        note_attach_line_heights=_positive_float(table, "note_attach_line_heights"),
        label_boundary_axis_gap_ratio=_positive_float(table, "label_boundary_axis_gap_ratio"),
        forbidden_header_inputs=tuple(str(item) for item in forbidden),
    )


def _load_lines(path: Path, minimum_score: float) -> tuple[str, tuple[_Line, ...]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise KQKDWordBoxError(f"cannot read PP-OCRv6 result: {path}") from exc
    texts = payload.get("rec_texts")
    scores = payload.get("rec_scores")
    boxes = payload.get("rec_boxes")
    if (
        not all(isinstance(axis, list) for axis in (texts, scores, boxes))
        or len({len(texts), len(scores), len(boxes)}) != 1
    ):
        raise KQKDWordBoxError("PP-OCRv6 result axes are incomplete")
    lines = []
    for index, (text, score, box) in enumerate(zip(texts, scores, boxes, strict=True)):
        if not isinstance(box, list) or len(box) != 4:
            raise KQKDWordBoxError(f"line {index} has no four-coordinate box")
        bbox = BoundingBox(*(float(value) for value in box))
        if bbox.x1 <= bbox.x0 or bbox.y1 <= bbox.y0:
            raise KQKDWordBoxError(f"line {index} has a degenerate box")
        if float(score) >= minimum_score:
            lines.append(_Line(index, normalize_text(str(text)), float(score), bbox))
    if not lines:
        raise KQKDWordBoxError("PP-OCRv6 result contains no accepted lines")
    return str(payload.get("input_path", "")), tuple(lines)


def _similarity(text_key: str, anchor: str) -> float:
    if anchor in text_key:
        return 1.0
    return ratio(text_key, anchor) / 100


def _best_semantic(
    line: _Line,
    anchors: dict[str, tuple[str, ...]],
    *,
    minimum_similarity: float,
    minimum_margin: float,
) -> _SemanticLine | None:
    key = retrieval_key(line.text)
    scores = [
        (max(_similarity(key, anchor) for anchor in semantic_anchors), semantic)
        for semantic, semantic_anchors in anchors.items()
    ]
    scores.sort(key=lambda item: (-item[0], item[1]))
    best, semantic = scores[0]
    runner_up = scores[1][0]
    if best < minimum_similarity or best - runner_up < minimum_margin:
        return None
    return _SemanticLine(line, semantic, best, best - runner_up)


def _unique_semantic_lines(
    lines: tuple[_Line, ...],
    anchors: dict[str, tuple[str, ...]],
    *,
    minimum_similarity: float,
    minimum_margin: float,
) -> tuple[_SemanticLine, ...]:
    return tuple(
        match
        for line in lines
        if (
            match := _best_semantic(
                line,
                anchors,
                minimum_similarity=minimum_similarity,
                minimum_margin=minimum_margin,
            )
        )
        is not None
    )


def _quarter_period(line: _Line) -> tuple[int, int]:
    match = _QUARTER.search(retrieval_key(line.text))
    if match is None:
        raise KQKDWordBoxError("visible KQKD report quarter/year is absent")
    token = match.group("quarter")
    quarter = {
        "1": 1,
        "i": 1,
        "l": 1,
        "2": 2,
        "ii": 2,
        "3": 3,
        "iii": 3,
        "4": 4,
        "iv": 4,
    }.get(token)
    if quarter is None:
        raise KQKDWordBoxError("visible KQKD quarter token is invalid")
    return quarter, int(match.group("year"))


def _period_dates(quarter: int, year: int, role: str, group: str) -> tuple[date, date, str]:
    bound_year = year if role == "CURRENT" else year - 1
    end_month = quarter * 3
    period_end = date(bound_year, end_month, calendar.monthrange(bound_year, end_month)[1])
    if group == "QUARTER":
        return date(bound_year, end_month - 2, 1), period_end, "DURATION"
    return date(bound_year, 1, 1), period_end, "YTD"


def _union(lines: tuple[_Line, ...] | list[_Line]) -> BoundingBox:
    return BoundingBox(
        min(line.bbox.x0 for line in lines),
        min(line.bbox.y0 for line in lines),
        max(line.bbox.x1 for line in lines),
        max(line.bbox.y1 for line in lines),
    )


def _unit_matches(
    lines: tuple[_Line, ...], policy: KQKDWordBoxPolicy
) -> tuple[tuple[_Line, KQKDUnitAnchor, float], ...]:
    result = []
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
        margin = similarity - max(competing, default=0.0)
        if (
            similarity >= policy.minimum_header_similarity
            and margin >= policy.minimum_distinct_semantics_margin
        ):
            result.append((line, anchor, similarity))
    return tuple(result)


def _minimum_bijection(
    left: tuple[_Line, ...], right: tuple[_Line, ...]
) -> tuple[tuple[_Line, _Line], ...]:
    if len(left) != len(right):
        raise KQKDWordBoxError("KQKD header axes cannot be paired bijectively")
    best: tuple[float, tuple[int, ...]] | None = None
    for permutation in itertools.permutations(range(len(right))):
        cost = sum(
            abs(left[index].x_center - right[target].x_center)
            for index, target in enumerate(permutation)
        )
        candidate = (cost, permutation)
        if best is None or candidate < best:
            best = candidate
    assert best is not None
    return tuple((line, right[target]) for line, target in zip(left, best[1], strict=True))


def _bind_axes(
    lines: tuple[_Line, ...], policy: KQKDWordBoxPolicy, line_height: float
) -> tuple[str, _Line, _Line, tuple[KQKDAxisBinding, ...]]:
    title_candidates = [
        (
            max(
                _similarity(retrieval_key(line.text), anchor)
                for anchor in policy.statement_title_anchors
            ),
            line,
        )
        for line in lines
    ]
    title_similarity, title = max(title_candidates, key=lambda item: (item[0], -item[1].index))
    if title_similarity < policy.minimum_title_similarity:
        raise KQKDWordBoxError("visible KQKD statement title is absent")
    scope_match = _best_semantic(
        title,
        policy.scope_anchors,
        minimum_similarity=policy.minimum_header_similarity,
        minimum_margin=policy.minimum_distinct_semantics_margin,
    )
    if scope_match is None:
        raise KQKDWordBoxError("visible KQKD consolidated/separate scope is unresolved")

    period_candidates = []
    for line in lines:
        try:
            quarter, year = _quarter_period(line)
        except KQKDWordBoxError:
            continue
        period_candidates.append((line, quarter, year))
    if len(period_candidates) != 1:
        raise KQKDWordBoxError("visible KQKD report quarter/year is not unique")
    period_line, quarter, report_year = period_candidates[0]

    group_matches = _unique_semantic_lines(
        lines,
        policy.group_anchors,
        minimum_similarity=policy.minimum_header_similarity,
        minimum_margin=policy.minimum_distinct_semantics_margin,
    )
    role_matches = _unique_semantic_lines(
        lines,
        policy.role_anchors,
        minimum_similarity=policy.minimum_header_similarity,
        minimum_margin=policy.minimum_distinct_semantics_margin,
    )
    if len(group_matches) != 2 or {match.semantic for match in group_matches} != {
        "QUARTER",
        "YTD",
    }:
        raise KQKDWordBoxError("KQKD must expose one QUARTER and one YTD group header")
    if len(role_matches) != 4:
        raise KQKDWordBoxError("KQKD must expose four visible current/comparative role headers")

    units = _unit_matches(lines, policy)
    if len(units) != 4:
        raise KQKDWordBoxError("KQKD must expose four axis-local visible units")
    ordered_units = tuple(sorted(units, key=lambda item: item[0].x_right))
    unit_lines = tuple(item[0] for item in ordered_units)
    gaps = [
        right.x_right - left.x_right
        for left, right in zip(unit_lines, unit_lines[1:], strict=False)
    ]
    if min(gaps, default=0.0) < line_height * policy.minimum_axis_separation_line_heights:
        raise KQKDWordBoxError("KQKD unit-derived axes are not distinctly separated")

    role_by_index = {match.line.index: match for match in role_matches}
    role_lines = tuple(match.line for match in role_matches)
    role_pairs = _minimum_bijection(unit_lines, role_lines)
    if any(
        abs(unit.x_center - role.x_center)
        > line_height * policy.maximum_role_to_unit_center_distance_line_heights
        for unit, role in role_pairs
    ):
        raise KQKDWordBoxError("KQKD role/unit header geometry is not locally bounded")

    groups_by_semantic = {match.semantic: match for match in group_matches}
    quarter_group = groups_by_semantic["QUARTER"]
    ytd_group = groups_by_semantic["YTD"]
    best_grouping: tuple[float, frozenset[int]] | None = None
    for quarter_indices in itertools.combinations(range(4), 2):
        quarter_set = frozenset(quarter_indices)
        cost = sum(
            abs(unit_lines[index].x_center - quarter_group.line.x_center)
            if index in quarter_set
            else abs(unit_lines[index].x_center - ytd_group.line.x_center)
            for index in range(4)
        )
        candidate = (cost, quarter_set)
        if best_grouping is None or candidate < best_grouping:
            best_grouping = candidate
    assert best_grouping is not None
    quarter_indices = best_grouping[1]

    bound = []
    for ordinal, ((unit_line, role_line), unit_record) in enumerate(
        zip(role_pairs, ordered_units, strict=True), start=1
    ):
        role = role_by_index[role_line.index]
        group = "QUARTER" if ordinal - 1 in quarter_indices else "YTD"
        group_match = groups_by_semantic[group]
        if (
            abs(unit_line.x_center - group_match.line.x_center)
            > line_height * policy.maximum_group_to_axis_center_distance_line_heights
        ):
            raise KQKDWordBoxError("KQKD group/axis header geometry is not locally bounded")
        unit_anchor = unit_record[1]
        period_start, period_end, period_type = _period_dates(
            quarter, report_year, role.semantic, group
        )
        bound.append(
            KQKDAxisBinding(
                ordinal=ordinal,
                axis_id=f"value-{ordinal}",
                axis_right_edge=unit_line.x_right,
                group=KQKDAxisGroup(group),
                raw_group_header=group_match.line.text,
                group_header_line_index=group_match.line.index,
                raw_role_header=role.line.text,
                role_header_line_index=role.line.index,
                current_or_comparative=role.semantic,
                raw_unit_text=unit_line.text,
                unit_line_index=unit_line.index,
                canonical_unit=unit_anchor.canonical,
                unit_multiplier=unit_anchor.multiplier,
                period_start=period_start,
                period_end=period_end,
                period_type=period_type,
                duration_months=3 if group == "QUARTER" else quarter * 3,
                schema_export_candidate=group == "QUARTER",
                header_bbox=_union([group_match.line, role.line, unit_line]),
                unit_bbox=unit_line.bbox,
                evidence=(
                    "group semantics matched from the visible parent header",
                    "current/comparative role matched from the visible child header, not x-order",
                    "period year and quarter parsed from the visible report-period title",
                    "axis position and unit bound from the visible axis-local unit word box",
                    (
                        "quarter DURATION axis is eligible for schema export"
                        if group == "QUARTER"
                        else "YTD axis is retained as provenance and is not collapsed into quarter"
                    ),
                ),
            )
        )
    group_roles = {
        group: {axis.current_or_comparative for axis in bound if axis.group == group}
        for group in KQKDAxisGroup
    }
    if any(roles != {"CURRENT", "COMPARATIVE"} for roles in group_roles.values()):
        raise KQKDWordBoxError("each KQKD group must contain current and comparative axes")
    return scope_match.semantic, title, period_line, tuple(bound)


def _numeric_only(text: str) -> bool:
    normalized = normalize_text(text)
    return bool(
        normalized
        and not any(char.isalpha() for char in normalized)
        and _NUMERIC.fullmatch(normalized)
    )


def _note_like(text: str) -> bool:
    return bool(_NOTE_REFERENCE.fullmatch(normalize_text(text).replace(" ", "").strip(". ")))


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


def _nearest_anchor(line: _Line, centers: list[float], tolerance: float) -> int | None:
    if not centers:
        return None
    distances = [abs(line.y_center - center) for center in centers]
    index = min(range(len(distances)), key=distances.__getitem__)
    return index if distances[index] <= tolerance else None


def _source_ids(page_tag: str, lines: list[_Line]) -> tuple[str, ...]:
    return tuple(
        f"{page_tag}:line-{line.index:04d}" for line in sorted(lines, key=lambda item: item.index)
    )


def _join_financial_tokens(lines: list[_Line]) -> str | None:
    if not lines:
        return None
    return " ".join(line.text for line in sorted(lines, key=lambda item: item.bbox.x0))


def _reconstruct_rows(
    lines: tuple[_Line, ...],
    axes: tuple[KQKDAxisBinding, ...],
    policy: KQKDWordBoxPolicy,
    line_height: float,
    *,
    page_tag: str,
) -> tuple[
    tuple[KQKDLogicalRow, ...],
    tuple[int, ...],
    tuple[int, ...],
    BoundingBox,
]:
    unit_indices = {axis.unit_line_index for axis in axes}
    body_start = max(line.bbox.y1 for line in lines if line.index in unit_indices)
    body = [line for line in lines if line.y_center > body_start]
    axis_edges = [axis.axis_right_edge for axis in axes]
    axis_gaps = [right - left for left, right in zip(axis_edges, axis_edges[1:], strict=False)]
    typical_gap = statistics.median(axis_gaps)
    maximum_distance = typical_gap * policy.axis_right_edge_max_distance_ratio
    per_axis: list[list[_Line]] = [[] for _axis in axes]
    numeric_candidates = [line for line in body if _numeric_only(line.text)]
    unassigned = []
    for line in numeric_candidates:
        distances = [abs(line.x_right - edge) for edge in axis_edges]
        closest = min(range(len(distances)), key=distances.__getitem__)
        if (
            distances[closest] <= maximum_distance
            and line.x_right
            <= axis_edges[closest] + line_height * policy.axis_right_overrun_line_heights
        ):
            per_axis[closest].append(line)
        else:
            unassigned.append(line)
    assigned = [line for axis_lines in per_axis for line in axis_lines]
    if not assigned:
        raise KQKDWordBoxError("KQKD body contains no axis-assigned financial cells")
    anchor_groups = _clusters(assigned, line_height * policy.row_anchor_cluster_line_heights)
    centers = [statistics.fmean(line.y_center for line in group) for group in anchor_groups]
    last_center = centers[-1]

    label_boundary = axes[0].axis_right_edge - (typical_gap * policy.label_boundary_axis_gap_ratio)
    assigned_or_unassigned = {line.index for line in assigned + unassigned}
    note_lines = [
        line
        for line in body
        if line.index not in assigned_or_unassigned
        if line.y_center <= last_center + line_height * policy.note_attach_line_heights
        and line.x_right < label_boundary
        and _note_like(line.text)
    ]
    excluded = {line.index for line in assigned + unassigned + note_lines}
    label_lines = [
        line
        for line in body
        if line.index not in excluded
        and line.y_center
        <= last_center + line_height * policy.label_below_anchor_tolerance_line_heights
        and line.x_right < label_boundary
        and not _numeric_only(line.text)
    ]

    assignments: dict[int, int] = {}
    direct = line_height * policy.label_direct_attach_line_heights
    below = line_height * policy.label_below_anchor_tolerance_line_heights
    for line in label_lines:
        eligible = [
            index
            for index, center in enumerate(centers)
            if center >= line.y_center - below and center - line.y_center <= direct
        ]
        if eligible:
            assignments[line.index] = eligible[0]

    wrap = line_height * policy.wrapped_label_center_gap_line_heights
    ordered_labels = sorted(label_lines, key=lambda line: (line.y_center, line.bbox.x0))
    changed = True
    while changed:
        changed = False
        for position, line in enumerate(ordered_labels):
            if line.index in assignments:
                continue
            neighbors = []
            if position:
                neighbors.append(ordered_labels[position - 1])
            if position + 1 < len(ordered_labels):
                neighbors.append(ordered_labels[position + 1])
            candidates = {
                assignments[neighbor.index]
                for neighbor in neighbors
                if neighbor.index in assignments
                and abs(neighbor.y_center - line.y_center) <= wrap
                and centers[assignments[neighbor.index]] >= line.y_center - below
            }
            if len(candidates) == 1:
                assignments[line.index] = next(iter(candidates))
                changed = True

    note_assignments = {
        line.index: anchor
        for line in note_lines
        if (anchor := _nearest_anchor(line, centers, line_height * policy.note_attach_line_heights))
        is not None
    }
    proposals = []
    for ordinal, (anchor_lines, center) in enumerate(
        zip(anchor_groups, centers, strict=True), start=1
    ):
        anchor_index = ordinal - 1
        labels = sorted(
            (line for line in label_lines if assignments.get(line.index) == anchor_index),
            key=lambda line: (line.y_center, line.bbox.x0),
        )
        notes = sorted(
            (line for line in note_lines if note_assignments.get(line.index) == anchor_index),
            key=lambda line: line.bbox.x0,
        )
        value_lines = [
            sorted(
                (line for line in axis_lines if line in anchor_lines),
                key=lambda line: line.bbox.x0,
            )
            for axis_lines in per_axis
        ]
        cells: tuple[ParsedNumber, ...] = tuple(
            parse_financial_number(_join_financial_tokens(axis_lines)) for axis_lines in value_lines
        )
        warnings = []
        if not labels:
            warnings.append("numeric KQKD row has no attached visible label")
        if any(len(axis_lines) > 1 for axis_lines in value_lines):
            warnings.append("multiple OCR tokens reconstructed in one KQKD financial cell")
        if any(cell.observation is ObservationKind.INVALID for cell in cells):
            warnings.append("one or more KQKD financial cells are invalid")
        source_lines = labels + notes + [line for axis_lines in value_lines for line in axis_lines]
        proposals.append(
            KQKDLogicalRow(
                row_id=f"{page_tag}:row-{ordinal:04d}",
                ordinal=ordinal,
                row=ReaderRow(
                    source_row_ids=_source_ids(page_tag, source_lines),
                    label=normalize_text(" ".join(line.text for line in labels)),
                    note_reference=normalize_text(" ".join(line.text for line in notes)) or None,
                    cells=cells,
                ),
                y_anchor=center,
                label_bbox=_union(labels) if labels else None,
                note_bbox=_union(notes) if notes else None,
                value_bboxes=tuple(
                    _union(axis_lines) if axis_lines else None for axis_lines in value_lines
                ),
                label_line_indices=tuple(line.index for line in labels),
                note_line_indices=tuple(line.index for line in notes),
                value_line_indices=tuple(
                    tuple(line.index for line in axis_lines) for axis_lines in value_lines
                ),
                warnings=tuple(warnings),
            )
        )
    orphan_labels = tuple(line.index for line in label_lines if line.index not in assignments)
    table_lines = [
        line
        for proposal in proposals
        for source_id in proposal.row.source_row_ids
        for line in lines
        if line.index == int(source_id.rsplit("-", 1)[-1])
    ]
    return (
        tuple(proposals),
        tuple(line.index for line in sorted(unassigned, key=lambda item: item.index)),
        orphan_labels,
        _union(table_lines),
    )


def parse_kqkd_word_box_page(
    result_path: Path,
    policy: KQKDWordBoxPolicy,
    *,
    page_tag: str,
) -> ParsedKQKDWordBoxPage:
    """Reconstruct a hierarchical four-axis KQKD table from visible word boxes.

    Header roles are sealed before numeric rows are read. Equal quarter/YTD values
    therefore cannot collapse axes or influence period semantics.
    """

    input_path, lines = _load_lines(result_path, policy.minimum_line_score)
    line_height = float(statistics.median(line.height for line in lines))
    if line_height <= 0:
        raise KQKDWordBoxError("KQKD word-box line height is invalid")
    scope, title, period_line, axes = _bind_axes(lines, policy, line_height)
    rows, unassigned, orphan_labels, table_bbox = _reconstruct_rows(
        lines, axes, policy, line_height, page_tag=page_tag
    )
    return ParsedKQKDWordBoxPage(
        input_path=input_path,
        source_sha256=sha256_file(result_path),
        page_tag=page_tag,
        statement_title=title.text,
        statement_title_line_index=title.index,
        report_period_text=period_line.text,
        report_period_line_index=period_line.index,
        scope=scope,
        axes=axes,
        rows=rows,
        line_height=line_height,
        source_ocr_bbox=_union(list(lines)),
        table_bbox=table_bbox,
        unassigned_numeric_line_indices=unassigned,
        orphan_label_line_indices=orphan_labels,
        evidence=(
            "scope matched from the visible KQKD statement title",
            "four hierarchical axes bound before numeric body reconstruction",
            "quarter and YTD axes remain distinct regardless of equal cell values",
            "schema export is limited to the two visible quarter DURATION axes",
        ),
    )


__all__ = [
    "KQKDAxisBinding",
    "KQKDAxisGroup",
    "KQKDLogicalRow",
    "KQKDWordBoxError",
    "KQKDWordBoxPolicy",
    "ParsedKQKDWordBoxPage",
    "load_kqkd_word_box_policy",
    "parse_kqkd_word_box_page",
]
