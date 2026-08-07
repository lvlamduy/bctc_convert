#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.evaluation.logical_row_label_crops import (
    capture_e0035_logical_row_label_crops,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Freeze all E-0033 MBB CDKT logical-row label crops"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/experiments/e0035-mbb-cdkt-logical-row-label-crops.yaml"),
    )
    args = parser.parse_args()
    result = capture_e0035_logical_row_label_crops(
        PROJECT_ROOT,
        config_path=args.config,
    )
    print(
        json.dumps(
            {
                "state": result["state"],
                "sample_count": result["sample_count"],
                "git_commit": result["git_commit"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
