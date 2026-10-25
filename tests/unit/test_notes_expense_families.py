"""Notes engine: F36 operating expense and F37 credit-risk provision expense as CONCEPT_LIST configuration only."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from test_notes_income_tax import cells, context_of, document, kqkd, make_table

from bctc_ai.notes.concept_list_shape_v1 import assign_lines_v1, evaluate_concept_table_v1
from bctc_ai.notes.config_v1 import load_notes_config_v1
from bctc_ai.notes.engine_v1 import _assign_legacy_ids, hold_write_key_collisions_v1
from bctc_ai.notes.kernel_v1 import NoteRow

ROOT = Path(__file__).resolve().parents[2]
YEAR = "DURATION:YEAR:2025"
PRIOR = "DURATION:YEAR:2024"


@pytest.fixture(scope="module")
def config():
    return load_notes_config_v1(ROOT)


def link(table, child, parent):
    """Print ``child`` under ``parent`` as the source does: parent_row_id plus the raw hierarchy path."""

    owner = table.rows[parent]
    if not owner.hierarchy:
        owner = table.rows[parent] = replace(owner, hierarchy=(owner.label,))
    row = table.rows[child]
    table.rows[child] = replace(row, hierarchy=(*owner.hierarchy, row.label), parent_row_id=owner.row_id)


def opex_table():
    rows = [
        ("Chi nộp thuế và các khoản phí, lệ phí", ["10", "9"]),
        ("Chi phí cho nhân viên", ["100", "90"]),
        ("Chi lương và phụ cấp", ["80", "70"]),
        ("Các khoản chi đóng góp theo lương", ["15", "14"]),
        ("Chi khác", ["5", "6"]),
        ("Chi về tài sản", ["50", "40"]),
        ("Trong đó: Chi phí khấu hao tài sản cố định", ["20", "18"]),
        ("Chi thuê văn phòng và tài sản", ["30", "22"]),
        ("Chi cho hoạt động quản lý công vụ", ["40", "35"]),
        ("Chi quảng cáo, tiếp thị", ["12", "10"]),
        ("Chi khác", ["28", "25"]),
        ("Chi nộp phí bảo hiểm, bảo toàn tiền gửi của khách hàng", ["8", "7"]),
        ("Tổng chi phí hoạt động", ["208", "181"]),
    ]
    table = make_table(rows, [("Năm 2025",), ("Năm 2024",)], title="30. Chi phí hoạt động")
    parents = {2: 1, 3: 1, 4: 1, 6: 5, 7: 5, 9: 8, 10: 8}  # child row -> printed parent row
    for child, parent in parents.items():
        link(table, child, parent)
    return table


def test_bare_other_line_follows_its_printed_parent_only(config):
    family = config.families["OPERATING_EXPENSE"]
    lines = [(r.role, r.disposition) for r in assign_lines_v1(opex_table(), family)]
    assert lines[4] == ("OTHER_EMPLOYEE_EXPENSE", "MEMBER")
    assert lines[10] == ("OTHER_ADMIN_EXPENSE", "MEMBER")
    assert lines[7] == ("RENT_EXPENSE", "MEMBER") and lines[0] == ("TAX_FEES", "MEMBER")
    unparented = opex_table()
    row = unparented.rows[10]
    unparented.rows[10] = NoteRow(row.row_id, row.order, row.label, row.kind, (), None)
    assert assign_lines_v1(unparented, family)[10].disposition == "SOURCE_ONLY"  # never by position


def test_operating_expense_accepted_by_income_statement_total_and_legacy_ids(config):
    family = config.families["OPERATING_EXPENSE"]
    table = opex_table()
    primary = kqkd({"DURATION:YEAR:2025": {"OPEX": "208"}})
    evaluations = evaluate_concept_table_v1(table, family, document(quarter=4, primary=primary), context_of(table), [])
    result = cells(evaluations)
    assert result[("TOTAL_OPERATING_EXPENSE", YEAR)]["acceptance"] == "ACCEPTED"
    assert result[("RENT_EXPENSE", YEAR)]["value"] == "30"
    # Prior lane: no income-statement cell, but the employee group sums its printed detail.
    assert result[("SALARY_ALLOWANCE", PRIOR)]["acceptance"] == "ACCEPTED"
    flat = [c for e in evaluations for c in e.cells]
    _assign_legacy_ids(flat, config)
    ids = {c["member"]: c["report_norm_id"] for c in flat if c["period_key"] == YEAR}
    assert ids["TOTAL_OPERATING_EXPENSE"] == 1205 and ids["OTHER_EMPLOYEE_EXPENSE"] == 1211
    assert ids["RENT_EXPENSE"] is None  # comparable across banks, no legacy row


def test_credit_provision_general_and_specific_need_a_printed_subject_parent(config):
    family = config.families["CREDIT_PROVISION_EXPENSE"]
    rows = [("Chi phí dự phòng rủi ro cho vay khách hàng", ["300", "250"]), ("Dự phòng chung", ["20", "10"]),
            ("Dự phòng cụ thể", ["280", "240"]), ("Trích lập dự phòng trái phiếu đặc biệt VAMC", ["40", "50"]),
            ("Hoàn nhập dự phòng rủi ro cho các cam kết ngoại bảng", ["(5)", "(2)"]), ("Tổng cộng", ["335", "298"])]
    table = make_table(rows, [("Năm 2025",), ("Năm 2024",)], title="29. Chi phí dự phòng rủi ro tín dụng")
    for child in (1, 2):
        link(table, child, 0)
    lines = [r.role for r in assign_lines_v1(table, family)]
    assert lines == ["CUSTOMER_PROVISION", "CUSTOMER_GENERAL", "CUSTOMER_SPECIFIC", "VAMC_PROVISION",
                     "OFF_BALANCE_PROVISION", "TOTAL_CREDIT_PROVISION"]
    result = cells(evaluate_concept_table_v1(table, family, document(quarter=4), context_of(table), []))
    assert result[("OFF_BALANCE_PROVISION", YEAR)]["value"] == "-5"  # sign as printed
    assert result[("TOTAL_CREDIT_PROVISION", YEAR)]["acceptance"] == "ACCEPTED"  # 300 + 40 - 5 = 335


def test_dispositions_keep_rejected_tables_and_unread_rows():
    from bctc_ai.notes.concept_list_shape_v1 import evaluate_concept_table_v1 as evaluate
    from bctc_ai.notes.engine_v1 import FamilyRun, dispositions_v1
    family = load_notes_config_v1(ROOT).families["OPERATING_EXPENSE"]
    table = opex_table()
    run = FamilyRun("OPERATING_EXPENSE")
    run.evaluations = evaluate(table, family, document(quarter=4), context_of(table), [])
    budget = make_table([("Chi lương", ["1", "1"])], [("Năm 2025",), ("Năm 2024",)], title="Tình hình thu nhập của cán bộ")
    run.evaluations += evaluate(budget, family, document(quarter=4), context_of(budget), [])
    records = dispositions_v1(run)
    assert [r["status"] for r in records] == ["EVALUATED", "REJECTED"]
    assert records[1]["reasons"] and records[1]["rows"] == []
    assert {row["disposition"] for row in records[0]["rows"]} >= {"MEMBER"}
    assert all({"row_id", "label_exact", "parent_row_id", "line", "disposition", "reason"} <= set(row) for row in records[0]["rows"])


def _roles(table, family):
    return [(r.role, r.disposition, r.reason) for r in assign_lines_v1(table, family)]


def test_payroll_contributions_need_their_proven_employee_owner(config):
    family = config.families["OPERATING_EXPENSE"]
    assert _roles(opex_table(), family)[3][:2] == ("PAYROLL_CONTRIBUTIONS", "MEMBER")
    payroll = "Các khoản chi đóng góp theo lương"
    # Missing owner (top level), owner claimed but not proven by the raw path, owner printed after it.
    top = opex_table()
    top.rows[3] = replace(top.rows[3], hierarchy=(), parent_row_id=None)
    unproven = opex_table()
    unproven.rows[3] = replace(unproven.rows[3], hierarchy=())
    later = make_table([(payroll, ["15", "14"]), ("Chi phí cho nhân viên", ["100", "90"])], [("Năm 2025",), ("Năm 2024",)],
                       title="30. Chi phí hoạt động")
    later.rows[1] = replace(later.rows[1], hierarchy=("Chi phí cho nhân viên",))
    later.rows[0] = replace(later.rows[0], hierarchy=("Chi phí cho nhân viên", payroll), parent_row_id="r1")
    for table, index, reason in ((top, 3, "NO_PRINTED_PARENT"), (unproven, 3, "RAW_HIERARCHY_PATH_DOES_NOT_PROVE_PARENT"),
                                 (later, 0, "PARENT_PRINTED_AFTER_CHILD")):
        assert _roles(table, family)[index] == (None, "SOURCE_ONLY", "OWNER_NOT_PROVEN:" + reason)
    # Wrong, ambiguous or unknown owner line.
    for owner, reason in (("Chi về tài sản", "PARENT_LINE_ASSET_EXPENSE"),
                          ("Chi phí cho nhân viên và chi về tài sản", "PARENT_LINE_AMBIGUOUS"),
                          ("Nội dung khác nhau", "PARENT_IS_NOT_A_LINE")):
        table = make_table([(owner, ["50", "40"]), (payroll, ["15", "14"])], [("Năm 2025",), ("Năm 2024",)],
                           title="30. Chi phí hoạt động")
        link(table, 1, 0)
        assert _roles(table, family)[1] == (None, "SOURCE_ONLY", "OWNER_NOT_PROVEN:" + reason)
    # An income-statement total equal to the printed values cannot grant the role.
    evaluations = evaluate_concept_table_v1(top, family, document(quarter=4, primary=kqkd({YEAR: {"OPEX": "208"}})),
                                            context_of(top), [])
    assert not [c for e in evaluations for c in e.cells if c["member"] == "PAYROLL_CONTRIBUTIONS"]


def test_credit_provision_general_and_specific_reject_missing_ambiguous_or_crossed_parents(config):
    family = config.families["CREDIT_PROVISION_EXPENSE"]
    headers, title = [("Năm 2025",), ("Năm 2024",)], "29. Chi phí dự phòng rủi ro tín dụng"
    missing = make_table([("Chi phí dự phòng rủi ro cho vay khách hàng", ["300", "250"]), ("Dự phòng chung", ["20", "10"])],
                         headers, title=title)
    assert _roles(missing, family)[1][:2] == (None, "SOURCE_ONLY")  # no printed parent: never by position
    for owner, expected in (("Dự phòng cho vay khách hàng và cam kết", None),       # ambiguous owner
                            ("Dự phòng các cam kết ngoại bảng", None),             # crossed subject
                            ("Dự phòng tiền gửi và cho vay các TCTD khác", "INTERBANK_GENERAL"),
                            ("Chi phí dự phòng rủi ro cho vay khách hàng", "CUSTOMER_GENERAL")):
        table = make_table([(owner, ["300", "250"]), ("Dự phòng chung", ["20", "10"])], headers, title=title)
        link(table, 1, 0)
        assert _roles(table, family)[1][0] == expected, owner
    # A parent id without the raw hierarchy proof is not an owner either.
    claimed = make_table([("Chi phí dự phòng rủi ro cho vay khách hàng", ["300", "250"]), ("Dự phòng chung", ["20", "10"])],
                         headers, title=title)
    claimed.rows[1] = replace(claimed.rows[1], parent_row_id="r0")
    assert _roles(claimed, family)[1][:2] == (None, "SOURCE_ONLY")


CUSTOMER_LINES = {"CUSTOMER_PROVISION", "CUSTOMER_GENERAL", "CUSTOMER_SPECIFIC"}


def test_stock_or_movement_rows_and_their_children_are_never_credit_provision_lines(config):
    # Codex 0199: a closing balance 300 = chung 20 + cụ thể 280 passes the components arithmetic, but a stock is not
    # the expense 6031/1224/1225; the family title does not establish each row's flow basis.
    family = config.families["CREDIT_PROVISION_EXPENSE"]
    headers, title = [("Năm 2025",), ("Năm 2024",)], "29. Chi phí dự phòng rủi ro tín dụng"
    rows = [("Số dư dự phòng cho vay khách hàng cuối kỳ", ["300", "250"]), ("Dự phòng chung", ["20", "10"]),
            ("Dự phòng cụ thể", ["280", "240"]), ("Trích lập dự phòng trái phiếu đặc biệt VAMC", ["40", "50"]),
            ("Tổng cộng", ["340", "300"])]
    table = make_table(rows, headers, title=title)
    for child in (1, 2):
        link(table, child, 0)
    roles = _roles(table, family)
    assert roles[0] == (None, "SOURCE_ONLY", "ROW_VETO:STOCK_OR_MOVEMENT_BASIS")
    assert roles[1][:2] == roles[2][:2] == (None, "SOURCE_ONLY")  # a vetoed row is no parent of a scoped line
    result = cells(evaluate_concept_table_v1(table, family, document(quarter=4), context_of(table), []))
    assert not {member for member, _period in result} & CUSTOMER_LINES
    assert result.get(("TOTAL_CREDIT_PROVISION", YEAR), {}).get("acceptance") != "ACCEPTED"
    for label in ("Dự phòng cho vay khách hàng đầu kỳ", "Sử dụng dự phòng cho vay khách hàng",
                  "Chênh lệch tỷ giá dự phòng cho vay khách hàng", "Biến động dự phòng cho vay khách hàng"):
        assert _roles(make_table([(label, ["1", "1"])], headers, title=title), family)[0] == (
            None, "SOURCE_ONLY", "ROW_VETO:STOCK_OR_MOVEMENT_BASIS"), label
    # Genuine charges and reversals keep their line and their printed sign.
    for label in ("Trích lập dự phòng cho vay khách hàng", "Hoàn nhập dự phòng cho vay khách hàng",
                  "Chi phí dự phòng rủi ro cho vay khách hàng trong kỳ"):
        assert _roles(make_table([(label, ["(5)", "1"])], headers, title=title), family)[0][:2] == (
            "CUSTOMER_PROVISION", "MEMBER"), label


def test_explicit_non_credit_population_never_closes_a_credit_total(config):
    # Codex 0199: "Chi phí dự phòng khác cho tài sản cố định" 5 must not become OTHER_PROVISION to close 305 = 300 + 5.
    family = config.families["CREDIT_PROVISION_EXPENSE"]
    headers, title = [("Năm 2025",), ("Năm 2024",)], "29. Chi phí dự phòng rủi ro tín dụng"
    rows = [("Chi phí dự phòng rủi ro cho vay khách hàng", ["300", "250"]),
            ("Chi phí dự phòng khác cho tài sản cố định", ["5", "4"]), ("Tổng cộng", ["305", "254"])]
    table = make_table(rows, headers, title=title)
    assert _roles(table, family)[1] == (None, "SOURCE_ONLY", "ROW_VETO:NON_CREDIT_ASSET_POPULATION")
    result = cells(evaluate_concept_table_v1(table, family, document(quarter=4), context_of(table), []))
    assert ("OTHER_PROVISION", YEAR) not in result
    assert all(result[(line, YEAR)]["acceptance"] != "ACCEPTED" for line in ("TOTAL_CREDIT_PROVISION", "CUSTOMER_PROVISION")
               if (line, YEAR) in result)
    # An explicit credit population of "other provision" reads on its own.
    explicit = make_table([("Dự phòng tài sản Có khác", ["5", "4"])], headers, title=title)
    assert _roles(explicit, family)[0][:2] == ("OTHER_PROVISION", "MEMBER")


def test_a_contextual_child_of_a_population_held_line_is_held_with_it(config):
    # Codex 0208: bare "Dự phòng chung / cụ thể" read only under the customer line depend on its population; when a
    # foreign row claiming that parent holds the customer line, 300 = 20 + 280 cannot keep the bare children accepted.
    family = config.families["CREDIT_PROVISION_EXPENSE"]
    headers, title = [("Năm 2025",), ("Năm 2024",)], "29. Chi phí dự phòng rủi ro tín dụng"
    customer, total = ("Chi phí dự phòng rủi ro cho vay khách hàng", ["300", "250"]), ("Tổng cộng", ["305", "254"])
    general, specific = ("Dự phòng chung", ["20", "10"]), ("Dự phòng cụ thể", ["280", "240"])
    bare = make_table([customer, general, specific, ("Chi phí dự phòng khác cho tài sản cố định", ["5", "4"]), total],
                      headers, title=title)
    for child in (1, 2, 3):
        link(bare, child, 0)
    result, _exact = _anchored(bare, family, "305", "254")
    for line in ("CUSTOMER_PROVISION", "CUSTOMER_GENERAL", "CUSTOMER_SPECIFIC"):
        assert result[(line, YEAR)]["acceptance"] == "HOLD"
        assert "POPULATION_MAY_INCLUDE_VETOED_ROW" in result[(line, YEAR)]["hold_reasons"], line
    # The same bare children under a clean customer line keep their proof (no amount decides the dependency).
    clean = make_table([customer, general, specific, ("Trích lập dự phòng trái phiếu đặc biệt VAMC", ["5", "4"]), total],
                       headers, title=title)
    for child in (1, 2):
        link(clean, child, 0)
    result, _exact = _anchored(clean, family, "305", "254")
    assert all(result[(line, period)]["acceptance"] == "ACCEPTED" for line in CUSTOMER_LINES for period in (YEAR, PRIOR))


def test_bare_other_provision_needs_the_subject_of_the_tables_own_context(config):
    # Codex 0203: bare "Dự phòng khác" prints no population; only a positively proven flow/credit owner (the family
    # subject in the table's OWN context) admits it - never arithmetic, a preceding heading or the anchor lines alone.
    family = config.families["CREDIT_PROVISION_EXPENSE"]
    headers = [("Năm 2025",), ("Năm 2024",)]
    rows = [("Chi phí dự phòng rủi ro cho vay khách hàng", ["300", "250"]), ("Trích lập dự phòng trái phiếu đặc biệt VAMC", ["40", "50"]),
            ("Chi phí dự phòng khác", ["5", "4"]), ("Tổng cộng", ["345", "304"])]
    owned = make_table(rows, headers, title="29. Chi phí dự phòng rủi ro tín dụng")
    roles = assign_lines_v1(owned, family, owned_subject=True)
    assert (roles[2].role, roles[2].disposition) == ("OTHER_PROVISION", "MEMBER")
    result = cells(evaluate_concept_table_v1(owned, family, document(quarter=4), context_of(owned), []))
    assert result[("OTHER_PROVISION", YEAR)]["acceptance"] == "ACCEPTED"  # 300 + 40 + 5 = 345, own population owned
    assert _roles(owned, family)[2] == (None, "SOURCE_ONLY", "OWNER_NOT_PROVEN:NO_OWNED_FLOW_SUBJECT")  # default: not owned
    # No owned subject: the table is admitted by its anchor lines only, or the subject is only a preceding heading.
    untitled = make_table(rows, headers, title="", section="")
    for context in ([], [("PRECEDING_NOTE_HEADING", "29. Chi phí dự phòng rủi ro tín dụng")]):
        evaluations = evaluate_concept_table_v1(untitled, family, document(quarter=4), context, [])
        assert [(r.role, r.reason) for r in evaluations[0].roles][2] == (None, "OWNER_NOT_PROVEN:NO_OWNED_FLOW_SUBJECT")
        assert ("OTHER_PROVISION", YEAR) not in cells(evaluations), context


def _anchored(table, family, year_value, prior_value):
    evaluations = evaluate_concept_table_v1(
        table, family, document(quarter=4, primary=kqkd({YEAR: {"PROVISION": year_value}, PRIOR: {"PROVISION": prior_value}})),
        context_of(table), [])
    exact = {(c["line"], c["period_key"]) for e in evaluations for c in e.corroboration if c["status"] == "EXACT"}
    return cells(evaluations), exact


def test_an_exact_income_statement_anchor_never_accepts_a_total_containing_a_vetoed_row(config):
    # Codex 0203: the vetoed row leaves one term, the top-level equation is skipped before any span check, and an
    # exact KQKD 4392 equal to the printed total would otherwise accept the generic total with the foreign population.
    family = config.families["CREDIT_PROVISION_EXPENSE"]
    headers, title = [("Năm 2025",), ("Năm 2024",)], "29. Chi phí dự phòng rủi ro tín dụng"
    customer, foreign = ("Chi phí dự phòng rủi ro cho vay khách hàng", ["300", "250"]), ("Chi phí dự phòng khác cho tài sản cố định", ["5", "4"])
    general, specific = ("Dự phòng chung cho vay khách hàng", ["20", "10"]), ("Dự phòng cụ thể cho vay khách hàng", ["280", "240"])
    total = ("Tổng cộng", ["305", "254"])
    for rows in ([customer, foreign, total], [customer, total, foreign], [foreign, customer, total]):  # every printed order
        table = make_table(rows, headers, title=title)
        result, exact = _anchored(table, family, "305", "254")
        for period in (YEAR, PRIOR):
            assert ("TOTAL_CREDIT_PROVISION", period) in exact  # the anchor IS exact; it is overridden, not absent
            held = result[("TOTAL_CREDIT_PROVISION", period)]
            assert held["acceptance"] == "HOLD" and "POPULATION_MAY_INCLUDE_VETOED_ROW" in held["hold_reasons"], rows
            assert held["value"] in {"305", "254"}  # stored as printed; nothing is filled or inferred
        assert ("OTHER_PROVISION", YEAR) not in result
    # The stock counterexample of 0199 with an exact 340 / 300 anchor: the total stays held too.
    stock = make_table([("Số dư dự phòng cho vay khách hàng cuối kỳ", ["300", "250"]), ("Dự phòng chung", ["20", "10"]),
                        ("Dự phòng cụ thể", ["280", "240"]), ("Trích lập dự phòng trái phiếu đặc biệt VAMC", ["40", "50"]),
                        ("Tổng cộng", ["340", "300"])], headers, title=title)
    for child in (1, 2):
        link(stock, child, 0)
    result, exact = _anchored(stock, family, "340", "300")
    assert ("TOTAL_CREDIT_PROVISION", YEAR) in exact
    assert "POPULATION_MAY_INCLUDE_VETOED_ROW" in result[("TOTAL_CREDIT_PROVISION", YEAR)]["hold_reasons"]
    assert not {member for member, _period in result} & CUSTOMER_LINES
    # An unrelated line with its own printed population and its own passing equation keeps its proof.
    table = make_table([customer, general, specific, total, foreign], headers, title=title)
    result, _exact = _anchored(table, family, "305", "254")
    assert all(result[(line, YEAR)]["acceptance"] == "ACCEPTED" for line in CUSTOMER_LINES)
    assert result[("TOTAL_CREDIT_PROVISION", YEAR)]["acceptance"] == "HOLD"
    # A foreign row CLAIMING a read line as its parent holds that line (and every line summing it), proven or not.
    claimed = make_table([customer, general, specific, foreign, total], headers, title=title)
    for child in (1, 2, 3):
        link(claimed, child, 0)
    result, _exact = _anchored(claimed, family, "305", "254")
    assert "POPULATION_MAY_INCLUDE_VETOED_ROW" in result[("CUSTOMER_PROVISION", YEAR)]["hold_reasons"]
    assert result[("CUSTOMER_GENERAL", YEAR)]["acceptance"] == "ACCEPTED"  # its own population, its own proof
    # Without any vetoed row the same anchored table is accepted: the hold comes from the foreign row only.
    clean = make_table([customer, ("Trích lập dự phòng trái phiếu đặc biệt VAMC", ["5", "4"]), total], headers, title=title)
    result, _exact = _anchored(clean, family, "305", "254")
    assert result[("TOTAL_CREDIT_PROVISION", YEAR)]["acceptance"] == "ACCEPTED"


def test_write_key_collisions_hold_every_occurrence_even_with_equal_values():
    def cell(member, value, table_id, acceptance="ACCEPTED"):
        return {"acceptance": acceptance, "value": value, "unit": "MILLION_VND", "observation_state": "VALUE",
                "hold_reasons": [], "write_key": ["plan", "SEPARATE", "C", "A", member, "AS_PRESENTED", YEAR],
                "locator": {"physical_page": 3, "section_id": "s1", "table_id": table_id}}
    equal = [cell("M1", "10", "t1"), cell("M1", "10", "t2")]
    different = [cell("M2", "10", "t1"), cell("M2", "11", "t2")]
    single = [cell("M3", "10", "t1"), cell("M3", "10", "t2", acceptance="HOLD")]  # a held occurrence does not collide
    hold_write_key_collisions_v1(equal + different + single)
    assert all(c["acceptance"] == "HOLD" and c["hold_reasons"] == ["WRITE_KEY_COLLISION_EQUAL_VALUES"] for c in equal)
    assert all(c["acceptance"] == "HOLD" and c["hold_reasons"] == ["WRITE_KEY_COLLISION_DIFFERENT_VALUES"] for c in different)
    assert equal[0]["collides_with"] == [equal[1]["locator"]] and equal[1]["collides_with"] == [equal[0]["locator"]]
    assert single[0]["acceptance"] == "ACCEPTED" and not single[0]["hold_reasons"]
    assert not any(c["acceptance"] == "DUPLICATE_IDENTICAL_CONTROL" for c in equal + different + single)


def test_owner_made_ambiguous_by_a_duplicate_population_releases_its_child(config):
    # Codex 0128: two EMPLOYEE rows under distinct coherent raw paths (Khối A / Khối B) are both
    # AMBIGUOUS after duplicate-line resolution, so payroll uniquely linked under A is not read either.
    family = config.families["OPERATING_EXPENSE"]
    rows = [("Khối A", [None, None]), ("Chi phí cho nhân viên", ["100", "90"]), ("Các khoản chi đóng góp theo lương", ["15", "14"]),
            ("Khối B", [None, None]), ("Chi phí cho nhân viên", ["60", "50"])]
    table = make_table(rows, [("Năm 2025",), ("Năm 2024",)], title="30. Chi phí hoạt động")
    for child, parent in ((1, 0), (2, 1), (4, 3)):
        link(table, child, parent)
    roles = _roles(table, family)
    assert roles[1][1] == roles[4][1] == "AMBIGUOUS"
    assert roles[2] == (None, "SOURCE_ONLY", "OWNER_NOT_PROVEN:PARENT_NOT_A_FINAL_MEMBER")
    # No amount equality resolves it: an income-statement total equal to a printed value grants nothing.
    evaluations = evaluate_concept_table_v1(table, family, document(quarter=4, primary=kqkd({YEAR: {"OPEX": "15"}})),
                                            context_of(table), [])
    assert not [c for e in evaluations for c in e.cells if c["member"] == "PAYROLL_CONTRIBUTIONS"]
    # The same layout with one employee population keeps payroll under its unique final MEMBER owner.
    single = make_table(rows[:3], [("Năm 2025",), ("Năm 2024",)], title="30. Chi phí hoạt động")
    for child, parent in ((1, 0), (2, 1)):
        link(single, child, parent)
    assert _roles(single, family)[2][:2] == ("PAYROLL_CONTRIBUTIONS", "MEMBER")


def test_fully_qualified_general_and_specific_labels_read_without_a_parent(config):
    # Codex 0131: a direct, fully qualified label also matching its optional scoped phrase must neither
    # crash nor need a parent; only a member added by the scoped fallback depends on the proven parent.
    family = config.families["CREDIT_PROVISION_EXPENSE"]
    headers, title = [("Năm 2025",), ("Năm 2024",)], "29. Chi phí dự phòng rủi ro tín dụng"
    table = make_table([("Dự phòng chung cho vay khách hàng", ["20", "10"]),
                        ("Dự phòng cụ thể tiền gửi và cho vay các TCTD khác", ["5", "4"]),
                        ("Dự phòng chung", ["7", "6"])], headers, title=title)
    roles = _roles(table, family)
    assert roles[0][:2] == ("CUSTOMER_GENERAL", "MEMBER") and roles[1][:2] == ("INTERBANK_SPECIFIC", "MEMBER")
    assert roles[2][:2] == (None, "SOURCE_ONLY")  # bare scoped label without a parent stays unread
    # Printed under a parent that later becomes AMBIGUOUS, the direct qualified label still reads on its own.
    dup = make_table([("Chi phí dự phòng rủi ro cho vay khách hàng", ["30", "20"]), ("Dự phòng chung cho vay khách hàng", ["20", "10"]),
                      ("Chi phí dự phòng rủi ro cho vay khách hàng", ["31", "21"])], headers, title=title)
    link(dup, 1, 0)
    roles = _roles(dup, family)
    assert roles[0][1] == roles[2][1] == "AMBIGUOUS" and roles[1][:2] == ("CUSTOMER_GENERAL", "MEMBER")


def test_composite_label_matching_several_lines_stays_ambiguous_with_or_without_owner(config):
    # Codex 0151/0152: a missing owner is not evidence selecting the remaining direct meaning.
    family = config.families["OPERATING_EXPENSE"]
    headers, title = [("Năm 2025",), ("Năm 2024",)], "30. Chi phí hoạt động"
    composite = "- Các khoản chi đóng góp theo lương, chi trang phục giao dịch, phương tiện bảo hộ lao động"
    expected = {"PAYROLL_CONTRIBUTIONS", "UNIFORM_EXPENSE"}
    without_owner = make_table([("Chi phí cho nhân viên", ["100", "90"]), (composite, ["15", "14"])], headers, title=title)
    with_owner = make_table([("Chi phí cho nhân viên", ["100", "90"]), (composite, ["15", "14"])], headers, title=title)
    link(with_owner, 1, 0)
    for table in (without_owner, with_owner):
        role = assign_lines_v1(table, family)[1]
        assert (role.role, role.disposition, role.reason) == (None, "AMBIGUOUS", "ROW_MATCHES_SEVERAL_LINES")
        assert set(role.candidates) == expected
    # Single-label controls keep their behaviour: uniform reads on its own, payroll still needs its owner.
    single = make_table([("Chi phí cho nhân viên", ["100", "90"]), ("Chi trang phục giao dịch", ["3", "2"]),
                         ("Các khoản chi đóng góp theo lương", ["15", "14"])], headers, title=title)
    roles = _roles(single, family)
    assert roles[1][:2] == ("UNIFORM_EXPENSE", "MEMBER")
    assert roles[2] == (None, "SOURCE_ONLY", "OWNER_NOT_PROVEN:NO_PRINTED_PARENT")
    link(single, 2, 0)
    assert _roles(single, family)[2][:2] == ("PAYROLL_CONTRIBUTIONS", "MEMBER")
    # Scoped-parent control: a bare "Chi khác" still chooses its scoped meaning only under a proven owner.
    scoped = make_table([("Chi phí cho nhân viên", ["100", "90"]), ("Chi khác", ["5", "6"])], headers, title=title)
    assert _roles(scoped, family)[1][:2] == (None, "SOURCE_ONLY")
    link(scoped, 1, 0)
    assert _roles(scoped, family)[1][:2] == ("OTHER_EMPLOYEE_EXPENSE", "MEMBER")


def _wrapped(wrapper="Trong đó:", wrapper_values=(None, None), wrapper_kind="GROUP", owner="Chi phí cho nhân viên"):
    """owner (r0) -> wrapper (r1) -> payroll (r2), both edges printed as the source does (parent id + raw path)."""

    table = make_table([(owner, ["100", "90"]), (wrapper, list(wrapper_values)),
                        ("Các khoản chi đóng góp theo lương", ["15", "14"])], [("Năm 2025",), ("Năm 2024",)],
                       title="30. Chi phí hoạt động")
    table.rows[1] = replace(table.rows[1], kind=wrapper_kind)
    link(table, 1, 0)
    link(table, 2, 1)
    return bridged(table)


def bridged(table, status="EXACT", column_map=None):
    """Attach a source-bridge proof: EXACT with the identity column map = SQL columns ARE the ORIGINAL axis."""

    columns = sorted(table.columns, key=lambda column: column.ordinal)
    table.bridge = {"status": status, "page_json_version_id": table.page_json_version_id, "section_ordinal": 1,
                    "table_ordinal": 1, "row_count": len(table.rows),
                    "column_map": column_map or {c.column_id: i for i, c in enumerate(columns, 1)}}
    return table


def test_payroll_reaches_its_owner_through_one_null_trong_do_wrapper(config):
    # Codex 0150: F36 opt-in, literal "Trong đó", one GROUP layer whose original cells are all JSON null.
    family = config.families["OPERATING_EXPENSE"]
    table = _wrapped()
    roles = assign_lines_v1(table, family)
    assert (roles[1].disposition, roles[1].reason) == ("HEADING", "NO_VALUES")  # the wrapper is never a value
    assert (roles[2].role, roles[2].disposition, roles[2].reason) == (
        "PAYROLL_CONTRIBUTIONS", "MEMBER", "LINE_RULE_VIA_TRANSPARENT_WRAPPER:r1:ORIGINAL_EXACT_UNSHIFTED_SINGLE_TABLE")
    assert _roles(_wrapped(wrapper="Trong đó"), family)[2][:2] == ("PAYROLL_CONTRIBUTIONS", "MEMBER")
    # Public evaluation under the UNCHANGED table gate (min_emitted_lines = 3): the synthetic table also prints a
    # salary line under the same wrapper, so EMPLOYEE / SALARY / PAYROLL are three emitted lines and the fixed
    # EMPLOYEE_FROM_DETAIL equation has printed detail (100 = 85 + 15; 90 = 76 + 14). Fixture-only (Codex 0160).
    printed = make_table([("Chi phí cho nhân viên", ["100", "90"]), ("Trong đó:", [None, None]),
                          ("Chi lương và phụ cấp", ["85", "76"]), ("Các khoản chi đóng góp theo lương", ["15", "14"])],
                         [("Năm 2025",), ("Năm 2024",)], title="30. Chi phí hoạt động")
    printed.rows[1] = replace(printed.rows[1], kind="GROUP")
    for child, parent in ((1, 0), (2, 1), (3, 1)):
        link(printed, child, parent)
    bridged(printed)
    assert _roles(printed, family)[3][:2] == ("PAYROLL_CONTRIBUTIONS", "MEMBER")
    evaluations = evaluate_concept_table_v1(printed, family, document(quarter=4), context_of(printed), [])
    assert any(c["member"] == "PAYROLL_CONTRIBUTIONS" for e in evaluations for c in e.cells)


def test_wrapper_negatives_never_grant_the_owner(config):
    family = config.families["OPERATING_EXPENSE"]
    held = (None, "SOURCE_ONLY")
    for table in (_wrapped(wrapper_values=("-", None)),             # a printed dash is not a null wrapper cell
                  _wrapped(wrapper_values=("", None)),              # a blank string is not JSON null
                  _wrapped(wrapper_values=("0", None)),             # a number is never a wrapper
                  _wrapped(wrapper_kind="ITEM"),                    # only a GROUP row wraps
                  _wrapped(wrapper="Bao gồm:"),                     # undeclared literal
                  _wrapped(wrapper="Trong đó, chi phí"),            # not the exact literal
                  _wrapped(owner="Chi về tài sản")):                # foreign owner
        assert _roles(table, family)[2][:2] == held
    # Nested wrappers (owner -> Trong đó -> Trong đó -> payroll): one layer only.
    nested = make_table([("Chi phí cho nhân viên", ["100", "90"]), ("Trong đó:", [None, None]), ("Trong đó:", [None, None]),
                         ("Các khoản chi đóng góp theo lương", ["15", "14"])], [("Năm 2025",), ("Năm 2024",)],
                        title="30. Chi phí hoạt động")
    for wrapper in (1, 2):
        nested.rows[wrapper] = replace(nested.rows[wrapper], kind="GROUP")
    link(nested, 1, 0)
    link(nested, 2, 1)
    link(nested, 3, 2)
    assert _roles(bridged(nested), family)[3][:2] == held
    # The wrapper edge must itself be raw-path proven (an id alone is not enough).
    id_only = _wrapped()
    id_only.rows[1] = replace(id_only.rows[1], hierarchy=())
    assert _roles(id_only, family)[2][:2] == held
    # An owner made AMBIGUOUS by a second EMPLOYEE population releases the wrapped child too.
    dup = _wrapped()
    dup.rows.append(replace(dup.rows[0], row_id="r3", order=3))
    for column in dup.columns:
        dup.cells[("r3", column.column_id)] = ("50", "VALUE")
    roles = _roles(dup, family)
    assert roles[2] == (None, "SOURCE_ONLY", "OWNER_NOT_PROVEN:PARENT_NOT_A_FINAL_MEMBER")
    # Opt-in only: a family without transparent_wrappers keeps the immediate-owner rule.
    plain = replace(family, raw={k: v for k, v in family.raw.items() if k != "transparent_wrappers"})
    assert _roles(_wrapped(), plain)[2] == (None, "SOURCE_ONLY", "OWNER_NOT_PROVEN:PARENT_IS_NOT_A_LINE")


def test_wrapper_needs_the_complete_original_value_axis(config):
    # Codex 0155: with a proven TEXT-column shift the SQL row is a projection (the removed original cell may hold
    # "Trong đó:"), so "all SQL cells null" does not prove "every ORIGINAL cell null". Merged tables are excluded too.
    family = config.families["OPERATING_EXPENSE"]
    held = (None, "SOURCE_ONLY")
    assert _roles(_wrapped(), family)[2][:2] == ("PAYROLL_CONTRIBUTIONS", "MEMBER")      # EXACT, identity axis
    shifted = bridged(_wrapped(), status="EXACT_WITH_PROVEN_TEXT_COLUMN_SHIFT", column_map={"c1": 2, "c2": 3})
    no_bridge = _wrapped()
    no_bridge.bridge = None
    partial = bridged(_wrapped(), column_map={"c1": 1})                                 # not the whole SQL axis
    moved = bridged(_wrapped(), column_map={"c1": 2, "c2": 1})                          # not the identity map
    merged = _wrapped()
    merged.fragments = [merged.locator(), {**merged.locator(), "physical_page": 38}]   # continuation domain
    for table in (shifted, no_bridge, partial, moved, merged):
        assert _roles(table, family)[2][:2] == held


def _wrapped_child(child="Chi khác", **kwargs):
    """_wrapped with another printed child label under the same proven wrapper edge."""

    table = _wrapped(**kwargs)
    table.rows[2] = replace(table.rows[2], label=child, hierarchy=(*table.rows[1].hierarchy, child))
    return table


def test_scoped_other_reaches_its_owner_through_one_null_trong_do_wrapper(config):
    # FULL docs 124/125/130/131: "Chi phí cho nhân viên" -> "Trong đó:" -> bare "Chi khác". The scoped phrase looks
    # through exactly the wrapper the owner rule accepts; the wrapper stays a heading, never a value.
    family = config.families["OPERATING_EXPENSE"]
    roles = assign_lines_v1(_wrapped_child(), family)
    assert (roles[1].disposition, roles[1].reason) == ("HEADING", "NO_VALUES")
    assert (roles[2].role, roles[2].disposition, roles[2].reason) == (
        "OTHER_EMPLOYEE_EXPENSE", "MEMBER", "LINE_RULE_VIA_TRANSPARENT_WRAPPER:r1:ORIGINAL_EXACT_UNSHIFTED_SINGLE_TABLE")
    assert roles[2].depends_on == 0
    for label in ("Khác", "Chi phí khác", "Các khoản chi khác"):
        assert _roles(_wrapped_child(label), family)[2][:2] == ("OTHER_EMPLOYEE_EXPENSE", "MEMBER")
    # Under the asset line the same wrapper reads the asset meaning (its own scoped rule), never the employee one.
    assert _roles(_wrapped_child(owner="Chi về tài sản"), family)[2][0] != "OTHER_EMPLOYEE_EXPENSE"


def test_scoped_other_wrapper_negatives_never_grant_the_owner(config):
    family = config.families["OPERATING_EXPENSE"]
    held = (None, "SOURCE_ONLY")
    for kwargs in ({"wrapper_values": ("-", None)}, {"wrapper_values": ("", None)}, {"wrapper_values": ("0", None)},
                   {"wrapper_kind": "ITEM"}, {"wrapper": "Bao gồm:"}, {"wrapper": "Trong đó, chi phí"},
                   {"owner": "Tổng chi phí hoạt động"}):
        assert _roles(_wrapped_child(**kwargs), family)[2][:2] == held, kwargs
    shifted = bridged(_wrapped_child(), status="EXACT_WITH_PROVEN_TEXT_COLUMN_SHIFT", column_map={"c1": 2, "c2": 3})
    merged = _wrapped_child()
    merged.fragments = [merged.locator(), {**merged.locator(), "physical_page": 38}]
    id_only = _wrapped_child()
    id_only.rows[1] = replace(id_only.rows[1], hierarchy=())
    for table in (shifted, merged, id_only):
        assert _roles(table, family)[2][:2] == held
    # A duplicate EMPLOYEE population releases the wrapped scoped child (FINAL MEMBER fixed point).
    dup = _wrapped_child()
    dup.rows.append(replace(dup.rows[0], row_id="r3", order=3))
    for column in dup.columns:
        dup.cells[("r3", column.column_id)] = ("50", "VALUE")
    assert _roles(dup, family)[2] == (None, "SOURCE_ONLY", "OWNER_NOT_PROVEN:PARENT_NOT_A_FINAL_MEMBER")
    plain = replace(family, raw={k: v for k, v in family.raw.items() if k != "transparent_wrappers"})
    assert _roles(_wrapped_child(), plain)[2] == (None, "SOURCE_ONLY", "NO_LINE_RULE")


def test_other_employee_expense_reads_the_printed_staff_label(config):
    # FULL doc 20 prints "Chi khác cho cán bộ, nhân viên"; both phrases are required (never a bare "cán bộ").
    family = config.families["OPERATING_EXPENSE"]
    table = make_table([("Chi phí cho nhân viên", ["100", "90"]), ("Chi khác cho cán bộ, nhân viên", ["5", "6"]),
                        ("Chi cho cán bộ", ["1", "1"])], [("Năm 2025",), ("Năm 2024",)], title="30. Chi phí hoạt động")
    roles = _roles(table, family)
    assert roles[1][:2] == ("OTHER_EMPLOYEE_EXPENSE", "MEMBER")
    assert roles[2][0] != "OTHER_EMPLOYEE_EXPENSE"


def test_document_coverage_separates_observed_unresolved_from_not_observed():
    # Codex 0155/0157: metadata only - FOUND precedence, cells/roles/thresholds untouched.
    from bctc_ai.notes.engine_v1 import COVERAGE_FORMAT, document_coverage_v1
    from bctc_ai.notes.list_shape_v1 import RowRole, TableEvaluation

    def evaluation(ordinal, status, reasons, subject=None):
        table = replace(make_table([("Chi phí cho nhân viên", ["1", "1"])], [("Năm 2025",), ("Năm 2024",)]),
                        document_ordinal=ordinal)
        result = TableEvaluation(table, status, list(reasons), subject=subject)
        result.roles = [RowRole(0, None, "SOURCE_ONLY", "OWNER_NOT_PROVEN:PARENT_NOT_A_FINAL_MEMBER", ["CUSTOMER_GENERAL"])]
        return result

    subject = "OPERATING_EXPENSE_NOTE"
    evaluations = [evaluation(1, "REJECTED", ["ONLY_1_LINES"], subject),          # observed, lines unprovable
                   evaluation(2, "REJECTED", ["ONLY_1_LINES"]),                   # no explicit subject
                   evaluation(3, "REJECTED", ["NO_TITLE_AND_ONLY_1_ANCHOR_LINES"]),
                   evaluation(3, "REJECTED", ["OWNER_CONTEXT_IS_ANOTHER_NOTE"]),
                   evaluation(3, "REJECTED", ["PRIMARY_STATEMENT_PAGE"]),
                   evaluation(4, "EVALUATED", [], subject), evaluation(4, "REJECTED", ["ONLY_1_LINES"], subject),
                   evaluation(5, "REJECTED", ["ONLY_X_LINES"], subject),          # not the finite reason grammar
                   evaluation(5, "REJECTED", ["ONLY_1_LINES", "OTHER"], subject)]
    coverage = document_coverage_v1(evaluations, [], [1, 2, 3, 4, 5, 6], "CONCEPT_LIST")
    assert {k: v["status"] for k, v in coverage.items()} == {
        1: "OBSERVED_UNRESOLVED", 2: "NOT_OBSERVED_AFTER_FULL_RETRIEVAL", 3: "NOT_OBSERVED_AFTER_FULL_RETRIEVAL",
        4: "FOUND", 5: "NOT_OBSERVED_AFTER_FULL_RETRIEVAL", 6: "NOT_OBSERVED_AFTER_FULL_RETRIEVAL"}
    assert all(v["coverage_format"] == COVERAGE_FORMAT for v in coverage.values())
    assert coverage[1]["unresolved_tables"][0]["reasons"] == ["ONLY_1_LINES"]
    assert coverage[1]["unresolved_tables"][0]["subject"] == subject
    assert coverage[1]["unresolved_row_reasons"] == {"OWNER_NOT_PROVEN:PARENT_NOT_A_FINAL_MEMBER": 1}
    assert "unresolved_tables" not in coverage[4] and coverage[4]["evaluated_tables"] == 1
    # Other shapes are unchanged.
    other = document_coverage_v1(evaluations, [], [1], "LIST_BY_AXIS")
    assert other[1]["status"] == "NOT_OBSERVED_AFTER_FULL_RETRIEVAL"


def _kinds(table, kinds):
    """Give the synthetic columns their source value kinds (make_table builds MONEY columns)."""

    table.columns = [replace(column, value_kind=kinds.get(column.column_id, column.value_kind)) for column in table.columns]
    return table


def test_an_own_table_position_schedule_is_not_a_credit_provision_flow(config):
    # Codex 0233/0234 E1 (doc 112 literals): maturity TEXT, rate PERCENT, count COUNT and "Giá trị đầu tư" MONEY with
    # no period word is a bond position schedule; it is REJECTED with its deciding columns, never read as F37 flow.
    family = config.families["CREDIT_PROVISION_EXPENSE"]
    rows = [("Trái phiếu đặc biệt VAMC", ["31/12/2027", "0%", "100", "1.000"]), ("Tổng cộng", [None, None, None, "1.000"])]
    schedule = _kinds(make_table(rows, [("Ngày đáo hạn",), ("Lãi suất",), ("Số lượng trái phiếu",), ("Giá trị đầu tư",)],
                                 title=None, section=None), {"c1": "TEXT", "c2": "PERCENT", "c3": "COUNT"})
    evaluation = evaluate_concept_table_v1(schedule, family, document(quarter=4), [], [])[0]
    assert evaluation.status == "REJECTED"
    assert evaluation.reasons == ["OWN_TABLE_IS_A_POSITION_SCHEDULE:money=c4;schedule=c1,c2,c3"]
    # Positives keep reading: a flow table with a "Thuyết minh" TEXT column (doc 69 C2 shape), a real VAMC / bond
    # provision flow, and a schedule-like table whose MONEY column is a flow measure.
    flow_rows = [("Trích lập dự phòng trái phiếu đặc biệt VAMC", ["7", "40", "50"]),
                 ("Dự phòng trái phiếu doanh nghiệp chưa niêm yết", ["8", "5", "4"]), ("Tổng cộng", [None, "45", "54"])]
    with_note = _kinds(make_table(flow_rows, [("Thuyết minh",), ("Năm 2025",), ("Năm 2024",)],
                                  title="29. Chi phí dự phòng rủi ro tín dụng"), {"c1": "TEXT"})
    evaluations = evaluate_concept_table_v1(with_note, family, document(quarter=4), context_of(with_note), [])
    assert evaluations[0].status == "EVALUATED"
    result = cells(evaluations)
    assert result[("VAMC_PROVISION", YEAR)]["acceptance"] == "ACCEPTED" and result[("CORPORATE_BOND_PROVISION", YEAR)]["value"] == "5"
    rate_flow = _kinds(make_table([("Trích lập dự phòng trái phiếu đặc biệt VAMC", ["5%", "40"]), ("Tổng cộng", [None, "40"])],
                                  [("Tỷ lệ trích lập",), ("Chi phí dự phòng",)], title=None, section=None), {"c1": "PERCENT"})
    assert evaluate_concept_table_v1(rate_flow, family, document(quarter=4), [], [])[0].reasons[:1] != [
        "OWN_TABLE_IS_A_POSITION_SCHEDULE:money=c2;schedule=c1"]


def test_a_position_header_beside_a_flow_money_header_is_not_a_schedule(config):
    # Codex 0236: condition (c) scans EVERY MONEY header. A stock "Giá trị đầu tư" column and a COUNT column next to a
    # second MONEY header printing a flow period ("Chi phí dự phòng năm 2025") is not an own-table position schedule.
    family = config.families["CREDIT_PROVISION_EXPENSE"]
    rows = [("Trích lập dự phòng trái phiếu đặc biệt VAMC", ["100", "1.000", "40"]), ("Tổng cộng", [None, "1.000", "40"])]
    mixed = _kinds(make_table(rows, [("Số lượng trái phiếu",), ("Giá trị đầu tư",), ("Chi phí dự phòng năm 2025",)],
                              title=None, section=None), {"c1": "COUNT"})
    evaluation = evaluate_concept_table_v1(mixed, family, document(quarter=4), [], [])[0]
    assert not any(reason.startswith("OWN_TABLE_IS_A_POSITION_SCHEDULE") for reason in evaluation.reasons)
    # The same columns without the flow MONEY header are the schedule (all three conditions hold).
    stock = _kinds(make_table([(label, values[:2]) for label, values in rows], [("Số lượng trái phiếu",), ("Giá trị đầu tư",)],
                              title=None, section=None), {"c1": "COUNT"})
    assert evaluate_concept_table_v1(stock, family, document(quarter=4), [], [])[0].reasons == [
        "OWN_TABLE_IS_A_POSITION_SCHEDULE:money=c2;schedule=c1"]
