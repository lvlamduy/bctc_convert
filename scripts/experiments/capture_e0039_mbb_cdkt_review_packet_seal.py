#!/usr/bin/env python3
"""Exclusively hash-seal the existing answer-free E-0039 review packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.e0039_review_packet_seal import (
    CONTROL_RELATIVE_PATH,
    OUTPUT_RELATIVE_PATH,
    PACKET_RELATIVE_PATH,
    capture_e0039_review_packet_seal,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Hash-seal the existing E-0039 blank pre-decision evidence packet"
    )
    parser.add_argument("--config", type=Path, default=CONTROL_RELATIVE_PATH)
    parser.add_argument("--packet", type=Path, default=PACKET_RELATIVE_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_RELATIVE_PATH)
    return parser


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    inventory = payload.get("inventory")
    return {
        "state": payload.get("state"),
        "packet_capture_git_commit": payload.get("packet_capture_git_commit"),
        "seal_git_commit": payload.get("seal_git_commit"),
        "file_count": inventory.get("file_count") if isinstance(inventory, dict) else None,
        "exact_canonical_byte_equality": payload.get("replay", {}).get(
            "exact_canonical_byte_equality"
        ),
    }


def main() -> int:
    args = _parser().parse_args()
    payload = capture_e0039_review_packet_seal(
        PROJECT_ROOT,
        config_path=args.config,
        packet_path=args.packet,
        output_path=args.output,
    )
    print(json.dumps(_summary(payload), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
