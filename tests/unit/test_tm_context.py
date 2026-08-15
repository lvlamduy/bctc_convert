from __future__ import annotations

from collections import Counter
from dataclasses import replace

import pytest
import yaml

from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import retrieval_key
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import SchemaItem, load_all
from bctc_ai.schema.tm_context import (
    TM_CONTEXT_POLICY_RELATIVE_PATH,
    TmContextError,
    TmContextPolicy,
    TmLevelMismatchPolicy,
    build_tm_schema_context,
    load_tm_context_policy,
    tm_context_projection,
    tm_context_projection_sha256,
)


@pytest.fixture(scope="module")
def live_tm_context(project_root):
    _, schema = load_all(project_root / "template", project_root)
    _, hierarchy = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml",
        project_root,
        schema,
    )
    apply_hierarchy_reference(schema, hierarchy)
    policy = load_tm_context_policy(project_root / TM_CONTEXT_POLICY_RELATIVE_PATH)
    return policy, build_tm_schema_context(schema, policy)


def _item(
    schema_id: int,
    canonical_name: str,
    display_order: int,
    *,
    statement_type: str = "TM",
    parent_id: int | None = None,
    children: tuple[int, ...] = (),
    hierarchy_level: int | None = 0,
) -> SchemaItem:
    return SchemaItem(
        schema_id=schema_id,
        canonical_name=canonical_name,
        normalized_name=retrieval_key(canonical_name),
        statement_type=statement_type,
        display_order=display_order,
        parent_id=parent_id,
        children=list(children),
        hierarchy_level=hierarchy_level,
    )


def _synthetic_schema(policy: TmContextPolicy) -> list[SchemaItem]:
    roots = {root.report_norm_id: root.canonical_name for root in policy.section_roots}
    orphan = policy.orphan_items[0]
    items = [
        _item(560, roots[560], 0, children=(561, 783)),
        _item(561, "Nhóm thuyết minh A", 1, parent_id=560, children=(562,), hierarchy_level=1),
        _item(562, "Khác", 2, parent_id=561, hierarchy_level=2),
        _item(783, "Nhóm dự phòng", 3, parent_id=560, children=(784, 792), hierarchy_level=1),
        _item(
            784,
            "Dự phòng nhóm một",
            4,
            parent_id=783,
            children=tuple(range(785, 792)),
            hierarchy_level=2,
        ),
    ]
    for movement_id in range(785, 792):
        items.append(
            _item(
                movement_id,
                f"Dòng biến động {movement_id}",
                len(items),
                parent_id=784,
                hierarchy_level=3,
            )
        )
    items.append(
        _item(
            792,
            "Dự phòng nhóm hai",
            len(items),
            parent_id=783,
            children=tuple(range(793, 800)),
            hierarchy_level=2,
        )
    )
    for movement_id in range(793, 800):
        items.append(
            _item(
                movement_id,
                f"Dòng biến động {movement_id}",
                len(items),
                parent_id=792,
                hierarchy_level=3,
            )
        )
    items.extend(
        [
            _item(1142, roots[1142], len(items), children=(1150,)),
            _item(1150, "Khác", len(items) + 1, parent_id=1142, hierarchy_level=1),
            _item(1247, roots[1247], len(items) + 2),
            _item(1259, roots[1259], len(items) + 3),
        ]
    )
    items.append(
        _item(
            orphan.report_norm_id,
            orphan.canonical_name,
            len(items),
            hierarchy_level=None,
        )
    )
    return items


def _replace_item(items: list[SchemaItem], schema_id: int, **changes: object) -> list[SchemaItem]:
    return [replace(item, **changes) if item.schema_id == schema_id else item for item in items]


def _resequence(items: list[SchemaItem]) -> list[SchemaItem]:
    return [replace(item, display_order=index) for index, item in enumerate(items)]


def test_live_tm_context_is_complete_ordered_and_hash_stable(project_root, live_tm_context):
    policy, contexts = live_tm_context
    assert policy.source_sha256 == sha256_file(project_root / TM_CONTEXT_POLICY_RELATIVE_PATH)
    assert policy.source_sha256 == (
        "50b0e7fcd5fbb54b45f6643d1d9c577de6013fdd04b748c620c755c54ee55e0a"
    )
    assert len(contexts) == 1717
    assert [context.display_order for context in contexts] == list(range(1717))
    assert len({context.report_norm_id for context in contexts}) == 1717
    assert Counter(context.section for context in contexts) == {
        "BALANCE_SHEET_NOTES": 684,
        "INCOME_STATEMENT_NOTES": 139,
        "CASH_FLOW_NOTES": 12,
        "OTHER_QUANTITATIVE_NOTES": 881,
        None: 1,
    }
    assert Counter(context.context_status for context in contexts) == {
        "RESOLVED": 1716,
        "UNRESOLVED_ORPHAN": 1,
    }
    assert Counter(context.mapping_eligible for context in contexts) == {True: 1716, False: 1}

    by_id = {context.report_norm_id: context for context in contexts}
    assert by_id[560].ancestor_path == (560,)
    assert by_id[560].section_root_id == 560
    assert by_id[560].note_family_root_id is None
    assert by_id[561].ancestor_path == (560, 561)
    assert by_id[561].parent_report_norm_id == 560
    assert by_id[561].note_family_root_id == 561
    assert by_id[562].ancestor_path == (560, 561, 562)
    assert by_id[562].note_family_root_id == 561
    assert by_id[562].derived_hierarchy_level == 2
    movement_ids = {*range(785, 792), *range(793, 800)}
    for movement_id in movement_ids:
        movement = by_id[movement_id]
        assert movement.section == "BALANCE_SHEET_NOTES"
        assert movement.section_root_id == 560
        assert movement.note_family_root_id == 783
        assert movement.parent_report_norm_id in {784, 792}
        assert movement.hierarchy_level == 3
        assert movement.derived_hierarchy_level == 3
        assert movement.context_status == "RESOLVED"
        assert movement.mapping_eligible is True
    assert all(
        context.hierarchy_level == context.derived_hierarchy_level
        for context in contexts
        if context.context_status == "RESOLVED"
    )
    assert by_id[1944].ancestor_path == (1944,)
    assert by_id[1944].section is None
    assert by_id[1944].section_root_id is None
    assert by_id[1944].note_family_root_id is None
    assert by_id[1944].context_status == "UNRESOLVED_ORPHAN"
    assert by_id[1944].mapping_eligible is False
    assert by_id[1944].derived_hierarchy_level is None

    projection = tm_context_projection(contexts)
    assert len(projection) == 1717
    assert projection[0]["report_norm_id"] == 560
    assert projection[-1]["report_norm_id"] == 1944
    assert tm_context_projection_sha256(contexts) == (
        "b1352d09b9368e5fbe129050340bb620006b40a59e2c84aaf3d6c889f44d3f94"
    )


def test_same_label_is_disambiguated_by_section_family_and_ancestor_path(project_root):
    policy = load_tm_context_policy(project_root / TM_CONTEXT_POLICY_RELATIVE_PATH)
    contexts = build_tm_schema_context(_synthetic_schema(policy), policy)
    by_id = {context.report_norm_id: context for context in contexts}

    assert by_id[562].canonical_name == by_id[1150].canonical_name == "Khác"
    assert by_id[562].section == "BALANCE_SHEET_NOTES"
    assert by_id[562].note_family_root_id == 561
    assert by_id[562].ancestor_path == (560, 561, 562)
    assert by_id[1150].section == "INCOME_STATEMENT_NOTES"
    assert by_id[1150].note_family_root_id == 1150
    assert by_id[1150].ancestor_path == (1142, 1150)


@pytest.mark.parametrize("routing_field", ["source_bank", "source_pages", "source_row_count"])
def test_policy_rejects_source_routing_fields(project_root, tmp_path, routing_field):
    source = project_root / TM_CONTEXT_POLICY_RELATIVE_PATH
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload[routing_field] = []
    candidate = tmp_path / "tm-context.yaml"
    candidate.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")

    with pytest.raises(TmContextError, match="policy fields are invalid"):
        load_tm_context_policy(candidate)


def test_tm_context_rejects_out_of_order_schema(project_root):
    policy = load_tm_context_policy(project_root / TM_CONTEXT_POLICY_RELATIVE_PATH)

    with pytest.raises(TmContextError, match="ordered by contiguous workbook display order"):
        build_tm_schema_context(list(reversed(_synthetic_schema(policy))), policy)


def test_tm_context_rejects_missing_accounting_section_root(project_root):
    policy = load_tm_context_policy(project_root / TM_CONTEXT_POLICY_RELATIVE_PATH)
    items = [item for item in _synthetic_schema(policy) if item.schema_id != 1247]

    with pytest.raises(TmContextError, match="accounting section root 1247 is missing"):
        build_tm_schema_context(_resequence(items), policy)


def test_tm_context_rejects_cross_statement_parent(project_root):
    policy = load_tm_context_policy(project_root / TM_CONTEXT_POLICY_RELATIVE_PATH)
    items = _synthetic_schema(policy)
    items = _replace_item(items, 560, children=(783,))
    items = _replace_item(items, 561, parent_id=999)
    items.append(
        _item(
            999,
            "Không thuộc thuyết minh",
            0,
            statement_type="CDKT",
            children=(561,),
        )
    )

    with pytest.raises(TmContextError, match="cross-statement parent 999"):
        build_tm_schema_context(items, policy)


def test_tm_context_rejects_hierarchy_cycle(project_root):
    policy = load_tm_context_policy(project_root / TM_CONTEXT_POLICY_RELATIVE_PATH)
    items = _synthetic_schema(policy)
    items = _replace_item(items, 560, children=(783,))
    items = _replace_item(items, 561, parent_id=562, children=(562,))
    items = _replace_item(items, 562, parent_id=561, children=(561,))

    with pytest.raises(TmContextError, match="hierarchy cycle detected"):
        build_tm_schema_context(items, policy)


def test_tm_context_quarantines_only_the_pinned_unresolved_orphan(project_root):
    policy = load_tm_context_policy(project_root / TM_CONTEXT_POLICY_RELATIVE_PATH)
    items = _synthetic_schema(policy)
    items = _replace_item(items, 1259, children=(1944,))
    items = _replace_item(items, 1944, parent_id=1259, hierarchy_level=1)

    with pytest.raises(TmContextError, match="quarantined orphan 1944 drifted"):
        build_tm_schema_context(items, policy)


def test_tm_context_rejects_connected_item_without_resolved_level(project_root):
    policy = load_tm_context_policy(project_root / TM_CONTEXT_POLICY_RELATIVE_PATH)
    items = _replace_item(_synthetic_schema(policy), 562, hierarchy_level=None)

    with pytest.raises(TmContextError, match="lacks resolved hierarchy level"):
        build_tm_schema_context(items, policy)


def test_tm_context_rejects_unquarantined_declared_level_mismatch(project_root):
    policy = load_tm_context_policy(project_root / TM_CONTEXT_POLICY_RELATIVE_PATH)
    items = _replace_item(_synthetic_schema(policy), 562, hierarchy_level=1)

    with pytest.raises(TmContextError, match="does not match ancestor depth 2"):
        build_tm_schema_context(items, policy)


def test_retired_level_mismatch_quarantine_cannot_be_reintroduced(project_root):
    policy = load_tm_context_policy(project_root / TM_CONTEXT_POLICY_RELATIVE_PATH)
    mutated_policy = replace(
        policy,
        level_mismatch_items=(
            TmLevelMismatchPolicy(
                report_norm_id=785,
                canonical_name="Số dư đầu kỳ này",
                expected_parent_report_norm_id=784,
                expected_declared_hierarchy_level=2,
                expected_derived_hierarchy_level=3,
                status="UNRESOLVED_LEVEL_MISMATCH",
                mapping_eligible=False,
            ),
        ),
    )

    with pytest.raises(TmContextError, match="not mapping-safe"):
        build_tm_schema_context(_synthetic_schema(policy), mutated_policy)
