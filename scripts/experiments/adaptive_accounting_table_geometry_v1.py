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
