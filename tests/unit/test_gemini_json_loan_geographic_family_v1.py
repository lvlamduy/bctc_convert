from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_dual_axis_accounting_family_v1 import (
    evaluate_gemini_json_dual_axis_family_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    READY,
    UNRESOLVED,
    GeminiJsonFlatAccountingFamilyV1Error,
    compile_gemini_json_flat_family_specs_v1,
)

ROOT = Path(__file__).resolve().parents[2]


def _specs() -> tuple[dict, dict, dict]:
    root = ROOT / "config/families"
    return tuple(
        json.loads((root / f"tm-loan-geographic-classification-{name}-v1.json").read_text())
        for name in ("topology", "evaluation", "schema-binding")
    )


def _compiled() -> dict:
    return compile_gemini_json_flat_family_specs_v1(*_specs())


def _version(character: str) -> str:
    return "gfpstorev1:json:" + character * 64


def _row_page(
    *,
    current: bool = True,
    continuation: str = "NONE",
    include_total: bool = True,
) -> dict:
    period = "Tại ngày 31 tháng 12 năm 2025" if current else "Tại ngày 31 tháng 12 năm 2024"
    values = ("120", "20", "140") if current else ("100", "10", "110")
    rows = [
        {
            "hierarchy_path_exact": ["Trong nước"],
            "label_exact": "Trong nước",
            "row_kind": "ITEM",
            "values_exact": [values[0]],
        },
        {
            "hierarchy_path_exact": ["Nước ngoài"],
            "label_exact": "Nước ngoài",
            "row_kind": "ITEM",
            "values_exact": [values[1]],
        },
    ]
    if include_total:
        rows.append(
            {
                "hierarchy_path_exact": [None],
                "label_exact": "Tổng cộng",
                "row_kind": "TOTAL",
                "values_exact": [values[2]],
            }
        )
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [
                    {
                        "columns": [
                            {
                                "header_path_exact": ["Cho vay khách hàng", "Triệu đồng"],
                                "value_kind": "MONEY",
                            }
                        ],
                        "continuation": continuation,
                        "rows": rows,
                        "title_exact": period,
                        "unit_exact": "Triệu đồng",
                    }
                ],
                "title_exact": "Phân tích dư nợ cho vay theo khu vực địa lý",
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _column_page(
    *,
    current: bool,
    blank_role: str | None = None,
    continuation: str = "NONE",
    include_total: bool = True,
) -> dict:
    period = "Tại ngày 30 tháng 6 năm 2026" if current else "Tại ngày 31 tháng 12 năm 2025"
    domestic = "200" if current else "180"
    foreign: str | None = "-" if current else "0"
    if blank_role == "DOMESTIC_TOTAL":
        domestic = None
    elif blank_role == "FOREIGN_TOTAL":
        foreign = None
    columns = [
        {"header_path_exact": ["Trong nước", "Triệu VND"], "value_kind": "MONEY"},
        {"header_path_exact": ["Nước ngoài", "Triệu VND"], "value_kind": "MONEY"},
    ]
    values: list[str | None] = [domestic, foreign]
    if include_total:
        columns.append({"header_path_exact": ["Tổng cộng", "Triệu VND"], "value_kind": "MONEY"})
        values.append(
            domestic if foreign in {None, "-", "0"} else str(int(domestic) + int(foreign))
        )
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [
                    "Số liệu được trình bày theo khu vực địa lý của khách hàng đối tác."
                ],
                "statement_type": "NOT_APPLICABLE",
                "tables": [
                    {
                        "columns": columns,
                        "continuation": continuation,
                        "rows": [
                            {
                                "hierarchy_path_exact": ["Cho vay khách hàng"],
                                "label_exact": "Cho vay khách hàng",
                                "row_kind": "ITEM",
                                "values_exact": values,
                            }
                        ],
                        "title_exact": period,
                        "unit_exact": "Triệu VND",
                    }
                ],
                "title_exact": "Mức độ tập trung theo khu vực địa lý",
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _region(*, version: str, page: int, orientation: str) -> dict:
    return {
        "orientation": orientation,
        "page_json_version_id": version,
        "physical_page": page,
        "section_id": "s1",
        "source_logical_name": "report.pdf",
        "table_id": "t1",
    }


def _context(*dates: str, unit_records: list[dict] | None = None) -> dict:
    period_evidence = []
    for ordinal, text in enumerate(dates, start=1):
        # Two-page support makes each declared reporting date eligible for the
        # generic document consensus when table-local evidence is absent.
        for page in (ordinal, ordinal + 10):
            period_evidence.append(
                {
                    "physical_page": page,
                    "section_id": "s1",
                    "source_kind": "COLUMN_HEADER",
                    "table_id": "t1",
                    "text_exact": text,
                }
            )
    return {
        "period_evidence": period_evidence,
        "unit_evidence": unit_records
        or [
            {
                "physical_page": 20,
                "section_id": "s1",
                "source_kind": "TABLE_UNIT",
                "table_id": "t1",
                "text_exact": "Triệu đồng",
            },
            {
                "physical_page": 21,
                "section_id": "s1",
                "source_kind": "TABLE_UNIT",
                "table_id": "t1",
                "text_exact": "Triệu đồng",
            },
        ],
    }


def _evaluate(pages: list[tuple[dict, dict]], context: dict) -> dict:
    return evaluate_gemini_json_dual_axis_family_cluster_v1(
        regions=[region for region, _page in pages],
        page_json_by_version={region["page_json_version_id"]: page for region, page in pages},
        document_context=context,
        compiled_specs=_compiled(),
        query_receipt={"exact_region_axis_sha256": "f" * 64},
    )


def test_specs_keep_authoritative_context_only_schema_identity() -> None:
    compiled = _compiled()

    assert compiled["topology"]["family_id"] == "LOAN_GEOGRAPHIC_CLASSIFICATION"
    assert compiled["schema"]["family_owner_report_norm_id"] == 716
    assert compiled["schema"]["family_report_norm_id"] == 759
    assert compiled["bindings"] == {"DOMESTIC_TOTAL": 5752, "FOREIGN_TOTAL": 765}
    assert compiled["schema"]["family_root_mapping_policy"] == (
        "REQUIRE_HIERARCHICALLY_RESOLVED_CONTEXT_ONLY"
    )


def test_row_orientation_two_periods_closes_and_maps_only_two_children() -> None:
    version = _version("a")
    page = _row_page(current=True)
    page["sections"][0]["tables"].append(_row_page(current=False)["sections"][0]["tables"][0])
    regions = [
        {
            **_region(version=version, page=20, orientation="ROW_ROLES_METRIC_COLUMN"),
            "table_id": table_id,
        }
        for table_id in ("t1", "t2")
    ]

    result = _evaluate(
        [(regions[0], page), (regions[1], page)],
        _context("31/12/2025", "31/12/2024"),
    )

    assert result["status"] == READY
    assert [mapping["report_norm_id"] for mapping in result["mappings"]] == [5752, 765]
    assert [binding["role"] for binding in result["mapping_lane_source_bindings"]] == [
        "DOMESTIC_TOTAL",
        "FOREIGN_TOTAL",
    ]
    assert all(
        mapping["dual_axis_lane_source_binding_id"].startswith("gjdafv1:source-binding:")
        for mapping in result["mappings"]
    )
    assert [source["period"] for source in result["mapping_lane_source_bindings"][0]["lanes"]] == [
        "2025-12-31",
        "2024-12-31",
    ]


def test_one_period_exhaustive_table_uses_document_period_and_unit_context() -> None:
    version = _version("b")
    page = _row_page(include_total=False)
    table = page["sections"][0]["tables"][0]
    table["title_exact"] = None
    table["unit_exact"] = None
    context = _context("31/12/2025")
    context["unit_evidence"] = [
        {
            "physical_page": 19,
            "section_id": "s1",
            "source_kind": "TABLE_UNIT",
            "table_id": "t9",
            "text_exact": "Triệu đồng",
        }
    ]

    result = _evaluate(
        [
            (
                _region(version=version, page=20, orientation="ROW_ROLES_METRIC_COLUMN"),
                page,
            )
        ],
        context,
    )

    assert result["status"] == READY
    equation = result["dual_axis_projection_receipt"]["source_table_equations"][0]
    assert equation["mode"] == "EXHAUSTIVE_ROLE_PAIR_WITHOUT_PRINTED_TOTAL"
    assert result["dual_axis_projection_receipt"]["period_axis"]["periods"] == ["2025-12-31"]


def test_repeated_visible_dash_is_canonical_zero_without_changing_raw_source() -> None:
    version = _version("9")
    page = _row_page()
    table = page["sections"][0]["tables"][0]
    table["rows"][1]["values_exact"][0] = "--"
    table["rows"][2]["values_exact"][0] = "120"

    result = _evaluate(
        [
            (
                _region(version=version, page=20, orientation="ROW_ROLES_METRIC_COLUMN"),
                page,
            )
        ],
        _context("31/12/2025"),
    )

    assert result["status"] == READY
    foreign = next(mapping for mapping in result["mappings"] if mapping["role"] == "FOREIGN_TOTAL")
    assert foreign["values"] == [{"coefficient": 0, "source_text": "--", "state": "DASH_ZERO"}]


def test_column_orientation_adjacent_pair_preserves_dash_and_derives_only_foreign_blank() -> None:
    current_version = _version("c")
    prior_version = _version("d")
    current = _column_page(current=True, continuation="CONTINUES_ON_NEXT_PAGE")
    prior = _column_page(current=False, blank_role="FOREIGN_TOTAL")
    # Column reorder is a presentation variant, not semantic drift.
    for page in (current, prior):
        table = page["sections"][0]["tables"][0]
        table["columns"][0], table["columns"][1] = table["columns"][1], table["columns"][0]
        table["rows"][0]["values_exact"][0], table["rows"][0]["values_exact"][1] = (
            table["rows"][0]["values_exact"][1],
            table["rows"][0]["values_exact"][0],
        )

    result = _evaluate(
        [
            (
                _region(
                    version=current_version,
                    page=20,
                    orientation="METRIC_ROW_ROLE_COLUMNS",
                ),
                current,
            ),
            (
                _region(
                    version=prior_version,
                    page=21,
                    orientation="METRIC_ROW_ROLE_COLUMNS",
                ),
                prior,
            ),
        ],
        _context("30/06/2026", "31/12/2025"),
    )

    assert result["status"] == READY
    foreign = next(mapping for mapping in result["mappings"] if mapping["role"] == "FOREIGN_TOTAL")
    assert [value["state"] for value in foreign["values"]] == [
        "DASH_ZERO",
        "DERIVED_ZERO_FROM_EXACT_VISIBLE_TOTAL_AND_OTHER_ROLE",
    ]
    binding = next(
        item for item in result["mapping_lane_source_bindings"] if item["role"] == "FOREIGN_TOTAL"
    )
    assert binding["lanes"][1]["axis_source"]["column_id"] in {"c1", "c2"}
    assert binding["lanes"][1]["blank_zero_equation"]["total_cell"]["raw_value_exact"] == "180"


def test_adjacent_period_complement_ignores_repeated_section_date_and_spurious_dates() -> None:
    current_version = _version("2")
    prior_version = _version("3")
    current = _column_page(current=True, continuation="CONTINUES_ON_NEXT_PAGE")
    prior = _column_page(current=False)
    prior["sections"][0]["tables"][0]["title_exact"] = None
    prior["sections"][0]["title_exact"] = (
        "Thuyết minh giữa niên độ tại ngày 30 tháng 6 năm 2026 theo khu vực địa lý"
    )
    period_evidence = []
    for text, pages in (
        ("30/06/2026", range(1, 9)),
        ("31/12/2025", range(1, 5)),
        ("30/09/2026", [30]),
        ("01/01/2026", [31]),
    ):
        period_evidence.extend(
            {
                "physical_page": page,
                "section_id": "s1",
                "source_kind": "COLUMN_HEADER",
                "table_id": "t1",
                "text_exact": text,
            }
            for page in pages
        )
    context = _context()
    context["period_evidence"] = period_evidence
    regions = [
        _region(
            version=current_version,
            page=20,
            orientation="METRIC_ROW_ROLE_COLUMNS",
        ),
        _region(
            version=prior_version,
            page=21,
            orientation="METRIC_ROW_ROLE_COLUMNS",
        ),
    ]

    result = _evaluate([(regions[0], current), (regions[1], prior)], context)

    assert result["status"] == READY
    period_axis = result["dual_axis_projection_receipt"]["period_axis"]
    assert period_axis["periods"] == ["2026-06-30", "2025-12-31"]
    assert period_axis["document_balance_axis"]["dominant_candidate_dates"] == [
        "2025-12-31",
        "2026-06-30",
    ]

    prior["sections"][0]["tables"][0]["title_exact"] = "Tại ngày 31 tháng 3 năm 2025"
    conflict = _evaluate([(regions[0], current), (regions[1], prior)], context)
    assert conflict["status"] == UNRESOLVED
    assert "SOURCE_TABLE_LOCAL_BALANCE_PERIOD_AXIS_IS_NOT_EXACT" in conflict["reasons"]


def test_adjacent_period_cluster_requires_explicit_continuation_binding() -> None:
    pages = [
        (
            _region(
                version=_version("4"),
                page=20,
                orientation="METRIC_ROW_ROLE_COLUMNS",
            ),
            _column_page(current=True),
        ),
        (
            _region(
                version=_version("5"),
                page=21,
                orientation="METRIC_ROW_ROLE_COLUMNS",
            ),
            _column_page(current=False),
        ),
    ]

    result = _evaluate(pages, _context("30/06/2026", "31/12/2025"))

    assert result["status"] == UNRESOLVED
    assert "ADJACENT_PERIOD_TABLE_CLUSTER_HAS_NO_CONTINUATION_BINDING" in result["reasons"]


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("BROAD_METRIC", "METRIC_ROW_ROLE_COLUMN_EXACT_ASSIGNMENT_COUNT_NOT_ONE"),
        ("DUPLICATE_METRIC", "METRIC_ROW_ROLE_COLUMN_EXACT_ASSIGNMENT_COUNT_NOT_ONE"),
        ("DUPLICATE_ROLE", "METRIC_ROW_ROLE_COLUMN_EXACT_ASSIGNMENT_COUNT_NOT_ONE"),
        ("HARD_NEGATIVE", "HARD_NEGATIVE_FAMILY_TITLE_PRESENT"),
        ("STRUCTURAL_RESET", "STRUCTURAL_RESET_FAMILY_TITLE_PRESENT"),
        ("BLANK_DOMESTIC", "BLANK_ROLE_CELL_IS_NOT_DECLARED_ZERO_DERIVABLE:DOMESTIC_TOTAL"),
        ("BLANK_FOREIGN_NO_TOTAL", "BLANK_ROLE_CELL_HAS_NO_EXACT_TOTAL_EQUATION:FOREIGN_TOTAL"),
        ("TOTAL_MISMATCH", "DUAL_AXIS_VISIBLE_TOTAL_EQUATION_FAILED"),
        ("UNIT_SCALE_CONFLICT", "DUAL_AXIS_SOURCE_TABLE_MONEY_UNIT_SCALE_CONFLICT"),
    ],
)
def test_dual_axis_adversarial_cells_and_context_fail_closed(mutation: str, reason: str) -> None:
    version = _version("e")
    page = _column_page(current=True)
    table = page["sections"][0]["tables"][0]
    if mutation == "BROAD_METRIC":
        table["rows"][0]["label_exact"] = (
            "Tổng dư nợ cho vay khách hàng, mua nợ và cấp tín dụng cho các TCTD khác"
        )
    elif mutation == "DUPLICATE_METRIC":
        table["rows"].append(deepcopy(table["rows"][0]))
    elif mutation == "DUPLICATE_ROLE":
        table["columns"].insert(1, deepcopy(table["columns"][0]))
        table["rows"][0]["values_exact"].insert(1, table["rows"][0]["values_exact"][0])
    elif mutation == "HARD_NEGATIVE":
        page["sections"][0]["title_exact"] = "Báo cáo bộ phận theo khu vực địa lý"
    elif mutation == "STRUCTURAL_RESET":
        page["sections"][0]["title_exact"] = "Phân tích theo loại hình doanh nghiệp"
    elif mutation == "BLANK_DOMESTIC":
        page = _column_page(current=True, blank_role="DOMESTIC_TOTAL")
    elif mutation == "BLANK_FOREIGN_NO_TOTAL":
        page = _column_page(current=True, blank_role="FOREIGN_TOTAL", include_total=False)
    elif mutation == "TOTAL_MISMATCH":
        table["rows"][0]["values_exact"][-1] = "999"
    elif mutation == "UNIT_SCALE_CONFLICT":
        table["unit_exact"] = "Tỷ VND / Triệu VND"

    result = _evaluate(
        [
            (
                _region(version=version, page=20, orientation="METRIC_ROW_ROLE_COLUMNS"),
                page,
            )
        ],
        _context("30/06/2026"),
    )

    assert result["status"] == UNRESOLVED
    assert reason in result["reasons"]


def test_nonadjacent_period_cluster_fails_but_equivalent_unit_spellings_canonicalize() -> None:
    current_version = _version("f")
    prior_version = _version("1")
    pages = [
        (
            _region(
                version=current_version,
                page=20,
                orientation="METRIC_ROW_ROLE_COLUMNS",
            ),
            _column_page(current=True, continuation="CONTINUES_ON_NEXT_PAGE"),
        ),
        (
            _region(
                version=prior_version,
                page=22,
                orientation="METRIC_ROW_ROLE_COLUMNS",
            ),
            _column_page(current=False),
        ),
    ]
    context = _context("30/06/2026", "31/12/2025")
    result = _evaluate(pages, context)
    assert result["status"] == UNRESOLVED
    assert "DUAL_AXIS_CLUSTER_IS_NOT_SAME_OR_ADJACENT_PAGE" in result["reasons"]

    one = pages[:1]
    table = one[0][1]["sections"][0]["tables"][0]
    table["unit_exact"] = None
    context["unit_evidence"] = [
        {
            "physical_page": 20,
            "section_id": "s1",
            "source_kind": "COLUMN_HEADER",
            "table_id": "t1",
            "text_exact": alias,
        }
        for alias in ("Triệu đồng", "Triệu VND")
    ]
    equivalent = _evaluate(one, context)
    assert equivalent["status"] == READY
    assert equivalent["reasons"] == []


def test_mixed_orientation_and_duplicate_period_clusters_fail_closed() -> None:
    current_region = _region(
        version=_version("6"),
        page=20,
        orientation="METRIC_ROW_ROLE_COLUMNS",
    )
    other_region = _region(
        version=_version("7"),
        page=21,
        orientation="ROW_ROLES_METRIC_COLUMN",
    )
    mixed = _evaluate(
        [
            (
                current_region,
                _column_page(current=True, continuation="CONTINUES_ON_NEXT_PAGE"),
            ),
            (other_region, _row_page(current=False)),
        ],
        _context("30/06/2026", "31/12/2025"),
    )
    assert mixed["status"] == UNRESOLVED
    assert "DUAL_AXIS_CLUSTER_ORIENTATION_IS_NOT_UNIQUE" in mixed["reasons"]

    other_region["orientation"] = "METRIC_ROW_ROLE_COLUMNS"
    duplicate = _evaluate(
        [
            (
                current_region,
                _column_page(current=True, continuation="CONTINUES_ON_NEXT_PAGE"),
            ),
            (other_region, _column_page(current=True)),
        ],
        _context("30/06/2026", "31/12/2025"),
    )
    assert duplicate["status"] == UNRESOLVED
    assert "SOURCE_TABLE_PERIODS_ARE_NOT_DISTINCT" in duplicate["reasons"]


@pytest.mark.parametrize(
    "family",
    ["loan-currency-classification", "loan-quality-classification"],
)
def test_v5_and_v6_specs_still_reject_a_single_money_lane(family: str) -> None:
    root = ROOT / "config/families"
    topology = json.loads((root / f"tm-{family}-topology-v1.json").read_text())
    evaluation = json.loads((root / f"tm-{family}-evaluation-v1.json").read_text())
    schema = json.loads((root / f"tm-{family}-schema-binding-v1.json").read_text())
    evaluation["expected_lane_unit_kind_alternatives"] = [["MONEY"]]

    with pytest.raises(GeminiJsonFlatAccountingFamilyV1Error):
        compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
