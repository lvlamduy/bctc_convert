"""Public query/trial binding controls; no financial permission is added."""

from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256

import pytest
from test_gemini_json_income_tax_family_v1 import _adapter_compiled
from test_gemini_json_income_tax_printed_dash_real_profiles_v1 import (
    METADATA_PATH,
    METADATA_SHA256,
    _source_record,
)
from test_gemini_json_income_tax_signed_display_v1 import _records

from bctc_ai.evaluation import gemini_json_income_tax_family_v1 as family
from bctc_ai.evaluation import gemini_json_multitable_hierarchical_family_v1 as shared
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    audit_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

HOLD_REASON = "ALGORITHM_PRINTED_PRIMARY_ROOT_SOURCE_OWNERSHIP_UNPROVEN"
HANDOFF = "income_tax_query_axis_handoff_receipt"


def _indexed_case(records):
    """Declare the complete bounded test axis and use every public stage."""
    compiled = _adapter_compiled()
    first = records[0]
    base = shared.coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled,
    )
    indexed = shared.build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=[{key: first[key] for key in (
            "document_id", "document_ordinal", "source_logical_name", "source_sha256",
        )}],
        selected_page_axis=[{key: value for key, value in record.items() if key != "page_json"}
                            for record in records],
        document_clusters=[base], query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]),
    )
    pages = {first["document_ordinal"]: {
        record["page_json_version_id"]: record["page_json"] for record in records
    }}
    adapted = family.adapt_gemini_json_income_tax_indexed_query_evidence_v1(
        indexed_query_evidence=indexed, page_json_by_document=pages, compiled_specs=compiled,
    )
    trials = family.build_gemini_json_income_tax_trials_v1(
        indexed_query_evidence=adapted, page_json_by_document=pages, compiled_specs=compiled,
    )
    # Invoke the ACTUAL frozen validator explicitly, as the streaming runner
    # does. Successful direct evaluation alone missed the original regression.
    assert shared.validate_gemini_json_multitable_hierarchical_sweep_query_bindings_v1(
        trials=trials, indexed_query_evidence=adapted, compiled_specs=compiled,
    ) == trials
    options = {
        "base_indexed_query_evidence": indexed, "indexed_query_evidence": adapted,
        "trials": trials, "page_json_by_document": pages, "compiled_specs": compiled,
    }
    assert family.validate_gemini_json_income_tax_replay_v1(**options) == trials
    return options


def _query_for(options):
    cluster = options["indexed_query_evidence"]["candidate_dispositions"][0]["cluster"]
    return cluster, family.build_gemini_json_income_tax_region_query_receipt_v1(
        cluster["component_regions"], cluster=cluster,
    )


def _primary(records, compiled):
    repaired, repairs, _ = family._prepare_income_tax_evaluation_records_v1(
        records, compiled_specs=compiled,
    )
    selected, reasons = family._select_primary_presentation(repaired, compiled_specs=compiled)
    assert selected is not None and not reasons
    candidate = family._evaluate_selected_primary(
        selected, repaired_pages={item["page_json_version_id"]: item["page_json"] for item in repaired},
        repair_receipts=repairs, compiled_specs=compiled,
    )
    return selected, candidate


def _handoff(candidate, query):
    receipt = candidate["closure_receipt"][HANDOFF]
    payload = receipt["authenticated_query_receipt"]["canonical_json"].encode("utf-8")
    assert payload == canonical_json_bytes_v1(query)
    assert receipt["authenticated_query_receipt"] == {
        "canonical_json": payload.decode("utf-8"), "sha256": sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    assert receipt["query_receipt_id"] == query["query_receipt_id"]
    assert receipt["accepted_component_regions"] == candidate["component_regions"] == query[
        "shared_query_receipt"
    ]["region_axis"]
    assert receipt["authority"] == "AUTHENTICATED_QUERY_CONTEXT_ONLY_NO_FINANCIAL_PERMISSION"
    assert receipt["status_reasons_mappings_and_source_evidence_unchanged"] is True
    assert receipt["receipt_id"] == "gjitfav1:query-axis-handoff:" + canonical_json_sha256_v1(
        {key: value for key, value in receipt.items() if key != "receipt_id"})
    assert candidate["candidate_id"] == "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in candidate.items() if key != "candidate_id"})
    assert audit_source_observation_mapping_contract_v1(receipt)["mapping_count"] == 0
    return receipt


def _held_records():
    records = _records()
    records[-1]["page_json"]["sections"][0]["tables"][0]["rows"][3]["values_exact"][-1] = None
    return records


def _before_public_handoff(records, compiled, query):
    """Recreate the existing financial route without the new context helper."""
    repaired, repairs, _ = family._prepare_income_tax_evaluation_records_v1(
        records, compiled_specs=compiled,
    )
    context = query["source_context_receipt"]
    bundle = family._build_original_note_adapter_bundle(
        repaired, compiled_specs=compiled, source_context=context, repair_receipts=repairs,
    )
    if bundle is not None:
        return family._evaluate_original_note_adapter(
            bundle, compiled_specs=compiled, repair_receipts=repairs,
            source_context=context, page_records=repaired,
        )
    selected, primary = _primary(records, compiled)
    assert query["adapter_receipt"]["strategy"] == "DIRECT_NOTE_PLUS_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION"
    note = shared.evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=query["shared_query_receipt"]["region_axis"],
        page_json_by_version={item["page_json_version_id"]: item["page_json"] for item in repaired},
        compiled_specs=compiled, query_receipt=query["shared_query_receipt"],
    )
    note = family._recognition_rate_source_only_projection(note, source_context=context)
    merged = family._merge_note_and_primary_candidates(
        note, primary, descriptor=selected["descriptor"], repair_receipts=repairs,
        compiled_specs=compiled, strategy=query["adapter_receipt"]["strategy"], page_records=repaired,
    )
    return family._seal_income_tax_source_controls(
        merged, source_context=context, repaired_records=repaired, compiled_specs=compiled,
    )


def test_actual_frozen_binding_preserves_note_axis_and_all_t6_private_hold_evidence():
    # The observed BAB20/EIB39 failure has this topology: accepted NOTE region
    # plus a separately selected PRIMARY whose printed total cannot be owned.
    records = _held_records()
    original = deepcopy(records)
    options = _indexed_case(records)
    cluster, query = _query_for(options)
    trial = options["trials"][0]
    result = trial["candidates"][0]
    selected, private = _primary(records, options["compiled_specs"])
    assert result["status"] == trial["status"] == shared.UNRESOLVED
    assert result["reasons"] == trial["reasons"] == [HOLD_REASON]
    assert result["mappings"] == trial["mappings"] == []
    assert trial["selected_candidate_id"] is None
    receipt = _handoff(result, query)
    assert receipt["axis_replaced"] is True
    assert receipt["component_regions_before"] == receipt["private_primary_component_regions"] == private[
        "component_regions"
    ] == selected["cluster"]["component_regions"]
    assert private["component_regions"] != cluster["component_regions"]
    assert receipt["prior_candidate_id"] == private["candidate_id"]
    assert {key: value for key, value in result["closure_receipt"].items() if key != HANDOFF} == private[
        "closure_receipt"
    ]
    assert result["closure_receipt"]["income_tax_unresolved_evidence_receipt"]["evidence"][
        "ownership_failure"
    ] == "PRINTED_TOTAL_SOURCE_MONEY_LANE_NOT_DIRECTLY_OBSERVED"
    audit = audit_source_observation_mapping_contract_v1(result)
    assert audit["status"] == "PASS" and audit["mapping_count"] == 0
    assert records == original


def test_ready_external_primary_printed_total_keeps_note_axis_and_existing_financial_proof():
    records = _records()
    original = deepcopy(records)
    options = _indexed_case(records)
    cluster, query = _query_for(options)
    result = options["trials"][0]["candidates"][0]
    assert result["status"] == shared.READY and result["reasons"] == []
    before = _before_public_handoff(records, options["compiled_specs"], query)
    assert canonical_json_bytes_v1(result) == canonical_json_bytes_v1(before)
    assert HANDOFF not in result["closure_receipt"]
    assert result["component_regions"] == cluster["component_regions"]
    root = next(item for item in result["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL")
    assert [value["coefficient"] for value in root["values"]] == [-22, -17]
    root_ref = root["source_refs"][0]
    assert root_ref["locator"]["page_json_version_id"] == records[-1]["page_json_version_id"]
    assert root_ref["row_ordinal"] == 4
    assert root_ref["locator"]["page_json_version_id"] not in {
        region["page_json_version_id"] for region in result["component_regions"]
    }
    adapter = result["closure_receipt"]["income_tax_adapter_receipt"]
    proof = adapter["primary_candidate_proof"]
    assert proof["signed_display_proof"]["source_values_changed"] is False
    assert proof["post_merge_root_closure"]["status"] == "EXACT_ALL_OBSERVED_LANES"
    assert records == original


def test_already_bound_public_note_ready_ignores_unused_unresolved_primary_metadata():
    options = _indexed_case([_records()[0]])
    _cluster, query = _query_for(options)
    note = options["trials"][0]["candidates"][0]
    assert note["status"] == shared.READY
    assert HANDOFF not in note["closure_receipt"]
    # No PRIMARY enters this note-only public query. Supplying an independently
    # selected but unresolved PRIMARY to the context helper cannot impose a
    # new permission check on an already authenticated candidate.
    selected, unsupported = _primary(_held_records(), options["compiled_specs"])
    assert unsupported["status"] == shared.UNRESOLVED and unsupported["reasons"] == [HOLD_REASON]
    result = family._retain_authenticated_note_query_axis_v1(
        note, query_receipt=query, selected_primary=selected,
    )
    assert canonical_json_bytes_v1(result) == canonical_json_bytes_v1(note)
    assert HANDOFF not in result["closure_receipt"]


@pytest.mark.parametrize("case,reason", [
    ("171:7:s1:t1:r19", "SOURCE_PRINTED_DASH_VS_JSON_NUMERIC_DISCREPANCY"),
    ("232:63:s2:t1:r4", "SOURCE_PRINTED_DASH_VS_JSON_NUMERIC_DISCREPANCY"),
])
def test_real_registered_primary_and_note_holds_reach_actual_frozen_binding(case, reason):
    raw = METADATA_PATH.read_bytes()
    assert sha256(raw).hexdigest() == METADATA_SHA256 and len(raw) == 52757
    profile = next(item for item in json.loads(raw)["cases"] if item["case"] == case)
    record = _source_record(profile)
    # This bounded one-page test has a newly declared dense manifest. Original
    # DID/name/SHA/VID/physical page and every raw source cell remain exact.
    record.update(document_ordinal=1, selected_page_ordinal=1)
    original = deepcopy(record)
    options = _indexed_case([record])
    cluster, _query = _query_for(options)
    trial = options["trials"][0]
    result = trial["candidates"][0]
    assert result["status"] == trial["status"] == shared.UNRESOLVED
    assert result["reasons"] == trial["reasons"] == [reason]
    assert result["mappings"] == trial["mappings"] == []
    assert result["component_regions"] == cluster["component_regions"]
    assert trial["selected_candidate_id"] is None
    audit = audit_source_observation_mapping_contract_v1(result)
    assert audit["status"] == "PASS"
    if reason == "SOURCE_PRINTED_DASH_VS_JSON_NUMERIC_DISCREPANCY":
        # Each existing T7a negative observation retains its rejected
        # selected_mapping as evidence. The recursive audit counts those images;
        # the query-context-only change must preserve it, not invent an active
        # mapping or silently change the older financial receipt format.
        observations = result["closure_receipt"]["income_tax_unresolved_evidence_receipt"][
            "evidence"
        ]["registered_negative_source_label_observations"]
        assert observations
        assert all(item["classification"] == "PRINTED_DASH_VS_JSON_NUMERIC" for item in observations)
        assert all(item["selected_source_ref"]["row_ordinal"]
                   == profile["citing_mappings"][0]["source_ref"]["row_ordinal"] for item in observations)
        archived = [item["selected_mapping"] for item in observations]
        assert audit_source_observation_mapping_contract_v1(archived)["mapping_count"] == len(archived)
        assert audit["mapping_count"] == len(archived)
        assert audit == audit_source_observation_mapping_contract_v1(observations)
    else:
        assert audit["mapping_count"] == 0
    assert record == original


@pytest.mark.parametrize("mutation", ["axis", "status", "mappings", "reason", "source_locator", "source_sha"])
def test_handoff_rejects_arbitrary_drift_or_non_t6_permission(mutation):
    records = _held_records()
    options = _indexed_case(records)
    _cluster, query = _query_for(options)
    selected, private = _primary(records, options["compiled_specs"])
    changed = deepcopy(private)
    if mutation == "axis":
        changed["component_regions"][0]["table_id"] = "t9"
    elif mutation == "status":
        changed["status"] = shared.READY
    elif mutation == "mappings":
        changed["mappings"] = [{"role": "FAMILY_ROOT_TOTAL"}]
    elif mutation == "reason":
        changed["reasons"] = ["UNRELATED_HOLD"]
    elif mutation == "source_locator":
        changed["closure_receipt"]["income_tax_unresolved_evidence_receipt"]["evidence"]["locator"]["table_id"] = "t9"
    else:
        changed["closure_receipt"]["income_tax_unresolved_evidence_receipt"]["evidence"]["original_page_json_sha256"] = "0" * 64
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="authenticated T6 HOLD handoff"):
        family._retain_authenticated_note_query_axis_v1(
            changed, query_receipt=query, selected_primary=selected,
        )


@pytest.mark.parametrize("field", ["private_primary_component_regions", "authenticated_query_receipt"])
def test_self_resealed_context_handoff_tamper_fails_fresh_public_trial_replay(field):
    options = _indexed_case(_held_records())
    changed = deepcopy(options["trials"])
    candidate = changed[0]["candidates"][0]
    receipt = candidate["closure_receipt"][HANDOFF]
    if field == "private_primary_component_regions":
        receipt[field][0]["table_id"] = "t9"
    else:
        payload = canonical_json_bytes_v1({"forged": True})
        receipt[field] = {"canonical_json": payload.decode("utf-8"),
                          "sha256": sha256(payload).hexdigest(), "size_bytes": len(payload)}
    receipt["receipt_id"] = "gjitfav1:query-axis-handoff:" + canonical_json_sha256_v1(
        {key: value for key, value in receipt.items() if key != "receipt_id"})
    candidate["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in candidate.items() if key != "candidate_id"})
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="trial replay drifted"):
        family.validate_gemini_json_income_tax_replay_v1(**{**options, "trials": changed})
