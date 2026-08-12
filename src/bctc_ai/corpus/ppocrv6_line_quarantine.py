"""Pure PP-OCR line quarantine before strict word-box normalization."""

from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any

from bctc_ai.corpus.wave1_role_b_word_box_normalization import (
    canonical_payload_sha256,
    normalize_ppocrv6_word_boxes,
)
from bctc_ai.ocr.ppocrv6_page_session import (
    PPOCRV6PageSessionError,
    validate_ppocrv6_payload,
)

__all__ = [
    "ALIGNED_LINE_AXES",
    "LINE_QUARANTINE_LEDGER_FORMAT",
    "PPOCRV6LineQuarantineError",
    "build_ppocrv6_page_outlying_child_line_quarantine",
    "validate_ppocrv6_page_outlying_child_line_quarantine",
]


class PPOCRV6LineQuarantineError(RuntimeError):
    """The geometry-only line quarantine cannot be built or replayed safely."""


ALIGNED_LINE_AXES = (
    "dt_polys",
    "rec_boxes",
    "rec_polys",
    "rec_scores",
    "rec_texts",
    "text_word",
    "text_word_boxes",
    "textline_orientation_angles",
)
LINE_QUARANTINE_LEDGER_FORMAT = "PPOCRV6_PAGE_OUTLYING_CHILD_WHOLE_LINE_QUARANTINE_LEDGER_V1"

_MAXIMUM_PER_EDGE_OVERSHOOT_PIXELS = 1
_REASON_PAGE_OVERSHOOT = "PAGE_OVERSHOOT_GT_1PX"
_REASON_NONPOSITIVE = "POST_CLIP_NONPOSITIVE"
_REASON_OUTSIDE_PARENT = "POST_CLIP_OUTSIDE_PARENT_REC_BOX"
_REASON_ORDER = (
    _REASON_PAGE_OVERSHOOT,
    _REASON_NONPOSITIVE,
    _REASON_OUTSIDE_PARENT,
)
_RAW_PROVIDER_FIELDS = frozenset(
    {
        "dt_polys",
        "model_settings",
        "page_index",
        "rec_boxes",
        "rec_polys",
        "rec_scores",
        "rec_texts",
        "return_word_box",
        "text_det_params",
        "text_rec_score_thresh",
        "text_type",
        "text_word",
        "text_word_boxes",
        "textline_orientation_angles",
    }
)


def _positive_dimension(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise PPOCRV6LineQuarantineError(f"{label} must be a positive integer")
    return value


def _finite_positive_box(value: Any, label: str) -> list[int | float]:
    if not isinstance(value, list) or len(value) != 4:
        raise PPOCRV6LineQuarantineError(f"{label} must be [x0, y0, x1, y1]")
    box: list[int | float] = []
    for coordinate in value:
        if (
            isinstance(coordinate, bool)
            or not isinstance(coordinate, (int, float))
            or not isfinite(coordinate)
        ):
            raise PPOCRV6LineQuarantineError(
                f"{label} coordinates must be finite non-boolean numbers"
            )
        box.append(coordinate)
    x0, y0, x1, y1 = box
    if not x0 < x1 or not y0 < y1:
        raise PPOCRV6LineQuarantineError(f"{label} must have positive area")
    return box


def _validated_parent_box(
    value: Any,
    *,
    line_index: int,
    pixel_width: int,
    pixel_height: int,
) -> list[int | float]:
    box = _finite_positive_box(value, f"parent rec_box on line {line_index}")
    x0, y0, x1, y1 = box
    if not 0 <= x0 < x1 <= pixel_width or not 0 <= y0 < y1 <= pixel_height:
        raise PPOCRV6LineQuarantineError(
            f"parent rec_box on line {line_index} must be page-contained"
        )
    return box


def _clip_to_page(
    box: list[int | float],
    *,
    pixel_width: int,
    pixel_height: int,
) -> tuple[list[int | float], dict[str, int | float]]:
    x0, y0, x1, y1 = box
    per_edge = {
        "left": max(0, -x0),
        "top": max(0, -y0),
        "right": max(0, x1 - pixel_width),
        "bottom": max(0, y1 - pixel_height),
    }
    clipped = [
        min(pixel_width, max(0, x0)),
        min(pixel_height, max(0, y0)),
        min(pixel_width, max(0, x1)),
        min(pixel_height, max(0, y1)),
    ]
    return clipped, per_edge


def _positive(box: list[int | float]) -> bool:
    return box[0] < box[2] and box[1] < box[3]


def _contained(
    box: list[int | float],
    parent: list[int | float],
) -> bool:
    return (
        parent[0] <= box[0] and parent[1] <= box[1] and box[2] <= parent[2] and box[3] <= parent[3]
    )


def _validate_provider_only_line_axes(
    axes: dict[str, list[Any]],
    *,
    pixel_width: int,
    pixel_height: int,
) -> None:
    for line_index, polygon in enumerate(axes["dt_polys"]):
        if not isinstance(polygon, list) or len(polygon) != 4:
            raise PPOCRV6LineQuarantineError(
                f"detection polygon on line {line_index} must be a quadrilateral"
            )
        points: list[tuple[int | float, int | float]] = []
        for point_index, point in enumerate(polygon):
            if not isinstance(point, list) or len(point) != 2:
                raise PPOCRV6LineQuarantineError(
                    f"detection polygon point {point_index} on line {line_index} must be [x, y]"
                )
            x, y = point
            if (
                isinstance(x, bool)
                or isinstance(y, bool)
                or not isinstance(x, (int, float))
                or not isinstance(y, (int, float))
                or not isfinite(x)
                or not isfinite(y)
            ):
                raise PPOCRV6LineQuarantineError(
                    f"detection polygon point {point_index} on line {line_index} "
                    "must contain finite non-boolean numbers"
                )
            if not 0 <= x <= pixel_width or not 0 <= y <= pixel_height:
                raise PPOCRV6LineQuarantineError(
                    f"detection polygon point {point_index} on line {line_index} "
                    "must be page-contained"
                )
            points.append((x, y))
        area_twice = abs(
            sum(
                points[index][0] * points[(index + 1) % 4][1]
                - points[(index + 1) % 4][0] * points[index][1]
                for index in range(4)
            )
        )
        if area_twice == 0:
            raise PPOCRV6LineQuarantineError(
                f"detection polygon on line {line_index} must be nondegenerate"
            )

    for line_index, angle in enumerate(axes["textline_orientation_angles"]):
        if isinstance(angle, bool) or not isinstance(angle, (int, float)) or not isfinite(angle):
            raise PPOCRV6LineQuarantineError(
                f"text-line orientation angle on line {line_index} "
                "must be a finite non-boolean number"
            )


def _validated_line_geometry(
    raw_payload: Any,
    *,
    pixel_width: int,
    pixel_height: int,
) -> tuple[int, list[list[int | float]], list[list[list[int | float]]]]:
    if not isinstance(raw_payload, dict):
        raise PPOCRV6LineQuarantineError("raw PP-OCR payload must be an object")
    if set(raw_payload) != _RAW_PROVIDER_FIELDS:
        raise PPOCRV6LineQuarantineError("raw PP-OCR provider field set differs")
    axes: dict[str, list[Any]] = {}
    for axis in ALIGNED_LINE_AXES:
        value = raw_payload.get(axis)
        if not isinstance(value, list):
            raise PPOCRV6LineQuarantineError(f"raw PP-OCR aligned line axis must be a list: {axis}")
        axes[axis] = value
    counts = {axis: len(value) for axis, value in axes.items()}
    if len(set(counts.values())) != 1:
        raise PPOCRV6LineQuarantineError(f"raw PP-OCR aligned line axis lengths differ: {counts}")
    _validate_provider_only_line_axes(
        axes,
        pixel_width=pixel_width,
        pixel_height=pixel_height,
    )

    line_count = counts[ALIGNED_LINE_AXES[0]]
    parent_boxes: list[list[int | float]] = []
    word_box_lines: list[list[list[int | float]]] = []
    for line_index in range(line_count):
        parent_boxes.append(
            _validated_parent_box(
                axes["rec_boxes"][line_index],
                line_index=line_index,
                pixel_width=pixel_width,
                pixel_height=pixel_height,
            )
        )
        raw_boxes = axes["text_word_boxes"][line_index]
        raw_words = axes["text_word"][line_index]
        if not isinstance(raw_boxes, list) or not isinstance(raw_words, list):
            raise PPOCRV6LineQuarantineError(
                f"raw PP-OCR word axes on line {line_index} must be lists"
            )
        if len(raw_boxes) != len(raw_words):
            raise PPOCRV6LineQuarantineError(
                f"raw PP-OCR word axis lengths differ on line {line_index}"
            )
        word_box_lines.append(
            [
                _finite_positive_box(
                    raw_box,
                    f"raw PP-OCR word box line {line_index} word {word_index}",
                )
                for word_index, raw_box in enumerate(raw_boxes)
            ]
        )

    sanitized = deepcopy(raw_payload)
    sanitized["text_word_boxes"] = [
        [deepcopy(parent_box) for _word in raw_words]
        for parent_box, raw_words in zip(parent_boxes, axes["text_word"], strict=True)
    ]
    try:
        validate_ppocrv6_payload(
            sanitized,
            pixel_width=pixel_width,
            pixel_height=pixel_height,
        )
    except PPOCRV6PageSessionError as error:
        raise PPOCRV6LineQuarantineError(
            "raw PP-OCR payload has a non-word-geometry structural failure"
        ) from error
    return line_count, parent_boxes, word_box_lines


def _quarantine_lines(
    raw_payload: dict[str, Any],
    *,
    pixel_width: int,
    pixel_height: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    line_count, parent_boxes, word_box_lines = _validated_line_geometry(
        raw_payload,
        pixel_width=pixel_width,
        pixel_height=pixel_height,
    )
    quarantined_lines: list[dict[str, Any]] = []
    quarantined_indexes: set[int] = set()

    for line_index, (parent_box, raw_boxes) in enumerate(
        zip(parent_boxes, word_box_lines, strict=True)
    ):
        offenders: list[dict[str, Any]] = []
        for word_index, raw_box in enumerate(raw_boxes):
            clipped_box, per_edge = _clip_to_page(
                raw_box,
                pixel_width=pixel_width,
                pixel_height=pixel_height,
            )
            page_outlying = any(amount > 0 for amount in per_edge.values())
            if not page_outlying:
                continue
            overshoot_exceeds_maximum = any(
                amount > _MAXIMUM_PER_EDGE_OVERSHOOT_PIXELS for amount in per_edge.values()
            )
            post_clip_positive = _positive(clipped_box)
            post_clip_contained = _contained(clipped_box, parent_box)
            reasons = []
            if overshoot_exceeds_maximum:
                reasons.append(_REASON_PAGE_OVERSHOOT)
            if not post_clip_positive:
                reasons.append(_REASON_NONPOSITIVE)
            if not post_clip_contained:
                reasons.append(_REASON_OUTSIDE_PARENT)
            if not reasons:
                continue
            offenders.append(
                {
                    "word_index": word_index,
                    "raw_box": deepcopy(raw_box),
                    "clipped_box": deepcopy(clipped_box),
                    "per_edge_overshoot_pixels": per_edge,
                    "evidence": {
                        "page_outlying": page_outlying,
                        "overshoot_exceeds_maximum": overshoot_exceeds_maximum,
                        "post_clip_positive": post_clip_positive,
                        "post_clip_contained_in_parent_rec_box": post_clip_contained,
                    },
                    "reasons": reasons,
                }
            )
        if offenders:
            quarantined_indexes.add(line_index)
            quarantined_lines.append(
                {
                    "line_index": line_index,
                    "parent_rec_box": deepcopy(parent_box),
                    "word_count": len(raw_boxes),
                    "reasons": [
                        reason
                        for reason in _REASON_ORDER
                        if any(reason in offender["reasons"] for offender in offenders)
                    ],
                    "offenders": offenders,
                }
            )

    retained = deepcopy(raw_payload)
    retained_indexes = [
        line_index for line_index in range(line_count) if line_index not in quarantined_indexes
    ]
    for axis in ALIGNED_LINE_AXES:
        copied_axis = retained[axis]
        retained[axis] = [copied_axis[line_index] for line_index in retained_indexes]

    raw_word_count = sum(len(line) for line in word_box_lines)
    quarantined_word_count = sum(
        len(word_box_lines[line_index]) for line_index in quarantined_indexes
    )
    ledger = {
        "format_version": LINE_QUARANTINE_LEDGER_FORMAT,
        "status": "NO_CHANGE" if not quarantined_lines else "WHOLE_LINES_QUARANTINED",
        "maximum_per_edge_overshoot_pixels": _MAXIMUM_PER_EDGE_OVERSHOOT_PIXELS,
        "pixel_dimensions": [pixel_width, pixel_height],
        "aligned_line_axes": list(ALIGNED_LINE_AXES),
        "raw_payload_sha256": canonical_payload_sha256(raw_payload),
        "retained_payload_sha256": canonical_payload_sha256(retained),
        "raw_line_count": line_count,
        "retained_line_count": len(retained_indexes),
        "quarantined_line_count": len(quarantined_lines),
        "raw_word_count": raw_word_count,
        "retained_word_count": raw_word_count - quarantined_word_count,
        "quarantined_word_count": quarantined_word_count,
        "quarantined_lines": quarantined_lines,
    }
    return retained, ledger


def build_ppocrv6_page_outlying_child_line_quarantine(
    raw_payload: dict[str, Any],
    *,
    pixel_width: int,
    pixel_height: int,
    normalization_authority: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Quarantine unsafe page-outlying child lines, then run the strict normalizer."""

    width = _positive_dimension(pixel_width, "render pixel width")
    height = _positive_dimension(pixel_height, "render pixel height")
    retained, quarantine_ledger = _quarantine_lines(
        raw_payload,
        pixel_width=width,
        pixel_height=height,
    )
    normalized, normalization_ledger = normalize_ppocrv6_word_boxes(
        retained,
        pixel_width=width,
        pixel_height=height,
        authority=normalization_authority,
    )
    return normalized, quarantine_ledger, normalization_ledger


def _same_typed_json(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(
            _same_typed_json(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _same_typed_json(a, b) for a, b in zip(left, right, strict=True)
        )
    if isinstance(left, float):
        return isfinite(left) and isfinite(right) and left.hex() == right.hex()
    return left == right


def validate_ppocrv6_page_outlying_child_line_quarantine(
    raw_payload: dict[str, Any],
    normalized_payload: dict[str, Any],
    quarantine_ledger: dict[str, Any],
    normalization_ledger: dict[str, Any],
    *,
    pixel_width: int,
    pixel_height: int,
    normalization_authority: dict[str, Any],
) -> None:
    """Require supplied pure-function outputs to equal a typed deterministic replay."""

    expected = build_ppocrv6_page_outlying_child_line_quarantine(
        raw_payload,
        pixel_width=pixel_width,
        pixel_height=pixel_height,
        normalization_authority=normalization_authority,
    )
    observed = (normalized_payload, quarantine_ledger, normalization_ledger)
    if not all(
        _same_typed_json(observed_item, expected_item)
        for observed_item, expected_item in zip(observed, expected, strict=True)
    ):
        raise PPOCRV6LineQuarantineError(
            "page-outlying child line quarantine differs from deterministic typed replay"
        )
