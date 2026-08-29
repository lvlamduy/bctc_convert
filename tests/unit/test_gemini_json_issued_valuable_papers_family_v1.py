from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
)

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "1" * 64
VERSION_ID = "gfpstorev1:json:" + "2" * 64
SOURCE_SHA256 = "3" * 64


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-issued-valuable-papers-topology-v1.json"),
        _json("tm-issued-valuable-papers-evaluation-v1.json"),
        _json("tm-issued-valuable-papers-schema-binding-v1.json"),
    )


def _row(label: str | None, values: list[str | None], *, kind: str, path: list[str | None]):
    return {
        "hierarchy_path_exact": path,
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _instrument_columns() -> list[dict]:
    return [
        {"header_path_exact": ["Kỳ phiếu", "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": ["Trái phiếu ghi sổ", "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": ["Chứng chỉ tiền gửi", "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": ["Tổng cộng", "Triệu đồng"], "value_kind": "MONEY"},
    ]


def _one_period_rows() -> list[dict]:
    return [
        _row("Dưới 12 tháng", [None] * 4, kind="GROUP", path=["Dưới 12 tháng"]),
        _row(
            "Mệnh giá",
            ["10", "-", "30", "40"],
            kind="ITEM",
            path=["Dưới 12 tháng", "Mệnh giá"],
        ),
        _row(
            "Từ 12 tháng đến 5 năm",
            [None] * 4,
            kind="GROUP",
            path=["Từ 12 tháng đến 5 năm"],
        ),
        _row(
            "Mệnh giá",
            ["-", "20", "5", "25"],
            kind="ITEM",
            path=["Từ 12 tháng đến 5 năm", "Mệnh giá"],
        ),
        _row("Trên 5 năm", [None] * 4, kind="GROUP", path=["Trên 5 năm"]),
        _row(
            "Mệnh giá",
            ["-", "-", "7", "7"],
            kind="ITEM",
            path=["Trên 5 năm", "Mệnh giá"],
        ),
        _row(None, ["10", "20", "42", "72"], kind="TOTAL", path=[None]),
    ]


def _table(rows: list[dict]) -> dict:
    return {
        "columns": _instrument_columns(),
        "continuation": "NONE",
        "rows": rows,
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }


def _ordinary_period_table() -> dict:
    return {
        "columns": [
            {"header_path_exact": ["30/6/2025", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["31/12/2024", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            _row("Trái phiếu", [None, None], kind="GROUP", path=["Trái phiếu"]),
            _row(
                "Từ 12 tháng đến dưới 5 năm",
                ["16.000.000", "16.948.000"],
                kind="ITEM",
                path=["Trái phiếu", "Từ 12 tháng đến dưới 5 năm"],
            ),
            _row(
                "Từ 5 năm trở lên",
                ["4.000.000", "4.000.000"],
                kind="ITEM",
                path=["Trái phiếu", "Từ 5 năm trở lên"],
            ),
            _row(
                "Chứng chỉ tiền gửi",
                [None, None],
                kind="GROUP",
                path=["Chứng chỉ tiền gửi"],
            ),
            _row(
                "Từ 6 tháng đến dưới 12 tháng",
                ["100.000", None],
                kind="ITEM",
                path=["Chứng chỉ tiền gửi", "Từ 6 tháng đến dưới 12 tháng"],
            ),
            _row(
                "Từ 12 tháng đến 5 năm",
                ["9.100.000", "2.300.000"],
                kind="ITEM",
                path=["Chứng chỉ tiền gửi", "Từ 12 tháng đến 5 năm"],
            ),
            _row(
                "Từ 5 năm trở lên",
                ["-", "54.579"],
                kind="ITEM",
                path=["Chứng chỉ tiền gửi", "Từ 5 năm trở lên"],
            ),
            _row(None, ["29.200.000", "23.302.579"], kind="TOTAL", path=[None]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }


def _section(title: str, tables: list[dict]) -> dict:
    return {
        "content_kind": "FINANCIAL_NOTE",
        "narratives_exact": [],
        "statement_type": "NOT_APPLICABLE",
        "tables": tables,
        "title_exact": title,
    }


def _page(rows: list[dict]) -> dict:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            _section(
                "THUYẾT MINH BÁO CÁO TÀI CHÍNH Tại ngày 31/03/2026",
                [],
            ),
            _section("10. PHÁT HÀNH GIẤY TỜ CÓ GIÁ", [_table(rows)]),
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


def test_transposed_one_current_period_is_closed_locally() -> None:
    candidate = _evaluate(_page(_one_period_rows()))
    assert candidate["status"] == READY
    assert {
        item["role"]: [cell["coefficient"] for cell in item["values"]]
        for item in candidate["mappings"]
    } == {
        "BOND": [20],
        "BOND_LONG": [0],
        "BOND_MEDIUM": [20],
        "BOND_SHORT": [0],
        "CD_LONG": [7],
        "CD_MEDIUM": [5],
        "CD_SHORT": [30],
        "CERTIFICATE_OF_DEPOSIT": [42],
        "FAMILY_ROOT_TOTAL": [72],
        "PROMISSORY_AND_BOND_LONG": [0],
        "PROMISSORY_AND_BOND_MEDIUM": [20],
        "PROMISSORY_AND_BOND_SHORT": [10],
        "PROMISSORY_AND_BOND_TOTAL": [30],
        "PROMISSORY_LONG": [0],
        "PROMISSORY_MEDIUM": [0],
        "PROMISSORY_NOTE": [10],
        "PROMISSORY_SHORT": [10],
    }


def test_transposed_single_instrument_plus_total_is_structurally_sufficient() -> None:
    table = {
        "columns": [
            {"header_path_exact": ["Trái phiếu", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Tổng cộng", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            _row(
                "Từ 12 tháng đến dưới 5 năm",
                [None, None],
                kind="GROUP",
                path=["Từ 12 tháng đến dưới 5 năm"],
            ),
            _row(
                "Mệnh giá",
                ["20", "20"],
                kind="ITEM",
                path=["Từ 12 tháng đến dưới 5 năm", "Mệnh giá"],
            ),
            _row(None, ["20", "20"], kind="TOTAL", path=[None]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    page = _page([])
    page["sections"][1]["tables"] = [table]
    candidate = _evaluate(page)
    by_role = {
        item["role"]: [cell["coefficient"] for cell in item["values"]]
        for item in candidate["mappings"]
    }
    assert by_role["BOND_MEDIUM"] == [20]
    assert by_role["BOND"] == [20]
    assert by_role["FAMILY_ROOT_TOTAL"] == [20]


def test_transposed_instrument_totals_without_tenor_breakdown_are_mappable() -> None:
    table = {
        "columns": [
            {"header_path_exact": ["Trái phiếu", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Chứng chỉ tiền gửi", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Tổng cộng", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [_row(None, ["20", "30", "50"], kind="TOTAL", path=[None])],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    page = _page([])
    page["sections"][1]["tables"] = [table]
    candidate = _evaluate(page)
    by_role = {
        item["role"]: [cell["coefficient"] for cell in item["values"]]
        for item in candidate["mappings"]
    }
    assert by_role["BOND"] == [20]
    assert by_role["CERTIFICATE_OF_DEPOSIT"] == [30]
    assert by_role["FAMILY_ROOT_TOTAL"] == [50]


def test_transposed_semantic_current_and_comparative_blocks_are_supported() -> None:
    current = _one_period_rows()
    comparative = copy.deepcopy(_one_period_rows())
    comparative[-1]["values_exact"] = ["8", "15", "35", "58"]
    comparative[1]["values_exact"] = ["8", "-", "25", "33"]
    comparative[3]["values_exact"] = ["-", "15", "4", "19"]
    comparative[5]["values_exact"] = ["-", "-", "6", "6"]
    rows = [
        _row("Số cuối kỳ", [None] * 4, kind="GROUP", path=["Số cuối kỳ"]),
        *current,
        _row("Số dư đầu kỳ", [None] * 4, kind="GROUP", path=["Số dư đầu kỳ"]),
        *comparative,
    ]
    candidate = _evaluate(_page(rows))
    assert candidate["status"] == READY
    root = next(item for item in candidate["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL")
    assert [cell["coefficient"] for cell in root["values"]] == [72, 58]


def test_transposed_dated_current_and_comparative_markers_bind_exact_dates() -> None:
    current = _one_period_rows()
    comparative = copy.deepcopy(_one_period_rows())
    comparative[-1]["values_exact"] = ["8", "15", "35", "58"]
    comparative[1]["values_exact"] = ["8", "-", "25", "33"]
    comparative[3]["values_exact"] = ["-", "15", "4", "19"]
    comparative[5]["values_exact"] = ["-", "-", "6", "6"]
    rows = [
        _row(
            "Số cuối kỳ tại 31/03/2026",
            [None] * 4,
            kind="GROUP",
            path=["Số cuối kỳ tại 31/03/2026"],
        ),
        *current,
        _row(
            "Số dư đầu kỳ tại 31/12/2025",
            [None] * 4,
            kind="GROUP",
            path=["Số dư đầu kỳ tại 31/12/2025"],
        ),
        *comparative,
    ]
    candidate = _evaluate(_page(rows))
    root = next(item for item in candidate["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL")
    assert [cell["coefficient"] for cell in root["values"]] == [72, 58]
    blocks = candidate["closure_receipt"]["table_receipts"][0]["lane_axis"]["blocks"]
    assert [block["lane_key"] for block in blocks] == [
        ["DATE", "2026-03-31"],
        ["DATE", "2025-12-31"],
    ]


def test_transposed_row_blocks_reject_column_period_evidence() -> None:
    rows = [
        _row("Số cuối kỳ", [None] * 4, kind="GROUP", path=["Số cuối kỳ"]),
        *_one_period_rows(),
        _row("Số dư đầu kỳ", [None] * 4, kind="GROUP", path=["Số dư đầu kỳ"]),
        *copy.deepcopy(_one_period_rows()),
    ]
    page = _page(rows)
    for column in page["sections"][1]["tables"][0]["columns"]:
        column["header_path_exact"].append("31/03/2026")
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    reasons = candidate["closure_receipt"]["table_receipts"][0]["lane_axis"]["reasons"]
    assert "TRANSPOSED_ROW_BLOCKS_CONFLICT_WITH_COLUMN_PERIOD_EVIDENCE" in reasons


def test_transposed_period_marker_cannot_carry_money_values() -> None:
    rows = [
        _row("Số cuối kỳ", ["1", "2", "3", "6"], kind="ITEM", path=["Số cuối kỳ"]),
        *_one_period_rows(),
    ]
    candidate = _evaluate(_page(rows))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    reasons = candidate["closure_receipt"]["table_receipts"][0]["lane_axis"]["reasons"]
    assert "TRANSPOSED_ROW_PERIOD_MARKER_HAS_MONEY_VALUES:r1" in reasons


def test_role_visible_only_in_current_block_remains_mappable() -> None:
    current = _one_period_rows()
    comparative = copy.deepcopy(_one_period_rows())
    comparative[1]["values_exact"] = ["8", "-", "25", "33"]
    comparative[3]["values_exact"] = ["-", "15", "4", "19"]
    comparative = comparative[:4] + comparative[6:]
    comparative[-1]["values_exact"] = ["8", "15", "29", "52"]
    rows = [
        _row("Số cuối kỳ", [None] * 4, kind="GROUP", path=["Số cuối kỳ"]),
        *current,
        _row("Số dư đầu kỳ", [None] * 4, kind="GROUP", path=["Số dư đầu kỳ"]),
        *comparative,
    ]
    candidate = _evaluate(_page(rows))
    assert candidate["status"] == READY
    cd_long = next(item for item in candidate["mappings"] if item["role"] == "CD_LONG")
    assert [cell["coefficient"] for cell in cd_long["values"]] == [7]


def test_transposed_horizontal_mismatch_is_unresolved() -> None:
    rows = _one_period_rows()
    rows[1]["values_exact"][-1] = "41"
    candidate = _evaluate(_page(rows))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert any(
        "TRANSPOSED_ROW_HORIZONTAL_EQUATION_MISMATCH" in item for item in candidate["reasons"]
    )


def test_transposed_total_column_must_be_explicit_and_unique() -> None:
    page = _page(_one_period_rows())
    table = page["sections"][1]["tables"][0]
    table["columns"][-1]["header_path_exact"] = ["Không rõ", "Triệu đồng"]
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_transposed_unique_equation_sealed_suffix_alignment_is_generic() -> None:
    rows = _one_period_rows()
    rows[1]["values_exact"] = ["10", "30", "40", None]
    candidate = _evaluate(_page(rows))
    assert candidate["status"] == READY
    receipt = candidate["closure_receipt"]["table_receipts"][0]
    assert receipt["value_alignment_receipt"]["row_ordinal"] == 2
    assert receipt["value_alignment_receipt"]["after_values_exact"] == [
        "10",
        None,
        "30",
        "40",
    ]


def test_dash_only_neighbor_rows_do_not_create_false_alignment_ambiguity() -> None:
    rows = _one_period_rows()
    rows[1]["values_exact"] = ["10", "30", "40", None]
    rows[2:2] = [
        _row(
            "Chiết khấu",
            ["-", None, "-", None],
            kind="ITEM",
            path=["Dưới 12 tháng", "Chiết khấu"],
        ),
        _row(
            "Phụ trội",
            ["-", None, "-", None],
            kind="ITEM",
            path=["Dưới 12 tháng", "Phụ trội"],
        ),
    ]
    candidate = _evaluate(_page(rows))
    assert candidate["status"] == READY
    receipt = candidate["closure_receipt"]["table_receipts"][0]
    assert receipt["value_alignment_receipt"]["row_ordinal"] == 2
    assert receipt["value_alignment_receipt"]["after_values_exact"] == [
        "10",
        None,
        "30",
        "40",
    ]


def test_transposed_multiple_row_suffix_shifts_require_one_joint_closure() -> None:
    rows = _one_period_rows()
    rows[1]["values_exact"] = ["10", "30", "40", None]
    rows[5]["values_exact"] = [None, "7", "7", None]
    candidate = _evaluate(_page(rows))
    assert candidate["status"] == READY
    receipt = candidate["closure_receipt"]["table_receipts"][0]["value_alignment_receipt"]
    assert [item["row_ordinal"] for item in receipt["row_repairs"]] == [2, 6]
    assert receipt["row_repairs"][0]["after_values_exact"] == ["10", None, "30", "40"]
    assert receipt["row_repairs"][1]["after_values_exact"] == [None, None, "7", "7"]


def test_transposed_multiple_equation_closing_alignments_remain_unresolved() -> None:
    rows = _one_period_rows()
    rows[1]["values_exact"] = ["-", "10", "10", None]
    rows[-1]["values_exact"] = ["-", "20", "22", "42"]
    candidate = _evaluate(_page(rows))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "value_alignment_receipt" not in candidate["closure_receipt"]["table_receipts"][0]


def test_label_only_parent_exact_frontier_proves_blank_child_zero() -> None:
    page = _page([])
    page["sections"][1]["tables"] = [_ordinary_period_table()]
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    short = next(item for item in candidate["mappings"] if item["role"] == "CD_SHORT")
    assert [cell["coefficient"] for cell in short["values"]] == [100000, 0]
    assert short["values"][1]["state"].startswith("INFERRED_")


def test_declared_metric_header_excludes_non_accounting_terms_control() -> None:
    page = _page([])
    control = {
        "columns": [
            {
                "header_path_exact": ["Số lượng đã phát hành (Trái phiếu)"],
                "value_kind": "MONEY",
            },
            {"header_path_exact": ["Giá trị (USD)"], "value_kind": "MONEY"},
            {
                "header_path_exact": ["Giá chuyển đổi dự kiến (VND/cổ phần)"],
                "value_kind": "MONEY",
            },
        ],
        "continuation": "NONE",
        "rows": [_row("Trái phiếu chuyển đổi", ["10", "20", "30"], kind="ITEM", path=[])],
        "title_exact": None,
        "unit_exact": None,
    }
    page["sections"][1]["tables"] = [_ordinary_period_table(), control]
    compiled = _compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    assert len(cluster["component_regions"]) == 1
    control_inventory = next(
        item for item in cluster["declared_money_table_inventory"] if item["table_id"] == "t2"
    )
    assert control_inventory["disposition"] == "EXCLUDED_TYPED_CONTROL"
    assert (
        control_inventory["classification"]["typed_control_disposition"]
        == "NON_ACCOUNTING_CONVERTIBLE_BOND_TERMS_CONTROL"
    )


def test_control_header_cannot_hide_a_declared_family_role() -> None:
    page = _page([])
    control = {
        "columns": [
            {
                "header_path_exact": ["Số lượng đã phát hành (Trái phiếu)"],
                "value_kind": "MONEY",
            }
        ],
        "continuation": "NONE",
        "rows": [_row("Trái phiếu", ["10"], kind="GROUP", path=["Trái phiếu"])],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    page["sections"][1]["tables"] = [_ordinary_period_table(), control]
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert any("TYPED_CONTROL_AND_DECLARED_FAMILY_ROLE_CONFLICT" in x for x in cluster["reasons"])


def _two_date_context_table() -> dict:
    return {
        "columns": [
            {"header_path_exact": ["31/03/2026", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["31/12/2025", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [_row("Khoản mục khác", ["1", "1"], kind="ITEM", path=[])],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }


def test_transposed_document_period_context_requires_repeated_tables() -> None:
    page = _page(_one_period_rows())
    page["sections"][0]["title_exact"] = "THUYẾT MINH BÁO CÁO TÀI CHÍNH"
    page["sections"][0]["tables"] = [_two_date_context_table()]
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["closure_receipt"]["document_period_context"]["resolution"] == (
        "EXACT_TWO_DATE_MONEY_TABLE_CONTEXT_NOT_REPEATED"
    )


def test_transposed_document_period_context_uses_repeated_table_consensus() -> None:
    page = _page(_one_period_rows())
    page["sections"][0]["title_exact"] = "THUYẾT MINH BÁO CÁO TÀI CHÍNH"
    page["sections"][0]["tables"] = [_two_date_context_table(), _two_date_context_table()]
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    root = next(item for item in candidate["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL")
    assert root["values"][0]["coefficient"] == 72


def test_transposed_date_and_semantic_period_conflict_is_unresolved() -> None:
    page = _page(_one_period_rows())
    for column in page["sections"][1]["tables"][0]["columns"]:
        column["header_path_exact"].extend(["31/03/2026", "Số dư đầu kỳ"])
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    lane_reasons = candidate["closure_receipt"]["table_receipts"][0]["lane_axis"]["reasons"]
    assert "TRANSPOSED_DATE_SEMANTIC_PERIOD_CONFLICT" in lane_reasons


def test_transposed_conflicting_semantic_period_aliases_are_unresolved() -> None:
    page = _page(_one_period_rows())
    page["sections"][0]["title_exact"] = "THUYẾT MINH BÁO CÁO TÀI CHÍNH"
    for column in page["sections"][1]["tables"][0]["columns"]:
        column["header_path_exact"].extend(["Số cuối kỳ", "Số dư đầu kỳ"])
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    lane_reasons = candidate["closure_receipt"]["table_receipts"][0]["lane_axis"]["reasons"]
    assert any("PERIOD_ROLE" in reason for reason in lane_reasons)


def test_transposed_conflicting_money_magnitudes_are_unresolved() -> None:
    page = _page(_one_period_rows())
    page["sections"][1]["tables"][0]["columns"][0]["header_path_exact"].append("Nghìn VND")
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    unit_axis = candidate["closure_receipt"]["table_receipts"][0]["unit_axis"]
    assert unit_axis["complete"] is False


def test_transposed_unclassified_money_column_is_not_silently_ignored() -> None:
    page = _page(_one_period_rows())
    table = page["sections"][1]["tables"][0]
    table["columns"].insert(
        -1,
        {"header_path_exact": ["Giá trị khác", "Triệu đồng"], "value_kind": "MONEY"},
    )
    for row in table["rows"]:
        row["values_exact"].insert(-1, "999")
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    lane_axis = candidate["closure_receipt"]["table_receipts"][0]["lane_axis"]
    assert lane_axis["unclassified_money_column_ordinals"] == [4]


def test_tenor_parent_instrument_child_hierarchy_is_resolved_generically() -> None:
    table = {
        "columns": [
            {"header_path_exact": ["Số cuối kỳ", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Số đầu kỳ", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            _row("Dưới 12 tháng", ["30", "25"], kind="SUBTOTAL", path=["Dưới 12 tháng"]),
            _row(
                "Mệnh giá chứng chỉ tiền gửi bằng VND",
                ["30", "25"],
                kind="ITEM",
                path=["Dưới 12 tháng", "Mệnh giá chứng chỉ tiền gửi bằng VND"],
            ),
            _row(
                "Từ 12 tháng đến dưới 5 năm",
                ["25", "20"],
                kind="SUBTOTAL",
                path=["Từ 12 tháng đến dưới 5 năm"],
            ),
            _row(
                "Mệnh giá chứng chỉ tiền gửi bằng VND",
                ["5", "4"],
                kind="ITEM",
                path=[
                    "Từ 12 tháng đến dưới 5 năm",
                    "Mệnh giá chứng chỉ tiền gửi bằng VND",
                ],
            ),
            _row(
                "Mệnh giá trái phiếu bằng VND",
                ["20", "16"],
                kind="ITEM",
                path=["Từ 12 tháng đến dưới 5 năm", "Mệnh giá trái phiếu bằng VND"],
            ),
            _row("Từ 5 năm trở lên", ["7", "6"], kind="SUBTOTAL", path=["Từ 5 năm trở lên"]),
            _row(
                "Mệnh giá chứng chỉ tiền gửi bằng VND",
                ["7", "6"],
                kind="ITEM",
                path=["Từ 5 năm trở lên", "Mệnh giá chứng chỉ tiền gửi bằng VND"],
            ),
            _row(None, ["62", "51"], kind="TOTAL", path=[None]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    page = _page([])
    page["sections"][1]["tables"] = [table]
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    by_role = {
        item["role"]: [cell["coefficient"] for cell in item["values"]]
        for item in candidate["mappings"]
    }
    assert by_role["CERTIFICATE_OF_DEPOSIT"] == [42, 35]
    assert by_role["BOND"] == [20, 16]
    assert by_role["CD_SHORT"] == [30, 25]
    assert by_role["CD_MEDIUM"] == [5, 4]
    assert by_role["CD_LONG"] == [7, 6]
    assert by_role["BOND_MEDIUM"] == [20, 16]
    assert by_role["FAMILY_ROOT_TOTAL"] == [62, 51]


def test_instrument_child_with_two_tenor_ancestors_is_ambiguous() -> None:
    table = {
        "columns": [
            {"header_path_exact": ["Số cuối kỳ", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Số đầu kỳ", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            _row("Dưới 12 tháng", ["10", "9"], kind="SUBTOTAL", path=["Dưới 12 tháng"]),
            _row(
                "Mệnh giá chứng chỉ tiền gửi bằng VND",
                ["10", "9"],
                kind="ITEM",
                path=[
                    "Dưới 12 tháng",
                    "Từ 12 tháng đến dưới 5 năm",
                    "Mệnh giá chứng chỉ tiền gửi bằng VND",
                ],
            ),
            _row(None, ["10", "9"], kind="TOTAL", path=[None]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    page = _page([])
    page["sections"][1]["tables"] = [table]
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []


def test_generic_capital_bond_alias_accepts_issuer_suffix_without_routing() -> None:
    table = {
        "columns": [
            {"header_path_exact": ["30/06/2026", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["31/12/2025", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            _row(
                "Trái phiếu tăng vốn BIDV",
                ["5", "4"],
                kind="ITEM",
                path=["Trái phiếu tăng vốn BIDV"],
            ),
            _row(None, ["5", "4"], kind="TOTAL", path=[None]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    page = _page([])
    page["sections"][1]["tables"] = [table]
    candidate = _evaluate(page)
    by_role = {
        item["role"]: [cell["coefficient"] for cell in item["values"]]
        for item in candidate["mappings"]
    }
    assert by_role["OTHER_ISSUED_PAPER"] == [5, 4]
    assert by_role["FAMILY_ROOT_TOTAL"] == [5, 4]


def test_declared_alias_prefix_policy_rejects_unknown_role() -> None:
    evaluation = _json("tm-issued-valuable-papers-evaluation-v1.json")
    evaluation["row_alias_prefix_roles"] = ["UNKNOWN_ROLE"]
    with pytest.raises(ValueError, match="row_alias_prefix_roles"):
        compile_gemini_json_multitable_hierarchical_family_specs_v1(
            _json("tm-issued-valuable-papers-topology-v1.json"),
            evaluation,
            _json("tm-issued-valuable-papers-schema-binding-v1.json"),
        )
