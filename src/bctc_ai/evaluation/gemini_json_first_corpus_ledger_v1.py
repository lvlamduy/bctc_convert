"""Crash-resumable task ledger for the Gemini JSON-first corpus plan."""

from __future__ import annotations

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
    if prompt_variant not in {"simple", "compact", "balanced"}:
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
        "result",
    }:
        raise _error("offline revalidation receipt fields drifted")
    if checked["offline_revalidated"] is not True:
        raise _error("offline revalidation receipt is not affirmative")
    if type(checked["document_manifest_id"]) is not str or not checked[
        "document_manifest_id"
    ].startswith("gfdmv1:manifest:"):
        raise _error("offline revalidation document manifest is invalid")
    pages = checked["replayed_pages"]
    if (
        type(pages) is not list
        or not pages
        or pages != sorted(set(pages))
        or any(type(page) is not int or page <= 0 for page in pages)
    ):
        raise _error("offline revalidation page frontier is invalid")
    result = checked["result"]
    if (
        type(result) is not dict
        or result.get("disposition") != "SUCCEEDED"
        or result.get("manifest_id") != checked["document_manifest_id"]
        or result.get("failed_pages") != []
        or result.get("offline_missing_pages") != []
        or result.get("semantic_failed_pages") != []
    ):
        raise _error("offline revalidation result is not terminally complete")
    receipt_bytes = canonical_json_bytes_v1(checked)
    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT * FROM task WHERE task_id=?", (task_id,)).fetchone()
        if row is None or row["state"] != "FAILED" or row["route"] != OPENROUTER_ROUTE:
            raise _error("offline revalidation requires one failed OpenRouter task")
        if any(
            page < row["first_physical_page"] or page > row["last_physical_page"] for page in pages
        ):
            raise _error("offline revalidation page lies outside the task frontier")
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
