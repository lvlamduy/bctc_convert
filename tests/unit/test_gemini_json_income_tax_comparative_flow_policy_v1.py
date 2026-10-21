from __future__ import annotations

import re
import unicodedata
from copy import deepcopy

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
    section["title_exact"] = "Trình bày về khả năng so sánh thông tin trên báo cáo tài chính riêng giữa niên độ"
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
