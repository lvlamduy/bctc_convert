from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_categorical_period_matrix_v1 import (
    CANONICAL_RATE_UNIT,
    _decimal_hundredths,
)
from bctc_ai.evaluation.gemini_json_equity_matrix_accounting_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    build_gemini_json_equity_matrix_region_query_receipt_v1,
    classify_gemini_json_equity_matrix_table_v1,
    coalesce_gemini_json_equity_matrix_document_v1,
    compile_gemini_json_equity_matrix_family_specs_v1,
    evaluate_gemini_json_equity_matrix_family_cluster_v1,
    validate_gemini_json_equity_matrix_family_candidate_replay_v1,
)

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "a" * 64
SOURCE_SHA256 = "b" * 64


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict:
    return compile_gemini_json_equity_matrix_family_specs_v1(
        _json("tm-exchange-rate-topology-v1.json"),
        _json("tm-exchange-rate-evaluation-v1.json"),
        _json("tm-exchange-rate-schema-binding-v1.json"),
    )


def _column(label: str, *, kind: str = "MONEY") -> dict:
    return {"header_path_exact": [label], "value_kind": kind}


def _row(label: str, current: str, comparative: str) -> dict:
    return {
        "hierarchy_path_exact": [label],
        "label_exact": label,
        "row_kind": "ITEM",
        "values_exact": [current, comparative],
    }


def _table() -> dict:
    return {
        "columns": [_column("31/12/2025 VND"), _column("31/12/2024 VND")],
        "continuation": "NONE",
        "rows": [
            _row("USD", "26.300,00", "25.450"),
            _row("EUR", "30.945,50", "26.715"),
            _row("GBP", "35.443", "32.025"),
            _row("JPY", "168,88", "163,92"),
            _row("CHF", "33.195", "28.340,50"),
            _row("AUD", "17.641", "15.915,50"),
            _row("CAD", "19.250,50", "17.841,50"),
            _row("SGD", "20.505,50", "18.808"),
            _row("THB", "841,86", "752,87"),
            _row("SEK", "2.775", "2.318"),
            _row("DKK", "3.951", "4.150"),
            _row("XAU (*)", "1.535.500", "832.000"),
        ],
        "title_exact": None,
        "unit_exact": "VND",
    }


def _page(
    table: dict | None,
    *,
    title: str | None = "49. Tỷ giá một số loại ngoại tệ so với VND tại thời điểm cuối kỳ",
    narratives: list[str] | None = None,
) -> dict:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": narratives or [],
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
        "source_logical_name": "exchange-rate-fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }


def _evaluate(table: dict) -> tuple[dict, dict, dict]:
    compiled = _compiled()
    record = _record(_page(table))
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[record], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    query = build_gemini_json_equity_matrix_region_query_receipt_v1(
        cluster["component_regions"], owner_receipt=cluster["owner_receipt"]
    )
    candidate = evaluate_gemini_json_equity_matrix_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={record["page_json_version_id"]: record["page_json"]},
        compiled_specs=compiled,
        query_receipt=query,
        document_unit_context_evidence=cluster["document_unit_context_evidence"],
    )
    return compiled, cluster, candidate


def test_exact_category_period_matrix_maps_locally_without_prompt_logic() -> None:
    compiled, cluster, candidate = _evaluate(_table())
    assert compiled["exchange_rate_mode"] is True
    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 11  # structural root + ten schema currencies
    assert sum(len(item["values"]) for item in candidate["mappings"]) == 20
    assert all(
        item["unit"] == CANONICAL_RATE_UNIT for item in candidate["mappings"] if item["values"]
    )
    usd = next(item for item in candidate["mappings"] if item["role"] == "USD")
    assert [value["coefficient"] for value in usd["values"]] == [2630000, 2545000]
    assert [value["period_role"] for value in usd["values"]] == [
        "CURRENT_PERIOD",
        "COMPARATIVE_PERIOD",
    ]
    assert [item["role"] for item in candidate["closure_receipt"]["source_only_category_axis"]] == [
        "SOURCE_DKK",
        "SOURCE_XAU",
    ]
    assert cluster["owner_receipt"]["rate_denominator_receipt"]["source"] == (
        "EXPLICIT_OWNER_RATE_DENOMINATOR_VND"
    )


@pytest.mark.parametrize(
    ("source", "coefficient", "normalized"),
    [
        ("26.300,00", 2630000, "26300.00"),
        ("26.300", 2630000, "26300.00"),
        ("26,300", 2630000, "26300.00"),
        ("162,59", 16259, "162.59"),
        ("162.5", 16250, "162.50"),
        ("1.535.500", 153550000, "1535500.00"),
    ],
)
def test_decimal_separator_variants_canonicalize_locally(
    source: str, coefficient: int, normalized: str
) -> None:
    assert _decimal_hundredths(source) == (
        coefficient,
        normalized,
        "RAW_RATE_DECIMAL_SCALED_HUNDREDTHS",
    )


@pytest.mark.parametrize("source", [None, "-", "(26.300)", "26.30.0", "abc"])
def test_invalid_rate_tokens_fail_closed(source: str | None) -> None:
    coefficient, _normalized, state = _decimal_hundredths(source)
    assert coefficient is None
    assert state.startswith("INVALID")


def test_count_and_unknown_value_kind_are_contextually_numeric() -> None:
    for kind in ("COUNT", "UNKNOWN"):
        table = _table()
        for column in table["columns"]:
            column["value_kind"] = kind
        _compiled_specs, _cluster, candidate = _evaluate(table)
        assert candidate["status"] == READY


@pytest.mark.parametrize(
    ("source_label", "role"),
    [
        ("Đô la Mỹ", "USD"),
        ("Euro", "EUR"),
        ("British Pound", "GBP"),
        ("Yên Nhật", "JPY"),
        ("Swiss Franc", "CHF"),
        ("Australian Dollar", "AUD"),
        ("Đô la Canada", "CAD"),
        ("Singapore Dollar", "SGD"),
        ("Baht Thái", "THB"),
        ("Swedish Krona", "SEK"),
    ],
)
def test_declared_currency_name_variants_map_without_prompt_changes(
    source_label: str, role: str
) -> None:
    table = _table()
    row = next(item for item in table["rows"] if item["label_exact"] == role)
    row["label_exact"] = source_label
    row["hierarchy_path_exact"] = [source_label]
    _compiled_specs, _cluster, candidate = _evaluate(table)
    assert candidate["status"] == READY
    assert any(item["role"] == role for item in candidate["mappings"])


def test_explicit_vnd_owner_ignores_incidental_amount_scale_metadata() -> None:
    table = _table()
    table["unit_exact"] = "Triệu đồng"
    for column in table["columns"]:
        column["header_path_exact"].append("Triệu đồng")
    _compiled_specs, cluster, candidate = _evaluate(table)
    assert candidate["status"] == READY
    receipt = cluster["owner_receipt"]["rate_denominator_receipt"]
    assert receipt["canonical_rate_unit"] == CANONICAL_RATE_UNIT
    assert receipt["incidental_amount_scale_evidence"]


def test_implicit_rate_denominator_requires_typed_document_currency_evidence() -> None:
    table = _table()
    table["unit_exact"] = None
    table["columns"] = [_column("31/12/2025"), _column("31/12/2024")]
    page = _page(table, title="Tỷ giá một số loại ngoại tệ")
    absent = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert absent["status"] == UNRESOLVED
    assert "RATE_DENOMINATOR_VND_NOT_SOURCE_AUTHENTICATED" in absent["reasons"]

    page["sections"].insert(
        0,
        {
            "content_kind": "PRIMARY_STATEMENT",
            "narratives_exact": [],
            "statement_type": "BALANCE_SHEET",
            "tables": [
                {
                    "columns": [_column("Tài sản")],
                    "continuation": "NONE",
                    "rows": [
                        {
                            "hierarchy_path_exact": ["Tổng tài sản"],
                            "label_exact": "Tổng tài sản",
                            "row_kind": "TOTAL",
                            "values_exact": ["1"],
                        }
                    ],
                    "title_exact": "Bảng cân đối kế toán",
                    "unit_exact": "Đơn vị: Triệu VND",
                }
            ],
            "title_exact": "Báo cáo tình hình tài chính",
        },
    )
    ready = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert ready["status"] == READY
    denominator = ready["owner_receipt"]["rate_denominator_receipt"]
    assert denominator["source"] == "TYPED_DOCUMENT_REPORTING_CURRENCY_VND"
    assert (
        denominator["document_reporting_currency_receipt"]["status"]
        == "UNIQUE_VND_REPORTING_CURRENCY"
    )


def test_conflicting_document_currency_cannot_authorize_implicit_rate_denominator() -> None:
    table = _table()
    table["unit_exact"] = None
    table["columns"] = [_column("31/12/2025"), _column("31/12/2024")]
    page = _page(table, title="Tỷ giá một số loại ngoại tệ")
    page["sections"].insert(
        0,
        {
            "content_kind": "PRIMARY_STATEMENT",
            "narratives_exact": [],
            "statement_type": "BALANCE_SHEET",
            "tables": [
                {
                    "columns": [_column("USD")],
                    "continuation": "NONE",
                    "rows": [
                        {
                            "hierarchy_path_exact": ["Tổng tài sản"],
                            "label_exact": "Tổng tài sản",
                            "row_kind": "TOTAL",
                            "values_exact": ["1"],
                        }
                    ],
                    "title_exact": "Bảng cân đối kế toán",
                    "unit_exact": "Đơn vị: Triệu VND",
                }
            ],
            "title_exact": "Báo cáo tình hình tài chính",
        },
    )
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    denominator = cluster["owner_receipt"]["rate_denominator_receipt"]
    assert denominator["document_reporting_currency_receipt"]["status"] == (
        "CONFLICTING_DOCUMENT_REPORTING_CURRENCY"
    )


def test_relative_beginning_ending_headers_bind_from_document_period_context() -> None:
    table = _table()
    table["columns"] = [_column("Số cuối kỳ VND"), _column("Số đầu kỳ VND")]
    page = _page(table)
    page["sections"].insert(
        0,
        {
            "content_kind": "PRIMARY_STATEMENT",
            "narratives_exact": [],
            "statement_type": "BALANCE_SHEET",
            "tables": [],
            "title_exact": "Báo cáo tình hình tài chính tại ngày 30 tháng 6 năm 2025",
        },
    )
    record = _record(page)
    compiled = _compiled()
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[record], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    assert [
        (item["period_role"], item["period_date"], item["source"])
        for item in cluster["owner_receipt"]["period_assignments"]
    ] == [
        ("CURRENT_PERIOD", "2025-06-30", "TYPED_DOCUMENT_REPORTING_DATE_AXIS"),
        (
            "COMPARATIVE_PERIOD",
            "2024-12-31",
            "VISIBLE_BEGINNING_PERIOD_CALENDAR_YEAR_BOUNDARY",
        ),
    ]


def test_relative_period_headers_do_not_invent_a_nonstandard_year_boundary() -> None:
    table = _table()
    table["columns"] = [_column("Số cuối kỳ VND"), _column("Số đầu kỳ VND")]
    page = _page(table)
    page["sections"].insert(
        0,
        {
            "content_kind": "PRIMARY_STATEMENT",
            "narratives_exact": [],
            "statement_type": "BALANCE_SHEET",
            "tables": [],
            "title_exact": "Báo cáo tình hình tài chính tại ngày 15 tháng 5 năm 2025",
        },
    )
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert "EXCHANGE_RATE_PERIOD_ASSIGNMENT_UNRESOLVED" in cluster["reasons"]


def test_relative_period_headers_reject_conflicting_typed_document_date_pairs() -> None:
    table = _table()
    table["columns"] = [_column("Số cuối kỳ VND"), _column("Số đầu kỳ VND")]

    def balance_table(comparative: str) -> dict:
        return {
            "columns": [_column("31/12/2025"), _column(comparative)],
            "continuation": "NONE",
            "rows": [
                {
                    "hierarchy_path_exact": ["Tổng tài sản"],
                    "label_exact": "Tổng tài sản",
                    "row_kind": "TOTAL",
                    "values_exact": ["1", "1"],
                }
            ],
            "title_exact": "Bảng cân đối kế toán",
            "unit_exact": "Triệu VND",
        }

    page = _page(table)
    page["sections"].insert(
        0,
        {
            "content_kind": "PRIMARY_STATEMENT",
            "narratives_exact": [],
            "statement_type": "BALANCE_SHEET",
            "tables": [balance_table("31/12/2024"), balance_table("31/12/2023")],
            "title_exact": "Báo cáo tình hình tài chính tại ngày 31/12/2025",
        },
    )
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert "RELATIVE_PERIOD_REQUIRES_UNIQUE_TYPED_DOCUMENT_DATE_AXIS" in cluster["reasons"]


def test_unavailable_source_only_rate_is_retained_without_blocking_schema_rows() -> None:
    table = _table()
    table["rows"][-1]["values_exact"] = [None, "-"]
    _compiled_specs, _cluster, candidate = _evaluate(table)
    assert candidate["status"] == READY
    xau = candidate["closure_receipt"]["source_only_category_axis"][-1]
    assert xau["role"] == "SOURCE_XAU"
    assert xau["values"] == []
    assert [item["state"] for item in xau["cells"]] == [
        "INVALID_ABSENT_RATE",
        "INVALID_SIGNED_RATE",
    ]


def test_foreign_or_duplicate_category_row_fails_closed() -> None:
    for label in ("Khoản mục ngoại lai", "USD"):
        table = _table()
        table["rows"][-1]["label_exact"] = label
        table["rows"][-1]["hierarchy_path_exact"] = [label]
        cluster = coalesce_gemini_json_equity_matrix_document_v1(
            page_records=[_record(_page(table))], compiled_specs=_compiled()
        )
        assert cluster["status"] == UNRESOLVED
        assert cluster["component_regions"] == []


def test_multi_date_and_date_semantic_conflicts_fail_closed() -> None:
    for header in (
        "31/12/2025 và 30/06/2025 VND",
        "31/12/2025 Số đầu kỳ VND",
    ):
        table = _table()
        table["columns"][0] = _column(header)
        cluster = coalesce_gemini_json_equity_matrix_document_v1(
            page_records=[_record(_page(table))], compiled_specs=_compiled()
        )
        assert cluster["status"] == UNRESOLVED


def test_sensitivity_table_is_not_mistaken_for_exchange_rate_population() -> None:
    table = {
        "columns": [_column("Mức tăng tỷ giá", kind="PERCENT"), _column("Triệu đồng")],
        "continuation": "NONE",
        "rows": [_row("USD", "2,00%", "61.680"), _row("VND", "3,00%", "2.805.792")],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    record = _record(
        _page(
            table,
            title="Rủi ro tiền tệ",
            narratives=["Độ nhạy đối với tỷ giá"],
        )
    )
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[record], compiled_specs=_compiled()
    )
    assert cluster["status"] == NOT_OBSERVED
    assert cluster["component_regions"] == []


def test_candidate_replay_rejects_coherent_mapping_or_source_drift() -> None:
    compiled, cluster, candidate = _evaluate(_table())
    record = _record(_page(_table()))
    query = build_gemini_json_equity_matrix_region_query_receipt_v1(
        cluster["component_regions"], owner_receipt=cluster["owner_receipt"]
    )
    assert (
        validate_gemini_json_equity_matrix_family_candidate_replay_v1(
            candidate,
            regions=cluster["component_regions"],
            page_json_by_version={record["page_json_version_id"]: record["page_json"]},
            compiled_specs=compiled,
            query_receipt=query,
            document_unit_context_evidence=cluster["document_unit_context_evidence"],
        )
        == candidate
    )
    forged = copy.deepcopy(candidate)
    forged["closure_receipt"]["resolved_rows"][0]["cells"][0]["source_text"] = "99.999"
    forged["candidate_id"] = "gjeqmfv1:candidate:" + "0" * 64
    with pytest.raises(ValueError, match="does not replay"):
        validate_gemini_json_equity_matrix_family_candidate_replay_v1(
            forged,
            regions=cluster["component_regions"],
            page_json_by_version={record["page_json_version_id"]: record["page_json"]},
            compiled_specs=compiled,
            query_receipt=query,
            document_unit_context_evidence=cluster["document_unit_context_evidence"],
        )


def test_table_classifier_inventories_source_only_rows_in_source_order() -> None:
    classification = classify_gemini_json_equity_matrix_table_v1(
        _table(), compiled_specs=_compiled()
    )
    assert classification["status"] == "MATRIX_FRAGMENT"
    assert [
        item["role"]
        for item in classification["component_axis"]
        if item["kind"] == "SOURCE_ONLY_CATEGORY"
    ] == ["SOURCE_DKK", "SOURCE_XAU"]


def test_blank_group_header_is_retained_as_structural_context_not_a_foreign_value_row() -> None:
    table = _table()
    table["rows"].insert(
        0,
        {
            "hierarchy_path_exact": ["Ngoại tệ"],
            "label_exact": "Ngoại tệ",
            "row_kind": "GROUP",
            "values_exact": [None, None],
        },
    )
    _compiled_specs, _cluster, candidate = _evaluate(table)
    assert candidate["status"] == READY
    assert candidate["closure_receipt"]["category_axis"][0]["kind"] == ("STRUCTURAL_CONTEXT_ROW")
    assert len(candidate["mappings"]) == 11
