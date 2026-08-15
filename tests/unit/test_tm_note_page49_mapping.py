from __future__ import annotations

from pathlib import Path

from bctc_ai.mapping.tm_note_page49_mapping import (
    TMPage49SchemaStatus,
    TMPage49SourceStatus,
    load_tm_page49_mapping_policy,
    reconcile_tm_page49_items,
)
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.tm_note_page49 import load_tm_page49_policy, parse_tm_page49

_OCR_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0049-ppocrv6-word-box.json")
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")


def _mapped(project_root: Path, tmp_path: Path):
    render = Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={49},
        )[0].path
    )
    parsed = parse_tm_page49(
        project_root / _OCR_FIXTURE,
        render,
        load_tm_page49_policy(project_root / "config/tables/tm-note-page49-v1.yaml"),
    )
    _, schema = load_all(project_root / "template", project_root)
    return reconcile_tm_page49_items(
        parsed,
        schema=schema,
        policy=load_tm_page49_mapping_policy(
            project_root / "config/mapping/tm-note-page49-v1.yaml"
        ),
        source_pdf_path=project_root / _SOURCE_PDF,
    )


def test_page49_reconciles_exact_business_and_source_denominators(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.schema_item_count == 1_717
    assert result.status_reconciled_schema_count == 22
    assert result.mapped_schema_count == 10
    assert result.ambiguous_schema_count == 0
    assert result.not_observed_schema_count == 12
    assert result.not_applicable_schema_count == 0
    assert result.unassessed_schema_count == 1_695
    assert result.fully_verified_schema_count == 0
    assert result.source_row_count == 12
    assert result.mapped_source_row_count == 10
    assert result.ambiguous_source_row_count == 0
    assert result.source_only_row_count == 2
    assert result.source_question_row_count == 0
    assert result.financial_slot_count == 28
    assert result.extracted_value_count == 27
    assert result.dash_count == 1
    assert result.mapped_value_count == 27


def test_page49_exact_mapped_ambiguous_not_observed_and_unassessed_sets(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in {item.value for item in TMPage49SchemaStatus}
    }

    assert by_status[TMPage49SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] == {
        1221,
        1227,
        1228,
        1269,
        1270,
        1271,
        1278,
        6031,
        6032,
        6033,
    }
    assert by_status[TMPage49SchemaStatus.AMBIGUOUS_MAPPING.value] == set()
    assert by_status[TMPage49SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] == {
        1222,
        1223,
        1224,
        1225,
        1226,
        1272,
        1273,
        1274,
        1275,
        1276,
        1277,
        1279,
    }
    assert len(by_status[TMPage49SchemaStatus.UNASSESSED.value]) == 1_695
    assert 1220 in by_status[TMPage49SchemaStatus.UNASSESSED.value]
    assert 1280 in by_status[TMPage49SchemaStatus.UNASSESSED.value]


def test_page49_three_schema_gap_rows_map_exact_values_periods_and_no_candidates(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    resolved = [
        item for item in result.source_dispositions if item.report_norm_id in {6031, 6032, 6033}
    ]

    assert [(item.report_norm_id, item.row_id, item.values) for item in resolved] == [
        (6031, "page-0049:risk_provision_expense:row-0002", (3_451_261, 2_973_316)),
        (6032, "page-0049:risk_provision_expense:row-0003", (1_648, 76)),
        (6033, "page-0049:risk_provision_expense:row-0004", (1_775, 24_681)),
    ]
    assert all(item.period_roles == ("CURRENT", "COMPARATIVE") for item in resolved)
    assert all(
        item.status == TMPage49SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
        and not item.question_required
        and not item.candidate_report_norm_ids
        for item in resolved
    )


def test_page49_fixed_tax_rows_preserve_all_four_axes_and_root_total(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    mapped = {
        item.report_norm_id: item
        for item in result.source_dispositions
        if item.report_norm_id is not None
    }

    assert mapped[1270].values == (175_047, 289_454, -349_300, 115_201)
    assert mapped[1271].values == (3_897_818, 1_919_809, -3_908_383, 1_909_244)
    assert mapped[1278].values == (145_394, 951_670, -982_207, 114_857)
    assert mapped[1269].values == (4_218_259, 3_160_933, -5_239_890, 2_139_302)
    assert all(
        item.period_roles
        == (
            "OPENING_BALANCE",
            "PAYABLE_ACTIVITY",
            "PAID_ACTIVITY",
            "CLOSING_BALANCE",
        )
        for report_norm_id, item in mapped.items()
        if report_norm_id in {1269, 1270, 1271, 1278}
    )


def test_page49_five_checks_pass_and_dash_equation_is_not_testable(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.accounting_check_count == 6
    assert result.accounting_pass_count == 5
    assert result.accounting_not_testable_count == 1
    assert all(check.residual == 0 for check in result.accounting_checks if check.status == "PASS")
    not_testable = [
        check
        for check in result.accounting_checks
        if check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO"
    ]
    assert len(not_testable) == 1
    assert not_testable[0].axis_role == "CURRENT"
    assert not_testable[0].expected_value is None
    assert not_testable[0].residual is None


def test_page49_mapping_forbids_values_history_review_dash_zero_and_equation_selection(
    project_root: Path,
) -> None:
    policy = load_tm_page49_mapping_policy(project_root / "config/mapping/tm-note-page49-v1.yaml")

    assert set(policy.scoped_schema_ids) == {
        *range(1221, 1229),
        *range(1269, 1280),
        6031,
        6032,
        6033,
    }
    assert set(policy.forbidden_mapping_inputs) == {
        "numeric_cell_text",
        "numeric_cell_value_as_item_selector",
        "numeric_value_magnitude",
        "historical_or_mongodb_values",
        "human_review_answers",
        "dash_as_zero",
        "accounting_equation_result_as_item_selector",
    }
