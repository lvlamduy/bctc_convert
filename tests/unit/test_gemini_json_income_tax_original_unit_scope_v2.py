"""Original unit scope is independent of financial values and private units."""

from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256

import pytest
from test_gemini_json_income_tax_family_v1 import (
    _adapter_compiled,
    _primary_page,
    _primary_record,
    _primary_tax_rows,
    _primary_unit_control_page,
)
from test_gemini_json_income_tax_observed_subtotal_root_v1 import _original_records
from test_gemini_json_income_tax_signed_display_v1 import _records

from bctc_ai.evaluation import gemini_json_income_tax_family_v1 as family
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    audit_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

REASON = "ALGORITHM_ORIGINAL_INCOME_TAX_UNIT_SCOPE_UNPROVEN"


def _public(records, compiled=None):
    compiled = _adapter_compiled() if compiled is None else compiled
    base = family.coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled)
    cluster = family.recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled)
    if cluster["status"] != family.READY:
        return cluster, None
    options = {"regions": cluster["component_regions"],
        "page_json_by_version": {item["page_json_version_id"]: item["page_json"] for item in records},
        "selected_page_axis": [{key: value for key, value in item.items() if key != "page_json"} for item in records],
        "compiled_specs": compiled,
        "query_receipt": family.build_gemini_json_income_tax_region_query_receipt_v1(
            cluster["component_regions"], cluster=cluster)}
    return family.evaluate_gemini_json_income_tax_family_cluster_v1(**options), options


def _control(candidate):
    return candidate["closure_receipt"]["income_tax_original_unit_scope_receipt"]


def _audit_replay(candidate, options):
    audit = audit_source_observation_mapping_contract_v1(candidate)
    assert audit["status"] == "PASS", audit["violations"]
    assert audit["mapping_count"] == len(candidate["mappings"])
    assert family.validate_gemini_json_income_tax_family_candidate_replay_v1(candidate, **options) == candidate


def _primary_records(unit="Triệu đồng"):
    target = _primary_record(_primary_page(_primary_tax_rows(), unit=unit))
    target["selected_page_ordinal"] = 2
    balance = _primary_record(_primary_unit_control_page(statement_type="BALANCE_SHEET", unit="VND"),
        page_json_version_id="gfpstorev1:json:" + "d" * 64, physical_page=3, selected_page_ordinal=1)
    cash_flow = _primary_record(_primary_unit_control_page(statement_type="CASH_FLOW", unit="VND"),
        page_json_version_id="gfpstorev1:json:" + "e" * 64, physical_page=7, selected_page_ordinal=3)
    return [balance, target, cash_flow]


@pytest.mark.parametrize("case", ["bab-doc020", "eib-doc039"])
def test_original_raw_local_units_survive_public_source_replay_without_fixture_unit_fills(case):
    _metadata, records = _original_records(case)
    original = deepcopy(records)
    candidate, options = _public(records)
    assert options is not None and candidate["status"] == family.READY, candidate.get("reasons")
    receipt = _control(candidate)
    assert receipt["failures"] == []
    assert receipt["document_consensus_equal_amount_or_private_unit_projection_permission"] is False
    assert all(check["status"] == "SOURCE_OWNED" for check in receipt["checks"])
    assert records == original
    _audit_replay(candidate, options)


def test_two_primary_unit_votes_cannot_fill_an_original_unitless_primary_tax_table():
    records = _primary_records(unit=None)
    original = deepcopy(records)
    candidate, options = _public(records)
    assert options is not None
    assert candidate["status"] == family.UNRESOLVED and candidate["reasons"] == [REASON]
    assert candidate["mappings"] == []
    receipt = _control(candidate)
    target = next(check for check in receipt["checks"] if check["locator"]["selected_page_ordinal"] == 2)
    assert target["status"] == "HOLD"
    assert target["original_source_unit"]["original_local_unit_axis"]["axis"]["complete"] is False
    assert "PRIMARY_PROJECTION_SOURCE" in target["uses"]
    envelope = receipt["withheld_candidate_beforeimage"]
    raw = envelope["canonical_json"].encode("utf-8")
    assert len(raw) == envelope["size_bytes"] and sha256(raw).hexdigest() == envelope["sha256"]
    before = json.loads(raw)
    assert canonical_json_bytes_v1(before) == raw
    assert before["status"] == family.READY and before["mappings"]
    donated = before["closure_receipt"]["income_tax_adapter_receipt"]["primary_projection_receipt"]
    assert donated["primary_unit_corroboration_receipt"]["canonical_unit"] == "VND"
    assert records[1]["page_json"]["sections"][0]["tables"][0]["unit_exact"] is None
    assert candidate["closure_receipt"]["equations"] == []
    assert candidate["closure_receipt"]["root_component_sum_receipts"] == []
    assert candidate["closure_receipt"]["structural_root_receipt"]["emitted_mapping"] is False
    assert records == original
    _audit_replay(candidate, options)


def test_local_column_units_own_a_primary_when_its_table_unit_is_absent():
    record = _primary_record(_primary_page(_primary_tax_rows()))
    record["selected_page_ordinal"] = 1
    table = record["page_json"]["sections"][0]["tables"][0]
    table["unit_exact"] = None
    for column in table["columns"]:
        if column["value_kind"] == "MONEY":
            column["header_path_exact"].append("Triệu đồng")
    original = deepcopy(record)
    candidate, options = _public([record])
    assert candidate["status"] == family.READY and _control(candidate)["failures"] == []
    assert record == original
    _audit_replay(candidate, options)


def test_global_selected_axis_foreign_document_with_same_json_vid_is_not_an_original_unit_donor():
    record = _primary_record(_primary_page(_primary_tax_rows()))
    record["selected_page_ordinal"] = 1
    candidate, options = _public([record])
    assert candidate["status"] == family.READY
    foreign = deepcopy(options["selected_page_axis"][0])
    foreign.update({"document_id": "gfpstorev1:document:" + "f" * 64,
        "document_ordinal": 999, "source_sha256": "f" * 64,
        "source_logical_name": "independent-foreign-document.pdf"})
    options["selected_page_axis"].append(foreign)
    checked = family.evaluate_gemini_json_income_tax_family_cluster_v1(**options)
    assert checked == candidate
    assert all(check["locator"]["document_ordinal"] == 1 for check in _control(checked)["checks"])
    _audit_replay(checked, options)


def test_a_same_amount_primary_and_two_primary_unit_votes_do_not_own_a_raw_note_unit():
    records = _records()
    baseline, options = _public(records)
    assert options is not None and baseline["status"] == family.READY
    _audit_replay(baseline, options)
    note = records[0]["page_json"]["sections"][0]["tables"][0]
    note["unit_exact"] = None
    for column in note["columns"]:
        if column["value_kind"] == "MONEY":
            column["header_path_exact"] = [part for part in column["header_path_exact"]
                if family._normalized(part) not in {"trieu dong", "trieu vnd", "vnd", "dong"}]
    for ordinal, statement in enumerate(("BALANCE_SHEET", "CASH_FLOW"), 3):
        records.append(_primary_record(_primary_unit_control_page(statement_type=statement, unit="Triệu đồng"),
            page_json_version_id="gfpstorev1:json:" + str(ordinal) * 64,
            physical_page=ordinal + 10, selected_page_ordinal=ordinal))
    original = deepcopy(records)
    candidate, options = _public(records)
    assert candidate["status"] == family.UNRESOLVED and not candidate.get("mappings")
    if options is not None:
        _audit_replay(candidate, options)
    assert records == original


def test_an_unexported_typed_primary_control_still_needs_its_own_raw_unit():
    records = _records()[:1]
    baseline, options = _public(records)
    assert options is not None and baseline["status"] == family.READY
    _audit_replay(baseline, options)
    # With no second explicit PRIMARY unit, this unitless statement cannot
    # become a projected financial presentation. Its typed tax source remains
    # retained by the document's source-control inventory.
    control = _primary_record(_primary_page(_primary_tax_rows(
        current=("20", "16"), deferred=("2", "1"), root=("22", "17")), unit=None),
        page_json_version_id="gfpstorev1:json:" + "c" * 64, physical_page=2, selected_page_ordinal=2)
    records.append(control)
    original = deepcopy(records)
    candidate, options = _public(records)
    assert options is not None and candidate["status"] == family.UNRESOLVED
    assert candidate["reasons"] == [REASON] and candidate["mappings"] == []
    receipt = _control(candidate)
    source = next(check for check in receipt["checks"] if check["locator"]["selected_page_ordinal"] == 2)
    assert source["status"] == "HOLD"
    assert "RETAINED_TYPED_PRIMARY_TAX_SOURCE_CONTROL" in source["uses"]
    assert "EXPORTED_MAPPING_SOURCE" not in source["uses"]
    before = json.loads(receipt["withheld_candidate_beforeimage"]["canonical_json"])
    assert before["status"] == family.READY
    assert all(ref["locator"]["selected_page_ordinal"] == 1
        for mapping in before["mappings"] for ref in mapping["source_refs"])
    assert records == original
    _audit_replay(candidate, options)


def test_an_unselected_unknown_value_column_with_explicit_foreign_currency_is_a_veto():
    table = _primary_page(_primary_tax_rows())["sections"][0]["tables"][0]
    table["columns"].append({"header_path_exact": ["USD"], "value_kind": "UNKNOWN"})
    original = deepcopy(table)
    axis = family._original_local_unit_axis_v2(table, compiled_specs=_adapter_compiled())
    assert axis["original_declared_money_column_axis"]["complete"] is True
    assert axis["axis"]["complete"] is False
    assert axis["axis"]["undeclared_evidence"] or axis["axis"]["reasons"]
    assert table == original


def test_an_unknown_code_column_does_not_erase_independent_local_money_column_units():
    table = _primary_page(_primary_tax_rows())["sections"][0]["tables"][0]
    table["unit_exact"] = None
    for column in table["columns"]:
        column["header_path_exact"].append("Triệu đồng")
    table["columns"].append({"header_path_exact": ["Mã số"], "value_kind": "UNKNOWN"})
    original = deepcopy(table)
    axis = family._original_local_unit_axis_v2(table, compiled_specs=_adapter_compiled())
    assert axis["axis"]["complete"] is True and axis["axis"]["canonical_unit"] == "MILLION_VND"
    assert table == original


@pytest.mark.parametrize("suffix,complete", [("", True), (" Triệu đồng", True), (" VND", False)])
def test_exact_pnl_semantic_header_is_not_currency_but_its_explicit_unit_suffix_remains(suffix, complete):
    table = _primary_page(_primary_tax_rows())["sections"][0]["tables"][0]
    table["columns"][0]["header_path_exact"] = ["Được ghi nhận trong báo cáo kết quả hoạt động riêng" + suffix]
    original = deepcopy(table)
    axis = family._original_local_unit_axis_v2(table, compiled_specs=_adapter_compiled())
    assert axis["axis"]["complete"] is complete
    assert len(axis["noncurrency_semantic_headers"]) == 1
    assert axis["source_values_read"] is False
    assert table == original


def _continued_records():
    first = _primary_record(_primary_page(_primary_tax_rows()))
    first["physical_page"] = first["selected_page_ordinal"] = 1
    first["page_json"]["sections"][0]["tables"][0]["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    second = deepcopy(first)
    second.update({"page_json_version_id": "gfpstorev1:json:" + "f" * 64,
        "physical_page": 2, "selected_page_ordinal": 2})
    table = second["page_json"]["sections"][0]["tables"][0]
    table["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"
    table["title_exact"] = None
    table["unit_exact"] = None
    return [first, second]


def test_exact_raw_two_marker_continuation_has_unit_scope_without_reading_amounts():
    records = _continued_records()
    original = deepcopy(records)
    compiled = _adapter_compiled()
    inventory = family._original_source_unit_inventory_v2(records, compiled_specs=compiled)
    proof = inventory["tables"][-1]["source_owned_unit_proof"]
    assert proof is not None and proof["canonical_unit"] == "MILLION_VND"
    assert proof["receiver_period_shape"] == "EXACT_REPEATED_LOCAL_PERIOD_AXIS"
    assert proof["period_scope_or_source_value_permission_granted"] is False
    records[-1]["page_json"]["sections"][0]["tables"][0]["rows"][0]["values_exact"][-1] = "999999999"
    changed = family._original_source_unit_inventory_v2(records, compiled_specs=compiled)
    changed_proof = changed["tables"][-1]["source_owned_unit_proof"]
    assert changed_proof["canonical_unit"] == proof["canonical_unit"]
    assert original[1]["page_json"]["sections"][0]["tables"][0]["unit_exact"] is None
    # A unit predicate is not a financial READY/equation assertion.
    assert "mappings" not in inventory and "mappings" not in changed


@pytest.mark.parametrize("mutation", ["sender", "receiver", "physical", "selected", "source", "statement", "unit", "period"])
def test_raw_continuation_unit_scope_rejects_every_missing_identity_marker_owner_and_period(mutation):
    records = _continued_records()
    first = records[0]["page_json"]["sections"][0]["tables"][0]
    second = records[1]["page_json"]["sections"][0]["tables"][0]
    if mutation == "sender":
        first["continuation"] = "NONE"
    elif mutation == "receiver":
        second["continuation"] = "NONE"
    elif mutation == "physical":
        records[1]["physical_page"] += 1
    elif mutation == "selected":
        records[1]["selected_page_ordinal"] += 1
    elif mutation == "source":
        records[1]["source_sha256"] = "e" * 64
    elif mutation == "statement":
        records[1]["page_json"]["sections"][0]["statement_type"] = "CASH_FLOW"
    elif mutation == "unit":
        second["unit_exact"] = "USD"
    else:
        for column in second["columns"]:
            if column["value_kind"] == "MONEY":
                column["header_path_exact"] = ["Năm 2020"]
    original = deepcopy(records)
    inventory = family._original_source_unit_inventory_v2(records, compiled_specs=_adapter_compiled())
    assert inventory["tables"][-1]["source_owned_unit_proof"] is None
    assert records == original


@pytest.mark.parametrize("mutation", ["unit", "source", "envelope", "permission"])
def test_resealed_original_unit_evidence_cannot_substitute_for_fresh_raw_source_replay(mutation):
    candidate, options = _public(_primary_records(unit=None))
    assert candidate["status"] == family.UNRESOLVED and candidate["reasons"] == [REASON]
    forged = deepcopy(candidate)
    receipt = _control(forged)
    if mutation == "unit":
        receipt["checks"][0]["expected_units"] = ["MILLION_VND"]
    elif mutation == "source":
        receipt["checks"][0]["locator"]["source_sha256"] = "a" * 64
    elif mutation == "envelope":
        raw = b"{}\n"
        receipt["withheld_candidate_beforeimage"].update({
            "canonical_json": raw.decode(), "sha256": sha256(raw).hexdigest(), "size_bytes": len(raw)})
    else:
        receipt["document_consensus_equal_amount_or_private_unit_projection_permission"] = True
    receipt["receipt_id"] = "gjitunitv2:control:" + canonical_json_sha256_v1({
        key: value for key, value in receipt.items() if key != "receipt_id"})
    forged["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1({
        key: value for key, value in forged.items() if key != "candidate_id"})
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="candidate replay drifted"):
        family.validate_gemini_json_income_tax_family_candidate_replay_v1(forged, **options)


def test_an_existing_financial_hold_is_byte_exact_and_not_promoted_by_unit_control():
    candidate = {"status": family.UNRESOLVED, "reasons": ["EXISTING_SOURCE_OWNERSHIP_HOLD"],
        "mappings": [], "candidate_id": "existing"}
    original = canonical_json_bytes_v1(candidate)
    checked = family._enforce_original_source_units_v2(candidate, original_records=[], compiled_specs={})
    assert canonical_json_bytes_v1(checked) == original
