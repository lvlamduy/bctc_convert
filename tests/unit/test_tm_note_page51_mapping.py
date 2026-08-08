from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from bctc_ai.mapping.tm_note_page51_mapping import (
    TMPage51MappingError,
    TMPage51SchemaStatus,
    TMPage51SourceStatus,
    load_tm_page51_mapping_policy,
    reconcile_tm_page51_items,
)
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.tm_note_page51 import load_tm_page51_policy, parse_tm_page51

_OCR_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0051-ppocrv6-word-box.json")
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")


def _inputs(project_root: Path, tmp_path: Path):
    render = Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={51},
        )[0].path
    )
    parsed = parse_tm_page51(
        project_root / _OCR_FIXTURE,
        render,
        load_tm_page51_policy(project_root / "config/tables/tm-note-page51-v1.yaml"),
    )
    _, schema = load_all(project_root / "template", project_root)
    _, hierarchy = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml",
        project_root,
        schema,
    )
    apply_hierarchy_reference(schema, hierarchy)
    policy = load_tm_page51_mapping_policy(project_root / "config/mapping/tm-note-page51-v1.yaml")
    return parsed, schema, policy


def _mapped(project_root: Path, tmp_path: Path):
    parsed, schema, policy = _inputs(project_root, tmp_path)
    return reconcile_tm_page51_items(
        parsed,
        schema=schema,
        policy=policy,
        source_pdf_path=project_root / _SOURCE_PDF,
    )


def test_page51_reconciles_exact_business_and_source_denominators(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.schema_item_count == 1_701
    assert result.status_reconciled_schema_count == 15
    assert result.mapped_schema_count == 10
    assert result.value_bearing_mapped_schema_count == 9
    assert result.not_observed_schema_count == 5
    assert result.ambiguous_schema_count == 0
    assert result.not_applicable_schema_count == 0
    assert result.unassessed_schema_count == 1_686
    assert result.fully_verified_schema_count == 0
    assert result.source_row_count == 11
    assert result.mapped_source_row_count == 9
    assert result.source_only_row_count == 2
    assert result.source_question_row_count == 0
    assert result.financial_slot_count == 18
    assert result.extracted_value_count == 18
    assert result.dash_count == 0
    assert result.mapped_value_count == 18
    assert result.narrative_record_count == 7
    assert result.mapped_narrative_record_count == 1
    assert result.narrative_quantity_count == 2


def test_page51_exact_mapped_not_observed_and_unassessed_sets(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in {item.value for item in TMPage51SchemaStatus}
    }

    assert by_status[TMPage51SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] == {
        1294,
        1295,
        1296,
        1300,
        1301,
        1304,
        5741,
        5742,
        5743,
        5744,
    }
    assert by_status[TMPage51SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] == {
        1297,
        1298,
        1299,
        1302,
        1303,
    }
    assert len(by_status[TMPage51SchemaStatus.UNASSESSED.value]) == 1_686


def test_page51_nine_value_mappings_keep_exact_values_periods_unit_and_no_questions(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    mapped = {
        item.report_norm_id: item
        for item in result.source_dispositions
        if item.status == TMPage51SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
    }

    assert mapped[1296].values == (1_681_823, 1_684_717)
    assert mapped[1301].values == (723_980_330, 618_888_427)
    assert mapped[5741].values == (1_302_737, 9_738_358)
    assert mapped[5742].values == (2_160_046, 8_752_345)
    assert mapped[5743].values == (359_933_489, 299_830_234)
    assert mapped[5744].values == (360_584_058, 300_567_490)
    assert mapped[1295].values == (71_763_365, 59_728_018)
    assert mapped[1300].values == (186_098_713, 190_317_517)
    assert mapped[1304].values == (117_681_586, 127_878_633)
    assert all(item.period_roles == ("CURRENT", "COMPARATIVE") for item in mapped.values())
    assert all(item.unit == "VND" and item.unit_multiplier == 1_000_000 for item in mapped.values())
    assert all(not item.question_required for item in result.source_dispositions)


def test_page51_hierarchy_and_exact_structural_heading_are_bound_without_a_value(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    heading = next(item for item in result.narrative_dispositions if item.report_norm_id == 1294)

    assert heading.semantic_role == "CONTINGENT_LIABILITIES_HEADING"
    assert heading.status == "MAPPED_AUTOMATIC_STRUCTURAL_NO_VALUE"
    assert heading.quantity_count == 0
    assert heading.mapping_approved
    assert all(
        item.report_norm_id != 1302 for item in result.source_dispositions if item.report_norm_id
    )

    parsed, schema, policy = _inputs(project_root, tmp_path)
    drifted = deepcopy(schema)
    next(
        item for item in drifted if item.statement_type == "TM" and item.schema_id == 5743
    ).parent_id = 1301
    with pytest.raises(TMPage51MappingError, match="hierarchy parent drifted"):
        reconcile_tm_page51_items(
            parsed,
            schema=drifted,
            policy=policy,
            source_pdf_path=project_root / _SOURCE_PDF,
        )


def test_page51_equations_validate_only_and_never_promote_unprinted_1302(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.validation_check_count == 4
    assert result.validation_pass_count == 2
    assert result.validation_not_testable_count == 2
    passed = [check for check in result.validation_checks if check.status == "PASS"]
    assert [check.residual for check in passed] == [0, 0]
    assert [check.expected_value for check in passed] == [723_980_330, 618_888_427]
    not_testable = [
        check
        for check in result.validation_checks
        if check.status == "NOT_TESTABLE_TARGET_NOT_OBSERVED"
    ]
    assert [check.expected_value for check in not_testable] == [720_517_547, 600_397_724]
    assert all(check.observed_value is None and check.residual is None for check in not_testable)


def test_page51_mapping_forbids_values_history_review_equation_and_narrative_selection(
    project_root: Path,
) -> None:
    policy = load_tm_page51_mapping_policy(project_root / "config/mapping/tm-note-page51-v1.yaml")

    assert set(policy.scoped_schema_ids) == {*range(1294, 1305), *range(5741, 5745)}
    assert set(policy.forbidden_mapping_inputs) == {
        "numeric_cell_text",
        "numeric_cell_value_as_item_selector",
        "numeric_value_magnitude",
        "historical_or_mongodb_values",
        "human_review_answers",
        "dash_as_zero",
        "accounting_equation_result_as_item_selector",
        "narrative_quantity_as_schema_value",
        "narrative_text_except_exact_structural_heading",
        "derived_1302_value_as_observed_source",
        "schema_id_outside_page51_scope",
    }
