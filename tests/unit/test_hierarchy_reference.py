from __future__ import annotations

from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import load_all


def test_vst_hierarchy_is_complete_where_claimed_and_partial_for_direct_lctt(project_root):
    _, schema = load_all(project_root / "template", project_root)
    registry, hierarchy = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml",
        project_root,
        schema,
    )
    counts = {workbook.statement_type: workbook.item_count for workbook in registry.workbooks}
    assert counts == {"CDKT": 77, "KQKD": 24, "LCTT": 50, "TM": 1384}
    lctt = next(workbook for workbook in registry.workbooks if workbook.statement_type == "LCTT")
    assert lctt.coverage == "BRANCH_DIRECT"
    assert lctt.non_id_labels == ("LƯU CHUYỂN TIỀN TỆ TRỰC TIẾP",)
    cdkt = next(workbook for workbook in registry.workbooks if workbook.statement_type == "CDKT")
    assert cdkt.skipped_blank_rows == 47
    tm = next(workbook for workbook in registry.workbooks if workbook.statement_type == "TM")
    assert tm.schema_only_append_ids == (1944,)
    assert registry.status == "VALIDATED_SUPPORTING_REFERENCE_WITH_SCHEMA_ONLY_APPENDS"
    assert len(hierarchy) == 1535


def test_hierarchy_edges_and_structural_aliases_are_attached_without_reordering(project_root):
    _, schema = load_all(project_root / "template", project_root)
    _, hierarchy = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml",
        project_root,
        schema,
    )
    original_order = [(item.statement_type, item.schema_id) for item in schema]
    apply_hierarchy_reference(schema, hierarchy)
    assert [(item.statement_type, item.schema_id) for item in schema] == original_order
    by_id = {item.schema_id: item for item in schema}
    assert by_id[4312].children == [4344, 4326, 4345]
    assert by_id[4344].parent_id == 4312
    assert by_id[4344].siblings == [4326, 4345]
    assert by_id[560].parent_id is None
    assert by_id[4162].hierarchy_source is None
    assert by_id[1944].parent_id is None
    assert by_id[1944].hierarchy_source is None
