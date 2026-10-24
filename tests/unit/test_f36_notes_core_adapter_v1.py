"""UNRUN synthetic codec/frontier contracts; no financial or IO acceptance claim."""
from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest
from test_notes_f36_strict_ledger import cell
from test_notes_root_closure import PAGE_BLOB, build, lpb

from bctc_ai.evaluation.gemini_json_f36_notes_core_adapter_v1 import (
    EVALUATION_FORMAT,
    FAMILY,
    FORMAT,
    SCHEMA_FORMAT,
    TOPOLOGY_FORMAT,
    F36NotesCoreAdapterError,
    _fragments,
    _inventory,
    build_f36_notes_core_sweep_v1,
    build_f36_notes_query_evidence_v1,
    compile_f36_notes_core_specs_v1,
    replay_f36_notes_core_trials_from_source_v1,
    validate_f36_notes_core_sweep_v1,
)
from bctc_ai.notes.config_v1 import load_notes_config_v1
from bctc_ai.notes.f36_strict_ledger_v1 import (
    classify_observation_v1,
    classify_rows_v1,
    classify_table_v1,
)
from bctc_ai.notes.root_closure_v1 import root_closure_v1
from bctc_ai.primary_statements.periods_v1 import statement_period_context_v1
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1, canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
VID = "gfpstorev1:json:" + "9" * 64
CONTEXT = ["Cho năm tài chính kết thúc ngày 31 tháng 12 năm 2025"]


def ref(name):
    # Structural declaration only. These paths do not authenticate test fixtures.
    return {"path": str(ROOT / name), "sha256": "a" * 64, "size_bytes": 1}


@pytest.fixture
def example():
    config = load_notes_config_v1(ROOT)
    policy_path = ROOT / "config/families/tm-operating-expense-evaluation-v1.json"
    policy_raw = policy_path.read_bytes()
    doc = {"document_ordinal": 1, "source_logical_name": "synthetic.pdf", "source_sha256": "1" * 64,
           "document_identity": {"document_ordinal": 1, "relative_path": "synthetic.pdf", "source_sha256": "1" * 64},
           "pages": [{"physical_page": 64, "page_json_version_id": VID}]}
    index_id = "gjfccmiv1:index:" + "2" * 64
    source = {"corpus_name": "synthetic", "artifact_root": str(ROOT), "index_ref": ref("index.json"),
              "database_ref": ref("source.sqlite3"), "document_axis": [doc],
              "corpus_identity": {"corpus_name": "synthetic", "corpus_manifest_index_id": index_id,
                                  "index_sha256": "a" * 64, "database_sha256": "a" * 64}}
    topology = {"format_version": TOPOLOGY_FORMAT, "family_id": FAMILY, "source": source, "documents_requested": [1]}
    evaluation = {"format_version": EVALUATION_FORMAT, "family_id": FAMILY, "notes_config_pins": config.pins,
                  "notes_family": {"raw": config.families[FAMILY].raw, "sha256": config.families[FAMILY].sha256},
                  "production_policy": json.loads(policy_raw),
                  "production_policy_ref": {"path": str(policy_path), "sha256": sha256(policy_raw).hexdigest(), "size_bytes": len(policy_raw)},
                  "primary_store_ref": ref("primary.sqlite3"),
                  "frontier_receipt_refs": {name: ref(name) for name in ("producer_manifest", "ledger_summary",
                        "ledger_observations", "closure_results", "neutral_inventory", "root_build")}}
    schema = {"format_version": SCHEMA_FORMAT, "family_id": FAMILY,
              "crosswalk": [{"concept": k[0], "axis": k[1], "members": list(k[2]), "report_norm_id": v}
                            for k, v in config.crosswalk.items()]}
    compiled = compile_f36_notes_core_specs_v1(topology, evaluation, schema)
    inv, disposition = build(lpb())
    inv["table"].update(page_json_version_id=VID, section_id="s1", table_id="t1")
    inv["page"]["axis"]["page_json_version_id"] = VID
    inv["section"] = {"fields": {"title_exact": {"present": True, "value": "Chi phí hoạt động"}}}
    for row, spec in zip(inv["rows"], lpb(), strict=True):
        row["page_json_version_id"] = VID
        row["value_axis"]["items_one_lf_sha256"] = [canonical_json_sha256_v1(v) for v in [None, *spec[2]]]
    disposition["source_bridges"][0]["page_json_version_id"] = VID
    disposition["locator"] = {"document_ordinal": 1, "physical_page": 64, "page_json_version_id": VID,
                              "section_id": "s1", "table_id": "t1"}
    closure = root_closure_v1(inv, disposition, config.families[FAMILY])
    cells = []
    for column, year in ((2, 2025), (3, 2024)):
        c = cell(raw="1", value="1", column=f"c{column}", ordinal=column, document_ordinal=1,
                 period_key=f"DURATION:YEAR:{year}", period_basis="PRINTED_DURATION", header_text=f"Năm {year}")
        c["locator"]["physical_page"] = 64
        cells.append(c)
    rows = {(VID, 1, 1, r["row_ordinal"]): r for r in inv["rows"]}
    records = [classify_observation_v1(c, 1206, closure, rows) for c in cells]
    assert [r["class"] for r in records] == ["CORE_CANDIDATE", "CORE_CANDIDATE"]
    mappings, retained = _fragments(cells, records, {"MILLION_VND", "VND"}, {1: statement_period_context_v1(CONTEXT)})
    ledger = {"cells": cells, "classifications": records, "retained": retained, "dispositions": [disposition],
              "root_closures": [{"table": [VID, "s1", "t1"], "closure": closure}],
              "source_ledger": [{"inventory": inv,
                  "table_classification": classify_table_v1(inv["table"], inv["section"], {(VID, 1, 1): closure},
                      config.families[FAMILY].raw["subjects"]["OPERATING_EXPENSE_NOTE"]["any"]),
                  "rows": classify_rows_v1(inv["rows"], inv["columns"], cells, closure)}],
              "primary_income_context_texts": CONTEXT, "scope": "REQUESTED_F36_NOTES_DOCUMENT"}
    material = {**disposition["locator"], "status": "READY", "reasons": [], "mappings": mappings,
                "closure_receipt": ledger, "component_regions": [disposition["locator"]]}
    candidate = {**material, "candidate_id": "gjf36ncv1:candidate:" + canonical_json_sha256_v1(material)}
    trial = {"document_ordinal": 1, "source_logical_name": doc["source_logical_name"], "source_sha256": doc["source_sha256"],
             "status": "READY", "candidate_count": 1, "candidates": [candidate], "selected_candidate_id": candidate["candidate_id"],
             "mappings": mappings, "reasons": [], "notes_ledger": ledger}
    return compiled, trial, index_id


def sweep_of(compiled, trial, index_id):
    query = build_f36_notes_query_evidence_v1(trials=[trial], compiled_specs=compiled)
    return build_f36_notes_core_sweep_v1(corpus_manifest_index_id=index_id, topology_spec=compiled["topology"],
        evaluation_spec=compiled["evaluation"], schema_binding_spec=compiled["schema"], trials=[trial], indexed_query_evidence=query)


def reseal_trial(trial):
    candidate = trial["candidates"][0]
    candidate["mappings"] = deepcopy(trial["mappings"])
    candidate["closure_receipt"] = deepcopy(trial["notes_ledger"])
    material = {k: v for k, v in candidate.items() if k != "candidate_id"}
    candidate["candidate_id"] = "gjf36ncv1:candidate:" + canonical_json_sha256_v1(material)
    trial["selected_candidate_id"] = candidate["candidate_id"]


def test_existing_money_ids_source_contract_and_full_retention(example):
    compiled, trial, index_id = example
    sweep = sweep_of(compiled, trial, index_id)
    checked = validate_f36_notes_core_sweep_v1(sweep)
    assert canonical_json_bytes_v1(checked) == canonical_json_bytes_v1(sweep)
    assert sweep["format_version"] == FORMAT and "PROPOSAL_ONLY" in sweep["state"]
    mapping = sweep["trials"][0]["mappings"][0]
    assert mapping["report_norm_id"] == 1206 and mapping["values"] == [
        {"source_text": "1", "coefficient": 1, "state": "RAW_SIGNED_INTEGER"}] * 2
    assert [p["parsed_period"]["role"] for p in mapping["period_axis"]] == ["CURRENT", "COMPARATIVE"]
    assert len(sweep["trials"][0]["notes_ledger"]["source_ledger"][0]["rows"]) == 16
    assert mapping["source_refs"][1]["money_column_ordinals"] == [3]


@pytest.mark.parametrize("field,value", [("family_root_population_policy", "SUBTREE"),
    ("family_root_requirement", "OPTIONAL"), ("period_lane_policy", "CURRENT_ONLY"),
    ("source_presentation_rounding_policy", "UNBOUNDED")])
def test_family_policy_cannot_be_relaxed(example, field, value):
    compiled, _, _ = example
    compiled["evaluation"]["production_policy"][field] = value
    with pytest.raises(F36NotesCoreAdapterError, match="Production F36"):
        compile_f36_notes_core_specs_v1(compiled["topology"], compiled["evaluation"], compiled["schema"])


@pytest.mark.parametrize("target", ["family", "receipt", "ordinal", "version", "duplicate_page", "duplicate_crosswalk"])
def test_bad_declared_source_and_config_axes_fail(example, target):
    compiled, _, _ = example
    if target == "family":
        compiled["evaluation"]["family_id"] = "INCOME_TAX"
    elif target == "receipt":
        del compiled["evaluation"]["frontier_receipt_refs"]["neutral_inventory"]
    elif target == "ordinal":
        compiled["topology"]["source"]["document_axis"][0]["document_ordinal"] = True
    elif target == "version":
        compiled["evaluation"]["format_version"] = "ACCOUNTING_MULTITABLE_HIERARCHICAL_FAMILY_EVALUATION_SPEC_V1"
    elif target == "duplicate_page":
        pages = compiled["topology"]["source"]["document_axis"][0]["pages"]
        pages.append(deepcopy(pages[0]))
    else:
        compiled["schema"]["crosswalk"].append(deepcopy(compiled["schema"]["crosswalk"][0]))
    with pytest.raises(F36NotesCoreAdapterError):
        compile_f36_notes_core_specs_v1(compiled["topology"], compiled["evaluation"], compiled["schema"])


@pytest.mark.parametrize("target", ["raw", "value", "rnid", "state", "source_column", "root_equation", "retention"])
def test_resealed_candidates_cannot_hide_structural_or_source_drift(example, target):
    compiled, trial, index_id = example
    if target in {"raw", "value", "rnid", "state"}:
        field, value = {"raw": ("raw", "9"), "value": ("value", "9"), "rnid": ("report_norm_id", 999),
                        "state": ("observation_state", "DASH")}[target]
        trial["notes_ledger"]["cells"][0][field] = value
    elif target == "source_column":
        trial["mappings"][0]["source_refs"][0]["money_column_ordinals"] = [1]
        material = {k: v for k, v in trial["mappings"][0].items() if k != "item_mapping_id"}
        trial["mappings"][0]["item_mapping_id"] = "gjmthfmv1:item:" + canonical_json_sha256_v1(material)
    elif target == "root_equation":
        trial["notes_ledger"]["dispositions"][0]["equations"][-1]["status"] = "FAIL"
    else:
        trial["notes_ledger"]["retained"].append({"lost": True})
    reseal_trial(trial)
    with pytest.raises(F36NotesCoreAdapterError):
        sweep_of(compiled, trial, index_id)


@pytest.mark.parametrize("target", ["single", "duplicate_period", "unaccepted_unit", "fraction"])
def test_partial_or_unsupported_encoding_stays_outside_canonical_without_fabrication(example, target):
    _compiled, trial, _ = example
    cells, records = deepcopy((trial["notes_ledger"]["cells"], trial["notes_ledger"]["classifications"]))
    if target == "single":
        cells, records = cells[:1], records[:1]
    elif target == "duplicate_period":
        cells[1]["period_key"] = cells[0]["period_key"]
    elif target == "unaccepted_unit":
        for c in cells:
            c["unit"] = "BILLION_VND"
    else:
        for c in cells:
            c["raw"], c["value"] = "1,5", "1.5"
    for c, record in zip(cells, records, strict=True):
        record["cell"] = deepcopy(c)
    before = canonical_json_bytes_v1([cells, records])
    mappings, retained = _fragments(cells, records, {"MILLION_VND", "VND"}, {1: statement_period_context_v1(CONTEXT)})
    assert not mappings and len(retained) == len(cells)
    assert before == canonical_json_bytes_v1([cells, records])


def test_forged_core_flag_without_root_receipt_is_not_sufficient(example):
    _, trial, _ = example
    cells, records = deepcopy((trial["notes_ledger"]["cells"], trial["notes_ledger"]["classifications"]))
    records[0].pop("lane_closure")
    with pytest.raises(F36NotesCoreAdapterError, match="Core structural"):
        _fragments(cells, records, {"MILLION_VND"}, {1: statement_period_context_v1(CONTEXT)})


def test_sweep_outputs_do_not_alias_the_complete_input_trees(example):
    compiled, trial, index_id = example
    before = canonical_json_bytes_v1([compiled, trial])
    sweep = sweep_of(compiled, trial, index_id)
    sweep["trials"][0]["notes_ledger"]["cells"][0]["raw"] = "changed"
    sweep["specs"]["evaluation"]["value"]["notes_config_pins"].clear()
    assert canonical_json_bytes_v1([compiled, trial]) == before


def test_declarations_are_not_io_authentication_and_missing_pins_stop_before_source_work(example, tmp_path):
    compiled, trial, _ = example
    query = build_f36_notes_query_evidence_v1(trials=[trial], compiled_specs=compiled)
    with pytest.raises(F36NotesCoreAdapterError, match="Pinned replay input"):
        replay_f36_notes_core_trials_from_source_v1(source_page_database=tmp_path / "not-a-source.sqlite3",
            selected_page_json_version_ids=[VID], compiled_specs=compiled, indexed_query_evidence=query)


def test_neutral_envelopes_reuse_original_presence_null_and_hash_domains():
    page = {"sections": [{"content_kind": "NOTE", "tables": [{"columns": [{"value_kind": "MONEY"}],
             "rows": [{"row_kind": "TOTAL", "label_exact": None, "hierarchy_path_exact": [], "values_exact": [None]}]}]}]}
    inv = _inventory(page, VID, PAGE_BLOB)[(VID, "s1", "t1")]
    assert inv["rows"][0]["fields"]["label_exact"] == {"present": True, "value": None}
    assert inv["rows"][0]["value_axis"]["null_column_ordinals"] == [1]
    assert inv["rows"][0]["value_axis"]["items_one_lf_sha256"] == [canonical_json_sha256_v1(None)]
    assert inv["page"]["source_proof"]["stored_blob_two_lf_sha256"] == PAGE_BLOB
