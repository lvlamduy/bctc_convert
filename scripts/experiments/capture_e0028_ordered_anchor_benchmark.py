from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.evaluation.ordered_anchor_locator_benchmark import (
    capture_e0028_ordered_anchor_benchmark,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture frozen E-0028 bounded ordered-anchor locator calibration"
    )
    parser.add_argument(
        "--experiment-config",
        type=Path,
        default=Path("config/experiments/e0028-bounded-ordered-anchor-locator.yaml"),
    )
    parser.add_argument("--batch-root", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/experiments/E-0028-bounded-ordered-anchor-locator.json"),
    )
    args = parser.parse_args()
    result = capture_e0028_ordered_anchor_benchmark(
        PROJECT_ROOT,
        experiment_config_path=args.experiment_config,
        batch_root=args.batch_root,
        output_path=args.output,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "before": result["before"],
                "after": result["after"],
                "target_gates": result["target_gates"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if result["status"].startswith("PASS_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
