"""Crash-resumable task ledger for the Gemini JSON-first corpus plan."""

from __future__ import annotations

import fcntl
import json
import os
import sqlite3
import tempfile
from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.gemini_json_first_corpus_plan_v1 import (
    GOOGLE_ROUTE,
    OPENROUTER_ROUTE,
    build_gemini_json_first_corpus_plan_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

FORMAT_VERSION = "GEMINI_JSON_FIRST_CORPUS_LEDGER_V2"
TASK_STATES = frozenset(
    {
        "PENDING",
        "SUBMITTED",
        "RUNNING",
        "SUCCEEDED",
        "NEEDS_RETRY",
        "FALLBACK_PENDING",
        "FALLBACK_RUNNING",
        "FAILED",
    }
)
TERMINAL_TASK_STATES = frozenset({"SUCCEEDED", "FAILED"})
AGY_PROVIDER_JOB_PREFIX = "agyjobv1:"
CKEY_PROVIDER_JOB_PREFIX = "ckeyjobv1:"

_TRANSITIONS = {
    "PENDING": frozenset({"SUBMITTED", "RUNNING", "FAILED"}),
    "SUBMITTED": frozenset({"RUNNING", "SUCCEEDED", "NEEDS_RETRY", "FAILED"}),
    "RUNNING": frozenset({"SUCCEEDED", "NEEDS_RETRY", "FALLBACK_PENDING", "FAILED"}),
    "NEEDS_RETRY": frozenset({"SUBMITTED", "RUNNING", "FAILED"}),
    "FALLBACK_PENDING": frozenset({"FALLBACK_RUNNING", "FAILED"}),
    "FALLBACK_RUNNING": frozenset({"SUCCEEDED", "FALLBACK_PENDING", "FAILED"}),
    "SUCCEEDED": frozenset(),
    "FAILED": frozenset(),
}

_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE run_identity (
  singleton INTEGER PRIMARY KEY CHECK(singleton=1),
  format_version TEXT NOT NULL,
  corpus_run_id TEXT NOT NULL UNIQUE,
  corpus_plan_id TEXT NOT NULL,
  corpus_plan_sha256 TEXT NOT NULL,
  prompt_variant TEXT NOT NULL,
  output_contract_mode TEXT NOT NULL,
  max_task_attempts INTEGER NOT NULL
) STRICT;
CREATE TABLE task (
  task_id TEXT PRIMARY KEY,
  document_plan_id TEXT NOT NULL,
  relative_path TEXT NOT NULL,
  source_sha256 TEXT NOT NULL,
  source_size_bytes INTEGER NOT NULL,
  document_page_count INTEGER NOT NULL,
  route TEXT NOT NULL,
  task_kind TEXT NOT NULL,
  first_physical_page INTEGER NOT NULL,
  last_physical_page INTEGER NOT NULL,
  artifact_relative_path TEXT NOT NULL UNIQUE,
  state TEXT NOT NULL,
  attempt_count INTEGER NOT NULL,
  provider_job_ref TEXT,
  last_receipt_json BLOB,
  CHECK(state IN ('PENDING','SUBMITTED','RUNNING','SUCCEEDED','NEEDS_RETRY',
                  'FALLBACK_PENDING','FALLBACK_RUNNING','FAILED')),
  CHECK(route IN ('GOOGLE_GEMINI_BATCH_API','OPENROUTER_VERTEX_FLEX')),
  CHECK(first_physical_page > 0),
  CHECK(last_physical_page >= first_physical_page),
  CHECK(attempt_count >= 0)
) STRICT;
CREATE TABLE task_event (
  task_id TEXT NOT NULL,
  event_ordinal INTEGER NOT NULL,
  prior_state TEXT NOT NULL,
  next_state TEXT NOT NULL,
  receipt_json BLOB NOT NULL,
  PRIMARY KEY(task_id, event_ordinal),
  FOREIGN KEY(task_id) REFERENCES task(task_id)
) STRICT;
CREATE INDEX idx_corpus_task_state_route ON task(state, route, relative_path, first_physical_page);
CREATE INDEX idx_corpus_task_document ON task(document_plan_id, first_physical_page);
"""


class GeminiJsonFirstCorpusLedgerV1Error(ValueError):
    """The plan, task transition, or persisted task state is not exact."""


def _error(message: str) -> GeminiJsonFirstCorpusLedgerV1Error:
    return GeminiJsonFirstCorpusLedgerV1Error(message)


def acquire_corpus_task_execution_lock_v1(
    path: Path,
    *,
    task_id: str,
) -> Any:
    """Acquire one non-blocking provider lease for an exact ledger task.

    The task row remains the durable workflow record.  This process lease
    closes the much smaller selection-to-transition race between independent
    repair dispatchers: only the process holding it may claim or send the
    selected task.  The kernel releases the lease after a crash, so it cannot
    strand a corpus task in a new persistent state.
    """

    if type(task_id) is not str or not task_id.startswith("gjfptaskv1:"):
        raise _error("corpus task execution lock identity is invalid")
    with _connect(path, readonly=True) as connection:
        row = connection.execute("SELECT task_id FROM task WHERE task_id=?", (task_id,)).fetchone()
    if row is None:
        raise _error("corpus task execution lock task is absent")
    lock_root = path.resolve().with_name(path.name + ".task-locks")
    if lock_root.exists() and (lock_root.is_symlink() or not lock_root.is_dir()):
        raise _error("corpus task execution lock root is invalid")
    lock_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_path = lock_root / (task_id.removeprefix("gjfptaskv1:") + ".lock")
    handle = lock_path.open("a+b")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        handle.close()
        raise _error("corpus task execution is already owned") from exc
    return handle


def validate_gemini_json_first_corpus_plan_v1(value: Any) -> dict[str, Any]:
    """Rebuild and exact-compare an immutable corpus plan."""

    if type(value) is not dict:
        raise _error("corpus plan must be one object")
    required = {"corpus_plan_id", "documents", "format_version", "policy", "summary"}
    if set(value) != required or type(value.get("documents")) is not list:
        raise _error("corpus plan fields drifted")
    policy = value.get("policy")
    if type(policy) is not dict:
        raise _error("corpus plan policy is absent")
    documents = []
    for planned in value["documents"]:
        if type(planned) is not dict or type(planned.get("document")) is not dict:
            raise _error("corpus planned document is invalid")
        documents.append(planned["document"])
    try:
        rebuilt = build_gemini_json_first_corpus_plan_v1(
            documents,
            dpi=policy["dpi"],
            google_batch_chunk_pages=policy["google_batch_chunk_pages"],
            openrouter_page_fraction=policy["openrouter_page_fraction"],
            openrouter_workers=policy["openrouter_workers"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise _error("corpus plan cannot be rebuilt") from exc
    if rebuilt != value:
        raise _error("corpus plan does not replay exactly")
    return canonical_clone_v1(value)


def _connect(path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    if path.is_symlink() or not path.is_file():
        raise _error("corpus ledger is absent or not regular")
    uri = f"file:{path.resolve()}?mode={'ro' if readonly else 'rw'}"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    identity = connection.execute("SELECT * FROM run_identity WHERE singleton=1").fetchone()
    if identity is None or identity["format_version"] != FORMAT_VERSION:
        connection.close()
        raise _error("corpus ledger identity drifted")
    return connection


def initialize_gemini_json_first_corpus_ledger_v1(
    path: Path,
    *,
    plan: Mapping[str, Any],
    prompt_variant: str = "simple",
    output_contract_mode: str = "JSON_SCHEMA",
    max_task_attempts: int = 3,
) -> dict[str, Any]:
    """Create one exact ledger atomically and materialize every planned task."""

    checked = validate_gemini_json_first_corpus_plan_v1(dict(plan))
    if prompt_variant not in {"simple", "items", "compact", "balanced"}:
        raise _error("corpus ledger prompt variant is invalid")
    if output_contract_mode not in {"JSON_SCHEMA", "PROMPT_JSON"}:
        raise _error("corpus ledger output contract mode is invalid")
    if type(max_task_attempts) is not int or not 1 <= max_task_attempts <= 10:
        raise _error("corpus ledger retry bound lies outside 1..10")
    destination = path.resolve()
    if destination.exists():
        raise _error("refusing to overwrite corpus ledger")
    destination.parent.mkdir(parents=True, exist_ok=True)
    plan_bytes = canonical_json_bytes_v1(checked)
    material = {
        "corpus_plan_id": checked["corpus_plan_id"],
        "corpus_plan_sha256": sha256(plan_bytes).hexdigest(),
        "format_version": FORMAT_VERSION,
        "max_task_attempts": max_task_attempts,
        "output_contract_mode": output_contract_mode,
        "prompt_variant": prompt_variant,
    }
    run_id = "gjfpcrunv1:" + canonical_json_sha256_v1(material)
    descriptor, stage_name = tempfile.mkstemp(
        prefix=destination.name + ".stage-", suffix=".sqlite3", dir=destination.parent
    )
    os.close(descriptor)
    stage = Path(stage_name)
    try:
        with sqlite3.connect(stage) as connection:
            connection.executescript(_SCHEMA)
            connection.execute(
                "INSERT INTO run_identity VALUES (1,?,?,?,?,?,?,?)",
                (
                    FORMAT_VERSION,
                    run_id,
                    checked["corpus_plan_id"],
                    material["corpus_plan_sha256"],
                    prompt_variant,
                    output_contract_mode,
                    max_task_attempts,
                ),
            )
            for planned in checked["documents"]:
                document = planned["document"]
                for task in planned["tasks"]:
                    suffix = task["task_id"].split(":", 1)[1]
                    artifact = f"tasks/{suffix[:2]}/{suffix}"
                    connection.execute(
                        "INSERT INTO task VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            task["task_id"],
                            planned["document_plan_id"],
                            document["relative_path"],
                            document["source_sha256"],
                            document["source_size_bytes"],
                            document["page_count"],
                            task["route"],
                            task["task_kind"],
                            task["first_physical_page"],
                            task["last_physical_page"],
                            artifact,
                            "PENDING",
                            0,
                            None,
                            None,
                        ),
                    )
            connection.commit()
        os.chmod(stage, 0o600)
        os.replace(stage, destination)
    finally:
        stage.unlink(missing_ok=True)
    return corpus_ledger_summary_v1(destination)


def corpus_ledger_summary_v1(path: Path) -> dict[str, Any]:
    """Return deterministic progress counts and exact page/task denominators."""

    with _connect(path, readonly=True) as connection:
        identity = dict(connection.execute("SELECT * FROM run_identity").fetchone())
        counts = connection.execute(
            "SELECT state, route, COUNT(*) AS tasks, "
            "SUM(last_physical_page-first_physical_page+1) AS pages "
            "FROM task GROUP BY state, route ORDER BY state, route"
        ).fetchall()
        total = connection.execute(
            "SELECT COUNT(*) AS tasks, "
            "SUM(last_physical_page-first_physical_page+1) AS pages, "
            "COUNT(DISTINCT document_plan_id) AS documents FROM task"
        ).fetchone()
    return {
        "corpus_plan_id": identity["corpus_plan_id"],
        "corpus_run_id": identity["corpus_run_id"],
        "documents": total["documents"],
        "max_task_attempts": identity["max_task_attempts"],
        "output_contract_mode": identity["output_contract_mode"],
        "progress": [dict(row) for row in counts],
        "prompt_variant": identity["prompt_variant"],
        "total_pages": total["pages"],
        "total_tasks": total["tasks"],
    }


def list_corpus_tasks_v1(
    path: Path,
    *,
    states: Sequence[str] | None = None,
    route: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """List source-ordered tasks for a scheduler without changing state."""

    selected_states = list(states) if states is not None else sorted(TASK_STATES)
    if not selected_states or any(state not in TASK_STATES for state in selected_states):
        raise _error("task state filter is invalid")
    if route is not None and route not in {GOOGLE_ROUTE, OPENROUTER_ROUTE}:
        raise _error("task route filter is invalid")
    if limit is not None and (type(limit) is not int or limit <= 0):
        raise _error("task result limit must be positive")
    placeholders = ",".join("?" for _ in selected_states)
    query = f"SELECT * FROM task WHERE state IN ({placeholders})"
    parameters: list[Any] = list(selected_states)
    if route is not None:
        query += " AND route=?"
        parameters.append(route)
    query += " ORDER BY relative_path, first_physical_page, task_id"
    if limit is not None:
        query += " LIMIT ?"
        parameters.append(limit)
    with _connect(path, readonly=True) as connection:
        rows = connection.execute(query, parameters).fetchall()
    return [dict(row) for row in rows]


def transition_corpus_task_v1(
    path: Path,
    *,
    task_id: str,
    expected_state: str,
    next_state: str,
    receipt: Mapping[str, Any],
    provider_job_ref: str | None = None,
) -> dict[str, Any]:
    """Append one exact state transition, enforcing retry and transition bounds."""

    if expected_state not in TASK_STATES or next_state not in _TRANSITIONS[expected_state]:
        raise _error("corpus task state transition is invalid")
    if type(receipt) is not dict or not receipt:
        raise _error("corpus task transition receipt is empty")
    receipt_bytes = canonical_json_bytes_v1(dict(receipt))
    if provider_job_ref is not None and (type(provider_job_ref) is not str or not provider_job_ref):
        raise _error("provider job reference is invalid")
    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        identity = connection.execute("SELECT * FROM run_identity WHERE singleton=1").fetchone()
        row = connection.execute("SELECT * FROM task WHERE task_id=?", (task_id,)).fetchone()
        if row is None or row["state"] != expected_state:
            raise _error("corpus task current state differs from expected state")
        starts_attempt = expected_state in {"PENDING", "NEEDS_RETRY"} and next_state in {
            "SUBMITTED",
            "RUNNING",
        }
        attempt_count = row["attempt_count"] + (1 if starts_attempt else 0)
        if attempt_count > identity["max_task_attempts"]:
            raise _error("corpus task retry bound is exhausted")
        event_ordinal = connection.execute(
            "SELECT COUNT(*)+1 FROM task_event WHERE task_id=?", (task_id,)
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO task_event VALUES (?,?,?,?,?)",
            (task_id, event_ordinal, expected_state, next_state, receipt_bytes),
        )
        connection.execute(
            "UPDATE task SET state=?, attempt_count=?, provider_job_ref=COALESCE(?,provider_job_ref), "
            "last_receipt_json=? WHERE task_id=?",
            (next_state, attempt_count, provider_job_ref, receipt_bytes, task_id),
        )
        connection.commit()
        updated = connection.execute("SELECT * FROM task WHERE task_id=?", (task_id,)).fetchone()
    return dict(updated)


def claim_pending_openrouter_corpus_task_for_agy_v1(
    path: Path,
    *,
    task_id: str | None = None,
) -> dict[str, Any]:
    """Atomically reserve one pending OpenRouter-planned document for Agy.

    ``SUBMITTED`` is deliberately used as the external-worker lease state.  The
    ordinary OpenRouter scheduler only executes ``PENDING``, ``RUNNING`` and
    ``NEEDS_RETRY`` tasks, so it cannot send the same document after this
    transaction commits.  With no explicit task ID we take the greatest task
    ID, while the ordinary scheduler takes the least; this also prevents a
    stale pre-claim scheduler snapshot from selecting the same document.
    """

    if task_id is not None and (type(task_id) is not str or not task_id.startswith("gjfptaskv1:")):
        raise _error("Agy corpus task identity is invalid")
    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        identity = connection.execute("SELECT * FROM run_identity WHERE singleton=1").fetchone()
        if task_id is None:
            row = connection.execute(
                "SELECT * FROM task WHERE route=? AND state='PENDING' "
                "ORDER BY task_id DESC LIMIT 1",
                (OPENROUTER_ROUTE,),
            ).fetchone()
        else:
            row = connection.execute(
                "SELECT * FROM task WHERE task_id=? AND route=? AND state='PENDING'",
                (task_id, OPENROUTER_ROUTE),
            ).fetchone()
        if row is None:
            raise _error("no pending OpenRouter corpus task is available for Agy")
        attempt_count = row["attempt_count"] + 1
        if attempt_count > identity["max_task_attempts"]:
            raise _error("Agy corpus task retry bound is exhausted")
        claim_material = {
            "corpus_run_id": identity["corpus_run_id"],
            "format_version": "GEMINI_JSON_FIRST_AGY_TASK_CLAIM_V1",
            "source_sha256": row["source_sha256"],
            "task_id": row["task_id"],
        }
        provider_job_ref = AGY_PROVIDER_JOB_PREFIX + canonical_json_sha256_v1(claim_material)
        receipt = {
            **claim_material,
            "execution_provider": "AGY_CLI",
            "initial_effort": "low",
            "provider_job_ref": provider_job_ref,
        }
        receipt_bytes = canonical_json_bytes_v1(receipt)
        event_ordinal = connection.execute(
            "SELECT COUNT(*)+1 FROM task_event WHERE task_id=?", (row["task_id"],)
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO task_event VALUES (?,?,?,?,?)",
            (row["task_id"], event_ordinal, "PENDING", "SUBMITTED", receipt_bytes),
        )
        connection.execute(
            "UPDATE task SET state='SUBMITTED',attempt_count=?,provider_job_ref=?,"
            "last_receipt_json=? WHERE task_id=?",
            (attempt_count, provider_job_ref, receipt_bytes, row["task_id"]),
        )
        connection.commit()
        updated = connection.execute(
            "SELECT * FROM task WHERE task_id=?", (row["task_id"],)
        ).fetchone()
    return dict(updated)


def _checked_source_bound_store_frontier_v1(
    value: Mapping[str, Any],
    *,
    row: sqlite3.Row,
) -> tuple[list[int], list[int], str]:
    frontier = canonical_clone_v1(dict(value))
    required_fields = {
        "failed_pages",
        "format_version",
        "semantic_failure_artifact_pages",
        "source_logical_name",
        "source_sha256",
        "stored_pages",
    }
    expected_pages = list(range(row["first_physical_page"], row["last_physical_page"] + 1))
    failed_pages = frontier.get("failed_pages")
    stored_pages = frontier.get("stored_pages")
    semantic_pages = frontier.get("semantic_failure_artifact_pages")
    if (
        set(frontier) != required_fields
        or frontier.get("format_version") != "GEMINI_JSON_FIRST_SOURCE_BOUND_STORE_FRONTIER_V1"
        or frontier.get("source_sha256") != row["source_sha256"]
        or frontier.get("source_logical_name") != row["relative_path"]
        or type(failed_pages) is not list
        or not failed_pages
        or failed_pages != sorted(set(failed_pages))
        or type(stored_pages) is not list
        or stored_pages != sorted(set(stored_pages))
        or type(semantic_pages) is not list
        or semantic_pages != sorted(set(semantic_pages))
        or not set(semantic_pages).issubset(failed_pages)
        or set(failed_pages) & set(stored_pages)
        or sorted(set(failed_pages) | set(stored_pages)) != expected_pages
    ):
        raise _error("Agy source-bound store frontier is invalid")
    return failed_pages, semantic_pages, canonical_json_sha256_v1(frontier)


def claim_failed_openrouter_provider_pages_for_agy_v1(
    path: Path,
    *,
    task_id: str | None = None,
    source_bound_store_frontier: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Atomically lease one provider-only terminal page frontier to Agy.

    The ordinary retry budget is already exhausted at this boundary, so this
    lease does not increment ``attempt_count``.  Semantic, recitation, source,
    and otherwise unauthenticated failures remain outside the Agy frontier.
    """

    if task_id is not None and (type(task_id) is not str or not task_id.startswith("gjfptaskv1:")):
        raise _error("Agy terminal-repair task identity is invalid")
    if source_bound_store_frontier is not None and task_id is None:
        raise _error("Agy source-bound repair requires one exact task ID")
    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        identity = connection.execute("SELECT * FROM run_identity WHERE singleton=1").fetchone()
        if task_id is None:
            rows = list(
                connection.execute(
                    "SELECT * FROM task WHERE route=? AND state='FAILED' "
                    "ORDER BY relative_path DESC,task_id DESC",
                    (OPENROUTER_ROUTE,),
                )
            )
        else:
            row = connection.execute(
                "SELECT * FROM task WHERE task_id=? AND route=? AND state='FAILED'",
                (task_id, OPENROUTER_ROUTE),
            ).fetchone()
            rows = [] if row is None else [row]
        selected: tuple[sqlite3.Row, dict[str, Any], list[int], str | None] | None = None
        for row in rows:
            try:
                current = json.loads(row["last_receipt_json"])
            except (TypeError, json.JSONDecodeError, UnicodeDecodeError):
                continue
            if (
                type(current) is dict
                and current.get("disposition") == "AGY_TERMINAL_PROVIDER_REPAIR_FAILED"
            ):
                continue
            try:
                frontier = _openrouter_failed_task_repair_frontier_v1(connection, row=row)
            except GeminiJsonFirstCorpusLedgerV1Error:
                continue
            claimed_pages = frontier["failed_pages"]
            source_frontier_sha256 = None
            if source_bound_store_frontier is not None:
                claimed_pages, _artifact_semantic, source_frontier_sha256 = (
                    _checked_source_bound_store_frontier_v1(
                        source_bound_store_frontier,
                        row=row,
                    )
                )
                if not set(claimed_pages).issubset(frontier["failed_pages"]):
                    continue
            if any(
                set(frontier.get(field, [])) & set(claimed_pages)
                for field in (
                    "recitation_failed_pages",
                    "semantic_failed_pages",
                    "unresolved_pages",
                )
            ):
                continue
            selected = row, frontier, claimed_pages, source_frontier_sha256
            break
        if selected is None:
            raise _error("no authenticated provider-only failed task is available for Agy")
        row, frontier, claimed_pages, source_frontier_sha256 = selected
        prior_failed_receipt_sha256 = sha256(row["last_receipt_json"]).hexdigest()
        claim_material = {
            "corpus_run_id": identity["corpus_run_id"],
            "failed_pages": claimed_pages,
            "format_version": "GEMINI_JSON_FIRST_AGY_TERMINAL_PROVIDER_REPAIR_CLAIM_V1",
            "prior_failed_receipt_sha256": prior_failed_receipt_sha256,
            "source_sha256": row["source_sha256"],
            "task_id": row["task_id"],
        }
        if source_frontier_sha256 is not None:
            claim_material = {
                **claim_material,
                "authenticated_failed_pages": frontier["failed_pages"],
                "frontier_kind": "AUTHENTICATED_FAILURE_STORE_MISSING_INTERSECTION",
                "frontier_sha256": source_frontier_sha256,
            }
        provider_job_ref = AGY_PROVIDER_JOB_PREFIX + canonical_json_sha256_v1(claim_material)
        receipt = {
            **claim_material,
            "execution_provider": "AGY_CLI",
            "initial_effort": "low",
            "provider_job_ref": provider_job_ref,
        }
        receipt_bytes = canonical_json_bytes_v1(receipt)
        event_ordinal = connection.execute(
            "SELECT COUNT(*)+1 FROM task_event WHERE task_id=?", (row["task_id"],)
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO task_event VALUES (?,?,?,?,?)",
            (row["task_id"], event_ordinal, "FAILED", "SUBMITTED", receipt_bytes),
        )
        connection.execute(
            "UPDATE task SET state='SUBMITTED',provider_job_ref=?,last_receipt_json=? "
            "WHERE task_id=?",
            (provider_job_ref, receipt_bytes, row["task_id"]),
        )
        connection.commit()
        updated = connection.execute(
            "SELECT * FROM task WHERE task_id=?", (row["task_id"],)
        ).fetchone()
    return dict(updated)


def claim_legacy_failed_openrouter_provider_pages_for_agy_v1(
    path: Path,
    *,
    task_id: str,
    source_bound_store_frontier: Mapping[str, Any],
) -> dict[str, Any]:
    """Lease store-missing pages left by one strict legacy wrapper crash.

    Early wrappers sometimes retained only a local subprocess failure after
    successful pages had already reached the authenticated store.  The caller
    must hold the task execution lock while it derives this exact source-bound
    partition.  Pages with any semantic-failure artifact are deliberately
    rejected; Agy receives only the provider-only complement.
    """

    if type(task_id) is not str or not task_id.startswith("gjfptaskv1:"):
        raise _error("Agy legacy terminal-repair task identity is invalid")
    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        identity = connection.execute("SELECT * FROM run_identity WHERE singleton=1").fetchone()
        row = connection.execute(
            "SELECT * FROM task WHERE task_id=? AND route=? AND state='FAILED'",
            (task_id, OPENROUTER_ROUTE),
        ).fetchone()
        if row is None:
            raise _error("Agy legacy terminal repair requires one failed OpenRouter task")
        failed_pages, semantic_pages, frontier_sha = _checked_source_bound_store_frontier_v1(
            source_bound_store_frontier,
            row=row,
        )
        if semantic_pages:
            raise _error("Agy legacy source-bound frontier contains semantic failures")
        prior_bytes = row["last_receipt_json"]
        try:
            prior = json.loads(prior_bytes)
        except (TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise _error("Agy legacy subprocess failure receipt is invalid") from exc
        failure_fields = {
            "disposition",
            "provider_returncode",
            "provider_stderr_bytes",
            "provider_stderr_sha256",
            "provider_stdout_bytes",
            "provider_stdout_sha256",
            "retry_allowed",
        }
        if (
            row["attempt_count"] != identity["max_task_attempts"]
            or type(prior) is not dict
            or set(prior) != failure_fields
            or prior["disposition"] != "OPENROUTER_PROVIDER_SUBPROCESS_FAILURE"
            or type(prior["provider_returncode"]) is not int
            or prior["provider_returncode"] != 1
            or type(prior["provider_stderr_bytes"]) is not int
            or prior["provider_stderr_bytes"] <= 0
            or type(prior["provider_stdout_bytes"]) is not int
            or prior["provider_stdout_bytes"] != 0
            or prior["provider_stdout_sha256"] != sha256(b"").hexdigest()
            or prior["retry_allowed"] is not False
            or any(
                type(prior[field]) is not str
                or len(prior[field]) != 64
                or any(character not in "0123456789abcdef" for character in prior[field])
                for field in ("provider_stderr_sha256", "provider_stdout_sha256")
            )
        ):
            raise _error("Agy legacy subprocess failure is not strictly authenticated")
        prior_sha = sha256(prior_bytes).hexdigest()
        claim_material = {
            "corpus_run_id": identity["corpus_run_id"],
            "failed_pages": failed_pages,
            "format_version": "GEMINI_JSON_FIRST_AGY_TERMINAL_PROVIDER_REPAIR_CLAIM_V1",
            "frontier_kind": "LEGACY_SOURCE_BOUND_STORE_MISSING_PROVIDER_ONLY",
            "frontier_sha256": frontier_sha,
            "prior_failed_receipt_sha256": prior_sha,
            "source_sha256": row["source_sha256"],
            "task_id": row["task_id"],
        }
        provider_job_ref = AGY_PROVIDER_JOB_PREFIX + canonical_json_sha256_v1(claim_material)
        receipt = {
            **claim_material,
            "execution_provider": "AGY_CLI",
            "initial_effort": "low",
            "provider_job_ref": provider_job_ref,
        }
        receipt_bytes = canonical_json_bytes_v1(receipt)
        event_ordinal = connection.execute(
            "SELECT COUNT(*)+1 FROM task_event WHERE task_id=?", (row["task_id"],)
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO task_event VALUES (?,?,?,?,?)",
            (row["task_id"], event_ordinal, "FAILED", "SUBMITTED", receipt_bytes),
        )
        connection.execute(
            "UPDATE task SET state='SUBMITTED',provider_job_ref=?,last_receipt_json=? "
            "WHERE task_id=?",
            (provider_job_ref, receipt_bytes, row["task_id"]),
        )
        connection.commit()
        updated = connection.execute(
            "SELECT * FROM task WHERE task_id=?", (row["task_id"],)
        ).fetchone()
    return dict(updated)


def claim_exhausted_openrouter_unaccepted_pages_for_agy_v1(
    path: Path,
    *,
    task_id: str,
    source_bound_store_frontier: Mapping[str, Any],
    exhaustion_evidence: Sequence[Mapping[str, Any]],
    page_evidence: Sequence[Mapping[str, Any]],
    cross_corpus_history_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Lease exact no-JSON pages after bounded Flex repair is exhausted.

    This queue is intentionally separate from provider-only recovery.  Every
    page is bound to its current 300-DPI image and classified from the
    authenticated failed frontier.  Source/render failures are inadmissible.
    """

    if type(task_id) is not str or not task_id.startswith("gjfptaskv1:"):
        raise _error("Agy unaccepted-page task identity is invalid")
    evidence = canonical_clone_v1(list(page_evidence))
    exhausted = canonical_clone_v1(list(exhaustion_evidence))
    cross_history = (
        canonical_clone_v1(dict(cross_corpus_history_evidence))
        if cross_corpus_history_evidence is not None
        else None
    )
    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        identity = connection.execute("SELECT * FROM run_identity WHERE singleton=1").fetchone()
        row = connection.execute(
            "SELECT * FROM task WHERE task_id=? AND route=? AND state='FAILED'",
            (task_id, OPENROUTER_ROUTE),
        ).fetchone()
        if row is None:
            raise _error("Agy unaccepted-page repair requires one failed OpenRouter task")
        if row["attempt_count"] != identity["max_task_attempts"]:
            raise _error("Agy unaccepted-page repair requires an exhausted task")
        missing_pages, _artifact_semantic, frontier_sha = _checked_source_bound_store_frontier_v1(
            source_bound_store_frontier,
            row=row,
        )
        prior_bytes = row["last_receipt_json"]
        try:
            prior = json.loads(prior_bytes)
        except (TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise _error("Agy unaccepted-page prior receipt is invalid") from exc
        if type(prior) is dict and prior.get("disposition") in {
            "AGY_EXHAUSTED_UNACCEPTED_REPAIR_FAILED",
            "AGY_TERMINAL_PROVIDER_REPAIR_FAILED",
        }:
            raise _error("Agy unaccepted-page repair has already been attempted")
        strict_legacy_fallback = False
        try:
            frontier = _openrouter_failed_task_repair_frontier_v1(connection, row=row)
        except GeminiJsonFirstCorpusLedgerV1Error:
            # Early wrappers could retain only this strict local subprocess
            # failure even though successful pages had already reached the
            # source-bound store.  Two later canonical Flex receipts bind to
            # that exact failure receipt and prove that the remaining pages
            # were rendered and attempted.  Admit only that narrow legacy
            # shape; the caller's source-bound partition remains exact-checked
            # above and its semantic artifacts still control page classes.
            failure_fields = {
                "disposition",
                "provider_returncode",
                "provider_stderr_bytes",
                "provider_stderr_sha256",
                "provider_stdout_bytes",
                "provider_stdout_sha256",
                "retry_allowed",
            }
            if (
                type(prior) is not dict
                or set(prior) != failure_fields
                or prior["disposition"] != "OPENROUTER_PROVIDER_SUBPROCESS_FAILURE"
                or type(prior["provider_returncode"]) is not int
                or prior["provider_returncode"] != 1
                or type(prior["provider_stderr_bytes"]) is not int
                or prior["provider_stderr_bytes"] <= 0
                or type(prior["provider_stdout_bytes"]) is not int
                or prior["provider_stdout_bytes"] != 0
                or prior["provider_stdout_sha256"] != sha256(b"").hexdigest()
                or prior["retry_allowed"] is not False
                or any(
                    type(prior[field]) is not str
                    or len(prior[field]) != 64
                    or any(character not in "0123456789abcdef" for character in prior[field])
                    for field in ("provider_stderr_sha256", "provider_stdout_sha256")
                )
            ):
                raise
            frontier = {
                "failed_pages": missing_pages,
                "recitation_failed_pages": [],
                "semantic_failed_pages": _artifact_semantic,
                "unresolved_pages": [],
            }
            strict_legacy_fallback = True
        if not set(missing_pages).issubset(frontier["failed_pages"]):
            raise _error("Agy unaccepted pages lie outside the authenticated failure frontier")
        source_failed = prior.get("source_failed_pages", []) if type(prior) is dict else []
        if (
            type(source_failed) is not list
            or source_failed != sorted(set(source_failed))
            or set(source_failed) & set(missing_pages)
        ):
            raise _error("Agy unaccepted-page frontier contains a source/render failure")
        if (
            type(evidence) is not list
            or [item.get("physical_page") for item in evidence if type(item) is dict]
            != missing_pages
            or any(
                type(item) is not dict
                or set(item)
                != {
                    "failure_evidence_sha256s",
                    "failure_kind",
                    "image_sha256",
                    "physical_page",
                }
                for item in evidence
            )
        ):
            raise _error("Agy unaccepted-page evidence frontier is invalid")
        prior_sha = sha256(prior_bytes).hexdigest()
        cross_fields = {
            "current_corpus_plan_id",
            "current_corpus_run_id",
            "format_version",
            "historical_corpus_plan_id",
            "historical_corpus_run_id",
            "historical_ledger_sha256",
            "historical_prior_failed_receipt_sha256",
            "historical_task_event_ordinal",
            "historical_task_identity_sha256",
        }
        cross_mode = cross_history is not None
        if cross_mode and (
            not strict_legacy_fallback
            or type(cross_history) is not dict
            or set(cross_history) != cross_fields
            or cross_history.get("format_version")
            != "GEMINI_JSON_FIRST_AGY_CROSS_CORPUS_FLEX_HISTORY_V1"
            or cross_history.get("current_corpus_plan_id") != identity["corpus_plan_id"]
            or cross_history.get("current_corpus_run_id") != identity["corpus_run_id"]
            or cross_history.get("historical_corpus_plan_id") == identity["corpus_plan_id"]
            or cross_history.get("historical_corpus_run_id") == identity["corpus_run_id"]
            or type(cross_history.get("historical_task_event_ordinal")) is not int
            or cross_history["historical_task_event_ordinal"] <= 0
            or any(
                type(cross_history.get(field)) is not str
                or len(cross_history[field]) != 64
                or any(character not in "0123456789abcdef" for character in cross_history[field])
                for field in (
                    "historical_ledger_sha256",
                    "historical_prior_failed_receipt_sha256",
                    "historical_task_identity_sha256",
                )
            )
        ):
            raise _error("Agy unaccepted-page cross-corpus history is invalid")
        exhaustion_prior_sha = (
            cross_history["historical_prior_failed_receipt_sha256"] if cross_mode else prior_sha
        )
        one_attempt_balanced_exhaustion = bool(
            type(exhausted) is list
            and len(exhausted) == 1
            and type(exhausted[0]) is dict
            and exhausted[0].get("exhaustion_kind")
            == "BALANCED_SEMANTIC_RETRY_BLOCKS_SECOND_ATTEMPT"
        )
        if (
            type(exhausted) is not list
            or len(exhausted) not in {1, 2}
            or [item.get("repair_attempt") for item in exhausted if type(item) is dict]
            != ([1] if one_attempt_balanced_exhaustion else [1, 2])
        ):
            raise _error("Agy unaccepted-page exhaustion evidence is invalid")
        for item in exhausted:
            repair_failed = item.get("failed_pages") if type(item) is dict else None
            expected_fields = {
                "disposition",
                "failed_pages",
                "format_version",
                "prior_failed_receipt_sha256",
                "receipt_sha256",
                "repair_attempt",
            }
            if one_attempt_balanced_exhaustion:
                expected_fields.update({"balanced_semantic_failed_pages", "exhaustion_kind"})
            if (
                type(item) is not dict
                or set(item) != expected_fields
                or item["format_version"]
                not in {
                    "GEMINI_JSON_FIRST_OPENROUTER_EXHAUSTED_PAGE_REPAIR_V1",
                    "GEMINI_JSON_FIRST_OPENROUTER_EXHAUSTED_PAGE_REPAIR_V2",
                }
                or item["disposition"] != "NEEDS_REPAIR"
                or item["prior_failed_receipt_sha256"] != exhaustion_prior_sha
                or type(repair_failed) is not list
                or not repair_failed
                or repair_failed != sorted(set(repair_failed))
                or any(
                    type(page) is not int
                    or page < row["first_physical_page"]
                    or page > row["last_physical_page"]
                    for page in repair_failed
                )
                or type(item["receipt_sha256"]) is not str
                or len(item["receipt_sha256"]) != 64
                or any(character not in "0123456789abcdef" for character in item["receipt_sha256"])
            ):
                raise _error("Agy unaccepted-page exhaustion evidence is invalid")
        if one_attempt_balanced_exhaustion:
            balanced_semantic = exhausted[0].get("balanced_semantic_failed_pages")
            if (
                type(balanced_semantic) is not list
                or not balanced_semantic
                or balanced_semantic != sorted(set(balanced_semantic))
                or not set(balanced_semantic).issubset(missing_pages)
                or not set(balanced_semantic).issubset(exhausted[0]["failed_pages"])
            ):
                raise _error("Agy unaccepted-page balanced exhaustion evidence is invalid")
        if not set(missing_pages).issubset(exhausted[-1]["failed_pages"]) or (
            len(exhausted) == 2
            and not set(exhausted[1]["failed_pages"]).issubset(exhausted[0]["failed_pages"])
        ):
            raise _error("Agy unaccepted pages exceed the bounded Flex exhaustion frontier")
        semantic_pages = (
            set(frontier.get("semantic_failed_pages", []))
            | set(frontier.get("unresolved_pages", []))
            | set(_artifact_semantic)
        )
        recitation_pages = set(frontier.get("recitation_failed_pages", []))
        if recitation_pages & set(missing_pages):
            raise _error("Agy unaccepted-page frontier contains a recitation failure")
        for item in evidence:
            page = item["physical_page"]
            expected_kind = (
                "SEMANTIC_NO_ACCEPTED_JSON"
                if page in semantic_pages
                else "PROVIDER_NO_ACCEPTED_JSON"
            )
            digests = item["failure_evidence_sha256s"]
            image_sha256 = item["image_sha256"]
            if (
                item["failure_kind"] != expected_kind
                or type(image_sha256) is not str
                or len(image_sha256) != 64
                or any(character not in "0123456789abcdef" for character in image_sha256)
                or type(digests) is not list
                or not digests
                or digests != sorted(set(digests))
                or prior_sha not in digests
                or (cross_mode and exhaustion_prior_sha not in digests)
                or not {item["receipt_sha256"] for item in exhausted}.issubset(digests)
                or any(
                    type(digest) is not str
                    or len(digest) != 64
                    or any(character not in "0123456789abcdef" for character in digest)
                    for digest in digests
                )
            ):
                raise _error("Agy unaccepted-page evidence does not match its failure class")
        evidence_sha = canonical_json_sha256_v1(evidence)
        claim_material = {
            "corpus_run_id": identity["corpus_run_id"],
            "exhaustion_evidence": exhausted,
            "exhaustion_evidence_sha256": canonical_json_sha256_v1(exhausted),
            "failed_pages": missing_pages,
            "format_version": "GEMINI_JSON_FIRST_AGY_EXHAUSTED_UNACCEPTED_PAGE_CLAIM_V1",
            "frontier_kind": "EXHAUSTED_NO_ACCEPTED_JSON",
            "frontier_sha256": frontier_sha,
            "page_evidence": evidence,
            "page_evidence_sha256": evidence_sha,
            "prior_failed_receipt_sha256": prior_sha,
            "source_sha256": row["source_sha256"],
            "task_id": row["task_id"],
        }
        if cross_mode:
            claim_material.update(
                {
                    "cross_corpus_history_evidence": cross_history,
                    "cross_corpus_history_evidence_sha256": canonical_json_sha256_v1(cross_history),
                }
            )
        provider_job_ref = AGY_PROVIDER_JOB_PREFIX + canonical_json_sha256_v1(claim_material)
        receipt = {
            **claim_material,
            "execution_provider": "AGY_CLI",
            "initial_effort": "low",
            "provider_job_ref": provider_job_ref,
        }
        receipt_bytes = canonical_json_bytes_v1(receipt)
        event_ordinal = connection.execute(
            "SELECT COUNT(*)+1 FROM task_event WHERE task_id=?", (row["task_id"],)
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO task_event VALUES (?,?,?,?,?)",
            (row["task_id"], event_ordinal, "FAILED", "SUBMITTED", receipt_bytes),
        )
        connection.execute(
            "UPDATE task SET state='SUBMITTED',provider_job_ref=?,last_receipt_json=? "
            "WHERE task_id=?",
            (provider_job_ref, receipt_bytes, row["task_id"]),
        )
        connection.commit()
        updated = connection.execute(
            "SELECT * FROM task WHERE task_id=?", (row["task_id"],)
        ).fetchone()
    return dict(updated)


def claim_source_render_repaired_pages_for_agy_v1(
    path: Path,
    *,
    task_id: str,
    source_bound_store_frontier: Mapping[str, Any],
    local_render_repair_evidence: Sequence[Mapping[str, Any]],
    page_evidence: Sequence[Mapping[str, Any]],
    renderer_source_sha256: str,
) -> dict[str, Any]:
    """Lease a one-shot Agy retry after exact local render failures are repaired.

    This is deliberately narrower than ordinary terminal repair.  The prior
    Agy receipt must partition every currently missing page into either a
    provider failure or a source/render failure, and at least one source/render
    failure must exist.  Every repaired source page is bound to a newly
    rendered image and immutable render receipt before the task becomes
    ``SUBMITTED``.
    """

    if type(task_id) is not str or not task_id.startswith("gjfptaskv1:"):
        raise _error("Agy source-render recovery task identity is invalid")
    local_evidence = canonical_clone_v1(list(local_render_repair_evidence))
    evidence = canonical_clone_v1(list(page_evidence))
    if (
        type(renderer_source_sha256) is not str
        or len(renderer_source_sha256) != 64
        or any(character not in "0123456789abcdef" for character in renderer_source_sha256)
    ):
        raise _error("Agy source-render recovery renderer identity is invalid")
    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        identity = connection.execute("SELECT * FROM run_identity WHERE singleton=1").fetchone()
        row = connection.execute(
            "SELECT * FROM task WHERE task_id=? AND route=? AND state='FAILED'",
            (task_id, OPENROUTER_ROUTE),
        ).fetchone()
        if row is None:
            raise _error("Agy source-render recovery requires one failed OpenRouter task")
        missing_pages, artifact_semantic, frontier_sha = _checked_source_bound_store_frontier_v1(
            source_bound_store_frontier,
            row=row,
        )
        if artifact_semantic:
            raise _error("Agy source-render recovery contains a semantic failure")
        prior_bytes = row["last_receipt_json"]
        try:
            prior = json.loads(prior_bytes)
        except (TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise _error("Agy source-render recovery prior receipt is invalid") from exc
        base_failure_authenticated = bool(
            row["attempt_count"] == identity["max_task_attempts"]
            and type(prior) is dict
            and prior.get("disposition") == "AGY_TERMINAL_PROVIDER_REPAIR_FAILED"
            and prior.get("provider_job_ref") == row["provider_job_ref"]
            and type(row["provider_job_ref"]) is str
            and row["provider_job_ref"].startswith(AGY_PROVIDER_JOB_PREFIX)
        )
        ordinary_failure_authenticated = bool(
            base_failure_authenticated
            and prior.get("format_version") == "GEMINI_JSON_FIRST_AGY_DOCUMENT_RUNNER_V1"
            and prior.get("task_id") == row["task_id"]
        )
        local_or_provider_failure_authenticated = False
        if (
            base_failure_authenticated
            and prior.get("format_version")
            == "GEMINI_JSON_FIRST_AGY_TERMINAL_LOCAL_OR_PROVIDER_FAILURE_V1"
        ):
            events = connection.execute(
                "SELECT * FROM task_event WHERE task_id=? ORDER BY event_ordinal DESC LIMIT 2",
                (row["task_id"],),
            ).fetchall()
            try:
                claim_bytes = events[1]["receipt_json"]
                claim = json.loads(claim_bytes)
            except (IndexError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
                claim = None
                claim_bytes = None
            claim_material = (
                {
                    key: value
                    for key, value in claim.items()
                    if key not in {"execution_provider", "initial_effort", "provider_job_ref"}
                }
                if type(claim) is dict
                else None
            )
            accepted_pages = prior.get("accepted_pages")
            request_pages = prior.get("provider_request_pages")
            failed_pages = prior.get("failed_pages")
            source_failed_pages = prior.get("source_failed_pages")
            provider_failed_pages = prior.get("provider_failed_pages")
            strict_page_lists = all(
                type(pages) is list
                and pages == sorted(set(pages))
                and all(
                    type(page) is int
                    and row["first_physical_page"] <= page <= row["last_physical_page"]
                    for page in pages
                )
                for pages in (
                    accepted_pages,
                    request_pages,
                    failed_pages,
                    source_failed_pages,
                    provider_failed_pages,
                )
            )
            local_or_provider_failure_authenticated = bool(
                len(events) == 2
                and events[0]["prior_state"] == "SUBMITTED"
                and events[0]["next_state"] == "FAILED"
                and events[0]["receipt_json"] == prior_bytes
                and events[1]["prior_state"] == "FAILED"
                and events[1]["next_state"] == "SUBMITTED"
                and type(claim_bytes) is bytes
                and sha256(claim_bytes).hexdigest() == prior.get("claim_receipt_sha256")
                and type(claim) is dict
                and claim_bytes == canonical_json_bytes_v1(claim)
                and claim.get("format_version")
                == "GEMINI_JSON_FIRST_AGY_TERMINAL_PROVIDER_REPAIR_CLAIM_V1"
                and claim.get("execution_provider") == "AGY_CLI"
                and claim.get("provider_job_ref") == row["provider_job_ref"]
                and claim.get("source_sha256") == row["source_sha256"]
                and claim.get("task_id") == row["task_id"]
                and row["provider_job_ref"]
                == AGY_PROVIDER_JOB_PREFIX + canonical_json_sha256_v1(claim_material)
                and prior.get("prior_failed_receipt_sha256")
                == claim.get("prior_failed_receipt_sha256")
                and strict_page_lists
                and not set(accepted_pages) & set(failed_pages)
                and sorted(set(accepted_pages) | set(failed_pages)) == claim.get("failed_pages")
                and sorted(set(accepted_pages) | set(provider_failed_pages)) == request_pages
                and not set(source_failed_pages) & set(provider_failed_pages)
                and sorted(set(source_failed_pages) | set(provider_failed_pages)) == failed_pages
            )
        if not (ordinary_failure_authenticated or local_or_provider_failure_authenticated):
            raise _error("Agy source-render recovery prior failure is not authenticated")
        failed_pages = prior.get("failed_pages")
        source_failed = prior.get("source_failed_pages")
        provider_failed = prior.get("provider_failed_pages")
        semantic_failed = prior.get("semantic_failed_pages")
        unresolved = prior.get("unresolved_pages")
        recitation = prior.get("recitation_failed_pages")
        if (
            type(failed_pages) is not list
            or failed_pages != missing_pages
            or type(source_failed) is not list
            or not source_failed
            or source_failed != sorted(set(source_failed))
            or type(provider_failed) is not list
            or provider_failed != sorted(set(provider_failed))
            or type(semantic_failed) is not list
            or semantic_failed
            or type(recitation) is not list
            or recitation
            or type(unresolved) is not list
            or unresolved != source_failed
            or set(source_failed) & set(provider_failed)
            or sorted(set(source_failed) | set(provider_failed)) != missing_pages
        ):
            raise _error("Agy source-render recovery failure partition is invalid")
        if (
            type(local_evidence) is not list
            or [item.get("physical_page") for item in local_evidence if type(item) is dict]
            != source_failed
            or any(
                type(item) is not dict
                or set(item) != {"image_sha256", "physical_page", "render_receipt_sha256"}
                for item in local_evidence
            )
        ):
            raise _error("Agy source-render recovery local evidence frontier is invalid")
        prior_sha = sha256(prior_bytes).hexdigest()
        local_by_page = {item["physical_page"]: item for item in local_evidence}
        for item in local_evidence:
            if any(
                type(item[field]) is not str
                or len(item[field]) != 64
                or any(character not in "0123456789abcdef" for character in item[field])
                for field in ("image_sha256", "render_receipt_sha256")
            ):
                raise _error("Agy source-render recovery local evidence is invalid")
        if (
            type(evidence) is not list
            or [item.get("physical_page") for item in evidence if type(item) is dict]
            != missing_pages
            or any(
                type(item) is not dict
                or set(item)
                != {
                    "failure_evidence_sha256s",
                    "failure_kind",
                    "image_sha256",
                    "physical_page",
                }
                for item in evidence
            )
        ):
            raise _error("Agy source-render recovery page evidence frontier is invalid")
        for item in evidence:
            page = item["physical_page"]
            digests = item["failure_evidence_sha256s"]
            image_sha256 = item["image_sha256"]
            local = local_by_page.get(page)
            expected_kind = (
                "LOCAL_RENDER_REPAIRED" if local is not None else "PROVIDER_NO_ACCEPTED_JSON"
            )
            if (
                item["failure_kind"] != expected_kind
                or type(image_sha256) is not str
                or len(image_sha256) != 64
                or any(character not in "0123456789abcdef" for character in image_sha256)
                or type(digests) is not list
                or not digests
                or digests != sorted(set(digests))
                or prior_sha not in digests
                or any(
                    type(digest) is not str
                    or len(digest) != 64
                    or any(character not in "0123456789abcdef" for character in digest)
                    for digest in digests
                )
                or (local is not None and image_sha256 != local["image_sha256"])
                or (local is not None and local["render_receipt_sha256"] not in digests)
            ):
                raise _error("Agy source-render recovery page evidence is invalid")
        claim_material = {
            "corpus_run_id": identity["corpus_run_id"],
            "failed_pages": missing_pages,
            "format_version": "GEMINI_JSON_FIRST_AGY_SOURCE_RENDER_RECOVERY_CLAIM_V1",
            "frontier_kind": "LOCAL_RENDER_REPAIRED_STORE_MISSING_FRONTIER",
            "frontier_sha256": frontier_sha,
            "local_render_repair_evidence": local_evidence,
            "local_render_repair_evidence_sha256": canonical_json_sha256_v1(local_evidence),
            "page_evidence": evidence,
            "page_evidence_sha256": canonical_json_sha256_v1(evidence),
            "prior_failed_receipt_sha256": prior_sha,
            "renderer_source_sha256": renderer_source_sha256,
            "source_sha256": row["source_sha256"],
            "task_id": row["task_id"],
        }
        provider_job_ref = AGY_PROVIDER_JOB_PREFIX + canonical_json_sha256_v1(claim_material)
        receipt = {
            **claim_material,
            "execution_provider": "AGY_CLI",
            "initial_effort": "low",
            "provider_job_ref": provider_job_ref,
        }
        receipt_bytes = canonical_json_bytes_v1(receipt)
        event_ordinal = connection.execute(
            "SELECT COUNT(*)+1 FROM task_event WHERE task_id=?", (row["task_id"],)
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO task_event VALUES (?,?,?,?,?)",
            (row["task_id"], event_ordinal, "FAILED", "SUBMITTED", receipt_bytes),
        )
        connection.execute(
            "UPDATE task SET state='SUBMITTED',provider_job_ref=?,last_receipt_json=? "
            "WHERE task_id=?",
            (provider_job_ref, receipt_bytes, row["task_id"]),
        )
        connection.commit()
        updated = connection.execute(
            "SELECT * FROM task WHERE task_id=?", (row["task_id"],)
        ).fetchone()
    return dict(updated)


def claim_agy_tool_denied_orientation_repaired_pages_v1(
    path: Path,
    *,
    task_id: str,
    source_bound_store_frontier: Mapping[str, Any],
    orientation_repair_evidence: Sequence[Mapping[str, Any]],
    tool_denial_evidence: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Lease one exact, locally rotated retry after Agy denied its own command tool.

    The retry is one-shot and only follows an authenticated exhausted-page Agy
    claim whose low, medium, and high calls all returned no accepted JSON.  A
    caller must rotate every still-missing image before this transaction and
    bind both the original claimed image and corrected image to immutable
    receipts.  No generic provider failure can enter this lane.
    """

    if type(task_id) is not str or not task_id.startswith("gjfptaskv1:"):
        raise _error("Agy orientation recovery task identity is invalid")
    orientation_evidence = canonical_clone_v1(list(orientation_repair_evidence))
    denial_evidence = canonical_clone_v1(list(tool_denial_evidence))

    def _digest(value: Any) -> bool:
        return bool(
            type(value) is str
            and len(value) == 64
            and all(character in "0123456789abcdef" for character in value)
        )

    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        identity = connection.execute("SELECT * FROM run_identity WHERE singleton=1").fetchone()
        row = connection.execute(
            "SELECT * FROM task WHERE task_id=? AND route=? AND state='FAILED'",
            (task_id, OPENROUTER_ROUTE),
        ).fetchone()
        if row is None:
            raise _error("Agy orientation recovery requires one failed OpenRouter task")
        missing_pages, artifact_semantic, frontier_sha = _checked_source_bound_store_frontier_v1(
            source_bound_store_frontier,
            row=row,
        )
        if artifact_semantic:
            raise _error("Agy orientation recovery contains a semantic failure")
        prior_bytes = row["last_receipt_json"]
        try:
            prior = json.loads(prior_bytes)
        except (TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise _error("Agy orientation recovery prior receipt is invalid") from exc
        events = connection.execute(
            "SELECT * FROM task_event WHERE task_id=? ORDER BY event_ordinal DESC LIMIT 2",
            (row["task_id"],),
        ).fetchall()
        try:
            claim_bytes = events[1]["receipt_json"]
            claim = json.loads(claim_bytes)
        except (IndexError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
            claim = None
            claim_bytes = None
        claim_material = (
            {
                key: value
                for key, value in claim.items()
                if key not in {"execution_provider", "initial_effort", "provider_job_ref"}
            }
            if type(claim) is dict
            else None
        )
        if (
            row["attempt_count"] != identity["max_task_attempts"]
            or type(prior) is not dict
            or prior.get("format_version") != "GEMINI_JSON_FIRST_AGY_DOCUMENT_RUNNER_V1"
            or prior.get("disposition") != "AGY_EXHAUSTED_UNACCEPTED_REPAIR_FAILED"
            or prior.get("task_id") != row["task_id"]
            or prior.get("provider_job_ref") != row["provider_job_ref"]
            or prior.get("failed_pages") != missing_pages
            or prior.get("provider_request_pages") != missing_pages
            or prior.get("provider_failed_pages") != missing_pages
            or prior.get("source_failed_pages") != []
            or prior.get("semantic_failed_pages") != []
            or prior.get("recitation_failed_pages") != []
            or prior.get("unresolved_pages") != []
            or prior.get("effort_counts") != {"high": 0, "low": 0, "medium": 0}
            or len(events) != 2
            or events[0]["prior_state"] != "SUBMITTED"
            or events[0]["next_state"] != "FAILED"
            or events[0]["receipt_json"] != prior_bytes
            or events[1]["prior_state"] != "FAILED"
            or events[1]["next_state"] != "SUBMITTED"
            or type(claim_bytes) is not bytes
            or type(claim) is not dict
            or claim_bytes != canonical_json_bytes_v1(claim)
            or claim.get("format_version")
            != "GEMINI_JSON_FIRST_AGY_EXHAUSTED_UNACCEPTED_PAGE_CLAIM_V1"
            or claim.get("execution_provider") != "AGY_CLI"
            or claim.get("provider_job_ref") != row["provider_job_ref"]
            or claim.get("source_sha256") != row["source_sha256"]
            or claim.get("task_id") != row["task_id"]
            or claim.get("failed_pages") != missing_pages
            or row["provider_job_ref"]
            != AGY_PROVIDER_JOB_PREFIX + canonical_json_sha256_v1(claim_material)
        ):
            raise _error("Agy orientation recovery prior tool denial is not authenticated")
        claimed_page_evidence = claim.get("page_evidence")
        if (
            type(claimed_page_evidence) is not list
            or [item.get("physical_page") for item in claimed_page_evidence if type(item) is dict]
            != missing_pages
            or claim.get("page_evidence_sha256") != canonical_json_sha256_v1(claimed_page_evidence)
        ):
            raise _error("Agy orientation recovery prior image claim is invalid")
        claimed_images = {
            item["physical_page"]: item.get("image_sha256") for item in claimed_page_evidence
        }
        if (
            type(orientation_evidence) is not list
            or [item.get("physical_page") for item in orientation_evidence if type(item) is dict]
            != missing_pages
            or any(
                type(item) is not dict
                or set(item)
                != {
                    "clockwise_degrees",
                    "corrected_image_sha256",
                    "orientation_receipt_sha256",
                    "original_image_sha256",
                    "physical_page",
                }
                or item["clockwise_degrees"] not in {90, 270}
                or not _digest(item["original_image_sha256"])
                or not _digest(item["corrected_image_sha256"])
                or not _digest(item["orientation_receipt_sha256"])
                or item["original_image_sha256"] != claimed_images.get(item["physical_page"])
                or item["corrected_image_sha256"] == item["original_image_sha256"]
                for item in orientation_evidence
            )
        ):
            raise _error("Agy orientation recovery image evidence is invalid")
        expected_denial_axis = [
            (page, effort) for page in missing_pages for effort in ("low", "medium", "high")
        ]
        if (
            type(denial_evidence) is not list
            or [
                (item.get("physical_page"), item.get("effort"))
                for item in denial_evidence
                if type(item) is dict
            ]
            != expected_denial_axis
            or any(
                type(item) is not dict
                or set(item)
                != {
                    "effort",
                    "failure_sha256",
                    "invocation_sha256",
                    "physical_page",
                    "response_sha256",
                    "stderr_sha256",
                }
                or any(
                    not _digest(item[field])
                    for field in (
                        "failure_sha256",
                        "invocation_sha256",
                        "response_sha256",
                        "stderr_sha256",
                    )
                )
                for item in denial_evidence
            )
        ):
            raise _error("Agy orientation recovery tool-denial evidence is invalid")
        corrected_page_evidence = [
            {
                "image_sha256": item["corrected_image_sha256"],
                "physical_page": item["physical_page"],
            }
            for item in orientation_evidence
        ]
        claim_material = {
            "corpus_run_id": identity["corpus_run_id"],
            "failed_pages": missing_pages,
            "format_version": "GEMINI_JSON_FIRST_AGY_TOOL_DENIED_ORIENTATION_RECOVERY_CLAIM_V1",
            "frontier_kind": "TOOL_DENIED_SIDEWAYS_IMAGE_LOCAL_ORIENTATION_REPAIRED",
            "frontier_sha256": frontier_sha,
            "orientation_repair_evidence": orientation_evidence,
            "orientation_repair_evidence_sha256": canonical_json_sha256_v1(orientation_evidence),
            "page_evidence": corrected_page_evidence,
            "page_evidence_sha256": canonical_json_sha256_v1(corrected_page_evidence),
            "prior_failed_receipt_sha256": sha256(prior_bytes).hexdigest(),
            "source_sha256": row["source_sha256"],
            "task_id": row["task_id"],
            "tool_denial_evidence": denial_evidence,
            "tool_denial_evidence_sha256": canonical_json_sha256_v1(denial_evidence),
        }
        provider_job_ref = AGY_PROVIDER_JOB_PREFIX + canonical_json_sha256_v1(claim_material)
        receipt = {
            **claim_material,
            "execution_provider": "AGY_CLI",
            "initial_effort": "low",
            "provider_job_ref": provider_job_ref,
        }
        receipt_bytes = canonical_json_bytes_v1(receipt)
        event_ordinal = connection.execute(
            "SELECT COUNT(*)+1 FROM task_event WHERE task_id=?", (row["task_id"],)
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO task_event VALUES (?,?,?,?,?)",
            (row["task_id"], event_ordinal, "FAILED", "SUBMITTED", receipt_bytes),
        )
        connection.execute(
            "UPDATE task SET state='SUBMITTED',provider_job_ref=?,last_receipt_json=? "
            "WHERE task_id=?",
            (provider_job_ref, receipt_bytes, row["task_id"]),
        )
        connection.commit()
        updated = connection.execute(
            "SELECT * FROM task WHERE task_id=?", (row["task_id"],)
        ).fetchone()
    return dict(updated)


def claim_agy_schema_alignment_recovery_pages_v1(
    path: Path,
    *,
    task_id: str,
    source_bound_store_frontier: Mapping[str, Any],
    page_evidence: Sequence[Mapping[str, Any]],
    prior_attempt_evidence: Sequence[Mapping[str, Any]],
    repair_instruction_sha256: str,
    repair_registry_entry_sha256: str,
) -> dict[str, Any]:
    """Lease one exact retry for an authenticated row/column alignment failure.

    This is deliberately narrower than a generic Agy retry.  It accepts only a
    one-page, exhausted Agy claim whose low-effort response failed the semantic
    row/column alignment check and whose medium/high attempts were command-tool
    denials.  The unchanged page image and an explicit per-source repair hint
    are both bound into the new one-shot claim.
    """

    if type(task_id) is not str or not task_id.startswith("gjfptaskv1:"):
        raise _error("Agy schema-alignment recovery task identity is invalid")
    evidence = canonical_clone_v1(list(page_evidence))
    attempts = canonical_clone_v1(list(prior_attempt_evidence))

    def _digest(value: Any) -> bool:
        return bool(
            type(value) is str
            and len(value) == 64
            and all(character in "0123456789abcdef" for character in value)
        )

    if not _digest(repair_instruction_sha256) or not _digest(repair_registry_entry_sha256):
        raise _error("Agy schema-alignment recovery registry evidence is invalid")
    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        identity = connection.execute("SELECT * FROM run_identity WHERE singleton=1").fetchone()
        row = connection.execute(
            "SELECT * FROM task WHERE task_id=? AND route=? AND state='FAILED'",
            (task_id, OPENROUTER_ROUTE),
        ).fetchone()
        if row is None:
            raise _error("Agy schema-alignment recovery requires one failed OpenRouter task")
        missing_pages, artifact_semantic, frontier_sha = _checked_source_bound_store_frontier_v1(
            source_bound_store_frontier,
            row=row,
        )
        if len(missing_pages) != 1 or artifact_semantic != missing_pages:
            raise _error("Agy schema-alignment recovery requires one exact semantic page")
        prior_bytes = row["last_receipt_json"]
        try:
            prior = json.loads(prior_bytes)
        except (TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise _error("Agy schema-alignment recovery prior receipt is invalid") from exc
        events = connection.execute(
            "SELECT * FROM task_event WHERE task_id=? ORDER BY event_ordinal DESC LIMIT 2",
            (row["task_id"],),
        ).fetchall()
        try:
            prior_claim_bytes = events[1]["receipt_json"]
            prior_claim = json.loads(prior_claim_bytes)
        except (IndexError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
            prior_claim_bytes = None
            prior_claim = None
        prior_claim_material = (
            {
                key: value
                for key, value in prior_claim.items()
                if key not in {"execution_provider", "initial_effort", "provider_job_ref"}
            }
            if type(prior_claim) is dict
            else None
        )
        if (
            row["attempt_count"] != identity["max_task_attempts"]
            or type(prior) is not dict
            or prior.get("format_version") != "GEMINI_JSON_FIRST_AGY_DOCUMENT_RUNNER_V1"
            or prior.get("disposition") != "AGY_EXHAUSTED_UNACCEPTED_REPAIR_FAILED"
            or prior.get("task_id") != row["task_id"]
            or prior.get("provider_job_ref") != row["provider_job_ref"]
            or prior.get("failed_pages") != missing_pages
            or prior.get("provider_request_pages") != missing_pages
            or prior.get("provider_failed_pages") != missing_pages
            or prior.get("source_failed_pages") != []
            or prior.get("semantic_failed_pages") != []
            or prior.get("recitation_failed_pages") != []
            or prior.get("unresolved_pages") != []
            or prior.get("effort_counts") != {"high": 0, "low": 0, "medium": 0}
            or len(events) != 2
            or events[0]["prior_state"] != "SUBMITTED"
            or events[0]["next_state"] != "FAILED"
            or events[0]["receipt_json"] != prior_bytes
            or events[1]["prior_state"] != "FAILED"
            or events[1]["next_state"] != "SUBMITTED"
            or type(prior_claim_bytes) is not bytes
            or type(prior_claim) is not dict
            or prior_claim_bytes != canonical_json_bytes_v1(prior_claim)
            or prior_claim.get("format_version")
            != "GEMINI_JSON_FIRST_AGY_EXHAUSTED_UNACCEPTED_PAGE_CLAIM_V1"
            or prior_claim.get("execution_provider") != "AGY_CLI"
            or prior_claim.get("provider_job_ref") != row["provider_job_ref"]
            or prior_claim.get("source_sha256") != row["source_sha256"]
            or prior_claim.get("task_id") != row["task_id"]
            or prior_claim.get("failed_pages") != missing_pages
            or row["provider_job_ref"]
            != AGY_PROVIDER_JOB_PREFIX + canonical_json_sha256_v1(prior_claim_material)
        ):
            raise _error("Agy schema-alignment recovery prior failure is not authenticated")
        claimed_page_evidence = prior_claim.get("page_evidence")
        claimed_image = (
            claimed_page_evidence[0].get("image_sha256")
            if type(claimed_page_evidence) is list
            and len(claimed_page_evidence) == 1
            and type(claimed_page_evidence[0]) is dict
            else None
        )
        if (
            type(evidence) is not list
            or len(evidence) != 1
            or type(evidence[0]) is not dict
            or set(evidence[0]) != {"image_sha256", "physical_page"}
            or evidence[0].get("physical_page") != missing_pages[0]
            or not _digest(evidence[0].get("image_sha256"))
            or evidence[0].get("image_sha256") != claimed_image
        ):
            raise _error("Agy schema-alignment recovery image evidence is invalid")
        expected_axis = [(missing_pages[0], effort) for effort in ("low", "medium", "high")]
        if (
            type(attempts) is not list
            or [
                (item.get("physical_page"), item.get("effort"))
                for item in attempts
                if type(item) is dict
            ]
            != expected_axis
            or [item.get("failure_kind") for item in attempts if type(item) is dict]
            != ["ROW_COLUMN_ALIGNMENT", "COMMAND_TOOL_DENIED", "COMMAND_TOOL_DENIED"]
            or any(
                type(item) is not dict
                or set(item)
                != {
                    "effort",
                    "failure_kind",
                    "failure_sha256",
                    "invocation_sha256",
                    "physical_page",
                    "response_sha256",
                    "stderr_sha256",
                }
                or any(
                    not _digest(item[field])
                    for field in (
                        "failure_sha256",
                        "invocation_sha256",
                        "response_sha256",
                        "stderr_sha256",
                    )
                )
                for item in attempts
            )
        ):
            raise _error("Agy schema-alignment recovery prior-attempt evidence is invalid")
        claim_material = {
            "corpus_run_id": identity["corpus_run_id"],
            "failed_pages": missing_pages,
            "format_version": "GEMINI_JSON_FIRST_AGY_SCHEMA_ALIGNMENT_RECOVERY_CLAIM_V1",
            "frontier_kind": "EXACT_ROW_COLUMN_ALIGNMENT_PROMPT_REPAIR",
            "frontier_sha256": frontier_sha,
            "page_evidence": evidence,
            "page_evidence_sha256": canonical_json_sha256_v1(evidence),
            "prior_attempt_evidence": attempts,
            "prior_attempt_evidence_sha256": canonical_json_sha256_v1(attempts),
            "prior_failed_receipt_sha256": sha256(prior_bytes).hexdigest(),
            "repair_instruction_sha256": repair_instruction_sha256,
            "repair_registry_entry_sha256": repair_registry_entry_sha256,
            "source_sha256": row["source_sha256"],
            "task_id": row["task_id"],
        }
        provider_job_ref = AGY_PROVIDER_JOB_PREFIX + canonical_json_sha256_v1(claim_material)
        receipt = {
            **claim_material,
            "execution_provider": "AGY_CLI",
            "initial_effort": "low",
            "provider_job_ref": provider_job_ref,
        }
        receipt_bytes = canonical_json_bytes_v1(receipt)
        event_ordinal = connection.execute(
            "SELECT COUNT(*)+1 FROM task_event WHERE task_id=?", (row["task_id"],)
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO task_event VALUES (?,?,?,?,?)",
            (row["task_id"], event_ordinal, "FAILED", "SUBMITTED", receipt_bytes),
        )
        connection.execute(
            "UPDATE task SET state='SUBMITTED',provider_job_ref=?,last_receipt_json=? "
            "WHERE task_id=?",
            (provider_job_ref, receipt_bytes, row["task_id"]),
        )
        connection.commit()
        updated = connection.execute(
            "SELECT * FROM task WHERE task_id=?", (row["task_id"],)
        ).fetchone()
    return dict(updated)


def claim_pending_openrouter_corpus_task_for_ckey_v1(
    path: Path,
    *,
    task_id: str | None = None,
) -> dict[str, Any]:
    """Atomically reserve one pending OpenRouter-planned document for CKey.

    CKey and Agy deliberately use the same ``SUBMITTED`` lease state.  Their
    claims therefore serialize with the ordinary OpenRouter scheduler and
    with one another; a document can be owned by exactly one provider flow.
    """

    if task_id is not None and (type(task_id) is not str or not task_id.startswith("gjfptaskv1:")):
        raise _error("CKey corpus task identity is invalid")
    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        identity = connection.execute("SELECT * FROM run_identity WHERE singleton=1").fetchone()
        if task_id is None:
            row = connection.execute(
                "SELECT * FROM task WHERE route=? AND state='PENDING' "
                "ORDER BY task_id DESC LIMIT 1",
                (OPENROUTER_ROUTE,),
            ).fetchone()
        else:
            row = connection.execute(
                "SELECT * FROM task WHERE task_id=? AND route=? AND state='PENDING'",
                (task_id, OPENROUTER_ROUTE),
            ).fetchone()
        if row is None:
            raise _error("no pending OpenRouter corpus task is available for CKey")
        attempt_count = row["attempt_count"] + 1
        if attempt_count > identity["max_task_attempts"]:
            raise _error("CKey corpus task retry bound is exhausted")
        claim_material = {
            "corpus_run_id": identity["corpus_run_id"],
            "format_version": "GEMINI_JSON_FIRST_CKEY_TASK_CLAIM_V1",
            "source_sha256": row["source_sha256"],
            "task_id": row["task_id"],
        }
        provider_job_ref = CKEY_PROVIDER_JOB_PREFIX + canonical_json_sha256_v1(claim_material)
        receipt = {
            **claim_material,
            "execution_provider": "CKEY_API",
            "provider_job_ref": provider_job_ref,
        }
        receipt_bytes = canonical_json_bytes_v1(receipt)
        event_ordinal = connection.execute(
            "SELECT COUNT(*)+1 FROM task_event WHERE task_id=?", (row["task_id"],)
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO task_event VALUES (?,?,?,?,?)",
            (row["task_id"], event_ordinal, "PENDING", "SUBMITTED", receipt_bytes),
        )
        connection.execute(
            "UPDATE task SET state='SUBMITTED',attempt_count=?,provider_job_ref=?,"
            "last_receipt_json=? WHERE task_id=?",
            (attempt_count, provider_job_ref, receipt_bytes, row["task_id"]),
        )
        connection.commit()
        updated = connection.execute(
            "SELECT * FROM task WHERE task_id=?", (row["task_id"],)
        ).fetchone()
    return dict(updated)


def seal_agy_corpus_task_v1(
    path: Path,
    *,
    task_id: str,
    provider_job_ref: str,
    document_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Seal one Agy-reserved task only after a complete usable manifest exists."""

    if (
        type(task_id) is not str
        or not task_id.startswith("gjfptaskv1:")
        or type(provider_job_ref) is not str
        or not provider_job_ref.startswith(AGY_PROVIDER_JOB_PREFIX)
        or type(document_manifest) is not dict
    ):
        raise _error("Agy corpus task seal input is invalid")
    document = document_manifest.get("document")
    pages = document_manifest.get("pages")
    manifest_id = document_manifest.get("document_manifest_id")
    status_counts = document_manifest.get("status_counts")
    if (
        type(document) is not dict
        or type(pages) is not list
        or not pages
        or type(manifest_id) is not str
        or not manifest_id.startswith("gfdmv1:manifest:")
        or type(status_counts) is not dict
        or status_counts.get("UNRESOLVED_PAGE", 0) != 0
        or any(type(page) is not dict for page in pages)
    ):
        raise _error("Agy corpus task manifest is incomplete or unresolved")
    receipt = {
        "document_manifest_id": manifest_id,
        "execution_provider": "AGY_CLI",
        "format_version": "GEMINI_JSON_FIRST_AGY_TASK_SUCCESS_V1",
        "page_count": len(pages),
        "provider_job_ref": provider_job_ref,
    }
    with _connect(path, readonly=True) as connection:
        row = connection.execute("SELECT * FROM task WHERE task_id=?", (task_id,)).fetchone()
    expected_pages = (
        list(range(row["first_physical_page"], row["last_physical_page"] + 1))
        if row is not None
        else []
    )
    if (
        row is None
        or row["state"] != "SUBMITTED"
        or row["provider_job_ref"] != provider_job_ref
        or document.get("source_sha256") != row["source_sha256"]
        or document.get("source_logical_name") != row["relative_path"]
        or [page.get("physical_page") for page in pages] != expected_pages
    ):
        raise _error("Agy corpus task manifest differs from its reserved task")
    return transition_corpus_task_v1(
        path,
        task_id=task_id,
        expected_state="SUBMITTED",
        next_state="SUCCEEDED",
        receipt=receipt,
        provider_job_ref=provider_job_ref,
    )


def seal_ckey_corpus_task_v1(
    path: Path,
    *,
    task_id: str,
    provider_job_ref: str,
    document_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Seal one CKey-reserved task only after a complete usable manifest exists."""

    if (
        type(task_id) is not str
        or not task_id.startswith("gjfptaskv1:")
        or type(provider_job_ref) is not str
        or not provider_job_ref.startswith(CKEY_PROVIDER_JOB_PREFIX)
        or type(document_manifest) is not dict
    ):
        raise _error("CKey corpus task seal input is invalid")
    document = document_manifest.get("document")
    pages = document_manifest.get("pages")
    manifest_id = document_manifest.get("document_manifest_id")
    status_counts = document_manifest.get("status_counts")
    if (
        type(document) is not dict
        or type(pages) is not list
        or not pages
        or type(manifest_id) is not str
        or not manifest_id.startswith("gfdmv1:manifest:")
        or type(status_counts) is not dict
        or status_counts.get("UNRESOLVED_PAGE", 0) != 0
        or any(type(page) is not dict for page in pages)
    ):
        raise _error("CKey corpus task manifest is incomplete or unresolved")
    receipt = {
        "document_manifest_id": manifest_id,
        "execution_provider": "CKEY_API",
        "format_version": "GEMINI_JSON_FIRST_CKEY_TASK_SUCCESS_V1",
        "page_count": len(pages),
        "provider_job_ref": provider_job_ref,
    }
    with _connect(path, readonly=True) as connection:
        row = connection.execute("SELECT * FROM task WHERE task_id=?", (task_id,)).fetchone()
    expected_pages = (
        list(range(row["first_physical_page"], row["last_physical_page"] + 1))
        if row is not None
        else []
    )
    if (
        row is None
        or row["state"] != "SUBMITTED"
        or row["provider_job_ref"] != provider_job_ref
        or document.get("source_sha256") != row["source_sha256"]
        or document.get("source_logical_name") != row["relative_path"]
        or [page.get("physical_page") for page in pages] != expected_pages
    ):
        raise _error("CKey corpus task manifest differs from its reserved task")
    return transition_corpus_task_v1(
        path,
        task_id=task_id,
        expected_state="SUBMITTED",
        next_state="SUCCEEDED",
        receipt=receipt,
        provider_job_ref=provider_job_ref,
    )


def requeue_failed_openrouter_corpus_task_v1(
    path: Path,
    *,
    task_id: str,
) -> dict[str, Any]:
    """Authorize one final bounded Flex retry from an exact failed receipt."""

    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        identity = connection.execute("SELECT * FROM run_identity WHERE singleton=1").fetchone()
        row = connection.execute("SELECT * FROM task WHERE task_id=?", (task_id,)).fetchone()
        if row is None or row["state"] != "FAILED" or row["route"] != OPENROUTER_ROUTE:
            raise _error("OpenRouter requeue requires one failed Flex task")
        if row["attempt_count"] >= identity["max_task_attempts"]:
            raise _error("OpenRouter requeue retry bound is exhausted")
        prior_bytes = row["last_receipt_json"]
        try:
            prior = json.loads(prior_bytes)
        except (TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise _error("OpenRouter requeue receipt is invalid") from exc
        failed = prior.get("failed_pages") if type(prior) is dict else None
        semantic = prior.get("semantic_failed_pages", []) if type(prior) is dict else None
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
                type(page) is not int
                or page < row["first_physical_page"]
                or page > row["last_physical_page"]
                for page in failed
            )
        ):
            raise _error("OpenRouter requeue failed-page frontier is invalid")
        receipt = {
            "failed_pages": failed,
            "format_version": "GEMINI_JSON_FIRST_OPENROUTER_FAILED_REQUEUE_V1",
            "prior_failed_receipt_sha256": sha256(prior_bytes).hexdigest(),
            "recitation_failed_pages": recitation,
            "requeue_authorized": True,
            "semantic_failed_pages": semantic,
            "unresolved_pages": unresolved,
        }
        receipt_bytes = canonical_json_bytes_v1(receipt)
        event_ordinal = connection.execute(
            "SELECT COUNT(*)+1 FROM task_event WHERE task_id=?", (task_id,)
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO task_event VALUES (?,?,?,?,?)",
            (task_id, event_ordinal, "FAILED", "NEEDS_RETRY", receipt_bytes),
        )
        connection.execute(
            "UPDATE task SET state='NEEDS_RETRY',provider_job_ref=NULL,last_receipt_json=? "
            "WHERE task_id=?",
            (receipt_bytes, task_id),
        )
        connection.commit()
        updated = connection.execute("SELECT * FROM task WHERE task_id=?", (task_id,)).fetchone()
    return dict(updated)


def _checked_failed_page_frontier_v1(
    receipt: Any,
    *,
    row: sqlite3.Row,
    context: str,
) -> dict[str, Any]:
    if type(receipt) is not dict:
        raise _error(f"{context} receipt is invalid")
    failed = receipt.get("failed_pages")
    semantic = receipt.get("semantic_failed_pages", [])
    unresolved = receipt.get("unresolved_pages", [])
    recitation = receipt.get("recitation_failed_pages", [])
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
            type(page) is not int
            or page < row["first_physical_page"]
            or page > row["last_physical_page"]
            for page in failed
        )
    ):
        raise _error(f"{context} failed-page frontier is invalid")
    return canonical_clone_v1(receipt)


def _openrouter_failed_task_repair_frontier_v1(
    connection: sqlite3.Connection,
    *,
    row: sqlite3.Row,
) -> dict[str, Any]:
    """Resolve an exhausted task's frontier from its authenticated event chain."""

    identity = connection.execute("SELECT * FROM run_identity WHERE singleton=1").fetchone()
    if (
        row["state"] != "FAILED"
        or row["route"] != OPENROUTER_ROUTE
        or type(row["last_receipt_json"]) is not bytes
    ):
        raise _error("OpenRouter repair frontier requires one failed task")
    try:
        current = json.loads(row["last_receipt_json"])
    except (TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise _error("OpenRouter repair frontier receipt is invalid") from exc
    if type(current) is dict and "failed_pages" in current:
        return _checked_failed_page_frontier_v1(
            current,
            row=row,
            context="OpenRouter repair",
        )
    if row["attempt_count"] != identity["max_task_attempts"]:
        raise _error("OpenRouter subprocess repair frontier requires one exhausted task")

    failure_fields = {
        "disposition",
        "provider_returncode",
        "provider_stderr_bytes",
        "provider_stderr_sha256",
        "provider_stdout_bytes",
        "provider_stdout_sha256",
        "retry_allowed",
    }
    if (
        type(current) is not dict
        or set(current) != failure_fields
        or current["disposition"] != "OPENROUTER_PROVIDER_SUBPROCESS_FAILURE"
        or type(current["provider_returncode"]) is not int
        or current["provider_returncode"] != 1
        or type(current["provider_stderr_bytes"]) is not int
        or current["provider_stderr_bytes"] <= 0
        or type(current["provider_stdout_bytes"]) is not int
        or current["provider_stdout_bytes"] != 0
        or current["provider_stdout_sha256"] != sha256(b"").hexdigest()
        or current["retry_allowed"] is not False
        or any(
            type(current[field]) is not str
            or len(current[field]) != 64
            or any(character not in "0123456789abcdef" for character in current[field])
            for field in ("provider_stderr_sha256", "provider_stdout_sha256")
        )
    ):
        raise _error("OpenRouter repair subprocess failure is invalid")

    events = list(
        connection.execute(
            "SELECT * FROM task_event WHERE task_id=? ORDER BY event_ordinal DESC LIMIT 4",
            (row["task_id"],),
        )
    )
    if (
        len(events) != 4
        or (events[0]["prior_state"], events[0]["next_state"]) != ("RUNNING", "FAILED")
        or (events[1]["prior_state"], events[1]["next_state"]) != ("NEEDS_RETRY", "RUNNING")
        or (events[2]["prior_state"], events[2]["next_state"]) != ("FAILED", "NEEDS_RETRY")
        or (events[3]["prior_state"], events[3]["next_state"]) != ("RUNNING", "FAILED")
        or events[0]["receipt_json"] != row["last_receipt_json"]
    ):
        raise _error("OpenRouter repair subprocess event chain is invalid")
    try:
        start = json.loads(events[1]["receipt_json"])
        requeue = json.loads(events[2]["receipt_json"])
    except (TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise _error("OpenRouter repair event receipt is invalid") from exc
    if start != {"document_run_started": True}:
        raise _error("OpenRouter repair retry-start receipt is invalid")
    retry_fields = {
        "failed_pages",
        "format_version",
        "prior_failed_receipt_sha256",
        "recitation_failed_pages",
        "requeue_authorized",
        "semantic_failed_pages",
        "unresolved_pages",
    }
    if (
        type(requeue) is not dict
        or set(requeue) != retry_fields
        or requeue["format_version"] != "GEMINI_JSON_FIRST_OPENROUTER_FAILED_REQUEUE_V1"
        or requeue["requeue_authorized"] is not True
        or requeue["prior_failed_receipt_sha256"] != sha256(events[3]["receipt_json"]).hexdigest()
    ):
        raise _error("OpenRouter repair requeue authority is invalid")
    return _checked_failed_page_frontier_v1(
        requeue,
        row=row,
        context="OpenRouter repair requeue",
    )


def openrouter_failed_task_repair_frontier_v1(
    path: Path,
    *,
    task_id: str,
) -> dict[str, Any]:
    """Return the exact terminal-repair frontier without mutating the ledger."""

    with _connect(path, readonly=True) as connection:
        row = connection.execute("SELECT * FROM task WHERE task_id=?", (task_id,)).fetchone()
        if row is None:
            raise _error("OpenRouter repair task is absent")
        return _openrouter_failed_task_repair_frontier_v1(connection, row=row)


def recover_failed_openrouter_artifact_collision_v1(
    path: Path,
    *,
    task_id: str,
    artifact_root: Path,
) -> dict[str, Any]:
    """Resume one exhausted attempt proven to have failed before provider work.

    Older supervisors reused one immutable adaptive-retry directory for every
    frontier of the same prompt.  When a later attempt changed the frontier,
    the child rejected the pre-existing document contract before submitting a
    request.  This recovery is deliberately specific: it validates the exact
    event sequence and the conflicting immutable contracts, then returns the
    task to RUNNING without consuming another provider attempt.
    """

    if artifact_root.is_symlink() or not artifact_root.is_dir():
        raise _error("OpenRouter artifact-collision recovery root is invalid")
    resolved_artifact_root = artifact_root.resolve()
    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        identity = connection.execute("SELECT * FROM run_identity WHERE singleton=1").fetchone()
        row = connection.execute("SELECT * FROM task WHERE task_id=?", (task_id,)).fetchone()
        if (
            row is None
            or row["state"] != "FAILED"
            or row["route"] != OPENROUTER_ROUTE
            or row["attempt_count"] != identity["max_task_attempts"]
        ):
            raise _error("OpenRouter artifact-collision recovery requires one exhausted task")
        events = list(
            connection.execute(
                "SELECT * FROM task_event WHERE task_id=? ORDER BY event_ordinal DESC LIMIT 4",
                (task_id,),
            )
        )
        if (
            len(events) != 4
            or (events[0]["prior_state"], events[0]["next_state"]) != ("RUNNING", "FAILED")
            or (events[1]["prior_state"], events[1]["next_state"]) != ("NEEDS_RETRY", "RUNNING")
            or (events[2]["prior_state"], events[2]["next_state"]) != ("FAILED", "NEEDS_RETRY")
            or (events[3]["prior_state"], events[3]["next_state"]) != ("RUNNING", "FAILED")
            or events[0]["receipt_json"] != row["last_receipt_json"]
        ):
            raise _error("OpenRouter artifact-collision recovery event chain is invalid")
        try:
            failure = json.loads(row["last_receipt_json"])
            retry = json.loads(events[2]["receipt_json"])
            prior_attempt = json.loads(events[3]["receipt_json"])
        except (TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise _error("OpenRouter artifact-collision recovery receipt is invalid") from exc
        failure_fields = {
            "disposition",
            "provider_returncode",
            "provider_stderr_bytes",
            "provider_stderr_sha256",
            "provider_stdout_bytes",
            "provider_stdout_sha256",
            "retry_allowed",
        }
        if (
            type(failure) is not dict
            or set(failure) != failure_fields
            or failure["disposition"] != "OPENROUTER_PROVIDER_SUBPROCESS_FAILURE"
            or type(failure["provider_returncode"]) is not int
            or failure["provider_returncode"] != 1
            or type(failure["provider_stderr_bytes"]) is not int
            or failure["provider_stderr_bytes"] <= 0
            or type(failure["provider_stdout_bytes"]) is not int
            or failure["provider_stdout_bytes"] != 0
            or failure["provider_stdout_sha256"] != sha256(b"").hexdigest()
            or failure["retry_allowed"] is not False
            or any(
                type(failure[field]) is not str
                or len(failure[field]) != 64
                or any(character not in "0123456789abcdef" for character in failure[field])
                for field in ("provider_stderr_sha256", "provider_stdout_sha256")
            )
        ):
            raise _error("OpenRouter artifact-collision recovery child failure is invalid")
        retry_fields = {
            "failed_pages",
            "format_version",
            "prior_failed_receipt_sha256",
            "recitation_failed_pages",
            "requeue_authorized",
            "semantic_failed_pages",
            "unresolved_pages",
        }
        failed = retry.get("failed_pages") if type(retry) is dict else None
        semantic = retry.get("semantic_failed_pages") if type(retry) is dict else None
        unresolved = retry.get("unresolved_pages") if type(retry) is dict else None
        recitation = retry.get("recitation_failed_pages") if type(retry) is dict else None
        if (
            type(retry) is not dict
            or set(retry) != retry_fields
            or retry["format_version"] != "GEMINI_JSON_FIRST_OPENROUTER_FAILED_REQUEUE_V1"
            or retry["requeue_authorized"] is not True
            or retry["prior_failed_receipt_sha256"] != sha256(events[3]["receipt_json"]).hexdigest()
            or type(failed) is not list
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
                type(page) is not int
                or page < row["first_physical_page"]
                or page > row["last_physical_page"]
                for page in failed
            )
        ):
            raise _error("OpenRouter artifact-collision recovery retry frontier is invalid")

        protected = set(semantic) | set(unresolved)
        prompt_pages: dict[str, list[int]] = {}
        for variant, pages in (
            (
                identity["prompt_variant"],
                sorted(set(failed) - protected - set(recitation)),
            ),
            ("scope", recitation),
            ("items", sorted(protected)),
        ):
            prompt_pages.setdefault(variant, []).extend(pages)
        expected_frontiers = {
            variant: sorted(set(pages)) for variant, pages in prompt_pages.items() if pages
        }
        if not expected_frontiers:
            raise _error("OpenRouter artifact-collision recovery has no retry frontier")

        prior_frontier_items = (
            prior_attempt.get("alternate_prompt_variants") if type(prior_attempt) is dict else None
        )
        if type(prior_frontier_items) is not list or not prior_frontier_items:
            raise _error("OpenRouter prior adaptive-retry frontier is absent")
        legacy_frontiers: dict[str, list[int]] = {}
        for item in prior_frontier_items:
            variant = item.get("prompt_variant") if type(item) is dict else None
            pages = item.get("physical_pages") if type(item) is dict else None
            if (
                type(variant) is not str
                or variant in legacy_frontiers
                or type(pages) is not list
                or not pages
                or pages != sorted(set(pages))
                or any(
                    type(page) is not int
                    or page < row["first_physical_page"]
                    or page > row["last_physical_page"]
                    for page in pages
                )
            ):
                raise _error("OpenRouter prior adaptive-retry frontier is invalid")
            legacy_frontiers[variant] = pages
        if any(variant not in legacy_frontiers for variant in expected_frontiers):
            raise _error("OpenRouter prior adaptive-retry frontier omits a current prompt")

        task_root = resolved_artifact_root / row["artifact_relative_path"]
        try:
            resolved_task_root = task_root.resolve(strict=True)
        except OSError as exc:
            raise _error("OpenRouter artifact-collision recovery task root is absent") from exc
        if (
            task_root.is_symlink()
            or not task_root.is_dir()
            or not resolved_task_root.is_relative_to(resolved_artifact_root)
        ):
            raise _error("OpenRouter artifact-collision recovery task root is invalid")

        collisions = []
        for variant, retry_pages in sorted(expected_frontiers.items()):
            legacy_relative = Path("adaptive-retry") / variant / "document-contract.json"
            legacy_contract_path = resolved_task_root / legacy_relative
            if legacy_contract_path.is_symlink() or not legacy_contract_path.is_file():
                raise _error("OpenRouter legacy adaptive-retry contract is absent")
            legacy_bytes = legacy_contract_path.read_bytes()
            try:
                legacy = json.loads(legacy_bytes)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise _error("OpenRouter legacy adaptive-retry contract is invalid") from exc
            legacy_pages = legacy.get("selected_physical_pages") if type(legacy) is dict else None
            legacy_document = legacy.get("document") if type(legacy) is dict else None
            legacy_material = (
                {key: value for key, value in legacy.items() if key != "document_run_id"}
                if type(legacy) is dict
                else None
            )
            if (
                type(legacy) is not dict
                or legacy.get("format_version") != "GEMINI_JSON_FIRST_OPENROUTER_PAGE_FRONTIER_V1"
                or legacy.get("prompt_variant") != variant
                or type(legacy_document) is not dict
                or legacy_document.get("source_logical_name") != row["relative_path"]
                or legacy_document.get("source_sha256") != row["source_sha256"]
                or legacy_document.get("source_size_bytes") != row["source_size_bytes"]
                or legacy.get("page_count") != row["document_page_count"]
                or type(legacy_pages) is not list
                or legacy_pages != sorted(set(legacy_pages))
                or legacy_pages != legacy_frontiers[variant]
                or retry_pages == legacy_pages
                or legacy.get("document_run_id")
                != "gjfporv1:document:" + canonical_json_sha256_v1(legacy_material)
            ):
                raise _error("OpenRouter legacy adaptive-retry contract does not prove a collision")
            frontier_sha256 = sha256(canonical_json_bytes_v1(retry_pages)).hexdigest()
            replacement_relative = (
                Path("adaptive-retry")
                / variant
                / f"pages-{frontier_sha256}"
                / "document-contract.json"
            )
            if (resolved_task_root / replacement_relative).exists():
                raise _error("OpenRouter replacement adaptive-retry contract already exists")
            collisions.append(
                {
                    "legacy_contract_relative_path": legacy_relative.as_posix(),
                    "legacy_contract_sha256": sha256(legacy_bytes).hexdigest(),
                    "legacy_physical_pages": legacy_pages,
                    "prompt_variant": variant,
                    "replacement_contract_relative_path": replacement_relative.as_posix(),
                    "retry_physical_pages": retry_pages,
                }
            )

        recovery = {
            "collision_evidence": collisions,
            "failed_pages": failed,
            "format_version": "GEMINI_JSON_FIRST_OPENROUTER_LOCAL_ARTIFACT_COLLISION_RECOVERY_V1",
            "prior_failed_receipt_sha256": sha256(row["last_receipt_json"]).hexdigest(),
            "recitation_failed_pages": recitation,
            "recovery_same_attempt": True,
            "retry_frontier_receipt_sha256": sha256(events[2]["receipt_json"]).hexdigest(),
            "semantic_failed_pages": semantic,
            "unresolved_pages": unresolved,
        }
        recovery_bytes = canonical_json_bytes_v1(recovery)
        event_ordinal = connection.execute(
            "SELECT COUNT(*)+1 FROM task_event WHERE task_id=?", (task_id,)
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO task_event VALUES (?,?,?,?,?)",
            (task_id, event_ordinal, "FAILED", "RUNNING", recovery_bytes),
        )
        connection.execute(
            "UPDATE task SET state='RUNNING',provider_job_ref=NULL,last_receipt_json=? "
            "WHERE task_id=?",
            (recovery_bytes, task_id),
        )
        connection.commit()
        updated = connection.execute("SELECT * FROM task WHERE task_id=?", (task_id,)).fetchone()
    return dict(updated)


def seal_offline_revalidated_corpus_task_v1(
    path: Path,
    *,
    task_id: str,
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Seal FAILED→SUCCEEDED only after a no-provider raw-response revalidation."""

    checked = canonical_clone_v1(dict(receipt))
    if set(checked) != {
        "document_manifest_id",
        "offline_revalidated",
        "replayed_pages",
        "revalidated_pages",
        "result",
    }:
        raise _error("offline revalidation receipt fields drifted")
    if checked["offline_revalidated"] is not True:
        raise _error("offline revalidation receipt is not affirmative")
    if type(checked["document_manifest_id"]) is not str or not checked[
        "document_manifest_id"
    ].startswith("gfdmv1:manifest:"):
        raise _error("offline revalidation document manifest is invalid")
    replayed_pages = checked["replayed_pages"]
    if (
        type(replayed_pages) is not list
        or replayed_pages != sorted(set(replayed_pages))
        or any(type(page) is not int or page <= 0 for page in replayed_pages)
    ):
        raise _error("offline replayed page frontier is invalid")
    revalidated_pages = checked["revalidated_pages"]
    if (
        type(revalidated_pages) is not list
        or not revalidated_pages
        or revalidated_pages != sorted(set(revalidated_pages))
        or any(type(page) is not int or page <= 0 for page in revalidated_pages)
        or not set(replayed_pages) <= set(revalidated_pages)
    ):
        raise _error("offline revalidated page frontier is invalid")
    result = checked["result"]
    if (
        type(result) is not dict
        or result.get("disposition") != "SUCCEEDED"
        or result.get("manifest_id") != checked["document_manifest_id"]
        or result.get("failed_pages") != []
        or result.get("offline_missing_pages") != []
        or result.get("semantic_failed_pages") != []
        or result.get("ingested_pages") != replayed_pages
        or type(result.get("cached_pages")) is not list
        or result["cached_pages"] != sorted(set(result["cached_pages"]))
        or sorted(set(result["cached_pages"]) | set(replayed_pages)) != revalidated_pages
    ):
        raise _error("offline revalidation result is not terminally complete")
    receipt_bytes = canonical_json_bytes_v1(checked)
    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT * FROM task WHERE task_id=?", (task_id,)).fetchone()
        if row is None or row["state"] != "FAILED" or row["route"] != OPENROUTER_ROUTE:
            raise _error("offline revalidation requires one failed OpenRouter task")
        expected_pages = list(range(row["first_physical_page"], row["last_physical_page"] + 1))
        if revalidated_pages != expected_pages:
            raise _error("offline revalidation does not cover the task frontier")
        event_ordinal = connection.execute(
            "SELECT COUNT(*)+1 FROM task_event WHERE task_id=?", (task_id,)
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO task_event VALUES (?,?,?,?,?)",
            (task_id, event_ordinal, "FAILED", "SUCCEEDED", receipt_bytes),
        )
        connection.execute(
            "UPDATE task SET state='SUCCEEDED', last_receipt_json=? WHERE task_id=?",
            (receipt_bytes, task_id),
        )
        connection.commit()
        updated = connection.execute("SELECT * FROM task WHERE task_id=?", (task_id,)).fetchone()
    return dict(updated)


def seal_google_fallback_corpus_task_v1(
    path: Path,
    *,
    task_id: str,
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Seal FAILED→SUCCEEDED after bounded missing pages complete through Google."""

    checked = canonical_clone_v1(dict(receipt))
    if set(checked) != {
        "document_manifest_id",
        "fallback_gateway",
        "fallback_pages",
        "result",
    }:
        raise _error("Google fallback receipt fields drifted")
    if checked["fallback_gateway"] != "GOOGLE_GEMINI_API":
        raise _error("Google fallback gateway is invalid")
    if type(checked["document_manifest_id"]) is not str or not checked[
        "document_manifest_id"
    ].startswith("gfdmv1:manifest:"):
        raise _error("Google fallback document manifest is invalid")
    pages = checked["fallback_pages"]
    if (
        type(pages) is not list
        or not pages
        or pages != sorted(set(pages))
        or any(type(page) is not int or page <= 0 for page in pages)
    ):
        raise _error("Google fallback page frontier is invalid")
    result = checked["result"]
    if (
        type(result) is not dict
        or result.get("disposition") != "SUCCEEDED"
        or result.get("manifest_id") != checked["document_manifest_id"]
        or result.get("failed_pages") != []
        or result.get("offline_missing_pages") != []
        or result.get("semantic_failed_pages") != []
    ):
        raise _error("Google fallback result is not terminally complete")
    receipt_bytes = canonical_json_bytes_v1(checked)
    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT * FROM task WHERE task_id=?", (task_id,)).fetchone()
        if row is None or row["state"] != "FAILED" or row["route"] != OPENROUTER_ROUTE:
            raise _error("Google fallback requires one failed OpenRouter task")
        if any(
            page < row["first_physical_page"] or page > row["last_physical_page"] for page in pages
        ):
            raise _error("Google fallback page lies outside the task frontier")
        event_ordinal = connection.execute(
            "SELECT COUNT(*)+1 FROM task_event WHERE task_id=?", (task_id,)
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO task_event VALUES (?,?,?,?,?)",
            (task_id, event_ordinal, "FAILED", "SUCCEEDED", receipt_bytes),
        )
        connection.execute(
            "UPDATE task SET state='SUCCEEDED', last_receipt_json=? WHERE task_id=?",
            (receipt_bytes, task_id),
        )
        connection.commit()
        updated = connection.execute("SELECT * FROM task WHERE task_id=?", (task_id,)).fetchone()
    return dict(updated)


def seal_openrouter_exhausted_page_repair_corpus_task_v1(
    path: Path,
    *,
    task_id: str,
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Seal FAILED→SUCCEEDED after an explicit bounded Flex page repair."""

    checked = canonical_clone_v1(dict(receipt))
    required = {
        "disposition",
        "document_manifest_id",
        "failed_pages",
        "format_version",
        "offline_missing_pages",
        "prior_failed_receipt_sha256",
        "provider_results",
        "recitation_failed_pages",
        "repair_attempt",
        "repair_gateway",
        "requested_service_tier",
        "revalidated_pages",
        "semantic_failed_pages",
        "unresolved_pages",
    }
    format_version = checked.get("format_version")
    if format_version == "GEMINI_JSON_FIRST_OPENROUTER_EXHAUSTED_PAGE_REPAIR_V2":
        required.add("offline_replay_results")
    if set(checked) != required:
        raise _error("OpenRouter exhausted-page repair receipt fields drifted")
    if (
        format_version
        not in {
            "GEMINI_JSON_FIRST_OPENROUTER_EXHAUSTED_PAGE_REPAIR_V1",
            "GEMINI_JSON_FIRST_OPENROUTER_EXHAUSTED_PAGE_REPAIR_V2",
        }
        or checked["disposition"] != "SUCCEEDED"
        or checked["repair_gateway"] != "OPENROUTER"
        or checked["requested_service_tier"] != "flex"
        or type(checked["repair_attempt"]) is not int
        or not 1 <= checked["repair_attempt"] <= 2
        or checked["failed_pages"] != []
        or checked["offline_missing_pages"] != []
        or checked["recitation_failed_pages"] != []
        or checked["semantic_failed_pages"] != []
        or checked["unresolved_pages"] != []
    ):
        raise _error("OpenRouter exhausted-page repair is not terminally successful")
    manifest_id = checked["document_manifest_id"]
    prior_sha = checked["prior_failed_receipt_sha256"]
    if (
        type(manifest_id) is not str
        or not manifest_id.startswith("gfdmv1:manifest:")
        or type(prior_sha) is not str
        or len(prior_sha) != 64
        or any(character not in "0123456789abcdef" for character in prior_sha)
    ):
        raise _error("OpenRouter exhausted-page repair authority is invalid")
    revalidated_pages = checked["revalidated_pages"]
    provider_results = checked["provider_results"]
    offline_replay_results = checked.get("offline_replay_results", [])
    if (
        type(revalidated_pages) is not list
        or not revalidated_pages
        or revalidated_pages != sorted(set(revalidated_pages))
        or any(type(page) is not int or page <= 0 for page in revalidated_pages)
        or type(provider_results) is not list
        or type(offline_replay_results) is not list
        or not (provider_results or offline_replay_results)
        or (
            format_version == "GEMINI_JSON_FIRST_OPENROUTER_EXHAUSTED_PAGE_REPAIR_V1"
            and offline_replay_results
        )
    ):
        raise _error("OpenRouter exhausted-page repair frontier is invalid")
    completed_pages: set[int] = set()
    attempted_pages: set[int] = set()
    prior_item_attempt = 0
    for item in provider_results:
        if type(item) is not dict or set(item) != {
            "accepted_pages",
            "physical_pages",
            "prompt_variant",
            "repair_attempt",
            "result",
        }:
            raise _error("OpenRouter exhausted-page provider result fields drifted")
        pages = item["physical_pages"]
        result = item["result"]
        accepted = item["accepted_pages"]
        item_attempt = item["repair_attempt"]
        failed = result.get("failed_pages") if type(result) is dict else None
        cached = result.get("cached_pages") if type(result) is dict else None
        ingested = result.get("ingested_pages") if type(result) is dict else None
        if (
            type(pages) is not list
            or not pages
            or pages != sorted(set(pages))
            or completed_pages.intersection(pages)
            or type(accepted) is not list
            or accepted != sorted(set(accepted))
            or type(item_attempt) is not int
            or not max(1, prior_item_attempt) <= item_attempt <= checked["repair_attempt"]
            or item["prompt_variant"] not in {"balanced", "compact", "items", "scope", "simple"}
            or type(result) is not dict
            or result.get("disposition") not in {"NEEDS_RETRY", "SUCCEEDED"}
            or type(failed) is not list
            or failed != sorted(set(failed))
            or type(cached) is not list
            or cached != sorted(set(cached))
            or type(ingested) is not list
            or ingested != sorted(set(ingested))
            or set(cached) & set(ingested)
            or set(failed) & (set(cached) | set(ingested))
            or sorted(set(failed) | set(cached) | set(ingested)) != pages
            or not set(accepted).issubset(set(cached) | set(ingested))
            or result.get("offline_missing_pages", []) != []
            or any(
                type(values) is not list or not set(values).issubset(failed)
                for values in (
                    result.get("recitation_failed_pages", []),
                    result.get("semantic_failed_pages", []),
                    result.get("unresolved_pages", []),
                )
            )
        ):
            raise _error("OpenRouter exhausted-page provider result is invalid")
        prior_item_attempt = item_attempt
        attempted_pages.update(pages)
        completed_pages.update(accepted)
    for item in offline_replay_results:
        if type(item) is not dict or set(item) != {
            "accepted_pages",
            "execution_mode",
            "physical_pages",
            "prompt_variant",
            "repair_attempt",
            "result",
        }:
            raise _error("offline semantic replay result fields drifted")
        pages = item["physical_pages"]
        result = item["result"]
        accepted = item["accepted_pages"]
        item_attempt = item["repair_attempt"]
        failed = result.get("failed_pages") if type(result) is dict else None
        cached = result.get("cached_pages") if type(result) is dict else None
        ingested = result.get("ingested_pages") if type(result) is dict else None
        replay_sources = result.get("semantic_replay_sources") if type(result) is dict else None
        if (
            item["execution_mode"] != "OFFLINE_REPLAY_ONLY"
            or type(pages) is not list
            or not pages
            or pages != sorted(set(pages))
            or type(accepted) is not list
            or accepted != sorted(set(accepted))
            or completed_pages.intersection(accepted)
            or type(item_attempt) is not int
            or not 1 <= item_attempt <= checked["repair_attempt"]
            or item["prompt_variant"] not in {"balanced", "compact", "items", "scope", "simple"}
            or type(result) is not dict
            or result.get("execution_mode") != "OFFLINE_REPLAY_ONLY"
            or result.get("disposition") not in {"NEEDS_RETRY", "SUCCEEDED"}
            or type(failed) is not list
            or failed != sorted(set(failed))
            or type(cached) is not list
            or cached != sorted(set(cached))
            or type(ingested) is not list
            or ingested != sorted(set(ingested))
            or set(cached) & set(ingested)
            or set(failed) & (set(cached) | set(ingested))
            or sorted(set(failed) | set(cached) | set(ingested)) != pages
            or not set(accepted).issubset(set(cached) | set(ingested))
            or result.get("provider_request_pages") != []
            or result.get("recitation_failed_pages", []) != []
            or any(
                type(values) is not list or not set(values).issubset(failed)
                for values in (
                    result.get("offline_missing_pages", []),
                    result.get("semantic_failed_pages", []),
                    result.get("unresolved_pages", []),
                )
            )
            or type(replay_sources) is not list
            or any(
                type(source) is not dict
                or set(source) != {"physical_page", "source_relative_path"}
                or source["physical_page"] not in ingested
                or type(source["source_relative_path"]) is not str
                or not source["source_relative_path"]
                for source in replay_sources
            )
            or len({source["physical_page"] for source in replay_sources}) != len(replay_sources)
        ):
            raise _error("offline semantic replay result is invalid")
        attempted_pages.update(pages)
        completed_pages.update(accepted)
    receipt_bytes = canonical_json_bytes_v1(checked)
    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT * FROM task WHERE task_id=?", (task_id,)).fetchone()
        if row is None or row["state"] != "FAILED" or row["route"] != OPENROUTER_ROUTE:
            raise _error("OpenRouter exhausted-page repair requires one failed Flex task")
        expected_pages = list(range(row["first_physical_page"], row["last_physical_page"] + 1))
        try:
            repair_frontier = _openrouter_failed_task_repair_frontier_v1(connection, row=row)
            prior_failed_pages = repair_frontier["failed_pages"]
        except GeminiJsonFirstCorpusLedgerV1Error:
            # Early corpus wrappers could terminate after writing only this
            # strict subprocess-failure receipt, without the four-event retry
            # chain needed to reconstruct an older failed-page frontier.  At
            # this seal boundary every provider/cache result has already been
            # checked, the complete document page range has been revalidated,
            # and the exact pre-repair receipt hash is bound below.  Therefore
            # the union of actually attempted pages is the only admissible
            # legacy frontier; arbitrary pages outside the document or an
            # incomplete manifest remain rejected by the common checks.
            try:
                legacy_failure = json.loads(row["last_receipt_json"])
            except (TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise _error("OpenRouter legacy repair receipt is invalid") from exc
            identity = connection.execute("SELECT * FROM run_identity WHERE singleton=1").fetchone()
            legacy_fields = {
                "disposition",
                "provider_returncode",
                "provider_stderr_bytes",
                "provider_stderr_sha256",
                "provider_stdout_bytes",
                "provider_stdout_sha256",
                "retry_allowed",
            }
            if (
                row["attempt_count"] != identity["max_task_attempts"]
                or type(legacy_failure) is not dict
                or set(legacy_failure) != legacy_fields
                or legacy_failure["disposition"] != "OPENROUTER_PROVIDER_SUBPROCESS_FAILURE"
                or type(legacy_failure["provider_returncode"]) is not int
                or legacy_failure["provider_returncode"] != 1
                or type(legacy_failure["provider_stderr_bytes"]) is not int
                or legacy_failure["provider_stderr_bytes"] <= 0
                or type(legacy_failure["provider_stdout_bytes"]) is not int
                or legacy_failure["provider_stdout_bytes"] != 0
                or legacy_failure["provider_stdout_sha256"] != sha256(b"").hexdigest()
                or legacy_failure["retry_allowed"] is not False
                or any(
                    type(legacy_failure[field]) is not str
                    or len(legacy_failure[field]) != 64
                    or any(
                        character not in "0123456789abcdef" for character in legacy_failure[field]
                    )
                    for field in ("provider_stderr_sha256", "provider_stdout_sha256")
                )
            ):
                raise
            prior_failed_pages = sorted(attempted_pages)
        if (
            revalidated_pages != expected_pages
            or attempted_pages != set(prior_failed_pages)
            or completed_pages != set(prior_failed_pages)
            or not attempted_pages.issubset(expected_pages)
        ):
            raise _error("OpenRouter exhausted-page repair lies outside the task frontier")
        if sha256(row["last_receipt_json"]).hexdigest() != prior_sha:
            raise _error("OpenRouter exhausted-page prior failed receipt drifted")
        event_ordinal = connection.execute(
            "SELECT COUNT(*)+1 FROM task_event WHERE task_id=?", (task_id,)
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO task_event VALUES (?,?,?,?,?)",
            (task_id, event_ordinal, "FAILED", "SUCCEEDED", receipt_bytes),
        )
        connection.execute(
            "UPDATE task SET state='SUCCEEDED',last_receipt_json=? WHERE task_id=?",
            (receipt_bytes, task_id),
        )
        connection.commit()
        updated = connection.execute("SELECT * FROM task WHERE task_id=?", (task_id,)).fetchone()
    return dict(updated)


def seal_current_document_revalidated_corpus_tasks_v1(
    path: Path,
    *,
    task_id: str,
    receipt: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Atomically seal retryable/failed chunks after a current manifest replays.

    This is route agnostic: the authority is the validated document manifest,
    its complete image/prompt frontiers, and the already authenticated ledger
    document partition.  It never changes attempts or reopens a provider job.
    """

    checked = canonical_clone_v1(dict(receipt))
    if set(checked) != {
        "current_document_revalidated",
        "document_manifest_id",
        "page_image_sha256s",
        "page_prompt_variants",
        "repaired_task_ids",
        "revalidated_pages",
        "status_counts",
    }:
        raise _error("current document revalidation receipt fields drifted")
    if checked["current_document_revalidated"] is not True:
        raise _error("current document revalidation receipt is not affirmative")
    manifest_id = checked["document_manifest_id"]
    if type(manifest_id) is not str or not manifest_id.startswith("gfdmv1:manifest:"):
        raise _error("current document revalidation manifest is invalid")
    revalidated_pages = checked["revalidated_pages"]
    if (
        type(revalidated_pages) is not list
        or not revalidated_pages
        or revalidated_pages != list(range(1, len(revalidated_pages) + 1))
    ):
        raise _error("current document revalidation page frontier is invalid")
    image_frontier = checked["page_image_sha256s"]
    if (
        type(image_frontier) is not list
        or [item.get("physical_page") for item in image_frontier if type(item) is dict]
        != revalidated_pages
        or any(
            type(item) is not dict
            or set(item) != {"image_sha256", "physical_page"}
            or type(item["image_sha256"]) is not str
            or len(item["image_sha256"]) != 64
            or any(character not in "0123456789abcdef" for character in item["image_sha256"])
            for item in image_frontier
        )
    ):
        raise _error("current document revalidation image frontier is invalid")
    prompt_frontier = checked["page_prompt_variants"]
    allowed_variants = {"balanced", "compact", "items", "scope", "simple"}
    if (
        type(prompt_frontier) is not list
        or [item.get("physical_page") for item in prompt_frontier if type(item) is dict]
        != revalidated_pages
        or any(
            type(item) is not dict
            or set(item) != {"physical_page", "prompt_variant"}
            or item["prompt_variant"] not in allowed_variants
            for item in prompt_frontier
        )
    ):
        raise _error("current document revalidation prompt frontier is invalid")
    repaired_task_ids = checked["repaired_task_ids"]
    if (
        type(repaired_task_ids) is not list
        or not repaired_task_ids
        or repaired_task_ids != sorted(set(repaired_task_ids))
        or any(type(value) is not str or not value for value in repaired_task_ids)
    ):
        raise _error("current document revalidation task frontier is invalid")
    status_counts = checked["status_counts"]
    allowed_statuses = {
        "FINANCIAL_NOTE_CONTENT",
        "MIXED_FINANCIAL_CONTENT",
        "NO_RELEVANT_FINANCIAL_CONTENT",
        "PRIMARY_FINANCIAL_STATEMENT",
    }
    if (
        type(status_counts) is not dict
        or not status_counts
        or not set(status_counts) <= allowed_statuses
        or any(type(count) is not int or count < 0 for count in status_counts.values())
        or sum(status_counts.values()) != len(revalidated_pages)
    ):
        raise _error("current document revalidation status counts are invalid")

    receipt_bytes = canonical_json_bytes_v1(checked)
    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        selected = connection.execute("SELECT * FROM task WHERE task_id=?", (task_id,)).fetchone()
        if selected is None:
            raise _error("current document revalidation task is absent")
        rows = connection.execute(
            "SELECT * FROM task WHERE document_plan_id=? ORDER BY first_physical_page,task_id",
            (selected["document_plan_id"],),
        ).fetchall()
        if not rows or any(
            row["relative_path"] != selected["relative_path"]
            or row["source_sha256"] != selected["source_sha256"]
            or row["document_page_count"] != selected["document_page_count"]
            or row["state"] not in {"FAILED", "NEEDS_RETRY", "SUCCEEDED"}
            for row in rows
        ):
            raise _error("current document revalidation ledger frontier is not terminal")
        expected_pages = [
            page
            for row in rows
            for page in range(row["first_physical_page"], row["last_physical_page"] + 1)
        ]
        repairable_rows = [row for row in rows if row["state"] in {"FAILED", "NEEDS_RETRY"}]
        if (
            expected_pages != revalidated_pages
            or len(revalidated_pages) != selected["document_page_count"]
            or [row["task_id"] for row in repairable_rows] != repaired_task_ids
        ):
            raise _error("current document revalidation does not cover the ledger document")
        for row in repairable_rows:
            event_ordinal = connection.execute(
                "SELECT COUNT(*)+1 FROM task_event WHERE task_id=?", (row["task_id"],)
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO task_event VALUES (?,?,?,?,?)",
                (
                    row["task_id"],
                    event_ordinal,
                    row["state"],
                    "SUCCEEDED",
                    receipt_bytes,
                ),
            )
            connection.execute(
                "UPDATE task SET state='SUCCEEDED', last_receipt_json=? WHERE task_id=?",
                (receipt_bytes, row["task_id"]),
            )
        connection.commit()
        updated = [
            dict(
                connection.execute(
                    "SELECT * FROM task WHERE task_id=?", (row["task_id"],)
                ).fetchone()
            )
            for row in repairable_rows
        ]
    return updated


def claim_google_document_for_openrouter_acceleration_v1(
    path: Path,
    *,
    task_id: str,
) -> dict[str, Any]:
    """Atomically reserve every pending Google chunk of one document for OpenRouter."""

    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        selected = connection.execute("SELECT * FROM task WHERE task_id=?", (task_id,)).fetchone()
        if selected is None or selected["route"] != GOOGLE_ROUTE:
            raise _error("OpenRouter acceleration requires one planned Google task")
        rows = connection.execute(
            "SELECT * FROM task WHERE document_plan_id=? ORDER BY first_physical_page,task_id",
            (selected["document_plan_id"],),
        ).fetchall()
        task_ids = [row["task_id"] for row in rows]
        material = {
            "document_plan_id": selected["document_plan_id"],
            "format_version": "GEMINI_JSON_FIRST_OPENROUTER_ACCELERATION_CLAIM_V1",
            "gateway": "OPENROUTER",
            "source_sha256": selected["source_sha256"],
            "task_ids": task_ids,
        }
        claim_id = "gjfpaccelv1:claim:" + canonical_json_sha256_v1(material)
        receipt = {**material, "claim_id": claim_id}
        receipt_bytes = canonical_json_bytes_v1(receipt)
        expected_pages = [
            page
            for row in rows
            for page in range(row["first_physical_page"], row["last_physical_page"] + 1)
        ]
        if (
            not rows
            or any(
                row["route"] != GOOGLE_ROUTE
                or row["relative_path"] != selected["relative_path"]
                or row["source_sha256"] != selected["source_sha256"]
                or row["document_page_count"] != selected["document_page_count"]
                for row in rows
            )
            or expected_pages != list(range(1, selected["document_page_count"] + 1))
        ):
            raise _error("OpenRouter acceleration document frontier is invalid")
        states = {row["state"] for row in rows}
        retryable_states = {"PENDING", "NEEDS_RETRY"}
        if states and states <= retryable_states | {"SUCCEEDED"} and states & retryable_states:
            identity = connection.execute("SELECT * FROM run_identity WHERE singleton=1").fetchone()
            for row in rows:
                if row["state"] == "SUCCEEDED":
                    continue
                attempt_count = row["attempt_count"] + 1
                if attempt_count > identity["max_task_attempts"]:
                    raise _error("OpenRouter acceleration retry bound is exhausted")
                event_ordinal = connection.execute(
                    "SELECT COUNT(*)+1 FROM task_event WHERE task_id=?", (row["task_id"],)
                ).fetchone()[0]
                connection.execute(
                    "INSERT INTO task_event VALUES (?,?,?,?,?)",
                    (
                        row["task_id"],
                        event_ordinal,
                        row["state"],
                        "RUNNING",
                        receipt_bytes,
                    ),
                )
                connection.execute(
                    "UPDATE task SET state='RUNNING',attempt_count=?,provider_job_ref=?,"
                    "last_receipt_json=? WHERE task_id=?",
                    (attempt_count, claim_id, receipt_bytes, row["task_id"]),
                )
            connection.commit()
        elif states <= {"RUNNING", "SUCCEEDED"} and any(row["state"] == "RUNNING" for row in rows):
            if any(row["provider_job_ref"] != claim_id for row in rows):
                raise _error("OpenRouter acceleration resume claim is invalid")
            connection.commit()
        elif states == {"SUCCEEDED"} and all(row["provider_job_ref"] == claim_id for row in rows):
            connection.commit()
        else:
            raise _error("OpenRouter acceleration requires one retryable document frontier")
        updated = connection.execute(
            "SELECT * FROM task WHERE document_plan_id=? ORDER BY first_physical_page,task_id",
            (selected["document_plan_id"],),
        ).fetchall()
    return {
        "claim_id": claim_id,
        "document_plan_id": selected["document_plan_id"],
        "tasks": [dict(row) for row in updated],
    }
