#!/usr/bin/env python3
"""Run the 27-bank expansion only through OpenRouter Google Vertex Flex."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.gemini_json_first_vertex_flex_expansion_v1 import (  # noqa: E402
    validate_gemini_json_first_vertex_flex_expansion_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1  # noqa: E402

SUPERVISOR = ROOT / "scripts/experiments/run_gemini_json_first_corpus_supervisor_v1.py"


class RunGeminiJsonFirst27BankVertexFlexV1Error(RuntimeError):
    pass


def _load_bundle_and_plan(bundle_path: Path, plan_path: Path) -> dict[str, Any]:
    if any(path.is_symlink() or not path.is_file() for path in (bundle_path, plan_path)):
        raise RunGeminiJsonFirst27BankVertexFlexV1Error("bundle and plan must be regular files")
    bundle = validate_gemini_json_first_vertex_flex_expansion_v1(
        json.loads(bundle_path.read_bytes())
    )
    if plan_path.read_bytes() not in {
        canonical_json_bytes_v1(bundle["corpus_plan"]),
        canonical_json_bytes_v1(bundle["corpus_plan"]) + b"\n",
    }:
        raise RunGeminiJsonFirst27BankVertexFlexV1Error(
            "corpus plan does not match the provider-pinned bundle"
        )
    return bundle


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "status", "run", "run-one"):
        command = commands.add_parser(name)
        command.add_argument("--bundle", type=Path, required=True)
        command.add_argument("--plan", type=Path, required=True)
        command.add_argument("--ledger", type=Path, required=True)
        if name == "init":
            command.add_argument(
                "--prompt-variant",
                choices=("simple", "items", "scope", "compact", "balanced"),
                default="simple",
            )
            command.add_argument("--max-task-attempts", type=int, default=3)
        if name in {"run", "run-one"}:
            command.add_argument("--source-root", type=Path, required=True)
            command.add_argument("--database", type=Path, required=True)
            command.add_argument("--artifact-root", type=Path, required=True)
            command.add_argument("--openrouter-key-file", type=Path, required=True)
            command.add_argument("--openrouter-workers", type=int, default=20)
            command.add_argument("--provider-timeout-seconds", type=int, default=900)
        if name == "run-one":
            command.add_argument("--task-id", required=True)
        if name == "run":
            command.add_argument("--max-fallback-attempts", type=int, default=2)
    return parser


def _supervisor_command(args: argparse.Namespace) -> list[str]:
    _load_bundle_and_plan(args.bundle, args.plan)
    supervisor_command = "run-openrouter-task" if args.command == "run-one" else args.command
    command = [sys.executable, str(SUPERVISOR), supervisor_command]
    if args.command == "status":
        return [*command, "--ledger", str(args.ledger)]
    command.extend(("--plan", str(args.plan), "--ledger", str(args.ledger)))
    if args.command == "init":
        command.extend(
            (
                "--prompt-variant",
                args.prompt_variant,
                "--max-task-attempts",
                str(args.max_task_attempts),
            )
        )
        return command
    command.extend(
        (
            "--source-root",
            str(args.source_root),
            "--database",
            str(args.database),
            "--artifact-root",
            str(args.artifact_root),
            "--openrouter-key-file",
            str(args.openrouter_key_file),
            "--openrouter-workers",
            str(args.openrouter_workers),
            "--provider-timeout-seconds",
            str(args.provider_timeout_seconds),
        )
    )
    if args.command == "run":
        command.extend(("--max-fallback-attempts", str(args.max_fallback_attempts)))
    else:
        command.extend(("--task-id", args.task_id))
    command.append("--openrouter-only")
    return command


def main() -> int:
    args = _parser().parse_args()
    command = _supervisor_command(args)
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(command, cwd=ROOT, env=environment, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
