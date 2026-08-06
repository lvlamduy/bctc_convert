from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.line_reader_request import (
    LineReaderRequestError,
    prepare_line_reader_request,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest(tmp_path: Path, *, unsafe: bool = False) -> Path:
    crop = tmp_path / "crop.png"
    crop.write_bytes(b"crop")
    manifest = {
        "experiment_id": "E-0024",
        "state": "FROZEN_CROPS_BUILT_NO_CHALLENGER_INFERENCE",
        "dataset_role": "LOGIC_DEVELOPMENT_AND_CALIBRATION",
        "git_dirty": False,
        "authority": {
            "expected_text_must_not_enter_decoder": True,
            "semantic_reader_may_create_numeric_geometry": unsafe,
            "semantic_reader_may_replace_digits_periods_units_or_signs": False,
        },
        "sample_count": 1,
        "samples": [
            {
                "sample_id": "sample-1",
                "category": "TITLE",
                "crop_path": crop.name,
                "crop_sha256": _sha(crop),
                "expected_text": "must not leak",
                "ppocr_text": "must not leak either",
            }
        ],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_request_contains_only_allowlisted_crop_fields(tmp_path, monkeypatch):
    manifest = _manifest(tmp_path)
    monkeypatch.setattr(
        "bctc_ai.evaluation.line_reader_request._git",
        lambda _root, *args: "" if args[0] == "status" else "deadbeef",
    )

    result = prepare_line_reader_request(
        tmp_path,
        crop_manifest_path=Path(manifest.name),
        output_path=Path("request.json"),
    )

    assert result["reference_text_available_to_reader"] is False
    assert set(result["samples"][0]) == {
        "sample_id",
        "category",
        "crop_path",
        "crop_sha256",
    }
    serialized = json.dumps(result, ensure_ascii=False)
    assert "must not leak" not in serialized
    assert "expected" not in serialized
    assert "ppocr" not in serialized


def test_request_rejects_unsafe_reader_authority(tmp_path, monkeypatch):
    manifest = _manifest(tmp_path, unsafe=True)
    monkeypatch.setattr(
        "bctc_ai.evaluation.line_reader_request._git",
        lambda _root, *args: "" if args[0] == "status" else "deadbeef",
    )

    with pytest.raises(LineReaderRequestError, match="unsafe"):
        prepare_line_reader_request(
            tmp_path,
            crop_manifest_path=Path(manifest.name),
            output_path=Path("request.json"),
        )
