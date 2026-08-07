from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from bctc_ai.ocr.qwen35_logical_row_reader import run_qwen35_logical_row_reader

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run pinned Qwen3.5-27B GPTQ-Int4 on E-0036 logical-row crops"
    )
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--model-cache-root", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/models/qwen35-27b-gptq-int4-rtx4090-v1.toml"),
    )
    args = parser.parse_args()
    os.environ["BCTC_QWEN35_ONE_SHOT_WORKER"] = "1"
    manifest = run_qwen35_logical_row_reader(
        PROJECT_ROOT,
        request_path=args.request,
        output_directory=args.output_directory,
        model_cache_root=args.model_cache_root,
        config_path=args.config,
    )
    print(json.dumps({"status": "PASS", "metrics": manifest["metrics"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
