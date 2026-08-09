"""Generic causal visibility engine for native PDF text paints.

This is a deliberate V1 port of the already regression-tested causal render
core in bctc_ai.tables.native_tm_regions. Keeping that registered producer
byte-stable avoids invalidating historical ledgers while the OCR-layer API is
proved by parity tests. A later versioned migration may consolidate the two
implementations after all registered consumers move to this generic boundary.

The module is source-visual only. It contains no table, statement, accounting,
schema, Role A, mapping, bank, page-number, or financial-value logic.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from math import ceil, isfinite
from statistics import median
from typing import Any, Protocol

import fitz
from pymupdf import mupdf

from bctc_ai.core.contracts import BoundingBox
from bctc_ai.core.text import normalize_text
from bctc_ai.ocr.native_text_quality_v2 import apply_native_text_quality_v2
from bctc_ai.ocr.pdf_text import PDFTextPage, PDFWord, extract_pdf_text_page


class CausalNativeTextError(ValueError):
    """Native text visibility cannot be established without guessing."""


class CausalVisibilityPolicy(Protocol):
    """Minimum source-visual policy surface consumed by the causal engine."""

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


_MATERIAL_PAINTED_OCCLUSION_RATIO = 0.09
_FULL_HEIGHT_PAINTED_OCCLUSION_RATIO = 0.90


@dataclass(frozen=True)
class ExcludedNativeTextSpan:
    page: int
    raw_text: str
    bbox: BoundingBox
    block_number: int
    line_number: int
    span_number: int
    color: int
    alpha: int
    render_sequence: int
    occluding_sequence: int | None
    occluding_object_type: str | None
    reason: str


@dataclass(frozen=True)
class VisibleNativeTextPage:
    page: PDFTextPage
    excluded_spans: tuple[ExcludedNativeTextSpan, ...]


@dataclass(frozen=True)
class _NativeTextRenderIdentity:
    last_sequence: int
    painted_bbox: BoundingBox
    event_sequences: tuple[int, ...]


@dataclass(frozen=True)
class _GrayRaster:
    x: int
    y: int
    width: int
    height: int
    stride: int
    samples: bytes


@dataclass(frozen=True)
class _RGBRaster:
    x: int
    y: int
    width: int
    height: int
    stride: int
    samples: bytes


@dataclass(frozen=True)
class _GlyphAlphaMask:
    x: int
    y: int
    width: int
    height: int
    alpha: bytes
    paint_alpha: float


@dataclass(frozen=True)
class _TextPaint:
    color: int
    opacity: float
    kind: str


def _union(boxes: Iterable[BoundingBox]) -> BoundingBox:
    materialized = tuple(boxes)
    if not materialized:
        raise CausalNativeTextError("cannot union an empty set of source boxes")
    return BoundingBox(
        min(box.x0 for box in materialized),
        min(box.y0 for box in materialized),
        max(box.x1 for box in materialized),
        max(box.y1 for box in materialized),
    )


def _color_channels(color: int) -> tuple[int, int, int]:
    return ((color >> 16) & 255, (color >> 8) & 255, color & 255)


def _mupdf_matrix(matrix: fitz.Matrix) -> mupdf.FzMatrix:
    return mupdf.FzMatrix(matrix.a, matrix.b, matrix.c, matrix.d, matrix.e, matrix.f)


def _render_unrotated_raster(
    page: fitz.Page,
    *,
    scale: float,
    textless: bool,
    rgb: bool,
) -> _GrayRaster | _RGBRaster:
    """Render a page in native, unrotated source coordinates.

    The textless branch uses MuPDF's C forwarding/culling device.  It suppresses
    text paint while preserving paths, images, masks, clips, transparency
    groups, annotations, and their render order.  The two rasters are therefore
    a causal counterfactual: their delta is attributable to rendered text, not
    merely to unrelated contrast somewhere inside a padded text bbox.
    """

    derotation = _mupdf_matrix(page.derotation_matrix)
    device_matrix = mupdf.FzMatrix(scale, 0, 0, scale, 0, 0)
    page_bounds = mupdf.fz_bound_page(page.this)
    unrotated_bounds = mupdf.fz_transform_rect(page_bounds, derotation)
    pixmap_bounds = mupdf.fz_round_rect(mupdf.fz_transform_rect(unrotated_bounds, device_matrix))
    pixmap = mupdf.fz_new_pixmap_with_bbox(
        mupdf.fz_device_rgb() if rgb else mupdf.fz_device_gray(),
        pixmap_bounds,
        mupdf.FzSeparations(),
        0,
    )
    mupdf.fz_clear_pixmap_with_value(pixmap, 255)
    draw_device = mupdf.fz_new_draw_device(device_matrix, pixmap)
    run_device = draw_device
    if textless:
        raw_bounds = mupdf.fz_rect()
        raw_bounds.x0 = unrotated_bounds.x0
        raw_bounds.y0 = unrotated_bounds.y0
        raw_bounds.x1 = unrotated_bounds.x1
        raw_bounds.y1 = unrotated_bounds.y1
        regions = mupdf.vector_fz_rect()
        regions.append(raw_bounds)
        run_device = draw_device.fz_new_culling_device_with_rects2(regions)
    try:
        mupdf.fz_run_page(
            page.this,
            run_device,
            derotation,
            mupdf.FzCookie(),
        )
    finally:
        try:
            mupdf.fz_close_device(run_device)
        finally:
            if run_device is not draw_device:
                mupdf.fz_close_device(draw_device)
    samples = mupdf.raw_to_python_bytes(
        pixmap.samples(),
        pixmap.stride() * pixmap.h(),
    )
    raster_type = _RGBRaster if rgb else _GrayRaster
    return raster_type(
        x=int(pixmap.x()),
        y=int(pixmap.y()),
        width=int(pixmap.w()),
        height=int(pixmap.h()),
        stride=int(pixmap.stride()),
        samples=samples,
    )


def _render_unrotated_gray(page: fitz.Page, *, scale: float, textless: bool) -> _GrayRaster:
    rendered = _render_unrotated_raster(
        page,
        scale=scale,
        textless=textless,
        rgb=False,
    )
    if not isinstance(rendered, _GrayRaster):
        raise CausalNativeTextError("native grayscale raster identity is invalid")
    return rendered


def _render_unrotated_rgb(page: fitz.Page, *, scale: float, textless: bool) -> _RGBRaster:
    rendered = _render_unrotated_raster(
        page,
        scale=scale,
        textless=textless,
        rgb=True,
    )
    if not isinstance(rendered, _RGBRaster):
        raise CausalNativeTextError("native RGB raster identity is invalid")
    return rendered


def _render_unrotated_gray_pair(
    page: fitz.Page,
    *,
    scale: float,
) -> tuple[_GrayRaster, _GrayRaster]:
    original = _render_unrotated_gray(page, scale=scale, textless=False)
    textless = _render_unrotated_gray(page, scale=scale, textless=True)
    if (
        original.x,
        original.y,
        original.width,
        original.height,
        original.stride,
    ) != (
        textless.x,
        textless.y,
        textless.width,
        textless.height,
        textless.stride,
    ):
        raise CausalNativeTextError("native and textless raster identities drifted")
    return original, textless


def _render_unrotated_rgb_pair(
    page: fitz.Page,
    *,
    scale: float,
) -> tuple[_RGBRaster, _RGBRaster]:
    original = _render_unrotated_rgb(page, scale=scale, textless=False)
    textless = _render_unrotated_rgb(page, scale=scale, textless=True)
    if (
        original.x,
        original.y,
        original.width,
        original.height,
        original.stride,
    ) != (
        textless.x,
        textless.y,
        textless.width,
        textless.height,
        textless.stride,
    ):
        raise CausalNativeTextError("native and textless RGB raster identities drifted")
    return original, textless


class _ExpectedGlyphMaskDevice(mupdf.FzDevice2):
    """Capture exact MuPDF glyph alpha while preserving bboxlog identity."""

    def __init__(
        self,
        bbox_log: tuple[tuple[Any, ...], ...],
        *,
        scale: float,
    ) -> None:
        super().__init__()
        self.bbox_log = bbox_log
        self.scale = scale
        self.sequence = 0
        self.masks: dict[int, _GlyphAlphaMask] = {}
        self.paints: dict[int, _TextPaint] = {}
        self.device_rgb = mupdf.FzColorspace(mupdf.FzColorspace.Fixed_RGB)
        self.text_clip_encountered = False
        for callback in (
            "fill_path",
            "stroke_path",
            "fill_text",
            "stroke_text",
            "ignore_text",
            "fill_shade",
            "fill_image",
            "fill_image_mask",
            "clip_text",
            "clip_stroke_text",
        ):
            getattr(self, f"use_virtual_{callback}")()

    def _expect(self, expected: str) -> None:
        if self.sequence >= len(self.bbox_log) or self.bbox_log[self.sequence][0] != expected:
            raise CausalNativeTextError("native glyph device drifted from the render-order log")

    def _advance(self, expected: str) -> None:
        self._expect(expected)
        self.sequence += 1

    def fill_path(self, *_args: Any) -> None:
        self._advance("fill-path")

    def stroke_path(self, *_args: Any) -> None:
        self._advance("stroke-path")

    def fill_shade(self, *_args: Any) -> None:
        self._advance("fill-shade")

    def fill_image(self, *_args: Any) -> None:
        self._advance("fill-image")

    def fill_image_mask(self, *_args: Any) -> None:
        self._advance("fill-imgmask")

    def _paint_text(
        self,
        text: Any,
        stroke: Any,
        ctm: Any,
        colorspace: Any,
        color: Any,
        paint_alpha: float,
        color_params: Any,
        *,
        expected: str,
    ) -> None:
        self._expect(expected)
        sequence = self.sequence
        bound = mupdf.FzRect(mupdf.ll_fz_bound_text(text, stroke, ctm))
        logged_bbox = self.bbox_log[sequence][1]
        if not isinstance(logged_bbox, (list, tuple)) or len(logged_bbox) != 4:
            raise CausalNativeTextError("native glyph render entry lacks a valid bbox")
        if (
            max(
                abs(observed - float(expected_value))
                for observed, expected_value in zip(
                    (bound.x0, bound.y0, bound.x1, bound.y1),
                    logged_bbox,
                    strict=True,
                )
            )
            > 0.02
        ):
            raise CausalNativeTextError("native glyph bounds drifted from the render-order log")
        converted = mupdf.ll_fz_convert_color(
            colorspace,
            color,
            self.device_rgb.m_internal,
            None,
            color_params,
        )
        rgb_channels = tuple(
            round(max(0.0, min(1.0, float(channel))) * 255) for channel in converted[:3]
        )
        if len(rgb_channels) != 3:
            raise CausalNativeTextError("native glyph paint color conversion is malformed")
        self.paints[sequence] = _TextPaint(
            color=(rgb_channels[0] << 16) | (rgb_channels[1] << 8) | rgb_channels[2],
            opacity=float(paint_alpha),
            kind=expected,
        )
        if bound.x1 > bound.x0 and bound.y1 > bound.y0:
            matrix = mupdf.FzMatrix(self.scale, 0, 0, self.scale, 0, 0)
            pixel_bbox = mupdf.fz_round_rect(mupdf.fz_transform_rect(bound, matrix))
            pixmap = mupdf.fz_new_pixmap_with_bbox(
                mupdf.fz_device_gray(),
                pixel_bbox,
                mupdf.FzSeparations(),
                1,
            )
            mupdf.fz_clear_pixmap(pixmap)
            draw_device = mupdf.fz_new_draw_device(matrix, pixmap)
            try:
                if stroke is None:
                    mupdf._mupdf.ll_fz_fill_text(
                        draw_device.m_internal,
                        text,
                        ctm,
                        colorspace,
                        color,
                        1.0,
                        color_params,
                    )
                else:
                    mupdf._mupdf.ll_fz_stroke_text(
                        draw_device.m_internal,
                        text,
                        stroke,
                        ctm,
                        colorspace,
                        color,
                        1.0,
                        color_params,
                    )
            finally:
                mupdf.fz_close_device(draw_device)
            raw = mupdf.raw_to_python_bytes(
                pixmap.samples(),
                pixmap.stride() * pixmap.h(),
            )
            alpha = raw[1::2]
            if len(alpha) != pixmap.w() * pixmap.h():
                raise CausalNativeTextError("native glyph alpha raster is malformed")
            self.masks[sequence] = _GlyphAlphaMask(
                x=int(pixmap.x()),
                y=int(pixmap.y()),
                width=int(pixmap.w()),
                height=int(pixmap.h()),
                alpha=alpha,
                paint_alpha=float(paint_alpha),
            )
        self.sequence += 1

    def fill_text(
        self,
        _context: Any,
        text: Any,
        ctm: Any,
        colorspace: Any,
        color: Any,
        alpha: float,
        color_params: Any,
    ) -> None:
        self._paint_text(
            text,
            None,
            ctm,
            colorspace,
            color,
            alpha,
            color_params,
            expected="fill-text",
        )

    def stroke_text(
        self,
        _context: Any,
        text: Any,
        stroke: Any,
        ctm: Any,
        colorspace: Any,
        color: Any,
        alpha: float,
        color_params: Any,
    ) -> None:
        self._paint_text(
            text,
            stroke,
            ctm,
            colorspace,
            color,
            alpha,
            color_params,
            expected="stroke-text",
        )

    def ignore_text(self, *_args: Any) -> None:
        self._advance("ignore-text")

    def clip_text(self, *_args: Any) -> None:
        self.text_clip_encountered = True

    def clip_stroke_text(self, *_args: Any) -> None:
        self.text_clip_encountered = True


def _expected_glyph_masks_by_sequence(
    page: fitz.Page,
    bbox_log: tuple[tuple[Any, ...], ...],
    *,
    scale: float,
) -> tuple[dict[int, _GlyphAlphaMask], dict[int, _TextPaint]]:
    device = _ExpectedGlyphMaskDevice(bbox_log, scale=scale)
    mupdf.fz_run_page(
        page.this,
        device,
        _mupdf_matrix(page.derotation_matrix),
        mupdf.FzCookie(),
    )
    if device.text_clip_encountered:
        raise CausalNativeTextError("native text used as a clipping path is unresolved")
    if device.sequence != len(bbox_log):
        raise CausalNativeTextError("native glyph device did not consume the render-order log")
    return device.masks, device.paints


def _merged_span_alpha(
    render_identity: _NativeTextRenderIdentity,
    masks_by_sequence: dict[int, _GlyphAlphaMask],
    paints_by_sequence: dict[int, _TextPaint],
) -> tuple[dict[tuple[int, int], int], int | None]:
    merged: dict[tuple[int, int], int] = {}
    active_colors: set[int] = set()
    for sequence in render_identity.event_sequences:
        mask = masks_by_sequence.get(sequence)
        if mask is None:
            continue
        paint = paints_by_sequence.get(sequence)
        if paint is None or paint.kind not in {"fill-text", "stroke-text"}:
            raise CausalNativeTextError("native glyph mask lacks text-paint authority")
        if not isfinite(mask.paint_alpha) or not 0 <= mask.paint_alpha <= 1:
            raise CausalNativeTextError("native glyph paint alpha is invalid")
        if abs(mask.paint_alpha - paint.opacity) > 1e-6:
            raise CausalNativeTextError("native glyph alpha drifted across render inventories")
        if mask.paint_alpha > 0:
            active_colors.add(paint.color)
        for local_y in range(mask.height):
            offset = local_y * mask.width
            for local_x in range(mask.width):
                alpha = round(mask.alpha[offset + local_x] * mask.paint_alpha)
                if not alpha:
                    continue
                pixel = (mask.x + local_x, mask.y + local_y)
                merged[pixel] = max(alpha, merged.get(pixel, 0))
    if len(active_colors) > 1:
        raise CausalNativeTextError("native text has mixed render-event colors and is unresolved")
    return merged, (next(iter(active_colors)) if active_colors else None)


def _causal_glyph_core_survival(
    *,
    span: dict[str, Any],
    expected_color: int,
    expected_alpha: dict[tuple[int, int], int],
    original: _RGBRaster,
    textless: _RGBRaster,
    policy: CausalVisibilityPolicy,
) -> tuple[
    tuple[float, ...],
    frozenset[tuple[int, int]],
    tuple[frozenset[tuple[int, int]], ...],
    tuple[frozenset[tuple[int, int]], ...],
    tuple[frozenset[tuple[int, int]], ...],
]:
    character_ratios: list[float] = []
    core_by_character: list[frozenset[tuple[int, int]]] = []
    lost_core_by_character: list[frozenset[tuple[int, int]]] = []
    observable_core_by_character: list[frozenset[tuple[int, int]]] = []
    all_core: set[tuple[int, int]] = set()
    for character in span.get("chars", []):
        if str(character.get("c", "")).isspace():
            continue
        raw_bbox = character.get("bbox")
        if not isinstance(raw_bbox, (list, tuple)) or len(raw_bbox) != 4:
            raise CausalNativeTextError("native text character lacks a valid source bbox")
        character_bbox = BoundingBox(*(float(value) for value in raw_bbox))
        character_pixels = {
            pixel: alpha
            for pixel, alpha in expected_alpha.items()
            if character_bbox.x0 * policy.raster_scale - 1e-6
            <= pixel[0] + 0.5
            <= character_bbox.x1 * policy.raster_scale + 1e-6
            and character_bbox.y0 * policy.raster_scale - 1e-6
            <= pixel[1] + 0.5
            <= character_bbox.y1 * policy.raster_scale + 1e-6
        }
        if not character_pixels:
            raise CausalNativeTextError("native character owns no expected glyph pixels")
        maximum_alpha = max(character_pixels.values())
        core_threshold = max(
            policy.minimum_glyph_core_alpha,
            ceil(maximum_alpha * policy.relative_glyph_core_alpha),
        )
        core = {pixel for pixel, alpha in character_pixels.items() if alpha >= core_threshold}
        if not core:
            core = {pixel for pixel, alpha in character_pixels.items() if alpha == maximum_alpha}
        all_core.update(core)
        core_by_character.append(frozenset(core))
        survived_pixels: set[tuple[int, int]] = set()
        observable_pixels: set[tuple[int, int]] = set()
        visible_anchor = False
        for pixel_x, pixel_y in core:
            raster_x = pixel_x - original.x
            raster_y = pixel_y - original.y
            if not (0 <= raster_x < original.width and 0 <= raster_y < original.height):
                raise CausalNativeTextError("native glyph core lies outside the causal raster")
            offset = raster_y * original.stride + raster_x * 3
            observed = original.samples[offset : offset + 3]
            background = textless.samples[offset : offset + 3]
            if len(observed) != 3 or len(background) != 3:
                raise CausalNativeTextError("native RGB causal pixel is malformed")
            expected = _color_channels(expected_color)
            effective_alpha = expected_alpha[(pixel_x, pixel_y)] / 255
            ideal = tuple(
                round(
                    background_channel + effective_alpha * (expected_channel - background_channel)
                )
                for background_channel, expected_channel in zip(
                    background,
                    expected,
                    strict=True,
                )
            )
            expected_delta = tuple(
                ideal_channel - background_channel
                for ideal_channel, background_channel in zip(
                    ideal,
                    background,
                    strict=True,
                )
            )
            expected_energy = sum(channel * channel for channel in expected_delta)
            full_color_delta = max(
                abs(expected_channel - background_channel)
                for expected_channel, background_channel in zip(
                    expected,
                    background,
                    strict=True,
                )
            )
            if not expected_energy or full_color_delta < policy.minimum_visible_contrast:
                continue
            observable_pixels.add((pixel_x, pixel_y))
            visible_anchor = (
                visible_anchor
                or max(abs(channel) for channel in expected_delta)
                >= policy.minimum_visible_contrast
            )
            observed_delta = tuple(
                observed_channel - background_channel
                for observed_channel, background_channel in zip(
                    observed,
                    background,
                    strict=True,
                )
            )
            projection = (
                sum(
                    observed_channel * expected_channel
                    for observed_channel, expected_channel in zip(
                        observed_delta,
                        expected_delta,
                        strict=True,
                    )
                )
                / expected_energy
            )
            if projection >= policy.minimum_causal_contribution_ratio:
                survived_pixels.add((pixel_x, pixel_y))
        if not visible_anchor:
            observable_pixels.clear()
            survived_pixels.clear()
        character_ratios.append(
            len(survived_pixels) / len(observable_pixels) if observable_pixels else 0.0
        )
        observable_core_by_character.append(frozenset(observable_pixels))
        lost_core_by_character.append(frozenset(observable_pixels - survived_pixels))
    if not character_ratios:
        raise CausalNativeTextError("native text span has no non-space character evidence")
    return (
        tuple(character_ratios),
        frozenset(all_core),
        tuple(core_by_character),
        tuple(lost_core_by_character),
        tuple(observable_core_by_character),
    )


def _bbox_has_visible_contrast(
    pixmap: fitz.Pixmap | _GrayRaster,
    bbox: BoundingBox,
    *,
    scale: float,
    minimum_contrast: int,
) -> bool:
    observed = _bbox_samples(pixmap, bbox, scale=scale)
    return bool(observed) and max(observed) - min(observed) >= minimum_contrast


def _bbox_samples(
    pixmap: fitz.Pixmap | _GrayRaster,
    bbox: BoundingBox,
    *,
    scale: float,
) -> list[int]:
    origin_x = int(getattr(pixmap, "x", 0))
    origin_y = int(getattr(pixmap, "y", 0))
    x0 = max(0, min(pixmap.width - 1, int(bbox.x0 * scale) - origin_x))
    y0 = max(0, min(pixmap.height - 1, int(bbox.y0 * scale) - origin_y))
    x1 = max(x0 + 1, min(pixmap.width, int(bbox.x1 * scale + 1) - origin_x))
    y1 = max(y0 + 1, min(pixmap.height, int(bbox.y1 * scale + 1) - origin_y))
    samples = pixmap.samples
    stride = pixmap.stride
    observed: list[int] = []
    for y in range(y0, y1):
        start = y * stride + x0
        observed.extend(samples[start : y * stride + x1])
    return observed


def _bbox_rgb_pixels(
    raster: _RGBRaster,
    bbox: BoundingBox,
    *,
    scale: float,
) -> tuple[tuple[int, int, int], ...]:
    x0 = max(0, min(raster.width - 1, int(bbox.x0 * scale) - raster.x))
    y0 = max(0, min(raster.height - 1, int(bbox.y0 * scale) - raster.y))
    x1 = max(x0 + 1, min(raster.width, int(bbox.x1 * scale + 1) - raster.x))
    y1 = max(y0 + 1, min(raster.height, int(bbox.y1 * scale + 1) - raster.y))
    pixels: list[tuple[int, int, int]] = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            offset = y * raster.stride + x * 3
            channels = raster.samples[offset : offset + 3]
            if len(channels) != 3:
                raise CausalNativeTextError("native RGB bbox sample is malformed")
            pixels.append((channels[0], channels[1], channels[2]))
    return tuple(pixels)


def _inset_for_rendered_interior(
    bbox: BoundingBox,
    *,
    scale: float,
) -> BoundingBox:
    inset = 1.0 / scale
    if bbox.x1 - bbox.x0 <= 2 * inset or bbox.y1 - bbox.y0 <= 2 * inset:
        return bbox
    return BoundingBox(
        bbox.x0 + inset,
        bbox.y0 + inset,
        bbox.x1 - inset,
        bbox.y1 - inset,
    )


def _bbox_has_dark_background(
    pixmap: fitz.Pixmap | _GrayRaster,
    bbox: BoundingBox,
    *,
    scale: float,
    maximum_background_level: int,
) -> bool:
    observed = _bbox_samples(pixmap, bbox, scale=scale)
    return bool(observed) and median(observed) <= maximum_background_level


def _bbox_coverage(target: BoundingBox, candidate: BoundingBox) -> float:
    width = max(0.0, min(target.x1, candidate.x1) - max(target.x0, candidate.x0))
    height = max(0.0, min(target.y1, candidate.y1) - max(target.y0, candidate.y0))
    target_area = max(0.0, target.x1 - target.x0) * max(0.0, target.y1 - target.y0)
    return width * height / target_area if target_area else 0.0


def _bbox_contains(
    container: BoundingBox,
    target: BoundingBox,
    *,
    tolerance: float = 1e-3,
) -> bool:
    return (
        container.x0 <= target.x0 + tolerance
        and container.y0 <= target.y0 + tolerance
        and container.x1 >= target.x1 - tolerance
        and container.y1 >= target.y1 - tolerance
    )


def _bbox_intersects(first: BoundingBox, second: BoundingBox) -> bool:
    return min(first.x1, second.x1) > max(first.x0, second.x0) and min(first.y1, second.y1) > max(
        first.y0, second.y0
    )


def _bbox_intersection(
    first: BoundingBox,
    second: BoundingBox,
) -> BoundingBox | None:
    x0 = max(first.x0, second.x0)
    y0 = max(first.y0, second.y0)
    x1 = min(first.x1, second.x1)
    y1 = min(first.y1, second.y1)
    return BoundingBox(x0, y0, x1, y1) if x1 > x0 and y1 > y0 else None


def _drawing_rectangle(drawing: dict[str, Any]) -> BoundingBox | None:
    items = tuple(drawing.get("items", ()))
    if len(items) != 1 or items[0][0] != "re":
        return None
    rectangle = items[0][1]
    return BoundingBox(
        float(rectangle.x0),
        float(rectangle.y0),
        float(rectangle.x1),
        float(rectangle.y1),
    )


def _positive_area_render_text_events(
    bbox_log: tuple[tuple[Any, ...], ...],
) -> tuple[tuple[int, BoundingBox], ...]:
    events: list[tuple[int, BoundingBox]] = []
    for sequence, entry in enumerate(bbox_log):
        if not entry or entry[0] not in {"fill-text", "stroke-text", "ignore-text"}:
            continue
        raw_bbox = entry[1]
        if not isinstance(raw_bbox, (list, tuple)) or len(raw_bbox) != 4:
            raise CausalNativeTextError("native render text entry lacks a valid bbox")
        rendered_bbox = BoundingBox(*(float(value) for value in raw_bbox))
        if rendered_bbox.x1 > rendered_bbox.x0 and rendered_bbox.y1 > rendered_bbox.y0:
            events.append((sequence, rendered_bbox))
    return tuple(events)


def _span_and_render_event_are_compatible(
    span_bbox: BoundingBox,
    event_bbox: BoundingBox,
) -> bool:
    return (
        max(
            _bbox_coverage(span_bbox, event_bbox),
            _bbox_coverage(event_bbox, span_bbox),
        )
        >= 0.45
    )


def _render_sequences_for_spans(
    raw_spans: list[tuple[dict[str, Any], tuple[int, int, int], str]],
    bbox_log: tuple[tuple[Any, ...], ...],
) -> dict[tuple[int, int, int], _NativeTextRenderIdentity]:
    """Bind RAWDICT spans to text paint operations without geometry aliasing.

    RAWDICT preserves content-stream order when ``sort=False``.  BBOXLOG
    preserves paint order, but can contain more text operations because
    PyMuPDF may merge adjacent operations into one RAWDICT span.  We therefore
    require a unique order-preserving partition of every positive-area text
    paint event into non-empty contiguous groups, one group per RAWDICT span.
    The span identity is the last paint event in its group: a later covering
    object must follow every fragment of the span.  Independent bbox matching
    is unsafe because two different values painted at the same location can
    otherwise both bind to the old (or both to the replacement) operation.
    """

    if not raw_spans:
        return {}
    span_boxes: list[BoundingBox] = []
    for span, _span_id, _raw_text in raw_spans:
        raw_bbox = span.get("bbox")
        if not isinstance(raw_bbox, (list, tuple)) or len(raw_bbox) != 4:
            raise CausalNativeTextError("native text span lacks a valid source bbox")
        span_boxes.append(BoundingBox(*(float(value) for value in raw_bbox)))

    render_events = _positive_area_render_text_events(bbox_log)
    if len(render_events) < len(span_boxes):
        raise CausalNativeTextError("native render log has fewer text events than source spans")

    # event boundary -> (path count capped at two, first boundary path)
    states: dict[int, tuple[int, tuple[int, ...]]] = {0: (1, ())}
    for index, span_bbox in enumerate(span_boxes):
        next_states: dict[int, tuple[int, tuple[int, ...]]] = {}
        remaining_spans = len(span_boxes) - index - 1
        for start, (path_count, boundary_path) in states.items():
            maximum_end = len(render_events) - remaining_spans
            end = start
            while end < maximum_end and _span_and_render_event_are_compatible(
                span_bbox,
                render_events[end][1],
            ):
                end += 1
                candidate_path = (*boundary_path, end)
                existing = next_states.get(end)
                if existing is None:
                    next_states[end] = (path_count, candidate_path)
                else:
                    next_states[end] = (
                        min(2, existing[0] + path_count),
                        min(existing[1], candidate_path),
                    )
        if not next_states:
            raise CausalNativeTextError(
                "native text spans cannot be partitioned over render-order events"
            )
        states = next_states

    completed = states.get(len(render_events))
    if completed is None:
        raise CausalNativeTextError("native render-order text events are not fully owned")
    path_count, boundary_path = completed
    if path_count != 1:
        raise CausalNativeTextError("native render-order text ownership is ambiguous")

    start = 0
    render_identities: dict[tuple[int, int, int], _NativeTextRenderIdentity] = {}
    for index, (_span, span_id, _raw_text) in enumerate(raw_spans):
        end = boundary_path[index]
        if end <= start:
            raise CausalNativeTextError("native text span owns no render-order event")
        owned_events = render_events[start:end]
        render_identities[span_id] = _NativeTextRenderIdentity(
            last_sequence=owned_events[-1][0],
            painted_bbox=_union(event_bbox for _sequence, event_bbox in owned_events),
            event_sequences=tuple(sequence for sequence, _event_bbox in owned_events),
        )
        start = end
    return render_identities


def _rect_corners(bbox: BoundingBox) -> tuple[tuple[float, float], ...]:
    return (
        (bbox.x0, bbox.y0),
        (bbox.x1, bbox.y0),
        (bbox.x1, bbox.y1),
        (bbox.x0, bbox.y1),
    )


def _cross(
    first: tuple[float, float],
    second: tuple[float, float],
    third: tuple[float, float],
) -> float:
    return (second[0] - first[0]) * (third[1] - second[1]) - (second[1] - first[1]) * (
        third[0] - second[0]
    )


def _convex_polygon_covers_bbox(
    points: tuple[tuple[float, float], ...],
    bbox: BoundingBox,
) -> bool:
    if len(points) < 3:
        return False
    signs = []
    for index in range(len(points)):
        value = _cross(points[index - 1], points[index], points[(index + 1) % len(points)])
        if abs(value) > 1e-7:
            signs.append(value > 0)
    if not signs or len(set(signs)) != 1:
        return False
    orientation = signs[0]
    for corner in _rect_corners(bbox):
        edge_sides = []
        for index in range(len(points)):
            value = _cross(points[index], points[(index + 1) % len(points)], corner)
            if abs(value) > 1e-7:
                edge_sides.append(value > 0)
        if edge_sides and any(side != orientation for side in edge_sides):
            return False
    return True


def _line_polygon(drawing: dict[str, Any]) -> tuple[tuple[float, float], ...] | None:
    items = tuple(drawing.get("items", ()))
    if not items or any(item[0] != "l" for item in items):
        return None
    points: list[tuple[float, float]] = []
    for _kind, start, end in items:
        start_point = (float(start.x), float(start.y))
        end_point = (float(end.x), float(end.y))
        if not points:
            points.append(start_point)
        elif points[-1] != start_point:
            return None
        points.append(end_point)
    if points[0] != points[-1]:
        return None
    return tuple(points[:-1])


def _drawing_shape_covers_bbox(
    drawing: dict[str, Any],
    bbox: BoundingBox,
) -> bool:
    rectangle = _drawing_rectangle(drawing)
    if rectangle is not None:
        return _bbox_contains(rectangle, bbox)
    polygon = _line_polygon(drawing)
    return polygon is not None and _convex_polygon_covers_bbox(polygon, bbox)


def _point_in_bbox(point: tuple[float, float], bbox: BoundingBox) -> bool:
    return bbox.x0 <= point[0] <= bbox.x1 and bbox.y0 <= point[1] <= bbox.y1


def _point_in_convex_polygon(
    point: tuple[float, float],
    polygon: tuple[tuple[float, float], ...],
) -> bool:
    sides = []
    for index in range(len(polygon)):
        value = _cross(polygon[index], polygon[(index + 1) % len(polygon)], point)
        if abs(value) > 1e-7:
            sides.append(value > 0)
    return not sides or len(set(sides)) == 1


def _segments_intersect(
    first_start: tuple[float, float],
    first_end: tuple[float, float],
    second_start: tuple[float, float],
    second_end: tuple[float, float],
) -> bool:
    def on_segment(
        start: tuple[float, float],
        end: tuple[float, float],
        point: tuple[float, float],
    ) -> bool:
        return (
            min(start[0], end[0]) - 1e-7 <= point[0] <= max(start[0], end[0]) + 1e-7
            and min(start[1], end[1]) - 1e-7 <= point[1] <= max(start[1], end[1]) + 1e-7
        )

    values = (
        _cross(first_start, first_end, second_start),
        _cross(first_start, first_end, second_end),
        _cross(second_start, second_end, first_start),
        _cross(second_start, second_end, first_end),
    )
    if abs(values[0]) <= 1e-7 and on_segment(first_start, first_end, second_start):
        return True
    if abs(values[1]) <= 1e-7 and on_segment(first_start, first_end, second_end):
        return True
    if abs(values[2]) <= 1e-7 and on_segment(second_start, second_end, first_start):
        return True
    if abs(values[3]) <= 1e-7 and on_segment(second_start, second_end, first_end):
        return True
    return (values[0] > 0) != (values[1] > 0) and (values[2] > 0) != (values[3] > 0)


def _drawing_shape_intersects_bbox(
    drawing: dict[str, Any],
    bbox: BoundingBox,
) -> bool:
    rectangle = _drawing_rectangle(drawing)
    if rectangle is not None:
        return _bbox_intersects(rectangle, bbox)
    polygon = _line_polygon(drawing)
    if polygon is None:
        raw_rect = drawing.get("rect") or drawing.get("scissor")
        return isinstance(raw_rect, fitz.Rect) and _bbox_intersects(
            BoundingBox(
                float(raw_rect.x0),
                float(raw_rect.y0),
                float(raw_rect.x1),
                float(raw_rect.y1),
            ),
            bbox,
        )
    corners = _rect_corners(bbox)
    if any(_point_in_convex_polygon(corner, polygon) for corner in corners):
        return True
    if any(_point_in_bbox(point, bbox) for point in polygon):
        return True
    rectangle_edges = tuple(
        (corners[index], corners[(index + 1) % len(corners)]) for index in range(len(corners))
    )
    polygon_edges = tuple(
        (polygon[index], polygon[(index + 1) % len(polygon)]) for index in range(len(polygon))
    )
    return any(
        _segments_intersect(*polygon_edge, *rectangle_edge)
        for polygon_edge in polygon_edges
        for rectangle_edge in rectangle_edges
    )


def _opaque_filled_drawing_occlusion(
    drawing: dict[str, Any],
    bbox: BoundingBox,
    *,
    active_render_contexts: tuple[dict[str, Any], ...],
) -> str | None:
    if drawing.get("fill") is None or float(drawing.get("fill_opacity", 0.0)) < 1.0 - 1e-9:
        return None
    fully_covers = _drawing_shape_covers_bbox(drawing, bbox)
    intersects = _drawing_shape_intersects_bbox(drawing, bbox)
    if not intersects:
        return None
    effective_rectangle = _drawing_rectangle(drawing)
    for context in active_render_contexts:
        context_type = context.get("type")
        if context_type == "clip":
            context_intersects = _drawing_shape_intersects_bbox(context, bbox)
            if not context_intersects:
                return None
            fully_covers = fully_covers and _drawing_shape_covers_bbox(context, bbox)
            clip_rectangle = _drawing_rectangle(context)
            effective_rectangle = (
                _bbox_intersection(effective_rectangle, clip_rectangle)
                if effective_rectangle is not None and clip_rectangle is not None
                else None
            )
        elif context_type == "group":
            if (
                float(context.get("opacity", 0.0)) < 1.0 - 1e-9
                or context.get("blendmode") != "Normal"
                or context.get("knockout") is not False
            ):
                return None
            group_rect = context.get("rect")
            if not isinstance(group_rect, fitz.Rect):
                return None
            group_bbox = BoundingBox(
                float(group_rect.x0),
                float(group_rect.y0),
                float(group_rect.x1),
                float(group_rect.y1),
            )
            if not _bbox_intersects(group_bbox, bbox):
                return None
            fully_covers = fully_covers and _bbox_contains(group_bbox, bbox)
            effective_rectangle = (
                _bbox_intersection(effective_rectangle, group_bbox)
                if effective_rectangle is not None
                else None
            )
        else:
            return None
    if fully_covers:
        return "FULL"
    if effective_rectangle is None:
        return "PARTIAL"
    effective_intersection = _bbox_intersection(bbox, effective_rectangle)
    if effective_intersection is None:
        return None
    material_coverage = _bbox_coverage(bbox, effective_intersection)
    height = bbox.y1 - bbox.y0
    height_coverage = (
        (effective_intersection.y1 - effective_intersection.y0) / height if height else 0.0
    )
    return (
        "PARTIAL"
        if material_coverage >= _MATERIAL_PAINTED_OCCLUSION_RATIO
        or height_coverage >= _FULL_HEIGHT_PAINTED_OCCLUSION_RATIO
        else None
    )


def _extended_drawings_by_sequence(
    page: fitz.Page,
) -> tuple[
    dict[int, dict[str, Any]],
    dict[int, tuple[dict[str, Any], ...]],
]:
    drawings: dict[int, dict[str, Any]] = {}
    contexts: dict[int, tuple[dict[str, Any], ...]] = {}
    active_contexts_by_level: dict[int, dict[str, Any]] = {}
    for record in page.get_drawings(extended=True):
        level = record.get("level")
        if not isinstance(level, int) or level < 0:
            raise CausalNativeTextError("native drawing lacks a valid render-context level")
        active_contexts_by_level = {
            context_level: context
            for context_level, context in active_contexts_by_level.items()
            if context_level < level
        }
        record_type = record.get("type")
        if record_type in {"clip", "group"}:
            active_contexts_by_level[level] = record
            continue
        sequence = record.get("seqno")
        if not isinstance(sequence, int) or sequence in drawings:
            raise CausalNativeTextError("native drawing lacks a unique render-order identity")
        drawings[sequence] = record
        contexts[sequence] = tuple(
            active_contexts_by_level[context_level]
            for context_level in sorted(active_contexts_by_level)
        )
    return drawings, contexts


def _image_opacity_by_sequence(
    page: fitz.Page,
    bbox_log: tuple[tuple[Any, ...], ...],
) -> dict[int, bool | None]:
    """Return proven whole-image opacity for each image paint operation.

    ``True`` means every image pixel is opaque, ``False`` means every image
    pixel is fully transparent, and ``None`` means the mask is mixed or cannot
    be audited.
    A mixed mask cannot establish whether the particular covered glyph area is
    opaque without a separate image-coordinate proof, so callers fail closed.
    """

    rendered_images = [
        (sequence, entry)
        for sequence, entry in enumerate(bbox_log)
        if entry and entry[0] in {"fill-image", "fill-imgmask"}
    ]
    if not rendered_images:
        return {}
    image_info = tuple(page.get_image_info(xrefs=True))
    if len(image_info) != len(rendered_images):
        raise CausalNativeTextError("native image inventory does not match render-order log")
    image_xrefs = {int(record[0]): int(record[1]) for record in page.get_images(full=True)}
    opacity_by_sequence: dict[int, bool | None] = {}
    for (sequence, entry), info in zip(rendered_images, image_info, strict=True):
        raw_bbox = entry[1]
        info_bbox = info.get("bbox")
        if (
            not isinstance(raw_bbox, (list, tuple))
            or len(raw_bbox) != 4
            or not isinstance(info_bbox, (list, tuple))
            or len(info_bbox) != 4
        ):
            raise CausalNativeTextError("native image lacks a valid render bbox")
        rendered_bbox = BoundingBox(*(float(value) for value in raw_bbox))
        audited_bbox = BoundingBox(*(float(value) for value in info_bbox))
        if (
            min(
                _bbox_coverage(rendered_bbox, audited_bbox),
                _bbox_coverage(audited_bbox, rendered_bbox),
            )
            < 0.99
        ):
            raise CausalNativeTextError("native image identity drifted across render inventories")
        if info.get("has-mask") is not True:
            opacity_by_sequence[sequence] = True
            continue
        xref = info.get("xref")
        if not isinstance(xref, int) or xref <= 0:
            opacity_by_sequence[sequence] = None
            continue
        mask_xref = image_xrefs.get(xref, 0)
        if mask_xref <= 0 or page.parent is None:
            opacity_by_sequence[sequence] = None
            continue
        mask = fitz.Pixmap(page.parent, mask_xref)
        samples = mask.samples
        minimum = min(samples) if samples else -1
        maximum = max(samples) if samples else -1
        if minimum == maximum == 255:
            opacity_by_sequence[sequence] = True
        elif maximum == 0:
            opacity_by_sequence[sequence] = False
        else:
            opacity_by_sequence[sequence] = None
    return opacity_by_sequence


def _later_covering_render_object(
    bbox: BoundingBox,
    *,
    protected_character_bboxes: tuple[BoundingBox, ...],
    render_sequence: int,
    bbox_log: tuple[tuple[Any, ...], ...],
    drawings_by_sequence: dict[int, dict[str, Any]],
    drawing_contexts_by_sequence: dict[int, tuple[dict[str, Any], ...]],
    image_opacity_by_sequence: dict[int, bool | None],
) -> tuple[str, int, str] | None:
    partial_occlusion: tuple[str, int, str] | None = None
    for sequence, entry in enumerate(bbox_log):
        if sequence <= render_sequence or not entry:
            continue
        object_type = str(entry[0])
        if object_type not in {
            "fill-path",
            "stroke-path",
            "fill-image",
            "fill-imgmask",
            "fill-shade",
        }:
            continue
        raw_bbox = entry[1]
        if not isinstance(raw_bbox, (list, tuple)) or len(raw_bbox) != 4:
            raise CausalNativeTextError("native covering render object lacks a valid bbox")
        covering_bbox = BoundingBox(*(float(value) for value in raw_bbox))
        if not _bbox_intersects(covering_bbox, bbox):
            continue
        if object_type == "fill-shade":
            raise CausalNativeTextError(
                "native text visibility beneath a later shade is unresolved"
            )
        if object_type == "stroke-path":
            # A path's bounding box is not its painted area: ordinary table
            # rules commonly span a text bbox while touching only its fringe.
            # The causal glyph-core check below observes the composited stroke
            # and rejects any material/internal loss without treating a
            # translucent border as a categorical cover.
            continue
        if object_type in {"fill-image", "fill-imgmask"}:
            image_is_opaque = image_opacity_by_sequence.get(sequence)
            if image_is_opaque is False:
                continue
            raise CausalNativeTextError(
                "native text visibility beneath a later image is unresolved"
            )
        drawing = drawings_by_sequence.get(sequence)
        if drawing is None:
            raise CausalNativeTextError("native fill-path lacks render-order drawing evidence")
        occlusion = _opaque_filled_drawing_occlusion(
            drawing,
            bbox,
            active_render_contexts=drawing_contexts_by_sequence.get(sequence, ()),
        )
        if occlusion == "FULL":
            return occlusion, sequence, object_type
        character_occlusion = any(
            _opaque_filled_drawing_occlusion(
                drawing,
                character_bbox,
                active_render_contexts=drawing_contexts_by_sequence.get(sequence, ()),
            )
            == "FULL"
            for character_bbox in protected_character_bboxes
        )
        if (occlusion == "PARTIAL" or character_occlusion) and partial_occlusion is None:
            partial_occlusion = ("PARTIAL", sequence, object_type)
    return partial_occlusion


def _later_render_object_intersects_core_pixel(
    pixel: tuple[int, int],
    *,
    scale: float,
    render_sequence: int,
    bbox_log: tuple[tuple[Any, ...], ...],
    drawings_by_sequence: dict[int, dict[str, Any]],
    drawing_contexts_by_sequence: dict[int, tuple[dict[str, Any], ...]],
) -> bool:
    pixel_bbox = BoundingBox(
        pixel[0] / scale,
        pixel[1] / scale,
        (pixel[0] + 1) / scale,
        (pixel[1] + 1) / scale,
    )
    for sequence, entry in enumerate(bbox_log):
        if sequence <= render_sequence or not entry:
            continue
        object_type = str(entry[0])
        if object_type not in {
            "fill-path",
            "stroke-path",
            "fill-image",
            "fill-imgmask",
            "fill-shade",
            "fill-text",
            "stroke-text",
        }:
            continue
        raw_bbox = entry[1]
        if not isinstance(raw_bbox, (list, tuple)) or len(raw_bbox) != 4:
            raise CausalNativeTextError("native render object lacks a valid core-intersection bbox")
        object_bbox = BoundingBox(*(float(value) for value in raw_bbox))
        if not _bbox_intersects(object_bbox, pixel_bbox):
            continue
        if object_type in {"fill-text", "stroke-text", "fill-image", "fill-imgmask", "fill-shade"}:
            return True
        drawing = drawings_by_sequence.get(sequence)
        if drawing is None:
            raise CausalNativeTextError("native path lacks render-order drawing evidence")
        if object_type == "fill-path" and not _drawing_shape_intersects_bbox(drawing, pixel_bbox):
            continue
        if object_type == "stroke-path":
            raw_rect = drawing.get("rect")
            if not isinstance(raw_rect, fitz.Rect) or not _bbox_intersects(
                BoundingBox(
                    float(raw_rect.x0),
                    float(raw_rect.y0),
                    float(raw_rect.x1),
                    float(raw_rect.y1),
                ),
                pixel_bbox,
            ):
                continue
        permitted_by_context = True
        for context in drawing_contexts_by_sequence.get(sequence, ()):
            context_type = context.get("type")
            if context_type == "clip" and not _drawing_shape_intersects_bbox(context, pixel_bbox):
                permitted_by_context = False
                break
            if context_type == "group":
                raw_rect = context.get("rect")
                if not isinstance(raw_rect, fitz.Rect) or not _bbox_intersects(
                    BoundingBox(
                        float(raw_rect.x0),
                        float(raw_rect.y0),
                        float(raw_rect.x1),
                        float(raw_rect.y1),
                    ),
                    pixel_bbox,
                ):
                    permitted_by_context = False
                    break
        if permitted_by_context:
            return True
    return False


def extract_visible_native_text_page(
    page: fitz.Page,
    policy: CausalVisibilityPolicy,
    *,
    native_text_quality_config: dict[str, Any] | None = None,
) -> VisibleNativeTextPage:
    """Extract native words while excluding source-invisible text spans.

    Native glyph identity, callback paint color/alpha, and paired RGB renders
    establish each character's causal contribution. This preserves visible
    low-contrast, chromatic, and nonopaque text while excluding fully
    transparent/same-background ghosts and rejecting ambiguous occlusion.
    """

    bbox_log = tuple(tuple(entry) for entry in page.get_bboxlog())
    image_opacity_by_sequence = _image_opacity_by_sequence(page, bbox_log)
    drawings_by_sequence, drawing_contexts_by_sequence = _extended_drawings_by_sequence(page)
    text_page = page.get_textpage(flags=fitz.TEXTFLAGS_RAWDICT)
    extracted_identity_words = [
        PDFWord(
            raw_text=item[4],
            normalized_text=normalize_text(item[4]),
            bbox_points=BoundingBox(item[0], item[1], item[2], item[3]),
            block_number=int(item[5]),
            line_number=int(item[6]),
            word_number=int(item[7]),
        )
        for item in page.get_text("words", sort=True, textpage=text_page)
        if normalize_text(item[4])
    ]
    extracted_base = extract_pdf_text_page(page)
    extracted = replace(extracted_base, words=extracted_identity_words)
    raw_spans: list[tuple[dict[str, Any], tuple[int, int, int], str]] = []
    raw_chars_by_line: dict[
        tuple[int, int], list[tuple[str, tuple[int, int, int], BoundingBox]]
    ] = {}
    for block in text_page.extractRAWDICT(sort=False).get("blocks", []):
        if "number" not in block:
            raise CausalNativeTextError("native text block lacks a source identity")
        block_number = int(block["number"])
        for line_number, line in enumerate(block.get("lines", [])):
            for span_number, span in enumerate(line.get("spans", [])):
                span_id = (block_number, line_number, span_number)
                raw_text = "".join(
                    str(character.get("c", "")) for character in span.get("chars", [])
                )
                if not raw_text.strip():
                    continue
                raw_spans.append((span, span_id, raw_text))
                source_characters = []
                for character in span.get("chars", []):
                    raw_character = str(character.get("c", ""))
                    if raw_character.isspace():
                        continue
                    raw_bbox = character.get("bbox")
                    if not isinstance(raw_bbox, (list, tuple)) or len(raw_bbox) != 4:
                        raise CausalNativeTextError(
                            "native text character lacks a valid source bbox"
                        )
                    source_characters.append(
                        (
                            raw_character,
                            span_id,
                            BoundingBox(*(float(value) for value in raw_bbox)),
                        )
                    )
                raw_chars_by_line.setdefault((block_number, line_number), []).extend(
                    source_characters
                )
    render_identities = _render_sequences_for_spans(raw_spans, bbox_log)
    original_raster: _RGBRaster | None = None
    textless_raster: _RGBRaster | None = None
    glyph_masks_by_sequence: dict[int, _GlyphAlphaMask] = {}
    text_paints_by_sequence: dict[int, _TextPaint] = {}
    if raw_spans:
        original_raster, textless_raster = _render_unrotated_rgb_pair(
            page,
            scale=policy.raster_scale,
        )
        glyph_masks_by_sequence, text_paints_by_sequence = _expected_glyph_masks_by_sequence(
            page,
            bbox_log,
            scale=policy.raster_scale,
        )
    excluded: list[ExcludedNativeTextSpan] = []
    excluded_span_ids: set[tuple[int, int, int]] = set()
    visible_core_by_span: dict[tuple[int, int, int], frozenset[tuple[int, int]]] = {}
    raw_text_by_id = {span_id: raw_text for _span, span_id, raw_text in raw_spans}
    for span, span_id, raw_text in raw_spans:
        alpha = int(span.get("alpha", 255))
        color = int(span.get("color", 0))
        raw_bbox = span.get("bbox")
        if not isinstance(raw_bbox, (list, tuple)) or len(raw_bbox) != 4:
            raise CausalNativeTextError("native text span lacks a valid source bbox")
        bbox = BoundingBox(*(float(value) for value in raw_bbox))
        render_identity = render_identities[span_id]
        render_sequence = render_identity.last_sequence
        painted_bbox = render_identity.painted_bbox
        protected_character_bboxes: list[BoundingBox] = []
        for character in span.get("chars", []):
            if str(character.get("c", "")).isspace():
                continue
            character_bbox_raw = character.get("bbox")
            if not isinstance(character_bbox_raw, (list, tuple)) or len(character_bbox_raw) != 4:
                raise CausalNativeTextError("native character lacks a valid source bbox")
            character_bbox = BoundingBox(*(float(value) for value in character_bbox_raw))
            painted_character_bbox = _bbox_intersection(painted_bbox, character_bbox)
            if painted_character_bbox is not None:
                protected_character_bboxes.append(painted_character_bbox)
        covering_object: tuple[str, int, str] | None = None
        reason: str | None = None
        if not policy.require_causal_visibility_for_nonopaque_text:
            raise CausalNativeTextError("native nonopaque-text causal gate is disabled")
        else:
            covering_object = _later_covering_render_object(
                painted_bbox,
                protected_character_bboxes=tuple(protected_character_bboxes),
                render_sequence=render_sequence,
                bbox_log=bbox_log,
                drawings_by_sequence=drawings_by_sequence,
                drawing_contexts_by_sequence=drawing_contexts_by_sequence,
                image_opacity_by_sequence=image_opacity_by_sequence,
            )
            if covering_object is not None and covering_object[0] == "PARTIAL":
                raise CausalNativeTextError(
                    "native text is materially or character-wise occluded and unresolved"
                )
            if covering_object is not None:
                reason = "later opaque render object fully covers painted native text"
            elif original_raster is None or textless_raster is None:
                raise CausalNativeTextError("native causal text raster is unavailable")
            else:
                expected_alpha, expected_color = _merged_span_alpha(
                    render_identity,
                    glyph_masks_by_sequence,
                    text_paints_by_sequence,
                )
                if not expected_alpha or expected_color is None:
                    if policy.exclude_fully_transparent_text_paints:
                        reason = "native text span owns no source-visible glyph paint"
                    else:
                        raise CausalNativeTextError(
                            "native fully transparent text-paint gate is disabled"
                        )
                else:
                    (
                        survival,
                        core,
                        _character_cores,
                        lost_character_cores,
                        observable_character_cores,
                    ) = _causal_glyph_core_survival(
                        span=span,
                        expected_color=expected_color,
                        expected_alpha=expected_alpha,
                        original=original_raster,
                        textless=textless_raster,
                        policy=policy,
                    )
                    if all(not observable for observable in observable_character_cores):
                        reason = "native glyph paint has no potential source-visible contrast"
                    elif any(not observable for observable in observable_character_cores):
                        raise CausalNativeTextError(
                            "native text is only partially capable of source-visible contrast"
                        )
                    elif any(
                        len(observable) / len(character_core)
                        < policy.minimum_glyph_core_survival_ratio
                        for character_core, observable in zip(
                            _character_cores,
                            observable_character_cores,
                            strict=True,
                        )
                    ):
                        raise CausalNativeTextError(
                            "native glyph core has insufficient observable background coverage"
                        )
                    elif all(ratio == 0 for ratio in survival):
                        if any(
                            _later_render_object_intersects_core_pixel(
                                pixel,
                                scale=policy.raster_scale,
                                render_sequence=render_sequence,
                                bbox_log=bbox_log,
                                drawings_by_sequence=drawings_by_sequence,
                                drawing_contexts_by_sequence=drawing_contexts_by_sequence,
                            )
                            for observable in observable_character_cores
                            for pixel in observable
                        ):
                            raise CausalNativeTextError(
                                "native glyph paint is causally occluded and unresolved"
                            )
                        raise CausalNativeTextError("native glyph color attribution is unresolved")
                    else:
                        fringe_pixels = ceil(policy.raster_scale)
                        for character_core, lost_core in zip(
                            observable_character_cores,
                            lost_character_cores,
                            strict=True,
                        ):
                            if not lost_core:
                                continue
                            minimum_y = min(pixel[1] for pixel in character_core)
                            maximum_y = max(pixel[1] for pixel in character_core)
                            internal_losses = {
                                pixel
                                for pixel in lost_core
                                if pixel[1] - minimum_y > fringe_pixels
                                and maximum_y - pixel[1] > fringe_pixels
                            }
                            if any(
                                _later_render_object_intersects_core_pixel(
                                    pixel,
                                    scale=policy.raster_scale,
                                    render_sequence=render_sequence,
                                    bbox_log=bbox_log,
                                    drawings_by_sequence=drawings_by_sequence,
                                    drawing_contexts_by_sequence=drawing_contexts_by_sequence,
                                )
                                for pixel in internal_losses
                            ):
                                raise CausalNativeTextError(
                                    "native glyph core is internally occluded and unresolved"
                                )
                    if reason is None:
                        if any(
                            ratio < policy.minimum_glyph_core_survival_ratio for ratio in survival
                        ):
                            nonspace_characters = [
                                character
                                for character in span.get("chars", [])
                                if not str(character.get("c", "")).isspace()
                            ]
                            character_bbox = (
                                BoundingBox(
                                    *(
                                        float(value)
                                        for value in nonspace_characters[0].get("bbox", ())
                                    )
                                )
                                if len(nonspace_characters) == 1
                                and isinstance(
                                    nonspace_characters[0].get("bbox"),
                                    (list, tuple),
                                )
                                and len(nonspace_characters[0].get("bbox")) == 4
                                else None
                            )
                            if (
                                character_bbox is not None
                                and _bbox_coverage(painted_bbox, character_bbox) < 0.5
                                and _bbox_coverage(character_bbox, painted_bbox) >= 0.9
                            ):
                                reason = (
                                    "native character geometry owns insufficient causal glyph core"
                                )
                            else:
                                raise CausalNativeTextError(
                                    "native glyph core is only partially source-visible"
                                )
                        if reason is None:
                            visible_core_by_span[span_id] = core
        if reason:
            excluded_span_ids.add(span_id)
            excluded.append(
                ExcludedNativeTextSpan(
                    page=page.number + 1,
                    raw_text=raw_text,
                    bbox=bbox,
                    block_number=span_id[0],
                    line_number=span_id[1],
                    span_number=span_id[2],
                    color=color,
                    alpha=alpha,
                    render_sequence=render_sequence,
                    occluding_sequence=(covering_object[1] if covering_object else None),
                    occluding_object_type=(covering_object[2] if covering_object else None),
                    reason=reason,
                )
            )

    visible_span_ids = tuple(sorted(visible_core_by_span))
    for index, span_id in enumerate(visible_span_ids):
        for other_id in visible_span_ids[index + 1 :]:
            if visible_core_by_span[span_id].isdisjoint(visible_core_by_span[other_id]):
                continue
            raise CausalNativeTextError(
                "materially overlapping native text paints have ambiguous source ownership: "
                f"{raw_text_by_id[span_id]!r} / {raw_text_by_id[other_id]!r}"
            )

    words_by_line: dict[tuple[int, int], list[PDFWord]] = {}
    for word in extracted.words:
        words_by_line.setdefault((word.block_number, word.line_number), []).append(word)
    visible_word_overrides: dict[tuple[int, int, int], PDFWord | None] = {}
    for line_id, line_words in words_by_line.items():
        raw_chars = raw_chars_by_line.get(line_id, [])
        ordered_words = sorted(line_words, key=lambda word: word.word_number)
        raw_signature = "".join(character for character, _owner, _bbox in raw_chars)
        word_signature = "".join(
            "".join(character for character in word.raw_text if not character.isspace())
            for word in ordered_words
        )
        if raw_signature != word_signature:
            if not any(owner in excluded_span_ids for _character, owner, _bbox in raw_chars):
                continue
            characters_by_word: dict[
                tuple[int, int, int], list[tuple[str, tuple[int, int, int], BoundingBox]]
            ] = {
                (word.block_number, word.line_number, word.word_number): []
                for word in ordered_words
            }
            for character, owner, bbox in raw_chars:
                candidates = [
                    word
                    for word in ordered_words
                    if word.bbox_points.x0 - 0.5
                    <= (bbox.x0 + bbox.x1) / 2
                    <= word.bbox_points.x1 + 0.5
                    and word.bbox_points.y0 - 0.5
                    <= (bbox.y0 + bbox.y1) / 2
                    <= word.bbox_points.y1 + 0.5
                ]
                if not candidates:
                    if owner not in excluded_span_ids:
                        raise CausalNativeTextError(
                            "visible native text cannot be reconciled to extracted word geometry"
                        )
                    continue
                word = min(
                    candidates,
                    key=lambda candidate: abs(
                        (candidate.bbox_points.x0 + candidate.bbox_points.x1) / 2
                        - (bbox.x0 + bbox.x1) / 2
                    ),
                )
                characters_by_word[(word.block_number, word.line_number, word.word_number)].append(
                    (character, owner, bbox)
                )
            for word in ordered_words:
                word_id = (word.block_number, word.line_number, word.word_number)
                retained_characters = [
                    (character, bbox)
                    for character, owner, bbox in characters_by_word[word_id]
                    if owner not in excluded_span_ids
                ]
                if not retained_characters:
                    visible_word_overrides[word_id] = None
                    continue
                raw_text = "".join(character for character, _bbox in retained_characters)
                visible_word_overrides[word_id] = PDFWord(
                    raw_text=raw_text,
                    normalized_text=normalize_text(raw_text),
                    bbox_points=_union(bbox for _character, bbox in retained_characters),
                    block_number=word.block_number,
                    line_number=word.line_number,
                    word_number=word.word_number,
                )
            continue
        offset = 0
        for word in ordered_words:
            length = sum(not character.isspace() for character in word.raw_text)
            source_characters = raw_chars[offset : offset + length]
            retained_characters = [
                (character, bbox)
                for character, owner, bbox in source_characters
                if owner not in excluded_span_ids
            ]
            word_id = (word.block_number, word.line_number, word.word_number)
            if not retained_characters:
                visible_word_overrides[word_id] = None
            elif len(retained_characters) != len(source_characters):
                raw_text = "".join(character for character, _bbox in retained_characters)
                visible_word_overrides[word_id] = PDFWord(
                    raw_text=raw_text,
                    normalized_text=normalize_text(raw_text),
                    bbox_points=_union(bbox for _character, bbox in retained_characters),
                    block_number=word.block_number,
                    line_number=word.line_number,
                    word_number=word.word_number,
                )
            offset += length

    visible_words = []
    for word in extracted.words:
        word_id = (word.block_number, word.line_number, word.word_number)
        if word_id in visible_word_overrides:
            override = visible_word_overrides[word_id]
            if override is not None and override.normalized_text:
                visible_words.append(override)
        else:
            visible_words.append(word)
    native_page_bounds = page.rect * page.derotation_matrix
    visible_page = PDFTextPage(
        page=extracted.page,
        width_points=float(native_page_bounds.width),
        height_points=float(native_page_bounds.height),
        rotation=extracted.rotation,
        words=visible_words,
        text_quality=(extracted.text_quality if visible_words else "NO_TEXT_LAYER"),
        corruption_markers=extracted.corruption_markers,
    )
    if native_text_quality_config is not None:
        visible_page = apply_native_text_quality_v2(
            visible_page,
            native_text_quality_config,
        )
    return VisibleNativeTextPage(visible_page, tuple(excluded))
