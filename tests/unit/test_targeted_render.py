from __future__ import annotations

import copy

import fitz
import pytest

from bctc_ai.core.hashing import sha256_file
from bctc_ai.preprocessing.targeted_render import render_targeted_reread_page
from bctc_ai.preprocessing.targeted_reread import TargetedRereadError


def _source(path):
    document = fitz.open()
    page = document.new_page(width=200, height=100)
    page.insert_text((20, 25), "Năm 2025                    Năm 2024", fontsize=8)
    page.insert_text((20, 50), "Tiền mặt                1.000       900", fontsize=8)
    document.save(path)
    document.close()


def _plan():
    return {
        "page": 1,
        "statement_type": "CDKT",
        "status": "PLANNED",
        "baseline_render": {"width_pixels": 400, "height_pixels": 200},
        "regions": [
            {
                "region_id": "region-0001",
                "region_kind": "FULL_TABLE_STRUCTURAL_RECOVERY",
                "bbox_in_baseline_render": (40, 20, 360, 160),
                "bbox_normalized": (0.1, 0.1, 0.9, 0.8),
                "target_dpi": 600,
                "readers": ("PADDLEOCR_VL_1_6", "PP_OCRV6_MEDIUM"),
                "variant_policy": "QUALITY_GATED_ORIGINAL_PLUS_PROVENANCED_VARIANTS",
                "automatic_value_replacement": False,
                "automatic_confidence_promotion": False,
            }
        ],
        "safety": {
            "require_upstream_mapping_eligible": True,
            "preserve_original": True,
            "arithmetic_selects_variant": False,
            "history_selects_variant": False,
            "schema_selects_variant": False,
            "automatic_value_replacement": False,
            "automatic_confidence_promotion": False,
            "cross_page_region": False,
        },
    }


def test_targeted_render_uses_pdf_clip_and_records_inverse_transforms(tmp_path):
    source = tmp_path / "source.pdf"
    _source(source)
    original_hash = sha256_file(source)
    output = tmp_path / "reread" / "page-0001"

    manifest = render_targeted_reread_page(
        source,
        _plan(),
        output,
        expected_source_sha256=original_hash,
        source_identity_path="fixtures/source.pdf",
    )

    assert sha256_file(source) == original_hash
    assert manifest["state"] == "TARGETED_REREAD_INPUTS_RENDERED"
    region = manifest["regions"][0]
    assert region["source_page_bbox_points"] == pytest.approx([20, 10, 180, 80])
    assert region["render"]["width_pixels"] in {1333, 1334}
    assert region["render"]["height_pixels"] in {583, 584}
    assert region["render"]["pixel_to_pdf_points"][0][2] == pytest.approx(20)
    assert region["render"]["pixel_to_baseline_render"][0][2] == pytest.approx(40)
    assert region["variants"][0]["name"] == "original"
    assert region["variants"][0]["geometry_transform_kind"] == "IDENTITY"
    assert region["variants"][0]["pixel_to_pdf_points"][0][2] == pytest.approx(20)
    assert (output / region["variants"][0]["path"]).is_file()
    assert (output / "manifest.json").is_file()
    assert region["selection_status"] == "PENDING_OCR_EVIDENCE"
    assert region["automatic_value_replacement"] is False


def test_targeted_render_retains_inverse_geometry_for_skew_variant(tmp_path, monkeypatch):
    source = tmp_path / "source.pdf"
    _source(source)
    output = tmp_path / "reread"

    from bctc_ai.preprocessing import targeted_render

    original_assess = targeted_render.assess_array

    def skewed_assess(image):
        quality = original_assess(image)
        return quality.__class__(
            **{
                **quality.__dict__,
                "estimated_skew_degrees": 2.0,
                "classifications": ["SKEWED"],
            }
        )

    monkeypatch.setattr(targeted_render, "assess_array", skewed_assess)
    manifest = render_targeted_reread_page(
        source,
        _plan(),
        output,
        expected_source_sha256=sha256_file(source),
        source_identity_path="fixtures/source.pdf",
    )

    variant = next(
        item for item in manifest["regions"][0]["variants"] if item["name"] == "deskewed"
    )
    assert variant["geometry_transform_kind"] == "GEOMETRIC_DESKEW"
    assert variant["transform_to_original_region_pixels"] != [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ]
    assert variant["pixel_to_pdf_points"] != manifest["regions"][0]["render"]["pixel_to_pdf_points"]


def test_targeted_render_refuses_overwrite(tmp_path):
    source = tmp_path / "source.pdf"
    _source(source)
    output = tmp_path / "reread"
    output.mkdir()

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        render_targeted_reread_page(
            source,
            _plan(),
            output,
            expected_source_sha256=sha256_file(source),
            source_identity_path="fixtures/source.pdf",
        )


def test_targeted_render_rejects_automatic_replacement_contract(tmp_path):
    source = tmp_path / "source.pdf"
    _source(source)
    plan = copy.deepcopy(_plan())
    plan["regions"][0]["automatic_value_replacement"] = True

    with pytest.raises(TargetedRereadError, match="replacement policy"):
        render_targeted_reread_page(
            source,
            plan,
            tmp_path / "reread",
            expected_source_sha256=sha256_file(source),
            source_identity_path="fixtures/source.pdf",
        )
