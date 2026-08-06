from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bctc_ai.ocr.vietocr_line_reader import run_vietocr_line_reader  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the pinned VietOCR line reader")
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/models/vietocr-0.3.13.toml"),
    )
    args = parser.parse_args()
    result = run_vietocr_line_reader(
        PROJECT_ROOT,
        request_path=args.request,
        output_directory=args.output_directory,
        runtime_root=args.runtime_root,
        config_path=args.config,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
