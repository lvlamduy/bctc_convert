from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

import bctc_ai.mapping.e0040_calibration_challenger as challenger_module
from bctc_ai.mapping.e0040_calibration_challenger import (
    E0040ChallengerError,
    _normalized_projection,
    align_e0040_calibration_challenger,
    challenger_result_json,
    load_e0040_policy,
    load_e0040_policy_bytes,
    projection_from_sealed_mapping_payload,
    semantic_key,
    source_rows_from_sealed_mapping_payload,
)
from bctc_ai.mapping.ordered_subgraph_v2 import (
    SchemaProjectionV2,
    _projection_digest,
    load_ordered_subgraph_v2_policy,
)

_CONFIG = Path("config/mapping/e0040-cdkt-semantic-normalization.yaml")
_MAPPER_POLICY = Path("config/mapping/ordered-subgraph-v2-exact-e0038.yaml")
_E0037_MAPPING = Path("output/calibration/e0037-mbb-cdkt-sealed-evidence-mapping/mapping_only.json")
_E0038_MAPPING = Path("output/calibration/e0038-mbb-cdkt-exact-mapping/mapping_only.json")
_BASE_PROJECTION_SHA256 = "7025ca729c01a3f2030af38e9745a0ee8d72b1dad60c8d4e3b7cf749e5eb860c"
_MAPPER_POLICY_SHA256 = "2f18880339b8e2c04ec3ba900919f174f8af478515adfbfb0e43ff80ddd13268"
_E0037_MAPPING_SHA256 = "e18f6b20825f93b20023c0d89caca1737481008b244696594852ca9fa972f99e"


@pytest.fixture(scope="module")
def e0037_payload(project_root: Path):
    payload = (project_root / _E0037_MAPPING).read_bytes()
    assert hashlib.sha256(payload).hexdigest() == _E0037_MAPPING_SHA256
    return json.loads(payload)


@pytest.fixture(scope="module")
def frozen_challenger(project_root: Path, e0037_payload):
    policy = load_e0040_policy(project_root / _CONFIG)
    mapper_policy = load_ordered_subgraph_v2_policy(project_root / _MAPPER_POLICY)
    rows = source_rows_from_sealed_mapping_payload(e0037_payload)
    projection = projection_from_sealed_mapping_payload(e0037_payload)
    result = align_e0040_calibration_challenger(
        rows,
        projection,
        policy=policy,
        mapper_policy=mapper_policy,
    )
    # Materialize canonical output before any E-0038 post-check is opened.
    canonical = challenger_result_json(result)
    return policy, mapper_policy, rows, projection, result, canonical


def _selected_from_e0038(payload: dict[str, object]) -> tuple[tuple[str, int], ...]:
    exact = payload["exact_mapping_bundle"]["exact_search"]
    rows = exact["mapping_result_without_internal_alias_authority"]["row_mappings"]
    return tuple(
        (row["row_id"], row["selected_report_norm_id"])
        for row in rows
        if row["selected_report_norm_id"] is not None
    )


def test_policy_is_generic_all_bank_cdkt_calibration_snapshot(project_root: Path):
    source = (project_root / _CONFIG).read_bytes()
    policy = load_e0040_policy_bytes(source, source_path=project_root / "not-opened.yaml")

    assert policy.source_bytes is source
    assert policy.policy_sha256 == hashlib.sha256(source).hexdigest()
    assert policy.statement_type == "CDKT"
    assert policy.bank_scope == "ALL_BANKS"
    assert policy.base_node_count == 77
    assert policy.base_projection_sha256 == _BASE_PROJECTION_SHA256
    assert policy.mapper_policy_sha256 == _MAPPER_POLICY_SHA256
    assert policy.mapper_invocation_count == 2
    assert [(item.full_form, item.acronym) for item in policy.acronym_rules] == [
        (("ngan", "hang", "nha", "nuoc"), "nhnn"),
        (("to", "chuc", "tin", "dung"), "tctd"),
    ]
    assert policy.removable_particles == ("cua",)
    assert policy.never_relax_observed_roles == ("SECTION", "TOTAL")


def test_generic_semantic_keys_cover_acronyms_particles_and_cdkt_aggregate_wording(
    frozen_challenger,
):
    policy = frozen_challenger[0]
    assert semantic_key('Tiền gửi tại Ngân hàng Nhà nước ("NHNN")', policy) == ("tien gui tai nhnn")
    assert semantic_key('các tổ chức tín dụng ("TCTD") khác', policy) == "cac tctd khac"
    assert semantic_key("Lợi ích của cổ đông không kiểm soát", policy) == semantic_key(
        "Lợi ích cổ đông không kiểm soát", policy
    )
    assert semantic_key("TỔNG TÀI SẢN CÓ", policy) == semantic_key("TỔNG CỘNG TÀI SẢN", policy)


def test_challenger_reaches_61_of_64_with_only_three_generic_additions(frozen_challenger):
    _policy, _mapper, _rows, _projection, result, _canonical = frozen_challenger
    selected = dict(result.final_selected_pairs)

    assert len(result.final_result.row_mappings) == 64
    assert len(result.final_selected_pairs) == 61
    assert selected["page-0003-row-002-label"] == 4311
    assert selected["page-0003-row-003-label"] == 4312
    assert selected["page-0004-row-002-label"] == 4319
    assert result.newly_selected_pairs == (
        ("page-0003-row-003-label", 4312),
        ("page-0004-row-002-label", 4319),
    )
    assert len(result.baseline_selected_pairs) == 59


def test_postfreeze_e0038_parity_preserves_all_58_pairs_and_adds_exactly_three(
    project_root: Path,
    frozen_challenger,
):
    # E-0038 is deliberately opened only here, after the E-0040 result and its
    # canonical bytes were already materialized by the module-scoped fixture.
    sealed = json.loads((project_root / _E0038_MAPPING).read_text(encoding="utf-8"))
    sealed_pairs = _selected_from_e0038(sealed)
    result = frozen_challenger[4]

    assert len(sealed_pairs) == 58
    assert set(sealed_pairs).issubset(result.final_selected_pairs)
    assert tuple(item for item in result.final_selected_pairs if item not in set(sealed_pairs)) == (
        ("page-0003-row-002-label", 4311),
        ("page-0003-row-003-label", 4312),
        ("page-0004-row-002-label", 4319),
    )


def test_combined_parent_gate_has_two_reader_and_child_composition_proof(
    frozen_challenger,
):
    _policy, _mapper, rows, _projection, result, _canonical = frozen_challenger
    original = {item.row.row_id: item for item in rows}
    overrides = result.combined_parent_overrides

    assert [(item.row_id, item.target_report_norm_id) for item in overrides] == [
        ("page-0003-row-003-label", 4312),
        ("page-0004-row-002-label", 4319),
    ]
    for item in overrides:
        assert original[item.row_id].row.row_role == "DETAIL"
        assert original[item.row_id].child_set_complete == "UNKNOWN"
        assert original[item.row_id].row.parent_row_id is None
        assert item.observed_role == "DETAIL"
        assert item.effective_role == "GROUP"
        assert len(item.supporting_reader_ids) >= 2
        supporting = [evidence for evidence in item.reader_evidence if evidence.passes]
        assert len(supporting) >= 2
        assert all(len(evidence.covered_child_report_norm_ids) >= 2 for evidence in supporting)
        assert all(evidence.distinct_discriminating_token_count >= 3 for evidence in supporting)

    # The first combined parent has six child-signature tokens but one of them
    # ("tai") is absent from the source.  Only the five actually observed
    # discriminating tokens may be credited.
    first_support = [
        evidence
        for evidence in overrides[0].reader_evidence
        if evidence.reader_id in {"deepseek_ocr2", "vietocr"}
    ]
    assert [item.distinct_discriminating_token_count for item in first_support] == [5, 5]


def test_section_and_total_rows_are_retained_as_source_only_unmatched(frozen_challenger):
    result = frozen_challenger[4]
    assert [
        (item.row_id, item.observed_role, item.selected_report_norm_id)
        for item in result.source_only_structural_rows
    ] == [
        ("page-0004-row-000-label", "SECTION", None),
        ("page-0004-row-013-label", "SECTION", None),
        ("page-0004-row-023-label", "TOTAL", None),
    ]
    assert all(
        item.disposition == "SOURCE_ONLY_STRUCTURAL_ROW_HYPOTHESIS_UNMATCHED"
        and item.final_mapping_status == "NO_ADMISSIBLE_PAIR"
        for item in result.source_only_structural_rows
    )


def test_generic_normalization_has_zero_new_cross_id_collision_across_all_77_nodes(
    frozen_challenger,
):
    result = frozen_challenger[4]
    audit = result.collision_audit

    assert audit.statement_type == "CDKT"
    assert audit.node_count == 77
    assert len(audit.base_collision_pairs) == 6
    assert audit.result_collision_pairs == audit.base_collision_pairs
    assert audit.new_collision_pairs == ()
    assert result.normalization.changed_schema_node_count == 21
    assert result.normalization.derived_key_count == 33
    assert result.normalization.id_scoped_alias_invocation_count == 0
    assert result.normalization.bank_page_or_row_rule_invocation_count == 0


def test_real_result_pins_limiting_margin_counterfactuals_and_exhaustive_search(
    frozen_challenger,
):
    policy, _mapper, _rows, _projection, result, _canonical = frozen_challenger
    final = result.final_result
    limiting = next(
        interval for interval in final.intervals if interval.row_ids == ("page-0003-row-003-label",)
    )

    assert policy.calibration_status == "CALIBRATION_CHALLENGER_NOT_PRODUCTION_APPROVED"
    assert limiting.status == "RESOLVED_PATH"
    assert limiting.best_path.total_score == 0.158511
    assert limiting.runner_up_path is not None
    assert limiting.runner_up_path.total_score == 0.0
    assert limiting.score_margin == 0.158511
    assert limiting.score_margin - 0.15 == pytest.approx(0.008511)
    assert limiting.counterfactuals[0].exclusion_margin == 0.158511
    assert limiting.counterfactuals[0].stable is True

    selected_path_count = sum(len(interval.best_path.matches) for interval in final.intervals)
    counterfactuals = tuple(
        counterfactual
        for interval in final.intervals
        for counterfactual in interval.counterfactuals
    )
    assert selected_path_count == 18
    assert len(counterfactuals) == selected_path_count
    assert all(item.stable and item.exclusion_margin >= 0.15 for item in counterfactuals)
    assert all(interval.search_exhaustive for interval in final.intervals)
    assert all(
        interval.main_search_pruned_states == 0
        and interval.counterfactual_search_pruned_states == 0
        for interval in final.intervals
    )
    assert final.search.pruned_states == 0
    assert final.search.main_search_pruned_states == 0
    assert final.search.counterfactual_search_pruned_states == 0

    selected_anchors = tuple(anchor for anchor in final.anchors if anchor.selected_report_norm_id)
    assert len(selected_anchors) == 43
    assert all(
        anchor.selection_allowed
        and anchor.counterfactual_margin is not None
        and anchor.counterfactual_margin >= 0.15
        for anchor in selected_anchors
    )
    alias_independent = {anchor.row_id: anchor for anchor in selected_anchors}
    assert alias_independent["page-0003-row-038-label"].counterfactual_margin == 0.357143
    assert alias_independent["page-0004-row-022-label"].counterfactual_margin == 0.233333


def test_former_alias_dependent_anchors_are_derived_without_id_scoped_aliases(
    frozen_challenger,
):
    policy, _mapper, rows, projection, result, _canonical = frozen_challenger
    nodes = projection.by_id()
    source = {item.row.row_id: item.row for item in rows}
    selected = dict(result.final_selected_pairs)

    assert nodes[4375].structural_aliases == ()
    assert nodes[5699].structural_aliases == ("6. Lợi ích cổ đông không kiểm soát",)
    assert selected["page-0003-row-038-label"] == 4375
    assert selected["page-0004-row-022-label"] == 5699
    for row_id, report_norm_id in (
        ("page-0003-row-038-label", 4375),
        ("page-0004-row-022-label", 5699),
    ):
        target = semantic_key(nodes[report_norm_id].canonical_name, policy)
        assert (
            sum(
                semantic_key(label, policy) == target
                for label in source[row_id].labels_by_reader.values()
            )
            >= 2
        )
    assert result.normalization.input_alias_authority == ("CANONICAL_AND_STRUCTURAL_ALIASES_ONLY")


def test_sealed_adapter_ignores_prior_mapping_and_page_metadata(
    project_root: Path,
    e0037_payload,
    frozen_challenger,
):
    mutated = copy.deepcopy(e0037_payload)
    for index, row in enumerate(mutated["rows"]):
        row["mapping"] = {"forbidden_prior_answer": index}
        row["page"] = 9000 + index
        row["row_ordinal"] = 8000 + index

    rows = source_rows_from_sealed_mapping_payload(mutated)
    projection = projection_from_sealed_mapping_payload(mutated)
    result = align_e0040_calibration_challenger(
        rows,
        projection,
        policy=frozen_challenger[0],
        mapper_policy=load_ordered_subgraph_v2_policy(project_root / _MAPPER_POLICY),
    )
    assert challenger_result_json(result) == frozen_challenger[5]


def test_repeat_is_byte_deterministic_and_does_not_mutate_inputs(
    project_root: Path,
    e0037_payload,
    frozen_challenger,
):
    projection = projection_from_sealed_mapping_payload(e0037_payload)
    rows = source_rows_from_sealed_mapping_payload(e0037_payload)
    projection_before = projection
    rows_before = rows
    replay = align_e0040_calibration_challenger(
        rows,
        projection,
        policy=frozen_challenger[0],
        mapper_policy=load_ordered_subgraph_v2_policy(project_root / _MAPPER_POLICY),
    )

    assert projection == projection_before
    assert rows == rows_before
    assert challenger_result_json(replay) == frozen_challenger[5]


def test_canonical_result_never_circulates_mapper_payload_without_e0040_receipt(
    frozen_challenger,
):
    result = frozen_challenger[4]
    payload = json.loads(frozen_challenger[5])

    assert set(payload) >= {
        "normalization",
        "collision_audit",
        "combined_parent_overrides",
        "baseline_result",
        "final_result",
    }
    assert (
        payload["normalization"]["result_projection_sha256"]
        == (payload["final_result"]["schema_projection_sha256"])
    )
    assert payload["normalization"]["id_scoped_alias_invocation_count"] == 0
    assert result.final_result.schema_alias_authority == (
        result.normalization.mapper_carrier_alias_authority
    )


def test_alias_overlay_and_foreign_statement_projections_fail_closed(frozen_challenger):
    policy, mapper, rows, projection, _result, _canonical = frozen_challenger
    overlay = replace(projection, alias_authority="E0038_CALIBRATION_FAILURE_HYPOTHESIS")
    with pytest.raises(E0040ChallengerError, match="projection identity/scope is unsafe"):
        align_e0040_calibration_challenger(
            rows,
            overlay,
            policy=policy,
            mapper_policy=mapper,
        )

    foreign = SchemaProjectionV2(
        statement_type="KQKD",
        nodes=projection.nodes,
        projection_sha256=projection.projection_sha256,
        alias_authority=projection.alias_authority,
    )
    with pytest.raises(E0040ChallengerError, match="projection identity/scope is unsafe"):
        align_e0040_calibration_challenger(
            rows,
            foreign,
            policy=policy,
            mapper_policy=mapper,
        )


def test_new_normalization_collision_is_rejected_before_mapping(
    project_root: Path,
    e0037_payload,
):
    projection = projection_from_sealed_mapping_payload(e0037_payload)
    nodes = list(projection.nodes)
    source_index = next(
        index for index, node in enumerate(nodes) if node.canonical_name == "Tiền gửi tại NHNN"
    )
    target_index = next(
        index
        for index, node in enumerate(nodes)
        if node.canonical_name == "Tiền mặt, vàng bạc, đá quý"
    )
    nodes[target_index] = replace(
        nodes[target_index],
        structural_aliases=(
            *nodes[target_index].structural_aliases,
            "Tiền gửi tại Ngân hàng Nhà nước",
        ),
    )
    assert nodes[source_index].report_norm_id != nodes[target_index].report_norm_id
    mutated_sha = _projection_digest(nodes)
    mutated_projection = SchemaProjectionV2(
        statement_type="CDKT",
        nodes=tuple(nodes),
        projection_sha256=mutated_sha,
        alias_authority=projection.alias_authority,
    )
    policy = replace(
        load_e0040_policy(project_root / _CONFIG),
        base_projection_sha256=mutated_sha,
    )

    with pytest.raises(E0040ChallengerError, match="introduces a cross-ID collision"):
        _normalized_projection(mutated_projection, policy)


def test_config_and_implementation_contain_no_sample_scoped_rules(project_root: Path):
    implementation = (
        project_root / "src/bctc_ai/mapping/e0040_calibration_challenger.py"
    ).read_text(encoding="utf-8")
    config = (project_root / _CONFIG).read_text(encoding="utf-8")
    for forbidden in (
        "page-0003",
        "page-0004",
        "MBB",
        "4375",
        "5699",
        "4311",
        "4312",
        "4319",
    ):
        assert forbidden not in implementation
        assert forbidden not in config


def test_policy_duplicate_keys_and_forged_memory_object_fail_closed(
    project_root: Path,
    frozen_challenger,
):
    source = (project_root / _CONFIG).read_bytes()
    duplicate = source.replace(b"version: 1\n", b"version: 1\nversion: 1\n", 1)
    with pytest.raises(E0040ChallengerError, match="duplicate key"):
        load_e0040_policy_bytes(duplicate, source_path=project_root / "duplicate.yaml")

    policy, mapper, rows, projection, _result, _canonical = frozen_challenger
    forged = replace(policy, minimum_group_label_score=0.65)
    with pytest.raises(E0040ChallengerError, match="differs from its source bytes"):
        align_e0040_calibration_challenger(
            rows,
            projection,
            policy=forged,
            mapper_policy=mapper,
        )


@pytest.mark.parametrize("failure", [ValueError("integer limit"), RecursionError("deep YAML")])
def test_yaml_parser_value_and_recursion_failures_are_typed_and_fail_closed(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
):
    def reject_yaml(*_args, **_kwargs):
        raise failure

    monkeypatch.setattr(challenger_module.yaml, "load", reject_yaml)
    with pytest.raises(E0040ChallengerError, match="policy YAML is invalid"):
        load_e0040_policy_bytes(
            (project_root / _CONFIG).read_bytes(),
            source_path=project_root / "parser-failure.yaml",
        )


@pytest.mark.parametrize(
    ("before", "after", "message"),
    [
        (
            b"full_form: ng\xc3\xa2n h\xc3\xa0ng nh\xc3\xa0 n\xc6\xb0\xe1\xbb\x9bc",
            b"full_form: ngan hang mau rieng",
            "generic acronym vocabulary drifted",
        ),
        (
            b"minimum_group_label_score: 0.80",
            b"minimum_group_label_score: 0.65",
            "thresholds drifted",
        ),
        (
            _BASE_PROJECTION_SHA256.encode(),
            ("a" * 64).encode(),
            "base projection identity drifted",
        ),
    ],
)
def test_policy_rejects_rule_threshold_and_identity_drift(
    project_root: Path,
    before: bytes,
    after: bytes,
    message: str,
):
    source = (project_root / _CONFIG).read_bytes()
    assert source.count(before) == 1
    mutated = source.replace(before, after, 1)
    with pytest.raises(E0040ChallengerError, match=message):
        load_e0040_policy_bytes(mutated, source_path=project_root / "mutated.yaml")
