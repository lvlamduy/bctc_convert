"""INACTIVE proposed unit module; not executed or actual FULL117/118 admission.

Intended target: tests/unit/test_gemini_json_income_tax_first_months_narrative_v1.py.
Base evaluator SHA177521586f3ff794e06345e2df5bd996a99d615939f0980940450b43692522e6.
Only synthetic existing-fixture source-period paths; no provider/PDF/database.
"""
import unicodedata
from copy import deepcopy
from hashlib import sha256

import pytest
from test_gemini_json_income_tax_family_v1 import (
    _adapter_compiled,
    _primary_page,
    _primary_record,
    _row,
)

from bctc_ai.evaluation.gemini_json_income_tax_family_v1 import (
    GeminiJsonIncomeTaxFamilyV1Error,
    _document_statement_period_inventory,
    _multitable_lane_axis,
    _owned_current_period_constraints,
    _owned_current_period_constraints_match,
    _owned_relative_year_duration_evidence,
    _record_locator,
    _source_period_correspondence_receipt,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _fixture(months=6, year=2025, *, narrative=None, relative=None, start_month=1):
    days = {3: 31, 6: 30, 9: 30, 12: 31}
    page = _primary_page([_row("Chi phí thuế TNDN hiện hành", "1", "2")])
    section = page["sections"][0]
    section["title_exact"] = "Báo cáo kết quả hoạt động riêng giữa niên độ"
    section["narratives_exact"] = [narrative if narrative is not None else f"Cho kỳ kế toán {months} tháng đầu năm {year}"]
    table = section["tables"][0]
    headers = relative or tuple(f"Từ 01/{start_month:02d}/{y} đến {days[months]:02d}/{months:02d}/{y}" for y in (year, year - 1))
    table["columns"] = [{"header_path_exact": [header], "value_kind": "MONEY"} for header in headers]
    return [_primary_record(page)], section, table


def _proof(records, inventory=None):
    compiled = _adapter_compiled()
    record = records[0]
    section, table = record["page_json"]["sections"][0], record["page_json"]["sections"][0]["tables"][0]
    lane = _multitable_lane_axis(section, table, compiled_specs=compiled)
    loc = _record_locator(record, section_id="s1", table_id="t1")
    return _source_period_correspondence_receipt(
        left_locator=loc, right_locator=loc,
        left_money_column_ordinals=lane["money_column_ordinals"],
        right_money_column_ordinals=lane["money_column_ordinals"],
        page_records=records, compiled_specs=compiled,
        document_period_inventory=inventory or _document_statement_period_inventory(records, compiled_specs=compiled),
    )


@pytest.mark.parametrize("months", [3, 6, 9, 12])
def test_first_months_narrative_requires_independent_explicit_pair(months):
    records, section, table = _fixture(months)
    before = deepcopy(records)
    constraint = _owned_current_period_constraints(section, table)[0]
    assert constraint["supported"] is True
    assert constraint["printed_months"] == months
    assert constraint["printed_reporting_quarter"] == months // 3
    assert "printed_end_date" not in constraint and "printed_start_date" not in constraint
    evidence = constraint["source_first_calendar_months_evidence"]
    assert evidence["semantic_origin"] == "FIRST_N_CALENDAR_MONTHS_OF_YEAR"
    assert evidence["literal_quarter_printed"] is False
    assert evidence["literal_endpoint_date_printed"] is False
    assert evidence["comparative_period_authority_granted"] is False
    assert evidence["source_sha256"] == sha256(section["narratives_exact"][0].encode()).hexdigest()
    proof = _proof(records)
    assert proof["complete"] is True and proof["status"] == "PASS_LITERAL_SOURCE_DURATION"
    assert proof["period_resolution_evidence"] == []
    assert records == before


@pytest.mark.parametrize("transform", [
    lambda s: unicodedata.normalize("NFD", s),
    lambda s: s.upper(),
    lambda s: s.replace(" ", "\n"),
    lambda s: s.replace(" ", "\\n"),
    lambda s: s.replace(" ", "\u00a0"),
])
def test_first_months_layout_keeps_exact_raw_source(transform):
    raw = transform("Cho kỳ kế toán 6 tháng đầu năm 2025")
    records, section, table = _fixture(narrative=raw)
    constraint = _owned_current_period_constraints(section, table)[0]
    assert constraint["supported"] is True and constraint["source_exact"] == raw
    assert _proof(records)["complete"] is True


@pytest.mark.parametrize("raw", [
    "Cho kỳ kế toán 5 tháng đầu năm 2025",
    "Cho kỳ kế toán 06 tháng đầu năm 2025",
    "Cho kỳ kế toán sáu tháng đầu năm 2025",
    "Cho kỳ kế toán 6 tháng đầu năm 0000",
    "Cho kỳ kế toán ６ tháng đầu năm 2025",
    "Cho kỳ kế toán 6 tháng đầu năm ２０２５",
    "Cho kỳ kế toán 6\u0301 tháng đầu năm 2025",
    "Cho kỳ kế toán 6 tháng đầu năm 2025\u0301",
    "Cho kỳ kế toán 6 tháng đầu năm 2025 (*)",
    "Cho kỳ kế toán 6 tháng đầu năm 2025; cho kỳ 3 tháng",
    "Cho kỳ kế toán 6 tháng đầu năm 2025 không bao gồm quý I",
    "Cho kỳ kế toán 6\v tháng đầu năm 2025",
    "Cho kỳ kế toán 6 tháng đầu năm 20\u200b25",
])
def test_first_months_invalid_raw_assertion_stays_unsupported(raw):
    records, section, table = _fixture(narrative=raw)
    before = deepcopy(records)
    constraints = _owned_current_period_constraints(section, table)
    assert constraints and any(item["supported"] is False for item in constraints)
    assert _proof(records)["complete"] is False
    assert records == before


@pytest.mark.parametrize("raw", [
    "Thông tin lịch sử: Cho kỳ kế toán 6 tháng đầu năm 2024",
    "Ngân hàng XYZ Cho kỳ kế toán 6 tháng đầu năm 2025",
])
def test_first_months_does_not_extract_substring_authority(raw):
    _records, section, table = _fixture(narrative=raw)
    assert not any("source_first_calendar_months_evidence" in c for c in _owned_current_period_constraints(section, table))


@pytest.mark.parametrize("relative", [("Năm nay", "Năm trước"), ("Kỳ này", "Kỳ trước")])
def test_first_months_does_not_invent_comparative_window(relative):
    records, section, table = _fixture(relative=relative)
    lane = _multitable_lane_axis(section, table, compiled_specs=_adapter_compiled())
    assert _owned_relative_year_duration_evidence(section, table, lane) is None
    assert _proof(records)["complete"] is False


@pytest.mark.parametrize("mutation", ["NOTE", "UNKNOWN", "CASH_FLOW", "MULTITABLE", "FOREIGN_TABLE"])
def test_first_months_extension_never_grants_other_owner_authority(mutation):
    _records, section, table = _fixture()
    if mutation in {"NOTE", "UNKNOWN"}:
        section["content_kind"] = "FINANCIAL_NOTE" if mutation == "NOTE" else "UNKNOWN"
    elif mutation == "CASH_FLOW":
        section["statement_type"] = "CASH_FLOW"
    elif mutation == "MULTITABLE":
        section["tables"].append(deepcopy(table))
    else:
        table = {**table, "title_exact": "Another table"}
    assert not any(c.get("supported") and "source_first_calendar_months_evidence" in c
                   for c in _owned_current_period_constraints(section, table))


def test_first_months_endpoint_alone_does_not_authorize_quarter_only_range():
    records, section, table = _fixture(start_month=4)
    lane = _multitable_lane_axis(section, table, compiled_specs=_adapter_compiled())
    assert not _owned_current_period_constraints_match(section, table, lane)
    assert _proof(records)["complete"] is False


@pytest.mark.parametrize("raw", ["Cho kỳ kế toán 3 tháng đầu năm 2025", "Cho kỳ kế toán 6 tháng đầu năm 2024"])
def test_first_months_current_month_or_year_mismatch_vetoes_explicit_headers(raw):
    records, _section, _table = _fixture(narrative=raw)
    assert _proof(records)["complete"] is False


def test_first_months_resealed_inventory_cannot_replace_current_source():
    records, _section, _table = _fixture()
    compiled = _adapter_compiled()
    inventory = deepcopy(_document_statement_period_inventory(records, compiled_specs=compiled))
    inventory["sources"][0]["owned_current_period_constraints"][0]["printed_months"] = 3
    material = {k: v for k, v in inventory.items() if k != "receipt_id"}
    inventory["receipt_id"] = "gjitfav1:document-statement-periods:" + canonical_json_sha256_v1(material)
    with pytest.raises(GeminiJsonIncomeTaxFamilyV1Error, match="inventory source replay drifted"):
        _proof(records, inventory)
