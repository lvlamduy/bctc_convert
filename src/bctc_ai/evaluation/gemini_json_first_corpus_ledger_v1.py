"""Crash-resumable task ledger for the Gemini JSON-first corpus plan."""

from __future__ import annotations

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


def seal_current_document_revalidated_corpus_tasks_v1(
    path: Path,
    *,
    task_id: str,
    receipt: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Atomically seal failed chunks after one current whole-page manifest replays.

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
            or row["state"] not in {"FAILED", "SUCCEEDED"}
            for row in rows
        ):
            raise _error("current document revalidation ledger frontier is not terminal")
        expected_pages = [
            page
            for row in rows
            for page in range(row["first_physical_page"], row["last_physical_page"] + 1)
        ]
        failed_rows = [row for row in rows if row["state"] == "FAILED"]
        if (
            expected_pages != revalidated_pages
            or len(revalidated_pages) != selected["document_page_count"]
            or [row["task_id"] for row in failed_rows] != repaired_task_ids
        ):
            raise _error("current document revalidation does not cover the ledger document")
        for row in failed_rows:
            event_ordinal = connection.execute(
                "SELECT COUNT(*)+1 FROM task_event WHERE task_id=?", (row["task_id"],)
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO task_event VALUES (?,?,?,?,?)",
                (row["task_id"], event_ordinal, "FAILED", "SUCCEEDED", receipt_bytes),
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
            for row in failed_rows
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
