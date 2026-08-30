from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_equity_matrix_accounting_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    GeminiJsonEquityMatrixAccountingFamilyV1Error,
    build_gemini_json_equity_matrix_region_query_receipt_v1,
    coalesce_gemini_json_equity_matrix_document_v1,
    compile_gemini_json_equity_matrix_family_specs_v1,
    evaluate_gemini_json_equity_matrix_family_cluster_v1,
    validate_gemini_json_equity_matrix_family_candidate_replay_v1,
)
from bctc_ai.evaluation.gemini_json_liquidity_risk_matrix_v1 import (
    LIQUIDITY_RISK_CLAIM_BOUNDARY,
    GeminiJsonLiquidityRiskMatrixV1Error,
    classify_liquidity_column_role_v1,
    validate_liquidity_row_alignment_receipt_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "4" * 64
SOURCE_SHA256 = "5" * 64


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict:
    return compile_gemini_json_equity_matrix_family_specs_v1(
        _json("tm-liquidity-risk-topology-v1.json"),
        _json("tm-liquidity-risk-evaluation-v1.json"),
        _json("tm-liquidity-risk-schema-binding-v1.json"),
    )


def _column(label: str) -> dict:
    return {"header_path_exact": [label], "value_kind": "MONEY"}


def _row(label: str, values: list[str | None], *, kind: str = "ITEM") -> dict:
    return {
        "hierarchy_path_exact": [label],
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _table() -> dict:
    columns = [
        _column("Quá hạn"),
        _column("Quá hạn trên 03 tháng"),
        _column("Quá hạn đến 03 tháng"),
        _column("Đến 01 tháng"),
        _column("Từ trên 01 tháng đến 03 tháng"),
        _column("Từ trên 03 tháng đến 12 tháng"),
        _column("Từ trên 01 năm đến 05 năm"),
        _column("Trên 05 năm"),
        _column("Tổng cộng"),
    ]
    return {
        "columns": columns,
        "continuation": "NONE",
        "rows": [
            _row("Tổng tài sản", ["100"] * len(columns), kind="TOTAL"),
            _row("Tổng nợ phải trả", ["40"] * len(columns), kind="TOTAL"),
            _row("Mức chênh thanh khoản ròng", ["60"] * len(columns), kind="TOTAL"),
        ],
        "title_exact": "Tại ngày 31/12/2025",
        "unit_exact": "Triệu VND",
    }


def _page(table: dict | None, *, title: str | None = "Rủi ro thanh khoản") -> dict:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [] if table is None else [table],
                "title_exact": title,
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _record(page: dict, *, ordinal: int = 1) -> dict:
    return {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": "gfpstorev1:json:" + str(ordinal) * 64,
        "physical_page": ordinal,
        "selected_page_ordinal": ordinal,
        "source_logical_name": "liquidity-risk-fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }


def _evaluate(records: list[dict]) -> tuple[dict, dict, dict]:
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
    return compiled, cluster, candidate


def test_liquidity_triplet_maps_exact_core_matrix() -> None:
    compiled, _cluster, candidate = _evaluate([_record(_page(_table()))])
    assert compiled["claim_boundary"] == LIQUIDITY_RISK_CLAIM_BOUNDARY
    assert candidate["status"] == READY
    assert candidate["claim_boundary"] == LIQUIDITY_RISK_CLAIM_BOUNDARY
    assert len(candidate["mappings"]) == 37  # root + 9 branches + 27 cells
    assert len(candidate["closure_receipt"]["equations"]) == 9
    assert all(item["status"] == "EXACT" for item in candidate["closure_receipt"]["equations"])


@pytest.mark.parametrize(
    ("surface", "expected"),
    [
        ("Quá hạn", "OVERDUE"),
        ("Quá hạn trên 03 tháng", "OVERDUE_GT3M"),
        ("Quá hạn đến 03 tháng", "OVERDUE_LE3M"),
        ("Từ 01T đến 03T", "WITHIN_1_3M"),
        ("Từ trên 03 tháng đến 12 tháng", "WITHIN_3_12M"),
        ("Từ 03 tháng đến 06 tháng", "WITHIN_3_6M_SOURCE"),
        ("Từ 06 tháng đến 12 tháng", "WITHIN_6_12M_SOURCE"),
    ],
)
def test_maturity_headers_are_canonicalized_without_prompt_logic(
    surface: str, expected: str
) -> None:
    role, _kind, matches = classify_liquidity_column_role_v1(
        _column(surface), compiled_specs=_compiled()
    )
    assert role == expected
    assert matches == [expected]


def test_split_source_buckets_are_retained_but_not_mapped_to_combined_schema() -> None:
    table = _table()
    table["columns"][5:6] = [
        _column("Từ 03 tháng đến 06 tháng"),
        _column("Từ 06 tháng đến 12 tháng"),
    ]
    for row in table["rows"]:
        row["values_exact"][5:6] = ["100" if row is table["rows"][0] else "40", "100"]
    table["rows"][2]["values_exact"][5:7] = ["60", "60"]
    _compiled_specs, _cluster, candidate = _evaluate([_record(_page(table))])
    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 34  # root + 8 mapped branches + 24 cells
    source_only = [
        item["column_axis"]["role"]
        for item in candidate["closure_receipt"]["table_receipts"][0]["resolved_columns"]
        if item["column_axis"]["kind"] == "SOURCE_ONLY_CURRENCY"
    ]
    assert source_only == ["WITHIN_3_6M_SOURCE", "WITHIN_6_12M_SOURCE"]


@pytest.mark.parametrize(
    ("header_path", "expected"),
    [
        (["Quá hạn", "Trên 3 tháng"], "OVERDUE_GT3M"),
        (["Quá hạn", "Đến 3 tháng"], "OVERDUE_LE3M"),
        (["Trong hạn", "Từ 1 - 3 T"], "WITHIN_1_3M"),
        (["Trong hạn", "Từ 3 - 12 T"], "WITHIN_3_12M"),
        (["Trong hạn", "Từ 1 - 5 năm"], "WITHIN_1_5Y"),
    ],
)
def test_hierarchical_and_hyphenated_corpus_headers_are_one_axis(
    header_path: list[str], expected: str
) -> None:
    role, _kind, matches = classify_liquidity_column_role_v1(
        {"header_path_exact": header_path, "value_kind": "MONEY"},
        compiled_specs=_compiled(),
    )
    assert role == expected
    assert matches == [expected]


def test_conflicting_maturity_header_fails_closed() -> None:
    table = _table()
    table["columns"][3] = _column("Đến 01 tháng / Từ 01 tháng đến 03 tháng")
    compiled = _compiled()
    role, kind, matches = classify_liquidity_column_role_v1(
        table["columns"][3], compiled_specs=compiled
    )
    assert (role, kind, matches) == (None, None, ["WITHIN_1_3M", "WITHIN_LE1M"])
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(_page(table))], compiled_specs=compiled
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []


def test_interest_rate_reset_prevents_liquidity_owner_leakage() -> None:
    owner = _record(_page(None))
    reset = _record(_page(None, title="Rủi ro lãi suất"), ordinal=2)
    matrix = _record(_page(_table(), title=None), ordinal=3)
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[owner, reset, matrix], compiled_specs=_compiled()
    )
    assert cluster["status"] == NOT_OBSERVED
    assert cluster["component_regions"] == []


def test_one_nonclosing_bucket_is_retained_without_blocking_exact_buckets() -> None:
    table = _table()
    table["rows"][2]["values_exact"][0] = "61"
    _compiled_specs, _cluster, candidate = _evaluate([_record(_page(table))])
    assert candidate["status"] == READY
    assert candidate["reasons"] == []
    assert not any(item["role"].startswith("OVERDUE:") for item in candidate["mappings"])
    frontiers = candidate["closure_receipt"]["nonclosing_currency_frontiers"]
    assert [(item["currency_role"], item["equation_status"]) for item in frontiers] == [
        ("OVERDUE", "MISMATCH")
    ]


def test_nonclosing_grand_total_keeps_the_entire_candidate_unresolved() -> None:
    table = _table()
    table["rows"][2]["values_exact"][-1] = "61"
    _compiled_specs, _cluster, candidate = _evaluate([_record(_page(table))])
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["reasons"] == ["CURRENCY_RISK_REQUIRED_EQUATION_COVERAGE_INCOMPLETE"]


def test_unique_missing_leading_blank_projects_one_core_row_without_gemini_retry() -> None:
    table = _table()
    table["rows"][0]["values_exact"] = ["10", *(["100"] * 8)]
    table["rows"][1]["values_exact"] = [*(["40"] * 8), None]
    table["rows"][2]["values_exact"] = ["10", *(["60"] * 8)]
    _compiled_specs, _cluster, candidate = _evaluate([_record(_page(table))])
    assert candidate["status"] == READY
    alignment = candidate["closure_receipt"]["table_receipts"][0]["classification"][
        "liquidity_row_alignment_receipt"
    ]
    assert alignment["status"] == "UNIQUE_BOUNDARY_BLANK_OFFSET_EXACT"
    assert [
        (item["role"], item["source_offset"], item["source_span_column_ids"])
        for item in alignment["effective_rows"]
    ] == [
        ("ASSET_TOTAL", 0, None),
        ("LIABILITY_TOTAL", 1, ["c1", "c9"]),
        ("NET_LIQUIDITY_GAP", 0, None),
    ]
    first_liability = next(
        item for item in candidate["mappings"] if item["role"] == "OVERDUE:LIABILITY_TOTAL"
    )
    assert first_liability["values"][0]["coefficient"] == 0
    assert first_liability["values"][0]["state"] == ("BLANK_ZERO_AFTER_ONE_UNKNOWN_EQUATION_EXACT")


def test_unique_row_projection_survives_one_independent_source_residual() -> None:
    table = _table()
    table["rows"][0]["values_exact"] = ["10", *(["100"] * 8)]
    table["rows"][1]["values_exact"] = [*(["40"] * 8), None]
    table["rows"][2]["values_exact"] = ["10", "60", "60", "61", *(["60"] * 5)]
    _compiled_specs, _cluster, candidate = _evaluate([_record(_page(table))])
    assert candidate["status"] == READY
    alignment = candidate["closure_receipt"]["table_receipts"][0]["classification"][
        "liquidity_row_alignment_receipt"
    ]
    assert alignment["status"] == "UNIQUE_BOUNDARY_BLANK_OFFSET_EXACT"
    liability = next(
        item for item in alignment["effective_rows"] if item["role"] == "LIABILITY_TOTAL"
    )
    assert (liability["source_offset"], liability["source_span_column_ids"]) == (
        1,
        ["c1", "c9"],
    )
    assert not any(item["role"].startswith("WITHIN_LE1M:") for item in candidate["mappings"])
    assert [
        (item["currency_role"], item["equation_status"])
        for item in candidate["closure_receipt"]["nonclosing_currency_frontiers"]
    ] == [("WITHIN_LE1M", "MISMATCH")]


def test_alignment_validator_rebuilds_the_exhaustive_minimum_span_frontier() -> None:
    table = _table()
    table["rows"][0]["values_exact"] = ["10", *(["100"] * 8)]
    table["rows"][1]["values_exact"] = [*(["40"] * 8), None]
    table["rows"][2]["values_exact"] = ["10", *(["60"] * 8)]
    _compiled_specs, _cluster, candidate = _evaluate([_record(_page(table))])
    forged = copy.deepcopy(
        candidate["closure_receipt"]["table_receipts"][0]["classification"][
            "liquidity_row_alignment_receipt"
        ]
    )
    assert len(forged["candidate_offset_axes"]) == 1
    forged["candidate_offset_axes"] = []
    forged["status"] = "NO_UNIQUE_EXACT_ALIGNMENT"
    forged["effective_rows"] = [
        {
            **row,
            "effective_values_exact": copy.deepcopy(row["raw_values_exact"]),
            "source_offset": 0,
            "source_span_column_ids": None,
        }
        for row in forged["effective_rows"]
    ]
    forged["alignment_receipt_id"] = "gjlrmv1:alignment:" + canonical_json_sha256_v1(
        {key: value for key, value in forged.items() if key != "alignment_receipt_id"}
    )
    with pytest.raises(
        GeminiJsonLiquidityRiskMatrixV1Error,
        match="candidate frontier is not exhaustive",
    ):
        validate_liquidity_row_alignment_receipt_v1(forged)


def test_row_offset_never_discards_a_visible_boundary_value() -> None:
    table = _table()
    table["rows"][0]["values_exact"] = ["10", *(["100"] * 8)]
    table["rows"][1]["values_exact"] = ["40"] * 9
    table["rows"][2]["values_exact"] = ["10", *(["60"] * 8)]
    _compiled_specs, _cluster, candidate = _evaluate([_record(_page(table))])
    assert candidate["status"] == READY
    alignment = candidate["closure_receipt"]["table_receipts"][0]["classification"][
        "liquidity_row_alignment_receipt"
    ]
    assert alignment["status"] == "NO_UNIQUE_EXACT_ALIGNMENT"
    liability = next(
        item for item in alignment["effective_rows"] if item["role"] == "LIABILITY_TOTAL"
    )
    assert liability["effective_values_exact"][0] == "40"
    assert not any(item["role"].startswith("OVERDUE:") for item in candidate["mappings"])
    assert [
        (item["currency_role"], item["equation_status"])
        for item in candidate["closure_receipt"]["nonclosing_currency_frontiers"]
    ] == [("OVERDUE", "MISMATCH")]


def test_ambiguous_equal_span_alignment_preserves_raw_rows_and_maps_only_exact_columns() -> None:
    table = _table()
    table["rows"][0]["values_exact"] = [None, None, "0", *(["0"] * 6)]
    table["rows"][1]["values_exact"] = ["0", None, "0", *(["0"] * 6)]
    table["rows"][2]["values_exact"] = ["0"] * 9
    _compiled_specs, _cluster, candidate = _evaluate([_record(_page(table))])
    assert candidate["status"] == READY
    alignment = candidate["closure_receipt"]["table_receipts"][0]["classification"][
        "liquidity_row_alignment_receipt"
    ]
    assert alignment["status"] == "NO_UNIQUE_EXACT_ALIGNMENT"
    assert len(alignment["candidate_offset_axes"]) == 2
    assert all(
        row["effective_values_exact"] == row["raw_values_exact"]
        for row in alignment["effective_rows"]
    )
    assert not any(item["role"].startswith("OVERDUE_GT3M:") for item in candidate["mappings"])
    assert [
        item["currency_role"]
        for item in candidate["closure_receipt"]["nonclosing_currency_frontiers"]
    ] == ["OVERDUE_GT3M"]


def test_unique_internal_blank_shift_preserves_anchored_first_and_total_cells() -> None:
    table = _table()
    table["rows"][0]["values_exact"] = ["10", "5", *(["100"] * 6), "615"]
    table["rows"][1]["values_exact"] = ["4", *(["40"] * 6), None, "244"]
    table["rows"][2]["values_exact"] = ["6", "5", *(["60"] * 6), "371"]
    _compiled_specs, _cluster, candidate = _evaluate([_record(_page(table))])
    assert candidate["status"] == READY
    alignment = candidate["closure_receipt"]["table_receipts"][0]["classification"][
        "liquidity_row_alignment_receipt"
    ]
    liability = next(
        item for item in alignment["effective_rows"] if item["role"] == "LIABILITY_TOTAL"
    )
    assert liability["source_offset"] == 1
    assert liability["source_span_column_ids"] == ["c2", "c8"]
    assert liability["effective_values_exact"] == [
        "4",
        None,
        *(["40"] * 6),
        "244",
    ]


def test_selected_json_candidate_replay_rejects_coherent_receipt_drift() -> None:
    record = _record(_page(_table()))
    compiled, cluster, candidate = _evaluate([record])
    forged = copy.deepcopy(candidate)
    forged["closure_receipt"]["table_receipts"][0]["classification"]["component_axis"][0][
        "label_exact"
    ] = "Tổng tài sản giả"
    with pytest.raises(
        GeminiJsonEquityMatrixAccountingFamilyV1Error,
        match="does not replay",
    ):
        validate_gemini_json_equity_matrix_family_candidate_replay_v1(
            forged,
            regions=cluster["component_regions"],
            page_json_by_version={record["page_json_version_id"]: record["page_json"]},
            compiled_specs=compiled,
            query_receipt=build_gemini_json_equity_matrix_region_query_receipt_v1(
                cluster["component_regions"], owner_receipt=cluster["owner_receipt"]
            ),
            document_unit_context_evidence=cluster["document_unit_context_evidence"],
        )


def test_selected_json_candidate_replay_rejects_mapping_axis_deletion_with_rehash() -> None:
    record = _record(_page(_table()))
    compiled, cluster, candidate = _evaluate([record])
    forged = copy.deepcopy(candidate)
    forged["mappings"] = forged["mappings"][:-1]
    forged["candidate_id"] = "gjeqmfv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in forged.items() if key != "candidate_id"}
    )
    with pytest.raises(
        GeminiJsonEquityMatrixAccountingFamilyV1Error,
        match="does not replay",
    ):
        validate_gemini_json_equity_matrix_family_candidate_replay_v1(
            forged,
            regions=cluster["component_regions"],
            page_json_by_version={record["page_json_version_id"]: record["page_json"]},
            compiled_specs=compiled,
            query_receipt=build_gemini_json_equity_matrix_region_query_receipt_v1(
                cluster["component_regions"], owner_receipt=cluster["owner_receipt"]
            ),
            document_unit_context_evidence=cluster["document_unit_context_evidence"],
        )
