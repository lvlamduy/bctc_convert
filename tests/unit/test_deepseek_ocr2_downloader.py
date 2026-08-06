from __future__ import annotations

import importlib.util
import tomllib
from pathlib import Path
from types import ModuleType

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_downloader() -> ModuleType:
    path = PROJECT_ROOT / "scripts/bootstrap/download_deepseek_ocr2.py"
    spec = importlib.util.spec_from_file_location("deepseek_ocr2_downloader", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


downloader = _load_downloader()


def test_deepseek_ocr2_manifest_is_pinned_and_has_no_pipeline_authority():
    config = tomllib.loads(downloader.DEFAULT_CONFIG.read_text(encoding="utf-8"))

    assert len(config["model"]["revision"]) == 40
    assert config["required_artifact_bytes"] == sum(
        artifact["size_bytes"] for artifact in config["artifacts"].values()
    )
    assert config["artifacts"]["weights"] == {
        "path": "model-00001-of-000001.safetensors",
        "size_bytes": 6778573880,
        "sha256": "d8ff67a424ba6f4dd077885eb9d6a05d2537e76fe5491f0e2a9b712f8c8870fa",
    }
    assert not any(config["safety"].values())
    assert config["inference"]["target_policy"] == "FAILED_OR_AMBIGUOUS_REGIONS_ONLY"


def test_deepseek_ocr2_verifier_rejects_hash_mismatch(tmp_path: Path):
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


def test_deepseek_ocr2_capacity_preflight_keeps_reserve(tmp_path: Path, monkeypatch):
    class Usage:
        total = 100
        used = 80
        free = 20

    monkeypatch.setattr(downloader.shutil, "disk_usage", lambda _path: Usage())

    with pytest.raises(RuntimeError, match="insufficient cache filesystem space"):
        downloader._preflight_capacity(
            tmp_path,
            {
                "required_artifact_bytes": 15,
                "minimum_free_bytes_after_download": 10,
            },
        )
