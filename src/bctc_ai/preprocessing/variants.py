from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from bctc_ai.core.atomic import atomic_write_bytes, atomic_write_json
from bctc_ai.preprocessing.quality import DifficultRegion, ImageQuality, assess_array


@dataclass(frozen=True)
class VariantRecord:
    name: str
    path: str
    sha256: str
    transform_to_render: list[list[float]]
    quality: dict[str, Any]
    selection_status: str = "PENDING_OCR_EVIDENCE"


@dataclass(frozen=True)
class RegionVariantRecord:
    region_index: int
    reason: str
    bbox_in_render: list[int]
    name: str
    path: str
    sha256: str
    transform_to_render: list[list[float]]
    selection_status: str = "PENDING_REGION_OCR_EVIDENCE"


def _png_bytes(image: np.ndarray) -> bytes:
    success, encoded = cv2.imencode(".png", image)
    if not success:
        raise ValueError("OpenCV failed to encode preprocessing variant")
    return encoded.tobytes()


def _deskew(gray: np.ndarray, angle: float) -> tuple[np.ndarray, list[list[float]]]:
    height, width = gray.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2.0, height / 2.0), angle, 1.0)
    result = cv2.warpAffine(
        gray,
        matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    inverse = cv2.invertAffineTransform(matrix)
    transform = [inverse[0].tolist(), inverse[1].tolist(), [0.0, 0.0, 1.0]]
    return result, transform


def _perspective_correct(
    gray: np.ndarray, corners: list[list[float]]
) -> tuple[np.ndarray, list[list[float]]]:
    source = np.array(corners, dtype=np.float32)
    top_width = np.linalg.norm(source[1] - source[0])
    bottom_width = np.linalg.norm(source[2] - source[3])
    left_height = np.linalg.norm(source[3] - source[0])
    right_height = np.linalg.norm(source[2] - source[1])
    width = max(1, int(round(max(top_width, bottom_width))))
    height = max(1, int(round(max(left_height, right_height))))
    target = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float32,
    )
    to_corrected = cv2.getPerspectiveTransform(source, target)
    corrected = cv2.warpPerspective(
        gray,
        to_corrected,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    to_render = np.linalg.inv(to_corrected)
    return corrected, to_render.tolist()


def generate_variants(
    render_path: Path, output_directory: Path, quality: ImageQuality
) -> list[VariantRecord]:
    image = cv2.imread(str(render_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"cannot decode render: {render_path}")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    identity = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    proposals: list[tuple[str, np.ndarray, list[list[float]]]] = [("grayscale", gray, identity)]
    classes = set(quality.classifications)
    if "LOW_CONTRAST" in classes or "UNEVEN_BACKGROUND" in classes:
        normalized = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
        proposals.append(("contrast-normalized", normalized, identity))
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
        proposals.append(("clahe", clahe, identity))
        adaptive = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 41, 15
        )
        proposals.append(("adaptive-threshold", adaptive, identity))
    if "NOISY" in classes or "COMPRESSED" in classes:
        proposals.append(("denoised", cv2.fastNlMeansDenoising(gray, None, 7, 7, 21), identity))
    if "BLURRY" in classes:
        blurred = cv2.GaussianBlur(gray, (0, 0), 1.0)
        proposals.append(("unsharp-light", cv2.addWeighted(gray, 1.5, blurred, -0.5, 0), identity))
    if "SKEWED" in classes:
        deskewed, transform = _deskew(gray, quality.estimated_skew_degrees)
        proposals.append(("deskewed", deskewed, transform))
    if "PERSPECTIVE_DISTORTED" in classes and quality.perspective_corners:
        corrected, transform = _perspective_correct(gray, quality.perspective_corners)
        proposals.append(("perspective-corrected", corrected, transform))

    output_directory.mkdir(parents=True, exist_ok=True)
    records: list[VariantRecord] = []
    seen_hashes: set[str] = set()
    for name, proposal, transform in proposals:
        payload = _png_bytes(proposal)
        path = output_directory / f"{name}.png"
        digest = atomic_write_bytes(path, payload)
        if digest in seen_hashes:
            path.unlink(missing_ok=True)
            continue
        seen_hashes.add(digest)
        records.append(
            VariantRecord(
                name=name,
                path=path.as_posix(),
                sha256=digest,
                transform_to_render=transform,
                quality=assess_array(proposal).to_dict(),
            )
        )
    atomic_write_json(
        output_directory / "manifest.json",
        {
            "format_version": 1,
            "source_render": render_path.as_posix(),
            "source_quality": quality.to_dict(),
            "selection_status": "PENDING_OCR_EVIDENCE",
            "variants": [asdict(record) for record in records],
        },
    )
    return records


def _region_proposals(crop: np.ndarray, region: DifficultRegion) -> list[tuple[str, np.ndarray]]:
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
    proposals = [("grayscale", gray)]
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(gray)
    proposals.append(("clahe", clahe))
    gamma = 0.55 if region.brightness_mean < 130 else 0.75
    lookup = np.array([((value / 255.0) ** gamma) * 255 for value in range(256)]).astype("uint8")
    proposals.append(("gamma-lightened", cv2.LUT(gray, lookup)))
    if region.reason == "DARK_HEADER_OR_REVERSED_TEXT":
        proposals.append(("inverted", cv2.bitwise_not(gray)))
    return proposals


def generate_difficult_region_variants(
    render_path: Path,
    output_directory: Path,
    regions: list[DifficultRegion],
) -> list[RegionVariantRecord]:
    image = cv2.imread(str(render_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"cannot decode render: {render_path}")
    output_directory.mkdir(parents=True, exist_ok=True)
    records: list[RegionVariantRecord] = []
    for index, region in enumerate(regions, start=1):
        crop = image[region.y0 : region.y1, region.x0 : region.x1]
        transform = [
            [1.0, 0.0, float(region.x0)],
            [0.0, 1.0, float(region.y0)],
            [0.0, 0.0, 1.0],
        ]
        seen: set[str] = set()
        for name, proposal in _region_proposals(crop, region):
            path = output_directory / f"region-{index:03d}-{name}.png"
            digest = atomic_write_bytes(path, _png_bytes(proposal))
            if digest in seen:
                path.unlink(missing_ok=True)
                continue
            seen.add(digest)
            records.append(
                RegionVariantRecord(
                    region_index=index,
                    reason=region.reason,
                    bbox_in_render=[region.x0, region.y0, region.x1, region.y1],
                    name=name,
                    path=path.as_posix(),
                    sha256=digest,
                    transform_to_render=transform,
                )
            )
    atomic_write_json(
        output_directory / "manifest.json",
        {
            "format_version": 1,
            "source_render": render_path.as_posix(),
            "selection_status": "PENDING_REGION_OCR_EVIDENCE",
            "variants": [asdict(record) for record in records],
        },
    )
    return records
