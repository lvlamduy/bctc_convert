"""Proposed finite period regressions; synthetic evidence is not corpus approval."""

from __future__ import annotations

import unicodedata
from copy import deepcopy
from hashlib import sha256

import pytest
from test_gemini_json_income_tax_family_v1 import _adapter_compiled
from test_gemini_json_income_tax_signed_display_v1 import (
    _contextual_period_locator,
    _contextual_period_records,
)

from bctc_ai.evaluation import gemini_json_income_tax_family_v1 as family

FRAME = "Lũy kế từ đầu năm nay đến cuối quý này"
CAPTION = "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG riêng\nCho Quý 1 kết thúc ngày 31 tháng 03 năm 2025"
PERIODS = [["SOURCE_YTD_QUARTER", 2025, 1], ["SOURCE_YTD_QUARTER", 2024, 1]]


def _records(*, carrier="both", include_cf=True, scope="riêng"):
    records = _contextual_period_records(quarter="I", scope=scope, include_cash_flow=include_cf)
    # The existing fixture prints 2026/2025. Change only its printed period
    # headers to 2025/2024; never infer a year from the path or a source value.
    for record in records:
        for section in record["page_json"]["sections"]:
            for table in section["tables"]:
                for column in table["columns"]:
                    column["header_path_exact"] = [
                        part.replace("2025", "2024").replace("2026", "2025")
                        for part in column["header_path_exact"]
                    ]
    section = records[1]["page_json"]["sections"][0]
    table = section["tables"][0]
    caption = CAPTION.replace(" riêng", " " + scope if scope else "")
    section["title_exact"] = caption if carrier in {"SECTION_TITLE", "both"} else "Báo cáo kết quả hoạt động " + scope
    table["title_exact"] = caption if carrier in {"TABLE_TITLE", "both"} else None
    for index, column in enumerate(table["columns"]):
        column["header_path_exact"] = [
            "Quý 1" if index < 2 else FRAME,
            "Năm nay" if index % 2 == 0 else "Năm trước",
        ]
    return records


def _primary(records):
    section = records[1]["page_json"]["sections"][0]
    return section, section["tables"][0]


def _proof(records):
    compiled = _adapter_compiled()
    inventory = family._document_statement_period_inventory(records, compiled_specs=compiled)
    return family._source_period_correspondence_receipt(
        left_locator=_contextual_period_locator(records[1]),
        right_locator=_contextual_period_locator(records[1]),
        left_money_column_ordinals=[3, 4], right_money_column_ordinals=[3, 4],
        page_records=records, compiled_specs=compiled, document_period_inventory=inventory,
    )


@pytest.mark.parametrize("quarter,month,day", [("1", 3, 31), ("II", 6, 30), ("III", 9, 30), ("IV", 12, 31)])
@pytest.mark.parametrize("scope", ["", " riêng", " hợp nhất"])
def test_whole_inc_quarter_ended_caption_is_only_current_endpoint(quarter, month, day, scope):
    raw = f"Báo cáo kết quả hoạt động{scope}\nCho Quý {quarter} kết thúc ngày {day} tháng {month:02d} năm 2025"
    section = {"content_kind": "PRIMARY_STATEMENT", "statement_type": "INCOME_STATEMENT"}
    before = deepcopy(section)
    receipt = family._owned_flow_report_quarter_constraint(section, source_kind="SECTION_TITLE", source_exact=raw)
    assert section == before
    assert receipt is not None and receipt["supported"] is True
    assert receipt["printed_reporting_quarter"] == month // 3 and receipt["printed_year"] == 2025
    assert not {"printed_end_date", "printed_months", "printed_start_date"} & receipt.keys()
    evidence = receipt["source_report_quarter_evidence"]
    assert evidence["printed_reporting_end_date"] == f"2025-{month:02d}-{day:02d}"
    assert evidence["source_exact"] == raw
    assert evidence["source_sha256"] == sha256(raw.encode("utf-8")).hexdigest()
    for key in ("comparative_year_permission_granted", "start_dates_inferred", "source_period_keys_modified",
                "unit_permission_granted", "entity_permission_granted", "report_scope_permission_granted"):
        assert evidence[key] is False


@pytest.mark.parametrize("presentation", ["upper", "nfd", "serialized_newline"])
def test_new_endpoint_layout_keeps_raw_proof(presentation):
    raw = CAPTION.upper() if presentation == "upper" else unicodedata.normalize("NFD", CAPTION) if presentation == "nfd" else CAPTION.replace("\n", "\\n")
    section = {"content_kind": "PRIMARY_STATEMENT", "statement_type": "INCOME_STATEMENT"}
    result = family._owned_flow_report_quarter_constraint(section, source_kind="TABLE_TITLE", source_exact=raw)
    assert result is not None and result["supported"] is True
    assert result["source_exact"] == raw
    assert result["source_report_quarter_evidence"]["printed_reporting_end_date"] == "2025-03-31"


@pytest.mark.parametrize("raw", [
    CAPTION.replace("31 tháng 03", "30 tháng 06"),
    CAPTION.replace("Quý 1", "Quý II"),
    CAPTION.replace("31 tháng 03", "31 tháng 02"),
    CAPTION.replace("2025", "0000"),
    CAPTION.replace("2025", "２０２５"),
    CAPTION.replace("2025", "202\u03015"),
    CAPTION.replace("Quý 1", "Quý I\u0301"),
    CAPTION.replace("31 tháng", "31\u0301 tháng"),
    CAPTION + " năm 2024",
    CAPTION + " Cho quý II năm 2025",
    CAPTION + " (chưa kiểm tra)",
    CAPTION + "*",
    CAPTION + " ghi chú",
    "Năm 2024\n" + CAPTION,
    CAPTION.replace("Cho Quý", "Không phải Cho Quý"),
    CAPTION.replace("kết thúc", "kết\u200b thúc"),
])
def test_ended_caption_cannot_erase_invalid_calendar_tokens_or_other_assertions(raw):
    section = {"content_kind": "PRIMARY_STATEMENT", "statement_type": "INCOME_STATEMENT"}
    result = family._owned_flow_report_quarter_constraint(section, source_kind="SECTION_TITLE", source_exact=raw)
    assert result is not None and result["supported"] is False


@pytest.mark.parametrize("kind,content,statement", [
    ("OWNED_NARRATIVE", "PRIMARY_STATEMENT", "INCOME_STATEMENT"),
    ("SECTION_TITLE", "FINANCIAL_NOTE", "NOT_APPLICABLE"),
    ("SECTION_TITLE", "PRIMARY_STATEMENT", "BALANCE_SHEET"),
])
def test_ended_caption_does_not_widen_source_ownership(kind, content, statement):
    section = {"content_kind": content, "statement_type": statement}
    assert family._owned_flow_report_quarter_constraint(section, source_kind=kind, source_exact=CAPTION) is None


def test_ended_scaffold_does_not_expand_cf_or_legal_prologue_grammar():
    section = {"content_kind": "PRIMARY_STATEMENT", "statement_type": "CASH_FLOW"}
    raw = CAPTION.replace("KẾT QUẢ HOẠT ĐỘNG", "LƯU CHUYỂN TIỀN TỆ")
    assert family._owned_flow_report_quarter_constraint(section, source_kind="SECTION_TITLE", source_exact=raw)["supported"] is False
    section["statement_type"] = "INCOME_STATEMENT"
    raw = "Ngân hàng TMCP Mẫu\n123 Đường An Bình\nThành phố Hà Nội\n" + CAPTION
    assert family._owned_flow_report_quarter_constraint(section, source_kind="SECTION_TITLE", source_exact=raw)["supported"] is False


@pytest.mark.parametrize("carrier", ["SECTION_TITLE", "TABLE_TITLE", "both"])
def test_new_quarter_caption_and_shared_ytd_frame_need_real_cf_absolute_pair(carrier):
    records = _records(carrier=carrier)
    before = deepcopy(records)
    section, table = _primary(records)
    lane = family._multitable_lane_axis(section, table, compiled_specs=_adapter_compiled())
    assert lane["complete"] is True and lane["money_column_ordinals"] == [3, 4]
    assert lane["excluded_parallel_duration_money_column_ordinals"] == [1, 2]
    siblings = family._printed_ytd_sibling_period_evidence(section, table, lane)
    assert siblings is not None and siblings["relative_year_tokens"] == ["nay", "truoc"]
    assert siblings["intrinsic_absolute_periods"] is None and siblings["printed_absolute_year_tokens"] is None
    assert siblings["cumulative_columns_exact"] == table["columns"][2:]
    proof = _proof(records)
    assert proof["complete"] is True, proof["reasons"]
    assert proof["status"] == "PASS_AUTHENTICATED_SOURCE_YTD_CORRESPONDENCE"
    for resolution in proof["period_resolution_evidence"]:
        assert resolution["resolved_source_duration_semantics"] == PERIODS
        assert resolution["cash_flow_used_as_period_authority"] is True
        assert resolution["cash_flow_anchor_sources"]
    assert proof["start_dates_inferred"] is False and proof["source_period_keys_modified"] is False
    assert records == before


@pytest.mark.parametrize("seam", ["caption_only", "header_only", "both_without_cf"])
def test_neither_lexical_seam_alone_supplies_missing_period_authority(seam):
    records = _records(include_cf=seam != "both_without_cf")
    section, table = _primary(records)
    if seam == "caption_only":
        for column in table["columns"][2:]:
            column["header_path_exact"][0] = "Lũy kế từ đầu năm nay"
    elif seam == "header_only":
        section["title_exact"] += " ghi chú"
        table["title_exact"] += " ghi chú"
    before = deepcopy(records)
    lane = family._multitable_lane_axis(section, table, compiled_specs=_adapter_compiled())
    siblings = family._printed_ytd_sibling_period_evidence(section, table, lane)
    constraints = family._owned_current_period_constraints(section, table)
    if seam == "caption_only":
        assert siblings is None and all(item["supported"] for item in constraints)
    else:
        assert siblings is not None and siblings["intrinsic_absolute_periods"] is None
        assert all(item["supported"] for item in constraints) is (seam == "both_without_cf")
    proof = _proof(records)
    assert proof["complete"] is False and proof["status"] == "ALGORITHM_HOLD"
    assert records == before


@pytest.mark.parametrize("mutation", ["one_frame", "prior_frame", "reversed_years", "bare_year_words", "wrong_quarter", "extra_suffix"])
def test_common_current_reporting_frame_cannot_replace_matching_full_four_headers(mutation):
    records = _records()
    section, table = _primary(records)
    if mutation == "one_frame":
        table["columns"][3]["header_path_exact"][0] = "Lũy kế từ đầu năm"
    elif mutation == "prior_frame":
        for column in table["columns"][2:]:
            column["header_path_exact"][0] = FRAME.replace("năm nay", "năm trước")
    elif mutation == "reversed_years":
        for column in table["columns"][2:]:
            column["header_path_exact"][1] = "Năm trước" if column["header_path_exact"][1] == "Năm nay" else "Năm nay"
    elif mutation == "bare_year_words":
        for column in table["columns"]:
            column["header_path_exact"][1] = column["header_path_exact"][1].replace("Năm ", "")
    elif mutation == "wrong_quarter":
        table["columns"][1]["header_path_exact"][0] = "Quý II"
    else:
        table["columns"][3]["header_path_exact"].append("chưa rõ")
    before = deepcopy(records)
    lane = family._multitable_lane_axis(section, table, compiled_specs=_adapter_compiled())
    assert family._printed_ytd_sibling_period_evidence(section, table, lane) is None
    assert _proof(records)["complete"] is False
    assert records == before


@pytest.mark.parametrize("mutation", ["unknown_scope", "undated_cf", "wrong_cf_end", "nonadjacent_cf_prior", "contrary_cf_continuation"])
def test_relative_ytd_comparison_cannot_guess_or_ignore_cf_window(mutation):
    records = _records(scope="" if mutation == "unknown_scope" else "riêng")
    cf = records[2]["page_json"]["sections"][0]
    if mutation == "undated_cf":
        for column, label in zip(cf["tables"][0]["columns"], ("Năm nay", "Năm trước"), strict=True):
            column["header_path_exact"] = [label]
    elif mutation == "wrong_cf_end":
        for column in cf["tables"][0]["columns"]:
            column["header_path_exact"] = [part.replace("3 tháng", "6 tháng").replace("31/3/", "30/6/") for part in column["header_path_exact"]]
    elif mutation == "nonadjacent_cf_prior":
        cf["tables"][0]["columns"][1]["header_path_exact"] = [part.replace("2024", "2023") for part in cf["tables"][0]["columns"][1]["header_path_exact"]]
    elif mutation == "contrary_cf_continuation":
        continuation = deepcopy(records[2])
        continuation.update(page_json_version_id="gfpstorev1:json:" + "f" * 64, physical_page=4, selected_page_ordinal=4)
        table = continuation["page_json"]["sections"][0]["tables"][0]
        for column in table["columns"]:
            column["header_path_exact"] = [part.replace("3 tháng", "6 tháng").replace("31/3/", "30/6/") for part in column["header_path_exact"]]
        records.append(continuation)
    before = deepcopy(records)
    proof = _proof(records)
    assert proof["complete"] is False and proof["status"] == "ALGORITHM_HOLD"
    assert records == before


def test_existing_cho_quarter_fields_and_sibling_receipt_shape_remain_unchanged():
    records = _records()
    section, table = _primary(records)
    raw = "Báo cáo kết quả hoạt động riêng\nCho quý I năm 2025"
    section["title_exact"], table["title_exact"] = raw, None
    for column in table["columns"][2:]:
        column["header_path_exact"][0] = "Lũy kế từ đầu năm đến cuối quý này"
    before = deepcopy(records)
    assert family._owned_flow_report_quarter_constraint(section, source_kind="SECTION_TITLE", source_exact=raw) is None
    assert family._owned_current_period_constraints(section, table) == [
        {"source_kind": "SECTION_TITLE", "source_exact": raw, "supported": True,
         "printed_reporting_quarter": 1, "printed_year": 2025},
    ]
    lane = family._multitable_lane_axis(section, table, compiled_specs=_adapter_compiled())
    sibling = family._printed_ytd_sibling_period_evidence(section, table, lane)
    assert sibling is not None
    assert set(sibling) == {"quarter", "relative_year_tokens", "printed_absolute_year_tokens",
                            "intrinsic_absolute_periods", "money_column_ordinals", "quarter_columns_exact",
                            "cumulative_columns_exact", "original_table_json_sha256", "rule", "receipt_id"}
    assert sibling["relative_year_tokens"] == ["nay", "truoc"] and sibling["intrinsic_absolute_periods"] is None
    assert _proof(records)["complete"] is True
    assert records == before
