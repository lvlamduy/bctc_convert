from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from bctc_ai.mapping.tm_note_page58_mapping import (
    TMPage58MappingError,
    TMPage58SchemaStatus,
    TMPage58SourceStatus,
    load_tm_page58_mapping_policy,
    reconcile_tm_page58_items,
)
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.tm_note_page58 import load_tm_page58_policy, parse_tm_page58

_OCR_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0058-ppocrv6-word-box.json")
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_SCHEMA_WORKBOOK = Path("template/Bank_TM_ReportNormId.v2.xlsx")


def _inputs(project_root: Path, tmp_path: Path):
    render = Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={58},
        )[0].path
    )
    parsed = parse_tm_page58(
        project_root / _OCR_FIXTURE,
        render,
        load_tm_page58_policy(project_root / "config/tables/tm-note-page58-v1.yaml"),
    )
    _, schema = load_all(project_root / "template", project_root)
    _, hierarchy = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml",
        project_root,
        schema,
    )
    apply_hierarchy_reference(schema, hierarchy)
    policy = load_tm_page58_mapping_policy(project_root / "config/mapping/tm-note-page58-v1.yaml")
    return parsed, schema, policy


@pytest.fixture(scope="module")
def page58_inputs(project_root: Path, tmp_path_factory: pytest.TempPathFactory):
    return _inputs(project_root, tmp_path_factory.mktemp("tm-page58-mapping"))


@pytest.fixture(scope="module")
def page58_result(project_root: Path, page58_inputs):
    parsed, schema, policy = page58_inputs
    return reconcile_tm_page58_items(
        parsed,
        schema=schema,
        policy=policy,
        source_pdf_path=project_root / _SOURCE_PDF,
        schema_workbook_path=project_root / _SCHEMA_WORKBOOK,
    )


def test_page58_reconciles_exact_schema_source_and_financial_slot_denominators(
    page58_result,
) -> None:
    result = page58_result

    assert result.schema_item_count == 1_613
    assert result.status_reconciled_schema_count == 139
    assert result.mapped_schema_count == 77
    assert result.structural_mapped_schema_count == 5
    assert result.value_bearing_mapped_schema_count == 72
    assert result.not_observed_schema_count == 62
    assert result.unassessed_schema_count == 1_474
    assert result.not_applicable_schema_count == 0
    assert result.ambiguous_schema_count == 0
    assert result.unresolved_schema_count == 0
    assert result.fully_verified_schema_count == 0
    assert result.source_row_count == 20
    assert result.mapped_source_row_count == 18
    assert result.source_only_row_count == 2
    assert result.source_question_row_count == 0
    assert result.financial_slot_count == result.mapped_assignment_count == 72
    assert result.extracted_value_count == 63
    assert result.dash_count == 9
    assert result.schema_workbook_sha256 == (
        "ea5b690e88c2986613e650663eaea3e05860053c5f56e6445d19e6f0a719a8e1"
    )
    assert result.schema_projection_sha256 == (
        "0f3b22d3d1bb65a243a14a69116df83e6a9e5457f2f616e561f0b2d99821736c"
    )


def test_page58_owns_exact_currency_risk_scope_and_keeps_page57_disjoint(
    page58_result,
) -> None:
    mapped = {
        item.report_norm_id
        for item in page58_result.schema_dispositions
        if item.status == TMPage58SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
    }
    not_observed = {
        item.report_norm_id
        for item in page58_result.schema_dispositions
        if item.status == TMPage58SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
    }
    unassessed = {
        item.report_norm_id
        for item in page58_result.schema_dispositions
        if item.status == TMPage58SchemaStatus.UNASSESSED.value
    }

    assert len(mapped) == 77
    assert len(not_observed) == 62
    assert len(unassessed) == 1_474
    assert mapped | not_observed == set(range(1352, 1483)) | set(range(5849, 5857))
    assert not mapped & not_observed
    assert set(range(1405, 1431)) <= not_observed
    assert set(range(5857, 5898)) <= unassessed
    assert not set(range(5857, 5898)) & {
        item.report_norm_id for item in page58_result.mapped_assignments
    }
    assert [item.status for item in page58_result.source_dispositions].count(
        TMPage58SourceStatus.SOURCE_ONLY_CONTEXT.value
    ) == 2
    assert all(not item.question_required for item in page58_result.source_dispositions)


def test_page58_maps_all_cells_by_metric_and_currency_axis_preserving_status(
    page58_result,
) -> None:
    assignments = {item.report_norm_id: item for item in page58_result.mapped_assignments}

    assert assignments[1381].value == 385_410
    assert assignments[1355].value == 36_806
    assert assignments[1433].value == 68_200
    assert assignments[1459].value == 490_416
    assert assignments[1385].observation == "DASH"
    assert assignments[1385].value is None
    assert assignments[5849].observation == "DASH"
    assert assignments[5851].value == 347_892
    assert assignments[5852].value == 74_482_657
    assert assignments[5856].value == 77_813_916
    assert assignments[1397].value == -34_673_329
    assert assignments[1404].value == -1_108_624
    assert assignments[1482].value == -772_008
    dashes = [item for item in page58_result.mapped_assignments if item.observation == "DASH"]
    assert len(dashes) == 9
    assert all(item.value is None for item in dashes)
    assert {(item.unit, item.unit_multiplier) for item in page58_result.mapped_assignments} == {
        ("VND", 1_000_000)
    }
    assert {item.period_type for item in page58_result.mapped_assignments} == {"SNAPSHOT"}
    assert {item.period_start for item in page58_result.mapped_assignments} == {"2026-03-31"}
    assert {item.period_role for item in page58_result.mapped_assignments} == {"CURRENT"}


def test_page58_new_combined_and_total_liability_hierarchy_is_fail_closed(
    project_root: Path, page58_inputs
) -> None:
    parsed, schema, policy = page58_inputs
    by_id = {item.schema_id: item for item in schema if item.statement_type == "TM"}

    for axis_parent, fixed_id, child_a, child_b, header_id, total_id in (
        (1379, 5851, 1389, 1390, 1392, 5852),
        (1353, 5849, 1363, 1364, 1366, 5850),
        (1431, 5853, 1441, 1442, 1444, 5854),
        (1457, 5855, 1467, 1468, 1470, 5856),
    ):
        assert by_id[fixed_id].parent_id == axis_parent
        assert by_id[fixed_id].children == [child_a, child_b]
        assert by_id[child_a].parent_id == fixed_id
        assert by_id[child_b].parent_id == fixed_id
        assert by_id[total_id].parent_id == header_id
        assert by_id[header_id].children[0] == total_id

    drifted = deepcopy(schema)
    next(item for item in drifted if item.schema_id == 5849).children = [1363]
    with pytest.raises(TMPage58MappingError, match="owned schema scope drifted"):
        reconcile_tm_page58_items(
            parsed,
            schema=drifted,
            policy=policy,
            source_pdf_path=project_root / _SOURCE_PDF,
            schema_workbook_path=project_root / _SCHEMA_WORKBOOK,
        )


def test_page58_equations_are_validation_only_and_dash_is_never_zero(page58_result) -> None:
    assert page58_result.validation_check_count == 34
    assert page58_result.validation_pass_count == 26
    assert page58_result.validation_not_testable_count == 8
    assert all(check.status != "FAIL" for check in page58_result.validation_checks)
    expected = {
        "ROW_TOTAL_VALIDATION_ONLY": (18, 14, 4),
        "ASSET_COMPOSITION_VALIDATION_ONLY": (4, 0, 4),
        "LIABILITY_COMPOSITION_VALIDATION_ONLY": (4, 4, 0),
        "ON_BALANCE_POSITION_VALIDATION_ONLY": (4, 4, 0),
        "COMBINED_POSITION_VALIDATION_ONLY": (4, 4, 0),
    }
    for kind, (count, passed, not_testable) in expected.items():
        selected = [check for check in page58_result.validation_checks if check.check_kind == kind]
        assert len(selected) == count
        assert sum(check.status == "PASS" for check in selected) == passed
        assert sum(check.status.startswith("NOT_TESTABLE") for check in selected) == not_testable
    blocked = [check for check in page58_result.validation_checks if check.status.startswith("NOT")]
    assert all(
        check.expected_value is None and check.residual is None and "never coerced" in check.reason
        for check in blocked
    )


def test_page58_mapping_policy_forbids_selector_leakage_and_tampering(
    project_root: Path, page58_inputs
) -> None:
    parsed, schema, policy = page58_inputs

    assert set(policy.forbidden_mapping_inputs) == {
        "numeric_cell_text_as_item_selector",
        "numeric_value_magnitude_as_item_selector",
        "historical_or_mongodb_values",
        "human_review_answers",
        "dash_as_zero",
        "accounting_equation_result_as_item_selector",
        "accounting_equation_result_as_extracted_value",
        "schema_id_outside_page58_scope",
        "page57_value_as_page58_item_selector",
        "page57_value_as_page58_imputation",
    }
    targets = list(policy.metric_target_ids)
    targets[0] = (targets[0][0], (999_999, *targets[0][1][1:]))
    with pytest.raises(TMPage58MappingError, match="mapping policy target drifted"):
        reconcile_tm_page58_items(
            parsed,
            schema=schema,
            policy=replace(policy, metric_target_ids=tuple(targets)),
            source_pdf_path=project_root / _SOURCE_PDF,
            schema_workbook_path=project_root / _SCHEMA_WORKBOOK,
        )
