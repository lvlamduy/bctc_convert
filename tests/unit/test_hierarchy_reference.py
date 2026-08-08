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
    assert lctt.schema_only_append_ids == (5714,)
    cdkt = next(workbook for workbook in registry.workbooks if workbook.statement_type == "CDKT")
    assert cdkt.skipped_blank_rows == 47
    assert cdkt.schema_only_append_ids == (5712,)
    kqkd = next(workbook for workbook in registry.workbooks if workbook.statement_type == "KQKD")
    assert kqkd.schema_only_append_ids == (5713,)
    tm = next(workbook for workbook in registry.workbooks if workbook.statement_type == "TM")
    assert tm.schema_only_append_ids == (1944, *range(5718, 5750))
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
    assert by_id[4364].children == [4337, 4373, 4338, 4340, 4374, 4339]
    assert by_id[4365].parent_id == 4325
    assert by_id[4325].children == [4364, 4365, 4342, 4341, 4343, 5699]
    assert by_id[4325].parent_id == 5712
    assert by_id[5712].children == [4325, 4306]
    assert by_id[5712].parent_id == 4305
    assert by_id[4305].children == [4304, 5712]
    assert by_id[5713].children == [4385, 4386, 4387, 4388, 4389, 4390, 4393]
    assert by_id[5713].parent_id == 4376
    assert by_id[4376].children == [5713, 4391]
    assert by_id[5714].parent_id == 4111
    assert by_id[5714].children == [4120, 4121]
    assert by_id[4120].parent_id == 5714
    assert by_id[4121].parent_id == 5714
    assert by_id[4111].children == [4118, 4119, 4143, 4144, 4145, 4146, 5714, 4147]
    assert by_id[5718].parent_id == 575
    assert by_id[5718].children == []
    assert by_id[575].children == [576, 585, 5718]
    assert by_id[583].parent_id == 576
    assert by_id[590].parent_id == 585
    assert by_id[727].children == [
        728,
        729,
        730,
        731,
        732,
        733,
        734,
        735,
        736,
        737,
        5719,
        738,
        739,
        740,
        741,
        742,
        743,
        5720,
        5721,
        5722,
        744,
        745,
        5749,
    ]
    assert all(
        by_id[schema_id].parent_id == 727 for schema_id in (737, 5719, 5720, 5721, 5722, 5749)
    )
    assert by_id[717].children == [*range(718, 727), 5745]
    assert by_id[747].children == [5746]
    assert by_id[752].children == [753, 754, 755, 5747]
    assert by_id[766].children == [*range(767, 783), 5748]
    assert by_id[782].parent_id == 766
    assert by_id[783].children == [784, 792]
    assert by_id[784].children == list(range(785, 792))
    assert by_id[792].children == list(range(793, 800))
    assert by_id[1294].children == [1295, 1296, 1297, 1298, 1299, 1300, 1301, 1303, 1304]
    assert by_id[1301].children == [5741, 5742, 1302]
    assert by_id[1302].children == [5743, 5744]
    assert by_id[1944].parent_id is None
    assert by_id[1944].hierarchy_source is None
