#!/usr/bin/env python3
"""Run the 27-bank expansion only through OpenRouter Google Vertex Flex."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.gemini_json_first_corpus_ledger_v1 import (  # noqa: E402
    corpus_ledger_summary_v1,
    list_corpus_tasks_v1,
)
from bctc_ai.evaluation.gemini_json_first_corpus_plan_v1 import (  # noqa: E402
    OPENROUTER_ROUTE,
)
from bctc_ai.evaluation.gemini_json_first_vertex_flex_expansion_v1 import (  # noqa: E402
    validate_gemini_json_first_vertex_flex_expansion_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1  # noqa: E402

SUPERVISOR = ROOT / "scripts/experiments/run_gemini_json_first_corpus_supervisor_v1.py"
OPENROUTER_DOCUMENT_RUNNER = (
    ROOT / "scripts/experiments/run_gemini_json_first_openrouter_document_v1.py"
)
PROMPT_VARIANTS = frozenset({"balanced", "compact", "items", "scope", "simple"})


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
    for name in ("init", "status", "run", "run-one", "repair-one", "repair-failed"):
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
        if name in {"run", "run-one", "repair-one", "repair-failed"}:
            command.add_argument("--source-root", type=Path, required=True)
            command.add_argument("--database", type=Path, required=True)
            command.add_argument("--artifact-root", type=Path, required=True)
            command.add_argument("--openrouter-key-file", type=Path, required=True)
            command.add_argument("--openrouter-workers", type=int, default=20)
            command.add_argument("--provider-timeout-seconds", type=int, default=900)
        if name in {"run-one", "repair-one"}:
            command.add_argument("--task-id", required=True)
        if name == "run":
            command.add_argument("--max-fallback-attempts", type=int, default=2)
    return parser


def _supervisor_command(args: argparse.Namespace) -> list[str]:
    if args.command == "repair-one":
        raise RunGeminiJsonFirst27BankVertexFlexV1Error(
            "repair-one uses the bounded page repair path"
        )
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


def _retry_prompt_variants(
    receipt: dict[str, Any], *, document_page_count: int, default_variant: str
) -> tuple[list[int], dict[int, str]]:
    """Recover the exact terminal failed-page and prompt-variant frontiers."""

    if default_variant not in PROMPT_VARIANTS:
        raise RunGeminiJsonFirst27BankVertexFlexV1Error(
            "failed-task default prompt variant is invalid"
        )
    expected_pages = set(range(1, document_page_count + 1))
    failed_pages = receipt.get("failed_pages")
    if (
        type(failed_pages) is not list
        or not failed_pages
        or failed_pages != sorted(set(failed_pages))
        or any(type(page) is not int or page not in expected_pages for page in failed_pages)
    ):
        raise RunGeminiJsonFirst27BankVertexFlexV1Error(
            "failed task lacks one exact terminal page frontier"
        )
    variants = {page: default_variant for page in expected_pages}

    def apply_group(group: Any) -> None:
        if type(group) is not dict:
            raise RunGeminiJsonFirst27BankVertexFlexV1Error("failed-task prompt group is invalid")
        pages = group.get("physical_pages")
        variant = group.get("prompt_variant")
        if (
            type(pages) is not list
            or pages != sorted(set(pages))
            or any(type(page) is not int or page not in expected_pages for page in pages)
            or variant not in PROMPT_VARIANTS
        ):
            raise RunGeminiJsonFirst27BankVertexFlexV1Error(
                "failed-task prompt frontier is invalid"
            )
        variants.update({page: variant for page in pages})

    alternate_groups = receipt.get("alternate_prompt_variants", [])
    if type(alternate_groups) is not list:
        raise RunGeminiJsonFirst27BankVertexFlexV1Error(
            "failed-task alternate prompt frontier is invalid"
        )
    for group in alternate_groups:
        apply_group(group)
    retry_results = receipt.get("adaptive_retry_results", [])
    if type(retry_results) is not list:
        raise RunGeminiJsonFirst27BankVertexFlexV1Error("failed-task adaptive receipt is invalid")
    for group in retry_results:
        apply_group(group)
    return failed_pages, variants


def _json_subprocess(
    command: list[str], *, environment: dict[str, str], expected: set[int]
) -> tuple[int, dict[str, Any]]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode not in expected:
        raise RunGeminiJsonFirst27BankVertexFlexV1Error(
            "bounded repair subprocess failed outside its typed disposition"
        )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise RunGeminiJsonFirst27BankVertexFlexV1Error(
            "bounded repair subprocess returned no JSON receipt"
        )
    try:
        value = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise RunGeminiJsonFirst27BankVertexFlexV1Error(
            "bounded repair subprocess receipt is invalid"
        ) from exc
    if type(value) is not dict:
        raise RunGeminiJsonFirst27BankVertexFlexV1Error(
            "bounded repair subprocess receipt is not one object"
        )
    return completed.returncode, value


def _repair_one(args: argparse.Namespace, *, environment: dict[str, str]) -> dict[str, Any]:
    """Retry only the terminal missing pages, then seal the complete document."""

    bundle = _load_bundle_and_plan(args.bundle, args.plan)
    if not 1 <= args.openrouter_workers <= 30:
        raise RunGeminiJsonFirst27BankVertexFlexV1Error("repair worker bound lies outside 1..30")
    summary = corpus_ledger_summary_v1(args.ledger)
    if summary["corpus_plan_id"] != bundle["corpus_plan"]["corpus_plan_id"]:
        raise RunGeminiJsonFirst27BankVertexFlexV1Error(
            "repair ledger and provider-pinned plan disagree"
        )
    matches = [
        task for task in list_corpus_tasks_v1(args.ledger) if task["task_id"] == args.task_id
    ]
    if len(matches) != 1:
        raise RunGeminiJsonFirst27BankVertexFlexV1Error("repair requires one exact corpus task")
    task = matches[0]
    if task["state"] != "FAILED" or task["route"] != OPENROUTER_ROUTE:
        raise RunGeminiJsonFirst27BankVertexFlexV1Error(
            "repair requires one failed OpenRouter task"
        )
    try:
        receipt = json.loads(task["last_receipt_json"])
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunGeminiJsonFirst27BankVertexFlexV1Error("failed task receipt is invalid") from exc
    if type(receipt) is not dict:
        raise RunGeminiJsonFirst27BankVertexFlexV1Error("failed task receipt is not one object")
    failed_pages, variants = _retry_prompt_variants(
        receipt,
        document_page_count=task["document_page_count"],
        default_variant=summary["prompt_variant"],
    )
    source = args.source_root.resolve() / task["relative_path"]
    if source.is_symlink() or not source.is_file():
        raise RunGeminiJsonFirst27BankVertexFlexV1Error("repair PDF is absent or not regular")
    source_bytes = source.read_bytes()
    if (
        len(source_bytes) != task["source_size_bytes"]
        or sha256(source_bytes).hexdigest() != task["source_sha256"]
    ):
        raise RunGeminiJsonFirst27BankVertexFlexV1Error("repair PDF bytes drifted")
    task_root = args.artifact_root / task["artifact_relative_path"]
    repair_root = task_root / "terminal-openrouter-repair"
    existing = [
        int(path.name.removeprefix("attempt-"))
        for path in repair_root.glob("attempt-[0-9][0-9][0-9][0-9]")
        if path.is_dir() and path.name.removeprefix("attempt-").isdigit()
    ]
    attempt_root = repair_root / f"attempt-{max(existing, default=0) + 1:04d}"
    groups: dict[str, list[int]] = {}
    for page in failed_pages:
        groups.setdefault(variants[page], []).append(page)
    provider_results = []
    remaining_pages: set[int] = set()
    for variant in sorted(groups):
        pages = groups[variant]
        command = [
            sys.executable,
            str(OPENROUTER_DOCUMENT_RUNNER),
            "--pdf",
            str(source),
            "--source-logical-name",
            task["relative_path"],
            "--database",
            str(args.database),
            "--artifact-dir",
            str(attempt_root / variant),
            "--dpi",
            str(bundle["corpus_plan"]["policy"]["dpi"]),
            "--workers",
            str(min(args.openrouter_workers, len(pages))),
            "--prompt-variant",
            variant,
            "--output-contract-mode",
            "json-schema",
            "--openrouter-key-file",
            str(args.openrouter_key_file),
            "--google-standard-mode",
            "disabled",
            "--timeout-seconds",
            str(args.provider_timeout_seconds),
        ]
        for page in pages:
            command.extend(("--physical-page", str(page)))
        code, result = _json_subprocess(command, environment=environment, expected={0, 2})
        result_failed = result.get("failed_pages")
        if (
            type(result_failed) is not list
            or result_failed != sorted(set(result_failed))
            or any(page not in pages for page in result_failed)
        ):
            raise RunGeminiJsonFirst27BankVertexFlexV1Error(
                "bounded page repair returned an invalid failure frontier"
            )
        if code == 0 and result_failed:
            raise RunGeminiJsonFirst27BankVertexFlexV1Error(
                "bounded page repair success contradicts its failure frontier"
            )
        remaining_pages.update(result_failed)
        provider_results.append(
            {"physical_pages": pages, "prompt_variant": variant, "result": result}
        )
    if remaining_pages:
        return {
            "disposition": "NEEDS_RETRY",
            "provider_results": provider_results,
            "remaining_pages": sorted(remaining_pages),
            "task_id": task["task_id"],
        }
    manifest_command = [
        sys.executable,
        str(SUPERVISOR),
        "document-manifest-current",
        "--plan",
        str(args.plan),
        "--ledger",
        str(args.ledger),
        "--task-id",
        task["task_id"],
        "--source-root",
        str(args.source_root),
        "--database",
        str(args.database),
        "--artifact-root",
        str(args.artifact_root),
    ]
    for page, variant in variants.items():
        if variant != summary["prompt_variant"]:
            manifest_command.extend(("--page-prompt-variant", f"{page}={variant}"))
    _code, manifest = _json_subprocess(manifest_command, environment=environment, expected={0})
    if manifest.get("disposition") != "SUCCEEDED":
        raise RunGeminiJsonFirst27BankVertexFlexV1Error(
            "bounded repair did not seal one complete current document manifest"
        )
    return {
        "disposition": "SUCCEEDED",
        "document_manifest_id": manifest["document_manifest_id"],
        "provider_results": provider_results,
        "task_id": task["task_id"],
    }


def _repair_failed(args: argparse.Namespace, *, environment: dict[str, str]) -> dict[str, Any]:
    """Run one bounded repair round over a quiescent terminal ledger.

    This deliberately delegates every task to ``_repair_one`` so the batch path
    cannot broaden the document/page frontier or relax the provider pin. A
    subsequent round is explicit: tasks whose bounded page repair still fails
    remain ``FAILED`` and are reported as ``NEEDS_RETRY``.
    """

    bundle = _load_bundle_and_plan(args.bundle, args.plan)
    summary = corpus_ledger_summary_v1(args.ledger)
    if summary["corpus_plan_id"] != bundle["corpus_plan"]["corpus_plan_id"]:
        raise RunGeminiJsonFirst27BankVertexFlexV1Error(
            "repair ledger and provider-pinned plan disagree"
        )
    tasks = list_corpus_tasks_v1(args.ledger)
    active = sorted(
        (task for task in tasks if task["state"] not in {"FAILED", "SUCCEEDED"}),
        key=lambda task: (task["relative_path"], task["task_id"]),
    )
    if active:
        raise RunGeminiJsonFirst27BankVertexFlexV1Error(
            "batch repair requires a quiescent terminal ledger"
        )
    failed = sorted(
        (task for task in tasks if task["state"] == "FAILED"),
        key=lambda task: (task["relative_path"], task["task_id"]),
    )
    results: list[dict[str, Any]] = []
    for task in failed:
        task_values = {**vars(args), "command": "repair-one", "task_id": task["task_id"]}
        task_args = argparse.Namespace(**task_values)
        results.append(_repair_one(task_args, environment=environment))
    remaining = [result["task_id"] for result in results if result["disposition"] != "SUCCEEDED"]
    return {
        "disposition": "NEEDS_RETRY" if remaining else "SUCCEEDED",
        "initial_failed_task_count": len(failed),
        "remaining_task_count": len(remaining),
        "remaining_task_ids": remaining,
        "repaired_task_count": len(failed) - len(remaining),
        "results": results,
    }


def main() -> int:
    args = _parser().parse_args()
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    if args.command in {"repair-one", "repair-failed"}:
        result = (
            _repair_one(args, environment=environment)
            if args.command == "repair-one"
            else _repair_failed(args, environment=environment)
        )
        print(json.dumps(result, sort_keys=True))
        return 0 if result["disposition"] == "SUCCEEDED" else 2
    command = _supervisor_command(args)
    completed = subprocess.run(command, cwd=ROOT, env=environment, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
