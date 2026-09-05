from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation import gemini_json_government_sbv_liabilities_family_v1 as subject
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
PAGE_1 = "gfpstorev1:json:" + "1" * 64
PAGE_2 = "gfpstorev1:json:" + "2" * 64
DOCUMENT_ID = "gfpstorev1:document:" + "3" * 64
SOURCE_SHA256 = "4" * 64


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_text())


def _empty_repairs() -> dict:
    return _json(
        "data/registered/gemini_json_government_sbv_liabilities_source_repairs_v1.json"
    )


def _compiled() -> dict:
    return subject.compile_gemini_json_government_sbv_liabilities_family_specs_v1(
        _json("config/families/tm-government-sbv-liabilities-topology-v1.json"),
        _json("config/families/tm-government-sbv-liabilities-evaluation-v1.json"),
        _json("config/families/tm-government-sbv-liabilities-schema-binding-v1.json"),
        _empty_repairs(),
    )


def _adjacent_fixture() -> tuple[dict, list[dict], dict[str, dict], dict, dict]:
    owner_table = {
        "columns": [
            {"header_path_exact": ["Cuối kỳ"], "value_kind": "MONEY"},
            {"header_path_exact": ["Đầu kỳ"], "value_kind": "MONEY"},
        ],
        "continuation": "CONTINUES_ON_NEXT_PAGE",
        "rows": [{"label_exact": None, "row_kind": "UNKNOWN", "values_exact": [None, None]}],
        "title_exact": "14. Các khoản nợ chính phủ và NHNN",
        "unit_exact": None,
    }
    target_table = {
        "columns": [
            {"header_path_exact": [None], "value_kind": "MONEY"},
            {"header_path_exact": [None], "value_kind": "MONEY"},
        ],
        "continuation": "CONTINUES_FROM_PREVIOUS_PAGE",
        "rows": [
            {"label_exact": "Vay NHNN", "row_kind": "GROUP", "values_exact": ["7", "3"]},
            {
                "label_exact": "Tiền gửi của KBNN",
                "row_kind": "GROUP",
                "values_exact": ["-", "-"],
            },
            {"label_exact": "Tổng", "row_kind": "TOTAL", "values_exact": ["7", "3"]},
        ],
        "title_exact": None,
        "unit_exact": None,
    }
    pages = {
        PAGE_1: {
            "sections": [
                {"narrative_exact": None, "tables": [owner_table], "title_exact": None}
            ],
            "status": "FINANCIAL_NOTE_CONTENT",
        },
        PAGE_2: {
            "sections": [
                {"narrative_exact": None, "tables": [target_table], "title_exact": None}
            ],
            "status": "FINANCIAL_NOTE_CONTENT",
        },
    }
    base = {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }
    selected_pages = [
        {
            **base,
            "page_json_version_id": PAGE_1,
            "physical_page": 10,
            "selected_page_ordinal": 1,
        },
        {
            **base,
            "page_json_version_id": PAGE_2,
            "physical_page": 11,
            "selected_page_ordinal": 2,
        },
    ]
    owner_classification = {
        "owner_visible": True,
        "role_hits": [],
        "total_rows": [],
        "unbound_money_row_ordinals": [],
    }
    target_classification = {
        "ambiguous_rows": [],
        "context_roles": [],
        "family_presence_anchor_visible": True,
        "owner_visible": False,
        "role_hits": [
            {"role": "CENTRAL_BANK_LOAN", "row_kind": "GROUP", "row_ordinal": 1},
            {
                "role": "TREASURY_PAYMENT_DEPOSIT",
                "row_kind": "GROUP",
                "row_ordinal": 2,
            },
        ],
        "total_rows": [{"row_kind": "TOTAL", "row_ordinal": 3, "source_order": 3}],
        "typed_control_disposition": None,
        "unbound_money_row_ordinals": [3],
    }
    cluster = {
        **base,
        "declared_money_table_inventory": [
            {
                "classification": owner_classification,
                "page_json_version_id": PAGE_1,
                "physical_page": 10,
                "position": [10, 1, 1],
                "section_id": "s1",
                "table_id": "t1",
            },
            {
                "classification": target_classification,
                "page_json_version_id": PAGE_2,
                "physical_page": 11,
                "position": [11, 1, 1],
                "section_id": "s1",
                "table_id": "t1",
            },
        ],
        "reasons": ["COMPLETE_OWNER_CLUSTER_NOT_RESOLVED"],
    }
    owner_period = subject._two_period_axis(owner_table)
    unit_context = {
        "owner_row_evidence": [
            {
                "canonical_unit": "MILLION_VND",
                "coefficients": [7, 3],
                "magnitude_power10": 6,
                "period_axis_complete": True,
                "period_signatures": owner_period["signatures"],
            }
        ]
    }
    return cluster, selected_pages, pages, _compiled(), unit_context


def _recover(
    cluster: dict, selected_pages: list[dict], pages: dict[str, dict], compiled: dict, unit: dict
):
    return subject._adjacent_owner_continuation_receipt_v1(
        cluster=cluster,
        selected_page_axis=selected_pages,
        page_json_by_version=pages,
        compiled_specs=compiled,
        document_unit_context=unit,
    )


def _primary_root_fixture() -> tuple[dict, dict[str, dict], dict]:
    table = {
        "columns": [
            {"header_path_exact": ["Thuyết minh"], "value_kind": "TEXT"},
            {"header_path_exact": ["Cuối kỳ"], "value_kind": "MONEY"},
            {"header_path_exact": ["Đầu kỳ"], "value_kind": "MONEY"},
        ],
        "continuation": "CONTINUES_FROM_PREVIOUS_PAGE",
        "rows": [
            {
                "hierarchy_path_exact": ["NỢ PHẢI TRẢ"],
                "label_exact": "NỢ PHẢI TRẢ",
                "row_kind": "GROUP",
                "values_exact": [None, None, None],
            },
            {
                "hierarchy_path_exact": [
                    "NỢ PHẢI TRẢ",
                    "Các khoản nợ Chính phủ và Ngân hàng Nhà nước",
                ],
                "label_exact": "I. Các khoản nợ Chính phủ và Ngân hàng Nhà nước",
                "row_kind": "ITEM",
                "values_exact": [None, "7", "3"],
            },
            {
                "hierarchy_path_exact": ["NỢ PHẢI TRẢ", "Tiền gửi khách hàng"],
                "label_exact": "Tiền gửi khách hàng",
                "row_kind": "ITEM",
                "values_exact": [None, "100", "90"],
            },
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    pages = {
        PAGE_1: {
            "completion": "COMPLETE",
            "sections": [
                {
                    "content_kind": "PRIMARY_STATEMENT",
                    "narratives_exact": [],
                    "statement_type": "BALANCE_SHEET",
                    "tables": [table],
                    "title_exact": "Báo cáo tình hình tài chính",
                }
            ],
            "status": "PRIMARY_FINANCIAL_STATEMENT",
        }
    }
    region = {
        "component_roles": [],
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "fragment_ordinal": 1,
        "page_json_version_id": PAGE_1,
        "physical_page": 4,
        "section_id": "s1",
        "selected_page_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
        "table_id": "t1",
    }
    return region, pages, _compiled()


def test_exact_adjacent_owner_continuation_receipt_closes() -> None:
    fixture = _adjacent_fixture()
    region, receipt = _recover(*fixture)
    assert region["page_json_version_id"] == PAGE_2
    assert receipt["owner_locator"]["physical_page"] == 10
    assert receipt["target_locator"]["physical_page"] == 11
    assert receipt["intervening_reset_surface_axis"] == []


def test_adjacent_receipt_rejects_mismatched_owner() -> None:
    cluster, selected_pages, pages, compiled, unit = _adjacent_fixture()
    pages[PAGE_1]["sections"][0]["tables"][0]["title_exact"] = "14. Phải trả khác"
    assert _recover(cluster, selected_pages, pages, compiled, unit) is None


def test_adjacent_receipt_rejects_nonadjacent_page() -> None:
    cluster, selected_pages, pages, compiled, unit = _adjacent_fixture()
    selected_pages[1]["physical_page"] = 12
    cluster["declared_money_table_inventory"][1]["physical_page"] = 12
    cluster["declared_money_table_inventory"][1]["position"][0] = 12
    assert _recover(cluster, selected_pages, pages, compiled, unit) is None


def test_adjacent_receipt_rejects_intervening_reset_table() -> None:
    cluster, selected_pages, pages, compiled, unit = _adjacent_fixture()
    target = pages[PAGE_2]["sections"][0]["tables"][0]
    pages[PAGE_2]["sections"][0]["tables"] = [
        {
            "columns": [],
            "continuation": "NONE",
            "rows": [],
            "title_exact": "15. Tiền gửi và vay các TCTD khác",
            "unit_exact": None,
        },
        target,
    ]
    inventory = cluster["declared_money_table_inventory"][1]
    inventory["position"] = [11, 1, 2]
    inventory["table_id"] = "t2"
    assert _recover(cluster, selected_pages, pages, compiled, unit) is None


def test_owner_total_match_does_not_turn_null_into_zero() -> None:
    assert subject._coefficient(None) is None
    candidate = {
        "mappings": [
            {
                "report_norm_id": "RNID1",
                "role": "UNAUTHENTICATED_BLANK",
                "source_refs": [],
                "values": [
                    {"coefficient": 7, "source_text": "7", "state": "PARSED_INTEGER"},
                    {
                        "coefficient": 0,
                        "source_text": None,
                        "state": "INFERRED_BLANK_ZERO_IF_EQUATION_EXACT",
                    },
                ],
            },
            {
                "report_norm_id": "RNID2",
                "role": "VISIBLE_TOTAL",
                "source_refs": [],
                "values": [
                    {"coefficient": 7, "source_text": "7", "state": "PARSED_INTEGER"},
                    {"coefficient": 3, "source_text": "3", "state": "PARSED_INTEGER"},
                ],
            },
        ],
        "reasons": [],
        "status": subject.READY,
    }
    filtered, omissions = subject._drop_unauthenticated_null_derived_mappings(candidate)
    assert [mapping["role"] for mapping in filtered["mappings"]] == ["VISIBLE_TOTAL"]
    assert omissions[0]["role"] == "UNAUTHENTICATED_BLANK"

    regions = [
        {
            "page_json_version_id": PAGE_1,
            "physical_page": 1,
            "section_id": "s1",
            "table_id": "t1",
        }
    ]
    pages = {
        PAGE_1: {
            "sections": [
                {
                    "tables": [
                        {
                            "columns": [
                                {"value_kind": "MONEY"},
                                {"value_kind": "MONEY"},
                            ],
                            "rows": [
                                {
                                    "label_exact": "Tổng",
                                    "row_kind": "TOTAL",
                                    "values_exact": ["7", None],
                                }
                            ],
                        }
                    ]
                }
            ]
        }
    }
    raw = {
        "closure_receipt": {
            "document_unit_context": {
                "owner_row_evidence": [
                    {
                        "canonical_unit": "MILLION_VND",
                        "coefficients": [7, 0],
                        "period_axis_complete": True,
                    }
                ]
            }
        }
    }
    overlaid_pages, receipt = subject._prepare_dash_overlay(
        raw_candidate=raw,
        regions=regions,
        page_json_by_version=pages,
        compiled_specs=_compiled(),
    )
    assert receipt is None
    assert overlaid_pages[PAGE_1]["sections"][0]["tables"][0]["rows"][0][
        "values_exact"
    ] == ["7", None]


def test_visible_child_sum_can_materialize_absent_structural_and_family_roots() -> None:
    compiled = _compiled()
    candidate = {
        "mappings": [
            {
                "item_mapping_id": "fixture",
                "report_norm_id": compiled["bindings"]["DISCOUNT_LOAN"],
                "role": "DISCOUNT_LOAN",
                "row_id": "r1",
                "source_refs": [
                    {
                        "locator": {
                            "page_json_version_id": PAGE_1,
                            "section_id": "s1",
                            "table_id": "t1",
                        },
                        "row_id": "r1",
                    }
                ],
                "state": "DIRECT_SOURCE_ROW",
                "unit": "MILLION_VND",
                "values": [
                    {"coefficient": 7, "source_text": "7", "state": "PARSED_INTEGER"},
                    {"coefficient": 3, "source_text": "3", "state": "PARSED_INTEGER"},
                ],
            }
        ]
    }
    corrections = subject._overlay_mapping_value_corrections(
        candidate,
        overlay_receipt={"repaired_total_coefficients": [7, 3]},
        compiled_specs=compiled,
    )
    mappings = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert set(mappings) == {
        "CENTRAL_BANK_LOAN",
        "DISCOUNT_LOAN",
        "FAMILY_ROOT_TOTAL",
    }
    assert [value["coefficient"] for value in mappings["CENTRAL_BANK_LOAN"]["values"]] == [
        7,
        3,
    ]
    assert [value["coefficient"] for value in mappings["FAMILY_ROOT_TOTAL"]["values"]] == [
        7,
        3,
    ]
    assert all(
        value["source_text"] is None
        and value["state"].startswith("DERIVED_EXACT_")
        for role in ("CENTRAL_BANK_LOAN", "FAMILY_ROOT_TOTAL")
        for value in mappings[role]["values"]
    )
    assert {correction["role"] for correction in corrections} == {
        "CENTRAL_BANK_LOAN",
        "FAMILY_ROOT_TOTAL",
    }


def test_exact_primary_statement_root_projects_and_restores_source_row() -> None:
    region, pages, compiled = _primary_root_fixture()
    projected = subject._primary_statement_exact_root_projection_v1(
        region=region,
        page_json_by_version=pages,
        compiled_specs=compiled,
    )
    assert projected is not None
    projected_pages, receipt = projected
    table = projected_pages[PAGE_1]["sections"][0]["tables"][0]
    assert len(table["rows"]) == 1
    assert table["rows"][0]["row_kind"] == "TOTAL"
    assert receipt["root_row"]["row_ordinal"] == 2

    query_receipt = subject.build_gemini_json_government_sbv_liabilities_region_query_receipt_v1(
        [region]
    )
    candidate = subject.evaluate_gemini_json_government_sbv_liabilities_family_cluster_v1(
        regions=[region],
        page_json_by_version=pages,
        compiled_specs=compiled,
        query_receipt=query_receipt,
    )
    assert candidate["status"] == subject.READY
    assert [mapping["role"] for mapping in candidate["mappings"]] == [
        "FAMILY_ROOT_TOTAL"
    ]
    mapping = candidate["mappings"][0]
    assert [value["coefficient"] for value in mapping["values"]] == [7, 3]
    assert {ref["row_ordinal"] for ref in mapping["source_refs"]} == {2}
    assert {ref["row_kind"] for ref in mapping["source_refs"]} == {"ITEM"}
    assert (
        candidate["closure_receipt"]["government_sbv_liabilities_adapter_receipt"][
            "primary_root_projection_receipt"
        ]["primary_root_query_receipt_id"]
        == receipt["primary_root_query_receipt_id"]
    )


def test_primary_statement_projection_rejects_ambiguous_or_combined_rows() -> None:
    region, pages, compiled = _primary_root_fixture()
    root = pages[PAGE_1]["sections"][0]["tables"][0]["rows"][1]
    pages[PAGE_1]["sections"][0]["tables"][0]["rows"].append(copy.deepcopy(root))
    assert (
        subject._primary_statement_exact_root_projection_v1(
            region=region,
            page_json_by_version=pages,
            compiled_specs=compiled,
        )
        is None
    )
    pages[PAGE_1]["sections"][0]["tables"][0]["rows"] = [
        {
            **root,
            "hierarchy_path_exact": ["Tiền gửi và vay NHNN và các TCTD khác"],
            "label_exact": "Tiền gửi và vay NHNN và các TCTD khác",
        }
    ]
    assert (
        subject._primary_statement_exact_root_projection_v1(
            region=region,
            page_json_by_version=pages,
            compiled_specs=compiled,
        )
        is None
    )


def test_primary_statement_projection_receipt_detects_source_shape_tamper() -> None:
    region, pages, compiled = _primary_root_fixture()
    projected = subject._primary_statement_exact_root_projection_v1(
        region=region,
        page_json_by_version=pages,
        compiled_specs=compiled,
    )
    assert projected is not None
    _projected_pages, receipt = projected
    pages[PAGE_1]["sections"][0]["tables"][0]["rows"][1]["row_kind"] = "GROUP"
    with pytest.raises(
        subject.GeminiJsonGovernmentSbvLiabilitiesFamilyV1Error,
        match="source shape drifted",
    ):
        subject._apply_primary_root_projection_receipt_v1(
            page_json_by_version=pages,
            receipt=receipt,
        )


def test_query_recovery_requires_one_classifier_proved_primary_root() -> None:
    region, pages, compiled = _primary_root_fixture()
    cluster = {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
        "status": "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY",
        "declared_money_table_inventory": [
            {
                "classification": {
                    "ambiguous_rows": [],
                    "family_root_row_ordinals": [2],
                    "money_column_ordinals": [2, 3],
                    "typed_control_disposition": "PRIMARY_FINANCIAL_STATEMENT_SUMMARY",
                },
                "page_json_version_id": PAGE_1,
                "physical_page": 4,
                "section_id": "s1",
                "table_id": "t1",
            }
        ],
    }
    selected_pages = [
        {
            key: region[key]
            for key in (
                "document_id",
                "document_ordinal",
                "page_json_version_id",
                "physical_page",
                "selected_page_ordinal",
                "source_logical_name",
                "source_sha256",
            )
        }
    ]
    recovered = subject._primary_statement_exact_root_query_recovery_v1(
        cluster=cluster,
        selected_page_axis=selected_pages,
        page_json_by_version=pages,
        compiled_specs=compiled,
    )
    assert recovered is not None
    recovered_region, receipt = recovered
    assert recovered_region == region
    assert receipt["root_row"]["row_ordinal"] == 2

    cluster["declared_money_table_inventory"].append(
        copy.deepcopy(cluster["declared_money_table_inventory"][0])
    )
    assert (
        subject._primary_statement_exact_root_query_recovery_v1(
            cluster=cluster,
            selected_page_axis=selected_pages,
            page_json_by_version=pages,
            compiled_specs=compiled,
        )
        is None
    )


def test_direct_root_loan_children_get_scoped_without_value_changes() -> None:
    compiled = _compiled()
    owner = "15. Các khoản nợ Chính phủ và Ngân hàng Nhà nước"
    table = {
        "columns": [
            {"header_path_exact": ["Cuối kỳ"], "value_kind": "MONEY"},
            {"header_path_exact": ["Đầu kỳ"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            {
                "hierarchy_path_exact": [owner, "Vay chiết khấu các giấy tờ có giá"],
                "label_exact": "Vay chiết khấu các giấy tờ có giá",
                "row_kind": "ITEM",
                "values_exact": ["70", "30"],
            },
            {
                "hierarchy_path_exact": [owner, "Vay theo hồ sơ tín dụng"],
                "label_exact": "Vay theo hồ sơ tín dụng",
                "row_kind": "ITEM",
                "values_exact": ["20", "10"],
            },
            {
                "hierarchy_path_exact": [owner, "Khác"],
                "label_exact": "Khác",
                "row_kind": "ITEM",
                "values_exact": ["10", "5"],
            },
            {
                "hierarchy_path_exact": [owner, None],
                "label_exact": None,
                "row_kind": "TOTAL",
                "values_exact": ["100", "45"],
            },
        ],
        "title_exact": owner,
        "unit_exact": "Triệu đồng",
    }
    pages = {
        PAGE_1: {
            "completion": "COMPLETE",
            "sections": [
                {
                    "content_kind": "FINANCIAL_NOTE",
                    "narratives_exact": [],
                    "statement_type": "NOT_APPLICABLE",
                    "tables": [table],
                    "title_exact": owner,
                }
            ],
            "status": "FINANCIAL_NOTE_CONTENT",
        }
    }
    region = {
        "component_roles": ["CENTRAL_BANK_LOAN", "DISCOUNT_LOAN"],
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "fragment_ordinal": 1,
        "page_json_version_id": PAGE_1,
        "physical_page": 15,
        "section_id": "s1",
        "selected_page_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
        "table_id": "t1",
    }
    projected = subject._direct_root_central_child_projection_v1(
        region=region,
        page_json_by_version=pages,
        compiled_specs=compiled,
    )
    assert projected is not None
    projected_pages, receipt = projected
    assert receipt["region_component_roles"]["after"] == [
        "CENTRAL_BANK_LOAN",
        "CREDIT_FILE_LOAN",
        "DISCOUNT_LOAN",
        "OTHER_LOAN",
    ]
    assert projected_pages[PAGE_1]["sections"][0]["tables"][0]["rows"][1][
        "values_exact"
    ] == ["20", "10"]

    query_receipt = subject.build_gemini_json_government_sbv_liabilities_region_query_receipt_v1(
        [region]
    )
    candidate = subject.evaluate_gemini_json_government_sbv_liabilities_family_cluster_v1(
        regions=[region],
        page_json_by_version=pages,
        compiled_specs=compiled,
        query_receipt=query_receipt,
    )
    assert candidate["status"] == subject.READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "CENTRAL_BANK_LOAN",
        "CREDIT_FILE_LOAN",
        "DISCOUNT_LOAN",
        "OTHER_LOAN",
        "FAMILY_ROOT_TOTAL",
    }
    assert candidate["component_regions"] == [region]
    assert candidate["closure_receipt"]["query_receipt"] == query_receipt
    assert all(
        "Vay NHNN" not in source_ref["hierarchy_path_exact"]
        for mapping in candidate["mappings"]
        for source_ref in mapping["source_refs"]
    )


def test_direct_root_child_projection_rejects_unmappable_sibling() -> None:
    region, pages, compiled = _primary_root_fixture()
    pages[PAGE_1]["status"] = "FINANCIAL_NOTE_CONTENT"
    section = pages[PAGE_1]["sections"][0]
    section["content_kind"] = "FINANCIAL_NOTE"
    section["statement_type"] = "NOT_APPLICABLE"
    section["title_exact"] = "Các khoản nợ Chính phủ và NHNN"
    table = section["tables"][0]
    table["title_exact"] = "Các khoản nợ Chính phủ và NHNN"
    table["rows"] = [
        {
            "hierarchy_path_exact": [
                "Các khoản nợ Chính phủ và NHNN",
                "Khoản không xác định",
            ],
            "label_exact": "Khoản không xác định",
            "row_kind": "ITEM",
            "values_exact": [None, "7", "3"],
        },
        {
            "hierarchy_path_exact": [
                "Các khoản nợ Chính phủ và NHNN",
                "Vay theo hồ sơ tín dụng",
            ],
            "label_exact": "Vay theo hồ sơ tín dụng",
            "row_kind": "ITEM",
            "values_exact": [None, "7", "3"],
        },
    ]
    assert (
        subject._direct_root_central_child_projection_v1(
            region=region,
            page_json_by_version=pages,
            compiled_specs=compiled,
        )
        is None
    )
def test_same_document_repair_outside_selected_region_is_not_applied() -> None:
    region, pages, compiled = _primary_root_fixture()
    compiled["government_sbv_liabilities_source_repairs"] = [
        {
            "after_exact": "-",
            "before_exact": None,
            "locator": {
                "column_ordinal": 2,
                "page_json_version_id": PAGE_2,
                "physical_page": 5,
                "row_ordinal": 1,
                "section_id": "s1",
                "table_id": "t1",
            },
            "source": {
                "source_logical_name": "fixture.pdf",
                "source_sha256": SOURCE_SHA256,
                "source_size_bytes": 100,
            },
        }
    ]
    unchanged, applied = subject._apply_authenticated_source_repairs(
        regions=[region],
        page_json_by_version=pages,
        compiled_specs=compiled,
    )
    assert applied == []
    assert unchanged == pages


def test_source_repair_identity_tamper_fails_closed() -> None:
    spec = _empty_repairs()
    repair = {
        "after_exact": "-",
        "before_exact": None,
        "crop_evidence": {
            "bbox_pixels_xyxy": [1, 2, 11, 12],
            "pixel_height": 10,
            "pixel_width": 10,
            "rgb_sha256": "5" * 64,
        },
        "locator": {
            "column_ordinal": 2,
            "page_json_version_id": PAGE_2,
            "physical_page": 11,
            "row_ordinal": 1,
            "section_id": "s1",
            "table_id": "t1",
        },
        "observed_pdf_glyph": "-",
        "repair_kind": "MONEY_CELL_VISIBLE_DASH",
        "render": {
            "image_sha256": "6" * 64,
            "image_size_bytes": 100,
            "media_type": "image/png",
            "physical_page": 11,
            "pixel_height": 20,
            "pixel_width": 20,
            "render_dpi": 300,
            "render_receipt_sha256": "7" * 64,
        },
        "source": {
            "source_logical_name": "fixture.pdf",
            "source_sha256": SOURCE_SHA256,
            "source_size_bytes": 100,
        },
    }
    material = copy.deepcopy(repair)
    repair["repair_id"] = "gjslfav1:source-repair:" + canonical_json_sha256_v1(material)
    spec["repairs"] = [repair]
    spec["repair_axis_sha256"] = canonical_json_sha256_v1(spec["repairs"])
    assert subject._validate_source_repairs(spec) == [repair]
    spec["repairs"][0]["crop_evidence"]["rgb_sha256"] = "8" * 64
    spec["repair_axis_sha256"] = canonical_json_sha256_v1(spec["repairs"])
    with pytest.raises(
        subject.GeminiJsonGovernmentSbvLiabilitiesFamilyV1Error,
        match="identity drifted",
    ):
        subject._validate_source_repairs(spec)
