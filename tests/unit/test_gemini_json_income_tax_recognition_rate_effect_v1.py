"""Printed RATE effects remain authenticated controls, not income exports."""
from __future__ import annotations

from copy import deepcopy

import pytest
from test_gemini_json_income_tax_family_v1 import (
    OWNER,
    VERSION_ID,
    _adapter_compiled,
    _page,
    _record,
    _row,
)

from bctc_ai.evaluation.gemini_json_income_tax_family_v1 import (
    _recognition_rate_effect_forward_control,
    _recognition_rate_source_only_projection,
    _source_context_receipt,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
)

CURRENT = "Chi phí thuế TNDN - hiện hành"
DEFERRED = "Thu nhập thuế TNDN - hoãn lại"
ROOT = "Chi phí thuế TNDN"
CALCULATION = "Chi phí thuế TNDN tính trên thu nhập chịu thuế kỳ hiện hành"
ADJUSTMENT_GROUP = "Điều chỉnh:"
ANNOTATION = (
    "(*) Chi phí thuế TNDN cho kỳ kế toán được ước tính dựa vào thu nhập chịu thuế "
    "và có thể có những điều chỉnh tùy thuộc vào sự kiểm tra của cơ quan thuế."
)
EFFECT_ROLES = {"NON_TAXABLE_AGGREGATE", "NON_DEDUCTIBLE_EXPENSE"}


def _raw(value):
    return "(" + str(-value) + ")" if value < 0 else str(value)


def _rate_recognition_fixture(*, variant="basic"):
    scope = "hợp nhất" if variant in {"consolidated", "all_adjustments"} else "riêng"
    group = "Chi phí thuế TNDN ghi nhận trong báo cáo kết quả hoạt động " + scope + ":"
    adjustments = [
        ("Thu nhập không chịu thuế", -2, -1),
        ("Chi phí không được khấu trừ", 1, 2),
    ]
    if variant in {"prior", "all_adjustments"}:
        adjustments.append(("Điều chỉnh số thuế phải nộp năm trước", 1, -1))
    if variant == "all_adjustments":
        adjustments.extend([("Điều chỉnh lợi nhuận do hợp nhất", -3, 2), ("Khác", 2, -1)])
    if variant == "dash_adjustments":
        adjustments = [(label, 0, 0) for label, _, _ in adjustments]
    current = (20 + sum(item[1] for item in adjustments), 16 + sum(item[2] for item in adjustments))
    root = ROOT + (" (*)" if variant == "annotated_root" else "")
    rows = [
        _row("Lợi nhuận kế toán trước thuế TNDN", "999" if variant == "not_twenty_percent" else "100", "888" if variant == "not_twenty_percent" else "80"),
        _row("Thuế tính ở thuế suất 20%", "20", "16"),
        _row(ADJUSTMENT_GROUP, None, None, kind="GROUP"),
    ]
    for label, first, second in adjustments:
        row = _row(label, "-" if variant == "dash_adjustments" else _raw(first), "-" if variant == "dash_adjustments" else _raw(second))
        row["hierarchy_path_exact"] = [ADJUSTMENT_GROUP, label]
        rows.append(row)
    rows.extend([
        _row(CALCULATION, *map(_raw, current), kind="TOTAL" if variant == "calculation_total" else "SUBTOTAL"),
        _row(group, None, None, kind="GROUP"),
        {**_row(CURRENT, *map(_raw, current)), "hierarchy_path_exact": [group, CURRENT]},
        {**_row(DEFERRED, "-", " -"), "hierarchy_path_exact": [group, DEFERRED]},
        _row(root, *map(_raw, current), kind="TOTAL"),
    ])
    page = _page(rows, owner=OWNER + " " + scope)
    section = page["sections"][0]
    if variant == "annotated_root":
        section["narratives_exact"].append(ANNOTATION)
    if variant == "vnd":
        section["tables"][0]["unit_exact"] = "VND"
        for column in section["tables"][0]["columns"]:
            column["header_path_exact"][-1] = "VND"
    return page, section, section["tables"][0]


def _control(section, table):
    before = deepcopy(section)
    control = _recognition_rate_effect_forward_control(section, table, compiled_specs=_adapter_compiled())
    assert section == before
    return control


@pytest.mark.parametrize("variant", [
    "basic", "consolidated", "prior", "all_adjustments", "dash_adjustments",
    "calculation_total", "annotated_root", "vnd", "not_twenty_percent",
])
def test_recognition_rate_effect_control_authenticates_printed_signed_forward_operands_only(variant):
    _, section, table = _rate_recognition_fixture(variant=variant)
    control = _control(section, table)
    assert control["status"] == "PASS", control["reasons"]
    assert control["reasons"] == []
    assert control["measurement_basis"] == "TAX_EFFECT_NOT_TAXABLE_INCOME_ADJUSTMENT"
    assert control["schema_mapping_authority"] is False
    assert control["profit_times_rate_used"] is False
    assert control["source_values_changed"] is False
    assert control["ownership_inferred_from_values"] is False
    assert control["source_table_rows_exact"] == table["rows"]
    assert len(control["lane_equations"]) == 2
    for lane, equation in enumerate(control["lane_equations"]):
        assert equation["lane_ordinal"] == lane
        assert equation["residual"] == 0
        assert equation["calculation_current_residual"] == 0
        assert equation["component_sum"] == equation["observed_calculation"]
        for source in equation["component_source_cells"]:
            assert source["source_text_exact"] == table["rows"][source["row_ordinal"] - 1]["values_exact"][lane]
    assert _control(section, table) == control


def test_recognition_rate_effect_control_does_not_invent_a_rate_prefix_for_pure_recognition():
    _, section, table = _rate_recognition_fixture()
    table["rows"] = table["rows"][-4:]
    assert _control(section, table)["status"] == "NOT_APPLICABLE"


@pytest.mark.parametrize("mutation", [
    "missing_profit", "missing_rate", "missing_adjustment_group", "missing_calculation",
    "duplicate_profit", "duplicate_rate", "duplicate_adjustment", "duplicate_calculation",
    "unknown_adjustment", "reversed_adjustments", "missing_non_deductible", "unknown_prefix", "unknown_tail",
    "foreign_adjustment_ancestor", "foreign_current_ancestor", "profit_total", "rate_subtotal",
    "numeric_adjustment_group", "dash_adjustment_group", "calculation_item", "nested_calculation",
    "profit_blank", "rate_blank", "adjustment_blank", "calculation_blank", "current_blank", "root_blank",
    "rate_marker", "adjustment_marker", "rate_percentage_cell", "wrong_adjustment_sign", "wrong_rate_sign",
    "calculation_residual", "calculation_current_residual", "nonzero_deferred_closing_arithmetic",
    "scope_conflict", "unit_conflict", "missing_unit", "root_unowned_marker", "root_unknown_marker",
])
def test_recognition_rate_effect_control_holds_incomplete_unknown_or_conflicting_source(mutation):
    _, section, table = _rate_recognition_fixture()
    rows = table["rows"]
    if mutation.startswith("missing_") and mutation not in {"missing_non_deductible", "missing_unit"}:
        rows.pop({"missing_profit": 0, "missing_rate": 1, "missing_adjustment_group": 2, "missing_calculation": 5}[mutation])
    elif mutation in {"duplicate_profit", "duplicate_rate", "duplicate_adjustment", "duplicate_calculation"}:
        rows.insert(5, deepcopy(rows[{"duplicate_profit": 0, "duplicate_rate": 1, "duplicate_adjustment": 3, "duplicate_calculation": 5}[mutation]]))
    elif mutation == "unknown_adjustment":
        rows[3]["label_exact"] = "Khoản điều chỉnh chưa xác định"
        rows[3]["hierarchy_path_exact"] = [ADJUSTMENT_GROUP, rows[3]["label_exact"]]
    elif mutation == "reversed_adjustments":
        rows[3], rows[4] = rows[4], rows[3]
    elif mutation == "missing_non_deductible":
        rows.pop(4)
    elif mutation == "unknown_prefix":
        rows.insert(0, _row("Khoản nguồn khác", "0", "0"))
    elif mutation == "unknown_tail":
        rows.append(_row("Khoản nguồn khác", "0", "0"))
    elif mutation == "foreign_adjustment_ancestor":
        rows[3]["hierarchy_path_exact"].insert(0, "Ngân hàng mẹ")
    elif mutation == "foreign_current_ancestor":
        rows[-3]["hierarchy_path_exact"].insert(0, "Công ty con")
    elif mutation in {"profit_total", "rate_subtotal", "calculation_item"}:
        rows[{"profit_total": 0, "rate_subtotal": 1, "calculation_item": 5}[mutation]]["row_kind"] = {
            "profit_total": "TOTAL", "rate_subtotal": "SUBTOTAL", "calculation_item": "ITEM",
        }[mutation]
    elif mutation in {"numeric_adjustment_group", "dash_adjustment_group"}:
        rows[2]["values_exact"] = ["0", "0"] if mutation == "numeric_adjustment_group" else ["-", "-"]
    elif mutation == "nested_calculation":
        rows[5]["hierarchy_path_exact"].insert(0, ADJUSTMENT_GROUP)
    elif mutation in {"profit_blank", "rate_blank", "adjustment_blank", "calculation_blank", "current_blank", "root_blank"}:
        rows[{"profit_blank": 0, "rate_blank": 1, "adjustment_blank": 3, "calculation_blank": 5, "current_blank": 7, "root_blank": 9}[mutation]]["values_exact"][0] = None
    elif mutation in {"rate_marker", "adjustment_marker", "rate_percentage_cell"}:
        rows[3 if mutation == "adjustment_marker" else 1]["values_exact"][0] = "20%" if mutation == "rate_percentage_cell" else "?"
    elif mutation == "wrong_adjustment_sign":
        rows[3]["values_exact"][0] = "2"
    elif mutation == "wrong_rate_sign":
        rows[1]["values_exact"][0] = "(20)"
    elif mutation == "calculation_residual":
        rows[5]["values_exact"][0] = "18"
    elif mutation == "calculation_current_residual":
        rows[7]["values_exact"][0] = rows[9]["values_exact"][0] = "18"
    elif mutation == "nonzero_deferred_closing_arithmetic":
        rows[8]["values_exact"] = ["1", "2"]
        rows[9]["values_exact"] = ["20", "19"]
    elif mutation == "scope_conflict":
        section["title_exact"] = OWNER + " hợp nhất"
    elif mutation == "unit_conflict":
        table["unit_exact"] = "VND"
    elif mutation == "missing_unit":
        table["unit_exact"] = None
        for column in table["columns"]:
            column["header_path_exact"].pop()
    else:
        label = ROOT + (" (*)" if mutation == "root_unowned_marker" else " (**)")
        rows[-1]["label_exact"] = label
        rows[-1]["hierarchy_path_exact"] = [label]
    control = _control(section, table)
    if mutation == "missing_adjustment_group":
        # Historical node ID retained; complete repeated ancestry is no
        # longer missing ownership, and must not manufacture an owner row.
        assert control["status"] == "PASS", control["reasons"]
        assert control["adjustment_group_source_row"] is None
        assert control["adjustment_owner_receipt"]["owner_source_row"] is None
        assert [item["row_ordinal"] for item in control["adjustment_owner_receipt"]["owner_occurrences"]] == [3, 4]
        assert control["source_table_rows_exact"] == table["rows"]
        assert control["schema_mapping_authority"] is False
        assert control["profit_times_rate_used"] is False
        assert all(item["residual"] == item["calculation_current_residual"] == 0
                   for item in control["lane_equations"])
    else:
        assert control["status"] == "ALGORITHM_HOLD", (mutation, control)
        assert control["reasons"]


def _generic_candidate_and_context():
    page, _, _ = _rate_recognition_fixture()
    records = [_record(page)]
    compiled = _adapter_compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(page_records=records, compiled_specs=compiled)
    assert cluster["status"] == READY, cluster["reasons"]
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"], page_json_by_version={VERSION_ID: page}, compiled_specs=compiled,
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(cluster["component_regions"]),
    )
    assert candidate["status"] == READY, candidate["reasons"]
    context = _source_context_receipt(compiled_specs=compiled, repair_receipts=[], root_controls=[], page_records=records)
    assert len(context["tax_population_inventory"]) == 1
    assert context["tax_population_inventory"][0]["recognition_rate_effect_control"]["status"] == "PASS"
    assert {item["role"] for item in candidate["mappings"]} >= EFFECT_ROLES | {"PROFIT_BEFORE_TAX", "CURRENT_TAX_PARENT"}
    return records, candidate, context, compiled


def test_recognition_rate_source_only_projection_retains_exact_effect_mappings_as_controls_not_excel_income():
    records, candidate, context, compiled = _generic_candidate_and_context()
    original = deepcopy((records, candidate, context))
    output = _recognition_rate_source_only_projection(candidate, source_context=context)
    assert output["status"] == READY, output["reasons"]
    before = {item["role"]: item for item in candidate["mappings"]}
    after = {item["role"]: item for item in output["mappings"]}
    assert not EFFECT_ROLES & after.keys()
    assert after == {role: mapping for role, mapping in before.items() if role not in EFFECT_ROLES}
    for role in ("PROFIT_BEFORE_TAX", "CURRENT_TAX_PARENT"):
        assert after[role] == before[role]
    receipt = output["closure_receipt"]["recognition_rate_source_only_receipt"]
    suppressed = receipt["suppressed_income_basis_mappings"]
    assert len(suppressed) == 2
    assert {item["mapping"]["report_norm_id"] for item in suppressed} == {compiled["bindings"][role] for role in EFFECT_ROLES}
    assert {item["mapping"]["role"]: item["mapping"] for item in suppressed} == {role: before[role] for role in EFFECT_ROLES}
    assert all(item["schema_exported"] is False for item in suppressed)
    assert all(item["measurement_basis"] == "TAX_EFFECT_NOT_TAXABLE_INCOME_ADJUSTMENT" for item in suppressed)
    assert receipt["independent_source_controls"][0] == context["tax_population_inventory"][0]
    assert receipt["source_values_changed"] is False
    assert (records, candidate, context) == original


@pytest.mark.parametrize("mutation", [
    "coefficient", "source_text", "value_state", "mapping_state", "unit", "money_columns",
    "row_kind", "label", "path", "duplicate_ref", "foreign_extra_ref", "income_equation",
])
def test_recognition_rate_source_only_projection_rejects_forged_matching_source_observations(mutation):
    records, candidate, context, _ = _generic_candidate_and_context()
    mapping = next(item for item in candidate["mappings"] if item["role"] == "NON_TAXABLE_AGGREGATE")
    ref = mapping["source_refs"][0]
    if mutation == "coefficient":
        mapping["values"][0]["coefficient"] = 999
    elif mutation == "source_text":
        mapping["values"][0]["source_text"] = "(999)"
    elif mutation == "value_state":
        mapping["values"][0]["state"] = "DERIVED_VALUE"
    elif mutation == "mapping_state":
        mapping["state"] = "DERIVED_SOURCE_VISIBLE_VALUE"
    elif mutation == "unit":
        mapping["unit"] = "VND"
    elif mutation == "money_columns":
        ref["money_column_ordinals"] = [2, 1]
    elif mutation == "row_kind":
        ref["row_kind"] = "TOTAL"
    elif mutation == "label":
        ref["label_exact"] += " đã điều chỉnh"
    elif mutation == "path":
        ref["hierarchy_path_exact"].insert(0, "Công ty con")
    elif mutation in {"duplicate_ref", "foreign_extra_ref"}:
        extra = deepcopy(ref)
        if mutation == "foreign_extra_ref":
            extra["locator"]["document_id"] = "another-document"
        mapping["source_refs"].append(extra)
    else:
        candidate["closure_receipt"].setdefault("equations", []).append({
            "component_roles": [mapping["role"]], "result_role": "TAXABLE_INCOME",
        })
    before = deepcopy((records, candidate, context))
    output = _recognition_rate_source_only_projection(candidate, source_context=context)
    assert output["status"] == UNRESOLVED, (mutation, output)
    assert output["mappings"] == []
    assert (records, candidate, context) == before


@pytest.mark.parametrize("identity", ["document_id", "document_ordinal", "source_sha256", "page_json_version_id", "physical_page", "section_id", "table_id"])
def test_recognition_rate_source_only_projection_does_not_accept_a_different_source_locator_as_matching(identity):
    records, candidate, context, _ = _generic_candidate_and_context()
    mapping = next(item for item in candidate["mappings"] if item["role"] == "NON_TAXABLE_AGGREGATE")
    mapping["source_refs"][0]["locator"][identity] = 99 if identity in {"document_ordinal", "physical_page"} else "different-source"
    target = deepcopy(mapping)
    before = deepcopy((records, candidate, context))
    output = _recognition_rate_source_only_projection(candidate, source_context=context)
    assert target in output["mappings"]
    receipt = output["closure_receipt"].get("recognition_rate_source_only_receipt")
    assert receipt is None or all(item["mapping"] != target for item in receipt["suppressed_income_basis_mappings"])
    assert (records, candidate, context) == before


def test_recognition_rate_source_only_projection_requires_a_complete_independent_source_control():
    records, candidate, context, _ = _generic_candidate_and_context()
    context["tax_population_inventory"][0]["recognition_rate_effect_control"]["status"] = "ALGORITHM_HOLD"
    before = deepcopy((records, candidate, context))
    assert _recognition_rate_source_only_projection(candidate, source_context=context) == candidate
    assert (records, candidate, context) == before


@pytest.mark.parametrize("equation_role", ["SOURCE_ROW", "UNKNOWN_SOURCE_COMPONENT"])
def test_recognition_rate_source_only_projection_cannot_detach_equations_with_exact_effect_source_refs(equation_role):
    records, candidate, context, _ = _generic_candidate_and_context()
    mapping = next(item for item in candidate["mappings"] if item["role"] == "NON_TAXABLE_AGGREGATE")
    candidate["closure_receipt"].setdefault("equations", []).append({
        "component_roles": [equation_role],
        "result_role": "UNKNOWN_RESULT",
        "component_sources": [{"role": equation_role, "source_refs": deepcopy(mapping["source_refs"])}],
    })
    before = deepcopy((records, candidate, context))
    output = _recognition_rate_source_only_projection(candidate, source_context=context)
    assert output["status"] == UNRESOLVED
    assert output["mappings"] == []
    assert (records, candidate, context) == before


def test_recognition_rate_source_only_projection_cannot_leave_derived_taxable_mapping_using_effect_refs():
    records, candidate, context, compiled = _generic_candidate_and_context()
    derived = deepcopy(next(item for item in candidate["mappings"] if item["role"] == "NON_TAXABLE_AGGREGATE"))
    derived.update(role="TAXABLE_INCOME", report_norm_id=compiled["bindings"]["TAXABLE_INCOME"], state="DERIVED_FROM_SOURCE_ROWS")
    candidate["mappings"].append(derived)
    before = deepcopy((records, candidate, context))
    output = _recognition_rate_source_only_projection(candidate, source_context=context)
    assert output["status"] == UNRESOLVED
    assert output["mappings"] == []
    assert (records, candidate, context) == before


def test_recognition_rate_source_only_projection_cannot_leave_derived_role_receipt_using_effect_refs():
    records, candidate, context, _ = _generic_candidate_and_context()
    mapping = next(item for item in candidate["mappings"] if item["role"] == "NON_TAXABLE_AGGREGATE")
    candidate["closure_receipt"].setdefault("derived_role_receipts", []).append({
        "role": "TAXABLE_INCOME", "component_role": "SOURCE_ROW", "source_refs": deepcopy(mapping["source_refs"]),
    })
    before = deepcopy((records, candidate, context))
    output = _recognition_rate_source_only_projection(candidate, source_context=context)
    assert output["status"] == UNRESOLVED
    assert output["mappings"] == []
    assert (records, candidate, context) == before


def _rate_recognition_signed_records():
    from test_gemini_json_income_tax_recognition_frontier_v1 import (
        _recognition_signed_records,
    )

    records = _recognition_signed_records()
    page, _, _ = _rate_recognition_fixture()
    records[0]["page_json"] = page
    primary = records[1]["page_json"]["sections"][0]
    primary["title_exact"] = "Báo cáo kết quả hoạt động riêng"
    rows = primary["tables"][0]["rows"]
    rows[0]["values_exact"] = ["100", "80"]
    rows[1]["values_exact"] = ["(19)", "(17)"]
    rows[2]["values_exact"] = ["-", "-"]
    rows[3]["values_exact"] = ["(19)", "(17)"]
    rows[4]["values_exact"] = ["81", "63"]
    return records


def _nested_rate_source_only_receipts(value):
    found = []
    if isinstance(value, dict):
        receipt = value.get("recognition_rate_source_only_receipt")
        if isinstance(receipt, dict):
            found.append(receipt)
        for child in value.values():
            found.extend(_nested_rate_source_only_receipts(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_nested_rate_source_only_receipts(child))
    return found


def test_recognition_rate_public_merge_exports_only_authenticated_recognition_not_rate_effect_income():
    from test_gemini_json_income_tax_recognition_frontier_v1 import (
        _public_evaluate,
        _public_query,
    )

    records = _rate_recognition_signed_records()
    original = deepcopy(records)
    compiled = _adapter_compiled()
    cluster, query = _public_query(records, compiled)
    assert cluster["status"] == READY, cluster["reasons"]
    assert query is not None
    candidate = _public_evaluate(records, compiled, cluster, query)
    assert candidate["status"] == READY, candidate["reasons"]
    mappings = {item["role"]: item for item in candidate["mappings"]}
    assert not EFFECT_ROLES & mappings.keys()
    assert not {compiled["bindings"][role] for role in EFFECT_ROLES} & {
        item["report_norm_id"] for item in candidate["mappings"]
    }
    assert [cell["coefficient"] for cell in mappings["PROFIT_BEFORE_TAX"]["values"]] == [100, 80]
    assert [cell["source_text"] for cell in mappings["PROFIT_BEFORE_TAX"]["values"]] == ["100", "80"]
    assert [cell["coefficient"] for cell in mappings["CURRENT_TAX_PARENT"]["values"]] == [19, 17]
    assert [cell["source_text"] for cell in mappings["CURRENT_TAX_PARENT"]["values"]] == ["19", "17"]
    assert [cell["coefficient"] for cell in mappings["DEFERRED_TAX_NET"]["values"]] == [0, 0]
    assert [cell["coefficient"] for cell in mappings["FAMILY_ROOT_TOTAL"]["values"]] == [-19, -17]
    receipts = {item["receipt_id"]: item for item in _nested_rate_source_only_receipts(candidate["closure_receipt"])}
    assert len(receipts) == 1
    suppressed = next(iter(receipts.values()))["suppressed_income_basis_mappings"]
    assert len(suppressed) == 2
    assert {item["mapping"]["role"] for item in suppressed} == EFFECT_ROLES
    assert all(item["schema_exported"] is False for item in suppressed)
    assert records == original


@pytest.mark.parametrize("mutation", [
    "wrong_rate_sum", "blank_rate", "unknown_prefix", "unknown_adjustment_child", "numeric_adjustment_group",
    "numeric_recognition_group", "nonzero_deferred_closing", "unit_conflict", "scope_conflict", "duplicate_adjustment",
    "missing_adjustment_group", "unknown_post_root_child", "blank_calculation", "wrong_calculation", "unknown_root_marker",
])
def test_recognition_rate_public_malformed_prefix_cannot_fallback_after_generic_row_consumption(mutation):
    from test_gemini_json_income_tax_recognition_frontier_v1 import (
        _public_evaluate,
        _public_query,
    )

    records = _rate_recognition_signed_records()
    section = records[0]["page_json"]["sections"][0]
    table = section["tables"][0]
    rows = table["rows"]
    if mutation == "wrong_rate_sum":
        rows[1]["values_exact"][0] = "21"
    elif mutation == "blank_rate":
        rows[1]["values_exact"][0] = None
    elif mutation == "unknown_prefix":
        rows.insert(0, _row("Khoản khác chưa xác định", "0", "0"))
    elif mutation == "unknown_adjustment_child":
        rows[3]["label_exact"] = "Khoản khác chưa xác định"
        rows[3]["hierarchy_path_exact"] = [ADJUSTMENT_GROUP, rows[3]["label_exact"]]
    elif mutation == "numeric_adjustment_group":
        rows[2]["values_exact"] = ["0", "0"]
    elif mutation == "numeric_recognition_group":
        rows[6]["values_exact"] = ["0", "0"]
    elif mutation == "nonzero_deferred_closing":
        rows[8]["values_exact"] = ["1", "2"]
        rows[9]["values_exact"] = ["20", "19"]
    elif mutation == "unit_conflict":
        table["unit_exact"] = "VND"
    elif mutation == "scope_conflict":
        section["title_exact"] = OWNER + " hợp nhất"
    elif mutation == "duplicate_adjustment":
        rows.insert(5, deepcopy(rows[3]))
    elif mutation == "missing_adjustment_group":
        rows.pop(2)
    elif mutation == "unknown_post_root_child":
        unknown = _row("Khoản khác chưa xác định", "0", "0")
        unknown["hierarchy_path_exact"] = [rows[6]["label_exact"], unknown["label_exact"]]
        rows.append(unknown)
    elif mutation == "blank_calculation":
        rows[5]["values_exact"][0] = None
    elif mutation == "wrong_calculation":
        rows[5]["values_exact"][0] = "18"
    else:
        rows[9]["label_exact"] += " (**)"
        rows[9]["hierarchy_path_exact"] = [rows[9]["label_exact"]]
    original = deepcopy(records)
    compiled = _adapter_compiled()
    if mutation == "wrong_rate_sum":
        generic = coalesce_gemini_json_multitable_hierarchical_document_v1(page_records=[records[0]], compiled_specs=compiled)
        assert generic["status"] == READY
        generic_candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
            regions=generic["component_regions"], page_json_by_version={records[0]["page_json_version_id"]: records[0]["page_json"]},
            compiled_specs=compiled,
            query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(generic["component_regions"]),
        )
        assert generic_candidate["status"] == READY, generic_candidate["reasons"]
    cluster, query = _public_query(records, compiled)
    if mutation == "missing_adjustment_group":
        assert cluster["status"] == READY, cluster["reasons"]
        assert query is not None
        candidate = _public_evaluate(records, compiled, cluster, query)
        assert candidate["status"] == READY, candidate["reasons"]
        control = next(item["recognition_rate_effect_control"]
                       for item in query["source_context_receipt"]["tax_population_inventory"]
                       if item["recognition_rate_effect_control"]["status"] == "PASS")
        assert control["adjustment_group_source_row"] is None
        assert control["adjustment_owner_receipt"]["owner_source_row"] is None
        assert control["source_table_rows_exact"] == table["rows"]
        assert not EFFECT_ROLES & {item["role"] for item in candidate["mappings"]}
    elif query is None:
        assert cluster["status"] == UNRESOLVED
    else:
        candidate = _public_evaluate(records, compiled, cluster, query)
        assert candidate["status"] == UNRESOLVED, (mutation, candidate)
        assert candidate["mappings"] == []
    assert records == original
