"""Notes engine proposal T (Codex 0292/0296): a printed total row WITHOUT a label closes an operating-expense table.

LPB FULL69 page 64 prints its closing total with no label; the authenticated ORIGINAL row is
{label_exact: null, row_kind: TOTAL, hierarchy_path_exact: [null]} after every top-level line. The row becomes the
family's total by source structure only; TOTAL_FROM_TOP_LEVEL_LINES then validates it (proof, never membership).
Amounts here are synthetic.
"""

from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

import pytest
from test_notes_expense_families import link
from test_notes_income_tax import cells, context_of, document, make_table

from bctc_ai.notes.concept_list_shape_v1 import assign_lines_v1, evaluate_concept_table_v1, unlabeled_total_row_v1
from bctc_ai.notes.config_v1 import NotesConfigError, load_notes_config_v1

ROOT = Path(__file__).resolve().parents[2]
YEAR, PRIOR = "DURATION:YEAR:2025", "DURATION:YEAR:2024"
TOP = ["TAX_FEES", "EMPLOYEE_EXPENSE", "ASSET_EXPENSE", "ADMIN_EXPENSE", "DEPOSIT_INSURANCE_EXPENSE",
       "OTHER_ASSET_PROVISION", "OTHER_OPERATING_EXPENSE"]
T_REASON = "UNLABELED_ORIGINAL_ROW_KIND_TOTAL:NULL_LABEL"


@pytest.fixture(scope="module")
def family():
    return load_notes_config_v1(ROOT).families["OPERATING_EXPENSE"]


def lpb_like(total=("221", "196"), *, label=None, kind="TOTAL"):
    """The LPB page-64 shape: top-level lines, printed detail under three of them, then the unlabeled total."""

    rows = [
        ("Chi nộp thuế và các khoản phí, lệ phí", ["10", "9"]),                    # 0 TAX_FEES
        ("Chi phí cho nhân viên", ["100", "90"]),                                   # 1 EMPLOYEE
        ("Chi lương và phụ cấp", ["80", "70"]),                                     # 2  detail of 1
        ("Chi trợ cấp thôi việc", ["15", "14"]),                                    # 3  detail of 1
        ("Chi phí khác cho nhân viên", ["5", "6"]),                                 # 4  detail of 1
        ("Chi về tài sản", ["50", "40"]),                                           # 5 ASSET
        ("Khấu hao tài sản cố định", ["20", "18"]),                                 # 6  detail of 5
        ("Chi phí thuê tài sản", ["30", "22"]),                                     # 7  detail of 5
        ("Chi cho hoạt động quản lý công vụ", ["40", "35"]),                        # 8 ADMIN
        ("Công tác phí", ["12", "10"]),                                             # 9  detail of 8
        ("Chi phí khác cho hoạt động quản lý", ["28", "25"]),                       # 10 detail of 8 (no line rule)
        ("Chi nộp phí bảo hiểm, bảo hiểm tiền gửi của khách hàng", ["8", "7"]),    # 11 DEPOSIT_INSURANCE
        ("Chi phí dự phòng khác", ["2", "1"]),                                      # 12 OTHER_ASSET_PROVISION
        ("Chi phí hoạt động khác", ["11", "14"]),                                   # 13 OTHER_OPERATING
        ("TOTAL", list(total)),                                                     # 14 the printed total
    ]
    table = make_table(rows, [("Năm 2025",), ("Năm 2024",)], title="30. Chi phí hoạt động")
    for child, parent in {2: 1, 3: 1, 4: 1, 6: 5, 7: 5, 9: 8, 10: 8}.items():
        link(table, child, parent)
    table.rows[14] = replace(table.rows[14], label=label, kind=kind, hierarchy=(), hierarchy_raw=[None])
    return table


def roles(table, family, owned=True):
    return assign_lines_v1(table, family, owned_subject=owned)


def evaluate(table, family):
    return evaluate_concept_table_v1(table, family, document(quarter=4), context_of(table), [])


def test_the_unlabeled_original_total_is_the_family_total_and_closes_the_top_level_equation(family):
    table = lpb_like()
    role = roles(table, family)[14]
    assert (role.role, role.disposition, role.reason) == ("TOTAL_OPERATING_EXPENSE", "MEMBER", T_REASON)
    [evaluation] = evaluate(table, family)
    statuses = {(e["name"], e["lane"]): e["status"] for e in evaluation.equations}
    assert statuses[("TOTAL_FROM_TOP_LEVEL_LINES", "c1")] == statuses[("TOTAL_FROM_TOP_LEVEL_LINES", "c2")] == "PASS"
    result = cells([evaluation])
    for line in [*TOP, "TOTAL_OPERATING_EXPENSE"]:
        for period in (YEAR, PRIOR):
            assert result[(line, period)]["acceptance"] == "ACCEPTED", (line, period, result[(line, period)]["hold_reasons"])
    assert result[("TOTAL_OPERATING_EXPENSE", YEAR)]["value"] == "221"  # the printed string, nothing derived


def test_without_the_source_total_kind_the_top_level_lines_stay_held_exactly_as_before(family):
    # The pre-T behaviour (and LPB's actual 06e result): an unlabeled ITEM row is unread, the total equation is never
    # formed, and every line bound to it stays held for want of its own proof.
    table = lpb_like(kind="ITEM")
    assert (roles(table, family)[14].disposition, roles(table, family)[14].reason) == ("SOURCE_ONLY", "NO_LINE_RULE")
    [evaluation] = evaluate(table, family)
    assert not any(e["name"] == "TOTAL_FROM_TOP_LEVEL_LINES" for e in evaluation.equations)
    result = cells([evaluation])
    for line in ["TAX_FEES", "ASSET_EXPENSE", "ADMIN_EXPENSE", "DEPOSIT_INSURANCE_EXPENSE", "OTHER_ASSET_PROVISION",
                 "OTHER_OPERATING_EXPENSE"]:
        assert "LINE_NOT_PROVEN_BY_ITS_OWN_EQUATION_OR_ANCHOR" in result[(line, YEAR)]["hold_reasons"]
    assert result[("EMPLOYEE_EXPENSE", YEAR)]["acceptance"] == "ACCEPTED"  # its own detail equation


def test_an_empty_string_label_is_kept_apart_from_a_null_label(family):
    assert roles(lpb_like(label=""), family)[14].reason == "UNLABELED_ORIGINAL_ROW_KIND_TOTAL:EMPTY_LABEL"
    assert roles(lpb_like(label="  "), family)[14].reason == "UNLABELED_ORIGINAL_ROW_KIND_TOTAL:EMPTY_LABEL"


def _subtotal(table):
    table.rows[14] = replace(table.rows[14], kind="SUBTOTAL")


def _labeled(table):
    table.rows[14] = replace(table.rows[14], label="Khác")


def _nested(table):
    table.rows[14] = replace(table.rows[14], parent_row_id=table.rows[8].row_id)


def _printed_component(table):
    table.rows[14] = replace(table.rows[14], hierarchy=("Chi cho hoạt động quản lý công vụ",),
                             hierarchy_raw=["Chi cho hoạt động quản lý công vụ"])


def _not_last(table):
    table.rows.append(replace(table.rows[13], row_id="r15", order=15))
    table.cells[("r15", "c1")], table.cells[("r15", "c2")] = ("1", "VALUE"), ("1", "VALUE")


def _two_totals(table):
    table.rows[5] = replace(table.rows[5], kind="TOTAL")


def _no_values(table):
    table.cells[("r14", "c1")], table.cells[("r14", "c2")] = (None, "BLANK"), (None, "BLANK")


def _printed_total_present(table):
    table.rows[13] = replace(table.rows[13], label="Tổng chi phí hoạt động")


@pytest.mark.parametrize("mutate,why", [
    (_subtotal, "TOTAL_KIND_ROWS_0_NOT_ONE"),
    (_labeled, "TOTAL_ROW_PRINTS_A_LABEL"),
    (_nested, "TOTAL_ROW_CLAIMS_A_PARENT"),
    (_printed_component, "TOTAL_ROW_CLAIMS_A_PARENT"),
    (_not_last, "TOTAL_ROW_NOT_THE_LAST_VALUED_ROW"),
    (_two_totals, "TOTAL_KIND_ROWS_2_NOT_ONE"),
    (_no_values, "TOTAL_ROW_HAS_NO_VALUES"),
    (_printed_total_present, "PRINTED_TOTAL_LINE_ALREADY_PRESENT"),
])
def test_every_structural_condition_is_required(family, mutate, why):
    table = lpb_like()
    mutate(table)
    assigned = roles(table, family)
    assert unlabeled_total_row_v1(table, family, assigned, owned_subject=True) == (None, why)
    assert not any(role.reason.startswith("UNLABELED_ORIGINAL_ROW_KIND_TOTAL") for role in assigned)


def test_no_grant_without_the_subject_in_the_tables_own_context_or_the_family_opt_in(family):
    table = lpb_like()
    assert unlabeled_total_row_v1(table, family, roles(table, family, owned=False), owned_subject=False) == (
        None, "SUBJECT_NOT_IN_OWN_CONTEXT")
    assert roles(table, family, owned=False)[14].disposition == "SOURCE_ONLY"
    plain = replace(family, raw={k: v for k, v in family.raw.items() if k != "unlabeled_total_line"})
    assert unlabeled_total_row_v1(table, plain, roles(table, plain), owned_subject=True) == (None, "NOT_OPTED_IN")
    others = load_notes_config_v1(ROOT).families
    assert [name for name, f in others.items() if f.raw.get("unlabeled_total_line")] == ["OPERATING_EXPENSE"]


def test_a_total_that_differs_from_its_lines_holds_them_and_loses_the_employee_acceptance(family):
    # Cascade (counted in both directions): a FAIL holds every line of the equation, including EMPLOYEE_EXPENSE,
    # which its own detail equation accepts without T. No amount is changed, chosen or backsolved.
    [evaluation] = evaluate(lpb_like(total=("222", "196")), family)
    statuses = {(e["name"], e["lane"]): e["status"] for e in evaluation.equations}
    assert statuses[("TOTAL_FROM_TOP_LEVEL_LINES", "c1")] == "FAIL" and statuses[("TOTAL_FROM_TOP_LEVEL_LINES", "c2")] == "PASS"
    result = cells([evaluation])
    for line in [*TOP, "TOTAL_OPERATING_EXPENSE"]:
        assert "VALIDATION_FAIL" in result[(line, YEAR)]["hold_reasons"], line
        assert result[(line, PRIOR)]["acceptance"] == "ACCEPTED", line
    assert result[("SALARY_ALLOWANCE", YEAR)]["acceptance"] == "ACCEPTED"  # not a term of the failing equation


def test_an_unread_top_level_row_inside_the_span_leaves_the_equation_incomplete(family):
    table = lpb_like()
    row = table.rows[12]
    table.rows[12] = replace(row, label="Chi phí chưa có quy tắc dòng")  # a valued top-level row with no line rule
    [evaluation] = evaluate(table, family)
    statuses = {(e["name"], e["lane"]): e["status"] for e in evaluation.equations}
    assert statuses[("TOTAL_FROM_TOP_LEVEL_LINES", "c1")] == "INCOMPLETE_UNREAD_ROWS_IN_SPAN"
    result = cells([evaluation])
    assert "EQUATION_SPAN_HAS_UNREAD_ROWS" in result[("EMPLOYEE_EXPENSE", YEAR)]["hold_reasons"]
    assert result[("TOTAL_OPERATING_EXPENSE", YEAR)]["acceptance"] == "HOLD"


@pytest.mark.parametrize("line", ["RENT_EXPENSE", "NOT_A_LINE", "EMPLOYEE_EXPENSE"])
def test_the_opt_in_must_name_the_familys_emitted_root_total(tmp_path, line):
    # RENT is emitted but no equation's target; NOT_A_LINE is no axis member; EMPLOYEE is an equation target but also a
    # term of the total equation, so it is no root total. The shipped TOTAL_OPERATING_EXPENSE loads (fixture above).
    shutil.copytree(ROOT / "config" / "notes", tmp_path / "config" / "notes")
    path = tmp_path / "config" / "notes" / "families" / "operating_expense_v1.yaml"
    text = path.read_text(encoding="utf-8")
    assert text.count("unlabeled_total_line: TOTAL_OPERATING_EXPENSE") == 1
    path.write_text(text.replace("unlabeled_total_line: TOTAL_OPERATING_EXPENSE", f"unlabeled_total_line: {line}"),
                    encoding="utf-8")
    with pytest.raises(NotesConfigError, match="unlabeled_total_line"):
        load_notes_config_v1(tmp_path)
