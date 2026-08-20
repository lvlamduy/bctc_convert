"""Text-blind detector geometry and crop freeze for family-first VietOCR.

PP-OCRv6 detection supplies only quadrilateral geometry and detector scores.
Every detected line is retained without inspecting recognition text, bank,
filing metadata, page identity, or a family specification.  Deterministic RGB
PNG crops become the reference-blind input to VietOCR Transformer; downstream
family topology still has to replay the source, geometry, periods, units,
accounting relations, and schema separately.
"""

from __future__ import annotations

import hashlib
import io
import math
from collections.abc import Mapping, Sequence
from statistics import median
from typing import Any

from PIL import Image, ImageOps

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "SOURCE_PADDING",
    "WHITE_BORDER",
    "FamilyFirstSemanticLabelFreezeV1Error",
    "build_family_first_semantic_label_page_freeze_v1",
    "project_ordered_detector_line_axis_v1",
    "validate_family_first_semantic_label_page_freeze_replay_v1",
]


FORMAT_VERSION = "FAMILY_FIRST_SEMANTIC_LABEL_PAGE_FREEZE_V1"
SOURCE_PADDING = (8, 4, 8, 4)
WHITE_BORDER = (12, 8, 12, 8)
CLAIM_BOUNDARY = (
    "TEXT_BLIND_ALL_PPOCRV6_DETECTED_LINE_GEOMETRY_DETERMINISTIC_RGB_PNG_CROP_"
    "FREEZE_FOR_REFERENCE_BLIND_VIETOCR_ONLY_NO_RECOGNITION_NUMERIC_PERIOD_UNIT_"
    "STRUCTURE_FAMILY_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "all_detected_lines_retained": True,
    "bank_file_page_period_family_used_for_line_selection": False,
    "detector_recognition_text_accessed": False,
    "family_authority": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "period_or_unit_authority": False,
    "ppocrv6_detection_geometry_only": True,
    "schema_authority": False,
    "semantic_authority": False,
}
_DETECTOR_FIELDS = {"dt_polys", "dt_scores", "input_path", "page_index"}
_PAGE_FIELDS = {
    "authority",
    "claim_boundary",
    "crops",
    "detector_line_axis",
    "format_version",
    "metrics",
    "page_id",
    "physical_page",
    "render_ref",
}


class FamilyFirstSemanticLabelFreezeV1Error(ValueError):
    """Detector geometry, render bytes, crop output, or replay drifted."""


def _error(message: str) -> FamilyFirstSemanticLabelFreezeV1Error:
    return FamilyFirstSemanticLabelFreezeV1Error(message)


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be one positive exact integer")
    return value


def _finite_number(value: Any, label: str) -> float:
    if type(value) not in {int, float} or not math.isfinite(float(value)):
        raise _error(f"{label} must be one finite non-boolean number")
    return float(value)


def _point(value: Any, *, width: int, height: int, label: str) -> tuple[float, float]:
    if type(value) is not list or len(value) != 2:
        raise _error(f"{label} must be one [x, y] point")
    x = _finite_number(value[0], f"{label} x")
    y = _finite_number(value[1], f"{label} y")
    if not 0 <= x <= width or not 0 <= y <= height:
        raise _error(f"{label} lies outside the rendered page")
    return x, y


def _polygon(value: Any, *, width: int, height: int, label: str) -> list[list[float]]:
    if type(value) is not list or len(value) != 4:
        raise _error(f"{label} must be one quadrilateral")
    points = [_point(point, width=width, height=height, label=label) for point in value]
    area = abs(
        sum(
            left[0] * right[1] - right[0] * left[1]
            for left, right in zip(points, [*points[1:], points[0]], strict=True)
        )
        / 2
    )
    if area <= 0:
        raise _error(f"{label} quadrilateral is degenerate")
    return [[x, y] for x, y in points]


def _outward_bbox(polygon: Sequence[Sequence[float]], *, width: int, height: int) -> list[int]:
    left = max(0, math.floor(min(point[0] for point in polygon)))
    top = max(0, math.floor(min(point[1] for point in polygon)))
    right = min(width, math.ceil(max(point[0] for point in polygon)))
    bottom = min(height, math.ceil(max(point[1] for point in polygon)))
    if right <= left or bottom <= top:
        raise _error("detector quadrilateral has no positive outward bbox")
    return [left, top, right, bottom]


def _row_bands(records: Sequence[Mapping[str, Any]]) -> list[list[Mapping[str, Any]]]:
    if not records:
        return []
    scale = float(
        median(record["raw_pixel_bbox"][3] - record["raw_pixel_bbox"][1] for record in records)
    )
    bands: list[list[Mapping[str, Any]]] = []
    for record in sorted(
        records,
        key=lambda item: (
            (item["raw_pixel_bbox"][1] + item["raw_pixel_bbox"][3]) / 2,
            item["raw_pixel_bbox"][0],
            item["detector_index"],
        ),
    ):
        center = (record["raw_pixel_bbox"][1] + record["raw_pixel_bbox"][3]) / 2
        candidates = [
            band
            for band in bands
            if abs(
                center
                - float(
                    median(
                        (item["raw_pixel_bbox"][1] + item["raw_pixel_bbox"][3]) / 2 for item in band
                    )
                )
            )
            <= scale * 0.62
        ]
        if candidates:
            min(
                candidates,
                key=lambda band: abs(
                    center
                    - median(
                        (item["raw_pixel_bbox"][1] + item["raw_pixel_bbox"][3]) / 2 for item in band
                    )
                ),
            ).append(record)
        else:
            bands.append([record])
    return sorted(
        bands,
        key=lambda band: min(item["raw_pixel_bbox"][1] for item in band),
    )


def project_ordered_detector_line_axis_v1(
    detector_payload: Any, *, pixel_width: int, pixel_height: int
) -> list[dict[str, Any]]:
    """Validate and put all detector quadrilaterals in geometric reading order."""

    width = _positive_int(pixel_width, "render width")
    height = _positive_int(pixel_height, "render height")
    if type(detector_payload) is not dict or set(detector_payload) != _DETECTOR_FIELDS:
        raise _error("detector-only provider payload fields drifted")
    polygons = detector_payload["dt_polys"]
    scores = detector_payload["dt_scores"]
    if type(polygons) is not list or type(scores) is not list or len(polygons) != len(scores):
        raise _error("detector polygon and score axes differ")
    records = []
    for detector_index, (raw_polygon, raw_score) in enumerate(zip(polygons, scores, strict=True)):
        polygon = _polygon(
            raw_polygon,
            width=width,
            height=height,
            label=f"detector polygon {detector_index}",
        )
        score = _finite_number(raw_score, f"detector score {detector_index}")
        if not 0 <= score <= 1:
            raise _error("detector score lies outside [0, 1]")
        records.append(
            {
                "detector_index": detector_index,
                "detector_score": score,
                "polygon": polygon,
                "raw_pixel_bbox": _outward_bbox(polygon, width=width, height=height),
            }
        )
    ordered = [
        record
        for band in _row_bands(records)
        for record in sorted(
            band,
            key=lambda item: (item["raw_pixel_bbox"][0], item["detector_index"]),
        )
    ]
    return [
        {**canonical_clone_v1(record), "line_ordinal": line_ordinal}
        for line_ordinal, record in enumerate(ordered)
    ]


def _render_image(render_png_bytes: bytes) -> Image.Image:
    if type(render_png_bytes) is not bytes or not render_png_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        raise _error("page render must be exact PNG bytes")
    try:
        with Image.open(io.BytesIO(render_png_bytes)) as raw:
            raw.load()
            image = raw.convert("RGB")
    except OSError as exc:
        raise _error("page render PNG cannot be decoded") from exc
    if image.width <= 0 or image.height <= 0:
        raise _error("page render has invalid dimensions")
    return image


def _crop_png(image: Image.Image, bbox: Sequence[int]) -> tuple[bytes, list[int]]:
    left, top, right, bottom = bbox
    pad_left, pad_top, pad_right, pad_bottom = SOURCE_PADDING
    padded = [
        max(0, left - pad_left),
        max(0, top - pad_top),
        min(image.width, right + pad_right),
        min(image.height, bottom + pad_bottom),
    ]
    crop = image.crop(tuple(padded)).convert("RGB")
    crop = ImageOps.expand(crop, border=WHITE_BORDER, fill=(255, 255, 255))
    stream = io.BytesIO()
    crop.save(stream, format="PNG", optimize=False, compress_level=9)
    return stream.getvalue(), padded


def _validate_page(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _PAGE_FIELDS:
        raise _error("semantic label page freeze fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["authority"], _SAFETY)
        or type(value["physical_page"]) is not int
        or value["physical_page"] <= 0
    ):
        raise _error("semantic label page freeze identity drifted")
    material = canonical_clone_v1(value)
    page_id = material.pop("page_id")
    if page_id != "ffslfv1:page:" + canonical_json_sha256_v1(material):
        raise _error("semantic label page freeze hash identity drifted")
    if type(value["crops"]) is not list or type(value["detector_line_axis"]) is not list:
        raise _error("semantic label page freeze axes drifted")
    if len(value["crops"]) != len(value["detector_line_axis"]):
        raise _error("semantic label crop and detector axes differ")
    return canonical_clone_v1(value)


def build_family_first_semantic_label_page_freeze_v1(
    *,
    render_png_bytes: bytes,
    detector_payload: Any,
    physical_page: int,
    crop_path_prefix: str,
) -> tuple[dict[str, Any], tuple[bytes, ...]]:
    """Build one text-blind page record and its ordered immutable crop bytes."""

    page = _positive_int(physical_page, "physical page")
    if (
        type(crop_path_prefix) is not str
        or not crop_path_prefix
        or crop_path_prefix.startswith("/")
    ):
        raise _error("crop path prefix must be one non-empty project-relative string")
    if ".." in crop_path_prefix.split("/"):
        raise _error("crop path prefix escapes its artifact root")
    image = _render_image(render_png_bytes)
    axis = project_ordered_detector_line_axis_v1(
        detector_payload,
        pixel_width=image.width,
        pixel_height=image.height,
    )
    crop_bytes: list[bytes] = []
    crop_records: list[dict[str, Any]] = []
    for line in axis:
        payload, padded = _crop_png(image, line["raw_pixel_bbox"])
        crop_bytes.append(payload)
        crop_records.append(
            {
                "crop_ref": {
                    "path": f"{crop_path_prefix}/line-{line['line_ordinal']:04d}.png",
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size_bytes": len(payload),
                },
                "line_ordinal": line["line_ordinal"],
                "padded_source_bbox_raw_pixels": padded,
                "source_bbox_raw_pixels": line["raw_pixel_bbox"],
            }
        )
    material = {
        "authority": canonical_clone_v1(_SAFETY),
        "claim_boundary": CLAIM_BOUNDARY,
        "crops": crop_records,
        "detector_line_axis": axis,
        "format_version": FORMAT_VERSION,
        "metrics": {
            "crop_count": len(crop_records),
            "detected_line_count": len(axis),
            "excluded_detected_line_count": 0,
        },
        "physical_page": page,
        "render_ref": {
            "pixel_height": image.height,
            "pixel_width": image.width,
            "sha256": hashlib.sha256(render_png_bytes).hexdigest(),
            "size_bytes": len(render_png_bytes),
        },
    }
    record = _validate_page(
        {**material, "page_id": "ffslfv1:page:" + canonical_json_sha256_v1(material)}
    )
    return record, tuple(crop_bytes)


def validate_family_first_semantic_label_page_freeze_replay_v1(
    value: Any,
    crop_bytes: Any,
    *,
    render_png_bytes: bytes,
    detector_payload: Any,
    physical_page: int,
    crop_path_prefix: str,
) -> dict[str, Any]:
    """Exact-rebuild page geometry/crops and compare every supplied crop byte."""

    persisted = _validate_page(value)
    if type(crop_bytes) is not tuple or any(type(item) is not bytes for item in crop_bytes):
        raise _error("semantic label replay crops must be one exact bytes tuple")
    expected, expected_crops = build_family_first_semantic_label_page_freeze_v1(
        render_png_bytes=render_png_bytes,
        detector_payload=detector_payload,
        physical_page=physical_page,
        crop_path_prefix=crop_path_prefix,
    )
    if not same_typed_json_v1(persisted, expected) or crop_bytes != expected_crops:
        raise _error("semantic label page freeze does not replay exactly")
    return persisted
