from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from bctc_ai.mapping.lctt import CashFlowMethod
from bctc_ai.mapping.lctt_item_mapping import (
    LCTT_POLICY_RELATIVE_PATH,
    LCTT_TRAILING_AGGREGATE_IDS,
    LCTTItemMappingError,
    LCTTSchemaStatus,
    LCTTSourceRowStatus,
    adapt_lctt_logical_rows,
    build_lctt_direct_schema_projection,
    load_lctt_direct_mapping_policy,
    reconcile_lctt_direct_items,
    validate_lctt_item_mapping_result,
)
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.lctt_word_box import (
    LCTTPageInput,
    load_lctt_word_box_policy,
    parse_lctt_word_box_document,
)

_OCR_ROOT = Path("output/calibration/recovery-e0027-mbb-q1-2026-role-c-20260807")
_RENDER_ROOT = Path(
    "output/calibration/recovery-e0027-mbb-q1-2026-20260807/eebeda2ebc09b0d42032/renders"
)
_VISIBLE_CANDIDATES = (
    (4104,),
    (4123,),
    (4124,),
    (4125,),
    (4126,),
    (4154,),
    (4127,),
    (4122,),
    (4128,),
    (4109,),
    (4107,),
    (4129,),
    (4130,),
    (4131,),
    (4132,),
    (4133,),
    (4134,),
    (4108,),
    (4135,),
    (4136,),
    (4137,),
    (4138,),
    (4139,),
    (4140,),
    (4141,),
    (4142,),
    (4110,),
    (4105,),
    (4118,),
    (4119,),
    (4144, 4145, 4146),
    (4120, 4121),
    (4147,),
    (4111,),
    (4106,),
    (4148,),
    (4149,),
    (4150,),
    (4153,),
    (4112,),
    (4114,),
    (4115,),
    (4116,),
)
_DEEPSEEK_LABELS = (
    "| LƯU CHUYỂN TIỀN TỪ HOẠT ĐỘNG KINH DOANH",
    "| Thu lãi và các khoản thu tương tự nhận được",
    "| Chi lài và các khoản chi tương tự đã trả",
    "Thu nhập từ hoạt động dịch vụ nhận được",
    "Chênh lệch số tiền thực thu/(chỉ) từ hoạt động kinh doanh (ngoại tệ, vàng bạc, chứng khoán)",
    "| Thu nhập/(Chi phí) khác",
    "Tiền thu các khoản nợ đã được xử lý, xoá, bù đắp bằng nguồn rủi ro",
    "Tiền chi trả cho nhân viên và hoạt động quản lý, công vụ",
    "Tiền thuế thu nhập doanh nghiệp thực nộp trong kỳ",
    "Lưu chuyển tiền thuần từ hoạt động kinh doanh trước những thay đổi về tài sản và vốn lưu động",
    "Những thay đổi về tài sản hoạt động",
    "(Tăng)/Giảm các khoản tiền gửi và cho vay các TCTD khác",
    "(Tăng)/Giảm các khoản về kinh doanh chứng khoán",
    "(Tăng)/Giảm các công cụ tài chính phái sinh và các tài sản tài chính khác",
    "(Tăng)/Giảm các khoản cho vay khách hàng và mua nợ",
    "Giảm nguồn dự phòng để xử lý rủi ro, xử lý, bù đắp tổn thất các khoản (tín dụng, "
    "chứng khoán, đầu tư, phải thu khác)",
    "(Tăng)/Giảm khác về tài sản hoạt động",
    "Những thay đổi về công nghệ hoạt động",
    "| [Tăng/(Giảm)] các khoản nợ Chính phủ và NHNN",
    "Tăng/(Giảm) các khoản tiền gửi, tiền vay các TCTD khác",
    "Tăng/(giảm) tiền gửi của khách hàng",
    "Tăng/(Giảm) phát hành giấy tờ có giá",
    "TẠNG/(Giám) vốn tài trợ, uỷ thác đầu tư, cho vay mà TCTD chịu rủi ro",
    "Tăng/(Giảm) các công cụ tài chính phái sinh và các tài sản tài chính khác",
    "Tăng/(Giảm) khác về công nợ hoạt động",
    "| Chi tiết các quỹ của TCTD",
    "| Lưu chuyển tiền thuần từ hoạt động kinh doanh",
    "LƯU CHUYỂN TIỀN TỪ HOẠT ĐỘNG ĐẦU TƯ",
    "Mua sắm tài sản cố định",
    "Tiền thu từ thanh lý, nhượng bán tài sản cố định",
    "| Tiền thu/(chi) bất động sản đầu tư",
    "| Tiền thu/(chi) đầu tư, góp vốn vào các đơn vị khác",
    "Tên thủ công của lợi nhuận được chia từ các khoản đầu tư, góp vốn dài hạn",
    "//Lưu chuyển tiền thuần sử dụng trong hoạt động đầu tư",
    "LƯU CHUYỂN TIỀN TỪ HOẠT ĐỘNG TÀI CHÍNH",
    "|Tăng vốn cổ phần từ góp vốn và/hoặc phát hành cổ phiếu",
    "Tiền thu từ phát hành giấy tờ có giá dài hạn đủ điều kiện tính vào vốn tự có và "
    "các khoản vốn vay dài hạn khác",
    "Tiền chi thanh toán giấy tờ có giá dài hạn có đủ điều kiện tính vào vốn tự có và "
    "các khoản vốn vay dài hạn khác",
    "Cố tức trả cho cổ đông",
    "| Lưu chuyển tiền thuần từ hoạt động tài chính",
    "| Lưu chuyển tiền thuần trong kỳ",
    "| Tiền và các khoản tương đương tiền tại thời điểm đầu kỳ",
    "# Tiền và các khoản tương đương tiền tại thời điểm cuối kỳ",
)


@pytest.fixture(scope="module")
def lctt_schema(project_root: Path):
    _workbooks, schema = load_all(project_root / "template", project_root)
    _registry, hierarchy = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml",
        project_root,
        schema,
    )
    apply_hierarchy_reference(schema, hierarchy)
    return schema


@pytest.fixture(scope="module")
def parsed_lctt(project_root: Path):
    inputs = tuple(
        LCTTPageInput(
            result_path=(project_root / _OCR_ROOT / f"ppocrv6-page-{page:04d}" / "ocr_result.json"),
            source_image_path=project_root / _RENDER_ROOT / f"page-{page:04d}.png",
            page_tag=f"page-{page:04d}",
        )
        for page in (7, 8)
    )
    if not all(page.result_path.is_file() and page.source_image_path.is_file() for page in inputs):
        pytest.skip("MBB Q1/2026 LCTT source-visible artifacts are not local")
    return parse_lctt_word_box_document(
        inputs,
        load_lctt_word_box_policy(project_root / "config/tables/lctt-word-box-v1.yaml"),
    )


@pytest.fixture(scope="module")
def real_reconciliation(project_root: Path, lctt_schema, parsed_lctt):
    policy = load_lctt_direct_mapping_policy(project_root / LCTT_POLICY_RELATIVE_PATH)
    result = reconcile_lctt_direct_items(
        parsed_lctt.rows,
        schema=lctt_schema,
        policy=policy,
        report_scope=parsed_lctt.scope,
        cash_flow_method=parsed_lctt.method,
    )
    return policy, result


@pytest.fixture(scope="module")
def real_dual_reconciliation(project_root: Path, lctt_schema, parsed_lctt):
    assert len(_DEEPSEEK_LABELS) == 43
    semantic_rows = tuple(
        {
            "row_id": row.row_id,
            "page_tag": row.page_tag,
            "proposal_text": label,
        }
        for row, label in zip(parsed_lctt.rows, _DEEPSEEK_LABELS, strict=True)
    )
    policy = load_lctt_direct_mapping_policy(project_root / LCTT_POLICY_RELATIVE_PATH)
    result = reconcile_lctt_direct_items(
        parsed_lctt.rows,
        schema=lctt_schema,
        policy=policy,
        report_scope=parsed_lctt.scope,
        cash_flow_method=parsed_lctt.method,
        independent_semantic_rows=semantic_rows,
        independent_source_reader_id="deepseek-ocr2-logical-row",
    )
    return policy, result


def test_direct_projection_and_policy_reconcile_exact_denominators(
    project_root: Path, lctt_schema
) -> None:
    projection = build_lctt_direct_schema_projection(lctt_schema)
    policy = load_lctt_direct_mapping_policy(project_root / LCTT_POLICY_RELATIVE_PATH)

    assert len(projection.nodes) == 50
    assert [node.display_order for node in projection.nodes] == list(range(57, 107))
    assert (
        tuple(node.report_norm_id for node in projection.nodes if node.child_report_norm_ids)
        == LCTT_TRAILING_AGGREGATE_IDS
    )
    assert policy.schema_total == 107
    assert policy.applicable_branch_total == 50
    assert policy.non_applicable_branch_total == 57
    assert policy.visible_source_row_total == 43
    assert policy.currently_available_independent_semantic_streams == 1
    assert policy.minimum_independent_semantic_streams == 2
    assert policy.minimum_cross_reader_label_similarity == 0.85
    assert tuple(rule.report_norm_id for rule in policy.label_conflict_rules) == (4140,)
    assert policy.not_observed_report_norm_ids == (4143, 4151, 4152, 4117)


def test_real_43_rows_reconcile_all_107_without_automatic_selection(
    real_reconciliation,
) -> None:
    _policy, result = real_reconciliation

    assert validate_lctt_item_mapping_result(result) is result
    assert result.status == "CANDIDATE_RECONCILIATION"
    assert not result.automatic_selection_allowed
    assert result.schema_item_count == 107
    assert result.schema_status_reconciled_count == 107
    assert result.mapped_schema_count == 0
    assert result.candidate_linked_schema_count == 41
    assert result.label_conflict_schema_count == 1
    assert result.ambiguous_schema_count == 5
    assert result.not_observed_schema_count == 4
    assert result.not_applicable_schema_count == 57
    assert result.fully_verified_schema_count == 0
    assert result.source_row_count == 43
    assert result.mapped_source_row_count == 0
    assert result.candidate_linked_source_row_count == 41
    assert result.label_conflict_source_row_count == 1
    assert result.source_only_row_count == 2
    assert result.independent_label_sha256 is None
    assert (
        tuple(item.candidate_report_norm_ids for item in result.source_dispositions)
        == _VISIBLE_CANDIDATES
    )

    schema_by_status = {
        status: {
            item.report_norm_id for item in result.schema_dispositions if item.status == status
        }
        for status in {item.value for item in LCTTSchemaStatus}
    }
    assert schema_by_status[LCTTSchemaStatus.AMBIGUOUS_MAPPING.value] == {
        4144,
        4145,
        4146,
        4120,
        4121,
    }
    assert schema_by_status[LCTTSchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value] == {
        4143,
        4151,
        4152,
        4117,
    }
    assert len(schema_by_status[LCTTSchemaStatus.SCHEMA_ITEM_NOT_APPLICABLE.value]) == 57
    assert {
        item.row_id
        for item in result.source_dispositions
        if item.status == LCTTSourceRowStatus.SOURCE_ONLY_PDF_ROW.value
    } == {"page-0007:row-0031", "page-0007:row-0032"}
    assert schema_by_status[LCTTSchemaStatus.LABEL_CONFLICT_CANDIDATE_NOT_AUTOMATIC.value] == {4140}
    assert {
        item.row_id
        for item in result.source_dispositions
        if item.status == LCTTSourceRowStatus.LABEL_CONFLICT_CANDIDATE_NOT_AUTOMATIC.value
    } == {"page-0007:row-0024"}
    assert (
        min(
            item.label_similarity
            for item in result.source_dispositions
            if item.status == LCTTSourceRowStatus.CANDIDATE_MAPPING_NOT_AUTOMATIC.value
        )
        >= 0.45
    )


def test_real_deepseek_stream_promotes_40_and_withholds_visible_label_conflict(
    real_dual_reconciliation,
) -> None:
    _policy, result = real_dual_reconciliation

    assert validate_lctt_item_mapping_result(result) is result
    assert result.status == "PARTIAL_AUTOMATIC_MAPPING_WITH_UNRESOLVED_ITEMS"
    assert result.automatic_selection_allowed
    assert result.independent_semantic_stream_count == 2
    assert result.schema_item_count == 107
    assert result.schema_status_reconciled_count == 107
    assert result.mapped_schema_count == 40
    assert result.candidate_linked_schema_count == 1
    assert result.label_conflict_schema_count == 1
    assert result.ambiguous_schema_count == 5
    assert result.not_observed_schema_count == 4
    assert result.not_applicable_schema_count == 57
    assert result.fully_verified_schema_count == 0
    assert result.source_row_count == 43
    assert result.mapped_source_row_count == 40
    assert result.candidate_linked_source_row_count == 1
    assert result.label_conflict_source_row_count == 1
    assert result.source_only_row_count == 2
    assert result.independent_label_sha256 is not None

    mapped_schema = tuple(
        item
        for item in result.schema_dispositions
        if item.status == LCTTSchemaStatus.MAPPED_AUTOMATIC.value
    )
    mapped_source = tuple(
        item
        for item in result.source_dispositions
        if item.status == LCTTSourceRowStatus.MAPPED_AUTOMATIC.value
    )
    assert len(mapped_schema) == len(mapped_source) == 40
    assert all(len(item.supporting_reader_ids) == 2 for item in mapped_schema)
    assert all(len(item.supporting_reader_ids) == 2 for item in mapped_source)
    assert min(item.label_similarity for item in mapped_source) >= 0.60
    assert min(item.independent_label_similarity for item in mapped_source) >= 0.60
    assert min(item.cross_reader_label_similarity for item in mapped_source) >= 0.85
    assert {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == LCTTSchemaStatus.AMBIGUOUS_MAPPING.value
    } == {4144, 4145, 4146, 4120, 4121}
    assert {
        item.row_id
        for item in result.source_dispositions
        if item.status == LCTTSourceRowStatus.SOURCE_ONLY_PDF_ROW.value
    } == {"page-0007:row-0031", "page-0007:row-0032"}
    conflict_schema = next(
        item
        for item in result.schema_dispositions
        if item.status == LCTTSchemaStatus.LABEL_CONFLICT_CANDIDATE_NOT_AUTOMATIC.value
    )
    conflict_source = next(
        item
        for item in result.source_dispositions
        if item.status == LCTTSourceRowStatus.LABEL_CONFLICT_CANDIDATE_NOT_AUTOMATIC.value
    )
    assert conflict_schema.report_norm_id == 4140
    assert conflict_schema.candidate_source_row_ids == ("page-0007:row-0024",)
    assert conflict_source.row_id == "page-0007:row-0024"
    assert conflict_source.candidate_report_norm_ids == (4140,)
    assert conflict_schema.label_conflict_key == conflict_source.label_conflict_key


def test_non_direct_method_cannot_enter_direct_candidate_reconciliation(
    lctt_schema, parsed_lctt, real_reconciliation
) -> None:
    policy, _result = real_reconciliation
    with pytest.raises(LCTTItemMappingError, match="requires visible DIRECT"):
        reconcile_lctt_direct_items(
            parsed_lctt.rows,
            schema=lctt_schema,
            policy=policy,
            report_scope=parsed_lctt.scope,
            cash_flow_method=CashFlowMethod.INDIRECT,
        )


@dataclass(frozen=True)
class _VisibleReaderRow:
    label: str

    @property
    def cells(self):
        raise AssertionError("LCTT mapping adapter must not read numeric cells")


@dataclass(frozen=True)
class _ParserRow:
    row_id: str
    page_tag: str
    row: _VisibleReaderRow


def test_adapter_reads_visible_labels_but_never_numeric_cells() -> None:
    rows = tuple(
        _ParserRow(f"page-0001:row-{index + 1:04d}", "page-0001", _VisibleReaderRow("Label"))
        for index in range(43)
    )

    adapted = adapt_lctt_logical_rows(rows)

    assert len(adapted) == 43
    assert [row.order for row in adapted] == list(range(43))
    assert {row.visible_label for row in adapted} == {"Label"}
