from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from bctc_ai.mapping.tm_note_page41_mapping import (
    TM_PAGE41_POLICY_RELATIVE_PATH,
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
_MAPPED_IDS = {942, 943, 944, 955, 956, 957, 965}
_UNRESOLVED_IDS = {*range(945, 955), 958, 959, 960, 964}
_NOT_OBSERVED_IDS = {961, 962, 963}


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
    assert result.schema_item_count == 1_417
    assert result.status_reconciled_schema_count == 24
    assert result.mapped_schema_count == 7
    assert result.unresolved_schema_count == 14
    assert result.not_observed_schema_count == 3
    assert result.not_applicable_schema_count == 0
    assert result.unassessed_schema_count == 1_393
    assert result.fully_verified_schema_count == 0
    assert result.source_row_count == 25
    assert result.mapped_source_row_count == 12
    assert result.partial_source_row_count == 8
    assert result.source_only_row_count == 13
    assert result.source_question_row_count == 19
    assert result.context_source_row_count == 2
    assert result.financial_slot_count == 57
    assert result.extracted_value_count == 51
    assert result.dash_count == 6
    assert result.mapped_value_count == 8
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
    assert len(by_status[TMPage41SchemaStatus.UNASSESSED.value]) == 1_393
    assert _MAPPED_IDS | _UNRESOLVED_IDS | _NOT_OBSERVED_IDS == set(range(942, 966))


def test_only_eight_total_cells_map_across_both_duration_panels(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    partial = [
        item
        for item in result.source_dispositions
        if item.status == TMPage41SourceStatus.PARTIAL_TOTAL_COLUMN_MAPPING.value
    ]

    assert len(partial) == 8
    assert all(
        len(item.mapped_assignments) == 1
        and item.mapped_assignments[0].cell_index == 2
        and item.mapped_assignments[0].axis_role == "TOTAL"
        and item.question_group_ids == ("Q037",)
        for item in partial
    )
    actual = {
        (item.panel_key, item.row_key): (
            item.mapped_assignments[0].report_norm_id,
            item.mapped_assignments[0].value,
            item.period_start,
            item.period_end,
        )
        for item in partial
    }
    assert actual == {
        ("Q1_2026", "GROSS_OPENING"): (
            944,
            Decimal("255126"),
            "2026-01-01",
            "2026-03-31",
        ),
        ("Q1_2026", "GROSS_CLOSING"): (
            955,
            Decimal("250155"),
            "2026-01-01",
            "2026-03-31",
        ),
        ("Q1_2026", "DEPRECIATION_OPENING"): (
            957,
            Decimal("32313"),
            "2026-01-01",
            "2026-03-31",
        ),
        ("Q1_2026", "DEPRECIATION_CLOSING"): (
            965,
            Decimal("33841"),
            "2026-01-01",
            "2026-03-31",
        ),
        ("FY_2025", "GROSS_OPENING"): (
            944,
            Decimal("260415"),
            "2025-01-01",
            "2025-12-31",
        ),
        ("FY_2025", "GROSS_CLOSING"): (
            955,
            Decimal("255126"),
            "2025-01-01",
            "2025-12-31",
        ),
        ("FY_2025", "DEPRECIATION_OPENING"): (
            957,
            Decimal("26300"),
            "2025-01-01",
            "2025-12-31",
        ),
        ("FY_2025", "DEPRECIATION_CLOSING"): (
            965,
            Decimal("32313"),
            "2025-01-01",
            "2025-12-31",
        ),
    }
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
        ("FY_2025", "GROSS_COST_SECTION"),
        ("FY_2025", "ACCUMULATED_DEPRECIATION_SECTION"),
    ]
    assert [item.mapped_assignments[0].report_norm_id for item in structural] == [
        943,
        956,
        943,
        956,
    ]
    assert all(item.mapped_assignments[0].value is None for item in structural)


def test_q037_q042_q043_q044_cover_class_axes_aggregates_and_net_rows(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.question_group_ids == ("Q037", "Q042", "Q043", "Q044")
    by_question = {
        question: [
            item.row_key
            for item in result.source_dispositions
            if question in item.question_group_ids
        ]
        for question in result.question_group_ids
    }
    assert len(by_question["Q037"]) == 19
    assert by_question["Q042"] == [
        "GROSS_INCREASE",
        "GROSS_OTHER",
        "GROSS_INCREASE",
        "GROSS_DECREASE",
    ]
    assert by_question["Q043"] == [
        "DEPRECIATION_INCREASE",
        "DEPRECIATION_INCREASE",
        "DEPRECIATION_OTHER",
    ]
    assert by_question["Q044"] == ["NET_OPENING", "NET_CLOSING"] * 2
    unresolved = [
        item
        for item in result.schema_dispositions
        if item.status == TMPage41SchemaStatus.UNRESOLVED.value
    ]
    assert all(item.source_refs for item in unresolved)


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
    project_root: Path,
) -> None:
    policy = load_tm_page41_mapping_policy(project_root / TM_PAGE41_POLICY_RELATIVE_PATH)

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
