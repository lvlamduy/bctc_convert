"""Bind one selected-snapshot line to exact page pixels and dash evidence.

The family-first document store exposes two caller-authenticated immutable
objects: a selected-page line snapshot and an exact full-page render snapshot.
This bridge joins one existing line across those objects, crops its exact
source bbox, and runs the shared pixel-only dash classifier.  It does not use
the selected text, a family, an expected value, or an accounting equation.

Detector-hole geometry is deliberately not accepted by this V1 entry point.
Such a hole has no selected-snapshot sample of its own and must additionally
bind an authenticated stable row-axis/graph proposal identity.  Treating an
arbitrary row sample as that identity would let caller geometry manufacture a
zero, so holes remain fail-closed until that separate binding is supplied.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from bctc_ai.evaluation import authenticated_semantic_region_snapshot_v1 as snapshot_v1
from bctc_ai.evaluation import family_first_authenticated_page_region_v1 as region_v1
from bctc_ai.evaluation import family_first_visible_dash_glyph_evidence_v1 as dash_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "BINDING_KIND",
    "FORMAT_VERSION",
    "FamilyFirstAuthenticatedSnapshotCellDashV1Error",
    "build_family_first_authenticated_snapshot_cell_dash_v1",
    "validate_family_first_authenticated_snapshot_cell_dash_replay_v1",
]


FORMAT_VERSION = "FAMILY_FIRST_AUTHENTICATED_SNAPSHOT_CELL_DASH_EVIDENCE_V1"
CLAIM_BOUNDARY = (
    "CALLER_AUTHENTICATED_SELECTED_SNAPSHOT_EXISTING_LINE_EXACT_PHYSICAL_PAGE_"
    "RENDER_CROP_AND_PIXEL_DASH_GLYPH_EVIDENCE_ONLY_NO_DETECTOR_HOLE_TEXT_"
    "NUMERIC_ACCOUNTING_FAMILY_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
BINDING_KIND = "EXISTING_SELECTED_SNAPSHOT_LINE_EXACT_BBOX"
_AUTHORITY = {
    "accounting_or_expected_value_used_for_classification": False,
    "blank_crop_means_zero": False,
    "caller_authenticated_render_snapshot_required": True,
    "caller_authenticated_selected_snapshot_required": True,
    "degraded_mark_means_zero": False,
    "detector_hole_geometry_accepted": False,
    "family_or_schema_authority": False,
    "input_self_hash_is_authentication_authority": False,
    "mapping_authority": False,
    "numeric_digits_authority": False,
    "selected_snapshot_text_used_for_classification": False,
    "visible_pixel_dash_glyph_is_only_zero_authority": True,
}
_INPUT_FIELDS = {
    "binding_kind",
    "document_ordinal",
    "local_to_physical_page",
    "raw_pixel_bbox",
    "render_dimensions",
    "render_id",
    "sample_id",
    "snapshot_id",
    "source_line_index",
}
_PAGE_BINDING_FIELDS = {"local_page_sequence", "physical_page"}
_DIMENSION_FIELDS = {"pixel_height", "pixel_width"}
_RESULT_FIELDS = {
    "authority",
    "claim_boundary",
    "classification",
    "crop_binding",
    "dash_evidence",
    "evidence_id",
    "format_version",
    "input_binding",
    "normalized_value",
    "render_binding",
    "source_line_crop_ref",
    "state",
}
_CROP_BINDING_FIELDS = {
    "ink_localization_status",
    "proposed_raw_pixel_bbox",
    "recognition_raw_pixel_bbox",
    "region_id",
    "region_png_ref",
    "white_border",
}
_RENDER_BINDING_FIELDS = {"render_id", "render_ref"}
_CONTENT_REF_FIELDS = {"path", "sha256", "size_bytes"}
_BLOB_REF_FIELDS = {"sha256", "size_bytes"}
_RENDER_REF_FIELDS = {
    "pixel_height",
    "pixel_width",
    "sha256",
    "size_bytes",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class FamilyFirstAuthenticatedSnapshotCellDashV1Error(ValueError):
    """The selected line, page render, crop, dash evidence, or replay drifted."""


def _error(message: str) -> FamilyFirstAuthenticatedSnapshotCellDashV1Error:
    return FamilyFirstAuthenticatedSnapshotCellDashV1Error(message)


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be one positive exact integer")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise _error(f"{label} must be one nonnegative exact integer")
    return value


def _sha256(value: Any, label: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise _error(f"{label} must be one lowercase SHA-256")
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
        raise _error("snapshot-cell raw pixel bbox drifted")
    return list(value)


def _blob_ref(value: Any, label: str) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _BLOB_REF_FIELDS
        or type(value["size_bytes"]) is not int
        or value["size_bytes"] <= 0
    ):
        raise _error(f"{label} reference drifted")
    _sha256(value["sha256"], f"{label} hash")
    return canonical_clone_v1(value)


def _content_ref(value: Any, label: str) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _CONTENT_REF_FIELDS
        or type(value["path"]) is not str
        or not value["path"]
        or type(value["size_bytes"]) is not int
        or value["size_bytes"] <= 0
    ):
        raise _error(f"{label} reference drifted")
    _sha256(value["sha256"], f"{label} hash")
    return canonical_clone_v1(value)


def _render_ref(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RENDER_REF_FIELDS:
        raise _error("snapshot-cell render reference drifted")
    _positive_int(value["pixel_height"], "render pixel height")
    _positive_int(value["pixel_width"], "render pixel width")
    _positive_int(value["size_bytes"], "render byte size")
    _sha256(value["sha256"], "render hash")
    return canonical_clone_v1(value)


def _input_binding(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _INPUT_FIELDS:
        raise _error("snapshot-cell input binding fields drifted")
    if value["binding_kind"] != BINDING_KIND:
        raise _error(
            "detector-hole input requires an authenticated stable geometry proposal binding"
        )
    document_ordinal = _positive_int(value["document_ordinal"], "document ordinal")
    source_line_index = _nonnegative_int(value["source_line_index"], "source line index")
    if type(value["snapshot_id"]) is not str or not value["snapshot_id"]:
        raise _error("snapshot ID drifted")
    if type(value["sample_id"]) is not str or not value["sample_id"]:
        raise _error("sample ID drifted")
    if type(value["render_id"]) is not str or not value["render_id"]:
        raise _error("render ID drifted")
    raw_page = value["local_to_physical_page"]
    if type(raw_page) is not dict or set(raw_page) != _PAGE_BINDING_FIELDS:
        raise _error("local-to-physical page binding fields drifted")
    page_binding = {
        "local_page_sequence": _positive_int(
            raw_page["local_page_sequence"], "local page sequence"
        ),
        "physical_page": _positive_int(raw_page["physical_page"], "physical page"),
    }
    raw_dimensions = value["render_dimensions"]
    if type(raw_dimensions) is not dict or set(raw_dimensions) != _DIMENSION_FIELDS:
        raise _error("render dimension binding fields drifted")
    dimensions = {
        "pixel_height": _positive_int(raw_dimensions["pixel_height"], "pixel height"),
        "pixel_width": _positive_int(raw_dimensions["pixel_width"], "pixel width"),
    }
    bbox = _bbox(
        value["raw_pixel_bbox"],
        width=dimensions["pixel_width"],
        height=dimensions["pixel_height"],
    )
    return {
        "binding_kind": BINDING_KIND,
        "document_ordinal": document_ordinal,
        "local_to_physical_page": page_binding,
        "raw_pixel_bbox": bbox,
        "render_dimensions": dimensions,
        "render_id": value["render_id"],
        "sample_id": value["sample_id"],
        "snapshot_id": value["snapshot_id"],
        "source_line_index": source_line_index,
    }


def _derived_local_page_binding(selected_pages: list[int], *, physical_page: int) -> dict[str, int]:
    local_sequence = 0
    prior = None
    for page in selected_pages:
        local_sequence = local_sequence + 1 if prior is not None and page == prior + 1 else 1
        if page == physical_page:
            return {
                "local_page_sequence": local_sequence,
                "physical_page": physical_page,
            }
        prior = page
    raise _error("physical page is absent from the authenticated selected snapshot")


def _build(
    selected_snapshot: Mapping[str, Any],
    render_snapshot: Mapping[str, Any],
    cell_binding: Mapping[str, Any],
) -> dict[str, Any]:
    binding = _input_binding(cell_binding)
    try:
        projection = snapshot_v1.build_authenticated_semantic_region_snapshot_v1(selected_snapshot)
        snapshot_v1.validate_authenticated_semantic_region_snapshot_replay_v1(
            projection, selected_snapshot
        )
    except (ValueError, RuntimeError) as exc:
        raise _error("caller-authenticated selected snapshot contract drifted") from exc
    source = projection["source_binding"]
    page = binding["local_to_physical_page"]["physical_page"]
    if (
        source["document_ordinal"] != binding["document_ordinal"]
        or source["snapshot_id"] != binding["snapshot_id"]
    ):
        raise _error("snapshot-cell document or snapshot identity differs")
    expected_page_binding = _derived_local_page_binding(
        source["selected_pages"], physical_page=page
    )
    if not same_typed_json_v1(binding["local_to_physical_page"], expected_page_binding):
        raise _error("snapshot-cell local-to-physical page binding differs")
    selected_pages = [item for item in projection["page_bindings"] if item["page_sequence"] == page]
    selected_lines = [
        item for item in projection["line_bindings"] if item["sample_id"] == binding["sample_id"]
    ]
    if len(selected_pages) != 1 or len(selected_lines) != 1:
        raise _error("snapshot-cell page or sample does not resolve exactly once")
    selected_page = selected_pages[0]
    selected_line = selected_lines[0]
    if (
        selected_line["page_sequence"] != page
        or selected_line["source_line_index"] != binding["source_line_index"]
        or not same_typed_json_v1(selected_line["bbox"], binding["raw_pixel_bbox"])
        or selected_page["page_width"] != binding["render_dimensions"]["pixel_width"]
        or selected_page["page_height"] != binding["render_dimensions"]["pixel_height"]
    ):
        raise _error("snapshot-cell sample geometry or dimensions differ")
    try:
        render_record, _render_png_bytes = region_v1._validated_render_snapshot(render_snapshot)
    except (ValueError, RuntimeError) as exc:
        raise _error("caller-authenticated render snapshot contract drifted") from exc
    render_ref = _render_ref(render_record["render_ref"])
    if (
        render_record["document_ordinal"] != binding["document_ordinal"]
        or render_record["physical_page"] != page
        or render_snapshot["render_id"] != binding["render_id"]
        or render_ref["pixel_width"] != binding["render_dimensions"]["pixel_width"]
        or render_ref["pixel_height"] != binding["render_dimensions"]["pixel_height"]
        or render_ref["sha256"] != selected_page["render_ref"]["sha256"]
        or render_ref["size_bytes"] != selected_page["render_ref"]["size_bytes"]
    ):
        raise _error("snapshot-cell selected page and exact render differ")
    try:
        region = region_v1._crop_authenticated_family_first_page_render_snapshot_v1(
            dict(render_snapshot), raw_pixel_bbox=binding["raw_pixel_bbox"]
        )
        dash = dash_v1.build_family_first_visible_dash_glyph_evidence_v1(
            crop_png_bytes=region["region_png_bytes"]
        )
    except (ValueError, RuntimeError) as exc:
        raise _error("snapshot-cell exact render crop or dash classification failed") from exc
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "classification": dash["classification"],
        "crop_binding": {
            "ink_localization_status": region["ink_localization_status"],
            "proposed_raw_pixel_bbox": canonical_clone_v1(region["proposed_raw_pixel_bbox"]),
            "recognition_raw_pixel_bbox": canonical_clone_v1(region["recognition_raw_pixel_bbox"]),
            "region_id": region["region_id"],
            "region_png_ref": canonical_clone_v1(region["region_png_ref"]),
            "white_border": canonical_clone_v1(region["white_border"]),
        },
        "dash_evidence": canonical_clone_v1(dash),
        "format_version": FORMAT_VERSION,
        "input_binding": binding,
        "normalized_value": dash["normalized_value"],
        "render_binding": {
            "render_id": render_snapshot["render_id"],
            "render_ref": render_ref,
        },
        "source_line_crop_ref": canonical_clone_v1(selected_line["crop_ref"]),
        "state": "AUTHENTICATED_SELECTED_LINE_EXACT_PIXEL_DASH_EVIDENCE",
    }
    return _validate(
        {
            **material,
            "evidence_id": "ffascdv1:evidence:" + canonical_json_sha256_v1(material),
        }
    )


def _validate(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _RESULT_FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "AUTHENTICATED_SELECTED_LINE_EXACT_PIXEL_DASH_EVIDENCE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
    ):
        raise _error("snapshot-cell dash evidence fields drifted")
    binding = _input_binding(value["input_binding"])
    source_crop_ref = _content_ref(value["source_line_crop_ref"], "source line crop")
    render = value["render_binding"]
    crop = value["crop_binding"]
    if (
        type(render) is not dict
        or set(render) != _RENDER_BINDING_FIELDS
        or render["render_id"] != binding["render_id"]
        or type(crop) is not dict
        or set(crop) != _CROP_BINDING_FIELDS
        or type(crop["ink_localization_status"]) is not str
        or not crop["ink_localization_status"]
        or type(crop["region_id"]) is not str
        or not crop["region_id"].startswith("ffaprv1:region:")
        or crop["white_border"] != list(region_v1.WHITE_BORDER)
        or not same_typed_json_v1(crop["proposed_raw_pixel_bbox"], binding["raw_pixel_bbox"])
    ):
        raise _error("snapshot-cell crop or render binding drifted")
    render_ref = _render_ref(render["render_ref"])
    if (
        render_ref["pixel_height"] != binding["render_dimensions"]["pixel_height"]
        or render_ref["pixel_width"] != binding["render_dimensions"]["pixel_width"]
    ):
        raise _error("snapshot-cell render dimensions drifted")
    recognition_bbox = _bbox(
        crop["recognition_raw_pixel_bbox"],
        width=render_ref["pixel_width"],
        height=render_ref["pixel_height"],
    )
    proposed_bbox = binding["raw_pixel_bbox"]
    if not (
        proposed_bbox[0] <= recognition_bbox[0] < recognition_bbox[2] <= proposed_bbox[2]
        and proposed_bbox[1] <= recognition_bbox[1] < recognition_bbox[3] <= proposed_bbox[3]
    ):
        raise _error("snapshot-cell recognition bbox lies outside its source line")
    region_ref = _blob_ref(crop["region_png_ref"], "snapshot-cell region PNG")
    try:
        dash = dash_v1._validate(value["dash_evidence"])
    except (ValueError, RuntimeError) as exc:
        raise _error("snapshot-cell dash glyph evidence drifted") from exc
    if (
        dash["crop_ref"]["sha256"] != region_ref["sha256"]
        or dash["crop_ref"]["size_bytes"] != region_ref["size_bytes"]
        or value["classification"] != dash["classification"]
        or not same_typed_json_v1(value["normalized_value"], dash["normalized_value"])
        or (
            value["normalized_value"] is not None
            and (type(value["normalized_value"]) is not int or value["normalized_value"] != 0)
        )
    ):
        raise _error("snapshot-cell crop, classification, or zero binding drifted")
    material = canonical_clone_v1(value)
    evidence_id = material.pop("evidence_id")
    if evidence_id != "ffascdv1:evidence:" + canonical_json_sha256_v1(material):
        raise _error("snapshot-cell dash evidence identity drifted")
    # Keep the local names live so their strict validation cannot be removed
    # accidentally as an apparent no-op during future contract refactors.
    if source_crop_ref != value["source_line_crop_ref"]:
        raise _error("snapshot-cell source crop canonicalization drifted")
    return canonical_clone_v1(value)


def build_family_first_authenticated_snapshot_cell_dash_v1(
    *,
    selected_snapshot: Mapping[str, Any],
    render_snapshot: Mapping[str, Any],
    cell_binding: Mapping[str, Any],
) -> dict[str, Any]:
    """Build pixel-only dash evidence for one exact selected-snapshot line."""

    return _build(selected_snapshot, render_snapshot, cell_binding)


def validate_family_first_authenticated_snapshot_cell_dash_replay_v1(
    value: Any,
    *,
    selected_snapshot: Mapping[str, Any],
    render_snapshot: Mapping[str, Any],
    cell_binding: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild the line-to-render crop and glyph observation exactly."""

    persisted = _validate(value)
    rebuilt = _build(selected_snapshot, render_snapshot, cell_binding)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("snapshot-cell dash evidence does not replay exactly")
    return persisted
