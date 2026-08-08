from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from bctc_ai.mapping.tm_note_page44_mapping import (
    TM_PAGE44_POLICY_RELATIVE_PATH,
    TMPage44SchemaStatus,
    TMPage44SourceStatus,
    load_tm_page44_mapping_policy,
    reconcile_tm_page44_items,
    validate_tm_page44_mapping_result,
)
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.tm_note_page44 import load_tm_page44_policy, parse_tm_page44

_OCR_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0044-ppocrv6-word-box.json")
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_MAPPED_IDS = {1100, 1101, 1109, 1112, 1118, 1119, 1122, 1128, 1129, 1131, 1141}
_AMBIGUOUS_IDS = {1102, 1103, 1104, 1110, 1111}
_UNRESOLVED_IDS = {1130, *range(1132, 1141)}
_NOT_OBSERVED_IDS = {
    1105,
    1106,
    1107,
    1108,
    1113,
    1114,
    1115,
    1116,
    1117,
    1120,
    1121,
    1123,
    1124,
    1125,
    1126,
    1127,
}


def _mapped(project_root: Path, tmp_path: Path):
    render = Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={44},
        )[0].path
    )
    parsed = parse_tm_page44(
        project_root / _OCR_FIXTURE,
        render,
        load_tm_page44_policy(project_root / "config/tables/tm-note-page44-v1.yaml"),
    )
    _workbooks, schema = load_all(project_root / "template", project_root)
    return reconcile_tm_page44_items(
        parsed,
        schema=schema,
        policy=load_tm_page44_mapping_policy(project_root / TM_PAGE44_POLICY_RELATIVE_PATH),
        source_pdf_path=project_root / _SOURCE_PDF,
    )


def test_page44_reconciles_complete_1100_1141_branch_with_exact_statuses(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert validate_tm_page44_mapping_result(result) is result
    assert result.mapping_authority_scope.endswith("FIXED_ROWS_AND_CELLS_ONLY")
    assert result.mapping_authority_granted
    assert result.schema_item_count == 1_417
    assert result.status_reconciled_schema_count == 42
    assert result.mapped_schema_count == 11
    assert result.ambiguous_schema_count == 5
    assert result.unresolved_schema_count == 10
    assert result.not_observed_schema_count == 16
    assert result.not_applicable_schema_count == 0
    assert result.unassessed_schema_count == 1_375
    assert result.fully_verified_schema_count == 0
    assert result.source_row_count == 24
    assert result.mapped_source_row_count == 10
    assert result.partial_source_row_count == 2
    assert result.source_only_row_count == 14
    assert result.source_question_row_count == 13
    assert result.context_source_row_count == 3
    assert result.financial_slot_count == 60
    assert result.extracted_value_count == 51
    assert result.dash_count == 9
    assert result.mapped_value_count == 17
    assert result.narrative_fact_count == 5
    assert result.narrative_value_count == 7


def test_exact_mapped_ambiguous_unresolved_not_observed_and_unassessed_sets(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in {item.value for item in TMPage44SchemaStatus}
    }

    assert by_status[TMPage44SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] == _MAPPED_IDS
    assert by_status[TMPage44SchemaStatus.AMBIGUOUS_MAPPING.value] == _AMBIGUOUS_IDS
    assert by_status[TMPage44SchemaStatus.UNRESOLVED.value] == _UNRESOLVED_IDS
    assert by_status[TMPage44SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] == (_NOT_OBSERVED_IDS)
    assert len(by_status[TMPage44SchemaStatus.UNASSESSED.value]) == 1_375
    assert _MAPPED_IDS | _AMBIGUOUS_IDS | _UNRESOLVED_IDS | _NOT_OBSERVED_IDS == set(
        range(1100, 1142)
    )


def test_q050_maturity_rows_remain_source_only_with_exact_candidates(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    q050 = [item for item in result.source_dispositions if item.question_group_id == "Q050"]

    assert [item.row_id for item in q050] == [
        "page-0044:paper_issuance:row-0003",
        "page-0044:paper_issuance:row-0006",
        "page-0044:paper_issuance:row-0007",
    ]
    assert [item.candidate_report_norm_ids for item in q050] == [
        (1110, 1111),
        (1102, 1103),
        (1103, 1104),
    ]
    assert all(item.status == TMPage44SourceStatus.SOURCE_ONLY_QUESTION.value for item in q050)


def test_equity_grid_only_maps_three_exact_cells_plus_structural_root(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    equity = [item for item in result.source_dispositions if item.table_key == "EQUITY_MOVEMENT"]
    partial = [
        item for item in equity if item.status == TMPage44SourceStatus.PARTIAL_CELL_MAPPING.value
    ]
    structural = equity[0]

    assert [
        (
            item.row_id,
            [
                (x.cell_index, x.axis_role, x.report_norm_id, x.value)
                for x in item.mapped_assignments
            ],
        )
        for item in partial
    ] == [
        (
            "page-0044:equity_movement:row-0010",
            [(1, "INCREASE", 1131, 7_515_513)],
        ),
        (
            "page-0044:equity_movement:row-0012",
            [
                (0, "BEGINNING_BALANCE", 1129, 142_022_525),
                (3, "ENDING_BALANCE", 1141, 149_745_325),
            ],
        ),
    ]
    assert [(x.cell_index, x.report_norm_id) for x in structural.mapped_assignments] == [
        (None, 1128)
    ]
    assert all(item.question_group_id == "Q051" for item in equity[2:])


def test_fourteen_checks_pass_and_eight_dash_equations_are_not_testable(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.accounting_check_count == 22
    assert result.accounting_pass_count == 14
    assert result.accounting_not_testable_count == 8
    assert result.accounting_fail_count == 0
    not_testable = [
        check
        for check in result.accounting_checks
        if check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO"
    ]
    assert len(not_testable) == 8
    assert all(check.expected_value is None and check.residual is None for check in not_testable)
    assert all(check.residual == 0 for check in result.accounting_checks if check.status == "PASS")
    assert result.dash_pixel_evidence_sha256 == (
        "f818530118fe2aead1739b005a273b73f4efecf9d2828282e1a3b4e6c8433c9b"
    )


def test_q052_share_times_par_diagnostic_passes_rounding_without_schema_mapping(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    diagnostic = result.narrative_diagnostic

    assert result.question_group_ids == ("Q050", "Q051", "Q052")
    assert diagnostic.question_group_id == "Q052"
    assert diagnostic.share_count == 8_054_999_909
    assert diagnostic.par_value_vnd == 10_000
    assert diagnostic.implied_capital_vnd_million == Decimal("80549999.09")
    assert diagnostic.stated_capital_vnd_million == 80_549_999
    assert diagnostic.exact_residual_vnd_million == Decimal("-0.09")
    assert diagnostic.rounded_implied_capital_vnd_million == 80_549_999
    assert diagnostic.status == "PASS_ROUNDED_TO_NEAREST_MILLION"


def test_mapping_policy_forbids_values_history_review_dash_zero_and_equation_selection(
    project_root: Path,
) -> None:
    policy = load_tm_page44_mapping_policy(project_root / TM_PAGE44_POLICY_RELATIVE_PATH)

    assert set(policy.forbidden_mapping_inputs) == {
        "numeric_cell_text",
        "numeric_cell_value_as_item_selector",
        "numeric_value_magnitude",
        "historical_or_mongodb_values",
        "human_review_answers",
        "dash_as_zero",
        "accounting_equation_result_as_item_selector",
    }
