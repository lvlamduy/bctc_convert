"""Generic, calibration-only CDKT mapping challenger for E-0040.

The challenger is deliberately isolated from the sealed v2 mapper.  It builds
generic semantic keys, proves that those keys add no same-statement cross-ID
collision, and performs one bounded semantic-role repair before a second v2
alignment.  No rule in this module is scoped by bank, document, page, source
row, or ReportNormId.

Only source structure and semantic proposals are consumed.  Values, periods,
history, human-review answers, and the E-0038 ID-scoped alias overlay are not
represented by the input types and cannot participate in scoring.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml
from rapidfuzz.fuzz import ratio

from bctc_ai.core.text import retrieval_key
from bctc_ai.mapping.ordered_subgraph_v2 import (
    OrderedSubgraphV2Policy,
    OrderedSubgraphV2Result,
    RowMappingStatus,
    SchemaProjectionNodeV2,
    SchemaProjectionV2,
    SourceRowRole,
    SourceStructureRowV2,
    align_ordered_subgraph_v2,
)

_EXPECTED_MODE = "TWO_PASS_GENERIC_SEMANTIC_NORMALIZATION_AND_COMBINED_PARENT"
_EXPECTED_CALIBRATION_STATUS = "CALIBRATION_CHALLENGER_NOT_PRODUCTION_APPROVED"
_EXPECTED_DATASET_ROLE = "CALIBRATION"
_EXPECTED_MAPPER_MODE = "ANCHORED_INTERVAL_K_BEST_MONOTONE_DP_FAIL_CLOSED"
_EXPECTED_BASE_NODE_COUNT = 77
_EXPECTED_BASE_PROJECTION_SHA256 = (
    "7025ca729c01a3f2030af38e9745a0ee8d72b1dad60c8d4e3b7cf749e5eb860c"
)
_EXPECTED_MAPPER_POLICY_SHA256 = "2f18880339b8e2c04ec3ba900919f174f8af478515adfbfb0e43ff80ddd13268"
_EXPECTED_ACRONYM_RULES = (
    (("ngan", "hang", "nha", "nuoc"), "nhnn"),
    (("to", "chuc", "tin", "dung"), "tctd"),
)
_EXPECTED_PHRASE_REWRITES = (
    (("tong", "cong"), ("tong",)),
    (("tai", "san", "co"), ("tai", "san")),
)
_EXPECTED_REMOVABLE_PARTICLES = ("cua",)
_EXPECTED_SOURCE_ONLY_DISPOSITION = "SOURCE_ONLY_STRUCTURAL_ROW_HYPOTHESIS_UNMATCHED"
_MAX_CONFIG_BYTES = 64 * 1024
_MAX_SOURCE_ROWS = 4096
_MAX_SCHEMA_NODES = 4096
_MAX_RULES = 64
_MAX_TEXT_LENGTH = 512


class E0040ChallengerError(ValueError):
    """Raised when an E-0040 contract cannot be proved safely."""


class _UniqueKeySafeLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: _UniqueKeySafeLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, (str, int, float, bool, type(None), tuple)):
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable key",
                key_node.start_mark,
            )
        if key in result:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


@dataclass(frozen=True)
class TokenRewrite:
    source: tuple[str, ...]
    target: tuple[str, ...]


@dataclass(frozen=True)
class AcronymRule:
    full_form: tuple[str, ...]
    acronym: str


@dataclass(frozen=True)
class E0040Policy:
    version: int
    mode: str
    calibration_status: str
    statement_type: str
    bank_scope: str
    base_node_count: int
    base_projection_sha256: str
    required_alias_authority: str
    mapper_mode: str
    mapper_policy_sha256: str
    mapper_invocation_count: int
    acronym_rules: tuple[AcronymRule, ...]
    phrase_rewrites: tuple[TokenRewrite, ...]
    removable_particles: tuple[str, ...]
    collapse_adjacent_duplicate_acronyms: bool
    observed_role: str
    effective_role: str
    required_child_set_complete: str
    require_no_physical_parent: bool
    required_baseline_status: str
    require_all_schema_children_inside_interval: bool
    minimum_independent_reader_count: int
    minimum_group_label_score: float
    minimum_child_signature_coverage: float
    minimum_covered_child_count: int
    minimum_distinct_discriminating_token_count: int
    require_unique_passing_group: bool
    never_relax_observed_roles: tuple[str, ...]
    source_only_disposition: str
    source_path: Path
    source_bytes: bytes = field(repr=False)
    policy_sha256: str


@dataclass(frozen=True)
class E0040SourceEvidenceRow:
    row: SourceStructureRowV2
    child_set_complete: str


@dataclass(frozen=True)
class CollisionPair:
    semantic_key: str
    left_report_norm_id: int
    right_report_norm_id: int


@dataclass(frozen=True)
class CollisionAudit:
    statement_type: str
    node_count: int
    base_collision_pairs: tuple[CollisionPair, ...]
    result_collision_pairs: tuple[CollisionPair, ...]
    new_collision_pairs: tuple[CollisionPair, ...]


@dataclass(frozen=True)
class ReaderCombinedParentEvidence:
    reader_id: str
    group_label_score: float
    covered_child_report_norm_ids: tuple[int, ...]
    distinct_discriminating_token_count: int
    passes: bool


@dataclass(frozen=True)
class CombinedParentOverride:
    row_id: str
    interval_index: int
    target_report_norm_id: int
    observed_role: str
    effective_role: str
    child_set_complete: str
    reader_evidence: tuple[ReaderCombinedParentEvidence, ...]
    supporting_reader_ids: tuple[str, ...]


@dataclass(frozen=True)
class SourceOnlyStructuralDisposition:
    row_id: str
    observed_role: str
    final_mapping_status: str
    disposition: str
    selected_report_norm_id: None = None


@dataclass(frozen=True)
class NormalizationReceipt:
    statement_type: str
    bank_scope: str
    base_projection_sha256: str
    result_projection_sha256: str
    changed_schema_node_count: int
    derived_key_count: int
    id_scoped_alias_invocation_count: int
    bank_page_or_row_rule_invocation_count: int
    input_alias_authority: str
    mapper_carrier_alias_authority: str


@dataclass(frozen=True)
class E0040ChallengerResult:
    policy_sha256: str
    mapper_policy_sha256: str
    mapper_invocation_count: int
    normalization: NormalizationReceipt
    collision_audit: CollisionAudit
    combined_parent_overrides: tuple[CombinedParentOverride, ...]
    source_only_structural_rows: tuple[SourceOnlyStructuralDisposition, ...]
    baseline_selected_pairs: tuple[tuple[str, int], ...]
    final_selected_pairs: tuple[tuple[str, int], ...]
    newly_selected_pairs: tuple[tuple[str, int], ...]
    baseline_result: OrderedSubgraphV2Result
    final_result: OrderedSubgraphV2Result

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _expect_keys(payload: Mapping[str, Any], expected: set[str], context: str) -> None:
    actual = set(payload)
    if actual != expected:
        raise E0040ChallengerError(
            f"{context} keyset drifted: missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )


def _mapping(payload: Mapping[str, Any], key: str, context: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise E0040ChallengerError(f"{context} has invalid {key}")
    if any(type(item) is not str for item in value):
        raise E0040ChallengerError(f"{context}.{key} contains a non-string key")
    return value


def _required_text(payload: Mapping[str, Any], key: str, context: str) -> str:
    value = payload.get(key)
    if type(value) is not str or not value or len(value) > _MAX_TEXT_LENGTH:
        raise E0040ChallengerError(f"{context} has invalid {key}")
    return value


def _required_bool(payload: Mapping[str, Any], key: str, context: str) -> bool:
    value = payload.get(key)
    if type(value) is not bool:
        raise E0040ChallengerError(f"{context} has invalid {key}")
    return value


def _required_int(
    payload: Mapping[str, Any], key: str, context: str, *, minimum: int, maximum: int
) -> int:
    value = payload.get(key)
    if type(value) is not int or not minimum <= value <= maximum:
        raise E0040ChallengerError(f"{context} has invalid {key}")
    return value


def _required_float(
    payload: Mapping[str, Any], key: str, context: str, *, minimum: float, maximum: float
) -> float:
    value = payload.get(key)
    if isinstance(value, bool):
        raise E0040ChallengerError(f"{context} has invalid {key}")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise E0040ChallengerError(f"{context} has invalid {key}") from exc
    if not minimum <= numeric <= maximum:
        raise E0040ChallengerError(f"{context} has out-of-range {key}")
    return numeric


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_text(payload: str) -> str:
    return _sha256_bytes(payload.encode("utf-8"))


def _token_tuple(value: str, context: str) -> tuple[str, ...]:
    key = retrieval_key(value)
    tokens = tuple(key.split())
    if not tokens or any(token.isdigit() for token in tokens):
        raise E0040ChallengerError(f"{context} is not a generic non-numeric token rule")
    return tokens


def load_e0040_policy(path: Path) -> E0040Policy:
    resolved = path.resolve()
    return load_e0040_policy_bytes(resolved.read_bytes(), source_path=resolved)


def load_e0040_policy_bytes(source_bytes: bytes, *, source_path: Path) -> E0040Policy:
    if type(source_bytes) is not bytes or not source_bytes or len(source_bytes) > _MAX_CONFIG_BYTES:
        raise E0040ChallengerError("E-0040 policy bytes are invalid")
    try:
        text = source_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise E0040ChallengerError("E-0040 policy is not UTF-8") from exc
    try:
        raw = yaml.load(text, Loader=_UniqueKeySafeLoader)
    except (yaml.YAMLError, ValueError, RecursionError) as exc:
        raise E0040ChallengerError(f"E-0040 policy YAML is invalid: {exc}") from exc
    if not isinstance(raw, Mapping) or any(type(item) is not str for item in raw):
        raise E0040ChallengerError("E-0040 policy is not a string-keyed mapping")
    _expect_keys(
        raw,
        {
            "version",
            "mode",
            "calibration_status",
            "statement_type",
            "bank_scope",
            "base_projection",
            "base_mapper",
            "authority",
            "normalization",
            "collision_gate",
            "combined_parent_gate",
            "source_only_guard",
        },
        "E-0040 policy",
    )
    if raw.get("version") != 1 or raw.get("mode") != _EXPECTED_MODE:
        raise E0040ChallengerError("E-0040 policy version/mode is unsafe")
    if raw.get("calibration_status") != _EXPECTED_CALIBRATION_STATUS:
        raise E0040ChallengerError("E-0040 policy status is unsafe")
    if raw.get("statement_type") != "CDKT" or raw.get("bank_scope") != "ALL_BANKS":
        raise E0040ChallengerError("E-0040 policy must remain all-bank CDKT scoped")

    base = _mapping(raw, "base_projection", "E-0040 policy")
    _expect_keys(base, {"node_count", "sha256", "required_alias_authority"}, "base_projection")
    node_count = _required_int(base, "node_count", "base_projection", minimum=1, maximum=4096)
    base_sha = _required_text(base, "sha256", "base_projection")
    if len(base_sha) != 64 or any(char not in "0123456789abcdef" for char in base_sha):
        raise E0040ChallengerError("base_projection sha256 is invalid")
    alias_authority = _required_text(base, "required_alias_authority", "base_projection")
    if alias_authority != "CANONICAL_AND_STRUCTURAL_ALIASES_ONLY":
        raise E0040ChallengerError("E-0040 refuses an alias-overlay projection")
    if node_count != _EXPECTED_BASE_NODE_COUNT or base_sha != _EXPECTED_BASE_PROJECTION_SHA256:
        raise E0040ChallengerError("E-0040 base projection identity drifted")

    mapper = _mapping(raw, "base_mapper", "E-0040 policy")
    _expect_keys(mapper, {"mode", "policy_sha256", "invocation_count"}, "base_mapper")
    mapper_mode = _required_text(mapper, "mode", "base_mapper")
    mapper_sha = _required_text(mapper, "policy_sha256", "base_mapper")
    if (
        mapper_mode != _EXPECTED_MAPPER_MODE
        or mapper_sha != _EXPECTED_MAPPER_POLICY_SHA256
        or len(mapper_sha) != 64
        or any(char not in "0123456789abcdef" for char in mapper_sha)
    ):
        raise E0040ChallengerError("E-0040 base mapper identity is unsafe")
    mapper_invocations = _required_int(
        mapper, "invocation_count", "base_mapper", minimum=2, maximum=2
    )

    authority = _mapping(raw, "authority", "E-0040 policy")
    _expect_keys(
        authority,
        {
            "dataset_role",
            "id_scoped_alias_rules_allowed",
            "bank_page_or_row_rules_allowed",
            "historical_features_allowed",
            "numeric_period_or_unit_features_allowed",
            "review_or_steward_answers_allowed",
            "holdout_features_allowed",
            "production_allowed",
        },
        "authority",
    )
    if authority.get("dataset_role") != _EXPECTED_DATASET_ROLE:
        raise E0040ChallengerError("E-0040 dataset role is unsafe")
    for key in set(authority) - {"dataset_role"}:
        if _required_bool(authority, key, "authority"):
            raise E0040ChallengerError(f"E-0040 authority unexpectedly allows {key}")

    normalization = _mapping(raw, "normalization", "E-0040 policy")
    _expect_keys(
        normalization,
        {
            "base_key",
            "apply_symmetrically_to_source_and_schema",
            "acronym_rules",
            "phrase_rewrites",
            "removable_particles",
            "collapse_adjacent_duplicate_acronyms",
        },
        "normalization",
    )
    if normalization.get("base_key") != "RETRIEVAL_KEY_V1":
        raise E0040ChallengerError("E-0040 normalization base key drifted")
    if not _required_bool(
        normalization, "apply_symmetrically_to_source_and_schema", "normalization"
    ):
        raise E0040ChallengerError("E-0040 normalization must be symmetric")
    raw_acronyms = normalization.get("acronym_rules")
    if not isinstance(raw_acronyms, list) or not 1 <= len(raw_acronyms) <= _MAX_RULES:
        raise E0040ChallengerError("E-0040 acronym rules are invalid")
    acronym_rules: list[AcronymRule] = []
    for index, item in enumerate(raw_acronyms):
        if not isinstance(item, Mapping):
            raise E0040ChallengerError(f"acronym rule {index} is invalid")
        _expect_keys(item, {"full_form", "acronym"}, f"acronym rule {index}")
        full_form = _token_tuple(
            _required_text(item, "full_form", f"acronym rule {index}"),
            f"acronym rule {index} full_form",
        )
        acronym_tokens = _token_tuple(
            _required_text(item, "acronym", f"acronym rule {index}"),
            f"acronym rule {index} acronym",
        )
        if len(full_form) < 2 or len(acronym_tokens) != 1:
            raise E0040ChallengerError(f"acronym rule {index} is not phrase-to-token")
        acronym_rules.append(AcronymRule(full_form=full_form, acronym=acronym_tokens[0]))
    if len({item.full_form for item in acronym_rules}) != len(acronym_rules) or len(
        {item.acronym for item in acronym_rules}
    ) != len(acronym_rules):
        raise E0040ChallengerError("E-0040 acronym rules contain duplicates")
    if tuple((item.full_form, item.acronym) for item in acronym_rules) != (_EXPECTED_ACRONYM_RULES):
        raise E0040ChallengerError("E-0040 generic acronym vocabulary drifted")

    raw_rewrites = normalization.get("phrase_rewrites")
    if not isinstance(raw_rewrites, list) or not 1 <= len(raw_rewrites) <= _MAX_RULES:
        raise E0040ChallengerError("E-0040 phrase rewrites are invalid")
    phrase_rewrites: list[TokenRewrite] = []
    for index, item in enumerate(raw_rewrites):
        if not isinstance(item, Mapping):
            raise E0040ChallengerError(f"phrase rewrite {index} is invalid")
        _expect_keys(item, {"source", "target"}, f"phrase rewrite {index}")
        source = _token_tuple(
            _required_text(item, "source", f"phrase rewrite {index}"),
            f"phrase rewrite {index} source",
        )
        target = _token_tuple(
            _required_text(item, "target", f"phrase rewrite {index}"),
            f"phrase rewrite {index} target",
        )
        if source == target:
            raise E0040ChallengerError(f"phrase rewrite {index} is a no-op")
        phrase_rewrites.append(TokenRewrite(source=source, target=target))
    if len({item.source for item in phrase_rewrites}) != len(phrase_rewrites):
        raise E0040ChallengerError("E-0040 phrase rewrite sources are duplicated")
    if tuple((item.source, item.target) for item in phrase_rewrites) != (_EXPECTED_PHRASE_REWRITES):
        raise E0040ChallengerError("E-0040 generic phrase vocabulary drifted")

    raw_particles = normalization.get("removable_particles")
    if not isinstance(raw_particles, list) or not 1 <= len(raw_particles) <= _MAX_RULES:
        raise E0040ChallengerError("E-0040 removable particles are invalid")
    if any(type(item) is not str for item in raw_particles):
        raise E0040ChallengerError("E-0040 removable particles must be text")
    particles = tuple(
        _token_tuple(item, f"removable particle {index}")
        for index, item in enumerate(raw_particles)
    )
    if any(len(item) != 1 for item in particles) or len(set(particles)) != len(particles):
        raise E0040ChallengerError("E-0040 removable particles must be unique tokens")
    if tuple(item[0] for item in particles) != _EXPECTED_REMOVABLE_PARTICLES:
        raise E0040ChallengerError("E-0040 generic particle vocabulary drifted")
    collapse = _required_bool(
        normalization, "collapse_adjacent_duplicate_acronyms", "normalization"
    )
    if not collapse:
        raise E0040ChallengerError("E-0040 acronym duplicate collapse must remain enabled")

    collision = _mapping(raw, "collision_gate", "E-0040 policy")
    _expect_keys(
        collision,
        {
            "universe",
            "compare_base_keys_plus_generic_derived_keys",
            "reject_any_new_cross_id_exact_key_collision",
        },
        "collision_gate",
    )
    if collision.get("universe") != "SAME_STATEMENT_ALL_CANONICAL_AND_STRUCTURAL_KEYS":
        raise E0040ChallengerError("E-0040 collision universe is unsafe")
    if not _required_bool(
        collision, "compare_base_keys_plus_generic_derived_keys", "collision_gate"
    ) or not _required_bool(
        collision, "reject_any_new_cross_id_exact_key_collision", "collision_gate"
    ):
        raise E0040ChallengerError("E-0040 collision gate must fail closed")

    combined = _mapping(raw, "combined_parent_gate", "E-0040 policy")
    _expect_keys(
        combined,
        {
            "observed_role",
            "effective_role",
            "required_child_set_complete",
            "require_no_physical_parent",
            "required_baseline_status",
            "require_group_inside_same_baseline_interval",
            "require_all_schema_children_inside_interval",
            "minimum_independent_reader_count",
            "minimum_group_label_score",
            "minimum_child_signature_coverage",
            "minimum_covered_child_count",
            "minimum_distinct_discriminating_token_count",
            "require_unique_passing_group",
        },
        "combined_parent_gate",
    )
    if (
        combined.get("observed_role") != SourceRowRole.DETAIL.value
        or combined.get("effective_role") != SourceRowRole.GROUP.value
    ):
        raise E0040ChallengerError("E-0040 role repair must remain DETAIL-to-GROUP")
    if combined.get("required_child_set_complete") != "UNKNOWN":
        raise E0040ChallengerError("E-0040 cannot assume a complete source child set")
    if combined.get("required_baseline_status") != RowMappingStatus.BEST_PATH_SKIPPED.value:
        raise E0040ChallengerError("E-0040 baseline status gate drifted")
    for key in (
        "require_no_physical_parent",
        "require_group_inside_same_baseline_interval",
        "require_all_schema_children_inside_interval",
        "require_unique_passing_group",
    ):
        if not _required_bool(combined, key, "combined_parent_gate"):
            raise E0040ChallengerError(f"E-0040 combined-parent gate requires {key}")

    source_only = _mapping(raw, "source_only_guard", "E-0040 policy")
    _expect_keys(
        source_only,
        {
            "never_relax_observed_roles",
            "disposition",
            "automatic_report_norm_id_assignment_allowed",
        },
        "source_only_guard",
    )
    raw_never = source_only.get("never_relax_observed_roles")
    if raw_never != [SourceRowRole.SECTION.value, SourceRowRole.TOTAL.value]:
        raise E0040ChallengerError("E-0040 source-only role guard drifted")
    if _required_bool(
        source_only, "automatic_report_norm_id_assignment_allowed", "source_only_guard"
    ):
        raise E0040ChallengerError("E-0040 source-only rows cannot receive an ID")

    minimum_reader_count = _required_int(
        combined,
        "minimum_independent_reader_count",
        "combined_parent_gate",
        minimum=2,
        maximum=16,
    )
    minimum_group_score = _required_float(
        combined,
        "minimum_group_label_score",
        "combined_parent_gate",
        minimum=0.65,
        maximum=1.0,
    )
    minimum_child_coverage = _required_float(
        combined,
        "minimum_child_signature_coverage",
        "combined_parent_gate",
        minimum=0.5,
        maximum=1.0,
    )
    minimum_child_count = _required_int(
        combined,
        "minimum_covered_child_count",
        "combined_parent_gate",
        minimum=2,
        maximum=64,
    )
    minimum_token_count = _required_int(
        combined,
        "minimum_distinct_discriminating_token_count",
        "combined_parent_gate",
        minimum=1,
        maximum=128,
    )
    if (
        minimum_reader_count != 2
        or minimum_group_score != 0.8
        or minimum_child_coverage != 0.75
        or minimum_child_count != 2
        or minimum_token_count != 3
    ):
        raise E0040ChallengerError("E-0040 combined-parent thresholds drifted")
    source_only_disposition = _required_text(source_only, "disposition", "source_only_guard")
    if source_only_disposition != _EXPECTED_SOURCE_ONLY_DISPOSITION:
        raise E0040ChallengerError("E-0040 source-only disposition drifted")

    return E0040Policy(
        version=1,
        mode=_EXPECTED_MODE,
        calibration_status=_EXPECTED_CALIBRATION_STATUS,
        statement_type="CDKT",
        bank_scope="ALL_BANKS",
        base_node_count=node_count,
        base_projection_sha256=base_sha,
        required_alias_authority=alias_authority,
        mapper_mode=mapper_mode,
        mapper_policy_sha256=mapper_sha,
        mapper_invocation_count=mapper_invocations,
        acronym_rules=tuple(acronym_rules),
        phrase_rewrites=tuple(phrase_rewrites),
        removable_particles=tuple(item[0] for item in particles),
        collapse_adjacent_duplicate_acronyms=collapse,
        observed_role=SourceRowRole.DETAIL.value,
        effective_role=SourceRowRole.GROUP.value,
        required_child_set_complete="UNKNOWN",
        require_no_physical_parent=True,
        required_baseline_status=RowMappingStatus.BEST_PATH_SKIPPED.value,
        require_all_schema_children_inside_interval=True,
        minimum_independent_reader_count=minimum_reader_count,
        minimum_group_label_score=minimum_group_score,
        minimum_child_signature_coverage=minimum_child_coverage,
        minimum_covered_child_count=minimum_child_count,
        minimum_distinct_discriminating_token_count=minimum_token_count,
        require_unique_passing_group=True,
        never_relax_observed_roles=(SourceRowRole.SECTION.value, SourceRowRole.TOTAL.value),
        source_only_disposition=source_only_disposition,
        source_path=source_path.resolve(),
        source_bytes=source_bytes,
        policy_sha256=_sha256_bytes(source_bytes),
    )


def _replace_tokens(
    tokens: tuple[str, ...], source: tuple[str, ...], target: tuple[str, ...]
) -> tuple[str, ...]:
    result: list[str] = []
    index = 0
    while index < len(tokens):
        if tokens[index : index + len(source)] == source:
            result.extend(target)
            index += len(source)
        else:
            result.append(tokens[index])
            index += 1
    return tuple(result)


def semantic_key(value: str, policy: E0040Policy) -> str:
    """Return the generic statement-scoped key used by both sides."""

    tokens = tuple(retrieval_key(value).split())
    for rule in sorted(
        policy.acronym_rules, key=lambda item: (-len(item.full_form), item.full_form)
    ):
        tokens = _replace_tokens(tokens, rule.full_form, (rule.acronym,))
    for rule in sorted(policy.phrase_rewrites, key=lambda item: (-len(item.source), item.source)):
        tokens = _replace_tokens(tokens, rule.source, rule.target)
    particles = set(policy.removable_particles)
    tokens = tuple(token for token in tokens if token not in particles)
    if policy.collapse_adjacent_duplicate_acronyms:
        acronyms = {item.acronym for item in policy.acronym_rules}
        collapsed: list[str] = []
        for token in tokens:
            if collapsed and token == collapsed[-1] and token in acronyms:
                continue
            collapsed.append(token)
        tokens = tuple(collapsed)
    return " ".join(tokens)


def _projection_digest(nodes: Sequence[SchemaProjectionNodeV2]) -> str:
    serialized = [asdict(node) for node in nodes]
    return _sha256_text(
        json.dumps(serialized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )


def projection_from_sealed_mapping_payload(payload: Mapping[str, Any]) -> SchemaProjectionV2:
    """Reconstruct only the history-free projection fields from sealed mapping evidence."""

    raw = payload.get("schema_projection")
    if not isinstance(raw, Mapping):
        raise E0040ChallengerError("sealed mapping payload has no schema projection")
    nodes_raw = raw.get("nodes")
    if not isinstance(nodes_raw, list) or not nodes_raw or len(nodes_raw) > _MAX_SCHEMA_NODES:
        raise E0040ChallengerError("sealed mapping projection nodes are invalid")
    nodes: list[SchemaProjectionNodeV2] = []
    for index, item in enumerate(nodes_raw):
        if not isinstance(item, Mapping):
            raise E0040ChallengerError(f"sealed projection node {index} is invalid")
        try:
            node = SchemaProjectionNodeV2(
                report_norm_id=item["report_norm_id"],
                canonical_name=item["display_name"],
                structural_aliases=tuple(item["structural_aliases"]),
                statement_type=raw["statement_type"],
                display_order=item["display_order"],
                parent_report_norm_id=item["parent_report_norm_id"],
                child_report_norm_ids=tuple(item["child_report_norm_ids"]),
                hierarchy_level=item["hierarchy_level"],
                section_path=tuple(item["section_path"]),
                scopes=tuple(item["scopes"]),
            )
        except (KeyError, TypeError) as exc:
            raise E0040ChallengerError(f"sealed projection node {index} drifted") from exc
        nodes.append(node)
    projection = SchemaProjectionV2(
        statement_type=raw.get("statement_type"),
        nodes=tuple(nodes),
        projection_sha256=raw.get("projection_sha256"),
        alias_authority=raw.get("alias_authority"),
    )
    if _projection_digest(projection.nodes) != projection.projection_sha256:
        raise E0040ChallengerError("sealed mapping projection content/hash drifted")
    return projection


def source_rows_from_sealed_mapping_payload(
    payload: Mapping[str, Any],
) -> tuple[E0040SourceEvidenceRow, ...]:
    """Read only source structure and semantic proposals, never prior mapping decisions."""

    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, list) or not raw_rows or len(raw_rows) > _MAX_SOURCE_ROWS:
        raise E0040ChallengerError("sealed mapping source rows are invalid")
    rows: list[E0040SourceEvidenceRow] = []
    for expected_order, raw in enumerate(raw_rows):
        if not isinstance(raw, Mapping):
            raise E0040ChallengerError(f"sealed mapping source row {expected_order} is invalid")
        structure = raw.get("source_structure")
        labels = raw.get("semantic_proposals")
        if not isinstance(structure, Mapping) or not isinstance(labels, Mapping):
            raise E0040ChallengerError(f"sealed source evidence {expected_order} is incomplete")
        # Page, row ordinal, values, and the existing mapping record are intentionally
        # not read.  Source order and opaque row identity are the only ordering fields.
        row_id = raw.get("row_id")
        order = raw.get("source_order")
        parent = structure.get("physical_parent_row_id")
        relation = structure.get("mapper_relation_type")
        if (
            type(row_id) is not str
            or not row_id
            or type(order) is not int
            or order != expected_order
            or relation not in {"UNKNOWN", "DIRECT_PARENT"}
            or (relation == "DIRECT_PARENT" and type(parent) is not str)
            or (relation == "UNKNOWN" and parent is not None)
            or any(type(key) is not str or type(value) is not str for key, value in labels.items())
        ):
            raise E0040ChallengerError(f"sealed source evidence {expected_order} drifted")
        source_row = SourceStructureRowV2(
            row_id=row_id,
            order=order,
            labels_by_reader=MappingProxyType(dict(sorted(labels.items()))),
            row_role=structure.get("row_role"),
            parent_row_id=parent,
            relation_type=relation,
            report_scope=structure.get("report_scope"),
            target_template_in_scope=structure.get("target_template_in_scope"),
        )
        child_set_complete = structure.get("child_set_complete")
        if type(child_set_complete) is not str or not child_set_complete:
            raise E0040ChallengerError(f"sealed source child-set state {expected_order} drifted")
        rows.append(E0040SourceEvidenceRow(source_row, child_set_complete))
    if len({item.row.row_id for item in rows}) != len(rows):
        raise E0040ChallengerError("sealed source evidence has duplicate row IDs")
    return tuple(rows)


def _validate_projection(projection: SchemaProjectionV2, policy: E0040Policy) -> None:
    if type(projection) is not SchemaProjectionV2:
        raise E0040ChallengerError("E-0040 projection has invalid type")
    if (
        projection.statement_type != policy.statement_type
        or len(projection.nodes) != policy.base_node_count
        or len(projection.nodes) > _MAX_SCHEMA_NODES
        or projection.projection_sha256 != policy.base_projection_sha256
        or projection.alias_authority != policy.required_alias_authority
    ):
        raise E0040ChallengerError("E-0040 projection identity/scope is unsafe")
    if _projection_digest(projection.nodes) != projection.projection_sha256:
        raise E0040ChallengerError("E-0040 projection content/hash drifted")
    if tuple(sorted(projection.nodes, key=lambda node: node.display_order)) != projection.nodes:
        raise E0040ChallengerError("E-0040 projection is not workbook ordered")
    if (
        len({node.report_norm_id for node in projection.nodes}) != len(projection.nodes)
        or len({node.display_order for node in projection.nodes}) != len(projection.nodes)
        or any(node.statement_type != policy.statement_type for node in projection.nodes)
    ):
        raise E0040ChallengerError("E-0040 projection nodes are inconsistent")


def _validate_source_rows(
    rows: Sequence[E0040SourceEvidenceRow],
) -> tuple[E0040SourceEvidenceRow, ...]:
    if not rows or len(rows) > _MAX_SOURCE_ROWS:
        raise E0040ChallengerError("E-0040 source row count is invalid")
    frozen: list[E0040SourceEvidenceRow] = []
    for item in rows:
        if type(item) is not E0040SourceEvidenceRow or type(item.row) is not SourceStructureRowV2:
            raise E0040ChallengerError("E-0040 source evidence has invalid type")
        row = item.row
        if (
            type(row.row_id) is not str
            or not row.row_id
            or type(row.order) is not int
            or type(row.labels_by_reader) not in (dict, MappingProxyType)
            or not row.labels_by_reader
            or any(
                type(reader) is not str
                or not reader
                or type(label) is not str
                or len(label) > _MAX_TEXT_LENGTH
                for reader, label in row.labels_by_reader.items()
            )
            or type(item.child_set_complete) is not str
            or not item.child_set_complete
        ):
            raise E0040ChallengerError(f"E-0040 source row {row.row_id!r} is malformed")
        frozen.append(
            E0040SourceEvidenceRow(
                replace(
                    row,
                    labels_by_reader=MappingProxyType(dict(sorted(row.labels_by_reader.items()))),
                ),
                item.child_set_complete,
            )
        )
    frozen.sort(key=lambda item: item.row.order)
    if len({item.row.row_id for item in frozen}) != len(frozen) or len(
        {item.row.order for item in frozen}
    ) != len(frozen):
        raise E0040ChallengerError("E-0040 source row identity/order is duplicated")
    return tuple(frozen)


def _collision_pairs(
    projection: SchemaProjectionV2,
    policy: E0040Policy,
    *,
    include_derived: bool,
) -> tuple[CollisionPair, ...]:
    ids_by_key: dict[str, set[int]] = {}
    for node in projection.nodes:
        for text in (node.canonical_name, *node.structural_aliases):
            keys = {retrieval_key(text)}
            if include_derived:
                keys.add(semantic_key(text, policy))
            for key in keys:
                if key:
                    ids_by_key.setdefault(key, set()).add(node.report_norm_id)
    pairs = [
        CollisionPair(key, left, right)
        for key, ids in ids_by_key.items()
        for left in sorted(ids)
        for right in sorted(ids)
        if left < right
    ]
    return tuple(
        sorted(
            pairs,
            key=lambda item: (
                item.semantic_key,
                item.left_report_norm_id,
                item.right_report_norm_id,
            ),
        )
    )


def _normalized_projection(
    projection: SchemaProjectionV2, policy: E0040Policy
) -> tuple[SchemaProjectionV2, NormalizationReceipt, CollisionAudit]:
    base_pairs = _collision_pairs(projection, policy, include_derived=False)
    result_pairs = _collision_pairs(projection, policy, include_derived=True)
    base_set = set(base_pairs)
    new_pairs = tuple(item for item in result_pairs if item not in base_set)
    audit = CollisionAudit(
        statement_type=projection.statement_type,
        node_count=len(projection.nodes),
        base_collision_pairs=base_pairs,
        result_collision_pairs=result_pairs,
        new_collision_pairs=new_pairs,
    )
    if new_pairs:
        raise E0040ChallengerError("generic normalization introduces a cross-ID collision")

    changed = 0
    derived_count = 0
    nodes: list[SchemaProjectionNodeV2] = []
    for node in projection.nodes:
        aliases = list(node.structural_aliases)
        existing_keys = {retrieval_key(text) for text in (node.canonical_name, *aliases)}
        for text in (node.canonical_name, *node.structural_aliases):
            key = semantic_key(text, policy)
            if key and key not in existing_keys:
                aliases.append(key)
                existing_keys.add(key)
                derived_count += 1
        updated = replace(node, structural_aliases=tuple(aliases))
        changed += updated != node
        nodes.append(updated)
    digest = _projection_digest(nodes)
    result = SchemaProjectionV2(
        statement_type=projection.statement_type,
        nodes=tuple(nodes),
        projection_sha256=digest,
        # The v2 field describes its carrier type.  The E-0040 receipt below
        # separately and explicitly records the generic derived-key authority.
        alias_authority=projection.alias_authority,
    )
    receipt = NormalizationReceipt(
        statement_type=projection.statement_type,
        bank_scope=policy.bank_scope,
        base_projection_sha256=projection.projection_sha256,
        result_projection_sha256=digest,
        changed_schema_node_count=changed,
        derived_key_count=derived_count,
        id_scoped_alias_invocation_count=0,
        bank_page_or_row_rule_invocation_count=0,
        input_alias_authority=projection.alias_authority,
        mapper_carrier_alias_authority=result.alias_authority,
    )
    return result, receipt, audit


def _normalized_rows(
    rows: Sequence[E0040SourceEvidenceRow], policy: E0040Policy
) -> tuple[SourceStructureRowV2, ...]:
    return tuple(
        replace(
            item.row,
            labels_by_reader=MappingProxyType(
                {
                    reader: semantic_key(label, policy)
                    for reader, label in sorted(item.row.labels_by_reader.items())
                }
            ),
        )
        for item in rows
    )


def _node_keys(node: SchemaProjectionNodeV2, policy: E0040Policy) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            semantic_key(text, policy)
            for text in (node.canonical_name, *node.structural_aliases)
            if semantic_key(text, policy)
        )
    )


def _reader_parent_evidence(
    *,
    reader_id: str,
    label: str,
    group: SchemaProjectionNodeV2,
    children: Sequence[SchemaProjectionNodeV2],
    policy: E0040Policy,
) -> ReaderCombinedParentEvidence:
    source_key = semantic_key(label, policy)
    group_score = max(
        (ratio(source_key, key) / 100.0 for key in _node_keys(group, policy)),
        default=0.0,
    )
    child_token_sets = [
        set(semantic_key(child.canonical_name, policy).split()) for child in children
    ]
    common = set.intersection(*child_token_sets) if child_token_sets else set()
    signatures = [tokens - common for tokens in child_token_sets]
    source_tokens = set(source_key.split())
    covered: list[int] = []
    discriminating: set[str] = set()
    for child, signature in zip(children, signatures, strict=True):
        if not signature:
            continue
        coverage = len(source_tokens & signature) / len(signature)
        if coverage >= policy.minimum_child_signature_coverage:
            covered.append(child.report_norm_id)
            # Count only discriminating tokens actually present in the source.
            # A threshold such as 0.75 must not receive credit for the missing
            # quarter of a child signature.
            discriminating.update(source_tokens & signature)
    passes = (
        group_score >= policy.minimum_group_label_score
        and len(covered) >= policy.minimum_covered_child_count
        and len(discriminating) >= policy.minimum_distinct_discriminating_token_count
    )
    return ReaderCombinedParentEvidence(
        reader_id=reader_id,
        group_label_score=round(group_score, 6),
        covered_child_report_norm_ids=tuple(covered),
        distinct_discriminating_token_count=len(discriminating),
        passes=passes,
    )


def _discover_combined_parent_overrides(
    rows: Sequence[E0040SourceEvidenceRow],
    projection: SchemaProjectionV2,
    baseline: OrderedSubgraphV2Result,
    policy: E0040Policy,
) -> tuple[CombinedParentOverride, ...]:
    node_by_id = projection.by_id()
    mapping_by_row = {item.row_id: item for item in baseline.row_mappings}
    interval_by_index = {item.interval_index: item for item in baseline.intervals}
    overrides: list[CombinedParentOverride] = []
    for evidence in rows:
        row = evidence.row
        mapping = mapping_by_row[row.row_id]
        if (
            row.row_role != policy.observed_role
            or evidence.child_set_complete != policy.required_child_set_complete
            or row.parent_row_id is not None
            or mapping.status != policy.required_baseline_status
            or mapping.interval_index is None
        ):
            continue
        interval = interval_by_index[mapping.interval_index]
        interval_ids = set(interval.report_norm_ids)
        passing: list[tuple[SchemaProjectionNodeV2, tuple[ReaderCombinedParentEvidence, ...]]] = []
        for report_norm_id in interval.report_norm_ids:
            group = node_by_id[report_norm_id]
            if len(group.child_report_norm_ids) < policy.minimum_covered_child_count:
                continue
            if policy.require_all_schema_children_inside_interval and not set(
                group.child_report_norm_ids
            ).issubset(interval_ids):
                continue
            children = tuple(node_by_id[item] for item in group.child_report_norm_ids)
            reader_evidence = tuple(
                _reader_parent_evidence(
                    reader_id=reader,
                    label=label,
                    group=group,
                    children=children,
                    policy=policy,
                )
                for reader, label in sorted(row.labels_by_reader.items())
            )
            if (
                sum(item.passes for item in reader_evidence)
                >= policy.minimum_independent_reader_count
            ):
                passing.append((group, reader_evidence))
        if len(passing) != 1:
            continue
        group, reader_evidence = passing[0]
        supporting = tuple(item.reader_id for item in reader_evidence if item.passes)
        overrides.append(
            CombinedParentOverride(
                row_id=row.row_id,
                interval_index=mapping.interval_index,
                target_report_norm_id=group.report_norm_id,
                observed_role=policy.observed_role,
                effective_role=policy.effective_role,
                child_set_complete=evidence.child_set_complete,
                reader_evidence=reader_evidence,
                supporting_reader_ids=supporting,
            )
        )
    return tuple(overrides)


def _selected_pairs(result: OrderedSubgraphV2Result) -> tuple[tuple[str, int], ...]:
    return tuple(
        (item.row_id, item.selected_report_norm_id)
        for item in result.row_mappings
        if item.selected_report_norm_id is not None
    )


def align_e0040_calibration_challenger(
    rows: Sequence[E0040SourceEvidenceRow],
    projection: SchemaProjectionV2,
    *,
    policy: E0040Policy,
    mapper_policy: OrderedSubgraphV2Policy,
) -> E0040ChallengerResult:
    """Run the bounded two-pass challenger without reading any artifact path."""

    if type(policy) is not E0040Policy or type(policy.source_bytes) is not bytes:
        raise E0040ChallengerError("E-0040 policy has invalid in-memory type")
    canonical_policy = load_e0040_policy_bytes(
        policy.source_bytes,
        source_path=policy.source_path,
    )
    if policy != canonical_policy or _sha256_bytes(policy.source_bytes) != policy.policy_sha256:
        raise E0040ChallengerError("E-0040 in-memory policy differs from its source bytes")
    if (
        mapper_policy.mode != policy.mapper_mode
        or mapper_policy.policy_sha256 != policy.mapper_policy_sha256
        or _sha256_bytes(mapper_policy.source_bytes) != mapper_policy.policy_sha256
    ):
        raise E0040ChallengerError("E-0040 mapper policy identity drifted")
    _validate_projection(projection, policy)
    source_rows = _validate_source_rows(rows)
    normalized_projection, normalization, collision_audit = _normalized_projection(
        projection, policy
    )
    baseline_rows = _normalized_rows(source_rows, policy)
    baseline = align_ordered_subgraph_v2(
        baseline_rows,
        normalized_projection,
        policy=mapper_policy,
    )
    overrides = _discover_combined_parent_overrides(
        source_rows,
        normalized_projection,
        baseline,
        policy,
    )
    override_by_row = {item.row_id: item for item in overrides}
    final_rows = tuple(
        replace(row, row_role=policy.effective_role) if row.row_id in override_by_row else row
        for row in baseline_rows
    )
    final = align_ordered_subgraph_v2(
        final_rows,
        normalized_projection,
        policy=mapper_policy,
    )

    baseline_pairs = _selected_pairs(baseline)
    final_pairs = _selected_pairs(final)
    final_by_row = dict(final_pairs)
    if any(final_by_row.get(row_id) != report_norm_id for row_id, report_norm_id in baseline_pairs):
        raise E0040ChallengerError("E-0040 role repair changed a baseline-selected pair")
    new_pairs = tuple(item for item in final_pairs if item not in set(baseline_pairs))
    expected_new = tuple((item.row_id, item.target_report_norm_id) for item in overrides)
    if new_pairs != expected_new:
        raise E0040ChallengerError("E-0040 role repair produced an unproved new mapping")

    original_by_id = {item.row.row_id: item for item in source_rows}
    source_only = tuple(
        SourceOnlyStructuralDisposition(
            row_id=item.row_id,
            observed_role=original_by_id[item.row_id].row.row_role,
            final_mapping_status=item.status,
            disposition=policy.source_only_disposition,
        )
        for item in final.row_mappings
        if item.selected_report_norm_id is None
        and original_by_id[item.row_id].row.row_role in policy.never_relax_observed_roles
    )
    if any(item.row_id in override_by_row for item in source_only):
        raise E0040ChallengerError("E-0040 source-only guard was bypassed")

    return E0040ChallengerResult(
        policy_sha256=policy.policy_sha256,
        mapper_policy_sha256=mapper_policy.policy_sha256,
        mapper_invocation_count=2,
        normalization=normalization,
        collision_audit=collision_audit,
        combined_parent_overrides=overrides,
        source_only_structural_rows=source_only,
        baseline_selected_pairs=baseline_pairs,
        final_selected_pairs=final_pairs,
        newly_selected_pairs=new_pairs,
        baseline_result=baseline,
        final_result=final,
    )


def challenger_result_json(result: E0040ChallengerResult) -> str:
    return json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
