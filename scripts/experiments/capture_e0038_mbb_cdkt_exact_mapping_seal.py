#!/usr/bin/env python3
"""Deterministically replay and exclusively seal one E-0038 mapping artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.e0038_exact_mapping import (
    CONTROL_RELATIVE_PATH,
    MAPPING_ONLY_RELATIVE_PATH,
    MAPPING_SEAL_RELATIVE_PATH,
    capture_e0038_mapping_seal,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=("Replay and hash-seal exactly one E-0038 mapping-only artifact before review")
    )
    parser.add_argument("--config", type=Path, default=CONTROL_RELATIVE_PATH)
    parser.add_argument(
        "--mapping-only",
        type=Path,
        default=MAPPING_ONLY_RELATIVE_PATH,
    )
    parser.add_argument("--output", type=Path, default=MAPPING_SEAL_RELATIVE_PATH)
    return parser


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    inventory = payload.get("inventory")
    return {
        "state": payload.get("state"),
        "mapping_status": payload.get("mapping_status"),
        "file_count": inventory.get("file_count") if isinstance(inventory, dict) else None,
        "exact_byte_equality": payload.get("replay", {}).get("exact_byte_equality"),
    }


def main() -> int:
    args = _parser().parse_args()
    payload = capture_e0038_mapping_seal(
        PROJECT_ROOT,
        config_path=args.config,
        mapping_only_path=args.mapping_only,
        output_path=args.output,
    )
    print(json.dumps(_summary(payload), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
