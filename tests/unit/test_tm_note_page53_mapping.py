from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from bctc_ai.mapping.tm_note_page53_mapping import (
    TMPage53MappingError,
    TMPage53SchemaStatus,
    load_tm_page53_mapping_policy,
    reconcile_tm_page53_items,
)
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.tm_note_page53 import load_tm_page53_policy, parse_tm_page53

_OCR_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0053-ppocrv6-word-box.json")
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_SCHEMA_WORKBOOK = Path("template/Bank_TM_ReportNormId.v2.xlsx")


def _inputs(project_root: Path, tmp_path: Path):
    render = Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={53},
        )[0].path
    )
    parsed = parse_tm_page53(
        project_root / _OCR_FIXTURE,
        render,
        load_tm_page53_policy(project_root / "config/tables/tm-note-page53-v1.yaml"),
    )
    _, schema = load_all(project_root / "template", project_root)
    _, hierarchy = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml",
        project_root,
        schema,
    )
    apply_hierarchy_reference(schema, hierarchy)
    policy = load_tm_page53_mapping_policy(project_root / "config/mapping/tm-note-page53-v1.yaml")
    return parsed, schema, policy


def _mapped(project_root: Path, tmp_path: Path):
    parsed, schema, policy = _inputs(project_root, tmp_path)
    return reconcile_tm_page53_items(
        parsed,
        schema=schema,
        policy=policy,
        source_pdf_path=project_root / _SOURCE_PDF,
        schema_workbook_path=project_root / _SCHEMA_WORKBOOK,
    )


def test_page53_reconciles_exact_schema_source_and_cell_denominators(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.schema_item_count == 1_705
    assert result.status_reconciled_schema_count == 44
    assert result.mapped_schema_count == 44
    assert result.structural_mapped_schema_count == 8
    assert result.value_bearing_mapped_schema_count == 36
    assert result.unassessed_schema_count == 1_661
    assert result.not_observed_schema_count == 0
    assert result.ambiguous_schema_count == 0
    assert result.unresolved_schema_count == 0
    assert result.fully_verified_schema_count == 0
    assert result.source_row_count == result.mapped_source_row_count == 14
    assert result.structural_source_row_count == 2
    assert result.numeric_source_row_count == 12
    assert result.source_question_row_count == 0
    assert result.financial_slot_count == result.mapped_assignment_count == 72
    assert result.extracted_value_count == 68
    assert result.dash_count == 4


def test_page53_owns_exact_5762_5805_hierarchy_with_complete_provenance(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    mapped = {
        item.report_norm_id: item
        for item in result.schema_dispositions
        if item.status == TMPage53SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
    }
    unassessed = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage53SchemaStatus.UNASSESSED.value
    }

    assert set(mapped) == set(range(5762, 5806))
    assert len(unassessed) == 1_661
    assert all(item.source_ids for item in mapped.values())
    assert all(
        not item.source_ids
        for item in result.schema_dispositions
        if item.report_norm_id in unassessed
    )
    assert [item.report_norm_ids for item in result.source_dispositions[:2]] == [
        (5762,),
        (5763,),
    ]
    assert all(not item.question_required for item in result.source_dispositions)


def test_page53_transposes_exact_printed_cells_to_metric_children(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    assignments = {
        (item.report_norm_id, item.period_role): item for item in result.mapped_assignments
    }

    assert assignments[(5765, "CURRENT")].value == 1_158_931_821
    assert assignments[(5765, "COMPARATIVE")].value == 1_172_468_605
    assert assignments[(5793, "CURRENT")].value == -38_865_441
    assert assignments[(5793, "COMPARATIVE")].value == -35_496_903
    assert assignments[(5800, "CURRENT")].value == 1_611_222_764
    assert assignments[(5803, "CURRENT")].value == 37_600_291
    assert assignments[(5803, "COMPARATIVE")].value == 121_589_719
    assert assignments[(5805, "CURRENT")].value == 9_628_386
    assert assignments[(5805, "COMPARATIVE")].value == 34_268_358
    dash = [item for item in result.mapped_assignments if item.observation == "DASH"]
    assert [(item.report_norm_id, item.period_role) for item in dash] == [
        (5795, "CURRENT"),
        (5798, "CURRENT"),
        (5795, "COMPARATIVE"),
        (5798, "COMPARATIVE"),
    ]
    assert all(item.value is None and item.axis_key == "ELIMINATION" for item in dash)
    assert {(item.unit, item.unit_multiplier) for item in result.mapped_assignments} == {
        ("VND", 1_000_000)
    }
    assert all(
        item.period_type == "SNAPSHOT"
        for item in result.mapped_assignments
        if item.metric_key in {"ASSETS", "LIABILITIES", "FIXED_ASSETS"}
    )
    assert all(
        item.period_type == "DURATION"
        for item in result.mapped_assignments
        if item.metric_key in {"REVENUE", "EXPENSE", "PROFIT_BEFORE_TAX"}
    )


def test_page53_formulas_and_page54_totals_are_validation_only_with_dash_not_testable(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.validation_check_count == 36
    assert result.validation_pass_count == 30
    assert result.validation_not_testable_count == 6
    assert all(check.status != "FAIL" for check in result.validation_checks)
    assert (
        sum(check.check_kind == "SEGMENT_SUM_VALIDATION_ONLY" for check in result.validation_checks)
        == 12
    )
    assert (
        sum(
            check.check_kind == "PBT_SUBTRACTION_VALIDATION_ONLY"
            for check in result.validation_checks
        )
        == 12
    )
    assert (
        sum(
            check.check_kind == "EXTERNAL_PAGE54_TOTAL_VALIDATION_ONLY"
            for check in result.validation_checks
        )
        == 12
    )
    segment_sums = [
        check
        for check in result.validation_checks
        if check.check_kind == "SEGMENT_SUM_VALIDATION_ONLY"
    ]
    assert sum(check.status == "PASS" for check in segment_sums) == 8
    segment_not_testable = [
        check for check in segment_sums if check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO"
    ]
    assert [(check.period_role, check.metric_key) for check in segment_not_testable] == [
        ("CURRENT", "FIXED_ASSETS"),
        ("CURRENT", "PROFIT_BEFORE_TAX"),
        ("COMPARATIVE", "FIXED_ASSETS"),
        ("COMPARATIVE", "PROFIT_BEFORE_TAX"),
    ]
    assert all(
        check.expected_value is None and check.residual is None for check in segment_not_testable
    )
    pbt_checks = [
        check
        for check in result.validation_checks
        if check.check_kind == "PBT_SUBTRACTION_VALIDATION_ONLY"
    ]
    assert sum(check.status == "PASS" for check in pbt_checks) == 10
    elimination_pbt = [check for check in pbt_checks if check.axis_key == "ELIMINATION"]
    assert len(elimination_pbt) == 2
    assert all(
        check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO"
        and check.expected_value == 0
        and check.observed_value is None
        and check.residual is None
        for check in elimination_pbt
    )
    external = [
        check
        for check in result.validation_checks
        if check.check_kind == "EXTERNAL_PAGE54_TOTAL_VALIDATION_ONLY"
    ]
    assert all(check.external_owner_scope == "page-0054" for check in external)
    assert all(check.status == "PASS" and check.residual == 0 for check in external)
    assert dict(result.total_formulas_validation_only)[5805] == (
        5770,
        5777,
        5784,
        5791,
        5798,
    )
    assert dict(result.pbt_formulas_validation_only)[5798] == (5796, 5797)
    assert dict(result.pbt_formulas_validation_only)[5805] == (5803, 5804)
    assert all("VALIDATION_ONLY" in check.check_kind for check in result.validation_checks)


def test_page53_schema_hierarchy_and_mapping_policy_fail_closed(
    project_root: Path, tmp_path: Path
) -> None:
    parsed, schema, policy = _inputs(project_root, tmp_path)
    drifted = deepcopy(schema)
    next(
        item for item in drifted if item.statement_type == "TM" and item.schema_id == 5805
    ).parent_id = 5763

    with pytest.raises(TMPage53MappingError, match="scope hash drifted"):
        reconcile_tm_page53_items(
            parsed,
            schema=drifted,
            policy=policy,
            source_pdf_path=project_root / _SOURCE_PDF,
            schema_workbook_path=project_root / _SCHEMA_WORKBOOK,
        )

    policy_path = project_root / "config/mapping/tm-note-page53-v1.yaml"
    tampered = tmp_path / "page53-mapping-tampered.yaml"
    tampered.write_text(
        policy_path.read_text(encoding="utf-8").replace(
            "ASSETS: [5765, 5772", "ASSETS: [5766, 5772", 1
        ),
        encoding="utf-8",
    )
    with pytest.raises(TMPage53MappingError, match="metric targets drifted"):
        load_tm_page53_mapping_policy(tampered)


def test_page53_forbids_value_equation_dash_and_page54_selection(project_root: Path) -> None:
    policy = load_tm_page53_mapping_policy(project_root / "config/mapping/tm-note-page53-v1.yaml")

    assert set(policy.forbidden_mapping_inputs) == {
        "numeric_cell_text_as_item_selector",
        "numeric_value_magnitude_as_item_selector",
        "historical_or_mongodb_values",
        "human_review_answers",
        "dash_as_zero",
        "accounting_equation_result_as_item_selector",
        "accounting_equation_result_as_extracted_value",
        "page54_value_as_page53_item_selector",
        "page54_value_as_page53_imputation",
        "schema_id_outside_page53_scope",
    }
