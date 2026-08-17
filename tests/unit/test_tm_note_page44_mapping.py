from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from bctc_ai.mapping.tm_note_page44_mapping import (
    TM_PAGE44_POLICY_RELATIVE_PATH,
    TMPage44SchemaStatus,
    TMPage44SourceStatus,
    load_tm_page44_mapping_policy,
    reconcile_tm_page44_items,
    validate_tm_page44_mapping_result,
)
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.tm_note_page44 import load_tm_page44_policy, parse_tm_page44

_OCR_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0044-ppocrv6-word-box.json")
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_MAPPED_IDS = {
    1100,
    1101,
    1109,
    1112,
    1118,
    1119,
    1122,
    1128,
    1129,
    1131,
    1141,
    *range(5978, 5985),
    *range(6008, 6021),
}
_AMBIGUOUS_IDS: set[int] = set()
_UNRESOLVED_IDS: set[int] = set()
_NOT_OBSERVED_IDS = {
    1102,
    1103,
    1104,
    1105,
    1106,
    1107,
    1108,
    1110,
    1111,
    1113,
    1114,
    1115,
    1116,
    1117,
    1120,
    1121,
    1123,
    1124,
    1125,
    1126,
    1127,
    1130,
    *range(1132, 1141),
}


def _mapped(project_root: Path, tmp_path: Path):
    render = Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={44},
        )[0].path
    )
    parsed = parse_tm_page44(
        project_root / _OCR_FIXTURE,
        render,
        load_tm_page44_policy(project_root / "config/tables/tm-note-page44-v1.yaml"),
    )
    _workbooks, schema = load_all(project_root / "template", project_root)
    return reconcile_tm_page44_items(
        parsed,
        schema=schema,
        policy=load_tm_page44_mapping_policy(project_root / TM_PAGE44_POLICY_RELATIVE_PATH),
        source_pdf_path=project_root / _SOURCE_PDF,
    )


def test_page44_reconciles_universal_branch_and_all_source_rows_with_exact_statuses(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert validate_tm_page44_mapping_result(result) is result
    assert result.mapping_authority_scope.endswith("FIXED_ROWS_CELLS_AND_NARRATIVE_FACTS_ONLY")
    assert result.mapping_authority_granted
    assert result.schema_item_count == 1_719
    assert result.status_reconciled_schema_count == 62
    assert result.mapped_schema_count == 31
    assert result.ambiguous_schema_count == 0
    assert result.unresolved_schema_count == 0
    assert result.not_observed_schema_count == 31
    assert result.not_applicable_schema_count == 0
    assert result.unassessed_schema_count == (
        result.schema_item_count - result.status_reconciled_schema_count
    )
    assert result.fully_verified_schema_count == 0
    assert result.source_row_count == 24
    assert result.mapped_source_row_count == 21
    assert result.partial_source_row_count == 2
    assert result.source_only_row_count == 3
    assert result.source_question_row_count == 0
    assert result.context_source_row_count == 3
    assert result.financial_slot_count == 60
    assert result.extracted_value_count == 51
    assert result.dash_count == 9
    assert result.mapped_value_count == 59
    assert result.narrative_fact_count == 5
    assert result.narrative_value_count == 7
    assert result.narrative_mapped_assignment_count == 7


def test_exact_mapped_ambiguous_unresolved_not_observed_and_unassessed_sets(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in {item.value for item in TMPage44SchemaStatus}
    }

    assert by_status[TMPage44SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] == _MAPPED_IDS
    assert by_status[TMPage44SchemaStatus.AMBIGUOUS_MAPPING.value] == _AMBIGUOUS_IDS
    assert by_status[TMPage44SchemaStatus.UNRESOLVED.value] == _UNRESOLVED_IDS
    assert by_status[TMPage44SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] == (_NOT_OBSERVED_IDS)
    assert len(by_status[TMPage44SchemaStatus.UNASSESSED.value]) == (result.unassessed_schema_count)
    assert _MAPPED_IDS | _AMBIGUOUS_IDS | _UNRESOLVED_IDS | _NOT_OBSERVED_IDS == (
        set(range(1100, 1142)) | set(range(5978, 5985)) | set(range(6008, 6021))
    )


def test_maturity_rows_map_exact_new_items_and_retire_old_candidates(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    maturity = [
        item
        for item in result.source_dispositions
        if item.row_id
        in {
            "page-0044:paper_issuance:row-0003",
            "page-0044:paper_issuance:row-0006",
            "page-0044:paper_issuance:row-0007",
        }
    ]

    assert [
        (
            item.row_id,
            item.mapped_assignments[0].report_norm_id,
            item.values,
        )
        for item in maturity
    ] == [
        ("page-0044:paper_issuance:row-0003", 6010, (24_009_801, 23_039_165)),
        ("page-0044:paper_issuance:row-0006", 6008, (85_267_048, 76_253_073)),
        ("page-0044:paper_issuance:row-0007", 6009, (79_970_220, 64_577_077)),
    ]
    assert all(
        item.status == TMPage44SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
        and not item.question_required
        and not item.candidate_report_norm_ids
        for item in maturity
    )
    by_id = {item.report_norm_id: item for item in result.schema_dispositions}
    assert all(
        by_id[schema_id].status == TMPage44SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
        for schema_id in {1102, 1103, 1104, 1110, 1111}
    )


def test_equity_grid_preserves_all_four_printed_axes_and_existing_alias_binding(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    equity = [item for item in result.source_dispositions if item.table_key == "EQUITY_MOVEMENT"]
    structural = equity[0]

    assert [(x.cell_index, x.report_norm_id) for x in structural.mapped_assignments] == [
        (None, 1128)
    ]
    row_assignments = {
        item.ordinal: [
            (x.cell_index, x.axis_role, x.report_norm_id, x.observation, x.value)
            for x in item.mapped_assignments
        ]
        for item in equity[2:]
    }
    for ordinal, schema_id in {
        3: 5984,
        4: 6011,
        5: 6012,
        6: 6013,
        7: 6014,
        8: 6015,
        9: 6016,
        11: 6018,
    }.items():
        assert [assignment[0] for assignment in row_assignments[ordinal]] == [0, 1, 2, 3]
        assert {assignment[2] for assignment in row_assignments[ordinal]} == {schema_id}
    assert row_assignments[10] == [
        (0, "BEGINNING_BALANCE", 6017, "VALUE", 32_577_391),
        (1, "INCREASE", 6017, "VALUE", 7_515_513),
        (2, "DECREASE", 6017, "VALUE", -31_846),
        (3, "ENDING_BALANCE", 6017, "VALUE", 40_061_058),
        (1, "INCREASE", 1131, "VALUE", 7_515_513),
    ]
    assert row_assignments[12] == [
        (0, "BEGINNING_BALANCE", 1129, "VALUE", 142_022_525),
        (1, "INCREASE", 6019, "VALUE", 7_810_203),
        (2, "DECREASE", 6020, "VALUE", -87_403),
        (3, "ENDING_BALANCE", 1141, "VALUE", 149_745_325),
    ]
    assert all(item.question_group_id is None and not item.question_required for item in equity)


def test_fourteen_checks_pass_and_eight_dash_equations_are_not_testable(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.accounting_check_count == 22
    assert result.accounting_pass_count == 14
    assert result.accounting_not_testable_count == 8
    assert result.accounting_fail_count == 0
    not_testable = [
        check
        for check in result.accounting_checks
        if check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO"
    ]
    assert len(not_testable) == 8
    assert all(check.expected_value is None and check.residual is None for check in not_testable)
    assert all(check.residual == 0 for check in result.accounting_checks if check.status == "PASS")
    assert result.dash_pixel_evidence_sha256 == (
        "f818530118fe2aead1739b005a273b73f4efecf9d2828282e1a3b4e6c8433c9b"
    )


def test_q052_narrative_facts_map_exact_native_values_and_capital_equation_only_validates(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    diagnostic = result.narrative_diagnostic

    assert result.question_group_ids == ()
    assert [
        (
            item.fact_id,
            item.value_index,
            item.report_norm_id,
            item.value,
            item.source_unit,
            item.canonical_unit,
            item.unit_multiplier,
            item.period_start,
            item.period_end,
            item.period_role,
            item.period_type,
        )
        for item in result.narrative_assignments
    ] == [
        (
            "CERTIFICATE_INTEREST_RATE_RANGE",
            0,
            5978,
            Decimal("4.40"),
            "PERCENT_PER_YEAR",
            "PERCENT_PER_YEAR",
            1,
            "2026-03-31",
            "2026-03-31",
            "REPORT_DATE",
            "SNAPSHOT",
        ),
        (
            "CERTIFICATE_INTEREST_RATE_RANGE",
            1,
            5979,
            Decimal("11.18"),
            "PERCENT_PER_YEAR",
            "PERCENT_PER_YEAR",
            1,
            "2026-03-31",
            "2026-03-31",
            "REPORT_DATE",
            "SNAPSHOT",
        ),
        (
            "BANK_BOND_INTEREST_RATE_RANGE",
            0,
            5980,
            Decimal("5.00"),
            "PERCENT_PER_YEAR",
            "PERCENT_PER_YEAR",
            1,
            "2026-03-31",
            "2026-03-31",
            "REPORT_DATE",
            "SNAPSHOT",
        ),
        (
            "BANK_BOND_INTEREST_RATE_RANGE",
            1,
            5981,
            Decimal("8.80"),
            "PERCENT_PER_YEAR",
            "PERCENT_PER_YEAR",
            1,
            "2026-03-31",
            "2026-03-31",
            "REPORT_DATE",
            "SNAPSHOT",
        ),
        (
            "ISSUED_SHARE_COUNT",
            0,
            5982,
            Decimal(8_054_999_909),
            "SHARE",
            "SHARE",
            1,
            "2026-03-31",
            "2026-03-31",
            "REPORT_DATE",
            "SNAPSHOT",
        ),
        (
            "PAR_VALUE",
            0,
            5983,
            Decimal(10_000),
            "VND_PER_SHARE",
            "VND_PER_SHARE",
            1,
            "2026-03-31",
            "2026-03-31",
            "REPORT_DATE",
            "SNAPSHOT",
        ),
        (
            "STATED_CHARTER_CAPITAL",
            0,
            5984,
            Decimal(80_549_999),
            "VND_MILLION",
            "VND",
            1_000_000,
            "2026-03-31",
            "2026-03-31",
            "REPORT_DATE",
            "SNAPSHOT",
        ),
    ]
    assert all(item.observation == "VALUE" for item in result.narrative_assignments)
    assert all(
        item.source_row_ids and item.source_line_indices for item in result.narrative_assignments
    )
    assert diagnostic.question_group_id == "Q052"
    assert diagnostic.share_count == 8_054_999_909
    assert diagnostic.par_value_vnd == 10_000
    assert diagnostic.implied_capital_vnd_million == Decimal("80549999.09")
    assert diagnostic.stated_capital_vnd_million == 80_549_999
    assert diagnostic.exact_residual_vnd_million == Decimal("-0.09")
    assert diagnostic.rounded_implied_capital_vnd_million == 80_549_999
    assert diagnostic.status == "PASS_ROUNDED_TO_NEAREST_MILLION"
    assert "validation only" in diagnostic.reason


def test_mapping_policy_forbids_values_history_review_dash_zero_and_equation_selection(
    project_root: Path,
) -> None:
    policy = load_tm_page44_mapping_policy(project_root / TM_PAGE44_POLICY_RELATIVE_PATH)

    assert set(policy.forbidden_mapping_inputs) == {
        "numeric_cell_text",
        "numeric_cell_value_as_item_selector",
        "numeric_value_magnitude",
        "historical_or_mongodb_values",
        "human_review_answers",
        "dash_as_zero",
        "accounting_equation_result_as_item_selector",
        "accounting_equation_result_as_extracted_value",
        "narrative_value_as_item_selector",
        "capital_equation_result_as_item_selector",
        "capital_equation_result_as_extracted_value",
    }
    assert [rule.report_norm_id for rule in policy.narrative_fact_mappings] == list(
        range(5978, 5985)
    )
