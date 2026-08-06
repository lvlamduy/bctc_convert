from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bctc_ai.evaluation.line_reader_request import prepare_line_reader_request  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare a reference-blind E-0024 line-reader request"
    )
    parser.add_argument("--crop-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = prepare_line_reader_request(
        PROJECT_ROOT,
        crop_manifest_path=args.crop_manifest,
        output_path=args.output,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
