from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from bctc_ai.corpus.wave1_role_b_sentinel import (  # noqa: E402
    _canonical_bytes,
    finalize_authenticated_sentinel,
    publish_authenticated_control,
    run_authenticated_sentinel,
    verify_authenticated_sentinel,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run and finalize the authenticated Wave-1 24-page Role-B OCR sentinel"
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("control", "authenticate Milestone A and publish the exact two-shard control"),
        ("run", "render and execute missing exact sentinel requests with pinned workers"),
        ("verify", "rerender sources and verify all checkpoints/results without publishing"),
        ("finalize", "verify and exclusively publish the deterministic aggregate"),
    ):
        command = subcommands.add_parser(name, help=help_text)
        command.add_argument("--model-cache", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    if arguments.command == "control":
        result = publish_authenticated_control(
            PROJECT_ROOT,
            model_cache=arguments.model_cache,
        )
        summary = {
            "status": result["status"],
            "control_identity_sha256": result["control_identity_sha256"],
            "artifact_sha256": hashlib.sha256(_canonical_bytes(result)).hexdigest(),
            "artifact_size_bytes": len(_canonical_bytes(result)),
            **result["accounting"],
        }
    elif arguments.command == "run":
        summary = run_authenticated_sentinel(
            PROJECT_ROOT,
            model_cache=arguments.model_cache,
        )
    elif arguments.command == "verify":
        result = verify_authenticated_sentinel(
            PROJECT_ROOT,
            model_cache=arguments.model_cache,
        )
        summary = {
            "status": result["status"],
            "aggregate_identity_sha256": result["aggregate_identity_sha256"],
            "candidate_artifact_sha256": hashlib.sha256(_canonical_bytes(result)).hexdigest(),
            "candidate_artifact_size_bytes": len(_canonical_bytes(result)),
            **result["accounting"],
            "published": False,
        }
    elif arguments.command == "finalize":
        result = finalize_authenticated_sentinel(
            PROJECT_ROOT,
            model_cache=arguments.model_cache,
        )
        summary = {
            "status": result["status"],
            "aggregate_identity_sha256": result["aggregate_identity_sha256"],
            "artifact_sha256": hashlib.sha256(_canonical_bytes(result)).hexdigest(),
            "artifact_size_bytes": len(_canonical_bytes(result)),
            **result["accounting"],
            "published": True,
        }
    else:  # pragma: no cover - argparse enforces the command set
        raise RuntimeError("unsupported sentinel command")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
