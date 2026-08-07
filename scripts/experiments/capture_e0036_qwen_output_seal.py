#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.evaluation.qwen35_logical_row_output_seal import (
    seal_qwen35_logical_row_output,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hash-seal the canonical reference-blind E-0036 Qwen output"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/models/qwen35-27b-gptq-int4-rtx4090-v1.toml"),
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("output/calibration/e0036-mbb-cdkt-semantic-label-readers/qwen-reader"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/experiments/E-0036-qwen-output-seal.json"),
    )
    args = parser.parse_args()
    seal = seal_qwen35_logical_row_output(
        PROJECT_ROOT,
        config_path=args.config,
        output_directory=args.output_directory,
        output_path=args.output,
    )
    print(
        json.dumps(
            {
                "state": seal["state"],
                "sample_count": seal["reader"]["sample_count"],
                "inference_git_commit": seal["inference_git_commit"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
