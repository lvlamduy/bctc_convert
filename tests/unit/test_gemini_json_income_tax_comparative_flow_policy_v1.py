from __future__ import annotations

import json
import re
import unicodedata
from copy import deepcopy
from hashlib import sha256

import pytest
from test_gemini_json_income_tax_family_v1 import _adapter_compiled, _page, _record
from test_gemini_json_income_tax_root_controls_v1 import _evaluate_query
from test_gemini_json_income_tax_signed_display_v1 import (
    _contextual_period_locator,
    _document_annual_relative_note_records,
)

from bctc_ai.evaluation import gemini_json_income_tax_family_v1 as family
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
)
from bctc_ai.evaluation.gemini_json_other_long_term_investments_family_v1 import (
    GeminiJsonOtherLongTermInvestmentsFamilyV1Error,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _printed_flow_policy(*, scope="riêng", year=2024, scaffold="a"):
    population = " " + scope if scope else ""
    ending = f"cho kỳ hoạt động 6 tháng kết thúc ngày 30 tháng 6 năm {year}"
    if scaffold == "a":
        return (
            f"Số liệu so sánh trên báo cáo kết quả hoạt động{population} giữa niên độ, "
            f"báo cáo lưu chuyển tiền tệ{population} giữa niên độ và các thuyết minh tương ứng "
            f"là số liệu trên báo cáo tài chính{population} giữa niên độ đã được soát xét {ending}."
        )
    if scaffold == "b":
        return (
            "Số liệu so sánh của của báo cáo kết quả hoạt động giữa niên độ, "
            "báo cáo lưu chuyển tiền tệ giữa niên độ và các thuyết minh tương ứng "
            f"là số liệu của báo cáo tài chính đã được soát xét giữa niên độ {ending}."
        )
    return (
        f"Số liệu so sánh của Báo cáo kết quả hoạt động{population} giữa niên độ, "
        f"báo cáo lưu chuyển tiền tệ{population} giữa niên độ và các thuyết minh tương ứng "
        f"là số liệu của báo cáo tài chính{population} giữa niên độ {ending} đã được soát xét."
    )


def _printed_stock_policy():
    return (
        "Số liệu so sánh của báo cáo tình hình tài chính hợp nhất giữa niên độ và các thuyết minh "
        "tương ứng là số liệu của báo cáo tài chính hợp nhất cho năm tài chính kết thúc ngày "
        "31 tháng 12 năm 2024 đã được kiểm toán."
    )


def _comparative_flow_records(*, scope="riêng", current_year=2026, prior_year=2024, scaffold="a"):
    records = _document_annual_relative_note_records()
    for index, record in enumerate(records):
        section = record["page_json"]["sections"][0]
        if index == 0:
            section["title_exact"] = "Chi phí thuế thu nhập doanh nghiệp " + scope
        else:
            caption = "Báo cáo kết quả hoạt động" if index == 1 else "Báo cáo lưu chuyển tiền tệ"
            section["title_exact"] = (
                f"{caption} {scope}\nCho kỳ hoạt động 6 tháng kết thúc ngày 30 tháng 6 năm {current_year}"
            )
        for column, label in zip(section["tables"][0]["columns"], ("Kỳ này", "Kỳ trước"), strict=True):
            column["header_path_exact"] = [label]
    policy = _record(_page([], owner="Cơ sở lập báo cáo tài chính", tables=[]))
    policy.update(page_json_version_id="gfpstorev1:json:" + "f" * 64,
                  physical_page=4, selected_page_ordinal=4)
    policy["page_json"]["sections"][0]["narratives_exact"] = [
        _printed_flow_policy(scope=scope, year=prior_year, scaffold=scaffold),
    ]
    records.append(policy)
    return records


def _policy_section(records):
    policy = [record for record in records if record["page_json_version_id"] == "gfpstorev1:json:" + "f" * 64]
    assert len(policy) == 1
    return policy[0]["page_json"]["sections"][0]


def _period_proof(records, *, inventory=None):
    compiled = _adapter_compiled()
    if inventory is None:
        inventory = family._document_statement_period_inventory(records, compiled_specs=compiled)
    return family._source_period_correspondence_receipt(
        left_locator=_contextual_period_locator(records[0]),
        right_locator=_contextual_period_locator(records[1]),
        left_money_column_ordinals=[1, 2], right_money_column_ordinals=[1, 2],
        page_records=records, compiled_specs=compiled, document_period_inventory=inventory,
    )


def _public_query(records):
    compiled = _adapter_compiled()
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(page_records=records, compiled_specs=compiled)
    cluster = family.recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled,
    )
    query = None
    if cluster["status"] == READY:
        query = family.build_gemini_json_income_tax_region_query_receipt_v1(cluster["component_regions"], cluster=cluster)
    return compiled, cluster, query


def _public_candidate(records):
    compiled, cluster, query = _public_query(records)
    return cluster if query is None else _evaluate_query(records, compiled, cluster, query)


@pytest.mark.parametrize("scope,scaffold,stock", [
    ("riêng", "a", False), ("hợp nhất", "a", False), ("", "b", False),
    ("", "c", False), ("hợp nhất", "c", True),
])
def test_printed_comparative_flow_parser_authenticates_finite_source_scaffolds(scope, scaffold, stock):
    raw = _printed_flow_policy(scope=scope, scaffold=scaffold)
    if stock:
        raw = _printed_stock_policy() + " " + raw
    original = deepcopy(raw)
    receipt = family._parse_printed_comparative_flow_policy(raw)
    assert receipt["complete"] is True, receipt["reasons"]
    assert receipt["status"] == "PASS"
    assert receipt["comparative_period"]["printed_months"] == 6
    assert receipt["comparative_period"]["printed_end_date"] == "2024-06-30"
    assert set(receipt["applies_to"]) == {"INCOME_STATEMENT", "CASH_FLOW", "CORRESPONDING_NOTES"}
    assert receipt["source_exact"] == raw == original


@pytest.mark.parametrize("presentation", ["unicode_nfd", "newline", "nonadjacent_year"])
def test_printed_comparative_flow_retains_real_unicode_layout_and_printed_prior_year(presentation):
    raw = _printed_flow_policy()
    if presentation == "unicode_nfd":
        raw = unicodedata.normalize("NFD", raw)
    elif presentation == "newline":
        raw = raw.replace(", báo cáo", ",\nbáo cáo")
    else:
        raw = raw.replace("2024", "2022")
    receipt = family._parse_printed_comparative_flow_policy(raw)
    assert receipt["complete"] is True, receipt["reasons"]
    assert receipt["source_exact"] == raw
    assert receipt["comparative_period"]["printed_end_date"] == ("2022-06-30" if presentation == "nonadjacent_year" else "2024-06-30")


@pytest.mark.parametrize("mutation", [
    "negated", "extra_assertion", "two_flow_assertions", "wrong_months", "invalid_date", "stock_only",
    "income_only", "cash_flow_only", "unknown_furniture", "footnote", "combining_circle", "combining_overlay",
    "missing_period", "not_reviewed", "unknown_method", "unmatched_parenthesis", "double_period",
])
def test_printed_comparative_flow_parser_cannot_discard_unreviewed_or_conflicting_source(mutation):
    raw = _printed_flow_policy()
    if mutation == "negated":
        raw = raw.replace("là số liệu", "không phải là số liệu")
    elif mutation == "extra_assertion":
        raw += " Số liệu này áp dụng cho quý II năm 2023."
    elif mutation == "two_flow_assertions":
        raw += " " + _printed_flow_policy(year=2023)
    elif mutation == "wrong_months":
        raw = raw.replace("6 tháng", "13 tháng")
    elif mutation == "invalid_date":
        raw = raw.replace("30 tháng 6", "31 tháng 6")
    elif mutation == "stock_only":
        raw = _printed_stock_policy()
    elif mutation == "income_only":
        raw = raw.replace(", báo cáo lưu chuyển tiền tệ riêng giữa niên độ", "")
    elif mutation == "cash_flow_only":
        raw = raw.replace("báo cáo kết quả hoạt động riêng giữa niên độ, ", "")
    elif mutation == "unknown_furniture":
        raw += " B04a/TCTD-HN"
    elif mutation == "footnote":
        raw = raw.replace("so sánh", "so sánh¹")
    elif mutation == "combining_circle":
        raw = raw.replace("so sánh", "so sánh\u20dd")
    elif mutation == "combining_overlay":
        raw = raw.replace("so sánh", "so sánh\u0338")
    elif mutation == "missing_period":
        raw = raw.replace("cho kỳ hoạt động 6 tháng kết thúc ngày 30 tháng 6 năm 2024", "")
    elif mutation == "not_reviewed":
        raw = raw.replace("đã được soát xét", "chưa được soát xét")
    elif mutation == "unknown_method":
        raw = raw.replace("đã được soát xét", "đã được xác nhận")
    elif mutation == "unmatched_parenthesis":
        raw += "("
    else:
        raw += "."
    original = deepcopy(raw)
    receipt = family._parse_printed_comparative_flow_policy(raw)
    assert receipt["complete"] is False
    assert receipt["status"] in {"NOT_APPLICABLE", "ALGORITHM_HOLD"}
    assert raw == original


@pytest.mark.parametrize("scope", ["riêng", "hợp nhất"])
@pytest.mark.parametrize("current_year,prior_year", [(2026, 2024), (2025, 2024), (2026, 2022)])
def test_comparative_flow_policy_binds_literal_ky_lanes_without_previous_year_guess(scope, current_year, prior_year):
    records = _comparative_flow_records(scope=scope, current_year=current_year, prior_year=prior_year)
    original = deepcopy(records)
    proof = _period_proof(records)
    assert proof["complete"] is True, proof["reasons"]
    assert proof["status"] == "PASS_AUTHENTICATED_PRINTED_COMPARATIVE_FLOW_POLICY"
    assert proof["amounts_used_as_authority"] is False
    assert proof["start_dates_inferred"] is False
    assert proof["source_period_keys_modified"] is False
    for selector in proof["source_selectors"]:
        assert selector["raw_lane_axis"]["source_lane_keys"] == [
            ["SEMANTIC_ALIAS", "CURRENT_PERIOD"], ["SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"],
        ]
    candidate = _public_candidate(records)
    assert candidate["status"] == READY, candidate["reasons"]
    roles = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [value["source_text"] for value in roles["CURRENT_TAX_PARENT"]["values"]] == ["20", "16"]
    assert [value["source_text"] for value in roles["FAMILY_ROOT_TOTAL"]["values"]] == ["(22)", "(17)"]
    assert records == original


def _append_flow_continuation(records, index):
    continuation = deepcopy(records[index])
    continuation.update(page_json_version_id="gfpstorev1:json:" + "a" * 64,
                        physical_page=5, selected_page_ordinal=5)
    records.append(continuation)
    return continuation["page_json"]["sections"][0]


@pytest.mark.parametrize("mutation", [
    "missing_income", "missing_cf", "fake_income_caption", "fake_cf_caption", "unknown_all_scope",
    "wrong_cf_scope", "wrong_note_scope", "policy_wrong_scope", "policy_scope_unknown_all",
    "income_current_absent", "cf_current_absent", "cf_current_conflict", "policy_current_or_future",
    "cf_date_only_stock", "income_date_only_stock", "cf_quarter_only", "cf_three_months",
    "cf_conflicting_continuation", "cf_undated_continuation", "income_conflicting_continuation",
    "income_undated_continuation", "note_owned_period_conflict", "note_unmapped_period_ancestor",
    "note_entity_header", "note_entity_ancestor", "income_entity", "cf_entity", "policy_wrong_page_status",
    "policy_not_note", "policy_history", "missing_policy", "filename_only", "unknown_relative_label",
    "reversed_relative_columns", "duplicate_relative_columns", "cross_document_policy",
])
def test_comparative_flow_route_cannot_replace_absent_or_conflicting_source_authority(mutation):
    records = _comparative_flow_records()
    note, income, cash = [record["page_json"]["sections"][0] for record in records[:3]]
    policy = _policy_section(records)
    if mutation == "missing_income":
        records.pop(1)
    elif mutation == "missing_cf":
        records.pop(2)
    elif mutation == "fake_income_caption":
        income["title_exact"] = income["title_exact"].replace("Báo cáo kết quả hoạt động", "Bảng phân tích kết quả")
    elif mutation == "fake_cf_caption":
        cash["title_exact"] = cash["title_exact"].replace("Báo cáo lưu chuyển tiền tệ", "Bảng phân tích lưu chuyển")
    elif mutation in {"unknown_all_scope", "policy_scope_unknown_all"}:
        for section in (note, income, cash):
            section["title_exact"] = section["title_exact"].replace(" riêng", "")
        policy["narratives_exact"] = [_printed_flow_policy(scope="", scaffold="c")]
    elif mutation == "wrong_cf_scope":
        cash["title_exact"] = cash["title_exact"].replace("riêng", "hợp nhất")
    elif mutation == "wrong_note_scope":
        note["title_exact"] = note["title_exact"].replace("riêng", "hợp nhất")
    elif mutation == "policy_wrong_scope":
        policy["narratives_exact"] = [_printed_flow_policy(scope="hợp nhất")]
    elif mutation in {"income_current_absent", "cf_current_absent"}:
        target = income if mutation.startswith("income") else cash
        target["title_exact"] = target["title_exact"].split("\n")[0]
    elif mutation == "cf_current_conflict":
        cash["title_exact"] = cash["title_exact"].replace("2026", "2025")
    elif mutation == "policy_current_or_future":
        policy["narratives_exact"] = [_printed_flow_policy(year=2026)]
    elif mutation in {"cf_date_only_stock", "income_date_only_stock"}:
        target = cash if mutation.startswith("cf") else income
        target["title_exact"] = target["title_exact"].split("\n")[0] + "\nTại ngày 30 tháng 6 năm 2026"
    elif mutation == "cf_quarter_only":
        cash["title_exact"] = cash["title_exact"].split("\n")[0] + "\nCho quý II năm 2026"
    elif mutation == "cf_three_months":
        cash["title_exact"] = cash["title_exact"].replace("6 tháng", "3 tháng")
    elif mutation.endswith("continuation"):
        target = _append_flow_continuation(records, 1 if mutation.startswith("income") else 2)
        target["title_exact"] = (target["title_exact"].split("\n")[0]
                                 if "undated" in mutation else target["title_exact"].replace("2026", "2023"))
    elif mutation == "note_owned_period_conflict":
        note["title_exact"] += "\nCho kỳ hoạt động 3 tháng kết thúc ngày 30 tháng 6 năm 2026"
    elif mutation == "note_unmapped_period_ancestor":
        row = deepcopy(note["tables"][0]["rows"][0])
        row.update(label_exact="Hàng bổ sung chưa ánh xạ", hierarchy_path_exact=["Quý II năm 2026", "Hàng bổ sung chưa ánh xạ"])
        note["tables"][0]["rows"].append(row)
    elif mutation == "note_entity_header":
        note["tables"][0]["columns"][0]["header_path_exact"].append("Ngân hàng mẹ")
    elif mutation == "note_entity_ancestor":
        for row in note["tables"][0]["rows"]:
            row["hierarchy_path_exact"] = ["Ngân hàng mẹ", row["label_exact"]]
    elif mutation in {"income_entity", "cf_entity"}:
        (income if mutation.startswith("income") else cash)["title_exact"] += "\nNgân hàng mẹ"
    elif mutation == "policy_wrong_page_status":
        records[-1]["page_json"]["status"] = "PRIMARY_FINANCIAL_STATEMENT"
    elif mutation == "policy_not_note":
        policy["content_kind"] = "FINANCIAL_NARRATIVE"
    elif mutation == "policy_history":
        policy["narratives_exact"][0] = "Thông tin lịch sử: " + policy["narratives_exact"][0]
    elif mutation in {"missing_policy", "filename_only"}:
        policy["narratives_exact"] = []
        if mutation == "filename_only":
            for record in records:
                record["source_logical_name"] = "2026_6_thang_so_sanh_2024.pdf"
    elif mutation == "unknown_relative_label":
        note["tables"][0]["columns"][1]["header_path_exact"] = ["Kỳ tham chiếu"]
    elif mutation == "reversed_relative_columns":
        note["tables"][0]["columns"].reverse()
    elif mutation == "duplicate_relative_columns":
        note["tables"][0]["columns"][1] = deepcopy(note["tables"][0]["columns"][0])
    else:
        records[-1]["document_id"] = "gfpstorev1:document:" + "b" * 64
    original = deepcopy(records)
    proof = _period_proof(records)
    assert proof["complete"] is False, proof
    if mutation == "cross_document_policy":
        with pytest.raises(
            GeminiJsonOtherLongTermInvestmentsFamilyV1Error,
            match="^other-long-term-investment selected pages cross document identity$",
        ):
            _public_candidate(records)
    else:
        result = _public_candidate(records)
        assert result["status"] == UNRESOLVED, result.get("reasons")
        if "mappings" in result:
            assert result["mappings"] == []
    assert records == original


def _reseal_receipts(value):
    if type(value) is list:
        for child in value:
            _reseal_receipts(child)
    elif type(value) is dict:
        for child in value.values():
            _reseal_receipts(child)
        for key in ("receipt_id", "query_receipt_id"):
            identity = value.get(key)
            if type(identity) is str and re.fullmatch(r".+:[0-9a-f]{64}", identity):
                value[key] = identity.rsplit(":", 1)[0] + ":" + canonical_json_sha256_v1(
                    {name: child for name, child in value.items() if name != key}
                )


@pytest.mark.parametrize("mutation", ["policy_complete", "printed_source", "resolved_period", "inventory_source"])
def test_public_comparative_flow_policy_self_resealing_cannot_replace_fresh_source_authentication(mutation):
    records = _comparative_flow_records()
    original = deepcopy(records)
    compiled, cluster, query = _public_query(records)
    assert cluster["status"] == READY and query is not None
    assert _evaluate_query(records, compiled, cluster, query)["status"] == READY
    forged = deepcopy(query)
    inventory = forged["source_context_receipt"]["document_statement_period_inventory"]
    receipt = inventory["document_comparative_flow_policy_receipt"]
    if mutation == "policy_complete":
        receipt["complete"] = False
    elif mutation == "printed_source":
        receipt["unregistered_source_assertion"] = _printed_flow_policy(year=2023)
    elif mutation == "resolved_period":
        receipt["resolved_source_duration_semantics"] = [["SOURCE_YTD_QUARTER", 2026, 2], ["SOURCE_YTD_QUARTER", 2023, 2]]
    else:
        inventory["sources"][0]["original_table_json_sha256"] = "0" * 64
    _reseal_receipts(forged)
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error):
        _evaluate_query(records, compiled, cluster, forged)
    assert records == original


def test_comparative_flow_inventory_self_reseal_cannot_authorize_changed_actual_policy():
    records = _comparative_flow_records()
    inventory = family._document_statement_period_inventory(records, compiled_specs=_adapter_compiled())
    changed = deepcopy(records)
    _policy_section(changed)["narratives_exact"] = [_printed_flow_policy(year=2023)]
    original = deepcopy(changed)
    _reseal_receipts(inventory)
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="drifted"):
        _period_proof(changed, inventory=inventory)
    assert changed == original


@pytest.mark.parametrize("presentation", ["unit", "restated", "restated_before_unit", "restated_after_unit"])
def test_comparative_flow_literal_ky_paths_preserve_exact_unit_and_restated_source(presentation):
    records = _comparative_flow_records()
    for record in records[:3]:
        for index, column in enumerate(record["page_json"]["sections"][0]["tables"][0]["columns"]):
            if presentation in {"unit", "restated_before_unit", "restated_after_unit"}:
                column["header_path_exact"].append("Triệu đồng")
            if index == 1 and presentation != "unit":
                if presentation == "restated_after_unit":
                    column["header_path_exact"].append("(Trình bày lại)")
                else:
                    column["header_path_exact"][0] += " (Trình bày lại)"
    original = deepcopy(records)
    compiled = _adapter_compiled()
    for record in records[:3]:
        section = record["page_json"]["sections"][0]
        table = section["tables"][0]
        lane = family._multitable_lane_axis(section, table, compiled_specs=compiled)
        paths = family._relative_flow_column_paths(table, lane)
        assert paths == [column["header_path_exact"] for column in table["columns"]]
    proof = _period_proof(records)
    assert proof["complete"] is True, proof["reasons"]
    if presentation == "restated_after_unit":
        candidate = _public_candidate(records)
        assert candidate["status"] == READY, candidate["reasons"]
    assert records == original


@pytest.mark.parametrize("suffix", ["(*)", "¹", "\u20dd", "\u0338", " (Trình bày lại) (Trình bày lại)", " (chưa soát xét)"])
def test_comparative_flow_literal_ky_helper_rejects_unknown_annotations(suffix):
    records = _comparative_flow_records()
    section = records[0]["page_json"]["sections"][0]
    table = section["tables"][0]
    table["columns"][1]["header_path_exact"][0] += suffix
    lane = family._multitable_lane_axis(section, table, compiled_specs=_adapter_compiled())
    original = deepcopy(records)
    assert family._relative_flow_column_paths(table, lane) is None
    assert _period_proof(records)["complete"] is False
    assert records == original


@pytest.mark.parametrize("presentation", ["compatible_note_caption", "historical_narrative", "policy_with_table"])
def test_comparative_flow_policy_preserves_supported_local_context_without_fictional_ownership_rules(presentation):
    records = _comparative_flow_records()
    note = records[0]["page_json"]["sections"][0]
    if presentation == "compatible_note_caption":
        note["title_exact"] += "\nCho kỳ hoạt động 6 tháng kết thúc ngày 30 tháng 6 năm 2026"
    elif presentation == "historical_narrative":
        note["narratives_exact"].append(
            "Thông tin lịch sử: cho kỳ hoạt động 6 tháng kết thúc ngày 30 tháng 6 năm 2023."
        )
    else:
        _policy_section(records)["tables"].append({
            "columns": [{"header_path_exact": ["Thông tin"], "value_kind": "TEXT"}],
            "continuation": "NONE", "rows": [{
                "label_exact": "Cơ sở trình bày", "hierarchy_path_exact": ["Cơ sở trình bày"],
                "row_kind": "ITEM", "values_exact": ["Đơn vị báo cáo"],
            }], "title_exact": "Thông tin bổ sung", "unit_exact": None,
        })
    original = deepcopy(records)
    proof = _period_proof(records)
    assert proof["complete"] is True, proof["reasons"]
    candidate = _public_candidate(records)
    assert candidate["status"] == READY, candidate["reasons"]
    assert records == original


@pytest.mark.parametrize("mutation", [
    "unknown_duration_ancestor", "annual_year_ancestor", "calendar_date_ancestor", "duplicate_dates_ancestor",
    "unbalanced_caption", "unsupported_report_narrative", "unsupported_naked_duration_narrative",
    "multitable_unsupported_report_narrative", "multitable_unsupported_naked_duration_narrative",
    "blank_selfpath_entity_group", "unselected_cf_ancestor", "second_prior_policy_without_so_sanh",
])
def test_comparative_flow_exhaustive_source_census_vetoes_unselected_or_unsupported_context(mutation):
    records = _comparative_flow_records()
    note = records[0]["page_json"]["sections"][0]
    table = note["tables"][0]
    if mutation.endswith("ancestor") and mutation != "unselected_cf_ancestor":
        surface = {
            "unknown_duration_ancestor": "Cho kỳ 7 tháng kết thúc ngày 31 tháng 7 năm 2026",
            "annual_year_ancestor": "Năm tài chính 2026",
            "calendar_date_ancestor": "31.03.2026",
            "duplicate_dates_ancestor": "Cho kỳ hoạt động 6 tháng kết thúc ngày 30/6/2026 30/6/2026",
        }[mutation]
        row = deepcopy(table["rows"][0])
        row.update(label_exact="Hàng chưa ánh xạ", hierarchy_path_exact=[surface, "Hàng chưa ánh xạ"])
        table["rows"].append(row)
    elif mutation == "unbalanced_caption":
        note["title_exact"] += "\nCho kỳ hoạt động 6 tháng kết thúc ngày 30 tháng 6 năm 2026 ("
    elif "narrative" in mutation:
        raw = ("6 tháng kết thúc ngày 31/12/2026" if "naked" in mutation
               else "Giai đoạn sáu tháng kết thúc ngày 31/12/2026")
        note["narratives_exact"].append(raw)
        if mutation.startswith("multitable"):
            other = deepcopy(table)
            other.update(rows=[], title_exact="Thông tin bổ sung không sở hữu đoạn văn")
            note["tables"].append(other)
    elif mutation == "blank_selfpath_entity_group":
        table["rows"].insert(0, {
            "label_exact": "Ngân hàng mẹ", "hierarchy_path_exact": ["Ngân hàng mẹ"],
            "row_kind": "GROUP", "values_exact": [None, None],
        })
    elif mutation == "unselected_cf_ancestor":
        continuation = _append_flow_continuation(records, 2)
        row = continuation["tables"][0]["rows"][0]
        row["hierarchy_path_exact"] = ["Cho kỳ hoạt động 3 tháng kết thúc ngày 30 tháng 6 năm 2026", row["label_exact"]]
    else:
        _policy_section(records)["narratives_exact"].append(
            "Số liệu kỳ trước của báo cáo kết quả hoạt động riêng giữa niên độ, báo cáo lưu chuyển tiền tệ "
            "riêng giữa niên độ và các thuyết minh tương ứng là số liệu cho kỳ hoạt động 6 tháng kết thúc "
            "ngày 30 tháng 6 năm 2023."
        )
    original = deepcopy(records)
    proof = _period_proof(records)
    assert proof["complete"] is False, proof
    if mutation in {"annual_year_ancestor", "unsupported_report_narrative", "blank_selfpath_entity_group",
                    "unselected_cf_ancestor", "second_prior_policy_without_so_sanh"}:
        result = _public_candidate(records)
        assert result["status"] == UNRESOLVED, result.get("reasons")
        if "mappings" in result:
            assert result["mappings"] == []
    assert records == original


@pytest.mark.parametrize("punctuation", [".", "?", "!", "..", ".?!"])
@pytest.mark.parametrize("position", ["prefix", "suffix"])
def test_printed_comparative_flow_segmentation_consumes_unknown_punctuation(punctuation, position):
    raw = _printed_flow_policy()
    raw = punctuation + " " + raw if position == "prefix" else raw + " " + punctuation
    original = deepcopy(raw)
    receipt = family._parse_printed_comparative_flow_policy(raw)
    assert receipt["complete"] is False
    assert raw == original


def _independent_existing_flow_records(*, route="absolute", scope="riêng", policy_year=2024, include_cf=True):
    """A printed policy cannot disappear because an older proof route succeeds."""
    records = _comparative_flow_records(scope=scope, prior_year=policy_year)
    note = records[0]["page_json"]["sections"][0]
    note["title_exact"] += "\nCho kỳ hoạt động 6 tháng kết thúc ngày 30 tháng 6 năm 2026"
    for record in records[:3]:
        table = record["page_json"]["sections"][0]["tables"][0]
        for column, year, label in zip(table["columns"], (2026, 2025), ("Năm nay", "Năm trước"), strict=True):
            column["header_path_exact"] = (
                ["Kỳ 6 tháng kết thúc ngày", f"30/6/{year}", "Triệu đồng"]
                if route == "absolute" else [label]
            )
    if not include_cf:
        records.pop(2)
    return records


@pytest.mark.parametrize("surface", ["Năm bất thường", "32. Năm bất thường"])
def test_numbered_heading_classification_never_waives_an_unknown_year_assertion(surface):
    records = _comparative_flow_records()
    row = records[0]["page_json"]["sections"][0]["tables"][0]["rows"][0]
    row["hierarchy_path_exact"] = [surface, row["label_exact"]]
    original = deepcopy(records)
    assert _period_proof(records)["complete"] is False
    candidate = _public_candidate(records)
    assert candidate["status"] == UNRESOLVED, candidate.get("reasons")
    assert candidate.get("mappings", []) == []
    assert records == original


@pytest.mark.parametrize("route", ["absolute", "nam"])
@pytest.mark.parametrize("scope", ["riêng", "hợp nhất"])
def test_printed_comparative_policy_conflict_vetoes_existing_literal_or_nam_period_routes(route, scope):
    records = _independent_existing_flow_records(route=route, scope=scope, policy_year=2024)
    original = deepcopy(records)
    proof = _period_proof(records)
    assert proof["complete"] is False, proof
    candidate = _public_candidate(records)
    assert candidate["status"] == UNRESOLVED, candidate.get("reasons")
    if "mappings" in candidate:
        assert candidate["mappings"] == []
    assert records == original


@pytest.mark.parametrize("printed_policy", [False, True])
def test_independent_absolute_source_periods_do_not_require_cash_flow_for_irrelevant_inheritance_gaps(printed_policy):
    records = _independent_existing_flow_records(policy_year=2025, include_cf=False)
    if not printed_policy:
        _policy_section(records)["narratives_exact"] = []
    original = deepcopy(records)
    for record in records[:2]:
        unit = family._unit_axis(record["page_json"]["sections"][0]["tables"][0], compiled_specs=_adapter_compiled())
        assert unit["complete"] is True and unit["canonical_unit"] == "MILLION_VND"
    inventory = family._document_statement_period_inventory(records, compiled_specs=_adapter_compiled())
    assert inventory["document_comparative_flow_policy_receipt"]["complete"] is False
    proof = _period_proof(records, inventory=inventory)
    assert proof["complete"] is True, proof["reasons"]
    assert proof["status"] == "PASS_LITERAL_SOURCE_DURATION"
    candidate = _public_candidate(records)
    assert candidate["status"] == READY, candidate["reasons"]
    assert records == original


@pytest.mark.parametrize("competing", ["prior_wording", "invalid_date", "unknown_annotation"])
def test_valid_printed_policy_does_not_hide_malformed_competing_policy_on_old_absolute_route(competing):
    records = _independent_existing_flow_records(policy_year=2025)
    if competing == "prior_wording":
        raw = (
            "Số liệu kỳ trước của báo cáo kết quả hoạt động riêng giữa niên độ, báo cáo lưu chuyển tiền tệ "
            "riêng giữa niên độ và các thuyết minh tương ứng là số liệu cho kỳ hoạt động 6 tháng kết thúc "
            "ngày 30 tháng 6 năm 2023."
        )
    elif competing == "invalid_date":
        raw = _printed_flow_policy(year=2023).replace("30 tháng 6", "31 tháng 6")
    else:
        raw = _printed_flow_policy(year=2023).replace("so sánh", "so sánh (*)")
    _policy_section(records)["narratives_exact"].append(raw)
    original = deepcopy(records)
    proof = _period_proof(records)
    assert proof["complete"] is False, proof
    candidate = _public_candidate(records)
    assert candidate["status"] == UNRESOLVED, candidate.get("reasons")
    if "mappings" in candidate:
        assert candidate["mappings"] == []
    assert records == original


@pytest.mark.parametrize("contradiction", ["wrong_current_year", "wrong_current_duration"])
def test_literal_absolute_route_cannot_ignore_unselected_cash_flow_printed_current_contradiction(contradiction):
    records = _independent_existing_flow_records(policy_year=2025)
    cash = records[2]["page_json"]["sections"][0]
    cash["title_exact"] = (
        cash["title_exact"].replace("2026", "2023") if contradiction == "wrong_current_year"
        else cash["title_exact"].replace("6 tháng", "3 tháng")
    )
    original = deepcopy(records)
    proof = _period_proof(records)
    assert proof["complete"] is False, proof
    candidate = _public_candidate(records)
    assert candidate["status"] == UNRESOLVED, candidate.get("reasons")
    if "mappings" in candidate:
        assert candidate["mappings"] == []
    assert records == original


@pytest.mark.parametrize("heading", [
    "32. CHI PHÍ THUẾ THU NHẬP DOANH NGHIỆP",
    "31. CHI PHÍ THUẾ THU NHẬP DOANH NGHIỆP",
    "28. CHI PHÍ THUẾ THU NHẬP DOANH NGHIỆP (TNDN)",
    "1. CHI PHÍ THUẾ THU NHẬP DOANH NGHIỆP",
    "7.1. CHI PHÍ THUẾ THU NHẬP DOANH NGHIỆP",
])
def test_numbered_tax_note_heading_is_not_itself_a_reporting_period_assertion(heading):
    records = _comparative_flow_records()
    records[0]["page_json"]["sections"][0]["title_exact"] = heading
    original = deepcopy(records)
    proof = _period_proof(records)
    assert proof["complete"] is True, proof["reasons"]
    assert proof["status"] == "PASS_AUTHENTICATED_PRINTED_COMPARATIVE_FLOW_POLICY"
    candidate = _public_candidate(records)
    assert candidate["status"] == READY, candidate["reasons"]
    assert records == original


@pytest.mark.parametrize("assertion", [
    "Cho kỳ hoạt động 3 tháng kết thúc ngày 30 tháng 6 năm 2026",
    "Cho kỳ hoạt động 6 tháng kết thúc ngày 31 tháng 3 năm 2026",
    "Cho kỳ hoạt động 6 tháng kết thúc ngày 30 tháng 6 năm 2023",
    "Cho quý II năm 2026",
    "Năm tài chính 2026",
    "31.03.2026",
    "32.03.2026",
    "Cho kỳ chưa xác định",
])
def test_numbered_tax_heading_cannot_hide_printed_or_unknown_period_assertion(assertion):
    records = _comparative_flow_records()
    records[0]["page_json"]["sections"][0]["title_exact"] = (
        "7.1. CHI PHÍ THUẾ THU NHẬP DOANH NGHIỆP\n" + assertion
    )
    original = deepcopy(records)
    proof = _period_proof(records)
    assert proof["complete"] is False, proof
    candidate = _public_candidate(records)
    assert candidate["status"] == UNRESOLVED, candidate.get("reasons")
    if "mappings" in candidate:
        assert candidate["mappings"] == []
    assert records == original


@pytest.mark.parametrize("surface", [
    "7.1.",
    "7.1. CHI PHÍ THUẾ THU NHẬP DOANH NGHIỆP (*)",
    "7.1. CHI PHÍ THUẾ THU NHẬP DOANH NGHIỆP 31.03.2026",
    "7.1. CHI PHÍ THUẾ THU NHẬP DOANH NGHIỆP chưa xác định",
    "7/1. CHI PHÍ THUẾ THU NHẬP DOANH NGHIỆP",
    "7-1. CHI PHÍ THUẾ THU NHẬP DOANH NGHIỆP",
])
def test_finite_numbered_tax_caption_exemption_never_consumes_unknown_date_or_annotation(surface):
    records = _comparative_flow_records()
    section = records[0]["page_json"]["sections"][0]
    section["title_exact"] = surface
    original = deepcopy(records)
    surfaces, _, reasons = family._comparative_flow_local_surface_census(
        section, section["tables"][0], {"money_column_ordinals": [1, 2]},
        [("CUMULATIVE_QUARTER", 2026, 2), ("CUMULATIVE_QUARTER", 2024, 2)],
    )
    assert "UNREVIEWED_LOCAL_DATE_SYNTAX" in reasons
    assert surfaces[0]["finite_numbered_tax_caption_not_period_assertion"] is False
    assert records == original


@pytest.mark.parametrize("suffix", ["31 03 2026", "30 06 2026", "Niên độ bất thường 2026", "2026"])
@pytest.mark.parametrize("surface_kind", ["section", "table", "ancestor"])
def test_unconsumed_printed_year_cannot_hide_in_tax_caption_or_unmapped_ancestry(suffix, surface_kind):
    records = _comparative_flow_records()
    section = records[0]["page_json"]["sections"][0]
    table = section["tables"][0]
    raw = "CHI PHÍ THUẾ THU NHẬP DOANH NGHIỆP " + suffix
    if surface_kind == "section":
        section["title_exact"] = raw
    elif surface_kind == "table":
        table["title_exact"] = raw
    else:
        row = deepcopy(table["rows"][0])
        row.update(label_exact="Hàng chưa ánh xạ", hierarchy_path_exact=[raw, "Hàng chưa ánh xạ"])
        table["rows"].append(row)
    original = deepcopy(records)
    _, _, reasons = family._comparative_flow_local_surface_census(
        section, table, {"money_column_ordinals": [1, 2]},
        [("CUMULATIVE_QUARTER", 2026, 2), ("CUMULATIVE_QUARTER", 2024, 2)],
    )
    assert "UNCONSUMED_LOCAL_PRINTED_YEAR" in reasons
    assert _period_proof(records)["complete"] is False
    assert _public_candidate(records)["status"] == UNRESOLVED
    assert records == original


@pytest.mark.parametrize("assertion", [
    "Niên độ kết thúc ngày 31 tháng 12 năm 2026",
    "Tài khóa bất thường", "Năm bất thường", "Bán niên bất thường", "Nửa cuối năm 2026", "Nửa đầu năm 2026",
    "For the period ended 31 December 2026", "For the six months ended 31 December 2026",
    "Period ended 31 December 2026", "Fiscal year 2026", "Financial year ended 31 December 2026",
    "Year ended 31 December 2026", "Year to date 2026", "Quarter ended 30 September 2026", "QIII 2026",
    "CHI PHÍ THUẾ THU NHẬP DOANH NGHIỆP\nFor the period ended 31 December 2026",
    "CHI PHÍ THUẾ THU NHẬP DOANH NGHIỆP\\nFor the period ended 31 December 2026",
    "CHI PHÍ THUẾ THU NHẬP DOANH NGHIỆP\\nNiên độ kết thúc ngày 31 tháng 12 năm 2026",
])
@pytest.mark.parametrize("ambiguous_owner", [False, True])
def test_unsupported_affirmative_reporting_narratives_are_not_historical_neutral_prose(assertion, ambiguous_owner):
    records = _comparative_flow_records()
    section = records[0]["page_json"]["sections"][0]
    section["narratives_exact"].append(assertion)
    if ambiguous_owner:
        other = deepcopy(section["tables"][0])
        other.update(rows=[], title_exact="Thông tin bổ sung")
        section["tables"].append(other)
    original = deepcopy(records)
    assert _period_proof(records)["complete"] is False
    candidate = _public_candidate(records)
    assert candidate["status"] == UNRESOLVED
    assert candidate.get("mappings", []) == []
    assert records == original


@pytest.mark.parametrize("route", ["relative", "absolute"])
@pytest.mark.parametrize("keep_supported_policy", [True, False])
def test_unsupported_english_comparative_policy_cannot_disappear_from_competing_policy_census(route, keep_supported_policy):
    records = (_comparative_flow_records() if route == "relative"
               else _independent_existing_flow_records(policy_year=2025))
    assertion = (
        "Comparative figures in the income statement, statement of cash flows and corresponding notes "
        "are for the six months ended 30 June 2023."
    )
    if not keep_supported_policy:
        _policy_section(records)["narratives_exact"] = []
    _policy_section(records)["narratives_exact"].append(assertion)
    original = deepcopy(records)
    receipt = family._parse_printed_comparative_flow_policy(assertion)
    assert receipt["status"] == "ALGORITHM_HOLD"
    assert receipt["complete"] is False
    assert _period_proof(records)["complete"] is False
    candidate = _public_candidate(records)
    assert candidate["status"] == UNRESOLVED
    assert candidate.get("mappings", []) == []
    assert records == original


@pytest.mark.parametrize("row_kind", ["GROUP", "ITEM"])
@pytest.mark.parametrize("assertion", [
    "Quý III năm 2026", "Cho kỳ hoạt động 3 tháng kết thúc ngày 30 tháng 6 năm 2026", "Niên độ bất thường",
])
def test_blank_selfpath_reporting_heading_cannot_disappear_from_local_period_census(row_kind, assertion):
    records = _comparative_flow_records()
    table = records[0]["page_json"]["sections"][0]["tables"][0]
    table["rows"].insert(0, {
        "label_exact": assertion, "hierarchy_path_exact": [assertion],
        "row_kind": row_kind, "values_exact": [None, None],
    })
    original = deepcopy(records)
    assert _period_proof(records)["complete"] is False
    candidate = _public_candidate(records)
    assert candidate["status"] == UNRESOLVED
    assert candidate.get("mappings", []) == []
    assert records == original


def test_text_note_reference_does_not_make_a_financially_blank_reporting_heading_populated():
    records = _comparative_flow_records()
    table = records[0]["page_json"]["sections"][0]["tables"][0]
    table["columns"].append({"header_path_exact": ["Thuyết minh"], "value_kind": "TEXT"})
    for row in table["rows"]:
        row["values_exact"].append(None)
    table["rows"].insert(0, {
        "label_exact": "Quý III năm 2026", "hierarchy_path_exact": ["Quý III năm 2026"],
        "row_kind": "ITEM", "values_exact": [None, None, "19"],
    })
    original = deepcopy(records)
    assert _period_proof(records)["complete"] is False
    candidate = _public_candidate(records)
    assert candidate["status"] == UNRESOLVED
    assert candidate.get("mappings", []) == []
    assert records == original


def _annual_or_nine_month_policy(kind):
    scope = "riêng" if kind == "annual_separate" else "hợp nhất"
    if kind != "nine_month_consolidated":
        return (
            f"Số liệu so sánh trên báo cáo tình hình tài chính {scope}, báo cáo kết quả hoạt động {scope}, "
            f"báo cáo lưu chuyển tiền tệ {scope} và các thuyết minh liên quan là số liệu của báo cáo tài chính "
            f"{scope} cho năm tài chính kết thúc ngày 31 tháng 12 năm 2024 đã được kiểm toán."
        )
    return (
        "Số liệu so sánh trên báo cáo tình hình tài chính hợp nhất giữa niên độ và các thuyết minh liên quan "
        "là số liệu của báo cáo tài chính hợp nhất cho năm tài chính kết thúc ngày 31 tháng 12 năm 2024 "
        "đã được kiểm toán. Số liệu so sánh trên báo cáo kết quả hoạt động hợp nhất giữa niên độ, báo cáo "
        "lưu chuyển tiền tệ hợp nhất giữa niên độ và các thuyết minh liên quan là số liệu của báo cáo tài chính "
        "hợp nhất giữa niên độ cho kỳ chín tháng kết thúc ngày 30 tháng 9 năm 2024 đã được soát xét."
    )


@pytest.mark.parametrize("kind,expected_sha,months,end", [
    ("annual_separate", "0ec2a38da6130032b6f753e32a397c672975108a92fbe1b4904e9315c404bc6f", 12, "2024-12-31"),
    ("nine_month_consolidated", "10945fc24f0cc25abc6bcc23fd1aca45ba00447437794012f3fa7f53faaf1e6b", 9, "2024-09-30"),
    ("annual_consolidated", "898e22c21aa310aff0a74add1d5314a6e490ec7efa65b4dea67408bd61882883", 12, "2024-12-31"),
])
def test_actual_annual_and_written_nine_month_policy_scaffolds(kind, expected_sha, months, end):
    raw = _annual_or_nine_month_policy(kind)
    assert canonical_json_sha256_v1(raw) == expected_sha
    receipt = family._parse_printed_comparative_flow_policy(raw)
    assert receipt["complete"] is True, receipt["reasons"]
    assert receipt["comparative_period"]["printed_months"] == months
    assert receipt["comparative_period"]["printed_end_date"] == end
    assert receipt["source_exact"] == raw
    if months == 9:
        assert receipt["clause_receipts"][0]["applies_to"] == ["BALANCE_SHEET"]
        assert receipt["clause_receipts"][0]["used_as_flow_period_authority"] is False
        assert receipt["clause_receipts"][1]["scaffold"] == "TREN_RELATED_NOTES_WRITTEN_NINE_MONTHS"
        # Exact parser receipt retained in the authenticated pre-SIX a272 panel.
        assert receipt["receipt_id"] == (
            "gjitfav1:printed-comparative-flow-policy:"
            "18b56a76af1936da6378b41defeedcb4c7026869041b56a819679807c5a95bda"
        )


@pytest.mark.parametrize("kind", ["annual_separate", "nine_month_consolidated", "annual_consolidated"])
def test_annual_and_written_nine_month_policies_own_relative_lanes_without_year_inference(kind):
    scope = "riêng" if kind == "annual_separate" else "hợp nhất"
    records = _comparative_flow_records(scope=scope, current_year=2025)
    for record in records[1:3]:
        section = record["page_json"]["sections"][0]
        section["title_exact"] = (
            section["title_exact"].replace("6 tháng", "9 tháng").replace("30 tháng 6", "30 tháng 9")
            if kind == "nine_month_consolidated" else section["title_exact"].replace(
                "Cho kỳ hoạt động 6 tháng kết thúc ngày 30 tháng 6 năm 2025",
                "Cho năm tài chính kết thúc ngày 31 tháng 12 năm 2025",
            )
        )
    _policy_section(records)["narratives_exact"] = [_annual_or_nine_month_policy(kind)]
    original = deepcopy(records)
    proof = _period_proof(records)
    assert proof["complete"] is True, proof["reasons"]
    candidate = _public_candidate(records)
    assert candidate["status"] == READY, candidate.get("reasons")
    assert records == original


@pytest.mark.parametrize("kind", ["annual_separate", "nine_month_consolidated", "annual_consolidated"])
@pytest.mark.parametrize("mutation", ["suffix", "duplicate", "mixed_scope", "missing_cash_flow"])
def test_annual_and_written_nine_month_policy_scaffolds_are_whole_clause_not_keyword_matches(kind, mutation):
    raw = _annual_or_nine_month_policy(kind)
    if mutation == "suffix":
        raw += " Số liệu áp dụng cho một kỳ khác."
    elif mutation == "duplicate":
        raw += " " + raw
    elif mutation == "mixed_scope":
        scope = "riêng" if kind == "annual_separate" else "hợp nhất"
        raw = raw.replace("báo cáo lưu chuyển tiền tệ " + scope, "báo cáo lưu chuyển tiền tệ ngân hàng mẹ")
    else:
        raw = raw.replace("báo cáo lưu chuyển tiền tệ", "thông tin khác")
    receipt = family._parse_printed_comparative_flow_policy(raw)
    assert receipt["complete"] is False
    assert receipt["status"] == "ALGORITHM_HOLD"


@pytest.mark.parametrize("route", ["relative", "absolute", "nam"])
@pytest.mark.parametrize("policy_kind", ["compatible", "contradictory", "unsupported"])
def test_unowned_affirmative_comparability_policy_is_veto_only_not_permission_to_ignore_or_inherit(route, policy_kind):
    records = (_comparative_flow_records() if route == "relative"
               else _independent_existing_flow_records(route=route, policy_year=2025))
    section = _policy_section(records)
    section["content_kind"] = "FINANCIAL_NARRATIVE"
    section["title_exact"] = "Thông tin khác về số liệu so sánh"
    if policy_kind == "contradictory":
        section["narratives_exact"] = [_printed_flow_policy(year=2023)]
    elif policy_kind == "unsupported":
        section["narratives_exact"][0] += " Số liệu áp dụng cho kỳ khác."
    original = deepcopy(records)
    proof = _period_proof(records)
    assert proof["complete"] is False
    control = proof["printed_comparative_flow_policy_consistency_receipt"]
    assert "SOURCE_PERIOD_AFFIRMATIVE_UNOWNED_FLOW_POLICY_APPLICABILITY_NOT_PROVEN" in control["reasons"]
    assert control["unowned_affirmative_policy_applicability_holds"]
    assert all(item["positive_period_authority_eligible"] is False
               for item in control["unowned_affirmative_policy_applicability_holds"])
    candidate = _public_candidate(records)
    assert candidate["status"] == UNRESOLVED
    assert candidate.get("mappings", []) == []
    assert records == original


def _interim_caption_records(*, scope="riêng", continuation=False):
    records = _comparative_flow_records(scope=scope)
    for record in records[1:3]:
        section = record["page_json"]["sections"][0]
        section["title_exact"] = section["title_exact"].replace(scope + "\n", scope + " GIỮA NIÊN ĐỘ\n")
    if continuation:
        section = _append_flow_continuation(records, 2)
        section["title_exact"] = section["title_exact"].replace("GIỮA NIÊN ĐỘ", "GIỮA NIÊN ĐỘ (Tiếp theo)")
    return records


@pytest.mark.parametrize("scope,continuation", [("riêng", False), ("hợp nhất", False), ("riêng", True)])
def test_whole_owned_interim_flow_caption_furniture_is_not_an_unknown_fiscal_period(scope, continuation):
    records = _interim_caption_records(scope=scope, continuation=continuation)
    original = deepcopy(records)
    proof = _period_proof(records)
    assert proof["complete"] is True, proof["reasons"]
    candidate = _public_candidate(records)
    assert candidate["status"] == READY, candidate.get("reasons")
    assert records == original


@pytest.mark.parametrize("mutation", ["suffix", "wrong_month", "wrong_scope", "untyped", "note_heading", "row_heading"])
def test_interim_caption_furniture_cannot_hide_unowned_or_contrary_period_assertions(mutation):
    records = _interim_caption_records()
    section = records[2]["page_json"]["sections"][0]
    if mutation == "suffix":
        section["title_exact"] += " kỳ chưa xác định"
    elif mutation == "wrong_month":
        section["title_exact"] = section["title_exact"].replace("6 tháng", "3 tháng")
    elif mutation == "wrong_scope":
        section["title_exact"] = section["title_exact"].replace("riêng", "hợp nhất")
    elif mutation == "untyped":
        section["content_kind"] = "FINANCIAL_NOTE"
        section["statement_type"] = "NOT_APPLICABLE"
    elif mutation == "note_heading":
        records[0]["page_json"]["sections"][0]["title_exact"] += " GIỮA NIÊN ĐỘ"
    else:
        table = records[0]["page_json"]["sections"][0]["tables"][0]
        table["rows"].insert(0, {
            "label_exact": "GIỮA NIÊN ĐỘ", "hierarchy_path_exact": ["GIỮA NIÊN ĐỘ"],
            "row_kind": "GROUP", "values_exact": [None, None],
        })
    original = deepcopy(records)
    assert _period_proof(records)["complete"] is False
    candidate = _public_candidate(records)
    assert candidate["status"] == UNRESOLVED
    assert candidate.get("mappings", []) == []
    assert records == original


def _audited_written_six_policy(*, scope="riêng", prior_year=2024):
    # Original paragraph authenticated by the 857184... source-audit receipt.
    # Only the exact base is an actual-source fixture; transformed populations
    # and years below are explicit synthetic challengers, not source repairs.
    raw = (_annual_or_nine_month_policy("nine_month_consolidated")
           .replace("hợp nhất", "riêng")
           .replace("kỳ chín tháng", "kỳ sáu tháng")
           .replace("30 tháng 9", "30 tháng 6"))
    assert canonical_json_sha256_v1(raw) == "7c9cfd9bfd3796f5582502a055bbd5df7dd36c1e06a2a491312e558fd671ffdd"
    return raw.replace("riêng", scope).replace("2024", str(prior_year))


def _genuine_narrative_policy_records(*, scope="riêng", prior_year=2024):
    records = _comparative_flow_records(scope=scope, current_year=2025, prior_year=prior_year)
    policy = _policy_section(records)
    policy["content_kind"] = "FINANCIAL_NARRATIVE"
    policy["title_exact"] = (
        "Trình bày về khả năng so sánh thông tin trên báo cáo tài chính " + scope + " giữa niên độ"
    )
    policy["tables"] = []
    policy["narratives_exact"] = [_audited_written_six_policy(scope=scope, prior_year=prior_year)]
    return records


def _unrelated_policy_sibling():
    return {
        "content_kind": "FINANCIAL_NOTE", "statement_type": "NOT_APPLICABLE",
        "title_exact": "Đặc điểm hoạt động của Ngân hàng",
        "narratives_exact": [
            "Tại ngày 30 tháng 6 năm 2025, Ngân hàng có 1 công ty con.",
            "Giấy phép được cấp ngày 25 tháng 3 năm 1994.",
        ],
        "tables": [{
            "columns": [{"header_path_exact": ["Thông tin"], "value_kind": "TEXT"}],
            "continuation": "NONE", "rows": [{
                "label_exact": "Công ty A", "hierarchy_path_exact": ["Công ty A"],
                "row_kind": "ITEM", "values_exact": ["Đơn vị đầu tư"],
            }], "title_exact": "Danh sách đơn vị", "unit_exact": None,
        }],
    }


@pytest.mark.parametrize("presentation", ["exact", "unicode_nfd", "newline"])
def test_audited_written_six_policy_preserves_exact_stock_and_flow_clauses(presentation):
    raw = _audited_written_six_policy()
    if presentation == "unicode_nfd":
        raw = unicodedata.normalize("NFD", raw)
    elif presentation == "newline":
        raw = raw.replace(". Số liệu", ".\nSố liệu")
    original = deepcopy(raw)
    receipt = family._parse_printed_comparative_flow_policy(raw)
    assert receipt["complete"] is True, receipt["reasons"]
    assert receipt["source_exact"] == raw == original
    assert receipt["comparative_period"] == {
        "printed_months": 6, "printed_end_date": "2024-06-30", "report_scope": "SEPARATE",
    }
    stock, flow = receipt["clause_receipts"]
    assert stock["kind"] == "RETAINED_NON_FLOW_SENTENCE"
    assert stock["printed_snapshot_date"] == "2024-12-31"
    assert stock["used_as_flow_period_authority"] is False
    assert flow["scaffold"] == "TREN_RELATED_NOTES_WRITTEN_SIX_MONTHS"
    for clause in (stock, flow):
        assert raw[clause["start"]:clause["end"]] == clause["source_exact"]
        assert canonical_json_sha256_v1(clause["source_exact"]) == clause["source_sha256"]


@pytest.mark.parametrize("scope,sibling_table,prior_year", [
    ("riêng", False, 2024), ("riêng", True, 2024),
    ("hợp nhất", False, 2024), ("hợp nhất", True, 2024), ("riêng", False, 2022),
])
def test_genuine_narrative_policy_owns_only_its_section_not_sibling_context(scope, sibling_table, prior_year):
    records = _genuine_narrative_policy_records(scope=scope, prior_year=prior_year)
    policy = _policy_section(records)
    if sibling_table:
        records[-1]["page_json"]["sections"].insert(0, _unrelated_policy_sibling())
    original = deepcopy(records)
    inventory = family._document_statement_period_inventory(records, compiled_specs=_adapter_compiled())
    document = inventory["document_comparative_flow_policy_receipt"]
    assert document["complete"] is True, document["reasons"]
    assert len(document["policy_source_receipts"]) == 1
    source = document["policy_source_receipts"][0]
    ownership = source["financial_narrative_ownership"]
    expected_scope = "SEPARATE" if scope == "riêng" else "CONSOLIDATED"
    assert source["owned"] is True and source["section_table_count"] == 0
    assert source["locator"]["section_id"] == ("s2" if sibling_table else "s1")
    assert source["original_section_json_sha256"] == canonical_json_sha256_v1(policy)
    assert ownership["complete"] is True and ownership["context_complete"] is True
    assert ownership["title_scope"] == ownership["parsed_flow_scope"] == expected_scope
    assert ownership["caption_scope_coherent"] is True
    assert ownership["section_narrative_count"] == 1
    assert ownership["sibling_section_context_used"] is False
    assert document["resolved_source_duration_semantics"] == [
        ["SOURCE_YTD_QUARTER", 2025, 2], ["SOURCE_YTD_QUARTER", prior_year, 2],
    ]
    assert _period_proof(records, inventory=inventory)["complete"] is True
    candidate = _public_candidate(records)
    assert candidate["status"] == READY, candidate.get("reasons")
    assert records == original


def test_genuine_narrative_owner_is_not_a_written_six_source_specific_permission():
    records = _genuine_narrative_policy_records()
    _policy_section(records)["narratives_exact"] = [_printed_flow_policy()]
    original = deepcopy(records)
    assert _period_proof(records)["complete"] is True
    assert _public_candidate(records)["status"] == READY
    assert records == original


@pytest.mark.parametrize("mutation", [
    "wrong_page_status", "wrong_statement_type", "wrong_content_kind", "missing_title", "unknown_title",
    "title_suffix", "title_footnote", "title_overlay", "borrowed_sibling_title", "policy_table",
    "second_paragraph", "title_wrong_scope", "title_entity", "title_missing_scope", "missing_flow_year",
])
def test_genuine_narrative_owner_requires_full_original_section_and_scope_proof(mutation):
    records = _genuine_narrative_policy_records()
    policy = _policy_section(records)
    if mutation == "wrong_page_status":
        records[-1]["page_json"]["status"] = "PRIMARY_FINANCIAL_STATEMENT"
    elif mutation == "wrong_statement_type":
        policy["statement_type"] = "CASH_FLOW"
    elif mutation == "wrong_content_kind":
        policy["content_kind"] = "PRIMARY_STATEMENT"
    elif mutation == "missing_title":
        policy["title_exact"] = None
    elif mutation == "unknown_title":
        policy["title_exact"] = "Thông tin khác về số liệu so sánh"
    elif mutation == "title_suffix":
        policy["title_exact"] += " áp dụng trong trường hợp khác"
    elif mutation == "title_footnote":
        policy["title_exact"] += " (*)"
    elif mutation == "title_overlay":
        policy["title_exact"] += "\u0338"
    elif mutation == "borrowed_sibling_title":
        other = deepcopy(policy)
        other["narratives_exact"] = ["Thông tin lịch sử."]
        records[-1]["page_json"]["sections"].append(other)
        policy["title_exact"] = "Thông tin khác về số liệu so sánh"
    elif mutation == "policy_table":
        policy["tables"] = _unrelated_policy_sibling()["tables"]
    elif mutation == "second_paragraph":
        policy["narratives_exact"].append("Thông tin lịch sử.")
    elif mutation == "title_wrong_scope":
        policy["title_exact"] = policy["title_exact"].replace("riêng", "hợp nhất")
    elif mutation == "title_entity":
        policy["title_exact"] += " của công ty con"
    elif mutation == "title_missing_scope":
        policy["title_exact"] = policy["title_exact"].replace(" riêng", "")
    else:
        policy["narratives_exact"][0] = policy["narratives_exact"][0].replace("30 tháng 6 năm 2024", "30 tháng 6")
    original = deepcopy(records)
    proof = _period_proof(records)
    assert proof["complete"] is False, proof
    candidate = _public_candidate(records)
    assert candidate["status"] == UNRESOLVED, candidate.get("reasons")
    assert candidate.get("mappings", []) == []
    assert records == original


@pytest.mark.parametrize("mutation", [
    "unknown_word", "missing_year", "extra_sentence", "duplicate_flow", "not_reviewed",
    "mixed_flow_scope", "mixed_stock_scope", "six_months_september_end",
])
def test_written_six_policy_cannot_drop_unknown_or_conflicting_source_assertions(mutation):
    records = _genuine_narrative_policy_records()
    policy = _policy_section(records)
    raw = policy["narratives_exact"][0]
    if mutation == "unknown_word":
        raw = raw.replace("kỳ sáu tháng", "kỳ bảy tháng")
    elif mutation == "missing_year":
        raw = raw.replace("30 tháng 6 năm 2024", "30 tháng 6")
    elif mutation == "extra_sentence":
        raw += " Số liệu này áp dụng cho một kỳ khác."
    elif mutation == "duplicate_flow":
        raw += " " + raw.split(". ", 1)[1]
    elif mutation == "not_reviewed":
        raw = raw.replace("đã được soát xét", "chưa được soát xét")
    elif mutation == "mixed_flow_scope":
        raw = raw.replace("báo cáo lưu chuyển tiền tệ riêng", "báo cáo lưu chuyển tiền tệ hợp nhất")
    elif mutation == "mixed_stock_scope":
        raw = (raw.replace("báo cáo tình hình tài chính riêng", "báo cáo tình hình tài chính hợp nhất")
               .replace("của báo cáo tài chính riêng cho năm", "của báo cáo tài chính hợp nhất cho năm"))
    else:
        raw = raw.replace("30 tháng 6 năm 2024", "30 tháng 9 năm 2024")
    policy["narratives_exact"] = [raw]
    original = deepcopy(records)
    if mutation not in {"mixed_stock_scope", "six_months_september_end"}:
        assert family._parse_printed_comparative_flow_policy(raw)["complete"] is False
    assert _period_proof(records)["complete"] is False
    candidate = _public_candidate(records)
    assert candidate["status"] == UNRESOLVED, candidate.get("reasons")
    assert candidate.get("mappings", []) == []
    assert records == original


@pytest.mark.parametrize("mutation", ["ownership_complete", "title_scope", "section_table_count", "source_exact"])
def test_genuine_narrative_ownership_self_reseal_cannot_replace_fresh_source(mutation):
    records = _genuine_narrative_policy_records()
    original = deepcopy(records)
    compiled, cluster, query = _public_query(records)
    assert cluster["status"] == READY and query is not None
    assert _evaluate_query(records, compiled, cluster, query)["status"] == READY
    forged = deepcopy(query)
    context = forged["source_context_receipt"]
    document = context["document_statement_period_inventory"]["document_comparative_flow_policy_receipt"]
    policy = document["policy_source_receipts"][0]
    if mutation == "ownership_complete":
        policy["financial_narrative_ownership"]["complete"] = False
    elif mutation == "title_scope":
        policy["financial_narrative_ownership"]["title_scope"] = "CONSOLIDATED"
    elif mutation == "section_table_count":
        policy["section_table_count"] = 1
    else:
        changed = deepcopy(records)
        _policy_section(changed)["narratives_exact"][0] = _audited_written_six_policy(prior_year=2023)
        context["document_statement_period_inventory"] = family._document_statement_period_inventory(
            changed, compiled_specs=compiled,
        )
    _reseal_receipts(forged)
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error):
        _evaluate_query(records, compiled, cluster, forged)
    assert records == original


def _absolute_flow_header_records(*, literal_note=False, scope="riêng", continuation=False):
    records = _genuine_narrative_policy_records(scope=scope)
    for index, record in enumerate(records[1:3], 1):
        section = record["page_json"]["sections"][0]
        statement = "kết quả hoạt động" if index == 1 else "lưu chuyển tiền tệ"
        section["title_exact"] = f"BÁO CÁO {statement.upper()} {scope.upper()} GIỮA NIÊN ĐỘ"
        section["narratives_exact"] = []
        table = section["tables"][0]
        table["title_exact"] = None
        for column, year in zip(table["columns"], (2025, 2024), strict=True):
            column["header_path_exact"] = ["Kỳ 6 tháng kết thúc ngày", f"30.6.{year}", "Triệu đồng"]
    if literal_note:
        note = records[0]["page_json"]["sections"][0]["tables"][0]
        for column, year in zip(note["columns"], (2025, 2024), strict=True):
            column["header_path_exact"] = ["Kỳ 6 tháng kết thúc ngày", f"30/6/{year}", "Triệu đồng"]
    if continuation:
        section = _append_flow_continuation(records, 2)
        section["title_exact"] += " (TIẾP THEO)"
    return records


def _absolute_header_section_table(records, index=1):
    section = records[index]["page_json"]["sections"][0]
    return section, section["tables"][0]


@pytest.mark.parametrize("statement_type", ["INCOME_STATEMENT", "CASH_FLOW"])
@pytest.mark.parametrize("months,day", [(3, 31), (6, 30), (9, 30), (12, 31)])
def test_owned_absolute_flow_header_pair_proves_only_full_printed_ytd_duration(statement_type, months, day):
    records = _absolute_flow_header_records()
    section, table = _absolute_header_section_table(records, 1 if statement_type == "INCOME_STATEMENT" else 2)
    for column, year in zip(table["columns"], (2025, 2022), strict=True):
        column["header_path_exact"] = [f"Kỳ {months} tháng kết thúc ngày", f"{day}.{months}.{year}", "Triệu đồng"]
    before = deepcopy((section, table))
    receipt = family._owned_absolute_flow_header_constraint(section, table)
    assert receipt is not None
    assert receipt["source_kind"] == "OWNED_PRIMARY_FLOW_HEADER_PAIR" and receipt["supported"] is True
    assert receipt["printed_months"] == months and receipt["printed_end_date"] == f"2025-{months:02d}-{day:02d}"
    assert receipt["annual_assertion"] is (months == 12)
    evidence = receipt["source_header_pair_evidence"]
    material = {key: value for key, value in evidence.items() if key != "receipt_id"}
    assert evidence["receipt_id"] == "gjitfav1:owned-absolute-flow-header-pair:" + canonical_json_sha256_v1(material)
    assert evidence["money_column_ordinals"] == [1, 2]
    assert evidence["header_paths_exact"] == [column["header_path_exact"] for column in table["columns"]]
    assert evidence["comparative_end_date"] == f"2022-{months:02d}-{day:02d}"
    assert evidence["comparative_year_origin"] == "EXPLICIT_PRINTED_HEADER"
    assert evidence["amounts_used_as_authority"] is False and evidence["source_period_keys_modified"] is False
    for ordinal, header in enumerate(evidence["headers"], 1):
        raw = " ".join(table["columns"][ordinal - 1]["header_path_exact"])
        assert header["column_ordinal"] == ordinal and header["source_exact"] == raw
        assert header["source_path_exact"] == table["columns"][ordinal - 1]["header_path_exact"]
        assert header["source_sha256"] == sha256(raw.encode("utf-8")).hexdigest()
        assert header["printed_months"] == months
    assert (section, table) == before


@pytest.mark.parametrize("presentation", ["no_currency", "trieu_vnd", "vnd", "dong", "unicode_nfd", "zero_padded", "text_column", "blank_unit"])
def test_absolute_header_pair_retains_source_layout_without_unit_or_amount_inference(presentation):
    records = _absolute_flow_header_records()
    section, table = _absolute_header_section_table(records)
    if presentation == "no_currency":
        for column in table["columns"]:
            column["header_path_exact"].pop()
    elif presentation in {"trieu_vnd", "vnd", "dong"}:
        for column in table["columns"]:
            column["header_path_exact"][-1] = {"trieu_vnd": "Triệu VND", "vnd": "VND", "dong": "đồng"}[presentation]
    elif presentation == "unicode_nfd":
        for column in table["columns"]:
            column["header_path_exact"] = [unicodedata.normalize("NFD", value) for value in column["header_path_exact"]]
    elif presentation == "zero_padded":
        for column in table["columns"]:
            column["header_path_exact"][1] = column["header_path_exact"][1].replace("30.6.", "30.06.")
    elif presentation == "text_column":
        table["columns"].insert(0, {"value_kind": "TEXT", "header_path_exact": ["Thuyết minh"]})
        for row in table["rows"]:
            row["values_exact"].insert(0, None)
    else:
        table["unit_exact"] = None
    before = deepcopy((section, table))
    receipt = family._owned_absolute_flow_header_constraint(section, table)
    assert receipt is not None and receipt["supported"] is True
    assert receipt["source_header_pair_evidence"]["money_column_ordinals"] == ([2, 3] if presentation == "text_column" else [1, 2])
    assert receipt["printed_end_date"] == "2025-06-30"
    assert (section, table) == before
    if presentation == "blank_unit":
        assert table["unit_exact"] is None


@pytest.mark.parametrize("literal_note,scope,continuation", [
    (False, "riêng", False), (True, "riêng", False), (False, "hợp nhất", False),
    (True, "hợp nhất", False), (False, "riêng", True), (True, "riêng", True),
])
def test_absolute_primary_header_context_supports_literal_and_policy_relative_note_without_rewriting_source(literal_note, scope, continuation):
    records = _absolute_flow_header_records(literal_note=literal_note, scope=scope, continuation=continuation)
    original = deepcopy(records)
    inventory = family._document_statement_period_inventory(records, compiled_specs=_adapter_compiled())
    policy = inventory["document_comparative_flow_policy_receipt"]
    assert policy["complete"] is True, policy["reasons"]
    assert len(policy["anchor_source_receipts"]) == (3 if continuation else 2)
    for source in inventory["sources"]:
        assert source["owned_current_period_constraints"]
        assert all(item["source_kind"] == "OWNED_PRIMARY_FLOW_HEADER_PAIR" for item in source["owned_current_period_constraints"])
    for anchor in policy["anchor_source_receipts"]:
        surfaces = anchor["local_period_surface_census"]
        captions = [surface for surface in surfaces if surface.get("owned_header_pair_caption_evidence")]
        dates = [surface for surface in surfaces if surface.get("owned_header_pair_date_evidence")]
        assert captions and dates
        pair = anchor["owned_current_period_constraints"][0]["source_header_pair_evidence"]
        assert all(surface["finite_owned_interim_flow_caption"] is True for surface in captions)
        assert all(surface["owned_header_pair_caption_evidence"]["header_pair_receipt_id"] == pair["receipt_id"] for surface in captions)
        assert all(surface["owned_header_pair_date_evidence"]["header_pair_receipt_id"] == pair["receipt_id"] for surface in dates)
    proof = _period_proof(records, inventory=inventory)
    assert proof["complete"] is True, proof["reasons"]
    assert proof["status"] == ("PASS_LITERAL_SOURCE_DURATION" if literal_note else "PASS_AUTHENTICATED_PRINTED_COMPARATIVE_FLOW_POLICY")
    assert proof["amounts_used_as_authority"] is False and proof["source_period_keys_modified"] is False
    assert proof["start_dates_inferred"] is False
    assert _public_candidate(records)["status"] == READY
    assert records == original


@pytest.mark.parametrize("linebreak,method", [("\n", "trực tiếp"), ("\\n", "trực tiếp"), ("\n", "gián tiếp"), ("\\n", "gián tiếp")])
def test_owned_absolute_header_cf_continuation_accepts_only_full_finite_method_caption(linebreak, method):
    records = _absolute_flow_header_records(continuation=True)
    for index in (2, 4):
        section, _table = _absolute_header_section_table(records, index)
        section["title_exact"] += linebreak + f"(Phương pháp {method})"
    before = deepcopy(records)
    assert _period_proof(records)["complete"] is True
    assert _public_candidate(records)["status"] == READY
    assert records == before


@pytest.mark.parametrize("mutation", [
    "missing_header_part", "empty_path", "null_path_token", "relative_label", "unknown_month_word",
    "unsupported_month", "non_ytd_month", "non_last_day", "invalid_date", "different_months",
    "different_endpoint", "same_year", "reversed_years", "slash_dates", "mixed_separators",
    "suffix", "prefix", "footnote", "overlay", "superscript", "extra_money", "one_money",
    "percent_column", "unknown_unit", "date_range", "duplicate_date",
])
def test_absolute_header_pair_rejects_every_unreviewed_or_incomplete_axis(mutation):
    records = _absolute_flow_header_records()
    section, table = _absolute_header_section_table(records)
    current, prior = table["columns"]
    path = current["header_path_exact"]
    if mutation == "missing_header_part":
        path.pop(0)
    elif mutation == "empty_path":
        current["header_path_exact"] = []
    elif mutation == "null_path_token":
        path[1] = None
    elif mutation == "relative_label":
        current["header_path_exact"] = ["Kỳ này"]
    elif mutation == "unknown_month_word":
        path[0] = "Kỳ sáu tháng kết thúc ngày"
    elif mutation == "unsupported_month":
        path[0] = "Kỳ 2 tháng kết thúc ngày"
    elif mutation == "non_ytd_month":
        path[1] = "30.9.2025"
    elif mutation == "non_last_day":
        path[1] = "29.6.2025"
    elif mutation == "invalid_date":
        path[1] = "31.6.2025"
    elif mutation == "different_months":
        prior["header_path_exact"] = ["Kỳ 3 tháng kết thúc ngày", "31.3.2024", "Triệu đồng"]
    elif mutation == "different_endpoint":
        prior["header_path_exact"][1] = "29.6.2024"
    elif mutation == "same_year":
        prior["header_path_exact"][1] = "30.6.2025"
    elif mutation == "reversed_years":
        current["header_path_exact"], prior["header_path_exact"] = prior["header_path_exact"], current["header_path_exact"]
    elif mutation == "slash_dates":
        path[1] = "30/6/2025"
    elif mutation == "mixed_separators":
        path[1] = "30.6/2025"
    elif mutation == "suffix":
        path.append("cho kỳ khác")
    elif mutation == "prefix":
        path.insert(0, "Ước tính")
    elif mutation == "footnote":
        path.append("(*)")
    elif mutation == "overlay":
        path[0] += "\u0338"
    elif mutation == "superscript":
        path[0] += "¹"
    elif mutation == "extra_money":
        table["columns"].append(deepcopy(current))
        for row in table["rows"]:
            row["values_exact"].append("999")
    elif mutation == "one_money":
        prior["value_kind"] = "TEXT"
    elif mutation == "percent_column":
        table["columns"].append({"value_kind": "PERCENT", "header_path_exact": ["Tỷ lệ"]})
        for row in table["rows"]:
            row["values_exact"].append("20%")
    elif mutation == "unknown_unit":
        path[-1] = "USD"
    elif mutation == "date_range":
        path[1] = "1.1.2025-30.6.2025"
    else:
        path.append("30.6.2025")
    before = deepcopy((section, table))
    assert family._owned_absolute_flow_header_constraint(section, table) is None
    assert (section, table) == before


@pytest.mark.parametrize("kind,statement_type", [
    ("FINANCIAL_NOTE", "NOT_APPLICABLE"), ("FINANCIAL_NARRATIVE", "NOT_APPLICABLE"),
    ("PRIMARY_STATEMENT", "BALANCE_SHEET"), ("PRIMARY_STATEMENT", "NOT_APPLICABLE"),
])
def test_header_duration_fallback_cannot_create_statement_ownership(kind, statement_type):
    records = _absolute_flow_header_records()
    section, table = _absolute_header_section_table(records)
    section["content_kind"], section["statement_type"] = kind, statement_type
    before = deepcopy((section, table))
    assert family._owned_absolute_flow_header_constraint(section, table) is None
    assert (section, table) == before


@pytest.mark.parametrize("mutation", [
    "unsupported_caption", "conflicting_caption", "conflicting_narrative", "unknown_caption_suffix",
    "method_suffix", "income_method", "wrong_scope", "entity_override", "unknown_row_ancestor",
    "note_interim_title", "policy_prior_conflict", "competing_policy", "continuation_missing_date",
])
def test_header_fallback_never_waives_caption_scope_policy_or_other_source_veto(mutation):
    records = _absolute_flow_header_records(continuation=True)
    section, table = _absolute_header_section_table(records, 2)
    if mutation == "unsupported_caption":
        section["title_exact"] += "\nCho kỳ kế toán chưa xác định"
    elif mutation == "conflicting_caption":
        section["title_exact"] += "\nCho kỳ hoạt động 6 tháng kết thúc ngày 30 tháng 6 năm 2023"
    elif mutation == "conflicting_narrative":
        section["narratives_exact"] = ["Cho kỳ hoạt động 6 tháng kết thúc ngày 30 tháng 6 năm 2023"]
    elif mutation == "unknown_caption_suffix":
        section["title_exact"] += " cho một kỳ khác"
    elif mutation == "method_suffix":
        section["title_exact"] += "\n(Phương pháp trực tiếp) thêm"
    elif mutation == "income_method":
        _absolute_header_section_table(records)[0]["title_exact"] += "\n(Phương pháp trực tiếp)"
    elif mutation == "wrong_scope":
        section["title_exact"] = section["title_exact"].replace("RIÊNG", "HỢP NHẤT")
    elif mutation == "entity_override":
        section["title_exact"] += " của công ty con"
    elif mutation == "unknown_row_ancestor":
        table["rows"][0]["hierarchy_path_exact"].insert(0, "Kỳ vô định năm 2023")
    elif mutation == "note_interim_title":
        records[0]["page_json"]["sections"][0]["title_exact"] += " GIỮA NIÊN ĐỘ"
    elif mutation == "policy_prior_conflict":
        _policy_section(records)["narratives_exact"] = [_audited_written_six_policy(prior_year=2022)]
    elif mutation == "competing_policy":
        second = deepcopy(_policy_section(records))
        second["narratives_exact"] = [_audited_written_six_policy(prior_year=2022)]
        records[-2]["page_json"]["sections"].append(second)
    else:
        continuation, _ = _absolute_header_section_table(records, 4)
        continuation["tables"][0]["columns"][1]["header_path_exact"] = ["Kỳ trước"]
    before = deepcopy(records)
    assert _period_proof(records)["complete"] is False
    candidate = _public_candidate(records)
    assert candidate["status"] == UNRESOLVED, candidate.get("reasons")
    assert candidate.get("mappings", []) == []
    assert records == before


def test_matching_owned_caption_remains_authority_instead_of_header_fallback():
    records = _absolute_flow_header_records()
    section, table = _absolute_header_section_table(records)
    section["title_exact"] += "\nCho kỳ hoạt động 6 tháng kết thúc ngày 30 tháng 6 năm 2025"
    before = deepcopy(records)
    inventory = family._document_statement_period_inventory(records, compiled_specs=_adapter_compiled())
    income = next(source for source in inventory["sources"] if source["statement_type"] == "INCOME_STATEMENT")
    assert income["owned_current_period_constraints"]
    assert all(item["source_kind"] != "OWNED_PRIMARY_FLOW_HEADER_PAIR" for item in income["owned_current_period_constraints"])
    assert _period_proof(records, inventory=inventory)["complete"] is True
    assert _public_candidate(records)["status"] == READY
    assert records == before and table["columns"][0]["header_path_exact"][1] == "30.6.2025"


@pytest.mark.parametrize("mutation", ["end_date", "header_path", "money_axis", "comparative_year_origin", "source_pair_hash"])
def test_self_resealed_absolute_header_context_cannot_replace_original_source(mutation):
    records = _absolute_flow_header_records()
    before = deepcopy(records)
    compiled, cluster, query = _public_query(records)
    assert query is not None and _evaluate_query(records, compiled, cluster, query)["status"] == READY
    forged = deepcopy(query)
    inventory = forged["source_context_receipt"]["document_statement_period_inventory"]
    source = next(item for item in inventory["sources"] if item["statement_type"] == "INCOME_STATEMENT")
    constraint = source["owned_current_period_constraints"][0]
    evidence = constraint["source_header_pair_evidence"]
    if mutation == "end_date":
        constraint["printed_end_date"] = "2023-06-30"
    elif mutation == "header_path":
        evidence["header_paths_exact"][0][1] = "30.6.2023"
    elif mutation == "money_axis":
        evidence["money_column_ordinals"] = [2, 1]
    elif mutation == "comparative_year_origin":
        evidence["comparative_year_origin"] = "DERIVED_YEAR_MINUS_ONE"
    else:
        evidence["headers"][0]["source_sha256"] = "0" * 64
    _reseal_receipts(forged)
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error):
        _evaluate_query(records, compiled, cluster, forged)
    assert records == before


@pytest.mark.parametrize("index,statement", [(1, "kết quả hoạt động"), (2, "lưu chuyển tiền tệ")])
def test_bare_annual_statement_caption_cannot_be_overridden_by_six_month_headers(index, statement):
    records = _absolute_flow_header_records()
    section, table = _absolute_header_section_table(records, index)
    section["title_exact"] = f"Báo cáo {statement} riêng năm 2025"
    before = deepcopy(records)
    constraints = family._owned_current_period_constraints(section, table)
    assert constraints and all(item["source_kind"] != "OWNED_PRIMARY_FLOW_HEADER_PAIR" for item in constraints)
    assert any(item["supported"] is True and item.get("printed_annual_year") == 2025 for item in constraints)
    inventory = family._document_statement_period_inventory(records, compiled_specs=_adapter_compiled())
    policy = inventory["document_comparative_flow_policy_receipt"]
    assert policy["complete"] is False and policy["status"] == "ALGORITHM_HOLD"
    assert _period_proof(records, inventory=inventory)["complete"] is False
    candidate = _public_candidate(records)
    assert candidate["status"] == UNRESOLVED and candidate.get("mappings", []) == []
    assert records == before


@pytest.mark.parametrize("index,statement", [(1, "kết quả hoạt động"), (2, "lưu chuyển tiền tệ")])
def test_matching_bare_annual_statement_is_existing_caption_authority_not_header_fallback(index, statement):
    records = _absolute_flow_header_records()
    section, table = _absolute_header_section_table(records, index)
    section["title_exact"] = f"Báo cáo {statement} riêng năm 2025"
    for column, year in zip(table["columns"], (2025, 2024), strict=True):
        column["header_path_exact"] = ["Kỳ 12 tháng kết thúc ngày", f"31.12.{year}", "Triệu đồng"]
    before = deepcopy((section, table))
    constraints = family._owned_current_period_constraints(section, table)
    assert constraints and all(item["source_kind"] != "OWNED_PRIMARY_FLOW_HEADER_PAIR" for item in constraints)
    assert any(item["supported"] is True and item.get("printed_annual_year") == 2025
               and item["source_kind"] == "SECTION_TITLE" for item in constraints)
    assert (section, table) == before


@pytest.mark.parametrize("index,statement", [(1, "kết quả hoạt động"), (2, "lưu chuyển tiền tệ")])
@pytest.mark.parametrize("annotation", [" kỳ chưa xác định", " (*)", "\u0338"])
def test_malformed_bare_annual_caption_is_unsupported_never_ignored_for_header_fallback(index, statement, annotation):
    records = _absolute_flow_header_records()
    section, table = _absolute_header_section_table(records, index)
    section["title_exact"] = f"Báo cáo {statement} riêng năm 2025" + annotation
    before = deepcopy(records)
    constraints = family._owned_current_period_constraints(section, table)
    assert constraints and any(item["supported"] is False for item in constraints)
    assert all(item["source_kind"] != "OWNED_PRIMARY_FLOW_HEADER_PAIR" for item in constraints)
    assert _period_proof(records)["complete"] is False
    candidate = _public_candidate(records)
    assert candidate["status"] == UNRESOLVED and candidate.get("mappings", []) == []
    assert records == before


@pytest.mark.parametrize("index", [1, 2])
@pytest.mark.parametrize("literal_note", [False, True])
@pytest.mark.parametrize("assertion", [
    "Quý II năm 2025",
    "Kỳ kế toán 9 tháng kết thúc ngày 30 tháng 9 năm 2025",
    "Từ ngày 01/04/2025 đến ngày 30/06/2025",
    "For the period ended 30/6/2025",
    "For the year ended 31/12/2025",
    "For the quarter ended 30/6/2025",
    "From 01/04/2025 to 30/06/2025",
])
def test_unparsed_explicit_caption_without_cho_cannot_hide_behind_dated_header_fallback(index, literal_note, assertion):
    records = _absolute_flow_header_records(literal_note=literal_note)
    section, table = _absolute_header_section_table(records, index)
    section["title_exact"] += "\n" + assertion
    before = deepcopy(records)
    constraints = family._owned_current_period_constraints(section, table)
    if assertion == "Quý II năm 2025":
        # Preserve this baseline NODEID. The complete typed report caption is
        # now recognized by a finite endpoint grammar; it is no longer an
        # unsupported assertion hidden behind the dated-header fallback.
        # Select expectations from the literal fixture, never from whether the
        # implementation happens to recognize it on this run.
        expected_periods = [["SOURCE_YTD_QUARTER", 2025, 2], ["SOURCE_YTD_QUARTER", 2024, 2]]
        assert len(constraints) == 1
        constraint = constraints[0]
        assert constraint["source_kind"] == "SECTION_TITLE"
        assert constraint["source_exact"] == section["title_exact"]
        assert constraint["supported"] is True
        assert constraint["printed_reporting_quarter"] == 2
        assert constraint["printed_year"] == 2025
        endpoint = constraint["source_report_quarter_evidence"]
        assert endpoint["supported"] is True
        assert endpoint["source_exact"] == section["title_exact"]
        assert endpoint["comparative_year_permission_granted"] is False
        assert endpoint["start_dates_inferred"] is False
        assert all(item["source_kind"] != "OWNED_PRIMARY_FLOW_HEADER_PAIR" for item in constraints)
        compiled = _adapter_compiled()
        lane = family._multitable_lane_axis(section, table, compiled_specs=compiled)
        assert lane["complete"] is True
        assert family._printed_duration_lengths(table, [1, 2], section=section) == [[6], [6]]
        assert family._absolute_source_duration_semantics(section, table, lane) == expected_periods
        inventory = family._document_statement_period_inventory(records, compiled_specs=compiled)
        policy = inventory["document_comparative_flow_policy_receipt"]
        assert policy["complete"] is True
        assert policy["resolved_source_duration_semantics"] == expected_periods
        for left in (index, 0):
            accepted = family._source_period_correspondence_receipt(
                left_locator=_contextual_period_locator(records[left]),
                right_locator=_contextual_period_locator(records[index]),
                left_money_column_ordinals=[1, 2], right_money_column_ordinals=[1, 2],
                page_records=records, compiled_specs=compiled, document_period_inventory=inventory,
            )
            assert accepted["complete"] is True
            assert accepted["status"].startswith("PASS_")
        selected = _period_proof(records, inventory=inventory)
        assert selected["complete"] is True
        if literal_note:
            assert selected["status"] == "PASS_LITERAL_SOURCE_DURATION"
            assert selected["period_resolution_evidence"] == []
        else:
            assert selected["status"] == "PASS_AUTHENTICATED_PRINTED_COMPARATIVE_FLOW_POLICY"
            inherited = [item["inherited_document_comparative_flow_policy_receipt"]
                         for item in selected["period_resolution_evidence"]
                         if item["inherited_document_comparative_flow_policy_receipt"] is not None]
            assert inherited and all(item["complete"] is True for item in inherited)
        candidate = _public_candidate(records)
        assert candidate["status"] == READY and candidate["mappings"]
        allowed_versions = {records[0]["page_json_version_id"], records[1]["page_json_version_id"]}
        refs = [ref for mapping in candidate["mappings"] for ref in mapping.get("source_refs", [])]
        assert refs and all(ref["locator"]["page_json_version_id"] in allowed_versions for ref in refs)
        assert all(ref["locator"]["page_json_version_id"] != records[2]["page_json_version_id"] for ref in refs)
        assert records == before
        return
    assert constraints and any(item["supported"] is False for item in constraints)
    assert all(item["source_kind"] != "OWNED_PRIMARY_FLOW_HEADER_PAIR" for item in constraints)
    compiled = _adapter_compiled()
    lane = family._multitable_lane_axis(section, table, compiled_specs=compiled)
    assert lane["complete"] is True
    assert family._absolute_source_duration_semantics(section, table, lane) is None
    inventory = family._document_statement_period_inventory(records, compiled_specs=compiled)
    policy = inventory["document_comparative_flow_policy_receipt"]
    assert policy["complete"] is False and policy["status"] == "ALGORITHM_HOLD"
    for left in (index, 0):
        rejected = family._source_period_correspondence_receipt(
            left_locator=_contextual_period_locator(records[left]),
            right_locator=_contextual_period_locator(records[index]),
            left_money_column_ordinals=[1, 2], right_money_column_ordinals=[1, 2],
            page_records=records, compiled_specs=compiled, document_period_inventory=inventory,
        )
        assert rejected["complete"] is False and rejected["status"] == "ALGORITHM_HOLD"
    selected = _period_proof(records, inventory=inventory)
    candidate = _public_candidate(records)
    if index == 2 and literal_note:
        # Unsupported unselected CF cannot supply authority, but does not
        # falsify an independent literal NOTE/INCOME pair either.
        assert selected["complete"] is True and selected["status"] == "PASS_LITERAL_SOURCE_DURATION"
        assert selected["period_resolution_evidence"] == []
        assert candidate["status"] == READY and candidate["mappings"]
        allowed_versions = {records[0]["page_json_version_id"], records[1]["page_json_version_id"]}
        refs = [ref for mapping in candidate["mappings"] for ref in mapping.get("source_refs", [])]
        assert refs and all(ref["locator"]["page_json_version_id"] in allowed_versions for ref in refs)
        assert all(ref["locator"]["page_json_version_id"] != records[2]["page_json_version_id"] for ref in refs)
    else:
        assert selected["complete"] is False
        assert candidate["status"] == UNRESOLVED and candidate.get("mappings", []) == []
    assert records == before


@pytest.mark.parametrize("index", [1, 2])
@pytest.mark.parametrize("literal_note", [False, True])
def test_supported_report_quarter_endpoint_must_match_actual_six_month_header_window(index, literal_note):
    records = _absolute_flow_header_records(literal_note=literal_note)
    section, table = _absolute_header_section_table(records, index)
    section["title_exact"] += "\nQuý III năm 2025"
    before = deepcopy(records)
    constraints = family._owned_current_period_constraints(section, table)
    assert len(constraints) == 1 and constraints[0]["supported"] is True
    assert constraints[0]["printed_reporting_quarter"] == 3
    assert constraints[0]["printed_year"] == 2025
    assert constraints[0]["source_report_quarter_evidence"]["source_exact"] == section["title_exact"]
    compiled = _adapter_compiled()
    lane = family._multitable_lane_axis(section, table, compiled_specs=compiled)
    assert lane["complete"] is True
    assert family._printed_duration_lengths(table, [1, 2], section=section) == [[6], [6]]
    assert family._owned_current_period_constraints_match(section, table, lane) is False
    assert family._absolute_source_duration_semantics(section, table, lane) is None
    inventory = family._document_statement_period_inventory(records, compiled_specs=compiled)
    for left in (index, 0):
        rejected = family._source_period_correspondence_receipt(
            left_locator=_contextual_period_locator(records[left]),
            right_locator=_contextual_period_locator(records[index]),
            left_money_column_ordinals=[1, 2], right_money_column_ordinals=[1, 2],
            page_records=records, compiled_specs=compiled, document_period_inventory=inventory,
        )
        assert rejected["complete"] is False and rejected["status"] == "ALGORITHM_HOLD"
    selected = _period_proof(records, inventory=inventory)
    assert selected["complete"] is False and selected["status"] == "ALGORITHM_HOLD"
    if index == 2:
        assert any(item["status"] == "PROVEN_CONTRADICTORY_PRINTED_PERIOD"
                   for item in selected["cash_flow_printed_period_controls"])
    candidate = _public_candidate(records)
    assert candidate["status"] == UNRESOLVED and candidate.get("mappings", []) == []
    assert records == before


@pytest.mark.parametrize("index", [1, 2])
@pytest.mark.parametrize("literal_note", [False, True])
def test_unknown_annotation_is_not_whole_report_quarter_endpoint_authority(index, literal_note):
    records = _absolute_flow_header_records(literal_note=literal_note)
    section, table = _absolute_header_section_table(records, index)
    section["title_exact"] += "\nQuý II năm 2025 (kỳ kế toán khác)"
    before = deepcopy(records)
    constraints = family._owned_current_period_constraints(section, table)
    assert constraints and any(item["supported"] is False for item in constraints)
    assert all(item["source_kind"] != "OWNED_PRIMARY_FLOW_HEADER_PAIR" for item in constraints)
    compiled = _adapter_compiled()
    lane = family._multitable_lane_axis(section, table, compiled_specs=compiled)
    assert lane["complete"] is True
    assert family._absolute_source_duration_semantics(section, table, lane) is None
    inventory = family._document_statement_period_inventory(records, compiled_specs=compiled)
    rejected = family._source_period_correspondence_receipt(
        left_locator=_contextual_period_locator(records[index]),
        right_locator=_contextual_period_locator(records[index]),
        left_money_column_ordinals=[1, 2], right_money_column_ordinals=[1, 2],
        page_records=records, compiled_specs=compiled, document_period_inventory=inventory,
    )
    assert rejected["complete"] is False and rejected["status"] == "ALGORITHM_HOLD"
    selected = _period_proof(records, inventory=inventory)
    candidate = _public_candidate(records)
    if index == 2 and literal_note:
        # An unknown, unselected CF caption remains unknown, not contradictory
        # evidence against an independently printed literal NOTE/INCOME pair.
        assert selected["complete"] is True and selected["status"] == "PASS_LITERAL_SOURCE_DURATION"
        assert selected["period_resolution_evidence"] == []
        assert candidate["status"] == READY and candidate["mappings"]
        allowed_versions = {records[0]["page_json_version_id"], records[1]["page_json_version_id"]}
        refs = [ref for mapping in candidate["mappings"] for ref in mapping.get("source_refs", [])]
        assert refs and all(ref["locator"]["page_json_version_id"] in allowed_versions for ref in refs)
    else:
        assert selected["complete"] is False
        assert candidate["status"] == UNRESOLVED and candidate.get("mappings", []) == []
    assert records == before


@pytest.mark.parametrize("index", [1, 2])
@pytest.mark.parametrize("literal_note", [False, True])
def test_multi_table_section_does_not_make_its_explicit_caption_assertion_absent(index, literal_note):
    records = _absolute_flow_header_records(literal_note=literal_note)
    section, table = _absolute_header_section_table(records, index)
    section["title_exact"] += "\nKỳ kế toán 9 tháng kết thúc ngày 30 tháng 9 năm 2025"
    section["tables"].append(deepcopy(table))
    before = deepcopy(records)
    compiled = _adapter_compiled()
    for source_table in section["tables"]:
        constraints = family._owned_current_period_constraints(section, source_table)
        assert constraints and any(item["supported"] is False for item in constraints)
        assert all(item["source_kind"] != "OWNED_PRIMARY_FLOW_HEADER_PAIR" for item in constraints)
        lane = family._multitable_lane_axis(section, source_table, compiled_specs=compiled)
        assert lane["complete"] is True
        assert family._absolute_source_duration_semantics(section, source_table, lane) is None
    inventory = family._document_statement_period_inventory(records, compiled_specs=compiled)
    assert inventory["document_comparative_flow_policy_receipt"]["complete"] is False
    for table_ordinal, _source_table in enumerate(section["tables"], 1):
        bad_locator = _contextual_period_locator(records[index]) | {"table_id": f"t{table_ordinal}"}
        for left_locator in (bad_locator, _contextual_period_locator(records[0])):
            rejected = family._source_period_correspondence_receipt(
                left_locator=left_locator, right_locator=bad_locator,
                left_money_column_ordinals=[1, 2], right_money_column_ordinals=[1, 2],
                page_records=records, compiled_specs=compiled, document_period_inventory=inventory,
            )
            assert rejected["complete"] is False and rejected["status"] == "ALGORITHM_HOLD"
    selected = _period_proof(records, inventory=inventory)
    candidate = _public_candidate(records)
    if index == 2 and literal_note:
        assert selected["complete"] is True and selected["status"] == "PASS_LITERAL_SOURCE_DURATION"
        assert selected["period_resolution_evidence"] == []
        assert candidate["status"] == READY and candidate["mappings"]
        allowed_versions = {records[0]["page_json_version_id"], records[1]["page_json_version_id"]}
        refs = [ref for mapping in candidate["mappings"] for ref in mapping.get("source_refs", [])]
        assert refs and all(ref["locator"]["page_json_version_id"] in allowed_versions for ref in refs)
        assert all(ref["locator"]["page_json_version_id"] != records[2]["page_json_version_id"] for ref in refs)
    else:
        assert selected["complete"] is False
        assert candidate["status"] == UNRESOLVED and candidate.get("mappings", []) == []
    assert records == before


def _whole_flow_range_caption(*, statement="INCOME_STATEMENT", scope="riêng", months=6, year=2025):
    title = {"INCOME_STATEMENT": "kết quả hoạt động", "CASH_FLOW": "lưu chuyển tiền tệ"}[statement]
    population = " " + scope if scope else ""
    day = {3: 31, 6: 30, 9: 30, 12: 31}[months]
    return (
        f"Báo cáo {title}{population} giữa niên độ cho giai đoạn\n"
        f"từ ngày 01/1/{year} đến ngày {day}/{months}/{year}"
    )


def _whole_flow_range_records(*, source_kind="SECTION_TITLE", scope="riêng"):
    # Literal relative axes make the printed range necessary: no dated header
    # pair can accidentally supply the current duration being tested here.
    records = _comparative_flow_records(scope=scope, current_year=2025, prior_year=2024)
    for index, statement in ((1, "INCOME_STATEMENT"), (2, "CASH_FLOW")):
        section, table = _absolute_header_section_table(records, index)
        section["narratives_exact"] = []
        title = "kết quả hoạt động" if index == 1 else "lưu chuyển tiền tệ"
        section["title_exact"] = f"Báo cáo {title} {scope}"
        table["title_exact"] = None
        owner = section if source_kind == "SECTION_TITLE" else table
        owner["title_exact"] = _whole_flow_range_caption(statement=statement, scope=scope)
    return records


@pytest.mark.parametrize("statement", ["INCOME_STATEMENT", "CASH_FLOW"])
@pytest.mark.parametrize("source_kind", ["SECTION_TITLE", "TABLE_TITLE"])
@pytest.mark.parametrize("months", [3, 6, 9])
def test_whole_primary_range_retains_both_explicit_dates_without_other_permissions(statement, source_kind, months):
    section = {"content_kind": "PRIMARY_STATEMENT", "statement_type": statement}
    raw = _whole_flow_range_caption(statement=statement, months=months)
    before = deepcopy(section)
    constraint = family._owned_flow_date_range_caption_constraint(section, source_kind=source_kind, source_exact=raw)
    assert constraint is not None and constraint["supported"] is True
    assert constraint["source_kind"] == source_kind and constraint["source_exact"] == raw
    assert constraint["printed_start_date"] == "2025-01-01"
    assert constraint["printed_end_date"] == f"2025-{months:02d}-" + ("31" if months == 3 else "30")
    assert constraint["printed_months"] == months and constraint["annual_assertion"] is False
    evidence = constraint["source_date_range_evidence"]
    assert evidence["format_version"] == "F39_WHOLE_OWNED_FLOW_DATE_RANGE_CAPTION_V1"
    assert evidence["source_sha256"] == sha256(raw.encode("utf-8")).hexdigest()
    assert evidence["source_lines_exact"] == raw.split("\n")
    assert evidence["printed_start_date"] == constraint["printed_start_date"]
    assert evidence["printed_end_date"] == constraint["printed_end_date"]
    assert evidence["printed_months"] == months and evidence["reasons"] == []
    for flag in (
        "unit_permission_granted", "report_scope_permission_granted", "comparative_year_permission_granted",
        "amounts_used_as_authority", "source_period_keys_modified", "start_dates_inferred", "sibling_or_other_surface_used",
    ):
        assert evidence[flag] is False
    material = {key: value for key, value in evidence.items() if key != "receipt_id"}
    assert evidence["receipt_id"] == "gjitfav1:owned-flow-date-range-caption:" + canonical_json_sha256_v1(material)
    assert section == before


@pytest.mark.parametrize("presentation", [
    "unqualified_scope", "consolidated", "nfd", "serialized_newline", "whitespace", "continuation_before",
    "continuation_after", "cf_direct", "cf_indirect", "zero_padded", "tab_cues", "newline_cues",
])
def test_whole_primary_range_admits_only_reviewed_printed_layout_variants(presentation):
    statement = "CASH_FLOW" if presentation.startswith("cf_") else "INCOME_STATEMENT"
    raw = _whole_flow_range_caption(statement=statement)
    if presentation == "unqualified_scope":
        raw = raw.replace(" riêng", "")
    elif presentation == "consolidated":
        raw = raw.replace(" riêng", " hợp nhất")
    elif presentation == "nfd":
        raw = unicodedata.normalize("NFD", raw)
    elif presentation == "serialized_newline":
        raw = raw.replace("\n", "\\n")
    elif presentation == "whitespace":
        raw = " \t" + raw.replace(" cho ", "\r\ncho ") + "\n "
    elif presentation in {"tab_cues", "newline_cues"}:
        separator = "\t" if presentation == "tab_cues" else "\n"
        raw = raw.replace("từ ngày", "từ" + separator + "ngày").replace("đến ngày", "đến" + separator + "ngày")
    elif presentation == "continuation_before":
        raw = raw.replace("giữa niên độ", "giữa niên độ (tiếp theo)")
    elif presentation == "continuation_after":
        raw += "\n(tiếp theo)"
    elif presentation.startswith("cf_"):
        raw += "\n(Phương pháp " + ("trực tiếp" if presentation == "cf_direct" else "gián tiếp") + ")"
    else:
        raw = raw.replace("01/1/", "01/01/").replace("30/6/", "30/06/")
    section = {"content_kind": "PRIMARY_STATEMENT", "statement_type": statement}
    constraint = family._owned_flow_date_range_caption_constraint(section, source_kind="SECTION_TITLE", source_exact=raw)
    assert constraint is not None and constraint["supported"] is True
    assert constraint["source_exact"] == raw and constraint["printed_start_date"] == "2025-01-01"
    assert constraint["printed_end_date"] == "2025-06-30"
    evidence = constraint["source_date_range_evidence"]
    assert evidence["source_lines_exact"] == raw.split("\n")
    assert evidence["source_sha256"] == sha256(raw.encode("utf-8")).hexdigest()
    assert evidence["report_scope_permission_granted"] is False


@pytest.mark.parametrize("mutation", [
    "non_january_start", "second_day_start", "different_years", "reverse_years", "invalid_start", "invalid_end",
    "non_quarter_end", "non_last_day", "annual_interim", "missing_start", "missing_end", "missing_year",
    "wrong_separator", "company_prefix", "extra_sentence", "footnote", "overlay", "superscript",
    "date_digit_accent", "end_date_digit_acute", "end_date_digit_grave", "end_date_digit_horn",
    "duplicate_continuation", "income_method", "negation",
])
def test_whole_primary_range_keeps_malformed_or_unsupported_assertions_as_vetoes(mutation):
    raw = _whole_flow_range_caption()
    replacements = {
        "non_january_start": ("01/1/2025", "01/4/2025"),
        "second_day_start": ("01/1/2025", "02/1/2025"),
        "different_years": ("01/1/2025", "01/1/2024"),
        "reverse_years": ("01/1/2025", "01/1/2026"),
        "invalid_start": ("01/1/2025", "32/1/2025"),
        "invalid_end": ("30/6/2025", "31/6/2025"),
        "non_quarter_end": ("30/6/2025", "31/5/2025"),
        "non_last_day": ("30/6/2025", "29/6/2025"),
        "annual_interim": ("30/6/2025", "31/12/2025"),
        "missing_start": ("01/1/2025", ""),
        "missing_end": ("30/6/2025", ""),
        "missing_year": ("30/6/2025", "30/6"),
        "wrong_separator": ("30/6/2025", "30.6.2025"),
        "date_digit_accent": ("01/1/2025", "0\u03011/1/2025"),
        "end_date_digit_acute": ("30/6/2025", "3\u03010/6/2025"),
        "end_date_digit_grave": ("30/6/2025", "30/6\u0300/2025"),
        "end_date_digit_horn": ("30/6/2025", "30/6/202\u031b5"),
        "negation": ("cho giai đoạn", "không cho giai đoạn"),
    }
    if mutation in replacements:
        raw = raw.replace(*replacements[mutation])
    elif mutation == "company_prefix":
        raw = "Ngân hàng A\n" + raw
    elif mutation == "extra_sentence":
        raw += ". Áp dụng cho kỳ khác."
    elif mutation == "footnote":
        raw += " (*)"
    elif mutation == "overlay":
        raw += "\u0338"
    elif mutation == "superscript":
        raw += "¹"
    elif mutation == "duplicate_continuation":
        raw = raw.replace("giữa niên độ", "giữa niên độ (tiếp theo)") + " (tiếp theo)"
    else:
        raw += " (Phương pháp trực tiếp)"
    section = {"content_kind": "PRIMARY_STATEMENT", "statement_type": "INCOME_STATEMENT"}
    constraint = family._owned_flow_date_range_caption_constraint(section, source_kind="SECTION_TITLE", source_exact=raw)
    assert constraint is not None and constraint["supported"] is False
    evidence = constraint["source_date_range_evidence"]
    assert evidence["reasons"] and evidence["source_exact"] == raw
    assert evidence["source_sha256"] == sha256(raw.encode("utf-8")).hexdigest()


@pytest.mark.parametrize("content_kind,statement_type", [
    ("FINANCIAL_NOTE", "NOT_APPLICABLE"), ("FINANCIAL_NARRATIVE", "NOT_APPLICABLE"),
    ("PRIMARY_STATEMENT", "BALANCE_SHEET"), ("PRIMARY_STATEMENT", "NOT_APPLICABLE"),
    ("FINANCIAL_NOTE", "INCOME_STATEMENT"),
])
def test_whole_primary_range_does_not_grant_duration_to_another_source_kind(content_kind, statement_type):
    section = {"content_kind": content_kind, "statement_type": statement_type}
    raw = _whole_flow_range_caption()
    constraint = family._owned_flow_date_range_caption_constraint(section, source_kind="TABLE_TITLE", source_exact=raw)
    assert constraint is not None and constraint["supported"] is False
    assert "RANGE_NOT_OWNED_BY_TYPED_PRIMARY_FLOW_CAPTION" in constraint["source_date_range_evidence"]["reasons"]


@pytest.mark.parametrize("source_kind,raw", [
    ("SECTION_TITLE", "Báo cáo kết quả hoạt động riêng giữa niên độ"),
    ("OWNED_NARRATIVE", "Từ ngày 01/1/2025 đến ngày 30/6/2025"),
])
def test_whole_primary_range_leaves_irrelevant_or_unowned_surfaces_without_authority(source_kind, raw):
    section = {"content_kind": "PRIMARY_STATEMENT", "statement_type": "INCOME_STATEMENT"}
    assert family._owned_flow_date_range_caption_constraint(section, source_kind=source_kind, source_exact=raw) is None


@pytest.mark.parametrize("source_kind", ["SECTION_TITLE", "TABLE_TITLE"])
@pytest.mark.parametrize("scope", ["riêng", "hợp nhất"])
def test_whole_primary_ranges_supply_relative_note_policy_without_absolute_header_fallback(source_kind, scope):
    records = _whole_flow_range_records(source_kind=source_kind, scope=scope)
    before = deepcopy(records)
    compiled = _adapter_compiled()
    inventory = family._document_statement_period_inventory(records, compiled_specs=compiled)
    policy = inventory["document_comparative_flow_policy_receipt"]
    assert policy["complete"] is True and policy["reasons"] == []
    for index, source in enumerate(inventory["sources"], 1):
        section, table = _absolute_header_section_table(records, index)
        assert family._owned_absolute_flow_header_constraint(section, table) is None
        constraints = source["owned_current_period_constraints"]
        assert len(constraints) == 1 and constraints[0]["source_kind"] == source_kind
        assert constraints[0]["supported"] is True and constraints[0]["printed_start_date"] == "2025-01-01"
        assert source["lane_axis"]["source_lane_keys"] == [
            ["SEMANTIC_ALIAS", "CURRENT_PERIOD"], ["SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"],
        ]
    proof = _period_proof(records, inventory=inventory)
    assert proof["complete"] is True and proof["status"] == "PASS_AUTHENTICATED_PRINTED_COMPARATIVE_FLOW_POLICY"
    assert proof["start_dates_inferred"] is False and proof["source_period_keys_modified"] is False
    assert _public_candidate(records)["status"] == READY
    assert records == before


@pytest.mark.parametrize("mutation", ["competing_title", "wrong_current_year", "missing_policy", "partial_split"])
def test_whole_primary_range_does_not_waive_other_period_or_comparative_authority(mutation):
    records = _whole_flow_range_records()
    section, table = _absolute_header_section_table(records)
    if mutation == "competing_title":
        table["title_exact"] = _whole_flow_range_caption(months=9)
    elif mutation == "wrong_current_year":
        section["title_exact"] = _whole_flow_range_caption(year=2026)
    elif mutation == "missing_policy":
        _policy_section(records)["narratives_exact"] = []
    else:
        section["title_exact"], table["title_exact"] = section["title_exact"].split(" đến ngày ")
        table["title_exact"] = "đến ngày " + table["title_exact"]
    before = deepcopy(records)
    proof = _period_proof(records)
    assert proof["complete"] is False and proof["status"] == "ALGORITHM_HOLD"
    candidate = _public_candidate(records)
    assert candidate["status"] == UNRESOLVED and candidate.get("mappings", []) == []
    assert records == before


@pytest.mark.parametrize("ownership", ["section", "each_table", "table1_only", "narrative_only"])
def test_whole_primary_range_multiple_tables_keep_source_local_ownership(ownership):
    records = _whole_flow_range_records(source_kind="TABLE_TITLE" if ownership != "section" else "SECTION_TITLE")
    section, table = _absolute_header_section_table(records, 2)
    section["tables"].append(deepcopy(table))
    if ownership == "table1_only":
        section["tables"][1]["title_exact"] = None
    elif ownership == "narrative_only":
        section["narratives_exact"] = [table["title_exact"]]
        for source_table in section["tables"]:
            source_table["title_exact"] = None
    before = deepcopy(records)
    inventory = family._document_statement_period_inventory(records, compiled_specs=_adapter_compiled())
    policy = inventory["document_comparative_flow_policy_receipt"]
    assert len(policy["anchor_source_receipts"]) == 3
    assert policy["complete"] is (ownership in {"section", "each_table"})
    if ownership in {"section", "each_table"}:
        assert all(anchor["complete"] for anchor in policy["anchor_source_receipts"])
    else:
        sibling = [source for source in inventory["sources"] if source["locator"]["table_id"] == "t2"]
        assert len(sibling) == 1 and sibling[0]["owned_current_period_constraints"] == []
        assert _period_proof(records, inventory=inventory)["complete"] is False
    assert records == before


@pytest.mark.parametrize("field,value", [("printed_start_date", "2025-02-01"), ("printed_end_date", "2025-09-30")])
def test_whole_primary_range_self_resealed_query_cannot_replace_original_caption(field, value):
    records = _whole_flow_range_records()
    before = deepcopy(records)
    compiled, cluster, query = _public_query(records)
    assert cluster["status"] == READY and query is not None
    forged = deepcopy(query)
    inventory = forged["source_context_receipt"]["document_statement_period_inventory"]
    constraint = inventory["sources"][0]["owned_current_period_constraints"][0]
    constraint[field] = value
    constraint["source_date_range_evidence"][field] = value
    _reseal_receipts(forged)
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error):
        _evaluate_query(records, compiled, cluster, forged)
    assert records == before



def _four_money_ytd_records(*, layout="seven", marker=False, ytd_tail=False):
    from test_gemini_json_income_tax_signed_display_v1 import _contextual_period_records

    records = _contextual_period_records(quarter="II", absolute_primary=True, include_cash_flow=False)
    section = records[1]["page_json"]["sections"][0]
    table = section["tables"][0]
    section["title_exact"] = _whole_flow_range_caption(year=2026)
    section["narratives_exact"] = []
    table["title_exact"] = None
    text_headers = ["STT", "Chỉ tiêu", "Thuyết\\nminh"] if layout == "seven" else ["STT", "Thuyết minh"]
    money = []
    for index in range(4):
        stem = "Quý II" if index < 2 else "Lũy kế từ đầu năm"
        if ytd_tail and index >= 2:
            stem += " đến cuối quý này"
        year = ("Năm " if marker else "") + ("2026" if index % 2 == 0 else "2025")
        # Match both authentic source shapes, not one synthetic normalized axis.
        path = [stem, year + "\\nTriệu VND"] if layout == "seven" else [stem, year, "Triệu VND"]
        money.append({"value_kind": "MONEY", "header_path_exact": path})
    table["columns"] = [{"value_kind": "TEXT", "header_path_exact": [label]} for label in text_headers] + money
    for row in table["rows"]:
        row["values_exact"] = [None] * len(text_headers) + row["values_exact"]
        assert len(row["values_exact"]) == len(table["columns"])
    return records


def _four_money_ytd_probe(records):
    section = records[1]["page_json"]["sections"][0]
    table = section["tables"][0]
    lane = family._multitable_lane_axis(section, table, compiled_specs=_adapter_compiled())
    return section, table, lane, family._printed_ytd_sibling_period_evidence(section, table, lane)


def _four_money_ytd_columns(table):
    return [column for column in table["columns"] if column["value_kind"] == "MONEY"]


@pytest.mark.parametrize("layout", ["seven", "six"])
@pytest.mark.parametrize("marker", [False, True, "mixed"])
@pytest.mark.parametrize("ytd_tail", [False, True])
def test_four_money_ytd_exact_numeric_headers_preserve_old_stem_and_actual_source_shapes(layout, marker, ytd_tail):
    records = _four_money_ytd_records(layout=layout, marker=marker is True, ytd_tail=ytd_tail)
    if marker == "mixed":
        columns = _four_money_ytd_columns(records[1]["page_json"]["sections"][0]["tables"][0])
        for index in (0, 3):
            columns[index]["header_path_exact"][1] = "Năm " + columns[index]["header_path_exact"][1]
    before = deepcopy(records)
    _section, table, lane, evidence = _four_money_ytd_probe(records)
    money = [4, 5, 6, 7] if layout == "seven" else [3, 4, 5, 6]
    assert lane["complete"] is True and lane["money_column_ordinals"] == money[2:]
    assert lane["excluded_parallel_duration_money_column_ordinals"] == money[:2]
    assert evidence is not None
    assert evidence["quarter"] == 2 and evidence["money_column_ordinals"] == money
    assert evidence["printed_absolute_year_tokens"] == ["2026", "2025"]
    assert evidence["relative_year_tokens"] is None
    assert evidence["intrinsic_absolute_periods"] == [["SOURCE_YTD_QUARTER", 2026, 2], ["SOURCE_YTD_QUARTER", 2025, 2]]
    assert evidence["original_table_json_sha256"] == canonical_json_sha256_v1(table)
    assert records == before


@pytest.mark.parametrize("layout", ["seven", "six"])
def test_four_money_ytd_old_literal_material_and_receipt_identity_remain_unchanged(layout):
    records = _four_money_ytd_records(layout=layout, marker=True, ytd_tail=True)
    _section, table, _lane, evidence = _four_money_ytd_probe(records)
    money = [4, 5, 6, 7] if layout == "seven" else [3, 4, 5, 6]
    expected = {
        "quarter": 2, "relative_year_tokens": None, "printed_absolute_year_tokens": ["2026", "2025"],
        "intrinsic_absolute_periods": [["SOURCE_YTD_QUARTER", 2026, 2], ["SOURCE_YTD_QUARTER", 2025, 2]],
        "money_column_ordinals": money,
        "quarter_columns_exact": [deepcopy(table["columns"][index - 1]) for index in money[:2]],
        "cumulative_columns_exact": [deepcopy(table["columns"][index - 1]) for index in money[2:]],
        "original_table_json_sha256": canonical_json_sha256_v1(table),
        "rule": "EXACT_FOUR_MONEY_PARALLEL_QUARTER_YTD_SOURCE_AXIS_MATCHED_YEAR_SUFFIXES_NO_AMOUNT_INFERENCE",
    }
    assert evidence == expected | {"receipt_id": "gjitfav1:printed-ytd-siblings:" + canonical_json_sha256_v1(expected)}


@pytest.mark.parametrize("quarter,number", [("I", 1), ("II", 2), ("III", 3), ("IV", 4), ("1", 1), ("2", 2), ("3", 3), ("4", 4)])
def test_four_money_ytd_explicit_quarter_and_nonadjacent_years_are_not_inferred(quarter, number):
    records = _four_money_ytd_records(layout="six")
    section = records[1]["page_json"]["sections"][0]
    section["title_exact"] = "Báo cáo kết quả hoạt động riêng"
    for column in _four_money_ytd_columns(section["tables"][0]):
        path = column["header_path_exact"]
        path[:] = [value.replace("Quý II", "Quý " + quarter).replace("2025", "2021") for value in path]
    _section, _table, _lane, evidence = _four_money_ytd_probe(records)
    assert evidence is not None and evidence["quarter"] == number
    expected = [["ANNUAL_YEAR", 2026], ["ANNUAL_YEAR", 2021]] if number == 4 else [
        ["SOURCE_YTD_QUARTER", 2026, number], ["SOURCE_YTD_QUARTER", 2021, number],
    ]
    assert evidence["intrinsic_absolute_periods"] == expected


@pytest.mark.parametrize("units", [
    ("", "", "", ""), ("Triệu VND", "", "Triệu VND", ""),
    ("Triệu đồng", "Triệu VND", "VND", "đồng"),
    ("VND", "VND", "", ""), ("", "", "đồng", "Triệu đồng"),
])
def test_four_money_ytd_known_currency_furniture_is_independent_not_unit_authority(units):
    records = _four_money_ytd_records(layout="six")
    table = records[1]["page_json"]["sections"][0]["tables"][0]
    for column, unit in zip(_four_money_ytd_columns(table), units, strict=True):
        column["header_path_exact"] = column["header_path_exact"][:2] + ([unit] if unit else [])
    before = deepcopy(records)
    _section, _table, _lane, evidence = _four_money_ytd_probe(records)
    assert evidence is not None
    assert evidence["intrinsic_absolute_periods"] == [["SOURCE_YTD_QUARTER", 2026, 2], ["SOURCE_YTD_QUARTER", 2025, 2]]
    assert not any("unit" in key or "scope" in key for key in evidence)
    assert records == before


@pytest.mark.parametrize("presentation", ["nfd", "uppercase", "whitespace", "actual_newline", "split_year_unit"])
def test_four_money_ytd_preserves_raw_layout_in_source_bound_receipt(presentation):
    records = _four_money_ytd_records()
    table = records[1]["page_json"]["sections"][0]["tables"][0]
    for column in _four_money_ytd_columns(table):
        path = column["header_path_exact"]
        if presentation == "nfd":
            path[:] = [unicodedata.normalize("NFD", value) for value in path]
        elif presentation == "uppercase":
            path[:] = [value.replace("\\n", "\n").upper() for value in path]
        elif presentation == "whitespace":
            path[:] = [" \t" + value.replace(" ", "\t") + "\r\n" for value in path]
        elif presentation == "actual_newline":
            path[:] = [value.replace("\\n", "\n") for value in path]
        else:
            path[:] = [path[0], *path[1].split("\\n")]
    before = deepcopy(records)
    _section, _table, _lane, evidence = _four_money_ytd_probe(records)
    assert evidence is not None
    assert evidence["quarter_columns_exact"] + evidence["cumulative_columns_exact"] == _four_money_ytd_columns(table)
    assert records == before


@pytest.mark.parametrize("layout", ["seven", "six"])
@pytest.mark.parametrize("ytd_tail", [False, True])
def test_four_money_ytd_relative_tokens_keep_literal_nam_and_no_absolute_year_permission(layout, ytd_tail):
    records = _four_money_ytd_records(layout=layout, marker=True, ytd_tail=ytd_tail)
    for column in _four_money_ytd_columns(records[1]["page_json"]["sections"][0]["tables"][0]):
        column["header_path_exact"] = [
            value.replace("2026", "nay").replace("2025", "trước") for value in column["header_path_exact"]
        ]
    before = deepcopy(records)
    _section, _table, _lane, evidence = _four_money_ytd_probe(records)
    assert evidence is not None and evidence["relative_year_tokens"] == ["nay", "truoc"]
    assert evidence["printed_absolute_year_tokens"] is None and evidence["intrinsic_absolute_periods"] is None
    assert records == before


@pytest.mark.parametrize("mutation", [
    "year_acute", "year_grave", "year_horn", "year_overlay", "year_circle", "year_superscript",
    "year_fullwidth", "year_arabic", "quarter_roman_acute", "quarter_roman_i_acute", "quarter_roman_i_grave",
    "quarter_roman_i_horn", "quarter_unicode_roman", "quarter_numeric_acute",
    "quarter_superscript", "quarter_unknown_suffix", "period_suffix", "footnote_suffix", "currency_unknown",
    "year_missing", "year_short", "year_zero", "year_duplicate", "year_reversed", "year_pair_mismatch",
    "quarter_pair_mismatch", "relative_bare", "relative_one_missing_nam", "mixed_relative", "relative_reversed",
    "extra_year", "wrong_ytd_stem",
])
def test_four_money_ytd_rejects_unprinted_or_annotated_periods_without_mutation(mutation):
    records = _four_money_ytd_records(layout="six")
    table = records[1]["page_json"]["sections"][0]["tables"][0]
    columns = _four_money_ytd_columns(table)
    replacements = {
        "year_acute": "2026\u0301", "year_grave": "202\u03006", "year_horn": "202\u031b6",
        "year_overlay": "2026\u0338", "year_circle": "2026\u20dd", "year_superscript": "202⁶",
        "year_fullwidth": "２０２６", "year_arabic": "٢٠٢٦", "year_missing": "", "year_short": "026", "year_zero": "0000",
    }
    if mutation in replacements:
        columns[0]["header_path_exact"][1] = replacements[mutation]
    elif mutation.startswith("quarter_"):
        columns[0]["header_path_exact"][0] = {
            "quarter_roman_acute": "Quý II\u0301", "quarter_numeric_acute": "Quý 2\u0301",
            "quarter_roman_i_acute": "Quý I\u0301", "quarter_roman_i_grave": "Quý I\u0300",
            "quarter_roman_i_horn": "Quý I\u031b", "quarter_unicode_roman": "Quý Ⅱ",
            "quarter_superscript": "Quý ²", "quarter_unknown_suffix": "Quý II (*)",
            "quarter_pair_mismatch": "Quý III",
        }[mutation]
        if mutation.startswith("quarter_roman_i_") or mutation == "quarter_unicode_roman":
            columns[1]["header_path_exact"][0] = columns[0]["header_path_exact"][0]
    elif mutation in {"period_suffix", "footnote_suffix", "extra_year"}:
        columns[2]["header_path_exact"].append({
            "period_suffix": ".", "footnote_suffix": "(*)", "extra_year": "2023",
        }[mutation])
    elif mutation == "currency_unknown":
        columns[3]["header_path_exact"][-1] = "USD"
    elif mutation == "year_duplicate":
        columns[1]["header_path_exact"][1] = "2026"
    elif mutation == "year_reversed":
        for column in columns:
            column["header_path_exact"][1] = "2025" if column["header_path_exact"][1] == "2026" else "2026"
    elif mutation == "year_pair_mismatch":
        columns[3]["header_path_exact"][1] = "2024"
    elif mutation.startswith("relative_"):
        for index, column in enumerate(columns):
            prefix = "" if mutation == "relative_bare" else "Năm "
            token = ("trước" if index % 2 == 0 else "nay") if mutation == "relative_reversed" else ("nay" if index % 2 == 0 else "trước")
            column["header_path_exact"][1] = prefix + token
        if mutation == "relative_one_missing_nam":
            columns[3]["header_path_exact"][1] = "trước"
    elif mutation == "mixed_relative":
        columns[2]["header_path_exact"][1] = "Năm nay"
        columns[3]["header_path_exact"][1] = "Năm trước"
    else:
        columns[2]["header_path_exact"][0] = "Lũy kế từ đầu kỳ"
    before = deepcopy(records)
    assert _four_money_ytd_probe(records)[3] is None
    assert records == before


@pytest.mark.parametrize("invalid", [None, [], (), ["Quý II", None], ["Quý II", 2026], ["Quý II", ""], ["Quý II", " "], ("Quý II", "2026")])
def test_four_money_ytd_malformed_raw_header_paths_are_not_coerced_or_padded(invalid):
    records = _four_money_ytd_records(layout="six")
    section = records[1]["page_json"]["sections"][0]
    table = section["tables"][0]
    lane = family._multitable_lane_axis(section, table, compiled_specs=_adapter_compiled())
    _four_money_ytd_columns(table)[0]["header_path_exact"] = deepcopy(invalid)
    before = deepcopy(table)
    assert family._printed_ytd_sibling_period_evidence(section, table, lane) is None
    assert table == before


@pytest.mark.parametrize("layout", ["seven", "six"])
def test_four_money_ytd_numeric_years_get_only_fresh_selected_header_census_permission(layout):
    records = _four_money_ytd_records(layout=layout)
    before = deepcopy(records)
    section, table, lane, evidence = _four_money_ytd_probe(records)
    assert evidence is not None
    periods = [["SOURCE_YTD_QUARTER", 2026, 2], ["SOURCE_YTD_QUARTER", 2025, 2]]
    surfaces, _ancestors, reasons = family._comparative_flow_local_surface_census(section, table, lane, periods)
    assert reasons == []
    headers = [item for item in surfaces if item["kind"] == "MONEY_HEADER"]
    assert headers and {item["column_ordinal"] for item in headers} == set(lane["money_column_ordinals"])
    assert all(item["reasons"] == [] for item in headers)
    for item in headers:
        bound = item["owned_ytd_sibling_header_evidence"]
        ordinal, token = item["column_ordinal"], item["ordinal"]
        selected = lane["money_column_ordinals"].index(ordinal)
        path = table["columns"][ordinal - 1]["header_path_exact"]
        assert bound["printed_ytd_sibling_receipt_id"] == evidence["receipt_id"]
        assert bound["column_ordinal"] == ordinal and bound["header_path_ordinal"] == token
        assert bound["source_path_exact"] == path and bound["source_exact"] == item["source_exact"] == path[token - 1]
        assert bound["source_sha256"] == sha256(item["source_exact"].encode("utf-8")).hexdigest()
        assert bound["independently_resolved_source_period"] == periods[selected]
        assert bound["printed_absolute_year"] == periods[selected][1]
        assert item["year_consumed_from_owned_header"] is (token == 2)
    assert family._absolute_source_duration_semantics(section, table, lane) == periods
    assert records == before


@pytest.mark.parametrize("surface", ["section_title", "table_title", "narrative", "ancestor", "group", "wrong_expected_year"])
def test_four_money_ytd_header_permission_cannot_erase_unowned_or_conflicting_year_assertions(surface):
    records = _four_money_ytd_records(layout="six")
    section, table, lane, evidence = _four_money_ytd_probe(records)
    assert evidence is not None
    periods = [["SOURCE_YTD_QUARTER", 2026, 2], ["SOURCE_YTD_QUARTER", 2025, 2]]
    if surface == "section_title":
        section["title_exact"] += " 2023"
    elif surface == "table_title":
        table["title_exact"] = "Năm 2023"
    elif surface == "narrative":
        section["narratives_exact"] = ["Cho kỳ hoạt động 6 tháng kết thúc ngày 30 tháng 6 năm 2023"]
    elif surface == "ancestor":
        table["rows"][0]["hierarchy_path_exact"] = ["Năm 2023", table["rows"][0]["label_exact"]]
    elif surface == "group":
        row = deepcopy(table["rows"][0])
        row.update(row_kind="GROUP", label_exact="Năm 2023", hierarchy_path_exact=["Năm 2023"],
                   values_exact=[None] * len(table["columns"]))
        table["rows"].insert(0, row)
    else:
        periods[0][1] = 2027
    before = deepcopy(records)
    _surfaces, _ancestors, reasons = family._comparative_flow_local_surface_census(section, table, lane, periods)
    assert reasons
    assert records == before


@pytest.mark.parametrize("layout", ["seven", "six"])
def test_four_money_ytd_public_numeric_window_uses_literal_note_without_cash_flow_or_policy(layout):
    records = _four_money_ytd_records(layout=layout)
    before = deepcopy(records)
    compiled = _adapter_compiled()
    section, table, lane, _evidence = _four_money_ytd_probe(records)
    assert len(records) == 2
    inventory = family._document_statement_period_inventory(records, compiled_specs=compiled)
    proof = family._source_period_correspondence_receipt(
        left_locator=_contextual_period_locator(records[0]), right_locator=_contextual_period_locator(records[1]),
        left_money_column_ordinals=[1, 2], right_money_column_ordinals=lane["money_column_ordinals"],
        page_records=records, compiled_specs=compiled, document_period_inventory=inventory,
    )
    assert proof["complete"] is True, proof["reasons"]
    assert proof["amounts_used_as_authority"] is False and proof["source_period_keys_modified"] is False
    assert family._absolute_source_duration_semantics(section, table, lane) == [
        ["SOURCE_YTD_QUARTER", 2026, 2], ["SOURCE_YTD_QUARTER", 2025, 2],
    ]
    assert all(item.get("cash_flow_used_as_period_authority") is False for item in proof["period_resolution_evidence"])
    candidate = _public_candidate(records)
    assert candidate["status"] == READY and candidate["mappings"], candidate["reasons"]
    assert records == before


@pytest.mark.parametrize("mutation", ["receipt_year", "source_year"])
def test_four_money_ytd_resealed_query_inventory_cannot_supply_missing_original_header_authority(mutation):
    records = _four_money_ytd_records(layout="six")
    compiled, cluster, query = _public_query(records)
    assert cluster["status"] == READY and query is not None
    forged = deepcopy(query)
    if mutation == "receipt_year":
        source = forged["source_context_receipt"]["document_statement_period_inventory"]["sources"][0]
        source["ytd_sibling_evidence"]["intrinsic_absolute_periods"][0][1] = 2023
        _reseal_receipts(forged)
    else:
        table = records[1]["page_json"]["sections"][0]["tables"][0]
        _four_money_ytd_columns(table)[2]["header_path_exact"][1] = "2023"
    before = deepcopy(records)
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error):
        _evaluate_query(records, compiled, cluster, forged)
    assert records == before



@pytest.mark.parametrize("layout", ["seven", "six"])
def test_four_money_ytd_zero_comparative_year_in_both_pairs_is_not_calendar_authority(layout):
    records = _four_money_ytd_records(layout=layout)
    table = records[1]["page_json"]["sections"][0]["tables"][0]
    for index in (1, 3):
        column = _four_money_ytd_columns(table)[index]
        column["header_path_exact"] = [value.replace("2025", "0000") for value in column["header_path_exact"]]
    before = deepcopy(records)
    assert _four_money_ytd_probe(records)[3] is None
    assert records == before


def test_four_money_ytd_period_permission_does_not_waive_public_mixed_scale_unit_gate():
    records = _four_money_ytd_records(layout="six")
    table = records[1]["page_json"]["sections"][0]["tables"][0]
    for index, column in enumerate(_four_money_ytd_columns(table)):
        column["header_path_exact"][-1] = "VND" if index % 2 == 0 else "Triệu VND"
    before = deepcopy(records)
    section, table, lane, evidence = _four_money_ytd_probe(records)
    assert evidence is not None
    expected = [["SOURCE_YTD_QUARTER", 2026, 2], ["SOURCE_YTD_QUARTER", 2025, 2]]
    assert family._absolute_source_duration_semantics(section, table, lane) == expected
    compiled = _adapter_compiled()
    inventory = family._document_statement_period_inventory(records, compiled_specs=compiled)
    proof = family._source_period_correspondence_receipt(
        left_locator=_contextual_period_locator(records[0]), right_locator=_contextual_period_locator(records[1]),
        left_money_column_ordinals=[1, 2], right_money_column_ordinals=lane["money_column_ordinals"],
        page_records=records, compiled_specs=compiled, document_period_inventory=inventory,
    )
    assert proof["complete"] is True, proof["reasons"]
    assert proof["amounts_used_as_authority"] is False
    candidate = _public_candidate(records)
    assert candidate["status"] == UNRESOLVED and candidate.get("mappings", []) == []
    assert records == before


@pytest.mark.parametrize("missing", ["all", "one_quarter", "one_ytd"])
def test_four_money_ytd_relative_missing_nam_cannot_borrow_complete_current_range_caption(missing):
    records = _four_money_ytd_records(layout="six", marker=True)
    table = records[1]["page_json"]["sections"][0]["tables"][0]
    for index, column in enumerate(_four_money_ytd_columns(table)):
        token = "nay" if index % 2 == 0 else "trước"
        omit = missing == "all" or (missing == "one_quarter" and index == 1) or (missing == "one_ytd" and index == 3)
        column["header_path_exact"][1] = ("" if omit else "Năm ") + token
    before = deepcopy(records)
    section, table, lane, evidence = _four_money_ytd_probe(records)
    assert evidence is None
    constraint = family._owned_flow_date_range_caption_constraint(
        section, source_kind="SECTION_TITLE", source_exact=section["title_exact"],
    )
    assert constraint is not None and constraint["supported"] is True
    assert family._absolute_source_duration_semantics(section, table, lane) is None
    candidate = _public_candidate(records)
    assert candidate["status"] == UNRESOLVED and candidate.get("mappings", []) == []
    assert records == before


@pytest.mark.parametrize("split", ["word_components", "stem_tail", "serialized_components"])
def test_four_money_ytd_census_binds_split_stem_tail_year_and_currency_without_global_stripping(split):
    records = _four_money_ytd_records(layout="six", ytd_tail=True)
    table = records[1]["page_json"]["sections"][0]["tables"][0]
    columns = _four_money_ytd_columns(table)
    for index in (2, 3):
        year = str(2026 if index == 2 else 2025)
        if split == "word_components":
            path = ["Lũy kế", "từ đầu năm", "đến cuối", "quý này", year, "Triệu", "VND"]
        elif split == "stem_tail":
            path = ["Lũy kế từ đầu năm", "đến cuối quý này", year, "Triệu VND"]
        else:
            path = ["Lũy kế\\ntừ đầu năm", "đến cuối\\nquý này", year + "\\nTriệu", "VND"]
        columns[index]["header_path_exact"] = path
    before = deepcopy(records)
    section, table, lane, evidence = _four_money_ytd_probe(records)
    assert evidence is not None
    periods = [["SOURCE_YTD_QUARTER", 2026, 2], ["SOURCE_YTD_QUARTER", 2025, 2]]
    surfaces, _ancestors, reasons = family._comparative_flow_local_surface_census(section, table, lane, periods)
    assert reasons == []
    for surface in (item for item in surfaces if item["kind"] == "MONEY_HEADER"):
        ordinal, token = surface["column_ordinal"], surface["ordinal"]
        source_path = table["columns"][ordinal - 1]["header_path_exact"]
        selected = lane["money_column_ordinals"].index(ordinal)
        binding = surface["owned_ytd_sibling_header_evidence"]
        assert binding["printed_ytd_sibling_receipt_id"] == evidence["receipt_id"]
        assert binding["source_path_exact"] == source_path
        assert binding["column_ordinal"] == ordinal and binding["header_path_ordinal"] == token
        assert binding["source_exact"] == surface["source_exact"] == source_path[token - 1]
        assert binding["source_sha256"] == sha256(surface["source_exact"].encode("utf-8")).hexdigest()
        assert binding["independently_resolved_source_period"] == periods[selected]
        has_year = bool(re.search(r"(?<!\S)[0-9]{4}(?!\S)", surface["source_exact"].replace("\\n", "\n")))
        assert surface["year_consumed_from_owned_header"] is has_year
    assert records == before


@pytest.mark.parametrize("mismatch", ["prior_year", "current_quarter", "prior_quarter", "annual_type"])
def test_four_money_ytd_census_requires_the_complete_expected_window_not_just_one_matching_year(mismatch):
    records = _four_money_ytd_records(layout="six")
    section, table, lane, evidence = _four_money_ytd_probe(records)
    assert evidence is not None
    periods = [["SOURCE_YTD_QUARTER", 2026, 2], ["SOURCE_YTD_QUARTER", 2025, 2]]
    affected = 1 if mismatch in {"prior_year", "prior_quarter"} else 0
    if mismatch == "prior_year":
        periods[1][1] = 2024
    elif mismatch == "current_quarter":
        periods[0][2] = 3
    elif mismatch == "prior_quarter":
        periods[1][2] = 3
    else:
        periods = [["ANNUAL_YEAR", 2026], ["ANNUAL_YEAR", 2025]]
    before = deepcopy(records)
    surfaces, _ancestors, reasons = family._comparative_flow_local_surface_census(section, table, lane, periods)
    assert reasons
    affected_headers = [item for item in surfaces if item["kind"] == "MONEY_HEADER"
                        and item["column_ordinal"] == lane["money_column_ordinals"][affected]]
    assert affected_headers
    assert all("owned_ytd_sibling_header_evidence" not in item for item in affected_headers)
    assert records == before



@pytest.mark.parametrize("pair", ["duplicate", "reversed"])
def test_four_money_ytd_relative_census_cannot_bind_duplicate_or_reversed_expected_years(pair):
    records = _four_money_ytd_records(layout="six", marker=True)
    table = records[1]["page_json"]["sections"][0]["tables"][0]
    for index, column in enumerate(_four_money_ytd_columns(table)):
        column["header_path_exact"][1] = "Năm " + ("nay" if index % 2 == 0 else "trước")
    before = deepcopy(records)
    section, table, lane, evidence = _four_money_ytd_probe(records)
    assert evidence is not None and evidence["intrinsic_absolute_periods"] is None
    valid = [["SOURCE_YTD_QUARTER", 2026, 2], ["SOURCE_YTD_QUARTER", 2025, 2]]
    valid_surfaces, _ancestors, valid_reasons = family._comparative_flow_local_surface_census(section, table, lane, valid)
    assert valid_reasons == []
    valid_headers = [item for item in valid_surfaces if item["kind"] == "MONEY_HEADER"]
    assert valid_headers and all("owned_ytd_sibling_header_evidence" in item for item in valid_headers)
    assert all(item["owned_ytd_sibling_header_evidence"]["printed_absolute_year"] is None for item in valid_headers)
    assert all(item["year_consumed_from_owned_header"] is False for item in valid_headers)
    invalid = deepcopy(valid)
    if pair == "duplicate":
        invalid[1][1] = invalid[0][1]
    else:
        invalid.reverse()
    surfaces, _ancestors, _reasons = family._comparative_flow_local_surface_census(section, table, lane, invalid)
    assert all("owned_ytd_sibling_header_evidence" not in item for item in surfaces)
    assert records == before



@pytest.mark.parametrize("conflict", ["quarter_only", "ytd_only", "table_vs_headers", "same_surface"])
def test_four_money_ytd_invalid_primary_units_are_authenticated_before_note_only_fallback(conflict):
    records = _four_money_ytd_records(layout="six")
    section = records[1]["page_json"]["sections"][0]
    table = section["tables"][0]
    columns = _four_money_ytd_columns(table)
    if conflict == "quarter_only":
        for index in (0, 1):
            columns[index]["header_path_exact"][-1] = "VND"
    elif conflict == "ytd_only":
        for index in (2, 3):
            columns[index]["header_path_exact"][-1] = "VND"
    elif conflict == "table_vs_headers":
        for column in columns:
            column["header_path_exact"][-1] = "VND"
    else:
        columns[2]["header_path_exact"][-1] = "Triệu VND / Đồng"
    before = deepcopy(records)
    compiled = _adapter_compiled()
    actual_unit = family._unit_axis(table, compiled_specs=compiled)
    assert actual_unit["complete"] is False
    expected_conflict = ("MULTIPLE_CONFLICTING_DECLARED_MONEY_UNITS_ON_ONE_SURFACE"
                         if conflict == "same_surface" else "CONFLICTING_EXPLICIT_MONEY_UNITS")
    assert expected_conflict in actual_unit["reasons"]
    invalid = family._primary_invalid_source_role_rows(records, compiled_specs=compiled)
    assert invalid
    for row in invalid:
        assert "INVALID_PRIMARY_SOURCE_MONEY_UNIT_CONFLICT" in row["reasons"]
        assert row["source_unit_axis"] == actual_unit
        assert row["locator"] == _contextual_period_locator(records[1])
        assert row["table_json_sha256"] == canonical_json_sha256_v1(table)
    selected, reasons = family._select_primary_presentation(records, compiled_specs=compiled)
    assert selected is None and "INVALID_PRIMARY_INCOME_TAX_SOURCE_MONEY_UNIT" in reasons
    conflict_receipt = family._primary_selection_conflict_receipt(
        records, reasons=reasons, repair_receipts=[], compiled_specs=compiled,
    )
    assert conflict_receipt["invalid_source_rows"] == invalid
    material = {key: value for key, value in conflict_receipt.items() if key != "receipt_id"}
    assert conflict_receipt["receipt_id"] == "gjitfav1:primary-conflict:" + canonical_json_sha256_v1(material)
    candidate = _public_candidate(records)
    assert candidate["status"] == UNRESOLVED and candidate.get("mappings", []) == []
    assert "INVALID_PRIMARY_INCOME_TAX_SOURCE_MONEY_UNIT" in candidate["reasons"]
    assert records == before


@pytest.mark.parametrize("unit", ["Triệu VND", "VND"])
def test_four_money_ytd_uniform_explicit_primary_and_note_units_remain_publicly_usable(unit):
    records = _four_money_ytd_records(layout="six")
    for record in records:
        for section in record["page_json"]["sections"]:
            for table in section["tables"]:
                table["unit_exact"] = unit
                for column in table["columns"]:
                    if column["value_kind"] == "MONEY":
                        column["header_path_exact"] = [
                            value.replace("Triệu VND", unit).replace("Triệu đồng", unit)
                            for value in column["header_path_exact"]
                        ]
    before = deepcopy(records)
    compiled = _adapter_compiled()
    table = records[1]["page_json"]["sections"][0]["tables"][0]
    actual_unit = family._unit_axis(table, compiled_specs=compiled)
    assert actual_unit["complete"] is True and actual_unit["reasons"] == []
    assert actual_unit["canonical_unit"] == ("VND" if unit == "VND" else "MILLION_VND")
    assert family._primary_invalid_source_role_rows(records, compiled_specs=compiled) == []
    candidate = _public_candidate(records)
    assert candidate["status"] == READY and candidate["mappings"], candidate["reasons"]
    assert records == before


def test_original_note_adapter_retains_existing_invalid_primary_unit_evidence_instead_of_optional_primary():
    from test_gemini_json_income_tax_family_v1 import (
        _evaluate_original_note_production,
        _original_note_production_records,
    )

    records = _original_note_production_records()
    table = records[-1]["page_json"]["sections"][0]["tables"][0]
    assert len(table["columns"]) == 2 and all(column["value_kind"] == "MONEY" for column in table["columns"])
    table["columns"][0]["header_path_exact"].append("VND")
    table["columns"][1]["header_path_exact"].append("Triệu VND")
    before = deepcopy(records)
    compiled = _adapter_compiled()
    actual_unit = family._unit_axis(table, compiled_specs=compiled)
    assert actual_unit["complete"] is False
    assert actual_unit["reasons"] == ["MULTIPLE_CONFLICTING_DECLARED_MONEY_UNITS_ON_ONE_SURFACE"]
    cluster, query, candidate = _evaluate_original_note_production(records, compiled=compiled)
    assert cluster["status"] == READY  # Authenticated query carrier, not accepted semantics.
    adapter = query["adapter_receipt"]
    assert adapter["adapter_format_version"] == "GEMINI_JSON_INCOME_TAX_ORIGINAL_NOTE_ADAPTER_V1"
    assert adapter["primary_projection_receipt"] is None
    assert "INVALID_PRIMARY_INCOME_TAX_SOURCE_MONEY_UNIT" in adapter["primary_selection_reasons"]
    conflict = adapter["primary_selection_conflict_receipt"]
    invalid = family._primary_invalid_source_role_rows(records, compiled_specs=compiled)
    assert conflict["invalid_source_rows"] == invalid and invalid
    assert all(item["source_unit_axis"] == actual_unit
               and item["table_json_sha256"] == canonical_json_sha256_v1(table)
               and item["locator"] == _contextual_period_locator(records[-1]) for item in invalid)
    assert candidate["status"] == UNRESOLVED and candidate["mappings"] == []
    assert "INVALID_PRIMARY_INCOME_TAX_SOURCE_MONEY_UNIT" in candidate["reasons"]
    assert candidate["closure_receipt"]["original_note_adapter_receipt"]["primary_selection_conflict_receipt"] == conflict
    assert records == before



def test_explicit_primary_unit_conflict_with_incomplete_lane_retains_all_raw_source_evidence():
    records = _four_money_ytd_records(layout="six")
    section = records[1]["page_json"]["sections"][0]
    table = section["tables"][0]
    for index, column in enumerate(_four_money_ytd_columns(table)):
        column["header_path_exact"] = ["Chưa xác định kỳ", "VND" if index % 2 == 0 else "Triệu VND"]
    before = deepcopy(records)
    compiled = _adapter_compiled()
    lane = family._multitable_lane_axis(section, table, compiled_specs=compiled)
    assert lane["complete"] is False
    unit = family._unit_axis(table, compiled_specs=compiled)
    assert unit["complete"] is False and "CONFLICTING_EXPLICIT_MONEY_UNITS" in unit["reasons"]
    invalid = family._primary_invalid_source_role_rows(records, compiled_specs=compiled)
    assert invalid
    expected_columns = [{"column_ordinal": ordinal, "source_column_exact": column}
                        for ordinal, column in enumerate(table["columns"], 1) if column["value_kind"] == "MONEY"]
    for item in invalid:
        assert "INVALID_PRIMARY_SOURCE_MONEY_UNIT_CONFLICT" in item["reasons"]
        assert item["source_unit_axis"] == unit and item["source_lane_axis"] == lane
        assert item["source_row_exact"] == table["rows"][item["row_ordinal"] - 1]
        assert item["source_money_columns_exact"] == expected_columns
        assert item["source_values_exact"] == []
        assert item["locator"] == _contextual_period_locator(records[1])
        assert item["table_json_sha256"] == canonical_json_sha256_v1(table)
    candidate = _public_candidate(records)
    assert candidate["status"] == UNRESOLVED and candidate.get("mappings", []) == []
    assert "INVALID_PRIMARY_INCOME_TAX_SOURCE_MONEY_UNIT" in candidate["reasons"]
    assert records == before


def test_original_note_resealed_primary_unit_conflict_receipt_cannot_change_original_unit_evidence():
    from test_gemini_json_income_tax_family_v1 import (
        _evaluate_original_note_production,
        _original_note_production_records,
    )

    records = _original_note_production_records()
    table = records[-1]["page_json"]["sections"][0]["tables"][0]
    table["columns"][0]["header_path_exact"].append("VND")
    table["columns"][1]["header_path_exact"].append("Triệu VND")
    before = deepcopy(records)
    compiled = _adapter_compiled()
    cluster, query, candidate = _evaluate_original_note_production(records, compiled=compiled)
    assert candidate["status"] == UNRESOLVED and candidate["mappings"] == []
    forged = deepcopy(query)
    conflict = forged["adapter_receipt"]["primary_selection_conflict_receipt"]
    assert conflict["invalid_source_rows"]
    conflict["invalid_source_rows"][0]["source_unit_axis"]["complete"] = True
    conflict["invalid_source_rows"][0]["source_unit_axis"]["reasons"] = []
    _reseal_receipts(forged)
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error):
        _evaluate_query(records, compiled, cluster, forged)
    assert records == before



def _assert_four_ytd_whitespace_census_bound(records, *, relative):
    section, table, lane, evidence = _four_money_ytd_probe(records)
    assert evidence is not None
    periods = [["SOURCE_YTD_QUARTER", 2026, 2], ["SOURCE_YTD_QUARTER", 2025, 2]]
    surfaces, _ancestors, reasons = family._comparative_flow_local_surface_census(section, table, lane, periods)
    assert reasons == []
    headers = [item for item in surfaces if item["kind"] == "MONEY_HEADER"]
    assert headers
    for surface in headers:
        ordinal, token = surface["column_ordinal"], surface["ordinal"]
        selected = lane["money_column_ordinals"].index(ordinal)
        path = table["columns"][ordinal - 1]["header_path_exact"]
        binding = surface["owned_ytd_sibling_header_evidence"]
        assert binding["printed_ytd_sibling_receipt_id"] == evidence["receipt_id"]
        assert binding["column_ordinal"] == ordinal and binding["header_path_ordinal"] == token
        assert binding["source_path_exact"] == path
        assert binding["source_exact"] == surface["source_exact"] == path[token - 1]
        assert binding["source_sha256"] == sha256(surface["source_exact"].encode("utf-8")).hexdigest()
        assert binding["independently_resolved_source_period"] == periods[selected]
        assert binding["printed_absolute_year"] == (None if relative else periods[selected][1])
        has_numeric_year = bool(re.search(r"(?<!\S)[0-9]{4}(?!\S)", surface["source_exact"].replace("\\n", "\n")))
        assert surface["year_consumed_from_owned_header"] is (not relative and has_numeric_year)
    return table, evidence


@pytest.mark.parametrize("space,layout", [
    ("\u00a0", "seven"), ("\u202f", "six"), ("\u2003", "seven"),
    ("\u2002", "six"), ("\u2009", "seven"), ("\u2028", "six"),
], ids=["nbsp_serialized", "narrow_nbsp_split", "em_space_serialized", "en_space_split", "thin_space_serialized", "line_separator_split"])
@pytest.mark.parametrize("marker", [False, True], ids=["bare_numeric", "literal_nam_numeric"])
def test_four_money_ytd_printed_unicode_whitespace_keeps_numeric_source_and_legacy_material(space, layout, marker):
    records = _four_money_ytd_records(layout=layout, marker=marker, ytd_tail=True)
    table = records[1]["page_json"]["sections"][0]["tables"][0]
    for column in _four_money_ytd_columns(table):
        column["header_path_exact"] = [value.replace(" ", space) for value in column["header_path_exact"]]
    before = deepcopy(records)
    table, evidence = _assert_four_ytd_whitespace_census_bound(records, relative=False)
    money = [4, 5, 6, 7] if layout == "seven" else [3, 4, 5, 6]
    # Exact legacy receipt material, including ORIGINAL Unicode whitespace,
    # remains unchanged. Layout recognition grants no unit/scope/value power.
    expected = {
        "quarter": 2, "relative_year_tokens": None, "printed_absolute_year_tokens": ["2026", "2025"],
        "intrinsic_absolute_periods": [["SOURCE_YTD_QUARTER", 2026, 2], ["SOURCE_YTD_QUARTER", 2025, 2]],
        "money_column_ordinals": money,
        "quarter_columns_exact": [deepcopy(table["columns"][index - 1]) for index in money[:2]],
        "cumulative_columns_exact": [deepcopy(table["columns"][index - 1]) for index in money[2:]],
        "original_table_json_sha256": canonical_json_sha256_v1(table),
        "rule": "EXACT_FOUR_MONEY_PARALLEL_QUARTER_YTD_SOURCE_AXIS_MATCHED_YEAR_SUFFIXES_NO_AMOUNT_INFERENCE",
    }
    assert evidence == expected | {"receipt_id": "gjitfav1:printed-ytd-siblings:" + canonical_json_sha256_v1(expected)}
    assert records == before


@pytest.mark.parametrize("space,layout", [
    ("\u00a0", "seven"), ("\u202f", "six"), ("\u2003", "seven"),
    ("\u2002", "six"), ("\u2009", "seven"), ("\u2028", "six"),
], ids=["nbsp_serialized", "narrow_nbsp_split", "em_space_serialized", "en_space_split", "thin_space_serialized", "line_separator_split"])
def test_four_money_ytd_unicode_whitespace_cannot_invent_absolute_years_for_literal_relative_headers(space, layout):
    records = _four_money_ytd_records(layout=layout, marker=True, ytd_tail=True)
    table = records[1]["page_json"]["sections"][0]["tables"][0]
    for index, column in enumerate(_four_money_ytd_columns(table)):
        path = [value.replace("2026", "nay").replace("2025", "trước") for value in column["header_path_exact"]]
        if layout == "six" and index >= 2:
            path = ["Lũy kế", "từ đầu năm", "đến cuối", "quý này", path[1], path[2]]
        column["header_path_exact"] = [value.replace(" ", space) for value in path]
    before = deepcopy(records)
    _table, evidence = _assert_four_ytd_whitespace_census_bound(records, relative=True)
    assert evidence["relative_year_tokens"] == ["nay", "truoc"]
    assert evidence["printed_absolute_year_tokens"] is None and evidence["intrinsic_absolute_periods"] is None
    assert records == before


@pytest.mark.parametrize("annotation", [
    "zero_width_space", "word_joiner", "bom", "roman_acute", "year_grave", "year_horn",
    "split_ascii_year", "split_roman_quarter",
])
def test_four_money_ytd_whitespace_compatibility_never_erases_annotations_or_joins_period_digits(annotation):
    records = _four_money_ytd_records(layout="six")
    table = records[1]["page_json"]["sections"][0]["tables"][0]
    columns = _four_money_ytd_columns(table)
    for column in columns:
        column["header_path_exact"] = [value.replace(" ", "\u00a0") for value in column["header_path_exact"]]
    unknown = {"zero_width_space": "\u200b", "word_joiner": "\u2060", "bom": "\ufeff"}
    if annotation in unknown:
        columns[0]["header_path_exact"][0] += unknown[annotation]
    elif annotation == "roman_acute":
        for index in (0, 1):
            columns[index]["header_path_exact"][0] = "Quý\u00a0II\u0301"
    elif annotation in {"year_grave", "year_horn"}:
        mark = "\u0300" if annotation == "year_grave" else "\u031b"
        for index in (0, 2):
            columns[index]["header_path_exact"][1] = "2026" + mark
    elif annotation == "split_ascii_year":
        for index in (0, 2):
            columns[index]["header_path_exact"][1] = "20\u00a026"
    else:
        for index in (0, 1):
            columns[index]["header_path_exact"][0] = "Quý\u00a0I\u00a0I"
    before = deepcopy(records)
    section, table, lane, evidence = _four_money_ytd_probe(records)
    assert evidence is None
    periods = [["SOURCE_YTD_QUARTER", 2026, 2], ["SOURCE_YTD_QUARTER", 2025, 2]]
    surfaces, _ancestors, _reasons = family._comparative_flow_local_surface_census(section, table, lane, periods)
    assert all("owned_ytd_sibling_header_evidence" not in item for item in surfaces)
    assert records == before



@pytest.mark.parametrize("relative", [False, True], ids=["numeric", "literal_relative"])
def test_four_money_ytd_complete_ascii_tail_is_header_furniture_not_a_second_date_range(relative):
    records = _four_money_ytd_records(layout="six", marker=relative, ytd_tail=True)
    table = records[1]["page_json"]["sections"][0]["tables"][0]
    if relative:
        for column in _four_money_ytd_columns(table):
            column["header_path_exact"] = [
                value.replace("2026", "nay").replace("2025", "trước") for value in column["header_path_exact"]
            ]
    before = deepcopy(records)
    _table, evidence = _assert_four_ytd_whitespace_census_bound(records, relative=relative)
    assert evidence["quarter"] == 2
    expected = None if relative else [["SOURCE_YTD_QUARTER", 2026, 2], ["SOURCE_YTD_QUARTER", 2025, 2]]
    assert evidence["intrinsic_absolute_periods"] == expected
    assert records == before


def _quarter_endpoint_absolute_policy_records(*, layout="slash"):
    records = _absolute_flow_header_records()
    _policy_section(records)["narratives_exact"] = [_audited_written_six_policy(prior_year=2023)]
    for index in (1, 2):
        section, table = _absolute_header_section_table(records, index)
        section["title_exact"] += "\nQuý II năm 2025"
        if layout == "four_money":
            columns = []
            for stem in ("Quý II", "Lũy kế từ đầu năm"):
                columns.extend({"value_kind": "MONEY", "header_path_exact": [stem, str(year), "Triệu đồng"]}
                               for year in (2025, 2023))
            table["columns"] = columns
            for row in table["rows"]:
                # Synthetic parallel-quarter positions are retained, never
                # used to establish calendar or selected-YTD authority.
                row["values_exact"] = [*row["values_exact"], *row["values_exact"]]
        else:
            for column, year in zip(table["columns"], (2025, 2023), strict=True):
                if layout == "date_range":
                    column["header_path_exact"] = [f"Từ ngày 01/01/{year} đến ngày 30/06/{year}", "Triệu đồng"]
                else:
                    separator = "." if layout == "dotted" else "/"
                    column["header_path_exact"] = ["Kỳ 6 tháng kết thúc ngày", f"30{separator}6{separator}{year}", "Triệu đồng"]
    return records


def _quarter_endpoint_selected_policy_proof(records, inventory, compiled):
    left_section, left_table = _absolute_header_section_table(records, 0)
    right_section, right_table = _absolute_header_section_table(records, 1)
    left_lane = family._multitable_lane_axis(left_section, left_table, compiled_specs=compiled)
    right_lane = family._multitable_lane_axis(right_section, right_table, compiled_specs=compiled)
    return family._source_period_correspondence_receipt(
        left_locator=_contextual_period_locator(records[0]), right_locator=_contextual_period_locator(records[1]),
        left_money_column_ordinals=left_lane["money_column_ordinals"],
        right_money_column_ordinals=right_lane["money_column_ordinals"],
        page_records=records, compiled_specs=compiled, document_period_inventory=inventory,
    )


@pytest.mark.parametrize("layout", ["slash", "dotted", "date_range", "four_money"])
def test_report_quarter_endpoint_requires_fresh_same_table_absolute_duration_with_printed_nonadjacent_policy(layout):
    records = _quarter_endpoint_absolute_policy_records(layout=layout)
    before = deepcopy(records)
    compiled = _adapter_compiled()
    inventory = family._document_statement_period_inventory(records, compiled_specs=compiled)
    expected = [["SOURCE_YTD_QUARTER", 2025, 2], ["SOURCE_YTD_QUARTER", 2023, 2]]
    policy = inventory["document_comparative_flow_policy_receipt"]
    assert policy["complete"] is True and policy["resolved_source_duration_semantics"] == expected
    assert {item["statement_type"] for item in policy["anchor_source_receipts"]} == {"INCOME_STATEMENT", "CASH_FLOW"}
    for anchor in policy["anchor_source_receipts"]:
        assert anchor["complete"] is True and anchor["reasons"] == []
        assert anchor["owned_current_duration"] == {"printed_months": 6, "printed_end_date": "2025-06-30"}
        evidence = anchor["quarter_caption_absolute_header_duration_evidence"]
        assert evidence is not None
        assert evidence["resolved_source_duration_semantics"] == expected
        assert evidence["money_column_ordinals"] == ([3, 4] if layout == "four_money" else [1, 2])
        assert evidence["columns_exact"] == anchor["columns_exact"]
        assert evidence["relative_year_inference_used"] is False
        if layout == "four_money":
            assert evidence["intrinsic_absolute_sibling_evidence"]["intrinsic_absolute_periods"] == expected
        else:
            assert evidence["intrinsic_absolute_sibling_evidence"] is None
            assert all(key[0] == ("DURATION_DATE_RANGE" if layout == "date_range" else "DURATION_END_DATE")
                       for key in evidence["source_lane_keys"])
    selected = _quarter_endpoint_selected_policy_proof(records, inventory, compiled)
    assert selected["complete"] is True
    assert selected["status"] == "PASS_AUTHENTICATED_PRINTED_COMPARATIVE_FLOW_POLICY"
    inherited = [item["inherited_document_comparative_flow_policy_receipt"] for item in selected["period_resolution_evidence"]
                 if item["inherited_document_comparative_flow_policy_receipt"] is not None]
    assert inherited and all(item["resolved_source_duration_semantics"] == expected for item in inherited)
    candidate = _public_candidate(records)
    assert candidate["status"] == READY and candidate["mappings"]
    assert records == before


@pytest.mark.parametrize("mutation", [
    "relative_two", "relative_four", "wrong_year", "three_months_june", "start_april", "start_jan2",
    "malformed_prior", "continuation_relative", "continuation_conflict", "continuation_prior_conflict",
])
def test_report_quarter_endpoint_cannot_invent_or_select_away_independent_absolute_duration(mutation):
    records = _quarter_endpoint_absolute_policy_records(layout="four_money" if mutation == "relative_four" else "slash")
    section, table = _absolute_header_section_table(records, 2)
    if mutation == "relative_two":
        for column, label in zip(table["columns"], ("Kỳ này", "Kỳ trước"), strict=True):
            column["header_path_exact"] = [label, "Triệu đồng"]
    elif mutation == "relative_four":
        for ordinal, column in enumerate(table["columns"]):
            column["header_path_exact"][1] = "Năm " + ("nay" if ordinal % 2 == 0 else "trước")
    elif mutation == "wrong_year":
        table["columns"][0]["header_path_exact"][1] = "30/6/2024"
    elif mutation == "three_months_june":
        for column in table["columns"]:
            column["header_path_exact"][0] = "Kỳ 3 tháng kết thúc ngày"
    elif mutation in {"start_april", "start_jan2"}:
        start = "01/04" if mutation == "start_april" else "02/01"
        for column, year in zip(table["columns"], (2025, 2023), strict=True):
            column["header_path_exact"] = [f"Từ ngày {start}/{year} đến ngày 30/06/{year}", "Triệu đồng"]
    elif mutation == "malformed_prior":
        table["columns"][1]["header_path_exact"][1] = "31/6/2023"
    else:
        section = _append_flow_continuation(records, 2)
        table = section["tables"][0]
        if mutation == "continuation_relative":
            for column, label in zip(table["columns"], ("Kỳ này", "Kỳ trước"), strict=True):
                column["header_path_exact"] = [label, "Triệu đồng"]
        elif mutation == "continuation_conflict":
            section["title_exact"] = section["title_exact"].replace("Quý II", "Quý III")
        else:
            table["columns"][1]["header_path_exact"][1] = "30/6/2024"
    before = deepcopy(records)
    compiled = _adapter_compiled()
    inventory = family._document_statement_period_inventory(records, compiled_specs=compiled)
    policy = inventory["document_comparative_flow_policy_receipt"]
    assert policy["complete"] is False and policy["status"] == "ALGORITHM_HOLD"
    assert policy["reasons"]
    assert any(anchor["complete"] is False for anchor in policy["anchor_source_receipts"])
    selected = _quarter_endpoint_selected_policy_proof(records, inventory, compiled)
    assert selected["complete"] is False and selected["status"] == "ALGORITHM_HOLD"
    candidate = _public_candidate(records)
    assert candidate["status"] == UNRESOLVED and candidate.get("mappings", []) == []
    assert records == before


@pytest.mark.parametrize("gate", [
    "scope", "unit", "rejected_header", "billion_table", "unknown_million_vnd", "unknown_thousand_million",
])
def test_quarter_caption_absolute_duration_composition_cannot_grant_scope_or_unit_acceptance(gate):
    records = _quarter_endpoint_absolute_policy_records()
    section, table = _absolute_header_section_table(records, 1)
    if gate == "scope":
        section["title_exact"] = section["title_exact"].replace("RIÊNG", "HỢP NHẤT")
    elif gate == "rejected_header":
        table["unit_exact"] = "Triệu đồng"
        for column in table["columns"]:
            column["header_path_exact"][-1] = "Nghìn đồng"
    elif gate == "billion_table":
        table["unit_exact"] = "Tỷ đồng"
    elif gate.startswith("unknown_"):
        table["unit_exact"] = "Triệu đồng" if gate == "unknown_million_vnd" else "Nghìn đồng"
        for column in table["columns"]:
            column["value_kind"] = "UNKNOWN"
            column["header_path_exact"][-1] = "Đồng" if gate == "unknown_million_vnd" else "Triệu đồng"
    else:
        table["unit_exact"] = "Nghìn đồng"
    before = deepcopy(records)
    if gate != "scope":
        compiled = _adapter_compiled()
        unknown = gate.startswith("unknown_")
        if unknown:
            assert "UNKNOWN" in compiled["accepted_value_column_kinds"]
            unit_view = {**table, "columns": [{**column, "value_kind": "MONEY"} for column in table["columns"]]}
            unit = {
                **family._unit_axis(unit_view, compiled_specs=compiled),
                "veto_only_unknown_column_unit_view": {
                    "column_ordinals": list(range(1, len(table["columns"]) + 1)),
                    "source_column_kinds_modified": False,
                    "positive_unit_permission_granted": False,
                },
            }
        else:
            unit = family._unit_axis(table, compiled_specs=compiled)
        identities = {(item["canonical_unit"], item["magnitude_power10"]) for item in unit["evidence"]}
        assert len(identities) > 1 and unit["complete"] is False
        if gate == "unknown_million_vnd":
            assert all(item["accepted"] is True for item in unit["evidence"])
        else:
            assert any(item["accepted"] is False for item in unit["evidence"])
        assert any(item["accepted"] is True for item in unit["evidence"])
        assert ("MILLION_VND", 6) in identities
        expected_other = ("BILLION_VND", 9) if gate == "billion_table" else (
            ("VND", 0) if gate == "unknown_million_vnd" else ("THOUSAND_VND", 3)
        )
        assert expected_other in identities
        invalid = family._primary_invalid_source_role_rows(records, compiled_specs=compiled)
        assert invalid
        raw_columns = [{"column_ordinal": ordinal, "source_column_exact": column}
                       for ordinal, column in enumerate(table["columns"], 1)
                       if column["value_kind"] in compiled["accepted_value_column_kinds"]]
        for item in invalid:
            assert item["locator"]["page_json_version_id"] == records[1]["page_json_version_id"]
            assert item["source_unit_axis"] == unit
            assert item["source_money_columns_exact"] == raw_columns
            assert item["source_row_exact"] == table["rows"][item["row_ordinal"] - 1]
            assert item["source_lane_axis"] == family._multitable_lane_axis(section, table, compiled_specs=compiled)
            assert "INVALID_PRIMARY_SOURCE_MONEY_UNIT_CONFLICT" in item["reasons"]
        if unknown:
            assert [column["value_kind"] for column in table["columns"]] == ["UNKNOWN", "UNKNOWN"]
    candidate = _public_candidate(records)
    assert candidate["status"] == UNRESOLVED and candidate.get("mappings", []) == []
    assert records == before


@pytest.mark.parametrize("forged", [None, [["SOURCE_YTD_QUARTER", 2025, 2], ["SOURCE_YTD_QUARTER", 2022, 2]]])
def test_quarter_caption_policy_builder_rejects_reserialized_forged_absolute_derived_field(forged):
    records = _quarter_endpoint_absolute_policy_records()
    before = deepcopy(records)
    compiled = _adapter_compiled()
    inventory = family._document_statement_period_inventory(records, compiled_specs=compiled)
    sources = deepcopy(inventory["sources"])
    original_source_sha = canonical_json_sha256_v1(sources[0])
    sources[0]["absolute_duration_semantics"] = deepcopy(forged)
    sources = json.loads(json.dumps(sources, ensure_ascii=False, allow_nan=False))
    assert canonical_json_sha256_v1(sources[0]) != original_source_sha
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error,
                       match="^income-tax quarter-caption absolute header duration source replay drifted$"):
        family._document_comparative_flow_policy_receipt(
            records, sources, family._document_report_scope_receipt(records), compiled_specs=compiled,
        )
    assert records == before


@pytest.mark.parametrize("conflict", [False, True])
def test_primary_unknown_unit_view_only_vetoes_actual_mixed_units_without_promoting_source(conflict):
    records = _quarter_endpoint_absolute_policy_records()
    _, table = _absolute_header_section_table(records, 1)
    for column in table["columns"]:
        column["value_kind"] = "UNKNOWN"
    table["unit_exact"] = "Nghìn đồng" if conflict else "Triệu đồng"
    before = deepcopy(records)
    compiled = _adapter_compiled()
    assert "UNKNOWN" in compiled["accepted_value_column_kinds"]
    invalid = family._primary_invalid_source_role_rows(records, compiled_specs=compiled)
    if conflict:
        assert invalid
        raw_columns = [{"column_ordinal": ordinal, "source_column_exact": column}
                       for ordinal, column in enumerate(table["columns"], 1)]
        for item in invalid:
            assert item["locator"]["page_json_version_id"] == records[1]["page_json_version_id"]
            assert "INVALID_PRIMARY_SOURCE_MONEY_UNIT_CONFLICT" in item["reasons"]
            assert item["source_money_columns_exact"] == raw_columns
            assert all(column["source_column_exact"]["value_kind"] == "UNKNOWN" for column in raw_columns)
            assert item["table_json_sha256"] == canonical_json_sha256_v1(table)
            unit = item["source_unit_axis"]
            assert {(evidence["canonical_unit"], evidence["magnitude_power10"])
                    for evidence in unit["evidence"]} == {("MILLION_VND", 6), ("THOUSAND_VND", 3)}
            assert unit["veto_only_unknown_column_unit_view"] == {
                "column_ordinals": [1, 2], "source_column_kinds_modified": False,
                "positive_unit_permission_granted": False,
            }
    else:
        assert invalid == []
    assert records == before


def test_quarter_caption_policy_builder_cannot_reseal_a_forged_dated_lane_over_relative_four_money_headers():
    records = _quarter_endpoint_absolute_policy_records(layout="four_money")
    _, table = _absolute_header_section_table(records, 2)
    for ordinal, column in enumerate(table["columns"]):
        column["header_path_exact"][1] = "Năm " + ("nay" if ordinal % 2 == 0 else "trước")
    before = deepcopy(records)
    compiled = _adapter_compiled()
    inventory = family._document_statement_period_inventory(records, compiled_specs=compiled)
    sources = deepcopy(inventory["sources"])
    forged = next(source for source in sources if source["statement_type"] == "CASH_FLOW")
    assert forged["absolute_duration_semantics"] is None
    assert forged["ytd_sibling_evidence"]["intrinsic_absolute_periods"] is None
    forged["lane_axis"]["source_lane_keys"] = [
        ["DURATION_DATE_RANGE", "2025-01-01", "2025-06-30"],
        ["DURATION_DATE_RANGE", "2023-01-01", "2023-06-30"],
    ]
    forged["absolute_duration_semantics"] = [["SOURCE_YTD_QUARTER", 2025, 2], ["SOURCE_YTD_QUARTER", 2023, 2]]
    sources = json.loads(json.dumps(sources, ensure_ascii=False, allow_nan=False))
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error,
                       match="^income-tax quarter-caption original header lane source replay drifted$"):
        family._document_comparative_flow_policy_receipt(
            records, sources, family._document_report_scope_receipt(records), compiled_specs=compiled,
        )
    assert records == before
