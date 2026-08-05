from __future__ import annotations

import importlib.util
import tomllib
from pathlib import Path
from types import ModuleType

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_downloader() -> ModuleType:
    path = PROJECT_ROOT / "scripts/bootstrap/download_paddle_runtime_wheel.py"
    spec = importlib.util.spec_from_file_location("paddle_runtime_downloader", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


downloader = _load_downloader()


def test_paddle_runtime_wheel_has_a_complete_integrity_pin_and_rebuild_link():
    manifest = tomllib.loads(downloader.RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    artifact = manifest["artifacts"][downloader.ARTIFACT_KEY]
    rebuild_script = (PROJECT_ROOT / "scripts/bootstrap/create_gpu_runtime.sh").read_text(
        encoding="utf-8"
    )

    assert artifact["filename"] in artifact["url"]
    assert "scripts/bootstrap/download_paddle_runtime_wheel.py" in rebuild_script
    assert '"paddlepaddle==3.3.0"' in rebuild_script
    assert "--no-index" in rebuild_script
    assert "--no-deps" in rebuild_script
    assert artifact["size_bytes"] > 0
    assert len(artifact["sha256"]) == 64
    assert artifact["license"] == "Apache-2.0"
    assert manifest["paddle_inference_device"] == "cpu"


def test_verify_paddle_runtime_wheel_accepts_only_exact_size_and_hash(tmp_path: Path):
    wheel = tmp_path / "paddle.whl"
    wheel.write_bytes(b"pinned-wheel")
    config = {
        "size_bytes": wheel.stat().st_size,
        "sha256": downloader._sha256(wheel),
    }

    assert downloader._verify(wheel, config)["status"] == "VERIFIED"

    config["sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        downloader._verify(wheel, config)
