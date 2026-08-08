#!/usr/bin/env python3
"""Replay and exclusively seal the formal E-0041 workbook/provenance pair."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.evaluation.e0041_formal_export import (
    CONTROL_RELATIVE_PATH,
    capture_e0041_formal_export_seal,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Replay and exclusively hash-seal the formal E-0041 export pair"
    )
    parser.add_argument("--config", type=Path, default=CONTROL_RELATIVE_PATH)
    return parser


def main() -> int:
    args = _parser().parse_args()
    payload = capture_e0041_formal_export_seal(PROJECT_ROOT, config_path=args.config)
    inventory = payload.get("inventory", {})
    replay = payload.get("replay", {})
    print(
        json.dumps(
            {
                "state": payload.get("state"),
                "file_count": inventory.get("file_count"),
                "workbook_exact_byte_equality": replay.get("workbook_exact_byte_equality"),
                "provenance_exact_canonical_byte_equality": replay.get(
                    "provenance_exact_canonical_byte_equality"
                ),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
