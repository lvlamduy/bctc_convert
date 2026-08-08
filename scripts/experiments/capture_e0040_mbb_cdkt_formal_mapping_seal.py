#!/usr/bin/env python3
"""Replay and exclusively seal the answer-free E-0040 mapping artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.e0040_formal_mapping import (
    CONTROL_RELATIVE_PATH,
    MAPPING_ONLY_RELATIVE_PATH,
    MAPPING_SEAL_RELATIVE_PATH,
    capture_e0040_mapping_seal,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Replay and hash-seal exactly one E-0040 mapping-only artifact"
    )
    parser.add_argument("--config", type=Path, default=CONTROL_RELATIVE_PATH)
    parser.add_argument("--mapping-only", type=Path, default=MAPPING_ONLY_RELATIVE_PATH)
    parser.add_argument("--output", type=Path, default=MAPPING_SEAL_RELATIVE_PATH)
    return parser


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    inventory = payload.get("inventory")
    replay = payload.get("replay")
    return {
        "state": payload.get("state"),
        "mapping_status": payload.get("mapping_status"),
        "file_count": inventory.get("file_count") if isinstance(inventory, dict) else None,
        "exact_canonical_byte_equality": (
            replay.get("exact_canonical_byte_equality") if isinstance(replay, dict) else None
        ),
    }


def main() -> int:
    args = _parser().parse_args()
    payload = capture_e0040_mapping_seal(
        PROJECT_ROOT,
        config_path=args.config,
        mapping_only_path=args.mapping_only,
        output_path=args.output,
    )
    print(json.dumps(_summary(payload), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
