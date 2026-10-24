"""Notes engine: COORDINATE_LIST shape (deposit type x currency; customer entity type) on synthetic tables."""

from __future__ import annotations

from pathlib import Path

import pytest

from bctc_ai.notes.config_v1 import load_notes_config_v1
from bctc_ai.notes.coordinate_shape_v1 import evaluate_coordinate_table_v1
from bctc_ai.notes.kernel_v1 import DocumentContext, NoteColumn, NoteRow, NoteTable
from bctc_ai.primary_statements.numbers_v1 import SeparatorRoles

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def config():
    return load_notes_config_v1(ROOT)


def document(primary=None):
    return DocumentContext(
        ordinal=1, document_plan_id="plan", relative_path="x.pdf", source_sha256="0" * 64, scope="SEPARATE",
        scope_basis="PRIMARY_DOCUMENT_SCOPE", reporting_date="2025-06-30",
        balance_lanes=[{"key": "INSTANT:2025-06-30", "role": "CURRENT", "header": "30/06/2025"},
                       {"key": "INSTANT:2024-12-31", "role": "COMPARATIVE", "header": "31/12/2024"}],
        context_texts=["Tại ngày 30 tháng 6 năm 2025"], primary_cells=primary or {},
        separator_roles=SeparatorRoles(thousands=frozenset({"."})),
    )


def table(rows, *, title="Tiền gửi của khách hàng", section=None, headers=(("30/06/2025", "Triệu VND"), ("31/12/2024", "Triệu VND"))):
    columns = [NoteColumn(f"c{i}", i, tuple(h), "MONEY") for i, h in enumerate(headers, 1)]
    result = NoteTable(1, 20, "v20", "s1", "t1", 0, 0, "FINANCIAL_NOTE", section, title, None, "NONE", [], columns)
    for index, spec in enumerate(rows):
        label, values, kind = spec[0], spec[1], (spec[2] if len(spec) > 2 else None)
        parent = spec[3] if len(spec) > 3 else None
        kind = kind or ("TOTAL" if label in (None, "Tổng", "Cộng") else "ITEM")
        result.rows.append(NoteRow(f"r{index}", index, label, kind, (), parent))
        for column, value in zip(columns, values, strict=False):
            state = "BLANK" if value is None else ("DASH" if value.strip() == "-" else "VALUE")
            result.cells[(f"r{index}", column.column_id)] = (value, state)
    return result


def run(config, family_name, rows, primary=None, **kwargs):
    family = config.families[family_name]
    axes = [config.axes[name] for name in family.raw["axes"]]
    t = table(rows, **kwargs)
    context = [(s, x) for s, x in (("TABLE_TITLE", t.table_title), ("SECTION_TITLE", t.section_title)) if x]
    evaluations = evaluate_coordinate_table_v1(t, family, document(primary), context, [], axes=axes)
    return {(c["member"], c["period_key"]): c for e in evaluations for c in e.cells}, evaluations


def test_nested_currency_rows_inherit_the_open_deposit_type(config):
    rows = [("Tiền gửi không kỳ hạn", ["100", "90"], "SUBTOTAL"), ("Bằng VND", ["60", "50"]), ("Bằng ngoại tệ", ["40", "40"]),
            ("Tiền gửi có kỳ hạn", ["200", "150"], "SUBTOTAL"), ("Bằng VND", ["200", "150"]), ("Tổng", ["300", "240"])]
    cells, _ = run(config, "DEPOSITS_BY_TYPE", rows)
    cell = cells[("DEPOSIT_TYPE=DEMAND;CURRENCY=VND", "INSTANT:2025-06-30")]
    assert cell["value"] == "60" and cell["acceptance"] == "ACCEPTED" and cell["concept"] == "CUSTOMER_DEPOSITS"
    assert cells[("TOTAL", "INSTANT:2024-12-31")]["acceptance"] == "ACCEPTED"


def test_headings_without_values_move_children_to_the_frontier(config):
    rows = [("Tiền gửi không kỳ hạn", [None, None], "GROUP"), ("Tiền gửi không kỳ hạn bằng VND", ["60", "50"]),
            ("Tiền gửi tiết kiệm có kỳ hạn bằng VND", ["240", "190"]), ("Tổng", ["300", "240"])]
    cells, evaluations = run(config, "DEPOSITS_BY_TYPE", rows)
    assert ("DEPOSIT_TYPE=DEMAND", "INSTANT:2025-06-30") not in cells  # a heading is never a value cell
    assert cells[("DEPOSIT_TYPE=SAVINGS_TERM;CURRENCY=VND", "INSTANT:2025-06-30")]["acceptance"] == "ACCEPTED"


def test_parent_child_mismatch_holds_and_never_backsolves(config):
    rows = [("Tiền gửi có kỳ hạn", ["200", "150"], "SUBTOTAL"), ("Bằng VND", ["150", "150"]), ("Bằng ngoại tệ", ["40", "-"]),
            ("Tiền gửi không kỳ hạn", ["100", "90"]), ("Tổng", ["300", "240"])]
    cells, _ = run(config, "DEPOSITS_BY_TYPE", rows)
    assert cells[("DEPOSIT_TYPE=TERM;CURRENCY=VND", "INSTANT:2025-06-30")]["acceptance"] == "HOLD"
    dash = cells[("DEPOSIT_TYPE=TERM;CURRENCY=FOREIGN_CURRENCY", "INSTANT:2024-12-31")]
    assert dash["observation_state"] == "DASH_ZERO" and dash["acceptance"] == "ACCEPTED"


def test_subject_heading_inside_table_starts_a_new_block(config):
    rows = [("Tiền gửi tại các TCTD khác", [None, None], "GROUP"), ("Tiền gửi không kỳ hạn", ["10", "9"]),
            ("Tiền gửi có kỳ hạn", ["20", "19"]), (None, ["30", "28"], "SUBTOTAL"),
            ("Cho vay các TCTD khác", [None, None], "GROUP"), ("Bằng VND", ["5", "4"]), (None, ["35", "32"], "TOTAL")]
    cells, evaluations = run(config, "DEPOSITS_BY_TYPE", rows, title="Tiền gửi và cho vay các TCTD khác")
    assert cells[("DEPOSIT_TYPE=DEMAND", "INSTANT:2025-06-30")]["concept"] == "DEPOSITS_AT_OTHER_CIS"
    assert cells[("CURRENCY=VND", "INSTANT:2025-06-30")]["concept"] == "LOANS_TO_OTHER_CIS"


def test_member_hierarchy_needs_printed_nesting(config):
    flat = [("Tiền gửi của tổ chức kinh tế", ["100", "90"]), ("Công ty cổ phần khác", ["60", "50"]),
            ("Công ty TNHH khác", ["40", "40"]), ("Tiền gửi của cá nhân", ["50", "50"]), ("Cộng", ["150", "140"])]
    cells, _ = run(config, "BY_CUSTOMER_ENTITY_TYPE", flat)
    # Flat list: the organisation row is not proven to be the parent, so the total check fails and holds.
    assert cells[("CUSTOMER_ENTITY_TYPE=JSC_OTHER", "INSTANT:2025-06-30")]["acceptance"] == "HOLD"
    nested = [("Tiền gửi của tổ chức kinh tế", ["100", "90"], "SUBTOTAL"), ("Công ty cổ phần khác", ["60", "50"], None, "r0"),
              ("Công ty TNHH khác", ["40", "40"], None, "r0"), ("Tiền gửi của cá nhân", ["50", "50"]), ("Cộng", ["150", "140"])]
    cells, _ = run(config, "BY_CUSTOMER_ENTITY_TYPE", nested)
    assert cells[("CUSTOMER_ENTITY_TYPE=JSC_OTHER", "INSTANT:2025-06-30")]["acceptance"] == "ACCEPTED"
    assert cells[("TOTAL", "INSTANT:2025-06-30")]["acceptance"] == "ACCEPTED"


def test_folded_co_phan_is_not_a_joint_stock_company(config):
    axis = config.axes["CUSTOMER_ENTITY_TYPE"]
    assert axis.match("cong ty tnhh 2 thanh vien tro len co phan von nha nuoc tren 50") == ["LLC_STATE_OVER_50"]
    assert axis.match("cong ty co phan co hon 50 von nha nuoc") == ["JSC_STATE_OVER_50"]
    assert axis.match("doanh nghiep tu nhan va cong ty hop danh") == ["PRIVATE_AND_PARTNERSHIP"]


def test_savings_term_is_its_own_member_not_term_or_savings(config):
    axis = config.axes["DEPOSIT_TYPE"]
    assert axis.match("tien gui tiet kiem co ky han bang vnd") == ["SAVINGS_TERM"]
    assert axis.match("tien gui khong ky han") == ["DEMAND"]


JUN, DEC = "INSTANT:2025-06-30", "INSTANT:2024-12-31"


def primary_balance(report_norm_id, current, comparative):
    from decimal import Decimal
    return {("CDKT", report_norm_id, JUN): (Decimal(current), "MILLION_VND"),
            ("CDKT", report_norm_id, DEC): (Decimal(comparative), "MILLION_VND")}


def test_an_axis_match_never_erases_the_population_a_deposit_row_prints(config):
    # Codex 0206: "Tiền gửi tại các TCTD …" rows under a customer-deposit title are asset placements, not 1056/1057/1060.
    placements = [("Tiền gửi tại các TCTD không kỳ hạn", ["100", "90"]), ("Tiền gửi tại các TCTD có kỳ hạn", ["200", "150"]),
                  ("Tổng", ["300", "240"])]
    cells, evaluations = run(config, "DEPOSITS_BY_TYPE", placements, primary=primary_balance(4320, "300", "240"))
    assert not [c for c in cells.values() if c["acceptance"] == "ACCEPTED"]
    # Printed after a closed total, the foreign row still holds the table, against an agreeing primary total.
    mixed = [("Tiền gửi không kỳ hạn", ["100", "90"]), ("Tiền gửi có kỳ hạn", ["200", "150"]), ("Tổng", ["300", "240"]),
             ("Tiền gửi tại các TCTD có kỳ hạn", ["50", "40"])]
    cells, evaluations = run(config, "DEPOSITS_BY_TYPE", mixed, primary=primary_balance(4320, "300", "240"))
    assert evaluations[0].rows[3].reason == "ROW_SUBJECT_CONFLICT:DEPOSITS_AT_OTHER_CIS"
    assert any(c["status"] == "AGREES_WITH_PRIMARY" for c in evaluations[0].corroboration)  # overridden, not absent
    for key in ("TOTAL", "DEPOSIT_TYPE=DEMAND", "DEPOSIT_TYPE=TERM"):
        assert cells[(key, JUN)]["acceptance"] == "HOLD"
        assert "TABLE_CONTAINS_ROW_OF_ANOTHER_SUBJECT" in cells[(key, JUN)]["hold_reasons"], key
    # Positives: the same rows without the foreign row, and rows naming the table's own subject.
    cells, _ = run(config, "DEPOSITS_BY_TYPE", mixed[:3], primary=primary_balance(4320, "300", "240"))
    assert cells[("TOTAL", JUN)]["acceptance"] == "ACCEPTED"
    cells, _ = run(config, "DEPOSITS_BY_TYPE", placements, primary=primary_balance(4344, "300", "240"),
                   title="Tiền gửi tại các TCTD khác")
    assert cells[("DEPOSIT_TYPE=DEMAND", JUN)]["acceptance"] == "ACCEPTED"
    assert cells[("DEPOSIT_TYPE=DEMAND", JUN)]["concept"] == "DEPOSITS_AT_OTHER_CIS"


LOANS_TITLE = "Cho vay khách hàng theo loại hình doanh nghiệp"
LOAN_ROWS = [("Công ty TNHH khác", ["10", "9"]), ("Công ty cổ phần khác", ["20", "19"]),
             ("Doanh nghiệp tư nhân và công ty hợp danh", ["30", "29"]), ("Cộng", ["60", "57"])]


def test_deposit_labelled_entity_rows_are_never_loans(config):
    cells, _ = run(config, "BY_CUSTOMER_ENTITY_TYPE", LOAN_ROWS, primary=primary_balance(4348, "60", "57"), title=LOANS_TITLE)
    assert cells[("CUSTOMER_ENTITY_TYPE=LLC_OTHER", JUN)]["acceptance"] == "ACCEPTED"
    assert cells[("TOTAL", JUN)]["acceptance"] == "ACCEPTED" and cells[("TOTAL", JUN)]["concept"] == "LOANS_TO_CUSTOMERS"
    deposits = [("Tiền gửi của " + label[0].lower() + label[1:], values) for label, values in LOAN_ROWS[:3]] + [LOAN_ROWS[3]]
    cells, _ = run(config, "BY_CUSTOMER_ENTITY_TYPE", deposits, primary=primary_balance(4348, "60", "57"), title=LOANS_TITLE)
    assert not [c for c in cells.values() if c["acceptance"] == "ACCEPTED"]
    mixed = LOAN_ROWS + [("Tiền gửi của cá nhân", ["5", "5"])]
    cells, evaluations = run(config, "BY_CUSTOMER_ENTITY_TYPE", mixed, primary=primary_balance(4348, "60", "57"), title=LOANS_TITLE)
    assert evaluations[0].rows[4].reason == "ROW_SUBJECT_CONFLICT:CUSTOMER_DEPOSITS"
    assert all(c["acceptance"] == "HOLD" and "TABLE_CONTAINS_ROW_OF_ANOTHER_SUBJECT" in c["hold_reasons"]
               for c in cells.values() if c["period_key"] == JUN)


def test_a_provision_column_is_never_a_gross_balance(config):
    # Codex 0206: "Dự phòng rủi ro 30/06/2025" sums 10 + 20 + 30 = 60 but is not the loan balance.
    rows = [(label, values[:1]) for label, values in LOAN_ROWS]
    cells, evaluations = run(config, "BY_CUSTOMER_ENTITY_TYPE", rows, primary=primary_balance(4348, "60", "57"),
                             title=LOANS_TITLE, headers=(("Dự phòng rủi ro 30/06/2025", "Triệu VND"),))
    assert cells and all(c["acceptance"] == "HOLD" and c["measure"] == "PROVISION"
                         and "COLUMN_MEASURE_NOT_A_BALANCE:PROVISION" in c["hold_reasons"] for c in cells.values())
    assert not evaluations[0].corroboration  # never compared with the balance-sheet loan balance
    for header in ("Giá trị thuần 30/06/2025", "Lãi dự thu 30/06/2025"):
        cells, _ = run(config, "BY_CUSTOMER_ENTITY_TYPE", rows, title=LOANS_TITLE, headers=((header, "Triệu VND"),))
        assert all(c["acceptance"] == "HOLD" and c["measure"] is not None for c in cells.values()), header
    # The plain dated column is the balance and still reads.
    cells, _ = run(config, "BY_CUSTOMER_ENTITY_TYPE", rows, primary=primary_balance(4348, "60", "57"),
                   title=LOANS_TITLE, headers=(("30/06/2025", "Triệu VND"),))
    assert cells[("TOTAL", JUN)]["acceptance"] == "ACCEPTED" and cells[("TOTAL", JUN)]["measure"] is None


def test_a_blank_child_never_proves_a_sibling_dash_zero(config):
    # Codex 0209: DEMAND 100 + TERM "-" + MARGIN blank = 100 looks closed only by ignoring the unknown MARGIN.
    rows = [("Tiền gửi không kỳ hạn", ["100", "90"]), ("Tiền gửi có kỳ hạn", ["-", "-"]), ("Tiền ký quỹ", [None, "30"]),
            ("Tổng", ["100", "120"])]
    for primary in (None, primary_balance(4320, "100", "120")):  # without and with an exact total anchor
        cells, evaluations = run(config, "DEPOSITS_BY_TYPE", rows, primary=primary)
        assert any(e["lane"] == "c1" and e["status"] == "INCOMPLETE_BLANK_OPERAND" for e in evaluations[0].equations)
        dash = cells[("DEPOSIT_TYPE=TERM", JUN)]
        assert dash["observation_state"] == "DASH" and dash["value"] is None and dash["acceptance"] == "HOLD"
        assert cells[("DEPOSIT_TYPE=MARGIN", JUN)]["value"] is None
        closed = cells[("DEPOSIT_TYPE=TERM", DEC)]  # 90 + 0 + 30 = 120, every child observed
        assert closed["observation_state"] == "DASH_ZERO" and closed["acceptance"] == "ACCEPTED"


def test_an_all_null_printed_item_stays_an_unknown_component(config):
    # Codex 0213: MARGIN printed as an ITEM with no value in either lane is not a heading; TOTAL = DEMAND + TERM("-")
    # must not close and read TERM as zero. A source GROUP heading keeps its heading meaning (test above).
    rows = [("Tiền gửi không kỳ hạn", ["100", "90"]), ("Tiền gửi có kỳ hạn", ["-", "-"]), ("Tiền ký quỹ", [None, None]),
            ("Tổng", ["100", "90"])]
    for primary in (None, primary_balance(4320, "100", "90")):
        cells, evaluations = run(config, "DEPOSITS_BY_TYPE", rows, primary=primary)
        assert evaluations[0].rows[2].disposition == "COORDINATE"
        assert {e["lane"] for e in evaluations[0].equations if e["status"] == "INCOMPLETE_BLANK_OPERAND"} == {"c1", "c2"}
        for period in (JUN, DEC):
            assert cells[("DEPOSIT_TYPE=MARGIN", period)]["value"] is None
            dash = cells[("DEPOSIT_TYPE=TERM", period)]
            assert dash["observation_state"] == "DASH" and dash["value"] is None and dash["acceptance"] == "HOLD", primary


def _related_table(rows, headers, kinds, *, title=None, section=None):
    from dataclasses import replace as _replace
    t = table(rows, title=title, section=section, headers=headers)
    t.columns = [_replace(column, value_kind=kinds.get(column.column_id, column.value_kind)) for column in t.columns]
    return t


def test_related_party_ownership_is_never_the_gross_deposit_total(config):
    # Codex 0234 E2: the deposits family reads the table's OWN context only.
    family = config.families["DEPOSITS_BY_TYPE"]
    axes = [config.axes[name] for name in family.raw["axes"]]
    # 1. Related-party transactions (doc 111 literals): counterparty TEXT and flow / receivable-payable MONEY columns.
    rows = [("Tiền gửi không kỳ hạn", ["Công ty A", "Công ty con", "10", "100"]), ("Tiền gửi có kỳ hạn", ["Công ty B", "Công ty liên kết", "20", "200"]),
            ("Tổng", [None, None, "30", "300"])]
    transactions = _related_table(rows, (("Bên liên quan",), ("Mối quan hệ",), ("Phát sinh trong kỳ Chi phí/ (Thu nhập)",),
                                         ("Số dư tại 30/06/2025 Phải thu/ (Phải trả)", "Triệu VND")),
                                  {"c1": "TEXT", "c2": "TEXT"}, section="33. GIAO DỊCH VỚI CÁC BÊN LIÊN QUAN")
    evaluation = evaluate_coordinate_table_v1(transactions, family, document(primary_balance(4320, "300", "270")),
                                              [("SECTION_TITLE", transactions.section_title)], [], axes=axes)[0]
    assert evaluation.status == "REJECTED"
    assert evaluation.reasons == ["OWNER_IS_RELATED_PARTY_TRANSACTIONS:counterparty=c1,c2;flow=c3,c4"]
    # 2. An explicitly related-party deposit subset with genuine term columns: held, never the gross total, even
    #    though the PRIMARY customer-deposit total agrees.
    subset_rows = [("Tiền gửi không kỳ hạn", ["100", "90"]), ("Tiền gửi có kỳ hạn", ["200", "150"]), ("Tổng", ["300", "240"])]
    cells_, evaluations = run(config, "DEPOSITS_BY_TYPE", subset_rows, primary=primary_balance(4320, "300", "240"),
                              title="Tiền gửi của khách hàng là các bên liên quan")
    assert evaluations[0].status == "EVALUATED" and not evaluations[0].corroboration
    assert all(c["acceptance"] == "HOLD" and c["concept"] is None and "RELATED_PARTY_SUBSET_NOT_GROSS_TOTAL" in c["hold_reasons"]
               for c in cells_.values())
    # 3. Ordinary gross customer deposits, with and without a related-party section elsewhere on the page.
    cells_, _ = run(config, "DEPOSITS_BY_TYPE", subset_rows, primary=primary_balance(4320, "300", "240"))
    assert cells_[("TOTAL", JUN)]["acceptance"] == "ACCEPTED" and cells_[("TOTAL", JUN)]["concept"] == "CUSTOMER_DEPOSITS"
    gross = table(subset_rows)
    context = [("TABLE_TITLE", gross.table_title), ("PRECEDING_SECTION_TITLE", "33. GIAO DỊCH VỚI CÁC BÊN LIÊN QUAN")]
    other = evaluate_coordinate_table_v1(gross, family, document(primary_balance(4320, "300", "240")), context, [], axes=axes)
    assert {(c["member"], c["period_key"]): c for e in other for c in e.cells}[("TOTAL", JUN)]["acceptance"] == "ACCEPTED"


def test_a_narrative_cross_reference_to_related_parties_does_not_make_a_gross_table_a_subset(config):
    # Codex 0236: an ordinary customer-deposit table whose own section narrative only points to the related-party note
    # stays the gross total (narrative authority deferred); a related-party HEADING still decides.
    family = config.families["DEPOSITS_BY_TYPE"]
    axes = [config.axes[name] for name in family.raw["axes"]]
    rows = [("Tiền gửi không kỳ hạn", ["100", "90"]), ("Tiền gửi có kỳ hạn", ["200", "150"]), ("Tổng", ["300", "240"])]
    gross = table(rows)
    context = [("TABLE_TITLE", gross.table_title),
               ("SECTION_NARRATIVE", "Giao dịch với các bên liên quan được trình bày tại Thuyết minh 33.")]
    evaluations = evaluate_coordinate_table_v1(gross, family, document(primary_balance(4320, "300", "240")), context, [], axes=axes)
    result = {(c["member"], c["period_key"]): c for e in evaluations for c in e.cells}
    assert result[("TOTAL", JUN)]["acceptance"] == "ACCEPTED" and result[("TOTAL", JUN)]["concept"] == "CUSTOMER_DEPOSITS"
    assert not any("RELATED_PARTY_SUBSET_NOT_GROSS_TOTAL" in c["hold_reasons"] for c in result.values())
    headed = table(rows, section="Tiền gửi của các bên liên quan")
    context = [("TABLE_TITLE", headed.table_title), ("SECTION_TITLE", headed.section_title)]
    held = evaluate_coordinate_table_v1(headed, family, document(primary_balance(4320, "300", "240")), context, [], axes=axes)
    assert all("RELATED_PARTY_SUBSET_NOT_GROSS_TOTAL" in c["hold_reasons"] for e in held for c in e.cells)
