#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.evaluation.e0038_reviewed_evaluation import (
    capture_e0038_reviewed_evaluation,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the sealed E-0038 mapping and evaluate only its fixed six "
            "pre-existing reviewed MBB rows"
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/experiments/e0038-mbb-cdkt-reviewed-evaluation.yaml"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/experiments/E-0038-mbb-cdkt-reviewed-evaluation.json"),
    )
    arguments = parser.parse_args()
    result = capture_e0038_reviewed_evaluation(
        PROJECT_ROOT,
        config_path=arguments.config,
        output_path=arguments.output,
    )
    reviewed = result["reviewed_mapping_evaluation"]
    coverage = reviewed["coverage_limits"]
    print(
        json.dumps(
            {
                "state": result["state"],
                "mechanism_calibration_gate": result["mechanism_calibration_gate"],
                "reviewed_exact_count": reviewed["exact_report_norm_id_count"],
                "reviewed_row_count": reviewed["reviewed_row_count"],
                "changed_alias_target_reviewed_count": coverage[
                    "changed_alias_target_reviewed_count"
                ],
                "unselected_row_reviewed_count": coverage["unselected_row_reviewed_count"],
                "automatic_mapping_adoption": result["conclusion"]["automatic_mapping_adoption"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
