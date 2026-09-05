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
from bctc_ai.evaluation.gemini_json_other_activity_family_v1 import (
    GeminiJsonOtherActivityFamilyV1Error,
    build_gemini_json_other_activity_region_query_receipt_v1,
    compile_gemini_json_other_activity_family_specs_v1,
    evaluate_gemini_json_other_activity_family_cluster_v1,
    recover_gemini_json_other_activity_query_cluster_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    validate_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "a" * 64
SOURCE_SHA256 = "c" * 64
OWNER = "Lãi thuần từ hoạt động khác"


def _json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict[str, Any]:
    return compile_gemini_json_other_activity_family_specs_v1(
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
    assert compiled["duration_header_path_scope_policy"] == (
        "DISTINCT_SUFFIX_AFTER_EXACT_COMMON_PREFIX"
    )
    assert compiled["adjacent_continuation_family_root_policy"] == (
        "EXACT_UNION_OF_DECLARED_ROOT_COMPONENTS_EQUALS_RECEIVER_TERMINAL_TOTAL"
    )
    assert compiled["continuation_period_axis_policy"] == (
        "ADJACENT_PAGE_EXPLICIT_CONTINUATION_INHERITS_COMPLETE_BLANK_HEADER_AXIS"
    )
    assert {item["canonical_unit"] for item in compiled["unit_bindings"] if item["accepted"]} == {
        "MILLION_VND",
        "VND",
    }
    assert (
        compiled["other_activity_primary_specs"]["schema"]["root_mapping_policy"]
        == "SOURCE_VISIBLE_PRIMARY_RESULT_OR_EXACT_NOTE_EQUATION"
    )
    assert (
        compiled["other_activity_direct_detail_specs"]["schema"]["root_mapping_policy"]
        == "STRUCTURAL_CONTEXT_ONLY"
    )
    assert compiled["other_activity_adapter_spec"]["primary_duplicate_presentation_policy"] == (
        "EXACT_OR_VND_WITHIN_ONE_MILLION_TWO_COMPONENT_INDEPENDENT_"
        "DISPLAY_ROUNDING_PREFER_MILLION_VND"
    )
    assert compiled["other_activity_adapter_spec"]["primary_unit_corroboration_policy"] == (
        "EXACT_SAME_DOCUMENT_ROOT_LABEL_AND_NONZERO_SCALAR_IN_EXPLICIT_UNIT_"
        "TABLE_OR_EXACT_UNIQUE_IMMEDIATELY_PRECEDING_PRIMARY_STATEMENT_UNIT"
    )
    assert (
        compiled["other_activity_adapter_spec"]["unlabeled_structural_subtotal_policy"]
        == "EXACT_NONTERMINAL_CONTIGUOUS_SOURCE_COMPONENT_SUM_PRIVATE_OMISSION"
    )


def test_other_activity_adapter_config_rejects_invalid_rounding_policy() -> None:
    adapter = _json("tm-other-activity-adapter-v1.json")
    adapter["primary_duplicate_presentation_policy"] = "MAGNITUDE_GUESS"
    with pytest.raises(GeminiJsonOtherActivityFamilyV1Error):
        compile_gemini_json_other_activity_family_specs_v1(
            _json("tm-other-activity-topology-v1.json"),
            _json("tm-other-activity-evaluation-v1.json"),
            _json("tm-other-activity-schema-binding-v1.json"),
            adapter,
        )


def test_other_activity_adapter_config_rejects_undeclared_primary_unit_policy() -> None:
    adapter = _json("tm-other-activity-adapter-v1.json")
    adapter["primary_unit_corroboration_policy"] = "ASSUME_VND_FROM_MAGNITUDE"
    with pytest.raises(GeminiJsonOtherActivityFamilyV1Error):
        compile_gemini_json_other_activity_family_specs_v1(
            _json("tm-other-activity-topology-v1.json"),
            _json("tm-other-activity-evaluation-v1.json"),
            _json("tm-other-activity-schema-binding-v1.json"),
            adapter,
        )


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


def _adapted_candidate(
    pages: list[dict[str, Any]], *, compiled: dict[str, Any] | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    records = [_record(page, ordinal=ordinal) for ordinal, page in enumerate(pages, start=1)]
    compiled = _compiled() if compiled is None else compiled
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    cluster = recover_gemini_json_other_activity_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == READY
    receipt = build_gemini_json_other_activity_region_query_receipt_v1(
        cluster["component_regions"], cluster=cluster
    )
    candidate = evaluate_gemini_json_other_activity_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={
            record["page_json_version_id"]: page
            for record, page in zip(records, pages, strict=True)
        },
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    return cluster, candidate


def _single_dash_source_repair_spec() -> dict[str, Any]:
    repair = {
        "after_exact": "-",
        "before_exact": None,
        "column_ordinal": 2,
        "locator": {
            "page_json_version_id": "gfpstorev1:json:" + "2" * 64,
            "physical_page": 2,
            "row_ordinal": 5,
            "section_id": "s1",
            "table_id": "t1",
        },
        "pdf_page_render_sha256": "d" * 64,
        "repair_kind": "MONEY_CELL_PDF_VISIBLE_DASH",
        "source_sha256": SOURCE_SHA256,
    }
    repair["repair_id"] = "gjoafav1:repair:" + canonical_json_sha256_v1(repair)
    return {
        "family_id": "OTHER_ACTIVITY",
        "format_version": "OTHER_ACTIVITY_AUTHENTICATED_SOURCE_REPAIR_SPEC_V1",
        "render_contract": {
            "alpha": False,
            "colorspace": "RGB",
            "format": "PNG",
            "matrix": [2, 2],
            "renderer": "PyMuPDF",
        },
        "repairs": [repair],
    }


def test_pdf_visible_dash_repair_is_exact_and_never_treated_as_blank() -> None:
    rows = _gross_rows()
    rows[4]["values_exact"][1] = None
    rows[5]["values_exact"][1] = "(20)"
    note = _page(rows)
    primary = _page([_row(OWNER, "70", "60", kind="TOTAL")], primary=True)
    compiled = compile_gemini_json_other_activity_family_specs_v1(
        _json("tm-other-activity-topology-v1.json"),
        _json("tm-other-activity-evaluation-v1.json"),
        _json("tm-other-activity-schema-binding-v1.json"),
        _json("tm-other-activity-adapter-v1.json"),
        _single_dash_source_repair_spec(),
    )
    cluster, candidate = _adapted_candidate([primary, note], compiled=compiled)
    assert candidate["status"] == READY
    expense = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "EXPENSE_DERIVATIVE"
    )
    assert [cell["coefficient"] for cell in expense["values"]] == [-10, 0]
    assert expense["values"][1]["source_text"] == "-"
    repair_receipts = cluster["owner_receipt"]["other_activity_query_adapter_receipt"][
        "source_repair_receipts"
    ]
    assert len(repair_receipts) == 1
    validate_source_observation_mapping_contract_v1(
        {"trials": [{"mappings": candidate["mappings"]}]}
    )


def test_source_repair_identity_and_before_image_tamper_fail_closed() -> None:
    source_repairs = _single_dash_source_repair_spec()
    source_repairs["repairs"][0]["repair_id"] = "gjoafav1:repair:" + "0" * 64
    with pytest.raises(GeminiJsonOtherActivityFamilyV1Error):
        compile_gemini_json_other_activity_family_specs_v1(
            _json("tm-other-activity-topology-v1.json"),
            _json("tm-other-activity-evaluation-v1.json"),
            _json("tm-other-activity-schema-binding-v1.json"),
            _json("tm-other-activity-adapter-v1.json"),
            source_repairs,
        )

    source_repairs = _single_dash_source_repair_spec()
    compiled = compile_gemini_json_other_activity_family_specs_v1(
        _json("tm-other-activity-topology-v1.json"),
        _json("tm-other-activity-evaluation-v1.json"),
        _json("tm-other-activity-schema-binding-v1.json"),
        _json("tm-other-activity-adapter-v1.json"),
        source_repairs,
    )
    rows = _gross_rows()
    rows[4]["values_exact"][1] = "not-the-bound-blank"
    note = _page(rows)
    primary = _page([_row(OWNER, "70", "60", kind="TOTAL")], primary=True)
    records = [_record(primary, ordinal=1), _record(note, ordinal=2)]
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    with pytest.raises(GeminiJsonOtherActivityFamilyV1Error):
        recover_gemini_json_other_activity_query_cluster_v1(
            page_records=records,
            base_cluster=base,
            compiled_specs=compiled,
        )


def test_pdf_visible_primary_row_alignment_repair_preserves_direct_values() -> None:
    repair = {
        "after_exact": ["32", "70", "60"],
        "before_exact": ["70", "60", "32"],
        "locator": {
            "page_json_version_id": "gfpstorev1:json:" + "1" * 64,
            "physical_page": 1,
            "row_ordinal": 1,
            "section_id": "s1",
            "table_id": "t1",
        },
        "pdf_page_render_sha256": "d" * 64,
        "repair_kind": "ROW_VALUES_PDF_VISIBLE_EXACT",
        "source_sha256": SOURCE_SHA256,
    }
    repair["repair_id"] = "gjoafav1:repair:" + canonical_json_sha256_v1(repair)
    source_repairs = {
        "family_id": "OTHER_ACTIVITY",
        "format_version": "OTHER_ACTIVITY_AUTHENTICATED_SOURCE_REPAIR_SPEC_V1",
        "render_contract": {
            "alpha": False,
            "colorspace": "RGB",
            "format": "PNG",
            "matrix": [2, 2],
            "renderer": "PyMuPDF",
        },
        "repairs": [repair],
    }
    compiled = compile_gemini_json_other_activity_family_specs_v1(
        _json("tm-other-activity-topology-v1.json"),
        _json("tm-other-activity-evaluation-v1.json"),
        _json("tm-other-activity-schema-binding-v1.json"),
        _json("tm-other-activity-adapter-v1.json"),
        source_repairs,
    )
    columns = [
        {"header_path_exact": ["Thuyết minh"], "value_kind": "TEXT"},
        {"header_path_exact": ["Năm 2026", "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": ["Năm 2025", "Triệu đồng"], "value_kind": "MONEY"},
    ]
    primary = _page(
        [_row(OWNER, "70", "60", kind="TOTAL")],
        columns=columns,
        primary=True,
    )
    primary["sections"][0]["tables"][0]["rows"][0]["values_exact"] = [
        "70",
        "60",
        "32",
    ]
    cluster, candidate = _adapted_candidate([primary], compiled=compiled)
    assert candidate["status"] == READY
    root = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL"
    )
    assert [cell["coefficient"] for cell in root["values"]] == [70, 60]
    repair_receipts = cluster["owner_receipt"]["other_activity_query_adapter_receipt"][
        "source_repair_receipts"
    ]
    assert len(repair_receipts) == 1


def test_primary_source_result_maps_directly_only_after_note_not_observed() -> None:
    primary = _page([_row(OWNER, "70", "60", kind="TOTAL")], primary=True)
    cluster, candidate = _adapted_candidate([primary])
    assert (
        cluster["owner_receipt"]["other_activity_query_adapter_receipt"]["rule"]
        == "EXACT_PRIMARY_SOURCE_RESULT_AFTER_NOTE_NOT_OBSERVED"
    )
    assert candidate["status"] == READY
    assert [mapping["role"] for mapping in candidate["mappings"]] == ["FAMILY_ROOT_TOTAL"]
    root = candidate["mappings"][0]
    assert root["state"] == "SOURCE_VISIBLE_PRIMARY_STATEMENT_EXACT_RESULT"
    assert [cell["coefficient"] for cell in root["values"]] == [70, 60]


def test_exact_vnd_and_rounded_million_primary_presentations_prefer_million() -> None:
    raw = _page(
        [_row(OWNER, "4,378,799,768", "24,237,999,626", kind="TOTAL")],
        primary=True,
        unit="VND",
    )
    rounded = _page(
        [_row(OWNER, "4,379", "24,238", kind="TOTAL")],
        primary=True,
        unit="Triệu đồng",
    )
    _cluster, candidate = _adapted_candidate([raw, rounded])
    assert candidate["status"] == READY
    root = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL"
    )
    assert root["unit"] == "MILLION_VND"
    assert [cell["coefficient"] for cell in root["values"]] == [4379, 24238]


def test_two_component_independent_rounding_allows_submillion_root_difference() -> None:
    raw = _page(
        [_row(OWNER, "97,034,133,037", "48,906,452,055", kind="TOTAL")],
        primary=True,
        unit="VND",
    )
    rounded = _page(
        [_row(OWNER, "97,035", "48,907", kind="TOTAL")],
        primary=True,
        unit="Triệu đồng",
    )
    _cluster, candidate = _adapted_candidate([raw, rounded])
    assert candidate["status"] == READY
    root = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL"
    )
    assert [cell["coefficient"] for cell in root["values"]] == [97_035, 48_907]


def test_conflicting_duplicate_primary_presentations_fail_closed() -> None:
    raw = _page(
        [_row(OWNER, "4,378,000,000", "24,237,000,000", kind="TOTAL")],
        primary=True,
        unit="VND",
    )
    rounded = _page(
        [_row(OWNER, "4,379", "24,238", kind="TOTAL")],
        primary=True,
        unit="Triệu đồng",
    )
    records = [_record(raw, ordinal=1), _record(rounded, ordinal=2)]
    compiled = _compiled()
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    cluster = recover_gemini_json_other_activity_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert cluster["reasons"] == ["CONFLICTING_PRIMARY_OTHER_ACTIVITY_SOURCE_PRESENTATIONS"]


def test_visible_note_details_bind_root_to_direct_primary_source_result() -> None:
    note = _page(_gross_rows())
    primary = _page([_row(OWNER, "70", "60", kind="TOTAL")], primary=True)
    cluster, candidate = _adapted_candidate([primary, note])
    assert candidate["status"] == READY
    roots = [mapping for mapping in candidate["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL"]
    assert len(roots) == 1
    assert roots[0]["state"] == "SOURCE_VISIBLE_PRIMARY_STATEMENT_EXACT_RESULT"
    assert roots[0]["source_refs"][0]["locator"]["physical_page"] == 1
    assert {
        mapping["source_refs"][0]["locator"]["physical_page"]
        for mapping in candidate["mappings"]
        if mapping["role"] != "FAMILY_ROOT_TOTAL"
    } == {2}
    assert (
        candidate["closure_receipt"]["other_activity_adapter_receipt"]["strategy"]
        == "DIRECT_NOTE_DETAILS_PLUS_DIRECT_PRIMARY_SOURCE_RESULT"
    )


def test_unitless_note_uses_only_exact_primary_root_vector_unit_control() -> None:
    columns = [
        {"header_path_exact": ["Năm 2026"], "value_kind": "MONEY"},
        {"header_path_exact": ["Năm 2025"], "value_kind": "MONEY"},
    ]
    note = _page(_gross_rows(), columns=columns, unit=None)  # type: ignore[arg-type]
    primary = _page([_row(OWNER, "70", "60", kind="TOTAL")], primary=True)
    _cluster, candidate = _adapted_candidate([primary, note])
    assert candidate["status"] == READY
    receipts = candidate["closure_receipt"]["other_activity_adapter_receipt"][
        "unit_corroboration_receipts"
    ]
    assert len(receipts) == 1
    assert receipts[0]["matched_note_vector"] == [70, 60]
    assert receipts[0]["matched_primary_vector"] == [70, 60]


def test_unitless_primary_uses_exact_same_document_root_scalar_unit_control() -> None:
    primary_columns = [
        {"header_path_exact": ["Quý II", "Năm 2026"], "value_kind": "MONEY"},
        {"header_path_exact": ["Quý II", "Năm 2025"], "value_kind": "MONEY"},
        {
            "header_path_exact": ["Luỹ kế từ đầu năm đến cuối Quý II", "Năm 2026"],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": ["Luỹ kế từ đầu năm đến cuối Quý II", "Năm 2025"],
            "value_kind": "MONEY",
        },
    ]
    primary = _page(
        [_row(OWNER, "1", "2", kind="TOTAL")],
        columns=primary_columns,
        primary=True,
        unit=None,  # type: ignore[arg-type]
    )
    primary["sections"][0]["tables"][0]["rows"][0]["values_exact"] = [
        "1",
        "2",
        "70",
        "60",
    ]
    geography_columns = [
        {"header_path_exact": [name], "value_kind": "MONEY"}
        for name in ["Miền Bắc", "Miền Nam", "Miền Trung", "Nước ngoài", "Tổng cộng"]
    ]
    control = _page(
        [
            {
                "hierarchy_path_exact": [OWNER],
                "label_exact": OWNER,
                "row_kind": "ITEM",
                "values_exact": ["20", "30", "10", "10", "70"],
            }
        ],
        columns=geography_columns,
    )
    control["sections"][0]["title_exact"] = "Báo cáo bộ phận theo khu vực địa lý"
    control["sections"][0]["tables"][0]["title_exact"] = "Từ đầu năm đến cuối kỳ"
    cluster, candidate = _adapted_candidate([primary, control])
    assert candidate["status"] == READY
    root = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL"
    )
    assert root["unit"] == "MILLION_VND"
    assert [cell["coefficient"] for cell in root["values"]] == [70, 60]
    receipt = cluster["owner_receipt"]["other_activity_query_adapter_receipt"][
        "primary_projection_receipt"
    ]["primary_unit_corroboration_receipt"]
    assert receipt["canonical_unit"] == "MILLION_VND"
    assert receipt["control_value"] == 70
    assert receipt["locator"]["physical_page"] == 2
    assert receipt["locator"]["column_ordinal"] == 5


def _primary_balance_sheet_unit_control_page(unit: str = "VND") -> dict[str, Any]:
    page = _page([_row("TỔNG TÀI SẢN", "100", "80", kind="TOTAL")], primary=True, unit=unit)
    page["sections"][0]["statement_type"] = "BALANCE_SHEET"
    page["sections"][0]["title_exact"] = "Báo cáo tình hình tài chính"
    page["sections"][0]["tables"][0]["title_exact"] = "Báo cáo tình hình tài chính"
    return page


def _unitless_primary_other_activity_page() -> dict[str, Any]:
    return _page(
        [_row(OWNER, "70", "60", kind="TOTAL")],
        columns=[
            {"header_path_exact": ["Năm 2026"], "value_kind": "MONEY"},
            {"header_path_exact": ["Năm 2025"], "value_kind": "MONEY"},
        ],
        primary=True,
        unit=None,  # type: ignore[arg-type]
    )


def test_unitless_primary_uses_exact_adjacent_primary_statement_unit_control() -> None:
    control = _primary_balance_sheet_unit_control_page()
    target = _unitless_primary_other_activity_page()
    cluster, candidate = _adapted_candidate([control, target])
    assert candidate["status"] == READY
    root = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL"
    )
    assert root["unit"] == "VND"
    assert [cell["coefficient"] for cell in root["values"]] == [70, 60]
    receipt = cluster["owner_receipt"]["other_activity_query_adapter_receipt"][
        "primary_projection_receipt"
    ]["primary_unit_corroboration_receipt"]
    assert receipt["control_kind"] == "ADJACENT_PRIMARY_STATEMENT_EXPLICIT_UNIT"
    assert receipt["canonical_unit"] == "VND"
    assert receipt["locator"]["physical_page"] == 1
    assert receipt["locator"]["selected_page_ordinal"] == 1
    assert receipt["control_unit_evidence"]


def test_unitless_primary_does_not_inherit_nonadjacent_primary_statement_unit() -> None:
    control = _primary_balance_sheet_unit_control_page()
    intervening = _primary_balance_sheet_unit_control_page()
    intervening["sections"][0]["tables"][0]["unit_exact"] = None
    for column in intervening["sections"][0]["tables"][0]["columns"]:
        column["header_path_exact"] = [column["header_path_exact"][0]]
    records = [
        _record(control, ordinal=1),
        _record(intervening, ordinal=2),
        _record(_unitless_primary_other_activity_page(), ordinal=3),
    ]
    compiled = _compiled()
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    cluster = recover_gemini_json_other_activity_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["reasons"] == ["PRIMARY_OTHER_ACTIVITY_SOURCE_RESULT_NOT_LOCALLY_USABLE"]


def test_unitless_million_note_uses_exact_vnd_rounding_interval_control() -> None:
    columns = [
        {"header_path_exact": ["Năm 2026"], "value_kind": "MONEY"},
        {"header_path_exact": ["Năm 2025"], "value_kind": "MONEY"},
    ]
    note = _page(_gross_rows(), columns=columns, unit=None)  # type: ignore[arg-type]
    primary = _page(
        [_row(OWNER, "70,000,200", "59,999,800", kind="TOTAL")],
        primary=True,
        unit="VND",
    )
    _cluster, candidate = _adapted_candidate([primary, note])
    assert candidate["status"] == READY
    receipts = candidate["closure_receipt"]["other_activity_adapter_receipt"][
        "unit_corroboration_receipts"
    ]
    assert len(receipts) == 1
    assert receipts[0]["canonical_unit"] == "MILLION_VND"
    assert receipts[0]["primary_canonical_unit"] == "VND"
    assert receipts[0]["matched_note_vector"] == [70, 60]
    assert receipts[0]["matched_primary_vector"] == [70_000_200, 59_999_800]


def test_unitless_note_mismatch_is_not_unit_inferred() -> None:
    columns = [
        {"header_path_exact": ["Năm 2026"], "value_kind": "MONEY"},
        {"header_path_exact": ["Năm 2025"], "value_kind": "MONEY"},
    ]
    note = _page(_gross_rows(), columns=columns, unit=None)  # type: ignore[arg-type]
    primary = _page([_row(OWNER, "71", "60", kind="TOTAL")], primary=True)
    _cluster, candidate = _adapted_candidate([primary, note])
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert (
        candidate["closure_receipt"]["other_activity_adapter_receipt"][
            "unit_corroboration_receipts"
        ]
        == []
    )


def test_repeated_owner_header_prefix_cannot_create_false_vnd_unit() -> None:
    columns = [
        {"header_path_exact": [OWNER, "Kỳ này"], "value_kind": "MONEY"},
        {"header_path_exact": [OWNER, "Kỳ trước"], "value_kind": "MONEY"},
    ]
    note = _page(_gross_rows(), columns=columns)
    primary = _page([_row(OWNER, "70", "60", kind="TOTAL")], primary=True)
    _cluster, candidate = _adapted_candidate([primary, note])
    assert candidate["status"] == READY
    receipts = candidate["closure_receipt"]["other_activity_adapter_receipt"][
        "unit_corroboration_receipts"
    ]
    scope = next(
        receipt
        for receipt in receipts
        if receipt["rule"].startswith("EXACT_REPEATED_OWNER_HEADER_PREFIX")
    )
    assert scope["canonical_unit"] == "MILLION_VND"
    assert [
        projection["after_header_path_exact"] for projection in scope["header_projections"]
    ] == [["Kỳ này"], ["Kỳ trước"]]


def test_partial_blank_note_lane_never_becomes_numeric() -> None:
    rows = _gross_rows()
    rows[2]["values_exact"] = ["40", None]
    rows[0]["values_exact"] = ["100", None]
    note = _page(rows)
    primary = _page([_row(OWNER, "70", "60", kind="TOTAL")], primary=True)
    _cluster, candidate = _adapted_candidate([primary, note])
    assert candidate["status"] == READY
    income_other = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "INCOME_OTHER"
    )
    assert [cell["coefficient"] for cell in income_other["values"]] == [40, None]
    assert income_other["values"][1]["state"] == "BLANK_SOURCE_CELL"
    validate_source_observation_mapping_contract_v1(
        {"trials": [{"mappings": candidate["mappings"]}]}
    )


def test_pdf_visible_money_column_repair_unlocks_exact_adjacent_continuation() -> None:
    prior = _page(
        [
            _row("Thu từ hoạt động khác", "100", "80", kind="TOTAL"),
            _row("Chi từ hoạt động khác", "(30)", "(20)", kind="TOTAL"),
        ]
    )
    prior["sections"][0]["tables"][0]["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    receiver = _page(
        [_row(None, "70", "60", kind="UNKNOWN")],
        columns=[
            {"header_path_exact": [None], "value_kind": "UNKNOWN"},
            {"header_path_exact": [None], "value_kind": "MONEY"},
        ],
        unit=None,  # type: ignore[arg-type]
    )
    receiver["sections"][0]["title_exact"] = None
    receiver["sections"][0]["tables"][0]["title_exact"] = None
    receiver["sections"][0]["tables"][0]["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"
    column_repair = {
        "after_exact": "MONEY",
        "before_exact": "UNKNOWN",
        "column_ordinal": 1,
        "locator": {
            "page_json_version_id": "gfpstorev1:json:" + "3" * 64,
            "physical_page": 3,
            "row_ordinal": 1,
            "section_id": "s1",
            "table_id": "t1",
        },
        "pdf_page_render_sha256": "d" * 64,
        "repair_kind": "COLUMN_VALUE_KIND_PDF_VISIBLE_MONEY",
        "source_sha256": SOURCE_SHA256,
    }
    column_repair["repair_id"] = "gjoafav1:repair:" + canonical_json_sha256_v1(column_repair)
    row_repair = {
        "after_exact": "TOTAL",
        "before_exact": "UNKNOWN",
        "locator": {
            "page_json_version_id": "gfpstorev1:json:" + "3" * 64,
            "physical_page": 3,
            "row_ordinal": 1,
            "section_id": "s1",
            "table_id": "t1",
        },
        "pdf_page_render_sha256": "d" * 64,
        "repair_kind": "ROW_KIND_PDF_VISIBLE_TOTAL",
        "source_sha256": SOURCE_SHA256,
    }
    row_repair["repair_id"] = "gjoafav1:repair:" + canonical_json_sha256_v1(row_repair)
    source_repairs = {
        "family_id": "OTHER_ACTIVITY",
        "format_version": "OTHER_ACTIVITY_AUTHENTICATED_SOURCE_REPAIR_SPEC_V1",
        "render_contract": {
            "alpha": False,
            "colorspace": "RGB",
            "format": "PNG",
            "matrix": [2, 2],
            "renderer": "PyMuPDF",
        },
        "repairs": [row_repair, column_repair],
    }
    compiled = compile_gemini_json_other_activity_family_specs_v1(
        _json("tm-other-activity-topology-v1.json"),
        _json("tm-other-activity-evaluation-v1.json"),
        _json("tm-other-activity-schema-binding-v1.json"),
        _json("tm-other-activity-adapter-v1.json"),
        source_repairs,
    )
    primary = _page([_row(OWNER, "70", "60", kind="TOTAL")], primary=True)
    cluster, candidate = _adapted_candidate([primary, prior, receiver], compiled=compiled)
    assert candidate["status"] == READY
    assert [region["physical_page"] for region in cluster["component_regions"]] == [
        1,
        2,
        3,
    ]
    repair_receipts = cluster["owner_receipt"]["other_activity_query_adapter_receipt"][
        "source_repair_receipts"
    ]
    assert [receipt["repair"]["repair_kind"] for receipt in repair_receipts] == [
        "ROW_KIND_PDF_VISIBLE_TOTAL",
        "COLUMN_VALUE_KIND_PDF_VISIBLE_MONEY",
    ]
    assert [mapping["role"] for mapping in candidate["mappings"]] == [
        "INCOME_PARENT",
        "EXPENSE_PARENT",
        "FAMILY_ROOT_TOTAL",
    ]


def test_exact_unlabeled_nonterminal_subtotals_are_equation_bound_not_mapped() -> None:
    rows = [
        _row("Thu bán tài sản gán nợ", "10", "8"),
        _row("Thu hồi các khoản nợ đã xóa", "20", "12"),
        _row(None, "30", "20", kind="SUBTOTAL"),
        _row("Chi phí khác", None, None, kind="GROUP"),
        _row("Tài sản cố định giảm trong kỳ", "(5)", "(4)", parent="Chi phí khác"),
        _row("Chi phí xử lý nợ, chi phí khác", "(2)", "(1)", parent="Chi phí khác"),
        _row(None, "(7)", "(5)", kind="SUBTOTAL"),
        _row("Cộng", "23", "15", kind="TOTAL"),
    ]
    note = _page(rows)
    primary = _page([_row(OWNER, "23", "15", kind="TOTAL")], primary=True)
    _cluster, candidate = _adapted_candidate([primary, note])
    assert candidate["status"] == READY
    receipts = candidate["closure_receipt"]["other_activity_adapter_receipt"][
        "structural_projection_receipts"
    ]
    assert [receipt["subtotal_row_ordinal"] for receipt in receipts] == [3, 7]
    assert [receipt["component_row_ordinals"] for receipt in receipts] == [
        [1, 2],
        [5, 6],
    ]
    assert all(
        lane["status"] == "EXACT_OBSERVED_SOURCE_LANE"
        for receipt in receipts
        for lane in receipt["lane_receipts"]
    )
    mapped_rows = {
        source_ref["row_ordinal"]
        for mapping in candidate["mappings"]
        for source_ref in mapping["source_refs"]
    }
    assert mapped_rows.isdisjoint({3, 7})


def test_lpb_explicit_income_expense_groups_map_every_declared_visible_row() -> None:
    income = "Thu nhập hoạt động kinh doanh khác"
    expense = "Chi phí hoạt động kinh doanh khác"
    rows = [
        _row(income, None, None, kind="GROUP"),
        _row("Thu từ thanh lý tài sản", "10", "8", parent=income),
        _row("Thu từ các khoản nợ đã được xử lý", "20", "12", parent=income),
        _row("Thu từ các hợp đồng hoán đổi lãi suất", "30", "15", parent=income),
        _row("Thu nhập khác", "40", "25", parent=income),
        _row(None, "100", "60", kind="SUBTOTAL"),
        _row(expense, None, None, kind="GROUP"),
        _row("Chi về các hợp đồng hoán đổi lãi suất", "(5)", "(4)", parent=expense),
        _row("Chi phí khác", "(2)", "(1)", parent=expense),
        _row(None, "(7)", "(5)", kind="SUBTOTAL"),
        _row("Cộng", "93", "55", kind="TOTAL"),
    ]
    note = _page(rows)
    primary = _page([_row(OWNER, "93", "55", kind="TOTAL")], primary=True)
    _cluster, candidate = _adapted_candidate([primary, note])
    assert candidate["status"] == READY
    roles = {mapping["role"] for mapping in candidate["mappings"]}
    assert {
        "INCOME_PARENT",
        "INCOME_ASSET_DISPOSAL",
        "INCOME_DEBT_RECOVERY",
        "INCOME_DERIVATIVE",
        "INCOME_OTHER",
        "EXPENSE_PARENT",
        "EXPENSE_DERIVATIVE",
        "EXPENSE_OTHER",
        "FAMILY_ROOT_TOTAL",
    }.issubset(roles)


def test_unlabeled_subtotal_with_blank_component_lane_cannot_prove_projection() -> None:
    rows = [
        _row("Thu bán tài sản gán nợ", "10", None),
        _row("Thu hồi các khoản nợ đã xóa", "20", "12"),
        _row(None, "30", "20", kind="SUBTOTAL"),
        _row("Chi phí khác", None, None, kind="GROUP"),
        _row("Tài sản cố định giảm trong kỳ", "(5)", "(4)", parent="Chi phí khác"),
        _row("Chi phí xử lý nợ, chi phí khác", "(2)", "(1)", parent="Chi phí khác"),
        _row(None, "(7)", "(5)", kind="SUBTOTAL"),
        _row("Cộng", "23", "15", kind="TOTAL"),
    ]
    note = _page(rows)
    primary = _page([_row(OWNER, "23", "15", kind="TOTAL")], primary=True)
    _cluster, candidate = _adapted_candidate([primary, note])
    assert candidate["status"] == READY
    receipts = candidate["closure_receipt"]["other_activity_adapter_receipt"][
        "structural_projection_receipts"
    ]
    assert [receipt["subtotal_row_ordinal"] for receipt in receipts] == [7]
    income = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "INCOME_ASSET_DISPOSAL"
    )
    assert [cell["coefficient"] for cell in income["values"]] == [10, None]
    assert income["values"][1]["state"] == "BLANK_SOURCE_CELL"
    validate_source_observation_mapping_contract_v1(
        {"trials": [{"mappings": candidate["mappings"]}]}
    )


def test_primary_projection_receipt_tamper_is_rejected() -> None:
    primary = _page([_row(OWNER, "70", "60", kind="TOTAL")], primary=True)
    records = [_record(primary)]
    compiled = _compiled()
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    cluster = recover_gemini_json_other_activity_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled
    )
    receipt = build_gemini_json_other_activity_region_query_receipt_v1(
        cluster["component_regions"], cluster=cluster
    )
    receipt["adapter_receipt"]["primary_projection_receipt"]["label_exact"] = "tampered"
    with pytest.raises(GeminiJsonOtherActivityFamilyV1Error):
        evaluate_gemini_json_other_activity_family_cluster_v1(
            regions=cluster["component_regions"],
            page_json_by_version={records[0]["page_json_version_id"]: primary},
            compiled_specs=compiled,
            query_receipt=receipt,
        )
