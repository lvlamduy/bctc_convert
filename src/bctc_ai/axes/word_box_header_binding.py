from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Protocol

import yaml
from rapidfuzz.fuzz import ratio

from bctc_ai.axes.header_binding import HeaderBinding
from bctc_ai.core.contracts import BoundingBox
from bctc_ai.core.text import normalize_text, parse_vietnamese_dates, retrieval_key
from bctc_ai.evaluation.word_box_rows import GeometryAxis


class WordBoxHeaderBindingError(RuntimeError):
    pass


class _HeaderGeometry(Protocol):
    axes: tuple[GeometryAxis, ...]
    line_height: float


@dataclass(frozen=True)
class UnitAnchor:
    text: str
    key: str
    canonical: str
    multiplier: int


@dataclass(frozen=True)
class WordBoxHeaderBindingPolicy:
    source_path: Path
    statement_period_types: dict[str, str]
    maximum_axis_right_edge_drift_line_heights: float
    maximum_unit_vertical_distance_line_heights: float
    maximum_unit_axis_right_edge_distance_line_heights: float
    maximum_unit_tokens: int
    minimum_unit_similarity: float
    minimum_distinct_semantics_margin: float
    unit_anchors: tuple[UnitAnchor, ...]
    required_roles: dict[str, int]
    forbidden_inputs: tuple[str, ...]


@dataclass(frozen=True)
class BoundWordBoxAxis:
    ordinal: int
    axis_id: str
    axis_right_edge: float
    header_line_index: int
    raw_period_header: str
    header_bbox: BoundingBox
    raw_unit_text: str
    unit_line_index: int
    unit_bbox: BoundingBox
    canonical_unit: str
    unit_multiplier: int
    matched_unit_anchor: str
    unit_similarity: float
    distinct_semantics_margin: float
    period_start: date
    period_end: date
    period_type: str
    current_or_comparative: str
    evidence: tuple[str, ...]

    def as_header_binding(self) -> HeaderBinding:
        return HeaderBinding(
            axis_id=self.axis_id,
            raw_header=self.raw_period_header,
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
class BoundWordBoxTableHeaders:
    statement_type: str
    axes: tuple[BoundWordBoxAxis, ...]
    evidence: tuple[str, ...]

    @property
    def header_bindings(self) -> tuple[HeaderBinding, ...]:
        return tuple(axis.as_header_binding() for axis in self.axes)


@dataclass(frozen=True)
class _OCRLine:
    index: int
    text: str
    score: float
    bbox: BoundingBox

    @property
    def x_right(self) -> float:
        return self.bbox.x1

    @property
    def y_center(self) -> float:
        return (self.bbox.y0 + self.bbox.y1) / 2


@dataclass(frozen=True)
class _UnitMatch:
    line: _OCRLine
    anchor: UnitAnchor
    similarity: float
    distinct_semantics_margin: float


def _positive_float(mapping: dict[str, Any], name: str) -> float:
    value = mapping.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise WordBoxHeaderBindingError(f"invalid positive header-binding setting: {name}")
    return float(value)


def load_word_box_header_binding_policy(path: Path) -> WordBoxHeaderBindingPolicy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise WordBoxHeaderBindingError(f"cannot load word-box header policy: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 1
        or payload.get("policy") != "VISIBLE_WORD_BOX_TABLE_HEADER_BINDING_V1"
        or payload.get("geometry_authority") != "PP_OCRV6_WORD_BOXES"
        or payload.get("role_assignment") != "PARSED_DATE_RECENCY_NOT_HORIZONTAL_ORDER_OR_VALUE"
    ):
        raise WordBoxHeaderBindingError("word-box header-binding identity drifted")

    period_types = payload.get("supported_statement_period_types")
    geometry = payload.get("header_geometry")
    unit_matching = payload.get("unit_matching")
    required_roles = payload.get("required_roles")
    forbidden_inputs = payload.get("forbidden_inputs")
    if (
        not isinstance(period_types, dict)
        or not period_types
        or not isinstance(geometry, dict)
        or not isinstance(unit_matching, dict)
        or not isinstance(required_roles, dict)
        or required_roles != {"CURRENT": 1, "COMPARATIVE": 1}
        or not isinstance(forbidden_inputs, list)
    ):
        raise WordBoxHeaderBindingError("word-box header-binding policy is incomplete")
    required_forbidden = {
        "numeric_cell_text_or_value_as_period_unit_feature",
        "numeric_value_magnitude",
        "historical_or_mongodb_values",
        "template_labels_or_report_norm_ids",
        "human_review_period_answers",
        "horizontal_position_as_period_role",
    }
    if set(forbidden_inputs) != required_forbidden:
        raise WordBoxHeaderBindingError("word-box header-binding forbidden inputs drifted")
    if any(value != "SNAPSHOT" for value in period_types.values()):
        raise WordBoxHeaderBindingError("only explicit snapshot semantics are supported in v1")

    maximum_tokens = geometry.get("maximum_unit_tokens")
    if (
        isinstance(maximum_tokens, bool)
        or not isinstance(maximum_tokens, int)
        or maximum_tokens < 1
    ):
        raise WordBoxHeaderBindingError("maximum_unit_tokens must be a positive integer")
    minimum_similarity = unit_matching.get("minimum_similarity")
    minimum_margin = unit_matching.get("minimum_distinct_semantics_margin")
    if (
        isinstance(minimum_similarity, bool)
        or not isinstance(minimum_similarity, (int, float))
        or not 0 < float(minimum_similarity) <= 1
        or isinstance(minimum_margin, bool)
        or not isinstance(minimum_margin, (int, float))
        or not 0 < float(minimum_margin) <= 1
    ):
        raise WordBoxHeaderBindingError("unit similarity gates are invalid")
    raw_anchors = unit_matching.get("anchors")
    if not isinstance(raw_anchors, list) or not raw_anchors:
        raise WordBoxHeaderBindingError("unit anchor vocabulary is empty")
    anchors: list[UnitAnchor] = []
    for raw in raw_anchors:
        if not isinstance(raw, dict):
            raise WordBoxHeaderBindingError("unit anchor must be a mapping")
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
            raise WordBoxHeaderBindingError("unit anchor is invalid")
        anchors.append(UnitAnchor(text, retrieval_key(text), canonical, multiplier))

    return WordBoxHeaderBindingPolicy(
        source_path=path.resolve(),
        statement_period_types={str(key): str(value) for key, value in period_types.items()},
        maximum_axis_right_edge_drift_line_heights=_positive_float(
            geometry, "maximum_axis_right_edge_drift_line_heights"
        ),
        maximum_unit_vertical_distance_line_heights=_positive_float(
            geometry, "maximum_unit_vertical_distance_line_heights"
        ),
        maximum_unit_axis_right_edge_distance_line_heights=_positive_float(
            geometry, "maximum_unit_axis_right_edge_distance_line_heights"
        ),
        maximum_unit_tokens=maximum_tokens,
        minimum_unit_similarity=float(minimum_similarity),
        minimum_distinct_semantics_margin=float(minimum_margin),
        unit_anchors=tuple(anchors),
        required_roles={str(key): int(value) for key, value in required_roles.items()},
        forbidden_inputs=tuple(str(value) for value in forbidden_inputs),
    )


def _load_lines(path: Path) -> tuple[_OCRLine, ...]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WordBoxHeaderBindingError(f"cannot read PP-OCRv6 result: {path}") from exc
    texts = payload.get("rec_texts")
    scores = payload.get("rec_scores")
    boxes = payload.get("rec_boxes")
    if (
        not all(isinstance(value, list) for value in (texts, scores, boxes))
        or len({len(texts), len(scores), len(boxes)}) != 1
    ):
        raise WordBoxHeaderBindingError("PP-OCRv6 result axes are incomplete")
    lines = []
    for index, (text, score, box) in enumerate(zip(texts, scores, boxes, strict=True)):
        if not isinstance(box, list) or len(box) != 4:
            raise WordBoxHeaderBindingError(f"line {index} has no four-coordinate box")
        bbox = BoundingBox(*(float(value) for value in box))
        if bbox.x1 <= bbox.x0 or bbox.y1 <= bbox.y0:
            raise WordBoxHeaderBindingError(f"line {index} has a degenerate box")
        lines.append(_OCRLine(index, normalize_text(str(text)), float(score), bbox))
    return tuple(lines)


def _unit_semantics(anchor: UnitAnchor) -> tuple[str, int]:
    return anchor.canonical, anchor.multiplier


def _best_unit_match(
    *,
    axis: GeometryAxis,
    header_line: _OCRLine,
    lines: tuple[_OCRLine, ...],
    line_height: float,
    policy: WordBoxHeaderBindingPolicy,
) -> _UnitMatch:
    candidates: list[tuple[float, float, _OCRLine, UnitAnchor, float]] = []
    for line in lines:
        if line.index == header_line.index:
            continue
        key = retrieval_key(line.text)
        if (
            not key
            or any(character.isdigit() for character in key)
            or len(key.split()) > policy.maximum_unit_tokens
        ):
            continue
        vertical_distance = abs(line.y_center - header_line.y_center) / line_height
        horizontal_distance = abs(line.x_right - axis.right_edge) / line_height
        if (
            vertical_distance > policy.maximum_unit_vertical_distance_line_heights
            or horizontal_distance > policy.maximum_unit_axis_right_edge_distance_line_heights
        ):
            continue
        for anchor in policy.unit_anchors:
            similarity = ratio(key, anchor.key) / 100
            candidates.append((similarity, -vertical_distance, line, anchor, horizontal_distance))
    if not candidates:
        raise WordBoxHeaderBindingError(f"axis {axis.axis_id} has no bounded visible unit")
    candidates.sort(key=lambda item: (-item[0], -item[1], item[4], item[2].index, item[3].text))
    best_similarity, _negative_vertical, best_line, best_anchor, _horizontal = candidates[0]
    if best_similarity < policy.minimum_unit_similarity:
        raise WordBoxHeaderBindingError(f"axis {axis.axis_id} has no bounded visible unit")
    best_semantics = _unit_semantics(best_anchor)
    competing = [item[0] for item in candidates if _unit_semantics(item[3]) != best_semantics]
    runner_up = max(competing, default=0.0)
    margin = best_similarity - runner_up
    if margin < policy.minimum_distinct_semantics_margin:
        raise WordBoxHeaderBindingError(
            f"axis {axis.axis_id} unit semantics are ambiguous at margin {margin:.6f}"
        )
    return _UnitMatch(
        line=best_line,
        anchor=best_anchor,
        similarity=best_similarity,
        distinct_semantics_margin=margin,
    )


def bind_word_box_visible_headers(
    result_path: Path,
    geometry: _HeaderGeometry,
    policy: WordBoxHeaderBindingPolicy,
    *,
    statement_type: str,
) -> BoundWordBoxTableHeaders:
    """Bind periods and units from visible word boxes without reading values."""

    period_type = policy.statement_period_types.get(statement_type)
    if period_type is None:
        raise WordBoxHeaderBindingError(
            f"statement type {statement_type!r} has no explicit v1 period semantics"
        )
    if not geometry.axes or geometry.line_height <= 0:
        raise WordBoxHeaderBindingError("reconstructed header geometry is empty")
    lines = _load_lines(result_path)
    by_index = {line.index: line for line in lines}
    provisional: list[tuple[int, GeometryAxis, _OCRLine, date, _UnitMatch]] = []
    for ordinal, axis in enumerate(geometry.axes):
        header = by_index.get(axis.header_line_index)
        if header is None:
            raise WordBoxHeaderBindingError(
                f"axis {axis.axis_id} header line {axis.header_line_index} is absent"
            )
        if normalize_text(axis.raw_header) != header.text:
            raise WordBoxHeaderBindingError(f"axis {axis.axis_id} raw header drifted")
        if (
            abs(header.x_right - axis.right_edge) / geometry.line_height
            > policy.maximum_axis_right_edge_drift_line_heights
        ):
            raise WordBoxHeaderBindingError(f"axis {axis.axis_id} right edge drifted")
        dates = tuple(dict.fromkeys(parse_vietnamese_dates(header.text)))
        if len(dates) != 1:
            raise WordBoxHeaderBindingError(
                f"axis {axis.axis_id} must contain exactly one visible valid date"
            )
        unit = _best_unit_match(
            axis=axis,
            header_line=header,
            lines=lines,
            line_height=geometry.line_height,
            policy=policy,
        )
        provisional.append((ordinal, axis, header, dates[0], unit))

    dates = [item[3] for item in provisional]
    if len(set(dates)) != len(dates) or len(dates) != sum(policy.required_roles.values()):
        raise WordBoxHeaderBindingError("visible period dates do not support unique required roles")
    latest = max(dates)
    roles = ["CURRENT" if item[3] == latest else "COMPARATIVE" for item in provisional]
    counts = {role: roles.count(role) for role in policy.required_roles}
    if counts != policy.required_roles:
        raise WordBoxHeaderBindingError(
            f"parsed dates do not satisfy required period roles: {counts}"
        )

    bound = []
    for role, (ordinal, axis, header, period_end, unit) in zip(roles, provisional, strict=True):
        bound.append(
            BoundWordBoxAxis(
                ordinal=ordinal,
                axis_id=axis.axis_id,
                axis_right_edge=axis.right_edge,
                header_line_index=header.index,
                raw_period_header=header.text,
                header_bbox=header.bbox,
                raw_unit_text=unit.line.text,
                unit_line_index=unit.line.index,
                unit_bbox=unit.line.bbox,
                canonical_unit=unit.anchor.canonical,
                unit_multiplier=unit.anchor.multiplier,
                matched_unit_anchor=unit.anchor.text,
                unit_similarity=round(unit.similarity, 6),
                distinct_semantics_margin=round(unit.distinct_semantics_margin, 6),
                period_start=period_end,
                period_end=period_end,
                period_type=period_type,
                current_or_comparative=role,
                evidence=(
                    "period parsed from the axis-local visible header",
                    "current/comparative role assigned by parsed date, not x-order or values",
                    "unit matched inside the bounded axis-local visible header band",
                    f"raw unit retained as {unit.line.text!r}",
                ),
            )
        )
    return BoundWordBoxTableHeaders(
        statement_type=statement_type,
        axes=tuple(bound),
        evidence=(
            "all required period roles resolved from unique visible dates",
            "numeric cells, history, schema IDs and human review were not inputs",
        ),
    )
