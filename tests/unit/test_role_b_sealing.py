from __future__ import annotations

import json
from pathlib import Path

import pytest

from bctc_ai.core.hashing import sha256_file
from bctc_ai.evaluation.sealing import RoleBSealError, seal_role_b_ocr_run


def test_role_b_seal_fails_closed_on_dirty_preprocess_run(tmp_path):
    project_root = tmp_path
    run_root = project_root / "output/calibration/run/document"
    run_root.mkdir(parents=True)
    (run_root / "manifest.json").write_text(
        json.dumps(
            {
                "dataset_role": "CALIBRATION",
                "state": "PREPROCESSED",
                "code": {"git_commit": "abc", "git_dirty": True},
                "pages": [],
            }
        )
    )

    with pytest.raises(RoleBSealError, match="clean Git state"):
        seal_role_b_ocr_run(
            project_root,
            run_root,
            pages=(1,),
            model_cache_root=Path("/missing"),
        )


def test_role_b_seal_refuses_to_overwrite_existing_seal(tmp_path):
    project_root = tmp_path
    run_root = project_root / "output/calibration/run/document"
    run_root.mkdir(parents=True)
    (run_root / "role_b_ocr_seal.json").write_text("{}")

    with pytest.raises(RoleBSealError, match="refusing to overwrite"):
        seal_role_b_ocr_run(
            project_root,
            run_root,
            pages=(1,),
            model_cache_root=Path("/missing"),
        )


def test_role_b_seal_verifies_render_result_runtime_and_model_hashes(tmp_path):
    project_root = tmp_path
    run_root = project_root / "output/calibration/run/document"
    render = run_root / "renders/page-0001.png"
    result = run_root / "ocr/paddleocr-vl-page-0001/page-0001_res.json"
    markdown = result.with_name("page-0001.md")
    metric = run_root / "experiments/paddleocr-vl-page-0001-metrics.json"
    for path in (render, result, markdown, metric):
        path.parent.mkdir(parents=True, exist_ok=True)
    render.write_bytes(b"render")
    result.write_text(
        json.dumps(
            {
                "input_path": render.relative_to(project_root).as_posix(),
                "parsing_res_list": [],
            }
        )
    )
    markdown.write_text("result")
    metric.write_text(
        json.dumps(
            {
                "status": "PASS",
                "return_code": 0,
                "wall_seconds": 1.25,
                "gpu": {"peak_memory_used_mib": 100.0},
            }
        )
    )
    (run_root / "manifest.json").write_text(
        json.dumps(
            {
                "dataset_role": "CALIBRATION",
                "state": "PREPROCESSED",
                "source": "input.pdf",
                "source_sha256": "a" * 64,
                "code": {"git_commit": "abc", "git_dirty": False},
                "pages": [
                    {
                        "page": 1,
                        "render": {
                            "path": render.as_posix(),
                            "sha256": sha256_file(render),
                            "dpi": 200,
                            "rotation": 0,
                        },
                    }
                ],
            }
        )
    )
    config = project_root / "config/models/paddleocr-vl-1.6-transformers.yaml"
    freeze = project_root / "config/models/gpu-requirements.freeze.txt"
    runtime = project_root / "config/models/gpu-runtime.toml"
    implementation = project_root / "src/bctc_ai/evaluation/sealing.py"
    for path in (config, freeze, runtime, implementation):
        path.parent.mkdir(parents=True, exist_ok=True)
    config.write_text("pipeline: test\n")
    freeze.write_text("test==1\n")
    model_cache = project_root / "model-cache"
    weights = model_cache / "official_models/TestModel/model.bin"
    weights.parent.mkdir(parents=True)
    weights.write_bytes(b"weights")
    runtime.write_text(
        "\n".join(
            (
                f'freeze_sha256 = "{sha256_file(freeze)}"',
                "[models.test]",
                'repo_id = "owner/test"',
                'revision = "revision"',
                'cache_directory = "TestModel"',
                'weights_file = "model.bin"',
                f"weights_size_bytes = {weights.stat().st_size}",
                f'weights_sha256 = "{sha256_file(weights)}"',
            )
        )
        + "\n"
    )
    implementation.write_text("# test implementation\n")

    sealed = seal_role_b_ocr_run(
        project_root,
        run_root,
        pages=(1,),
        model_cache_root=model_cache,
        seal_implementation_path=implementation,
    )

    assert sealed["state"] == "OCR_COMPLETE"
    assert sealed["metrics"]["page_count"] == 1
    assert sealed["runtime"]["models"][0]["weights_sha256"] == sha256_file(weights)
    assert (run_root / "role_b_ocr_seal.json").is_file()
