from __future__ import annotations

from pathlib import Path

from bctc_ai.mapping.tm_note_page31_mapping import (
    TM_PAGE31_POLICY_RELATIVE_PATH,
    TMPage31SchemaStatus,
    TMPage31SourceStatus,
    load_tm_page31_mapping_policy,
    reconcile_tm_page31_items,
    validate_tm_page31_mapping_result,
)
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.tm_note_word_box import load_tm_page31_policy, parse_tm_page31

_OCR_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0031-ppocrv6-word-box.json")
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_MAPPED_IDS = {
    592,
    617,
    618,
    619,
    620,
    621,
    622,
    626,
    627,
    716,
    717,
    718,
    721,
    722,
    723,
    725,
    746,
    747,
    748,
    749,
    750,
    751,
    752,
    753,
    754,
    755,
    1944,
    5745,
    5746,
    5747,
}
_NOT_OBSERVED_IDS = {616, 623, 624, 625, 628, 629, 630, 719, 720, 724, 726, 6057}
_NOT_APPLICABLE_IDS = set(range(593, 616))


def _mapped(project_root: Path, tmp_path: Path):
    parsed = parse_tm_page31(
        project_root / _OCR_FIXTURE,
        load_tm_page31_policy(project_root / "config/tables/tm-note-page31-v1.yaml"),
    )
    _workbooks, schema = load_all(project_root / "template", project_root)
    render = render_pages(
        project_root / _SOURCE_PDF,
        tmp_path / "render",
        dpi=300,
        page_numbers={31},
    )[0]
    return reconcile_tm_page31_items(
        parsed,
        schema=schema,
        policy=load_tm_page31_mapping_policy(project_root / TM_PAGE31_POLICY_RELATIVE_PATH),
        source_pdf_path=project_root / _SOURCE_PDF,
        source_render_path=project_root / render.path,
    )


def test_page31_reconciles_65_schema_statuses_and_maps_30_distinct_items(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert validate_tm_page31_mapping_result(result) is result
    assert result.status == "SCOPED_PAGE31_MAPPING_WITH_COMPLETE_ACCOUNTING_VALIDATION"
    assert result.mapping_authority_scope.endswith("PDF_PAGE_31_FIXED_ROWS_ONLY")
    assert result.mapping_authority_granted
    assert result.schema_item_count == 1_721
    assert result.status_reconciled_schema_count == 65
    assert result.mapped_schema_count == 30
    assert result.not_observed_schema_count == 12
    assert result.not_applicable_schema_count == 23
    assert result.unassessed_schema_count == (
        result.schema_item_count - result.status_reconciled_schema_count
    )
    assert result.fully_verified_schema_count == 0
    assert result.source_row_count == 33
    assert result.mapped_source_row_count == 29
    assert result.source_only_row_count == 4
    assert result.numeric_source_row_count == 28
    assert result.structural_blank_source_row_count == 5
    assert result.extracted_value_count == 56
    assert result.mapped_value_count == 48
    assert result.mapped_value_assignment_count == 50


def test_exact_mapped_not_observed_not_applicable_and_unassessed_sets(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in {item.value for item in TMPage31SchemaStatus}
    }

    assert by_status[TMPage31SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] == _MAPPED_IDS
    assert by_status[TMPage31SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] == (_NOT_OBSERVED_IDS)
    assert by_status[TMPage31SchemaStatus.SCHEMA_ITEM_NOT_APPLICABLE.value] == (_NOT_APPLICABLE_IDS)
    assert len(by_status[TMPage31SchemaStatus.UNASSESSED.value]) == (result.unassessed_schema_count)


def test_margin_rows_have_explicit_context_assignments_and_legacy_dual_provenance(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    primary = [item for item in result.source_dispositions if item.report_norm_id == 1944]
    contexts = {
        item.report_norm_id: item
        for item in result.source_dispositions
        if item.report_norm_id in {5746, 5747}
    }

    assert len(primary) == 1
    assert primary[0].row_id == "page-0031:loan_type:row-0008"
    assert primary[0].values == (15_520_372, 15_040_585)
    assert primary[0].canonical_name == (
        "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán"
    )
    assert primary[0].report_norm_ids == (1944, 5745)
    assert primary[0].assignment_roles == (
        "LEGACY_GLOBAL_PRIMARY",
        "CONTEXT_BRANCH_MEMBER",
    )
    assert contexts[5746].row_id == "page-0031:loan_quality:row-0003"
    assert contexts[5747].row_id == "page-0031:loan_maturity:row-0006"
    assert all(item.values == (15_520_372, 15_040_585) for item in contexts.values())


def test_seven_equations_across_two_periods_pass_with_zero_residual(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.accounting_check_count == result.accounting_pass_count == 14
    assert len({check.check_id for check in result.accounting_checks}) == 7
    assert {check.axis_role for check in result.accounting_checks} == {
        "CURRENT",
        "COMPARATIVE",
    }
    assert all(check.status == "PASS" and check.residual == 0 for check in result.accounting_checks)


def test_four_source_only_rows_are_exact_subtotals_or_repeated_grand_totals(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    source_only = {
        item.row_id
        for item in result.source_dispositions
        if item.status == TMPage31SourceStatus.SOURCE_ONLY_VALIDATION.value
    }

    assert source_only == {
        "page-0031:loan_type:row-0007",
        "page-0031:loan_quality:row-0008",
        "page-0031:loan_maturity:row-0005",
        "page-0031:loan_maturity:row-0007",
    }


def test_mapping_policy_forbids_values_history_review_and_equation_selection(
    project_root: Path,
) -> None:
    policy = load_tm_page31_mapping_policy(project_root / TM_PAGE31_POLICY_RELATIVE_PATH)

    assert set(policy.forbidden_mapping_inputs) == {
        "numeric_cell_text",
        "numeric_cell_value",
        "numeric_value_magnitude",
        "historical_or_mongodb_values",
        "human_review_answers",
        "accounting_equation_result_as_item_selector",
    }
