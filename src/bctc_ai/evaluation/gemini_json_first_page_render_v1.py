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
_NONPAINTED_DISPLAY_TYPES = frozenset({"ignore-text"})


class GeminiJsonFirstPageRenderV1Error(RuntimeError):
    pass


@dataclass(frozen=True)
class FullPdfPageRenderV1:
    image: bytes
    page: dict[str, Any]
    receipt: dict[str, Any]


def _rect_values(rect: fitz.Rect) -> list[float]:
    return [round(float(value), 6) for value in (rect.x0, rect.y0, rect.x1, rect.y1)]


def _valid_rect(rect: fitz.Rect) -> bool:
    return (
        not rect.is_empty
        and not rect.is_infinite
        and all(math.isfinite(value) for value in (rect.x0, rect.y0, rect.x1, rect.y1))
    )


def _painted_content_bounds(page: fitz.Page) -> tuple[fitz.Rect | None, int]:
    bounds = None
    count = 0
    for entry in page.get_bboxlog():
        if type(entry) is not tuple or len(entry) < 2 or type(entry[0]) is not str:
            raise GeminiJsonFirstPageRenderV1Error("PDF display-list bounds are invalid")
        if entry[0] in _NONPAINTED_DISPLAY_TYPES:
            continue
        rect = fitz.Rect(entry[1])
        if not _valid_rect(rect):
            continue
        if bounds is None:
            bounds = fitz.Rect(rect)
        else:
            bounds.include_rect(rect)
        count += 1
    return bounds, count


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
    painted, painted_object_count = _painted_content_bounds(page)
    if painted is None:
        return original, None, painted_object_count
    allowed = fitz.Rect(
        original.x0 - original.width * MAX_PAGE_BOX_EXPANSION_RATIO,
        original.y0 - original.height * MAX_PAGE_BOX_EXPANSION_RATIO,
        original.x1 + original.width * MAX_PAGE_BOX_EXPANSION_RATIO,
        original.y1 + original.height * MAX_PAGE_BOX_EXPANSION_RATIO,
    )
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
    original_media = fitz.Rect(page.mediabox)
    original_crop = fitz.Rect(page.cropbox)
    selected_media, painted, painted_object_count = _selected_media_box(page)
    source_bounds_expanded = (
        _rect_delta(selected_media, original_media) > PAGE_BOX_EQUALITY_TOLERANCE_POINTS
    )
    declared_crop_expanded = (
        _rect_delta(original_crop, original_media) > PAGE_BOX_EQUALITY_TOLERANCE_POINTS
    )
    expanded = source_bounds_expanded or declared_crop_expanded
    if expanded:
        # PyMuPDF resets CropBox to the complete local page rectangle when the
        # MediaBox is assigned.  Assigning ``selected_media`` again as a
        # CropBox is incorrect for MediaBoxes with a negative origin because
        # CropBox coordinates are local to that newly assigned media extent.
        page.set_mediabox(selected_media)
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
        "mode": (
            "EXPANDED_SOURCE_CONTENT_BOUNDS"
            if source_bounds_expanded
            else "EXPANDED_DECLARED_MEDIA_BOX"
            if declared_crop_expanded
            else "DECLARED_PAGE_BOX"
        ),
        "material_overflow_ratio": format(MIN_MATERIAL_OVERFLOW_RATIO, ".2f"),
        "original_crop_box": _rect_values(original_crop),
        "original_media_box": _rect_values(original_media),
        "painted_content_box": None if painted is None else _rect_values(painted),
        "painted_object_count": painted_object_count,
        "physical_page": physical_page,
        "rotation_degrees": page.rotation,
        "selected_media_box": _rect_values(selected_media),
        "source_sha256": source_sha256,
    }
    return FullPdfPageRenderV1(image=image, page=page_record, receipt=receipt)
