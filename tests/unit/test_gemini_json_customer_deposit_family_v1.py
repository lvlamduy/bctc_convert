from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_customer_deposit_family_v1 import (
    READY,
    UNRESOLVED,
    GeminiJsonCustomerDepositFamilyV1Error,
    _apply_authenticated_source_repairs,
    bind_gemini_json_customer_deposit_source_repairs_v1,
    build_gemini_json_customer_deposit_region_query_receipt_v1,
    coalesce_gemini_json_customer_deposit_document_v1,
    compile_gemini_json_customer_deposit_family_specs_v1,
    evaluate_gemini_json_customer_deposit_family_cluster_v1,
    validate_gemini_json_customer_deposit_family_candidate_replay_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT = "gfpstorev1:document:" + "b" * 64
SOURCE_SHA = "c" * 64


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_text(encoding="utf-8"))


def _compiled() -> dict:
    return compile_gemini_json_customer_deposit_family_specs_v1(
        _json("tm-customer-deposit-classification-topology-v1.json"),
        _json("tm-customer-deposit-classification-evaluation-v1.json"),
        _json("tm-customer-deposit-classification-schema-binding-v1.json"),
    )


def test_schema_bindings_remain_inside_customer_deposit_schema_branches() -> None:
    graph = {
        item["schema_id"]: item
        for item in (
            json.loads(line)
            for line in (ROOT / "reference/schemas/schema_graph.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        )
    }
    compiled = _compiled()
    type_roles = set(compiled["bindings"]) & set(
        (
            "NO_TERM",
            "NO_TERM_VND",
            "NO_TERM_FOREIGN",
            "TERM",
            "TERM_VND",
            "TERM_FOREIGN",
            "SAVINGS",
            "SAVINGS_VND",
            "SAVINGS_FOREIGN",
            "ESCROW",
            "ESCROW_VND",
            "ESCROW_FOREIGN",
            "DEDICATED",
            "DEDICATED_VND",
            "DEDICATED_FOREIGN",
            "OTHER_PAYMENT_GUARANTEE",
            "OTHER_PAYMENT_GUARANTEE_VND",
            "OTHER_PAYMENT_GUARANTEE_FOREIGN",
        )
    )
    customer_roles = set(compiled["bindings"]) - type_roles

    assert {graph[compiled["bindings"][role]]["parent_id"] for role in type_roles} == {
        1056
    }
    assert {
        graph[compiled["bindings"][role]]["parent_id"] for role in customer_roles
    } == {1075}


def _source_repair_spec(
    *,
    column_ordinal: int = 1,
    source_logical_name: str = "fixture.pdf",
) -> dict:
    repair = {
        "after_exact": "-",
        "before_exact": None,
        "crop_evidence": {
            "bbox_pixels_xyxy": [0, 0, 10, 10],
            "pixel_height": 10,
            "pixel_width": 10,
            "rgb_sha256": "d" * 64,
        },
        "locator": {
            "column_ordinal": column_ordinal,
            "page_json_version_id": "gfpstorev1:json:" + f"{1:064x}",
            "physical_page": 1,
            "row_ordinal": 5,
            "section_id": "s1",
            "table_id": "t1",
        },
        "observed_pdf_glyph": "-",
        "render": {
            "image_sha256": "e" * 64,
            "image_size_bytes": 100,
            "media_type": "image/png",
            "physical_page": 1,
            "pixel_height": 20,
            "pixel_width": 20,
            "render_dpi": 300,
            "render_receipt_sha256": "f" * 64,
        },
        "repair_kind": "MONEY_CELL_VISIBLE_DASH",
        "source": {
            "source_logical_name": source_logical_name,
            "source_sha256": SOURCE_SHA,
            "source_size_bytes": 100,
        },
    }
    repair["repair_id"] = "gjfcdav1:source-repair:" + canonical_json_sha256_v1(repair)
    repairs = [repair]
    return {
        "family_id": "CUSTOMER_DEPOSIT_CLASSIFICATION",
        "format_version": "GEMINI_JSON_CUSTOMER_DEPOSIT_AUTHENTICATED_SOURCE_REPAIR_SPEC_V1",
        "policy": "ONLY_PDF_VISIBLE_ACCOUNTING_DASH_MISSING_AS_NULL_NO_BLANK_ZERO_INFERENCE",
        "render_contract": {
            "alpha": False,
            "colorspace": "RGB",
            "format": "PNG",
            "render_dpi": 300,
            "renderer": "BCTC_AI_FULL_PDF_PAGE_RENDER_V1_PYMUPDF",
        },
        "repair_axis_sha256": canonical_json_sha256_v1(repairs),
        "repairs": repairs,
    }


def test_customer_unit_helper_does_not_restrict_other_hierarchical_families() -> None:
    compiled = compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-government-sbv-liabilities-topology-v1.json"),
        _json("tm-government-sbv-liabilities-evaluation-v1.json"),
        _json("tm-government-sbv-liabilities-schema-binding-v1.json"),
    )
    assert {
        item["canonical_unit"] for item in compiled["unit_bindings"] if item["accepted"]
    } == {"MILLION_VND", "VND"}


def _columns(*, unit: bool = True) -> list[dict]:
    suffix = ["Triệu đồng"] if unit else []
    return [
        {"header_path_exact": ["31/12/2025", *suffix], "value_kind": "MONEY"},
        {"header_path_exact": ["31/12/2024", *suffix], "value_kind": "MONEY"},
    ]


def _row(
    label: str | None,
    values: list[str | None],
    kind: str = "ITEM",
    hierarchy: list[str | None] | None = None,
) -> dict:
    return {
        "hierarchy_path_exact": [label] if hierarchy is None else hierarchy,
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _ordinary_type(*, nested_savings: bool = False, unit: str | None = "Triệu đồng") -> dict:
    if nested_savings:
        no_term = ["15", "14"]
        savings_hierarchy = ["Tiền gửi không kỳ hạn", "Tiền gửi tiết kiệm không kỳ hạn"]
    else:
        no_term = ["10", "9"]
        savings_hierarchy = ["Tiền gửi tiết kiệm không kỳ hạn"]
    return {
        "columns": _columns(unit=unit is not None),
        "continuation": "NONE",
        "rows": [
            _row("Tiền gửi không kỳ hạn", no_term),
            _row("Tiền gửi có kỳ hạn", ["20", "18"]),
            _row(
                "Tiền gửi tiết kiệm không kỳ hạn",
                ["5", "5"],
                hierarchy=savings_hierarchy,
            ),
            _row("Tiền gửi ký quỹ", ["3", "2"]),
            _row("Tiền gửi vốn chuyên dùng", ["2", "1"]),
            _row(None, ["40", "35"], "TOTAL", [None]),
        ],
        "title_exact": "Theo loại tiền gửi",
        "unit_exact": unit,
    }


def _customer(*, mismatch: bool = False) -> dict:
    return {
        "columns": _columns(),
        "continuation": "NONE",
        "rows": [
            _row("Công ty Nhà nước", ["10", "9"]),
            _row("Hộ kinh doanh, cá nhân", ["30", "26"]),
            _row(None, ["40", "38" if mismatch else "35"], "TOTAL", [None]),
        ],
        "title_exact": "Theo đối tượng khách hàng và loại hình doanh nghiệp",
        "unit_exact": "Triệu đồng",
    }


def _hierarchical_customer(*, parent_comparative: str = "35-", child_comparative: str = "26") -> dict:
    return {
        "columns": _columns(),
        "continuation": "NONE",
        "rows": [
            _row("Tiền gửi của TCKT", ["30", parent_comparative], "GROUP"),
            _row(
                "Doanh nghiệp Nhà nước",
                ["10", "9"],
                hierarchy=["Tiền gửi của TCKT", "Doanh nghiệp Nhà nước"],
            ),
            _row(
                "Công ty TNHH",
                ["20", child_comparative],
                hierarchy=["Tiền gửi của TCKT", "Công ty TNHH"],
            ),
            _row(None, ["30", "35"], "TOTAL", [None]),
        ],
        "title_exact": "Theo đối tượng khách hàng và loại hình doanh nghiệp",
        "unit_exact": "Triệu đồng",
    }


def _nested_savings_currency_type() -> dict:
    return {
        "columns": _columns(),
        "continuation": "NONE",
        "rows": [
            _row("Tiền gửi không kỳ hạn", ["5", "4"]),
            _row(
                "Tiền gửi tiết kiệm không kỳ hạn bằng VND",
                ["3", "2"],
                hierarchy=["Tiền gửi không kỳ hạn", "Tiền gửi tiết kiệm không kỳ hạn bằng VND"],
            ),
            _row(
                "Tiền gửi tiết kiệm không kỳ hạn bằng ngoại tệ",
                ["2", "2"],
                hierarchy=[
                    "Tiền gửi không kỳ hạn",
                    "Tiền gửi tiết kiệm không kỳ hạn bằng ngoại tệ",
                ],
            ),
            _row("Tiền gửi có kỳ hạn", ["5", "4"]),
            _row(
                "Tiền gửi tiết kiệm có kỳ hạn bằng VND",
                ["4", "3"],
                hierarchy=["Tiền gửi có kỳ hạn", "Tiền gửi tiết kiệm có kỳ hạn bằng VND"],
            ),
            _row(
                "Tiền gửi tiết kiệm có kỳ hạn bằng ngoại tệ",
                ["1", "1"],
                hierarchy=[
                    "Tiền gửi có kỳ hạn",
                    "Tiền gửi tiết kiệm có kỳ hạn bằng ngoại tệ",
                ],
            ),
            _row("Tiền gửi vốn chuyên dùng", ["0", "0"]),
            _row(None, ["10", "8"], "TOTAL", [None]),
        ],
        "title_exact": "Theo loại tiền gửi",
        "unit_exact": "Triệu đồng",
    }


def _combined_savings_currency_type() -> dict:
    return {
        "columns": _columns(),
        "continuation": "NONE",
        "rows": [
            _row("Tiền gửi không kỳ hạn", ["10", "9"]),
            _row("Tiền gửi có kỳ hạn", ["20", "18"]),
            _row("Tiền gửi tiết kiệm", ["30", "28"], "SUBTOTAL"),
            _row(
                "- Bằng VND",
                ["28", "26"],
                hierarchy=["Tiền gửi tiết kiệm", "- Bằng VND"],
            ),
            _row(
                "- Bằng ngoại tệ",
                ["2", "2"],
                hierarchy=["Tiền gửi tiết kiệm", "- Bằng ngoại tệ"],
            ),
            _row("Tiền gửi ký quỹ", ["3", "2"]),
            _row("Tiền gửi vốn chuyên dùng", ["2", "1"]),
            _row(None, ["65", "58"], "TOTAL", [None]),
        ],
        "title_exact": "Theo loại tiền gửi",
        "unit_exact": "Triệu đồng",
    }


def _split_type_tables(*, conflict: str | None = None) -> tuple[dict, dict]:
    first = {
        "columns": _columns(),
        "continuation": "CONTINUES_ON_NEXT_PAGE",
        "rows": [
            _row("Tiền gửi không kỳ hạn", ["10", "9"]),
            _row("Tiền gửi có kỳ hạn", ["20", "18"]),
            _row("Tiền gửi tiết kiệm", ["5", "5"]),
        ],
        "title_exact": "Theo loại tiền gửi",
        "unit_exact": "Triệu đồng",
    }
    second = {
        "columns": copy.deepcopy(_columns()),
        "continuation": "CONTINUES_FROM_PREVIOUS_PAGE",
        "rows": [
            _row("Tiền gửi ký quỹ", ["3", "2"]),
            _row("Tiền gửi vốn chuyên dùng", ["2", "1"]),
            _row(None, ["40", "35"], "TOTAL", [None]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    if conflict == "PERIOD":
        second["columns"][1]["header_path_exact"] = ["31/12/2023", "Triệu đồng"]
    elif conflict == "UNIT":
        second["unit_exact"] = "Nghìn đồng"
    return first, second


def _subtotal_customer() -> dict:
    return {
        "columns": _columns(),
        "continuation": "NONE",
        "rows": [
            _row("Tổ chức kinh tế", [None, None], "GROUP"),
            _row(
                "Doanh nghiệp Nhà nước",
                ["10", "9"],
                hierarchy=["Tổ chức kinh tế", "Doanh nghiệp Nhà nước"],
            ),
            _row(
                "Các đối tượng khác",
                ["20", "17"],
                hierarchy=["Tổ chức kinh tế", "Các đối tượng khác"],
            ),
            _row(None, ["30", "26"], "SUBTOTAL", ["Tổ chức kinh tế", None]),
            _row("Hộ kinh doanh, cá nhân", ["10", "9"]),
            _row(None, ["40", "35"], "TOTAL", [None]),
        ],
        "title_exact": "Theo đối tượng khách hàng và loại hình doanh nghiệp",
        "unit_exact": "Triệu đồng",
    }


def _stacked_type(period: str, *, semantic: str | None = None, comparative: bool = False) -> dict:
    if comparative:
        rows = [
            _row("Tiền gửi không kỳ hạn", ["9", "1", "10"]),
            _row("Tiền gửi có kỳ hạn", ["18", "2", "20"]),
            _row("Tiền gửi vốn chuyên dùng", ["1", "0", "1"]),
            _row(None, ["28", "3", "31"], "TOTAL", [None]),
        ]
    else:
        rows = [
            _row("Tiền gửi không kỳ hạn", ["10", "1", "11"]),
            _row("Tiền gửi có kỳ hạn", ["20", "2", "22"]),
            _row("Tiền gửi vốn chuyên dùng", ["3", "0", "3"]),
            _row(None, ["33", "3", "36"], "TOTAL", [None]),
        ]
    title = period if semantic is None else f"{period} — {semantic}"
    return {
        "columns": [
            {"header_path_exact": ["VND", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Ngoại tệ", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Tổng cộng", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": rows,
        "title_exact": title,
        "unit_exact": "Triệu đồng",
    }


def _page(*tables: dict, title: str = "Tiền gửi của khách hàng") -> dict:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": list(tables),
                "title_exact": title,
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _record(page: dict, ordinal: int) -> dict:
    return {
        "document_id": DOCUMENT,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": "gfpstorev1:json:" + f"{ordinal:064x}",
        "physical_page": ordinal,
        "selected_page_ordinal": ordinal,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA,
    }


def _evaluate(records: list[dict]) -> tuple[dict, dict]:
    compiled = _compiled()
    cluster = coalesce_gemini_json_customer_deposit_document_v1(
        page_records=records, compiled_specs=compiled
    )
    assert cluster["status"] == READY
    regions = cluster["component_regions"]
    candidate = evaluate_gemini_json_customer_deposit_family_cluster_v1(
        regions=regions,
        page_json_by_version={item["page_json_version_id"]: item["page_json"] for item in records},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_customer_deposit_region_query_receipt_v1(regions),
    )
    return cluster, candidate


def test_top_level_savings_is_additive_but_nested_savings_is_not() -> None:
    _cluster, top_level = _evaluate([_record(_page(_ordinary_type()), 1)])
    _cluster, nested = _evaluate([_record(_page(_ordinary_type(nested_savings=True)), 1)])
    assert top_level["status"] == READY
    assert nested["status"] == READY
    assert {item["role"] for item in top_level["mappings"]} == {
        "NO_TERM",
        "TERM",
        "SAVINGS",
        "ESCROW",
        "DEDICATED",
    }
    assert top_level["closure_receipt"]["equations"][-1]["component_roles"] == [
        "NO_TERM",
        "TERM",
        "ESCROW",
        "DEDICATED",
        "SAVINGS_COMBINED",
    ]
    assert nested["closure_receipt"]["equations"][-1]["component_roles"] == [
        "NO_TERM",
        "TERM",
        "ESCROW",
        "DEDICATED",
    ]


def test_nested_currency_savings_rows_derive_the_schema_savings_total() -> None:
    _cluster, candidate = _evaluate([_record(_page(_nested_savings_currency_type()), 1)])
    by_role = {item["role"]: item for item in candidate["mappings"]}
    assert candidate["status"] == READY
    assert [cell["coefficient"] for cell in by_role["SAVINGS"]["values"]] == [10, 8]
    assert [cell["coefficient"] for cell in by_role["SAVINGS_VND"]["values"]] == [7, 5]
    assert [cell["coefficient"] for cell in by_role["SAVINGS_FOREIGN"]["values"]] == [3, 3]


def test_source_visible_combined_savings_maps_rnid_1063_without_allocating_subtypes() -> None:
    _cluster, candidate = _evaluate([_record(_page(_combined_savings_currency_type()), 1)])
    by_role = {item["role"]: item for item in candidate["mappings"]}

    assert candidate["status"] == READY
    assert by_role["SAVINGS"]["report_norm_id"] == 1063
    assert [cell["coefficient"] for cell in by_role["SAVINGS"]["values"]] == [30, 28]
    assert [cell["coefficient"] for cell in by_role["SAVINGS_VND"]["values"]] == [28, 26]
    assert [cell["coefficient"] for cell in by_role["SAVINGS_FOREIGN"]["values"]] == [2, 2]
    assert not {"SAVINGS_NO_TERM", "SAVINGS_TERM"} & set(by_role)


def test_adjacent_split_row_table_is_composed_with_exact_row_bound_receipts() -> None:
    first, second = _split_type_tables()
    records = [_record(_page(first), 1), _record(_page(second), 2)]
    cluster, candidate = _evaluate(records)

    assert cluster["status"] == READY
    assert candidate["status"] == READY
    assert [region["row_start_ordinal"] for region in cluster["component_regions"]] == [1, 1]
    assert all(
        region["fragment_layout"] == "ROW_CONTINUATION"
        for region in cluster["component_regions"]
    )
    assert candidate["closure_receipt"]["type_currency_view"]["layout"] == (
        "ROW_CONTINUATION_FRAGMENTS_X_TWO_PERIOD_COLUMNS"
    )


@pytest.mark.parametrize("conflict", ["PERIOD", "UNIT"])
def test_split_row_table_rejects_conflicting_period_or_unit(conflict: str) -> None:
    first, second = _split_type_tables(conflict=conflict)
    cluster = coalesce_gemini_json_customer_deposit_document_v1(
        page_records=[_record(_page(first), 1), _record(_page(second), 2)],
        compiled_specs=_compiled(),
    )

    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert "OWNER_BOUND_TYPE_COMPONENT_INCOMPLETE" in cluster["reasons"]


def test_one_physical_table_is_split_into_type_and_customer_subtotal_views() -> None:
    mixed = _combined_savings_currency_type()
    mixed["rows"].extend(_subtotal_customer()["rows"])
    mixed["title_exact"] = "Tiền gửi của khách hàng"
    cluster, candidate = _evaluate([_record(_page(mixed), 1)])
    by_role = {item["role"]: item for item in candidate["mappings"]}

    assert candidate["status"] == READY
    assert [(item["component_role"], item["row_start_ordinal"], item["row_end_ordinal"]) for item in cluster["component_regions"]] == [
        ("TYPE_CURRENCY", 1, 8),
        ("CUSTOMER_TYPE", 9, 14),
    ]
    assert [cell["coefficient"] for cell in by_role["CUSTOMER_TCKT"]["values"]] == [30, 26]
    assert by_role["CUSTOMER_TCKT"]["report_norm_id"] == 5977
    customer_inventory = candidate["closure_receipt"]["customer_view"]["source_inventory"]
    assert next(item for item in customer_inventory if item["row_ordinal"] == 9)[
        "disposition"
    ] == "STRUCTURAL_CUSTOMER_ROLE_WITHOUT_VISIBLE_VALUE"


def test_two_stacked_period_tables_are_bound_without_bank_or_page_rules() -> None:
    records = [
        _record(
            _page(
                _stacked_type("31/12/2025"),
                _stacked_type("31/12/2024", comparative=True),
            ),
            1,
        )
    ]
    cluster, candidate = _evaluate(records)
    by_role = {item["role"]: item for item in candidate["mappings"]}
    assert (
        candidate["closure_receipt"]["type_currency_view"]["layout"]
        == "TWO_STACKED_PERIOD_TABLES_X_CURRENCY_COLUMNS"
    )
    assert candidate["status"] == READY
    assert [cell["coefficient"] for cell in by_role["NO_TERM"]["values"]] == [11, 10]
    assert [cell["coefficient"] for cell in by_role["TERM_FOREIGN"]["values"]] == [2, 2]


def test_stacked_date_and_semantic_period_conflict_is_unresolved() -> None:
    records = [
        _record(
            _page(
                _stacked_type("31/12/2025", semantic="Kỳ trước"),
                _stacked_type("31/12/2024", comparative=True),
            ),
            1,
        )
    ]
    cluster, candidate = _evaluate(records)
    assert candidate["status"] == UNRESOLVED
    assert "STACKED_DATE_AND_SEMANTIC_PERIOD_EVIDENCE_CONFLICT:fragment_1" in candidate["reasons"]
    assert candidate["mappings"] == []


def test_adjacent_stacked_period_continuation_uses_typed_evidence() -> None:
    comparative = _stacked_type("31/12/2024", comparative=True)
    comparative["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"
    records = [
        _record(_page(_stacked_type("31/12/2025")), 1),
        _record(_page(comparative, title="Tiền gửi của khách hàng (tiếp theo)"), 2),
    ]
    cluster, candidate = _evaluate(records)
    assert cluster["status"] == READY
    assert candidate["status"] == READY
    assert len(cluster["component_regions"]) == 2


def test_unconsumed_declared_role_table_inside_owner_fence_is_unresolved() -> None:
    mixed = {
        "columns": _columns(),
        "continuation": "NONE",
        "rows": [
            _row("Tiền gửi vốn chuyên dùng", ["1", "1"]),
            _row("Khoản mục ngoại lai", ["2", "2"]),
        ],
        "title_exact": "Bảng bổ sung",
        "unit_exact": "Triệu đồng",
    }
    compiled = _compiled()
    cluster = coalesce_gemini_json_customer_deposit_document_v1(
        page_records=[_record(_page(_ordinary_type(), mixed), 1)],
        compiled_specs=compiled,
    )
    assert cluster["status"] == UNRESOLVED
    assert "UNCONSUMED_DECLARED_ROLE_TABLE_WITHIN_OWNER_FENCE" in cluster["reasons"]
    assert any(
        item["disposition"] == "UNCONSUMED_DECLARED_ROLE_TABLE_WITHIN_OWNER_FENCE"
        for item in cluster["declared_role_table_inventory"]
    )


def test_selected_component_with_ambiguous_row_role_is_clustered_as_unresolved() -> None:
    ambiguous_customer = _customer()
    label = "Hợp tác xã và hộ kinh doanh, cá nhân"
    ambiguous_customer["rows"][1]["label_exact"] = label
    ambiguous_customer["rows"][1]["hierarchy_path_exact"] = [label]
    cluster = coalesce_gemini_json_customer_deposit_document_v1(
        page_records=[_record(_page(_ordinary_type(), ambiguous_customer), 1)],
        compiled_specs=_compiled(),
    )

    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert cluster["reasons"] == [
        "SELECTED_COMPONENT_CLASSIFICATION_UNRESOLVED",
        "SOURCE_ROW_ROLE_MATCH_IS_AMBIGUOUS",
    ]
    ambiguous_inventory = [
        item
        for item in cluster["declared_role_table_inventory"]
        if item["classification"]["ambiguous_row_ordinals"]
    ]
    assert len(ambiguous_inventory) == 1
    assert ambiguous_inventory[0]["classification"]["component_role"] == "CUSTOMER_TYPE"
    assert ambiguous_inventory[0]["disposition"] == (
        "SELECTED_COMPONENT_CLASSIFICATION_UNRESOLVED"
    )


def test_evaluator_rejects_ambiguous_row_role_tamper_after_clean_query() -> None:
    clean_page = _page(_ordinary_type(), _customer())
    record = _record(clean_page, 1)
    compiled = _compiled()
    cluster = coalesce_gemini_json_customer_deposit_document_v1(
        page_records=[record], compiled_specs=compiled
    )
    assert cluster["status"] == READY

    tampered_page = copy.deepcopy(clean_page)
    label = "Doanh nghiệp tư nhân và công ty hợp danh"
    tampered_row = tampered_page["sections"][0]["tables"][1]["rows"][1]
    tampered_row["label_exact"] = label
    tampered_row["hierarchy_path_exact"] = [label]
    with pytest.raises(
        GeminiJsonCustomerDepositFamilyV1Error,
        match="source fragment classification drifted",
    ):
        evaluate_gemini_json_customer_deposit_family_cluster_v1(
            regions=cluster["component_regions"],
            page_json_by_version={record["page_json_version_id"]: tampered_page},
            compiled_specs=compiled,
            query_receipt=build_gemini_json_customer_deposit_region_query_receipt_v1(
                cluster["component_regions"]
            ),
        )


def test_adjacent_primary_statement_continuation_binds_unitless_owner_total() -> None:
    statement_columns = [
        {"header_path_exact": ["Số dư cuối quý", "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": ["Số dư đầu năm", "Triệu đồng"], "value_kind": "MONEY"},
    ]
    detail = _ordinary_type(unit=None)
    detail["columns"] = [
        {"header_path_exact": ["Cuối kỳ"], "value_kind": "MONEY"},
        {"header_path_exact": ["Đầu kỳ"], "value_kind": "MONEY"},
    ]
    unit_carrier = {
        "columns": statement_columns,
        "continuation": "CONTINUES_ON_NEXT_PAGE",
        "rows": [_row("Tài sản khác", ["1", "1"])],
        "title_exact": "Báo cáo tình hình tài chính",
        "unit_exact": "Triệu đồng",
    }
    owner_continuation = {
        "columns": [
            {"header_path_exact": ["Số dư cuối quý"], "value_kind": "MONEY"},
            {"header_path_exact": ["Số dư đầu năm"], "value_kind": "MONEY"},
        ],
        "continuation": "CONTINUES_FROM_PREVIOUS_PAGE",
        "rows": [_row("Tiền gửi của khách hàng", ["40", "35"])],
        "title_exact": "Báo cáo tình hình tài chính (tiếp theo)",
        "unit_exact": None,
    }
    carrier_page = _page(unit_carrier, title="Báo cáo tình hình tài chính")
    carrier_page["status"] = "PRIMARY_FINANCIAL_STATEMENT"
    owner_page = _page(owner_continuation, title="Báo cáo tình hình tài chính")
    owner_page["status"] = "PRIMARY_FINANCIAL_STATEMENT"
    records = [
        _record(carrier_page, 1),
        _record(owner_page, 2),
        _record(_page(detail), 3),
    ]
    cluster, candidate = _evaluate(records)
    unit = candidate["closure_receipt"]["type_currency_view"]["unit_axis"]

    assert candidate["status"] == READY
    assert {item["unit"] for item in candidate["mappings"]} == {"MILLION_VND"}
    assert unit["source"] == "DOCUMENT_OWNER_ROW_EXACT_VALUE_PERIOD_UNIT_CORROBORATION"
    owner_evidence = unit["document_unit_context_evidence"]["evidence"]
    assert [item["source_kind"] for item in owner_evidence] == [
        "ADJACENT_PRIMARY_STATEMENT_CONTINUATION_UNIT_CUSTOMER_DEPOSIT_OWNER_ROW"
    ]
    reordered = {
        records[1]["page_json_version_id"]: records[1]["page_json"],
        records[0]["page_json_version_id"]: records[0]["page_json"],
        records[2]["page_json_version_id"]: records[2]["page_json"],
    }
    with pytest.raises(
        GeminiJsonCustomerDepositFamilyV1Error,
        match="does not replay exactly",
    ):
        validate_gemini_json_customer_deposit_family_candidate_replay_v1(
            candidate,
            regions=cluster["component_regions"],
            page_json_by_version=reordered,
            compiled_specs=_compiled(),
            query_receipt=build_gemini_json_customer_deposit_region_query_receipt_v1(
                cluster["component_regions"]
            ),
        )


def test_statement_unit_carryover_rejects_nonadjacent_or_value_tampered_owner() -> None:
    statement_columns = [
        {"header_path_exact": ["Số dư cuối quý", "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": ["Số dư đầu năm", "Triệu đồng"], "value_kind": "MONEY"},
    ]
    detail = _ordinary_type(unit=None)
    detail["columns"] = [
        {"header_path_exact": ["Cuối kỳ"], "value_kind": "MONEY"},
        {"header_path_exact": ["Đầu kỳ"], "value_kind": "MONEY"},
    ]
    unit_carrier = {
        "columns": statement_columns,
        "continuation": "CONTINUES_ON_NEXT_PAGE",
        "rows": [_row("Tài sản khác", ["1", "1"])],
        "title_exact": "Báo cáo tình hình tài chính",
        "unit_exact": "Triệu đồng",
    }
    owner_continuation = {
        "columns": [
            {"header_path_exact": ["Số dư cuối quý"], "value_kind": "MONEY"},
            {"header_path_exact": ["Số dư đầu năm"], "value_kind": "MONEY"},
        ],
        "continuation": "CONTINUES_FROM_PREVIOUS_PAGE",
        "rows": [_row("Tiền gửi của khách hàng", ["41", "35"])],
        "title_exact": "Báo cáo tình hình tài chính (tiếp theo)",
        "unit_exact": None,
    }
    carrier_page = _page(unit_carrier, title="Báo cáo tình hình tài chính")
    carrier_page["status"] = "PRIMARY_FINANCIAL_STATEMENT"
    owner_page = _page(owner_continuation, title="Báo cáo tình hình tài chính")
    owner_page["status"] = "PRIMARY_FINANCIAL_STATEMENT"
    _cluster, value_tamper = _evaluate(
        [
            _record(carrier_page, 1),
            _record(owner_page, 2),
            _record(_page(detail), 3),
        ]
    )
    assert value_tamper["status"] == UNRESOLVED
    assert "MONEY_UNIT_NOT_EXACTLY_RESOLVED" in value_tamper["reasons"]

    gap_page = _page(title="Thuyết minh khác")
    gap_page["status"] = "PRIMARY_FINANCIAL_STATEMENT"
    owner_continuation["rows"][0]["values_exact"] = ["40", "35"]
    _cluster, nonadjacent = _evaluate(
        [
            _record(carrier_page, 1),
            _record(gap_page, 2),
            _record(owner_page, 3),
            _record(_page(detail), 4),
        ]
    )
    assert nonadjacent["status"] == UNRESOLVED
    assert "MONEY_UNIT_NOT_EXACTLY_RESOLVED" in nonadjacent["reasons"]


def test_other_payment_guarantee_and_currency_children_map_schema_1072_to_1074() -> None:
    table = _ordinary_type()
    table["rows"][-1]["values_exact"] = ["45", "39"]
    table["rows"][2:3] = [
        _row("Tiền gửi tiết kiệm không kỳ hạn", [None, None], "GROUP"),
        _row(
            "Bằng VND",
            ["1", "1"],
            hierarchy=["Tiền gửi tiết kiệm không kỳ hạn", "Bằng VND"],
        ),
        _row(
            "Bằng ngoại tệ",
            ["1", "1"],
            hierarchy=["Tiền gửi tiết kiệm không kỳ hạn", "Bằng ngoại tệ"],
        ),
        _row("Tiền gửi tiết kiệm có kỳ hạn", [None, None], "GROUP"),
        _row(
            "Bằng VND",
            ["2", "2"],
            hierarchy=["Tiền gửi tiết kiệm có kỳ hạn", "Bằng VND"],
        ),
        _row(
            "Bằng ngoại tệ",
            ["1", "1"],
            hierarchy=["Tiền gửi tiết kiệm có kỳ hạn", "Bằng ngoại tệ"],
        ),
    ]
    table["rows"][-1:-1] = [
        _row("Tiền gửi đảm bảo thanh toán khác", [None, None], "GROUP"),
        _row(
            "Bằng VND",
            ["4", "3"],
            hierarchy=["Tiền gửi đảm bảo thanh toán khác", "Bằng VND"],
        ),
        _row(
            "Bằng ngoại tệ",
            ["1", "1"],
            hierarchy=["Tiền gửi đảm bảo thanh toán khác", "Bằng ngoại tệ"],
        ),
    ]
    _cluster, candidate = _evaluate([_record(_page(table), 1)])
    by_role = {item["role"]: item for item in candidate["mappings"]}

    assert candidate["status"] == READY
    assert {
        role: by_role[role]["report_norm_id"]
        for role in (
            "OTHER_PAYMENT_GUARANTEE",
            "OTHER_PAYMENT_GUARANTEE_VND",
            "OTHER_PAYMENT_GUARANTEE_FOREIGN",
        )
    } == {
        "OTHER_PAYMENT_GUARANTEE": 1072,
        "OTHER_PAYMENT_GUARANTEE_VND": 1073,
        "OTHER_PAYMENT_GUARANTEE_FOREIGN": 1074,
    }
    assert [
        cell["coefficient"] for cell in by_role["OTHER_PAYMENT_GUARANTEE"]["values"]
    ] == [5, 4]


def test_joint_venture_and_partnership_use_distinct_schema_ids() -> None:
    customer = {
        "columns": _columns(),
        "continuation": "NONE",
        "rows": [
            _row("Tiền gửi của TCKT", ["30", "26"], "GROUP"),
            _row("Doanh nghiệp Nhà nước", ["20", "18"]),
            _row("Công ty liên doanh, hợp doanh", ["5", "4"]),
            _row("Công ty hợp danh", ["5", "4"]),
            _row("Hộ kinh doanh, cá nhân", ["10", "9"]),
            _row(None, ["40", "35"], "TOTAL", [None]),
        ],
        "title_exact": "Theo đối tượng khách hàng và loại hình doanh nghiệp",
        "unit_exact": "Triệu đồng",
    }
    _cluster, candidate = _evaluate([_record(_page(_ordinary_type(), customer), 1)])
    by_role = {item["role"]: item for item in candidate["mappings"]}

    assert candidate["status"] == READY
    assert by_role["JOINT_VENTURE_COOPERATIVE"]["report_norm_id"] == 1086
    assert by_role["PARTNERSHIP"]["report_norm_id"] == 1087


def test_multi_member_state_controlled_tnhh_is_disclosed_not_cross_family_770() -> None:
    source_label = (
        "Công ty TNHH hai thành viên trở lên có phần vốn góp của Nhà nước "
        "trên 50% vốn điều lệ hoặc Nhà nước giữ quyền chi phối"
    )
    customer = {
        "columns": _columns(),
        "continuation": "NONE",
        "rows": [
            _row("Tiền gửi của TCKT", ["30", "26"], "GROUP"),
            _row("Doanh nghiệp Nhà nước", ["10", "9"]),
            _row(source_label, ["20", "17"]),
            _row("Hộ kinh doanh, cá nhân", ["10", "9"]),
            _row(None, ["40", "35"], "TOTAL", [None]),
        ],
        "title_exact": "Theo đối tượng khách hàng và loại hình doanh nghiệp",
        "unit_exact": "Triệu đồng",
    }
    _cluster, candidate = _evaluate([_record(_page(_ordinary_type(), customer), 1)])
    receipt = candidate["closure_receipt"]["customer_view"]

    assert candidate["status"] == READY
    assert all(item["report_norm_id"] != 770 for item in candidate["mappings"])
    assert receipt["source_only_schema_roles"] == ["STATE_OVER_50_MULTI_MEMBER_TNHH"]
    source_only = next(
        item for item in receipt["source_inventory"] if item["label_exact"] == source_label
    )
    assert source_only["disposition"] == (
        "SOURCE_ONLY_NO_EQUIVALENT_CUSTOMER_DEPOSIT_SCHEMA_ID"
    )


def test_typed_non_money_interest_control_is_excluded_without_hiding_money_rows() -> None:
    control = {
        "columns": [
            {"header_path_exact": ["Năm nay", "%/năm"], "value_kind": "TEXT"},
            {"header_path_exact": ["Năm trước", "%/năm"], "value_kind": "TEXT"},
        ],
        "continuation": "NONE",
        "rows": [
            _row("Tiền gửi không kỳ hạn", ["0,1%", "0,1%"]),
            _row("Tiền gửi có kỳ hạn", ["5%", "4%"]),
        ],
        "title_exact": "Lãi suất tiền gửi",
        "unit_exact": "%/năm",
    }
    cluster, candidate = _evaluate([_record(_page(_ordinary_type(), control), 1)])
    assert cluster["status"] == READY
    assert candidate["status"] == READY
    assert any(
        item["disposition"] == "EXCLUDED_TYPED_NON_MONEY_CONTROL"
        for item in cluster["declared_role_table_inventory"]
    )


def test_explicit_rate_narrative_excludes_mislabeled_text_range_table() -> None:
    control = {
        "columns": [
            {"header_path_exact": ["31/12/2025", "Triệu đồng"], "value_kind": "TEXT"},
            {"header_path_exact": ["31/12/2024", "Triệu đồng"], "value_kind": "TEXT"},
        ],
        "continuation": "NONE",
        "rows": [
            _row("Tiền gửi không kỳ hạn bằng VND", ["0,50", "0,20"]),
            _row("Tiền gửi không kỳ hạn bằng ngoại tệ", ["0,00", "0,00"]),
            _row("Tiền gửi có kỳ hạn bằng VND", ["0,30 - 8,50", "0,20 - 8,80"]),
            _row("Tiền gửi có kỳ hạn bằng ngoại tệ", ["0,00 - 0,70", "0,00 - 0,70"]),
        ],
        "title_exact": None,
        "unit_exact": None,
    }
    page = _page(_ordinary_type(), _customer(), control)
    page["sections"][0]["narratives_exact"] = [
        "Mức lãi suất tiền gửi của khách hàng tại thời điểm cuối năm như sau:"
    ]

    cluster, candidate = _evaluate([_record(page, 1)])

    assert candidate["status"] == READY
    excluded = [
        item
        for item in cluster["declared_role_table_inventory"]
        if item["table_id"] == "t3"
    ]
    assert len(excluded) == 1
    assert excluded[0]["disposition"] == "EXCLUDED_TYPED_NON_MONEY_CONTROL"
    assert excluded[0]["exclusion_evidence"]["rule"] == (
        "TEXT_COLUMNS_WITH_INTRINSIC_BOUNDED_RATE_RANGE_VALUES"
    )
    assert excluded[0]["exclusion_evidence"]["rate_range_evidence"]["range_cell_count"] == 4
    assert excluded[0]["exclusion_evidence"]["interest_rate_marker"]["source_exact"] == (
        "Mức lãi suất tiền gửi của khách hàng tại thời điểm cuối năm như sau:"
    )

    page["sections"][0]["narratives_exact"] = []
    no_narrative_cluster, no_narrative_candidate = _evaluate([_record(page, 1)])
    assert no_narrative_candidate["status"] == READY
    no_narrative_control = next(
        item
        for item in no_narrative_cluster["declared_role_table_inventory"]
        if item["table_id"] == "t3"
    )
    assert "interest_rate_marker" not in no_narrative_control["exclusion_evidence"]


def test_mislabeled_text_rate_table_needs_a_range_and_bounded_values() -> None:
    control = {
        "columns": [
            {"header_path_exact": ["31/12/2025", "Triệu đồng"], "value_kind": "TEXT"},
            {"header_path_exact": ["31/12/2024", "Triệu đồng"], "value_kind": "TEXT"},
        ],
        "continuation": "NONE",
        "rows": [
            _row("Tiền gửi không kỳ hạn bằng VND", ["0,50", "0,20"]),
            _row("Tiền gửi có kỳ hạn bằng VND", ["0,30 - 8,50", "0,20 - 8,80"]),
        ],
        "title_exact": None,
        "unit_exact": None,
    }
    no_range = _page(_ordinary_type(), _customer(), copy.deepcopy(control))
    no_range["sections"][0]["tables"][2]["rows"][1]["values_exact"] = ["8,50", "8,80"]
    unbounded = _page(_ordinary_type(), _customer(), copy.deepcopy(control))
    unbounded["sections"][0]["narratives_exact"] = [
        "Mức lãi suất tiền gửi của khách hàng tại thời điểm cuối năm như sau:"
    ]
    unbounded["sections"][0]["tables"][2]["rows"][1]["values_exact"][0] = "1.000.000"

    for page in (no_range, unbounded):
        cluster = coalesce_gemini_json_customer_deposit_document_v1(
            page_records=[_record(page, 1)], compiled_specs=_compiled()
        )
        assert cluster["status"] == UNRESOLVED
        assert "UNCONSUMED_DECLARED_ROLE_TABLE_WITHIN_OWNER_FENCE" in cluster["reasons"]


def test_reset_between_owner_and_component_blocks_implied_owner() -> None:
    page = _page(_ordinary_type())
    page["sections"][0]["narratives_exact"] = ["Giao dịch với các bên liên quan"]
    cluster = coalesce_gemini_json_customer_deposit_document_v1(
        page_records=[_record(page, 1)], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert "IMPLIED_OWNER_BLOCKED_BY_RESET_OR_HARD_NEGATIVE" in cluster["reasons"]


def test_nonclosing_optional_customer_view_keeps_only_direct_exact_rows() -> None:
    _cluster, exact = _evaluate([_record(_page(_ordinary_type(), _customer()), 1)])
    _cluster, mismatch = _evaluate([_record(_page(_ordinary_type(), _customer(mismatch=True)), 1)])
    assert exact["status"] == READY
    assert exact["closure_receipt"]["customer_view"]["disposition"] == (
        "INCLUDED_EXACT_OPTIONAL_CUSTOMER_VIEW"
    )
    assert {"STATE_COMPANY", "HOUSEHOLD_INDIVIDUAL"} <= {item["role"] for item in exact["mappings"]}
    assert mismatch["status"] == READY
    assert mismatch["closure_receipt"]["customer_view"]["disposition"] == (
        "INCLUDED_PARTIAL_DIRECT_CUSTOMER_VIEW_WITH_SOURCE_ONLY_RESIDUAL"
    )
    assert (
        "CUSTOMER_ROOT_TOTAL_EQUATION_MISMATCH"
        in mismatch["closure_receipt"]["customer_view"]["rejection_reasons"]
    )
    assert {"STATE_COMPANY", "HOUSEHOLD_INDIVIDUAL"} <= {
        item["role"] for item in mismatch["mappings"]
    }


def test_trailing_dash_parent_money_is_recovered_only_by_exact_child_closure() -> None:
    _cluster, candidate = _evaluate(
        [_record(_page(_ordinary_type(), _hierarchical_customer()), 1)]
    )
    by_role = {item["role"]: item for item in candidate["mappings"]}
    customer = candidate["closure_receipt"]["customer_view"]

    assert candidate["status"] == READY
    assert [cell["coefficient"] for cell in by_role["CUSTOMER_TCKT"]["values"]] == [
        30,
        35,
    ]
    assert by_role["CUSTOMER_TCKT"]["values"][1] == {
        "coefficient": 35,
        "source_text": "35-",
        "state": "INFERRED_TRAILING_DASH_POSITIVE_EXACT_CHILD_CLOSURE",
    }
    assert customer["disposition"] == "INCLUDED_EXACT_OPTIONAL_CUSTOMER_VIEW"
    assert customer["conditional_money_recoveries"][0]["source_text"] == "35-"
    provisional_row = next(
        item for item in customer["source_inventory"] if item["label_exact"] == "Tiền gửi của TCKT"
    )
    assert provisional_row["disposition"] == "MAPPED_AFTER_EXACT_CHILD_CLOSURE"


def test_trailing_dash_parent_money_without_exact_child_closure_is_excluded() -> None:
    _cluster, candidate = _evaluate(
        [
            _record(
                _page(
                    _ordinary_type(),
                    _hierarchical_customer(child_comparative="25"),
                ),
                1,
            )
        ]
    )
    customer = candidate["closure_receipt"]["customer_view"]

    assert candidate["status"] == READY
    assert customer["disposition"] == (
        "INCLUDED_PARTIAL_DIRECT_CUSTOMER_VIEW_WITH_SOURCE_ONLY_RESIDUAL"
    )
    assert (
        "CUSTOMER_TRAILING_DASH_NOT_EXACT_CHILD_CLOSURE:CUSTOMER_TCKT:r1:lane2"
        in customer["rejection_reasons"]
    )
    assert "CUSTOMER_TCKT" not in {item["role"] for item in candidate["mappings"]}
    assert {"STATE_COMPANY", "TNHH"} <= {item["role"] for item in candidate["mappings"]}


def test_invalid_customer_money_vector_is_excluded_without_evaluator_crash() -> None:
    _cluster, candidate = _evaluate(
        [
            _record(
                _page(
                    _ordinary_type(),
                    _hierarchical_customer(parent_comparative="35x"),
                ),
                1,
            )
        ]
    )
    customer = candidate["closure_receipt"]["customer_view"]

    assert candidate["status"] == READY
    assert customer["disposition"] == "EXCLUDED_NONEXACT_OPTIONAL_CUSTOMER_VIEW"
    assert "CUSTOMER_ROLE_MONEY_VECTOR_INVALID:CUSTOMER_TCKT:r1" in customer[
        "rejection_reasons"
    ]
    assert "CUSTOMER_ROLE_CELL_VECTOR_INCOMPLETE:CUSTOMER_TCKT" in customer[
        "rejection_reasons"
    ]
    invalid_row = next(
        item for item in customer["source_inventory"] if item["label_exact"] == "Tiền gửi của TCKT"
    )
    assert invalid_row["disposition"] == "UNRESOLVED_INVALID_CUSTOMER_MONEY_VECTOR"


def test_source_only_customer_row_does_not_hide_other_unique_schema_rows() -> None:
    customer = _customer()
    customer["rows"].insert(
        1,
        _row("Công ty chứng khoán, bảo hiểm, tài chính", ["7", "6"]),
    )
    customer["rows"][-1]["values_exact"] = ["47", "41"]
    _cluster, candidate = _evaluate([_record(_page(_ordinary_type(), customer), 1)])
    receipt = candidate["closure_receipt"]["customer_view"]
    by_role = {item["role"]: item for item in candidate["mappings"]}

    assert candidate["status"] == READY
    assert receipt["disposition"] == (
        "INCLUDED_PARTIAL_DIRECT_CUSTOMER_VIEW_WITH_SOURCE_ONLY_RESIDUAL"
    )
    assert receipt["partial_direct_roles"] == ["HOUSEHOLD_INDIVIDUAL", "STATE_COMPANY"]
    assert {"STATE_COMPANY", "HOUSEHOLD_INDIVIDUAL"} <= set(by_role)
    unresolved = next(
        item
        for item in receipt["source_inventory"]
        if item["label_exact"] == "Công ty chứng khoán, bảo hiểm, tài chính"
    )
    assert unresolved["disposition"] == "UNCONSUMED_OR_AMBIGUOUS"


def test_trailing_dash_recovery_replay_rejects_source_sign_tamper() -> None:
    clean_page = _page(_ordinary_type(), _hierarchical_customer())
    record = _record(clean_page, 1)
    cluster, candidate = _evaluate([record])
    tampered_page = copy.deepcopy(clean_page)
    tampered_page["sections"][0]["tables"][1]["rows"][0]["values_exact"][1] = "-35"

    with pytest.raises(
        GeminiJsonCustomerDepositFamilyV1Error,
        match="does not replay exactly",
    ):
        validate_gemini_json_customer_deposit_family_candidate_replay_v1(
            candidate,
            regions=cluster["component_regions"],
            page_json_by_version={record["page_json_version_id"]: tampered_page},
            compiled_specs=_compiled(),
            query_receipt=build_gemini_json_customer_deposit_region_query_receipt_v1(
                cluster["component_regions"]
            ),
        )


def test_document_unit_consensus_is_used_only_for_locally_unitless_target() -> None:
    target = _ordinary_type(unit=None)
    context = {
        "columns": [{"header_path_exact": ["Giá trị"], "value_kind": "MONEY"}],
        "continuation": "NONE",
        "rows": [_row("Khoản mục khác", ["1"])],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    records = [
        _record(_page(target), 1),
        _record(_page(context, title="Thuyết minh khác"), 2),
        _record(_page(context, title="Thuyết minh tiếp"), 3),
    ]
    _cluster, candidate = _evaluate(records)
    unit = candidate["closure_receipt"]["type_currency_view"]["unit_axis"]
    assert candidate["status"] == READY
    assert unit["source"] == "DOCUMENT_EXPLICIT_TABLE_UNIT_CONSENSUS"
    assert unit["document_unit_context_evidence"]["distinct_page_version_count"] == 2


def test_unitless_detail_inherits_exact_period_value_matched_owner_row_unit() -> None:
    target = _ordinary_type(unit=None)
    carrier = {
        "columns": [
            {"header_path_exact": ["31/12/2025", "VND"], "value_kind": "MONEY"},
            {"header_path_exact": ["31/12/2024", "VND"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [_row("Tiền gửi của khách hàng", ["40", "35"])],
        "title_exact": "Báo cáo tình hình tài chính",
        "unit_exact": "VND",
    }
    _cluster, candidate = _evaluate(
        [_record(_page(target), 1), _record(_page(carrier, title="Báo cáo tài chính"), 2)]
    )
    unit = candidate["closure_receipt"]["type_currency_view"]["unit_axis"]

    assert candidate["status"] == READY
    assert {item["unit"] for item in candidate["mappings"]} == {"VND"}
    assert unit["source"] == "DOCUMENT_OWNER_ROW_EXACT_VALUE_PERIOD_UNIT_CORROBORATION"
    assert len(unit["document_unit_context_evidence"]["evidence"]) == 1


def test_owner_row_unit_corroboration_rejects_value_tamper_and_unit_ambiguity() -> None:
    target = _ordinary_type(unit=None)

    def carrier(unit: str, current: str = "40") -> dict:
        return {
            "columns": [
                {"header_path_exact": ["31/12/2025", unit], "value_kind": "MONEY"},
                {"header_path_exact": ["31/12/2024", unit], "value_kind": "MONEY"},
            ],
            "continuation": "NONE",
            "rows": [_row("Tiền gửi của khách hàng", [current, "35"])],
            "title_exact": "Báo cáo tình hình tài chính",
            "unit_exact": unit,
        }

    _cluster, tampered = _evaluate(
        [
            _record(_page(target), 1),
            _record(_page(carrier("VND", current="41"), title="Báo cáo tài chính"), 2),
        ]
    )
    assert tampered["status"] == UNRESOLVED
    assert "MONEY_UNIT_NOT_EXACTLY_RESOLVED" in tampered["reasons"]

    _cluster, ambiguous = _evaluate(
        [
            _record(_page(target), 1),
            _record(_page(carrier("VND"), title="Báo cáo tài chính"), 2),
            _record(_page(carrier("Triệu đồng"), title="Báo cáo tài chính"), 3),
        ]
    )
    assert ambiguous["status"] == UNRESOLVED
    assert "MONEY_UNIT_NOT_EXACTLY_RESOLVED" in ambiguous["reasons"]


def test_related_party_role_population_without_root_total_is_not_a_second_component() -> None:
    foreign = copy.deepcopy(_ordinary_type())
    foreign["rows"] = foreign["rows"][:-1]
    foreign["title_exact"] = "Giao dịch với các bên liên quan"
    cluster, candidate = _evaluate([_record(_page(_ordinary_type(), foreign), 1)])
    assert candidate["status"] == READY
    assert len(cluster["component_regions"]) == 1


def test_conflicting_explicit_unit_is_unresolved() -> None:
    table = _ordinary_type(unit="Triệu đồng và Nghìn đồng")
    _cluster, candidate = _evaluate([_record(_page(table), 1)])
    assert candidate["status"] == UNRESOLVED
    assert "MULTIPLE_CONFLICTING_DECLARED_MONEY_UNITS_ON_ONE_SURFACE" in candidate["reasons"]
    assert candidate["mappings"] == []


def test_exact_vnd_source_unit_is_retained_without_silent_rescaling() -> None:
    table = _ordinary_type(unit="VND")
    table["columns"] = [
        {"header_path_exact": ["31/12/2025", "VND"], "value_kind": "MONEY"},
        {"header_path_exact": ["31/12/2024", "VND"], "value_kind": "MONEY"},
    ]
    _cluster, candidate = _evaluate([_record(_page(table), 1)])

    assert candidate["status"] == READY
    assert {item["unit"] for item in candidate["mappings"]} == {"VND"}
    no_term = next(item for item in candidate["mappings"] if item["role"] == "NO_TERM")
    assert [cell["coefficient"] for cell in no_term["values"]] == [10, 9]


def test_one_million_rounding_delta_is_disclosed_and_bounded() -> None:
    table = _ordinary_type()
    table["rows"][-1]["values_exact"][0] = "39"
    _cluster, candidate = _evaluate([_record(_page(table), 1)])
    root = next(
        equation
        for equation in candidate["closure_receipt"]["equations"]
        if equation["equation_kind"] == "TYPE_ROOT_EQUALS_DIRECT_PARENT_FRONTIER"
    )

    assert candidate["status"] == READY
    assert root["status"] == "BOUNDED_MILLION_VND_ROUNDING"
    assert root["rounding_receipt"]["observed_deltas"] == [1, 0]
    assert root["rounding_receipt"]["maximum_absolute_delta"] == 3


def test_exact_vnd_source_does_not_receive_million_vnd_rounding_tolerance() -> None:
    table = _ordinary_type(unit="VND")
    table["columns"] = [
        {"header_path_exact": ["31/12/2025", "VND"], "value_kind": "MONEY"},
        {"header_path_exact": ["31/12/2024", "VND"], "value_kind": "MONEY"},
    ]
    table["rows"][-1]["values_exact"][0] = "39"
    _cluster, candidate = _evaluate([_record(_page(table), 1)])

    assert candidate["status"] == UNRESOLVED
    assert "TYPE_ROOT_TOTAL_EQUATION_MISMATCH" in candidate["reasons"]


def test_all_blank_optional_type_role_is_omitted_even_when_root_closes() -> None:
    table = _ordinary_type()
    table["rows"][4]["values_exact"] = [None, None]
    table["rows"][-1]["values_exact"] = ["38", "34"]
    _cluster, candidate = _evaluate([_record(_page(table), 1)])

    assert candidate["status"] == READY
    assert "DEDICATED" not in {item["role"] for item in candidate["mappings"]}
    assert all(
        value["source_text"] is not None or value["coefficient"] is None
        for mapping in candidate["mappings"]
        for value in mapping["values"]
        if "DERIVED" not in value["state"]
    )


def test_visible_zero_lane_is_kept_while_blank_sibling_lane_stays_null() -> None:
    table = _ordinary_type()
    table["rows"][4]["values_exact"] = ["-", None]
    table["rows"][-1]["values_exact"] = ["38", "33"]
    _cluster, candidate = _evaluate([_record(_page(table), 1)])
    dedicated = next(item for item in candidate["mappings"] if item["role"] == "DEDICATED")
    root = next(
        equation
        for equation in candidate["closure_receipt"]["equations"]
        if equation["equation_kind"] == "TYPE_ROOT_EQUALS_DIRECT_PARENT_FRONTIER"
    )

    assert candidate["status"] == READY
    assert dedicated["values"] == [
        {"coefficient": 0, "source_text": "-", "state": "DASH_ZERO"},
        {"coefficient": None, "source_text": None, "state": "BLANK_SOURCE_CELL"},
    ]
    assert root["status"] == "PARTIAL_OBSERVED_LANES_EXACT"
    assert [receipt["status"] for receipt in root["lane_receipts"]] == [
        "EXACT_OBSERVED_SOURCE_LANE",
        "COMPONENT_SOURCE_LANE_UNOBSERVED",
    ]
    assert root["lane_receipts"][1]["component_sum"] is None


def test_all_blank_currency_subtype_is_omitted_from_mapping_and_equation() -> None:
    table = {
        "columns": _columns(),
        "continuation": "NONE",
        "rows": [
            _row("Tiền gửi không kỳ hạn", ["10", "9"], "GROUP"),
            _row(
                "Tiền gửi không kỳ hạn bằng VND",
                ["8", "7"],
                hierarchy=[
                    "Tiền gửi không kỳ hạn",
                    "Tiền gửi không kỳ hạn bằng VND",
                ],
            ),
            _row(
                "Tiền gửi không kỳ hạn bằng ngoại tệ",
                ["2", "2"],
                hierarchy=[
                    "Tiền gửi không kỳ hạn",
                    "Tiền gửi không kỳ hạn bằng ngoại tệ",
                ],
            ),
            _row(
                "Tiền gửi tiết kiệm không kỳ hạn bằng ngoại tệ",
                [None, None],
                hierarchy=[
                    "Tiền gửi không kỳ hạn",
                    "Tiền gửi tiết kiệm không kỳ hạn bằng ngoại tệ",
                ],
            ),
            _row("Tiền gửi có kỳ hạn", ["20", "18"]),
            _row("Tiền gửi ký quỹ", ["3", "2"]),
            _row("Tiền gửi vốn chuyên dùng", ["2", "1"]),
            _row(None, ["35", "30"], "TOTAL", [None]),
        ],
        "title_exact": "Theo loại tiền gửi",
        "unit_exact": "Triệu đồng",
    }
    _cluster, candidate = _evaluate([_record(_page(table), 1)])
    by_role = {item["role"]: item for item in candidate["mappings"]}
    parent = next(
        equation
        for equation in candidate["closure_receipt"]["equations"]
        if equation["equation_kind"] == "TYPE_PARENT_EQUALS_CURRENCY_CHILDREN"
    )
    inventory = candidate["closure_receipt"]["type_currency_view"][
        "source_inventory"
    ]

    assert candidate["status"] == READY
    assert "SAVINGS_FOREIGN" not in by_role
    assert parent["status"] == "EXACT"
    assert parent["component_roles"] == ["NO_TERM_VND", "NO_TERM_FOREIGN"]
    assert all(
        value["coefficient"] is not None
        for mapping in candidate["mappings"]
        for value in mapping["values"]
    )
    assert inventory[3]["disposition"] == (
        "TYPE_CURRENCY_CHILD_ALL_LANES_BLANK_OMITTED"
    )


def test_blank_structural_tckt_group_is_derived_from_complete_child_frontier() -> None:
    customer = {
        "columns": _columns(),
        "continuation": "NONE",
        "rows": [
            _row("Tổ chức kinh tế", [None, None], "GROUP"),
            _row("Doanh nghiệp Nhà nước", ["10", "9"]),
            _row("Công ty TNHH", ["20", "17"]),
            _row("Hộ kinh doanh, cá nhân", ["10", "9"]),
            _row(None, ["40", "35"], "TOTAL", [None]),
        ],
        "title_exact": "Theo đối tượng khách hàng và loại hình doanh nghiệp",
        "unit_exact": "Triệu đồng",
    }
    _cluster, candidate = _evaluate([_record(_page(_ordinary_type(), customer), 1)])
    by_role = {item["role"]: item for item in candidate["mappings"]}

    assert candidate["status"] == READY
    assert [cell["coefficient"] for cell in by_role["CUSTOMER_TCKT"]["values"]] == [30, 26]
    receipt = candidate["closure_receipt"]["customer_view"]
    group = next(item for item in receipt["source_inventory"] if item["row_ordinal"] == 1)
    assert group["disposition"] == "DERIVED_FROM_COMPLETE_HIERARCHY_CHILD_FRONTIER"


def test_non_state_domestic_enterprise_alias_maps_combined_company_schema_role() -> None:
    customer = {
        "columns": _columns(),
        "continuation": "NONE",
        "rows": [
            _row("Tiền gửi của tổ chức kinh tế", ["30", "26"], "GROUP"),
            _row(
                "Doanh nghiệp ngoài quốc doanh",
                ["20", "17"],
                hierarchy=["Tiền gửi của tổ chức kinh tế", "Doanh nghiệp ngoài quốc doanh"],
            ),
            _row(
                "Doanh nghiệp quốc doanh",
                ["10", "9"],
                hierarchy=["Tiền gửi của tổ chức kinh tế", "Doanh nghiệp quốc doanh"],
            ),
            _row("Tiền gửi của cá nhân", ["10", "9"]),
            _row(None, ["40", "35"], "TOTAL", [None]),
        ],
        "title_exact": "Theo đối tượng khách hàng và loại hình doanh nghiệp",
        "unit_exact": "Triệu đồng",
    }
    _cluster, candidate = _evaluate([_record(_page(_ordinary_type(), customer), 1)])
    by_role = {item["role"]: item for item in candidate["mappings"]}

    assert candidate["status"] == READY
    assert by_role["COMBINED_COMPANY"]["report_norm_id"] == 1084
    assert [cell["coefficient"] for cell in by_role["COMBINED_COMPANY"]["values"]] == [
        20,
        17,
    ]


def test_customer_parent_context_continues_across_exact_adjacent_fragments() -> None:
    first_customer = {
        "columns": _columns(),
        "continuation": "CONTINUES_ON_NEXT_PAGE",
        "rows": [
            _row("Tiền gửi của tổ chức kinh tế", ["30", "26"], "GROUP"),
            _row("Doanh nghiệp Nhà nước", ["10", "9"]),
        ],
        "title_exact": "Theo đối tượng khách hàng và loại hình doanh nghiệp",
        "unit_exact": "Triệu đồng",
    }
    second_customer = {
        "columns": _columns(),
        "continuation": "CONTINUES_FROM_PREVIOUS_PAGE",
        "rows": [
            _row("Công ty TNHH", ["20", "17"]),
            _row("Hộ kinh doanh, cá nhân", ["10", "9"]),
            _row(None, ["40", "35"], "TOTAL", [None]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    records = [
        _record(_page(_ordinary_type(), first_customer), 1),
        _record(
            _page(second_customer, title="Tiền gửi của khách hàng (tiếp theo)"),
            2,
        ),
    ]
    cluster, candidate = _evaluate(records)
    by_role = {item["role"]: item for item in candidate["mappings"]}

    assert candidate["status"] == READY
    assert [
        (region["physical_page"], region["component_role"])
        for region in cluster["component_regions"]
        if region["component_role"] == "CUSTOMER_TYPE"
    ] == [(1, "CUSTOMER_TYPE"), (2, "CUSTOMER_TYPE")]
    assert [cell["coefficient"] for cell in by_role["CUSTOMER_TCKT"]["values"]] == [30, 26]


def test_blank_numbered_owner_row_is_structural_but_valued_owner_fails_closed() -> None:
    structural = _ordinary_type()
    structural["rows"].insert(
        0,
        _row("18. Tiền gửi của khách hàng", [None, None], "ITEM"),
    )
    _cluster, accepted = _evaluate([_record(_page(structural), 1)])
    inventory = accepted["closure_receipt"]["type_currency_view"]["source_inventory"]
    assert accepted["status"] == READY
    assert inventory[0]["disposition"] == (
        "EXCLUDED_EXACT_STRUCTURAL_CUSTOMER_DEPOSIT_OWNER"
    )

    valued = copy.deepcopy(structural)
    valued["rows"][0]["values_exact"] = ["1", "1"]
    _cluster, rejected = _evaluate([_record(_page(valued), 1)])
    assert rejected["status"] == UNRESOLVED
    assert "UNCONSUMED_TYPE_SOURCE_ROW:r1" in rejected["reasons"]


def test_candidate_replay_rejects_coherently_rehashed_source_drift() -> None:
    cluster, candidate = _evaluate([_record(_page(_ordinary_type()), 1)])
    forged = copy.deepcopy(candidate)
    forged["mappings"][0]["values"][0]["coefficient"] += 1
    with pytest.raises(
        GeminiJsonCustomerDepositFamilyV1Error,
        match="does not replay exactly",
    ):
        validate_gemini_json_customer_deposit_family_candidate_replay_v1(
            forged,
            regions=cluster["component_regions"],
            page_json_by_version={"gfpstorev1:json:" + f"{1:064x}": _page(_ordinary_type())},
            compiled_specs=_compiled(),
            query_receipt=build_gemini_json_customer_deposit_region_query_receipt_v1(
                cluster["component_regions"]
            ),
        )


def test_authenticated_dash_repair_is_exact_and_does_not_mutate_source() -> None:
    page = _page(_ordinary_type())
    page["sections"][0]["tables"][0]["rows"][4]["values_exact"] = [None, "1"]
    page["sections"][0]["tables"][0]["rows"][-1]["values_exact"] = ["38", "35"]
    record = _record(page, 1)
    compiled = bind_gemini_json_customer_deposit_source_repairs_v1(
        _compiled(), _source_repair_spec()
    )
    cluster = coalesce_gemini_json_customer_deposit_document_v1(
        page_records=[record], compiled_specs=compiled
    )
    regions = cluster["component_regions"]
    candidate = evaluate_gemini_json_customer_deposit_family_cluster_v1(
        regions=regions,
        page_json_by_version={record["page_json_version_id"]: page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_customer_deposit_region_query_receipt_v1(regions),
    )
    dedicated = next(item for item in candidate["mappings"] if item["role"] == "DEDICATED")
    repair_receipt = candidate["closure_receipt"][
        "customer_deposit_source_repair_receipt"
    ]

    assert candidate["status"] == READY
    assert dedicated["values"] == [
        {"coefficient": 0, "source_text": "-", "state": "DASH_ZERO"},
        {"coefficient": 1, "source_text": "1", "state": "RAW_SIGNED_INTEGER"},
    ]
    assert len(repair_receipt["authenticated_source_repairs"]) == 1
    assert page["sections"][0]["tables"][0]["rows"][4]["values_exact"][0] is None


def test_source_repair_binding_rejects_identity_and_axis_tamper() -> None:
    identity_tamper = _source_repair_spec()
    identity_tamper["repairs"][0]["repair_id"] = "gjfcdav1:source-repair:" + "0" * 64
    with pytest.raises(GeminiJsonCustomerDepositFamilyV1Error, match="identity drifted"):
        bind_gemini_json_customer_deposit_source_repairs_v1(
            _compiled(), identity_tamper
        )

    axis_tamper = _source_repair_spec()
    axis_tamper["repair_axis_sha256"] = "0" * 64
    with pytest.raises(GeminiJsonCustomerDepositFamilyV1Error, match="axis seal drifted"):
        bind_gemini_json_customer_deposit_source_repairs_v1(_compiled(), axis_tamper)


def test_source_repair_overlay_rejects_source_and_before_image_drift() -> None:
    page = _page(_ordinary_type())
    page["sections"][0]["tables"][0]["rows"][4]["values_exact"] = [None, "1"]
    record = _record(page, 1)
    cluster = coalesce_gemini_json_customer_deposit_document_v1(
        page_records=[record], compiled_specs=_compiled()
    )
    regions = cluster["component_regions"]

    wrong_name = bind_gemini_json_customer_deposit_source_repairs_v1(
        _compiled(), _source_repair_spec(source_logical_name="other.pdf")
    )
    with pytest.raises(GeminiJsonCustomerDepositFamilyV1Error, match="logical source"):
        _apply_authenticated_source_repairs(
            regions=regions,
            page_json_by_version={record["page_json_version_id"]: page},
            compiled_specs=wrong_name,
        )

    drifted_page = copy.deepcopy(page)
    drifted_page["sections"][0]["tables"][0]["rows"][4]["values_exact"][0] = "0"
    compiled = bind_gemini_json_customer_deposit_source_repairs_v1(
        _compiled(), _source_repair_spec()
    )
    with pytest.raises(GeminiJsonCustomerDepositFamilyV1Error, match="before-image"):
        _apply_authenticated_source_repairs(
            regions=regions,
            page_json_by_version={record["page_json_version_id"]: drifted_page},
            compiled_specs=compiled,
        )
