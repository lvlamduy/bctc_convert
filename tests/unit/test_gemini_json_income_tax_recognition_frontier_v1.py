"""Local source-frontier tests; PASS here is not document/family acceptance."""
from __future__ import annotations

import re
from copy import deepcopy

import pytest
from test_gemini_json_income_tax_family_v1 import (
    OWNER,
    _adapter_compiled,
    _page,
    _printed_annual_primary,
    _row,
    _table,
)
from test_gemini_json_income_tax_signed_display_v1 import _records as _signed_records

from bctc_ai.evaluation.gemini_json_income_tax_family_v1 import (
    GeminiJsonIncomeTaxFamilyV1Error,
    _recognition_expense_source_frontier,
    build_gemini_json_income_tax_region_query_receipt_v1,
    evaluate_gemini_json_income_tax_family_cluster_v1,
    recover_gemini_json_income_tax_query_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


CURRENT = "Chi phí thuế TNDN - hiện hành"
DEFERRED = "Thu nhập thuế TNDN - hoãn lại"
ROOT = "Chi phí thuế TNDN"
ANNOTATION = (
    "(*) Chi phí thuế TNDN cho kỳ kế toán được ước tính dựa vào thu nhập chịu thuế "
    "và có thể có những điều chỉnh tùy thuộc vào sự kiểm tra của cơ quan thuế."
)


def _recognition_fixture(*, scope="riêng", interim=True, zero="-", annotated=False):
    group = "Chi phí thuế TNDN ghi nhận trong báo cáo kết quả hoạt động " + scope
    if interim:
        group += " giữa niên độ"
    group += ":"
    parent = ROOT + (" (*)" if annotated else "")
    page = _page([
        _row(group, None, None, kind="GROUP"),
        {**_row(CURRENT, "20", "16"), "hierarchy_path_exact": [group, CURRENT]},
        {**_row(DEFERRED, zero, zero), "hierarchy_path_exact": [group, DEFERRED]},
        _row(parent, "20", "16", kind="TOTAL"),
    ], owner=OWNER + " " + scope)
    section = page["sections"][0]
    if annotated:
        section["narratives_exact"].append(ANNOTATION)
    return section, section["tables"][0]


def _check(section, table):
    before = deepcopy(section)
    receipt = _recognition_expense_source_frontier(section, table, compiled_specs=_adapter_compiled())
    assert section == before
    assert isinstance(receipt, dict)
    assert isinstance(receipt["reasons"], list)
    assert receipt["status"] in {"NOT_APPLICABLE", "PASS", "ALGORITHM_HOLD"}
    return receipt


@pytest.mark.parametrize("scope", ["riêng", "hợp nhất"])
@pytest.mark.parametrize("interim", [False, True])
@pytest.mark.parametrize("zero", ["0", "-"])
def test_recognition_frontier_authenticates_actual_blank_group_and_observed_zero(scope, interim, zero):
    section, table = _recognition_fixture(scope=scope, interim=interim, zero=zero)
    receipt = _check(section, table)
    assert receipt["status"] == "PASS", receipt["reasons"]
    assert receipt["reasons"] == []
    for field, index in (
        ("group_source_row", 0), ("current_source_row", 1),
        ("deferred_source_row", 2), ("parent_source_row", 3),
    ):
        source = receipt[field]
        assert source["row_ordinal"] == index + 1
        assert source["label_exact"] == table["rows"][index]["label_exact"]
        assert source["hierarchy_path_exact"] == table["rows"][index]["hierarchy_path_exact"]
        assert source["source_values_exact"] == table["rows"][index]["values_exact"]
    assert receipt["group_source_row"]["source_values_exact"] == [None, None]
    assert receipt["deferred_source_row"]["source_values_exact"] == [zero, zero]
    assert receipt["component_source_rows"] == [receipt["current_source_row"], receipt["deferred_source_row"]]
    assert receipt["lane_axis"]["complete"] is True
    assert receipt["unit_axis"]["canonical_unit"] == "MILLION_VND"
    assert len(receipt["lane_equations"]) == 2
    assert any(table["rows"][0]["label_exact"] in path for path in receipt["printed_scope_source_paths_exact"])
    assert "root_annotation_receipt" in receipt
    assert _check(section, table) == receipt


@pytest.mark.parametrize("qualifier", ["hợp nhất", "Ngân hàng mẹ", "Công ty con"])
def test_recognition_frontier_cannot_discard_explicit_money_header_population(qualifier):
    section, table = _recognition_fixture()
    table["columns"][0]["header_path_exact"].append(qualifier)
    receipt = _check(section, table)
    assert receipt["status"] == "ALGORITHM_HOLD"
    assert receipt["reasons"]


def test_recognition_frontier_unrelated_tax_table_is_not_applicable_not_a_fake_group():
    section = _page([
        _row(CURRENT, "20", "16"),
        _row(DEFERRED, "0", "0"),
        _row(ROOT, "20", "16", kind="TOTAL"),
    ])["sections"][0]
    receipt = _check(section, section["tables"][0])
    assert receipt["status"] == "NOT_APPLICABLE"


@pytest.mark.parametrize("mutation", [
    "item_instead_of_group", "numeric_group", "dash_group", "partial_group",
    "duplicate_group", "missing_current", "missing_deferred", "missing_root",
    "reversed_children", "extra_child", "intervening_group", "duplicate_current",
    "duplicate_deferred", "duplicate_root", "duplicate_current_before_group",
    "duplicate_deferred_after_root", "foreign_group_ancestor", "foreign_current_ancestor",
    "foreign_deferred_ancestor", "root_under_group", "caption_scope_conflict",
    "child_entity_override", "explicit_unit_conflict", "unsupported_explicit_unit",
    "no_printed_unit", "extra_money_lane", "single_money_lane", "current_blank",
    "current_marker", "deferred_blank", "deferred_empty_string", "deferred_marker",
    "nonzero_deferred_with_closing_arithmetic", "partially_nonzero_deferred",
    "root_blank", "root_mismatch", "marked_root_without_annotation",
    "unknown_root_marker", "superscript_root_marker", "other_semantic_root",
    "qualified_group", "ambiguous_group_scope",
])
def test_recognition_frontier_recognized_but_invalid_source_is_hold_never_fallback(mutation):
    section, table = _recognition_fixture()
    rows = table["rows"]
    if mutation == "item_instead_of_group":
        rows[0]["row_kind"] = "ITEM"
    elif mutation in {"numeric_group", "dash_group", "partial_group"}:
        rows[0]["values_exact"] = {"numeric_group": ["0", "0"], "dash_group": ["-", "-"], "partial_group": [None, "0"]}[mutation]
    elif mutation == "duplicate_group":
        rows.append(deepcopy(rows[0]))
    elif mutation in {"missing_current", "missing_deferred", "missing_root"}:
        rows.pop({"missing_current": 1, "missing_deferred": 2, "missing_root": 3}[mutation])
    elif mutation == "reversed_children":
        rows[1], rows[2] = rows[2], rows[1]
    elif mutation in {"extra_child", "intervening_group"}:
        label = "Khoản mục khác chưa có nghĩa được xác định"
        child = _row(label, "0", "0") if mutation == "extra_child" else _row(label, None, None, kind="GROUP")
        child["hierarchy_path_exact"] = [rows[0]["label_exact"], label]
        rows.insert(2, child)
    elif mutation in {"duplicate_current", "duplicate_deferred", "duplicate_root"}:
        rows.append(deepcopy(rows[{"duplicate_current": 1, "duplicate_deferred": 2, "duplicate_root": 3}[mutation]]))
    elif mutation == "duplicate_current_before_group":
        duplicate = deepcopy(rows[1])
        duplicate["hierarchy_path_exact"] = [CURRENT]
        rows.insert(0, duplicate)
    elif mutation == "duplicate_deferred_after_root":
        duplicate = deepcopy(rows[2])
        duplicate["hierarchy_path_exact"] = [DEFERRED]
        rows.append(duplicate)
    elif mutation in {"foreign_group_ancestor", "foreign_current_ancestor", "foreign_deferred_ancestor"}:
        rows[{"foreign_group_ancestor": 0, "foreign_current_ancestor": 1, "foreign_deferred_ancestor": 2}[mutation]]["hierarchy_path_exact"].insert(0, "Ngân hàng mẹ")
    elif mutation == "root_under_group":
        rows[3]["hierarchy_path_exact"] = [rows[0]["label_exact"], ROOT]
    elif mutation == "caption_scope_conflict":
        section["title_exact"] = OWNER + " hợp nhất"
    elif mutation == "child_entity_override":
        rows[1]["hierarchy_path_exact"].insert(1, "Công ty con")
    elif mutation == "explicit_unit_conflict":
        table["unit_exact"] = "VND"
    elif mutation == "unsupported_explicit_unit":
        table["unit_exact"] = "USD"
        for column in table["columns"]:
            column["header_path_exact"][-1] = "USD"
    elif mutation == "no_printed_unit":
        table["unit_exact"] = None
        for column in table["columns"]:
            column["header_path_exact"].pop()
    elif mutation == "extra_money_lane":
        table["columns"].append({"header_path_exact": ["Năm 2024", "Triệu đồng"], "value_kind": "MONEY"})
        for row in rows:
            row["values_exact"].append(None if row["row_kind"] == "GROUP" else "0")
    elif mutation == "single_money_lane":
        table["columns"].pop()
        for row in rows:
            row["values_exact"].pop()
    elif mutation in {"current_blank", "current_marker"}:
        rows[1]["values_exact"][0] = None if mutation == "current_blank" else "?"
    elif mutation in {"deferred_blank", "deferred_empty_string", "deferred_marker"}:
        rows[2]["values_exact"][0] = {"deferred_blank": None, "deferred_empty_string": "", "deferred_marker": "?"}[mutation]
    elif mutation == "nonzero_deferred_with_closing_arithmetic":
        rows[2]["values_exact"] = ["1", "2"]
        rows[3]["values_exact"] = ["21", "18"]
    elif mutation == "partially_nonzero_deferred":
        rows[2]["values_exact"] = ["0", "1"]
        rows[3]["values_exact"] = ["20", "17"]
    elif mutation == "root_blank":
        rows[3]["values_exact"][0] = None
    elif mutation == "root_mismatch":
        rows[3]["values_exact"][0] = "21"
    elif mutation in {"marked_root_without_annotation", "unknown_root_marker", "superscript_root_marker", "other_semantic_root"}:
        label = {"marked_root_without_annotation": ROOT + " (*)", "unknown_root_marker": ROOT + " (**)",
                 "superscript_root_marker": ROOT + "¹", "other_semantic_root": "Thu nhập chịu thuế"}[mutation]
        rows[3]["label_exact"] = label
        rows[3]["hierarchy_path_exact"] = [label]
    else:
        old = rows[0]["label_exact"]
        new = old.rstrip(":") + (" của Ngân hàng mẹ:" if mutation == "qualified_group" else " hợp nhất:")
        rows[0]["label_exact"] = new
        for row in rows[:3]:
            row["hierarchy_path_exact"] = [new if value == old else value for value in row["hierarchy_path_exact"]]
    receipt = _check(section, table)
    assert receipt["status"] == "ALGORITHM_HOLD", (mutation, receipt)
    assert receipt["reasons"]


def test_recognition_frontier_marked_root_requires_its_exact_owned_single_table_annotation():
    section, table = _recognition_fixture(annotated=True)
    receipt = _check(section, table)
    assert receipt["status"] == "PASS", receipt["reasons"]
    assert receipt["parent_source_row"]["label_exact"] == ROOT + " (*)"
    assert receipt["root_annotation_receipt"] is not None


@pytest.mark.parametrize("mutation", [
    "missing", "duplicate", "different_marker", "marker_missing", "changed_text",
    "additional_prose", "multiple_tables", "title_not_narrative", "table_title_not_narrative",
])
def test_recognition_frontier_marked_root_cannot_borrow_or_loosen_annotation_authority(mutation):
    section, table = _recognition_fixture(annotated=True)
    if mutation == "missing":
        section["narratives_exact"] = []
    elif mutation == "duplicate":
        section["narratives_exact"].append(ANNOTATION)
    elif mutation == "different_marker":
        section["narratives_exact"] = [ANNOTATION.replace("(*)", "(**)")]
    elif mutation == "marker_missing":
        section["narratives_exact"] = [ANNOTATION.removeprefix("(*) ")]
    elif mutation == "changed_text":
        section["narratives_exact"] = [ANNOTATION.replace("thu nhập chịu thuế", "lợi nhuận kế toán")]
    elif mutation == "additional_prose":
        section["narratives_exact"] = [ANNOTATION + " Áp dụng riêng cho công ty con."]
    elif mutation == "multiple_tables":
        section["tables"].append(_table([_row("Khoản khác", "1", "2")]))
    elif mutation == "title_not_narrative":
        section["narratives_exact"] = []
        section["title_exact"] += "\n" + ANNOTATION
    else:
        section["narratives_exact"] = []
        table["title_exact"] = ANNOTATION
    receipt = _check(section, table)
    assert receipt["status"] == "ALGORITHM_HOLD", (mutation, receipt)
    assert receipt["reasons"]


def test_recognition_frontier_child_paths_cannot_invent_a_missing_actual_group():
    section, table = _recognition_fixture()
    table["rows"].pop(0)
    assert _check(section, table)["status"] == "ALGORITHM_HOLD"


def test_recognition_frontier_cannot_ignore_an_unknown_group_descendant_after_the_root():
    section, table = _recognition_fixture()
    label = "Điều chỉnh khác chưa có bản chất xác định"
    table["rows"].append({**_row(label, "0", "0"),
                          "hierarchy_path_exact": [table["rows"][0]["label_exact"], label]})
    assert _check(section, table)["status"] == "ALGORITHM_HOLD"


@pytest.mark.parametrize("marker", ["\u20dd", "\u0338"])
@pytest.mark.parametrize("target", ["group", "current", "deferred", "root", "annotation"])
def test_recognition_frontier_cannot_fold_away_non_vietnamese_combining_annotations(marker, target):
    section, table = _recognition_fixture(annotated=True)
    if target == "annotation":
        section["narratives_exact"][0] += marker
    else:
        row = table["rows"][{"group": 0, "current": 1, "deferred": 2, "root": 3}[target]]
        old = row["label_exact"]
        row["label_exact"] += marker
        for source_row in table["rows"]:
            source_row["hierarchy_path_exact"] = [
                row["label_exact"] if value == old else value
                for value in source_row["hierarchy_path_exact"]
            ]
    assert _check(section, table)["status"] == "ALGORITHM_HOLD"


def _recognition_signed_records(*, scope="riêng"):
    """Pure recognition population: no RATE-prefix authority is invented."""
    records = _signed_records()
    section, _ = _recognition_fixture(scope=scope, interim=False)
    records[0]["page_json"]["sections"] = [section]
    primary_section = records[1]["page_json"]["sections"][0]
    primary_section["title_exact"] = "Báo cáo kết quả hoạt động " + scope
    primary_rows = primary_section["tables"][0]["rows"]
    primary_rows[2]["values_exact"][-2:] = ["-", "-"]
    primary_rows[3]["values_exact"][-2:] = ["(20)", "(16)"]
    primary_rows[4]["values_exact"][-2:] = ["80", "64"]
    _printed_annual_primary(records)
    return records


def _public_query(records, compiled):
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled,
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled,
    )
    if cluster["status"] != READY:
        return cluster, None
    return cluster, build_gemini_json_income_tax_region_query_receipt_v1(
        cluster["component_regions"], cluster=cluster,
    )


def _public_evaluate(records, compiled, cluster, query):
    return evaluate_gemini_json_income_tax_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={item["page_json_version_id"]: item["page_json"] for item in records},
        selected_page_axis=[{key: value for key, value in item.items() if key != "page_json"} for item in records],
        compiled_specs=compiled, query_receipt=query,
    )


@pytest.mark.parametrize("scope", ["riêng", "hợp nhất"])
def test_recognition_public_merge_preserves_group_scope_after_structural_ancestry_removal(scope):
    records = _recognition_signed_records(scope=scope)
    original = deepcopy(records)
    compiled = _adapter_compiled()
    cluster, query = _public_query(records, compiled)
    assert cluster["status"] == READY, cluster["reasons"]
    assert query is not None
    inventory = query["source_context_receipt"]["tax_population_inventory"]
    frontiers = [item["recognition_expense_frontier"] for item in inventory
                 if item["recognition_expense_frontier"]["status"] == "PASS"]
    assert len(frontiers) == 1
    group = records[0]["page_json"]["sections"][0]["tables"][0]["rows"][0]["label_exact"]
    assert any(group in path for path in frontiers[0]["printed_scope_source_paths_exact"])
    candidate = _public_evaluate(records, compiled, cluster, query)
    assert candidate["status"] == READY, candidate["reasons"]
    mappings = {item["role"]: item for item in candidate["mappings"]}
    assert [cell["coefficient"] for cell in mappings["CURRENT_TAX_PARENT"]["values"]] == [20, 16]
    assert [cell["coefficient"] for cell in mappings["DEFERRED_TAX_NET"]["values"]] == [0, 0]
    assert all(cell["source_text"] == "-" for cell in mappings["DEFERRED_TAX_NET"]["values"])
    assert records == original


@pytest.mark.parametrize("scope", ["riêng", "hợp nhất"])
def test_recognition_public_scope_veto_cannot_disappear_with_the_structural_group(scope):
    records = _recognition_signed_records(scope=scope)
    rows = records[0]["page_json"]["sections"][0]["tables"][0]["rows"]
    old = rows[0]["label_exact"]
    other = "hợp nhất" if scope == "riêng" else "riêng"
    new = old.replace(scope, other)
    rows[0]["label_exact"] = new
    for row in rows[:3]:
        row["hierarchy_path_exact"] = [new if value == old else value for value in row["hierarchy_path_exact"]]
    original = deepcopy(records)
    compiled = _adapter_compiled()
    cluster, query = _public_query(records, compiled)
    if query is None:
        assert cluster["status"] == UNRESOLVED
    else:
        candidate = _public_evaluate(records, compiled, cluster, query)
        assert candidate["status"] == UNRESOLVED
        assert candidate["mappings"] == []
    assert records == original


@pytest.mark.parametrize("mutation", [
    "item_group", "nonblank_group", "missing_group_retained_paths",
    "unknown_post_root_descendant", "unowned_root_marker", "nonzero_deferred_closing",
])
def test_recognition_malformed_source_cannot_be_hidden_by_generic_consumed_row_success(mutation):
    records = _recognition_signed_records()
    rows = records[0]["page_json"]["sections"][0]["tables"][0]["rows"]
    if mutation == "item_group":
        rows[0]["row_kind"] = "ITEM"
    elif mutation == "nonblank_group":
        rows[0]["values_exact"] = ["0", "0"]
    elif mutation == "missing_group_retained_paths":
        rows.pop(0)
    elif mutation == "unknown_post_root_descendant":
        rows.append({**_row("Khoản chưa xác định", "0", "0"),
                     "hierarchy_path_exact": [rows[0]["label_exact"], "Khoản chưa xác định"]})
    elif mutation == "unowned_root_marker":
        rows[3]["label_exact"] += " (*)"
        rows[3]["hierarchy_path_exact"] = [rows[3]["label_exact"]]
    else:
        rows[2]["values_exact"] = ["1", "2"]
        rows[3]["values_exact"] = ["21", "18"]
    original = deepcopy(records)
    compiled = _adapter_compiled()
    cluster, query = _public_query(records, compiled)
    if query is None:
        assert cluster["status"] == UNRESOLVED
    else:
        candidate = _public_evaluate(records, compiled, cluster, query)
        assert candidate["status"] == UNRESOLVED
        assert candidate["mappings"] == []
    assert records == original


def _reseal_public_receipt_ids(value):
    if isinstance(value, list):
        for child in value:
            _reseal_public_receipt_ids(child)
    elif isinstance(value, dict):
        for child in value.values():
            _reseal_public_receipt_ids(child)
        for key in ("receipt_id", "query_receipt_id"):
            identity = value.get(key)
            if isinstance(identity, str) and re.fullmatch(r".+:[0-9a-f]{64}", identity):
                value[key] = identity.rsplit(":", 1)[0] + ":" + canonical_json_sha256_v1(
                    {field: item for field, item in value.items() if field != key}
                )


@pytest.mark.parametrize("mutation", ["blank_group", "scope_path", "root_marker", "inventory_raw_group"])
def test_recognition_public_query_rebuild_rejects_self_resealed_frontier_or_context_tamper(mutation):
    records = _recognition_signed_records()
    original = deepcopy(records)
    compiled = _adapter_compiled()
    cluster, query = _public_query(records, compiled)
    assert cluster["status"] == READY, cluster["reasons"]
    assert query is not None
    forged = deepcopy(query)
    inventory = forged["source_context_receipt"]["tax_population_inventory"][0]
    frontier = inventory["recognition_expense_frontier"]
    assert frontier["status"] == "PASS"
    if mutation == "blank_group":
        frontier["group_source_row"]["source_values_exact"] = ["0", "0"]
    elif mutation == "scope_path":
        frontier["printed_scope_source_paths_exact"] = [["Ghi nhận trong báo cáo kết quả hoạt động hợp nhất"]]
    elif mutation == "root_marker":
        frontier["parent_source_row"]["label_exact"] += " (*)"
    else:
        inventory["source_table_row_axis"][0]["row_kind"] = "ITEM"
        inventory["source_table_rows_exact"][0]["row_kind"] = "ITEM"
    _reseal_public_receipt_ids(forged)
    with pytest.raises(GeminiJsonIncomeTaxFamilyV1Error):
        _public_evaluate(records, compiled, cluster, forged)
    assert records == original
