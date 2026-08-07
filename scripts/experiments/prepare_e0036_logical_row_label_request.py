#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.evaluation.logical_row_label_request import (
    build_logical_row_label_request,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare the reference-blind E-0036 logical-row label request"
    )
    parser.add_argument("--crop-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    request = build_logical_row_label_request(
        PROJECT_ROOT,
        crop_manifest_path=args.crop_manifest,
        output_path=args.output,
    )
    print(
        json.dumps(
            {
                "state": request["state"],
                "sample_count": request["sample_count"],
                "git_commit": request["git_commit"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
