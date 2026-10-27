"""Original-source unit permissions; no runtime or corpus result is asserted."""
from __future__ import annotations

import copy

import pytest
from test_gemini_json_issued_valuable_papers_family_v1 import (
    _adjacent_generic_root_fixture,
    _family_compiled_without_repairs,
    _primary_root_page,
    _shb_repeated_summary_fixture,
)
from test_gemini_json_issued_valuable_papers_source_total_lanes_v1 import (
    _decode_beforeimage,
    _evaluate,
    _packet_context,
    _page,
    _summary,
)

from bctc_ai.evaluation import gemini_json_issued_valuable_papers_family_v1 as family
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import READY, UNRESOLVED
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    audit_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _unit_receipt(candidate):
    return candidate["closure_receipt"]["issued_valuable_papers_adapter_receipt"][
        "original_source_unit_ownership_receipt"
    ]


def _options(pages, regions):
    return {"page_json_by_version": pages, "regions": regions,
            "compiled_specs": _family_compiled_without_repairs(),
            "query_receipt": family.build_gemini_json_issued_valuable_papers_region_query_receipt_v1(regions)}


def _audit_replay(candidate, options):
    audit = audit_source_observation_mapping_contract_v1(candidate)
    assert audit["status"] == "PASS", audit["violations"]
    assert audit["mapping_count"] == len(candidate["mappings"])
    assert family.validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(
        candidate, **options,
    ) == candidate


def _remove_units(table):
    table["unit_exact"] = None
    for column in table["columns"]:
        column["header_path_exact"] = [value for value in column["header_path_exact"]
                                       if value not in {"Triệu đồng", "Triệu VND", "VND"}]


@pytest.mark.parametrize("source", ["table", "columns", "VND"])
def test_genuine_original_unit_literals_preserve_financial_values_and_raw_pages(source):
    table = _summary()
    if source == "columns":
        table["unit_exact"] = None
    elif source == "VND":
        table["unit_exact"] = "VND"
        for column in table["columns"]:
            column["header_path_exact"][-1] = "VND"
    page = _page([table])
    before = copy.deepcopy(page)
    candidate, options = _evaluate(page)
    assert candidate["status"] == READY, candidate["reasons"]
    receipt = _unit_receipt(candidate)
    assert receipt["failures"] == []
    assert receipt["withheld_mappings"] is receipt["withheld_candidate_beforeimage"] is None
    assert all(item["original_source_unit_proof"]["source_kind"] == "ORIGINAL_TABLE_OR_ALL_MONEY_COLUMN_UNIT"
               for item in receipt["checks"])
    expected_unit = "VND" if source == "VND" else "MILLION_VND"
    assert {item["unit"] for item in candidate["mappings"]} == {expected_unit}
    root = next(item for item in candidate["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL")
    assert [cell["coefficient"] for cell in root["values"]] == [140, 110]
    financial_before = copy.deepcopy(candidate)
    checked = family._enforce_original_source_unit_ownership_v1(
        candidate, original_pages=options["page_json_by_version"], regions=options["regions"],
        compiled_specs=options["compiled_specs"],
    )
    assert checked["failures"] == [] and candidate == financial_before
    _audit_replay(candidate, options)
    assert page == before


@pytest.mark.parametrize("case,status", [
    ("f25-lpb-doc069", READY), ("f25-msb-doc076", UNRESOLVED), ("f25-vab-doc241", UNRESOLVED),
])
def test_actual_source_packets_keep_their_owned_units_and_existing_financial_dispositions(case, status):
    _case, options = _packet_context(case)
    before = copy.deepcopy(options["page_json_by_version"])
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**options)
    assert candidate["status"] == status, candidate["reasons"]
    assert _unit_receipt(candidate)["failures"] == []
    if status == READY:
        root = next(item for item in candidate["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL")
        assert [cell["coefficient"] for cell in root["values"]] == [64097013, 55458916]
        assert [cell["source_text"] for cell in root["values"]] == ["64.097.013", "55.458.916"]
    else:
        assert candidate["mappings"] == []
        assert "source_local_lane_binding_receipt" in candidate["closure_receipt"]["issued_valuable_papers_adapter_receipt"]
    _audit_replay(candidate, options)
    assert options["page_json_by_version"] == before


def test_shb_owned_transposed_instrument_and_explicit_row_periods_remain_ready():
    pages, regions = _shb_repeated_summary_fixture()
    before = copy.deepcopy(pages)
    options = _options(pages, regions)
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**options)
    assert candidate["status"] == READY, candidate["reasons"]
    assert _unit_receipt(candidate)["failures"] == []
    assert {item["unit"] for item in candidate["mappings"]} == {"MILLION_VND"}
    root = next(item for item in candidate["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL")
    assert [cell["coefficient"] for cell in root["values"]] == [53096625, 39248195]
    _audit_replay(candidate, options)
    assert pages == before


def test_raw_two_marker_owned_continuation_preserves_a_truly_blank_receiver_unit():
    pages, regions = _adjacent_generic_root_fixture()
    before = copy.deepcopy(pages)
    options = _options(pages, regions)
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**options)
    assert candidate["status"] == READY, candidate["reasons"]
    receipt = _unit_receipt(candidate)
    receiver_key = family._source_unit_scope_key_v1(regions[1])
    receiver = next(item for item in receipt["checks"]
                    if family._source_unit_scope_key_v1(item["locator"]) == receiver_key)
    proof = receiver["original_source_unit_proof"]
    assert proof["source_kind"] == "EXPLICIT_RAW_CONTINUATION_OF_SOURCE_OWNED_UNIT"
    assert proof["raw_unit_exact"] is None
    assert proof["raw_sender_continuation"] == "CONTINUES_ON_NEXT_PAGE"
    assert proof["raw_receiver_continuation"] == "CONTINUES_FROM_PREVIOUS_PAGE"
    assert proof["source_values_used_as_unit_authority"] is False
    assert [cell["coefficient"] for cell in candidate["mappings"][0]["values"]] == [4, 3]
    _audit_replay(candidate, options)
    assert pages == before
    assert pages[regions[1]["page_json_version_id"]]["sections"][0]["tables"][0]["unit_exact"] is None


def _numbered_context():
    _candidate, options = _evaluate(_page([_summary()]))
    region = options["regions"][0]
    page = options["page_json_by_version"][region["page_json_version_id"]]
    page["sections"][0]["title_exact"] = "22.1 Phát hành giấy tờ có giá"
    parent = page["sections"][0]["tables"][0]
    parent["title_exact"] = "22.1 Phát hành giấy tờ có giá"
    for column in parent["columns"]:
        column["header_path_exact"] = column["header_path_exact"][:1]
    child = copy.deepcopy(parent)
    child["title_exact"] = "22.1.1 Chi tiết phát hành giấy tờ có giá"
    child["unit_exact"] = None
    page["sections"][0]["tables"].append(child)
    regions = [region, {**region, "table_id": "t2", "fragment_ordinal": 2}]
    return page, _options(options["page_json_by_version"], regions)


def test_existing_explicit_numbered_note_context_uses_printed_scope_not_amounts():
    page, options = _numbered_context()
    before = copy.deepcopy(page)
    proofs = family._original_source_unit_proofs_v1(pages=options["page_json_by_version"],
        regions=options["regions"], compiled_specs=options["compiled_specs"])
    proof = proofs[family._source_unit_scope_key_v1(options["regions"][1])]
    assert proof["source_kind"] == "EXISTING_RAW_EXPLICIT_OWNER_NUMBERED_SUBSECTION"
    assert proof["raw_parent_outline_path"] == [22, 1]
    assert proof["raw_child_outline_path"] == [22, 1, 1]
    assert proof["source_values_used_as_unit_authority"] is False
    assert page == before


@pytest.mark.parametrize("drift", ["not_descendant", "intervening_table", "negative_owner", "prefixed_negative_owner", "qualified_family_owner", "period", "explicit_unknown_unit", "PRIMARY"])
def test_numbered_unit_context_cannot_cross_source_scope_or_override_local_evidence(drift):
    page, options = _numbered_context()
    section = page["sections"][0]
    child = section["tables"][1]
    if drift == "not_descendant":
        child["title_exact"] = "23.1.1 Chi tiết phát hành giấy tờ có giá"
    elif drift == "intervening_table":
        section["tables"].insert(1, copy.deepcopy(_summary()))
        options["regions"][1]["table_id"] = "t3"
    elif drift == "negative_owner":
        child["title_exact"] = "22.1.1 Tiền gửi khách hàng"
    elif drift == "prefixed_negative_owner":
        child["title_exact"] = "22.1.1 Chi tiết tiền gửi khách hàng"
    elif drift == "qualified_family_owner":
        child["title_exact"] = "22.1.1 Phát hành giấy tờ có giá của công ty con"
    elif drift == "period":
        child["columns"][0]["header_path_exact"] = ["31/12/2023"]
    elif drift == "explicit_unknown_unit":
        child["unit_exact"] = "USD"
    else:
        section["content_kind"] = "PRIMARY_STATEMENT"
        section["statement_type"] = "BALANCE_SHEET"
        page["status"] = "PRIMARY_FINANCIAL_STATEMENT"
    before = copy.deepcopy(page)
    proofs = family._original_source_unit_proofs_v1(pages=options["page_json_by_version"],
        regions=options["regions"], compiled_specs=options["compiled_specs"])
    assert family._source_unit_scope_key_v1(options["regions"][1]) not in proofs
    assert page == before


def _unknown_note_options(*, consensus=False):
    table = _summary()
    _remove_units(table)
    _candidate, options = _evaluate(_page([table]))
    primary = _primary_root_page()
    primary_table = primary["sections"][0]["tables"][0]
    primary_table["columns"][1]["header_path_exact"] = ["31/12/2025"]
    primary_table["columns"][2]["header_path_exact"] = ["31/12/2024"]
    primary_table["rows"][1]["values_exact"] = [None, "140", "110"]
    if consensus:
        primary_table["rows"][1]["values_exact"] = [None, "999", "888"]
    options["page_json_by_version"]["gfpstorev1:json:" + "c" * 64] = primary
    if consensus:
        options["page_json_by_version"]["gfpstorev1:json:" + "d" * 64] = copy.deepcopy(primary)
    return options


@pytest.mark.parametrize("consensus", [False, True])
def test_public_unknown_note_unit_cannot_use_primary_equality_periods_or_consensus(consensus):
    options = _unknown_note_options(consensus=consensus)
    before = copy.deepcopy(options["page_json_by_version"])
    projected, _regions, receipts = family._project_adjacent_source_syntax_v1(
        pages=before, regions=options["regions"], compiled_specs=options["compiled_specs"], original_pages=before,
    )
    note_version = options["regions"][0]["page_json_version_id"]
    assert projected[note_version]["sections"][0]["tables"][0]["unit_exact"] is None
    assert not any(projection.get("projection_kind") == "EXACT_PRIMARY_OWNER_ROW_AND_NOTE_TERMINAL_TOTAL_ALL_LANE_PERIOD_MATCH_SCOPES_BLANK_FRAGMENT_UNIT"
                   for receipt in receipts for projection in receipt["table_projections"])
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**options)
    assert candidate["status"] == UNRESOLVED and candidate["mappings"] == []
    assert _unit_receipt(candidate)["failures"] == ["ORIGINAL_SOURCE_MONEY_UNIT_NOT_OWNED"]
    assert candidate["closure_receipt"]["equations"] == []
    assert candidate["closure_receipt"]["root_component_sum_receipts"] == []
    assert candidate["closure_receipt"]["structural_root_receipt"]["emitted_mapping"] is False
    _audit_replay(candidate, options)
    assert options["page_json_by_version"] == before


def test_public_one_sided_marker_projection_cannot_supply_missing_original_unit_permission():
    pages, regions = _adjacent_generic_root_fixture()
    pages[regions[0]["page_json_version_id"]]["sections"][0]["tables"][0]["continuation"] = "NONE"
    options = _options(pages, regions)
    before = copy.deepcopy(pages)
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**options)
    assert candidate["status"] == UNRESOLVED and candidate["mappings"] == []
    assert "ORIGINAL_SOURCE_MONEY_UNIT_NOT_OWNED" in _unit_receipt(candidate)["failures"]
    _audit_replay(candidate, options)
    assert pages == before


@pytest.mark.parametrize("second_unit", [None, "VND"])
def test_every_selected_money_scope_needs_its_own_unit_even_for_zero_financial_rows(second_unit):
    if second_unit is None:
        options = _unknown_note_options()
    else:
        _candidate, options = _evaluate(_page([_summary()]))
    note_version = options["regions"][0]["page_json_version_id"]
    page = options["page_json_by_version"][note_version]
    second = _summary()
    for row in second["rows"]:
        row["values_exact"] = ["0", "0"]
    if second_unit is None:
        _remove_units(second)
    else:
        second["unit_exact"] = second_unit
        for column in second["columns"]:
            column["header_path_exact"][-1] = second_unit
    page["sections"][0]["tables"].append(second)
    options["regions"].append({**options["regions"][0], "table_id": "t2", "fragment_ordinal": 2})
    options["query_receipt"] = family.build_gemini_json_issued_valuable_papers_region_query_receipt_v1(options["regions"])
    before = copy.deepcopy(options["page_json_by_version"])
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**options)
    assert candidate["status"] == UNRESOLVED and candidate["mappings"] == []
    receipt = _unit_receipt(candidate)
    assert len([item for item in receipt["checks"] if "SELECTED_ORIGINAL_MONEY_TABLE" in item["uses"]]) == 2
    expected = "ORIGINAL_SOURCE_MONEY_UNIT_NOT_OWNED" if second_unit is None else "FINANCIAL_SOURCE_UNIT_POPULATIONS_CONFLICT"
    assert expected in receipt["failures"]
    _audit_replay(candidate, options)
    assert options["page_json_by_version"] == before


@pytest.mark.parametrize("drift", ["sender_marker", "receiver_marker", "nonadjacent", "owner", "qualified_headers", "unit_override"])
def test_continuation_unit_permission_is_replayed_from_raw_original_source(drift):
    pages, regions = _adjacent_generic_root_fixture()
    options = _options(pages, regions)
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**options)
    assert candidate["status"] == READY
    sender = pages[regions[0]["page_json_version_id"]]["sections"][0]["tables"][0]
    receiver_page = pages[regions[1]["page_json_version_id"]]
    receiver = receiver_page["sections"][0]["tables"][0]
    if drift == "sender_marker":
        sender["continuation"] = "NONE"
    elif drift == "receiver_marker":
        receiver["continuation"] = "NONE"
    elif drift == "nonadjacent":
        regions[1]["physical_page"] += 1
    elif drift == "owner":
        receiver_page["sections"][0]["title_exact"] = "Tiền gửi khách hàng"
    elif drift == "qualified_headers":
        receiver["columns"][0]["header_path_exact"] = ["Cuối kỳ", "Công ty con"]
        receiver["columns"][1]["header_path_exact"] = ["Đầu kỳ", "Công ty con"]
    else:
        receiver["unit_exact"] = "VND"
    before_candidate, before_pages = copy.deepcopy(candidate), copy.deepcopy(pages)
    receipt = family._enforce_original_source_unit_ownership_v1(
        candidate, original_pages=pages, regions=regions, compiled_specs=options["compiled_specs"],
    )
    assert receipt["failures"]
    assert candidate["status"] == UNRESOLVED and candidate["mappings"] == []
    assert _decode_beforeimage(receipt["withheld_mappings"]) == before_candidate["mappings"]
    assert _decode_beforeimage(receipt["withheld_candidate_beforeimage"]) == before_candidate
    assert audit_source_observation_mapping_contract_v1(candidate)["mapping_count"] == 0
    assert audit_source_observation_mapping_contract_v1(receipt)["mapping_count"] == 0
    assert pages == before_pages


@pytest.mark.parametrize("input_kind", ["equation", "table_receipt"])
def test_unit_guard_covers_financial_inputs_outside_the_mapping_list(input_kind):
    candidate, options = _evaluate(_page([_summary()]))
    assert candidate["status"] == READY
    foreign = {**options["regions"][0], "table_id": "t99"}
    if input_kind == "equation":
        candidate["closure_receipt"]["equations"][0]["result_source_refs"][0]["locator"] = foreign
    else:
        candidate["closure_receipt"]["table_receipts"].append({"region": foreign, "unit_axis": {"canonical_unit": "MILLION_VND"}})
    before = copy.deepcopy(candidate)
    receipt = family._enforce_original_source_unit_ownership_v1(candidate,
        original_pages=options["page_json_by_version"], regions=options["regions"], compiled_specs=options["compiled_specs"])
    assert receipt["failures"] == ["FINANCIAL_SOURCE_SCOPE_NOT_IN_ORIGINAL_QUERY"]
    assert candidate["status"] == UNRESOLVED and candidate["mappings"] == []
    assert _decode_beforeimage(receipt["withheld_candidate_beforeimage"]) == before
    assert candidate["closure_receipt"]["equations"] == []
    assert audit_source_observation_mapping_contract_v1(candidate)["mapping_count"] == 0


def test_empty_mapping_hold_does_not_invent_a_nonempty_withheld_image():
    options = _unknown_note_options()
    candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**options)
    assert candidate["status"] == UNRESOLVED and candidate["mappings"] == []
    before = copy.deepcopy(candidate)
    receipt = family._enforce_original_source_unit_ownership_v1(candidate,
        original_pages=options["page_json_by_version"], regions=options["regions"], compiled_specs=options["compiled_specs"])
    assert receipt["withheld_mappings"] is None
    assert _decode_beforeimage(receipt["withheld_candidate_beforeimage"]) == before
    assert _decode_beforeimage(receipt["withheld_candidate_beforeimage"])["mappings"] == []
    assert audit_source_observation_mapping_contract_v1(candidate)["mapping_count"] == 0


@pytest.mark.parametrize("field", ["owned_literal", "withheld_beforeimage"])
def test_self_resealed_unit_permission_or_opaque_beforeimage_cannot_bypass_fresh_replay(field):
    if field == "owned_literal":
        candidate, options = _evaluate(_page([_summary()]))
    else:
        options = _unknown_note_options()
        candidate = family.evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(**options)
    adapter = candidate["closure_receipt"]["issued_valuable_papers_adapter_receipt"]
    receipt = adapter["original_source_unit_ownership_receipt"]
    if field == "owned_literal":
        receipt["checks"][0]["original_source_unit_proof"]["raw_unit_exact"] = "VND"
    else:
        receipt["withheld_candidate_beforeimage"] = family._mapping_beforeimage_evidence_v1({"mappings": []})
    receipt["source_unit_ownership_receipt_id"] = "gjivpsuov1:receipt:" + canonical_json_sha256_v1(
        {key: value for key, value in receipt.items() if key != "source_unit_ownership_receipt_id"})
    if candidate["status"] == UNRESOLVED:
        candidate["closure_receipt"]["structural_root_receipt"]["source_unit_ownership_receipt_id"] = receipt["source_unit_ownership_receipt_id"]
    adapter["adapter_receipt_id"] = "gjivpfav1:receipt:" + canonical_json_sha256_v1(
        {key: value for key, value in adapter.items() if key != "adapter_receipt_id"})
    candidate["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in candidate.items() if key != "candidate_id"})
    with pytest.raises(family.GeminiJsonIssuedValuablePapersFamilyV1Error, match="candidate replay drifted"):
        family.validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(candidate, **options)
