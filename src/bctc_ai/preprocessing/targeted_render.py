from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import cv2
import fitz
import numpy as np

from bctc_ai.core.atomic import atomic_write_bytes, atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.preprocessing.quality import assess_array
from bctc_ai.preprocessing.targeted_reread import TargetedRereadError


def _png_bytes(image: np.ndarray) -> bytes:
    success, encoded = cv2.imencode(".png", image)
    if not success:
        raise TargetedRereadError("OpenCV failed to encode targeted-reread variant")
    return encoded.tobytes()


_IDENTITY = np.eye(3, dtype=np.float64)


def _deskew_variant(gray: np.ndarray, angle: float) -> tuple[np.ndarray, np.ndarray]:
    height, width = gray.shape
    to_variant = cv2.getRotationMatrix2D((width / 2.0, height / 2.0), angle, 1.0)
    result = cv2.warpAffine(
        gray,
        to_variant,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    inverse = cv2.invertAffineTransform(to_variant)
    transform = np.vstack([inverse, [0.0, 0.0, 1.0]]).astype(np.float64)
    return result, transform


def _perspective_variant(
    gray: np.ndarray, corners: list[list[float]]
) -> tuple[np.ndarray, np.ndarray]:
    source = np.asarray(corners, dtype=np.float32)
    if source.shape != (4, 2) or not np.all(np.isfinite(source)):
        raise TargetedRereadError("perspective candidate has invalid corners")
    top_width = np.linalg.norm(source[1] - source[0])
    bottom_width = np.linalg.norm(source[2] - source[3])
    left_height = np.linalg.norm(source[3] - source[0])
    right_height = np.linalg.norm(source[2] - source[1])
    width = max(1, int(round(max(top_width, bottom_width))))
    height = max(1, int(round(max(left_height, right_height))))
    target = np.asarray(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float32,
    )
    to_variant = cv2.getPerspectiveTransform(source, target)
    if abs(float(np.linalg.det(to_variant))) < 1e-12:
        raise TargetedRereadError("perspective candidate transform is singular")
    result = cv2.warpPerspective(
        gray,
        to_variant,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return result, np.linalg.inv(to_variant)


def _dark_region_variants(
    gray: np.ndarray, difficult_regions: list[Any]
) -> list[tuple[str, np.ndarray, np.ndarray, str]]:
    if not difficult_regions:
        return []
    clahe_image = gray.copy()
    gamma_image = gray.copy()
    inverted_image = gray.copy()
    has_reversed = False
    lookup = np.asarray([((value / 255.0) ** 0.60) * 255 for value in range(256)], dtype=np.uint8)
    for region in difficult_regions:
        y0, y1 = int(region.y0), int(region.y1)
        x0, x1 = int(region.x0), int(region.x1)
        crop = gray[y0:y1, x0:x1]
        if not crop.size:
            continue
        clahe_image[y0:y1, x0:x1] = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(crop)
        gamma_image[y0:y1, x0:x1] = cv2.LUT(crop, lookup)
        if region.reason == "DARK_HEADER_OR_REVERSED_TEXT":
            inverted_image[y0:y1, x0:x1] = cv2.bitwise_not(crop)
            has_reversed = True
    proposals = [
        ("dark-region-clahe", clahe_image, _IDENTITY.copy(), "PHOTOMETRIC"),
        ("dark-region-gamma", gamma_image, _IDENTITY.copy(), "PHOTOMETRIC"),
    ]
    if has_reversed:
        proposals.append(("dark-region-inverted", inverted_image, _IDENTITY.copy(), "PHOTOMETRIC"))
    return proposals


def _quality_gated_variants(
    image: np.ndarray, quality: Any
) -> list[tuple[str, np.ndarray, np.ndarray, str]]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    variants: list[tuple[str, np.ndarray, np.ndarray, str]] = [
        ("grayscale", gray, _IDENTITY.copy(), "PHOTOMETRIC")
    ]
    classifications = set(quality.classifications)
    if classifications & {"LOW_CONTRAST", "UNEVEN_BACKGROUND"}:
        variants.extend(
            [
                (
                    "contrast-normalized",
                    cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX),
                    _IDENTITY.copy(),
                    "PHOTOMETRIC",
                ),
                (
                    "clahe",
                    cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray),
                    _IDENTITY.copy(),
                    "PHOTOMETRIC",
                ),
                (
                    "adaptive-threshold",
                    cv2.adaptiveThreshold(
                        gray,
                        255,
                        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                        cv2.THRESH_BINARY,
                        41,
                        15,
                    ),
                    _IDENTITY.copy(),
                    "PHOTOMETRIC",
                ),
            ]
        )
    if classifications & {"NOISY", "COMPRESSED"}:
        variants.append(
            (
                "denoised",
                cv2.fastNlMeansDenoising(gray, None, 7, 7, 21),
                _IDENTITY.copy(),
                "PHOTOMETRIC",
            )
        )
    if "BLURRY" in classifications:
        blurred = cv2.GaussianBlur(gray, (0, 0), 1.0)
        variants.append(
            (
                "unsharp-light",
                cv2.addWeighted(gray, 1.5, blurred, -0.5, 0),
                _IDENTITY.copy(),
                "PHOTOMETRIC",
            )
        )
    if "SKEWED" in classifications:
        deskewed, transform = _deskew_variant(gray, quality.estimated_skew_degrees)
        variants.append(("deskewed", deskewed, transform, "GEOMETRIC_DESKEW"))
    if "PERSPECTIVE_DISTORTED" in classifications and quality.perspective_corners:
        corrected, transform = _perspective_variant(gray, quality.perspective_corners)
        variants.append(("perspective-corrected", corrected, transform, "GEOMETRIC_PERSPECTIVE"))
    variants.extend(_dark_region_variants(gray, quality.difficult_regions))
    return variants


def _matrix_record(matrix: np.ndarray) -> list[list[float]]:
    return [[round(float(value), 12) for value in row] for row in matrix.tolist()]


def _validate_region(region: dict[str, Any]) -> tuple[float, float, float, float]:
    normalized = region.get("bbox_normalized")
    if (
        not isinstance(normalized, (list, tuple))
        or len(normalized) != 4
        or any(
            not isinstance(value, (int, float)) or isinstance(value, bool) for value in normalized
        )
    ):
        raise TargetedRereadError("reread region lacks a normalized bbox")
    x0, y0, x1, y1 = (float(value) for value in normalized)
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        raise TargetedRereadError("normalized reread bbox falls outside the page")
    dpi = region.get("target_dpi")
    if not isinstance(dpi, int) or not 300 <= dpi <= 600:
        raise TargetedRereadError("targeted reread DPI must be in [300, 600]")
    if (
        region.get("automatic_value_replacement") is not False
        or region.get("automatic_confidence_promotion") is not False
    ):
        raise TargetedRereadError("reread region violates fail-closed replacement policy")
    return x0, y0, x1, y1


def _directory_fsync(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def render_targeted_reread_page(
    source_pdf: Path,
    page_plan: dict[str, Any],
    output_directory: Path,
    *,
    expected_source_sha256: str,
    source_identity_path: str,
) -> dict[str, Any]:
    """Rerender planned page regions from the PDF, never by resizing a baseline PNG."""

    source_pdf = source_pdf.resolve()
    output_directory = output_directory.resolve()
    if not source_pdf.is_file():
        raise FileNotFoundError(source_pdf)
    if output_directory.exists():
        raise FileExistsError(f"refusing to overwrite reread page directory: {output_directory}")
    if sha256_file(source_pdf) != expected_source_sha256:
        raise TargetedRereadError("source PDF hash drift before targeted rerender")
    if page_plan.get("status") not in {
        "PLANNED",
        "PLANNED_WITH_UNSUPPORTED_ESCALATIONS",
    }:
        raise TargetedRereadError("only a planned page can be rerendered")
    raw_regions = page_plan.get("regions")
    page_number = page_plan.get("page")
    if (
        not isinstance(raw_regions, list)
        or not raw_regions
        or not isinstance(page_number, int)
        or page_number < 1
    ):
        raise TargetedRereadError("page plan has no renderable regions")
    safety = page_plan.get("safety")
    if not isinstance(safety, dict) or any(
        safety.get(name) is not expected
        for name, expected in {
            "preserve_original": True,
            "arithmetic_selects_variant": False,
            "history_selects_variant": False,
            "schema_selects_variant": False,
            "automatic_value_replacement": False,
            "automatic_confidence_promotion": False,
            "cross_page_region": False,
        }.items()
    ):
        raise TargetedRereadError("page plan safety contract is absent or drifted")

    output_directory.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{output_directory.name}.", dir=output_directory.parent)
    )
    try:
        with fitz.open(source_pdf) as document:
            if document.needs_pass:
                raise TargetedRereadError("password-protected source cannot be rerendered")
            if page_number > document.page_count:
                raise TargetedRereadError("planned page exceeds source PDF page count")
            page = document[page_number - 1]
            page_width = float(page.rect.width)
            page_height = float(page.rect.height)
            region_records = []
            seen_ids: set[str] = set()
            for raw_region in raw_regions:
                if not isinstance(raw_region, dict):
                    raise TargetedRereadError("reread region is not an object")
                region_id = raw_region.get("region_id")
                if not isinstance(region_id, str) or not region_id or region_id in seen_ids:
                    raise TargetedRereadError("reread region IDs are missing or duplicated")
                seen_ids.add(region_id)
                x0, y0, x1, y1 = _validate_region(raw_region)
                clip = fitz.Rect(
                    x0 * page_width,
                    y0 * page_height,
                    x1 * page_width,
                    y1 * page_height,
                )
                dpi = int(raw_region["target_dpi"])
                scale = dpi / 72.0
                pixmap = page.get_pixmap(
                    matrix=fitz.Matrix(scale, scale),
                    colorspace=fitz.csRGB,
                    alpha=False,
                    clip=clip,
                )
                original_payload = pixmap.tobytes("png")
                decoded = cv2.imdecode(
                    np.frombuffer(original_payload, dtype=np.uint8), cv2.IMREAD_COLOR
                )
                if decoded is None:
                    raise TargetedRereadError("cannot decode targeted PDF render")
                quality = assess_array(decoded)
                region_directory = temporary / region_id
                region_directory.mkdir(parents=True)
                original_path = region_directory / "original.png"
                original_hash = atomic_write_bytes(original_path, original_payload)
                variant_records = [
                    {
                        "name": "original",
                        "path": f"{region_id}/original.png",
                        "sha256": original_hash,
                        "geometry_transform_kind": "IDENTITY",
                        "transform_to_original_region_pixels": _matrix_record(_IDENTITY),
                        "selection_status": "PENDING_OCR_EVIDENCE",
                    }
                ]
                seen_hashes = {original_hash}
                for name, variant, transform, transform_kind in _quality_gated_variants(
                    decoded, quality
                ):
                    payload = _png_bytes(variant)
                    candidate_path = region_directory / f"{name}.png"
                    digest = atomic_write_bytes(candidate_path, payload)
                    if digest in seen_hashes:
                        candidate_path.unlink()
                        continue
                    seen_hashes.add(digest)
                    variant_records.append(
                        {
                            "name": name,
                            "path": f"{region_id}/{name}.png",
                            "sha256": digest,
                            "geometry_transform_kind": transform_kind,
                            "transform_to_original_region_pixels": _matrix_record(transform),
                            "selection_status": "PENDING_OCR_EVIDENCE",
                        }
                    )
                pixel_to_pdf = [
                    [(clip.x1 - clip.x0) / pixmap.width, 0.0, clip.x0],
                    [0.0, (clip.y1 - clip.y0) / pixmap.height, clip.y0],
                    [0.0, 0.0, 1.0],
                ]
                baseline = page_plan.get("baseline_render", {})
                baseline_width = baseline.get("width_pixels")
                baseline_height = baseline.get("height_pixels")
                if (
                    not isinstance(baseline_width, int)
                    or baseline_width < 1
                    or not isinstance(baseline_height, int)
                    or baseline_height < 1
                ):
                    raise TargetedRereadError("page plan lacks baseline render dimensions")
                pixel_to_baseline = [
                    [
                        (x1 - x0) * baseline_width / pixmap.width,
                        0.0,
                        x0 * baseline_width,
                    ],
                    [
                        0.0,
                        (y1 - y0) * baseline_height / pixmap.height,
                        y0 * baseline_height,
                    ],
                    [0.0, 0.0, 1.0],
                ]
                pixel_to_pdf_matrix = np.asarray(pixel_to_pdf, dtype=np.float64)
                pixel_to_baseline_matrix = np.asarray(pixel_to_baseline, dtype=np.float64)
                for variant in variant_records:
                    transform = np.asarray(
                        variant["transform_to_original_region_pixels"], dtype=np.float64
                    )
                    variant["pixel_to_pdf_points"] = _matrix_record(pixel_to_pdf_matrix @ transform)
                    variant["pixel_to_baseline_render"] = _matrix_record(
                        pixel_to_baseline_matrix @ transform
                    )
                region_records.append(
                    {
                        "plan": raw_region,
                        "source_page_bbox_points": [clip.x0, clip.y0, clip.x1, clip.y1],
                        "render": {
                            "dpi": dpi,
                            "width_pixels": pixmap.width,
                            "height_pixels": pixmap.height,
                            "pixel_to_pdf_points": pixel_to_pdf,
                            "pixel_to_baseline_render": pixel_to_baseline,
                            "quality": quality.to_dict(),
                        },
                        "variants": variant_records,
                        "selection_status": "PENDING_OCR_EVIDENCE",
                        "variant_selection_basis": "UNDECIDED_REQUIRES_OCR_EVIDENCE",
                        "automatic_value_replacement": False,
                        "automatic_confidence_promotion": False,
                    }
                )
        manifest = {
            "format_version": 1,
            "state": "TARGETED_REREAD_INPUTS_RENDERED",
            "source": {
                "path": source_identity_path,
                "sha256": expected_source_sha256,
                "size_bytes": source_pdf.stat().st_size,
            },
            "page": page_number,
            "statement_type": page_plan.get("statement_type"),
            "source_page_size_points": [page_width, page_height],
            "regions": region_records,
            "selection_status": "PENDING_OCR_EVIDENCE",
            "safety": safety,
        }
        atomic_write_json(temporary / "manifest.json", manifest)
        os.replace(temporary, output_directory)
        _directory_fsync(output_directory.parent)
        return manifest
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
