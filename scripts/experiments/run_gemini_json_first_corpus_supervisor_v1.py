#!/usr/bin/env python3
"""Initialize, run, resume, and report the Gemini JSON-first corpus plan."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
from collections import Counter
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
    openrouter_failed_task_repair_frontier_v1,
    recover_failed_openrouter_artifact_collision_v1,
    requeue_failed_openrouter_corpus_task_v1,
    seal_current_document_revalidated_corpus_tasks_v1,
    seal_google_fallback_corpus_task_v1,
    seal_offline_revalidated_corpus_task_v1,
    seal_openrouter_exhausted_page_repair_corpus_task_v1,
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
    OPENROUTER_STANDARD_FALLBACK_SERVICE_TIER,
    GeminiJsonFirstProviderV1Error,
    load_openrouter_api_key_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import (  # noqa: E402
    build_current_corpus_manifest_index_v1,
)
from bctc_ai.storage.gemini_current_document_manifest_selection_v1 import (  # noqa: E402
    build_current_document_manifest_selection_v1,
    load_current_document_manifest_selection_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    GeminiFinancialPageStoreV1Error,
    batch_failed_page_requests_v1,
    batch_finalized_requests_v1,
    batch_progress_v1,
    build_financial_document_manifest_v1,
    document_page_extraction_frontier_v1,
    document_page_image_frontier_v1,
    selected_page_extraction_receipts_v1,
    usage_summary_v1,
)

BATCH_RUNNER = ROOT / "scripts/experiments/run_gemini_json_first_batch_v1.py"
OPENROUTER_RUNNER = ROOT / "scripts/experiments/run_gemini_json_first_openrouter_document_v1.py"
GOOGLE_SUBMIT_RETRY_DELAY_SECONDS = 30.0
GOOGLE_SUBMIT_WORKERS = 1
RETRYABLE_GOOGLE_UPLOAD_DISPOSITION = "RETRYABLE_GOOGLE_UPLOAD_START"
OPENROUTER_CREDENTIAL_COMMANDS = frozenset(
    {
        "accelerate-google-document",
        "accelerate-pending-google",
        "repair-openrouter-flex-failed",
        "repair-openrouter-flex-pages",
        "repair-openrouter-google",
        "run",
        "run-openrouter-task",
    }
)


class RunGeminiJsonFirstCorpusSupervisorV1Error(RuntimeError):
    pass


class _ProviderSubprocessError(RunGeminiJsonFirstCorpusSupervisorV1Error):
    def __init__(self, *, returncode: int, stdout: str, stderr: str) -> None:
        super().__init__("provider subprocess failed outside its typed disposition")
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _preflight_openrouter_credential_v1(path: Path) -> None:
    """Validate the paid gateway credential before any task state mutation."""

    try:
        load_openrouter_api_key_v1(path)
    except GeminiJsonFirstProviderV1Error as exc:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter credential preflight failed before task execution"
        ) from exc


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

    requeue = commands.add_parser("requeue-openrouter")
    requeue.add_argument("--plan", type=Path, required=True)
    requeue.add_argument("--ledger", type=Path, required=True)
    requeue.add_argument("--task-id", required=True)

    recover_collision = commands.add_parser("recover-openrouter-artifact-collision")
    recover_collision.add_argument("--plan", type=Path, required=True)
    recover_collision.add_argument("--ledger", type=Path, required=True)
    recover_collision.add_argument("--task-id", required=True)
    recover_collision.add_argument("--artifact-root", type=Path, required=True)

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

    repair_flex = commands.add_parser("repair-openrouter-flex-pages")
    repair_flex.add_argument("--plan", type=Path, required=True)
    repair_flex.add_argument("--ledger", type=Path, required=True)
    repair_flex.add_argument("--task-id", required=True)
    repair_flex.add_argument("--source-root", type=Path, required=True)
    repair_flex.add_argument("--database", type=Path, required=True)
    repair_flex.add_argument("--artifact-root", type=Path, required=True)
    repair_flex.add_argument(
        "--openrouter-key-file", type=Path, default=ROOT / "docs/experiments/openrouter"
    )
    repair_flex.add_argument(
        "--google-key-file", type=Path, default=ROOT / "docs/experiments/gemma.txt"
    )
    repair_flex.add_argument("--repair-attempt", type=int, choices=(1, 2), required=True)
    repair_flex.add_argument("--openrouter-workers", type=int, default=20)
    repair_flex.add_argument("--provider-timeout-seconds", type=int, default=900)

    repair_failed_flex = commands.add_parser("repair-openrouter-flex-failed")
    repair_failed_flex.add_argument("--plan", type=Path, required=True)
    repair_failed_flex.add_argument("--ledger", type=Path, required=True)
    repair_failed_flex.add_argument("--source-root", type=Path, required=True)
    repair_failed_flex.add_argument("--database", type=Path, required=True)
    repair_failed_flex.add_argument("--artifact-root", type=Path, required=True)
    repair_failed_flex.add_argument(
        "--openrouter-key-file", type=Path, default=ROOT / "docs/experiments/openrouter"
    )
    repair_failed_flex.add_argument(
        "--google-key-file", type=Path, default=ROOT / "docs/experiments/gemma.txt"
    )
    repair_failed_flex.add_argument("--openrouter-workers", type=int, default=1)
    repair_failed_flex.add_argument("--provider-timeout-seconds", type=int, default=900)
    repair_failed_flex.add_argument("--max-repair-actions", type=int, default=558)
    repair_failed_flex.add_argument(
        "--openrouter-circuit-cooldown-seconds", type=float, default=300.0
    )

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

    corpus_manifest = commands.add_parser("corpus-manifest-current")
    corpus_manifest.add_argument("--plan", type=Path, required=True)
    corpus_manifest.add_argument("--ledger", type=Path, required=True)
    corpus_manifest.add_argument("--source-root", type=Path, required=True)
    corpus_manifest.add_argument("--database", type=Path, required=True)
    corpus_manifest.add_argument("--artifact-root", type=Path, required=True)

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
    accelerate.add_argument(
        "--openrouter-only",
        action="store_true",
        help="Disable direct-Google fallback for every OpenRouter page request.",
    )

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
    accelerate_pending.add_argument(
        "--openrouter-only",
        action="store_true",
        help="Disable direct-Google fallback for every OpenRouter page request.",
    )

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
    run.add_argument(
        "--openrouter-circuit-cooldown-seconds",
        type=float,
        default=300.0,
        help="Delay the next OpenRouter document after a single-worker transient circuit trip.",
    )
    run.add_argument("--max-active-google", type=int, default=4)
    run.add_argument("--google-poll-interval-seconds", type=float, default=30.0)
    run.add_argument("--google-watch-max-seconds", type=float, default=172_800.0)
    run.add_argument("--provider-timeout-seconds", type=int, default=900)
    run.add_argument("--max-fallback-attempts", type=int, default=2)
    run.add_argument(
        "--openrouter-only",
        action="store_true",
        help="Disable direct-Google fallback for every OpenRouter task.",
    )
    run_one = commands.add_parser("run-openrouter-task")
    run_one.add_argument("--plan", type=Path, required=True)
    run_one.add_argument("--ledger", type=Path, required=True)
    run_one.add_argument("--task-id", required=True)
    run_one.add_argument("--source-root", type=Path, required=True)
    run_one.add_argument("--database", type=Path, required=True)
    run_one.add_argument("--artifact-root", type=Path, required=True)
    run_one.add_argument(
        "--google-key-file", type=Path, default=ROOT / "docs/experiments/gemma.txt"
    )
    run_one.add_argument(
        "--openrouter-key-file", type=Path, default=ROOT / "docs/experiments/openrouter"
    )
    run_one.add_argument("--openrouter-workers", type=int, default=20)
    run_one.add_argument("--provider-timeout-seconds", type=int, default=900)
    run_one.add_argument(
        "--openrouter-only",
        action="store_true",
        help="Required: disable direct-Google fallback for this task.",
    )
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
        raise _ProviderSubprocessError(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
    try:
        receipt = _last_json(completed.stdout)
    except RunGeminiJsonFirstCorpusSupervisorV1Error as exc:
        raise _ProviderSubprocessError(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr + f"\n{type(exc).__name__}: {exc}\n",
        ) from exc
    return completed.returncode, receipt


def _record_openrouter_subprocess_failure_v1(
    *,
    error: _ProviderSubprocessError,
    task: dict[str, Any],
    ledger: Path,
    max_attempts: int,
) -> dict[str, Any]:
    """Make an unexpected child exit resumable instead of stranding RUNNING."""

    if task.get("state") != "RUNNING":
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter subprocess failure is not bound to one running task"
        )
    attempt_count = task.get("attempt_count")
    if type(attempt_count) is not int or not 1 <= attempt_count <= max_attempts:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter subprocess failure attempt count is invalid"
        )
    next_state = "FAILED" if attempt_count >= max_attempts else "NEEDS_RETRY"
    stdout = error.stdout.encode("utf-8", errors="surrogatepass")
    stderr = error.stderr.encode("utf-8", errors="surrogatepass")
    return transition_corpus_task_v1(
        ledger,
        task_id=task["task_id"],
        expected_state="RUNNING",
        next_state=next_state,
        receipt={
            "disposition": "OPENROUTER_PROVIDER_SUBPROCESS_FAILURE",
            "provider_returncode": error.returncode,
            "provider_stderr_bytes": len(stderr),
            "provider_stderr_sha256": sha256(stderr).hexdigest(),
            "provider_stdout_bytes": len(stdout),
            "provider_stdout_sha256": sha256(stdout).hexdigest(),
            "retry_allowed": next_state == "NEEDS_RETRY",
        },
    )


def _retryable_google_upload_start_failure_v1(error: _ProviderSubprocessError) -> bool:
    if error.returncode != 1:
        return False
    marker = "Google file upload start returned HTTP "
    if marker in error.stderr:
        suffix = error.stderr.rsplit(marker, 1)[1].splitlines()[0]
        try:
            status = int(suffix)
        except ValueError:
            return False
        return status in {429, 500, 502, 503, 504}
    return "Google file upload start failed or timed out" in error.stderr


def _google_submit_capacity_v1(*, active_count: int, future_count: int, max_active: int) -> int:
    provider_capacity = max(0, max_active - active_count - future_count)
    uploader_capacity = max(0, GOOGLE_SUBMIT_WORKERS - future_count)
    return min(provider_capacity, uploader_capacity)


def _google_submit_ready_v1(
    *,
    task_id: str,
    now: float,
    global_not_before: float,
    task_not_before: dict[str, float],
) -> bool:
    return now >= global_not_before and now >= task_not_before.get(task_id, 0.0)


def _defer_retryable_google_upload_v1(
    *, task: dict[str, Any], attempt: Path, artifact_root: Path
) -> dict[str, Any]:
    unsafe_names = {
        "batch-input.jsonl",
        "manifest.json",
        "submission-receipt.json",
        "submission-response.json",
    }
    if any((attempt / name).exists() for name in unsafe_names):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "retryable Google upload failure crossed the safe pre-submission boundary"
        )
    if attempt.exists():
        unexpected = {path.name for path in attempt.iterdir()} - {"uploaded-files"}
        if unexpected:
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "retryable Google upload failure has an unsafe artifact shape"
            )
    material = {
        "disposition": RETRYABLE_GOOGLE_UPLOAD_DISPOSITION,
        "format_version": "GEMINI_JSON_FIRST_GOOGLE_UPLOAD_DEFERRAL_V1",
        "provider_failure_kind": "GOOGLE_FILE_UPLOAD_START_TRANSIENT",
        "task_id": task["task_id"],
    }
    deferral_id = "gjfpgudv1:deferral:" + canonical_json_sha256_v1(material)
    receipt = {**material, "deferral_id": deferral_id}
    receipt_path = (
        _task_root(task, artifact_root)
        / "google-submit-deferrals"
        / (deferral_id.rsplit(":", 1)[1] + ".json")
    )
    _write_or_verify(receipt_path, canonical_json_bytes_v1(receipt) + b"\n")
    return {
        "disposition": RETRYABLE_GOOGLE_UPLOAD_DISPOSITION,
        "receipt": receipt,
        "state": task["state"],
        "task_id": task["task_id"],
    }


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


def _adaptive_retry_artifact_dir_v1(
    *,
    task_root: Path,
    prompt_variant: str,
    pages: list[int],
) -> Path:
    """Bind immutable retry artifacts to one exact prompt/page frontier."""

    if (
        type(prompt_variant) is not str
        or not prompt_variant
        or type(pages) is not list
        or not pages
        or pages != sorted(set(pages))
        or any(type(page) is not int or page <= 0 for page in pages)
    ):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "adaptive retry artifact frontier is invalid"
        )
    frontier_sha256 = sha256(canonical_json_bytes_v1(pages)).hexdigest()
    return task_root / "adaptive-retry" / prompt_variant / f"pages-{frontier_sha256}"


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


def _quarantine_pre_submission_google_uploads_v1(attempt: Path) -> Path:
    """Preserve an interrupted file-upload frontier that cannot have submitted a batch."""

    children = sorted(attempt.iterdir())
    if len(children) != 1 or children[0].name != "uploaded-files" or not children[0].is_dir():
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "incomplete Google attempt is beyond its safe pre-submission upload boundary"
        )
    uploaded = []
    for path in sorted(children[0].iterdir()):
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_nlink != 1
            or path.suffix != ".json"
            or path.name == "batch-input.json"
        ):
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "incomplete Google upload frontier contains an unsafe artifact"
            )
        raw = path.read_bytes()
        try:
            value = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "incomplete Google upload receipt is invalid"
            ) from exc
        if type(value) is not dict or type(value.get("file")) is not dict:
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "incomplete Google upload receipt fields drifted"
            )
        uploaded.append(
            {
                "path": path.relative_to(attempt).as_posix(),
                "sha256": sha256(raw).hexdigest(),
                "size_bytes": len(raw),
            }
        )
    if not uploaded:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "incomplete Google upload frontier is empty"
        )
    material = {
        "attempt_name": attempt.name,
        "disposition": "QUARANTINED_PRE_SUBMISSION_UPLOADS",
        "format_version": "GEMINI_JSON_FIRST_GOOGLE_INCOMPLETE_ATTEMPT_V1",
        "uploaded_files": uploaded,
    }
    quarantine_id = "gjfpgqv1:quarantine:" + canonical_json_sha256_v1(material)
    receipt = {**material, "quarantine_id": quarantine_id}
    quarantine_root = attempt.parent / "abandoned-google-attempts"
    quarantine = quarantine_root / quarantine_id.split(":", 2)[2]
    if quarantine.exists():
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "incomplete Google upload quarantine identity already exists"
        )
    quarantine_root.mkdir(parents=True, exist_ok=True)
    os.replace(attempt, quarantine)
    _write_or_verify(
        quarantine / "quarantine-receipt.json",
        canonical_json_bytes_v1(receipt) + b"\n",
    )
    return quarantine


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
            _quarantine_pre_submission_google_uploads_v1(attempt)
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
        try:
            _, submitted = _command(command, expected={0})
        except _ProviderSubprocessError as error:
            if not _retryable_google_upload_start_failure_v1(error):
                raise
            return _defer_retryable_google_upload_v1(
                task=task,
                attempt=attempt,
                artifact_root=artifact_root,
            )
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
    prior_receipt = None
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
    prior_item_semantic_pages: set[int] = set()
    if type(prior_receipt) is dict:
        prior_results = prior_receipt.get("fallback_results")
        if type(prior_results) is list:
            for prior_result in prior_results:
                result = prior_result.get("result") if type(prior_result) is dict else None
                semantic = result.get("semantic_failed_pages") if type(result) is dict else None
                if (
                    type(prior_result) is dict
                    and prior_result.get("prompt_variant") == "items"
                    and type(semantic) is list
                    and semantic == sorted(set(semantic))
                    and all(type(page) is int for page in semantic)
                ):
                    prior_item_semantic_pages.update(semantic)
    prompt_frontiers: dict[str, list[int]] = {}
    for failure in failures:
        error = failure.get("error")
        provider_error = error.get("provider_error") if type(error) is dict else None
        if type(provider_error) is dict and provider_error.get("finish_reason") == "RECITATION":
            variant = "scope"
        elif type(error) is dict and error.get("error_type") == "GeminiFinancialPageJsonV1Error":
            variant = (
                "balanced" if failure["physical_page"] in prior_item_semantic_pages else "items"
            )
        else:
            variant = default_variant
        prompt_frontiers.setdefault(variant, []).append(failure["physical_page"])

    return_code = 0
    fallback_results = []
    for variant in (default_variant, "scope", "items", "balanced"):
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
            "--openrouter-route-policy",
            "flex-then-standard",
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

    if task["state"] not in {"NEEDS_RETRY", "RUNNING"}:
        return None
    try:
        prior = json.loads(task["last_receipt_json"])
    except (TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter retry receipt is invalid"
        ) from exc
    if task["state"] == "RUNNING" and not (
        type(prior) is dict
        and prior.get("format_version")
        == "GEMINI_JSON_FIRST_OPENROUTER_LOCAL_ARTIFACT_COLLISION_RECOVERY_V1"
        and prior.get("recovery_same_attempt") is True
    ):
        return None
    subprocess_fields = {
        "disposition",
        "provider_returncode",
        "provider_stderr_bytes",
        "provider_stderr_sha256",
        "provider_stdout_bytes",
        "provider_stdout_sha256",
        "retry_allowed",
    }
    if type(prior) is dict and set(prior) == subprocess_fields:
        digests = (prior["provider_stderr_sha256"], prior["provider_stdout_sha256"])
        if (
            prior["disposition"] == "OPENROUTER_PROVIDER_SUBPROCESS_FAILURE"
            and type(prior["provider_returncode"]) is int
            and type(prior["provider_stderr_bytes"]) is int
            and prior["provider_stderr_bytes"] >= 0
            and type(prior["provider_stdout_bytes"]) is int
            and prior["provider_stdout_bytes"] >= 0
            and all(
                type(digest) is str
                and len(digest) == 64
                and all(character in "0123456789abcdef" for character in digest)
                for digest in digests
            )
            and prior["retry_allowed"] is True
        ):
            # The child did not return a page frontier. Re-enter the whole
            # document command; its image/prompt cache ensures only missing
            # pages reach the provider.
            return None
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


def _prior_acceleration_provider_failures_v1(
    receipt_root: Path,
) -> dict[str, set[int]]:
    """Replay provider-only failures from immutable prior acceleration receipts."""

    failures: dict[str, set[int]] = {}
    attempts: set[int] = set()
    for path in receipt_root.glob("*.json"):
        receipt = _json_file(path)
        attempt = receipt.get("acceleration_attempt")
        results = receipt.get("provider_results")
        if (
            receipt.get("format_version") != "GEMINI_JSON_FIRST_OPENROUTER_ACCELERATION_RECEIPT_V1"
            or type(attempt) is not int
            or attempt <= 0
            or attempt in attempts
            or type(results) is not list
        ):
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "prior OpenRouter acceleration receipt is invalid"
            )
        attempts.add(attempt)
        for item in results:
            if type(item) is not dict:
                raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                    "prior OpenRouter acceleration result is invalid"
                )
            variant = item.get("prompt_variant")
            pages = item.get("physical_pages")
            result = item.get("result")
            if (
                type(variant) is not str
                or type(pages) is not list
                or not pages
                or pages != sorted(set(pages))
                or any(type(page) is not int or page <= 0 for page in pages)
                or type(result) is not dict
            ):
                raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                    "prior OpenRouter acceleration result frontier is invalid"
                )
            failed = result.get("failed_pages")
            if failed == []:
                continue
            frontiers = _retry_prompt_frontiers_from_receipt_v1(
                result,
                first_physical_page=min(pages),
                last_physical_page=max(pages),
            )
            if not set(failed).issubset(pages):
                raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                    "prior OpenRouter acceleration failed outside its result frontier"
                )
            failures.setdefault(variant, set()).update(frontiers["default"])
    return failures


def _missing_current_default_pages_v1(
    *,
    database: Path,
    task: dict[str, Any],
    expected_pages: list[int],
    current_images: dict[int, str],
    default_variant: str,
) -> list[int]:
    """Find only pages without one preferred, authenticated default-prompt version."""

    prompt_sha256 = sha256(
        build_financial_page_json_prompt_v1(variant=default_variant).encode("utf-8")
    ).hexdigest()
    missing = []
    for page in expected_pages:
        try:
            build_financial_document_manifest_v1(
                database,
                source_sha256=task["source_sha256"],
                source_logical_name=task["relative_path"],
                expected_physical_pages=[page],
                page_image_sha256s={page: current_images[page]},
                prompt_sha256=prompt_sha256,
                response_schema_sha256=canonical_json_sha256_v1(
                    financial_page_json_response_schema_v1()
                ),
                requested_model=GOOGLE_MODEL,
                allowed_gateway_service_tiers=_allowed_gateway_service_tiers_v1(),
                preferred_gateway_service_tiers=_preferred_gateway_service_tiers_v1(),
            )
        except GeminiFinancialPageStoreV1Error as exc:
            if str(exc) != "document manifest page frontier is incomplete":
                raise
            missing.append(page)
    return missing


def _provider_retry_pages_v1(task: dict[str, Any]) -> list[int] | None:
    frontiers = _retry_prompt_frontiers_v1(task)
    if frontiers is None:
        return None
    return sorted(page for pages in frontiers.values() for page in pages)


def _protected_retry_pages_v1(task: dict[str, Any]) -> list[int]:
    """Return pages known to contain financial content before an item retry."""

    frontiers = _retry_prompt_frontiers_v1(task)
    if frontiers is None:
        return []
    return frontiers["items"]


def _successful_historical_prompt_context_v1(
    *,
    ledger: Path,
    task: dict[str, Any],
) -> tuple[dict[int, str], list[int]]:
    """Replay successful adaptive page variants from earlier task attempts.

    A later provider-only retry must not forget an ``items`` or ``scope`` page
    that succeeded in an earlier attempt.  The complete document manifest is a
    page-by-page prompt frontier, so defaulting such a page back to the corpus
    prompt would either select no version or silently select the wrong one.
    """

    expected_pages = set(range(task["first_physical_page"], task["last_physical_page"] + 1))
    allowed_variants = {"balanced", "compact", "items", "scope", "simple"}
    uri = f"file:{ledger.resolve()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        rows = connection.execute(
            "SELECT receipt_json FROM task_event WHERE task_id=? ORDER BY event_ordinal",
            (task["task_id"],),
        ).fetchall()
    finally:
        connection.close()
    successful_variants: dict[int, str] = {}
    protected_pages: set[int] = set()
    for (receipt_bytes,) in rows:
        try:
            receipt = json.loads(receipt_bytes)
        except (TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "historical OpenRouter retry receipt is invalid"
            ) from exc
        variants = receipt.get("alternate_prompt_variants") if type(receipt) is dict else None
        if variants is None:
            continue
        failed = receipt.get("failed_pages")
        protected = receipt.get("protected_retry_pages", [])
        if (
            type(variants) is not list
            or not variants
            or type(failed) is not list
            or failed != sorted(set(failed))
            or type(protected) is not list
            or protected != sorted(set(protected))
            or any(type(page) is not int or page not in expected_pages for page in failed)
            or any(type(page) is not int or page not in expected_pages for page in protected)
        ):
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "historical OpenRouter prompt frontier is invalid"
            )
        attempted: set[int] = set()
        page_variants: dict[int, str] = {}
        for item in variants:
            if type(item) is not dict or set(item) != {"physical_pages", "prompt_variant"}:
                raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                    "historical OpenRouter prompt variant is invalid"
                )
            pages = item["physical_pages"]
            variant = item["prompt_variant"]
            if (
                type(pages) is not list
                or not pages
                or pages != sorted(set(pages))
                or variant not in allowed_variants
                or any(type(page) is not int or page not in expected_pages for page in pages)
                or attempted.intersection(pages)
            ):
                raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                    "historical OpenRouter prompt variant frontier is invalid"
                )
            attempted.update(pages)
            page_variants.update({page: variant for page in pages})
        if not set(failed).issubset(attempted):
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "historical OpenRouter failure lies outside its prompt frontier"
            )
        for page in attempted - set(failed):
            successful_variants[page] = page_variants[page]
        protected_pages.update(protected)
    return successful_variants, sorted(protected_pages)


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
            {
                "gateway": "OPENROUTER",
                "requested_service_tier": OPENROUTER_STANDARD_FALLBACK_SERVICE_TIER,
            },
        ],
        preferred_gateway_service_tiers=[
            {
                "gateway": "OPENROUTER",
                "requested_service_tier": OPENROUTER_SERVICE_TIER,
            },
            {
                "gateway": "OPENROUTER",
                "requested_service_tier": OPENROUTER_STANDARD_FALLBACK_SERVICE_TIER,
            },
            {
                "gateway": "GOOGLE_GEMINI_API",
                "requested_service_tier": GOOGLE_STANDARD_SERVICE_TIER,
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


def _manifest_page_image_sha256s_v1(
    manifest: dict[str, Any],
    *,
    expected_pages: list[int],
    dpi: int,
) -> dict[int, str]:
    """Recover the exact image receipt already bound to every selected JSON."""

    pages = manifest.get("pages")
    if (
        type(pages) is not list
        or [page.get("physical_page") for page in pages if type(page) is dict] != expected_pages
    ):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "selected document page image receipt frontier is invalid"
        )
    frontier = []
    for page in pages:
        image = page.get("image")
        if (
            type(image) is not dict
            or set(image)
            != {
                "height",
                "media_type",
                "render_dpi",
                "sha256",
                "size_bytes",
                "width",
            }
            or image["render_dpi"] != dpi
            or image["media_type"] not in {"image/png", "image/jpeg"}
            or any(
                type(image[field]) is not int or image[field] <= 0
                for field in ("height", "size_bytes", "width")
            )
        ):
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "selected document page image receipt is invalid"
            )
        frontier.append({"image_sha256": image["sha256"], "physical_page": page["physical_page"]})
    result = _summary_page_image_sha256s_v1(frontier, allowed_pages=expected_pages)
    contract = manifest.get("extraction_contract")
    contract_frontier = contract.get("page_image_sha256s") if type(contract) is dict else None
    if contract_frontier is not None and contract_frontier != frontier:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "selected document image receipt differs from extraction contract"
        )
    return result


def _manifest_extraction_frontier_v1(
    *,
    database: Path,
    manifest: dict[str, Any],
    expected_pages: list[int],
    dpi: int,
    source_sha256: str,
    source_logical_name: str,
) -> dict[str, Any]:
    """Cross-bind one manifest to the immutable extraction rows it selected."""

    pages = manifest.get("pages")
    page_images = _manifest_page_image_sha256s_v1(
        manifest,
        expected_pages=expected_pages,
        dpi=dpi,
    )
    receipts = selected_page_extraction_receipts_v1(
        database,
        page_json_version_ids=[page.get("page_json_version_id") for page in pages],
    )
    variants: dict[int, str] = {}
    prompt_sha256s: dict[int, str] = {}
    for page, receipt in zip(pages, receipts, strict=True):
        physical_page = page["physical_page"]
        if (
            receipt["physical_page"] != physical_page
            or receipt["source_sha256"] != source_sha256
            or receipt["source_logical_name"] != source_logical_name
            or receipt["render_dpi"] != dpi
            or receipt["image_sha256"] != page_images[physical_page]
            or (
                page.get("prompt_sha256") is not None
                and page["prompt_sha256"] != receipt["prompt_sha256"]
            )
        ):
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "selected document extraction receipt differs from its manifest"
            )
        variants[physical_page] = receipt["prompt_variant"]
        prompt_sha256s[physical_page] = receipt["prompt_sha256"]
    contract = manifest.get("extraction_contract")
    if type(contract) is not dict:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "selected document extraction contract is absent"
        )
    if manifest.get("format_version") == "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V2":
        contract_prompt_sha = contract.get("prompt_sha256")
        if any(prompt_sha != contract_prompt_sha for prompt_sha in prompt_sha256s.values()):
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "selected legacy document prompt differs from extraction receipt"
            )
    else:
        expected_prompt_frontier = [
            {"physical_page": page, "prompt_sha256": prompt_sha256s[page]}
            for page in expected_pages
        ]
        if contract.get("page_prompt_sha256s") != expected_prompt_frontier:
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "selected document prompt frontier differs from extraction receipts"
            )
    return {
        "page_images": page_images,
        "prompt_sha256s": prompt_sha256s,
        "variants": variants,
    }


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
        if document.page_count < task["document_page_count"]:
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


def _stored_page_image_sha256s_v1(
    *,
    database: Path,
    task: dict[str, Any],
    source_root: Path,
    dpi: int,
) -> dict[int, str]:
    """Replay the already-ingested image frontier without rendering it again."""

    _source(task, source_root)
    return document_page_image_frontier_v1(
        database,
        source_sha256=task["source_sha256"],
        source_logical_name=task["relative_path"],
        expected_physical_pages=range(1, task["document_page_count"] + 1),
        render_dpi=dpi,
    )


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


def _allowed_gateway_service_tiers_v1() -> list[dict[str, str]]:
    return [
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
        {
            "gateway": "OPENROUTER",
            "requested_service_tier": OPENROUTER_STANDARD_FALLBACK_SERVICE_TIER,
        },
    ]


def _preferred_gateway_service_tiers_v1() -> list[dict[str, str]]:
    """Select the paid OpenRouter version before historical Google versions."""

    return [
        {
            "gateway": "OPENROUTER",
            "requested_service_tier": OPENROUTER_SERVICE_TIER,
        },
        {
            "gateway": "OPENROUTER",
            "requested_service_tier": OPENROUTER_STANDARD_FALLBACK_SERVICE_TIER,
        },
        {
            "gateway": "GOOGLE_GEMINI_BATCH_API",
            "requested_service_tier": GOOGLE_BATCH_SERVICE_TIER,
        },
        {
            "gateway": "GOOGLE_GEMINI_API",
            "requested_service_tier": GOOGLE_STANDARD_SERVICE_TIER,
        },
    ]


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


def _resume_acceleration_from_current_manifest_v1(
    *,
    ledger: Path,
    planned: dict[str, Any],
    tasks: list[dict[str, Any]],
    document_root: Path,
    current_images: dict[int, str],
) -> dict[str, Any] | None:
    """Seal a claimed document from an already authenticated current head.

    This is the crash/recovery boundary after a page-specific repair or after
    manifest publication but before ledger transition.  It never submits a
    provider request and accepts only the selected, content-addressed manifest
    whose complete image frontier is the freshly rendered whole-page frontier.
    """

    selected = load_current_document_manifest_selection_v1(
        document_root,
        document_plan_id=planned["document_plan_id"],
        source_sha256=planned["document"]["source_sha256"],
    )
    if selected is None:
        return None
    selection, manifest_path = selected
    manifest = _json_file(manifest_path)
    claimed_manifest_id = manifest.get("document_manifest_id")
    material = {key: value for key, value in manifest.items() if key != "document_manifest_id"}
    expected_manifest_id = "gfdmv1:manifest:" + canonical_json_sha256_v1(material)
    document = manifest.get("document")
    pages = manifest.get("pages")
    contract = manifest.get("extraction_contract")
    image_frontier = contract.get("page_image_sha256s") if type(contract) is dict else None
    expected_pages = list(range(1, planned["document"]["page_count"] + 1))
    expected_frontier = [
        {"image_sha256": current_images[page], "physical_page": page} for page in expected_pages
    ]
    if (
        claimed_manifest_id != expected_manifest_id
        or claimed_manifest_id != selection["document_manifest_id"]
        or manifest.get("format_version") != "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V4"
        or manifest.get("page_count") != planned["document"]["page_count"]
        or type(document) is not dict
        or document.get("source_logical_name") != planned["document"]["relative_path"]
        or document.get("source_sha256") != planned["document"]["source_sha256"]
        or document.get("source_size_bytes") != planned["document"]["source_size_bytes"]
        or type(pages) is not list
        or [page.get("physical_page") for page in pages if type(page) is dict] != expected_pages
        or any(page.get("status") == "UNRESOLVED_PAGE" for page in pages)
        or image_frontier != expected_frontier
        or selection["page_image_frontier_sha256"] != canonical_json_sha256_v1(expected_frontier)
    ):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "selected acceleration document manifest does not replay exactly"
        )
    claims = {task.get("provider_job_ref") for task in tasks if task["state"] == "RUNNING"}
    if len(claims) != 1 or any(
        task["state"] not in {"RUNNING", "SUCCEEDED"}
        or (task["state"] == "RUNNING" and not _is_openrouter_acceleration_task_v1(task))
        for task in tasks
    ):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "current manifest acceleration claim does not replay exactly"
        )
    receipt = {
        "claim_id": next(iter(claims)),
        "disposition": "SUCCEEDED",
        "document_manifest_id": claimed_manifest_id,
        "format_version": "GEMINI_JSON_FIRST_CURRENT_ACCELERATION_RESUME_V1",
        "selection_id": selection["selection_id"],
        "task_ids": [task["task_id"] for task in tasks],
    }
    completed = []
    for task in tasks:
        if task["state"] != "RUNNING":
            continue
        updated = transition_corpus_task_v1(
            ledger,
            task_id=task["task_id"],
            expected_state="RUNNING",
            next_state="SUCCEEDED",
            receipt=receipt,
        )
        completed.append(updated["task_id"])
    payload = canonical_json_bytes_v1(receipt)
    _write_or_verify(
        document_root
        / "openrouter-acceleration"
        / "run-receipts"
        / (sha256(payload).hexdigest() + ".json"),
        payload,
    )
    return {**receipt, "completed_task_ids": completed}


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
        return task["state"] in {"FAILED", "NEEDS_RETRY", "SUCCEEDED"} or (
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
    stored_prompt_sha256s = getattr(args, "stored_prompt_sha256s", None)
    if stored_prompt_sha256s is None:
        prompt_sha256s = {
            page: sha256(
                build_financial_page_json_prompt_v1(variant=variant).encode("utf-8")
            ).hexdigest()
            for page, variant in variants.items()
        }
    elif (
        type(stored_prompt_sha256s) is not dict
        or set(stored_prompt_sha256s) != set(expected_pages)
        or any(
            type(prompt_sha) is not str
            or len(prompt_sha) != 64
            or any(character not in "0123456789abcdef" for character in prompt_sha)
            for prompt_sha in stored_prompt_sha256s.values()
        )
    ):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "stored document prompt receipt frontier is invalid"
        )
    else:
        prompt_sha256s = dict(sorted(stored_prompt_sha256s.items()))
    stored_page_images = getattr(args, "stored_page_images", None)
    if stored_page_images is not None:
        _source(task, args.source_root)
        page_images = _summary_page_image_sha256s_v1(
            stored_page_images,
            allowed_pages=expected_pages,
        )
    elif getattr(args, "reuse_stored_page_images", False):
        page_images = _stored_page_image_sha256s_v1(
            database=args.database,
            task=task,
            source_root=args.source_root,
            dpi=plan["policy"]["dpi"],
        )
    else:
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
        allowed_gateway_service_tiers=_allowed_gateway_service_tiers_v1(),
        preferred_gateway_service_tiers=_preferred_gateway_service_tiers_v1(),
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
    repairable_task_ids = sorted(
        task["task_id"] for task in tasks if task["state"] in {"FAILED", "NEEDS_RETRY"}
    )
    repaired_tasks = []
    if repairable_task_ids:
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
                "repaired_task_ids": repairable_task_ids,
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


def _sha256_file_v1(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _artifact_content_ref_v1(*, artifact_root: Path, path: Path) -> dict[str, Any]:
    root = artifact_root.resolve()
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "corpus freeze artifact lies outside its root"
        ) from exc
    if path.is_symlink() or not path.is_file():
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "corpus freeze artifact is absent or not regular"
        )
    stat = path.stat()
    if stat.st_nlink != 1 or stat.st_mode & 0o777 != 0o444:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "corpus freeze artifact is not immutable and single-link"
        )
    return {
        "path": relative.as_posix(),
        "sha256": _sha256_file_v1(path),
        "size_bytes": stat.st_size,
    }


def _sqlite_snapshot_v1(
    *, source: Path, artifact_root: Path, logical_name: str
) -> tuple[Path, dict[str, Any]]:
    """Create one integrity-checked, immutable SQLite backup without copying WAL state."""

    if (
        source.is_symlink()
        or not source.is_file()
        or source.stat().st_nlink != 1
        or "/" in logical_name
        or not logical_name.endswith(".sqlite3")
    ):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "corpus freeze SQLite source or logical name is invalid"
        )
    output_root = artifact_root / "current-corpus-freeze-inputs"
    output_root.mkdir(parents=True, exist_ok=True)
    descriptor, stage_name = tempfile.mkstemp(
        prefix=logical_name + ".stage-", suffix=".sqlite3", dir=output_root
    )
    os.close(descriptor)
    stage = Path(stage_name)
    try:
        source_uri = f"file:{source.resolve()}?mode=ro"
        with sqlite3.connect(source_uri, uri=True) as source_connection:
            with sqlite3.connect(stage) as destination_connection:
                source_connection.backup(destination_connection)
                integrity = destination_connection.execute("PRAGMA integrity_check").fetchall()
                if integrity != [("ok",)]:
                    raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                        "corpus freeze SQLite snapshot failed integrity check"
                    )
        with stage.open("rb") as stream:
            os.fsync(stream.fileno())
        digest = _sha256_file_v1(stage)
        destination = output_root / f"{logical_name.removesuffix('.sqlite3')}-{digest}.sqlite3"
        if destination.exists():
            if (
                destination.is_symlink()
                or not destination.is_file()
                or destination.stat().st_nlink != 1
                or destination.stat().st_size != stage.stat().st_size
                or _sha256_file_v1(destination) != digest
            ):
                raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                    "immutable corpus freeze SQLite snapshot drifted"
                )
            stage.unlink()
        else:
            os.chmod(stage, 0o444)
            os.replace(stage, destination)
        os.chmod(destination, 0o444)
        return destination, _artifact_content_ref_v1(artifact_root=artifact_root, path=destination)
    finally:
        stage.unlink(missing_ok=True)


def _prompt_variants_from_manifest_v1(manifest: dict[str, Any]) -> dict[int, str]:
    allowed = ("balanced", "compact", "items", "scope", "simple")
    variant_by_sha = {
        sha256(
            build_financial_page_json_prompt_v1(variant=variant).encode("utf-8")
        ).hexdigest(): variant
        for variant in allowed
    }
    if len(variant_by_sha) != len(allowed):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "financial page prompt variants are not content-distinct"
        )
    contract = manifest.get("extraction_contract")
    prompt_frontier = contract.get("page_prompt_sha256s") if type(contract) is dict else None
    expected_pages = list(range(1, manifest.get("page_count", 0) + 1))
    if (
        manifest.get("format_version") == "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V2"
        and type(contract) is dict
        and prompt_frontier is None
    ):
        prompt_sha256 = contract.get("prompt_sha256")
        if prompt_sha256 not in variant_by_sha or not expected_pages:
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "selected legacy document prompt does not map to one known variant"
            )
        return {physical_page: variant_by_sha[prompt_sha256] for physical_page in expected_pages}
    if (
        type(prompt_frontier) is not list
        or [item.get("physical_page") for item in prompt_frontier if type(item) is dict]
        != expected_pages
        or any(
            type(item) is not dict
            or set(item) != {"physical_page", "prompt_sha256"}
            or item["prompt_sha256"] not in variant_by_sha
            for item in prompt_frontier
        )
    ):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "selected document prompt frontier does not map to one known variant"
        )
    return {
        item["physical_page"]: variant_by_sha[item["prompt_sha256"]] for item in prompt_frontier
    }


def _receipt_bound_legacy_document_manifest_v1(
    *, artifact_root: Path, task: dict[str, Any]
) -> dict[str, Any] | None:
    """Locate the exact completed manifest named by a pre-selection task receipt."""

    raw_receipt = task.get("last_receipt_json")
    if raw_receipt is None:
        return None
    if type(raw_receipt) is bytes:
        receipt_bytes = raw_receipt
    elif type(raw_receipt) is str:
        receipt_bytes = raw_receipt.encode("utf-8")
    else:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "completed corpus task receipt has an invalid type"
        )
    try:
        receipt = json.loads(receipt_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "completed corpus task receipt is not JSON"
        ) from exc
    if type(receipt) is not dict:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "completed corpus task receipt is not one object"
        )
    result = receipt.get("result")
    identifiers = {
        value
        for value in (
            receipt.get("document_manifest_id"),
            result.get("document_manifest_id") if type(result) is dict else None,
            result.get("manifest_id") if type(result) is dict else None,
        )
        if value is not None
    }
    if not identifiers:
        return None
    if len(identifiers) != 1 or any(
        type(value) is not str
        or not value.startswith("gfdmv1:manifest:")
        or len(value) != len("gfdmv1:manifest:") + 64
        or any(
            character not in "0123456789abcdef"
            for character in value.removeprefix("gfdmv1:manifest:")
        )
        for value in identifiers
    ):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "completed corpus task manifest identity is invalid or contradictory"
        )
    expected_id = next(iter(identifiers))
    task_root = _task_root(task, artifact_root)
    matches: list[tuple[bytes, dict[str, Any]]] = []
    if task_root.exists():
        for path in sorted(task_root.glob("**/*document-manifest*.json")):
            if path.is_symlink() or not path.is_file():
                raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                    "completed corpus task manifest candidate is not a regular file"
                )
            candidate = _json_file(path)
            if candidate.get("document_manifest_id") == expected_id:
                matches.append((canonical_json_bytes_v1(candidate), candidate))
    if not matches:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "completed corpus task receipt manifest artifact is absent"
        )
    distinct = {payload for payload, _candidate in matches}
    if len(distinct) != 1:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "completed corpus task receipt resolves to conflicting manifests"
        )
    return matches[0][1]


def _replay_selected_document_for_corpus_v1(
    *,
    args: argparse.Namespace,
    plan: dict[str, Any],
    planned: dict[str, Any],
    task: dict[str, Any],
) -> dict[str, Any]:
    document_root = args.artifact_root / "documents" / planned["document_plan_id"].split(":", 1)[1]
    selected = load_current_document_manifest_selection_v1(
        document_root,
        document_plan_id=planned["document_plan_id"],
        source_sha256=planned["document"]["source_sha256"],
    )
    if selected is None:
        page_prompt_variant = []
        stored_page_images = None
        stored_prompt_sha256s = None
        legacy_manifest_path = document_root / "current-document-manifest.json"
        legacy_manifest = (
            _json_file(legacy_manifest_path)
            if legacy_manifest_path.exists()
            else _receipt_bound_legacy_document_manifest_v1(
                artifact_root=args.artifact_root, task=task
            )
        )
        if legacy_manifest is not None:
            legacy_material = {
                key: value
                for key, value in legacy_manifest.items()
                if key != "document_manifest_id"
            }
            legacy_document = legacy_manifest.get("document")
            legacy_pages = legacy_manifest.get("pages")
            expected_pages = list(range(1, planned["document"]["page_count"] + 1))
            if (
                legacy_manifest.get("format_version")
                not in {
                    "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V2",
                    "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V3",
                    "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V4",
                }
                or legacy_manifest.get("document_manifest_id")
                != "gfdmv1:manifest:" + canonical_json_sha256_v1(legacy_material)
                or legacy_manifest.get("page_count") != len(expected_pages)
                or type(legacy_document) is not dict
                or legacy_document.get("source_logical_name")
                != planned["document"]["relative_path"]
                or legacy_document.get("source_sha256") != planned["document"]["source_sha256"]
                or legacy_document.get("source_size_bytes")
                != planned["document"]["source_size_bytes"]
                or type(legacy_pages) is not list
                or [page.get("physical_page") for page in legacy_pages if type(page) is dict]
                != expected_pages
                or any(page.get("status") == "UNRESOLVED_PAGE" for page in legacy_pages)
            ):
                raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                    "legacy current document manifest identity or page frontier drifted"
                )
            legacy_frontier = _manifest_extraction_frontier_v1(
                database=args.database,
                manifest=legacy_manifest,
                expected_pages=expected_pages,
                dpi=plan["policy"]["dpi"],
                source_sha256=planned["document"]["source_sha256"],
                source_logical_name=planned["document"]["relative_path"],
            )
            variants = legacy_frontier["variants"]
            stored_prompt_sha256s = legacy_frontier["prompt_sha256s"]
            stored_page_images = [
                {
                    "image_sha256": legacy_frontier["page_images"][page],
                    "physical_page": page,
                }
                for page in expected_pages
            ]
        else:
            expected_pages = list(range(1, planned["document"]["page_count"] + 1))
            stored_frontier = document_page_extraction_frontier_v1(
                args.database,
                source_sha256=planned["document"]["source_sha256"],
                source_logical_name=planned["document"]["relative_path"],
                expected_physical_pages=expected_pages,
                render_dpi=plan["policy"]["dpi"],
            )
            variants = {page: stored_frontier[page]["prompt_variant"] for page in expected_pages}
            stored_prompt_sha256s = {
                page: stored_frontier[page]["prompt_sha256"] for page in expected_pages
            }
            stored_page_images = [
                {
                    "image_sha256": stored_frontier[page]["image_sha256"],
                    "physical_page": page,
                }
                for page in expected_pages
            ]
        default_variant = corpus_ledger_summary_v1(args.ledger)["prompt_variant"]
        page_prompt_variant = [
            f"{page}={variant}" for page, variant in variants.items() if variant != default_variant
        ]
        built = build_current_document_manifest(
            argparse.Namespace(
                artifact_root=args.artifact_root,
                database=args.database,
                ledger=args.ledger,
                page_prompt_variant=page_prompt_variant,
                plan=args.plan,
                reuse_stored_page_images=True,
                source_root=args.source_root,
                stored_page_images=stored_page_images,
                stored_prompt_sha256s=stored_prompt_sha256s,
                task_id=planned["tasks"][0]["task_id"],
            )
        )
        if built.get("disposition") != "SUCCEEDED":
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "corpus freeze could not derive a complete default-prompt document manifest"
            )
        selected = load_current_document_manifest_selection_v1(
            document_root,
            document_plan_id=planned["document_plan_id"],
            source_sha256=planned["document"]["source_sha256"],
        )
    if selected is None:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "corpus freeze current document selection is absent"
        )
    selection, manifest_path = selected
    manifest = _json_file(manifest_path)
    material = {key: value for key, value in manifest.items() if key != "document_manifest_id"}
    expected_manifest_id = "gfdmv1:manifest:" + canonical_json_sha256_v1(material)
    expected_pages = list(range(1, planned["document"]["page_count"] + 1))
    document = manifest.get("document")
    pages = manifest.get("pages")
    if (
        manifest.get("format_version") != "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V4"
        or manifest.get("document_manifest_id") != expected_manifest_id
        or selection["document_manifest_id"] != expected_manifest_id
        or manifest.get("page_count") != len(expected_pages)
        or type(document) is not dict
        or document.get("source_logical_name") != planned["document"]["relative_path"]
        or document.get("source_sha256") != planned["document"]["source_sha256"]
        or document.get("source_size_bytes") != planned["document"]["source_size_bytes"]
        or type(pages) is not list
        or [page.get("physical_page") for page in pages if type(page) is dict] != expected_pages
        or any(page.get("status") == "UNRESOLVED_PAGE" for page in pages)
    ):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "selected corpus document manifest identity or page frontier drifted"
        )
    _source(task, args.source_root)
    selected_frontier = _manifest_extraction_frontier_v1(
        database=args.database,
        manifest=manifest,
        expected_pages=expected_pages,
        dpi=plan["policy"]["dpi"],
        source_sha256=planned["document"]["source_sha256"],
        source_logical_name=planned["document"]["relative_path"],
    )
    page_images = selected_frontier["page_images"]
    prompt_sha256s = selected_frontier["prompt_sha256s"]
    variants = selected_frontier["variants"]
    rebuilt = build_financial_document_manifest_v1(
        args.database,
        source_sha256=task["source_sha256"],
        source_logical_name=task["relative_path"],
        expected_physical_pages=expected_pages,
        page_image_sha256s=page_images,
        prompt_sha256=prompt_sha256s,
        response_schema_sha256=canonical_json_sha256_v1(financial_page_json_response_schema_v1()),
        requested_model=GOOGLE_MODEL,
        allowed_gateway_service_tiers=_allowed_gateway_service_tiers_v1(),
        preferred_gateway_service_tiers=_preferred_gateway_service_tiers_v1(),
    )
    image_frontier = [
        {"image_sha256": page_images[page], "physical_page": page} for page in expected_pages
    ]
    prompt_sha_frontier = [
        {"physical_page": page, "prompt_sha256": prompt_sha256s[page]} for page in expected_pages
    ]
    prompt_frontier = [
        {"physical_page": page, "prompt_variant": variants[page]} for page in expected_pages
    ]
    rebuilt_material = {
        key: value for key, value in rebuilt.items() if key != "document_manifest_id"
    }
    rebuilt_document = rebuilt.get("document")
    rebuilt_contract = rebuilt.get("extraction_contract")
    rebuilt_pages = rebuilt.get("pages")
    if (
        rebuilt.get("document_manifest_id")
        != "gfdmv1:manifest:" + canonical_json_sha256_v1(rebuilt_material)
        or rebuilt.get("format_version") != "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V4"
        or rebuilt.get("page_count") != len(expected_pages)
        or rebuilt_document != document
        or type(rebuilt_contract) is not dict
        or rebuilt_contract.get("page_image_sha256s") != image_frontier
        or rebuilt_contract.get("page_prompt_sha256s") != prompt_sha_frontier
        or rebuilt_contract.get("preferred_gateway_service_tiers")
        != _preferred_gateway_service_tiers_v1()
        or type(rebuilt_pages) is not list
        or [page.get("physical_page") for page in rebuilt_pages if type(page) is dict]
        != expected_pages
        or any(page.get("status") == "UNRESOLVED_PAGE" for page in rebuilt_pages)
    ):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "rebuilt corpus document manifest does not replay exactly"
        )
    if rebuilt != manifest:
        manifest_path, selection = _write_current_document_manifest_selection_v1(
            artifact_root=args.artifact_root,
            planned=planned,
            task=task,
            manifest=rebuilt,
            page_images=page_images,
            variants=variants,
        )
        manifest = rebuilt
        pages = manifest["pages"]
    if selection["page_image_frontier_sha256"] != canonical_json_sha256_v1(
        image_frontier
    ) or selection["page_prompt_frontier_sha256"] != canonical_json_sha256_v1(prompt_frontier):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "selected corpus document does not replay from source, prompts, and database"
        )
    provider_counts: Counter[tuple[str, str, str]] = Counter()
    for page in pages:
        route = page.get("provider_route")
        if (
            type(route) is not dict
            or set(route) != {"gateway", "requested_service_tier", "selected_provider"}
            or any(type(route[field]) is not str or not route[field] for field in route)
            or page.get("selected_service_tier") != route["requested_service_tier"]
        ):
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "selected corpus document provider route is invalid"
            )
        provider_counts[
            (route["gateway"], route["selected_provider"], page["selected_service_tier"])
        ] += 1
    selection_path = (
        document_root
        / "current-document-manifest-selections"
        / (selection["selection_id"].split(":", 2)[2] + ".json")
    )
    status_counts = {
        status: manifest["status_counts"].get(status, 0)
        for status in (
            "FINANCIAL_NOTE_CONTENT",
            "MIXED_FINANCIAL_CONTENT",
            "NO_RELEVANT_FINANCIAL_CONTENT",
            "PRIMARY_FINANCIAL_STATEMENT",
        )
    }
    return {
        "document_manifest_id": manifest["document_manifest_id"],
        "document_manifest_ref": _artifact_content_ref_v1(
            artifact_root=args.artifact_root, path=manifest_path
        ),
        "document_plan_id": planned["document_plan_id"],
        "page_count": len(expected_pages),
        "page_json_frontier_sha256": canonical_json_sha256_v1(pages),
        "page_status_counts": status_counts,
        "provider_counts": [
            {
                "count": provider_counts[key],
                "gateway": key[0],
                "selected_provider": key[1],
                "selected_service_tier": key[2],
            }
            for key in sorted(provider_counts)
        ],
        "relative_path": planned["document"]["relative_path"],
        "selection_id": selection["selection_id"],
        "selection_ref": _artifact_content_ref_v1(
            artifact_root=args.artifact_root, path=selection_path
        ),
        "source_sha256": planned["document"]["source_sha256"],
        "source_size_bytes": planned["document"]["source_size_bytes"],
    }


def build_current_corpus_manifest(args: argparse.Namespace) -> dict[str, Any]:
    """Freeze all selected pages after the complete 140-document ledger closes."""

    plan = _plan(args.plan)
    ledger_summary = corpus_ledger_summary_v1(args.ledger)
    tasks = list_corpus_tasks_v1(args.ledger)
    planned_task_ids = {
        task["task_id"] for document in plan["documents"] for task in document["tasks"]
    }
    if (
        ledger_summary["corpus_plan_id"] != plan["corpus_plan_id"]
        or ledger_summary["documents"] != len(plan["documents"])
        or ledger_summary["total_pages"] != plan["summary"]["page_count"]
        or {task["task_id"] for task in tasks} != planned_task_ids
        or any(task["state"] != "SUCCEEDED" for task in tasks)
    ):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "corpus freeze requires the exact fully succeeded ledger frontier"
        )
    by_task_id = {task["task_id"]: task for task in tasks}
    documents = []
    for source_ordinal, planned in enumerate(plan["documents"], start=1):
        record = _replay_selected_document_for_corpus_v1(
            args=args,
            plan=plan,
            planned=planned,
            task=by_task_id[planned["tasks"][0]["task_id"]],
        )
        documents.append({**record, "source_ordinal": source_ordinal})

    plan_payload = canonical_json_bytes_v1(plan) + b"\n"
    plan_digest = sha256(plan_payload).hexdigest()
    plan_output = (
        args.artifact_root / "current-corpus-freeze-inputs" / f"corpus-plan-{plan_digest}.json"
    )
    _write_or_verify(plan_output, plan_payload)
    database_snapshot, database_ref = _sqlite_snapshot_v1(
        source=args.database,
        artifact_root=args.artifact_root,
        logical_name="store.sqlite3",
    )
    ledger_snapshot, ledger_ref = _sqlite_snapshot_v1(
        source=args.ledger,
        artifact_root=args.artifact_root,
        logical_name="ledger.sqlite3",
    )
    usage = usage_summary_v1(database_snapshot)
    frozen_ledger_summary = corpus_ledger_summary_v1(ledger_snapshot)
    frozen_tasks = list_corpus_tasks_v1(ledger_snapshot)
    if (
        frozen_ledger_summary != ledger_summary
        or frozen_tasks != tasks
        or any(task["state"] != "SUCCEEDED" for task in frozen_tasks)
    ):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "corpus freeze ledger snapshot does not replay exactly"
        )
    index = build_current_corpus_manifest_index_v1(
        corpus_plan_id=plan["corpus_plan_id"],
        corpus_run_id=ledger_summary["corpus_run_id"],
        corpus_plan_ref=_artifact_content_ref_v1(
            artifact_root=args.artifact_root, path=plan_output
        ),
        database_ref=database_ref,
        ledger_ref=ledger_ref,
        documents=documents,
        store_usage_summary=usage,
    )
    digest = index["corpus_manifest_index_id"].split(":", 2)[2]
    output = args.artifact_root / "current-corpus-manifest-indexes" / f"{digest}.json"
    _write_or_verify(output, canonical_json_bytes_v1(index) + b"\n")
    return {
        "corpus_manifest_index_id": index["corpus_manifest_index_id"],
        "database_ref": database_ref,
        "disposition": "SUCCEEDED",
        "document_count": index["summary"]["document_count"],
        "ledger_ref": ledger_ref,
        "output": str(output),
        "page_count": index["summary"]["page_count"],
        "page_status_counts": index["summary"]["page_status_counts"],
        "provider_counts": index["summary"]["provider_counts"],
        "store_usage_summary": usage,
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
    current_document_root = (
        args.artifact_root / "documents" / planned["document_plan_id"].split(":", 1)[1]
    )
    resumed = _resume_acceleration_from_current_manifest_v1(
        ledger=args.ledger,
        planned=planned,
        tasks=tasks,
        document_root=current_document_root,
        current_images=current_images,
    )
    if resumed is not None:
        return {**resumed, "ledger": corpus_ledger_summary_v1(args.ledger)}
    source = _source(task, args.source_root)
    document_root = current_document_root / "openrouter-acceleration"
    receipt_root = document_root / "run-receipts"
    attempt_number = len(list(receipt_root.glob("*.json"))) + 1
    google_standard_mode = (
        "disabled" if getattr(args, "openrouter_only", False) else "on-provider-error"
    )
    attempted_contract = (
        document_root / f"attempt-{attempt_number:02d}" / "base" / "document-contract.json"
    )
    if attempted_contract.is_file():
        attempted_mode = _json_file(attempted_contract).get("google_standard_mode", "disabled")
        if attempted_mode != google_standard_mode:
            existing_attempts = [
                int(path.name.removeprefix("attempt-"))
                for path in document_root.glob("attempt-[0-9][0-9]")
                if path.is_dir() and path.name.removeprefix("attempt-").isdigit()
            ]
            attempt_number = max(existing_attempts, default=attempt_number) + 1
    if attempt_number > args.max_acceleration_attempts:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter acceleration attempt bound is exhausted"
        )
    attempt_root = document_root / f"attempt-{attempt_number:02d}"
    default_variant = corpus_ledger_summary_v1(args.ledger)["prompt_variant"]
    prior_provider_failures = _prior_acceleration_provider_failures_v1(receipt_root)

    def run_frontier(
        *,
        pages: list[int] | None,
        prompt_variant: str,
        retry_artifact: bool = False,
    ):
        artifact_dir = attempt_root / "base"
        if retry_artifact:
            if pages is None:
                raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                    "adaptive retry artifact lacks its page frontier"
                )
            artifact_dir = _adaptive_retry_artifact_dir_v1(
                task_root=attempt_root,
                prompt_variant=prompt_variant,
                pages=pages,
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
            "--openrouter-route-policy",
            "flex-then-standard",
            "--google-key-file",
            str(args.google_key_file),
            "--google-key-slot",
            str(args.google_key_slot),
            "--google-standard-mode",
            google_standard_mode,
            "--timeout-seconds",
            str(args.provider_timeout_seconds),
        ]
        if pages is not None:
            for page in pages:
                command.extend(("--physical-page", str(page)))
        return _command(command, expected={0, 2})

    variants = {page: default_variant for page in expected_pages}
    initial_pages = expected_pages
    if any(task.get("attempt_count", 1) > 1 for task in tasks):
        initial_pages = _missing_current_default_pages_v1(
            database=args.database,
            task=task,
            expected_pages=expected_pages,
            current_images=current_images,
            default_variant=default_variant,
        )
    return_code = 0
    initial: dict[str, Any] | None = None
    provider_results = []
    if initial_pages:
        return_code, initial = run_frontier(
            pages=(
                None
                if initial_pages == expected_pages and "page_selection" not in planned["document"]
                else initial_pages
            ),
            prompt_variant=default_variant,
        )
        if _summary_page_image_sha256s_v1(
            initial.get("page_image_sha256s"), allowed_pages=initial_pages
        ) != {page: current_images[page] for page in initial_pages}:
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "OpenRouter acceleration base image frontier drifted"
            )
        provider_results.append(
            {
                "physical_pages": initial_pages,
                "prompt_variant": default_variant,
                "result": initial,
            }
        )
    protected_pages: list[int] = []
    if return_code != 0:
        assert initial is not None
        frontiers = _retry_prompt_frontiers_from_receipt_v1(
            initial,
            first_physical_page=1,
            last_physical_page=task["document_page_count"],
        )
        repeated_default_provider_pages = set(frontiers["default"]) & prior_provider_failures.get(
            default_variant, set()
        )
        protected_pages = frontiers["items"]
        failed_retry_pages: set[int] = set()
        balanced_pages: set[int] = set()
        prompt_pages: dict[str, list[int]] = {}
        for variant, pages in (
            (
                default_variant,
                sorted(set(frontiers["default"]) - repeated_default_provider_pages),
            ),
            ("scope", frontiers["scope"]),
            ("items", sorted(set(frontiers["items"]) | repeated_default_provider_pages)),
        ):
            prompt_pages.setdefault(variant, []).extend(pages)
        for prompt_variant, pages in (
            (variant, sorted(set(pages))) for variant, pages in prompt_pages.items()
        ):
            if not pages:
                continue
            code, result = run_frontier(
                pages=pages,
                prompt_variant=prompt_variant,
                retry_artifact=True,
            )
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
            failed_retry_pages.difference_update(pages)
            if code != 0:
                retry_frontiers = _retry_prompt_frontiers_from_receipt_v1(
                    result,
                    first_physical_page=min(pages),
                    last_physical_page=max(pages),
                )
                failed_retry_pages.update(result["failed_pages"])
                if prompt_variant == default_variant:
                    prompt_pages["items"].extend(
                        retry_frontiers["default"] + retry_frontiers["items"]
                    )
                if prompt_variant == "items" and not retry_frontiers["scope"]:
                    balanced_pages.update(retry_frontiers["default"])
                    balanced_pages.update(retry_frontiers["items"])
        if balanced_pages:
            pages = sorted(balanced_pages)
            code, result = run_frontier(
                pages=pages,
                prompt_variant="balanced",
                retry_artifact=True,
            )
            if _summary_page_image_sha256s_v1(
                result.get("page_image_sha256s"), allowed_pages=pages
            ) != {page: current_images[page] for page in pages}:
                raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                    "OpenRouter acceleration balanced-retry image frontier drifted"
                )
            provider_results.append(
                {
                    "physical_pages": pages,
                    "prompt_variant": "balanced",
                    "result": result,
                }
            )
            variants.update({page: "balanced" for page in pages})
            failed_retry_pages.difference_update(pages)
            if code != 0:
                failed_retry_pages.update(result["failed_pages"])
        return_code = 2 if failed_retry_pages else 0

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
        allowed_gateway_service_tiers=_allowed_gateway_service_tiers_v1(),
        preferred_gateway_service_tiers=_preferred_gateway_service_tiers_v1(),
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
    """Return retryable or crash-resumable Google documents, smallest first."""

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
        retryable_states = {"PENDING", "NEEDS_RETRY"}
        retryable = (
            document_rows
            and any(row["state"] in retryable_states for row in document_rows)
            and all(row["state"] in retryable_states | {"SUCCEEDED"} for row in document_rows)
        )
        resumable = (
            document_rows
            and any(row["state"] == "RUNNING" for row in document_rows)
            and all(row["state"] in {"RUNNING", "SUCCEEDED"} for row in document_rows)
        )
        if retryable or resumable:
            candidates.append(
                {
                    "document_plan_id": document["document_plan_id"],
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
    retry_count = 0
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
                if "requires one retryable document frontier" not in str(exc):
                    raise
                race_count += 1
                continue
            except RunGeminiJsonFirstCorpusSupervisorV1Error as exc:
                if str(exc) != "OpenRouter acceleration attempt bound is exhausted":
                    raise
                return {
                    "completed_documents": completed
                    + [
                        {
                            "disposition": "NEEDS_RETRY",
                            "document_manifest_id": None,
                            "document_page_count": candidate["document_page_count"],
                            "relative_path": candidate["relative_path"],
                            "selection_id": None,
                            "task_id": candidate["task_id"],
                        }
                    ],
                    "disposition": "NEEDS_RETRY",
                    "ledger": corpus_ledger_summary_v1(args.ledger),
                    "race_count": race_count,
                    "retry_count": retry_count,
                }
            claimed = True
            if result["disposition"] == "NEEDS_RETRY":
                retry_count += 1
                break
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
        "retry_count": retry_count,
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
    openrouter_only: bool = False,
) -> dict[str, Any]:
    language_prefix_pages = None
    if "documents" in plan:
        selected_plan = _task_index(plan).get(task["task_id"])
        if selected_plan is None:
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "OpenRouter task is absent from the corpus plan"
            )
        planned_document = selected_plan["planned_document"]["document"]
        if planned_document["page_count"] != task["document_page_count"]:
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "OpenRouter task page count differs from the corpus plan"
            )
        if "page_selection" in planned_document:
            language_prefix_pages = list(range(1, task["document_page_count"] + 1))
    retry_frontiers = _retry_prompt_frontiers_v1(task)
    retry_pages = (
        None
        if retry_frontiers is None
        else sorted(page for pages in retry_frontiers.values() for page in pages)
    )
    semantic_retry_pages: list[int] = []
    if retry_frontiers is not None:
        try:
            prior_retry_receipt = json.loads(task["last_receipt_json"])
        except (TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "OpenRouter semantic retry receipt is invalid"
            ) from exc
        semantic_retry_pages = prior_retry_receipt.get("semantic_failed_pages", [])
        if (
            type(semantic_retry_pages) is not list
            or semantic_retry_pages != sorted(set(semantic_retry_pages))
            or not set(semantic_retry_pages).issubset(retry_frontiers["items"])
        ):
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "OpenRouter semantic retry frontier is invalid"
            )
    protected_retry_pages = _protected_retry_pages_v1(task)
    historical_prompt_context = (
        ({}, [])
        if retry_frontiers is None or task["attempt_count"] <= 1
        else _successful_historical_prompt_context_v1(ledger=ledger, task=task)
    )
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

    def run_frontier(
        *,
        pages: list[int] | None,
        prompt_variant: str,
        retry_artifact: bool = False,
        offline_replay_only: bool = False,
    ) -> tuple[int, dict[str, Any]]:
        selected_artifact_dir = _task_root(task, artifact_root)
        if retry_artifact:
            if pages is None:
                raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                    "adaptive retry artifact lacks its page frontier"
                )
            selected_artifact_dir = _adaptive_retry_artifact_dir_v1(
                task_root=selected_artifact_dir,
                prompt_variant=prompt_variant,
                pages=pages,
            )
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
            "--openrouter-route-policy",
            "flex-then-standard",
            "--google-key-file",
            str(google_key_file),
            "--google-key-slot",
            str(google_key_slot),
            "--google-standard-mode",
            "disabled" if openrouter_only else "on-provider-error",
            "--timeout-seconds",
            str(provider_timeout_seconds),
        ]
        if pages is not None:
            for page in pages:
                command.extend(("--physical-page", str(page)))
        if openrouter_workers == 1:
            command.append("--stop-provider-frontier-on-transient-error")
        if offline_replay_only:
            command.append("--offline-replay-only")
        return _command(command, expected={0, 2})

    if retry_frontiers is None:
        try:
            return_code, receipt = run_frontier(
                pages=language_prefix_pages,
                prompt_variant=default_prompt_variant,
            )
        except _ProviderSubprocessError as error:
            return _record_openrouter_subprocess_failure_v1(
                error=error,
                task=task,
                ledger=ledger,
                max_attempts=max_attempts,
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
        historical_variants, historical_protected_pages = historical_prompt_context
        retry_results = []
        offline_replay_results = []
        retry_variants: dict[int, str] = {}
        provider_circuit_open = False
        provider_circuit_deferred_pages: list[int] = []
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
        offline_accepted: list[int] = []
        remaining_semantic_pages = list(semantic_retry_pages)
        for offline_variant in dict.fromkeys((default_prompt_variant, "items")):
            offline_item = _offline_semantic_replay_result_v1(
                args=argparse.Namespace(
                    database=database,
                    openrouter_workers=openrouter_workers,
                    repair_attempt=task["attempt_count"],
                ),
                attempt_root=(
                    _task_root(task, artifact_root)
                    / "adaptive-retry"
                    / f"offline-attempt-{task['attempt_count']:02d}"
                ),
                current_images=current_page_images,
                prompt_variant=offline_variant,
                semantic_pages=remaining_semantic_pages,
                source=source,
                task=task,
                task_root=_task_root(task, artifact_root),
                dpi=plan["policy"]["dpi"],
            )
            if offline_item is None:
                continue
            offline_replay_results.append(offline_item)
            accepted_for_variant = offline_item["accepted_pages"]
            offline_accepted.extend(accepted_for_variant)
            offline_result = offline_item["result"]
            for field in ("cached_pages", "ingested_pages"):
                aggregate[field].extend(
                    page for page in offline_result.get(field, []) if page in accepted_for_variant
                )
            retry_variants.update({page: offline_variant for page in accepted_for_variant})
            remaining_semantic_pages = sorted(
                set(remaining_semantic_pages) - set(accepted_for_variant)
            )
            if not remaining_semantic_pages:
                break
        prompt_pages: dict[str, list[int]] = {}
        for prompt_variant, pages in (
            (default_prompt_variant, retry_frontiers["default"]),
            ("scope", retry_frontiers["scope"]),
            ("items", retry_frontiers["items"]),
        ):
            prompt_pages.setdefault(prompt_variant, []).extend(
                page for page in pages if page not in offline_accepted
            )
        prompt_frontiers = tuple(
            (variant, sorted(set(pages))) for variant, pages in prompt_pages.items()
        )
        for prompt_variant, pages in prompt_frontiers:
            if not pages:
                continue
            offline_due_to_circuit = provider_circuit_open
            try:
                code, result = run_frontier(
                    pages=pages,
                    prompt_variant=prompt_variant,
                    retry_artifact=True,
                    offline_replay_only=offline_due_to_circuit,
                )
            except _ProviderSubprocessError as error:
                return _record_openrouter_subprocess_failure_v1(
                    error=error,
                    task=task,
                    ledger=ledger,
                    max_attempts=max_attempts,
                )
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
            if offline_due_to_circuit:
                provider_circuit_deferred_pages.extend(pages)
            circuit_trigger_page = result.get("provider_circuit_breaker_trigger_page")
            if circuit_trigger_page is not None and (
                type(circuit_trigger_page) is not int or circuit_trigger_page not in pages
            ):
                raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                    "adaptive retry provider circuit trigger page is invalid"
                )
            if type(circuit_trigger_page) is int:
                provider_circuit_open = True
            if code != 0:
                return_code = 2
        complete_retry_variants = {**historical_variants, **retry_variants}
        complete_protected_pages = sorted(
            set(historical_protected_pages) | set(protected_retry_pages)
        )
        receipt_prompt_frontiers = [
            {
                "physical_pages": sorted(
                    page for page, page_variant in retry_variants.items() if page_variant == variant
                ),
                "prompt_variant": variant,
            }
            for variant in (default_prompt_variant, "scope", "items")
            if any(page_variant == variant for page_variant in retry_variants.values())
        ]
        receipt = {
            **{field: sorted(values) for field, values in aggregate.items()},
            "adaptive_retry_results": retry_results,
            "offline_replay_results": offline_replay_results,
            "alternate_prompt_pages": retry_pages,
            "alternate_prompt_variants": receipt_prompt_frontiers,
            "provider_circuit_deferred_pages": sorted(provider_circuit_deferred_pages),
            "protected_retry_pages": complete_protected_pages,
        }
        if return_code == 0:
            manifest = _page_variant_manifest_v1(
                task=task,
                ledger=ledger,
                database=database,
                artifact_root=artifact_root,
                page_image_sha256s=current_page_images,
                page_prompt_variants=complete_retry_variants,
                write=False,
            )
            dropped_semantic_pages = _semantic_retry_no_relevant_pages_v1(
                manifest, protected_pages=complete_protected_pages
            )
            if dropped_semantic_pages:
                receipt["semantic_item_no_relevant_pages"] = dropped_semantic_pages
                return_code = 2
            else:
                manifest_name = (
                    "mixed-prompt-document-manifest.json"
                    if set(complete_retry_variants.values()) == {"items"}
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


def _openrouter_task_result_has_circuit_trip_v1(task: dict[str, Any]) -> bool:
    """Read the typed child receipt and detect one provider circuit trip."""

    raw = task.get("last_receipt_json") if type(task) is dict else None
    if type(raw) is not bytes:
        return False
    try:
        receipt = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter circuit receipt is invalid"
        ) from exc

    def visit(value: Any) -> bool:
        if type(value) is dict:
            if "provider_circuit_breaker_trigger_page" in value:
                page = value["provider_circuit_breaker_trigger_page"]
                if page is not None and (type(page) is not int or page <= 0):
                    raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                        "OpenRouter circuit trigger page is invalid"
                    )
                if type(page) is int:
                    return True
            return any(visit(item) for item in value.values())
        if type(value) is list:
            return any(visit(item) for item in value)
        return False

    return visit(receipt)


def _openrouter_schedule_key_v1(task: dict[str, Any]) -> tuple[int, str]:
    """Prefer crash recovery, then paid semantic replay, before new provider work."""

    state = task.get("state")
    if state == "RUNNING":
        priority = 0
    elif state == "NEEDS_RETRY":
        frontiers = _retry_prompt_frontiers_v1(task)
        priority = 1 if frontiers is not None and frontiers["items"] else 2
    elif state == "PENDING":
        priority = 3
    else:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter scheduler received a non-runnable task"
        )
    task_id = task.get("task_id")
    if type(task_id) is not str:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter scheduler task identity is invalid"
        )
    return priority, task_id


def _openrouter_circuit_cooldown_v1(*, base_seconds: float, consecutive_trips: int) -> float:
    """Exponentially cool one persistently throttled Flex route, capped at one hour."""

    if (
        type(base_seconds) not in {int, float}
        or not 0 <= base_seconds <= 3_600
        or type(consecutive_trips) is not int
        or consecutive_trips <= 0
    ):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter circuit cooldown inputs are invalid"
        )
    return min(3_600.0, float(base_seconds) * (2 ** min(consecutive_trips - 1, 20)))


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
    openrouter_circuit_cooldown_seconds = getattr(
        args, "openrouter_circuit_cooldown_seconds", 300.0
    )
    if (
        type(openrouter_circuit_cooldown_seconds) not in {int, float}
        or not 0 <= openrouter_circuit_cooldown_seconds <= 3_600
    ):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter circuit cooldown lies outside 0..3600 seconds"
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
    openrouter_not_before = 0.0
    openrouter_consecutive_circuit_trips = 0
    google_submit_executor = ThreadPoolExecutor(
        max_workers=GOOGLE_SUBMIT_WORKERS,
        thread_name_prefix="google-batch-submit",
    )
    google_submit_futures: dict[Future[dict[str, Any]], str] = {}
    google_submit_not_before: dict[str, float] = {}
    google_submit_global_not_before = 0.0
    next_google_poll_at = 0.0
    while True:
        if openrouter_future is not None and openrouter_future.done():
            try:
                openrouter_result = openrouter_future.result()
            except Exception:
                openrouter_executor.shutdown(wait=True, cancel_futures=True)
                google_submit_executor.shutdown(wait=True, cancel_futures=True)
                raise
            if _openrouter_task_result_has_circuit_trip_v1(openrouter_result):
                openrouter_consecutive_circuit_trips += 1
                openrouter_not_before = max(
                    openrouter_not_before,
                    time.monotonic()
                    + _openrouter_circuit_cooldown_v1(
                        base_seconds=openrouter_circuit_cooldown_seconds,
                        consecutive_trips=openrouter_consecutive_circuit_trips,
                    ),
                )
            else:
                openrouter_consecutive_circuit_trips = 0
            openrouter_future = None
        for future in [future for future in google_submit_futures if future.done()]:
            try:
                submission_result = future.result()
            except Exception:
                openrouter_executor.shutdown(wait=True, cancel_futures=True)
                google_submit_executor.shutdown(wait=True, cancel_futures=True)
                raise
            task_id = google_submit_futures[future]
            if submission_result.get("disposition") == RETRYABLE_GOOGLE_UPLOAD_DISPOSITION:
                retry_at = time.monotonic() + GOOGLE_SUBMIT_RETRY_DELAY_SECONDS
                google_submit_not_before[task_id] = retry_at
                google_submit_global_not_before = max(google_submit_global_not_before, retry_at)
            else:
                google_submit_not_before.pop(task_id, None)
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
        accelerated_google = [
            task for task in unfinished if _is_openrouter_acceleration_task_v1(task)
        ]
        openrouter = sorted(
            (
                task
                for task in unfinished
                if task["route"] == OPENROUTER_ROUTE
                and task["state"] in {"PENDING", "RUNNING", "NEEDS_RETRY"}
            ),
            key=_openrouter_schedule_key_v1,
        )
        if openrouter_future is None and openrouter and time.monotonic() >= openrouter_not_before:
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
                openrouter_only=getattr(args, "openrouter_only", False),
            )
        available = _google_submit_capacity_v1(
            active_count=len(active_google),
            future_count=len(google_submit_futures),
            max_active=args.max_active_google,
        )
        inflight_google_task_ids = set(google_submit_futures.values())
        submit_now = time.monotonic()
        for task in [
            item
            for item in unfinished
            if item["route"] == GOOGLE_ROUTE
            and item["state"] in {"PENDING", "NEEDS_RETRY"}
            and item["task_id"] not in inflight_google_task_ids
            and _google_submit_ready_v1(
                task_id=item["task_id"],
                now=submit_now,
                global_not_before=google_submit_global_not_before,
                task_not_before=google_submit_not_before,
            )
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
        cooling_google = [
            deadline
            for task_id, deadline in google_submit_not_before.items()
            if deadline > time.monotonic()
            and any(task["task_id"] == task_id for task in unfinished)
        ]
        if google_submit_global_not_before > time.monotonic() and any(
            task["route"] == GOOGLE_ROUTE and task["state"] in {"PENDING", "NEEDS_RETRY"}
            for task in unfinished
        ):
            cooling_google.append(google_submit_global_not_before)
        if cooling_google:
            time.sleep(min(max(0.0, min(cooling_google) - time.monotonic()), 1.0))
            continue
        if openrouter and openrouter_not_before > time.monotonic():
            time.sleep(min(openrouter_not_before - time.monotonic(), 1.0))
            continue
        if accelerated_google:
            # A separate accelerator owns this document under a sealed ledger
            # claim.  It will atomically move every task in the document to a
            # terminal state; the ordinary supervisor must neither poll the
            # claim as a Google batch nor mistake it for a dead scheduler.
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


def run_one_openrouter_task(args: argparse.Namespace) -> dict[str, Any]:
    """Run one exact pending Flex document and leave the corpus ledger resumable."""

    if args.openrouter_only is not True:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "single-task execution requires --openrouter-only"
        )
    if not 1 <= args.openrouter_workers <= 30:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter worker bound lies outside 1..30"
        )
    plan = _plan(args.plan)
    if not args.ledger.is_file():
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "single-task execution requires an initialized corpus ledger"
        )
    summary = corpus_ledger_summary_v1(args.ledger)
    if summary["corpus_plan_id"] != plan["corpus_plan_id"]:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error("ledger and plan identity disagree")
    matches = [
        task for task in list_corpus_tasks_v1(args.ledger) if task["task_id"] == args.task_id
    ]
    if len(matches) != 1:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "single-task execution requires one exact ledger task"
        )
    task = matches[0]
    if task["route"] != OPENROUTER_ROUTE or task["state"] not in {
        "PENDING",
        "RUNNING",
        "NEEDS_RETRY",
    }:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "single-task execution requires one runnable OpenRouter task"
        )
    args.artifact_root.mkdir(parents=True, exist_ok=True)
    _write_or_verify(args.artifact_root / "corpus-plan.json", canonical_json_bytes_v1(plan))
    task_result = _run_openrouter(
        task=task,
        plan=plan,
        ledger=args.ledger,
        source_root=args.source_root,
        database=args.database,
        artifact_root=args.artifact_root,
        openrouter_key_file=args.openrouter_key_file,
        openrouter_workers=args.openrouter_workers,
        google_key_file=args.google_key_file,
        google_key_slot=1,
        provider_timeout_seconds=args.provider_timeout_seconds,
        max_attempts=summary["max_task_attempts"],
        openrouter_only=True,
    )
    receipt_bytes = task_result.get("last_receipt_json")
    if type(receipt_bytes) is not bytes:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "single-task result lacks its exact receipt bytes"
        )
    state = task_result.get("state")
    if state not in {"SUCCEEDED", "FAILED", "NEEDS_RETRY"}:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "single-task result is not terminal or retryable"
        )
    return {
        "corpus_run_id": summary["corpus_run_id"],
        "disposition": state,
        "ledger": corpus_ledger_summary_v1(args.ledger),
        "task": {
            "attempt_count": task_result["attempt_count"],
            "last_receipt_sha256": sha256(receipt_bytes).hexdigest(),
            "state": state,
            "task_id": args.task_id,
        },
    }


def requeue_openrouter_task(args: argparse.Namespace) -> dict[str, Any]:
    """Reopen one exact failed Flex task only when its retry bound permits."""

    plan = _plan(args.plan)
    summary = corpus_ledger_summary_v1(args.ledger)
    if summary["corpus_plan_id"] != plan["corpus_plan_id"]:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error("ledger and plan identity disagree")
    task = requeue_failed_openrouter_corpus_task_v1(
        args.ledger,
        task_id=args.task_id,
    )
    receipt_bytes = task.get("last_receipt_json")
    if type(receipt_bytes) is not bytes:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "requeued OpenRouter task lacks its exact receipt bytes"
        )
    return {
        "corpus_run_id": summary["corpus_run_id"],
        "disposition": "NEEDS_RETRY",
        "ledger": corpus_ledger_summary_v1(args.ledger),
        "task": {
            "attempt_count": task["attempt_count"],
            "last_receipt_sha256": sha256(receipt_bytes).hexdigest(),
            "state": task["state"],
            "task_id": task["task_id"],
        },
    }


def recover_openrouter_artifact_collision(args: argparse.Namespace) -> dict[str, Any]:
    """Resume an exhausted Flex attempt proven to have made no provider call."""

    plan = _plan(args.plan)
    summary = corpus_ledger_summary_v1(args.ledger)
    if summary["corpus_plan_id"] != plan["corpus_plan_id"]:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error("ledger and plan identity disagree")
    task = recover_failed_openrouter_artifact_collision_v1(
        args.ledger,
        task_id=args.task_id,
        artifact_root=args.artifact_root,
    )
    receipt_bytes = task.get("last_receipt_json")
    if type(receipt_bytes) is not bytes:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "recovered OpenRouter task lacks its exact receipt bytes"
        )
    return {
        "corpus_run_id": summary["corpus_run_id"],
        "disposition": "RUNNING",
        "ledger": corpus_ledger_summary_v1(args.ledger),
        "task": {
            "attempt_count": task["attempt_count"],
            "last_receipt_sha256": sha256(receipt_bytes).hexdigest(),
            "state": task["state"],
            "task_id": task["task_id"],
        },
    }


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
        "--openrouter-route-policy",
        "flex-then-standard",
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
    for physical_page in range(task["first_physical_page"], task["last_physical_page"] + 1):
        command.extend(("--physical-page", str(physical_page)))
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


def _canonical_repair_receipt_v1(path: Path) -> dict[str, Any]:
    receipt = _json_file(path)
    if path.read_bytes() != canonical_json_bytes_v1(receipt):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter exhausted-page repair receipt is not canonical"
        )
    return receipt


def _repair_successful_prompt_context_v1(
    repair_results: list[dict[str, Any]],
) -> tuple[dict[int, str], list[int]]:
    variants: dict[int, str] = {}
    protected: set[int] = set()
    for item in repair_results:
        pages = item.get("physical_pages") if type(item) is dict else None
        accepted = item.get("accepted_pages") if type(item) is dict else None
        variant = item.get("prompt_variant") if type(item) is dict else None
        if (
            type(pages) is not list
            or type(accepted) is not list
            or not set(accepted).issubset(pages)
            or type(variant) is not str
        ):
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "OpenRouter exhausted-page prompt history is invalid"
            )
        for page in accepted:
            variants[page] = variant
        if variant == "items":
            protected.update(accepted)
    return variants, sorted(protected)


def _offline_semantic_replay_result_v1(
    *,
    args: argparse.Namespace,
    attempt_root: Path,
    current_images: dict[int, str],
    prompt_variant: str,
    semantic_pages: list[int],
    source: Path,
    task: dict[str, Any],
    task_root: Path,
    dpi: int,
) -> dict[str, Any] | None:
    """Revalidate paid semantic responses without authorizing another provider call."""

    if not semantic_pages:
        return None
    frontier_sha256 = canonical_json_sha256_v1(semantic_pages)
    selected_artifact_dir = (
        attempt_root / "offline-semantic-replay" / prompt_variant / f"pages-{frontier_sha256}"
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
        str(selected_artifact_dir),
        "--semantic-replay-source-dir",
        str(task_root),
        "--dpi",
        str(dpi),
        "--workers",
        str(args.openrouter_workers),
        "--prompt-variant",
        prompt_variant,
        "--output-contract-mode",
        "json-schema",
        "--offline-replay-only",
        "--google-standard-mode",
        "disabled",
    ]
    for page in semantic_pages:
        command.extend(("--physical-page", str(page)))
    _code, result = _command(command, expected={0, 2})
    result_images = _summary_page_image_sha256s_v1(
        result.get("page_image_sha256s"), allowed_pages=semantic_pages
    )
    completed = sorted(set(result.get("cached_pages", [])) | set(result.get("ingested_pages", [])))
    failed = result.get("failed_pages")
    if (
        result.get("execution_mode") != "OFFLINE_REPLAY_ONLY"
        or result_images != {page: current_images[page] for page in semantic_pages}
        or type(failed) is not list
        or failed != sorted(set(failed))
        or set(completed) & set(failed)
        or sorted(set(completed) | set(failed)) != semantic_pages
        or result.get("provider_request_pages") != []
        or result.get("recitation_failed_pages", []) != []
        or any(
            type(values) is not list or not set(values).issubset(failed)
            for values in (
                result.get("semantic_failed_pages", []),
                result.get("unresolved_pages", []),
                result.get("offline_missing_pages", []),
            )
        )
    ):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "offline semantic replay result frontier is invalid"
        )
    return {
        "accepted_pages": completed,
        "execution_mode": "OFFLINE_REPLAY_ONLY",
        "physical_pages": semantic_pages,
        "prompt_variant": prompt_variant,
        "repair_attempt": args.repair_attempt,
        "result": result,
    }


def repair_openrouter_flex_pages_task(args: argparse.Namespace) -> dict[str, Any]:
    """Repair only an exhausted task's exact failed pages through Vertex Flex."""

    plan = _plan(args.plan)
    summary = corpus_ledger_summary_v1(args.ledger)
    if summary["corpus_plan_id"] != plan["corpus_plan_id"]:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error("ledger and plan identity disagree")
    if not 1 <= args.openrouter_workers <= 30:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter worker bound lies outside 1..30"
        )
    tasks = list_corpus_tasks_v1(args.ledger, states=["FAILED"], route=OPENROUTER_ROUTE)
    selected = [task for task in tasks if task["task_id"] == args.task_id]
    if len(selected) != 1:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "Flex page repair requires one exact exhausted OpenRouter task"
        )
    task = selected[0]
    source = _source(task, args.source_root)
    task_root = _task_root(task, args.artifact_root)
    repair_root = task_root / "openrouter-exhausted-page-repair"
    receipts_root = repair_root / "receipts"
    receipt_path = receipts_root / f"attempt-{args.repair_attempt:02d}.json"
    ledger_failed_sha256 = sha256(task["last_receipt_json"]).hexdigest()
    if receipt_path.exists():
        receipt = _canonical_repair_receipt_v1(receipt_path)
        if (
            receipt.get("repair_attempt") != args.repair_attempt
            or receipt.get("prior_failed_receipt_sha256") != ledger_failed_sha256
        ):
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "OpenRouter exhausted-page repair receipt binding drifted"
            )
        if receipt.get("disposition") == "SUCCEEDED":
            sealed = seal_openrouter_exhausted_page_repair_corpus_task_v1(
                args.ledger, task_id=task["task_id"], receipt=receipt
            )
            return {
                "disposition": "SUCCEEDED",
                "repair_attempt": args.repair_attempt,
                "resumed_from_receipt": True,
                "task_id": sealed["task_id"],
            }
        return {
            "disposition": receipt.get("disposition"),
            "failed_pages": receipt.get("failed_pages"),
            "repair_attempt": args.repair_attempt,
            "resumed_from_receipt": True,
            "task_id": task["task_id"],
        }

    prior_provider_results: list[dict[str, Any]] = []
    prior_offline_replay_results: list[dict[str, Any]] = []
    if args.repair_attempt == 1:
        if receipts_root.exists() and any(receipts_root.glob("attempt-*.json")):
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "OpenRouter exhausted-page repair attempt order drifted"
            )
        frontier_receipt = _terminal_repair_frontier_receipt_v1(
            task=task,
            ledger=args.ledger,
        )
    else:
        prior_path = receipts_root / "attempt-01.json"
        frontier_receipt = _canonical_repair_receipt_v1(prior_path)
        if (
            frontier_receipt.get("format_version")
            not in {
                "GEMINI_JSON_FIRST_OPENROUTER_EXHAUSTED_PAGE_REPAIR_V1",
                "GEMINI_JSON_FIRST_OPENROUTER_EXHAUSTED_PAGE_REPAIR_V2",
            }
            or frontier_receipt.get("disposition") != "NEEDS_REPAIR"
            or frontier_receipt.get("repair_attempt") != 1
            or frontier_receipt.get("prior_failed_receipt_sha256") != ledger_failed_sha256
            or type(frontier_receipt.get("provider_results")) is not list
        ):
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "prior OpenRouter exhausted-page repair receipt is invalid"
            )
        prior_provider_results = frontier_receipt["provider_results"]
        if frontier_receipt["format_version"].endswith("_V2"):
            prior_offline_replay_results = frontier_receipt.get("offline_replay_results")
            if type(prior_offline_replay_results) is not list:
                raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                    "prior offline semantic replay history is invalid"
                )
    frontiers = _retry_prompt_frontiers_from_receipt_v1(
        frontier_receipt,
        first_physical_page=task["first_physical_page"],
        last_physical_page=task["last_physical_page"],
    )
    repair_pages = sorted(page for pages in frontiers.values() for page in pages)
    current_images = _current_page_image_sha256s_v1(
        task=task, source_root=args.source_root, dpi=plan["policy"]["dpi"]
    )
    attempt_root = repair_root / f"attempt-{args.repair_attempt:02d}"
    offline_replay_results = list(prior_offline_replay_results)
    semantic_pages = frontier_receipt.get("semantic_failed_pages", [])
    if type(semantic_pages) is not list or not set(semantic_pages).issubset(repair_pages):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter semantic replay frontier is invalid"
        )
    offline_item = _offline_semantic_replay_result_v1(
        args=args,
        attempt_root=attempt_root,
        current_images=current_images,
        prompt_variant=summary["prompt_variant"],
        semantic_pages=semantic_pages,
        source=source,
        task=task,
        task_root=task_root,
        dpi=plan["policy"]["dpi"],
    )
    offline_accepted: list[int] = []
    if offline_item is not None:
        offline_replay_results.append(offline_item)
        offline_accepted = offline_item["accepted_pages"]
    provider_frontiers = {
        name: sorted(set(pages) - set(offline_accepted)) for name, pages in frontiers.items()
    }
    contract = {
        "format_version": "GEMINI_JSON_FIRST_OPENROUTER_EXHAUSTED_PAGE_REPAIR_CONTRACT_V1",
        "page_image_sha256s": [
            {"image_sha256": current_images[page], "physical_page": page} for page in repair_pages
        ],
        "prior_failed_receipt_sha256": ledger_failed_sha256,
        "offline_semantic_replay_frontier": semantic_pages,
        "prompt_frontiers": [
            {"physical_pages": pages, "prompt_variant": variant}
            for variant, pages in (
                (summary["prompt_variant"], provider_frontiers["default"]),
                ("scope", provider_frontiers["scope"]),
                ("items", provider_frontiers["items"]),
            )
            if pages
        ],
        "repair_attempt": args.repair_attempt,
        "requested_gateway": "OPENROUTER",
        "requested_model": GOOGLE_MODEL,
        "requested_service_tier": OPENROUTER_SERVICE_TIER,
        "source_sha256": task["source_sha256"],
        "task_id": task["task_id"],
    }
    _write_or_verify(attempt_root / "repair-contract.json", canonical_json_bytes_v1(contract))

    provider_results = list(prior_provider_results)
    aggregate: dict[str, list[int]] = {
        "failed_pages": [],
        "offline_missing_pages": [],
        "recitation_failed_pages": [],
        "semantic_failed_pages": [],
        "unresolved_pages": [],
    }
    current_prompt_variants: dict[int, str] = {
        page: summary["prompt_variant"] for page in offline_accepted
    }
    provider_circuit_open = False
    for prompt_variant, pages in (
        (summary["prompt_variant"], provider_frontiers["default"]),
        ("scope", provider_frontiers["scope"]),
        ("items", provider_frontiers["items"]),
    ):
        if not pages:
            continue
        offline_due_to_circuit = provider_circuit_open
        frontier_sha256 = canonical_json_sha256_v1(pages)
        selected_artifact_dir = attempt_root / prompt_variant / f"pages-{frontier_sha256}"
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
            str(selected_artifact_dir),
            "--dpi",
            str(plan["policy"]["dpi"]),
            "--workers",
            str(args.openrouter_workers),
            "--prompt-variant",
            prompt_variant,
            "--output-contract-mode",
            "json-schema",
            "--openrouter-key-file",
            str(args.openrouter_key_file),
            "--openrouter-route-policy",
            "flex-then-standard",
            "--google-key-file",
            str(args.google_key_file),
            "--google-key-slot",
            "1",
            "--google-standard-mode",
            "disabled",
            "--timeout-seconds",
            str(args.provider_timeout_seconds),
        ]
        if args.openrouter_workers == 1:
            command.append("--stop-provider-frontier-on-transient-error")
        if offline_due_to_circuit:
            command.append("--offline-replay-only")
        for page in pages:
            command.extend(("--physical-page", str(page)))
        _code, result = _command(command, expected={0, 2})
        result_images = _summary_page_image_sha256s_v1(
            result.get("page_image_sha256s"), allowed_pages=pages
        )
        if result_images != {page: current_images[page] for page in pages}:
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "Flex page repair image frontier drifted"
            )
        completed = sorted(
            set(result.get("cached_pages", [])) | set(result.get("ingested_pages", []))
        )
        failed = result.get("failed_pages")
        if (
            type(failed) is not list
            or failed != sorted(set(failed))
            or set(completed) & set(failed)
            or sorted(set(completed) | set(failed)) != pages
        ):
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "Flex page repair result frontier is invalid"
            )
        result_item = {
            "accepted_pages": completed,
            "physical_pages": pages,
            "prompt_variant": prompt_variant,
            "repair_attempt": args.repair_attempt,
            "result": result,
        }
        if offline_due_to_circuit:
            if (
                result.get("execution_mode") != "OFFLINE_REPLAY_ONLY"
                or result.get("provider_request_pages") != []
            ):
                raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                    "Flex page repair crossed an open provider circuit"
                )
            offline_replay_results.append({**result_item, "execution_mode": "OFFLINE_REPLAY_ONLY"})
        else:
            provider_results.append(result_item)
        current_prompt_variants.update({page: prompt_variant for page in completed})
        for field in aggregate:
            values = result.get(field, [])
            if type(values) is not list or not set(values).issubset(pages):
                raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                    "Flex page repair typed failure frontier is invalid"
                )
            aggregate[field].extend(values)
        circuit_trigger_page = result.get("provider_circuit_breaker_trigger_page")
        if circuit_trigger_page is not None and (
            offline_due_to_circuit
            or type(circuit_trigger_page) is not int
            or circuit_trigger_page not in pages
        ):
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "Flex page repair provider circuit trigger page is invalid"
            )
        if type(circuit_trigger_page) is int:
            provider_circuit_open = True

    failed_pages = sorted(set(aggregate["failed_pages"]))
    disposition = "NEEDS_REPAIR" if failed_pages else "SUCCEEDED"
    document_manifest_id = None
    revalidated_pages: list[int] = []
    if not failed_pages:
        historical_variants, historical_protected = _successful_historical_prompt_context_v1(
            ledger=args.ledger, task=task
        )
        repaired_variants, repaired_protected = _repair_successful_prompt_context_v1(
            [*provider_results, *offline_replay_results]
        )
        complete_variants = {
            **historical_variants,
            **repaired_variants,
            **current_prompt_variants,
        }
        manifest = _page_variant_manifest_v1(
            task=task,
            ledger=args.ledger,
            database=args.database,
            artifact_root=args.artifact_root,
            page_image_sha256s=current_images,
            page_prompt_variants=complete_variants,
            write=False,
        )
        protected = sorted(set(historical_protected) | set(repaired_protected))
        dropped = _semantic_retry_no_relevant_pages_v1(manifest, protected_pages=protected)
        if dropped:
            failed_pages = dropped
            aggregate["semantic_failed_pages"] = dropped
            disposition = "NEEDS_REPAIR"
            for item in provider_results:
                item["accepted_pages"] = sorted(set(item["accepted_pages"]) - set(dropped))
            for item in offline_replay_results:
                item["accepted_pages"] = sorted(set(item["accepted_pages"]) - set(dropped))
        else:
            document_manifest_id = manifest["document_manifest_id"]
            revalidated_pages = list(
                range(task["first_physical_page"], task["last_physical_page"] + 1)
            )
            _write_or_verify(
                attempt_root / "document-manifest.json", canonical_json_bytes_v1(manifest)
            )
    receipt = {
        "disposition": disposition,
        "document_manifest_id": document_manifest_id,
        "failed_pages": failed_pages,
        "format_version": "GEMINI_JSON_FIRST_OPENROUTER_EXHAUSTED_PAGE_REPAIR_V2",
        "offline_replay_results": offline_replay_results,
        "offline_missing_pages": sorted(set(aggregate["offline_missing_pages"])),
        "prior_failed_receipt_sha256": ledger_failed_sha256,
        "provider_results": provider_results,
        "recitation_failed_pages": sorted(set(aggregate["recitation_failed_pages"])),
        "repair_attempt": args.repair_attempt,
        "repair_gateway": "OPENROUTER",
        "requested_service_tier": OPENROUTER_SERVICE_TIER,
        "revalidated_pages": revalidated_pages,
        "semantic_failed_pages": sorted(set(aggregate["semantic_failed_pages"])),
        "unresolved_pages": sorted(set(aggregate["unresolved_pages"])),
    }
    _write_or_verify(receipt_path, canonical_json_bytes_v1(receipt))
    if disposition != "SUCCEEDED":
        return {
            "disposition": disposition,
            "failed_pages": failed_pages,
            "repair_attempt": args.repair_attempt,
            "task_id": task["task_id"],
        }
    sealed = seal_openrouter_exhausted_page_repair_corpus_task_v1(
        args.ledger, task_id=task["task_id"], receipt=receipt
    )
    return {
        "disposition": "SUCCEEDED",
        "document_manifest_id": document_manifest_id,
        "repair_attempt": args.repair_attempt,
        "task_id": sealed["task_id"],
    }


def _next_exhausted_page_repair_attempt_v1(
    *, task: dict[str, Any], artifact_root: Path
) -> int | None:
    """Return the next bounded repair attempt, replaying any crash receipt first."""

    raw = task.get("last_receipt_json")
    if type(raw) is not bytes:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "failed OpenRouter task lacks its exact receipt bytes"
        )
    prior_sha256 = sha256(raw).hexdigest()
    receipts_root = (
        _task_root(task, artifact_root) / "openrouter-exhausted-page-repair" / "receipts"
    )
    for attempt in (1, 2):
        path = receipts_root / f"attempt-{attempt:02d}.json"
        if not path.exists():
            if attempt == 2 and not (receipts_root / "attempt-01.json").exists():
                raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                    "OpenRouter exhausted-page repair attempt order drifted"
                )
            return attempt
        receipt = _canonical_repair_receipt_v1(path)
        if (
            receipt.get("format_version")
            not in {
                "GEMINI_JSON_FIRST_OPENROUTER_EXHAUSTED_PAGE_REPAIR_V1",
                "GEMINI_JSON_FIRST_OPENROUTER_EXHAUSTED_PAGE_REPAIR_V2",
            }
            or receipt.get("repair_attempt") != attempt
            or receipt.get("prior_failed_receipt_sha256") != prior_sha256
            or receipt.get("disposition") not in {"NEEDS_REPAIR", "SUCCEEDED"}
        ):
            raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                "OpenRouter exhausted-page repair history is invalid"
            )
        if receipt["disposition"] == "SUCCEEDED":
            if attempt == 1 and (receipts_root / "attempt-02.json").exists():
                raise RunGeminiJsonFirstCorpusSupervisorV1Error(
                    "OpenRouter exhausted-page repair continued after success"
                )
            return attempt
    return None


def _exhausted_page_repair_receipt_has_circuit_v1(
    *, task: dict[str, Any], artifact_root: Path, repair_attempt: int
) -> bool:
    path = (
        _task_root(task, artifact_root)
        / "openrouter-exhausted-page-repair"
        / "receipts"
        / f"attempt-{repair_attempt:02d}.json"
    )
    receipt = _canonical_repair_receipt_v1(path)
    return _openrouter_task_result_has_circuit_trip_v1(
        {"last_receipt_json": canonical_json_bytes_v1(receipt)}
    )


def _terminal_repair_frontier_receipt_v1(
    *,
    task: dict[str, Any],
    ledger: Path,
) -> dict[str, Any]:
    """Read a direct frontier, or recover it from the ledger event chain."""

    raw = task.get("last_receipt_json")
    try:
        receipt = json.loads(raw) if type(raw) is bytes else None
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "failed OpenRouter task receipt is invalid"
        ) from exc
    if type(receipt) is dict and "failed_pages" in receipt:
        return receipt
    try:
        return openrouter_failed_task_repair_frontier_v1(
            ledger,
            task_id=task["task_id"],
        )
    except GeminiJsonFirstCorpusLedgerV1Error as exc:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "failed OpenRouter task has no authenticated repair frontier"
        ) from exc


def _exhausted_page_repair_remaining_page_count_v1(
    *, task: dict[str, Any], ledger: Path, artifact_root: Path, repair_attempt: int
) -> int:
    """Count only the exact pages still named by the next immutable receipt."""

    receipts_root = (
        _task_root(task, artifact_root) / "openrouter-exhausted-page-repair" / "receipts"
    )
    current_path = receipts_root / f"attempt-{repair_attempt:02d}.json"
    if current_path.exists():
        current = _canonical_repair_receipt_v1(current_path)
        if current.get("disposition") == "SUCCEEDED":
            return 0
    if repair_attempt == 1:
        frontier_receipt = _terminal_repair_frontier_receipt_v1(
            task=task,
            ledger=ledger,
        )
    else:
        frontier_receipt = _canonical_repair_receipt_v1(receipts_root / "attempt-01.json")
    frontiers = _retry_prompt_frontiers_from_receipt_v1(
        frontier_receipt,
        first_physical_page=task["first_physical_page"],
        last_physical_page=task["last_physical_page"],
    )
    return sum(len(pages) for pages in frontiers.values())


def repair_failed_openrouter_flex_tasks(args: argparse.Namespace) -> dict[str, Any]:
    """Repair terminal Flex tasks only after the ordinary corpus frontier ends."""

    if not 1 <= args.max_repair_actions <= 558:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "terminal Flex repair action bound lies outside 1..558"
        )
    if not 1 <= args.openrouter_workers <= 30:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter worker bound lies outside 1..30"
        )
    if (
        type(args.openrouter_circuit_cooldown_seconds) not in {int, float}
        or not 0 <= args.openrouter_circuit_cooldown_seconds <= 3_600
    ):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "OpenRouter circuit cooldown lies outside 0..3600 seconds"
        )
    plan = _plan(args.plan)
    summary = corpus_ledger_summary_v1(args.ledger)
    if summary["corpus_plan_id"] != plan["corpus_plan_id"]:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error("ledger and plan identity disagree")
    initial_tasks = list_corpus_tasks_v1(args.ledger)
    unfinished = [task for task in initial_tasks if task["state"] not in {"SUCCEEDED", "FAILED"}]
    if unfinished:
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "terminal Flex repair requires the ordinary corpus frontier to be exhausted"
        )
    if any(task.get("route") != OPENROUTER_ROUTE for task in initial_tasks):
        raise RunGeminiJsonFirstCorpusSupervisorV1Error(
            "terminal Flex repair requires an OpenRouter-only corpus ledger"
        )

    actions: list[dict[str, Any]] = []
    completed_task_ids: list[str] = []
    consecutive_circuit_trips = 0
    while len(actions) < args.max_repair_actions:
        failed = list_corpus_tasks_v1(args.ledger, states=["FAILED"], route=OPENROUTER_ROUTE)
        candidates: list[tuple[int, str, dict[str, Any], int]] = []
        for task in failed:
            attempt = _next_exhausted_page_repair_attempt_v1(
                task=task, artifact_root=args.artifact_root
            )
            if attempt is not None:
                candidates.append(
                    (
                        _exhausted_page_repair_remaining_page_count_v1(
                            task=task,
                            ledger=args.ledger,
                            artifact_root=args.artifact_root,
                            repair_attempt=attempt,
                        ),
                        task["relative_path"],
                        task,
                        attempt,
                    )
                )
        if not candidates:
            break
        _page_count, _relative_path, task, repair_attempt = min(
            candidates, key=lambda item: (item[0], item[1])
        )
        result = repair_openrouter_flex_pages_task(
            argparse.Namespace(**vars(args), task_id=task["task_id"], repair_attempt=repair_attempt)
        )
        circuit_tripped = _exhausted_page_repair_receipt_has_circuit_v1(
            task=task,
            artifact_root=args.artifact_root,
            repair_attempt=repair_attempt,
        )
        action = {
            "circuit_tripped": circuit_tripped,
            "disposition": result["disposition"],
            "failed_pages": result.get("failed_pages", []),
            "relative_path": task["relative_path"],
            "repair_attempt": repair_attempt,
            "task_id": task["task_id"],
        }
        actions.append(action)
        if result["disposition"] == "SUCCEEDED":
            completed_task_ids.append(task["task_id"])
        if circuit_tripped:
            consecutive_circuit_trips += 1
        else:
            consecutive_circuit_trips = 0
        if circuit_tripped and len(actions) < args.max_repair_actions:
            remaining = list_corpus_tasks_v1(args.ledger, states=["FAILED"], route=OPENROUTER_ROUTE)
            if any(
                _next_exhausted_page_repair_attempt_v1(task=item, artifact_root=args.artifact_root)
                is not None
                for item in remaining
            ):
                time.sleep(
                    _openrouter_circuit_cooldown_v1(
                        base_seconds=args.openrouter_circuit_cooldown_seconds,
                        consecutive_trips=consecutive_circuit_trips,
                    )
                )

    remaining_failed = list_corpus_tasks_v1(args.ledger, states=["FAILED"], route=OPENROUTER_ROUTE)
    repairable_task_ids = sorted(
        task["task_id"]
        for task in remaining_failed
        if _next_exhausted_page_repair_attempt_v1(task=task, artifact_root=args.artifact_root)
        is not None
    )
    exhausted_task_ids = sorted(
        set(task["task_id"] for task in remaining_failed) - set(repairable_task_ids)
    )
    disposition = (
        "SUCCEEDED" if not remaining_failed else "NEEDS_REPAIR" if repairable_task_ids else "FAILED"
    )
    return {
        "actions": actions,
        "completed_task_ids": sorted(completed_task_ids),
        "disposition": disposition,
        "exhausted_task_ids": exhausted_task_ids,
        "ledger": corpus_ledger_summary_v1(args.ledger),
        "repairable_task_ids": repairable_task_ids,
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
    if args.command in OPENROUTER_CREDENTIAL_COMMANDS:
        _preflight_openrouter_credential_v1(args.openrouter_key_file)
    if args.command == "init":
        result = initialize_gemini_json_first_corpus_ledger_v1(
            args.ledger,
            plan=_plan(args.plan),
            prompt_variant=args.prompt_variant,
            max_task_attempts=args.max_task_attempts,
        )
    elif args.command == "status":
        result = corpus_ledger_summary_v1(args.ledger)
    elif args.command == "requeue-openrouter":
        result = requeue_openrouter_task(args)
    elif args.command == "recover-openrouter-artifact-collision":
        result = recover_openrouter_artifact_collision(args)
    elif args.command == "repair-openrouter":
        result = repair_openrouter_task(args)
    elif args.command == "repair-openrouter-items":
        result = repair_openrouter_items_task(args)
    elif args.command == "repair-openrouter-google":
        result = repair_openrouter_google_task(args)
    elif args.command == "repair-openrouter-flex-pages":
        result = repair_openrouter_flex_pages_task(args)
    elif args.command == "repair-openrouter-flex-failed":
        result = repair_failed_openrouter_flex_tasks(args)
    elif args.command == "document-manifest-current":
        result = build_current_document_manifest(args)
    elif args.command == "corpus-manifest-current":
        result = build_current_corpus_manifest(args)
    elif args.command == "accelerate-google-document":
        result = accelerate_google_document(args)
    elif args.command == "accelerate-pending-google":
        result = accelerate_pending_google_documents(args)
    elif args.command == "run-openrouter-task":
        result = run_one_openrouter_task(args)
    else:
        result = run_corpus(args)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("disposition") not in {"FAILED", "NEEDS_REPAIR", "NEEDS_RETRY"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
