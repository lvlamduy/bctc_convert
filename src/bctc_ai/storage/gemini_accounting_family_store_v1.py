"""Traceable SQLite store for derived Gemini JSON-first accounting families."""

from __future__ import annotations

import json
import os
import sqlite3
import stat
import tempfile
from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import (
    validate_current_corpus_manifest_index_v1,
)
from bctc_ai.storage.gemini_family_effective_page_frontier_v1 import (
    apply_gemini_family_effective_page_frontier_v1,
    effective_page_frontier_stages_v1,
)

FORMAT_VERSION = "GEMINI_ACCOUNTING_FAMILY_STORE_V1"


class GeminiAccountingFamilyStoreV1Error(RuntimeError):
    """The derived-family store or one of its immutable bindings drifted."""


def _error(message: str) -> GeminiAccountingFamilyStoreV1Error:
    return GeminiAccountingFamilyStoreV1Error(message)


_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE store_identity (
  singleton INTEGER PRIMARY KEY CHECK(singleton=1),
  format_version TEXT NOT NULL
) STRICT;
CREATE TABLE family_run (
  family_run_id TEXT PRIMARY KEY,
  sweep_id TEXT NOT NULL,
  family_id TEXT NOT NULL,
  sweep_format_version TEXT NOT NULL,
  corpus_manifest_index_id TEXT NOT NULL,
  corpus_index_sha256 TEXT NOT NULL,
  topology_spec_sha256 TEXT NOT NULL,
  evaluation_spec_sha256 TEXT NOT NULL,
  schema_binding_spec_sha256 TEXT NOT NULL,
  implementation_axis_sha256 TEXT NOT NULL,
  implementation_refs_json BLOB NOT NULL,
  sweep_sha256 TEXT NOT NULL,
  sweep_bytes BLOB NOT NULL,
  document_count INTEGER NOT NULL CHECK(document_count >= 0),
  ready_count INTEGER NOT NULL CHECK(ready_count >= 0),
  not_observed_count INTEGER NOT NULL CHECK(not_observed_count >= 0),
  unresolved_count INTEGER NOT NULL CHECK(unresolved_count >= 0),
  mapping_count INTEGER NOT NULL CHECK(mapping_count >= 0),
  UNIQUE(sweep_id, corpus_index_sha256, implementation_axis_sha256)
) STRICT;
CREATE TABLE family_run_execution (
  execution_ordinal INTEGER PRIMARY KEY AUTOINCREMENT,
  family_run_id TEXT NOT NULL REFERENCES family_run(family_run_id),
  run_kind TEXT NOT NULL CHECK(run_kind IN ('EXPERIMENTAL','OFFICIAL')),
  recorded_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
) STRICT;
CREATE TABLE family_trial (
  family_run_id TEXT NOT NULL REFERENCES family_run(family_run_id),
  document_ordinal INTEGER NOT NULL CHECK(document_ordinal > 0),
  source_logical_name TEXT NOT NULL,
  source_sha256 TEXT NOT NULL,
  status TEXT NOT NULL,
  candidate_count INTEGER NOT NULL CHECK(candidate_count >= 0),
  selected_candidate_id TEXT,
  mapping_count INTEGER NOT NULL CHECK(mapping_count >= 0),
  reasons_json BLOB NOT NULL,
  trial_sha256 TEXT NOT NULL,
  trial_bytes BLOB NOT NULL,
  PRIMARY KEY(family_run_id, document_ordinal),
  UNIQUE(family_run_id, source_logical_name)
) STRICT;
CREATE TABLE family_candidate (
  family_run_id TEXT NOT NULL,
  document_ordinal INTEGER NOT NULL,
  candidate_id TEXT NOT NULL,
  page_json_version_id TEXT NOT NULL,
  physical_page INTEGER NOT NULL CHECK(physical_page > 0),
  section_id TEXT NOT NULL,
  table_id TEXT NOT NULL,
  status TEXT NOT NULL,
  reason_count INTEGER NOT NULL CHECK(reason_count >= 0),
  mapping_count INTEGER NOT NULL CHECK(mapping_count >= 0),
  candidate_sha256 TEXT NOT NULL,
  candidate_bytes BLOB NOT NULL,
  PRIMARY KEY(family_run_id, document_ordinal, candidate_id),
  FOREIGN KEY(family_run_id, document_ordinal)
    REFERENCES family_trial(family_run_id, document_ordinal)
) STRICT;
CREATE TABLE family_mapping (
  family_run_id TEXT NOT NULL,
  document_ordinal INTEGER NOT NULL,
  mapping_ordinal INTEGER NOT NULL CHECK(mapping_ordinal > 0),
  report_norm_id INTEGER NOT NULL CHECK(report_norm_id > 0),
  role TEXT NOT NULL,
  row_id TEXT NOT NULL,
  mapping_sha256 TEXT NOT NULL,
  mapping_bytes BLOB NOT NULL,
  PRIMARY KEY(family_run_id, document_ordinal, mapping_ordinal),
  FOREIGN KEY(family_run_id, document_ordinal)
    REFERENCES family_trial(family_run_id, document_ordinal)
) STRICT;
CREATE TABLE family_current_selection (
  family_id TEXT PRIMARY KEY,
  family_run_id TEXT NOT NULL REFERENCES family_run(family_run_id),
  selected_at_utc TEXT NOT NULL
) STRICT;
CREATE TABLE family_selection_event (
  event_ordinal INTEGER PRIMARY KEY AUTOINCREMENT,
  family_id TEXT NOT NULL,
  prior_family_run_id TEXT,
  next_family_run_id TEXT NOT NULL REFERENCES family_run(family_run_id),
  selected_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE(family_id, next_family_run_id)
) STRICT;
CREATE TABLE family_export (
  family_run_id TEXT NOT NULL REFERENCES family_run(family_run_id),
  output_path TEXT NOT NULL,
  output_sha256 TEXT NOT NULL,
  output_size_bytes INTEGER NOT NULL CHECK(output_size_bytes > 0),
  recorded_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  PRIMARY KEY(family_run_id, output_path)
) STRICT;
CREATE INDEX idx_family_run_family ON family_run(family_id, family_run_id);
CREATE INDEX idx_family_trial_status ON family_trial(family_run_id, status, document_ordinal);
CREATE INDEX idx_family_candidate_page_version
  ON family_candidate(page_json_version_id, family_run_id);
CREATE INDEX idx_family_mapping_role
  ON family_mapping(report_norm_id, role, family_run_id, document_ordinal);
"""

_REGION_REPAIR_QUEUE_SCHEMA = """
CREATE TABLE IF NOT EXISTS family_region_repair_job (
  repair_job_id TEXT PRIMARY KEY,
  family_run_id TEXT NOT NULL REFERENCES family_run(family_run_id),
  document_ordinal INTEGER NOT NULL CHECK(document_ordinal > 0),
  candidate_id TEXT NOT NULL,
  base_page_json_version_id TEXT NOT NULL,
  physical_page INTEGER NOT NULL CHECK(physical_page > 0),
  status TEXT NOT NULL CHECK(status IN ('PENDING','RUNNING','RESOLVED','ABSTAINED')),
  plan_sha256 TEXT NOT NULL,
  plan_bytes BLOB NOT NULL,
  selected_page_json_version_id TEXT,
  created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE(family_run_id, candidate_id, base_page_json_version_id)
) STRICT;
CREATE TABLE IF NOT EXISTS family_region_repair_attempt (
  repair_job_id TEXT NOT NULL REFERENCES family_region_repair_job(repair_job_id),
  attempt_ordinal INTEGER NOT NULL CHECK(attempt_ordinal > 0),
  thinking_level TEXT NOT NULL CHECK(thinking_level IN ('low','medium','high')),
  outcome TEXT NOT NULL,
  page_json_version_id TEXT,
  usage_json BLOB,
  reason_json BLOB NOT NULL,
  recorded_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  PRIMARY KEY(repair_job_id, attempt_ordinal)
) STRICT;
CREATE INDEX IF NOT EXISTS idx_family_region_repair_status
  ON family_region_repair_job(status, family_run_id, document_ordinal);
"""


def initialize_gemini_accounting_family_store_v1(path: Path) -> None:
    """Create a derived-family store atomically without replacing an existing file."""

    destination = path.resolve()
    if destination.exists():
        raise _error("refusing to overwrite an existing Gemini family store")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, stage_name = tempfile.mkstemp(
        prefix=destination.name + ".stage-", suffix=".sqlite3", dir=destination.parent
    )
    os.close(descriptor)
    stage = Path(stage_name)
    try:
        with sqlite3.connect(stage) as connection:
            connection.executescript(_SCHEMA)
            connection.execute("INSERT INTO store_identity VALUES (1, ?)", (FORMAT_VERSION,))
            connection.commit()
        os.chmod(stage, 0o600)
        os.replace(stage, destination)
    finally:
        stage.unlink(missing_ok=True)


def _connect(path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    if path.is_symlink() or not path.is_file():
        raise _error("Gemini family store is absent or not regular")
    uri = f"file:{path.resolve()}?mode={'ro' if readonly else 'rw'}"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    identity = connection.execute(
        "SELECT format_version FROM store_identity WHERE singleton=1"
    ).fetchone()
    if identity is None or identity[0] != FORMAT_VERSION:
        connection.close()
        raise _error("Gemini family store identity drifted")
    return connection


def _stored_candidate_repair_target_replays_v1(
    *,
    plan: Mapping[str, Any],
    candidate_row: Sequence[Any],
    stored_trial: Mapping[str, Any],
    stored_candidate: Mapping[str, Any],
) -> bool:
    """Bind a repair target to the candidate root or one exact sealed component."""

    status = stored_candidate.get("status")
    if (
        status
        not in {
            "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY",
            "UNRESOLVED_GEMINI_JSON_FAMILY",
        }
        or stored_trial.get("status") != status
    ):
        return False
    row = tuple(candidate_row)
    target_locator = (
        plan.get("base_page_json_version_id"),
        plan.get("physical_page"),
        plan.get("section_id"),
        plan.get("table_id"),
    )
    if len(row) != 7 or row[4:] != (
        status,
        plan.get("source_logical_name"),
        plan.get("source_sha256"),
    ):
        return False
    query_receipt = (
        stored_candidate.get("closure_receipt", {}).get("query_receipt")
        if type(stored_candidate.get("closure_receipt")) is dict
        else None
    )
    component_regions = (
        query_receipt.get("component_regions", []) if type(query_receipt) is dict else []
    )
    matching_components = [
        region
        for region in component_regions
        if type(region) is dict
        and (
            region.get("page_json_version_id"),
            region.get("physical_page"),
            region.get("section_id"),
            region.get("table_id"),
            region.get("source_logical_name"),
            region.get("source_sha256"),
        )
        == (
            *target_locator,
            plan.get("source_logical_name"),
            plan.get("source_sha256"),
        )
    ]
    if row[:4] != target_locator and len(matching_components) != 1:
        return False
    return not (
        status == "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
        or "candidate_semantic_replay_sha256" in plan
    ) or plan.get("candidate_semantic_replay_sha256") == canonical_json_sha256_v1(stored_candidate)


def enqueue_gemini_family_region_repair_plans_v1(
    path: Path,
    *,
    family_run_id: str,
    plans: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Append deterministic pending repair jobs emitted by one stored family run."""

    checked = [dict(plan) for plan in plans]
    if any(
        plan.get("format_version") != "GEMINI_JSON_REGION_REPAIR_QUEUE_V1"
        or type(plan.get("repair_job_id")) is not str
        or not plan["repair_job_id"].startswith("gjfrrqv1:job:")
        or type(plan.get("document_ordinal")) is not int
        or plan["document_ordinal"] <= 0
        or type(plan.get("candidate_id")) is not str
        or type(plan.get("base_page_json_version_id")) is not str
        or type(plan.get("physical_page")) is not int
        or plan["physical_page"] <= 0
        or type(plan.get("target_ids")) is not list
        or not plan["target_ids"]
        for plan in checked
    ):
        raise _error("family region repair plan is invalid")
    with _connect(path) as connection:
        connection.executescript(_REGION_REPAIR_QUEUE_SCHEMA)
        run = connection.execute(
            "SELECT family_id,sweep_sha256,sweep_bytes FROM family_run WHERE family_run_id=?",
            (family_run_id,),
        ).fetchone()
        if run is None:
            raise _error("family region repair run is absent")
        sweep_payload = bytes(run["sweep_bytes"])
        if sha256(sweep_payload).hexdigest() != run["sweep_sha256"]:
            raise _error("family region repair source sweep bytes drifted")
        try:
            stored_sweep = validate_gemini_json_flat_family_sweep_v1(json.loads(sweep_payload))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise _error("family region repair source sweep is invalid") from exc
        for plan in checked:
            if plan.get("family_id") != run["family_id"]:
                raise _error("family region repair plan family does not replay")
            candidate = connection.execute(
                "SELECT c.page_json_version_id,c.physical_page,c.section_id,c.table_id,"
                "c.status,t.source_logical_name,t.source_sha256 "
                "FROM family_candidate AS c JOIN family_trial AS t "
                "ON t.family_run_id=c.family_run_id "
                "AND t.document_ordinal=c.document_ordinal "
                "WHERE c.family_run_id=? AND c.document_ordinal=? AND c.candidate_id=?",
                (family_run_id, plan["document_ordinal"], plan["candidate_id"]),
            ).fetchone()
            stored_trials = [
                trial
                for trial in stored_sweep["trials"]
                if trial["document_ordinal"] == plan["document_ordinal"]
            ]
            stored_candidates = (
                [
                    item
                    for item in stored_trials[0]["candidates"]
                    if item["candidate_id"] == plan["candidate_id"]
                ]
                if len(stored_trials) == 1
                else []
            )
            stored_candidate = stored_candidates[0] if len(stored_candidates) == 1 else None
            if candidate is None:
                disposition_sha256 = plan.get("query_disposition_sha256")
                evidence = stored_sweep.get("indexed_query_evidence")
                matching_dispositions = (
                    [
                        disposition
                        for disposition in evidence["candidate_dispositions"]
                        if disposition["source_logical_name"] == plan.get("source_logical_name")
                        and disposition["source_sha256"] == plan.get("source_sha256")
                        and disposition["page_json_version_id"] == plan["base_page_json_version_id"]
                        and disposition["physical_page"] == plan["physical_page"]
                        and disposition["section_id"] == plan.get("section_id")
                        and disposition["table_id"] == plan.get("table_id")
                    ]
                    if type(evidence) is dict
                    else []
                )
                trial = connection.execute(
                    "SELECT source_logical_name,source_sha256,status "
                    "FROM family_trial WHERE family_run_id=? AND document_ordinal=?",
                    (family_run_id, plan["document_ordinal"]),
                ).fetchone()
                if len(matching_dispositions) != 1 or trial is None:
                    raise _error("family indexed repair disposition does not replay")
                disposition = matching_dispositions[0]
                disposition_hash = canonical_json_sha256_v1(disposition)
                candidate_material = {
                    "disposition_sha256": disposition_hash,
                    "family_id": run["family_id"],
                    "page_json_version_id": disposition["page_json_version_id"],
                    "section_id": disposition["section_id"],
                    "table_id": disposition["table_id"],
                }
                if (
                    disposition_sha256 != disposition_hash
                    or plan["candidate_id"]
                    != "gjfafcv1:query-disposition:" + canonical_json_sha256_v1(candidate_material)
                    or disposition["disposition"]
                    not in {
                        "BRANCH_ABSENT",
                        "INSUFFICIENT_DISTINCT_CHILD_ROLES",
                    }
                    or disposition["hard_negative_evidence"] is not None
                    or (
                        disposition["branch_evidence"] is None
                        and disposition["owner_evidence"] is None
                    )
                    or tuple(trial)
                    != (
                        plan.get("source_logical_name"),
                        plan.get("source_sha256"),
                        "UNRESOLVED_GEMINI_JSON_FAMILY",
                    )
                    or plan.get("structural_context_pages") != disposition["context_pages"]
                    or plan.get("repair_scope")
                    != (
                        "ROW_LABEL_AND_VALUES"
                        if disposition["disposition"] == "INSUFFICIENT_DISTINCT_CHILD_ROLES"
                        else "STRUCTURAL_CONTEXT_SURFACES"
                    )
                ):
                    raise _error("family indexed repair disposition identity drifted")
            elif stored_candidate is None or not _stored_candidate_repair_target_replays_v1(
                plan=plan,
                candidate_row=candidate,
                stored_trial=stored_trials[0],
                stored_candidate=stored_candidate,
            ):
                raise _error("family region repair candidate does not replay")
            material = {key: plan[key] for key in plan if key != "repair_job_id"}
            if plan["repair_job_id"] != "gjfrrqv1:job:" + canonical_json_sha256_v1(material):
                raise _error("family region repair plan ID does not replay")
            plan_bytes = canonical_json_bytes_v1(plan) + b"\n"
            values = (
                plan["repair_job_id"],
                family_run_id,
                plan["document_ordinal"],
                plan["candidate_id"],
                plan["base_page_json_version_id"],
                plan["physical_page"],
                "PENDING",
                sha256(plan_bytes).hexdigest(),
                plan_bytes,
                None,
            )
            existing = connection.execute(
                "SELECT repair_job_id, family_run_id, document_ordinal, candidate_id, "
                "base_page_json_version_id, physical_page, status, plan_sha256, "
                "plan_bytes, selected_page_json_version_id "
                "FROM family_region_repair_job WHERE repair_job_id=?",
                (plan["repair_job_id"],),
            ).fetchone()
            if existing is None:
                connection.execute(
                    "INSERT INTO family_region_repair_job("
                    "repair_job_id,family_run_id,document_ordinal,candidate_id,"
                    "base_page_json_version_id,physical_page,status,plan_sha256,"
                    "plan_bytes,selected_page_json_version_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    values,
                )
            elif tuple(existing) != values:
                raise _error("family region repair job is already bound differently")
        connection.commit()
    return [plan["repair_job_id"] for plan in checked]


def pending_gemini_family_region_repair_plans_v1(
    path: Path, *, family_run_id: str | None = None
) -> list[dict[str, Any]]:
    """Read pending jobs in stable family/document order for an automated worker."""

    with _connect(path) as connection:
        connection.executescript(_REGION_REPAIR_QUEUE_SCHEMA)
        where = "WHERE j.status='PENDING'"
        parameters: tuple[Any, ...] = ()
        if family_run_id is not None:
            where += " AND j.family_run_id=?"
            parameters = (family_run_id,)
        rows = connection.execute(
            "SELECT j.repair_job_id,j.family_run_id,j.plan_sha256,j.plan_bytes,"
            "(SELECT COUNT(*) FROM family_region_repair_attempt AS a "
            " WHERE a.repair_job_id=j.repair_job_id) AS attempt_count "
            "FROM family_region_repair_job AS j JOIN family_run AS r USING(family_run_id) "
            f"{where} ORDER BY r.family_id,j.document_ordinal,j.repair_job_id",
            parameters,
        ).fetchall()
    result = []
    for row in rows:
        if sha256(row["plan_bytes"]).hexdigest() != row["plan_sha256"]:
            raise _error("family region repair plan bytes do not replay")
        try:
            plan = json.loads(row["plan_bytes"])
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _error("family region repair plan JSON is invalid") from exc
        result.append(
            {
                "attempt_count": row["attempt_count"],
                "family_run_id": row["family_run_id"],
                "next_thinking_level": [
                    plan["repair_policy"]["initial_thinking_level"],
                    *plan["repair_policy"]["thinking_escalation"],
                ][row["attempt_count"]],
                "plan": plan,
                "repair_job_id": row["repair_job_id"],
            }
        )
    return result


def record_gemini_family_region_repair_attempt_v1(
    path: Path,
    *,
    repair_job_id: str,
    thinking_level: str,
    outcome: str,
    page_json_version_id: str | None,
    usage: Mapping[str, Any] | None,
    reasons: Sequence[str],
) -> dict[str, Any]:
    """Append one repair attempt and atomically advance its bounded state machine."""

    allowed_outcomes = {
        "PROVIDER_OR_VALIDATION_FAILURE",
        "RESOLVED",
        "RETRYABLE_VALIDATION_FAILURE",
        "STABLE_SOURCE_EVIDENCE",
    }
    if (
        thinking_level not in {"low", "medium", "high"}
        or outcome not in allowed_outcomes
        or type(reasons) not in {list, tuple}
        or any(type(reason) is not str or not reason for reason in reasons)
        or (outcome in {"RESOLVED", "STABLE_SOURCE_EVIDENCE"}) != (page_json_version_id is not None)
        or (usage is not None and type(usage) is not dict)
    ):
        raise _error("family region repair attempt is invalid")
    with _connect(path) as connection:
        connection.executescript(_REGION_REPAIR_QUEUE_SCHEMA)
        connection.execute("BEGIN IMMEDIATE")
        job = connection.execute(
            "SELECT status,plan_bytes FROM family_region_repair_job WHERE repair_job_id=?",
            (repair_job_id,),
        ).fetchone()
        if job is None or job["status"] not in {"PENDING", "RUNNING"}:
            raise _error("family region repair job is absent or terminal")
        plan = json.loads(job["plan_bytes"])
        levels = [
            plan["repair_policy"]["initial_thinking_level"],
            *plan["repair_policy"]["thinking_escalation"],
        ][: plan["repair_policy"]["max_attempts"]]
        ordinal = (
            connection.execute(
                "SELECT COUNT(*) FROM family_region_repair_attempt WHERE repair_job_id=?",
                (repair_job_id,),
            ).fetchone()[0]
            + 1
        )
        if ordinal > len(levels) or thinking_level != levels[ordinal - 1]:
            raise _error("family region repair thinking escalation does not replay")
        terminal = outcome in {"RESOLVED", "STABLE_SOURCE_EVIDENCE"} or ordinal == len(levels)
        next_status = (
            "RESOLVED"
            if outcome in {"RESOLVED", "STABLE_SOURCE_EVIDENCE"}
            else ("ABSTAINED" if terminal else "PENDING")
        )
        connection.execute(
            "INSERT INTO family_region_repair_attempt("
            "repair_job_id,attempt_ordinal,thinking_level,outcome,page_json_version_id,"
            "usage_json,reason_json) VALUES (?,?,?,?,?,?,?)",
            (
                repair_job_id,
                ordinal,
                thinking_level,
                outcome,
                page_json_version_id,
                None if usage is None else canonical_json_bytes_v1(dict(usage)),
                canonical_json_bytes_v1(list(reasons)),
            ),
        )
        connection.execute(
            "UPDATE family_region_repair_job SET status=?,selected_page_json_version_id=? "
            "WHERE repair_job_id=?",
            (
                next_status,
                page_json_version_id if outcome in {"RESOLVED", "STABLE_SOURCE_EVIDENCE"} else None,
                repair_job_id,
            ),
        )
        connection.commit()
    return {
        "attempt_ordinal": ordinal,
        "next_status": next_status,
        "outcome": outcome,
        "repair_job_id": repair_job_id,
        "thinking_level": thinking_level,
    }


def resolved_gemini_family_region_repair_overlay_v1(
    path: Path, *, family_run_id: str
) -> dict[str, Any]:
    """Load one terminal, traceable repair frontier for a later family rerun."""

    if type(family_run_id) is not str or not family_run_id.startswith("gjfafstorev1:run:"):
        raise _error("family repair overlay run identity is invalid")
    with _connect(path, readonly=True) as connection:
        try:
            run = connection.execute(
                "SELECT family_id FROM family_run WHERE family_run_id=?", (family_run_id,)
            ).fetchone()
            jobs = connection.execute(
                "SELECT repair_job_id,document_ordinal,candidate_id,base_page_json_version_id,"
                "physical_page,status,plan_sha256,plan_bytes,selected_page_json_version_id "
                "FROM family_region_repair_job WHERE family_run_id=? "
                "ORDER BY document_ordinal,physical_page,repair_job_id",
                (family_run_id,),
            ).fetchall()
        except sqlite3.OperationalError as exc:
            raise _error("family repair overlay tables are absent") from exc
        if run is None or not jobs:
            raise _error("family repair overlay run or job frontier is absent")
        if any(job["status"] not in {"RESOLVED", "ABSTAINED"} for job in jobs):
            raise _error("family repair overlay job frontier is not terminal")
        replacements = []
        for job in jobs:
            plan_bytes = job["plan_bytes"]
            if sha256(plan_bytes).hexdigest() != job["plan_sha256"]:
                raise _error("family repair overlay plan bytes do not replay")
            try:
                plan = json.loads(plan_bytes)
            except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _error("family repair overlay plan JSON is invalid") from exc
            material = {key: plan[key] for key in plan if key != "repair_job_id"}
            if (
                plan.get("repair_job_id") != job["repair_job_id"]
                or job["repair_job_id"] != "gjfrrqv1:job:" + canonical_json_sha256_v1(material)
                or plan.get("document_ordinal") != job["document_ordinal"]
                or plan.get("candidate_id") != job["candidate_id"]
                or plan.get("base_page_json_version_id") != job["base_page_json_version_id"]
                or plan.get("physical_page") != job["physical_page"]
            ):
                raise _error("family repair overlay plan identity does not replay")
            if job["status"] == "ABSTAINED":
                if job["selected_page_json_version_id"] is not None:
                    raise _error("abstained family repair unexpectedly selected a page version")
                continue
            selected = job["selected_page_json_version_id"]
            attempt = connection.execute(
                "SELECT outcome,page_json_version_id FROM family_region_repair_attempt "
                "WHERE repair_job_id=? ORDER BY attempt_ordinal DESC LIMIT 1",
                (job["repair_job_id"],),
            ).fetchone()
            if (
                type(selected) is not str
                or not selected.startswith("gfpstorev1:json:")
                or attempt is None
                or attempt["outcome"] not in {"RESOLVED", "STABLE_SOURCE_EVIDENCE"}
                or attempt["page_json_version_id"] != selected
            ):
                raise _error("resolved family repair selected version does not replay")
            replacements.append(
                {
                    "base_page_json_version_id": job["base_page_json_version_id"],
                    "candidate_id": job["candidate_id"],
                    "document_ordinal": job["document_ordinal"],
                    "physical_page": job["physical_page"],
                    "repair_job_id": job["repair_job_id"],
                    "selected_page_json_version_id": selected,
                }
            )
    if len({item["base_page_json_version_id"] for item in replacements}) != len(replacements):
        raise _error("family repair overlay replaces one base page more than once")
    return {
        "family_id": run["family_id"],
        "job_status_counts": {
            status: sum(job["status"] == status for job in jobs)
            for status in ("ABSTAINED", "RESOLVED")
        },
        "repair_source_family_run_id": family_run_id,
        "replacements": replacements,
    }


def _checked_ref(reference: Mapping[str, Any]) -> dict[str, Any]:
    checked = dict(reference)
    if set(checked) != {"path", "sha256", "size_bytes"}:
        raise _error("family implementation/content reference fields drifted")
    if (
        type(checked["path"]) is not str
        or not checked["path"]
        or type(checked["sha256"]) is not str
        or len(checked["sha256"]) != 64
        or type(checked["size_bytes"]) is not int
        or checked["size_bytes"] <= 0
    ):
        raise _error("family implementation/content reference is invalid")
    return checked


def _checked_implementation_refs(
    references: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    checked = [_checked_ref(reference) for reference in references]
    if not checked or len({reference["path"] for reference in checked}) != len(checked):
        raise _error("family implementation reference axis is empty or duplicate")
    return sorted(checked, key=lambda reference: reference["path"])


def _read_authenticated_file_v1(
    path: Path,
    reference: Mapping[str, Any],
    *,
    retain_payload: bool,
) -> bytes | None:
    checked = _checked_ref(reference)
    if path.is_symlink() or not path.is_file():
        raise _error("family authority content is absent, a symlink, or not a regular file")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise _error("family authority content cannot be opened without following links") from exc
    chunks = [] if retain_payload else None
    try:
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size != checked["size_bytes"]:
                raise _error("family authority content reference does not authenticate")
            digest = sha256()
            while block := stream.read(1024 * 1024):
                digest.update(block)
                if chunks is not None:
                    chunks.append(block)
            after = os.fstat(stream.fileno())
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_dev,
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
            ) or digest.hexdigest() != checked["sha256"]:
                raise _error("family authority content reference does not authenticate")
    except BaseException:
        # fdopen owns and closes the descriptor after successful construction.
        raise
    return b"".join(chunks) if chunks is not None else None


def _authenticate_file_ref_v1(path: Path, reference: Mapping[str, Any]) -> None:
    _read_authenticated_file_v1(path, reference, retain_payload=False)


def _authenticated_file_bytes_v1(path: Path, reference: Mapping[str, Any]) -> bytes:
    payload = _read_authenticated_file_v1(path, reference, retain_payload=True)
    assert payload is not None
    return payload


def _artifact_content_path_v1(
    artifact_root: Path,
    reference: Mapping[str, Any],
) -> Path:
    checked = _checked_ref(reference)
    relative = Path(checked["path"])
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise _error("family authority content reference escapes its artifact root")
    root = artifact_root.resolve()
    candidate = root.joinpath(relative)
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise _error("family authority content path crosses a symlink")
    try:
        candidate.resolve().relative_to(root)
    except ValueError as exc:
        raise _error("family authority content reference escapes its artifact root") from exc
    return candidate


def _json_object_bytes_v1(payload: bytes, *, field: str) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"{field} is not valid JSON") from exc
    if type(value) is not dict:
        raise _error(f"{field} is not one JSON object")
    return value


def _selected_corpus_page_frontier_v1(
    *,
    corpus_index_ref: Mapping[str, Any],
    corpus_artifact_root: Path,
    effective_page_artifact_root: Path | None,
    checked_sweep: Mapping[str, Any],
    source_page_database: Path,
) -> list[str]:
    checked_ref = _checked_ref(corpus_index_ref)
    index_path = Path(checked_ref["path"])
    if not index_path.is_absolute():
        raise _error("roll-forward corpus index authority path must be absolute")
    index_payload = _authenticated_file_bytes_v1(index_path, checked_ref)
    try:
        index = validate_current_corpus_manifest_index_v1(
            _json_object_bytes_v1(index_payload, field="roll-forward corpus index authority")
        )
    except ValueError as exc:
        raise _error("roll-forward corpus index authority does not validate") from exc
    if index["corpus_manifest_index_id"] != checked_sweep["corpus_manifest_index_id"]:
        raise _error("roll-forward sweep does not bind the authenticated corpus index")

    root = Path(corpus_artifact_root)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise _error("roll-forward corpus artifact root is not an absolute regular directory")
    root = root.resolve()
    selected_ids: list[str] = []
    for document in index["documents"]:
        manifest_path = _artifact_content_path_v1(root, document["document_manifest_ref"])
        manifest = _json_object_bytes_v1(
            _authenticated_file_bytes_v1(manifest_path, document["document_manifest_ref"]),
            field="selected document manifest authority",
        )
        material = {key: manifest[key] for key in manifest if key != "document_manifest_id"}
        pages = manifest.get("pages")
        source = manifest.get("document")
        if (
            manifest.get("document_manifest_id") != document["document_manifest_id"]
            or manifest.get("document_manifest_id")
            != "gfdmv1:manifest:" + canonical_json_sha256_v1(material)
            or manifest.get("page_count") != document["page_count"]
            or type(pages) is not list
            or len(pages) != document["page_count"]
            or canonical_json_sha256_v1(pages) != document["page_json_frontier_sha256"]
            or type(source) is not dict
            or source.get("source_logical_name") != document["relative_path"]
            or source.get("source_sha256") != document["source_sha256"]
        ):
            raise _error("selected document manifest identity or page axis drifted")
        document_ids = [page.get("page_json_version_id") for page in pages]
        physical_pages = [page.get("physical_page") for page in pages]
        if (
            any(
                type(version_id) is not str or not version_id.startswith("gfpstorev1:json:")
                for version_id in document_ids
            )
            or len(set(document_ids)) != len(document_ids)
            or any(type(page) is not int or page <= 0 for page in physical_pages)
            or physical_pages != sorted(set(physical_pages))
        ):
            raise _error("selected document manifest JSON version axis is incomplete")
        selected_ids.extend(document_ids)
    if len(selected_ids) != index["summary"]["page_count"] or len(set(selected_ids)) != len(
        selected_ids
    ):
        raise _error("selected corpus JSON version frontier is incomplete or duplicate")

    expected_database_ref = index["database_ref"]
    database_artifact_root = root
    effective_frontier = checked_sweep.get("effective_page_frontier")
    if effective_frontier is not None:
        try:
            checked_frontier, selected_ids = apply_gemini_family_effective_page_frontier_v1(
                effective_frontier,
                base_page_json_version_ids=selected_ids,
            )
        except ValueError as exc:
            raise _error("roll-forward effective page frontier does not replay") from exc
        if (
            checked_frontier["base_corpus_manifest_index_id"] != index["corpus_manifest_index_id"]
            or checked_frontier["family_id"] != checked_sweep["family_id"]
        ):
            raise _error("roll-forward effective page frontier binds another corpus or family")
        expected_database_ref = effective_page_frontier_stages_v1(checked_frontier)[-1][
            "database_ref"
        ]
        if effective_page_artifact_root is not None:
            candidate_root = Path(effective_page_artifact_root)
            if (
                not candidate_root.is_absolute()
                or candidate_root.is_symlink()
                or not candidate_root.is_dir()
            ):
                raise _error("effective page artifact root is not an absolute regular directory")
            database_artifact_root = candidate_root.resolve()
    elif effective_page_artifact_root is not None:
        raise _error("effective page artifact root requires an effective page frontier")

    authenticated_database = _artifact_content_path_v1(
        database_artifact_root, expected_database_ref
    )
    _authenticate_file_ref_v1(authenticated_database, expected_database_ref)
    # A runner may query an immutable private snapshot instead of reopening the
    # corpus pathname.  Exact bytes, not pathname identity, are the authority.
    _authenticate_file_ref_v1(source_page_database, expected_database_ref)
    return selected_ids


def ingest_gemini_accounting_family_sweep_v1(
    path: Path,
    *,
    sweep: Mapping[str, Any],
    corpus_index_ref: Mapping[str, Any],
    implementation_refs: Sequence[Mapping[str, Any]],
    run_kind: str,
    source_page_database: Path | None = None,
    selected_page_json_version_ids: Sequence[str] | None = None,
    corpus_artifact_root: Path | None = None,
    effective_page_artifact_root: Path | None = None,
) -> dict[str, Any]:
    """Store one validated sweep and every trace row in one SQLite transaction."""

    if run_kind not in {"EXPERIMENTAL", "OFFICIAL"}:
        raise _error("family run kind must be EXPERIMENTAL or OFFICIAL")
    checked_sweep = validate_gemini_json_flat_family_sweep_v1(dict(sweep))
    source_replay_format = checked_sweep["format_version"]
    if source_replay_format in {
        "GEMINI_JSON_CUSTOMER_DEPOSIT_ACCOUNTING_FAMILY_V1",
        "GEMINI_JSON_DUAL_COMPONENT_ACCOUNTING_FAMILY_V1",
        "GEMINI_JSON_EQUITY_MATRIX_ACCOUNTING_FAMILY_V1",
        "GEMINI_JSON_FIXED_ASSET_ROLLFORWARD_ACCOUNTING_FAMILY_V1",
        "GEMINI_JSON_INVESTMENT_SECURITIES_ACCOUNTING_FAMILY_V1",
        "GEMINI_JSON_MULTITABLE_HIERARCHICAL_ACCOUNTING_FAMILY_V1",
        "GEMINI_JSON_OTHER_LONG_TERM_INVESTMENTS_ACCOUNTING_FAMILY_V1",
        "GEMINI_JSON_ROLLFORWARD_ACCOUNTING_FAMILY_V1",
    }:
        if (
            source_page_database is None
            or corpus_artifact_root is None
            or type(selected_page_json_version_ids) not in {list, tuple}
            or not selected_page_json_version_ids
            or len(set(selected_page_json_version_ids)) != len(selected_page_json_version_ids)
        ):
            raise _error("source-replayed family ingest requires its canonical page frontier")

        compiled_specs = compile_gemini_json_flat_family_specs_v1(
            checked_sweep["specs"]["topology"]["value"],
            checked_sweep["specs"]["evaluation"]["value"],
            checked_sweep["specs"]["schema_binding"]["value"],
        )
        try:
            authoritative_selected_ids = _selected_corpus_page_frontier_v1(
                corpus_index_ref=corpus_index_ref,
                corpus_artifact_root=corpus_artifact_root,
                effective_page_artifact_root=effective_page_artifact_root,
                checked_sweep=checked_sweep,
                source_page_database=source_page_database,
            )
            if list(selected_page_json_version_ids) != authoritative_selected_ids:
                raise _error("caller page frontier differs from authenticated corpus authority")
            if source_replay_format == "GEMINI_JSON_EQUITY_MATRIX_ACCOUNTING_FAMILY_V1":
                from bctc_ai.storage.gemini_financial_page_store_v1 import (
                    validate_selected_equity_matrix_family_candidate_replays_v1,
                )

                validate_selected_equity_matrix_family_candidate_replays_v1(
                    source_page_database,
                    selected_page_json_version_ids=authoritative_selected_ids,
                    compiled_specs=compiled_specs,
                    indexed_query_evidence=checked_sweep["indexed_query_evidence"],
                    trials=checked_sweep["trials"],
                )
            elif source_replay_format == "GEMINI_JSON_CUSTOMER_DEPOSIT_ACCOUNTING_FAMILY_V1":
                from bctc_ai.storage.gemini_financial_page_store_v1 import (
                    validate_selected_customer_deposit_family_candidate_replays_v1,
                )

                validate_selected_customer_deposit_family_candidate_replays_v1(
                    source_page_database,
                    selected_page_json_version_ids=authoritative_selected_ids,
                    compiled_specs=compiled_specs,
                    indexed_query_evidence=checked_sweep["indexed_query_evidence"],
                    trials=checked_sweep["trials"],
                )
            elif source_replay_format == "GEMINI_JSON_INVESTMENT_SECURITIES_ACCOUNTING_FAMILY_V1":
                from bctc_ai.storage.gemini_financial_page_store_v1 import (
                    validate_selected_investment_securities_family_candidate_replays_v1,
                )

                validate_selected_investment_securities_family_candidate_replays_v1(
                    source_page_database,
                    selected_page_json_version_ids=authoritative_selected_ids,
                    compiled_specs=compiled_specs,
                    indexed_query_evidence=checked_sweep["indexed_query_evidence"],
                    trials=checked_sweep["trials"],
                )
            elif (
                source_replay_format
                == "GEMINI_JSON_OTHER_LONG_TERM_INVESTMENTS_ACCOUNTING_FAMILY_V1"
            ):
                from bctc_ai.storage.gemini_financial_page_store_v1 import (
                    validate_selected_other_long_term_investments_family_candidate_replays_v1,
                )

                validate_selected_other_long_term_investments_family_candidate_replays_v1(
                    source_page_database,
                    selected_page_json_version_ids=authoritative_selected_ids,
                    compiled_specs=compiled_specs,
                    indexed_query_evidence=checked_sweep["indexed_query_evidence"],
                    trials=checked_sweep["trials"],
                )
            elif source_replay_format == "GEMINI_JSON_MULTITABLE_HIERARCHICAL_ACCOUNTING_FAMILY_V1":
                from bctc_ai.storage.gemini_financial_page_store_v1 import (
                    validate_selected_multitable_hierarchical_family_candidate_replays_v1,
                )

                validate_selected_multitable_hierarchical_family_candidate_replays_v1(
                    source_page_database,
                    selected_page_json_version_ids=authoritative_selected_ids,
                    compiled_specs=compiled_specs,
                    indexed_query_evidence=checked_sweep["indexed_query_evidence"],
                    trials=checked_sweep["trials"],
                )
            elif source_replay_format == "GEMINI_JSON_ROLLFORWARD_ACCOUNTING_FAMILY_V1":
                from bctc_ai.storage.gemini_financial_page_store_v1 import (
                    validate_selected_rollforward_family_query_evidence_v1,
                )

                validate_selected_rollforward_family_query_evidence_v1(
                    source_page_database,
                    selected_page_json_version_ids=authoritative_selected_ids,
                    compiled_specs=compiled_specs,
                    indexed_query_evidence=checked_sweep["indexed_query_evidence"],
                    trials=checked_sweep["trials"],
                )
            elif source_replay_format == "GEMINI_JSON_FIXED_ASSET_ROLLFORWARD_ACCOUNTING_FAMILY_V1":
                from bctc_ai.storage.gemini_financial_page_store_v1 import (
                    validate_selected_fixed_asset_rollforward_family_candidate_replays_v1,
                )

                validate_selected_fixed_asset_rollforward_family_candidate_replays_v1(
                    source_page_database,
                    selected_page_json_version_ids=authoritative_selected_ids,
                    compiled_specs=compiled_specs,
                    indexed_query_evidence=checked_sweep["indexed_query_evidence"],
                    trials=checked_sweep["trials"],
                )
            else:
                from bctc_ai.storage.gemini_financial_page_store_v1 import (
                    validate_selected_dual_component_family_candidate_replays_v1,
                )

                validate_selected_dual_component_family_candidate_replays_v1(
                    source_page_database,
                    selected_page_json_version_ids=authoritative_selected_ids,
                    compiled_specs=compiled_specs,
                    indexed_query_evidence=checked_sweep["indexed_query_evidence"],
                    trials=checked_sweep["trials"],
                )
        except GeminiAccountingFamilyStoreV1Error:
            raise
        except (RuntimeError, ValueError) as exc:
            raise _error(
                "family selected query and candidates do not replay from page store"
            ) from exc
    checked_index_ref = _checked_ref(corpus_index_ref)
    checked_implementation = _checked_implementation_refs(implementation_refs)
    if not path.exists():
        initialize_gemini_accounting_family_store_v1(path)

    sweep_bytes = canonical_json_bytes_v1(checked_sweep) + b"\n"
    implementation_bytes = canonical_json_bytes_v1(checked_implementation)
    implementation_axis_sha256 = sha256(implementation_bytes).hexdigest()
    family_run_id = "gjfafstorev1:run:" + canonical_json_sha256_v1(
        {
            "corpus_index_sha256": checked_index_ref["sha256"],
            "implementation_axis_sha256": implementation_axis_sha256,
            "sweep_id": checked_sweep["sweep_id"],
            "sweep_sha256": sha256(sweep_bytes).hexdigest(),
        }
    )
    metrics = checked_sweep["metrics"]
    specs = checked_sweep["specs"]
    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        existing = connection.execute(
            "SELECT sweep_sha256, sweep_bytes FROM family_run WHERE family_run_id=?",
            (family_run_id,),
        ).fetchone()
        if existing is None:
            connection.execute(
                "INSERT INTO family_run VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    family_run_id,
                    checked_sweep["sweep_id"],
                    checked_sweep["family_id"],
                    checked_sweep["format_version"],
                    checked_sweep["corpus_manifest_index_id"],
                    checked_index_ref["sha256"],
                    specs["topology"]["sha256"],
                    specs["evaluation"]["sha256"],
                    specs["schema_binding"]["sha256"],
                    implementation_axis_sha256,
                    implementation_bytes,
                    sha256(sweep_bytes).hexdigest(),
                    sweep_bytes,
                    metrics["document_count"],
                    metrics["ready_count"],
                    metrics["not_observed_count"],
                    metrics["unresolved_count"],
                    metrics["mapping_count"],
                ),
            )
            for trial in checked_sweep["trials"]:
                trial_bytes = canonical_json_bytes_v1(trial)
                ordinal = trial["document_ordinal"]
                connection.execute(
                    "INSERT INTO family_trial VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        family_run_id,
                        ordinal,
                        trial["source_logical_name"],
                        trial["source_sha256"],
                        trial["status"],
                        trial["candidate_count"],
                        trial["selected_candidate_id"],
                        len(trial["mappings"]),
                        canonical_json_bytes_v1(trial["reasons"]),
                        sha256(trial_bytes).hexdigest(),
                        trial_bytes,
                    ),
                )
                for candidate in trial["candidates"]:
                    candidate_bytes = canonical_json_bytes_v1(candidate)
                    connection.execute(
                        "INSERT INTO family_candidate VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            family_run_id,
                            ordinal,
                            candidate["candidate_id"],
                            candidate["page_json_version_id"],
                            candidate["physical_page"],
                            candidate["section_id"],
                            candidate["table_id"],
                            candidate["status"],
                            len(candidate["reasons"]),
                            len(candidate["mappings"]),
                            sha256(candidate_bytes).hexdigest(),
                            candidate_bytes,
                        ),
                    )
                for mapping_ordinal, mapping in enumerate(trial["mappings"], start=1):
                    mapping_bytes = canonical_json_bytes_v1(mapping)
                    mapping_role = mapping.get("role", mapping.get("movement_role"))
                    if (
                        type(mapping_role) is not str
                        or not mapping_role
                        or (
                            "role" in mapping
                            and "movement_role" in mapping
                            and mapping["role"] != mapping["movement_role"]
                        )
                    ):
                        raise _error("family mapping has no typed role identity")
                    connection.execute(
                        "INSERT INTO family_mapping VALUES (?,?,?,?,?,?,?,?)",
                        (
                            family_run_id,
                            ordinal,
                            mapping_ordinal,
                            mapping["report_norm_id"],
                            mapping_role,
                            mapping["row_id"],
                            sha256(mapping_bytes).hexdigest(),
                            mapping_bytes,
                        ),
                    )
        elif (
            existing["sweep_sha256"] != sha256(sweep_bytes).hexdigest()
            or bytes(existing["sweep_bytes"]) != sweep_bytes
        ):
            raise _error("family run ID is already bound to different sweep bytes")

        connection.execute(
            "INSERT INTO family_run_execution(family_run_id, run_kind) VALUES (?,?)",
            (family_run_id, run_kind),
        )
        if run_kind == "OFFICIAL":
            prior = connection.execute(
                "SELECT family_run_id FROM family_current_selection WHERE family_id=?",
                (checked_sweep["family_id"],),
            ).fetchone()
            prior_id = prior[0] if prior is not None else None
            connection.execute(
                "INSERT OR IGNORE INTO family_selection_event"
                "(family_id, prior_family_run_id, next_family_run_id) VALUES (?,?,?)",
                (checked_sweep["family_id"], prior_id, family_run_id),
            )
            connection.execute(
                "INSERT INTO family_current_selection VALUES (?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now')) "
                "ON CONFLICT(family_id) DO UPDATE SET family_run_id=excluded.family_run_id, "
                "selected_at_utc=excluded.selected_at_utc",
                (checked_sweep["family_id"], family_run_id),
            )
        connection.commit()
    return {
        "family_run_id": family_run_id,
        "family_id": checked_sweep["family_id"],
        "run_kind": run_kind,
        "sweep_id": checked_sweep["sweep_id"],
        "sweep_sha256": sha256(sweep_bytes).hexdigest(),
    }


def load_gemini_accounting_family_sweep_v1(path: Path, family_run_id: str) -> dict[str, Any]:
    """Load and revalidate one exact family sweep from its database identity."""

    with _connect(path, readonly=True) as connection:
        row = connection.execute(
            "SELECT sweep_sha256, sweep_bytes FROM family_run WHERE family_run_id=?",
            (family_run_id,),
        ).fetchone()
    if row is None:
        raise _error("family run is absent")
    payload = bytes(row["sweep_bytes"])
    if sha256(payload).hexdigest() != row["sweep_sha256"]:
        raise _error("stored family sweep hash drifted")
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("stored family sweep JSON is invalid") from exc
    return validate_gemini_json_flat_family_sweep_v1(value)


def record_gemini_accounting_family_export_v1(
    path: Path,
    *,
    family_run_id: str,
    output_path: Path,
) -> dict[str, Any]:
    """Bind one materialized JSON export back to its stored family run."""

    if output_path.is_symlink() or not output_path.is_file():
        raise _error("family export is absent or not regular")
    payload = output_path.read_bytes()
    with _connect(path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        run = connection.execute(
            "SELECT sweep_sha256, sweep_bytes FROM family_run WHERE family_run_id=?",
            (family_run_id,),
        ).fetchone()
        if run is None:
            raise _error("family export does not equal its stored sweep")
        stored_payload = bytes(run["sweep_bytes"])
        if stored_payload != payload:
            try:
                exported = validate_gemini_json_flat_family_sweep_v1(json.loads(payload))
                stored = validate_gemini_json_flat_family_sweep_v1(json.loads(stored_payload))
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                raise _error("family export does not equal its stored sweep") from exc
            canonical_export = canonical_json_bytes_v1(exported)
            if payload != canonical_export or canonical_json_bytes_v1(stored) != canonical_export:
                raise _error("family export does not equal its stored sweep")
        connection.execute(
            "INSERT OR IGNORE INTO family_export"
            "(family_run_id, output_path, output_sha256, output_size_bytes) VALUES (?,?,?,?)",
            (family_run_id, str(output_path.resolve()), sha256(payload).hexdigest(), len(payload)),
        )
        connection.commit()
    return {
        "output_path": str(output_path.resolve()),
        "sha256": sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def gemini_accounting_family_store_summary_v1(path: Path) -> dict[str, Any]:
    """Return compact current/history counts without reading loose exports."""

    with _connect(path, readonly=True) as connection:
        totals = connection.execute(
            "SELECT COUNT(*) runs, COUNT(DISTINCT family_id) families, "
            "COALESCE(SUM(document_count),0) documents, COALESCE(SUM(mapping_count),0) mappings "
            "FROM family_run"
        ).fetchone()
        current = connection.execute(
            "SELECT c.family_id, c.family_run_id, r.sweep_id, r.ready_count, "
            "r.not_observed_count, r.unresolved_count, r.mapping_count "
            "FROM family_current_selection c JOIN family_run r USING(family_run_id) "
            "ORDER BY c.family_id"
        ).fetchall()
    return {
        "current": [dict(row) for row in current],
        "documents_across_runs": totals["documents"],
        "family_count": totals["families"],
        "mapping_count_across_runs": totals["mappings"],
        "run_count": totals["runs"],
    }


def canonical_family_store_record_v1(value: Any) -> dict[str, Any]:
    """Expose the canonical-clone helper for small tooling without DB objects."""

    return canonical_clone_v1(value)
