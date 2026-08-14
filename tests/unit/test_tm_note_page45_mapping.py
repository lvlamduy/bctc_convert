from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.mapping.tm_note_page45_mapping import (
    TM_PAGE45_MAPPED_SCHEMA_IDS,
    TM_PAGE45_MAPPING_POLICY_RELATIVE_PATH,
    TMPage45MappingError,
    TMPage45SchemaStatus,
    TMPage45SourceStatus,
    load_tm_page45_mapping_policy,
    reconcile_tm_page45_items,
    validate_tm_page45_mapping_result,
)
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.tm_note_page45 import load_tm_page45_policy, parse_tm_page45

_OCR_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0045-ppocrv6-word-box.json")
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_SCHEMA_WORKBOOK = Path("template/Bank_TM_ReportNormId.v2.xlsx")


@pytest.fixture(scope="module")
def page45_mapping(project_root: Path, tmp_path_factory: pytest.TempPathFactory):
    tmp_path = tmp_path_factory.mktemp("page45-mapping")
    render = Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={45},
        )[0].path
    )
    parsed = parse_tm_page45(
        project_root / _OCR_FIXTURE,
        render,
        load_tm_page45_policy(project_root / "config/tables/tm-note-page45-v1.yaml"),
    )
    _workbooks, schema = load_all(project_root / "template", project_root)
    _hierarchy_payload, hierarchy = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml",
        project_root,
        schema,
    )
    apply_hierarchy_reference(schema, hierarchy)
    policy = load_tm_page45_mapping_policy(project_root / TM_PAGE45_MAPPING_POLICY_RELATIVE_PATH)
    result = reconcile_tm_page45_items(
        parsed,
        schema=schema,
        policy=policy,
        source_pdf_path=project_root / _SOURCE_PDF,
        schema_workbook_path=project_root / _SCHEMA_WORKBOOK,
    )
    return SimpleNamespace(
        parsed=parsed,
        schema=schema,
        policy=policy,
        result=result,
        project_root=project_root,
    )


def test_page45_reconciles_exact_schema_source_and_assignment_denominators(
    page45_mapping: SimpleNamespace,
) -> None:
    result = page45_mapping.result

    assert validate_tm_page45_mapping_result(result) is result
    assert result.mapping_authority_scope.endswith("IDS_5946_5958_ONLY")
    assert result.mapping_authority_granted
    assert result.schema_item_count == 1_710
    assert result.status_reconciled_schema_count == 13
    assert result.mapped_schema_count == 13
    assert result.structural_mapped_schema_count == 2
    assert result.value_bearing_mapped_schema_count == 11
    assert result.not_observed_schema_count == 0
    assert result.not_applicable_schema_count == 0
    assert result.ambiguous_schema_count == 0
    assert result.unresolved_schema_count == 0
    assert result.unassessed_schema_count == 1_697
    assert result.source_row_count == 14
    assert result.mapped_source_row_count == 13
    assert result.source_only_validation_row_count == 1
    assert result.source_question_row_count == 0
    assert result.financial_slot_count == 24
    assert result.extracted_value_count == 14
    assert result.dash_count == 8
    assert result.blank_count == 2
    assert result.zero_count == 0
    assert result.mapped_assignment_count == 22
    assert result.mapped_value_count == 12
    assert result.external_validation_observation_count == 2


def test_all_thirteen_frozen_items_have_exact_hierarchy_and_unique_page45_owner(
    page45_mapping: SimpleNamespace,
) -> None:
    result = page45_mapping.result
    schema_by_id = {item.schema_id: item for item in page45_mapping.schema}
    mapped = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage45SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
    }

    assert mapped == TM_PAGE45_MAPPED_SCHEMA_IDS == set(range(5946, 5959))
    assert schema_by_id[5946].parent_id == 1128
    assert schema_by_id[5946].children == [5947, 5948]
    assert schema_by_id[5949].parent_id == 1128
    assert schema_by_id[5949].children == [5950, 5951, 5953, 5956]
    assert schema_by_id[5951].children == [5952]
    assert schema_by_id[5953].children == [5954, 5955]
    assert schema_by_id[5956].children == [5957, 5958]
    assert all(
        item.source_ids for item in result.schema_dispositions if item.report_norm_id in mapped
    )
    assert all(
        not item.source_ids
        for item in result.schema_dispositions
        if item.report_norm_id not in mapped
    )


def test_twenty_two_assignments_preserve_value_dash_blank_period_and_row_unit(
    page45_mapping: SimpleNamespace,
) -> None:
    assignments = page45_mapping.result.mapped_assignments
    by_id = {
        schema_id: [item for item in assignments if item.report_norm_id == schema_id]
        for schema_id in range(5947, 5959)
        if schema_id != 5949
    }

    assert {schema_id: [item.value for item in items] for schema_id, items in by_id.items()} == {
        5947: [8_054_999_909, 8_054_999_909],
        5948: [933, 815],
        5950: [None, None],
        5951: [8_054_999_909, 8_054_999_909],
        5952: [8_054_999_909, 8_054_999_909],
        5953: [None, None],
        5954: [None, None],
        5955: [None, None],
        5956: [8_054_999_909, 8_054_999_909],
        5957: [8_054_999_909, 8_054_999_909],
        5958: [None, None],
    }
    assert {item.observation for item in by_id[5950]} == {ObservationKind.BLANK.value}
    assert {
        item.observation for schema_id in (5953, 5954, 5955, 5958) for item in by_id[schema_id]
    } == {ObservationKind.DASH.value}
    assert [(item.unit, item.unit_multiplier, item.period_type) for item in by_id[5947]] == [
        ("SHARE", 1, "DURATION"),
        ("SHARE", 1, "DURATION"),
    ]
    assert [(item.unit, item.unit_multiplier, item.period_type) for item in by_id[5948]] == [
        ("VND_PER_SHARE", 1, "DURATION"),
        ("VND_PER_SHARE", 1, "DURATION"),
    ]
    assert {
        (item.unit, item.unit_multiplier, item.period_type)
        for schema_id in range(5950, 5959)
        for item in by_id[schema_id]
    } == {("SHARE", 1, "SNAPSHOT")}
    assert {
        (item.period_role, item.period_start, item.period_end) for item in by_id[5947] + by_id[5948]
    } == {
        ("CURRENT", "2026-01-01", "2026-03-31"),
        ("COMPARATIVE", "2025-01-01", "2025-03-31"),
    }
    assert {
        (item.period_role, item.period_start, item.period_end)
        for schema_id in range(5950, 5959)
        for item in by_id[schema_id]
    } == {
        ("CURRENT", "2026-03-31", "2026-03-31"),
        ("COMPARATIVE", "2025-12-31", "2025-12-31"),
    }


def test_profit_cells_are_validation_only_for_page44_owner_1131_and_eps_checks_pass(
    page45_mapping: SimpleNamespace,
) -> None:
    result = page45_mapping.result
    profit = result.external_validation_observations
    source_only = [
        item
        for item in result.source_dispositions
        if item.status == TMPage45SourceStatus.SOURCE_ONLY_EXTERNAL_VALIDATION.value
    ]

    assert [(item.value, item.period_role) for item in profit] == [
        (7_515_513, "CURRENT"),
        (6_567_740, "COMPARATIVE"),
    ]
    assert {item.external_report_norm_id for item in profit} == {1131}
    assert {item.external_owner_scope for item in profit} == {"page-0044"}
    assert all(not item.mapping_authority_granted for item in profit)
    assert all(item.report_norm_id != 1131 for item in result.mapped_assignments)
    assert len(source_only) == 1
    assert source_only[0].report_norm_id is None
    assert source_only[0].external_validation_report_norm_id == 1131
    assert result.accounting_check_count == 2
    assert result.accounting_pass_count == 2
    assert result.accounting_fail_count == 0
    assert [
        (check.expected_value, check.observed_value, check.residual)
        for check in result.accounting_checks
    ] == [
        (Decimal("933"), Decimal("933"), Decimal("0")),
        (Decimal("815"), Decimal("815"), Decimal("0")),
    ]


def test_status_evidence_and_mapping_policy_are_hash_bound_and_semantically_closed(
    page45_mapping: SimpleNamespace,
) -> None:
    result = page45_mapping.result
    policy = page45_mapping.policy

    assert result.status_evidence_sha256 == (
        "d9879f30c8744050294afb4d2047f7187bcb920aeca0ca596492cb2558c5c282"
    )
    assert result.policy_sha256 == sha256_file(policy.source_path)
    assert set(policy.forbidden_mapping_inputs) == {
        "numeric_cell_text_as_item_selector",
        "numeric_value_magnitude_as_item_selector",
        "historical_or_mongodb_values",
        "human_review_answers",
        "dash_as_zero",
        "blank_as_zero",
        "zero_as_blank_or_dash",
        "header_trieu_dong_as_share_or_eps_unit",
        "schema_id_outside_page45_scope",
        "external_owner_1131_as_page45_owned_item",
        "profit_row_as_duplicate_mapped_assignment",
        "period_axis_swapping",
        "accounting_equation_result_as_item_selector",
        "accounting_equation_result_as_extracted_value",
    }


def test_policy_target_drift_cannot_claim_external_1131_as_page45_owner(
    page45_mapping: SimpleNamespace,
) -> None:
    drifted_targets = dict(page45_mapping.policy.row_target_ids)
    drifted_targets["WEIGHTED_AVERAGE_ORDINARY_SHARES"] = 1131
    drifted = replace(
        page45_mapping.policy,
        row_target_ids=tuple(drifted_targets.items()),
    )

    with pytest.raises(TMPage45MappingError, match="policy target drifted"):
        reconcile_tm_page45_items(
            page45_mapping.parsed,
            schema=page45_mapping.schema,
            policy=drifted,
            source_pdf_path=page45_mapping.project_root / _SOURCE_PDF,
            schema_workbook_path=page45_mapping.project_root / _SCHEMA_WORKBOOK,
        )
