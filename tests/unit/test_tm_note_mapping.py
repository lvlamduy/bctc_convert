from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from pathlib import Path

import pytest

from bctc_ai.core.contracts import BoundingBox
from bctc_ai.mapping.tm_note_mapping import (
    TM_PAGE30_ACCOUNTING_CHECK_COUNT,
    TM_PAGE30_AGGREGATE_TARGET_ID,
    TM_PAGE30_AMBIGUOUS_IDS,
    TM_PAGE30_FIXED_IDS,
    TM_PAGE30_MAPPED_VALUE_COUNT,
    TM_PAGE30_NOT_OBSERVED_IDS,
    TM_PAGE30_POLICY_RELATIVE_PATH,
    TM_PAGE30_PROVISION_TOTAL_ID,
    TMNoteMappingError,
    TMSchemaMappingStatus,
    TMSourceMappingStatus,
    adapt_tm_page30_rows,
    load_tm_page30_deepseek_evidence,
    load_tm_page30_mapping_policy,
    reconcile_tm_page30_items,
    validate_tm_page30_mapping_result,
)
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.tm_note_word_box import (
    load_tm_note_word_box_policy,
    parse_tm_note_word_box_page,
)

_OCR_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0030-ppocrv6-word-box.json")
_DEEPSEEK_FIXTURE = Path("tests/golden/tm/mbb-q1-2026-page-0030-deepseek-labels.json")
_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_EXPECTED_SOURCE_CANDIDATES = (
    (562,),
    (563,),
    (565,),
    (561,),
    (570,),
    (571,),
    (572,),
    (574,),
    (574,),
    (569,),
    (576,),
    (577,),
    (578,),
    (579,),
    (580,),
    (581,),
    (582,),
    (585,),
    (586,),
    (588,),
    (5718,),
    (575,),
)


def _parsed(project_root: Path):
    return parse_tm_note_word_box_page(
        project_root / _OCR_FIXTURE,
        load_tm_note_word_box_policy(project_root / "config/tables/tm-note-word-box-v1.yaml"),
        page_tag="page-0030",
    )


def _schema(project_root: Path):
    _workbooks, schema = load_all(project_root / "template", project_root)
    return schema


def _policy(project_root: Path):
    return load_tm_page30_mapping_policy(project_root / TM_PAGE30_POLICY_RELATIVE_PATH)


def _mapped(project_root: Path):
    return reconcile_tm_page30_items(
        _parsed(project_root),
        schema=_schema(project_root),
        policy=_policy(project_root),
        source_pdf_path=project_root / _SOURCE_PDF,
        independent_evidence=load_tm_page30_deepseek_evidence(project_root / _DEEPSEEK_FIXTURE),
    )


def test_real_page30_reconciles_1710_schema_and_all_22_source_rows(
    project_root: Path,
) -> None:
    result = _mapped(project_root)

    assert validate_tm_page30_mapping_result(result) is result
    assert (
        result.status == "SCOPED_PAGE30_MAPPING_RESOLVED_WITH_AGGREGATION_AND_ACCOUNTING_VALIDATION"
    )
    assert result.mapping_authority_scope.endswith(
        "PDF_PAGE_30_FIXED_AND_DECLARED_AGGREGATE_ROWS_ONLY"
    )
    assert result.mapping_authority_granted
    assert result.automatic_fixed_selection_allowed
    assert result.complete_page_mapping_resolved
    assert result.independent_semantic_stream_count == 2
    assert result.minimum_independent_semantic_streams == 2
    assert result.independent_reader_status == "COMPLETE"
    assert result.independent_reader_blocker is None
    assert result.schema_item_count == 1_710
    assert result.assessed_schema_count == 23
    assert result.mapped_schema_count == 21
    assert result.candidate_linked_schema_count == 0
    assert TM_PAGE30_AMBIGUOUS_IDS == ()
    assert result.not_observed_schema_count == 2
    assert result.ambiguous_schema_count == 0
    assert result.unassessed_schema_count == 1_687
    assert result.fully_verified_schema_count == 0
    assert result.source_row_count == result.mapped_source_row_count == 22
    assert result.candidate_linked_source_row_count == 0
    assert result.ambiguous_source_row_count == 0
    assert result.source_only_row_count == 0
    assert result.structural_blank_source_row_count == 2
    assert result.mapped_value_count == 38
    assert result.accounting_check_count == result.accounting_pass_count == 14
    assert result.schema_projection_sha256 == (
        "b9bd1d743b57ba6e5490a051c309ecff987e320178324c4fc6e2abc6f896ee9c"
    )
    assert result.independent_evidence_sha256 == (
        "6182e4634a80371ba560019b85ae67d706608ff48872f689e2645a5b03487c06"
    )


def test_exact_ordered_row_targets_names_and_structural_blanks(project_root: Path) -> None:
    result = _mapped(project_root)

    assert (
        tuple(item.candidate_report_norm_ids for item in result.source_dispositions)
        == _EXPECTED_SOURCE_CANDIDATES
    )
    assert {item.status for item in result.source_dispositions} == {
        TMSourceMappingStatus.MAPPED_AUTOMATIC_SCOPED.value
    }
    structural = tuple(
        item
        for item in result.source_dispositions
        if item.value_presence == "OBSERVED_STRUCTURAL_ITEM_WITH_BLANK_CELLS"
    )
    assert [(item.row_id, item.candidate_report_norm_ids) for item in structural] == [
        ("page-0030:note-3:row-0002", (577,)),
        ("page-0030:note-3:row-0005", (580,)),
    ]
    assert [item.candidate_canonical_names for item in structural] == [
        ("-Tiền gửi không kỳ hạn",),
        ("- Tiền gửi có kỳ hạn",),
    ]
    assert result.source_dispositions[7].candidate_canonical_names == ("Tiền gửi khác",)
    assert result.source_dispositions[8].candidate_canonical_names == ("Tiền gửi khác",)
    provision = result.source_dispositions[20]
    assert provision.visible_label == "D phòng ri ro"
    assert provision.candidate_report_norm_ids == (5718,)
    assert provision.candidate_canonical_names == (
        "Tổng dự phòng rủi ro tiền gửi và cho vay các tổ chức tín dụng khác",
    )


def test_schema_dispositions_are_21_mapped_2_not_observed_1682_unassessed(
    project_root: Path,
) -> None:
    result = _mapped(project_root)
    by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in {item.value for item in TMSchemaMappingStatus}
    }

    assert by_status[TMSchemaMappingStatus.MAPPED_AUTOMATIC_SCOPED.value] == set(
        TM_PAGE30_FIXED_IDS
    )
    assert by_status[TMSchemaMappingStatus.CANDIDATE_MAPPING_NOT_AUTOMATIC.value] == set()
    assert by_status[TMSchemaMappingStatus.NOT_OBSERVED_IN_THIS_PDF.value] == set(
        TM_PAGE30_NOT_OBSERVED_IDS
    )
    assert by_status[TMSchemaMappingStatus.AMBIGUOUS_MAPPING.value] == set()
    assert len(by_status[TMSchemaMappingStatus.UNASSESSED.value]) == 1_687
    schema_by_id = {item.report_norm_id: item for item in result.schema_dispositions}
    assert schema_by_id[574].source_row_ids == (
        "page-0030:note-2:row-0004",
        "page-0030:note-2:row-0005",
    )
    assert schema_by_id[5718].source_row_ids == ("page-0030:note-3:row-0011",)
    assert schema_by_id[583].source_row_ids == ()
    assert schema_by_id[590].source_row_ids == ()
    assert schema_by_id[1944].status == TMSchemaMappingStatus.UNASSESSED.value


def test_mapped_values_bind_period_unit_and_preserve_aggregate_provenance(
    project_root: Path,
) -> None:
    result = _mapped(project_root)
    by_key = {(item.report_norm_id, item.axis_id): item for item in result.mapped_values}

    assert len(by_key) == result.mapped_value_count == TM_PAGE30_MAPPED_VALUE_COUNT
    assert {item.report_norm_id for item in result.mapped_values} == set(TM_PAGE30_FIXED_IDS) - {
        577,
        580,
    }
    current = by_key[(TM_PAGE30_AGGREGATE_TARGET_ID, "value-1")]
    comparative = by_key[(TM_PAGE30_AGGREGATE_TARGET_ID, "value-2")]
    assert (current.reported_value, comparative.reported_value) == ("2223753", "2258533")
    assert current.canonical_value_vnd == 2_223_753_000_000
    assert comparative.canonical_value_vnd == 2_258_533_000_000
    assert current.aggregation == comparative.aggregation == "SUM_SOURCE_ROWS"
    assert (
        current.source_row_ids
        == comparative.source_row_ids
        == (
            "page-0030:note-2:row-0004",
            "page-0030:note-2:row-0005",
        )
    )
    assert current.source_raw_values == ("797.376", "1.426.377")
    assert current.source_reported_values == ("797376", "1426377")
    assert comparative.source_raw_values == ("667.675", "1.590.858")
    assert comparative.source_reported_values == ("667675", "1590858")

    provision_current = by_key[(TM_PAGE30_PROVISION_TOTAL_ID, "value-1")]
    provision_comparative = by_key[(TM_PAGE30_PROVISION_TOTAL_ID, "value-2")]
    assert (provision_current.reported_value, provision_comparative.reported_value) == (
        "-10785",
        "-9096",
    )
    assert provision_current.source_raw_values == ("(10.785)",)
    assert provision_comparative.source_raw_values == ("(9.096)",)
    assert (
        provision_current.aggregation == provision_comparative.aggregation == ("DIRECT_SOURCE_ROW")
    )
    assert {
        (
            item.axis_id,
            item.current_or_comparative,
            item.period_start,
            item.period_end,
            item.period_type,
            item.canonical_unit,
            item.unit_multiplier,
        )
        for item in result.mapped_values
    } == {
        ("value-1", "CURRENT", "2026-03-31", "2026-03-31", "SNAPSHOT", "VND", 1_000_000),
        (
            "value-2",
            "COMPARATIVE",
            "2025-12-31",
            "2025-12-31",
            "SNAPSHOT",
            "VND",
            1_000_000,
        ),
    }


def test_aggregation_and_six_accounting_equations_pass_on_both_axes(
    project_root: Path,
) -> None:
    result = _mapped(project_root)
    checks = {(item.check_id, item.axis_id): item for item in result.accounting_checks}

    assert len(checks) == TM_PAGE30_ACCOUNTING_CHECK_COUNT
    assert {item.status for item in checks.values()} == {"PASS"}
    assert {Decimal(item.residual_reported_unit) for item in checks.values()} == {Decimal(0)}
    aggregate = checks[("OTHER_CENTRAL_BANK_DEPOSITS_AGGREGATION", "value-1")]
    assert aggregate.target_report_norm_id == 574
    assert aggregate.operand_report_norm_ids == ()
    assert aggregate.operand_source_row_ids == (
        "page-0030:note-2:row-0004",
        "page-0030:note-2:row-0005",
    )
    assert aggregate.operand_reported_values == ("797376", "1426377")
    net = checks[("INTERBANK_NET_TOTAL", "value-1")]
    assert net.target_report_norm_id == 575
    assert net.operand_report_norm_ids == (576, 585, 5718)
    assert net.operand_reported_values == ("149138239", "16170508", "-10785")


def test_post_selection_aggregate_value_drift_fails_closed(project_root: Path) -> None:
    parsed = _parsed(project_root)
    aggregate_component = parsed.rows[7]
    cells = aggregate_component.row.cells
    tampered_cell = replace(cells[0], value=Decimal(797_377))
    tampered_reader_row = replace(
        aggregate_component.row,
        cells=(tampered_cell, cells[1]),
    )
    tampered_source_row = replace(aggregate_component, row=tampered_reader_row)
    tampered_page = replace(
        parsed,
        rows=(*parsed.rows[:7], tampered_source_row, *parsed.rows[8:]),
    )

    with pytest.raises(TMNoteMappingError, match="ID 574 aggregate value drifted"):
        reconcile_tm_page30_items(
            tampered_page,
            schema=_schema(project_root),
            policy=_policy(project_root),
            source_pdf_path=project_root / _SOURCE_PDF,
            independent_evidence=load_tm_page30_deepseek_evidence(project_root / _DEEPSEEK_FIXTURE),
        )


def test_pdf_pixels_verify_all_label_boxes_and_text_layer_is_truthfully_absent(
    project_root: Path,
) -> None:
    geometry = _mapped(project_root).geometry_evidence

    assert geometry.source_pdf_sha256 == (
        "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
    )
    assert geometry.source_render_sha256 == (
        "e8cea48c6d8f93771b4b5bd9026df7a8b3e592ff7e403e036ed33eda913a092b"
    )
    assert (geometry.rendered_width, geometry.rendered_height) == (2481, 3508)
    assert geometry.embedded_image_count == 2
    assert geometry.pdf_text_token_count == 0
    assert not geometry.pdf_text_available
    assert geometry.label_row_count == geometry.verified_label_row_count == 22
    assert geometry.minimum_observed_ink_fraction == 0.22344007
    assert geometry.geometry_sha256 == (
        "b1129402bc494f11aec11ceff1ec0475e0228b51a1813b606182fee7d892b558"
    )
    assert geometry.semantic_crop_attempt_count == 26
    assert geometry.verified_semantic_crop_attempt_count == 26
    assert geometry.semantic_crop_geometry_sha256 is not None


def test_missing_independent_reader_retains_all_links_as_candidates_without_value_leak(
    project_root: Path,
) -> None:
    result = reconcile_tm_page30_items(
        _parsed(project_root),
        schema=_schema(project_root),
        policy=_policy(project_root),
        source_pdf_path=project_root / _SOURCE_PDF,
        independent_reader_blocker="pinned reader unavailable",
    )

    assert result.status == "CANDIDATE_RECONCILIATION_SECOND_READER_BLOCKED"
    assert not result.mapping_authority_granted
    assert not result.automatic_fixed_selection_allowed
    assert not result.complete_page_mapping_resolved
    assert result.mapped_schema_count == result.mapped_source_row_count == 0
    assert result.candidate_linked_schema_count == 21
    assert result.candidate_linked_source_row_count == 22
    assert result.not_observed_schema_count == 2
    assert result.mapped_value_count == 0
    assert result.mapped_values == ()
    assert result.accounting_check_count == result.accounting_pass_count == 14


@dataclass(frozen=True)
class _LabelOnlyReader:
    label: str

    @property
    def cells(self):
        raise AssertionError("TM item selection must never read numeric cells")


@dataclass(frozen=True)
class _ParserRow:
    row_id: str
    note_number: str
    ordinal: int
    row_kind: str
    source_role: str
    label_bbox: BoundingBox
    row: _LabelOnlyReader


def test_adapter_reads_label_hierarchy_geometry_but_never_numeric_cells(
    project_root: Path,
) -> None:
    parsed = _parsed(project_root)
    rows = tuple(
        _ParserRow(
            row_id=row.row_id,
            note_number=row.note_number,
            ordinal=row.ordinal,
            row_kind=str(row.row_kind),
            source_role=row.source_role,
            label_bbox=row.label_bbox,
            row=_LabelOnlyReader(row.row.label),
        )
        for row in parsed.rows
    )

    adapted = adapt_tm_page30_rows(rows)

    assert len(adapted) == 22
    assert [row.order for row in adapted] == list(range(22))
    assert [(row.note_number, row.ordinal) for row in adapted] == [
        (rule.note_number, rule.ordinal) for rule in _policy(project_root).rows
    ]


def test_policy_forbids_values_as_item_selectors_but_result_records_post_selection_checks(
    project_root: Path,
) -> None:
    assert set(_policy(project_root).forbidden_mapping_inputs) == {
        "numeric_cell_text",
        "numeric_cell_value",
        "numeric_value_magnitude",
        "accounting_equation_result",
        "period_or_unit_as_item_selector",
        "historical_or_mongodb_values",
        "human_review_answers",
        "parser_candidate_report_norm_ids",
    }
    assert {
        "SOURCE_NUMERIC_CELLS_FOR_POST_SELECTION_VALUE_BINDING_ONLY",
        "ACCOUNTING_EQUATIONS_AS_POST_MAPPING_VALIDATION_ONLY",
    } <= set(_mapped(project_root).mapping_inputs)
