from __future__ import annotations

import pytest

from bctc_ai.schema.hierarchy import (
    _reject_schema_graph_cycles,
    apply_hierarchy_reference,
    load_hierarchy_reference,
)
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
    assert lctt.schema_only_append_ids == (5714, 6034, 6054)
    cdkt = next(workbook for workbook in registry.workbooks if workbook.statement_type == "CDKT")
    assert cdkt.skipped_blank_rows == 47
    assert cdkt.schema_only_append_ids == (5712, *range(6035, 6054), 6055, 6056)
    kqkd = next(workbook for workbook in registry.workbooks if workbook.statement_type == "KQKD")
    assert kqkd.schema_only_append_ids == (5713,)
    tm = next(workbook for workbook in registry.workbooks if workbook.statement_type == "TM")
    assert tm.schema_only_append_ids == (1944, *range(5718, 6034), *range(6057, 6068))
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
    assert by_id[4313].children == [4346, 6035, 4347]
    assert by_id[4316].children == [4350, 4351, 6036, 4352]
    assert by_id[4318].children == [6037]
    assert by_id[6038].parent_id is None
    assert by_id[6038].children == [6055]
    assert by_id[6055].parent_id == 6038
    assert by_id[6055].children == [6039, 6050]
    assert by_id[6039].children == [6040, 6041, 6046, 6047, 6048]
    assert by_id[6041].children == [6042, 6043, 6056]
    assert by_id[6056].parent_id == 6041
    assert by_id[6056].children == [6044, 6045]
    assert by_id[6048].children == [6049]
    assert by_id[6050].children == [6051, 6052, 6053]
    assert by_id[5713].children == [4385, 4386, 4387, 4388, 4389, 4390, 4393]
    assert by_id[5713].parent_id == 4376
    assert by_id[4376].children == [5713, 4391]
    assert by_id[5714].parent_id == 4111
    assert by_id[5714].children == [4120, 4121]
    assert by_id[4120].parent_id == 5714
    assert by_id[4121].parent_id == 5714
    assert by_id[6034].parent_id == 4111
    assert by_id[6034].children == [4144, 4145, 4146]
    assert all(by_id[schema_id].parent_id == 6034 for schema_id in (4144, 4145, 4146))
    assert by_id[4111].children == [4118, 4119, 4143, 6034, 5714, 4147]
    assert by_id[4110].children == [4109, 4107, 4108, 4142]
    assert by_id[4107].children == [4129, 4130, 4131, 4132, 6054, 4133, 4134]
    assert by_id[4108].children == list(range(4135, 4142))
    assert by_id[6054].parent_id == 4107
    assert "Lợi nhuận từ hoạt động kinh doanh trước thay đổi vốn lưu động" in (
        by_id[4109].structural_aliases
    )
    assert "Thuế Thu nhập doanh nghiệp phải nộp" in by_id[4382].structural_aliases
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
        6060,
        740,
        741,
        742,
        743,
        5720,
        5721,
        5722,
        6059,
        744,
        745,
        6058,
        5749,
    ]
    assert all(
        by_id[schema_id].parent_id == 727
        for schema_id in (737, 5719, 5720, 5721, 5722, 5749, 6058, 6059, 6060)
    )
    assert by_id[717].children == [718, 719, 720, 6057, 721, 722, 723, 724, 725, 726, 5745]
    assert by_id[747].children == [5746]
    assert by_id[752].children == [753, 754, 755, 5747]
    assert by_id[766].children == [*range(767, 783), 5748]
    assert by_id[782].parent_id == 766
    assert by_id[783].children == [784, 792, 6061]
    assert by_id[784].children == list(range(785, 792))
    assert by_id[792].children == list(range(793, 800))
    assert by_id[6061].children == list(range(6062, 6066))
    assert by_id[1294].children == [1295, 1296, 1297, 1298, 1299, 1300, 1301, 1303, 1304]
    assert by_id[1301].children == [5741, 5742, 1302]
    assert by_id[1302].children == [5743, 5744]
    assert by_id[759].children == [5752, 765]
    assert by_id[5752].children == list(range(760, 765))
    assert by_id[1055].children == [1056, 1075, 5753]
    assert by_id[5753].children == [5754, 5755]
    assert by_id[1295].children == [5756]
    assert by_id[5756].children == [5757, 5758]
    assert by_id[5750].children == [5751]
    assert by_id[5759].children == [5760, 5761]
    assert by_id[1259].children == [
        1260,
        1269,
        1280,
        1289,
        1294,
        5750,
        5759,
        5762,
        1305,
        1352,
        1483,
        1759,
        5935,
    ]
    assert by_id[5762].children == [5763, 5806]
    assert by_id[5763].children == [5764, 5771, 5778, 5785, 5792, 5799]
    for axis_id in (5764, 5771, 5778, 5785, 5792, 5799):
        assert by_id[axis_id].children == list(range(axis_id + 1, axis_id + 7))
    assert by_id[5806].children == [5807, 5814, 5821, 5828, 5835, 5842]
    for axis_id in (5807, 5814, 5821, 5828, 5835, 5842):
        assert by_id[axis_id].children == list(range(axis_id + 1, axis_id + 7))
    assert by_id[5828].structural_aliases == ["Khai thác nợ Quản lý tài sản"]
    assert by_id[5849].children == [1363, 1364]
    assert by_id[1363].parent_id == 5849
    assert by_id[1366].children == [5850, 1375]
    assert by_id[5850].children == [1367, 1370, 1371, 1372, 1373, 1374]
    assert by_id[1367].children == [1368, 1369]
    assert by_id[5857].children == []
    assert by_id[1491].parent_id == 1484
    assert by_id[5858].children == [1494, 1495]
    assert by_id[1483].children == [
        1484,
        1509,
        1584,
        1609,
        1634,
        1659,
        1684,
        1709,
        5869,
        1734,
    ]
    assert by_id[5869].children == [*range(5870, 5881), *range(5883, 5896)]
    assert by_id[5876].children == []
    assert by_id[5877].parent_id == 5869
    assert by_id[5880].children == [5881, 5882]
    assert by_id[5896].children == []
    assert by_id[1741].parent_id == 1734
    assert by_id[5897].children == [1744, 1745]
    assert by_id[1759].children == [5898, 1760, 1783, 1806, 1829, 1852, 1875, 1898, 1921]
    assert by_id[5898].children == [
        *range(5899, 5910),
        *range(5912, 5923),
    ]
    assert by_id[5905].children == []
    assert by_id[5905].structural_aliases == ["Cho vay khách hàng và mua nợ (*)"]
    assert by_id[5909].children == [5910, 5911]
    for loan_id in (5923, 5925, 5927, 5929, 5931, 5933):
        assert by_id[loan_id].children == []
        assert by_id[loan_id].structural_aliases == ["Cho vay khách hàng và mua nợ (*)"]
    for combined_id, component_ids in {
        5924: (1816, 1817),
        5926: (1839, 1840),
        5928: (1862, 1863),
        5930: (1885, 1886),
        5932: (1908, 1909),
        5934: (1931, 1932),
    }.items():
        assert by_id[combined_id].children == list(component_ids)
        assert all(by_id[item_id].parent_id == combined_id for item_id in component_ids)
    assert by_id[5935].children == list(range(5936, 5946))
    assert by_id[5935].structural_aliases == ["6. Tỷ giá một số ngoại tệ tại thời điểm lập báo cáo"]
    assert [by_id[item_id].structural_aliases for item_id in range(5936, 5946)] == [
        ["Đô la Mỹ"],
        ["Euro"],
        ["Bảng Anh"],
        ["Yên Nhật"],
        ["Franc Thụy Sĩ"],
        ["Đô la Úc"],
        ["Đô la Canada"],
        ["Đô la Singapore"],
        ["Baht Thái"],
        ["Krona Thụy Điển"],
    ]
    assert by_id[1944].parent_id is None
    assert by_id[1944].hierarchy_source is None


def test_final_universal_overlay_rejects_cycles(project_root):
    _, schema = load_all(project_root / "template", project_root)
    _, hierarchy = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml",
        project_root,
        schema,
    )
    apply_hierarchy_reference(schema, hierarchy)
    by_id = {item.schema_id: item for item in schema}
    by_id[6029].parent_id = 6030
    with pytest.raises(ValueError, match="schema hierarchy cycle"):
        _reject_schema_graph_cycles(schema)
