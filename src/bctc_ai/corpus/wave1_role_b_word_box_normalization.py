from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from math import isfinite
from typing import Any

from bctc_ai.ocr.ppocrv6_page_session import (
    PPOCRV6PageSessionError,
    model_neutral_page_result,
    validate_ppocrv6_payload,
)


class WaveOneRoleBWordBoxNormalizationError(RuntimeError):
    """A raw PP-OCR word box cannot be normalized under the sealed B rule."""


WORD_BOX_NORMALIZATION_POLICY = {
    "rule_id": "PP_OCRV6_TEXT_WORD_BOX_PAGE_BOUNDARY_CLIP_MAX_1PX_V1",
    "scope": "TEXT_WORD_BOXES_ONLY",
    "maximum_per_edge_overshoot_pixels": 1,
    "page_bounds": "CLOSED_ZERO_TO_RENDER_PIXEL_DIMENSIONS",
    "raw_word_box_positive_area_required": True,
    "clipped_word_box_positive_area_required": True,
    "corrected_box_contained_in_validated_line_rec_box_required": True,
    "unchanged_word_box_validation": "MILESTONE_A_STRICT_VALIDATION_UNCHANGED",
    "all_other_geometry_validation": "MILESTONE_A_STRICT_VALIDATION_UNCHANGED",
    "correction_order": "LINE_INDEX_ASC_THEN_WORD_INDEX_ASC",
    "raw_provider_payload_preserved": True,
}

NORMALIZATION_LEDGER_FORMAT = "BANK_CORPUS_WAVE_1_ROLE_B_PPOCRV6_WORD_BOX_NORMALIZATION_LEDGER_V1"
_SHA256_CHARACTERS = frozenset("0123456789abcdef")


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_payload_sha256(payload: dict[str, Any]) -> str:
    try:
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    except (TypeError, ValueError) as error:
        raise WaveOneRoleBWordBoxNormalizationError(
            "PP-OCR payload is not finite canonical JSON"
        ) from error


def normalization_policy_sha256(policy: dict[str, Any]) -> str:
    if (
        not isinstance(policy, dict)
        or set(policy) != set(WORD_BOX_NORMALIZATION_POLICY)
        or any(
            type(policy[key]) is not type(expected) or policy[key] != expected
            for key, expected in WORD_BOX_NORMALIZATION_POLICY.items()
        )
    ):
        raise WaveOneRoleBWordBoxNormalizationError(
            "word-box normalization policy identity drifted"
        )
    try:
        if _canonical_bytes(policy) != _canonical_bytes(WORD_BOX_NORMALIZATION_POLICY):
            raise WaveOneRoleBWordBoxNormalizationError(
                "word-box normalization policy canonical bytes drifted"
            )
    except (TypeError, ValueError) as error:
        raise WaveOneRoleBWordBoxNormalizationError(
            "word-box normalization policy is not canonical finite JSON"
        ) from error
    return canonical_payload_sha256(policy)


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _SHA256_CHARACTERS


def validate_normalization_authority(authority: dict[str, Any]) -> dict[str, Any]:
    required = {
        "policy",
        "policy_sha256",
        "control_identity_sha256",
        "normalization_producer_implementation_ledger_sha256",
    }
    if not isinstance(authority, dict) or set(authority) != required:
        raise WaveOneRoleBWordBoxNormalizationError(
            "word-box normalization authority fields drifted"
        )
    policy = authority.get("policy")
    if (
        not isinstance(policy, dict)
        or authority.get("policy_sha256") != normalization_policy_sha256(policy)
        or not _is_sha256(authority.get("control_identity_sha256"))
        or not _is_sha256(authority.get("normalization_producer_implementation_ledger_sha256"))
    ):
        raise WaveOneRoleBWordBoxNormalizationError(
            "word-box normalization authority identity drifted"
        )
    return deepcopy(authority)


def _positive_render_dimension(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise WaveOneRoleBWordBoxNormalizationError(f"{label} must be a positive integer")
    return value


def _finite_box(box: Any, label: str) -> list[int | float]:
    if not isinstance(box, list) or len(box) != 4:
        raise WaveOneRoleBWordBoxNormalizationError(f"{label} must be [x0, y0, x1, y1]")
    coordinates: list[int | float] = []
    for coordinate in box:
        if (
            isinstance(coordinate, bool)
            or not isinstance(coordinate, (int, float))
            or not isfinite(coordinate)
        ):
            raise WaveOneRoleBWordBoxNormalizationError(
                f"{label} coordinates must be finite non-boolean numbers"
            )
        coordinates.append(coordinate)
    x0, y0, x1, y1 = coordinates
    if not x0 < x1 or not y0 < y1:
        raise WaveOneRoleBWordBoxNormalizationError(f"{label} must have positive area")
    return coordinates


def _clip_box_to_page(
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


def _contained_in_line(
    box: list[int | float],
    line_box: list[int | float],
) -> bool:
    x0, y0, x1, y1 = box
    line_x0, line_y0, line_x1, line_y1 = line_box
    return line_x0 <= x0 and line_y0 <= y0 and x1 <= line_x1 and y1 <= line_y1


def normalize_ppocrv6_word_boxes(
    raw_payload: dict[str, Any],
    *,
    pixel_width: int,
    pixel_height: int,
    authority: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a strict-A-valid copy plus a deterministic B normalization ledger."""

    width = _positive_render_dimension(pixel_width, "render pixel width")
    height = _positive_render_dimension(pixel_height, "render pixel height")
    bound_authority = validate_normalization_authority(authority)
    if not isinstance(raw_payload, dict):
        raise WaveOneRoleBWordBoxNormalizationError("raw PP-OCR payload must be an object")
    normalized = deepcopy(raw_payload)
    raw_lines = raw_payload.get("text_word_boxes")
    normalized_lines = normalized.get("text_word_boxes")
    if not isinstance(raw_lines, list) or not isinstance(normalized_lines, list):
        raise WaveOneRoleBWordBoxNormalizationError(
            "raw PP-OCR text_word_boxes must be a line-axis list"
        )

    maximum = bound_authority["policy"]["maximum_per_edge_overshoot_pixels"]
    provisional: list[dict[str, Any]] = []
    for line_index, raw_line in enumerate(raw_lines):
        if not isinstance(raw_line, list) or not isinstance(normalized_lines[line_index], list):
            raise WaveOneRoleBWordBoxNormalizationError(
                f"raw PP-OCR word boxes on line {line_index} must be a list"
            )
        for word_index, raw_box_value in enumerate(raw_line):
            raw_box = _finite_box(
                raw_box_value,
                f"raw PP-OCR word box line {line_index} word {word_index}",
            )
            clipped, per_edge = _clip_box_to_page(
                raw_box,
                pixel_width=width,
                pixel_height=height,
            )
            if any(amount > maximum for amount in per_edge.values()):
                raise WaveOneRoleBWordBoxNormalizationError(
                    f"raw PP-OCR word box line {line_index} word {word_index} "
                    "exceeds the one-pixel page-boundary allowance"
                )
            if not clipped[0] < clipped[2] or not clipped[1] < clipped[3]:
                raise WaveOneRoleBWordBoxNormalizationError(
                    f"clipped PP-OCR word box line {line_index} word {word_index} "
                    "does not have positive area"
                )
            if clipped != raw_box:
                normalized_lines[line_index][word_index] = clipped
                provisional.append(
                    {
                        "json_path": f"$.text_word_boxes[{line_index}][{word_index}]",
                        "line_index": line_index,
                        "word_index": word_index,
                        "raw_box": deepcopy(raw_box_value),
                        "normalized_box": deepcopy(clipped),
                        "per_edge_clip_pixels": per_edge,
                    }
                )

    try:
        validate_ppocrv6_payload(
            normalized,
            pixel_width=width,
            pixel_height=height,
        )
    except PPOCRV6PageSessionError as error:
        raise WaveOneRoleBWordBoxNormalizationError(
            "normalized PP-OCR payload failed strict Milestone-A validation"
        ) from error

    corrections = []
    for correction in provisional:
        line_box = deepcopy(normalized["rec_boxes"][correction["line_index"]])
        if not _contained_in_line(correction["normalized_box"], line_box):
            raise WaveOneRoleBWordBoxNormalizationError(
                "corrected PP-OCR word box is not contained in its validated line rec_box"
            )
        corrections.append({**correction, "validated_line_rec_box": line_box})

    raw_sha256 = canonical_payload_sha256(raw_payload)
    normalized_sha256 = canonical_payload_sha256(normalized)
    corrected_edge_count = sum(
        amount > 0
        for correction in corrections
        for amount in correction["per_edge_clip_pixels"].values()
    )
    ledger = {
        "format_version": NORMALIZATION_LEDGER_FORMAT,
        "status": "NO_CHANGE" if not corrections else "PAGE_BOUNDARY_CLIPPED",
        "rule_id": bound_authority["policy"]["rule_id"],
        "maximum_per_edge_overshoot_pixels": maximum,
        "policy_sha256": bound_authority["policy_sha256"],
        "control_identity_sha256": bound_authority["control_identity_sha256"],
        "normalization_producer_implementation_ledger_sha256": bound_authority[
            "normalization_producer_implementation_ledger_sha256"
        ],
        "pixel_dimensions": [width, height],
        "raw_payload_sha256": raw_sha256,
        "normalized_payload_sha256": normalized_sha256,
        "correction_count": len(corrections),
        "corrected_edge_count": corrected_edge_count,
        "corrections": corrections,
    }
    return normalized, ledger


def model_neutral_result_from_normalized_payload(
    normalized_payload: dict[str, Any],
    *,
    coordinate_authority: dict[str, Any],
) -> dict[str, Any]:
    """Project B-normalized words without labeling their pixel boxes as provider-raw."""

    neutral = model_neutral_page_result(
        normalized_payload,
        coordinate_authority=coordinate_authority,
    )
    input_fields = {
        "raw_text",
        "score",
        "score_kind",
        "raw_pixel_bbox",
        "canonical_bbox_mpt",
        "canonical_polygon_mpt",
    }
    output_fields = (input_fields - {"raw_pixel_bbox"}) | {"normalized_pixel_bbox"}
    words = [word for line in neutral["lines"] for word in line["words"]]
    words.extend(neutral["words"])
    seen: set[int] = set()
    for word in words:
        identity = id(word)
        if identity in seen:
            continue
        seen.add(identity)
        if not isinstance(word, dict) or set(word) != input_fields:
            raise WaveOneRoleBWordBoxNormalizationError(
                "Milestone-A model-neutral word projection fields drifted"
            )
        word["normalized_pixel_bbox"] = word.pop("raw_pixel_bbox")
    if any(not isinstance(word, dict) or set(word) != output_fields for word in words):
        raise WaveOneRoleBWordBoxNormalizationError(
            "B model-neutral normalized word projection fields drifted"
        )
    return neutral


__all__ = [
    "NORMALIZATION_LEDGER_FORMAT",
    "WORD_BOX_NORMALIZATION_POLICY",
    "WaveOneRoleBWordBoxNormalizationError",
    "canonical_payload_sha256",
    "model_neutral_result_from_normalized_payload",
    "normalization_policy_sha256",
    "normalize_ppocrv6_word_boxes",
    "validate_normalization_authority",
]
