from decimal import Decimal

import pytest

from bctc_ai.primary_statements.numbers_v1 import (
    SeparatorRoles,
    evidence_roles_v1,
    parse_money_cell_v1,
)
from bctc_ai.primary_statements.periods_v1 import (
    duration_lane_period_v1,
    instant_lane_period_v1,
    statement_period_context_v1,
)
from bctc_ai.primary_statements.text_v1 import label_key_v1
from bctc_ai.primary_statements.units_v1 import (
    MILLION_VND,
    PERCENT,
    VND,
    VND_PER_SHARE,
    units_in_header_component_v1,
    units_in_prose_v1,
    units_in_row_label_annotation_v1,
    units_in_unit_field_v1,
)

DOT = SeparatorRoles(frozenset({"."}))


@pytest.mark.parametrize(
    ("label", "key"),
    [
        ("VI Cho vay khách hàng", "cho vay khach hang"),
        ("03.Thu nhập từ hoạt động dịch vụ nhận được", "thu nhap tu hoat dong dich vu nhan duoc"),
        ("(Tăng)/Giảm các khoản cho vay khách hàng", "cac khoan cho vay khach hang"),
        ("Tăng các khoản cho vay khách hàng", "cac khoan cho vay khach hang"),
        ("(Lỗ)/lãi thuần từ mua bán chứng khoán đầu tư", "lai lo thuan tu mua ban chung khoan dau tu"),
        ("Lãi thuần từ mua bán chứng khoán đầu tư", "lai lo thuan tu mua ban chung khoan dau tu"),
        ('Tiền gửi tại Ngân hàng Nhà nước Việt Nam (“NHNN”)', "tien gui tai ngan hang nha nuoc"),
        ("Tiền thu/(chi) đầu tư, góp vốn vào các đơn vị khác", "tien thu chi dau tu gop von vao cac don vi khac"),
        ("Lưu chuyển tiền thuần sử dụng vào hoạt động đầu tư", "luu chuyen tien thuan tu hoat dong dau tu"),
        ("Dự phòng rủi ro cho vay khách hàng (*)", "du phong rui ro cho vay khach hang"),
        ("XI. Tổng lợi nhuận trước thuế (IX-X)", "tong loi nhuan truoc thue"),
    ],
)
def test_label_key_normalizes_presentation_only(label, key):
    assert label_key_v1(label).key == key


def test_label_key_keeps_annotations_as_evidence():
    parsed = label_key_v1("Lãi cơ bản trên cổ phiếu (VND/cổ phiếu)")
    assert parsed.key == "lai co ban tren co phieu"
    assert parsed.removed_annotations == ("(vnd/co phieu)",)
    carry = label_key_v1("Tổng lợi nhuận trước thuế (mang sang trang sau)")
    assert carry.key == "tong loi nhuan truoc thue" and "mang sang" in carry.removed_annotations[0]


def test_parenthetical_words_are_not_dropped_as_acronyms():
    assert "chi" in label_key_v1("Tiền thu/(chi) bất động sản đầu tư").key.split()


@pytest.mark.parametrize(
    ("raw", "state", "value"),
    [
        (None, "BLANK", None),
        ("", "BLANK", None),
        ("-", "DASH", None),
        (" – ", "DASH", None),
        ("0", "PRINTED_ZERO", Decimal(0)),
        ("1.234.567", "VALUE", Decimal(1234567)),
        ("(1.790.085)", "VALUE", Decimal(-1790085)),
        ("1,234,567", "VALUE", Decimal(1234567)),
        ("5.600,00", "VALUE", Decimal("5600.00")),
        ("487.573", "VALUE", Decimal(487573)),
        ("- tieu", "MALFORMED", None),
        ("-隆-", "MALFORMED", None),
        ("4.038.523)", "MALFORMED", None),
        ("7.500.000\n\n479.250", "MALFORMED", None),
        ("2.823.560.", "MALFORMED", None),
    ],
)
def test_money_cell_states_never_coerce_blank_or_noise(raw, state, value):
    parsed = parse_money_cell_v1(raw, DOT)
    assert parsed.state == state
    assert parsed.value == value


def test_single_group_separator_requires_scope_evidence():
    assert parse_money_cell_v1("487.573", SeparatorRoles()).state == "AMBIGUOUS_SEPARATOR"
    assert parse_money_cell_v1("589,729", DOT).state == "AMBIGUOUS_SEPARATOR"
    conflicted = SeparatorRoles(frozenset({"."}), frozenset({"."}))
    assert parse_money_cell_v1("487.573", conflicted).state == "AMBIGUOUS_SEPARATOR"
    # Multi-group numbers are self-evident even when a scope is conflicted.
    assert parse_money_cell_v1("1.234.567", conflicted).value == Decimal(1234567)
    assert evidence_roles_v1("1.234.567").thousands == frozenset({"."})
    assert evidence_roles_v1("487.573").thousands == frozenset()


def test_restated_qualifier_is_retained():
    parsed = parse_money_cell_v1("3.221\n(trình bày lại)", DOT)
    assert parsed.state == "VALUE" and parsed.value == Decimal(3221) and parsed.qualifiers


def test_units_read_only_from_explicit_phrases():
    assert [u.unit for u in units_in_unit_field_v1("Đơn vị tính: Triệu Đồng Việt Nam", source_kind="T")] == [MILLION_VND]
    assert [u.unit for u in units_in_unit_field_v1("Unit: million VND, %", source_kind="T")] == [MILLION_VND, PERCENT]
    assert [u.unit for u in units_in_header_component_v1("31/12/2024\nTriệu VND")] == [MILLION_VND]
    assert [u.unit for u in units_in_header_component_v1("VND")] == [VND]
    assert units_in_prose_v1("Ngân hàng ký hợp đồng với khách hàng", source_kind="N") == []
    assert [u.unit for u in units_in_prose_v1("ĐVT: triệu đồng", source_kind="N")] == [MILLION_VND]
    assert [u.unit for u in units_in_row_label_annotation_v1(("(vnd/co phieu)",))] == [VND_PER_SHARE]


def _period(header, context, basis="D"):
    ctx = statement_period_context_v1(context)
    return (duration_lane_period_v1 if basis == "D" else instant_lane_period_v1)(header, ctx)


@pytest.mark.parametrize(
    ("header", "context", "basis", "key"),
    [
        ("30/6/2025\nTriệu VND", [], "I", "INSTANT:2025-06-30"),
        ("Số cuối kỳ\n(3)", ["Tại ngày 31 tháng 03 năm 2025"], "I", "INSTANT:2025-03-31"),
        ("Số dư cuối quý", ["QUÝ I/2025"], "I", "INSTANT:END_OF_QUARTER(Q1:2025)"),
        ("Số đầu năm", ["Tại ngày 30 tháng 6 năm 2025"], "I", "INSTANT:OPENING_OF_FISCAL_YEAR(2025-06-30)"),
        ("Quý 1\nKỳ này", ["Cho giai đoạn từ ngày 01/01/2025 đến ngày 31/03/2025"], "D", "DURATION:QUARTER:1:2025"),
        ("Lũy kế từ đầu năm nay đến cuối quý này\nNăm trước", ["Cho Quý 4 kết thúc ngày 31 tháng 12 năm 2025"], "D",
         "DURATION:YTD:Q4:PRIOR_YEAR_OF(2025)"),
        ("Quý I/2025\nNăm\ntrước", ["Quý I năm 2025"], "D", "DURATION:QUARTER:1:PRIOR_YEAR_OF(2025)"),
        ("Kỳ ba tháng\nkết thúc ngày\n31//03/2025", [], "D", "DURATION:MONTHS_ENDED:3:2025-03-31"),
        ("Từ 1/1/2026 đến 31/3/2026", [], "D", "DURATION:RANGE:2026-01-01..2026-03-31"),
        ("2025\nTriệu VND", ["Năm kết thúc ngày 31 tháng 12 năm 2025"], "D", "DURATION:YEAR:2025"),
        ("Lũy kế từ đầu kỳ đến ngày\n31/12/2025", [], "D", "DURATION:CUMULATIVE_FROM_START_OF_PERIOD_TO:2025-12-31"),
    ],
)
def test_lane_periods_use_printed_evidence_only(header, context, basis, key):
    assert _period(header, context, basis).key == key


def test_prior_relative_label_never_subtracts_one_year():
    descriptor = _period("Quý này năm trước", ["Quý 2 năm 2025"])
    assert descriptor.key == "DURATION:QUARTER:2:PRIOR_YEAR_OF(2025)"
    assert "2024" not in descriptor.key


def test_first_months_of_fiscal_year_is_not_months_ended():
    context = statement_period_context_v1(
        ["6 tháng đầu của năm tài chính kết thúc ngày 31 tháng 12 năm 2025"]
    )
    assert context.months is None and context.reporting_date is None
    assert context.first_months_of_fiscal_year == 6 and context.fiscal_year_end == "2025-12-31"
    assert _period("Lũy kế từ đầu năm đến cuối kỳ này\nNăm nay",
                   ["6 tháng đầu của năm tài chính kết thúc ngày 31 tháng 12 năm 2025"]).key \
        == "DURATION:YTD:FIRST_6M_OF_FY:2025"


def test_quarter_and_ytd_lanes_are_distinct_and_mismatched_bases_veto():
    context = ["Quý 2 năm 2025"]
    quarter = _period("Quý này\nNăm nay", context)
    ytd = _period("Lũy kế từ đầu năm đến cuối quý này\nNăm nay", context)
    assert quarter.key != ytd.key
    assert _period("Số cuối kỳ", ["Quý 2 năm 2025"], "D").basis == "UNRESOLVED"
    assert _period("Lũy kế từ đầu năm", ["Tại ngày 30/06/2025"], "I").basis == "UNRESOLVED"
    assert _period("Kỳ này", ["Quý 2 năm 2025"]).basis == "UNRESOLVED"  # quarter-only vs YTD not proven


def test_signing_date_and_conflicting_reporting_dates():
    context = statement_period_context_v1(["Hà Nội, ngày 29 tháng 7 năm 2025", "Tại ngày 30 tháng 6 năm 2025"])
    assert context.reporting_date == "2025-06-30" and context.conflict is None
    conflict = statement_period_context_v1(["Tại ngày 30 tháng 6 năm 2025", "Tại ngày 31 tháng 12 năm 2025"])
    assert conflict.conflict == "MULTIPLE_PRINTED_REPORTING_DATES"
    assert _period("Số cuối kỳ", ["Tại ngày 30 tháng 6 năm 2025", "Tại ngày 31 tháng 12 năm 2025"], "I").basis == "UNRESOLVED"


def test_ytd_through_this_quarter_binds_to_printed_period_end():
    context = ["Cho kỳ kế toán từ ngày 01/01/2025 đến ngày 30/09/2025"]
    descriptor = _period("Lũy kế từ đầu năm đến cuối quý này\nNăm nay", context)
    assert descriptor.basis != "UNRESOLVED"
    assert "TO_09-30" in descriptor.key or ":Q3:" in descriptor.key
    assert descriptor.resolution == "CONTEXT_BOUND"
    assert _period("Lũy kế từ đầu năm đến cuối quý này\nNăm nay", []).basis == "UNRESOLVED"


def test_transcribed_literal_line_break_does_not_glue_words():
    context = statement_period_context_v1(["BÁO CÁO KẾT QUẢ HOẠT ĐỘNG HỢP NHẤT\nQuý II năm 2026"])
    assert context.quarter == 2 and context.year == 2026


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("Quý trước", None),                                           # preceding quarter: no printed window
        ("Quý này năm trước", "DURATION:QUARTER:2:PRIOR_YEAR_OF(2025)"),
        ("Quý 2\nNăm trước", "DURATION:QUARTER:2:PRIOR_YEAR_OF(2025)"),
    ],
)
def test_previous_quarter_is_not_the_same_quarter_of_prior_year(header, expected):
    descriptor = _period(header, ["Báo cáo kết quả hoạt động cho Quý II năm 2025"])
    assert descriptor.key == expected
    if expected is None:
        assert descriptor.reason == "PREVIOUS_QUARTER_WITHOUT_PRINTED_COMPARATIVE_WINDOW"


@pytest.mark.parametrize(
    ("header", "context", "key", "reason"),
    [
        # "Kỳ trước" alone: the comparative window is not printed -> held.
        ("Kỳ trước", ["Cho giai đoạn từ ngày 01/01/2025 đến ngày 30/06/2025"], None,
         "PRIOR_PERIOD_WITHOUT_PRINTED_COMPARATIVE_WINDOW"),
        ("Kỳ trước", ["Cho kỳ sáu tháng kết thúc ngày 30 tháng 6 năm 2025"], None,
         "PRIOR_PERIOD_WITHOUT_PRINTED_COMPARATIVE_WINDOW"),
        ("Quý 2\nKỳ trước", ["Quý 2 năm 2025"], None, "PRIOR_PERIOD_WITHOUT_PRINTED_COMPARATIVE_WINDOW"),
        # The window printed in the column itself binds it.
        ("Kỳ trước\nTừ 01/01/2024 đến 30/06/2024", [], "DURATION:RANGE:2024-01-01..2024-06-30", None),
        # "Cùng kỳ năm trước" and "Năm trước" print the prior-year relation.
        ("Cùng kỳ năm trước", ["Cho giai đoạn từ ngày 01/01/2025 đến ngày 30/06/2025"],
         "DURATION:CORRESPONDING_PRIOR_YEAR_RANGE:2025-01-01..2025-06-30", None),
        ("Năm trước", ["Cho năm tài chính kết thúc ngày 31 tháng 12 năm 2025"], "DURATION:YEAR:PRIOR_YEAR_OF(2025)", None),
        ("Kỳ này", ["Cho giai đoạn từ ngày 01/01/2025 đến ngày 30/06/2025"], "DURATION:RANGE:2025-01-01..2025-06-30", None),
    ],
)
def test_prior_period_relations_are_distinct(header, context, key, reason):
    descriptor = _period(header, context)
    assert descriptor.key == key
    if reason:
        assert descriptor.reason == reason
