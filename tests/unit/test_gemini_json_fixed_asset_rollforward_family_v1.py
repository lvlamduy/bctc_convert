from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

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
