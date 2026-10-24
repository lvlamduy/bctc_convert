"""Notes engine: kernel helpers and the LIST_BY_AXIS credit-quality plugin on synthetic tables."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from bctc_ai.notes.config_v1 import NotesConfigError, load_notes_config_v1
from bctc_ai.notes.engine_v1 import _assign_legacy_ids
from bctc_ai.notes.kernel_v1 import (
    DocumentContext,
    NoteColumn,
    NoteRow,
    NoteTable,
    assemble_continuations_v1,
)
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
        for column, value in zip(columns, values, strict=False):
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


def test_header_unit_contradicting_the_tables_own_unit_is_a_conflict_never_a_choice(family):
    # Codex 0122: a "VND" header under a printed "Triệu đồng" table unit field (or own title) is held.
    vnd = (("30/06/2025", "VND"), ("31/12/2024", "VND"))
    for table in (make_table(FIVE, headers=vnd, unit="Đơn vị: Triệu đồng"),
                  make_table(FIVE, headers=vnd, title="Phân tích chất lượng nợ cho vay (Đơn vị: triệu đồng)")):
        result = cells(evaluate_table_v1(table, family, document(), context_of(table), []))
        assert all("UNIT_CONFLICT_HEADER_VS_TABLE_OWNED_UNIT" in c["hold_reasons"] and c["unit"] is None
                   for c in result.values())
    agreeing = make_table(FIVE, headers=(("30/06/2025", "Triệu VND"), ("31/12/2024", "Triệu VND")), unit="Đơn vị: Triệu đồng")
    result = cells(evaluate_table_v1(agreeing, family, document(), context_of(agreeing), []))
    assert result[("G2", "INSTANT:2025-06-30")]["unit"] == "MILLION_VND"
    # No header unit: the table's own unit field and own title disagree -> held before any fallback (Codex 0127).
    bare = (("30/06/2025",), ("31/12/2024",))
    owned_conflict = make_table(FIVE, headers=bare, unit="Đơn vị: VND",
                                title="Phân tích chất lượng nợ cho vay (Đơn vị: triệu đồng)")
    result = cells(evaluate_table_v1(owned_conflict, family, document(), context_of(owned_conflict), []))
    assert all("UNIT_CONFLICT_TABLE_OWNED_UNITS" in c["hold_reasons"] and c["unit"] is None for c in result.values())
    # Field and own title agreeing still resolve; a conflicting unit in shared section prose stays outside the guard.
    owned_agree = make_table(FIVE, headers=bare, unit="Đơn vị: Triệu đồng",
                             title="Phân tích chất lượng nợ cho vay (Đơn vị: triệu đồng)")
    owned_agree.narratives = ["Đơn vị: VND"]
    owned_agree.section_table_count = 2
    result = cells(evaluate_table_v1(owned_agree, family, document(), context_of(owned_agree), []))
    assert result[("G2", "INSTANT:2025-06-30")]["unit"] == "MILLION_VND"
    # A unit printed only in a shared section narrative does not contradict the table's own header.
    shared = make_table(FIVE, headers=vnd)
    shared.narratives = ["Đơn vị: triệu đồng"]
    shared.section_table_count = 2
    result = cells(evaluate_table_v1(shared, family, document(), context_of(shared), []))
    assert not any("UNIT_CONFLICT_HEADER_VS_TABLE_OWNED_UNIT" in c["hold_reasons"] for c in result.values())


def test_primary_agreement_never_supplies_a_unit(family):
    # Codex 0009: matching the primary line (even exactly) corroborates numbers only.
    primary = {("CDKT", 4348, "INSTANT:2025-06-30"): (Decimal("1000"), "MILLION_VND")}
    table = make_table(FIVE, headers=(("30/06/2025",), ("31/12/2024",)))
    evaluations = evaluate_table_v1(table, family, document(primary), context_of(table), [])
    result = cells(evaluations)
    assert all("UNIT_UNRESOLVED" in c["hold_reasons"] and c["unit"] is None for c in result.values())
    assert not any(c["status"].startswith(("EXACT", "EQUAL")) for e in evaluations for c in e.corroboration)


def test_primary_agreement_corroborates_when_both_units_printed(family):
    primary = {("CDKT", 4348, "INSTANT:2025-06-30"): (Decimal("1000400000"), "VND")}
    table = make_table(FIVE, headers=(("30/06/2025", "Triệu VND"), ("31/12/2024", "Triệu VND")))
    evaluations = evaluate_table_v1(table, family, document(primary), context_of(table), [])
    assert any(c["status"] == "EQUAL_TO_PRIMARY_WITHIN_ONE_UNIT" for e in evaluations for c in e.corroboration)


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
    table = make_table(FIVE, title="Phân tích chất lượng dư nợ của hoạt động mua nợ", section="7. Hoạt động mua nợ")
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


def test_owner_context_with_two_subjects_holds_not_first_wins(family):
    table = make_table(FIVE, title="Phân tích chất lượng nợ cho vay", section="7. Hoạt động mua nợ")
    result = cells(evaluate_table_v1(table, family, document(), context_of(table), []))
    assert all(any(r.startswith("SUBJECT_UNRESOLVED") for r in c["hold_reasons"]) for c in result.values())


def test_vbb258_interbank_quality_table_is_not_customer_loans(family):
    # p15/s3: same five group labels, but the section narrative owns the subject.
    table = make_table(FIVE, title=None, section=None)
    table.narratives = ["Phân tích chất lượng dư nợ tiền gửi có kỳ hạn và cho vay các TCTD khác như sau:"]
    context = [("SECTION_NARRATIVE", table.narratives[0]), ("PRECEDING_TABLE_TITLE", "6. Cho vay khách hàng")]
    concepts = {c["concept"] for e in evaluate_table_v1(table, family, document(), context, []) for c in e.cells}
    assert concepts == {"INTERBANK_DEPOSITS_AND_LOANS"}


class _OutlineSource:
    def __init__(self, entries):
        self._entries = entries

    def outline(self):
        return {1: self._entries}


def _entry(page, section, table_id, title, continuation):
    return {"page": page, "section_order": 0, "table_order": 0, "kind": "FINANCIAL_NOTE", "title": title,
            "source": "TABLE_TITLE", "version": f"v{page}", "section_id": section, "table_id": table_id,
            "continuation": continuation}


def test_vbb258_declared_continuation_joins_head_group_and_follower_rows(family):
    head = make_table([("Cho vay các tổ chức kinh tế, cá nhân trong nước", ["100", "90"]),
                       ("Phân tích chất lượng nợ cho vay:", [None, None])],
                      headers=(("Số cuối quý",), ("Số đầu năm",)), title=None, section="6. Cho vay khách hàng\n6.1 Cho vay khách hàng",
                      unit="ĐVT : Triệu đồng", page=15)
    head.rows[1].kind = "GROUP"
    follower = make_table(FIVE, headers=((), ()), title=None, section=None, page=16)
    follower.section_id = "s1"
    source = _OutlineSource([_entry(15, "s1", "t1", None, "CONTINUES_ON_NEXT_PAGE"), _entry(16, "s1", "t1", None, "CONTINUES_FROM_PREVIOUS_PAGE")])
    joined, receipts = assemble_continuations_v1(source, [head, follower])
    assert len(joined) == 1 and len(receipts) == 1 and len(joined[0].rows) == 8
    context = [("SECTION_TITLE", head.section_title)]
    result = cells(evaluate_table_v1(joined[0], family, document(), context, []))
    g1 = result[("G1", "INSTANT:2025-06-30")]
    assert g1["concept"] == "LOANS_TO_CUSTOMERS" and g1["value"] == "900" and g1["unit"] == "MILLION_VND"
    assert g1["period_basis"] == "ALIGNED_TO_PRIMARY_BALANCE_CURRENT_LANE"


def test_titled_follower_is_not_a_continuation(family):
    head = make_table(FIVE[:3], title="Phân tích chất lượng nợ cho vay", page=15)
    follower = make_table(FIVE[3:], title="Phân tích dư nợ theo ngành", page=16)
    source = _OutlineSource([_entry(15, "s1", "t1", None, "CONTINUES_ON_NEXT_PAGE"), _entry(16, "s1", "t1", None, "CONTINUES_FROM_PREVIOUS_PAGE")])
    joined, receipts = assemble_continuations_v1(source, [head, follower])
    assert len(joined) == 2 and not receipts


def test_shared_section_narrative_date_has_no_owner(family):
    rows = FIVE
    table = make_table(rows, headers=(("Dư nợ cho vay", "Triệu đồng"), ("Dự phòng cụ thể", "Triệu đồng")), title=None,
                       section="11.1 Dự phòng rủi ro cho vay khách hàng")
    table.narratives = ["Kết quả phân loại nợ tại ngày 31 tháng 12 năm 2025 như sau:"]
    context = [("SECTION_TITLE", table.section_title), ("SECTION_NARRATIVE", table.narratives[0])]
    table.section_table_count = 2
    held = cells(evaluate_table_v1(table, family, document(), context, []))
    assert all(c["period_key"] is None for c in held.values())
    table.section_table_count = 1
    owned = cells(evaluate_table_v1(table, family, document(), context, []))
    assert owned[("G1", "INSTANT:2025-12-31")]["period_basis"] == "OWN_CAPTION_PRINTED_DATE"


def _pair(head_section="6. Cho vay khách hàng", follower_section=None, head_flag="CONTINUES_ON_NEXT_PAGE",
          follower_flag="CONTINUES_FROM_PREVIOUS_PAGE", follower_unit=None):
    head = make_table(FIVE[:3], title=None, section=head_section, unit="Triệu đồng", page=15)
    follower = make_table(FIVE[3:], headers=((), ()), title=None, section=follower_section, unit=follower_unit, page=16)
    source = _OutlineSource([_entry(15, "s1", "t1", None, head_flag), _entry(16, "s1", "t1", None, follower_flag)])
    joined, receipts = assemble_continuations_v1(source, [head, follower])
    return len(joined) == 1 and len(receipts) == 1


def test_continuation_requires_both_flags():
    assert _pair()
    assert not _pair(follower_flag="NONE")
    assert not _pair(head_flag="NONE")


def test_continued_marker_does_not_erase_note_identity():
    assert _pair(follower_section="6. Cho vay khách hàng (tiếp theo)")
    assert _pair(follower_section="THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT (tiếp theo)")  # generic page header
    assert not _pair(follower_section="7. Tiền gửi của khách hàng (tiếp theo)")


def test_continuation_unit_conflict_is_not_joined():
    assert not _pair(follower_unit="VND")


def test_signing_date_in_a_single_table_section_is_not_a_reporting_date(family):
    table = make_table(FIVE, headers=(("Dư nợ cho vay", "Triệu đồng"), ("Dự phòng cụ thể", "Triệu đồng")), title=None,
                       section="11.1 Dự phòng rủi ro cho vay khách hàng")
    table.narratives = ["Hà Nội, ngày 25 tháng 7 năm 2025"]
    context = [("SECTION_TITLE", table.section_title), ("SECTION_NARRATIVE", table.narratives[0])]
    result = cells(evaluate_table_v1(table, family, document(), context, []))
    assert all(c["period_key"] is None for c in result.values())


def test_follower_with_its_own_owner_narrative_is_not_joined():
    head = make_table(FIVE[:3], title=None, section="6. Cho vay khách hàng", unit="Triệu đồng", page=15)
    follower = make_table(FIVE[3:], headers=((), ()), title=None, section=None, page=16)
    follower.narratives = ["Phân tích chất lượng dư nợ tiền gửi có kỳ hạn và cho vay các TCTD khác như sau:"]
    source = _OutlineSource([_entry(15, "s1", "t1", None, "CONTINUES_ON_NEXT_PAGE"), _entry(16, "s1", "t1", None, "CONTINUES_FROM_PREVIOUS_PAGE")])
    joined, receipts = assemble_continuations_v1(source, [head, follower])
    assert len(joined) == 2 and not receipts


def test_signed_on_date_without_comma_is_not_a_reporting_date(family):
    table = make_table(FIVE, headers=(("Dư nợ cho vay", "Triệu đồng"), ("Dự phòng cụ thể", "Triệu đồng")), title=None,
                       section="11.1 Dự phòng rủi ro cho vay khách hàng")
    table.narratives = ["Báo cáo được ký ngày 25 tháng 7 năm 2025"]
    context = [("SECTION_TITLE", table.section_title), ("SECTION_NARRATIVE", table.narratives[0])]
    result = cells(evaluate_table_v1(table, family, document(), context, []))
    assert all(c["period_key"] is None for c in result.values())


def test_unit_of_a_sibling_table_is_never_inherited(family):
    # Codex 0019 veto: a unit printed on another table of the same section does not
    # prove the unit of a table that prints none; the cells stay held.
    table = make_table(FIVE, headers=(("30/09/2025",), ("31/12/2024",)), title="Phân tích chất lượng nợ cho vay",
                       section="6. CHO VAY KHÁCH HÀNG")
    result = cells(evaluate_table_v1(table, family, document(), context_of(table), ["Triệu Đồng Việt Nam"]))
    assert all("UNIT_UNRESOLVED" in c["hold_reasons"] for c in result.values())


JUN = "INSTANT:2025-06-30"
DEC = "INSTANT:2024-12-31"


def test_a_blank_operand_never_proves_another_components_dash_zero(family):
    # Codex 0209: G1..G5 = 900, 50, 30, "-", blank with total 980 looks closed only by ignoring the unknown G5.
    rows = [("Nhóm 1 - Nợ đủ tiêu chuẩn", ["900", "800"]), ("Nhóm 2 - Nợ cần chú ý", ["50", "40"]),
            ("Nhóm 3 - Nợ dưới tiêu chuẩn", ["30", "10"]), ("Nhóm 4 - Nợ nghi ngờ", ["-", "-"]),
            ("Nhóm 5 - Nợ có khả năng mất vốn", [None, "20"]), ("Tổng", ["980", "870"])]
    for primary in ({}, {("CDKT", 4348, JUN): (Decimal("980"), "MILLION_VND")}):  # without and with an exact total anchor
        table = make_table(rows)
        evaluations = evaluate_table_v1(table, family, document(primary), context_of(table), [])
        result = cells(evaluations)
        assert any(e["lane"] == "c1" and e["status"] == "INCOMPLETE_BLANK_OPERAND" for e in evaluations[0].equations)
        dash = result[("G4", JUN)]
        assert dash["observation_state"] == "DASH" and dash["value"] is None and dash["acceptance"] == "HOLD"
        assert "DASH_WITHOUT_PROOF" in dash["hold_reasons"], primary
        blank = result[("G5", JUN)]
        assert blank["observation_state"] == "BLANK" and blank["value"] is None
        # The fully observed lane closes its frontier: 800 + 40 + 10 + 0 + 20 = 870 reads the dash as zero.
        closed = result[("G4", DEC)]
        assert closed["observation_state"] == "DASH_ZERO" and closed["acceptance"] == "ACCEPTED"
    assert any(c["status"].startswith("EXACT") for c in evaluations[0].corroboration)  # the anchor is exact, yet no zero


def test_an_explicit_single_column_subject_is_never_erased_by_the_context(family):
    # Codex 0210: one "Chứng khoán kinh doanh" column under customer-loan context is not customer loans.
    securities = (("Chứng khoán kinh doanh", "30/06/2025", "Triệu VND"),)
    table = make_table(FIVE, headers=securities)
    result = cells(evaluate_table_v1(table, family, document(), context_of(table), []))
    assert result and all(c["acceptance"] == "HOLD" and any(r.startswith("SUBJECT_CONFLICT_COLUMN_VS_OWNED_CONTEXT")
                                                            for r in c["hold_reasons"]) for c in result.values())
    owned = make_table(FIVE, headers=securities, title="Phân tích chất lượng chứng khoán kinh doanh", section="5. Chứng khoán kinh doanh")
    result = cells(evaluate_table_v1(owned, family, document(), context_of(owned), []))
    assert result[("G2", JUN)]["acceptance"] == "ACCEPTED" and result[("G2", JUN)]["concept"] == "TRADING_SECURITIES_DEBT"
    gross = make_table(FIVE, headers=(("Dư nợ cho vay khách hàng", "30/06/2025", "Triệu VND"),))
    result = cells(evaluate_table_v1(gross, family, document(), context_of(gross), []))
    assert result[("G2", JUN)]["acceptance"] == "ACCEPTED" and result[("G2", JUN)]["concept"] == "LOANS_TO_CUSTOMERS"


def test_a_net_or_interest_column_is_never_the_gross_balance(family):
    # Codex 0210: "dư nợ" also matches "Dư nợ thuần sau dự phòng"; a balanced vector cannot choose the measure.
    primary = {("CDKT", 4348, JUN): (Decimal("1000"), "MILLION_VND")}
    for header, measure in (("Dư nợ thuần sau dự phòng", "NET_OF_PROVISION"), ("Lãi dự thu", "ACCRUED_INTEREST")):
        table = make_table(FIVE, headers=((header, "30/06/2025", "Triệu VND"),))
        evaluations = evaluate_table_v1(table, family, document(primary), context_of(table), [])
        result = cells(evaluations)
        assert result and all(c["acceptance"] == "HOLD" and c["measure"] == measure
                              and "COLUMN_MEASURE_NOT_GROSS_BALANCE:" + measure in c["hold_reasons"] for c in result.values())
        assert not evaluations[0].corroboration  # never compared with the gross loan balance
    plain = make_table(FIVE, headers=(("Dư nợ", "30/06/2025", "Triệu VND"),))
    result = cells(evaluate_table_v1(plain, family, document(primary), context_of(plain), []))
    assert result[("G2", JUN)]["acceptance"] == "ACCEPTED" and result[("G2", JUN)]["measure"] == "BALANCE"


def test_an_all_null_printed_group_row_stays_an_unknown_component(family):
    # Codex 0213: a printed "Nhóm 5" ITEM with no value in ANY lane must not leave the run (as a heading) so that
    # 900 + 50 + 30 + "-" = 980 closes and reads the dash as zero.
    rows = [("Nhóm 1 - Nợ đủ tiêu chuẩn", ["900", "800"]), ("Nhóm 2 - Nợ cần chú ý", ["50", "40"]),
            ("Nhóm 3 - Nợ dưới tiêu chuẩn", ["30", "10"]), ("Nhóm 4 - Nợ nghi ngờ", ["-", "-"]),
            ("Nhóm 5 - Nợ có khả năng mất vốn", [None, None]), ("Tổng", ["980", "850"])]
    primary = {("CDKT", 4348, JUN): (Decimal("980"), "MILLION_VND"), ("CDKT", 4348, DEC): (Decimal("850"), "MILLION_VND")}
    for cells_primary in ({}, primary):
        table = make_table(rows)
        assert axis_blocks_v1(table, family) == [([], list(range(6)))]  # one run: G5 is not a heading
        evaluations = evaluate_table_v1(table, family, document(cells_primary), context_of(table), [])
        assert len(evaluations) == 1
        assert {e["lane"] for e in evaluations[0].equations if e["status"] == "INCOMPLETE_BLANK_OPERAND"} == {"c1", "c2"}
        result = cells(evaluations)
        for period in (JUN, DEC):
            assert result[("G5", period)]["observation_state"] == "BLANK" and result[("G5", period)]["value"] is None
            dash = result[("G4", period)]
            assert dash["observation_state"] == "DASH" and dash["value"] is None and dash["acceptance"] == "HOLD", cells_primary
