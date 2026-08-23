from __future__ import annotations

import hashlib
import importlib.util
import io
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _ROOT / "scripts/experiments/loan_type_missing_cell_evidence_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "loan_type_missing_cell_evidence_v1_test", _MODULE_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
evidence_v1 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = evidence_v1
_SPEC.loader.exec_module(evidence_v1)


def _pages() -> list[dict[str, object]]:
    return [
        {
            "lines": [
                {
                    "bbox": [10, 20, 80, 30],
                    "line_ordinal": 1,
                    "numeric_recognition": {"raw_prediction": "Khoan vay"},
                    "vietocr_text": "Khoản vay",
                },
                {
                    "bbox": [100, 20, 120, 30],
                    "line_ordinal": 2,
                    "numeric_recognition": {"raw_prediction": "3"},
                    "vietocr_text": "3",
                },
            ],
            "page_sequence": 1,
            "page_width": 200,
        }
    ]


def _base(*, total: int) -> dict[str, object]:
    return {
        "intermediate_subtotals": [],
        "lane_types": ["MONEY", "MONEY"],
        "result_id": "ltnrrv1:result:base",
        "rows": [
            {
                "cells": [
                    {
                        "lane_index": 0,
                        "lane_type": "MONEY",
                        "parsed_value": 3,
                        "ppocrv6_surface": "3",
                        "semantic_surface": "3",
                        "source_line_index": 2,
                        "status": "PP_OCRV6_NUMERIC_PROPOSAL",
                    },
                    {
                        "lane_index": 1,
                        "lane_type": "MONEY",
                        "parsed_value": None,
                        "ppocrv6_surface": None,
                        "semantic_surface": None,
                        "source_line_index": None,
                        "status": "MISSING_CELL_REQUIRES_VISIBLE_DASH_OR_NUMERIC_RESCUE",
                    },
                ],
                "label": {
                    "bbox": [10, 20, 80, 30],
                    "source_line_indices": [1],
                    "surface": "Khoản vay",
                },
                "role": "OTHER",
            }
        ],
        "total": [
            {"parsed_value": 3},
            {"parsed_value": total},
        ],
        "unmodelled_additive_rows": [],
    }


def _graph() -> dict[str, object]:
    return {
        "graphs": [
            {
                "lane_centers_x2": [220, 320],
                "page_sequence": 1,
            }
        ]
    }


def _patch_common(monkeypatch, *, total: int, crop: bytes) -> None:
    monkeypatch.setattr(
        evidence_v1.numeric_v1,
        "build_loan_type_numeric_row_reconciliation_v1",
        lambda _pages: _base(total=total),
    )
    monkeypatch.setattr(
        evidence_v1.graph_v1,
        "build_loan_type_variant_graph_document_v1",
        lambda *_args, **_kwargs: _graph(),
    )
    monkeypatch.setattr(
        evidence_v1.region_v1,
        "_validated_render_snapshot",
        lambda _snapshot: (
            {
                "physical_page": 1,
                "render_ref": {"pixel_height": 100, "pixel_width": 200},
            },
            b"render",
        ),
    )
    monkeypatch.setattr(
        evidence_v1,
        "propose_missing_value_lane_regions_v1",
        lambda *_args, **_kwargs: [{"column_ordinal": 1, "raw_pixel_bbox": [130, 15, 180, 40]}],
    )
    monkeypatch.setattr(
        evidence_v1.region_v1,
        "_crop_authenticated_family_first_page_render_snapshot_v1",
        lambda *_args, **_kwargs: {
            "recognition_raw_pixel_bbox": [140, 20, 160, 30],
            "region_id": "region",
            "region_png_bytes": crop,
            "region_png_ref": {
                "sha256": hashlib.sha256(crop).hexdigest(),
                "size_bytes": len(crop),
            },
        },
    )


def test_direct_visible_dash_is_the_only_zero_evidence(monkeypatch) -> None:
    _patch_common(monkeypatch, total=0, crop=b"dash")
    monkeypatch.setattr(
        evidence_v1,
        "build_family_first_visible_dash_glyph_evidence_v1",
        lambda **_kwargs: {"classification": "VISIBLE_HORIZONTAL_DASH_GLYPH"},
    )

    result = evidence_v1.build_loan_type_missing_cell_evidence_v1(_pages(), {"snapshot": True})

    assert result["status"] == "PIXEL_AND_PP_NUMERIC_EXACT"
    assert result["rows"][0]["cells"][1]["parsed_value"] == 0
    assert result["evidence"][0]["selection"] == "DIRECT_GRID_REGION"
    assert result["authority"]["blank_cell_means_zero"] is False


def test_reference_blind_same_crop_digit_rescue_requires_exact_crop_hash(monkeypatch) -> None:
    crop = b"numeric-two"
    _patch_common(monkeypatch, total=2, crop=crop)
    monkeypatch.setattr(
        evidence_v1,
        "build_family_first_visible_dash_glyph_evidence_v1",
        lambda **_kwargs: {"classification": "NO_VISIBLE_DASH"},
    )
    monkeypatch.setattr(evidence_v1, "_tight_dash_bbox", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        evidence_v1,
        "build_family_first_ppocrv6_numeric_cell_evidence_v1",
        lambda **_kwargs: {
            "parsed_token": {
                "classification": "SIGNED_NUMBER",
                "coefficient": 2,
                "scale": 0,
            }
        },
    )
    rescue = {
        "crop_sha256": hashlib.sha256(crop).hexdigest(),
        "lane_index": 1,
        "page_sequence": 1,
        "raw_prediction": "2",
        "reader_score": 0.999,
        "role": "OTHER",
    }

    result = evidence_v1.build_loan_type_missing_cell_evidence_v1(
        _pages(), {"snapshot": True}, numeric_rescue_observations=(rescue,)
    )
    assert result["status"] == "PIXEL_AND_PP_NUMERIC_EXACT"
    assert result["rows"][0]["cells"][1]["parsed_value"] == 2
    assert result["evidence"][0]["classification"] == ("TARGETED_SAME_CROP_PPOCRV6_NUMERIC_RESCUE")

    tampered = dict(rescue)
    tampered["crop_sha256"] = "0" * 64
    with pytest.raises(evidence_v1.LoanTypeMissingCellEvidenceV1Error):
        evidence_v1.build_loan_type_missing_cell_evidence_v1(
            _pages(), {"snapshot": True}, numeric_rescue_observations=(tampered,)
        )


def test_dash_component_selector_ignores_table_rule_and_uses_row_baseline() -> None:
    image = Image.new("RGB", (120, 100), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 24, 109, 25), fill="black")
    draw.rectangle((54, 58, 65, 60), fill="black")
    stream = io.BytesIO()
    image.save(stream, format="PNG", optimize=False, compress_level=9)

    assert evidence_v1._tight_dash_bbox(
        stream.getvalue(), [10, 20, 110, 90], label_baseline_y=59
    ) == [40, 50, 80, 69]
