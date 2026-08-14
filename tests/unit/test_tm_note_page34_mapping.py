from __future__ import annotations

from pathlib import Path

import pytest

from bctc_ai.mapping.tm_note_page34_mapping import (
    TM_PAGE34_MAPPING_POLICY_RELATIVE_PATH,
    TMPage34CellStatus,
    TMPage34MappingError,
    TMPage34SchemaStatus,
    TMPage34SourceStatus,
    load_tm_page34_mapping_policy,
    reconcile_tm_page34_items,
    validate_tm_page34_mapping_result,
)
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.tm_note_page34 import load_tm_page34_policy, parse_tm_page34

_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0034-ppocrv6-word-box.json")
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_MAPPED_IDS = {
    783,
    784,
    785,
    786,
    787,
    788,
    790,
    791,
    792,
    793,
    794,
    795,
    796,
    798,
    799,
}


def _mapped(project_root: Path, tmp_path: Path):
    render = Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={34},
        )[0].path
    )
    parsed = parse_tm_page34(
        project_root / _FIXTURE,
        render,
        load_tm_page34_policy(project_root / "config/tables/tm-note-page34-v1.yaml"),
    )
    _workbooks, schema = load_all(project_root / "template", project_root)
    return reconcile_tm_page34_items(
        parsed,
        schema=schema,
        policy=load_tm_page34_mapping_policy(project_root / TM_PAGE34_MAPPING_POLICY_RELATIVE_PATH),
        source_pdf_path=project_root / _SOURCE_PDF,
    )


def test_page34_reconciles_complete_783_799_scope_and_exact_source_denominators(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert validate_tm_page34_mapping_result(result) is result
    assert result.mapping_authority_scope.endswith("OVERALL_SPECIFIC_GENERAL_AXES_ONLY")
    assert result.mapping_authority_granted
    assert result.schema_item_count == 1_710
    assert result.status_reconciled_schema_count == 17
    assert result.mapped_schema_count == 15
    assert result.ambiguous_schema_count == 0
    assert result.not_observed_schema_count == 2
    assert result.unassessed_schema_count == 1_693
    assert result.fully_verified_schema_count == 0
    assert result.source_row_count == 11
    assert result.mapped_source_row_count == 11
    assert result.ambiguous_source_row_count == 0
    assert result.source_only_row_count == 0
    assert result.source_question_row_count == 0
    assert result.partially_mapped_source_row_count == 11
    assert result.financial_slot_count == 99
    assert result.extracted_value_count == 80
    assert result.dash_count == 19
    assert result.mapped_status_assignment_count == 22
    assert result.mapped_value_assignment_count == 20
    assert result.mapped_dash_assignment_count == 2
    assert result.ambiguous_source_slot_count == 0
    assert result.source_only_slot_count == 77


def test_exact_mapped_ambiguous_not_observed_and_unassessed_schema_sets(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in (item.value for item in TMPage34SchemaStatus)
    }

    assert by_status[TMPage34SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] == _MAPPED_IDS
    assert by_status[TMPage34SchemaStatus.AMBIGUOUS_MAPPING.value] == set()
    assert by_status[TMPage34SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] == {789, 797}
    assert len(by_status[TMPage34SchemaStatus.UNASSESSED.value]) == 1_693
    assert _MAPPED_IDS | {789, 797} == set(range(783, 800))
    assert all(
        item.source_evidence_ids
        for item in result.schema_dispositions
        if item.report_norm_id in _MAPPED_IDS
    )


def test_structural_title_headers_and_only_overall_specific_general_cells_map(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert [item.report_norm_id for item in result.structural_mappings] == [783, 784, 792]
    assert [item.evidence_role for item in result.structural_mappings] == [
        "NOTE_TITLE",
        "AXIS_HEADER",
        "AXIS_HEADER",
    ]
    assert all(
        item.source_line_ids and item.bbox is not None for item in result.structural_mappings
    )
    assert len(result.mapped_assignments) == 22
    assert {item.axis_role for item in result.mapped_assignments} == {
        "OVERALL_SPECIFIC",
        "OVERALL_GENERAL",
    }
    assert all(
        item.mapping_role == "OVERALL_SPECIFIC_OR_GENERAL_DIRECT_VISIBLE_CELL"
        and item.unit == "VND"
        and item.unit_multiplier == 1_000_000
        and item.value_bbox is not None
        for item in result.mapped_assignments
    )
    q1 = [item for item in result.mapped_assignments if item.panel_key == "Q1_2026"]
    assert [(item.report_norm_id, item.observation, item.value) for item in q1] == [
        (793, "VALUE", 5_052_448),
        (785, "VALUE", 8_098_145),
        (794, "VALUE", 3_185_262),
        (786, "VALUE", 265_999),
        (795, "VALUE", -1_892_559),
        (787, "DASH", None),
        (796, "VALUE", 966),
        (788, "VALUE", 69),
        (799, "VALUE", 6_346_117),
        (791, "VALUE", 8_364_213),
    ]
    mapped_dashes = [item for item in result.mapped_assignments if item.observation == "DASH"]
    assert len(mapped_dashes) == 2
    assert all(
        item.report_norm_id == 787 and item.value is None and item.visual_cell_evidence is not None
        for item in mapped_dashes
    )


def test_audit_adjustment_maps_only_user_confirmed_overall_axes(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    audit = next(item for item in result.source_dispositions if item.row_role == "AUDIT_ADJUSTMENT")

    assert audit.status == TMPage34SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
    assert not audit.question_required
    assert audit.candidate_report_norm_ids == ()
    assert audit.values[6:9] == (33_942, -1_444, 32_498)
    mapped = [
        cell
        for cell in audit.cell_dispositions
        if cell.status == TMPage34CellStatus.MAPPED_AUTOMATIC_SCOPED.value
    ]
    assert [(cell.axis_role, cell.report_norm_ids, cell.value) for cell in mapped] == [
        ("OVERALL_SPECIFIC", (798,), 33_942),
        ("OVERALL_GENERAL", (790,), -1_444),
    ]
    source_only = [
        cell
        for source in result.source_dispositions
        for cell in source.cell_dispositions
        if cell.status == TMPage34CellStatus.SOURCE_ONLY_GEOGRAPHIC_OR_COMBINED_AXIS.value
    ]
    assert len(source_only) == 77
    assert all(
        cell.axis_role not in {"OVERALL_SPECIFIC", "OVERALL_GENERAL"} and not cell.report_norm_ids
        for cell in source_only
    )
    combined = next(
        cell for cell in audit.cell_dispositions if cell.axis_role == "OVERALL_COMBINED"
    )
    assert combined.value == 32_498
    assert combined.report_norm_ids == ()
    assert not combined.question_required


def test_geographic_measure_rollforward_and_cross_panel_checks_are_dash_safe(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.accounting_check_count == 84
    assert result.accounting_pass_count == 46
    assert result.accounting_not_testable_count == 38
    assert result.duplicate_check_count == result.duplicate_pass_count == 9
    assert all(check.status != "FAIL" for check in result.accounting_checks)
    not_testable = [
        check
        for check in result.accounting_checks
        if check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO"
    ]
    assert len(not_testable) == 38
    assert all(
        check.expected_value is check.observed_value is check.residual is None
        for check in not_testable
    )
    assert all(check.status == "PASS" and check.residual == 0 for check in result.duplicate_checks)


def test_mapping_policy_pins_user_confirmed_overall_axes_and_forbidden_inputs(
    project_root: Path, tmp_path: Path
) -> None:
    source = project_root / TM_PAGE34_MAPPING_POLICY_RELATIVE_PATH
    policy = load_tm_page34_mapping_policy(source)
    assert set(policy.forbidden_mapping_inputs) == {
        "numeric_cell_text",
        "numeric_cell_value_as_item_selector",
        "numeric_value_magnitude",
        "historical_or_mongodb_values",
        "human_review_answers",
        "dash_as_zero",
        "accounting_equation_result_as_item_selector",
    }

    drifted_axis = tmp_path / "drifted-axis.yaml"
    drifted_axis.write_text(
        source.read_text(encoding="utf-8").replace(
            "axis_report_norm_ids: {OVERALL_SPECIFIC: 793, OVERALL_GENERAL: 785}",
            "axis_report_norm_ids: {OVERALL_SPECIFIC: 793, OVERALL_COMBINED: 785}",
            1,
        ),
        encoding="utf-8",
    )
    with pytest.raises(TMPage34MappingError, match="entry is invalid|authority"):
        load_tm_page34_mapping_policy(drifted_axis)

    drifted_audit = tmp_path / "drifted-audit.yaml"
    drifted_audit.write_text(
        source.read_text(encoding="utf-8").replace(
            "OVERALL_SPECIFIC: 798, OVERALL_GENERAL: 790",
            "OVERALL_SPECIFIC: 790, OVERALL_GENERAL: 798",
            1,
        ),
        encoding="utf-8",
    )
    with pytest.raises(TMPage34MappingError, match="locations drifted"):
        load_tm_page34_mapping_policy(drifted_audit)
