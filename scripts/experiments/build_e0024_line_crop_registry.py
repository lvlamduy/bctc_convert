from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bctc_ai.evaluation.line_crop_registry import build_line_crop_registry  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the frozen E-0024 line-crop registry")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/experiments/e0024-vietnamese-line-recognizer.yaml"),
    )
    args = parser.parse_args()
    result = build_line_crop_registry(PROJECT_ROOT, config_path=args.config)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
