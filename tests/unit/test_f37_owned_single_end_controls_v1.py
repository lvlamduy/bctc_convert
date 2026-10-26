"""F37 single printed duration end and known-end conflicts (Codex review 0399 / 0404)."""
import pytest

from bctc_ai.evaluation.gemini_json_credit_risk_provision_expense_family_v1 import (
    _family37_period_compatibility_v1,
    _family37_period_scope_v1,
)


@pytest.mark.parametrize("year,role", [(2025, "CURRENT_PERIOD"), (2024, "COMPARATIVE_PERIOD")])
def test_different_explicit_single_ends_stay_different(year, role):
    detail = _family37_period_scope_v1(
        f"Kỳ ba tháng kết thúc ngày 30/06/{year}", semantic_role=role
    )
    root = _family37_period_scope_v1(
        f"Kỳ ba tháng kết thúc ngày 31/03/{year}", semantic_role=role
    )
    assert detail["start_date"] is None
    assert detail["end_date"] == f"{year}-06-30"
    assert root["start_date"] is None
    assert root["end_date"] == f"{year}-03-31"
    assert not _family37_period_compatibility_v1(detail, root)[0]


def test_same_full_year_basis_keeps_off_calendar_end_conflict():
    detail = _family37_period_scope_v1(
        "Từ 01/07/2025 đến 30/06/2026", semantic_role="CURRENT_PERIOD"
    )
    root = _family37_period_scope_v1(
        "Cho năm tài chính kết thúc ngày 31/12/2025", semantic_role="CURRENT_PERIOD"
    )
    assert detail["basis"] == root["basis"] == "FULL_YEAR"
    assert root["start_date"] is None
    assert root["end_date"] == "2025-12-31"
    assert not _family37_period_compatibility_v1(detail, root)[0]


@pytest.mark.parametrize("surface", [
    "Cho năm tài chính kết thúc ngày 31/12/2025",
    "Từ 01/01/2025 đến 31/12/2025",
])
def test_existing_calendar_full_year_and_twelve_month_positive(surface):
    detail = _family37_period_scope_v1(surface, semantic_role="CURRENT_PERIOD")
    root = _family37_period_scope_v1(
        "Lũy kế 12 tháng từ đầu năm 2025", semantic_role="CURRENT_PERIOD"
    )
    assert _family37_period_compatibility_v1(detail, root) == (
        True, "FULL_YEAR_EQUIVALENT_TWELVE_MONTH_SCOPE"
    )


def test_legal_only_date_is_not_newly_bound_as_duration_end():
    title = (
        "NGÂN HÀNG THƯƠNG MẠI CỔ PHẦN SÀI GÒN THƯƠNG TÍN\nBIỂU SỐ: B03a/TCTD\n"
        "Ban hành theo Thông tư 49/2014/TT-NHNN ngày 31/12/2014 của Thống đốc NHNN VN\n"
        "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG\nQúy IV.2025"
    )
    root = _family37_period_scope_v1(
        ["Lũy kế từ đầu năm", "Năm nay", "(5)", title], semantic_role="CURRENT_PERIOD"
    )
    detail = _family37_period_scope_v1(
        "Từ 01/01/2025 đến 31/12/2025", semantic_role="CURRENT_PERIOD"
    )
    assert root["calendar_year"] == 2025
    assert root["start_date"] is None
    assert root["end_date"] is None
    assert _family37_period_compatibility_v1(detail, root) == (
        True, "FULL_YEAR_EQUIVALENT_TWELVE_MONTH_SCOPE"
    )


def test_identical_explicit_fiscal_full_year_windows_are_not_forced_to_calendar():
    scope = _family37_period_scope_v1(
        "Từ 01/07/2025 đến 30/06/2026", semantic_role="CURRENT_PERIOD"
    )
    assert scope["basis"] == "FULL_YEAR"
    assert _family37_period_compatibility_v1(scope, scope) == (True, "EXACT_COMPATIBLE")


def test_incomplete_ending_day_cannot_borrow_later_legal_date():
    scope = _family37_period_scope_v1(
        "Kỳ ba tháng kết thúc ngày 30, theo Thông tư ngày 31/03/2025",
        semantic_role="CURRENT_PERIOD",
    )
    assert scope["start_date"] is None
    assert scope["end_date"] is None


def test_written_complete_date_is_owned_by_its_ending_connector():
    scope = _family37_period_scope_v1(
        "Kỳ ba tháng kết thúc ngày 30 tháng 6 năm 2025",
        semantic_role="CURRENT_PERIOD",
    )
    assert scope["start_date"] is None
    assert scope["end_date"] == "2025-06-30"


# V6 additions: ASCII source with explicit Unicode escapes; UNRUN.
@pytest.mark.parametrize("year,role", [(2025, "CURRENT_PERIOD"), (2024, "COMPARATIVE_PERIOD")])
def test_numeric_single_end_without_ngay_keeps_different_windows(year, role):
    detail = _family37_period_scope_v1(
        f"K\u1ef3 ba th\u00e1ng k\u1ebft th\u00fac 30/06/{year}", semantic_role=role
    )
    root = _family37_period_scope_v1(
        f"K\u1ef3 ba th\u00e1ng k\u1ebft th\u00fac 31/03/{year}", semantic_role=role
    )
    assert detail["basis"] == root["basis"] == "ELAPSED_FROM_YEAR_START"
    assert detail["elapsed_month_count"] == root["elapsed_month_count"] == 3
    assert detail["start_date"] is root["start_date"] is None
    assert detail["end_date"] == f"{year}-06-30"
    assert root["end_date"] == f"{year}-03-31"
    assert _family37_period_compatibility_v1(detail, root) == (
        False, "EXACT_DATE_RANGE_ENDPOINT_CONFLICT"
    )


@pytest.mark.parametrize("role", ["CURRENT_PERIOD", "COMPARATIVE_PERIOD"])
def test_matching_numeric_single_end_without_ngay_remains_compatible(role):
    scope = _family37_period_scope_v1(
        "K\u1ef3 ba th\u00e1ng k\u1ebft th\u00fac 31/03/2025", semantic_role=role
    )
    assert scope["start_date"] is None and scope["end_date"] == "2025-03-31"
    assert _family37_period_compatibility_v1(scope, scope) == (True, "EXACT_COMPATIBLE")


def test_full_year_numeric_end_without_ngay_rejects_off_calendar_range():
    detail = _family37_period_scope_v1(
        "T\u1eeb 01/07/2025 \u0111\u1ebfn 30/06/2026", semantic_role="CURRENT_PERIOD"
    )
    root = _family37_period_scope_v1(
        "Cho n\u0103m t\u00e0i ch\u00ednh k\u1ebft th\u00fac 31/12/2025",
        semantic_role="CURRENT_PERIOD",
    )
    assert detail["basis"] == root["basis"] == "FULL_YEAR"
    assert root["start_date"] is None and root["end_date"] == "2025-12-31"
    assert _family37_period_compatibility_v1(detail, root) == (
        False, "EXACT_DATE_RANGE_ENDPOINT_CONFLICT"
    )


def test_incomplete_unprefixed_day_cannot_skip_ahead_to_later_legal_date():
    scope = _family37_period_scope_v1(
        "K\u1ef3 ba th\u00e1ng k\u1ebft th\u00fac 30, theo Th\u00f4ng t\u01b0 ng\u00e0y 31/03/2025",
        semantic_role="CURRENT_PERIOD",
    )
    assert scope["start_date"] is None and scope["end_date"] is None


@pytest.mark.parametrize("surface,basis", [
    ("31/03/2025", "UNKNOWN"),
    ("T\u1ea1i ng\u00e0y 31/03/2025", "STOCK_DATE"),
    ("As of 31/03/2025", "STOCK_DATE"),
])
def test_bare_and_as_of_dates_do_not_gain_duration_end(surface, basis):
    detail = _family37_period_scope_v1(surface, semantic_role="CURRENT_PERIOD")
    root = _family37_period_scope_v1(
        "Cho n\u0103m t\u00e0i ch\u00ednh k\u1ebft th\u00fac 31/12/2025",
        semantic_role="CURRENT_PERIOD",
    )
    assert detail["basis"] == basis
    assert detail["start_date"] is None and detail["end_date"] is None
    assert not _family37_period_compatibility_v1(detail, root)[0]
