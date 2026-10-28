"""F37 D2: an annual PRIMARY column printed exactly "Năm trước" is the fiscal year before the title's.

Real shape: EIB parent annual 2025 (FULL271 doc 39) p11, KQKD columns "Năm nay | Năm trước" under the title
"BÁO CÁO KẾT QUẢ HOẠT ĐỘNG RIÊNG / Cho năm tài chính kết thúc ngày 31 tháng 12 năm 2025". After 6996dae0 the
comparative lane had no year at all; D2 gives it fiscal 2024 only from that label + that annual title.
"""
import pytest

from bctc_ai.evaluation.gemini_json_credit_risk_provision_expense_family_v1 import (
    _family37_period_compatibility_v1,
    _family37_period_scope_v1,
    _family37_root_has_exact_period_axis_v1,
    _family37_root_lane_surfaces_v1,
)

ANNUAL = "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG RIÊNG\nCho năm tài chính kết thúc ngày 31 tháng 12 năm 2025"


def _scope(role, local, titles):
    return _family37_period_scope_v1(_family37_root_lane_surfaces_v1(role, local, titles), semantic_role=role)


def test_eib039_annual_prior_year_column_is_fiscal_2024():
    current = _scope("CURRENT_PERIOD", ["Năm nay"], [ANNUAL])
    comparative = _scope("COMPARATIVE_PERIOD", ["Năm trước"], [ANNUAL])
    assert (current["basis"], current["calendar_year"], current["end_date"]) == ("FULL_YEAR", 2025, "2025-12-31")
    assert (comparative["basis"], comparative["calendar_year"], comparative["end_date"]) == (
        "FULL_YEAR", 2024, "2024-12-31")
    assert any("F37 D2 derived" in item for item in comparative["raw_surface_axis"])
    root = {"period_scope_by_lane": {"CURRENT_PERIOD": current, "COMPARATIVE_PERIOD": comparative}}
    assert _family37_root_has_exact_period_axis_v1(root)
    detail = _family37_period_scope_v1(
        ["Biến động ... cho năm tài chính kết thúc ngày 31 tháng 12 năm 2024 như sau:"], semantic_role="COMPARATIVE_PERIOD")
    assert _family37_period_compatibility_v1(detail, comparative) == (True, "EXACT_COMPATIBLE")
    wrong = _family37_period_scope_v1(
        ["Biến động ... cho năm tài chính kết thúc ngày 31 tháng 12 năm 2025 như sau:"], semantic_role="COMPARATIVE_PERIOD")
    assert _family37_period_compatibility_v1(wrong, comparative)[0] is False


def test_numeric_fiscal_year_end_title_is_accepted():
    comparative = _scope("COMPARATIVE_PERIOD", ["Năm trước"], ["Cho năm kết thúc ngày 31/12/2025"])
    assert (comparative["calendar_year"], comparative["end_date"]) == (2024, "2024-12-31")


@pytest.mark.parametrize(("local", "titles"), [
    (["Kỳ trước"], [ANNUAL]),                                           # not the annual label
    (["Lũy kế từ đầu năm đến cuối quý này", "Năm trước"], [ANNUAL]),   # not exactly "Năm trước"
    (["Năm trước"], ["BÁO CÁO KẾT QUẢ HOẠT ĐỘNG RIÊNG\nQuý IV năm 2025"]),  # interim title
    (["Năm trước"], ["Cho kỳ kế toán sáu tháng kết thúc ngày 30 tháng 6 năm 2025"]),  # interim window
    (["Năm trước"], ["Cho năm tài chính kết thúc ngày 30 tháng 6 năm 2025"]),  # not a 31 December year end
    (["Năm trước"], [ANNUAL, "Cho năm tài chính kết thúc ngày 31 tháng 12 năm 2024"]),  # two fiscal years printed
])
def test_prior_year_is_not_derived_outside_the_exact_annual_shape(local, titles):
    comparative = _scope("COMPARATIVE_PERIOD", local, titles)
    assert comparative["calendar_year"] is None
    assert not any("F37 D2 derived" in item for item in comparative["raw_surface_axis"])


def test_current_lane_is_never_rewritten():
    assert _family37_root_lane_surfaces_v1("CURRENT_PERIOD", ["Năm trước"], [ANNUAL]) == ["Năm trước", ANNUAL]
