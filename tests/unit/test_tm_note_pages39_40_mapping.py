from __future__ import annotations

from pathlib import Path

import pytest

from bctc_ai.mapping.tm_note_pages39_40_mapping import (
    TM_NOTE_PAGES3940_POLICY_RELATIVE_PATH,
    TMNotePages3940CellStatus,
    TMNotePages3940MappingError,
    TMNotePages3940SchemaStatus,
    TMNotePages3940SourceStatus,
    load_tm_note_pages39_40_mapping_policy,
    reconcile_tm_note_pages39_40_items,
    validate_tm_note_pages39_40_mapping_result,
)
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.tm_note_pages39_40 import (
    load_tm_note_pages39_40_policy,
    parse_tm_note_pages39_40,
)

_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_TABLE_POLICY = Path("config/tables/tm-note-pages39-40-v1.yaml")
_FIXTURES = {
    39: Path("tests/golden/tm/mbb-q1-2026-page-0039-ppocrv6-word-box.json"),
    40: Path("tests/golden/tm/mbb-q1-2026-page-0040-ppocrv6-word-box.json"),
}
_MAPPED_IDS = {913, 914, 915, 925, 928, 929, 930, 941}
_UNRESOLVED_IDS = {
    916,
    917,
    918,
    919,
    920,
    927,
    931,
    932,
    933,
    934,
    935,
    936,
    937,
    938,
    939,
    940,
}
_NOT_OBSERVED_IDS = {921, 922, 923, 924, 926}


def _mapped(project_root: Path, tmp_path: Path):
    renders = {
        item.page: Path(item.path)
        for item in render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={39, 40},
        )
    }
    parsed = parse_tm_note_pages39_40(
        {page: (project_root / fixture, renders[page]) for page, fixture in _FIXTURES.items()},
        load_tm_note_pages39_40_policy(project_root / _TABLE_POLICY),
    )
    _workbooks, schema = load_all(project_root / "template", project_root)
    return reconcile_tm_note_pages39_40_items(
        parsed,
        schema=schema,
        policy=load_tm_note_pages39_40_mapping_policy(
            project_root / TM_NOTE_PAGES3940_POLICY_RELATIVE_PATH
        ),
        source_pdf_path=project_root / _SOURCE_PDF,
    )


def test_exact_29_item_schema_reconciliation(project_root: Path, tmp_path: Path) -> None:
    result = _mapped(project_root, tmp_path)

    assert validate_tm_note_pages39_40_mapping_result(result) is result
    assert result.schema_item_count == 1_613
    assert result.status_reconciled_schema_count == 29
    assert result.mapped_schema_count == 8
    assert result.unresolved_schema_count == 16
    assert result.not_observed_schema_count == 5
    assert result.not_applicable_schema_count == 0
    assert result.unassessed_schema_count == 1_584
    assert result.fully_verified_schema_count == 0
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in (item.value for item in TMNotePages3940SchemaStatus)
    }
    assert by_status[TMNotePages3940SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] == _MAPPED_IDS
    assert by_status[TMNotePages3940SchemaStatus.UNRESOLVED.value] == _UNRESOLVED_IDS
    assert (
        by_status[TMNotePages3940SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] == _NOT_OBSERVED_IDS
    )


def test_source_and_slot_statuses_reconcile_without_class_axis_overmapping(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.source_row_count == 30
    assert result.mapped_source_row_count == 13
    assert result.unresolved_source_row_count == 7
    assert result.source_only_row_count == 10
    assert result.partially_mapped_source_row_count == 9
    assert result.question_source_row_count == 17
    assert result.financial_slot_count == 96
    assert result.extracted_value_count == 79
    assert result.dash_count == 17
    assert result.mapped_source_slot_count == 9
    assert result.unresolved_source_slot_count == 28
    assert result.source_only_slot_count == 59
    assert (
        result.mapped_source_slot_count
        + result.unresolved_source_slot_count
        + result.source_only_slot_count
        == result.financial_slot_count
    )
    mapped_cells = [
        cell
        for cell in result.cell_dispositions
        if cell.status == TMNotePages3940CellStatus.MAPPED_AUTOMATIC_SCOPED.value
    ]
    assert len(mapped_cells) == 9
    assert all(cell.cell_index == 3 and cell.axis_role == "TOTAL" for cell in mapped_cells)
    assert (
        sum(
            cell.status == TMNotePages3940CellStatus.SOURCE_ONLY_CLASS_AXIS.value
            for cell in result.cell_dispositions
        )
        == 27
    )


def test_fixed_total_assignments_have_exact_values_periods_units_and_scope(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    values = {
        (item.page_tag, item.report_norm_id): item.value for item in result.mapped_assignments
    }

    assert values == {
        ("page-0039", 915): 5_684_904,
        ("page-0039", 928): 5_762_160,
        ("page-0039", 930): 3_873_890,
        ("page-0039", 941): 3_978_526,
        ("page-0040", 915): 4_976_669,
        ("page-0040", 925): -105_478,
        ("page-0040", 928): 5_684_904,
        ("page-0040", 930): 3_296_949,
        ("page-0040", 941): 3_873_890,
    }
    assert all(
        item.cell_index == 3 and item.axis_role == "TOTAL" for item in result.mapped_assignments
    )
    assert all(
        item.unit == "VND" and item.unit_multiplier == 1_000_000
        for item in result.mapped_assignments
    )
    assert all(item.scope == "CONSOLIDATED" for item in result.mapped_assignments)
    assert {
        (item.page_tag, item.period_role, item.period_start, item.period_end, item.period_type)
        for item in result.mapped_assignments
    } == {
        ("page-0039", "CURRENT", "2026-01-01", "2026-03-31", "DURATION"),
        ("page-0040", "COMPARATIVE", "2025-01-01", "2025-12-31", "DURATION"),
    }


def test_aggregate_fx_and_net_rows_remain_visible_without_forced_mapping(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    by_identity = {(item.page_tag, item.row_key): item for item in result.source_dispositions}

    assert by_identity[("page-0039", "GROSS_INCREASE")].status == (
        TMNotePages3940SourceStatus.UNRESOLVED.value
    )
    assert by_identity[("page-0039", "GROSS_INCREASE")].candidate_report_norm_ids == (
        916,
        917,
        918,
        919,
        920,
    )
    assert by_identity[("page-0040", "ACCUM_DECREASE")].candidate_report_norm_ids == (
        934,
        935,
        936,
        937,
        938,
        939,
        940,
    )
    assert by_identity[("page-0039", "GROSS_FX")].status == (
        TMNotePages3940SourceStatus.SOURCE_ONLY_SCHEMA_GAP.value
    )
    assert by_identity[("page-0040", "NET_CLOSE")].status == (
        TMNotePages3940SourceStatus.SOURCE_ONLY_VALIDATION.value
    )
    assert not any(
        assignment.row_key.startswith("NET_") or assignment.row_key.endswith("_FX")
        for assignment in result.mapped_assignments
    )


def test_accounting_abstains_on_dash_and_cross_panel_checks_all_pass(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.accounting_check_count == 56
    assert result.accounting_pass_count == 39
    assert result.accounting_not_testable_count == 17
    assert result.duplicate_check_count == result.duplicate_pass_count == 12
    assert all(check.status != "FAIL" for check in result.accounting_checks)
    assert all(check.status == "PASS" and check.residual == 0 for check in result.duplicate_checks)
    abstentions = [
        check
        for check in result.accounting_checks
        if check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO"
    ]
    assert len(abstentions) == 17
    assert all(
        check.expected is None and check.observed is None and check.residual is None
        for check in abstentions
    )


def test_five_question_groups_and_forbidden_inputs_are_pinned(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    assert {question.question_key for question in result.questions} == {
        "P39_AGGREGATE_INCREASES",
        "P40_GROSS_AGGREGATES",
        "P40_ACCUM_AGGREGATES",
        "FX_SCHEMA_GAP",
        "NET_SCHEMA_GAP",
    }
    fx = next(question for question in result.questions if question.question_key == "FX_SCHEMA_GAP")
    assert fx.candidate_report_norm_ids == ()
    assert fx.visible_values == (
        "page-0039:GROSS_FX:[DASH,159,DASH,159]",
        "page-0039:ACCUM_FX:[DASH,44,DASH,44]",
        "page-0040:GROSS_FX:[DASH,1263,DASH,1263]",
        "page-0040:ACCUM_FX:[DASH,391,DASH,391]",
    )

    policy_path = project_root / TM_NOTE_PAGES3940_POLICY_RELATIVE_PATH
    text = policy_path.read_text(encoding="utf-8")
    assert "human_review_answers" in text
    tampered = tmp_path / "mapping-tampered.yaml"
    tampered.write_text(
        text.replace("mapped_cell_index: 3", "mapped_cell_index: 2", 1), encoding="utf-8"
    )
    with pytest.raises(TMNotePages3940MappingError, match="rule identity"):
        load_tm_note_pages39_40_mapping_policy(tampered)
