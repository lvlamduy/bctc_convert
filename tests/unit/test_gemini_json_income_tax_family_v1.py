from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from bctc_ai.evaluation.gemini_json_income_tax_family_v1 import (
    GeminiJsonIncomeTaxFamilyV1Error,
    build_gemini_json_income_tax_region_query_receipt_v1,
    compile_gemini_json_income_tax_family_specs_v1,
    evaluate_gemini_json_income_tax_family_cluster_v1,
    recover_gemini_json_income_tax_query_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    GeminiJsonMultitableHierarchicalFamilyV1Error,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    classify_gemini_json_multitable_hierarchical_table_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
    validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "a" * 64
VERSION_ID = "gfpstorev1:json:" + "b" * 64
SOURCE_SHA256 = "c" * 64
OWNER = "Chi phí thuế thu nhập doanh nghiệp"


def _json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict[str, Any]:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-income-tax-topology-v1.json"),
        _json("tm-income-tax-evaluation-v1.json"),
        _json("tm-income-tax-schema-binding-v1.json"),
    )


def _adapter_compiled() -> dict[str, Any]:
    return compile_gemini_json_income_tax_family_specs_v1(
        _json("tm-income-tax-topology-v1.json"),
        _json("tm-income-tax-evaluation-v1.json"),
        _json("tm-income-tax-schema-binding-v1.json"),
    )


def _collapsed_current_tax_row() -> dict[str, Any]:
    return {
        "hierarchy_path_exact": [
            "Chi phí thuế TNDN ghi nhận trong báo cáo kết quả hoạt động riêng giữa niên độ:",
            "Chi phí thuế TNDN - hiện hành",
        ],
        "label_exact": (
            "Chi phí thuế TNDN ghi nhận trong báo cáo\n"
            "kết quả hoạt động riêng giữa niên độ:\n"
            "Chi phí thuế TNDN - hiện hành"
        ),
        "row_kind": "ITEM",
        "values_exact": ["20\n20", "15\n15"],
    }


def _repaired_current_tax_row() -> dict[str, Any]:
    return {
        "hierarchy_path_exact": [
            "Chi phí thuế TNDN ghi nhận trong báo cáo kết quả hoạt động riêng giữa niên độ:",
            "Chi phí thuế TNDN - hiện hành",
        ],
        "label_exact": "Chi phí thuế TNDN - hiện hành",
        "row_kind": "ITEM",
        "values_exact": ["20", "15"],
    }


def _adapter_compiled_with_fixture_row_repair() -> dict[str, Any]:
    repair = {
        "after_exact": _repaired_current_tax_row(),
        "before_exact": _collapsed_current_tax_row(),
        "locator": {
            "page_json_version_id": VERSION_ID,
            "physical_page": 1,
            "row_ordinal": 6,
            "section_id": "s1",
            "table_id": "t1",
        },
        "pdf_source": {
            "logical_name": "fixture.pdf",
            "sha256": SOURCE_SHA256,
            "size_bytes": 1,
        },
        "repair_kind": "ROW_PDF_VISIBLE_EXACT",
        "visual_evidence": {
            "crop_bbox_pixels": [0, 0, 1, 1],
            "crop_rgb_sha256": "d" * 64,
            "page_render": {
                "height_pixels": 1,
                "sha256": "e" * 64,
                "width_pixels": 1,
            },
        },
    }
    repair["repair_id"] = "gjitfav1:repair:" + canonical_json_sha256_v1(repair)
    return compile_gemini_json_income_tax_family_specs_v1(
        _json("tm-income-tax-topology-v1.json"),
        _json("tm-income-tax-evaluation-v1.json"),
        _json("tm-income-tax-schema-binding-v1.json"),
        source_repair_spec={
            "family_id": "INCOME_TAX",
            "format_version": "INCOME_TAX_AUTHENTICATED_SOURCE_REPAIR_SPEC_V1",
            "render_contract": {
                "alpha": False,
                "colorspace": "RGB",
                "format": "PNG",
                "matrix": [2, 2],
                "renderer": "PyMuPDF",
            },
            "repairs": [repair],
        },
    )


def _row(
    label: str | None,
    current: str | None,
    comparative: str | None,
    *,
    kind: str = "ITEM",
) -> dict[str, Any]:
    return {
        "hierarchy_path_exact": [] if label is None else [label],
        "label_exact": label,
        "row_kind": kind,
        "values_exact": [current, comparative],
    }


def _canonical_rows() -> list[dict[str, Any]]:
    return [
        _row("Tổng lợi nhuận kế toán trước thuế", "100", "80"),
        _row("Điều chỉnh khác", "(10)", "(8)"),
        _row("Lợi nhuận trước thuế của Ngân hàng mẹ", "90", "72"),
        _row("Chi phí không được khấu trừ", "5", "3"),
        _row("Thu nhập chịu thuế", "95", "75"),
        _row("Thuế suất thuế TNDN", "20%", "20%"),
        _row("Chi phí thuế TNDN hiện hành ước tính của Ngân hàng mẹ", "19", "15"),
        _row("Thuế TNDN của chi nhánh nước ngoài", "1", None),
        _row("Chi phí thuế TNDN trong kỳ", "20", "15"),
        _row("Chi phí thuế TNDN hiện hành", "20", "15"),
        _row("Điều chỉnh khác", "1", "2"),
    ]


def _table(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "columns": [
            {"header_path_exact": ["Năm 2026", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Năm 2025", "Triệu đồng"], "value_kind": "MONEY"},
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


def _primary_page(
    rows: list[dict[str, Any]],
    *,
    unit: str | None = "Triệu đồng",
) -> dict[str, Any]:
    table = {
        "columns": [
            {"header_path_exact": ["Quý IV năm 2026"], "value_kind": "MONEY"},
            {"header_path_exact": ["Quý IV năm 2025"], "value_kind": "MONEY"},
            {
                "header_path_exact": ["Lũy kế từ đầu năm", "Năm 2026"],
                "value_kind": "MONEY",
            },
            {
                "header_path_exact": ["Lũy kế từ đầu năm", "Năm 2025"],
                "value_kind": "MONEY",
            },
        ],
        "continuation": "NONE",
        "rows": rows,
        "title_exact": None,
        "unit_exact": unit,
    }
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "PRIMARY_STATEMENT",
                "narratives_exact": [],
                "statement_type": "INCOME_STATEMENT",
                "tables": [table],
                "title_exact": "Báo cáo kết quả hoạt động kinh doanh",
            }
        ],
        "status": "PRIMARY_FINANCIAL_STATEMENT",
    }


def _primary_unit_control_page(*, statement_type: str, unit: str) -> dict[str, Any]:
    page = _primary_page([_row("Chỉ tiêu ngoài phạm vi thuế", "1", "2")], unit=unit)
    page["sections"][0]["statement_type"] = statement_type
    page["sections"][0]["title_exact"] = f"Báo cáo {statement_type}"
    return page


def _primary_record(
    page: dict[str, Any],
    *,
    page_json_version_id: str = VERSION_ID,
    physical_page: int = 5,
    selected_page_ordinal: int = 2,
) -> dict[str, Any]:
    return {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": page_json_version_id,
        "physical_page": physical_page,
        "selected_page_ordinal": selected_page_ordinal,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }


def _primary_tax_rows(
    *,
    current: tuple[str | None, str | None] = ("10", "20"),
    deferred: tuple[str | None, str | None] = ("30", "40"),
    root: tuple[str | None, str | None] = ("40", "60"),
) -> list[dict[str, Any]]:
    return [
        {
            **_row("Chi phí thuế TNDN hiện hành", "1", "2"),
            "values_exact": ["1", "2", *current],
        },
        {
            **_row("Chi phí thuế TNDN hoãn lại", "3", "4"),
            "values_exact": ["3", "4", *deferred],
        },
        {
            **_row("Chi phí thuế TNDN", "4", "6", kind="TOTAL"),
            "values_exact": ["4", "6", *root],
        },
    ]


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


def test_income_tax_config_binds_schema_and_generic_stage_policy() -> None:
    compiled = _compiled()
    assert compiled["topology"]["family_id"] == "INCOME_TAX"
    assert compiled["schema"]["family_root_report_norm_id"] == 5727
    assert set(compiled["bindings"].values()) == set(range(5723, 5738)) - {5727}
    assert compiled["accepted_value_column_kinds"] == ["MONEY", "UNKNOWN"]
    adapter_compiled = _adapter_compiled()
    assert adapter_compiled["income_tax_adapter_spec"][
        "primary_duplicate_presentation_policy"
    ] == (
        "EVIDENCE_FRONTIER_DOMINANT_PRESENTATION_THEN_UNIQUE_VND_WITH_EXACT_"
        "COMMON_ROLE_ECONOMIC_COMPATIBILITY"
    )
    assert compiled["duration_header_path_scope_policy"] == (
        "DISTINCT_SUFFIX_AFTER_EXACT_COMMON_PREFIX"
    )
    assert "STATUTORY_TAX_AMOUNT_SOURCE_ONLY" in compiled["validation_only_roles"]
    assert compiled["topology"]["required_role_combinations"] == [
        ["PROFIT_BEFORE_TAX", "TAXABLE_INCOME"],
        [
            "PROFIT_BEFORE_TAX",
            "STATUTORY_TAX_AMOUNT_SOURCE_ONLY",
            "CURRENT_TAX_PARENT",
        ],
        ["PROFIT_BEFORE_TAX", "CURRENT_TAX_AT_RATE", "CURRENT_TAX_PARENT"],
    ]
    unit_bindings = _json("tm-income-tax-evaluation-v1.json")["money_unit_bindings"]
    vnd = next(item for item in unit_bindings if item["canonical_unit"] == "VND")
    assert vnd == {
        "accepted": True,
        "aliases": ["VND", "Đồng", "Đơn vị tính: VND"],
        "canonical_unit": "VND",
        "magnitude_power10": 0,
    }
    assert [item["scope_id"] for item in compiled["ordered_role_scopes"]] == [
        "TAXABLE_INCOME_RECONCILIATION",
        "CURRENT_TAX_EXPENSE",
    ]


def test_item_typed_results_stages_percentage_and_blank_close_locally() -> None:
    page = _page(_canonical_rows())
    candidate, cluster, receipt = _evaluate(page)
    assert candidate["status"] == READY
    assert {mapping["report_norm_id"] for mapping in candidate["mappings"]} == {
        5723,
        5728,
        5729,
        5730,
        5731,
        5732,
        5734,
    }
    table_receipt = candidate["closure_receipt"]["table_receipts"][0]
    assert len(table_receipt["non_money_metric_source_rows"]) == 1
    assert {
        item["row_ordinal"]
        for item in table_receipt["classification"]["outside_ordered_role_scope_rows"]
    } == {10, 11}
    assert len(candidate["closure_receipt"]["equations"]) == 2
    non_taxable = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "NON_TAXABLE_AGGREGATE"
    )
    assert non_taxable["row_id"] == "r2"
    assert non_taxable["state"] == (
        "SOURCE_VALIDATION_ROLE_PROJECTED_TO_MAPPED_ROLE_AFTER_ORDERED_STAGE_EXACT_EQUATION_CLOSURE"
    )
    assert table_receipt["ordered_role_scope_projection_receipts"] == [
        {
            "projected_source_refs": non_taxable["source_refs"],
            "rule": (
                "VALIDATION_ROLE_PROJECTS_TO_DECLARED_MAPPED_AGGREGATE_ONLY_"
                "INSIDE_ONE_ORDERED_STAGE_AFTER_EXACT_EQUATION_CONSUMPTION"
            ),
            "scope_id": "TAXABLE_INCOME_RECONCILIATION",
            "source_role": "SOURCE_ONLY_EQUATION_COMPONENT",
            "target_role": "NON_TAXABLE_AGGREGATE",
        }
    ]
    foreign = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "FOREIGN_BRANCH_TAX"
    )
    assert foreign["state"] == "PARTIAL_SOURCE_OBSERVATION"
    assert [value["coefficient"] for value in foreign["values"]] == [1, None]
    assert [value["source_text"] for value in foreign["values"]] == ["1", None]
    assert [value["state"] for value in foreign["values"]] == [
        "RAW_SIGNED_INTEGER",
        "BLANK_SOURCE_CELL",
    ]
    validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
        candidate,
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=_compiled(),
        query_receipt=receipt,
    )


def test_unique_required_role_table_supplies_generic_owner_fallback() -> None:
    page = _page(_canonical_rows(), owner=None)
    candidate, cluster, _receipt = _evaluate(page)
    assert candidate["status"] == READY
    assert cluster["owner_receipt"]["alias"] == "DECLARED_REQUIRED_ROLE_TABLE"


def test_duplicate_complete_role_tables_without_owner_are_unresolved() -> None:
    page = _page(
        [],
        owner=None,
        tables=[_table(_canonical_rows()), _table(deepcopy(_canonical_rows()))],
    )
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []


def test_incomplete_role_population_without_owner_is_not_observed() -> None:
    page = _page(
        [
            _row("Lợi nhuận trước thuế", "100", "80"),
            _row("Chi phí thuế thu nhập doanh nghiệp hiện hành", "20", "16"),
        ],
        owner=None,
    )
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] != READY
    assert cluster["component_regions"] == []


def test_bvb_variant_uses_first_exact_taxable_subtotal_without_double_mapping() -> None:
    page = _page(
        [
            _row("Tổng lợi nhuận/(lỗ) kế toán trước thuế", "100", "80"),
            _row("Chi phí không được trừ khi xác định thu nhập chịu thuế", "10", "8"),
            _row("Thu nhập/(lỗ) chịu thuế ước tính trong kỳ", "110", "88", kind="SUBTOTAL"),
            _row("Lỗ năm trước chuyển sang", "-", "-"),
            _row("Thu nhập/(lỗ) chịu thuế ước tính trong kỳ", "110", "88", kind="SUBTOTAL"),
            _row("Thuế TNDN theo thuế suất quy định (20%)", "22", "18"),
            _row("Chi phí thuế TNDN hiện hành trong kỳ", "22", "18", kind="TOTAL"),
        ],
        owner="28. Chi phí thuế thu nhập\nChi phí thuế thu nhập doanh nghiệp hiện hành",
    )
    candidate, _cluster, _receipt = _evaluate(page)
    taxable = [item for item in candidate["mappings"] if item["role"] == "TAXABLE_INCOME"]
    assert [
        (item["row_id"], [value["coefficient"] for value in item["values"]]) for item in taxable
    ] == [("r3", [110, 88])]
    classification = candidate["closure_receipt"]["table_receipts"][0]["classification"]
    assert classification["outside_ordered_role_scope_rows"] == [
        {
            "original_role": "TAXABLE_INCOME",
            "row_ordinal": 5,
            "scope_ids": ["TAXABLE_INCOME_RECONCILIATION"],
            "rule": "DECLARED_ROLE_OUTSIDE_ALL_ORDERED_SOURCE_STAGES_RETAINED_SOURCE_ONLY",
        }
    ]


def test_bare_tax_owner_accepts_statutory_amount_only_as_validation_evidence() -> None:
    page = _page(
        [
            _row("Tổng lợi nhuận/(lỗ) kế toán trước thuế", "100", "80"),
            _row("Thuế tính ở thuế suất 20%", "20", "16"),
            _row("Chi phí thuế TNDN trong kỳ", "20", "16", kind="TOTAL"),
        ],
        owner="30 THUẾ TNDN",
    )
    candidate, _cluster, _receipt = _evaluate(page)
    assert candidate["status"] == READY
    assert {item["role"] for item in candidate["mappings"]} == {
        "PROFIT_BEFORE_TAX",
        "CURRENT_TAX_PARENT",
    }
    source_only = candidate["closure_receipt"]["table_receipts"][0]["source_only_rows"]
    statutory = next(item for item in source_only if item["row_ordinal"] == 2)
    assert statutory["declared_validation_role"] == "STATUTORY_TAX_AMOUNT_SOURCE_ONLY"
    assert statutory["source_ref"]["money_column_ordinals"] == [1, 2]


def test_rate_reconciliation_without_taxable_income_uses_exact_visible_roles() -> None:
    page = _page(
        [
            _row("Tổng lợi nhuận trước thuế", "100", "80"),
            _row("Thuế TNDN theo thuế suất áp dụng cho Ngân hàng (20%)", "20", "16"),
            _row("Chi phí không được khấu trừ", "1", "2"),
            _row("Tổng chi phí thuế TNDN ước tính trong kỳ", "21", "18", kind="TOTAL"),
        ],
        owner="b. Đối chiếu thuế suất thực tế",
    )
    candidate, _cluster, _receipt = _evaluate(page)
    assert candidate["status"] == READY
    assert [item["role"] for item in candidate["mappings"]] == [
        "PROFIT_BEFORE_TAX",
        "NON_DEDUCTIBLE_EXPENSE",
        "CURRENT_TAX_AT_RATE",
        "CURRENT_TAX_PARENT",
    ]
    assert [
        [value["coefficient"] for value in item["values"]] for item in candidate["mappings"]
    ] == [[100, 80], [1, 2], [20, 16], [21, 18]]


def test_bare_other_row_is_not_a_non_taxable_alias() -> None:
    page = _page(
        [
            _row("Lợi nhuận trước thuế", "100", "80"),
            _row("Khác", "10", "8"),
            _row("Thu nhập chịu thuế", "110", "88", kind="SUBTOTAL"),
        ]
    )
    candidate, _cluster, _receipt = _evaluate(page)
    assert candidate["status"] == READY
    assert "NON_TAXABLE_AGGREGATE" not in {item["role"] for item in candidate["mappings"]}
    source_only = candidate["closure_receipt"]["table_receipts"][0]["source_only_rows"]
    other = next(item for item in source_only if item["row_ordinal"] == 2)
    assert other["declared_role"] is None


def test_explicit_vnd_is_accepted_without_scaling() -> None:
    page = _page(
        [
            _row("Lợi nhuận trước thuế thu nhập doanh nghiệp", "100000000", "80000000"),
            _row("Thu nhập tính thuế", "100000000", "80000000", kind="SUBTOTAL"),
        ]
    )
    table = page["sections"][0]["tables"][0]
    table["unit_exact"] = "Đơn vị tính: VND"
    table["columns"][0]["header_path_exact"] = ["Kỳ này", "VND"]
    table["columns"][1]["header_path_exact"] = ["Kỳ trước", "VND"]
    candidate, _cluster, _receipt = _evaluate(page)
    assert candidate["status"] == READY
    assert {item["unit"] for item in candidate["mappings"]} == {"VND"}
    pbt = next(item for item in candidate["mappings"] if item["role"] == "PROFIT_BEFORE_TAX")
    assert [value["coefficient"] for value in pbt["values"]] == [100_000_000, 80_000_000]


def test_unknown_value_columns_require_a_source_visible_period_axis() -> None:
    page = _page(
        [
            _row("Lợi nhuận trước thuế thu nhập doanh nghiệp", "100", "80"),
            _row("Thu nhập tính thuế", "100", "80", kind="SUBTOTAL"),
        ]
    )
    table = page["sections"][0]["tables"][0]
    table["unit_exact"] = "Đơn vị tính: triệu đồng"
    for column, header in zip(table["columns"], [["Mã A"], ["Mã B"]], strict=True):
        column["value_kind"] = "UNKNOWN"
        column["header_path_exact"] = header
    candidate, _cluster, _receipt = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["reasons"] == ["FRAGMENT_PERIOD_OR_UNIT_AXIS_NOT_LOCALLY_USABLE"]


def test_unknown_duration_columns_use_only_distinct_suffix_after_common_prefix() -> None:
    page = _page(
        [
            _row("Tổng lợi nhuận kế toán trước thuế", "100", "80"),
            _row("Tổng thu nhập chịu thuế", "100", "80", kind="SUBTOTAL"),
        ]
    )
    table = page["sections"][0]["tables"][0]
    table["unit_exact"] = "Đơn vị tính: triệu đồng"
    for column, header in zip(
        table["columns"],
        [
            ["Luỹ kế từ đầu năm đến cuối kỳ này", "Năm nay"],
            ["Luỹ kế từ đầu năm đến cuối kỳ này", "Năm trước"],
        ],
        strict=True,
    ):
        column["value_kind"] = "UNKNOWN"
        column["header_path_exact"] = header
    candidate, _cluster, _receipt = _evaluate(page)
    assert candidate["status"] == READY
    assert [item["role"] for item in candidate["mappings"]] == [
        "PROFIT_BEFORE_TAX",
        "TAXABLE_INCOME",
    ]

    conflicting = deepcopy(page)
    conflicting["sections"][0]["tables"][0]["columns"][1]["header_path_exact"] = [
        "Luỹ kế từ đầu năm đến cuối kỳ này",
        "Năm nay",
    ]
    unresolved, _cluster, _receipt = _evaluate(conflicting)
    assert unresolved["status"] == UNRESOLVED
    assert unresolved["mappings"] == []


def test_deferred_tax_balance_surface_is_typed_control() -> None:
    page = _page(
        [
            _row("Tài sản thuế thu nhập hoãn lại", None, None, kind="GROUP"),
            _row("Số dư cuối kỳ", "10", "8", kind="TOTAL"),
        ],
        owner="34.2 Thuế thu nhập doanh nghiệp hoãn lại",
    )
    section = page["sections"][0]
    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        page, section, section["tables"][0], compiled_specs=_compiled()
    )
    assert classification["typed_control_disposition"] == (
        "DEFERRED_TAX_BALANCE_CONTROL_OUTSIDE_INCOME_TAX_EXPENSE"
    )


def test_deferred_expense_context_maps_only_exact_printed_net_total() -> None:
    page = _page(_canonical_rows())
    deferred_rows = [
        _row(
            "Chi phí thuế thu nhập doanh nghiệp hoãn lại phát sinh từ hoàn nhập "
            "tài sản thuế thu nhập hoãn lại",
            "14.913",
            "33.594",
        ),
        _row(
            "Thu nhập thuế thu nhập doanh nghiệp hoãn lại phát sinh từ các khoản "
            "chênh lệch tạm thời được khấu trừ",
            "(14.858)",
            "(17.190)",
        ),
        _row(None, "55", "16.404", kind="TOTAL"),
    ]
    page["sections"].append(
        {
            "content_kind": "FINANCIAL_NOTE",
            "narratives_exact": [],
            "statement_type": "NOT_APPLICABLE",
            "tables": [_table(deferred_rows)],
            "title_exact": "33.2 Chi phí thuế thu nhập doanh nghiệp hoãn lại",
        }
    )
    candidate, _cluster, _receipt = _evaluate(page)
    mapping = next(item for item in candidate["mappings"] if item["role"] == "DEFERRED_TAX_NET")
    assert mapping["row_id"] == "r3"
    assert mapping["source_refs"][0]["label_exact"] is None
    assert [value["coefficient"] for value in mapping["values"]] == [55, 16_404]
    deferred_receipt = candidate["closure_receipt"]["table_receipts"][1]
    assert deferred_receipt["classification"]["typed_control_disposition"] is None
    assert deferred_receipt["classification"]["typed_control_override_receipts"] == [
        {
            "control_disposition": ("DEFERRED_TAX_BALANCE_CONTROL_OUTSIDE_INCOME_TAX_EXPENSE"),
            "declared_roles": ["DEFERRED_TAX_NET"],
            "rule": "DECLARED_ROLE_EXPLICITLY_OVERRIDES_BROAD_CONTROL_SURFACE",
        }
    ]
    assert len(deferred_receipt["source_only_rows"]) == 2
    assert all(item["consumed_by_exact_equation"] for item in deferred_receipt["source_only_rows"])


def test_candidate_replay_rejects_stage_receipt_tamper() -> None:
    page = _page(_canonical_rows())
    candidate, cluster, receipt = _evaluate(page)
    candidate["closure_receipt"]["table_receipts"][0]["classification"][
        "outside_ordered_role_scope_rows"
    ][0]["row_ordinal"] = 999
    with pytest.raises(GeminiJsonMultitableHierarchicalFamilyV1Error):
        validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
            candidate,
            regions=cluster["component_regions"],
            page_json_by_version={VERSION_ID: page},
            compiled_specs=_compiled(),
            query_receipt=receipt,
        )


def test_candidate_replay_rejects_ordered_projection_receipt_tamper() -> None:
    page = _page(_canonical_rows())
    candidate, cluster, receipt = _evaluate(page)
    candidate["closure_receipt"]["table_receipts"][0]["ordered_role_scope_projection_receipts"][0][
        "target_role"
    ] = "NON_DEDUCTIBLE_EXPENSE"
    with pytest.raises(GeminiJsonMultitableHierarchicalFamilyV1Error):
        validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
            candidate,
            regions=cluster["component_regions"],
            page_json_by_version={VERSION_ID: page},
            compiled_specs=_compiled(),
            query_receipt=receipt,
        )


def test_family_adapter_compiles_private_primary_source_policies_fail_closed() -> None:
    compiled = _adapter_compiled()
    assert compiled["income_tax_adapter_spec"]["family_id"] == "INCOME_TAX"
    assert compiled["income_tax_adapter_spec"]["primary_unit_corroboration_policy"] == (
        "UNIQUE_CANONICAL_UNIT_FROM_AT_LEAST_TWO_EXPLICIT_PRIMARY_"
        "STATEMENT_TABLES_SAME_DOCUMENT"
    )
    assert len(compiled["income_tax_source_repairs"]) == 13
    assert compiled["income_tax_primary_both_specs"]["root_component_roles"] == [
        "CURRENT_TAX_PARENT",
        "DEFERRED_TAX_NET",
    ]
    malformed = _json("tm-income-tax-adapter-v1.json")
    malformed["primary_projection_policy"] = "ALLOW_ANY_PRIMARY_ROW"
    with pytest.raises(GeminiJsonIncomeTaxFamilyV1Error):
        compile_gemini_json_income_tax_family_specs_v1(
            _json("tm-income-tax-topology-v1.json"),
            _json("tm-income-tax-evaluation-v1.json"),
            _json("tm-income-tax-schema-binding-v1.json"),
            adapter_spec=malformed,
            source_repair_spec=_json("tm-income-tax-source-repair-v1.json"),
        )

    malformed_repairs = _json("tm-income-tax-source-repair-v1.json")
    malformed_repairs["repairs"][0]["visual_evidence"]["crop_bbox_pixels"][2] = 99_999
    with pytest.raises(GeminiJsonIncomeTaxFamilyV1Error):
        compile_gemini_json_income_tax_family_specs_v1(
            _json("tm-income-tax-topology-v1.json"),
            _json("tm-income-tax-evaluation-v1.json"),
            _json("tm-income-tax-schema-binding-v1.json"),
            adapter_spec=_json("tm-income-tax-adapter-v1.json"),
            source_repair_spec=malformed_repairs,
        )


def test_source_repair_recoalesces_private_note_before_candidate_replay() -> None:
    compiled = _adapter_compiled_with_fixture_row_repair()
    page = _page(
        [
            _row("Lợi nhuận kế toán trước thuế TNDN", "100", "80"),
            _row("Thuế tính ở thuế suất 20%", "20", "16"),
            _row("Thu nhập không chịu thuế", "-", "-"),
            _row("Chi phí không được khấu trừ", "1", "2"),
            _row(
                "Chi phí thuế TNDN tính trên thu nhập chịu thuế kỳ hiện hành",
                "20",
                "15",
                kind="SUBTOTAL",
            ),
            _collapsed_current_tax_row(),
            _row("Thu nhập thuế TNDN - hoãn lại", "-", "-"),
            _row("Chi phí thuế TNDN", "20", "15", kind="TOTAL"),
        ],
        owner="29 THUẾ TNDN",
    )
    record = _record(page)
    original = deepcopy(record)
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[record], compiled_specs=compiled
    )
    assert base["status"] == READY
    repaired = deepcopy(page)
    repaired["sections"][0]["tables"][0]["rows"][5] = _repaired_current_tax_row()
    with pytest.raises(
        GeminiJsonMultitableHierarchicalFamilyV1Error,
        match="fragment classification drifted",
    ):
        evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
            regions=base["component_regions"],
            page_json_by_version={VERSION_ID: repaired},
            compiled_specs=compiled,
            query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
                base["component_regions"]
            ),
        )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=[record], base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == READY
    assert cluster["cluster_id"] != base["cluster_id"]
    candidate = evaluate_gemini_json_income_tax_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        selected_page_axis=[{key: value for key, value in record.items() if key != "page_json"}],
        compiled_specs=compiled,
        query_receipt=build_gemini_json_income_tax_region_query_receipt_v1(
            cluster["component_regions"], cluster=cluster
        ),
    )
    assert candidate["status"] == READY
    current = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "CURRENT_TAX_PARENT"
    )
    assert [value["coefficient"] for value in current["values"]] == [20, 15]
    assert [value["source_text"] for value in current["values"]] == ["20", "15"]
    assert current["source_refs"][0]["label_exact"] == "Chi phí thuế TNDN - hiện hành"
    assert record == original


def test_primary_income_statement_projects_only_final_duration_lanes_and_restores_source() -> None:
    compiled = _adapter_compiled()
    page = _primary_page(_primary_tax_rows())
    record = _primary_record(page)
    original = deepcopy(record)
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[record], compiled_specs=compiled
    )
    assert base["status"] != READY
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=[record], base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == READY
    regions = cluster["component_regions"]
    candidate = evaluate_gemini_json_income_tax_family_cluster_v1(
        regions=regions,
        page_json_by_version={VERSION_ID: page},
        selected_page_axis=[{key: value for key, value in record.items() if key != "page_json"}],
        compiled_specs=compiled,
        query_receipt=build_gemini_json_income_tax_region_query_receipt_v1(
            regions, cluster=cluster
        ),
    )
    assert candidate["status"] == READY
    assert [mapping["role"] for mapping in candidate["mappings"]] == [
        "CURRENT_TAX_PARENT",
        "DEFERRED_TAX_NET",
        "FAMILY_ROOT_TOTAL",
    ]
    assert [
        [value["coefficient"] for value in mapping["values"]] for mapping in candidate["mappings"]
    ] == [[10, 20], [30, 40], [40, 60]]
    assert {
        (ref["row_ordinal"], tuple(ref["money_column_ordinals"]))
        for mapping in candidate["mappings"]
        for ref in mapping["source_refs"]
    } == {(1, (3, 4)), (2, (3, 4)), (3, (3, 4))}
    assert candidate["closure_receipt"]["income_tax_adapter_receipt"]["strategy"] == (
        "DIRECT_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION"
    )
    assert record == original


def test_primary_projection_preserves_blank_deferred_lane_without_zero_imputation() -> None:
    compiled = _adapter_compiled()
    rows = _primary_tax_rows(deferred=(None, None), root=("10", "20"))
    page = _primary_page(rows)
    record = _primary_record(page)
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[record], compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=[record], base_cluster=base, compiled_specs=compiled
    )
    regions = cluster["component_regions"]
    candidate = evaluate_gemini_json_income_tax_family_cluster_v1(
        regions=regions,
        page_json_by_version={VERSION_ID: page},
        selected_page_axis=[{key: value for key, value in record.items() if key != "page_json"}],
        compiled_specs=compiled,
        query_receipt=build_gemini_json_income_tax_region_query_receipt_v1(
            regions, cluster=cluster
        ),
    )
    assert candidate["status"] == READY
    assert [mapping["role"] for mapping in candidate["mappings"]] == [
        "CURRENT_TAX_PARENT",
        "FAMILY_ROOT_TOTAL",
    ]
    assert all(mapping["role"] != "DEFERRED_TAX_NET" for mapping in candidate["mappings"])


def test_primary_projection_preserves_explicit_dash_and_true_blank_as_partial_source() -> None:
    compiled = _adapter_compiled()
    page = _primary_page(_primary_tax_rows(deferred=("-", None), root=("10", "20")))
    record = _primary_record(page)
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[record], compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=[record], base_cluster=base, compiled_specs=compiled
    )
    candidate = evaluate_gemini_json_income_tax_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        selected_page_axis=[{key: value for key, value in record.items() if key != "page_json"}],
        compiled_specs=compiled,
        query_receipt=build_gemini_json_income_tax_region_query_receipt_v1(
            cluster["component_regions"], cluster=cluster
        ),
    )
    assert candidate["status"] == READY
    deferred = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "DEFERRED_TAX_NET"
    )
    assert [value["coefficient"] for value in deferred["values"]] == [0, None]
    assert [value["source_text"] for value in deferred["values"]] == ["-", None]
    assert [value["state"] for value in deferred["values"]] == [
        "DASH_ZERO",
        "BLANK_SOURCE_CELL",
    ]
    equation = candidate["closure_receipt"]["equations"][0]
    assert equation["lane_statuses"] == ["EXACT", "INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"]


def test_unitless_primary_tax_rows_use_two_exact_primary_statement_unit_controls() -> None:
    compiled = _adapter_compiled()
    target = _primary_record(_primary_page(_primary_tax_rows(), unit=None))
    balance = _primary_record(
        _primary_unit_control_page(statement_type="BALANCE_SHEET", unit="VND"),
        page_json_version_id="gfpstorev1:json:" + "d" * 64,
        physical_page=3,
        selected_page_ordinal=1,
    )
    cash_flow = _primary_record(
        _primary_unit_control_page(statement_type="CASH_FLOW", unit="VND"),
        page_json_version_id="gfpstorev1:json:" + "e" * 64,
        physical_page=7,
        selected_page_ordinal=3,
    )
    records = [balance, target, cash_flow]
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == READY
    adapter = cluster["owner_receipt"]["income_tax_query_adapter_receipt"]
    assert adapter["adapter_spec_sha256"] == compiled["income_tax_adapter_spec_sha256"]
    unit_receipt = adapter["primary_projection_receipt"][
        "primary_unit_corroboration_receipt"
    ]
    assert unit_receipt["canonical_unit"] == "VND"
    assert len(unit_receipt["sources"]) == 2
    pages = {record["page_json_version_id"]: record["page_json"] for record in records}
    candidate = evaluate_gemini_json_income_tax_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version=pages,
        selected_page_axis=[
            {key: value for key, value in record.items() if key != "page_json"}
            for record in records
        ],
        compiled_specs=compiled,
        query_receipt=build_gemini_json_income_tax_region_query_receipt_v1(
            cluster["component_regions"], cluster=cluster
        ),
    )
    assert candidate["status"] == READY
    assert {mapping["unit"] for mapping in candidate["mappings"]} == {"VND"}


def test_primary_unit_corroboration_rejects_one_source_or_mixed_canonical_units() -> None:
    compiled = _adapter_compiled()
    target = _primary_record(_primary_page(_primary_tax_rows(), unit=None))
    balance = _primary_record(
        _primary_unit_control_page(statement_type="BALANCE_SHEET", unit="VND"),
        page_json_version_id="gfpstorev1:json:" + "d" * 64,
        physical_page=3,
        selected_page_ordinal=1,
    )
    cash_flow = _primary_record(
        _primary_unit_control_page(statement_type="CASH_FLOW", unit="Triệu đồng"),
        page_json_version_id="gfpstorev1:json:" + "e" * 64,
        physical_page=7,
        selected_page_ordinal=3,
    )
    for records in ([balance, target], [balance, target, cash_flow]):
        base = coalesce_gemini_json_multitable_hierarchical_document_v1(
            page_records=records, compiled_specs=compiled
        )
        cluster = recover_gemini_json_income_tax_query_cluster_v1(
            page_records=records, base_cluster=base, compiled_specs=compiled
        )
        assert cluster["status"] == UNRESOLVED
        assert cluster["component_regions"] == []
        assert cluster["reasons"] == ["PRIMARY_INCOME_TAX_SOURCE_ROWS_NOT_LOCALLY_USABLE"]


def test_primary_unit_corroboration_never_overrides_explicit_unsupported_unit() -> None:
    compiled = _adapter_compiled()
    target = _primary_record(_primary_page(_primary_tax_rows(), unit="Nghìn đồng"))
    balance = _primary_record(
        _primary_unit_control_page(statement_type="BALANCE_SHEET", unit="VND"),
        page_json_version_id="gfpstorev1:json:" + "d" * 64,
        physical_page=3,
        selected_page_ordinal=1,
    )
    cash_flow = _primary_record(
        _primary_unit_control_page(statement_type="CASH_FLOW", unit="VND"),
        page_json_version_id="gfpstorev1:json:" + "e" * 64,
        physical_page=7,
        selected_page_ordinal=3,
    )
    records = [balance, target, cash_flow]
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert cluster["reasons"] == ["PRIMARY_INCOME_TAX_SOURCE_ROWS_NOT_LOCALLY_USABLE"]


def test_unitless_primary_rejects_unsupported_document_unit_control() -> None:
    compiled = _adapter_compiled()
    target = _primary_record(_primary_page(_primary_tax_rows(), unit=None))
    balance = _primary_record(
        _primary_unit_control_page(statement_type="BALANCE_SHEET", unit="VND"),
        page_json_version_id="gfpstorev1:json:" + "d" * 64,
        physical_page=3,
        selected_page_ordinal=1,
    )
    cash_flow = _primary_record(
        _primary_unit_control_page(statement_type="CASH_FLOW", unit="VND"),
        page_json_version_id="gfpstorev1:json:" + "e" * 64,
        physical_page=7,
        selected_page_ordinal=3,
    )
    unsupported = _primary_record(
        _primary_unit_control_page(statement_type="BALANCE_SHEET", unit="Nghìn đồng"),
        page_json_version_id="gfpstorev1:json:" + "f" * 64,
        physical_page=8,
        selected_page_ordinal=4,
    )
    records = [balance, target, cash_flow, unsupported]
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert cluster["reasons"] == ["PRIMARY_INCOME_TAX_SOURCE_ROWS_NOT_LOCALLY_USABLE"]


def test_primary_projection_rejects_visible_root_equation_mismatch() -> None:
    compiled = _adapter_compiled()
    page = _primary_page(_primary_tax_rows(root=("41", "60")))
    record = _primary_record(page)
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[record], compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=[record], base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert cluster["reasons"] == ["MISMATCHED_PRIMARY_INCOME_TAX_SOURCE_EQUATION"]


@pytest.mark.parametrize(
    "current,deferred,root",
    [
        (("10", "20"), ("không rõ", "1"), ("10", "20")),
        (("10", "20"), ("2", "1"), ("không rõ", "21")),
        (("không rõ", "20"), ("2", "1"), ("2", "1")),
    ],
)
def test_primary_projection_rejects_any_invalid_recognized_money_cell(
    current: tuple[str | None, str | None],
    deferred: tuple[str | None, str | None],
    root: tuple[str | None, str | None],
) -> None:
    compiled = _adapter_compiled()
    record = _primary_record(
        _primary_page(_primary_tax_rows(current=current, deferred=deferred, root=root))
    )
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[record], compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=[record], base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert cluster["reasons"] == ["INVALID_PRIMARY_INCOME_TAX_SOURCE_MONEY_CELL"]
    receipt = cluster["owner_receipt"]["income_tax_primary_selection_conflict_receipt"]
    assert len(receipt["invalid_source_rows"]) == 1


def test_primary_projection_rejects_two_incompatible_source_presentations() -> None:
    compiled = _adapter_compiled()
    first = _primary_record(_primary_page(_primary_tax_rows()))
    second_page = _primary_page(_primary_tax_rows(root=("41", "60")))
    # Keep the second table internally exact but economically different.
    second_page["sections"][0]["tables"][0]["rows"][0]["values_exact"][2] = "11"
    second = _primary_record(
        second_page,
        page_json_version_id="gfpstorev1:json:" + "d" * 64,
        physical_page=6,
        selected_page_ordinal=3,
    )
    records = [first, second]
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["reasons"] == ["CONFLICTING_PRIMARY_INCOME_TAX_SOURCE_PRESENTATIONS"]


def test_primary_projection_rejects_complementary_partial_duplicate_lanes() -> None:
    compiled = _adapter_compiled()
    first = _primary_record(
        _primary_page(
            _primary_tax_rows(
                current=("10000000", None),
                deferred=(None, None),
                root=("10000000", None),
            ),
            unit="VND",
        )
    )
    second = _primary_record(
        _primary_page(
            _primary_tax_rows(
                current=(None, "20"), deferred=(None, None), root=(None, "20")
            ),
            unit="Triệu đồng",
        ),
        page_json_version_id="gfpstorev1:json:" + "d" * 64,
        physical_page=6,
        selected_page_ordinal=3,
    )
    records = [first, second]
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert cluster["reasons"] == ["CONFLICTING_PRIMARY_INCOME_TAX_SOURCE_PRESENTATIONS"]


def test_primary_projection_selects_role_complete_compatible_presentation() -> None:
    compiled = _adapter_compiled()
    vnd = _primary_record(
        _primary_page(
            _primary_tax_rows(
                current=("10000000", "20000000"),
                deferred=(None, None),
                root=("10000000", "20000000"),
            ),
            unit="VND",
        )
    )
    million = _primary_record(
        _primary_page(
            _primary_tax_rows(
                current=("10", "20"), deferred=("-", "-"), root=("10", "20")
            ),
            unit="Triệu đồng",
        ),
        page_json_version_id="gfpstorev1:json:" + "d" * 64,
        physical_page=6,
        selected_page_ordinal=3,
    )
    records = [vnd, million]
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == READY
    adapter = cluster["owner_receipt"]["income_tax_query_adapter_receipt"]
    assert adapter["primary_projection_receipt"]["canonical_unit"] == "MILLION_VND"
    assert adapter["primary_projection_receipt"]["selection_rule"].startswith(
        "ROLE_AND_OBSERVED_LANE_EVIDENCE_FRONTIER_DOMINANT"
    )
    candidate = evaluate_gemini_json_income_tax_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={
            record["page_json_version_id"]: record["page_json"] for record in records
        },
        selected_page_axis=[
            {key: value for key, value in record.items() if key != "page_json"}
            for record in records
        ],
        compiled_specs=compiled,
        query_receipt=build_gemini_json_income_tax_region_query_receipt_v1(
            cluster["component_regions"], cluster=cluster
        ),
    )
    assert candidate["status"] == READY
    deferred = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "DEFERRED_TAX_NET"
    )
    assert [value["coefficient"] for value in deferred["values"]] == [0, 0]
    assert deferred["unit"] == "MILLION_VND"


def test_valid_note_cannot_hide_conflicting_primary_presentations() -> None:
    compiled = _adapter_compiled()
    note = _record(_page(_canonical_rows()))
    first = _primary_record(
        _primary_page(
            _primary_tax_rows(current=("20", "15"), deferred=("1", "2"), root=("21", "17"))
        ),
        page_json_version_id="gfpstorev1:json:" + "d" * 64,
        physical_page=5,
        selected_page_ordinal=2,
    )
    second = _primary_record(
        _primary_page(
            _primary_tax_rows(
                current=("90", "80"), deferred=("10", "20"), root=("100", "100")
            )
        ),
        page_json_version_id="gfpstorev1:json:" + "e" * 64,
        physical_page=6,
        selected_page_ordinal=3,
    )
    records = [note, first, second]
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    assert base["status"] == READY
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert cluster["reasons"] == ["CONFLICTING_PRIMARY_INCOME_TAX_SOURCE_PRESENTATIONS"]
    receipt = cluster["owner_receipt"]["income_tax_primary_selection_conflict_receipt"]
    assert len(receipt["presentations"]) == 2


def test_valid_note_roles_are_preserved_while_primary_direct_root_is_added() -> None:
    compiled = _adapter_compiled()
    note_page = _page(_canonical_rows())
    note_record = _record(note_page)
    primary_page = _primary_page(
        _primary_tax_rows(
            current=("20", "15"),
            deferred=("1", "2"),
            root=("21", "17"),
        )
    )
    primary_record = _primary_record(
        primary_page,
        page_json_version_id="gfpstorev1:json:" + "d" * 64,
        physical_page=2,
        selected_page_ordinal=2,
    )
    records = [note_record, primary_record]
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    assert base["status"] == READY
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == READY
    assert cluster["component_regions"] == base["component_regions"]
    regions = cluster["component_regions"]
    candidate = evaluate_gemini_json_income_tax_family_cluster_v1(
        regions=regions,
        page_json_by_version={
            VERSION_ID: note_page,
            primary_record["page_json_version_id"]: primary_page,
        },
        selected_page_axis=[
            {key: value for key, value in record.items() if key != "page_json"}
            for record in records
        ],
        compiled_specs=compiled,
        query_receipt=build_gemini_json_income_tax_region_query_receipt_v1(
            regions, cluster=cluster
        ),
    )
    assert candidate["status"] == READY
    root = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL"
    )
    assert [value["coefficient"] for value in root["values"]] == [21, 17]
    assert (
        root["source_refs"][0]["locator"]["page_json_version_id"]
        == (primary_record["page_json_version_id"])
    )
    current = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "CURRENT_TAX_PARENT"
    )
    assert current["source_refs"][0]["locator"]["page_json_version_id"] == VERSION_ID
    adapter = candidate["closure_receipt"]["income_tax_adapter_receipt"]
    assert adapter["strategy"] == ("DIRECT_NOTE_PLUS_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION")
    suppressed = adapter["primary_candidate_proof"]["suppressed_duplicate_primary_mappings"]
    assert [item["role"] for item in suppressed] == ["CURRENT_TAX_PARENT"]


def test_partial_direct_note_mapping_yields_to_full_compatible_primary_mapping() -> None:
    compiled = _adapter_compiled()
    note_page = _page(
        [
            _row("Chi phí thuế TNDN hiện hành", "20", None),
            _row("Chi phí thuế thu nhập doanh nghiệp hoãn lại", "1", "2"),
            _row("Chi phí thuế thu nhập doanh nghiệp", "21", "18", kind="TOTAL"),
        ]
    )
    note_record = _record(note_page)
    primary_page = _primary_page(
        _primary_tax_rows(current=("20", "16"), deferred=("1", "2"), root=("21", "18"))
    )
    primary_record = _primary_record(
        primary_page,
        page_json_version_id="gfpstorev1:json:" + "d" * 64,
        physical_page=2,
        selected_page_ordinal=2,
    )
    records = [note_record, primary_record]
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    assert base["status"] == READY
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    candidate = evaluate_gemini_json_income_tax_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={
            note_record["page_json_version_id"]: note_page,
            primary_record["page_json_version_id"]: primary_page,
        },
        selected_page_axis=[
            {key: value for key, value in record.items() if key != "page_json"}
            for record in records
        ],
        compiled_specs=compiled,
        query_receipt=build_gemini_json_income_tax_region_query_receipt_v1(
            cluster["component_regions"], cluster=cluster
        ),
    )
    assert candidate["status"] == READY
    current = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "CURRENT_TAX_PARENT"
    )
    assert [value["coefficient"] for value in current["values"]] == [20, 16]
    proof = candidate["closure_receipt"]["income_tax_adapter_receipt"][
        "primary_candidate_proof"
    ]
    assert [item["role"] for item in proof["suppressed_cross_source_note_mappings"]] == [
        "CURRENT_TAX_PARENT"
    ]


def test_sign_inverted_generic_note_and_primary_presentations_fail_closed() -> None:
    compiled = _adapter_compiled()
    note_page = _page(
        [
            _row("Chi phí thuế TNDN theo thuế suất", "20", "16"),
            _row("Chi phí thuế TNDN hiện hành", "20", "16"),
            _row("Chi phí thuế thu nhập doanh nghiệp hoãn lại", "2", "1"),
            _row("Chi phí thuế thu nhập doanh nghiệp", "22", "17", kind="TOTAL"),
        ]
    )
    note_record = _record(note_page)
    primary_page = _primary_page(
        _primary_tax_rows(
            current=("(20)", "(16)"),
            deferred=("(2)", "(1)"),
            root=("(22)", "(17)"),
        )
    )
    primary_record = _primary_record(
        primary_page,
        page_json_version_id="gfpstorev1:json:" + "d" * 64,
        physical_page=2,
        selected_page_ordinal=2,
    )
    records = [note_record, primary_record]
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    assert base["status"] == READY
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    candidate = evaluate_gemini_json_income_tax_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={
            note_record["page_json_version_id"]: note_page,
            primary_record["page_json_version_id"]: primary_page,
        },
        selected_page_axis=[
            {key: value for key, value in record.items() if key != "page_json"}
            for record in records
        ],
        compiled_specs=compiled,
        query_receipt=build_gemini_json_income_tax_region_query_receipt_v1(
            cluster["component_regions"], cluster=cluster
        ),
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["reasons"] == [
        "SIGN_INVERTED_DIRECT_NOTE_AND_PRIMARY_INCOME_TAX_PRESENTATIONS"
    ]


def test_conflicting_direct_note_and_primary_tax_presentations_fail_closed() -> None:
    compiled = _adapter_compiled()
    note_page = _page(
        [
            _row("Chi phí thuế TNDN hiện hành", "20", "15"),
            _row("Chi phí thuế thu nhập doanh nghiệp hoãn lại", "1", "2"),
            _row("Chi phí thuế thu nhập doanh nghiệp", "21", "17", kind="TOTAL"),
        ]
    )
    note_record = _record(note_page)
    primary_page = _primary_page(
        _primary_tax_rows(current=("90", "80"), deferred=("10", "20"), root=("100", "100"))
    )
    primary_record = _primary_record(
        primary_page,
        page_json_version_id="gfpstorev1:json:" + "d" * 64,
        physical_page=2,
        selected_page_ordinal=2,
    )
    records = [note_record, primary_record]
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    # Exercise the actual direct-note strategy selected from the complete base query.
    candidate = evaluate_gemini_json_income_tax_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={
            note_record["page_json_version_id"]: note_page,
            primary_record["page_json_version_id"]: primary_page,
        },
        selected_page_axis=[
            {key: value for key, value in record.items() if key != "page_json"}
            for record in records
        ],
        compiled_specs=compiled,
        query_receipt=build_gemini_json_income_tax_region_query_receipt_v1(
            cluster["component_regions"], cluster=cluster
        ),
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["reasons"] == [
        "CONFLICTING_DIRECT_NOTE_AND_PRIMARY_INCOME_TAX_PRESENTATIONS"
    ]
    assert "income_tax_unresolved_evidence_receipt" in candidate["closure_receipt"]


def test_equal_direct_note_and_primary_tax_roots_remain_ready() -> None:
    compiled = _adapter_compiled()
    note_page = _page(
        [
            _row("Chi phí thuế TNDN hiện hành", "20", "15"),
            _row("Chi phí thuế thu nhập doanh nghiệp hoãn lại", "1", "2"),
            _row("Chi phí thuế thu nhập doanh nghiệp", "21", "17", kind="TOTAL"),
        ]
    )
    note_record = _record(note_page)
    primary_page = _primary_page(
        _primary_tax_rows(current=("20", "15"), deferred=("1", "2"), root=("21", "17"))
    )
    primary_record = _primary_record(
        primary_page,
        page_json_version_id="gfpstorev1:json:" + "d" * 64,
        physical_page=2,
        selected_page_ordinal=2,
    )
    records = [note_record, primary_record]
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    candidate = evaluate_gemini_json_income_tax_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={
            note_record["page_json_version_id"]: note_page,
            primary_record["page_json_version_id"]: primary_page,
        },
        selected_page_axis=[
            {key: value for key, value in record.items() if key != "page_json"}
            for record in records
        ],
        compiled_specs=compiled,
        query_receipt=build_gemini_json_income_tax_region_query_receipt_v1(
            cluster["component_regions"], cluster=cluster
        ),
    )
    assert candidate["status"] == READY
    root = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL"
    )
    assert [value["coefficient"] for value in root["values"]] == [21, 17]
    proof = candidate["closure_receipt"]["income_tax_adapter_receipt"][
        "primary_candidate_proof"
    ]
    assert proof["suppressed_note_root_mappings"] == []
    assert [
        item["role"] for item in proof["suppressed_duplicate_primary_mappings"]
    ] == ["CURRENT_TAX_PARENT", "DEFERRED_TAX_NET"]


def _supplemental_records(
    note_rows: list[dict[str, Any]],
    *,
    primary_current: tuple[str | None, str | None] = ("10", "8"),
    primary_deferred: tuple[str | None, str | None] = ("2", "1"),
    primary_root: tuple[str | None, str | None] = ("12", "9"),
    note_owner: str = "Chi phí thuế thu nhập doanh nghiệp hiện hành",
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    note_page = _page(note_rows, owner=note_owner)
    note_record = _record(note_page)
    primary_page = _primary_page(
        _primary_tax_rows(
            current=primary_current,
            deferred=primary_deferred,
            root=primary_root,
        )
    )
    primary_record = _primary_record(
        primary_page,
        page_json_version_id="gfpstorev1:json:" + "d" * 64,
        physical_page=2,
        selected_page_ordinal=2,
    )
    return [note_record, primary_record], note_page, primary_page


def _evaluate_supplemental_records(
    records: list[dict[str, Any]],
    *,
    compiled: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    # The shared query deliberately excludes the primary statement.  Build the
    # synthetic base disposition from that carrier alone, then give the
    # family-local adapter the complete selected-page document frontier.
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[records[-1]], compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    pages = {record["page_json_version_id"]: record["page_json"] for record in records}
    candidate = evaluate_gemini_json_income_tax_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version=pages,
        selected_page_axis=[
            {key: value for key, value in record.items() if key != "page_json"}
            for record in records
        ],
        compiled_specs=compiled,
        query_receipt=build_gemini_json_income_tax_region_query_receipt_v1(
            cluster["component_regions"], cluster=cluster
        ),
    )
    return cluster, candidate


def test_supplemental_bank_and_subsidiary_exact_sum_maps_direct_source_rows() -> None:
    compiled = _adapter_compiled()
    records, _note_page, _primary_page_value = _supplemental_records(
        [
            _row("Ngân hàng", "7", "5"),
            _row("Công ty TNHH Quản lý nợ và Khai thác tài sản", "3", "3"),
            _row("Cộng", "10", "8", kind="TOTAL"),
        ]
    )
    original = deepcopy(records)
    cluster, candidate = _evaluate_supplemental_records(records, compiled=compiled)
    assert cluster["status"] == READY
    assert candidate["status"] == READY
    assert [mapping["role"] for mapping in candidate["mappings"]] == [
        "CURRENT_TAX_BANK",
        "SUBSIDIARY_TAX",
        "CURRENT_TAX_PARENT",
        "DEFERRED_TAX_NET",
        "FAMILY_ROOT_TOTAL",
    ]
    assert [
        [value["coefficient"] for value in mapping["values"]]
        for mapping in candidate["mappings"][:3]
    ] == [[7, 5], [3, 3], [10, 8]]
    assert {
        ref["locator"]["page_json_version_id"]
        for mapping in candidate["mappings"][:3]
        for ref in mapping["source_refs"]
    } == {VERSION_ID}
    adapter = candidate["closure_receipt"]["income_tax_adapter_receipt"]
    assert adapter["strategy"] == (
        "DIRECT_SUPPLEMENTAL_NOTE_PLUS_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION"
    )
    proof = adapter["primary_candidate_proof"]
    assert len(proof["supplemental_projection_receipts"]) == 1
    receipt = proof["supplemental_projection_receipts"][0]
    assert receipt["presentation_kind"] == "CURRENT_TAX_ENTITY_SPLIT_EXACT_SUM"
    assert [row["row_ordinal"] for row in receipt["source_table_row_axis"]] == [1, 2, 3]
    assert records == original


def test_conflicting_supplemental_and_primary_current_tax_fails_closed() -> None:
    compiled = _adapter_compiled()
    records, _note_page, _primary_page_value = _supplemental_records(
        [
            _row("Ngân hàng", "7", "5"),
            _row("Công ty TNHH Quản lý nợ và Khai thác tài sản", "3", "3"),
            _row("Cộng", "10", "8", kind="TOTAL"),
        ],
        primary_current=("90", "80"),
        primary_deferred=("10", "20"),
        primary_root=("100", "100"),
    )
    _cluster, candidate = _evaluate_supplemental_records(records, compiled=compiled)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["reasons"] == [
        "CONFLICTING_DIRECT_SUPPLEMENTAL_AND_PRIMARY_INCOME_TAX_PRESENTATIONS"
    ]
    evidence = candidate["closure_receipt"]["income_tax_unresolved_evidence_receipt"]
    assert len(evidence["evidence"]["supplemental_candidates"]) == 1


def test_exact_sign_inverted_supplemental_and_primary_current_tax_is_explicit_control() -> None:
    compiled = _adapter_compiled()
    records, _note_page, _primary_page_value = _supplemental_records(
        [
            _row("Ngân hàng", "7", "5"),
            _row("Công ty TNHH Quản lý nợ và Khai thác tài sản", "3", "3"),
            _row("Cộng", "10", "8", kind="TOTAL"),
        ],
        primary_current=("(10)", "(8)"),
        primary_deferred=("(2)", "(1)"),
        primary_root=("(12)", "(9)"),
    )
    _cluster, candidate = _evaluate_supplemental_records(records, compiled=compiled)
    assert candidate["status"] == READY
    current = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "CURRENT_TAX_PARENT"
    )
    assert [value["coefficient"] for value in current["values"]] == [-10, -8]
    proof = candidate["closure_receipt"]["income_tax_adapter_receipt"][
        "primary_candidate_proof"
    ]
    assert proof["cross_source_sign_orientation"] == -1
    assert proof["suppressed_duplicate_primary_mappings"] == []
    suppressed = proof["suppressed_cross_source_supplemental_mappings"]
    assert [item["role"] for item in suppressed] == [
        "CURRENT_TAX_BANK",
        "SUBSIDIARY_TAX",
        "CURRENT_TAX_PARENT",
    ]
    assert [value["coefficient"] for value in suppressed[-1]["values"]] == [10, 8]
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "CURRENT_TAX_PARENT",
        "DEFERRED_TAX_NET",
        "FAMILY_ROOT_TOTAL",
    }


def test_mixed_cross_source_sign_orientations_fail_closed() -> None:
    compiled = _adapter_compiled()
    current = _table([_row("Chi phí thuế TNDN hiện hành", "20", "16")])
    deferred = _table(
        [_row("Chi phí thuế thu nhập doanh nghiệp hoãn lại", "2", "1")]
    )
    records, _unused_note, primary_page = _supplemental_records(
        [],
        primary_current=("(20)", "(16)"),
        primary_deferred=("2", "1"),
        primary_root=("(18)", "(15)"),
    )
    records[0]["page_json"] = _page([], tables=[current, deferred])
    records[1]["page_json"] = primary_page
    _cluster, candidate = _evaluate_supplemental_records(records, compiled=compiled)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["reasons"] == [
        "CONFLICTING_DIRECT_SUPPLEMENTAL_AND_PRIMARY_INCOME_TAX_PRESENTATIONS"
    ]


def test_partial_supplemental_mapping_yields_to_full_compatible_primary_mapping() -> None:
    compiled = _adapter_compiled()
    records, _unused_note, primary_page = _supplemental_records(
        [_row("Chi phí thuế TNDN hiện hành", "20", None)],
        primary_current=("20", "16"),
        primary_deferred=("1", "2"),
        primary_root=("21", "18"),
    )
    records[1]["page_json"] = primary_page
    _cluster, candidate = _evaluate_supplemental_records(records, compiled=compiled)
    assert candidate["status"] == READY
    current = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "CURRENT_TAX_PARENT"
    )
    assert [value["coefficient"] for value in current["values"]] == [20, 16]
    proof = candidate["closure_receipt"]["income_tax_adapter_receipt"][
        "primary_candidate_proof"
    ]
    assert [
        item["role"] for item in proof["suppressed_cross_source_supplemental_mappings"]
    ] == ["CURRENT_TAX_PARENT"]


@pytest.mark.parametrize(
    "rows,reason",
    [
        (
            [
                _row("Ngân hàng", "7", "5"),
                _row("Công ty TNHH Quản lý nợ và Khai thác tài sản", "4", "3"),
                _row("Cộng", "10", "8", kind="TOTAL"),
            ],
            "SUPPLEMENTAL_CURRENT_TAX_ENTITY_EQUATION_MISMATCH",
        ),
        (
            [
                _row("Ngân hàng", "7", "5"),
                _row("Ngân hàng", "1", "1"),
                _row("Công ty TNHH Quản lý nợ và Khai thác tài sản", "3", "3"),
                _row("Cộng", "10", "8", kind="TOTAL"),
            ],
            "SUPPLEMENTAL_CURRENT_TAX_ENTITY_AXIS_NOT_UNIQUE",
        ),
        (
            [
                _row("Ngân hàng", "7", None),
                _row("Công ty TNHH Quản lý nợ và Khai thác tài sản", "3", "3"),
                _row("Cộng", "10", "8", kind="TOTAL"),
            ],
            "SUPPLEMENTAL_CURRENT_TAX_ENTITY_AXIS_NOT_UNIQUE",
        ),
        (
            [
                _row("Ngân hàng", "7", "5"),
                _row("Đơn vị phụ thuộc chưa xác định", None, None),
                _row("Công ty TNHH Quản lý nợ và Khai thác tài sản", "3", "3"),
                _row("Cộng", "10", "8", kind="TOTAL"),
            ],
            "SUPPLEMENTAL_CURRENT_TAX_ENTITY_FRONTIER_NOT_COMPLETE",
        ),
        (
            [
                _row("Ngân hàng", "7", "5"),
                _row("Nhóm thuế khác", None, None, kind="GROUP"),
                _row("Công ty TNHH Quản lý nợ và Khai thác tài sản", "3", "3"),
                _row("Cộng", "10", "8", kind="TOTAL"),
            ],
            "SUPPLEMENTAL_CURRENT_TAX_ENTITY_FRONTIER_NOT_COMPLETE",
        ),
        (
            [
                _row("Cộng", "10", "8", kind="TOTAL"),
                _row("Ngân hàng", "7", "5"),
                _row("Công ty TNHH Quản lý nợ và Khai thác tài sản", "3", "3"),
            ],
            "SUPPLEMENTAL_CURRENT_TAX_ENTITY_FRONTIER_NOT_COMPLETE",
        ),
    ],
)
def test_supplemental_entity_projection_fails_closed(
    rows: list[dict[str, Any]], reason: str
) -> None:
    compiled = _adapter_compiled()
    records, _note_page, _primary_page_value = _supplemental_records(rows)
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[records[-1]], compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert cluster["reasons"] == [reason]


def test_entity_equation_does_not_open_post_parent_adjustment_scope() -> None:
    compiled = _adapter_compiled()
    records, _note_page, _primary_page_value = _supplemental_records(
        [
            _row("Ngân hàng", "7", "5"),
            _row("Công ty TNHH Quản lý nợ và Khai thác tài sản", "3", "3"),
            _row("Cộng", "10", "8", kind="TOTAL"),
            _row("Số dư đầu kỳ", "100", "90"),
            _row("Điều chỉnh thuế TNDN năm trước", "4", "6"),
            _row("Thuế đã nộp", "(20)", "(10)"),
            _row("Số dư cuối kỳ", "84", "86", kind="TOTAL"),
        ]
    )
    _cluster, candidate = _evaluate_supplemental_records(records, compiled=compiled)
    assert candidate["status"] == READY
    assert "PRIOR_PERIOD_TAX_ADJUSTMENT" not in {
        mapping["role"] for mapping in candidate["mappings"]
    }
    proof = candidate["closure_receipt"]["income_tax_adapter_receipt"][
        "primary_candidate_proof"
    ]
    receipt = proof["supplemental_projection_receipts"][0]
    assert [row["row_ordinal"] for row in receipt["source_table_row_axis"]] == list(
        range(1, 8)
    )


@pytest.mark.parametrize(
    "label,role,values",
    [
        ("Chi phí thuế TNDN hiện hành ước tính của Ngân hàng", "CURRENT_TAX_BANK", [7, 5]),
        ("Chi phí thuế TNDN hiện hành của công ty con", "SUBSIDIARY_TAX", [3, 3]),
    ],
)
def test_direct_entity_specific_role_is_never_silently_dropped(
    label: str, role: str, values: list[int]
) -> None:
    compiled = _adapter_compiled()
    records, _unused_note, _primary_page_value = _supplemental_records(
        [_row(label, str(values[0]), str(values[1]))]
    )
    _cluster, candidate = _evaluate_supplemental_records(records, compiled=compiled)
    assert candidate["status"] == READY
    mapping = next(mapping for mapping in candidate["mappings"] if mapping["role"] == role)
    assert [value["coefficient"] for value in mapping["values"]] == values


def test_row_level_hard_negative_reset_preempts_supplemental_role() -> None:
    compiled = _adapter_compiled()
    records, _unused_note, _primary_page_value = _supplemental_records(
        [
            _row("Tài sản thuế thu nhập hoãn lại", None, None, kind="GROUP"),
            _row("Chi phí thuế thu nhập doanh nghiệp hoãn lại", "2", "1"),
        ]
    )
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[records[-1]], compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert cluster["reasons"] == ["SUPPLEMENTAL_ROLE_AFTER_STRUCTURAL_RESET"]


def test_rich_supplemental_reconciliation_keeps_unknown_adjustment_source_only() -> None:
    compiled = _adapter_compiled()
    current_table = _table(
        [
            _row("Năm hiện hành", "20", "16"),
            _row("Chi phí năm trước", "1", "2"),
            _row("Chi phí thuế TNDN hiện hành", "21", "18", kind="TOTAL"),
        ]
    )
    reconciliation = _table(
        [
            _row("Lợi nhuận kế toán trước thuế", "100", "80"),
            _row("Chi phí thuế TNDN theo thuế suất", "20", "16"),
            _row("Chi phí không được khấu trừ", "2", "3"),
            _row("Điều chỉnh khác", "(1)", "(1)"),
            _row("Chi phí thuế TNDN hiện hành", "21", "18", kind="TOTAL"),
        ]
    )
    note_page = _page([], tables=[current_table, reconciliation])
    records, _unused_note, primary_page = _supplemental_records(
        [],
        primary_current=("21", "18"),
        primary_deferred=("2", "1"),
        primary_root=("23", "19"),
    )
    records[0]["page_json"] = note_page
    records[1]["page_json"] = primary_page
    _cluster, candidate = _evaluate_supplemental_records(records, compiled=compiled)
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [value["coefficient"] for value in by_role["CURRENT_TAX_AT_RATE"]["values"]] == [
        20,
        16,
    ]
    assert (
        by_role["CURRENT_TAX_AT_RATE"]["source_refs"][0]["locator"]["table_id"]
        == "t1"
    )
    assert [value["coefficient"] for value in by_role["NON_DEDUCTIBLE_EXPENSE"]["values"]] == [
        2,
        3,
    ]
    proof = candidate["closure_receipt"]["income_tax_adapter_receipt"][
        "primary_candidate_proof"
    ]
    reconciliation_receipt = next(
        item
        for item in proof["supplemental_projection_receipts"]
        if item["locator"]["table_id"] == "t2"
    )
    assert [
        component["role"]
        for component in reconciliation_receipt["equation_receipts"][0]["component_rows"]
    ] == [
        "CURRENT_TAX_AT_RATE",
        "NON_DEDUCTIBLE_EXPENSE",
        "SOURCE_ONLY_EQUATION_COMPONENT",
    ]
    assert all(
        mapping["source_refs"][0]["locator"]["table_id"] != "t2"
        for mapping in candidate["mappings"]
        if mapping["role"] in {"CURRENT_TAX_AT_RATE", "CURRENT_TAX_PARENT"}
    )


def test_rich_reconciliation_parent_conflict_with_primary_fails_closed() -> None:
    compiled = _adapter_compiled()
    reconciliation = _table(
        [
            _row("Lợi nhuận kế toán trước thuế", "100", "80"),
            _row("Chi phí thuế TNDN theo thuế suất", "20", "16"),
            _row("Điều chỉnh khác", "(1)", "(1)"),
            _row("Chi phí thuế TNDN hiện hành", "19", "15", kind="TOTAL"),
        ]
    )
    records, _unused_note, primary_page = _supplemental_records(
        [],
        primary_current=("90", "80"),
        primary_deferred=("10", "20"),
        primary_root=("100", "100"),
    )
    records[0]["page_json"] = _page([], tables=[reconciliation])
    records[1]["page_json"] = primary_page
    _cluster, candidate = _evaluate_supplemental_records(records, compiled=compiled)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["reasons"] == [
        "CONFLICTING_DIRECT_SUPPLEMENTAL_AND_PRIMARY_INCOME_TAX_PRESENTATIONS"
    ]


@pytest.mark.parametrize(
    "rows,reason",
    [
        (
            [
                _row("Lợi nhuận kế toán trước thuế", "100", "80"),
                _row("Lợi nhuận trước thuế", None, None),
            ],
            "SUPPLEMENTAL_DIRECT_ROLE_AXIS_NOT_UNIQUE:PROFIT_BEFORE_TAX",
        ),
        (
            [
                _row("Chi phí thuế thu nhập doanh nghiệp hoãn lại", "2", "1"),
                _row("Lợi ích thuế thu nhập hoãn lại", None, None),
            ],
            "SUPPLEMENTAL_DIRECT_ROLE_AXIS_NOT_UNIQUE:DEFERRED_TAX_NET",
        ),
        (
            [
                _row("Chi phí thuế TNDN hiện hành", "10", "8"),
                _row("Chi phí thuế TNDN trong kỳ", "không rõ", "1"),
            ],
            "SUPPLEMENTAL_CURRENT_TAX_PARENT_AXIS_NOT_UNIQUE",
        ),
    ],
)
def test_supplemental_role_uniqueness_counts_blank_or_invalid_surfaces(
    rows: list[dict[str, Any]], reason: str
) -> None:
    compiled = _adapter_compiled()
    records, _note_page, _primary_page_value = _supplemental_records(rows)
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[records[-1]], compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert cluster["reasons"] == [reason]


@pytest.mark.parametrize("unusable", [(None, None), ("không rõ", "1")])
def test_supplemental_reconciliation_cannot_skip_unusable_frontier_row(
    unusable: tuple[str | None, str | None],
) -> None:
    compiled = _adapter_compiled()
    records, _unused_note, primary_page = _supplemental_records([])
    records[0]["page_json"] = _page(
        [
            _row("Chi phí thuế TNDN theo thuế suất", "10", "20"),
            _row("Điều chỉnh chưa xác định", *unusable),
            _row("Chi phí thuế TNDN hiện hành", "10", "20", kind="TOTAL"),
        ]
    )
    records[1]["page_json"] = primary_page
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[records[-1]], compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert cluster["reasons"] == ["SUPPLEMENTAL_CURRENT_TAX_FRONTIER_NOT_COMPLETE"]


def test_supplemental_reconciliation_cannot_cross_group_boundary() -> None:
    compiled = _adapter_compiled()
    records, _unused_note, primary_page = _supplemental_records([])
    records[0]["page_json"] = _page(
        [
            _row("Chi phí thuế TNDN theo thuế suất", "20", "16"),
            _row("Nhóm thuế khác", None, None, kind="GROUP"),
            _row("Điều chỉnh thuế TNDN năm trước", "1", "2"),
            _row("Chi phí thuế TNDN hiện hành", "21", "18", kind="TOTAL"),
        ]
    )
    records[1]["page_json"] = primary_page
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[records[-1]], compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["reasons"] == ["SUPPLEMENTAL_CURRENT_TAX_FRONTIER_NOT_COMPLETE"]


@pytest.mark.parametrize(
    "duplicate_rows,role",
    [
        (
            [
                _row("Lợi nhuận kế toán trước thuế", "100", "80"),
                _row("Lợi nhuận trước thuế", "100", "80"),
            ],
            "PROFIT_BEFORE_TAX",
        ),
        (
            [
                _row("Chi phí thuế thu nhập doanh nghiệp hoãn lại", "2", "1"),
                _row("Lợi ích thuế thu nhập hoãn lại", "2", "1"),
            ],
            "DEFERRED_TAX_NET",
        ),
    ],
)
def test_duplicate_supplemental_direct_role_fails_closed(
    duplicate_rows: list[dict[str, Any]], role: str
) -> None:
    compiled = _adapter_compiled()
    records, _unused_note, primary_page = _supplemental_records([])
    records[0]["page_json"] = _page(duplicate_rows)
    records[1]["page_json"] = primary_page
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[records[-1]], compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert cluster["reasons"] == ["SUPPLEMENTAL_DIRECT_ROLE_AXIS_NOT_UNIQUE:" + role]


@pytest.mark.parametrize(
    "rows,reason",
    [
        (
            [
                _row("Chi phí thuế TNDN hiện hành", "7", "5"),
                _row("Chi phí thuế TNDN trong kỳ", "9", "6"),
            ],
            "SUPPLEMENTAL_CURRENT_TAX_PARENT_AXIS_NOT_UNIQUE",
        ),
        (
            [
                _row("Chi phí thuế TNDN hiện hành", "7", "5"),
                _row("Khoản khác", "1", "1"),
            ],
            "SUPPLEMENTAL_CURRENT_TAX_SINGLETON_FRONTIER_NOT_COMPLETE",
        ),
    ],
)
def test_supplemental_direct_current_parent_requires_unique_complete_frontier(
    rows: list[dict[str, Any]], reason: str
) -> None:
    compiled = _adapter_compiled()
    records, _unused_note, primary_page = _supplemental_records([])
    records[0]["page_json"] = _page(rows)
    records[1]["page_json"] = primary_page
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[records[-1]], compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert cluster["reasons"] == [reason]


def test_supplemental_hard_negative_owner_never_maps_deferred_tax_balance() -> None:
    compiled = _adapter_compiled()
    records, _unused_note, primary_page = _supplemental_records([])
    records[0]["page_json"] = _page(
        [_row("Chi phí thuế thu nhập doanh nghiệp hoãn lại", "7", "5")],
        owner="Tài sản thuế thu nhập hoãn lại - Thuế TNDN",
    )
    records[1]["page_json"] = primary_page
    cluster, candidate = _evaluate_supplemental_records(records, compiled=compiled)
    assert cluster["status"] == READY
    assert candidate["status"] == READY
    assert [mapping["role"] for mapping in candidate["mappings"]] == [
        "CURRENT_TAX_PARENT",
        "DEFERRED_TAX_NET",
        "FAMILY_ROOT_TOTAL",
    ]
    deferred = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "DEFERRED_TAX_NET"
    )
    assert deferred["source_refs"][0]["locator"]["page_json_version_id"] != VERSION_ID
    adapter = cluster["owner_receipt"]["income_tax_query_adapter_receipt"]
    assert adapter["supplemental_projection_receipts"] == []


def test_supplemental_unit_corroboration_never_overrides_explicit_unsupported_unit() -> None:
    compiled = _adapter_compiled()
    records, _unused_note, primary_page = _supplemental_records(
        [
            _row("Ngân hàng", "7", "5"),
            _row("Công ty TNHH Quản lý nợ và Khai thác tài sản", "3", "3"),
            _row("Cộng", "10", "8", kind="TOTAL"),
        ]
    )
    note_table = records[0]["page_json"]["sections"][0]["tables"][0]
    note_table["unit_exact"] = "Nghìn đồng"
    for column in note_table["columns"]:
        column["header_path_exact"] = [column["header_path_exact"][0]]
    records[1]["page_json"] = primary_page
    controls = _primary_record(
        _primary_unit_control_page(statement_type="BALANCE_SHEET", unit="Triệu đồng"),
        page_json_version_id="gfpstorev1:json:" + "e" * 64,
        physical_page=3,
        selected_page_ordinal=3,
    )
    records.append(controls)
    cluster, candidate = _evaluate_supplemental_records(records, compiled=compiled)
    assert cluster["status"] == READY
    assert candidate["status"] == READY
    adapter = cluster["owner_receipt"]["income_tax_query_adapter_receipt"]
    assert adapter["supplemental_projection_receipts"] == []
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "CURRENT_TAX_PARENT",
        "DEFERRED_TAX_NET",
        "FAMILY_ROOT_TOTAL",
    }


@pytest.mark.parametrize(
    "key,value",
    [
        ("adapter_spec_sha256", "f" * 64),
        ("adapter_format_version", "TAMPERED"),
        ("rule", "TAMPERED"),
        ("repair_receipt_ids", ["gjitfav1:repair:" + "f" * 64]),
    ],
)
def test_self_resealed_adapter_metadata_tamper_is_rejected(key: str, value: Any) -> None:
    compiled = _adapter_compiled()
    records, _note_page, _primary_page_value = _supplemental_records(
        [
            _row("Ngân hàng", "7", "5"),
            _row("Công ty TNHH Quản lý nợ và Khai thác tài sản", "3", "3"),
            _row("Cộng", "10", "8", kind="TOTAL"),
        ]
    )
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[records[-1]], compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    receipt = build_gemini_json_income_tax_region_query_receipt_v1(
        cluster["component_regions"], cluster=cluster
    )
    tampered = deepcopy(receipt)
    tampered["adapter_receipt"][key] = value
    adapter_material = {
        item_key: item_value
        for item_key, item_value in tampered["adapter_receipt"].items()
        if item_key != "receipt_id"
    }
    tampered["adapter_receipt"]["receipt_id"] = (
        "gjitfav1:query:" + canonical_json_sha256_v1(adapter_material)
    )
    outer_material = {
        item_key: item_value
        for item_key, item_value in tampered.items()
        if item_key != "query_receipt_id"
    }
    tampered["query_receipt_id"] = (
        "gjitfav1:query-receipt:" + canonical_json_sha256_v1(outer_material)
    )
    with pytest.raises(GeminiJsonIncomeTaxFamilyV1Error):
        evaluate_gemini_json_income_tax_family_cluster_v1(
            regions=cluster["component_regions"],
            page_json_by_version={
                record["page_json_version_id"]: record["page_json"] for record in records
            },
            selected_page_axis=[
                {item_key: item_value for item_key, item_value in record.items() if item_key != "page_json"}
                for record in records
            ],
            compiled_specs=compiled,
            query_receipt=tampered,
        )


def test_self_resealed_adapter_removal_cannot_drop_usable_primary_source() -> None:
    compiled = _adapter_compiled()
    note_page = _page(_canonical_rows())
    note_record = _record(note_page)
    primary_page = _primary_page(
        _primary_tax_rows(current=("20", "15"), deferred=("1", "2"), root=("21", "17"))
    )
    primary_record = _primary_record(
        primary_page,
        page_json_version_id="gfpstorev1:json:" + "d" * 64,
        physical_page=2,
        selected_page_ordinal=2,
    )
    records = [note_record, primary_record]
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    receipt = build_gemini_json_income_tax_region_query_receipt_v1(
        cluster["component_regions"], cluster=cluster
    )
    tampered = deepcopy(receipt)
    tampered["adapter_receipt"] = None
    material = {
        key: value for key, value in tampered.items() if key != "query_receipt_id"
    }
    tampered["query_receipt_id"] = (
        "gjitfav1:query-receipt:" + canonical_json_sha256_v1(material)
    )
    with pytest.raises(GeminiJsonIncomeTaxFamilyV1Error):
        evaluate_gemini_json_income_tax_family_cluster_v1(
            regions=cluster["component_regions"],
            page_json_by_version={
                note_record["page_json_version_id"]: note_page,
                primary_record["page_json_version_id"]: primary_page,
            },
            selected_page_axis=[
                {key: value for key, value in record.items() if key != "page_json"}
                for record in records
            ],
            compiled_specs=compiled,
            query_receipt=tampered,
        )


def test_supplemental_query_receipt_rejects_source_value_tamper() -> None:
    compiled = _adapter_compiled()
    records, _note_page, _primary_page_value = _supplemental_records(
        [
            _row("Ngân hàng", "7", "5"),
            _row("Công ty TNHH Quản lý nợ và Khai thác tài sản", "3", "3"),
            _row("Cộng", "10", "8", kind="TOTAL"),
        ]
    )
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[records[-1]], compiled_specs=compiled
    )
    cluster = recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    tampered_records = deepcopy(records)
    tampered_records[0]["page_json"]["sections"][0]["tables"][0]["rows"][0][
        "values_exact"
    ][0] = "8"
    with pytest.raises(GeminiJsonIncomeTaxFamilyV1Error):
        evaluate_gemini_json_income_tax_family_cluster_v1(
            regions=cluster["component_regions"],
            page_json_by_version={
                record["page_json_version_id"]: record["page_json"]
                for record in tampered_records
            },
            selected_page_axis=[
                {key: value for key, value in record.items() if key != "page_json"}
                for record in tampered_records
            ],
            compiled_specs=compiled,
            query_receipt=build_gemini_json_income_tax_region_query_receipt_v1(
                cluster["component_regions"], cluster=cluster
            ),
        )
