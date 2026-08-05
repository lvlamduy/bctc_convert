from __future__ import annotations

import importlib
import importlib.metadata
import json
import sys
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "config/models/gpu-runtime.toml"


def main() -> int:
    manifest = tomllib.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    expected = manifest["packages"]
    result: dict[str, object] = {
        "status": "FAIL",
        "stage": "import",
        "manifest": MANIFEST_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "packages": {},
    }
    try:
        for distribution, module_name in manifest["import_modules"].items():
            importlib.import_module(module_name)
            installed = importlib.metadata.version(distribution)
            result["packages"][distribution] = installed
            if installed != expected[distribution]:
                raise RuntimeError(
                    f"{distribution} version {installed!r} does not match {expected[distribution]!r}"
                )
        import torch
    except Exception as error:
        result["error"] = str(error)
        print(json.dumps(result, sort_keys=True))
        return 1

    result.update(
        stage="device",
        torch_cuda_build=torch.version.cuda,
        cuda_available=torch.cuda.is_available(),
        architectures=torch.cuda.get_arch_list() if torch.cuda.is_available() else [],
    )
    if not torch.cuda.is_available():
        result["error"] = "CUDA is unavailable"
        print(json.dumps(result, sort_keys=True))
        return 1

    result["device"] = torch.cuda.get_device_name(0)
    result["capability"] = ".".join(map(str, torch.cuda.get_device_capability(0)))
    if manifest["required_native_arch"] not in result["architectures"]:
        result["error"] = f"missing native architecture {manifest['required_native_arch']}"
        print(json.dumps(result, sort_keys=True))
        return 1
    if result["capability"] != manifest["required_compute_capability"]:
        result["error"] = (
            f"device capability {result['capability']} does not match "
            f"{manifest['required_compute_capability']}"
        )
        print(json.dumps(result, sort_keys=True))
        return 1

    try:
        left = torch.arange(4096, device="cuda", dtype=torch.float32).reshape(64, 64)
        output = left @ left.transpose(0, 1)
        torch.cuda.synchronize()
        result["checksum"] = float(output.sum().cpu())
    except Exception as error:
        result.update(stage="kernel", error=str(error))
        print(json.dumps(result, sort_keys=True))
        return 1

    result.update(status="PASS", stage="complete")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
