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
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    validate_source_observation_mapping_contract_v1,
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
    paths = (
        "config/families/tm-leased-fixed-assets-topology-v1.json",
        "config/families/tm-leased-fixed-assets-evaluation-v1.json",
        "config/families/tm-leased-fixed-assets-schema-binding-v1.json",
    )
    topology, evaluation, binding = [json.loads((ROOT / path).read_bytes()) for path in paths]
    return compile_gemini_json_fixed_asset_rollforward_family_specs_v1(
        topology, evaluation, binding
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


def _endpoint_first_table(*, ending_carry="264"):
    return {
        "columns": [
            {"header_path_exact": ["Nhà cửa, vật kiến trúc"], "value_kind": "MONEY"},
            {"header_path_exact": ["Máy móc, thiết bị"], "value_kind": "MONEY"},
            {"header_path_exact": ["Tổng cộng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            _row(
                "Số dư đầu kỳ tại ngày 01/01/2025",
                "Số dư đầu kỳ",
                [None, None, "240"],
                row_kind="SUBTOTAL",
                path=["Số dư đầu kỳ tại ngày 01/01/2025"],
            ),
            _row(
                "- Nguyên giá TSCĐ",
                "Số dư đầu kỳ",
                ["100", "200", "300"],
                path=["Số dư đầu kỳ- Nguyên giá TSCĐ"],
            ),
            _row(
                "- Hao mòn TSCĐ",
                "Số dư đầu kỳ",
                ["(20)", "(40)", "(60)"],
                path=["Số dư đầu kỳ", "- Hao mòn TSCĐ"],
            ),
            _row(
                "Số dư cuối kỳ tại ngày 31/12/2025",
                "Số dư cuối kỳ",
                [None, None, ending_carry],
                row_kind="SUBTOTAL",
                path=["Số dư cuối kỳ tại ngày 31/12/2025"],
            ),
            _row(
                "- Nguyên giá TSCĐ",
                "Số dư cuối kỳ",
                ["110", "220", "330"],
                path=["Số dư cuối kỳ- Nguyên giá TSCĐ"],
            ),
            _row(
                "- Hao mòn TSCĐ",
                "Số dư cuối kỳ",
                ["(22)", "(44)", "(66)"],
                path=["Số dư cuối kỳ", "- Hao mòn TSCĐ"],
            ),
        ],
        "title_exact": "Tài sản cố định hữu hình",
        "unit_exact": "Triệu VND",
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


def _investment_relative_statement_page(*, current=15, comparative=10):
    page = _investment_statement_page(current=current, comparative=comparative)
    section = page["sections"][0]
    section["title_exact"] = (
        "BÁO CÁO TÌNH HÌNH TÀI CHÍNH tại ngày 31 tháng 12 năm 2025"
    )
    columns = section["tables"][0]["columns"]
    columns[0]["header_path_exact"] = ["Số cuối năm"]
    columns[1]["header_path_exact"] = ["Số đầu năm"]
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


def _nab_single_asset_leased_table(
    *,
    opening_label="Số dư đầu năm",
    ending_label="Số dư cuối năm",
    cost_opening="159.317",
    cost_increase_label="Tăng trong năm",
    cost_increase="1.715",
    cost_transfer="(32.200)",
    cost_ending="128.832",
    depreciation_opening="79.572",
    depreciation_charge_label="Khấu hao trong năm",
    depreciation_charge="23.953",
    depreciation_transfer="(28.311)",
    depreciation_ending="75.214",
    carrying_opening="79.745",
    carrying_ending="53.618",
):
    rows = [
        _row("Nguyên giá", "Nguyên giá", [None], row_kind="GROUP", path=["Nguyên giá"]),
        _row(opening_label, "Nguyên giá", [cost_opening]),
    ]
    if cost_increase is not None:
        rows.append(_row(cost_increase_label, "Nguyên giá", [cost_increase]))
    rows.extend(
        [
            _row(
                "Chuyển sang tài sản cố định hữu hình",
                "Nguyên giá",
                [cost_transfer],
            ),
            _row(ending_label, "Nguyên giá", [cost_ending], row_kind="SUBTOTAL"),
        ]
    )
    depreciation_branch = "Giá trị khấu hao luỹ kế"
    rows.extend(
        [
            _row(
                depreciation_branch,
                depreciation_branch,
                [None],
                row_kind="GROUP",
                path=[depreciation_branch],
            ),
            _row(opening_label, depreciation_branch, [depreciation_opening]),
            _row(depreciation_charge_label, depreciation_branch, [depreciation_charge]),
            _row(
                "Chuyển sang tài sản cố định hữu hình",
                depreciation_branch,
                [depreciation_transfer],
            ),
            _row(
                ending_label,
                depreciation_branch,
                [depreciation_ending],
                row_kind="SUBTOTAL",
            ),
            _row(
                "Giá trị còn lại",
                "Giá trị còn lại",
                [None],
                row_kind="GROUP",
                path=["Giá trị còn lại"],
            ),
            _row(opening_label, "Giá trị còn lại", [carrying_opening]),
            _row(
                ending_label,
                "Giá trị còn lại",
                [carrying_ending],
                row_kind="SUBTOTAL",
            ),
        ]
    )
    return {
        "columns": [
            {"header_path_exact": ["Phương tiện vận tải"], "value_kind": "MONEY"}
        ],
        "continuation": "NONE",
        "rows": rows,
        "title_exact": "Tài sản cố định thuê tài chính năm 2025",
        "unit_exact": "Triệu đồng",
    }


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


def test_positive_printed_decrease_uses_configured_economic_direction_in_equations():
    table = _table()
    cost_ending = next(
        index
        for index, row in enumerate(table["rows"])
        if row["hierarchy_path_exact"][0] == "Nguyên giá"
        and row["label_exact"].startswith("Tại ngày 31")
    )
    table["rows"].insert(
        cost_ending,
        _row("Thanh lý", "Nguyên giá", ["2", "3", "5"]),
    )
    depreciation_ending = next(
        index
        for index, row in enumerate(table["rows"])
        if row["hierarchy_path_exact"][0] == "Hao mòn lũy kế"
        and row["label_exact"].startswith("Tại ngày 31")
    )
    table["rows"].insert(
        depreciation_ending,
        _row("Thanh lý", "Hao mòn lũy kế", ["1", "1", "2"]),
    )
    for row in table["rows"]:
        branch = row["hierarchy_path_exact"][0]
        if row["label_exact"].startswith("Tại ngày 31"):
            row["values_exact"] = {
                "Nguyên giá": ["108", "217", "325"],
                "Hao mòn lũy kế": ["21", "43", "64"],
                "Giá trị còn lại": ["87", "174", "261"],
            }[branch]
    _compiled_specs, _page_json, _cluster, _receipt, candidate = _candidate(table)
    assert candidate["status"] == READY
    by_role = {item["role"]: item for item in candidate["mappings"]}
    assert by_role["COST_DISPOSAL"]["cell"]["coefficient"] == 5
    assert by_role["DEP_DISPOSAL"]["cell"]["coefficient"] == 2
    receipts = candidate["closure_receipt"]["table_receipt"][
        "movement_direction_receipts"
    ]
    assert {
        (item["role"], item["configured_direction"], item["equation_multiplier"])
        for item in receipts
        if item["role"].endswith("DISPOSAL")
    } == {
        ("COST_DISPOSAL", "DECREASE", -1),
        ("DEP_DISPOSAL", "DECREASE", -1),
    }


def test_visible_total_remains_authoritative_when_detail_cells_are_blank():
    table = _table()
    purchase = next(row for row in table["rows"] if row["label_exact"] == "Mua trong kỳ")
    purchase["values_exact"] = ["10", None, "30"]
    _compiled_specs, _page_json, _cluster, _receipt, candidate = _candidate(table)
    assert candidate["status"] == READY
    mapping = next(item for item in candidate["mappings"] if item["role"] == "COST_PURCHASE")
    assert mapping["cell"]["coefficient"] == 30
    assert candidate["closure_receipt"]["width_seal"]["status"] == (
        "SEALED_EXACT_PRESERVED_BLANK_TOTAL_LANE"
    )
    omission = candidate["closure_receipt"]["table_receipt"]["omitted_horizontal_rows"]
    assert omission == [
        {
            "disposition": "SOURCE_VISIBLE_TOTAL_CONTROLS_VERTICAL_ONLY",
            "preserved_blank_column_ids": ["c2"],
            "row_id": "r3",
        }
    ]
    projected = candidate["closure_receipt"]["width_seal"]["effective_projection"]
    row = next(item for item in projected["rows"] if item["row_id"] == "r3")
    assert row["cells"]["c2"]["state"] == "BLANK"
    assert row["cells"]["c2"]["coefficient"] is None


def test_blank_total_exact_net_zero_row_is_source_only_and_never_mapped_as_zero():
    table = _table()
    table["rows"].insert(
        3,
        _row("Phân loại lại", "Nguyên giá", ["5", "(5)", None]),
    )
    _compiled_specs, _page_json, _cluster, _receipt, candidate = _candidate(table)
    assert candidate["status"] == READY
    assert not any(item["role"] == "COST_RECLASSIFICATION" for item in candidate["mappings"])
    omission = candidate["closure_receipt"]["table_receipt"]["omitted_horizontal_rows"]
    assert any(
        item["disposition"] == "SOURCE_ONLY_DERIVED_EXACT_NET_ZERO_NO_MAPPING"
        and item["row_id"] == "r4"
        for item in omission
    )
    projected = candidate["closure_receipt"]["width_seal"]["effective_projection"]
    row = next(item for item in projected["rows"] if item["row_id"] == "r4")
    assert row["cells"]["c3"]["state"] == "BLANK"
    assert row["cells"]["c3"]["coefficient"] is None


def test_blank_total_nonzero_detail_row_remains_unresolved():
    table = _table()
    table["rows"].insert(
        3,
        _row("Phân loại lại", "Nguyên giá", ["5", "(4)", None]),
    )
    _compiled_specs, _page_json, _cluster, _receipt, candidate = _candidate(table)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "SOURCE_TOTAL_BLANK_WITH_NONZERO_OR_INCOMPLETE_DETAILS:r4" in candidate["reasons"]


def test_endpoint_first_layout_maps_six_visible_endpoints_with_carrying_controls_only():
    _compiled_specs, _page_json, cluster, _receipt, candidate = _candidate(
        _endpoint_first_table()
    )
    assert cluster["status"] == READY
    assert candidate["status"] == READY
    assert {item["role"] for item in candidate["mappings"]} == {
        "COST_OPENING",
        "COST_ENDING",
        "DEP_OPENING",
        "DEP_ENDING",
        "CARRY_OPENING",
        "CARRY_ENDING",
    }
    table_receipt = candidate["closure_receipt"]["table_receipt"]
    assert table_receipt["endpoint_first_layout_receipt"]["projection_kind"] == (
        "ENDPOINT_ONLY_NO_MOVEMENT_ROLLFORWARD_EQUATION"
    )
    assert {item["equation_id"] for item in table_receipt["equations"]} >= {
        "carrying:CARRY_OPENING",
        "carrying:CARRY_ENDING",
    }
    assert not any(
        item["equation_id"].startswith("branch:") for item in table_receipt["equations"]
    )
    cost = next(item for item in candidate["mappings"] if item["role"] == "COST_OPENING")
    assert cost["source_refs"][0]["label_exact"] == "- Nguyên giá TSCĐ"


def test_endpoint_first_layout_carrying_tamper_fails_closed():
    _compiled_specs, _page_json, _cluster, _receipt, candidate = _candidate(
        _endpoint_first_table(ending_carry="266")
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "PRESERVED_BLANK_TOTAL_LANE_EQUATION_MISMATCH" in candidate["reasons"]


def test_endpoint_first_unknown_numeric_columns_are_typed_from_configured_headers():
    table = _endpoint_first_table()
    table["columns"] = [
        {"header_path_exact": ["Nhà cửa, vật, kiến trúc"], "value_kind": "UNKNOWN"},
        {"header_path_exact": ["Máy móc thiết bị"], "value_kind": "UNKNOWN"},
        {"header_path_exact": ["TSCĐ khác"], "value_kind": "UNKNOWN"},
        {"header_path_exact": ["Tổng cộng"], "value_kind": "UNKNOWN"},
    ]
    for row in table["rows"]:
        row["values_exact"].insert(-1, None)
    table["rows"][1]["values_exact"][1] = "195"
    table["rows"][1]["values_exact"][2] = "5"
    table["rows"][2]["values_exact"][1] = "(39)"
    table["rows"][2]["values_exact"][2] = "(1)"
    table["rows"][4]["values_exact"][1] = "214"
    table["rows"][4]["values_exact"][2] = "6"
    table["rows"][5]["values_exact"][1] = "(42)"
    table["rows"][5]["values_exact"][2] = "(2)"

    _compiled_specs, _page_json, cluster, _receipt, candidate = _candidate(table)

    assert cluster["status"] == READY
    assert candidate["status"] == READY
    typing = candidate["closure_receipt"]["table_receipt"][
        "endpoint_first_layout_receipt"
    ]["column_typing_receipt"]
    assert typing == {
        "column_ordinals": [1, 2, 3, 4],
        "policy": (
            "ALL_UNKNOWN_COLUMNS_CONFIGURED_ASSET_OR_UNIQUE_RIGHT_EDGE_TOTAL_"
            "WITH_EXACT_INTEGER_MONEY_CELLS"
        ),
        "source_value_kind": "UNKNOWN",
    }


def test_endpoint_first_unknown_column_with_nonmoney_cell_fails_closed():
    table = _endpoint_first_table()
    for column in table["columns"]:
        column["value_kind"] = "UNKNOWN"
    table["rows"][1]["values_exact"][0] = "không phải số"

    compiled = _compiled()
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(_page(table))], compiled_specs=compiled
    )

    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert "FAMILY_SIGNAL_TABLE_IS_NOT_A_COMPLETE_FIXED_ASSET_PRESENTATION" in cluster[
        "reasons"
    ]


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


def test_path_depth_without_subtotal_ancestor_does_not_turn_direct_movement_into_child():
    table = _table()
    purchase = next(row for row in table["rows"] if row["label_exact"] == "Mua trong kỳ")
    purchase["hierarchy_path_exact"] = [
        "Nguyên giá",
        "Số dư đầu năm",
        "- Mua trong kỳ",
    ]
    _compiled_specs, _page_json, _cluster, _receipt, candidate = _candidate(table)
    assert candidate["status"] == READY
    assert not any(
        reason.startswith("VISIBLE_SUBTOTAL_CHILD_HAS_NO_PRECEDING_SUBTOTAL")
        for reason in candidate["reasons"]
    )
    branch = next(
        item
        for item in candidate["closure_receipt"]["table_receipt"]["equations"]
        if item["equation_id"] == "branch:COST_BRANCH"
    )
    assert any(term["row_id"] == "r3" for term in branch["terms"])


def test_flattened_subtotal_child_without_newline_uses_visible_ancestor_surface():
    table = _table(subtotal=True)
    for row in table["rows"]:
        path = row["hierarchy_path_exact"]
        if len(path) == 2 and "\n- " in path[-1]:
            path[-1] = path[-1].replace("\n- ", "- ")
    _compiled_specs, _page_json, _cluster, _receipt, candidate = _candidate(table)
    assert candidate["status"] == READY
    collapse = candidate["closure_receipt"]["subtotal_collapse"]
    assert any(
        item["parent_projection_mode"] == "CONSISTENT_FLATTENED_EXTERNAL_PARENT"
        for item in collapse["block_receipts"]
    )


def test_unclassified_numeric_source_row_fails_closed():
    table = _table()
    table["rows"].insert(2, _row("Dòng lạ", "Nguyên giá", ["1", "2", "3"]))
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(_page(table))], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert "UNCLASSIFIED_NUMERIC_ROW_INSIDE_FIXED_ASSET_BRANCH" in cluster["reasons"]


def test_declared_source_only_row_is_receipted_without_schema_mapping_or_branch_poison():
    table = _table()
    table["rows"].insert(
        4,
        _row(
            "Đã khấu hao hết nhưng vẫn còn sử dụng",
            "Nguyên giá",
            ["5", "7", "12"],
            path=["Nguyên giá", "Trong đó", "Đã khấu hao hết nhưng vẫn còn sử dụng"],
        ),
    )
    _compiled_specs, _page_json, _cluster, _receipt, candidate = _candidate(table)
    assert candidate["status"] == READY
    assert not any(
        item["source_refs"][0]["label_exact"] == "Đã khấu hao hết nhưng vẫn còn sử dụng"
        for item in candidate["mappings"]
    )
    assert candidate["closure_receipt"]["table_receipt"]["source_only_rows"] == [
        {
            "disposition": "SOURCE_ONLY_NO_SCHEMA_ROLE",
            "label_exact": "Đã khấu hao hết nhưng vẫn còn sử dụng",
            "row_id": "r5",
            "source_ordinal": 5,
        }
    ]


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


def test_decrease_slash_increase_other_uses_net_role_and_preserves_printed_sign():
    table = _table()
    ending_index = next(
        index
        for index, row in enumerate(table["rows"])
        if row["hierarchy_path_exact"][0] == "Nguyên giá"
        and row["label_exact"].startswith("Tại ngày 31")
    )
    table["rows"].insert(
        ending_index,
        _row("(Giảm)/ Tăng khác", "Nguyên giá", ["(1)", "1", "-"]),
    )
    _compiled_specs, _page_json, _cluster, _receipt, candidate = _candidate(table)
    assert candidate["status"] == READY
    mapping = next(item for item in candidate["mappings"] if item["role"] == "COST_OTHER_NET")
    assert mapping["cell"]["coefficient"] == 0
    direction = next(
        item
        for item in candidate["closure_receipt"]["table_receipt"][
            "movement_direction_receipts"
        ]
        if item["role"] == "COST_OTHER_NET"
    )
    assert direction["configured_direction"] == "PRESERVE_SIGN"
    assert direction["equation_multiplier"] == 1


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


def test_two_distinct_31_december_balances_bind_chronological_endpoints():
    table = _table()
    for row in table["rows"]:
        if row["label_exact"] != "Tại ngày 1 tháng 1 năm 2025":
            continue
        row["label_exact"] = "Tại ngày 31/12/2024"
        row["hierarchy_path_exact"][-1] = "Tại ngày 31/12/2024"
    _compiled_specs, _page_json, cluster, _receipt, candidate = _candidate(table)
    assert cluster["status"] == READY
    assert cluster["component_regions"][0]["period_end_date"] == "2025-12-31"
    assert candidate["status"] == READY
    receipt = candidate["closure_receipt"]["table_receipt"][
        "ordered_dated_endpoint_receipt"
    ]
    assert receipt["projection_kind"] == (
        "TWO_DISTINCT_DATED_BALANCE_ROWS_CHRONOLOGICAL_ENDPOINT_BINDING"
    )
    assert {item["projected_role"] for item in receipt["rows"]} == {
        "COST_OPENING",
        "COST_ENDING",
        "DEP_OPENING",
        "DEP_ENDING",
        "CARRY_OPENING",
        "CARRY_ENDING",
    }


def test_unique_endpoint_row_inherits_preceding_visible_branch_scope():
    table = _table()
    ending = next(
        row
        for row in table["rows"]
        if row["hierarchy_path_exact"][0] == "Nguyên giá"
        and row["label_exact"].startswith("Tại ngày 31")
    )
    ending["hierarchy_path_exact"] = [ending["label_exact"]]
    _compiled_specs, _page_json, _cluster, _receipt, candidate = _candidate(table)
    assert candidate["status"] == READY
    scope = candidate["closure_receipt"]["table_receipt"][
        "ordered_branch_scope_receipt"
    ]
    assert scope["projection_kind"] == "PRECEDING_EXPLICIT_BRANCH_UNIQUE_ROLE_BINDING"
    assert scope["rows"] == [
        {
            "branch_role": "COST_BRANCH",
            "projected_role": "COST_ENDING",
            "source_ordinal": 4,
        }
    ]


def test_adjacent_continuation_heading_inherits_exact_prior_owner_scope():
    current = _page_record(_page(_table()), physical_page=10)
    comparative_table = _table(current_year=2024)
    comparative_table["title_exact"] = "Năm kết thúc ngày 31 tháng 12 năm 2024"
    comparative_page = _page(comparative_table)
    comparative_page["sections"][0]["title_exact"] = (
        "Thuyết minh báo cáo tài chính (tiếp theo)"
    )
    comparative = _page_record(
        comparative_page, selected_page_ordinal=2, physical_page=11
    )
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[current, comparative], compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    assert cluster["component_regions"][0]["period_end_date"] == "2025-12-31"
    assert cluster["control_regions"][0]["period_end_date"] == "2024-12-31"
    inherited = next(
        item
        for item in cluster["family_table_inventory"]
        if item["physical_page"] == 11
    )
    assert inherited["classification"]["adjacent_owner_continuation_receipt"][
        "status"
    ] == "EXACT_ADJACENT_OWNER_SCOPE"


def _trailing_owner_page(title="11. Tài sản cố định hữu hình"):
    page = _page()
    page["sections"] = [
        {
            "content_kind": "FINANCIAL_NOTE",
            "narratives_exact": [],
            "statement_type": "NOT_APPLICABLE",
            "tables": [],
            "title_exact": title,
        }
    ]
    return page


def test_trailing_empty_owner_heading_binds_first_table_on_immediate_next_page():
    table = _endpoint_first_table()
    table["title_exact"] = None
    page = _page(table)
    page["sections"][0]["title_exact"] = None
    records = [
        _page_record(_trailing_owner_page(), physical_page=9),
        _page_record(page, selected_page_ordinal=2, physical_page=10),
    ]
    compiled = _compiled()
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=records, compiled_specs=compiled
    )
    assert cluster["status"] == READY
    receipt = cluster["family_table_inventory"][0]["classification"][
        "trailing_owner_heading_receipt"
    ]
    assert receipt["status"] == "EXACT_TRAILING_OWNER_HEADING_NEXT_PAGE_SCOPE"
    query = build_gemini_json_fixed_asset_rollforward_region_query_receipt_v1(
        cluster["component_regions"], control_regions=[]
    )
    candidate = evaluate_gemini_json_fixed_asset_rollforward_family_cluster_v1(
        regions=cluster["component_regions"],
        control_regions=[],
        page_json_by_version={item["page_json_version_id"]: item["page_json"] for item in records},
        compiled_specs=compiled,
        query_receipt=query,
    )
    assert candidate["status"] == READY


def test_unrelated_trailing_empty_heading_cannot_supply_owner_scope():
    table = _endpoint_first_table()
    table["title_exact"] = None
    page = _page(table)
    page["sections"][0]["title_exact"] = None
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[
            _page_record(_trailing_owner_page("11. Tài sản có khác"), physical_page=9),
            _page_record(page, selected_page_ordinal=2, physical_page=10),
        ],
        compiled_specs=_compiled(),
    )
    assert cluster["status"] == UNRESOLVED
    assert "EXPLICIT_FIXED_ASSET_OWNER_NOT_VISIBLE" in cluster["reasons"]


def test_quarter_heading_on_typed_statement_authenticates_period_end():
    statement = _typed_balance_sheet_page()
    statement["sections"][0]["title_exact"] = (
        "BÁO CÁO TÌNH HÌNH TÀI CHÍNH QUÝ II/2025"
    )
    statement["sections"][0]["tables"][0]["columns"][0]["header_path_exact"] = [
        "Số dư cuối quý"
    ]
    statement["sections"][0]["tables"][0]["columns"][1]["header_path_exact"] = [
        "Số dư đầu năm"
    ]
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[
            _page_record(statement, physical_page=1),
            _page_record(
                _page(_undated_table()), selected_page_ordinal=2, physical_page=10
            ),
        ],
        compiled_specs=_compiled(),
    )
    assert cluster["status"] == READY
    assert cluster["component_regions"][0]["period_end_date"] == "2025-06-30"
    assert cluster["component_regions"][0]["period_selection_kind"] == (
        "UNIQUE_TYPED_DOCUMENT_REPORTING_DATE"
    )


def test_literal_json_newline_escape_is_layout_whitespace_not_header_text():
    assert fixed_asset_v1._normalized("Phương tiện vận\\ntải truyền dẫn") == (
        fixed_asset_v1._normalized("Phương tiện vận tải truyền dẫn")
    )


def test_interim_month_heading_on_typed_statement_authenticates_period_end():
    statement = _typed_balance_sheet_page()
    statement["sections"][0]["title_exact"] = (
        "BÁO CÁO TÌNH HÌNH TÀI CHÍNH 6 THÁNG ĐẦU NĂM 2025"
    )
    statement["sections"][0]["tables"][0]["columns"][0]["header_path_exact"] = [
        "Số dư cuối kỳ"
    ]
    statement["sections"][0]["tables"][0]["columns"][1]["header_path_exact"] = [
        "Số dư đầu năm"
    ]
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[
            _page_record(statement, physical_page=1),
            _page_record(
                _page(_undated_table()), selected_page_ordinal=2, physical_page=10
            ),
        ],
        compiled_specs=_compiled(),
    )
    assert cluster["status"] == READY
    assert cluster["component_regions"][0]["period_end_date"] == "2025-06-30"
    assert cluster["component_regions"][0]["period_selection_kind"] == (
        "UNIQUE_TYPED_DOCUMENT_REPORTING_DATE"
    )


def test_first_six_months_of_fiscal_year_ending_december_binds_june_not_december():
    assert fixed_asset_v1._governed_period_end_from_surface(
        "6 tháng đầu của năm tài chính kết thúc ngày 31 tháng 12 năm 2025"
    ).isoformat() == "2025-06-30"


def test_uniform_period_in_asset_headers_outranks_source_only_disclosure_dates():
    current = _page_record(_page(_table()), physical_page=10)
    comparative_table = _undated_table()
    for column in comparative_table["columns"]:
        column["header_path_exact"].insert(
            0, "Kỳ sáu tháng kết thúc ngày 30 tháng 6 năm 2024"
        )
    comparative_page = _page(comparative_table)
    comparative_page["sections"][0]["narratives_exact"] = [
        "Tại ngày 30 tháng 6 năm 2025, tài sản đã khấu hao hết nhưng vẫn đang được sử dụng."
    ]
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[
            current,
            _page_record(
                comparative_page, selected_page_ordinal=2, physical_page=11
            ),
        ],
        compiled_specs=_compiled(),
    )
    assert cluster["status"] == READY
    assert cluster["component_regions"][0]["period_end_date"] == "2025-12-31"
    assert cluster["control_regions"][0]["period_end_date"] == "2024-06-30"


def _missing_unit_table():
    table = _table(unit=None)
    for column in table["columns"]:
        column["header_path_exact"] = column["header_path_exact"][:1]
    return table


def _balance_sheet_owner_page(*, current="264000000", comparative="240000000"):
    page = _typed_balance_sheet_page()
    page["sections"][0]["tables"][0]["unit_exact"] = "VND"
    page["sections"][0]["tables"][0]["rows"] = [
        _row(
            "Tài sản cố định hữu hình",
            "Tài sản cố định hữu hình",
            [current, comparative],
            row_kind="TOTAL",
            path=["Tài sản cố định hữu hình"],
        )
    ]
    return page


def _candidate_with_statement_cross_control(statement_page, *, table=None):
    compiled = _compiled()
    note_page = _page(_missing_unit_table() if table is None else table)
    page_records = [
        _page_record(statement_page, physical_page=1),
        _page_record(note_page, selected_page_ordinal=2, physical_page=10),
    ]
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=page_records, compiled_specs=compiled
    )
    assert cluster["status"] == READY
    receipt = build_gemini_json_fixed_asset_rollforward_region_query_receipt_v1(
        cluster["component_regions"], control_regions=cluster["control_regions"]
    )
    candidate = evaluate_gemini_json_fixed_asset_rollforward_family_cluster_v1(
        regions=cluster["component_regions"],
        control_regions=cluster["control_regions"],
        page_json_by_version={
            item["page_json_version_id"]: item["page_json"] for item in page_records
        },
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    return candidate


def test_missing_local_unit_resolves_from_exact_typed_balance_sheet_owner_vector():
    candidate = _candidate_with_statement_cross_control(_balance_sheet_owner_page())
    assert candidate["status"] == READY
    assert {item["bound_unit"] for item in candidate["mappings"]} == {"MILLION_VND"}
    unit_axis = candidate["closure_receipt"]["table_receipt"]["unit_axis"]
    assert unit_axis["cross_control_receipt"]["status"] == "EXACT_UNIQUE_LOCAL_UNIT"


def test_missing_local_unit_cross_control_value_tamper_fails_closed():
    candidate = _candidate_with_statement_cross_control(
        _balance_sheet_owner_page(current="265000000")
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "CURRENT_TABLE_MONEY_UNIT_IS_NOT_COMPLETE" in candidate["reasons"]


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


def test_exact_document_current_table_dominates_undated_complete_sibling_as_source_only():
    historical_page = _page(_undated_table())
    historical_page["sections"][0]["narratives_exact"] = [
        "Tài sản đã khấu hao hết nhưng vẫn đang được sử dụng tại ngày báo cáo."
    ]
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[
            _page_record(_typed_balance_sheet_page(), physical_page=1),
            _page_record(
                _page(_table()), selected_page_ordinal=2, physical_page=10
            ),
            _page_record(
                historical_page, selected_page_ordinal=3, physical_page=11
            ),
        ],
        compiled_specs=_compiled(),
    )
    assert cluster["status"] == READY
    assert cluster["component_regions"][0]["physical_page"] == 10
    assert cluster["control_regions"] == []
    assert next(
        item
        for item in cluster["family_table_inventory"]
        if item["physical_page"] == 11
    )["disposition"] == "SOURCE_ONLY_UNDATED_NONCURRENT_TABLE"


def test_undated_complete_sibling_stays_ambiguous_without_declared_policy():
    compiled = _compiled()
    compiled["evaluation"]["undated_sibling_policy"] = None
    historical_page = _page(_undated_table())
    historical_page["sections"][0]["narratives_exact"] = [
        "Tài sản đã khấu hao hết nhưng vẫn đang được sử dụng tại ngày báo cáo."
    ]
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[
            _page_record(_typed_balance_sheet_page(), physical_page=1),
            _page_record(
                _page(_table()), selected_page_ordinal=2, physical_page=10
            ),
            _page_record(
                historical_page, selected_page_ordinal=3, physical_page=11
            ),
        ],
        compiled_specs=compiled,
    )
    assert cluster["status"] == UNRESOLVED
    assert (
        "MULTIPLE_FAMILY_TABLES_REQUIRE_UNIQUE_PERIOD_OR_ENDPOINT_CONTINUITY"
        in cluster["reasons"]
    )


def test_leading_undated_owner_then_adjacent_continuation_binds_current():
    first = _page(_undated_table())
    second = _page(_undated_table(current_year=2024))
    second["sections"][0]["title_exact"] = "Tài sản cố định hữu hình (tiếp theo)"
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[
            _page_record(_typed_balance_sheet_page(), physical_page=1),
            _page_record(first, selected_page_ordinal=2, physical_page=10),
            _page_record(second, selected_page_ordinal=3, physical_page=11),
        ],
        compiled_specs=_compiled(),
    )
    assert cluster["status"] == READY
    assert cluster["component_regions"][0]["physical_page"] == 10
    assert cluster["component_regions"][0]["period_end_date"] == "2025-12-31"
    assert cluster["control_regions"] == []
    assert next(
        item
        for item in cluster["family_table_inventory"]
        if item["physical_page"] == 11
    )["disposition"] == "SOURCE_ONLY_UNDATED_NONCURRENT_TABLE"


def test_two_undated_full_tables_without_continuation_heading_stay_ambiguous():
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[
            _page_record(_typed_balance_sheet_page(), physical_page=1),
            _page_record(
                _page(_undated_table()), selected_page_ordinal=2, physical_page=10
            ),
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
        "MULTIPLE_FAMILY_TABLES_REQUIRE_UNIQUE_PERIOD_OR_ENDPOINT_CONTINUITY"
        in cluster["reasons"]
    )


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


def test_leased_compiled_policy_declares_nab_roles_and_source_only_carrying_control():
    compiled = _compiled_leased()

    assert compiled["evaluation"]["source_only_carrying_control"] == {
        "control_kind": "COST_MINUS_DEPRECIATION_ENDPOINTS_EXACT_NO_SCHEMA_MAPPING",
        "hierarchy_aliases": ["gia tri con lai"],
    }
    assert {"tang trong ky", "tang trong nam"} <= set(
        compiled["role_aliases"]["COST_LEASED_ADDITION"]
    )
    assert "chuyen sang tai san co dinh huu hinh" in compiled["role_aliases"][
        "COST_BUYOUT"
    ]
    assert "chuyen sang tai san co dinh huu hinh" in compiled["role_aliases"][
        "DEP_BUYOUT"
    ]


@pytest.mark.parametrize(
    ("table_kwargs", "expected_mappings"),
    [
        pytest.param(
            {
                "cost_opening": "156.859",
                "cost_increase_label": None,
                "cost_increase": None,
                "cost_transfer": "(32.200)",
                "cost_ending": "124.659",
                "depreciation_opening": "79.173",
                "depreciation_charge": "23.363",
                "depreciation_transfer": "(28.311)",
                "depreciation_ending": "74.225",
                "carrying_opening": "77.686",
                "carrying_ending": "50.434",
            },
            {
                "COST_OPENING": 156859,
                "COST_BUYOUT": -32200,
                "COST_ENDING": 124659,
                "DEP_OPENING": 79173,
                "DEP_CHARGE": 23363,
                "DEP_BUYOUT": -28311,
                "DEP_ENDING": 74225,
            },
            id="separate-audited-annual",
        ),
        pytest.param(
            {
                "opening_label": "Số dư đầu kỳ",
                "ending_label": "Số dư cuối kỳ",
                "cost_opening": "156.859",
                "cost_increase_label": None,
                "cost_increase": None,
                "cost_transfer": "(8.416)",
                "cost_ending": "148.443",
                "depreciation_opening": "79.173",
                "depreciation_charge_label": "Khấu hao trong kỳ",
                "depreciation_charge": "12.689",
                "depreciation_transfer": "(7.628)",
                "depreciation_ending": "84.234",
                "carrying_opening": "77.686",
                "carrying_ending": "64.209",
            },
            {
                "COST_OPENING": 156859,
                "COST_BUYOUT": -8416,
                "COST_ENDING": 148443,
                "DEP_OPENING": 79173,
                "DEP_CHARGE": 12689,
                "DEP_BUYOUT": -7628,
                "DEP_ENDING": 84234,
            },
            id="separate-reviewed-half-year",
        ),
        pytest.param(
            {},
            {
                "COST_OPENING": 159317,
                "COST_LEASED_ADDITION": 1715,
                "COST_BUYOUT": -32200,
                "COST_ENDING": 128832,
                "DEP_OPENING": 79572,
                "DEP_CHARGE": 23953,
                "DEP_BUYOUT": -28311,
                "DEP_ENDING": 75214,
            },
            id="consolidated-audited-annual",
        ),
        pytest.param(
            {
                "opening_label": "Số dư đầu kỳ",
                "ending_label": "Số dư cuối kỳ",
                "cost_increase_label": "Tăng trong kỳ",
                "cost_increase": "893",
                "cost_transfer": "(8.416)",
                "cost_ending": "151.794",
                "depreciation_charge_label": "Khấu hao trong kỳ",
                "depreciation_charge": "12.944",
                "depreciation_transfer": "(7.628)",
                "depreciation_ending": "84.888",
                "carrying_ending": "66.906",
            },
            {
                "COST_OPENING": 159317,
                "COST_LEASED_ADDITION": 893,
                "COST_BUYOUT": -8416,
                "COST_ENDING": 151794,
                "DEP_OPENING": 79572,
                "DEP_CHARGE": 12944,
                "DEP_BUYOUT": -7628,
                "DEP_ENDING": 84888,
            },
            id="consolidated-reviewed-half-year",
        ),
    ],
)
def test_all_four_nab_single_asset_tables_map_every_visible_schema_role(
    table_kwargs, expected_mappings
):
    compiled = _compiled_leased()
    table = _nab_single_asset_leased_table(**table_kwargs)
    page = _leased_page()
    page["sections"][0]["tables"] = [table]
    table_page = _page_record(page, selected_page_ordinal=2)
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(_typed_income_statement_page(), physical_page=1), table_page],
        compiled_specs=compiled,
    )
    assert cluster["status"] == READY
    classification = cluster["family_table_inventory"][0]["classification"]
    assert classification["total_column_binding_kind"] == (
        "IMPLICIT_SINGLE_RECOGNIZED_ASSET_MONEY_COLUMN"
    )
    assert classification["total_column_ordinals"] == [1]
    receipt = build_gemini_json_fixed_asset_rollforward_region_query_receipt_v1(
        cluster["component_regions"], control_regions=[]
    )
    candidate = evaluate_gemini_json_fixed_asset_rollforward_family_cluster_v1(
        regions=cluster["component_regions"],
        control_regions=[],
        page_json_by_version={table_page["page_json_version_id"]: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    assert candidate["status"] == READY
    assert {
        item["role"]: item["cell"]["coefficient"] for item in candidate["mappings"]
    } == expected_mappings
    source_observation_audit = validate_source_observation_mapping_contract_v1(candidate)
    assert source_observation_audit["status"] == "PASS"
    assert source_observation_audit["mapping_count"] == len(expected_mappings)
    assert source_observation_audit["source_blank_cell_count"] == 0
    assert source_observation_audit["violation_count"] == 0
    seal = candidate["closure_receipt"]["width_seal"]
    assert seal["status"] == "SEALED_EXACT_SINGLE_ASSET_COLUMN_VERTICAL_BINDING"
    assert seal["safety"]["horizontal_equation_skipped_as_vacuous_identity"] is True
    assert all(item["status"] == "EXACT" for item in seal["equation_receipts"])
    control = candidate["closure_receipt"]["table_receipt"][
        "source_only_carrying_control"
    ]
    assert control["mapping_emitted"] is False
    assert [item["role"] for item in control["rows"]] == [
        "SOURCE_ONLY_CARRY_OPENING",
        "SOURCE_ONLY_CARRY_ENDING",
    ]


def test_single_asset_implicit_total_rejects_carrying_control_mismatch():
    compiled = _compiled_leased()
    table = _nab_single_asset_leased_table()
    table["rows"][-1]["values_exact"] = ["53.619"]
    page = _leased_page()
    page["sections"][0]["tables"] = [table]
    table_page = _page_record(page, selected_page_ordinal=2)
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(_typed_income_statement_page(), physical_page=1), table_page],
        compiled_specs=compiled,
    )
    assert cluster["status"] == READY
    receipt = build_gemini_json_fixed_asset_rollforward_region_query_receipt_v1(
        cluster["component_regions"], control_regions=[]
    )
    candidate = evaluate_gemini_json_fixed_asset_rollforward_family_cluster_v1(
        regions=cluster["component_regions"],
        control_regions=[],
        page_json_by_version={table_page["page_json_version_id"]: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "SINGLE_ASSET_COLUMN_VERTICAL_EQUATION_MISMATCH" in candidate["reasons"]


def test_leased_multiple_asset_columns_without_visible_total_fail_closed():
    table = _nab_single_asset_leased_table()
    table["columns"].append(
        {"header_path_exact": ["Thiết bị, dụng cụ quản lý"], "value_kind": "MONEY"}
    )
    for row in table["rows"]:
        row["values_exact"].append(row["values_exact"][0])
    page = _leased_page()
    page["sections"][0]["tables"] = [table]

    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(page)], compiled_specs=_compiled_leased()
    )

    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert "UNIQUE_RIGHT_EDGE_TOTAL_COLUMN_NOT_VISIBLE" in cluster["reasons"]


def test_leased_single_unrecognized_money_column_is_not_an_implicit_total():
    table = _nab_single_asset_leased_table()
    table["columns"][0]["header_path_exact"] = ["Cột không xác định"]
    page = _leased_page()
    page["sections"][0]["tables"] = [table]

    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(page)], compiled_specs=_compiled_leased()
    )

    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert "DISTINCT_ASSET_HEADER_FRONTIER_INCOMPLETE" in cluster["reasons"]


def test_leased_explicit_no_activity_then_intangible_tables_is_not_observed():
    page = _intangible_page(
        tables=[_intangible_table(), _intangible_table(current_year=2024)],
        narratives=[
            "11. Tài sản cố định thuê tài chính: Không phát sinh.",
            "12. Tài sản cố định vô hình",
        ],
    )
    page["sections"][0]["title_exact"] = "THUYẾT MINH BÁO CÁO TÀI CHÍNH"

    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(page)], compiled_specs=_compiled_leased()
    )

    assert cluster["status"] == NOT_OBSERVED
    assert cluster["component_regions"] == []
    assert cluster["reasons"] == []


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


def test_money_normalizer_accepts_only_grouped_integer_zero_decimal_rendering():
    locator = {"column_id": "c1", "row_id": "r1"}
    assert fixed_asset_v1._money(
        "1.117.708.788,00", source_locator=locator
    )["coefficient"] == 1_117_708_788
    assert fixed_asset_v1._money(
        "(1,117,708,788.00)", source_locator=locator
    )["coefficient"] == -1_117_708_788
    for unsupported in ("1.117.708.788,01", "1,117,708,788.01"):
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
    assert len(candidate["mappings"]) == 9
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


def test_investment_property_single_visible_charge_projects_exact_declared_subtotal():
    page = _investment_property_page(tables=[_investment_property_table()])

    _compiled_specs, _cluster, _receipt, _pages, candidate = _investment_candidate(
        [_page_record(page)]
    )

    assert candidate["status"] == READY
    by_role = {item["role"]: item for item in candidate["mappings"]}
    assert by_role["DEP_CHARGE"]["report_norm_id"] == 958
    assert by_role["DEP_CHARGE"]["cell"]["coefficient"] == 6
    assert by_role["DEP_TOTAL_INCREASE"]["report_norm_id"] == 6005
    assert by_role["DEP_TOTAL_INCREASE"]["cell"] == {
        "coefficient": 6,
        "state": "DERIVED_EXACT_SINGLETON_DECLARED_SUBTOTAL",
    }
    assert by_role["DEP_TOTAL_INCREASE"]["source_refs"][0]["cell"]["source_text"] == "6"
    assert by_role["DEP_TOTAL_INCREASE"]["source_refs"][0]["cell"]["state"] == "NUMBER"
    component = candidate["closure_receipt"]["component_population_receipt"]["components"][0]
    assert component["table_receipt"]["singleton_declared_subtotal_receipts"] == [
        {
            "branch_equation_id": "branch:DEPRECIATION_BRANCH",
            "disposition": "DERIVED_EXACT_SINGLETON_DIRECT_CHILD_IS_DECLARED_SUBTOTAL",
            "source_role": "DEP_CHARGE",
            "source_row_id": "r7",
            "subtotal_role": "DEP_TOTAL_INCREASE",
        }
    ]
    assert validate_source_observation_mapping_contract_v1(candidate)["status"] == "PASS"


def test_investment_property_explicit_subtotal_prevents_second_singleton_projection():
    table = _table(subtotal=True)
    table["columns"][1]["header_path_exact"] = [
        "Quyền sử dụng đất có thời hạn",
        "Triệu VND",
    ]
    table["title_exact"] = "Bất động sản đầu tư cho thuê năm 2025"
    page = _investment_property_page(tables=[table])

    _compiled_specs, _cluster, _receipt, _pages, candidate = _investment_candidate(
        [_page_record(page)]
    )

    assert candidate["status"] == READY
    subtotal = next(
        item for item in candidate["mappings"] if item["role"] == "DEP_TOTAL_INCREASE"
    )
    assert subtotal["cell"] == {"coefficient": 6, "state": "NUMBER"}
    assert subtotal["source_refs"][0]["label_exact"] == "Tăng trong kỳ"
    component = candidate["closure_receipt"]["component_population_receipt"]["components"][0]
    assert component["table_receipt"]["singleton_declared_subtotal_receipts"] == []


@pytest.mark.parametrize("mutation", ["BLANK_CHILD_LANE", "BRANCH_MISMATCH"])
def test_investment_property_singleton_subtotal_requires_fully_observed_exact_branch(
    mutation,
):
    table = _investment_property_table()
    charge = next(row for row in table["rows"] if row["label_exact"] == "Khấu hao trong kỳ")
    if mutation == "BLANK_CHILD_LANE":
        charge["values_exact"] = [None, "4", "4"]
    else:
        ending = next(
            row
            for row in table["rows"]
            if row["label_exact"].startswith("Tại ngày 31")
            and row["hierarchy_path_exact"][0] == "Hao mòn lũy kế"
        )
        ending["values_exact"] = ["22", "44", "67"]
    page = _investment_property_page(tables=[table])

    _compiled_specs, _cluster, _receipt, _pages, candidate = _investment_candidate(
        [_page_record(page)]
    )

    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    component = candidate["closure_receipt"]["component_population_receipt"]["components"][0]
    assert component["table_receipt"]["singleton_declared_subtotal_receipts"] == []


def test_singleton_subtotal_config_rejects_one_child_with_multiple_declared_parents():
    paths = (
        "config/families/tm-investment-property-topology-v1.json",
        "config/families/tm-investment-property-evaluation-v1.json",
        "config/families/tm-investment-property-schema-binding-v1.json",
    )
    topology, evaluation, binding = [
        json.loads((ROOT / path).read_bytes()) for path in paths
    ]
    evaluation["singleton_declared_subtotal_projections"].append(
        {"source_role": "DEP_CHARGE", "subtotal_role": "DEP_TOTAL_DECREASE"}
    )

    with pytest.raises(
        GeminiJsonFixedAssetRollforwardFamilyV1Error,
        match="singleton declared-subtotal projection drifted",
    ):
        compile_gemini_json_fixed_asset_rollforward_family_specs_v1(
            topology, evaluation, binding
        )


def test_component_policy_allows_declared_absent_branch_with_single_asset_total():
    table = _investment_property_table()
    table["columns"] = [
        {"header_path_exact": ["Nhà cửa", "Triệu VND"], "value_kind": "MONEY"}
    ]
    table["rows"] = [
        row
        for row in table["rows"]
        if row["hierarchy_path_exact"][0] != "Hao mòn lũy kế"
    ]
    for row in table["rows"]:
        branch = row["hierarchy_path_exact"][0]
        if row["row_kind"] == "GROUP":
            row["values_exact"] = [None]
        elif branch == "Nguyên giá" and row["label_exact"].startswith("Tại ngày 1"):
            row["values_exact"] = ["100"]
        elif branch == "Nguyên giá" and row["label_exact"] == "Mua trong kỳ":
            row["values_exact"] = ["10"]
        elif branch == "Nguyên giá":
            row["values_exact"] = ["110"]
        elif row["label_exact"].startswith("Tại ngày 1"):
            row["values_exact"] = ["100"]
        else:
            row["values_exact"] = ["110"]
    page = _investment_property_page(tables=[table])
    _compiled_specs, cluster, _receipt, _pages, candidate = _investment_candidate(
        [_page_record(page)]
    )
    assert cluster["status"] == READY
    classification = cluster["family_table_inventory"][0]["classification"]
    assert classification["branch_roles"] == ["CARRYING_BRANCH", "COST_BRANCH"]
    assert classification["total_column_binding_kind"] == (
        "IMPLICIT_SINGLE_RECOGNIZED_ASSET_MONEY_COLUMN"
    )
    assert candidate["status"] == READY
    assert {item["role"] for item in candidate["mappings"]} == {
        "COST_OPENING",
        "COST_PURCHASE",
        "COST_ENDING",
        "CARRY_OPENING",
        "CARRY_ENDING",
    }
    equations = candidate["closure_receipt"]["component_population_receipt"]["components"][
        0
    ]["table_receipt"]["equations"]
    assert {item["equation_id"] for item in equations} >= {
        "branch:COST_BRANCH",
        "carrying:CARRY_OPENING",
        "carrying:CARRY_ENDING",
    }


def test_component_policy_does_not_make_required_cost_branch_optional():
    table = _investment_property_table()
    table["rows"] = [
        row for row in table["rows"] if row["hierarchy_path_exact"][0] == "Giá trị còn lại"
    ]
    page = _investment_property_page(tables=[table])
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(page)], compiled_specs=_compiled_investment_property()
    )
    assert cluster["status"] == UNRESOLVED
    assert "CONFIGURED_BRANCH_SEED_FRONTIER_INCOMPLETE" in cluster["reasons"]


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


def test_investment_property_relative_statement_columns_bind_exact_section_endpoint():
    statement = _page_record(_investment_relative_statement_page(), physical_page=1)
    note = _page_record(
        _investment_property_page(tables=[_investment_cost_fragment()]),
        selected_page_ordinal=2,
        physical_page=20,
    )
    _compiled_specs, cluster, _receipt, _pages, candidate = _investment_candidate(
        [statement, note]
    )

    statement_control = next(
        item
        for item in cluster["family_table_inventory"]
        if item["classification"]["component_kind"]
        == "PRIMARY_STATEMENT_CARRYING_CONTROL"
    )
    period_receipt = statement_control["classification"]["period_receipt"]
    assert period_receipt["status"] == (
        "UNIQUE_TYPED_BALANCE_SHEET_RELATIVE_CARRYING_PERIOD_AXIS"
    )
    assert period_receipt["period_end_date"] == "2025-12-31"
    assert [
        (item["period_role"], item["period_date"])
        for item in period_receipt["column_period_bindings"]
    ] == [("CARRY_ENDING", "2025-12-31"), ("CARRY_OPENING", None)]
    assert candidate["status"] == READY
    carrying = {
        item["role"]: item for item in candidate["mappings"] if item["role"].startswith("CARRY_")
    }
    assert carrying["CARRY_OPENING"]["cell"]["coefficient"] == 10
    assert carrying["CARRY_ENDING"]["cell"]["coefficient"] == 15
    assert carrying["CARRY_OPENING"]["source_refs"][0]["column_period_date"] is None
    assert carrying["CARRY_ENDING"]["source_refs"][0]["column_period_date"] == (
        "2025-12-31"
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "MISSING_SECTION_ENDPOINT",
        "CONFLICTING_SECTION_ENDPOINT",
        "MIXED_EXPLICIT_AND_RELATIVE_COLUMNS",
        "DUPLICATE_CURRENT_ROLE",
        "ONE_HEADER_CONTAINS_BOTH_ROLES",
        "THREE_MONEY_COLUMNS",
    ],
)
def test_investment_property_relative_statement_period_axis_fails_closed(mutation):
    statement_page = _investment_relative_statement_page()
    section = statement_page["sections"][0]
    columns = section["tables"][0]["columns"]
    if mutation == "MISSING_SECTION_ENDPOINT":
        section["title_exact"] = "BÁO CÁO TÌNH HÌNH TÀI CHÍNH"
    elif mutation == "CONFLICTING_SECTION_ENDPOINT":
        section["narratives_exact"] = ["Tại ngày 30 tháng 6 năm 2025"]
    elif mutation == "MIXED_EXPLICIT_AND_RELATIVE_COLUMNS":
        columns[0]["header_path_exact"] = ["31/12/2025"]
    elif mutation == "DUPLICATE_CURRENT_ROLE":
        columns[1]["header_path_exact"] = ["Số cuối năm"]
    elif mutation == "ONE_HEADER_CONTAINS_BOTH_ROLES":
        columns[0]["header_path_exact"] = ["Số cuối năm / Số đầu năm"]
    else:
        columns.append({"header_path_exact": ["Khác"], "value_kind": "MONEY"})
        section["tables"][0]["rows"][0]["values_exact"].append("1")
    statement = _page_record(statement_page, physical_page=1)
    note = _page_record(
        _investment_property_page(tables=[_investment_cost_fragment()]),
        selected_page_ordinal=2,
        physical_page=20,
    )
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[statement, note], compiled_specs=_compiled_investment_property()
    )
    assert cluster["status"] == UNRESOLVED
    assert "CARRYING_SUMMARY_CONTROL_STRUCTURE_IS_NOT_AUTHENTICATED" in cluster["reasons"]


def test_investment_property_does_not_capture_intangible_software_variant():
    statement = _page_record(_investment_statement_page(), physical_page=1)
    intangible = _investment_property_table()
    intangible["title_exact"] = None
    intangible["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"
    intangible["columns"][0]["header_path_exact"] = [
        "Quyền sử dụng đất",
        "Triệu VND",
    ]
    intangible["columns"][1]["header_path_exact"] = [
        "Phần mềm máy vi tính",
        "Triệu VND",
    ]
    page = _page(intangible)
    page["sections"][0]["title_exact"] = (
        "Thuyết minh báo cáo tài chính hợp nhất cho năm kết thúc ngày 31 tháng 12 năm 2025"
    )
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[
            statement,
            _page_record(page, selected_page_ordinal=2, physical_page=54),
        ],
        compiled_specs=_compiled_investment_property(),
    )
    assert cluster["status"] == NOT_OBSERVED
    assert cluster["reasons"] == []


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


def _synthetic_authenticated_source_repair_fixture():
    """Build the smallest exact replay fixture without weakening the compiler."""

    compiled = deepcopy(_compiled())
    page = _page()
    page_version_id = "gfpstorev1:json:" + "1" * 64
    table = page["sections"][0]["tables"][0]
    row = table["rows"][2]
    column = table["columns"][0]
    assert row["values_exact"][0] == "10"
    effective_page = deepcopy(page)
    effective_page["sections"][0]["tables"][0]["rows"][2]["values_exact"][0] = "11"
    effective_table = effective_page["sections"][0]["tables"][0]
    repair = {
        "base_page_json_sha256": canonical_json_sha256_v1(page),
        "base_page_json_version_id": page_version_id,
        "cell_repairs": [
            {
                "after_exact": "11",
                "before_exact": "10",
                "cell_id": "r3:c1",
                "column_header_path_exact": deepcopy(column["header_path_exact"]),
                "row_hierarchy_path_exact": deepcopy(row["hierarchy_path_exact"]),
                "row_label_exact": row["label_exact"],
            }
        ],
        "effective_page_json_sha256": canonical_json_sha256_v1(effective_page),
        "repair_id": "gjffasrv1:repair:" + "a" * 64,
        "source_binding": {},
        "table_ref": {
            "base_table_sha256": canonical_json_sha256_v1(table),
            "effective_table_sha256": canonical_json_sha256_v1(effective_table),
            "section_id": "s1",
            "table_id": "t1",
        },
    }
    compiled["source_repair_overlay"] = {
        "overlay_id": "gjffasrv1:overlay:" + "b" * 64,
        "repairs": [repair],
    }
    return compiled, page_version_id, page


def test_registered_authenticated_source_repair_artifact_compiles_exactly():
    compiled = _compiled()
    ref = compiled["source_repair_artifact_ref"]
    overlay = compiled["source_repair_overlay"]
    artifact_bytes = (ROOT / ref["path"]).read_bytes()
    assert len(artifact_bytes) == ref["size_bytes"] == 142430
    assert fixed_asset_v1.sha256(artifact_bytes).hexdigest() == ref["sha256"]
    assert overlay["overlay_id"] == ref["overlay_id"]
    assert len(overlay["repairs"]) == 10
    assert sum(len(item["cell_repairs"]) for item in overlay["repairs"]) == 184
    assert len({item["base_page_json_version_id"] for item in overlay["repairs"]}) == 10


def test_authenticated_source_repair_artifact_outer_bytes_tamper_fails_closed(monkeypatch):
    paths = (
        "config/families/tm-tangible-fixed-assets-topology-v1.json",
        "config/families/tm-tangible-fixed-assets-evaluation-v1.json",
        "config/families/tm-tangible-fixed-assets-schema-binding-v1.json",
    )
    topology, evaluation, binding = [json.loads((ROOT / path).read_bytes()) for path in paths]
    original_read_bytes = Path.read_bytes

    def tampered_read_bytes(path):
        payload = original_read_bytes(path)
        if path.name == "gemini_json_fixed_asset_source_repair_artifact_v1.json":
            return payload + b" "
        return payload

    monkeypatch.setattr(Path, "read_bytes", tampered_read_bytes)
    with pytest.raises(
        GeminiJsonFixedAssetRollforwardFamilyV1Error,
        match="authenticated source-repair artifact bytes drifted",
    ):
        compile_gemini_json_fixed_asset_rollforward_family_specs_v1(
            topology, evaluation, binding
        )


@pytest.mark.parametrize(
    ("tamper", "message"),
    [
        ("image", "source identity does not replay"),
        ("stored_page", "page version does not replay"),
    ],
)
def test_authenticated_source_repair_internal_identity_tamper_fails_with_rehashed_bytes(
    monkeypatch, tamper, message
):
    paths = (
        "config/families/tm-tangible-fixed-assets-topology-v1.json",
        "config/families/tm-tangible-fixed-assets-evaluation-v1.json",
        "config/families/tm-tangible-fixed-assets-schema-binding-v1.json",
    )
    topology, evaluation, binding = [json.loads((ROOT / path).read_bytes()) for path in paths]
    artifact_path = ROOT / evaluation["authenticated_source_repair_artifact_ref"]["path"]
    artifact = json.loads(artifact_path.read_bytes())
    if tamper == "image":
        artifact["repairs"][0]["source_binding"]["image_sha256"] = "0" * 64
    else:
        artifact["repairs"][0]["stored_canonical_json_sha256"] = "0" * 64
    tampered_payload = json.dumps(
        artifact, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    ref = evaluation["authenticated_source_repair_artifact_ref"]
    ref["sha256"] = fixed_asset_v1.sha256(tampered_payload).hexdigest()
    ref["size_bytes"] = len(tampered_payload)
    original_read_bytes = Path.read_bytes

    def tampered_read_bytes(path):
        if path.name == artifact_path.name:
            return tampered_payload
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", tampered_read_bytes)
    with pytest.raises(GeminiJsonFixedAssetRollforwardFamilyV1Error, match=message):
        compile_gemini_json_fixed_asset_rollforward_family_specs_v1(
            topology, evaluation, binding
        )


@pytest.mark.parametrize(
    ("tamper", "message"),
    [
        ("base_page", "base page drifted"),
        ("base_table", "base table drifted"),
        ("before_cell", "cell binding drifted"),
        ("after_cell", "effective table drifted"),
        ("effective_page", "effective page drifted"),
    ],
)
def test_authenticated_source_repair_exact_application_and_tamper_replay(tamper, message):
    compiled, page_version_id, page = _synthetic_authenticated_source_repair_fixture()
    input_page = deepcopy(page)
    if tamper == "base_page":
        input_page["sections"][0]["title_exact"] += " drift"
    elif tamper == "base_table":
        compiled["source_repair_overlay"]["repairs"][0]["table_ref"][
            "base_table_sha256"
        ] = "0" * 64
    elif tamper == "before_cell":
        compiled["source_repair_overlay"]["repairs"][0]["cell_repairs"][0][
            "before_exact"
        ] = "9"
    elif tamper == "after_cell":
        compiled["source_repair_overlay"]["repairs"][0]["cell_repairs"][0][
            "after_exact"
        ] = "12"
    elif tamper == "effective_page":
        compiled["source_repair_overlay"]["repairs"][0][
            "effective_page_json_sha256"
        ] = "0" * 64
    with pytest.raises(GeminiJsonFixedAssetRollforwardFamilyV1Error, match=message):
        fixed_asset_v1._apply_authenticated_source_repair_artifact_v1(
            page_json_by_version={page_version_id: input_page},
            compiled_specs=compiled,
        )


def test_authenticated_source_repair_replays_to_clone_without_mutating_selected_json():
    compiled, page_version_id, page = _synthetic_authenticated_source_repair_fixture()
    effective, receipts = fixed_asset_v1._apply_authenticated_source_repair_artifact_v1(
        page_json_by_version={page_version_id: page},
        compiled_specs=compiled,
    )
    assert page["sections"][0]["tables"][0]["rows"][2]["values_exact"][0] == "10"
    assert effective[page_version_id]["sections"][0]["tables"][0]["rows"][2][
        "values_exact"
    ][0] == "11"
    assert receipts[0]["status"] == "AUTHENTICATED_PDF_VISIBLE_CELLS_TRANSCRIBED"
    assert receipts[0]["cell_axis_sha256"] == canonical_json_sha256_v1(
        compiled["source_repair_overlay"]["repairs"][0]["cell_repairs"]
    )


def test_immediately_preceding_sibling_table_period_is_exact_and_local():
    compiled = _compiled()
    preceding = {
        "columns": [{"header_path_exact": ["Khoản mục"], "value_kind": "TEXT"}],
        "continuation": "NONE",
        "rows": [
            {
                "hierarchy_path_exact": ["Tại ngày 31/12/2025"],
                "label_exact": "Tại ngày 31/12/2025",
                "row_kind": "ITEM",
                "values_exact": ["Ngày báo cáo"],
            }
        ],
        "title_exact": "Thông tin ngày báo cáo",
        "unit_exact": None,
    }
    current = _undated_table()
    current_section = {
        "content_kind": "FINANCIAL_NOTE",
        "narratives_exact": [],
        "statement_type": "NOT_APPLICABLE",
        "tables": [current],
        "title_exact": "Tài sản cố định hữu hình",
    }
    page = _page()
    page["sections"] = [
        {
            "content_kind": "FINANCIAL_NOTE",
            "narratives_exact": [],
            "statement_type": "NOT_APPLICABLE",
            "tables": [preceding],
            "title_exact": "Thông tin chung",
        },
        current_section,
    ]
    projected, receipt = fixed_asset_v1._project_immediately_preceding_table_period(
        current,
        section=current_section,
        page_json=page,
        page_json_version_id="gfpstorev1:json:" + "1" * 64,
        physical_page=35,
        section_ordinal=2,
        table_ordinal=1,
        compiled_specs=compiled,
    )
    assert receipt["period_end_date"] == "2025-12-31"
    assert receipt["preceding_section_id"] == "s1"
    assert receipt["preceding_table_id"] == "t1"
    assert projected["__immediately_preceding_table_period_receipt"] == receipt
    period = fixed_asset_v1._table_period_receipt(
        current_section, projected, compiled_specs=compiled
    )
    assert period["status"] == "UNIQUE_IMMEDIATELY_PRECEDING_TABLE_PERIOD_END_DATE"
    assert period["period_end_date"] == "2025-12-31"


def test_nonadjacent_or_ambiguous_sibling_date_never_propagates():
    compiled = _compiled()
    current = _undated_table()
    current_section = {
        "content_kind": "FINANCIAL_NOTE",
        "narratives_exact": [],
        "statement_type": "NOT_APPLICABLE",
        "tables": [current],
        "title_exact": "Tài sản cố định hữu hình",
    }
    dated_row = lambda value: {
        "hierarchy_path_exact": [value],
        "label_exact": value,
        "row_kind": "ITEM",
        "values_exact": ["x"],
    }
    preceding = {
        "columns": [{"header_path_exact": ["Khoản mục"], "value_kind": "TEXT"}],
        "continuation": "NONE",
        "rows": [dated_row("Tại ngày 30/06/2025"), dated_row("Tại ngày 31/12/2025")],
        "title_exact": "Hai ngày",
        "unit_exact": None,
    }
    page = _page()
    page["sections"] = [
        {
            "content_kind": "FINANCIAL_NOTE",
            "narratives_exact": [],
            "statement_type": "NOT_APPLICABLE",
            "tables": [preceding],
            "title_exact": "Thông tin chung",
        },
        current_section,
    ]
    projected, receipt = fixed_asset_v1._project_immediately_preceding_table_period(
        current,
        section=current_section,
        page_json=page,
        page_json_version_id="gfpstorev1:json:" + "1" * 64,
        physical_page=35,
        section_ordinal=2,
        table_ordinal=1,
        compiled_specs=compiled,
    )
    assert receipt is None
    assert "__immediately_preceding_table_period_receipt" not in projected


def test_ssb_abbreviated_sibling_fixed_asset_owner_is_a_structural_reset_for_components():
    paths = (
        "config/families/tm-investment-property-topology-v1.json",
        "config/families/tm-investment-property-evaluation-v1.json",
        "config/families/tm-investment-property-schema-binding-v1.json",
    )
    topology, evaluation, binding = [json.loads((ROOT / path).read_bytes()) for path in paths]
    topology["structural_reset_aliases"] += [
        "TSCĐ hữu hình",
        "TSCĐ vô hình",
        "TSCĐ thuê tài chính",
    ]
    compiled = compile_gemini_json_fixed_asset_rollforward_family_specs_v1(
        topology, evaluation, binding
    )
    page = _investment_property_page(
        tables=[_investment_property_table()], narratives=["15. TSCĐ hữu hình"]
    )
    cluster = coalesce_gemini_json_fixed_asset_rollforward_document_v1(
        page_records=[_page_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == UNRESOLVED
    assert "STRUCTURAL_RESET_HEADING_INSIDE_COMPONENT_OWNER_SCOPE" in cluster["reasons"]


def test_f20_single_asset_period_columns_select_exact_current_source_column_only():
    table = _intangible_table()
    table["columns"] = [
        {
            "header_path_exact": ["Phần mềm", "31/12/2024", "Triệu VND"],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": ["Phần mềm", "31/12/2025", "Triệu VND"],
            "value_kind": "MONEY",
        },
    ]
    expected_current = {}
    for source_ordinal, row in enumerate(table["rows"], start=1):
        if row["row_kind"] == "GROUP":
            row["values_exact"] = [None, None]
            continue
        current = row["values_exact"][-1]
        expected_current[source_ordinal] = int(current)
        row["values_exact"] = [str(900_000 + source_ordinal), current]
    page = _intangible_page(tables=[table])
    page["sections"][0]["title_exact"] = (
        "Tài sản cố định vô hình tại ngày 31/12/2025"
    )
    source_page = deepcopy(page)

    _compiled_specs, cluster, _receipt, candidate = _intangible_candidate(page)

    classification = cluster["family_table_inventory"][0]["classification"]
    assert classification["total_column_binding_kind"] == (
        "IMPLICIT_SINGLE_RECOGNIZED_ASSET_CURRENT_PERIOD_COLUMN"
    )
    assert classification["total_column_ordinals"] == [2]
    period_binding = classification["period_receipt"][
        "single_asset_period_column_receipt"
    ]
    assert period_binding["source_values_mutated"] is False
    assert candidate["status"] == READY
    assert all(
        mapping["source_refs"][0]["cell"]["source_locator"]["column_id"] == "c2"
        for mapping in candidate["mappings"]
    )
    assert page == source_page
    assert all(
        mapping["cell"]["coefficient"]
        == expected_current[
            int(mapping["source_refs"][0]["cell"]["source_locator"]["row_id"][1:])
        ]
        for mapping in candidate["mappings"]
    )


def test_f20_contextual_short_supplemental_alias_requires_family_asset_header():
    compiled = _compiled_intangible()
    disclosure = compiled["evaluation"]["supplemental_disclosure_roles"][0]
    row = {
        "hierarchy_path_exact": ["Đã khấu hao hết nhưng vẫn còn sử dụng"],
        "label_exact": "Đã khấu hao hết nhưng vẫn còn sử dụng",
        "row_kind": "ITEM",
        "values_exact": ["1", "2", "3"],
    }

    assert fixed_asset_v1._supplemental_row_matches(
        row,
        disclosure,
        table=_intangible_table(),
        compiled_specs=compiled,
    )
    assert not fixed_asset_v1._supplemental_row_matches(
        row,
        disclosure,
        table=_table(),
        compiled_specs=compiled,
    )


def test_f20_balance_sheet_date_dominates_stale_other_statement_date():
    balance_sheet = _page_record(_typed_balance_sheet_page(), physical_page=1)
    cash_flow_page = _typed_income_statement_page("30 tháng 6 năm 2025")
    cash_flow_page["sections"][0]["statement_type"] = "CASH_FLOW"
    cash_flow = _page_record(cash_flow_page, selected_page_ordinal=2, physical_page=2)

    receipt = fixed_asset_v1._document_reporting_date_receipt([balance_sheet, cash_flow])

    assert receipt["status"] == (
        "UNIQUE_TYPED_BALANCE_SHEET_DATE_DOMINATES_OTHER_STATEMENT_TYPES"
    )
    assert receipt["current_date"] == "2025-12-31"
    assert receipt["comparative_date"] == "2024-12-31"


def test_f20_missing_local_unit_uses_independent_display_rounding_intervals():
    compiled = _compiled_intangible()
    table = _intangible_table()
    table["unit_exact"] = None
    for column in table["columns"]:
        column["header_path_exact"] = [column["header_path_exact"][0]]
    section = _intangible_page(tables=[table])["sections"][0]
    classification = fixed_asset_v1.classify_gemini_json_fixed_asset_rollforward_table_v1(
        section, table, compiled_specs=compiled
    )
    local_unit_axis = fixed_asset_v1._unit_axis(table, compiled_specs=compiled)
    statement = _typed_balance_sheet_page()
    statement_table = statement["sections"][0]["tables"][0]
    statement_table["unit_exact"] = "VND"
    statement_table["rows"] = [
        _row(
            "Tài sản cố định vô hình",
            "Tài sản cố định vô hình",
            ["264.000.400", "239.999.600"],
            path=["Tài sản cố định vô hình"],
        )
    ]

    resolved = fixed_asset_v1._resolve_missing_local_unit_from_balance_sheet_owner_vector(
        table=table,
        classification=classification,
        local_unit_axis=local_unit_axis,
        page_json_by_version={"gfpstorev1:json:" + "8" * 64: statement},
        compiled_specs=compiled,
    )

    assert resolved["complete"] is True
    assert resolved["canonical_unit"] == "MILLION_VND"
    assert resolved["cross_control_receipt"]["status"] == (
        "UNIQUE_LOCAL_UNIT_WITHIN_INDEPENDENT_DISPLAY_ROUNDING_INTERVAL"
    )
    assert resolved["cross_control_receipt"]["matches"][0][
        "base_value_deltas"
    ] == [-400, 400]


def test_f20_blank_subtotal_heading_promotes_visible_children_without_imputation():
    table = _intangible_table(subtotal=True)
    table["rows"] = [
        row
        for row in table["rows"]
        if not (
            row["row_kind"] == "SUBTOTAL"
            and row["label_exact"] == "Tăng trong kỳ"
        )
    ]
    page = _intangible_page(tables=[table])

    _compiled_specs, _cluster, _receipt, candidate = _intangible_candidate(page)

    assert candidate["status"] == READY
    table_receipt = candidate["closure_receipt"]["table_receipt"]
    assert table_receipt["blank_subtotal_heading_receipts"]
    assert {mapping["role"] for mapping in candidate["mappings"]} >= {
        "COST_PURCHASE",
        "COST_OTHER_INCREASE",
        "DEP_CHARGE",
        "DEP_OTHER_INCREASE",
    }
    assert all(mapping["cell"]["state"] != "BLANK" for mapping in candidate["mappings"])


def test_f20_visible_subtotal_owns_same_role_flattened_child_without_double_count():
    table = _intangible_table(subtotal=True)
    cost_subtotal = next(
        row
        for row in table["rows"]
        if row["row_kind"] == "SUBTOTAL"
        and row["hierarchy_path_exact"][0] == "Nguyên giá"
    )
    cost_subtotal["label_exact"] = "Số tăng trong kỳ"
    cost_subtotal["hierarchy_path_exact"] = ["Nguyên giá", "Số tăng trong kỳ"]
    duplicate = next(
        row
        for row in table["rows"]
        if row["label_exact"] == "Mua trong kỳ"
        and row["hierarchy_path_exact"][0] == "Nguyên giá"
    )
    duplicate["label_exact"] = "- Tăng trong kỳ"
    duplicate["hierarchy_path_exact"] = [
        "Nguyên giá",
        "Số tăng trong kỳ",
        "- Tăng trong kỳ",
    ]
    duplicate["values_exact"] = list(cost_subtotal["values_exact"])
    table["rows"] = [
        row
        for row in table["rows"]
        if not (
            row["label_exact"] == "Tăng khác"
            and row["hierarchy_path_exact"][0] == "Nguyên giá"
        )
    ]
    page = _intangible_page(tables=[table])

    _compiled_specs, _cluster, _receipt, candidate = _intangible_candidate(page)

    assert candidate["status"] == READY
    mapping = next(
        item for item in candidate["mappings"] if item["role"] == "COST_TOTAL_INCREASE"
    )
    assert mapping["cell"]["coefficient"] == 30
    assert mapping["row_id"] == "r3"
    assert [source["row_id"] for source in mapping["source_refs"]] == ["r3"]
    receipts = candidate["closure_receipt"]["table_receipt"][
        "same_role_subtotal_child_receipts"
    ]
    assert receipts == [
        {
            "disposition": "SOURCE_ONLY_CHILD_CORROBORATES_VISIBLE_SUBTOTAL",
            "row_id": "r4",
            "subtotal_role": "COST_TOTAL_INCREASE",
            "subtotal_row_id": "r3",
        }
    ]
