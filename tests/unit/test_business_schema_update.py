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


def audit_formula_components(project_root, schema_id: int) -> tuple[int, ...]:
    audit = verify_business_schema_update(project_root, project_root / BUSINESS_UPDATE_AUDIT)
    formula = next(
        record for record in audit["business_formulas"] if record["schema_id"] == schema_id
    )
    return tuple(formula["component_schema_ids"])
