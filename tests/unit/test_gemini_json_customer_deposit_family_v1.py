from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_customer_deposit_family_v1 import (
    READY,
    UNRESOLVED,
    GeminiJsonCustomerDepositFamilyV1Error,
    build_gemini_json_customer_deposit_region_query_receipt_v1,
    coalesce_gemini_json_customer_deposit_document_v1,
    compile_gemini_json_customer_deposit_family_specs_v1,
    evaluate_gemini_json_customer_deposit_family_cluster_v1,
    validate_gemini_json_customer_deposit_family_candidate_replay_v1,
)

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
            _row(None, ["40", "36" if mismatch else "35"], "TOTAL", [None]),
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
        "SAVINGS_NO_TERM",
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
    _cluster, candidate = _evaluate(records)
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


def test_reset_between_owner_and_component_blocks_implied_owner() -> None:
    page = _page(_ordinary_type())
    page["sections"][0]["narratives_exact"] = ["Giao dịch với các bên liên quan"]
    cluster = coalesce_gemini_json_customer_deposit_document_v1(
        page_records=[_record(page, 1)], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert "IMPLIED_OWNER_BLOCKED_BY_RESET_OR_HARD_NEGATIVE" in cluster["reasons"]


def test_optional_customer_view_is_included_only_after_exact_closure() -> None:
    _cluster, exact = _evaluate([_record(_page(_ordinary_type(), _customer()), 1)])
    _cluster, mismatch = _evaluate([_record(_page(_ordinary_type(), _customer(mismatch=True)), 1)])
    assert exact["status"] == READY
    assert exact["closure_receipt"]["customer_view"]["disposition"] == (
        "INCLUDED_EXACT_OPTIONAL_CUSTOMER_VIEW"
    )
    assert {"STATE_COMPANY", "HOUSEHOLD_INDIVIDUAL"} <= {item["role"] for item in exact["mappings"]}
    assert mismatch["status"] == READY
    assert mismatch["closure_receipt"]["customer_view"]["disposition"] == (
        "EXCLUDED_NONEXACT_OPTIONAL_CUSTOMER_VIEW"
    )
    assert (
        "CUSTOMER_ROOT_TOTAL_EQUATION_MISMATCH"
        in mismatch["closure_receipt"]["customer_view"]["rejection_reasons"]
    )
    assert not {"STATE_COMPANY", "HOUSEHOLD_INDIVIDUAL"} & {
        item["role"] for item in mismatch["mappings"]
    }


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
