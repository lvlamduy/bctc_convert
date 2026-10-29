"""UNRUN F36 retrieval scope tests: real source parity plus SQL metadata boundaries.

The two-source financial fixtures use actual page-store/PRIMARY/config rules.
The separate small title/neighbor database tests only retrieval metadata; it is
not an authenticated financial corpus and never enters evaluation or admission.
No passing financial/source validator is mocked.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest
from test_f36_notes_core_adapter_v1 import example as example
from test_f36_notes_stream_store_v1 import _two_actual

from bctc_ai.evaluation import gemini_json_f36_notes_core_adapter_v1 as adapter
from bctc_ai.evaluation import gemini_json_f36_notes_stream_store_v1 as storage
from bctc_ai.notes.config_v1 import load_notes_config_v1
from bctc_ai.notes.kernel_v1 import NotesSource, continuation_neighbors_v1
from bctc_ai.primary_statements.source_v1 import CorpusSelection, SelectedDocument, SelectedPage
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1

ROOT = Path(__file__).resolve().parents[2]


def _local(corpus, ordinal):
    owner = NotesSource(corpus)
    return adapter._F36DocumentScopedNotesSource(
        corpus, owner.metrics, original_loader=owner._original_loader,
        document=adapter._document_axis(corpus)[ordinal - 1],
    )


@pytest.mark.parametrize("ordinal", [1, 2])
def test_actual_two_sources_match_existing_full_query_then_document_filter(
    example, tmp_path, monkeypatch, ordinal,
):
    corpus, _trials, options = _two_actual(example, tmp_path, monkeypatch)
    before = corpus.db_path.read_bytes()
    full = NotesSource(corpus)
    local = _local(corpus, ordinal)
    patterns = load_notes_config_v1(ROOT).families[adapter.FAMILY].retrieval_patterns
    all_candidates = full.candidate_tables(patterns)
    expected = {key: hits for key, hits in all_candidates.items() if full.page_of[key[0]][0] == ordinal}
    assert expected and len(all_candidates) > len(expected)
    assert local.candidate_tables(patterns) == expected
    all_outline = full.outline()
    assert local.outline() == {key: value for key, value in all_outline.items() if key == ordinal}
    assert local.corpus is corpus and local.corpus.identity() == full.corpus.identity()
    assert local.page_of == full.page_of and local._documents == full._documents
    assert local._original_loader is full._original_loader
    assert set(local._f36_retrieval.page_of) == {
        page.page_json_version_id for page in corpus.documents[ordinal - 1].pages
    }
    # rows_read counts returned metadata, not SQLite physical scans or a timing gain.
    assert local.metrics.rows_read < full.metrics.rows_read
    assert corpus.db_path.read_bytes() == before
    assert len(options["compiled_specs"]["topology"]["source"]["document_axis"]) == 2


@pytest.mark.parametrize("mode", ["two-ready", "unrequested-U", "requested-unknown-primary-U"])
def test_actual_financial_trials_keep_exact_all_original_statuses_and_source_bytes(
    example, tmp_path, monkeypatch, mode,
):
    requested = [1] if mode == "unrequested-U" else None
    corpus, fixture_trials, options = _two_actual(example, tmp_path, monkeypatch, requested=requested)
    compiled = options["compiled_specs"]
    primary = Path(compiled["evaluation"]["primary_store_ref"]["path"])
    if mode == "requested-unknown-primary-U":
        # A coherent newly pinned PRIMARY counterfactual, not a passing validator mock.
        # Original financial JSON/value bytes stay unchanged; only explicit scope is absent.
        with closing(sqlite3.connect(primary)) as connection:
            raw = connection.execute("SELECT result_json FROM document_result WHERE document_ordinal=2").fetchone()[0]
            result = json.loads(raw)
            result["instances"][0]["scope"] = None
            connection.execute("UPDATE document_result SET result_json=? WHERE document_ordinal=2",
                               (json.dumps(result, ensure_ascii=False),))
            connection.commit()
        evaluation = deepcopy(compiled["evaluation"])
        evaluation["primary_store_ref"] = {
            "path": str(primary), "sha256": sha256(primary.read_bytes()).hexdigest(),
            "size_bytes": primary.stat().st_size,
        }
        compiled = adapter.compile_f36_notes_core_specs_v1(compiled["topology"], evaluation, compiled["schema"])
    snapshot = canonical_json_bytes_v1(compiled)
    source_bytes, primary_bytes = corpus.db_path.read_bytes(), primary.read_bytes()
    contexts = adapter.load_primary_context_v1(primary, compiled["evaluation"]["primary_store_ref"]["sha256"])
    config = load_notes_config_v1(ROOT)
    wanted = set(compiled["topology"]["documents_requested"])
    def parent_full_query_source(corpus, metrics, *, original_loader, document):
        # Parent83e used this real full-corpus SQL source for each original output.
        # The document keyword belongs only to the new constructor call boundary.
        return NotesSource(corpus, metrics, original_loader=original_loader)

    with monkeypatch.context() as parent_factory:
        parent_factory.setattr(adapter, "_F36DocumentScopedNotesSource", parent_full_query_source)
        original = list(adapter.iter_rebuild_f36_notes_trials_v1(
            source=NotesSource(corpus), contexts=contexts, config=config, compiled_specs=compiled,
        ))
    storage._check_bindings()  # Real factory restored before evaluating the candidate.
    current = list(adapter.iter_rebuild_f36_notes_trials_v1(
        source=NotesSource(corpus), contexts=contexts, config=config, compiled_specs=compiled,
    ))
    # Includes whole ledger, raw states, mappings, candidate IDs and observation evidence.
    assert canonical_json_bytes_v1(current) == canonical_json_bytes_v1(original)
    if mode != "requested-unknown-primary-U":
        assert canonical_json_bytes_v1(current) == canonical_json_bytes_v1(fixture_trials)
    else:
        assert contexts[2].scope is None and 2 in wanted
    assert [trial["document_ordinal"] for trial in current] == [1, 2]
    assert [trial["status"] for trial in current] == ["READY", "READY" if mode == "two-ready" else "UNRESOLVED"]
    assert [len(trial["mappings"]) for trial in current] == [4, 4 if mode == "two-ready" else 0]
    assert canonical_json_bytes_v1(compiled) == snapshot
    assert corpus.db_path.read_bytes() == source_bytes and primary.read_bytes() == primary_bytes


def _metadata_corpus(tmp_path, *, empty_second=False):
    """Only a tiny SQL title/neighbor protocol fixture, never financial authority."""
    database = tmp_path / "retrieval-metadata.sqlite3"
    documents = []
    for ordinal, physical_pages in ((1, (1, 2, 3)), (2, (1, 2))):
        pages = tuple(SelectedPage(
            physical_page=physical, page_json_version_id=f"gfpstorev1:json:{ordinal * 10 + physical:064x}",
            page_id=f"metadata-page-{ordinal}-{physical}", status="FINANCIAL_NOTE_CONTENT", image_sha256="a" * 64,
        ) for physical in physical_pages)
        documents.append(SelectedDocument(
            ordinal=ordinal, relative_path=f"metadata-only/{ordinal}.pdf", source_sha256=str(ordinal) * 64,
            source_size_bytes=10 + ordinal, page_count=len(pages), document_plan_id=f"metadata-plan-{ordinal}",
            document_manifest_id=f"metadata-manifest-{ordinal}",
            selection_id=f"metadata-selection-{ordinal}", pages=pages,
        ))
    with closing(sqlite3.connect(database)) as connection:
        connection.executescript("""
            CREATE TABLE section_node(page_json_version_id TEXT,section_id TEXT,source_order INTEGER,
                                      content_kind TEXT,title_exact TEXT);
            CREATE TABLE table_node(page_json_version_id TEXT,section_id TEXT,table_id TEXT,
                                    source_order INTEGER,title_exact TEXT,continuation TEXT);
            CREATE TABLE row_node(page_json_version_id TEXT,section_id TEXT,table_id TEXT,label_ascii_folded TEXT);
        """)
        for document in documents:
            if document.ordinal == 2 and empty_second:
                continue
            for selected in document.pages:
                if selected.physical_page == 3:  # Selected original page with no section/table rows.
                    continue
                version = selected.page_json_version_id
                continuation = (
                    "CONTINUES_ON_NEXT_PAGE" if selected.physical_page == 1 else "CONTINUES_FROM_PREVIOUS_PAGE"
                )
                connection.execute("INSERT INTO section_node VALUES (?,?,?,?,?)",
                                   (version, "s1", 1, "FINANCIAL_NOTE",
                                    f"source-{document.ordinal}-page-{selected.physical_page}"))
                connection.execute("INSERT INTO table_node VALUES (?,?,?,?,?,?)",
                                   (version, "s1", "t1", 1, "same-table-title", continuation))
                label = "chi phi nhan vien" if selected.physical_page == 1 else "carried row"
                connection.execute("INSERT INTO row_node VALUES (?,?,?,?)", (version, "s1", "t1", label))
        connection.commit()
    return CorpusSelection(
        name="METADATA_QUERY_ONLY_NO_FINANCIAL_AUTH", root=tmp_path,
        index_path=tmp_path / "unused-metadata-protocol-index.json", index_sha256="0" * 64,
        corpus_manifest_index_id="metadata-protocol-only", db_path=database,
        db_sha256=sha256(database.read_bytes()).hexdigest(), documents=tuple(documents),
    )


def test_same_document_adjacent_page_neighbors_and_all_selected_pages_are_preserved(tmp_path):
    corpus = _metadata_corpus(tmp_path)
    full, local = NotesSource(corpus), _local(corpus, 1)
    candidates = local.candidate_tables(["%chi phi%"])
    first, second, empty = corpus.documents[0].pages
    assert set(candidates) == {(first.page_json_version_id, "s1", "t1")}
    expected = {(second.page_json_version_id, "s1", "t1")}
    assert continuation_neighbors_v1(local, candidates) == expected
    assert continuation_neighbors_v1(full, candidates) == expected
    assert local.outline() == {1: full.outline()[1]}
    assert local.outline()[1][0]["title"] == "source-1-page-1"
    assert all(local.page_of[key[0]][0] == 1 for key in expected)
    assert empty.page_json_version_id in local._f36_retrieval.page_of
    assert all(page.page_json_version_id in local.page_of for document in corpus.documents for page in document.pages)
    assert not set(local._f36_retrieval.page_of) & {page.page_json_version_id for page in corpus.documents[1].pages}


def test_no_outline_stays_empty_without_manufacturing_a_document_entry(tmp_path):
    corpus = _metadata_corpus(tmp_path, empty_second=True)
    full, local = NotesSource(corpus), _local(corpus, 2)
    assert local.candidate_tables(["%chi phi%"]) == {}
    assert local.outline() == {key: value for key, value in full.outline().items() if key == 2} == {}
    assert len(local._f36_retrieval.page_of) == 2 and len(local.page_of) == 5


@pytest.mark.parametrize("attack", [
    "bool_ordinal", "unknown_ordinal", "foreign_identity", "identity_source_sha", "missing_page",
    "duplicate_page", "reordered_pages", "foreign_vid", "wrong_physical_page",
])
def test_retrieval_constructor_rejects_wrong_identity_or_incomplete_membership(tmp_path, attack):
    corpus = _metadata_corpus(tmp_path)
    document = deepcopy(adapter._document_axis(corpus)[0])
    if attack == "bool_ordinal":
        document["document_ordinal"] = True
    elif attack == "unknown_ordinal":
        document["document_ordinal"] = 99
    elif attack == "foreign_identity":
        document["document_identity"] = corpus.documents[1].identity()
    elif attack == "identity_source_sha":
        document["document_identity"]["source_sha256"] = "f" * 64
    elif attack == "missing_page":
        document["pages"].pop()  # Even the page with no title/table rows cannot be omitted.
    elif attack == "duplicate_page":
        document["pages"].append(deepcopy(document["pages"][0]))
    elif attack == "reordered_pages":
        document["pages"].reverse()
    elif attack == "foreign_vid":
        document["pages"][0]["page_json_version_id"] = corpus.documents[1].pages[0].page_json_version_id
    else:
        document["pages"][0]["physical_page"] = 99
    owner = NotesSource(corpus)
    with pytest.raises(adapter.F36NotesCoreAdapterError, match="F36 retrieval"):
        adapter._F36DocumentRetrievalView(owner, document)


def test_retrieval_rejects_owner_membership_disagreeing_with_its_document(tmp_path):
    corpus = _metadata_corpus(tmp_path)
    owner = NotesSource(corpus)
    document = adapter._document_axis(corpus)[0]
    owner.page_of[document["pages"][0]["page_json_version_id"]] = (2, 1)
    with pytest.raises(adapter.F36NotesCoreAdapterError, match="membership"):
        adapter._F36DocumentRetrievalView(owner, document)


def test_public_iterator_rejects_top_level_source_sha_mismatch_at_full_compile_guard(
    example, tmp_path, monkeypatch,
):
    corpus, _trials, options = _two_actual(example, tmp_path, monkeypatch)
    compiled = deepcopy(options["compiled_specs"])
    primary_ref = compiled["evaluation"]["primary_store_ref"]
    contexts = adapter.load_primary_context_v1(Path(primary_ref["path"]), primary_ref["sha256"])
    compiled["topology"]["source"]["document_axis"][0]["source_sha256"] = "f" * 64
    with pytest.raises(adapter.F36NotesCoreAdapterError, match="Nested document identity"):
        list(adapter.iter_rebuild_f36_notes_trials_v1(
            source=NotesSource(corpus), contexts=contexts, config=load_notes_config_v1(ROOT), compiled_specs=compiled,
        ))


@pytest.mark.parametrize("class_name,method", [
    ("_F36DocumentRetrievalView", "_connect"),
    ("_F36DocumentRetrievalView", "candidate_tables"),
    ("_F36DocumentRetrievalView", "outline"),
    ("_F36DocumentScopedNotesSource", "__init__"),
    ("_F36DocumentScopedNotesSource", "candidate_tables"),
])
def test_existing_producer_binding_scanner_rejects_replaced_new_classes_and_aliases(
    monkeypatch, class_name, method,
):
    owner = getattr(adapter, class_name)
    original = vars(owner)[method]
    assert any(bound_owner is owner and name == method and value is original
               for bound_owner, name, value in storage._PRODUCER_BINDINGS)
    storage._check_bindings()

    def replacement(*_args, **_kwargs):
        raise AssertionError("A replaced retrieval method must not execute")

    monkeypatch.setattr(owner, method, replacement)
    with pytest.raises(adapter.F36NotesCoreAdapterError, match="producer callable binding changed"):
        storage._check_bindings()
