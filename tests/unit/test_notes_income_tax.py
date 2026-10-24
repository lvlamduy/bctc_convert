"""Notes engine: duration lanes, printed period keys and the CONCEPT_LIST income-tax plugin on synthetic tables."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from bctc_ai.notes.concept_list_shape_v1 import (
    assign_lines_v1,
    evaluate_concept_table_v1,
    evaluate_equations_v1,
)
from bctc_ai.notes.config_v1 import load_notes_config_v1
from bctc_ai.notes.engine_v1 import _assign_legacy_ids
from bctc_ai.notes.kernel_v1 import (
    DocumentContext,
    NoteColumn,
    NoteRow,
    NoteTable,
    ParsedValue,
    canonical_period_key_v1,
    resolve_duration_lanes_v1,
)
from bctc_ai.primary_statements.numbers_v1 import SeparatorRoles

ROOT = Path(__file__).resolve().parents[2]
Q1 = "DURATION:QUARTER:1:2025"
Q1_PRIOR = "DURATION:QUARTER:1:2024"
Q3 = "DURATION:QUARTER:3:2025"
YTD_Q3 = "DURATION:YTD:Q3:2025"
Q3_PRIOR = "DURATION:QUARTER:3:2024"
YTD_Q3_PRIOR = "DURATION:YTD:Q3:2024"
YEAR = "DURATION:YEAR:2025"
YEAR_PRIOR = "DURATION:YEAR:2024"


@pytest.fixture(scope="module")
def config():
    return load_notes_config_v1(ROOT)


@pytest.fixture(scope="module")
def family(config):
    return config.families["INCOME_TAX"]


def document(quarter=3, primary=None, scope="SEPARATE"):
    end = {1: "31 tháng 03", 2: "30 tháng 06", 3: "30 tháng 09", 4: "31 tháng 12"}[quarter]
    return DocumentContext(
        ordinal=1, document_plan_id="plan", relative_path="x.pdf", source_sha256="0" * 64, scope=scope,
        scope_basis="PRIMARY_DOCUMENT_SCOPE", reporting_date=None, balance_lanes=[], context_texts=[],
        primary_cells=primary or {}, separator_roles=SeparatorRoles(thousands=frozenset({"."})),
        income_context_texts=[f"BÁO CÁO KẾT QUẢ HOẠT ĐỘNG\nCho Quý {quarter} kết thúc ngày {end} năm 2025"],
        statement_pages=frozenset({"v3"}), notes_start_page=9,
    )


def kqkd(values: dict[str, dict[str, str]]):
    """{period_key: {line: value}} as accepted primary KQKD cells (million VND)."""

    rnid = {"PBT": 4377, "CURRENT": 4383, "DEFERRED": 4384, "TOTAL": 4382, "OPEX": 4391, "PROVISION": 4392}
    return {("KQKD", rnid[line], key): (Decimal(v), "MILLION_VND") for key, lines in values.items() for line, v in lines.items()}


def make_table(rows, headers, *, title="28. Chi phí thuế thu nhập doanh nghiệp", section="Thuyết minh báo cáo tài chính",
               unit="Đơn vị: triệu đồng", page=37, version="v37"):
    columns = [NoteColumn(f"c{i}", i, tuple(h), "MONEY") for i, h in enumerate(headers, 1)]
    table = NoteTable(1, page, version, "s1", "t1", 0, 0, "FINANCIAL_NOTE", section, title, unit, "NONE", [], columns)
    for index, (label, values) in enumerate(rows):
        table.rows.append(NoteRow(f"r{index}", index, label, "ITEM", (), None))
        for column, value in zip(columns, values, strict=False):
            state = "BLANK" if value is None else ("DASH" if value.strip() == "-" else "VALUE")
            table.cells[(f"r{index}", column.column_id)] = (value, state)
    return table


def context_of(table):
    return [(s, t) for s, t in (("TABLE_TITLE", table.table_title), ("SECTION_TITLE", table.section_title)) if t]


def cells(evaluations):
    return {(c["member"], c["period_key"]): c for e in evaluations for c in e.cells}


RECON = [
    ("Tổng lợi nhuận/(lỗ) kế toán trước thuế", ["435.432", "180.905"]),
    ("Các khoản điều chỉnh giảm:", [None, None]),
    ("Thu nhập không chịu thuế", ["(589)", "(4.068)"]),
    ("Chi phí không được trừ khi xác định thu nhập chịu thuế", ["3.608", "4.900"]),
    ("Thu nhập/(lỗ) chịu thuế ước tính trong kỳ", ["438.451", "181.737"]),
    ("Thuế TNDN theo thuế suất quy định (20%)", ["87.690", "36.347"]),
    ("Điều chỉnh thuế TNDN năm trước", ["118", "815"]),
    ("Chi phí thuế TNDN hiện hành trong kỳ", ["87.808", "37.162"]),
    ("Thuế TNDN phải nộp đầu kỳ", ["41.908", "2.159"]),
    ("Thuế TNDN đã nộp trong kỳ", ["(60.637)", "(33.261)"]),
    ("Thuế TNDN phải nộp cuối kỳ", ["69.079", "6.060"]),
]


# --------------------------------------------------------------------------- period keys


@pytest.mark.parametrize("key,canonical", [
    ("DURATION:QUARTER:1:2025", Q1),
    ("DURATION:YTD:Q1:2025", Q1),                       # year-to-date through Q1 is Q1, by definition
    ("DURATION:YTD:Q4:PRIOR_YEAR_OF(2025)", YEAR_PRIOR),  # through Q4 is the year
    ("DURATION:QUARTER:3:PRIOR_YEAR_OF(2025)", Q3_PRIOR),
    ("DURATION:YTD:Q3:2025", YTD_Q3),
    ("DURATION:RANGE:2025-01-01..2025-06-30", "DURATION:RANGE:2025-01-01..2025-06-30"),
    ("DURATION:MONTHS_ENDED:9:2025-09-30", "DURATION:MONTHS_ENDED:9:2025-09-30"),  # no computed start date
    ("INSTANT:2025-09-30", None),
    ("DURATION:YTD:Q2:NOT_A_YEAR", None),
])
def test_canonical_period_key_uses_definitional_identities_only(key, canonical):
    assert canonical_period_key_v1(key) == canonical


# --------------------------------------------------------------------------- lanes


def test_printed_quarter_and_ytd_headers_resolve_explicitly():
    table = make_table(RECON[:1], [("Quý 3/2025",), ("Lũy kế từ đầu năm đến cuối quý 3/2025",), ("Năm 2025",)])
    lanes = resolve_duration_lanes_v1(table, document(), [], [table.table_title])
    assert [lane.period_key for lane in lanes[:2]] == [Q3, YTD_Q3]
    assert lanes[0].period_basis.startswith("HEADER_PRINTED") and lanes[0].unit == "MILLION_VND"
    assert lanes[2].period_key is None  # "Năm 2025" in a third-quarter report is not bound


def test_bare_end_date_in_first_quarter_is_the_quarter_by_definition():
    table = make_table(RECON[:1], [("31/03/2025",), ("31/03/2024",)])
    lanes = resolve_duration_lanes_v1(table, document(quarter=1), [], [table.table_title])
    assert [lane.period_key for lane in lanes] == [Q1, Q1_PRIOR]
    assert all(lane.period_basis == "FIRST_QUARTER_IS_YEAR_TO_DATE" for lane in lanes)


def test_bare_end_date_in_third_quarter_keeps_two_candidates():
    table = make_table(RECON[:1], [("30/09/2025",), ("30/09/2024",)])
    lanes = resolve_duration_lanes_v1(table, document(quarter=3), [], [table.table_title])
    assert [lane.period_key for lane in lanes] == [None, None]
    assert lanes[0].candidates == [Q3, YTD_Q3] and lanes[1].candidates == [Q3_PRIOR, YTD_Q3_PRIOR]
    assert "PERIOD_QUARTER_OR_YEAR_TO_DATE_NOT_PRINTED" in lanes[0].reasons


def test_cumulative_from_start_of_period_is_held_with_a_named_reason_not_none():
    # "Từ đầu kỳ" does not print where the period starts: no canonical key, no candidate, and the
    # stored reason names the printed grain instead of the literal "PERIOD_UNRESOLVED:None".
    table = make_table(RECON[:1], [("Lũy kế từ đầu kỳ đến ngày 31/12/2025",), ("Lũy kế từ đầu năm đến ngày 31/12/2025",)])
    lanes = resolve_duration_lanes_v1(table, document(quarter=4), [], [table.table_title])
    assert lanes[0].period_key is None and lanes[0].candidates == []
    assert lanes[0].reasons == ["PERIOD_UNRESOLVED:PRINTED_WINDOW_WITHOUT_CANONICAL_KEY:CUMULATIVE_FROM_START_OF_PERIOD_TO"]
    assert lanes[1].period_key == "DURATION:CUMULATIVE_FROM_START_OF_YEAR_TO:2025-12-31"  # kept as printed
    assert not any("None" in reason for lane in lanes for reason in lane.reasons)
    # The literal held FULL271 headers (ord 140, s2/t1/c1-c2): "Lũy kế <date>" prints only the end (0203-claude).
    printed = make_table(RECON[:1], [("Lũy kế 30/09/2025",), ("Lũy kế 30/09/2024",)])
    lanes = resolve_duration_lanes_v1(printed, document(quarter=3), [], [printed.table_title])
    assert [(lane.period_key, lane.candidates, lane.reasons) for lane in lanes] == [
        (None, [], ["PERIOD_UNRESOLVED:PRINTED_WINDOW_WITHOUT_CANONICAL_KEY:CUMULATIVE_FROM_START_OF_PERIOD_TO"])] * 2


def test_this_period_has_candidates_previous_period_never_and_segments_are_not_periods():
    table = make_table(RECON[:1], [("Kỳ này",), ("Kỳ trước",), ("Miền Bắc",)])
    lanes = resolve_duration_lanes_v1(table, document(quarter=3), [], [table.table_title])
    assert lanes[0].candidates == [Q3, YTD_Q3]
    assert lanes[1].candidates == [] and lanes[1].period_key is None
    assert lanes[2].period_key is None and "HEADER_NAMES_SEGMENT_OR_SCOPE" in lanes[2].reasons
    first = resolve_duration_lanes_v1(table, document(quarter=1), [], [table.table_title])
    assert first[0].period_key == Q1 and first[1].period_key is None  # "Kỳ trước" of Q1 may be Q4: held


def test_own_and_report_context_disagreement_holds():
    table = make_table(RECON[:1], [("Kỳ này",)], section="Thuyết minh báo cáo tài chính cho năm kết thúc ngày 31/12/2025")
    lanes = resolve_duration_lanes_v1(table, document(quarter=3), [], [table.section_title])
    assert lanes[0].period_key is None and "OWN_AND_REPORT_CONTEXT_DISAGREE" in lanes[0].reasons


# --------------------------------------------------------------------------- lines


def test_line_rules_on_printed_labels(family):
    table = make_table(RECON + [("Thuế suất thuế thu nhập doanh nghiệp", ["20%", "20%"]),
                                ("Thu nhập miễn thuế (lợi nhuận năm trước công ty con chuyển)", ["(5.145)", "(4.366)"]),
                                ("Chi phí thuế TNDN hoãn lại", ["-", "-"]), ("Chi phí thuế TNDN", ["87.808", "37.162"])],
                       [("Kỳ này",), ("Kỳ trước",)])
    lines = {table.rows[r.row_index].label: (r.role, r.disposition) for r in assign_lines_v1(table, family)}
    assert lines["Tổng lợi nhuận/(lỗ) kế toán trước thuế"] == ("PROFIT_BEFORE_TAX", "MEMBER")
    assert lines["Chi phí không được trừ khi xác định thu nhập chịu thuế"] == ("NON_DEDUCTIBLE_EXPENSES", "MEMBER")
    assert lines["Thu nhập/(lỗ) chịu thuế ước tính trong kỳ"] == ("TAXABLE_INCOME", "MEMBER")
    assert lines["Thuế TNDN theo thuế suất quy định (20%)"] == ("TAX_AT_STATUTORY_RATE", "MEMBER")
    assert lines["Điều chỉnh thuế TNDN năm trước"] == ("PRIOR_YEAR_TAX_ADJUSTMENT", "MEMBER")
    assert lines["Chi phí thuế TNDN hiện hành trong kỳ"] == ("CURRENT_TAX_EXPENSE", "MEMBER")
    assert lines["Thuế TNDN phải nộp đầu kỳ"] == ("TAX_PAYABLE_OPENING", "MEMBER")
    assert lines["Thuế TNDN đã nộp trong kỳ"] == ("TAX_PAID", "MEMBER")
    assert lines["Thuế TNDN phải nộp cuối kỳ"] == ("TAX_PAYABLE_CLOSING", "MEMBER")
    assert lines["Thuế suất thuế thu nhập doanh nghiệp"] == ("TAX_RATE", "MEMBER")
    assert lines["Chi phí thuế TNDN hoãn lại"] == ("DEFERRED_TAX_EXPENSE", "MEMBER")
    assert lines["Chi phí thuế TNDN"] == ("TOTAL_TAX_EXPENSE", "MEMBER")
    assert lines["Các khoản điều chỉnh giảm:"] == (None, "HEADING")
    # Two printed non-taxable lines: neither is chosen.
    assert lines["Thu nhập không chịu thuế"][1] == "AMBIGUOUS"
    assert lines["Thu nhập miễn thuế (lợi nhuận năm trước công ty con chuyển)"][1] == "AMBIGUOUS"


def test_a_line_printed_twice_is_held_even_with_identical_values(family):
    same = [("Lợi nhuận trước thuế", ["100", "90"]), ("Thu nhập chịu thuế", ["99", "92"]), ("Thu nhập chịu thuế", ["99", "92"])]
    roles = assign_lines_v1(make_table(same, [("Năm 2025",), ("Năm 2024",)]), family)
    assert (roles[1].disposition, roles[2].disposition) == ("AMBIGUOUS", "AMBIGUOUS")


def test_deduction_sign_follows_printed_sign_not_the_variant_that_passes(family):
    def parsed(text):
        return ParsedValue("VALUE", Decimal(text), text, None)

    positive = {"PROFIT_BEFORE_TAX": parsed("100"), "NON_TAXABLE_INCOME": parsed("10"), "TAXABLE_INCOME": parsed("90")}
    negative = {"PROFIT_BEFORE_TAX": parsed("100"), "NON_TAXABLE_INCOME": parsed("-10"), "TAXABLE_INCOME": parsed("90")}
    wrong = {"PROFIT_BEFORE_TAX": parsed("100"), "NON_TAXABLE_INCOME": parsed("10"), "TAXABLE_INCOME": parsed("110")}
    def status(values):
        return next(e["status"] for e in evaluate_equations_v1(family, values, "MILLION_VND", "c1")
                    if e["name"] == "TAXABLE_FROM_PROFIT")
    assert status(positive) == "PASS" and status(negative) == "PASS"
    assert status(wrong) == "FAIL"  # a positive deduction is never added to make the sum work


# --------------------------------------------------------------------------- evaluation


def test_first_quarter_reconciliation_accepted_with_equation_and_primary_proof(family, config):
    rows = [("Lợi nhuận trước thuế", ["406.920", "178.212"]), ("Chi phí không được khấu trừ", ["1.000", "8"]),
            ("Thu nhập chịu thuế", ["407.920", "178.220"]), ("Chi phí thuế TNDN hiện hành", ["81.584", "35.644"])]
    table = make_table(rows, [("31/03/2025",), ("31/03/2024",)])
    primary = kqkd({"DURATION:QUARTER:1:2025": {"PBT": "406920"}, "DURATION:YTD:Q1:2025": {"PBT": "406920"},
                    "DURATION:QUARTER:1:PRIOR_YEAR_OF(2025)": {"PBT": "178212"}})
    evaluations = evaluate_concept_table_v1(table, family, document(quarter=1, primary=primary), context_of(table), [])
    result = cells(evaluations)
    pbt = result[("PROFIT_BEFORE_TAX", Q1)]
    assert pbt["acceptance"] == "ACCEPTED" and pbt["value"] == "406920" and pbt["concept"] == "INCOME_TAX_NOTE"
    assert pbt["product_status"] == "PROTOTYPE_NOT_ACCEPTANCE"
    assert result[("TAXABLE_INCOME", Q1_PRIOR)]["acceptance"] == "ACCEPTED"
    assert any(e["name"] == "TAXABLE_FROM_PROFIT" and e["status"] == "PASS" for e in evaluations[0].equations)
    all_cells = [c for e in evaluations for c in e.cells]
    _assign_legacy_ids(all_cells, config)
    ids = {c["member"]: c["report_norm_id"] for c in all_cells if c["period_key"] == Q1}
    # 5729/5730 are held: the label alone proves neither the legacy base amount nor the population.
    assert ids["PROFIT_BEFORE_TAX"] == 5728 and ids["NON_DEDUCTIBLE_EXPENSES"] is None
    states = {c["member"]: c["semantic_state"] for c in all_cells if c["period_key"] == Q1}
    assert states["NON_DEDUCTIBLE_EXPENSES"] == "BASE_OR_TAX_EFFECT_UNPROVEN" and states["PROFIT_BEFORE_TAX"] is None


def test_primary_line_differing_for_the_period_vetoes_the_lane(family):
    rows = [("Lợi nhuận trước thuế", ["500", "90"]), ("Thu nhập chịu thuế", ["500", "90"])]
    table = make_table(rows, [("Năm 2025",), ("Năm 2024",)])
    primary = kqkd({"DURATION:YEAR:2025": {"PBT": "499"}})
    result = cells(evaluate_concept_table_v1(table, family, document(quarter=4, primary=primary), context_of(table), []))
    held = result[("PROFIT_BEFORE_TAX", YEAR)]
    assert held["acceptance"] == "HOLD" and "PRIMARY_LINE_DIFFERS_FOR_PERIOD" in held["hold_reasons"]
    assert result[("PROFIT_BEFORE_TAX", YEAR_PRIOR)]["acceptance"] == "ACCEPTED"  # own arithmetic, no primary cell


def test_failing_equation_holds_its_lines_even_when_primary_matches(family):
    rows = [("Lợi nhuận trước thuế", ["500", "90"]), ("Chi phí không được khấu trừ", ["7", "1"]), ("Thu nhập chịu thuế", ["500", "91"])]
    table = make_table(rows, [("Năm 2025",), ("Năm 2024",)])
    primary = kqkd({"DURATION:YEAR:2025": {"PBT": "500"}})
    result = cells(evaluate_concept_table_v1(table, family, document(quarter=4, primary=primary), context_of(table), []))
    assert "VALIDATION_FAIL" in result[("TAXABLE_INCOME", YEAR)]["hold_reasons"]
    assert result[("PROFIT_BEFORE_TAX", YEAR_PRIOR)]["acceptance"] == "ACCEPTED"


def test_candidate_periods_stay_held_and_primary_comparison_is_diagnostic_only(family):
    table = make_table(RECON, [("30/09/2025", "Triệu VND"), ("30/09/2024", "Triệu VND")])
    primary = kqkd({"DURATION:QUARTER:3:2025": {"PBT": "150000"}, "DURATION:YTD:Q3:2025": {"PBT": "435432", "CURRENT": "87808"}})
    evaluations = evaluate_concept_table_v1(table, family, document(quarter=3, primary=primary), context_of(table), [])
    result = [c for e in evaluations for c in e.cells]
    assert result and all(c["acceptance"] == "HOLD" and c["period_key"] is None and c["period_candidates"] for c in result)
    diagnostics = [c for c in evaluations[0].corroboration if c.get("diagnostic_only")]
    assert {c["status"] for c in diagnostics} >= {"EXACT", "DIFFERS"}
    assert not any(c["member"] in {"TAX_PAYABLE_OPENING", "TAX_PAYABLE_CLOSING"} for c in result)


def test_statement_pages_budget_notes_and_untitled_lists_are_rejected(family):
    rows = [("Lợi nhuận trước thuế", ["100", "90"]), ("Thu nhập chịu thuế", ["100", "90"])]
    on_statement = make_table(rows, [("Năm 2025",), ("Năm 2024",)], version="v3")
    assert evaluate_concept_table_v1(on_statement, family, document(), context_of(on_statement), [])[0].reasons == ["PRIMARY_STATEMENT_PAGE"]
    budget = make_table(rows, [("Năm 2025",), ("Năm 2024",)], title="36. Tình hình thực hiện nghĩa vụ với Ngân sách Nhà nước")
    assert evaluate_concept_table_v1(budget, family, document(), context_of(budget), [])[0].status == "REJECTED"
    untitled = make_table([("Lợi nhuận trước thuế", ["100", "90"]), ("Khác", ["1", "2"])], [("Năm 2025",), ("Năm 2024",)],
                          title=None, section="Thông tin bổ sung")
    assert evaluate_concept_table_v1(untitled, family, document(), context_of(untitled), [])[0].status == "REJECTED"


def test_dash_stays_a_dash_and_blank_is_never_zero(family):
    rows = [("Lợi nhuận trước thuế", ["100", "90"]), ("Chi phí không được khấu trừ", ["-", None]), ("Thu nhập chịu thuế", ["100", "90"])]
    table = make_table(rows, [("Năm 2025",), ("Năm 2024",)])
    evaluations = evaluate_concept_table_v1(table, family, document(quarter=4), context_of(table), [])
    result = cells(evaluations)
    dash = result[("NON_DEDUCTIBLE_EXPENSES", YEAR)]
    assert dash["observation_state"] == "DASH" and dash["value"] is None
    blank = result[("NON_DEDUCTIBLE_EXPENSES", YEAR_PRIOR)]
    assert blank["observation_state"] == "BLANK" and blank["value"] is None
    # The 2025 equation has a dash term: not evaluable, so it proves nothing.
    assert any(e["status"] == "NOT_EVALUABLE" for e in evaluations[0].equations if e["lane"] == "c1")


def test_unread_row_inside_the_equation_span_makes_it_incomplete(family):
    rows = [("Lợi nhuận trước thuế", ["100", "90"]), ("Lỗ từ hoạt động khác được bù trừ", ["5", "5"]),
            ("Thu nhập chịu thuế", ["95", "85"])]
    table = make_table(rows, [("Năm 2025",), ("Năm 2024",)])
    evaluations = evaluate_concept_table_v1(table, family, document(quarter=4), context_of(table), [])
    assert {e["status"] for e in evaluations[0].equations} == {"INCOMPLETE_UNREAD_ROWS_IN_SPAN"}
    assert all("VALIDATION_FAIL" not in c["hold_reasons"] for c in evaluations[0].cells)
    assert all(c["acceptance"] == "HOLD" and "EQUATION_SPAN_HAS_UNREAD_ROWS" in c["hold_reasons"] for c in evaluations[0].cells)


def annual_document():
    doc = document(quarter=4)
    doc.income_context_texts = ["BÁO CÁO KẾT QUẢ HOẠT ĐỘNG\nCho năm tài chính kết thúc ngày 31 tháng 12 năm 2025"]
    return doc


def test_annual_report_end_date_headers_are_the_reported_years():
    table = make_table(RECON[:1], [("31/12/2025",), ("Năm tài chính kết thúc ngày 31.12.2024",), ("30/06/2025",)])
    lanes = resolve_duration_lanes_v1(table, annual_document(), [], [table.table_title])
    assert [lane.period_key for lane in lanes] == [YEAR, YEAR_PRIOR, None]
    assert lanes[0].period_basis == "ANNUAL_REPORT_END_DATE"
    # The same bare date in a fourth-quarter report stays open between Q4 and the year.
    q4 = resolve_duration_lanes_v1(make_table(RECON[:1], [("31/12/2025",)]), document(quarter=4), [], [table.table_title])
    assert q4[0].period_key is None and q4[0].candidates == ["DURATION:QUARTER:4:2025", YEAR]


def annual_with(text):
    doc = document(quarter=4)
    doc.income_context_texts = [text]
    return doc


@pytest.mark.parametrize("report_title", [
    "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG\nCho năm tài chính kết thúc ngày 30 tháng 06 năm 2025",          # non-calendar fiscal year
    "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG\nCho năm tài chính từ ngày 01/04/2025 đến ngày 31/12/2025",       # contrary range start
])
def test_annual_rule_never_relabels_a_non_calendar_or_partial_window(report_title):
    table = make_table(RECON[:1], [("30/06/2025",), ("31/12/2025",)])
    lanes = resolve_duration_lanes_v1(table, annual_with(report_title), [], [table.table_title])
    assert [lane.period_key for lane in lanes] == [None, None]


def test_annual_rule_holds_when_the_note_caption_prints_another_window():
    table = make_table(RECON[:1], [("31/12/2025",)], section="Thuyết minh cho 6 tháng đầu của năm tài chính kết thúc ngày 31/12/2025")
    lanes = resolve_duration_lanes_v1(table, annual_document(), [], [table.section_title])
    assert lanes[0].period_key is None and "OWN_AND_REPORT_CONTEXT_DISAGREE" in lanes[0].reasons
    other_year = make_table(RECON[:1], [("31/12/2025",)], section="Thuyết minh cho năm tài chính kết thúc ngày 31/12/2024")
    lanes = resolve_duration_lanes_v1(other_year, annual_document(), [], [other_year.section_title])
    assert lanes[0].period_key is None


@pytest.mark.parametrize("header", ["2020 31/12/2025", "31/12/2025 32/12/2025", "31/12/2025 (đã kiểm toán)", "Tại 31/12/2025 và 2024"])
def test_end_date_header_grammar_rejects_extra_assertions(header):
    table = make_table(RECON[:1], [(header,)])
    assert resolve_duration_lanes_v1(table, annual_document(), [], [table.table_title])[0].period_key is None
    assert resolve_duration_lanes_v1(table, document(quarter=4), [], [table.table_title])[0].candidates == []


def test_more_specific_own_caption_is_not_a_contradiction():
    table = make_table(RECON[:1], [("Kỳ này",)], section="Thuyết minh báo cáo tài chính cho kỳ 9 tháng kết thúc ngày 30/09/2025")
    lanes = resolve_duration_lanes_v1(table, document(quarter=3), [], [table.section_title])
    assert "OWN_AND_REPORT_CONTEXT_DISAGREE" not in lanes[0].reasons
    assert lanes[0].period_key == "DURATION:MONTHS_ENDED:9:2025-09-30"
    assert lanes[0].period_basis == "OWN_CAPTION_BOUND:DURATION:MONTHS_ENDED:9:2025-09-30"


def test_owned_partial_window_blocks_the_annual_fallback_even_if_primary_prints_no_start():
    table = make_table(RECON[:1], [("31/12/2025",)], section="Thuyết minh cho giai đoạn từ ngày 01/04/2025 đến ngày 31/12/2025")
    lanes = resolve_duration_lanes_v1(table, annual_document(), [], [table.section_title])
    assert lanes[0].period_key is None


@pytest.mark.parametrize("header", [
    "31/12/2025\u0301",       # combining acute after the date
    "\u0663\u0661/12/2025",  # Arabic-Indic day digits
    "31/12/20\u0662\u0665",  # mixed-digit year
])
def test_raw_date_tokens_must_be_plain_ascii_without_stray_marks(header):
    table = make_table(RECON[:1], [(header,)])
    assert resolve_duration_lanes_v1(table, annual_document(), [], [table.table_title])[0].period_key is None
    assert resolve_duration_lanes_v1(table, document(quarter=4), [], [table.table_title])[0].candidates == []


def test_printed_year_header_is_not_relabelled_under_a_non_calendar_fiscal_year():
    doc = annual_with("BÁO CÁO KẾT QUẢ HOẠT ĐỘNG\nCho năm tài chính kết thúc ngày 30 tháng 06 năm 2025")
    table = make_table(RECON[:1], [("Năm 2025",)])
    lane = resolve_duration_lanes_v1(table, doc, [], [table.table_title])[0]
    assert lane.period_key is None and "NON_CALENDAR_FISCAL_WINDOW_NOT_RELABELLED_AS_YEAR" in lane.reasons
    calendar = resolve_duration_lanes_v1(table, annual_document(), [], [table.table_title])[0]
    assert calendar.period_key == YEAR  # an independent full calendar-year header stays resolved


def test_context_bound_year_is_not_relabelled_under_a_non_calendar_fiscal_year():
    doc = annual_with("BÁO CÁO KẾT QUẢ HOẠT ĐỘNG\nCho năm tài chính kết thúc ngày 30 tháng 06 năm 2025")
    table = make_table(RECON[:1], [("Kỳ này",), ("Năm nay",)])
    lanes = resolve_duration_lanes_v1(table, doc, [], [table.table_title])
    assert [lane.period_key for lane in lanes] == [None, None]
    assert all("NON_CALENDAR_FISCAL_WINDOW_NOT_RELABELLED_AS_YEAR" in lane.reasons for lane in lanes)


def test_raw_guard_runs_before_the_owned_context_parser():
    table = make_table(RECON[:1], [("30/09/2025\u0301",), ("Kỳ này",)],
                       section="Thuyết minh báo cáo tài chính cho kỳ 9 tháng kết thúc ngày 30/09/2025")
    lanes = resolve_duration_lanes_v1(table, document(quarter=3), [], [table.section_title])
    assert lanes[0].period_key is None and "HEADER_RAW_DIGIT_OR_MARK_NOT_PLAIN" in lanes[0].reasons
    assert lanes[1].period_key == "DURATION:MONTHS_ENDED:9:2025-09-30"  # accented words stay valid


def nested_table(parent_label="Chi phí không được khấu trừ", parent_values=("5", "5"), child_parent="r1",
                 child_path=None, parent_path=None, extra_rows=()):
    rows = [("Lợi nhuận trước thuế", ["100", "90"]), (parent_label, list(parent_values)),
            ("Chi phí tiếp khách vượt định mức", ["5", "5"]), *extra_rows, ("Thu nhập chịu thuế", ["105", "95"])]
    table = make_table(rows, [("Năm 2025",), ("Năm 2024",)])
    parent_path = (parent_label,) if parent_path is None else parent_path
    child_path = (parent_label, "Chi phí tiếp khách vượt định mức") if child_path is None else child_path
    p, c = table.rows[1], table.rows[2]
    table.rows[1] = NoteRow(p.row_id, p.order, p.label, p.kind, parent_path, None)
    table.rows[2] = NoteRow(c.row_id, c.order, c.label, c.kind, child_path, child_parent)
    return table


def taxable_status(family, table, lane="c1"):
    evaluations = evaluate_concept_table_v1(table, family, document(quarter=4), context_of(table), [])
    return {e["status"] for e in evaluations[0].equations if e["name"] == "TAXABLE_FROM_PROFIT" and e["lane"] == lane}


def test_unread_row_proven_as_printed_detail_of_a_term_does_not_open_the_equation(family):
    assert taxable_status(family, nested_table()) == {"PASS"}
    flat = make_table([("Lợi nhuận trước thuế", ["100", "90"]), ("Chi phí không được khấu trừ", ["5", "5"]),
                       ("Chi phí tiếp khách vượt định mức", ["5", "5"]), ("Thu nhập chịu thuế", ["105", "95"])],
                      [("Năm 2025",), ("Năm 2024",)])
    assert taxable_status(family, flat) == {"INCOMPLETE_UNREAD_ROWS_IN_SPAN"}


@pytest.mark.parametrize("case", ["raw_path_disagrees", "self_parent", "parent_missing", "parent_ambiguous",
                                  "parent_blank_in_lane", "parent_not_in_equation", "duplicate_row_ids"])
def test_unread_detail_is_never_excused_without_full_printed_proof(family, case):
    if case == "raw_path_disagrees":
        table = nested_table(child_path=("Khác", "Chi phí tiếp khách vượt định mức"))
    elif case == "self_parent":
        table = nested_table(child_parent="r2")
    elif case == "parent_missing":
        table = nested_table(child_parent="r99")
    elif case == "parent_ambiguous":
        # The parent's line is printed twice, so the parent is AMBIGUOUS: it never contains detail.
        table = nested_table(extra_rows=[("Chi phí không được khấu trừ", ["1", "1"])])
    elif case == "parent_blank_in_lane":
        table = nested_table(parent_values=(None, "5"))
    elif case == "parent_not_in_equation":
        table = nested_table(parent_label="Thuế TNDN đã nộp trong kỳ")
    else:
        table = nested_table()
        dup = table.rows[3]
        table.rows[3] = NoteRow("r1", dup.order, dup.label, dup.kind, dup.hierarchy, dup.parent_row_id)
    assert "PASS" not in taxable_status(family, table)


def _link(table, child, parent):
    """Print ``child`` under ``parent`` as the source does: parent_row_id plus the raw hierarchy path."""

    from dataclasses import replace
    owner = table.rows[parent]
    if not owner.hierarchy:
        owner = table.rows[parent] = replace(owner, hierarchy=(owner.label,))
    row = table.rows[child]
    table.rows[child] = replace(row, hierarchy=(*owner.hierarchy, row.label), parent_row_id=owner.row_id)


ANNUAL = [("Năm 2025",), ("Năm 2024",)]


def test_payable_or_stock_rows_are_never_the_current_tax_expense(family):
    # Codex 0196: positive current-EXPENSE meaning only.
    rows = [("Số dư thuế TNDN phải nộp", ["69.079", "6.060"]), ("Thuế TNDN phải nộp", ["50", "40"]),
            ("Thuế thu nhập doanh nghiệp phải nộp", ["50", "40"]), ("Chi phí thuế TNDN hiện hành", ["87.808", "37.162"])]
    roles = assign_lines_v1(make_table(rows, ANNUAL), family)
    assert [r.role for r in roles[:3]] == [None, None, None]
    assert (roles[3].role, roles[3].disposition) == ("CURRENT_TAX_EXPENSE", "MEMBER")


def test_bound_line_needs_its_own_equation_or_anchor_not_the_lanes(family):
    # A valid PBT -> taxable reconciliation proves its own lines; a current-tax row that no own equation or anchor
    # proves is held, never accepted by that unrelated arithmetic (annual headers, Q4 document).
    rows = [("Lợi nhuận kế toán trước thuế", ["1.000", "900"]), ("Chi phí không được khấu trừ", ["20", "10"]),
            ("Thu nhập chịu thuế", ["1.020", "910"]), ("Chi phí thuế TNDN hiện hành", ["999", "888"])]
    table = make_table(rows, ANNUAL)
    result = cells(evaluate_concept_table_v1(table, family, document(quarter=4), context_of(table), []))
    assert result[("PROFIT_BEFORE_TAX", YEAR)]["acceptance"] == "ACCEPTED"
    assert result[("TAXABLE_INCOME", YEAR_PRIOR)]["acceptance"] == "ACCEPTED"
    current = result[("CURRENT_TAX_EXPENSE", YEAR)]
    assert current["acceptance"] == "HOLD" and "LINE_NOT_PROVEN_BY_ITS_OWN_EQUATION_OR_ANCHOR" in current["hold_reasons"]
    # Genuine positive: the current-tax line proven by its own components equation (20% of 1.020 + prior-year 0).
    proven = make_table(rows[:3] + [("Thuế TNDN tính theo thuế suất", ["204", "182"]), ("Điều chỉnh thuế TNDN năm trước", ["6", "8"]),
                                    ("Chi phí thuế TNDN hiện hành", ["210", "190"])], ANNUAL)
    result = cells(evaluate_concept_table_v1(proven, family, document(quarter=4), context_of(proven), []))
    assert result[("CURRENT_TAX_EXPENSE", YEAR)]["acceptance"] == "ACCEPTED"
    assert result[("CURRENT_TAX_EXPENSE", YEAR_PRIOR)]["acceptance"] == "ACCEPTED"


def test_bare_current_year_label_needs_a_proven_current_tax_owner(family):
    # Codex 0196: "Năm hiện hành" is CURRENT_YEAR_PORTION only under its proven, final CURRENT_TAX_EXPENSE parent.
    def table_under(owner_label):
        table = make_table([(owner_label, ["87.808", "37.162"]), ("Năm hiện hành", ["87.690", "36.347"])], ANNUAL)
        _link(table, 1, 0)
        return table

    roles = assign_lines_v1(table_under("Chi phí thuế TNDN hiện hành"), family)
    assert (roles[1].role, roles[1].disposition) == ("CURRENT_YEAR_PORTION", "MEMBER")
    paid = assign_lines_v1(table_under("Thuế TNDN đã nộp trong năm"), family)[1]
    assert (paid.role, paid.disposition, paid.reason) == (None, "SOURCE_ONLY", "OWNER_NOT_PROVEN:PARENT_LINE_TAX_PAID")
    top = assign_lines_v1(make_table([("Năm hiện hành", ["87.690", "36.347"])], ANNUAL), family)[0]
    assert (top.role, top.disposition, top.reason) == (None, "SOURCE_ONLY", "OWNER_NOT_PROVEN:NO_PRINTED_PARENT")
    # A CURRENT_TAX_EXPENSE parent made AMBIGUOUS by a second printing releases the child.
    dup = table_under("Chi phí thuế TNDN hiện hành")
    dup.rows.append(type(dup.rows[0])("r2", 2, "Chi phí thuế TNDN hiện hành", "ITEM", ("Chi phí thuế TNDN hiện hành",), None))
    for column in dup.columns:
        dup.cells[("r2", column.column_id)] = ("1", "VALUE")
    child = assign_lines_v1(dup, family)[1]
    assert (child.role, child.disposition, child.reason) == (None, "SOURCE_ONLY", "OWNER_NOT_PROVEN:PARENT_NOT_A_FINAL_MEMBER")


INTERIM_Q4 = ["Báo cáo kết quả hoạt động giữa niên độ cho giai đoạn từ ngày 01/1/2025 đến ngày 31/12/2025"]
YEAR_ENDED_HEADERS = [("Năm kết thúc ngày 31/12/2025 Triệu VND",), ("Năm kết thúc\nngày 31/12/2024\nTriệu VND",)]


def test_year_ended_header_is_recorded_as_shadow_evidence_only(family, monkeypatch):
    # Codex 0230/0232 R1 (doc 69 C1/C2 literals): "Năm kết thúc ngày D" under an interim 01/01..31/12 statement is
    # recorded as DURATION:YEAR_ENDED:D shadow evidence. Nothing else changes: same cells, acceptance, holds, period
    # keys, candidates and legacy IDs as with the shadow grammar disabled, even with a PRIMARY amount that would agree.
    from dataclasses import replace

    from bctc_ai.notes import kernel_v1

    interim = replace(document(quarter=4), income_context_texts=INTERIM_Q4,
                      primary_cells=kqkd({"DURATION:YTD:TO_12-31:2025": {"CURRENT": "87808"}}))

    def evaluate():
        table = make_table(RECON, YEAR_ENDED_HEADERS)
        evaluations = evaluate_concept_table_v1(table, family, interim, context_of(table), [])
        cells_ = [dict(c) for e in evaluations for c in e.cells]
        _assign_legacy_ids(cells_, load_notes_config_v1(ROOT))
        return evaluations, cells_

    shadowed, with_shadow = evaluate()
    monkeypatch.setattr(kernel_v1, "year_ended_shadow_v1", lambda header: None)
    plain, without_shadow = evaluate()
    assert with_shadow == without_shadow and with_shadow  # every field of every cell, including report_norm_id
    assert all(c["period_key"] is None and c["period_candidates"] == [] and c["acceptance"] == "HOLD"
               and "PERIOD_UNRESOLVED:PERIOD_END_WITHOUT_PRINTED_DURATION" in c["hold_reasons"] for c in with_shadow)
    extra = [c for c in shadowed[0].corroboration if c not in plain[0].corroboration]
    assert extra == [
        {"rule": "YEAR_ENDED", "status": "SHADOW_PERIOD_CANDIDATE_NOT_GRANTED", "candidate": "DURATION:YEAR_ENDED:2025-12-31",
         "header_path_exact": ["Năm kết thúc ngày 31/12/2025 Triệu VND"], "lane": "c1", "diagnostic_only": True},
        {"rule": "YEAR_ENDED", "status": "SHADOW_PERIOD_CANDIDATE_NOT_GRANTED", "candidate": "DURATION:YEAR_ENDED:2024-12-31",
         "header_path_exact": ["Năm kết thúc\nngày 31/12/2024\nTriệu VND"], "lane": "c2", "diagnostic_only": True}]
    assert not any(c.get("status") == "EXACT" for c in shadowed[0].corroboration)  # the agreeing amount chose nothing


def test_year_ended_shadow_grammar_is_finite(family):
    # Positive: a printed non-calendar year end stays as printed. Negatives: a bare end date, "kỳ kết thúc" (no grain),
    # two dates, and a lane already resolved by its own printed quarter record nothing.
    headers = [("31/12/2025",), ("Kỳ kết thúc ngày 31/12/2025",), ("Năm kết thúc ngày 31/12/2025 và 31/12/2024",),
               ("Năm kết thúc ngày 30/06/2025",), ("Quý 4/2025",), ("Cho năm tài chính kết thúc ngày 31.12.2025",)]
    from dataclasses import replace
    table = make_table(RECON[:1], headers)
    lanes = resolve_duration_lanes_v1(table, replace(document(quarter=4), income_context_texts=INTERIM_Q4), [], [table.table_title])
    assert [[e["candidate"] for e in lane.shadow_evidence] for lane in lanes] == [
        [], [], [], ["DURATION:YEAR_ENDED:2025-06-30"], [], ["DURATION:YEAR_ENDED:2025-12-31"]]
    assert lanes[4].period_key == "DURATION:QUARTER:4:2025" and all(lane.period_key is None for lane in lanes[:4])
