from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from bctc_ai.mapping.tm_note_page60_mapping import (
    TM_PAGE60_MAPPED_SCHEMA_IDS,
    TM_PAGE60_NOT_OBSERVED_SCHEMA_IDS,
    TM_PAGE60_SCOPE_IDS,
    TMPage60MappingError,
    TMPage60SchemaStatus,
    TMPage60SourceStatus,
    load_tm_page60_mapping_policy,
    reconcile_tm_page60_items,
)
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.tm_note_page60 import load_tm_page60_policy, parse_tm_page60

_OCR_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0060-ppocrv6-word-box.json")
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_SCHEMA_WORKBOOK = Path("template/Bank_TM_ReportNormId.v2.xlsx")


def _inputs(project_root: Path, tmp_path: Path):
    render = Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={60},
        )[0].path
    )
    parsed = parse_tm_page60(
        project_root / _OCR_FIXTURE,
        render,
        load_tm_page60_policy(project_root / "config/tables/tm-note-page60-v1.yaml"),
    )
    _, schema = load_all(project_root / "template", project_root)
    _, hierarchy = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml",
        project_root,
        schema,
    )
    apply_hierarchy_reference(schema, hierarchy)
    policy = load_tm_page60_mapping_policy(project_root / "config/mapping/tm-note-page60-v1.yaml")
    return parsed, schema, policy


@pytest.fixture(scope="module")
def page60_inputs(project_root: Path, tmp_path_factory: pytest.TempPathFactory):
    return _inputs(project_root, tmp_path_factory.mktemp("tm-page60-mapping"))


@pytest.fixture(scope="module")
def page60_result(project_root: Path, page60_inputs):
    parsed, schema, policy = page60_inputs
    return reconcile_tm_page60_items(
        parsed,
        schema=schema,
        policy=policy,
        source_pdf_path=project_root / _SOURCE_PDF,
        schema_workbook_path=project_root / _SCHEMA_WORKBOOK,
    )


def test_page60_reconciles_exact_schema_source_cell_and_validation_denominators(
    page60_result,
) -> None:
    result = page60_result

    assert result.schema_item_count == 1_710
    assert result.status_reconciled_schema_count == 222
    assert result.mapped_schema_count == 148
    assert result.structural_mapped_schema_count == 8
    assert result.value_bearing_mapped_schema_count == 140
    assert result.not_observed_schema_count == 74
    assert result.unassessed_schema_count == 1_488
    assert result.not_applicable_schema_count == 0
    assert result.ambiguous_schema_count == 0
    assert result.unresolved_schema_count == 0
    assert result.fully_verified_schema_count == 0
    assert result.source_row_count == 22
    assert result.mapped_source_row_count == 20
    assert result.source_only_row_count == 2
    assert result.source_question_row_count == 0
    assert result.financial_slot_count == result.mapped_assignment_count == 140
    assert result.extracted_value_count == 93
    assert result.dash_count == 47
    assert result.validation_check_count == 47
    assert result.validation_pass_count == 31
    assert result.validation_not_testable_count == 16
    assert result.schema_workbook_sha256 == (
        "8912e6cbd279f33d507f1bef2235e46328ddcca97ed382d9ddd3fe453cee08d8"
    )
    assert result.schema_projection_sha256 == (
        "787eb5bda3947450c726c11a680dbc8780a61d3f7e311fd5edd26e5e89853a6d"
    )


def test_page60_owns_exact_scope_and_keeps_page57_page61_disjoint(page60_result) -> None:
    result = page60_result
    mapped = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage60SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
    }
    not_observed = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage60SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
    }
    unassessed = {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == TMPage60SchemaStatus.UNASSESSED.value
    }

    assert mapped == TM_PAGE60_MAPPED_SCHEMA_IDS
    assert not_observed == TM_PAGE60_NOT_OBSERVED_SCHEMA_IDS
    assert mapped | not_observed == TM_PAGE60_SCOPE_IDS
    assert len(mapped) == 148
    assert len(not_observed) == 74
    assert len(unassessed) == 1_488
    assert TM_PAGE60_SCOPE_IDS.isdisjoint(set(range(1483, 1759)) | set(range(5857, 5898)))
    assert TM_PAGE60_SCOPE_IDS.isdisjoint(set(range(5935, 5946)))
    assert set(range(1760, 1806)) <= not_observed
    assert {5906, 5910, 5911, 5916} <= not_observed
    assert all(
        item.source_ids for item in result.schema_dispositions if item.report_norm_id in mapped
    )
    assert all(
        not item.source_ids
        for item in result.schema_dispositions
        if item.report_norm_id not in mapped
    )
    assert [item.status for item in result.source_dispositions].count(
        TMPage60SourceStatus.SOURCE_ONLY_CONTEXT.value
    ) == 2
    assert all(not item.question_required for item in result.source_dispositions)


def test_page60_maps_metric_axis_cells_preserving_dash_snapshot_and_unit(page60_result) -> None:
    assignments = {item.report_norm_id: item for item in page60_result.mapped_assignments}

    assert assignments[5905].value == 23_974_299
    assert assignments[5923].value == 102_219_076
    assert assignments[5933].value == 1_122_849_750
    assert assignments[5909].observation == "DASH"
    assert assignments[5909].value is None
    assert assignments[5930].value == 5_716_976
    assert assignments[5899].value == 25_671_665
    assert assignments[1922].value == 1_626_723_706
    assert assignments[5913].observation == "DASH"
    assert assignments[5913].value is None
    assert assignments[1943].value == 165_248_587
    dashes = [item for item in page60_result.mapped_assignments if item.observation == "DASH"]
    assert len(dashes) == 47
    assert all(item.value is None for item in dashes)
    assert {(item.unit, item.unit_multiplier) for item in page60_result.mapped_assignments} == {
        ("VND", 1_000_000)
    }
    assert {item.period_type for item in page60_result.mapped_assignments} == {"SNAPSHOT"}
    assert {item.period_start for item in page60_result.mapped_assignments} == {"2026-03-31"}
    assert {item.period_end for item in page60_result.mapped_assignments} == {"2026-03-31"}
    assert {item.period_role for item in page60_result.mapped_assignments} == {"CURRENT"}


def test_page60_validation_split_keeps_dash_status_non_arithmetic(page60_result) -> None:
    result = page60_result
    expected = {
        "ROW_TOTAL_VALIDATION_ONLY": (20, 5, 15),
        "ASSETS_MINUS_LIABILITIES_VALIDATION_ONLY": (7, 6, 1),
        "EXTERNAL_PAGE57_TOTAL_VALIDATION_ONLY": (19, 19, 0),
        "DUPLICATE_STATUS_EQUAL": (1, 1, 0),
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
    external = [
        check
        for check in result.validation_checks
        if check.check_kind == "EXTERNAL_PAGE57_TOTAL_VALIDATION_ONLY"
    ]
    assert all(check.external_owner_scope == "page-0057" for check in external)
    assert all(check.status == "PASS" and check.residual == 0 for check in external)
    status = [
        check for check in result.validation_checks if check.check_kind == "DUPLICATE_STATUS_EQUAL"
    ]
    assert len(status) == 1
    assert status[0].metric_key == "DERIVATIVE_ASSETS"
    assert status[0].expected_observation == status[0].observed_observation == "DASH"
    assert status[0].expected_value is status[0].observed_value is status[0].residual is None
    assert "not an arithmetic equality" in status[0].reason


def test_page60_combined_hierarchy_and_schema_projection_fail_closed(
    project_root: Path, page60_inputs
) -> None:
    parsed, schema, policy = page60_inputs
    by_id = {item.schema_id: item for item in schema if item.statement_type == "TM"}
    pairs = (
        (5898, 5905, 5909, 5906, 5910, 5911),
        (1806, 5923, 5924, 1813, 1816, 1817),
        (1829, 5925, 5926, 1836, 1839, 1840),
        (1852, 5927, 5928, 1859, 1862, 1863),
        (1875, 5929, 5930, 1882, 1885, 1886),
        (1898, 5931, 5932, 1905, 1908, 1909),
        (1921, 5933, 5934, 1928, 1931, 1932),
    )
    for parent, loan, fixed, old_loan, fixed_a, fixed_b in pairs:
        assert by_id[loan].parent_id == parent
        assert by_id[loan].children == []
        assert by_id[old_loan].parent_id == parent
        assert by_id[fixed].parent_id == parent
        assert by_id[fixed].children == [fixed_a, fixed_b]
        assert by_id[fixed_a].parent_id == fixed
        assert by_id[fixed_b].parent_id == fixed

    drifted = deepcopy(schema)
    next(item for item in drifted if item.schema_id == 5924).children = []
    with pytest.raises(TMPage60MappingError, match="full schema projection drifted"):
        reconcile_tm_page60_items(
            parsed,
            schema=drifted,
            policy=policy,
            source_pdf_path=project_root / _SOURCE_PDF,
            schema_workbook_path=project_root / _SCHEMA_WORKBOOK,
        )


def test_page60_policy_forbids_selector_leakage_and_target_tampering(
    project_root: Path, page60_inputs
) -> None:
    parsed, schema, policy = page60_inputs
    assert {
        "numeric_value_magnitude_as_item_selector",
        "dash_as_zero",
        "accounting_equation_result_as_extracted_value",
        "page57_value_as_page60_item_selector",
        "page57_value_as_page60_imputation",
        "page61_value_as_page60_item_selector",
        "page61_value_as_page60_imputation",
    } <= set(policy.forbidden_mapping_inputs)
    targets = list(policy.metric_target_ids)
    targets[0] = (targets[0][0], (5901, *targets[0][1][1:]))
    tampered = replace(policy, metric_target_ids=tuple(targets))
    with pytest.raises(TMPage60MappingError, match="mapping policy target drifted"):
        reconcile_tm_page60_items(
            parsed,
            schema=schema,
            policy=tampered,
            source_pdf_path=project_root / _SOURCE_PDF,
            schema_workbook_path=project_root / _SCHEMA_WORKBOOK,
        )

    external = list(policy.external_page57_totals)
    external[0] = replace(external[0], report_norm_id=1737)
    tampered_external = replace(policy, external_page57_totals=tuple(external))
    with pytest.raises(TMPage60MappingError, match="mapping policy target drifted"):
        reconcile_tm_page60_items(
            parsed,
            schema=schema,
            policy=tampered_external,
            source_pdf_path=project_root / _SOURCE_PDF,
            schema_workbook_path=project_root / _SCHEMA_WORKBOOK,
        )

    external[0] = replace(policy.external_page57_totals[0], owner_scope="page-0060")
    tampered_owner = replace(policy, external_page57_totals=tuple(external))
    with pytest.raises(TMPage60MappingError, match="mapping policy target drifted"):
        reconcile_tm_page60_items(
            parsed,
            schema=schema,
            policy=tampered_owner,
            source_pdf_path=project_root / _SOURCE_PDF,
            schema_workbook_path=project_root / _SCHEMA_WORKBOOK,
        )

    first_numeric_index = next(
        index for index, row in enumerate(parsed.rows) if row.metric_key is not None
    )
    first_numeric = parsed.rows[first_numeric_index]
    drifted_row = replace(
        first_numeric,
        cell_period_starts=(date(2000, 1, 1), *first_numeric.cell_period_starts[1:]),
    )
    drifted_rows = list(parsed.rows)
    drifted_rows[first_numeric_index] = drifted_row
    drifted_parsed = replace(parsed, rows=tuple(drifted_rows))
    with pytest.raises(TMPage60MappingError, match="row/header period alignment drifted"):
        reconcile_tm_page60_items(
            drifted_parsed,
            schema=schema,
            policy=policy,
            source_pdf_path=project_root / _SOURCE_PDF,
            schema_workbook_path=project_root / _SCHEMA_WORKBOOK,
        )
