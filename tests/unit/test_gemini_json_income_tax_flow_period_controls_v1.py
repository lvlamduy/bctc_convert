"""Finite lexical/control tests; synthetic inputs are not source approval.

These helpers may retain compatible assertions but must never manufacture a
comparative year, a start date, report scope, or a family acceptance result.
No corpus/PDF/source-registry fixture is replaced by these synthetic objects.
"""

from __future__ import annotations

import unicodedata
from copy import deepcopy

import pytest

from bctc_ai.evaluation import gemini_json_income_tax_family_v1 as family

PERIODS = [["SOURCE_YTD_QUARTER", 2025, 2], ["SOURCE_YTD_QUARTER", 2024, 2]]
PREFIX = "Ngân hàng TMCP Mẫu\n123 Đường An Bình\nThành phố Hà Nội\n"


def _section(caption, *, statement="CASH_FLOW", content_kind="PRIMARY_STATEMENT"):
    table = {
        "title_exact": None,
        "unit_exact": "Triệu đồng",
        "columns": [
            {"header_path_exact": ["Kỳ này"], "value_kind": "MONEY"},
            {"header_path_exact": ["Kỳ trước"], "value_kind": "MONEY"},
        ],
        "rows": [],
        "continuation": "NONE",
    }
    section = {
        "title_exact": caption,
        "content_kind": content_kind,
        "statement_type": statement,
        "narratives_exact": [],
        "tables": [table],
    }
    return section, table


def _scope(value="SEPARATE", *, conflict=False, entity=None):
    return {
        "report_scope": value,
        "conflict": conflict,
        "local_entity_qualifiers": [] if entity is None else [entity],
    }


def _locator(page):
    return {
        "document_id": "gfpstorev1:document:" + "a" * 64,
        "document_ordinal": 1,
        "source_logical_name": "synthetic/2025/report.pdf",
        "source_sha256": "b" * 64,
        "page_json_version_id": "gfpstorev1:json:" + str(page) * 64,
        "physical_page": page,
        "selected_page_ordinal": page,
        "section_id": "s1",
        "table_id": "t1",
    }


def _source(*, current=None, prior="Năm trước", constraints=None, scope=None, full=None):
    return {
        "locator": _locator(2),
        "statement_type": "CASH_FLOW",
        "scope_receipt": _scope() if scope is None else scope,
        "original_page_json_sha256": "c" * 64,
        "original_table_json_sha256": "d" * 64,
        "absolute_duration_semantics": full,
        "owned_current_period_constraints": [] if constraints is None else constraints,
        "owned_narratives_exact": [],
        "columns_exact": [
            {"header_path_exact": ["Mã số"], "value_kind": "TEXT"},
            {"header_path_exact": ["Kỳ này" if current is None else current], "value_kind": "MONEY"},
            {"header_path_exact": [prior], "value_kind": "MONEY"},
        ],
    }


def _control(source, *, selector_scope=None, periods=None):
    before = deepcopy(source)
    selector = {"locator": _locator(1), "scope_receipt": _scope() if selector_scope is None else selector_scope}
    result = family._cash_flow_printed_period_control_v1(selector, deepcopy(PERIODS if periods is None else periods), source)
    assert source == before
    assert result["used_as_positive_period_authority"] is False
    assert result["comparative_year_inferred"] is False
    assert result["source_period_keys_modified"] is False
    assert result["amounts_used_as_authority"] is False
    return result


@pytest.mark.parametrize("statement,title", [
    ("CASH_FLOW", "Báo cáo lưu chuyển tiền tệ"),
    ("INCOME_STATEMENT", "Báo cáo kết quả hoạt động"),
    ("INCOME_STATEMENT", "Báo cáo kết quả kinh doanh"),
])
@pytest.mark.parametrize("quarter,number", [("I", 1), ("II", 2), ("III", 3), ("IV", 4), ("2", 2)])
def test_whole_report_quarter_is_endpoint_only(statement, title, quarter, number):
    raw = f"{title} riêng quý {quarter} năm 2025"
    section, _ = _section(raw, statement=statement)
    before = deepcopy(section)
    result = family._owned_flow_report_quarter_constraint(section, source_kind="SECTION_TITLE", source_exact=raw)
    assert section == before
    assert result is not None and result["supported"] is True
    assert result["printed_reporting_quarter"] == number
    assert result["printed_year"] == 2025
    assert "printed_months" not in result
    assert "printed_start_date" not in result
    evidence = result["source_report_quarter_evidence"]
    assert evidence["source_exact"] == raw
    for key in ("report_scope_permission_granted", "entity_permission_granted", "unit_permission_granted",
                "comparative_year_permission_granted", "start_dates_inferred", "source_period_keys_modified"):
        assert evidence[key] is False


@pytest.mark.parametrize("prefix", [PREFIX, PREFIX + "Mẫu số B04a/TCTD-HN\n"])
@pytest.mark.parametrize("suffix", ["", " (tiếp theo)"])
def test_finite_legal_prologue_is_retained_without_entity_permission(prefix, suffix):
    raw = prefix + "BÁO CÁO LƯU CHUYỂN TIỀN TỆ riêng quý II năm 2025" + suffix
    section, _ = _section(raw)
    result = family._owned_flow_report_quarter_constraint(section, source_kind="SECTION_TITLE", source_exact=raw)
    assert result is not None and result["supported"] is True
    evidence = result["source_report_quarter_evidence"]
    assert evidence["source_exact"] == raw
    assert evidence["recognized_prefix_lines_exact"] == prefix.rstrip("\n").split("\n")
    assert evidence["entity_permission_granted"] is False


@pytest.mark.parametrize("title,statement", [
    ("Báo cáo lưu chuyển tiền tệ", "CASH_FLOW"),
    ("Báo cáo kết quả hoạt động", "INCOME_STATEMENT"),
])
@pytest.mark.parametrize("quarter,number", [("I", 1), ("II", 2), ("IV", 4)])
def test_existing_cho_quarter_constraint_remains_supported_with_old_fields(title, statement, quarter, number):
    raw = f"{title}\nCho quý {quarter} năm 2025"
    section, table = _section(raw, statement=statement)
    constraints = family._owned_current_period_constraints(section, table)
    assert constraints == [{"source_kind": "SECTION_TITLE", "source_exact": raw, "supported": True,
                            "printed_reporting_quarter": number, "printed_year": 2025}]


@pytest.mark.parametrize("raw", [
    "Báo cáo lưu chuyển tiền tệ quý II năm 2025 ghi chú",
    "Báo cáo lưu chuyển tiền tệ quý II năm 2025 (chưa kiểm tra)",
    "Báo cáo lưu chuyển tiền tệ quý II năm 2025*",
    "Báo cáo lưu chuyển tiền tệ quý II năm 2025 năm 2024",
    "Báo cáo lưu chuyển tiền tệ quý II năm 2025 cho quý I năm 2025",
    "Báo cáo lưu chuyển tiền tệ quý II năm 2025 (tiếp theo",
    "Báo cáo lưu chuyển tiền tệ quý II năm 2025 ()",
    "Báo cáo lưu chuyển tiền tệ quý II năm 2025 (tiếp theo) (tiếp theo)",
    "Báo cáo lưu chuyển tiền tệ quý II năm 2025¹",
    "Báo cáo lưu chuyển tiền tệ quý I\u0301I năm 2025",
    "Báo cáo lưu chuyển tiền tệ quý II năm 202\u03015",
    "Báo cáo lưu chuyển tiền tệ quý II năm 0000",
    "Thông tin không rõ\nBáo cáo lưu chuyển tiền tệ quý II năm 2025",
    PREFIX.replace("123 Đường An Bình", "123 Đường An Bình kỳ sáu tháng")
    + "Báo cáo lưu chuyển tiền tệ quý II năm 2025",
])
def test_report_quarter_never_erases_unsupported_prefix_suffix_or_raw_tokens(raw):
    section, _ = _section(raw)
    result = family._owned_flow_report_quarter_constraint(section, source_kind="SECTION_TITLE", source_exact=raw)
    assert result is not None and result["supported"] is False


@pytest.mark.parametrize("control", ["\x00", "\x0b", "\x0c", "\x1f", "\x7f", "\x85"])
@pytest.mark.parametrize("placement", ["prologue", "caption"])
def test_report_quarter_raw_controls_cannot_disappear_in_split(control, placement):
    raw = (PREFIX.replace("Mẫu", "Mẫu" + control) if placement == "prologue" else PREFIX)
    raw += "Báo cáo lưu chuyển tiền tệ quý II năm 2025" + (control if placement == "caption" else "")
    section, _ = _section(raw)
    result = family._owned_flow_report_quarter_constraint(section, source_kind="SECTION_TITLE", source_exact=raw)
    assert result is not None and result["supported"] is False


@pytest.mark.parametrize("kind,content,statement", [
    ("OWNED_NARRATIVE", "PRIMARY_STATEMENT", "CASH_FLOW"),
    ("SECTION_TITLE", "FINANCIAL_NOTE", "NOT_APPLICABLE"),
    ("SECTION_TITLE", "PRIMARY_STATEMENT", "BALANCE_SHEET"),
])
def test_report_quarter_endpoint_route_cannot_promote_other_source_ownership(kind, content, statement):
    raw = "Báo cáo lưu chuyển tiền tệ quý II năm 2025"
    section, _ = _section(raw, content_kind=content, statement=statement)
    assert family._owned_flow_report_quarter_constraint(section, source_kind=kind, source_exact=raw) is None


@pytest.mark.parametrize("prior", ["Năm trước", "Kỳ trước"])
@pytest.mark.parametrize("unit", ["", " Triệu đồng", " Triệu VND"])
def test_partial_current_header_retains_actual_ordinals_and_no_comparative_year(prior, unit):
    source = _source(current="Kỳ 6 tháng kết thúc ngày 30/06/2025" + unit, prior=prior + unit)
    before = deepcopy(source)
    partial = family._cash_flow_partial_current_header_assertion_v1(source)
    assert source == before
    assert partial is not None
    assert partial["current_column_ordinal"] == 2
    assert partial["comparative_column_ordinal"] == 3
    assert partial["printed_months"] == 6
    assert partial["printed_end_date"] == "2025-06-30"
    assert partial["header_paths_exact"] == [source["columns_exact"][1]["header_path_exact"], source["columns_exact"][2]["header_path_exact"]]
    assert partial["comparative_period_proven"] is False
    assert partial["used_as_positive_period_authority"] is False
    result = _control(source)
    assert result["status"] == "PROVEN_COMPATIBLE_PRINTED_PERIOD"
    assert result["complete_cash_flow_period_pair_proven"] is False


@pytest.mark.parametrize("current", [
    "Kỳ 0 tháng kết thúc ngày 30/06/2025",
    "Kỳ 13 tháng kết thúc ngày 30/06/2025",
    "Kỳ 6 tháng kết thúc ngày 31/02/2025",
    "Kỳ 6 tháng kết thúc ngày 00/06/2025",
    "Kỳ 6 tháng kết thúc ngày 30/06/0000",
    "Kỳ 6\u0301 tháng kết thúc ngày 30/06/2025",
    "Kỳ 6 tháng kết thúc ngày 30/06/202\u03015",
    "Kỳ 6 tháng kết thúc ngày 30/06/2025¹",
])
def test_recognized_malformed_partial_header_is_hold_not_silently_compatible(current):
    # A valid caption cannot hide an unsupported affirmative current header.
    section, table = _section("Báo cáo lưu chuyển tiền tệ riêng quý II năm 2025")
    constraints = family._owned_current_period_constraints(section, table)
    source = _source(current=current, constraints=constraints)
    partial = family._cash_flow_partial_current_header_assertion_v1(source)
    assert partial is not None and partial["complete"] is False
    assert partial["reasons"]
    result = _control(source)
    assert result["status"] == "UNRESOLVED_PERIOD_OR_POPULATION_NOT_AUTHORITY"
    assert result["unsupported_compatible_current_assertion_requires_hold"] is True


@pytest.mark.parametrize("current", [
    "Kỳ 3 tháng kết thúc ngày 30/06/2025",
    "Kỳ 9 tháng kết thúc ngày 30/09/2025",
    "Kỳ 6 tháng kết thúc ngày 30/06/2024",
])
def test_actual_partial_current_duration_or_end_conflict_is_veto(current):
    result = _control(_source(current=current))
    assert result["status"] == "PROVEN_CONTRADICTORY_PRINTED_PERIOD"
    assert any(check["compatible"] is False for check in result["printed_assertion_checks"])


@pytest.mark.parametrize("selector_scope,source_scope", [
    (_scope(None), _scope(None)),
    (_scope(), _scope(None)),
    (_scope(None), _scope()),
    (_scope(), _scope("CONSOLIDATED")),
    (_scope(conflict=True), _scope()),
    (_scope(), _scope(entity="PARENT_ENTITY")),
])
def test_partial_current_conflict_cannot_veto_without_known_same_population(selector_scope, source_scope):
    source = _source(current="Kỳ 3 tháng kết thúc ngày 31/03/2024", scope=source_scope)
    result = _control(source, selector_scope=selector_scope)
    assert result["compatible_report_population_proven"] is False
    assert result["status"] == "UNRESOLVED_PERIOD_OR_POPULATION_NOT_AUTHORITY"


@pytest.mark.parametrize("current,prior", [
    ("Kỳ này", "Kỳ trước"),
    ("30/06/2025", "Năm trước"),
    ("Không rõ", "Không rõ"),
])
def test_unknown_or_bare_date_cf_is_not_positive_period_authority(current, prior):
    source = _source(current=current, prior=prior)
    assert family._cash_flow_partial_current_header_assertion_v1(source) is None
    result = _control(source)
    assert result["status"] == "UNRESOLVED_PERIOD_OR_POPULATION_NOT_AUTHORITY"
    assert result["printed_assertion_checks"] == []
    assert result["unsupported_compatible_current_assertion_requires_hold"] is False


@pytest.mark.parametrize("caption,periods", [
    ("Báo cáo lưu chuyển tiền tệ riêng quý II năm 2025", PERIODS),
    ("Báo cáo lưu chuyển tiền tệ hợp nhất quý IV năm 2025 (tiếp theo)", [["ANNUAL_YEAR", 2025], ["ANNUAL_YEAR", 2024]]),
])
def test_census_only_exact_owned_report_quarter_caption_can_match_cumulative_endpoint(caption, periods):
    section, table = _section(caption)
    lane = {"complete": True, "money_column_ordinals": [1, 2],
            "source_lane_keys": [["SEMANTIC_ALIAS", "CURRENT_PERIOD"], ["SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"]]}
    before = deepcopy((section, table, lane, periods))
    assert family._owned_current_period_constraints_match(section, table, lane, periods)
    surfaces, _, failures = family._comparative_flow_local_surface_census(section, table, lane, periods)
    assert failures == []
    assert any(surface["kind"] == "SECTION_TITLE" and surface["source_exact"] == caption for surface in surfaces)
    assert (section, table, lane, periods) == before


@pytest.mark.parametrize("ancestor", ["Quý II năm 2025", "Báo cáo lưu chuyển tiền tệ riêng quý II năm 2025"])
def test_note_row_ancestor_does_not_receive_report_caption_endpoint_permission(ancestor):
    section, table = _section("Chi phí thuế thu nhập doanh nghiệp", content_kind="FINANCIAL_NOTE", statement="NOT_APPLICABLE")
    table["rows"] = [{"row_kind": "ITEM", "label_exact": "Chi phí thuế hiện hành",
                      "hierarchy_path_exact": [ancestor, "Chi phí thuế hiện hành"], "values_exact": ["1", "1"]}]
    lane = {"complete": True, "money_column_ordinals": [1, 2],
            "source_lane_keys": [["SEMANTIC_ALIAS", "CURRENT_PERIOD"], ["SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"]]}
    surfaces, _, failures = family._comparative_flow_local_surface_census(section, table, lane, PERIODS)
    assert failures
    assert any(surface["kind"] == "SOURCE_ROW_ANCESTOR" and surface["source_exact"] == ancestor and surface["reasons"] for surface in surfaces)


@pytest.mark.parametrize("kind", ["SECTION_TITLE", "TABLE_TITLE"])
def test_report_quarter_accepts_nfd_vietnamese_words_without_rewriting_raw_source(kind):
    raw = unicodedata.normalize("NFD", "Báo cáo lưu chuyển tiền tệ riêng quý II năm 2025")
    section, table = _section(raw if kind == "SECTION_TITLE" else None)
    if kind == "TABLE_TITLE":
        table["title_exact"] = raw
    before = deepcopy((section, table))
    result = family._owned_flow_report_quarter_constraint(section, source_kind=kind, source_exact=raw)
    assert result is not None and result["supported"] is True
    assert result["printed_reporting_quarter"] == 2
    assert result["printed_year"] == 2025
    assert result["source_report_quarter_evidence"]["source_exact"] == raw
    assert (section, table) == before


@pytest.mark.parametrize("raw", [
    "Báo cáo lưu chuyển tiền tệ riêng quý I\u0301I năm 2025",
    "Báo cáo lưu chuyển tiền tệ riêng quý II năm 202\u03015",
])
def test_nfd_word_support_never_normalizes_annotation_on_ascii_quarter_or_year(raw):
    raw = unicodedata.normalize("NFD", raw)
    section, _ = _section(raw)
    result = family._owned_flow_report_quarter_constraint(section, source_kind="SECTION_TITLE", source_exact=raw)
    assert result is not None and result["supported"] is False


def test_restatement_prior_companion_keeps_current_duration_contradiction_visible():
    source = _source(current="Kỳ 3 tháng kết thúc ngày 30/06/2025", prior="Kỳ trước (Trình bày lại)")
    partial = family._cash_flow_partial_current_header_assertion_v1(source)
    assert partial is not None and partial["complete"] is True
    assert partial["printed_months"] == 3
    assert partial["printed_end_date"] == "2025-06-30"
    assert partial["header_paths_exact"][1] == ["Kỳ trước (Trình bày lại)"]
    result = _control(source)
    assert result["status"] == "PROVEN_CONTRADICTORY_PRINTED_PERIOD"
    assert result["complete_cash_flow_period_pair_proven"] is False


@pytest.mark.parametrize("prior", ["Năm trước tham khảo", "Kỳ trước (*)"])
def test_unknown_trailer_after_recognized_prior_prefix_cannot_hide_current_assertion(prior):
    source = _source(current="Kỳ 3 tháng kết thúc ngày 30/06/2025", prior=prior)
    partial = family._cash_flow_partial_current_header_assertion_v1(source)
    assert partial is not None and partial["complete"] is False
    assert partial["header_paths_exact"][1] == [prior]
    assert partial["reasons"]
    result = _control(source)
    assert result["status"] == "UNRESOLVED_PERIOD_OR_POPULATION_NOT_AUTHORITY"
    assert result["unsupported_compatible_current_assertion_requires_hold"] is True


def test_veto_only_cf_preserves_full_pair_without_imposing_its_comparative_year_on_income():
    cash_flow_pair = deepcopy(PERIODS)
    independent_income_pair = [["SOURCE_YTD_QUARTER", 2025, 2], ["SOURCE_YTD_QUARTER", 2023, 2]]
    source = _source(current="Kỳ 6 tháng kết thúc ngày 30/06/2025",
                     prior="Kỳ 6 tháng kết thúc ngày 30/06/2024", full=cash_flow_pair)
    result = _control(source, periods=independent_income_pair)
    assert result["status"] == "PROVEN_COMPATIBLE_PRINTED_PERIOD"
    assert result["selector_periods"] == independent_income_pair
    pair_checks = [item for item in result["printed_assertion_checks"] if item["source_kind"] == "COMPLETE_CASH_FLOW_PERIOD_PAIR"]
    assert len(pair_checks) == 1
    assert pair_checks[0]["printed_periods"] == cash_flow_pair
    assert pair_checks[0]["compatible"] is True
    assert result["used_as_positive_period_authority"] is False


def test_whole_owned_bare_cf_duration_narrative_vetoes_otherwise_matching_headers():
    narrative = "Kỳ kế toán 9 tháng kết thúc ngày 30 tháng 9 năm 2025"
    source = _source(current="Kỳ 6 tháng kết thúc ngày 30/06/2025",
                     prior="Kỳ 6 tháng kết thúc ngày 30/06/2024", full=deepcopy(PERIODS))
    source["owned_narratives_exact"] = [narrative]
    result = _control(source)
    assert result["status"] == "PROVEN_CONTRADICTORY_PRINTED_PERIOD"
    assert any(check["compatible"] is False for check in result["printed_assertion_checks"])
    assert source["owned_narratives_exact"] == [narrative]


@pytest.mark.parametrize("narrative", [
    "Thông tin lịch sử: Kỳ kế toán 9 tháng kết thúc ngày 30 tháng 9 năm 2025",
    "Ngân hàng đã lập báo cáo cho kỳ kế toán 9 tháng kết thúc ngày 30 tháng 9 năm 2025",
])
def test_historical_cf_narrative_does_not_relabel_an_independently_proved_current_window(narrative):
    source = _source(current="Kỳ 6 tháng kết thúc ngày 30/06/2025",
                     prior="Kỳ 6 tháng kết thúc ngày 30/06/2024", full=deepcopy(PERIODS))
    source["owned_narratives_exact"] = [narrative]
    result = _control(source)
    assert result["status"] == "PROVEN_COMPATIBLE_PRINTED_PERIOD"
    assert all(check["compatible"] is True for check in result["printed_assertion_checks"])
    assert result["unsupported_compatible_current_assertion_requires_hold"] is False
