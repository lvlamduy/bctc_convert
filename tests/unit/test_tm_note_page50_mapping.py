from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from bctc_ai.mapping.tm_note_page50_mapping import (
    TM_PAGE50_POLICY_RELATIVE_PATH,
    TMPage50SchemaStatus,
    TMPage50SourceStatus,
    load_tm_page50_mapping_policy,
    reconcile_tm_page50_items,
    validate_tm_page50_mapping_result,
)
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.tm_note_page50 import load_tm_page50_policy, parse_tm_page50

_OCR_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0050-ppocrv6-word-box.json")
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_TAX_IDS = set(range(5723, 5738))
_MAPPED_IDS = {1248, 1249, 1250, 1253} | _TAX_IDS
_NOT_OBSERVED_IDS = {1247, 1251, 1252, 1254}
_TAX_ROW_IDS = [
    *(("TAX_EXPENSE", ordinal, 5721 + ordinal) for ordinal in range(2, 7)),
    ("TAX_RECONCILIATION", 2, 5728),
    *(("TAX_RECONCILIATION", ordinal, 5725 + ordinal) for ordinal in range(4, 13)),
]
_TAX_VALUES = {
    5723: (Decimal(1_929_120), Decimal(1_708_859)),
    5724: (Decimal(1_929_120), Decimal(1_708_859)),
    5725: (Decimal(-3_454), Decimal(2_587)),
    5726: (Decimal(-3_454), Decimal(2_587)),
    5727: (Decimal(1_925_666), Decimal(1_711_446)),
    5728: (Decimal(9_628_386), Decimal(8_386_325)),
    5729: (Decimal(-747_622), Decimal(-706_432)),
    5730: (Decimal(2_665), Decimal(11_536)),
    5731: (Decimal(8_883_429), Decimal(7_691_429)),
    5732: (Decimal(1_776_686), Decimal(1_538_286)),
    5733: (Decimal(-4_257), Decimal(14_533)),
    5734: (None, Decimal(1_854)),
    5735: (Decimal(156_691), Decimal(154_186)),
    5736: (Decimal(-3_454), Decimal(2_587)),
    5737: (Decimal(1_925_666), Decimal(1_711_446)),
}


def _mapped(project_root: Path, tmp_path: Path):
    render = Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={50},
        )[0].path
    )
    parsed = parse_tm_page50(
        project_root / _OCR_FIXTURE,
        render,
        load_tm_page50_policy(project_root / "config/tables/tm-note-page50-v1.yaml"),
    )
    _workbooks, schema = load_all(project_root / "template", project_root)
    return reconcile_tm_page50_items(
        parsed,
        schema=schema,
        policy=load_tm_page50_mapping_policy(project_root / TM_PAGE50_POLICY_RELATIVE_PATH),
        source_pdf_path=project_root / _SOURCE_PDF,
    )


def test_page50_reconciles_23_item_scope_and_maps_all_19_visible_items(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert validate_tm_page50_mapping_result(result) is result
    assert result.status == "SCOPED_PAGE50_TAX_AND_CASH_MAPPING_WITH_COMPLETE_ITEM_COVERAGE"
    assert result.schema_item_count == 1_705
    assert result.status_reconciled_schema_count == 23
    assert result.mapped_schema_count == 19
    assert result.not_observed_schema_count == 4
    assert result.ambiguous_schema_count == 0
    assert result.unassessed_schema_count == 1_682
    assert result.source_row_count == 23
    assert result.mapped_source_row_count == 19
    assert result.source_only_row_count == 4
    assert result.source_only_schema_gap_count == 0
    assert result.source_question_row_count == 0
    assert result.financial_slot_count == 38
    assert result.extracted_value_count == 37
    assert result.dash_count == 1
    assert result.mapped_value_count == 37
    assert result.narrative_record_count == 3
    assert result.narrative_quantity_count == 1


def test_exact_schema_partition_is_disjoint_from_pages47_to49(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in {item.value for item in TMPage50SchemaStatus}
    }

    assert by_status[TMPage50SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] == _MAPPED_IDS
    assert by_status[TMPage50SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] == _NOT_OBSERVED_IDS
    assert len(by_status[TMPage50SchemaStatus.UNASSESSED.value]) == 1_682
    assert not ({*range(1175, 1247), *range(1269, 1280)} & (_MAPPED_IDS | _NOT_OBSERVED_IDS))


def test_cash_values_periods_unit_and_unlabeled_total_map_exactly(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    by_id = {
        item.report_norm_id: item
        for item in result.source_dispositions
        if item.report_norm_id is not None
    }

    assert by_id[1249].values == (Decimal(5_741_287), Decimal(4_965_786))
    assert by_id[1250].values == (Decimal(15_106_404), Decimal(68_475_175))
    assert by_id[1253].values == (Decimal(149_138_239), Decimal(165_819_028))
    assert by_id[1248].values == (Decimal(169_985_930), Decimal(239_259_989))
    assert by_id[1248].visible_label == ""
    assert by_id[1248].period_starts == ("2026-03-31", "2025-12-31")
    assert by_id[1248].period_ends == ("2026-03-31", "2025-12-31")
    assert by_id[1248].period_roles == ("CURRENT", "COMPARATIVE")
    assert {item.unit for item in by_id.values()} == {"VND"}
    assert {item.unit_multiplier for item in by_id.values()} == {1_000_000}
    assert all(
        item.status == TMPage50SourceStatus.MAPPED_AUTOMATIC_SCOPED.value for item in by_id.values()
    )


def test_fifteen_tax_rows_map_exact_ids_values_periods_and_dash_status(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    tax_rows = [item for item in result.source_dispositions if item.report_norm_id in _TAX_IDS]

    assert len(tax_rows) == 15
    assert [(item.table_key, item.ordinal, item.report_norm_id) for item in tax_rows] == (
        _TAX_ROW_IDS
    )
    assert {item.report_norm_id: item.values for item in tax_rows} == _TAX_VALUES
    assert all(
        item.status == TMPage50SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
        and not item.question_required
        and item.period_starts == ("2026-01-01", "2025-01-01")
        and item.period_ends == ("2026-03-31", "2025-03-31")
        and item.period_roles == ("CURRENT", "COMPARATIVE")
        and item.unit == "VND"
        and item.unit_multiplier == 1_000_000
        for item in tax_rows
    )
    dash = next(item for item in tax_rows if item.report_norm_id == 5734)
    assert dash.observations == ("DASH", "VALUE")
    assert dash.values == (None, Decimal(1_854))
    assert dash.visual_cell_evidence[0] is not None
    assert dash.visual_cell_evidence[1] is None

    source_only = [
        (item.table_key, item.ordinal)
        for item in result.source_dispositions
        if item.status == TMPage50SourceStatus.SOURCE_ONLY_VALIDATION.value
    ]
    assert source_only == [
        ("TAX_EXPENSE", 1),
        ("TAX_RECONCILIATION", 1),
        ("TAX_RECONCILIATION", 3),
        ("CASH_EQUIVALENTS", 1),
    ]


def test_tax_schema_order_parents_levels_and_formula_children_are_exact(project_root: Path) -> None:
    _workbooks, schema = load_all(project_root / "template", project_root)
    _registry, hierarchy = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml",
        project_root,
        schema,
    )
    apply_hierarchy_reference(schema, hierarchy)
    tm = sorted(
        (item for item in schema if item.statement_type == "TM"),
        key=lambda item: item.display_order,
    )
    ordered_ids = [item.schema_id for item in tm]
    insertion = ordered_ids.index(1246)
    assert ordered_ids[insertion : insertion + 17] == [1246, *range(5723, 5738), 1247]

    by_id = {item.schema_id: item for item in tm}
    expected = {
        5723: (5727, 2, (5724,)),
        5724: (5723, 3, ()),
        5725: (5727, 2, (5726,)),
        5726: (5725, 3, ()),
        5727: (1142, 1, (5723, 5725)),
        5728: (5731, 2, ()),
        5729: (5731, 2, ()),
        5730: (5731, 2, ()),
        5731: (1142, 1, (5728, 5729, 5730)),
        5732: (5737, 2, ()),
        5733: (5737, 2, ()),
        5734: (5737, 2, ()),
        5735: (5737, 2, ()),
        5736: (5737, 2, ()),
        5737: (1142, 1, (5732, 5733, 5734, 5735, 5736)),
    }
    assert {
        schema_id: (
            by_id[schema_id].parent_id,
            by_id[schema_id].hierarchy_level,
            tuple(by_id[schema_id].children),
        )
        for schema_id in _TAX_IDS
    } == expected
    assert {5727, 5731, 5737} <= set(by_id[1142].children)


def test_ten_accounting_checks_pass_or_preserve_dash_as_not_testable(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.validation_check_count == 10
    assert result.validation_pass_count == 9
    assert result.validation_not_testable_count == 1
    assert all(check.residual == 0 for check in result.validation_checks if check.status == "PASS")
    not_testable = [
        check
        for check in result.validation_checks
        if check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO"
    ]
    assert len(not_testable) == 1
    assert not_testable[0].check_id == "TAX_RECONCILIATION_SUM_CURRENT"
    assert not_testable[0].expected_value is None
    assert not_testable[0].observed_value == Decimal(1_925_666)
    assert not_testable[0].residual is None

    by_id = {check.check_id: check for check in result.validation_checks}
    assert (
        by_id["TAX_EXPENSE_SUM_CURRENT"].expected_value,
        by_id["TAX_EXPENSE_SUM_CURRENT"].observed_value,
    ) == (Decimal(1_925_666), Decimal(1_925_666))
    assert (
        by_id["ESTIMATED_TAXABLE_INCOME_CURRENT"].expected_value,
        by_id["ESTIMATED_TAXABLE_INCOME_CURRENT"].observed_value,
    ) == (Decimal(8_883_429), Decimal(8_883_429))
    assert (
        by_id["TAX_RECONCILIATION_SUM_COMPARATIVE"].status,
        by_id["TAX_RECONCILIATION_SUM_COMPARATIVE"].expected_value,
        by_id["TAX_RECONCILIATION_SUM_COMPARATIVE"].observed_value,
        by_id["TAX_RECONCILIATION_SUM_COMPARATIVE"].residual,
    ) == ("PASS", Decimal(1_711_446), Decimal(1_711_446), Decimal(0))


def test_mapping_policy_pins_tax_ids_and_forbids_non_scoped_forced_mapping(
    project_root: Path,
) -> None:
    policy = load_tm_page50_mapping_policy(project_root / TM_PAGE50_POLICY_RELATIVE_PATH)

    assert set(policy.scoped_schema_ids) == set(range(1247, 1255)) | _TAX_IDS
    assert set(policy.not_observed_schema_ids) == _NOT_OBSERVED_IDS
    assert {
        (rule.table_key, rule.ordinal): rule.report_norm_id
        for rule in policy.rows
        if rule.report_norm_id in _TAX_IDS
    } == {(table_key, ordinal): schema_id for table_key, ordinal, schema_id in _TAX_ROW_IDS}
    assert {
        "narrative_tax_rate_as_schema_value",
        "tax_row_as_preexisting_non_page50_schema_id",
        "schema_id_outside_page50_scope",
        "dash_as_zero",
        "human_review_answers",
    } <= set(policy.forbidden_mapping_inputs)
    assert not any(rule.question_required for rule in policy.rows)
