"""Notes engine: F36 operating expense and F37 credit-risk provision expense as CONCEPT_LIST configuration only."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from bctc_ai.notes.concept_list_shape_v1 import assign_lines_v1, evaluate_concept_table_v1
from bctc_ai.notes.config_v1 import load_notes_config_v1
from bctc_ai.notes.engine_v1 import _assign_legacy_ids, hold_write_key_collisions_v1
from bctc_ai.notes.kernel_v1 import NoteRow

from test_notes_income_tax import cells, context_of, document, kqkd, make_table

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
    from bctc_ai.notes.engine_v1 import FamilyRun, dispositions_v1
    from bctc_ai.notes.concept_list_shape_v1 import evaluate_concept_table_v1 as evaluate
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
    return table


def test_payroll_reaches_its_owner_through_one_null_trong_do_wrapper(config):
    # Codex 0150: F36 opt-in, literal "Trong đó", one GROUP layer whose original cells are all JSON null.
    family = config.families["OPERATING_EXPENSE"]
    table = _wrapped()
    roles = assign_lines_v1(table, family)
    assert (roles[1].disposition, roles[1].reason) == ("HEADING", "NO_VALUES")  # the wrapper is never a value
    assert (roles[2].role, roles[2].disposition, roles[2].reason) == (
        "PAYROLL_CONTRIBUTIONS", "MEMBER", "LINE_RULE_VIA_TRANSPARENT_WRAPPER:r1")
    assert _roles(_wrapped(wrapper="Trong đó"), family)[2][:2] == ("PAYROLL_CONTRIBUTIONS", "MEMBER")
    # The wrapper does not change the equation: EMPLOYEE = Σ printed detail still uses the payroll line only.
    evaluations = evaluate_concept_table_v1(table, family, document(quarter=4), context_of(table), [])
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
    assert _roles(nested, family)[3][:2] == held
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
