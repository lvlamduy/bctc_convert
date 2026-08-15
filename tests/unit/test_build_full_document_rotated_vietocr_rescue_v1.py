from __future__ import annotations

import importlib.util
import io
import sys
from pathlib import Path

import pytest
from PIL import Image

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_full_document_rotated_vietocr_rescue_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "build_full_document_rotated_vietocr_rescue_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
rescue = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = rescue
_SPEC.loader.exec_module(rescue)


def _line(index: int, *, vertical: bool) -> dict[str, object]:
    bbox = [10 + index, 20, 20 + index, 60] if vertical else [10, 20 + index, 60, 30 + index]
    return {
        "crop_ref": {
            "path": f"output/crops/source-{index:04d}.png",
            "sha256": f"{index + 1:064x}",
            "size_bytes": 100 + index,
        },
        "source_bbox_raw_pixels": bbox,
        "source_line_index": index,
    }


def _index(vertical_count: int) -> dict[str, object]:
    lines = [_line(index, vertical=index < vertical_count) for index in range(20)]
    return {
        "documents": [
            {
                "bank_code": "MUST_NOT_ROUTE",
                "document_ordinal": 1,
                "pages": [
                    {
                        "lines": lines,
                        "physical_page": 1,
                        "source_projection": {
                            "identity": "ssv2:page:" + "1" * 64,
                            "sha256": "2" * 64,
                        },
                    }
                ],
                "source_pdf": {
                    "path": "corpus/report.pdf",
                    "sha256": "3" * 64,
                    "size_bytes": 999,
                },
            }
        ]
    }


def test_geometry_selection_uses_closed_85_percent_rule() -> None:
    selected = rescue._selected_pages(_index(17))
    assert len(selected) == 1
    assert selected[0]["vertical_line_count"] == 17
    assert rescue._selected_pages(_index(16)) == []


def test_selection_is_independent_of_bank_filename_page_and_text() -> None:
    first = _index(20)
    second = _index(20)
    second["documents"][0]["bank_code"] = "ANOTHER_BANK"
    second["documents"][0]["source_pdf"]["path"] = "different/name.pdf"
    for line in second["documents"][0]["pages"][0]["lines"]:
        line["vietocr_text"] = "arbitrary semantic content"

    left = rescue._selected_pages(first)
    right = rescue._selected_pages(second)
    assert [(item["physical_page"], item["vertical_line_count"]) for item in left] == [
        (item["physical_page"], item["vertical_line_count"]) for item in right
    ]


def test_clockwise_rotation_is_deterministic_and_pixel_exact() -> None:
    image = Image.new("RGB", (2, 3))
    image.putdata(
        [
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
            (255, 255, 0),
            (255, 0, 255),
            (0, 255, 255),
        ]
    )
    source = io.BytesIO()
    image.save(source, format="PNG")

    first = rescue._rotated_png(source.getvalue())
    second = rescue._rotated_png(source.getvalue())
    assert first == second
    with Image.open(io.BytesIO(first)) as rotated:
        assert rotated.size == (3, 2)
        assert list(rotated.convert("RGB").get_flattened_data()) == [
            (255, 0, 255),
            (0, 0, 255),
            (255, 0, 0),
            (0, 255, 255),
            (255, 255, 0),
            (0, 255, 0),
        ]


@pytest.mark.parametrize(
    "payload",
    [b'{"a":1,"a":2}', b'{"a":NaN}', b"[]"],
)
def test_strict_json_rejects_ambiguous_payloads(payload: bytes) -> None:
    with pytest.raises(rescue.FullDocumentRotatedVietOCRRescueV1Error):
        rescue._strict_json(payload, "test")


def test_current_full_document_index_selects_exact_rotated_denominator() -> None:
    index, reference = rescue._source_index()
    selected = rescue._selected_pages(index)

    assert reference == {
        "path": rescue.SOURCE_INDEX_PATH.as_posix(),
        "sha256": rescue.SOURCE_INDEX_SHA256,
        "size_bytes": rescue.SOURCE_INDEX_SIZE,
    }
    assert len(selected) == 15
    assert sum(len(page["lines"]) for page in selected) == 1_863
    assert [page["document_ordinal"] for page in selected] == [
        1,
        1,
        1,
        7,
        7,
        7,
        7,
        8,
        8,
        8,
        8,
        8,
        8,
        8,
        8,
    ]


def test_reader_surface_is_reference_blind() -> None:
    assert rescue._REQUEST_SAMPLE_FIELDS == {
        "category",
        "crop_path",
        "crop_sha256",
        "sample_id",
    }
    assert not {
        "bank_code",
        "physical_page",
        "source_text",
        "vietocr_text",
        "family_id",
        "report_norm_id",
    }.intersection(rescue._REQUEST_SAMPLE_FIELDS)
