from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from bctc_ai.mapping.tm_note_page41_mapping import (
    TM_PAGE41_POLICY_RELATIVE_PATH,
    TMPage41MappingError,
    TMPage41SchemaStatus,
    TMPage41SourceStatus,
    load_tm_page41_mapping_policy,
    reconcile_tm_page41_items,
    validate_tm_page41_mapping_result,
)
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.tm_note_page41 import load_tm_page41_policy, parse_tm_page41

_OCR_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0041-ppocrv6-word-box.json")
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_MAPPED_IDS = {
    942,
    943,
    944,
    955,
    956,
    957,
    965,
    5972,
    5973,
    5974,
    *range(6002, 6007),
}
_UNRESOLVED_IDS: set[int] = set()
_NOT_OBSERVED_IDS = {*range(945, 955), 958, 959, 960, 961, 962, 963, 964}


def _mapped(project_root: Path, tmp_path: Path):
    render = Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={41},
        )[0].path
    )
    parsed = parse_tm_page41(
        project_root / _OCR_FIXTURE,
        render,
        load_tm_page41_policy(project_root / "config/tables/tm-note-page41-v1.yaml"),
    )
    _workbooks, schema = load_all(project_root / "template", project_root)
    return reconcile_tm_page41_items(
        parsed,
        schema=schema,
        policy=load_tm_page41_mapping_policy(project_root / TM_PAGE41_POLICY_RELATIVE_PATH),
        source_pdf_path=project_root / _SOURCE_PDF,
    )


def test_page41_reconciles_complete_942_965_branch_with_exact_statuses(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert validate_tm_page41_mapping_result(result) is result
    assert result.mapping_authority_scope.endswith("TOTAL_COLUMN_FIXED_ROWS_ONLY")
    assert result.mapping_authority_granted
    assert result.schema_item_count == 1_713
    assert result.status_reconciled_schema_count == 32
    assert result.mapped_schema_count == 15
    assert result.unresolved_schema_count == 0
    assert result.not_observed_schema_count == 17
    assert result.not_applicable_schema_count == 0
    assert result.unassessed_schema_count == 1_681
    assert result.fully_verified_schema_count == 0
    assert result.source_row_count == 25
    assert result.mapped_source_row_count == 25
    assert result.partial_source_row_count == 19
    assert result.source_only_row_count == 0
    assert result.source_question_row_count == 0
    assert result.context_source_row_count == 0
    assert result.financial_slot_count == 57
    assert result.extracted_value_count == 51
    assert result.dash_count == 6
    assert result.mapped_value_count == 18
    assert result.class_axis_slot_count == 38
    assert result.class_axis_value_count == 33


def test_exact_mapped_unresolved_not_observed_and_unassessed_sets(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in {item.value for item in TMPage41SchemaStatus}
    }

    assert by_status[TMPage41SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] == _MAPPED_IDS
    assert by_status[TMPage41SchemaStatus.UNRESOLVED.value] == _UNRESOLVED_IDS
    assert by_status[TMPage41SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] == (_NOT_OBSERVED_IDS)
    assert len(by_status[TMPage41SchemaStatus.UNASSESSED.value]) == 1_681
    assert _MAPPED_IDS | _UNRESOLVED_IDS | _NOT_OBSERVED_IDS == (
        set(range(942, 966)) | {5972, 5973, 5974} | set(range(6002, 6007))
    )


def test_nineteen_total_cells_preserve_panel_duration_or_row_local_snapshot_periods(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    partial = [
        item
        for item in result.source_dispositions
        if item.status == TMPage41SourceStatus.PARTIAL_TOTAL_COLUMN_MAPPING.value
    ]

    assert len(partial) == 19
    assert all(
        len(item.mapped_assignments) == 1
        and item.mapped_assignments[0].cell_index == 2
        and item.mapped_assignments[0].axis_role == "TOTAL"
        for item in partial
    )
    assert all(not item.question_group_ids for item in partial)
    actual = {
        (item.panel_key, item.row_key): (
            item.mapped_assignments[0].report_norm_id,
            item.mapped_assignments[0].value,
            item.mapped_assignments[0].period_start,
            item.mapped_assignments[0].period_end,
            item.mapped_assignments[0].period_type,
        )
        for item in partial
    }
    assert actual == {
        ("Q1_2026", "GROSS_OPENING"): (
            944,
            Decimal("255126"),
            "2026-01-01",
            "2026-03-31",
            "DURATION_PANEL",
        ),
        ("Q1_2026", "GROSS_INCREASE"): (
            6002,
            None,
            "2026-01-01",
            "2026-03-31",
            "DURATION_PANEL",
        ),
        ("Q1_2026", "GROSS_OTHER"): (
            6004,
            Decimal("-4971"),
            "2026-01-01",
            "2026-03-31",
            "DURATION_PANEL",
        ),
        ("Q1_2026", "GROSS_CLOSING"): (
            955,
            Decimal("250155"),
            "2026-01-01",
            "2026-03-31",
            "DURATION_PANEL",
        ),
        ("Q1_2026", "DEPRECIATION_OPENING"): (
            957,
            Decimal("32313"),
            "2026-01-01",
            "2026-03-31",
            "DURATION_PANEL",
        ),
        ("Q1_2026", "DEPRECIATION_INCREASE"): (
            6005,
            Decimal("1528"),
            "2026-01-01",
            "2026-03-31",
            "DURATION_PANEL",
        ),
        ("Q1_2026", "DEPRECIATION_CLOSING"): (
            965,
            Decimal("33841"),
            "2026-01-01",
            "2026-03-31",
            "DURATION_PANEL",
        ),
        ("Q1_2026", "NET_OPENING"): (
            5973,
            Decimal("222813"),
            "2026-01-01",
            "2026-01-01",
            "SNAPSHOT",
        ),
        ("Q1_2026", "NET_CLOSING"): (
            5974,
            Decimal("216314"),
            "2026-03-31",
            "2026-03-31",
            "SNAPSHOT",
        ),
        ("FY_2025", "GROSS_OPENING"): (
            944,
            Decimal("260415"),
            "2025-01-01",
            "2025-12-31",
            "DURATION_PANEL",
        ),
        ("FY_2025", "GROSS_INCREASE"): (
            6002,
            Decimal("4971"),
            "2025-01-01",
            "2025-12-31",
            "DURATION_PANEL",
        ),
        ("FY_2025", "GROSS_DECREASE"): (
            6003,
            Decimal("-10260"),
            "2025-01-01",
            "2025-12-31",
            "DURATION_PANEL",
        ),
        ("FY_2025", "GROSS_CLOSING"): (
            955,
            Decimal("255126"),
            "2025-01-01",
            "2025-12-31",
            "DURATION_PANEL",
        ),
        ("FY_2025", "DEPRECIATION_OPENING"): (
            957,
            Decimal("26300"),
            "2025-01-01",
            "2025-12-31",
            "DURATION_PANEL",
        ),
        ("FY_2025", "DEPRECIATION_INCREASE"): (
            6005,
            Decimal("6145"),
            "2025-01-01",
            "2025-12-31",
            "DURATION_PANEL",
        ),
        ("FY_2025", "DEPRECIATION_OTHER"): (
            6006,
            Decimal("-132"),
            "2025-01-01",
            "2025-12-31",
            "DURATION_PANEL",
        ),
        ("FY_2025", "DEPRECIATION_CLOSING"): (
            965,
            Decimal("32313"),
            "2025-01-01",
            "2025-12-31",
            "DURATION_PANEL",
        ),
        ("FY_2025", "NET_OPENING"): (
            5973,
            Decimal("234115"),
            "2025-01-01",
            "2025-01-01",
            "SNAPSHOT",
        ),
        ("FY_2025", "NET_CLOSING"): (
            5974,
            Decimal("222813"),
            "2025-12-31",
            "2025-12-31",
            "SNAPSHOT",
        ),
    }
    assert all(
        (item.period_start, item.period_end, item.period_type)
        == (
            item.mapped_assignments[0].period_start,
            item.mapped_assignments[0].period_end,
            item.mapped_assignments[0].period_type,
        )
        for item in partial
    )
    assert result.note_title_assignment.report_norm_id == 942
    assert result.note_title_assignment.value is None


def test_structural_parents_repeat_as_provenance_without_duplicate_value_export(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    structural = [
        item
        for item in result.source_dispositions
        if item.status == TMPage41SourceStatus.MAPPED_STRUCTURAL_SCOPED.value
    ]

    assert [(item.panel_key, item.row_key) for item in structural] == [
        ("Q1_2026", "GROSS_COST_SECTION"),
        ("Q1_2026", "ACCUMULATED_DEPRECIATION_SECTION"),
        ("Q1_2026", "NET_BOOK_VALUE_SECTION"),
        ("FY_2025", "GROSS_COST_SECTION"),
        ("FY_2025", "ACCUMULATED_DEPRECIATION_SECTION"),
        ("FY_2025", "NET_BOOK_VALUE_SECTION"),
    ]
    assert [item.mapped_assignments[0].report_norm_id for item in structural] == [
        943,
        956,
        5972,
        943,
        956,
        5972,
    ]
    assert all(item.mapped_assignments[0].value is None for item in structural)


def test_class_axes_remain_provenance_only_and_questions_are_retired(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.question_group_ids == ()
    assert all(not item.question_group_ids for item in result.source_dispositions)
    unresolved = [
        item
        for item in result.schema_dispositions
        if item.status == TMPage41SchemaStatus.UNRESOLVED.value
    ]
    assert unresolved == []
    mapped_dash = next(
        item
        for item in result.source_dispositions
        if item.panel_key == "Q1_2026" and item.row_key == "GROSS_INCREASE"
    )
    assert mapped_dash.mapped_assignments[0].report_norm_id == 6002
    assert mapped_dash.mapped_assignments[0].observation == "DASH"
    assert mapped_dash.mapped_assignments[0].value is None
    assert mapped_dash.visual_cell_evidence[2] is not None


def test_fifty_two_checks_pass_or_remain_dash_not_testable_without_failures(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.accounting_check_count == 52
    assert result.accounting_pass_count == 43
    assert result.accounting_not_testable_count == 9
    assert result.accounting_fail_count == 0
    assert (
        len(
            [
                check
                for check in result.accounting_checks
                if check.check_id.startswith("CROSS_PANEL_") and check.status == "PASS"
            ]
        )
        == 9
    )
    not_testable = [
        check
        for check in result.accounting_checks
        if check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO"
    ]
    assert len(not_testable) == 9
    assert all(check.expected_value is None and check.residual is None for check in not_testable)
    assert all(check.residual == 0 for check in result.accounting_checks if check.status == "PASS")
    assert result.dash_pixel_evidence_sha256 == (
        "7afbe3d6debce41437ec7e3675a2befcdab6ba9dcf529168b4c483358cb64757"
    )


def test_mapping_policy_forbids_class_axis_export_values_history_review_and_dash_zero(
    project_root: Path, tmp_path: Path
) -> None:
    policy_path = project_root / TM_PAGE41_POLICY_RELATIVE_PATH
    policy = load_tm_page41_mapping_policy(policy_path)

    assert set(policy.forbidden_mapping_inputs) == {
        "numeric_cell_text",
        "numeric_cell_value_as_item_selector",
        "numeric_value_magnitude",
        "class_axis_value_export_to_total_schema",
        "historical_or_mongodb_values",
        "human_review_answers",
        "dash_as_zero",
        "accounting_equation_result_as_item_selector",
        "cross_panel_value_as_item_selector",
    }
    period_tampered = tmp_path / "page41-mapping-period-tampered.yaml"
    period_tampered.write_text(
        policy_path.read_text(encoding="utf-8").replace(
            "assignment_period: OPENING_SNAPSHOT", "assignment_period: PANEL_DURATION", 1
        ),
        encoding="utf-8",
    )
    with pytest.raises(TMPage41MappingError, match="mapping row identity"):
        load_tm_page41_mapping_policy(period_tampered)
