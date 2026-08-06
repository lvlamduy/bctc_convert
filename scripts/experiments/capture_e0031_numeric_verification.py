#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.evaluation.numeric_cell_verification_benchmark import (
    capture_e0031_numeric_cell_verification_benchmark,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture frozen E-0031 independent numeric-cell verification"
    )
    parser.add_argument(
        "--experiment-config",
        type=Path,
        default=Path("config/experiments/e0031-mbb-cdkt-numeric-verification.yaml"),
    )
    parser.add_argument("--crop-registry", type=Path, required=True)
    parser.add_argument("--reader-output-directory", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/experiments/E-0031-mbb-cdkt-numeric-verification.json"),
    )
    args = parser.parse_args()
    result = capture_e0031_numeric_cell_verification_benchmark(
        PROJECT_ROOT,
        experiment_config_path=args.experiment_config,
        crop_registry_path=args.crop_registry,
        reader_output_directory=args.reader_output_directory,
        output_path=args.output,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "before": result["before"],
                "after_metrics": result["after"]["metrics"],
                "gates": result["gates"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if result["status"].startswith("PASS_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
