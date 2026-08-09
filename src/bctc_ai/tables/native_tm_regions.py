from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import date
from math import ceil, isfinite
from pathlib import Path
from statistics import median
from typing import Any

import fitz
import yaml
from pymupdf import mupdf

from bctc_ai.axes.header_binding import bind_value_headers
from bctc_ai.core.contracts import BoundingBox, ObservationKind, RowType
from bctc_ai.core.text import (
    normalize_text,
    parse_financial_number,
    parse_unit,
    parse_vietnamese_dates,
    retrieval_key,
)
from bctc_ai.ocr.native_text_quality_v2 import apply_native_text_quality_v2
from bctc_ai.ocr.pdf_text import PDFTextPage, PDFWord, extract_pdf_text_page
from bctc_ai.rows.pdf_statement import (
    StatementRow,
    financial_table_span,
    reconstruct_statement_rows,
)
from bctc_ai.tables.geometry import (
    ColumnAxis,
    ColumnRole,
    GeometryConfig,
    PageGeometry,
    TextRun,
    build_text_runs,
)


class NativeTMRegionError(ValueError):
    """A native-text TM table region cannot be established without guessing."""


_MATERIAL_PAINTED_OCCLUSION_RATIO = 0.09
_FULL_HEIGHT_PAINTED_OCCLUSION_RATIO = 0.90


@dataclass(frozen=True)
class NativeTMRegionPolicy:
    version: int
    policy: str
    claim_boundary: str
    exact_unit_header_keys: tuple[str, ...]
    maximum_group_vertical_gap_height_factor: float
    data_start_gap_height_factor: float
    next_header_gap_height_factor: float
    header_lookback_height_factor: float
    minimum_aligned_observations_per_single_header: int
    axis_alignment_tolerance_multiplier: float
    require_every_distinct_unit_axis_observed: bool
    label_boundary_margin_ratio: float
    maximum_adjacent_axis_gap_ratio: float
    minimum_stable_numeric_cluster_samples: int
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


@dataclass(frozen=True)
class UnitGroupDiagnostic:
    page: int
    unit_run_ids: tuple[str, ...]
    unit_texts: tuple[str, ...]
    bbox: BoundingBox
    accepted: bool
    aligned_observation_counts: tuple[int, ...]
    reason: str


@dataclass(frozen=True)
class NativeTMGridSlot:
    row_id: str
    axis_id: str
    axis_ordinal: int
    source_status: str
    raw_text: str | None
    value_text: str | None
    source_bbox: BoundingBox | None
    grid_slot_bbox: BoundingBox
    source_run_id: str | None
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class NativeTMScalarDisclosure:
    scalar_id: str
    source_row_id: str
    page: int
    label: str
    label_boxes: tuple[BoundingBox, ...]
    period_end: date
    source_status: str
    raw_text: str
    value_text: str | None
    value_bbox: BoundingBox
    value_run_id: str
    unit: str
    unit_multiplier: int
    unit_raw_text: str
    unit_bbox: BoundingBox
    unit_run_id: str
    ownership_status: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class NativeTMAxisBinding:
    axis_id: str
    raw_header: str
    header_bbox: BoundingBox | None
    period_group_id: str | None
    period_start: date | None
    period_end: date | None
    period_type: str | None
    period_scope: str
    duration_months: int | None
    current_or_comparative: str | None
    measure_role: str
    unit: str | None
    unit_multiplier: int | None
    unit_denominator: str | None
    unit_scope: str
    unit_bbox: BoundingBox | None
    restated: bool
    binding_status: str
    confidence: float
    source_run_ids: tuple[str, ...]
    conflicts: tuple[str, ...]
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class NativeTMInterTableContext:
    page: int
    preceding_table_id: str
    following_table_id: str
    source_row_ids: tuple[str, ...]
    runs: tuple[TextRun, ...]
    bbox: BoundingBox
    ownership_status: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class NativeTMTableRegion:
    table_id: str
    page: int
    table_order: int
    region_bbox: BoundingBox
    header_runs: tuple[TextRun, ...]
    geometry: PageGeometry
    header_bindings: tuple[NativeTMAxisBinding, ...]
    rows: tuple[StatementRow, ...]
    grid_slots: tuple[NativeTMGridSlot, ...]
    scalar_disclosures: tuple[NativeTMScalarDisclosure, ...]
    outside_financial_span_rows: tuple[StatementRow, ...]
    detached_margin_runs: tuple[TextRun, ...]
    unassigned_runs: tuple[TextRun, ...]
    acceptance_signals: tuple[str, ...]

    @property
    def value_bearing_row_count(self) -> int:
        return sum(bool(row.cells) for row in self.rows) + len(self.scalar_disclosures)

    @property
    def visible_cell_count(self) -> int:
        return sum(len(row.cells) for row in self.rows) + len(self.scalar_disclosures)

    @property
    def grid_slot_count(self) -> int:
        return len(self.grid_slots)

    @property
    def unresolved_empty_slot_count(self) -> int:
        return sum(slot.source_status == "UNRESOLVED_EMPTY_SLOT" for slot in self.grid_slots)


@dataclass(frozen=True)
class NativeTMPageRegions:
    page: int
    regions: tuple[NativeTMTableRegion, ...]
    inter_table_contexts: tuple[NativeTMInterTableContext, ...]
    unit_group_diagnostics: tuple[UnitGroupDiagnostic, ...]
    excluded_spans: tuple[ExcludedNativeTextSpan, ...]
    unassigned_page_runs: tuple[TextRun, ...]


@dataclass(frozen=True)
class _LocalNumericCluster:
    right_edge: float
    left_edge: float
    runs: tuple[TextRun, ...]


_OBSERVED_FINANCIAL = {
    ObservationKind.VALUE,
    ObservationKind.ZERO,
    ObservationKind.DASH,
}
_FORBIDDEN_POLICY_KEY_FRAGMENTS = (
    "bank",
    "filename",
    "file_hash",
    "pdf_hash",
    "page_number",
    "note_number",
    "reportnorm",
    "schema_label",
    "expected_row",
    "expected_cell",
)
_EXACT_UNIT_HEADER_KEYS = ("trieu dong", "nghin dong", "ty dong", "vnd")


def _assert_source_driven_policy(value: Any, *, path: str = "policy") -> None:
    if isinstance(value, dict):
        for raw_key, child in value.items():
            key = str(raw_key).lower()
            is_explicit_prohibition = key.endswith("allowed") and child is False
            if not is_explicit_prohibition and any(
                fragment in key for fragment in _FORBIDDEN_POLICY_KEY_FRAGMENTS
            ):
                raise NativeTMRegionError(f"{path}.{raw_key} is document/schema specific")
            _assert_source_driven_policy(child, path=f"{path}.{raw_key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_source_driven_policy(child, path=f"{path}[{index}]")


def _positive_number(value: Any, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(float(value))
        or value <= 0
    ):
        raise NativeTMRegionError(f"{name} must be a positive number")
    return float(value)


def load_native_tm_region_policy(path: Path) -> NativeTMRegionPolicy:
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    _assert_source_driven_policy(raw)
    expected_sections = {
        "version",
        "policy",
        "claim_boundary",
        "unit_headers",
        "acceptance",
        "geometry",
        "visibility",
        "safety",
    }
    if not isinstance(raw, dict) or set(raw) != expected_sections:
        raise NativeTMRegionError("native TM region policy fields are invalid")
    unit = raw.get("unit_headers")
    acceptance = raw.get("acceptance")
    geometry = raw.get("geometry")
    visibility = raw.get("visibility")
    safety = raw.get("safety")
    if (
        raw.get("version") != 1
        or raw.get("policy") != "NATIVE_TM_LOCAL_TABLE_REGIONS_V1"
        or raw.get("claim_boundary")
        != "SOURCE_VISIBLE_QUANTITATIVE_TABLE_GEOMETRY_AND_HEADER_SEMANTICS"
        or not all(
            isinstance(section, dict)
            for section in (unit, acceptance, geometry, visibility, safety)
        )
    ):
        raise NativeTMRegionError(f"invalid native TM region policy identity: {path}")
    expected_section_fields = {
        "unit_headers": {
            "exact_retrieval_keys",
            "maximum_group_vertical_gap_height_factor",
            "data_start_gap_height_factor",
            "next_header_gap_height_factor",
            "header_lookback_height_factor",
        },
        "acceptance": {
            "minimum_aligned_observations_per_single_header",
            "axis_alignment_tolerance_multiplier",
            "require_every_distinct_unit_axis_observed",
            "require_source_visible_unit_header",
            "permit_value_magnitude_as_period_or_identity_evidence",
        },
        "geometry": {
            "label_boundary_margin_ratio",
            "maximum_adjacent_axis_gap_ratio",
            "minimum_stable_numeric_cluster_samples",
            "preserve_rows_outside_financial_span",
            "preserve_unassigned_runs",
        },
        "visibility": {
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
        },
        "safety": {
            "historical_values_allowed",
            "role_a_outputs_allowed",
            "schema_inputs_allowed",
            "template_inputs_allowed",
            "bank_or_page_specific_rules_allowed",
            "expected_row_or_cell_counts_allowed",
        },
    }
    for section_name, expected_fields in expected_section_fields.items():
        if set(raw[section_name]) != expected_fields:
            raise NativeTMRegionError(f"native TM region {section_name} fields are invalid")
    exact_keys = unit.get("exact_retrieval_keys")
    if (
        not isinstance(exact_keys, list)
        or not exact_keys
        or any(not isinstance(item, str) or retrieval_key(item) != item for item in exact_keys)
        or tuple(exact_keys) != _EXACT_UNIT_HEADER_KEYS
    ):
        raise NativeTMRegionError("native TM exact unit-header keys are invalid")
    required_acceptance = {
        "require_source_visible_unit_header": True,
        "require_every_distinct_unit_axis_observed": True,
        "permit_value_magnitude_as_period_or_identity_evidence": False,
    }
    required_safety = {
        "historical_values_allowed": False,
        "role_a_outputs_allowed": False,
        "schema_inputs_allowed": False,
        "template_inputs_allowed": False,
        "bank_or_page_specific_rules_allowed": False,
        "expected_row_or_cell_counts_allowed": False,
    }
    required_geometry = {
        "preserve_rows_outside_financial_span": True,
        "preserve_unassigned_runs": True,
    }
    required_visibility = {
        "near_white_channel_minimum": 250,
        "raster_scale": 2.0,
        "minimum_visible_contrast": 12,
        "exclude_fully_transparent_text_paints": True,
        "require_causal_visibility_for_nonopaque_text": True,
        "minimum_causal_contribution_ratio": 0.25,
        "minimum_glyph_core_alpha": 128,
        "relative_glyph_core_alpha": 0.75,
        "minimum_glyph_core_survival_ratio": 0.75,
        "blank_slot_inset_ratio": 0.12,
    }
    if any(visibility.get(key) != value for key, value in required_visibility.items()):
        raise NativeTMRegionError("native TM causal visibility gate is invalid")
    if any(acceptance.get(key) is not value for key, value in required_acceptance.items()):
        raise NativeTMRegionError("native TM region acceptance weakens a source-only gate")
    if any(geometry.get(key) is not value for key, value in required_geometry.items()):
        raise NativeTMRegionError("native TM region geometry weakens evidence preservation")
    if any(safety.get(key) is not value for key, value in required_safety.items()):
        raise NativeTMRegionError("native TM region safety gate is invalid")
    minimum_single = acceptance.get("minimum_aligned_observations_per_single_header")
    near_white = visibility.get("near_white_channel_minimum")
    minimum_contrast = visibility.get("minimum_visible_contrast")
    minimum_causal_contribution = float(visibility.get("minimum_causal_contribution_ratio", -1))
    minimum_glyph_core_alpha = visibility.get("minimum_glyph_core_alpha")
    relative_glyph_core_alpha = float(visibility.get("relative_glyph_core_alpha", -1))
    minimum_glyph_core_survival = float(visibility.get("minimum_glyph_core_survival_ratio", -1))
    blank_slot_inset = float(visibility.get("blank_slot_inset_ratio", -1))
    if (
        isinstance(minimum_single, bool)
        or not isinstance(minimum_single, int)
        or minimum_single < 1
    ):
        raise NativeTMRegionError("single-header observation minimum must be positive")
    if (
        isinstance(near_white, bool)
        or not isinstance(near_white, int)
        or not 0 <= near_white <= 255
        or isinstance(minimum_contrast, bool)
        or not isinstance(minimum_contrast, int)
        or not 0 <= minimum_contrast <= 255
        or not isfinite(minimum_causal_contribution)
        or not 0 < minimum_causal_contribution <= 1
        or isinstance(minimum_glyph_core_alpha, bool)
        or not isinstance(minimum_glyph_core_alpha, int)
        or not 1 <= minimum_glyph_core_alpha <= 255
        or not isfinite(relative_glyph_core_alpha)
        or not 0 < relative_glyph_core_alpha <= 1
        or not isfinite(minimum_glyph_core_survival)
        or not 0 < minimum_glyph_core_survival <= 1
        or not isfinite(blank_slot_inset)
        or not 0 <= blank_slot_inset < 0.45
    ):
        raise NativeTMRegionError("native TM visibility thresholds are invalid")
    margin = float(geometry.get("label_boundary_margin_ratio", -1))
    maximum_axis_gap = float(geometry.get("maximum_adjacent_axis_gap_ratio", -1))
    minimum_cluster_samples = geometry.get("minimum_stable_numeric_cluster_samples")
    if (
        not isfinite(margin)
        or not isfinite(maximum_axis_gap)
        or not 0 < margin < 0.25
        or not 0 < maximum_axis_gap < 0.5
    ):
        raise NativeTMRegionError("native TM label-boundary margin is invalid")
    if (
        isinstance(minimum_cluster_samples, bool)
        or not isinstance(minimum_cluster_samples, int)
        or minimum_cluster_samples < 2
    ):
        raise NativeTMRegionError("stable numeric-cluster minimum is invalid")
    return NativeTMRegionPolicy(
        version=1,
        policy=str(raw["policy"]),
        claim_boundary=str(raw["claim_boundary"]),
        exact_unit_header_keys=tuple(exact_keys),
        maximum_group_vertical_gap_height_factor=_positive_number(
            unit.get("maximum_group_vertical_gap_height_factor"),
            "unit group vertical gap",
        ),
        data_start_gap_height_factor=_positive_number(
            unit.get("data_start_gap_height_factor"), "data start gap"
        ),
        next_header_gap_height_factor=_positive_number(
            unit.get("next_header_gap_height_factor"), "next header gap"
        ),
        header_lookback_height_factor=_positive_number(
            unit.get("header_lookback_height_factor"), "header lookback"
        ),
        minimum_aligned_observations_per_single_header=minimum_single,
        axis_alignment_tolerance_multiplier=_positive_number(
            acceptance.get("axis_alignment_tolerance_multiplier"),
            "axis alignment tolerance multiplier",
        ),
        require_every_distinct_unit_axis_observed=(
            acceptance.get("require_every_distinct_unit_axis_observed") is True
        ),
        label_boundary_margin_ratio=margin,
        maximum_adjacent_axis_gap_ratio=maximum_axis_gap,
        minimum_stable_numeric_cluster_samples=minimum_cluster_samples,
        near_white_channel_minimum=near_white,
        raster_scale=_positive_number(visibility.get("raster_scale"), "raster scale"),
        minimum_visible_contrast=minimum_contrast,
        minimum_causal_contribution_ratio=minimum_causal_contribution,
        minimum_glyph_core_alpha=minimum_glyph_core_alpha,
        relative_glyph_core_alpha=relative_glyph_core_alpha,
        minimum_glyph_core_survival_ratio=minimum_glyph_core_survival,
        blank_slot_inset_ratio=blank_slot_inset,
        exclude_fully_transparent_text_paints=(
            visibility.get("exclude_fully_transparent_text_paints") is True
        ),
        require_causal_visibility_for_nonopaque_text=(
            visibility.get("require_causal_visibility_for_nonopaque_text") is True
        ),
        source_path=path.resolve(),
    )


def _union(boxes: Iterable[BoundingBox]) -> BoundingBox:
    materialized = tuple(boxes)
    if not materialized:
        raise NativeTMRegionError("cannot union an empty set of source boxes")
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
        raise NativeTMRegionError("native grayscale raster identity is invalid")
    return rendered


def _render_unrotated_rgb(page: fitz.Page, *, scale: float, textless: bool) -> _RGBRaster:
    rendered = _render_unrotated_raster(
        page,
        scale=scale,
        textless=textless,
        rgb=True,
    )
    if not isinstance(rendered, _RGBRaster):
        raise NativeTMRegionError("native RGB raster identity is invalid")
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
        raise NativeTMRegionError("native and textless raster identities drifted")
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
        raise NativeTMRegionError("native and textless RGB raster identities drifted")
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
            raise NativeTMRegionError("native glyph device drifted from the render-order log")

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
            raise NativeTMRegionError("native glyph render entry lacks a valid bbox")
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
            raise NativeTMRegionError("native glyph bounds drifted from the render-order log")
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
            raise NativeTMRegionError("native glyph paint color conversion is malformed")
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
                raise NativeTMRegionError("native glyph alpha raster is malformed")
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
        raise NativeTMRegionError("native text used as a clipping path is unresolved")
    if device.sequence != len(bbox_log):
        raise NativeTMRegionError("native glyph device did not consume the render-order log")
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
            raise NativeTMRegionError("native glyph mask lacks text-paint authority")
        if not isfinite(mask.paint_alpha) or not 0 <= mask.paint_alpha <= 1:
            raise NativeTMRegionError("native glyph paint alpha is invalid")
        if abs(mask.paint_alpha - paint.opacity) > 1e-6:
            raise NativeTMRegionError("native glyph alpha drifted across render inventories")
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
        raise NativeTMRegionError("native text has mixed render-event colors and is unresolved")
    return merged, (next(iter(active_colors)) if active_colors else None)


def _causal_glyph_core_survival(
    *,
    span: dict[str, Any],
    expected_color: int,
    expected_alpha: dict[tuple[int, int], int],
    original: _RGBRaster,
    textless: _RGBRaster,
    policy: NativeTMRegionPolicy,
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
            raise NativeTMRegionError("native text character lacks a valid source bbox")
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
            raise NativeTMRegionError("native character owns no expected glyph pixels")
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
                raise NativeTMRegionError("native glyph core lies outside the causal raster")
            offset = raster_y * original.stride + raster_x * 3
            observed = original.samples[offset : offset + 3]
            background = textless.samples[offset : offset + 3]
            if len(observed) != 3 or len(background) != 3:
                raise NativeTMRegionError("native RGB causal pixel is malformed")
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
        raise NativeTMRegionError("native text span has no non-space character evidence")
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
                raise NativeTMRegionError("native RGB bbox sample is malformed")
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
            raise NativeTMRegionError("native render text entry lacks a valid bbox")
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
            raise NativeTMRegionError("native text span lacks a valid source bbox")
        span_boxes.append(BoundingBox(*(float(value) for value in raw_bbox)))

    render_events = _positive_area_render_text_events(bbox_log)
    if len(render_events) < len(span_boxes):
        raise NativeTMRegionError("native render log has fewer text events than source spans")

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
            raise NativeTMRegionError(
                "native text spans cannot be partitioned over render-order events"
            )
        states = next_states

    completed = states.get(len(render_events))
    if completed is None:
        raise NativeTMRegionError("native render-order text events are not fully owned")
    path_count, boundary_path = completed
    if path_count != 1:
        raise NativeTMRegionError("native render-order text ownership is ambiguous")

    start = 0
    render_identities: dict[tuple[int, int, int], _NativeTextRenderIdentity] = {}
    for index, (_span, span_id, _raw_text) in enumerate(raw_spans):
        end = boundary_path[index]
        if end <= start:
            raise NativeTMRegionError("native text span owns no render-order event")
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
            raise NativeTMRegionError("native drawing lacks a valid render-context level")
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
            raise NativeTMRegionError("native drawing lacks a unique render-order identity")
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
        raise NativeTMRegionError("native image inventory does not match render-order log")
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
            raise NativeTMRegionError("native image lacks a valid render bbox")
        rendered_bbox = BoundingBox(*(float(value) for value in raw_bbox))
        audited_bbox = BoundingBox(*(float(value) for value in info_bbox))
        if (
            min(
                _bbox_coverage(rendered_bbox, audited_bbox),
                _bbox_coverage(audited_bbox, rendered_bbox),
            )
            < 0.99
        ):
            raise NativeTMRegionError("native image identity drifted across render inventories")
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
            raise NativeTMRegionError("native covering render object lacks a valid bbox")
        covering_bbox = BoundingBox(*(float(value) for value in raw_bbox))
        if not _bbox_intersects(covering_bbox, bbox):
            continue
        if object_type == "fill-shade":
            raise NativeTMRegionError("native text visibility beneath a later shade is unresolved")
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
            raise NativeTMRegionError("native text visibility beneath a later image is unresolved")
        drawing = drawings_by_sequence.get(sequence)
        if drawing is None:
            raise NativeTMRegionError("native fill-path lacks render-order drawing evidence")
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
            raise NativeTMRegionError("native render object lacks a valid core-intersection bbox")
        object_bbox = BoundingBox(*(float(value) for value in raw_bbox))
        if not _bbox_intersects(object_bbox, pixel_bbox):
            continue
        if object_type in {"fill-text", "stroke-text", "fill-image", "fill-imgmask", "fill-shade"}:
            return True
        drawing = drawings_by_sequence.get(sequence)
        if drawing is None:
            raise NativeTMRegionError("native path lacks render-order drawing evidence")
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
    policy: NativeTMRegionPolicy,
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
            raise NativeTMRegionError("native text block lacks a source identity")
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
                        raise NativeTMRegionError("native text character lacks a valid source bbox")
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
            raise NativeTMRegionError("native text span lacks a valid source bbox")
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
                raise NativeTMRegionError("native character lacks a valid source bbox")
            character_bbox = BoundingBox(*(float(value) for value in character_bbox_raw))
            painted_character_bbox = _bbox_intersection(painted_bbox, character_bbox)
            if painted_character_bbox is not None:
                protected_character_bboxes.append(painted_character_bbox)
        covering_object: tuple[str, int, str] | None = None
        reason: str | None = None
        if not policy.require_causal_visibility_for_nonopaque_text:
            raise NativeTMRegionError("native nonopaque-text causal gate is disabled")
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
                raise NativeTMRegionError(
                    "native text is materially or character-wise occluded and unresolved"
                )
            if covering_object is not None:
                reason = "later opaque render object fully covers painted native text"
            elif original_raster is None or textless_raster is None:
                raise NativeTMRegionError("native causal text raster is unavailable")
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
                        raise NativeTMRegionError(
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
                        raise NativeTMRegionError(
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
                        raise NativeTMRegionError(
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
                            raise NativeTMRegionError(
                                "native glyph paint is causally occluded and unresolved"
                            )
                        raise NativeTMRegionError("native glyph color attribution is unresolved")
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
                                raise NativeTMRegionError(
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
                                raise NativeTMRegionError(
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
            raise NativeTMRegionError(
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
                        raise NativeTMRegionError(
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


def resolve_region_blank_slots(
    page: fitz.Page,
    region: NativeTMTableRegion,
    policy: NativeTMRegionPolicy,
) -> NativeTMTableRegion:
    """Promote source-empty slots to BLANK only with rendered whitespace evidence."""

    if page.number + 1 != region.page:
        raise NativeTMRegionError("blank-slot pixel page does not match the table region")
    pixmap = _render_unrotated_rgb(
        page,
        scale=policy.raster_scale,
        textless=False,
    )
    resolved: list[NativeTMGridSlot] = []
    for slot in region.grid_slots:
        if slot.source_status != "UNRESOLVED_EMPTY_SLOT":
            resolved.append(slot)
            continue
        width = slot.grid_slot_bbox.x1 - slot.grid_slot_bbox.x0
        height = slot.grid_slot_bbox.y1 - slot.grid_slot_bbox.y0
        inset_x = width * policy.blank_slot_inset_ratio
        inset_y = height * policy.blank_slot_inset_ratio
        interior = BoundingBox(
            slot.grid_slot_bbox.x0 + inset_x,
            slot.grid_slot_bbox.y0 + inset_y,
            slot.grid_slot_bbox.x1 - inset_x,
            slot.grid_slot_bbox.y1 - inset_y,
        )
        pixels = _bbox_rgb_pixels(
            pixmap,
            interior,
            scale=policy.raster_scale,
        )
        proven_white = bool(pixels) and all(
            min(pixel) >= policy.near_white_channel_minimum for pixel in pixels
        )
        resolved.append(
            replace(
                slot,
                source_status=("BLANK" if proven_white else "UNRESOLVED_EMPTY_SLOT"),
                evidence=(
                    *slot.evidence,
                    (
                        "rendered grid-slot interior is source-white; BLANK is proven"
                        if proven_white
                        else "rendered grid-slot interior is not proven source-white"
                    ),
                ),
            )
        )
    return replace(region, grid_slots=tuple(resolved))


def _is_observed_financial(run: TextRun) -> bool:
    return parse_financial_number(run.normalized_text).observation in _OBSERVED_FINANCIAL


def _median_run_height(runs: list[TextRun]) -> float:
    heights = [run.height for run in runs if run.height > 0]
    return float(median(heights)) if heights else 8.0


def _group_unit_runs(
    runs: list[TextRun],
    *,
    median_height: float,
    policy: NativeTMRegionPolicy,
) -> list[list[TextRun]]:
    unit_runs = [
        run for run in runs if retrieval_key(run.normalized_text) in policy.exact_unit_header_keys
    ]
    groups: list[list[TextRun]] = []
    maximum_gap = median_height * policy.maximum_group_vertical_gap_height_factor
    for run in sorted(unit_runs, key=lambda item: (item.y_center, item.bbox.x0, item.run_id)):
        if not groups or run.bbox.y0 > max(item.bbox.y1 for item in groups[-1]) + maximum_gap:
            groups.append([run])
        else:
            groups[-1].append(run)
    return groups


def _distinct_unit_axes(group: list[TextRun], tolerance: float) -> list[list[TextRun]]:
    axes: list[list[TextRun]] = []
    for run in sorted(group, key=lambda item: item.bbox.x1):
        target = next(
            (
                members
                for members in axes
                if abs(run.bbox.x1 - median(item.bbox.x1 for item in members)) <= tolerance
            ),
            None,
        )
        if target is None:
            axes.append([run])
        else:
            target.append(run)
    return axes


def _candidate_data_bounds(
    page: PDFTextPage,
    group: list[TextRun],
    following_group: list[TextRun] | None,
    *,
    median_height: float,
    policy: NativeTMRegionPolicy,
    geometry_config: GeometryConfig,
) -> tuple[float, float]:
    start = max(run.bbox.y1 for run in group) + (
        median_height * policy.data_start_gap_height_factor
    )
    end = (
        min(run.bbox.y0 for run in following_group)
        - median_height * policy.next_header_gap_height_factor
        if following_group
        else page.height_points * geometry_config.footer_y_ratio
    )
    return start, end


def _header_start(
    page: PDFTextPage,
    runs: list[TextRun],
    group: list[TextRun],
    *,
    median_height: float,
    policy: NativeTMRegionPolicy,
) -> float:
    unit_y = min(run.bbox.y0 for run in group)
    minimum_x = min(run.bbox.x0 for run in group) - page.width_points * 0.04
    candidates = [
        run
        for run in runs
        if unit_y - median_height * policy.header_lookback_height_factor <= run.bbox.y0 < unit_y
        and run.bbox.x1 >= minimum_x
        and not _is_observed_financial(run)
    ]
    return min(
        (run.bbox.y0 for run in candidates),
        default=unit_y - median_height * 3,
    )


def _aligned_counts(
    group: list[TextRun],
    numeric_runs: list[TextRun],
    *,
    tolerance: float,
) -> tuple[int, ...]:
    return tuple(
        sum(abs(candidate.bbox.x1 - unit.bbox.x1) <= tolerance for candidate in numeric_runs)
        for unit in group
    )


def _diagnose_unit_groups(
    page: PDFTextPage,
    runs: list[TextRun],
    groups: list[list[TextRun]],
    *,
    median_height: float,
    policy: NativeTMRegionPolicy,
    geometry_config: GeometryConfig,
    edge_tolerance: float,
) -> tuple[list[list[TextRun]], list[UnitGroupDiagnostic]]:
    accepted: list[list[TextRun]] = []
    diagnostics: list[UnitGroupDiagnostic] = []
    alignment_tolerance = edge_tolerance * policy.axis_alignment_tolerance_multiplier
    for index, group in enumerate(groups):
        following = groups[index + 1] if index + 1 < len(groups) else None
        start, end = _candidate_data_bounds(
            page,
            group,
            following,
            median_height=median_height,
            policy=policy,
            geometry_config=geometry_config,
        )
        numeric_runs = [
            run for run in runs if start <= run.y_center < end and _is_observed_financial(run)
        ]
        counts = _aligned_counts(group, numeric_runs, tolerance=alignment_tolerance)
        distinct_axes = _distinct_unit_axes(group, edge_tolerance)
        distinct_observed = sum(
            any(
                abs(candidate.bbox.x1 - unit.bbox.x1) <= alignment_tolerance
                for candidate in numeric_runs
                for unit in axis_members
            )
            for axis_members in distinct_axes
        )
        if end <= start:
            reason = "unit-like source text has no positive data band"
            is_accepted = False
        elif len(distinct_axes) == 1:
            is_accepted = sum(counts) >= policy.minimum_aligned_observations_per_single_header
            reason = (
                "one source-visible unit axis has repeated aligned observations"
                if is_accepted
                else "single unit-like run lacks repeated aligned observations"
            )
        else:
            required = len(distinct_axes) if policy.require_every_distinct_unit_axis_observed else 1
            is_accepted = distinct_observed >= required
            reason = (
                "every distinct source-visible unit axis has aligned observations"
                if is_accepted
                else "one or more visible unit axes lack aligned observations"
            )
        if is_accepted:
            accepted.append(group)
        diagnostics.append(
            UnitGroupDiagnostic(
                page=page.page,
                unit_run_ids=tuple(run.run_id for run in group),
                unit_texts=tuple(run.raw_text for run in group),
                bbox=_union(run.bbox for run in group),
                accepted=is_accepted,
                aligned_observation_counts=counts,
                reason=reason,
            )
        )
    return accepted, diagnostics


def _axes_for_region(
    group: list[TextRun],
    numeric_runs: list[TextRun],
    *,
    page_width: float,
    edge_tolerance: float,
    policy: NativeTMRegionPolicy,
) -> tuple[ColumnAxis, ...]:
    clusters: list[list[TextRun]] = []
    for run in sorted(numeric_runs, key=lambda item: item.bbox.x1):
        target = next(
            (
                members
                for members in clusters
                if abs(run.bbox.x1 - median(item.bbox.x1 for item in members)) <= edge_tolerance
            ),
            None,
        )
        if target is None:
            clusters.append([run])
        else:
            target.append(run)
    local_clusters = sorted(
        (
            _LocalNumericCluster(
                right_edge=float(median(run.bbox.x1 for run in members)),
                left_edge=float(median(run.bbox.x0 for run in members)),
                runs=tuple(members),
            )
            for members in clusters
        ),
        key=lambda item: item.right_edge,
    )
    alignment_tolerance = edge_tolerance * policy.axis_alignment_tolerance_multiplier
    anchor_indices: list[int] = []
    for unit_members in _distinct_unit_axes(group, edge_tolerance):
        unit_right = float(median(run.bbox.x1 for run in unit_members))
        closest = min(
            enumerate(local_clusters),
            key=lambda pair: abs(pair[1].right_edge - unit_right),
            default=None,
        )
        if closest is None or abs(closest[1].right_edge - unit_right) > alignment_tolerance:
            raise NativeTMRegionError("accepted unit axis has no aligned source observation")
        anchor_indices.append(closest[0])
    if not anchor_indices:
        raise NativeTMRegionError("accepted native TM region has no unit-anchored axis")

    stable_indices = {
        index
        for index, cluster in enumerate(local_clusters)
        if len(cluster.runs) >= policy.minimum_stable_numeric_cluster_samples
    }
    stable_indices.update(anchor_indices)
    selected = set(range(min(anchor_indices), max(anchor_indices) + 1)) & stable_indices
    selected.update(anchor_indices)
    maximum_gap = policy.maximum_adjacent_axis_gap_ratio * page_width
    left = min(selected)
    while left > 0:
        candidate = left - 1
        if (
            candidate not in stable_indices
            or local_clusters[left].right_edge - local_clusters[candidate].right_edge > maximum_gap
        ):
            break
        selected.add(candidate)
        left = candidate
    right = max(selected)
    while right + 1 < len(local_clusters):
        candidate = right + 1
        if (
            candidate not in stable_indices
            or local_clusters[candidate].right_edge - local_clusters[right].right_edge > maximum_gap
        ):
            break
        selected.add(candidate)
        right = candidate

    unit_anchor_set = set(anchor_indices)
    axes = [
        ColumnAxis(
            axis_id="",
            role=ColumnRole.VALUE,
            right_edge=local_clusters[index].right_edge,
            left_edge=local_clusters[index].left_edge,
            sample_count=len(local_clusters[index].runs),
            source=(
                "source-visible-exact-unit-header+local-numeric-cluster"
                if index in unit_anchor_set
                else "stable-local-numeric-cluster-adjacent-to-unit-anchored-axes"
            ),
        )
        for index in sorted(selected)
    ]
    return tuple(
        ColumnAxis(
            axis_id=f"value-{index}",
            role=axis.role,
            right_edge=axis.right_edge,
            left_edge=axis.left_edge,
            sample_count=axis.sample_count,
            source=axis.source,
        )
        for index, axis in enumerate(axes, start=1)
    )


def _row_box_keys(rows: Iterable[StatementRow]) -> set[tuple[float, float, float, float]]:
    boxes: set[tuple[float, float, float, float]] = set()
    for row in rows:
        for box in row.label_boxes:
            boxes.add((box.x0, box.y0, box.x1, box.y1))
        if row.note_bbox:
            boxes.add((row.note_bbox.x0, row.note_bbox.y0, row.note_bbox.x1, row.note_bbox.y1))
        for cell in row.cells:
            boxes.add((cell.bbox.x0, cell.bbox.y0, cell.bbox.x1, cell.bbox.y1))
    return boxes


def _row_label_box(row: StatementRow) -> BoundingBox | None:
    return _union(row.label_boxes) if row.label_boxes else None


def _first_alpha_is_lower(text: str) -> bool:
    return next((character.islower() for character in text if character.isalpha()), False)


def _should_merge_multiline_rows(
    left: StatementRow,
    right: StatementRow,
    *,
    geometry: PageGeometry,
    geometry_config: GeometryConfig,
    median_height: float,
) -> bool:
    """Recognize one source label wrapped across adjacent row bands.

    The generic row assembler already handles many label fragments preceding a
    numeric band.  This bounded second pass handles the two remaining source
    layouts: a continuation printed after the numeric band, and a long first
    line followed by a short value-bearing final line.  It never joins two
    value-bearing rows and never uses accounting labels or schema knowledge.
    """

    if (
        left.page != right.page
        or not left.label
        or not right.label
        or (left.cells and right.cells)
        or (
            left.note_reference is not None
            and right.note_reference is not None
            and left.note_reference != right.note_reference
        )
    ):
        return False
    left_box = _row_label_box(left)
    right_box = _row_label_box(right)
    if left_box is None or right_box is None:
        return False
    vertical_gap = right_box.y0 - left_box.y1
    if not (
        -median_height * geometry_config.band_y_tolerance_height_factor
        <= vertical_gap
        <= median_height * geometry_config.maximum_wrap_gap_height_factor
    ):
        return False
    indentation_tolerance = geometry.width_points * geometry_config.indentation_tolerance_ratio
    if abs(left_box.x0 - right_box.x0) > indentation_tolerance:
        return False

    if left.cells and not right.cells:
        return (
            _first_alpha_is_lower(right.label)
            and not right.label.lstrip().startswith(("(", "[", "-", "•", "+", "*"))
            and (right_box.x1 - right_box.x0) <= (left_box.x1 - left_box.x0)
        )

    if right.label.lstrip().startswith(("-", "•", "+")):
        return False

    available_width = max(1.0, geometry.label_right_boundary - left_box.x0)
    occupancy = (left_box.x1 - left_box.x0) / available_width
    short_continuation = (right_box.x1 - right_box.x0) <= ((left_box.x1 - left_box.x0) * 0.65)
    continuation_signal = (
        _first_alpha_is_lower(right.label)
        or left.label.endswith((",", "/", "-", "("))
        or (
            occupancy >= geometry_config.preceding_line_occupancy_threshold * 0.80
            and short_continuation
        )
    )
    return continuation_signal


def _merge_statement_rows(
    rows: Iterable[StatementRow],
    *,
    geometry: PageGeometry,
    geometry_config: GeometryConfig,
    table_id: str,
) -> tuple[StatementRow, ...]:
    ordered = sorted(rows, key=lambda row: (row.y0, row.indentation, row.row_id))
    heights = [row.y1 - row.y0 for row in ordered if row.y1 > row.y0]
    median_height = float(median(heights)) if heights else 8.0
    merged: list[StatementRow] = []
    for row in ordered:
        if merged and _should_merge_multiline_rows(
            merged[-1],
            row,
            geometry=geometry,
            geometry_config=geometry_config,
            median_height=median_height,
        ):
            left = merged.pop()
            cell_row = left if left.cells else row if row.cells else None
            inherited_warnings = [
                warning
                for warning in (*left.warnings, *row.warnings)
                if not (
                    cell_row is not None
                    and warning == "label-only row retained for ordered context"
                )
            ]
            merged.append(
                StatementRow(
                    row_id="",
                    page=left.page,
                    row_type=(cell_row.row_type if cell_row else RowType.SECTION_HEADER),
                    label=normalize_text(f"{left.label} {row.label}"),
                    label_boxes=(*left.label_boxes, *row.label_boxes),
                    note_reference=left.note_reference or row.note_reference,
                    note_bbox=left.note_bbox or row.note_bbox,
                    cells=cell_row.cells if cell_row else (),
                    y0=min(left.y0, row.y0),
                    y1=max(left.y1, row.y1),
                    indentation=min(left.indentation, row.indentation),
                    warnings=tuple(
                        dict.fromkeys(
                            (
                                *inherited_warnings,
                                "source-adjacent multiline label fragments merged by geometry",
                            )
                        )
                    ),
                )
            )
            continue
        merged.append(row)
    normalized_rows = []
    for index, row in enumerate(merged, 1):
        accented_label = normalize_text(row.label).casefold()
        explicit_total = accented_label in {
            "cộng",
            "tổng",
            "tổng cộng",
            "total",
        } or accented_label.startswith(("cộng ", "tổng ", "total "))
        normalized_rows.append(
            replace(
                row,
                row_id=f"{table_id}:row-{index:04d}",
                row_type=(
                    RowType.SECTION_HEADER
                    if not row.cells
                    else RowType.TOTAL_ROW
                    if explicit_total
                    else RowType.DATA_ROW
                ),
            )
        )
    return tuple(normalized_rows)


def _detached_margin_runs(
    runs: Iterable[TextRun],
    *,
    data_start: float,
    data_end: float,
    label_right_boundary: float,
    edge_tolerance: float,
) -> tuple[TextRun, ...]:
    body_label_runs = [
        run
        for run in runs
        if data_start <= run.y_center < data_end
        and run.bbox.x0 < label_right_boundary
        and any(character.isalpha() for character in run.normalized_text)
    ]
    if not body_label_runs:
        return ()
    content_left = min(run.bbox.x0 for run in body_label_runs)
    return tuple(
        run
        for run in runs
        if data_start <= run.y_center < data_end
        and run.bbox.x1 < label_right_boundary
        and run.bbox.x0 < content_left - edge_tolerance * 2
        and not any(character.isalpha() for character in run.normalized_text)
        and _is_observed_financial(run)
        and run.raw_text.strip().isdigit()
    )


def _duration_start(period_end: date, months: int) -> date:
    month_index = period_end.year * 12 + period_end.month - months
    return date(month_index // 12, month_index % 12 + 1, 1)


def _parse_tm_header_money_unit(text: str):
    """Parse only explicit source unit atoms, never ordinary Vietnamese prose.

    ``parse_unit`` intentionally accepts the standalone word ``đồng``.  Its
    accent-folded retrieval form also occurs inside unrelated words such as
    ``biến động``.  TM header routing therefore requires an explicit money
    scale phrase or a compact standalone currency atom before delegating.
    """

    key = retrieval_key(text)
    explicit_scales = (
        "ty dong",
        "trieu dong",
        "nghin dong",
        "ngan dong",
        "ty vnd",
        "trieu vnd",
        "nghin vnd",
        "vnd billion",
        "vnd million",
    )
    if any(scale in key for scale in explicit_scales) or key in {
        "vnd",
        "dong",
        "viet nam dong",
    }:
        parsed = parse_unit(text)
        if parsed.canonical is not None and parsed.multiplier is not None:
            return parsed
    return None


def _native_tm_axis_bindings(
    geometry: PageGeometry,
    geometry_config: GeometryConfig,
    rows: tuple[StatementRow, ...],
) -> tuple[NativeTMAxisBinding, ...]:
    """Bind local TM axes without copying an incompatible shared unit."""

    axes = tuple(axis for axis in geometry.axes if axis.role is ColumnRole.VALUE)
    if not axes:
        return ()
    base_by_axis = {
        binding.axis_id: binding for binding in bind_value_headers(geometry, geometry_config)
    }
    header_runs = tuple(
        run
        for run in geometry.runs
        if run.bbox.y1 < geometry.data_start_y and run.bbox.y0 >= geometry.height_points * 0.08
    )
    local_runs: dict[str, list[TextRun]] = {axis.axis_id: [] for axis in axes}
    for run in header_runs:
        if run.bbox.x1 < geometry.label_right_boundary - geometry.edge_tolerance:
            continue
        if (
            run.bbox.x0 < geometry.label_right_boundary
            and run.bbox.x1 - run.bbox.x0 > geometry.width_points * 0.40
        ):
            continue
        owner = min(axes, key=lambda axis: abs(axis.right_edge - run.bbox.x1))
        local_runs[owner.axis_id].append(run)
    for runs in local_runs.values():
        runs.sort(key=lambda run: (run.bbox.y0, run.bbox.x0, run.run_id))

    all_header_text = normalize_text(" ".join(run.normalized_text for run in header_runs))
    all_header_key = retrieval_key(all_header_text)
    semantic_percent_runs = tuple(
        run for run in header_runs if "%" in run.raw_text and "ty le" in retrieval_key(run.raw_text)
    )
    table_wide_percentage = len(semantic_percent_runs) == 1 and (
        len(axes) == 1
        or (
            semantic_percent_runs[0].bbox.x0 <= axes[0].center
            and semantic_percent_runs[0].bbox.x1 >= (axes[0].center + axes[-1].center) / 2
        )
    )
    table_wide_rate = "ty gia" in all_header_key and "vnd" in all_header_key
    table_wide_vnd_conversion = "quy doi sang vnd" in all_header_key
    row_keys = tuple(retrieval_key(row.label) for row in rows)
    row_dates = {observed for row in rows for observed in parse_vietnamese_dates(row.label)}
    has_snapshot_rows = any(
        key.startswith(("so du dau", "so du cuoi", "tai ngay")) for key in row_keys
    )
    has_duration_rows = any(
        marker in key
        for key in row_keys
        for marker in ("trong ky", "trong nam", "phat sinh", "trich lap", "hoan nhap")
    )
    has_duration_statement_rows = any(
        re.match(r"^(?:i|ii)\s+(?:doanh thu|chi phi)\b", key)
        or key.startswith("ket qua kinh doanh")
        for key in row_keys
    )
    has_snapshot_statement_rows = any(
        re.match(r"^(?:iii|iv)\s+(?:tai san|no phai tra)\b", key) for key in row_keys
    )
    row_dependent_period = (
        (has_snapshot_rows and has_duration_rows)
        or (has_duration_statement_rows and has_snapshot_statement_rows)
        or len(row_dates) >= 2
    )
    header_has_separate_share_axes = "so luong" in all_header_key and "co phieu" in all_header_key
    row_dependent_unit = table_wide_rate or (
        not header_has_separate_share_axes
        and any(
            "nguoi" in key
            or "so luong co phieu" in key
            or "thu nhap tren moi co phieu" in key
            or ("thoi gian" in key and ("nam" in key or "thang" in key))
            for key in row_keys
        )
    )
    global_source_units = {
        (parsed.canonical, parsed.multiplier)
        for run in header_runs
        if run.run_id in geometry.unit_run_ids
        for parsed in (_parse_tm_header_money_unit(run.normalized_text),)
        if parsed is not None
    }

    drafts: list[dict[str, Any]] = []
    for axis in axes:
        runs = local_runs[axis.axis_id]
        raw_header = normalize_text(" ".join(run.normalized_text for run in runs))
        key = retrieval_key(raw_header)
        dates = parse_vietnamese_dates(raw_header)
        explicit_period_end = dates[-1] if dates else None
        parsed_units = [
            (run, parsed)
            for run in runs
            for parsed in (_parse_tm_header_money_unit(run.normalized_text),)
            if parsed is not None
        ]
        percent_evidence = "%" in raw_header
        share_evidence = "so luong" in key and "co phieu" in key
        conflicts: list[str] = []
        evidence: list[str] = [
            "header atoms are assigned by source right-edge alignment within this table"
        ]
        unit_bbox: BoundingBox | None = None
        unit_denominator: str | None = None
        if table_wide_rate:
            measure_role = "RATE"
            unit = "VND"
            unit_multiplier = 1
            unit_denominator = "ROW_LABEL_CURRENCY_OR_COMMODITY_UNIT"
            unit_scope = "ROW_DEPENDENT"
            evidence.append("source table title explicitly states exchange rates against VND")
        elif percent_evidence or table_wide_percentage:
            measure_role = "PERCENTAGE"
            unit = "PERCENT"
            unit_multiplier = 1
            unit_scope = "AXIS"
            percent_source = next(
                (run for run in runs if "%" in run.raw_text),
                semantic_percent_runs[0] if table_wide_percentage else None,
            )
            unit_bbox = percent_source.bbox if percent_source else None
            evidence.append(
                "explicit source percentage heading governs this axis"
                if percent_evidence
                else "single explicit table-wide percentage heading governs all value axes"
            )
            if parsed_units:
                conflicts.append("EXPLICIT_PERCENT_MEASURE_VS_MONEY_SCALE_TOKEN")
        elif share_evidence:
            measure_role = "QUANTITY"
            unit = "SHARE"
            unit_multiplier = 1
            unit_scope = "AXIS"
            unit_bbox = _union(
                run.bbox for run in runs if "co phieu" in retrieval_key(run.raw_text)
            )
            evidence.append("source axis header explicitly states share quantity")
        elif parsed_units:
            source_units = {(parsed.canonical, parsed.multiplier) for _run, parsed in parsed_units}
            if len(source_units) == 1:
                measure_role = "AMOUNT"
                unit, unit_multiplier = next(iter(source_units))
                unit_scope = "ROW_DEPENDENT" if row_dependent_unit else "AXIS_DEFAULT"
                unit_bbox = parsed_units[-1][0].bbox
                evidence.append("money scale is parsed from an axis-local source unit token")
            else:
                measure_role = "UNKNOWN"
                unit = None
                unit_multiplier = None
                unit_scope = "UNRESOLVED"
                conflicts.append("MULTIPLE_INCOMPATIBLE_AXIS_UNIT_TOKENS")
        elif table_wide_vnd_conversion:
            if len(global_source_units) == 1:
                measure_role = "AMOUNT"
                unit, unit_multiplier = next(iter(global_source_units))
                unit_scope = "TABLE_DEFAULT"
                evidence.append(
                    "source table title states conversion to VND and sibling axes expose the scale"
                )
            else:
                measure_role = "UNKNOWN"
                unit = None
                unit_multiplier = None
                unit_scope = "UNRESOLVED"
                conflicts.append("TABLE_WIDE_CONVERSION_SCALE_IS_NOT_UNIQUE")
        else:
            measure_role = "UNKNOWN"
            unit = None
            unit_multiplier = None
            unit_scope = "UNRESOLVED"
            evidence.append("no compatible source measure/unit authority resolves this axis")

        base = base_by_axis.get(axis.axis_id)
        period_type = None
        duration_months = None
        period_start = None
        if explicit_period_end is not None:
            duration_match = re.search(
                r"(?:ky ke toan\s+)?(?P<months>\d{1,2})\s+thang\s+ket thuc",
                key,
            )
            if duration_match:
                duration_months = int(duration_match.group("months"))
                period_type = "DURATION" if 1 <= duration_months <= 12 else None
                period_start = (
                    _duration_start(explicit_period_end, duration_months) if period_type else None
                )
            elif re.search(r"(?:trong|cho)\s+ky\s+ke\s+toan.*ket\s+thuc", key):
                period_type = "DURATION"
            elif base and base.period_end == explicit_period_end and base.period_type:
                period_type = base.period_type
                duration_months = base.duration_months
                period_start = base.period_start
            else:
                period_type = "SNAPSHOT"
                period_start = explicit_period_end
            evidence.append("period is parsed from right-edge-aligned source header atoms")
        drafts.append(
            {
                "axis": axis,
                "runs": runs,
                "raw_header": raw_header,
                "header_bbox": _union(run.bbox for run in runs) if runs else None,
                "period_end": explicit_period_end,
                "period_start": period_start,
                "period_type": period_type,
                "period_scope": "AXIS_OR_TABLE_HEADER" if explicit_period_end else "UNRESOLVED",
                "duration_months": duration_months,
                "period_group_owner": None,
                "measure_role": measure_role,
                "unit": unit,
                "unit_multiplier": unit_multiplier,
                "unit_denominator": unit_denominator,
                "unit_scope": unit_scope,
                "unit_bbox": unit_bbox,
                "restated": "trinh bay lai" in key or "restated" in key,
                "conflicts": conflicts,
                "evidence": evidence,
            }
        )

    dated_indices = [index for index, draft in enumerate(drafts) if draft["period_end"]]
    if not dated_indices:
        table_dates = tuple(dict.fromkeys(parse_vietnamese_dates(all_header_text)))
        if len(table_dates) == 1:
            table_duration_match = re.search(
                r"(?:ky ke toan\s+)?(?P<months>\d{1,2})\s+thang\s+ket thuc",
                all_header_key,
            )
            table_is_duration = bool(
                table_duration_match
                or re.search(
                    r"(?:trong|cho)\s+ky\s+ke\s+toan.*ket\s+thuc",
                    all_header_key,
                )
            )
            table_duration_months = (
                int(table_duration_match.group("months"))
                if table_duration_match and 1 <= int(table_duration_match.group("months")) <= 12
                else None
            )
            for draft in drafts:
                draft["period_end"] = table_dates[0]
                draft["period_start"] = (
                    _duration_start(table_dates[0], table_duration_months)
                    if table_duration_months is not None
                    else None
                    if table_is_duration
                    else table_dates[0]
                )
                draft["period_type"] = "DURATION" if table_is_duration else "SNAPSHOT"
                draft["duration_months"] = table_duration_months
                draft["period_group_owner"] = 0
                draft["evidence"].append(
                    "single source table-wide date applies to every local value axis"
                )
    else:
        for index in dated_indices:
            drafts[index]["period_group_owner"] = index
        explicit_dates = {drafts[index]["period_end"] for index in dated_indices}
        if len(explicit_dates) == 1 and len({draft["measure_role"] for draft in drafts}) == 1:
            owner = dated_indices[0]
            for draft in drafts:
                draft["period_group_owner"] = owner
                if draft["period_end"] is None:
                    for field in (
                        "period_end",
                        "period_start",
                        "period_type",
                        "duration_months",
                    ):
                        draft[field] = drafts[owner][field]
                    draft["evidence"].append(
                        "one repeated source period governs homogeneous table measures"
                    )
        elif len(dated_indices) >= 2:
            for draft in drafts:
                if draft["period_end"] is not None:
                    continue
                distances = sorted(
                    (
                        abs(draft["axis"].center - drafts[owner]["axis"].center),
                        owner,
                    )
                    for owner in dated_indices
                )
                if len(distances) == 1 or distances[0][0] < distances[1][0] - 1e-6:
                    draft["period_group_owner"] = distances[0][1]
            grouped: list[list[int]] = []
            for owner in dated_indices:
                grouped.append(
                    [
                        index
                        for index, draft in enumerate(drafts)
                        if draft["period_group_owner"] == owner
                    ]
                )
            signatures = [
                tuple(drafts[index]["measure_role"] for index in group) for group in grouped
            ]
            repeated_signature = bool(signatures) and len(set(signatures)) == 1
            if repeated_signature:
                for draft in drafts:
                    owner = draft["period_group_owner"]
                    if owner is None or draft["period_end"] is not None:
                        continue
                    for field in (
                        "period_end",
                        "period_start",
                        "period_type",
                        "duration_months",
                    ):
                        draft[field] = drafts[owner][field]
                    draft["evidence"].append(
                        "period is propagated within a uniquely repeated local measure group"
                    )
            else:
                for index, draft in enumerate(drafts):
                    if index not in dated_indices:
                        draft["period_group_owner"] = None

    if row_dependent_period:
        for draft in drafts:
            draft["period_start"] = None
            draft["period_type"] = None
            draft["duration_months"] = None
            draft["period_scope"] = "ROW_DEPENDENT"
            draft["evidence"].append(
                "source rows mix or carry their own period semantics; the axis cannot flatten them"
            )
    else:
        for draft in drafts:
            if draft["period_end"] is not None:
                draft["period_scope"] = "AXIS_OR_TABLE_HEADER"

    resolved_dates = sorted(
        {draft["period_end"] for draft in drafts if draft["period_end"] is not None},
        reverse=True,
    )
    date_role = (
        {
            observed: "CURRENT" if index == 0 else "COMPARATIVE"
            for index, observed in enumerate(resolved_dates)
        }
        if len(resolved_dates) >= 2
        else {}
    )
    owner_ordinals = {
        owner: ordinal
        for ordinal, owner in enumerate(
            dict.fromkeys(
                draft["period_group_owner"]
                for draft in drafts
                if draft["period_group_owner"] is not None
            ),
            1,
        )
    }
    bindings = []
    for draft in drafts:
        conflicts = tuple(draft["conflicts"])
        status = (
            "RESOLVED_WITH_SOURCE_CONFLICT"
            if conflicts
            else "PARTIALLY_RESOLVED"
            if draft["unit_scope"] == "ROW_DEPENDENT" or draft["period_scope"] == "ROW_DEPENDENT"
            else "RESOLVED"
            if draft["measure_role"] != "UNKNOWN" and draft["period_end"] is not None
            else "PARTIALLY_RESOLVED"
            if draft["measure_role"] != "UNKNOWN" or draft["period_end"] is not None
            else "UNRESOLVED"
        )
        period_owner = draft["period_group_owner"]
        bindings.append(
            NativeTMAxisBinding(
                axis_id=draft["axis"].axis_id,
                raw_header=draft["raw_header"],
                header_bbox=draft["header_bbox"],
                period_group_id=(
                    f"period-group-{owner_ordinals[period_owner]:03d}"
                    if period_owner is not None
                    else None
                ),
                period_start=draft["period_start"],
                period_end=draft["period_end"],
                period_type=draft["period_type"],
                period_scope=draft["period_scope"],
                duration_months=draft["duration_months"],
                current_or_comparative=date_role.get(draft["period_end"]),
                measure_role=draft["measure_role"],
                unit=draft["unit"],
                unit_multiplier=draft["unit_multiplier"],
                unit_denominator=draft["unit_denominator"],
                unit_scope=draft["unit_scope"],
                unit_bbox=draft["unit_bbox"],
                restated=draft["restated"],
                binding_status=status,
                confidence=(1.0 if status == "RESOLVED" else 0.85 if conflicts else 0.5),
                source_run_ids=tuple(run.run_id for run in draft["runs"]),
                conflicts=conflicts,
                evidence=tuple(draft["evidence"]),
            )
        )
    return tuple(bindings)


def _separate_row_local_scalars(
    rows: Iterable[StatementRow],
    *,
    axes: tuple[ColumnAxis, ...],
    region_runs: tuple[TextRun, ...],
    table_id: str,
    edge_tolerance: float,
) -> tuple[
    tuple[StatementRow, ...], tuple[NativeTMScalarDisclosure, ...], tuple[StatementRow, ...]
]:
    """Separate dated one-value disclosures from an adjacent multi-axis grid."""

    retained: list[StatementRow] = []
    scalar_rows: list[StatementRow] = []
    disclosures: list[NativeTMScalarDisclosure] = []
    if len(axes) <= 1:
        materialized = tuple(rows)
        return materialized, (), ()
    for row in rows:
        dates = parse_vietnamese_dates(row.label)
        if len(row.cells) != 1 or len(dates) != 1:
            retained.append(row)
            continue
        cell = row.cells[0]
        unit_candidates = []
        for run in region_runs:
            parsed_unit = _parse_tm_header_money_unit(run.normalized_text)
            if (
                parsed_unit is not None
                and run.bbox.x0 >= cell.bbox.x1
                and abs(run.y_center - ((cell.bbox.y0 + cell.bbox.y1) / 2))
                <= max(run.height, cell.bbox.y1 - cell.bbox.y0, edge_tolerance)
            ):
                unit_candidates.append((run, parsed_unit))
        if len(unit_candidates) != 1:
            retained.append(row)
            continue
        unit_run, parsed_unit = unit_candidates[0]
        source_status = {
            ObservationKind.VALUE: "OBSERVED_VALUE",
            ObservationKind.ZERO: "OBSERVED_ZERO",
            ObservationKind.DASH: "DASH",
            ObservationKind.BLANK: "BLANK",
            ObservationKind.INVALID: "INVALID_SOURCE_MARKER",
        }[cell.parsed.observation]
        disclosures.append(
            NativeTMScalarDisclosure(
                scalar_id=f"{table_id}:scalar-{len(disclosures) + 1:03d}",
                source_row_id=row.row_id,
                page=row.page,
                label=row.label,
                label_boxes=row.label_boxes,
                period_end=dates[0],
                source_status=source_status,
                raw_text=cell.raw_text,
                value_text=(str(cell.parsed.value) if cell.parsed.value is not None else None),
                value_bbox=cell.bbox,
                value_run_id=cell.run_id,
                unit=parsed_unit.canonical,
                unit_multiplier=parsed_unit.multiplier,
                unit_raw_text=unit_run.raw_text,
                unit_bbox=unit_run.bbox,
                unit_run_id=unit_run.run_id,
                ownership_status="ROW_LOCAL_SCALAR_DISCLOSURE",
                evidence=(
                    "source row contains exactly one date and one visible financial value",
                    "an explicit source unit is aligned on the same row",
                    "the disclosure is separated from the preceding multi-axis grid",
                    "no value magnitude, page rule, schema, or history selected this structure",
                ),
            )
        )
        scalar_rows.append(row)
    return tuple(retained), tuple(disclosures), tuple(scalar_rows)


def _grid_slots(
    rows: Iterable[StatementRow],
    axes: tuple[ColumnAxis, ...],
    *,
    geometry: PageGeometry,
) -> tuple[NativeTMGridSlot, ...]:
    centers = [axis.center for axis in axes]
    slots: list[NativeTMGridSlot] = []
    for row in rows:
        if not row.cells:
            continue
        by_axis = {cell.axis_id: cell for cell in row.cells}
        if len(by_axis) != len(row.cells):
            raise NativeTMRegionError(f"row {row.row_id} has duplicate source cells on one axis")
        for ordinal, axis in enumerate(axes):
            left = (
                geometry.label_right_boundary
                if ordinal == 0
                else (centers[ordinal - 1] + centers[ordinal]) / 2
            )
            right = (
                geometry.width_points
                if ordinal + 1 == len(axes)
                else (centers[ordinal] + centers[ordinal + 1]) / 2
            )
            slot_bbox = BoundingBox(left, row.y0, right, row.y1)
            cell = by_axis.get(axis.axis_id)
            if cell is None:
                slots.append(
                    NativeTMGridSlot(
                        row_id=row.row_id,
                        axis_id=axis.axis_id,
                        axis_ordinal=ordinal,
                        source_status="UNRESOLVED_EMPTY_SLOT",
                        raw_text=None,
                        value_text=None,
                        source_bbox=None,
                        grid_slot_bbox=slot_bbox,
                        source_run_id=None,
                        evidence=(
                            "no native text run is assigned to this expected grid slot",
                            "absence is not promoted to BLANK without independent pixel evidence",
                        ),
                    )
                )
                continue
            status = {
                ObservationKind.VALUE: "OBSERVED_VALUE",
                ObservationKind.ZERO: "OBSERVED_ZERO",
                ObservationKind.DASH: "DASH",
                ObservationKind.BLANK: "BLANK",
                ObservationKind.INVALID: "INVALID_SOURCE_MARKER",
            }[cell.parsed.observation]
            slots.append(
                NativeTMGridSlot(
                    row_id=row.row_id,
                    axis_id=axis.axis_id,
                    axis_ordinal=ordinal,
                    source_status=status,
                    raw_text=cell.raw_text,
                    value_text=(str(cell.parsed.value) if cell.parsed.value is not None else None),
                    source_bbox=cell.bbox,
                    grid_slot_bbox=slot_bbox,
                    source_run_id=cell.run_id,
                    evidence=(
                        "source-visible native run is assigned to the local value axis",
                        "numeric parsing preserves value, zero, dash, and invalid marker distinctions",
                    ),
                )
            )
    return tuple(slots)


def _separate_inter_table_context(
    regions: Iterable[NativeTMTableRegion],
) -> tuple[tuple[NativeTMTableRegion, ...], tuple[NativeTMInterTableContext, ...]]:
    """Separate source rows whose table ownership is geometrically ambiguous.

    A band between tables may contain either a heading for the following table
    or a footnote for the preceding one.  Geometry alone cannot distinguish
    them, so this stage gives the band its own explicit unresolved ownership.
    It does not interpret note numbers or titles and leaves axis-local headers
    unchanged.
    """

    allocated = list(regions)
    contexts: list[NativeTMInterTableContext] = []
    for target_index in range(1, len(allocated)):
        predecessor = allocated[target_index - 1]
        target = allocated[target_index]
        if not predecessor.rows or not target.header_runs:
            continue
        predecessor_data_end = max(row.y1 for row in predecessor.rows)
        target_header_start = min(run.bbox.y0 for run in target.header_runs)
        selected_rows = tuple(
            row
            for row in predecessor.outside_financial_span_rows
            if not row.cells
            and row.y0 >= predecessor_data_end
            and row.y1 <= target_header_start
            and any(box.x0 < target.geometry.label_right_boundary for box in row.label_boxes)
        )
        if not selected_rows:
            continue

        runs_by_box: dict[tuple[float, float, float, float], list[TextRun]] = {}
        for run in predecessor.geometry.runs:
            key = (run.bbox.x0, run.bbox.y0, run.bbox.x1, run.bbox.y1)
            runs_by_box.setdefault(key, []).append(run)
        selected_runs: list[TextRun] = []
        for row in selected_rows:
            boxes = [*row.label_boxes]
            if row.note_bbox is not None:
                boxes.append(row.note_bbox)
            for box in boxes:
                key = (box.x0, box.y0, box.x1, box.y1)
                matches = runs_by_box.get(key, [])
                if len(matches) != 1:
                    raise NativeTMRegionError(
                        "inter-table context row does not resolve to one native run"
                    )
                selected_runs.append(matches[0])
        if len({run.run_id for run in selected_runs}) != len(selected_runs):
            raise NativeTMRegionError("inter-table context repeats a native run")
        selected_runs.sort(key=lambda run: (run.bbox.y0, run.bbox.x0, run.run_id))
        selected_run_ids = {run.run_id for run in selected_runs}
        selected_row_ids = {row.row_id for row in selected_rows}
        predecessor = replace(
            predecessor,
            geometry=replace(
                predecessor.geometry,
                runs=tuple(
                    run for run in predecessor.geometry.runs if run.run_id not in selected_run_ids
                ),
            ),
            outside_financial_span_rows=tuple(
                row
                for row in predecessor.outside_financial_span_rows
                if row.row_id not in selected_row_ids
            ),
            unassigned_runs=tuple(
                run for run in predecessor.unassigned_runs if run.run_id not in selected_run_ids
            ),
        )
        contexts.append(
            NativeTMInterTableContext(
                page=target.page,
                preceding_table_id=predecessor.table_id,
                following_table_id=target.table_id,
                source_row_ids=tuple(row.row_id for row in selected_rows),
                runs=tuple(selected_runs),
                bbox=_union(run.bbox for run in selected_runs),
                ownership_status="UNRESOLVED_INTER_TABLE_OWNERSHIP",
                evidence=(
                    "cell-free source rows occur after the preceding financial span",
                    "source rows end before the following axis-local header",
                    "geometry cannot decide whether the band is a prior footnote or next heading",
                    "no note number, page rule, schema, or historical value selected an owner",
                ),
            )
        )
        allocated[target_index - 1] = predecessor
    return tuple(allocated), tuple(contexts)


def discover_native_tm_regions(
    page: PDFTextPage,
    *,
    geometry_config: GeometryConfig,
    policy: NativeTMRegionPolicy,
    table_id_prefix: str,
    excluded_spans: tuple[ExcludedNativeTextSpan, ...] = (),
) -> NativeTMPageRegions:
    """Discover locally headed quantitative table regions on one native-text page.

    Every accepted region has independent source-visible unit and aligned-value
    evidence.  Unit-like prose remains in diagnostics, never a table.  This
    function does not infer accounting concepts, periods from magnitudes, schema
    IDs, note numbers, or missing items.
    """

    if page.text_quality != "USABLE_TEXT_LAYER":
        raise NativeTMRegionError(f"page {page.page} has no usable native text geometry")
    if not table_id_prefix or any(character.isspace() for character in table_id_prefix):
        raise NativeTMRegionError("native TM table ID prefix must be nonempty and whitespace-free")
    runs = build_text_runs(
        page.words,
        gap_height_factor=geometry_config.run_separation_gap_height_factor,
        financial_gap_height_factor=geometry_config.financial_token_separation_gap_height_factor,
    )
    median_height = _median_run_height(runs)
    edge_tolerance = max(
        geometry_config.minimum_edge_tolerance_points,
        page.width_points * geometry_config.edge_tolerance_ratio,
    )
    raw_groups = _group_unit_runs(runs, median_height=median_height, policy=policy)
    accepted_groups, diagnostics = _diagnose_unit_groups(
        page,
        runs,
        raw_groups,
        median_height=median_height,
        policy=policy,
        geometry_config=geometry_config,
        edge_tolerance=edge_tolerance,
    )
    header_starts = [
        _header_start(
            page,
            runs,
            group,
            median_height=median_height,
            policy=policy,
        )
        for group in accepted_groups
    ]
    regions: list[NativeTMTableRegion] = []
    assigned_run_ids: set[str] = set()
    for index, group in enumerate(accepted_groups):
        data_start = max(run.bbox.y1 for run in group) + (
            median_height * policy.data_start_gap_height_factor
        )
        data_end = (
            header_starts[index + 1] - median_height * policy.next_header_gap_height_factor
            if index + 1 < len(accepted_groups)
            else page.height_points * geometry_config.footer_y_ratio
        )
        if data_end <= data_start:
            raise NativeTMRegionError("accepted native TM regions overlap after local headers")
        numeric_runs = [
            run
            for run in runs
            if data_start <= run.y_center < data_end and _is_observed_financial(run)
        ]
        axes = _axes_for_region(
            group,
            numeric_runs,
            page_width=page.width_points,
            edge_tolerance=edge_tolerance,
            policy=policy,
        )
        if not axes:
            raise NativeTMRegionError("accepted native TM region has no value axes")
        header_start = header_starts[index]
        bounded_runs = tuple(run for run in runs if header_start <= run.y_center < data_end)
        label_right_boundary = (
            min(axis.left_edge for axis in axes)
            - page.width_points * policy.label_boundary_margin_ratio
        )
        detached_margin_runs = _detached_margin_runs(
            bounded_runs,
            data_start=data_start,
            data_end=data_end,
            label_right_boundary=label_right_boundary,
            edge_tolerance=edge_tolerance,
        )
        detached_margin_run_ids = {run.run_id for run in detached_margin_runs}
        region_runs = tuple(
            run for run in bounded_runs if run.run_id not in detached_margin_run_ids
        )
        geometry = PageGeometry(
            page=page.page,
            width_points=page.width_points,
            height_points=page.height_points,
            data_start_y=data_start,
            data_end_y=data_end,
            label_right_boundary=label_right_boundary,
            edge_tolerance=edge_tolerance,
            runs=region_runs,
            axes=axes,
            unit_run_ids=tuple(run.run_id for run in group),
            warnings=(),
        )
        table_id = f"{table_id_prefix}:page-{page.page:04d}:table-{index + 1:03d}"
        all_rows = _merge_statement_rows(
            reconstruct_statement_rows(
                geometry,
                geometry_config,
                table_id=table_id,
            ),
            geometry=geometry,
            geometry_config=geometry_config,
            table_id=table_id,
        )
        span_rows = tuple(financial_table_span(list(all_rows)))
        span_ids = {row.row_id for row in span_rows}
        outside_rows = tuple(row for row in all_rows if row.row_id not in span_ids)
        span_rows, scalar_disclosures, scalar_rows = _separate_row_local_scalars(
            span_rows,
            axes=axes,
            region_runs=region_runs,
            table_id=table_id,
            edge_tolerance=edge_tolerance,
        )
        slots = _grid_slots(span_rows, axes, geometry=geometry)
        used_boxes = _row_box_keys([*span_rows, *scalar_rows, *outside_rows])
        used_run_ids = {
            run.run_id
            for run in region_runs
            if (run.bbox.x0, run.bbox.y0, run.bbox.x1, run.bbox.y1) in used_boxes
        }
        used_run_ids.update(run.run_id for run in group)
        used_run_ids.update(disclosure.unit_run_id for disclosure in scalar_disclosures)
        unassigned = tuple(
            sorted(
                [*detached_margin_runs]
                + [
                    run
                    for run in region_runs
                    if run.y_center >= data_start and run.run_id not in used_run_ids
                ],
                key=lambda run: (run.bbox.y0, run.bbox.x0, run.run_id),
            )
        )
        assigned_run_ids.update(run.run_id for run in bounded_runs)
        header_runs = tuple(run for run in region_runs if run.bbox.y1 < data_start)
        regions.append(
            NativeTMTableRegion(
                table_id=table_id,
                page=page.page,
                table_order=index,
                region_bbox=BoundingBox(0.0, header_start, page.width_points, data_end),
                header_runs=header_runs,
                geometry=geometry,
                header_bindings=_native_tm_axis_bindings(
                    geometry,
                    geometry_config,
                    tuple(span_rows),
                ),
                rows=tuple(span_rows),
                grid_slots=slots,
                scalar_disclosures=scalar_disclosures,
                outside_financial_span_rows=outside_rows,
                detached_margin_runs=detached_margin_runs,
                unassigned_runs=unassigned,
                acceptance_signals=(
                    "source-visible exact unit header group",
                    "local numeric observations align with every distinct unit axis",
                    "table header and data bounds are local to this region",
                    "numeric magnitudes and schema/history were not routing inputs",
                ),
            )
        )
    unassigned_page_runs = tuple(run for run in runs if run.run_id not in assigned_run_ids)
    allocated_regions, inter_table_contexts = _separate_inter_table_context(regions)
    return NativeTMPageRegions(
        page=page.page,
        regions=allocated_regions,
        inter_table_contexts=inter_table_contexts,
        unit_group_diagnostics=tuple(diagnostics),
        excluded_spans=excluded_spans,
        unassigned_page_runs=unassigned_page_runs,
    )
