#!/usr/bin/env python3
"""Build or exclusively publish the formal E-0041 workbook/provenance pair."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.evaluation.e0041_formal_export import (
    CONTROL_RELATIVE_PATH,
    capture_e0041_formal_export,
    dry_run_e0041_formal_export,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build or exclusively publish the formal E-0041 workbook/provenance pair"
    )
    parser.add_argument("--config", type=Path, default=CONTROL_RELATIVE_PATH)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.dry_run:
        build = dry_run_e0041_formal_export(PROJECT_ROOT, config_path=args.config)
        provenance = build.provenance
    else:
        provenance = capture_e0041_formal_export(PROJECT_ROOT, config_path=args.config)
    outputs = provenance.get("outputs", {})
    metrics = provenance.get("metrics", {})
    print(
        json.dumps(
            {
                "dry_run": args.dry_run,
                "state": provenance.get("state"),
                "pair_hash_sealed": provenance.get("pair_hash_sealed"),
                "workbook_sha256": outputs.get("workbook", {}).get("sha256"),
                "source_row_count": metrics.get("source_row_count"),
                "physical_cell_count": metrics.get("physical_cell_count"),
                "schema_row_count": metrics.get("schema_row_count"),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
