from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from bctc_ai.mapping.tm_note_page48_mapping import (
    TM_PAGE48_POLICY_RELATIVE_PATH,
    TMPage48SchemaStatus,
    TMPage48SourceStatus,
    load_tm_page48_mapping_policy,
    reconcile_tm_page48_items,
    validate_tm_page48_mapping_result,
)
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.tm_note_page48 import load_tm_page48_policy, parse_tm_page48

_OCR_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0048-ppocrv6-word-box.json")
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_MAPPED_IDS = {1198, 1205, 1206, 1207, 1212, 1213, 1214, 1217, 1220}
_NOT_OBSERVED_IDS = {
    1199,
    1200,
    1201,
    1202,
    1203,
    1204,
    1208,
    1209,
    1210,
    1211,
    1215,
    1216,
    1219,
}


def _mapped(project_root: Path, tmp_path: Path):
    render = Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={48},
        )[0].path
    )
    parsed = parse_tm_page48(
        project_root / _OCR_FIXTURE,
        render,
        load_tm_page48_policy(project_root / "config/tables/tm-note-page48-v1.yaml"),
    )
    _workbooks, schema = load_all(project_root / "template", project_root)
    return reconcile_tm_page48_items(
        parsed,
        schema=schema,
        policy=load_tm_page48_mapping_policy(project_root / TM_PAGE48_POLICY_RELATIVE_PATH),
        source_pdf_path=project_root / _SOURCE_PDF,
    )


def test_page48_reconciles_disjoint_22_item_scope_and_maps_nine_items(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert validate_tm_page48_mapping_result(result) is result
    assert result.schema_item_count == 1_701
    assert result.status_reconciled_schema_count == 22
    assert result.mapped_schema_count == 9
    assert result.not_observed_schema_count == 13
    assert result.ambiguous_schema_count == 0
    assert result.unassessed_schema_count == 1_679
    assert result.externally_owned_schema_ids == (1218,)
    assert result.source_row_count == 13
    assert result.mapped_source_row_count == 9
    assert result.source_only_row_count == 4
    assert result.source_question_row_count == 0
    assert result.financial_slot_count == 20
    assert result.extracted_value_count == 19
    assert result.dash_count == 1
    assert result.mapped_value_count == 17
    assert result.auxiliary_source_row_count == 11
    assert result.narrative_quantity_count == 2


def test_exact_schema_partition_excludes_1218_for_page47_owner(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in {item.value for item in TMPage48SchemaStatus}
    }

    assert by_status[TMPage48SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] == _MAPPED_IDS
    assert by_status[TMPage48SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] == _NOT_OBSERVED_IDS
    assert len(by_status[TMPage48SchemaStatus.UNASSESSED.value]) == 1_679
    external = next(item for item in result.schema_dispositions if item.report_norm_id == 1218)
    assert external.status == TMPage48SchemaStatus.UNASSESSED.value
    assert "PAGE47_AMBIGUOUS_LONG_TERM_INVESTMENT_PROVISION" in external.reason


def test_mapped_values_periods_and_dash_status_are_source_preserving(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    by_id = {
        item.report_norm_id: item
        for item in result.source_dispositions
        if item.report_norm_id is not None
    }

    assert by_id[1198].values == (Decimal(30), Decimal(40))
    assert by_id[1205].values == (Decimal(4_347_002), Decimal(3_949_958))
    assert by_id[1220].values == (Decimal(-2_033), None)
    assert by_id[1220].observations == ("VALUE", "DASH")
    assert by_id[1220].visual_cell_evidence[0] is None
    assert by_id[1220].visual_cell_evidence[1] is not None
    assert by_id[1220].period_roles == ("CURRENT", "COMPARATIVE")
    assert by_id[1220].unit == "VND"
    assert by_id[1220].unit_multiplier == 1_000_000
    assert all(
        item.status == TMPage48SourceStatus.MAPPED_AUTOMATIC_SCOPED.value for item in by_id.values()
    )
    assert not any(item.question_required for item in result.source_dispositions)


def test_six_validation_checks_pass_or_preserve_dash_as_not_testable(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.validation_check_count == 6
    assert result.validation_pass_count == 5
    assert result.validation_not_testable_count == 1
    assert all(check.residual == 0 for check in result.validation_checks if check.status == "PASS")
    not_testable = [
        check
        for check in result.validation_checks
        if check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO"
    ]
    assert len(not_testable) == 1
    assert not_testable[0].check_id == "OPERATING_EXPENSE_SUM_COMPARATIVE"
    assert not_testable[0].expected_value is None


def test_mapping_policy_forbids_auxiliary_narrative_values_and_external_1218_promotion(
    project_root: Path,
) -> None:
    policy = load_tm_page48_mapping_policy(project_root / TM_PAGE48_POLICY_RELATIVE_PATH)

    assert set(policy.scoped_schema_ids) == {*range(1198, 1218), 1219, 1220}
    assert 1218 not in policy.scoped_schema_ids
    assert [(owner.report_norm_id, owner.owner) for owner in policy.external_owners] == [
        (1218, "PAGE47_AMBIGUOUS_LONG_TERM_INVESTMENT_PROVISION")
    ]
    assert {
        "auxiliary_variance_as_schema_value",
        "narrative_quantity_as_schema_value",
        "externally_owned_schema_id_as_page48_status",
        "dash_as_zero",
        "human_review_answers",
    } <= set(policy.forbidden_mapping_inputs)
