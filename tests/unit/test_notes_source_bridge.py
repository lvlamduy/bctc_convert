"""Notes ORIGINAL-source bridge: SQL table coordinates proven against the original page, and PRIMARY identity binding."""

from __future__ import annotations

import copy
import sqlite3
from pathlib import Path

import pytest
from test_gemini_financial_page_store_v1 import _ingest

from bctc_ai.evaluation.gemini_financial_page_json_v1 import validate_financial_page_json_v1
from bctc_ai.notes.config_v1 import load_notes_config_v1
from bctc_ai.notes.engine_v1 import run_family_v1
from bctc_ai.notes.kernel_v1 import (
    DocumentContext,
    NoteColumn,
    NoteRow,
    NotesKernelError,
    NotesSource,
    NoteTable,
    assemble_continuations_v1,
)
from bctc_ai.notes.source_bridge_v1 import EXACT, EXACT_SHIFT, bridge_table_v1, original_cell_v1, table_fingerprint_v1
from bctc_ai.primary_statements.numbers_v1 import SeparatorRoles
from bctc_ai.primary_statements.source_v1 import CorpusSelection, SelectedDocument, SelectedPage
from bctc_ai.storage import gemini_financial_page_store_v1 as shared
from bctc_ai.storage.gemini_financial_page_store_v1 import _parents
from bctc_ai.storage.gemini_income_tax_source_page_loader_v1 import (
    GeminiIncomeTaxSourcePageReplayV1Error,
    prove_lossless_text_label_validation_v1,
)

ROOT = Path(__file__).resolve().parents[2]
VID = "gfpstorev1:json:" + "a" * 64
HEADERS = (["30/06/2025", "Triệu VND"], ["31/12/2024", "Triệu VND"])
FIVE = [("Nhóm 1 - Nợ đủ tiêu chuẩn", ["900", "800"]), ("Nhóm 2 - Nợ cần chú ý", ["50", "40"]),
        ("Nhóm 3 - Nợ dưới tiêu chuẩn", ["20", "10"]), ("Nhóm 4 - Nợ nghi ngờ", ["10", "5"]),
        ("Nhóm 5 - Nợ có khả năng mất vốn", ["20", "15"]), ("Tổng", ["1.000", "870"])]


def page(rows=FIVE, *, label_column=False, title="Phân tích chất lượng nợ cho vay", section="9. Cho vay khách hàng",
         continuation="NONE"):
    columns = [{"header_path_exact": list(h), "value_kind": "MONEY"} for h in HEADERS]
    if label_column:
        columns.insert(0, {"header_path_exact": ["Chỉ tiêu"], "value_kind": "TEXT"})
    body = [{"label_exact": label, "hierarchy_path_exact": [label], "row_kind": "TOTAL" if label == "Tổng" else "ITEM",
             "values_exact": ([label] if label_column else []) + list(values)} for label, values in rows]
    return {"status": "FINANCIAL_NOTE_CONTENT",
            "sections": [{"content_kind": "FINANCIAL_NOTE", "statement_type": "NOT_APPLICABLE", "title_exact": section,
                          "narratives_exact": [], "tables": [{"title_exact": title, "unit_exact": None,
                                                              "continuation": continuation, "columns": columns, "rows": body}]}],
            "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []}}


def sql_table(stored_page, *, vid=VID, physical_page=10, ordinal=1):
    """What the store ingest writes for s1/t1 of the page it stored (same ids, raw JSON, store parent rule)."""

    section = stored_page["sections"][0]
    raw = section["tables"][0]
    table = NoteTable(ordinal, physical_page, vid, "s1", "t1", 0, 0, section["content_kind"], section["title_exact"],
                      raw["title_exact"], raw["unit_exact"], raw["continuation"],
                      [n for n in section["narratives_exact"] if isinstance(n, str)],
                      narratives_raw=copy.deepcopy(section["narratives_exact"]))
    for index, column in enumerate(raw["columns"]):
        header = copy.deepcopy(column["header_path_exact"])
        table.columns.append(NoteColumn(f"c{index + 1}", index, tuple(p for p in header if isinstance(p, str)),
                                        column["value_kind"], header))
    parents = _parents(raw["rows"])
    for index, row in enumerate(raw["rows"]):
        row_id = f"r{index + 1}"
        path = copy.deepcopy(row["hierarchy_path_exact"])
        table.rows.append(NoteRow(row_id, index, row["label_exact"], row["row_kind"],
                                  tuple(p for p in path if isinstance(p, str)), parents[row_id], path))
        for column_index, value in enumerate(row["values_exact"]):
            table.cells[(row_id, f"c{column_index + 1}")] = (value, "VALUE")
    return table


def proven(original):
    validated = validate_financial_page_json_v1(original)
    return validated, prove_lossless_text_label_validation_v1(original, validated)


def at(table, row_id, column_id, **override):
    return {**table.locator(), "row_id": row_id, "column_id": column_id, **override}


def test_exact_bijection_maps_every_cell_to_its_original_coordinate():
    original = page()
    validated, changes = proven(original)
    assert changes == []
    table = sql_table(original)
    table.bridge = bridge_table_v1(table, original, validated, changes)
    assert table.bridge["status"] == EXACT and table.bridge_failure() is None
    assert table.bridge["column_map"] == {"c1": 1, "c2": 2}
    assert original_cell_v1(table, at(table, "r2", "c2")) == {
        "page_json_version_id": VID, "section_ordinal": 1, "table_ordinal": 1, "row_ordinal": 2, "column_ordinal": 2,
        "bridge_status": EXACT}
    assert original["sections"][0]["tables"][0]["rows"][1]["values_exact"][1] == "40"


def test_original_cell_requires_existing_row_cell_and_the_same_table_identity():
    original = page()
    validated, changes = proven(original)
    table = sql_table(original)
    table.bridge = bridge_table_v1(table, original, validated, changes)
    assert original_cell_v1(table, at(table, "r999", "c1")) is None  # absent row
    assert original_cell_v1(table, at(table, "r1", "c3")) is None  # absent cell
    assert original_cell_v1(table, at(table, "r01", "c1")) is None  # noncanonical row key
    for key, wrong in (("page_json_version_id", "gfpstorev1:json:" + "f" * 64), ("section_id", "s2"), ("table_id", "t2")):
        assert original_cell_v1(table, at(table, "r1", "c1", **{key: wrong})) is None
    proof = table.bridge
    for key in ("section_ordinal", "table_ordinal"):  # a same-VID proof made for another table is not this inverse
        table.bridge = dict(proof, **{key: 2})
        assert original_cell_v1(table, at(table, "r1", "c1")) is None
    table.bridge = proof
    assert original_cell_v1(table, at(table, "r1", "c1")) is not None
    table.bridge = None  # missing inverse -> not bijective
    assert original_cell_v1(table, at(table, "r1", "c1")) is None


def test_store_built_from_original_maps_identity_and_store_built_from_validated_needs_the_proven_shift():
    original = page(label_column=True)
    validated, changes = proven(original)
    assert [c["redundant_text_column_ordinal"] for c in changes] == [1]
    # A store whose nodes keep the original TEXT label column: identity map to the ORIGINAL.
    legacy = sql_table(original)
    assert bridge_table_v1(legacy, original, validated, changes)["column_map"] == {"c1": 1, "c2": 2, "c3": 3}
    # Nodes built from the validated projection: only through the loader-proven TEXT shift.
    table = sql_table(validated)
    bridge = bridge_table_v1(table, original, validated, changes)
    assert bridge["status"] == EXACT_SHIFT and bridge["column_map"] == {"c1": 2, "c2": 3}
    table.bridge = bridge
    assert original_cell_v1(table, at(table, "r1", "c1"))["column_ordinal"] == 2
    # The same difference without the loader's replayed proof is not admitted.
    assert bridge_table_v1(table, original, validated, [])["status"] == "MISMATCH:COLUMN_COUNT"
    # A recorded shift that does not explain the original exactly is not admitted either.
    tampered = copy.deepcopy(original)
    tampered["sections"][0]["tables"][0]["rows"][0]["values_exact"][2] = "801"
    assert bridge_table_v1(table, tampered, validated, changes)["status"] == "MISMATCH:TEXT_SHIFT_ROW_DIFFERS"
    relabelled = copy.deepcopy(original)
    relabelled["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "Khác"
    assert bridge_table_v1(table, relabelled, validated, changes)["status"] == "MISMATCH:TEXT_SHIFT_CELL_NOT_REDUNDANT"


def test_same_row_id_with_moved_row_or_compound_cell_is_a_mismatch():
    original = page()
    validated, changes = proven(original)
    moved = sql_table(original)
    moved.rows[0].label, moved.rows[1].label = moved.rows[1].label, moved.rows[0].label
    assert bridge_table_v1(moved, original, validated, changes)["status"] == "MISMATCH:ROW_IDENTITY"
    compound = sql_table(original)
    compound.cells[("r1", "c1")] = ("900\n900", "VALUE")  # duplicated text under one coordinate
    result = bridge_table_v1(compound, original, validated, changes)
    assert result["status"] == "MISMATCH:CELL_VALUE" and (result["row_id"], result["column_id"]) == ("r1", "c1")


def test_missing_extra_or_untyped_cells_are_mismatches():
    original = page([("Nhóm 1 - Nợ đủ tiêu chuẩn", ["900", None]), ("Tổng", ["900", "800"])])
    validated, changes = proven(original)
    assert bridge_table_v1(sql_table(original), original, validated, changes)["status"] == EXACT  # null kept positionally
    missing = sql_table(original)
    del missing.cells[("r1", "c2")]
    assert bridge_table_v1(missing, original, validated, changes)["status"] == "MISMATCH:CELL_COUNT"
    extra = sql_table(original)
    extra.cells[("r1", "c3")] = ("1", "VALUE")
    assert bridge_table_v1(extra, original, validated, changes)["status"] == "MISMATCH:CELL_COUNT"
    orphan = sql_table(original)
    orphan.cells[("r9", "c1")] = ("1", "VALUE")
    assert bridge_table_v1(orphan, original, validated, changes)["status"] == "MISMATCH:CELL_WITHOUT_ROW"
    blank = sql_table(original)
    blank.cells[("r1", "c2")] = ("", "BLANK")  # "" is not the stored null
    assert bridge_table_v1(blank, original, validated, changes)["status"] == "MISMATCH:CELL_VALUE"
    header = sql_table(original)
    header.columns[0].header_raw = ["30/06/2025"]  # filtered header is not the raw header
    assert bridge_table_v1(header, original, validated, changes)["status"] == "MISMATCH:COLUMN_IDENTITY"


def test_parent_edge_must_recompute_from_raw_hierarchy_and_ambiguity_has_no_parent():
    rows = [{"label_exact": "A", "hierarchy_path_exact": ["A"], "row_kind": "GROUP", "values_exact": [None]},
            {"label_exact": "A", "hierarchy_path_exact": ["A"], "row_kind": "GROUP", "values_exact": [None]},
            {"label_exact": "x", "hierarchy_path_exact": ["A", "x"], "row_kind": "ITEM", "values_exact": ["1"]}]
    raw = {"status": "FINANCIAL_NOTE_CONTENT", "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
           "sections": [{"content_kind": "FINANCIAL_NOTE", "statement_type": "NOT_APPLICABLE", "title_exact": "Note",
                         "narratives_exact": [], "tables": [{"title_exact": None, "unit_exact": None, "continuation": "NONE",
                                                             "columns": [{"header_path_exact": ["31/12/2025"], "value_kind": "MONEY"}],
                                                             "rows": rows}]}]}
    table = sql_table(raw)
    assert table.rows[2].parent_row_id is None
    assert bridge_table_v1(table, raw, copy.deepcopy(raw), [])["status"] == EXACT
    table.rows[2].parent_row_id = "r1"  # an ETL edge that the raw hierarchy does not prove
    result = bridge_table_v1(table, raw, copy.deepcopy(raw), [])
    assert result["status"] == "MISMATCH:PARENT_EDGE_NOT_RECOMPUTED" and result["row_id"] == "r3"


class _OutlineSource:
    def __init__(self, entries):
        self._entries = entries

    def outline(self):
        return {1: self._entries}


def _entry(page_number, vid, continuation):
    return {"page": page_number, "section_order": 0, "table_order": 0, "kind": "FINANCIAL_NOTE", "title": None,
            "source": "TABLE_TITLE", "version": vid, "section_id": "s1", "table_id": "t1", "continuation": continuation}


def test_continuation_keeps_inverse_fragment_coordinates_through_a_column_offset():
    head_original = page(FIVE[:3], continuation="CONTINUES_ON_NEXT_PAGE")
    follower_original = page(FIVE[3:], label_column=True, title=None, section=None, continuation="CONTINUES_FROM_PREVIOUS_PAGE")
    head_vid, follower_vid = "gfpstorev1:json:" + "1" * 64, "gfpstorev1:json:" + "2" * 64
    head = sql_table(head_original, vid=head_vid, physical_page=15)
    follower = sql_table(follower_original, vid=follower_vid, physical_page=16)  # nodes keep the TEXT column
    head.bridge = bridge_table_v1(head, head_original, *proven(head_original))
    follower.bridge = bridge_table_v1(follower, follower_original, *proven(follower_original))
    assert head.bridge["status"] == follower.bridge["status"] == EXACT
    source = _OutlineSource([_entry(15, head_vid, "CONTINUES_ON_NEXT_PAGE"), _entry(16, follower_vid, "CONTINUES_FROM_PREVIOUS_PAGE")])
    joined, receipts = assemble_continuations_v1(source, [head, follower])
    assert len(joined) == 1 and len(receipts) == 1
    merged = joined[0]
    assert merged.bridge_failure() is None and merged.fragment_column_maps[16] == {"c1": "c2", "c2": "c3"}
    # Follower row r1 head column c2 is the follower's own c3: original column 3 of page 16.
    assert merged.cells[("p16:r1", "c2")][0] == "5"
    assert original_cell_v1(merged, at(merged, "p16:r1", "c2")) == {
        "page_json_version_id": follower_vid, "section_ordinal": 1, "table_ordinal": 1, "row_ordinal": 1,
        "column_ordinal": 3, "bridge_status": EXACT}
    assert original_cell_v1(merged, at(merged, "p15:r2", "c1"))["page_json_version_id"] == head_vid
    for row_id in ("p17:r1", "r1", "p016:r1", "p16:r9"):  # unknown page, unprefixed, noncanonical, absent row
        assert original_cell_v1(merged, at(merged, row_id, "c1")) is None
    assert original_cell_v1(merged, at(merged, "p16:r1", "c2", page_json_version_id=follower_vid)) is None  # not this table
    # A fragment proof that belongs to another VID or another table, or an unproven fragment, is not an inverse.
    follower_proof = merged.fragment_bridges[1]
    for wrong in ({"page_json_version_id": head_vid}, {"section_ordinal": 2}, {"table_ordinal": 2}):
        merged.fragment_bridges[1] = dict(follower_proof, **wrong)
        assert original_cell_v1(merged, at(merged, "p16:r1", "c2")) is None
    merged.fragment_bridges[1] = {"status": "MISMATCH:CELL_VALUE", "physical_page": 16}
    assert merged.bridge_failure() == "SOURCE_BRIDGE:MISMATCH:CELL_VALUE"


# ---------------------------------------------------------------- real store + authenticated loader


def corpus(db_path, pages, relative_path="report.pdf", source_sha256="b" * 64):
    selected = tuple(SelectedPage(number, vid, f"page-{number}", "FINANCIAL_NOTE_CONTENT", "c" * 64) for number, vid in pages)
    document = SelectedDocument(1, relative_path, source_sha256, 123, 20, "plan", "manifest", "selection", selected)
    return CorpusSelection("full271", db_path.parent, db_path.parent / "index.json", "1" * 64, "cmi", db_path, "2" * 64,
                           (document,))


def store(tmp_path, monkeypatch, original, *, keep_original_nodes=False):
    db = tmp_path / "source.sqlite3"
    shared.initialize_gemini_financial_page_store_v1(db)
    with monkeypatch.context() as context:
        if keep_original_nodes:  # an earlier ingestion that retained the TEXT label column in its nodes
            context.setattr(shared, "validate_financial_page_json_v1", copy.deepcopy)
        stored = _ingest(db, page_json=original, physical_page=1)
    return db, stored["page_json_version_id"]


def test_real_store_tables_are_bridged_through_the_authenticated_loader(tmp_path, monkeypatch):
    db, vid = store(tmp_path, monkeypatch, page())
    source = NotesSource(corpus(db, [(1, vid)]))
    [table] = source.load_tables([(vid, "s1", "t1")])
    assert table.bridge["status"] == EXACT and table.bridge["source_logical_name"] == "report.pdf"
    assert table.bridge["original_blob_sha256"] and table.bridge["replay_receipt_id"]
    assert original_cell_v1(table, at(table, "r6", "c1"))["row_ordinal"] == 6
    (tmp_path / "legacy").mkdir()
    legacy_db, legacy_vid = store(tmp_path / "legacy", monkeypatch, page(label_column=True), keep_original_nodes=True)
    [legacy] = NotesSource(corpus(legacy_db, [(1, legacy_vid)])).load_tables([(legacy_vid, "s1", "t1")])
    assert legacy.bridge["status"] == EXACT and legacy.bridge["column_map"] == {"c1": 1, "c2": 2, "c3": 3}


@pytest.mark.parametrize("failure", ["blob_sha", "content_id", "missing_vid", "missing_table", "provenance", "sqlite"])
def test_loader_integrity_and_missing_input_fail_the_invocation(tmp_path, monkeypatch, failure):
    db, vid = store(tmp_path, monkeypatch, page())
    pages, key, relative_path = [(1, vid)], (vid, "s1", "t1"), "report.pdf"
    if failure == "blob_sha":
        with sqlite3.connect(db) as connection:
            connection.execute("UPDATE page_json_version SET canonical_json_sha256=?", ("0" * 64,))
    elif failure == "content_id":
        with sqlite3.connect(db) as connection:
            connection.execute("UPDATE page_json_version SET page_id=?", ("gfpstorev1:page:" + "0" * 64,))
    elif failure == "missing_table":
        key = (vid, "s1", "t9")
    elif failure == "provenance":
        relative_path = "other.pdf"
    elif failure == "sqlite":
        db.write_bytes(b"not a database")
    source = NotesSource(corpus(db, pages, relative_path=relative_path))
    if failure == "missing_vid":
        absent = "gfpstorev1:json:" + "0" * 64
        source = NotesSource(corpus(db, pages + [(2, absent)]))
        with pytest.raises(shared.GeminiFinancialPageStoreV1Error):
            source._attach_bridges([sql_table(page(), vid=absent, physical_page=2)])
        return
    with pytest.raises((NotesKernelError, GeminiIncomeTaxSourcePageReplayV1Error, shared.GeminiFinancialPageStoreV1Error,
                        sqlite3.DatabaseError)):
        source.load_tables([key])


def test_cached_proof_binds_the_sql_payload_and_is_detached(tmp_path, monkeypatch):
    db, vid = store(tmp_path, monkeypatch, page())
    calls = []

    def loader(path, *, page_json_version_ids):
        from bctc_ai.storage.gemini_income_tax_source_page_loader_v1 import load_income_tax_source_page_json_versions_v1
        calls.append(list(page_json_version_ids))
        return load_income_tax_source_page_json_versions_v1(path, page_json_version_ids=page_json_version_ids)

    source = NotesSource(corpus(db, [(1, vid)]), original_loader=loader)
    [first] = source.load_tables([(vid, "s1", "t1")])
    assert first.bridge["status"] == EXACT and len(calls) == 1
    first.bridge["status"] = "POISONED"  # mutating an attached receipt must not poison the cache
    [again] = source.load_tables([(vid, "s1", "t1")])
    assert again.bridge["status"] == EXACT and len(calls) == 1  # identical payload: no second original load
    for mutate in (lambda t: t.cells.__setitem__(("r1", "c1"), ("901", "VALUE")),
                   lambda t: setattr(t.columns[0], "header_raw", ["30/06/2025"]),
                   lambda t: setattr(t.rows[0], "hierarchy_raw", ["Nhóm 1"]),
                   lambda t: setattr(t.rows[0], "kind", "GROUP"),
                   # same values, other container type: typed-exact comparison rejects it, so must the cache
                   lambda t: setattr(t.columns[0], "header_raw", tuple(t.columns[0].header_raw)),
                   lambda t: setattr(t.rows[0], "hierarchy_raw", tuple(t.rows[0].hierarchy_raw)),
                   lambda t: setattr(t, "narratives_raw", tuple(t.narratives_raw))):
        changed = copy.deepcopy(again)
        mutate(changed)
        assert table_fingerprint_v1(changed) != table_fingerprint_v1(again)
        source._attach_bridges([changed])
        assert changed.bridge["status"].startswith("MISMATCH:")  # never the old EXACT proof
    assert table_fingerprint_v1(copy.deepcopy(again)) == table_fingerprint_v1(again)


# ---------------------------------------------------------------- engine


def context(relative_path="report.pdf", source_sha256="b" * 64, corpus_identity=None, db=None):
    return DocumentContext(
        ordinal=1, document_plan_id="plan", relative_path=relative_path, source_sha256=source_sha256, scope="CONSOLIDATED",
        scope_basis="PRIMARY_DOCUMENT_SCOPE", reporting_date="2025-06-30",
        balance_lanes=[{"key": "INSTANT:2025-06-30", "role": "CURRENT", "header": "30/06/2025"},
                       {"key": "INSTANT:2024-12-31", "role": "COMPARATIVE", "header": "31/12/2024"}],
        context_texts=["Tại ngày 30 tháng 6 năm 2025"], primary_cells={},
        separator_roles=SeparatorRoles(thousands=frozenset({"."})), corpus_identity=corpus_identity or {})


class _StoreSource(NotesSource):
    """The real store and loader; only retrieval/outline are fixed for one table."""

    def candidate_tables(self, like_patterns):
        return {(page.page_json_version_id, "s1", "t1"): 1 for page in self.corpus.documents[0].pages}

    def outline(self):
        return {1: [_entry(page.physical_page, page.page_json_version_id, "NONE") for page in self.corpus.documents[0].pages]}


@pytest.fixture(scope="module")
def config():
    return load_notes_config_v1(ROOT)


def test_engine_binds_primary_context_by_identity_and_rejects_unbridged_tables(tmp_path, monkeypatch, config):
    db, vid = store(tmp_path, monkeypatch, page())
    selection = corpus(db, [(1, vid)])
    identity = selection.identity()
    run = run_family_v1("CREDIT_QUALITY", config, _StoreSource(selection), {1: context(corpus_identity=identity)})
    assert [e.status for e in run.evaluations] == ["EVALUATED"]
    accepted = [c for c in run.cells if c["acceptance"] == "ACCEPTED"]
    assert accepted and all(c["original_cell"]["page_json_version_id"] == vid for c in accepted)
    # Same ordinal, different source document or different corpus: never an ordinal fallback.
    for wrong, reason in ((context(source_sha256="9" * 64, corpus_identity=identity), "PRIMARY_CONTEXT_DOCUMENT_IDENTITY_MISMATCH"),
                          (context(corpus_identity={**identity, "corpus_name": "common204"}),
                           "PRIMARY_CONTEXT_CORPUS_IDENTITY_MISMATCH")):
        held = run_family_v1("CREDIT_QUALITY", config, _StoreSource(selection), {1: wrong})
        assert [(e.status, e.reasons) for e in held.evaluations] == [("REJECTED", [reason])] and held.cells == []
    missing = run_family_v1("CREDIT_QUALITY", config, _StoreSource(selection), {})
    assert [e.reasons for e in missing.evaluations] == [["PRIMARY_CONTEXT_MISSING"]]
    # The normalized cell disagrees with the ORIGINAL: the table is rejected, never read.
    with sqlite3.connect(db) as connection:
        connection.execute("UPDATE value_cell SET source_text='5' WHERE row_id='r2' AND column_id='c1'")
    rejected = run_family_v1("CREDIT_QUALITY", config, _StoreSource(selection), {1: context(corpus_identity=identity)})
    assert [(e.status, e.reasons) for e in rejected.evaluations] == [("REJECTED", ["SOURCE_BRIDGE:MISMATCH:CELL_VALUE"])]
