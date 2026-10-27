"""UNRUN F28 source-root/fragment tests. All source pages are synthetic.

No actual-source registration, corpus/DB/PDF/provider job or financial validator
mock is used. The frozen engine's old source behavior is retained as an oracle.
"""
from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256

import pytest
from test_gemini_json_interest_income_family_v1 import (
    NOTE_VERSION,
    PRIMARY_VERSION,
    _cluster_and_candidate,
    _columns,
    _compiled,
    _indexed_query_evidence,
    _interest_rows,
    _page,
    _record,
    _row,
    _table,
)

from bctc_ai.evaluation import gemini_json_interest_income_family_v1 as family
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    _row_local_record as _frozen_row_local_record,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    audit_source_observation_mapping_contract_v1,
    validate_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _candidate(page):
    compiled = _compiled()
    cluster = family.coalesce_gemini_json_interest_income_document_v1(
        page_records=[_record(page)], compiled_specs=compiled,
    )
    assert cluster["status"] == READY
    receipt = family.build_gemini_json_interest_income_region_query_receipt_v1(cluster["component_regions"])
    options = {"regions": cluster["component_regions"], "page_json_by_version": {NOTE_VERSION: page},
               "compiled_specs": compiled, "query_receipt": receipt}
    return evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(**options), family.evaluate_gemini_json_interest_income_family_cluster_v1(**options), options


def _root(candidate):
    return next(item for item in candidate["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL")


def _control(candidate):
    return candidate["closure_receipt"]["interest_income_adapter_receipt"]["source_root_control_receipts"][0]


def _retired(envelope):
    assert envelope["format_version"] == "F28_RETIRED_MAPPING_CANONICAL_JSON_UTF8_TEXT_V1"
    raw = envelope["canonical_json_one_lf_utf8_text"].encode("utf-8")
    assert len(raw) == envelope["size_bytes"] and sha256(raw).hexdigest() == envelope["sha256"]
    return json.loads(raw)


@pytest.mark.parametrize("token,coefficient,cell_state", [
    ("1.234", 1234, "RAW_SIGNED_INTEGER"),
    ("(1.234)", -1234, "RAW_SIGNED_INTEGER"),
    (" - ", 0, "DASH_ZERO"),
    ("0", 0, "RAW_SIGNED_INTEGER"),
    (None, None, "BLANK_SOURCE_CELL"),
    ("  ", None, "BLANK_SOURCE_CELL"),
    ("1:234", 1234, "COLON_GROUP_SEPARATOR_INTEGER_IF_EQUATION_EXACT"),
    ("...", 0, "PUNCTUATION_PLACEHOLDER_ZERO_IF_EQUATION_EXACT"),
])
@pytest.mark.parametrize("compound", [False, True])
def test_local_printed_root_observation_preserves_exact_consumed_frozen_cells_and_source_refs(token, coefficient, cell_state, compound):
    row = _row("Tổng", ["7", "non-MONEY source text", token], kind="TOTAL", hierarchy=[None, "Tổng"])
    projection = {"source_row_ordinal": 9, "subrow_ordinal": 2}
    if compound:
        row["_compound_row_projection"] = projection
    region = {**{key: value for key, value in _record(_page(_table([]))).items() if key != "page_json"},
              "section_id": "s1", "table_id": "t1", "fragment_ordinal": 2,
              "component_roles": ["FAMILY_ROOT_TOTAL"]}
    axis = {"money_column_ordinals": [3, 1], "lane_keys": [["CURRENT"], ["COMPARATIVE"]]}
    before = deepcopy((row, region, axis))
    state = "SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_BY_F28_SOURCE_CONTROL"
    actual = family._printed_root_source_observation_v1(4, row, region=region, lane_axis=axis, state=state)
    expected_ref = {"hierarchy_path_exact": [None, "Tổng"], "label_exact": "Tổng",
                    "locator": deepcopy(region), "money_column_ordinals": [3, 1],
                    "row_id": "r4", "row_kind": "TOTAL", "row_ordinal": 4}
    if compound:
        expected_ref.update({"compound_row_projection": deepcopy(projection), "row_id": "r9#line2"})
    assert actual == {"cells": [
        {"coefficient": coefficient, "source_text": None if cell_state == "BLANK_SOURCE_CELL" else token, "state": cell_state},
        {"coefficient": 7, "source_text": "7", "state": "RAW_SIGNED_INTEGER"}],
        "source_refs": [expected_ref], "state": state}
    # The oracle is exposed by the already-frozen engine, never imported from
    # the other-family module by production F28 code. Only consumed fields agree.
    frozen = _frozen_row_local_record("FAMILY_ROOT_TOTAL", 4, row, region=region, lane_axis=axis, state=state)
    assert actual == {key: frozen[key] for key in ("cells", "source_refs", "state")}
    assert (row, region, axis) == before
    actual["source_refs"][0]["hierarchy_path_exact"].append("private mutation")
    actual["source_refs"][0]["locator"]["component_roles"].append("private mutation")
    if compound:
        actual["source_refs"][0]["compound_row_projection"]["subrow_ordinal"] = 99
    assert (row, region, axis) == before


@pytest.mark.parametrize("values", [None, {"1": "7"}, ["7"]])
def test_local_printed_root_observation_does_not_fill_missing_or_nonlist_source_cells(values):
    row = _row("Tổng", values, kind="TOTAL")
    before = deepcopy(row)
    assert family._printed_root_source_observation_v1(1, row, region={},
        lane_axis={"money_column_ordinals": [1, 2]}, state="SOURCE_ONLY") is None
    assert row == before


def _nonadditive_group_options(*, split=False):
    sender = _page(_table([
        _row("Thu nhập lãi tiền gửi", ["10", "8"]),
        _row("Thu nhập lãi cho vay khách hàng", ["20", "12"]),
        _row("Thu lãi từ kinh doanh, đầu tư chứng khoán nợ", ["5", "4"], kind="GROUP"),
    ]))
    details = ([_row("Thu lãi từ chứng khoán kinh doanh", ["2", "1"]),
                _row("Thu lãi từ chứng khoán đầu tư", ["3", "3"])] if split
               else [_row("Thu lãi từ chứng khoán đầu tư", ["5", "4"])])
    receiver = _page(_table([
        *details, _row("Thu phí từ nghiệp vụ bảo lãnh", ["1", "1"]),
        _row("Thu nhập lãi cho thuê tài chính", ["-", "-"]),
        _row("Thu khác từ hoạt động tín dụng", ["2", "2"]),
        _row(None, ["38", "27"], kind="TOTAL"),
    ], columns=_columns([None], [None]), title=None, unit=None))
    sender["sections"][0]["tables"][0]["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    receiver["sections"][0]["tables"][0]["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"
    compiled = _compiled()
    records = [_record(sender), _record(receiver, version=PRIMARY_VERSION,
        physical_page=3, selected_page_ordinal=3)]
    cluster = family.coalesce_gemini_json_interest_income_document_v1(page_records=records, compiled_specs=compiled)
    assert cluster["status"] == READY and len(cluster["component_regions"]) == 2
    regions = cluster["component_regions"]
    return {"regions": regions, "page_json_by_version": {NOTE_VERSION: sender, PRIMARY_VERSION: receiver},
        "compiled_specs": compiled, "query_receipt": family.build_gemini_json_interest_income_region_query_receipt_v1(regions)}


def test_raw_semantic_group_owns_securities_and_narrower_continued_detail_is_nonadditive():
    options = _nonadditive_group_options()
    original = deepcopy(options["page_json_by_version"])
    before = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(**options)
    assert before["status"] == READY
    old_securities = next(item for item in before["mappings"] if item["role"] == "SECURITIES_INTEREST")
    assert [cell["coefficient"] for cell in old_securities["values"]] == [10, 8]
    assert [cell["coefficient"] for cell in _root(before)["values"]] == [43, 31]
    actual = family.evaluate_gemini_json_interest_income_family_cluster_v1(**options)
    assert actual["status"] == READY, actual["reasons"]
    securities = next(item for item in actual["mappings"] if item["role"] == "SECURITIES_INTEREST")
    assert securities["values"] == [
        {"coefficient": 5, "source_text": "5", "state": "RAW_SIGNED_INTEGER"},
        {"coefficient": 4, "source_text": "4", "state": "RAW_SIGNED_INTEGER"},
    ]
    assert [(ref["locator"]["page_json_version_id"], ref["row_ordinal"]) for ref in securities["source_refs"]] == [(NOTE_VERSION, 3)]
    assert [cell["coefficient"] for cell in _root(actual)["values"]] == [38, 27]
    assert [cell["source_text"] for cell in _root(actual)["values"]] == ["38", "27"]
    assert _root(actual)["source_refs"][0]["locator"]["page_json_version_id"] == PRIMARY_VERSION
    control = _control(actual)
    assert control["shared_candidate_before_sha256"] == canonical_json_sha256_v1(before)
    proof = control["nonadditive_group_continuation_receipt"]
    assert proof["status"] == "SOURCE_OWNED_GROUP_SUBTOTAL_DETAIL_NONADDITIVE"
    assert proof["amounts_select_scope"] is False and proof["missing_components_inferred"] is False
    assert proof["child_amounts_only_corroborate_or_veto"] is True
    assert proof["bound_role_mapping_id"] == securities["item_mapping_id"]
    retired = _retired(proof["retired_role_authority"])
    assert retired["role_mappings"] == [old_securities]
    assert retired["root_mappings"] == [_root(before)]
    assert retired["cluster_aggregation_receipts"] == before["closure_receipt"]["cluster_aggregation_receipts"]
    assert actual["closure_receipt"]["cluster_aggregation_receipts"] == []
    assert actual["closure_receipt"]["root_component_sum_receipts"] == []
    assert not any(item["equation_kind"] == "EXACT_COMPLETE_TOP_LEVEL_COMPONENT_SUM_DERIVES_FAMILY_ROOT" for item in actual["closure_receipt"]["equations"])
    retained_local = [item for item in before["closure_receipt"]["equations"] if item["equation_kind"] != "EXACT_COMPLETE_TOP_LEVEL_COMPONENT_SUM_DERIVES_FAMILY_ROOT"]
    assert actual["closure_receipt"]["equations"][:-1] == retained_local
    assert actual["closure_receipt"]["equations"][-1]["equation_id"] == proof["corroborating_equation_id"]
    source_only = actual["closure_receipt"]["source_only_unmapped_rows"]
    assert len(source_only) == 1
    assert all(item["declared_validation_role"] == "F28_NONADDITIVE_CONTINUED_SECURITIES_SUBSET_SOURCE_ONLY" for item in source_only)
    assert {ref["row_ordinal"] for item in source_only for ref in item["source_refs"]} == {1}
    assert audit_source_observation_mapping_contract_v1(actual)["mapping_count"] == len(actual["mappings"]) == 7
    assert family.validate_gemini_json_interest_income_family_candidate_replay_v1(actual, **options) == actual
    assert options["page_json_by_version"] == original


def test_unsealed_two_detail_group_shape_remains_an_explicit_algorithm_hold():
    options = _nonadditive_group_options(split=True)
    original = deepcopy(options["page_json_by_version"])
    before = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(**options)
    reasons = [
        "CONFLICTING_SOURCE_VALUES_FOR_ROLE_LANE:SECURITIES_INTEREST:COMPARATIVE_PERIOD",
        "CONFLICTING_SOURCE_VALUES_FOR_ROLE_LANE:SECURITIES_INTEREST:CURRENT_PERIOD",
        "DUPLICATE_ROLE_SOURCE_ROWS_NOT_ALL_EQUATION_CONSUMED",
    ]
    assert before["status"] == UNRESOLVED and before["reasons"] == reasons and before["mappings"] == []
    actual = family.evaluate_gemini_json_interest_income_family_cluster_v1(**options)
    assert actual["status"] == UNRESOLVED and actual["reasons"] == reasons and actual["mappings"] == []
    assert audit_source_observation_mapping_contract_v1(actual)["mapping_count"] == 0
    assert family.validate_gemini_json_interest_income_family_candidate_replay_v1(actual, **options) == actual
    assert options["page_json_by_version"] == original


def test_complete_raw_parent_owns_both_lanes_while_narrower_child_blank_stays_source_only_null():
    options = _nonadditive_group_options()
    child = options["page_json_by_version"][PRIMARY_VERSION]["sections"][0]["tables"][0]["rows"][0]
    child["values_exact"][1] = None
    original = deepcopy(options["page_json_by_version"])
    before = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(**options)
    assert before["status"] == READY
    old_role = next(item for item in before["mappings"] if item["role"] == "SECURITIES_INTEREST")
    assert old_role["state"] == "PARTIAL_SOURCE_OBSERVATION"
    assert [cell["coefficient"] for cell in old_role["values"]] == [10, None]
    assert not any(item["role"] == "FAMILY_ROOT_TOTAL" for item in before["mappings"])
    actual = family.evaluate_gemini_json_interest_income_family_cluster_v1(**options)
    assert actual["status"] == READY, actual["reasons"]
    role = next(item for item in actual["mappings"] if item["role"] == "SECURITIES_INTEREST")
    assert [cell["coefficient"] for cell in role["values"]] == [5, 4]
    assert [cell["source_text"] for cell in role["values"]] == ["5", "4"]
    assert [(ref["locator"]["page_json_version_id"], ref["row_ordinal"]) for ref in role["source_refs"]] == [(NOTE_VERSION, 3)]
    assert [cell["coefficient"] for cell in _root(actual)["values"]] == [38, 27]
    proof = _control(actual)["nonadditive_group_continuation_receipt"]
    assert proof["narrower_prefix_corroboration"]["observed_prefix_sum"] == [5, None]
    missing = {"coefficient": None, "source_text": None, "state": "BLANK_SOURCE_CELL"}
    assert proof["narrower_prefix_corroboration"]["observed_children"][0]["cells"][1] == missing
    assert actual["closure_receipt"]["source_only_unmapped_rows"][0]["cells"][1] == missing
    assert proof["missing_components_inferred"] is False
    assert proof["narrower_prefix_corroboration"]["child_prefix_exhaustiveness_claimed"] is False
    retired = _retired(proof["retired_role_authority"])
    assert retired["role_mappings"] == [old_role] and retired["root_mappings"] == []
    assert retired["cluster_aggregation_receipts"] == before["closure_receipt"]["cluster_aggregation_receipts"]
    assert _retired(_control(actual)["direct_printed_root_binding"]["prior_root_mapping"]) is None
    assert actual["closure_receipt"]["cluster_aggregation_receipts"] == []
    assert actual["closure_receipt"]["structural_root_receipt"]["emitted_mapping"] is True
    assert audit_source_observation_mapping_contract_v1(actual)["mapping_count"] == len(actual["mappings"]) == 7
    assert family.validate_gemini_json_interest_income_family_candidate_replay_v1(actual, **options) == actual
    assert options["page_json_by_version"] == original


@pytest.mark.parametrize("mutation", [
    "missing_sender_marker", "missing_receiver_marker", "parent_not_group", "wrong_parent", "qualified_parent",
    "qualified_child", "partial_scope", "competing_group", "later_same_role",
    "child_conflict", "parent_blank", "sender_unit_missing", "receiver_wrong_unit",
    "receiver_owner_reset", "receiver_qualified_header", "extra_unmapped_row",
    "sender_qualified_section", "sender_unrelated_section", "sender_qualified_table",
])
def test_nonadditive_group_requires_independent_semantic_scope_even_when_old_sum_can_match(mutation):
    options = _nonadditive_group_options()
    sender = options["page_json_by_version"][NOTE_VERSION]["sections"][0]["tables"][0]
    receiver = options["page_json_by_version"][PRIMARY_VERSION]["sections"][0]["tables"][0]
    # These scope negatives deliberately agree with the OLD double-counted sum.
    # Numerical closure can never grant the absent semantic parent permission.
    if mutation in {"parent_not_group", "wrong_parent", "qualified_parent", "qualified_child", "partial_scope", "competing_group", "later_same_role", "receiver_owner_reset", "receiver_qualified_header", "extra_unmapped_row", "sender_qualified_section", "sender_unrelated_section", "sender_qualified_table"}:
        receiver["rows"][-1]["values_exact"] = ["43", "31"]
    if mutation == "missing_sender_marker":
        sender["continuation"] = "NONE"
    elif mutation == "missing_receiver_marker":
        receiver["continuation"] = "NONE"
    elif mutation == "parent_not_group":
        sender["rows"][-1]["row_kind"] = "ITEM"
    elif mutation == "wrong_parent":
        sender["rows"][-1]["label_exact"] = "Thu lãi từ đầu tư chứng khoán nợ"
        sender["rows"][-1]["hierarchy_path_exact"] = [sender["rows"][-1]["label_exact"]]
    elif mutation == "qualified_parent":
        sender["rows"][-1]["label_exact"] += " của công ty con"
        sender["rows"][-1]["hierarchy_path_exact"] = [sender["rows"][-1]["label_exact"]]
    elif mutation == "qualified_child":
        receiver["rows"][0]["label_exact"] += " của công ty con"
        receiver["rows"][0]["hierarchy_path_exact"] = [receiver["rows"][0]["label_exact"]]
    elif mutation == "partial_scope":
        receiver["rows"][0]["hierarchy_path_exact"].insert(0, "Công ty con")
    elif mutation == "competing_group":
        sender["rows"][0]["row_kind"] = "GROUP"
    elif mutation == "later_same_role":
        receiver["rows"].insert(2, _row("Thu lãi từ chứng khoán kinh doanh", ["-", "-"]))
    elif mutation == "child_conflict":
        receiver["rows"][0]["values_exact"] = ["4", "3"]
    elif mutation == "parent_blank":
        sender["rows"][-1]["values_exact"][0] = None
    elif mutation == "sender_unit_missing":
        sender["unit_exact"] = None
    elif mutation == "receiver_wrong_unit":
        receiver["unit_exact"] = "VND"
    elif mutation == "receiver_owner_reset":
        receiver["title_exact"] = "Thu nhập lãi và các khoản thu nhập tương tự của công ty con"
    elif mutation == "receiver_qualified_header":
        receiver["columns"] = _columns(["Từ ngày 01/01/2025 đến ngày 31/03/2025", "Công ty con"],
            ["Từ ngày 01/01/2024 đến ngày 31/03/2024", "Công ty con"])
    elif mutation == "sender_qualified_section":
        options["page_json_by_version"][NOTE_VERSION]["sections"][0]["title_exact"] = sender["title_exact"] + " của công ty con"
    elif mutation == "sender_unrelated_section":
        options["page_json_by_version"][NOTE_VERSION]["sections"][0]["title_exact"] = "Thu nhập từ hoạt động dịch vụ"
    elif mutation == "sender_qualified_table":
        options["page_json_by_version"][NOTE_VERSION]["sections"][0]["title_exact"] = sender["title_exact"]
        sender["title_exact"] += " của công ty con"
    else:
        receiver["rows"].insert(1, _row("Khoản khác chưa được phân loại", ["-", "-"]))
    original = deepcopy(options["page_json_by_version"])
    if mutation in {"qualified_parent", "qualified_child"}:
        with pytest.raises(ValueError, match="fragment classification drifted"):
            family.evaluate_gemini_json_interest_income_family_cluster_v1(**options)
        # The source mutation must also pass through a freshly rebuilt public
        # query; the stale classification exception alone is not this control.
        records = [_record(options["page_json_by_version"][NOTE_VERSION]),
            _record(options["page_json_by_version"][PRIMARY_VERSION], version=PRIMARY_VERSION,
                physical_page=3, selected_page_ordinal=3)]
        cluster = family.coalesce_gemini_json_interest_income_document_v1(
            page_records=records, compiled_specs=options["compiled_specs"])
        if cluster["status"] != READY:
            assert cluster["status"] == UNRESOLVED and cluster["reasons"] and "mappings" not in cluster
            assert audit_source_observation_mapping_contract_v1(cluster)["mapping_count"] == 0
            assert options["page_json_by_version"] == original
            return
        options["regions"] = cluster["component_regions"]
        options["query_receipt"] = family.build_gemini_json_interest_income_region_query_receipt_v1(options["regions"])
    actual = family.evaluate_gemini_json_interest_income_family_cluster_v1(**options)
    assert actual["status"] == UNRESOLVED and actual["mappings"] == [], actual["reasons"]
    assert actual["closure_receipt"]["cluster_aggregation_receipts"] == []
    assert actual["closure_receipt"]["structural_root_receipt"]["emitted_mapping"] is False
    assert audit_source_observation_mapping_contract_v1(actual)["mapping_count"] == 0
    assert family.validate_gemini_json_interest_income_family_candidate_replay_v1(actual, **options) == actual
    if mutation == "parent_blank":
        proof = _control(actual)["nonadditive_group_continuation_receipt"]
        beforeimages = _retired(proof["retired_role_authority"])
        assert beforeimages["root_mappings"] == []
        assert [cell["coefficient"] for cell in beforeimages["role_mappings"][0]["values"]] == [None, 8]
        assert beforeimages["cluster_aggregation_receipts"]
        assert _retired(_control(actual)["retired_global_root_authority"])["structural_root_receipt_before"]["emitted_mapping"] is False
        assert actual["closure_receipt"]["root_component_sum_receipts"] == []
        assert not any(item["equation_kind"] == "EXACT_COMPLETE_TOP_LEVEL_COMPONENT_SUM_DERIVES_FAMILY_ROOT" for item in actual["closure_receipt"]["equations"])
    assert options["page_json_by_version"] == original


def test_repeated_narrower_alias_with_different_ordinals_is_not_distinct_semantic_scope():
    options = _nonadditive_group_options()
    # Genuine frozen beforeimage, not a fabricated READY candidate. The source
    # finalizer must independently reject drift to repeated semantic ownership.
    before = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(**options)
    assert before["status"] == READY
    receiver = options["page_json_by_version"][PRIMARY_VERSION]["sections"][0]["tables"][0]
    receiver["rows"][:1] = [
        _row("1. Thu lãi từ chứng khoán đầu tư", ["2", "1"]),
        _row("2. Thu lãi từ chứng khoán đầu tư", ["3", "3"]),
    ]
    original = deepcopy(options["page_json_by_version"])
    controlled, receipts = family._apply_source_root_controls_v1(before,
        pages=options["page_json_by_version"], original_pages=options["page_json_by_version"],
        regions=options["regions"], compiled_specs=options["compiled_specs"])
    assert controlled["status"] == UNRESOLVED and controlled["mappings"] == []
    assert "F28_NONADDITIVE_GROUP_DECLARED_PREFIX_NOT_PROVEN" in receipts[0]["reasons"]
    # Both children sum to the observed parent5/4, and the source total is38/27.
    # Different row ordinals cannot manufacture two distinct narrower owners.
    actual = family.evaluate_gemini_json_interest_income_family_cluster_v1(**options)
    assert actual["status"] == UNRESOLVED and actual["mappings"] == []
    assert audit_source_observation_mapping_contract_v1(actual)["mapping_count"] == 0
    assert family.validate_gemini_json_interest_income_family_candidate_replay_v1(actual, **options) == actual
    assert options["page_json_by_version"] == original


def test_nonadditive_group_scope_has_no_fixed_amount_or_zero_missing_component_rule():
    options = _nonadditive_group_options()
    sender = options["page_json_by_version"][NOTE_VERSION]["sections"][0]["tables"][0]
    receiver = options["page_json_by_version"][PRIMARY_VERSION]["sections"][0]["tables"][0]
    sender["rows"][-1]["values_exact"] = ["9", "7"]
    receiver["rows"][0]["values_exact"] = ["9", "7"]
    receiver["rows"][-1]["values_exact"] = ["42", "30"]
    original = deepcopy(options["page_json_by_version"])
    actual = family.evaluate_gemini_json_interest_income_family_cluster_v1(**options)
    assert actual["status"] == READY, actual["reasons"]
    assert [cell["coefficient"] for cell in next(item for item in actual["mappings"] if item["role"] == "SECURITIES_INTEREST")["values"]] == [9, 7]
    assert [cell["coefficient"] for cell in _root(actual)["values"]] == [42, 30]
    assert _control(actual)["nonadditive_group_continuation_receipt"]["missing_components_inferred"] is False
    assert family.validate_gemini_json_interest_income_family_candidate_replay_v1(actual, **options) == actual
    assert options["page_json_by_version"] == original


@pytest.mark.parametrize("field,value", [
    ("source_sha256", "e" * 64), ("source_logical_name", "different.pdf"),
    ("document_id", "gfpstorev1:document:" + "e" * 64),
    ("physical_page", 4), ("selected_page_ordinal", 4),
])
def test_nonadditive_group_never_crosses_a_changed_selected_source_identity(field, value):
    options = _nonadditive_group_options()
    options["regions"][1][field] = value
    try:
        options["query_receipt"] = family.build_gemini_json_interest_income_region_query_receipt_v1(options["regions"])
        actual = family.evaluate_gemini_json_interest_income_family_cluster_v1(**options)
    except ValueError:
        return  # The source-axis contract can reject before financial evaluation.
    assert actual["status"] == UNRESOLVED and actual["mappings"] == []
    assert audit_source_observation_mapping_contract_v1(actual)["mapping_count"] == 0


@pytest.mark.parametrize("field", ["retired_authority", "parent_ref", "source_only_cell"])
def test_nonadditive_group_policy_and_self_resealed_source_authority_replay_fail_closed(field):
    options = _nonadditive_group_options()
    actual = family.evaluate_gemini_json_interest_income_family_cluster_v1(**options)
    assert actual["status"] == READY
    proof = _control(actual)["nonadditive_group_continuation_receipt"]
    if field == "retired_authority":
        proof["retired_role_authority"] = family._retired_mapping_evidence_v1(None)
    elif field == "parent_ref":
        proof["source_parent_ref"]["row_ordinal"] = 1
    else:
        actual["closure_receipt"]["source_only_unmapped_rows"][0]["cells"][0]["coefficient"] = 999
    proof["receipt_id"] = "gjiifav1:nonadditive-group:" + canonical_json_sha256_v1({key: value for key, value in proof.items() if key != "receipt_id"})
    control = _control(actual)
    control["receipt_id"] = "gjiifav1:source-root:" + canonical_json_sha256_v1({key: value for key, value in control.items() if key != "receipt_id"})
    actual["closure_receipt"]["structural_root_receipt"]["source_root_control_receipt_id"] = control["receipt_id"]
    adapter = actual["closure_receipt"]["interest_income_adapter_receipt"]
    adapter["adapter_receipt_id"] = "gjiifav1:receipt:" + canonical_json_sha256_v1({key: value for key, value in adapter.items() if key != "adapter_receipt_id"})
    actual["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1({key: value for key, value in actual.items() if key != "candidate_id"})
    with pytest.raises(family.GeminiJsonInterestIncomeFamilyV1Error, match="candidate replay drifted"):
        family.validate_gemini_json_interest_income_family_candidate_replay_v1(actual, **options)
    options["compiled_specs"]["interest_income_nonadditive_group_scope"]["child_aliases"].append("Unproved alias")
    options["compiled_specs"]["interest_income_nonadditive_group_scope_sha256"] = canonical_json_sha256_v1(options["compiled_specs"]["interest_income_nonadditive_group_scope"])
    with pytest.raises(family.GeminiJsonInterestIncomeFamilyV1Error, match="nonadditive group scope drifted"):
        family.evaluate_gemini_json_interest_income_family_cluster_v1(**options)


def test_old_twenty_vs_twenty_four_positive_fixture_is_now_an_explicit_source_mismatch_negative():
    page = _page(_table(_interest_rows()))
    original = deepcopy(page)
    old, actual, _options = _candidate(page)
    assert old["status"] == READY
    assert [cell["coefficient"] for cell in _root(old)["values"]] == [35, 24]
    assert original["sections"][0]["tables"][0]["rows"][-1]["values_exact"] == ["35", "20"]
    assert actual["status"] == UNRESOLVED and actual["mappings"] == []
    assert "F28_PRINTED_FAMILY_ROOT_DIFFERS_FROM_EMITTED_ROOT" in actual["reasons"]
    proof = _control(actual)
    assert _retired(proof["withheld_mapping_evidence"]) == old["mappings"]
    assert proof["shared_candidate_before_sha256"] == canonical_json_sha256_v1(old)
    assert proof["fragments"][0]["printed_root_rows"][-1]["source_row"]["values_exact"] == ["35", "20"]
    assert page == original


def _omitted_sender_receiver(*, columns=None, unit="Triệu đồng", title=None):
    table = _table([
        _row("Thu nhập lãi cho vay", ["2.037.228", "1.828.993"]),
        _row("Thu lãi từ kinh doanh, đầu tư chứng khoán nợ:", ["223.238", "200.706"]),
        _row("Thu phí từ nghiệp vụ bảo lãnh", ["1.228", "4.807"]),
        _row("Thu nhập lãi cho thuê tài chính", ["-", " -"]),
        _row("Thu khác từ hoạt động tín dụng", ["16.192", "21.184"]),
        _row("Tổng", ["2.739.236", "2.236.509"], kind="TOTAL"),
    ], columns=columns, unit=unit, title=title)
    page = _page(table)
    page["sections"][0]["title_exact"] = None
    return page


def test_role_rich_local_fragment_cannot_claim_a_complete_root_over_an_omitted_sender():
    # Reproduce the review's arithmetic only; this is NOT actual VBB JSON/VIDs.
    page = _omitted_sender_receiver(title="Thu nhập lãi và các khoản thu nhập tương tự")
    original = deepcopy(page)
    old, actual, _options = _candidate(page)
    assert old["status"] == READY
    assert [cell["coefficient"] for cell in _root(old)["values"]] == [2277886, 2055690]
    assert actual["status"] == UNRESOLVED and actual["mappings"] == []
    assert "F28_PRINTED_FAMILY_ROOT_DIFFERS_FROM_EMITTED_ROOT" in actual["reasons"]
    assert _retired(_control(actual)["withheld_mapping_evidence"]) == old["mappings"]
    assert page == original


def test_complete_owned_source_binds_the_actual_printed_total_row_without_changing_cells():
    rows = _interest_rows()
    rows[-1] = _row("Tổng", ["35", "24"], kind="TOTAL")
    page = _page(_table(rows))
    original = deepcopy(page)
    _old, actual, options = _candidate(page)
    assert actual["status"] == READY
    root = _root(actual)
    assert root["row_id"] == "r4" and len(root["source_refs"]) == 1
    assert root["source_refs"][0]["label_exact"] == "Tổng"
    assert root["source_refs"][0]["row_kind"] == "TOTAL"
    assert [cell["source_text"] for cell in root["values"]] == ["35", "24"]
    assert _control(actual)["direct_printed_root_binding"]["bound_mapping_id"] == root["item_mapping_id"]
    assert family.validate_gemini_json_interest_income_family_candidate_replay_v1(actual, **options) == actual
    assert page == original


@pytest.mark.parametrize("printed", ["-", "0", None])
def test_direct_total_preserves_printed_dash_zero_and_blank_types(printed):
    rows = [_row("Thu nhập lãi tiền gửi", ["10", "-"]),
            _row("Thu nhập lãi cho vay khách hàng", ["20", "-"]),
            _row("Thu lãi từ đầu tư chứng khoán nợ", ["5", "-"]),
            _row("Tổng", ["35", printed], kind="TOTAL")]
    page = _page(_table(rows))
    original = deepcopy(page)
    _old, actual, _options = _candidate(page)
    if printed is None:
        assert actual["status"] == UNRESOLVED and actual["mappings"] == []
    else:
        assert actual["status"] == READY
        assert _root(actual)["values"][1] == {"coefficient": 0, "source_text": printed,
                                             "state": "DASH_ZERO" if printed == "-" else "RAW_SIGNED_INTEGER"}
    assert page == original


def _recovered_pair(mutation=None):
    sender = _page(_table([_row("Thu nhập lãi tiền gửi", ["461.350", "180.819"])]))
    receiver = _omitted_sender_receiver(columns=_columns([None], [None]), unit=None)
    receiver["sections"][0]["tables"][0]["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"
    if mutation == "sender_not_owned":
        sender["sections"][0]["tables"][0]["title_exact"] = None
    elif mutation == "sender_qualified_title":
        sender["sections"][0]["tables"][0]["title_exact"] += " của công ty con"
    elif mutation == "missing_receiver_marker":
        receiver["sections"][0]["tables"][0]["continuation"] = "NONE"
    elif mutation == "receiver_local_header":
        receiver["sections"][0]["tables"][0]["columns"] = _columns()
    elif mutation == "sender_unit_missing":
        sender["sections"][0]["tables"][0]["unit_exact"] = None
    elif mutation == "sender_period_missing":
        sender["sections"][0]["tables"][0]["columns"] = _columns([None], [None])
    elif mutation == "receiver_wrong_unit":
        receiver["sections"][0]["tables"][0]["unit_exact"] = "VND"
    prior = _record(sender, version=PRIMARY_VERSION, physical_page=2, selected_page_ordinal=1)
    current = _record(receiver, physical_page=3, selected_page_ordinal=2)
    if mutation == "physical_gap":
        prior["physical_page"] = 1
    elif mutation == "selected_gap":
        prior["selected_page_ordinal"] = 0
    elif mutation == "different_source":
        prior["source_sha256"] = "e" * 64
    compiled = _compiled()
    # Actual source coalescer on the role-rich receiver; the full selected page
    # axis below still contains the sender. No financial/query function is mocked.
    cluster = family.coalesce_gemini_json_interest_income_document_v1(
        page_records=[current], compiled_specs=compiled,
    )
    assert cluster["status"] == READY
    records = [prior, current]
    inventory_cluster = family.coalesce_gemini_json_interest_income_document_v1(
        page_records=records, compiled_specs=compiled,
    )
    cluster["declared_money_table_inventory"] = inventory_cluster["declared_money_table_inventory"]
    cluster["cluster_id"] = "gjmthfcv1:cluster:" + canonical_json_sha256_v1({key: value for key, value in cluster.items() if key != "cluster_id"})
    indexed = _indexed_query_evidence(cluster=cluster, records=records, compiled=compiled)
    pages = {PRIMARY_VERSION: sender, NOTE_VERSION: receiver}
    original = deepcopy(pages)
    adapted, proofs = family.adapt_gemini_json_interest_income_indexed_query_evidence_v1(
        indexed, page_json_by_document={1: pages}, compiled_specs=compiled,
    )
    return adapted, proofs, pages, original, compiled


def test_source_owned_previous_sender_is_recovered_before_financial_evaluation():
    adapted, proofs, pages, original, compiled = _recovered_pair()
    cluster = adapted["accepted_clusters"][0]
    assert len(proofs) == 1 and len(cluster["component_regions"]) == 2
    assert [item["fragment_ordinal"] for item in cluster["component_regions"]] == [1, 2]
    options = {"regions": cluster["component_regions"], "page_json_by_version": pages, "compiled_specs": compiled,
               "query_receipt": family.build_gemini_json_interest_income_region_query_receipt_v1(cluster["component_regions"])}
    actual = family.evaluate_gemini_json_interest_income_family_cluster_v1(**options)
    assert actual["status"] == READY
    assert [cell["coefficient"] for cell in _root(actual)["values"]] == [2739236, 2236509]
    assert _root(actual)["source_refs"][0]["locator"]["page_json_version_id"] == NOTE_VERSION
    assert _root(actual)["source_refs"][0]["row_ordinal"] == 6
    deposit = next(item for item in actual["mappings"] if item["role"] == "DEPOSIT_INTEREST")
    assert [cell["source_text"] for cell in deposit["values"]] == ["461.350", "180.819"]
    assert family.validate_gemini_json_interest_income_family_candidate_replay_v1(actual, **options) == actual
    assert pages == original


@pytest.mark.parametrize("mutation", ["sender_not_owned", "sender_qualified_title", "missing_receiver_marker",
    "receiver_local_header", "sender_unit_missing", "sender_period_missing", "receiver_wrong_unit", "physical_gap"])
def test_adjacency_or_amount_closure_never_replaces_the_required_source_edge(mutation):
    adapted, proofs, pages, original, _compiled_specs = _recovered_pair(mutation)
    assert proofs == []
    assert len(adapted["accepted_clusters"][0]["component_regions"]) == 1
    assert pages == original


@pytest.mark.parametrize("mutation", ["selected_gap", "different_source"])
def test_invalid_selected_source_axes_are_rejected_before_continuation_authority(mutation):
    with pytest.raises(ValueError):
        _recovered_pair(mutation)


def test_role_only_owner_cannot_mint_root_even_when_its_local_sum_matches():
    rows = _interest_rows()
    rows[-1]["values_exact"] = ["35", "24"]
    page = _page(_table(rows, title=None))
    page["sections"][0]["title_exact"] = None
    original = deepcopy(page)
    old, actual, _options = _candidate(page)
    assert old["status"] == READY
    assert actual["status"] == UNRESOLVED and actual["mappings"] == []
    assert "F28_FAMILY_ROOT_SOURCE_OWNER_NOT_PROVEN" in actual["reasons"]
    assert page == original


def _note_and_primary(*, note_unit, primary_unit, primary_columns=None):
    rows = _interest_rows()
    rows[-1]["values_exact"] = ["35", "24"]
    note = _page(_table(rows, unit=note_unit))
    primary = _page(_table([
        _row("Thu nhập lãi và các khoản thu nhập tương tự", ["35", "24"]),
    ], title="Báo cáo kết quả hoạt động kinh doanh", unit=primary_unit, columns=primary_columns),
        status="PRIMARY_FINANCIAL_STATEMENT")
    original = deepcopy([note, primary])
    _cluster, actual = _cluster_and_candidate(
        compiled=_compiled(), pages={PRIMARY_VERSION: primary, NOTE_VERSION: note},
        records=[_record(primary, version=PRIMARY_VERSION, physical_page=1, selected_page_ordinal=1), _record(note)],
    )
    assert [note, primary] == original
    return actual


def test_unique_same_document_primary_unit_cannot_fill_a_missing_note_unit():
    actual = _note_and_primary(note_unit=None, primary_unit="Triệu đồng")
    assert actual["status"] == UNRESOLVED and actual["mappings"] == []
    assert "F28_NOTE_UNIT_SOURCE_OWNERSHIP_NOT_PROVEN" in actual["reasons"]
    assert actual["closure_receipt"]["interest_income_adapter_receipt"]["unit_corroboration_receipts"] == []
    # Without numeric unit donation the shared candidate already has no
    # mappings. The guard records the missing ownership without inventing a
    # withheld before-image that never existed.
    assert _retired(_control(actual)["withheld_mapping_evidence"]) == []
    assert _control(actual)["fragments"][0]["source_unit_evidence"] is None


def test_numeric_primary_match_cannot_override_an_independently_printed_note_unit():
    actual = _note_and_primary(note_unit="Triệu đồng", primary_unit="VND")
    assert actual["status"] == READY
    assert {mapping["unit"] for mapping in actual["mappings"]} == {"MILLION_VND"}
    assert actual["closure_receipt"]["interest_income_adapter_receipt"]["unit_corroboration_receipts"] == []


def test_other_primary_period_cannot_supply_even_a_corroboration_receipt():
    actual = _note_and_primary(note_unit="Triệu đồng", primary_unit="Triệu đồng",
        primary_columns=_columns(["Từ ngày 01/01/2026 đến ngày 31/03/2026"], ["Từ ngày 01/01/2025 đến ngày 31/03/2025"]))
    assert actual["status"] == READY
    assert actual["closure_receipt"]["interest_income_adapter_receipt"]["unit_corroboration_receipts"] == []


def test_unit_printed_in_this_note_columns_does_not_require_table_unit_mutation():
    rows = _interest_rows()
    rows[-1]["values_exact"] = ["35", "24"]
    columns = _columns()
    for column in columns:
        column["header_path_exact"].append("Triệu đồng")
    page = _page(_table(rows, columns=columns, unit=None))
    original = deepcopy(page)
    _old, actual, _options = _candidate(page)
    assert actual["status"] == READY
    assert {mapping["unit"] for mapping in actual["mappings"]} == {"MILLION_VND"}
    assert _control(actual)["fragments"][0]["source_unit_evidence"]["source_kind"] == "EXACT_FRAGMENT_LOCAL_PRINTED_UNIT"
    assert page == original


@pytest.mark.parametrize("held", [False, True])
def test_full_candidate_source_observation_audit_counts_only_active_mappings(held):
    rows = _interest_rows()
    if not held:
        rows[-1]["values_exact"] = ["35", "24"]
    _old, actual, _options = _candidate(_page(_table(rows)))
    audit = validate_source_observation_mapping_contract_v1(actual)
    assert audit["mapping_count"] == len(actual["mappings"])
    if held:
        assert actual["status"] == UNRESOLVED and audit["mapping_count"] == 0
    else:
        assert actual["status"] == READY and audit["mapping_count"] > 0


@pytest.mark.parametrize("held", [False, True])
def test_superseded_global_root_authority_is_retired_but_local_equations_survive(held):
    rows = _interest_rows()
    if not held:
        rows[-1]["values_exact"] = ["35", "24"]
    old, actual, _options = _candidate(_page(_table(rows)))
    retired = _retired(_control(actual)["retired_global_root_authority"])
    kind = "EXACT_COMPLETE_TOP_LEVEL_COMPONENT_SUM_DERIVES_FAMILY_ROOT"
    assert actual["closure_receipt"]["equations"] == [item for item in old["closure_receipt"]["equations"] if item["equation_kind"] != kind]
    assert retired["global_root_equations"] == [item for item in old["closure_receipt"]["equations"] if item["equation_kind"] == kind]
    assert retired["root_component_sum_receipts"] == old["closure_receipt"]["root_component_sum_receipts"]
    assert actual["closure_receipt"]["root_component_sum_receipts"] == []
    structural = actual["closure_receipt"]["structural_root_receipt"]
    assert structural["source_root_control_receipt_id"] == _control(actual)["receipt_id"]
    if held:
        assert structural["emitted_mapping"] is False
        assert structural["active_permission"] == "NONE_HELD_BY_F28_SOURCE_ROOT_CONTROL"
    else:
        assert structural["source_root_mapping_id"] == _root(actual)["item_mapping_id"]
        assert structural["active_permission"] == "F28_SOURCE_OWNED_PRINTED_TOTAL_ROW"


@pytest.mark.parametrize("field", ["canonical_json_one_lf_utf8_text", "sha256", "size_bytes"])
def test_fresh_candidate_replay_rejects_resealed_retired_mapping_envelope_tamper(field):
    _old, actual, options = _candidate(_page(_table(_interest_rows())))
    forged = deepcopy(actual)
    envelope = _control(forged)["withheld_mapping_evidence"]
    if field == "canonical_json_one_lf_utf8_text":
        envelope[field] = envelope[field].replace("35", "36", 1)
        envelope["sha256"] = sha256(envelope[field].encode("utf-8")).hexdigest()
        envelope["size_bytes"] = len(envelope[field].encode("utf-8"))
    elif field == "sha256":
        envelope[field] = "0" * 64
    else:
        envelope[field] += 1
    control = _control(forged)
    control["receipt_id"] = "gjiifav1:source-root:" + canonical_json_sha256_v1({key: value for key, value in control.items() if key != "receipt_id"})
    adapter = forged["closure_receipt"]["interest_income_adapter_receipt"]
    adapter["adapter_receipt_id"] = "gjiifav1:receipt:" + canonical_json_sha256_v1({key: value for key, value in adapter.items() if key != "adapter_receipt_id"})
    forged["closure_receipt"]["structural_root_receipt"]["source_root_control_receipt_id"] = control["receipt_id"]
    forged["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1({key: value for key, value in forged.items() if key != "candidate_id"})
    with pytest.raises(family.GeminiJsonInterestIncomeFamilyV1Error, match="candidate replay drifted"):
        family.validate_gemini_json_interest_income_family_candidate_replay_v1(forged, **options)
