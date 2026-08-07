from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.ocr.vietocr_logical_row_reader import run_vietocr_logical_row_reader

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run pinned VietOCR on the E-0036 logical-row label crops"
    )
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/models/vietocr-0.3.13-rtx4090.toml"),
    )
    args = parser.parse_args()
    manifest = run_vietocr_logical_row_reader(
        PROJECT_ROOT,
        request_path=args.request,
        output_directory=args.output_directory,
        runtime_root=args.runtime_root,
        config_path=args.config,
    )
    print(json.dumps({"status": "PASS", "metrics": manifest["metrics"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
