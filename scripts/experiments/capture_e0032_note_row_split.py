#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.evaluation.note_row_split_benchmark import (
    capture_e0032_note_row_split_benchmark,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture frozen E-0032 note-row anchor split"
    )
    parser.add_argument(
        "--experiment-config",
        type=Path,
        default=Path("config/experiments/e0032-mbb-cdkt-note-row-split.yaml"),
    )
    parser.add_argument("--batch-root", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/experiments/E-0032-mbb-cdkt-note-row-split.json"),
    )
    args = parser.parse_args()
    result = capture_e0032_note_row_split_benchmark(
        PROJECT_ROOT,
        experiment_config_path=args.experiment_config,
        batch_root=args.batch_root,
        output_path=args.output,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "comparison": result["comparison"],
                "after": [page["summary"] for page in result["after"]],
                "gates": result["gates"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if result["status"].startswith("PASS_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
