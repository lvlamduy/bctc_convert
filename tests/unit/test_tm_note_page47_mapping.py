from __future__ import annotations

from pathlib import Path

from bctc_ai.mapping.tm_note_page47_mapping import (
    TM_PAGE47_POLICY_RELATIVE_PATH,
    TMPage47SchemaStatus,
    TMPage47SourceStatus,
    load_tm_page47_mapping_policy,
    reconcile_tm_page47_items,
    validate_tm_page47_mapping_result,
)
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.tm_note_page47 import load_tm_page47_policy, parse_tm_page47

_OCR_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0047-ppocrv6-word-box.json")
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_MAPPED_IDS = {
    1175,
    1176,
    1179,
    1182,
    1185,
    1188,
    1189,
    1190,
    1191,
    1193,
    1194,
    1195,
    1196,
    1232,
    1234,
    5990,
    6026,
    6027,
    6028,
    6029,
    6030,
}
_AMBIGUOUS_IDS: set[int] = set()
_NOT_OBSERVED_IDS = {
    1177,
    1178,
    1180,
    1181,
    1183,
    1184,
    1186,
    1187,
    1192,
    1197,
    1218,
    1229,
    1230,
    1231,
    1233,
    1235,
    1236,
    1237,
    1238,
    1239,
    1240,
    1241,
    1242,
    1243,
    1244,
    1245,
    1246,
}


def _mapped(project_root: Path, tmp_path: Path):
    render = Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={47},
        )[0].path
    )
    parsed = parse_tm_page47(
        project_root / _OCR_FIXTURE,
        render,
        load_tm_page47_policy(project_root / "config/tables/tm-note-page47-v1.yaml"),
    )
    _workbooks, schema = load_all(project_root / "template", project_root)
    return reconcile_tm_page47_items(
        parsed,
        schema=schema,
        policy=load_tm_page47_mapping_policy(project_root / TM_PAGE47_POLICY_RELATIVE_PATH),
        source_pdf_path=project_root / _SOURCE_PDF,
    )


def test_page47_reconciles_48_item_scope_and_maps_twenty_one_items(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert validate_tm_page47_mapping_result(result) is result
    assert result.mapping_authority_scope.endswith("PDF_PAGE_47_FIXED_ROWS_ONLY")
    assert result.mapping_authority_granted
    assert result.schema_item_count == 1_714
    assert result.status_reconciled_schema_count == 48
    assert result.mapped_schema_count == 21
    assert result.ambiguous_schema_count == 0
    assert result.not_observed_schema_count == 27
    assert result.not_applicable_schema_count == 0
    assert result.unassessed_schema_count == 1_666
    assert result.fully_verified_schema_count == 0
    assert result.source_row_count == 28
    assert result.mapped_source_row_count == 21
    assert result.ambiguous_source_row_count == 0
    assert result.source_only_row_count == 7
    assert result.source_question_row_count == 0
    assert result.financial_slot_count == 42
    assert result.extracted_value_count == 41
    assert result.dash_count == 1
    assert result.mapped_value_count == 41


def test_exact_mapped_ambiguous_not_observed_and_unassessed_schema_sets(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in {item.value for item in TMPage47SchemaStatus}
    }

    assert by_status[TMPage47SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] == _MAPPED_IDS
    assert by_status[TMPage47SchemaStatus.AMBIGUOUS_MAPPING.value] == _AMBIGUOUS_IDS
    assert by_status[TMPage47SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] == _NOT_OBSERVED_IDS
    assert len(by_status[TMPage47SchemaStatus.UNASSESSED.value]) == 1_666
    assert 1142 in by_status[TMPage47SchemaStatus.UNASSESSED.value]
    assert 1247 in by_status[TMPage47SchemaStatus.UNASSESSED.value]


def test_five_schema_gap_rows_map_exact_new_items_with_periods_and_no_candidates(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    resolved = [
        item
        for item in result.source_dispositions
        if item.report_norm_id in {6026, 6027, 6028, 6029, 6030}
    ]

    assert [(item.report_norm_id, item.row_id, item.values) for item in resolved] == [
        (6026, "page-0047:net_fx:row-0003", (662_413, 983_504)),
        (6027, "page-0047:net_fx:row-0007", (-486_848, -221_138)),
        (6028, "page-0047:net_securities:row-0011", (None, 20_861)),
        (6030, "page-0047:net_other:row-0004", (252_019, 113_256)),
        (6029, "page-0047:net_other:row-0005", (1_090_478, 1_179_210)),
    ]
    assert all(item.period_roles == ("CURRENT", "COMPARATIVE") for item in resolved)
    assert all(
        item.status == TMPage47SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
        and not item.question_required
        and not item.candidate_report_norm_ids
        for item in resolved
    )


def test_combined_securities_net_maps_5990_from_printed_values_and_formula_only_validates(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    item = next(source for source in result.source_dispositions if source.report_norm_id == 5990)

    assert item.row_id == "page-0047:net_securities:row-0013"
    assert item.canonical_name == ("Lãi thuần từ chứng khoán kinh doanh, chứng khoán đầu tư")
    assert item.status == TMPage47SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
    assert item.observations == ("VALUE", "VALUE")
    assert item.values == (-250_457, 678_047)
    assert item.period_starts == ("2026-01-01", "2025-01-01")
    assert item.period_ends == ("2026-03-31", "2025-03-31")
    assert item.period_roles == ("CURRENT", "COMPARATIVE")
    assert item.unit == "VND"
    assert item.unit_multiplier == 1_000_000
    assert not item.question_required
    checks = [
        check
        for check in result.accounting_checks
        if check.check_id == "NET_SECURITIES_COMBINED_TOTAL"
    ]
    assert len(checks) == 2
    assert all(check.status == "PASS" and check.residual == 0 for check in checks)


def test_processed_debt_receipts_map_to_recovery_and_narrow_disposition_is_not_observed(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    item = next(source for source in result.source_dispositions if source.report_norm_id == 1234)

    assert item.row_id == "page-0047:net_other:row-0002"
    assert item.visible_label == "Thu tù các khon n đã x lý"
    assert item.visible_label_similarity is not None and item.visible_label_similarity >= 0.78
    assert item.canonical_name == "Thu hồi nợ xấu,nợ đã xử lý, nợ đã xóa sổ trước đây"
    assert item.status == TMPage47SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
    assert item.observations == ("VALUE", "VALUE")
    assert item.values == (733_893, 1_003_397)
    assert item.period_roles == ("CURRENT", "COMPARATIVE")
    assert item.period_starts == ("2026-01-01", "2025-01-01")
    assert item.period_ends == ("2026-03-31", "2025-03-31")
    assert not item.question_required
    assert not item.candidate_report_norm_ids

    disposition = next(
        schema_item
        for schema_item in result.schema_dispositions
        if schema_item.report_norm_id == 1230
    )
    assert disposition.status == TMPage47SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
    assert disposition.canonical_name == "Nợ xấu đã được xử lý"
    assert not disposition.source_row_ids


def test_6028_mixed_dash_value_maps_with_pixel_evidence_and_not_zero(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    item = next(item for item in result.source_dispositions if item.report_norm_id == 6028)

    assert item.status == TMPage47SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
    assert item.observations == ("DASH", "VALUE")
    assert item.values == (None, 20_861)
    assert item.visual_cell_evidence[0] is not None
    assert item.visual_cell_evidence[0].component_box == (1851, 2022, 1863, 2026)
    assert item.visual_cell_evidence[1] is None
    assert not item.question_required
    assert not item.candidate_report_norm_ids
    assert result.dash_pixel_evidence_sha256 == (
        "87f9eb6dcaa1b9d05baf04f9203273863a34e33b40c980e7c9d260a13a72eab5"
    )


def test_thirteen_checks_pass_and_mixed_dash_equation_is_not_testable(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.accounting_check_count == 14
    assert result.accounting_pass_count == 13
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
    assert "cannot be coerced" in not_testable[0].reason


def test_mapping_policy_forbids_values_history_review_dash_zero_and_equation_selection(
    project_root: Path,
) -> None:
    policy = load_tm_page47_mapping_policy(project_root / TM_PAGE47_POLICY_RELATIVE_PATH)

    assert set(policy.scoped_schema_ids) == {
        *range(1175, 1198),
        5990,
        *range(6026, 6031),
        1218,
        *range(1229, 1247),
    }
    assert set(policy.forbidden_mapping_inputs) == {
        "numeric_cell_text",
        "numeric_cell_value_as_item_selector",
        "numeric_value_magnitude",
        "historical_or_mongodb_values",
        "human_review_answers",
        "dash_as_zero",
        "accounting_equation_result_as_item_selector",
        "accounting_equation_result_as_extracted_value",
    }
