from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bctc_ai.evaluation.targeted_fusion_evaluation import (  # noqa: E402
    evaluate_targeted_fixed_grid_fusion,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate E-0019 fixed-grid semantic fusion")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/experiments/e0019-fixed-grid-semantic-fusion-tcb-lctt.yaml"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/experiments/E-0019-fixed-grid-semantic-fusion-tcb-lctt.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = evaluate_targeted_fixed_grid_fusion(
        PROJECT_ROOT,
        experiment_config=args.config,
        output=args.output,
    )
    print(json.dumps(result["delta"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
