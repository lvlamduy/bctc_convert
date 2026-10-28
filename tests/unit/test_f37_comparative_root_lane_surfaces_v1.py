"""F37 PRIMARY root comparative lane must not take the current period's year/date from the statement title.

Real shape: SSB Q1-2025 (FULL271 doc 178). KQKD columns "Lũy kế từ đầu năm đến cuối quý này: Năm nay | Năm trước"
under the title "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG RIÊNG / Quý I năm 2025"; note movement columns "Kỳ ba tháng kết thúc ngày
31/03/2025 | 31/03/2024". At 7b9756c6 the comparative root scope read calendar year 2025 from the title and the correct
Q1-2024 detail was rejected with CALENDAR_YEAR_CONFLICT.
"""
import pytest

from bctc_ai.evaluation.gemini_json_credit_risk_provision_expense_family_v1 import (
    _family37_period_compatibility_v1,
    _family37_period_scope_v1,
    _family37_root_lane_surfaces_v1,
)

TITLE = "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG RIÊNG\nQuý I năm 2025"
YTD = "Lũy kế từ đầu năm đến cuối quý này"


def _root(role, local):
    return _family37_period_scope_v1(_family37_root_lane_surfaces_v1(role, local, [TITLE]), semantic_role=role)


def _detail(text, role):
    return _family37_period_scope_v1([text, "Triệu VND"], semantic_role=role)


def test_ssb178_comparative_q1_prior_year_is_compatible():
    root = _root("COMPARATIVE_PERIOD", [YTD, "Năm trước"])
    assert root["calendar_year"] is None and root["end_date"] is None
    assert root["basis"] == "ELAPSED_FROM_YEAR_START" and root["elapsed_month_count"] == 3
    detail = _detail("Kỳ ba tháng kết thúc ngày 31/03/2024", "COMPARATIVE_PERIOD")
    assert _family37_period_compatibility_v1(detail, root) == (True, "EXACT_COMPATIBLE")


def test_ssb178_current_lane_keeps_the_title_year():
    root = _root("CURRENT_PERIOD", [YTD, "Năm nay"])
    assert root["calendar_year"] == 2025
    detail = _detail("Kỳ ba tháng kết thúc ngày 31/03/2025", "CURRENT_PERIOD")
    assert _family37_period_compatibility_v1(detail, root) == (True, "EXACT_COMPATIBLE")
    wrong = _detail("Kỳ ba tháng kết thúc ngày 31/03/2024", "CURRENT_PERIOD")
    assert _family37_period_compatibility_v1(wrong, root)[0] is False


def test_comparative_column_with_its_own_year_still_conflicts():
    # The column prints 2025 itself: nothing is stripped and a 2024 detail is still a conflict.
    root = _root("COMPARATIVE_PERIOD", [YTD, "Năm 2025"])
    assert root["calendar_year"] == 2025
    detail = _detail("Kỳ ba tháng kết thúc ngày 31/03/2024", "COMPARATIVE_PERIOD")
    assert _family37_period_compatibility_v1(detail, root) == (False, "CALENDAR_YEAR_CONFLICT")


@pytest.mark.parametrize("detail_text", [
    "Kỳ sáu tháng kết thúc ngày 30/06/2024",   # different elapsed window
    "Năm 2024",                                 # full prior year, not prior YTD
])
def test_comparative_window_must_still_match_by_printed_duration(detail_text):
    root = _root("COMPARATIVE_PERIOD", [YTD, "Năm trước"])
    detail = _detail(detail_text, "COMPARATIVE_PERIOD")
    assert _family37_period_compatibility_v1(detail, root)[0] is False


def test_title_words_are_kept_only_dates_and_years_are_dropped():
    surfaces = _family37_root_lane_surfaces_v1(
        "COMPARATIVE_PERIOD", ["Năm trước"], ["cho kỳ kế toán ba tháng kết thúc ngày 31/03/2025 năm 2025"])
    assert "31/03/2025" not in surfaces[1] and "2025" not in surfaces[1]
    assert "ba tháng kết thúc ngày" in surfaces[1]
    assert _family37_root_lane_surfaces_v1("CURRENT_PERIOD", ["Năm nay"], [TITLE]) == ["Năm nay", TITLE]
