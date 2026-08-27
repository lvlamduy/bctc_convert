"""Traceable SQLite store for derived Gemini JSON-first accounting families."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
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


def ingest_gemini_accounting_family_sweep_v1(
    path: Path,
    *,
    sweep: Mapping[str, Any],
    corpus_index_ref: Mapping[str, Any],
    implementation_refs: Sequence[Mapping[str, Any]],
    run_kind: str,
) -> dict[str, Any]:
    """Store one validated sweep and every trace row in one SQLite transaction."""

    if run_kind not in {"EXPERIMENTAL", "OFFICIAL"}:
        raise _error("family run kind must be EXPERIMENTAL or OFFICIAL")
    checked_sweep = validate_gemini_json_flat_family_sweep_v1(dict(sweep))
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
                    connection.execute(
                        "INSERT INTO family_mapping VALUES (?,?,?,?,?,?,?,?)",
                        (
                            family_run_id,
                            ordinal,
                            mapping_ordinal,
                            mapping["report_norm_id"],
                            mapping["role"],
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
        if run is None or bytes(run["sweep_bytes"]) != payload:
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
