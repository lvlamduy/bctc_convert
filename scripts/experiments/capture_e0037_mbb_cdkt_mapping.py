#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.e0037_sealed_mapping import (
    CONTROL_RELATIVE_PATH,
    MAPPING_ONLY_RELATIVE_PATH,
    MAPPING_SEAL_RELATIVE_PATH,
    POSTJOIN_RELATIVE_PATH,
    SOURCE_STRUCTURE_RELATIVE_PATH,
    capture_e0037_mapping_only,
    capture_e0037_mapping_seal,
    capture_e0037_postjoin,
    capture_e0037_source_structure,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture one isolated E-0037 source/mapping/postjoin phase"
    )
    parser.add_argument("--config", type=Path, default=CONTROL_RELATIVE_PATH)
    subparsers = parser.add_subparsers(dest="phase", required=True)

    source = subparsers.add_parser(
        "source-structure",
        help="publish source-only Seal A before schema access",
    )
    source.add_argument("--output", type=Path, default=SOURCE_STRUCTURE_RELATIVE_PATH)

    mapping = subparsers.add_parser(
        "mapping-only",
        help="run mapping without period, numeric, review, or history inputs",
    )
    mapping.add_argument(
        "--source-structure",
        type=Path,
        default=SOURCE_STRUCTURE_RELATIVE_PATH,
    )
    mapping.add_argument("--output", type=Path, default=MAPPING_ONLY_RELATIVE_PATH)

    seal = subparsers.add_parser(
        "seal-mapping",
        help="hash-seal mapping-only bytes before postjoin access",
    )
    seal.add_argument("--mapping-only", type=Path, default=MAPPING_ONLY_RELATIVE_PATH)
    seal.add_argument("--output", type=Path, default=MAPPING_SEAL_RELATIVE_PATH)

    postjoin = subparsers.add_parser(
        "postjoin",
        help="join E-0030/E-0034 only after validating the committed mapping seal",
    )
    postjoin.add_argument("--mapping-seal", type=Path, default=MAPPING_SEAL_RELATIVE_PATH)
    postjoin.add_argument("--output", type=Path, default=POSTJOIN_RELATIVE_PATH)
    return parser


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    metrics = payload.get("metrics")
    return {
        "state": payload.get("state"),
        "row_count": (
            metrics.get("row_count") if isinstance(metrics, dict) else payload.get("row_count")
        ),
        "schema_disposition_count": (
            metrics.get("schema_disposition_count")
            if isinstance(metrics, dict)
            else payload.get("schema_disposition_count")
        ),
        "cell_count": metrics.get("cell_count") if isinstance(metrics, dict) else None,
    }


def main() -> int:
    args = _parser().parse_args()
    if args.phase == "source-structure":
        result = capture_e0037_source_structure(
            PROJECT_ROOT,
            config_path=args.config,
            output_path=args.output,
        )
    elif args.phase == "mapping-only":
        result = capture_e0037_mapping_only(
            PROJECT_ROOT,
            config_path=args.config,
            source_structure_path=args.source_structure,
            output_path=args.output,
        )
    elif args.phase == "seal-mapping":
        result = capture_e0037_mapping_seal(
            PROJECT_ROOT,
            config_path=args.config,
            mapping_only_path=args.mapping_only,
            output_path=args.output,
        )
    elif args.phase == "postjoin":
        result = capture_e0037_postjoin(
            PROJECT_ROOT,
            config_path=args.config,
            mapping_seal_path=args.mapping_seal,
            output_path=args.output,
        )
    else:  # pragma: no cover - argparse enforces the finite phase set.
        raise AssertionError(args.phase)
    print(json.dumps(_summary(result), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
