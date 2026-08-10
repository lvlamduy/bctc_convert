from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from bctc_ai.core.hashing import sha256_bytes  # noqa: E402
from bctc_ai.corpus.wave1_role_b_line_only_supplement_v1 import (  # noqa: E402
    _canonical_bytes,
    authenticated_line_only_aggregate_is_published,
    finalize_authenticated_line_only_supplement,
    publish_authenticated_line_only_control,
    run_authenticated_line_only_supplement,
    verify_authenticated_line_only_supplement,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Build the authenticated post-V2 line-only supplement without OCR or network")
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("control", "authenticate finalized V2 and publish the line-only control"),
        ("run", "checkpoint all exact terminal-page supplemental dispositions"),
        ("verify", "read-only replay of every supplemental page and upstream authority"),
        ("finalize", "verify and publish the deterministic supplemental aggregate"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--model-cache", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    if arguments.command == "control":
        published = publish_authenticated_line_only_control(
            PROJECT_ROOT, model_cache=arguments.model_cache
        )
        payload = _canonical_bytes(published)
        summary = {
            "status": published["status"],
            "control_identity_sha256": published["control_identity_sha256"],
            "artifact_sha256": sha256_bytes(payload),
            "artifact_size_bytes": len(payload),
            **published["accounting"],
        }
    elif arguments.command == "run":
        summary = run_authenticated_line_only_supplement(
            PROJECT_ROOT, model_cache=arguments.model_cache
        )
    elif arguments.command == "verify":
        aggregate = verify_authenticated_line_only_supplement(
            PROJECT_ROOT, model_cache=arguments.model_cache
        )
        payload = _canonical_bytes(aggregate)
        summary = {
            "status": aggregate["status"],
            "aggregate_identity_sha256": aggregate["aggregate_identity_sha256"],
            "candidate_artifact_sha256": sha256_bytes(payload),
            "candidate_artifact_size_bytes": len(payload),
            **aggregate["accounting"],
            "authenticated_published_aggregate_present": (
                authenticated_line_only_aggregate_is_published(PROJECT_ROOT, aggregate)
            ),
            "publication_command_invoked": False,
        }
    elif arguments.command == "finalize":
        aggregate = finalize_authenticated_line_only_supplement(
            PROJECT_ROOT, model_cache=arguments.model_cache
        )
        payload = _canonical_bytes(aggregate)
        summary = {
            "status": aggregate["status"],
            "aggregate_identity_sha256": aggregate["aggregate_identity_sha256"],
            "artifact_sha256": sha256_bytes(payload),
            "artifact_size_bytes": len(payload),
            **aggregate["accounting"],
            "authenticated_published_aggregate_present": (
                authenticated_line_only_aggregate_is_published(PROJECT_ROOT, aggregate)
            ),
            "publication_command_invoked": True,
        }
    else:  # pragma: no cover - argparse enforces this set
        raise RuntimeError("unsupported line-only supplement command")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
