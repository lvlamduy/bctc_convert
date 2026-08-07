#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.evaluation.e0039_review_packet import capture_e0039_review_packet

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Capture the answer-free E-0039 six-row review and separate two-alias "
            "schema-steward evidence packet"
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/experiments/e0039-mbb-cdkt-review-packet.yaml"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/calibration/e0039-mbb-cdkt-review-packet/evidence_packet.json"),
    )
    arguments = parser.parse_args()
    result = capture_e0039_review_packet(
        PROJECT_ROOT,
        config_path=arguments.config,
        output_path=arguments.output,
    )
    print(
        json.dumps(
            {
                "state": result["state"],
                "unselected_row_count": result["row_review_packet"]["row_count"],
                "alias_hypothesis_count": result["alias_steward_packet"]["candidate_count"],
                "row_decision_status": result["row_review_packet"]["decision_status"],
                "alias_decision_status": result["alias_steward_packet"]["decision_status"],
                "automatic_mapping_adoption": result["authority"]["automatic_mapping_adoption"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
