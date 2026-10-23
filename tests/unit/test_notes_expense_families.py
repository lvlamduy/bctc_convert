"""Notes engine: F36 operating expense and F37 credit-risk provision expense as CONCEPT_LIST configuration only."""

from __future__ import annotations

from pathlib import Path

import pytest

from bctc_ai.notes.concept_list_shape_v1 import assign_lines_v1, evaluate_concept_table_v1
from bctc_ai.notes.config_v1 import load_notes_config_v1
from bctc_ai.notes.engine_v1 import _assign_legacy_ids
from bctc_ai.notes.kernel_v1 import NoteRow

from test_notes_income_tax import cells, context_of, document, kqkd, make_table

ROOT = Path(__file__).resolve().parents[2]
YEAR = "DURATION:YEAR:2025"
PRIOR = "DURATION:YEAR:2024"


@pytest.fixture(scope="module")
def config():
    return load_notes_config_v1(ROOT)


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
        row = table.rows[child]
        table.rows[child] = NoteRow(row.row_id, row.order, row.label, row.kind, row.hierarchy, f"r{parent}")
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
        row = table.rows[child]
        table.rows[child] = NoteRow(row.row_id, row.order, row.label, row.kind, row.hierarchy, "r0")
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
