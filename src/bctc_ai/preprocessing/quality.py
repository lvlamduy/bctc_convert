from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np


@dataclass(frozen=True)
class QualityThresholds:
    blur_variance_minimum: float = 85.0
    foreground_contrast_minimum: float = 65.0
    background_nonuniformity_maximum: float = 10.0
    noise_residual_maximum: float = 13.0
    skew_degrees_minimum: float = 0.6
    compression_blockiness_maximum: float = 1.8


@dataclass(frozen=True)
class DifficultRegion:
    x0: int
    y0: int
    x1: int
    y1: int
    reason: str
    brightness_mean: float
    foreground_contrast: float
    dark_pixel_ratio: float
    saturated_pixel_ratio: float


@dataclass(frozen=True)
class ImageQuality:
    width: int
    height: int
    blur_variance: float
    contrast_std: float
    foreground_contrast: float
    brightness_mean: float
    background_nonuniformity: float
    noise_residual: float
    compression_blockiness: float
    estimated_skew_degrees: float
    perspective_distortion_score: float | None
    perspective_corners: list[list[float]] | None
    perspective_confidence: float | None
    classifications: list[str]
    difficult_regions: list[DifficultRegion]
    unmeasured: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _estimate_skew(gray: np.ndarray) -> float:
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    minimum_length = max(40, gray.shape[1] // 6)
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 1800,
        threshold=max(40, gray.shape[1] // 20),
        minLineLength=minimum_length,
        maxLineGap=20,
    )
    if lines is None:
        return 0.0
    angles: list[float] = []
    for x0, y0, x1, y1 in lines[:, 0]:
        angle = float(np.degrees(np.arctan2(y1 - y0, x1 - x0)))
        if -15.0 <= angle <= 15.0:
            angles.append(angle)
    return float(np.median(angles)) if angles else 0.0


def _background_nonuniformity(gray: np.ndarray) -> float:
    # Estimate each tile's paper/background level from its lightest quartile;
    # this avoids mistaking sparse black text for uneven illumination.
    height, width = gray.shape
    levels: list[float] = []
    for y in range(0, height, max(1, height // 8)):
        for x in range(0, width, max(1, width // 8)):
            tile = gray[
                y : min(height, y + max(1, height // 8)), x : min(width, x + max(1, width // 8))
            ]
            if tile.size:
                levels.append(float(np.percentile(tile, 75)))
    return float(np.std(levels)) if levels else 0.0


def _compression_blockiness(gray: np.ndarray) -> float:
    values = gray.astype(np.float32)
    vertical = np.abs(values[:, 1:] - values[:, :-1])
    horizontal = np.abs(values[1:, :] - values[:-1, :])
    boundary_values = []
    interior_values = []
    if vertical.shape[1] >= 9:
        boundary_values.append(vertical[:, 7::8].mean())
        interior_values.append(np.delete(vertical, np.s_[7::8], axis=1).mean())
    if horizontal.shape[0] >= 9:
        boundary_values.append(horizontal[7::8, :].mean())
        interior_values.append(np.delete(horizontal, np.s_[7::8], axis=0).mean())
    boundary = float(np.mean(boundary_values)) if boundary_values else 0.0
    interior = float(np.mean(interior_values)) if interior_values else 0.0
    return boundary / max(interior, 1e-6)


def _difficult_regions(image: np.ndarray, gray: np.ndarray) -> list[DifficultRegion]:
    height, width = gray.shape
    tile_height = max(64, height // 12)
    tile_width = max(96, width // 6)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV) if image.ndim == 3 else None
    regions: list[DifficultRegion] = []
    for y0 in range(0, height, tile_height):
        for x0 in range(0, width, tile_width):
            y1, x1 = min(height, y0 + tile_height), min(width, x0 + tile_width)
            tile = gray[y0:y1, x0:x1]
            if tile.size < 1024:
                continue
            brightness = float(tile.mean())
            contrast = float(np.percentile(tile, 99) - np.percentile(tile, 1))
            dark_ratio = float(np.mean(tile < 150))
            saturated_ratio = (
                float(np.mean((hsv[y0:y1, x0:x1, 1] > 45) & (hsv[y0:y1, x0:x1, 2] < 215)))
                if hsv is not None
                else 0.0
            )
            reason = None
            if dark_ratio >= 0.55 and contrast >= 20:
                reason = "DARK_HEADER_OR_REVERSED_TEXT"
            elif saturated_ratio >= 0.40 and contrast < 80:
                reason = "DARK_COLORED_LOW_CONTRAST_HEADER"
            if reason:
                regions.append(
                    DifficultRegion(
                        x0=x0,
                        y0=y0,
                        x1=x1,
                        y1=y1,
                        reason=reason,
                        brightness_mean=round(brightness, 6),
                        foreground_contrast=round(contrast, 6),
                        dark_pixel_ratio=round(dark_ratio, 6),
                        saturated_pixel_ratio=round(saturated_ratio, 6),
                    )
                )
    return regions[:32]


def _order_quad(points: np.ndarray) -> np.ndarray:
    points = points.reshape(4, 2).astype(np.float32)
    ordered = np.zeros((4, 2), dtype=np.float32)
    sums = points.sum(axis=1)
    differences = np.diff(points, axis=1).reshape(-1)
    ordered[0] = points[np.argmin(sums)]  # top left
    ordered[2] = points[np.argmax(sums)]  # bottom right
    ordered[1] = points[np.argmin(differences)]  # top right
    ordered[3] = points[np.argmax(differences)]  # bottom left
    return ordered


def _perspective_estimate(
    gray: np.ndarray,
) -> tuple[float | None, list[list[float]] | None, float | None]:
    height, width = gray.shape
    reduced = gray
    scale = 1.0
    maximum_dimension = max(height, width)
    if maximum_dimension > 1800:
        scale = 1800.0 / maximum_dimension
        reduced = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    blurred = cv2.GaussianBlur(reduced, (5, 5), 0)
    edges = cv2.Canny(blurred, 40, 120)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    image_area = float(reduced.shape[0] * reduced.shape[1])
    candidates: list[tuple[float, np.ndarray]] = []
    for contour in contours:
        perimeter = cv2.arcLength(contour, True)
        approximation = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        area = float(abs(cv2.contourArea(approximation)))
        if (
            len(approximation) == 4
            and cv2.isContourConvex(approximation)
            and area >= 0.45 * image_area
        ):
            candidates.append((area, approximation))
    if not candidates:
        return None, None, None
    area, contour = max(candidates, key=lambda item: item[0])
    corners = _order_quad(contour) / scale
    ideal = np.array(
        [[0.0, 0.0], [width - 1.0, 0.0], [width - 1.0, height - 1.0], [0.0, height - 1.0]],
        dtype=np.float32,
    )
    diagonal = float(np.hypot(width, height))
    distortion = float(np.mean(np.linalg.norm(corners - ideal, axis=1)) / max(diagonal, 1.0))
    confidence = min(1.0, area / image_area)
    return distortion, corners.tolist(), confidence


def assess_array(image: np.ndarray, thresholds: QualityThresholds | None = None) -> ImageQuality:
    thresholds = thresholds or QualityThresholds()
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    elif image.ndim == 2:
        gray = image
    else:
        raise ValueError("expected a grayscale or BGR image")
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    contrast = float(gray.std())
    foreground_contrast = float(np.percentile(gray, 99) - np.percentile(gray, 1))
    brightness = float(gray.mean())
    background_nonuniformity = _background_nonuniformity(gray)
    residual = gray.astype(np.float32) - cv2.GaussianBlur(gray, (3, 3), 0).astype(np.float32)
    noise = float(np.median(np.abs(residual - np.median(residual))) * 1.4826)
    compression = _compression_blockiness(gray)
    difficult_regions = _difficult_regions(image, gray)
    perspective_score, perspective_corners, perspective_confidence = _perspective_estimate(gray)
    skew = _estimate_skew(gray)
    classes: list[str] = []
    if blur < thresholds.blur_variance_minimum:
        classes.append("BLURRY")
    if foreground_contrast < thresholds.foreground_contrast_minimum:
        classes.append("LOW_CONTRAST")
    if background_nonuniformity > thresholds.background_nonuniformity_maximum:
        classes.append("UNEVEN_BACKGROUND")
    if noise > thresholds.noise_residual_maximum:
        classes.append("NOISY")
    if abs(skew) >= thresholds.skew_degrees_minimum:
        classes.append("SKEWED")
    if compression > thresholds.compression_blockiness_maximum:
        classes.append("COMPRESSED")
    if perspective_score is not None and perspective_score >= 0.015:
        classes.append("PERSPECTIVE_DISTORTED")
    if not classes:
        classes = ["CLEAN"]
    elif len(classes) > 1:
        classes.append("MIXED")
    return ImageQuality(
        width=int(gray.shape[1]),
        height=int(gray.shape[0]),
        blur_variance=round(blur, 6),
        contrast_std=round(contrast, 6),
        foreground_contrast=round(foreground_contrast, 6),
        brightness_mean=round(brightness, 6),
        background_nonuniformity=round(background_nonuniformity, 6),
        noise_residual=round(noise, 6),
        compression_blockiness=round(compression, 6),
        estimated_skew_degrees=round(skew, 6),
        perspective_distortion_score=round(perspective_score, 6)
        if perspective_score is not None
        else None,
        perspective_corners=perspective_corners,
        perspective_confidence=round(perspective_confidence, 6)
        if perspective_confidence is not None
        else None,
        classifications=classes,
        difficult_regions=difficult_regions,
        unmeasured=(["PERSPECTIVE_BORDER_NOT_DETECTED"] if perspective_corners is None else [])
        + ["CROPPING_DAMAGE", "TEXT_SIZE"],
    )


def assess_image(path: Path, thresholds: QualityThresholds | None = None) -> ImageQuality:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"cannot decode image: {path}")
    return assess_array(image, thresholds)
