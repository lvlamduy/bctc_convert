"""Authenticated proof for one material dash plus isolated scan specks.

This receipt is deliberately not a split-glyph classifier.  It applies only
when the shared visible-dash classifier has already failed closed on a crop
with multiple connected components.  Exactly one component must independently
replay as a centered material dash after deterministic isolation.  Every other
component must be individually tiny, non-horizontal, far away in both axes,
and off the dash baseline.  The discarded ink budget is bounded as a fraction
of the retained dash.

The caller supplies an exact V4 occurrence/parent/lane binding.  Pixels alone
classify the glyph; occurrence metadata only prevents a valid receipt from
being moved to another row, parent, lane, proposal, crop, or render.  No bank,
filename, page number, period, expected value, accounting equation, schema, or
mapping route can make an ambiguous crop resolve.
"""

from __future__ import annotations

import hashlib
import io
import math
import re
from typing import Any

from PIL import Image, ImageOps

from bctc_ai.evaluation import family_first_authenticated_page_region_v1 as region_v1
from bctc_ai.evaluation import family_first_visible_dash_glyph_evidence_v1 as dash_v1
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
    "CLASSIFICATION",
    "FORMAT_VERSION",
    "FamilyFirstAuthenticatedUniqueDashSpeckV1Error",
    "build_family_first_authenticated_unique_dash_speck_v1",
    "validate_family_first_authenticated_unique_dash_speck_replay_v1",
]


FORMAT_VERSION = "FAMILY_FIRST_AUTHENTICATED_UNIQUE_DASH_ISOLATED_SPECK_EVIDENCE_V1"
CLASSIFICATION = "VISIBLE_HORIZONTAL_DASH_WITH_ISOLATED_TINY_SCAN_SPECKS"
CLAIM_BOUNDARY = (
    "CALLER_AUTHENTICATED_V4_EXACT_OCCURRENCE_PARENT_LANE_RENDER_REGION_BINDING_"
    "ONE_MATERIAL_CENTERED_HORIZONTAL_DASH_COMPONENT_WITH_ONLY_FAR_OFF_BASELINE_"
    "TINY_SCAN_SPECKS_PIXEL_EVIDENCE_NO_SPLIT_GLYPH_OCR_EXPECTED_VALUE_"
    "ACCOUNTING_BANK_FILE_PAGE_PERIOD_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "accounting_or_expected_value_used_for_classification": False,
    "bank_file_page_period_routing_authority": False,
    "blank_crop_means_zero": False,
    "caller_authenticated_exact_region_required": True,
    "connected_or_nearby_marks_may_be_discarded": False,
    "mapping_or_schema_authority": False,
    "multiple_material_dash_components_may_resolve": False,
    "occurrence_parent_lane_metadata_used_for_pixel_classification": False,
    "split_glyph_authority": False,
    "tiny_far_off_baseline_scan_specks_may_be_discarded": True,
    "unique_isolated_material_dash_is_only_zero_authority": True,
}
_RESULT_FIELDS = {
    "authority",
    "claim_boundary",
    "classification",
    "component_analysis",
    "evidence_id",
    "format_version",
    "input_binding",
    "isolated_crop_ref",
    "isolated_dash_evidence",
    "normalized_value",
    "original_dash_evidence",
}
_INPUT_FIELDS = {
    "lane_binding",
    "occurrence_binding",
    "parent_binding",
    "source_row_sha256",
    "topology_candidates_id",
    "topology_scan_id",
}
_OCCURRENCE_FIELDS = {
    "document_line_ordinal",
    "end_document_line_ordinal",
    "end_source_line_index",
    "label_match_sha256",
    "occurrence_id",
    "page_sequence",
    "role",
    "role_kind",
    "scope_owner_occurrence_id",
    "scope_owner_role",
    "source_line_index",
}
_PARENT_FIELDS = {
    "document_line_ordinal",
    "end_document_line_ordinal",
    "end_source_line_index",
    "label_match_sha256",
    "occurrence_id",
    "page_sequence",
    "role",
    "role_kind",
    "source_line_index",
}
_LANE_FIELDS = {
    "column_center",
    "column_ordinal",
    "document_ordinal",
    "index_id",
    "physical_page",
    "proposed_raw_pixel_bbox",
    "recognition_raw_pixel_bbox",
    "region_id",
    "region_png_ref",
    "render_id",
    "render_ref",
    "white_border",
}
_ANALYSIS_FIELDS = {
    "background_luma",
    "component_count",
    "crop_height",
    "crop_width",
    "discarded_component_count",
    "discarded_components",
    "discarded_total_ink_pixel_count",
    "isolation_source_bbox",
    "selected_component",
    "threshold_luma",
}
_COMPONENT_FIELDS = {
    "aspect_ratio",
    "bbox",
    "height",
    "height_ratio",
    "horizontal_center_displacement_ratio",
    "ink_fill_ratio",
    "ink_pixel_count",
    "vertical_center_displacement_ratio",
    "width",
    "width_ratio",
}
_DISCARDED_COMPONENT_FIELDS = {
    *_COMPONENT_FIELDS,
    "baseline_overlaps_selected",
    "horizontal_center_distance",
    "horizontal_clear_gap",
    "vertical_center_distance",
    "vertical_clear_gap",
}
_BLOB_REF_FIELDS = {"pixel_height", "pixel_width", "sha256", "size_bytes"}
_REGION_REF_FIELDS = {"sha256", "size_bytes"}
_RENDER_REF_FIELDS = {"pixel_height", "pixel_width", "sha256", "size_bytes"}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_WHITE_BORDER = tuple(region_v1.WHITE_BORDER)
_MAX_COMPONENT_COUNT = 4


class FamilyFirstAuthenticatedUniqueDashSpeckV1Error(ValueError):
    """The binding, pixels, component proof, or replay drifted."""


def _error(message: str) -> FamilyFirstAuthenticatedUniqueDashSpeckV1Error:
    return FamilyFirstAuthenticatedUniqueDashSpeckV1Error(message)


def _sha256(value: Any, label: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise _error(f"{label} must be one lowercase SHA-256")
    return value


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be one positive exact integer")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise _error(f"{label} must be one nonnegative exact integer")
    return value


def _bbox(value: Any, *, width: int | None = None, height: int | None = None) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or value[0] < 0
        or value[1] < 0
        or value[0] >= value[2]
        or value[1] >= value[3]
        or (width is not None and value[2] > width)
        or (height is not None and value[3] > height)
    ):
        raise _error("unique-dash/speck bbox drifted")
    return list(value)


def _region_ref(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _REGION_REF_FIELDS
        or type(value["size_bytes"]) is not int
        or value["size_bytes"] <= 0
    ):
        raise _error("unique-dash region PNG reference drifted")
    _sha256(value["sha256"], "region PNG hash")
    return canonical_clone_v1(value)


def _render_ref(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RENDER_REF_FIELDS:
        raise _error("unique-dash render reference drifted")
    _positive_int(value["pixel_height"], "render pixel height")
    _positive_int(value["pixel_width"], "render pixel width")
    _positive_int(value["size_bytes"], "render byte size")
    _sha256(value["sha256"], "render hash")
    return canonical_clone_v1(value)


def _occurrence_binding(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _OCCURRENCE_FIELDS:
        raise _error("unique-dash occurrence binding fields drifted")
    result = canonical_clone_v1(value)
    if (
        type(result["occurrence_id"]) is not str
        or not result["occurrence_id"].startswith("aforav2:occurrence:")
        or type(result["scope_owner_occurrence_id"]) is not str
        or not result["scope_owner_occurrence_id"].startswith("aforav2:occurrence:")
        or type(result["role"]) is not str
        or not result["role"]
        or type(result["role_kind"]) is not str
        or not result["role_kind"]
        or type(result["scope_owner_role"]) is not str
        or not result["scope_owner_role"]
    ):
        raise _error("unique-dash occurrence or explicit parent identity drifted")
    _sha256(result["label_match_sha256"], "occurrence label-match hash")
    _positive_int(result["page_sequence"], "occurrence page sequence")
    start = _nonnegative_int(result["source_line_index"], "occurrence source line")
    end = _nonnegative_int(result["end_source_line_index"], "occurrence ending source line")
    document_start = _nonnegative_int(result["document_line_ordinal"], "occurrence document line")
    document_end = _nonnegative_int(
        result["end_document_line_ordinal"], "occurrence ending document line"
    )
    if end < start or document_end < document_start:
        raise _error("unique-dash occurrence source span drifted")
    return result


def _parent_binding(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _PARENT_FIELDS:
        raise _error("unique-dash parent binding fields drifted")
    result = canonical_clone_v1(value)
    if (
        type(result["occurrence_id"]) is not str
        or not result["occurrence_id"].startswith("aforav2:occurrence:")
        or type(result["role"]) is not str
        or not result["role"]
        or type(result["role_kind"]) is not str
        or not result["role_kind"]
    ):
        raise _error("unique-dash parent identity drifted")
    _sha256(result["label_match_sha256"], "parent label-match hash")
    _positive_int(result["page_sequence"], "parent page sequence")
    start = _nonnegative_int(result["source_line_index"], "parent source line")
    end = _nonnegative_int(result["end_source_line_index"], "parent ending source line")
    document_start = _nonnegative_int(result["document_line_ordinal"], "parent document line")
    document_end = _nonnegative_int(
        result["end_document_line_ordinal"], "parent ending document line"
    )
    if end < start or document_end < document_start:
        raise _error("unique-dash parent source span drifted")
    return result


def _lane_binding(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _LANE_FIELDS:
        raise _error("unique-dash lane binding fields drifted")
    result = canonical_clone_v1(value)
    center = result["column_center"]
    if type(center) is not float or not math.isfinite(center) or center < 0:
        raise _error("unique-dash column center drifted")
    _nonnegative_int(result["column_ordinal"], "column ordinal")
    _positive_int(result["document_ordinal"], "document ordinal")
    page = _positive_int(result["physical_page"], "physical page")
    if (
        type(result["index_id"]) is not str
        or not result["index_id"]
        or type(result["region_id"]) is not str
        or not result["region_id"].startswith("ffaprv1:region:")
        or type(result["render_id"]) is not str
        or not result["render_id"]
        or result["white_border"] != list(_WHITE_BORDER)
    ):
        raise _error("unique-dash region/render identity drifted")
    render = _render_ref(result["render_ref"])
    proposed = _bbox(
        result["proposed_raw_pixel_bbox"],
        width=render["pixel_width"],
        height=render["pixel_height"],
    )
    recognition = _bbox(
        result["recognition_raw_pixel_bbox"],
        width=render["pixel_width"],
        height=render["pixel_height"],
    )
    if not (
        proposed[0] <= recognition[0] < recognition[2] <= proposed[2]
        and proposed[1] <= recognition[1] < recognition[3] <= proposed[3]
    ):
        raise _error("unique-dash recognition bbox escapes its exact lane proposal")
    _region_ref(result["region_png_ref"])
    # Keep the local exact page live in this strict validator.
    if page != result["physical_page"]:
        raise _error("unique-dash physical page canonicalization drifted")
    return result


def _input_binding(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _INPUT_FIELDS:
        raise _error("unique-dash input binding fields drifted")
    result = canonical_clone_v1(value)
    if (
        type(result["topology_candidates_id"]) is not str
        or not result["topology_candidates_id"].startswith("aftcv2:result:")
        or type(result["topology_scan_id"]) is not str
        or not result["topology_scan_id"].startswith("aftv1:scan:")
    ):
        raise _error("unique-dash proof requires exact V4 topology authority")
    _sha256(result["source_row_sha256"], "source row hash")
    occurrence = _occurrence_binding(result["occurrence_binding"])
    parent = _parent_binding(result["parent_binding"])
    lane = _lane_binding(result["lane_binding"])
    if (
        occurrence["scope_owner_occurrence_id"] != parent["occurrence_id"]
        or occurrence["scope_owner_role"] != parent["role"]
        or occurrence["page_sequence"] != lane["physical_page"]
    ):
        raise _error("unique-dash occurrence, parent, and lane do not form one exact binding")
    return result


def _image_and_ref(payload: Any) -> tuple[Image.Image, dict[str, Any]]:
    if type(payload) is not bytes or not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        raise _error("unique-dash proof requires exact PNG region bytes")
    try:
        with Image.open(io.BytesIO(payload)) as raw:
            raw.load()
            image = raw.convert("RGB")
    except OSError as exc:
        raise _error("unique-dash region PNG cannot be decoded") from exc
    if image.width <= 0 or image.height <= 0:
        raise _error("unique-dash crop dimensions drifted")
    return image, {
        "pixel_height": image.height,
        "pixel_width": image.width,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _component_metrics(
    component: dict[str, Any], *, crop_width: int, crop_height: int
) -> dict[str, Any]:
    left, top, right, bottom = component["bbox"]
    width = right - left
    height = bottom - top
    return {
        "aspect_ratio": round(width / height, 8),
        "bbox": list(component["bbox"]),
        "height": height,
        "height_ratio": round(height / crop_height, 8),
        "horizontal_center_displacement_ratio": round(
            abs((left + right) / 2 - crop_width / 2) / crop_width, 8
        ),
        "ink_fill_ratio": round(component["ink_pixel_count"] / (width * height), 8),
        "ink_pixel_count": component["ink_pixel_count"],
        "vertical_center_displacement_ratio": round(
            abs((top + bottom) / 2 - crop_height / 2) / crop_height, 8
        ),
        "width": width,
        "width_ratio": round(width / crop_width, 8),
    }


def _is_material_dash_candidate(component: dict[str, Any], *, width: int, height: int) -> bool:
    left, top, right, bottom = component["bbox"]
    return (
        component["width"] >= max(8, math.ceil(width * 0.04))
        and component["height"] >= 2
        and component["aspect_ratio"] >= 1.8
        and 0.02 <= component["height_ratio"] <= 0.20
        and component["ink_fill_ratio"] >= 0.65
        and component["vertical_center_displacement_ratio"] <= 0.18
        and left >= _WHITE_BORDER[0]
        and top >= _WHITE_BORDER[1]
        and right <= width - _WHITE_BORDER[2]
        and bottom <= height - _WHITE_BORDER[3]
    )


def _clear_gap(first_start: int, first_stop: int, second_start: int, second_stop: int) -> int:
    if first_stop <= second_start:
        return second_start - first_stop
    if second_stop <= first_start:
        return first_start - second_stop
    return 0


def _discarded_metrics(
    component: dict[str, Any],
    selected: dict[str, Any],
    *,
    crop_width: int,
    crop_height: int,
) -> dict[str, Any]:
    metrics = _component_metrics(component, crop_width=crop_width, crop_height=crop_height)
    left, top, right, bottom = metrics["bbox"]
    selected_left, selected_top, selected_right, selected_bottom = selected["bbox"]
    return {
        **metrics,
        "baseline_overlaps_selected": not (bottom <= selected_top or selected_bottom <= top),
        "horizontal_center_distance": round(
            abs((left + right) / 2 - (selected_left + selected_right) / 2), 8
        ),
        "horizontal_clear_gap": _clear_gap(left, right, selected_left, selected_right),
        "vertical_center_distance": round(
            abs((top + bottom) / 2 - (selected_top + selected_bottom) / 2), 8
        ),
        "vertical_clear_gap": _clear_gap(top, bottom, selected_top, selected_bottom),
    }


def _isolated_crop(image: Image.Image, selected: dict[str, Any]) -> tuple[bytes, list[int]]:
    left, top, right, bottom = selected["bbox"]
    pad_x = max(4, int(round(selected["height"] * 0.7)))
    pad_y = max(3, int(round(selected["height"] * 0.45)))
    source_bbox = [left - pad_x, top - pad_y, right + pad_x, bottom + pad_y]
    if (
        source_bbox[0] < 0
        or source_bbox[1] < 0
        or source_bbox[2] > image.width
        or source_bbox[3] > image.height
    ):
        raise _error("material dash cannot be isolated without clipping")
    isolated = ImageOps.expand(
        image.crop(tuple(source_bbox)).convert("RGB"),
        border=_WHITE_BORDER,
        fill=(255, 255, 255),
    )
    stream = io.BytesIO()
    isolated.save(stream, format="PNG", optimize=False, compress_level=9)
    return stream.getvalue(), source_bbox


def _analysis(image: Image.Image) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    try:
        raw = foreground_components_v1(image)
    except AccountingPixelGlyphsV1Error as exc:
        raise _error("unique-dash foreground analysis failed") from exc
    components = raw["components"]
    if not 2 <= len(components) <= _MAX_COMPONENT_COUNT:
        raise _error("unique-dash proof requires two to four exact foreground components")
    metrics = [
        _component_metrics(component, crop_width=image.width, crop_height=image.height)
        for component in components
    ]
    candidates = [
        component
        for component in metrics
        if _is_material_dash_candidate(component, width=image.width, height=image.height)
    ]
    if len(candidates) != 1:
        raise _error("crop does not contain exactly one material dash candidate")
    selected = candidates[0]
    discarded = [
        _discarded_metrics(
            component,
            selected,
            crop_width=image.width,
            crop_height=image.height,
        )
        for component in components
        if component["bbox"] != selected["bbox"]
    ]
    ink_limit = max(8, int(selected["ink_pixel_count"] * 0.25))
    width_limit = max(4, selected["width"] // 2)
    horizontal_gap_limit = max(selected["width"] * 2, math.ceil(image.width * 0.10))
    vertical_gap_limit = max(selected["height"], math.ceil(image.height * 0.08))
    if sum(item["ink_pixel_count"] for item in discarded) > ink_limit or any(
        item["ink_pixel_count"] > ink_limit
        or item["width"] > width_limit
        or item["height"] > selected["height"]
        or (item["aspect_ratio"] >= 1.8 and item["ink_fill_ratio"] >= 0.5)
        or item["baseline_overlaps_selected"]
        or item["horizontal_clear_gap"] < horizontal_gap_limit
        or item["vertical_clear_gap"] < vertical_gap_limit
        for item in discarded
    ):
        raise _error("extra foreground is not only far off-baseline bounded tiny scan speck ink")
    isolated_payload, isolation_bbox = _isolated_crop(image, selected)
    if any(
        not (
            item["bbox"][2] <= isolation_bbox[0]
            or isolation_bbox[2] <= item["bbox"][0]
            or item["bbox"][3] <= isolation_bbox[1]
            or isolation_bbox[3] <= item["bbox"][1]
        )
        for item in discarded
    ):
        raise _error("discarded scan speck intersects the isolated material dash crop")
    isolated_dash = dash_v1.build_family_first_visible_dash_glyph_evidence_v1(
        crop_png_bytes=isolated_payload
    )
    if (
        isolated_dash["classification"] != "VISIBLE_HORIZONTAL_DASH_GLYPH"
        or isolated_dash["normalized_value"] != 0
        or isolated_dash["glyph_metrics"]["component_count"] != 1
        or isolated_dash["glyph_metrics"]["horizontal_center_displacement_ratio"] != 0.0
    ):
        raise _error("isolated material component does not replay as one centered visible dash")
    analysis = {
        "background_luma": raw["background_luma"],
        "component_count": len(components),
        "crop_height": image.height,
        "crop_width": image.width,
        "discarded_component_count": len(discarded),
        "discarded_components": discarded,
        "discarded_total_ink_pixel_count": sum(item["ink_pixel_count"] for item in discarded),
        "isolation_source_bbox": isolation_bbox,
        "selected_component": selected,
        "threshold_luma": raw["threshold_luma"],
    }
    return analysis, isolated_payload, isolated_dash


def _validate_component(
    value: Any, *, crop_width: int, crop_height: int, discarded: bool
) -> dict[str, Any]:
    fields = _DISCARDED_COMPONENT_FIELDS if discarded else _COMPONENT_FIELDS
    if type(value) is not dict or set(value) != fields:
        raise _error("unique-dash component metric fields drifted")
    bbox = _bbox(value["bbox"], width=crop_width, height=crop_height)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    ink = value["ink_pixel_count"]
    if (
        value["width"] != width
        or value["height"] != height
        or type(ink) is not int
        or not 0 < ink <= width * height
        or any(
            type(value[field]) is not float or not math.isfinite(value[field])
            for field in {
                "aspect_ratio",
                "height_ratio",
                "horizontal_center_displacement_ratio",
                "ink_fill_ratio",
                "vertical_center_displacement_ratio",
                "width_ratio",
            }
        )
    ):
        raise _error("unique-dash component metric types drifted")
    expected = _component_metrics(
        {"bbox": bbox, "ink_pixel_count": ink},
        crop_width=crop_width,
        crop_height=crop_height,
    )
    if any(not same_typed_json_v1(value[field], expected[field]) for field in _COMPONENT_FIELDS):
        raise _error("unique-dash component metrics do not replay arithmetically")
    if discarded and (
        type(value["baseline_overlaps_selected"]) is not bool
        or type(value["horizontal_center_distance"]) is not float
        or type(value["vertical_center_distance"]) is not float
        or type(value["horizontal_clear_gap"]) is not int
        or value["horizontal_clear_gap"] < 0
        or type(value["vertical_clear_gap"]) is not int
        or value["vertical_clear_gap"] < 0
    ):
        raise _error("discarded scan-speck separation metrics drifted")
    return canonical_clone_v1(value)


def _isolated_ref(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _BLOB_REF_FIELDS:
        raise _error("isolated material dash crop reference drifted")
    _positive_int(value["pixel_height"], "isolated crop height")
    _positive_int(value["pixel_width"], "isolated crop width")
    _positive_int(value["size_bytes"], "isolated crop byte size")
    _sha256(value["sha256"], "isolated crop hash")
    return canonical_clone_v1(value)


def _validate(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _RESULT_FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["classification"] != CLASSIFICATION
        or type(value["normalized_value"]) is not int
        or value["normalized_value"] != 0
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
    ):
        raise _error("unique-dash/speck evidence fields drifted")
    binding = _input_binding(value["input_binding"])
    try:
        original = dash_v1._validate(value["original_dash_evidence"])
        isolated = dash_v1._validate(value["isolated_dash_evidence"])
    except dash_v1.FamilyFirstVisibleDashGlyphEvidenceV1Error as exc:
        raise _error("embedded visible-dash evidence drifted") from exc
    isolated_ref = _isolated_ref(value["isolated_crop_ref"])
    lane = binding["lane_binding"]
    recognition = lane["recognition_raw_pixel_bbox"]
    expected_width = recognition[2] - recognition[0] + _WHITE_BORDER[0] + _WHITE_BORDER[2]
    expected_height = recognition[3] - recognition[1] + _WHITE_BORDER[1] + _WHITE_BORDER[3]
    if (
        original["classification"] != "UNRESOLVED_NOT_ONE_DASH_GLYPH"
        or original["normalized_value"] is not None
        or original["crop_ref"]["sha256"] != lane["region_png_ref"]["sha256"]
        or original["crop_ref"]["size_bytes"] != lane["region_png_ref"]["size_bytes"]
        or original["crop_ref"]["pixel_width"] != expected_width
        or original["crop_ref"]["pixel_height"] != expected_height
        or isolated["classification"] != "VISIBLE_HORIZONTAL_DASH_GLYPH"
        or isolated["normalized_value"] != 0
        or not same_typed_json_v1(isolated["crop_ref"], isolated_ref)
    ):
        raise _error("original/isolated dash evidence or exact lane crop binding drifted")
    analysis = value["component_analysis"]
    if (
        type(analysis) is not dict
        or set(analysis) != _ANALYSIS_FIELDS
        or type(analysis["background_luma"]) is not float
        or not math.isfinite(analysis["background_luma"])
        or type(analysis["crop_width"]) is not int
        or analysis["crop_width"] != original["crop_ref"]["pixel_width"]
        or type(analysis["crop_height"]) is not int
        or analysis["crop_height"] != original["crop_ref"]["pixel_height"]
        or type(analysis["component_count"]) is not int
        or not 2 <= analysis["component_count"] <= _MAX_COMPONENT_COUNT
        or original["glyph_metrics"]["component_count"] != analysis["component_count"]
        or type(analysis["discarded_component_count"]) is not int
        or analysis["discarded_component_count"] != analysis["component_count"] - 1
        or type(analysis["discarded_components"]) is not list
        or len(analysis["discarded_components"]) != analysis["discarded_component_count"]
        or type(analysis["discarded_total_ink_pixel_count"]) is not int
        or analysis["discarded_total_ink_pixel_count"] <= 0
        or type(analysis["threshold_luma"]) is not int
        or not 0 <= analysis["threshold_luma"] <= 255
    ):
        raise _error("unique-dash component analysis fields drifted")
    selected = _validate_component(
        analysis["selected_component"],
        crop_width=analysis["crop_width"],
        crop_height=analysis["crop_height"],
        discarded=False,
    )
    discarded = [
        _validate_component(
            item,
            crop_width=analysis["crop_width"],
            crop_height=analysis["crop_height"],
            discarded=True,
        )
        for item in analysis["discarded_components"]
    ]
    if discarded != sorted(discarded, key=lambda item: item["bbox"]):
        raise _error("discarded scan-speck component order drifted")
    expected_discarded = [
        _discarded_metrics(
            {"bbox": item["bbox"], "ink_pixel_count": item["ink_pixel_count"]},
            selected,
            crop_width=analysis["crop_width"],
            crop_height=analysis["crop_height"],
        )
        for item in discarded
    ]
    ink_limit = max(8, int(selected["ink_pixel_count"] * 0.25))
    width_limit = max(4, selected["width"] // 2)
    horizontal_gap_limit = max(selected["width"] * 2, math.ceil(analysis["crop_width"] * 0.10))
    vertical_gap_limit = max(selected["height"], math.ceil(analysis["crop_height"] * 0.08))
    isolation_bbox = _bbox(
        analysis["isolation_source_bbox"],
        width=analysis["crop_width"],
        height=analysis["crop_height"],
    )
    if (
        not _is_material_dash_candidate(
            selected, width=analysis["crop_width"], height=analysis["crop_height"]
        )
        or not same_typed_json_v1(discarded, expected_discarded)
        or analysis["discarded_total_ink_pixel_count"]
        != sum(item["ink_pixel_count"] for item in discarded)
        or analysis["discarded_total_ink_pixel_count"] > ink_limit
        or any(
            item["ink_pixel_count"] > ink_limit
            or item["width"] > width_limit
            or item["height"] > selected["height"]
            or (item["aspect_ratio"] >= 1.8 and item["ink_fill_ratio"] >= 0.5)
            or item["baseline_overlaps_selected"]
            or item["horizontal_clear_gap"] < horizontal_gap_limit
            or item["vertical_clear_gap"] < vertical_gap_limit
            for item in discarded
        )
        or isolated["glyph_metrics"]["component_count"] != 1
        or isolated["glyph_metrics"]["horizontal_center_displacement_ratio"] != 0.0
        or any(
            not (
                item["bbox"][2] <= isolation_bbox[0]
                or isolation_bbox[2] <= item["bbox"][0]
                or item["bbox"][3] <= isolation_bbox[1]
                or isolation_bbox[3] <= item["bbox"][1]
            )
            for item in discarded
        )
    ):
        raise _error("unique material dash or isolated-speck predicates drifted")
    material = canonical_clone_v1(value)
    evidence_id = material.pop("evidence_id")
    if evidence_id != "ffaudsv1:evidence:" + canonical_json_sha256_v1(material):
        raise _error("unique-dash/speck evidence identity drifted")
    return canonical_clone_v1(value)


def _build(*, crop_png_bytes: bytes, input_binding: Any) -> dict[str, Any]:
    binding = _input_binding(input_binding)
    image, crop_ref = _image_and_ref(crop_png_bytes)
    if (
        crop_ref["sha256"] != binding["lane_binding"]["region_png_ref"]["sha256"]
        or crop_ref["size_bytes"] != binding["lane_binding"]["region_png_ref"]["size_bytes"]
    ):
        raise _error("unique-dash pixels differ from their exact authenticated region binding")
    original = dash_v1.build_family_first_visible_dash_glyph_evidence_v1(
        crop_png_bytes=crop_png_bytes
    )
    if original["classification"] != "UNRESOLVED_NOT_ONE_DASH_GLYPH":
        raise _error("unique-dash/speck receipt cannot replace an already resolved dash decision")
    analysis, isolated_payload, isolated_dash = _analysis(image)
    isolated_ref = {
        "pixel_height": isolated_dash["crop_ref"]["pixel_height"],
        "pixel_width": isolated_dash["crop_ref"]["pixel_width"],
        "sha256": hashlib.sha256(isolated_payload).hexdigest(),
        "size_bytes": len(isolated_payload),
    }
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "classification": CLASSIFICATION,
        "component_analysis": analysis,
        "format_version": FORMAT_VERSION,
        "input_binding": binding,
        "isolated_crop_ref": isolated_ref,
        "isolated_dash_evidence": isolated_dash,
        "normalized_value": 0,
        "original_dash_evidence": original,
    }
    return _validate(
        {
            **material,
            "evidence_id": "ffaudsv1:evidence:" + canonical_json_sha256_v1(material),
        }
    )


def build_family_first_authenticated_unique_dash_speck_v1(
    *, crop_png_bytes: bytes, input_binding: Any
) -> dict[str, Any]:
    """Prove one material dash after discarding only isolated tiny scan specks."""

    return _build(crop_png_bytes=crop_png_bytes, input_binding=input_binding)


def validate_family_first_authenticated_unique_dash_speck_replay_v1(
    value: Any, *, crop_png_bytes: bytes, input_binding: Any
) -> dict[str, Any]:
    """Rebuild the exact binding, components, isolation crop, and receipt."""

    persisted = _validate(value)
    rebuilt = _build(crop_png_bytes=crop_png_bytes, input_binding=input_binding)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("unique-dash/speck evidence does not replay exactly")
    return persisted
