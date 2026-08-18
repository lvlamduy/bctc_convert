from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from bctc_ai.mapping.tm_note_page52_mapping import (
    TMPage52MappingError,
    TMPage52SchemaStatus,
    TMPage52SourceStatus,
    load_tm_page52_mapping_policy,
    reconcile_tm_page52_items,
)
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.tm_note_page52 import load_tm_page52_policy, parse_tm_page52

_OCR_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0052-ppocrv6-word-box.json")
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_SCHEMA_WORKBOOK = Path("template/Bank_TM_ReportNormId.v2.xlsx")


def _inputs(project_root: Path, tmp_path: Path):
    render = Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={52},
        )[0].path
    )
    parsed = parse_tm_page52(
        project_root / _OCR_FIXTURE,
        render,
        load_tm_page52_policy(project_root / "config/tables/tm-note-page52-v1.yaml"),
    )
    _, schema = load_all(project_root / "template", project_root)
    _, hierarchy = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml",
        project_root,
        schema,
    )
    apply_hierarchy_reference(schema, hierarchy)
    policy = load_tm_page52_mapping_policy(project_root / "config/mapping/tm-note-page52-v1.yaml")
    return parsed, schema, policy


def _mapped(project_root: Path, tmp_path: Path):
    parsed, schema, policy = _inputs(project_root, tmp_path)
    return reconcile_tm_page52_items(
        parsed,
        schema=schema,
        policy=policy,
        source_pdf_path=project_root / _SOURCE_PDF,
        schema_workbook_path=project_root / _SCHEMA_WORKBOOK,
    )


def test_page52_reconciles_promoted_schema_source_and_assignment_denominators(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.schema_item_count == 1_721
    assert result.status_reconciled_schema_count == 19
    assert result.mapped_schema_count == 14
    assert result.value_bearing_mapped_schema_count == 10
    assert result.not_observed_schema_count == 5
    assert result.unassessed_schema_count == (
        result.schema_item_count - result.status_reconciled_schema_count
    )
    assert result.source_row_count == 6
    assert result.mapped_source_row_count == 5
    assert result.source_only_row_count == 1
    assert result.source_question_row_count == 0
    assert result.ambiguous_source_row_count == 0
    assert result.financial_slot_count == 12
    assert result.extracted_value_count == 12
    assert result.dash_count == 0
    assert result.mapped_assignment_count == 12
    assert result.narrative_record_count == 3
    assert result.narrative_quantity_count == 3
    assert not hasattr(result, "automatic_schema_addition_count")
    assert not hasattr(result, "schema_addition_proposals")
    assert not hasattr(result, "proposed_value_count")


def test_page52_owns_exact_promoted_scope_and_preserves_external_owner_roles(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    mapped = {
        item.report_norm_id: item
        for item in result.schema_dispositions
        if item.status == TMPage52SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
    }
    not_observed = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage52SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
    }
    unassessed = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage52SchemaStatus.UNASSESSED.value
    }

    assert set(mapped) == {759, 765, *range(5750, 5762)}
    assert not_observed == {760, 761, 762, 763, 764}
    assert len(unassessed) == result.unassessed_schema_count
    assert {716, 1055, 1295} <= unassessed
    assert all(item.source_row_ids for item in mapped.values())
    assert {
        item.report_norm_id: (item.status, item.owner_scope)
        for item in result.structural_dispositions
    } == {
        716: ("EXTERNAL_OWNER_VALIDATION", "page-0031"),
        759: ("MAPPED_AUTOMATIC_SCOPED", "page-0052"),
        1055: ("EXTERNAL_OWNER_VALIDATION", "page-0043"),
        5753: ("MAPPED_AUTOMATIC_SCOPED", "page-0052"),
        1295: ("EXTERNAL_OWNER_VALIDATION", "page-0051"),
        5756: ("MAPPED_AUTOMATIC_SCOPED", "page-0052"),
        5759: ("MAPPED_AUTOMATIC_SCOPED", "page-0052"),
    }
    assert [item.status for item in result.source_dispositions] == [
        TMPage52SourceStatus.MAPPED_AUTOMATIC_SCOPED.value,
        TMPage52SourceStatus.MAPPED_AUTOMATIC_SCOPED.value,
        TMPage52SourceStatus.MAPPED_AUTOMATIC_SCOPED.value,
        TMPage52SourceStatus.SOURCE_ONLY_VALIDATION.value,
        TMPage52SourceStatus.MAPPED_AUTOMATIC_SCOPED.value,
        TMPage52SourceStatus.MAPPED_AUTOMATIC_SCOPED.value,
    ]
    assert all(not item.question_required for item in result.source_dispositions)


def test_page52_maps_all_twelve_printed_values_to_promoted_ids_with_period_and_unit(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    by_id_role = {
        (item.report_norm_id, item.period_role): item for item in result.mapped_assignments
    }

    assert by_id_role[(5751, "CURRENT")].value == 37_248_180
    assert by_id_role[(5751, "COMPARATIVE")].value == 40_201_646
    assert by_id_role[(5750, "CURRENT")].value == 37_248_180
    assert by_id_role[(5750, "COMPARATIVE")].value == 40_201_646
    assert by_id_role[(5752, "CURRENT")].value == 1_111_746_709
    assert by_id_role[(765, "CURRENT")].value == 8_815_772
    assert by_id_role[(5754, "CURRENT")].value == 901_132_249
    assert by_id_role[(5755, "CURRENT")].value == 4_786_083
    assert by_id_role[(5757, "CURRENT")].value == 71_244_194
    assert by_id_role[(5758, "CURRENT")].value == 519_171
    assert by_id_role[(5760, "CURRENT")].value == 268_437_816
    assert by_id_role[(5761, "CURRENT")].value == 46_914
    assert {(item.unit, item.unit_multiplier) for item in result.mapped_assignments} == {
        ("VND", 1_000_000)
    }
    assert all(item.observation == "VALUE" for item in result.mapped_assignments)
    assert [item.report_norm_ids for item in result.source_dispositions] == [
        (5750,),
        (5751, 5751),
        (5750, 5750),
        (),
        (5752, 5754, 5757, 5760),
        (765, 5755, 5758, 5761),
    ]


def test_page52_formulas_and_external_owner_values_are_validation_only(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    policy = load_tm_page52_mapping_policy(project_root / "config/mapping/tm-note-page52-v1.yaml")

    assert result.validation_check_count == result.validation_pass_count == 6
    assert result.validation_not_testable_count == 0
    assert [check.expected_value for check in result.validation_checks] == [
        37_248_180,
        40_201_646,
        1_120_562_481,
        905_918_332,
        71_763_365,
        268_484_730,
    ]
    assert [check.target_report_norm_id for check in result.validation_checks] == [
        5750,
        5750,
        759,
        5753,
        5756,
        5759,
    ]
    assert all(
        check.status == "PASS"
        and check.observed_value == check.expected_value
        and check.residual == 0
        for check in result.validation_checks
    )
    assert dict(result.validation_formulas) == {
        5750: (5751,),
        759: (5752, 765),
        5753: (5754, 5755),
        5756: (5757, 5758),
        5759: (5760, 5761),
    }
    assert policy.external_owner_validations[-1].owner_report_norm_ids == (626, 824, 848)
    assert policy.external_owner_validations[-1].owner_scopes == (
        "page-0031",
        "page-0035",
        "page-0036",
    )


def test_page52_promoted_hierarchy_is_fail_closed(project_root: Path, tmp_path: Path) -> None:
    parsed, schema, policy = _inputs(project_root, tmp_path)
    for schema_id in (760, 765, 5754, 5757, 5760):
        drifted = deepcopy(schema)
        next(
            item for item in drifted if item.statement_type == "TM" and item.schema_id == schema_id
        ).parent_id = 716

        with pytest.raises(TMPage52MappingError, match="owned schema branch drifted"):
            reconcile_tm_page52_items(
                parsed,
                schema=drifted,
                policy=policy,
                source_pdf_path=project_root / _SOURCE_PDF,
                schema_workbook_path=project_root / _SCHEMA_WORKBOOK,
            )


def test_page52_forbids_value_history_review_equation_and_adjacent_id_selection(
    project_root: Path,
) -> None:
    policy = load_tm_page52_mapping_policy(project_root / "config/mapping/tm-note-page52-v1.yaml")

    assert set(policy.forbidden_mapping_inputs) == {
        "numeric_cell_text",
        "numeric_value_magnitude",
        "historical_or_mongodb_values",
        "human_review_answers",
        "dash_as_zero",
        "accounting_equation_result_as_item_selector",
        "accounting_equation_result_as_extracted_value",
        "narrative_quantity_as_schema_value",
        "schema_id_outside_page52_scope",
        "silent_mapping_to_semantically_adjacent_existing_item",
    }
    assert not hasattr(policy, "schema_addition_proposals")
