from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import fitz

from bctc_ai.core.contracts import BoundingBox
from bctc_ai.core.text import normalize_text

_MOJIBAKE_MARKERS = ("�", "Ã", "Â", "Ä", "á»", "áº")


@dataclass(frozen=True)
class PDFWord:
    raw_text: str
    normalized_text: str
    bbox_points: BoundingBox
    block_number: int
    line_number: int
    word_number: int


@dataclass(frozen=True)
class PDFTextPage:
    page: int
    width_points: float
    height_points: float
    rotation: int
    words: list[PDFWord]
    text_quality: str
    corruption_markers: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _quality(words: list[PDFWord]) -> tuple[str, tuple[str, ...]]:
    raw = " ".join(word.raw_text for word in words)
    markers = tuple(marker for marker in _MOJIBAKE_MARKERS if marker in raw)
    if not words:
        return "NO_TEXT_LAYER", ()
    replacement_ratio = raw.count("�") / max(1, len(raw))
    if markers or replacement_ratio > 0.001:
        return "CORRUPT_TEXT_LAYER", markers
    return "USABLE_TEXT_LAYER", ()


def extract_pdf_text_page(page: fitz.Page) -> PDFTextPage:
    words = [
        PDFWord(
            raw_text=item[4],
            normalized_text=normalize_text(item[4]),
            bbox_points=BoundingBox(item[0], item[1], item[2], item[3]),
            block_number=int(item[5]),
            line_number=int(item[6]),
            word_number=int(item[7]),
        )
        for item in page.get_text("words", sort=True)
        if normalize_text(item[4])
    ]
    quality, markers = _quality(words)
    return PDFTextPage(
        page=page.number + 1,
        width_points=page.rect.width,
        height_points=page.rect.height,
        rotation=page.rotation,
        words=words,
        text_quality=quality,
        corruption_markers=markers,
    )


def extract_pdf_text(path: Path, page_numbers: set[int] | None = None) -> list[PDFTextPage]:
    with fitz.open(path) as document:
        selected = page_numbers or set(range(1, document.page_count + 1))
        return [extract_pdf_text_page(document[number - 1]) for number in sorted(selected)]
