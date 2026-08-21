"""Authenticated full-page render and detector-independent region crops.

The all-filing semantic cache deliberately freezes every detector-produced line,
but a detector can still omit a visible dash or a narrow numeric cell.  This
module closes that geometry gap without treating a missing detector box as a
missing source value.  It re-renders an exact source PDF page from the live
family-first capability, authenticates the render against the sealed page
artifact, and deterministically crops a caller-proposed pixel region.

The proposed region remains geometry evidence only.  A separate pinned
recognizer must read the returned immutable PNG bytes, and downstream period,
unit, population, and accounting checks still decide whether the observation is
admissible.
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

from bctc_ai.evaluation import family_first_semantic_index_v1 as index_v1
from bctc_ai.evaluation import family_first_semantic_label_archive_v1 as archive_v1
from bctc_ai.evaluation import family_first_semantic_label_freeze_v1 as freeze_v1
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
    "FamilyFirstAuthenticatedPageRegionV1Error",
    "crop_authenticated_family_first_page_region_v1",
    "read_authenticated_family_first_page_render_v1",
    "read_authenticated_family_first_page_renders_v1",
]


FORMAT_VERSION = "FAMILY_FIRST_AUTHENTICATED_PAGE_REGION_V1"
RENDER_FORMAT_VERSION = "FAMILY_FIRST_AUTHENTICATED_PAGE_RENDER_V1"
WHITE_BORDER = (12, 8, 12, 8)
_RENDER_AUTHORITY = {
    "authenticated_source_page_render": True,
    "bank_page_or_family_routing_authority": False,
    "detector_geometry_required": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "schema_authority": False,
    "semantic_text_authority": False,
}
_REGION_AUTHORITY = {
    "authenticated_source_page_render": True,
    "caller_proposed_region_geometry": True,
    "detector_geometry_required": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "recognizer_required_for_text_or_number": True,
    "schema_authority": False,
}
_RENDER_SELECTION_FIELDS = {"document_ordinal", "physical_page"}
_RENDER_SNAPSHOT_FIELDS = {
    "archive_id",
    "authority",
    "document_ordinal",
    "format_version",
    "index_id",
    "physical_page",
    "plan_id",
    "render_id",
    "render_png_bytes",
    "render_ref",
    "state",
}


class FamilyFirstAuthenticatedPageRegionV1Error(RuntimeError):
    """The live source/page/render/region contract could not be replayed."""


def _error(message: str) -> FamilyFirstAuthenticatedPageRegionV1Error:
    return FamilyFirstAuthenticatedPageRegionV1Error(message)


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be one positive exact integer")
    return value


def _render_reference(value: Any) -> dict[str, Any]:
    fields = {"pixel_height", "pixel_width", "sha256", "size_bytes"}
    if (
        type(value) is not dict
        or set(value) != fields
        or type(value["pixel_height"]) is not int
        or value["pixel_height"] <= 0
        or type(value["pixel_width"]) is not int
        or value["pixel_width"] <= 0
        or type(value["sha256"]) is not str
        or len(value["sha256"]) != 64
        or any(character not in "0123456789abcdef" for character in value["sha256"])
        or type(value["size_bytes"]) is not int
        or value["size_bytes"] <= 0
    ):
        raise _error("sealed source render reference drifted")
    return canonical_clone_v1(value)


def _region_bbox(value: Any, *, width: int, height: int) -> list[int]:
    if type(value) is not list or len(value) != 4 or any(type(item) is not int for item in value):
        raise _error("region bbox must be one exact [left, top, right, bottom] integer list")
    left, top, right, bottom = value
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        raise _error("region bbox must have positive area inside the authenticated render")
    return [left, top, right, bottom]


def _png_image(payload: bytes) -> Image.Image:
    if type(payload) is not bytes or not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        raise _error("authenticated source render is not exact PNG bytes")
    try:
        with Image.open(io.BytesIO(payload)) as raw:
            raw.load()
            image = raw.convert("RGB")
    except OSError as exc:
        raise _error("authenticated source render PNG cannot be decoded") from exc
    if image.width <= 0 or image.height <= 0:
        raise _error("authenticated source render dimensions drifted")
    return image


def _foreground_recognition_bbox(
    image: Image.Image, proposed_bbox: list[int]
) -> tuple[list[int], str]:
    """Tighten a table-cell proposal to stable dark foreground components.

    Numeric recognizers can miss a small dash when it occupies only a few
    pixels inside a wide column-domain crop.  Connected components remove
    isolated antialias noise and full-span table rules, then retain a padded
    union of the remaining glyph-like foreground.  If no such component
    exists, the complete proposed cell is preserved so a blank remains an
    unresolved recognition result rather than being manufactured as zero.
    """

    left, top, right, bottom = proposed_bbox
    cell = image.crop((left, top, right, bottom))
    try:
        analysis = foreground_components_v1(cell)
    except AccountingPixelGlyphsV1Error as exc:
        raise _error("proposed cell foreground analysis failed") from exc
    width, height = cell.size
    components = analysis["components"]
    if not components:
        return list(proposed_bbox), "NO_GLYPH_COMPONENT_FULL_PROPOSED_CELL_PRESERVED"

    ink_left = min(component["bbox"][0] for component in components)
    ink_top = min(component["bbox"][1] for component in components)
    ink_right = max(component["bbox"][2] for component in components)
    ink_bottom = max(component["bbox"][3] for component in components)
    ink_height = ink_bottom - ink_top
    pad_x = max(4, int(round(ink_height * 0.7)))
    pad_y = max(3, int(round(ink_height * 0.45)))
    recognition = [
        left + max(0, ink_left - pad_x),
        top + max(0, ink_top - pad_y),
        left + min(width, ink_right + pad_x),
        top + min(height, ink_bottom + pad_y),
    ]
    if recognition[2] <= recognition[0] or recognition[3] <= recognition[1]:
        raise _error("foreground-localized recognition region has no positive area")
    return recognition, "GLYPH_COMPONENT_TIGHTENED_WITHIN_PROPOSED_CELL"


def _document(plan: dict[str, Any], document_ordinal: int) -> dict[str, Any]:
    documents = plan["documents"]
    if document_ordinal > len(documents):
        raise _error("document ordinal lies outside the authenticated filing denominator")
    document = documents[document_ordinal - 1]
    if document["document_ordinal"] != document_ordinal:
        raise _error("authenticated filing order drifted")
    return document


def _render_page(source: bytes, *, physical_page: int, dpi: int) -> bytes:
    try:
        import fitz
    except ImportError as exc:
        raise _error("pinned PyMuPDF is required to replay one source page") from exc
    try:
        document = fitz.open(stream=source, filetype="pdf")
    except (RuntimeError, ValueError) as exc:
        raise _error("authenticated source PDF cannot be opened") from exc
    try:
        if physical_page > document.page_count:
            raise _error("physical page lies outside the authenticated PDF denominator")
        pixmap = document[physical_page - 1].get_pixmap(
            matrix=fitz.Matrix(dpi / 72, dpi / 72),
            colorspace=fitz.csRGB,
            alpha=False,
        )
        return pixmap.tobytes("png")
    finally:
        document.close()


def _render_selections(value: Any) -> tuple[tuple[int, int], ...]:
    if type(value) is not tuple or not value:
        raise _error("page-render selections must be one non-empty exact tuple")
    result = []
    for raw in value:
        if type(raw) is not dict or set(raw) != _RENDER_SELECTION_FIELDS:
            raise _error("page-render selection shape drifted")
        result.append(
            (
                _positive_int(raw["document_ordinal"], "document ordinal"),
                _positive_int(raw["physical_page"], "physical page"),
            )
        )
    if result != sorted(set(result)):
        raise _error("page-render selections must be unique and source ordered")
    return tuple(result)


def _authenticated_renders(
    capability: Any, *, selections: tuple[dict[str, int], ...]
) -> tuple[tuple[dict[str, Any], bytes], ...]:
    locators = _render_selections(selections)
    try:
        index_state, index_manifest = index_v1._live_index(capability)
        archive_state, archive_manifest, _batch, plan, _private = archive_v1._archive_payloads(
            index_state.archive
        )
    except (
        index_v1.FamilyFirstSemanticIndexV1Error,
        archive_v1.FamilyFirstSemanticLabelArchiveV1Error,
    ) as exc:
        raise _error("live semantic/archive capability replay failed") from exc
    if archive_state.root != index_state.root:
        raise _error("semantic index and source archive belong to different roots")

    results = []
    stable_inputs = []
    for ordinal, page_number in locators:
        planned = _document(plan, ordinal)
        if page_number > planned["page_count"]:
            raise _error("physical page lies outside the authenticated filing denominator")
        if (
            ordinal > len(index_manifest["documents"])
            or index_manifest["documents"][ordinal - 1]["document_ordinal"] != ordinal
        ):
            raise _error("semantic index document denominator drifted")

        relative = (
            Path("output/calibration/family-first-semantic-label-cache-v1/documents")
            / f"document-{ordinal:04d}"
            / f"page-{page_number:04d}"
            / "page.json"
        )
        page_payload = archive_v1._root_bytes(
            archive_state.root, relative, "semantic-label page artifact"
        )
        page_artifact = archive_v1._page_artifact(
            archive_v1._historical_cache_object(page_payload, "semantic-label page artifact")
        )
        try:
            page_freeze = freeze_v1._validate_page(page_artifact["page_freeze"])
        except freeze_v1.FamilyFirstSemanticLabelFreezeV1Error as exc:
            raise _error("sealed page-freeze contract drifted") from exc
        if (
            page_artifact["plan_id"] != plan["plan_id"]
            or page_artifact["document_ordinal"] != ordinal
            or page_artifact["physical_page"] != page_number
            or page_freeze["physical_page"] != page_number
        ):
            raise _error("sealed page artifact belongs to another source page")

        source_path = planned["source_pdf_ref"]["path"]
        source = archive_v1._root_bytes(archive_state.root, source_path, "authenticated source PDF")
        archive_v1._matches_ref(source, planned["source_pdf_ref"], "authenticated source PDF")
        dpi = plan["render_policy"]["dpi"]
        if type(dpi) is not int or dpi <= 0:
            raise _error("authenticated render DPI drifted")
        render = _render_page(source, physical_page=page_number, dpi=dpi)
        reference = _render_reference(page_freeze["render_ref"])
        image = _png_image(render)
        if (
            len(render) != reference["size_bytes"]
            or hashlib.sha256(render).hexdigest() != reference["sha256"]
            or image.width != reference["pixel_width"]
            or image.height != reference["pixel_height"]
        ):
            raise _error("re-rendered source page differs from its sealed render reference")
        material = {
            "archive_id": archive_manifest["archive_id"],
            "authority": canonical_clone_v1(_RENDER_AUTHORITY),
            "document_ordinal": ordinal,
            "format_version": RENDER_FORMAT_VERSION,
            "index_id": index_manifest["index_id"],
            "physical_page": page_number,
            "plan_id": plan["plan_id"],
            "render_ref": reference,
            "state": "AUTHENTICATED_EXACT_SOURCE_PAGE_RENDER_SNAPSHOT",
        }
        results.append(
            (
                {
                    **material,
                    "render_id": "ffaprv1:render:" + canonical_json_sha256_v1(material),
                },
                render,
            )
        )
        stable_inputs.append((source_path, source, relative, page_payload))

    try:
        final_index_state, final_index_manifest = index_v1._live_index(capability)
        final_archive_state, final_archive_manifest, _batch, final_plan, _private = (
            archive_v1._archive_payloads(final_index_state.archive)
        )
    except (
        index_v1.FamilyFirstSemanticIndexV1Error,
        archive_v1.FamilyFirstSemanticLabelArchiveV1Error,
    ) as exc:
        raise _error("live capability changed while replaying source pages") from exc
    if (
        final_index_state is not index_state
        or final_archive_state is not archive_state
        or not same_typed_json_v1(final_index_manifest, index_manifest)
        or not same_typed_json_v1(final_archive_manifest, archive_manifest)
        or not same_typed_json_v1(final_plan, plan)
    ):
        raise _error("archive, semantic index, or render plan changed during batched replay")
    for source_path, source, relative, page_payload in stable_inputs:
        if (
            archive_v1._root_bytes(archive_state.root, source_path, "authenticated source PDF")
            != source
            or archive_v1._root_bytes(archive_state.root, relative, "semantic-label page artifact")
            != page_payload
        ):
            raise _error("source or page changed during render replay (batched snapshot)")
    return tuple(results)


def _authenticated_render(
    capability: Any, *, document_ordinal: int, physical_page: int
) -> tuple[dict[str, Any], bytes]:
    return _authenticated_renders(
        capability,
        selections=(
            {
                "document_ordinal": document_ordinal,
                "physical_page": physical_page,
            },
        ),
    )[0]


def read_authenticated_family_first_page_render_v1(
    capability: index_v1.AuthenticatedFamilyFirstSemanticIndexV1,
    *,
    document_ordinal: int,
    physical_page: int,
) -> dict[str, Any]:
    """Return one immutable, exact-replayed source-page PNG snapshot."""

    record, render = _authenticated_render(
        capability,
        document_ordinal=document_ordinal,
        physical_page=physical_page,
    )
    return {**record, "render_png_bytes": render}


def read_authenticated_family_first_page_renders_v1(
    capability: index_v1.AuthenticatedFamilyFirstSemanticIndexV1,
    *,
    selections: tuple[dict[str, int], ...],
) -> tuple[dict[str, Any], ...]:
    """Return several source-ordered renders from one authenticated snapshot."""

    return tuple(
        {**record, "render_png_bytes": render}
        for record, render in _authenticated_renders(capability, selections=selections)
    )


def _validated_render_snapshot(value: Any) -> tuple[dict[str, Any], bytes]:
    if (
        type(value) is not dict
        or set(value) != _RENDER_SNAPSHOT_FIELDS
        or value["format_version"] != RENDER_FORMAT_VERSION
        or value["state"] != "AUTHENTICATED_EXACT_SOURCE_PAGE_RENDER_SNAPSHOT"
        or not same_typed_json_v1(value["authority"], _RENDER_AUTHORITY)
        or type(value["archive_id"]) is not str
        or not value["archive_id"]
        or type(value["index_id"]) is not str
        or not value["index_id"]
        or type(value["plan_id"]) is not str
        or not value["plan_id"]
        or type(value["render_id"]) is not str
        or type(value["render_png_bytes"]) is not bytes
    ):
        raise _error("authenticated page-render snapshot shape drifted")
    _positive_int(value["document_ordinal"], "document ordinal")
    _positive_int(value["physical_page"], "physical page")
    reference = _render_reference(value["render_ref"])
    render = value["render_png_bytes"]
    image = _png_image(render)
    if (
        len(render) != reference["size_bytes"]
        or hashlib.sha256(render).hexdigest() != reference["sha256"]
        or image.width != reference["pixel_width"]
        or image.height != reference["pixel_height"]
    ):
        raise _error("authenticated page-render snapshot bytes drifted")
    material = {
        key: canonical_clone_v1(item)
        for key, item in value.items()
        if key not in {"render_id", "render_png_bytes"}
    }
    if value["render_id"] != "ffaprv1:render:" + canonical_json_sha256_v1(material):
        raise _error("authenticated page-render snapshot identity drifted")
    return material, render


def _crop_authenticated_family_first_page_render_snapshot_v1(
    render_snapshot: dict[str, Any], *, raw_pixel_bbox: list[int]
) -> dict[str, Any]:
    """Crop one already authenticated immutable page-render snapshot."""

    render_record, render = _validated_render_snapshot(render_snapshot)
    image = _png_image(render)
    proposed_bbox = _region_bbox(raw_pixel_bbox, width=image.width, height=image.height)
    recognition_bbox, localization_status = _foreground_recognition_bbox(image, proposed_bbox)
    crop = ImageOps.expand(
        image.crop(tuple(recognition_bbox)).convert("RGB"),
        border=WHITE_BORDER,
        fill=(255, 255, 255),
    )
    stream = io.BytesIO()
    crop.save(stream, format="PNG", optimize=False, compress_level=9)
    payload = stream.getvalue()
    crop_ref = {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    material = {
        "authority": canonical_clone_v1(_REGION_AUTHORITY),
        "document_ordinal": render_record["document_ordinal"],
        "format_version": FORMAT_VERSION,
        "index_id": render_record["index_id"],
        "ink_localization_status": localization_status,
        "physical_page": render_record["physical_page"],
        "proposed_raw_pixel_bbox": proposed_bbox,
        "recognition_raw_pixel_bbox": recognition_bbox,
        "region_png_ref": crop_ref,
        "render_id": render_snapshot["render_id"],
        "render_ref": canonical_clone_v1(render_record["render_ref"]),
        "state": "AUTHENTICATED_RENDER_CALLER_PROPOSED_REGION_CROP",
        "white_border": list(WHITE_BORDER),
    }
    return {
        **material,
        "region_id": "ffaprv1:region:" + canonical_json_sha256_v1(material),
        "region_png_bytes": payload,
    }


def crop_authenticated_family_first_page_region_v1(
    capability: index_v1.AuthenticatedFamilyFirstSemanticIndexV1,
    *,
    document_ordinal: int,
    physical_page: int,
    raw_pixel_bbox: list[int],
) -> dict[str, Any]:
    """Crop a proposed cell/region even when PP-OCRv6 detector emitted no box."""

    snapshot = read_authenticated_family_first_page_render_v1(
        capability,
        document_ordinal=document_ordinal,
        physical_page=physical_page,
    )
    return _crop_authenticated_family_first_page_render_snapshot_v1(
        snapshot, raw_pixel_bbox=raw_pixel_bbox
    )
