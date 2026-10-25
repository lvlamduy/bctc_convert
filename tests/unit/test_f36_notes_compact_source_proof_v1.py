"""UNRUN compact-A source-partition controls; synthetic source facts, no acceptance."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_f36_notes_core_adapter_v1 import VID, reseal_trial, sweep_of
from test_f36_notes_core_adapter_v1 import example as example
from test_notes_root_closure import lpb

from bctc_ai.evaluation import gemini_json_f36_notes_core_adapter_v1 as adapter
from bctc_ai.notes.config_v1 import load_notes_config_v1
from bctc_ai.notes.f36_strict_ledger_v1 import (
    classify_observation_v1,
    classify_rows_v1,
    classify_table_v1,
)
from bctc_ai.notes.root_closure_v1 import root_closure_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)


def _page():
    paths, rows = [], []
    for label, kind, values, parent, _line in lpb():
        path = ([] if parent is None else paths[parent]) + [label]
        paths.append(path)
        rows.append({"label_exact": label, "row_kind": kind, "hierarchy_path_exact": path,
                     "values_exact": [None, *values]})
    table = {"title_exact": None, "unit_exact": "Triệu đồng", "continuation": "NONE",
             "columns": [{"header_path_exact": [None], "value_kind": "TEXT"},
                         {"header_path_exact": ["Năm 2025"], "value_kind": "MONEY"},
                         {"header_path_exact": ["Năm 2024"], "value_kind": "MONEY"}], "rows": rows}
    unrelated = {"title_exact": "Other notes", "columns": [{"value_kind": "MONEY"}],
                 "rows": [{"row_kind": "ITEM", "label_exact": "Unassessed source",
                           "hierarchy_path_exact": ["Unassessed source"], "values_exact": ["9"]}]}
    return {"sections": [
        {"title_exact": "Chi phí hoạt động", "content_kind": "FINANCIAL_NOTE", "statement_type": "NOT_APPLICABLE",
         "tables": [table]},
        {"title_exact": "Other notes", "tables": [unrelated]},
        {"title_exact": "Chi phí hoạt động dịch vụ", "tables": [deepcopy(unrelated)]}]}


def _compact_specs(compiled):
    evaluation = deepcopy(compiled["evaluation"])
    evaluation["format_version"] = adapter.COMPACT_EVALUATION_FORMAT
    return adapter.compile_f36_notes_core_specs_v1(compiled["topology"], evaluation, compiled["schema"])


def _partition(compiled, page, dispositions, cells):
    doc = compiled["topology"]["source"]["document_axis"][0]
    required = adapter._required_source_keys(dispositions, cells)
    subjects = adapter._family(compiled["evaluation"]).raw["subjects"]["OPERATING_EXPENSE_NOTE"]["any"]
    page_proof, inventories = adapter._compact_page(page, doc=doc, selected=doc["pages"][0], blob_sha="a" * 64,
        required=required, subjects=subjects)
    return adapter._source_partition(doc, compiled, [page_proof]), inventories


def _reseal_partition(trial, compiled):
    ledger = trial["notes_ledger"]
    doc = compiled["topology"]["source"]["document_axis"][0]
    ledger["source_partition"] = adapter._source_partition(doc, compiled, ledger["source_partition"]["pages"])
    reseal_trial(trial)


def _check_partition(proof, inventories, compiled, dispositions, cells):
    doc = compiled["topology"]["source"]["document_axis"][0]
    subjects = adapter._family(compiled["evaluation"]).raw["subjects"]["OPERATING_EXPENSE_NOTE"]["any"]
    adapter._validate_compact_partition({"source_partition": proof, "dispositions": dispositions, "cells": cells},
                                      doc, compiled, inventories, subjects)


@pytest.fixture
def compact_example(example):
    old_compiled, trial, index_id = deepcopy(example)
    compiled, page = _compact_specs(old_compiled), _page()
    ledger = trial["notes_ledger"]
    proof, inventories = _partition(compiled, page, ledger["dispositions"], ledger["cells"])
    family = adapter._family(compiled["evaluation"])
    disposition = ledger["dispositions"][0]
    key = (VID, "s1", "t1")
    closure = root_closure_v1(inventories[key], disposition, family)
    assert closure == ledger["root_closures"][0]["closure"]
    ledger["production_policy_receipts"][0]["receipt"] = adapter._production_table_policy_v1(
        inventories[key], disposition, closure, compiled)
    rows = {(k[0], int(k[1][1:]), int(k[2][1:]), row["row_ordinal"]): row
            for k, inv in inventories.items() for row in inv["rows"]}
    ledger["classifications"] = [classify_observation_v1(c, 1206, closure, rows) for c in ledger["cells"]]
    subjects = family.raw["subjects"]["OPERATING_EXPENSE_NOTE"]["any"]
    ledger["source_ledger"] = [{"inventory": inv,
        "table_classification": classify_table_v1(inv["table"], inv["section"], {(VID, 1, 1): closure}, subjects),
        "rows": classify_rows_v1(inv["rows"], inv["columns"],
            ledger["cells"] if k == key else [], closure if k == key else None)} for k, inv in inventories.items()]
    ledger["source_partition"] = proof
    reseal_trial(trial)
    return compiled, trial, index_id, page


def test_versioned_compact_keeps_financial_cells_and_whole_held_row_axis(example, compact_example):
    old_compiled, old_trial, index_id = deepcopy(example)
    compiled, trial, _, page = compact_example
    old_bytes = canonical_json_bytes_v1(sweep_of(old_compiled, old_trial, index_id))
    compact = sweep_of(compiled, trial, index_id)
    checked = adapter.validate_f36_notes_core_sweep_v1(compact)
    assert checked["format_version"] == adapter.COMPACT_FORMAT
    assert checked["indexed_query_evidence"]["format_version"] == adapter.COMPACT_QUERY_FORMAT
    for field in ("mappings", "status", "reasons"):
        assert canonical_json_bytes_v1(trial[field]) == canonical_json_bytes_v1(old_trial[field])
    for field in ("cells", "classifications", "retained", "dispositions", "root_closures"):
        assert canonical_json_bytes_v1(trial["notes_ledger"][field]) == canonical_json_bytes_v1(old_trial["notes_ledger"][field])
    source = trial["notes_ledger"]["source_ledger"]
    assert len(source) == 2  # required s1 and unassessed caption-potential s3; s2 is compact only
    assert len(source[0]["inventory"]["rows"]) == 16
    assert source[0]["inventory"]["rows"][11]["fields"]["label_exact"]["value"] == page["sections"][0]["tables"][0]["rows"][11]["label_exact"]
    summary = trial["notes_ledger"]["source_partition"]
    assert summary["counts"]["table"] == 3 and summary["counts"]["full_tables"] == 2
    assert summary["pages"][0]["tables"][1]["disposition"] == "UNASSESSED_NOT_ABSENT"
    assert "STRUCTURAL_NOT_AUTHENTICATED" in summary["validation_boundary"]
    assert canonical_json_bytes_v1(sweep_of(old_compiled, old_trial, index_id)) == old_bytes
    checked["trials"][0]["notes_ledger"]["source_partition"]["pages"].clear()
    assert len(trial["notes_ledger"]["source_partition"]["pages"]) == 1


@pytest.mark.parametrize("status", ["REJECTED", "SOURCE_ONLY", "UNRESOLVED"])
def test_zero_cell_rejected_and_held_owners_are_full(example, status):
    compiled, trial, _ = example
    compiled = _compact_specs(compiled)
    disposition = deepcopy(trial["notes_ledger"]["dispositions"][0])
    disposition["status"] = status
    disposition["locator"]["section_id"] = "s2"
    disposition["source_bridges"] = [None]  # absent bridge stays recorded, never a fabricated coordinate
    proof, kept = _partition(compiled, _page(), [disposition], [])
    _check_partition(proof, kept, compiled, [disposition], [])
    assert (VID, "s2", "t1") in kept


@pytest.mark.parametrize("route", ["fragments", "source_bridges", "original_cell"])
def test_original_dependency_keeps_noncarrier_tail_without_a_mapped_cell(example, route):
    compiled, trial, _ = example
    compiled = _compact_specs(compiled)
    disposition, cells = deepcopy(trial["notes_ledger"]["dispositions"][0]), []
    if route == "fragments":
        disposition["fragments"] = [{**disposition["locator"], "section_id": "s2"}]
    elif route == "source_bridges":
        disposition["source_bridges"].append({"page_json_version_id": VID, "section_ordinal": 2, "table_ordinal": 1})
    else:
        cells = [deepcopy(trial["notes_ledger"]["cells"][0])]
        cells[0]["original_cell"]["section_ordinal"] = 2
    proof, kept = _partition(compiled, _page(), [disposition], cells)
    _check_partition(proof, kept, compiled, [disposition], cells)
    assert (VID, "s2", "t1") in kept
    kept.pop((VID, "s2", "t1"))
    with pytest.raises(adapter.F36NotesCoreAdapterError, match="required"):
        _check_partition(proof, kept, compiled, [disposition], cells)


@pytest.mark.parametrize("shape", ["sections", "section_tables", "bad_table", "width"])
def test_unsupported_page_section_and_table_envelopes_survive(example, shape):
    compiled, _, _ = example
    compiled, page = _compact_specs(compiled), _page()
    if shape == "sections":
        page["sections"] = None
    elif shape == "section_tables":
        page["sections"].append({"tables": None})
    elif shape == "bad_table":
        page["sections"][1]["tables"].append(None)
    else:
        page["sections"][1]["tables"][0]["rows"][0]["values_exact"] = []
    proof, kept = _partition(compiled, page, [], [])
    _check_partition(proof, kept, compiled, [], [])
    original_unsupported = [n for n in adapter._nodes(page) if n["record_type"] == "unsupported_shape"]
    retained_unsupported = [n for inv in kept.values() for n in inv["unsupported"]]
    outside = proof["pages"][0]["outside_table_nodes"]
    assert all(n in retained_unsupported or n in outside for n in original_unsupported)
    assert proof["counts"]["unsupported_shape"] == len(original_unsupported)


@pytest.mark.parametrize("raw", [None, "-", "", "   "])
def test_full_required_unknown_operands_never_disappear(example, raw):
    compiled, trial, _ = example
    compiled, page = _compact_specs(compiled), _page()
    page["sections"][0]["tables"][0]["rows"][11]["values_exact"][1] = raw
    proof, kept = _partition(compiled, page, trial["notes_ledger"]["dispositions"], [])
    _check_partition(proof, kept, compiled, trial["notes_ledger"]["dispositions"], [])
    row = kept[(VID, "s1", "t1")]["rows"][11]
    assert row["value_axis"]["items_one_lf_sha256"][1] == canonical_json_sha256_v1(raw)
    assert len(kept[(VID, "s1", "t1")]["rows"]) == 16


@pytest.mark.parametrize("attack", ["drop_page", "duplicate_page", "drop_table", "duplicate_table", "wrong_vid",
    "bool_physical", "blob", "count", "outside", "node_hash", "compact_required", "missing_full", "extra_full"])
def test_resealed_partition_tamper_cannot_hide_required_or_universe_axes(compact_example, attack):
    compiled, trial, _, _ = deepcopy(compact_example)
    ledger = trial["notes_ledger"]
    page = ledger["source_partition"]["pages"][0]
    if attack == "drop_page":
        ledger["source_partition"]["pages"].clear()
    elif attack == "duplicate_page":
        ledger["source_partition"]["pages"].append(deepcopy(page))
    elif attack == "drop_table":
        page["tables"].pop(1)
    elif attack == "duplicate_table":
        page["tables"].append(deepcopy(page["tables"][0]))
    elif attack == "wrong_vid":
        page["axis"]["page_json_version_id"] = "gfpstorev1:json:" + "8" * 64
    elif attack == "bool_physical":
        page["axis"]["physical_page"] = True
    elif attack == "blob":
        page["stored_blob_two_lf_sha256"] = "b" * 64
    elif attack == "count":
        page["tables"][1]["counts"]["row"] += 1
    elif attack == "outside":
        page["outside_table_nodes"].clear()
    elif attack == "node_hash":
        page["node_axis"][2][2] = "c" * 64
        page["node_axis_sha256"] = canonical_json_sha256_v1(page["node_axis"])
    elif attack == "compact_required":
        page["tables"][0]["retention_reasons"] = []
        page["tables"][0]["disposition"] = "UNASSESSED_NOT_ABSENT"
        ledger["source_ledger"].pop(0)
    elif attack == "missing_full":
        ledger["source_ledger"].pop()
    else:
        inv = adapter._inventory(_page(), VID, "a" * 64)[(VID, "s2", "t1")]
        ledger["source_ledger"].append({"inventory": inv})
    _reseal_partition(trial, compiled)
    inventories = {adapter._source_key(s["inventory"]["table"]): s["inventory"] for s in ledger["source_ledger"]}
    with pytest.raises(adapter.F36NotesCoreAdapterError):
        _check_partition(ledger["source_partition"], inventories, compiled, ledger["dispositions"], ledger["cells"])


@pytest.mark.parametrize("kind", ["foreign_vid", "bool_ordinal", "missing_ordinal"])
def test_missing_or_malformed_named_original_axes_never_guessed(example, kind):
    compiled, trial, _ = example
    disposition = deepcopy(trial["notes_ledger"]["dispositions"][0])
    bridge = disposition["source_bridges"][0]
    if kind == "foreign_vid":
        bridge["page_json_version_id"] = "gfpstorev1:json:" + "8" * 64
    elif kind == "bool_ordinal":
        bridge["section_ordinal"] = True
    else:
        bridge.pop("table_ordinal")
    with pytest.raises(adapter.F36NotesCoreAdapterError):
        proof, kept = _partition(_compact_specs(compiled), _page(), [disposition], [])
        _check_partition(proof, kept, _compact_specs(compiled), [disposition], [])


def test_outside_requested_document_stays_unassessed_without_a_fresh_page_claim(example):
    compiled, _, _ = example
    topology = deepcopy(compiled["topology"])
    outside = deepcopy(topology["source"]["document_axis"][0])
    outside.update(document_ordinal=2, source_logical_name="outside.pdf", source_sha256="2" * 64)
    outside["document_identity"].update(document_ordinal=2, relative_path="outside.pdf", source_sha256="2" * 64)
    outside["pages"] = [{"physical_page": 1, "page_json_version_id": "gfpstorev1:json:" + "8" * 64}]
    topology["source"]["document_axis"].append(outside)
    evaluation = deepcopy(compiled["evaluation"])
    evaluation["format_version"] = adapter.COMPACT_EVALUATION_FORMAT
    compact = adapter.compile_f36_notes_core_specs_v1(topology, evaluation, compiled["schema"])
    proof = adapter._source_partition(outside, compact, [])
    ledger = {"source_partition": proof, "dispositions": [], "cells": []}
    subjects = adapter._family(compact["evaluation"]).raw["subjects"]["OPERATING_EXPENSE_NOTE"]["any"]
    adapter._validate_compact_partition(ledger, outside, compact, {}, subjects)
    assert proof["scope"] == "OUTSIDE_REQUESTED_SUBSET_NOT_EVALUATED" and proof["counts"] == {}
    fresh, kept = adapter._compact_page(_page(), doc=outside, selected=outside["pages"][0], blob_sha="a" * 64,
                                       required=set(), subjects=subjects)
    ledger["source_partition"] = adapter._source_partition(outside, compact, [fresh])
    with pytest.raises(adapter.F36NotesCoreAdapterError, match="selected-page"):
        adapter._validate_compact_partition(ledger, outside, compact, kept, subjects)


def test_unaddressable_rejected_bridge_is_named_unsupported_not_guessed(example):
    _, trial, _ = deepcopy(example)
    disposition = trial["notes_ledger"]["dispositions"][0]
    disposition["status"] = "REJECTED"
    bridge = {"status": "MISMATCH:NORMALIZED_IDS", "page_json_version_id": VID}
    disposition["source_bridges"] = [bridge]
    before = canonical_json_bytes_v1(disposition)
    with pytest.raises(adapter.F36NotesCoreAdapterError, match="COMPACT_PROOF_UNSUPPORTED_BRIDGE_AXIS") as caught:
        adapter._required_source_keys([disposition], [])
    assert "MISMATCH:NORMALIZED_IDS" in str(caught.value) and "REJECTED" in str(caught.value)
    assert VID in str(caught.value) and canonical_json_bytes_v1(disposition) == before


def test_fresh_rebuild_rejects_old_query_after_discarded_row_drift(example, monkeypatch):
    """Protocol-only fake IO: financial evaluator is fixed; the actual partition scan must still re-read every page."""
    compiled, trial, _ = example
    compiled = _compact_specs(compiled)
    doc = compiled["topology"]["source"]["document_axis"][0]
    page, calls = _page(), []
    selected = SimpleNamespace(**doc["pages"][0])
    document = SimpleNamespace(ordinal=1, source_sha256=doc["source_sha256"], relative_path=doc["source_logical_name"], pages=[selected])
    document.identity = lambda: doc["document_identity"]
    corpus = SimpleNamespace(documents=[document], identity=lambda: compiled["topology"]["source"]["corpus_identity"])

    def load(versions):
        calls.append(list(versions))
        return {VID: {"source_sha256": doc["source_sha256"], "source_logical_name": doc["source_logical_name"],
                      "physical_page": 64, "source_json_replay_receipt": {"canonical_json_sha256": "a" * 64}, "page_json": deepcopy(page)}}

    source = SimpleNamespace(corpus=corpus, _load_originals=load)
    config = load_notes_config_v1(Path(__file__).resolve().parents[2])
    run = SimpleNamespace(cells=trial["notes_ledger"]["cells"], evaluations=[])
    monkeypatch.setattr(adapter, "run_family_v1", lambda *_a, **_kw: run)
    monkeypatch.setattr(adapter, "dispositions_v1", lambda _run: trial["notes_ledger"]["dispositions"])
    context = SimpleNamespace(scope="SEPARATE", annual_policy=None,
                              income_context_texts=trial["notes_ledger"]["primary_income_context_texts"])
    first = adapter.rebuild_f36_notes_trials_v1(source=source, contexts={1: context}, config=config, compiled_specs=compiled)
    query = adapter.build_f36_notes_query_evidence_v1(trials=first, compiled_specs=compiled)
    page["sections"][1]["tables"][0]["rows"][0]["values_exact"] = ["10"]
    fresh = adapter.rebuild_f36_notes_trials_v1(source=source, contexts={1: context}, config=config, compiled_specs=compiled)
    assert calls == [[VID], [VID]]
    assert first[0]["mappings"] == fresh[0]["mappings"]
    with pytest.raises(adapter.F36NotesCoreAdapterError, match="frontier/query"):
        adapter.validate_f36_notes_trials_v1(trials=fresh, indexed_query_evidence=query, compiled_specs=compiled)

