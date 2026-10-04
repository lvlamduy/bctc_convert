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
    _at_rate_cross_presentation_conflicts,
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


@pytest.mark.parametrize("label", [
    "Tổng lợi nhuận trước thuế\n(mang sang từ trang trước)",
    "Tổng lợi nhuận trước thuế\n(mang từ trang trước)",
    "XI. Tổng lợi nhuận trước thuế\n(mang sang từ trang trước)",
    "XI. Tổng lợi nhuận trước thuế\n(mang từ trang trước)",
])
def test_exact_printed_carry_forward_profit_row_is_observed_not_backsolved(label):
    records = _records()
    row = records[-1]["page_json"]["sections"][0]["tables"][0]["rows"][0]
    row["label_exact"] = label
    row["hierarchy_path_exact"] = [label]
    before = deepcopy(records)
    candidate = _candidate(records)
    assert candidate["status"] == READY
    assert records == before
    bridge = candidate["closure_receipt"]["income_tax_adapter_receipt"]["primary_projection_receipt"]["expense_display_receipt"]
    assert bridge["before_source_row"]["source_row"]["label_exact"] == label
    assert bridge["before_source_row"]["source_row"]["values_exact"] == ["30", "40", "100", "80"]
    assert bridge["missing_root_created"] is False
    assert bridge["source_values_changed"] is False


@pytest.mark.parametrize("label", [
    "Tổng lợi nhuận trước thuế (Ngân hàng mẹ)",
    "Tổng lợi nhuận trước thuế (công ty con)",
    "Tổng lợi nhuận trước thuế (mang từ trang trước, đã điều chỉnh)",
    "Tổng lợi nhuận trước thuế (mang sang từ trang trước) sau điều chỉnh",
    "Lợi nhuận sau thuế (mang từ trang trước)",
    "Tổng lợi nhuận trước thuế (ước tính)",
])
def test_carry_forward_allowlist_does_not_strip_other_population_or_qualifier(label):
    records = _records()
    row = records[-1]["page_json"]["sections"][0]["tables"][0]["rows"][0]
    row["label_exact"] = label
    row["hierarchy_path_exact"] = [label]
    candidate = _candidate(records)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["reasons"] == ["SIGN_INVERTED_DIRECT_NOTE_AND_PRIMARY_INCOME_TAX_PRESENTATIONS"]


@pytest.mark.parametrize("label", ["Năm hiện hành", "I. Năm hiện hành"])
@pytest.mark.parametrize("include_primary", [True, False])
def test_current_year_expense_cannot_be_added_to_explicit_rate_base_even_if_parent_closes(label, include_primary):
    records = _records()
    note = records[0]["page_json"]["sections"][0]["tables"][0]["rows"]
    note.insert(1, _row(label, "19", "16"))
    next(row for row in note if row["label_exact"] == "Chi phí thuế TNDN hiện hành")["values_exact"] = ["39", "32"]
    next(row for row in note if row["label_exact"] == "Chi phí thuế thu nhập doanh nghiệp")["values_exact"] = ["41", "33"]
    primary = records[-1]["page_json"]["sections"][0]["tables"][0]["rows"]
    primary[1]["values_exact"][-2:] = ["(39)", "(32)"]
    primary[3]["values_exact"][-2:] = ["(41)", "(33)"]
    primary[-1]["values_exact"][-2:] = ["59", "47"]
    if not include_primary:
        records.pop()
    original = deepcopy(records)
    candidate = _candidate(records)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["reasons"] == ["CURRENT_TAX_AT_RATE_CROSS_PRESENTATION_POPULATION_AMBIGUITY"]
    assert records == original
    proof = candidate["closure_receipt"]["income_tax_unresolved_evidence_receipt"]["evidence"]["at_rate_population_conflicts"][0]
    assert proof["classification"] == "ALGORITHM_ROLE_POPULATION_AMBIGUITY_NOT_GENUINE_SOURCE_CONFLICT"
    inventory = proof["population_inventory"]
    assert inventory["source_table_rows_exact"][1]["values_exact"] == ["19", "16"]
    assert inventory["source_table_row_axis"][1]["normalized_label"] == "nam hien hanh"
    assert len(inventory["explicit_rate_surface_ordinals"]) == len(inventory["current_year_surface_ordinals"]) == 1
    assert inventory["current_year_frontier"] is None


@pytest.mark.parametrize("qualified_row", [0, 1, 2, 3, 4])
def test_signed_profit_bridge_cannot_mix_a_qualified_population_with_unqualified_rows(qualified_row):
    records = _records()
    rows = records[-1]["page_json"]["sections"][0]["tables"][0]["rows"]
    row = rows[qualified_row]
    row["hierarchy_path_exact"] = ["Ngân hàng mẹ", row["label_exact"]]
    original = deepcopy(records)
    candidate = _candidate(records)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["reasons"] == ["SIGN_INVERTED_DIRECT_NOTE_AND_PRIMARY_INCOME_TAX_PRESENTATIONS"]
    assert records == original


def test_signed_profit_bridge_rejects_explicit_different_profit_populations():
    records = _records()
    rows = records[-1]["page_json"]["sections"][0]["tables"][0]["rows"]
    rows[0]["hierarchy_path_exact"] = ["Ngân hàng mẹ", rows[0]["label_exact"]]
    rows[-1]["hierarchy_path_exact"] = ["Công ty con", rows[-1]["label_exact"]]
    assert _candidate(records)["status"] == UNRESOLVED


def test_signed_profit_bridge_retains_equal_explicit_population_ancestry():
    records = _records()
    rows = records[-1]["page_json"]["sections"][0]["tables"][0]["rows"]
    for row in rows:
        row["hierarchy_path_exact"] = ["Ngân hàng mẹ", row["label_exact"]]
    before = deepcopy(records)
    descriptor = _primary_presentations(records, compiled_specs=_adapter_compiled())[0]
    bridge = descriptor["expense_display_receipt"]
    assert bridge is not None
    assert bridge["population_ancestry_receipt"]["common_normalized_ancestry"] == ["ngan hang me"]
    assert records == before


def test_standalone_printed_roman_ordinals_are_not_different_profit_populations():
    records = _records()
    rows = records[-1]["page_json"]["sections"][0]["tables"][0]["rows"]
    for row, ordinal in zip(rows, ["XI", "XII", "XII", "XII", "XIII"], strict=True):
        row["hierarchy_path_exact"] = [ordinal, row["label_exact"]]
    original = deepcopy(records)
    candidate = _candidate(records)
    assert candidate["status"] == READY
    assert records == original


@pytest.mark.parametrize("path", [[], None, ["Ngân hàng mẹ"], ["", "Tổng lợi nhuận trước thuế"]])
def test_profit_population_bridge_does_not_accept_missing_or_malformed_source_ancestry(path):
    records = _records()
    row = records[-1]["page_json"]["sections"][0]["tables"][0]["rows"][0]
    row["hierarchy_path_exact"] = path
    assert _primary_presentations(records, compiled_specs=_adapter_compiled())[0]["expense_display_receipt"] is None


def test_profit_population_prefix_is_not_equal_to_its_subsidiary_population():
    records = _records()
    rows = records[-1]["page_json"]["sections"][0]["tables"][0]["rows"]
    for row in rows:
        row["hierarchy_path_exact"] = ["Ngân hàng mẹ", row["label_exact"]]
    rows[-1]["hierarchy_path_exact"].insert(1, "Công ty con")
    assert _candidate(records)["status"] == UNRESOLVED


@pytest.mark.parametrize("before_scope,after_scope", [("2024", "2025"), ("1", "2"), ("123456", "654321"), ("Entity A-B", "Entity A/B")])
def test_numeric_year_or_entity_identifier_is_not_a_discardable_population_ordinal(before_scope, after_scope):
    records = _records()
    rows = records[-1]["page_json"]["sections"][0]["tables"][0]["rows"]
    for row in rows:
        row["hierarchy_path_exact"] = [after_scope, row["label_exact"]]
    rows[0]["hierarchy_path_exact"] = [before_scope, rows[0]["label_exact"]]
    assert _candidate(records)["status"] == UNRESOLVED


def test_note_and_primary_explicit_different_populations_cannot_prove_opposite_tax_display():
    records = _records()
    for row in records[0]["page_json"]["sections"][0]["tables"][0]["rows"]:
        row["hierarchy_path_exact"] = ["Công ty con", row["label_exact"]]
    for row in records[-1]["page_json"]["sections"][0]["tables"][0]["rows"]:
        row["hierarchy_path_exact"] = ["Ngân hàng mẹ", row["label_exact"]]
    original = deepcopy(records)
    assert _candidate(records)["status"] == UNRESOLVED
    assert records == original


@pytest.mark.parametrize("mutation", [None, "missing_group", "wrong_group_kind", "later_group", "different_population"])
def test_only_an_actual_preceding_root_tax_group_can_explain_tax_row_ancestry(mutation):
    records = _records()
    rows = records[-1]["page_json"]["sections"][0]["tables"][0]["rows"]
    group = rows[3]
    group["row_kind"] = "GROUP"
    rows.insert(1, rows.pop(3))
    for row in rows[2:4]:
        row["hierarchy_path_exact"] = [group["label_exact"], row["label_exact"]]
    if mutation == "missing_group":
        rows.remove(group)
    elif mutation == "wrong_group_kind":
        group["row_kind"] = "TOTAL"
    elif mutation == "later_group":
        rows.insert(4, rows.pop(1))
    elif mutation == "different_population":
        rows[2]["hierarchy_path_exact"].insert(0, "Công ty con")
    original = deepcopy(records)
    descriptor = _primary_presentations(records, compiled_specs=_adapter_compiled())[0]
    bridge = descriptor["expense_display_receipt"]
    if mutation is None:
        assert bridge is not None
        population = bridge["population_ancestry_receipt"]
        assert population["common_normalized_ancestry"] == []
        assert population["structural_tax_group_sources"][0]["source_row"] == group
        assert _candidate(records)["status"] == READY
    else:
        assert bridge is None
    assert records == original


def test_note_ancestry_can_only_remove_the_actual_declared_tax_owner_surface():
    records = _records()
    section = records[0]["page_json"]["sections"][0]
    owner = section["title_exact"]
    for row in section["tables"][0]["rows"]:
        row["hierarchy_path_exact"] = [owner, row["label_exact"]]
    original = deepcopy(records)
    candidate = _candidate(records)
    assert candidate["status"] == READY
    signed = candidate["closure_receipt"]["income_tax_adapter_receipt"]["primary_candidate_proof"]["signed_display_proof"]
    assert all(item["population_ancestry_receipt"]["structural_owner_sources"] for item in signed["note_source_tables"])
    assert records == original


@pytest.mark.parametrize("scope", ["Ngân hàng mẹ", "Chi phí thuế TNDN ghi nhận trong báo cáo kết quả hoạt động riêng giữa niên độ:"])
def test_note_qualifiers_cannot_be_discarded_as_unobserved_tax_owner_aliases(scope):
    records = _records()
    for row in records[0]["page_json"]["sections"][0]["tables"][0]["rows"]:
        row["hierarchy_path_exact"] = [scope, row["label_exact"]]
    assert _candidate(records)["status"] == UNRESOLVED


def test_resealed_population_receipt_does_not_replace_original_source_ancestry():
    records = _records()
    compiled = _adapter_compiled()
    cluster, receipt = _query(records, compiled)
    adapter = receipt["adapter_receipt"]
    bridge = adapter["primary_projection_receipt"]["expense_display_receipt"]
    population = bridge["population_ancestry_receipt"]
    population["common_population_ancestry_exact"] = ["Ngân hàng mẹ"]
    for value, prefix, key in (
        (population, "gjitfav1:bridge-population:", "receipt_id"),
        (bridge, "gjitfav1:expense-display:", "receipt_id"),
        (adapter, "gjitfav1:query:", "receipt_id"),
        (receipt, "gjitfav1:query-receipt:", "query_receipt_id"),
    ):
        value[key] = prefix + canonical_json_sha256_v1({name: item for name, item in value.items() if name != key})
    with pytest.raises(GeminiJsonIncomeTaxFamilyV1Error, match="drifted"):
        _evaluate_query(records, compiled, cluster, receipt)


@pytest.mark.parametrize("use_owner_ancestry", [True, False])
@pytest.mark.parametrize("qualifier", ["Công ty con", "Ngân hàng mẹ", "Hợp nhất"])
def test_tax_owner_alias_line_does_not_erase_another_printed_population_qualifier(use_owner_ancestry, qualifier):
    records = _records()
    section = records[0]["page_json"]["sections"][0]
    owner = section["title_exact"]
    section["title_exact"] = owner + "\n" + qualifier
    if use_owner_ancestry:
        for row in section["tables"][0]["rows"]:
            row["hierarchy_path_exact"] = [owner, row["label_exact"]]
    original = deepcopy(records)
    assert _candidate(records)["status"] == UNRESOLVED
    assert records == original


def test_equal_explicit_population_titles_remain_bound_without_changing_source():
    records = _records()
    for record in records:
        section = record["page_json"]["sections"][0]
        section["title_exact"] += "\nNgân hàng mẹ"
    original = deepcopy(records)
    candidate = _candidate(records)
    assert candidate["status"] == READY
    proof = candidate["closure_receipt"]["income_tax_adapter_receipt"]["primary_candidate_proof"]["signed_display_proof"]
    assert all(item["printed_population_scope_receipt"]["note_scope"] == ["PARENT_ENTITY"] for item in proof["note_source_tables"])
    assert records == original


@pytest.mark.parametrize("labels", [
    ["Chi phí thuế TNDN theo thuế suất"], ["Năm hiện hành"],
    ["Chi phí thuế TNDN theo thuế suất", "Điều chỉnh khác"],
])
def test_at_rate_guard_is_not_a_generic_duplicate_or_label_substring_veto(labels):
    candidate = {"mappings": [{"role": "CURRENT_TAX_AT_RATE", "source_refs": [{"label_exact": label} for label in labels]}]}
    assert _at_rate_cross_presentation_conflicts(candidate, compiled_specs=_adapter_compiled()) == []
