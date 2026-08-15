from __future__ import annotations

import json

from bctc_ai.mapping.lctt import load_cash_flow_rules
from bctc_ai.schema.append_only import (
    TM_1944_BEFORE_SHA256,
    TM_1944_NAME,
    verify_tm_1944_append,
)
from bctc_ai.schema.registry import load_all, load_schema_contract


def test_supplied_schema_is_imported_without_reordering(project_root):
    workbooks, items = load_all(project_root / "template", project_root)
    assert {workbook.statement_type: workbook.item_count for workbook in workbooks} == {
        "CDKT": 99,
        "KQKD": 25,
        "LCTT": 110,
        "TM": 1714,
    }
    assert len(items) == len({item.schema_id for item in items}) == 1948
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
    assert by_id[6034].canonical_name == "Tiền thu/(chi) bất động sản đầu tư"
    assert by_id[6034].display_order == 89
    assert by_id[6034].previous_id == 4143
    assert by_id[6034].next_id == 4144
    assert all(
        by_id[schema_id].scope == ["CONSOLIDATED"] for schema_id in (*range(6038, 6054), 6055, 6056)
    )
    assert by_id[6035].canonical_name == "Dự phòng rủi ro chứng khoán kinh doanh"
    assert by_id[6035].display_order == 9
    assert by_id[6035].previous_id == 4346
    assert by_id[6035].next_id == 4347
    assert by_id[6036].previous_id == 4351
    assert by_id[6036].next_id == 4352
    assert by_id[6037].previous_id == 4318
    assert by_id[6037].next_id == 4319
    assert by_id[6038].display_order == 81
    assert by_id[6038].previous_id == 4305
    assert by_id[6038].next_id == 6039
    assert by_id[6053].display_order == 97
    assert by_id[6053].next_id == 6055
    assert by_id[6055].canonical_name == "Tổng chỉ tiêu ngoại bảng"
    assert by_id[6055].display_order == 98
    assert by_id[6055].previous_id == 6053
    assert by_id[6055].next_id is None
    assert by_id[6056].canonical_name == "Cam kết giao dịch hoán đổi"
    assert by_id[6056].display_order == 87
    assert by_id[6056].previous_id == 6043
    assert by_id[6056].next_id == 6044
    assert by_id[4360].canonical_name == "Vay các TCTC, TCTD khác"
    assert by_id[4319].canonical_name == "Tiền gửi và vay các TCTC, TCTD khác"
    assert by_id[4136].canonical_name == ("Tăng, giảm các khoản tiền gửi và vay các TCTC, TCTD")
    assert by_id[6054].display_order == 72
    assert by_id[6054].previous_id == 4132
    assert by_id[6054].next_id == 4133
    assert by_id[4382].canonical_name == "Tổng chi phí thuế thu nhập doanh nghiệp"
    assert by_id[4109].canonical_name == (
        "Lưu chuyển tiền thuần từ hoạt động kinh doanh trước những thay đổi về tài sản "
        "và nợ phải trả hoạt động"
    )
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
    assert by_id[5959].canonical_name == "Dự phòng giảm giá"
    assert by_id[5959].previous_id == 5961
    assert by_id[5959].next_id == 868
    assert by_id[5975].canonical_name == "Phải thu liên quan đến dịch vụ thanh toán"
    assert by_id[5975].previous_id == 980
    assert by_id[5975].next_id == 5976
    assert by_id[5984].canonical_name == "Vốn điều lệ của Ngân hàng"
    assert by_id[5984].previous_id == 5983
    assert by_id[5984].next_id == 6011
    assert by_id[5990].canonical_name == ("Lãi thuần từ chứng khoán kinh doanh, chứng khoán đầu tư")
    assert by_id[5990].previous_id == 1197
    assert by_id[5990].next_id == 1198
    assert by_id[5991].canonical_name == "Tổng tăng nguyên giá TSCĐ hữu hình trong kỳ"
    assert by_id[5991].previous_id == 870
    assert by_id[5991].next_id == 871
    assert by_id[6019].canonical_name == "Trích lập/Tăng"
    assert by_id[6019].previous_id == 1129
    assert by_id[6019].next_id == 1130
    assert by_id[6029].canonical_name == "Lãi thuần từ hoạt động kinh doanh khác"
    assert by_id[6029].previous_id == 1228
    assert by_id[6029].next_id == 6030
    assert by_id[6033].canonical_name == "Chi phí/(Hoàn nhập) dự phòng mua nợ"
    assert by_id[6033].previous_id == 1225
    assert by_id[6033].next_id == 1226
    assert by_id[6061].canonical_name == (
        "Dự phòng rủi ro cho vay giao dịch ký quỹ và ứng trước khách hàng"
    )
    assert by_id[6061].previous_id == 799
    assert by_id[6065].next_id == 800
    assert by_id[6066].canonical_name == "Đầu tư vào công ty liên doanh"
    assert by_id[6066].previous_id == 866
    assert by_id[6066].next_id == 6067
    assert by_id[6067].canonical_name == "Đầu tư vào công ty liên kết"
    assert by_id[6067].next_id == 867
    assert by_id[6068].canonical_name == "Tổng giảm nguyên giá TSCĐ vô hình trong kỳ"
    assert by_id[6068].previous_id == 920
    assert by_id[6068].next_id == 921
    assert by_id[6069].canonical_name == (
        "Nguyên giá TSCĐ vô hình đã hao mòn hết nhưng vẫn còn sử dụng"
    )
    assert by_id[6069].previous_id == 5971
    assert by_id[6069].next_id == 942
    assert {schema_id for schema_id in range(5991, 6035)} <= set(by_id)
    tm = [item for item in items if item.statement_type == "TM"]
    assert tm[-2].schema_id == 5945
    assert tm[-2].next_id == 1944
    assert tm[-1].schema_id == 1944
    assert tm[-1].canonical_name == TM_1944_NAME
    assert tm[-1].display_order == 1713
    assert tm[-1].previous_id == 5945
    assert tm[-1].next_id is None


def test_universal_schema_contract_is_base_plus_audited_additions(project_root):
    contract = load_schema_contract(project_root)
    assert contract["schema_name"] == "UNIVERSAL_BANK_BCTC_SCHEMA"
    assert contract["schema_strategy"] == "SOURCE_EVIDENCE_DRIVEN_APPEND_ONLY_SUPERSET"
    assert contract["base_schema"]["item_count"] == 1593
    assert contract["base_schema"]["ordered_canonical_projection_sha256"] == (
        "e63b77ebf99907843bea419cef32bc64cd709129813f89309f3b42fc818a1b10"
    )
    assert contract["base_schema"]["ordered_report_norm_ids_sha256"] == (
        "5cc0e9ea70b23af236ce43b920838299dbc91e9c0ef19d31165f4ce49eea4f9f"
    )
    assert contract["universal_schema"] == {
        "revision": "UNIVERSAL_BANK_BCTC_SCHEMA@6069",
        "item_count": 1948,
        "counts": {"CDKT": 99, "KQKD": 25, "LCTT": 110, "TM": 1714},
        "high_watermark": 6069,
    }
    registry = json.loads(
        (project_root / "data/registered/schema_registry.json").read_text(encoding="utf-8")
    )
    assert registry["schema_name"] == "UNIVERSAL_BANK_BCTC_SCHEMA"
    assert registry["base_schema"] == contract["base_schema"]
    assert registry["universal_schema"]["revision"] == "UNIVERSAL_BANK_BCTC_SCHEMA@6069"
    assert registry["universal_schema"]["high_watermark"] == 6069
    assert registry["universal_schema"]["item_count"] == 1948
    assert registry["universal_schema"]["universal_schema_sha256"] == registry["graph_sha256"]


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
