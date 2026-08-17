from __future__ import annotations

import copy
from functools import lru_cache

import pytest

from bctc_ai.core.hashing import sha256_file
from bctc_ai.schema import business_update as business
from bctc_ai.schema.business_update import (
    BUSINESS_UPDATE_AUDIT,
    CDKT_BEFORE_SHA256,
    CDKT_CURRENT_SCHEMA_IDS,
    CDKT_OFF_BALANCE_TOTAL_COMPONENTS,
    CDKT_OFF_BALANCE_TOTAL_ID,
    CDKT_SWAP_COMMITMENT_TOTAL_COMPONENTS,
    CDKT_SWAP_COMMITMENT_TOTAL_ID,
    CDKT_TOTAL_EQUITY_COMPONENTS,
    CDKT_TOTAL_EQUITY_ID,
    CDKT_VPB_SCHEMA_IDS,
    CDKT_WORKBOOK,
    KQKD_BEFORE_SHA256,
    KQKD_TOTAL_OPERATING_INCOME_COMPONENTS,
    KQKD_TOTAL_OPERATING_INCOME_ID,
    KQKD_WORKBOOK,
    LCTT_BEFORE_SHA256,
    LCTT_INVESTMENT_CONTRIBUTION_NET_COMPONENTS,
    LCTT_INVESTMENT_CONTRIBUTION_NET_ID,
    LCTT_INVESTMENT_PROPERTY_NET_COMPONENTS,
    LCTT_INVESTMENT_PROPERTY_NET_ID,
    LCTT_VPB_COMBINED_LOAN_ID,
    LCTT_WORKBOOK,
    REVIEWED_EXTERNAL_IDS,
    TM_ARTS_RECREATION_ID,
    TM_BEFORE_SHA256,
    TM_EDUCATION_ID,
    TM_GENERAL_PROVISION_MOVEMENT_ID,
    TM_HEALTH_SOCIAL_ID,
    TM_HOUSEHOLD_EMPLOYMENT_ID,
    TM_LOAN_BUSINESS_OTHER_ID,
    TM_LOAN_BUSINESS_PARENT_ID,
    TM_LOAN_INDUSTRY_PARENT_ID,
    TM_OTHER_SERVICES_ID,
    TM_PROVISION_MOVEMENT_COMPONENTS,
    TM_PROVISION_MOVEMENT_ID,
    TM_SPECIFIC_PROVISION_MOVEMENT_ID,
    TM_TOTAL_INTERBANK_PROVISION_COMPONENTS,
    TM_TOTAL_INTERBANK_PROVISION_ID,
    TM_UNIVERSAL_SCHEMA_IDS,
    TM_WORKBOOK,
    BusinessSchemaUpdateError,
    verify_business_schema_update,
)
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import load_all


def test_business_schema_migration_is_hash_bound_and_preserves_sealed_baselines(project_root):
    audit = _verified_audit(project_root)
    assert sha256_file(project_root / "template/Bank_CDKT_ReportNormId.xlsx") == (
        CDKT_BEFORE_SHA256
    )
    assert sha256_file(project_root / "template/Bank_KQKD_ReportNormId.xlsx") == (
        KQKD_BEFORE_SHA256
    )
    assert sha256_file(project_root / "template/Bank_LCTT_ReportNormId.xlsx") == (
        LCTT_BEFORE_SHA256
    )
    assert sha256_file(project_root / "template/Bank_TM_ReportNormId.xlsx") == (TM_BEFORE_SHA256)
    assert sha256_file(project_root / CDKT_WORKBOOK) == audit["workbooks"]["CDKT"]["after_sha256"]
    assert sha256_file(project_root / KQKD_WORKBOOK) == audit["workbooks"]["KQKD"]["after_sha256"]
    assert sha256_file(project_root / LCTT_WORKBOOK) == audit["workbooks"]["LCTT"]["after_sha256"]
    assert sha256_file(project_root / TM_WORKBOOK) == audit["workbooks"]["TM"]["after_sha256"]
    assert set(audit["collision_safety"]["new_ids"]).isdisjoint(REVIEWED_EXTERNAL_IDS)
    assert audit["schema_strategy"]["base_schema"]["item_count"] == 1593
    assert audit["schema_strategy"]["universal_schema"] == {
        "revision": "UNIVERSAL_BANK_BCTC_SCHEMA@6074",
        "item_count": 1953,
        "counts": {"CDKT": 99, "KQKD": 25, "LCTT": 110, "TM": 1719},
        "high_watermark": 6074,
        "workbook_sha256": {
            statement: record["after_sha256"] for statement, record in audit["workbooks"].items()
        },
    }
    assert audit["schema_strategy"]["migration_delta"]["new_report_norm_ids"] == [
        6073,
        6074,
    ]
    accepted_changes = {
        record["schema_id"]: record
        for record in audit["schema_changes"]
        if record.get("schema_status") == "ACCEPTED_UNIVERSAL"
    }
    assert set(accepted_changes) == set(range(5991, 6075))
    assert all(
        accepted_changes[schema_id]["section"] == "BALANCE_SHEET_NOTES"
        for schema_id in range(5991, 6021)
    )
    assert all(
        accepted_changes[schema_id]["section"] == "INCOME_STATEMENT_NOTES"
        for schema_id in range(6021, 6034)
    )
    assert accepted_changes[6034]["section"] == "DIRECT_CASH_FLOW_INVESTING_ACTIVITIES"
    assert accepted_changes[6035]["section"] == "BALANCE_SHEET_ASSETS"
    assert accepted_changes[6036]["section"] == "BALANCE_SHEET_ASSETS"
    assert accepted_changes[6037]["section"] == "BALANCE_SHEET_LIABILITIES"
    assert all(
        accepted_changes[schema_id]["section"] == "OFF_BALANCE_SHEET"
        for schema_id in range(6038, 6054)
    )
    assert accepted_changes[6054]["section"] == "DIRECT_CASH_FLOW_OPERATING_ASSET_CHANGES"
    assert accepted_changes[6055]["section"] == "OFF_BALANCE_SHEET"
    assert accepted_changes[6056]["section"] == "OFF_BALANCE_SHEET"
    assert all(
        accepted_changes[schema_id]["section"] == "BALANCE_SHEET_NOTES"
        for schema_id in range(6057, 6075)
    )
    assert accepted_changes[6057]["evidence"]["observed_values"] == ["DASH", "DASH"]
    assert accepted_changes[6058]["evidence"]["visible_label"] == (
        "Cho vay tại Chi nhánh và ngân hàng con nước ngoài"
    )
    assert accepted_changes[6059]["evidence"]["visible_label"].startswith(
        "Cho vay cá nhân để mua nhà ở"
    )
    assert accepted_changes[6060]["evidence"]["visible_label"] == "Dịch vụ"
    assert accepted_changes[6061]["evidence"]["visible_label"] == (
        "Dự phòng cho vay giao dịch ký quỹ và ứng trước"
    )
    assert accepted_changes[6062]["evidence"]["observed_values"] == ["161.614"]
    assert accepted_changes[6063]["evidence"]["observed_values"] == ["-"]
    assert accepted_changes[6064]["evidence"]["observed_values"] == ["-"]
    assert accepted_changes[6065]["evidence"]["observed_values"] == ["161.614"]
    assert accepted_changes[6066]["evidence"]["visible_label"] == ("Đầu tư vào công ty liên doanh")
    assert accepted_changes[6067]["evidence"]["visible_label"] == ("Đầu tư vào công ty liên kết")
    assert accepted_changes[6068]["evidence"]["visible_label"] == ("Giảm nguyên giá trong kỳ")
    assert accepted_changes[6069]["evidence"]["visible_label"] == (
        "Nguyên giá TSCĐ vô hình đã hao mòn hết nhưng vẫn còn sử dụng"
    )
    assert accepted_changes[6070]["evidence"]["visible_label"] == "Vay Ngân hàng Nhà nước"
    assert accepted_changes[6071]["evidence"]["visible_label"] == ("Tiền gửi có kỳ hạn của KBNN")
    assert accepted_changes[6072]["evidence"]["visible_label"] == "Tiền gửi của Bộ Tài chính"
    assert accepted_changes[6073]["evidence"]["visible_label"] == "Thương mại, dịch vụ"
    assert accepted_changes[6074]["evidence"]["visible_label"] == ("Hợp tác xã và công ty tư nhân")
    ctg_swap = accepted_changes[6056]["evidence"]
    assert ctg_swap["user_decision"] == "Q076"
    assert ctg_swap["source_row_ref"] == "ctg-p5-5705"
    assert ctg_swap["source_document_sha256"] == (
        "f7453816648cac21536621e09d4e52a40e8ce9fcdbaf824981b3b997a8197318"
    )
    assert ctg_swap["reviewed_evidence_sha256"] == (
        "32c86c0bf7642d3bd7596225331fc6f10906970476e1a9ba982b2f478d0f8e74"
    )
    assert ctg_swap["observed_values"] == ["937.179.489", "849.738.846"]
    assert ctg_swap["exact_parent_equation"] == {
        "target_schema_id": 6041,
        "component_schema_ids": [6042, 6043, 6056],
        "current": "953123645=7973593+7970563+937179489",
        "comparative": "860422276=5341651+5341779+849738846",
    }
    bridge = ctg_swap["reviewed_evidence_bridge"]
    assert bridge["reviewed_item_id"] == 5705
    assert bridge["visible_row_id"] == "ctg-p5-5705"
    assert bridge["period_axes"] == {
        "CURRENT": "2026-06-30",
        "COMPARATIVE": "2025-12-31",
    }
    assert bridge["current_schema_target_id"] == 6056
    assert bridge["current_schema_target_authority"] == "Q076"
    assert bridge["sealed_historical_template_membership"] == ("OUTSIDE_CURRENT_TARGET_TEMPLATE")
    assert bridge["sealed_historical_mapping_action"] == "DO_NOT_MAP_TO_TARGET_CDKT"
    assert bridge["sealed_history_mutated"] is False
    alias_changes = audit["structural_alias_changes"]
    assert len(alias_changes) == 57
    assert sum(change["added_to_structural_aliases"] is True for change in alias_changes) == 54
    corrected_names = {
        record["schema_id"]: record
        for record in audit["schema_changes"]
        if record.get("change") == "CORRECT_DISPLAY_NAME"
    }
    assert corrected_names[4360]["after"] == "Vay các TCTC, TCTD khác"
    assert corrected_names[4319]["after"] == "Tiền gửi và vay các TCTC, TCTD khác"
    assert corrected_names[4136]["after"] == ("Tăng, giảm các khoản tiền gửi và vay các TCTC, TCTD")


def test_q078_declared_cross_branch_alias_collision_fails_closed(
    project_root, monkeypatch: pytest.MonkeyPatch
):
    _, loaded = load_all(project_root / "template", project_root)
    schema = copy.deepcopy(loaded)
    by_key = {(item.statement_type, item.schema_id): item for item in schema}
    collision_change = next(
        change
        for change in business._expected_structural_alias_changes()
        if change.get("collision_handling") == "OPPOSITE_CASH_FLOW_BRANCH_TYPED_ALIAS"
    )
    monkeypatch.setattr(business, "_expected_structural_alias_changes", lambda: [collision_change])
    by_key[("LCTT", 4179)].canonical_name = "Synthetic owner drift"
    with pytest.raises(BusinessSchemaUpdateError, match="structural alias collision"):
        business._apply_structural_alias_changes(schema, by_key)


def test_business_formula_overlay_has_exact_authorized_edges(project_root):
    _, schema = load_all(project_root / "template", project_root)
    _, hierarchy = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml",
        project_root,
        schema,
    )
    apply_hierarchy_reference(schema, hierarchy)
    by_id = {item.schema_id: item for item in schema}
    assert tuple(by_id[CDKT_TOTAL_EQUITY_ID].children) == CDKT_TOTAL_EQUITY_COMPONENTS
    assert tuple(by_id[KQKD_TOTAL_OPERATING_INCOME_ID].children) == (
        KQKD_TOTAL_OPERATING_INCOME_COMPONENTS
    )
    assert tuple(by_id[LCTT_INVESTMENT_CONTRIBUTION_NET_ID].children) == (
        LCTT_INVESTMENT_CONTRIBUTION_NET_COMPONENTS
    )
    assert tuple(by_id[LCTT_INVESTMENT_PROPERTY_NET_ID].children) == (
        LCTT_INVESTMENT_PROPERTY_NET_COMPONENTS
    )
    assert audit_formula_components(project_root, TM_TOTAL_INTERBANK_PROVISION_ID) == (
        TM_TOTAL_INTERBANK_PROVISION_COMPONENTS
    )
    assert by_id[4305].children == [4304, CDKT_TOTAL_EQUITY_ID]
    assert by_id[4313].children == [4346, 6035, 4347]
    assert by_id[4316].children == [4350, 4351, 6036, 4352]
    assert by_id[4318].children == [6037]
    assert by_id[6038].parent_id is None
    assert by_id[6038].children == [CDKT_OFF_BALANCE_TOTAL_ID]
    assert by_id[CDKT_OFF_BALANCE_TOTAL_ID].children == list(CDKT_OFF_BALANCE_TOTAL_COMPONENTS)
    assert by_id[6039].children == [6040, 6041, 6046, 6047, 6048]
    assert by_id[6041].children == [6042, 6043, CDKT_SWAP_COMMITMENT_TOTAL_ID]
    assert by_id[CDKT_SWAP_COMMITMENT_TOTAL_ID].children == list(
        CDKT_SWAP_COMMITMENT_TOTAL_COMPONENTS
    )
    assert by_id[6048].children == [6049]
    assert by_id[6050].children == [6051, 6052, 6053]
    assert by_id[4376].children == [KQKD_TOTAL_OPERATING_INCOME_ID, 4391]
    assert by_id[4111].children == [
        4118,
        4119,
        4143,
        LCTT_INVESTMENT_PROPERTY_NET_ID,
        LCTT_INVESTMENT_CONTRIBUTION_NET_ID,
        4147,
    ]
    assert all(
        by_id[schema_id].parent_id == LCTT_INVESTMENT_PROPERTY_NET_ID
        for schema_id in LCTT_INVESTMENT_PROPERTY_NET_COMPONENTS
    )
    assert by_id[4110].children == [4109, 4107, 4108, 4142]
    assert by_id[4107].children == [4129, 4130, 4131, 4132, 6054, 4133, 4134]
    assert by_id[4108].children == list(range(4135, 4142))
    assert by_id[LCTT_VPB_COMBINED_LOAN_ID].parent_id == 4107
    assert (
        "Tăng các khoản cho vay khách hàng và mua nợ"
        in by_id[LCTT_VPB_COMBINED_LOAN_ID].structural_aliases
    )
    assert "Cam kết mua giao dịch hoán đổi ngoại tệ" in by_id[6044].structural_aliases
    assert "Cam kết bán giao dịch hoán đổi ngoại tệ" in by_id[6045].structural_aliases
    assert (
        "CÁC CHỈ TIÊU NGOÀI BÁO CÁO TÌNH HÌNH TÀI CHÍNH HỢP NHẤT" in by_id[6038].structural_aliases
    )
    assert set(CDKT_VPB_SCHEMA_IDS) == set(range(6035, 6054))
    assert set(CDKT_CURRENT_SCHEMA_IDS) == {6055, 6056}
    assert {*CDKT_VPB_SCHEMA_IDS, *CDKT_CURRENT_SCHEMA_IDS} == {
        *range(6035, 6054),
        6055,
        6056,
    }
    assert all(
        by_id[schema_id].scope == ["CONSOLIDATED"] for schema_id in (*range(6038, 6054), 6055, 6056)
    )
    assert by_id[4360].canonical_name == "Vay các TCTC, TCTD khác"
    assert by_id[4319].canonical_name == "Tiền gửi và vay các TCTC, TCTD khác"
    assert by_id[4136].canonical_name == ("Tăng, giảm các khoản tiền gửi và vay các TCTC, TCTD")
    assert set(by_id[4360].structural_aliases) == {
        "2. Vay các TCTD khác",
        "Vay các TCTD khác",
    }
    assert set(by_id[4319].structural_aliases) == {
        "II. Tiền gửi và vay các TCTD khác",
        "Tiền gửi và vay các TCTD khác",
        'Tiền gửi và vay các tổ chức tài chính ("TCTC"), TCTD khác',
    }
    assert set(by_id[4136].structural_aliases) == {
        "16. Tăng/(Giảm) các khoản tiền gửi, tiền vay các tổ chức tín dụng",
        "Tăng, giảm các khoản tiền gửi và vay các TCTD",
        "Tăng/(Giảm) tiền gửi, tiền vay các TCTD khác",
        ("Tăng/(Giảm) tiền gửi, tiền vay từ các tổ chức tài chính, tổ chức tín dụng khác"),
    }
    assert by_id[TM_TOTAL_INTERBANK_PROVISION_ID].parent_id == 575
    assert by_id[TM_TOTAL_INTERBANK_PROVISION_ID].children == []
    assert by_id[575].children == [576, 585, TM_TOTAL_INTERBANK_PROVISION_ID]
    assert by_id[583].parent_id == 576
    assert by_id[590].parent_id == 585
    assert by_id[TM_LOAN_INDUSTRY_PARENT_ID].children == [
        728,
        729,
        730,
        731,
        732,
        733,
        734,
        6073,
        735,
        736,
        TM_EDUCATION_ID,
        TM_HEALTH_SOCIAL_ID,
        738,
        739,
        6060,
        740,
        741,
        742,
        743,
        TM_ARTS_RECREATION_ID,
        TM_OTHER_SERVICES_ID,
        TM_HOUSEHOLD_EMPLOYMENT_ID,
        6059,
        744,
        745,
        6058,
        5749,
    ]
    assert all(
        by_id[schema_id].parent_id == TM_LOAN_INDUSTRY_PARENT_ID
        for schema_id in (
            TM_EDUCATION_ID,
            TM_HEALTH_SOCIAL_ID,
            TM_ARTS_RECREATION_ID,
            TM_OTHER_SERVICES_ID,
            TM_HOUSEHOLD_EMPLOYMENT_ID,
            5749,
            6058,
            6059,
            6060,
        )
    )
    assert by_id[717].children == [718, 719, 720, 6057, 721, 722, 723, 724, 725, 726, 5745]
    assert by_id[747].children == [5746]
    assert by_id[752].children == [753, 754, 755, 5747]
    assert by_id[TM_LOAN_BUSINESS_PARENT_ID].children == [
        *range(767, 777),
        6074,
        *range(777, 783),
        5748,
    ]
    assert by_id[TM_LOAN_BUSINESS_OTHER_ID].parent_id == TM_LOAN_BUSINESS_PARENT_ID
    assert tuple(by_id[TM_PROVISION_MOVEMENT_ID].children) == TM_PROVISION_MOVEMENT_COMPONENTS
    assert by_id[TM_GENERAL_PROVISION_MOVEMENT_ID].children == list(range(785, 792))
    assert by_id[TM_SPECIFIC_PROVISION_MOVEMENT_ID].children == list(range(793, 800))
    assert by_id[6061].children == list(range(6062, 6066))
    assert audit_formula_components(project_root, TM_PROVISION_MOVEMENT_ID) == (
        TM_PROVISION_MOVEMENT_COMPONENTS
    )
    assert by_id[1294].children == [1295, 1296, 1297, 1298, 1299, 1300, 1301, 1303, 1304]
    assert by_id[1301].children == [5741, 5742, 1302]
    assert by_id[1302].children == [5743, 5744]
    assert audit_formula_components(project_root, 1301) == (5741, 5742, 1302)
    assert audit_formula_components(project_root, 1302) == (5743, 5744)
    assert by_id[759].children == [5752, 765]
    assert by_id[5752].children == list(range(760, 765))
    assert by_id[1055].children == [1056, 1075, 5753]
    assert by_id[5753].children == [5754, 5755]
    assert by_id[1295].children == [5756]
    assert by_id[5756].children == [5757, 5758]
    assert by_id[5750].children == [5751]
    assert by_id[5759].children == [5760, 5761]
    assert by_id[5762].children == [5763, 5806]
    assert by_id[5763].children == [5764, 5771, 5778, 5785, 5792, 5799]
    for axis_id in (5764, 5771, 5778, 5785, 5792, 5799):
        assert by_id[axis_id].children == list(range(axis_id + 1, axis_id + 7))
    assert by_id[5806].children == [5807, 5814, 5821, 5828, 5835, 5842]
    for axis_id in (5807, 5814, 5821, 5828, 5835, 5842):
        assert by_id[axis_id].children == list(range(axis_id + 1, axis_id + 7))
    assert audit_formula_components(project_root, 5750) == (5751,)
    assert audit_formula_components(project_root, 5753) == (5754, 5755)
    assert audit_formula_components(project_root, 5756) == (5757, 5758)
    assert audit_formula_components(project_root, 5759) == (5760, 5761)
    assert audit_formula_components(project_root, 5800) == (5765, 5772, 5779, 5786, 5793)
    assert audit_formula_components(project_root, 5805) == (5770, 5777, 5784, 5791, 5798)
    assert audit_formula_components(project_root, 5843) == (5808, 5815, 5822, 5829, 5836)
    assert audit_formula_components(project_root, 5848) == (5813, 5820, 5827, 5834, 5841)
    assert by_id[5849].children == [1363, 1364]
    assert by_id[1366].children == [5850, 1375]
    assert by_id[5850].children == [1367, 1370, 1371, 1372, 1373, 1374]
    assert by_id[1367].children == [1368, 1369]
    assert audit_formula_components(project_root, 5849) == (1363, 1364)
    assert audit_formula_components(project_root, 5850) == (
        1367,
        1370,
        1371,
        1372,
        1373,
        1374,
    )
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
    assert by_id[5857].parent_id == 1484
    assert by_id[5857].children == []
    assert by_id[1491].parent_id == 1484
    assert by_id[5858].children == [1494, 1495]
    assert by_id[1494].parent_id == 5858
    assert audit_formula_components(project_root, 5858) == (1494, 1495)
    assert by_id[5869].children == [*range(5870, 5881), *range(5883, 5896)]
    assert by_id[5876].children == []
    assert by_id[5877].parent_id == 5869
    assert by_id[5880].children == [5881, 5882]
    assert audit_formula_components(project_root, 5870) == (
        5871,
        5872,
        5873,
        5874,
        5875,
        5876,
        5878,
        5879,
        5880,
        5883,
    )
    assert audit_formula_components(project_root, 5884) == tuple(range(5885, 5893))
    assert audit_formula_components(project_root, 5893) == (5870, 5884)
    assert audit_formula_components(project_root, 5895) == (5893, 5894)
    assert by_id[5896].parent_id == 1734
    assert by_id[1741].parent_id == 1734
    assert by_id[5897].children == [1744, 1745]
    assert by_id[1759].children == [5898, 1760, 1783, 1806, 1829, 1852, 1875, 1898, 1921]
    assert by_id[5898].children == [*range(5899, 5910), *range(5912, 5923)]
    assert by_id[5905].children == []
    assert by_id[5909].children == [5910, 5911]
    assert by_id[5923].parent_id == 1806
    assert by_id[5923].children == []
    assert by_id[1813].parent_id == 1806
    assert by_id[5924].children == [1816, 1817]
    assert by_id[1816].parent_id == 5924
    assert by_id[5933].parent_id == 1921
    assert by_id[5933].children == []
    assert by_id[1928].parent_id == 1921
    assert by_id[5934].children == [1931, 1932]
    assert by_id[1931].parent_id == 5934
    assert by_id[1259].children[-2:] == [1759, 5935]
    assert by_id[5935].children == list(range(5936, 5946))
    assert by_id[862].children == [863, 864, 865, 866, 6066, 6067, 867, 5959]
    assert by_id[867].children == [5960, 5961]
    assert by_id[868].children == [869, 883, 5964]
    assert by_id[869].children == [870, 5991, 5992, 5993, 5962, 882]
    assert by_id[914].children == [915, 5997, 6068, 5998, 5967, 928]
    assert by_id[6068].children == list(range(921, 928))
    assert by_id[5991].children == list(range(871, 876))
    assert by_id[5992].children == list(range(876, 882))
    assert by_id[883].children == [884, 5994, 5995, 5996, 5963, 895]
    assert by_id[5994].children == list(range(885, 888))
    assert by_id[5995].children == list(range(888, 895))
    assert by_id[5964].children == [5965, 5966]
    assert by_id[913].children == [914, 929, 5969, 6069]
    assert by_id[914].children == [915, 5997, 6068, 5998, 5967, 928]
    assert by_id[6068].children == list(range(921, 928))
    assert by_id[5997].children == list(range(916, 921))
    assert by_id[929].children == [930, 5999, 6000, 6001, 5968, 941]
    assert by_id[5999].children == list(range(931, 934))
    assert by_id[6000].children == list(range(934, 941))
    assert by_id[5969].children == [5970, 5971]
    assert by_id[942].children == [943, 956, 5972]
    assert by_id[943].children == [944, 6002, 6003, 6004, 955]
    assert by_id[6002].children == list(range(945, 952))
    assert by_id[6003].children == list(range(952, 955))
    assert by_id[956].children == [957, 6005, 961, 962, 963, 964, 6006, 965]
    assert by_id[6005].children == list(range(958, 961))
    assert by_id[5972].children == [5973, 5974]
    assert by_id[967].children[0] == 6007
    assert by_id[967].children[-4:] == [980, 5975, 5976, 981]
    assert by_id[1075].children[0] == 5977
    assert by_id[1024].children == [6070, 1035, 6071, 1038, 6072, 1039]
    assert by_id[6070].children == list(range(1025, 1035))
    assert by_id[1035].children == [1036, 1037]
    assert by_id[1100].children == [1101, 1105, 1109, 1113, 1117]
    assert by_id[1101].children == [5978, 5979, 6008, 6009, 1102, 1103, 1104]
    assert by_id[1105].children == [1106, 1107, 1108]
    assert by_id[1109].children == [5980, 5981, 6010, 1110, 1111, 1112]
    assert by_id[1113].children == [1114, 1115, 1116]
    assert by_id[1103].canonical_name == "Từ 12 tháng đến 5 năm"
    assert by_id[1111].canonical_name == "Từ 12 tháng đến 5 năm"
    assert by_id[1117].canonical_name == (
        "Các loại giấy tờ có giá khác (bao gồm trái phiếu tăng vốn)"
    )
    assert by_id[1128].children[:11] == [5982, 5983, 5984, *range(6011, 6019)]
    assert by_id[1128].children[11:15] == [1129, 6019, 6020, 1141]
    assert by_id[1128].children[-2:] == [5946, 5949]
    assert by_id[6019].children == list(range(1130, 1137))
    assert by_id[6020].children == list(range(1137, 1141))
    assert by_id[5946].children == [5947, 5948]
    assert by_id[5949].children == [5950, 5951, 5953, 5956]
    assert by_id[1142].children[:7] == [1143, 1151, 5985, 1157, 1167, 5989, 1175]
    assert 5990 in by_id[1142].children
    assert 6029 in by_id[1142].children
    assert by_id[1157].children[0] == 6021
    assert by_id[1170].children == [6024, 6025]
    assert by_id[6029].children == [6030]
    assert by_id[1221].children == [
        6032,
        1222,
        1223,
        6031,
        1224,
        1225,
        6033,
        1226,
        1227,
        1228,
    ]
    assert audit_formula_components(project_root, 862) == (867, 5959)
    assert audit_formula_components(project_root, 5965) == (870, 884)
    assert audit_formula_components(project_root, 5970) == (915, 930)
    assert audit_formula_components(project_root, 5973) == (944, 957)
    assert audit_formula_components(project_root, 5985) == (1143, 1151)
    assert audit_formula_components(project_root, 5989) == (1157, 1167)
    assert audit_formula_components(project_root, 5990) == (1188, 1193)
    assert audit_formula_components(project_root, LCTT_INVESTMENT_PROPERTY_NET_ID) == (
        LCTT_INVESTMENT_PROPERTY_NET_COMPONENTS
    )
    for schema_id, components in (
        (5991, tuple(range(871, 876))),
        (5992, tuple(range(876, 882))),
        (5994, tuple(range(885, 888))),
        (5995, tuple(range(888, 895))),
        (5997, tuple(range(916, 921))),
        (6068, tuple(range(921, 928))),
        (5999, tuple(range(931, 934))),
        (6000, tuple(range(934, 941))),
        (6002, tuple(range(945, 952))),
        (6003, tuple(range(952, 955))),
        (6005, tuple(range(958, 961))),
        (6019, tuple(range(1130, 1137))),
        (6020, tuple(range(1137, 1141))),
        (1170, (6024, 6025)),
    ):
        assert audit_formula_components(project_root, schema_id) == components
    formula_ids = {
        record["schema_id"] for record in _verified_audit(project_root)["business_formulas"]
    }
    assert formula_ids.isdisjoint(range(5898, 5946))
    assert by_id[1944].parent_id is None
    assert by_id[1944].display_order == 1718
    assert set(TM_UNIVERSAL_SCHEMA_IDS) == {
        *range(5991, 6034),
        *range(6057, 6075),
    }


@lru_cache(maxsize=1)
def _verified_audit(project_root):
    return verify_business_schema_update(project_root, project_root / BUSINESS_UPDATE_AUDIT)


def audit_formula_components(project_root, schema_id: int) -> tuple[int, ...]:
    audit = _verified_audit(project_root)
    formula = next(
        record for record in audit["business_formulas"] if record["schema_id"] == schema_id
    )
    return tuple(formula["component_schema_ids"])
