from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.recovery.e0027_reproduction import capture_e0027_reproduction

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture the bounded E-0027 recovery seal")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/recovery/e0027-reproduction-v1.yaml"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/recovery/R-0001-e0027-functional-reproduction.json"),
    )
    args = parser.parse_args()
    result = capture_e0027_reproduction(
        PROJECT_ROOT,
        config_path=args.config,
        output_path=args.output,
    )
    print(
        json.dumps(
            {
                "recovery_id": result["recovery_id"],
                "status": result["status"],
                "stable_metrics_exact": result["stable_metrics_exact"],
                "discovery_result_json_exact": result["discovery_result_json_exact"],
                "page_count": len(result["page_evidence"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
