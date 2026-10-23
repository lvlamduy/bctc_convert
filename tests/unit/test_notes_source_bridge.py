"""Notes ORIGINAL-source bridge: SQL table coordinates proven against the original page, and PRIMARY identity binding."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_financial_page_json_v1 import validate_financial_page_json_v1
from bctc_ai.notes.config_v1 import load_notes_config_v1
from bctc_ai.notes.engine_v1 import run_family_v1
from bctc_ai.notes.kernel_v1 import DocumentContext, NoteColumn, NoteRow, NotesSource, NoteTable, assemble_continuations_v1
from bctc_ai.notes.source_bridge_v1 import EXACT, EXACT_SHIFT, bridge_table_v1, original_cell_v1
from bctc_ai.primary_statements.numbers_v1 import SeparatorRoles
from bctc_ai.primary_statements.source_v1 import CorpusSelection, SelectedDocument, SelectedPage
from bctc_ai.storage.gemini_financial_page_store_v1 import _parents
from bctc_ai.storage.gemini_income_tax_source_page_loader_v1 import prove_lossless_text_label_validation_v1

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


def sql_table(validated, *, vid=VID, physical_page=10, ordinal=1):
    """What the store ingest writes for s1/t1 of a validated page (same ids, raw JSON, store parent rule)."""

    section = validated["sections"][0]
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


def test_exact_bijection_maps_every_cell_to_its_original_coordinate():
    original = page()
    validated, changes = proven(original)
    assert changes == []
    table = sql_table(validated)
    table.bridge = bridge_table_v1(table, validated, original, changes)
    assert table.bridge["status"] == EXACT and table.bridge_failure() is None
    assert table.bridge["column_map"] == {"c1": 1, "c2": 2}
    cell = original_cell_v1(table, {"row_id": "r2", "column_id": "c2"})
    assert cell == {"page_json_version_id": VID, "section_ordinal": 1, "table_ordinal": 1, "row_ordinal": 2,
                    "column_ordinal": 2, "bridge_status": EXACT}
    assert original["sections"][0]["tables"][0]["rows"][1]["values_exact"][1] == "40"


def test_proven_text_column_shift_maps_sql_columns_to_original_ordinals_and_unproven_is_held():
    original = page(label_column=True)
    validated, changes = proven(original)
    assert [c["redundant_text_column_ordinal"] for c in changes] == [1]
    table = sql_table(validated)
    bridge = bridge_table_v1(table, validated, original, changes)
    assert bridge["status"] == EXACT_SHIFT and bridge["column_map"] == {"c1": 2, "c2": 3}
    table.bridge = bridge
    assert original_cell_v1(table, {"row_id": "r1", "column_id": "c1"})["column_ordinal"] == 2
    # The same difference without the loader's replayed proof is not admitted.
    assert bridge_table_v1(table, validated, original, [])["status"] == "MISMATCH:UNPROVEN_ORIGINAL_TRANSFORM"
    # A recorded shift that does not explain the original exactly is not admitted either.
    tampered = copy.deepcopy(original)
    tampered["sections"][0]["tables"][0]["rows"][0]["values_exact"][2] = "801"
    assert bridge_table_v1(table, validated, tampered, changes)["status"] == "MISMATCH:TEXT_SHIFT_ROW_DIFFERS"


def test_same_row_id_with_moved_row_or_compound_cell_is_a_mismatch():
    original = page()
    validated, changes = proven(original)
    moved = sql_table(validated)
    moved.rows[0].label, moved.rows[1].label = moved.rows[1].label, moved.rows[0].label
    assert bridge_table_v1(moved, validated, original, changes)["status"] == "MISMATCH:ROW_IDENTITY"
    compound = sql_table(validated)
    compound.cells[("r1", "c1")] = ("900\n900", "VALUE")  # duplicated text under one coordinate
    result = bridge_table_v1(compound, validated, original, changes)
    assert result["status"] == "MISMATCH:CELL_VALUE" and (result["row_id"], result["column_id"]) == ("r1", "c1")


def test_missing_extra_or_untyped_cells_are_mismatches():
    original = page([("Nhóm 1 - Nợ đủ tiêu chuẩn", ["900", None]), ("Tổng", ["900", "800"])])
    validated, changes = proven(original)
    assert bridge_table_v1(sql_table(validated), validated, original, changes)["status"] == EXACT  # null kept positionally
    missing = sql_table(validated)
    del missing.cells[("r1", "c2")]
    assert bridge_table_v1(missing, validated, original, changes)["status"] == "MISMATCH:CELL_COUNT"
    extra = sql_table(validated)
    extra.cells[("r1", "c3")] = ("1", "VALUE")
    assert bridge_table_v1(extra, validated, original, changes)["status"] == "MISMATCH:CELL_COUNT"
    orphan = sql_table(validated)
    orphan.cells[("r9", "c1")] = ("1", "VALUE")
    assert bridge_table_v1(orphan, validated, original, changes)["status"] == "MISMATCH:CELL_WITHOUT_ROW"
    blank = sql_table(validated)
    blank.cells[("r1", "c2")] = ("", "BLANK")  # "" is not the stored null
    assert bridge_table_v1(blank, validated, original, changes)["status"] == "MISMATCH:CELL_VALUE"
    header = sql_table(validated)
    header.columns[0].header_raw = ["30/06/2025"]  # filtered header is not the raw header
    assert bridge_table_v1(header, validated, original, changes)["status"] == "MISMATCH:COLUMN_IDENTITY"


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
    head_validated, head_changes = proven(head_original)
    follower_validated, follower_changes = proven(follower_original)
    head_vid, follower_vid = "gfpstorev1:json:" + "1" * 64, "gfpstorev1:json:" + "2" * 64
    head = sql_table(head_validated, vid=head_vid, physical_page=15)
    follower = sql_table(follower_original, vid=follower_vid, physical_page=16)  # store-like with the TEXT column kept
    follower_original_as_validated = copy.deepcopy(follower_original)
    head.bridge = bridge_table_v1(head, head_validated, head_original, head_changes)
    follower.bridge = bridge_table_v1(follower, follower_original_as_validated, follower_original, [])
    assert head.bridge["status"] == follower.bridge["status"] == EXACT
    source = _OutlineSource([_entry(15, head_vid, "CONTINUES_ON_NEXT_PAGE"), _entry(16, follower_vid, "CONTINUES_FROM_PREVIOUS_PAGE")])
    joined, receipts = assemble_continuations_v1(source, [head, follower])
    assert len(joined) == 1 and len(receipts) == 1
    merged = joined[0]
    assert merged.bridge_failure() is None and merged.fragment_column_maps[16] == {"c1": "c2", "c2": "c3"}
    # Follower row r1 head column c2 is the follower's own c3: original column 3 of page 16.
    assert merged.cells[("p16:r1", "c2")][0] == "5"
    assert original_cell_v1(merged, {"row_id": "p16:r1", "column_id": "c2"}) == {
        "page_json_version_id": follower_vid, "section_ordinal": 1, "table_ordinal": 1, "row_ordinal": 1,
        "column_ordinal": 3, "bridge_status": EXACT}
    assert original_cell_v1(merged, {"row_id": "p15:r2", "column_id": "c1"})["page_json_version_id"] == head_vid
    assert original_cell_v1(merged, {"row_id": "p17:r1", "column_id": "c1"}) is None
    assert original_cell_v1(merged, {"row_id": "r1", "column_id": "c1"}) is None
    # One unproven fragment rejects the whole merged table.
    merged.fragment_bridges[1] = {"status": "MISMATCH:CELL_VALUE", "physical_page": 16}
    assert merged.bridge_failure() == "SOURCE_BRIDGE:MISMATCH:CELL_VALUE"


# ---------------------------------------------------------------- NotesSource binding and engine


def corpus(relative_path="bank/x.pdf", source_sha256="0" * 64):
    selected = SelectedPage(10, VID, "page-1", "FINANCIAL_NOTE_CONTENT", "f" * 64)
    document = SelectedDocument(1, relative_path, source_sha256, 1, 20, "plan", "manifest", "selection", (selected,))
    return CorpusSelection("full271", Path("/r"), Path("/r/index.json"), "1" * 64, "cmi", Path("/r/db.sqlite3"), "2" * 64,
                           (document,))


def loaded_item(original, *, logical_name="bank/x.pdf", source_sha256="0" * 64, physical_page=10, changes=()):
    return {"page_json_version_id": VID, "source_logical_name": logical_name, "source_sha256": source_sha256,
            "physical_page": physical_page, "page_json": original,
            "source_json_replay_receipt": {"canonical_json_sha256": "b" * 64, "replay_receipt_id": "r",
                                           "changed_tables": list(changes)}}


def test_loader_provenance_must_be_the_selected_corpus_page():
    original = page()
    source = NotesSource(corpus(), original_loader=lambda *a, **k: [])
    table = sql_table(validate_financial_page_json_v1(original))
    assert source._bridge_one(table, loaded_item(original))["status"] == EXACT
    for wrong in ({"logical_name": "bank/y.pdf"}, {"source_sha256": "9" * 64}, {"physical_page": 11}):
        assert source._bridge_one(table, loaded_item(original, **wrong))["status"] == "MISMATCH:PROVENANCE_NOT_SELECTED_PAGE"
    assert source._bridge_one(table, "ORIGINAL_LOAD_GeminiIncomeTaxSourcePageReplayV1Error")["status"].startswith("MISMATCH:ORIGINAL_LOAD")


def test_a_failing_original_is_isolated_and_bridges_are_cached_per_table():
    calls = []

    def loader(path, *, page_json_version_ids):
        calls.append(list(page_json_version_ids))
        if len(page_json_version_ids) > 1 or page_json_version_ids[0] != VID:
            raise ValueError("bad page")
        return [loaded_item(page())]

    other = "gfpstorev1:json:" + "c" * 64
    selection = corpus()
    pages = selection.documents[0].pages + (SelectedPage(11, other, "page-2", "FINANCIAL_NOTE_CONTENT", "e" * 64),)
    document = SelectedDocument(1, "bank/x.pdf", "0" * 64, 1, 20, "plan", "manifest", "selection", pages)
    source = NotesSource(CorpusSelection(*[getattr(selection, f) for f in ("name", "root", "index_path", "index_sha256",
                                                                          "corpus_manifest_index_id", "db_path", "db_sha256")],
                                         (document,)), original_loader=loader)
    good = sql_table(validate_financial_page_json_v1(page()))
    bad = sql_table(validate_financial_page_json_v1(page()), vid=other, physical_page=11)
    source._attach_bridges([good, bad])
    assert good.bridge["status"] == EXACT and bad.bridge["status"] == "MISMATCH:ORIGINAL_LOAD_ValueError"
    count = len(calls)
    source._attach_bridges([good, bad])
    assert len(calls) == count  # cached proofs, no second page load


def context(relative_path="bank/x.pdf", source_sha256="0" * 64, corpus_identity=None):
    return DocumentContext(
        ordinal=1, document_plan_id="plan", relative_path=relative_path, source_sha256=source_sha256, scope="CONSOLIDATED",
        scope_basis="PRIMARY_DOCUMENT_SCOPE", reporting_date="2025-06-30",
        balance_lanes=[{"key": "INSTANT:2025-06-30", "role": "CURRENT", "header": "30/06/2025"},
                       {"key": "INSTANT:2024-12-31", "role": "COMPARATIVE", "header": "31/12/2024"}],
        context_texts=["Tại ngày 30 tháng 6 năm 2025"], primary_cells={},
        separator_roles=SeparatorRoles(thousands=frozenset({"."})),
        corpus_identity=corpus().identity() if corpus_identity is None else corpus_identity)


class _FakeSource(NotesSource):
    def __init__(self, selection, tables, original):
        super().__init__(selection, original_loader=lambda *a, **k: [loaded_item(original)])
        self._tables = tables

    def candidate_tables(self, like_patterns):
        return {t.key: 1 for t in self._tables}

    def load_tables(self, keys):
        tables = [t for t in self._tables if t.key in set(keys)]
        self._attach_bridges(tables)
        return tables

    def outline(self):
        return {1: [_entry(10, VID, "NONE")]}


@pytest.fixture(scope="module")
def config():
    return load_notes_config_v1(ROOT)


def test_engine_binds_primary_context_by_identity_and_rejects_unbridged_tables(config):
    original = page()
    validated = validate_financial_page_json_v1(original)
    run = run_family_v1("CREDIT_QUALITY", config, _FakeSource(corpus(), [sql_table(validated)], original), {1: context()})
    assert [e.status for e in run.evaluations] == ["EVALUATED"]
    accepted = [c for c in run.cells if c["acceptance"] == "ACCEPTED"]
    assert accepted and all(c["original_cell"]["page_json_version_id"] == VID for c in accepted)
    # Same ordinal, different source document or different corpus: never an ordinal fallback.
    for wrong, reason in ((context(source_sha256="9" * 64), "PRIMARY_CONTEXT_DOCUMENT_IDENTITY_MISMATCH"),
                          (context(corpus_identity={**corpus().identity(), "corpus_name": "common204"}),
                           "PRIMARY_CONTEXT_CORPUS_IDENTITY_MISMATCH")):
        held = run_family_v1("CREDIT_QUALITY", config, _FakeSource(corpus(), [sql_table(validated)], original), {1: wrong})
        assert [(e.status, e.reasons) for e in held.evaluations] == [("REJECTED", [reason])] and held.cells == []
    missing = run_family_v1("CREDIT_QUALITY", config, _FakeSource(corpus(), [sql_table(validated)], original), {})
    assert [e.reasons for e in missing.evaluations] == [["PRIMARY_CONTEXT_MISSING"]]
    tampered = sql_table(validated)
    tampered.cells[("r2", "c1")] = ("5", "VALUE")
    rejected = run_family_v1("CREDIT_QUALITY", config, _FakeSource(corpus(), [tampered], original), {1: context()})
    assert [(e.status, e.reasons) for e in rejected.evaluations] == [("REJECTED", ["SOURCE_BRIDGE:MISMATCH:CELL_VALUE"])]
