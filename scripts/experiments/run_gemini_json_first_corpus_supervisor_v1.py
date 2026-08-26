#!/usr/bin/env python3
"""Initialize, run, resume, and report the Gemini JSON-first corpus plan."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import Future, ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.gemini_json_first_corpus_ledger_v1 import (  # noqa: E402
    corpus_ledger_summary_v1,
    initialize_gemini_json_first_corpus_ledger_v1,
    list_corpus_tasks_v1,
    seal_google_fallback_corpus_task_v1,
    seal_offline_revalidated_corpus_task_v1,
    transition_corpus_task_v1,
    validate_gemini_json_first_corpus_plan_v1,
)
from bctc_ai.evaluation.gemini_json_first_corpus_plan_v1 import (  # noqa: E402
    GOOGLE_ROUTE,
    OPENROUTER_ROUTE,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1  # noqa: E402
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    batch_failed_page_requests_v1,
    batch_finalized_requests_v1,
    batch_progress_v1,
    usage_summary_v1,
)

BATCH_RUNNER = ROOT / "scripts/experiments/run_gemini_json_first_batch_v1.py"
OPENROUTER_RUNNER = ROOT / "scripts/experiments/run_gemini_json_first_openrouter_document_v1.py"


class RunGeminiJsonFirstCorpusSupervisorV1Error(RuntimeError):
    pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    initialize = commands.add_parser("init")
    initialize.add_argument("--plan", type=Path, required=True)
    initialize.add_argument("--ledger", type=Path, required=True)
    initialize.add_argument(
        "--prompt-variant", choices=("simple", "compact", "balanced"), default="simple"
    )
    initialize.add_argument("--max-task-attempts", type=int, default=3)

    status = commands.add_parser("status")
    status.add_argument("--ledger", type=Path, required=True)

    repair = commands.add_parser("repair-openrouter")
    repair.add_argument("--plan", type=Path, required=True)
    repair.add_argument("--ledger", type=Path, required=True)
    repair.add_argument("--task-id", required=True)
    repair.add_argument("--source-root", type=Path, required=True)
    repair.add_argument("--database", type=Path, required=True)
    repair.add_argument("--artifact-root", type=Path, required=True)
    repair.add_argument("--google-key-file", type=Path, default=ROOT / "docs/experiments/gemma.txt")
    repair.add_argument("--google-key-slot", type=int, default=2)

    repair_google = commands.add_parser("repair-openrouter-google")
    repair_google.add_argument("--plan", type=Path, required=True)
    repair_google.add_argument("--ledger", type=Path, required=True)
    repair_google.add_argument("--task-id", required=True)
    repair_google.add_argument("--source-root", type=Path, required=True)
    repair_google.add_argument("--database", type=Path, required=True)
    repair_google.add_argument("--artifact-root", type=Path, required=True)
    repair_google.add_argument(
        "--openrouter-key-file", type=Path, default=ROOT / "docs/experiments/openrouter"
    )
    repair_google.add_argument(
        "--google-key-file", type=Path, default=ROOT / "docs/experiments/gemma.txt"
    )
    repair_google.add_argument("--google-key-slot", type=int, default=2)
    repair_google.add_argument("--openrouter-workers", type=int, default=20)
    repair_google.add_argument("--provider-timeout-seconds", type=int, default=900)

    run = commands.add_parser("run")
    run.add_argument("--plan", type=Path, required=True)
    run.add_argument("--ledger", type=Path, required=True)
    run.add_argument("--source-root", type=Path, required=True)
    run.add_argument("--database", type=Path, required=True)
    run.add_argument("--artifact-root", type=Path, required=True)
    run.add_argument("--google-key-file", type=Path, default=ROOT / "docs/experiments/gemma.txt")
    run.add_argument(
        "--google-key-slot",
        type=int,
        help="Force one Google slot; otherwise --google-key-slots is distributed per task.",
    )
    run.add_argument("--google-key-slots", default="1,2")
    run.add_argument(
        "--openrouter-key-file", type=Path, default=ROOT / "docs/experiments/openrouter"
    )
    run.add_argument(
        "--openrouter-workers",
        type=int,
        default=20,
        help="Bounded concurrent page requests for one OpenRouter document (1..30).",
    )
    run.add_argument("--max-active-google", type=int, default=4)
    run.add_argument("--google-poll-interval-seconds", type=float, default=30.0)
    run.add_argument("--google-watch-max-seconds", type=float, default=172_800.0)
    run.add_argument("--provider-timeout-seconds", type=int, default=900)
    run.add_argument("--max-fallback-attempts", type=int, default=2)
    return parser


def _json_file(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(f"JSON artifact is absent: {path}")
    try:
        value = json.loads(path.read_bytes())
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            f"JSON artifact is invalid: {path}"
        ) from exc
    if type(value) is not dict:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error("JSON artifact is not one object")
    return value


def _write_or_verify(path: Path, payload: bytes) -> None:
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                f"immutable supervisor artifact drifted: {path}"
            )
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o444)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def _last_json(stdout: str) -> dict[str, Any]:
    for line in reversed(stdout.splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if type(value) is dict:
            return value
    raise RunGeminiJsonFirstCorpusSupervisorV1Error("provider subprocess returned no JSON receipt")


def _command(command: list[str], *, expected: set[int]) -> tuple[int, dict[str, Any]]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode not in expected:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "provider subprocess failed outside its typed disposition"
        )
    return completed.returncode, _last_json(completed.stdout)


def _plan(path: Path) -> dict[str, Any]:
    return validate_gemini_json_first_corpus_plan_v1(_json_file(path))


def _task_index(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {}
    for document in plan["documents"]:
        for task in document["tasks"]:
            result[task["task_id"]] = {"planned_document": document, "task": task}
    return result


def _google_slots_v1(args: argparse.Namespace) -> list[int]:
    forced = getattr(args, "google_key_slot", None)
    if forced is not None:
        slots = [forced]
    else:
        raw = getattr(args, "google_key_slots", "1,2")
        try:
            slots = [int(value) for value in raw.split(",")]
        except (AttributeError, ValueError) as exc:
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "Google key-slot axis is invalid"
            ) from exc
    if not slots or slots != list(dict.fromkeys(slots)) or any(slot <= 0 for slot in slots):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "Google key-slot axis is empty, duplicate, or nonpositive"
        )
    return slots


def _google_slot_for_task_v1(task_id: str, slots: list[int]) -> int:
    if type(task_id) is not str or not task_id.startswith("gjfptaskv1:"):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error("corpus task ID is invalid")
    digest = task_id.removeprefix("gjfptaskv1:")
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error("corpus task digest is invalid")
    return slots[int(digest[:16], 16) % len(slots)]


def _source(task: dict[str, Any], source_root: Path) -> Path:
    path = source_root / task["relative_path"]
    if path.is_symlink() or not path.is_file():
        raise RunGeminiJsonFirstCorpusSupervisorV1Error("planned source PDF is absent")
    stat = path.stat()
    if stat.st_size != task["source_size_bytes"]:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error("planned source PDF size drifted")
    if sha256(path.read_bytes()).hexdigest() != task["source_sha256"]:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error("planned source PDF SHA-256 drifted")
    return path


def _task_root(task: dict[str, Any], artifact_root: Path) -> Path:
    return artifact_root / task["artifact_relative_path"]


def _google_attempt_root(task: dict[str, Any], artifact_root: Path) -> Path:
    return _task_root(task, artifact_root) / f"google-attempt-{task['attempt_count'] + 1:04d}"


def _google_success_pages(task: dict[str, Any], artifact_root: Path, database: Path) -> set[int]:
    succeeded: set[int] = set()
    task_root = _task_root(task, artifact_root)
    for attempt in sorted(task_root.glob("google-attempt-*")) if task_root.exists() else []:
        receipt_path = attempt / "submission-receipt.json"
        manifest_path = attempt / "manifest.json"
        if not receipt_path.is_file() or not manifest_path.is_file():
            continue
        receipt = _json_file(receipt_path)
        manifest = _json_file(manifest_path)
        dispositions = batch_finalized_requests_v1(database, batch_name=receipt["batch_name"])
        for request in manifest["requests"]:
            if dispositions.get(request["request_id"]) == "INGESTED":
                succeeded.add(request["page"]["physical_page"])
    return succeeded


def _recover_or_submit_google(
    *,
    task: dict[str, Any],
    plan: dict[str, Any],
    ledger: Path,
    source_root: Path,
    database: Path,
    artifact_root: Path,
    google_key_file: Path,
    google_key_slot: int,
    provider_timeout_seconds: int,
) -> dict[str, Any]:
    attempt = _google_attempt_root(task, artifact_root)
    receipt_path = attempt / "submission-receipt.json"
    if receipt_path.is_file():
        _command(
            [
                sys.executable,
                str(BATCH_RUNNER),
                "register-existing",
                "--database",
                str(database),
                "--artifact-dir",
                str(attempt),
            ],
            expected={0},
        )
        submitted = _json_file(receipt_path)
    else:
        if attempt.exists() and any(attempt.iterdir()):
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "incomplete Google attempt has no submission receipt"
            )
        pages = sorted(
            set(range(task["first_physical_page"], task["last_physical_page"] + 1))
            - _google_success_pages(task, artifact_root, database)
        )
        if not pages:
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "retry task has no unresolved Google pages"
            )
        planned = _task_index(plan)[task["task_id"]]
        source = _source(task, source_root)
        command = [
            sys.executable,
            str(BATCH_RUNNER),
            "submit",
            "--pdf",
            str(source),
            "--source-logical-name",
            task["relative_path"],
        ]
        for page in pages:
            command.extend(("--physical-page", str(page)))
        command.extend(
            (
                "--dpi",
                str(plan["policy"]["dpi"]),
                "--prompt-variant",
                corpus_ledger_summary_v1(ledger)["prompt_variant"],
                "--output-contract-mode",
                "json-schema",
                "--display-name",
                planned["task"]["task_id"],
                "--provider",
                "google",
                "--database",
                str(database),
                "--artifact-dir",
                str(attempt),
                "--google-key-file",
                str(google_key_file),
                "--google-key-slot",
                str(google_key_slot),
                "--media-transfer",
                "files",
                "--timeout-seconds",
                str(provider_timeout_seconds),
            )
        )
        _, submitted = _command(command, expected={0})
    return transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state=task["state"],
        next_state="SUBMITTED",
        receipt={
            "artifact_relative_path": attempt.relative_to(artifact_root).as_posix(),
            "batch_name": submitted["batch_name"],
        },
        provider_job_ref=submitted["batch_name"],
    )


def _poll_google(
    *,
    task: dict[str, Any],
    ledger: Path,
    database: Path,
    artifact_root: Path,
    google_key_file: Path,
    provider_timeout_seconds: int,
    max_attempts: int,
) -> dict[str, Any]:
    if task["state"] == "SUBMITTED":
        task = transition_corpus_task_v1(
            ledger,
            task_id=task["task_id"],
            expected_state="SUBMITTED",
            next_state="RUNNING",
            receipt={"batch_name": task["provider_job_ref"], "watch_started": True},
        )
    attempt = _task_root(task, artifact_root) / f"google-attempt-{task['attempt_count']:04d}"
    _command(
        [
            sys.executable,
            str(BATCH_RUNNER),
            "poll",
            "--database",
            str(database),
            "--artifact-dir",
            str(attempt),
            "--google-key-file",
            str(google_key_file),
            "--timeout-seconds",
            str(provider_timeout_seconds),
        ],
        expected={0, 2},
    )
    matching = [
        item
        for item in batch_progress_v1(database)
        if item["batch_name"] == task["provider_job_ref"]
    ]
    if len(matching) != 1:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "polled Google batch is not uniquely present in the page store"
        )
    progress = matching[0]
    if progress["state"] in {"BATCH_STATE_PENDING", "BATCH_STATE_RUNNING"}:
        return task
    if progress["failed_pages"] == 0 and progress["ingested_pages"] == progress["request_count"]:
        next_state = "SUCCEEDED"
    elif task["attempt_count"] >= max_attempts:
        next_state = "FALLBACK_PENDING"
    else:
        next_state = "NEEDS_RETRY"
    return transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="RUNNING",
        next_state=next_state,
        receipt=progress,
    )


def _run_google_fallback(
    *,
    task: dict[str, Any],
    plan: dict[str, Any],
    ledger: Path,
    source_root: Path,
    database: Path,
    artifact_root: Path,
    openrouter_key_file: Path,
    openrouter_workers: int,
    provider_timeout_seconds: int,
    max_fallback_attempts: int,
) -> dict[str, Any]:
    """Run only terminal Google failures through bounded OpenRouter Flex calls."""

    failures = batch_failed_page_requests_v1(database, batch_name=task["provider_job_ref"])
    pages = sorted({failure["physical_page"] for failure in failures})
    if not pages or len(pages) != len(failures):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "Google fallback page frontier is empty or duplicate"
        )
    if task["state"] == "FALLBACK_PENDING":
        task = transition_corpus_task_v1(
            ledger,
            task_id=task["task_id"],
            expected_state="FALLBACK_PENDING",
            next_state="FALLBACK_RUNNING",
            receipt={
                "failed_requests": failures,
                "gateway": "OPENROUTER",
            },
        )
    source = _source(task, source_root)
    fallback_root = _task_root(task, artifact_root) / "openrouter-fallback"
    prior_receipts = len(list((fallback_root / "run-receipts").glob("*.json")))
    fallback_attempt = prior_receipts + 1
    command = [
        sys.executable,
        str(OPENROUTER_RUNNER),
        "--pdf",
        str(source),
        "--source-logical-name",
        task["relative_path"],
        "--database",
        str(database),
        "--artifact-dir",
        str(fallback_root),
        "--dpi",
        str(plan["policy"]["dpi"]),
        "--workers",
        str(min(openrouter_workers, len(pages))),
        "--prompt-variant",
        corpus_ledger_summary_v1(ledger)["prompt_variant"],
        "--output-contract-mode",
        "json-schema",
        "--openrouter-key-file",
        str(openrouter_key_file),
        "--timeout-seconds",
        str(provider_timeout_seconds),
    ]
    for page in pages:
        command.extend(("--physical-page", str(page)))
    return_code, receipt = _command(command, expected={0, 2})
    next_state = (
        "SUCCEEDED"
        if return_code == 0
        else "FALLBACK_PENDING"
        if fallback_attempt < max_fallback_attempts
        else "FAILED"
    )
    return transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="FALLBACK_RUNNING",
        next_state=next_state,
        receipt={
            "fallback_attempt": fallback_attempt,
            "fallback_pages": pages,
            "fallback_result": receipt,
            "gateway": "OPENROUTER",
        },
    )


def _run_openrouter(
    *,
    task: dict[str, Any],
    plan: dict[str, Any],
    ledger: Path,
    source_root: Path,
    database: Path,
    artifact_root: Path,
    openrouter_key_file: Path,
    openrouter_workers: int,
    google_key_file: Path,
    google_key_slot: int,
    provider_timeout_seconds: int,
    max_attempts: int,
) -> dict[str, Any]:
    if task["state"] in {"PENDING", "NEEDS_RETRY"}:
        task = transition_corpus_task_v1(
            ledger,
            task_id=task["task_id"],
            expected_state=task["state"],
            next_state="RUNNING",
            receipt={"document_run_started": True},
        )
    source = _source(task, source_root)
    return_code, receipt = _command(
        [
            sys.executable,
            str(OPENROUTER_RUNNER),
            "--pdf",
            str(source),
            "--source-logical-name",
            task["relative_path"],
            "--database",
            str(database),
            "--artifact-dir",
            str(_task_root(task, artifact_root)),
            "--dpi",
            str(plan["policy"]["dpi"]),
            "--workers",
            str(openrouter_workers),
            "--prompt-variant",
            corpus_ledger_summary_v1(ledger)["prompt_variant"],
            "--output-contract-mode",
            "json-schema",
            "--openrouter-key-file",
            str(openrouter_key_file),
            "--google-key-file",
            str(google_key_file),
            "--google-key-slot",
            str(google_key_slot),
            "--google-standard-mode",
            "on-provider-error",
            "--timeout-seconds",
            str(provider_timeout_seconds),
        ],
        expected={0, 2},
    )
    semantic_failed_pages = receipt.get("semantic_failed_pages")
    if type(semantic_failed_pages) is not list:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter result lacks its semantic-failure frontier"
        )
    next_state = (
        "SUCCEEDED"
        if return_code == 0
        else "FAILED"
        if semantic_failed_pages
        else "FAILED"
        if task["attempt_count"] >= max_attempts
        else "NEEDS_RETRY"
    )
    return transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="RUNNING",
        next_state=next_state,
        receipt=receipt,
    )


def _finalize_google_manifests(
    *,
    plan: dict[str, Any],
    ledger: Path,
    database: Path,
    artifact_root: Path,
) -> list[str]:
    outputs = []
    by_id = {task["task_id"]: task for task in list_corpus_tasks_v1(ledger)}
    for planned in plan["documents"]:
        if planned["route"] != GOOGLE_ROUTE:
            continue
        artifact_dirs: list[Path] = []
        for task in planned["tasks"]:
            row = by_id[task["task_id"]]
            task_root = _task_root(row, artifact_root)
            artifact_dirs.extend(
                attempt
                for attempt in sorted(task_root.glob("google-attempt-*"))
                if (attempt / "manifest.json").is_file()
            )
        fallback_used = any(
            (_task_root(by_id[task["task_id"]], artifact_root) / "openrouter-fallback").exists()
            for task in planned["tasks"]
        )
        output = (
            artifact_root
            / "documents"
            / planned["document_plan_id"].split(":", 1)[1]
            / "document-manifest.json"
        )
        command = [
            sys.executable,
            str(BATCH_RUNNER),
            "document-manifest",
            "--database",
            str(database),
            "--expected-page-count",
            str(planned["document"]["page_count"]),
            "--output",
            str(output),
        ]
        for artifact in artifact_dirs:
            command.extend(("--batch-artifact-dir", str(artifact)))
        if fallback_used:
            command.append("--allow-openrouter-fallback")
        _command(command, expected={0})
        outputs.append(str(output))
    return outputs


def run_corpus(args: argparse.Namespace) -> dict[str, Any]:
    plan = _plan(args.plan)
    if not args.ledger.exists():
        initialize_gemini_json_first_corpus_ledger_v1(args.ledger, plan=plan)
    summary = corpus_ledger_summary_v1(args.ledger)
    if summary["corpus_plan_id"] != plan["corpus_plan_id"]:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error("ledger and plan identity disagree")
    if not 1 <= args.max_active_google <= 32:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error("active Google bound lies outside 1..32")
    if not 1 <= args.openrouter_workers <= 30:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter worker bound lies outside 1..30"
        )
    if not 1 <= args.max_fallback_attempts <= 10:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error("fallback attempt bound lies outside 1..10")
    google_slots = _google_slots_v1(args)
    args.artifact_root.mkdir(parents=True, exist_ok=True)
    _write_or_verify(args.artifact_root / "corpus-plan.json", canonical_json_bytes_v1(plan))
    started = time.monotonic()
    openrouter_executor = ThreadPoolExecutor(
        max_workers=1,
        thread_name_prefix="openrouter-document",
    )
    openrouter_future: Future[dict[str, Any]] | None = None
    google_submit_executor = ThreadPoolExecutor(
        max_workers=min(args.max_active_google, 4),
        thread_name_prefix="google-batch-submit",
    )
    google_submit_futures: dict[Future[dict[str, Any]], str] = {}
    while True:
        if openrouter_future is not None and openrouter_future.done():
            try:
                openrouter_future.result()
            except Exception:
                openrouter_executor.shutdown(wait=True, cancel_futures=True)
                google_submit_executor.shutdown(wait=True, cancel_futures=True)
                raise
            openrouter_future = None
        for future in [future for future in google_submit_futures if future.done()]:
            try:
                future.result()
            except Exception:
                openrouter_executor.shutdown(wait=True, cancel_futures=True)
                google_submit_executor.shutdown(wait=True, cancel_futures=True)
                raise
            del google_submit_futures[future]
        if time.monotonic() - started > args.google_watch_max_seconds:
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "corpus supervisor exceeded its bounded provider wait"
            )
        tasks = list_corpus_tasks_v1(args.ledger)
        failed = [task for task in tasks if task["state"] == "FAILED"]
        unfinished = [task for task in tasks if task["state"] not in {"SUCCEEDED", "FAILED"}]
        if not unfinished:
            if failed:
                openrouter_executor.shutdown(wait=True, cancel_futures=True)
                google_submit_executor.shutdown(wait=True, cancel_futures=True)
                return {"disposition": "FAILED", **corpus_ledger_summary_v1(args.ledger)}
            break
        active_google = [
            task
            for task in unfinished
            if task["route"] == GOOGLE_ROUTE and task["state"] in {"SUBMITTED", "RUNNING"}
        ]
        openrouter = [
            task
            for task in unfinished
            if task["route"] == OPENROUTER_ROUTE
            and task["state"] in {"PENDING", "RUNNING", "NEEDS_RETRY"}
        ]
        if openrouter_future is None and openrouter:
            openrouter_future = openrouter_executor.submit(
                _run_openrouter,
                task=openrouter[0],
                plan=plan,
                ledger=args.ledger,
                source_root=args.source_root,
                database=args.database,
                artifact_root=args.artifact_root,
                openrouter_key_file=args.openrouter_key_file,
                openrouter_workers=args.openrouter_workers,
                google_key_file=args.google_key_file,
                google_key_slot=_google_slot_for_task_v1(openrouter[0]["task_id"], google_slots),
                provider_timeout_seconds=args.provider_timeout_seconds,
                max_attempts=summary["max_task_attempts"],
            )
        available = args.max_active_google - len(active_google) - len(google_submit_futures)
        inflight_google_task_ids = set(google_submit_futures.values())
        for task in [
            item
            for item in unfinished
            if item["route"] == GOOGLE_ROUTE
            and item["state"] in {"PENDING", "NEEDS_RETRY"}
            and item["task_id"] not in inflight_google_task_ids
        ][:available]:
            future = google_submit_executor.submit(
                _recover_or_submit_google,
                task=task,
                plan=plan,
                ledger=args.ledger,
                source_root=args.source_root,
                database=args.database,
                artifact_root=args.artifact_root,
                google_key_file=args.google_key_file,
                google_key_slot=_google_slot_for_task_v1(task["task_id"], google_slots),
                provider_timeout_seconds=args.provider_timeout_seconds,
            )
            google_submit_futures[future] = task["task_id"]
        fallback = [
            task
            for task in unfinished
            if task["route"] == GOOGLE_ROUTE
            and task["state"] in {"FALLBACK_PENDING", "FALLBACK_RUNNING"}
        ]
        if fallback:
            _run_google_fallback(
                task=fallback[0],
                plan=plan,
                ledger=args.ledger,
                source_root=args.source_root,
                database=args.database,
                artifact_root=args.artifact_root,
                openrouter_key_file=args.openrouter_key_file,
                openrouter_workers=args.openrouter_workers,
                provider_timeout_seconds=args.provider_timeout_seconds,
                max_fallback_attempts=args.max_fallback_attempts,
            )
            continue
        if active_google:
            polled = _poll_google(
                task=active_google[0],
                ledger=args.ledger,
                database=args.database,
                artifact_root=args.artifact_root,
                google_key_file=args.google_key_file,
                provider_timeout_seconds=args.provider_timeout_seconds,
                max_attempts=summary["max_task_attempts"],
            )
            if polled["state"] != "RUNNING":
                # Refill the newly free Google slot before starting a document call.
                continue
            if openrouter_future is None:
                time.sleep(args.google_poll_interval_seconds)
                continue
        if openrouter_future is not None:
            time.sleep(min(args.google_poll_interval_seconds, 1.0))
            continue
        if google_submit_futures:
            time.sleep(min(args.google_poll_interval_seconds, 1.0))
            continue
        openrouter_executor.shutdown(wait=True, cancel_futures=True)
        google_submit_executor.shutdown(wait=True, cancel_futures=True)
        raise RunGeminiJsonFirstCorpusSupervisorV1Error("scheduler has no runnable task")

    manifests = _finalize_google_manifests(
        plan=plan,
        ledger=args.ledger,
        database=args.database,
        artifact_root=args.artifact_root,
    )
    result = {
        "disposition": "SUCCEEDED",
        "google_document_manifests": manifests,
        "ledger": corpus_ledger_summary_v1(args.ledger),
        "usage": usage_summary_v1(args.database),
    }
    payload = canonical_json_bytes_v1(result)
    _write_or_verify(
        args.artifact_root / "run-receipts" / (sha256(payload).hexdigest() + ".json"),
        payload,
    )
    openrouter_executor.shutdown(wait=True)
    google_submit_executor.shutdown(wait=True)
    return result


def repair_openrouter_task(args: argparse.Namespace) -> dict[str, Any]:
    """Replay immutable semantic responses and seal one formerly failed document."""

    plan = _plan(args.plan)
    tasks = list_corpus_tasks_v1(args.ledger, states=["FAILED"], route=OPENROUTER_ROUTE)
    matches = [task for task in tasks if task["task_id"] == args.task_id]
    if len(matches) != 1:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "offline repair requires one exact failed OpenRouter task"
        )
    task = matches[0]
    source = _source(task, args.source_root)
    task_root = _task_root(task, args.artifact_root)
    contract = _json_file(task_root / "document-contract.json")
    google_standard_mode = contract.get("google_standard_mode", "disabled")
    if google_standard_mode not in {"disabled", "on-provider-error"}:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "offline repair document fallback mode is invalid"
        )
    command = [
        sys.executable,
        str(OPENROUTER_RUNNER),
        "--pdf",
        str(source),
        "--source-logical-name",
        task["relative_path"],
        "--database",
        str(args.database),
        "--artifact-dir",
        str(task_root),
        "--dpi",
        str(plan["policy"]["dpi"]),
        "--workers",
        str(plan["policy"]["openrouter_workers"]),
        "--prompt-variant",
        corpus_ledger_summary_v1(args.ledger)["prompt_variant"],
        "--output-contract-mode",
        "json-schema",
        "--offline-replay-only",
    ]
    if google_standard_mode != "disabled":
        command.extend(
            (
                "--google-key-file",
                str(args.google_key_file),
                "--google-key-slot",
                str(args.google_key_slot),
                "--google-standard-mode",
                google_standard_mode,
            )
        )
    return_code, result = _command(command, expected={0, 2})
    if return_code != 0 or result.get("disposition") != "SUCCEEDED":
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "offline OpenRouter repair did not close the document"
        )
    replayed_pages = result.get("ingested_pages")
    if type(replayed_pages) is not list or not replayed_pages:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "offline OpenRouter repair replayed no semantic page"
        )
    sealed = seal_offline_revalidated_corpus_task_v1(
        args.ledger,
        task_id=task["task_id"],
        receipt={
            "document_manifest_id": result["manifest_id"],
            "offline_revalidated": True,
            "replayed_pages": replayed_pages,
            "result": result,
        },
    )
    return {
        "disposition": "SUCCEEDED",
        "ledger": corpus_ledger_summary_v1(args.ledger),
        "repaired_task": {
            "attempt_count": sealed["attempt_count"],
            "state": sealed["state"],
            "task_id": sealed["task_id"],
        },
        "result": result,
    }


def repair_openrouter_google_task(args: argparse.Namespace) -> dict[str, Any]:
    """Complete provider-failed OpenRouter pages through direct Google standard."""

    plan = _plan(args.plan)
    tasks = list_corpus_tasks_v1(args.ledger, states=["FAILED"], route=OPENROUTER_ROUTE)
    selected = [task for task in tasks if task["task_id"] == args.task_id]
    if len(selected) != 1:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "Google repair requires one exact failed OpenRouter task"
        )
    task = selected[0]
    try:
        prior = json.loads(task["last_receipt_json"])
    except (TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "failed OpenRouter task receipt is invalid"
        ) from exc
    failed_pages = prior.get("failed_pages") if type(prior) is dict else None
    semantic_pages = prior.get("semantic_failed_pages", []) if type(prior) is dict else None
    if (
        type(failed_pages) is not list
        or not failed_pages
        or failed_pages != sorted(set(failed_pages))
        or type(semantic_pages) is not list
        or semantic_pages != sorted(set(semantic_pages))
        or not set(semantic_pages) <= set(failed_pages)
        or any(
            type(page) is not int
            or page < task["first_physical_page"]
            or page > task["last_physical_page"]
            for page in failed_pages
        )
    ):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "failed OpenRouter provider page frontier is invalid"
        )
    pages = sorted(set(failed_pages) - set(semantic_pages))
    if not pages:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "failed OpenRouter task has no provider page to repair"
        )
    if not 1 <= args.openrouter_workers <= 30:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter worker bound lies outside 1..30"
        )
    source = _source(task, args.source_root)
    repair_root = _task_root(task, args.artifact_root) / "google-standard-repair"
    _, result = _command(
        [
            sys.executable,
            str(OPENROUTER_RUNNER),
            "--pdf",
            str(source),
            "--source-logical-name",
            task["relative_path"],
            "--database",
            str(args.database),
            "--artifact-dir",
            str(repair_root),
            "--dpi",
            str(plan["policy"]["dpi"]),
            "--workers",
            str(args.openrouter_workers),
            "--prompt-variant",
            corpus_ledger_summary_v1(args.ledger)["prompt_variant"],
            "--output-contract-mode",
            "json-schema",
            "--openrouter-key-file",
            str(args.openrouter_key_file),
            "--google-key-file",
            str(args.google_key_file),
            "--google-key-slot",
            str(args.google_key_slot),
            "--google-standard-mode",
            "for-missing",
            "--timeout-seconds",
            str(args.provider_timeout_seconds),
        ],
        expected={0},
    )
    cached_pages = result.get("cached_pages")
    ingested_pages = result.get("ingested_pages")
    if (
        type(cached_pages) is not list
        or cached_pages != sorted(set(cached_pages))
        or type(ingested_pages) is not list
        or ingested_pages != sorted(set(ingested_pages))
        or any(page in ingested_pages for page in semantic_pages)
        or any(page not in cached_pages for page in semantic_pages)
    ):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "Google repair did not preserve replayed semantic pages as cache hits"
        )
    completed_pages = sorted(set(cached_pages + ingested_pages))
    if result.get("disposition") != "SUCCEEDED" or any(
        page not in completed_pages for page in pages
    ):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "Google repair did not complete the failed page frontier"
        )
    sealed = seal_google_fallback_corpus_task_v1(
        args.ledger,
        task_id=task["task_id"],
        receipt={
            "document_manifest_id": result["manifest_id"],
            "fallback_gateway": "GOOGLE_GEMINI_API",
            "fallback_pages": pages,
            "result": result,
        },
    )
    return {
        "disposition": "SUCCEEDED",
        "fallback_pages": pages,
        "manifest_id": result["manifest_id"],
        "task_id": sealed["task_id"],
    }


def main() -> int:
    args = _parser().parse_args()
    if args.command == "init":
        result = initialize_gemini_json_first_corpus_ledger_v1(
            args.ledger,
            plan=_plan(args.plan),
            prompt_variant=args.prompt_variant,
            max_task_attempts=args.max_task_attempts,
        )
    elif args.command == "status":
        result = corpus_ledger_summary_v1(args.ledger)
    elif args.command == "repair-openrouter":
        result = repair_openrouter_task(args)
    elif args.command == "repair-openrouter-google":
        result = repair_openrouter_google_task(args)
    else:
        result = run_corpus(args)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("disposition") != "FAILED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
