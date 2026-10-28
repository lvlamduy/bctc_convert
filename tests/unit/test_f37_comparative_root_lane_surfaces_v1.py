"""F37 PRIMARY root comparative lane must not take the current period's year/date from the statement title.

Real shape: SSB Q1-2025 (FULL271 doc 178). KQKD columns "Lũy kế từ đầu năm đến cuối quý này: Năm nay | Năm trước"
under the title "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG RIÊNG / Quý I năm 2025"; note movement columns "Kỳ ba tháng kết thúc ngày
31/03/2025 | 31/03/2024". At 7b9756c6 the comparative root scope read calendar year 2025 from the title and the correct
Q1-2024 detail was rejected with CALENDAR_YEAR_CONFLICT. At 6996dae0 the year was dropped and left unknown, which
also accepted a 2023 detail (Codex 0563). The comparative year is now the title window one year earlier, derived from
the lane's own "Năm trước" label and recorded as a structured derivation, or the lane withholds permission.
"""
import pytest

from bctc_ai.evaluation.gemini_json_credit_risk_provision_expense_family_v1 import (
    PRIMARY_COMPARATIVE_YEAR_NOT_PROVEN,
    _family37_period_compatibility_v1,
    _family37_period_scope_v1,
    _family37_root_lane_scope_v1,
    _family37_root_lane_surfaces_v1,
)

TITLE = "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG RIÊNG\nQuý I năm 2025"
YTD = "Lũy kế từ đầu năm đến cuối quý này"


def _root(role, local, title=TITLE):
    return _family37_root_lane_scope_v1(role, local, [title])


def _detail(text, role):
    return _family37_period_scope_v1([text, "Triệu VND"], semantic_role=role)


def test_ssb178_comparative_lane_is_the_title_window_one_year_earlier():
    root = _root("COMPARATIVE_PERIOD", [YTD, "Năm trước"])
    assert root["basis"] == "ELAPSED_FROM_YEAR_START" and root["elapsed_month_count"] == 3
    assert root["calendar_year"] == 2024 and root["reasons"] == []
    derivation = root["derivation"]
    assert derivation["column_header_path_exact"] == [YTD, "Năm trước"]
    assert derivation["title_surfaces_exact"] == [TITLE]
    assert (derivation["title_calendar_year"], derivation["derived_calendar_year"]) == (2025, 2024)
    detail = _detail("Kỳ ba tháng kết thúc ngày 31/03/2024", "COMPARATIVE_PERIOD")
    assert _family37_period_compatibility_v1(detail, root) == (True, "EXACT_COMPATIBLE")


@pytest.mark.parametrize("year", [2023, 2025])
def test_ssb178_comparative_lane_rejects_a_wrong_detail_year(year):
    root = _root("COMPARATIVE_PERIOD", [YTD, "Năm trước"])
    detail = _detail(f"Kỳ ba tháng kết thúc ngày 31/03/{year}", "COMPARATIVE_PERIOD")
    assert _family37_period_compatibility_v1(detail, root) == (False, "CALENDAR_YEAR_CONFLICT")


@pytest.mark.parametrize("local", [
    [YTD, "Kỳ trước"],          # not the "Năm trước" label
    [YTD],                        # no comparative label at all
    ["Năm nay", "Năm trước"],    # two period-role labels
])
def test_unknown_comparative_year_withholds_permission(local):
    root = _root("COMPARATIVE_PERIOD", local)
    assert root["calendar_year"] is None and "derivation" not in root
    assert PRIMARY_COMPARATIVE_YEAR_NOT_PROVEN in root["reasons"]
    for year in (2023, 2024, 2025):
        detail = _detail(f"Kỳ ba tháng kết thúc ngày 31/03/{year}", "COMPARATIVE_PERIOD")
        assert _family37_period_compatibility_v1(detail, root) == (False, PRIMARY_COMPARATIVE_YEAR_NOT_PROVEN)


def test_title_printing_two_years_withholds_permission():
    root = _root("COMPARATIVE_PERIOD", [YTD, "Năm trước"], "Quý I năm 2025 (so sánh năm 2024)")
    assert PRIMARY_COMPARATIVE_YEAR_NOT_PROVEN in root["reasons"]


def test_ssb178_current_lane_keeps_the_title_year():
    root = _root("CURRENT_PERIOD", [YTD, "Năm nay"])
    assert root["calendar_year"] == 2025 and "derivation" not in root
    detail = _detail("Kỳ ba tháng kết thúc ngày 31/03/2025", "CURRENT_PERIOD")
    assert _family37_period_compatibility_v1(detail, root) == (True, "EXACT_COMPATIBLE")
    wrong = _detail("Kỳ ba tháng kết thúc ngày 31/03/2024", "CURRENT_PERIOD")
    assert _family37_period_compatibility_v1(wrong, root)[0] is False


def test_comparative_column_with_its_own_year_still_conflicts():
    # The column prints 2025 itself: nothing is stripped or derived and a 2024 detail is still a conflict.
    root = _root("COMPARATIVE_PERIOD", [YTD, "Năm 2025"])
    assert root["calendar_year"] == 2025 and "derivation" not in root
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
