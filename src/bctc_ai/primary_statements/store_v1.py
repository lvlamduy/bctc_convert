"""Write-once SQLite store for PRIMARY_ONLY document results.

Each run writes a new database file (never next to or into a source DB). The
canonical result JSON of every document is stored with its SHA-256 and content
id, and its cells, item statuses, source rows and checks are projected into
typed tables. ``UNIQUE`` on the write key (document, scope, statement, period,
ReportNormId) rejects duplicates at the database level even if equal. Reload
re-hashes every stored document and re-derives every projection row from the
stored JSON, so a row edited in place (and re-hashed) is detected.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1, canonical_json_sha256_v1

STORE_FORMAT_VERSION = "PRIMARY_ONLY_RESULT_STORE_V1"

_SCHEMA = """
CREATE TABLE store_identity (
  singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
  format_version TEXT NOT NULL,
  run_manifest_sha256 TEXT NOT NULL,
  run_manifest_json BLOB NOT NULL
) STRICT;
CREATE TABLE document_result (
  document_ordinal INTEGER PRIMARY KEY,
  document_plan_id TEXT NOT NULL UNIQUE,
  relative_path TEXT NOT NULL,
  source_sha256 TEXT NOT NULL,
  result_id TEXT NOT NULL UNIQUE,
  result_sha256 TEXT NOT NULL,
  result_json BLOB NOT NULL
) STRICT;
CREATE TABLE mapped_cell (
  document_plan_id TEXT NOT NULL REFERENCES document_result(document_plan_id),
  scope TEXT,
  statement TEXT NOT NULL,
  period_key TEXT,
  report_norm_id INTEGER NOT NULL,
  lane INTEGER NOT NULL,
  instance_key TEXT NOT NULL,
  row_uid TEXT NOT NULL,
  observation_state TEXT NOT NULL,
  value_text TEXT,
  raw_text TEXT,
  unit TEXT,
  acceptance TEXT NOT NULL CHECK (acceptance IN ('ACCEPTED','ACCEPTED_BLANK','HOLD')),
  hold_reasons_json TEXT NOT NULL,
  page_json_version_id TEXT NOT NULL,
  physical_page INTEGER NOT NULL,
  section_ordinal INTEGER NOT NULL,
  table_ordinal INTEGER NOT NULL,
  row_ordinal INTEGER NOT NULL,
  column_ordinal INTEGER NOT NULL
) STRICT;
CREATE UNIQUE INDEX mapped_cell_write_key ON mapped_cell(
  document_plan_id, scope, statement, period_key, report_norm_id
) WHERE acceptance != 'HOLD';
CREATE TABLE item_status (
  document_plan_id TEXT NOT NULL REFERENCES document_result(document_plan_id),
  instance_key TEXT NOT NULL,
  statement TEXT NOT NULL,
  scope TEXT,
  report_norm_id INTEGER NOT NULL,
  display_order INTEGER NOT NULL,
  status TEXT NOT NULL,
  reason TEXT,
  PRIMARY KEY (document_plan_id, instance_key, report_norm_id)
) STRICT;
CREATE TABLE source_row (
  document_plan_id TEXT NOT NULL REFERENCES document_result(document_plan_id),
  instance_key TEXT NOT NULL,
  row_uid TEXT NOT NULL,
  disposition TEXT NOT NULL,
  reason TEXT NOT NULL,
  report_norm_id INTEGER,
  label_exact TEXT,
  PRIMARY KEY (document_plan_id, instance_key, row_uid)
) STRICT;
CREATE TABLE equation_check (
  document_plan_id TEXT NOT NULL REFERENCES document_result(document_plan_id),
  instance_key TEXT NOT NULL,
  equation_id TEXT NOT NULL,
  lane INTEGER NOT NULL,
  status TEXT NOT NULL,
  residual TEXT,
  PRIMARY KEY (document_plan_id, instance_key, equation_id, lane)
) STRICT;
CREATE INDEX mapped_cell_acceptance ON mapped_cell(acceptance, statement);
CREATE INDEX item_status_status ON item_status(status, statement);
"""


class PrimaryStoreError(ValueError):
    """The result store does not replay exactly."""


def _projection(result: dict[str, Any]) -> dict[str, list[tuple]]:
    plan = result["document"]["document_plan_id"]
    cells = [
        (plan, c["scope"], c["statement"], c["period_key"], c["report_norm_id"], c["lane"], c["instance_key"],
         c["row_uid"], c["observation_state"], c["value"], c["raw"], c["unit"], c["acceptance"],
         json.dumps(c["hold_reasons"], ensure_ascii=False), c["locator"]["page_json_version_id"],
         c["locator"]["physical_page"], c["locator"]["section_ordinal"], c["locator"]["table_ordinal"],
         c["locator"]["row_ordinal"], c["locator"]["column_ordinal"])
        for c in result["cells"]
    ]
    items = [
        (plan, i["instance_key"], i["statement"], i["scope"], i["report_norm_id"], i["display_order"],
         i["status"], i["reason"])
        for i in result["item_status"]
    ]
    rows = [
        (plan, instance["instance_key"], row["row_uid"], row["disposition"], row["reason"],
         row["report_norm_id"], row["label_exact"])
        for instance in result["instances"] for row in instance["source_rows"]
    ]
    checks = [
        (plan, instance["instance_key"], check["equation_id"], check["lane"], check["status"], check["residual"])
        for instance in result["instances"] for check in instance["validations"]
    ]
    return {"mapped_cell": cells, "item_status": items, "source_row": rows, "equation_check": checks}


_COLUMNS = {
    "mapped_cell": 20, "item_status": 8, "source_row": 7, "equation_check": 6,
}


def write_result_store_v1(path: Path, *, run_manifest: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    if path.exists():
        raise PrimaryStoreError("result store already exists; every run writes a new store")
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest_bytes = canonical_json_bytes_v1(run_manifest)
    with closing(sqlite3.connect(path)) as connection:
        connection.executescript(_SCHEMA)
        connection.execute(
            "INSERT INTO store_identity VALUES (1,?,?,?)",
            (STORE_FORMAT_VERSION, hashlib.sha256(manifest_bytes).hexdigest(), manifest_bytes),
        )
        for result in results:
            raw = canonical_json_bytes_v1(result)
            document = result["document"]
            connection.execute(
                "INSERT INTO document_result VALUES (?,?,?,?,?,?,?)",
                (document["document_ordinal"], document["document_plan_id"], document["relative_path"],
                 document["source_sha256"], result["result_id"], hashlib.sha256(raw).hexdigest(), raw),
            )
            for table, rows in _projection(result).items():
                placeholders = ",".join("?" * _COLUMNS[table])
                connection.executemany(f"INSERT INTO {table} VALUES ({placeholders})", rows)
        connection.commit()
        quick = connection.execute("PRAGMA quick_check").fetchall()
        foreign = connection.execute("PRAGMA foreign_key_check").fetchall()
    if quick != [("ok",)] or foreign:
        raise PrimaryStoreError("result store integrity check failed")
    raw = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw),
            "documents": len(results), "quick_check": "ok", "foreign_key_violations": 0}


def reload_result_store_v1(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Re-hash every document result and re-derive every projection row."""

    with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True)) as connection:
        identity = connection.execute("SELECT format_version, run_manifest_sha256, run_manifest_json FROM store_identity").fetchone()
        if identity is None or identity[0] != STORE_FORMAT_VERSION or hashlib.sha256(identity[2]).hexdigest() != identity[1]:
            raise PrimaryStoreError("result store identity does not replay")
        manifest = json.loads(identity[2])
        results = []
        for ordinal, plan, path_text, source_sha, result_id, digest, raw in connection.execute(
            "SELECT * FROM document_result ORDER BY document_ordinal"
        ):
            if hashlib.sha256(raw).hexdigest() != digest:
                raise PrimaryStoreError(f"document result bytes drifted: {ordinal}")
            result = json.loads(raw)
            if canonical_json_bytes_v1(result) != raw:
                raise PrimaryStoreError(f"document result is not canonical: {ordinal}")
            body = {key: value for key, value in result.items() if key != "result_id"}
            if result.get("result_id") != result_id or result_id != "primaryresultv1:" + canonical_json_sha256_v1(body):
                raise PrimaryStoreError(f"document result id does not replay: {ordinal}")
            if result["document"]["document_plan_id"] != plan or result["document"]["source_sha256"] != source_sha \
                    or result["document"]["relative_path"] != path_text:
                raise PrimaryStoreError(f"document result binding drifted: {ordinal}")
            results.append(result)
        expected: dict[str, set] = {table: set() for table in _COLUMNS}
        for result in results:
            for table, rows in _projection(result).items():
                for row in rows:
                    if row in expected[table]:
                        raise PrimaryStoreError(f"projection duplicates a row in {table}")
                    expected[table].add(row)
        for table in _COLUMNS:
            stored = connection.execute(f"SELECT * FROM {table}").fetchall()
            if len(stored) != len(expected[table]) or set(stored) != expected[table]:
                raise PrimaryStoreError(f"projection table {table} does not replay from stored results")
    return manifest, results
