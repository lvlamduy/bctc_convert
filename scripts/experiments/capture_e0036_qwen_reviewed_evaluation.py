#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.evaluation.qwen35_reviewed_evaluation import (
    capture_qwen35_reviewed_evaluation,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate the sealed E-0036 Qwen proposal field on fixed reviewed rows"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/experiments/e0036-qwen-reviewed-evaluation.yaml"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/experiments/E-0036-qwen-reviewed-evaluation.json"),
    )
    args = parser.parse_args()
    result = capture_qwen35_reviewed_evaluation(
        PROJECT_ROOT,
        config_path=args.config,
        output_path=args.output,
    )
    print(
        json.dumps(
            {
                "state": result["state"],
                "decision": result["decision"],
                "valid_proposal_count": result["all_row_proposal_coverage"][
                    "valid_semantic_proposal_count"
                ],
                "reviewed_abstention_count": result["mapping_disposition"][
                    "reviewed_mapping_abstention_count"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
