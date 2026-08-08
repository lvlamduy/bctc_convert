from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bctc_ai.core.contracts import BoundingBox
from bctc_ai.mapping.tm_note_mapping import (
    TM_PAGE30_AMBIGUOUS_IDS,
    TM_PAGE30_FIXED_IDS,
    TM_PAGE30_POLICY_RELATIVE_PATH,
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
    (),
    (),
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
    (583, 590),
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


def test_real_page30_deepseek_reconciles_full_schema_with_scoped_mapping_authority(
    project_root: Path,
) -> None:
    result = _mapped(project_root)

    assert validate_tm_page30_mapping_result(result) is result
    assert result.status == "SCOPED_FIXED_MAPPING_WITH_OPEN_AMBIGUITY"
    assert result.mapping_authority_scope.endswith("PDF_PAGE_30_FIXED_ROWS_ONLY")
    assert result.mapping_authority_granted
    assert result.automatic_fixed_selection_allowed
    assert not result.complete_page_mapping_resolved
    assert result.independent_semantic_stream_count == 2
    assert result.minimum_independent_semantic_streams == 2
    assert result.independent_reader_status == "COMPLETE"
    assert result.independent_reader_blocker is None
    assert result.schema_item_count == 1_385
    assert result.assessed_schema_count == 21
    assert result.mapped_schema_count == 19
    assert result.candidate_linked_schema_count == 0
    assert result.ambiguous_schema_count == 2
    assert result.unassessed_schema_count == 1_364
    assert result.fully_verified_schema_count == 0
    assert result.source_row_count == 22
    assert result.mapped_source_row_count == 19
    assert result.candidate_linked_source_row_count == 0
    assert result.ambiguous_source_row_count == 1
    assert result.source_only_row_count == 2
    assert result.structural_blank_source_row_count == 2
    assert result.independent_label_sha256 is not None
    assert result.independent_evidence_sha256 == (
        "6182e4634a80371ba560019b85ae67d706608ff48872f689e2645a5b03487c06"
    )


def test_exact_ordered_row_candidates_names_and_structural_blanks(project_root: Path) -> None:
    result = _mapped(project_root)

    assert (
        tuple(item.candidate_report_norm_ids for item in result.source_dispositions)
        == _EXPECTED_SOURCE_CANDIDATES
    )
    assert tuple(item.status for item in result.source_dispositions) == (
        *([TMSourceMappingStatus.MAPPED_AUTOMATIC_SCOPED.value] * 7),
        TMSourceMappingStatus.SOURCE_ONLY_PDF_ROW.value,
        TMSourceMappingStatus.SOURCE_ONLY_PDF_ROW.value,
        *([TMSourceMappingStatus.MAPPED_AUTOMATIC_SCOPED.value] * 11),
        TMSourceMappingStatus.AMBIGUOUS_MAPPING.value,
        TMSourceMappingStatus.MAPPED_AUTOMATIC_SCOPED.value,
    )
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
    ambiguous = result.source_dispositions[20]
    assert ambiguous.visible_label == "D phòng ri ro"
    assert ambiguous.candidate_report_norm_ids == (583, 590)
    assert ambiguous.candidate_canonical_names == (
        "- Dự phòng rủi ro tiền gửi tại các TCTD khác",
        "+ Dự phòng cho vay các tổ chức tín dụng khác(*)",
    )
    assert {
        item.row_id
        for item in result.source_dispositions
        if item.status == TMSourceMappingStatus.SOURCE_ONLY_PDF_ROW.value
    } == {
        "page-0030:note-2:row-0004",
        "page-0030:note-2:row-0005",
    }


def test_schema_dispositions_are_19_fixed_2_ambiguous_and_1364_unassessed(
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
    assert by_status[TMSchemaMappingStatus.AMBIGUOUS_MAPPING.value] == set(TM_PAGE30_AMBIGUOUS_IDS)
    assert len(by_status[TMSchemaMappingStatus.UNASSESSED.value]) == 1_364
    schema_by_id = {item.report_norm_id: item for item in result.schema_dispositions}
    assert schema_by_id[562].source_row_ids == ("page-0030:note-1:row-0001",)
    assert schema_by_id[583].source_row_ids == ("page-0030:note-3:row-0011",)
    assert schema_by_id[590].source_row_ids == ("page-0030:note-3:row-0011",)
    assert schema_by_id[1944].status == TMSchemaMappingStatus.UNASSESSED.value


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


def test_real_deepseek_evidence_can_authorize_only_19_fixed_rows(
    project_root: Path,
) -> None:
    parsed = _parsed(project_root)
    policy = _policy(project_root)
    evidence = load_tm_page30_deepseek_evidence(project_root / _DEEPSEEK_FIXTURE)
    result = reconcile_tm_page30_items(
        parsed,
        schema=_schema(project_root),
        policy=policy,
        source_pdf_path=project_root / _SOURCE_PDF,
        independent_evidence=evidence,
    )

    assert result.status == "SCOPED_FIXED_MAPPING_WITH_OPEN_AMBIGUITY"
    assert result.mapping_authority_granted
    assert result.automatic_fixed_selection_allowed
    assert not result.complete_page_mapping_resolved
    assert result.independent_semantic_stream_count == 2
    assert result.mapped_schema_count == result.mapped_source_row_count == 19
    assert result.candidate_linked_schema_count == result.candidate_linked_source_row_count == 0
    assert result.ambiguous_schema_count == 2
    assert result.ambiguous_source_row_count == 1
    assert result.source_only_row_count == 2
    assert result.independent_label_sha256 is not None
    assert result.independent_evidence_sha256 == evidence.evidence_sha256
    assert result.mapping_inputs[-1] == "DEEPSEEK_OCR_2_REFERENCE_BLIND_LABELS"


@dataclass(frozen=True)
class _LabelOnlyReader:
    label: str

    @property
    def cells(self):
        raise AssertionError("TM mapping must never read numeric cells")


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


def test_policy_explicitly_forbids_value_history_review_and_parser_mapping_inputs(
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
