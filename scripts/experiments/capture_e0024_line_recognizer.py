from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bctc_ai.evaluation.line_recognizer_evaluation import (  # noqa: E402
    capture_line_recognizer_evaluation,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture the E-0024 line-reader comparison")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/experiments/e0024-vietnamese-line-recognizer.yaml"),
    )
    parser.add_argument("--crop-manifest", type=Path, required=True)
    parser.add_argument("--inference-directory", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/experiments/E-0024-vietnamese-line-recognizer.json"),
    )
    args = parser.parse_args()
    result = capture_line_recognizer_evaluation(
        PROJECT_ROOT,
        config_path=args.config,
        crop_manifest_path=args.crop_manifest,
        inference_directory=args.inference_directory,
        output_path=args.output,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
