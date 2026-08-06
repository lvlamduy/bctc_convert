from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.evaluation.calibration_discovery_control import (
    capture_e0027_role_b_discovery,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture the reference-blind E-0027 statement-discovery v3 baseline"
    )
    parser.add_argument(
        "--experiment-config",
        type=Path,
        default=Path("config/experiments/e0027-mbb-q1-2026-end-to-end.yaml"),
    )
    parser.add_argument("--batch-root", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/experiments/E-0027-mbb-q1-2026-role-b-discovery-v3.json"),
    )
    args = parser.parse_args()
    result = capture_e0027_role_b_discovery(
        PROJECT_ROOT,
        experiment_config_path=args.experiment_config,
        batch_root=args.batch_root,
        output_path=args.output,
    )
    print(json.dumps(result["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
