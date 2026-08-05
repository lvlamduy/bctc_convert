from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import fitz

from bctc_ai.core.atomic import atomic_write_bytes, atomic_write_json
from bctc_ai.core.hashing import sha256_file


@dataclass(frozen=True)
class PageInspection:
    page: int
    width_points: float
    height_points: float
    rotation: int
    extracted_text_characters: int
    embedded_image_count: int
    content_kind: str


@dataclass(frozen=True)
class DocumentInspection:
    source_sha256: str
    page_count: int
    encrypted: bool
    document_kind: str
    pages: list[PageInspection]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RenderedPage:
    page: int
    dpi: int
    path: str
    width_pixels: int
    height_pixels: int
    sha256: str
    rotation: int
    source_sha256: str


def _page_content_kind(text_characters: int, image_count: int) -> str:
    if text_characters >= 40 and image_count:
        return "MIXED"
    if text_characters >= 40:
        return "BORN_DIGITAL"
    if image_count:
        return "SCANNED"
    return "UNKNOWN"


def inspect_pdf(path: Path) -> DocumentInspection:
    source_hash = sha256_file(path)
    with fitz.open(path) as document:
        if document.needs_pass:
            return DocumentInspection(source_hash, document.page_count, True, "ENCRYPTED", [])
        pages: list[PageInspection] = []
        for index, page in enumerate(document):
            text_characters = len("".join(page.get_text("text").split()))
            image_count = len(page.get_images(full=True))
            pages.append(
                PageInspection(
                    page=index + 1,
                    width_points=round(page.rect.width, 4),
                    height_points=round(page.rect.height, 4),
                    rotation=page.rotation,
                    extracted_text_characters=text_characters,
                    embedded_image_count=image_count,
                    content_kind=_page_content_kind(text_characters, image_count),
                )
            )
    kinds = {page.content_kind for page in pages}
    if not pages:
        document_kind = "EMPTY"
    elif kinds == {"BORN_DIGITAL"}:
        document_kind = "BORN_DIGITAL"
    elif kinds <= {"SCANNED", "UNKNOWN"}:
        document_kind = "SCANNED"
    else:
        document_kind = "MIXED"
    return DocumentInspection(source_hash, len(pages), False, document_kind, pages)


def render_pages(
    source: Path,
    output_directory: Path,
    *,
    dpi: int = 300,
    page_numbers: set[int] | None = None,
) -> list[RenderedPage]:
    if dpi < 72 or dpi > 600:
        raise ValueError("DPI must be between 72 and 600")
    source_hash = sha256_file(source)
    output_directory.mkdir(parents=True, exist_ok=True)
    records: list[RenderedPage] = []
    with fitz.open(source) as document:
        if document.needs_pass:
            raise ValueError(f"password-protected PDF cannot be rendered: {source}")
        selected = page_numbers or set(range(1, document.page_count + 1))
        invalid = sorted(page for page in selected if page < 1 or page > document.page_count)
        if invalid:
            raise ValueError(f"page numbers outside document: {invalid}")
        scale = dpi / 72.0
        for page_number in sorted(selected):
            page = document[page_number - 1]
            pixmap = page.get_pixmap(
                matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False
            )
            payload = pixmap.tobytes("png")
            path = output_directory / f"page-{page_number:04d}.png"
            digest = atomic_write_bytes(path, payload)
            records.append(
                RenderedPage(
                    page=page_number,
                    dpi=dpi,
                    path=path.as_posix(),
                    width_pixels=pixmap.width,
                    height_pixels=pixmap.height,
                    sha256=digest,
                    rotation=page.rotation,
                    source_sha256=source_hash,
                )
            )
    atomic_write_json(
        output_directory / "manifest.json",
        {
            "format_version": 1,
            "source": source.as_posix(),
            "source_sha256": source_hash,
            "dpi": dpi,
            "pages": [asdict(record) for record in records],
        },
    )
    return records
