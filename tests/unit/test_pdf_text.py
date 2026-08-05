from __future__ import annotations

import fitz

from bctc_ai.ocr.pdf_text import extract_pdf_text


def test_pdf_text_keeps_raw_normalized_and_geometry(tmp_path):
    path = tmp_path / "text.pdf"
    document = fitz.open()
    page = document.new_page()
    # PyMuPDF's built-in test font does not embed Vietnamese glyphs. Unicode
    # normalization itself is covered separately in test_text.py.
    page.insert_text((72, 72), "Von chu so huu")
    document.save(path)
    document.close()
    pages = extract_pdf_text(path)
    assert pages[0].text_quality == "USABLE_TEXT_LAYER"
    assert any(word.normalized_text == "Von" for word in pages[0].words)
    assert all(word.bbox_points.x1 >= word.bbox_points.x0 for word in pages[0].words)


def test_scan_without_text_layer_fails_to_ocr_required_state(tmp_path):
    path = tmp_path / "scan.pdf"
    document = fitz.open()
    document.new_page()
    document.save(path)
    document.close()
    assert extract_pdf_text(path)[0].text_quality == "NO_TEXT_LAYER"
