from __future__ import annotations

from bctc_ai.core.text import retrieval_key
from bctc_ai.mapping.alignment_v2 import MappingDecisionStatus
from bctc_ai.mapping.ordered_subgraph import (
    MappingBlockContext,
    PdfGraphRow,
    align_ordered_subgraph,
    build_schema_graph,
    load_ordered_subgraph_policy,
)
from bctc_ai.mapping.scope import load_scope_policy
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import SchemaItem, load_all


def _schema(
    specifications: list[tuple[int, str, int | None, int | None]],
) -> list[SchemaItem]:
    items = [
        SchemaItem(
            schema_id=schema_id,
            canonical_name=label,
            normalized_name=retrieval_key(label),
            statement_type="CDKT",
            display_order=order,
            parent_id=parent_id,
            hierarchy_level=level,
        )
        for order, (schema_id, label, parent_id, level) in enumerate(specifications)
    ]
    for index, item in enumerate(items):
        item.previous_id = items[index - 1].schema_id if index else None
        item.next_id = items[index + 1].schema_id if index + 1 < len(items) else None
    by_id = {item.schema_id: item for item in items}
    for item in items:
        if item.parent_id is not None:
            by_id[item.parent_id].children.append(item.schema_id)
    return items


def _policies(project_root):
    mapping = load_ordered_subgraph_policy(project_root / "config/mapping/ordered-subgraph-v1.yaml")
    scope = load_scope_policy(project_root / "config/mapping/scope_exclusions.yaml")
    return mapping, scope


def test_six_pdf_rows_align_to_three_schema_rows_without_forcing_extras(project_root):
    schema = _schema(
        [
            (900, "Tài sản cố định", None, 0),
            (50, "Nguyên giá tài sản cố định", 900, 1),
            (700, "Hao mòn tài sản cố định", 900, 1),
            (10, "Giá trị còn lại", 900, 1),
            (800, "Tổng tài sản", None, 0),
        ]
    )
    graph = build_schema_graph(schema, "CDKT")
    rows = [
        PdfGraphRow("p0", "Tài sản cố định", 0, "CDKT", "CONSOLIDATED", table_id="t"),
        PdfGraphRow(
            "p1",
            "Nguyên giá tài sản cố định",
            1,
            "CDKT",
            "CONSOLIDATED",
            table_id="t",
            parent_row_id="p0",
            indentation_level=1,
        ),
        PdfGraphRow("p2", "Chi phí xây dựng dở dang", 2, "CDKT", "CONSOLIDATED", table_id="t"),
        PdfGraphRow(
            "p3",
            "Hao mòn tài sản cố định",
            3,
            "CDKT",
            "CONSOLIDATED",
            table_id="t",
            parent_row_id="p0",
            indentation_level=1,
        ),
        PdfGraphRow("p4", "Thuyết minh bổ sung", 4, "CDKT", "CONSOLIDATED", table_id="t"),
        PdfGraphRow(
            "p5",
            "Giá trị còn lại",
            5,
            "CDKT",
            "CONSOLIDATED",
            table_id="t",
            parent_row_id="p0",
            indentation_level=1,
        ),
    ]
    policy, scope = _policies(project_root)
    result = align_ordered_subgraph(
        rows,
        graph,
        context=MappingBlockContext(
            statement_type="CDKT",
            scope="CONSOLIDATED",
            table_id="t",
            schema_cluster_ids=(50, 700, 10),
            block_is_exhaustive_for_schema_cluster=True,
            minimum_schema_coverage=1.0,
        ),
        policy=policy,
        scope_policy=scope,
    )

    assert result.status is MappingDecisionStatus.RESOLVED
    assert result.automatic_selection_allowed
    assert [(match.row_id, match.schema_id) for match in result.best_path.matches] == [
        ("p1", 50),
        ("p3", 700),
        ("p5", 10),
    ]
    assert result.best_path.skipped_pdf_row_ids == ("p0", "p2", "p4")
    assert result.best_path.skipped_schema_ids == ()
    assert result.best_path.structural_issues == ()
    assert result.score_margin >= policy.minimum_path_margin
    assert [item.status for item in result.row_dispositions if item.schema_id is None] == [
        "UNMATCHED_PDF_ROW_RETAINED",
        "UNMATCHED_PDF_ROW_RETAINED",
        "UNMATCHED_PDF_ROW_RETAINED",
    ]
    assert result.search.algorithm == "K_BEST_MONOTONE_DYNAMIC_PROGRAMMING_FAIL_CLOSED"
    assert result.search.dp_cells == 28
    assert result.search.generated_states < 5_000


def test_duplicate_label_is_resolved_by_mapped_parent_and_neighbor_cluster(project_root):
    schema = _schema(
        [
            (100, "Tài sản cố định hữu hình", None, 0),
            (901, "Nguyên giá tài sản cố định", 100, 1),
            (902, "Hao mòn tài sản cố định", 100, 1),
            (50, "Tài sản cố định vô hình", None, 0),
            (801, "Nguyên giá tài sản cố định", 50, 1),
            (802, "Hao mòn tài sản cố định", 50, 1),
        ]
    )
    graph = build_schema_graph(schema, "CDKT")
    rows = [
        PdfGraphRow("r0", "Tài sản cố định vô hình", 0, "CDKT", "CONSOLIDATED", table_id="t"),
        PdfGraphRow(
            "r1",
            "Nguyên giá tài sản cố định",
            1,
            "CDKT",
            "CONSOLIDATED",
            table_id="t",
            parent_row_id="r0",
            indentation_level=1,
        ),
        PdfGraphRow(
            "r2",
            "Hao mòn tài sản cố định",
            2,
            "CDKT",
            "CONSOLIDATED",
            table_id="t",
            parent_row_id="r0",
            indentation_level=1,
        ),
    ]
    policy, scope = _policies(project_root)
    result = align_ordered_subgraph(
        rows,
        graph,
        context=MappingBlockContext(
            "CDKT",
            "CONSOLIDATED",
            "t",
            (100, 901, 902, 50, 801, 802),
            minimum_schema_coverage=0.5,
        ),
        policy=policy,
        scope_policy=scope,
    )

    assert result.status is MappingDecisionStatus.RESOLVED
    assert [(match.row_id, match.schema_id) for match in result.best_path.matches] == [
        ("r0", 50),
        ("r1", 801),
        ("r2", 802),
    ]


def test_verified_parent_rejects_wrong_same_label_even_with_semantic_score(project_root):
    schema = _schema(
        [
            (100, "Hữu hình", None, 0),
            (901, "Nguyên giá", 100, 1),
            (50, "Vô hình", None, 0),
            (801, "Nguyên giá", 50, 1),
        ]
    )
    graph = build_schema_graph(schema, "CDKT")
    row = PdfGraphRow(
        "r",
        "Nguyên giá",
        0,
        "CDKT",
        "CONSOLIDATED",
        table_id="t",
        parent_schema_id=50,
        indentation_level=1,
    )
    policy, scope = _policies(project_root)
    result = align_ordered_subgraph(
        [row],
        graph,
        context=MappingBlockContext("CDKT", "CONSOLIDATED", "t", (901, 801)),
        policy=policy,
        scope_policy=scope,
        accounting_semantic_scores={("r", 901): 1.0, ("r", 801): 0.0},
    )

    assert result.status is MappingDecisionStatus.RESOLVED
    assert result.best_path.matches[0].schema_id == 801
    assert all(match.schema_id != 901 for path in result.ranked_paths for match in path.matches)


def test_indistinguishable_duplicate_labels_abstain_on_path_margin(project_root):
    schema = _schema(
        [
            (900, "Khác", None, 0),
            (10, "Khác", None, 0),
        ]
    )
    graph = build_schema_graph(schema, "CDKT")
    policy, scope = _policies(project_root)
    result = align_ordered_subgraph(
        [PdfGraphRow("r", "Khác", 0, "CDKT", "CONSOLIDATED", table_id="t")],
        graph,
        context=MappingBlockContext("CDKT", "CONSOLIDATED", "t", (900, 10)),
        policy=policy,
        scope_policy=scope,
    )

    assert result.status is MappingDecisionStatus.AMBIGUOUS_MAPPING
    assert not result.automatic_selection_allowed
    assert result.score_margin == 0
    assert {path.matches[0].schema_id for path in result.ranked_paths[:2]} == {900, 10}
    assert "decisive margin" in result.reason


def test_schema_graph_and_alignment_use_workbook_order_not_numeric_id(project_root):
    schema = _schema(
        [
            (4337, "Vốn đầu tư của chủ sở hữu", None, 0),
            (4373, "Vốn đầu tư XDCB", None, 0),
            (4338, "Thặng dư vốn cổ phần", None, 0),
        ]
    )
    graph = build_schema_graph(schema, "CDKT")
    policy, scope = _policies(project_root)
    rows = [
        PdfGraphRow("r1", schema[0].canonical_name, 1, "CDKT", "CONSOLIDATED", table_id="t"),
        PdfGraphRow("r2", schema[1].canonical_name, 2, "CDKT", "CONSOLIDATED", table_id="t"),
        PdfGraphRow("r3", schema[2].canonical_name, 3, "CDKT", "CONSOLIDATED", table_id="t"),
    ]
    result = align_ordered_subgraph(
        rows,
        graph,
        context=MappingBlockContext(
            "CDKT", "CONSOLIDATED", "t", (4338, 4337, 4373), minimum_schema_coverage=1.0
        ),
        policy=policy,
        scope_policy=scope,
    )

    assert [node.schema_id for node in graph.nodes] == [4337, 4373, 4338]
    assert [match.schema_id for match in result.best_path.matches] == [4337, 4373, 4338]
    assert result.status is MappingDecisionStatus.RESOLVED


def test_scope_policy_is_required_and_schema_absence_is_not_assumed(project_root):
    schema = _schema([(10, "Tiền", None, 0), (900, "Vàng", None, 0)])
    graph = build_schema_graph(schema, "CDKT")
    policy, _scope = _policies(project_root)
    result = align_ordered_subgraph(
        [PdfGraphRow("r", "Tiền", 0, "CDKT", "CONSOLIDATED", table_id="t")],
        graph,
        context=MappingBlockContext("CDKT", "CONSOLIDATED", "t", (10, 900)),
        policy=policy,
        scope_policy=None,
    )

    assert result.status is MappingDecisionStatus.AMBIGUOUS_MAPPING
    assert result.best_path is None
    assert all(
        item.status == "UNMATCHED_SCHEMA_NODE_IN_BLOCK" for item in result.schema_dispositions
    )


def test_numbering_is_structural_evidence_and_mismatch_cannot_auto_resolve(project_root):
    schema = _schema([(900, "Khoản khác", None, 0), (10, "Khoản khác", None, 0)])
    graph = build_schema_graph(schema, "CDKT")
    policy, scope = _policies(project_root)
    result = align_ordered_subgraph(
        [
            PdfGraphRow(
                "r",
                "Khoản khác",
                0,
                "CDKT",
                "CONSOLIDATED",
                table_id="t",
                numbering="II",
            )
        ],
        graph,
        context=MappingBlockContext("CDKT", "CONSOLIDATED", "t", (900, 10)),
        policy=policy,
        scope_policy=scope,
        schema_numbering={900: "I", 10: "II"},
    )

    assert result.status is MappingDecisionStatus.RESOLVED
    assert result.best_path.matches[0].schema_id == 10
    assert result.best_path.matches[0].features.numbering_match is True
    wrong_path = next(path for path in result.ranked_paths if path.matches[0].schema_id == 900)
    assert "numbering conflicts" in wrong_path.structural_issues[0]


def test_real_template_graph_preserves_hierarchy_and_non_numeric_workbook_order(project_root):
    _workbooks, schema = load_all(project_root / "template", project_root)
    _registry, hierarchy = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml", project_root, schema
    )
    apply_hierarchy_reference(schema, hierarchy)
    graph = build_schema_graph(schema, "CDKT")
    by_id = graph.by_id()

    assert len(graph.nodes) == 77
    assert [node.schema_id for node in graph.nodes[64:67]] == [4337, 4373, 4338]
    assert by_id[4367].parent_id == 4328
    assert by_id[4369].parent_id == 4329
    assert by_id[4371].parent_id == 4330
    assert len(graph.graph_sha256) == 64


def test_scope_exclusion_prevents_exact_off_balance_label_from_matching(project_root):
    schema = _schema([(5701, "Bảo lãnh vay vốn", None, 0)])
    graph = build_schema_graph(schema, "CDKT")
    policy, scope = _policies(project_root)
    result = align_ordered_subgraph(
        [
            PdfGraphRow(
                "r",
                "Bảo lãnh vay vốn",
                0,
                "CDKT",
                "CONSOLIDATED",
                section_heading="CÁC CHỈ TIÊU NGOÀI BÁO CÁO TÌNH HÌNH TÀI CHÍNH",
                table_id="t",
            )
        ],
        graph,
        context=MappingBlockContext(
            "CDKT",
            "CONSOLIDATED",
            "t",
            (5701,),
            section_heading="CÁC CHỈ TIÊU NGOÀI BÁO CÁO TÌNH HÌNH TÀI CHÍNH",
        ),
        policy=policy,
        scope_policy=scope,
    )

    assert result.status is MappingDecisionStatus.OUT_OF_SCOPE_FOR_TARGET_TEMPLATE
    assert result.best_path.matches == ()
    assert result.row_dispositions[0].status == "OUT_OF_SCOPE_FOR_TARGET_TEMPLATE"


def test_not_observed_requires_resolved_exhaustive_block(project_root):
    schema = _schema([(10, "Tiền", None, 0), (900, "Vàng", None, 0)])
    graph = build_schema_graph(schema, "CDKT")
    policy, scope = _policies(project_root)
    row = PdfGraphRow("r", "Tiền", 0, "CDKT", "CONSOLIDATED", table_id="t")
    exhaustive = align_ordered_subgraph(
        [row],
        graph,
        context=MappingBlockContext(
            "CDKT",
            "CONSOLIDATED",
            "t",
            (10, 900),
            block_is_exhaustive_for_schema_cluster=True,
        ),
        policy=policy,
        scope_policy=scope,
    )
    non_exhaustive = align_ordered_subgraph(
        [row],
        graph,
        context=MappingBlockContext("CDKT", "CONSOLIDATED", "t", (10, 900)),
        policy=policy,
        scope_policy=scope,
    )

    assert exhaustive.status is MappingDecisionStatus.RESOLVED
    assert exhaustive.schema_dispositions[1].status == "NOT_OBSERVED"
    assert non_exhaustive.schema_dispositions[1].status == "UNMATCHED_SCHEMA_NODE_IN_BLOCK"
