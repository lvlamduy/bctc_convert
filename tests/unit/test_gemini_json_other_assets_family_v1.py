from __future__ import annotations

import json
from pathlib import Path

from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    _adjacent_continuation_lane_axis,
    _adjacent_numbered_subsection_unit_axis,
    _multitable_lane_axis,
    _typed_control_surface_matches,
    _unit_axis,
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    classify_gemini_json_multitable_hierarchical_table_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_other_assets_family_v1 import (
    _exact_provision_control_receipt_v1,
    _one_sided_continuation_receipt_v1,
    adapt_gemini_json_other_assets_indexed_query_evidence_v1,
    evaluate_gemini_json_other_assets_family_cluster_v1,
    validate_gemini_json_other_assets_family_candidate_replay_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "1" * 64
SOURCE_SHA256 = "2" * 64


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-other-assets-topology-v1.json"),
        _json("tm-other-assets-evaluation-v1.json"),
        _json("tm-other-assets-schema-binding-v1.json"),
    )


def test_family29_and_family30_continuation_extensions_are_absent_by_default() -> None:
    compiled = _compiled()

    assert "adjacent_continuation_family_root_policy" not in compiled
    assert "continuation_leading_child_scope_policy" not in compiled
    assert "root_component_role_combinations" not in compiled


def _unit_table(*, table_unit: str, noisy_header: bool) -> dict:
    unit_surface = "nTriệu VND" if noisy_header else "Triệu VND"
    return {
        "columns": [
            {
                "header_path_exact": ["31/12/2025", unit_surface, "Triệu VND"],
                "value_kind": "MONEY",
            },
            {
                "header_path_exact": ["31/12/2024", unit_surface, "Triệu VND"],
                "value_kind": "MONEY",
            },
        ],
        "continuation": "NONE",
        "rows": [],
        "title_exact": "Tài sản Có khác",
        "unit_exact": table_unit,
    }


def test_noisy_full_header_vnd_suffix_is_dominated_by_specific_million_unit() -> None:
    axis = _unit_axis(
        _unit_table(table_unit="Triệu VND", noisy_header=True),
        compiled_specs=_compiled(),
    )
    assert axis["complete"] is True
    assert axis["canonical_unit"] == "MILLION_VND"
    assert axis["reasons"] == []
    assert {item["matched_alias"] for item in axis["evidence"]} == {"trieu vnd"}


def test_standalone_vnd_surface_is_not_specificity_pruned() -> None:
    table = _unit_table(table_unit="VND", noisy_header=False)
    table["columns"][0]["header_path_exact"] = ["31/12/2025", "VND"]
    table["columns"][1]["header_path_exact"] = ["31/12/2024", "VND"]
    axis = _unit_axis(table, compiled_specs=_compiled())
    assert axis["complete"] is True
    assert axis["canonical_unit"] == "VND"
    assert axis["reasons"] == []
    assert any(
        item["canonical_unit"] == "VND" and item["accepted"] is True
        for item in axis["evidence"]
    )


def test_literal_escaped_newline_does_not_create_a_fake_ntrieu_unit() -> None:
    table = _unit_table(table_unit="Triệu VND", noisy_header=False)
    table["columns"][0]["header_path_exact"] = ["31/12/2025\\nTriệu VND"]
    table["columns"][1]["header_path_exact"] = ["31/12/2024\\nTriệu VND"]
    axis = _unit_axis(table, compiled_specs=_compiled())
    assert axis["complete"] is True
    assert axis["canonical_unit"] == "MILLION_VND"
    assert axis["reasons"] == []
    assert {item["matched_alias"] for item in axis["evidence"]} == {"trieu vnd"}


def _columns(*, blank: bool = False) -> list[dict]:
    headers = ([None], [None]) if blank else (["31/12/2025"], ["31/12/2024"])
    return [
        {"header_path_exact": list(header), "value_kind": "MONEY"}
        for header in headers
    ]


def _row(
    label: str | None,
    *,
    kind: str = "ITEM",
    values: list[str | None] | None = None,
    hierarchy: list[str | None] | None = None,
) -> dict:
    return {
        "hierarchy_path_exact": [label] if hierarchy is None else hierarchy,
        "label_exact": label,
        "row_kind": kind,
        "values_exact": ["10", "9"] if values is None else values,
    }


def _table(
    title: str | None,
    rows: list[dict],
    *,
    continuation: str = "NONE",
    columns: list[dict] | None = None,
) -> dict:
    return {
        "columns": _columns() if columns is None else columns,
        "continuation": continuation,
        "rows": rows,
        "title_exact": title,
        "unit_exact": "Triệu đồng",
    }


def _section(title: str | None, *tables: dict, narratives: list[str] | None = None) -> dict:
    return {
        "content_kind": "FINANCIAL_NOTE",
        "narratives_exact": [] if narratives is None else narratives,
        "statement_type": "NOT_APPLICABLE",
        "tables": list(tables),
        "title_exact": title,
    }


def _page(*sections: dict) -> dict:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": list(sections),
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _record(page: dict, *, ordinal: int, page_number: int) -> dict:
    return {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": "gfpstorev1:json:" + str(ordinal) * 64,
        "physical_page": page_number,
        "selected_page_ordinal": page_number,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }


def _evaluate(page: dict) -> tuple[dict, dict]:
    compiled = _compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page, ordinal=3, page_number=1)],
        compiled_specs=compiled,
    )
    assert cluster["status"] == READY
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        cluster["component_regions"]
    )
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={"gfpstorev1:json:" + "3" * 64: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    return cluster, candidate


def test_project_detail_generic_rows_stay_source_only_but_total_keeps_context() -> None:
    table = _table(
        "11.1 Chi phí xây dựng cơ bản dở dang",
        [_row("Khác"), _row("Tổng cộng", kind="TOTAL")],
    )
    section = _section("11. Tài sản Có khác", table)

    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        _page(section), section, table, compiled_specs=_compiled()
    )

    assert classification["context_roles"] == ["CONSTRUCTION_IN_PROGRESS"]
    assert classification["role_hits"] == []
    assert classification["unbound_money_row_ordinals"] == [1, 2]
    assert classification["total_rows"] == [
        {"row_kind": "TOTAL", "row_ordinal": 2, "source_order": 2}
    ]


def test_explicit_cip_movement_title_is_required_for_generic_movement_rows() -> None:
    true_table = _table(
        "Thay đổi khoản mục chi phí xây dựng cơ bản dở dang trong năm như sau:",
        [_row("Số dư đầu năm"), _row("Tăng trong năm"), _row("Số dư cuối năm", kind="TOTAL")],
    )
    true_section = _section("Tài sản Có khác", true_table)
    true_classification = classify_gemini_json_multitable_hierarchical_table_v1(
        _page(true_section), true_section, true_table, compiled_specs=_compiled()
    )
    assert true_classification["context_roles"] == ["CIP_MOVEMENT"]
    assert {hit["role"] for hit in true_classification["role_hits"]} == {
        "CIP_OPENING",
        "CIP_INCREASE",
        "CIP_ENDING",
    }

    sibling = _table("Chi phí trả trước", [_row("Chi phí trả trước")])
    false_table = _table(
        None,
        [_row("Số dư đầu năm"), _row("Tăng trong năm"), _row("Số dư cuối năm", kind="TOTAL")],
    )
    false_section = _section("Tài sản Có khác", sibling, false_table)
    false_classification = classify_gemini_json_multitable_hierarchical_table_v1(
        _page(false_section), false_section, false_table, compiled_specs=_compiled()
    )
    assert false_classification["context_roles"] == []
    assert false_classification["role_hits"] == []
    assert false_classification["row_population_context_suppressions"] == [
        {
            "context_roles": ["CIP_MOVEMENT"],
            "row_ordinals": [1, 2, 3],
            "rule": "ROW_POPULATION_CONTEXT_REQUIRES_EXPLICIT_HEADING_OR_HIERARCHY_PATH",
        }
    ]

    period_table = _table(
        "Thay đổi khoản mục chi phí xây dựng cơ bản dở dang trong kỳ như sau:",
        [_row("Số dư đầu kỳ"), _row("Tăng trong kỳ"), _row("Số dư cuối kỳ", kind="TOTAL")],
    )
    period_section = _section("Tài sản Có khác", period_table)
    period_classification = classify_gemini_json_multitable_hierarchical_table_v1(
        _page(period_section), period_section, period_table, compiled_specs=_compiled()
    )
    assert period_classification["context_roles"] == ["CIP_MOVEMENT"]


def test_comprehensive_owner_summary_prefers_structural_root_over_detail_leaf() -> None:
    table = _table(
        None,
        [
            _row("Các khoản phải thu"),
            _row("Các khoản lãi, phí phải thu"),
            _row("Tài sản Có khác"),
            _row("Tổng cộng", kind="TOTAL"),
        ],
    )
    section = _section("12. Tài sản Có khác", table)

    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        _page(section), section, table, compiled_specs=_compiled()
    )

    by_row = {hit["row_ordinal"]: hit["role"] for hit in classification["role_hits"]}
    assert by_row[3] == "OTHER_ASSET_BRANCH"
    assert classification["owner_summary_structural_role_resolutions"][0][
        "original_role"
    ] == "OTHER_ASSET"


def test_ordinal_owner_summary_uses_two_visible_outside_branch_frontier_rows() -> None:
    table = _table(
        None,
        [
            _row("Chi phí xây dựng cơ bản dở dang"),
            _row("Các khoản phải thu"),
            _row("4. Tài sản Có khác"),
            _row("Tổng cộng", kind="TOTAL"),
        ],
    )
    section = _section("4. Tài sản Có khác", table)

    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        _page(section), section, table, compiled_specs=_compiled()
    )

    by_row = {hit["row_ordinal"]: hit["role"] for hit in classification["role_hits"]}
    assert by_row[3] == "OTHER_ASSET_BRANCH"
    receipt = classification["owner_summary_structural_role_resolutions"][0]
    assert {item["row_ordinal"] for item in receipt["outside_branch_frontier"]} == {1, 2}


def test_owner_branch_detail_does_not_trigger_summary_structural_rewrite() -> None:
    table = _table(
        "4.1 Tài sản Có khác",
        [
            _row("Chi phí trả trước"),
            _row("Tài sản Có khác"),
            _row("Tổng cộng", kind="TOTAL"),
        ],
    )
    section = _section("4. Tài sản Có khác", table)

    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        _page(section), section, table, compiled_specs=_compiled()
    )

    assert classification.get("owner_summary_structural_role_resolutions", []) == []


def test_titleless_sole_money_table_uses_exact_longest_detail_narrative_context() -> None:
    detail = _table(
        None,
        [_row("Phải thu nội bộ"), _row("Tổng cộng", kind="TOTAL")],
    )
    section = _section(
        "15. Tài sản Có khác",
        detail,
        narratives=["b) Các khoản phải thu khác bao gồm:"],
    )

    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        _page(section), section, detail, compiled_specs=_compiled()
    )

    assert classification["context_roles"] == ["OTHER_RECEIVABLE"]
    assert (
        classification["context_resolution_kind"]
        == "EXPLICIT_TITLELESS_SOLE_TABLE_SECTION_NARRATIVE"
    )

    generic_movement_labels = _table(
        None,
        [_row("Số dư đầu kỳ"), _row("Số dư cuối kỳ", kind="TOTAL")],
    )
    generic_section = _section(
        "15. Tài sản Có khác",
        generic_movement_labels,
        narratives=["b) Các khoản phải thu khác bao gồm:"],
    )
    generic = classify_gemini_json_multitable_hierarchical_table_v1(
        _page(generic_section),
        generic_section,
        generic_movement_labels,
        compiled_specs=_compiled(),
    )
    assert generic["context_roles"] == ["OTHER_RECEIVABLE"]
    assert generic["role_hits"] == []

    sibling = _table("Một bảng tiền khác", [_row("Không thuộc schema")])
    multi_section = _section(
        "15. Tài sản Có khác",
        detail,
        sibling,
        narratives=["b) Các khoản phải thu khác bao gồm:"],
    )
    multi = classify_gemini_json_multitable_hierarchical_table_v1(
        _page(multi_section), multi_section, detail, compiled_specs=_compiled()
    )
    assert multi["context_roles"] != ["OTHER_RECEIVABLE"]


def test_additive_hierarchy_path_expands_only_its_unique_declared_parent_chain() -> None:
    row = _row("Các khoản khác")
    row["hierarchy_path_exact"] = ["- Các khoản phải thu bên ngoài", "Các khoản khác"]
    target = _table(None, [row])
    sibling = _table("Một bảng tiền khác", [_row("Không thuộc schema")])
    section = _section("14.3 Chi tiết", target, sibling)

    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        _page(section), section, target, compiled_specs=_compiled()
    )

    assert classification["ambiguous_rows"] == []
    assert classification["role_hits"][0]["role"] == "OTHER_RECEIVABLE"
    assert classification["hierarchy_path_scope_resolutions"][0]["rule"] == (
        "EXACT_HIERARCHY_PATH_DECLARED_PARENT_CHAIN_SCOPES_CHILD"
    )


def test_exact_goodwill_control_does_not_poison_longer_declared_heading() -> None:
    compiled = _compiled()
    exclusion = next(
        item
        for item in compiled["typed_control_exclusions"]
        if item["disposition"]
        == "GOODWILL_DETAIL_WITH_NON_PERIOD_OR_MOVEMENT_AXIS_SOURCE_ONLY"
    )
    exact = _table("Lợi thế thương mại", [_row("Số dư đầu năm")])
    longer = _table("Lợi thế thương mại kỳ này", [_row("Tổng giá trị Lợi thế thương mại")])
    section = _section("Tài sản Có khác", exact, longer)

    assert _typed_control_surface_matches(exclusion, section=section, table=exact)
    assert not _typed_control_surface_matches(exclusion, section=section, table=longer)


def test_higher_numbered_narrative_does_not_split_prior_numbered_table_continuation() -> None:
    summary = _table(
        "14. Tài sản Có khác",
        [_row("Các khoản phải thu"), _row("Tổng cộng", kind="TOTAL")],
    )
    continuation = _table(
        "14.4 Tài sản Có khác",
        [_row("Chi phí trả trước"), _row("Tổng cộng", kind="TOTAL")],
    )
    page_one = _page(_section("14. Tài sản Có khác", summary))
    page_two = _page(
        _section(
            "Tài sản Có khác (tiếp theo)",
            continuation,
            narratives=["15. Tài sản cố định hữu hình"],
        )
    )

    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[
            _record(page_one, ordinal=3, page_number=36),
            _record(page_two, ordinal=4, page_number=37),
        ],
        compiled_specs=_compiled(),
    )

    assert cluster["status"] == READY
    assert {
        (region["physical_page"], region["table_id"])
        for region in cluster["component_regions"]
    } == {(36, "t1"), (37, "t1")}


def test_blank_header_continuation_inherits_only_adjacent_explicit_prior_axis() -> None:
    prior_table = _table(
        "14. Tài sản Có khác",
        [_row("Các khoản phải thu")],
        continuation="CONTINUES_ON_NEXT_PAGE",
    )
    continuation = _table(
        None,
        [_row("Chi phí trả trước")],
        continuation="CONTINUES_FROM_PREVIOUS_PAGE",
        columns=_columns(blank=True),
    )
    prior_section = _section("14. Tài sản Có khác", prior_table)
    section = _section("Tài sản Có khác (tiếp theo)", continuation)
    prior_axis = _multitable_lane_axis(
        prior_section, prior_table, compiled_specs=_compiled()
    )
    prior = {
        "lane_axis": prior_axis,
        "region": {
            "document_id": DOCUMENT_ID,
            "physical_page": 18,
            "selected_page_ordinal": 18,
        },
        "table": prior_table,
    }
    region = {
        "document_id": DOCUMENT_ID,
        "physical_page": 19,
        "selected_page_ordinal": 19,
    }

    inherited = _adjacent_continuation_lane_axis(
        section,
        continuation,
        region,
        compiled_specs=_compiled(),
        prior_fragment=prior,
    )
    assert inherited is not None
    assert inherited["complete"] is True
    assert inherited["source_lane_keys"] == prior_axis["source_lane_keys"]
    assert inherited["money_column_ordinals"] == [1, 2]

    nonadjacent = {**region, "physical_page": 20, "selected_page_ordinal": 20}
    assert (
        _adjacent_continuation_lane_axis(
            section,
            continuation,
            nonadjacent,
            compiled_specs=_compiled(),
            prior_fragment=prior,
        )
        is None
    )


def test_coalescer_admits_only_exact_adjacent_blank_header_continuation() -> None:
    prior_table = _table(
        "14. Tài sản Có khác",
        [_row("Tài sản Có khác")],
        continuation="CONTINUES_ON_NEXT_PAGE",
    )
    continuation = _table(
        None,
        [_row("Chi phí trả trước")],
        continuation="CONTINUES_FROM_PREVIOUS_PAGE",
        columns=_columns(blank=True),
    )
    first = _page(_section("14. Tài sản Có khác", prior_table))
    second = _page(_section(None, continuation))
    compiled = _compiled()

    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[
            _record(first, ordinal=5, page_number=18),
            _record(second, ordinal=6, page_number=19),
        ],
        compiled_specs=compiled,
    )
    assert cluster["status"] == READY
    assert [region["physical_page"] for region in cluster["component_regions"]] == [
        18,
        19,
    ]

    conflicting = json.loads(json.dumps(second))
    conflicting["sections"][0]["tables"][0]["columns"] = list(
        reversed(_columns())
    )
    conflict_cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[
            _record(first, ordinal=5, page_number=18),
            _record(conflicting, ordinal=6, page_number=19),
        ],
        compiled_specs=compiled,
    )
    assert 19 not in {
        region["physical_page"] for region in conflict_cluster["component_regions"]
    }

    nonadjacent = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[
            _record(first, ordinal=5, page_number=18),
            _record(second, ordinal=7, page_number=20),
        ],
        compiled_specs=compiled,
    )
    assert 20 not in {region["physical_page"] for region in nonadjacent["component_regions"]}


def test_adjacent_explicit_owner_numbered_parent_supplies_unit_to_strict_subsection() -> None:
    prior_table = _table(
        "4.10 Tài sản Có khác",
        [_row("Các khoản phải thu"), _row("Tổng cộng", kind="TOTAL")],
        columns=[
            {"header_path_exact": ["31/12/2025", "VND"], "value_kind": "MONEY"},
            {"header_path_exact": ["31/12/2024", "VND"], "value_kind": "MONEY"},
        ],
    )
    prior_table["unit_exact"] = "VND"
    table = _table(
        "4.10.1 Các khoản phải thu",
        [_row("Phải thu nội bộ"), _row("Tổng cộng", kind="TOTAL")],
    )
    table["unit_exact"] = None
    prior_section = _section("4.10 Tài sản Có khác", prior_table)
    section = _section("4.10.1 Các khoản phải thu", table)
    compiled = _compiled()
    prior_lane_axis = _multitable_lane_axis(
        prior_section, prior_table, compiled_specs=compiled
    )
    lane_axis = _multitable_lane_axis(section, table, compiled_specs=compiled)
    prior_unit_axis = _unit_axis(prior_table, compiled_specs=compiled)
    local_unit_axis = _unit_axis(table, compiled_specs=compiled)
    region = {
        "document_id": DOCUMENT_ID,
        "physical_page": 36,
        "selected_page_ordinal": 36,
    }
    prior_fragment = {
        "classification": classify_gemini_json_multitable_hierarchical_table_v1(
            _page(prior_section), prior_section, prior_table, compiled_specs=compiled
        ),
        "lane_axis": prior_lane_axis,
        "region": region,
        "section": prior_section,
        "table": prior_table,
        "unit_axis": prior_unit_axis,
    }

    inherited = _adjacent_numbered_subsection_unit_axis(
        section,
        table,
        region,
        lane_axis,
        local_unit_axis,
        compiled_specs=compiled,
        prior_fragment=prior_fragment,
    )
    assert inherited is not None
    assert inherited["complete"] is True
    assert inherited["canonical_unit"] == "VND"
    assert inherited["source"] == "ADJACENT_EXPLICIT_OWNER_NUMBERED_PARENT_UNIT"

    unrelated = {**table, "title_exact": "4.11.1 Các khoản phải thu"}
    assert (
        _adjacent_numbered_subsection_unit_axis(
            section,
            unrelated,
            region,
            lane_axis,
            local_unit_axis,
            compiled_specs=compiled,
            prior_fragment=prior_fragment,
        )
        is None
    )


def test_provision_movement_control_requires_complete_structural_row_signature() -> None:
    compiled = _compiled()
    exclusion = next(
        item
        for item in compiled["typed_control_exclusions"]
        if item["disposition"] == "OTHER_ASSET_PROVISION_MOVEMENT_CONTROL"
    )
    movement = _table(
        None,
        [
            _row("Số dư đầu kỳ"),
            _row("Trích lập dự phòng"),
            _row("Số dư cuối kỳ", kind="TOTAL"),
        ],
    )
    balance = _table(
        None,
        [
            _row("Dự phòng chung"),
            _row("Dự phòng cụ thể"),
            _row("Tổng cộng", kind="TOTAL"),
        ],
    )
    section = _section(
        "Tài sản Có khác",
        movement,
        balance,
        narratives=["Biến động dự phòng rủi ro cho các tài sản Có nội bảng khác"],
    )

    assert _typed_control_surface_matches(exclusion, section=section, table=movement)
    assert not _typed_control_surface_matches(exclusion, section=section, table=balance)


def test_ordered_exact_narratives_scope_each_titleless_money_table_one_to_one() -> None:
    external = _table(
        None,
        [_row("Khác"), _row("Tổng cộng", kind="TOTAL")],
    )
    internal = _table(
        None,
        [_row("Khác"), _row("Tổng cộng", kind="TOTAL")],
    )
    section = _section(
        "Tài sản Có khác",
        external,
        internal,
        narratives=[
            "(iii) Các khoản phải thu bên ngoài",
            "(iv) Các khoản phải thu nội bộ",
        ],
    )
    page = _page(section)
    compiled = _compiled()

    external_classification = classify_gemini_json_multitable_hierarchical_table_v1(
        page, section, external, compiled_specs=compiled
    )
    internal_classification = classify_gemini_json_multitable_hierarchical_table_v1(
        page, section, internal, compiled_specs=compiled
    )
    assert external_classification["context_roles"] == ["EXTERNAL_RECEIVABLES"]
    assert internal_classification["context_roles"] == ["INTERNAL_RECEIVABLES"]
    assert {
        external_classification["context_resolution_kind"],
        internal_classification["context_resolution_kind"],
    } == {"EXPLICIT_TITLELESS_ORDERED_TABLE_SECTION_NARRATIVE"}
    assert internal_classification["role_hits"] == []

    _cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "INTERNAL_RECEIVABLES",
        "OTHER_RECEIVABLE",
    }
    internal_receipt = candidate["closure_receipt"]["table_receipts"][1]
    assert internal_receipt["source_only_rows"][0]["row_ordinal"] == 1
    assert internal_receipt["source_only_rows"][0]["consumed_by_exact_equation"] is True


def test_ordered_narrative_context_fails_closed_when_a_titled_money_sibling_exists() -> None:
    titleless = _table(None, [_row("Khác")])
    titled = _table("Các khoản phải thu", [_row("Phải thu nội bộ")])
    section = _section(
        "Tài sản Có khác",
        titleless,
        titled,
        narratives=["(iii) Các khoản phải thu bên ngoài"],
    )
    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        _page(section), section, titleless, compiled_specs=_compiled()
    )

    assert classification["context_resolution_kind"] != (
        "EXPLICIT_TITLELESS_ORDERED_TABLE_SECTION_NARRATIVE"
    )


def test_composite_capex_heading_resolves_unique_declared_context() -> None:
    table = _table(
        "Mua sắm tài sản cố định và xây dựng cơ bản dở dang",
        [_row("Khác"), _row("Tổng cộng", kind="TOTAL")],
    )
    section = _section("Tài sản Có khác", table)
    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        _page(section), section, table, compiled_specs=_compiled()
    )

    assert classification["context_roles"] == ["FIXED_ASSET_PURCHASE_REPAIR"]
    assert classification["context_resolution_kind"] == "EXPLICIT_TABLE_TITLE"


def _primary_balance_sheet(*tables: dict) -> dict:
    page = _page(
        {
            "content_kind": "PRIMARY_STATEMENT",
            "narratives_exact": [],
            "statement_type": "BALANCE_SHEET",
            "tables": list(tables),
            "title_exact": "Bảng cân đối kế toán",
        }
    )
    page["status"] = "PRIMARY_FINANCIAL_STATEMENT"
    return page


def test_primary_fallback_maps_unique_shallow_root_and_omits_blank_child() -> None:
    table = _table(
        None,
        [
            _row(
                "Tài sản Có khác",
                kind="SUBTOTAL",
                values=["100", "90"],
                hierarchy=["Tài sản Có khác"],
            ),
            _row(
                "Tài sản Có khác",
                values=["100", "90"],
                hierarchy=["Tài sản Có khác", "Tài sản Có khác"],
            ),
            _row(
                "Các khoản phải thu",
                values=["70", "60"],
                hierarchy=["Tài sản Có khác", "Các khoản phải thu"],
            ),
            _row(
                "Chi phí trả trước",
                values=[None, None],
                hierarchy=["Tài sản Có khác", "Chi phí trả trước"],
            ),
        ],
    )
    page = _primary_balance_sheet(table)
    cluster, candidate = _evaluate(page)

    assert cluster["owner_receipt"]["alias"] == (
        "EXACT_PRIMARY_STATEMENT_SOURCE_RESULT_FALLBACK"
    )
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert set(by_role) == {"FAMILY_ROOT_TOTAL", "RECEIVABLES"}
    assert [cell["coefficient"] for cell in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [
        100,
        90,
    ]
    assert by_role["FAMILY_ROOT_TOTAL"]["state"] == (
        "SOURCE_VISIBLE_PRIMARY_STATEMENT_EXACT_RESULT"
    )
    classification = candidate["closure_receipt"]["table_receipts"][0]["classification"]
    assert classification["family_root_row_ordinals"] == [1]
    assert classification["primary_statement_source_result_receipt"][
        "candidate_row_ordinals"
    ] == [1, 2]


def test_primary_fallback_rejects_multiple_source_result_tables() -> None:
    first = _table(
        None,
        [_row("Tài sản Có khác", kind="SUBTOTAL", hierarchy=["Tài sản Có khác"])],
    )
    second = _table(
        None,
        [_row("Tài sản Có khác", kind="SUBTOTAL", hierarchy=["Tài sản Có khác"])],
    )
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[
            _record(_primary_balance_sheet(first, second), ordinal=4, page_number=1)
        ],
        compiled_specs=_compiled(),
    )

    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert cluster["reasons"] == [
        "MULTIPLE_PRIMARY_STATEMENT_SOURCE_RESULT_FALLBACK_POPULATIONS"
    ]


def _adapter_region(
    *, page_json_version_id: str, physical_page: int, selected_page_ordinal: int
) -> dict:
    return {
        "component_roles": [],
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "fragment_ordinal": selected_page_ordinal,
        "page_json_version_id": page_json_version_id,
        "physical_page": physical_page,
        "section_id": "s1",
        "selected_page_ordinal": selected_page_ordinal,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
        "table_id": "t1",
    }


def _adapter_continuation_pages(*, sender_marker: str = "NONE") -> tuple[dict, dict]:
    prior = _table(
        "14. Tài sản Có khác",
        [_row("Các khoản phải thu", values=["50", "40"])],
        continuation=sender_marker,
    )
    receiver = _table(
        None,
        [
            _row(
                "Tài sản Có khác",
                kind="GROUP",
                values=[None, None],
            ),
            _row(
                "Chi phí trả trước",
                values=["30", "20"],
                hierarchy=["Tài sản Có khác", "Chi phí trả trước"],
            ),
            _row(
                "Tài sản khác",
                values=["30", "20"],
                hierarchy=["Tài sản Có khác", "Tài sản khác"],
            ),
            _row("Tổng cộng", kind="TOTAL", values=["110", "80"]),
        ],
        continuation="CONTINUES_FROM_PREVIOUS_PAGE",
        columns=_columns(blank=True),
    )
    receiver["unit_exact"] = None
    return (
        _page(_section("14. Tài sản Có khác", prior)),
        _page(_section(None, receiver)),
    )


def test_family22_indexed_adapter_replays_one_sided_continuation_without_mutating_source() -> None:
    compiled = _compiled()
    first_id = "gfpstorev1:json:" + "7" * 64
    second_id = "gfpstorev1:json:" + "8" * 64
    first, second = _adapter_continuation_pages()
    pages = {1: {first_id: first, second_id: second}}
    first_classification = classify_gemini_json_multitable_hierarchical_table_v1(
        first,
        first["sections"][0],
        first["sections"][0]["tables"][0],
        compiled_specs=compiled,
    )
    second_classification = classify_gemini_json_multitable_hierarchical_table_v1(
        second,
        second["sections"][0],
        second["sections"][0]["tables"][0],
        compiled_specs=compiled,
    )
    reason = f"UNCONSUMED_MONEY_TABLE_INSIDE_OWNER_FENCE:{second_id}:s1:t1"
    cluster_material = {
        "component_regions": [],
        "declared_money_table_inventory": [
            {
                "classification": first_classification,
                "disposition": "SELECTED_FAMILY_COMPONENT",
                "page_json_version_id": first_id,
                "physical_page": 18,
                "position": [1, 1, 1],
                "section_id": "s1",
                "table_id": "t1",
            },
            {
                "classification": second_classification,
                "disposition": "UNCONSUMED_MONEY_TABLE_INSIDE_OWNER_FENCE",
                "page_json_version_id": second_id,
                "physical_page": 19,
                "position": [2, 1, 1],
                "section_id": "s1",
                "table_id": "t1",
            },
        ],
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "reasons": [reason],
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
        "status": UNRESOLVED,
    }
    cluster = {
        **cluster_material,
        "cluster_id": "gjmthfcv1:cluster:"
        + canonical_json_sha256_v1(cluster_material),
    }
    document = {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }
    selected_pages = [
        {
            **document,
            "page_json_version_id": first_id,
            "physical_page": 18,
            "selected_page_ordinal": 1,
        },
        {
            **document,
            "page_json_version_id": second_id,
            "physical_page": 19,
            "selected_page_ordinal": 2,
        },
    ]
    indexed = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=[document],
        selected_page_axis=selected_pages,
        document_clusters=[cluster],
        query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]),
    )
    indexed_before = canonical_clone_v1(indexed)
    source_before = canonical_clone_v1(pages[1])

    adapted, receipts = adapt_gemini_json_other_assets_indexed_query_evidence_v1(
        indexed,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    replayed, replayed_receipts = (
        adapt_gemini_json_other_assets_indexed_query_evidence_v1(
            indexed,
            page_json_by_document=pages,
            compiled_specs=compiled,
        )
    )

    assert same_typed_json_v1(pages[1], source_before)
    assert same_typed_json_v1(indexed, indexed_before)
    assert same_typed_json_v1(adapted, replayed)
    assert same_typed_json_v1(receipts, replayed_receipts)
    assert len(adapted["accepted_clusters"]) == 1
    query_adapter_receipt = adapted["accepted_clusters"][0][
        "other_assets_query_adapter_receipt"
    ]
    assert len(query_adapter_receipt["continuation_receipts"]) == 1
    assert query_adapter_receipt["continuation_receipts"][0][
        "sender_marker_rule"
    ] == "ADJACENT_SENDER_OMITTED_ON_NEXT_MARKER"
    regions = adapted["accepted_clusters"][0]["component_regions"]
    query_receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        regions
    )
    candidate = evaluate_gemini_json_other_assets_family_cluster_v1(
        regions=regions,
        page_json_by_version=pages[1],
        compiled_specs=compiled,
        query_receipt=query_receipt,
    )
    replay = validate_gemini_json_other_assets_family_candidate_replay_v1(
        candidate,
        regions=regions,
        page_json_by_version=pages[1],
        compiled_specs=compiled,
        query_receipt=query_receipt,
    )
    assert same_typed_json_v1(candidate, replay)
    assert candidate["status"] == READY
    assert candidate["closure_receipt"]["other_assets_adapter_receipt"][
        "continuation_receipts"
    ][0]["sender_marker_rule"] == "ADJACENT_SENDER_OMITTED_ON_NEXT_MARKER"
    assert same_typed_json_v1(pages[1], source_before)


def test_family22_continuation_receipt_is_bounded_and_accepts_exact_two_sided_marker() -> None:
    compiled = _compiled()
    first_id = "gfpstorev1:json:" + "7" * 64
    second_id = "gfpstorev1:json:" + "8" * 64
    first, second = _adapter_continuation_pages(sender_marker="CONTINUES_ON_NEXT_PAGE")
    page_axis = {first_id: first, second_id: second}
    prior_region = _adapter_region(
        page_json_version_id=first_id,
        physical_page=18,
        selected_page_ordinal=1,
    )
    receiver_region = _adapter_region(
        page_json_version_id=second_id,
        physical_page=19,
        selected_page_ordinal=2,
    )

    receipt = _one_sided_continuation_receipt_v1(
        prior_region=prior_region,
        receiver_region=receiver_region,
        page_json_by_version=page_axis,
        compiled_specs=compiled,
    )
    assert receipt is not None
    assert receipt["sender_marker_rule"] == "EXACT_TWO_SIDED_EXPLICIT_CONTINUATION"

    nonadjacent = {**receiver_region, "physical_page": 20}
    assert (
        _one_sided_continuation_receipt_v1(
            prior_region=prior_region,
            receiver_region=nonadjacent,
            page_json_by_version=page_axis,
            compiled_specs=compiled,
        )
        is None
    )
    conflicting = canonical_clone_v1(second)
    conflicting["sections"][0]["tables"][0]["columns"] = list(
        reversed(_columns())
    )
    assert (
        _one_sided_continuation_receipt_v1(
            prior_region=prior_region,
            receiver_region=receiver_region,
            page_json_by_version={first_id: first, second_id: conflicting},
            compiled_specs=compiled,
        )
        is None
    )


def test_family22_split_interest_details_never_become_f22_source_mappings() -> None:
    compiled = _compiled()
    first_id = "gfpstorev1:json:" + "b" * 64
    second_id = "gfpstorev1:json:" + "c" * 64
    prior_table = _table(
        "14. Tài sản Có khác",
        [
            _row("Các khoản phải thu", values=["722.787", "617.690"]),
            _row("Các khoản lãi, phí phải thu", values=["3.237.776", "2.560.595"]),
        ],
        continuation="CONTINUES_ON_NEXT_PAGE",
    )
    receiver_table = _table(
        None,
        [
            _row("- Lãi phải thu từ cho vay", values=["2.580.853", "2.053.697"]),
            _row("- Lãi phải thu từ chứng khoán đầu tư", values=["459.313", "345.606"]),
            _row("- Lãi phải thu từ tiền gửi", values=["195.391", "155.747"]),
            _row(
                "- Lãi phải thu từ công cụ tài chính phái sinh",
                values=["2.219", "5.545"],
            ),
            _row("- Phí phải thu", values=["-", "-"]),
            _row("Tài sản thuế TNDN hoãn lại", values=["-", "-"]),
            _row(
                "Tài sản Có khác",
                kind="GROUP",
                values=["206.753", "157.316"],
            ),
            _row(
                "- Chi phí chờ phân bổ",
                values=["130.517", "91.362"],
                hierarchy=["Tài sản Có khác", "- Chi phí chờ phân bổ"],
            ),
            _row(
                "- Tài sản gán nợ đã chuyển quyền sở hữu cho TCTD, đang chờ xử lý",
                values=["13.578", "13.576"],
                hierarchy=[
                    "Tài sản Có khác",
                    "- Tài sản gán nợ đã chuyển quyền sở hữu cho TCTD, đang chờ xử lý",
                ],
            ),
            _row(
                "- Vật liệu, công cụ lao động",
                values=["14.176", "12.557"],
                hierarchy=["Tài sản Có khác", "- Vật liệu, công cụ lao động"],
            ),
            _row(
                "- Tài sản Có khác",
                values=["48.482", "39.821"],
                hierarchy=["Tài sản Có khác", "- Tài sản Có khác"],
            ),
            _row(
                "Các khoản dự phòng rủi ro cho các tài sản có nội bảng khác",
                values=["(13.548)", "(13.548)"],
            ),
            _row("Tổng cộng", kind="TOTAL", values=["4.153.768", "3.322.053"]),
        ],
        continuation="CONTINUES_FROM_PREVIOUS_PAGE",
        columns=_columns(blank=True),
    )
    receiver_table["unit_exact"] = None
    first = _page(_section("14. Tài sản Có khác", prior_table))
    second = _page(_section(None, receiver_table))
    regions = [
        {
            **_adapter_region(
                page_json_version_id=first_id,
                physical_page=18,
                selected_page_ordinal=1,
            ),
            "component_roles": [
                "INTEREST_FEE_RECEIVABLES",
                "OTHER_ASSET_BRANCH",
                "RECEIVABLES",
            ],
            "fragment_ordinal": 1,
        },
        {
            **_adapter_region(
                page_json_version_id=second_id,
                physical_page=19,
                selected_page_ordinal=2,
            ),
            "component_roles": [
                "COLLATERAL_ASSET",
                "MATERIAL",
                "OTHER_ASSET",
                "OTHER_ASSET_BRANCH",
                "PREPAID_COST",
            ],
            "fragment_ordinal": 2,
        },
    ]
    source_pages = {first_id: first, second_id: second}
    source_before = canonical_clone_v1(source_pages)
    query_receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        regions
    )

    candidate = evaluate_gemini_json_other_assets_family_cluster_v1(
        regions=regions,
        page_json_by_version=source_pages,
        compiled_specs=compiled,
        query_receipt=query_receipt,
    )

    assert candidate["status"] == READY
    assert not {982, 983, 984, 985, 986}.intersection(
        mapping["report_norm_id"] for mapping in candidate["mappings"]
    )
    forbidden_refs = []
    for mapping in candidate["mappings"]:
        for source_ref in mapping["source_refs"]:
            locator = source_ref["locator"]
            if (
                locator["page_json_version_id"] == second_id
                and locator["table_id"] == "t1"
                and source_ref["row_ordinal"] in range(1, 6)
            ):
                forbidden_refs.append(source_ref)
    assert forbidden_refs == []
    assert same_typed_json_v1(source_pages, source_before)


def test_family22_exact_provision_control_is_source_only_and_fail_closed() -> None:
    compiled = _compiled()
    page_id = "gfpstorev1:json:" + "9" * 64
    table = _table(
        "15.2 Dự phòng rủi ro cho các tài sản Có khác",
        [
            _row("Số đầu năm", values=["58", "38"]),
            _row("Trích lập trong năm", values=["148", "20"]),
            _row("Số cuối năm", kind="TOTAL", values=["206", "58"]),
        ],
    )
    section = _section(
        "THUYẾT MINH BÁO CÁO TÀI CHÍNH (Tiếp theo)",
        table,
    )
    page = _page(section)
    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        page, section, table, compiled_specs=compiled
    )
    region = _adapter_region(
        page_json_version_id=page_id,
        physical_page=43,
        selected_page_ordinal=1,
    )
    receipt = _exact_provision_control_receipt_v1(
        region=region,
        page_json_by_version={page_id: page},
        classification=classification,
    )
    assert receipt is not None
    assert receipt["control_kind"] == (
        "TWO_PERIOD_PROVISION_ONLY_WITH_NO_SCHEMA_ROLE_HIT"
    )
    assert receipt["disposition"] == (
        "PROVISION_ONLY_POPULATION_OUTSIDE_FAMILY22_SCHEMA_SOURCE_ONLY"
    )
    assert receipt["table_title_exact"] == (
        "15.2 Dự phòng rủi ro cho các tài sản Có khác"
    )
    assert receipt["total_row_ordinals"] == [3]
    assert receipt["selected_mapping_money_column_ordinals"] == []

    ordinary = _table(
        "11.4 Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác",
        [_row("Tài sản Có khác", kind="TOTAL")],
    )
    ordinary_section = _section("Tài sản Có khác", ordinary)
    ordinary_page = _page(ordinary_section)
    ordinary_classification = classify_gemini_json_multitable_hierarchical_table_v1(
        ordinary_page,
        ordinary_section,
        ordinary,
        compiled_specs=compiled,
    )
    assert (
        _exact_provision_control_receipt_v1(
            region=region,
            page_json_by_version={page_id: ordinary_page},
            classification=ordinary_classification,
        )
        is None
    )


def test_family22_provision_risk_subset_receipt_inventories_every_original_cell() -> None:
    compiled = _compiled()
    page_id = "gfpstorev1:json:" + "a" * 64
    table = _table(
        "Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác",
        [
            _row("Các khoản phải thu bên ngoài", values=["728", "700", "701", "699"]),
            _row(
                "Tài sản Có khác",
                values=["51", "51", "50", "50"],
            ),
            _row("Tổng cộng", kind="TOTAL", values=["779", "751", "751", "749"]),
        ],
    )
    table["columns"] = [
        {
            "header_path_exact": ["31/12/2025", "Số dư tài sản có Triệu VND"],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": ["31/12/2025", "Dự phòng Triệu VND"],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": ["31/12/2024", "Số dư tài sản có Triệu VND"],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": ["31/12/2024", "Dự phòng Triệu VND"],
            "value_kind": "MONEY",
        },
    ]
    section = _section(
        "Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác", table
    )
    page = _page(section)
    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        page, section, table, compiled_specs=compiled
    )
    region = _adapter_region(
        page_json_version_id=page_id,
        physical_page=57,
        selected_page_ordinal=1,
    )

    receipt = _exact_provision_control_receipt_v1(
        region=region,
        page_json_by_version={page_id: page},
        classification=classification,
    )
    assert receipt is not None
    assert receipt["disposition"] == (
        "SECONDARY_PROVISION_RISK_SUBSET_CONTROL_SOURCE_ONLY"
    )
    assert receipt["gross_money_column_ordinals"] == [1, 3]
    assert receipt["provision_money_column_ordinals"] == [2, 4]
    assert receipt["selected_mapping_money_column_ordinals"] == []
    assert len(receipt["table_row_axis"]) == 3
    assert receipt["table_row_axis"][0]["values_exact"] == [
        "728",
        "700",
        "701",
        "699",
    ]
    by_role = {item["role"]: item for item in receipt["role_observation_axis"]}
    assert [
        item["source_text"] for item in by_role["EXTERNAL_RECEIVABLES"]["gross_source_cells"]
    ] == ["728", "701"]
    assert [
        item["source_text"]
        for item in by_role["EXTERNAL_RECEIVABLES"]["provision_source_cells"]
    ] == ["700", "699"]

    changed = canonical_clone_v1(page)
    changed["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "729"
    changed_receipt = _exact_provision_control_receipt_v1(
        region=region,
        page_json_by_version={page_id: changed},
        classification=classification,
    )
    assert changed_receipt is not None
    assert changed_receipt["receipt_id"] != receipt["receipt_id"]

    for malformed in ("SWAPPED", "DUPLICATE", "ORDINARY", "AMBIGUOUS"):
        malformed_page = canonical_clone_v1(page)
        malformed_classification = canonical_clone_v1(classification)
        if malformed == "SWAPPED":
            columns = malformed_page["sections"][0]["tables"][0]["columns"]
            columns[0], columns[1] = columns[1], columns[0]
        elif malformed == "DUPLICATE":
            malformed_page["sections"][0]["tables"][0]["columns"][1][
                "header_path_exact"
            ] = ["31/12/2025", "Số dư tài sản có Triệu VND"]
        elif malformed == "ORDINARY":
            malformed_page["sections"][0]["title_exact"] = "Tài sản Có khác"
            malformed_page["sections"][0]["tables"][0]["title_exact"] = (
                "Tài sản Có khác"
            )
        else:
            malformed_classification["ambiguous_rows"] = [{"row_ordinal": 1}]
        assert (
            _exact_provision_control_receipt_v1(
                region=region,
                page_json_by_version={page_id: malformed_page},
                classification=malformed_classification,
            )
            is None
        )
