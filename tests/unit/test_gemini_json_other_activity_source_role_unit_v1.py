"""UNRUN F38 source-role/unit controls; every source page here is synthetic."""
from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256

import pytest
from test_gemini_json_other_activity_family_v1 import (
    OWNER,
    _compiled,
    _gross_rows,
    _page,
    _record,
    _repaired_continuation_case,
    _row,
)

from bctc_ai.evaluation import gemini_json_other_activity_family_v1 as family
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    GeminiJsonMultitableHierarchicalFamilyV1Error,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    validate_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _public_candidate(pages, *, compiled=None):
    compiled = _compiled() if compiled is None else compiled
    records = [_record(page, ordinal=ordinal) for ordinal, page in enumerate(pages, 1)]
    source = {record["page_json_version_id"]: record["page_json"] for record in records}
    before = deepcopy(source)
    base = family.coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled)
    cluster = family.recover_gemini_json_other_activity_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled)
    assert cluster["status"] == family.READY
    options = {"regions": cluster["component_regions"], "page_json_by_version": source,
        "compiled_specs": compiled, "query_receipt": family.build_gemini_json_other_activity_region_query_receipt_v1(
            cluster["component_regions"], cluster=cluster)}
    candidate = family.evaluate_gemini_json_other_activity_family_cluster_v1(**options)
    assert source == before
    return candidate, options


def _primary(unit="Triệu đồng"):
    return _page([_row(OWNER, "70", "60", kind="TOTAL")], primary=True, unit=unit)


def _continued_scope_inputs():
    primary, sender, receiver, compiled = _repaired_continuation_case(None)
    candidate, options = _public_candidate([primary, sender, receiver], compiled=compiled)
    assert candidate["status"] == family.READY
    assert family.validate_gemini_json_other_activity_family_candidate_replay_v1(candidate, **options) == candidate
    proof = _control(candidate)["fragments"][-1]["source_owned_continuation_unit_context"]
    assert proof["canonical_unit"] == "MILLION_VND" and proof["period_proof_kind"] == "EXACT_INHERITED_BLANK_HEADERS"
    receipts = {family._source_identity_v1(item["region"]): item for item in candidate["closure_receipt"]["table_receipts"]}
    semantic_pages = family._apply_source_repair_receipts_to_pages(
        deepcopy(options["page_json_by_version"]), options["query_receipt"]["adapter_receipt"]["source_repair_receipts"])
    contexts = []
    for region in options["regions"][-2:]:
        page = options["page_json_by_version"][region["page_json_version_id"]]
        section, table = family._source_table(page, section_id=region["section_id"], table_id=region["table_id"])
        semantic_section, semantic_table = family._source_table(semantic_pages[region["page_json_version_id"]],
            section_id=region["section_id"], table_id=region["table_id"])
        contexts.append({"region": region, "page": page, "section": section, "table": table,
            "semantic_section": semantic_section, "semantic_table": semantic_table,
            "scoped_axis": family._unit_axis(table, compiled_specs=options["compiled_specs"], document_unit_context=None),
            "table_receipt": receipts[family._source_identity_v1(region)]})
    assert receiver["sections"][0]["tables"][0]["unit_exact"] is None
    return contexts, options, candidate


def _assert_changed_continuation_source_is_held(records, compiled):
    original = deepcopy(records)
    candidate, options = None, None
    try:
        base = family.coalesce_gemini_json_multitable_hierarchical_document_v1(
            page_records=records, compiled_specs=compiled)
        cluster = family.recover_gemini_json_other_activity_query_cluster_v1(
            page_records=records, base_cluster=base, compiled_specs=compiled)
        if cluster["status"] == family.READY:
            options = {"regions": cluster["component_regions"],
                "page_json_by_version": {record["page_json_version_id"]: record["page_json"] for record in records},
                "compiled_specs": compiled,
                "query_receipt": family.build_gemini_json_other_activity_region_query_receipt_v1(
                    cluster["component_regions"], cluster=cluster)}
            candidate = family.evaluate_gemini_json_other_activity_family_cluster_v1(**options)
    except (family.GeminiJsonOtherActivityFamilyV1Error, GeminiJsonMultitableHierarchicalFamilyV1Error) as error:
        # A changed source/axis can be rejected by authentication before a
        # query or financial candidate exists. No stale READY receipt is used.
        assert str(error)
        assert records == original
        return
    if candidate is None:
        assert cluster["status"] == family.UNRESOLVED and not cluster.get("mappings")
    else:
        assert candidate["status"] == family.UNRESOLVED and candidate["mappings"] == []
        # Replay/audit failures are not accepted as source-axis rejections.
        assert family.validate_gemini_json_other_activity_family_candidate_replay_v1(candidate, **options) == candidate
        assert validate_source_observation_mapping_contract_v1(candidate)["mapping_count"] == 0
    assert records == original


def _control(candidate):
    return candidate["closure_receipt"]["other_activity_source_role_unit_control_receipt"]


def _inactive(envelope):
    assert envelope["format_version"] == "F38_INACTIVE_CANONICAL_JSON_UTF8_TEXT_V1"
    raw = envelope["canonical_json_one_lf_utf8_text"].encode("utf-8")
    assert len(raw) == envelope["size_bytes"] and sha256(raw).hexdigest() == envelope["sha256"]
    return json.loads(raw)


def _reseal(candidate):
    receipt = _control(candidate)
    receipt["receipt_id"] = "gjoafav1:source-role-unit:" + canonical_json_sha256_v1(
        {key: value for key, value in receipt.items() if key != "receipt_id"})
    if "source_role_unit_control_receipt_id" in candidate["closure_receipt"]["structural_root_receipt"]:
        candidate["closure_receipt"]["structural_root_receipt"]["source_role_unit_control_receipt_id"] = receipt["receipt_id"]
    candidate["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in candidate.items() if key != "candidate_id"})


@pytest.mark.parametrize("label,role,index", [
    ("Thu hồi các khoản nợ đã xử lý bằng quỹ dự phòng", "INCOME_DEBT_RECOVERY", 1),
    ("Thu từ các khoản nợ đã được xử lý, bù đắp bằng nguồn dự phòng rủi ro", "INCOME_DEBT_RECOVERY", 1),
    ("Thu từ các khoản nợ đã xử lý rủi ro", "INCOME_DEBT_RECOVERY", 1),
    ("Lãi từ thanh lý tài sản cố định", "INCOME_ASSET_DISPOSAL", 1),
    ("Thu từ nghiệp vụ phái sinh khác", "INCOME_DERIVATIVE", 1),
    ("Chi phí nghiệp vụ phái sinh khác", "EXPENSE_DERIVATIVE", 4),
    ("Chi cho thanh lý, nhượng bán tài sản cố định", "EXPENSE_ASSET_DISPOSAL", 4),
    ("Chi về công tác xã hội", "EXPENSE_SOCIAL", 4),
])
def test_exact_nonmixed_source_variant_keeps_its_specific_role_cells_and_parent_scope(label, role, index):
    rows = _gross_rows()
    rows[index]["label_exact"] = label
    rows[index]["hierarchy_path_exact"][-1] = label
    note = _page(rows)
    before = deepcopy(note)
    candidate, options = _public_candidate([_primary(), note])
    assert candidate["status"] == family.READY
    mapping = next(item for item in candidate["mappings"] if item["role"] == role)
    assert [cell["source_text"] for cell in mapping["values"]] == rows[index]["values_exact"]
    assert mapping["source_refs"][0]["row_ordinal"] == index + 1
    assert mapping["source_refs"][0]["hierarchy_path_exact"] == rows[index]["hierarchy_path_exact"]
    assert not any(ref["label_exact"] == label for item in candidate["mappings"]
        if item["role"] in {"INCOME_OTHER", "EXPENSE_OTHER"} for ref in item["source_refs"])
    assert validate_source_observation_mapping_contract_v1(candidate)["mapping_count"] == len(candidate["mappings"])
    assert family.validate_gemini_json_other_activity_family_candidate_replay_v1(candidate, **options) == candidate
    assert note == before


@pytest.mark.parametrize("label", ["Chi về công tác xã hội", "Chi phí nghiệp vụ phái sinh khác", "Chi cho thanh lý, nhượng bán tài sản cố định"])
def test_specific_expense_alias_cannot_claim_the_income_context_or_be_rescued_by_other(label):
    rows = _gross_rows()
    rows[1]["label_exact"] = label
    rows[1]["hierarchy_path_exact"] = ["Thu nhập từ hoạt động khác", label]
    candidate, _options = _public_candidate([_primary(), _page(rows)])
    assert candidate["status"] == family.UNRESOLVED and candidate["mappings"] == []
    assert validate_source_observation_mapping_contract_v1(candidate)["mapping_count"] == 0


@pytest.mark.parametrize("label", list(family._UNPROVEN_MIXED_ROLE_LABELS_V1))
def test_source_mixed_granularity_never_splits_or_claims_other_from_amount_closure(label):
    rows = _gross_rows()
    rows[1]["label_exact"] = label
    rows[1]["hierarchy_path_exact"][-1] = label
    note = _page(rows)
    before = deepcopy(note)
    candidate, options = _public_candidate([_primary(), note])
    assert candidate["status"] == family.UNRESOLVED and candidate["mappings"] == []
    assert "F38_SOURCE_TEMPLATE_ROLE_GRANULARITY_NOT_PROVEN" in candidate["reasons"]
    assert _control(candidate)["unproven_role_source_rows"][0]["source_row"] == before["sections"][0]["tables"][0]["rows"][1]
    assert validate_source_observation_mapping_contract_v1(candidate)["mapping_count"] == 0
    assert family.validate_gemini_json_other_activity_family_candidate_replay_v1(candidate, **options) == candidate
    assert note == before


def test_locally_printed_column_units_are_independent_authority_when_table_unit_is_blank():
    note = _page(_gross_rows())
    note["sections"][0]["tables"][0]["unit_exact"] = None
    candidate, _options = _public_candidate([_primary(), note])
    assert candidate["status"] == family.READY
    assert note["sections"][0]["tables"][0]["unit_exact"] is None
    assert all(fragment["source_local_unit_axis"]["complete"] for fragment in _control(candidate)["fragments"])


def test_primary_root_replacement_retires_exact_note_root_authority_and_binds_actual_mapping():
    candidate, options = _public_candidate([_primary(), _page(_gross_rows())])
    assert candidate["status"] == family.READY
    adapter = candidate["closure_receipt"]["other_activity_adapter_receipt"]
    retired = _inactive(adapter["retired_note_root_authority"])
    assert retired["root_mappings_before"]
    assert all(ref["locator"]["physical_page"] == 2 for mapping in retired["root_mappings_before"] for ref in mapping["source_refs"])
    root = next(item for item in candidate["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL")
    assert root["source_refs"][0]["locator"]["physical_page"] == 1
    structural = candidate["closure_receipt"]["structural_root_receipt"]
    assert structural["active_permission"] == "F38_DIRECT_PRIMARY_SOURCE_ROOT"
    assert structural["source_root_mapping_id"] == root["item_mapping_id"] == adapter["direct_primary_root_mapping_id"]
    assert structural["source_role_unit_control_receipt_id"] == _control(candidate)["receipt_id"]
    assert all(equation.get("equation_kind") != "EXACT_COMPLETE_TOP_LEVEL_COMPONENT_SUM_DERIVES_FAMILY_ROOT" for equation in candidate["closure_receipt"]["equations"])
    assert validate_source_observation_mapping_contract_v1(candidate)["mapping_count"] == len(candidate["mappings"])
    assert family.validate_gemini_json_other_activity_family_candidate_replay_v1(candidate, **options) == candidate


def test_equal_primary_cannot_donate_a_missing_note_unit_and_beforeimages_stay_truthful():
    note = _page(_gross_rows(), columns=[
        {"header_path_exact": ["Năm 2026"], "value_kind": "MONEY"},
        {"header_path_exact": ["Năm 2025"], "value_kind": "MONEY"}], unit=None)
    before = deepcopy(note)
    candidate, options = _public_candidate([_primary(), note])
    assert candidate["status"] == family.UNRESOLVED and candidate["mappings"] == []
    assert "F38_SOURCE_UNIT_NOT_LOCALLY_PROVEN" in candidate["reasons"]
    shared = family._evaluate_source_projected_cluster_v1(**options)
    assert _inactive(_control(candidate)["withheld_mapping_evidence"]) == shared["mappings"]
    assert note == before


@pytest.mark.parametrize("changed", ["source_sha", "selected_gap", "physical_gap", "sender_marker", "receiver_marker",
    "qualified_title", "receiver_statement_reset", "unknown_sender_unit", "conflicting_receiver_unit", "nonblank_header"])
def test_continued_table_unit_scope_rejects_identity_marker_owner_unit_and_period_counterexamples(changed):
    contexts, options, _candidate = _continued_scope_inputs()
    compiled = options["compiled_specs"]
    prior, current = contexts
    if changed == "source_sha":
        current["region"]["source_sha256"] = "f" * 64
    elif changed == "selected_gap":
        current["region"]["selected_page_ordinal"] += 1
    elif changed == "physical_gap":
        current["region"]["physical_page"] += 1
    elif changed == "sender_marker":
        prior["table"]["continuation"] = "NONE"
    elif changed == "receiver_marker":
        current["table"]["continuation"] = "NONE"
    elif changed == "qualified_title":
        current["table"]["title_exact"] = "Hoạt động khác của công ty con"
    elif changed == "receiver_statement_reset":
        current["section"]["statement_type"] = "INCOME_STATEMENT"
    elif changed == "unknown_sender_unit":
        prior["table"]["unit_exact"] = None
        for column in prior["table"]["columns"]:
            column["header_path_exact"] = [column["header_path_exact"][0]]
        prior["scoped_axis"] = family._unit_axis(prior["table"], compiled_specs=compiled, document_unit_context=None)
    elif changed == "conflicting_receiver_unit":
        current["table"]["unit_exact"] = "USD"
        current["scoped_axis"] = family._unit_axis(current["table"], compiled_specs=compiled, document_unit_context=None)
    else:
        current["table"]["columns"][0]["header_path_exact"] = ["Năm 2024"]
    records = [_record(page, ordinal=ordinal) for ordinal, page in enumerate(options["page_json_by_version"].values(), 1)]
    for field in ("source_sha256", "selected_page_ordinal", "physical_page"):
        records[-1][field] = current["region"][field]
    _assert_changed_continuation_source_is_held(records, compiled)


def test_continued_unit_scope_rejects_a_stale_inherited_period_locator_and_fresh_replay_detects_it():
    contexts, options, candidate = _continued_scope_inputs()
    prior, current = contexts
    locator = current["table_receipt"]["lane_axis"]["source_period_axis"]["inherited_from_locator"]
    locator["page_json_version_id"] = "gfpstorev1:json:" + "f" * 64
    assert family._source_owned_continuation_unit_context_v1(prior, current, compiled_specs=options["compiled_specs"]) is None
    with pytest.raises(family.GeminiJsonOtherActivityFamilyV1Error, match="candidate replay"):
        family.validate_gemini_json_other_activity_family_candidate_replay_v1(candidate, **options)


def test_unit_scope_proof_does_not_read_amounts_or_claim_financial_closure():
    contexts, options, _candidate = _continued_scope_inputs()
    compiled = options["compiled_specs"]
    prior, current = deepcopy(contexts)
    # This tests only the nonnumeric scope predicate. The changed monetary
    # source is never claimed READY or used as a substituted financial result.
    current["table"]["rows"][0]["values_exact"] = ["999", "888"]
    proof = family._source_owned_continuation_unit_context_v1(prior, current, compiled_specs=compiled)
    assert proof["canonical_unit"] == "MILLION_VND"
    assert current["table"]["unit_exact"] is None


def test_held_beforeimages_are_exact_inactive_envelopes_and_do_not_reenter_mapping_audit():
    rows = _gross_rows()
    rows[1]["label_exact"] = "Thu bán tài sản gán nợ"
    rows[1]["hierarchy_path_exact"][-1] = rows[1]["label_exact"]
    candidate, options = _public_candidate([_primary(), _page(rows)])
    shared = family._evaluate_source_projected_cluster_v1(**options)
    assert shared["status"] == family.READY and shared["mappings"]
    assert candidate["status"] == family.UNRESOLVED and candidate["mappings"] == []
    proof = _control(candidate)
    assert proof["candidate_before_sha256"] == canonical_json_sha256_v1(shared)
    assert _inactive(proof["withheld_mapping_evidence"]) == shared["mappings"]
    retired = _inactive(proof["retired_root_authority"])
    root_kind = "EXACT_COMPLETE_TOP_LEVEL_COMPONENT_SUM_DERIVES_FAMILY_ROOT"
    assert retired["global_root_equations"] == [item for item in shared["closure_receipt"]["equations"] if item.get("equation_kind") == root_kind]
    assert candidate["closure_receipt"]["equations"] == [item for item in shared["closure_receipt"]["equations"] if item.get("equation_kind") != root_kind]
    assert candidate["closure_receipt"]["structural_root_receipt"]["emitted_mapping"] is False
    assert validate_source_observation_mapping_contract_v1(shared)["mapping_count"] == len(shared["mappings"])
    assert validate_source_observation_mapping_contract_v1(candidate)["mapping_count"] == 0
    forged = deepcopy(candidate)
    changed = _inactive(_control(forged)["withheld_mapping_evidence"])
    changed[0]["values"][0]["coefficient"] += 1
    _control(forged)["withheld_mapping_evidence"] = family._inactive_evidence_envelope_v1(changed)
    _reseal(forged)
    with pytest.raises(family.GeminiJsonOtherActivityFamilyV1Error, match="candidate replay drifted"):
        family.validate_gemini_json_other_activity_family_candidate_replay_v1(forged, **options)


@pytest.mark.parametrize("axis", ["source_local_unit_axis", "scoped_local_unit_axis", "retired_root_authority"])
def test_self_resealed_source_unit_or_retired_authority_proof_does_not_replace_fresh_source_replay(axis):
    rows = _gross_rows()
    rows[1]["label_exact"] = "Thu bán tài sản gán nợ"
    rows[1]["hierarchy_path_exact"][-1] = rows[1]["label_exact"]
    candidate, options = _public_candidate([_primary(), _page(rows)])
    forged = deepcopy(candidate)
    control = _control(forged)
    if axis == "retired_root_authority":
        value = _inactive(control[axis])
        value["structural_root_receipt_before"]["emitted_mapping"] = False
        control[axis] = family._inactive_evidence_envelope_v1(value)
    else:
        control["fragments"][0][axis]["canonical_unit"] = "VND"
    _reseal(forged)
    with pytest.raises(family.GeminiJsonOtherActivityFamilyV1Error, match="candidate replay drifted"):
        family.validate_gemini_json_other_activity_family_candidate_replay_v1(forged, **options)
