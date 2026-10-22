"""Public F39 competing-taxable-stage regression tests.

Uses actual project/public APIs and existing unit fixtures, not AST stand-ins.
No source-authentication or PDF approval is mocked. Expected carrier READY is
asserted so a fixture cannot silently pass by failing before the proposed gate.
"""
from __future__ import annotations

from copy import deepcopy

import pytest
from test_gemini_json_income_tax_family_v1 import _adapter_compiled, _row
from test_gemini_json_income_tax_root_controls_v1 import _evaluate_query
from test_gemini_json_income_tax_signed_display_v1 import _records
from test_gemini_json_income_tax_source_context_v1 import _reseal

from bctc_ai.evaluation import gemini_json_income_tax_family_v1 as family
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

REASON = "ALGORITHM_TAXABLE_INCOME_STAGE_BASIS_AMBIGUITY"


def _stage_records(mode="merged", *, adjustment=("(10)", "(5)")):
    records = _records()
    table = records[0]["page_json"]["sections"][0]["tables"][0]
    first = _row("Tổng thu nhập chịu thuế", "100", "80", kind="SUBTOTAL")
    exempt = _row("Thu nhập miễn thuế (lợi nhuận năm trước công ty con chuyển)", *adjustment)
    later = _row("Thu nhập tính thuế", "90", "75", kind="SUBTOTAL")
    prefix = [_row("Lợi nhuận kế toán trước thuế", "100", "80"), first, exempt, later]
    if mode == "primary_fallback":
        # Missing roles alone are allowed by QUERY_EVIDENCE_ONLY. An explicit
        # unreadable numeric token makes the real NOTE evaluator reject it.
        first["values_exact"][0] = "SOURCE_ILLEGIBLE"
        table["rows"] = [first, exempt, later]
    elif mode == "ownerless_required_roles":
        section = records[0]["page_json"]["sections"][0]
        section["title_exact"] = None
        table["title_exact"] = None
        table["rows"] = prefix
        records = records[:1]
    else:
        table["rows"] = prefix + table["rows"]
        if mode == "note_only":
            records = records[:1]
    return records


def _public_query(records, compiled, *, fallback=False):
    if fallback:
        rejected_note = coalesce_gemini_json_multitable_hierarchical_document_v1(
            page_records=records[:1], compiled_specs=compiled)
        # Query ownership/readiness is not final mapping usability. Prove the
        # NOTE is unusable by executing the unchanged shared evaluator first.
        assert rejected_note["status"] == READY, rejected_note["reasons"]
        rejected_note_candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
            regions=rejected_note["component_regions"],
            page_json_by_version={record["page_json_version_id"]: record["page_json"] for record in records[:1]},
            compiled_specs=compiled,
            query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
                rejected_note["component_regions"]),
        )
        assert rejected_note_candidate["status"] == UNRESOLVED, rejected_note_candidate
        assert rejected_note_candidate["mappings"] == []
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled)
    cluster = family.recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled)
    assert cluster["status"] == READY, cluster["reasons"]
    query = family.build_gemini_json_income_tax_region_query_receipt_v1(cluster["component_regions"], cluster=cluster)
    if fallback:
        assert query["adapter_receipt"]["strategy"] == "DIRECT_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION"
    return cluster, query


def _assert_hold(records, compiled, cluster, query):
    candidate = _evaluate_query(records, compiled, cluster, query)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["reasons"] == [REASON]
    evidence = candidate["closure_receipt"]["income_tax_unresolved_evidence_receipt"]["evidence"]
    populations = evidence["competing_taxable_stage_populations"]
    assert len(populations) == 1
    control = populations[0]["competing_taxable_stage_control"]
    assert control["status"] == "ALGORITHM_HOLD"
    assert control["independent_schema_basis_ownership_proven"] is False
    assert control["amounts_used_as_authority"] is False
    assert control["source_values_changed"] is False
    source_rows = records[0]["page_json"]["sections"][0]["tables"][0]["rows"]
    assert populations[0]["source_table_rows_exact"] == source_rows
    for pair in control["competing_stage_pairs"]:
        for source in pair["stage_source_rows_exact"]:
            assert source["source_row_exact"] == source_rows[source["row_ordinal"] - 1]
    assert control["competing_stage_pairs"][0]["row_ordinals_are_input_table_ordinals"] is True
    return candidate


@pytest.mark.parametrize("mode", ["note_only", "merged", "primary_fallback", "ownerless_required_roles"])
@pytest.mark.parametrize("enabled", [False, True])
def test_competing_taxable_bases_cannot_export_via_note_merge_or_primary_fallback(mode, enabled):
    records = _stage_records(mode)
    original = deepcopy(records)
    compiled = _adapter_compiled()
    with family.income_tax_document_period_evaluation_scope_v1(enabled=enabled):
        cluster, query = _public_query(records, compiled, fallback=mode == "primary_fallback")
        _assert_hold(records, compiled, cluster, query)
    assert records == original


@pytest.mark.parametrize("adjustment", [(None, None), ("-", "-")])
def test_blank_or_dash_exemption_never_proves_basis_identity_or_creates_values(adjustment):
    records = _stage_records(adjustment=adjustment)
    table = records[0]["page_json"]["sections"][0]["tables"][0]
    table["rows"][3]["values_exact"] = deepcopy(table["rows"][1]["values_exact"])
    before = deepcopy(records)
    compiled = _adapter_compiled()
    cluster, query = _public_query(records, compiled)
    _assert_hold(records, compiled, cluster, query)
    assert records == before
    assert table["rows"][2]["values_exact"] == list(adjustment)


@pytest.mark.parametrize("mutation", ["remove_control", "remove_population", "self_reseal_pass", "change_row_axis"])
def test_fully_resealed_control_or_inventory_cannot_replace_fresh_original_source(mutation):
    records = _stage_records()
    compiled = _adapter_compiled()
    cluster, query = _public_query(records, compiled)
    forged = deepcopy(query)
    inventory = forged["source_context_receipt"]["tax_population_inventory"]
    assert len(inventory) == 1
    control = inventory[0]["competing_taxable_stage_control"]
    if mutation == "remove_control":
        del inventory[0]["competing_taxable_stage_control"]
    elif mutation == "remove_population":
        inventory.clear()
    else:
        if mutation == "self_reseal_pass":
            control["status"] = "PASS"
            control["competing_stage_pairs"] = []
            control["independent_schema_basis_ownership_proven"] = True
        else:
            control["competing_stage_pairs"][0]["later_taxable_row_ordinal"] = 999
        control["receipt_id"] = "gjitfav1:competing-taxable-stages:" + canonical_json_sha256_v1(
            {key: value for key, value in control.items() if key != "receipt_id"})
    _reseal(forged)
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="source context query replay drifted"):
        _evaluate_query(records, compiled, cluster, forged)


def test_same_id_source_value_mutation_invalidates_old_context_even_if_veto_shape_unchanged():
    records = _stage_records()
    compiled = _adapter_compiled()
    cluster, query = _public_query(records, compiled)
    changed = deepcopy(records)
    changed[0]["page_json"]["sections"][0]["tables"][0]["rows"][2]["values_exact"][0] = "(11)"
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="source context query replay drifted"):
        _evaluate_query(changed, compiled, cluster, query)


def test_enabled_and_independent_disabled_public_results_are_exact():
    records = _stage_records()
    compiled = _adapter_compiled()
    results = []
    for enabled in (True, False):
        with family.income_tax_document_period_evaluation_scope_v1(enabled=enabled):
            cluster, query = _public_query(records, compiled)
            results.append(_assert_hold(records, compiled, cluster, query))
    assert results[0] == results[1]


def test_adjacent_equal_bases_are_not_this_veto_and_not_a_new_basis_approval():
    records = _stage_records()
    table = records[0]["page_json"]["sections"][0]["tables"][0]
    del table["rows"][2]
    table["rows"][2]["values_exact"] = deepcopy(table["rows"][1]["values_exact"])
    result = family._competing_taxable_stage_control_v1(
        records[0]["page_json"]["sections"][0], table, compiled_specs=_adapter_compiled())
    assert result["status"] == "NOT_APPLICABLE"
    assert "source_table_json_sha256" not in result
    assert "columns_exact" not in result
    assert "source_rows_exact" not in result
    assert result["independent_schema_basis_ownership_proven"] is False
    assert result["scope_unit_period_or_mapping_permission_granted"] is False
