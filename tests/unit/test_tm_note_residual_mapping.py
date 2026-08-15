from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from bctc_ai.mapping.tm_note_mapping import (
    TM_PAGE30_MAPPED_VALUE_COUNT,
    TM_PAGE30_SOURCE_ROW_COUNT,
)
from bctc_ai.mapping.tm_note_page51_mapping import (
    TM_PAGE51_FINANCIAL_SLOT_COUNT,
    TM_PAGE51_SOURCE_ROW_COUNT,
)
from bctc_ai.mapping.tm_note_residual_mapping import (
    TM_RESIDUAL_MAPPED_IDS,
    TM_RESIDUAL_NOT_OBSERVED_IDS,
    TM_RESIDUAL_SCOPE_IDS,
    TMResidualMappingError,
    TMResidualSchemaStatus,
    load_tm_residual_mapping_policy,
    reconcile_tm_residual_items,
)
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import load_all

_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_SCHEMA_WORKBOOK = Path("template/Bank_TM_ReportNormId.v2.xlsx")


@pytest.fixture(scope="module")
def residual_inputs(project_root: Path):
    _, schema = load_all(project_root / "template", project_root)
    _, hierarchy = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml",
        project_root,
        schema,
    )
    apply_hierarchy_reference(schema, hierarchy)
    policy = load_tm_residual_mapping_policy(
        project_root / "config/mapping/tm-note-residual-v1.yaml"
    )
    all_tm_ids = {item.schema_id for item in schema if item.statement_type == "TM"}
    return schema, policy, all_tm_ids


@pytest.fixture(scope="module")
def residual_result(project_root: Path, residual_inputs):
    schema, policy, all_tm_ids = residual_inputs
    return reconcile_tm_residual_items(
        schema,
        policy=policy,
        project_root=project_root,
        source_pdf_path=project_root / _SOURCE_PDF,
        schema_workbook_path=project_root / _SCHEMA_WORKBOOK,
        existing_owned_schema_ids=all_tm_ids - TM_RESIDUAL_SCOPE_IDS,
    )


def test_exact_residual_91_reconciles_without_numeric_or_source_row_mutation(
    residual_result,
) -> None:
    result = residual_result

    assert result.schema_item_count == 1_714
    assert result.status_reconciled_schema_count == 91
    assert result.mapped_schema_count == 2
    assert result.not_observed_schema_count == 89
    assert result.ambiguous_schema_count == 0
    assert result.unresolved_schema_count == 0
    assert result.not_applicable_schema_count == 0
    assert result.extraction_miss_schema_count == 0
    assert result.unassessed_schema_count == 1_623
    assert result.structural_evidence_count == 2
    assert result.source_row_count_delta == 0
    assert result.financial_slot_count == 0
    assert result.mapped_assignment_count == 0
    assert TM_PAGE30_SOURCE_ROW_COUNT == 22
    assert TM_PAGE30_MAPPED_VALUE_COUNT == 38
    assert TM_PAGE51_SOURCE_ROW_COUNT == 11
    assert TM_PAGE51_FINANCIAL_SLOT_COUNT == 18


def test_only_560_and_1259_are_source_backed_structural_mappings(residual_result) -> None:
    mapped = {
        item.report_norm_id: item
        for item in residual_result.schema_dispositions
        if item.status == TMResidualSchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
    }
    not_observed = {
        item.report_norm_id
        for item in residual_result.schema_dispositions
        if item.status == TMResidualSchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
    }
    evidence = {item.report_norm_id: item for item in residual_result.structural_evidence}

    assert set(mapped) == set(evidence) == TM_RESIDUAL_MAPPED_IDS
    assert not_observed == TM_RESIDUAL_NOT_OBSERVED_IDS
    assert mapped[560].source_ids == ("page-0030:section-title",)
    assert mapped[1259].source_ids == ("page-0051:off_balance_commitments:row-0001",)
    assert evidence[560].visible_label_similarity == pytest.approx(0.977778)
    assert evidence[1259].visible_label_similarity == pytest.approx(0.947368)
    assert all(
        item.value_status == "STRUCTURAL_HEADING_NO_VALUE_NO_FINANCIAL_SLOT"
        for item in evidence.values()
    )
    assert {item.source_role for item in evidence.values()} == {"STATEMENT_SECTION_TITLE"}
    assert all(
        item.bbox[2] > item.bbox[0] and item.bbox[3] > item.bbox[1] for item in evidence.values()
    )


def test_residual_scope_fails_closed_on_overlap_or_policy_drift(
    project_root: Path,
    residual_inputs,
) -> None:
    schema, policy, all_tm_ids = residual_inputs
    common = {
        "schema": schema,
        "policy": policy,
        "project_root": project_root,
        "source_pdf_path": project_root / _SOURCE_PDF,
        "schema_workbook_path": project_root / _SCHEMA_WORKBOOK,
        "existing_owned_schema_ids": all_tm_ids - TM_RESIDUAL_SCOPE_IDS,
    }
    with pytest.raises(TMResidualMappingError, match="overlaps"):
        reconcile_tm_residual_items(
            **{**common, "existing_owned_schema_ids": {*common["existing_owned_schema_ids"], 560}}
        )
    with pytest.raises(TMResidualMappingError, match="in-memory policy"):
        reconcile_tm_residual_items(
            **{
                **common,
                "policy": replace(
                    policy,
                    not_observed_schema_ids=policy.not_observed_schema_ids[:-1],
                ),
            }
        )
