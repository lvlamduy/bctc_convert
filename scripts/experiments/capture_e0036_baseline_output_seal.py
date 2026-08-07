#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.evaluation.logical_row_label_baseline_seal import (
    seal_logical_row_label_baselines,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hash-seal both reference-blind E-0036 baseline outputs"
    )
    parser.add_argument(
        "--experiment-config",
        type=Path,
        default=Path("config/experiments/e0036-mbb-cdkt-semantic-label-readers.yaml"),
    )
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    seal = seal_logical_row_label_baselines(
        PROJECT_ROOT,
        experiment_config_path=args.experiment_config,
        request_path=args.request,
        output_path=args.output,
    )
    print(
        json.dumps(
            {
                "state": seal["state"],
                "sample_count_per_reader": seal["sample_count_per_reader"],
                "inference_git_commit": seal["inference_git_commit"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
