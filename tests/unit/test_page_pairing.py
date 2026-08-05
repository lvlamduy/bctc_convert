from __future__ import annotations

import cv2
import numpy as np

from bctc_ai.evaluation.page_pairing import (
    PagePairAction,
    PagePairingConfig,
    align_page_fingerprints,
    fingerprint_page_image,
)


def _page(seed: int) -> np.ndarray:
    image = np.full((720, 520), 255, dtype=np.uint8)
    cv2.rectangle(image, (35, 28), (485, 675), 210, 2)
    for row in range(7 + seed):
        y = 75 + row * (54 - seed)
        cv2.rectangle(image, (70 + seed * 3, y), (330 + row * 7, y + 8), 0, -1)
        cv2.rectangle(image, (385, y), (450, y + 8), 0, -1)
    cv2.circle(image, (105 + seed * 35, 620), 10 + seed * 2, 0, -1)
    return image


def test_ordered_page_pairing_handles_inserted_cover_and_mild_scan_degradation():
    config = PagePairingConfig(minimum_similarity=0.35)
    references = tuple(
        fingerprint_page_image(_page(seed), page=seed + 1, config=config)
        for seed in range(3)
    )
    cover = np.full((720, 520), 255, dtype=np.uint8)
    cv2.putText(cover, "COVER", (120, 350), cv2.FONT_HERSHEY_SIMPLEX, 2, 0, 4)
    candidate_images = [cover]
    for seed in range(3):
        degraded = cv2.GaussianBlur(_page(seed), (3, 3), 0.4)
        degraded = cv2.convertScaleAbs(degraded, alpha=0.92, beta=12)
        candidate_images.append(degraded)
    candidates = tuple(
        fingerprint_page_image(image, page=index + 1, config=config)
        for index, image in enumerate(candidate_images)
    )

    alignment = align_page_fingerprints(references, candidates, config)

    assert alignment.steps[0].action is PagePairAction.CANDIDATE_ONLY
    assert [(step.reference_page, step.candidate_page) for step in alignment.accepted] == [
        (1, 2),
        (2, 3),
        (3, 4),
    ]


def test_ambiguous_single_page_pair_is_retained_but_not_accepted():
    config = PagePairingConfig(minimum_runner_up_margin=0.05)
    source = fingerprint_page_image(_page(1), page=1, config=config)
    duplicate_a = fingerprint_page_image(_page(1), page=1, config=config)
    duplicate_b = fingerprint_page_image(_page(1), page=2, config=config)

    alignment = align_page_fingerprints((source,), (duplicate_a, duplicate_b), config)

    matched = alignment.matched[0]
    assert matched.similarity == 1.0
    assert matched.runner_up_margin == 0.0
    assert matched.sequence_supported is False
    assert matched.accepted is False

