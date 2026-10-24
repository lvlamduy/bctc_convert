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
from test_notes_expense_families import bridged, link
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


@pytest.mark.parametrize("unread,total", [
    (0, ("211", "187")),   # Codex 0302: BEFORE the first recognized term; the remaining terms sum to the total
    (12, ("219", "195")),  # between terms; the remaining terms sum to the total here too
])
def test_an_unaccounted_valued_row_before_the_total_refuses_it(family, unread, total):
    # The equation span starts at its first recognized term, so only the complete pre-total population guard keeps an
    # unread top-level component from being ignored. Refused, the table is exactly the pre-T table: nothing is
    # accepted through T and nothing accepted before is lost.
    table = lpb_like(total=total)
    table.rows[unread] = replace(table.rows[unread], label="Chi phí chưa có quy tắc dòng")  # valued, no line rule
    assigned = roles(table, family)
    assert assigned[unread].disposition == "SOURCE_ONLY" and assigned[14].disposition == "SOURCE_ONLY"
    assert unlabeled_total_row_v1(table, family, assigned, owned_subject=True) == (
        None, f"UNACCOUNTED_VALUED_ROW_BEFORE_TOTAL:r{unread}")
    [evaluation] = evaluate(table, family)
    assert not any(e["name"] == "TOTAL_FROM_TOP_LEVEL_LINES" for e in evaluation.equations)
    result = cells([evaluation])
    assert ("TOTAL_OPERATING_EXPENSE", YEAR) not in result
    assert result[("EMPLOYEE_EXPENSE", YEAR)]["acceptance"] == "ACCEPTED"
    assert "LINE_NOT_PROVEN_BY_ITS_OWN_EQUATION_OR_ANCHOR" in result[("ASSET_EXPENSE", YEAR)]["hold_reasons"]


def lpb_wrapped(bridge=True):
    """LPB's actual layout: each group prints a value-less "Trong đó:" GROUP row, and the unread admin detail
    "Chi phí khác cho hoạt động quản lý" hangs under that wrapper (ORIGINAL r14 -> r17), not under ADMIN itself."""

    rows = [
        ("Chi nộp thuế và các khoản phí, lệ phí", ["10", "9"]),                    # 0 TAX_FEES
        ("Chi phí cho nhân viên", ["100", "90"]),                                   # 1 EMPLOYEE
        ("Trong đó:", [None, None]),                                                # 2 wrapper of 1
        ("Chi lương và phụ cấp", ["80", "70"]),                                     # 3
        ("Chi trợ cấp thôi việc", ["15", "14"]),                                    # 4
        ("Chi phí khác cho nhân viên", ["5", "6"]),                                 # 5
        ("Chi về tài sản", ["50", "40"]),                                           # 6 ASSET
        ("Trong đó:", [None, None]),                                                # 7 wrapper of 6
        ("Khấu hao tài sản cố định", ["20", "18"]),                                 # 8
        ("Chi phí thuê tài sản", ["30", "22"]),                                     # 9
        ("Chi cho hoạt động quản lý công vụ", ["40", "35"]),                        # 10 ADMIN
        ("Trong đó:", [None, None]),                                                # 11 wrapper of 10
        ("Công tác phí", ["12", "10"]),                                             # 12
        ("Chi phí khác cho hoạt động quản lý", ["28", "25"]),                       # 13 unread detail via wrapper
        ("Chi nộp phí bảo hiểm, bảo hiểm tiền gửi của khách hàng", ["8", "7"]),    # 14 DEPOSIT_INSURANCE
        ("Chi phí dự phòng khác", ["2", "1"]),                                      # 15 OTHER_ASSET_PROVISION
        ("Chi phí hoạt động khác", ["11", "14"]),                                   # 16 OTHER_OPERATING
        ("TOTAL", ["221", "196"]),                                                  # 17 unlabeled printed total
    ]
    table = make_table(rows, [("Năm 2025",), ("Năm 2024",)], title="30. Chi phí hoạt động")
    for wrapper in (2, 7, 11):
        table.rows[wrapper] = replace(table.rows[wrapper], kind="GROUP")
    for child, parent in {2: 1, 3: 2, 4: 2, 5: 2, 7: 6, 8: 7, 9: 7, 11: 10, 12: 11, 13: 11}.items():
        link(table, child, parent)
    table.rows[17] = replace(table.rows[17], label=None, kind="TOTAL", hierarchy=(), hierarchy_raw=[None])
    return bridged(table) if bridge else table


def test_detail_under_a_proven_wrapper_is_accounted_inside_its_owner_never_as_a_component(family):
    table = lpb_wrapped()
    assigned = roles(table, family)
    assert (assigned[13].disposition, assigned[11].disposition) == ("SOURCE_ONLY", "HEADING")
    assert (assigned[17].role, assigned[17].reason) == ("TOTAL_OPERATING_EXPENSE", T_REASON)
    [evaluation] = evaluate(table, family)
    total = {e["lane"]: e for e in evaluation.equations if e["name"] == "TOTAL_FROM_TOP_LEVEL_LINES"}
    for lane in ("c1", "c2"):
        assert total[lane]["status"] == "PASS"
        assert total[lane]["excused_detail_rows"] == [13]  # recorded as ADMIN's printed detail
        assert set(total[lane]["terms"]) == set(TOP)  # the detail row is no term: counted once, inside ADMIN
    result = cells([evaluation])
    for line in [*TOP, "TOTAL_OPERATING_EXPENSE"]:
        assert result[(line, YEAR)]["acceptance"] == "ACCEPTED", (line, result[(line, YEAR)]["hold_reasons"])


def test_without_the_original_axis_proof_a_wrapper_accounts_for_nothing(family):
    # No EXACT single-table bridge: "all wrapper cells null" is not proven, so even the recognized salary line under the
    # first wrapper (r3, a non-root MEMBER) reaches no root-frontier owner.
    table = lpb_wrapped(bridge=False)
    assigned = roles(table, family)
    assert assigned[3].role == "SALARY_ALLOWANCE"
    assert unlabeled_total_row_v1(table, family, assigned, owned_subject=True) == (
        None, "UNACCOUNTED_VALUED_ROW_BEFORE_TOTAL:r3")
    assert assigned[17].disposition == "SOURCE_ONLY"


def _flat_depreciation(table):
    # Codex 0304: amounts unchanged; only the printed parent edge of r6 is removed. "Khấu hao" is still recognized
    # (a MEMBER), but it is not a root term and no longer printed inside ASSET's population.
    table.rows[6] = replace(table.rows[6], parent_row_id=None, hierarchy=(), hierarchy_raw=None)


def _detail_under_a_non_root_line(table):
    link(table, 10, 9)  # the unread admin detail printed under "Công tác phí" (a non-root line), not under ADMIN


def _nested_root_term(table):
    link(table, 11, 8)  # the deposit-insurance root term printed INSIDE the admin group


@pytest.mark.parametrize("mutate,why", [
    (_flat_depreciation, "UNACCOUNTED_VALUED_ROW_BEFORE_TOTAL:r6"),
    (_detail_under_a_non_root_line, "UNACCOUNTED_VALUED_ROW_BEFORE_TOTAL:r10"),
    (_nested_root_term, "ROOT_TERM_NOT_AT_SOURCE_TOP_LEVEL:r11"),
])
def test_recognition_alone_never_places_a_row_in_the_root_population(family, mutate, why):
    table = lpb_like()  # printed totals 221 / 196 unchanged
    mutate(table)
    assigned = roles(table, family)
    assert unlabeled_total_row_v1(table, family, assigned, owned_subject=True) == (None, why)
    assert assigned[14].disposition == "SOURCE_ONLY"
    [evaluation] = evaluate(table, family)
    assert not any(e["name"] == "TOTAL_FROM_TOP_LEVEL_LINES" for e in evaluation.equations)
    assert cells([evaluation])[("EMPLOYEE_EXPENSE", YEAR)]["acceptance"] == "ACCEPTED"


def test_a_labeled_total_keeps_the_immediate_parent_rule_unchanged(family):
    # Outside the T route nothing changes: the same wrapped detail under a PRINTED "Tổng chi phí hoạt động" still
    # blocks the span exactly as before (INCOMPLETE), so other tables and families see no new excuse.
    table = lpb_wrapped()
    table.rows[17] = replace(table.rows[17], label="Tổng chi phí hoạt động", kind="ITEM", hierarchy=(), hierarchy_raw=None)
    assert roles(table, family)[17].reason == "LINE_RULE"
    [evaluation] = evaluate(table, family)
    statuses = {(e["name"], e["lane"]): e["status"] for e in evaluation.equations}
    assert statuses[("TOTAL_FROM_TOP_LEVEL_LINES", "c1")] == "INCOMPLETE_UNREAD_ROWS_IN_SPAN"


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
