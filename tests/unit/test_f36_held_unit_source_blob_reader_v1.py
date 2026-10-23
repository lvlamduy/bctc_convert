"""Real private SQLite BLOB IO only; no PDF, unit or financial approval.

The enclosing authenticated snapshot/corpus supplies authority in production.
These tests prove declared dependency selection and the two serialization
domains; fake unit metadata alone is never a source of financial permission.
"""
from __future__ import annotations

import copy
import sqlite3
from hashlib import sha256

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1 as digest
from scripts.experiments import run_gemini_json_operating_expense_accounting_family_v1 as runner

NOTE = "gfpstorev1:json:" + "1" * 64
PRIMARY = "gfpstorev1:json:" + "2" * 64
OTHER = "gfpstorev1:json:" + "3" * 64


def _blob_ref(version, page):
    blob = canonical_json_bytes_v1(page) + b"\n"
    return {"page_json_version_id": version, "stored_blob_sha256": sha256(blob).hexdigest(),
            "stored_blob_size_bytes": len(blob), "original_object_sha256": digest(page)}


def _case(tmp_path):
    document = {"document_id": "gfpstorev1:document:" + "a" * 64, "document_ordinal": 1,
                "source_logical_name": "bank/report.pdf", "source_sha256": "b" * 64}
    axes = [{**document, "page_json_version_id": version, "physical_page": physical,
             "selected_page_ordinal": selected}
            for version, physical, selected in ((NOTE, 44, 2), (PRIMARY, 7, 1))]
    pages = {1: {
        NOTE: {"status": "SUCCESS", "sections": [{"content_kind": "FINANCIAL_NOTE",
            "tables": [{"unit_exact": None, "rows": [{"values_exact": ["(10)", None]}]}]}]},
        PRIMARY: {"status": "PRIMARY_FINANCIAL_STATEMENT", "sections": [{
            "content_kind": "PRIMARY_STATEMENT", "statement_type": "INCOME_STATEMENT",
            "tables": [{"unit_exact": "Triệu đồng", "rows": [{"values_exact": ["(10)", "-"]}]}]}]}}}
    expected = {version: _blob_ref(version, page) for version, page in pages[1].items()}
    database = tmp_path / "source.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE page_json_version(page_json_version_id TEXT PRIMARY KEY, canonical_json_bytes BLOB, canonical_json_sha256 TEXT)")
        for version, page in pages[1].items():
            blob = canonical_json_bytes_v1(page) + b"\n"
            connection.execute("INSERT INTO page_json_version VALUES(?,?,?)", (version, blob, sha256(blob).hexdigest()))
        # An unselected corrupt extra BLOB must never be enumerated/returned.
        connection.execute("INSERT INTO page_json_version VALUES(?,?,?)", (OTHER, b"not source JSON", "0" * 64))
    frontier = {"locator": {**axes[0], "section_id": "s1", "table_id": "t1"},
        "unit_corroboration_receipts": [{"matched_primary_roots": [{
            # Existing binder locator is FOUR fields, not a newly invented7.
            "locator": {"page_json_version_id": PRIMARY, "physical_page": 7,
                        "section_id": "s1", "table_id": "t1"}, "row_ordinal": 1}]}],
        "unit_source_page_blob_refs": [{"selected_page_axis": copy.deepcopy(axes[1]),
                                       "stored_page_blob_ref": copy.deepcopy(expected[PRIMARY])}]}
    indexed = {"selected_document_axis": [document], "selected_page_axis": axes}
    declaration = {"reviews": [{"document": copy.deepcopy(document), "printed_frontier": frontier}]}
    return database, indexed, pages, declaration, expected


def _read(case):
    database, indexed, pages, declaration, _ = case
    return runner._row_original_blob_refs_v1(database, indexed, pages, declaration)


def test_no_unit_dependency_fields_preserve_exact_note_only_blob_result(tmp_path):
    case = _case(tmp_path)
    frontier = case[3]["reviews"][0]["printed_frontier"]
    del frontier["unit_corroboration_receipts"], frontier["unit_source_page_blob_refs"]
    before, objects = case[0].read_bytes(), copy.deepcopy(case[1:4])
    actual = _read(case)
    assert actual == {NOTE: case[4][NOTE]}
    assert PRIMARY not in actual and OTHER not in actual
    assert case[0].read_bytes() == before and case[1:4] == objects


def test_declared_primary_dependency_returns_both_original_domains_read_only(tmp_path):
    case = _case(tmp_path)
    before, objects = case[0].read_bytes(), copy.deepcopy(case[1:4])
    actual = _read(case)
    assert actual == case[4] and set(actual) == {NOTE, PRIMARY}
    primary = case[2][1][PRIMARY]
    assert actual[PRIMARY]["original_object_sha256"] == digest(primary)
    assert actual[PRIMARY]["stored_blob_sha256"] == sha256(canonical_json_bytes_v1(primary) + b"\n").hexdigest()
    assert actual[PRIMARY]["stored_blob_sha256"] != actual[PRIMARY]["original_object_sha256"]
    assert primary["sections"][0]["tables"][0]["rows"][0]["values_exact"] == ["(10)", "-"]
    assert case[0].read_bytes() == before and case[1:4] == objects
    assert not any(case[0].with_name(case[0].name + suffix).exists() for suffix in ("-wal", "-shm", "-journal"))


def test_multiple_existing_roots_on_same_primary_vid_need_one_blob_dependency(tmp_path):
    case = _case(tmp_path)
    roots = case[3]["reviews"][0]["printed_frontier"]["unit_corroboration_receipts"][0]["matched_primary_roots"]
    roots.append({**copy.deepcopy(roots[0]), "row_ordinal": 2})
    assert _read(case) == case[4]


@pytest.mark.parametrize("attack", [
    "missing-receipt", "missing-dependency", "duplicate-dependency", "extra-dependency",
    "foreign-document", "foreign-source", "bool-document", "float-physical", "bool-selected",
    "unselected-vid", "duplicate-selected-axis", "wrong-root-physical", "not-primary",
    "declared-blob-drift", "object-drift", "stored-sha-drift", "one-lf-blob", "sidecar",
])
def test_declared_unit_source_dependency_fails_closed_without_source_mutation(tmp_path, attack):
    case = _case(tmp_path)
    database, indexed, pages, declaration, _ = case
    review = declaration["reviews"][0]
    frontier = review["printed_frontier"]
    dependency = frontier["unit_source_page_blob_refs"][0]
    root = frontier["unit_corroboration_receipts"][0]["matched_primary_roots"][0]
    if attack == "missing-receipt":
        del frontier["unit_corroboration_receipts"]
    elif attack == "missing-dependency":
        del frontier["unit_source_page_blob_refs"]
    elif attack == "duplicate-dependency":
        frontier["unit_source_page_blob_refs"].append(copy.deepcopy(dependency))
    elif attack == "extra-dependency":
        extra = copy.deepcopy(dependency)
        extra["selected_page_axis"]["page_json_version_id"] = OTHER
        extra["selected_page_axis"]["physical_page"] = 8
        extra["selected_page_axis"]["selected_page_ordinal"] = 3
        indexed["selected_page_axis"].append(copy.deepcopy(extra["selected_page_axis"]))
        pages[1][OTHER] = copy.deepcopy(pages[1][PRIMARY])
        frontier["unit_source_page_blob_refs"].append(extra)
    elif attack == "foreign-document":
        dependency["selected_page_axis"]["document_ordinal"] = 2
        indexed["selected_page_axis"][1]["document_ordinal"] = 2
        indexed["selected_document_axis"].append({**review["document"], "document_ordinal": 2})
        pages[2] = {PRIMARY: copy.deepcopy(pages[1][PRIMARY])}
    elif attack == "foreign-source":
        dependency["selected_page_axis"]["source_sha256"] = "c" * 64
        indexed["selected_page_axis"][1]["source_sha256"] = "c" * 64
    elif attack == "bool-document":
        review["document"]["document_ordinal"] = True
        indexed["selected_document_axis"][0]["document_ordinal"] = True
    elif attack in {"float-physical", "bool-selected"}:
        field, value = ("physical_page", 7.0) if attack == "float-physical" else ("selected_page_ordinal", True)
        dependency["selected_page_axis"][field] = value
        indexed["selected_page_axis"][1][field] = value
    elif attack == "unselected-vid":
        dependency["selected_page_axis"]["page_json_version_id"] = OTHER
        root["locator"]["page_json_version_id"] = OTHER
    elif attack == "duplicate-selected-axis":
        indexed["selected_page_axis"].append(copy.deepcopy(indexed["selected_page_axis"][1]))
    elif attack == "wrong-root-physical":
        root["locator"]["physical_page"] = 8
    elif attack == "not-primary":
        pages[1][PRIMARY]["status"] = "SUCCESS"
    elif attack == "declared-blob-drift":
        dependency["stored_page_blob_ref"]["stored_blob_sha256"] = "0" * 64
    elif attack == "object-drift":
        pages[1][PRIMARY]["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "999"
    elif attack == "stored-sha-drift":
        with sqlite3.connect(database) as connection:
            connection.execute("UPDATE page_json_version SET canonical_json_sha256=? WHERE page_json_version_id=?", ("0" * 64, PRIMARY))
    elif attack == "one-lf-blob":
        blob = canonical_json_bytes_v1(pages[1][PRIMARY])
        with sqlite3.connect(database) as connection:
            connection.execute("UPDATE page_json_version SET canonical_json_bytes=?, canonical_json_sha256=? WHERE page_json_version_id=?", (blob, sha256(blob).hexdigest(), PRIMARY))
    elif attack == "sidecar":
        database.with_name(database.name + "-wal").write_bytes(b"not ignored")
    else:
        raise AssertionError(attack)
    before, objects = database.read_bytes(), copy.deepcopy(case[1:4])
    match = "dependency VID set/order" if attack == "extra-dependency" else None
    with pytest.raises(runner.RunGeminiJsonOperatingExpenseV1Error, match=match):
        _read(case)
    assert database.read_bytes() == before and case[1:4] == objects
