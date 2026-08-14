from __future__ import annotations

from pathlib import Path

import pytest

from bctc_ai.mapping.tm_note_pages37_38_mapping import (
    TM_FIXED_ASSET_MAPPING_POLICY_RELATIVE_PATH,
    TMFixedAssetCellStatus,
    TMFixedAssetMappingError,
    TMFixedAssetSchemaStatus,
    TMFixedAssetSourceStatus,
    load_tm_fixed_asset_pages37_38_mapping_policy,
    reconcile_tm_fixed_asset_pages37_38_items,
    validate_tm_fixed_asset_pages37_38_mapping_result,
)
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.tm_note_pages37_38 import (
    load_tm_fixed_asset_pages37_38_policy,
    parse_tm_fixed_asset_pages37_38,
)

_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_FIXTURES = {
    37: Path("tests/golden/tm/mbb-q1-2026-page-0037-ppocrv6-word-box.json"),
    38: Path("tests/golden/tm/mbb-q1-2026-page-0038-ppocrv6-word-box.json"),
}
_MAPPED_IDS = {
    868,
    869,
    870,
    879,
    882,
    883,
    884,
    887,
    891,
    895,
    *range(5962, 5967),
    *range(5991, 5997),
}
_FORMER_COMPONENT_IDS = {
    871,
    872,
    873,
    874,
    875,
    876,
    877,
    878,
    880,
    881,
    885,
    886,
    888,
    889,
    890,
    892,
    893,
    894,
}
_UNRESOLVED_IDS: set[int] = set()
_NOT_OBSERVED_IDS = _FORMER_COMPONENT_IDS | set(range(896, 913))


def _mapped(project_root: Path, tmp_path: Path):
    renders = render_pages(
        project_root / _SOURCE_PDF,
        tmp_path / "render",
        dpi=300,
        page_numbers={37, 38},
    )
    parsed = parse_tm_fixed_asset_pages37_38(
        {page: project_root / path for page, path in _FIXTURES.items()},
        {record.page: Path(record.path) for record in renders},
        load_tm_fixed_asset_pages37_38_policy(
            project_root / "config/tables/tm-note-pages37-38-v1.yaml"
        ),
    )
    _workbooks, schema = load_all(project_root / "template", project_root)
    return reconcile_tm_fixed_asset_pages37_38_items(
        parsed,
        schema=schema,
        policy=load_tm_fixed_asset_pages37_38_mapping_policy(
            project_root / TM_FIXED_ASSET_MAPPING_POLICY_RELATIVE_PATH
        ),
        source_pdf_path=project_root / _SOURCE_PDF,
    )


def test_pages37_38_reconcile_complete_note10_scope_and_source_denominators(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert validate_tm_fixed_asset_pages37_38_mapping_result(result) is result
    assert result.mapping_authority_scope.endswith("TOTAL_COLUMN_FIXED_ROWS_ONLY")
    assert result.mapping_authority_granted
    assert result.schema_item_count == 1_705
    assert result.status_reconciled_schema_count == 56
    assert result.mapped_schema_count == 21
    assert result.unresolved_schema_count == 0
    assert result.not_observed_schema_count == 35
    assert result.unassessed_schema_count == 1_649
    assert result.fully_verified_schema_count == 0
    assert result.source_row_count == 35
    assert result.mapped_source_row_count == 35
    assert result.source_only_row_count == 0
    assert result.source_question_row_count == 0
    assert result.source_validation_row_count == 0
    assert result.partially_mapped_source_row_count == 29
    assert result.financial_slot_count == 145
    assert result.extracted_value_count == 130
    assert result.dash_count == 15
    assert result.mapped_source_slot_count == 29
    assert result.mapped_value_assignment_count == 28
    assert result.mapped_dash_assignment_count == 1
    assert result.source_only_slot_count == 116
    assert result.asset_class_source_only_slot_count == 116


def test_exact_mapped_unresolved_not_observed_and_unassessed_schema_sets(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in (item.value for item in TMFixedAssetSchemaStatus)
    }

    assert by_status[TMFixedAssetSchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] == _MAPPED_IDS
    assert by_status[TMFixedAssetSchemaStatus.UNRESOLVED.value] == _UNRESOLVED_IDS
    assert by_status[TMFixedAssetSchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] == _NOT_OBSERVED_IDS
    assert len(by_status[TMFixedAssetSchemaStatus.UNASSESSED.value]) == 1_649
    assert _MAPPED_IDS | _UNRESOLVED_IDS | _NOT_OBSERVED_IDS == (
        set(range(868, 913)) | set(range(5962, 5967)) | set(range(5991, 5997))
    )
    unresolved = [
        item
        for item in result.schema_dispositions
        if item.status == TMFixedAssetSchemaStatus.UNRESOLVED.value
    ]
    assert unresolved == []


def test_only_total_cells_map_with_exact_value_period_unit_and_raw_provenance(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.title_mapping.report_norm_id == 868
    assert result.title_mapping.source_line_ids == ("page-0037:line-0001",)
    assert result.title_mapping.title_bbox is not None
    assert len(result.mapped_assignments) == 29
    assert all(
        item.axis_role == "TOTAL"
        and item.cell_index == 4
        and item.mapping_role == "TOTAL_COLUMN_DIRECT_VISIBLE_ROW"
        and item.unit == "VND"
        and item.unit_multiplier == 1_000_000
        and (item.source_line_ids or item.visual_cell_evidence is not None)
        and item.value_bbox is not None
        and (
            item.visual_cell_evidence is not None
            if item.observation == "DASH"
            else item.visual_cell_evidence is None
        )
        for item in result.mapped_assignments
    )
    assert [
        (item.report_norm_id, item.panel_key, item.value) for item in result.mapped_assignments
    ] == [
        (870, "Q1_2026", 9_423_236),
        (5991, "Q1_2026", 56_387),
        (5992, "Q1_2026", -6_224),
        (5993, "Q1_2026", -480),
        (5962, "Q1_2026", 565),
        (882, "Q1_2026", 9_473_484),
        (884, "Q1_2026", 5_617_703),
        (5994, "Q1_2026", 144_587),
        (5995, "Q1_2026", -5_996),
        (5996, "Q1_2026", None),
        (5963, "Q1_2026", 162),
        (895, "Q1_2026", 5_756_456),
        (5965, "Q1_2026", 3_805_533),
        (5966, "Q1_2026", 3_717_028),
        (870, "FY_2025", 9_014_672),
        (5991, "FY_2025", 754_094),
        (5992, "FY_2025", -354_092),
        (879, "FY_2025", -44),
        (5962, "FY_2025", 8_606),
        (882, "FY_2025", 9_423_236),
        (884, "FY_2025", 5_263_976),
        (5994, "FY_2025", 551_766),
        (5995, "FY_2025", -201_454),
        (891, "FY_2025", -31),
        (887, "FY_2025", 1_221),
        (5963, "FY_2025", 2_225),
        (895, "FY_2025", 5_617_703),
        (5965, "FY_2025", 3_750_696),
        (5966, "FY_2025", 3_805_533),
    ]
    q1_open = next(
        item
        for item in result.mapped_assignments
        if item.report_norm_id == 870 and item.panel_key == "Q1_2026"
    )
    fy_reclass = next(item for item in result.mapped_assignments if item.report_norm_id == 879)
    assert (q1_open.period_start, q1_open.period_end, q1_open.period_type) == (
        "2025-12-31",
        "2025-12-31",
        "SNAPSHOT",
    )
    assert (fy_reclass.period_start, fy_reclass.period_end, fy_reclass.period_type) == (
        "2025-01-01",
        "2025-12-31",
        "DURATION",
    )
    audit_adjustment = next(
        item for item in result.mapped_assignments if item.report_norm_id == 887
    )
    assert (
        audit_adjustment.row_id,
        audit_adjustment.canonical_name,
        audit_adjustment.raw_text,
        audit_adjustment.observation,
        audit_adjustment.value,
        audit_adjustment.period_role,
    ) == (
        "page-0038:accumulated_depreciation:row-0006",
        "+ Tăng khác",
        "1.221",
        "VALUE",
        1_221,
        "COMPARATIVE",
    )


def test_asset_class_cells_remain_source_only_while_printed_totals_map(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    cells = [cell for source in result.source_dispositions for cell in source.cell_dispositions]
    class_cells = [
        cell
        for cell in cells
        if cell.status == TMFixedAssetCellStatus.SOURCE_ONLY_ASSET_CLASS_AXIS.value
    ]
    question_totals = [
        cell for cell in cells if cell.status == TMFixedAssetCellStatus.SOURCE_ONLY_QUESTION.value
    ]

    assert len(class_cells) == 116
    assert all(cell.axis_role != "TOTAL" and not cell.report_norm_ids for cell in class_cells)
    assert question_totals == []
    questions = [item for item in result.source_dispositions if item.question_required]
    assert questions == []
    assert all(
        item.status == TMFixedAssetSourceStatus.MAPPED_AUTOMATIC_SCOPED.value
        for item in result.source_dispositions
    )


def test_dash_safe_accounting_and_cross_panel_validation_have_no_failures(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.accounting_check_count == 69
    assert result.accounting_pass_count == 51
    assert result.accounting_not_testable_count == 18
    assert result.duplicate_check_count == result.duplicate_pass_count == 15
    assert all(check.status != "FAIL" for check in result.accounting_checks)
    not_testable = [
        check
        for check in result.accounting_checks
        if check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO"
    ]
    assert len(not_testable) == 18
    assert all(
        check.expected_value is check.observed_value is check.residual is None
        for check in not_testable
    )
    assert all(check.status == "PASS" and check.residual == 0 for check in result.duplicate_checks)
    assert {(check.section_key, check.axis_role) for check in result.duplicate_checks} == {
        (section, axis)
        for section in ("GROSS_COST", "ACCUMULATED_DEPRECIATION", "NET_BOOK_VALUE")
        for axis in ("BUILDINGS", "MACHINERY", "TRANSPORT", "OTHER_TANGIBLE", "TOTAL")
    }


def test_mapping_policy_pins_fixed_locations_total_axis_and_forbidden_inputs(
    project_root: Path, tmp_path: Path
) -> None:
    source = project_root / TM_FIXED_ASSET_MAPPING_POLICY_RELATIVE_PATH
    policy = load_tm_fixed_asset_pages37_38_mapping_policy(source)
    assert set(policy.forbidden_mapping_inputs) == {
        "numeric_cell_text",
        "numeric_cell_value_as_item_selector",
        "numeric_value_magnitude",
        "historical_or_mongodb_values",
        "human_review_answers",
        "dash_as_zero",
        "accounting_equation_result_as_item_selector",
    }

    drifted_location = tmp_path / "drifted-location.yaml"
    drifted_location.write_text(
        source.read_text(encoding="utf-8").replace(
            "section_ordinal: 5, visible_label_anchor: phan loai lai trong nam, "
            "expected_row_kind: NUMERIC, expected_observations: [DASH, VALUE, VALUE, VALUE, VALUE], "
            "disposition: FIXED_TOTAL_CELL, report_norm_id: 879",
            "section_ordinal: 6, visible_label_anchor: phan loai lai trong nam, "
            "expected_row_kind: NUMERIC, expected_observations: [DASH, VALUE, VALUE, VALUE, VALUE], "
            "disposition: FIXED_TOTAL_CELL, report_norm_id: 879",
            1,
        ),
        encoding="utf-8",
    )
    with pytest.raises(TMFixedAssetMappingError, match="fixed mapping locations|duplicated"):
        load_tm_fixed_asset_pages37_38_mapping_policy(drifted_location)

    drifted_axis = tmp_path / "drifted-axis.yaml"
    drifted_axis.write_text(
        source.read_text(encoding="utf-8").replace(
            "disposition: FIXED_TOTAL_CELL, report_norm_id: 870, mapped_axis_role: TOTAL",
            "disposition: FIXED_TOTAL_CELL, report_norm_id: 870, mapped_axis_role: MACHINERY",
            1,
        ),
        encoding="utf-8",
    )
    with pytest.raises(TMFixedAssetMappingError, match="malformed"):
        load_tm_fixed_asset_pages37_38_mapping_policy(drifted_axis)
