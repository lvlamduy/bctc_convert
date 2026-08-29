from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    GeminiJsonMultitableHierarchicalFamilyV1Error,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
    validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "a" * 64
SOURCE_SHA256 = "c" * 64
OWNER = "Lãi thuần từ hoạt động khác"


def _json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict[str, Any]:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-other-activity-topology-v1.json"),
        _json("tm-other-activity-evaluation-v1.json"),
        _json("tm-other-activity-schema-binding-v1.json"),
    )


def _row(
    label: str | None,
    current: str | None,
    comparative: str | None,
    *,
    kind: str = "ITEM",
    parent: str | None = None,
) -> dict[str, Any]:
    path = [] if label is None else [label]
    if parent is not None and label is not None:
        path = [parent, label]
    return {
        "hierarchy_path_exact": path,
        "label_exact": label,
        "row_kind": kind,
        "values_exact": [current, comparative],
    }


def _gross_rows() -> list[dict[str, Any]]:
    income = "Thu nhập từ hoạt động khác"
    expense = "Chi phí từ hoạt động khác"
    return [
        _row(income, "100", "80", kind="TOTAL"),
        _row("Thu từ nợ đã xử lý rủi ro", "60", "50", parent=income),
        _row("Thu nhập khác", "40", "30", parent=income),
        _row(expense, "(30)", "(20)", kind="TOTAL"),
        _row("Chi từ các công cụ phái sinh khác", "(10)", "(5)", parent=expense),
        _row("Chi phí khác", "(20)", "(15)", parent=expense),
        _row(OWNER, "70", "60", kind="TOTAL"),
    ]


def _net_only_rows() -> list[dict[str, Any]]:
    return [
        _row("Thu từ nợ đã xử lý rủi ro", "60", "50"),
        _row("Lãi từ các công cụ tài chính phái sinh khác", "10", "8"),
        _row("Thu nhập/(Chi phí) khác", "5", "2"),
        _row(OWNER, "75", "60", kind="TOTAL"),
    ]


def _page(
    rows: list[dict[str, Any]],
    *,
    columns: list[dict[str, Any]] | None = None,
    primary: bool = False,
    unit: str = "Triệu đồng",
) -> dict[str, Any]:
    if columns is None:
        columns = [
            {"header_path_exact": ["Năm 2026", unit], "value_kind": "MONEY"},
            {"header_path_exact": ["Năm 2025", unit], "value_kind": "MONEY"},
        ]
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "PRIMARY_STATEMENT" if primary else "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "INCOME_STATEMENT" if primary else "NOT_APPLICABLE",
                "tables": [
                    {
                        "columns": columns,
                        "continuation": "NONE",
                        "rows": rows,
                        "title_exact": OWNER,
                        "unit_exact": unit,
                    }
                ],
                "title_exact": OWNER,
            }
        ],
        "status": "PRIMARY_FINANCIAL_STATEMENT" if primary else "FINANCIAL_NOTE_CONTENT",
    }


def _record(page: dict[str, Any], *, ordinal: int = 1) -> dict[str, Any]:
    return {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": "gfpstorev1:json:" + str(ordinal) * 64,
        "physical_page": ordinal,
        "selected_page_ordinal": ordinal,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }


def _evaluate(page: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    compiled = _compiled()
    record = _record(page)
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[record], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        cluster["component_regions"]
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={record["page_json_version_id"]: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    return candidate, cluster, receipt


def test_other_activity_config_binds_complete_schema_axis() -> None:
    compiled = _compiled()
    assert compiled["topology"]["family_id"] == "OTHER_ACTIVITY"
    assert compiled["schema"]["family_root_report_norm_id"] == 6029
    assert set(compiled["bindings"].values()) == {
        6030,
        1229,
        1230,
        1231,
        1232,
        1233,
        1234,
        1235,
        1236,
        1237,
        1238,
        1239,
        1240,
        1241,
        1242,
        1243,
        1244,
        1245,
        1246,
    }


def test_context_residual_config_rejects_structural_or_untyped_targets() -> None:
    evaluation = copy.deepcopy(_json("tm-other-activity-evaluation-v1.json"))
    evaluation["context_residual_bindings"][0]["residual_role"] = "EXPENSE_PARENT"
    with pytest.raises(GeminiJsonMultitableHierarchicalFamilyV1Error):
        compile_gemini_json_multitable_hierarchical_family_specs_v1(
            _json("tm-other-activity-topology-v1.json"),
            evaluation,
            _json("tm-other-activity-schema-binding-v1.json"),
        )

    evaluation["context_residual_bindings"] = {"context_role": "INCOME_PARENT"}
    with pytest.raises(GeminiJsonMultitableHierarchicalFamilyV1Error):
        compile_gemini_json_multitable_hierarchical_family_specs_v1(
            _json("tm-other-activity-topology-v1.json"),
            evaluation,
            _json("tm-other-activity-schema-binding-v1.json"),
        )


def test_gross_income_expense_graph_closes_and_replays() -> None:
    page = _page(_gross_rows())
    candidate, cluster, receipt = _evaluate(page)
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "EXPENSE_DERIVATIVE",
        "EXPENSE_OTHER",
        "EXPENSE_PARENT",
        "FAMILY_ROOT_TOTAL",
        "INCOME_DEBT_RECOVERY",
        "INCOME_OTHER",
        "INCOME_PARENT",
    }
    root = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL"
    )
    assert [value["coefficient"] for value in root["values"]] == [70, 60]
    validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
        candidate,
        regions=cluster["component_regions"],
        page_json_by_version={cluster["component_regions"][0]["page_json_version_id"]: page},
        compiled_specs=_compiled(),
        query_receipt=receipt,
    )


def test_net_only_graph_closes_and_replays() -> None:
    page = _page(_net_only_rows())
    candidate, cluster, receipt = _evaluate(page)
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "FAMILY_ROOT_TOTAL",
        "INCOME_DEBT_RECOVERY",
        "INCOME_DERIVATIVE",
        "NET_OTHER",
    }
    validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
        candidate,
        regions=cluster["component_regions"],
        page_json_by_version={cluster["component_regions"][0]["page_json_version_id"]: page},
        compiled_specs=_compiled(),
        query_receipt=receipt,
    )


def test_contract_penalty_is_aggregated_into_schema_catchall_without_document_routing() -> None:
    income = "Thu nhập từ hoạt động khác"
    rows = _gross_rows()
    rows.insert(3, _row("Thu từ phạt vi phạm hợp đồng", "3", "2", parent=income))
    rows[0]["values_exact"] = ["103", "82"]
    rows[-1]["values_exact"] = ["73", "62"]
    candidate, _cluster, _receipt = _evaluate(_page(rows))
    assert candidate["status"] == READY
    catchall = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "INCOME_OTHER"
    )
    assert [value["coefficient"] for value in catchall["values"]] == [43, 32]
    assert len(catchall["source_refs"]) == 2


def test_unknown_direct_context_child_projects_to_declared_schema_residual() -> None:
    rows = _gross_rows()
    rows.insert(
        3,
        _row(
            "Khoản thu hoạt động khác chưa khai báo",
            "1",
            "1",
            parent="Thu nhập từ hoạt động khác",
        ),
    )
    rows[0]["values_exact"] = ["101", "81"]
    rows[-1]["values_exact"] = ["71", "61"]
    candidate, _cluster, _receipt = _evaluate(_page(rows))
    assert candidate["status"] == READY
    catchall = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "INCOME_OTHER"
    )
    assert [value["coefficient"] for value in catchall["values"]] == [41, 31]
    receipts = candidate["closure_receipt"]["table_receipts"][0][
        "context_residual_projection_receipts"
    ]
    assert [(item["context_role"], item["residual_role"]) for item in receipts] == [
        ("INCOME_PARENT", "INCOME_OTHER")
    ]


def test_candidate_replay_rejects_coherently_rehashed_context_residual_drift() -> None:
    rows = _gross_rows()
    rows.insert(
        3,
        _row(
            "Khoản thu hoạt động khác chưa khai báo",
            "1",
            "1",
            parent="Thu nhập từ hoạt động khác",
        ),
    )
    rows[0]["values_exact"] = ["101", "81"]
    rows[-1]["values_exact"] = ["71", "61"]
    page = _page(rows)
    candidate, cluster, receipt = _evaluate(page)
    forged = copy.deepcopy(candidate)
    forged["closure_receipt"]["table_receipts"][0]["context_residual_projection_receipts"][0][
        "residual_role"
    ] = "EXPENSE_OTHER"
    material = {key: value for key, value in forged.items() if key != "candidate_id"}
    forged["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(material)
    with pytest.raises(
        GeminiJsonMultitableHierarchicalFamilyV1Error,
        match="candidate replay drifted",
    ):
        validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
            forged,
            regions=cluster["component_regions"],
            page_json_by_version={cluster["component_regions"][0]["page_json_version_id"]: page},
            compiled_specs=_compiled(),
            query_receipt=receipt,
        )


def test_unknown_expense_context_child_projects_only_to_expense_residual() -> None:
    rows = _gross_rows()
    rows.insert(
        -1,
        _row(
            "Khoản chi hoạt động khác chưa khai báo",
            "(1)",
            "(1)",
            parent="Chi phí từ hoạt động khác",
        ),
    )
    rows[3]["values_exact"] = ["(31)", "(21)"]
    rows[-1]["values_exact"] = ["69", "59"]
    candidate, _cluster, _receipt = _evaluate(_page(rows))
    assert candidate["status"] == READY
    catchall = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "EXPENSE_OTHER"
    )
    assert [value["coefficient"] for value in catchall["values"]] == [-21, -16]
    assert not any(
        source_ref["label_exact"] == "Khoản chi hoạt động khác chưa khai báo"
        for mapping in candidate["mappings"]
        if mapping["role"] == "INCOME_OTHER"
        for source_ref in mapping["source_refs"]
    )


def test_context_residual_projection_requires_exact_parent_equation() -> None:
    rows = _gross_rows()
    rows.insert(
        3,
        _row(
            "Khoản thu hoạt động khác chưa khai báo",
            "1",
            "1",
            parent="Thu nhập từ hoạt động khác",
        ),
    )
    # The visible income parent remains 100/80 although its children sum to 101/81.
    candidate, _cluster, _receipt = _evaluate(_page(rows))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_root_only_aggregate_is_not_a_usable_detail_graph() -> None:
    page = _page([_row(OWNER, "70", "60", kind="TOTAL")])
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        cluster["component_regions"]
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={_record(page)["page_json_version_id"]: page},
        compiled_specs=_compiled(),
        query_receipt=receipt,
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_primary_statement_summary_is_typed_control_not_a_note_population() -> None:
    page = _page(_gross_rows(), primary=True)
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"].startswith("NOT_OBSERVED")
    assert cluster["component_regions"] == []


def test_conflicting_period_evidence_is_unresolved() -> None:
    columns = [
        {
            "header_path_exact": ["Năm 2026", "Năm trước", "Triệu đồng"],
            "value_kind": "MONEY",
        },
        {"header_path_exact": ["Năm 2025", "Triệu đồng"], "value_kind": "MONEY"},
    ]
    candidate, _cluster, _receipt = _evaluate(_page(_gross_rows(), columns=columns))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_conflicting_unit_evidence_is_unresolved() -> None:
    columns = [
        {
            "header_path_exact": ["Năm 2026", "Triệu đồng", "Nghìn đồng"],
            "value_kind": "MONEY",
        },
        {"header_path_exact": ["Năm 2025", "Triệu đồng"], "value_kind": "MONEY"},
    ]
    candidate, _cluster, _receipt = _evaluate(_page(_gross_rows(), columns=columns))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_duplicate_complete_population_is_unresolved() -> None:
    page = _page(_gross_rows())
    records = [_record(page, ordinal=1), _record(page, ordinal=2)]
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    assert len(cluster["component_regions"]) == 2
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        cluster["component_regions"]
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={record["page_json_version_id"]: page for record in records},
        compiled_specs=_compiled(),
        query_receipt=receipt,
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
