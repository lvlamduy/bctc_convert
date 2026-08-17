from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from bctc_ai.mapping.tm_note_page57_mapping import (
    TMPage57MappingError,
    TMPage57SchemaStatus,
    TMPage57SourceStatus,
    load_tm_page57_mapping_policy,
    reconcile_tm_page57_items,
)
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.tm_note_page57 import load_tm_page57_policy, parse_tm_page57

_OCR_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0057-ppocrv6-word-box.json")
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_SCHEMA_WORKBOOK = Path("template/Bank_TM_ReportNormId.v2.xlsx")


def _inputs(project_root: Path, tmp_path: Path):
    render = Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={57},
        )[0].path
    )
    parsed = parse_tm_page57(
        project_root / _OCR_FIXTURE,
        render,
        load_tm_page57_policy(project_root / "config/tables/tm-note-page57-v1.yaml"),
    )
    _, schema = load_all(project_root / "template", project_root)
    _, hierarchy = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml",
        project_root,
        schema,
    )
    apply_hierarchy_reference(schema, hierarchy)
    policy = load_tm_page57_mapping_policy(project_root / "config/mapping/tm-note-page57-v1.yaml")
    return parsed, schema, policy


@pytest.fixture(scope="module")
def page57_inputs(project_root: Path, tmp_path_factory: pytest.TempPathFactory):
    return _inputs(project_root, tmp_path_factory.mktemp("tm-page57-mapping"))


@pytest.fixture(scope="module")
def page57_result(project_root: Path, page57_inputs):
    parsed, schema, policy = page57_inputs
    return reconcile_tm_page57_items(
        parsed,
        schema=schema,
        policy=policy,
        source_pdf_path=project_root / _SOURCE_PDF,
        schema_workbook_path=project_root / _SCHEMA_WORKBOOK,
    )


def test_page57_reconciles_exact_schema_source_and_cell_denominators(
    page57_result,
) -> None:
    result = page57_result

    assert result.schema_item_count == 1_719
    assert result.status_reconciled_schema_count == 317
    assert result.mapped_schema_count == 169
    assert result.structural_mapped_schema_count == 9
    assert result.value_bearing_mapped_schema_count == 160
    assert result.not_observed_schema_count == 148
    assert result.unassessed_schema_count == (
        result.schema_item_count - result.status_reconciled_schema_count
    )
    assert result.not_applicable_schema_count == 0
    assert result.ambiguous_schema_count == 0
    assert result.unresolved_schema_count == 0
    assert result.fully_verified_schema_count == 0
    assert result.source_row_count == 22
    assert result.mapped_source_row_count == 20
    assert result.source_only_row_count == 2
    assert result.source_question_row_count == 0
    assert result.financial_slot_count == result.mapped_assignment_count == 160
    assert result.extracted_value_count == 92
    assert result.dash_count == 68
    assert result.schema_workbook_sha256 == (
        "8d9e76de0d42aa26591a87a5e2d522e7a69e089528047928b029ac4ed49f2b3c"
    )
    assert result.schema_projection_sha256 == (
        "194df64364a4dd2452252585770128697168feb7014961479dfcbd8db942b695"
    )


def test_page57_owns_exact_interest_risk_scope_and_keeps_page58_disjoint(
    page57_result,
) -> None:
    result = page57_result
    mapped = {
        item.report_norm_id: item
        for item in result.schema_dispositions
        if item.status == TMPage57SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
    }
    not_observed = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage57SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
    }
    unassessed = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage57SchemaStatus.UNASSESSED.value
    }

    assert len(mapped) == 169
    assert len(not_observed) == 148
    assert len(unassessed) == result.unassessed_schema_count
    assert set(mapped) | not_observed == set(range(1483, 1759)) | set(range(5857, 5898))
    assert not set(mapped) & not_observed
    assert set(range(5849, 5857)) <= unassessed
    assert not ({*range(5849, 5857)} & {item.report_norm_id for item in result.mapped_assignments})
    assert set(range(1534, 1584)) <= not_observed
    assert set(range(1684, 1734)) <= not_observed
    assert {5877, 5881, 5882, 5887, 5894, 5895} <= not_observed
    assert all(item.source_ids for item in mapped.values())
    assert all(
        not item.source_ids
        for item in result.schema_dispositions
        if item.report_norm_id not in mapped
    )
    assert [item.status for item in result.source_dispositions].count(
        TMPage57SourceStatus.SOURCE_ONLY_CONTEXT.value
    ) == 2
    assert all(not item.question_required for item in result.source_dispositions)


def test_page57_maps_printed_cells_by_metric_and_axis_preserving_dash_period_and_unit(
    page57_result,
) -> None:
    result = page57_result
    assignments = {item.report_norm_id: item for item in result.mapped_assignments}

    assert assignments[5859].value == 23_974_299
    assert assignments[5857].observation == "DASH"
    assert assignments[5857].value is None
    assert assignments[5861].value == 324_460_963
    assert assignments[5876].value == 92_768_242
    assert assignments[5896].value == 1_122_849_750
    assert assignments[5858].value == 5_716_976
    assert assignments[5860].observation == "DASH"
    assert assignments[5880].observation == "DASH"
    assert assignments[5897].value == 5_716_976
    assert assignments[5870].value == 205_986_214
    assert assignments[5893].value == 73_527_644
    assert assignments[1756].value == 165_248_587
    assert assignments[1677].value == -27_092
    dashes = [item for item in result.mapped_assignments if item.observation == "DASH"]
    assert len(dashes) == 68
    assert all(item.value is None for item in dashes)
    assert {(item.unit, item.unit_multiplier) for item in result.mapped_assignments} == {
        ("VND", 1_000_000)
    }
    assert {item.period_type for item in result.mapped_assignments} == {"SNAPSHOT"}
    assert {item.period_start for item in result.mapped_assignments} == {"2026-03-31"}
    assert {item.period_end for item in result.mapped_assignments} == {"2026-03-31"}
    assert {item.period_role for item in result.mapped_assignments} == {"CURRENT"}


def test_page57_combined_item_hierarchy_is_authoritative_and_fail_closed(
    project_root: Path, page57_inputs
) -> None:
    parsed, schema, policy = page57_inputs
    by_id = {item.schema_id: item for item in schema if item.statement_type == "TM"}
    contracts = (
        (1484, 5857, 5858, 1491, 1494, 1495),
        (1509, 5859, 5860, 1516, 1519, 1520),
        (1584, 5861, 5862, 1591, 1594, 1595),
        (1609, 5863, 5864, 1616, 1619, 1620),
        (1634, 5865, 5866, 1641, 1644, 1645),
        (1659, 5867, 5868, 1666, 1669, 1670),
        (5869, 5876, 5880, 5877, 5881, 5882),
        (1734, 5896, 5897, 1741, 1744, 1745),
    )
    for parent, combined_loan, combined_fixed, old_loan, fixed_a, fixed_b in contracts:
        assert by_id[combined_loan].parent_id == parent
        assert by_id[combined_loan].children == []
        assert by_id[old_loan].parent_id == parent
        assert by_id[combined_fixed].parent_id == parent
        assert by_id[combined_fixed].children == [fixed_a, fixed_b]
        assert by_id[fixed_a].parent_id == combined_fixed
        assert by_id[fixed_b].parent_id == combined_fixed

    drifted = deepcopy(schema)
    next(item for item in drifted if item.schema_id == 5857).children = [1491]
    next(item for item in drifted if item.schema_id == 1491).parent_id = 5857
    with pytest.raises(TMPage57MappingError, match="owned schema scope drifted"):
        reconcile_tm_page57_items(
            parsed,
            schema=drifted,
            policy=policy,
            source_pdf_path=project_root / _SOURCE_PDF,
            schema_workbook_path=project_root / _SCHEMA_WORKBOOK,
        )


def test_page57_equations_are_validation_only_and_dash_is_never_zero(
    page57_result,
) -> None:
    result = page57_result

    assert result.validation_check_count == 44
    assert result.validation_pass_count == 10
    assert result.validation_not_testable_count == 34
    assert all(check.status != "FAIL" for check in result.validation_checks)
    expected = {
        "ROW_TOTAL_VALIDATION_ONLY": (20, 2, 18),
        "ASSET_COMPOSITION_VALIDATION_ONLY": (8, 0, 8),
        "LIABILITY_COMPOSITION_VALIDATION_ONLY": (8, 1, 7),
        "ON_BALANCE_GAP_VALIDATION_ONLY": (8, 7, 1),
    }
    for kind, (count, passed, not_testable) in expected.items():
        selected = [check for check in result.validation_checks if check.check_kind == kind]
        assert len(selected) == count
        assert sum(check.status == "PASS" for check in selected) == passed
        assert sum(check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO" for check in selected) == (
            not_testable
        )
    blocked = [
        check for check in result.validation_checks if check.status.startswith("NOT_TESTABLE")
    ]
    assert all(
        check.expected_value is None and check.residual is None and "never coerced" in check.reason
        for check in blocked
    )
    assert all("VALIDATION_ONLY" in check.check_kind for check in result.validation_checks)
    assert "ACCOUNTING_EQUATIONS_AS_POST_MAPPING_VALIDATION_ONLY" in result.mapping_inputs


def test_page57_mapping_policy_forbids_selector_leakage_and_tampering(
    project_root: Path, page57_inputs
) -> None:
    parsed, schema, policy = page57_inputs

    assert set(policy.forbidden_mapping_inputs) == {
        "numeric_cell_text_as_item_selector",
        "numeric_value_magnitude_as_item_selector",
        "historical_or_mongodb_values",
        "human_review_answers",
        "dash_as_zero",
        "accounting_equation_result_as_item_selector",
        "accounting_equation_result_as_extracted_value",
        "schema_id_outside_page57_scope",
        "page58_value_as_page57_item_selector",
        "page58_value_as_page57_imputation",
    }
    targets = list(policy.metric_target_ids)
    targets[0] = (targets[0][0], (1512, *targets[0][1][1:]))
    tampered = replace(policy, metric_target_ids=tuple(targets))
    with pytest.raises(TMPage57MappingError, match="mapping policy target drifted"):
        reconcile_tm_page57_items(
            parsed,
            schema=schema,
            policy=tampered,
            source_pdf_path=project_root / _SOURCE_PDF,
            schema_workbook_path=project_root / _SCHEMA_WORKBOOK,
        )
