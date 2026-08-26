from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import fitz
import pytest

from bctc_ai.evaluation.gemini_json_first_page_render_v1 import (
    GeminiJsonFirstPageRenderV1Error,
    inspect_full_pdf_page_box_v1,
    render_full_pdf_page_v1,
)


def _pdf(path: Path, *, hidden_x: float | None = None) -> bytes:
    document = fitz.open()
    page = document.new_page(width=200, height=100)
    page.insert_text((70, 30), "MIDDLE", fontsize=10)
    if hidden_x is not None:
        page.insert_text((hidden_x, 30), "HIDDEN", fontsize=10)
    document.save(path)
    document.close()
    return path.read_bytes()


def test_full_page_render_expands_declared_box_for_hidden_pdf_content(tmp_path) -> None:
    path = tmp_path / "hidden.pdf"
    source = _pdf(path, hidden_x=190)
    with fitz.open(path) as document:
        rendered = render_full_pdf_page_v1(
            document[0],
            physical_page=1,
            dpi=300,
            source_sha256=sha256(source).hexdigest(),
        )
    assert rendered.receipt["mode"] == "EXPANDED_SOURCE_CONTENT_BOUNDS"
    assert rendered.receipt["original_media_box"] == [0.0, 0.0, 200.0, 100.0]
    assert rendered.receipt["selected_media_box"][2] > 200
    assert rendered.page["pixel_width"] > 834
    assert rendered.page["image_sha256"] == sha256(rendered.image).hexdigest()


def test_full_page_render_keeps_one_normal_declared_page_box(tmp_path) -> None:
    path = tmp_path / "normal.pdf"
    source = _pdf(path)
    with fitz.open(path) as document:
        standard = document[0].get_pixmap(dpi=200, alpha=False).tobytes("png")
    with fitz.open(path) as document:
        rendered = render_full_pdf_page_v1(
            document[0],
            physical_page=1,
            dpi=200,
            source_sha256=sha256(source).hexdigest(),
        )
    assert rendered.receipt["mode"] == "DECLARED_PAGE_BOX"
    assert rendered.receipt["selected_media_box"] == [0.0, 0.0, 200.0, 100.0]
    assert rendered.page["pixel_width"] == 556
    assert rendered.image == standard


def test_full_page_render_restores_complete_media_box_from_declared_crop(
    tmp_path,
) -> None:
    path = tmp_path / "cropped.pdf"
    document = fitz.open()
    page = document.new_page(width=200, height=100)
    page.insert_text((70, 30), "MIDDLE", fontsize=10)
    page.set_cropbox(fitz.Rect(0, 10, 200, 90))
    document.save(path)
    document.close()
    source = path.read_bytes()
    with fitz.open(path) as document:
        standard = document[0].get_pixmap(dpi=200, alpha=False).tobytes("png")
    with fitz.open(path) as document:
        rendered = render_full_pdf_page_v1(
            document[0],
            physical_page=1,
            dpi=200,
            source_sha256=sha256(source).hexdigest(),
        )
    assert rendered.receipt["mode"] == "EXPANDED_DECLARED_MEDIA_BOX"
    assert rendered.receipt["original_crop_box"] == [0.0, 10.0, 200.0, 90.0]
    assert rendered.receipt["selected_media_box"] == [0.0, 0.0, 200.0, 100.0]
    assert rendered.page["pixel_height"] == 278
    assert rendered.image != standard


def test_full_page_box_inspection_matches_render_without_mutating_page(tmp_path) -> None:
    path = tmp_path / "cropped.pdf"
    document = fitz.open()
    page = document.new_page(width=200, height=100)
    page.insert_text((70, 30), "MIDDLE", fontsize=10)
    page.set_cropbox(fitz.Rect(0, 10, 200, 90))
    document.save(path)
    document.close()
    with fitz.open(path) as document:
        before = fitz.Rect(document[0].cropbox)
        inspection = inspect_full_pdf_page_box_v1(document[0])
        after = fitz.Rect(document[0].cropbox)
    assert inspection.mode == "EXPANDED_DECLARED_MEDIA_BOX"
    assert list(inspection.selected_media) == [0.0, 0.0, 200.0, 100.0]
    assert before == after


def test_full_page_render_ignores_out_of_page_invisible_ocr_text(tmp_path) -> None:
    path = tmp_path / "invisible-ocr.pdf"
    document = fitz.open()
    page = document.new_page(width=200, height=100)
    page.insert_text((70, 30), "MIDDLE", fontsize=10)
    page.insert_text((400, 30), "OCR", fontsize=10, render_mode=3)
    document.save(path)
    document.close()
    source = path.read_bytes()
    with fitz.open(path) as document:
        standard = document[0].get_pixmap(dpi=200, alpha=False).tobytes("png")
    with fitz.open(path) as document:
        rendered = render_full_pdf_page_v1(
            document[0],
            physical_page=1,
            dpi=200,
            source_sha256=sha256(source).hexdigest(),
        )
    assert rendered.receipt["mode"] == "DECLARED_PAGE_BOX"
    assert rendered.receipt["painted_object_count"] == 1
    assert rendered.image == standard


def test_full_page_render_handles_visible_content_above_media_origin(tmp_path) -> None:
    path = tmp_path / "negative-origin.pdf"
    document = fitz.open()
    page = document.new_page(width=200, height=100)
    page.draw_rect(
        fitz.Rect(10, -20, 50, 20),
        color=(0, 0, 0),
        fill=(0, 0, 0),
    )
    document.save(path)
    document.close()
    source = path.read_bytes()
    with fitz.open(path) as document:
        rendered = render_full_pdf_page_v1(
            document[0],
            physical_page=1,
            dpi=200,
            source_sha256=sha256(source).hexdigest(),
        )
    assert rendered.receipt["mode"] == "EXPANDED_SOURCE_CONTENT_BOUNDS"
    assert rendered.receipt["selected_media_box"][1] < 0
    assert rendered.page["pixel_height"] > 278


def test_full_page_render_rejects_unbounded_hidden_source_content(tmp_path) -> None:
    path = tmp_path / "unsafe.pdf"
    source = _pdf(path, hidden_x=400)
    with (
        fitz.open(path) as document,
        pytest.raises(
            GeminiJsonFirstPageRenderV1Error,
            match="bounded whole-page expansion",
        ),
    ):
        render_full_pdf_page_v1(
            document[0],
            physical_page=1,
            dpi=300,
            source_sha256=sha256(source).hexdigest(),
        )
