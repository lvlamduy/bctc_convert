from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_equity_matrix_accounting_family_v1 import (
    READY,
    UNRESOLVED,
    build_gemini_json_equity_matrix_region_query_receipt_v1,
    coalesce_gemini_json_equity_matrix_document_v1,
    compile_gemini_json_equity_matrix_family_specs_v1,
    evaluate_gemini_json_equity_matrix_family_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_segment_report_matrix_v1 import (
    _period_ends,
    validate_gemini_json_segment_report_candidate_binding_v1,
)

ROOT = Path(__file__).resolve().parents[2]
VERSION_A = "gfpstorev1:json:" + "1" * 64
VERSION_B = "gfpstorev1:json:" + "2" * 64
DOCUMENT_ID = "gfpstorev1:document:" + "3" * 64
SOURCE_SHA = "4" * 64


@pytest.mark.parametrize(
    ("surface", "expected"),
    [
        ("31/03/2026", {"2026-03-31"}),
        ("31-03-2026", {"2026-03-31"}),
        ("31.03.2026", {"2026-03-31"}),
        ("31 tháng 03 năm 2026", {"2026-03-31"}),
        ("31/02/2026", set()),
        ("Năm 2026", set()),
        (
            "Giai đoạn từ 01/01/2026 đến 31/03/2026 và giai đoạn từ 01/01/2025 đến 31/03/2025",
            {"2026-03-31", "2025-03-31"},
        ),
    ],
)
def test_period_end_parser_preserves_exact_visible_date_semantics(
    surface: str, expected: set[str]
) -> None:
    assert _period_ends(surface) == expected


def _spec_values() -> list[dict]:
    names = ("topology", "evaluation", "schema-binding")
    return [
        json.loads(
            (
                ROOT / "config/families" / f"tm-consolidated-segment-report-{name}-v1.json"
            ).read_text()
        )
        for name in names
    ]


def _compiled() -> dict:
    values = _spec_values()
    return compile_gemini_json_equity_matrix_family_specs_v1(*values)


def _table(*, year: int, blank_source_only: bool = False) -> dict:
    return {
        "columns": [
            {
                "header_path_exact": [f"31/12/{year}", "Ngân hàng\nTriệu VND"],
                "value_kind": "MONEY",
            },
            {
                "header_path_exact": [f"31/12/{year}", "Cho thuê tài chính\nTriệu VND"],
                "value_kind": "MONEY",
            },
            {
                "header_path_exact": [f"31/12/{year}", "Loại trừ\nTriệu VND"],
                "value_kind": "MONEY",
            },
            {
                "header_path_exact": [f"31/12/{year}", "Tổng cộng\nTriệu VND"],
                "value_kind": "MONEY",
            },
        ],
        "continuation": "NONE",
        "rows": [
            {
                "hierarchy_path_exact": ["Doanh thu"],
                "label_exact": "Doanh thu",
                "row_kind": "TOTAL",
                "values_exact": ["100", None, "(10)", "90"]
                if blank_source_only
                else ["100", "20", "(10)", "110"],
            },
            {
                "hierarchy_path_exact": ["Chi phí"],
                "label_exact": "Chi phí",
                "row_kind": "TOTAL",
                "values_exact": ["(50)", "(5)", "5", "(50)"],
            },
        ],
        "title_exact": "Báo cáo bộ phận theo lĩnh vực kinh doanh",
        "unit_exact": "Triệu VND",
    }


def _record(*, version: str, page: int, year: int, scope: str = "HỢP NHẤT") -> dict:
    return {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": {
            "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
            "sections": [
                {
                    "content_kind": "FINANCIAL_NOTE",
                    "narratives_exact": [],
                    "statement_type": "NOT_APPLICABLE",
                    "tables": [_table(year=year)],
                    "title_exact": (
                        f"THUYẾT MINH BÁO CÁO TÀI CHÍNH {scope} NĂM {year}\nBÁO CÁO BỘ PHẬN"
                    ),
                }
            ],
            "status": "FINANCIAL_NOTE_CONTENT",
        },
        "page_json_version_id": version,
        "physical_page": page,
        "selected_page_ordinal": page,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA,
    }


def _primary_flow_period_record(
    *, version: str, page: int, current_end: str, comparative_end: str
) -> dict:
    current_year = int(current_end[:4])
    record = _record(version=version, page=page, year=current_year)
    record["page_json"]["status"] = "PRIMARY_FINANCIAL_STATEMENT"
    section = record["page_json"]["sections"][0]
    section["statement_type"] = "INCOME_STATEMENT"
    section["tables"] = []
    section["title_exact"] = (
        "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG KINH DOANH HỢP NHẤT "
        f"CHO KỲ KẾT THÚC {current_end[8:10]}/{current_end[5:7]}/{current_end[:4]} "
        f"VÀ {comparative_end[8:10]}/{comparative_end[5:7]}/{comparative_end[:4]}"
    )
    return record


def _primary_stock_period_record(
    *, version: str, page: int, current_end: str, comparative_end: str
) -> dict:
    current_year = int(current_end[:4])
    record = _record(version=version, page=page, year=current_year)
    record["page_json"]["status"] = "PRIMARY_FINANCIAL_STATEMENT"
    section = record["page_json"]["sections"][0]
    section["statement_type"] = "BALANCE_SHEET"
    section["tables"] = []
    section["title_exact"] = (
        "BÁO CÁO TÌNH HÌNH TÀI CHÍNH HỢP NHẤT TẠI "
        f"{current_end[8:10]}/{current_end[5:7]}/{current_end[:4]} "
        f"VÀ {comparative_end[8:10]}/{comparative_end[5:7]}/{comparative_end[:4]}"
    )
    return record


def _transposed_table(*, year: int, mismatch: bool = False) -> dict:
    return {
        "columns": [
            {
                "header_path_exact": [f"31/12/{year}", "Doanh thu", "Triệu VND"],
                "value_kind": "MONEY",
            },
            {
                "header_path_exact": [f"31/12/{year}", "Chi phí", "Triệu VND"],
                "value_kind": "MONEY",
            },
        ],
        "continuation": "NONE",
        "rows": [
            {
                "hierarchy_path_exact": ["Ngân hàng"],
                "label_exact": "Ngân hàng",
                "row_kind": "ITEM",
                "values_exact": ["100", "(50)"],
            },
            {
                "hierarchy_path_exact": ["Cho thuê tài chính"],
                "label_exact": "Cho thuê tài chính",
                "row_kind": "ITEM",
                "values_exact": ["20", "(5)"],
            },
            {
                "hierarchy_path_exact": ["Loại trừ"],
                "label_exact": "Loại trừ",
                "row_kind": "ITEM",
                "values_exact": ["(10)", "5"],
            },
            {
                "hierarchy_path_exact": ["Tổng cộng"],
                "label_exact": "Tổng cộng",
                "row_kind": "TOTAL",
                "values_exact": ["999" if mismatch else "110", "(50)"],
            },
        ],
        "title_exact": "Báo cáo bộ phận theo lĩnh vực kinh doanh",
        "unit_exact": "Triệu VND",
    }


def _candidate(records: list[dict]) -> tuple[dict, dict]:
    compiled = _compiled()
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=records, compiled_specs=compiled
    )
    assert cluster["status"] == READY
    query = build_gemini_json_equity_matrix_region_query_receipt_v1(
        cluster["component_regions"], owner_receipt=cluster["owner_receipt"]
    )
    candidate = evaluate_gemini_json_equity_matrix_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={item["page_json_version_id"]: item["page_json"] for item in records},
        compiled_specs=compiled,
        query_receipt=query,
        document_unit_context_evidence=cluster["document_unit_context_evidence"],
    )
    return candidate, cluster


def test_maps_two_periods_and_validates_candidate_binding() -> None:
    candidate, cluster = _candidate(
        [
            _record(version=VERSION_A, page=1, year=2025),
            _record(version=VERSION_B, page=2, year=2024),
        ]
    )
    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 6
    assert all(len(item["values"]) == 2 for item in candidate["mappings"])
    validate_gemini_json_segment_report_candidate_binding_v1(
        candidate,
        document={"source_logical_name": "fixture.pdf", "source_sha256": SOURCE_SHA},
        cluster=cluster,
        compiled_specs=_compiled(),
    )


def test_source_blank_is_preserved_without_backsolve() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    record["page_json"]["sections"][0]["tables"][0] = _table(year=2025, blank_source_only=True)
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assert any(
        item["state"] == "SOURCE_BLANK" for item in candidate["closure_receipt"]["blank_cell_axis"]
    )
    assert all(
        value["source_text"] is not None
        for mapping in candidate["mappings"]
        for value in mapping["values"]
    )
    source_only = [
        cell["axis_role"]
        for receipt in candidate["closure_receipt"]["table_receipts"]
        for cell in receipt["cell_axis"]
        if cell["axis_role"].startswith("SOURCE_ONLY:")
    ]
    assert source_only and all("cho thue tai chinh" in role for role in source_only)


def test_visible_total_mismatch_fails_closed() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    record["page_json"]["sections"][0]["tables"][0]["rows"][0]["values_exact"][-1] = "999"
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "VISIBLE_SEGMENT_TOTAL_MISMATCH" in candidate["reasons"]


def test_rounding_residual_of_one_unit_is_receipted() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    record["page_json"]["sections"][0]["tables"][0]["rows"][0]["values_exact"][-1] = "111"
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assert any(
        equation["status"] == "EXACT_ROUNDING_RESIDUAL"
        for equation in candidate["closure_receipt"]["equations"]
    )


def test_unbalanced_closing_parenthesis_is_not_backsolved_by_total() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    row = record["page_json"]["sections"][0]["tables"][0]["rows"][0]
    row["values_exact"] = ["100", "20", "10)", "110"]
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "SEGMENT_MONEY_CELL_AMBIGUOUS" in candidate["reasons"]


def test_explicit_comparative_year_outranks_owner_current_year() -> None:
    record = _record(version=VERSION_A, page=1, year=2024)
    record["page_json"]["sections"][0]["title_exact"] = (
        "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT NĂM 2025\nBÁO CÁO BỘ PHẬN"
    )
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assert {
        value["axis_role"] for mapping in candidate["mappings"] for value in mapping["values"]
    } == {"COMPARATIVE_PERIOD"}


def test_explicit_periods_do_not_require_global_fragment_order_consistency() -> None:
    records = [
        _record(version="gfpstorev1:json:" + str(index) * 64, page=index, year=year)
        for index, year in enumerate((2025, 2024, 2024, 2025), start=1)
    ]
    for record in records[:2]:
        record["page_json"]["sections"][0]["tables"][0]["rows"] = [
            record["page_json"]["sections"][0]["tables"][0]["rows"][0]
        ]
    for record in records[2:]:
        record["page_json"]["sections"][0]["tables"][0]["rows"] = [
            record["page_json"]["sections"][0]["tables"][0]["rows"][1]
        ]
    candidate, _cluster = _candidate(records)
    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 6
    assert all(len(mapping["values"]) == 2 for mapping in candidate["mappings"])


def test_period_order_does_not_leak_between_unrelated_same_branch_signatures() -> None:
    records = [
        _record(version="gfpstorev1:json:" + str(index) * 64, page=index, year=year)
        for index, year in enumerate((2025, 2024, 2025, 2024), start=1)
    ]
    for record in records[2:]:
        table = record["page_json"]["sections"][0]["tables"][0]
        for column in table["columns"]:
            column["header_path_exact"] = column["header_path_exact"][1:]
        for row, label in zip(table["rows"], ("Tài sản", "Nợ phải trả"), strict=True):
            row["label_exact"] = label
            row["hierarchy_path_exact"] = [label]

    candidate, _cluster = _candidate(records)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "SEGMENT_PERIOD_NOT_RESOLVED" in candidate["reasons"]
    assert all(
        receipt.get("period_assignment_evidence") is None
        for receipt in candidate["closure_receipt"]["table_receipts"]
    )


def test_unknown_axes_cannot_collapse_to_total_only_ready() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    columns = record["page_json"]["sections"][0]["tables"][0]["columns"]
    for index, label in enumerate(("Bộ phận bí ẩn A", "Bộ phận bí ẩn B", "Bộ phận bí ẩn C")):
        columns[index]["header_path_exact"] = ["Năm 2025", f"{label}\nTriệu VND"]
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "INSUFFICIENT_DECLARED_SEGMENT_AXIS_COVERAGE" in candidate["reasons"]


def test_source_only_metric_values_cannot_satisfy_mapped_axis_coverage() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    table = record["page_json"]["sections"][0]["tables"][0]
    for row in table["rows"]:
        row["values_exact"][2] = None
    table["rows"].append(
        {
            "hierarchy_path_exact": ["Khấu hao"],
            "label_exact": "Khấu hao",
            "row_kind": "ITEM",
            "values_exact": ["1", "2", "3", "6"],
        }
    )
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "INSUFFICIENT_DECLARED_SEGMENT_AXIS_COVERAGE" in candidate["reasons"]


def test_axis_from_the_other_branch_is_not_silently_treated_as_source_only() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    columns = record["page_json"]["sections"][0]["tables"][0]["columns"]
    columns[1]["header_path_exact"] = ["Năm 2025", "Miền Bắc\nTriệu VND"]
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "SEGMENT_AXIS_CONTRADICTS_SELECTED_BRANCH" in candidate["reasons"]


def test_bare_other_axis_is_branch_scoped_for_geographic_tables() -> None:
    geographic = _record(version=VERSION_A, page=1, year=2025)
    table = geographic["page_json"]["sections"][0]["tables"][0]
    table["title_exact"] = "Báo cáo bộ phận theo khu vực địa lý"
    for column, label in zip(
        table["columns"], ("Miền Bắc", "Khác", "Loại trừ", "Tổng cộng"), strict=True
    ):
        column["header_path_exact"][-1] = f"{label}\nTriệu VND"
    candidate, _cluster = _candidate([geographic])
    assert candidate["status"] == READY
    assert any(":OTHER:" in mapping["role"] for mapping in candidate["mappings"])

    business = _record(version=VERSION_A, page=1, year=2025)
    business_table = business["page_json"]["sections"][0]["tables"][0]
    business_table["columns"][1]["header_path_exact"][-1] = "Khác\nTriệu VND"
    business_candidate, _cluster = _candidate([business])
    assert business_candidate["status"] == READY
    assert not any(":OTHER:" in mapping["role"] for mapping in business_candidate["mappings"])
    assert any(
        cell["axis_role"].startswith("SOURCE_ONLY:") and "khac" in cell["axis_role"]
        for receipt in business_candidate["closure_receipt"]["table_receipts"]
        for cell in receipt["cell_axis"]
    )


@pytest.mark.parametrize("surface", ["−50", "（５０）", "－５０"])
def test_equivalent_unicode_money_spellings_are_canonicalized(surface: str) -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    record["page_json"]["sections"][0]["tables"][0]["rows"][1]["values_exact"][0] = surface
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    bank_expense = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "BUSINESS:BANK:EXPENSE"
    )
    assert bank_expense["values"][0]["coefficient"] == -50
    assert bank_expense["values"][0]["source_text"] == surface
    assert bank_expense["values"][0]["state"] == "NORMALIZED_UNICODE_ACCOUNTING_INTEGER"


def test_transposed_matrix_maps_and_validates_source_only_total_frontier() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    record["page_json"]["sections"][0]["tables"][0] = _transposed_table(year=2025)
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 6
    equations = candidate["closure_receipt"]["equations"]
    assert len(equations) == 2
    assert all(equation["status"] == "EXACT" for equation in equations)
    assert all(len(equation["term_cells"]) == 3 for equation in equations)


def test_leaf_table_branch_outranks_ancestor_section_branch() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    section = record["page_json"]["sections"][0]
    section["title_exact"] = (
        "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT NĂM 2025\nBÁO CÁO BỘ PHẬN THEO LĨNH VỰC KINH DOANH"
    )
    table = section["tables"][0]
    table["title_exact"] = "Báo cáo bộ phận theo khu vực địa lý"
    for column, label in zip(
        table["columns"],
        ("Miền Bắc", "Miền Trung", "Loại trừ", "Tổng cộng"),
        strict=True,
    ):
        column["header_path_exact"][-1] = f"{label}\nTriệu VND"
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assert all(mapping["role"].startswith("GEOGRAPHIC:") for mapping in candidate["mappings"])


def test_transposed_visible_total_mismatch_fails_closed() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    record["page_json"]["sections"][0]["tables"][0] = _transposed_table(year=2025, mismatch=True)
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == UNRESOLVED
    assert "VISIBLE_SEGMENT_TOTAL_MISMATCH" in candidate["reasons"]


def test_transposed_ordinal_only_axis_label_falls_back_to_hierarchy_leaf() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    table = _transposed_table(year=2025)
    table["title_exact"] = "Báo cáo bộ phận theo khu vực địa lý"
    for row, label in zip(
        table["rows"],
        ("Miền Bắc", "Miền Trung", "Loại trừ", "Tổng cộng"),
        strict=True,
    ):
        row["label_exact"] = label
        row["hierarchy_path_exact"] = [label]
    table["rows"][0]["label_exact"] = "1."
    record["page_json"]["sections"][0]["tables"][0] = table

    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} >= {
        "GEOGRAPHIC:NORTH:REVENUE",
        "GEOGRAPHIC:NORTH:EXPENSE",
    }


def test_transposed_two_period_blocks_are_closed_independently() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    table = _transposed_table(year=2025)
    current_rows = copy.deepcopy(table["rows"])
    comparative_rows = copy.deepcopy(table["rows"])
    for row in current_rows:
        row["label_exact"] += " Năm 2025"
        row["hierarchy_path_exact"] = ["31/12/2025", row["label_exact"]]
    for row in comparative_rows:
        row["label_exact"] += " Năm 2024"
        row["hierarchy_path_exact"] = ["31/12/2024", row["label_exact"]]
    table["rows"] = current_rows + comparative_rows
    table["title_exact"] += " Năm 2025 và 2024"
    record["page_json"]["sections"][0]["tables"][0] = table
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 6
    assert all(len(mapping["values"]) == 2 for mapping in candidate["mappings"])
    assert len(candidate["closure_receipt"]["equations"]) == 4


@pytest.mark.parametrize("orientation", ["METRIC_ROWS", "METRIC_COLUMNS"])
def test_repeated_column_period_blocks_are_partitioned_locally(orientation: str) -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    table = _table(year=2025) if orientation == "METRIC_ROWS" else _transposed_table(year=2025)
    comparative_columns = copy.deepcopy(table["columns"])
    for column in comparative_columns:
        column["header_path_exact"] = [
            surface.replace("2025", "2024") for surface in column["header_path_exact"]
        ]
    table["columns"] += comparative_columns
    for row in table["rows"]:
        row["values_exact"] += copy.deepcopy(row["values_exact"])
    table["title_exact"] += " Năm 2025 và 2024"
    record["page_json"]["sections"][0]["tables"][0] = table

    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 6
    assert all(len(mapping["values"]) == 2 for mapping in candidate["mappings"])
    assert len(candidate["closure_receipt"]["equations"]) == 4

    table["columns"][0]["header_path_exact"].append("So sánh năm 2024")
    ambiguous, _cluster = _candidate([record])
    assert ambiguous["status"] == UNRESOLVED
    assert "SEGMENT_COLUMN_PERIOD_AMBIGUOUS" in ambiguous["reasons"]


@pytest.mark.parametrize("orientation", ["METRIC_ROWS", "METRIC_COLUMNS"])
def test_adjacent_axis_major_period_pairs_share_one_authenticated_order(
    orientation: str,
) -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    table = _table(year=2025) if orientation == "METRIC_ROWS" else _transposed_table(year=2025)
    interleaved_columns = []
    for index, column in enumerate(table["columns"]):
        current = copy.deepcopy(column)
        comparative = copy.deepcopy(column)
        current["header_path_exact"] = [
            surface for surface in current["header_path_exact"] if "2025" not in surface
        ]
        comparative["header_path_exact"] = [
            surface for surface in comparative["header_path_exact"] if "2025" not in surface
        ]
        if index == 0:
            current["header_path_exact"].insert(0, "31/12/2025")
            comparative["header_path_exact"].insert(0, "31/12/2024")
        interleaved_columns.extend([current, comparative])
    table["columns"] = interleaved_columns
    for row in table["rows"]:
        row["values_exact"] = [
            duplicate
            for value in row["values_exact"]
            for duplicate in (copy.deepcopy(value), copy.deepcopy(value))
        ]
    table["title_exact"] += " Năm 2025 và 2024"
    record["page_json"]["sections"][0]["tables"][0] = table

    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 6
    assert all(len(mapping["values"]) == 2 for mapping in candidate["mappings"])
    assert len(candidate["closure_receipt"]["equations"]) == 4


@pytest.mark.parametrize("orientation", ["METRIC_ROWS", "METRIC_COLUMNS"])
def test_multi_year_spanner_does_not_override_local_column_period(orientation: str) -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    table = _table(year=2025) if orientation == "METRIC_ROWS" else _transposed_table(year=2025)
    comparative_columns = copy.deepcopy(table["columns"])
    for column in comparative_columns:
        column["header_path_exact"] = [
            surface.replace("2025", "2024") for surface in column["header_path_exact"]
        ]
    table["columns"] += comparative_columns
    for column in table["columns"]:
        column["header_path_exact"].insert(0, "Năm 2025 và 2024")
    for row in table["rows"]:
        row["values_exact"] += copy.deepcopy(row["values_exact"])
    table["title_exact"] += " Năm 2025 và 2024"
    record["page_json"]["sections"][0]["tables"][0] = table
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 6
    assert all(len(mapping["values"]) == 2 for mapping in candidate["mappings"])


@pytest.mark.parametrize("orientation", ["METRIC_ROWS", "METRIC_COLUMNS"])
@pytest.mark.parametrize("marker_mode", ["FIRST", "PREFIX", "LAST", "FIRST_WITH_COMMON_SPANNER"])
def test_merged_period_header_propagates_over_repeated_complete_block(
    orientation: str, marker_mode: str
) -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    table = _table(year=2025) if orientation == "METRIC_ROWS" else _transposed_table(year=2025)
    for column in table["columns"]:
        column["header_path_exact"] = column["header_path_exact"][1:]
    comparative_columns = copy.deepcopy(table["columns"])
    marker_positions = (
        [0]
        if marker_mode in {"FIRST", "FIRST_WITH_COMMON_SPANNER"}
        else list(range(min(2, len(table["columns"]))))
        if marker_mode == "PREFIX"
        else [len(table["columns"]) - 1]
    )
    for position in marker_positions:
        table["columns"][position]["header_path_exact"].insert(0, "31/12/2025")
        comparative_columns[position]["header_path_exact"].insert(0, "31/12/2024")
    table["columns"] += comparative_columns
    if marker_mode == "FIRST_WITH_COMMON_SPANNER":
        for column in table["columns"]:
            column["header_path_exact"].insert(0, "Năm 2025 và 2024")
    for row in table["rows"]:
        row["values_exact"] += copy.deepcopy(row["values_exact"])
    table["title_exact"] += " Năm 2025 và 2024"
    record["page_json"]["sections"][0]["tables"][0] = table

    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 6
    assert all(len(mapping["values"]) == 2 for mapping in candidate["mappings"])
    assert len(candidate["closure_receipt"]["equations"]) == 4


def test_multi_year_and_unit_conflicts_fail_closed() -> None:
    period = _record(version=VERSION_A, page=1, year=2025)
    period["page_json"]["sections"][0]["tables"][0]["columns"][0]["header_path_exact"].append(
        "So sánh năm 2024"
    )
    period_candidate, _cluster = _candidate([period])
    assert period_candidate["status"] == UNRESOLVED
    assert "SEGMENT_COLUMN_PERIOD_AMBIGUOUS" in period_candidate["reasons"]

    unit = _record(version=VERSION_A, page=1, year=2025)
    unit["page_json"]["sections"][0]["tables"][0]["columns"][0]["header_path_exact"].append(
        "Nghìn VND"
    )
    unit_candidate, _cluster = _candidate([unit])
    assert unit_candidate["status"] == UNRESOLVED
    assert "SEGMENT_TABLE_UNIT_CONFLICT" in unit_candidate["reasons"]


def test_multi_year_title_is_allowed_when_every_cell_has_local_period() -> None:
    primary = _primary_flow_period_record(
        version="gfpstorev1:json:" + "8" * 64,
        page=1,
        current_end="2025-12-31",
        comparative_end="2024-12-31",
    )
    record = _record(version=VERSION_A, page=2, year=2025)
    table = record["page_json"]["sections"][0]["tables"][0]
    source_rows = copy.deepcopy(table["rows"])
    table["title_exact"] += " Năm 2025 và 2024"
    table["columns"] = [
        {**column, "header_path_exact": column["header_path_exact"][1:]}
        for column in table["columns"]
    ]
    table["rows"] = [
        {
            "hierarchy_path_exact": ["31/12/2025"],
            "label_exact": "31/12/2025",
            "row_kind": "GROUP",
            "values_exact": [None, None, None, None],
        },
        *source_rows,
        {
            "hierarchy_path_exact": ["31/12/2024"],
            "label_exact": "31/12/2024",
            "row_kind": "GROUP",
            "values_exact": [None, None, None, None],
        },
        *copy.deepcopy(source_rows),
    ]
    candidate, _cluster = _candidate([primary, record])
    assert candidate["status"] == READY
    assert all(len(mapping["values"]) == 2 for mapping in candidate["mappings"])


def test_future_or_stale_period_cannot_replace_authenticated_reporting_year() -> None:
    for year in (2026, 2023):
        record = _record(version=VERSION_A, page=1, year=year)
        record["page_json"]["sections"][0]["title_exact"] = (
            "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT NĂM 2025\nBÁO CÁO BỘ PHẬN"
        )
        candidate, _cluster = _candidate([record])
        assert candidate["status"] == UNRESOLVED
        assert "SEGMENT_PERIOD_OUTSIDE_AUTHENTICATED_REPORTING_WINDOW" in candidate["reasons"]


def test_primary_reporting_year_cannot_be_replaced_by_later_scope_year() -> None:
    primary = _record(version=VERSION_A, page=1, year=2025)
    primary["page_json"]["status"] = "PRIMARY_FINANCIAL_STATEMENT"
    primary["page_json"]["sections"][0]["tables"] = []
    primary["page_json"]["sections"][0]["title_exact"] = (
        "BÁO CÁO TÌNH HÌNH TÀI CHÍNH HỢP NHẤT NĂM 2025"
    )

    future = _record(version=VERSION_B, page=2, year=2026)
    future_cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[primary, future], compiled_specs=_compiled()
    )
    assert future_cluster["status"] == UNRESOLVED
    assert "SEGMENT_REPORTING_YEAR_CONTEXT_CONFLICT" in future_cluster["reasons"]

    comparative = _record(version=VERSION_B, page=2, year=2024)
    candidate, cluster = _candidate([primary, comparative])
    assert cluster["owner_receipt"]["reporting_year_axis"] == [2025]
    assert candidate["status"] == READY
    assert {
        value["axis_role"] for mapping in candidate["mappings"] for value in mapping["values"]
    } == {"COMPARATIVE_PERIOD"}


def test_primary_current_date_persists_across_comparative_only_continuation() -> None:
    primary = _record(version=VERSION_A, page=1, year=2026)
    primary["page_json"]["status"] = "PRIMARY_FINANCIAL_STATEMENT"
    primary["page_json"]["sections"][0]["tables"] = []
    primary["page_json"]["sections"][0]["title_exact"] = (
        "BÁO CÁO TÌNH HÌNH TÀI CHÍNH HỢP NHẤT TẠI NGÀY 31/03/2026"
    )
    comparative = copy.deepcopy(primary)
    comparative["page_json_version_id"] = "gfpstorev1:json:" + "8" * 64
    comparative["physical_page"] = 2
    comparative["selected_page_ordinal"] = 2
    comparative["page_json"]["sections"][0]["title_exact"] = "SỐ SO SÁNH TẠI NGÀY 31/12/2025"
    segment = _record(version=VERSION_B, page=3, year=2026)
    segment["page_json"]["sections"][0]["title_exact"] = (
        "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT\nBÁO CÁO BỘ PHẬN"
    )
    for column in segment["page_json"]["sections"][0]["tables"][0]["columns"]:
        column["header_path_exact"] = column["header_path_exact"][1:]
    candidate, cluster = _candidate([primary, comparative, segment])
    assert cluster["owner_receipt"]["reporting_year_axis"] == [2026]
    assert cluster["owner_receipt"]["reporting_period_axis"][0]["period_end"] == "2026-03-31"
    assert candidate["status"] == READY
    assert {
        value["period_end"] for mapping in candidate["mappings"] for value in mapping["values"]
    } == {"2026-03-31"}


def test_primary_period_end_is_bound_by_metric_temporal_class() -> None:
    stock = _record(version="gfpstorev1:json:" + "6" * 64, page=1, year=2026)
    stock["page_json"]["status"] = "PRIMARY_FINANCIAL_STATEMENT"
    stock_section = stock["page_json"]["sections"][0]
    stock_section["statement_type"] = "BALANCE_SHEET"
    stock_section["tables"] = []
    stock_section["title_exact"] = (
        "BÁO CÁO TÌNH HÌNH TÀI CHÍNH HỢP NHẤT TẠI NGÀY 30/06/2026 VÀ 31/12/2025"
    )

    flow = _record(version="gfpstorev1:json:" + "7" * 64, page=2, year=2026)
    flow["page_json"]["status"] = "PRIMARY_FINANCIAL_STATEMENT"
    flow_section = flow["page_json"]["sections"][0]
    flow_section["statement_type"] = "INCOME_STATEMENT"
    flow_section["tables"] = []
    flow_section["title_exact"] = (
        "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG KINH DOANH HỢP NHẤT CHO KỲ KẾT THÚC 30/06/2026 VÀ 30/06/2025"
    )

    current = _record(version=VERSION_A, page=3, year=2026)
    comparative = _record(version=VERSION_B, page=4, year=2025)
    for record in (current, comparative):
        year = 2026 if record is current else 2025
        record["page_json"]["sections"][0]["title_exact"] = (
            f"THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT NĂM {year}\nBÁO CÁO BỘ PHẬN"
        )
        table = record["page_json"]["sections"][0]["tables"][0]
        for column in table["columns"]:
            column["header_path_exact"][0] = f"Năm {year}"
        for label in ("Tài sản", "Nợ phải trả"):
            row = copy.deepcopy(table["rows"][0])
            row["label_exact"] = label
            row["hierarchy_path_exact"] = [label]
            table["rows"].append(row)

    candidate, cluster = _candidate([stock, flow, current, comparative])
    assert candidate["status"] == READY
    assert {
        (item["temporal_class"], item["period_role"], item["period_end"])
        for item in cluster["owner_receipt"]["reporting_period_axis"]
    } == {
        ("FLOW", "CURRENT_PERIOD", "2026-06-30"),
        ("FLOW", "COMPARATIVE_PERIOD", "2025-06-30"),
        ("STOCK", "CURRENT_PERIOD", "2026-06-30"),
        ("STOCK", "COMPARATIVE_PERIOD", "2025-12-31"),
    }
    endpoints = {
        (mapping["role"].rsplit(":", 1)[-1], value["axis_role"]): value["period_end"]
        for mapping in candidate["mappings"]
        for value in mapping["values"]
    }
    assert endpoints[("REVENUE", "COMPARATIVE_PERIOD")] == "2025-06-30"
    assert endpoints[("EXPENSE", "COMPARATIVE_PERIOD")] == "2025-06-30"
    assert endpoints[("ASSETS", "COMPARATIVE_PERIOD")] == "2025-12-31"
    assert endpoints[("LIABILITIES", "COMPARATIVE_PERIOD")] == "2025-12-31"


def test_local_table_dates_are_preserved_in_mapping_and_equation_receipts() -> None:
    current = _record(version=VERSION_A, page=1, year=2026)
    for column in current["page_json"]["sections"][0]["tables"][0]["columns"]:
        column["header_path_exact"] = column["header_path_exact"][1:]
    current["page_json"]["sections"][0]["tables"][0]["title_exact"] += " tại ngày 31/03/2026"
    comparative = _record(version=VERSION_B, page=2, year=2025)
    for column in comparative["page_json"]["sections"][0]["tables"][0]["columns"]:
        column["header_path_exact"] = column["header_path_exact"][1:]
    comparative["page_json"]["sections"][0]["tables"][0]["title_exact"] += " tại ngày 31/12/2025"
    candidate, _cluster = _candidate([current, comparative])
    assert candidate["status"] == READY
    endpoints = {
        value["axis_role"]: value["period_end"]
        for mapping in candidate["mappings"]
        for value in mapping["values"]
    }
    assert endpoints == {
        "CURRENT_PERIOD": "2026-03-31",
        "COMPARATIVE_PERIOD": "2025-12-31",
    }
    assert {
        (equation["axis_role"], equation["period_end"])
        for equation in candidate["closure_receipt"]["equations"]
    } == {
        ("CURRENT_PERIOD", "2026-03-31"),
        ("COMPARATIVE_PERIOD", "2025-12-31"),
    }


def test_duplicate_semantic_period_with_different_exact_endpoints_fails_closed() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    tables = record["page_json"]["sections"][0]["tables"]
    for column in tables[0]["columns"]:
        column["header_path_exact"] = column["header_path_exact"][1:]
    tables[0]["title_exact"] += " tại ngày 31/03/2025"
    duplicate = copy.deepcopy(tables[0])
    duplicate["title_exact"] = duplicate["title_exact"].replace("31/03/2025", "30/06/2025")
    tables.append(duplicate)
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "CONFLICTING_DUPLICATE_SEGMENT_AXIS_METRIC_PERIOD_CELL" in candidate["reasons"]


def test_one_equation_cannot_mix_distinct_or_missing_period_endpoints() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    columns = record["page_json"]["sections"][0]["tables"][0]["columns"]
    for column in columns:
        column["header_path_exact"] = column["header_path_exact"][1:]
    columns[0]["header_path_exact"].insert(0, "31/03/2025")
    columns[-1]["header_path_exact"].insert(0, "30/06/2025")
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "SEGMENT_EQUATION_PERIOD_END_CONFLICT" in candidate["reasons"]


@pytest.mark.parametrize("orientation", ["METRIC_ROWS", "METRIC_COLUMNS"])
def test_unique_merged_period_end_propagates_within_one_table_role(
    orientation: str,
) -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    record["page_json"]["sections"][0]["title_exact"] = (
        "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT NĂM 2025\nBÁO CÁO BỘ PHẬN"
    )
    table = (
        record["page_json"]["sections"][0]["tables"][0]
        if orientation == "METRIC_ROWS"
        else _transposed_table(year=2025)
    )
    for column in table["columns"]:
        column["header_path_exact"] = column["header_path_exact"][1:]
    table["columns"][0]["header_path_exact"].insert(0, "31 tháng 03 năm 2025")
    record["page_json"]["sections"][0]["tables"][0] = table
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assert {
        value["period_end"] for mapping in candidate["mappings"] for value in mapping["values"]
    } == {"2025-03-31"}
    assert {equation["period_end"] for equation in candidate["closure_receipt"]["equations"]} == {
        "2025-03-31"
    }


def test_single_visible_year_does_not_invent_current_without_reporting_context() -> None:
    record = _record(version=VERSION_A, page=1, year=2024)
    record["page_json"]["sections"][0]["title_exact"] = (
        "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT\nBÁO CÁO BỘ PHẬN"
    )
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "SEGMENT_CURRENT_PERIOD_CONTEXT_NOT_AUTHENTICATED" in candidate["reasons"]


def test_mapped_cells_require_an_exact_source_visible_period_end() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    record["page_json"]["sections"][0]["title_exact"] = (
        "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT NĂM 2025\nBÁO CÁO BỘ PHẬN"
    )
    for column in record["page_json"]["sections"][0]["tables"][0]["columns"]:
        column["header_path_exact"] = column["header_path_exact"][1:]
    candidate, cluster = _candidate([record])

    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "SEGMENT_PERIOD_END_NOT_RESOLVED" in candidate["reasons"]
    assert {
        item["authority_class"]
        for item in candidate["closure_receipt"]["period_receipt"]["period_assignment_axis"]
    } == {"NO_EXACT_PERIOD_END"}
    validate_gemini_json_segment_report_candidate_binding_v1(
        candidate,
        document={"source_logical_name": "fixture.pdf", "source_sha256": SOURCE_SHA},
        cluster=cluster,
        compiled_specs=_compiled(),
    )


def test_single_undated_metric_does_not_gain_current_role_from_absence() -> None:
    primary = _primary_flow_period_record(
        version="gfpstorev1:json:" + "7" * 64,
        page=1,
        current_end="2025-12-31",
        comparative_end="2024-12-31",
    )
    current = _record(version=VERSION_A, page=2, year=2025)
    current_table = current["page_json"]["sections"][0]["tables"][0]
    for column in current_table["columns"]:
        column["header_path_exact"] = column["header_path_exact"][1:]
    profit_before_tax = copy.deepcopy(current_table["rows"][0])
    profit_before_tax["label_exact"] = "Lợi nhuận trước thuế"
    profit_before_tax["hierarchy_path_exact"] = ["Lợi nhuận trước thuế"]
    current_table["rows"].append(profit_before_tax)

    comparative = _record(version=VERSION_B, page=3, year=2024)
    candidate, cluster = _candidate([primary, current, comparative])

    assert candidate["status"] == UNRESOLVED
    assert "SEGMENT_PERIOD_NOT_RESOLVED" in candidate["reasons"]
    assert not any(
        equation["metric_role"] == "PROFIT_BEFORE_TAX"
        for equation in candidate["closure_receipt"]["equations"]
    )
    validate_gemini_json_segment_report_candidate_binding_v1(
        candidate,
        document={"source_logical_name": "fixture.pdf", "source_sha256": SOURCE_SHA},
        cluster=cluster,
        compiled_specs=_compiled(),
    )


def test_unique_same_section_period_carrier_binds_undated_metric_sibling() -> None:
    primary = _primary_flow_period_record(
        version="gfpstorev1:json:" + "8" * 64,
        page=1,
        current_end="2025-12-31",
        comparative_end="2024-12-31",
    )
    current = _record(version=VERSION_A, page=2, year=2025)
    current_tables = current["page_json"]["sections"][0]["tables"]
    flow = current_tables[0]
    for column in flow["columns"]:
        column["header_path_exact"] = column["header_path_exact"][1:]
    stock = _table(year=2025)
    for row, label in zip(stock["rows"], ("Tài sản", "Nợ phải trả"), strict=True):
        row["label_exact"] = label
        row["hierarchy_path_exact"] = [label]
    current_tables.append(stock)

    comparative = _record(version=VERSION_B, page=3, year=2024)
    comparative_tables = comparative["page_json"]["sections"][0]["tables"]
    comparative_stock = _table(year=2024)
    for row, label in zip(comparative_stock["rows"], ("Tài sản", "Nợ phải trả"), strict=True):
        row["label_exact"] = label
        row["hierarchy_path_exact"] = [label]
    comparative_tables.append(comparative_stock)

    candidate, cluster = _candidate([primary, current, comparative])
    assert candidate["status"] == READY
    assert {
        value["axis_role"]
        for mapping in candidate["mappings"]
        if mapping["role"].endswith(":REVENUE")
        for value in mapping["values"]
    } == {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"}
    evidence = candidate["closure_receipt"]["table_receipts"][0].get("period_assignment_evidence")
    assert evidence is not None
    assert evidence["rule"] == "UNIQUE_EXPLICIT_PERIOD_ROLE_WITHIN_SAME_PAGE_SECTION"
    validate_gemini_json_segment_report_candidate_binding_v1(
        candidate,
        document={"source_logical_name": "fixture.pdf", "source_sha256": SOURCE_SHA},
        cluster=cluster,
        compiled_specs=_compiled(),
    )

    from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

    evidence["carrier_metric_signatures"] = [["REVENUE"]]
    candidate["candidate_id"] = "gjeqmfv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in candidate.items() if key != "candidate_id"}
    )
    with pytest.raises(ValueError, match="sibling period carrier"):
        validate_gemini_json_segment_report_candidate_binding_v1(
            candidate,
            document={"source_logical_name": "fixture.pdf", "source_sha256": SOURCE_SHA},
            cluster=cluster,
            compiled_specs=_compiled(),
        )


def test_unique_visible_role_in_mixed_table_binds_complete_undated_metric_block() -> None:
    current = _record(version=VERSION_A, page=1, year=2025)
    current_table = current["page_json"]["sections"][0]["tables"][0]
    for column in current_table["columns"]:
        column["header_path_exact"] = column["header_path_exact"][1:]
    stock_rows = copy.deepcopy(current_table["rows"])
    for row, label in zip(stock_rows, ("Tài sản tại ngày 31/12/2025", "Nợ phải trả"), strict=True):
        row["label_exact"] = label
        row["hierarchy_path_exact"] = [label]
    current_table["rows"].extend(stock_rows)

    comparative = _record(version=VERSION_B, page=2, year=2024)
    comparative_table = comparative["page_json"]["sections"][0]["tables"][0]
    comparative_stock = copy.deepcopy(comparative_table["rows"])
    for row, label in zip(comparative_stock, ("Tài sản", "Nợ phải trả"), strict=True):
        row["label_exact"] = label
        row["hierarchy_path_exact"] = [label]
    comparative_table["rows"].extend(comparative_stock)

    candidate, cluster = _candidate([current, comparative])
    assert candidate["status"] == READY
    assert {
        value["axis_role"]
        for mapping in candidate["mappings"]
        if mapping["role"].endswith(":REVENUE")
        for value in mapping["values"]
    } == {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"}
    receipt = candidate["closure_receipt"]["table_receipts"][0]
    assert receipt["period_role_by_metric"] == {
        "EXPENSE": "CURRENT_PERIOD",
        "REVENUE": "CURRENT_PERIOD",
    }
    assert receipt["period_assignment_evidence"]["rule"] == (
        "UNIQUE_VISIBLE_PERIOD_ROLE_WITHIN_SAME_TABLE"
    )
    validate_gemini_json_segment_report_candidate_binding_v1(
        candidate,
        document={"source_logical_name": "fixture.pdf", "source_sha256": SOURCE_SHA},
        cluster=cluster,
        compiled_specs=_compiled(),
    )


def test_unique_section_date_binds_one_complete_undated_table_signature() -> None:
    current = _record(version=VERSION_A, page=1, year=2025)
    current["page_json"]["sections"][0]["title_exact"] = (
        "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT\nBÁO CÁO BỘ PHẬN TẠI NGÀY 30/09/2025"
    )
    current_table = current["page_json"]["sections"][0]["tables"][0]
    for column in current_table["columns"]:
        column["header_path_exact"] = column["header_path_exact"][1:]
    current_stock = copy.deepcopy(current_table["rows"])
    for row, label in zip(current_stock, ("Tài sản", "Nợ phải trả"), strict=True):
        row["label_exact"] = label
        row["hierarchy_path_exact"] = [label]
    current_table["rows"].extend(current_stock)

    comparative = _record(version=VERSION_B, page=2, year=2024)
    comparative_stock = _table(year=2024)
    for row, label in zip(comparative_stock["rows"], ("Tài sản", "Nợ phải trả"), strict=True):
        row["label_exact"] = label
        row["hierarchy_path_exact"] = [label]
    comparative["page_json"]["sections"][0]["tables"].append(comparative_stock)
    candidate, cluster = _candidate([current, comparative])
    assert candidate["status"] == READY
    assert all(len(mapping["values"]) == 2 for mapping in candidate["mappings"])
    evidence = candidate["closure_receipt"]["table_receipts"][0]["period_assignment_evidence"]
    assert evidence["rule"] == "UNIQUE_SECTION_PERIOD_ROLE_FOR_UNDATED_TABLE"
    assert evidence["period_role"] == "CURRENT_PERIOD"
    assert evidence["section_period_end_axis"][0]["period_end"] == "2025-09-30"
    validate_gemini_json_segment_report_candidate_binding_v1(
        candidate,
        document={"source_logical_name": "fixture.pdf", "source_sha256": SOURCE_SHA},
        cluster=cluster,
        compiled_specs=_compiled(),
    )


def test_consecutive_scope_year_pair_authenticates_role_but_not_period_end() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    record["page_json"]["sections"][0]["title_exact"] = (
        "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT NĂM 2025 VÀ 2024\nBÁO CÁO BỘ PHẬN"
    )
    for column in record["page_json"]["sections"][0]["tables"][0]["columns"]:
        column["header_path_exact"] = column["header_path_exact"][1:]
    candidate, cluster = _candidate([record])
    assert cluster["owner_receipt"]["reporting_year_axis"] == [2025]
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "SEGMENT_PERIOD_END_NOT_RESOLVED" in candidate["reasons"]


@pytest.mark.parametrize(
    ("surface", "coherent_total"),
    [("1.2.3", "133"), ("12,34", "1.244"), ("1 23", "133")],
)
def test_invalid_integer_grouping_is_not_hidden_by_equation(
    surface: str, coherent_total: str
) -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    row = record["page_json"]["sections"][0]["tables"][0]["rows"][0]
    row["values_exact"][0] = surface
    row["values_exact"][-1] = coherent_total
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == UNRESOLVED
    assert "SEGMENT_MONEY_CELL_INVALID" in candidate["reasons"]


def test_nfkc_equivalent_axis_headers_are_not_lost() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    columns = record["page_json"]["sections"][0]["tables"][0]["columns"]
    columns[0]["header_path_exact"][1] = "Ｎｇâｎ ｈàｎｇ\nTriệu VND"
    columns[-1]["header_path_exact"][1] = "Ｔổｎｇ ｃộｎｇ\nTriệu VND"
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} >= {
        "BUSINESS:BANK:REVENUE",
        "BUSINESS:TOTAL:REVENUE",
    }


@pytest.mark.parametrize(
    ("column_marker", "row_marker"),
    [("(1)", "[1]"), ("(a)", "[a]"), ("¹", "²")],
)
def test_bounded_footnote_markers_and_ordinal_only_labels_do_not_hide_graph(
    column_marker: str, row_marker: str
) -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    table = record["page_json"]["sections"][0]["tables"][0]
    for column in table["columns"]:
        column["header_path_exact"][-1] += f" {column_marker}"
    for row in table["rows"]:
        row["label_exact"] += f" {row_marker}"
        row["hierarchy_path_exact"] = [row["label_exact"]]
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY

    ordinal = _record(version=VERSION_A, page=1, year=2025)
    ordinal["page_json"]["sections"][0]["tables"][0]["rows"][0]["label_exact"] = "1."
    ordinal_candidate, _cluster = _candidate([ordinal])
    assert ordinal_candidate["status"] == READY


@pytest.mark.parametrize("prefix", ["II.1.", "1.1"])
def test_multilevel_structural_ordinals_do_not_hide_metric_labels(prefix: str) -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    for row in record["page_json"]["sections"][0]["tables"][0]["rows"]:
        row["label_exact"] = f"{prefix} {row['label_exact']}"
        row["hierarchy_path_exact"] = [row["label_exact"]]
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY


@pytest.mark.parametrize("prefix", ["1.", "II.1."])
def test_structural_ordinal_without_following_space_is_tolerated(prefix: str) -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    for row in record["page_json"]["sections"][0]["tables"][0]["rows"]:
        row["label_exact"] = f"{prefix}{row['label_exact']}"
        row["hierarchy_path_exact"] = [row["label_exact"]]
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY


def test_numeric_superscript_footnote_does_not_become_a_magnitude_digit() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    record["page_json"]["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "100¹"
    candidate, _cluster = _candidate([record])
    mapping = next(
        item for item in candidate["mappings"] if item["role"] == "BUSINESS:BANK:REVENUE"
    )
    assert mapping["values"][0]["coefficient"] == 100
    assert mapping["values"][0]["source_text"] == "100¹"
    assert mapping["values"][0]["state"] == "NORMALIZED_TRAILING_FOOTNOTE_INTEGER"


@pytest.mark.parametrize(
    "label",
    [
        "Cho thuê tài chính / Chứng khoán / Khác",
        "Cho thuê tài chính và Chứng khoán và Khác",
        "Cho thuê tài chính, Chứng khoán và Khác",
    ],
)
def test_declared_source_only_composite_is_consumed_but_not_mapped(label: str) -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    columns = record["page_json"]["sections"][0]["tables"][0]["columns"]
    columns[1]["header_path_exact"][1] = f"{label}\nTriệu VND"
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assert all(
        "c2" not in value["cell_ref"]["column_id"]
        for mapping in candidate["mappings"]
        for value in mapping["values"]
    )
    assert all(
        len(equation["term_cells"]) == 3 for equation in candidate["closure_receipt"]["equations"]
    )


def test_novel_non_target_axis_is_consumed_when_declared_mapping_coverage_remains() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    columns = record["page_json"]["sections"][0]["tables"][0]["columns"]
    columns[1]["header_path_exact"][-1] = "Ngân hàng số\nTriệu VND"
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assert any(
        cell["axis_role"].startswith("SOURCE_ONLY:") and "ngan hang so" in cell["axis_role"]
        for receipt in candidate["closure_receipt"]["table_receipts"]
        for cell in receipt["cell_axis"]
    )
    assert all("ngan hang so" not in mapping["role"] for mapping in candidate["mappings"])


def test_unlabelled_all_blank_money_spacer_is_preserved_without_veto() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    table = record["page_json"]["sections"][0]["tables"][0]
    table["columns"].append({"header_path_exact": [], "value_kind": "MONEY"})
    for row in table["rows"]:
        row["values_exact"].append(None)
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assert any(
        cell["cell_ref"]["column_id"] == "c5" and cell["state"] == "SOURCE_BLANK"
        for cell in candidate["closure_receipt"]["blank_cell_axis"]
    )


@pytest.mark.parametrize("carrier", ["title", "narrative"])
def test_unit_can_be_read_from_bounded_visible_context(carrier: str) -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    section = record["page_json"]["sections"][0]
    table = section["tables"][0]
    table["unit_exact"] = None
    for column in table["columns"]:
        column["header_path_exact"] = [
            surface.replace("\nTriệu VND", "") for surface in column["header_path_exact"]
        ]
    if carrier == "title":
        table["title_exact"] += " (Đơn vị tính: triệu đồng)"
    else:
        section["narratives_exact"] = ["Đơn vị tính: triệu đồng"]
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assert {mapping["unit"] for mapping in candidate["mappings"]} == {"MILLION_VND"}


@pytest.mark.parametrize(
    ("carrier", "surface"),
    [
        ("title", " (Triệu VND)"),
        ("narrative", "Số liệu được trình bày bằng triệu đồng"),
    ],
)
def test_common_explicit_unit_carrier_phrases_are_canonicalized(carrier: str, surface: str) -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    section = record["page_json"]["sections"][0]
    table = section["tables"][0]
    table["unit_exact"] = None
    for column in table["columns"]:
        column["header_path_exact"] = [
            member.replace("\nTriệu VND", "") for member in column["header_path_exact"]
        ]
    if carrier == "title":
        table["title_exact"] += surface
    else:
        section["narratives_exact"] = [surface]
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assert {mapping["unit"] for mapping in candidate["mappings"]} == {"MILLION_VND"}


def test_unit_can_cross_adjacent_sections_inside_selected_owner_scope() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    table_section = record["page_json"]["sections"][0]
    table = table_section["tables"][0]
    table["unit_exact"] = None
    for column in table["columns"]:
        column["header_path_exact"] = [
            surface.replace("\nTriệu VND", "") for surface in column["header_path_exact"]
        ]
    context_section = copy.deepcopy(table_section)
    context_section["tables"] = []
    context_section["narratives_exact"] = ["Đơn vị tính: triệu đồng"]
    table_section["title_exact"] = "BÁO CÁO BỘ PHẬN THEO LĨNH VỰC KINH DOANH"
    table_section["narratives_exact"] = []
    record["page_json"]["sections"] = [context_section, table_section]

    candidate, cluster = _candidate([record])
    assert candidate["status"] == READY
    assert {mapping["unit"] for mapping in candidate["mappings"]} == {"MILLION_VND"}
    assert cluster["document_unit_context_evidence"]["status"] == "UNIQUE_BOUNDED_SEGMENT_UNIT"


def test_document_unit_evidence_is_reparsed_from_its_visible_source_text() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    section = record["page_json"]["sections"][0]
    table = section["tables"][0]
    table["unit_exact"] = None
    for column in table["columns"]:
        column["header_path_exact"] = [
            member.replace("\nTriệu VND", "") for member in column["header_path_exact"]
        ]
    section["narratives_exact"] = ["Đơn vị tính: triệu đồng"]
    candidate, cluster = _candidate([record])
    assert candidate["status"] == READY

    from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

    contexts = [
        cluster["document_unit_context_evidence"],
        candidate["closure_receipt"]["unit_receipt"]["document_unit_context_evidence"],
    ]
    for context in contexts:
        context["evidence_axis"][0]["source_exact"] = "Đơn vị tính: nghìn đồng"
        context["evidence_axis_sha256"] = canonical_json_sha256_v1(context["evidence_axis"])
        material = {
            "canonical_unit": context["canonical_unit"],
            "evidence_axis": context["evidence_axis"],
            "evidence_axis_sha256": context["evidence_axis_sha256"],
            "rule": context["rule"],
            "status": context["status"],
        }
        context["document_unit_context_sha256"] = canonical_json_sha256_v1(material)
    candidate["candidate_id"] = "gjeqmfv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in candidate.items() if key != "candidate_id"}
    )
    with pytest.raises(ValueError, match="unit evidence contradicts source text"):
        validate_gemini_json_segment_report_candidate_binding_v1(
            candidate,
            document={"source_logical_name": "fixture.pdf", "source_sha256": SOURCE_SHA},
            cluster=cluster,
            compiled_specs=_compiled(),
        )


def test_table_local_unit_outranks_earlier_lower_specificity_context() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    selected_section = record["page_json"]["sections"][0]
    context_section = copy.deepcopy(selected_section)
    context_section["tables"] = []
    context_section["narratives_exact"] = ["Đơn vị tính: nghìn đồng"]
    selected_section["title_exact"] = "BÁO CÁO BỘ PHẬN THEO LĨNH VỰC KINH DOANH"
    record["page_json"]["sections"] = [context_section, selected_section]

    candidate, cluster = _candidate([record])
    assert cluster["document_unit_context_evidence"]["status"] == ("REJECTED_BOUNDED_SEGMENT_UNIT")
    assert candidate["status"] == READY
    assert {mapping["unit"] for mapping in candidate["mappings"]} == {"MILLION_VND"}


def test_unitless_table_inherits_only_from_same_page_section_sibling() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    section = record["page_json"]["sections"][0]
    geographic = _transposed_table(year=2025)
    geographic["title_exact"] = "Báo cáo bộ phận theo khu vực địa lý"
    geographic["unit_exact"] = None
    for row, label in zip(
        geographic["rows"],
        ("Miền Bắc", "Miền Trung", "Loại trừ", "Tổng cộng"),
        strict=True,
    ):
        row["label_exact"] = label
        row["hierarchy_path_exact"] = [label]
    for column in geographic["columns"]:
        column["header_path_exact"] = [
            surface.replace("Triệu VND", "") for surface in column["header_path_exact"]
        ]
    section["tables"].append(geographic)

    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assignment = candidate["closure_receipt"]["unit_receipt"]["table_unit_assignment_axis"][1]
    assert assignment["source"] == "SAME_PAGE_SECTION_EXPLICIT_SIBLING_UNIT"
    assert assignment["canonical_unit"] == "MILLION_VND"
    assert assignment["carrier_regions"]


def test_unitless_table_does_not_inherit_across_conflicting_section_context() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    business_section = record["page_json"]["sections"][0]
    context_section = copy.deepcopy(business_section)
    context_section["tables"] = []
    context_section["title_exact"] = "BÁO CÁO BỘ PHẬN"
    context_section["narratives_exact"] = ["Đơn vị tính: nghìn đồng"]
    geographic_section = copy.deepcopy(business_section)
    geographic_section["title_exact"] = "BÁO CÁO BỘ PHẬN THEO KHU VỰC ĐỊA LÝ"
    geographic = _transposed_table(year=2025)
    geographic["title_exact"] = "Báo cáo bộ phận theo khu vực địa lý"
    geographic["unit_exact"] = None
    for row, label in zip(
        geographic["rows"],
        ("Miền Bắc", "Miền Trung", "Loại trừ", "Tổng cộng"),
        strict=True,
    ):
        row["label_exact"] = label
        row["hierarchy_path_exact"] = [label]
    for column in geographic["columns"]:
        column["header_path_exact"] = [
            surface.replace("Triệu VND", "") for surface in column["header_path_exact"]
        ]
    geographic_section["tables"] = [geographic]
    record["page_json"]["sections"] = [
        business_section,
        context_section,
        geographic_section,
    ]

    candidate, _cluster = _candidate([record])
    assert candidate["status"] == UNRESOLVED
    assert "SEGMENT_DOCUMENT_UNIT_CONFLICT" in candidate["reasons"]


@pytest.mark.parametrize("total_label", [None, "Tổng cộng"])
def test_blank_metric_group_can_bind_adjacent_unlabelled_total_row(
    total_label: str | None,
) -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    table = record["page_json"]["sections"][0]["tables"][0]
    table["rows"] += [
        {
            "hierarchy_path_exact": ["Tài sản"],
            "label_exact": "Tài sản",
            "row_kind": "GROUP",
            "values_exact": [None, None, None, None],
        },
        {
            "hierarchy_path_exact": ["Tài sản", total_label],
            "label_exact": total_label,
            "row_kind": "TOTAL",
            "values_exact": ["200", "40", "(20)", "220"],
        },
    ]
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert by_role["BUSINESS:BANK:ASSETS"]["values"][0]["coefficient"] == 200
    assert by_role["BUSINESS:ELIMINATION:ASSETS"]["values"][0]["coefficient"] == -20
    assert by_role["BUSINESS:TOTAL:ASSETS"]["values"][0]["coefficient"] == 220


def test_blank_metric_group_binds_truly_unlabelled_advisory_item_row() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    table = record["page_json"]["sections"][0]["tables"][0]
    table["rows"] += [
        {
            "hierarchy_path_exact": ["Tài sản"],
            "label_exact": "Tài sản",
            "row_kind": "GROUP",
            "values_exact": [None, None, None, None],
        },
        {
            "hierarchy_path_exact": [],
            "label_exact": None,
            "row_kind": "ITEM",
            "values_exact": ["200", "40", "(20)", "220"],
        },
    ]
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} >= {
        "BUSINESS:BANK:ASSETS",
        "BUSINESS:ELIMINATION:ASSETS",
        "BUSINESS:TOTAL:ASSETS",
    }


def test_blank_group_heading_is_not_a_competing_semantic_value_row() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    rows = record["page_json"]["sections"][0]["tables"][0]["rows"]
    rows.insert(
        0,
        {
            "hierarchy_path_exact": ["Doanh thu"],
            "label_exact": "I. Doanh thu",
            "row_kind": "GROUP",
            "values_exact": [None, None, None, None],
        },
    )

    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    bank_revenue = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "BUSINESS:BANK:REVENUE"
    )
    assert bank_revenue["values"][0]["coefficient"] == 100
    assert "CONFLICTING_DUPLICATE_SEGMENT_AXIS_METRIC_PERIOD_CELL" not in candidate["reasons"]


def test_metric_group_does_not_override_contradictory_total_hierarchy() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    table = record["page_json"]["sections"][0]["tables"][0]
    table["rows"] += [
        {
            "hierarchy_path_exact": ["Tài sản"],
            "label_exact": "Tài sản",
            "row_kind": "GROUP",
            "values_exact": [None, None, None, None],
        },
        {
            "hierarchy_path_exact": ["Nợ phải trả", "Tổng cộng"],
            "label_exact": "Tổng cộng",
            "row_kind": "TOTAL",
            "values_exact": ["200", "40", "(20)", "220"],
        },
    ]
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == UNRESOLVED
    assert "SEGMENT_METRIC_GROUP_TOTAL_HIERARCHY_CONFLICT" in candidate["reasons"]


def test_generic_metric_group_can_bind_its_adjacent_visible_total() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    table = record["page_json"]["sections"][0]["tables"][0]
    table["rows"] += [
        {
            "hierarchy_path_exact": ["Lợi nhuận trước thuế"],
            "label_exact": "Lợi nhuận trước thuế",
            "row_kind": "GROUP",
            "values_exact": [None, None, None, None],
        },
        {
            "hierarchy_path_exact": ["Lợi nhuận trước thuế", "Tổng cộng"],
            "label_exact": "Tổng cộng",
            "row_kind": "TOTAL",
            "values_exact": ["200", "40", "(20)", "220"],
        },
    ]
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} >= {
        "BUSINESS:BANK:PROFIT_BEFORE_TAX",
        "BUSINESS:ELIMINATION:PROFIT_BEFORE_TAX",
        "BUSINESS:TOTAL:PROFIT_BEFORE_TAX",
    }


def test_generic_total_leaf_uses_its_unique_metric_hierarchy_without_group_row() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    table = record["page_json"]["sections"][0]["tables"][0]
    table["rows"].append(
        {
            "hierarchy_path_exact": ["Tài sản", "Tổng cộng"],
            "label_exact": "Tổng cộng",
            "row_kind": "TOTAL",
            "values_exact": ["200", "40", "(20)", "220"],
        }
    )
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} >= {
        "BUSINESS:BANK:ASSETS",
        "BUSINESS:ELIMINATION:ASSETS",
        "BUSINESS:TOTAL:ASSETS",
    }


@pytest.mark.parametrize("label", ["Tổng cộng Năm 2025", "Tổng cộng 2025", "Cộng năm 2025"])
def test_generic_total_leaf_tolerates_bounded_period_suffix(label: str) -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    record["page_json"]["sections"][0]["tables"][0]["rows"].append(
        {
            "hierarchy_path_exact": ["Tài sản", label],
            "label_exact": label,
            "row_kind": "TOTAL",
            "values_exact": ["200", "40", "(20)", "220"],
        }
    )
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} >= {
        "BUSINESS:BANK:ASSETS",
        "BUSINESS:ELIMINATION:ASSETS",
        "BUSINESS:TOTAL:ASSETS",
    }


def test_deepest_metric_label_outranks_hierarchy_ancestor() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    rows = record["page_json"]["sections"][0]["tables"][0]["rows"]
    row = rows[0]
    row["label_exact"] = "Tài sản cố định"
    row["hierarchy_path_exact"] = ["Tài sản", "Tài sản cố định"]
    rows[1]["label_exact"] = "Lợi nhuận trước thuế"
    rows[1]["hierarchy_path_exact"] = ["Lợi nhuận trước thuế"]
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} >= {
        "BUSINESS:BANK:FIXED_ASSETS",
        "BUSINESS:ELIMINATION:FIXED_ASSETS",
        "BUSINESS:TOTAL:FIXED_ASSETS",
    }


def test_metric_label_and_deepest_hierarchy_role_conflict_fails_closed() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    row = record["page_json"]["sections"][0]["tables"][0]["rows"][0]
    row["label_exact"] = "Tài sản"
    row["hierarchy_path_exact"] = ["Tài sản", "Tài sản cố định"]
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "SEGMENT_METRIC_ROW_AMBIGUOUS" in candidate["reasons"]


def test_metric_labels_tolerate_hierarchy_only_and_period_suffix() -> None:
    hierarchy = _record(version=VERSION_A, page=1, year=2025)
    for row in hierarchy["page_json"]["sections"][0]["tables"][0]["rows"]:
        row["label_exact"] = None
    hierarchy_candidate, _cluster = _candidate([hierarchy])
    assert hierarchy_candidate["status"] == READY

    suffixed = _record(version=VERSION_A, page=1, year=2025)
    for row in suffixed["page_json"]["sections"][0]["tables"][0]["rows"]:
        row["label_exact"] += " Năm 2025"
        row["hierarchy_path_exact"] = [row["label_exact"]]
    suffixed_candidate, _cluster = _candidate([suffixed])
    assert suffixed_candidate["status"] == READY


def test_required_metric_combination_cannot_silently_drop_expense() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    table = record["page_json"]["sections"][0]["tables"][0]
    table["rows"] = [table["rows"][0]]
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == UNRESOLVED
    assert "REQUIRED_SEGMENT_METRIC_COMBINATION_NOT_VISIBLE" in candidate["reasons"]


def test_source_only_metric_is_total_checked_but_not_mapped() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    table = record["page_json"]["sections"][0]["tables"][0]
    table["rows"].append(
        {
            "hierarchy_path_exact": ["Khấu hao"],
            "label_exact": "Khấu hao",
            "row_kind": "ITEM",
            "values_exact": ["1", "2", "3", "6"],
        }
    )
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assert len(candidate["closure_receipt"]["equations"]) == 3
    assert all("SOURCE_ONLY_METRIC" not in mapping["role"] for mapping in candidate["mappings"])

    table["rows"][-1]["values_exact"][-1] = "999"
    mismatch, _cluster = _candidate([record])
    assert mismatch["status"] == READY
    assert "VISIBLE_SEGMENT_TOTAL_MISMATCH" not in mismatch["reasons"]
    assert any(
        equation["metric_role"].startswith("SOURCE_ONLY_METRIC:")
        and equation["status"] == "MISMATCH"
        for equation in mismatch["closure_receipt"]["equations"]
    )


def test_transposed_source_only_metric_column_is_also_total_checked() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    table = _transposed_table(year=2025)
    table["columns"].append(
        {
            "header_path_exact": ["Năm 2025", "Khấu hao", "Triệu VND"],
            "value_kind": "MONEY",
        }
    )
    for row, value in zip(table["rows"], ("1", "2", "3", "6"), strict=True):
        row["values_exact"].append(value)
    record["page_json"]["sections"][0]["tables"][0] = table
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assert len(candidate["closure_receipt"]["equations"]) == 3

    table["rows"][-1]["values_exact"][-1] = "999"
    mismatch, _cluster = _candidate([record])
    assert mismatch["status"] == READY
    assert "VISIBLE_SEGMENT_TOTAL_MISMATCH" not in mismatch["reasons"]
    assert any(
        equation["metric_role"].startswith("SOURCE_ONLY_METRIC:")
        and equation["status"] == "MISMATCH"
        for equation in mismatch["closure_receipt"]["equations"]
    )


@pytest.mark.parametrize(
    ("surface", "expected_state"),
    [
        ('-"', "INVALID_MONEY_SOURCE"),
        ("10)", "AMBIGUOUS_UNBALANCED_CLOSING_PARENTHESIS"),
    ],
)
def test_source_only_metric_parse_defect_is_receipted_without_blocking_targets(
    surface: str, expected_state: str
) -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    table = record["page_json"]["sections"][0]["tables"][0]
    table["rows"].append(
        {
            "hierarchy_path_exact": ["Khấu hao"],
            "label_exact": "Khấu hao",
            "row_kind": "ITEM",
            "values_exact": [surface, "2", "3", None],
        }
    )
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 6
    source_only_cells = [
        cell
        for receipt in candidate["closure_receipt"]["table_receipts"]
        for cell in receipt["cell_axis"]
        if cell["metric_role"].startswith("SOURCE_ONLY_METRIC:")
    ]
    assert any(cell["state"] == expected_state for cell in source_only_cells)
    assert all(
        cell["state"] == "SOURCE_BLANK" for cell in candidate["closure_receipt"]["blank_cell_axis"]
    )


def test_reset_inside_owner_interval_fails_closed() -> None:
    first = _record(version=VERSION_A, page=1, year=2025)
    second = _record(version=VERSION_B, page=3, year=2024)
    reset = copy.deepcopy(first)
    reset["page_json_version_id"] = "gfpstorev1:json:" + "5" * 64
    reset["physical_page"] = 2
    reset["selected_page_ordinal"] = 2
    reset["page_json"]["sections"] = [
        {
            "content_kind": "NARRATIVE",
            "narratives_exact": [],
            "statement_type": "NOT_APPLICABLE",
            "tables": [],
            "title_exact": "GIAO DỊCH VỚI CÁC BÊN LIÊN QUAN",
        }
    ]
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[first, reset, second], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert "RESET_OR_HARD_NEGATIVE_INSIDE_OWNER_INTERVAL" in cluster["reasons"]


def test_reset_in_narrative_representation_also_fails_closed() -> None:
    first = _record(version=VERSION_A, page=1, year=2025)
    second = _record(version=VERSION_B, page=3, year=2024)
    reset = copy.deepcopy(first)
    reset["page_json_version_id"] = "gfpstorev1:json:" + "6" * 64
    reset["physical_page"] = 2
    reset["selected_page_ordinal"] = 2
    reset["page_json"]["sections"] = [
        {
            "content_kind": "NARRATIVE",
            "narratives_exact": ["GIAO DỊCH VỚI CÁC BÊN LIÊN QUAN"],
            "statement_type": "NOT_APPLICABLE",
            "tables": [],
            "title_exact": None,
        }
    ]
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[first, reset, second], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert "RESET_OR_HARD_NEGATIVE_INSIDE_OWNER_INTERVAL" in cluster["reasons"]


def test_later_same_page_fence_does_not_retroactively_veto_table() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    record["page_json"]["sections"].append(
        {
            "content_kind": "NARRATIVE",
            "narratives_exact": [],
            "statement_type": "NOT_APPLICABLE",
            "tables": [],
            "title_exact": "GIAO DỊCH VỚI CÁC BÊN LIÊN QUAN",
        }
    )
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == READY


def test_non_consolidated_scope_is_not_observed() -> None:
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(version=VERSION_A, page=1, year=2025, scope="RIÊNG LẺ")],
        compiled_specs=_compiled(),
    )
    assert cluster["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
    assert cluster["component_regions"] == []


def test_incomplete_relevant_page_or_gap_requires_retry() -> None:
    partial = _record(version=VERSION_A, page=1, year=2025)
    partial["page_json"]["status"] = "UNRESOLVED_PAGE"
    partial["page_json"]["completion"] = {
        "all_relevant_content_transcribed": False,
        "uncertainty_exact": ["table may be partial"],
    }
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[partial], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert "SELECTED_SEGMENT_PAGE_NOT_CANONICALLY_COMPLETE" in cluster["reasons"]

    first = _record(version=VERSION_A, page=1, year=2025)
    gap = copy.deepcopy(first)
    gap["page_json_version_id"] = "gfpstorev1:json:" + "7" * 64
    gap["physical_page"] = 2
    gap["selected_page_ordinal"] = 2
    gap["page_json"] = {
        "completion": {
            "all_relevant_content_transcribed": False,
            "uncertainty_exact": ["continuation cut"],
        },
        "sections": [],
        "status": "UNRESOLVED_PAGE",
    }
    last = _record(version=VERSION_B, page=3, year=2024)
    gap_cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[first, gap, last], compiled_specs=_compiled()
    )
    assert gap_cluster["status"] == UNRESOLVED
    assert gap_cluster["component_regions"] == []
    assert "SELECTED_SEGMENT_PAGE_INTERVAL_NOT_CANONICALLY_COMPLETE" in gap_cluster["reasons"]


def test_incomplete_scope_carrier_cannot_authorize_a_complete_later_table() -> None:
    scope = _record(version=VERSION_A, page=1, year=2025)
    scope["page_json"]["status"] = "UNRESOLVED_PAGE"
    scope["page_json"]["completion"] = {
        "all_relevant_content_transcribed": False,
        "uncertainty_exact": ["scope may be wrong"],
    }
    scope["page_json"]["sections"][0]["tables"] = []
    scope["page_json"]["sections"][0]["title_exact"] = (
        "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT NĂM 2025"
    )
    table = _record(version=VERSION_B, page=2, year=2025)
    table["page_json"]["sections"][0]["title_exact"] = "BÁO CÁO BỘ PHẬN"
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[scope, table], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert "SELECTED_SEGMENT_PAGE_NOT_CANONICALLY_COMPLETE" in cluster["reasons"]


def test_later_unbound_scope_or_year_does_not_authorize_or_relabel_table() -> None:
    table_page = _record(version=VERSION_A, page=1, year=2025, scope="RIÊNG LẺ")
    later_scope = copy.deepcopy(table_page)
    later_scope["page_json_version_id"] = VERSION_B
    later_scope["physical_page"] = 2
    later_scope["selected_page_ordinal"] = 2
    later_scope["page_json"]["sections"] = [
        {
            "content_kind": "NARRATIVE",
            "narratives_exact": [],
            "statement_type": "NOT_APPLICABLE",
            "tables": [],
            "title_exact": "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT NĂM 2026",
        }
    ]
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[table_page, later_scope], compiled_specs=_compiled()
    )
    assert cluster["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"

    bound = _record(version=VERSION_A, page=1, year=2025)
    bound["page_json"]["sections"].append(copy.deepcopy(later_scope["page_json"]["sections"][0]))
    candidate, cluster = _candidate([bound])
    assert cluster["owner_receipt"]["reporting_year_axis"] == [2025]
    assert {
        value["axis_role"] for mapping in candidate["mappings"] for value in mapping["values"]
    } == {"CURRENT_PERIOD"}


def test_strong_document_scope_can_precede_fallback_branch_owner() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    record["page_json"]["sections"][0]["title_exact"] = (
        "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT NĂM 2025"
    )
    candidate, cluster = _candidate([record])
    assert candidate["status"] == READY
    assert cluster["owner_receipt"]["document_scope_state_axis"][0]["scope_state"] == (
        "CONSOLIDATED"
    )


def test_later_strong_separate_scope_state_blocks_prior_document_scope() -> None:
    first = _record(version=VERSION_A, page=1, year=2025)
    first["page_json"]["sections"][0]["tables"] = []
    second = _record(version=VERSION_B, page=2, year=2025, scope="RIÊNG LẺ")
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[first, second], compiled_specs=_compiled()
    )
    assert cluster["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
    assert cluster["component_regions"] == []


def test_interim_separate_statement_title_overrides_earlier_consolidated_reference() -> None:
    reference = _record(version=VERSION_A, page=1, year=2025)
    reference["page_json"]["status"] = "PRIMARY_FINANCIAL_STATEMENT"
    reference["page_json"]["sections"][0]["tables"] = []
    reference["page_json"]["sections"][0]["title_exact"] = "2. Số liệu Báo cáo tài chính hợp nhất:"
    separate = _record(version=VERSION_B, page=2, year=2025)
    separate["page_json"]["status"] = "PRIMARY_FINANCIAL_STATEMENT"
    separate["page_json"]["sections"][0]["tables"] = []
    separate["page_json"]["sections"][0]["title_exact"] = (
        "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG KINH DOANH RIÊNG GIỮA NIÊN ĐỘ"
    )
    segment = _record(version="gfpstorev1:json:" + "8" * 64, page=3, year=2025)
    segment["page_json"]["sections"][0]["title_exact"] = "BÁO CÁO BỘ PHẬN"

    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[reference, separate, segment], compiled_specs=_compiled()
    )
    assert cluster["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
    assert cluster["component_regions"] == []


@pytest.mark.parametrize(
    ("first_scope", "second_scope", "selected_page"),
    [("HỢP NHẤT", "RIÊNG LẺ", 1), ("RIÊNG LẺ", "HỢP NHẤT", 2)],
)
def test_scope_state_is_resolved_per_table_interval(
    first_scope: str, second_scope: str, selected_page: int
) -> None:
    first = _record(version=VERSION_A, page=1, year=2025, scope=first_scope)
    second = _record(version=VERSION_B, page=2, year=2025, scope=second_scope)
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[first, second], compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    assert [region["selected_page_ordinal"] for region in cluster["component_regions"]] == [
        selected_page
    ]


def test_ambiguous_scope_table_is_not_silently_dropped() -> None:
    first = _record(version=VERSION_A, page=1, year=2025)
    second = _record(version=VERSION_B, page=2, year=2024)
    second["page_json"]["sections"][0]["title_exact"] = (
        "BÁO CÁO TÀI CHÍNH HỢP NHẤT VÀ BÁO CÁO TÀI CHÍNH RIÊNG LẺ\nBÁO CÁO BỘ PHẬN"
    )
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[first, second], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert "SEGMENT_DOCUMENT_SCOPE_STATE_CONFLICT" in cluster["reasons"]


def test_table_qualified_opposite_scope_narrative_requires_retry() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    record["page_json"]["sections"][0]["narratives_exact"] = [
        "Bảng báo cáo bộ phận dưới đây được lập theo Báo cáo tài chính riêng lẻ của Ngân hàng."
    ]
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[record], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert "SEGMENT_OPPOSITE_SCOPE_NARRATIVE_INSIDE_OWNER_INTERVAL" in cluster["reasons"]


def test_incomplete_table_under_explicit_separate_scope_does_not_veto_consolidated() -> None:
    first = _record(version=VERSION_A, page=1, year=2025)
    second = _record(version=VERSION_B, page=2, year=2024, scope="RIÊNG LẺ")
    second["page_json"]["status"] = "UNRESOLVED_PAGE"
    second["page_json"]["completion"] = {
        "all_relevant_content_transcribed": False,
        "uncertainty_exact": ["partial separate disclosure"],
    }
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[first, second], compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    assert [region["selected_page_ordinal"] for region in cluster["component_regions"]] == [1]


@pytest.mark.parametrize(
    "continuation",
    ["CONTINUES_FROM_PREVIOUS_PAGE", "CONTINUES_ON_NEXT_PAGE", "BOTH"],
)
def test_unpaired_directional_continuation_is_an_advisory_when_local_semantics_close(
    continuation: str,
) -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    record["page_json"]["sections"][0]["tables"][0]["continuation"] = continuation
    candidate, cluster = _candidate([record])
    assert cluster["status"] == READY
    assert candidate["status"] == READY
    assert cluster["owner_receipt"]["continuation_advisory_axis"]
    assert {
        item["resolution"] for item in cluster["owner_receipt"]["continuation_advisory_axis"]
    } == {"UNPAIRED_DIRECTIONAL_ADVISORY_LOCAL_SEMANTIC_GATES_REQUIRED"}


def test_unknown_table_continuation_requires_retry() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    record["page_json"]["sections"][0]["tables"][0]["continuation"] = "UNKNOWN"
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[record], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert any("CONTINUATION" in reason for reason in cluster["reasons"])


def test_continuation_table_inside_explicit_interval_is_censused() -> None:
    first = _record(version=VERSION_A, page=1, year=2025)
    middle = _record(version="gfpstorev1:json:" + "5" * 64, page=2, year=2025)
    middle_table = middle["page_json"]["sections"][0]["tables"][0]
    middle_table["title_exact"] = None
    middle["page_json"]["sections"][0]["title_exact"] = (
        "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT NĂM 2025"
    )
    last = _record(version=VERSION_B, page=3, year=2024)
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[first, middle, last], compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    assert [item["physical_page"] for item in cluster["component_regions"]] == [1, 2, 3]


def test_section_only_owner_carries_into_adjacent_continuation_table() -> None:
    owner = _record(version=VERSION_A, page=1, year=2025)
    owner["page_json"]["sections"][0]["tables"] = []
    continuation = _record(version=VERSION_B, page=2, year=2025)
    section = continuation["page_json"]["sections"][0]
    section["title_exact"] = "Số LIỆU TIẾP THEO"
    table = section["tables"][0]
    table["title_exact"] = "Năm 2025"
    table["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"

    candidate, cluster = _candidate([owner, continuation])
    assert cluster["status"] == READY
    assert candidate["status"] == READY
    assert [region["selected_page_ordinal"] for region in cluster["component_regions"]] == [2]
    assert cluster["owner_receipt"]["owner_continuation_axis"] == [
        {
            "owner_marker": cluster["owner_receipt"]["owner_marker_axis"][0],
            "region": cluster["component_regions"][0],
            "rule": "PHYSICALLY_ADJACENT_FROM_PREVIOUS_TABLE_UNDER_OPEN_SEGMENT_OWNER",
        }
    ]


def test_owner_branch_marker_resolves_shared_axis_only_continuation_chain() -> None:
    owner = _record(version=VERSION_A, page=1, year=2025)
    owner_section = owner["page_json"]["sections"][0]
    owner_section["tables"] = []
    owner_section["title_exact"] = (
        "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT NĂM 2025\n45. BÁO CÁO BỘ PHẬN"
    )
    owner_section["narratives_exact"] = ["(a) Báo cáo bộ phận chính yếu theo lĩnh vực kinh doanh"]

    continuation = _record(version=VERSION_B, page=2, year=2025)
    continuation_section = continuation["page_json"]["sections"][0]
    continuation_section["title_exact"] = "SỐ LIỆU TIẾP THEO"
    table = continuation_section["tables"][0]
    table["title_exact"] = "Năm 2025"
    table["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"
    table["columns"][0]["header_path_exact"][-1] = "Mảng thứ nhất\nTriệu VND"
    table["columns"][1]["header_path_exact"][-1] = "Mảng thứ hai\nTriệu VND"

    candidate, cluster = _candidate([owner, continuation])
    assert cluster["status"] == READY
    assert candidate["status"] == UNRESOLVED
    assert "SEGMENT_BRANCH_AMBIGUOUS" not in candidate["reasons"]
    assert "INSUFFICIENT_DECLARED_SEGMENT_AXIS_COVERAGE" in candidate["reasons"]
    assert candidate["closure_receipt"]["table_receipts"][0]["branch"] == "BUSINESS"
    binding = cluster["owner_receipt"]["owner_branch_binding_axis"][0]
    assert binding["branch_role"] == "BUSINESS"
    assert binding["region"] == cluster["component_regions"][0]
    validate_gemini_json_segment_report_candidate_binding_v1(
        candidate,
        document={"source_logical_name": "fixture.pdf", "source_sha256": SOURCE_SHA},
        cluster=cluster,
        compiled_specs=_compiled(),
    )

    from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

    forged_cluster = copy.deepcopy(cluster)
    forged_candidate = copy.deepcopy(candidate)
    forged_binding = forged_cluster["owner_receipt"]["owner_branch_binding_axis"][0]
    forged_binding["branch_role"] = "GEOGRAPHIC"
    for marker in forged_binding["branch_marker_axis"]:
        marker["branch_role"] = "GEOGRAPHIC"
    forged_query = build_gemini_json_equity_matrix_region_query_receipt_v1(
        forged_cluster["component_regions"],
        owner_receipt=forged_cluster["owner_receipt"],
    )
    forged_candidate["closure_receipt"]["query_receipt"] = forged_query
    forged_candidate["candidate_id"] = "gjeqmfv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in forged_candidate.items() if key != "candidate_id"}
    )
    with pytest.raises(ValueError, match="marker contradicts"):
        validate_gemini_json_segment_report_candidate_binding_v1(
            forged_candidate,
            document={"source_logical_name": "fixture.pdf", "source_sha256": SOURCE_SHA},
            cluster=forged_cluster,
            compiled_specs=_compiled(),
        )


def test_owner_branch_marker_cannot_override_exclusive_opposite_axis_evidence() -> None:
    owner = _record(version=VERSION_A, page=1, year=2025)
    owner_section = owner["page_json"]["sections"][0]
    owner_section["tables"] = []
    owner_section["narratives_exact"] = ["(a) Báo cáo bộ phận chính yếu theo lĩnh vực kinh doanh"]

    continuation = _record(version=VERSION_B, page=2, year=2025)
    section = continuation["page_json"]["sections"][0]
    section["title_exact"] = "SỐ LIỆU TIẾP THEO"
    table = section["tables"][0]
    table["title_exact"] = "Năm 2025"
    table["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"
    table["columns"][1]["header_path_exact"][-1] = "Miền Bắc\nTriệu VND"

    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[owner, continuation], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert "SEGMENT_OWNER_BRANCH_AUTHORITY_CONTRADICTS_VISIBLE_TABLE_AXIS" in cluster["reasons"]


def test_continuation_pair_can_skip_an_interleaved_independent_table() -> None:
    first = _record(version=VERSION_A, page=1, year=2025)
    business = first["page_json"]["sections"][0]["tables"][0]
    business["rows"] = [business["rows"][0]]
    business["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    geographic = _table(year=2025)
    geographic["title_exact"] = "Báo cáo bộ phận theo khu vực địa lý"
    for column, label in zip(
        geographic["columns"],
        ("Miền Bắc", "Miền Trung", "Loại trừ", "Tổng cộng"),
        strict=True,
    ):
        column["header_path_exact"][-1] = f"{label}\nTriệu VND"
    first["page_json"]["sections"][0]["tables"].append(geographic)

    second = _record(version=VERSION_B, page=2, year=2025)
    second_business = second["page_json"]["sections"][0]["tables"][0]
    second_business["rows"] = [second_business["rows"][1]]
    second_business["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"

    candidate, cluster = _candidate([first, second])
    assert cluster["status"] == READY
    assert candidate["status"] == READY
    assert len(cluster["component_regions"]) == 3


def test_continuation_requires_physical_as_well_as_selected_page_adjacency() -> None:
    first = _record(version=VERSION_A, page=1, year=2025)
    first["page_json"]["sections"][0]["tables"][0]["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    second = _record(version=VERSION_B, page=3, year=2025)
    second["selected_page_ordinal"] = 2
    second["page_json"]["sections"][0]["tables"][0]["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[first, second], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert {
        "SEGMENT_TABLE_CONTINUATION_PREDECESSOR_MISSING",
        "SEGMENT_TABLE_CONTINUATION_SUCCESSOR_MISSING",
    } <= set(cluster["reasons"])


def test_coherent_candidate_rehash_cannot_change_mapping_axis() -> None:
    candidate, cluster = _candidate([_record(version=VERSION_A, page=1, year=2025)])
    candidate["mappings"][0]["values"][0]["coefficient"] += 1
    from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

    candidate["candidate_id"] = "gjeqmfv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in candidate.items() if key != "candidate_id"}
    )
    try:
        validate_gemini_json_segment_report_candidate_binding_v1(
            candidate,
            document={"source_logical_name": "fixture.pdf", "source_sha256": SOURCE_SHA},
            cluster=cluster,
            compiled_specs=_compiled(),
        )
    except ValueError as exc:
        assert "candidate binding drifted" in str(exc)
    else:
        raise AssertionError("coherent mapping drift was accepted")


def test_coherent_mapping_and_duplicate_closure_rehash_is_rejected() -> None:
    candidate, cluster = _candidate([_record(version=VERSION_A, page=1, year=2025)])
    mapping = candidate["mappings"][0]
    mapping["values"][0]["coefficient"] += 777
    from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

    mapping["item_mapping_id"] = "gjsrmv1:item:" + canonical_json_sha256_v1(
        {key: value for key, value in mapping.items() if key != "item_mapping_id"}
    )
    candidate["closure_receipt"]["mapping_axis"] = copy.deepcopy(candidate["mappings"])
    candidate["candidate_id"] = "gjeqmfv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in candidate.items() if key != "candidate_id"}
    )
    with pytest.raises(ValueError, match="closure axes drifted"):
        validate_gemini_json_segment_report_candidate_binding_v1(
            candidate,
            document={"source_logical_name": "fixture.pdf", "source_sha256": SOURCE_SHA},
            cluster=cluster,
            compiled_specs=_compiled(),
        )


def test_semantically_identical_duplicate_table_is_collapsed_but_conflict_is_not() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    tables = record["page_json"]["sections"][0]["tables"]
    tables.append(copy.deepcopy(tables[0]))
    candidate, cluster = _candidate([record])
    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 6
    assert len(candidate["closure_receipt"]["equations"]) == 2
    assert candidate["closure_receipt"]["duplicate_equivalent_cell_axis"]
    validate_gemini_json_segment_report_candidate_binding_v1(
        candidate,
        document={"source_logical_name": "fixture.pdf", "source_sha256": SOURCE_SHA},
        cluster=cluster,
        compiled_specs=_compiled(),
    )

    tables[1]["rows"][0]["values_exact"][0] = "101"
    tables[1]["rows"][0]["values_exact"][-1] = "111"
    conflict, _cluster = _candidate([record])
    assert conflict["status"] == UNRESOLVED
    assert "CONFLICTING_DUPLICATE_SEGMENT_AXIS_METRIC_PERIOD_CELL" in conflict["reasons"]


def test_undated_duplicate_is_not_invented_as_comparative_period() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    tables = record["page_json"]["sections"][0]["tables"]
    undated = copy.deepcopy(tables[0])
    undated["title_exact"] = "Báo cáo bộ phận theo lĩnh vực kinh doanh"
    for column in undated["columns"]:
        column["header_path_exact"] = column["header_path_exact"][1:]
    tables.append(undated)
    candidate, _cluster = _candidate([record])
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "SEGMENT_PERIOD_NOT_RESOLVED" in candidate["reasons"]


def test_structural_cross_branch_period_carrier_is_exactly_bound_and_tamper_checked() -> None:
    target = _record(version=VERSION_A, page=1, year=2025)
    target_section = target["page_json"]["sections"][0]
    geographic_tables = []
    for _year in (2025, 2024):
        table = _table(year=_year)
        table["title_exact"] = "Báo cáo bộ phận theo khu vực địa lý"
        for column, label in zip(
            table["columns"],
            ("Miền Bắc", "Miền Trung", "Loại trừ", "Tổng cộng"),
            strict=True,
        ):
            column["header_path_exact"] = [f"{label}\nTriệu VND"]
        geographic_tables.append(table)
    target_section["tables"] = geographic_tables

    carrier = _record(version=VERSION_B, page=2, year=2025)
    carrier_section = carrier["page_json"]["sections"][0]
    carrier_section["tables"] = [_table(year=2025), _table(year=2024)]

    candidate, cluster = _candidate([target, carrier])
    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 14
    evidence_receipts = [
        receipt
        for receipt in candidate["closure_receipt"]["table_receipts"]
        if receipt.get("period_assignment_evidence") is not None
    ]
    assert len(evidence_receipts) == 2
    validate_gemini_json_segment_report_candidate_binding_v1(
        candidate,
        document={"source_logical_name": "fixture.pdf", "source_sha256": SOURCE_SHA},
        cluster=cluster,
        compiled_specs=_compiled(),
    )

    from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

    for receipt in evidence_receipts:
        evidence = receipt["period_assignment_evidence"]
        evidence["carrier"]["metric_signature"] = ["ASSETS"]
        evidence["target_regions"].reverse()
    candidate["candidate_id"] = "gjeqmfv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in candidate.items() if key != "candidate_id"}
    )
    with pytest.raises(ValueError, match="structural period"):
        validate_gemini_json_segment_report_candidate_binding_v1(
            candidate,
            document={"source_logical_name": "fixture.pdf", "source_sha256": SOURCE_SHA},
            cluster=cluster,
            compiled_specs=_compiled(),
        )


def test_structural_cross_branch_period_carrier_can_use_adjacent_same_page_sections() -> None:
    record = _record(version=VERSION_A, page=1, year=2025)
    geographic_section = record["page_json"]["sections"][0]
    geographic_section["tables"] = []
    for _year in (2025, 2024):
        table = _table(year=_year)
        table["title_exact"] = "Báo cáo bộ phận theo khu vực địa lý"
        for column, label in zip(
            table["columns"],
            ("Miền Bắc", "Miền Trung", "Loại trừ", "Tổng cộng"),
            strict=True,
        ):
            column["header_path_exact"] = [f"{label}\nTriệu VND"]
        geographic_section["tables"].append(table)
    business_section = copy.deepcopy(geographic_section)
    business_section["title_exact"] = "BÁO CÁO BỘ PHẬN THEO LĨNH VỰC KINH DOANH"
    business_section["tables"] = [_table(year=2025), _table(year=2024)]
    record["page_json"]["sections"].append(business_section)

    candidate, cluster = _candidate([record])
    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 14
    evidence = [
        receipt["period_assignment_evidence"]
        for receipt in candidate["closure_receipt"]["table_receipts"]
        if receipt.get("period_assignment_evidence") is not None
    ]
    assert len(evidence) == 2
    assert {item["carrier"]["pair_binding_mode"] for item in evidence} == {
        "SAME_PAGE_ADJACENT_SECTIONS"
    }
    validate_gemini_json_segment_report_candidate_binding_v1(
        candidate,
        document={"source_logical_name": "fixture.pdf", "source_sha256": SOURCE_SHA},
        cluster=cluster,
        compiled_specs=_compiled(),
    )


def test_matching_declared_totals_do_not_route_periods_across_shape_drift() -> None:
    target = _record(version=VERSION_A, page=1, year=2025)
    target_tables = []
    for values in (
        (["100", "20", "(10)", "0", "110"], ["50", "5", "(5)", "0", "50"]),
        (["200", "30", "(10)", "0", "220"], ["120", "10", "(10)", "0", "120"]),
    ):
        table = _table(year=2025)
        for column in table["columns"]:
            column["header_path_exact"] = column["header_path_exact"][1:]
        table["columns"].insert(
            -1,
            {"header_path_exact": ["Ngân hàng số\nTriệu VND"], "value_kind": "MONEY"},
        )
        table["rows"] = [
            {
                "hierarchy_path_exact": ["Tài sản"],
                "label_exact": "Tài sản",
                "row_kind": "TOTAL",
                "values_exact": values[0],
            },
            {
                "hierarchy_path_exact": ["Nợ phải trả"],
                "label_exact": "Nợ phải trả",
                "row_kind": "TOTAL",
                "values_exact": values[1],
            },
        ]
        target_tables.append(table)
    target["page_json"]["sections"][0]["tables"] = target_tables

    carrier = _record(version=VERSION_B, page=2, year=2025)
    carrier_tables = []
    for year, values in (
        (2025, (["80", "40", "(10)", "110"], ["40", "15", "(5)", "50"])),
        (2024, (["160", "70", "(10)", "220"], ["100", "30", "(10)", "120"])),
    ):
        table = _table(year=year)
        table["title_exact"] = "Báo cáo bộ phận theo khu vực địa lý"
        for column, label in zip(
            table["columns"],
            ("Miền Bắc", "Miền Trung", "Loại trừ", "Tổng cộng"),
            strict=True,
        ):
            column["header_path_exact"] = [f"31/12/{year}", f"{label}\nTriệu VND"]
        table["rows"] = [
            {
                "hierarchy_path_exact": ["Tài sản"],
                "label_exact": "Tài sản",
                "row_kind": "TOTAL",
                "values_exact": values[0],
            },
            {
                "hierarchy_path_exact": ["Nợ phải trả"],
                "label_exact": "Nợ phải trả",
                "row_kind": "TOTAL",
                "values_exact": values[1],
            },
        ]
        carrier_tables.append(table)
    carrier["page_json"]["sections"][0]["tables"] = carrier_tables

    candidate, _cluster = _candidate([target, carrier])
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "SEGMENT_PERIOD_NOT_RESOLVED" in candidate["reasons"]
    target_receipts = candidate["closure_receipt"]["table_receipts"][:2]
    assert all(receipt.get("period_assignment_evidence") is None for receipt in target_receipts)


def test_repeated_adjacent_metric_blocks_share_each_visible_block_role() -> None:
    records = [
        _primary_flow_period_record(
            version="gfpstorev1:json:" + "8" * 64,
            page=1,
            current_end="2025-12-31",
            comparative_end="2024-12-31",
        )
    ]
    for page, year, stock in (
        (2, 2025, False),
        (3, 2025, True),
        (4, 2024, False),
        (5, 2024, True),
    ):
        record = _record(
            version="gfpstorev1:json:" + str(page) * 64,
            page=page,
            year=year,
        )
        table = record["page_json"]["sections"][0]["tables"][0]
        if stock:
            for row, label in zip(table["rows"], ("Tài sản", "Nợ phải trả"), strict=True):
                row["label_exact"] = label
                row["hierarchy_path_exact"] = [label]
        else:
            for column in table["columns"]:
                column["header_path_exact"] = column["header_path_exact"][1:]
            table["title_exact"] = "Báo cáo bộ phận theo lĩnh vực kinh doanh"
        records.append(record)

    candidate, cluster = _candidate(records)
    assert candidate["status"] == READY
    flow_receipts = candidate["closure_receipt"]["table_receipts"][::2]
    assert {receipt["period_role"] for receipt in flow_receipts} == {
        "CURRENT_PERIOD",
        "COMPARATIVE_PERIOD",
    }
    assert {receipt["period_assignment_evidence"]["rule"] for receipt in flow_receipts} == {
        "UNIQUE_ROLE_WITHIN_REPEATED_ADJACENT_METRIC_BLOCK"
    }
    validate_gemini_json_segment_report_candidate_binding_v1(
        candidate,
        document={"source_logical_name": "fixture.pdf", "source_sha256": SOURCE_SHA},
        cluster=cluster,
        compiled_specs=_compiled(),
    )

    from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

    for receipt in flow_receipts:
        receipt["period_assignment_evidence"]["block_axis"][0]["period_role"] = "COMPARATIVE_PERIOD"
    candidate["candidate_id"] = "gjeqmfv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in candidate.items() if key != "candidate_id"}
    )
    with pytest.raises(ValueError, match="repeated metric block"):
        validate_gemini_json_segment_report_candidate_binding_v1(
            candidate,
            document={"source_logical_name": "fixture.pdf", "source_sha256": SOURCE_SHA},
            cluster=cluster,
            compiled_specs=_compiled(),
        )


def test_repeated_block_can_have_one_fully_explicit_carrier_block() -> None:
    records = [
        _primary_stock_period_record(
            version="gfpstorev1:json:" + "7" * 64,
            page=1,
            current_end="2025-12-31",
            comparative_end="2024-12-31",
        ),
        _primary_flow_period_record(
            version="gfpstorev1:json:" + "8" * 64,
            page=2,
            current_end="2025-12-31",
            comparative_end="2024-12-31",
        ),
    ]
    for page, year, stock, undated in (
        (3, 2025, False, False),
        (4, 2025, True, False),
        (5, 2024, False, False),
        (6, 2024, True, True),
    ):
        record = _record(
            version="gfpstorev1:json:" + str(page) * 64,
            page=page,
            year=year,
        )
        table = record["page_json"]["sections"][0]["tables"][0]
        if stock:
            for row, label in zip(table["rows"], ("Tài sản", "Nợ phải trả"), strict=True):
                row["label_exact"] = label
                row["hierarchy_path_exact"] = [label]
        if undated:
            for column in table["columns"]:
                column["header_path_exact"] = column["header_path_exact"][1:]
            table["title_exact"] = "Báo cáo bộ phận theo lĩnh vực kinh doanh"
        records.append(record)

    candidate, cluster = _candidate(records)
    target = candidate["closure_receipt"]["table_receipts"][-1]
    assert target["period_role"] == "COMPARATIVE_PERIOD"
    assert target["period_assignment_evidence"]["target_regions"] == [target["region"]]
    validate_gemini_json_segment_report_candidate_binding_v1(
        candidate,
        document={"source_logical_name": "fixture.pdf", "source_sha256": SOURCE_SHA},
        cluster=cluster,
        compiled_specs=_compiled(),
    )


def test_partial_stock_pair_binds_to_unique_cross_branch_declared_totals() -> None:
    primary = _primary_stock_period_record(
        version="gfpstorev1:json:" + "a" * 64,
        page=1,
        current_end="2025-12-31",
        comparative_end="2024-12-31",
    )
    target_records = []
    target_values = (
        (
            ["80", "40", "(10)", "110"],
            ["30", "10", "0", "40"],
            ["30", "25", "(5)", "50"],
        ),
        (
            ["160", "70", "(10)", "220"],
            ["60", "20", "0", "80"],
            ["90", "40", "(10)", "120"],
        ),
    )
    for page, year, values in ((2, 2025, target_values[0]), (3, 2024, target_values[1])):
        record = _record(
            version="gfpstorev1:json:" + str(page) * 64,
            page=page,
            year=year,
        )
        table = record["page_json"]["sections"][0]["tables"][0]
        table["rows"] = [
            {
                "hierarchy_path_exact": [label],
                "label_exact": label,
                "row_kind": "TOTAL",
                "values_exact": row_values,
            }
            for label, row_values in zip(
                ("Tài sản", "Tài sản cố định", "Nợ phải trả"), values, strict=True
            )
        ]
        if page == 2:
            table["title_exact"] = "Báo cáo bộ phận theo lĩnh vực kinh doanh"
            for column in table["columns"]:
                column["header_path_exact"] = column["header_path_exact"][1:]
        target_records.append(record)

    carrier = _record(version="gfpstorev1:json:" + "b" * 64, page=4, year=2025)
    carrier_tables = []
    for year, values in (
        (2025, (["60", "60", "(10)", "110"], ["30", "25", "(5)", "50"])),
        (2024, (["140", "90", "(10)", "220"], ["90", "40", "(10)", "120"])),
    ):
        table = _table(year=year)
        table["title_exact"] = "Báo cáo bộ phận theo khu vực địa lý"
        for column, label in zip(
            table["columns"],
            ("Miền Bắc", "Miền Trung", "Loại trừ", "Tổng cộng"),
            strict=True,
        ):
            column["header_path_exact"] = [f"31/12/{year}", f"{label}\nTriệu VND"]
        table["rows"] = [
            {
                "hierarchy_path_exact": [label],
                "label_exact": label,
                "row_kind": "TOTAL",
                "values_exact": row_values,
            }
            for label, row_values in zip(("Tài sản", "Nợ phải trả"), values, strict=True)
        ]
        carrier_tables.append(table)
    carrier["page_json"]["sections"][0]["tables"] = carrier_tables

    candidate, cluster = _candidate([primary, *target_records, carrier])
    assert candidate["status"] == READY
    target_receipt = candidate["closure_receipt"]["table_receipts"][0]
    evidence = target_receipt["period_assignment_evidence"]
    assert target_receipt["period_role"] == "CURRENT_PERIOD"
    assert evidence["rule"] == "UNIQUE_CROSS_BRANCH_TWO_PERIOD_DECLARED_TOTAL_CORRESPONDENCE"
    assert evidence["common_total_metric_roles"] == ["ASSETS", "LIABILITIES"]
    assert {item["period_role"] for item in evidence["total_correspondence_axis"]} == {
        "CURRENT_PERIOD",
        "COMPARATIVE_PERIOD",
    }
    validate_gemini_json_segment_report_candidate_binding_v1(
        candidate,
        document={"source_logical_name": "fixture.pdf", "source_sha256": SOURCE_SHA},
        cluster=cluster,
        compiled_specs=_compiled(),
    )

    from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

    evidence["total_correspondence_axis"][0]["metric_axis"][0]["coefficient"] += 1
    candidate["candidate_id"] = "gjeqmfv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in candidate.items() if key != "candidate_id"}
    )
    with pytest.raises(ValueError, match="total correspondence"):
        validate_gemini_json_segment_report_candidate_binding_v1(
            candidate,
            document={"source_logical_name": "fixture.pdf", "source_sha256": SOURCE_SHA},
            cluster=cluster,
            compiled_specs=_compiled(),
        )


def test_two_adjacent_page_two_table_blocks_bind_complement_with_typed_endpoints() -> None:
    records = [
        _primary_stock_period_record(
            version="gfpstorev1:json:" + "a" * 64,
            page=1,
            current_end="2025-06-30",
            comparative_end="2024-12-31",
        ),
        _primary_flow_period_record(
            version="gfpstorev1:json:" + "b" * 64,
            page=2,
            current_end="2025-06-30",
            comparative_end="2024-06-30",
        ),
    ]
    for page, current in ((3, True), (4, False)):
        record = _record(
            version="gfpstorev1:json:" + str(page) * 64,
            page=page,
            year=2025 if current else 2024,
        )
        flow = record["page_json"]["sections"][0]["tables"][0]
        flow["title_exact"] = "Báo cáo bộ phận theo khu vực địa lý"
        flow["rows"].append(
            {
                "hierarchy_path_exact": ["Lợi nhuận trước thuế"],
                "label_exact": "Lợi nhuận trước thuế",
                "row_kind": "TOTAL",
                "values_exact": ["50", "10", "(5)", "55"],
            }
        )
        stock = copy.deepcopy(flow)
        stock["rows"] = [
            {
                "hierarchy_path_exact": [label],
                "label_exact": label,
                "row_kind": "TOTAL",
                "values_exact": values,
            }
            for label, values in (
                ("Tài sản", ["100", "40", "(10)", "130"]),
                ("Tài sản cố định", ["30", "10", "0", "40"]),
                ("Nợ phải trả", ["60", "20", "(5)", "75"]),
            )
        ]
        for table in (flow, stock):
            for column, label in zip(
                table["columns"],
                ("Miền Bắc", "Miền Trung", "Loại trừ", "Tổng cộng"),
                strict=True,
            ):
                date_prefix = ["30/06/2025"] if current and table is stock else []
                column["header_path_exact"] = [*date_prefix, f"{label}\nTriệu VND"]
        if current:
            stock["unit_exact"] = None
            for column in stock["columns"]:
                column["header_path_exact"][-1] = column["header_path_exact"][-1].replace(
                    "\nTriệu VND", ""
                )
        record["page_json"]["sections"][0]["tables"] = [flow, stock]
        records.append(record)

    candidate, cluster = _candidate(records)
    assert candidate["status"] == READY
    target_receipts = candidate["closure_receipt"]["table_receipts"][-2:]
    assert {receipt["period_role"] for receipt in target_receipts} == {"COMPARATIVE_PERIOD"}
    assert {
        receipt["period_assignment_evidence"]["binding_mode"] for receipt in target_receipts
    } == {"TWO_ADJACENT_PAGE_SAME_SECTION_TABLE_PAIRS"}
    endpoints = {
        mapping["role"].rsplit(":", 1)[-1]: next(
            value["period_end"]
            for value in mapping["values"]
            if value["axis_role"] == "COMPARATIVE_PERIOD"
        )
        for mapping in candidate["mappings"]
    }
    assert endpoints["REVENUE"] == "2024-06-30"
    assert endpoints["EXPENSE"] == "2024-06-30"
    assert endpoints["PROFIT_BEFORE_TAX"] == "2024-06-30"
    assert endpoints["ASSETS"] == "2024-12-31"
    assert endpoints["FIXED_ASSETS"] == "2024-12-31"
    assert endpoints["LIABILITIES"] == "2024-12-31"
    validate_gemini_json_segment_report_candidate_binding_v1(
        candidate,
        document={"source_logical_name": "fixture.pdf", "source_sha256": SOURCE_SHA},
        cluster=cluster,
        compiled_specs=_compiled(),
    )


def test_repeated_metric_block_role_does_not_cross_source_axis_shape_drift() -> None:
    records = []
    for page, year, stock in (
        (1, 2025, False),
        (2, 2025, True),
        (3, 2024, False),
        (4, 2024, True),
    ):
        record = _record(
            version="gfpstorev1:json:" + str(page + 2) * 64,
            page=page,
            year=year,
        )
        table = record["page_json"]["sections"][0]["tables"][0]
        if stock:
            for row, label in zip(table["rows"], ("Tài sản", "Nợ phải trả"), strict=True):
                row["label_exact"] = label
                row["hierarchy_path_exact"] = [label]
        else:
            for column in table["columns"]:
                column["header_path_exact"] = column["header_path_exact"][1:]
            table["title_exact"] = "Báo cáo bộ phận theo lĩnh vực kinh doanh"
        records.append(record)
    records[2]["page_json"]["sections"][0]["tables"][0]["columns"][1]["header_path_exact"][0] = (
        "Khoản ngoài cấu hình\nTriệu VND"
    )

    candidate, _cluster = _candidate(records)
    assert candidate["status"] == UNRESOLVED
    assert "SEGMENT_PERIOD_NOT_RESOLVED" in candidate["reasons"]
    assert all(
        receipt.get("period_assignment_evidence", {}).get("rule")
        != "UNIQUE_ROLE_WITHIN_REPEATED_ADJACENT_METRIC_BLOCK"
        for receipt in candidate["closure_receipt"]["table_receipts"]
    )


def test_adjacent_split_and_combined_metric_blocks_bind_complement_with_typed_endpoints() -> None:
    stock_primary = _record(version="gfpstorev1:json:" + "6" * 64, page=1, year=2026)
    stock_primary["page_json"]["status"] = "PRIMARY_FINANCIAL_STATEMENT"
    stock_primary_section = stock_primary["page_json"]["sections"][0]
    stock_primary_section["statement_type"] = "BALANCE_SHEET"
    stock_primary_section["tables"] = []
    stock_primary_section["title_exact"] = (
        "BÁO CÁO TÌNH HÌNH TÀI CHÍNH HỢP NHẤT TẠI 30/06/2026 VÀ 31/12/2025"
    )
    flow_primary = _record(version="gfpstorev1:json:" + "7" * 64, page=2, year=2026)
    flow_primary["page_json"]["status"] = "PRIMARY_FINANCIAL_STATEMENT"
    flow_primary_section = flow_primary["page_json"]["sections"][0]
    flow_primary_section["statement_type"] = "INCOME_STATEMENT"
    flow_primary_section["tables"] = []
    flow_primary_section["title_exact"] = (
        "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG KINH DOANH HỢP NHẤT CHO KỲ KẾT THÚC 30/06/2026 VÀ 30/06/2025"
    )

    split = _record(version=VERSION_A, page=3, year=2026)
    split_table = split["page_json"]["sections"][0]["tables"][0]
    stock_table = copy.deepcopy(split_table)
    for row, label in zip(stock_table["rows"], ("Tài sản", "Nợ phải trả"), strict=True):
        row["label_exact"] = label
        row["hierarchy_path_exact"] = [label]
    split["page_json"]["sections"][0]["tables"].append(stock_table)

    combined = _record(version=VERSION_B, page=4, year=2025)
    combined_table = combined["page_json"]["sections"][0]["tables"][0]
    stock_rows = copy.deepcopy(combined_table["rows"])
    for row, label in zip(stock_rows, ("Tài sản", "Nợ phải trả"), strict=True):
        row["label_exact"] = label
        row["hierarchy_path_exact"] = [label]
    combined_table["rows"].extend(stock_rows)
    for column in combined_table["columns"]:
        column["header_path_exact"] = column["header_path_exact"][1:]

    candidate, cluster = _candidate([stock_primary, flow_primary, split, combined])
    assert candidate["status"] == READY
    target_receipt = candidate["closure_receipt"]["table_receipts"][-1]
    assert target_receipt["period_role"] == "COMPARATIVE_PERIOD"
    assert target_receipt["period_assignment_evidence"]["rule"] == (
        "UNIQUE_COMPLEMENT_ROLE_FROM_ADJACENT_SPLIT_COMBINED_METRIC_BLOCK"
    )
    endpoints = {
        (mapping["role"].rsplit(":", 1)[-1], value["axis_role"]): value["period_end"]
        for mapping in candidate["mappings"]
        for value in mapping["values"]
        if value["axis_role"] == "COMPARATIVE_PERIOD"
    }
    assert endpoints[("REVENUE", "COMPARATIVE_PERIOD")] == "2025-06-30"
    assert endpoints[("EXPENSE", "COMPARATIVE_PERIOD")] == "2025-06-30"
    assert endpoints[("ASSETS", "COMPARATIVE_PERIOD")] == "2025-12-31"
    assert endpoints[("LIABILITIES", "COMPARATIVE_PERIOD")] == "2025-12-31"
    validate_gemini_json_segment_report_candidate_binding_v1(
        candidate,
        document={"source_logical_name": "fixture.pdf", "source_sha256": SOURCE_SHA},
        cluster=cluster,
        compiled_specs=_compiled(),
    )


def test_candidate_unit_must_remain_bound_to_explicit_table_evidence() -> None:
    candidate, cluster = _candidate([_record(version=VERSION_A, page=1, year=2025)])
    from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

    candidate["closure_receipt"]["unit_receipt"]["canonical_unit"] = "FORGED_UNIT"
    for mapping in candidate["mappings"]:
        mapping["unit"] = "FORGED_UNIT"
        mapping["item_mapping_id"] = "gjsrmv1:item:" + canonical_json_sha256_v1(
            {key: value for key, value in mapping.items() if key != "item_mapping_id"}
        )
    candidate["closure_receipt"]["mapping_axis"] = copy.deepcopy(candidate["mappings"])
    candidate["candidate_id"] = "gjeqmfv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in candidate.items() if key != "candidate_id"}
    )
    with pytest.raises(ValueError, match="canonical unit drifted"):
        validate_gemini_json_segment_report_candidate_binding_v1(
            candidate,
            document={"source_logical_name": "fixture.pdf", "source_sha256": SOURCE_SHA},
            cluster=cluster,
            compiled_specs=_compiled(),
        )


def test_axis_alias_cannot_change_role_across_branch_projections() -> None:
    topology, evaluation, schema = _spec_values()
    evaluation["matrix_policy"]["geographic_axis_aliases"]["NORTH"].append("Ngân hàng")
    with pytest.raises(ValueError, match="changes role across branch"):
        compile_gemini_json_equity_matrix_family_specs_v1(topology, evaluation, schema)


def test_source_only_alias_cannot_overlap_both_branch_projections() -> None:
    topology, evaluation, schema = _spec_values()
    evaluation["matrix_policy"]["source_only_axis_aliases"].append("Tổng cộng")
    with pytest.raises(ValueError, match="source-only alias axis is ambiguous"):
        compile_gemini_json_equity_matrix_family_specs_v1(topology, evaluation, schema)


@pytest.mark.parametrize(
    ("canonical_unit", "magnitude_power10"),
    [("", 6), ("   ", 6), ("MILLION_VND", -1)],
)
def test_unit_binding_identity_is_nonempty_and_nonnegative(
    canonical_unit: str, magnitude_power10: int
) -> None:
    topology, evaluation, schema = _spec_values()
    binding = evaluation["matrix_policy"]["unit_bindings"][0]
    binding["canonical_unit"] = canonical_unit
    binding["magnitude_power10"] = magnitude_power10
    with pytest.raises(ValueError, match="unit bindings are invalid"):
        compile_gemini_json_equity_matrix_family_specs_v1(topology, evaluation, schema)


def test_same_canonical_unit_cannot_have_two_magnitudes() -> None:
    topology, evaluation, schema = _spec_values()
    evaluation["matrix_policy"]["unit_bindings"][1]["canonical_unit"] = "MILLION_VND"
    with pytest.raises(ValueError, match="canonical unit magnitude is ambiguous"):
        compile_gemini_json_equity_matrix_family_specs_v1(topology, evaluation, schema)


def test_same_canonical_unit_cannot_be_both_accepted_and_rejected() -> None:
    topology, evaluation, schema = _spec_values()
    accepted = evaluation["matrix_policy"]["unit_bindings"][0]
    rejected = evaluation["matrix_policy"]["unit_bindings"][1]
    rejected["canonical_unit"] = accepted["canonical_unit"]
    rejected["magnitude_power10"] = accepted["magnitude_power10"]
    with pytest.raises(ValueError, match="canonical unit acceptance is ambiguous"):
        compile_gemini_json_equity_matrix_family_specs_v1(topology, evaluation, schema)


@pytest.mark.parametrize("invalid_alias", ["   ", 42])
def test_scope_aliases_are_typed_and_nonempty(invalid_alias: object) -> None:
    topology, evaluation, schema = _spec_values()
    evaluation["matrix_policy"]["consolidated_scope_aliases"].append(invalid_alias)
    with pytest.raises(ValueError, match="scope aliases are invalid"):
        compile_gemini_json_equity_matrix_family_specs_v1(topology, evaluation, schema)


def test_consolidated_and_separate_scope_aliases_are_disjoint() -> None:
    topology, evaluation, schema = _spec_values()
    evaluation["matrix_policy"]["separate_scope_aliases"].append(
        evaluation["matrix_policy"]["consolidated_scope_aliases"][0]
    )
    with pytest.raises(ValueError, match="scope aliases overlap"):
        compile_gemini_json_equity_matrix_family_specs_v1(topology, evaluation, schema)


@pytest.mark.parametrize("target", ["root", "branch", "axis"])
def test_schema_graph_identifiers_must_be_positive(target: str) -> None:
    topology, evaluation, schema = _spec_values()
    if target == "root":
        schema["family_root_report_norm_id"] = -1
    elif target == "branch":
        schema["branch_bindings"][0]["branch_report_norm_id"] = -2
    else:
        schema["branch_bindings"][0]["axis_bindings"][0]["parent_report_norm_id"] = -3
    with pytest.raises(ValueError, match="schema binding|branch binding|axis binding"):
        compile_gemini_json_equity_matrix_family_specs_v1(topology, evaluation, schema)
