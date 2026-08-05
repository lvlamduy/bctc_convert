from __future__ import annotations

import cv2
import fitz
import numpy as np

from bctc_ai.preprocessing.quality import assess_array, assess_image
from bctc_ai.preprocessing.variants import generate_difficult_region_variants, generate_variants
from bctc_ai.rendering.pdf import inspect_pdf, render_pages


def test_born_digital_pdf_render_and_quality_manifest(tmp_path):
    source = tmp_path / "sample.pdf"
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((72, 72), "Báo cáo tài chính ngân hàng " * 3)
    document.save(source)
    document.close()

    inspection = inspect_pdf(source)
    assert inspection.page_count == 1
    assert inspection.document_kind == "BORN_DIGITAL"

    rendered = render_pages(source, tmp_path / "renders", dpi=150)
    assert len(rendered) == 1
    render_path = tmp_path / "renders" / "page-0001.png"
    assert render_path.is_file()

    quality = assess_image(render_path)
    variants = generate_variants(render_path, tmp_path / "preprocess", quality)
    assert variants
    assert (tmp_path / "preprocess" / "manifest.json").is_file()


def test_dark_colored_header_gets_local_variants(tmp_path):
    image = np.full((480, 720, 3), 255, dtype=np.uint8)
    cv2.rectangle(image, (0, 80), (719, 179), (110, 35, 20), thickness=-1)
    cv2.putText(
        image,
        "CURRENT PERIOD",
        (40, 145),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    quality = assess_array(image)
    assert any("DARK" in region.reason for region in quality.difficult_regions)
    render = tmp_path / "page.png"
    assert cv2.imwrite(str(render), image)
    variants = generate_difficult_region_variants(
        render, tmp_path / "regions", quality.difficult_regions
    )
    assert any(variant.name == "gamma-lightened" for variant in variants)
    assert any(variant.name == "inverted" for variant in variants)


def test_perspective_page_is_detected_and_corrected(tmp_path):
    image = np.zeros((600, 800, 3), dtype=np.uint8)
    quadrilateral = np.array([[100, 50], [730, 95], [680, 560], [55, 520]], dtype=np.int32)
    cv2.fillConvexPoly(image, quadrilateral, (245, 245, 245))
    cv2.polylines(image, [quadrilateral], True, (255, 255, 255), 5)
    quality = assess_array(image)
    assert "PERSPECTIVE_DISTORTED" in quality.classifications
    assert quality.perspective_corners is not None
    render = tmp_path / "perspective.png"
    assert cv2.imwrite(str(render), image)
    variants = generate_variants(render, tmp_path / "variants", quality)
    corrected = next(variant for variant in variants if variant.name == "perspective-corrected")
    assert corrected.transform_to_render != [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
