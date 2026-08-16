"""DPI- and layout-adaptive row/column geometry for accounting tables.

The helpers in this module deliberately know nothing about banks, pages,
notes, families, or text aliases.  They infer their tolerances from the boxes
present on the page.  Semantic matchers remain responsible for deciding which
labels belong to a family; this module only resolves row and numeric-column
geometry.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from statistics import median
from typing import Any

__all__ = [
    "AdaptiveAccountingTableGeometryV1Error",
    "assign_numeric_row_v1",
    "build_multilevel_header_graph_v1",
    "cluster_numeric_rows_v1",
    "infer_numeric_column_centers_v1",
    "median_text_height_v1",
    "project_merged_header_tokens_v1",
    "row_affinity_v1",
]


class AdaptiveAccountingTableGeometryV1Error(ValueError):
    """One page supplied malformed or non-positive geometry."""


def _error(message: str) -> AdaptiveAccountingTableGeometryV1Error:
    return AdaptiveAccountingTableGeometryV1Error(message)


def _bbox(value: Any) -> tuple[int, int, int, int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or value[0] < 0
        or value[1] < 0
        or value[2] <= value[0]
        or value[3] <= value[1]
    ):
        raise _error("bbox must be four exact nonnegative positive-area integers")
    return value[0], value[1], value[2], value[3]


def median_text_height_v1(lines: Sequence[Mapping[str, Any]]) -> float:
    """Return the robust page-local text height used as the scale unit."""

    if not lines:
        raise _error("adaptive geometry requires a nonempty line axis")
    heights = []
    for line in lines:
        if type(line) is not dict or "bbox" not in line:
            raise _error("line must be one exact mapping with a bbox")
        _left, top, _right, bottom = _bbox(line["bbox"])
        heights.append(bottom - top)
    scale = float(median(heights))
    if scale <= 0:
        raise _error("median text height must be positive")
    return scale


def _union(boxes: Sequence[Any]) -> tuple[int, int, int, int]:
    parsed = [_bbox(value) for value in boxes]
    if not parsed:
        raise _error("row label must contain at least one bbox")
    return (
        min(box[0] for box in parsed),
        min(box[1] for box in parsed),
        max(box[2] for box in parsed),
        max(box[3] for box in parsed),
    )


def row_affinity_v1(
    label_boxes: Sequence[Any], candidate_bbox: Any, *, median_text_height: float
) -> float | None:
    """Score a candidate against a possibly wrapped label row.

    A score is returned only when the vertical intervals overlap or their gap
    is small relative to the page-local median glyph height.  The calculation
    has no absolute pixel tolerance, so the same rule works across DPI scales.
    """

    if type(median_text_height) is not float or median_text_height <= 0:
        raise _error("median text height must be one positive float")
    _lx0, ly0, _lx1, ly1 = _union(label_boxes)
    _cx0, cy0, _cx1, cy1 = _bbox(candidate_bbox)
    overlap = min(ly1, cy1) - max(ly0, cy0)
    gap = max(0, ly0 - cy1, cy0 - ly1)
    label_height = ly1 - ly0
    candidate_height = cy1 - cy0
    scale = max(median_text_height, min(label_height, median_text_height * 2), candidate_height)
    if gap > scale * 0.28:
        return None
    label_center = (ly0 + ly1) / 2
    candidate_center = (cy0 + cy1) / 2
    normalized_distance = abs(candidate_center - label_center) / scale
    if overlap <= 0 and normalized_distance > 0.9:
        return None
    overlap_ratio = max(0, overlap) / max(1, min(label_height, candidate_height))
    return overlap_ratio * 2.0 - normalized_distance


def _x_center(line: Mapping[str, Any]) -> float:
    left, _top, right, _bottom = _bbox(line["bbox"])
    return (left + right) / 2


def infer_numeric_column_centers_v1(
    lines: Sequence[Mapping[str, Any]],
    *,
    is_numeric: Callable[[Mapping[str, Any]], bool],
    page_width: int,
    minimum_x_ratio: float = 0.45,
    maximum_x_ratio: float = 0.96,
) -> list[float]:
    """Infer numeric lanes from repeated x centers using page-local scale."""

    if type(page_width) is not int or page_width <= 0:
        raise _error("page width must be one positive exact integer")
    if not 0 <= minimum_x_ratio < maximum_x_ratio <= 1:
        raise _error("numeric x ratios must be ordered inside [0, 1]")
    scale = median_text_height_v1(lines)
    candidates = [
        line
        for line in lines
        if is_numeric(line)
        and _bbox(line["bbox"])[0] > page_width * minimum_x_ratio
        and _bbox(line["bbox"])[0] < page_width * maximum_x_ratio
    ]
    tolerance = max(scale * 1.35, page_width * 0.012)
    clusters: list[list[float]] = []
    for center in sorted(_x_center(line) for line in candidates):
        target = next(
            (cluster for cluster in clusters if abs(center - float(median(cluster))) <= tolerance),
            None,
        )
        if target is None:
            clusters.append([center])
        else:
            target.append(center)
    repeated = [cluster for cluster in clusters if len(cluster) >= 2]
    selected = repeated if repeated else clusters
    return [float(median(cluster)) for cluster in selected]


def project_merged_header_tokens_v1(
    *,
    header_bbox: Any,
    tokens: Sequence[str],
    column_centers: Sequence[float],
    token_bboxes: Sequence[Any] | None = None,
) -> list[dict[str, Any]]:
    """Project a merged header onto body-derived columns.

    Word/token boxes are preferred.  If the OCR provider merged the entire
    header and no sub-boxes survive, an equal token/column count may be
    projected by reading order.  The latter is explicitly marked as an
    order-only proposal and therefore still needs period/accounting replay.
    """

    left, _top, right, _bottom = _bbox(header_bbox)
    if (
        not tokens
        or any(type(token) is not str or not token.strip() for token in tokens)
        or not column_centers
        or any(type(center) not in {int, float} for center in column_centers)
        or list(column_centers) != sorted(set(float(center) for center in column_centers))
    ):
        raise _error("merged header tokens or body-derived columns are invalid")
    centers = [float(center) for center in column_centers]
    if token_bboxes is not None:
        if len(token_bboxes) != len(tokens):
            raise _error("merged header token-box axis length drifted")
        assignments = []
        used: set[int] = set()
        for token, raw_box in zip(tokens, token_bboxes, strict=True):
            box = _bbox(raw_box)
            token_center = (box[0] + box[2]) / 2
            lane = min(range(len(centers)), key=lambda index: abs(token_center - centers[index]))
            if lane in used:
                raise _error("multiple merged-header tokens resolve to one numeric lane")
            used.add(lane)
            assignments.append(
                {
                    "column_ordinal": lane,
                    "geometry_status": "WORD_BOX_PROJECTED_TO_BODY_COLUMN",
                    "token": token,
                    "token_bbox": list(box),
                }
            )
        return sorted(assignments, key=lambda item: item["column_ordinal"])
    if len(tokens) != len(centers):
        raise _error("order-only merged header projection requires one token per body column")
    if centers[0] < left or centers[-1] > right:
        raise _error("merged header bbox does not span the inferred numeric columns")
    return [
        {
            "column_ordinal": ordinal,
            "geometry_status": "ORDER_ONLY_PROJECTED_TO_BODY_COLUMN_REQUIRES_REPLAY",
            "token": token,
            "token_bbox": None,
        }
        for ordinal, token in enumerate(tokens)
    ]


def _column_domains(centers: Sequence[float], *, page_width: int) -> list[tuple[float, float]]:
    if (
        type(page_width) is not int
        or page_width <= 0
        or not centers
        or any(type(center) not in {int, float} for center in centers)
    ):
        raise _error("header column centers or page width are invalid")
    parsed = [float(center) for center in centers]
    if parsed != sorted(set(parsed)) or parsed[0] < 0 or parsed[-1] > page_width:
        raise _error("header column centers must be unique, ordered, and on the page")
    if len(parsed) == 1:
        half_width = max(page_width * 0.08, 1.0)
        return [(max(0.0, parsed[0] - half_width), min(float(page_width), parsed[0] + half_width))]
    boundaries = [max(0.0, parsed[0] - (parsed[1] - parsed[0]) / 2)]
    boundaries.extend((left + right) / 2 for left, right in zip(parsed, parsed[1:], strict=False))
    boundaries.append(min(float(page_width), parsed[-1] + (parsed[-1] - parsed[-2]) / 2))
    return list(zip(boundaries, boundaries[1:], strict=False))


def _header_bands(cells: Sequence[dict[str, Any]], *, scale: float) -> list[dict[str, Any]]:
    """Cluster physical header baselines without collapsing adjacent levels."""

    bands: list[list[dict[str, Any]]] = []
    for cell in sorted(cells, key=lambda item: (item["bbox"][1], item["bbox"][0])):
        top, bottom = cell["bbox"][1], cell["bbox"][3]
        center = (top + bottom) / 2
        target = next(
            (
                band
                for band in bands
                if abs(
                    center - float(median((item["bbox"][1] + item["bbox"][3]) / 2 for item in band))
                )
                <= scale * 0.58
            ),
            None,
        )
        if target is None:
            bands.append([cell])
        else:
            target.append(cell)
    return [
        {
            "bottom": max(item["bbox"][3] for item in band),
            "center": float(median((item["bbox"][1] + item["bbox"][3]) / 2 for item in band)),
            "top": min(item["bbox"][1] for item in band),
        }
        for band in bands
    ]


def _span_score(
    bbox: tuple[int, int, int, int],
    *,
    start: int,
    stop: int,
    centers: Sequence[float],
    domains: Sequence[tuple[float, float]],
    lane_gap: float,
) -> float:
    left, _top, right, _bottom = bbox
    box_center = (left + right) / 2
    span_center = (centers[start] + centers[stop - 1]) / 2
    span_left = domains[start][0]
    span_right = domains[stop - 1][1]
    overflow = max(0.0, span_left - left) + max(0.0, right - span_right)
    contained_centers = {
        ordinal for ordinal, center in enumerate(centers) if left <= center <= right
    }
    excluded_contained = sum(not start <= ordinal < stop for ordinal in contained_centers)
    return (
        abs(box_center - span_center) / lane_gap
        + overflow / lane_gap
        + excluded_contained * 4.0
        + (stop - start - 1) * 0.06
    )


def _ordered_spans(
    cells: Sequence[dict[str, Any]],
    *,
    centers: Sequence[float],
    domains: Sequence[tuple[float, float]],
    lane_gap: float,
) -> tuple[list[tuple[int, int, float]], bool]:
    """Globally assign non-crossing contiguous spans to one header level."""

    ordered = sorted(cells, key=lambda item: (item["bbox"][0], item["bbox"][2]))
    lane_count = len(centers)
    if len(ordered) > lane_count:
        return [], True
    states: dict[int, tuple[float, list[tuple[int, int, float]]]] = {0: (0.0, [])}
    for cell in ordered:
        parsed = _bbox(cell["bbox"])
        next_states: dict[int, tuple[float, list[tuple[int, int, float]]]] = {}
        for prior_stop, (prior_score, prior_spans) in states.items():
            for start in range(prior_stop, lane_count):
                for stop in range(start + 1, lane_count + 1):
                    score = _span_score(
                        parsed,
                        start=start,
                        stop=stop,
                        centers=centers,
                        domains=domains,
                        lane_gap=lane_gap,
                    )
                    total = prior_score + score + (start - prior_stop) * 0.12
                    candidate = (total, [*prior_spans, (start, stop, score)])
                    existing = next_states.get(stop)
                    if existing is None or candidate[0] < existing[0]:
                        next_states[stop] = candidate
        states = next_states
    if not states:
        return [], True
    _final_stop, (_score, spans) = min(
        states.items(),
        key=lambda item: item[1][0] + (lane_count - item[0]) * 0.12,
    )
    return spans, False


def build_multilevel_header_graph_v1(
    header_lines: Sequence[Mapping[str, Any]],
    *,
    column_centers: Sequence[float],
    page_width: int,
    median_text_height: float | None = None,
) -> dict[str, Any]:
    """Build a body-anchored graph for multi-row and OCR-merged headers.

    The body numeric lanes are the geometric anchor.  Header cells are assigned
    contiguous, non-crossing column spans by a small global optimization rather
    than fixed pixels or equal-width slicing.  Optional ``tokens`` and
    ``token_bboxes`` on a line preserve OCR word boxes.  A token list without
    word boxes is projected only in the one-token-per-body-column case and is
    explicitly marked as requiring semantic/accounting replay.

    The graph deliberately does not decide whether two stacked texts are a
    wrapped phrase or distinct period/unit levels.  It exposes a continuation
    candidate and a containment edge; the family matcher must decide with text,
    period, unit, body values, and accounting equations.
    """

    if not header_lines:
        raise _error("multilevel header graph requires at least one header line")
    centers = [float(center) for center in column_centers]
    domains = _column_domains(centers, page_width=page_width)
    if median_text_height is None:
        scale = median_text_height_v1(header_lines)
    elif type(median_text_height) is float and median_text_height > 0:
        scale = median_text_height
    else:
        raise _error("multilevel header median text height must be one positive float")
    lane_gap = (
        float(median(right - left for left, right in zip(centers, centers[1:], strict=False)))
        if len(centers) > 1
        else max(scale * 4.0, page_width * 0.15)
    )

    cells: list[dict[str, Any]] = []
    ambiguities: list[dict[str, Any]] = []
    for ordinal, raw_line in enumerate(header_lines):
        if type(raw_line) is not dict:
            raise _error("header line must be one exact mapping")
        bbox = list(_bbox(raw_line.get("bbox")))
        source_index = raw_line.get("source_line_index")
        text = raw_line.get("vietocr_text")
        if type(source_index) is not int or type(text) is not str or not text.strip():
            raise _error("header line index/text drifted")
        tokens = raw_line.get("tokens")
        token_bboxes = raw_line.get("token_bboxes")
        if tokens is None:
            expanded = [(text, bbox, "BODY_COLUMN_SPAN_INFERRED")]
        else:
            if (
                type(tokens) is not list
                or not tokens
                or any(type(token) is not str or not token.strip() for token in tokens)
            ):
                raise _error("merged header tokens drifted")
            if token_bboxes is not None:
                if type(token_bboxes) is not list or len(token_bboxes) != len(tokens):
                    raise _error("merged header token boxes drifted")
                expanded = [
                    (token, list(_bbox(token_box)), "WORD_BOX_PROJECTED_TO_BODY_COLUMN")
                    for token, token_box in zip(tokens, token_bboxes, strict=True)
                ]
            elif len(tokens) == len(centers) and bbox[0] <= centers[0] <= centers[-1] <= bbox[2]:
                expanded = [
                    (
                        token,
                        [
                            int(round(domains[token_ordinal][0])),
                            bbox[1],
                            int(round(domains[token_ordinal][1])),
                            bbox[3],
                        ],
                        "ORDER_ONLY_PROJECTED_TO_BODY_COLUMN_REQUIRES_REPLAY",
                    )
                    for token_ordinal, token in enumerate(tokens)
                ]
                ambiguities.append(
                    {
                        "kind": "MERGED_HEADER_ORDER_ONLY_WITHOUT_WORD_BOXES",
                        "source_line_index": source_index,
                    }
                )
            else:
                expanded = [(" ".join(tokens), bbox, "MERGED_TEXT_REQUIRES_SEGMENTATION")]
                ambiguities.append(
                    {
                        "kind": "MERGED_HEADER_TOKEN_GRID_AMBIGUOUS",
                        "source_line_index": source_index,
                    }
                )
        for piece_ordinal, (piece_text, piece_bbox, status) in enumerate(expanded):
            cells.append(
                {
                    "bbox": piece_bbox,
                    "cell_id": f"header-cell-{ordinal + 1:04d}-{piece_ordinal + 1:02d}",
                    "geometry_status": status,
                    "source_line_index": source_index,
                    "text": piece_text,
                }
            )

    bands = _header_bands(cells, scale=scale)
    numeric_left = domains[0][0]
    numeric_right = domains[-1][1]
    for cell in cells:
        left, top, right, bottom = _bbox(cell["bbox"])
        covered_levels = [
            ordinal
            for ordinal, band in enumerate(bands)
            if top - scale * 0.2 <= band["center"] <= bottom + scale * 0.2
        ]
        if not covered_levels:
            covered_levels = [
                min(
                    range(len(bands)),
                    key=lambda ordinal: abs((top + bottom) / 2 - bands[ordinal]["center"]),
                )
            ]
        cell["level_start"] = min(covered_levels)
        cell["level_stop"] = max(covered_levels) + 1
        if right < numeric_left - lane_gap * 0.45 or left > numeric_right + lane_gap * 0.45:
            cell["column_start"] = None
            cell["column_stop"] = None
            cell["geometry_status"] = "STUB_HEADER_OUTSIDE_NUMERIC_COLUMNS"

    numeric_groups: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for cell in cells:
        if "column_start" not in cell:
            numeric_groups.setdefault((cell["level_start"], cell["level_stop"]), []).append(cell)
    for level_span, group in numeric_groups.items():
        ordered = sorted(group, key=lambda item: (item["bbox"][0], item["bbox"][2]))
        spans, failed = _ordered_spans(
            ordered,
            centers=centers,
            domains=domains,
            lane_gap=lane_gap,
        )
        if failed:
            ambiguities.append(
                {
                    "kind": "NON_CROSSING_COLUMN_SPAN_ASSIGNMENT_FAILED",
                    "level_start": level_span[0],
                    "level_stop": level_span[1],
                }
            )
            for cell in ordered:
                center = (cell["bbox"][0] + cell["bbox"][2]) / 2
                lane = min(range(len(centers)), key=lambda index: abs(center - centers[index]))
                cell["column_start"] = lane
                cell["column_stop"] = lane + 1
                cell["geometry_status"] = "NEAREST_COLUMN_FALLBACK_REQUIRES_REPLAY"
            continue
        for cell, (start, stop, score) in zip(ordered, spans, strict=True):
            cell["column_start"] = start
            cell["column_stop"] = stop
            cell["span_score"] = round(score, 8)
            if score > 1.25:
                ambiguities.append(
                    {
                        "cell_id": cell["cell_id"],
                        "kind": "LOW_CONFIDENCE_COLUMN_SPAN",
                    }
                )

    edges: list[dict[str, Any]] = []
    continuation_candidates: list[dict[str, Any]] = []
    numeric_cells = [cell for cell in cells if cell["column_start"] is not None]
    for child in numeric_cells:
        parents = [
            parent
            for parent in numeric_cells
            if parent["level_stop"] <= child["level_start"]
            and parent["column_start"] <= child["column_start"]
            and parent["column_stop"] >= child["column_stop"]
        ]
        if parents:
            closest_level = max(parent["level_stop"] for parent in parents)
            closest = [parent for parent in parents if parent["level_stop"] == closest_level]
            smallest_width = min(
                parent["column_stop"] - parent["column_start"] for parent in closest
            )
            closest = [
                parent
                for parent in closest
                if parent["column_stop"] - parent["column_start"] == smallest_width
            ]
            if len(closest) == 1:
                parent = closest[0]
                edges.append(
                    {
                        "child_cell_id": child["cell_id"],
                        "parent_cell_id": parent["cell_id"],
                        "relation": "CONTAINING_COLUMN_SPAN_ON_PRECEDING_HEADER_LEVEL",
                    }
                )
                if (
                    parent["column_start"] == child["column_start"]
                    and parent["column_stop"] == child["column_stop"]
                    and child["level_start"] == parent["level_stop"]
                ):
                    gap = child["bbox"][1] - parent["bbox"][3]
                    if gap <= scale * 0.45:
                        continuation_candidates.append(
                            {
                                "lower_cell_id": child["cell_id"],
                                "relation": "STACKED_SAME_SPAN_TEXT_REQUIRES_SEMANTIC_DECISION",
                                "upper_cell_id": parent["cell_id"],
                            }
                        )
            else:
                ambiguities.append(
                    {
                        "cell_id": child["cell_id"],
                        "kind": "MULTIPLE_EQUAL_GEOMETRIC_PARENTS",
                    }
                )

    result_cells = sorted(
        cells,
        key=lambda item: (
            item["level_start"],
            -1 if item["column_start"] is None else item["column_start"],
            item["bbox"][0],
            item["cell_id"],
        ),
    )
    return {
        "ambiguities": ambiguities,
        "cells": result_cells,
        "column_centers": centers,
        "continuation_candidates": continuation_candidates,
        "edges": edges,
        "format_version": "ADAPTIVE_ACCOUNTING_MULTILEVEL_HEADER_GRAPH_V1",
        "levels": [
            {
                "bottom": band["bottom"],
                "level_ordinal": ordinal,
                "top": band["top"],
            }
            for ordinal, band in enumerate(bands)
        ],
        "status": "GEOMETRY_GRAPH_WITH_REPLAY_REQUIRED"
        if ambiguities
        else "RESOLVED_GEOMETRY_GRAPH",
    }


def assign_numeric_row_v1(
    lines: Sequence[Mapping[str, Any]],
    *,
    label_boxes: Sequence[Any],
    is_numeric: Callable[[Mapping[str, Any]], bool],
    page_width: int,
    minimum_x_ratio: float = 0.47,
    maximum_x_ratio: float = 0.94,
) -> list[Mapping[str, Any]]:
    """Assign at most one numeric cell per inferred lane to one label row."""

    scale = median_text_height_v1(lines)
    centers = infer_numeric_column_centers_v1(
        lines,
        is_numeric=is_numeric,
        page_width=page_width,
        minimum_x_ratio=minimum_x_ratio,
        maximum_x_ratio=maximum_x_ratio,
    )
    lane_tolerance = (
        max(scale * 1.6, min(b - a for a, b in zip(centers, centers[1:], strict=False)) * 0.42)
        if len(centers) > 1
        else scale * 2.5
    )
    by_lane: dict[int, tuple[float, Mapping[str, Any]]] = {}
    for line in lines:
        left, _top, _right, _bottom = _bbox(line["bbox"])
        if (
            not is_numeric(line)
            or left <= page_width * minimum_x_ratio
            or left >= page_width * maximum_x_ratio
        ):
            continue
        affinity = row_affinity_v1(
            label_boxes,
            line["bbox"],
            median_text_height=scale,
        )
        if affinity is None or not centers:
            continue
        center = _x_center(line)
        lane = min(range(len(centers)), key=lambda index: abs(center - centers[index]))
        if abs(center - centers[lane]) > lane_tolerance:
            continue
        prior = by_lane.get(lane)
        if prior is None or affinity > prior[0]:
            by_lane[lane] = (affinity, line)
    return [by_lane[lane][1] for lane in sorted(by_lane)]


def cluster_numeric_rows_v1(
    lines: Sequence[Mapping[str, Any]],
    *,
    is_numeric: Callable[[Mapping[str, Any]], bool],
    start_index: int,
    stop_index: int,
    page_width: int,
    minimum_x_ratio: float = 0.47,
    maximum_x_ratio: float = 0.94,
) -> list[list[Mapping[str, Any]]]:
    """Cluster right-side numeric cells into adaptive horizontal row bands."""

    if type(start_index) is not int or type(stop_index) is not int or stop_index <= start_index:
        raise _error("numeric row source-index interval is invalid")
    scale = median_text_height_v1(lines)
    candidates = [
        line
        for line in lines
        if start_index < line["source_line_index"] < stop_index
        and page_width * minimum_x_ratio < _bbox(line["bbox"])[0] < page_width * maximum_x_ratio
        and is_numeric(line)
    ]
    rows: list[list[Mapping[str, Any]]] = []
    for line in sorted(
        candidates, key=lambda item: (_bbox(item["bbox"])[1], _bbox(item["bbox"])[0])
    ):
        _left, top, _right, bottom = _bbox(line["bbox"])
        center = (top + bottom) / 2
        target = next(
            (
                row
                for row in rows
                if abs(
                    center
                    - float(
                        median(
                            (_bbox(item["bbox"])[1] + _bbox(item["bbox"])[3]) / 2 for item in row
                        )
                    )
                )
                <= scale * 0.55
            ),
            None,
        )
        if target is None:
            rows.append([line])
        else:
            target.append(line)
    return [sorted(row, key=_x_center) for row in rows]
