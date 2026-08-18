from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from bctc_ai.mapping.tm_note_pages32_33_mapping import (
    TM_NOTE_PAGES3233_POLICY_RELATIVE_PATH,
    TMNotePages3233CellStatus,
    TMNotePages3233MappingError,
    TMNotePages3233SchemaStatus,
    TMNotePages3233SourceStatus,
    load_tm_note_pages32_33_mapping_policy,
    reconcile_tm_note_pages32_33_items,
    validate_tm_note_pages32_33_mapping_result,
)
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.tm_note_pages32_33 import (
    load_tm_note_pages32_33_policy,
    parse_tm_note_pages32_33,
)

_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_TABLE_POLICY = Path("config/tables/tm-note-pages32-33-v1.yaml")
_FIXTURES = {
    32: Path("tests/golden/tm/mbb-q1-2026-page-0032-ppocrv6-word-box.json"),
    33: Path("tests/golden/tm/mbb-q1-2026-page-0033-ppocrv6-word-box.json"),
}
_MAPPED_IDS = {
    727,
    728,
    729,
    730,
    731,
    732,
    733,
    734,
    735,
    736,
    737,
    738,
    740,
    741,
    742,
    743,
    766,
    767,
    769,
    770,
    771,
    772,
    773,
    776,
    778,
    779,
    780,
    781,
    782,
    5719,
    5720,
    5721,
    5722,
    5748,
    5749,
    6058,
}
_AMBIGUOUS_IDS: set[int] = set()
_NOT_OBSERVED_IDS = {
    739,
    744,
    745,
    756,
    757,
    758,
    768,
    774,
    775,
    777,
    6059,
    6060,
}


def _mapped(project_root: Path, tmp_path: Path):
    renders = {
        item.page: Path(item.path)
        for item in render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={32, 33},
        )
    }
    parsed = parse_tm_note_pages32_33(
        {page: (project_root / fixture, renders[page]) for page, fixture in _FIXTURES.items()},
        load_tm_note_pages32_33_policy(project_root / _TABLE_POLICY),
    )
    _workbooks, schema = load_all(project_root / "template", project_root)
    return reconcile_tm_note_pages32_33_items(
        parsed,
        schema=schema,
        policy=load_tm_note_pages32_33_mapping_policy(
            project_root / TM_NOTE_PAGES3233_POLICY_RELATIVE_PATH
        ),
        source_pdf_path=project_root / _SOURCE_PDF,
    )


def test_exact_48_item_schema_reconciliation(project_root: Path, tmp_path: Path) -> None:
    result = _mapped(project_root, tmp_path)

    assert validate_tm_note_pages32_33_mapping_result(result) is result
    assert result.schema_item_count == 1_721
    assert result.status_reconciled_schema_count == 48
    assert result.mapped_schema_count == 36
    assert result.ambiguous_schema_count == 0
    assert result.not_observed_schema_count == 12
    assert result.not_applicable_schema_count == 0
    assert result.unassessed_schema_count == (
        result.schema_item_count - result.status_reconciled_schema_count
    )
    assert result.fully_verified_schema_count == 0
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in (item.value for item in TMNotePages3233SchemaStatus)
    }
    assert by_status[TMNotePages3233SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] == _MAPPED_IDS
    assert by_status[TMNotePages3233SchemaStatus.AMBIGUOUS_MAPPING.value] == _AMBIGUOUS_IDS
    assert (
        by_status[TMNotePages3233SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] == _NOT_OBSERVED_IDS
    )
    assert set(range(759, 766)) <= by_status[TMNotePages3233SchemaStatus.UNASSESSED.value]


def test_source_and_slot_statuses_reconcile_without_percentage_mapping(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.source_row_count == 46
    assert result.mapped_source_row_count == 37
    assert result.ambiguous_source_row_count == 0
    assert result.source_only_row_count == 9
    assert result.partially_mapped_source_row_count == 35
    assert result.financial_slot_count == 176
    assert result.extracted_value_count == 174
    assert result.zero_count == 2
    assert result.mapped_source_slot_count == 70
    assert result.ambiguous_source_slot_count == 0
    assert result.source_only_slot_count == 106
    assert result.mapped_assignment_count == 68
    assert all(
        cell.measure_role == "AMOUNT" and cell.cell_index in {0, 2}
        for cell in result.cell_dispositions
        if cell.status == TMNotePages3233CellStatus.MAPPED_AMOUNT.value
    )
    assert all(
        cell.report_norm_id is None
        for cell in result.cell_dispositions
        if cell.measure_role == "PERCENTAGE"
    )
    assert (
        sum(
            cell.status == TMNotePages3233CellStatus.SOURCE_ONLY_PERCENTAGE.value
            for cell in result.cell_dispositions
        )
        == 70
    )


def test_fixed_assignments_have_exact_values_periods_units_scope_and_no_duplicates(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    values = {
        (item.page_tag, item.report_norm_id, item.period_role): item.value
        for item in result.mapped_assignments
    }

    assert values[("page-0032", 767, "CURRENT")] == Decimal("43570696")
    assert values[("page-0032", 770, "CURRENT")] == Decimal("4853278")
    assert values[("page-0032", 770, "COMPARATIVE")] == Decimal("4337893")
    assert values[("page-0032", 778, "COMPARATIVE")] == Decimal("319")
    assert values[("page-0032", 780, "CURRENT")] == Decimal("459681597")
    assert values[("page-0033", 728, "CURRENT")] == Decimal("11849690")
    assert values[("page-0033", 735, "COMPARATIVE")] == Decimal("121188714")
    assert values[("page-0033", 743, "CURRENT")] == Decimal("4252091")
    assert values[("page-0032", 782, "CURRENT")] == Decimal("9402280")
    assert values[("page-0032", 782, "COMPARATIVE")] == Decimal("9938997")
    assert values[("page-0033", 737, "CURRENT")] == Decimal("2689938")
    assert values[("page-0033", 5719, "CURRENT")] == Decimal("8122254")
    assert values[("page-0033", 5720, "CURRENT")] == Decimal("1531664")
    assert values[("page-0033", 5721, "CURRENT")] == Decimal("818537")
    assert values[("page-0033", 5722, "CURRENT")] == Decimal("264294420")
    assert values[("page-0032", 5748, "CURRENT")] == Decimal("15520372")
    assert values[("page-0032", 5748, "COMPARATIVE")] == Decimal("15040585")
    assert values[("page-0033", 5749, "CURRENT")] == Decimal("15520372")
    assert values[("page-0033", 5749, "COMPARATIVE")] == Decimal("15040585")
    assert len(values) == 68
    assert all(
        item.measure_role == "AMOUNT"
        and item.cell_index in {0, 2}
        and item.unit == "VND"
        and item.unit_multiplier == 1_000_000
        and item.scope == "CONSOLIDATED"
        and item.period_type == "SNAPSHOT"
        for item in result.mapped_assignments
    )
    assert {(item.period_role, item.period_end) for item in result.mapped_assignments} == {
        ("CURRENT", "2026-03-31"),
        ("COMPARATIVE", "2025-12-31"),
    }


def test_resolved_user_mappings_and_catch_all_are_export_safe(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    by_identity = {(item.page_tag, item.row_key): item for item in result.source_dispositions}

    tnhh = by_identity[("page-0032", "STATE_OWNED_OVER_50")]
    assert tnhh.status == TMNotePages3233SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
    assert tnhh.mapped_report_norm_ids == (770,)
    assert tnhh.candidate_report_norm_ids == ()
    assert tnhh.question_key is None
    assert by_identity[("page-0033", "EDUCATION")].mapped_report_norm_ids == (737,)
    assert by_identity[("page-0033", "HEALTH_SOCIAL")].mapped_report_norm_ids == (5719,)
    assert by_identity[("page-0033", "ARTS_RECREATION")].mapped_report_norm_ids == (5720,)
    assert by_identity[("page-0033", "OTHER_SERVICES")].mapped_report_norm_ids == (5721,)
    assert by_identity[("page-0033", "HOUSEHOLD_EMPLOYMENT")].mapped_report_norm_ids == (5722,)
    assert by_identity[("page-0032", "OTHER_ECONOMIC")].mapped_report_norm_ids == (782,)
    assert by_identity[("page-0032", "FOREIGN_BRANCH_TOTAL")].mapped_report_norm_ids == (782,)
    assert by_identity[("page-0032", "TCKT_TOTAL")].status == (
        TMNotePages3233SourceStatus.SOURCE_ONLY_SUBTOTAL.value
    )
    assert by_identity[("page-0033", "FOREIGN_BRANCH")].status == (
        TMNotePages3233SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
    )
    assert by_identity[("page-0033", "FOREIGN_BRANCH")].mapped_report_norm_ids == (6058,)
    assert by_identity[("page-0032", "MARGIN_MBS")].mapped_report_norm_ids == (5748,)
    assert by_identity[("page-0033", "MARGIN_MBS")].mapped_report_norm_ids == (5749,)
    forbidden_rows = {
        item.row_id
        for item in result.source_dispositions
        if item.status != TMNotePages3233SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
    }
    assert not any(item.row_id in forbidden_rows for item in result.mapped_assignments)
    catch_all = [item for item in result.mapped_assignments if item.report_norm_id == 782]
    assert len(catch_all) == 2
    assert all(
        item.row_key == "OTHER_ECONOMIC+FOREIGN_BRANCH_TOTAL"
        and item.mapping_basis.startswith("USER_CONFIRMED_ID_782_CATCH_ALL_SUM")
        and len(item.source_row_ids) >= 2
        for item in catch_all
    )


def test_percentage_hierarchy_and_cross_page_duplicate_checks_all_pass(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.percentage_check_count == result.percentage_pass_count == 88
    assert result.hierarchy_check_count == result.hierarchy_pass_count == 36
    assert result.catch_all_check_count == result.catch_all_pass_count == 2
    assert result.duplicate_check_count == result.duplicate_pass_count == 16
    assert all(
        check.status == "PASS" and check.absolute_delta <= Decimal("0.01")
        for check in result.percentage_checks
    )
    assert all(check.status == "PASS" and check.residual == 0 for check in result.hierarchy_checks)
    assert all(check.status == "PASS" and check.residual == 0 for check in result.duplicate_checks)


def test_all_question_groups_and_forbidden_inputs_are_pinned(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.question_source_row_count == 0
    assert result.question_group_count == 0
    assert result.questions == ()

    policy_path = project_root / TM_NOTE_PAGES3233_POLICY_RELATIVE_PATH
    text = policy_path.read_text(encoding="utf-8")
    assert "percentage_axis_as_report_norm_mapping" in text
    tampered = tmp_path / "mapping-tampered.yaml"
    tampered.write_text(
        text.replace("fixed_mapped_ids: [727", "fixed_mapped_ids: [746", 1),
        encoding="utf-8",
    )
    with pytest.raises(TMNotePages3233MappingError, match="schema reconciliation sets"):
        load_tm_note_pages32_33_mapping_policy(tampered)
