from __future__ import annotations

from bctc_ai.mapping.lctt import load_cash_flow_rules
from bctc_ai.schema.append_only import (
    TM_1944_BEFORE_SHA256,
    TM_1944_NAME,
    verify_tm_1944_append,
)
from bctc_ai.schema.registry import load_all


def test_supplied_schema_is_imported_without_reordering(project_root):
    workbooks, items = load_all(project_root / "template", project_root)
    assert {workbook.statement_type: workbook.item_count for workbook in workbooks} == {
        "CDKT": 78,
        "KQKD": 25,
        "LCTT": 108,
        "TM": 1613,
    }
    assert len(items) == len({item.schema_id for item in items}) == 1824
    by_id = {item.schema_id: item for item in items}
    assert by_id[4350].canonical_name == "Chứng khoán đầu tư sẵn sàng để bán"
    assert by_id[5712].canonical_name == "TỔNG VỐN CHỦ SỞ HỮU"
    assert by_id[5712].previous_id == 4306
    assert by_id[5712].next_id == 4305
    assert by_id[5713].canonical_name == "TỔNG THU NHẬP HOẠT ĐỘNG"
    assert by_id[5713].previous_id == 4393
    assert by_id[5713].next_id == 4391
    assert by_id[5714].canonical_name == ("Tiền thu/(chi) đầu tư, góp vốn vào các đơn vị khác")
    assert by_id[5714].previous_id == 4146
    assert by_id[5714].next_id == 4120
    assert by_id[5718].canonical_name == (
        "Tổng dự phòng rủi ro tiền gửi và cho vay các tổ chức tín dụng khác"
    )
    assert by_id[5718].previous_id == 591
    assert by_id[5718].next_id == 592
    assert by_id[5718].display_order == 32
    assert by_id[770].canonical_name == ("Công ty TNHH MTV (hoặc trên MTV) vốn nhà nước trên 50%")
    assert by_id[737].canonical_name == "Giáo dục & Đào tạo"
    assert by_id[5719].canonical_name == "Y tế & hoạt động trợ giúp xã hội"
    assert by_id[5720].canonical_name == "Ngành nghệ thuật vui chơi giải trí"
    assert by_id[5721].canonical_name == "Ngành hoạt động dịch vụ khác"
    assert by_id[5722].canonical_name == (
        "Ngành hoạt động làm thuê các công việc trong các hộ gia đình, sản xuất "
        "sản phẩm vật chất và dịch vụ tự tiêu dùng của hộ gia đình"
    )
    assert by_id[5750].canonical_name == "Giao dịch với các bên liên quan"
    assert by_id[5752].canonical_name == "+ Trong nước"
    assert by_id[5752].previous_id == 759
    assert by_id[5752].next_id == 760
    assert by_id[5762].canonical_name == "Báo cáo bộ phận hợp nhất"
    assert by_id[5763].canonical_name == "Báo cáo bộ phận hợp nhất theo khu vực địa lý"
    assert by_id[5764].canonical_name == "Miền Bắc"
    assert by_id[5765].canonical_name == "+ Tài sản"
    assert by_id[5799].canonical_name == "Tổng cộng"
    assert by_id[5805].canonical_name == "+ Lợi nhuận trước thuế"
    assert by_id[5805].next_id == 5806
    assert by_id[5806].canonical_name == "Báo cáo bộ phận hợp nhất theo khu vực kinh doanh"
    assert by_id[5807].canonical_name == "Tài chính Ngân hàng"
    assert by_id[5808].canonical_name == "+ Tài sản"
    assert by_id[5828].canonical_name == "Quản lý nợ và Khai thác tài sản"
    assert by_id[5842].canonical_name == "Tổng cộng"
    assert by_id[5848].canonical_name == "+ Lợi nhuận trước thuế"
    assert by_id[5848].next_id == 1305
    assert by_id[5849].canonical_name == "Tài sản cố định và bất động sản đầu tư"
    assert by_id[5849].previous_id == 1362
    assert by_id[5849].next_id == 1363
    assert by_id[5856].canonical_name == "Tổng nợ phải trả"
    assert by_id[5857].canonical_name == "Cho vay khách hàng và mua nợ"
    assert by_id[5869].canonical_name == "Rủi ro lãi suất - Trong hạn trên 01 năm"
    assert by_id[5897].canonical_name == "Tài sản cố định, bất động sản đầu tư"
    assert by_id[5897].previous_id == 1743
    assert by_id[5897].next_id == 1744
    assert by_id[5898].canonical_name == "Rủi ro thanh khoản - Quá hạn"
    assert by_id[5898].previous_id == 1759
    assert by_id[5898].next_id == 5899
    assert by_id[5905].canonical_name == "Cho vay khách hàng và mua nợ"
    assert by_id[5909].canonical_name == "Tài sản cố định, bất động sản đầu tư"
    assert by_id[5922].next_id == 1760
    assert by_id[5923].previous_id == 1812
    assert by_id[5923].next_id == 1813
    assert by_id[5924].previous_id == 1815
    assert by_id[5924].next_id == 1816
    assert by_id[5933].previous_id == 1927
    assert by_id[5933].next_id == 1928
    assert by_id[5934].previous_id == 1930
    assert by_id[5934].next_id == 1931
    assert by_id[5935].canonical_name == "Tỷ giá một số ngoại tệ tại thời điểm lập báo cáo"
    assert by_id[5935].previous_id == 1943
    assert by_id[5935].next_id == 5936
    assert by_id[5945].canonical_name == "SEK"
    assert by_id[5945].previous_id == 5944
    assert by_id[5945].next_id == 1944
    tm = [item for item in items if item.statement_type == "TM"]
    assert tm[-2].schema_id == 5945
    assert tm[-2].next_id == 1944
    assert tm[-1].schema_id == 1944
    assert tm[-1].canonical_name == TM_1944_NAME
    assert tm[-1].display_order == 1612
    assert tm[-1].previous_id == 5945
    assert tm[-1].next_id is None


def test_tm_1944_append_audit_proves_existing_rows_were_preserved(project_root):
    audit = verify_tm_1944_append(
        project_root,
        project_root / "data/registered/schema_append_1944.json",
    )
    assert audit["workbook"]["before_sha256"] == TM_1944_BEFORE_SHA256
    assert audit["preservation"]["existing_id_name_order_mapping_preserved"] is True
    assert audit["preservation"]["only_changed_zip_members"] == [
        "xl/sharedStrings.xml",
        "xl/worksheets/sheet1.xml",
    ]
    assert audit["preservation"]["supporting_hierarchy_workbook_mutated"] is False


def test_lctt_blocks_follow_user_confirmed_workbook_order(project_root):
    _, items = load_all(project_root / "template", project_root)
    rules = load_cash_flow_rules(project_root / "config/mapping/lctt-v2.yaml")
    assert rules.semantic_authority_status == "RESOLVED"
    lctt = [item for item in items if item.statement_type == "LCTT"]
    assert lctt[0].schema_id == 4155
    assert lctt[0].cash_flow_branch == "INDIRECT"
    assert lctt[56].schema_id == 4168
    assert lctt[56].cash_flow_branch == "INDIRECT"
    assert lctt[57].schema_id == 4104
    assert lctt[-1].schema_id == 4116
    direct_structural = next(item for item in lctt if item.schema_id == 4104)
    assert direct_structural.cash_flow_branch == "DIRECT"
    assert next(item for item in lctt if item.schema_id == 4154).cash_flow_branch == "DIRECT"


def test_historical_lctt_v1_policy_remains_replayable(project_root):
    rules = load_cash_flow_rules(project_root / "config/mapping/lctt.yaml")
    assert rules.semantic_authority_status == "REOPENED_EVIDENCE_CONFLICT"
