"""Deterministic pixel evidence for a visible accounting dash glyph.

Some financial tables print a dash for zero, yet the detector can omit the
cell and a text recognizer can misread the short glyph as a letter or accent.
This module does not perform OCR.  It classifies only one centered horizontal
glyph in an immutable crop: either a thin dash or the solid horizontal bar that
some embedded PDF fonts render for a dash.  Blank crops, full-span table rules,
digits, letters, multiple components, and ambiguous shapes remain unresolved.
"""

from __future__ import annotations

import hashlib
import io
import math
import re
from typing import Any

from PIL import Image

from bctc_ai.evaluation.accounting_pixel_glyphs_v1 import (
    AccountingPixelGlyphsV1Error,
    foreground_components_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FamilyFirstVisibleDashGlyphEvidenceV1Error",
    "build_family_first_visible_dash_glyph_evidence_v1",
    "validate_family_first_visible_dash_glyph_evidence_replay_v1",
]


FORMAT_VERSION = "FAMILY_FIRST_VISIBLE_DASH_GLYPH_EVIDENCE_V1"
CLAIM_BOUNDARY = (
    "IMMUTABLE_PIXEL_CROP_SINGLE_CENTERED_HORIZONTAL_DASH_GLYPH_EVIDENCE_ONLY_"
    "NO_OCR_EXPECTED_VALUE_ACCOUNTING_FAMILY_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "accounting_equation_used_for_glyph_classification": False,
    "blank_crop_means_zero": False,
    "dash_glyph_may_normalize_to_zero": True,
    "expected_value_available": False,
    "family_authority": False,
    "gemma_used": False,
    "mapping_authority": False,
    "numeric_digits_authority": False,
    "raw_record_self_authenticates": False,
    "schema_authority": False,
    "visible_dash_glyph_evidence": True,
}
_FIELDS = {
    "authority",
    "claim_boundary",
    "classification",
    "crop_ref",
    "evidence_id",
    "format_version",
    "glyph_metrics",
    "normalized_value",
}
_METRIC_FIELDS = {
    "component_aspect_ratio",
    "component_bbox",
    "component_count",
    "component_height_ratio",
    "component_width_ratio",
    "horizontal_center_displacement_ratio",
    "ink_fill_ratio",
    "vertical_center_displacement_ratio",
}
_CROP_REF_FIELDS = {"pixel_height", "pixel_width", "sha256", "size_bytes"}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class FamilyFirstVisibleDashGlyphEvidenceV1Error(ValueError):
    """The crop or dash-glyph evidence contract drifted."""


def _error(message: str) -> FamilyFirstVisibleDashGlyphEvidenceV1Error:
    return FamilyFirstVisibleDashGlyphEvidenceV1Error(message)


def _image_and_ref(payload: Any) -> tuple[Image.Image, dict[str, Any]]:
    if type(payload) is not bytes or not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        raise _error("visible-dash evidence requires exact PNG crop bytes")
    try:
        with Image.open(io.BytesIO(payload)) as raw:
            raw.load()
            image = raw.convert("RGB")
    except OSError as exc:
        raise _error("visible-dash crop PNG cannot be decoded") from exc
    if image.width <= 0 or image.height <= 0:
        raise _error("visible-dash crop dimensions drifted")
    return image, {
        "pixel_height": image.height,
        "pixel_width": image.width,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _metrics(image: Image.Image) -> tuple[dict[str, Any], bool]:
    try:
        components = foreground_components_v1(image)["components"]
    except AccountingPixelGlyphsV1Error as exc:
        raise _error("visible-dash foreground analysis failed") from exc
    if len(components) != 1:
        return {
            "component_aspect_ratio": None,
            "component_bbox": None,
            "component_count": len(components),
            "component_height_ratio": None,
            "component_width_ratio": None,
            "horizontal_center_displacement_ratio": None,
            "ink_fill_ratio": None,
            "vertical_center_displacement_ratio": None,
        }, False
    component = components[0]
    left, top, right, bottom = component["bbox"]
    width = right - left
    height = bottom - top
    box_area = width * height
    crop_width, crop_height = image.size
    aspect = width / height
    width_ratio = width / crop_width
    height_ratio = height / crop_height
    horizontal_displacement = abs((left + right) / 2 - crop_width / 2) / crop_width
    vertical_displacement = abs((top + bottom) / 2 - crop_height / 2) / crop_height
    fill = component["ink_pixel_count"] / box_area
    metrics = {
        "component_aspect_ratio": round(aspect, 8),
        "component_bbox": list(component["bbox"]),
        "component_count": 1,
        "component_height_ratio": round(height_ratio, 8),
        "component_width_ratio": round(width_ratio, 8),
        "horizontal_center_displacement_ratio": round(horizontal_displacement, 8),
        "ink_fill_ratio": round(fill, 8),
        "vertical_center_displacement_ratio": round(vertical_displacement, 8),
    }
    return metrics, _is_dash_metrics(metrics)


def _is_dash_metrics(metrics: dict[str, Any]) -> bool:
    common = (
        metrics["component_aspect_ratio"] >= 1.8
        and 0.04 <= metrics["component_width_ratio"] <= 0.65
        and metrics["horizontal_center_displacement_ratio"] <= 0.18
        and metrics["vertical_center_displacement_ratio"] <= 0.18
    )
    thin_dash = (
        0.02 <= metrics["component_height_ratio"] <= 0.35 and metrics["ink_fill_ratio"] >= 0.2
    )
    embedded_font_solid_bar = (
        metrics["component_aspect_ratio"] >= 3.0
        and 0.35 < metrics["component_height_ratio"] <= 0.75
        and metrics["ink_fill_ratio"] >= 0.85
    )
    return common and (thin_dash or embedded_font_solid_bar)


def _validate(value: Any) -> dict[str, Any]:
    crop_ref = value.get("crop_ref") if type(value) is dict else None
    metrics = value.get("glyph_metrics") if type(value) is dict else None
    if (
        type(value) is not dict
        or set(value) != _FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(crop_ref) is not dict
        or set(crop_ref) != _CROP_REF_FIELDS
        or type(crop_ref["pixel_height"]) is not int
        or crop_ref["pixel_height"] <= 0
        or type(crop_ref["pixel_width"]) is not int
        or crop_ref["pixel_width"] <= 0
        or type(crop_ref["sha256"]) is not str
        or _SHA256.fullmatch(crop_ref["sha256"]) is None
        or type(crop_ref["size_bytes"]) is not int
        or crop_ref["size_bytes"] <= 0
        or type(metrics) is not dict
        or set(metrics) != _METRIC_FIELDS
        or type(metrics["component_count"]) is not int
        or metrics["component_count"] < 0
        or value["classification"]
        not in {"VISIBLE_HORIZONTAL_DASH_GLYPH", "UNRESOLVED_NOT_ONE_DASH_GLYPH"}
    ):
        raise _error("visible-dash glyph evidence fields drifted")
    if metrics["component_count"] == 1:
        bbox = metrics["component_bbox"]
        scalar_fields = _METRIC_FIELDS - {"component_bbox", "component_count"}
        if (
            type(bbox) is not list
            or len(bbox) != 4
            or any(type(item) is not int for item in bbox)
            or not (0 <= bbox[0] < bbox[2] <= crop_ref["pixel_width"])
            or not (0 <= bbox[1] < bbox[3] <= crop_ref["pixel_height"])
            or any(
                type(metrics[field]) is not float or not math.isfinite(metrics[field])
                for field in scalar_fields
            )
        ):
            raise _error("visible-dash glyph metric types drifted")
        is_dash = _is_dash_metrics(metrics)
    else:
        if any(metrics[field] is not None for field in _METRIC_FIELDS - {"component_count"}):
            raise _error("multi/zero-component dash metrics must remain null")
        is_dash = False
    if (
        is_dash
        and (
            value["classification"] != "VISIBLE_HORIZONTAL_DASH_GLYPH"
            or type(value["normalized_value"]) is not int
            or value["normalized_value"] != 0
        )
    ) or (
        not is_dash
        and (
            value["classification"] != "UNRESOLVED_NOT_ONE_DASH_GLYPH"
            or value["normalized_value"] is not None
        )
    ):
        raise _error("visible-dash glyph classification/metrics drifted")
    material = canonical_clone_v1(value)
    evidence_id = material.pop("evidence_id")
    if evidence_id != "ffvdgev1:evidence:" + canonical_json_sha256_v1(material):
        raise _error("visible-dash glyph evidence identity drifted")
    return canonical_clone_v1(value)


def build_family_first_visible_dash_glyph_evidence_v1(*, crop_png_bytes: bytes) -> dict[str, Any]:
    """Classify only a single centered horizontal glyph in an immutable crop."""

    image, crop_ref = _image_and_ref(crop_png_bytes)
    metrics, is_dash = _metrics(image)
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "classification": (
            "VISIBLE_HORIZONTAL_DASH_GLYPH" if is_dash else "UNRESOLVED_NOT_ONE_DASH_GLYPH"
        ),
        "crop_ref": crop_ref,
        "format_version": FORMAT_VERSION,
        "glyph_metrics": metrics,
        "normalized_value": 0 if is_dash else None,
    }
    return _validate(
        {
            **material,
            "evidence_id": "ffvdgev1:evidence:" + canonical_json_sha256_v1(material),
        }
    )


def validate_family_first_visible_dash_glyph_evidence_replay_v1(
    value: Any, *, crop_png_bytes: bytes
) -> dict[str, Any]:
    """Exact-rebuild a persisted dash-glyph observation from immutable pixels."""

    persisted = _validate(value)
    expected = build_family_first_visible_dash_glyph_evidence_v1(crop_png_bytes=crop_png_bytes)
    if not same_typed_json_v1(persisted, expected):
        raise _error("visible-dash glyph evidence does not replay exactly")
    return persisted
