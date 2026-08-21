from __future__ import annotations

import copy
import hashlib
import io

import pytest
from PIL import Image

from bctc_ai.evaluation import family_first_authenticated_page_region_v1 as render_v1
from bctc_ai.evaluation import family_first_semantic_index_v1 as semantic_v1
from bctc_ai.evaluation.accounting_family_document_axis_join_v1 import (
    AccountingFamilyDocumentAxisJoinV1Error,
    build_accounting_family_document_axis_join_v1,
    project_accounting_family_document_pages_v1,
    validate_accounting_family_document_axis_join_replay_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _ref(sample: int) -> dict[str, object]:
    return {
        "path": f"opaque/crop-{sample:04d}.png",
        "sha256": f"{sample:064x}",
        "size_bytes": 100 + sample,
    }


def _semantic_line(sample: int, line: int, text: str, bbox: list[int]):
    return {
        "accentless_text": text.lower(),
        "crop_ref": _ref(sample),
        "format_version": semantic_v1.LINE_FORMAT_VERSION,
        "line_ordinal": line,
        "mean_decoded_character_probability": 0.95,
        "processed_height": 32,
        "processed_width": 100,
        "sample_id": f"sample-{sample:09d}",
        "source_bbox_raw_pixels": bbox,
        "vietocr_text": text,
        "vietocr_text_nfc": text,
    }


def _semantic_document():
    pages = [
        {
            "line_count": 2,
            "lines": [
                _semantic_line(1, 0, "Tiền, kim loại quý và đá quý", [20, 20, 300, 45]),
                _semantic_line(2, 1, "100", [600, 80, 700, 105]),
            ],
            "physical_page": 1,
        },
        {
            "line_count": 1,
            "lines": [_semantic_line(3, 0, "Thuyết minh khác", [20, 20, 300, 45])],
            "physical_page": 2,
        },
    ]
    material = {
        "document_ordinal": 1,
        "format_version": semantic_v1.DOCUMENT_FORMAT_VERSION,
        "line_count": 3,
        "page_count": 2,
        "pages": pages,
        "private_provenance": {"opaque": "source-binding"},
        "source_pdf_ref": {
            "path": "opaque/source.pdf",
            "sha256": "a" * 64,
            "size_bytes": 999,
        },
    }
    return {
        **material,
        "document_id": "ffsiv1:document:" + canonical_json_sha256_v1(material),
    }


def _numeric_document():
    return {
        "document_ordinal": 1,
        "lines": [
            {
                "crop_ref": _ref(1),
                "line_ordinal": 0,
                "physical_page": 1,
                "raw_prediction": "",
                "reader_score": 0.1,
                "sample_id": "sample-000000001",
                "source_bbox_raw_pixels": [20, 20, 300, 45],
            },
            {
                "crop_ref": _ref(2),
                "line_ordinal": 1,
                "physical_page": 1,
                "raw_prediction": "100",
                "reader_score": 0.99,
                "sample_id": "sample-000000002",
                "source_bbox_raw_pixels": [600, 80, 700, 105],
            },
            {
                "crop_ref": _ref(3),
                "line_ordinal": 0,
                "physical_page": 2,
                "raw_prediction": "",
                "reader_score": 0.1,
                "sample_id": "sample-000000003",
                "source_bbox_raw_pixels": [20, 20, 300, 45],
            },
        ],
        "private_provenance": {"opaque": "source-binding"},
        "source_pdf_ref": {
            "path": "opaque/source.pdf",
            "sha256": "a" * 64,
            "size_bytes": 999,
        },
    }


def _render_snapshot(page: int = 1):
    stream = io.BytesIO()
    Image.new("RGB", (1000, 1400), color=(255, 255, 255)).save(stream, format="PNG")
    payload = stream.getvalue()
    material = {
        "archive_id": "ffslav1:archive:" + "1" * 64,
        "authority": copy.deepcopy(render_v1._RENDER_AUTHORITY),
        "document_ordinal": 1,
        "format_version": render_v1.RENDER_FORMAT_VERSION,
        "index_id": "ffsiv1:index:" + "2" * 64,
        "physical_page": page,
        "plan_id": "ffslpv1:plan:" + "3" * 64,
        "render_ref": {
            "pixel_height": 1400,
            "pixel_width": 1000,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        },
        "state": "AUTHENTICATED_EXACT_SOURCE_PAGE_RENDER_SNAPSHOT",
    }
    return {
        **material,
        "render_id": "ffaprv1:render:" + canonical_json_sha256_v1(material),
        "render_png_bytes": payload,
    }


def test_complete_join_uses_selected_page_dimensions_only() -> None:
    semantic = _semantic_document()
    numeric = _numeric_document()
    render = _render_snapshot()
    result = build_accounting_family_document_axis_join_v1(
        semantic,
        numeric,
        selected_page_render_snapshots=(render,),
    )

    assert result["metrics"] == {
        "line_count": 3,
        "page_count": 2,
        "page_count_with_authenticated_dimensions": 1,
    }
    pages = project_accounting_family_document_pages_v1(result)
    assert pages[0]["page_width"] == 1000
    assert pages[1]["page_width"] is None
    assert pages[0]["lines"][1]["vietocr_text"] == "100"
    assert pages[0]["lines"][1]["numeric_recognition"] == {
        "raw_prediction": "100",
        "reader_score": 0.99,
    }
    assert result["safety"]["detector_geometry_treated_as_numeric_recognition"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        lambda numeric: numeric["lines"][1].__setitem__("sample_id", "sample-999999999"),
        lambda numeric: numeric["lines"][1].__setitem__("raw_prediction", 100),
        lambda numeric: numeric["lines"][1].__setitem__("reader_score", True),
        lambda numeric: numeric["lines"][1].__setitem__(
            "source_bbox_raw_pixels", [601, 80, 700, 105]
        ),
    ],
)
def test_semantic_numeric_crop_axis_mismatch_fails_closed(mutation) -> None:
    numeric = _numeric_document()
    mutation(numeric)
    with pytest.raises(AccountingFamilyDocumentAxisJoinV1Error):
        build_accounting_family_document_axis_join_v1(
            _semantic_document(),
            numeric,
            selected_page_render_snapshots=(_render_snapshot(),),
        )


def test_render_bytes_and_page_identity_fail_closed() -> None:
    render = _render_snapshot()
    render["render_png_bytes"] += b"x"
    with pytest.raises(AccountingFamilyDocumentAxisJoinV1Error, match="reference"):
        build_accounting_family_document_axis_join_v1(
            _semantic_document(),
            _numeric_document(),
            selected_page_render_snapshots=(render,),
        )

    duplicate = _render_snapshot()
    with pytest.raises(AccountingFamilyDocumentAxisJoinV1Error, match="repeats"):
        build_accounting_family_document_axis_join_v1(
            _semantic_document(),
            _numeric_document(),
            selected_page_render_snapshots=(duplicate, duplicate),
        )


def test_exact_replay_rejects_joined_numeric_mutation() -> None:
    semantic = _semantic_document()
    numeric = _numeric_document()
    renders = (_render_snapshot(),)
    result = build_accounting_family_document_axis_join_v1(
        semantic, numeric, selected_page_render_snapshots=renders
    )
    forged = copy.deepcopy(result)
    forged["pages"][0]["lines"][1]["numeric_recognition"]["raw_prediction"] = "999"
    material = copy.deepcopy(forged)
    material.pop("document_axis_id")
    forged["document_axis_id"] = "afdajv1:axis:" + canonical_json_sha256_v1(material)

    with pytest.raises(AccountingFamilyDocumentAxisJoinV1Error, match="replay exactly"):
        validate_accounting_family_document_axis_join_replay_v1(
            forged,
            semantic,
            numeric,
            selected_page_render_snapshots=renders,
        )
