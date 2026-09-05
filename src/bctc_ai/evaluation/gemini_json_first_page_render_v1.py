"""Render one complete PDF page for Gemini without trusting a broken page box.

Some filings contain painted PDF objects outside their declared MediaBox or
CropBox.  A normal renderer clips those objects even though they belong to the
same physical page.  This module performs one bounded source-level repair: it
expands the in-memory page box to include the PDF display-list bounds, then
renders one whole-page image.  The bounds are never used to infer tables,
labels, hierarchy, or accounting meaning.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

import fitz

FORMAT_VERSION = "GEMINI_JSON_FIRST_FULL_PDF_PAGE_RENDER_V1"
MAX_PAGE_BOX_EXPANSION_RATIO = 0.25
MIN_MATERIAL_OVERFLOW_RATIO = 0.03
MIN_MATERIAL_OVERFLOW_POINTS = 8.0
EDGE_PADDING_POINTS = 2.0
PAGE_BOX_EQUALITY_TOLERANCE_POINTS = 0.5
MIN_FULL_PAGE_IMAGE_COVERAGE_RATIO = 0.95
MIN_RECURRING_MASKED_OVERLAY_OCCURRENCES = 3
MIN_RECURRING_MASKED_OVERLAY_DOCUMENT_RATIO = 0.5
_NONPAINTED_DISPLAY_TYPES = frozenset({"ignore-text"})


class GeminiJsonFirstPageRenderV1Error(RuntimeError):
    pass


@dataclass(frozen=True)
class FullPdfPageRenderV1:
    image: bytes
    page: dict[str, Any]
    receipt: dict[str, Any]


@dataclass(frozen=True)
class FullPdfPageBoxInspectionV1:
    mode: str
    original_crop: fitz.Rect
    original_media: fitz.Rect
    painted: fitz.Rect | None
    painted_object_count: int
    selected_media: fitz.Rect


def _rect_values(rect: fitz.Rect) -> list[float]:
    return [round(float(value), 6) for value in (rect.x0, rect.y0, rect.x1, rect.y1)]


def _valid_rect(rect: fitz.Rect) -> bool:
    return (
        not rect.is_empty
        and not rect.is_infinite
        and all(math.isfinite(value) for value in (rect.x0, rect.y0, rect.x1, rect.y1))
    )


def _painted_content_entries(page: fitz.Page) -> list[tuple[str, fitz.Rect]]:
    entries: list[tuple[str, fitz.Rect]] = []
    for entry in page.get_bboxlog():
        if type(entry) is not tuple or len(entry) < 2 or type(entry[0]) is not str:
            raise GeminiJsonFirstPageRenderV1Error("PDF display-list bounds are invalid")
        if entry[0] in _NONPAINTED_DISPLAY_TYPES:
            continue
        rect = fitz.Rect(entry[1])
        if not _valid_rect(rect):
            continue
        entries.append((entry[0], rect))
    return entries


def _allowed_page_box(original: fitz.Rect) -> fitz.Rect:
    return fitz.Rect(
        original.x0 - original.width * MAX_PAGE_BOX_EXPANSION_RATIO,
        original.y0 - original.height * MAX_PAGE_BOX_EXPANSION_RATIO,
        original.x1 + original.width * MAX_PAGE_BOX_EXPANSION_RATIO,
        original.y1 + original.height * MAX_PAGE_BOX_EXPANSION_RATIO,
    )


def _image_info_for_bbox(
    image_infos: list[dict[str, Any]], rect: fitz.Rect
) -> dict[str, Any] | None:
    matches = [
        info
        for info in image_infos
        if type(info) is dict
        and "bbox" in info
        and _rect_delta(fitz.Rect(info["bbox"]), rect) <= PAGE_BOX_EQUALITY_TOLERANCE_POINTS
    ]
    return matches[0] if len(matches) == 1 else None


def _has_unmasked_full_page_image(image_infos: list[dict[str, Any]], original: fitz.Rect) -> bool:
    if original.get_area() <= 0:
        return False
    for info in image_infos:
        if type(info) is not dict or info.get("has-mask") is not False:
            continue
        rect = fitz.Rect(info.get("bbox", ()))
        if not _valid_rect(rect):
            continue
        covered = (rect & original).get_area() / original.get_area()
        if covered >= MIN_FULL_PAGE_IMAGE_COVERAGE_RATIO:
            return True
    return False


def _is_recurring_masked_overlay(page: fitz.Page, *, image_info: dict[str, Any]) -> bool:
    """Recognize only a repeated transparent overlay with one safe sibling placement.

    Scanned filings can reuse one portrait watermark XObject on every page.  On a
    landscape page its unchanged portrait placement extends far below MediaBox,
    even though a separate unmasked scan already covers the complete declared
    page.  Such an overlay must not authorize a page-box expansion.  Requiring the
    exact masked XObject on a majority of document pages, plus a bounded sibling
    placement, keeps this exception limited to document-wide decoration.
    """

    xref = image_info.get("xref")
    if image_info.get("has-mask") is not True or type(xref) is not int or xref <= 0:
        return False
    document = page.parent
    if document is None or len(document) < MIN_RECURRING_MASKED_OVERLAY_OCCURRENCES:
        return False
    occurrence_pages: set[int] = set()
    has_bounded_sibling_placement = False
    for sibling in document:
        sibling_media = fitz.Rect(sibling.mediabox)
        if not _valid_rect(sibling_media):
            continue
        sibling_allowed = _allowed_page_box(sibling_media)
        for sibling_info in sibling.get_image_info(xrefs=True):
            if (
                type(sibling_info) is not dict
                or sibling_info.get("xref") != xref
                or sibling_info.get("has-mask") is not True
            ):
                continue
            occurrence_pages.add(sibling.number)
            sibling_bbox = fitz.Rect(sibling_info.get("bbox", ()))
            if (
                sibling.number != page.number
                and _valid_rect(sibling_bbox)
                and sibling_allowed.contains(sibling_bbox)
            ):
                has_bounded_sibling_placement = True
    minimum = max(
        MIN_RECURRING_MASKED_OVERLAY_OCCURRENCES,
        math.ceil(len(document) * MIN_RECURRING_MASKED_OVERLAY_DOCUMENT_RATIO),
    )
    return len(occurrence_pages) >= minimum and has_bounded_sibling_placement


def _painted_content_bounds(
    page: fitz.Page, *, original: fitz.Rect, allowed: fitz.Rect
) -> tuple[fitz.Rect | None, int]:
    entries = _painted_content_entries(page)
    image_infos = list(page.get_image_info(xrefs=True))
    has_full_page_scan = _has_unmasked_full_page_image(image_infos, original)
    bounds = None
    for entry_type, source_rect in entries:
        rect = fitz.Rect(source_rect)
        if entry_type == "fill-image" and not allowed.contains(rect) and has_full_page_scan:
            image_info = _image_info_for_bbox(image_infos, rect)
            if image_info is not None and _is_recurring_masked_overlay(page, image_info=image_info):
                rect &= original
                if not _valid_rect(rect):
                    continue
        if bounds is None:
            bounds = fitz.Rect(rect)
        else:
            bounds.include_rect(rect)
    return bounds, len(entries)


def _rect_delta(left: fitz.Rect, right: fitz.Rect) -> float:
    return max(
        abs(float(left.x0) - float(right.x0)),
        abs(float(left.y0) - float(right.y0)),
        abs(float(left.x1) - float(right.x1)),
        abs(float(left.y1) - float(right.y1)),
    )


def _selected_media_box(page: fitz.Page) -> tuple[fitz.Rect, fitz.Rect | None, int]:
    original = fitz.Rect(page.mediabox)
    if not _valid_rect(original):
        raise GeminiJsonFirstPageRenderV1Error("PDF MediaBox is invalid")
    allowed = _allowed_page_box(original)
    painted, painted_object_count = _painted_content_bounds(
        page, original=original, allowed=allowed
    )
    if painted is None:
        return original, None, painted_object_count
    if not allowed.contains(painted):
        raise GeminiJsonFirstPageRenderV1Error(
            "painted PDF content exceeds the bounded whole-page expansion"
        )
    horizontal_threshold = max(
        MIN_MATERIAL_OVERFLOW_POINTS,
        original.width * MIN_MATERIAL_OVERFLOW_RATIO,
    )
    vertical_threshold = max(
        MIN_MATERIAL_OVERFLOW_POINTS,
        original.height * MIN_MATERIAL_OVERFLOW_RATIO,
    )
    selected = fitz.Rect(original)
    if original.x0 - painted.x0 > horizontal_threshold:
        selected.x0 = painted.x0 - EDGE_PADDING_POINTS
    if original.y0 - painted.y0 > vertical_threshold:
        selected.y0 = painted.y0 - EDGE_PADDING_POINTS
    if painted.x1 - original.x1 > horizontal_threshold:
        selected.x1 = painted.x1 + EDGE_PADDING_POINTS
    if painted.y1 - original.y1 > vertical_threshold:
        selected.y1 = painted.y1 + EDGE_PADDING_POINTS
    if not allowed.contains(selected):
        raise GeminiJsonFirstPageRenderV1Error(
            "whole-page edge padding exceeds the bounded expansion"
        )
    return selected, painted, painted_object_count


def inspect_full_pdf_page_box_v1(page: fitz.Page) -> FullPdfPageBoxInspectionV1:
    """Inspect only the physical canvas; never infer table or semantic structure."""

    original_media = fitz.Rect(page.mediabox)
    original_crop = fitz.Rect(page.cropbox)
    selected_media, painted, painted_object_count = _selected_media_box(page)
    source_bounds_expanded = (
        _rect_delta(selected_media, original_media) > PAGE_BOX_EQUALITY_TOLERANCE_POINTS
    )
    declared_crop_expanded = (
        _rect_delta(original_crop, original_media) > PAGE_BOX_EQUALITY_TOLERANCE_POINTS
    )
    return FullPdfPageBoxInspectionV1(
        mode=(
            "EXPANDED_SOURCE_CONTENT_BOUNDS"
            if source_bounds_expanded
            else "EXPANDED_DECLARED_MEDIA_BOX"
            if declared_crop_expanded
            else "DECLARED_PAGE_BOX"
        ),
        original_crop=original_crop,
        original_media=original_media,
        painted=painted,
        painted_object_count=painted_object_count,
        selected_media=selected_media,
    )


def render_full_pdf_page_v1(
    page: fitz.Page,
    *,
    physical_page: int,
    dpi: int,
    source_sha256: str,
) -> FullPdfPageRenderV1:
    """Return one 200/300-DPI whole-page PNG and its source-bound receipt."""

    if type(physical_page) is not int or physical_page <= 0:
        raise GeminiJsonFirstPageRenderV1Error("physical page is invalid")
    if dpi not in {200, 300}:
        raise GeminiJsonFirstPageRenderV1Error("render DPI must be 200 or 300")
    if (
        type(source_sha256) is not str
        or len(source_sha256) != 64
        or any(character not in "0123456789abcdef" for character in source_sha256)
    ):
        raise GeminiJsonFirstPageRenderV1Error("source SHA-256 is invalid")
    inspection = inspect_full_pdf_page_box_v1(page)
    if inspection.mode != "DECLARED_PAGE_BOX":
        # PyMuPDF resets CropBox to the complete local page rectangle when the
        # MediaBox is assigned.  Assigning ``selected_media`` again as a
        # CropBox is incorrect for MediaBoxes with a negative origin because
        # CropBox coordinates are local to that newly assigned media extent.
        page.set_mediabox(inspection.selected_media)
    pixmap = page.get_pixmap(dpi=dpi, alpha=False)
    image = pixmap.tobytes("png")
    image_sha256 = sha256(image).hexdigest()
    page_record = {
        "physical_page": physical_page,
        "image_sha256": image_sha256,
        "image_size_bytes": len(image),
        "pixel_width": pixmap.width,
        "pixel_height": pixmap.height,
        "render_dpi": dpi,
        "media_type": "image/png",
    }
    receipt = {
        "dpi": dpi,
        "expansion_ratio_limit": format(MAX_PAGE_BOX_EXPANSION_RATIO, ".2f"),
        "format_version": FORMAT_VERSION,
        "image": {
            "height": pixmap.height,
            "media_type": "image/png",
            "sha256": image_sha256,
            "size_bytes": len(image),
            "width": pixmap.width,
        },
        "mode": inspection.mode,
        "material_overflow_ratio": format(MIN_MATERIAL_OVERFLOW_RATIO, ".2f"),
        "original_crop_box": _rect_values(inspection.original_crop),
        "original_media_box": _rect_values(inspection.original_media),
        "painted_content_box": (
            None if inspection.painted is None else _rect_values(inspection.painted)
        ),
        "painted_object_count": inspection.painted_object_count,
        "physical_page": physical_page,
        "rotation_degrees": page.rotation,
        "selected_media_box": _rect_values(inspection.selected_media),
        "source_sha256": source_sha256,
    }
    return FullPdfPageRenderV1(image=image, page=page_record, receipt=receipt)
