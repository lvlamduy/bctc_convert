from __future__ import annotations

import hashlib
import json
from pathlib import Path

from bctc_ai.core import environment


def _configured_root(root: Path) -> str:
    freeze = "alpha==1.0\nbeta==2.0\n"
    freeze_hash = hashlib.sha256(freeze.encode()).hexdigest()
    manifest = f'''status = "LOGIC_DEVELOPMENT_INFERENCE_PASS_NOT_PRODUCTION_APPROVED"
isolation_directory = ".gpu-venv"
freeze_path = "config/models/gpu-requirements.freeze.txt"
freeze_sha256 = "{freeze_hash}"
cuda_runtime = "13.0"
required_compute_capability = "12.0"
required_native_arch = "sm_120"

[packages]
torch = "2.12.0+cu130"
'''
    (root / "config/models").mkdir(parents=True)
    (root / "config/models/gpu-runtime.toml").write_text(manifest, encoding="utf-8")
    (root / "config/models/gpu-requirements.freeze.txt").write_text(freeze, encoding="utf-8")
    (root / ".gpu-venv/bin").mkdir(parents=True)
    (root / ".gpu-venv/bin/python").touch()
    (root / ".venv/bin").mkdir(parents=True)
    (root / ".venv/bin/uv").touch()
    (root / "scripts/diagnostics").mkdir(parents=True)
    (root / "scripts/diagnostics/gpu_model_runtime_smoke.py").touch()
    return freeze


def test_gpu_runtime_is_not_configured_without_manifest(tmp_path):
    result = environment.collect_gpu_model_runtime(tmp_path)

    assert result["configured"] is False
    assert result["local_acceptance"] == "NOT_CONFIGURED"


def test_gpu_runtime_acceptance_revalidates_smoke_compatibility_and_freeze(tmp_path, monkeypatch):
    freeze = _configured_root(tmp_path)

    def fake_run(command: list[str], *, timeout: int = 20) -> tuple[int, str]:
        assert timeout == 120
        if command[0].endswith("/python"):
            return 0, json.dumps(
                {
                    "status": "PASS",
                    "torch_cuda_build": "13.0",
                    "capability": "12.0",
                    "architectures": ["sm_120"],
                    "packages": {"torch": "2.12.0+cu130"},
                }
            )
        if "check" in command:
            return 0, "All installed packages are compatible"
        if "freeze" in command:
            return 0, freeze.rstrip()
        raise AssertionError(command)

    monkeypatch.setattr(environment, "_run", fake_run)
    result = environment.collect_gpu_model_runtime(tmp_path)

    assert result["local_acceptance"] == "PASS"
    assert result["smoke"]["status"] == "PASS"
    assert result["compatibility"]["status"] == "PASS"
    assert result["freeze"]["manifest_hash_matches"] is True
    assert result["freeze"]["installed_matches_expected"] is True
    assert result["freeze"]["installed_package_count"] == 2


def test_gpu_runtime_acceptance_fails_on_installed_freeze_drift(tmp_path, monkeypatch):
    _configured_root(tmp_path)

    def fake_run(command: list[str], *, timeout: int = 20) -> tuple[int, str]:
        if command[0].endswith("/python"):
            return 0, json.dumps(
                {
                    "status": "PASS",
                    "torch_cuda_build": "13.0",
                    "capability": "12.0",
                    "architectures": ["sm_120"],
                    "packages": {"torch": "2.12.0+cu130"},
                }
            )
        if "check" in command:
            return 0, "compatible"
        if "freeze" in command:
            return 0, "alpha==9.9\nbeta==2.0"
        raise AssertionError(command)

    monkeypatch.setattr(environment, "_run", fake_run)
    result = environment.collect_gpu_model_runtime(tmp_path)

    assert result["local_acceptance"] == "FAIL"
    assert result["freeze"]["installed_matches_expected"] is False
