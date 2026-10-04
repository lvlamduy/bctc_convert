from __future__ import annotations

from copy import deepcopy

import pytest
from test_gemini_json_income_tax_family_v1 import (
    _adapter_compiled,
    _page,
    _primary_page,
    _primary_record,
    _primary_tax_rows,
    _record,
    _row,
)
from test_gemini_json_income_tax_root_controls_v1 import _evaluate_query

from bctc_ai.evaluation.gemini_json_income_tax_family_v1 import (
    GeminiJsonIncomeTaxFamilyV1Error,
    _authenticated_root_comparison_orientations,
    _post_merge_root_closure,
    _primary_presentations,
    build_gemini_json_income_tax_region_query_receipt_v1,
    recover_gemini_json_income_tax_query_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _records(*, note_root: bool = True, note_deferred: bool = True):
    note_rows = [
        _row("Chi phí thuế TNDN theo thuế suất", "20", "16"),
        _row("Chi phí thuế TNDN hiện hành", "20", "16"),
    ]
    if note_deferred:
        note_rows.append(_row("Chi phí thuế thu nhập doanh nghiệp hoãn lại", "2", "1"))
    if note_root:
        note_rows.append(_row("Chi phí thuế thu nhập doanh nghiệp", "22", "17", kind="TOTAL"))
    tax_rows = _primary_tax_rows(current=("(20)", "(16)"), deferred=("(2)", "(1)"), root=("(22)", "(17)"))
    before = {**_row("Tổng lợi nhuận trước thuế", "100", "80"), "values_exact": ["30", "40", "100", "80"]}
    after = {**_row("Lợi nhuận sau thuế", "78", "63"), "values_exact": ["25", "35", "78", "63"]}
    primary = _primary_page([before, *tax_rows, after])
    return [
        _record(_page(note_rows)),
        _primary_record(primary, page_json_version_id="gfpstorev1:json:" + "d" * 64,
                        physical_page=2, selected_page_ordinal=2),
    ]


def _query(records, compiled):
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled,
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled,
    )
    assert cluster["status"] == READY, cluster["reasons"]
    return cluster, build_gemini_json_income_tax_region_query_receipt_v1(
        cluster["component_regions"], cluster=cluster,
    )


def _candidate(records):
    compiled = _adapter_compiled()
    cluster, receipt = _query(records, compiled)
    return _evaluate_query(records, compiled, cluster, receipt)


@pytest.mark.parametrize("note_root,note_deferred", [(True, True), (False, True), (False, False), (True, False)])
def test_signed_display_preserves_all_printed_values_and_checks_comparison_only(note_root, note_deferred):
    records = _records(note_root=note_root, note_deferred=note_deferred)
    before = deepcopy(records)
    candidate = _candidate(records)
    assert candidate["status"] == READY, candidate["reasons"]
    assert records == before
    roles = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [cell["coefficient"] for cell in roles["CURRENT_TAX_PARENT"]["values"]] == [20, 16]
    assert [cell["coefficient"] for cell in roles["FAMILY_ROOT_TOTAL"]["values"]] == [-22, -17]
    assert [cell["coefficient"] for cell in roles["DEFERRED_TAX_NET"]["values"]] == ([2, 1] if note_deferred else [-2, -1])
    proof = candidate["closure_receipt"]["income_tax_adapter_receipt"]["primary_candidate_proof"]
    signed = proof["signed_display_proof"]
    material = {key: value for key, value in signed.items() if key != "receipt_id"}
    assert signed["receipt_id"] == "gjitfav1:signed-display:" + canonical_json_sha256_v1(material)
    assert signed["source_values_changed"] is False
    assert len(signed["independent_nonroot_overlaps"]) == (2 if note_deferred else 1)
    closure = proof["post_merge_root_closure"]
    assert closure["status"] == "EXACT_ALL_OBSERVED_LANES"
    assert all(lane["residual_vnd"] == 0 for lane in closure["lane_receipts"])
    assert closure["source_mapping_values_unchanged"] is True


@pytest.mark.parametrize("mutation", ["before_blank", "after_blank", "bad_after", "bad_before", "duplicate_before", "duplicate_after", "missing_before", "missing_after", "wrong_after_semantics", "reordered_anchors"])
def test_signed_display_requires_unique_observed_independent_profit_bridge(mutation):
    records = _records()
    rows = records[-1]["page_json"]["sections"][0]["tables"][0]["rows"]
    if mutation == "before_blank":
        rows[0]["values_exact"][-1] = None
    elif mutation == "after_blank":
        rows[-1]["values_exact"][-1] = None
    elif mutation == "bad_after":
        rows[-1]["values_exact"][-1] = "64"
    elif mutation == "bad_before":
        rows[0]["values_exact"][-1] = "81"
    elif mutation == "duplicate_before":
        rows.insert(0, deepcopy(rows[0]))
    elif mutation == "duplicate_after":
        rows.append(deepcopy(rows[-1]))
    elif mutation == "missing_before":
        rows.pop(0)
    elif mutation == "missing_after":
        rows.pop()
    elif mutation == "wrong_after_semantics":
        rows[-1]["label_exact"] = "Lợi nhuận sau thuế của cổ đông không kiểm soát"
    else:
        rows[0], rows[-1] = rows[-1], rows[0]
    candidate = _candidate(records)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["reasons"] == ["SIGN_INVERTED_DIRECT_NOTE_AND_PRIMARY_INCOME_TAX_PRESENTATIONS"]


def test_profit_bridge_is_bound_to_original_source_table_and_final_duration_columns():
    records = _records()
    descriptor = _primary_presentations(records, compiled_specs=_adapter_compiled())[0]
    bridge = descriptor["expense_display_receipt"]
    assert bridge["money_column_ordinals"] == [3, 4]
    assert bridge["original_table_json_sha256"] == descriptor["original_table_json_sha256"]
    assert bridge["before_source_row"]["source_row"]["values_exact"] == ["30", "40", "100", "80"]
    assert bridge["lane_receipts"][0] == {"lane_ordinal": 0, "before": 100, "signed_expense": -22, "after": 78, "residual": 0}


def test_query_cannot_reseal_a_forged_profit_bridge_without_actual_source_change():
    records = _records()
    compiled = _adapter_compiled()
    cluster, receipt = _query(records, compiled)
    changed = deepcopy(records)
    changed[-1]["page_json"]["sections"][0]["tables"][0]["rows"][-1]["values_exact"][-1] = "64"
    with pytest.raises(GeminiJsonIncomeTaxFamilyV1Error, match="drifted"):
        _evaluate_query(changed, compiled, cluster, receipt)


def test_magnitude_match_is_not_enough_when_note_profit_before_tax_conflicts():
    records = _records()
    rows = records[0]["page_json"]["sections"][0]["tables"][0]["rows"]
    rows.insert(0, _row("Lợi nhuận kế toán trước thuế", "101", "80"))
    candidate = _candidate(records)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


@pytest.mark.parametrize("lane", [0, 1])
def test_opposite_amounts_from_a_different_source_year_cannot_prove_signed_display(lane):
    records = _records()
    table = records[0]["page_json"]["sections"][0]["tables"][0]
    table["columns"][lane]["header_path_exact"] = ["Năm 2024", "Triệu đồng"]
    candidate = _candidate(records)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


@pytest.mark.parametrize("corruption", ["adapter_hash", "signed_hash", "closure_hash", "mapping_axis", "orientation"])
def test_final_closure_rejects_forged_signed_comparison_receipts(corruption):
    candidate = _candidate(_records())
    assert candidate["status"] == READY
    adapter = candidate["closure_receipt"]["income_tax_adapter_receipt"]
    merged = deepcopy(candidate)
    merged["closure_receipt"]["income_tax_adapter_receipt"] = adapter
    proof = adapter["primary_candidate_proof"]
    if corruption == "adapter_hash":
        adapter["receipt_id"] = "gjitfav1:candidate:" + "0" * 64
    elif corruption == "signed_hash":
        proof["signed_display_proof"]["receipt_id"] = "gjitfav1:signed-display:" + "0" * 64
    elif corruption == "closure_hash":
        proof["post_merge_root_closure"]["receipt_id"] = "gjitfav1:post-merge-root-closure:" + "0" * 64
    elif corruption == "mapping_axis":
        current = next(mapping for mapping in merged["mappings"] if mapping["role"] == "CURRENT_TAX_PARENT")
        current["values"][0]["coefficient"] += 1
    else:
        proof["source_presentation_comparison_orientations"]["CURRENT_TAX_PARENT"] = 1
    with pytest.raises(GeminiJsonIncomeTaxFamilyV1Error, match="drifted"):
        _authenticated_root_comparison_orientations(merged)


@pytest.mark.parametrize("sign", [0, 2, True, "-1"])
def test_root_comparison_rejects_invalid_orientation_coefficients(sign):
    with pytest.raises(GeminiJsonIncomeTaxFamilyV1Error, match="invalid"):
        _post_merge_root_closure({"mappings": []}, comparison_orientations={"CURRENT_TAX_PARENT": sign})


def test_resealed_query_still_cannot_replace_the_actual_printed_profit_bridge():
    records = _records()
    compiled = _adapter_compiled()
    cluster, receipt = _query(records, compiled)
    adapter = receipt["adapter_receipt"]
    bridge = adapter["primary_projection_receipt"]["expense_display_receipt"]
    bridge["lane_receipts"][0]["before"] += 1
    for value, prefix, key in (
        (bridge, "gjitfav1:expense-display:", "receipt_id"),
        (adapter, "gjitfav1:query:", "receipt_id"),
        (receipt, "gjitfav1:query-receipt:", "query_receipt_id"),
    ):
        material = {name: item for name, item in value.items() if name != key}
        value[key] = prefix + canonical_json_sha256_v1(material)
    with pytest.raises(GeminiJsonIncomeTaxFamilyV1Error, match="drifted"):
        _evaluate_query(records, compiled, cluster, receipt)
