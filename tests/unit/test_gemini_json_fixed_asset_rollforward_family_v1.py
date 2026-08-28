from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from bctc_ai.evaluation import gemini_json_fixed_asset_rollforward_family_v1 as fixed_asset_v1
from bctc_ai.evaluation.gemini_json_fixed_asset_rollforward_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    GeminiJsonFixedAssetRollforwardFamilyV1Error,
    build_gemini_json_fixed_asset_rollforward_region_query_receipt_v1,
    coalesce_gemini_json_fixed_asset_rollforward_document_v1,
    compile_gemini_json_fixed_asset_rollforward_family_specs_v1,
    evaluate_gemini_json_fixed_asset_rollforward_family_cluster_v1,
    validate_gemini_json_fixed_asset_rollforward_family_candidate_replay_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]


def _compiled():
    return compile_gemini_json_fixed_asset_rollforward_family_specs_v1(
        *[
            json.loads((ROOT / path).read_bytes())
            for path in (
                "config/families/tm-tangible-fixed-assets-topology-v1.json",
                "config/families/tm-tangible-fixed-assets-evaluation-v1.json",
                "config/families/tm-tangible-fixed-assets-schema-binding-v1.json",
            )
        ]
    )


def _compiled_leased():
    return compile_gemini_json_fixed_asset_rollforward_family_specs_v1(
        *[
            json.loads((ROOT / path).read_bytes())
            for path in (
                "config/families/tm-leased-fixed-assets-topology-v1.json",
                "config/families/tm-leased-fixed-assets-evaluation-v1.json",
                "config/families/tm-leased-fixed-assets-schema-binding-v1.json",
            )
        ]
    )


def _compiled_intangible():
    return compile_gemini_json_fixed_asset_rollforward_family_specs_v1(
        *[
            json.loads((ROOT / path).read_bytes())
            for path in (
                "config/families/tm-intangible-fixed-assets-topology-v1.json",
                "config/families/tm-intangible-fixed-assets-evaluation-v1.json",
                "config/families/tm-intangible-fixed-assets-schema-binding-v1.json",
            )
        ]
    )


def _compiled_investment_property():
    return compile_gemini_json_fixed_asset_rollforward_family_specs_v1(
        *[
            json.loads((ROOT / path).read_bytes())
            for path in (
                "config/families/tm-investment-property-topology-v1.json",
                "config/families/tm-investment-property-evaluation-v1.json",
                "config/families/tm-investment-property-schema-binding-v1.json",
            )
        ]
    )


def _row(label, branch, values, *, row_kind="ITEM", path=None):
    return {
        "hierarchy_path_exact": path or [branch, label],
        "label_exact": label,
        "row_kind": row_kind,
        "values_exact": values,
    }


def _table(*, current_year=2025, unit="Triệu VND", shifted=False, subtotal=False):
    columns = [
        {"header_path_exact": ["Nhà cửa, vật kiến trúc", "Triệu VND"], "value_kind": "MONEY"},
        {"header_path_exact": ["Máy móc, thiết bị", "Triệu VND"], "value_kind": "MONEY"},
    ]
    if shifted:
        columns.append(
            {"header_path_exact": ["Thiết bị văn phòng", "Triệu VND"], "value_kind": "MONEY"}
        )
    columns.append({"header_path_exact": ["Tổng cộng", "Triệu VND"], "value_kind": "MONEY"})

    def values(left, right, total, *, shift=False):
        if shifted:
            return [
                str(left),
                str(right),
                str(total) if shift else "-",
                None if shift else str(total),
            ]
        return [str(left), str(right), str(total)]

    opening = f"Tại ngày 1 tháng 1 năm {current_year}"
    ending = f"Tại ngày 31 tháng 12 năm {current_year}"
    rows = [
        _row(
            "Nguyên giá", "Nguyên giá", [None] * len(columns), row_kind="GROUP", path=["Nguyên giá"]
        ),
        _row(opening, "Nguyên giá", values(100, 200, 300)),
    ]
    if subtotal:
        rows.extend(
            [
                _row("Tăng trong kỳ", "Nguyên giá", values(10, 20, 30), row_kind="SUBTOTAL"),
                _row(
                    "Mua trong kỳ",
                    "Nguyên giá",
                    values(4, 6, 10),
                    path=["Nguyên giá", "Tăng trong kỳ\n- Mua trong kỳ"],
                ),
                _row(
                    "Tăng khác",
                    "Nguyên giá",
                    values(6, 14, 20),
                    path=["Nguyên giá", "Tăng trong kỳ\n- Tăng khác"],
                ),
            ]
        )
    else:
        rows.append(_row("Mua trong kỳ", "Nguyên giá", values(10, 20, 30, shift=shifted)))
    rows.extend(
        [
            _row(ending, "Nguyên giá", values(110, 220, 330), row_kind="TOTAL"),
            _row(
                "Hao mòn lũy kế",
                "Hao mòn lũy kế",
                [None] * len(columns),
                row_kind="GROUP",
                path=["Hao mòn lũy kế"],
            ),
            _row(opening, "Hao mòn lũy kế", values(20, 40, 60)),
        ]
    )
    if subtotal:
        rows.extend(
            [
                _row(
                    "Tăng trong kỳ",
                    "Hao mòn lũy kế",
                    values(2, 4, 6),
                    row_kind="SUBTOTAL",
                ),
                _row(
                    "Khấu hao trong kỳ",
                    "Hao mòn lũy kế",
                    values(1, 2, 3),
                    path=["Hao mòn lũy kế", "Tăng trong kỳ", "Khấu hao trong kỳ"],
                ),
                _row(
                    "Tăng khác",
                    "Hao mòn lũy kế",
                    values(1, 2, 3),
                    path=["Hao mòn lũy kế", "Tăng trong kỳ", "Tăng khác"],
                ),
            ]
        )
    else:
        rows.append(_row("Khấu hao trong kỳ", "Hao mòn lũy kế", values(2, 4, 6)))
    rows.extend(
        [
            _row(ending, "Hao mòn lũy kế", values(22, 44, 66), row_kind="TOTAL"),
            _row(
                "Giá trị còn lại",
                "Giá trị còn lại",
                [None] * len(columns),
                row_kind="GROUP",
                path=["Giá trị còn lại"],
            ),
            _row(opening, "Giá trị còn lại", values(80, 160, 240)),
            _row(ending, "Giá trị còn lại", values(88, 176, 264)),
        ]
    )
    return {
        "columns": columns,
        "continuation": "NONE",
        "rows": rows,
        "title_exact": f"Tài sản cố định hữu hình năm {current_year}",
        "unit_exact": unit,
    }


def _page(table=None):
    return {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [_table() if table is None else table],
                "title_exact": "Tài sản cố định hữu hình",
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _investment_property_table(*, current_year=2025, unit="Triệu VND"):
    table = _table(current_year=current_year, unit=unit)
    table["columns"][1]["header_path_exact"] = [
        "Quyền sử dụng đất có thời hạn",
        "Triệu VND",
    ]
    table["title_exact"] = f"Bất động sản đầu tư cho thuê năm {current_year}"
    return table


def _investment_property_page(*, tables, narratives=None):
    page = _page()
    section = page["sections"][0]
    section["title_exact"] = "Bất động sản đầu tư"
    section["narratives_exact"] = [] if narratives is None else narratives
    section["tables"] = tables
    return page


def _investment_cost_fragment(*, current_year=2025, unit="Triệu VND"):
    table = _investment_property_table(current_year=current_year, unit=unit)
    table["rows"] = [row for row in table["rows"] if row["hierarchy_path_exact"][0] == "Nguyên giá"]
    for row in table["rows"]:
        if row["row_kind"] == "GROUP":
            continue
        if row["label_exact"].startswith("Tại ngày 1 tháng 1"):
            row["values_exact"] = ["4", "6", "10"]
        elif row["label_exact"] == "Mua trong kỳ":
            row["values_exact"] = ["2", "3", "5"]
        else:
            row["values_exact"] = ["6", "9", "15"]
    table["title_exact"] = f"Bất động sản đầu tư nắm giữ chờ tăng giá năm {current_year}"
    return table


def _investment_summary_table(*, current=279, comparative=250, unit="Triệu VND"):
    return {
        "columns": [
            {"header_path_exact": ["31/12/2025"], "value_kind": "MONEY"},
            {"header_path_exact": ["31/12/2024"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            _row(
                "Bất động sản đầu tư cho thuê",
                "Bất động sản đầu tư",
                [str(current - 15), str(comparative - 10)],
                path=["Bất động sản đầu tư cho thuê"],
            ),
            _row(
                "Bất động sản đầu tư nắm giữ chờ tăng giá",
                "Bất động sản đầu tư",
                ["15", "10"],
                path=["Bất động sản đầu tư nắm giữ chờ tăng giá"],
            ),
            _row(
                "Tổng cộng",
                "Bất động sản đầu tư",
                [str(current), str(comparative)],
                row_kind="TOTAL",
                path=["Tổng cộng"],
            ),
        ],
        "title_exact": "Giá trị còn lại của bất động sản đầu tư",
        "unit_exact": unit,
    }


def _investment_statement_page(*, current=330, comparative=300, unit="Triệu VND"):
    page = _typed_balance_sheet_page()
    table = page["sections"][0]["tables"][0]
    table["unit_exact"] = unit
    table["rows"] = [
        _row(
            "Bất động sản đầu tư",
            "Bất động sản đầu tư",
            [str(current), str(comparative)],
            row_kind="TOTAL",
            path=["Bất động sản đầu tư"],
        )
    ]
    return page


def _investment_candidate(page_records):
    compiled = _compiled_investment_property()
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=page_records, compiled_specs=compiled
    )
    assert cluster["status"] == READY
    receipt = build_gemini_json_fixed_asset_rollforward_region_query_receipt_v1(
        cluster["component_regions"], control_regions=cluster["control_regions"]
    )
    page_json_by_version = {
        item["page_json_version_id"]: item["page_json"] for item in page_records
    }
    candidate = evaluate_gemini_json_fixed_asset_rollforward_family_cluster_v1(
        regions=cluster["component_regions"],
        control_regions=cluster["control_regions"],
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    return compiled, cluster, receipt, page_json_by_version, candidate


def _leased_table():
    table = _table()
    table["rows"] = [
        row
        for row in table["rows"]
        if row.get("hierarchy_path_exact", [None])[0] != "Giá trị còn lại"
    ]
    for row in table["rows"]:
        if row["label_exact"] == "Mua trong kỳ":
            row["label_exact"] = "Thuê tài chính trong kỳ"
            row["hierarchy_path_exact"][-1] = "Thuê tài chính trong kỳ"
    table["title_exact"] = "Tài sản cố định thuê tài chính năm 2025"
    return table


def _leased_page(*, owner="Tài sản cố định thuê tài chính"):
    page = _page(_leased_table())
    page["sections"][0]["title_exact"] = owner
    return page


def _intangible_table(*, current_year=2025, subtotal=False):
    table = _table(current_year=current_year, subtotal=subtotal)
    table["columns"][0]["header_path_exact"] = ["Phần mềm máy tính", "Triệu VND"]
    table["columns"][1]["header_path_exact"] = ["Quyền sử dụng đất", "Triệu VND"]
    table["title_exact"] = f"Tài sản cố định vô hình năm {current_year}"
    return table


def _supplemental_table(*, current="1.234", comparative="1.000", unit="Triệu VND"):
    return {
        "columns": [
            {"header_path_exact": ["31/12/2025"], "value_kind": "MONEY"},
            {"header_path_exact": ["31/12/2024"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            {
                "hierarchy_path_exact": [
                    "Nguyên giá TSCĐ vô hình đã khấu hao hết nhưng vẫn còn sử dụng"
                ],
                "label_exact": "Nguyên giá TSCĐ vô hình đã khấu hao hết nhưng vẫn còn sử dụng",
                "row_kind": "ITEM",
                "values_exact": [current, comparative],
            }
        ],
        "title_exact": "TSCĐ vô hình đã khấu hao hết nhưng vẫn còn sử dụng",
        "unit_exact": unit,
    }


def _intangible_page(*, tables=None, narratives=None):
    page = _page(_intangible_table())
    section = page["sections"][0]
    section["title_exact"] = "Tài sản cố định vô hình"
    section["tables"] = [_intangible_table()] if tables is None else tables
    section["narratives_exact"] = [] if narratives is None else narratives
    return page


def _intangible_candidate(page):
    compiled = _compiled_intangible()
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    receipt = build_gemini_json_fixed_asset_rollforward_region_query_receipt_v1(
        cluster["component_regions"], control_regions=cluster["control_regions"]
    )
    candidate = evaluate_gemini_json_fixed_asset_rollforward_family_cluster_v1(
        regions=cluster["component_regions"],
        control_regions=cluster["control_regions"],
        page_json_by_version={cluster["component_regions"][0]["page_json_version_id"]: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    return compiled, cluster, receipt, candidate


def _page_record(page_json, *, selected_page_ordinal=1, physical_page=10):
    return {
        "document_id": "gfpstorev1:document:" + "1" * 64,
        "document_ordinal": 1,
        "page_json": page_json,
        "page_json_version_id": "gfpstorev1:json:" + str(selected_page_ordinal) * 64,
        "physical_page": physical_page,
        "selected_page_ordinal": selected_page_ordinal,
        "source_logical_name": "fixture.pdf",
        "source_sha256": "2" * 64,
    }


def _undated_table(*, current_year=2025):
    table = _table(current_year=current_year)
    replacements = {
        f"Tại ngày 1 tháng 1 năm {current_year}": "Số đầu năm",
        f"Tại ngày 31 tháng 12 năm {current_year}": "Số cuối năm",
    }
    for row in table["rows"]:
        old = row["label_exact"]
        if old in replacements:
            row["label_exact"] = replacements[old]
            row["hierarchy_path_exact"][-1] = replacements[old]
    table["title_exact"] = "Tài sản cố định hữu hình"
    return table


def _typed_income_statement_page(period_end="31 tháng 12 năm 2025"):
    return {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            {
                "content_kind": "PRIMARY_STATEMENT",
                "narratives_exact": [f"Cho năm kết thúc ngày {period_end}"],
                "statement_type": "INCOME_STATEMENT",
                "tables": [],
                "title_exact": "Báo cáo kết quả hoạt động",
            }
        ],
        "status": "PRIMARY_FINANCIAL_STATEMENT",
    }


def _typed_balance_sheet_page(current="31/12/2025", comparative="31/12/2024"):
    return {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            {
                "content_kind": "PRIMARY_STATEMENT",
                "narratives_exact": [],
                "statement_type": "BALANCE_SHEET",
                "tables": [
                    {
                        "columns": [
                            {"header_path_exact": [current], "value_kind": "MONEY"},
                            {"header_path_exact": [comparative], "value_kind": "MONEY"},
                        ],
                        "continuation": "NONE",
                        "rows": [],
                        "title_exact": None,
                        "unit_exact": "Triệu VND",
                    }
                ],
                "title_exact": "Báo cáo tình hình tài chính",
            }
        ],
        "status": "PRIMARY_FINANCIAL_STATEMENT",
    }


def _candidate(table=None):
    compiled = _compiled()
    page = _page(table)
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    receipt = build_gemini_json_fixed_asset_rollforward_region_query_receipt_v1(
        cluster["component_regions"], control_regions=cluster["control_regions"]
    )
    candidate = evaluate_gemini_json_fixed_asset_rollforward_family_cluster_v1(
        regions=cluster["component_regions"],
        control_regions=cluster["control_regions"],
        page_json_by_version={cluster["component_regions"][0]["page_json_version_id"]: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    return compiled, page, cluster, receipt, candidate


def test_fixed_asset_minimal_current_table_closes_without_prompt_logic():
    _compiled_specs, _page_json, _cluster, _receipt, candidate = _candidate()
    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 8
    assert {item["role"] for item in candidate["mappings"]} == {
        "CARRY_ENDING",
        "CARRY_OPENING",
        "COST_ENDING",
        "COST_OPENING",
        "COST_PURCHASE",
        "DEP_CHARGE",
        "DEP_ENDING",
        "DEP_OPENING",
    }
    assert candidate["closure_receipt"]["width_seal"]["status"] == (
        "SEALED_EXACT_RAW_COLUMN_BINDING"
    )


def test_right_edge_shift_is_sealed_only_by_all_equations():
    _compiled_specs, _page_json, _cluster, _receipt, candidate = _candidate(_table(shifted=True))
    assert candidate["status"] == READY
    seal = candidate["closure_receipt"]["width_seal"]
    assert seal["status"] == "SEALED_UNIQUE_ALL_EQUATION_CLOSING_PROJECTION"
    assert len(seal["relocation_receipts"]) == 1
    assert seal["relocation_receipts"][0]["action_kind"] == (
        "RELOCATE_RIGHTMOST_EARLIER_VALUE_TO_TOTAL"
    )


def test_flattened_and_explicit_subtotal_children_share_generic_collapse():
    _compiled_specs, _page_json, _cluster, _receipt, candidate = _candidate(_table(subtotal=True))
    assert candidate["status"] == READY
    collapse = candidate["closure_receipt"]["subtotal_collapse"]
    assert collapse["status"] == "COLLAPSED_EXACT_VISIBLE_SUBTOTAL_BLOCKS"
    assert len(collapse["block_receipts"]) == 2
    assert {item["parent_projection_mode"] for item in collapse["block_receipts"]} == {
        "ALREADY_CORRECT_DIRECT_PARENT",
        "CONSISTENT_FLATTENED_EXTERNAL_PARENT",
    }


def test_unclassified_numeric_source_row_fails_closed():
    table = _table()
    table["rows"].insert(2, _row("Dòng lạ", "Nguyên giá", ["1", "2", "3"]))
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(_page(table))], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert "UNCLASSIFIED_NUMERIC_ROW_INSIDE_FIXED_ASSET_BRANCH" in cluster["reasons"]


def test_numeric_row_cannot_hide_behind_unknown_hierarchy():
    table = _table()
    table["rows"].insert(
        2,
        _row("Dòng lạ", "Ngoài graph", ["1", "2", "3"], path=["Ngoài graph"]),
    )
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(_page(table))], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert "UNCLASSIFIED_NUMERIC_ROW_INSIDE_FIXED_ASSET_BRANCH" in cluster["reasons"]


def test_branch_source_order_is_not_inferred_from_arithmetic():
    table = _table()
    table["rows"][1], table["rows"][3] = table["rows"][3], table["rows"][1]
    compiled = _compiled()
    page = _page(table)
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    receipt = build_gemini_json_fixed_asset_rollforward_region_query_receipt_v1(
        cluster["component_regions"], control_regions=[]
    )
    candidate = evaluate_gemini_json_fixed_asset_rollforward_family_cluster_v1(
        regions=cluster["component_regions"],
        control_regions=[],
        page_json_by_version={cluster["component_regions"][0]["page_json_version_id"]: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    assert candidate["status"] == UNRESOLVED
    assert (
        "BRANCH_SOURCE_ORDER_OPENING_MOVEMENTS_ENDING_INVALID:COST_BRANCH" in candidate["reasons"]
    )


def test_conflicting_unit_magnitudes_fail_before_mapping():
    table = _table(unit="Triệu VND và Nghìn VND")
    _compiled_specs, _page_json, _cluster, _receipt, candidate = _candidate(table)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "MULTIPLE_CONFLICTING_DECLARED_MONEY_UNITS_ON_ONE_SURFACE" in candidate["reasons"]


def test_conflicting_source_visible_period_dates_fail_closed():
    table = _table()
    table["title_exact"] = "Năm tài chính kết thúc ngày 30 tháng 6 năm 2025"
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(_page(table))], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert "FIXED_ASSET_TABLE_PERIOD_EVIDENCE_CONFLICT" in cluster["reasons"]


def test_latest_explicit_period_selects_current_and_retains_control():
    current = _page_record(_page(_table(current_year=2026)), physical_page=10)
    comparative = _page_record(
        _page(_table(current_year=2025)), selected_page_ordinal=2, physical_page=11
    )
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[current, comparative], compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    assert cluster["component_regions"][0]["period_end_date"] == "2026-12-31"
    assert cluster["control_regions"][0]["period_end_date"] == "2025-12-31"


def test_duplicate_current_period_table_is_ambiguous():
    first = _page_record(_page(_table()), physical_page=10)
    second = _page_record(_page(_table()), selected_page_ordinal=2, physical_page=11)
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[first, second], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert "CURRENT_FIXED_ASSET_TABLE_IS_NOT_UNIQUE" in cluster["reasons"]


def test_incomplete_second_family_table_is_not_silently_ignored():
    incomplete = _table()
    incomplete["rows"] = incomplete["rows"][:4]
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[
            _page_record(_page(_table()), physical_page=10),
            _page_record(_page(incomplete), selected_page_ordinal=2, physical_page=11),
        ],
        compiled_specs=_compiled(),
    )
    assert cluster["status"] == UNRESOLVED
    assert "FAMILY_SIGNAL_TABLE_IS_NOT_A_COMPLETE_FIXED_ASSET_PRESENTATION" in cluster["reasons"]


def test_undated_table_binds_typed_document_reporting_date_without_filename_logic():
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[
            _page_record(_typed_income_statement_page(), physical_page=1),
            _page_record(_page(_undated_table()), selected_page_ordinal=2, physical_page=10),
        ],
        compiled_specs=_compiled(),
    )
    assert cluster["status"] == READY
    assert cluster["component_regions"][0]["period_end_date"] == "2025-12-31"
    assert cluster["component_regions"][0]["period_selection_kind"] == (
        "UNIQUE_TYPED_DOCUMENT_REPORTING_DATE"
    )


def test_undated_table_without_typed_document_context_fails_closed():
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(_page(_undated_table()))],
        compiled_specs=_compiled(),
    )
    assert cluster["status"] == UNRESOLVED
    assert "CURRENT_FIXED_ASSET_PERIOD_END_DATE_NOT_AUTHENTICATED" in cluster["reasons"]


def test_undated_control_binds_comparative_date_only_with_endpoint_continuity():
    control = _undated_table(current_year=2024)
    for row in control["rows"]:
        if row["label_exact"] != "Số cuối năm":
            continue
        branch = row["hierarchy_path_exact"][0]
        row["values_exact"] = {
            "Nguyên giá": ["100", "200", "300"],
            "Hao mòn lũy kế": ["20", "40", "60"],
            "Giá trị còn lại": ["80", "160", "240"],
        }[branch]
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[
            _page_record(_typed_balance_sheet_page(), physical_page=1),
            _page_record(_page(_table()), selected_page_ordinal=2, physical_page=10),
            _page_record(
                _page(control),
                selected_page_ordinal=3,
                physical_page=11,
            ),
        ],
        compiled_specs=_compiled(),
    )
    assert cluster["status"] == READY
    assert cluster["control_regions"][0]["period_end_date"] == "2024-12-31"
    assert cluster["control_regions"][0]["period_selection_kind"] == (
        "TYPED_DOCUMENT_COMPARATIVE_DATE_WITH_ENDPOINT_CONTINUITY"
    )


def test_comparative_date_context_cannot_replace_failed_endpoint_continuity():
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[
            _page_record(_typed_balance_sheet_page(), physical_page=1),
            _page_record(_page(_table()), selected_page_ordinal=2, physical_page=10),
            _page_record(
                _page(_undated_table(current_year=2024)),
                selected_page_ordinal=3,
                physical_page=11,
            ),
        ],
        compiled_specs=_compiled(),
    )
    assert cluster["status"] == UNRESOLVED
    assert (
        "MULTIPLE_FAMILY_TABLES_REQUIRE_UNIQUE_PERIOD_OR_ENDPOINT_CONTINUITY" in cluster["reasons"]
    )


def test_hard_negative_fixed_asset_family_is_not_captured():
    table = _table()
    table["title_exact"] = "Tài sản cố định vô hình"
    table["columns"][0]["header_path_exact"] = ["Phần mềm", "Triệu VND"]
    table["columns"][1]["header_path_exact"] = ["Quyền sử dụng đất", "Triệu VND"]
    page = _page(table)
    page["sections"][0]["title_exact"] = "Tài sản cố định vô hình"
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == NOT_OBSERVED


def test_two_signed_branch_leased_variant_closes_without_carrying_control():
    compiled = _compiled_leased()
    assert "CONFIGURED_BRANCH" in compiled["claim_boundary"]
    assert "OPTIONAL_CARRYING_CONTROL" in compiled["claim_boundary"]
    assert "THREE_BRANCH" not in compiled["claim_boundary"]
    page = _leased_page()
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    receipt = build_gemini_json_fixed_asset_rollforward_region_query_receipt_v1(
        cluster["component_regions"], control_regions=[]
    )
    candidate = evaluate_gemini_json_fixed_asset_rollforward_family_cluster_v1(
        regions=cluster["component_regions"],
        control_regions=[],
        page_json_by_version={cluster["component_regions"][0]["page_json_version_id"]: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    assert candidate["status"] == READY
    assert candidate["claim_boundary"] == compiled["claim_boundary"]
    assert len(candidate["mappings"]) == 6
    assert {item["role"] for item in candidate["mappings"]} == {
        "COST_OPENING",
        "COST_LEASED_ADDITION",
        "COST_ENDING",
        "DEP_OPENING",
        "DEP_CHARGE",
        "DEP_ENDING",
    }
    assert not any(
        equation["equation_id"].startswith("carrying:")
        for equation in candidate["closure_receipt"]["table_receipt"]["equations"]
    )


def test_leased_variant_rejects_tangible_owner_context_as_not_observed():
    page = _leased_page(owner="Thuyết minh báo cáo tài chính")
    page["sections"][0]["narratives_exact"] = [
        "15. Tài sản cố định",
        "15.1 Tài sản cố định hữu hình",
        "Biến động của tài sản cố định hữu hình trong kỳ như sau:",
    ]
    page["sections"][0]["tables"][0]["title_exact"] = None
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(page)], compiled_specs=_compiled_leased()
    )
    assert cluster["status"] == NOT_OBSERVED
    assert cluster["reasons"] == []


def test_leased_variant_missing_owner_without_variant_context_stays_unresolved():
    page = _leased_page(owner="Thuyết minh báo cáo tài chính")
    page["sections"][0]["tables"][0]["title_exact"] = None
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(page)], compiled_specs=_compiled_leased()
    )
    assert cluster["status"] == UNRESOLVED
    assert "EXPLICIT_FIXED_ASSET_OWNER_NOT_VISIBLE" in cluster["reasons"]


def test_leased_owner_and_conflicting_tangible_variant_context_fail_closed():
    page = _leased_page()
    page["sections"][0]["narratives_exact"] = [
        "15.1 Tài sản cố định hữu hình",
        "15.2 Tài sản cố định thuê tài chính",
    ]
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(page)], compiled_specs=_compiled_leased()
    )
    assert cluster["status"] == UNRESOLVED
    assert "HARD_NEGATIVE_FIXED_ASSET_VARIANT_SURFACE_VISIBLE" in cluster["reasons"]


def test_finance_lease_policy_text_is_not_a_fixed_asset_owner():
    page = _leased_page(owner="Chính sách kế toán")
    page["sections"][0]["narratives_exact"] = [
        "Một khoản thuê được xem là thuê tài chính khi phần lớn rủi ro và lợi ích được chuyển giao."
    ]
    page["sections"][0]["tables"] = []
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(page)], compiled_specs=_compiled_leased()
    )
    assert cluster["status"] == NOT_OBSERVED


def test_intangible_supplemental_table_maps_only_current_period_value():
    page = _intangible_page(tables=[_intangible_table(), _supplemental_table()])
    _compiled_specs, _cluster, _receipt, candidate = _intangible_candidate(page)
    assert candidate["status"] == READY
    supplemental = [
        item for item in candidate["mappings"] if item["role"] == "FULLY_AMORTIZED_STILL_IN_USE"
    ]
    assert [(item["report_norm_id"], item["cell"]["coefficient"]) for item in supplemental] == [
        (6069, 1234)
    ]
    assert supplemental[0]["source_refs"][0]["source_locator"]["column_id"] == "c1"


def test_supplemental_row_inside_core_table_is_consumed_without_hiding_core_graph():
    table = _intangible_table()
    table["rows"].append(
        {
            "hierarchy_path_exact": [
                "Nguyên giá TSCĐ vô hình đã khấu hao hết nhưng vẫn còn sử dụng"
            ],
            "label_exact": "Nguyên giá TSCĐ vô hình đã khấu hao hết nhưng vẫn còn sử dụng",
            "row_kind": "ITEM",
            "values_exact": ["100", "200", "300"],
        }
    )
    page = _intangible_page(tables=[table])
    _compiled_specs, cluster, _receipt, candidate = _intangible_candidate(page)
    assert cluster["component_regions"][0]["table_id"] == "t1"
    assert candidate["status"] == READY
    mapping = next(
        item for item in candidate["mappings"] if item["role"] == "FULLY_AMORTIZED_STILL_IN_USE"
    )
    assert mapping["cell"]["coefficient"] == 300
    assert mapping["source_refs"][0]["source_locator"]["column_id"] == "c3"


def test_intangible_supplemental_narrative_is_projected_by_local_algorithm():
    narrative = (
        "Tại ngày 31/12/2025, nguyên giá của các tài sản cố định vô hình "
        "đã khấu hao hết nhưng vẫn còn sử dụng là 1.234 triệu VND."
    )
    page = _intangible_page(narratives=[narrative])
    _compiled_specs, _cluster, _receipt, candidate = _intangible_candidate(page)
    mapping = next(
        item for item in candidate["mappings"] if item["role"] == "FULLY_AMORTIZED_STILL_IN_USE"
    )
    assert candidate["status"] == READY
    assert mapping["cell"]["coefficient"] == 1234
    assert mapping["source_refs"][0]["source_kind"] == "DATED_NARRATIVE_CURRENT_VALUE"


def test_intangible_supplemental_narrative_conflicting_unit_fails_closed():
    narrative = (
        "Tại ngày 31/12/2025, nguyên giá của các tài sản cố định vô hình "
        "đã khấu hao hết nhưng vẫn còn sử dụng là 1.234 tỷ VND."
    )
    page = _intangible_page(narratives=[narrative])
    _compiled_specs, _cluster, _receipt, candidate = _intangible_candidate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert (
        "SUPPLEMENTAL_NARRATIVE_UNIT_NOT_UNIQUE_OR_CONFLICTING:"
        "FULLY_AMORTIZED_STILL_IN_USE" in candidate["reasons"]
    )


def test_intangible_conflicting_duplicate_supplemental_values_fail_closed():
    page = _intangible_page(
        tables=[
            _intangible_table(),
            _supplemental_table(current="1.234"),
            _supplemental_table(current="1.235"),
        ]
    )
    _compiled_specs, _cluster, _receipt, candidate = _intangible_candidate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert (
        "SUPPLEMENTAL_DISCLOSURE_VALUES_CONFLICT:FULLY_AMORTIZED_STILL_IN_USE"
        in candidate["reasons"]
    )


def test_supplemental_table_conflicting_dates_on_one_column_fail_closed():
    supplemental = _supplemental_table()
    supplemental["columns"][0]["header_path_exact"] = ["31/12/2025", "31/12/2024"]
    page = _intangible_page(tables=[_intangible_table(), supplemental])
    _compiled_specs, _cluster, _receipt, candidate = _intangible_candidate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert (
        "SUPPLEMENTAL_TABLE_PERIOD_EVIDENCE_CONFLICT:FULLY_AMORTIZED_STILL_IN_USE"
        in candidate["reasons"]
    )


def test_supplemental_table_cannot_fallback_when_only_comparative_period_is_visible():
    supplemental = _supplemental_table()
    supplemental["columns"][0]["header_path_exact"] = ["Nguyên giá", "31/12/2024"]
    supplemental["columns"][1]["header_path_exact"] = ["31/12/2023"]
    page = _intangible_page(tables=[_intangible_table(), supplemental])
    _compiled_specs, _cluster, _receipt, candidate = _intangible_candidate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert (
        "SUPPLEMENTAL_TABLE_CURRENT_PERIOD_NOT_VISIBLE:FULLY_AMORTIZED_STILL_IN_USE"
        in candidate["reasons"]
    )


def test_generic_other_role_uses_visible_subtotal_ancestor_direction():
    table = _intangible_table(subtotal=True)
    other = next(
        row
        for row in table["rows"]
        if row["label_exact"] == "Tăng khác" and row["hierarchy_path_exact"][0] == "Nguyên giá"
    )
    other["label_exact"] = "Khác"
    other["hierarchy_path_exact"] = ["Nguyên giá", "Tăng trong kỳ", "Khác"]
    purchase = next(
        row
        for row in table["rows"]
        if row["label_exact"] == "Mua trong kỳ" and row["hierarchy_path_exact"][0] == "Nguyên giá"
    )
    purchase["hierarchy_path_exact"] = ["Nguyên giá", "Tăng trong kỳ", "Mua trong kỳ"]
    page = _intangible_page(tables=[table])
    _compiled_specs, _cluster, _receipt, candidate = _intangible_candidate(page)
    assert candidate["status"] == READY
    assert any(item["role"] == "COST_OTHER_INCREASE" for item in candidate["mappings"])


def test_declared_direct_role_fallback_uses_structure_not_document_routing():
    table = _intangible_table()
    movement = next(row for row in table["rows"] if row["label_exact"] == "Mua trong kỳ")
    movement["label_exact"] = "Phân loại lại"
    movement["hierarchy_path_exact"] = ["Nguyên giá", "Phân loại lại"]
    page = _intangible_page(tables=[table])
    _compiled_specs, _cluster, _receipt, candidate = _intangible_candidate(page)
    assert candidate["status"] == READY
    assert any(item["role"] == "COST_OTHER_NET" for item in candidate["mappings"])
    assert not any(item["role"] == "COST_RECLASSIFICATION" for item in candidate["mappings"])

    compiled = _compiled_intangible()
    row = _row(
        "Phân loại lại",
        "Nguyên giá",
        ["10", "20", "30"],
        path=["Nguyên giá", "Giảm trong kỳ", "Phân loại lại"],
    )
    layout = fixed_asset_v1._branch_layout_for_row(row, compiled_specs=compiled)
    assert layout is not None
    assert fixed_asset_v1._role_for_row(row, layout, compiled_specs=compiled) == (
        "COST_RECLASSIFICATION"
    )


def test_direct_fallback_does_not_merge_a_separate_explicit_fallback_population():
    table = _intangible_table()
    movement = next(row for row in table["rows"] if row["label_exact"] == "Mua trong kỳ")
    movement["label_exact"] = "Phân loại lại"
    movement["hierarchy_path_exact"] = ["Nguyên giá", "Phân loại lại"]
    ending_index = next(
        index
        for index, row in enumerate(table["rows"])
        if row["label_exact"] == "Tại ngày 31 tháng 12 năm 2025"
        and row["hierarchy_path_exact"][0] == "Nguyên giá"
    )
    table["rows"].insert(
        ending_index,
        _row("Biến động khác", "Nguyên giá", ["-", "-", "-"]),
    )
    page = _intangible_page(tables=[table])
    _compiled_specs, _cluster, _receipt, candidate = _intangible_candidate(page)
    assert candidate["status"] == READY
    assert {item["role"] for item in candidate["mappings"]} >= {
        "COST_OTHER_NET",
        "COST_RECLASSIFICATION",
    }
    assert candidate["closure_receipt"]["table_receipt"]["direct_role_fallback_receipts"] == []


def test_exact_one_child_visible_subtotal_is_a_valid_frontier():
    table = _intangible_table(subtotal=True)
    table["rows"] = [
        row
        for row in table["rows"]
        if not (
            row["label_exact"] == "Tăng khác" and row["hierarchy_path_exact"][0] == "Nguyên giá"
        )
    ]
    for row in table["rows"]:
        if row["label_exact"] == "Tăng trong kỳ" and row["hierarchy_path_exact"][0] == "Nguyên giá":
            row["values_exact"] = ["4", "6", "10"]
        elif row["label_exact"] == "Tại ngày 31 tháng 12 năm 2025":
            branch = row["hierarchy_path_exact"][0]
            if branch == "Nguyên giá":
                row["values_exact"] = ["104", "206", "310"]
            elif branch == "Giá trị còn lại":
                row["values_exact"] = ["82", "162", "244"]
    page = _intangible_page(tables=[table])
    _compiled_specs, _cluster, _receipt, candidate = _intangible_candidate(page)
    assert candidate["status"] == READY
    blocks = candidate["closure_receipt"]["subtotal_collapse"]["block_receipts"]
    assert any(len(block["child_row_ids"]) == 1 for block in blocks)


def test_money_normalizer_accepts_repeated_dash_and_one_ocr_glyph_only():
    locator = {"column_id": "c1", "row_id": "r1"}
    repeated_dash = fixed_asset_v1._money("-\n-", source_locator=locator)
    contaminated_number = fixed_asset_v1._money("(18.000)单", source_locator=locator)
    assert (repeated_dash["state"], repeated_dash["coefficient"]) == ("DASH_ZERO", 0)
    assert contaminated_number["coefficient"] == -18000
    with pytest.raises(
        GeminiJsonFixedAssetRollforwardFamilyV1Error,
        match="money text is not one exact signed integer",
    ):
        fixed_asset_v1._money("100triệu", source_locator=locator)
    for unsupported in ("-一百-", "100万"):
        with pytest.raises(
            GeminiJsonFixedAssetRollforwardFamilyV1Error,
            match="money text is not one exact signed integer",
        ):
            fixed_asset_v1._money(unsupported, source_locator=locator)


def test_investment_property_sibling_fragment_aggregation_closes_from_local_graph():
    page = _investment_property_page(
        tables=[
            _investment_summary_table(),
            _investment_property_table(),
            _investment_cost_fragment(),
        ]
    )
    compiled, cluster, _receipt, _pages, candidate = _investment_candidate([_page_record(page)])
    assert compiled["bindings"]["CARRY_ENDING"] == 5974
    assert len(cluster["component_regions"]) == 3
    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 8
    by_role = {item["role"]: item for item in candidate["mappings"]}
    assert by_role["COST_OPENING"]["cell"]["coefficient"] == 310
    assert by_role["COST_PURCHASE"]["cell"]["coefficient"] == 35
    assert by_role["COST_ENDING"]["cell"]["coefficient"] == 345
    assert by_role["CARRY_OPENING"]["cell"]["coefficient"] == 250
    assert by_role["CARRY_ENDING"]["cell"]["coefficient"] == 279
    assert all(
        item["status"] == "EXACT"
        for item in candidate["closure_receipt"]["component_population_receipt"][
            "aggregate_equations"
        ]
    )


def test_investment_property_cost_only_schedule_binds_typed_statement_control():
    statement = _page_record(
        _investment_statement_page(current=15, comparative=10), physical_page=1
    )
    note = _page_record(
        _investment_property_page(tables=[_investment_cost_fragment()]),
        selected_page_ordinal=2,
        physical_page=20,
    )
    _compiled_specs, cluster, _receipt, _pages, candidate = _investment_candidate([statement, note])
    assert len(cluster["component_regions"]) == 2
    assert candidate["status"] == READY
    assert [(item["role"], item["cell"]["coefficient"]) for item in candidate["mappings"]] == [
        ("COST_OPENING", 10),
        ("COST_PURCHASE", 5),
        ("COST_ENDING", 15),
        ("CARRY_OPENING", 10),
        ("CARRY_ENDING", 15),
    ]


def test_investment_property_note_and_statement_controls_must_agree():
    statement = _page_record(
        _investment_statement_page(current=279, comparative=250), physical_page=1
    )
    note = _page_record(
        _investment_property_page(
            tables=[
                _investment_summary_table(),
                _investment_property_table(),
                _investment_cost_fragment(),
            ]
        ),
        selected_page_ordinal=2,
        physical_page=20,
    )
    _compiled_specs, cluster, _receipt, _pages, candidate = _investment_candidate([statement, note])
    assert candidate["status"] == READY
    assert cluster["summary_control_comparison_receipt"]["status"] == "EXACT"
    assert len(cluster["summary_control_comparison_receipt"]["controls"]) == 2

    mismatched = _page_record(
        _investment_statement_page(current=280, comparative=250), physical_page=1
    )
    unresolved = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[mismatched, note], compiled_specs=_compiled_investment_property()
    )
    assert unresolved["status"] == UNRESOLVED
    assert "SAME_PERIOD_CARRYING_SUMMARY_CONTROLS_MISMATCH" in unresolved["reasons"]


def test_investment_property_summary_without_rollforward_is_not_observed():
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(_investment_statement_page())],
        compiled_specs=_compiled_investment_property(),
    )
    assert cluster["status"] == NOT_OBSERVED
    assert cluster["reasons"] == []


def test_investment_property_aggregate_summary_mismatch_fails_closed():
    page = _investment_property_page(
        tables=[
            _investment_summary_table(current=280),
            _investment_property_table(),
            _investment_cost_fragment(),
        ]
    )
    _compiled_specs, _cluster, _receipt, _pages, candidate = _investment_candidate(
        [_page_record(page)]
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "AGGREGATE_CARRYING_CONTROL_EQUATION_MISMATCH:CARRY_ENDING" in candidate["reasons"]


def test_investment_property_summary_detail_total_equation_fails_closed():
    summary = _investment_summary_table()
    summary["rows"][0]["values_exact"][0] = "263"
    page = _investment_property_page(
        tables=[summary, _investment_property_table(), _investment_cost_fragment()]
    )
    _compiled_specs, _cluster, _receipt, _pages, candidate = _investment_candidate(
        [_page_record(page)]
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "SUMMARY_CONTROL_HORIZONTAL_EQUATION_MISMATCH:CARRY_ENDING" in candidate["reasons"]


def test_investment_property_sibling_population_must_equal_summary_population():
    summary = _investment_summary_table()
    summary["rows"].pop(1)
    page = _investment_property_page(
        tables=[summary, _investment_property_table(), _investment_cost_fragment()]
    )
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(page)], compiled_specs=_compiled_investment_property()
    )
    assert cluster["status"] == UNRESOLVED
    assert "SIBLING_COMPONENT_TO_SUMMARY_POPULATION_EXACT_SET_MISMATCH" in cluster["reasons"]


def test_investment_property_duplicate_sibling_population_title_is_ambiguous():
    second = _investment_cost_fragment()
    second["title_exact"] = _investment_property_table()["title_exact"]
    page = _investment_property_page(
        tables=[_investment_summary_table(), _investment_property_table(), second]
    )
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(page)], compiled_specs=_compiled_investment_property()
    )
    assert cluster["status"] == UNRESOLVED
    assert "SIBLING_COMPONENT_SUMMARY_POPULATION_IS_DUPLICATE" in cluster["reasons"]


def test_investment_property_foreign_table_breaks_sibling_component_interval():
    foreign = {
        "columns": [{"header_path_exact": ["Khoản mục"], "value_kind": "TEXT"}],
        "continuation": "NONE",
        "rows": [],
        "title_exact": "Thuyết minh ngoại lai",
        "unit_exact": None,
    }
    page = _investment_property_page(
        tables=[
            _investment_summary_table(),
            _investment_property_table(),
            foreign,
            _investment_cost_fragment(),
        ]
    )
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(page)], compiled_specs=_compiled_investment_property()
    )
    assert cluster["status"] == UNRESOLVED
    assert "CURRENT_SIBLING_COMPONENT_TABLE_INTERVAL_IS_NOT_CONTIGUOUS" in cluster["reasons"]


def test_investment_property_standalone_reset_heading_vetoes_owner_scope():
    page = _investment_property_page(
        tables=[_investment_property_table()],
        narratives=["14 Tài sản cố định hữu hình"],
    )
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(page)], compiled_specs=_compiled_investment_property()
    )
    assert cluster["status"] == UNRESOLVED
    assert "STRUCTURAL_RESET_HEADING_INSIDE_COMPONENT_OWNER_SCOPE" in cluster["reasons"]


def test_investment_property_incidental_reset_phrase_does_not_veto_owner_scope():
    page = _investment_property_page(
        tables=[_investment_property_table()],
        narratives=["Trong kỳ có chuyển từ tài sản cố định hữu hình theo phê duyệt."],
    )
    _compiled_specs, _cluster, _receipt, _pages, candidate = _investment_candidate(
        [_page_record(page)]
    )
    assert candidate["status"] == READY


@pytest.mark.parametrize(
    "child_label",
    ["Bất động sản đầu tư - Nguyên giá", "Hao mòn bất động sản đầu tư"],
)
def test_investment_property_statement_child_cannot_masquerade_as_root_control(child_label):
    statement = _investment_statement_page(current=15, comparative=10)
    statement_row = statement["sections"][0]["tables"][0]["rows"][0]
    statement_row["label_exact"] = child_label
    statement_row["hierarchy_path_exact"] = [statement_row["label_exact"]]
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[
            _page_record(statement, physical_page=1),
            _page_record(
                _investment_property_page(tables=[_investment_cost_fragment()]),
                selected_page_ordinal=2,
                physical_page=20,
            ),
        ],
        compiled_specs=_compiled_investment_property(),
    )
    assert cluster["status"] == UNRESOLVED
    assert "COMPONENT_AGGREGATION_REQUIRES_CARRYING_SUMMARY_CONTROL" in cluster["reasons"]


def test_investment_property_duplicate_summary_is_ambiguous():
    summary = _investment_summary_table()
    page = _investment_property_page(
        tables=[_investment_property_table(), summary, deepcopy(summary)]
    )
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(page)], compiled_specs=_compiled_investment_property()
    )
    assert cluster["status"] == UNRESOLVED
    assert "CURRENT_CARRYING_SUMMARY_CONTROL_IS_NOT_UNIQUE" in cluster["reasons"]


def test_investment_property_malformed_extra_summary_evidence_is_not_ignored():
    malformed = _investment_summary_table()
    malformed["rows"].insert(
        1,
        _row(
            "Khoản mục ngoại lai",
            "Bất động sản đầu tư",
            ["1", "1"],
            path=["Khoản mục ngoại lai"],
        ),
    )
    page = _investment_property_page(
        tables=[
            _investment_summary_table(),
            _investment_property_table(),
            _investment_cost_fragment(),
            malformed,
        ]
    )
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(page)], compiled_specs=_compiled_investment_property()
    )
    assert cluster["status"] == UNRESOLVED
    assert "CARRYING_SUMMARY_CONTROL_STRUCTURE_IS_NOT_AUTHENTICATED" in cluster["reasons"]


def test_investment_property_malformed_summary_without_schedule_is_not_observed():
    malformed = _investment_summary_table()
    malformed["rows"].insert(
        1,
        _row(
            "Khoản mục ngoại lai",
            "Bất động sản đầu tư",
            ["1", "1"],
            path=["Khoản mục ngoại lai"],
        ),
    )
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(_investment_property_page(tables=[malformed]))],
        compiled_specs=_compiled_investment_property(),
    )
    assert cluster["status"] == NOT_OBSERVED
    assert cluster["reasons"] == []


def test_investment_property_malformed_statement_root_control_is_not_ignored():
    statement = _investment_statement_page(current=15, comparative=10)
    statement["sections"][0]["tables"][0]["columns"][1]["header_path_exact"] = [
        "30/06/2025",
        "31/12/2024",
    ]
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[
            _page_record(statement, physical_page=1),
            _page_record(
                _investment_property_page(tables=[_investment_cost_fragment()]),
                selected_page_ordinal=2,
                physical_page=20,
            ),
        ],
        compiled_specs=_compiled_investment_property(),
    )
    assert cluster["status"] == UNRESOLVED
    assert "CARRYING_SUMMARY_CONTROL_STRUCTURE_IS_NOT_AUTHENTICATED" in cluster["reasons"]


def test_investment_property_unknown_numeric_fragment_is_not_ignored():
    fragment = _investment_cost_fragment()
    fragment["rows"].insert(2, _row("Dòng lạ", "Nguyên giá", ["1", "2", "3"]))
    page = _investment_property_page(tables=[_investment_property_table(), fragment])
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(page)], compiled_specs=_compiled_investment_property()
    )
    assert cluster["status"] == UNRESOLVED
    assert "UNCLASSIFIED_NUMERIC_ROW_INSIDE_FIXED_ASSET_BRANCH" in cluster["reasons"]


def test_investment_property_source_cannot_inject_an_internal_forced_role():
    fragment = _investment_cost_fragment()
    movement = next(row for row in fragment["rows"] if row["label_exact"] == "Mua trong kỳ")
    movement["label_exact"] = "Dòng nguồn không khai báo"
    movement["hierarchy_path_exact"][-1] = movement["label_exact"]
    movement["__forced_role"] = "COST_PURCHASE"
    page = _investment_property_page(tables=[fragment])
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(page)], compiled_specs=_compiled_investment_property()
    )
    assert cluster["status"] == UNRESOLVED
    assert "UNCLASSIFIED_NUMERIC_ROW_INSIDE_FIXED_ASSET_BRANCH" in cluster["reasons"]


def test_investment_property_movement_date_range_is_not_two_endpoints():
    fragment = _investment_cost_fragment()
    movement = next(row for row in fragment["rows"] if row["label_exact"] == "Mua trong kỳ")
    movement["label_exact"] = "Khấu hao từ ngày 1 tháng 1 năm 2025 đến ngày 31 tháng 12 năm 2025"
    movement["hierarchy_path_exact"][-1] = movement["label_exact"]
    page = _investment_property_page(tables=[fragment])
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(page)], compiled_specs=_compiled_investment_property()
    )
    assert cluster["status"] == UNRESOLVED
    assert "UNCLASSIFIED_NUMERIC_ROW_INSIDE_FIXED_ASSET_BRANCH" in cluster["reasons"]


def test_investment_property_component_unit_conflict_fails_before_mapping():
    page = _investment_property_page(
        tables=[
            _investment_summary_table(),
            _investment_property_table(),
            _investment_cost_fragment(unit="Nghìn VND"),
        ]
    )
    _compiled_specs, _cluster, _receipt, _pages, candidate = _investment_candidate(
        [_page_record(page)]
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "CURRENT_COMPONENT_MONEY_UNIT_AXIS_IS_NOT_UNIQUE" in candidate["reasons"]


def test_investment_property_same_context_tables_use_exact_endpoint_continuity():
    current = _investment_property_table()
    for row in current["rows"]:
        if row["label_exact"].startswith("Tại ngày 1 tháng 1"):
            row["label_exact"] = "Số dư đầu kỳ"
            row["hierarchy_path_exact"][-1] = "Số dư đầu kỳ"
        elif "31 tháng 12" in row["label_exact"]:
            row["label_exact"] = "Số dư cuối kỳ"
            row["hierarchy_path_exact"][-1] = "Số dư cuối kỳ"
    comparative = _investment_property_table(current_year=2024)
    comparative["rows"] = [
        _row("Nguyên giá", "Nguyên giá", [None, None, None], row_kind="GROUP", path=["Nguyên giá"]),
        _row(
            "Số dư đầu năm và cuối năm",
            "Nguyên giá",
            ["100", "200", "300"],
            row_kind="SUBTOTAL",
        ),
        _row(
            "Giá trị hao mòn lũy kế",
            "Giá trị hao mòn lũy kế",
            [None, None, None],
            row_kind="GROUP",
            path=["Giá trị hao mòn lũy kế"],
        ),
        _row("Số dư đầu năm", "Giá trị hao mòn lũy kế", ["18", "36", "54"]),
        _row("Khấu hao trong năm", "Giá trị hao mòn lũy kế", ["2", "4", "6"]),
        _row(
            "Số dư cuối năm",
            "Giá trị hao mòn lũy kế",
            ["20", "40", "60"],
            row_kind="TOTAL",
        ),
        _row(
            "Giá trị còn lại",
            "Giá trị còn lại",
            [None, None, None],
            row_kind="GROUP",
            path=["Giá trị còn lại"],
        ),
        _row("Số dư đầu năm", "Giá trị còn lại", ["82", "164", "246"]),
        _row(
            "Số dư cuối năm",
            "Giá trị còn lại",
            ["80", "160", "240"],
            row_kind="TOTAL",
        ),
    ]
    note_page = _investment_property_page(
        tables=[current, comparative],
        narratives=["Cho kỳ sáu tháng kết thúc ngày 30 tháng 6 năm 2025"],
    )
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[
            _page_record(
                _typed_balance_sheet_page(current="30/06/2025", comparative="31/12/2024"),
                physical_page=1,
            ),
            _page_record(note_page, selected_page_ordinal=2, physical_page=20),
        ],
        compiled_specs=_compiled_investment_property(),
    )
    assert cluster["status"] == READY
    assert len(cluster["component_regions"]) == 1
    assert cluster["component_regions"][0]["table_id"] == "t1"
    assert cluster["control_regions"][0]["table_id"] == "t2"
    assert cluster["control_regions"][0]["period_end_date"] == "2024-12-31"
    combined = next(item for item in cluster["family_table_inventory"] if item["table_id"] == "t2")[
        "combined_endpoint_receipts"
    ]
    assert combined == [
        {
            "binding_kind": "ONE_SOURCE_ROW_BINDS_EXPLICIT_OPENING_AND_ENDING_SEMANTICS",
            "roles": ["COST_OPENING", "COST_ENDING"],
            "source_label_exact": "Số dư đầu năm và cuối năm",
            "source_row_id": "r2",
        }
    ]


def test_investment_property_gemini_dash_annotation_is_local_zero_observation():
    cell = fixed_asset_v1._money("-带有横线-", source_locator={"column_id": "c1", "row_id": "r1"})
    assert cell["state"] == "DASH_ZERO"
    assert cell["coefficient"] == 0
    assert cell["source_text"] == "-带有横线-"


def test_investment_property_candidate_coherent_mapping_tamper_rejects_replay():
    page = _investment_property_page(tables=[_investment_property_table()])
    compiled, cluster, receipt, pages, candidate = _investment_candidate([_page_record(page)])
    forged = deepcopy(candidate)
    forged["mappings"][0]["cell"]["coefficient"] += 7
    mapping_material = {
        key: value for key, value in forged["mappings"][0].items() if key != "item_mapping_id"
    }
    forged["mappings"][0]["item_mapping_id"] = "gjffarimv1:item:" + canonical_json_sha256_v1(
        mapping_material
    )
    candidate_material = {key: value for key, value in forged.items() if key != "candidate_id"}
    forged["candidate_id"] = "gjffarcv1:candidate:" + canonical_json_sha256_v1(candidate_material)
    with pytest.raises(GeminiJsonFixedAssetRollforwardFamilyV1Error):
        validate_gemini_json_fixed_asset_rollforward_family_candidate_replay_v1(
            forged,
            regions=cluster["component_regions"],
            control_regions=cluster["control_regions"],
            page_json_by_version=pages,
            compiled_specs=compiled,
            query_receipt=receipt,
        )


def test_two_period_tables_under_one_section_select_by_endpoint_period():
    page = _intangible_page(
        tables=[_intangible_table(current_year=2025), _intangible_table(current_year=2024)]
    )
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(page)], compiled_specs=_compiled_intangible()
    )
    assert cluster["status"] == READY
    assert cluster["component_regions"][0]["period_end_date"] == "2025-12-31"
    assert cluster["control_regions"][0]["period_end_date"] == "2024-12-31"


def test_coherent_candidate_mapping_tamper_rejects_exact_page_replay():
    compiled, page, cluster, receipt, candidate = _candidate()
    forged = deepcopy(candidate)
    forged["mappings"][0]["cell"]["coefficient"] += 1
    mapping_material = {
        key: value for key, value in forged["mappings"][0].items() if key != "item_mapping_id"
    }
    forged["mappings"][0]["item_mapping_id"] = "gjffarimv1:item:" + canonical_json_sha256_v1(
        mapping_material
    )
    candidate_material = {key: value for key, value in forged.items() if key != "candidate_id"}
    forged["candidate_id"] = "gjffarcv1:candidate:" + canonical_json_sha256_v1(candidate_material)
    with pytest.raises(GeminiJsonFixedAssetRollforwardFamilyV1Error):
        validate_gemini_json_fixed_asset_rollforward_family_candidate_replay_v1(
            forged,
            regions=cluster["component_regions"],
            control_regions=cluster["control_regions"],
            page_json_by_version={cluster["component_regions"][0]["page_json_version_id"]: page},
            compiled_specs=compiled,
            query_receipt=receipt,
        )
