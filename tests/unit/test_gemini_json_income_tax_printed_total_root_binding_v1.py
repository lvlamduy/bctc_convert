"""T6 synthetic source-role controls; no real filing amounts are fixtures."""

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
    _row,
)

from bctc_ai.evaluation import gemini_json_income_tax_family_v1 as family
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    audit_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

REASON = "ALGORITHM_PRINTED_PRIMARY_ROOT_SOURCE_OWNERSHIP_UNPROVEN"


def _decode_mapping_evidence(evidence):
    assert evidence["format_version"] == "INCOME_TAX_PRINTED_PRIMARY_ROOT_MAPPING_EVIDENCE_V1"
    payload = evidence["canonical_json"].encode("utf-8")
    assert evidence["size_bytes"] == len(payload)
    assert evidence["sha256"] == sha256(payload).hexdigest()
    value = json.loads(payload)
    assert canonical_json_bytes_v1(value) == payload
    return value


def _before_binding(page):
    """Use the actual private projection/evaluator, not a fabricated READY enum."""
    compiled = _adapter_compiled()
    record = _primary_record(page)
    selected, reasons = family._select_primary_presentation([record], compiled_specs=compiled)
    assert selected is not None and not reasons
    descriptor = selected["descriptor"]
    projected = family._project_primary_page(page, descriptor=descriptor)
    regions = selected["cluster"]["component_regions"]
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=regions,
        page_json_by_version={record["page_json_version_id"]: projected},
        compiled_specs=compiled[descriptor["projected_specs_key"]],
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions),
    )
    assert candidate["status"] == READY, candidate.get("reasons")
    candidate = family._reseal_candidate(
        candidate, descriptor=descriptor, repair_receipts=[],
        strategy="DIRECT_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION", compiled_specs=compiled,
    )
    return compiled, descriptor, candidate


def _bind(page):
    compiled, descriptor, before = _before_binding(page)
    after = family._bind_printed_primary_root_v1(
        before, source_page=page, descriptor=descriptor, compiled_specs=compiled,
    )
    return before, after


def _by_role(candidate, role):
    return next(item for item in candidate["mappings"] if item["role"] == role)


def _public(page):
    compiled = _adapter_compiled()
    record = _primary_record(page)
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[record], compiled_specs=compiled,
    )
    cluster = family.recover_gemini_json_income_tax_query_cluster_v1(
        page_records=[record], base_cluster=base, compiled_specs=compiled,
    )
    if cluster["status"] != READY:
        return cluster
    return family.evaluate_gemini_json_income_tax_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={record["page_json_version_id"]: page},
        selected_page_axis=[{key: value for key, value in record.items() if key != "page_json"}],
        compiled_specs=compiled,
        query_receipt=family.build_gemini_json_income_tax_region_query_receipt_v1(
            cluster["component_regions"], cluster=cluster,
        ),
    )


@pytest.mark.parametrize("root_label", [
    "Chi phí thuế TNDN", "XII. Chi phí thuế TNDN", "Tổng chi phí thuế TNDN",
])
def test_printed_total_role_owns_root_even_when_current_has_equal_amounts(root_label):
    rows = _primary_tax_rows(current=("10", "20"), deferred=("-", "-"), root=("10", "20"))
    rows[2]["label_exact"] = root_label
    rows[2]["hierarchy_path_exact"] = [root_label]
    page = _primary_page(rows)
    original = deepcopy(page)
    before, after = _bind(page)
    assert after["status"] == READY
    root = _by_role(after, "FAMILY_ROOT_TOTAL")
    assert root["source_refs"][0]["row_ordinal"] == 3
    assert root["source_refs"][0]["label_exact"] == root_label
    assert root["source_refs"][0]["money_column_ordinals"] == [3, 4]
    assert root["state"] == "SOURCE_VISIBLE_PRINTED_PRIMARY_FAMILY_ROOT_TOTAL"
    assert _by_role(after, "CURRENT_TAX_PARENT") == _by_role(before, "CURRENT_TAX_PARENT")
    assert _by_role(after, "DEFERRED_TAX_NET") == _by_role(before, "DEFERRED_TAX_NET")
    assert page == original


def test_public_family_path_uses_actual_total_with_nonzero_deferred_tax():
    page = _primary_page(_primary_tax_rows())
    result = _public(page)
    assert result["status"] == READY, result.get("reasons")
    root = _by_role(result, "FAMILY_ROOT_TOTAL")
    current = _by_role(result, "CURRENT_TAX_PARENT")
    assert [cell["coefficient"] for cell in root["values"]] == [40, 60]
    assert root["source_refs"][0]["row_ordinal"] == 3
    assert [cell["coefficient"] for cell in current["values"]] == [10, 20]
    assert current["source_refs"][0]["row_ordinal"] == 1


def test_current_tax_frontier_root_is_replaced_by_actual_printed_total_citation():
    page = _primary_page(_primary_tax_rows(current=("10", "20"), deferred=("-", "-"), root=("10", "20")))
    compiled, descriptor, candidate = _before_binding(page)
    current = deepcopy(_by_role(candidate, "CURRENT_TAX_PARENT"))
    root = _by_role(candidate, "FAMILY_ROOT_TOTAL")
    root["source_refs"] = deepcopy(current["source_refs"])
    root["row_id"] = current["row_id"]
    root["values"] = deepcopy(current["values"])
    root["state"] = "SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_BY_DIRECT_FRONTIER"
    root["item_mapping_id"] = "gjmthfmv1:item:" + canonical_json_sha256_v1(
        {key: value for key, value in root.items() if key != "item_mapping_id"})
    candidate["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in candidate.items() if key != "candidate_id"})
    result = family._bind_printed_primary_root_v1(
        candidate, source_page=page, descriptor=descriptor, compiled_specs=compiled,
    )
    assert _by_role(result, "FAMILY_ROOT_TOTAL")["source_refs"][0]["row_ordinal"] == 3
    assert _by_role(result, "CURRENT_TAX_PARENT") == current


@pytest.mark.parametrize("raw", ["(10)", "-10", "0", "-", "1.234.567.890.123.456.789"])
def test_binding_preserves_actual_total_raw_sign_dash_zero_and_integer_precision(raw):
    rows = _primary_tax_rows(current=(raw, raw), deferred=("-", "-"), root=(raw, raw))
    _, after = _bind(_primary_page(rows))
    root = _by_role(after, "FAMILY_ROOT_TOTAL")
    expected = family._source_money(raw)
    assert root["values"] == [expected, expected]
    assert [cell["source_text"] for cell in root["values"]] == [raw, raw]


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_present_blank_total_is_hold_never_replaced_with_current_tax(raw):
    rows = _primary_tax_rows(current=("10", "20"), deferred=("-", "-"), root=(raw, raw))
    before, result = _bind(_primary_page(rows))
    assert result["status"] == UNRESOLVED
    assert result["reasons"] == [REASON]
    assert result["mappings"] == []
    evidence = result["closure_receipt"]["income_tax_unresolved_evidence_receipt"]["evidence"]
    assert evidence["source_values_exact"] == [raw, raw]
    assert _decode_mapping_evidence(evidence["prior_root_mappings"]) == [
        item for item in before["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL"
    ]
    assert "bound_root_mapping" not in evidence


def test_binding_receipt_and_candidate_ids_authenticate_changed_mapping():
    before, result = _bind(_primary_page(_primary_tax_rows()))
    receipt = result["closure_receipt"]["income_tax_printed_primary_root_receipt"]
    material = {key: value for key, value in receipt.items() if key != "receipt_id"}
    assert receipt["receipt_id"] == "gjitfav1:printed-primary-root:" + canonical_json_sha256_v1(material)
    mapping = _by_role(result, "FAMILY_ROOT_TOTAL")
    assert mapping["item_mapping_id"] == "gjmthfmv1:item:" + canonical_json_sha256_v1(
        {key: value for key, value in mapping.items() if key != "item_mapping_id"})
    assert result["candidate_id"] == "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in result.items() if key != "candidate_id"})
    assert receipt["amounts_used_as_role_authority"] is False
    assert receipt["source_values_changed"] is False
    assert receipt["final_document_period_source_control_still_required"] is True
    assert _decode_mapping_evidence(receipt["prior_root_mappings"]) == [
        item for item in before["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL"
    ]
    assert _decode_mapping_evidence(receipt["bound_root_mapping"]) == mapping


@pytest.mark.parametrize("field,bad", [
    ("document_id", "d" * 64), ("document_ordinal", 2),
    ("page_json_version_id", "e" * 64), ("section_id", "s2"), ("table_id", "t2"),
])
def test_component_from_other_document_page_or_table_cannot_borrow_printed_total(field, bad):
    page = _primary_page(_primary_tax_rows())
    compiled, descriptor, candidate = _before_binding(page)
    current = _by_role(candidate, "CURRENT_TAX_PARENT")
    current["source_refs"][0]["locator"][field] = bad
    # This adverse candidate is resealed, so the negative is source ownership,
    # not an incidental stale candidate identifier.
    current["item_mapping_id"] = "gjmthfmv1:item:" + canonical_json_sha256_v1(
        {key: value for key, value in current.items() if key != "item_mapping_id"})
    candidate["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in candidate.items() if key != "candidate_id"})
    result = family._bind_printed_primary_root_v1(
        candidate, source_page=page, descriptor=descriptor, compiled_specs=compiled,
    )
    assert result["status"] == UNRESOLVED
    assert result["reasons"] == [REASON]


def test_different_printed_population_cannot_own_root():
    page = _primary_page(_primary_tax_rows())
    page["sections"][0]["tables"][0]["rows"][2]["hierarchy_path_exact"].insert(0, "Ngân hàng mẹ")
    _, result = _bind(page)
    assert result["status"] == UNRESOLVED
    assert result["reasons"] == [REASON]


def test_intervening_group_prevents_flat_path_cross_population_borrowing():
    rows = _primary_tax_rows()
    rows.insert(2, {**_row("Đơn vị khác", None, None, kind="GROUP"), "values_exact": [None] * 4})
    _, result = _bind(_primary_page(rows))
    assert result["status"] == UNRESOLVED
    assert result["reasons"] == [REASON]


def test_source_hash_drift_raises_instead_of_rebinding_a_different_table():
    page = _primary_page(_primary_tax_rows())
    compiled, descriptor, candidate = _before_binding(page)
    page["sections"][0]["tables"][0]["rows"][2]["values_exact"][2] = "41"
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="source identity drifted"):
        family._bind_printed_primary_root_v1(
            candidate, source_page=page, descriptor=descriptor, compiled_specs=compiled,
        )


def test_public_replay_rejects_changed_printed_period_with_old_query_authority():
    compiled = _adapter_compiled()
    page = _primary_page(_primary_tax_rows())
    record = _primary_record(page)
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[record], compiled_specs=compiled,
    )
    cluster = family.recover_gemini_json_income_tax_query_cluster_v1(
        page_records=[record], base_cluster=base, compiled_specs=compiled,
    )
    assert cluster["status"] == READY
    query = family.build_gemini_json_income_tax_region_query_receipt_v1(
        cluster["component_regions"], cluster=cluster,
    )
    changed = deepcopy(page)
    changed["sections"][0]["tables"][0]["columns"][2]["header_path_exact"][-1] = "Năm 2027"
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="drifted"):
        family.evaluate_gemini_json_income_tax_family_cluster_v1(
            regions=cluster["component_regions"],
            page_json_by_version={record["page_json_version_id"]: changed},
            selected_page_axis=[{key: value for key, value in record.items() if key != "page_json"}],
            compiled_specs=compiled, query_receipt=query,
        )


@pytest.mark.parametrize("field,value", [
    ("money_column_ordinals", [1, 2]), ("canonical_unit", "VND"),
])
def test_incomplete_lane_or_unit_ownership_cannot_bind_total(field, value):
    page = _primary_page(_primary_tax_rows())
    compiled, descriptor, candidate = _before_binding(page)
    descriptor[field] = value
    result = family._bind_printed_primary_root_v1(
        candidate, source_page=page, descriptor=descriptor, compiled_specs=compiled,
    )
    assert result["status"] == UNRESOLVED
    assert result["reasons"] == [REASON]


def test_unresolved_candidate_is_never_promoted_by_a_printed_total():
    page = _primary_page(_primary_tax_rows())
    compiled, descriptor, candidate = _before_binding(page)
    candidate = family._unresolved_from_candidate(candidate, reason="SYNTHETIC_PREEXISTING_HOLD")
    assert family._bind_printed_primary_root_v1(
        candidate, source_page=page, descriptor=descriptor, compiled_specs=compiled,
    ) == candidate


def test_duplicate_total_does_not_receive_public_ready_acceptance():
    rows = _primary_tax_rows()
    rows.append(deepcopy(rows[2]))
    assert _public(_primary_page(rows))["status"] != READY


def test_no_printed_total_does_not_acquire_new_printed_total_authority():
    # The existing structural-only private path may be READY without a root;
    # it remains governed by its existing frontier and final source controls.
    page = _primary_page(_primary_tax_rows()[:2])
    before, after = _bind(page)
    assert after == before
    assert "income_tax_printed_primary_root_receipt" not in after["closure_receipt"]


def test_typed_printed_total_hold_cannot_be_resurrected_by_note_or_supplement_merge():
    _, candidate = _bind(_primary_page(_primary_tax_rows(root=(None, None))))
    assert candidate["status"] == UNRESOLVED
    assert family._merge_supplemental_and_primary_candidates(
        [], candidate, descriptor={}, repair_receipts=[], compiled_specs={},
    ) == candidate
    assert family._merge_note_and_primary_candidates(
        {"status": READY}, candidate, descriptor={}, repair_receipts=[], compiled_specs={},
        strategy="SYNTHETIC_UNUSED_AFTER_TYPED_HOLD", page_records=[],
    ) == candidate


def _preceding_legacy_root_group_page():
    rows = _primary_tax_rows()
    root = rows.pop()
    root["row_kind"] = "GROUP"
    for row in rows:
        row["hierarchy_path_exact"] = [root["label_exact"], row["label_exact"]]
    return _primary_page([root, *rows])


def test_actual_preceding_legacy_tax_group_can_own_its_observed_printed_total():
    page = _preceding_legacy_root_group_page()
    original = deepcopy(page)
    before, after = _bind(page)
    assert after["status"] == READY
    root = _by_role(after, "FAMILY_ROOT_TOTAL")
    assert root["source_refs"][0]["row_ordinal"] == 1
    assert root["source_refs"][0]["row_kind"] == "GROUP"
    assert [cell["source_text"] for cell in root["values"]] == ["40", "60"]
    proof = after["closure_receipt"]["income_tax_printed_primary_root_receipt"]["same_printed_population_receipt"]
    assert proof["common_population_ancestry_exact"] == []
    assert proof["structural_tax_group_sources"] == [{
        "row_ordinal": 1, "source_row": original["sections"][0]["tables"][0]["rows"][0],
    }]
    assert _by_role(after, "CURRENT_TAX_PARENT") == _by_role(before, "CURRENT_TAX_PARENT")
    assert _by_role(after, "DEFERRED_TAX_NET") == _by_role(before, "DEFERRED_TAX_NET")
    assert page == original


@pytest.mark.parametrize("mutation", [
    "later_group", "quoted_group", "different_population", "unqualified_component", "unknown_total",
])
def test_root_group_label_cannot_bypass_actual_owner_order_population_or_observed_cells(mutation):
    page = _preceding_legacy_root_group_page()
    rows = page["sections"][0]["tables"][0]["rows"]
    if mutation == "later_group":
        rows.append(rows.pop(0))
    elif mutation == "quoted_group":
        old = rows[0]["label_exact"]
        quoted = 'Chi phí thuế thu nhập doanh nghiệp ("TNDN")'
        rows[0].update(label_exact=quoted, hierarchy_path_exact=[quoted])
        for row in rows[1:]:
            assert row["hierarchy_path_exact"][0] == old
            row["hierarchy_path_exact"][0] = quoted
    elif mutation == "different_population":
        rows[1]["hierarchy_path_exact"].insert(0, "Công ty con")
    elif mutation == "unqualified_component":
        rows[1]["hierarchy_path_exact"] = [rows[1]["label_exact"]]
    else:
        rows[0]["values_exact"][-1] = None
    original = deepcopy(page)
    _, after = _bind(page)
    assert after["status"] == UNRESOLVED and after["mappings"] == []
    assert after["reasons"] == [REASON]
    assert page == original


def test_valid_signed_note_cannot_rescue_an_unknown_printed_primary_total():
    from test_gemini_json_income_tax_signed_display_v1 import _candidate, _records

    records = _records()
    root = records[-1]["page_json"]["sections"][0]["tables"][0]["rows"][3]
    root["values_exact"][-1] = None
    original = deepcopy(records)
    after = _candidate(records)
    assert after["status"] == UNRESOLVED and after["mappings"] == []
    assert after["reasons"] == [REASON]
    assert records == original


def _assert_real_binder_candidate_audit(page, *, held):
    before, result = _bind(page)
    assert result["status"] == (UNRESOLVED if held else READY)
    audit = audit_source_observation_mapping_contract_v1(result)
    assert audit["status"] == "PASS", audit["violations"]
    assert audit["mapping_count"] == len(result["mappings"]) == (0 if held else 3)
    evidence = (
        result["closure_receipt"]["income_tax_unresolved_evidence_receipt"]["evidence"]
        if held else result["closure_receipt"]["income_tax_printed_primary_root_receipt"]
    )
    assert audit_source_observation_mapping_contract_v1(evidence)["mapping_count"] == 0
    assert _decode_mapping_evidence(evidence["prior_root_mappings"]) == [
        item for item in before["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL"
    ]
    if held:
        assert "bound_root_mapping" not in evidence
    else:
        assert _decode_mapping_evidence(evidence["bound_root_mapping"]) == _by_role(
            result, "FAMILY_ROOT_TOTAL",
        )


@pytest.mark.parametrize("held", [False, True])
def test_normal_public_audit_identifies_legacy_post_merge_images_and_no_new_t6_mappings(held):
    page = _primary_page(_primary_tax_rows(root=(None, None) if held else ("40", "60")))
    original = deepcopy(page)
    _assert_real_binder_candidate_audit(page, held=held)
    result = _public(page)
    assert result["status"] == (UNRESOLVED if held else READY)
    audit = audit_source_observation_mapping_contract_v1(result)
    assert audit["status"] == "PASS", audit["violations"]
    if held:
        assert audit["mapping_count"] == len(result["mappings"]) == 0
        evidence = result["closure_receipt"]["income_tax_unresolved_evidence_receipt"]["evidence"]
        assert evidence["source_values_exact"] == [None, None]
        assert "bound_root_mapping" not in evidence
        assert type(_decode_mapping_evidence(evidence["prior_root_mappings"])) is list
    else:
        evidence = result["closure_receipt"]["income_tax_printed_primary_root_receipt"]
        legacy = result["closure_receipt"]["income_tax_source_control_receipt"][
            "post_merge_root_closure"
        ]["mappings"]
        assert legacy == [_by_role(result, role) for role in (
            "CURRENT_TAX_PARENT", "DEFERRED_TAX_NET", "FAMILY_ROOT_TOTAL",
        )]
        assert len(legacy) == len(result["mappings"]) == 3
        # The unchanged public route retains these three legacy evidence
        # images. Audit the unmodified whole candidate and identify them
        # explicitly; the new T6 receipt contributes no mapping objects.
        assert audit["mapping_count"] == len(result["mappings"]) + len(legacy) == 6
        assert _decode_mapping_evidence(evidence["bound_root_mapping"]) == _by_role(
            result, "FAMILY_ROOT_TOTAL",
        )
    assert audit_source_observation_mapping_contract_v1(evidence)["mapping_count"] == 0
    assert page == original


def _indexed_replay_case(*, held):
    compiled = _adapter_compiled()
    page = _primary_page(_primary_tax_rows(root=(None, None) if held else ("40", "60")))
    # This is a newly declared one-page test manifest, so its selected axis
    # starts at one. Physical page and all original source fields stay exact.
    record = _primary_record(page, selected_page_ordinal=1)
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[record], compiled_specs=compiled,
    )
    indexed = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=[{key: record[key] for key in (
            "document_id", "document_ordinal", "source_logical_name", "source_sha256",
        )}],
        selected_page_axis=[{key: value for key, value in record.items() if key != "page_json"}],
        document_clusters=[base], query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]),
    )
    pages = {record["document_ordinal"]: {record["page_json_version_id"]: page}}
    adapted = family.adapt_gemini_json_income_tax_indexed_query_evidence_v1(
        indexed_query_evidence=indexed, page_json_by_document=pages, compiled_specs=compiled,
    )
    trials = family.build_gemini_json_income_tax_trials_v1(
        indexed_query_evidence=adapted, page_json_by_document=pages, compiled_specs=compiled,
    )
    return {
        "base_indexed_query_evidence": indexed, "indexed_query_evidence": adapted,
        "trials": trials, "page_json_by_document": pages, "compiled_specs": compiled,
    }


@pytest.mark.parametrize("held,field", [
    (False, "prior_root_mappings"), (False, "bound_root_mapping"), (True, "prior_root_mappings"),
])
def test_resealed_mapping_evidence_tamper_is_rejected_by_actual_fresh_trial_replay(held, field):
    options = _indexed_replay_case(held=held)
    assert family.validate_gemini_json_income_tax_replay_v1(**options) == options["trials"]
    changed = deepcopy(options["trials"])
    candidate = changed[0]["candidates"][0]
    assert candidate["status"] == (UNRESOLVED if held else READY)
    receipt_key = "income_tax_unresolved_evidence_receipt" if held else "income_tax_printed_primary_root_receipt"
    receipt = candidate["closure_receipt"][receipt_key]
    material = receipt["evidence"] if held else receipt
    # Give the forged envelope valid canonical bytes, SHA, size and surrounding
    # IDs. Fresh source replay, rather than a stale hash, must reject it.
    payload = canonical_json_bytes_v1(None)
    material[field].update(canonical_json=payload.decode("utf-8"),
                           sha256=sha256(payload).hexdigest(), size_bytes=len(payload))
    prefix = "gjitfav1:unresolved:" if held else "gjitfav1:printed-primary-root:"
    receipt["receipt_id"] = prefix + canonical_json_sha256_v1(
        {key: value for key, value in receipt.items() if key != "receipt_id"})
    candidate["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in candidate.items() if key != "candidate_id"})
    if not held:
        changed[0]["selected_candidate_id"] = candidate["candidate_id"]
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="trial replay drifted"):
        family.validate_gemini_json_income_tax_replay_v1(**{**options, "trials": changed})
