"""F37 first-quarter equivalence needs source-owned calendar-Q1 start on both scopes (Codex review 0408 / 0409)."""
import pytest

from bctc_ai.evaluation.gemini_json_credit_risk_provision_expense_family_v1 import (
    _family37_period_compatibility_v1,
    _family37_period_scope_v1,
)


def _pair(raw, *, role="CURRENT_PERIOD", reverse=False):
    year = 2025 if role == "CURRENT_PERIOD" else 2024
    elapsed = _family37_period_scope_v1(raw, semantic_role=role)
    quarter = _family37_period_scope_v1(f"Qu\u00fd 1/{year}", semantic_role=role)
    assert elapsed["basis"] == "ELAPSED_FROM_YEAR_START"
    assert elapsed["elapsed_month_count"] == 3
    assert quarter["basis"] == "SINGLE_QUARTER" and quarter["quarter_ordinal"] == 1
    return (quarter, elapsed) if reverse else (elapsed, quarter)


@pytest.mark.parametrize("role", ["CURRENT_PERIOD", "COMPARATIVE_PERIOD"])
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("kind", ["bare_three_months", "from_period_start"])
def test_ambiguous_three_months_never_supplies_calendar_year_start(role, reverse, kind):
    year = 2025 if role == "CURRENT_PERIOD" else 2024
    raw = (f"K\u1ef3 ba th\u00e1ng {year}" if kind == "bare_three_months" else
           f"K\u1ef3 ba th\u00e1ng t\u1eeb \u0111\u1ea7u k\u1ef3 {year}")
    detail, root = _pair(raw, role=role, reverse=reverse)
    elapsed = root if reverse else detail
    assert elapsed["quarter_ordinal"] is None
    assert elapsed["start_date"] is None and elapsed["end_date"] is None
    assert _family37_period_compatibility_v1(detail, root) == (False, "FIRST_QUARTER_WINDOW_NOT_PROVEN")


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("authority", ["explicit_year_start", "printed_ocb_q1", "printed_exact_range"])
def test_owned_year_start_q1_or_exact_range_remains_positive(reverse, authority):
    if authority == "explicit_year_start":
        raw = "L\u0169y k\u1ebf 3 th\u00e1ng t\u1eeb \u0111\u1ea7u n\u0103m 2025"
    elif authority == "printed_ocb_q1":
        raw = ["S\u1ed1 lu\u1ef9 k\u1ebf t\u1eeb \u0111\u1ea7u n\u0103m \u0111\u1ebfn cu\u1ed1i Q1.2025",
               "B\u00c1O C\u00c1O K\u1ebeT QU\u1ea2 HO\u1ea0T \u0110\u1ed8NG\nQu\u00fd 01 n\u0103m 2025"]
    else:
        raw = "T\u1eeb 01/01/2025 \u0111\u1ebfn 31/03/2025"
    detail, root = _pair(raw, reverse=reverse)
    assert _family37_period_compatibility_v1(detail, root) == (
        True, "FIRST_QUARTER_EQUIVALENT_THREE_MONTH_SCOPE"
    )


@pytest.mark.parametrize("bad_date", ["30/06/2025", "31/03/2024"])
def test_original_all_raw_date_veto_still_applies_after_owned_start(bad_date):
    raw = ["L\u0169y k\u1ebf 3 th\u00e1ng t\u1eeb \u0111\u1ea7u n\u0103m 2025", bad_date]
    detail, root = _pair(raw)
    assert _family37_period_compatibility_v1(detail, root) == (False, "FIRST_QUARTER_WINDOW_NOT_PROVEN")


@pytest.mark.parametrize("raw", [
    "K\u1ef3 ba th\u00e1ng 2025 theo Th\u00f4ng t\u01b0 \u00e1p d\u1ee5ng t\u1eeb \u0111\u1ea7u n\u0103m 2025 ng\u00e0y 31/03/2025",
    "L\u0169y k\u1ebf 3 th\u00e1ng t\u1eeb \u0111\u1ea7u n\u0103m t\u00e0i ch\u00ednh 2025",
])
def test_legal_or_fiscal_tail_is_not_stripped_into_calendar_assertion(raw):
    detail, root = _pair(raw)
    assert _family37_period_compatibility_v1(detail, root) == (False, "FIRST_QUARTER_WINDOW_NOT_PROVEN")


def test_two_unlinked_raw_date_snippets_do_not_prove_printed_range():
    detail, root = _pair(["K\u1ef3 ba th\u00e1ng 2025", "01/01/2025", "31/03/2025"])
    # Existing parser pairs raw dates; the new authority requires an actual from/to clause.
    assert (detail["start_date"], detail["end_date"]) == ("2025-01-01", "2025-03-31")
    assert _family37_period_compatibility_v1(detail, root) == (False, "FIRST_QUARTER_WINDOW_NOT_PROVEN")


def test_foreign_year_start_assertion_cannot_borrow_scope_year():
    detail, root = _pair(["K\u1ef3 ba th\u00e1ng 2025",
                          "L\u0169y k\u1ebf 3 th\u00e1ng t\u1eeb \u0111\u1ea7u n\u0103m 2024"])
    assert detail["calendar_year"] == root["calendar_year"] == 2025
    assert _family37_period_compatibility_v1(detail, root) == (False, "FIRST_QUARTER_WINDOW_NOT_PROVEN")


def test_explicit_fiscal_q1_without_calendar_range_does_not_grant_january_start():
    raw = "S\u1ed1 l\u0169y k\u1ebf t\u1eeb \u0111\u1ea7u n\u0103m t\u00e0i ch\u00ednh \u0111\u1ebfn cu\u1ed1i Q1.2025"
    detail, root = _pair(raw)
    assert detail["quarter_ordinal"] == 1 and detail["start_date"] is None
    assert _family37_period_compatibility_v1(detail, root) == (False, "FIRST_QUARTER_WINDOW_NOT_PROVEN")


def test_financial_statement_title_is_not_a_fiscal_year_marker():
    raw = ["S\u1ed1 l\u0169y k\u1ebf t\u1eeb \u0111\u1ea7u n\u0103m \u0111\u1ebfn cu\u1ed1i Q1.2025",
           "B\u00e1o c\u00e1o t\u00e0i ch\u00ednh n\u0103m 2025"]
    detail, root = _pair(raw)
    assert _family37_period_compatibility_v1(detail, root) == (
        True, "FIRST_QUARTER_EQUIVALENT_THREE_MONTH_SCOPE"
    )


def test_explicit_same_clause_calendar_range_can_resolve_fiscal_q1_start():
    raw = ["S\u1ed1 l\u0169y k\u1ebf t\u1eeb \u0111\u1ea7u n\u0103m t\u00e0i ch\u00ednh \u0111\u1ebfn cu\u1ed1i Q1.2025",
           "T\u1eeb 01/01/2025 \u0111\u1ebfn 31/03/2025"]
    detail, root = _pair(raw)
    assert _family37_period_compatibility_v1(detail, root) == (
        True, "FIRST_QUARTER_EQUIVALENT_THREE_MONTH_SCOPE"
    )


# V2 additions: original 23 controls retained, including now-reachable range positives.
@pytest.mark.parametrize("role", ["CURRENT_PERIOD", "COMPARATIVE_PERIOD"])
@pytest.mark.parametrize("reverse", [False, True])
def test_fiscal_single_quarter_cannot_borrow_other_sides_calendar_start(role, reverse):
    year = 2025 if role == "CURRENT_PERIOD" else 2024
    fiscal = _family37_period_scope_v1(
        f"Qu\u00fd 1 n\u0103m t\u00e0i ch\u00ednh {year}", semantic_role=role)
    elapsed = _family37_period_scope_v1(
        f"L\u0169y k\u1ebf 3 th\u00e1ng t\u1eeb \u0111\u1ea7u n\u0103m {year}", semantic_role=role)
    assert fiscal["basis"] == "SINGLE_QUARTER" and fiscal["quarter_ordinal"] == 1
    assert fiscal["start_date"] is None and fiscal["end_date"] is None
    assert elapsed["basis"] == "ELAPSED_FROM_YEAR_START" and elapsed["elapsed_month_count"] == 3
    detail, root = (elapsed, fiscal) if reverse else (fiscal, elapsed)
    assert _family37_period_compatibility_v1(detail, root) == (False, "FIRST_QUARTER_WINDOW_NOT_PROVEN")


def test_numeric_space_dates_do_not_turn_normalized_tokens_into_raw_date_proof():
    detail, root = _pair("K\u1ef3 ba th\u00e1ng t\u1eeb 01 01 2025 \u0111\u1ebfn 31 03 2025")
    assert detail["start_date"] is None and detail["end_date"] is None
    assert _family37_period_compatibility_v1(detail, root) == (False, "FIRST_QUARTER_WINDOW_NOT_PROVEN")
    # Adversarial claimed bounds still cannot replace a complete date parsed from actual RAW.
    claimed = dict(detail, start_date="2025-01-01", end_date="2025-03-31")
    assert _family37_period_compatibility_v1(claimed, root) == (False, "FIRST_QUARTER_WINDOW_NOT_PROVEN")


# V3: formats already decoded by the existing RAW date parser; no new date codec.
@pytest.mark.parametrize("raw", [
    "T\u1eeb ng\u00e0y 1 th\u00e1ng 1 n\u0103m 2025 \u0111\u1ebfn ng\u00e0y 31 th\u00e1ng 3 n\u0103m 2025",
    "T\u1eeb 01/01/2025 \u0111\u1ebfn ng\u00e0y 31 th\u00e1ng 3 n\u0103m 2025",
    "T\u1eeb ng\u00e0y 1 th\u00e1ng 1 n\u0103m 2025 \u0111\u1ebfn 31/03/2025",
    "From 01/01/2025 To 31/03/2025",
])
def test_existing_written_or_mixed_raw_date_codec_preserves_owned_range_positive(raw):
    detail, root = _pair(raw)
    assert detail["start_date"] == "2025-01-01" and detail["end_date"] == "2025-03-31"
    assert detail["quarter_ordinal"] is None
    assert _family37_period_compatibility_v1(detail, root) == (
        True, "FIRST_QUARTER_EQUIVALENT_THREE_MONTH_SCOPE"
    )


# V4: recognized own assertions must all agree BEFORE range/Q1/year-start grants.
@pytest.mark.parametrize("role", ["CURRENT_PERIOD", "COMPARATIVE_PERIOD"])
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("assertion_order", ["matching_first", "conflicting_first"])
@pytest.mark.parametrize("early_authority", ["none", "q1", "range"])
def test_conflicting_owned_year_start_assertions_cannot_choose_first(role, reverse, assertion_order, early_authority):
    year = 2025 if role == "CURRENT_PERIOD" else 2024
    if early_authority == "q1":
        anchor = f"S\u1ed1 l\u0169y k\u1ebf t\u1eeb \u0111\u1ea7u n\u0103m \u0111\u1ebfn cu\u1ed1i Q1.{year}"
    elif early_authority == "range":
        anchor = f"T\u1eeb 01/01/{year} \u0111\u1ebfn 31/03/{year}"
    else:
        anchor = f"K\u1ef3 ba th\u00e1ng {year}"
    assertions = [f"L\u0169y k\u1ebf 3 th\u00e1ng t\u1eeb \u0111\u1ea7u n\u0103m {year}",
                  f"L\u0169y k\u1ebf 3 th\u00e1ng t\u1eeb \u0111\u1ea7u n\u0103m {year - 1}"]
    if assertion_order == "conflicting_first":
        assertions.reverse()
    detail, root = _pair([anchor, *assertions], role=role, reverse=reverse)
    elapsed = root if reverse else detail
    assert elapsed["calendar_year"] == year
    if early_authority == "q1":
        assert elapsed["quarter_ordinal"] == 1
    if early_authority == "range":
        assert (elapsed["start_date"], elapsed["end_date"]) == (f"{year}-01-01", f"{year}-03-31")
    assert _family37_period_compatibility_v1(detail, root) == (False, "FIRST_QUARTER_WINDOW_NOT_PROVEN")


def test_unrelated_legal_year_is_not_a_recognized_year_start_assertion():
    detail, root = _pair([
        "L\u0169y k\u1ebf 3 th\u00e1ng t\u1eeb \u0111\u1ea7u n\u0103m 2025",
        "Theo Th\u00f4ng t\u01b0 s\u1ed1 49/2014/TT-NHNN",
    ])
    # This legal reference is a year, NOT a complete date; the prior raw-date veto is unchanged.
    assert detail["calendar_year"] == 2025
    assert _family37_period_compatibility_v1(detail, root) == (
        True, "FIRST_QUARTER_EQUIVALENT_THREE_MONTH_SCOPE"
    )


@pytest.mark.parametrize("qualifier", ["fiscal year", "financial year"])
def test_explicit_english_fiscal_single_q1_needs_own_calendar_range(qualifier):
    detail = _family37_period_scope_v1(f"Q1 {qualifier} 2025", semantic_role="CURRENT_PERIOD")
    root = _family37_period_scope_v1(
        "L\u0169y k\u1ebf 3 th\u00e1ng t\u1eeb \u0111\u1ea7u n\u0103m 2025", semantic_role="CURRENT_PERIOD")
    assert detail["basis"] == "SINGLE_QUARTER" and detail["quarter_ordinal"] == 1
    assert detail["start_date"] is None and detail["end_date"] is None
    assert _family37_period_compatibility_v1(detail, root) == (False, "FIRST_QUARTER_WINDOW_NOT_PROVEN")


def test_clear_fy_year_single_q1_needs_own_calendar_range():
    detail = _family37_period_scope_v1("Q1 FY2025", semantic_role="CURRENT_PERIOD")
    root = _family37_period_scope_v1(
        "L\u0169y k\u1ebf 3 th\u00e1ng t\u1eeb \u0111\u1ea7u n\u0103m 2025", semantic_role="CURRENT_PERIOD")
    assert detail["basis"] == "SINGLE_QUARTER" and detail["quarter_ordinal"] == 1
    assert detail["calendar_year"] == 2025
    assert _family37_period_compatibility_v1(detail, root) == (False, "FIRST_QUARTER_WINDOW_NOT_PROVEN")
