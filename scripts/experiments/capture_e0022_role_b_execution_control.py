from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bctc_ai.evaluation.holdout_execution import capture_role_b_execution_control  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture E-0022 Role B execution control")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/experiments/e0022-role-b-execution-control.yaml"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/experiments/E-0022-role-b-execution-control.json"),
    )
    args = parser.parse_args()
    result = capture_role_b_execution_control(
        PROJECT_ROOT,
        config_path=args.config,
        output_path=args.output,
    )
    print(
        json.dumps(
            {
                "state": result["state"],
                "role_a_access_permitted": result["role_a_access_permitted"],
                "allowed_next_action": result["allowed_next_action"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
