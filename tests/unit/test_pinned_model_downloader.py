from __future__ import annotations

import importlib.util
import tomllib
from pathlib import Path
from types import ModuleType

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_downloader() -> ModuleType:
    path = PROJECT_ROOT / "scripts/bootstrap/download_paddleocr_vl_models.py"
    spec = importlib.util.spec_from_file_location("pinned_model_downloader", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


downloader = _load_downloader()


def test_every_downloaded_model_has_a_complete_integrity_pin():
    manifest = tomllib.loads(downloader.RUNTIME_MANIFEST.read_text(encoding="utf-8"))

    for key in downloader.MODEL_KEYS:
        model = manifest["models"][key]
        assert model["repo_id"]
        assert len(model["revision"]) == 40
        assert model["total_bytes"] > 0
        assert model["weights_size_bytes"] > 0
        assert len(model["weights_sha256"]) == 64
        assert model["license"] == "Apache-2.0"


def test_verify_model_rejects_a_weight_hash_mismatch(tmp_path: Path):
    weights = tmp_path / "model.bin"
    weights.write_bytes(b"not-the-pinned-weights")
    config = {
        "repo_id": "owner/model",
        "revision": "a" * 40,
        "weights_file": weights.name,
        "weights_size_bytes": weights.stat().st_size,
        "weights_sha256": "0" * 64,
    }

    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        downloader._verify_model(tmp_path, config)
