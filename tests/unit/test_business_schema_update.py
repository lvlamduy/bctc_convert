from __future__ import annotations

from bctc_ai.core.hashing import sha256_file
from bctc_ai.schema.business_update import (
    BUSINESS_UPDATE_AUDIT,
    CDKT_BEFORE_SHA256,
    CDKT_TOTAL_EQUITY_COMPONENTS,
    CDKT_TOTAL_EQUITY_ID,
    CDKT_WORKBOOK,
    KQKD_BEFORE_SHA256,
    KQKD_TOTAL_OPERATING_INCOME_COMPONENTS,
    KQKD_TOTAL_OPERATING_INCOME_ID,
    KQKD_WORKBOOK,
    LCTT_BEFORE_SHA256,
    LCTT_INVESTMENT_CONTRIBUTION_NET_COMPONENTS,
    LCTT_INVESTMENT_CONTRIBUTION_NET_ID,
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
    TM_WORKBOOK,
    verify_business_schema_update,
)
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import load_all


def test_business_schema_migration_is_hash_bound_and_preserves_sealed_baselines(project_root):
    audit = verify_business_schema_update(project_root, project_root / BUSINESS_UPDATE_AUDIT)
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
    assert audit_formula_components(project_root, TM_TOTAL_INTERBANK_PROVISION_ID) == (
        TM_TOTAL_INTERBANK_PROVISION_COMPONENTS
    )
    assert by_id[4305].children == [4304, CDKT_TOTAL_EQUITY_ID]
    assert by_id[4376].children == [KQKD_TOTAL_OPERATING_INCOME_ID, 4391]
    assert by_id[4111].children == [
        4118,
        4119,
        4143,
        4144,
        4145,
        4146,
        LCTT_INVESTMENT_CONTRIBUTION_NET_ID,
        4147,
    ]
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
        735,
        736,
        TM_EDUCATION_ID,
        TM_HEALTH_SOCIAL_ID,
        738,
        739,
        740,
        741,
        742,
        743,
        TM_ARTS_RECREATION_ID,
        TM_OTHER_SERVICES_ID,
        TM_HOUSEHOLD_EMPLOYMENT_ID,
        744,
        745,
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
        )
    )
    assert by_id[717].children == [*range(718, 727), 5745]
    assert by_id[747].children == [5746]
    assert by_id[752].children == [753, 754, 755, 5747]
    assert by_id[TM_LOAN_BUSINESS_PARENT_ID].children == [*range(767, 783), 5748]
    assert by_id[TM_LOAN_BUSINESS_OTHER_ID].parent_id == TM_LOAN_BUSINESS_PARENT_ID
    assert tuple(by_id[TM_PROVISION_MOVEMENT_ID].children) == TM_PROVISION_MOVEMENT_COMPONENTS
    assert by_id[TM_GENERAL_PROVISION_MOVEMENT_ID].children == list(range(785, 792))
    assert by_id[TM_SPECIFIC_PROVISION_MOVEMENT_ID].children == list(range(793, 800))
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
    audit = verify_business_schema_update(project_root, project_root / BUSINESS_UPDATE_AUDIT)
    formula_ids = {record["schema_id"] for record in audit["business_formulas"]}
    assert formula_ids.isdisjoint(range(5898, 5946))
    assert by_id[1944].parent_id is None


def audit_formula_components(project_root, schema_id: int) -> tuple[int, ...]:
    audit = verify_business_schema_update(project_root, project_root / BUSINESS_UPDATE_AUDIT)
    formula = next(
        record for record in audit["business_formulas"] if record["schema_id"] == schema_id
    )
    return tuple(formula["component_schema_ids"])
