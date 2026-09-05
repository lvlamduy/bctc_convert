from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    GeminiJsonMultitableHierarchicalFamilyV1Error,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
    validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    validate_source_observation_mapping_contract_v1,
)

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "a" * 64
VERSION_ID = "gfpstorev1:json:" + "b" * 64
SOURCE_SHA256 = "c" * 64
OWNER = "Tiền và các khoản tương đương tiền"


def _json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict[str, Any]:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-cash-equivalents-topology-v1.json"),
        _json("tm-cash-equivalents-evaluation-v1.json"),
        _json("tm-cash-equivalents-schema-binding-v1.json"),
    )


def _row(
    label: str | None,
    current: str | None,
    comparative: str | None,
    *,
    kind: str = "ITEM",
    hierarchy: list[str | None] | None = None,
) -> dict[str, Any]:
    return {
        "hierarchy_path_exact": (
            ([] if label is None else [label]) if hierarchy is None else hierarchy
        ),
        "label_exact": label,
        "row_kind": kind,
        "values_exact": [current, comparative],
    }


def _combined_rows(*, extra: bool = False) -> list[dict[str, Any]]:
    rows = [
        _row("Tiền mặt, vàng bạc, đá quý", "10", "9"),
        _row("Tiền gửi tại NHNN", "20", "18"),
        _row(
            "Tiền gửi tại các TCTD khác (gồm tiền gửi không kỳ hạn và "
            "tiền gửi có kỳ hạn không quá ba tháng)",
            "30",
            "27",
        ),
    ]
    if extra:
        rows.append(_row("Khoản tiền khác không được khai báo", "1", "1"))
    rows.append(_row(None, "60" if not extra else "61", "54" if not extra else "55", kind="TOTAL"))
    return rows


def _split_rows(*, blank_security: bool = False) -> list[dict[str, Any]]:
    parent = "Tiền gửi tại các TCTD khác"
    rows = [
        _row("Tiền mặt, vàng", "10", "9"),
        _row("Tiền gửi tại Ngân hàng Nhà nước", "20", "18"),
        _row(parent, "30", "27", kind="GROUP"),
        _row("- Không kỳ hạn", "10", "9", hierarchy=[parent, "- Không kỳ hạn"]),
        _row(
            "- Có kỳ hạn không quá 3 tháng",
            "20",
            "18",
            hierarchy=[parent, "- Có kỳ hạn không quá 3 tháng"],
        ),
    ]
    if blank_security:
        rows.append(
            _row(
                "Chứng khoán có thời hạn thu hồi hoặc đáo hạn không quá 3 tháng kể từ ngày mua",
                None,
                "4",
            )
        )
    rows.append(
        _row(
            None,
            "60",
            "58" if blank_security else "54",
            kind="TOTAL",
        )
    )
    return rows


def _table(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "columns": [
            {"header_path_exact": ["31/12/2025", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["31/12/2024", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": rows,
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }


def _page(
    rows: list[dict[str, Any]],
    *,
    owner: str | None = OWNER,
    tables: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": tables if tables is not None else [_table(rows)],
                "title_exact": owner,
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _primary_cash_flow_page(
    *,
    include_declared_subtree: bool = True,
    group_kind: str = "GROUP",
    root_kind: str = "TOTAL",
    root_current: str = "60",
    unknown_child: bool = False,
) -> dict[str, Any]:
    root_label = "VII TIỀN VÀ CÁC KHOẢN TƯƠNG ĐƯƠNG TIỀN TẠI NGÀY 31 THÁNG 12"
    group_label = "Tiền và các khoản tương đương tiền gồm có:"
    rows = [
        _row("IV LƯU CHUYỂN TIỀN THUẦN TRONG KỲ", "5", "4", kind="SUBTOTAL"),
        _row(
            "V TIỀN VÀ CÁC KHOẢN TƯƠNG ĐƯƠNG TIỀN TẠI NGÀY 1 THÁNG 1",
            "55",
            "50",
        ),
        _row(root_label, root_current, "54", kind=root_kind, hierarchy=[root_label]),
    ]
    if include_declared_subtree:
        rows.extend(
            [
                _row(
                    group_label,
                    None,
                    None,
                    kind=group_kind,
                    hierarchy=[root_label, group_label],
                ),
                _row(
                    "- Tiền mặt, vàng bạc, đá quý",
                    "10",
                    "9",
                    hierarchy=[root_label, group_label, "- Tiền mặt, vàng bạc, đá quý"],
                ),
                _row(
                    "- Tiền gửi thanh toán tại Ngân hàng Nhà nước",
                    "20",
                    "18",
                    hierarchy=[
                        root_label,
                        group_label,
                        "- Tiền gửi thanh toán tại Ngân hàng Nhà nước",
                    ],
                ),
                _row(
                    "- Tiền gửi tại các tổ chức tín dụng khác",
                    "30",
                    "27",
                    hierarchy=[
                        root_label,
                        group_label,
                        "- Tiền gửi tại các tổ chức tín dụng khác",
                    ],
                ),
            ]
        )
        if unknown_child:
            rows.insert(
                -1,
                _row(
                    "- Khoản tiền không thuộc frontier đã khai báo",
                    "1",
                    "1",
                    hierarchy=[
                        root_label,
                        group_label,
                        "- Khoản tiền không thuộc frontier đã khai báo",
                    ],
                ),
            )
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "PRIMARY_STATEMENT",
                "narratives_exact": [],
                "statement_type": "CASH_FLOW",
                "tables": [_table(rows)],
                "title_exact": "BÁO CÁO LƯU CHUYỂN TIỀN TỆ",
            }
        ],
        "status": "PRIMARY_FINANCIAL_STATEMENT",
    }


def _record(page: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": VERSION_ID,
        "physical_page": 1,
        "selected_page_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }


def _evaluate(page: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    compiled = _compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        cluster["component_regions"]
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    return candidate, cluster, receipt


def test_cash_equivalents_config_binds_complete_schema_without_prompt_logic() -> None:
    compiled = _compiled()
    assert compiled["topology"]["family_id"] == "CASH_EQUIVALENTS"
    assert compiled["schema"]["family_root_report_norm_id"] == 1248
    assert compiled["bindings"] == {
        "CASH": 1249,
        "CENTRAL_BANK": 1250,
        "INTERBANK_GENERAL": 1251,
        "INTERBANK_DEMAND": 1252,
        "INTERBANK_TERM": 1253,
        "SECURITIES": 1254,
    }


def test_combined_interbank_and_unlabelled_total_close_exactly() -> None:
    page = _page(_combined_rows())
    candidate, cluster, receipt = _evaluate(page)
    assert candidate["status"] == READY
    assert [(item["role"], item["report_norm_id"]) for item in candidate["mappings"]] == [
        ("CASH", 1249),
        ("CENTRAL_BANK", 1250),
        ("INTERBANK_GENERAL", 1251),
        ("FAMILY_ROOT_TOTAL", 1248),
    ]
    assert len(candidate["closure_receipt"]["equations"]) == 1
    validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
        candidate,
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=_compiled(),
        query_receipt=receipt,
    )


def test_split_interbank_maps_parent_and_children_without_double_counting() -> None:
    candidate, _cluster, _receipt = _evaluate(_page(_split_rows()))
    assert candidate["status"] == READY
    assert {item["role"] for item in candidate["mappings"]} == {
        "CASH",
        "CENTRAL_BANK",
        "INTERBANK_GENERAL",
        "INTERBANK_DEMAND",
        "INTERBANK_TERM",
        "FAMILY_ROOT_TOTAL",
    }
    assert len(candidate["closure_receipt"]["equations"]) == 2


def test_matching_owner_total_never_promotes_blank_security_to_zero() -> None:
    candidate, _cluster, _receipt = _evaluate(_page(_split_rows(blank_security=True)))
    assert candidate["status"] == UNRESOLVED
    assert candidate["reasons"] == ["REQUIRED_SOURCE_VISIBLE_EXACT_FAMILY_ROOT_NOT_PROVEN"]
    assert candidate["mappings"] == []
    assert "INFERRED_BLANK_ZERO" not in json.dumps(candidate, ensure_ascii=False)
    assert validate_source_observation_mapping_contract_v1(candidate)["status"] == "PASS"


def test_cash_flow_balance_only_surface_is_not_a_detailed_family() -> None:
    page = _primary_cash_flow_page(include_declared_subtree=False)
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == NOT_OBSERVED
    assert cluster["component_regions"] == []


def test_primary_cash_flow_explicit_family_subtree_is_accepted_without_prompt_logic() -> None:
    page = _primary_cash_flow_page()
    candidate, cluster, _receipt = _evaluate(page)
    assert cluster["status"] == READY
    assert candidate["status"] == READY
    assert [(item["role"], item["report_norm_id"]) for item in candidate["mappings"]] == [
        ("CASH", 1249),
        ("CENTRAL_BANK", 1250),
        ("INTERBANK_GENERAL", 1251),
        ("FAMILY_ROOT_TOTAL", 1248),
    ]
    table_receipt = candidate["closure_receipt"]["table_receipts"][0]
    assert table_receipt["classification"]["primary_statement_family_root_subtree_receipts"] == [
        {
            "declared_child_roles": ["CASH", "CENTRAL_BANK", "INTERBANK_GENERAL"],
            "declared_child_row_ordinals": [5, 6, 7],
            "family_group_row_ordinal": 4,
            "source_result_row_ordinal": 3,
            "rule": (
                "EXACT_PARENT_GROUP_DIRECTLY_UNDER_VISIBLE_SOURCE_TOTAL_WITH_"
                "COMPLETE_DECLARED_CHILD_FRONTIER"
            ),
        }
    ]


def test_primary_cash_flow_explicit_subtree_equation_mismatch_is_unresolved() -> None:
    candidate, cluster, _receipt = _evaluate(_primary_cash_flow_page(root_current="61"))
    assert cluster["status"] == READY
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_primary_cash_flow_generic_item_row_kinds_still_use_source_graph() -> None:
    candidate, cluster, _receipt = _evaluate(
        _primary_cash_flow_page(group_kind="ITEM", root_kind="ITEM")
    )
    assert cluster["status"] == READY
    assert candidate["status"] == READY
    assert {item["role"] for item in candidate["mappings"]} == {
        "CASH",
        "CENTRAL_BANK",
        "INTERBANK_GENERAL",
        "FAMILY_ROOT_TOTAL",
    }


def test_primary_cash_flow_unmapped_child_inside_authenticated_group_is_unresolved() -> None:
    candidate, cluster, _receipt = _evaluate(
        _primary_cash_flow_page(root_current="61", unknown_child=True)
    )
    assert cluster["status"] == READY
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "UNMAPPED_DIRECT_FAMILY_SOURCE_MONEY_ROW" in candidate["reasons"]


def test_unknown_direct_money_row_under_owner_fails_closed() -> None:
    candidate, _cluster, _receipt = _evaluate(_page(_combined_rows(extra=True)))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "UNMAPPED_DIRECT_FAMILY_SOURCE_MONEY_ROW" in candidate["reasons"]


def test_duplicate_complete_tables_are_unresolved() -> None:
    page = _page(
        [],
        tables=[_table(_combined_rows()), _table(deepcopy(_combined_rows()))],
    )
    candidate, cluster, _receipt = _evaluate(page)
    assert len(cluster["component_regions"]) == 2
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "DUPLICATE_COMPLETE_SOURCE_TABLE_POPULATION" in candidate["reasons"]


def test_candidate_replay_rejects_coherent_mapping_drift() -> None:
    page = _page(_combined_rows())
    candidate, cluster, receipt = _evaluate(page)
    forged = deepcopy(candidate)
    forged["mappings"][0]["values"][0]["coefficient"] += 1
    forged.pop("candidate_id")
    with pytest.raises(GeminiJsonMultitableHierarchicalFamilyV1Error):
        validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
            forged,
            regions=cluster["component_regions"],
            page_json_by_version={VERSION_ID: page},
            compiled_specs=_compiled(),
            query_receipt=receipt,
        )
