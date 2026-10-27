"""UNRUN stage-2 tiny actual-source goldens and negative persistence controls.

Definitions only: author did not execute Python, SQLite, tests or corpus jobs.
The positive cases use real source/PRIMARY/config/financial rules, no replay or
financial validator mocks. Injection tests explicitly corrupt a later boundary.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
from test_f36_notes_core_adapter_v1 import example as example
from test_f36_notes_core_canonical_store_v1 import _put, _ref, _source_fixture
from test_f36_notes_whole_stream_v1 import _old_sweep, _real_source_case
from test_gemini_income_tax_raw_money_census_v1 import _fixture

from bctc_ai.evaluation import gemini_json_f36_notes_core_adapter_v1 as adapter
from bctc_ai.evaluation import gemini_json_f36_notes_stream_v1 as spool
from bctc_ai.evaluation import gemini_json_f36_notes_stream_store_v1 as target
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1, canonical_json_sha256_v1
from bctc_ai.storage import gemini_accounting_family_store_v1 as old_store
from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import build_current_corpus_manifest_index_v1
from bctc_ai.storage.gemini_current_document_manifest_selection_v1 import build_current_document_manifest_selection_v1
from bctc_ai.storage.gemini_financial_page_store_v1 import build_financial_document_manifest_v1

ROOT = Path(__file__).resolve().parents[2]


def _pins():
    return [_ref(path) for path in sorted((ROOT / "src/bctc_ai").rglob("*.py"), key=str)]


def _case(example, tmp_path, monkeypatch, *, compact=False, interim_q4=False):
    corpus, contexts, compiled = _real_source_case(example, tmp_path, monkeypatch,
                                                  compact=compact, interim_q4=interim_q4)
    source = adapter.NotesSource(corpus)
    policies = source.annual_policies_v1({n: c.scope for n, c in contexts.items()})
    old_contexts = {n: replace(c, annual_policy=policies.get(n)) for n, c in contexts.items()}
    trials = adapter.rebuild_f36_notes_trials_v1(source=source, contexts=old_contexts,
        config=adapter.load_notes_config_v1(ROOT), compiled_specs=compiled)
    report = spool.write_f36_notes_sweep_spool_v1(trials=iter(trials), compiled_specs=compiled,
        corpus_manifest_index_id=corpus.corpus_manifest_index_id, scratch_directory=tmp_path / "spool")
    options = {"spool_report": report, "compiled_specs": compiled,
               "implementation_refs": [_ref(Path(adapter.__file__))], "producer_refs": _pins()}
    return corpus, trials, options


def _no_rows(path):
    if path.exists():
        with sqlite3.connect(path) as connection:
            for table in ("family_run", "family_trial", "family_candidate", "family_mapping", "family_run_execution",
                          "family_current_selection", "family_selection_event"):
                assert connection.execute("SELECT COUNT(*) FROM " + table).fetchone() == (0,)


@pytest.mark.parametrize("compact", [False, True])
@pytest.mark.parametrize("interim_q4", [False, True])
def test_actual_source_old_new_store_same_run_id_whole_blob_normalized_traces_and_original_accessor(
    example, tmp_path, monkeypatch, compact, interim_q4,
):
    corpus, trials, options = _case(example, tmp_path, monkeypatch, compact=compact, interim_q4=interim_q4)
    compiled = options["compiled_specs"]
    old_sweep = _old_sweep(compiled, trials, corpus.corpus_manifest_index_id)
    snapshot = tmp_path / "source-snapshot.sqlite3"
    shutil.copyfile(corpus.db_path, snapshot)
    old_path, new_path = tmp_path / "old.sqlite3", tmp_path / "streamed.sqlite3"
    legacy = old_store.ingest_gemini_accounting_family_sweep_v1(old_path, sweep=old_sweep,
        corpus_index_ref=_ref(corpus.index_path), implementation_refs=options["implementation_refs"], run_kind="EXPERIMENTAL",
        source_page_database=snapshot, corpus_artifact_root=corpus.root,
        selected_page_json_version_ids=[p.page_json_version_id for d in corpus.documents for p in d.pages],
        source_replay_adapter=adapter.replay_f36_notes_core_trials_from_source_v1,
        source_replay_adapter_ref=options["implementation_refs"][0])
    actual = target.ingest_f36_notes_streamed_sweep_v1(new_path, **options)
    for key in ("family_run_id", "family_id", "run_kind", "sweep_id", "sweep_sha256"):
        assert actual[key] == legacy[key]
    # Tiny fixture only: the test oracle may select a whole BLOB. Production never does.
    with sqlite3.connect(old_path) as left, sqlite3.connect(new_path) as right:
        assert left.execute("SELECT * FROM family_run").fetchall() == right.execute("SELECT * FROM family_run").fetchall()
        for table in ("family_trial", "family_candidate", "family_mapping"):
            assert left.execute("SELECT * FROM " + table + " ORDER BY 1,2,3").fetchall() == right.execute(
                "SELECT * FROM " + table + " ORDER BY 1,2,3").fetchall()
        assert right.execute("SELECT sweep_bytes FROM family_run").fetchone()[0] == canonical_json_bytes_v1(old_sweep) + b"\n"
        assert right.execute("SELECT run_kind FROM family_run_execution").fetchall() == [("EXPERIMENTAL",)]
        assert right.execute("SELECT COUNT(*) FROM family_current_selection").fetchone() == (0,)
        assert right.execute("SELECT COUNT(*) FROM family_selection_event").fetchone() == (0,)
        assert right.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
    with target.open_f36_notes_streamed_run_v1(new_path, **options) as reader:
        assert canonical_json_bytes_v1(reader.original_trial(1)) == canonical_json_bytes_v1(trials[0])
        with pytest.raises(adapter.F36NotesCoreAdapterError):
            reader.original_trial(True)
    with pytest.raises(adapter.F36NotesCoreAdapterError):
        reader.original_trial(1)


def _two_actual(example, tmp_path, monkeypatch, *, requested=None):
    """Two independently ingested real source records, not a declared fake slot."""
    seed = tmp_path / "seed"
    seed.mkdir()
    _corpus, page = _source_fixture(seed, monkeypatch, interim_q4=False)
    transport = tmp_path / "transport"
    transport.mkdir()
    options, old_index, _ = _fixture(transport, monkeypatch, pages=[page], documents=2)
    root = tmp_path / "authority"
    root.mkdir()
    database = root / "source.sqlite3"
    shutil.copyfile(options["database"], database)
    documents = []
    for original in old_index["documents"]:
        document = deepcopy(original)
        ordinal = document["source_ordinal"]
        manifest = build_financial_document_manifest_v1(database, source_sha256=document["source_sha256"],
            source_logical_name=document["relative_path"], expected_physical_pages=[1], prompt_sha256="d" * 64,
            response_schema_sha256="e" * 64, requested_model="gemini-3.7-flash", requested_service_tier="flex",
            selected_provider="GOOGLE_GEMINI_API")
        local_manifest = "current-document-manifests/complete.json"
        manifest_ref = _put(root, f"documents/{ordinal}/" + local_manifest, manifest)
        selection = build_current_document_manifest_selection_v1(document_plan_id=document["document_plan_id"],
            source_sha256=document["source_sha256"], document_manifest_id=manifest["document_manifest_id"],
            document_manifest_ref={**manifest_ref, "path": local_manifest},
            page_image_frontier_sha256=canonical_json_sha256_v1([
                {"physical_page": p["physical_page"], "image_sha256": p["image"]["sha256"]} for p in manifest["pages"]]),
            page_prompt_frontier_sha256=canonical_json_sha256_v1([{"physical_page": 1, "prompt_variant": "compact"}]),
            prior_selection_ids=[])
        selection_ref = _put(root, f"documents/{ordinal}/current-document-manifest-selections/"
            + selection["selection_id"].split(":", 2)[2] + ".json", selection)
        document.update(document_manifest_id=manifest["document_manifest_id"], document_manifest_ref=manifest_ref,
            selection_id=selection["selection_id"], selection_ref=selection_ref,
            page_json_frontier_sha256=canonical_json_sha256_v1(manifest["pages"]))
        documents.append(document)
    index = build_current_corpus_manifest_index_v1(**{k: old_index[k] for k in (
        "corpus_plan_id", "corpus_run_id", "corpus_plan_ref", "database_ref", "ledger_ref", "store_usage_summary")},
        documents=documents)
    index_ref = _put(root, "indexes/complete.json", index)
    corpus = adapter.load_corpus_selection_v1(name="two-actual-f36", root=root, index_relative_path=index_ref["path"],
        expected_index_sha256=index_ref["sha256"], expected_db_sha256=index["database_ref"]["sha256"])
    production, _trial, _index = example
    topology = deepcopy(production["topology"])
    topology["source"] = {"corpus_name": corpus.name, "artifact_root": str(root), "index_ref": _ref(corpus.index_path),
        "database_ref": _ref(database), "corpus_identity": corpus.identity(), "document_axis": adapter._document_axis(corpus)}
    topology["documents_requested"] = [1, 2] if requested is None else requested
    evaluation = deepcopy(production["evaluation"])
    primary = tmp_path / "primary.sqlite3"
    with sqlite3.connect(primary) as connection:
        connection.execute("CREATE TABLE document_result(document_ordinal INTEGER PRIMARY KEY, result_json TEXT NOT NULL)")
        for document in corpus.documents:
            result = {"document": document.identity(), "corpus": corpus.identity(), "notes_start_page": 1,
                "cells": [], "instances": [{"presentation_role": "PRIMARY", "scope": "SEPARATE", "statement": "KQKD",
                    "period_context": {"evidence": ["Cho năm tài chính kết thúc ngày 31 tháng 12 năm 2025"]},
                    "tables": [], "lanes": [{"period": {"key": f"DURATION:YEAR:{year}"}} for year in (2025, 2024)]}]}
            connection.execute("INSERT INTO document_result VALUES (?,?)", (document.ordinal, json.dumps(result, ensure_ascii=False)))
    evaluation["primary_store_ref"] = _ref(primary)
    for key in evaluation["frontier_receipt_refs"]:
        path = tmp_path / (key + ".json")
        path.write_bytes(canonical_json_bytes_v1({"fixture": key}))
        evaluation["frontier_receipt_refs"][key] = _ref(path)
    compiled = adapter.compile_f36_notes_core_specs_v1(topology, evaluation, production["schema"])
    contexts = adapter.load_primary_context_v1(primary, evaluation["primary_store_ref"]["sha256"])
    trials = list(adapter.iter_rebuild_f36_notes_trials_v1(source=adapter.NotesSource(corpus), contexts=contexts,
        config=adapter.load_notes_config_v1(ROOT), compiled_specs=compiled))
    assert [t["document_ordinal"] for t in trials] == [1, 2]
    assert [t["status"] for t in trials] == ["READY" if n in topology["documents_requested"] else "UNRESOLVED" for n in (1, 2)]
    report = spool.write_f36_notes_sweep_spool_v1(trials=iter(trials), compiled_specs=compiled,
        corpus_manifest_index_id=corpus.corpus_manifest_index_id, scratch_directory=tmp_path / "spool")
    return corpus, trials, {"spool_report": report, "compiled_specs": compiled,
        "implementation_refs": [_ref(Path(adapter.__file__))], "producer_refs": _pins()}


@pytest.mark.parametrize("requested", [[1, 2], [1]], ids=["both-requested", "second-original-outside-request"])
def test_two_actual_originals_persist_one_full_run_without_subsetting(example, tmp_path, monkeypatch, requested):
    corpus, trials, options = _two_actual(example, tmp_path, monkeypatch, requested=requested)
    path = tmp_path / "whole.sqlite3"
    receipt = target.ingest_f36_notes_streamed_sweep_v1(path, **options)
    expected = _old_sweep(options["compiled_specs"], trials, corpus.corpus_manifest_index_id)
    assert receipt["sweep_id"] == expected["sweep_id"]
    with target.open_f36_notes_streamed_run_v1(path, **options) as reader:
        assert [reader.original_trial(n) for n in (1, 2)] == trials
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM family_run").fetchone() == (1,)
        assert connection.execute("SELECT document_ordinal FROM family_trial ORDER BY document_ordinal").fetchall() == [(1,), (2,)]
        assert connection.execute("SELECT sweep_bytes FROM family_run").fetchone() == (canonical_json_bytes_v1(expected) + b"\n",)
        if requested == [1]:
            assert trials[1]["reasons"] == ["DOCUMENT_OUTSIDE_REQUESTED_SCOPE"]
            assert trials[1]["notes_ledger"]["scope"] == "NOT_EVALUATED_REQUESTED_SUBSET_ONLY"
            assert connection.execute("SELECT status,mapping_count FROM family_trial WHERE document_ordinal=2").fetchone() == ("UNRESOLVED", 0)


@pytest.mark.parametrize("attack", ["missing", "duplicate", "reorder", "extra"])
def test_private_cold_comparison_requires_exact_full_original_axis(example, tmp_path, monkeypatch, attack):
    _corpus, _trials, options = _two_actual(example, tmp_path, monkeypatch)
    with target._Proposal(options["spool_report"], options["compiled_specs"],
                          options["implementation_refs"], options["producer_refs"]) as proposal:
        with target._fresh_source(proposal) as actual:
            rebuilt = list(actual)
        if attack == "missing":
            rebuilt.pop()
        elif attack == "duplicate":
            rebuilt[1] = deepcopy(rebuilt[0])
        elif attack == "reorder":
            rebuilt.reverse()
        else:
            rebuilt.append(deepcopy(rebuilt[-1]))
        with pytest.raises(adapter.F36NotesCoreAdapterError, match="fresh cold"):
            target._compare_cold(proposal, iter(rebuilt))
    assert not list(tmp_path.glob("failed*.sqlite3"))


@pytest.mark.parametrize("spoof", [False, True], ids=["actual-cold-mismatch", "saved-trial-callable-replacement"])
def test_actual_new_primary_context_cannot_replay_an_old_structurally_valid_trial(example, tmp_path, monkeypatch, spoof):
    corpus, trials, options = _case(example, tmp_path, monkeypatch)
    compiled = options["compiled_specs"]
    primary = Path(compiled["evaluation"]["primary_store_ref"]["path"])
    with sqlite3.connect(primary) as connection:
        result = json.loads(connection.execute("SELECT result_json FROM document_result").fetchone()[0])
        result["instances"] = []
        connection.execute("UPDATE document_result SET result_json=?", (json.dumps(result, ensure_ascii=False),))
    evaluation = {**compiled["evaluation"], "primary_store_ref": _ref(primary)}
    compiled = adapter.compile_f36_notes_core_specs_v1(compiled["topology"], evaluation, compiled["schema"])
    report = spool.write_f36_notes_sweep_spool_v1(trials=iter(trials), compiled_specs=compiled,
        corpus_manifest_index_id=corpus.corpus_manifest_index_id, scratch_directory=tmp_path / "old-decisions-new-primary")
    options.update(compiled_specs=compiled, spool_report=report)
    if spoof:
        monkeypatch.setattr(adapter, "iter_rebuild_f36_notes_trials_v1", lambda **_kwargs: iter(trials))
    path = tmp_path / "failed.sqlite3"
    with pytest.raises(adapter.F36NotesCoreAdapterError, match="callable binding" if spoof else "fresh cold"):
        target.ingest_f36_notes_streamed_sweep_v1(path, **options)
    _no_rows(path)
    assert path.exists() is (not spoof)


@pytest.mark.parametrize("attack", ["spool", "receipt", "compiled", "query", "history_added", "store_identity"])
def test_late_held_input_or_control_change_rolls_back_all_proposal_rows(example, tmp_path, monkeypatch, attack):
    corpus, _trials, options = _case(example, tmp_path, monkeypatch)
    original = target._insert_trial
    injected = []

    def late(connection, run_id, trial, raw):
        original(connection, run_id, trial, raw)
        assert connection.in_transaction
        assert connection.execute("SELECT COUNT(*) FROM family_run").fetchone() == (1,)
        assert connection.execute("SELECT COUNT(*) FROM family_trial").fetchone() == (1,)
        injected.append(attack)
        if attack == "spool":
            path = Path(options["spool_report"]["sweep_ref"]["path"])
            with path.open("r+b") as handle:
                handle.seek(-1, 2)
                handle.write(b" ")
        elif attack == "receipt":
            path = Path(next(iter(options["compiled_specs"]["evaluation"]["frontier_receipt_refs"].values()))["path"])
            with path.open("ab") as handle:
                handle.write(b"\n")
        elif attack == "compiled":
            options["compiled_specs"]["topology"]["documents_requested"] = []
        elif attack == "query":
            options["spool_report"]["indexed_query_evidence"]["trial_frontier"].clear()
        elif attack == "store_identity":
            connection.execute("UPDATE store_identity SET format_version='tampered'")
        else:
            selection = next(corpus.root.glob("documents/*/current-document-manifest-selections/*.json"))
            (selection.parent / "added.json").write_bytes(b"{}\n")

    monkeypatch.setattr(target, "_insert_trial", late)
    path = tmp_path / "failed.sqlite3"
    with pytest.raises(adapter.F36NotesCoreAdapterError):
        target.ingest_f36_notes_streamed_sweep_v1(path, **options)
    assert injected == [attack]
    _no_rows(path)


@pytest.mark.parametrize("which", ["source", "primary"])
@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_source_and_primary_sidecars_fail_closed_before_ingest(example, tmp_path, monkeypatch, which, suffix):
    corpus, _trials, options = _case(example, tmp_path, monkeypatch)
    database = corpus.db_path if which == "source" else Path(options["compiled_specs"]["evaluation"]["primary_store_ref"]["path"])
    Path(str(database) + suffix).write_bytes(b"untrusted-sidecar")
    path = tmp_path / "failed.sqlite3"
    with pytest.raises(adapter.F36NotesCoreAdapterError, match="sidecar"):
        target.ingest_f36_notes_streamed_sweep_v1(path, **options)
    assert not path.exists()


@pytest.mark.parametrize("attack", ["trial", "candidate", "mapping", "blob", "schema", "execution", "missing_trace"])
def test_complete_committed_readback_rejects_every_trace_and_whole_blob_drift(example, tmp_path, monkeypatch, attack):
    _corpus, _trials, options = _case(example, tmp_path, monkeypatch)
    path = tmp_path / "stored.sqlite3"
    target.ingest_f36_notes_streamed_sweep_v1(path, **options)
    with sqlite3.connect(path) as connection:
        if attack == "trial":
            connection.execute("UPDATE family_trial SET reasons_json=?", (b'["tampered"]\n',))
        elif attack == "candidate":
            connection.execute("UPDATE family_candidate SET candidate_bytes=?", (b"{}\n",))
        elif attack == "mapping":
            connection.execute("UPDATE family_mapping SET row_id='foreign-row'")
        elif attack == "blob":
            rowid = connection.execute("SELECT rowid FROM family_run").fetchone()[0]
            with connection.blobopen("family_run", "sweep_bytes", rowid) as blob:
                blob.seek(1)
                blob.write(b" ")
        elif attack == "schema":
            connection.execute("CREATE TABLE unrelated(value TEXT)")
        elif attack == "execution":
            connection.execute("UPDATE family_run_execution SET run_kind='OFFICIAL'")
        else:
            connection.execute("DELETE FROM family_mapping WHERE mapping_ordinal=1")
    with pytest.raises(adapter.F36NotesCoreAdapterError):
        with target.open_f36_notes_streamed_run_v1(path, **options):
            pytest.fail("tampered run must not issue an original-trial reader")


def test_exclusive_store_official_fence_complete_producer_pins_and_no_callback_api(example, tmp_path, monkeypatch):
    _corpus, _trials, options = _case(example, tmp_path, monkeypatch)
    path = tmp_path / "stored.sqlite3"
    with pytest.raises(adapter.F36NotesCoreAdapterError, match="EXPERIMENTAL"):
        target.ingest_f36_notes_streamed_sweep_v1(path, **options, run_kind="OFFICIAL")
    with pytest.raises(TypeError):
        target.ingest_f36_notes_streamed_sweep_v1(path, **options, source_replay_adapter=lambda: [])
    omitted = {**options, "producer_refs": options["producer_refs"][:-1]}
    with pytest.raises(adapter.F36NotesCoreAdapterError, match="producer"):
        target.ingest_f36_notes_streamed_sweep_v1(path, **omitted)
    missing_adapter = {**options, "implementation_refs": [_ref(Path(spool.__file__))]}
    with pytest.raises(adapter.F36NotesCoreAdapterError, match="implementation axis"):
        target.ingest_f36_notes_streamed_sweep_v1(path, **missing_adapter)
    path.write_bytes(b"keep-existing")
    with pytest.raises(adapter.F36NotesCoreAdapterError, match="exclusive"):
        target.ingest_f36_notes_streamed_sweep_v1(path, **options)
    assert path.read_bytes() == b"keep-existing"
