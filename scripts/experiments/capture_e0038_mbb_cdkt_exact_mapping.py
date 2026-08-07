#!/usr/bin/env python3
"""Build or exclusively publish the E-0038 calibration mapping-only artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.e0038_exact_mapping import (
    CONTROL_RELATIVE_PATH,
    MAPPING_ONLY_RELATIVE_PATH,
    capture_e0038_mapping_only,
    dry_run_e0038_mapping_only,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the review-independent E-0038 calibration mapping mechanism; "
            "--dry-run never writes the canonical artifact"
        )
    )
    parser.add_argument("--config", type=Path, default=CONTROL_RELATIVE_PATH)
    parser.add_argument("--output", type=Path, default=MAPPING_ONLY_RELATIVE_PATH)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="execute and validate entirely in memory without publishing",
    )
    return parser


def _summary(payload: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    metrics = payload.get("metrics")
    bundle = payload.get("exact_mapping_bundle")
    exact = bundle.get("exact_search") if isinstance(bundle, dict) else None
    resources = exact.get("resource_semantics") if isinstance(exact, dict) else None
    return {
        "dry_run": dry_run,
        "state": payload.get("state"),
        "status": exact.get("status") if isinstance(exact, dict) else None,
        "row_count": metrics.get("source_row_count") if isinstance(metrics, dict) else None,
        "schema_node_count": (
            metrics.get("schema_node_count") if isinstance(metrics, dict) else None
        ),
        "selected_row_count": (
            metrics.get("selected_row_count") if isinstance(metrics, dict) else None
        ),
        "actual_generated_states": (
            resources.get("actual_generated_states") if isinstance(resources, dict) else None
        ),
        "actual_retained_states": (
            resources.get("actual_retained_states") if isinstance(resources, dict) else None
        ),
    }


def main() -> int:
    args = _parser().parse_args()
    if args.dry_run:
        payload = dry_run_e0038_mapping_only(
            PROJECT_ROOT,
            config_path=args.config,
        )
    else:
        payload = capture_e0038_mapping_only(
            PROJECT_ROOT,
            config_path=args.config,
            output_path=args.output,
        )
    print(json.dumps(_summary(payload, dry_run=args.dry_run), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
