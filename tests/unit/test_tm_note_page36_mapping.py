from __future__ import annotations

from pathlib import Path

from bctc_ai.mapping.tm_note_page36_mapping import (
    TM_PAGE36_POLICY_RELATIVE_PATH,
    TMPage36SchemaStatus,
    TMPage36SourceStatus,
    load_tm_page36_mapping_policy,
    reconcile_tm_page36_items,
    validate_tm_page36_mapping_result,
)
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.tm_note_page36 import load_tm_page36_policy, parse_tm_page36

_OCR_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0036-ppocrv6-word-box.json")
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_MAPPED_IDS = {829, 831, 832, 833, 848, 849, 862, 867, 5959, 5960, 5961}
_NOT_OBSERVED_IDS = {
    830,
    *range(834, 848),
    *range(850, 862),
    *range(863, 867),
    6066,
    6067,
}


def _mapped(project_root: Path, tmp_path: Path):
    render = Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={36},
        )[0].path
    )
    parsed = parse_tm_page36(
        project_root / _OCR_FIXTURE,
        render,
        load_tm_page36_policy(project_root / "config/tables/tm-note-page36-v1.yaml"),
    )
    _workbooks, schema = load_all(project_root / "template", project_root)
    return reconcile_tm_page36_items(
        parsed,
        schema=schema,
        policy=load_tm_page36_mapping_policy(project_root / TM_PAGE36_POLICY_RELATIVE_PATH),
        source_pdf_path=project_root / _SOURCE_PDF,
    )


def test_page36_reconciles_complete_branch_and_maps_eleven_distinct_items(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert validate_tm_page36_mapping_result(result) is result
    assert result.mapping_authority_scope.endswith("PDF_PAGE_36_FIXED_ROWS_ONLY")
    assert result.mapping_authority_granted
    assert result.schema_item_count == 1_713
    assert result.status_reconciled_schema_count == 44
    assert result.mapped_schema_count == 11
    assert result.not_observed_schema_count == 33
    assert result.not_applicable_schema_count == 0
    assert result.ambiguous_schema_count == 0
    assert result.unassessed_schema_count == 1_669
    assert result.fully_verified_schema_count == 0
    assert result.source_row_count == 14
    assert result.mapped_source_row_count == 11
    assert result.source_only_row_count == 3
    assert result.source_question_row_count == 0
    assert result.ambiguous_source_row_count == 0
    assert result.financial_slot_count == 26
    assert result.extracted_value_count == 26
    assert result.dash_count == 0
    assert result.mapped_value_count == 22


def test_exact_mapped_not_observed_and_unassessed_schema_sets(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in {item.value for item in TMPage36SchemaStatus}
    }

    assert by_status[TMPage36SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] == _MAPPED_IDS
    assert by_status[TMPage36SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] == (_NOT_OBSERVED_IDS)
    assert len(by_status[TMPage36SchemaStatus.UNASSESSED.value]) == 1_669
    assert _MAPPED_IDS | _NOT_OBSERVED_IDS == set(range(829, 868)) | {
        5959,
        5960,
        5961,
        6066,
        6067,
    }


def test_only_numeric_net_maps_829_and_duplicate_867_rows_are_not_exported(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    mapped_829 = [item for item in result.source_dispositions if item.report_norm_id == 829]
    mapped_867 = [item for item in result.source_dispositions if item.report_norm_id == 867]

    assert [(item.row_id, item.values) for item in mapped_829] == [
        ("page-0036:htm_securities:row-0007", (4_273_769, 4_225_737))
    ]
    assert [(item.row_id, item.values) for item in mapped_867] == [
        ("page-0036:long_term_net:row-0001", (559_134, 559_624))
    ]
    validation_rows = [
        item
        for item in result.source_dispositions
        if item.status == TMPage36SourceStatus.SOURCE_ONLY_VALIDATION.value
    ]
    assert [item.row_id for item in validation_rows] == [
        "page-0036:htm_securities:row-0001",
        "page-0036:long_term_net:row-0002",
        "page-0036:long_term_detail:row-0003",
    ]


def test_provision_and_two_long_term_details_map_with_exact_period_values(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    additions = [
        item for item in result.source_dispositions if item.report_norm_id in {5959, 5960, 5961}
    ]

    assert [
        (item.report_norm_id, item.row_id, item.values, item.period_ends) for item in additions
    ] == [
        (
            5959,
            "page-0036:long_term_net:row-0003",
            (-91_228, -91_228),
            ("2026-03-31", "2025-12-31"),
        ),
        (
            5960,
            "page-0036:long_term_detail:row-0001",
            (492_584, 493_184),
            ("2026-03-31", "2025-12-31"),
        ),
        (
            5961,
            "page-0036:long_term_detail:row-0002",
            (66_550, 66_440),
            ("2026-03-31", "2025-12-31"),
        ),
    ]
    assert all(
        item.status == TMPage36SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
        and not item.question_required
        and not item.candidate_report_norm_ids
        for item in additions
    )


def test_eight_accounting_and_four_duplicate_checks_pass_exactly(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.accounting_check_count == result.accounting_pass_count == 8
    assert all(check.status == "PASS" and check.residual == 0 for check in result.accounting_checks)
    assert result.duplicate_check_count == result.duplicate_pass_count == 4
    assert all(check.status == "PASS" and check.residual == 0 for check in result.duplicate_checks)


def test_mapping_policy_forbids_values_history_review_and_equation_selection(
    project_root: Path,
) -> None:
    policy = load_tm_page36_mapping_policy(project_root / TM_PAGE36_POLICY_RELATIVE_PATH)

    assert set(policy.forbidden_mapping_inputs) == {
        "numeric_cell_text",
        "numeric_cell_value_as_item_selector",
        "numeric_value_magnitude",
        "historical_or_mongodb_values",
        "human_review_answers",
        "accounting_equation_result_as_item_selector",
    }
