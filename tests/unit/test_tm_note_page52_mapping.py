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


def test_page52_reconciles_existing_mapping_and_addition_denominators(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.schema_item_count == 1_417
    assert result.status_reconciled_schema_count == 7
    assert result.mapped_schema_count == 2
    assert result.value_bearing_mapped_schema_count == 1
    assert result.not_observed_schema_count == 5
    assert result.unassessed_schema_count == 1_410
    assert result.automatic_schema_addition_count == 12
    assert result.automatic_value_bearing_addition_count == 9
    assert result.source_row_count == 6
    assert result.existing_mapped_source_row_count == 1
    assert result.schema_addition_source_row_count == 5
    assert result.source_only_row_count == 1
    assert result.source_question_row_count == 0
    assert result.ambiguous_source_row_count == 0
    assert result.financial_slot_count == 12
    assert result.extracted_value_count == 12
    assert result.dash_count == 0
    assert result.mapped_value_count == 1
    assert result.proposed_value_count == 11
    assert result.narrative_record_count == 3
    assert result.narrative_quantity_count == 3


def test_page52_pins_unique_existing_ids_and_external_owner_roles(
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

    assert set(mapped) == {759, 765}
    assert not_observed == {760, 761, 762, 763, 764}
    assert len(unassessed) == 1_410
    assert {716, 1055, 1295} <= unassessed
    assert not ({759, 760, 761, 762, 763, 764, 765} & unassessed)
    assert all(item.source_row_ids for item in mapped.values())
    assert {
        item.report_norm_id: (item.status, item.owner_scope)
        for item in result.structural_dispositions
    } == {
        716: ("EXTERNAL_OWNER_VALIDATION", "page-0031"),
        759: ("MAPPED_AUTOMATIC_SCOPED", "page-0052"),
        1055: ("EXTERNAL_OWNER_VALIDATION", "page-0043"),
        1295: ("EXTERNAL_OWNER_VALIDATION", "page-0051"),
    }
    assert {item.status for item in result.source_dispositions} == {
        TMPage52SourceStatus.SCHEMA_ADDITION_PROPOSED_STRUCTURAL.value,
        TMPage52SourceStatus.SCHEMA_ADDITION_PROPOSED_VALUE.value,
        TMPage52SourceStatus.MIXED_EXISTING_AND_SCHEMA_ADDITION_VALUE.value,
        TMPage52SourceStatus.SOURCE_ONLY_VALIDATION.value,
    }
    foreign = next(
        item
        for item in result.source_dispositions
        if item.status == TMPage52SourceStatus.MIXED_EXISTING_AND_SCHEMA_ADDITION_VALUE.value
    )
    assert foreign.report_norm_ids == (765, None, None, None)
    assert foreign.values[0] == 8_815_772
    assert all(not item.question_required for item in result.source_dispositions)


def test_page52_exact_addition_order_parentage_formulas_and_reparent_intent(
    project_root: Path, tmp_path: Path
) -> None:
    additions = _mapped(project_root, tmp_path).schema_addition_proposals
    by_key = {item.proposal_key: item for item in additions}

    assert [item.proposal_key for item in additions] == [
        "RP_ROOT",
        "RP_DEPOSIT_MB",
        "LOANS_DOMESTIC",
        "DEPOSITS_GEO",
        "DEPOSITS_DOMESTIC",
        "DEPOSITS_FOREIGN",
        "LC_GEO",
        "LC_DOMESTIC",
        "LC_FOREIGN",
        "SECURITIES_GEO",
        "SECURITIES_DOMESTIC",
        "SECURITIES_FOREIGN",
    ]
    assert by_key["RP_ROOT"].parent_report_norm_id == 1259
    assert by_key["RP_ROOT"].insert_after_report_norm_id == 1304
    assert by_key["RP_ROOT"].formula_terms == ("RP_DEPOSIT_MB",)
    assert by_key["RP_DEPOSIT_MB"].parent_proposal_key == "RP_ROOT"
    assert by_key["LOANS_DOMESTIC"].parent_report_norm_id == 759
    assert by_key["LOANS_DOMESTIC"].insert_before_report_norm_id == 760
    assert by_key["LOANS_DOMESTIC"].reparent_existing_report_norm_ids == (
        760,
        761,
        762,
        763,
        764,
    )
    assert 765 not in by_key["LOANS_DOMESTIC"].reparent_existing_report_norm_ids
    assert by_key["DEPOSITS_GEO"].parent_report_norm_id == 1055
    assert by_key["DEPOSITS_GEO"].insert_after_report_norm_id == 1075
    assert by_key["DEPOSITS_GEO"].formula_terms == (
        "DEPOSITS_DOMESTIC",
        "DEPOSITS_FOREIGN",
    )
    assert by_key["LC_GEO"].parent_report_norm_id == 1295
    assert by_key["LC_GEO"].formula_terms == ("LC_DOMESTIC", "LC_FOREIGN")
    assert by_key["SECURITIES_GEO"].parent_report_norm_id == 1259
    assert by_key["SECURITIES_GEO"].insert_after_proposal_key == "RP_ROOT"
    assert by_key["SECURITIES_GEO"].formula_terms == (
        "SECURITIES_DOMESTIC",
        "SECURITIES_FOREIGN",
    )
    assert by_key["DEPOSITS_GEO"].source_row_ids == (
        "page-0052:line-0046",
        "page-0052:line-0050",
    )
    assert by_key["LC_GEO"].source_row_ids == (
        "page-0052:line-0047",
        "page-0052:line-0051",
    )
    assert by_key["SECURITIES_GEO"].source_row_ids == (
        "page-0052:line-0048",
        "page-0052:line-0052",
    )
    assert all(item.report_norm_id is None for item in additions)
    assert all(item.source_row_ids for item in additions)
    assert all(not item.question_required for item in additions)


def test_page52_existing_and_proposed_values_preserve_period_and_unit(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    by_key = {item.proposal_key: item for item in result.schema_addition_proposals}

    assert by_key["RP_ROOT"].observed_values == (37_248_180, 40_201_646)
    assert by_key["RP_DEPOSIT_MB"].observed_values == (37_248_180, 40_201_646)
    assert by_key["RP_ROOT"].period_roles == ("CURRENT", "COMPARATIVE")
    assert by_key["LOANS_DOMESTIC"].observed_values == (1_111_746_709,)
    assert by_key["DEPOSITS_DOMESTIC"].observed_values == (901_132_249,)
    assert by_key["DEPOSITS_FOREIGN"].observed_values == (4_786_083,)
    assert by_key["LC_DOMESTIC"].observed_values == (71_244_194,)
    assert by_key["LC_FOREIGN"].observed_values == (519_171,)
    assert by_key["SECURITIES_DOMESTIC"].observed_values == (268_437_816,)
    assert by_key["SECURITIES_FOREIGN"].observed_values == (46_914,)
    assert {
        item.period_roles
        for item in by_key.values()
        if item.observed_values and item.proposal_key not in {"RP_ROOT", "RP_DEPOSIT_MB"}
    } == {("CURRENT",)}
    assert {
        (item.unit, item.unit_multiplier) for item in by_key.values() if item.observed_values
    } == {("VND", 1_000_000)}
    mapped_foreign = next(
        item
        for item in result.source_dispositions
        if item.report_norm_ids == (765, None, None, None)
    )
    assert mapped_foreign.values[0] == 8_815_772
    assert mapped_foreign.period_roles[0] == "CURRENT"
    assert (mapped_foreign.unit, mapped_foreign.unit_multiplier) == ("VND", 1_000_000)


def test_page52_all_core_checks_pass_with_external_values_validation_only(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    policy = load_tm_page52_mapping_policy(project_root / "config/mapping/tm-note-page52-v1.yaml")

    assert result.validation_check_count == 6
    assert result.validation_pass_count == 6
    assert result.validation_not_testable_count == 0
    assert [check.expected_value for check in result.validation_checks] == [
        37_248_180,
        40_201_646,
        1_120_562_481,
        905_918_332,
        71_763_365,
        268_484_730,
    ]
    assert all(
        check.status == "PASS"
        and check.observed_value == check.expected_value
        and check.residual == 0
        for check in result.validation_checks
    )
    assert [check.target_report_norm_id for check in result.validation_checks] == [
        None,
        None,
        716,
        1055,
        1295,
        None,
    ]
    assert policy.external_owner_validations[-1].owner_report_norm_ids == (626, 824, 848)
    assert policy.external_owner_validations[-1].owner_scopes == (
        "page-0031",
        "page-0035",
        "page-0036",
    )
    assert policy.external_owner_validations[-1].owner_values == (
        5_093_432,
        259_054_739,
        4_336_559,
    )


def test_page52_hierarchy_and_reparent_context_are_fail_closed(
    project_root: Path, tmp_path: Path
) -> None:
    parsed, schema, policy = _inputs(project_root, tmp_path)
    for schema_id in (760, 765):
        drifted = deepcopy(schema)
        next(
            item for item in drifted if item.statement_type == "TM" and item.schema_id == schema_id
        ).parent_id = 716

        with pytest.raises(TMPage52MappingError, match="loan geographic hierarchy drifted"):
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
