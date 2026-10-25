"""UNRUN synthetic codec/frontier contracts; no financial or IO acceptance claim."""
from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest
from test_notes_annual_policy import CALENDAR, INTERIM_Q4, YEAR_ENDED, policy_page
from test_notes_f36_strict_ledger import cell
from test_notes_root_closure import PAGE_BLOB, build, lpb

from bctc_ai.evaluation.gemini_json_f36_notes_core_adapter_v1 import (
    EVALUATION_FORMAT,
    FAMILY,
    FORMAT,
    SCHEMA_FORMAT,
    TOPOLOGY_FORMAT,
    F36NotesCoreAdapterError,
    _annual_capture_json_v1,
    _annual_context_v1,
    _fragments,
    _inventory,
    _production_table_policy_v1,
    _quarter_frame_lane_v1,
    build_f36_notes_core_sweep_v1,
    build_f36_notes_query_evidence_v1,
    compile_f36_notes_core_specs_v1,
    replay_f36_notes_core_trials_from_source_v1,
    validate_f36_notes_core_sweep_v1,
)
from bctc_ai.notes.annual_policy_v1 import PolicyCapture, policy_page_v1
from bctc_ai.notes.config_v1 import load_notes_config_v1
from bctc_ai.notes.f36_strict_ledger_v1 import (
    classify_observation_v1,
    classify_rows_v1,
    classify_table_v1,
)
from bctc_ai.notes.root_closure_v1 import root_closure_v1
from bctc_ai.primary_statements.periods_v1 import (
    duration_lane_period_v1,
    statement_period_context_v1,
)
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
    production = {}
    for field, filename in (("production_topology", "tm-operating-expense-topology-v1.json"),
                            ("production_schema_binding", "tm-operating-expense-schema-binding-v1.json")):
        path = ROOT / "config/families" / filename
        raw = path.read_bytes()
        production[field] = json.loads(raw)
        production[field + "_ref"] = {"path": str(path), "sha256": sha256(raw).hexdigest(), "size_bytes": len(raw)}
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
                  **production,
                  "notes_family": {"raw": config.families[FAMILY].raw, "sha256": config.families[FAMILY].sha256,
                      "axis": {"name": config.families[FAMILY].axis.name, "members": config.families[FAMILY].axis.members,
                               "outside_members": config.families[FAMILY].axis.outside_members}},
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
    inv["table"]["fields"] = {"title_exact": {"present": True, "value": None}}
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
    production_receipt = _production_table_policy_v1(inv, disposition, closure, compiled)
    policies = {(VID, "s1", "t1"): production_receipt}
    mappings, retained = _fragments(cells, records, {"MILLION_VND", "VND"}, {1: statement_period_context_v1(CONTEXT)}, policies,
                                   compiled["evaluation"]["production_schema_binding"])
    ledger = {"cells": cells, "classifications": records, "retained": retained, "dispositions": [disposition],
              "root_closures": [{"table": [VID, "s1", "t1"], "closure": closure}],
              "production_policy_receipts": [{"table": [VID, "s1", "t1"], "receipt": production_receipt}],
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


def policies_of(trial):
    return {tuple(p["table"]): p["receipt"] for p in trial["notes_ledger"]["production_policy_receipts"]}


def test_existing_money_ids_source_contract_and_full_retention(example):
    compiled, trial, index_id = example
    sweep = sweep_of(compiled, trial, index_id)
    checked = validate_f36_notes_core_sweep_v1(sweep)
    assert canonical_json_bytes_v1(checked) == canonical_json_bytes_v1(sweep)
    assert sweep["format_version"] == FORMAT and "PROPOSAL_ONLY" in sweep["state"]
    mapping = sweep["trials"][0]["mappings"][0]
    assert mapping["report_norm_id"] == 1206 and mapping["values"] == [
        {"source_text": "1", "coefficient": 1, "state": "RAW_SIGNED_INTEGER"}] * 2
    assert mapping["role"] == "TAX_FEES" and mapping["notes_member"] == "TAX_FEES"
    assert [p["parsed_period"]["role"] for p in mapping["period_axis"]] == ["CURRENT", "COMPARATIVE"]
    assert len(sweep["trials"][0]["notes_ledger"]["source_ledger"][0]["rows"]) == 16
    assert mapping["source_refs"][1]["money_column_ordinals"] == [3]


def test_reversed_printed_lanes_keep_current_first_and_all_original_evidence_aligned(example):
    compiled, trial, index_id = example
    ledger = trial["notes_ledger"]
    # Printed c2 is comparative; printed c3 is current. Distinct amounts make
    # an accidental physical-order export observable without selecting by value.
    current, comparative = ledger["cells"]
    for c, column, raw in ((current, 3, "25"), (comparative, 2, "24")):
        c["original_cell"]["column_ordinal"] = column
        c["locator"]["column_id"] = f"c{column}"
        c["raw"], c["value"] = raw, raw
    ledger["cells"] = [comparative, current]  # retain actual producer physical order
    inventory = ledger["source_ledger"][0]["inventory"]
    row = inventory["rows"][0]
    row["value_axis"]["items_one_lf_sha256"] = [canonical_json_sha256_v1(v) for v in (None, "24", "25")]
    rows = {(VID, 1, 1, r["row_ordinal"]): r for r in inventory["rows"]}
    closure = ledger["root_closures"][0]["closure"]
    ledger["classifications"] = [classify_observation_v1(c, 1206, closure, rows) for c in ledger["cells"]]
    ledger_before = canonical_json_bytes_v1(ledger)
    mappings, retained = _fragments(ledger["cells"], ledger["classifications"], {"MILLION_VND", "VND"},
                                   {1: statement_period_context_v1(CONTEXT)}, policies_of(trial),
                                   compiled["evaluation"]["production_schema_binding"])
    assert not retained and canonical_json_bytes_v1(ledger) == ledger_before
    trial["mappings"] = mappings
    reseal_trial(trial)
    checked = validate_f36_notes_core_sweep_v1(sweep_of(compiled, trial, index_id))
    mapping = checked["trials"][0]["mappings"][0]
    assert [v["coefficient"] for v in mapping["values"]] == [25, 24]
    assert [r["money_column_ordinals"] for r in mapping["source_refs"]] == [[3], [2]]
    assert [p["original_column_ordinal"] for p in mapping["period_axis"]] == [3, 2]
    assert [p["parsed_period"]["role"] for p in mapping["period_axis"]] == ["CURRENT", "COMPARATIVE"]
    assert [c["locator"]["column_id"] for c in checked["trials"][0]["notes_ledger"]["cells"]] == ["c2", "c3"]
    assert canonical_json_bytes_v1(checked["trials"][0]["notes_ledger"]) == ledger_before


@pytest.mark.parametrize("field,value", [("family_root_population_policy", "SUBTREE"),
    ("family_root_requirement", "OPTIONAL"), ("period_lane_policy", "CURRENT_ONLY"),
    ("source_presentation_rounding_policy", "UNBOUNDED")])
def test_family_policy_cannot_be_relaxed(example, field, value):
    compiled, _, _ = example
    compiled["evaluation"]["production_policy"][field] = value
    with pytest.raises(F36NotesCoreAdapterError, match="Production F36"):
        compile_f36_notes_core_specs_v1(compiled["topology"], compiled["evaluation"], compiled["schema"])


@pytest.mark.parametrize("target", ["family", "receipt", "ordinal", "version", "duplicate_page", "duplicate_crosswalk", "role_axis"])
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
    elif target == "duplicate_crosswalk":
        compiled["schema"]["crosswalk"].append(deepcopy(compiled["schema"]["crosswalk"][0]))
    else:
        compiled["evaluation"]["notes_family"]["axis"]["members"].clear()
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
    mappings, retained = _fragments(cells, records, {"MILLION_VND", "VND"}, {1: statement_period_context_v1(CONTEXT)}, policies_of(trial),
                                   _compiled["evaluation"]["production_schema_binding"])
    assert not mappings and len(retained) == len(cells)
    assert before == canonical_json_bytes_v1([cells, records])


def test_forged_core_flag_without_root_receipt_is_not_sufficient(example):
    compiled, trial, _ = example
    cells, records = deepcopy((trial["notes_ledger"]["cells"], trial["notes_ledger"]["classifications"]))
    records[0].pop("lane_closure")
    with pytest.raises(F36NotesCoreAdapterError, match="Core structural"):
        _fragments(cells, records, {"MILLION_VND"}, {1: statement_period_context_v1(CONTEXT)}, policies_of(trial),
                   compiled["evaluation"]["production_schema_binding"])


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


@pytest.mark.parametrize("count,blocked", [(2, True), (3, False)])
def test_production_minimum_counts_distinct_source_frontier_roles_not_total_or_emitted_cells(example, count, blocked):
    compiled, trial, _ = example
    source = [lpb()[i] for i in (0, 1, 5)[:count]]
    source.append(("Tổng chi phí hoạt động", "TOTAL", (str(count), str(count)), None, "TOTAL_OPERATING_EXPENSE"))
    inv, disposition = build(source)
    inv["section"] = {"fields": {"title_exact": {"present": True, "value": "Chi phí hoạt động"}}}
    config = load_notes_config_v1(ROOT)
    closure = root_closure_v1(inv, disposition, config.families[FAMILY])
    receipt = _production_table_policy_v1(inv, disposition, closure, compiled)
    assert len(receipt["distinct_configured_root_roles"]) == count
    assert ("F36_PRODUCTION_ROOT_COMPONENT_MINIMUM_NOT_MET" in receipt["reasons"]) is blocked
    cells, records = trial["notes_ledger"]["cells"], trial["notes_ledger"]["classifications"]
    before = canonical_json_bytes_v1([cells, records])
    mappings, retained = _fragments(cells, records, {"MILLION_VND"}, {1: statement_period_context_v1(CONTEXT)},
                                   {(VID, "s1", "t1"): receipt}, compiled["evaluation"]["production_schema_binding"])
    assert bool(mappings) is not blocked
    assert len(retained) == (2 if blocked else 0)
    if blocked:
        assert all("F36_PRODUCTION_ROOT_COMPONENT_MINIMUM_NOT_MET" in r["policy_reasons"] for r in retained)
    assert before == canonical_json_bytes_v1([cells, records])


@pytest.mark.parametrize("section_title,table_title,allowed", [
    ("Chi phí hoạt động", None, True),
    ("41. Chi phí hoạt động", None, True),
    (None, "Chi phí quản lý chung (Chi phí hoạt động)", True),
    ("Chi phí hoạt động dự kiến", None, False),
    (None, "Chi phí hoạt động dự kiến", False),
    (None, None, False),
    ("41. Chi phí hoạt động (tiếp theo)", "Chi phí hoạt động", True),
    ("41. Chi phí hoạt động (tiếp theo)", None, False),
])
def test_only_original_owned_production_title_surfaces_grant_owner(example, section_title, table_title, allowed):
    compiled, trial, _ = example
    ledger = trial["notes_ledger"]
    inv = deepcopy(ledger["source_ledger"][0]["inventory"])
    inv["section"]["fields"]["title_exact"] = {"present": True, "value": section_title}
    inv["table"]["fields"]["title_exact"] = {"present": True, "value": table_title}
    # These broader notes authorities must never become the production owner.
    inv["section"]["narratives_exact"] = ["Chi phí hoạt động"]
    inv["preceding_heading"] = "Chi phí hoạt động"
    receipt = _production_table_policy_v1(inv, ledger["dispositions"][0], ledger["root_closures"][0]["closure"], compiled)
    assert ("F36_PRODUCTION_ORIGINAL_OWNER_NOT_PROVEN" not in receipt["reasons"]) is allowed
    assert receipt["source_owner_surfaces"] == {"SECTION_TITLE": section_title, "TABLE_TITLE": table_title}


def test_existing_rnid_binding_bridges_provision_role_spelling_for_frontier_count(example):
    compiled, _, _ = example
    source = [lpb()[0], lpb()[1], ("Dự phòng đầu tư dài hạn", "ITEM", ("1", "1"), None, "LONG_TERM_INVESTMENT_PROVISION"),
              ("Tổng chi phí hoạt động", "TOTAL", ("3", "3"), None, "TOTAL_OPERATING_EXPENSE")]
    inv, disposition = build(source, terms=["TAX_FEES", "EMPLOYEE_EXPENSE", "LONG_TERM_INVESTMENT_PROVISION"])
    inv["section"] = {"fields": {"title_exact": {"present": True, "value": "Chi phí hoạt động"}}}
    family = load_notes_config_v1(ROOT).families[FAMILY]
    receipt = _production_table_policy_v1(inv, disposition, root_closure_v1(inv, disposition, family), compiled)
    assert receipt["distinct_configured_root_roles"] == ["EMPLOYEE_EXPENSE", "LONG_TERM_BAD_DEBT_PROVISION", "TAX_FEES"]
    assert not receipt["reasons"]


@pytest.mark.parametrize("topology_change,proven", [
    (None, True),
    ("WITHIN_ROLE", False),  # the bound role is no longer declared top-level
    ("REMOVED", False),      # the bound role is no longer declared at all
])
def test_goodwill_frontier_counts_only_through_the_declared_top_level_source_only_role(example, topology_change, proven):
    compiled, _, _ = example
    compiled = deepcopy(compiled)
    children = compiled["evaluation"]["production_topology"]["children"]
    child = next(c for c in children if c["role"] == "GOODWILL_AMORTIZATION_SOURCE_ONLY")
    if topology_change == "WITHIN_ROLE":
        child["matchers"][0]["within_role"] = "ASSET_EXPENSE"
    elif topology_change == "REMOVED":
        children.remove(child)
    source = [lpb()[0], lpb()[1], ("Phân bổ lợi thế thương mại", "ITEM", ("1", "1"), None, "GOODWILL_AMORTIZATION"),
              ("Tổng chi phí hoạt động", "TOTAL", ("3", "3"), None, "TOTAL_OPERATING_EXPENSE")]
    inv, disposition = build(source, terms=["TAX_FEES", "EMPLOYEE_EXPENSE", "GOODWILL_AMORTIZATION"])
    inv["section"] = {"fields": {"title_exact": {"present": True, "value": "Chi phí hoạt động"}}}
    family = load_notes_config_v1(ROOT).families[FAMILY]
    receipt = _production_table_policy_v1(inv, disposition, root_closure_v1(inv, disposition, family), compiled)
    goodwill = next(r for r in receipt["source_frontier"] if r["notes_member"] == "GOODWILL_AMORTIZATION")
    assert goodwill["production_role"] == ("GOODWILL_AMORTIZATION_SOURCE_ONLY" if proven else None)
    assert ("F36_PRODUCTION_FRONTIER_ROLE_UNPROVEN" in receipt["reasons"]) is not proven
    if proven:
        assert receipt["distinct_configured_root_roles"] == ["EMPLOYEE_EXPENSE", "GOODWILL_AMORTIZATION_SOURCE_ONLY", "TAX_FEES"]


def test_resealed_owner_policy_receipt_cannot_waive_original_title_mismatch(example):
    compiled, trial, index_id = example
    trial["notes_ledger"]["source_ledger"][0]["inventory"]["section"]["fields"]["title_exact"]["value"] = "Chi phí hoạt động dự kiến"
    # Keep the old empty refusal list and reseal all candidate/query ids.
    reseal_trial(trial)
    with pytest.raises(F36NotesCoreAdapterError, match="Production owner/frontier policy"):
        sweep_of(compiled, trial, index_id)


@pytest.mark.parametrize("member,rnid,role", [("TOTAL_OPERATING_EXPENSE", 1205, "FAMILY_ROOT_TOTAL"),
    ("LONG_TERM_INVESTMENT_PROVISION", 1218, "LONG_TERM_BAD_DEBT_PROVISION"), ("TAX_FEES", 1206, "TAX_FEES")])
def test_existing_production_rnid_binding_sets_role_and_hashes_original_notes_member(example, member, rnid, role):
    compiled, trial, _ = example
    cells, records = deepcopy((trial["notes_ledger"]["cells"], trial["notes_ledger"]["classifications"]))
    for c, record in zip(cells, records, strict=True):
        c["member"], c["report_norm_id"] = member, rnid
        record["cell"], record["exact_rnid_binding"] = deepcopy(c), rnid
    before = canonical_json_bytes_v1([cells, records])
    mappings, retained = _fragments(cells, records, {"MILLION_VND"}, {1: statement_period_context_v1(CONTEXT)},
        policies_of(trial), compiled["evaluation"]["production_schema_binding"])
    assert not retained and len(mappings) == 1
    assert mappings[0]["role"] == role and mappings[0]["notes_member"] == member
    assert mappings[0]["item_mapping_id"] == "gjmthfmv1:item:" + canonical_json_sha256_v1(
        {k: v for k, v in mappings[0].items() if k != "item_mapping_id"})
    assert before == canonical_json_bytes_v1([cells, records])


@pytest.mark.parametrize("problem,reason", [("unknown", "F36_CANONICAL_RNID_ROLE_UNDECLARED"),
    ("duplicate", "F36_CANONICAL_RNID_ROLE_AMBIGUOUS"), ("root_collision", "F36_CANONICAL_RNID_ROLE_AMBIGUOUS")])
def test_unknown_or_ambiguous_production_rnid_never_picks_a_role(example, problem, reason):
    compiled, trial, _ = example
    cells, records = deepcopy((trial["notes_ledger"]["cells"], trial["notes_ledger"]["classifications"]))
    schema = deepcopy(compiled["evaluation"]["production_schema_binding"])
    rnid = 987654 if problem == "unknown" else 1206
    if problem == "duplicate":
        schema["role_bindings"].append({"report_norm_id": rnid, "role": "TAX_FEES"})
    elif problem == "root_collision":
        rnid = schema["family_root_report_norm_id"]
        schema["role_bindings"].append({"report_norm_id": rnid, "role": "TAX_FEES"})
    for c, record in zip(cells, records, strict=True):
        c["report_norm_id"] = rnid
        record["cell"], record["exact_rnid_binding"] = deepcopy(c), rnid
    before = canonical_json_bytes_v1([cells, records])
    mappings, retained = _fragments(cells, records, {"MILLION_VND"}, {1: statement_period_context_v1(CONTEXT)}, policies_of(trial), schema)
    assert not mappings and len(retained) == 2
    assert {r["adapter_disposition"] for r in retained} == {reason}
    assert before == canonical_json_bytes_v1([cells, records])


def annual_example(example):
    compiled, trial, index_id = deepcopy(example)
    doc = compiled["topology"]["source"]["document_axis"][0]
    policy_vid = "gfpstorev1:json:" + "8" * 64
    doc["pages"].insert(0, {"physical_page": 12, "page_json_version_id": policy_vid})
    doc["document_identity"]["document_plan_id"] = "synthetic-plan"
    page = policy_page_v1(policy_page(CALENDAR), page_json_version_id=policy_vid, physical_page=12,
                         original_blob_sha256="a" * 64, replay_receipt_id="synthetic-policy-replay")
    capture = PolicyCapture((1, "synthetic.pdf", "1" * 64, "SEPARATE"), ((policy_vid, 1), (VID, 0)), (page,))
    ledger = trial["notes_ledger"]
    ledger["primary_income_context_texts"] = INTERIM_Q4
    serialized = _annual_capture_json_v1(capture)
    assert type(serialized["binding"]) is list and type(serialized["frontier"]) is list
    assert all(type(item) is list for item in serialized["frontier"])
    assert type(serialized["pages"][0]["narratives"]) is list
    assert all(type(item) is list for item in serialized["pages"][0]["narratives"])
    assert canonical_json_bytes_v1(serialized) == canonical_json_bytes_v1(json.loads(json.dumps(serialized)))
    ledger["annual_period_context"] = {"capture": serialized,
        "owned_table_texts": [{"table": [VID, "s1", "t1"], "texts": ["Chi phí hoạt động"]}]}
    for c, header in zip(ledger["cells"], YEAR_ENDED, strict=True):
        c["header_text"] = header[0]
        c["period_basis"] = f"PRINTED_YEAR_ENDED_WITH_DOCUMENT_ANNUAL_POLICY:{policy_vid}@p12/sections/0/narratives_exact/0"
    rows = {(VID, 1, 1, r["row_ordinal"]): r for r in ledger["source_ledger"][0]["inventory"]["rows"]}
    closure = ledger["root_closures"][0]["closure"]
    ledger["classifications"] = [classify_observation_v1(c, 1206, closure, rows) for c in ledger["cells"]]
    return compiled, trial, index_id


def annual_fragments(compiled, trial):
    ledger = trial["notes_ledger"]
    doc = compiled["topology"]["source"]["document_axis"][0]
    annual = _annual_context_v1(ledger.get("annual_period_context"), doc, ledger["primary_income_context_texts"])
    return _fragments(ledger["cells"], ledger["classifications"], {"MILLION_VND"},
        {1: statement_period_context_v1(ledger["primary_income_context_texts"])}, policies_of(trial),
        compiled["evaluation"]["production_schema_binding"], {1: annual})


@pytest.mark.parametrize("reverse", [False, True])
def test_printed_year_ended_pair_reuses_verified_policy_under_q4_without_changing_source(example, reverse):
    compiled, trial, index_id = annual_example(example)
    ledger = trial["notes_ledger"]
    if reverse:
        ledger["primary_income_context_texts"] = ["Quý IV năm 2025 cho 3 tháng kết thúc ngày 31/12/2025"]
        report = statement_period_context_v1(ledger["primary_income_context_texts"])
        assert report.months == 3 and report.reporting_date == "2025-12-31" and not report.conflict
        assert duration_lane_period_v1(ledger["cells"][0]["header_text"], report).key == "DURATION:MONTHS_ENDED:3:2025-12-31"
        for c, column in zip(ledger["cells"], (3, 2), strict=True):
            c["original_cell"]["column_ordinal"] = column
            c["locator"]["column_id"] = f"c{column}"
        ledger["cells"].reverse()
        rows = {(VID, 1, 1, r["row_ordinal"]): r for r in ledger["source_ledger"][0]["inventory"]["rows"]}
        closure = ledger["root_closures"][0]["closure"]
        ledger["classifications"] = [classify_observation_v1(c, 1206, closure, rows) for c in ledger["cells"]]
    before = canonical_json_bytes_v1(ledger)
    mappings, retained = annual_fragments(compiled, trial)
    assert len(mappings) == 1 and not retained
    assert [p["parsed_period"]["role"] for p in mappings[0]["period_axis"]] == ["CURRENT", "COMPARATIVE"]
    assert [p["period_key"] for p in mappings[0]["period_axis"]] == ["DURATION:YEAR:2025", "DURATION:YEAR:2024"]
    assert [r["money_column_ordinals"] for r in mappings[0]["source_refs"]] == ([[3], [2]] if reverse else [[2], [3]])
    assert all(p["parsed_period"]["resolution"] == "CONTEXT_BOUND" for p in mappings[0]["period_axis"])
    assert canonical_json_bytes_v1(ledger) == before
    trial["mappings"], ledger["retained"] = mappings, retained
    reseal_trial(trial)
    assert validate_f36_notes_core_sweep_v1(sweep_of(compiled, trial, index_id))["trials"][0]["mappings"] == mappings


@pytest.mark.parametrize("attack", ["absent", "absent_full_year_primary", "narrative_drift", "stale_pointer", "scope", "header", "basis", "period", "midyear", "own_quarter", "report_midyear"])
def test_annual_period_fallback_never_uses_unproven_capture_or_changed_lane_axes(example, attack):
    compiled, trial, _ = annual_example(example)
    ledger = trial["notes_ledger"]
    if attack in {"absent", "absent_full_year_primary"}:
        del ledger["annual_period_context"]
        if attack == "absent_full_year_primary":
            ledger["primary_income_context_texts"] = ["Cho 12 tháng kết thúc ngày 31/12/2025"]
    elif attack == "narrative_drift":
        ledger["annual_period_context"]["capture"]["pages"][0]["narratives"][0][1] += " unknown"
    elif attack == "stale_pointer":
        page = ledger["annual_period_context"]["capture"]["pages"][0]
        page["narratives"][0][0] = "/sections/0/narratives_exact/1"
        page["narratives_sha256"] = canonical_json_sha256_v1(page["narratives"])
    elif attack == "scope":
        ledger["annual_period_context"]["capture"]["binding"][3] = "CONSOLIDATED"
    elif attack == "own_quarter":
        ledger["annual_period_context"]["owned_table_texts"][0]["texts"] = ["Cho chín tháng kết thúc ngày 30/09/2025"]
    elif attack == "report_midyear":
        ledger["primary_income_context_texts"] = ["Cho 6 tháng kết thúc ngày 30/06/2025"]
    else:
        for c in ledger["cells"]:
            if attack == "header":
                c["header_text"] = c["header_text"].replace("202", "２０２")
            elif attack == "basis":
                c["period_basis"] += "FORGED"
            elif attack == "period":
                c["period_key"] = {"DURATION:YEAR:2025": "DURATION:YEAR:2023", "DURATION:YEAR:2024": "DURATION:YEAR:2022"}[c["period_key"]]
            elif attack == "midyear":
                c["header_text"] = c["header_text"].replace("31/12", "30/06")
    for c, record in zip(ledger["cells"], ledger["classifications"], strict=True):
        record["cell"] = deepcopy(c)
    mappings, retained = annual_fragments(compiled, trial)
    assert not mappings and len(retained) == 2
    assert {r["adapter_disposition"] for r in retained} == {"SOURCE_PERIOD_ROLE_PAIR_NOT_PROVEN_BY_EXISTING_PARSER"}


@pytest.mark.parametrize("attack", ["source", "missing_frontier", "bool_frontier", "page", "status_only"])
def test_annual_capture_must_name_exact_document_and_complete_selected_axis(example, attack):
    compiled, trial, _ = annual_example(example)
    capture = trial["notes_ledger"]["annual_period_context"]["capture"]
    if attack == "source":
        capture["binding"][2] = "2" * 64
    elif attack == "missing_frontier":
        capture["frontier"].pop()
    elif attack == "bool_frontier":
        capture["frontier"][0][1] = True
    elif attack == "page":
        capture["pages"][0]["physical_page"] = 13
    else:
        trial["notes_ledger"]["annual_period_context"]["capture"] = {"status": "CALENDAR_YEAR"}
    with pytest.raises(F36NotesCoreAdapterError, match="Annual"):
        annual_fragments(compiled, trial)


@pytest.mark.parametrize("frame,header,role,shape", [
    ("BÁO CÁO KẾT QUẢ HOẠT ĐỘNG RIÊNG\nQuý I năm 2025", "Kỳ ba tháng kết thúc ngày 31/03/2025\nTriệu VND", "CURRENT",
     "MONTHS_ENDED:3:03-31"),
    ("BÁO CÁO KẾT QUẢ HOẠT ĐỘNG RIÊNG\nQuý I năm 2025", "Kỳ ba tháng kết thúc ngày 31/03/2024\nTriệu VND", "COMPARATIVE",
     "MONTHS_ENDED:3:03-31"),
    ("BÁO CÁO KẾT QUẢ HOẠT ĐỘNG RIÊNG\nQuý III năm 2025", "Từ 01/01/2025 đến 30/09/2025", "CURRENT", "RANGE:01-01..09-30"),
    ("BÁO CÁO KẾT QUẢ HOẠT ĐỘNG RIÊNG\nQuý III năm 2025", "Từ 01/01/2024 đến 30/09/2024", "COMPARATIVE", "RANGE:01-01..09-30"),
    ("BÁO CÁO KẾT QUẢ HOẠT ĐỘNG HỢP NHẤT\nQuý II năm 2025", "Từ 01/04/2025 đến 30/06/2025", "CURRENT", "RANGE:04-01..06-30"),
    # A window that is not this frame's quarter end, two years back, or no printed frame: never a role.
    ("BÁO CÁO KẾT QUẢ HOẠT ĐỘNG RIÊNG\nQuý III năm 2025", "Từ 01/01/2025 đến 30/06/2025", None, None),
    ("BÁO CÁO KẾT QUẢ HOẠT ĐỘNG RIÊNG\nQuý I năm 2025", "Kỳ ba tháng kết thúc ngày 31/03/2023\nTriệu VND", None, None),
    ("BÁO CÁO KẾT QUẢ HOẠT ĐỘNG RIÊNG\nQuý I năm 2025", "Từ 01/02/2025 đến 31/03/2025", None, None),
    ("", "Kỳ 6 tháng kết thúc ngày\n30.6.2025\nTriệu đồng", None, None),
])
def test_printed_quarter_frame_binds_only_matching_explicit_windows(frame, header, role, shape):
    context = statement_period_context_v1([frame] if frame else [])
    descriptor = duration_lane_period_v1(header, context)
    assert descriptor.role is None and descriptor.resolution == "EXPLICIT"
    bound = _quarter_frame_lane_v1(descriptor, context)
    assert bound.role == role and bound.key == descriptor.key
    assert dict(bound.fields).get("window_shape") == shape


def test_quarter_frame_is_refused_under_printed_non_calendar_fiscal_evidence():
    context = statement_period_context_v1(["BÁO CÁO KẾT QUẢ HOẠT ĐỘNG RIÊNG\nQuý I năm 2025"])
    descriptor = duration_lane_period_v1("Kỳ ba tháng kết thúc ngày 31/03/2025", context)
    for change in ({"fiscal_year_end": "2025-06-30"}, {"first_months_of_fiscal_year": 3}, {"conflict": "X"},
                   {"reporting_date": "2025-03-31"}):
        assert _quarter_frame_lane_v1(descriptor, replace(context, **change)) is descriptor
