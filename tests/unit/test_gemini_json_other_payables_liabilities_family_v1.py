from __future__ import annotations

import copy
import json
from pathlib import Path

from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
)

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "4" * 64
VERSION_ID = "gfpstorev1:json:" + "5" * 64
SOURCE_SHA256 = "6" * 64


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-other-payables-liabilities-topology-v1.json"),
        _json("tm-other-payables-liabilities-evaluation-v1.json"),
        _json("tm-other-payables-liabilities-schema-binding-v1.json"),
    )


def _row(
    label: str | None,
    values: list[str | None],
    *,
    kind: str = "ITEM",
    path: list[str | None] | None = None,
) -> dict:
    return {
        "hierarchy_path_exact": path if path is not None else [label],
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _rows() -> list[dict]:
    return [
        _row("Các khoản phải trả nội bộ", ["30", "27"], kind="SUBTOTAL"),
        _row(
            "Phải trả nhân viên",
            ["10", "9"],
            path=["Các khoản phải trả nội bộ", "Phải trả nhân viên"],
        ),
        _row(
            "Phải trả nội bộ khác",
            ["20", "18"],
            path=["Các khoản phải trả nội bộ", "Phải trả nội bộ khác"],
        ),
        _row("Các khoản phải trả bên ngoài", ["60", "54"], kind="SUBTOTAL"),
        _row(
            "Thuế và các khoản phải nộp Nhà nước",
            ["20", "18"],
            path=[
                "Các khoản phải trả bên ngoài",
                "Thuế và các khoản phải nộp Nhà nước",
            ],
        ),
        _row(
            "Các khoản phải trả khác",
            ["15", "13"],
            path=["Các khoản phải trả bên ngoài", "Các khoản phải trả khác"],
        ),
        _row(
            "Các khoản lãi, phí phải trả",
            ["25", "23"],
            path=["Các khoản phải trả bên ngoài", "Các khoản lãi, phí phải trả"],
        ),
        _row("Quỹ khen thưởng, phúc lợi", ["10", "9"]),
        _row(None, ["100", "90"], kind="TOTAL", path=[None]),
    ]


def _table(rows: list[dict]) -> dict:
    return {
        "columns": [
            {
                "header_path_exact": ["30/06/2026", "Triệu đồng"],
                "value_kind": "MONEY",
            },
            {
                "header_path_exact": ["31/12/2025", "Triệu đồng"],
                "value_kind": "MONEY",
            },
        ],
        "continuation": "NONE",
        "rows": rows,
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }


def _page(rows: list[dict]) -> dict:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [_table(rows)],
                "title_exact": "12. CÁC KHOẢN PHẢI TRẢ VÀ CÔNG NỢ KHÁC",
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _record(page: dict) -> dict:
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


def _evaluate(page: dict) -> dict:
    compiled = _compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    return evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            cluster["component_regions"]
        ),
    )


def _by_role(candidate: dict) -> dict[str, list[int]]:
    return {
        item["role"]: [value["coefficient"] for value in item["values"]]
        for item in candidate["mappings"]
    }


def test_internal_external_and_optional_children_close_without_double_counting() -> None:
    candidate = _evaluate(_page(_rows()))
    assert candidate["status"] == READY
    assert _by_role(candidate) == {
        "EMPLOYEE_PAYABLE": [10, 9],
        "EXTERNAL_PAYABLE": [60, 54],
        "FAMILY_ROOT_TOTAL": [100, 90],
        "INTERNAL_OTHER": [20, 18],
        "INTERNAL_PAYABLE": [30, 27],
        "OTHER_DIRECT_SOURCE_ROWS": [25, 23],
        "OTHER_PAYABLE": [15, 13],
        "TAX_PAYABLE": [20, 18],
        "WELFARE_FUND": [10, 9],
    }


def test_duplicate_residual_rows_aggregate_only_after_source_frontier_closes() -> None:
    rows = _rows()
    rows[6:7] = [
        _row(
            "Thu nhập chưa thực hiện",
            ["10", "9"],
            path=["Các khoản phải trả bên ngoài", "Thu nhập chưa thực hiện"],
        ),
        _row(
            "Doanh thu chờ phân bổ",
            ["15", "14"],
            path=["Các khoản phải trả bên ngoài", "Doanh thu chờ phân bổ"],
        ),
    ]
    candidate = _evaluate(_page(rows))
    assert candidate["status"] == READY
    assert _by_role(candidate)["OTHER_DIRECT_SOURCE_ROWS"] == [25, 23]
    mapping = next(
        item for item in candidate["mappings"] if item["role"] == "OTHER_DIRECT_SOURCE_ROWS"
    )
    assert mapping["state"] == "SOURCE_SAME_ROLE_ROWS_AGGREGATED_AFTER_TABLE_CLOSURE"
    assert {item["row_id"] for item in mapping["source_refs"]} == {"r7", "r8"}


def test_nested_detail_total_is_context_parent_not_second_family_root() -> None:
    summary = _table(
        [
            _row("Các khoản phải trả nội bộ", ["30", "27"]),
            _row("Các khoản phải trả bên ngoài", ["60", "54"]),
            _row("Quỹ khen thưởng, phúc lợi", ["10", "9"]),
            _row(None, ["100", "90"], kind="TOTAL", path=[None]),
        ]
    )
    detail = _table(
        [
            _row("Thuế và các khoản phải nộp Nhà nước", ["20", "18"]),
            _row("Các khoản phải trả khác", ["15", "13"]),
            _row("Các khoản lãi, phí phải trả", ["25", "23"]),
            _row(None, ["60", "54"], kind="TOTAL", path=[None]),
        ]
    )
    page = _page([])
    page["sections"][0]["tables"] = [summary, detail]
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    assert _by_role(candidate)["FAMILY_ROOT_TOTAL"] == [100, 90]
    assert _by_role(candidate)["EXTERNAL_PAYABLE"] == [60, 54]
    assert len([item for item in candidate["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL"]) == 1


def test_structural_context_is_removed_before_distinct_table_residual_sum() -> None:
    interest_context = _table(
        [
            _row("Lãi phải trả tiền gửi", ["18", "15"]),
            _row("Lãi phải trả tiền vay", ["12", "8"]),
            _row(None, ["30", "23"], kind="TOTAL", path=[None]),
        ]
    )
    interest_context["title_exact"] = "Các khoản lãi, phí phải trả"
    summary = _table(
        [
            _row("Các khoản phải trả nội bộ", ["10", "9"]),
            _row("Các khoản phải trả bên ngoài", ["20", "18"]),
            _row("Quỹ phát triển khoa học và công nghệ", ["5", "4"]),
            _row("Quỹ khen thưởng, phúc lợi", ["5", "4"]),
            _row(None, ["40", "35"], kind="TOTAL", path=[None]),
        ]
    )
    summary["title_exact"] = "Các khoản phải trả và công nợ khác"
    external_detail = _table(
        [
            _row("Các khoản thuế phải nộp Nhà nước", ["5", "4"]),
            _row("Chuyển tiền phải trả", ["3", "2"]),
            _row("Khoản nguồn ngoài thứ nhất", ["5", "5"]),
            _row("Khoản nguồn ngoài thứ hai", ["7", "7"]),
            _row(None, ["20", "18"], kind="TOTAL", path=[None]),
        ]
    )
    external_detail["title_exact"] = "Chi tiết các khoản phải trả bên ngoài"
    page = _page([])
    page["sections"][0]["tables"] = [interest_context, summary, external_detail]

    candidate = _evaluate(page)

    assert candidate["status"] == READY
    assert _by_role(candidate)["OTHER_DIRECT_SOURCE_ROWS"] == [20, 18]
    mapping = next(
        item for item in candidate["mappings"] if item["role"] == "OTHER_DIRECT_SOURCE_ROWS"
    )
    assert mapping["state"] == "SOURCE_DISTINCT_LABEL_TABLES_AGGREGATED_AFTER_CLUSTER_CLOSURE"
    receipts = candidate["closure_receipt"]["cluster_aggregation_receipts"]
    assert [item["rule"] for item in receipts] == [
        "STRUCTURAL_CONTEXT_TOTAL_IS_NOT_A_RESIDUAL_LEAF_WHEN_"
        "EXPLICIT_RESIDUAL_SOURCE_ROWS_EXIST_ON_THE_SAME_LANE_AXIS",
        "CONFIGURED_ROLE_DISTINCT_VISIBLE_LABELS_DISTINCT_TABLES_DIRECT_SUM",
    ]


def test_unknown_direct_row_consumed_by_exact_equation_maps_declared_residual() -> None:
    rows = _rows()
    rows[6:7] = [
        _row(
            "Chuyển tiền phải trả",
            ["10", "9"],
            path=["Các khoản phải trả bên ngoài", "Chuyển tiền phải trả"],
        ),
        _row(
            "Khoản chờ xử lý chưa có schema leaf",
            ["15", "14"],
            path=[
                "Các khoản phải trả bên ngoài",
                "Khoản chờ xử lý chưa có schema leaf",
            ],
        ),
    ]
    candidate = _evaluate(_page(rows))
    assert candidate["status"] == READY
    assert _by_role(candidate)["OTHER_DIRECT_SOURCE_ROWS"] == [25, 23]
    source_only = candidate["closure_receipt"]["source_only_unmapped_rows"]
    assert not any(
        item["source_ref"]["label_exact"] == "Khoản chờ xử lý chưa có schema leaf"
        for item in source_only
    )
    receipt = candidate["closure_receipt"]["table_receipts"][0]
    assert (
        receipt["equation_consumed_residual_projection_receipts"][0]["residual_role"]
        == "OTHER_DIRECT_SOURCE_ROWS"
    )


def test_newline_joined_parent_child_path_preserves_exact_nested_frontier() -> None:
    root = "Các khoản phải trả và công nợ khác"
    internal = "Các khoản phải trả nội bộ"
    external = "Các khoản phải trả bên ngoài"
    rows = [
        _row("Các khoản lãi, phí phải trả", ["30", "28"]),
        _row(root, ["14", "12"], kind="GROUP", path=[root]),
        _row(internal, ["6", "4"], kind="GROUP", path=[root, internal]),
        _row(
            "- Phải trả nhân viên",
            ["5", "3"],
            path=[root, internal + "\n- Phải trả nhân viên"],
        ),
        _row(
            "- Phải trả nội bộ khác",
            ["1", "1"],
            path=[root, internal + "\n- Phải trả nội bộ khác"],
        ),
        _row(external, ["8", "8"], kind="GROUP", path=[root, external]),
        _row(
            "- Thuế và các khoản phải trả khác cho ngân sách Nhà nước",
            ["4", "3"],
            path=[
                root,
                external + "\n- Thuế và các khoản phải trả khác cho ngân sách Nhà nước",
            ],
        ),
        _row(
            "- Phải trả bên ngoài khác",
            ["4", "5"],
            path=[root, external + "\n- Phải trả bên ngoài khác"],
        ),
        _row("Quỹ khen thưởng, phúc lợi", ["2", "2"]),
        _row(None, ["46", "42"], kind="TOTAL", path=[None]),
    ]

    candidate = _evaluate(_page(rows))

    assert candidate["status"] == READY
    roles = _by_role(candidate)
    assert roles["FAMILY_ROOT_TOTAL"] == [46, 42]
    assert roles["OTHER_DIRECT_SOURCE_ROWS"] == [34, 33]
    mapping = next(
        item for item in candidate["mappings"] if item["role"] == "OTHER_DIRECT_SOURCE_ROWS"
    )
    assert mapping["state"] == "SOURCE_SAME_ROLE_ROWS_AGGREGATED_AFTER_TABLE_CLOSURE"


def test_unmatched_rows_inside_explicit_nonexhaustive_detail_scope_map_residual() -> None:
    rows = [
        _row("Các khoản phải trả nội bộ", ["30", "27"]),
        _row("Các khoản phải trả bên ngoài", ["60", "54"]),
        _row("Trong đó:", [None, None], kind="GROUP"),
        _row(
            "Các khoản lãi, phí phải trả",
            ["10", "9"],
            path=["Trong đó:", "Các khoản lãi, phí phải trả"],
        ),
        _row(
            "Khoản chi tiết nguồn chưa có alias riêng",
            ["5", "4"],
            path=["Trong đó:", "Khoản chi tiết nguồn chưa có alias riêng"],
        ),
        _row(
            "Thuế và các khoản phải trả khác cho ngân sách Nhà nước",
            ["20", "18"],
            path=["Trong đó:", "Thuế và các khoản phải trả khác cho ngân sách Nhà nước"],
        ),
        _row("Quỹ khen thưởng, phúc lợi", ["10", "9"]),
        _row(None, ["100", "90"], kind="TOTAL", path=[None]),
    ]
    candidate = _evaluate(_page(rows))
    assert candidate["status"] == READY
    roles = _by_role(candidate)
    assert roles["OTHER_DIRECT_SOURCE_ROWS"] == [15, 13]
    assert roles["TAX_PAYABLE"] == [20, 18]
    assert roles["FAMILY_ROOT_TOTAL"] == [100, 90]
    receipt = candidate["closure_receipt"]["table_receipts"][0]
    assert receipt["supplemental_residual_projection_receipts"][0]["marker"] == "trong do"
    assert receipt["aggregation_receipts"][0]["supplemental_detail_population"]["rule"].endswith(
        "NO_PARENT_OR_ROOT_ADDITION"
    )


def test_source_visible_root_uses_its_exact_frontier_not_every_disclosure_mapping() -> None:
    rows = [
        _row("Dự phòng rủi ro khác", ["20", "18"], kind="SUBTOTAL"),
        _row(
            "Khoản cấu thành trực tiếp",
            ["20", "18"],
            path=["Dự phòng rủi ro khác", "Khoản cấu thành trực tiếp"],
        ),
        _row("Trong đó:", [None, None], kind="GROUP"),
        _row(
            "Các khoản phải trả khác",
            ["5", "4"],
            path=["Trong đó:", "Các khoản phải trả khác"],
        ),
        _row(None, ["20", "18"], kind="TOTAL", path=[None]),
    ]
    candidate = _evaluate(_page(rows))
    assert candidate["status"] == READY
    roles = _by_role(candidate)
    assert roles["FAMILY_ROOT_TOTAL"] == [20, 18]
    assert roles["OTHER_PAYABLE"] == [5, 4]
    assert roles["OTHER_RISK_PROVISION"] == [20, 18]
    assert "OTHER_DIRECT_SOURCE_ROWS" not in roles
    receipt = candidate["closure_receipt"]["root_component_sum_receipts"][0]
    assert receipt["rule"].endswith("DISCLOSURE_MAPPINGS_ARE_NOT_ASSUMED_ADDITIVE")
    assert receipt["source_equation_id"].startswith("gjfoltiev1:equation:")


def test_source_parent_must_equal_its_exact_direct_child_frontier() -> None:
    rows = _rows()
    rows[0]["values_exact"][0] = "31"
    candidate = _evaluate(_page(rows))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_duplicate_residual_rows_cannot_aggregate_when_table_does_not_close() -> None:
    rows = _rows()
    rows[6:7] = [
        _row(
            "Thu nhập chưa thực hiện",
            ["10", "9"],
            path=["Các khoản phải trả bên ngoài", "Thu nhập chưa thực hiện"],
        ),
        _row(
            "Doanh thu chờ phân bổ",
            ["16", "14"],
            path=["Các khoản phải trả bên ngoài", "Doanh thu chờ phân bổ"],
        ),
    ]
    candidate = _evaluate(_page(rows))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_period_or_unit_conflict_fails_closed() -> None:
    page = _page(_rows())
    page["sections"][0]["tables"][0]["unit_exact"] = "Triệu đồng / Nghìn đồng"
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_structural_reset_blocks_owner_carry_to_later_table() -> None:
    page = _page([])
    page["sections"] = [
        {
            "content_kind": "FINANCIAL_NOTE",
            "narratives_exact": [],
            "statement_type": "NOT_APPLICABLE",
            "tables": [],
            "title_exact": "CÁC KHOẢN PHẢI TRẢ VÀ CÔNG NỢ KHÁC",
        },
        {
            "content_kind": "FINANCIAL_NOTE",
            "narratives_exact": [],
            "statement_type": "NOT_APPLICABLE",
            "tables": [],
            "title_exact": "VỐN CHỦ SỞ HỮU",
        },
        {
            "content_kind": "FINANCIAL_NOTE",
            "narratives_exact": [],
            "statement_type": "NOT_APPLICABLE",
            "tables": [_table(_rows())],
            "title_exact": None,
        },
    ]
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] != READY
    assert cluster["component_regions"] == []


def test_extra_declared_role_table_inside_owner_inventory_cannot_be_ignored() -> None:
    page = _page(_rows())
    extra = _table(
        [
            _row(
                "Phải trả nhân viên",
                ["999", "999"],
                path=["Các khoản phải trả nội bộ", "Phải trả nhân viên"],
            ),
            _row("Khoản ngoài family", ["1", "1"]),
        ]
    )
    page["sections"][0]["tables"].append(extra)
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_mapping_does_not_depend_on_bank_file_page_or_expected_value() -> None:
    page = copy.deepcopy(_page(_rows()))
    record = _record(page)
    record.update(
        {
            "document_ordinal": 999,
            "physical_page": 777,
            "selected_page_ordinal": 777,
            "source_logical_name": "unseen-filing.pdf",
            "source_sha256": "7" * 64,
        }
    )
    compiled = _compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[record], compiled_specs=compiled
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            cluster["component_regions"]
        ),
    )
    assert candidate["status"] == READY
    assert _by_role(candidate)["FAMILY_ROOT_TOTAL"] == [100, 90]
