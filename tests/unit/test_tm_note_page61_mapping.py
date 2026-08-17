from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from bctc_ai.mapping.tm_note_page61_mapping import (
    TM_PAGE61_MAPPED_SCHEMA_IDS,
    TM_PAGE61_NOT_OBSERVED_SCHEMA_IDS,
    TM_PAGE61_SCOPE_IDS,
    TMPage61MappingError,
    TMPage61SchemaStatus,
    load_tm_page61_mapping_policy,
    reconcile_tm_page61_items,
)
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.tm_note_page61 import load_tm_page61_policy, parse_tm_page61

_OCR_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0061-ppocrv6-word-box.json")
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_SCHEMA_WORKBOOK = Path("template/Bank_TM_ReportNormId.v2.xlsx")


def _inputs(project_root: Path, tmp_path: Path):
    render = Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={61},
        )[0].path
    )
    parsed = parse_tm_page61(
        project_root / _OCR_FIXTURE,
        render,
        load_tm_page61_policy(project_root / "config/tables/tm-note-page61-v1.yaml"),
    )
    _, schema = load_all(project_root / "template", project_root)
    _, hierarchy = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml",
        project_root,
        schema,
    )
    apply_hierarchy_reference(schema, hierarchy)
    policy = load_tm_page61_mapping_policy(project_root / "config/mapping/tm-note-page61-v1.yaml")
    return parsed, schema, policy


@pytest.fixture(scope="module")
def page61_inputs(project_root: Path, tmp_path_factory: pytest.TempPathFactory):
    return _inputs(project_root, tmp_path_factory.mktemp("tm-page61-mapping"))


@pytest.fixture(scope="module")
def page61_result(project_root: Path, page61_inputs):
    parsed, schema, policy = page61_inputs
    return reconcile_tm_page61_items(
        parsed,
        schema=schema,
        policy=policy,
        source_pdf_path=project_root / _SOURCE_PDF,
        schema_workbook_path=project_root / _SCHEMA_WORKBOOK,
    )


def test_page61_reconciles_exact_schema_source_and_cell_denominators(page61_result) -> None:
    result = page61_result

    assert result.schema_item_count == 1_719
    assert result.status_reconciled_schema_count == 11
    assert result.mapped_schema_count == 11
    assert result.structural_mapped_schema_count == 1
    assert result.value_bearing_mapped_schema_count == 10
    assert result.not_observed_schema_count == 0
    assert result.unassessed_schema_count == (
        result.schema_item_count - result.status_reconciled_schema_count
    )
    assert result.not_applicable_schema_count == 0
    assert result.ambiguous_schema_count == 0
    assert result.unresolved_schema_count == 0
    assert result.fully_verified_schema_count == 0
    assert result.source_row_count == result.mapped_source_row_count == 10
    assert result.source_question_row_count == 0
    assert result.financial_slot_count == result.mapped_assignment_count == 20
    assert result.extracted_value_count == 20
    assert result.dash_count == 0
    assert result.validation_check_count == 0
    assert result.schema_workbook_sha256 == (
        "8d9e76de0d42aa26591a87a5e2d522e7a69e089528047928b029ac4ed49f2b3c"
    )
    assert result.schema_projection_sha256 == (
        "194df64364a4dd2452252585770128697168feb7014961479dfcbd8db942b695"
    )


def test_page61_owns_exact_exchange_rate_scope_and_is_disjoint(page61_result) -> None:
    mapped = {
        item.report_norm_id
        for item in page61_result.schema_dispositions
        if item.status == TMPage61SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
    }
    unassessed = {
        item.report_norm_id
        for item in page61_result.schema_dispositions
        if item.status == TMPage61SchemaStatus.UNASSESSED.value
    }

    assert mapped == TM_PAGE61_MAPPED_SCHEMA_IDS == TM_PAGE61_SCOPE_IDS
    assert TM_PAGE61_NOT_OBSERVED_SCHEMA_IDS == frozenset()
    assert len(mapped) == 11
    assert len(unassessed) == page61_result.unassessed_schema_count
    assert TM_PAGE61_SCOPE_IDS.isdisjoint(set(range(1759, 1944)) | set(range(5898, 5935)))
    assert all(
        item.source_ids
        for item in page61_result.schema_dispositions
        if item.report_norm_id in mapped
    )
    assert all(
        not item.source_ids
        for item in page61_result.schema_dispositions
        if item.report_norm_id not in mapped
    )
    assert all(not item.question_required for item in page61_result.source_dispositions)


def test_page61_maps_two_decimal_comma_rates_per_currency_with_native_unit(
    page61_result,
) -> None:
    assignments = {
        (item.report_norm_id, item.period_role): item for item in page61_result.mapped_assignments
    }

    assert assignments[(5936, "CURRENT")].raw_value == "26.335,00"
    assert assignments[(5936, "CURRENT")].value == Decimal("26335.00")
    assert assignments[(5936, "PRIOR")].value == Decimal("26290.00")
    assert assignments[(5939, "CURRENT")].value == Decimal("165.68")
    assert assignments[(5944, "PRIOR")].value == Decimal("841.86")
    assert assignments[(5945, "CURRENT")].value == Decimal("2768.95")
    assert all(item.observation == "VALUE" for item in page61_result.mapped_assignments)
    assert all(
        "," in item.raw_value and item.value.as_tuple().exponent == -2
        for item in page61_result.mapped_assignments
    )
    assert {
        (item.unit, item.unit_multiplier, item.unit_denominator)
        for item in page61_result.mapped_assignments
    } == {("VND", 1, "ONE_UNIT_OF_ROW_CURRENCY")}
    assert {item.period_role for item in page61_result.mapped_assignments} == {
        "CURRENT",
        "PRIOR",
    }
    assert {item.period_type for item in page61_result.mapped_assignments} == {"SNAPSHOT"}
    assert {
        (item.period_role, item.period_start, item.period_end)
        for item in page61_result.mapped_assignments
    } == {
        ("CURRENT", "2026-03-31", "2026-03-31"),
        ("PRIOR", "2025-12-31", "2025-12-31"),
    }


def test_page61_hierarchy_and_full_schema_projection_fail_closed(
    project_root: Path, page61_inputs
) -> None:
    parsed, schema, policy = page61_inputs
    by_id = {item.schema_id: item for item in schema if item.statement_type == "TM"}
    assert by_id[5935].parent_id == 1259
    assert by_id[5935].children == list(range(5936, 5946))
    assert [by_id[schema_id].canonical_name for schema_id in range(5936, 5946)] == [
        "USD",
        "EUR",
        "GBP",
        "JPY",
        "CHF",
        "AUD",
        "CAD",
        "SGD",
        "THB",
        "SEK",
    ]
    assert all(
        by_id[schema_id].parent_id == 5935 and by_id[schema_id].children == []
        for schema_id in range(5936, 5946)
    )

    drifted = deepcopy(schema)
    next(item for item in drifted if item.schema_id == 5945).parent_id = 1259
    with pytest.raises(TMPage61MappingError, match="full schema projection drifted"):
        reconcile_tm_page61_items(
            parsed,
            schema=drifted,
            policy=policy,
            source_pdf_path=project_root / _SOURCE_PDF,
            schema_workbook_path=project_root / _SCHEMA_WORKBOOK,
        )


def test_page61_policy_forbids_unit_period_precision_leakage_and_tampering(
    project_root: Path, page61_inputs
) -> None:
    parsed, schema, policy = page61_inputs
    assert {
        "numeric_value_magnitude_as_item_selector",
        "vnd_million_multiplier",
        "decimal_comma_loss_or_integer_rounding",
        "period_axis_swapping",
        "page60_value_as_page61_item_selector",
        "page60_value_as_page61_imputation",
    } <= set(policy.forbidden_mapping_inputs)
    targets = list(policy.currency_target_ids)
    targets[0] = ("USD", 5937)
    tampered = replace(policy, currency_target_ids=tuple(targets))
    with pytest.raises(TMPage61MappingError, match="mapping policy target drifted"):
        reconcile_tm_page61_items(
            parsed,
            schema=schema,
            policy=tampered,
            source_pdf_path=project_root / _SOURCE_PDF,
            schema_workbook_path=project_root / _SCHEMA_WORKBOOK,
        )

    first = parsed.rows[0]
    drifted_first = replace(
        first,
        cell_period_starts=(date(2000, 1, 1), first.cell_period_starts[1]),
    )
    drifted_parsed = replace(parsed, rows=(drifted_first, *parsed.rows[1:]))
    with pytest.raises(TMPage61MappingError, match="row/header period alignment drifted"):
        reconcile_tm_page61_items(
            drifted_parsed,
            schema=schema,
            policy=policy,
            source_pdf_path=project_root / _SOURCE_PDF,
            schema_workbook_path=project_root / _SCHEMA_WORKBOOK,
        )
