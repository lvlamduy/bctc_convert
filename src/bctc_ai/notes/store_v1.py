"""Write-once SQLite store for notes pilot results, with exact reload.

One row per evaluated cell (accepted, blank, held, control), its locator and
hold reasons; one run manifest. Accepted cells have a unique write key, so a
second accepted value for the same (document, scope, concept, axis, member,
basis, period) cannot be stored. ``reload_notes_store_v1`` re-reads every
cell and re-hashes the projection; any edit to a stored cell or to the
manifest is detected.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

NOTES_STORE_FORMAT = "NOTES_PILOT_RESULT_STORE_V1"

_SCHEMA = """
CREATE TABLE store_identity (
  singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
  format_version TEXT NOT NULL,
  manifest_sha256 TEXT NOT NULL,
  manifest_json TEXT NOT NULL,
  cells_sha256 TEXT NOT NULL
) STRICT;
CREATE TABLE note_cell (
  cell_ordinal INTEGER PRIMARY KEY,
  document_ordinal INTEGER NOT NULL,
  document_plan_id TEXT NOT NULL,
  family TEXT NOT NULL,
  scope TEXT,
  concept TEXT,
  axis TEXT NOT NULL,
  member TEXT NOT NULL,
  classification_basis TEXT NOT NULL,
  period_key TEXT,
  unit TEXT,
  observation_state TEXT NOT NULL,
  value_text TEXT,
  raw_text TEXT,
  acceptance TEXT NOT NULL CHECK (acceptance IN ('ACCEPTED','ACCEPTED_BLANK','HOLD','DUPLICATE_IDENTICAL_CONTROL')),
  report_norm_id INTEGER,
  cell_json TEXT NOT NULL
) STRICT;
CREATE UNIQUE INDEX note_cell_accepted_write_key ON note_cell(
  document_plan_id, scope, concept, axis, member, classification_basis, period_key
) WHERE acceptance IN ('ACCEPTED', 'ACCEPTED_BLANK');
"""


class NotesStoreError(ValueError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def cells_projection_sha256_v1(cells: list[dict[str, Any]]) -> str:
    return hashlib.sha256(_canonical(cells).encode("utf-8")).hexdigest()


def write_notes_store_v1(path: Path, *, manifest: dict[str, Any], cells: list[dict[str, Any]]) -> dict[str, Any]:
    if path.exists():
        raise NotesStoreError(f"store already exists (write-once): {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest_json = _canonical(manifest)
    cells_sha = cells_projection_sha256_v1(cells)
    with closing(sqlite3.connect(path)) as connection:
        connection.executescript(_SCHEMA)
        connection.execute("INSERT INTO store_identity VALUES (1, ?, ?, ?, ?)",
                           (NOTES_STORE_FORMAT, hashlib.sha256(manifest_json.encode()).hexdigest(), manifest_json, cells_sha))
        try:
            connection.executemany(
                "INSERT INTO note_cell VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [(index, c["document_ordinal"], c["document_plan_id"], c["family"], c["scope"], c["concept"], c["axis"],
                  c["member"], c["classification_basis"], c["period_key"], c["unit"], c["observation_state"], c["value"],
                  c["raw"], c["acceptance"], c.get("report_norm_id"), _canonical(c)) for index, c in enumerate(cells)],
            )
        except sqlite3.IntegrityError as error:
            raise NotesStoreError(f"two accepted cells share a write key: {error}") from error
        connection.commit()
        check = connection.execute("PRAGMA quick_check").fetchone()[0]
    return {"path": str(path), "format_version": NOTES_STORE_FORMAT, "cells": len(cells), "cells_sha256": cells_sha,
            "quick_check": check, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "size_bytes": path.stat().st_size}


def reload_notes_store_v1(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with closing(sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)) as connection:
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise NotesStoreError("store quick_check failed")
        identity = connection.execute(
            "SELECT format_version, manifest_sha256, manifest_json, cells_sha256 FROM store_identity").fetchone()
        rows = connection.execute("SELECT cell_json, value_text, acceptance, period_key, member FROM note_cell ORDER BY cell_ordinal").fetchall()
    if identity is None or identity[0] != NOTES_STORE_FORMAT:
        raise NotesStoreError("store identity missing or of another format")
    if hashlib.sha256(identity[2].encode()).hexdigest() != identity[1]:
        raise NotesStoreError("run manifest was edited")
    cells = []
    for cell_json, value_text, acceptance, period_key, member in rows:
        cell = json.loads(cell_json)
        if (cell["value"], cell["acceptance"], cell["period_key"], cell["member"]) != (value_text, acceptance, period_key, member):
            raise NotesStoreError("a stored cell column differs from its JSON record")
        cells.append(cell)
    if cells_projection_sha256_v1(cells) != identity[3]:
        raise NotesStoreError("stored cells differ from the recorded projection")
    return json.loads(identity[2]), cells
