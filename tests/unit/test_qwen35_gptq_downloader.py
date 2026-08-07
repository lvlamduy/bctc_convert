from __future__ import annotations

import importlib.util
import tomllib
from pathlib import Path
from types import ModuleType

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_downloader() -> ModuleType:
    path = PROJECT_ROOT / "scripts/bootstrap/download_qwen35_gptq.py"
    spec = importlib.util.spec_from_file_location("qwen35_gptq_downloader", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


downloader = _load_downloader()


def test_qwen35_gptq_manifest_is_hash_pinned_and_has_no_pipeline_authority():
    config = downloader._load_config(downloader.DEFAULT_CONFIG)

    assert config["model"]["revision"] == "8f0c09f227ae570e79617c6d9172b59df9c16081"
    assert config["quantization"]["backend"] == "gptq_triton"
    assert config["quantization"]["loader"] == "GPTQModel.from_quantized"
    assert len(config["artifacts"]) == 24
    assert config["required_artifact_bytes"] == sum(
        artifact["size_bytes"] for artifact in config["artifacts"].values()
    )
    assert not any(config["safety"].values())
    assert config["inference"]["target_policy"] == (
        "UNCHANGED_E0036_FROZEN_64_LOGICAL_ROW_LABEL_CROPS_ONLY"
    )


def test_qwen35_gptq_verifier_rejects_hash_mismatch(tmp_path: Path):
    artifact = tmp_path / "model.safetensors"
    artifact.write_bytes(b"wrong")
    config = {
        "model": {"repo_id": "owner/model", "revision": "a" * 40},
        "required_artifact_bytes": artifact.stat().st_size,
        "artifacts": {
            "weights": {
                "path": artifact.name,
                "size_bytes": artifact.stat().st_size,
                "sha256": "0" * 64,
            }
        },
    }

    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        downloader._verify_model(tmp_path, config)


def test_qwen35_gptq_verifier_rejects_unregistered_files(tmp_path: Path):
    artifact = tmp_path / "model.safetensors"
    artifact.write_bytes(b"pinned")
    config = {
        "model": {"repo_id": "owner/model", "revision": "a" * 40},
        "required_artifact_bytes": artifact.stat().st_size,
        "artifacts": {
            "weights": {
                "path": artifact.name,
                "size_bytes": artifact.stat().st_size,
                "sha256": downloader._sha256_file(artifact),
            }
        },
    }
    (tmp_path / "quantize_config.json").write_text("{}", encoding="utf-8")

    with pytest.raises(RuntimeError, match="exact registered file set"):
        downloader._verify_model(tmp_path, config)


def test_qwen35_capacity_preflight_counts_registered_partial_files(tmp_path: Path, monkeypatch):
    staging = tmp_path / ".partial"
    staging.mkdir()
    (staging / "part-1").write_bytes(b"12345")
    config = {
        "required_artifact_bytes": 15,
        "minimum_free_bytes_after_download": 10,
        "artifacts": {
            "one": {"path": "part-1", "size_bytes": 5},
            "two": {"path": "part-2", "size_bytes": 10},
        },
    }

    class Usage:
        total = 100
        used = 80
        free = 20

    monkeypatch.setattr(downloader.shutil, "disk_usage", lambda _path: Usage())
    result = downloader._preflight_capacity(tmp_path, config, staging=staging)

    assert result["registered_complete_bytes_already_present"] == 5
    assert result["remaining_registered_bytes"] == 10

    (staging / "part-1").write_bytes(b"1234")
    with pytest.raises(RuntimeError, match="insufficient cache filesystem space"):
        downloader._preflight_capacity(tmp_path, config, staging=staging)


def test_qwen35_toml_inventory_matches_declared_selected_artifacts():
    config = tomllib.loads(downloader.DEFAULT_CONFIG.read_text(encoding="utf-8"))

    assert config["required_artifact_bytes"] == 30_258_477_628
    assert (
        sum(
            artifact["size_bytes"]
            for key, artifact in config["artifacts"].items()
            if key.startswith("weights_0")
        )
        == 30_235_264_416
    )
