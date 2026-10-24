"""Old-byte hash equivalence and tiny synthetic store integration; no corpus."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from decimal import Decimal

import pytest

from bctc_ai.notes.f36_ledger_projection_v1 import attach_f36_ledger_v1
from bctc_ai.notes.f36_strict_ledger_v1 import classify_observation_v1
from bctc_ai.notes.store_v1 import (
    NotesStoreError,
    cells_projection_sha256_v1,
    reload_notes_store_v1,
    write_notes_store_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1
from test_notes_f36_ledger_projection import REFS
from test_notes_f36_strict_ledger import CLOSED, cell, inventory_row


def _old_digest(cells):
    # The exact pre-change whole-buffer policy, independent of the new encoder loop.
    old_bytes = json.dumps(cells, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(old_bytes).hexdigest()


@pytest.mark.parametrize("cells", [
    [],
    [{"label": "Chi phí hoạt động — Ngân hàng", "raw": "(1.234)", "line": "năm\ntrước"}],
    [{"z": [None, True, False, {}, [], {"x": -3}], "a": {"nested": ["", "\\n", "\t"]}}],
    [{"large": 2**100, "negative": -(2**100), "zero": 0}],
    [{"floats": [0.1, -0.0, 1e-9, 1.2345678901234567, 1e30]}],
    [{"decimal_default_str": Decimal("1.2300"), "tuple": (1, None, "x"), "nfd": "a\u0301", "nfc": "á"}, {}],
])
def test_streaming_projection_matches_the_exact_old_canonical_byte_hash(cells):
    assert cells_projection_sha256_v1(cells) == _old_digest(cells)


def _cells():
    return [cell(raw="8", value="8"),
            cell("RENT_EXPENSE", "1.250", None, row=2, value="1250"),
            cell("ASSET_EXPENSE", None, 1212, row=3, acceptance="HOLD", observation_state="BLANK",
                 value=None, hold_reasons=["SOURCE_INCOMPLETE"]),
            cell(row=4, acceptance="DUPLICATE_IDENTICAL_CONTROL", value="8", raw="8")]


def test_empty_store_still_has_the_old_empty_projection_and_exact_reload(tmp_path):
    path = tmp_path / "empty.sqlite3"
    manifest = {"synthetic": True, "canonical_acceptance_granted": False}
    receipt = write_notes_store_v1(path, manifest=manifest, cells=[])
    assert receipt["cells_sha256"] == _old_digest([]) and receipt["cells"] == 0
    assert receipt["quick_check"] == "ok"
    assert reload_notes_store_v1(path) == (manifest, [])


@pytest.mark.parametrize("annotated", [False, True])
def test_write_reload_keeps_typed_rows_order_metadata_and_old_projection_hash(tmp_path, annotated):
    cells = _cells()
    if annotated:
        records = []
        for original in cells:
            origin = original["original_cell"]
            inventory = {(origin["page_json_version_id"], 1, 1, origin["row_ordinal"]):
                         inventory_row(origin["row_ordinal"], [None, original["raw"], "7"])}
            records.append(classify_observation_v1(original, original["report_norm_id"], CLOSED, inventory))
        cells = attach_f36_ledger_v1(cells, records, ledger_input_refs=REFS)
    before = canonical_json_bytes_v1(cells)
    expected = _old_digest(cells)
    path = tmp_path / "synthetic.sqlite3"
    manifest = {"synthetic": True, "nested": {"label": "Nguồn giữ nguyên", "rows": 4}, "provider_calls": False}
    receipt = write_notes_store_v1(path, manifest=manifest, cells=cells)
    actual_manifest, actual_cells = reload_notes_store_v1(path)
    assert canonical_json_bytes_v1(actual_manifest) == canonical_json_bytes_v1(manifest)
    assert canonical_json_bytes_v1(actual_cells) == before == canonical_json_bytes_v1(cells)
    assert receipt["cells_sha256"] == expected == cells_projection_sha256_v1(actual_cells)
    with closing(sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)) as connection:
        connection.execute("PRAGMA query_only=ON")
        assert connection.execute("SELECT cells_sha256 FROM store_identity").fetchall() == [(expected,)]
        rows = connection.execute("SELECT cell_ordinal, report_norm_id, value_text, acceptance FROM note_cell ORDER BY cell_ordinal").fetchall()
        assert rows == [(0, 1206, "8", "ACCEPTED"), (1, None, "1250", "ACCEPTED"),
                        (2, 1212, None, "HOLD"), (3, 1206, "8", "DUPLICATE_IDENTICAL_CONTROL")]
        assert connection.execute("PRAGMA quick_check").fetchall() == [("ok",)]
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    assert not any((tmp_path / (path.name + suffix)).exists() for suffix in ("-wal", "-shm", "-journal"))


def test_lazy_row_insertion_still_rejects_duplicate_accepted_write_keys(tmp_path):
    original = cell()
    duplicate = cell(row=2)  # Different locator, same accepted canonical write key.
    with pytest.raises(NotesStoreError, match="two accepted cells share a write key"):
        write_notes_store_v1(tmp_path / "duplicate.sqlite3", manifest={"synthetic": True}, cells=[original, duplicate])
