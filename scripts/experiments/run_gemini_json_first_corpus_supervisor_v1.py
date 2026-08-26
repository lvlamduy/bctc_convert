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

import fitz

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.gemini_financial_page_json_v1 import (  # noqa: E402
    build_financial_page_json_prompt_v1,
    financial_page_json_response_schema_v1,
)
from bctc_ai.evaluation.gemini_json_first_corpus_ledger_v1 import (  # noqa: E402
    GeminiJsonFirstCorpusLedgerV1Error,
    claim_google_document_for_openrouter_acceleration_v1,
    corpus_ledger_summary_v1,
    initialize_gemini_json_first_corpus_ledger_v1,
    list_corpus_tasks_v1,
    seal_current_document_revalidated_corpus_tasks_v1,
    seal_google_fallback_corpus_task_v1,
    seal_offline_revalidated_corpus_task_v1,
    transition_corpus_task_v1,
    validate_gemini_json_first_corpus_plan_v1,
)
from bctc_ai.evaluation.gemini_json_first_corpus_plan_v1 import (  # noqa: E402
    GOOGLE_ROUTE,
    OPENROUTER_ROUTE,
)
from bctc_ai.evaluation.gemini_json_first_page_render_v1 import (  # noqa: E402
    render_full_pdf_page_v1,
)
from bctc_ai.evaluation.gemini_json_first_provider_v1 import (  # noqa: E402
    GOOGLE_BATCH_SERVICE_TIER,
    GOOGLE_MODEL,
    GOOGLE_STANDARD_SERVICE_TIER,
    OPENROUTER_SERVICE_TIER,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.storage.gemini_current_document_manifest_selection_v1 import (  # noqa: E402
    build_current_document_manifest_selection_v1,
    load_current_document_manifest_selection_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    batch_failed_page_requests_v1,
    batch_finalized_requests_v1,
    batch_progress_v1,
    build_financial_document_manifest_v1,
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
        "--prompt-variant",
        choices=("simple", "items", "scope", "compact", "balanced"),
        default="simple",
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

    repair_items = commands.add_parser("repair-openrouter-items")
    repair_items.add_argument("--plan", type=Path, required=True)
    repair_items.add_argument("--ledger", type=Path, required=True)
    repair_items.add_argument("--task-id", required=True)
    repair_items.add_argument("--source-root", type=Path, required=True)
    repair_items.add_argument("--database", type=Path, required=True)
    repair_items.add_argument("--artifact-root", type=Path, required=True)
    repair_items.add_argument("--physical-page", type=int, action="append", required=True)

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

    current_manifest = commands.add_parser("document-manifest-current")
    current_manifest.add_argument("--plan", type=Path, required=True)
    current_manifest.add_argument("--ledger", type=Path, required=True)
    current_manifest.add_argument("--task-id", required=True)
    current_manifest.add_argument("--source-root", type=Path, required=True)
    current_manifest.add_argument("--database", type=Path, required=True)
    current_manifest.add_argument("--artifact-root", type=Path, required=True)
    current_manifest.add_argument(
        "--page-prompt-variant",
        action="append",
        default=[],
        metavar="PAGE=VARIANT",
    )

    accelerate = commands.add_parser("accelerate-google-document")
    accelerate.add_argument("--plan", type=Path, required=True)
    accelerate.add_argument("--ledger", type=Path, required=True)
    accelerate.add_argument("--task-id", required=True)
    accelerate.add_argument("--source-root", type=Path, required=True)
    accelerate.add_argument("--database", type=Path, required=True)
    accelerate.add_argument("--artifact-root", type=Path, required=True)
    accelerate.add_argument(
        "--openrouter-key-file", type=Path, default=ROOT / "docs/experiments/openrouter"
    )
    accelerate.add_argument(
        "--google-key-file", type=Path, default=ROOT / "docs/experiments/gemma.txt"
    )
    accelerate.add_argument("--google-key-slot", type=int, default=2)
    accelerate.add_argument("--openrouter-workers", type=int, default=25)
    accelerate.add_argument("--provider-timeout-seconds", type=int, default=900)
    accelerate.add_argument("--max-acceleration-attempts", type=int, default=2)

    accelerate_pending = commands.add_parser("accelerate-pending-google")
    accelerate_pending.add_argument("--plan", type=Path, required=True)
    accelerate_pending.add_argument("--ledger", type=Path, required=True)
    accelerate_pending.add_argument("--source-root", type=Path, required=True)
    accelerate_pending.add_argument("--database", type=Path, required=True)
    accelerate_pending.add_argument("--artifact-root", type=Path, required=True)
    accelerate_pending.add_argument(
        "--openrouter-key-file", type=Path, default=ROOT / "docs/experiments/openrouter"
    )
    accelerate_pending.add_argument(
        "--google-key-file", type=Path, default=ROOT / "docs/experiments/gemma.txt"
    )
    accelerate_pending.add_argument("--google-key-slot", type=int, default=2)
    accelerate_pending.add_argument("--openrouter-workers", type=int, default=25)
    accelerate_pending.add_argument("--provider-timeout-seconds", type=int, default=900)
    accelerate_pending.add_argument("--max-acceleration-attempts", type=int, default=2)
    accelerate_pending.add_argument("--max-documents", type=int, default=140)

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


def _is_openrouter_acceleration_task_v1(task: dict[str, Any]) -> bool:
    return (
        task.get("route") == GOOGLE_ROUTE
        and task.get("state") == "RUNNING"
        and type(task.get("provider_job_ref")) is str
        and task["provider_job_ref"].startswith("gjfpaccelv1:claim:")
    )


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
    google_key_file: Path,
    google_key_slot: int,
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
    original_state = task["state"]
    prior_fallback_attempt = 0
    if original_state == "FALLBACK_PENDING":
        try:
            prior_receipt = json.loads(task["last_receipt_json"])
        except (TypeError, json.JSONDecodeError, UnicodeDecodeError):
            prior_receipt = None
        if type(prior_receipt) is dict:
            value = prior_receipt.get("fallback_attempt", 0)
            if type(value) is int and value >= 0:
                prior_fallback_attempt = value
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
    existing_attempts = sorted(
        int(path.name.split("-", 1)[1])
        for path in fallback_root.glob("attempt-*")
        if path.is_dir() and path.name.split("-", 1)[1].isdigit()
    )
    if original_state == "FALLBACK_RUNNING" and existing_attempts:
        fallback_attempt = existing_attempts[-1]
    else:
        fallback_attempt = max(prior_fallback_attempt, *(existing_attempts or [0])) + 1
    fallback_attempt_root = fallback_root / f"attempt-{fallback_attempt:02d}"
    default_variant = corpus_ledger_summary_v1(ledger)["prompt_variant"]
    prompt_frontiers: dict[str, list[int]] = {}
    for failure in failures:
        error = failure.get("error")
        provider_error = error.get("provider_error") if type(error) is dict else None
        if type(provider_error) is dict and provider_error.get("finish_reason") == "RECITATION":
            variant = "scope"
        elif type(error) is dict and error.get("error_type") == "GeminiFinancialPageJsonV1Error":
            variant = "items"
        else:
            variant = default_variant
        prompt_frontiers.setdefault(variant, []).append(failure["physical_page"])

    return_code = 0
    fallback_results = []
    for variant in (default_variant, "scope", "items"):
        frontier = sorted(set(prompt_frontiers.get(variant, [])))
        if not frontier:
            continue
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
            str(fallback_attempt_root / variant),
            "--dpi",
            str(plan["policy"]["dpi"]),
            "--workers",
            str(min(openrouter_workers, len(frontier))),
            "--prompt-variant",
            variant,
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
        ]
        for page in frontier:
            command.extend(("--physical-page", str(page)))
        code, result = _command(command, expected={0, 2})
        fallback_results.append(
            {
                "physical_pages": frontier,
                "prompt_variant": variant,
                "result": result,
            }
        )
        if code != 0:
            return_code = 2
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
            "fallback_results": fallback_results,
            "gateway": "OPENROUTER",
        },
    )


def _retry_prompt_frontiers_v1(task: dict[str, Any]) -> dict[str, list[int]] | None:
    """Classify one exact failed-page frontier without inspecting page content."""

    if task["state"] != "NEEDS_RETRY":
        return None
    try:
        prior = json.loads(task["last_receipt_json"])
    except (TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter retry receipt is invalid"
        ) from exc
    return _retry_prompt_frontiers_from_receipt_v1(
        prior,
        first_physical_page=task["first_physical_page"],
        last_physical_page=task["last_physical_page"],
    )


def _retry_prompt_frontiers_from_receipt_v1(
    prior: Any,
    *,
    first_physical_page: int,
    last_physical_page: int,
) -> dict[str, list[int]]:
    """Classify a typed failed-page receipt into bounded adaptive prompts."""

    failed = prior.get("failed_pages") if type(prior) is dict else None
    semantic = prior.get("semantic_failed_pages") if type(prior) is dict else None
    unresolved = prior.get("unresolved_pages", []) if type(prior) is dict else None
    recitation = prior.get("recitation_failed_pages", []) if type(prior) is dict else None
    if (
        type(failed) is not list
        or not failed
        or failed != sorted(set(failed))
        or type(semantic) is not list
        or semantic != sorted(set(semantic))
        or type(unresolved) is not list
        or unresolved != sorted(set(unresolved))
        or type(recitation) is not list
        or recitation != sorted(set(recitation))
        or not (set(semantic) | set(unresolved) | set(recitation)).issubset(failed)
        or set(recitation) & (set(semantic) | set(unresolved))
        or any(
            type(page) is not int or page < first_physical_page or page > last_physical_page
            for page in failed
        )
    ):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter retry is not one exact failed-page frontier"
        )
    protected = set(semantic) | set(unresolved)
    recitation_pages = set(recitation)
    return {
        "default": sorted(set(failed) - protected - recitation_pages),
        "items": sorted(protected),
        "scope": sorted(recitation_pages),
    }


def _provider_retry_pages_v1(task: dict[str, Any]) -> list[int] | None:
    frontiers = _retry_prompt_frontiers_v1(task)
    if frontiers is None:
        return None
    return sorted(page for pages in frontiers.values() for page in pages)


def _protected_retry_pages_v1(task: dict[str, Any]) -> list[int]:
    """Return pages known to contain financial content before an item retry."""

    if task["state"] != "NEEDS_RETRY":
        return []
    frontiers = _retry_prompt_frontiers_v1(task)
    if frontiers is None:
        return []
    return frontiers["items"]


def _page_variant_manifest_v1(
    *,
    task: dict[str, Any],
    ledger: Path,
    database: Path,
    artifact_root: Path,
    page_image_sha256s: dict[int, str],
    page_prompt_variants: dict[int, str],
    write: bool = True,
) -> dict[str, Any]:
    """Build one document manifest with explicit prompt variants by page."""

    expected_pages = list(range(task["first_physical_page"], task["last_physical_page"] + 1))
    allowed_variants = {"balanced", "compact", "items", "scope", "simple"}
    if (
        not page_prompt_variants
        or any(type(page) is not int or page not in expected_pages for page in page_prompt_variants)
        or any(variant not in allowed_variants for variant in page_prompt_variants.values())
        or expected_pages != list(range(1, task["document_page_count"] + 1))
    ):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "page prompt variant frontier is invalid or not a full document"
        )
    default_variant = corpus_ledger_summary_v1(ledger)["prompt_variant"]
    if default_variant not in allowed_variants:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error("corpus default prompt variant is invalid")
    page_prompt_sha256s = {
        page: sha256(
            build_financial_page_json_prompt_v1(
                variant=page_prompt_variants.get(page, default_variant)
            ).encode("utf-8")
        ).hexdigest()
        for page in expected_pages
    }
    manifest = build_financial_document_manifest_v1(
        database,
        source_sha256=task["source_sha256"],
        source_logical_name=task["relative_path"],
        expected_physical_pages=expected_pages,
        page_image_sha256s=page_image_sha256s,
        prompt_sha256=page_prompt_sha256s,
        response_schema_sha256=canonical_json_sha256_v1(financial_page_json_response_schema_v1()),
        requested_model=GOOGLE_MODEL,
        allowed_gateway_service_tiers=[
            {
                "gateway": "GOOGLE_GEMINI_API",
                "requested_service_tier": GOOGLE_STANDARD_SERVICE_TIER,
            },
            {
                "gateway": "OPENROUTER",
                "requested_service_tier": OPENROUTER_SERVICE_TIER,
            },
        ],
    )
    if write:
        _write_or_verify(
            _task_root(task, artifact_root) / "adaptive-prompt-document-manifest.json",
            canonical_json_bytes_v1(manifest),
        )
    return manifest


def _mixed_prompt_manifest_v1(
    *,
    task: dict[str, Any],
    ledger: Path,
    database: Path,
    artifact_root: Path,
    page_image_sha256s: dict[int, str],
    repair_pages: list[int],
    write: bool = True,
) -> dict[str, Any]:
    """Backward-compatible item-only manifest wrapper."""

    if not repair_pages or repair_pages != sorted(set(repair_pages)):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "item-only repair page frontier is duplicate or empty"
        )
    manifest = _page_variant_manifest_v1(
        task=task,
        ledger=ledger,
        database=database,
        artifact_root=artifact_root,
        page_image_sha256s=page_image_sha256s,
        page_prompt_variants={page: "items" for page in repair_pages},
        write=False,
    )
    if write:
        _write_or_verify(
            _task_root(task, artifact_root) / "mixed-prompt-document-manifest.json",
            canonical_json_bytes_v1(manifest),
        )
    return manifest


def _summary_page_image_sha256s_v1(
    value: Any,
    *,
    allowed_pages: list[int],
) -> dict[int, str]:
    if type(value) is not list:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "provider result lacks its page image frontier"
        )
    result: dict[int, str] = {}
    for item in value:
        if type(item) is not dict or set(item) != {"image_sha256", "physical_page"}:
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "provider page image frontier fields drifted"
            )
        page = item["physical_page"]
        image_sha = item["image_sha256"]
        if (
            type(page) is not int
            or page not in allowed_pages
            or page in result
            or type(image_sha) is not str
            or len(image_sha) != 64
            or any(character not in "0123456789abcdef" for character in image_sha)
        ):
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "provider page image frontier is invalid"
            )
        result[page] = image_sha
    if sorted(result) != allowed_pages:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "provider page image frontier is incomplete"
        )
    return result


def _current_page_image_sha256s_v1(
    *,
    task: dict[str, Any],
    source_root: Path,
    dpi: int,
) -> dict[int, str]:
    source = _source(task, source_root)
    expected_pages = list(range(1, task["document_page_count"] + 1))
    result: dict[int, str] = {}
    with fitz.open(source) as document:
        if document.page_count != task["document_page_count"]:
            raise RunGeminiJsonFirstCorpusSupervisorV1Error("planned source PDF page count drifted")
        for physical_page in expected_pages:
            rendered = render_full_pdf_page_v1(
                document[physical_page - 1],
                physical_page=physical_page,
                dpi=dpi,
                source_sha256=task["source_sha256"],
            )
            result[physical_page] = rendered.page["image_sha256"]
    return result


def _page_prompt_variants_v1(
    *,
    expected_pages: list[int],
    default_variant: str,
    overrides: list[str],
) -> dict[int, str]:
    allowed = {"balanced", "compact", "items", "scope", "simple"}
    if default_variant not in allowed:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error("default page prompt variant is invalid")
    result = {page: default_variant for page in expected_pages}
    seen: set[int] = set()
    for override in overrides:
        if type(override) is not str or override.count("=") != 1:
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "page prompt override must be PAGE=VARIANT"
            )
        raw_page, variant = override.split("=", 1)
        try:
            page = int(raw_page)
        except ValueError as exc:
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "page prompt override page is invalid"
            ) from exc
        if page not in result or page in seen or variant not in allowed:
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "page prompt override is duplicate, out of range, or invalid"
            )
        seen.add(page)
        result[page] = variant
    return result


def _write_current_document_manifest_selection_v1(
    *,
    artifact_root: Path,
    planned: dict[str, Any],
    task: dict[str, Any],
    manifest: dict[str, Any],
    page_images: dict[int, str],
    variants: dict[int, str],
) -> tuple[Path, dict[str, Any]]:
    """Persist a content-addressed manifest and advance one append-only head."""

    document_root = artifact_root / "documents" / planned["document_plan_id"].split(":", 1)[1]
    payload = canonical_json_bytes_v1(manifest) + b"\n"
    manifest_digest = manifest["document_manifest_id"].split(":", 2)[2]
    relative_path = Path("current-document-manifests") / f"{manifest_digest}.json"
    output = document_root / relative_path
    _write_or_verify(output, payload)

    existing = load_current_document_manifest_selection_v1(
        document_root,
        document_plan_id=planned["document_plan_id"],
        source_sha256=task["source_sha256"],
    )
    if (
        existing is not None
        and existing[0]["document_manifest_id"] == manifest["document_manifest_id"]
    ):
        selection = existing[0]
    else:
        selection = build_current_document_manifest_selection_v1(
            document_plan_id=planned["document_plan_id"],
            source_sha256=task["source_sha256"],
            document_manifest_id=manifest["document_manifest_id"],
            document_manifest_ref={
                "path": relative_path.as_posix(),
                "sha256": sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            },
            page_image_frontier_sha256=canonical_json_sha256_v1(
                [
                    {"image_sha256": page_images[page], "physical_page": page}
                    for page in sorted(page_images)
                ]
            ),
            page_prompt_frontier_sha256=canonical_json_sha256_v1(
                [
                    {"physical_page": page, "prompt_variant": variants[page]}
                    for page in sorted(variants)
                ]
            ),
            prior_selection_ids=[] if existing is None else [existing[0]["selection_id"]],
        )
        selection_output = (
            document_root
            / "current-document-manifest-selections"
            / (selection["selection_id"].split(":", 2)[2] + ".json")
        )
        _write_or_verify(selection_output, canonical_json_bytes_v1(selection) + b"\n")
    legacy = document_root / "current-document-manifest.json"
    if not legacy.exists():
        _write_or_verify(legacy, payload)
    return output, selection


def build_current_document_manifest(args: argparse.Namespace) -> dict[str, Any]:
    """Seal one document only from current whole-page images and explicit prompts."""

    plan = _plan(args.plan)
    indexed = _task_index(plan)
    selected = indexed.get(args.task_id)
    if selected is None:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "current document manifest task is absent from the corpus plan"
        )
    planned = selected["planned_document"]
    planned_task_ids = {task["task_id"] for task in planned["tasks"]}
    tasks = [
        task for task in list_corpus_tasks_v1(args.ledger) if task["task_id"] in planned_task_ids
    ]

    def admissible(task: dict[str, Any]) -> bool:
        return task["state"] in {"FAILED", "SUCCEEDED"} or (
            task["state"] == "RUNNING"
            and task["route"] == GOOGLE_ROUTE
            and type(task.get("provider_job_ref")) is str
            and task["provider_job_ref"].startswith("gjfpaccelv1:claim:")
        )

    acceleration_claims = {
        task["provider_job_ref"]
        for task in tasks
        if task["state"] == "RUNNING" and admissible(task)
    }
    if (
        len(tasks) != len(planned_task_ids)
        or any(not admissible(task) for task in tasks)
        or len(acceleration_claims) > 1
    ):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "current document manifest requires a terminal or claimed acceleration frontier"
        )
    task = next(task for task in tasks if task["task_id"] == args.task_id)
    expected_pages = list(range(1, task["document_page_count"] + 1))
    variants = _page_prompt_variants_v1(
        expected_pages=expected_pages,
        default_variant=corpus_ledger_summary_v1(args.ledger)["prompt_variant"],
        overrides=args.page_prompt_variant,
    )
    prompt_sha256s = {
        page: sha256(
            build_financial_page_json_prompt_v1(variant=variant).encode("utf-8")
        ).hexdigest()
        for page, variant in variants.items()
    }
    page_images = _current_page_image_sha256s_v1(
        task=task,
        source_root=args.source_root,
        dpi=plan["policy"]["dpi"],
    )
    manifest = build_financial_document_manifest_v1(
        args.database,
        source_sha256=task["source_sha256"],
        source_logical_name=task["relative_path"],
        expected_physical_pages=expected_pages,
        page_image_sha256s=page_images,
        prompt_sha256=prompt_sha256s,
        response_schema_sha256=canonical_json_sha256_v1(financial_page_json_response_schema_v1()),
        requested_model=GOOGLE_MODEL,
        allowed_gateway_service_tiers=[
            {
                "gateway": "GOOGLE_GEMINI_API",
                "requested_service_tier": GOOGLE_STANDARD_SERVICE_TIER,
            },
            {
                "gateway": "GOOGLE_GEMINI_BATCH_API",
                "requested_service_tier": GOOGLE_BATCH_SERVICE_TIER,
            },
            {
                "gateway": "OPENROUTER",
                "requested_service_tier": OPENROUTER_SERVICE_TIER,
            },
        ],
    )
    unresolved_pages = [
        page["physical_page"] for page in manifest["pages"] if page["status"] == "UNRESOLVED_PAGE"
    ]
    if unresolved_pages:
        return {
            "disposition": "NEEDS_RETRY",
            "document_manifest_id": manifest["document_manifest_id"],
            "unresolved_pages": unresolved_pages,
        }
    output, selection = _write_current_document_manifest_selection_v1(
        artifact_root=args.artifact_root,
        planned=planned,
        task=task,
        manifest=manifest,
        page_images=page_images,
        variants=variants,
    )
    failed_task_ids = sorted(task["task_id"] for task in tasks if task["state"] == "FAILED")
    repaired_tasks = []
    if failed_task_ids:
        repaired_tasks = seal_current_document_revalidated_corpus_tasks_v1(
            args.ledger,
            task_id=args.task_id,
            receipt={
                "current_document_revalidated": True,
                "document_manifest_id": manifest["document_manifest_id"],
                "page_image_sha256s": [
                    {"image_sha256": page_images[page], "physical_page": page}
                    for page in expected_pages
                ],
                "page_prompt_variants": [
                    {"physical_page": page, "prompt_variant": variants[page]}
                    for page in expected_pages
                ],
                "repaired_task_ids": failed_task_ids,
                "revalidated_pages": expected_pages,
                "status_counts": manifest["status_counts"],
            },
        )
    return {
        "disposition": "SUCCEEDED",
        "document_manifest_id": manifest["document_manifest_id"],
        "output": str(output),
        "page_count": manifest["page_count"],
        "page_prompt_variants": [
            {"physical_page": page, "prompt_variant": variant} for page, variant in variants.items()
        ],
        "status_counts": manifest["status_counts"],
        "totals": manifest["totals"],
        "repaired_task_ids": [task["task_id"] for task in repaired_tasks],
        "selection_id": selection["selection_id"],
    }


def accelerate_google_document(args: argparse.Namespace) -> dict[str, Any]:
    """Run one all-pending Google document through bounded OpenRouter concurrency."""

    if not 1 <= args.openrouter_workers <= 30:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter acceleration worker bound lies outside 1..30"
        )
    if not 1 <= args.max_acceleration_attempts <= 10:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter acceleration attempt bound lies outside 1..10"
        )
    plan = _plan(args.plan)
    selected = _task_index(plan).get(args.task_id)
    if selected is None or selected["planned_document"]["route"] != GOOGLE_ROUTE:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter acceleration task is not one planned Google document"
        )
    planned = selected["planned_document"]
    claim = claim_google_document_for_openrouter_acceleration_v1(args.ledger, task_id=args.task_id)
    tasks = claim["tasks"]
    if all(task["state"] == "SUCCEEDED" for task in tasks):
        return {
            "claim_id": claim["claim_id"],
            "disposition": "ALREADY_SUCCEEDED",
            "task_ids": [task["task_id"] for task in tasks],
        }
    if any(task["state"] not in {"RUNNING", "SUCCEEDED"} for task in tasks):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter acceleration claim did not reserve its document"
        )
    task = tasks[0]
    expected_pages = list(range(1, task["document_page_count"] + 1))
    current_images = _current_page_image_sha256s_v1(
        task=task,
        source_root=args.source_root,
        dpi=plan["policy"]["dpi"],
    )
    source = _source(task, args.source_root)
    document_root = (
        args.artifact_root
        / "documents"
        / planned["document_plan_id"].split(":", 1)[1]
        / "openrouter-acceleration"
    )
    receipt_root = document_root / "run-receipts"
    attempt_number = len(list(receipt_root.glob("*.json"))) + 1
    if attempt_number > args.max_acceleration_attempts:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter acceleration attempt bound is exhausted"
        )
    attempt_root = document_root / f"attempt-{attempt_number:02d}"
    default_variant = corpus_ledger_summary_v1(args.ledger)["prompt_variant"]

    def run_frontier(*, pages: list[int] | None, prompt_variant: str):
        artifact_dir = attempt_root / "base"
        if pages is not None:
            artifact_dir = attempt_root / "adaptive-retry" / prompt_variant
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
            str(artifact_dir),
            "--dpi",
            str(plan["policy"]["dpi"]),
            "--workers",
            str(
                args.openrouter_workers
                if pages is None
                else min(args.openrouter_workers, len(pages))
            ),
            "--prompt-variant",
            prompt_variant,
            "--output-contract-mode",
            "json-schema",
            "--openrouter-key-file",
            str(args.openrouter_key_file),
            "--google-key-file",
            str(args.google_key_file),
            "--google-key-slot",
            str(args.google_key_slot),
            "--google-standard-mode",
            "on-provider-error",
            "--timeout-seconds",
            str(args.provider_timeout_seconds),
        ]
        if pages is not None:
            for page in pages:
                command.extend(("--physical-page", str(page)))
        return _command(command, expected={0, 2})

    return_code, initial = run_frontier(pages=None, prompt_variant=default_variant)
    if (
        _summary_page_image_sha256s_v1(
            initial.get("page_image_sha256s"), allowed_pages=expected_pages
        )
        != current_images
    ):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter acceleration base image frontier drifted"
        )
    variants = {page: default_variant for page in expected_pages}
    provider_results = [
        {"physical_pages": expected_pages, "prompt_variant": default_variant, "result": initial}
    ]
    protected_pages: list[int] = []
    if return_code != 0:
        frontiers = _retry_prompt_frontiers_from_receipt_v1(
            initial,
            first_physical_page=1,
            last_physical_page=task["document_page_count"],
        )
        protected_pages = frontiers["items"]
        retry_code = 0
        prompt_pages: dict[str, list[int]] = {}
        for variant, pages in (
            (default_variant, frontiers["default"]),
            ("scope", frontiers["scope"]),
            ("items", frontiers["items"]),
        ):
            prompt_pages.setdefault(variant, []).extend(pages)
        for prompt_variant, pages in (
            (variant, sorted(set(pages))) for variant, pages in prompt_pages.items()
        ):
            if not pages:
                continue
            code, result = run_frontier(pages=pages, prompt_variant=prompt_variant)
            if _summary_page_image_sha256s_v1(
                result.get("page_image_sha256s"), allowed_pages=pages
            ) != {page: current_images[page] for page in pages}:
                raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                    "OpenRouter acceleration retry image frontier drifted"
                )
            provider_results.append(
                {
                    "physical_pages": pages,
                    "prompt_variant": prompt_variant,
                    "result": result,
                }
            )
            variants.update({page: prompt_variant for page in pages})
            if code != 0:
                retry_code = 2
        return_code = retry_code

    receipt_material: dict[str, Any] = {
        "acceleration_attempt": attempt_number,
        "claim_id": claim["claim_id"],
        "format_version": "GEMINI_JSON_FIRST_OPENROUTER_ACCELERATION_RECEIPT_V1",
        "provider_results": provider_results,
        "task_ids": [task["task_id"] for task in tasks],
    }
    if return_code != 0:
        receipt_material["disposition"] = "NEEDS_RETRY"
        payload = canonical_json_bytes_v1(receipt_material)
        _write_or_verify(receipt_root / (sha256(payload).hexdigest() + ".json"), payload)
        return receipt_material

    prompt_sha256s = {
        page: sha256(
            build_financial_page_json_prompt_v1(variant=variant).encode("utf-8")
        ).hexdigest()
        for page, variant in variants.items()
    }
    manifest = build_financial_document_manifest_v1(
        args.database,
        source_sha256=task["source_sha256"],
        source_logical_name=task["relative_path"],
        expected_physical_pages=expected_pages,
        page_image_sha256s=current_images,
        prompt_sha256=prompt_sha256s,
        response_schema_sha256=canonical_json_sha256_v1(financial_page_json_response_schema_v1()),
        requested_model=GOOGLE_MODEL,
        allowed_gateway_service_tiers=[
            {
                "gateway": "GOOGLE_GEMINI_API",
                "requested_service_tier": GOOGLE_STANDARD_SERVICE_TIER,
            },
            {
                "gateway": "GOOGLE_GEMINI_BATCH_API",
                "requested_service_tier": GOOGLE_BATCH_SERVICE_TIER,
            },
            {
                "gateway": "OPENROUTER",
                "requested_service_tier": OPENROUTER_SERVICE_TIER,
            },
        ],
    )
    unresolved_pages = [
        page["physical_page"] for page in manifest["pages"] if page["status"] == "UNRESOLVED_PAGE"
    ]
    dropped_pages = _semantic_retry_no_relevant_pages_v1(manifest, protected_pages=protected_pages)
    if unresolved_pages or dropped_pages:
        receipt_material.update(
            {
                "disposition": "NEEDS_RETRY",
                "semantic_item_no_relevant_pages": dropped_pages,
                "unresolved_pages": unresolved_pages,
            }
        )
        payload = canonical_json_bytes_v1(receipt_material)
        _write_or_verify(receipt_root / (sha256(payload).hexdigest() + ".json"), payload)
        return receipt_material
    manifest_result = build_current_document_manifest(
        argparse.Namespace(
            artifact_root=args.artifact_root,
            database=args.database,
            ledger=args.ledger,
            page_prompt_variant=[
                f"{page}={variant}"
                for page, variant in variants.items()
                if variant != default_variant
            ],
            plan=args.plan,
            source_root=args.source_root,
            task_id=args.task_id,
        )
    )
    if manifest_result.get("document_manifest_id") != manifest["document_manifest_id"]:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter acceleration manifest does not replay exactly"
        )
    receipt_material.update(
        {
            "disposition": "SUCCEEDED",
            "document_manifest_id": manifest["document_manifest_id"],
            "selection_id": manifest_result["selection_id"],
        }
    )
    payload = canonical_json_bytes_v1(receipt_material)
    _write_or_verify(receipt_root / (sha256(payload).hexdigest() + ".json"), payload)
    completed = []
    for row in tasks:
        if row["state"] == "RUNNING":
            updated = transition_corpus_task_v1(
                args.ledger,
                task_id=row["task_id"],
                expected_state="RUNNING",
                next_state="SUCCEEDED",
                receipt=receipt_material,
            )
            completed.append(updated["task_id"])
    return {
        **receipt_material,
        "completed_task_ids": completed,
        "ledger": corpus_ledger_summary_v1(args.ledger),
    }


def _all_pending_google_documents_v1(*, plan: dict[str, Any], ledger: Path) -> list[dict[str, Any]]:
    """Return smallest-first documents whose complete Google task frontier is pending."""

    rows = list_corpus_tasks_v1(ledger, route=GOOGLE_ROUTE)
    row_by_task_id = {row["task_id"]: row for row in rows}
    if len(row_by_task_id) != len(rows):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "Google acceleration ledger task frontier is duplicate"
        )
    candidates: list[dict[str, Any]] = []
    for document in plan["documents"]:
        if document["route"] != GOOGLE_ROUTE:
            continue
        task_ids = [task["task_id"] for task in document["tasks"]]
        document_rows = [row_by_task_id.get(task_id) for task_id in task_ids]
        if any(row is None for row in document_rows):
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "Google acceleration plan and ledger task frontiers differ"
            )
        if all(row["state"] == "PENDING" for row in document_rows):
            candidates.append(
                {
                    "document_page_count": document["document"]["page_count"],
                    "relative_path": document["document"]["relative_path"],
                    "task_id": task_ids[0],
                }
            )
    return sorted(
        candidates,
        key=lambda item: (
            item["document_page_count"],
            item["relative_path"],
            item["task_id"],
        ),
    )


def accelerate_pending_google_documents(args: argparse.Namespace) -> dict[str, Any]:
    """Continuously claim pending Google documents and finish them through OpenRouter."""

    if not 1 <= args.max_documents <= 140:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter acceleration document bound lies outside 1..140"
        )
    plan = _plan(args.plan)
    completed: list[dict[str, Any]] = []
    race_count = 0
    while len(completed) < args.max_documents:
        candidates = _all_pending_google_documents_v1(plan=plan, ledger=args.ledger)
        if not candidates:
            break
        claimed = False
        for candidate in candidates:
            document_args = argparse.Namespace(**vars(args), task_id=candidate["task_id"])
            try:
                result = accelerate_google_document(document_args)
            except GeminiJsonFirstCorpusLedgerV1Error as exc:
                if "requires one all-pending document" not in str(exc):
                    raise
                race_count += 1
                continue
            claimed = True
            completed.append(
                {
                    "disposition": result["disposition"],
                    "document_manifest_id": result.get("document_manifest_id"),
                    "document_page_count": candidate["document_page_count"],
                    "relative_path": candidate["relative_path"],
                    "selection_id": result.get("selection_id"),
                    "task_id": candidate["task_id"],
                }
            )
            if result["disposition"] == "NEEDS_RETRY":
                return {
                    "completed_documents": completed,
                    "disposition": "NEEDS_RETRY",
                    "ledger": corpus_ledger_summary_v1(args.ledger),
                    "race_count": race_count,
                }
            break
        if not claimed:
            # Google may have claimed every candidate between the read and write locks.
            if not _all_pending_google_documents_v1(plan=plan, ledger=args.ledger):
                break
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "OpenRouter acceleration could not reserve a stable pending document"
            )
    return {
        "completed_documents": completed,
        "disposition": "SUCCEEDED",
        "ledger": corpus_ledger_summary_v1(args.ledger),
        "race_count": race_count,
    }


def _semantic_retry_no_relevant_pages_v1(
    manifest: dict[str, Any], *, protected_pages: list[int]
) -> list[int]:
    """Reject a known financial page that an item retry silently drops."""

    pages = manifest.get("pages")
    if type(pages) is not list:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "mixed-prompt manifest lacks its page frontier"
        )
    status_by_page: dict[int, str] = {}
    for page in pages:
        if type(page) is not dict:
            raise RunGeminiJsonFirstCorpusSupervisorV1Error("mixed-prompt manifest page is invalid")
        physical_page = page.get("physical_page")
        status = page.get("status")
        if type(physical_page) is not int or type(status) is not str:
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "mixed-prompt manifest page identity is invalid"
            )
        if physical_page in status_by_page:
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "mixed-prompt manifest page frontier is duplicate"
            )
        status_by_page[physical_page] = status
    if any(page not in status_by_page for page in protected_pages):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "mixed-prompt manifest omits a protected retry page"
        )
    return [
        page for page in protected_pages if status_by_page[page] == "NO_RELEVANT_FINANCIAL_CONTENT"
    ]


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
    retry_frontiers = _retry_prompt_frontiers_v1(task)
    retry_pages = (
        None
        if retry_frontiers is None
        else sorted(page for pages in retry_frontiers.values() for page in pages)
    )
    protected_retry_pages = _protected_retry_pages_v1(task)
    if task["state"] in {"PENDING", "NEEDS_RETRY"}:
        task = transition_corpus_task_v1(
            ledger,
            task_id=task["task_id"],
            expected_state=task["state"],
            next_state="RUNNING",
            receipt={"document_run_started": True},
        )
    source = _source(task, source_root)
    default_prompt_variant = corpus_ledger_summary_v1(ledger)["prompt_variant"]

    def run_frontier(*, pages: list[int] | None, prompt_variant: str) -> tuple[int, dict[str, Any]]:
        selected_artifact_dir = _task_root(task, artifact_root)
        if pages is not None:
            selected_artifact_dir = selected_artifact_dir / "adaptive-retry" / prompt_variant
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
            str(selected_artifact_dir),
            "--dpi",
            str(plan["policy"]["dpi"]),
            "--workers",
            str(openrouter_workers),
            "--prompt-variant",
            prompt_variant,
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
        ]
        if pages is not None:
            for page in pages:
                command.extend(("--physical-page", str(page)))
        return _command(command, expected={0, 2})

    if retry_frontiers is None:
        return_code, receipt = run_frontier(
            pages=None,
            prompt_variant=default_prompt_variant,
        )
        semantic_failed_pages = receipt.get("semantic_failed_pages")
        recitation_failed_pages = receipt.get("recitation_failed_pages", [])
        if type(semantic_failed_pages) is not list or type(recitation_failed_pages) is not list:
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "OpenRouter result lacks a typed retry frontier"
            )
    else:
        current_page_images = _current_page_image_sha256s_v1(
            task=task,
            source_root=source_root,
            dpi=plan["policy"]["dpi"],
        )
        retry_results = []
        retry_variants: dict[int, str] = {}
        return_code = 0
        aggregate: dict[str, list[int]] = {
            "cached_pages": [],
            "failed_pages": [],
            "ingested_pages": [],
            "offline_missing_pages": [],
            "recitation_failed_pages": [],
            "semantic_failed_pages": [],
            "unresolved_pages": [],
        }
        prompt_pages: dict[str, list[int]] = {}
        for prompt_variant, pages in (
            (default_prompt_variant, retry_frontiers["default"]),
            ("scope", retry_frontiers["scope"]),
            ("items", retry_frontiers["items"]),
        ):
            prompt_pages.setdefault(prompt_variant, []).extend(pages)
        prompt_frontiers = tuple(
            (variant, sorted(set(pages))) for variant, pages in prompt_pages.items()
        )
        for prompt_variant, pages in prompt_frontiers:
            if not pages:
                continue
            code, result = run_frontier(pages=pages, prompt_variant=prompt_variant)
            result_images = _summary_page_image_sha256s_v1(
                result.get("page_image_sha256s"),
                allowed_pages=pages,
            )
            if result_images != {page: current_page_images[page] for page in pages}:
                raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                    "retry result does not bind the current whole-page images"
                )
            for field in aggregate:
                values = result.get(field, [])
                if (
                    type(values) is not list
                    or values != sorted(set(values))
                    or any(page not in pages for page in values)
                ):
                    raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                        "adaptive retry result page frontier is invalid"
                    )
                aggregate[field].extend(values)
            retry_results.append(
                {
                    "physical_pages": pages,
                    "prompt_variant": prompt_variant,
                    "result": result,
                }
            )
            retry_variants.update({page: prompt_variant for page in pages})
            if code != 0:
                return_code = 2
        receipt = {
            **{field: sorted(values) for field, values in aggregate.items()},
            "adaptive_retry_results": retry_results,
            "alternate_prompt_pages": retry_pages,
            "alternate_prompt_variants": [
                {"physical_pages": pages, "prompt_variant": variant}
                for variant, pages in prompt_frontiers
                if pages
            ],
            "protected_retry_pages": protected_retry_pages,
        }
        if return_code == 0:
            manifest = _page_variant_manifest_v1(
                task=task,
                ledger=ledger,
                database=database,
                artifact_root=artifact_root,
                page_image_sha256s=current_page_images,
                page_prompt_variants=retry_variants,
                write=False,
            )
            dropped_semantic_pages = _semantic_retry_no_relevant_pages_v1(
                manifest, protected_pages=protected_retry_pages
            )
            if dropped_semantic_pages:
                receipt["semantic_item_no_relevant_pages"] = dropped_semantic_pages
                return_code = 2
            else:
                manifest_name = (
                    "mixed-prompt-document-manifest.json"
                    if set(retry_variants.values()) == {"items"}
                    else "adaptive-prompt-document-manifest.json"
                )
                _write_or_verify(
                    _task_root(task, artifact_root) / manifest_name,
                    canonical_json_bytes_v1(manifest),
                )
                receipt.update(
                    {
                        "manifest_id": manifest["document_manifest_id"],
                        "page_image_sha256s": [
                            {"image_sha256": image_sha, "physical_page": page}
                            for page, image_sha in current_page_images.items()
                        ],
                        "revalidated_document_pages": list(
                            range(1, task["document_page_count"] + 1)
                        ),
                    }
                )
            if len(retry_results) == 1:
                receipt["alternate_prompt_variant"] = retry_results[0]["prompt_variant"]
    next_state = (
        "SUCCEEDED"
        if return_code == 0
        else "FAILED"
        if retry_pages is not None or task["attempt_count"] >= max_attempts
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
        rows = [by_id[task["task_id"]] for task in planned["tasks"]]
        acceleration_claims = {row["provider_job_ref"] for row in rows}
        accelerated = (
            len(acceleration_claims) == 1
            and all(row["state"] == "SUCCEEDED" for row in rows)
            and all(
                type(row["provider_job_ref"]) is str
                and row["provider_job_ref"].startswith("gjfpaccelv1:claim:")
                for row in rows
            )
        )
        current_revalidated = False
        for row in rows:
            try:
                last_receipt = json.loads(row["last_receipt_json"])
            except (TypeError, json.JSONDecodeError, UnicodeDecodeError):
                continue
            if (
                type(last_receipt) is dict
                and last_receipt.get("current_document_revalidated") is True
            ):
                current_revalidated = True
        if accelerated or current_revalidated:
            document_root = (
                artifact_root / "documents" / planned["document_plan_id"].split(":", 1)[1]
            )
            selected = load_current_document_manifest_selection_v1(
                document_root,
                document_plan_id=planned["document_plan_id"],
                source_sha256=planned["document"]["source_sha256"],
            )
            if selected is None:
                raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                    "current Google document lacks its selected revalidated manifest"
                )
            _selection, selected_manifest_path = selected
            selected_manifest = _json_file(selected_manifest_path)
            selected_document = selected_manifest.get("document")
            if (
                type(selected_document) is not dict
                or selected_manifest.get("page_count") != planned["document"]["page_count"]
                or selected_document.get("source_sha256") != planned["document"]["source_sha256"]
                or selected_document.get("source_logical_name")
                != planned["document"]["relative_path"]
            ):
                raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                    "current Google document manifest binding drifted"
                )
            outputs.append(str(selected_manifest_path))
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
    next_google_poll_at = 0.0
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
            if task["route"] == GOOGLE_ROUTE
            and task["state"] in {"SUBMITTED", "RUNNING"}
            and not _is_openrouter_acceleration_task_v1(task)
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
                google_key_file=args.google_key_file,
                google_key_slot=_google_slot_for_task_v1(fallback[0]["task_id"], google_slots),
                openrouter_workers=args.openrouter_workers,
                provider_timeout_seconds=args.provider_timeout_seconds,
                max_fallback_attempts=args.max_fallback_attempts,
            )
            continue
        if active_google:
            now = time.monotonic()
            if now >= next_google_poll_at:
                polled = _poll_google(
                    task=active_google[0],
                    ledger=args.ledger,
                    database=args.database,
                    artifact_root=args.artifact_root,
                    google_key_file=args.google_key_file,
                    provider_timeout_seconds=args.provider_timeout_seconds,
                    max_attempts=summary["max_task_attempts"],
                )
                next_google_poll_at = time.monotonic() + args.google_poll_interval_seconds
                if polled["state"] != "RUNNING":
                    # Refill the newly free Google slot before polling another batch.
                    continue
            delay = max(0.0, next_google_poll_at - time.monotonic())
            if delay:
                if openrouter_future is not None or google_submit_futures:
                    delay = min(delay, 1.0)
                time.sleep(delay)
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
    cached_pages = result.get("cached_pages")
    expected_pages = list(range(task["first_physical_page"], task["last_physical_page"] + 1))
    if (
        type(replayed_pages) is not list
        or replayed_pages != sorted(set(replayed_pages))
        or type(cached_pages) is not list
        or cached_pages != sorted(set(cached_pages))
        or sorted(set(replayed_pages) | set(cached_pages)) != expected_pages
    ):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "offline OpenRouter repair did not revalidate its complete page frontier"
        )
    sealed = seal_offline_revalidated_corpus_task_v1(
        args.ledger,
        task_id=task["task_id"],
        receipt={
            "document_manifest_id": result["manifest_id"],
            "offline_revalidated": True,
            "replayed_pages": replayed_pages,
            "revalidated_pages": expected_pages,
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


def repair_openrouter_items_task(args: argparse.Namespace) -> dict[str, Any]:
    """Seal one failed document from explicit cached item-only page versions.

    No provider call is made here.  The V3 manifest binds the default prompt
    hash on every unaffected page and the distinct ``items`` prompt hash only
    on the caller-declared recitation frontier.
    """

    plan = _plan(args.plan)
    tasks = list_corpus_tasks_v1(args.ledger, states=["FAILED"], route=OPENROUTER_ROUTE)
    matches = [task for task in tasks if task["task_id"] == args.task_id]
    if len(matches) != 1:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "item-only repair requires one exact failed OpenRouter task"
        )
    task = matches[0]
    _source(task, args.source_root)
    repair_pages = sorted(set(args.physical_page))
    if len(repair_pages) != len(args.physical_page):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "item-only repair page frontier is duplicate"
        )
    manifest = _mixed_prompt_manifest_v1(
        task=task,
        ledger=args.ledger,
        database=args.database,
        artifact_root=args.artifact_root,
        page_image_sha256s=_current_page_image_sha256s_v1(
            task=task,
            source_root=args.source_root,
            dpi=plan["policy"]["dpi"],
        ),
        repair_pages=repair_pages,
    )
    expected_pages = list(range(1, task["document_page_count"] + 1))
    result = {
        "alternate_prompt_pages": repair_pages,
        "alternate_prompt_variant": "items",
        "cached_pages": expected_pages,
        "disposition": "SUCCEEDED",
        "failed_pages": [],
        "ingested_pages": [],
        "manifest_id": manifest["document_manifest_id"],
        "offline_missing_pages": [],
        "page_count": len(expected_pages),
        "semantic_failed_pages": [],
        "usage": usage_summary_v1(args.database),
    }
    sealed = seal_google_fallback_corpus_task_v1(
        args.ledger,
        task_id=task["task_id"],
        receipt={
            "document_manifest_id": manifest["document_manifest_id"],
            "fallback_gateway": "GOOGLE_GEMINI_API",
            "fallback_pages": repair_pages,
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
    elif args.command == "repair-openrouter-items":
        result = repair_openrouter_items_task(args)
    elif args.command == "repair-openrouter-google":
        result = repair_openrouter_google_task(args)
    elif args.command == "document-manifest-current":
        result = build_current_document_manifest(args)
    elif args.command == "accelerate-google-document":
        result = accelerate_google_document(args)
    elif args.command == "accelerate-pending-google":
        result = accelerate_pending_google_documents(args)
    else:
        result = run_corpus(args)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("disposition") not in {"FAILED", "NEEDS_RETRY"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
