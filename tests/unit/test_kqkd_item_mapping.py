from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

import pytest

from bctc_ai.mapping.kqkd_item_mapping import (
    KQKD_POLICY_RELATIVE_PATH,
    KQKD_TRAILING_AGGREGATE_IDS,
    KQKDItemMappingError,
    KQKDSchemaStatus,
    KQKDSourceRowStatus,
    adapt_kqkd_logical_rows,
    build_kqkd_schema_projection,
    load_kqkd_mapping_policy,
    map_kqkd_items,
    validate_kqkd_mapping_result,
)
from bctc_ai.mapping.ordered_subgraph_v2 import MappingRunStatus
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import load_all
from bctc_ai.tables.kqkd_word_box import (
    load_kqkd_word_box_policy,
    parse_kqkd_word_box_page,
)

_WORD_BOX_FIXTURE = Path("tests/golden/kqkd/mbb-q1-2026-page-0006-ppocrv6-word-box.json")
_DEEPSEEK_LABELS = (
    "_____ Thu nhập lãi và các khoản thu nhập tương tự",
    "Chi phí lãi và các khoản chi phí tương tự",
    "Thụ nhập lại thuận",
    "Thủ nhập từ hoạt động dịch vụ",
    "Chi phí hoạt động dịch vụ",
    "Lãi thuần từ hoạt động dịch vụ",
    "Lãi thuần từ hoạt động kinh doanh ngoại hối",
    "Lãi thuần từ mua bán chứng khoán kinh doanh",
    "Lãi thuần từ mua bán chứng khoán đầu tư",
    "Lãi thuần từ hoạt động kinh doanh khác",
    "Thu nhập từ góp vốn, mua cổ phần",
    "TỔNG THU NHẬP HOẠT ĐỘNG",
    "TỔNG CHI PHÍ HOẠT ĐỘNG",
    "Lợi nhuận thuần từ hoạt động kinh doanh trước chi phí dự phòng rủi ro",
    "Chi phí dự phòng rủi ro",
    "TỔNG LỢI NHUẬN TRƯỚC THUẾ",
    "Chi phí thuê TNDN hiện hành",
    "Chi phí thuế TNDN hoãn lại",
    "Chi phí thuê TNDN trong kỳ",
    "LƠI NHUẬN SAU THUẾ",
    "Lợi ích của cổ đông không kiểm soát",
    "LỢI NHUẬN SAU THUẾ CỦA NGÂN HÀNG",
)
_VISIBLE_SCHEMA_IDS = (
    4399,
    4396,
    4385,
    4397,
    4398,
    4386,
    4387,
    4388,
    4389,
    4390,
    4393,
    None,
    4391,
    4376,
    4392,
    4377,
    4383,
    4384,
    4382,
    4378,
    4379,
    4380,
)


@pytest.fixture(scope="module")
def kqkd_schema(project_root: Path):
    _workbooks, schema = load_all(project_root / "template", project_root)
    _registry, hierarchy = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml",
        project_root,
        schema,
    )
    apply_hierarchy_reference(schema, hierarchy)
    return schema


@pytest.fixture(scope="module")
def real_mapping(project_root: Path, kqkd_schema):
    parsed = parse_kqkd_word_box_page(
        project_root / _WORD_BOX_FIXTURE,
        load_kqkd_word_box_policy(project_root / "config/tables/kqkd-word-box-v1.yaml"),
        page_tag="page-0006",
    )
    labels_by_reader = {
        "deepseek": {
            row.row_id: label for row, label in zip(parsed.rows, _DEEPSEEK_LABELS, strict=True)
        },
        "ppocr": {row.row_id: row.row.label for row in parsed.rows},
    }
    result = map_kqkd_items(
        parsed.rows,
        labels_by_reader=labels_by_reader,
        schema=kqkd_schema,
        policy=load_kqkd_mapping_policy(project_root / KQKD_POLICY_RELATIVE_PATH),
        report_scope=parsed.scope,
    )
    return parsed, result


def test_kqkd_projection_and_policy_cover_all_children_before_rollups(
    project_root: Path,
    kqkd_schema,
):
    projection = build_kqkd_schema_projection(kqkd_schema)
    policy = load_kqkd_mapping_policy(project_root / KQKD_POLICY_RELATIVE_PATH)
    aggregates = tuple(
        node.report_norm_id for node in projection.nodes if node.child_report_norm_ids
    )

    assert len(projection.nodes) == 24
    assert aggregates == KQKD_TRAILING_AGGREGATE_IDS
    assert policy.trailing_aggregate_ids == aggregates
    assert policy.beam_width == 8192
    assert policy.minimum_interval_margin == 0.08
    assert all(
        projection.by_id()[child_id].display_order < aggregate.display_order
        for aggregate in projection.nodes
        for child_id in aggregate.child_report_norm_ids
    )


def test_real_22_row_order_reconciles_21_mapped_three_not_observed_and_source_only(
    real_mapping,
):
    parsed, result = real_mapping
    schema_by_id = {item.report_norm_id: item for item in result.schema_dispositions}
    source_by_id = {item.row_id: item for item in result.source_dispositions}

    assert len(parsed.rows) == 22
    assert result.status == MappingRunStatus.RESOLVED.value
    assert result.automatic_selection_allowed
    assert result.schema_item_count == 24
    assert result.mapped_schema_count == 21
    assert result.not_observed_schema_count == 3
    assert result.ambiguous_schema_count == 0
    assert result.source_row_count == 22
    assert result.mapped_source_row_count == 21
    assert result.source_only_row_count == 1
    assert result.ambiguous_source_row_count == 0
    assert {
        item.report_norm_id
        for item in result.schema_dispositions
        if item.status == KQKDSchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
    } == {4394, 4395, 4381}
    assert all(
        schema_by_id[report_norm_id].status == KQKDSchemaStatus.MAPPED.value
        for report_norm_id in _VISIBLE_SCHEMA_IDS
        if report_norm_id is not None
    )
    source_only = parsed.rows[11]
    assert source_by_id[source_only.row_id].status == KQKDSourceRowStatus.SOURCE_ONLY_PDF_ROW
    assert source_by_id[source_only.row_id].report_norm_id is None
    assert [item.report_norm_id for item in result.source_dispositions] == list(_VISIBLE_SCHEMA_IDS)


@dataclass(frozen=True)
class _ParserModel:
    row_id: str
    ordinal: int
    row: object


class _UnopenedPayload:
    def __getattribute__(self, name: str):
        raise AssertionError(f"parser payload must remain unopened: {name}")


def test_adapter_accepts_raw_dict_and_parser_model_but_only_reads_identity_and_labels():
    logical_rows = [
        {"row_id": "raw-row", "ordinal": 17, "unrelated_payload": object()},
        _ParserModel("model-row", 31, _UnopenedPayload()),
    ]
    rows = adapt_kqkd_logical_rows(
        logical_rows,
        labels_by_reader={
            "reader-a": {"raw-row": "Thu nhập lãi", "model-row": "Chi phí lãi"},
            "reader-b": {"raw-row": "Thu nhập lãi", "model-row": "Chi phí lãi"},
        },
    )

    assert [(row.row_id, row.order) for row in rows] == [("raw-row", 17), ("model-row", 31)]
    assert all(row.row_role == "UNKNOWN" for row in rows)
    assert all(row.parent_row_id is None and row.relation_type == "UNKNOWN" for row in rows)
    assert rows[0].labels_by_reader == {
        "reader-a": "Thu nhập lãi",
        "reader-b": "Thu nhập lãi",
    }


def test_adapter_rejects_duplicate_identity_and_cross_linked_reader_labels():
    with pytest.raises(KQKDItemMappingError, match="unique"):
        adapt_kqkd_logical_rows(
            [{"row_id": "same", "order": 1}, {"row_id": "same", "order": 2}],
            labels_by_reader={"reader": {"same": "label"}},
        )
    with pytest.raises(KQKDItemMappingError, match="unknown row"):
        adapt_kqkd_logical_rows(
            [{"row_id": "known", "order": 1}],
            labels_by_reader={"reader": {"different": "label"}},
        )


def test_disagreeing_independent_readers_fail_closed_as_ambiguous(
    project_root: Path,
    kqkd_schema,
):
    projection = build_kqkd_schema_projection(kqkd_schema)
    by_id = projection.by_id()
    result = map_kqkd_items(
        [{"row_id": "uncertain", "order": 91}],
        labels_by_reader={
            "reader-a": {"uncertain": by_id[4399].canonical_name},
            "reader-b": {"uncertain": by_id[4396].canonical_name},
        },
        schema=kqkd_schema,
        policy=load_kqkd_mapping_policy(project_root / KQKD_POLICY_RELATIVE_PATH),
    )

    assert result.status == MappingRunStatus.AMBIGUOUS_MAPPING.value
    assert not result.automatic_selection_allowed
    assert result.ambiguous_schema_count == 2
    assert result.not_observed_schema_count == 22
    assert result.ambiguous_source_row_count == 1
    assert result.source_dispositions[0].status == KQKDSourceRowStatus.AMBIGUOUS_MAPPING


def test_raw_and_model_results_are_validated_with_counts_and_bijections(real_mapping):
    _parsed, result = real_mapping
    assert validate_kqkd_mapping_result(result) is result
    raw = result.to_dict()
    assert validate_kqkd_mapping_result(raw) is raw

    wrong_count = deepcopy(raw)
    wrong_count["mapped_schema_count"] = 20
    with pytest.raises(KQKDItemMappingError, match="counts"):
        validate_kqkd_mapping_result(wrong_count)

    extra_field = deepcopy(raw)
    extra_field["schema_dispositions"][0]["unvalidated"] = True
    with pytest.raises(KQKDItemMappingError, match="keyset"):
        validate_kqkd_mapping_result(extra_field)

    cross_link = deepcopy(raw)
    cross_link["schema_dispositions"][0]["source_row_id"] = result.source_dispositions[1].row_id
    with pytest.raises(KQKDItemMappingError, match="bijective"):
        validate_kqkd_mapping_result(cross_link)
