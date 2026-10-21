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


def _contextual_period_records(*, quarter="III", scope="riêng", include_cash_flow=True, absolute_primary=False):
    """All period/scope authority is printed in source cells, never the filename."""
    records = _records()
    note_section = records[0]["page_json"]["sections"][0]
    note_section["title_exact"] += " " + scope
    primary_section = records[1]["page_json"]["sections"][0]
    primary_section["title_exact"] = "Báo cáo kết quả hoạt động " + scope
    note_table = note_section["tables"][0]
    primary_table = primary_section["tables"][0]
    years = ("2026", "2025")
    relative_years = ("Năm nay", "Năm trước")
    months = {"I": 3, "II": 6, "III": 9, "IV": 12}[quarter]
    endpoint = {"I": "31/3/", "II": "30/6/", "III": "30/9/"}.get(quarter)
    absolute_columns = [
        {"value_kind": "MONEY", "header_path_exact": (
            ["Năm " + year, "Triệu đồng"] if quarter == "IV" else
            ["Kỳ " + str(months) + " tháng kết thúc ngày", endpoint + year, "Triệu đồng"]
        )} for year in years
    ]
    note_table["columns"] = deepcopy(absolute_columns)
    primary_table["columns"] = [
        {"value_kind": "MONEY", "header_path_exact": ["Quý " + quarter, label]}
        for label in (("Năm " + year for year in years) if absolute_primary else relative_years)
    ] + [
        {"value_kind": "MONEY", "header_path_exact": ["Lũy kế từ đầu năm", label]}
        for label in (("Năm " + year for year in years) if absolute_primary else relative_years)
    ]
    if include_cash_flow:
        cash_flow = _primary_page([_row("Lưu chuyển tiền thuần từ hoạt động kinh doanh", "7", "8")])
        cash_flow_section = cash_flow["sections"][0]
        cash_flow_section["statement_type"] = "CASH_FLOW"
        cash_flow_section["title_exact"] = "Báo cáo lưu chuyển tiền tệ " + scope
        cash_flow_section["tables"][0]["columns"] = deepcopy(absolute_columns)
        records.append(_primary_record(
            cash_flow, page_json_version_id="gfpstorev1:json:" + "e" * 64,
            physical_page=3, selected_page_ordinal=3,
        ))
    return records


def _contextual_period_locator(record):
    return {key: deepcopy(value) for key, value in record.items() if key != "page_json"} | {
        "section_id": "s1", "table_id": "t1",
    }


def _contextual_period_proof(records, *, same_primary=False, inventory=None):
    from bctc_ai.evaluation.gemini_json_income_tax_family_v1 import (
        _document_statement_period_inventory,
        _source_period_correspondence_receipt,
    )

    compiled = _adapter_compiled()
    if inventory is None:
        inventory = _document_statement_period_inventory(records, compiled_specs=compiled)
    return _source_period_correspondence_receipt(
        left_locator=_contextual_period_locator(records[1] if same_primary else records[0]),
        left_money_column_ordinals=[3, 4] if same_primary else [1, 2],
        right_locator=_contextual_period_locator(records[1]), right_money_column_ordinals=[3, 4],
        page_records=records, compiled_specs=compiled, document_period_inventory=inventory,
    )


@pytest.mark.parametrize("quarter", ["III", "IV"])
@pytest.mark.parametrize("scope", ["riêng", "hợp nhất"])
def test_contextual_period_signed_display_uses_same_scope_cash_flow_absolute_periods(quarter, scope):
    records = _contextual_period_records(quarter=quarter, scope=scope)
    original = deepcopy(records)
    proof = _contextual_period_proof(records)
    assert proof["complete"] is True, proof["reasons"]
    assert proof["status"].startswith("PASS_")
    assert proof["start_dates_inferred"] is False
    assert proof["source_period_keys_modified"] is False
    assert proof["amounts_used_as_authority"] is False
    candidate = _candidate(records)
    assert candidate["status"] == READY, candidate["reasons"]
    mappings = {item["role"]: item for item in candidate["mappings"]}
    assert [cell["source_text"] for cell in mappings["CURRENT_TAX_PARENT"]["values"]] == ["20", "16"]
    assert [cell["source_text"] for cell in mappings["FAMILY_ROOT_TOTAL"]["values"]] == ["(22)", "(17)"]
    assert records == original


@pytest.mark.parametrize("quarter", ["I", "II", "III", "IV"])
def test_contextual_period_relative_primary_self_comparison_needs_real_absolute_anchor(quarter):
    records = _contextual_period_records(quarter=quarter)
    proof = _contextual_period_proof(records, same_primary=True)
    assert proof["complete"] is True, proof["reasons"]
    records.pop()
    missing = _contextual_period_proof(records, same_primary=True)
    assert missing["complete"] is False
    assert missing["status"] == "ALGORITHM_HOLD"
    assert missing["start_dates_inferred"] is False


def test_contextual_period_absolute_qiv_ytd_axis_has_intrinsic_annual_authority_without_cash_flow():
    records = _contextual_period_records(quarter="IV", include_cash_flow=False, absolute_primary=True)
    original = deepcopy(records)
    proof = _contextual_period_proof(records)
    assert proof["complete"] is True, proof["reasons"]
    assert proof["start_dates_inferred"] is False
    assert proof["source_period_keys_modified"] is False
    candidate = _candidate(records)
    assert candidate["status"] == READY, candidate["reasons"]
    assert records == original


@pytest.mark.parametrize("mutation", [
    "missing_cash_flow", "cash_flow_wrong_scope", "cash_flow_entity_override", "cash_flow_quarter_only",
    "cash_flow_duplicate_year", "cash_flow_wrong_endpoint", "cash_flow_no_duration", "income_quarter_conflict",
    "income_quarter_only", "income_reversed_relative_lanes", "income_unknown_relative_label", "filename_only",
])
def test_contextual_period_matching_amounts_cannot_replace_printed_period_or_population_proof(mutation):
    records = _contextual_period_records()
    primary_table = records[1]["page_json"]["sections"][0]["tables"][0]
    cash_flow_section = records[2]["page_json"]["sections"][0]
    cash_flow_table = cash_flow_section["tables"][0]
    if mutation == "missing_cash_flow":
        records.pop()
    elif mutation == "cash_flow_wrong_scope":
        cash_flow_section["title_exact"] = "Báo cáo lưu chuyển tiền tệ hợp nhất"
    elif mutation == "cash_flow_entity_override":
        cash_flow_section["title_exact"] += " của Ngân hàng mẹ"
    elif mutation == "cash_flow_quarter_only":
        for column, year in zip(cash_flow_table["columns"], ("2026", "2025"), strict=True):
            column["header_path_exact"] = ["Quý III năm " + year, "Triệu đồng"]
    elif mutation == "cash_flow_duplicate_year":
        cash_flow_table["columns"][1] = deepcopy(cash_flow_table["columns"][0])
    elif mutation == "cash_flow_wrong_endpoint":
        for column, year in zip(cash_flow_table["columns"], ("2026", "2025"), strict=True):
            column["header_path_exact"] = ["Kỳ 6 tháng kết thúc ngày", "30/6/" + year, "Triệu đồng"]
    elif mutation == "cash_flow_no_duration":
        for column, year in zip(cash_flow_table["columns"], ("2026", "2025"), strict=True):
            column["header_path_exact"] = ["30/9/" + year, "Triệu đồng"]
    elif mutation == "income_quarter_conflict":
        primary_table["columns"][0]["header_path_exact"][0] = "Quý II"
    elif mutation == "income_quarter_only":
        for column in primary_table["columns"][2:]:
            column["header_path_exact"][0] = "Quý III"
    elif mutation == "income_reversed_relative_lanes":
        primary_table["columns"][2:4] = list(reversed(primary_table["columns"][2:4]))
    elif mutation == "income_unknown_relative_label":
        primary_table["columns"][2]["header_path_exact"][-1] = "Kỳ này"
    else:
        records.pop()
        for record in records:
            record["source_logical_name"] = "2026_9_thang_BCTC_rieng.pdf"
    original = deepcopy(records)
    proof = _contextual_period_proof(records)
    assert proof["complete"] is False
    assert proof["status"] == "ALGORITHM_HOLD"
    assert proof["amounts_used_as_authority"] is False
    candidate = _candidate(records)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert records == original


@pytest.mark.parametrize("contradictory", [False, True])
def test_contextual_period_all_same_scope_cash_flow_continuations_must_agree(contradictory):
    records = _contextual_period_records()
    continuation = deepcopy(records[2])
    continuation.update(page_json_version_id="gfpstorev1:json:" + "f" * 64,
                        physical_page=4, selected_page_ordinal=4)
    if contradictory:
        for column, year in zip(continuation["page_json"]["sections"][0]["tables"][0]["columns"], ("2026", "2025"), strict=True):
            column["header_path_exact"] = ["Kỳ 6 tháng kết thúc ngày", "30/6/" + year, "Triệu đồng"]
    records.append(continuation)
    original = deepcopy(records)
    proof = _contextual_period_proof(records)
    assert proof["complete"] is not contradictory
    candidate = _candidate(records)
    assert candidate["status"] == (UNRESOLVED if contradictory else READY), candidate["reasons"]
    if contradictory:
        assert candidate["mappings"] == []
    assert records == original


def test_contextual_period_self_resealed_inventory_cannot_replace_current_original_statement_headers():
    from bctc_ai.evaluation.gemini_json_income_tax_family_v1 import (
        _document_statement_period_inventory,
    )

    records = _contextual_period_records()
    compiled = _adapter_compiled()
    inventory = _document_statement_period_inventory(records, compiled_specs=compiled)
    changed = deepcopy(records)
    changed[2]["page_json"]["sections"][0]["tables"][0]["columns"][0]["header_path_exact"][1] = "30/9/2024"
    forged = deepcopy(inventory)
    forged["source_period_keys_modified"] = True
    if type(forged.get("receipt_id")) is str:
        prefix = forged["receipt_id"].rsplit(":", 1)[0] + ":"
        forged["receipt_id"] = prefix + canonical_json_sha256_v1({key: value for key, value in forged.items() if key != "receipt_id"})
    with pytest.raises(GeminiJsonIncomeTaxFamilyV1Error, match="drifted"):
        _contextual_period_proof(changed, inventory=forged)


def test_contextual_period_reordered_cash_flow_columns_keep_exact_printed_source_lane_selectors():
    records = _contextual_period_records()
    records[2]["page_json"]["sections"][0]["tables"][0]["columns"].reverse()
    original = deepcopy(records)
    proof = _contextual_period_proof(records)
    assert proof["complete"] is True, proof["reasons"]
    anchors = [anchor for resolution in proof["period_resolution_evidence"] for anchor in resolution["cash_flow_anchor_sources"]]
    assert anchors and all(anchor["lane_axis"]["money_column_ordinals"] == [2, 1] for anchor in anchors)
    assert all(anchor["lane_axis"]["source_lane_keys"] == [["DURATION_END_DATE", "2026-09-30"], ["DURATION_END_DATE", "2025-09-30"]] for anchor in anchors)
    assert _candidate(records)["status"] == READY
    assert records == original


@pytest.mark.parametrize("field", ["document_id", "source_sha256"])
def test_contextual_period_absolute_years_cannot_cross_original_document_identity(field):
    records = _contextual_period_records(quarter="IV", include_cash_flow=False, absolute_primary=True)
    records[1][field] = "other-document" if field == "document_id" else "f" * 64
    proof = _contextual_period_proof(records)
    assert proof["complete"] is False
    assert "SOURCE_PERIOD_DOCUMENT_IDENTITY_NOT_UNIQUE" in proof["reasons"]


@pytest.mark.parametrize("caption", ["Cho quý III năm 2025", "Cho năm tài chính 2025"])
def test_contextual_period_owned_reporting_year_or_quarter_cannot_be_replaced_by_cash_flow(caption):
    records = _contextual_period_records()
    records[1]["page_json"]["sections"][0]["narratives_exact"] = [caption]
    proof = _contextual_period_proof(records)
    assert proof["complete"] is False
    assert _candidate(records)["status"] == UNRESOLVED


@pytest.mark.parametrize("include_cash_flow", [True, False])
def test_contextual_period_same_sign_supplemental_merge_without_note_root_still_requires_source_periods(include_cash_flow):
    records = _contextual_period_records(include_cash_flow=include_cash_flow)
    records[0]["page_json"]["sections"][0]["tables"][0]["rows"].pop()
    primary_rows = records[1]["page_json"]["sections"][0]["tables"][0]["rows"]
    for row, values in zip(primary_rows[1:4], (("20", "16"), ("2", "1"), ("22", "17")), strict=True):
        row["values_exact"][-2:] = values
    original = deepcopy(records)
    proof = _contextual_period_proof(records)
    assert proof["complete"] is include_cash_flow
    candidate = _candidate(records)
    assert candidate["status"] == (READY if include_cash_flow else UNRESOLVED), candidate["reasons"]
    if include_cash_flow:
        mappings = {item["role"]: item for item in candidate["mappings"]}
        assert [cell["source_text"] for cell in mappings["CURRENT_TAX_PARENT"]["values"]] == ["20", "16"]
        assert [cell["source_text"] for cell in mappings["FAMILY_ROOT_TOTAL"]["values"]] == ["22", "17"]
    else:
        assert candidate["mappings"] == []
    assert records == original


def test_contextual_period_relative_previous_year_requires_consecutive_printed_absolute_years():
    records = _contextual_period_records()
    for index in (0, 2):
        column = records[index]["page_json"]["sections"][0]["tables"][0]["columns"][1]
        column["header_path_exact"] = [part.replace("2025", "2024") for part in column["header_path_exact"]]
    original = deepcopy(records)
    proof = _contextual_period_proof(records)
    assert proof["complete"] is False
    assert proof["status"] == "ALGORITHM_HOLD"
    candidate = _candidate(records)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert records == original


@pytest.mark.parametrize("source_kind", ["caption", "narrative"])
@pytest.mark.parametrize("asserted_current_year", ["2026", "2025"])
def test_contextual_period_owned_current_report_assertion_must_match_cash_flow_year(source_kind, asserted_current_year):
    records = _contextual_period_records()
    section = records[1]["page_json"]["sections"][0]
    assertion = "Cho kỳ 9 tháng kết thúc ngày 30 tháng 9 năm " + asserted_current_year
    if source_kind == "caption":
        section["title_exact"] += "\n" + assertion
    else:
        section["narratives_exact"].append(assertion)
    original = deepcopy(records)
    proof = _contextual_period_proof(records)
    expected = asserted_current_year == "2026"
    assert proof["complete"] is expected
    candidate = _candidate(records)
    assert candidate["status"] == (READY if expected else UNRESOLVED), candidate["reasons"]
    if not expected:
        assert candidate["mappings"] == []
    assert records == original


@pytest.mark.parametrize("prose", [
    "Thông tin so sánh lịch sử: cho kỳ 9 tháng kết thúc ngày 30 tháng 9 năm 2025.",
    "Người lập báo cáo ký ngày 15 tháng 2 năm 2027.",
])
def test_contextual_period_historical_prose_and_signature_date_do_not_relabel_current_period(prose):
    records = _contextual_period_records()
    records[1]["page_json"]["sections"][0]["narratives_exact"].append(prose)
    original = deepcopy(records)
    proof = _contextual_period_proof(records)
    assert proof["complete"] is True, proof["reasons"]
    candidate = _candidate(records)
    assert candidate["status"] == READY, candidate["reasons"]
    assert records == original


@pytest.mark.parametrize("include_annual_cash_flow", [False, True])
def test_contextual_period_intrinsic_absolute_qiv_cannot_hide_conflicting_cash_flow_continuation(include_annual_cash_flow):
    records = _contextual_period_records(quarter="IV", absolute_primary=True)
    nine_month_records = _contextual_period_records(quarter="III")
    nine_month_cash_flow = deepcopy(nine_month_records[2])
    if include_annual_cash_flow:
        nine_month_cash_flow.update(page_json_version_id="gfpstorev1:json:" + "f" * 64,
                                    physical_page=4, selected_page_ordinal=4)
        records.append(nine_month_cash_flow)
    else:
        records[2] = nine_month_cash_flow
    original = deepcopy(records)
    proof = _contextual_period_proof(records)
    assert proof["complete"] is False
    assert proof["status"] == "ALGORITHM_HOLD"
    candidate = _candidate(records)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert records == original


def test_contextual_period_absolute_four_money_cash_flow_ytd_axis_can_anchor_relative_income_statement():
    records = _contextual_period_records(quarter="IV")
    absolute_primary = _contextual_period_records(quarter="IV", include_cash_flow=False, absolute_primary=True)
    cash_flow_table = records[2]["page_json"]["sections"][0]["tables"][0]
    cash_flow_table["columns"] = deepcopy(absolute_primary[1]["page_json"]["sections"][0]["tables"][0]["columns"])
    for row in cash_flow_table["rows"]:
        row["values_exact"] = ["3", "4", *row["values_exact"]]
    original = deepcopy(records)
    proof = _contextual_period_proof(records)
    assert proof["complete"] is True, proof["reasons"]
    assert proof["start_dates_inferred"] is False
    assert proof["source_period_keys_modified"] is False
    candidate = _candidate(records)
    assert candidate["status"] == READY, candidate["reasons"]
    assert records == original


def _direct_primary_annual_period_records():
    record = _records()[1]
    section = record["page_json"]["sections"][0]
    section["title_exact"] = "Báo cáo kết quả hoạt động riêng"
    table = section["tables"][0]
    table["columns"] = [
        {"value_kind": "MONEY", "header_path_exact": ["Năm " + year, "Triệu đồng"]}
        for year in ("2026", "2025")
    ]
    for row in table["rows"]:
        row["values_exact"] = row["values_exact"][-2:]
    return [record]


def _assert_direct_primary_annual_period_disposition(records, *, complete):
    from bctc_ai.evaluation.gemini_json_income_tax_family_v1 import (
        _document_statement_period_inventory,
        _source_period_correspondence_receipt,
    )

    original = deepcopy(records)
    compiled = _adapter_compiled()
    locator = _contextual_period_locator(records[0])
    inventory = _document_statement_period_inventory(records, compiled_specs=compiled)
    proof = _source_period_correspondence_receipt(
        left_locator=locator, right_locator=locator,
        left_money_column_ordinals=[1, 2], right_money_column_ordinals=[1, 2],
        page_records=records, compiled_specs=compiled, document_period_inventory=inventory,
    )
    assert proof["complete"] is complete, proof["reasons"]
    assert proof["start_dates_inferred"] is False
    assert proof["source_period_keys_modified"] is False
    candidate = _candidate(records)
    assert candidate["status"] == (READY if complete else UNRESOLVED), candidate["reasons"]
    if complete:
        assert candidate["closure_receipt"]["income_tax_adapter_receipt"]["strategy"] == (
            "DIRECT_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION"
        )
        roles = {mapping["role"]: mapping for mapping in candidate["mappings"]}
        for role, expected in (
            ("CURRENT_TAX_PARENT", ["(20)", "(16)"]),
            ("DEFERRED_TAX_NET", ["(2)", "(1)"]),
            ("FAMILY_ROOT_TOTAL", ["(22)", "(17)"]),
        ):
            assert [cell["source_text"] for cell in roles[role]["values"]] == expected
            assert all(ref["money_column_ordinals"] == [1, 2] for ref in roles[role]["source_refs"])
    else:
        assert candidate["mappings"] == []
    assert records == original


@pytest.mark.parametrize("source_kind", ["section_title", "table_title", "narrative"])
@pytest.mark.parametrize("year", ["2026", "2025"])
def test_direct_primary_annual_headers_must_match_owned_current_annual_assertion(source_kind, year):
    records = _direct_primary_annual_period_records()
    section = records[0]["page_json"]["sections"][0]
    caption = "Cho năm tài chính " + year
    if source_kind == "section_title":
        section["title_exact"] += "\n" + caption
    elif source_kind == "table_title":
        section["tables"][0]["title_exact"] = caption
    else:
        section["narratives_exact"].append(caption)
    _assert_direct_primary_annual_period_disposition(records, complete=year == "2026")


@pytest.mark.parametrize("prose", [
    "Thông tin so sánh lịch sử: cho năm tài chính 2025.",
    "Người lập báo cáo ký ngày 15 tháng 2 năm 2027.",
])
def test_direct_primary_annual_current_year_is_not_replaced_by_history_or_signature_date(prose):
    records = _direct_primary_annual_period_records()
    records[0]["page_json"]["sections"][0]["narratives_exact"].append(prose)
    _assert_direct_primary_annual_period_disposition(records, complete=True)


@pytest.mark.parametrize("source_kind", ["section_title", "table_title"])
@pytest.mark.parametrize("assertion", [
    "Cho kỳ từ ngày 1 tháng 1 năm 2025 đến ngày 31 tháng 12 năm 2025",
    "Năm kết thúc ngày 31 tháng 12 năm 2025",
])
def test_direct_primary_annual_unknown_affirmative_range_or_conflicting_standalone_year_stays_held(source_kind, assertion):
    records = _direct_primary_annual_period_records()
    section = records[0]["page_json"]["sections"][0]
    if source_kind == "section_title":
        section["title_exact"] += "\n" + assertion
    else:
        section["tables"][0]["title_exact"] = assertion
    _assert_direct_primary_annual_period_disposition(records, complete=False)


@pytest.mark.parametrize("source_kind", ["section_title", "table_title"])
@pytest.mark.parametrize("year", ["2026", "2025"])
def test_direct_primary_company_prefixed_owned_annual_caption_keeps_current_year_authority(source_kind, year):
    records = _direct_primary_annual_period_records()
    section = records[0]["page_json"]["sections"][0]
    caption = (
        "Ngân hàng thương mại cổ phần Ví dụ\n"
        "Báo cáo kết quả hoạt động riêng\n"
        "Cho năm tài chính " + year
    )
    if source_kind == "section_title":
        section["title_exact"] = caption
    else:
        section["tables"][0]["title_exact"] = caption
    _assert_direct_primary_annual_period_disposition(records, complete=year == "2026")


@pytest.mark.parametrize("corroborating_year", ["2026", "2025"])
def test_direct_primary_precision_preference_cannot_hide_another_typed_sources_current_year(corroborating_year):
    records = _direct_primary_annual_period_records()
    million_section = records[0]["page_json"]["sections"][0]
    million_section["title_exact"] += "\nCho năm tài chính " + corroborating_year
    vnd_record = deepcopy(records[0])
    vnd_record.update(page_json_version_id="gfpstorev1:json:" + "e" * 64,
                      physical_page=3, selected_page_ordinal=3)
    vnd_section = vnd_record["page_json"]["sections"][0]
    vnd_section["title_exact"] = "Báo cáo kết quả hoạt động riêng\nCho năm tài chính 2026"
    vnd_table = vnd_section["tables"][0]
    vnd_table["unit_exact"] = "VND"
    for column in vnd_table["columns"]:
        column["header_path_exact"][-1] = "VND"
    for row in vnd_table["rows"]:
        row["values_exact"] = [
            ("(" + str(int(value[1:-1]) * 1_000_000) + ")"
             if value.startswith("(") else str(int(value) * 1_000_000))
            for value in row["values_exact"]
        ]
    records.append(vnd_record)
    original = deepcopy(records)
    candidate = _candidate(records)
    if corroborating_year == "2026":
        assert candidate["status"] == READY, candidate["reasons"]
        assert all(mapping["unit"] == "VND" for mapping in candidate["mappings"])
        descriptor = candidate["closure_receipt"]["income_tax_adapter_receipt"]["primary_projection_receipt"]
        assert descriptor["locator"]["page_json_version_id"] == vnd_record["page_json_version_id"]
        assert len(descriptor["corroborating_presentations"]) == 2
    else:
        assert candidate["status"] == UNRESOLVED
        assert candidate["mappings"] == []
    assert records == original


def _owned_relative_year_period_records():
    records = _records()
    records[0]["page_json"]["sections"][0]["title_exact"] += " riêng"
    records[1] = _direct_primary_annual_period_records()[0]
    section = records[1]["page_json"]["sections"][0]
    section["title_exact"] += "\nCho năm tài chính kết thúc ngày 31 tháng 12 năm 2026"
    for column, label in zip(section["tables"][0]["columns"], ("Năm nay", "Năm trước"), strict=True):
        column["header_path_exact"] = [label]
    return records


def _owned_relative_year_period_proof(records):
    from bctc_ai.evaluation.gemini_json_income_tax_family_v1 import (
        _document_statement_period_inventory,
        _source_period_correspondence_receipt,
    )

    compiled = _adapter_compiled()
    inventory = _document_statement_period_inventory(records, compiled_specs=compiled)
    return _source_period_correspondence_receipt(
        left_locator=_contextual_period_locator(records[0]), right_locator=_contextual_period_locator(records[1]),
        left_money_column_ordinals=[1, 2], right_money_column_ordinals=[1, 2],
        page_records=records, compiled_specs=compiled, document_period_inventory=inventory,
    )


@pytest.mark.parametrize("presentation", ["annual_year", "annual_end_date", "header_unit", "restated_comparative", "finite_form_code"])
def test_owned_relative_year_columns_use_only_exact_owned_annual_source_context(presentation):
    records = _owned_relative_year_period_records()
    section = records[1]["page_json"]["sections"][0]
    table = section["tables"][0]
    if presentation == "annual_year":
        section["title_exact"] = "Báo cáo kết quả hoạt động riêng\nCho năm tài chính 2026"
    elif presentation == "header_unit":
        for column in table["columns"]:
            column["header_path_exact"].append("Triệu đồng")
    elif presentation == "restated_comparative":
        table["columns"][1]["header_path_exact"][0] += " (Trình bày lại)"
    elif presentation == "finite_form_code":
        section["title_exact"] += "\nB03/TCTD"
    original = deepcopy(records)
    proof = _owned_relative_year_period_proof(records)
    assert proof["complete"] is True, proof["reasons"]
    assert proof["source_period_keys_modified"] is False
    assert proof["start_dates_inferred"] is False
    assert proof["amounts_used_as_authority"] is False
    assert proof["source_selectors"][1]["raw_lane_axis"]["source_lane_keys"] == [
        ["SEMANTIC_ALIAS", "CURRENT_PERIOD"], ["SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"],
    ]
    candidate = _candidate(records)
    assert candidate["status"] == READY, candidate["reasons"]
    roles = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [value["source_text"] for value in roles["CURRENT_TAX_PARENT"]["values"]] == ["20", "16"]
    assert [value["source_text"] for value in roles["FAMILY_ROOT_TOTAL"]["values"]] == ["(22)", "(17)"]
    assert records == original


@pytest.mark.parametrize("mutation", [
    "no_owned_caption", "wrong_year", "unknown_range", "relative_period_not_year", "quarter_only_caption",
    "three_months_ending_june", "filename_only", "other_page_borrowing", "arbitrary_caption_suffix",
])
def test_owned_relative_year_route_does_not_invent_or_borrow_missing_period_authority(mutation):
    records = _owned_relative_year_period_records()
    section = records[1]["page_json"]["sections"][0]
    table = section["tables"][0]
    if mutation in {"no_owned_caption", "filename_only", "other_page_borrowing"}:
        section["title_exact"] = "Báo cáo kết quả hoạt động riêng"
    elif mutation == "wrong_year":
        section["title_exact"] = section["title_exact"].replace("2026", "2025")
    elif mutation == "unknown_range":
        section["title_exact"] = (
            "Báo cáo kết quả hoạt động riêng\n"
            "Cho kỳ từ ngày 1 tháng 1 năm 2026 đến ngày 31 tháng 12 năm 2026"
        )
    elif mutation == "relative_period_not_year":
        table["columns"][0]["header_path_exact"] = ["Kỳ này"]
        table["columns"][1]["header_path_exact"] = ["Kỳ trước"]
    elif mutation == "quarter_only_caption":
        section["title_exact"] = "Báo cáo kết quả hoạt động riêng\nCho quý IV năm 2026"
    elif mutation == "three_months_ending_june":
        section["title_exact"] = (
            "Báo cáo kết quả hoạt động riêng\nCho kỳ 3 tháng kết thúc ngày 30 tháng 6 năm 2026"
        )
    else:
        section["title_exact"] += " đã điều chỉnh"
    if mutation == "filename_only":
        for record in records:
            record["source_logical_name"] = "BCTC_nam_2026_ket_thuc_31_12_2026.pdf"
    elif mutation == "other_page_borrowing":
        unrelated = _record(_page([]))
        unrelated.update(page_json_version_id="gfpstorev1:json:" + "e" * 64,
                         physical_page=3, selected_page_ordinal=3)
        unrelated["page_json"]["sections"][0]["title_exact"] = "Thông tin chung\nCho năm tài chính 2026"
        records.append(unrelated)
    original = deepcopy(records)
    proof = _owned_relative_year_period_proof(records)
    assert proof["complete"] is False
    assert proof["status"] == "ALGORITHM_HOLD"
    assert proof["source_period_keys_modified"] is False
    assert proof["start_dates_inferred"] is False
    candidate = _candidate(records)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert records == original


def _document_annual_relative_note_records():
    records = _owned_relative_year_period_records()
    note_table = records[0]["page_json"]["sections"][0]["tables"][0]
    for column, label in zip(note_table["columns"], ("Năm nay", "Năm trước"), strict=True):
        column["header_path_exact"] = [label]
    cash_flow = _primary_page([_row("Lưu chuyển tiền thuần từ hoạt động kinh doanh", "7", "8")])
    section = cash_flow["sections"][0]
    section["statement_type"] = "CASH_FLOW"
    section["title_exact"] = (
        "Báo cáo lưu chuyển tiền tệ riêng\nCho năm tài chính kết thúc ngày 31 tháng 12 năm 2026"
    )
    section["tables"][0]["columns"] = [
        {"value_kind": "MONEY", "header_path_exact": [label]}
        for label in ("Năm nay", "Năm trước")
    ]
    records.append(_primary_record(
        cash_flow, page_json_version_id="gfpstorev1:json:" + "e" * 64,
        physical_page=3, selected_page_ordinal=3,
    ))
    return records


def _append_document_annual_cash_flow_continuation(records):
    continuation = deepcopy(records[2])
    continuation.update(page_json_version_id="gfpstorev1:json:" + "f" * 64,
                        physical_page=4, selected_page_ordinal=4)
    records.append(continuation)
    return continuation


@pytest.mark.parametrize("presentation", [
    "matching", "compatible_cash_flow_continuation", "restated_comparative", "header_units",
    "owned_annual_narrative", "company_prefixed_caption",
])
def test_document_annual_period_requires_two_distinct_typed_owned_statement_sources(presentation):
    from bctc_ai.evaluation.gemini_json_income_tax_family_v1 import (
        _document_statement_period_inventory,
    )

    records = _document_annual_relative_note_records()
    if presentation == "compatible_cash_flow_continuation":
        _append_document_annual_cash_flow_continuation(records)
    elif presentation == "restated_comparative":
        for record in records:
            record["page_json"]["sections"][0]["tables"][0]["columns"][1]["header_path_exact"][0] += " (Trình bày lại)"
    elif presentation == "header_units":
        for record in records:
            for column in record["page_json"]["sections"][0]["tables"][0]["columns"]:
                column["header_path_exact"].append("Triệu đồng")
    elif presentation == "owned_annual_narrative":
        section = records[2]["page_json"]["sections"][0]
        section["title_exact"] = "Báo cáo lưu chuyển tiền tệ riêng"
        section["narratives_exact"].append("Cho năm tài chính kết thúc ngày 31 tháng 12 năm 2026")
    elif presentation == "company_prefixed_caption":
        for record in records[1:]:
            section = record["page_json"]["sections"][0]
            section["title_exact"] = "Ngân hàng thương mại cổ phần Ví dụ\n" + section["title_exact"]
    original = deepcopy(records)
    inventory = _document_statement_period_inventory(records, compiled_specs=_adapter_compiled())
    annual = inventory["document_annual_period_receipt"]
    assert type(annual) is dict and type(annual.get("receipt_id")) is str
    proof = _owned_relative_year_period_proof(records)
    assert proof["complete"] is True, proof["reasons"]
    assert proof["status"] == "PASS_AUTHENTICATED_DOCUMENT_ANNUAL_PERIOD"
    assert any(item.get("inherited_document_annual_period_receipt") for item in proof["period_resolution_evidence"])
    assert proof["source_period_keys_modified"] is False
    assert proof["start_dates_inferred"] is False
    assert proof["amounts_used_as_authority"] is False
    assert proof["source_selectors"][0]["raw_lane_axis"]["source_lane_keys"] == [
        ["SEMANTIC_ALIAS", "CURRENT_PERIOD"], ["SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"],
    ]
    candidate = _candidate(records)
    assert candidate["status"] == READY, candidate["reasons"]
    roles = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [cell["source_text"] for cell in roles["CURRENT_TAX_PARENT"]["values"]] == ["20", "16"]
    assert [cell["source_text"] for cell in roles["FAMILY_ROOT_TOTAL"]["values"]] == ["(22)", "(17)"]
    assert records == original


@pytest.mark.parametrize("mutation", [
    "missing_cash_flow", "same_statement_type_only", "fake_cash_flow_caption", "conflicting_cash_flow_year",
    "conflict_plus_matching_continuation", "unknown_scope", "entity_override", "missing_date_continuation",
    "note_quarter_iv", "note_three_month_title", "note_six_month_title", "note_nine_month_title",
    "note_ytd_header", "note_six_month_narrative", "note_ytd_narrative", "note_six_month_row_ancestor",
    "note_relative_period_labels", "unknown_note_affirmative_range", "wrong_note_annual_year", "filename_only",
    "other_document_cash_flow", "note_duplicate_year_label", "note_unknown_comparative_annotation",
    "note_twelve_months_wrong_endpoint",
])
def test_document_annual_period_cannot_override_missing_conflicting_or_local_nonannual_source(mutation):
    records = _document_annual_relative_note_records()
    note_section = records[0]["page_json"]["sections"][0]
    note_table = note_section["tables"][0]
    cash_flow_section = records[2]["page_json"]["sections"][0]
    if mutation == "missing_cash_flow":
        records.pop()
    elif mutation == "same_statement_type_only":
        cash_flow_section["statement_type"] = "INCOME_STATEMENT"
        cash_flow_section["title_exact"] = cash_flow_section["title_exact"].replace("lưu chuyển tiền tệ", "kết quả hoạt động")
    elif mutation == "fake_cash_flow_caption":
        cash_flow_section["title_exact"] = (
            "Bản thống kê nội bộ riêng\nCho năm tài chính kết thúc ngày 31 tháng 12 năm 2026"
        )
    elif mutation in {"conflicting_cash_flow_year", "conflict_plus_matching_continuation"}:
        if mutation == "conflict_plus_matching_continuation":
            _append_document_annual_cash_flow_continuation(records)
        cash_flow_section["title_exact"] = cash_flow_section["title_exact"].replace("2026", "2023")
    elif mutation == "unknown_scope":
        for record in records:
            section = record["page_json"]["sections"][0]
            section["title_exact"] = section["title_exact"].replace(" riêng", "")
    elif mutation == "entity_override":
        cash_flow_section["title_exact"] += "\nNgân hàng mẹ"
    elif mutation == "missing_date_continuation":
        continuation = _append_document_annual_cash_flow_continuation(records)
        continuation["page_json"]["sections"][0]["title_exact"] = "Báo cáo lưu chuyển tiền tệ riêng"
    elif mutation == "note_quarter_iv":
        note_section["title_exact"] += " quý IV"
    elif mutation in {"note_three_month_title", "note_six_month_title", "note_nine_month_title"}:
        months, day = {"note_three_month_title": (3, 31), "note_six_month_title": (6, 30), "note_nine_month_title": (9, 30)}[mutation]
        note_section["title_exact"] += (
            "\nCho kỳ " + str(months) + " tháng kết thúc ngày " + str(day) + " tháng " + str(months) + " năm 2026"
        )
    elif mutation == "note_ytd_header":
        for column in note_table["columns"]:
            column["header_path_exact"].insert(0, "Lũy kế từ đầu năm")
    elif mutation == "note_six_month_narrative":
        note_section["narratives_exact"].append("Cho kỳ 6 tháng kết thúc ngày 30 tháng 6 năm 2026")
    elif mutation == "note_ytd_narrative":
        note_section["narratives_exact"].append("Cho kỳ lũy kế từ đầu năm đến ngày 30 tháng 9 năm 2026")
    elif mutation == "note_six_month_row_ancestor":
        for row in note_table["rows"]:
            row["hierarchy_path_exact"].insert(0, "Kỳ 6 tháng kết thúc ngày 30 tháng 6 năm 2026")
    elif mutation == "note_relative_period_labels":
        for column, label in zip(note_table["columns"], ("Kỳ này", "Kỳ trước"), strict=True):
            column["header_path_exact"] = [label]
    elif mutation == "unknown_note_affirmative_range":
        note_section["title_exact"] += "\nCho kỳ từ ngày 1 tháng 1 năm 2026 đến ngày 31 tháng 12 năm 2026"
    elif mutation == "wrong_note_annual_year":
        note_section["title_exact"] += "\nCho năm tài chính 2025"
    elif mutation == "filename_only":
        for record in records:
            section = record["page_json"]["sections"][0]
            section["title_exact"] = section["title_exact"].split("\nCho năm", 1)[0]
            record["source_logical_name"] = "BCTC_rieng_nam_2026_31_12_2026.pdf"
    elif mutation == "other_document_cash_flow":
        records[2]["document_id"] = "another-source-document"
    elif mutation == "note_duplicate_year_label":
        note_table["columns"][1]["header_path_exact"] = ["Năm nay"]
    elif mutation == "note_unknown_comparative_annotation":
        note_table["columns"][1]["header_path_exact"] = ["Năm trước (công ty con)"]
    else:
        note_section["title_exact"] += "\nCho kỳ 12 tháng kết thúc ngày 30 tháng 6 năm 2026"
    original = deepcopy(records)
    proof = _owned_relative_year_period_proof(records)
    assert proof["complete"] is False
    assert proof["status"] == "ALGORITHM_HOLD"
    assert proof["start_dates_inferred"] is False
    assert proof["source_period_keys_modified"] is False
    if mutation in {"note_duplicate_year_label", "note_unknown_comparative_annotation"}:
        compiled = _adapter_compiled()
        base = coalesce_gemini_json_multitable_hierarchical_document_v1(page_records=records, compiled_specs=compiled)
        cluster = recover_gemini_json_income_tax_query_cluster_v1(page_records=records, base_cluster=base, compiled_specs=compiled)
        assert cluster["status"] == UNRESOLVED
        assert cluster["component_regions"] == []
        assert cluster["reasons"] == (["SUPPLEMENTAL_ROOT_LANE_AXIS_NOT_COMPLETE"] if mutation == "note_duplicate_year_label"
                                       else ["SUPPLEMENTAL_ROOT_UNIT_AXIS_NOT_COMPLETE"])
    elif mutation != "other_document_cash_flow":
        # Mixed document identity is rejected at the direct correspondence
        # boundary above; it is not a valid whole-document evaluator input.
        candidate = _candidate(records)
        assert candidate["status"] == UNRESOLVED
        assert candidate["mappings"] == []
    assert records == original


def test_document_annual_period_inventory_self_resealing_does_not_authenticate_altered_source_date():
    from bctc_ai.evaluation.gemini_json_income_tax_family_v1 import (
        _document_statement_period_inventory,
        _source_period_correspondence_receipt,
    )

    records = _document_annual_relative_note_records()
    compiled = _adapter_compiled()
    forged = deepcopy(_document_statement_period_inventory(records, compiled_specs=compiled))
    annual = forged["document_annual_period_receipt"]
    annual["amounts_used_as_authority"] = True
    prefix = annual["receipt_id"].rsplit(":", 1)[0] + ":"
    annual["receipt_id"] = prefix + canonical_json_sha256_v1({key: value for key, value in annual.items() if key != "receipt_id"})
    prefix = forged["receipt_id"].rsplit(":", 1)[0] + ":"
    forged["receipt_id"] = prefix + canonical_json_sha256_v1({key: value for key, value in forged.items() if key != "receipt_id"})
    changed = deepcopy(records)
    changed[2]["page_json"]["sections"][0]["title_exact"] = (
        "Báo cáo lưu chuyển tiền tệ riêng\nCho năm tài chính kết thúc ngày 31 tháng 12 năm 2023"
    )
    original = deepcopy(changed)
    with pytest.raises(GeminiJsonIncomeTaxFamilyV1Error, match="drifted"):
        _source_period_correspondence_receipt(
            left_locator=_contextual_period_locator(changed[0]), right_locator=_contextual_period_locator(changed[1]),
            left_money_column_ordinals=[1, 2], right_money_column_ordinals=[1, 2],
            page_records=changed, compiled_specs=compiled, document_period_inventory=forged,
        )
    assert changed == original


@pytest.mark.parametrize("caption", ["6 tháng 2026", "For the six months ended 30 June 2026", "trong năm 2025"])
def test_document_annual_inheritance_veto_keeps_local_duration_followed_by_year(caption):
    records = _document_annual_relative_note_records()
    records[0]["page_json"]["sections"][0]["title_exact"] += " " + caption
    original = deepcopy(records)
    proof = _owned_relative_year_period_proof(records)
    assert proof["complete"] is False
    assert _candidate(records)["status"] == UNRESOLVED
    assert records == original


@pytest.mark.parametrize("ancestor", ["Ngân hàng mẹ", "Trong quý IV"])
def test_document_annual_inheritance_preserves_true_ancestor_only_paths(ancestor):
    records = _document_annual_relative_note_records()
    records[0]["page_json"]["sections"][0]["tables"][0]["rows"][0]["hierarchy_path_exact"] = [ancestor]
    original = deepcopy(records)
    proof = _owned_relative_year_period_proof(records)
    assert proof["complete"] is False
    inheritance = proof["period_resolution_evidence"][0]["inherited_document_annual_period_receipt"]
    assert inheritance["complete"] is False
    assert any(item["source_exact"] == ancestor for item in inheritance["local_period_surface_census"])
    assert records == original


@pytest.mark.parametrize("label,path_leaf", [
    ("- Lợi nhuận được chia từ công ty con", "Lợi nhuận được chia từ công ty con"),
    ("- Lợi nhuận của công ty con", "Lợi nhuận của công ty con"),
])
def test_document_annual_inheritance_does_not_turn_a_bulleted_component_leaf_into_entity_ancestry(label, path_leaf):
    records = _document_annual_relative_note_records()
    row = _row(label, "1", "2")
    row["hierarchy_path_exact"] = ["Điều chỉnh các khoản:", path_leaf]
    records[0]["page_json"]["sections"][0]["tables"][0]["rows"].append(row)
    original = deepcopy(records)
    proof = _owned_relative_year_period_proof(records)
    assert proof["complete"] is True, proof["reasons"]
    inheritance = proof["period_resolution_evidence"][0]["inherited_document_annual_period_receipt"]
    assert inheritance["scope_receipt"]["local_entity_qualifiers"] == []
    assert not any(item["source_exact"] == path_leaf for item in inheritance["local_period_surface_census"])
    assert records == original


@pytest.mark.parametrize("caption", [
    "tháng 9 năm 2026", "từ 01/01/2026 đến 30/06/2026", "từ 2026-01-01 đến 2026-06-30",
    "For the year ended 31 December 2025", "Q.IV năm 2026", "quí 3 năm 2026",
    "06 tháng 2026", "tháng 09 năm 2026",
])
def test_document_annual_inheritance_does_not_override_other_explicit_local_period_spellings(caption):
    records = _document_annual_relative_note_records()
    records[0]["page_json"]["sections"][0]["title_exact"] += " " + caption
    original = deepcopy(records)
    proof = _owned_relative_year_period_proof(records)
    assert proof["complete"] is False
    assert _candidate(records)["status"] == UNRESOLVED
    assert records == original


@pytest.mark.parametrize("prose", [
    "Thuế TNDN được tạm nộp hàng quý theo quy định.",
    "Người lập báo cáo ký ngày 15 tháng 2 năm 2027.",
    "Số liệu thuế của năm 2023 được trình bày lại trong phần thông tin so sánh.",
])
def test_document_annual_inheritance_retains_policy_history_and_signature_prose_without_relabeling_period(prose):
    records = _document_annual_relative_note_records()
    records[0]["page_json"]["sections"][0]["narratives_exact"].append(prose)
    original = deepcopy(records)
    proof = _owned_relative_year_period_proof(records)
    assert proof["complete"] is True, proof["reasons"]
    assert _candidate(records)["status"] == READY
    assert records == original
