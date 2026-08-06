from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.evaluation.deepseek_line_benchmark import capture_deepseek_line_benchmark

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture E-0026 DeepSeek bounded-line and statement-discovery result"
    )
    parser.add_argument(
        "--experiment-config",
        type=Path,
        default=Path("config/experiments/e0026-deepseek-aspect-preserving-line.yaml"),
    )
    parser.add_argument("--e0025-directory", type=Path, required=True)
    parser.add_argument("--e0026-directory", type=Path, required=True)
    parser.add_argument(
        "--e0013-artifact",
        type=Path,
        default=Path("docs/experiments/E-0013-mbb-vcb-statement-location.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/experiments/E-0026-deepseek-aspect-preserving-line.json"),
    )
    args = parser.parse_args()
    result = capture_deepseek_line_benchmark(
        PROJECT_ROOT,
        experiment_config_path=args.experiment_config,
        e0025_directory=args.e0025_directory,
        e0026_directory=args.e0026_directory,
        e0013_artifact_path=args.e0013_artifact,
        output_path=args.output,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "deepseek": result["readers"]["deepseek_aspect_preserving"]["aggregate"],
                "statement_discovery": result["statement_discovery"]["no_regression_pass"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if result["status"].startswith("PASS_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
