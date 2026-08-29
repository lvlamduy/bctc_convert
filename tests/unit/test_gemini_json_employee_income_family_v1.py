from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    GeminiJsonMultitableHierarchicalFamilyV1Error,
    _document_duration_month_context_axis,
    _table_duration_month_axis,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
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
OWNER = "Tình hình thu nhập của nhân viên"


def _json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict[str, Any]:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-employee-income-topology-v1.json"),
        _json("tm-employee-income-evaluation-v1.json"),
        _json("tm-employee-income-schema-binding-v1.json"),
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


def _full_rows(
    *,
    monthly_labels: bool = True,
    current_average_income: str = "4.00",
    anonymous_total: bool = False,
) -> list[dict[str, Any]]:
    return [
        _row("Tổng số nhân viên bình quân (người)", "100", "80"),
        _row("Tổng quỹ lương", "3.600", "2.880"),
        _row("Thu nhập khác", "1.200", "960"),
        _row(None if anonymous_total else "Tổng thu nhập", "4.800", "3.840", kind="TOTAL"),
        _row(
            "Tiền lương bình quân tháng" if monthly_labels else "Tiền lương bình quân",
            "3.00" if monthly_labels else "36.00",
            "3.00" if monthly_labels else "36.00",
        ),
        _row(
            "Thu nhập bình quân tháng" if monthly_labels else "Thu nhập bình quân",
            current_average_income if monthly_labels else "48.00",
            "4.00" if monthly_labels else "48.00",
        ),
    ]


def _simple_rows(
    *, count_label: str = "Bình quân số cán bộ, nhân viên (người)"
) -> list[dict[str, Any]]:
    return [
        _row(count_label, "100", "80"),
        _row("Thu nhập của cán bộ, nhân viên", "4.800", "3.840"),
        _row("Thu nhập bình quân/tháng", "4.00", "4.00"),
    ]


def _table(
    rows: list[dict[str, Any]],
    *,
    current_header: str = "Năm 2025",
    comparative_header: str = "Năm 2024",
    unit: str = "Triệu đồng",
    value_kind: str = "MONEY",
) -> dict[str, Any]:
    return {
        "columns": [
            {"header_path_exact": [current_header, unit], "value_kind": value_kind},
            {"header_path_exact": [comparative_header, unit], "value_kind": value_kind},
        ],
        "continuation": "NONE",
        "rows": rows,
        "title_exact": None,
        "unit_exact": unit,
    }


def _page(
    rows: list[dict[str, Any]],
    *,
    current_header: str = "Năm 2025",
    comparative_header: str = "Năm 2024",
    unit: str = "Triệu đồng",
    value_kind: str = "MONEY",
) -> dict[str, Any]:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [
                    _table(
                        rows,
                        current_header=current_header,
                        comparative_header=comparative_header,
                        unit=unit,
                        value_kind=value_kind,
                    )
                ],
                "title_exact": OWNER,
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


def test_config_binds_structural_root_and_eight_employee_roles() -> None:
    compiled = _compiled()
    assert compiled["topology"]["family_id"] == "EMPLOYEE_INCOME"
    assert compiled["accepted_value_column_kinds"] == ["MONEY", "UNKNOWN"]
    assert compiled["schema"]["family_root_report_norm_id"] == 1260
    assert compiled["schema"]["root_mapping_policy"] == "STRUCTURAL_CONTEXT_ONLY"
    assert compiled["bindings"] == {
        "EMPLOYEE_COUNT": 1261,
        "EMPLOYEE_INCOME": 1262,
        "SALARY_FUND": 1263,
        "BONUS": 1264,
        "OTHER_INCOME": 1265,
        "TOTAL_INCOME": 1266,
        "AVERAGE_SALARY_MONTH": 1267,
        "AVERAGE_INCOME_MONTH": 1268,
    }


def test_full_monthly_table_maps_source_visible_ratios_and_structural_root_is_not_emitted() -> None:
    page = _page(_full_rows())
    candidate, cluster, receipt = _evaluate(page)
    assert candidate["status"] == READY
    assert [item["role"] for item in candidate["mappings"]] == [
        "EMPLOYEE_COUNT",
        "SALARY_FUND",
        "OTHER_INCOME",
        "TOTAL_INCOME",
        "AVERAGE_SALARY_MONTH",
        "AVERAGE_INCOME_MONTH",
    ]
    averages = {item["role"]: item for item in candidate["mappings"] if "AVERAGE" in item["role"]}
    assert [cell["normalized_decimal"] for cell in averages["AVERAGE_SALARY_MONTH"]["values"]] == [
        "3.00",
        "3.00",
    ]
    assert averages["AVERAGE_INCOME_MONTH"]["values"][0]["source_text"] == "4.00"
    assert candidate["closure_receipt"]["structural_root_receipt"]["emitted_mapping"] is False
    validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
        candidate,
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=_compiled(),
        query_receipt=receipt,
    )


def test_period_total_average_is_derived_to_monthly_without_changing_source_evidence() -> None:
    candidate, _cluster_value, _receipt = _evaluate(_page(_full_rows(monthly_labels=False)))
    assert candidate["status"] == READY
    averages = {item["role"]: item for item in candidate["mappings"] if "AVERAGE" in item["role"]}
    assert [cell["normalized_decimal"] for cell in averages["AVERAGE_SALARY_MONTH"]["values"]] == [
        "3.00",
        "3.00",
    ]
    assert [cell["normalized_decimal"] for cell in averages["AVERAGE_INCOME_MONTH"]["values"]] == [
        "4.00",
        "4.00",
    ]
    assert all(cell["source_text"] is None for item in averages.values() for cell in item["values"])


def test_simple_direct_income_table_and_opted_in_unknown_value_columns_map() -> None:
    candidate, _cluster_value, _receipt = _evaluate(_page(_simple_rows(), value_kind="UNKNOWN"))
    assert candidate["status"] == READY
    assert [item["role"] for item in candidate["mappings"]] == [
        "EMPLOYEE_COUNT",
        "EMPLOYEE_INCOME",
        "AVERAGE_INCOME_MONTH",
    ]


def test_anonymous_source_total_is_not_required_when_declared_components_prove_it() -> None:
    candidate, _cluster_value, _receipt = _evaluate(_page(_full_rows(anonymous_total=True)))
    assert candidate["status"] == READY
    total = next(item for item in candidate["mappings"] if item["role"] == "TOTAL_INCOME")
    assert [cell["coefficient"] for cell in total["values"]] == [4800, 3840]


def test_visible_ratio_one_cent_from_nominal_is_accepted_only_by_propagated_display_interval() -> (
    None
):
    rows = [
        _row("Bình quân số cán bộ, nhân viên (người)", "100", "100"),
        _row("Thu nhập của cán bộ, nhân viên", "22.872", "22.800"),
        _row("Thu nhập bình quân tháng", "38.13", "38.00"),
    ]
    candidate, _cluster_value, _receipt = _evaluate(
        _page(rows, current_header="6 tháng năm 2025", comparative_header="6 tháng năm 2024")
    )
    assert candidate["status"] == READY
    equation = next(
        item
        for item in candidate["closure_receipt"]["equations"]
        if item.get("result_role") == "AVERAGE_INCOME_MONTH"
    )
    assert equation["visible_computed_decimals"] == ["38.12", "38.00"]
    assert equation["comparison_rules"][0] == (
        "EXACT_PROPAGATED_HALF_UNIT_SOURCE_DISPLAY_ROUNDING_INTERVAL"
    )
    assert equation["visible_rounding_intervals"][0]["source_ratio_interval_rule"] == (
        "WHOLE_UNIT_NUMERATOR_AND_DENOMINATOR_HALF_OPEN_BOUNDS"
    )


def test_only_typed_governed_primary_statement_titles_supply_document_duration() -> None:
    def primary(title: str, statement_type: str = "INCOME_STATEMENT") -> dict[str, Any]:
        return {
            "sections": [
                {
                    "content_kind": "PRIMARY_STATEMENT",
                    "narratives_exact": [],
                    "statement_type": statement_type,
                    "tables": [],
                    "title_exact": title,
                }
            ],
            "status": "PRIMARY_FINANCIAL_STATEMENT",
        }

    six_month = _document_duration_month_context_axis(
        {
            "gfpstorev1:json:" + "1" * 64: primary(
                "Báo cáo kết quả hoạt động cho kỳ 6 tháng kết thúc ngày 30 tháng 6 năm 2025"
            )
        }
    )
    assert (six_month["status"], six_month["months"]) == ("UNIQUE", 6)
    annual = _document_duration_month_context_axis(
        {
            "gfpstorev1:json:" + "2" * 64: primary(
                "Báo cáo kết quả hoạt động cho năm tài chính kết thúc ngày 31 tháng 12 năm 2025"
            )
        }
    )
    assert (annual["status"], annual["months"]) == ("UNIQUE", 12)
    unrelated = _document_duration_month_context_axis(
        {
            "gfpstorev1:json:" + "3" * 64: {
                "sections": [
                    {
                        "content_kind": "FINANCIAL_NOTE",
                        "narratives_exact": [
                            "Khoản vay có kỳ hạn 6 tháng kết thúc ngày 30 tháng 6 năm 2025"
                        ],
                        "statement_type": "NOT_APPLICABLE",
                        "tables": [],
                        "title_exact": "Các khoản vay",
                    }
                ],
                "status": "FINANCIAL_NOTE_CONTENT",
            }
        }
    )
    assert (unrelated["status"], unrelated["months"]) == ("ABSENT", None)
    conflict = _document_duration_month_context_axis(
        {
            "gfpstorev1:json:" + "4" * 64: primary(
                "Báo cáo kết quả hoạt động cho kỳ 3 tháng kết thúc ngày 31 tháng 3 năm 2025"
            ),
            "gfpstorev1:json:" + "5" * 64: primary(
                "Báo cáo lưu chuyển tiền tệ cho kỳ 6 tháng kết thúc ngày 30 tháng 6 năm 2025",
                "CASH_FLOW",
            ),
        }
    )
    assert (conflict["status"], conflict["months"]) == ("NOT_UNIQUE", None)


def test_typed_interim_context_overrides_a_local_bare_year_without_overriding_explicit_year() -> (
    None
):
    table = _table(_simple_rows(), current_header="2025", comparative_header="2024")
    lane_axis = {"complete": True, "money_column_ordinals": [1, 2]}
    interim = _table_duration_month_axis(
        table,
        lane_axis,
        document_context={"months": 6, "status": "UNIQUE"},
    )
    assert interim["complete"] is True
    assert interim["months"] == [6, 6]
    assert {item["source_kind"] for item in interim["evidence"]} == {
        "TYPED_DOCUMENT_DURATION_CONTEXT"
    }
    annual = _table_duration_month_axis(table, lane_axis, document_context={"status": "ABSENT"})
    assert annual["complete"] is True
    assert annual["months"] == [12, 12]
    symbolic = _table(_simple_rows(), current_header="Năm nay", comparative_header="Năm trước")
    symbolic_interim = _table_duration_month_axis(
        symbolic,
        lane_axis,
        document_context={"months": 6, "status": "UNIQUE"},
    )
    assert symbolic_interim["months"] == [6, 6]


@pytest.mark.parametrize(
    "rows",
    [
        _simple_rows(count_label="Tổng số nhân viên tại ngày 31 tháng 12 năm 2025"),
        [*_simple_rows(), _row("Thu nhập của nhân viên", "1", "1")],
        _full_rows(current_average_income="4.50"),
    ],
)
def test_missing_average_count_duplicate_role_or_ratio_mismatch_is_unresolved(
    rows: list[dict[str, Any]],
) -> None:
    candidate, _cluster_value, _receipt = _evaluate(_page(rows))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


@pytest.mark.parametrize(
    ("current_header", "comparative_header", "unit"),
    [
        ("6 tháng năm 2025", "12 tháng năm 2024", "Triệu đồng"),
        ("Quý 1 năm 2025", "Quý 1 năm 2024", "Triệu đồng"),
        ("Năm 2025", "Năm 2024", "Triệu đồng; Nghìn đồng"),
    ],
)
def test_duration_or_unit_conflict_is_unresolved(
    current_header: str, comparative_header: str, unit: str
) -> None:
    candidate, _cluster_value, _receipt = _evaluate(
        _page(
            _full_rows(),
            current_header=current_header,
            comparative_header=comparative_header,
            unit=unit,
        )
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_candidate_replay_rejects_coherently_rehashed_decimal_mapping_tamper() -> None:
    page = _page(_full_rows())
    candidate, cluster, receipt = _evaluate(page)
    tampered = deepcopy(candidate)
    mapping = next(item for item in tampered["mappings"] if item["role"] == "AVERAGE_INCOME_MONTH")
    mapping["values"][0]["coefficient"] = 999
    mapping["values"][0]["normalized_decimal"] = "9.99"
    material = {key: value for key, value in mapping.items() if key != "item_mapping_id"}
    mapping["item_mapping_id"] = "gjmthfmv1:item:" + canonical_json_sha256_v1(material)
    candidate_material = {key: value for key, value in tampered.items() if key != "candidate_id"}
    tampered["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(candidate_material)
    with pytest.raises(
        GeminiJsonMultitableHierarchicalFamilyV1Error,
        match="candidate replay drifted",
    ):
        validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
            tampered,
            regions=cluster["component_regions"],
            page_json_by_version={VERSION_ID: page},
            compiled_specs=_compiled(),
            query_receipt=receipt,
        )
