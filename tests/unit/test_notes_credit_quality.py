"""Notes engine: kernel helpers and the LIST_BY_AXIS credit-quality plugin on synthetic tables."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from bctc_ai.notes.config_v1 import NotesConfigError, load_notes_config_v1
from bctc_ai.notes.engine_v1 import _assign_legacy_ids
from bctc_ai.notes.kernel_v1 import DocumentContext, NoteColumn, NoteRow, NoteTable, positional_date_caption_v1
from bctc_ai.notes.list_shape_v1 import axis_blocks_v1, evaluate_table_v1
from bctc_ai.primary_statements.numbers_v1 import SeparatorRoles

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def config():
    return load_notes_config_v1(ROOT)


@pytest.fixture(scope="module")
def family(config):
    return config.families["CREDIT_QUALITY"]


def document(primary_cells=None, scope="CONSOLIDATED"):
    return DocumentContext(
        ordinal=1, document_plan_id="plan", relative_path="x.pdf", source_sha256="0" * 64, scope=scope,
        scope_basis="PRIMARY_DOCUMENT_SCOPE", reporting_date="2025-06-30",
        balance_lanes=[{"key": "INSTANT:2025-06-30", "role": "CURRENT", "header": "30/06/2025"},
                       {"key": "INSTANT:2024-12-31", "role": "COMPARATIVE", "header": "31/12/2024"}],
        context_texts=["Tại ngày 30 tháng 6 năm 2025"], primary_cells=primary_cells or {},
        separator_roles=SeparatorRoles(thousands=frozenset({"."})),
    )


def make_table(rows, headers=(("30/06/2025", "Triệu VND"), ("31/12/2024", "Triệu VND")), *, title="Phân tích chất lượng nợ cho vay",
               section="9. Cho vay khách hàng", unit=None, kinds=None, page=10):
    columns = [NoteColumn(f"c{i}", i, tuple(h), "MONEY") for i, h in enumerate(headers, 1)]
    table = NoteTable(1, page, f"v{page}", "s1", "t1", 0, 0, "FINANCIAL_NOTE", section, title, unit, "NONE", [], columns)
    for index, (label, values) in enumerate(rows):
        kind = (kinds or {}).get(index, "TOTAL" if label in (None, "Tổng", "Cộng", "Tổng cộng") else "ITEM")
        table.rows.append(NoteRow(f"r{index}", index, label, kind, (), None))
        for column, value in zip(columns, values):
            state = "BLANK" if value is None else ("DASH" if value.strip() == "-" else "VALUE")
            table.cells[(f"r{index}", column.column_id)] = (value, state)
    return table


def context_of(table):
    return [(s, t) for s, t in (("TABLE_TITLE", table.table_title), ("SECTION_TITLE", table.section_title)) if t]


FIVE = [("Nhóm 1 - Nợ đủ tiêu chuẩn", ["900", "800"]), ("Nhóm 2 - Nợ cần chú ý", ["50", "40"]),
        ("Nhóm 3 - Nợ dưới tiêu chuẩn", ["20", "10"]), ("Nhóm 4 - Nợ nghi ngờ", ["10", "5"]),
        ("Nhóm 5 - Nợ có khả năng mất vốn", ["20", "15"]), ("Tổng", ["1.000", "870"])]


def cells(evaluations):
    return {(c["member"], c["period_key"]): c for e in evaluations for c in e.cells}


def test_five_groups_accepted_with_equation_and_aliases(family):
    table = make_table(FIVE)
    result = cells(evaluate_table_v1(table, family, document(), context_of(table), []))
    g2 = result[("G2", "INSTANT:2025-06-30")]
    assert g2["acceptance"] == "ACCEPTED" and g2["value"] == "50" and g2["concept"] == "LOANS_TO_CUSTOMERS"
    assert result[("TOTAL_FIVE_GROUPS", "INSTANT:2024-12-31")]["value"] == "870"


def test_equation_failure_holds_and_never_backsolves(family):
    rows = list(FIVE)
    rows[1] = ("Nhóm 2 - Nợ cần chú ý", ["58", "40"])  # beyond the per-line rounding tolerance
    table = make_table(rows)
    result = cells(evaluate_table_v1(table, family, document(), context_of(table), []))
    assert result[("G2", "INSTANT:2025-06-30")]["acceptance"] == "HOLD"
    assert any(r.startswith("VALIDATION_FAIL") for r in result[("G2", "INSTANT:2025-06-30")]["hold_reasons"])
    assert result[("G2", "INSTANT:2024-12-31")]["acceptance"] == "ACCEPTED"


def test_blank_is_never_zero_and_dash_needs_proof(family):
    rows = list(FIVE)
    rows[3] = ("Nhóm 4 - Nợ nghi ngờ", ["-", None])
    rows[5] = ("Tổng", ["990", "865"])
    table = make_table(rows)
    result = cells(evaluate_table_v1(table, family, document(), context_of(table), []))
    dash = result[("G4", "INSTANT:2025-06-30")]
    assert dash["observation_state"] == "DASH_ZERO" and dash["acceptance"] == "ACCEPTED"
    blank = result[("G4", "INSTANT:2024-12-31")]
    assert blank["observation_state"] == "BLANK" and blank["value"] is None


def test_unit_never_inferred_from_magnitude(family):
    table = make_table(FIVE, headers=(("30/06/2025",), ("31/12/2024",)))
    result = cells(evaluate_table_v1(table, family, document(), context_of(table), []))
    assert all("UNIT_UNRESOLVED" in c["hold_reasons"] for c in result.values())


def test_unit_proven_only_by_agreement_with_printed_primary_figure(family):
    primary = {("CDKT", 4348, "INSTANT:2025-06-30"): (Decimal("1000000400"), "VND")}
    rows = list(FIVE)
    rows[0] = ("Nhóm 1 - Nợ đủ tiêu chuẩn", ["900.000", "800"])
    rows[5] = ("Tổng", ["1.000.000", "870"])
    table = make_table(rows, headers=(("30/06/2025",), ("31/12/2024",)))
    result = cells(evaluate_table_v1(table, family, document(primary), context_of(table), []))
    # 1.000.000 (7 digits) agrees with 1.000.000.400 VND within one unit only at the thousand scale: proven.
    assert result[("G1", "INSTANT:2025-06-30")]["unit"] == "THOUSAND_VND"
    assert result[("G1", "INSTANT:2025-06-30")]["unit_basis"] == "PRIMARY_SCALED_AGREEMENT"
    assert "UNIT_UNRESOLVED" in result[("G1", "INSTANT:2024-12-31")]["hold_reasons"]


def test_relative_headers_align_to_primary_balance_lanes(family):
    table = make_table(FIVE, headers=(("Cuối kỳ", "Triệu VND"), ("Đầu năm", "Triệu VND")))
    result = cells(evaluate_table_v1(table, family, document(), context_of(table), []))
    assert result[("G1", "INSTANT:2025-06-30")]["period_basis"] == "ALIGNED_TO_PRIMARY_BALANCE_CURRENT_LANE"
    assert result[("G1", "INSTANT:2024-12-31")]["period_basis"] == "ALIGNED_TO_PRIMARY_BALANCE_COMPARATIVE_LANE"


def test_member_printed_twice_is_ambiguous_not_first_wins(family):
    rows = FIVE[:2] + [("Nợ cần chú ý", ["60", "40"])] + FIVE[2:]
    table = make_table(rows)
    result = cells(evaluate_table_v1(table, family, document(), context_of(table), []))
    assert ("G2", "INSTANT:2025-06-30") not in result or result[("G2", "INSTANT:2025-06-30")]["acceptance"] == "HOLD"


def test_composite_row_is_not_group_five(family):
    rows = FIVE[:4] + [("Nợ có khả năng mất vốn và các khoản nợ chờ xử lý", ["20", "15"]), ("Tổng", ["1.000", "870"])]
    table = make_table(rows)
    evaluations = evaluate_table_v1(table, family, document(), context_of(table), [])
    roles = [r for e in evaluations for r in e.roles]
    assert any(r.reason == "COMPOSITE_ROW_MEMBER_PLUS_OTHER" for r in roles)
    assert ("G5", "INSTANT:2025-06-30") not in cells(evaluations)


def test_wide_table_splits_into_axis_blocks(family):
    rows = ([("Phân tích chất lượng nợ cho vay", [None, None])] + FIVE[:5] + [("Cộng", ["1.000", "870"])]
            + [("Phân tích dư nợ theo thời hạn", [None, None]), ("Nợ ngắn hạn", ["600", "500"]),
               ("Nợ trung hạn", ["400", "370"]), ("Cộng", ["1.000", "870"]), ("Công ty TNHH", ["10", "9"])])
    table = make_table(rows, title=None, section="9. Cho vay khách hàng")
    blocks = axis_blocks_v1(table, family)
    assert len(blocks) == 1 and blocks[0][0] == ["Phân tích chất lượng nợ cho vay"] and len(blocks[0][1]) == 6
    result = cells(evaluate_table_v1(table, family, document(), context_of(table), []))
    assert result[("TOTAL_FIVE_GROUPS", "INSTANT:2025-06-30")]["acceptance"] == "ACCEPTED"


def test_rate_table_is_rejected(family):
    table = make_table([(label, ["5%"]) for label, _ in FIVE[:5]], headers=(("Tỷ lệ trích lập dự phòng",),),
                       title="Tỷ lệ trích lập dự phòng cụ thể")
    evaluations = evaluate_table_v1(table, family, document(), context_of(table), [])
    assert all(e.status == "REJECTED" for e in evaluations)


def test_subject_from_printed_context_and_ambiguity_holds(family):
    table = make_table(FIVE, title="Phân tích chất lượng dư nợ của hoạt động mua nợ")
    assert {c["concept"] for e in evaluate_table_v1(table, family, document(), context_of(table), []) for c in e.cells} == {"PURCHASED_DEBT"}
    table = make_table(FIVE, title=None, section=None)
    result = cells(evaluate_table_v1(table, family, document(), [], []))
    assert all(any(r.startswith("SUBJECT_UNRESOLVED") for r in c["hold_reasons"]) for c in result.values())


def test_scope_unresolved_holds(family):
    table = make_table(FIVE)
    result = cells(evaluate_table_v1(table, family, document(scope=None), context_of(table), []))
    assert all("SCOPE_UNRESOLVED" in c["hold_reasons"] for c in result.values())


def test_legacy_ids_prefer_grand_total_and_skip_competing_bases(config, family):
    rows = FIVE[:5] + [("Tổng", ["1.000", "870"]), ("Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán", ["100", "50"]),
                       ("Tổng cộng", ["1.100", "920"])]
    table = make_table(rows)
    evaluated = [c for e in evaluate_table_v1(table, family, document(), context_of(table), []) for c in e.cells]
    _assign_legacy_ids(evaluated, config)
    by = {(c["member"], c["period_key"]): c["report_norm_id"] for c in evaluated}
    assert by[("GRAND_TOTAL", "INSTANT:2025-06-30")] == 746 and by[("TOTAL_FIVE_GROUPS", "INSTANT:2025-06-30")] is None
    assert by[("MARGIN_AND_SECURITIES_ADVANCE", "INSTANT:2025-06-30")] == 1944
    for cell in evaluated:
        cell["classification_basis"] = "TT31_2024"
    extra = [dict(c, classification_basis="AS_PRESENTED") for c in evaluated]
    _assign_legacy_ids(evaluated + extra, config)
    assert all(c["report_norm_id"] is None for c in evaluated)


def test_positional_caption_stops_at_previous_table():
    table = make_table(FIVE, title=None)
    outline = [
        {"page": 10, "section_order": 0, "table_order": -1, "title": "Tại ngày 31 tháng 12 năm 2024", "source": "SECTION_TITLE",
         "version": "v10", "section_id": "s0", "table_id": None},
        {"page": 10, "section_order": 0, "table_order": 0, "title": None, "source": "TABLE_TITLE",
         "version": "v10", "section_id": "s0", "table_id": "t0"},
        {"page": 10, "section_order": 1, "table_order": 0, "title": None, "source": "TABLE_TITLE",
         "version": "v10", "section_id": "s1", "table_id": "t1"},
    ]
    assert positional_date_caption_v1(table, outline) == (None, None)
    outline.insert(2, {"page": 10, "section_order": 1, "table_order": -1, "title": "Tại ngày 30 tháng 6 năm 2025",
                       "source": "SECTION_TITLE", "version": "v10", "section_id": "s9", "table_id": None})
    assert positional_date_caption_v1(table, outline) == ("2025-06-30", "Tại ngày 30 tháng 6 năm 2025")


def test_crosswalk_rejects_reused_report_norm_id(tmp_path):
    import shutil

    shutil.copytree(ROOT / "config" / "notes", tmp_path / "config" / "notes")
    path = tmp_path / "config" / "notes" / "crosswalk_v1.yaml"
    path.write_text(path.read_text(encoding="utf-8") +
                    "  - {concept: LOANS_TO_CUSTOMERS, axis: CREDIT_QUALITY_GROUP, member: G9, report_norm_id: 747}\n",
                    encoding="utf-8")
    with pytest.raises(NotesConfigError):
        load_notes_config_v1(tmp_path)


def test_config_pins_change_with_content(tmp_path, config):
    import shutil

    shutil.copytree(ROOT / "config" / "notes", tmp_path / "config" / "notes")
    path = tmp_path / "config" / "notes" / "axes_v1.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("nhom 2, no can chu y", "nhom 2, no can chu y, nhom ii"),
                    encoding="utf-8")
    assert load_notes_config_v1(tmp_path).pins["axes_v1.yaml"] != config.pins["axes_v1.yaml"]


def test_lone_separator_without_document_evidence_is_not_parsed(family):
    table = make_table(FIVE)
    doc = document()
    doc.separator_roles = SeparatorRoles()
    result = cells(evaluate_table_v1(table, family, doc, context_of(table), []))
    total = result[("TOTAL_FIVE_GROUPS", "INSTANT:2025-06-30")]
    assert total["acceptance"] == "HOLD" and total["value"] is None
