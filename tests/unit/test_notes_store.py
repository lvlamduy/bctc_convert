"""Notes pilot store: write-once, unique accepted write key, exact reload, tamper detection."""

from __future__ import annotations

import sqlite3

import pytest

from bctc_ai.notes.store_v1 import NotesStoreError, reload_notes_store_v1, write_notes_store_v1


def cell(value="10", acceptance="ACCEPTED", member="G1", period="INSTANT:2025-06-30"):
    return {"document_ordinal": 1, "document_plan_id": "plan", "family": "CREDIT_QUALITY", "scope": "SEPARATE",
            "concept": "LOANS_TO_CUSTOMERS", "axis": "CREDIT_QUALITY_GROUP", "member": member,
            "classification_basis": "AS_PRESENTED", "period_key": period, "unit": "MILLION_VND",
            "observation_state": "VALUE", "value": value, "raw": value, "acceptance": acceptance,
            "hold_reasons": [], "report_norm_id": 747, "locator": {"physical_page": 3}}


def test_store_round_trip_and_write_once(tmp_path):
    path = tmp_path / "notes.sqlite3"
    cells = [cell(), cell("5", member="G2"), cell(None, "HOLD", member="G3")]
    receipt = write_notes_store_v1(path, manifest={"run": 1}, cells=cells)
    assert receipt["quick_check"] == "ok" and receipt["cells"] == 3
    manifest, reloaded = reload_notes_store_v1(path)
    assert manifest == {"run": 1} and reloaded == cells
    with pytest.raises(NotesStoreError):
        write_notes_store_v1(path, manifest={}, cells=cells)


def test_two_accepted_cells_on_one_write_key_are_refused(tmp_path):
    with pytest.raises(NotesStoreError):
        write_notes_store_v1(tmp_path / "x.sqlite3", manifest={}, cells=[cell("10"), cell("11")])
    # A held duplicate is allowed (it is not exported).
    write_notes_store_v1(tmp_path / "y.sqlite3", manifest={}, cells=[cell("10"), cell("11", "HOLD")])


def test_edited_cell_is_detected_on_reload(tmp_path):
    path = tmp_path / "notes.sqlite3"
    write_notes_store_v1(path, manifest={"run": 1}, cells=[cell()])
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE note_cell SET value_text = '11'")
    with pytest.raises(NotesStoreError):
        reload_notes_store_v1(path)
    path2 = tmp_path / "notes2.sqlite3"
    write_notes_store_v1(path2, manifest={"run": 1}, cells=[cell()])
    with sqlite3.connect(path2) as connection:
        connection.execute("UPDATE note_cell SET cell_json = replace(cell_json, '\"10\"', '\"12\"'), value_text = '12', raw_text = '12'")
    with pytest.raises(NotesStoreError):
        reload_notes_store_v1(path2)
