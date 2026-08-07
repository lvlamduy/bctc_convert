from __future__ import annotations

import hashlib
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from bctc_ai.mapping.ordered_subgraph_v2 import (
    OrderedSubgraphV2Error,
    SourceStructureRowV2,
    align_ordered_subgraph_v2,
    build_schema_projection_v2,
    load_ordered_subgraph_v2_policy,
)
from bctc_ai.mapping.structural_alias_overlay import (
    StructuralAliasOverlayError,
    StructuralAliasOverlayPolicy,
    apply_structural_alias_overlay,
    load_structural_alias_overlay_bytes,
)
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import load_all

_CONFIG_RELATIVE = Path("config/mapping/e0038-cdkt-structural-alias-candidates.yaml")
_BASE_DIGEST = "7025ca729c01a3f2030af38e9745a0ee8d72b1dad60c8d4e3b7cf749e5eb860c"
_RESULT_DIGEST = "d0934db910063bdb98db83f02bc2444fc1fe6e1dce7e1ebc7e09c7d36e434283"


@pytest.fixture(scope="module")
def base_projection(project_root: Path):
    _workbooks, schema = load_all(project_root / "template", project_root)
    _registry, hierarchy = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml",
        project_root,
        schema,
    )
    apply_hierarchy_reference(schema, hierarchy)
    projection = build_schema_projection_v2(schema, "CDKT")
    assert projection.projection_sha256 == _BASE_DIGEST
    return projection


@pytest.fixture(scope="module")
def config_bytes(project_root: Path) -> bytes:
    return (project_root / _CONFIG_RELATIVE).read_bytes()


def _load(config_bytes: bytes, project_root: Path):
    return load_structural_alias_overlay_bytes(
        config_bytes,
        source_path=project_root / _CONFIG_RELATIVE,
    )


def _replace_once(payload: bytes, before: bytes, after: bytes) -> bytes:
    assert payload.count(before) == 1
    return payload.replace(before, after, 1)


def test_config_is_an_unapproved_calibration_only_immutable_snapshot(
    config_bytes: bytes,
    project_root: Path,
):
    missing_diagnostic_path = project_root / "does-not-exist-and-must-not-be-opened.yaml"
    policy = load_structural_alias_overlay_bytes(
        config_bytes,
        source_path=missing_diagnostic_path,
    )

    assert policy.source_path == missing_diagnostic_path
    assert policy.source_bytes is config_bytes
    assert policy.config_sha256 == hashlib.sha256(config_bytes).hexdigest()
    assert policy.statement_type == "CDKT"
    assert policy.base_node_count == 77
    assert policy.base_projection_sha256 == _BASE_DIGEST
    assert policy.candidate_count == 2
    assert [candidate.report_norm_id for candidate in policy.candidates] == [4375, 5699]
    assert [candidate.alias_text for candidate in policy.candidates] == [
        "TỔNG TÀI SẢN CÓ",
        "Lợi ích của cổ đông không kiểm soát",
    ]
    assert all(not candidate.production_allowed for candidate in policy.candidates)
    assert all(
        candidate.approval_status == "NOT_REVIEW_OR_STEWARD_APPROVED"
        for candidate in policy.candidates
    )


def test_overlay_is_additive_preserves_base_and_changes_only_two_nodes(
    base_projection,
    config_bytes: bytes,
    project_root: Path,
):
    base_nodes_before = base_projection.nodes
    result = apply_structural_alias_overlay(base_projection, _load(config_bytes, project_root))
    projected = result.projection

    assert base_projection.nodes is base_nodes_before
    assert base_projection.projection_sha256 == _BASE_DIGEST
    assert projected is not base_projection
    assert projected.projection_sha256 == _RESULT_DIGEST
    assert projected.alias_authority == "E0038_CALIBRATION_FAILURE_HYPOTHESIS"
    assert result.receipt.base_projection_sha256 == _BASE_DIGEST
    assert result.receipt.result_projection_sha256 == _RESULT_DIGEST
    assert result.receipt.changed_report_norm_ids == (4375, 5699)
    assert result.receipt.unchanged_node_count == 75
    assert (
        sum(
            before == after
            for before, after in zip(base_nodes_before, projected.nodes, strict=True)
        )
        == 75
    )

    before_by_id = base_projection.by_id()
    after_by_id = projected.by_id()
    assert after_by_id[4375].structural_aliases == ("TỔNG TÀI SẢN CÓ",)
    assert after_by_id[5699].structural_aliases == (
        "6. Lợi ích cổ đông không kiểm soát",
        "Lợi ích của cổ đông không kiểm soát",
    )
    for report_norm_id in set(before_by_id) - {4375, 5699}:
        assert after_by_id[report_norm_id] == before_by_id[report_norm_id]


def test_raw_all_77_scores_and_margins_are_pinned(
    base_projection,
    config_bytes: bytes,
    project_root: Path,
):
    receipt = apply_structural_alias_overlay(
        base_projection,
        _load(config_bytes, project_root),
    ).receipt
    audits = {audit.report_norm_id: audit for audit in receipt.score_audits}

    total_assets = audits[4375]
    assert total_assets.before_target_score == Decimal("0.75")
    assert total_assets.before_runner_up_report_norm_ids == (4307, 4366)
    assert total_assets.before_runner_up_score == Decimal("0.6875")
    assert total_assets.before_margin == Decimal("0.0625")
    assert total_assets.after_target_score == Decimal("1.0")
    assert total_assets.after_runner_up_report_norm_ids == (4307, 4366)
    assert total_assets.after_runner_up_score == Decimal("0.6875")
    assert total_assets.after_margin == Decimal("0.3125")

    non_controlling_interest = audits[5699]
    assert non_controlling_interest.before_target_score == Decimal("0.9393939393939393")
    assert non_controlling_interest.before_runner_up_report_norm_ids == (4306,)
    assert non_controlling_interest.before_runner_up_score == Decimal("0.7941176470588236")
    assert non_controlling_interest.before_margin == Decimal("0.1452762923351157")
    assert non_controlling_interest.after_target_score == Decimal("1.0")
    assert non_controlling_interest.after_runner_up_report_norm_ids == (4306,)
    assert non_controlling_interest.after_runner_up_score == Decimal("0.7941176470588236")
    assert non_controlling_interest.after_margin == Decimal("0.2058823529411764")


def test_collision_audit_preserves_only_two_preexisting_groups(
    base_projection,
    config_bytes: bytes,
    project_root: Path,
):
    receipt = apply_structural_alias_overlay(
        base_projection,
        _load(config_bytes, project_root),
    ).receipt
    expected = (
        ("a nguyen gia tscd", (4367, 4369, 4371)),
        ("b hao mon tscd", (4368, 4370, 4372)),
    )

    assert (
        tuple(
            (group.retrieval_key, group.report_norm_ids) for group in receipt.base_collision_groups
        )
        == expected
    )
    assert (
        tuple(
            (group.retrieval_key, group.report_norm_ids)
            for group in receipt.result_collision_groups
        )
        == expected
    )
    assert receipt.new_collision_pairs == ()
    assert receipt.collision_delta_pair_count == 0


def test_receipt_is_json_safe_and_denies_accuracy_or_production_authority(
    base_projection,
    config_bytes: bytes,
    project_root: Path,
):
    receipt = apply_structural_alias_overlay(
        base_projection,
        _load(config_bytes, project_root),
    ).receipt
    payload = receipt.to_dict()

    assert payload["status"] == "CALIBRATION_HYPOTHESIS_NOT_SCHEMA_AUTHORITY"
    assert payload["alias_authority"] == "E0038_CALIBRATION_FAILURE_HYPOTHESIS"
    assert payload["review_or_steward_approved"] is False
    assert payload["production_allowed"] is False
    assert payload["holdout_evidence_allowed"] is False
    assert payload["historical_alias_authority_allowed"] is False
    assert payload["numeric_period_or_value_features_allowed"] is False
    assert payload["score_audits"][0]["after_margin"] == "0.3125"


def test_calibration_projection_is_rejected_by_the_generic_mapper(
    base_projection,
    config_bytes: bytes,
    project_root: Path,
):
    projected = apply_structural_alias_overlay(
        base_projection,
        _load(config_bytes, project_root),
    ).projection
    policy = load_ordered_subgraph_v2_policy(
        project_root / "config/mapping/ordered-subgraph-v2.yaml"
    )
    row = SourceStructureRowV2(
        row_id="calibration-alias-row",
        order=0,
        labels_by_reader={"reader": "TỔNG TÀI SẢN CÓ"},
    )

    with pytest.raises(OrderedSubgraphV2Error, match="alias authority is unsafe"):
        align_ordered_subgraph_v2([row], projected, policy=policy)


def test_overlay_is_deterministic(
    base_projection,
    config_bytes: bytes,
    project_root: Path,
):
    first = apply_structural_alias_overlay(base_projection, _load(config_bytes, project_root))
    second = apply_structural_alias_overlay(base_projection, _load(config_bytes, project_root))

    assert first == second
    assert first.projection.nodes is not second.projection.nodes
    assert first.receipt.to_dict() == second.receipt.to_dict()


@pytest.mark.parametrize(
    ("before", "after", "message"),
    [
        (
            b"report_norm_id: 4375",
            b"report_norm_id: 999999",
            "unknown ReportNormId",
        ),
        (
            b"report_norm_id: 5699",
            b"report_norm_id: 4375",
            "duplicate target IDs",
        ),
        (
            "alias_text: TỔNG TÀI SẢN CÓ".encode(),
            "alias_text: TỔNG CỘNG TÀI SẢN".encode(),
            "redundant with its target",
        ),
        (
            "alias_text: TỔNG TÀI SẢN CÓ".encode(),
            "alias_text: TÀI SẢN".encode(),
            "introduces a new collision",
        ),
        (
            "alias_text: Lợi ích của cổ đông không kiểm soát".encode(),
            "alias_text: Lợi ích của cổ đông thiểu số".encode(),
            "insufficient raw all-node margin",
        ),
    ],
)
def test_overlay_rejects_unknown_duplicate_redundant_collision_and_weak_margin(
    base_projection,
    config_bytes: bytes,
    project_root: Path,
    before: bytes,
    after: bytes,
    message: str,
):
    mutated = _replace_once(config_bytes, before, after)
    with pytest.raises(StructuralAliasOverlayError, match=message):
        policy = _load(mutated, project_root)
        apply_structural_alias_overlay(base_projection, policy)


@pytest.mark.parametrize(
    ("before", "after", "message"),
    [
        (b"statement_type: CDKT", b"statement_type: KQKD", "pinned to CDKT"),
        (
            b"review_or_steward_approved: false",
            b"review_or_steward_approved: true",
            "unapproved calibration hypothesis",
        ),
        (
            b"production_allowed: false\n  holdout_evidence_allowed",
            b"production_allowed: true\n  holdout_evidence_allowed",
            "unapproved calibration hypothesis",
        ),
        (
            b"normalization: EXISTING_RETRIEVAL_KEY_V1_UNCHANGED",
            b"normalization: REMOVE_COMMON_TOKENS",
            "changes normalization",
        ),
        (
            b"historical_alias_authority_allowed: false",
            b"historical_alias_authority_allowed: true",
            "unapproved calibration hypothesis",
        ),
        (
            b"numeric_period_or_value_features_allowed: false",
            b"numeric_period_or_value_features_allowed: true",
            "unapproved calibration hypothesis",
        ),
        (
            b"candidate_id: CDKT_5699_NCI_POSSESSIVE_PARTICLE",
            b"candidate_id: CDKT_4375_TOTAL_ASSETS_BANKING_WORDING",
            "duplicate IDs",
        ),
        (
            "alias_text: Lợi ích của cổ đông không kiểm soát".encode(),
            "alias_text: TỔNG TÀI SẢN CÓ".encode(),
            "duplicate alias keys",
        ),
        (b"candidate_count: 2", b"candidate_count: 3", "does not match"),
    ],
)
def test_config_rejects_authority_or_identity_expansion(
    config_bytes: bytes,
    project_root: Path,
    before: bytes,
    after: bytes,
    message: str,
):
    mutated = _replace_once(config_bytes, before, after)
    with pytest.raises(StructuralAliasOverlayError, match=message):
        _load(mutated, project_root)


def test_config_rejects_duplicate_yaml_keys(config_bytes: bytes, project_root: Path):
    mutated = config_bytes.replace(b"version: 1\n", b"version: 1\nversion: 1\n", 1)

    with pytest.raises(StructuralAliasOverlayError, match="duplicate key"):
        _load(mutated, project_root)


def test_config_cannot_weaken_the_exact_margin_floor(config_bytes: bytes, project_root: Path):
    mutated = _replace_once(
        config_bytes,
        b"minimum_role_neutral_runner_up_margin: 0.15",
        b"minimum_role_neutral_runner_up_margin: 0.00",
    )

    with pytest.raises(StructuralAliasOverlayError, match="remain exactly 0.15"):
        _load(mutated, project_root)


def test_config_rejects_nonscalar_decimal_before_stringification(
    config_bytes: bytes,
    project_root: Path,
):
    mutated = _replace_once(
        config_bytes,
        b"minimum_role_neutral_runner_up_margin: 0.15",
        b"minimum_role_neutral_runner_up_margin: [0.15]",
    )

    with pytest.raises(StructuralAliasOverlayError, match="invalid minimum_role_neutral"):
        _load(mutated, project_root)


def test_config_wraps_oversized_yaml_integer_conversion(
    config_bytes: bytes,
    project_root: Path,
):
    mutated = _replace_once(
        config_bytes,
        b"minimum_role_neutral_runner_up_margin: 0.15",
        b"minimum_role_neutral_runner_up_margin: " + b"9" * 5_000,
    )

    with pytest.raises(StructuralAliasOverlayError, match="YAML is invalid"):
        _load(mutated, project_root)


def test_config_byte_budget_fails_before_yaml_parse(project_root: Path):
    with pytest.raises(StructuralAliasOverlayError, match="byte budget"):
        load_structural_alias_overlay_bytes(
            b"a" * (16 * 1024 + 1),
            source_path=project_root / "oversized.yaml",
        )


def test_bytes_subclass_cannot_split_parse_from_hash(config_bytes: bytes, project_root: Path):
    class ForgedDecodeBytes(bytes):
        def decode(self, *args, **kwargs):
            return (
                super()
                .decode(*args, **kwargs)
                .replace(
                    "TỔNG TÀI SẢN CÓ",
                    "FORGED ALIAS",
                )
            )

    with pytest.raises(StructuralAliasOverlayError, match="bytes are invalid"):
        load_structural_alias_overlay_bytes(
            ForgedDecodeBytes(config_bytes),
            source_path=project_root / "forged.yaml",
        )


def test_overlay_rejects_base_projection_identity_drift(
    base_projection,
    config_bytes: bytes,
    project_root: Path,
):
    policy = _load(config_bytes, project_root)
    drifted = replace(base_projection, projection_sha256="0" * 64)

    with pytest.raises(StructuralAliasOverlayError, match="content/hash drifted"):
        apply_structural_alias_overlay(drifted, policy)


def test_overlay_rejects_config_base_hash_drift(
    base_projection,
    config_bytes: bytes,
    project_root: Path,
):
    mutated = _replace_once(config_bytes, _BASE_DIGEST.encode(), ("f" * 64).encode())
    policy = _load(mutated, project_root)

    with pytest.raises(StructuralAliasOverlayError, match="not the pinned CDKT graph"):
        apply_structural_alias_overlay(base_projection, policy)


def test_overlay_rejects_in_memory_policy_drift(
    base_projection,
    config_bytes: bytes,
    project_root: Path,
):
    policy = _load(config_bytes, project_root)
    drifted = replace(policy, minimum_role_neutral_runner_up_margin=Decimal("0"))

    with pytest.raises(StructuralAliasOverlayError, match="differs from its source bytes"):
        apply_structural_alias_overlay(base_projection, drifted)


def test_policy_subclass_cannot_override_identity_equality(
    base_projection,
    config_bytes: bytes,
    project_root: Path,
):
    policy = _load(config_bytes, project_root)

    class AlwaysEqualPolicy(StructuralAliasOverlayPolicy):
        def __eq__(self, other):
            return True

    forged = AlwaysEqualPolicy(**policy.__dict__)
    with pytest.raises(StructuralAliasOverlayError, match="invalid type"):
        apply_structural_alias_overlay(base_projection, forged)


def test_overlay_deep_freezes_nested_projection_sequences(
    base_projection,
    config_bytes: bytes,
    project_root: Path,
):
    aliases = list(base_projection.nodes[0].structural_aliases)
    mutable_node = replace(base_projection.nodes[0], structural_aliases=aliases)
    mutable_projection = replace(
        base_projection,
        nodes=(mutable_node, *base_projection.nodes[1:]),
    )

    result = apply_structural_alias_overlay(
        mutable_projection,
        _load(config_bytes, project_root),
    )
    aliases.append("MUTATED AFTER RECEIPT")

    assert isinstance(result.projection.nodes[0].structural_aliases, tuple)
    assert "MUTATED AFTER RECEIPT" not in result.projection.nodes[0].structural_aliases
    assert result.projection.projection_sha256 == _RESULT_DIGEST


def test_overlay_rejects_projection_and_nested_sequence_budgets_before_freezing(
    base_projection,
    config_bytes: bytes,
    project_root: Path,
):
    policy = _load(config_bytes, project_root)
    oversized_projection = replace(
        base_projection,
        nodes=[*base_projection.nodes, base_projection.nodes[-1]],
    )
    with pytest.raises(StructuralAliasOverlayError, match="exceeds node budget"):
        apply_structural_alias_overlay(oversized_projection, policy)

    mutations = (
        {"structural_aliases": ["alias"] * 33},
        {"child_report_norm_ids": list(range(1, 79))},
        {"section_path": list(range(1, 18))},
        {"scopes": ["UNKNOWN"] * 9},
    )
    for mutation in mutations:
        oversized_node = replace(base_projection.nodes[0], **mutation)
        oversized_nested_projection = replace(
            base_projection,
            nodes=[oversized_node, *base_projection.nodes[1:]],
        )
        with pytest.raises(StructuralAliasOverlayError, match="sequence budget"):
            apply_structural_alias_overlay(oversized_nested_projection, policy)
