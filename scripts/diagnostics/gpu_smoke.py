from __future__ import annotations

import json
import sys


def main() -> int:
    try:
        import torch
    except Exception as error:
        print(json.dumps({"status": "FAIL", "stage": "import", "error": str(error)}))
        return 1
    result = {
        "torch_version": torch.__version__,
        "torch_cuda_build": torch.version.cuda,
        "cuda_available": torch.cuda.is_available(),
        "architectures": torch.cuda.get_arch_list() if torch.cuda.is_available() else [],
    }
    if not torch.cuda.is_available():
        result.update(status="FAIL", stage="device", error="CUDA is unavailable")
        print(json.dumps(result, sort_keys=True))
        return 1
    result["device"] = torch.cuda.get_device_name(0)
    result["capability"] = ".".join(map(str, torch.cuda.get_device_capability(0)))
    try:
        left = torch.arange(4096, device="cuda", dtype=torch.float32).reshape(64, 64)
        right = left.transpose(0, 1)
        output = left @ right
        torch.cuda.synchronize()
        result["checksum"] = float(output.sum().cpu())
    except Exception as error:
        result.update(status="FAIL", stage="kernel", error=str(error))
        print(json.dumps(result, sort_keys=True))
        return 1
    result.update(status="PASS", stage="complete")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
