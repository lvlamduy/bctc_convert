"""F37 D2: an annual PRIMARY column printed exactly "Năm trước" is the fiscal year before the title's.

Real shape: EIB parent annual 2025 (FULL271 doc 39) p11, KQKD columns "Năm nay | Năm trước" under the title
"BÁO CÁO KẾT QUẢ HOẠT ĐỘNG RIÊNG / Cho năm tài chính kết thúc ngày 31 tháng 12 năm 2025". The comparative lane gets
fiscal 2024 (end 31/12/2024) as a structured derivation next to the exact title and column labels; the raw surface
axis carries no invented text.
"""
import pytest

from bctc_ai.evaluation.gemini_json_credit_risk_provision_expense_family_v1 import (
    PRIMARY_COMPARATIVE_YEAR_NOT_PROVEN,
    _family37_period_compatibility_v1,
    _family37_period_scope_v1,
    _family37_root_has_exact_period_axis_v1,
    _family37_root_lane_scope_v1,
    _family37_root_lane_surfaces_v1,
)

ANNUAL = "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG RIÊNG\nCho năm tài chính kết thúc ngày 31 tháng 12 năm 2025"


def _scope(role, local, titles):
    return _family37_root_lane_scope_v1(role, local, titles)


def test_eib039_annual_prior_year_column_is_fiscal_2024():
    current = _scope("CURRENT_PERIOD", ["Năm nay"], [ANNUAL])
    comparative = _scope("COMPARATIVE_PERIOD", ["Năm trước"], [ANNUAL])
    assert (current["basis"], current["calendar_year"], current["end_date"]) == ("FULL_YEAR", 2025, "2025-12-31")
    assert (comparative["basis"], comparative["calendar_year"], comparative["end_date"]) == (
        "FULL_YEAR", 2024, "2024-12-31")
    assert comparative["derivation"]["title_surfaces_exact"] == [ANNUAL]
    assert comparative["derivation"]["column_header_path_exact"] == ["Năm trước"]
    assert not any("2024" in item for item in comparative["raw_surface_axis"])  # literal surfaces only
    root = {"period_scope_by_lane": {"CURRENT_PERIOD": current, "COMPARATIVE_PERIOD": comparative}}
    assert _family37_root_has_exact_period_axis_v1(root)
    detail = _family37_period_scope_v1(
        ["Biến động ... cho năm tài chính kết thúc ngày 31 tháng 12 năm 2024 như sau:"], semantic_role="COMPARATIVE_PERIOD")
    assert _family37_period_compatibility_v1(detail, comparative) == (True, "EXACT_COMPATIBLE")
    for year in (2023, 2025):
        wrong = _family37_period_scope_v1(
            [f"Biến động ... cho năm tài chính kết thúc ngày 31 tháng 12 năm {year} như sau:"],
            semantic_role="COMPARATIVE_PERIOD")
        assert _family37_period_compatibility_v1(wrong, comparative)[0] is False


def test_numeric_fiscal_year_end_title_is_accepted():
    comparative = _scope("COMPARATIVE_PERIOD", ["Năm trước"], ["Cho năm kết thúc ngày 31/12/2025"])
    assert (comparative["calendar_year"], comparative["end_date"]) == (2024, "2024-12-31")


def test_leap_day_endpoint_is_not_shifted():
    comparative = _scope("COMPARATIVE_PERIOD", ["Năm trước"], ["Cho kỳ kế toán từ 01/01/2024 đến 29/02/2024"])
    assert PRIMARY_COMPARATIVE_YEAR_NOT_PROVEN in comparative["reasons"]


@pytest.mark.parametrize(("local", "titles"), [
    (["Kỳ trước"], [ANNUAL]),                                           # not the "Năm trước" label
    (["Năm trước"], [ANNUAL, "Cho năm tài chính kết thúc ngày 31 tháng 12 năm 2024"]),  # two years printed
])
def test_prior_year_is_not_derived_outside_the_exact_shape(local, titles):
    comparative = _scope("COMPARATIVE_PERIOD", local, titles)
    assert comparative["calendar_year"] is None and "derivation" not in comparative
    assert PRIMARY_COMPARATIVE_YEAR_NOT_PROVEN in comparative["reasons"]


def test_current_lane_is_never_rewritten():
    assert _family37_root_lane_surfaces_v1("CURRENT_PERIOD", ["Năm trước"], [ANNUAL]) == ["Năm trước", ANNUAL]
    assert "derivation" not in _scope("CURRENT_PERIOD", ["Năm trước"], [ANNUAL])
