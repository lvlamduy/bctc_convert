#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.evaluation.logical_row_label_review_evaluation import (
    capture_logical_row_label_review_evaluation,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate sealed E-0036 readers on the pre-existing reviewed rows"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/experiments/e0036-mbb-cdkt-semantic-label-readers.yaml"),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = capture_logical_row_label_review_evaluation(
        PROJECT_ROOT,
        config_path=args.config,
        output_path=args.output,
    )
    print(
        json.dumps(
            {
                "state": result["state"],
                "qwen_triggered": result["conditional_qwen"]["triggered"],
                "vietocr_reviewed_exact": result["reader_evaluations"]["vietocr"]["labels"][
                    "aggregate"
                ]["exact_line_count"],
                "deepseek_reviewed_exact": result["reader_evaluations"]["deepseek_ocr2"]["labels"][
                    "aggregate"
                ]["exact_line_count"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
