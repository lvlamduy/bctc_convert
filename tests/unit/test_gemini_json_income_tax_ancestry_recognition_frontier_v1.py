"""Exact repeated source owners are not fabricated GROUP rows or acceptance."""
from __future__ import annotations

from copy import deepcopy

import pytest
from test_gemini_json_income_tax_family_v1 import _adapter_compiled, _row
from test_gemini_json_income_tax_recognition_frontier_v1 import (
    _public_evaluate,
    _public_query,
    _recognition_fixture,
    _recognition_signed_records,
    _reseal_public_receipt_ids,
)
from test_gemini_json_income_tax_recognition_rate_effect_v1 import (
    ADJUSTMENT_GROUP,
    EFFECT_ROLES,
    _rate_recognition_fixture,
    _rate_recognition_signed_records,
)

from bctc_ai.evaluation import gemini_json_income_tax_family_v1 as family
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import READY, UNRESOLVED
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _remove_actual_groups(table, *, recognition=True, adjustment=True, compound=True):
    rows = table["rows"]
    if recognition:
        rows[:] = [row for row in rows if not (
            row["row_kind"] == "GROUP" and "ghi nhận" in row["label_exact"])]
    if adjustment:
        rows[:] = [row for row in rows if row["label_exact"] != ADJUSTMENT_GROUP]
    if compound:
        first = next(row for row in rows if row["hierarchy_path_exact"][0] == ADJUSTMENT_GROUP)
        first["label_exact"] = ADJUSTMENT_GROUP + "\n" + first["hierarchy_path_exact"][-1]


def _fixture(*, variant="basic", compound=True, recognition=True, adjustment=True):
    _, section, table = _rate_recognition_fixture(variant=variant)
    _remove_actual_groups(table, recognition=recognition, adjustment=adjustment, compound=compound)
    return section, table


def _records(*, prefix=True):
    records = _rate_recognition_signed_records() if prefix else _recognition_signed_records()
    table = records[0]["page_json"]["sections"][0]["tables"][0]
    _remove_actual_groups(table, adjustment=prefix, compound=prefix)
    return records


def _proofs(section, table):
    before = deepcopy(section)
    compiled = _adapter_compiled()
    recognition = family._recognition_expense_source_frontier(section, table, compiled_specs=compiled)
    rate = family._recognition_rate_effect_forward_control(section, table, compiled_specs=compiled)
    assert section == before
    return recognition, rate


@pytest.mark.parametrize("variant", ["basic", "consolidated", "prior", "all_adjustments", "dash_adjustments",
                                     "calculation_total", "annotated_root", "vnd", "not_twenty_percent"])
@pytest.mark.parametrize("compound", [False, True])
def test_repeated_ancestry_authenticates_whole_finite_source_without_fake_group(variant, compound):
    section, table = _fixture(variant=variant, compound=compound)
    recognition, rate = _proofs(section, table)
    assert recognition["status"] == "PASS", recognition["reasons"]
    assert rate["status"] == "PASS", rate["reasons"]
    assert recognition["group_source_row"] is None
    assert rate["adjustment_group_source_row"] is None
    assert recognition["group_created"] is False
    assert rate["schema_mapping_authority"] is False
    assert rate["profit_times_rate_used"] is False
    owner = recognition["owner_receipt"]
    assert owner["owner_source_row"] is None
    current, deferred, root = (recognition[key] for key in (
        "current_source_row", "deferred_source_row", "parent_source_row"))
    assert [item["row_ordinal"] for item in owner["owner_occurrences"]] == [current["row_ordinal"], deferred["row_ordinal"]]
    assert recognition["frontier_start_source_row_ordinal"] == current["row_ordinal"]
    assert owner["scope_unit_period_or_amount_authority"] is False
    assert owner["source_table_row_axis_sha256"] == canonical_json_sha256_v1(recognition["source_table_row_axis"])
    assert [current["row_ordinal"], deferred["row_ordinal"], root["row_ordinal"]] == list(range(len(table["rows"]) - 2, len(table["rows"]) + 1))
    adjustment = rate["adjustment_owner_receipt"]
    assert adjustment["owner_exact"] == ADJUSTMENT_GROUP
    assert adjustment["raw_leaf_evidence"][0]["whole_owner_newline_leaf_label"] is compound
    assert rate["source_table_rows_exact"] == table["rows"]
    assert len(rate["lane_equations"]) == 2
    assert all(item["residual"] == item["calculation_current_residual"] == 0 for item in rate["lane_equations"])
    assert _proofs(section, table) == (recognition, rate)


@pytest.mark.parametrize("recognition,adjustment", [(True, False), (False, True)])
def test_actual_and_ancestry_owners_may_coexist_without_representing_either_as_the_other(recognition, adjustment):
    section, table = _fixture(recognition=recognition, adjustment=adjustment, compound=adjustment)
    front, control = _proofs(section, table)
    assert front["status"] == control["status"] == "PASS"
    assert (front["group_source_row"] is None) is recognition
    assert (control["adjustment_group_source_row"] is None) is adjustment


@pytest.mark.parametrize("zero", ["-", " -", "0"])
def test_pure_recognition_repeated_owner_needs_no_invented_rate_prefix(zero):
    section, table = _recognition_fixture(zero=zero)
    table["rows"].pop(0)
    front, control = _proofs(section, table)
    assert front["status"] == "PASS", front["reasons"]
    assert control["status"] == "NOT_APPLICABLE"
    assert front["deferred_source_row"]["source_values_exact"] == [zero, zero]


def test_no_recognition_owner_anywhere_does_not_invent_ancestry_permission():
    section, table = _recognition_fixture()
    table["rows"].pop(0)
    for row in table["rows"]:
        row["hierarchy_path_exact"] = [row["label_exact"]]
    front, control = _proofs(section, table)
    assert front["status"] == control["status"] == "NOT_APPLICABLE"


def test_original_population_consumers_rebuild_the_same_owner_and_keep_scope_paths():
    section, table = _fixture()
    compiled = _adapter_compiled()
    front, control = _proofs(section, table)
    for source in front["component_source_rows"]:
        population = family._original_note_population_ancestry(
            table, section, row_ordinal=source["row_ordinal"], compiled_specs=compiled,
        )
        assert population["common_population_ancestry_exact"] == []
        assert population["recognition_expense_frontier_receipt"] == front
        assert population["printed_scope_source_paths_exact"] == front["printed_scope_source_paths_exact"]
    for source in control["adjustment_source_rows"]:
        population = family._original_note_population_ancestry(
            table, section, row_ordinal=source["row_ordinal"], compiled_specs=compiled,
        )
        assert population["common_population_ancestry_exact"] == []
        assert population["recognition_rate_effect_control"] == control
        assert population["source_rows"][0]["label_exact"] == source["label_exact"]


@pytest.mark.parametrize("mutation", [
    "one_owner", "different_raw_owner", "owner_without_scope", "owner_annotation", "deeper_current",
    "deeper_deferred", "foreign_current", "interposed", "extra_descendant", "duplicate_current",
    "duplicate_deferred", "duplicate_root", "trailing_row", "reversed_children", "root_under_owner",
    "current_blank", "current_double_cell", "deferred_blank", "deferred_empty", "deferred_unknown",
    "deferred_nonzero_closing", "root_mismatch", "scope_conflict", "unit_conflict", "unit_missing",
    "current_annotation", "root_annotation", "rate_blank", "rate_sum", "calculation_blank",
    "adjustment_one_owner", "adjustment_foreign", "adjustment_deeper", "adjustment_extra",
    "adjustment_duplicate", "adjustment_reversed", "compound_annotation", "compound_extra_line",
    "compound_wrong_owner", "compound_wrong_leaf", "compound_second_child", "compound_inline_no_newline",
    "actual_bad_recognition_group", "actual_bad_adjustment_group", "unknown_prefix",
])
def test_incomplete_or_conflicting_ancestry_never_rescues_the_finite_frontier(mutation):
    section, table = _fixture()
    rows = table["rows"]
    current, deferred, root = rows[-3:]
    owner = current["hierarchy_path_exact"][0]
    if mutation == "one_owner":
        deferred["hierarchy_path_exact"] = [deferred["label_exact"]]
    elif mutation in {"different_raw_owner", "owner_without_scope", "owner_annotation"}:
        replacement = {"different_raw_owner": owner.upper(), "owner_without_scope": owner.replace(" riêng", ""),
                       "owner_annotation": owner + "\u20dd"}[mutation]
        targets = [deferred] if mutation == "different_raw_owner" else [current, deferred]
        for row in targets:
            row["hierarchy_path_exact"][0] = replacement
    elif mutation in {"deeper_current", "deeper_deferred", "foreign_current"}:
        row = deferred if mutation == "deeper_deferred" else current
        row["hierarchy_path_exact"].insert(0 if mutation == "foreign_current" else 1, "Ngân hàng mẹ")
    elif mutation in {"interposed", "extra_descendant"}:
        extra = _row("Khoản nguồn chưa xác định", "0", "0")
        if mutation == "extra_descendant":
            extra["hierarchy_path_exact"].insert(0, owner)
        rows.insert(len(rows) - 2, extra)
    elif mutation in {"duplicate_current", "duplicate_deferred", "duplicate_root"}:
        rows.append(deepcopy({"duplicate_current": current, "duplicate_deferred": deferred, "duplicate_root": root}[mutation]))
    elif mutation == "trailing_row":
        rows.append(_row("Khoản nguồn khác", "0", "0"))
    elif mutation == "reversed_children":
        rows[-3], rows[-2] = rows[-2], rows[-3]
    elif mutation == "root_under_owner":
        root["hierarchy_path_exact"].insert(0, owner)
    elif mutation in {"current_blank", "current_double_cell"}:
        current["values_exact"][0] = None if mutation == "current_blank" else "19\n19"
    elif mutation in {"deferred_blank", "deferred_empty", "deferred_unknown"}:
        deferred["values_exact"][0] = {"deferred_blank": None, "deferred_empty": "", "deferred_unknown": "?"}[mutation]
    elif mutation == "deferred_nonzero_closing":
        deferred["values_exact"] = ["1", "2"]
        root["values_exact"] = ["20", "19"]
    elif mutation == "root_mismatch":
        root["values_exact"][0] = "999"
    elif mutation == "scope_conflict":
        section["title_exact"] += " hợp nhất"
    elif mutation == "unit_conflict":
        table["unit_exact"] = "VND"
    elif mutation == "unit_missing":
        table["unit_exact"] = None
        for column in table["columns"]:
            column["header_path_exact"].pop()
    elif mutation in {"current_annotation", "root_annotation"}:
        row = current if mutation == "current_annotation" else root
        row["label_exact"] += "\u0338"
        row["hierarchy_path_exact"][-1] = row["label_exact"]
    elif mutation in {"rate_blank", "rate_sum", "calculation_blank"}:
        rows[1 if mutation != "calculation_blank" else 4]["values_exact"][0] = "21" if mutation == "rate_sum" else None
    elif mutation in {"adjustment_one_owner", "adjustment_foreign", "adjustment_deeper"}:
        row = rows[3]
        if mutation == "adjustment_one_owner":
            row["hierarchy_path_exact"] = [row["label_exact"]]
        else:
            row["hierarchy_path_exact"].insert(0 if mutation == "adjustment_foreign" else 1, "Công ty con")
    elif mutation in {"adjustment_extra", "adjustment_duplicate"}:
        extra = deepcopy(rows[3]) if mutation == "adjustment_duplicate" else _row("Khoản điều chỉnh khác chưa rõ", "0", "0")
        if mutation == "adjustment_extra":
            extra["hierarchy_path_exact"].insert(0, ADJUSTMENT_GROUP)
        rows.insert(4, extra)
    elif mutation == "adjustment_reversed":
        rows[2], rows[3] = rows[3], rows[2]
    elif mutation.startswith("compound_"):
        first = rows[2]
        if mutation == "compound_annotation":
            first["label_exact"] += " (*)"
        elif mutation == "compound_extra_line":
            first["label_exact"] += "\nKhoản khác"
        elif mutation == "compound_wrong_owner":
            first["label_exact"] = "Điều chỉnh khác:\n" + first["hierarchy_path_exact"][-1]
        elif mutation == "compound_wrong_leaf":
            first["label_exact"] = ADJUSTMENT_GROUP + "\nChi phí khác"
        elif mutation == "compound_second_child":
            rows[3]["label_exact"] = ADJUSTMENT_GROUP + "\n" + rows[3]["label_exact"]
        else:
            first["label_exact"] = first["label_exact"].replace("\n", " ")
    elif mutation == "actual_bad_recognition_group":
        rows.insert(len(rows) - 3, _row(owner, "0", "0", kind="GROUP"))
    elif mutation == "actual_bad_adjustment_group":
        rows.insert(2, _row(ADJUSTMENT_GROUP, "0", "0", kind="GROUP"))
    else:
        rows.insert(0, _row("Préfixe nguồn khác", "0", "0"))
    front, control = _proofs(section, table)
    assert front["status"] == "ALGORITHM_HOLD" or control["status"] == "ALGORITHM_HOLD", (mutation, front, control)


@pytest.mark.parametrize("prefix", [False, True])
def test_public_repeated_owner_keeps_raw_source_and_exports_only_recognition_semantics(prefix):
    records = _records(prefix=prefix)
    before = deepcopy(records)
    compiled = _adapter_compiled()
    cluster, query = _public_query(records, compiled)
    assert cluster["status"] == READY, cluster["reasons"]
    assert query is not None
    inventory = query["source_context_receipt"]["tax_population_inventory"]
    front = next(item["recognition_expense_frontier"] for item in inventory
                 if item["recognition_expense_frontier"]["status"] == "PASS")
    assert front["group_source_row"] is None
    candidate = _public_evaluate(records, compiled, cluster, query)
    assert candidate["status"] == READY, candidate["reasons"]
    mappings = {item["role"]: item for item in candidate["mappings"]}
    assert not EFFECT_ROLES & mappings.keys()
    assert [cell["coefficient"] for cell in mappings["CURRENT_TAX_PARENT"]["values"]] == ([19, 17] if prefix else [20, 16])
    assert [cell["coefficient"] for cell in mappings["DEFERRED_TAX_NET"]["values"]] == [0, 0]
    if prefix:
        assert [cell["coefficient"] for cell in mappings["PROFIT_BEFORE_TAX"]["values"]] == [100, 80]
        control = next(item["recognition_rate_effect_control"] for item in inventory
                       if item["recognition_rate_effect_control"]["status"] == "PASS")
        assert control["adjustment_group_source_row"] is None
        assert control["source_table_rows_exact"][2]["label_exact"].startswith(ADJUSTMENT_GROUP + "\n")
    assert records == before


@pytest.mark.parametrize("mutation", ["scope", "period", "blank", "extra", "actual_group", "adjustment_annotation"])
def test_public_ancestry_frontier_conflicts_cannot_fallback_to_generic_consumed_rows(mutation):
    records = _records()
    section = records[0]["page_json"]["sections"][0]
    table = section["tables"][0]
    if mutation == "scope":
        section["title_exact"] += " hợp nhất"
    elif mutation == "period":
        table["columns"][0]["header_path_exact"][0] = "Năm 2023"
    elif mutation == "blank":
        table["rows"][-2]["values_exact"][0] = None
    elif mutation == "extra":
        table["rows"].append(_row("Khoản nguồn khác", "0", "0"))
    elif mutation == "actual_group":
        owner = table["rows"][-3]["hierarchy_path_exact"][0]
        table["rows"].insert(len(table["rows"]) - 3, _row(owner, "0", "0", kind="GROUP"))
    else:
        table["rows"][2]["label_exact"] += " (*)"
    before = deepcopy(records)
    compiled = _adapter_compiled()
    cluster, query = _public_query(records, compiled)
    if query is None:
        assert cluster["status"] == UNRESOLVED
    else:
        result = _public_evaluate(records, compiled, cluster, query)
        assert result["status"] == UNRESOLVED, result
        assert result["mappings"] == []
    assert records == before


@pytest.mark.parametrize("mutation", ["owner_occurrence", "owner_scope", "fake_group", "adjustment_owner", "raw_axis"])
def test_public_fresh_rebuild_rejects_resealed_ancestry_owner_or_raw_axis_tamper(mutation):
    records = _records()
    before = deepcopy(records)
    compiled = _adapter_compiled()
    cluster, query = _public_query(records, compiled)
    assert cluster["status"] == READY, cluster["reasons"]
    forged = deepcopy(query)
    item = next(item for item in forged["source_context_receipt"]["tax_population_inventory"]
                if item["recognition_expense_frontier"]["status"] == "PASS")
    frontier = item["recognition_expense_frontier"]
    if mutation == "owner_occurrence":
        frontier["owner_receipt"]["owner_occurrences"][0]["row_ordinal"] += 1
    elif mutation == "owner_scope":
        frontier["owner_receipt"]["owner_exact"] += " hợp nhất"
    elif mutation == "fake_group":
        frontier["group_source_row"] = deepcopy(frontier["current_source_row"])
        frontier["group_source_row"]["row_kind"] = "GROUP"
    elif mutation == "adjustment_owner":
        item["recognition_rate_effect_control"]["adjustment_owner_receipt"]["owner_occurrences"].pop()
    else:
        item["source_table_rows_exact"][0]["values_exact"][0] = "101"
    _reseal_public_receipt_ids(forged)
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error):
        _public_evaluate(records, compiled, cluster, forged)
    assert records == before


@pytest.mark.parametrize("name", ["_recognition_immediate_ancestor_owner_v1", "_recognition_expense_source_frontier",
                                  "_recognition_rate_effect_forward_control"])
def test_ancestry_frontier_callable_drift_cannot_escape_operation_barrier(monkeypatch, name):
    records, compiled = _records(), _adapter_compiled()
    original = getattr(family, name)
    accepted = []
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="changed during operation"):
        with family.income_tax_document_period_evaluation_scope_v1():
            provisional = family._document_statement_period_inventory(records, compiled_specs=compiled)
            monkeypatch.setattr(family, name, lambda *args, **kwargs: original(*args, **kwargs))
        accepted.append(provisional)
    assert accepted == []
