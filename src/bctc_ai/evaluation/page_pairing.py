from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path

import cv2
import fitz
import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class PagePairingConfig:
    render_scale: float = 0.75
    feature_width: int = 48
    feature_height: int = 64
    row_projection_size: int = 128
    column_projection_size: int = 96
    content_crop_quantile: float = 0.005
    skip_penalty: float = 0.12
    minimum_similarity: float = 0.45
    minimum_runner_up_margin: float = 0.05
    minimum_ink_ratio: float = 0.002

    def validate(self) -> None:
        if self.render_scale <= 0:
            raise ValueError("render_scale must be positive")
        if min(
            self.feature_width,
            self.feature_height,
            self.row_projection_size,
            self.column_projection_size,
        ) < 8:
            raise ValueError("fingerprint dimensions must be at least 8")
        if not 0 <= self.content_crop_quantile < 0.1:
            raise ValueError("content_crop_quantile must be in [0, 0.1)")
        if self.skip_penalty <= 0:
            raise ValueError("skip_penalty must be positive")
        if not -1 <= self.minimum_similarity <= 1:
            raise ValueError("minimum_similarity must be in [-1, 1]")
        if self.minimum_runner_up_margin < 0:
            raise ValueError("minimum_runner_up_margin cannot be negative")
        if not 0 <= self.minimum_ink_ratio <= 1:
            raise ValueError("minimum_ink_ratio must be in [0, 1]")


class PagePairAction(StrEnum):
    MATCH = "MATCH"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    CANDIDATE_ONLY = "CANDIDATE_ONLY"


@dataclass(frozen=True)
class PageFingerprint:
    page: int
    raster_width: int
    raster_height: int
    content_bbox: tuple[int, int, int, int]
    ink_ratio: float
    feature: NDArray[np.float32]


@dataclass(frozen=True)
class PagePairStep:
    action: PagePairAction
    reference_page: int | None
    candidate_page: int | None
    similarity: float | None
    runner_up_margin: float | None
    sequence_supported: bool
    accepted: bool
    evidence: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["action"] = self.action.value
        return value


@dataclass(frozen=True)
class PagePairAlignment:
    reference_page_count: int
    candidate_page_count: int
    steps: tuple[PagePairStep, ...]

    @property
    def matched(self) -> tuple[PagePairStep, ...]:
        return tuple(step for step in self.steps if step.action is PagePairAction.MATCH)

    @property
    def accepted(self) -> tuple[PagePairStep, ...]:
        return tuple(step for step in self.matched if step.accepted)

    def to_dict(self) -> dict[str, object]:
        similarities = [step.similarity for step in self.matched if step.similarity is not None]
        return {
            "reference_page_count": self.reference_page_count,
            "candidate_page_count": self.candidate_page_count,
            "counts": {
                "steps": len(self.steps),
                "matched": len(self.matched),
                "accepted": len(self.accepted),
                "reference_only": sum(
                    step.action is PagePairAction.REFERENCE_ONLY for step in self.steps
                ),
                "candidate_only": sum(
                    step.action is PagePairAction.CANDIDATE_ONLY for step in self.steps
                ),
            },
            "mean_matched_similarity": (
                round(float(np.mean(similarities)), 6) if similarities else None
            ),
            "steps": [step.to_dict() for step in self.steps],
        }


def pairing_config_from_dict(value: dict[str, object]) -> PagePairingConfig:
    allowed = set(PagePairingConfig.__dataclass_fields__)
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"unknown page-pairing config fields: {sorted(unknown)}")
    config = PagePairingConfig(**value)
    config.validate()
    return config


def _grayscale(image: NDArray[np.uint8]) -> NDArray[np.uint8]:
    if image.ndim == 2:
        return image
    if image.ndim == 3 and image.shape[2] in {3, 4}:
        conversion = cv2.COLOR_BGRA2GRAY if image.shape[2] == 4 else cv2.COLOR_BGR2GRAY
        return cv2.cvtColor(image, conversion)
    raise ValueError("expected a grayscale, BGR, or BGRA page image")


def fingerprint_page_image(
    image: NDArray[np.uint8],
    *,
    page: int,
    config: PagePairingConfig | None = None,
) -> PageFingerprint:
    config = config or PagePairingConfig()
    config.validate()
    if page < 1:
        raise ValueError("page numbers are one-based")
    gray = _grayscale(image)
    _threshold, ink = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )
    original_height, original_width = ink.shape
    ys, xs = np.nonzero(ink)
    if len(xs) >= 30:
        low_quantile = config.content_crop_quantile
        high_quantile = 1.0 - low_quantile
        x0, x1 = np.quantile(xs, [low_quantile, high_quantile]).astype(int)
        y0, y1 = np.quantile(ys, [low_quantile, high_quantile]).astype(int)
        x0, y0 = max(0, x0 - 3), max(0, y0 - 3)
        x1, y1 = min(original_width - 1, x1 + 3), min(original_height - 1, y1 + 3)
        cropped = ink[y0 : y1 + 1, x0 : x1 + 1]
    else:
        x0, y0, x1, y1 = 0, 0, original_width - 1, original_height - 1
        cropped = ink
    low_resolution = cv2.resize(
        cropped,
        (config.feature_width, config.feature_height),
        interpolation=cv2.INTER_AREA,
    ).astype(np.float32) / 255.0
    row_projection = cv2.resize(
        cropped.mean(axis=1).reshape(-1, 1),
        (1, config.row_projection_size),
        interpolation=cv2.INTER_AREA,
    ).reshape(-1) / 255.0
    column_projection = cv2.resize(
        cropped.mean(axis=0).reshape(1, -1),
        (config.column_projection_size, 1),
        interpolation=cv2.INTER_AREA,
    ).reshape(-1) / 255.0
    feature = np.concatenate(
        (low_resolution.reshape(-1), row_projection * 2.0, column_projection * 2.0)
    ).astype(np.float32)
    feature -= feature.mean()
    norm = float(np.linalg.norm(feature))
    if norm > 1e-9:
        feature /= norm
    return PageFingerprint(
        page=page,
        raster_width=original_width,
        raster_height=original_height,
        content_bbox=(int(x0), int(y0), int(x1), int(y1)),
        ink_ratio=round(float(np.mean(ink > 0)), 8),
        feature=feature,
    )


def fingerprint_pdf_pages(
    path: Path, config: PagePairingConfig | None = None
) -> tuple[PageFingerprint, ...]:
    config = config or PagePairingConfig()
    config.validate()
    fingerprints: list[PageFingerprint] = []
    with fitz.open(path) as document:
        for index, page in enumerate(document, start=1):
            pixmap = page.get_pixmap(
                matrix=fitz.Matrix(config.render_scale, config.render_scale),
                colorspace=fitz.csGRAY,
                alpha=False,
            )
            image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
                pixmap.height, pixmap.width
            )
            fingerprints.append(
                fingerprint_page_image(image, page=index, config=config)
            )
    return tuple(fingerprints)


def _runner_up_margin(matrix: NDArray[np.float32], row: int, column: int) -> float:
    score = float(matrix[row, column])
    alternatives = [
        *(float(value) for index, value in enumerate(matrix[row]) if index != column),
        *(float(value) for index, value in enumerate(matrix[:, column]) if index != row),
    ]
    return score - max(alternatives) if alternatives else 1.0


def align_page_fingerprints(
    reference: tuple[PageFingerprint, ...],
    candidate: tuple[PageFingerprint, ...],
    config: PagePairingConfig | None = None,
) -> PagePairAlignment:
    config = config or PagePairingConfig()
    config.validate()
    reference_count, candidate_count = len(reference), len(candidate)
    if not reference_count or not candidate_count:
        raise ValueError("both documents must contain at least one page")
    matrix = np.asarray(
        [[float(left.feature @ right.feature) for right in candidate] for left in reference],
        dtype=np.float32,
    )
    scores = np.full((reference_count + 1, candidate_count + 1), -np.inf)
    previous: list[list[tuple[int, int, PagePairAction] | None]] = [
        [None] * (candidate_count + 1) for _ in range(reference_count + 1)
    ]
    scores[0, 0] = 0.0
    priorities = {
        PagePairAction.MATCH: 0,
        PagePairAction.REFERENCE_ONLY: 1,
        PagePairAction.CANDIDATE_ONLY: 2,
    }

    def update(
        next_reference: int,
        next_candidate: int,
        score: float,
        state: tuple[int, int, PagePairAction],
    ) -> None:
        current = float(scores[next_reference, next_candidate])
        current_state = previous[next_reference][next_candidate]
        if score > current + 1e-9 or (
            abs(score - current) <= 1e-9
            and current_state is not None
            and priorities[state[2]] < priorities[current_state[2]]
        ):
            scores[next_reference, next_candidate] = score
            previous[next_reference][next_candidate] = state

    for reference_index in range(reference_count + 1):
        for candidate_index in range(candidate_count + 1):
            base = float(scores[reference_index, candidate_index])
            if not np.isfinite(base):
                continue
            if reference_index < reference_count and candidate_index < candidate_count:
                update(
                    reference_index + 1,
                    candidate_index + 1,
                    base + float(matrix[reference_index, candidate_index]),
                    (reference_index, candidate_index, PagePairAction.MATCH),
                )
            if reference_index < reference_count:
                update(
                    reference_index + 1,
                    candidate_index,
                    base - config.skip_penalty,
                    (reference_index, candidate_index, PagePairAction.REFERENCE_ONLY),
                )
            if candidate_index < candidate_count:
                update(
                    reference_index,
                    candidate_index + 1,
                    base - config.skip_penalty,
                    (reference_index, candidate_index, PagePairAction.CANDIDATE_ONLY),
                )

    reference_index, candidate_index = reference_count, candidate_count
    raw_steps: list[tuple[PagePairAction, int | None, int | None]] = []
    while reference_index or candidate_index:
        state = previous[reference_index][candidate_index]
        if state is None:
            raise RuntimeError(
                f"page alignment has no predecessor at {(reference_index, candidate_index)}"
            )
        previous_reference, previous_candidate, action = state
        raw_steps.append(
            (
                action,
                previous_reference if action is not PagePairAction.CANDIDATE_ONLY else None,
                previous_candidate if action is not PagePairAction.REFERENCE_ONLY else None,
            )
        )
        reference_index, candidate_index = previous_reference, previous_candidate
    raw_steps.reverse()

    matched_positions = [
        index for index, step in enumerate(raw_steps) if step[0] is PagePairAction.MATCH
    ]
    matched_position_set = set(matched_positions)
    steps: list[PagePairStep] = []
    for position, (action, row, column) in enumerate(raw_steps):
        if action is not PagePairAction.MATCH:
            steps.append(
                PagePairStep(
                    action=action,
                    reference_page=reference[row].page if row is not None else None,
                    candidate_page=candidate[column].page if column is not None else None,
                    similarity=None,
                    runner_up_margin=None,
                    sequence_supported=False,
                    accepted=False,
                    evidence=("unpaired page retained explicitly",),
                )
            )
            continue
        assert row is not None and column is not None
        similarity = float(matrix[row, column])
        margin = _runner_up_margin(matrix, row, column)
        neighbor_pairs = []
        for neighbor_position in (position - 1, position + 1):
            if neighbor_position not in matched_position_set:
                continue
            _neighbor_action, neighbor_row, neighbor_column = raw_steps[neighbor_position]
            assert neighbor_row is not None and neighbor_column is not None
            neighbor_pairs.append((neighbor_row, neighbor_column))
        sequence_supported = any(
            abs(neighbor_row - row) == 1 and abs(neighbor_column - column) == 1
            for neighbor_row, neighbor_column in neighbor_pairs
        )
        enough_ink = (
            reference[row].ink_ratio >= config.minimum_ink_ratio
            and candidate[column].ink_ratio >= config.minimum_ink_ratio
        )
        accepted = (
            enough_ink
            and similarity >= config.minimum_similarity
            and (margin >= config.minimum_runner_up_margin or sequence_supported)
        )
        evidence: list[str] = []
        evidence.append(
            "visual similarity above threshold"
            if similarity >= config.minimum_similarity
            else "visual similarity below threshold"
        )
        if margin >= config.minimum_runner_up_margin:
            evidence.append("runner-up margin above threshold")
        if sequence_supported:
            evidence.append("adjacent monotonic page pair supports alignment")
        if not enough_ink:
            evidence.append("insufficient page ink for confident pairing")
        if not accepted:
            evidence.append("pair retained but rejected for benchmark use")
        steps.append(
            PagePairStep(
                action=action,
                reference_page=reference[row].page,
                candidate_page=candidate[column].page,
                similarity=round(similarity, 6),
                runner_up_margin=round(margin, 6),
                sequence_supported=sequence_supported,
                accepted=accepted,
                evidence=tuple(evidence),
            )
        )
    return PagePairAlignment(reference_count, candidate_count, tuple(steps))


def align_pdf_pages(
    reference_path: Path,
    candidate_path: Path,
    config: PagePairingConfig | None = None,
) -> PagePairAlignment:
    config = config or PagePairingConfig()
    return align_page_fingerprints(
        fingerprint_pdf_pages(reference_path, config),
        fingerprint_pdf_pages(candidate_path, config),
        config,
    )

