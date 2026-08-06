from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bctc_ai.evaluation.holdout_statement_diagnosis import (  # noqa: E402
    capture_e0022_statement_diagnosis,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture E-0022 statement discovery diagnosis")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/experiments/e0022-role-a-statement-diagnosis.yaml"),
    )
    args = parser.parse_args()
    result = capture_e0022_statement_diagnosis(PROJECT_ROOT, config_path=args.config)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
