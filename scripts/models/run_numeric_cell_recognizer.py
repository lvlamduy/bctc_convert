from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.ocr.numeric_cell_reader import run_numeric_cell_reader

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the independent numeric recognizer on fixed cell crops"
    )
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--model-cache", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/models/numeric-recognizer-v1.toml"),
    )
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--cpu-threads", type=int, default=8)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    result = run_numeric_cell_reader(
        PROJECT_ROOT,
        config_path=args.config,
        registry_path=args.registry,
        model_cache=args.model_cache,
        output_directory=args.output_directory,
        batch_size=args.batch_size,
        cpu_threads=args.cpu_threads,
        allow_dirty=args.allow_dirty,
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "output_directory": args.output_directory.as_posix(),
                "metrics": result["metrics"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
