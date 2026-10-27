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
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import validate_source_observation_mapping_contract_v1
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
    # The independent guard must actually withhold any global-unit result the
    # shared engine supplied, not merely rely on the old clone mutation going away.
    assert _retired(_control(actual)["withheld_mapping_evidence"])
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
