from __future__ import annotations

import json
from pathlib import Path

import pytest

from bctc_ai.core.hashing import sha256_file
from bctc_ai.document_phase.statement_evidence import (
    StatementEvidenceError,
    load_ocr_pages_from_batch,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


def _fixture(tmp_path: Path) -> Path:
    batch_root = tmp_path / "batch"
    page_root = batch_root / "ppocrv6-page-0001"
    source_path = tmp_path / "source.pdf"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(b"frozen-source")
    source_sha256 = sha256_file(source_path)
    render_path = tmp_path / "renders/page-0001.png"
    render_path.parent.mkdir(parents=True)
    render_path.write_bytes(b"frozen-render")
    render_sha256 = sha256_file(render_path)

    preprocess_render = {
        "page": 1,
        "path": render_path.as_posix(),
        "sha256": render_sha256,
        "source_sha256": source_sha256,
        "dpi": 120,
        "rotation": 0,
        "width_pixels": 1000,
        "height_pixels": 1400,
    }
    batch_render = {
        key: value for key, value in preprocess_render.items() if key != "source_sha256"
    }
    batch_render["size_bytes"] = render_path.stat().st_size
    preprocess_path = tmp_path / "preprocess/manifest.json"
    _write_json(
        preprocess_path,
        {
            "state": "PREPROCESSED",
            "dataset_role": "CALIBRATION",
            "source_sha256": source_sha256,
            "code": {"git_dirty": False},
            "pages": [{"page": 1, "render": preprocess_render}],
        },
    )

    result_path = page_root / "ocr_result.json"
    _write_json(
        result_path,
        {
            "rec_texts": ["Báo cáo tình hình tài chính", "100"],
            "rec_boxes": [[100, 40, 700, 80], [700, 400, 850, 430]],
            "rec_scores": [0.99, 0.98],
        },
    )
    result_sha256 = sha256_file(result_path)
    identity = "a" * 64
    run_manifest_path = page_root / "run_manifest.json"
    _write_json(
        run_manifest_path,
        {
            "state": "OCR_COMPLETE",
            "batch_identity": identity,
            "page": 1,
            "dataset_role": "CALIBRATION",
            "input": batch_render,
            "artifacts": {
                "ocr_result": {
                    "path": "ocr_result.json",
                    "sha256": result_sha256,
                }
            },
        },
    )
    _write_json(
        batch_root / "batch_manifest.json",
        {
            "state": "PARTIAL",
            "batch_identity": identity,
            "dataset_role": "CALIBRATION",
            "source": {"path": source_path.as_posix(), "sha256": source_sha256},
            "dataset_registration": {
                "immutable": True,
                "dataset_role": "CALIBRATION",
                "document_id": f"sha256:{source_sha256}",
                "source_path": source_path.as_posix(),
            },
            "code": {"dirty": False},
            "requested_pages": [1],
            "input_manifest": {
                "path": preprocess_path.as_posix(),
                "sha256": sha256_file(preprocess_path),
            },
            "renders": [batch_render],
            "pages": [
                {
                    "page": 1,
                    "run_manifest": {
                        "path": "ppocrv6-page-0001/run_manifest.json",
                        "sha256": sha256_file(run_manifest_path),
                    },
                    "ocr_result": {
                        "path": "ppocrv6-page-0001/ocr_result.json",
                        "sha256": result_sha256,
                    },
                }
            ],
        },
    )
    return batch_root


def test_load_pages_verifies_complete_identity_chain(tmp_path):
    batch_root = _fixture(tmp_path)

    batch, pages = load_ocr_pages_from_batch(batch_root, project_root=tmp_path)

    assert batch["batch_identity"] == "a" * 64
    assert len(pages) == 1
    assert pages[0].page == 1
    assert pages[0].width == 1000
    assert tuple(line.text for line in pages[0].lines) == (
        "Báo cáo tình hình tài chính",
        "100",
    )


def test_load_pages_rejects_batch_path_escape(tmp_path):
    batch_root = _fixture(tmp_path)
    batch_path = batch_root / "batch_manifest.json"
    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    original = batch_root / batch["pages"][0]["run_manifest"]["path"]
    outside = batch_root.parent / "outside-run-manifest.json"
    outside.write_bytes(original.read_bytes())
    batch["pages"][0]["run_manifest"] = {
        "path": "../outside-run-manifest.json",
        "sha256": sha256_file(outside),
    }
    _write_json(batch_path, batch)

    with pytest.raises(StatementEvidenceError, match="escapes or is absent"):
        load_ocr_pages_from_batch(batch_root, project_root=tmp_path)


def test_load_pages_rejects_hash_and_render_identity_drift(tmp_path):
    batch_root = _fixture(tmp_path)
    result_path = batch_root / "ppocrv6-page-0001/ocr_result.json"
    result_path.write_text("{}", encoding="utf-8")

    with pytest.raises(StatementEvidenceError, match="result hash drift"):
        load_ocr_pages_from_batch(batch_root, project_root=tmp_path)

    batch_root = _fixture(tmp_path / "second")
    run_path = batch_root / "ppocrv6-page-0001/run_manifest.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["input"]["width_pixels"] = 999
    _write_json(run_path, run)
    batch_path = batch_root / "batch_manifest.json"
    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    batch["pages"][0]["run_manifest"]["sha256"] = sha256_file(run_path)
    _write_json(batch_path, batch)

    with pytest.raises(StatementEvidenceError, match="render identity drift"):
        load_ocr_pages_from_batch(batch_root, project_root=tmp_path / "second")


def test_load_pages_allows_hash_identical_render_relocation(tmp_path):
    batch_root = _fixture(tmp_path)
    batch_path = batch_root / "batch_manifest.json"
    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    preprocess_path = Path(batch["input_manifest"]["path"])
    preprocess = json.loads(preprocess_path.read_text(encoding="utf-8"))
    preprocess["pages"][0]["render"]["path"] = "/old-server/missing/page-0001.png"
    _write_json(preprocess_path, preprocess)
    batch["input_manifest"]["sha256"] = sha256_file(preprocess_path)
    _write_json(batch_path, batch)

    _, pages = load_ocr_pages_from_batch(batch_root, project_root=tmp_path)

    assert pages[0].page == 1
