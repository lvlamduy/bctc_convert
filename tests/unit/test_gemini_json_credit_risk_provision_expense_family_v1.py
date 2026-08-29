from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
    validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1,
)

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "a" * 64
VERSION_ID = "gfpstorev1:json:" + "b" * 64
SOURCE_SHA256 = "c" * 64
OWNER = "Chi phí dự phòng rủi ro tín dụng"


def _json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict[str, Any]:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-credit-risk-provision-expense-topology-v1.json"),
        _json("tm-credit-risk-provision-expense-evaluation-v1.json"),
        _json("tm-credit-risk-provision-expense-schema-binding-v1.json"),
    )


def _row(
    label: str | None,
    current: str | None,
    comparative: str | None,
    *,
    kind: str = "ITEM",
    path: list[str | None] | None = None,
) -> dict[str, Any]:
    return {
        "hierarchy_path_exact": (
            [value for value in path if value is not None]
            if path is not None
            else ([label] if label is not None else [])
        ),
        "label_exact": label,
        "row_kind": kind,
        "values_exact": [current, comparative],
    }


def _base_rows() -> list[dict[str, Any]]:
    customer = "Chi phí/(Hoàn nhập) dự phòng rủi ro cho vay khách hàng"
    return [
        _row(customer, "100", "80", kind="GROUP"),
        _row(
            "Trích lập dự phòng chung",
            "20",
            "15",
            path=[customer, "Trích lập dự phòng chung"],
        ),
        _row(
            "Trích lập dự phòng cụ thể",
            "80",
            "65",
            path=[customer, "Trích lập dự phòng cụ thể"],
        ),
        _row("Chi phí/(Hoàn nhập) dự phòng mua nợ", "5", "4"),
        _row("Hoàn nhập dự phòng rủi ro cho các cam kết ngoại bảng", "(2)", "(1)"),
        _row("Dự phòng khác", "3", "2"),
        _row(None, "106", "85", kind="TOTAL", path=[None]),
    ]


def _page(rows: list[dict[str, Any]]) -> dict[str, Any]:
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
                                "header_path_exact": ["Năm 2026", "Triệu đồng"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": ["Năm 2025", "Triệu đồng"],
                                "value_kind": "MONEY",
                            },
                        ],
                        "continuation": "NONE",
                        "rows": rows,
                        "title_exact": None,
                        "unit_exact": "Triệu đồng",
                    }
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
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        cluster["component_regions"]
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=_compiled(),
        query_receipt=receipt,
    )
    return candidate, cluster, receipt


def test_credit_risk_provision_config_binds_exact_schema_axis() -> None:
    compiled = _compiled()
    assert compiled["topology"]["family_id"] == "CREDIT_RISK_PROVISION_EXPENSE"
    assert compiled["schema"]["family_root_report_norm_id"] == 1221
    assert set(compiled["bindings"].values()) == {
        1222,
        1223,
        1224,
        1225,
        1226,
        1227,
        1228,
        6031,
        6032,
        6033,
    }


def test_nested_customer_and_direct_components_close_and_replay() -> None:
    page = _page(_base_rows())
    candidate, cluster, receipt = _evaluate(page)
    assert candidate["status"] == READY
    assert {mapping["report_norm_id"] for mapping in candidate["mappings"]} == {
        1221,
        1224,
        1225,
        1227,
        1228,
        6031,
        6033,
    }
    validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
        candidate,
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=_compiled(),
        query_receipt=receipt,
    )


def test_unknown_direct_money_row_is_unresolved_with_no_mappings() -> None:
    rows = _base_rows()
    rows.insert(-1, _row("Khoản dự phòng không thuộc schema", "7", "6"))
    rows[-1]["values_exact"] = ["113", "91"]
    candidate, _cluster, _receipt = _evaluate(_page(rows))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_policy_or_statement_aggregate_is_not_a_detailed_note_population() -> None:
    page = _page([_row(OWNER, "106", "85", kind="TOTAL")])
    candidate, _cluster, _receipt = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_ordered_structural_carriers_scope_generic_validation_children() -> None:
    customer = "Biến động dự phòng rủi ro cho vay khách hàng"
    purchased = "Biến động dự phòng các khoản phải thu từ hợp đồng mua nợ"
    other = "Biến động dự phòng các khoản phải thu từ hoạt động tài trợ thương mại"
    rows = [
        _row(customer, "100", "80"),
        _row("- Trích lập/(hoàn nhập) dự phòng chung", "20", "15"),
        _row("- Trích lập dự phòng cụ thể", "80", "65"),
        _row(purchased, "5", "4"),
        _row("- Hoàn nhập dự phòng rủi ro", "5", "4"),
        _row(other, "3", "2"),
        _row("- Trích lập/(hoàn nhập) dự phòng rủi ro", "3", "2"),
        _row(None, "108", "86", kind="TOTAL", path=[None]),
    ]
    candidate, _cluster, _receipt = _evaluate(_page(rows))
    assert candidate["status"] == READY
    source_only = candidate["closure_receipt"]["source_only_unmapped_rows"]
    assert {item.get("declared_validation_role") for item in source_only} == {
        "OTHER_DETAIL_SOURCE_ONLY",
        "PURCHASED_DEBT_DETAIL_SOURCE_ONLY",
    }
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "CUSTOMER_GENERAL",
        "CUSTOMER_PROVISION",
        "CUSTOMER_SPECIFIC",
        "FAMILY_ROOT_TOTAL",
        "OTHER_PROVISION",
        "PURCHASED_DEBT_PROVISION",
    }


def test_label_only_customer_groups_project_from_exact_children_after_total_closure() -> None:
    general = "Dự phòng chung cho vay khách hàng"
    specific = "Dự phòng cụ thể cho vay khách hàng"
    rows = [
        _row(general, None, None, kind="GROUP"),
        _row(
            "Trích lập dự phòng",
            "20",
            "15",
            path=[general, "Trích lập dự phòng"],
        ),
        _row(specific, None, None, kind="GROUP"),
        _row(
            "(Hoàn nhập)/Trích lập dự phòng",
            "80",
            "65",
            path=[specific, "(Hoàn nhập)/Trích lập dự phòng"],
        ),
        _row("Chi phí dự phòng trái phiếu VAMC", "5", "4"),
        _row(None, "105", "84", kind="TOTAL", path=[None]),
    ]
    candidate, _cluster, _receipt = _evaluate(_page(rows))
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [value["coefficient"] for value in by_role["CUSTOMER_GENERAL"]["values"]] == [
        20,
        15,
    ]
    assert [value["coefficient"] for value in by_role["CUSTOMER_SPECIFIC"]["values"]] == [
        80,
        65,
    ]
    assert [value["coefficient"] for value in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [
        105,
        84,
    ]


def test_unscoped_generic_detail_row_remains_unresolved() -> None:
    rows = [
        _row("- Hoàn nhập dự phòng rủi ro", "1", "1"),
        *_base_rows(),
    ]
    rows[-1]["values_exact"] = ["107", "86"]
    candidate, _cluster, _receipt = _evaluate(_page(rows))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
