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
    1170,
    1171,
    1172,
    1174,
    5985,
    5986,
    5987,
    5988,
    5989,
    6021,
    6022,
    6023,
    6024,
    6025,
}
_AMBIGUOUS_IDS: set[int] = set()
_NOT_OBSERVED_IDS = {
    1147,
    1155,
    1158,
    1159,
    1161,
    1162,
    1165,
    1168,
    1169,
    1173,
}


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


def test_page46_reconciles_universal_scope_and_maps_printed_children_plus_derived_parent(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert validate_tm_page46_mapping_result(result) is result
    assert result.mapping_authority_scope.endswith("PDF_PAGE_46_FIXED_ROWS_ONLY")
    assert result.mapping_authority_granted
    assert result.schema_item_count == 1_721
    assert result.status_reconciled_schema_count == 43
    assert result.mapped_schema_count == 33
    assert result.ambiguous_schema_count == 0
    assert result.not_observed_schema_count == 10
    assert result.not_applicable_schema_count == 0
    assert result.unassessed_schema_count == (
        result.schema_item_count - result.status_reconciled_schema_count
    )
    assert result.fully_verified_schema_count == 0
    assert result.source_row_count == 38
    assert result.mapped_source_row_count == 32
    assert result.ambiguous_source_row_count == 0
    assert result.source_only_row_count == 6
    assert result.source_question_row_count == 0
    assert result.financial_slot_count == 62
    assert result.extracted_value_count == 60
    assert result.dash_count == 2
    assert result.mapped_value_count == 60
    assert result.derived_assignment_count == 2


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
    assert len(by_status[TMPage46SchemaStatus.UNASSESSED.value]) == (result.unassessed_schema_count)
    assert 5718 in by_status[TMPage46SchemaStatus.UNASSESSED.value]


def test_five_schema_gaps_now_map_directly_with_values_periods_and_no_candidates(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    resolved = [
        item
        for item in result.source_dispositions
        if item.row_id
        in {
            "page-0046:net_service:row-0003",
            "page-0046:net_service:row-0007",
            "page-0046:net_service:row-0012",
            "page-0046:net_service:row-0015",
            "page-0046:net_service:row-0018",
        }
    ]

    assert [(item.report_norm_id, item.values) for item in resolved] == [
        (6021, (1_460_480, 755_554)),
        (6022, (38_898, 126_730)),
        (6023, (-675_848, -551_556)),
        (6024, (-539_743, -232_408)),
        (6025, (-59_748, -32_105)),
    ]
    assert all(item.period_roles == ("CURRENT", "COMPARATIVE") for item in resolved)
    assert all(
        item.status == TMPage46SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
        and not item.question_required
        and not item.candidate_report_norm_ids
        for item in resolved
    )


def test_1170_is_explicitly_derived_without_overwriting_printed_child_values(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)

    assert [
        (
            item.report_norm_id,
            item.component_report_norm_ids,
            item.component_values,
            item.value,
            item.period_role,
            item.mapping_basis,
        )
        for item in result.derived_assignments
    ] == [
        (
            1170,
            (6024, 6025),
            (-539_743, -59_748),
            -599_491,
            "CURRENT",
            "DERIVED_SUM_OF_EXPLICIT_PRINTED_CHILDREN_6024_6025",
        ),
        (
            1170,
            (6024, 6025),
            (-232_408, -32_105),
            -264_513,
            "COMPARATIVE",
            "DERIVED_SUM_OF_EXPLICIT_PRINTED_CHILDREN_6024_6025",
        ),
    ]
    children = {
        item.report_norm_id: item.values
        for item in result.source_dispositions
        if item.report_norm_id in {6024, 6025}
    }
    assert children == {
        6024: (-539_743, -232_408),
        6025: (-59_748, -32_105),
    }
    parent = next(item for item in result.schema_dispositions if item.report_norm_id == 1170)
    assert parent.status == TMPage46SchemaStatus.MAPPED_AUTOMATIC_SCOPED.value
    assert parent.source_row_ids == (
        "page-0046:net_service:row-0015",
        "page-0046:net_service:row-0018",
    )


def test_five_promoted_rows_preserve_printed_values_dash_periods_units_and_formula_validation(
    project_root: Path, tmp_path: Path
) -> None:
    result = _mapped(project_root, tmp_path)
    promoted = {
        item.report_norm_id: item
        for item in result.source_dispositions
        if item.report_norm_id in set(range(5985, 5990))
    }

    assert set(promoted) == set(range(5985, 5990))
    assert {
        report_norm_id: (item.row_id, item.observations, item.values)
        for report_norm_id, item in promoted.items()
    } == {
        5985: (
            "page-0046:net_interest:row-0017",
            ("VALUE", "VALUE"),
            (14_913_117, 11_692_184),
        ),
        5986: (
            "page-0046:net_service:row-0004",
            ("VALUE", "VALUE"),
            (148_427, 98_268),
        ),
        5987: ("page-0046:net_service:row-0014", ("DASH", "DASH"), (None, None)),
        5988: (
            "page-0046:net_service:row-0017",
            ("VALUE", "VALUE"),
            (-38_259, -59_707),
        ),
        5989: (
            "page-0046:net_service:row-0021",
            ("VALUE", "VALUE"),
            (1_708_744, 1_235_416),
        ),
    }
    assert all(
        item.status == TMPage46SourceStatus.MAPPED_AUTOMATIC_SCOPED.value
        and item.period_starts == ("2026-01-01", "2025-01-01")
        and item.period_ends == ("2026-03-31", "2025-03-31")
        and item.period_roles == ("CURRENT", "COMPARATIVE")
        and item.unit == "VND"
        and item.unit_multiplier == 1_000_000
        and not item.question_required
        for item in promoted.values()
    )
    assert all(evidence is not None for evidence in promoted[5987].visual_cell_evidence)
    formula_checks = [
        check
        for check in result.accounting_checks
        if check.check_id in {"NET_INTEREST_NET", "NET_SERVICE_NET"}
    ]
    assert len(formula_checks) == 4
    assert all(check.status == "PASS" and check.residual == 0 for check in formula_checks)


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
        "accounting_equation_result_as_extracted_value",
    }
    assert set(policy.additional_scoped_schema_ids) == {
        *range(5985, 5990),
        *range(6021, 6026),
    }
