"""Real tiny SQLite source replay and EXPERIMENTAL persistence; no production grant."""
from __future__ import annotations

import json
import shutil
import sqlite3
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from test_f36_notes_core_adapter_v1 import example as example
from test_gemini_income_tax_raw_money_census_v1 import _fixture

from bctc_ai.evaluation import gemini_json_f36_notes_core_adapter_v1 as adapter
from bctc_ai.notes.config_v1 import load_notes_config_v1
from bctc_ai.notes.kernel_v1 import NotesSource, load_primary_context_v1
from bctc_ai.primary_statements.source_v1 import load_corpus_selection_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.storage.gemini_accounting_family_store_v1 import (
    ingest_gemini_accounting_family_sweep_v1,
    load_gemini_accounting_family_sweep_v1,
    record_gemini_accounting_family_export_v1,
)
from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import (
    build_current_corpus_manifest_index_v1,
)
from bctc_ai.storage.gemini_current_document_manifest_selection_v1 import (
    build_current_document_manifest_selection_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import build_financial_document_manifest_v1

ROOT = Path(__file__).resolve().parents[2]


def _ref(path):
    raw = path.read_bytes()
    return {"path": str(path.resolve()), "sha256": sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _put(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    # The current document-selection loader requires its stored two-LF domain.
    path.write_bytes(canonical_json_bytes_v1(value) + b"\n")
    return {**_ref(path), "path": relative}


def _source_fixture(tmp_path, monkeypatch):
    labels = ["Chi nộp thuế và các khoản phí, lệ phí", "Chi phí cho nhân viên", "Chi về tài sản",
              "Tổng chi phí hoạt động"]
    values = [("10", "9"), ("20", "18"), ("30", "27"), ("60", "54")]
    page = {"status": "FINANCIAL_NOTE_CONTENT",
            "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
            "sections": [{"content_kind": "FINANCIAL_NOTE", "statement_type": "NOT_APPLICABLE",
                "title_exact": "Chi phí hoạt động", "narratives_exact": [], "tables": [{
                    "title_exact": "Chi phí hoạt động", "unit_exact": "Triệu đồng", "continuation": "NONE",
                    "columns": [{"header_path_exact": [f"Năm {year}"], "value_kind": "MONEY"}
                                for year in (2025, 2024)],
                    "rows": [{"label_exact": label, "row_kind": "TOTAL" if i == 3 else "ITEM",
                              "hierarchy_path_exact": [label], "values_exact": list(amounts)}
                             for i, (label, amounts) in enumerate(zip(labels, values, strict=True))]}]}]}
    # The shared transport fixture uses the real page-store ingest; legacy=False
    # does not patch a validator or any financial function.
    options, old_index, _ = _fixture(tmp_path, monkeypatch, pages=[page])
    # Reuse only the real ingested DB, not the census fixture's deliberately
    # minimal manifests. Build a fresh full producer-compatible authority tree.
    root = tmp_path / "complete-authority"
    root.mkdir()
    database = root / "source.sqlite3"
    shutil.copyfile(options["database"], database)
    document = deepcopy(old_index["documents"][0])
    manifest = build_financial_document_manifest_v1(database, source_sha256=document["source_sha256"],
        source_logical_name=document["relative_path"], expected_physical_pages=[1], prompt_sha256="d" * 64,
        response_schema_sha256="e" * 64, requested_model="gemini-3.7-flash", requested_service_tier="flex")
    local_manifest = "current-document-manifests/complete.json"
    manifest_ref = _put(root, "documents/1/" + local_manifest, manifest)
    selection = build_current_document_manifest_selection_v1(
        document_plan_id=document["document_plan_id"], source_sha256=document["source_sha256"],
        document_manifest_id=manifest["document_manifest_id"],
        document_manifest_ref={**manifest_ref, "path": local_manifest},
        page_image_frontier_sha256=canonical_json_sha256_v1([
            {"physical_page": p["physical_page"], "image_sha256": p["image"]["sha256"]} for p in manifest["pages"]]),
        page_prompt_frontier_sha256=canonical_json_sha256_v1([{"physical_page": 1, "prompt_variant": "compact"}]),
        prior_selection_ids=[])
    selection_ref = _put(root, "documents/1/current-document-manifest-selections/"
                         + selection["selection_id"].split(":", 2)[2] + ".json", selection)
    document.update(document_manifest_id=manifest["document_manifest_id"], document_manifest_ref=manifest_ref,
                    selection_id=selection["selection_id"], selection_ref=selection_ref,
                    page_json_frontier_sha256=canonical_json_sha256_v1(manifest["pages"]))
    index = build_current_corpus_manifest_index_v1(**{key: old_index[key] for key in (
        "corpus_plan_id", "corpus_run_id", "corpus_plan_ref", "database_ref", "ledger_ref", "store_usage_summary")},
        documents=[document])
    index_ref = _put(root, "indexes/complete.json", index)
    corpus = load_corpus_selection_v1(name="synthetic-f36", root=root, index_relative_path=index_ref["path"],
        expected_index_sha256=index_ref["sha256"], expected_db_sha256=index["database_ref"]["sha256"])
    return corpus, page


def test_real_f36_source_replay_precedes_experimental_store_and_exact_readback(example, tmp_path, monkeypatch):
    """No saved trial is returned by the checked callback: it reconstructs source rules."""
    corpus, original = _source_fixture(tmp_path, monkeypatch)
    production, _, _ = example
    topology = deepcopy(production["topology"])
    topology["source"] = {"corpus_name": corpus.name, "artifact_root": str(corpus.root),
        "index_ref": _ref(corpus.index_path), "database_ref": _ref(corpus.db_path),
        "corpus_identity": corpus.identity(), "document_axis": adapter._document_axis(corpus)}
    evaluation = deepcopy(production["evaluation"])
    # This declared PRIMARY fixture supplies source-bound scope and printed annual
    # duration, not amounts, financial decisions, ROOT closures or notes trials.
    primary = tmp_path / "primary.sqlite3"
    result = {"document": corpus.documents[0].identity(), "corpus": corpus.identity(), "notes_start_page": 1,
              "cells": [], "instances": [{"presentation_role": "PRIMARY", "scope": "SEPARATE",
                "statement": "KQKD", "period_context": {"evidence": [
                    "Cho năm tài chính kết thúc ngày 31 tháng 12 năm 2025"]}, "tables": [],
                "lanes": [{"period": {"key": f"DURATION:YEAR:{year}"}} for year in (2025, 2024)]}]}
    with sqlite3.connect(primary) as connection:
        connection.execute("CREATE TABLE document_result(document_ordinal INTEGER PRIMARY KEY, result_json TEXT NOT NULL)")
        connection.execute("INSERT INTO document_result VALUES (?,?)", (1, json.dumps(result, ensure_ascii=False)))
    evaluation["primary_store_ref"] = _ref(primary)
    evaluation["frontier_receipt_refs"] = {}
    for name in production["evaluation"]["frontier_receipt_refs"]:
        path = tmp_path / f"{name}.json"
        path.write_bytes(canonical_json_bytes_v1({"fixture": name, "financial_acceptance": False}))
        evaluation["frontier_receipt_refs"][name] = _ref(path)
    compiled = adapter.compile_f36_notes_core_specs_v1(topology, evaluation, production["schema"])
    config = load_notes_config_v1(ROOT)
    source = NotesSource(corpus)
    contexts = load_primary_context_v1(primary, evaluation["primary_store_ref"]["sha256"])
    policies = source.annual_policies_v1({1: contexts[1].scope})
    contexts = {1: replace(contexts[1], annual_policy=policies.get(1))}
    before = {p: p.read_bytes() for p in (corpus.db_path, corpus.index_path, primary)}
    trials = adapter.rebuild_f36_notes_trials_v1(source=source, contexts=contexts, config=config, compiled_specs=compiled)
    assert trials[0]["status"] == "READY"
    assert len(trials[0]["mappings"]) == 4
    assert {m["role"] for m in trials[0]["mappings"]} == {
        "TAX_FEES", "EMPLOYEE_EXPENSE", "ASSET_EXPENSE", "FAMILY_ROOT_TOTAL"}
    assert {m["role"]: [v["coefficient"] for v in m["values"]] for m in trials[0]["mappings"]} == {
        "TAX_FEES": [10, 9], "EMPLOYEE_EXPENSE": [20, 18], "ASSET_EXPENSE": [30, 27],
        "FAMILY_ROOT_TOTAL": [60, 54]}
    query = adapter.build_f36_notes_query_evidence_v1(trials=trials, compiled_specs=compiled)
    sweep = adapter.build_f36_notes_core_sweep_v1(corpus_manifest_index_id=corpus.corpus_manifest_index_id,
        topology_spec=topology, evaluation_spec=evaluation, schema_binding_spec=production["schema"],
        trials=trials, indexed_query_evidence=query)
    snapshot = tmp_path / "source-snapshot.sqlite3"
    shutil.copyfile(corpus.db_path, snapshot)
    adapter_ref = _ref(Path(adapter.__file__))
    destination = tmp_path / "canonical.sqlite3"
    stored = ingest_gemini_accounting_family_sweep_v1(destination, sweep=sweep,
        corpus_index_ref=_ref(corpus.index_path), implementation_refs=[adapter_ref], run_kind="EXPERIMENTAL",
        source_page_database=snapshot, selected_page_json_version_ids=[p.page_json_version_id for p in corpus.documents[0].pages],
        corpus_artifact_root=corpus.root, source_replay_adapter=adapter.replay_f36_notes_core_trials_from_source_v1,
        source_replay_adapter_ref=adapter_ref)
    loaded = load_gemini_accounting_family_sweep_v1(destination, stored["family_run_id"])
    assert canonical_json_bytes_v1(loaded) == canonical_json_bytes_v1(sweep)
    with sqlite3.connect(destination) as connection:
        assert connection.execute("PRAGMA quick_check").fetchall() == [("ok",)]
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("SELECT COUNT(*) FROM family_mapping").fetchone()[0] == 4
        assert connection.execute("SELECT COUNT(*) FROM family_trial").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM family_current_selection").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM family_selection_event").fetchone()[0] == 0
    exported = tmp_path / "canonical.json"
    exported.write_bytes(canonical_json_bytes_v1(sweep))
    receipt = record_gemini_accounting_family_export_v1(destination, family_run_id=stored["family_run_id"], output_path=exported)
    assert receipt["sha256"] == sha256(exported.read_bytes()).hexdigest()
    assert receipt["size_bytes"] == len(exported.read_bytes())
    assert all(path.read_bytes() == raw for path, raw in before.items())
    assert snapshot.read_bytes() == before[corpus.db_path]
    assert source._load_originals([corpus.documents[0].pages[0].page_json_version_id])[
        corpus.documents[0].pages[0].page_json_version_id]["page_json"] == original
