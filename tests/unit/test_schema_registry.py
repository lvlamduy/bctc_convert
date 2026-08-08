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
        "TM": 1417,
    }
    assert len(items) == len({item.schema_id for item in items}) == 1628
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
    tm = [item for item in items if item.statement_type == "TM"]
    assert tm[-2].schema_id == 1943
    assert tm[-2].next_id == 1944
    assert tm[-1].schema_id == 1944
    assert tm[-1].canonical_name == TM_1944_NAME
    assert tm[-1].display_order == 1416
    assert tm[-1].previous_id == 1943
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
