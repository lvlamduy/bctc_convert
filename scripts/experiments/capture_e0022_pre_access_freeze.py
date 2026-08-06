from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bctc_ai.evaluation.holdout_freeze import capture_pre_access_holdout_freeze  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture E-0022 pre-access holdout freeze")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/experiments/e0022-acb-q1-2026-untouched-holdout.yaml"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/experiments/E-0022-pre-access-holdout-freeze.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = capture_pre_access_holdout_freeze(
        PROJECT_ROOT,
        config_path=args.config,
        output_path=args.output,
    )
    print(
        json.dumps(
            {
                "state": result["state"],
                "all_sources_locally_absent": result["all_sources_locally_absent"],
                "role_a_access_permitted": result["role_a_access_permitted"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
