from __future__ import annotations

import json
from pathlib import Path

import pytest

from bctc_ai.evaluation import logical_row_label_request
from bctc_ai.evaluation.logical_row_label_request import (
    LogicalRowLabelRequestError,
    build_logical_row_label_request,
)


def _manifest(crop_path: Path, crop_sha256: str) -> dict:
    sample = {
        "sample_id": "page-0003-row-000-label",
        "category": "LOGICAL_ROW_LABEL",
        "crop_path": crop_path.as_posix(),
        "crop_sha256": crop_sha256,
        "ppocr_text": "forbidden primary text",
        "page": 3,
        "row_ordinal": 0,
    }
    return {
        "format_version": 1,
        "experiment_id": "E-0035",
        "state": "FROZEN_ALL_LOGICAL_ROW_LABEL_CROPS_NO_SEMANTIC_INFERENCE",
        "dataset_role": "CALIBRATION",
        "git_dirty": False,
        "sample_count": 64,
        "decoder_visible_sample_fields": [
            "category",
            "crop_path",
            "crop_sha256",
            "sample_id",
        ],
        "reference_text_available_to_decoder": False,
        "authority": {
            "reader_receives_crop_pixels_only": True,
            "reader_may_change_geometry": False,
            "reader_may_change_numeric_value_or_status": False,
            "reader_may_assign_period_unit_scope_or_schema_id": False,
        },
        "samples": [
            sample | {"sample_id": f"page-0003-row-{index:03d}-label"} for index in range(64)
        ],
    }


def test_request_strips_primary_text_geometry_and_row_metadata(tmp_path, monkeypatch):
    project_root = tmp_path.resolve()
    crop = project_root / "crop.png"
    crop.write_bytes(b"fixed crop")
    from bctc_ai.core.hashing import sha256_file

    payload = _manifest(Path("crop.png"), sha256_file(crop))
    manifest = project_root / "manifest.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(
        logical_row_label_request,
        "_git",
        lambda _root, *arguments: "" if arguments[0] == "status" else "deadbeef",
    )

    request = build_logical_row_label_request(
        project_root,
        crop_manifest_path=Path("manifest.json"),
        output_path=Path("request.json"),
    )

    assert request["experiment_id"] == "E-0036"
    assert request["sample_count"] == 64
    assert set(request["samples"][0]) == {
        "sample_id",
        "category",
        "crop_path",
        "crop_sha256",
    }
    assert "ppocr_text" not in request["samples"][0]
    assert "row_ordinal" not in request["samples"][0]


def test_request_rejects_reference_availability(tmp_path, monkeypatch):
    project_root = tmp_path.resolve()
    crop = project_root / "crop.png"
    crop.write_bytes(b"fixed crop")
    from bctc_ai.core.hashing import sha256_file

    payload = _manifest(Path("crop.png"), sha256_file(crop))
    payload["reference_text_available_to_decoder"] = True
    manifest = project_root / "manifest.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(logical_row_label_request, "_git", lambda *_args: "")

    with pytest.raises(LogicalRowLabelRequestError, match="identity or authority"):
        build_logical_row_label_request(
            project_root,
            crop_manifest_path=Path("manifest.json"),
            output_path=Path("request.json"),
        )
