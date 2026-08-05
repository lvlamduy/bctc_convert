from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_runner() -> ModuleType:
    scripts_directory = PROJECT_ROOT / "scripts/models"
    path = scripts_directory / "run_ppocrv6_word_boxes_batch.py"
    sys.path.insert(0, scripts_directory.as_posix())
    try:
        spec = importlib.util.spec_from_file_location("ppocrv6_word_box_batch_runner", path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts_directory.as_posix())


runner = _load_runner()


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _preprocess_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(runner, "PROJECT_ROOT", tmp_path)
    registry = tmp_path / "data/registered/dataset_roles.jsonl"
    monkeypatch.setattr(runner, "DATASET_ROLE_REGISTRY", registry)

    source = tmp_path / "source.pdf"
    source.write_bytes(b"source-pdf")
    source_digest = runner._sha256(source)
    render = tmp_path / "output/calibration/run/document/renders/page-0001.png"
    render.parent.mkdir(parents=True, exist_ok=True)
    render.write_bytes(b"render-page")
    manifest_path = render.parent.parent / "manifest.json"
    manifest = {
        "format_version": 1,
        "state": "PREPROCESSED",
        "dataset_role": "CALIBRATION",
        "source": "/retired/server/source.pdf",
        "source_sha256": source_digest,
        "code": {"git_commit": "abc", "git_dirty": False},
        "pages": [
            {
                "page": 1,
                "render": {
                    "page": 1,
                    "path": "/retired/server/output/run/renders/page-0001.png",
                    "sha256": runner._sha256(render),
                    "source_sha256": source_digest,
                    "dpi": 200,
                    "rotation": 0,
                    "width_pixels": 100,
                    "height_pixels": 200,
                },
            }
        ],
    }
    _write_json(manifest_path, manifest)
    _write_json(
        manifest_path.with_name("run_manifest.json"),
        {
            "manifest": "manifest.json",
            "manifest_sha256": runner._sha256(manifest_path),
            "source_sha256": source_digest,
            "state": "PREPROCESSED",
        },
    )
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(
        json.dumps(
            {
                "document_id": f"sha256:{source_digest}",
                "dataset_role": "CALIBRATION",
                "source_path": "source.pdf",
                "assigned_at": "2026-08-05T00:00:00+00:00",
                "immutable": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest_path


def _valid_result() -> dict[str, object]:
    return {
        "return_word_box": True,
        "rec_texts": ["100"],
        "rec_scores": [0.95],
        "rec_polys": [[[0, 0], [1, 0], [1, 1], [0, 1]]],
        "rec_boxes": [[0, 0, 1, 1]],
        "text_word_boxes": [[[0, 0, 1, 1]]],
        "text_word": [["100"]],
    }


def test_parse_pages_normalizes_ranges_and_rejects_invalid_tokens():
    assert runner._parse_pages("3,1-2,2") == (1, 2, 3)
    assert runner._parse_pages(None) is None

    for value in ("", "1,,2", "0", "3-2", "a", "1-x"):
        with pytest.raises(argparse.ArgumentTypeError):
            runner._parse_pages(value)


def test_preprocess_manifest_resolves_relocated_files_by_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    manifest_path = _preprocess_fixture(tmp_path, monkeypatch)

    source, registration, renders = runner._render_records(manifest_path, None, "CALIBRATION")

    assert source["path"] == "source.pdf"
    assert source["sha256"] == registration["document_id"].removeprefix("sha256:")
    assert registration["immutable"] is True
    assert renders == (
        {
            "page": 1,
            "path": "output/calibration/run/document/renders/page-0001.png",
            "sha256": runner._sha256(
                tmp_path / "output/calibration/run/document/renders/page-0001.png"
            ),
            "size_bytes": 11,
            "dpi": 200,
            "rotation": 0,
            "width_pixels": 100,
            "height_pixels": 200,
        },
    )


def test_preprocess_manifest_cannot_relabel_frozen_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    manifest_path = _preprocess_fixture(tmp_path, monkeypatch)

    with pytest.raises(runner.BatchWordBoxError, match="requested role"):
        runner._render_records(manifest_path, None, "VALIDATION")


def test_preprocess_manifest_rejects_envelope_or_render_hash_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    manifest_path = _preprocess_fixture(tmp_path, monkeypatch)
    envelope_path = manifest_path.with_name("run_manifest.json")
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    envelope["manifest_sha256"] = "0" * 64
    _write_json(envelope_path, envelope)
    with pytest.raises(runner.BatchWordBoxError, match="does not bind"):
        runner._render_records(manifest_path, None, "CALIBRATION")

    _preprocess_fixture(tmp_path, monkeypatch)
    render_path = manifest_path.parent / "renders/page-0001.png"
    render_path.write_bytes(b"drift")
    with pytest.raises(runner.BatchWordBoxError, match="render page 1"):
        runner._render_records(manifest_path, None, "CALIBRATION")


def test_resume_requires_exact_immutable_batch_identity():
    expected = {
        "schema_version": 1,
        "batch_identity": "a" * 64,
        "configuration": {"sha256": "b" * 64},
    }
    state = {**expected, "state": "PARTIAL", "pages": [], "sessions": []}
    runner._validate_resume(state, expected)

    state["configuration"] = {"sha256": "c" * 64}
    with pytest.raises(runner.BatchWordBoxError, match="resume identity mismatch"):
        runner._validate_resume(state, expected)


def test_orphan_page_requires_full_page_identity(tmp_path: Path):
    expected = {
        "schema_version": 1,
        "state": "OCR_COMPLETE",
        "page": 1,
        "dataset_role": "CALIBRATION",
        "evidence_role": "INDEPENDENT_GEOMETRY_PROPOSAL_ONLY",
        "confidence_policy": "NO_AUTOMATIC_TRUTH_OR_SCHEMA_PROMOTION",
        "batch_identity": "a" * 64,
        "input": {"page": 1, "path": "render.png", "sha256": "b" * 64},
        "code": {"commit": "abc", "dirty": False},
        "configuration": {"sha256": "c" * 64},
        "runtime": {"manifest_sha256": "d" * 64},
    }
    manifest = {
        **expected,
        "metrics": {
            "line_count": 1,
            "word_token_count": 1,
            "wall_seconds": 1.0,
            "minimum_line_score": 0.95,
            "mean_line_score": 0.95,
            "lines_below_0_8": 0,
            "lines_below_0_9": 0,
        },
    }
    runner._write_artifacts(tmp_path / "ppocrv6-page-0001", _valid_result(), manifest)
    record = runner._page_output_record(tmp_path, 1, expected)
    assert record["page"] == 1

    changed = {**expected, "configuration": {"sha256": "e" * 64}}
    with pytest.raises(runner.BatchWordBoxError, match="page output identity mismatch"):
        runner._page_output_record(tmp_path, 1, changed)


def test_batch_metrics_keep_all_model_load_sessions():
    records = [
        {
            "metrics": {
                "line_count": 2,
                "word_token_count": 5,
                "wall_seconds": 3.0,
                "minimum_line_score": 0.7,
                "mean_line_score": 0.8,
                "lines_below_0_8": 1,
                "lines_below_0_9": 2,
            }
        },
        {
            "metrics": {
                "line_count": 1,
                "word_token_count": 2,
                "wall_seconds": 4.0,
                "minimum_line_score": 0.9,
                "mean_line_score": 0.95,
                "lines_below_0_8": 0,
                "lines_below_0_9": 0,
            }
        },
    ]
    sessions = [
        {"model_load_wall_seconds": 1.25},
        {"model_load_wall_seconds": 1.5},
    ]

    metrics = runner._aggregate(records, sessions)

    assert metrics["completed_page_count"] == 2
    assert metrics["line_count"] == 3
    assert metrics["word_token_count"] == 7
    assert metrics["page_inference_wall_seconds"] == 7.0
    assert metrics["model_load_session_count"] == 2
    assert metrics["model_load_wall_seconds_total"] == 2.75
    assert metrics["mean_line_score"] == pytest.approx(0.85)


def test_batch_wrapper_exposes_resume_without_model_or_network_downloads():
    wrapper = (PROJECT_ROOT / "scripts/models/run_ppocrv6_word_boxes_batch.sh").read_text(
        encoding="utf-8"
    )

    assert "--preprocess-manifest" in wrapper
    assert "BCTC_BATCH_RESUME" in wrapper
    assert "BCTC_DATASET_ROLE" in wrapper
    assert "BCTC_MODEL_CACHE_DIR" in wrapper
    assert "download" not in wrapper.lower()
