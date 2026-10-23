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


def document():
    return DocumentContext(
        ordinal=1, document_plan_id="plan", relative_path="x.pdf", source_sha256="0" * 64, scope="SEPARATE",
        scope_basis="PRIMARY_DOCUMENT_SCOPE", reporting_date="2025-06-30",
        balance_lanes=[{"key": "INSTANT:2025-06-30", "role": "CURRENT", "header": "30/06/2025"},
                       {"key": "INSTANT:2024-12-31", "role": "COMPARATIVE", "header": "31/12/2024"}],
        context_texts=["Tại ngày 30 tháng 6 năm 2025"], primary_cells={},
        separator_roles=SeparatorRoles(thousands=frozenset({"."})),
    )


def table(rows, *, title="Tiền gửi của khách hàng", section=None):
    columns = [NoteColumn("c1", 1, ("30/06/2025", "Triệu VND"), "MONEY"), NoteColumn("c2", 2, ("31/12/2024", "Triệu VND"), "MONEY")]
    result = NoteTable(1, 20, "v20", "s1", "t1", 0, 0, "FINANCIAL_NOTE", section, title, None, "NONE", [], columns)
    for index, spec in enumerate(rows):
        label, values, kind = spec[0], spec[1], (spec[2] if len(spec) > 2 else None)
        parent = spec[3] if len(spec) > 3 else None
        kind = kind or ("TOTAL" if label in (None, "Tổng", "Cộng") else "ITEM")
        result.rows.append(NoteRow(f"r{index}", index, label, kind, (), parent))
        for column, value in zip(columns, values):
            state = "BLANK" if value is None else ("DASH" if value.strip() == "-" else "VALUE")
            result.cells[(f"r{index}", column.column_id)] = (value, state)
    return result


def run(config, family_name, rows, **kwargs):
    family = config.families[family_name]
    axes = [config.axes[name] for name in family.raw["axes"]]
    t = table(rows, **kwargs)
    context = [(s, x) for s, x in (("TABLE_TITLE", t.table_title), ("SECTION_TITLE", t.section_title)) if x]
    evaluations = evaluate_coordinate_table_v1(t, family, document(), context, [], axes=axes)
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
