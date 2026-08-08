#!/usr/bin/env python3
"""Build or exclusively publish the answer-free E-0040 mapping artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.e0040_formal_mapping import (
    CONTROL_RELATIVE_PATH,
    MAPPING_ONLY_RELATIVE_PATH,
    capture_e0040_mapping_only,
    dry_run_e0040_mapping_only,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the answer-free E-0040 calibration mapping; --dry-run never publishes "
            "the canonical artifact"
        )
    )
    parser.add_argument("--config", type=Path, default=CONTROL_RELATIVE_PATH)
    parser.add_argument("--output", type=Path, default=MAPPING_ONLY_RELATIVE_PATH)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def _summary(payload: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    metrics = payload.get("metrics")
    return {
        "dry_run": dry_run,
        "state": payload.get("state"),
        "selected_row_count": (
            metrics.get("final_selected_count") if isinstance(metrics, dict) else None
        ),
        "source_only_row_count": (
            metrics.get("source_only_structural_count") if isinstance(metrics, dict) else None
        ),
        "selected_anchor_count": (
            metrics.get("selected_anchor_count") if isinstance(metrics, dict) else None
        ),
        "selected_path_count": (
            metrics.get("selected_path_count") if isinstance(metrics, dict) else None
        ),
        "all_pruning_counts_zero": (
            metrics.get("all_pruning_counts_zero") if isinstance(metrics, dict) else None
        ),
    }


def main() -> int:
    args = _parser().parse_args()
    if args.dry_run:
        payload = dry_run_e0040_mapping_only(PROJECT_ROOT, config_path=args.config)
    else:
        payload = capture_e0040_mapping_only(
            PROJECT_ROOT,
            config_path=args.config,
            output_path=args.output,
        )
    print(json.dumps(_summary(payload, dry_run=args.dry_run), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
