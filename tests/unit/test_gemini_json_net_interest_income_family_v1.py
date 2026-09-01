from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    NOT_OBSERVED,
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


def _json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict[str, Any]:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-net-interest-income-topology-v1.json"),
        _json("tm-net-interest-income-evaluation-v1.json"),
        _json("tm-net-interest-income-schema-binding-v1.json"),
    )


def _row(label: str, values: list[str | None], *, kind: str = "ITEM") -> dict[str, Any]:
    return {
        "hierarchy_path_exact": [label],
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _page(*, statement_type: str = "INCOME_STATEMENT") -> dict[str, Any]:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "PRIMARY_FINANCIAL_STATEMENT",
                "narratives_exact": [],
                "statement_type": statement_type,
                "tables": [
                    {
                        "columns": [
                            {
                                "header_path_exact": ["Năm 2025", "Triệu VND"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": ["Năm 2024", "Triệu VND"],
                                "value_kind": "MONEY",
                            },
                        ],
                        "continuation": "NONE",
                        "rows": [
                            _row(
                                "Thu nhập lãi và các khoản thu nhập tương tự",
                                ["100", "80"],
                            ),
                            _row(
                                "Chi phí lãi và các chi phí tương tự",
                                ["(40)", "(30)"],
                            ),
                            _row("Thu nhập lãi thuần", ["60", "50"], kind="SUBTOTAL"),
                        ],
                        "title_exact": None,
                        "unit_exact": "Triệu VND",
                    }
                ],
                "title_exact": "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG HỢP NHẤT NĂM 2025",
            }
        ],
        "status": "PRIMARY_FINANCIAL_STATEMENT",
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


def _evaluate(page: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    compiled = _compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    regions = cluster["component_regions"]
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=regions,
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    return candidate, regions, receipt


def test_visible_net_interest_row_maps_directly_to_report_norm_5985() -> None:
    candidate, _regions, _receipt = _evaluate(_page())

    assert candidate["status"] == READY
    assert len(candidate["mappings"]) == 1
    mapping = candidate["mappings"][0]
    assert mapping["report_norm_id"] == 5985
    assert mapping["role"] == "FAMILY_ROOT_TOTAL"
    assert [cell["coefficient"] for cell in mapping["values"]] == [60, 50]
    assert {item["report_norm_id"] for item in candidate["mappings"]}.isdisjoint({1143, 1151})


def test_interest_components_are_only_an_equation_veto() -> None:
    page = _page()
    page["sections"][0]["tables"][0]["rows"][-1]["values_exact"][0] = "61"

    candidate, _regions, _receipt = _evaluate(page)

    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert any(
        reason.startswith("SOURCE_RESULT_DECLARED_COMPONENT_") for reason in candidate["reasons"]
    )


def test_exact_source_row_maps_without_deriving_from_components() -> None:
    page = _page()
    page["sections"][0]["tables"][0]["rows"] = [
        _row("Thu nhập từ lãi thuần", ["60", "50"], kind="ITEM")
    ]

    candidate, _regions, _receipt = _evaluate(page)

    assert candidate["status"] == READY
    assert [cell["coefficient"] for cell in candidate["mappings"][0]["values"]] == [60, 50]
    assert (
        candidate["mappings"][0]["state"]
        == "SOURCE_VISIBLE_EXACT_RESULT_ROW_WITHOUT_COMPONENT_EVIDENCE"
    )


def test_components_without_visible_net_row_are_not_backsolved() -> None:
    page = _page()
    page["sections"][0]["tables"][0]["rows"] = page["sections"][0]["tables"][0]["rows"][:2]
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )

    assert cluster["status"] == NOT_OBSERVED
    assert cluster["component_regions"] == []


def test_same_text_in_cash_flow_is_not_treated_as_net_interest_result() -> None:
    page = _page(statement_type="CASH_FLOW")
    page["sections"][0]["tables"][0]["rows"] = [
        _row("Thu nhập lãi thuần", ["60", "50"], kind="ITEM")
    ]
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )

    assert cluster["status"] == NOT_OBSERVED
    assert cluster["component_regions"] == []


def test_candidate_replay_rejects_a_rehashed_value_change() -> None:
    candidate, regions, receipt = _evaluate(_page())
    forged = copy.deepcopy(candidate)
    forged["mappings"][0]["values"][0]["coefficient"] = 999

    try:
        validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
            forged,
            regions=regions,
            page_json_by_version={VERSION_ID: _page()},
            compiled_specs=_compiled(),
            query_receipt=receipt,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("forged net-interest mapping was accepted")


def test_cumulative_from_period_start_headers_do_not_claim_comparative_semantics() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["columns"] = [
        {"header_path_exact": ["Quý 3/2025", "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": ["Quý 3/2024", "Triệu đồng"], "value_kind": "MONEY"},
        {
            "header_path_exact": ["Lũy kế từ đầu kỳ đến", "30/09/2025", "Triệu đồng"],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": ["Lũy kế từ đầu kỳ đến", "30/09/2024", "Triệu đồng"],
            "value_kind": "MONEY",
        },
    ]
    table["rows"] = [
        _row("Thu nhập lãi và các khoản thu nhập tương tự", ["30", "25", "100", "80"]),
        _row("Chi phí lãi và các chi phí tương tự", ["(12)", "(10)", "(40)", "(30)"]),
        _row("Thu nhập lãi thuần", ["18", "15", "60", "50"], kind="SUBTOTAL"),
    ]

    candidate, _regions, _receipt = _evaluate(page)

    assert candidate["status"] == READY
    assert [cell["coefficient"] for cell in candidate["mappings"][0]["values"]] == [60, 50]


def test_positive_expense_presentation_uses_unique_subtractive_orientation() -> None:
    page = _page()
    table = page["sections"][0]["tables"][0]
    table["rows"][1]["values_exact"] = ["40", "30"]

    candidate, _regions, _receipt = _evaluate(page)

    assert candidate["status"] == READY
    assert [cell["coefficient"] for cell in candidate["mappings"][0]["values"]] == [60, 50]


def test_primary_result_outranks_a_repeated_note_presentation() -> None:
    page = _page()
    note = copy.deepcopy(page["sections"][0])
    note["content_kind"] = "FINANCIAL_NOTE"
    note["statement_type"] = "NOT_APPLICABLE"
    note["title_exact"] = "26. Thu nhập lãi thuần"
    page["sections"].append(note)

    compiled = _compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )

    assert cluster["status"] == READY
    assert len(cluster["component_regions"]) == 1
    assert cluster["component_regions"][0]["section_id"] == "s1"
