from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bctc_ai.evaluation.ordered_subgraph_evaluation import (  # noqa: E402
    capture_ordered_subgraph_evaluation,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate E-0023 ordered SchemaGraph mapping")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/experiments/e0023-ordered-schema-graph.yaml"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/experiments/E-0023-ordered-schema-graph.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = capture_ordered_subgraph_evaluation(
        PROJECT_ROOT,
        config_path=args.config,
        output_path=args.output,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "baseline_precision": result["metrics"]["baseline"]["precision"],
                "ordered_precision": result["metrics"]["ordered_subgraph"]["precision"],
                "score_margin": result["ordered_subgraph"]["score_margin"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
