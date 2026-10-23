"""Draft-only named-quarter YTD tests; local calendar proof is not financial admission."""

from __future__ import annotations

import unicodedata
from copy import deepcopy

import pytest
from test_gemini_json_income_tax_family_v1 import _adapter_compiled
from test_gemini_json_income_tax_signed_display_v1 import _contextual_period_records

from bctc_ai.evaluation import gemini_json_income_tax_family_v1 as family

QUARTERS = {"I": (1, 3, 31), "II": (2, 6, 30), "III": (3, 9, 30), "IV": (4, 12, 31)}


def _records(quarter="II", *, spelling="Lũy", prior=2024, scope="riêng", marker=True):
    records = _contextual_period_records(quarter=quarter, absolute_primary=True,
                                         include_cash_flow=False, scope=scope)
    section = records[1]["page_json"]["sections"][0]
    table = section["tables"][0]
    number, month, day = QUARTERS[quarter]
    section["title_exact"] = (f"Báo cáo kết quả hoạt động {scope}\n"
                              f"Cho kỳ hoạt động {month} tháng kết thúc ngày {day} tháng {month} năm 2026")
    table["title_exact"] = None
    for index, column in enumerate(table["columns"]):
        stem = f"Quý {quarter}" if index < 2 else f"{spelling} kế từ đầu năm đến cuối Quý {quarter}"
        year = 2026 if index % 2 == 0 else prior
        column["header_path_exact"] = [stem, ("Năm " if marker else "") + str(year), "Triệu đồng"]
    return records


def _probe(records):
    section = records[1]["page_json"]["sections"][0]
    table = section["tables"][0]
    lane = family._multitable_lane_axis(section, table, compiled_specs=_adapter_compiled())
    proof = family._printed_ytd_sibling_period_evidence(section, table, lane)
    return section, table, lane, proof


@pytest.mark.parametrize("quarter", ["I", "II", "III", "IV"])
@pytest.mark.parametrize("spelling", ["Lũy", "Luỹ"])
def test_named_quarter_ytd_requires_all_four_printed_quarters_and_absolute_years(quarter, spelling):
    records = _records(quarter, spelling=spelling)
    before = deepcopy(records)
    section, table, lane, proof = _probe(records)
    number = QUARTERS[quarter][0]
    expected = [["ANNUAL_YEAR", year] if number == 4 else ["SOURCE_YTD_QUARTER", year, number]
                for year in (2026, 2024)]
    assert lane["complete"] is True and lane["money_column_ordinals"] == [3, 4]
    assert lane["excluded_parallel_duration_money_column_ordinals"] == [1, 2]
    assert proof is not None and proof["quarter"] == number
    assert proof["printed_absolute_year_tokens"] == ["2026", "2024"]
    assert proof["relative_year_tokens"] is None and proof["intrinsic_absolute_periods"] == expected
    assert proof["cumulative_columns_exact"] == table["columns"][2:]
    assert family._absolute_source_duration_semantics(section, table, lane) == expected
    assert records == before


@pytest.mark.parametrize("presentation", ["bare_numeric_year", "nfd", "numeric_quarter", "serialized_newline"])
def test_named_quarter_raw_layout_retains_exact_columns_and_allows_only_finite_tokens(presentation):
    records = _records(marker=presentation != "bare_numeric_year")
    section, table, _lane, _proof = _probe(records)
    if presentation == "nfd":
        for column in table["columns"]:
            column["header_path_exact"] = [unicodedata.normalize("NFD", part) for part in column["header_path_exact"]]
    elif presentation == "numeric_quarter":
        for column in table["columns"]:
            column["header_path_exact"][0] = column["header_path_exact"][0].replace("Quý II", "Quý 2")
    elif presentation == "serialized_newline":
        for column in table["columns"]:
            column["header_path_exact"][0] = column["header_path_exact"][0].replace("cuối Quý", "cuối\\nQuý")
    before = deepcopy(records)
    _section, table, _lane, proof = _probe(records)
    assert proof is not None
    assert proof["intrinsic_absolute_periods"] == [["SOURCE_YTD_QUARTER", 2026, 2], ["SOURCE_YTD_QUARTER", 2024, 2]]
    assert proof["cumulative_columns_exact"] == table["columns"][2:]
    assert records == before


@pytest.mark.parametrize("mutation", [
    "one_named", "both_named_wrong_quarter", "parallel_wrong_quarter", "one_current_frame", "relative_years",
    "prior_year_mismatch", "reversed_years", "annotated_quarter", "fullwidth_quarter", "annotated_year",
    "fullwidth_year", "restated", "extra_assertion", "unknown_unit",
])
def test_named_quarter_cannot_erase_annotations_mixed_frames_or_unmatched_four_header_axes(mutation):
    records = _records()
    section, table, _lane, _proof = _probe(records)
    if mutation == "one_named":
        table["columns"][3]["header_path_exact"][0] = "Lũy kế từ đầu năm"
    elif mutation == "both_named_wrong_quarter":
        for column in table["columns"][2:]:
            column["header_path_exact"][0] = column["header_path_exact"][0].replace("II", "III")
    elif mutation == "parallel_wrong_quarter":
        table["columns"][1]["header_path_exact"][0] = "Quý III"
    elif mutation == "one_current_frame":
        table["columns"][3]["header_path_exact"][0] = "Lũy kế từ đầu năm nay đến cuối quý này"
    elif mutation == "relative_years":
        for index, column in enumerate(table["columns"]):
            column["header_path_exact"][1] = "Năm nay" if index % 2 == 0 else "Năm trước"
    elif mutation == "prior_year_mismatch":
        table["columns"][3]["header_path_exact"][1] = "Năm 2025"
    elif mutation == "reversed_years":
        for index, column in enumerate(table["columns"]):
            column["header_path_exact"][1] = "Năm 2024" if index % 2 == 0 else "Năm 2026"
    elif mutation in {"annotated_quarter", "fullwidth_quarter"}:
        table["columns"][3]["header_path_exact"][0] = table["columns"][3]["header_path_exact"][0].replace(
            "II", "I\u0301I" if mutation == "annotated_quarter" else "Ⅱ")
    elif mutation in {"annotated_year", "fullwidth_year"}:
        table["columns"][3]["header_path_exact"][1] = "Năm 202\u03014" if mutation == "annotated_year" else "Năm ２０２４"
    elif mutation == "restated":
        for column in table["columns"][2:]:
            column["header_path_exact"].append("(Trình bày lại)")
    elif mutation == "extra_assertion":
        table["columns"][3]["header_path_exact"].append("Quý I năm 2023")
    else:
        table["columns"][3]["header_path_exact"][2] = "Triệu USD"
    before = deepcopy(records)
    assert _probe(records)[3] is None
    assert records == before


@pytest.mark.parametrize("axis", ["selected", "excluded", "unknown_kind"])
def test_named_quarter_is_not_permission_to_rewrite_or_guess_the_selected_money_axis(axis):
    records = _records()
    section, table, lane, _proof = _probe(records)
    if axis == "selected":
        lane["money_column_ordinals"] = [1, 2]
    elif axis == "excluded":
        lane["excluded_parallel_duration_money_column_ordinals"] = [2, 1]
    else:
        table["columns"][3]["value_kind"] = "UNKNOWN"
    before = deepcopy((records, lane))
    assert family._printed_ytd_sibling_period_evidence(section, table, lane) is None
    assert (records, lane) == before


def test_named_quarter_local_calendar_does_not_supply_missing_scope_or_override_owned_caption():
    records = _records(scope="")
    section, table, lane, proof = _probe(records)
    assert proof is not None  # Explicit printed years still prove a LOCAL header calendar.
    assert proof["intrinsic_absolute_periods"] == [["SOURCE_YTD_QUARTER", 2026, 2], ["SOURCE_YTD_QUARTER", 2024, 2]]
    scope = family._note_report_scope_receipt(section, table, source_paths=[],
                                              document_scope=family._document_report_scope_receipt(records))
    assert scope["report_scope"] is None  # No financial/scope admission is asserted here.
    table["title_exact"] = "Báo cáo kết quả hoạt động cho quý II năm 2025"
    before = deepcopy(records)
    assert family._printed_ytd_sibling_period_evidence(section, table, lane) is not None
    assert family._absolute_source_duration_semantics(section, table, lane) is None
    assert records == before
