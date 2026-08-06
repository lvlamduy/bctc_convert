from __future__ import annotations

from bctc_ai.mapping.alignment_v2 import (
    MappingDecisionStatus,
    ObservedRowV2,
    load_structural_ranking_policy,
    rank_structural_candidates,
    validate_mapping_sequence,
)
from bctc_ai.mapping.scope import load_scope_policy
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import SchemaItem, load_all


def _real_schema(project_root):
    _, schema = load_all(project_root / "template", project_root)
    _, hierarchy = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml", project_root, schema
    )
    apply_hierarchy_reference(schema, hierarchy)
    return schema


def _policies(project_root):
    ranking = load_structural_ranking_policy(
        project_root / "config/mapping/structural-ranking-v2.yaml"
    )
    scope = load_scope_policy(project_root / ranking.scope_policy_path)
    return ranking, scope


def test_parent_hierarchy_disambiguates_generic_fixed_asset_label(project_root):
    schema = _real_schema(project_root)
    ranking, scope = _policies(project_root)
    row = ObservedRowV2(
        row_id="acb-p3-r-tangible-cost",
        label="Nguyên giá tài sản cố định",
        order=0,
        statement_type="CDKT",
        scope="CONSOLIDATED",
        parent_schema_id=4328,
        previous_schema_id=4328,
        next_schema_id=4368,
        indentation_level=4,
    )
    result = rank_structural_candidates(
        row,
        schema,
        policy=ranking,
        scope_policy=scope,
        # Deliberately favor the wrong finance-lease candidate historically.
        same_bank_history={4367: 0.0, 4369: 1.0, 4371: 1.0},
    )
    assert result.status is MappingDecisionStatus.RESOLVED
    assert result.recommended_schema_id == 4367
    assert result.automatic_selection_allowed


def test_parent_and_neighbors_resolve_generic_risk_provision(project_root):
    schema = _real_schema(project_root)
    ranking, scope = _policies(project_root)
    row = ObservedRowV2(
        row_id="acb-p3-risk-provision",
        label="Dự phòng rủi ro",
        order=0,
        statement_type="CDKT",
        scope="CONSOLIDATED",
        parent_schema_id=4312,
        previous_schema_id=4326,
        next_schema_id=4313,
        indentation_level=3,
    )
    result = rank_structural_candidates(row, schema, policy=ranking, scope_policy=scope)
    assert result.recommended_schema_id == 4345
    assert result.status is MappingDecisionStatus.RESOLVED


def test_xdcb_label_maps_once_to_4373_not_4337(project_root):
    schema = _real_schema(project_root)
    ranking, scope = _policies(project_root)
    row = ObservedRowV2(
        row_id="ctg-p4-xdcb",
        label="Vốn đầu tư XDCB, mua sắm TSCĐ",
        order=0,
        statement_type="CDKT",
        scope="CONSOLIDATED",
        parent_schema_id=4364,
        previous_schema_id=4337,
        next_schema_id=4338,
        indentation_level=4,
    )
    result = rank_structural_candidates(row, schema, policy=ranking, scope_policy=scope)
    assert result.status is MappingDecisionStatus.RESOLVED
    assert result.recommended_schema_id == 4373
    assert [candidate.schema_id for candidate in result.candidates].count(4373) == 1


def test_off_balance_section_is_a_scope_result_not_mapping_failure(project_root):
    schema = _real_schema(project_root)
    ranking, scope = _policies(project_root)
    row = ObservedRowV2(
        row_id="ctg-p5-other-documents",
        label="Tài sản và chứng từ khác",
        order=0,
        statement_type="CDKT",
        scope="CONSOLIDATED",
        section_heading="CÁC CHỈ TIÊU NGOÀI BÁO CÁO TÌNH HÌNH TÀI CHÍNH",
    )
    result = rank_structural_candidates(row, schema, policy=ranking, scope_policy=scope)
    assert result.status is MappingDecisionStatus.OUT_OF_SCOPE_FOR_TARGET_TEMPLATE
    assert result.recommended_schema_id is None
    assert result.candidates == ()


def test_history_only_difference_remains_ambiguous(tmp_path, project_root):
    ranking, scope = _policies(project_root)
    schema = [
        SchemaItem(1, "Khác", "khac", "CDKT", 0),
        SchemaItem(2, "Khác", "khac", "CDKT", 0),
    ]
    row = ObservedRowV2("r", "Khác", 0, "CDKT", "CONSOLIDATED")
    result = rank_structural_candidates(
        row,
        schema,
        policy=ranking,
        scope_policy=scope,
        same_bank_history={1: 0.9, 2: 0.1},
    )
    assert result.recommended_schema_id == 1
    assert result.status is MappingDecisionStatus.AMBIGUOUS_MAPPING
    assert not result.automatic_selection_allowed


def test_candidate_display_limit_cannot_hide_an_ambiguity(project_root):
    ranking, scope = _policies(project_root)
    schema = [
        SchemaItem(1, "Khác", "khac", "CDKT", 0),
        SchemaItem(2, "Khác", "khac", "CDKT", 1),
    ]
    row = ObservedRowV2("r", "Khác", 0, "CDKT", "CONSOLIDATED")
    result = rank_structural_candidates(
        row,
        schema,
        policy=ranking,
        scope_policy=scope,
        limit=1,
    )
    assert len(result.candidates) == 1
    assert result.status is MappingDecisionStatus.AMBIGUOUS_MAPPING
    assert result.recommended_schema_id is None


def test_sequence_gate_uses_template_display_order_not_numeric_id(project_root):
    schema = _real_schema(project_root)
    rows = [
        ObservedRowV2("r1", "Vốn đầu tư của chủ sở hữu", 1, "CDKT", "CONSOLIDATED"),
        ObservedRowV2("r2", "Vốn đầu tư XDCB", 2, "CDKT", "CONSOLIDATED"),
        ObservedRowV2("r3", "Thặng dư vốn cổ phần", 3, "CDKT", "CONSOLIDATED"),
    ]
    # Workbook order is 4337 -> 4373 -> 4338 even though numeric order differs.
    valid = validate_mapping_sequence(rows, {"r1": 4337, "r2": 4373, "r3": 4338}, schema)
    assert valid.valid
    assert valid.schema_id_sequence == (4337, 4373, 4338)
    assert valid.display_order_sequence == (64, 65, 66)

    numerically_sorted = validate_mapping_sequence(
        rows, {"r1": 4337, "r2": 4338, "r3": 4373}, schema
    )
    assert not numerically_sorted.valid
    assert "numeric ID order is irrelevant" in numerically_sorted.violations[-1]


def test_sequence_gate_rejects_duplicate_schema_assignment(project_root):
    schema = _real_schema(project_root)
    rows = [
        ObservedRowV2("r1", "Lợi ích của cổ đông không kiểm soát", 1, "CDKT", "CONSOLIDATED"),
        ObservedRowV2("r2", "Lợi ích cổ đông thiểu số", 2, "CDKT", "CONSOLIDATED"),
    ]
    result = validate_mapping_sequence(rows, {"r1": 5699, "r2": 5699}, schema)
    assert not result.valid
    assert "one schema ID" in result.violations[0]
