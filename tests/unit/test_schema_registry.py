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
        "CDKT": 77,
        "KQKD": 24,
        "LCTT": 107,
        "TM": 1385,
    }
    assert len(items) == len({item.schema_id for item in items}) == 1593
    tm = [item for item in items if item.statement_type == "TM"]
    assert tm[-2].schema_id == 1943
    assert tm[-2].next_id == 1944
    assert tm[-1].schema_id == 1944
    assert tm[-1].canonical_name == TM_1944_NAME
    assert tm[-1].display_order == 1384
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
