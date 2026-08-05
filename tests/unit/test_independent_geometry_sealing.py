from __future__ import annotations

import json
from pathlib import Path

import pytest

from bctc_ai.core.hashing import sha256_file
from bctc_ai.evaluation.sealing import (
    IndependentGeometrySealError,
    seal_independent_geometry_run,
)


def _geometry_fixture(tmp_path: Path, *, dirty: bool = False) -> dict[str, Path]:
    render = tmp_path / "output/upstream/renders/page-0001.png"
    render.parent.mkdir(parents=True)
    render.write_bytes(b"render")
    role_b_seal = tmp_path / "output/upstream/role_b_ocr_seal.json"
    role_b_seal.write_text(
        json.dumps(
            {
                "state": "OCR_COMPLETE",
                "dataset_role": "CALIBRATION",
                "source": "input.pdf",
                "source_sha256": "a" * 64,
                "artifact_set_sha256": "b" * 64,
                "pages": [
                    {
                        "page": 1,
                        "render": {
                            "path": render.relative_to(tmp_path).as_posix(),
                            "sha256": sha256_file(render),
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    config = tmp_path / "config/models/pp-ocrv6-word-box.yaml"
    freeze = tmp_path / "config/models/gpu-requirements.freeze.txt"
    runtime = tmp_path / "config/models/gpu-runtime.toml"
    runner = tmp_path / "scripts/models/run_ppocrv6_word_boxes.py"
    implementation = tmp_path / "src/bctc_ai/evaluation/sealing.py"
    for path in (config, freeze, runtime, runner, implementation):
        path.parent.mkdir(parents=True, exist_ok=True)
    config.write_text("pipeline_name: OCR\n", encoding="utf-8")
    freeze.write_text("paddlepaddle==3.3.0\n", encoding="utf-8")
    runner.write_text("# runner\n", encoding="utf-8")
    implementation.write_text("# sealer\n", encoding="utf-8")

    model_cache = tmp_path / "model-cache"
    model_sections = []
    for key, directory in (
        ("pp_ocrv6_medium_det", "PP-OCRv6_medium_det"),
        ("pp_ocrv6_medium_rec", "PP-OCRv6_medium_rec"),
    ):
        weights = model_cache / "official_models" / directory / "inference.pdiparams"
        weights.parent.mkdir(parents=True)
        weights.write_bytes(key.encode())
        model_sections.extend(
            (
                f"[models.{key}]",
                f'repo_id = "owner/{key}"',
                'revision = "revision"',
                f'cache_directory = "{directory}"',
                'weights_file = "inference.pdiparams"',
                f"weights_size_bytes = {weights.stat().st_size}",
                f'weights_sha256 = "{sha256_file(weights)}"',
            )
        )
    runtime.write_text(
        "\n".join((f'freeze_sha256 = "{sha256_file(freeze)}"', *model_sections)) + "\n",
        encoding="utf-8",
    )

    run_root = tmp_path / "output/calibration/geometry"
    page_root = run_root / "ppocrv6-page-0001"
    page_root.mkdir(parents=True)
    result = page_root / "ocr_result.json"
    result.write_text(
        json.dumps(
            {
                "return_word_box": True,
                "rec_texts": ["100"],
                "rec_scores": [0.95],
                "rec_polys": [[[0, 0], [1, 0], [1, 1], [0, 1]]],
                "rec_boxes": [[0, 0, 1, 1]],
                "text_word_boxes": [[[0, 0, 1, 1]]],
                "text_word": [["100"]],
            }
        ),
        encoding="utf-8",
    )
    manifest = page_root / "run_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "state": "OCR_COMPLETE",
                "dataset_role": "CALIBRATION",
                "evidence_role": "INDEPENDENT_GEOMETRY_PROPOSAL_ONLY",
                "code": {"commit": "abc", "dirty": dirty},
                "input": {"path": render.resolve().as_posix(), "sha256": sha256_file(render)},
                "configuration": {
                    "sha256": sha256_file(config),
                    "runner_sha256": sha256_file(runner),
                    "network_policy": "PROCESS_SOCKET_CONNECT_DENIED",
                    "implicit_orientation_or_unwarp": False,
                    "mkldnn": False,
                    "precision": "fp32",
                },
                "runtime": {
                    "manifest_sha256": sha256_file(runtime),
                    "device": "cpu",
                    "compiled_with_cuda": False,
                },
                "artifacts": {
                    "ocr_result": {
                        "path": result.name,
                        "sha256": sha256_file(result),
                    }
                },
                "metrics": {
                    "line_count": 1,
                    "word_token_count": 1,
                    "lines_below_0_8": 0,
                    "lines_below_0_9": 0,
                    "wall_seconds": 1.5,
                },
            }
        ),
        encoding="utf-8",
    )
    return {
        "run_root": run_root,
        "role_b_seal": role_b_seal,
        "model_cache": model_cache,
        "implementation": implementation,
    }


def test_independent_geometry_seal_verifies_axes_inputs_models_and_clean_code(tmp_path: Path):
    fixture = _geometry_fixture(tmp_path)

    sealed = seal_independent_geometry_run(
        tmp_path,
        fixture["run_root"],
        pages=(1,),
        role_b_seal_path=fixture["role_b_seal"],
        model_cache_root=fixture["model_cache"],
        seal_implementation_path=fixture["implementation"],
    )

    assert sealed["state"] == "GEOMETRY_OCR_COMPLETE"
    assert sealed["metrics"]["line_count"] == 1
    assert sealed["metrics"]["word_token_count"] == 1
    assert sealed["acceptance"]["automatic_truth_promotion"] is False
    assert (fixture["run_root"] / "role_c_geometry_seal.json").is_file()


def test_independent_geometry_seal_rejects_dirty_inference(tmp_path: Path):
    fixture = _geometry_fixture(tmp_path, dirty=True)

    with pytest.raises(IndependentGeometrySealError, match="did not use clean code"):
        seal_independent_geometry_run(
            tmp_path,
            fixture["run_root"],
            pages=(1,),
            role_b_seal_path=fixture["role_b_seal"],
            model_cache_root=fixture["model_cache"],
            seal_implementation_path=fixture["implementation"],
        )
