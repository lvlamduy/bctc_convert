from __future__ import annotations

from pathlib import Path

from bctc_ai.mapping.tm_note_page35_mapping import (
    TM_PAGE35_POLICY_RELATIVE_PATH,
    TMPage35SchemaStatus,
    TMPage35SourceStatus,
    load_tm_page35_mapping_policy,
    reconcile_tm_page35_items,
    validate_tm_page35_mapping_result,
)
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.tm_note_page35 import load_tm_page35_policy, parse_tm_page35

_OCR_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0035-ppocrv6-word-box.json")
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_MAPPED_IDS = {800, 801, 803, 804, 805, 807, 808, 809, 824, 825}
_NOT_OBSERVED_IDS = {
    802,
    806,
    810,
    811,
    *range(812, 824),
    826,
    827,
    828,
}


def _mapped(project_root: Path, tmp_path: Path):
    render = Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={35},
        )[0].path
    )
    parsed = parse_tm_page35(
        project_root / _OCR_FIXTURE,
        render,
        load_tm_page35_policy(project_root / "config/tables/tm-note-page35-v1.yaml"),
    )
    _workbooks, schema = load_all(project_root / "template", project_root)
    return reconcile_tm_page35_items(
        parsed,
        schema=schema,
        policy=load_tm_page35_mapping_policy(project_root / TM_PAGE35_POLICY_RELATIVE_PATH),
        source_pdf_path=project_root / _SOURCE_PDF,
    )


def test_page35_reconciles_complete_800_828_branch_and_maps_ten_distinct_items(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert validate_tm_page35_mapping_result(result) is result
    assert result.mapping_authority_scope.endswith("PDF_PAGE_35_FIXED_ROWS_ONLY")
    assert result.mapping_authority_granted
    assert result.schema_item_count == 1_385
    assert result.status_reconciled_schema_count == 29
    assert result.mapped_schema_count == 10
    assert result.not_observed_schema_count == 19
    assert result.not_applicable_schema_count == 0
    assert result.ambiguous_schema_count == 0
    assert result.unassessed_schema_count == 1_356
    assert result.fully_verified_schema_count == 0
    assert result.source_row_count == 14
    assert result.mapped_source_row_count == 10
    assert result.source_only_row_count == 4
    assert result.source_question_row_count == 2
    assert result.ambiguous_source_row_count == 1
    assert result.financial_slot_count == 26
    assert result.extracted_value_count == 24
    assert result.dash_count == 2
    assert result.mapped_value_count == 18


def test_exact_mapped_not_observed_and_unassessed_schema_sets(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in {item.value for item in TMPage35SchemaStatus}
    }

    assert by_status[TMPage35SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] == _MAPPED_IDS
    assert by_status[TMPage35SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] == (_NOT_OBSERVED_IDS)
    assert len(by_status[TMPage35SchemaStatus.UNASSESSED.value]) == 1_356


def test_government_guaranteed_debt_and_interest_dash_remain_source_only_questions(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    questions = [item for item in result.source_dispositions if item.question_required]

    assert [item.row_id for item in questions] == [
        "page-0035:purchased_detail:row-0002",
        "page-0035:afs_securities:row-0003",
    ]
    assert questions[0].observations == ("DASH", "DASH")
    assert questions[0].values == (None, None)
    assert questions[0].candidate_report_norm_ids == ()
    assert questions[1].values == (22_128_777, 22_204_008)
    assert questions[1].candidate_report_norm_ids == (807,)
    assert questions[1].candidate_canonical_names == ("+ Do Chính phủ phát hành (NHNN, Kho bạc)",)
    assert all(item.status == TMPage35SourceStatus.SOURCE_ONLY_QUESTION.value for item in questions)


def test_dash_pixel_evidence_is_pinned_and_never_coerced_to_zero_in_validation(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    dash_row = next(
        item for item in result.source_dispositions if item.observations == ("DASH", "DASH")
    )

    assert result.dash_pixel_evidence_sha256 == (
        "166561c752403019c30d736f211e82e9415e05d723484aeda4365761b7027996"
    )
    assert [evidence.component_box for evidence in dash_row.visual_cell_evidence if evidence] == [
        (1838, 1021, 1850, 1026),
        (2193, 1018, 2206, 1023),
    ]
    not_testable = [
        check
        for check in result.accounting_checks
        if check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO"
    ]
    assert len(not_testable) == 2
    assert all(
        check.expected_value is None
        and check.residual is None
        and "cannot be coerced" in check.reason
        for check in not_testable
    )


def test_six_accounting_checks_and_four_duplicate_checks_pass_exactly(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.accounting_check_count == 8
    assert result.accounting_pass_count == 6
    assert result.accounting_not_testable_count == 2
    assert all(check.residual == 0 for check in result.accounting_checks if check.status == "PASS")
    assert result.duplicate_check_count == result.duplicate_pass_count == 4
    assert all(check.status == "PASS" and check.residual == 0 for check in result.duplicate_checks)


def test_mapping_policy_forbids_values_history_review_dash_zero_and_equation_selection(
    project_root: Path,
) -> None:
    policy = load_tm_page35_mapping_policy(project_root / TM_PAGE35_POLICY_RELATIVE_PATH)

    assert set(policy.forbidden_mapping_inputs) == {
        "numeric_cell_text",
        "numeric_cell_value_as_item_selector",
        "numeric_value_magnitude",
        "historical_or_mongodb_values",
        "human_review_answers",
        "dash_as_zero",
        "accounting_equation_result_as_item_selector",
    }
