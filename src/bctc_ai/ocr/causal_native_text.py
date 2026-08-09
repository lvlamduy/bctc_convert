from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from pathlib import Path
from typing import Any

import fitz
import yaml

from bctc_ai.core.coordinates import points_to_millipoints
from bctc_ai.ocr._causal_visibility_core import (
    CausalNativeTextError,
    ExcludedNativeTextSpan,
    VisibleNativeTextPage,
    extract_visible_native_text_page,
)
from bctc_ai.ocr.native_text_quality_v2 import load_native_text_quality_v2_config

__all__ = [
    "CausalNativeTextError",
    "CausalNativeTextPolicy",
    "ExcludedNativeTextSpan",
    "VisibleNativeTextPage",
    "bbox_to_millipoints",
    "extract_visible_native_text_page",
    "load_causal_native_text_policy",
    "read_causal_native_text_page",
    "round_points_to_millipoints",
]


@dataclass(frozen=True)
class CausalNativeTextPolicy:
    version: int
    policy: str
    claim_boundary: str
    near_white_channel_minimum: int
    raster_scale: float
    minimum_visible_contrast: int
    minimum_causal_contribution_ratio: float
    minimum_glyph_core_alpha: int
    relative_glyph_core_alpha: float
    minimum_glyph_core_survival_ratio: float
    blank_slot_inset_ratio: float
    exclude_fully_transparent_text_paints: bool
    require_causal_visibility_for_nonopaque_text: bool
    source_path: Path


def load_causal_native_text_policy(path: Path) -> CausalNativeTextPolicy:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise CausalNativeTextError(f"cannot load causal native-text policy: {path}") from error
    if not isinstance(payload, dict):
        raise CausalNativeTextError("causal native-text policy must be an object")
    expected_root = {
        "version": 1,
        "policy": "CAUSAL_NATIVE_TEXT_VISIBILITY_V1",
        "claim_boundary": "SOURCE_VISIBLE_NATIVE_TEXT_GEOMETRY_ONLY",
    }
    if set(payload) != {*expected_root, "visibility", "safety"} or any(
        payload.get(key) != value for key, value in expected_root.items()
    ):
        raise CausalNativeTextError("causal native-text policy identity drifted")
    visibility = payload.get("visibility")
    safety = payload.get("safety")
    if not isinstance(visibility, dict) or not isinstance(safety, dict):
        raise CausalNativeTextError("causal native-text policy sections are malformed")
    expected_visibility_fields = {
        "near_white_channel_minimum",
        "raster_scale",
        "minimum_visible_contrast",
        "minimum_causal_contribution_ratio",
        "minimum_glyph_core_alpha",
        "relative_glyph_core_alpha",
        "minimum_glyph_core_survival_ratio",
        "blank_slot_inset_ratio",
        "exclude_fully_transparent_text_paints",
        "require_causal_visibility_for_nonopaque_text",
    }
    required_safety = {
        "source_visible_text_only": True,
        "ambiguous_occlusion_status": "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY",
        "corrupt_or_empty_text_status": "UNRESOLVED_NATIVE_TEXT_QUALITY",
        "ocr_fallback_allowed": False,
        "table_or_statement_semantics_allowed": False,
        "schema_inputs_allowed": False,
        "role_a_inputs_allowed": False,
        "historical_values_allowed": False,
        "bank_or_page_specific_rules_allowed": False,
    }
    if set(visibility) != expected_visibility_fields:
        raise CausalNativeTextError("causal native-text visibility fields drifted")
    if set(safety) != set(required_safety) or any(
        safety.get(key) != value for key, value in required_safety.items()
    ):
        raise CausalNativeTextError("causal native-text safety boundary drifted")

    def number(name: str) -> float:
        value = visibility.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            raise CausalNativeTextError(f"causal native-text {name} is invalid")
        return float(value)

    near_white = visibility.get("near_white_channel_minimum")
    minimum_contrast = visibility.get("minimum_visible_contrast")
    minimum_alpha = visibility.get("minimum_glyph_core_alpha")
    if any(
        isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 255
        for value in (near_white, minimum_contrast, minimum_alpha)
    ):
        raise CausalNativeTextError("causal native-text integer thresholds are invalid")
    raster_scale = number("raster_scale")
    contribution = number("minimum_causal_contribution_ratio")
    relative_alpha = number("relative_glyph_core_alpha")
    survival = number("minimum_glyph_core_survival_ratio")
    inset = number("blank_slot_inset_ratio")
    if raster_scale <= 0 or any(
        not 0 < value <= 1 for value in (contribution, relative_alpha, survival, inset)
    ):
        raise CausalNativeTextError("causal native-text ratio thresholds are invalid")
    if (
        visibility.get("exclude_fully_transparent_text_paints") is not True
        or visibility.get("require_causal_visibility_for_nonopaque_text") is not True
    ):
        raise CausalNativeTextError("causal native-text visibility gates must remain enabled")
    return CausalNativeTextPolicy(
        version=1,
        policy=expected_root["policy"],
        claim_boundary=expected_root["claim_boundary"],
        near_white_channel_minimum=near_white,
        raster_scale=raster_scale,
        minimum_visible_contrast=minimum_contrast,
        minimum_causal_contribution_ratio=contribution,
        minimum_glyph_core_alpha=minimum_alpha,
        relative_glyph_core_alpha=relative_alpha,
        minimum_glyph_core_survival_ratio=survival,
        blank_slot_inset_ratio=inset,
        exclude_fully_transparent_text_paints=True,
        require_causal_visibility_for_nonopaque_text=True,
        source_path=path.resolve(),
    )


def round_points_to_millipoints(value: int | float) -> int:
    """Round PDF points to integer millipoints, with ties away from zero."""

    try:
        return points_to_millipoints(value)
    except (TypeError, ValueError) as error:
        raise CausalNativeTextError(str(error)) from error


def bbox_to_millipoints(box: Any) -> list[int]:
    return [round_points_to_millipoints(float(value)) for value in (box.x0, box.y0, box.x1, box.y1)]


def _quarantined_span_record(span: ExcludedNativeTextSpan) -> dict[str, Any]:
    """Serialize ghost metadata without leaking its excluded raw text."""

    return {
        "page": span.page,
        "text_sha256": sha256(span.raw_text.encode("utf-8")).hexdigest(),
        "nonwhitespace_character_count": sum(
            not character.isspace() for character in span.raw_text
        ),
        "bbox_mpt": bbox_to_millipoints(span.bbox),
        "block_number": span.block_number,
        "line_number": span.line_number,
        "span_number": span.span_number,
        "color": span.color,
        "alpha": span.alpha,
        "render_sequence": span.render_sequence,
        "occluding_sequence": span.occluding_sequence,
        "occluding_object_type": span.occluding_object_type,
        "reason": span.reason,
    }


def read_causal_native_text_page(
    page: fitz.Page,
    *,
    policy: CausalNativeTextPolicy,
    quality_policy_path: Path,
) -> dict[str, Any]:
    quality = load_native_text_quality_v2_config(quality_policy_path)
    try:
        visible = extract_visible_native_text_page(
            page,
            policy,
            native_text_quality_config=quality,
        )
    except (CausalNativeTextError, RuntimeError, ValueError) as error:
        return {
            "status": "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY",
            "failure_type": type(error).__name__,
            "lines": [],
            "words": [],
            "quarantined_spans": [],
            "ocr_fallback_used": False,
            "source_blank_claimed": False,
        }
    native_page = visible.page
    if native_page.text_quality != "USABLE_TEXT_LAYER" or not native_page.words:
        return {
            "status": "UNRESOLVED_NATIVE_TEXT_QUALITY",
            "native_text_quality": native_page.text_quality,
            "corruption_markers": list(native_page.corruption_markers),
            "lines": [],
            "words": [],
            "quarantined_spans": [
                _quarantined_span_record(span) for span in visible.excluded_spans
            ],
            "ocr_fallback_used": False,
            "source_blank_claimed": False,
        }
    words = [
        {
            "raw_text": word.raw_text,
            "score": None,
            "score_kind": "NATIVE_TEXT_NO_RECOGNITION_SCORE",
            "canonical_bbox_mpt": bbox_to_millipoints(word.bbox_points),
            "block_number": word.block_number,
            "line_number": word.line_number,
            "word_number": word.word_number,
        }
        for word in native_page.words
    ]
    grouped: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for word in words:
        grouped.setdefault((word["block_number"], word["line_number"]), []).append(word)
    lines = []
    for (block_number, line_number), line_words in sorted(grouped.items()):
        boxes = [word["canonical_bbox_mpt"] for word in line_words]
        lines.append(
            {
                "raw_text": " ".join(word["raw_text"] for word in line_words),
                "score": None,
                "score_kind": "NATIVE_TEXT_NO_RECOGNITION_SCORE",
                "canonical_bbox_mpt": [
                    min(box[0] for box in boxes),
                    min(box[1] for box in boxes),
                    max(box[2] for box in boxes),
                    max(box[3] for box in boxes),
                ],
                "block_number": block_number,
                "line_number": line_number,
                "words": line_words,
            }
        )
    quarantined = [_quarantined_span_record(span) for span in visible.excluded_spans]
    return {
        "status": "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
        "native_text_quality": native_page.text_quality,
        "corruption_markers": list(native_page.corruption_markers),
        "lines": lines,
        "words": words,
        "quarantined_spans": quarantined,
        "ocr_fallback_used": False,
        "source_blank_claimed": False,
    }
