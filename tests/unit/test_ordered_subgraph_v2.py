from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest
from rapidfuzz.fuzz import ratio

from bctc_ai.core.text import retrieval_key
from bctc_ai.mapping.ordered_subgraph_v2 import (
    MappingRunStatus,
    OrderedSubgraphV2Error,
    RowMappingRecordV2,
    RowMappingStatus,
    SchemaProjectionV2,
    SourceStructureRowV2,
    _enforce_selected_direct_parent_closure,
    align_ordered_subgraph_v2,
    build_schema_projection_v2,
    load_ordered_subgraph_v2_policy,
    load_ordered_subgraph_v2_policy_bytes,
    result_json,
)
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import SchemaItem, load_all


def _policy(project_root: Path):
    return load_ordered_subgraph_v2_policy(project_root / "config/mapping/ordered-subgraph-v2.yaml")


def _projection(specifications: list[dict[str, object]]) -> SchemaProjectionV2:
    items: list[SchemaItem] = []
    for order, specification in enumerate(specifications):
        label = str(specification["label"])
        item = SchemaItem(
            schema_id=int(specification["id"]),
            canonical_name=label,
            normalized_name=retrieval_key(label),
            statement_type="CDKT",
            display_order=order,
            parent_id=(
                None if specification.get("parent") is None else int(specification["parent"])
            ),
            hierarchy_level=(
                None if specification.get("level") is None else int(specification["level"])
            ),
            structural_aliases=[str(item) for item in specification.get("aliases", ())],
            historical_aliases=[str(item) for item in specification.get("history", ())],
            scope=[str(item) for item in specification.get("scopes", ("SEPARATE", "CONSOLIDATED"))],
        )
        items.append(item)
    by_id = {item.schema_id: item for item in items}
    for item in items:
        if item.parent_id is not None:
            by_id[item.parent_id].children.append(item.schema_id)
    return build_schema_projection_v2(items, "CDKT")


def _row(
    row_id: str,
    order: int,
    label: str,
    role: str,
    *,
    two_streams: bool = False,
    parent: str | None = None,
    relation: str = "NONE",
    scope: str = "UNKNOWN",
) -> SourceStructureRowV2:
    labels = {"vietocr": label}
    if two_streams:
        labels["deepseek"] = label
    return SourceStructureRowV2(
        row_id=row_id,
        order=order,
        labels_by_reader=labels,
        row_role=role,
        parent_row_id=parent,
        relation_type=relation,
        report_scope=scope,
    )


def _mapped(result) -> dict[str, int | None]:
    return {item.row_id: item.selected_report_norm_id for item in result.row_mappings}


def _status(result) -> dict[str, str]:
    return {item.row_id: item.status for item in result.row_mappings}


def test_family_1_equity_interval_keeps_heading_unmatched_and_skips_4373(project_root):
    projection = _projection(
        [
            {"id": 4304, "label": "TỔNG NỢ PHẢI TRẢ", "parent": 4305, "level": 2},
            {"id": 4325, "label": "Vốn và các quỹ", "parent": 4305, "level": 2},
            {"id": 4364, "label": "Vốn của TCTD", "parent": 4325, "level": 3},
            {
                "id": 4337,
                "label": "Vốn đầu tư của chủ sở hữu",
                "parent": 4364,
                "level": 4,
                "aliases": ("a. Vốn điều lệ",),
            },
            {"id": 4373, "label": "Vốn đầu tư XDCB", "parent": 4364, "level": 4},
            {"id": 4338, "label": "Thặng dư vốn cổ phần", "parent": 4364, "level": 4},
            {
                "id": 4305,
                "label": "TỔNG NỢ PHẢI TRẢ VÀ VỐN CHỦ SỞ HỮU",
                "level": 1,
            },
        ]
    )
    rows = [
        _row("p4r12", 0, "TỔNG NỢ PHẢI TRẢ", "TOTAL"),
        _row("p4r13", 1, "VỐN CHỦ SỞ HỮU", "SECTION"),
        _row("p4r14", 2, "Vốn và các quỹ", "GROUP"),
        _row("p4r15", 3, "Vốn của TCTD", "GROUP", parent="p4r14", relation="PHYSICAL_PARENT"),
        _row("p4r16", 4, "a. Vốn điều lệ", "DETAIL", parent="p4r15", relation="PHYSICAL_PARENT"),
        _row(
            "p4r17", 5, "Thặng dư vốn cổ phần", "DETAIL", parent="p4r15", relation="PHYSICAL_PARENT"
        ),
    ]

    result = align_ordered_subgraph_v2(rows, projection, policy=_policy(project_root))

    assert result.status is MappingRunStatus.RESOLVED
    assert _mapped(result) == {
        "p4r12": 4304,
        "p4r13": None,
        "p4r14": 4325,
        "p4r15": 4364,
        "p4r16": 4337,
        "p4r17": 4338,
    }
    assert _status(result)["p4r13"] == RowMappingStatus.NO_ADMISSIBLE_PAIR.value
    assert 4373 in result.best_path.skipped_report_norm_ids
    assert all(item.selected_report_norm_id != 4373 for item in result.row_mappings)


def test_family_2_trailing_equity_total_skips_obsolete_4306(project_root):
    projection = _projection(
        [
            {"id": 4325, "label": "Vốn và các quỹ", "parent": 4305, "level": 2},
            {"id": 4343, "label": "Lợi nhuận chưa phân phối", "parent": 4325, "level": 3},
            {
                "id": 5699,
                "label": "Lợi ích cổ đông không kiểm soát",
                "parent": 4325,
                "level": 3,
            },
            {
                "id": 4306,
                "label": "LỢI ÍCH CỦA CỔ ĐÔNG THIỂU SỐ (CDKT)",
                "parent": 4305,
                "level": 2,
            },
            {
                "id": 4305,
                "label": "TỔNG NỢ PHẢI TRẢ VÀ VỐN CHỦ SỞ HỮU",
                "level": 1,
            },
        ]
    )
    rows = [
        _row("p4r20", 0, "Vốn và các quỹ", "GROUP"),
        _row(
            "p4r21",
            1,
            "Lợi nhuận chưa phân phối",
            "DETAIL",
            parent="p4r20",
            relation="PHYSICAL_PARENT",
        ),
        _row(
            "p4r22",
            2,
            "Lợi ích cổ đông không kiểm soát",
            "DETAIL",
            parent="p4r20",
            relation="PHYSICAL_PARENT",
        ),
        _row("p4r23", 3, "TỔNG VỐN CHỦ SỞ HỮU", "TOTAL"),
        _row("p4r24", 4, "TỔNG NỢ PHẢI TRẢ VÀ VỐN CHỦ SỞ HỮU", "TOTAL"),
    ]

    result = align_ordered_subgraph_v2(rows, projection, policy=_policy(project_root))

    assert result.status is MappingRunStatus.RESOLVED
    assert _mapped(result)["p4r22"] == 5699
    assert _mapped(result)["p4r23"] is None
    assert _mapped(result)["p4r24"] == 4305
    assert 4306 in result.best_path.skipped_report_norm_ids


def test_family_3_duplicate_two_stream_fixed_asset_children_never_become_anchors(project_root):
    projection = _projection(
        [
            {"id": 4328, "label": "Tài sản cố định hữu hình", "level": 3},
            {
                "id": 4367,
                "label": "Nguyên giá tài sản cố định hữu hình",
                "parent": 4328,
                "level": 4,
                "aliases": ("a. Nguyên giá TSCĐ",),
            },
            {"id": 4329, "label": "Tài sản cố định thuê tài chính", "level": 3},
            {
                "id": 4369,
                "label": "Nguyên giá tài sản cố định thuê tài chính",
                "parent": 4329,
                "level": 4,
                "aliases": ("a. Nguyên giá TSCĐ",),
            },
            {"id": 4330, "label": "Tài sản cố định vô hình", "level": 3},
            {
                "id": 4371,
                "label": "Nguyên giá tài sản cố định vô hình",
                "parent": 4330,
                "level": 4,
                "aliases": ("a. Nguyên giá TSCĐ",),
            },
        ]
    )
    rows = [
        _row("p3r4", 0, "a. Nguyên giá TSCĐ", "DETAIL", two_streams=True),
        _row("p3r5", 1, "a. Nguyên giá TSCĐ", "DETAIL", two_streams=True),
        _row("p3r8", 2, "a. Nguyên giá TSCĐ", "DETAIL", two_streams=True),
        _row("p3r9", 3, "a. Nguyên giá TSCĐ", "DETAIL", two_streams=True),
    ]

    result = align_ordered_subgraph_v2(rows, projection, policy=_policy(project_root))

    relevant = {item.row_id: item for item in result.anchors}
    assert all(
        relevant[row_id].status == "INSUFFICIENT_INDEPENDENT_STREAMS"
        for row_id in ("p3r4", "p3r5", "p3r8", "p3r9")
    )
    assert all(relevant[row_id].selected_report_norm_id is None for row_id in relevant)
    for row_id in relevant:
        assert all(
            item.margin == 0.0 and not item.valid for item in relevant[row_id].stream_diagnostics
        )


@pytest.mark.parametrize("mode", ["CROSSING", "TWO_ROWS_ONE_SCHEMA"])
def test_family_4_anchor_crossing_or_one_to_one_conflict_forces_abstention(project_root, mode):
    projection = _projection(
        [
            {"id": 10, "label": "Khoản mục Alpha"},
            {"id": 20, "label": "Khoản mục Beta"},
        ]
    )
    if mode == "CROSSING":
        rows = [
            _row("r0", 0, "Khoản mục Beta", "DETAIL", two_streams=True),
            _row("r1", 1, "Khoản mục Alpha", "DETAIL", two_streams=True),
        ]
        expected_anchor_status = "MONOTONICITY_CONFLICT"
    else:
        rows = [
            _row("r0", 0, "Khoản mục Alpha", "DETAIL", two_streams=True),
            _row("r1", 1, "Khoản mục Alpha", "DETAIL", two_streams=True),
        ]
        expected_anchor_status = "ONE_TO_ONE_CONFLICT"

    result = align_ordered_subgraph_v2(rows, projection, policy=_policy(project_root))

    assert result.status is MappingRunStatus.AMBIGUOUS_MAPPING
    assert not result.automatic_selection_allowed
    assert all(item.selected_report_norm_id is None for item in result.row_mappings)
    assert expected_anchor_status in {item.status for item in result.anchors}
    assert len(result.ranked_paths) >= 2


def test_family_5_physical_parent_adapter_relaxes_only_the_matching_child(project_root):
    projection = _projection(
        [
            {"id": 100, "label": "Nhóm hữu hình", "level": 0},
            {"id": 101, "label": "Hao mòn tài sản hữu hình", "parent": 100, "level": 1},
            {"id": 200, "label": "Nhóm vô hình", "level": 0},
            {"id": 201, "label": "Hao mòn tài sản vô hình", "parent": 200, "level": 1},
        ]
    )
    rows = [
        _row("parent", 0, "Nhóm hữu hình", "GROUP"),
        _row(
            "child",
            1,
            "Hao mòn",
            "DETAIL",
            parent="parent",
            relation="PHYSICAL_PARENT",
        ),
    ]

    result = align_ordered_subgraph_v2(rows, projection, policy=_policy(project_root))

    assert _mapped(result) == {"parent": 100, "child": 101}
    child_match = next(item for item in result.best_path.matches if item.row_id == "child")
    assert child_match.direct_parent_corroborated
    assert child_match.admissibility == "PARENT_RELAXED_BY_MAPPED_DIRECT_PARENT"
    for path in result.ranked_paths:
        path_map = {item.row_id: item.report_norm_id for item in path.matches}
        assert not (path_map.get("parent") == 100 and path_map.get("child") == 201)


def test_family_5_out_of_interval_parent_is_neutral_and_trailing_parent_is_exception(project_root):
    projection = _projection(
        [
            {"id": 100, "label": "Nhóm neo", "level": 0},
            {"id": 101, "label": "Chi tiết ngoài khoảng", "parent": 100, "level": 1},
            {"id": 4304, "label": "TỔNG NỢ PHẢI TRẢ", "level": 0},
            {"id": 102, "label": "Chi tiết sau tổng", "parent": 4304, "level": 1},
        ]
    )
    rows = [
        _row("anchor", 0, "Nhóm neo", "GROUP", two_streams=True),
        _row("outside", 1, "Chi tiết ngoài khoảng", "DETAIL"),
        _row("trailing", 2, "Chi tiết sau tổng", "DETAIL"),
    ]

    result = align_ordered_subgraph_v2(rows, projection, policy=_policy(project_root))

    assert _mapped(result)["outside"] == 101
    assert _mapped(result)["trailing"] == 102
    assert result.status is MappingRunStatus.RESOLVED


def test_family_5_trailing_exception_never_overrides_explicit_parent_conflict(project_root):
    projection = _projection(
        [
            {"id": 200, "label": "Nhóm nguồn", "level": 0},
            {"id": 202, "label": "Khoản mục phụ nhóm nguồn", "parent": 200, "level": 1},
            {"id": 4304, "label": "TỔNG NỢ PHẢI TRẢ", "level": 0},
            {"id": 201, "label": "Chi tiết", "parent": 4304, "level": 1},
        ]
    )
    rows = [
        _row("parent", 0, "Nhóm nguồn", "GROUP"),
        _row(
            "child",
            1,
            "Chi tiết",
            "DETAIL",
            parent="parent",
            relation="PHYSICAL_PARENT",
        ),
    ]

    result = align_ordered_subgraph_v2(rows, projection, policy=_policy(project_root))

    assert _mapped(result)["parent"] == 200
    assert _mapped(result)["child"] is None
    assert _status(result)["child"] == RowMappingStatus.BEST_PATH_SKIPPED.value


def test_family_6_unknown_scope_is_neutral_but_known_conflict_has_no_candidate(project_root):
    projection = _projection(
        [
            {
                "id": 10,
                "label": "Tiền mặt",
                "scopes": ("CONSOLIDATED",),
            }
        ]
    )
    unknown = align_ordered_subgraph_v2(
        [_row("u", 0, "Tiền mặt", "DETAIL", scope="UNKNOWN")],
        projection,
        policy=_policy(project_root),
    )
    conflict = align_ordered_subgraph_v2(
        [_row("c", 0, "Tiền mặt", "DETAIL", scope="SEPARATE")],
        projection,
        policy=_policy(project_root),
    )

    assert _mapped(unknown)["u"] == 10
    pair = unknown.intervals[0].candidate_pairs[0]
    assert pair.scope_compatibility == "UNKNOWN_SCOPE_NEUTRAL"
    assert _mapped(conflict)["c"] is None
    assert _status(conflict)["c"] == RowMappingStatus.NO_ADMISSIBLE_PAIR.value


def test_family_7_duplicate_label_interval_is_ambiguous_and_all_selected_ids_are_null(
    project_root,
):
    projection = _projection(
        [
            {"id": 10, "label": "Khoản khác"},
            {"id": 20, "label": "Khoản khác"},
        ]
    )
    result = align_ordered_subgraph_v2(
        [_row("r", 0, "Khoản khác", "DETAIL")],
        projection,
        policy=_policy(project_root),
    )

    record = result.row_mappings[0]
    assert result.status is MappingRunStatus.AMBIGUOUS_MAPPING
    assert record.status == RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value
    assert record.selected_report_norm_id is None
    assert record.candidate_report_norm_ids == (10, 20)
    assert len(result.intervals[0].ranked_paths) >= 2
    assert result.intervals[0].best_path.matches
    assert result.intervals[0].runner_up_path is not None
    assert result.intervals[0].score_margin == 0.0


def test_family_7_anchor_is_only_constraint_until_adjacent_interval_is_decisive(project_root):
    projection = _projection(
        [
            {"id": 1, "label": "Neo chắc chắn"},
            {"id": 10, "label": "Khoản khác"},
            {"id": 20, "label": "Khoản khác"},
        ]
    )
    rows = [
        _row("anchor", 0, "Neo chắc chắn", "DETAIL", two_streams=True),
        _row("ambiguous", 1, "Khoản khác", "DETAIL"),
    ]

    result = align_ordered_subgraph_v2(rows, projection, policy=_policy(project_root))

    anchor = next(item for item in result.anchors if item.row_id == "anchor")
    assert anchor.constraint_report_norm_id == 1
    assert anchor.status == RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value
    assert anchor.selected_report_norm_id is None
    assert _mapped(result)["anchor"] is None


def test_strong_direct_parent_never_bypasses_unresolved_parent_across_anchor(project_root):
    projection = _projection(
        [
            {"id": 1, "label": "Parent Group"},
            {"id": 2, "label": "Certain Anchor"},
            {"id": 3, "label": "Child Exact", "parent": 1},
        ]
    )
    rows = [
        _row("parent", 0, "no candidate whatsoever", "GROUP"),
        _row("anchor", 1, "Certain Anchor", "DETAIL", two_streams=True),
        _row(
            "child",
            2,
            "Child Exact",
            "DETAIL",
            parent="parent",
            relation="PHYSICAL_PARENT",
        ),
    ]

    result = align_ordered_subgraph_v2(rows, projection, policy=_policy(project_root))

    assert result.status is MappingRunStatus.RESOLVED
    assert _mapped(result) == {"parent": None, "anchor": 2, "child": None}
    assert _status(result)["child"] == RowMappingStatus.BEST_PATH_SKIPPED.value
    assert result.intervals[1].candidate_pairs
    assert not result.intervals[1].best_path.matches


def test_anchor_direct_parent_demotion_reaches_fixed_point(project_root):
    projection = _projection(
        [
            {"id": 1, "label": "Grand Root"},
            {"id": 2, "label": "Parent Branch", "parent": 1},
            {"id": 3, "label": "Child Leaf", "parent": 2},
        ]
    )
    rows = [
        _row("grand", 0, "no candidate whatsoever", "GROUP"),
        _row(
            "parent",
            1,
            "Parent Branch",
            "GROUP",
            two_streams=True,
            parent="grand",
            relation="PHYSICAL_PARENT",
        ),
        _row(
            "child",
            2,
            "Child Leaf",
            "DETAIL",
            two_streams=True,
            parent="parent",
            relation="PHYSICAL_PARENT",
        ),
    ]

    result = align_ordered_subgraph_v2(rows, projection, policy=_policy(project_root))

    anchors = {item.row_id: item for item in result.anchors}
    assert anchors["parent"].status == "DIRECT_PARENT_NOT_ANCHORED"
    assert anchors["child"].status == "DIRECT_PARENT_NOT_ANCHORED"
    assert all(item.selected_report_norm_id is None for item in result.row_mappings)


def test_two_stream_anchor_cannot_orphan_an_earlier_schema_parent(project_root):
    projection = _projection(
        [
            {"id": 1, "label": "Parent Group"},
            {"id": 2, "label": "Child Exact", "parent": 1},
        ]
    )

    result = align_ordered_subgraph_v2(
        [_row("child", 0, "Child Exact", "DETAIL", two_streams=True)],
        projection,
        policy=_policy(project_root),
    )

    anchor = result.anchors[0]
    assert anchor.status == "EARLIER_SCHEMA_PARENT_NOT_ANCHORED"
    assert anchor.selected_report_norm_id is None
    assert len(result.intervals) == 1
    assert result.intervals[0].report_norm_ids == (1, 2)
    assert result.row_mappings[0].status == RowMappingStatus.BEST_PATH_SKIPPED.value
    assert result.row_mappings[0].selected_report_norm_id is None
    assert {item.report_norm_id: item.status for item in result.schema_dispositions} == {
        1: "UNMATCHED_SCHEMA_NODE",
        2: "UNMATCHED_SCHEMA_NODE_WITH_SKIPPED_CANDIDATES",
    }


def test_earlier_compatible_parent_anchor_grounds_child_anchor(project_root):
    projection = _projection(
        [
            {"id": 1, "label": "Parent Group"},
            {"id": 2, "label": "Child Exact", "parent": 1},
        ]
    )
    rows = [
        _row("parent", 0, "Parent Group", "GROUP", two_streams=True),
        _row(
            "child",
            1,
            "Child Exact",
            "DETAIL",
            two_streams=True,
            parent="parent",
            relation="PHYSICAL_PARENT",
        ),
    ]

    result = align_ordered_subgraph_v2(rows, projection, policy=_policy(project_root))

    assert result.status is MappingRunStatus.RESOLVED
    assert result.automatic_selection_allowed
    assert _mapped(result) == {"parent": 1, "child": 2}
    assert {item.row_id: item.status for item in result.anchors} == {
        "parent": RowMappingStatus.RESOLVED_ANCHOR.value,
        "child": RowMappingStatus.RESOLVED_ANCHOR.value,
    }


def test_orphan_anchor_demotion_allows_interval_parent_and_child_path(project_root):
    projection = _projection(
        [
            {"id": 1, "label": "Parent Group"},
            {"id": 2, "label": "Child Exact", "parent": 1},
        ]
    )
    rows = [
        _row("parent", 0, "Parent Group", "GROUP"),
        _row("child", 1, "Child Exact", "DETAIL", two_streams=True),
    ]

    result = align_ordered_subgraph_v2(rows, projection, policy=_policy(project_root))

    assert result.status is MappingRunStatus.RESOLVED
    assert _mapped(result) == {"parent": 1, "child": 2}
    assert {item.row_id: item.status for item in result.anchors}["child"] == (
        "EARLIER_SCHEMA_PARENT_NOT_ANCHORED"
    )
    assert _status(result)["child"] == RowMappingStatus.RESOLVED_PATH.value


def test_unselected_anchor_boundary_nulls_conditioned_direct_child(project_root):
    projection = _projection(
        [
            {"id": 10, "label": "Duplicate"},
            {"id": 20, "label": "Duplicate"},
            {"id": 30, "label": "Parent Anchor"},
            {"id": 31, "label": "Child Exact", "parent": 30},
        ]
    )
    rows = [
        _row("ambiguous", 0, "Duplicate", "DETAIL"),
        _row("parent", 1, "Parent Anchor", "GROUP", two_streams=True),
        _row(
            "child",
            2,
            "Child Exact",
            "DETAIL",
            parent="parent",
            relation="PHYSICAL_PARENT",
        ),
    ]

    result = align_ordered_subgraph_v2(rows, projection, policy=_policy(project_root))

    assert result.status is MappingRunStatus.AMBIGUOUS_MAPPING
    assert not result.automatic_selection_allowed
    assert _mapped(result)["parent"] is None
    assert _mapped(result)["child"] is None
    assert _status(result)["child"] == RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value
    assert result.intervals[1].status == RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value
    assert "UNSELECTED_ANCHOR_BOUNDARY_CONDITION" in result.intervals[1].structural_issues


def test_unselected_anchor_boundary_nulls_unrelated_adjacent_interval_match(project_root):
    projection = _projection(
        [
            {"id": 10, "label": "Duplicate"},
            {"id": 20, "label": "Duplicate"},
            {"id": 30, "label": "Boundary Anchor"},
            {"id": 40, "label": "Unrelated Exact"},
        ]
    )
    rows = [
        _row("ambiguous", 0, "Duplicate", "DETAIL"),
        _row("anchor", 1, "Boundary Anchor", "DETAIL", two_streams=True),
        _row("unrelated", 2, "Unrelated Exact", "DETAIL"),
    ]

    result = align_ordered_subgraph_v2(rows, projection, policy=_policy(project_root))

    assert result.status is MappingRunStatus.AMBIGUOUS_MAPPING
    assert _mapped(result)["anchor"] is None
    assert _mapped(result)["unrelated"] is None
    right = result.intervals[1]
    assert [(item.row_id, item.report_norm_id) for item in right.best_path.matches] == [
        ("unrelated", 40)
    ]
    assert right.status == RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value
    assert not right.automatic_selection_allowed
    assert "UNSELECTED_ANCHOR_BOUNDARY_CONDITION" in right.structural_issues


def test_selected_direct_parent_dependency_closure_is_transitive(project_root):
    projection = _projection(
        [
            {"id": 30, "label": "Parent"},
            {"id": 31, "label": "Child", "parent": 30},
            {"id": 32, "label": "Grandchild", "parent": 31},
        ]
    )
    rows = (
        _row("parent", 0, "Parent", "GROUP"),
        _row(
            "child",
            1,
            "Child",
            "GROUP",
            parent="parent",
            relation="PHYSICAL_PARENT",
        ),
        _row(
            "grandchild",
            2,
            "Grandchild",
            "DETAIL",
            parent="child",
            relation="PHYSICAL_PARENT",
        ),
    )
    records = (
        RowMappingRecordV2(
            "parent",
            RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value,
            None,
            (30,),
            0,
            "parent withheld",
        ),
        RowMappingRecordV2("child", RowMappingStatus.RESOLVED_PATH.value, 31, (31,), 0, "selected"),
        RowMappingRecordV2(
            "grandchild", RowMappingStatus.RESOLVED_PATH.value, 32, (32,), 0, "selected"
        ),
    )

    closed, invalidated = _enforce_selected_direct_parent_closure(
        rows,
        projection.nodes,
        records,
    )

    assert invalidated.keys() == {"child", "grandchild"}
    assert all(item.selected_report_norm_id is None for item in closed)
    assert {item.status for item in closed[1:]} == {RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value}


def test_anchor_counterfactual_aggregates_all_streams_and_preserves_alternative(project_root):
    selected_label = "a" * 20
    alternative_label = "a" * 14 + "b" * 6
    dissenting_proposal = "a" * 16 + "b" * 4
    projection = _projection(
        [
            {"id": 1, "label": selected_label},
            {"id": 2, "label": alternative_label},
        ]
    )
    row = SourceStructureRowV2(
        row_id="r",
        order=0,
        labels_by_reader={
            "agree_1": selected_label,
            "agree_2": selected_label,
            "dissenting": dissenting_proposal,
        },
        row_role="DETAIL",
    )

    result = align_ordered_subgraph_v2([row], projection, policy=_policy(project_root))

    anchor = result.anchors[0]
    assert anchor.aggregate_label_score == 1.0
    assert anchor.counterfactual_alternative_report_norm_id == 2
    assert anchor.counterfactual_alternative_aggregate_label_score == 0.9
    assert anchor.counterfactual_margin == 0.1
    assert anchor.status == RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value
    assert result.row_mappings[0].candidate_report_norm_ids == (1, 2)
    assert result.row_mappings[0].selected_report_norm_id is None
    assert result.status is MappingRunStatus.AMBIGUOUS_MAPPING


def test_direct_parent_gain_is_monotone_across_strong_threshold(project_root):
    source_label = "a" * 650
    parent_relaxed_label = source_label + "b" * 703
    exactly_strong_label = source_label + "b" * 700
    projection = _projection(
        [
            {"id": 100, "label": "Parent Group"},
            {"id": 101, "label": parent_relaxed_label, "parent": 100},
            {"id": 102, "label": exactly_strong_label, "parent": 100},
        ]
    )
    rows = [
        _row("parent", 0, "Parent Group", "GROUP"),
        _row(
            "child",
            1,
            source_label,
            "DETAIL",
            parent="parent",
            relation="PHYSICAL_PARENT",
        ),
    ]

    result = align_ordered_subgraph_v2(rows, projection, policy=_policy(project_root))

    pairs = {
        item.report_norm_id: item
        for item in result.intervals[0].candidate_pairs
        if item.row_id == "child"
    }
    assert pairs[101].aggregate_label_score == 0.649026
    assert pairs[102].aggregate_label_score == 0.65
    assert pairs[101].evidence_baseline == pairs[102].evidence_baseline == 0.35
    assert pairs[101].base_evidence_gain < pairs[102].base_evidence_gain
    child_match = next(
        item for item in result.intervals[0].best_path.matches if item.row_id == "child"
    )
    assert child_match.report_norm_id == 102
    assert child_match.admissibility == "STRONG_LABEL_WITH_MAPPED_DIRECT_PARENT"


def test_parent_relaxed_threshold_uses_raw_score_before_diagnostic_rounding(project_root):
    source_label = "a" * 17_504
    just_below_threshold_label = source_label + "b" * 65_015
    raw_similarity = ratio(source_label, just_below_threshold_label) / 100.0
    assert 0.35 - 0.0000005 <= raw_similarity < 0.35
    assert round(raw_similarity, 6) == 0.35
    projection = _projection(
        [
            {"id": 1, "label": "Parent Group"},
            {"id": 2, "label": just_below_threshold_label, "parent": 1},
        ]
    )
    rows = [
        _row("parent", 0, "Parent Group", "GROUP"),
        _row(
            "child",
            1,
            source_label,
            "DETAIL",
            parent="parent",
            relation="PHYSICAL_PARENT",
        ),
    ]

    result = align_ordered_subgraph_v2(rows, projection, policy=_policy(project_root))

    assert _mapped(result) == {"parent": 1, "child": None}
    assert _status(result)["child"] == RowMappingStatus.NO_ADMISSIBLE_PAIR.value
    assert not any(
        item.row_id == "child" and item.report_norm_id == 2
        for item in result.intervals[0].candidate_pairs
    )


def test_interval_margin_uses_raw_scores_before_diagnostic_rounding(project_root):
    selected_label = "a" * 42_503
    rounded_tie_label = selected_label + "b" * 15_001
    alternative_similarity = ratio(selected_label, rounded_tie_label) / 100.0
    raw_margin = 1.0 - alternative_similarity
    assert raw_margin < 0.15
    assert round(raw_margin, 6) == 0.15
    projection = _projection(
        [
            {"id": 1, "label": selected_label},
            {"id": 2, "label": rounded_tie_label},
        ]
    )

    result = align_ordered_subgraph_v2(
        [_row("row", 0, selected_label, "DETAIL")],
        projection,
        policy=_policy(project_root),
    )

    interval = result.intervals[0]
    assert interval.score_margin == 0.15
    assert interval.counterfactuals[0].exclusion_margin == 0.15
    assert not interval.counterfactuals[0].stable
    assert interval.status == RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value
    assert result.row_mappings[0].selected_report_norm_id is None
    assert result.status is MappingRunStatus.AMBIGUOUS_MAPPING


def test_anchor_counterfactual_uses_raw_margin_before_diagnostic_rounding(project_root):
    selected_label = "a" * 42_503
    alternative_label = "b" * 42_503
    dissenting_label = alternative_label + "a" * 15_001
    alternative_similarity = ratio(alternative_label, dissenting_label) / 100.0
    raw_margin = 1.0 - alternative_similarity
    assert raw_margin < 0.15
    assert round(raw_margin, 6) == 0.15
    projection = _projection(
        [
            {"id": 1, "label": selected_label},
            {"id": 2, "label": alternative_label},
        ]
    )
    row = SourceStructureRowV2(
        row_id="anchor",
        order=0,
        labels_by_reader={
            "agree_1": selected_label,
            "agree_2": selected_label,
            "dissenting": dissenting_label,
        },
        row_role="DETAIL",
    )

    result = align_ordered_subgraph_v2([row], projection, policy=_policy(project_root))

    anchor = result.anchors[0]
    assert anchor.constraint_report_norm_id == 1
    assert anchor.counterfactual_alternative_report_norm_id == 2
    assert anchor.counterfactual_margin == 0.15
    assert anchor.status == RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value
    assert anchor.selected_report_norm_id is None
    assert result.row_mappings[0].selected_report_norm_id is None
    assert result.status is MappingRunStatus.AMBIGUOUS_MAPPING


def test_anchor_schema_candidates_use_raw_strong_threshold(project_root):
    selected_label = "a" * 32_512
    just_below_strong_label = selected_label + "b" * 35_013
    raw_similarity = ratio(selected_label, just_below_strong_label) / 100.0
    assert raw_similarity < 0.65
    assert round(raw_similarity, 6) == 0.65
    projection = _projection(
        [
            {"id": 1, "label": selected_label},
            {"id": 2, "label": just_below_strong_label},
            {"id": 3, "label": "Duplicate"},
            {"id": 4, "label": "Duplicate"},
        ]
    )
    rows = [
        _row("anchor", 0, selected_label, "DETAIL", two_streams=True),
        _row("ambiguous", 1, "Duplicate", "DETAIL"),
    ]

    result = align_ordered_subgraph_v2(rows, projection, policy=_policy(project_root))

    anchor = next(item for item in result.anchors if item.row_id == "anchor")
    anchor_record = next(item for item in result.row_mappings if item.row_id == "anchor")
    dispositions = {item.report_norm_id: item for item in result.schema_dispositions}
    assert anchor.status == RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value
    assert anchor.counterfactual_alternative_report_norm_id == 2
    assert anchor.counterfactual_alternative_aggregate_label_score == 0.65
    assert anchor_record.candidate_report_norm_ids == (1,)
    assert dispositions[2].status == "UNMATCHED_SCHEMA_NODE"


def test_beam_pruning_forces_abstention_for_main_and_counterfactual_searches(project_root):
    top_label = "a" * 20
    middle_label = top_label + "b" * 17
    enabling_parent_label = top_label + "b" * 21
    child_label = "z" * 20
    specifications: list[dict[str, object]] = [{"id": 1, "label": top_label}]
    specifications.extend(
        {"id": report_norm_id, "label": middle_label} for report_norm_id in range(2, 66)
    )
    specifications.extend(
        [
            {"id": 66, "label": enabling_parent_label},
            {"id": 67, "label": child_label, "parent": 66},
        ]
    )
    projection = _projection(specifications)
    rows = [
        _row("parent", 0, top_label, "UNKNOWN"),
        _row(
            "child",
            1,
            child_label,
            "DETAIL",
            parent="parent",
            relation="PHYSICAL_PARENT",
        ),
    ]

    result = align_ordered_subgraph_v2(rows, projection, policy=_policy(project_root))

    interval = result.intervals[0]
    assert interval.best_path.total_score == 0.35
    assert [(item.row_id, item.report_norm_id) for item in interval.best_path.matches] == [
        ("parent", 1)
    ]
    assert interval.main_search_pruned_states > 0
    assert interval.counterfactual_search_pruned_states > 0
    assert not interval.search_exhaustive
    assert interval.status == RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value
    assert result.search.pruned_states > 0
    assert result.search.main_search_pruned_states > 0
    assert result.search.counterfactual_search_pruned_states > 0
    assert result.status is MappingRunStatus.AMBIGUOUS_MAPPING
    assert all(item.selected_report_norm_id is None for item in result.row_mappings)


def test_family_8_weak_total_and_section_are_not_rescued_by_adjacency(project_root):
    projection = _projection(
        [
            {"id": 1, "label": "Tiền mặt"},
            {"id": 2, "label": "TỔNG TÀI SẢN"},
            {"id": 3, "label": "Nhóm vốn", "level": 0},
        ]
    )
    rows = [
        _row("strong", 0, "Tiền mặt", "DETAIL"),
        _row("weak_total", 1, "Tổng vốn", "TOTAL"),
        _row("header", 2, "Nhóm vốn", "SECTION"),
    ]

    result = align_ordered_subgraph_v2(rows, projection, policy=_policy(project_root))

    assert _mapped(result)["strong"] == 1
    assert _mapped(result)["weak_total"] is None
    assert _mapped(result)["header"] is None
    assert _status(result)["weak_total"] == RowMappingStatus.NO_ADMISSIBLE_PAIR.value
    assert _status(result)["header"] == RowMappingStatus.NO_ADMISSIBLE_PAIR.value


def test_family_8_known_compatible_role_admits_without_bonus_and_unknown_is_neutral(project_root):
    projection = _projection([{"id": 1, "label": "Tiền mặt"}])
    known = align_ordered_subgraph_v2(
        [_row("known", 0, "Tiền mặt", "DETAIL")],
        projection,
        policy=_policy(project_root),
    )
    unknown = align_ordered_subgraph_v2(
        [_row("unknown", 0, "Tiền mặt", "UNKNOWN")],
        projection,
        policy=_policy(project_root),
    )

    known_pair = known.intervals[0].candidate_pairs[0]
    unknown_pair = unknown.intervals[0].candidate_pairs[0]
    assert known_pair.role_compatibility == "KNOWN_ROLE_COMPATIBLE_DETAIL"
    assert unknown_pair.role_compatibility == "UNKNOWN_ROLE_NEUTRAL"
    assert known_pair.base_evidence_gain == unknown_pair.base_evidence_gain
    assert _mapped(known)["known"] == _mapped(unknown)["unknown"] == 1


def test_projection_uses_structural_alias_but_never_historical_alias(project_root):
    projection = _projection(
        [
            {
                "id": 4337,
                "label": "Vốn đầu tư của chủ sở hữu",
                "aliases": ("a. Vốn điều lệ",),
                "history": ("BÍ MẬT LỊCH SỬ",),
            }
        ]
    )
    node = projection.nodes[0]
    assert node.structural_aliases == ("a. Vốn điều lệ",)
    assert "BÍ MẬT LỊCH SỬ" not in node.structural_aliases
    structural = align_ordered_subgraph_v2(
        [_row("structural", 0, "a. Vốn điều lệ", "DETAIL")],
        projection,
        policy=_policy(project_root),
    )
    historical = align_ordered_subgraph_v2(
        [_row("historical", 0, "BÍ MẬT LỊCH SỬ", "DETAIL")],
        projection,
        policy=_policy(project_root),
    )
    assert _mapped(structural)["structural"] == 4337
    assert _mapped(historical)["historical"] is None


def test_projection_hash_and_alias_authority_are_verified(project_root):
    projection = _projection([{"id": 1, "label": "Tiền mặt"}])
    row = _row("r", 0, "Tiền mặt", "DETAIL")
    with pytest.raises(OrderedSubgraphV2Error, match="hash identity drifted"):
        align_ordered_subgraph_v2(
            [row],
            replace(projection, projection_sha256="0" * 64),
            policy=_policy(project_root),
        )
    with pytest.raises(OrderedSubgraphV2Error, match="alias authority"):
        align_ordered_subgraph_v2(
            [row],
            replace(projection, alias_authority="CANONICAL_PLUS_HISTORY"),
            policy=_policy(project_root),
        )


def test_real_cdkt_projection_is_history_free_and_preserves_non_numeric_workbook_order(
    project_root,
):
    _workbooks, schema = load_all(project_root / "template", project_root)
    _registry, hierarchy = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml",
        project_root,
        schema,
    )
    apply_hierarchy_reference(schema, hierarchy)

    projection = build_schema_projection_v2(schema, "CDKT")

    assert len(projection.nodes) == 77
    assert projection.projection_sha256 == (
        "7025ca729c01a3f2030af38e9745a0ee8d72b1dad60c8d4e3b7cf749e5eb860c"
    )
    assert [node.report_norm_id for node in projection.nodes[64:67]] == [4337, 4373, 4338]
    assert projection.alias_authority == "CANONICAL_AND_STRUCTURAL_ALIASES_ONLY"


def test_policy_forbids_skip_coverage_and_cardinality_rewards(tmp_path, project_root):
    original = project_root / "config/mapping/ordered-subgraph-v2.yaml"
    text = original.read_text(encoding="utf-8")
    for field in ("skip_baseline", "coverage_reward", "cardinality_reward"):
        mutated = tmp_path / f"{field}.yaml"
        mutated.write_text(text.replace(f"{field}: 0.00", f"{field}: 0.01"), encoding="utf-8")
        with pytest.raises(OrderedSubgraphV2Error, match=field):
            load_ordered_subgraph_v2_policy(mutated)


@pytest.mark.parametrize(
    ("safe_text", "unsafe_text"),
    [
        (
            "policy_bytes_authority: SINGLE_IMMUTABLE_BYTE_SNAPSHOT_FOR_PARSE_AND_SHA256",
            "policy_bytes_authority: MUTABLE_PATH_REOPEN",
        ),
        (
            "require_earlier_schema_parent_compatibility: true",
            "require_earlier_schema_parent_compatibility: false",
        ),
        (
            "threshold_comparison: RAW_UNROUNDED_SCORE_DIAGNOSTIC_ROUNDING_ONLY",
            "threshold_comparison: ROUNDED_SCORE",
        ),
        (
            "margin_comparison: RAW_UNROUNDED_SCORE_DIAGNOSTIC_ROUNDING_ONLY",
            "margin_comparison: ROUNDED_SCORE",
        ),
        (
            "direct_parent_gain_baseline: MINIMUM_PARENT_RELAXED_LABEL_SCORE",
            "direct_parent_gain_baseline: MINIMUM_STRONG_LABEL_SCORE",
        ),
        ("parent_relaxed_relation_type: DIRECT_PARENT", "parent_relaxed_relation_type: UNKNOWN"),
        ("require_zero_beam_pruning: true", "require_zero_beam_pruning: false"),
    ],
)
def test_policy_pins_monotone_parent_gain_and_zero_pruning(
    tmp_path, project_root, safe_text, unsafe_text
):
    canonical = project_root / "config/mapping/ordered-subgraph-v2.yaml"
    mutated = tmp_path / "unsafe-policy.yaml"
    mutated.write_text(
        canonical.read_text(encoding="utf-8").replace(safe_text, unsafe_text),
        encoding="utf-8",
    )

    with pytest.raises(OrderedSubgraphV2Error, match="identity is unsafe"):
        load_ordered_subgraph_v2_policy(mutated)


def test_best_path_skipped_is_distinct_from_no_candidate_and_ambiguity(tmp_path, project_root):
    canonical = project_root / "config/mapping/ordered-subgraph-v2.yaml"
    exact_baseline = tmp_path / "exact-baseline.yaml"
    exact_baseline.write_text(
        canonical.read_text(encoding="utf-8").replace(
            "minimum_strong_aggregate_label_score: 0.65",
            "minimum_strong_aggregate_label_score: 1.00",
        ),
        encoding="utf-8",
    )
    policy = load_ordered_subgraph_v2_policy(exact_baseline)
    projection = _projection([{"id": 1, "label": "Tiền mặt"}])

    result = align_ordered_subgraph_v2(
        [_row("r", 0, "Tiền mặt", "DETAIL")],
        projection,
        policy=policy,
    )

    assert result.status is MappingRunStatus.RESOLVED
    assert result.intervals[0].candidate_pairs
    assert not result.intervals[0].best_path.matches
    assert result.row_mappings[0].status == RowMappingStatus.BEST_PATH_SKIPPED.value
    assert result.row_mappings[0].selected_report_norm_id is None


def test_in_memory_policy_drift_is_rejected(project_root):
    policy = _policy(project_root)
    projection = _projection([{"id": 1, "label": "Tiền mặt"}])
    with pytest.raises(OrderedSubgraphV2Error, match="in-memory mapping policy"):
        align_ordered_subgraph_v2(
            [_row("r", 0, "Tiền mặt", "DETAIL")],
            projection,
            policy=replace(policy, minimum_strong_label_score=0.99),
        )


def test_policy_bytes_loader_binds_fields_and_hash_to_one_snapshot(project_root):
    canonical = project_root / "config/mapping/ordered-subgraph-v2.yaml"
    source_bytes = canonical.read_bytes()

    policy = load_ordered_subgraph_v2_policy_bytes(
        source_bytes,
        source_path=Path("config/mapping/ordered-subgraph-v2.yaml"),
    )

    assert policy.source_bytes == source_bytes
    assert policy.policy_sha256 == hashlib.sha256(source_bytes).hexdigest()
    assert policy.minimum_strong_label_score == 0.65


def test_alignment_uses_immutable_policy_bytes_after_path_mutation(tmp_path, project_root):
    policy_path = tmp_path / "policy.yaml"
    canonical_bytes = (project_root / "config/mapping/ordered-subgraph-v2.yaml").read_bytes()
    policy_path.write_bytes(canonical_bytes)
    policy = load_ordered_subgraph_v2_policy(policy_path)
    policy_path.write_bytes(b"version: 0\n")

    result = align_ordered_subgraph_v2(
        [_row("row", 0, "Cash", "DETAIL")],
        _projection([{"id": 1, "label": "Cash"}]),
        policy=policy,
    )

    assert result.policy_sha256 == hashlib.sha256(canonical_bytes).hexdigest()
    assert result.row_mappings[0].selected_report_norm_id == 1


def test_in_memory_policy_byte_drift_is_rejected(project_root):
    policy = _policy(project_root)
    tampered_bytes = policy.source_bytes.replace(
        b"minimum_strong_aggregate_label_score: 0.65",
        b"minimum_strong_aggregate_label_score: 0.66",
    )

    with pytest.raises(OrderedSubgraphV2Error, match="in-memory mapping policy"):
        align_ordered_subgraph_v2(
            [_row("row", 0, "Cash", "DETAIL")],
            _projection([{"id": 1, "label": "Cash"}]),
            policy=replace(policy, source_bytes=tampered_bytes),
        )


def test_serialized_contract_has_nullable_selected_id_and_diagnostics(project_root):
    projection = _projection([{"id": 10, "label": "Khoản khác"}, {"id": 20, "label": "Khoản khác"}])
    result = align_ordered_subgraph_v2(
        [_row("r", 0, "Khoản khác", "DETAIL")],
        projection,
        policy=_policy(project_root),
    )
    serialized = result_json(result)
    assert '"selected_report_norm_id":null' in serialized
    assert '"candidate_report_norm_ids":[10,20]' in serialized
    assert '"runner_up_path":{' in serialized
    assert len(result.row_mappings) == 1
    assert len(result.schema_dispositions) == 2
