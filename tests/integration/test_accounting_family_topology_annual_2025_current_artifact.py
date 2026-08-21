from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import fitz
from PIL import Image, ImageOps

from bctc_ai.evaluation.accounting_family_topology_v1 import (
    build_accounting_family_topology_scan_v1,
)
from bctc_ai.evaluation.adaptive_accounting_table_geometry_v1 import (
    propose_missing_value_lane_regions_v1,
)
from bctc_ai.evaluation.family_first_authenticated_page_region_v1 import (
    WHITE_BORDER,
    _foreground_recognition_bbox,
)
from bctc_ai.evaluation.family_first_numeric_cell_evidence_v1 import (
    parse_visible_financial_numeric_token_v1,
)
from bctc_ai.evaluation.family_first_visible_dash_glyph_evidence_v1 import (
    build_family_first_visible_dash_glyph_evidence_v1,
)
from bctc_ai.evaluation.full_document_vietocr_accounting_axis_v1 import (
    project_full_document_vietocr_accounting_axis_v1,
)

_ROOT = Path(__file__).resolve().parents[2]
_INDEX = _ROOT / (
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/"
    "verified-index/semantic_index.json"
)
_SPEC = _ROOT / "config/families/tm-cash-precious-metals-topology-v1.json"


def _blind_pages(document: dict[str, object]) -> list[dict[str, object]]:
    return [
        {
            "lines": [
                {
                    "bbox": line["bbox"],
                    "source_line_index": line["source_line_index"],
                    "source_text": None,
                    "vietocr_text": line["vietocr_text"],
                }
                for line in page["lines"]
            ],
            "page_sequence": page["page_sequence"],
        }
        for page in document["pages"]
    ]


def test_generic_cash_topology_is_unique_in_all_eight_annual_2025_documents() -> None:
    semantic_index = json.loads(_INDEX.read_text(encoding="utf-8"))
    family_spec = json.loads(_SPEC.read_text(encoding="utf-8"))
    documents = project_full_document_vietocr_accounting_axis_v1(semantic_index)["documents"]

    scans = [
        build_accounting_family_topology_scan_v1(_blind_pages(document), family_spec)
        for document in documents
    ]

    assert len(scans) == 8
    assert all(scan["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL" for scan in scans)
    assert all(scan["metrics"]["complete_region_count"] == 1 for scan in scans)
    assert all(
        scan["regions"][0]["minimal_unique_anchor"]["combination_size"] == 2 for scan in scans
    )
    observed_optional_roles = {
        role
        for scan in scans
        for role in scan["regions"][0]["observed_roles"]
        if role not in {"CASH_VND", "CASH_FOREIGN"}
    }
    assert observed_optional_roles == {
        "FOREIGN_CURRENCY_VALUABLE_DOCUMENT",
        "MONETARY_GOLD",
        "NONMONETARY_GOLD",
        "OTHER_PRECIOUS_METALS_GEMS",
    }


def test_ctg_detector_omitted_cash_dash_replays_from_source_pixels() -> None:
    persisted = json.loads(_INDEX.read_text(encoding="utf-8"))
    family_spec = json.loads(_SPEC.read_text(encoding="utf-8"))
    raw_document = next(item for item in persisted["documents"] if item["bank_code"] == "CTG")
    document = project_full_document_vietocr_accounting_axis_v1(persisted)["documents"][
        raw_document["document_ordinal"] - 1
    ]
    scan = build_accounting_family_topology_scan_v1(_blind_pages(document), family_spec)
    region = scan["regions"][0]
    match = next(item for item in region["child_matches"] if item["role"] == "NONMONETARY_GOLD")
    page = document["pages"][match["page_sequence"] - 1]
    offset = sum(len(item["lines"]) for item in document["pages"][: match["page_sequence"] - 1])
    lines = [
        {
            "bbox": item["bbox"],
            "source_line_index": item["source_line_index"],
            "vietocr_text": item["vietocr_text"],
        }
        for local, item in enumerate(page["lines"])
        if region["cluster_start_document_line_ordinal"]
        <= offset + local
        < region["cluster_end_document_line_ordinal_exclusive"]
    ]
    label_boxes = [
        item["bbox"]
        for item in lines
        if match["source_line_index"] <= item["source_line_index"] <= match["end_source_line_index"]
    ]

    def numeric(item):
        return parse_visible_financial_numeric_token_v1(item["vietocr_text"])["classification"] in {
            "DASH_ZERO",
            "SIGNED_NUMBER",
        }

    proposals = propose_missing_value_lane_regions_v1(
        lines,
        label_boxes=label_boxes,
        is_numeric=numeric,
        page_width=1654,
        page_height=2339,
        retain_singleton_columns=True,
    )
    assert len(proposals) == 1
    assert proposals[0]["column_ordinal"] == 0

    source = _ROOT / raw_document["source_pdf"]["path"]
    source_bytes = source.read_bytes()
    assert hashlib.sha256(source_bytes).hexdigest() == (
        "b82eeb879b667e80d0b5322969c808089fd39b83835b75dc47f9a890189fc137"
    )
    with fitz.open(stream=source_bytes, filetype="pdf") as pdf:
        render = (
            pdf[match["page_sequence"] - 1]
            .get_pixmap(matrix=fitz.Matrix(2, 2), colorspace=fitz.csRGB, alpha=False)
            .tobytes("png")
        )
    assert hashlib.sha256(render).hexdigest() == (
        "28da643f73188e3818ab3cfd7bb372b4c925677548e31bb71843eefce0675e21"
    )
    image = Image.open(io.BytesIO(render)).convert("RGB")
    recognition_bbox, _status = _foreground_recognition_bbox(image, proposals[0]["raw_pixel_bbox"])
    crop = ImageOps.expand(
        image.crop(tuple(recognition_bbox)), border=WHITE_BORDER, fill=(255, 255, 255)
    )
    stream = io.BytesIO()
    crop.save(stream, format="PNG", optimize=False, compress_level=9)
    evidence = build_family_first_visible_dash_glyph_evidence_v1(crop_png_bytes=stream.getvalue())

    assert evidence["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH"
    assert evidence["normalized_value"] == 0
