from __future__ import annotations

from pathlib import Path

from bctc_ai.mapping.tm_note_page46_mapping import (
    TM_PAGE46_POLICY_RELATIVE_PATH,
    TMPage46SchemaStatus,
    TMPage46SourceStatus,
    load_tm_page46_mapping_policy,
    reconcile_tm_page46_items,
    validate_tm_page46_mapping_result,
)
from bctc_ai.rendering.pdf import render_pages
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.tm_note_page46 import load_tm_page46_policy, parse_tm_page46

_OCR_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0046-ppocrv6-word-box.json")
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_MAPPED_IDS = {
    1142,
    1143,
    1144,
    1145,
    1146,
    1148,
    1149,
    1150,
    1151,
    1152,
    1153,
    1154,
    1156,
    1157,
    1160,
    1163,
    1164,
    1166,
    1167,
    1171,
    1172,
    1174,
}
_AMBIGUOUS_IDS = {1158, 1159, 1162, 1168, 1169, 1170}
_NOT_OBSERVED_IDS = {1147, 1155, 1161, 1165, 1173}


def _mapped(project_root: Path, tmp_path: Path):
    render = Path(
        render_pages(
            project_root / _SOURCE_PDF,
            tmp_path / "render",
            dpi=300,
            page_numbers={46},
        )[0].path
    )
    parsed = parse_tm_page46(
        project_root / _OCR_FIXTURE,
        render,
        load_tm_page46_policy(project_root / "config/tables/tm-note-page46-v1.yaml"),
    )
    _workbooks, schema = load_all(project_root / "template", project_root)
    return reconcile_tm_page46_items(
        parsed,
        schema=schema,
        policy=load_tm_page46_mapping_policy(project_root / TM_PAGE46_POLICY_RELATIVE_PATH),
        source_pdf_path=project_root / _SOURCE_PDF,
    )


def test_page46_reconciles_exact_1142_1174_scope_and_maps_twenty_two_items(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert validate_tm_page46_mapping_result(result) is result
    assert result.mapping_authority_scope.endswith("PDF_PAGE_46_FIXED_ROWS_ONLY")
    assert result.mapping_authority_granted
    assert result.schema_item_count == 1_613
    assert result.status_reconciled_schema_count == 33
    assert result.mapped_schema_count == 22
    assert result.ambiguous_schema_count == 6
    assert result.not_observed_schema_count == 5
    assert result.not_applicable_schema_count == 0
    assert result.unassessed_schema_count == 1_580
    assert result.fully_verified_schema_count == 0
    assert result.source_row_count == 38
    assert result.mapped_source_row_count == 22
    assert result.ambiguous_source_row_count == 5
    assert result.source_only_row_count == 11
    assert result.source_question_row_count == 10
    assert result.financial_slot_count == 62
    assert result.extracted_value_count == 60
    assert result.dash_count == 2
    assert result.mapped_value_count == 42


def test_exact_mapped_ambiguous_not_observed_and_unassessed_schema_sets(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in {item.value for item in TMPage46SchemaStatus}
    }

    assert by_status[TMPage46SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value] == _MAPPED_IDS
    assert by_status[TMPage46SchemaStatus.AMBIGUOUS_MAPPING.value] == _AMBIGUOUS_IDS
    assert by_status[TMPage46SchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] == _NOT_OBSERVED_IDS
    assert len(by_status[TMPage46SchemaStatus.UNASSESSED.value]) == 1_580
    assert 5718 in by_status[TMPage46SchemaStatus.UNASSESSED.value]


def test_ten_open_source_rows_retain_values_periods_candidates_and_dash(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    questions = [item for item in result.source_dispositions if item.question_required]

    assert [item.row_id for item in questions] == [
        "page-0046:net_interest:row-0017",
        "page-0046:net_service:row-0003",
        "page-0046:net_service:row-0004",
        "page-0046:net_service:row-0007",
        "page-0046:net_service:row-0012",
        "page-0046:net_service:row-0014",
        "page-0046:net_service:row-0015",
        "page-0046:net_service:row-0017",
        "page-0046:net_service:row-0018",
        "page-0046:net_service:row-0021",
    ]
    assert questions[1].candidate_report_norm_ids == (1158, 1159)
    assert questions[4].candidate_report_norm_ids == (1168, 1169)
    assert questions[6].candidate_report_norm_ids == (1170,)
    assert questions[8].candidate_report_norm_ids == (1170,)
    assert questions[5].observations == ("DASH", "DASH")
    assert questions[5].values == (None, None)
    assert all(evidence is not None for evidence in questions[5].visual_cell_evidence)
    assert questions[0].values == (14_913_117, 11_692_184)
    assert questions[-1].values == (1_708_744, 1_235_416)
    assert all(item.period_roles == ("CURRENT", "COMPARATIVE") for item in questions)
    assert (
        sum(item.status == TMPage46SourceStatus.AMBIGUOUS_MAPPING.value for item in questions) == 5
    )


def test_brokerage_income_maps_to_generic_securities_service_with_exact_period_values(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    item = next(source for source in result.source_dispositions if source.report_norm_id == 1160)

    assert item.row_id == "page-0046:net_service:row-0008"
    assert item.visible_label == "Thu tù hot đng môi gii chng khoán"
    assert item.visible_label_similarity is not None and item.visible_label_similarity >= 0.78
    assert item.canonical_name == "Dịch vụ chứng khoán"
    assert item.status == TMPage46SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
    assert item.observations == ("VALUE", "VALUE")
    assert item.values == (241_339, 133_456)
    assert item.period_roles == ("CURRENT", "COMPARATIVE")
    assert item.period_starts == ("2026-01-01", "2025-01-01")
    assert item.period_ends == ("2026-03-31", "2025-03-31")
    assert not item.question_required
    assert not item.candidate_report_norm_ids


def test_accounting_checks_pass_without_coercing_consulting_dash_to_zero(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert result.accounting_check_count == 12
    assert result.accounting_pass_count == 10
    assert result.accounting_not_testable_count == 2
    assert all(check.residual == 0 for check in result.accounting_checks if check.status == "PASS")
    not_testable = [
        check
        for check in result.accounting_checks
        if check.status == "NOT_TESTABLE_DASH_IS_NOT_ZERO"
    ]
    assert len(not_testable) == 2
    assert all(
        check.expected_value is None
        and check.residual is None
        and "cannot be coerced" in check.reason
        for check in not_testable
    )
    assert result.dash_pixel_evidence_sha256 == (
        "41f34e9f81f693ed01603d8ff37bdc39357e7b678592329b1f67624634943d5f"
    )


def test_mapping_policy_forbids_values_history_review_dash_zero_and_equation_selection(
    project_root: Path,
) -> None:
    policy = load_tm_page46_mapping_policy(project_root / TM_PAGE46_POLICY_RELATIVE_PATH)

    assert set(policy.forbidden_mapping_inputs) == {
        "numeric_cell_text",
        "numeric_cell_value_as_item_selector",
        "numeric_value_magnitude",
        "historical_or_mongodb_values",
        "human_review_answers",
        "dash_as_zero",
        "accounting_equation_result_as_item_selector",
    }
