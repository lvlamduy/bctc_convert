from __future__ import annotations

from pathlib import Path

from bctc_ai.mapping.tm_note_page42_mapping import (
    TM_PAGE42_POLICY_RELATIVE_PATH,
    TMPage42SchemaStatus,
    TMPage42SourceStatus,
    load_tm_page42_mapping_policy,
    reconcile_tm_page42_items,
    validate_tm_page42_mapping_result,
)
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.tm_note_page42 import load_tm_page42_policy, parse_tm_page42

_OCR_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0042-ppocrv6-word-box.json")
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_MAPPED_IDS = {
    967,
    970,
    971,
    973,
    981,
    987,
    989,
    997,
    1024,
    1040,
    1042,
    1043,
    1044,
    1045,
    1046,
    1047,
    1048,
    1049,
    1052,
    5975,
    5976,
    6007,
}
_AMBIGUOUS_IDS: set[int] = set()
_NOT_OBSERVED_IDS = set(range(966, 1_055)) - _MAPPED_IDS - _AMBIGUOUS_IDS


def _mapped(project_root: Path, tmp_path: Path):
    render = Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={42},
        )[0].path
    )
    parsed = parse_tm_page42(
        project_root / _OCR_FIXTURE,
        render,
        load_tm_page42_policy(project_root / "config/tables/tm-note-page42-v1.yaml"),
    )
    _workbooks, schema = load_all(project_root / "template", project_root)
    return reconcile_tm_page42_items(
        parsed,
        schema=schema,
        policy=load_tm_page42_mapping_policy(project_root / TM_PAGE42_POLICY_RELATIVE_PATH),
        source_pdf_path=project_root / _SOURCE_PDF,
    )


def test_page42_reconciles_complete_branch_and_maps_twenty_two_items(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert validate_tm_page42_mapping_result(result) is result
    assert result.mapping_authority_scope.endswith("PDF_PAGE_42_FIXED_ROWS_ONLY")
    assert result.mapping_authority_granted
    assert result.schema_item_count == 1_719
    assert result.status_reconciled_schema_count == 92
    assert result.mapped_schema_count == 22
    assert result.ambiguous_schema_count == 0
    assert result.not_observed_schema_count == 70
    assert result.not_applicable_schema_count == 0
    assert result.unassessed_schema_count == (
        result.schema_item_count - result.status_reconciled_schema_count
    )
    assert result.fully_verified_schema_count == 0
    assert result.source_row_count == 24
    assert result.mapped_source_row_count == 22
    assert result.source_only_row_count == 2
    assert result.source_question_row_count == 0
    assert result.ambiguous_source_row_count == 0
    assert result.financial_slot_count == result.extracted_value_count == 48
    assert result.dash_count == 0
    assert result.mapped_value_count == 44


def test_exact_mapped_ambiguous_not_observed_and_unassessed_schema_sets(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in {item.value for item in TMPage42SchemaStatus}
    }

    assert by_status[TMPage42SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] == _MAPPED_IDS
    assert by_status[TMPage42SchemaStatus.AMBIGUOUS_MAPPING.value] == _AMBIGUOUS_IDS
    assert by_status[TMPage42SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] == (_NOT_OBSERVED_IDS)
    assert len(by_status[TMPage42SchemaStatus.UNASSESSED.value]) == (result.unassessed_schema_count)
    assert _MAPPED_IDS | _AMBIGUOUS_IDS | _NOT_OBSERVED_IDS == (
        set(range(966, 1_055)) | {5975, 5976, 6007}
    )


def test_987_is_primary_note14_total_while_broader_966_is_not_observed(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    mapped_987 = [item for item in result.source_dispositions if item.report_norm_id == 987]
    schema_966 = next(item for item in result.schema_dispositions if item.report_norm_id == 966)

    assert [(item.row_id, item.values) for item in mapped_987] == [
        ("page-0042:other_assets:row-0003", (6_622_398, 7_894_091))
    ]
    assert schema_966.status == TMPage42SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value


def test_combined_capex_maps_new_exact_item_and_old_candidates_are_not_observed(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    capex = next(
        item
        for item in result.source_dispositions
        if item.row_id == "page-0042:receivable_detail:row-0001"
    )

    assert capex.report_norm_id == 6007
    assert capex.values == (1_295_059, 1_039_654)
    assert capex.status == TMPage42SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
    assert not capex.question_required
    assert not capex.candidate_report_norm_ids
    by_id = {item.report_norm_id: item for item in result.schema_dispositions}
    assert by_id[6007].source_row_ids == (capex.row_id,)
    assert by_id[968].status == TMPage42SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
    assert by_id[969].status == TMPage42SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value


def test_two_specialized_receivables_map_to_new_exact_schema_items(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    additions = [item for item in result.source_dispositions if item.report_norm_id in {5975, 5976}]

    assert [
        (item.report_norm_id, item.row_id, item.values, item.period_ends) for item in additions
    ] == [
        (
            5975,
            "page-0042:receivable_detail:row-0003",
            (861_287, 1_525_624),
            ("2026-03-31", "2025-12-31"),
        ),
        (
            5976,
            "page-0042:receivable_detail:row-0004",
            (11_281_653, 8_046_079),
            ("2026-03-31", "2025-12-31"),
        ),
    ]
    assert all(
        item.status == TMPage42SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
        and not item.question_required
        and not item.candidate_report_norm_ids
        for item in additions
    )
    mapped_981 = [item for item in result.source_dispositions if item.report_norm_id == 981]
    assert [item.row_id for item in mapped_981] == ["page-0042:receivable_detail:row-0005"]


def test_only_two_exact_totals_are_source_only_validation_duplicates(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    validation_rows = [
        item
        for item in result.source_dispositions
        if item.status == TMPage42SourceStatus.SOURCE_ONLY_VALIDATION.value
    ]

    assert [(item.row_id, item.values) for item in validation_rows] == [
        ("page-0042:receivable_detail:row-0006", (19_581_449, 27_766_232)),
        ("page-0042:government_debt:row-0002", (28_346_499, 47_474_800)),
    ]


def test_fourteen_accounting_plus_four_duplicate_checks_pass_exactly(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.accounting_check_count == result.accounting_pass_count == 14
    assert result.duplicate_check_count == result.duplicate_pass_count == 4
    assert result.validation_check_count == result.validation_pass_count == 18
    assert all(check.status == "PASS" and check.residual == 0 for check in result.accounting_checks)
    assert all(check.status == "PASS" and check.residual == 0 for check in result.duplicate_checks)


def test_mapping_policy_forbids_values_history_review_and_equation_selection(
    project_root: Path,
) -> None:
    policy = load_tm_page42_mapping_policy(project_root / TM_PAGE42_POLICY_RELATIVE_PATH)

    assert set(policy.forbidden_mapping_inputs) == {
        "numeric_cell_text",
        "numeric_cell_value_as_item_selector",
        "numeric_value_magnitude",
        "historical_or_mongodb_values",
        "human_review_answers",
        "accounting_equation_result_as_item_selector",
    }
