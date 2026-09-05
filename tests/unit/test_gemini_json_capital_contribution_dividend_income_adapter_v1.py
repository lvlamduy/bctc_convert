from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.gemini_json_capital_contribution_dividend_income_family_v1 import (
    READY,
    UNRESOLVED,
    build_gemini_json_capital_contribution_dividend_income_region_query_receipt_v1,
    coalesce_gemini_json_capital_contribution_dividend_income_document_v1,
    compile_gemini_json_capital_contribution_dividend_income_family_specs_v1,
    evaluate_gemini_json_capital_contribution_dividend_income_family_cluster_v1,
    validate_gemini_json_capital_contribution_dividend_income_family_candidate_replay_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    coalesce_gemini_json_multitable_hierarchical_document_v1,
)

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "a" * 64
VERSION_ID = "gfpstorev1:json:" + "b" * 64
SOURCE_SHA256 = "c" * 64


def _json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict[str, Any]:
    return compile_gemini_json_capital_contribution_dividend_income_family_specs_v1(
        _json("tm-capital-contribution-dividend-income-topology-v1.json"),
        _json("tm-capital-contribution-dividend-income-evaluation-v1.json"),
        _json("tm-capital-contribution-dividend-income-schema-binding-v1.json"),
    )


def _row(label: str, values: list[str | None], *, kind: str = "ITEM") -> dict[str, Any]:
    return {
        "hierarchy_path_exact": [label],
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _table(
    rows: list[dict[str, Any]],
    *,
    unit: str | None = "Triệu đồng",
) -> dict[str, Any]:
    unit_path = [] if unit is None else [unit]
    return {
        "columns": [
            {"header_path_exact": ["Năm 2026", *unit_path], "value_kind": "MONEY"},
            {"header_path_exact": ["Năm 2025", *unit_path], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": rows,
        "title_exact": None,
        "unit_exact": unit,
    }


def _primary_page(*, root_count: int = 1, statement_type: str = "INCOME_STATEMENT") -> dict[str, Any]:
    rows = [
        _row("Thu nhập lãi và các khoản thu nhập tương tự", ["100", "90"]),
        _row("Thu nhập góp vốn, mua cổ phần", ["12", "10"]),
        _row("Lợi nhuận sau thuế", ["50", "40"], kind="TOTAL"),
    ]
    if root_count == 2:
        rows.insert(2, _row("Thu nhập từ góp vốn, mua cổ phần", ["12", "10"]))
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "PRIMARY_STATEMENT",
                "narratives_exact": [],
                "statement_type": statement_type,
                "tables": [_table(rows)],
                "title_exact": "Báo cáo kết quả hoạt động kinh doanh",
            }
        ],
        "status": "PRIMARY_FINANCIAL_STATEMENT",
    }


def _primary_unit_context_page(unit: str) -> dict[str, Any]:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "PRIMARY_STATEMENT",
                "narratives_exact": [],
                "statement_type": "BALANCE_SHEET",
                "tables": [
                    {
                        **_table([_row("Tổng tài sản", ["100", "90"])], unit=unit),
                        "title_exact": "Báo cáo tình hình tài chính",
                    }
                ],
                "title_exact": "Báo cáo tình hình tài chính",
            }
        ],
        "status": "PRIMARY_FINANCIAL_STATEMENT",
    }


def _note_unit_context_page(unit: str) -> dict[str, Any]:
    page = _primary_unit_context_page(unit)
    page["status"] = "FINANCIAL_NOTE_CONTENT"
    page["sections"][0]["content_kind"] = "FINANCIAL_NOTE"
    page["sections"][0]["statement_type"] = "NOT_APPLICABLE"
    page["sections"][0]["title_exact"] = "Thuyết minh khác"
    page["sections"][0]["tables"][0]["title_exact"] = "Thuyết minh khác"
    return page


def _detail_page(*, unit: str | None) -> dict[str, Any]:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [
                    {
                        **_table(
                            [
                                _row(
                                    "Cổ tức nhận được trong kỳ từ góp vốn, mua cổ phần",
                                    ["12", "10"],
                                ),
                                _row("Các khoản thu nhập khác", ["3", "2"]),
                                {
                                    "hierarchy_path_exact": [None],
                                    "label_exact": None,
                                    "row_kind": "TOTAL",
                                    "values_exact": ["15", "12"],
                                },
                            ],
                            unit=unit,
                        ),
                        "title_exact": "Thu nhập từ góp vốn, mua cổ phần",
                    }
                ],
                "title_exact": "Thu nhập từ góp vốn, mua cổ phần",
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _record(page: dict[str, Any], *, version_id: str = VERSION_ID) -> dict[str, Any]:
    return {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": version_id,
        "physical_page": 1,
        "selected_page_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }


def _adapter_evaluate(records: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    compiled = _compiled()
    cluster = coalesce_gemini_json_capital_contribution_dividend_income_document_v1(
        page_records=records,
        compiled_specs=compiled,
    )
    assert cluster["status"] == READY
    pages = {item["page_json_version_id"]: item["page_json"] for item in records}
    receipt = build_gemini_json_capital_contribution_dividend_income_region_query_receipt_v1(
        cluster["component_regions"], cluster=cluster
    )
    candidate = evaluate_gemini_json_capital_contribution_dividend_income_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version=pages,
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    validate_gemini_json_capital_contribution_dividend_income_family_candidate_replay_v1(
        candidate,
        regions=cluster["component_regions"],
        page_json_by_version=pages,
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    return cluster, candidate


def test_unique_primary_income_statement_root_maps_only_rnid_1198() -> None:
    page = _primary_page()
    compiled = _compiled()
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert base["status"] != READY

    cluster, candidate = _adapter_evaluate([_record(page)])
    assert candidate["status"] == READY
    assert [(item["role"], item["report_norm_id"]) for item in candidate["mappings"]] == [
        ("FAMILY_ROOT_TOTAL", 1198)
    ]
    assert [cell["coefficient"] for cell in candidate["mappings"][0]["values"]] == [12, 10]
    receipt = cluster["owner_receipt"][
        "capital_contribution_dividend_income_primary_root_receipt"
    ]
    assert receipt["statement_type_before"] == "INCOME_STATEMENT"
    assert receipt["locator"]["row_id"] == "r2"


def test_primary_root_projection_ignores_malformed_unrelated_statement_cell() -> None:
    page = _primary_page()
    page["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "null"

    _cluster, candidate = _adapter_evaluate([_record(page)])

    assert candidate["status"] == READY
    assert [item["report_norm_id"] for item in candidate["mappings"]] == [1198]
    assert [cell["coefficient"] for cell in candidate["mappings"][0]["values"]] == [12, 10]


def test_primary_fallback_rejects_duplicate_and_cash_flow_roots() -> None:
    compiled = _compiled()
    duplicate = coalesce_gemini_json_capital_contribution_dividend_income_document_v1(
        page_records=[_record(_primary_page(root_count=2))], compiled_specs=compiled
    )
    assert duplicate["status"] == UNRESOLVED
    assert duplicate["reasons"] == ["MULTIPLE_EXACT_PRIMARY_INCOME_STATEMENT_FAMILY_ROOTS"]

    cash_flow = coalesce_gemini_json_capital_contribution_dividend_income_document_v1(
        page_records=[_record(_primary_page(statement_type="CASH_FLOW"))],
        compiled_specs=compiled,
    )
    assert cash_flow["status"] != READY
    assert cash_flow["component_regions"] == []


def test_explicit_local_vnd_retries_only_after_base_failure() -> None:
    _cluster, candidate = _adapter_evaluate([_record(_detail_page(unit="VND"))])
    assert candidate["status"] == READY
    assert {item["unit"] for item in candidate["mappings"]} == {"VND"}
    receipt = candidate["closure_receipt"][
        "capital_contribution_dividend_income_adapter_receipt"
    ]
    assert receipt["vnd_retry_receipt"]["rule"] == (
        "EVERY_SELECTED_TABLE_HAS_EXPLICIT_LOCAL_VND"
    )


def test_unitless_target_with_mixed_document_units_remains_unresolved() -> None:
    target = _detail_page(unit=None)
    context = _primary_page()
    context["sections"][0]["tables"][0]["unit_exact"] = "VND"
    for column in context["sections"][0]["tables"][0]["columns"]:
        column["header_path_exact"] = ["Năm 2026", "VND"]
    records = [
        _record(context, version_id="gfpstorev1:json:" + "d" * 64),
        {**_record(target), "physical_page": 2, "selected_page_ordinal": 2},
    ]
    compiled = _compiled()
    cluster = coalesce_gemini_json_capital_contribution_dividend_income_document_v1(
        page_records=records, compiled_specs=compiled
    )
    assert cluster["status"] == READY
    receipt = build_gemini_json_capital_contribution_dividend_income_region_query_receipt_v1(
        cluster["component_regions"], cluster=cluster
    )
    candidate = evaluate_gemini_json_capital_contribution_dividend_income_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={item["page_json_version_id"]: item["page_json"] for item in records},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_unitless_primary_root_uses_two_page_primary_statement_vnd_consensus() -> None:
    target = _record(_primary_page())
    target["page_json"]["sections"][0]["tables"][0]["unit_exact"] = None
    for column in target["page_json"]["sections"][0]["tables"][0]["columns"]:
        column["header_path_exact"] = [column["header_path_exact"][0]]
    contexts = [
        {
            **_record(
                _primary_unit_context_page("VND"),
                version_id="gfpstorev1:json:" + marker * 64,
            ),
            "physical_page": page,
            "selected_page_ordinal": page,
        }
        for marker, page in (("d", 2), ("e", 3))
    ]
    note = {
        **_record(
            _note_unit_context_page("Triệu đồng"),
            version_id="gfpstorev1:json:" + "f" * 64,
        ),
        "physical_page": 4,
        "selected_page_ordinal": 4,
    }
    _cluster, candidate = _adapter_evaluate([target, *contexts, note])
    assert candidate["status"] == READY
    assert {item["unit"] for item in candidate["mappings"]} == {"VND"}
    receipt = candidate["closure_receipt"][
        "capital_contribution_dividend_income_adapter_receipt"
    ]["vnd_retry_receipt"]
    assert receipt["rule"] == (
        "PRIMARY_FINANCIAL_STATEMENT_EXPLICIT_UNIT_CONSENSUS_ON_AT_LEAST_"
        "TWO_DISTINCT_PAGES_IS_UNIQUELY_VND"
    )


def test_primary_statement_vnd_context_requires_two_pages_and_no_mixed_unit() -> None:
    def target() -> dict[str, Any]:
        value = _record(_primary_page())
        value["page_json"]["sections"][0]["tables"][0]["unit_exact"] = None
        for column in value["page_json"]["sections"][0]["tables"][0]["columns"]:
            column["header_path_exact"] = [column["header_path_exact"][0]]
        return value

    one_context = {
        **_record(
            _primary_unit_context_page("VND"),
            version_id="gfpstorev1:json:" + "d" * 64,
        ),
        "physical_page": 2,
        "selected_page_ordinal": 2,
    }
    compiled = _compiled()
    note = {
        **_record(
            _note_unit_context_page("Triệu đồng"),
            version_id="gfpstorev1:json:" + "f" * 64,
        ),
        "physical_page": 4,
        "selected_page_ordinal": 4,
    }
    records = [target(), one_context, note]
    cluster = coalesce_gemini_json_capital_contribution_dividend_income_document_v1(
        page_records=records, compiled_specs=compiled
    )
    receipt = build_gemini_json_capital_contribution_dividend_income_region_query_receipt_v1(
        cluster["component_regions"], cluster=cluster
    )
    pages = {item["page_json_version_id"]: item["page_json"] for item in records}
    candidate = evaluate_gemini_json_capital_contribution_dividend_income_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version=pages,
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    assert candidate["status"] == UNRESOLVED

    contexts = [
        one_context,
        {
            **_record(
                _primary_unit_context_page("VND"),
                version_id="gfpstorev1:json:" + "e" * 64,
            ),
            "physical_page": 3,
            "selected_page_ordinal": 3,
        },
    ] + [
        {
            **_record(
                _primary_unit_context_page("Triệu đồng"),
                version_id="gfpstorev1:json:" + marker * 64,
            ),
            "physical_page": page,
            "selected_page_ordinal": page,
        }
        for marker, page in (("6", 5), ("7", 6))
    ]
    records = sorted(
        [target(), *contexts, note], key=lambda item: item["selected_page_ordinal"]
    )
    cluster = coalesce_gemini_json_capital_contribution_dividend_income_document_v1(
        page_records=records, compiled_specs=compiled
    )
    receipt = build_gemini_json_capital_contribution_dividend_income_region_query_receipt_v1(
        cluster["component_regions"], cluster=cluster
    )
    candidate = evaluate_gemini_json_capital_contribution_dividend_income_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={item["page_json_version_id"]: item["page_json"] for item in records},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    assert candidate["closure_receipt"][
        "capital_contribution_dividend_income_adapter_receipt"
    ]["vnd_retry_receipt"] is None
    if candidate["status"] == READY:
        assert {item["unit"] for item in candidate["mappings"]} == {"MILLION_VND"}
    else:
        assert candidate["status"] == UNRESOLVED


def test_million_vnd_base_candidate_is_byte_preserved_without_adapter_receipt() -> None:
    page = _detail_page(unit="Triệu đồng")
    compiled = _compiled()
    cluster = coalesce_gemini_json_capital_contribution_dividend_income_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    receipt = build_gemini_json_capital_contribution_dividend_income_region_query_receipt_v1(
        cluster["component_regions"], cluster=cluster
    )
    candidate = evaluate_gemini_json_capital_contribution_dividend_income_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    assert candidate["status"] == READY
    assert (
        "capital_contribution_dividend_income_adapter_receipt"
        not in candidate["closure_receipt"]
    )


def test_explicit_vnd_zero_decimal_suffix_is_parsed_as_integer_and_source_preserved() -> None:
    page = _detail_page(unit="VND")
    table = page["sections"][0]["tables"][0]
    table["rows"][0]["values_exact"] = ["12.345,00", "10.005,00"]
    table["rows"][1]["values_exact"] = ["3.000,00", "2.000,00"]
    table["rows"][2]["values_exact"] = ["15.345,00", "12.005,00"]

    _cluster, candidate = _adapter_evaluate([_record(page)])

    assert candidate["status"] == READY
    by_role = {item["role"]: item for item in candidate["mappings"]}
    assert [cell["coefficient"] for cell in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [
        15_345,
        12_005,
    ]
    assert [cell["source_text"] for cell in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [
        "15.345,00",
        "12.005,00",
    ]
    assert {cell["state"] for cell in by_role["FAMILY_ROOT_TOTAL"]["values"]} == {
        "RAW_VND_INTEGER_WITH_EXPLICIT_ZERO_DECIMAL_SUFFIX"
    }
    adapter = candidate["closure_receipt"][
        "capital_contribution_dividend_income_adapter_receipt"
    ]
    assert len(adapter["vnd_zero_decimal_projections"]) == 6
    assert {
        item["rule"] for item in adapter["vnd_zero_decimal_projections"]
    } == {"LITERAL_ZERO_DECIMAL_SUFFIX_REMOVED_FOR_INTEGER_PARSE_ONLY_NO_ROUNDING_NO_SCALING"}


def test_zero_decimal_projection_rejects_nonzero_fraction_or_missing_local_vnd() -> None:
    nonzero = _detail_page(unit="VND")
    nonzero["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "12.345,01"
    compiled = _compiled()
    cluster = coalesce_gemini_json_capital_contribution_dividend_income_document_v1(
        page_records=[_record(nonzero)], compiled_specs=compiled
    )
    receipt = build_gemini_json_capital_contribution_dividend_income_region_query_receipt_v1(
        cluster["component_regions"], cluster=cluster
    )
    candidate = evaluate_gemini_json_capital_contribution_dividend_income_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: nonzero},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    adapter = candidate.get("closure_receipt", {}).get(
        "capital_contribution_dividend_income_adapter_receipt"
    )
    assert adapter is None or adapter["vnd_zero_decimal_projections"] == []

    missing_unit = _detail_page(unit=None)
    missing_unit["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = (
        "12.345,00"
    )
    cluster = coalesce_gemini_json_capital_contribution_dividend_income_document_v1(
        page_records=[_record(missing_unit)], compiled_specs=compiled
    )
    receipt = build_gemini_json_capital_contribution_dividend_income_region_query_receipt_v1(
        cluster["component_regions"], cluster=cluster
    )
    candidate = evaluate_gemini_json_capital_contribution_dividend_income_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: missing_unit},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    adapter = candidate.get("closure_receipt", {}).get(
        "capital_contribution_dividend_income_adapter_receipt"
    )
    assert adapter is None or adapter["vnd_zero_decimal_projections"] == []


def test_printed_root_governs_when_one_component_equation_lane_is_blank() -> None:
    page = _detail_page(unit="Triệu đồng")
    table = page["sections"][0]["tables"][0]
    table["rows"] = [
        _row("Từ góp vốn, đầu tư dài hạn", ["8.521", None]),
        _row(
            "Phân chia lãi theo phương pháp vốn chủ sở hữu của các khoản đầu tư "
            "vào công ty liên doanh",
            ["310.951", "71.664"],
        ),
        {
            "hierarchy_path_exact": [None],
            "label_exact": None,
            "row_kind": "TOTAL",
            "values_exact": ["319.472", "71.664"],
        },
    ]

    _cluster, candidate = _adapter_evaluate([_record(page)])

    by_role = {item["role"]: item for item in candidate["mappings"]}
    assert [cell["coefficient"] for cell in by_role["LONG_TERM_CAPITAL_DIVIDEND"]["values"]] == [
        8_521,
        None,
    ]
    assert [cell["coefficient"] for cell in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [
        319_472,
        71_664,
    ]
    assert by_role["FAMILY_ROOT_TOTAL"]["state"] == (
        "SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_WITH_INCOMPLETE_COMPONENT_EQUATION"
    )
    adapter = candidate["closure_receipt"][
        "capital_contribution_dividend_income_adapter_receipt"
    ]
    receipt = adapter["partial_root_projection_receipt"]
    assert receipt["source_lane_statuses"] == [
        "EXACT",
        "INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL",
    ]
    assert not any(
        item["equation_kind"]
        == "EXACT_COMPLETE_TOP_LEVEL_COMPONENT_SUM_DERIVES_FAMILY_ROOT"
        for item in candidate["closure_receipt"]["equations"]
    )
