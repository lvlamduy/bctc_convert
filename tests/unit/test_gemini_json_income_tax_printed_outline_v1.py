"""Synthetic structural interpretation tests; no PDF/source-authentication claim."""
from copy import deepcopy

import pytest
from test_gemini_json_income_tax_family_v1 import _adapter_compiled, _row
from test_gemini_json_income_tax_signed_display_v1 import _candidate, _records

from bctc_ai.evaluation import gemini_json_income_tax_family_v1 as family
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import READY
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROMANS = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII",
          "IX", "X", "XI", "XII", "XIII", "XIV", "XV")


def _outline_records(*, arabic_prefix=2, roman_prefix=9):
    records = _records()
    section = records[-1]["page_json"]["sections"][0]
    table = section["tables"][0]
    before, current, deferred, root, after = table["rows"]
    prefix = []
    for number in range(1, arabic_prefix + 1):
        row = _row(f"Khoản mục nguồn {number}", "1", "1")
        row["values_exact"] = ["1"] * len(table["columns"])
        row["hierarchy_path_exact"] = [str(number), row["label_exact"]]
        prefix.append(row)
    for token in ROMANS[:roman_prefix]:
        row = _row(f"Tổng nguồn {token}", "1", "1", kind="SUBTOTAL")
        row["values_exact"] = ["1"] * len(table["columns"])
        row["hierarchy_path_exact"] = [token, row["label_exact"]]
        prefix.append(row)
    frontier = [before, current, deferred, root, after]
    tokens = [ROMANS[roman_prefix], str(arabic_prefix + 1), str(arabic_prefix + 2),
              ROMANS[roman_prefix + 1], ROMANS[roman_prefix + 2]]
    for row, token in zip(frontier, tokens, strict=True):
        row["hierarchy_path_exact"] = [token, row["label_exact"]]
    table["rows"] = [*prefix, *frontier]
    return records, section, table


@pytest.mark.parametrize("arabic_prefix,roman_prefix", [(2, 9), (6, 10), (1, 2)])
def test_whole_primary_outline_is_relative_not_literal_7_8_xii(arabic_prefix, roman_prefix):
    records, section, table = _outline_records(
        arabic_prefix=arabic_prefix, roman_prefix=roman_prefix)
    original = deepcopy(records)
    proof = family._primary_printed_outline_frontier_receipt_v1(section, table)
    assert proof is not None
    assert proof["arabic_outline_length"] == arabic_prefix + 2
    assert proof["roman_outline_length"] == roman_prefix + 3
    assert len(proof["permitted_frontier_tokens"]) == 5
    assert all(proof[key] is False for key in (
        "amounts_used_as_authority", "source_values_changed", "report_scope_permission_granted",
        "entity_permission_granted", "unit_permission_granted", "period_permission_granted",
        "source_kind_permission_granted"))
    material = {key: value for key, value in proof.items() if key != "receipt_id"}
    assert proof["receipt_id"] == "gjitfav1:printed-primary-outline:" + canonical_json_sha256_v1(material)
    descriptor = family._primary_presentations(records, compiled_specs=_adapter_compiled())[0]
    ancestry = descriptor["expense_display_receipt"]["population_ancestry_receipt"]
    assert ancestry["common_population_ancestry_exact"] == []
    assert ancestry["printed_primary_outline_receipt"] == proof
    assert records == original


@pytest.mark.parametrize("mutation", [
    "hole", "duplicate", "reverse", "leading_zero", "fullwidth", "unicode_roman",
    "annotated_code", "group", "extra_entity", "missing_code", "wrong_path_label",
    "wrong_owner", "wrong_statement", "duplicate_table", "width", "swapped_roles",
    "root_before_components", "extra_tax_role", "trailing_unknown",
])
def test_incomplete_or_population_qualified_outline_grants_no_permission(mutation):
    records, section, table = _outline_records()
    rows = table["rows"]
    if mutation == "hole":
        rows.pop(0)
    elif mutation == "duplicate":
        rows.insert(1, deepcopy(rows[0]))
    elif mutation == "reverse":
        rows[0], rows[1] = rows[1], rows[0]
    elif mutation == "leading_zero":
        rows[0]["hierarchy_path_exact"][0] = "01"
    elif mutation == "fullwidth":
        rows[0]["hierarchy_path_exact"][0] = "１"
    elif mutation == "unicode_roman":
        rows[2]["hierarchy_path_exact"][0] = "Ⅰ"
    elif mutation == "annotated_code":
        rows[-4]["hierarchy_path_exact"][0] += "\u0301"
    elif mutation == "group":
        rows[0]["row_kind"] = "GROUP"
    elif mutation == "extra_entity":
        rows[-4]["hierarchy_path_exact"].insert(0, "Công ty con")
    elif mutation == "missing_code":
        rows[0]["hierarchy_path_exact"] = [rows[0]["label_exact"]]
    elif mutation == "wrong_path_label":
        rows[0]["hierarchy_path_exact"][-1] = "Nhãn khác"
    elif mutation == "wrong_owner":
        section["content_kind"] = "FINANCIAL_NOTE"
    elif mutation == "wrong_statement":
        section["statement_type"] = "CASH_FLOW"
    elif mutation == "duplicate_table":
        section["tables"].append(deepcopy(table))
    elif mutation == "width":
        rows[0]["values_exact"].pop()
    elif mutation == "swapped_roles":
        rows[-4], rows[-3] = rows[-3], rows[-4]
    elif mutation == "root_before_components":
        rows[-4], rows[-2] = rows[-2], rows[-4]
    elif mutation == "extra_tax_role":
        rows[0]["label_exact"] = rows[-4]["label_exact"]
        rows[0]["hierarchy_path_exact"][-1] = rows[0]["label_exact"]
    else:
        rows.append(deepcopy(rows[0]))
    assert family._primary_printed_outline_frontier_receipt_v1(section, table) is None
    # Old fallback cannot erase an isolated numeric token just because it resembles an outline.
    bridge = family._primary_bridge_population_ancestry(
        table, row_ordinals=[len(rows) - 3], primary_section=section)
    if bridge is not None:
        assert "printed_primary_outline_receipt" not in bridge


def test_whole_outline_does_not_choose_totals_by_amount_or_make_blank_zero():
    records, section, table = _outline_records()
    table["rows"][-1]["values_exact"][-1] = "999"
    assert family._primary_printed_outline_frontier_receipt_v1(section, table) is not None
    assert family._primary_presentations(records, compiled_specs=_adapter_compiled())[0]["expense_display_receipt"] is None
    table["rows"][-1]["values_exact"][-1] = None
    assert family._primary_printed_outline_frontier_receipt_v1(section, table) is not None
    assert family._primary_presentations(records, compiled_specs=_adapter_compiled())[0]["expense_display_receipt"] is None


def test_whole_outline_permission_never_leaks_to_note_fallback_or_resealed_claim():
    records, section, table = _outline_records()
    proof = family._primary_printed_outline_frontier_receipt_v1(section, table)
    assert proof is not None
    proof["permitted_frontier_tokens"][1]["source_token_exact"] = "2025"
    row_ordinals = list(range(len(table["rows"]) - 4, len(table["rows"]) + 1))
    assert family._primary_bridge_population_ancestry(table, row_ordinals=row_ordinals) is None
    fresh = family._primary_bridge_population_ancestry(
        table, row_ordinals=row_ordinals, primary_section=section)
    assert fresh["printed_primary_outline_receipt"] != proof
    assert fresh["common_population_ancestry_exact"] == []
    table["rows"][-4]["hierarchy_path_exact"][0] = "2025"
    assert family._primary_bridge_population_ancestry(
        table, row_ordinals=row_ordinals, primary_section=section) is None


def test_public_outline_bridge_preserves_source_and_uses_existing_signed_display():
    records, section, table = _outline_records()
    original = deepcopy(records)
    candidate = _candidate(records)
    assert candidate["status"] == READY, candidate["reasons"]
    proof = candidate["closure_receipt"]["income_tax_adapter_receipt"]["primary_candidate_proof"]["signed_display_proof"]
    assert proof["source_values_changed"] is False
    controls = candidate["closure_receipt"]["income_tax_source_control_receipt"]
    assert controls["printed_primary_outline_receipt"] == family._primary_printed_outline_frontier_receipt_v1(section, table)
    assert proof["primary_expense_display_receipt"]["population_ancestry_receipt"]["printed_primary_outline_receipt"] == controls["printed_primary_outline_receipt"]
    assert records == original


def test_primary_original_population_consumer_recomputes_same_outline():
    records, section, table = _outline_records()
    compiled = _adapter_compiled()
    descriptor = family._primary_presentations(records, compiled_specs=compiled)[0]
    issues = []
    receipt = family._original_note_population_proofs(
        [], page_records=records, primary={"descriptor": descriptor}, compiled_specs=compiled,
        issues=issues, document_period_inventory=family._document_statement_period_inventory(
            records, compiled_specs=compiled))
    ancestry = receipt["populations"][0]["primary_population_ancestry_receipt"]
    assert ancestry["printed_primary_outline_receipt"] == family._primary_printed_outline_frontier_receipt_v1(section, table)
    assert "ORIGINAL_NOTE_PRIMARY_POPULATION_ANCESTRY_UNPROVEN" not in issues


def test_source_shaped_twenty_one_row_interleaving_and_separate_text_note_column():
    records, section, table = _outline_records(arabic_prefix=6, roman_prefix=10)
    prefix_by_code = {row["hierarchy_path_exact"][0]: row for row in table["rows"][:-5]}
    prefix_codes = ["1", "2", "I", "3", "4", "II", "III", "IV", "V",
                    "5", "6", "VI", "VII", "VIII", "IX", "X"]
    table["rows"] = [*[prefix_by_code[token] for token in prefix_codes], *table["rows"][-5:]]
    table["columns"] = [
        {"header_path_exact": ["Thuyết minh"], "value_kind": "TEXT"},
        {"header_path_exact": ["Kỳ 6 tháng kết thúc ngày", "30.6.2025", "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": ["Kỳ 6 tháng kết thúc ngày", "30.6.2024", "Triệu đồng"], "value_kind": "MONEY"},
    ]
    for row in table["rows"]:
        row["values_exact"] = [None, *row["values_exact"][-2:]]
    # Literal note reference is a separate TEXT cell, never the printed path code.
    table["rows"][-2]["values_exact"][0] = "28"
    section["title_exact"] = "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG RIÊNG GIỮA NIÊN ĐỘ"
    original = deepcopy(records)
    proof = family._primary_printed_outline_frontier_receipt_v1(section, table)
    assert proof is not None
    assert [item["source_token_exact"] for item in proof["ordered_outline_axis"]] == [
        *prefix_codes, "XI", "7", "8", "XII", "XIII"]
    assert [(item["row_ordinal"], item["semantic_role"]) for item in proof["permitted_frontier_tokens"]] == [
        (17, "PROFIT_BEFORE_TAX"), (18, "CURRENT_TAX_PARENT"), (19, "DEFERRED_TAX_NET"),
        (20, "FAMILY_ROOT_TOTAL"), (21, "PROFIT_AFTER_TAX")]
    assert proof["source_columns_exact"][0]["value_kind"] == "TEXT"
    assert proof["source_rows_exact"][-2]["values_exact"][0] == "28"
    descriptor = family._primary_presentations(records, compiled_specs=_adapter_compiled())[0]
    assert descriptor["money_column_ordinals"] == [2, 3]
    assert descriptor["expense_display_receipt"]["population_ancestry_receipt"]["printed_primary_outline_receipt"] == proof
    assert records == original
