from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.ocr.deepseek_line_reader import run_deepseek_line_reader

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run pinned DeepSeek-OCR-2 once over reference-blind bounded line crops"
    )
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--model-cache-root", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/models/deepseek-ocr2-line-v1.toml"),
    )
    args = parser.parse_args()
    manifest = run_deepseek_line_reader(
        PROJECT_ROOT,
        request_path=args.request,
        output_directory=args.output_directory,
        model_cache_root=args.model_cache_root,
        config_path=args.config,
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "output_directory": args.output_directory.as_posix(),
                "metrics": manifest["metrics"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
