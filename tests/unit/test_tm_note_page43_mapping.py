from __future__ import annotations

from pathlib import Path

import pytest

from bctc_ai.mapping.tm_note_page43_mapping import (
    TM_PAGE43_POLICY_RELATIVE_PATH,
    TMPage43CellStatus,
    TMPage43MappingError,
    TMPage43SchemaStatus,
    TMPage43SourceStatus,
    load_tm_page43_mapping_policy,
    reconcile_tm_page43_items,
    validate_tm_page43_mapping_result,
)
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.tm_note_page43 import load_tm_page43_policy, parse_tm_page43

_OCR_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0043-ppocrv6-word-box.json")
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_MAPPED_IDS = {
    631,
    660,
    661,
    662,
    663,
    674,
    675,
    676,
    677,
    688,
    689,
    690,
    691,
    702,
    703,
    704,
    705,
    1055,
    1056,
    1057,
    1058,
    1059,
    1060,
    1061,
    1062,
    1066,
    1067,
    1068,
    1069,
    1075,
    1089,
    1092,
    1093,
    5977,
}
_SCOPED_IDS = set(range(631, 716)) | set(range(1055, 1100)) | {5977}


def _mapped(project_root: Path, tmp_path: Path):
    render = Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={43},
        )[0].path
    )
    parsed = parse_tm_page43(
        project_root / _OCR_FIXTURE,
        render,
        load_tm_page43_policy(project_root / "config/tables/tm-note-page43-v1.yaml"),
    )
    _workbooks, schema = load_all(project_root / "template", project_root)
    return reconcile_tm_page43_items(
        parsed,
        schema=schema,
        policy=load_tm_page43_mapping_policy(project_root / TM_PAGE43_POLICY_RELATIVE_PATH),
        source_pdf_path=project_root / _SOURCE_PDF,
    )


def test_page43_reconciles_complete_two_branch_scope_and_exact_source_denominators(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert validate_tm_page43_mapping_result(result) is result
    assert result.mapping_authority_scope.endswith("FIXED_ROWS_AND_CELLS_ONLY")
    assert result.mapping_authority_granted
    assert result.schema_item_count == 1_721
    assert result.status_reconciled_schema_count == 131
    assert result.mapped_schema_count == 34
    assert result.ambiguous_schema_count == 0
    assert result.not_observed_schema_count == 97
    assert result.not_applicable_schema_count == 0
    assert result.unassessed_schema_count == (
        result.schema_item_count - result.status_reconciled_schema_count
    )
    assert result.fully_verified_schema_count == 0
    assert result.source_row_count == 29
    assert result.mapped_source_row_count == 24
    assert result.ambiguous_source_row_count == 0
    assert result.source_only_row_count == 5
    assert result.partially_mapped_source_row_count == 6
    assert (
        result.mapped_source_row_count
        + result.ambiguous_source_row_count
        + result.source_only_row_count
        == 29
    )
    assert result.financial_slot_count == 50
    assert result.extracted_value_count == 44
    assert result.dash_count == 6
    assert result.mapped_source_slot_count == 42
    assert result.mapped_value_assignment_count == 38
    assert result.mapped_dash_assignment_count == 8
    assert result.mapped_status_assignment_count == 46


def test_exact_mapped_ambiguous_not_observed_and_unassessed_schema_sets(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in {item.value for item in TMPage43SchemaStatus}
    }

    assert by_status[TMPage43SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] == _MAPPED_IDS
    assert by_status[TMPage43SchemaStatus.AMBIGUOUS_MAPPING.value] == set()
    assert by_status[TMPage43SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] == (
        _SCOPED_IDS - _MAPPED_IDS
    )
    assert len(by_status[TMPage43SchemaStatus.UNASSESSED.value]) == (result.unassessed_schema_count)
    assert (
        _MAPPED_IDS | by_status[TMPage43SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] == _SCOPED_IDS
    )


def test_deposit_and_trust_assignments_carry_exact_period_value_status_and_unit(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    root_deposit = [item for item in result.mapped_assignments if item.report_norm_id == 1055]
    trust_root = [item for item in result.mapped_assignments if item.report_norm_id == 1092]
    assert [item.value for item in root_deposit] == [905_918_332, 921_368_132]
    assert [item.period_end for item in root_deposit] == ["2026-03-31", "2025-12-31"]
    assert [item.period_role for item in root_deposit] == ["CURRENT", "COMPARATIVE"]
    assert [item.value for item in trust_root] == [3_247_015, 3_912_833]
    assert all(item.observation == "VALUE" for item in [*root_deposit, *trust_root])
    assert all(
        item.unit == "VND" and item.unit_multiplier == 1_000_000
        for item in result.mapped_assignments
    )
    assert not any(item.report_norm_id in {631, 1056, 1075} for item in result.mapped_assignments)


def test_four_authorized_aggregate_child_reuses_keep_one_exact_source_cell_provenance(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    reused = {}
    for item in result.mapped_assignments:
        if item.mapping_role != "DIRECT_VISIBLE_ROW_OR_MEASURE":
            reused.setdefault((item.row_id, item.cell_index), []).append(item)

    expected = {
        ("page-0043:derivatives:row-0003", 0): (660, 661),
        ("page-0043:derivatives:row-0003", 1): (688, 689),
        ("page-0043:derivatives:row-0007", 0): (674, 675),
        ("page-0043:derivatives:row-0007", 1): (702, 703),
    }
    assert {
        key: tuple(item.report_norm_id for item in assignments)
        for key, assignments in reused.items()
    } == expected
    for assignments in reused.values():
        assert [item.mapping_role for item in assignments] == [
            "AGGREGATE_MEASURE_TOTAL_FROM_COMBINED_VISIBLE_ROW",
            "PRIMARY_ONLY_VISIBLE_CURRENCY_DERIVATIVE_CHILD",
        ]
        assert len({item.observation for item in assignments}) == 1
        assert len({item.value for item in assignments}) == 1
        assert len({item.period_end for item in assignments}) == 1
        if assignments[0].observation == "DASH":
            assert assignments[0].value is assignments[1].value is None
            assert assignments[0].visual_cell_evidence == assignments[1].visual_cell_evidence


def test_net_measure_abstains_while_tckt_and_personal_rows_map_exactly(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    net_cells = [
        cell
        for source in result.source_dispositions
        if source.table_key == "DERIVATIVES" and source.row_kind == "NUMERIC"
        for cell in source.cell_dispositions
        if cell.measure_role == "NET_CARRYING"
    ]
    assert len(net_cells) == 6
    assert [cell.value for cell in net_cells] == [
        -661_326,
        -150_745,
        -510_581,
        -698_507,
        -19_293,
        -679_214,
    ]
    assert all(
        cell.status == TMPage43CellStatus.SOURCE_ONLY_QUESTION.value
        and not cell.report_norm_ids
        and cell.question_required
        for cell in net_cells
    )
    tckt = next(
        item
        for item in result.source_dispositions
        if item.row_id == "page-0043:deposit_customer:row-0002"
    )
    personal = next(
        item
        for item in result.source_dispositions
        if item.row_id == "page-0043:deposit_customer:row-0003"
    )
    assert tckt.status == TMPage43SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
    assert tckt.values == (365_071_880, 402_397_512)
    assert tckt.row_report_norm_ids == (5977,)
    assert tckt.candidate_report_norm_ids == ()
    assert not tckt.question_required
    assert personal.status == TMPage43SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
    assert personal.values == (540_846_452, 518_970_620)
    assert personal.row_report_norm_ids == (1089,)
    assert personal.candidate_report_norm_ids == ()
    assert not personal.question_required
    assert result.source_question_row_count == 6
    customer_assignments = [
        item for item in result.mapped_assignments if item.report_norm_id in {1089, 5977}
    ]
    assert [
        (item.report_norm_id, item.value, item.period_end, item.period_role)
        for item in customer_assignments
    ] == [
        (5977, 365_071_880, "2026-03-31", "CURRENT"),
        (5977, 402_397_512, "2025-12-31", "COMPARATIVE"),
        (1089, 540_846_452, "2026-03-31", "CURRENT"),
        (1089, 518_970_620, "2025-12-31", "COMPARATIVE"),
    ]


def test_accounting_and_duplicate_validation_combines_to_24_pass_and_two_dash_abstentions(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.accounting_check_count == 16
    assert result.accounting_pass_count == 14
    assert result.accounting_not_testable_count == 2
    assert result.duplicate_check_count == result.duplicate_pass_count == 10
    assert result.accounting_pass_count + result.duplicate_pass_count == 24
    assert all(check.status != "FAIL" for check in result.accounting_checks)
    assert all(check.status == "PASS" and check.residual == 0 for check in result.duplicate_checks)
    not_testable = [
        check
        for check in result.accounting_checks
        if check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO"
    ]
    assert [check.axis_role for check in not_testable] == ["CURRENT", "COMPARATIVE"]
    assert all(
        check.expected_value is check.observed_value is check.residual is None
        for check in not_testable
    )


def test_mapping_policy_pins_reuse_locations_and_forbids_values_history_review_and_dash_zero(
    project_root: Path, tmp_path: Path
) -> None:
    source = project_root / TM_PAGE43_POLICY_RELATIVE_PATH
    policy = load_tm_page43_mapping_policy(source)
    assert set(policy.forbidden_mapping_inputs) == {
        "numeric_cell_text",
        "numeric_cell_value_as_item_selector",
        "numeric_value_magnitude",
        "historical_or_mongodb_values",
        "human_review_answers",
        "dash_as_zero",
        "accounting_equation_result_as_item_selector",
    }

    drifted = tmp_path / "drifted-page43-mapping.yaml"
    drifted.write_text(
        source.read_text(encoding="utf-8")
        .replace(
            "cell_report_norm_ids: [[660, 661], [688, 689], []]",
            "cell_report_norm_ids: [[661], [688, 689], []]",
            1,
        )
        .replace(
            "cell_report_norm_ids: [[662], [690], []]",
            "cell_report_norm_ids: [[660, 662], [690], []]",
            1,
        ),
        encoding="utf-8",
    )
    with pytest.raises(TMPage43MappingError, match="reuse"):
        load_tm_page43_mapping_policy(drifted)
