from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml
from PIL import Image

from bctc_ai.evaluation.line_crop_registry import (
    LineCropRegistryError,
    build_line_crop_registry,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path, monkeypatch, *, unsafe: bool = False) -> Path:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"source")
    render_root = tmp_path / "renders"
    render_root.mkdir()
    render = render_root / "page-0001.png"
    Image.new("RGB", (100, 40), "white").save(render)
    ppocr_root = tmp_path / "ppocr"
    result_root = ppocr_root / "ppocrv6-page-0001"
    result_root.mkdir(parents=True)
    result = result_root / "ocr_result.json"
    result.write_text(
        json.dumps(
            {
                "rec_boxes": [[10, 10, 80, 30]],
                "rec_texts": ["Bao cao tai chinh"],
                "rec_scores": [0.9],
            }
        ),
        encoding="utf-8",
    )
    authority = {
        "source_render_is_ground_truth": True,
        "expected_text_is_evaluation_only": True,
        "expected_text_must_not_enter_decoder": True,
        "semantic_reader_may_read_headings_and_labels_only": True,
        "semantic_reader_may_create_numeric_geometry": unsafe,
        "semantic_reader_may_replace_digits_periods_units_or_signs": False,
        "ppocrv6_remains_geometry_and_numeric_authority": True,
        "automatic_ocr_post_correction": False,
    }
    config = {
        "version": 1,
        "experiment_id": "E-0024",
        "dataset_role": "LOGIC_DEVELOPMENT_AND_CALIBRATION",
        "selection_policy": "FROZEN_BEFORE_CHALLENGER_INFERENCE_SOURCE_VISIBLE_SINGLE_LINES",
        "forbidden_holdout_sha256": [],
        "authority": authority,
        "crop_policy": {
            "source_padding_left_top_right_bottom": [2, 1, 2, 1],
            "white_border_left_top_right_bottom": [3, 2, 3, 2],
            "color_mode": "RGB",
            "image_format": "PNG",
            "reject_numeric_only_samples": True,
        },
        "documents": {
            "DOC": {
                "source_pdf": source.name,
                "source_sha256": _sha(source),
                "source_size_bytes": source.stat().st_size,
                "render_root": render_root.name,
                "ppocr_root": ppocr_root.name,
                "pages": {
                    1: {
                        "render_sha256": _sha(render),
                        "ppocr_sha256": _sha(result),
                    }
                },
            }
        },
        "samples": [
            {
                "id": "line-1",
                "document": "DOC",
                "page": 1,
                "category": "TITLE",
                "ppocr_index": 0,
                "bbox": [10, 10, 80, 30],
                "expected": "Báo cáo tài chính",
                "ppocr_text": "Bao cao tai chinh",
            }
        ],
        "expected_sample_count": 1,
        "output_root": "output/crops",
        "claim_boundary": "calibration only",
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    monkeypatch.setattr(
        "bctc_ai.evaluation.line_crop_registry._git",
        lambda _root, *args: "" if args[0] == "status" else "deadbeef",
    )
    return config_path


def test_builds_hash_bound_crop_and_manifest(tmp_path, monkeypatch):
    config = _fixture(tmp_path, monkeypatch)

    result = build_line_crop_registry(tmp_path, config_path=Path(config.name))

    assert result["state"] == "FROZEN_CROPS_BUILT_NO_CHALLENGER_INFERENCE"
    assert result["sample_count"] == 1
    sample = result["samples"][0]
    assert sample["source_crop_bbox"] == [8, 9, 82, 31]
    assert (sample["crop_width"], sample["crop_height"]) == (80, 26)
    assert _sha(tmp_path / sample["crop_path"]) == sample["crop_sha256"]


def test_rejects_semantic_reader_numeric_geometry_authority(tmp_path, monkeypatch):
    config = _fixture(tmp_path, monkeypatch, unsafe=True)

    with pytest.raises(LineCropRegistryError, match="unsafe reader powers"):
        build_line_crop_registry(tmp_path, config_path=Path(config.name))


def test_rejects_ppocr_anchor_drift(tmp_path, monkeypatch):
    config = _fixture(tmp_path, monkeypatch)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    payload["samples"][0]["ppocr_text"] = "drifted"
    config.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")

    with pytest.raises(LineCropRegistryError, match="PP-OCR text drifted"):
        build_line_crop_registry(tmp_path, config_path=Path(config.name))
