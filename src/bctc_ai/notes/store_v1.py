"""Write-once SQLite store for notes pilot results, with exact reload.

One row per evaluated cell (accepted, blank, held, control), its locator and
hold reasons; one run manifest. Accepted cells have a unique write key, so a
second accepted value for the same (document, scope, concept, axis, member,
basis, period) cannot be stored. ``reload_notes_store_v1`` re-reads every
cell and re-hashes the projection; any edit to a stored cell or to the
manifest is detected: every normalized column, the contiguous ordinal and the
canonical JSON must agree with the record, and the schema must be exactly the
notes store schema (Codex 0222).
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
  acceptance TEXT NOT NULL CHECK (acceptance IN ('ACCEPTED','ACCEPTED_DASH','ACCEPTED_BLANK','HOLD',
                                                'DUPLICATE_IDENTICAL_CONTROL')),
  report_norm_id INTEGER,
  cell_json TEXT NOT NULL
) STRICT;
CREATE UNIQUE INDEX note_cell_accepted_write_key ON note_cell(
  document_plan_id, scope, concept, axis, member, classification_basis, period_key
) WHERE acceptance IN ('ACCEPTED', 'ACCEPTED_DASH', 'ACCEPTED_BLANK');
"""


class NotesStoreError(ValueError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def cells_projection_sha256_v1(cells: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    encoder = json.JSONEncoder(ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    for chunk in encoder.iterencode(cells):
        digest.update(chunk.encode("utf-8"))
    return digest.hexdigest()


def _cell_row_v1(index: int, c: dict[str, Any]) -> tuple[Any, ...]:
    """The one note_cell row projection used by the writer and by the exact reload (Codex 0222)."""

    return (index, c["document_ordinal"], c["document_plan_id"], c["family"], c["scope"], c["concept"], c["axis"],
            c["member"], c["classification_basis"], c["period_key"], c["unit"], c["observation_state"], c["value"],
            c["raw"], c["acceptance"], c.get("report_norm_id"), _canonical(c))


def _schema_objects(connection) -> list[tuple[Any, ...]]:
    return connection.execute("SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name").fetchall()


def _expected_schema_objects() -> list[tuple[Any, ...]]:
    with closing(sqlite3.connect(":memory:")) as connection:
        connection.executescript(_SCHEMA)
        return _schema_objects(connection)


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
                (_cell_row_v1(index, c) for index, c in enumerate(cells)),
            )
        except sqlite3.IntegrityError as error:
            raise NotesStoreError(f"two accepted cells share a write key: {error}") from error
        connection.commit()
        check = connection.execute("PRAGMA quick_check").fetchone()[0]
        foreign = connection.execute("PRAGMA foreign_key_check").fetchall()
    sidecars = [str(path) + suffix for suffix in ("-wal", "-shm", "-journal") if Path(str(path) + suffix).exists()]
    if check != "ok" or foreign or sidecars:
        raise NotesStoreError(f"store integrity barrier failed: quick_check={check} foreign={len(foreign)} sidecars={sidecars}")
    return {"path": str(path), "format_version": NOTES_STORE_FORMAT, "cells": len(cells), "cells_sha256": cells_sha,
            "quick_check": check, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "size_bytes": path.stat().st_size}


def reload_notes_store_v1(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with closing(sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)) as connection:
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise NotesStoreError("store quick_check failed")
        schema = _schema_objects(connection)
        identities = connection.execute(
            "SELECT singleton, format_version, manifest_sha256, manifest_json, cells_sha256 FROM store_identity").fetchall()
        rows = connection.execute("SELECT * FROM note_cell ORDER BY cell_ordinal").fetchall()
    if schema != _expected_schema_objects():
        raise NotesStoreError("store schema differs from the notes store schema (tables, columns, index)")
    if len(identities) != 1 or identities[0][0] != 1 or identities[0][1] != NOTES_STORE_FORMAT:
        raise NotesStoreError("store identity missing or of another format")
    identity = identities[0][1:]
    if hashlib.sha256(identity[2].encode()).hexdigest() != identity[1]:
        raise NotesStoreError("run manifest was edited")
    cells = []
    for index, row in enumerate(rows):
        cell = json.loads(row[-1])
        expected = _cell_row_v1(index, cell)
        # Every normalized column, the contiguous ordinal and the canonical JSON itself, with exact types (Codex 0222).
        if len(row) != len(expected) or any(type(a) is not type(b) or a != b for a, b in zip(row, expected, strict=False)):
            raise NotesStoreError(f"stored cell {index} differs from its canonical JSON record")
        cells.append(cell)
    if cells_projection_sha256_v1(cells) != identity[3]:
        raise NotesStoreError("stored cells differ from the recorded projection")
    return json.loads(identity[2]), cells
