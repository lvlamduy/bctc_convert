"""UNRUN bounded synthetic whole-axis controls; no whole-corpus/persistence claim."""
from __future__ import annotations

import json
import os
import sqlite3
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest
from test_f36_notes_compact_source_proof_v1 import compact_example as compact_example
from test_f36_notes_core_adapter_v1 import example as example
from test_f36_notes_core_adapter_v1 import reseal_trial
from test_f36_notes_core_canonical_store_v1 import _ref, _source_fixture

from bctc_ai.evaluation import gemini_json_f36_notes_core_adapter_v1 as adapter
from bctc_ai.evaluation import gemini_json_f36_notes_stream_v1 as stream
from bctc_ai.notes.config_v1 import load_notes_config_v1
from bctc_ai.notes.kernel_v1 import NotesSource, load_primary_context_v1
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1, canonical_json_sha256_v1
from bctc_ai.storage.gemini_accounting_family_store_v1 import _checked_implementation_refs

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(params=[False, True], ids=["full", "compact"])
def two_axis(request, example, compact_example):
    """Two declared original slots; the second is explicitly outside the request.

    Structural declarations only. No fake second source DB record is admitted;
    actual source replay is exercised separately on a real tiny source store.
    """
    if request.param:
        compiled, trial, index_id, _page = deepcopy(compact_example)
    else:
        compiled, trial, index_id = deepcopy(example)
    topology = deepcopy(compiled["topology"])
    second = deepcopy(topology["source"]["document_axis"][0])
    second.update(document_ordinal=2, source_logical_name="synthetic-other.pdf", source_sha256="3" * 64)
    second["document_identity"].update(document_ordinal=2, relative_path="synthetic-other.pdf", source_sha256="3" * 64)
    second["pages"][0]["page_json_version_id"] = "gfpstorev1:json:" + "4" * 64
    topology["source"]["document_axis"].append(second)
    compiled = adapter.compile_f36_notes_core_specs_v1(topology, compiled["evaluation"], compiled["schema"])
    ledger = {key: [] for key in ("cells", "classifications", "retained", "dispositions", "root_closures",
              "source_ledger", "production_policy_receipts", "primary_income_context_texts")}
    ledger["scope"] = "NOT_EVALUATED_REQUESTED_SUBSET_ONLY"
    if request.param:
        ledger["source_partition"] = adapter._source_partition(second, compiled, [])
    outside = {"document_ordinal": 2, "source_logical_name": second["source_logical_name"],
               "source_sha256": second["source_sha256"], "status": "UNRESOLVED", "candidate_count": 0,
               "candidates": [], "selected_candidate_id": None, "mappings": [],
               "reasons": ["DOCUMENT_OUTSIDE_REQUESTED_SCOPE"], "notes_ledger": ledger}
    return compiled, [trial, outside], index_id


def _old_sweep(compiled, trials, index_id):
    query = adapter.build_f36_notes_query_evidence_v1(trials=trials, compiled_specs=compiled)
    return adapter.build_f36_notes_core_sweep_v1(
        corpus_manifest_index_id=index_id, topology_spec=compiled["topology"],
        evaluation_spec=compiled["evaluation"], schema_binding_spec=compiled["schema"],
        trials=trials, indexed_query_evidence=query,
    )


def _write(tmp_path, compiled, trials, index_id, **kwargs):
    return stream.write_f36_notes_sweep_spool_v1(
        trials=iter(trials), compiled_specs=compiled, corpus_manifest_index_id=index_id,
        scratch_directory=tmp_path / "proposal", **kwargs,
    )


def test_whole_stream_exact_old_bytes_query_candidates_ids_and_all_original_slots(two_axis, tmp_path):
    compiled, trials, index_id = two_axis
    before = canonical_json_bytes_v1({"compiled": compiled, "trials": trials})
    old = _old_sweep(compiled, trials, index_id)
    report = _write(tmp_path, compiled, trials, index_id, expected_query_evidence=old["indexed_query_evidence"])
    actual = Path(report["sweep_ref"]["path"]).read_bytes()
    assert actual == canonical_json_bytes_v1(old) + b"\n"
    assert actual.endswith(b"\n\n") and not actual.endswith(b"\n\n\n")
    assert report["sweep_id"] == old["sweep_id"]
    assert report["metrics"] == old["metrics"]
    assert report["indexed_query_evidence"] == old["indexed_query_evidence"]
    decoded = json.loads(actual)
    assert [t["document_ordinal"] for t in decoded["trials"]] == [1, 2]
    assert canonical_json_bytes_v1(decoded["trials"][0]["candidates"]) == canonical_json_bytes_v1(trials[0]["candidates"])
    assert decoded["trials"][1]["reasons"] == ["DOCUMENT_OUTSIDE_REQUESTED_SCOPE"]
    assert canonical_json_bytes_v1({"compiled": compiled, "trials": trials}) == before
    refs = [{"path": "/synthetic/z.py", "sha256": "c" * 64, "size_bytes": 2},
            {"path": "/synthetic/a.py", "sha256": "d" * 64, "size_bytes": 3}]
    old_run = "gjfafstorev1:run:" + canonical_json_sha256_v1({
        "corpus_index_sha256": "a" * 64,
        "implementation_axis_sha256": canonical_json_sha256_v1(_checked_implementation_refs(refs)),
        "sweep_id": old["sweep_id"], "sweep_sha256": sha256(canonical_json_bytes_v1(old) + b"\n").hexdigest(),
    })
    assert stream.derive_f36_notes_proposed_run_id_v1(
        corpus_index_sha256="a" * 64, implementation_refs=refs,
        sweep_id=report["sweep_id"], sweep_sha256=report["sweep_ref"]["sha256"],
    ) == old_run
    assert report["stage_boundary"] == stream.STAGE_BOUNDARY
    assert report["sqlite_ingest_cold_replay_and_persisted_readback"] == "NOT_IMPLEMENTED"
    assert not list((tmp_path / "proposal").glob("*.sqlite3"))
    assert not (tmp_path / "proposal" / "COMPLETE").exists()


def test_offsets_hash_the_exact_original_canonical_trial_bytes(two_axis, tmp_path):
    compiled, trials, index_id = two_axis
    report = _write(tmp_path, compiled, trials, index_id)
    array = Path(report["trial_array_ref"]["path"]).read_bytes()
    assert json.loads(array) == trials
    for offset, trial in zip(report["trial_offsets"], trials, strict=True):
        raw = array[offset["offset"]:offset["offset"] + offset["size_bytes_without_lf"]] + b"\n"
        assert raw == canonical_json_bytes_v1(trial)
        assert sha256(raw).hexdigest() == offset["trial_one_lf_sha256"]


@pytest.mark.parametrize("attack", ["missing_tail", "duplicate", "reorder", "extra", "bool_ordinal"])
def test_complete_axis_never_silently_skips_duplicates_or_renumbers(two_axis, tmp_path, attack):
    compiled, trials, index_id = deepcopy(two_axis)
    if attack == "missing_tail":
        trials.pop()
    elif attack == "duplicate":
        trials[1] = deepcopy(trials[0])
    elif attack == "reorder":
        trials.reverse()
    elif attack == "extra":
        trials.append(deepcopy(trials[1]))
    else:
        trials[0]["document_ordinal"] = True
    with pytest.raises(adapter.F36NotesCoreAdapterError):
        _write(tmp_path, compiled, trials, index_id)
    assert not (tmp_path / "proposal" / "f36-whole-sweep.json").exists()


@pytest.mark.parametrize("attack", ["numeric", "blank", "root_evidence", "query"])
def test_same_financial_source_and_query_checks_remain_required(two_axis, tmp_path, attack):
    compiled, trials, index_id = deepcopy(two_axis)
    query = adapter.build_f36_notes_query_evidence_v1(trials=trials, compiled_specs=compiled)
    if attack == "numeric":
        trials[0]["mappings"][0]["values"][0]["coefficient"] += 1
        reseal_trial(trials[0])
    elif attack == "blank":
        trials[0]["notes_ledger"]["cells"][0]["raw"] = None
        reseal_trial(trials[0])
    elif attack == "root_evidence":
        trials[0]["notes_ledger"]["root_closures"].clear()
        reseal_trial(trials[0])
    else:
        query["trial_frontier"].pop()
        material = {k: v for k, v in query.items() if k != "query_evidence_id"}
        query["query_evidence_id"] = "gjf36nieqv1:evidence:" + canonical_json_sha256_v1(material)
    with pytest.raises((adapter.F36NotesCoreAdapterError, TypeError, ValueError)):
        _write(tmp_path, compiled, trials, index_id, expected_query_evidence=query)


def test_late_declared_input_change_after_last_trial_is_not_completion(two_axis, tmp_path):
    compiled, trials, index_id = deepcopy(two_axis)

    def changed():
        yield from trials
        compiled["topology"]["documents_requested"].append(2)

    with pytest.raises(adapter.F36NotesCoreAdapterError, match="late compiled input change"):
        _write(tmp_path, compiled, changed(), index_id)
    assert not (tmp_path / "proposal" / "f36-whole-sweep.json").exists()


def test_changed_earlier_spool_bytes_are_detected_at_whole_hash_barrier(two_axis, tmp_path):
    compiled, trials, index_id = two_axis

    def changed():
        yield trials[0]
        with (tmp_path / "proposal" / "trials-array.json").open("r+b", buffering=0) as handle:
            handle.write(b"{")  # Same-length corruption of the independently hashed '['.
            os.fsync(handle.fileno())
        yield trials[1]

    with pytest.raises(adapter.F36NotesCoreAdapterError, match="held spool bytes"):
        _write(tmp_path, compiled, changed(), index_id)
    assert not (tmp_path / "proposal" / "f36-whole-sweep.json").exists()


def test_expected_query_is_frozen_before_generator_can_change_it(two_axis, tmp_path):
    compiled, trials, index_id = two_axis
    query = adapter.build_f36_notes_query_evidence_v1(trials=trials, compiled_specs=compiled)
    query["query_evidence_id"] = "gjf36nieqv1:evidence:" + "0" * 64

    def changed():
        # Replacing a formerly wrong expectation with the eventual correct
        # value cannot make the original caller control valid retroactively.
        correct = adapter.build_f36_notes_query_evidence_v1(trials=trials, compiled_specs=compiled)
        query.clear()
        query.update(correct)
        yield from trials

    with pytest.raises(adapter.F36NotesCoreAdapterError, match="late expected query input change"):
        _write(tmp_path, compiled, changed(), index_id, expected_query_evidence=query)
    assert not (tmp_path / "proposal" / "f36-whole-sweep.json").exists()


def test_exclusive_output_collision_preserves_every_old_byte(two_axis, tmp_path):
    compiled, trials, index_id = two_axis
    _write(tmp_path, compiled, trials, index_id)
    before = {p.name: p.read_bytes() for p in (tmp_path / "proposal").iterdir()}
    with pytest.raises(adapter.F36NotesCoreAdapterError, match="new directory"):
        _write(tmp_path, compiled, trials, index_id)
    assert {p.name: p.read_bytes() for p in (tmp_path / "proposal").iterdir()} == before


def test_scratch_inside_git_is_rejected_before_directory_creation(two_axis, tmp_path):
    compiled, trials, index_id = two_axis
    (tmp_path / ".git").write_text("synthetic Git boundary", encoding="utf-8")
    with pytest.raises(adapter.F36NotesCoreAdapterError, match="outside Git"):
        _write(tmp_path, compiled, trials, index_id)
    assert not (tmp_path / "proposal").exists()


@pytest.mark.parametrize("limit", [False, 0, 1, stream.MAX_TRIAL_BYTES + 1])
def test_trial_bound_never_changes_to_a_larger_or_boolean_budget(two_axis, tmp_path, limit):
    compiled, trials, index_id = two_axis
    with pytest.raises(adapter.F36NotesCoreAdapterError):
        _write(tmp_path, compiled, trials, index_id, max_trial_bytes=limit)


def _real_source_case(example, tmp_path, monkeypatch, *, compact, interim_q4):
    """Actual tiny unit SQLite source and PRIMARY context; no financial/auth mocks."""
    corpus, _page = _source_fixture(tmp_path, monkeypatch, interim_q4=interim_q4, unrelated=compact)
    production, _trial, _index = example
    topology = deepcopy(production["topology"])
    topology["source"] = {"corpus_name": corpus.name, "artifact_root": str(corpus.root),
        "index_ref": _ref(corpus.index_path), "database_ref": _ref(corpus.db_path),
        "corpus_identity": corpus.identity(), "document_axis": adapter._document_axis(corpus)}
    evaluation = deepcopy(production["evaluation"])
    primary = tmp_path / "primary.sqlite3"
    result = {"document": corpus.documents[0].identity(), "corpus": corpus.identity(), "notes_start_page": 1,
        "cells": [], "instances": [{"presentation_role": "PRIMARY", "scope": "SEPARATE", "statement": "KQKD",
            "period_context": {"evidence": [
                "Báo cáo kết quả hoạt động giữa niên độ cho giai đoạn từ ngày 01/1/2025 đến ngày 31/12/2025" if interim_q4
                else "Cho năm tài chính kết thúc ngày 31 tháng 12 năm 2025"]}, "tables": [],
            "lanes": [] if interim_q4 else [{"period": {"key": f"DURATION:YEAR:{year}"}} for year in (2025, 2024)]}]}
    with sqlite3.connect(primary) as connection:
        connection.execute("CREATE TABLE document_result(document_ordinal INTEGER PRIMARY KEY, result_json TEXT NOT NULL)")
        connection.execute("INSERT INTO document_result VALUES (?,?)", (1, json.dumps(result, ensure_ascii=False)))
    evaluation["primary_store_ref"] = _ref(primary)
    if compact:
        evaluation["format_version"] = adapter.COMPACT_EVALUATION_FORMAT
    for name in evaluation["frontier_receipt_refs"]:
        path = tmp_path / f"{name}.json"
        path.write_bytes(canonical_json_bytes_v1({"synthetic_fixture": name}))
        evaluation["frontier_receipt_refs"][name] = _ref(path)
    compiled = adapter.compile_f36_notes_core_specs_v1(topology, evaluation, production["schema"])
    contexts = load_primary_context_v1(primary, evaluation["primary_store_ref"]["sha256"])
    return corpus, contexts, compiled


@pytest.mark.parametrize("compact", [False, True])
@pytest.mark.parametrize("interim_q4", [False, True])
def test_actual_tiny_source_old_monolith_equals_document_iterator_without_rule_mocks(
    example, tmp_path, monkeypatch, compact, interim_q4,
):
    corpus, contexts, compiled = _real_source_case(example, tmp_path, monkeypatch, compact=compact, interim_q4=interim_q4)
    config = load_notes_config_v1(ROOT)
    source = NotesSource(corpus)
    policies = source.annual_policies_v1({1: contexts[1].scope})
    old_contexts = {1: replace(contexts[1], annual_policy=policies[1])}
    old = adapter.rebuild_f36_notes_trials_v1(source=source, contexts=old_contexts, config=config, compiled_specs=compiled)
    snapshot = canonical_json_bytes_v1(compiled)
    bounded_source = NotesSource(corpus)
    fresh = list(adapter.iter_rebuild_f36_notes_trials_v1(
        source=bounded_source, contexts=contexts, config=config, compiled_specs=compiled,
    ))
    assert canonical_json_bytes_v1(fresh) == canonical_json_bytes_v1(old)
    assert canonical_json_bytes_v1(compiled) == snapshot
    assert old[0]["status"] == "READY" and len(old[0]["mappings"]) == 4
    sweep = _old_sweep(compiled, old, corpus.corpus_manifest_index_id)
    report = _write(tmp_path, compiled, fresh, corpus.corpus_manifest_index_id)
    assert Path(report["sweep_ref"]["path"]).read_bytes() == canonical_json_bytes_v1(sweep) + b"\n"
    assert bounded_source.metrics.sql_queries > 0 and bounded_source.metrics.pages_loaded > 0
    assert not bounded_source._bridges  # Counters aggregate; document bridge caches do not escape.


def test_document_iterator_rejects_late_compiled_drift_before_completion(example, tmp_path, monkeypatch):
    corpus, contexts, compiled = _real_source_case(example, tmp_path, monkeypatch, compact=True, interim_q4=False)
    iterator = adapter.iter_rebuild_f36_notes_trials_v1(
        source=NotesSource(corpus), contexts=contexts, config=load_notes_config_v1(ROOT), compiled_specs=compiled,
    )
    assert next(iterator)["document_ordinal"] == 1
    compiled["topology"]["documents_requested"] = []
    with pytest.raises(adapter.F36NotesCoreAdapterError, match="Stream authority changed"):
        next(iterator)
