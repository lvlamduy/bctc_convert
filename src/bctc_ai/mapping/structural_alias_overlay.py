"""Fail-closed, calibration-only structural alias overlay for E-0038."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from decimal import Decimal
from itertools import combinations
from pathlib import Path
from typing import Any

import yaml
from rapidfuzz.fuzz import ratio
from yaml.constructor import ConstructorError

from bctc_ai.core.text import normalize_text, retrieval_key
from bctc_ai.mapping.ordered_subgraph_v2 import (
    SchemaProjectionNodeV2,
    SchemaProjectionV2,
)

_EXPECTED_MODE = "ID_SCOPED_ADDITIVE_EXACT_STRUCTURAL_ALIAS_CANDIDATES"
_EXPECTED_STATUS = "CALIBRATION_HYPOTHESIS_NOT_SCHEMA_AUTHORITY"
_EXPECTED_STATEMENT = "CDKT"
_EXPECTED_NORMALIZATION = "EXISTING_RETRIEVAL_KEY_V1_UNCHANGED"
_EXPECTED_SCORE_METHOD = "RAPIDFUZZ_RATIO_MAX_CANONICAL_AND_STRUCTURAL_ALIASES"
_EXPECTED_SCORE_COMPARISON = "RAW_DECIMAL_FROM_FLOAT_STRING_NO_ROUNDING"
_EXPECTED_COLLISION_UNIVERSE = (
    "ALL_CANONICAL_AND_STRUCTURAL_ALIAS_KEYS_ACROSS_77_NODE_BASE_PROJECTION"
)
_EXPECTED_COLLISION_BEHAVIOR = "REJECT_ANY_NEW_CROSS_ID_EXACT_RETRIEVAL_KEY_COLLISION"
_EXPECTED_PROVENANCE = "E0038_CALIBRATION_FAILURE_HYPOTHESIS"
_EXPECTED_APPROVAL_STATUS = "NOT_REVIEW_OR_STEWARD_APPROVED"
_EXPECTED_ALIAS_AUTHORITY = "CANONICAL_AND_STRUCTURAL_ALIASES_ONLY"
_EXPECTED_MINIMUM_MARGIN = Decimal("0.15")
_MAX_CONFIG_BYTES = 16 * 1024
_MAX_TEXT_LENGTH = 256
_MAX_PROJECTION_NODES = 77
_MAX_STRUCTURAL_ALIASES_PER_NODE = 32
_MAX_CHILDREN_PER_NODE = 77
_MAX_SECTION_PATH_DEPTH = 16
_MAX_SCOPES_PER_NODE = 8
_MAX_DECIMAL_TEXT_LENGTH = 64
_CANDIDATE_ID = re.compile(r"[A-Z0-9_]+")


class StructuralAliasOverlayError(ValueError):
    """Raised when an E-0038 calibration alias contract fails closed."""


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueKeySafeLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in result
        except TypeError as exc:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable mapping key",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise ConstructorError(
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
class StructuralAliasCandidate:
    candidate_id: str
    report_norm_id: int
    alias_text: str
    provenance: str
    approval_status: str
    production_allowed: bool


@dataclass(frozen=True)
class StructuralAliasOverlayPolicy:
    version: int
    mode: str
    status: str
    statement_type: str
    candidate_count: int
    base_node_count: int
    base_projection_sha256: str
    normalization: str
    target_score_must_equal: Decimal
    minimum_role_neutral_runner_up_margin: Decimal
    candidates: tuple[StructuralAliasCandidate, ...]
    source_path: Path
    source_bytes: bytes = field(repr=False)
    config_sha256: str


@dataclass(frozen=True)
class RetrievalKeyCollision:
    retrieval_key: str
    report_norm_ids: tuple[int, ...]


@dataclass(frozen=True)
class RetrievalKeyCollisionPair:
    retrieval_key: str
    left_report_norm_id: int
    right_report_norm_id: int


@dataclass(frozen=True)
class StructuralAliasScoreAudit:
    candidate_id: str
    report_norm_id: int
    alias_text: str
    alias_retrieval_key: str
    before_target_score: Decimal
    before_runner_up_report_norm_ids: tuple[int, ...]
    before_runner_up_score: Decimal
    before_margin: Decimal
    after_target_score: Decimal
    after_runner_up_report_norm_ids: tuple[int, ...]
    after_runner_up_score: Decimal
    after_margin: Decimal


@dataclass(frozen=True)
class StructuralAliasOverlayReceipt:
    status: str
    statement_type: str
    config_sha256: str
    config_size_bytes: int
    base_projection_sha256: str
    result_projection_sha256: str
    node_count: int
    changed_report_norm_ids: tuple[int, ...]
    unchanged_node_count: int
    base_collision_groups: tuple[RetrievalKeyCollision, ...]
    result_collision_groups: tuple[RetrievalKeyCollision, ...]
    new_collision_pairs: tuple[RetrievalKeyCollisionPair, ...]
    collision_delta_pair_count: int
    score_audits: tuple[StructuralAliasScoreAudit, ...]
    alias_authority: str
    review_or_steward_approved: bool
    production_allowed: bool
    holdout_evidence_allowed: bool
    historical_alias_authority_allowed: bool
    numeric_period_or_value_features_allowed: bool

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe receipt while preserving raw Decimal text."""

        return _json_safe(asdict(self))


@dataclass(frozen=True)
class StructuralAliasOverlayResult:
    projection: SchemaProjectionV2
    receipt: StructuralAliasOverlayReceipt


def _strict_policy_identity_equal(
    canonical: StructuralAliasOverlayPolicy,
    candidate: StructuralAliasOverlayPolicy,
) -> bool:
    if type(candidate) is not StructuralAliasOverlayPolicy:
        return False
    scalar_types = (
        type(candidate.version) is int,
        type(candidate.mode) is str,
        type(candidate.status) is str,
        type(candidate.statement_type) is str,
        type(candidate.candidate_count) is int,
        type(candidate.base_node_count) is int,
        type(candidate.base_projection_sha256) is str,
        type(candidate.normalization) is str,
        type(candidate.target_score_must_equal) is Decimal,
        type(candidate.minimum_role_neutral_runner_up_margin) is Decimal,
        type(candidate.candidates) is tuple,
        isinstance(candidate.source_path, Path),
        type(candidate.source_bytes) is bytes,
        type(candidate.config_sha256) is str,
    )
    if not all(scalar_types):
        return False
    for item in candidate.candidates:
        if (
            type(item) is not StructuralAliasCandidate
            or type(item.candidate_id) is not str
            or type(item.report_norm_id) is not int
            or type(item.alias_text) is not str
            or type(item.provenance) is not str
            or type(item.approval_status) is not str
            or type(item.production_allowed) is not bool
        ):
            return False
    return canonical == candidate


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _exact_keys(payload: Mapping[str, Any], expected: set[str], context: str) -> None:
    if not all(isinstance(key, str) for key in payload):
        raise StructuralAliasOverlayError(f"{context} contains a non-string key")
    actual = set(payload)
    if actual != expected:
        raise StructuralAliasOverlayError(
            f"{context} keys are invalid: missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )


def _mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise StructuralAliasOverlayError(f"structural alias config has invalid {key}")
    return value


def _required_text(payload: Mapping[str, Any], key: str, context: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise StructuralAliasOverlayError(f"{context} has invalid {key}")
    return value


def _required_positive_int(payload: Mapping[str, Any], key: str, context: str) -> int:
    value = payload.get(key)
    if type(value) is not int or value < 1 or value > 2**31 - 1:
        raise StructuralAliasOverlayError(f"{context} has invalid {key}")
    return value


def _decimal_gate(
    payload: Mapping[str, Any],
    key: str,
    context: str,
    *,
    minimum: Decimal,
    maximum: Decimal,
) -> Decimal:
    value = payload.get(key)
    if type(value) not in (int, float, str):
        raise StructuralAliasOverlayError(f"{context} has invalid {key}")
    if type(value) is str and len(value) > _MAX_DECIMAL_TEXT_LENGTH:
        raise StructuralAliasOverlayError(f"{context} has invalid {key}")
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise StructuralAliasOverlayError(f"{context} has invalid {key}") from exc
    if not result.is_finite() or not minimum <= result <= maximum:
        raise StructuralAliasOverlayError(f"{context} has out-of-range {key}")
    return result


def _parse_candidate(raw: Any, index: int) -> StructuralAliasCandidate:
    context = f"structural alias candidate {index}"
    if not isinstance(raw, Mapping):
        raise StructuralAliasOverlayError(f"{context} is not a mapping")
    _exact_keys(
        raw,
        {
            "candidate_id",
            "report_norm_id",
            "alias_text",
            "provenance",
            "approval_status",
            "production_allowed",
        },
        context,
    )
    candidate_id = _required_text(raw, "candidate_id", context)
    alias_text = _required_text(raw, "alias_text", context)
    provenance = _required_text(raw, "provenance", context)
    approval_status = _required_text(raw, "approval_status", context)
    production_allowed = raw.get("production_allowed")
    if len(candidate_id) > _MAX_TEXT_LENGTH or _CANDIDATE_ID.fullmatch(candidate_id) is None:
        raise StructuralAliasOverlayError(f"{context} has invalid candidate_id")
    if len(alias_text) > _MAX_TEXT_LENGTH:
        raise StructuralAliasOverlayError(f"{context} alias_text exceeds the text budget")
    if normalize_text(alias_text) != alias_text or not retrieval_key(alias_text):
        raise StructuralAliasOverlayError(f"{context} alias_text is not normalized non-empty text")
    if provenance != _EXPECTED_PROVENANCE:
        raise StructuralAliasOverlayError(f"{context} provenance is not a calibration hypothesis")
    if approval_status != _EXPECTED_APPROVAL_STATUS:
        raise StructuralAliasOverlayError(f"{context} approval status is unsafe")
    if production_allowed is not False:
        raise StructuralAliasOverlayError(f"{context} must not be production allowed")
    return StructuralAliasCandidate(
        candidate_id=candidate_id,
        report_norm_id=_required_positive_int(raw, "report_norm_id", context),
        alias_text=alias_text,
        provenance=provenance,
        approval_status=approval_status,
        production_allowed=False,
    )


def load_structural_alias_overlay_bytes(
    source_bytes: bytes,
    *,
    source_path: Path,
) -> StructuralAliasOverlayPolicy:
    """Parse config semantics and identity from one caller-supplied byte snapshot.

    This function never opens ``source_path``. The path is diagnostic provenance
    only, so parsing and SHA-256 identity cannot observe different file versions.
    """

    if type(source_bytes) is not bytes:
        raise StructuralAliasOverlayError("structural alias config bytes are invalid")
    if not source_bytes or len(source_bytes) > _MAX_CONFIG_BYTES:
        raise StructuralAliasOverlayError("structural alias config exceeds the byte budget")
    try:
        text = source_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StructuralAliasOverlayError("structural alias config is not UTF-8") from exc
    try:
        loaded = yaml.load(text, Loader=_UniqueKeySafeLoader)
    except (yaml.YAMLError, RecursionError, ValueError) as exc:
        raise StructuralAliasOverlayError(
            f"structural alias config YAML is invalid: {exc}"
        ) from exc
    if not isinstance(loaded, Mapping):
        raise StructuralAliasOverlayError("structural alias config is not a mapping")
    payload = loaded
    _exact_keys(
        payload,
        {
            "version",
            "mode",
            "status",
            "statement_type",
            "candidate_count",
            "base_projection",
            "normalization",
            "score_audit",
            "collision_gate",
            "authority",
            "candidates",
        },
        "structural alias config",
    )

    base = _mapping(payload, "base_projection")
    _exact_keys(base, {"node_count", "sha256"}, "base_projection")
    score = _mapping(payload, "score_audit")
    _exact_keys(
        score,
        {
            "method",
            "target_score_must_equal",
            "minimum_role_neutral_runner_up_margin",
            "comparison",
        },
        "score_audit",
    )
    collision = _mapping(payload, "collision_gate")
    _exact_keys(collision, {"universe", "behavior"}, "collision_gate")
    authority = _mapping(payload, "authority")
    _exact_keys(
        authority,
        {
            "source",
            "review_or_steward_approved",
            "production_allowed",
            "holdout_evidence_allowed",
            "historical_alias_authority_allowed",
            "numeric_period_or_value_features_allowed",
        },
        "authority",
    )

    version = payload.get("version")
    candidate_count = payload.get("candidate_count")
    raw_candidates = payload.get("candidates")
    if version != 1 or isinstance(version, bool):
        raise StructuralAliasOverlayError("structural alias config version is unsafe")
    if payload.get("mode") != _EXPECTED_MODE:
        raise StructuralAliasOverlayError("structural alias config mode is unsafe")
    if payload.get("status") != _EXPECTED_STATUS:
        raise StructuralAliasOverlayError("structural alias config status is unsafe")
    if payload.get("statement_type") != _EXPECTED_STATEMENT:
        raise StructuralAliasOverlayError("structural alias config must be pinned to CDKT")
    if payload.get("normalization") != _EXPECTED_NORMALIZATION:
        raise StructuralAliasOverlayError("structural alias config changes normalization")
    if isinstance(candidate_count, bool) or not isinstance(candidate_count, int):
        raise StructuralAliasOverlayError("structural alias candidate_count is invalid")
    if not isinstance(raw_candidates, list) or candidate_count != len(raw_candidates):
        raise StructuralAliasOverlayError("structural alias candidate_count does not match")

    if score.get("method") != _EXPECTED_SCORE_METHOD:
        raise StructuralAliasOverlayError("structural alias score method is unsafe")
    if score.get("comparison") != _EXPECTED_SCORE_COMPARISON:
        raise StructuralAliasOverlayError("structural alias score comparison is unsafe")
    target_score = _decimal_gate(
        score,
        "target_score_must_equal",
        "score_audit",
        minimum=Decimal(0),
        maximum=Decimal(1),
    )
    if target_score != Decimal(1):
        raise StructuralAliasOverlayError("structural alias target score must remain exactly one")
    minimum_margin = _decimal_gate(
        score,
        "minimum_role_neutral_runner_up_margin",
        "score_audit",
        minimum=Decimal(0),
        maximum=Decimal(1),
    )
    if minimum_margin != _EXPECTED_MINIMUM_MARGIN:
        raise StructuralAliasOverlayError(
            "structural alias minimum runner-up margin must remain exactly 0.15"
        )

    if collision.get("universe") != _EXPECTED_COLLISION_UNIVERSE:
        raise StructuralAliasOverlayError("structural alias collision universe is unsafe")
    if collision.get("behavior") != _EXPECTED_COLLISION_BEHAVIOR:
        raise StructuralAliasOverlayError("structural alias collision behavior is unsafe")
    expected_authority = {
        "source": _EXPECTED_PROVENANCE,
        "review_or_steward_approved": False,
        "production_allowed": False,
        "holdout_evidence_allowed": False,
        "historical_alias_authority_allowed": False,
        "numeric_period_or_value_features_allowed": False,
    }
    if dict(authority) != expected_authority:
        raise StructuralAliasOverlayError(
            "structural alias authority must remain an unapproved calibration hypothesis"
        )

    node_count = _required_positive_int(base, "node_count", "base_projection")
    if node_count != 77:
        raise StructuralAliasOverlayError("structural alias base projection must contain 77 nodes")
    base_sha256 = _required_text(base, "sha256", "base_projection")
    if re.fullmatch(r"[0-9a-f]{64}", base_sha256) is None:
        raise StructuralAliasOverlayError("structural alias base projection SHA-256 is invalid")

    candidates = tuple(_parse_candidate(raw, index) for index, raw in enumerate(raw_candidates))
    if candidate_count != 2:
        raise StructuralAliasOverlayError("E-0038 requires exactly two alias candidates")
    if len({item.candidate_id for item in candidates}) != len(candidates):
        raise StructuralAliasOverlayError("structural alias candidates have duplicate IDs")
    if len({item.report_norm_id for item in candidates}) != len(candidates):
        raise StructuralAliasOverlayError("structural alias candidates have duplicate target IDs")
    if len({retrieval_key(item.alias_text) for item in candidates}) != len(candidates):
        raise StructuralAliasOverlayError("structural alias candidates have duplicate alias keys")

    return StructuralAliasOverlayPolicy(
        version=1,
        mode=_EXPECTED_MODE,
        status=_EXPECTED_STATUS,
        statement_type=_EXPECTED_STATEMENT,
        candidate_count=candidate_count,
        base_node_count=node_count,
        base_projection_sha256=base_sha256,
        normalization=_EXPECTED_NORMALIZATION,
        target_score_must_equal=target_score,
        minimum_role_neutral_runner_up_margin=minimum_margin,
        candidates=candidates,
        source_path=source_path,
        source_bytes=source_bytes,
        config_sha256=hashlib.sha256(source_bytes).hexdigest(),
    )


def _projection_digest(nodes: Sequence[SchemaProjectionNodeV2]) -> str:
    return hashlib.sha256(
        json.dumps(
            [asdict(node) for node in nodes],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _freeze_projection_node(node: object) -> SchemaProjectionNodeV2:
    if type(node) is not SchemaProjectionNodeV2:
        raise StructuralAliasOverlayError("structural alias base projection has a foreign node")
    if (
        type(node.report_norm_id) is not int
        or node.report_norm_id <= 0
        or type(node.canonical_name) is not str
        or not node.canonical_name
        or len(node.canonical_name) > 512
        or type(node.statement_type) is not str
        or type(node.display_order) is not int
        or node.display_order < 0
        or (node.parent_report_norm_id is not None and type(node.parent_report_norm_id) is not int)
        or (node.hierarchy_level is not None and type(node.hierarchy_level) is not int)
    ):
        raise StructuralAliasOverlayError("structural alias base projection node is malformed")
    sequence_fields = (
        node.structural_aliases,
        node.child_report_norm_ids,
        node.section_path,
        node.scopes,
    )
    if any(type(value) not in (list, tuple) for value in sequence_fields):
        raise StructuralAliasOverlayError(
            "structural alias base projection node has a non-freezable sequence"
        )
    if (
        len(node.structural_aliases) > _MAX_STRUCTURAL_ALIASES_PER_NODE
        or len(node.child_report_norm_ids) > _MAX_CHILDREN_PER_NODE
        or len(node.section_path) > _MAX_SECTION_PATH_DEPTH
        or len(node.scopes) > _MAX_SCOPES_PER_NODE
    ):
        raise StructuralAliasOverlayError(
            "structural alias base projection node exceeds a sequence budget"
        )
    aliases = tuple(node.structural_aliases)
    child_ids = tuple(node.child_report_norm_ids)
    section_path = tuple(node.section_path)
    scopes = tuple(node.scopes)
    if (
        any(type(value) is not str or not value or len(value) > 512 for value in aliases)
        or any(type(value) is not int or value <= 0 for value in child_ids)
        or any(type(value) is not int or value <= 0 for value in section_path)
        or any(type(value) is not str or not value or len(value) > 64 for value in scopes)
    ):
        raise StructuralAliasOverlayError(
            "structural alias base projection node has invalid sequence content"
        )
    return SchemaProjectionNodeV2(
        report_norm_id=node.report_norm_id,
        canonical_name=node.canonical_name,
        structural_aliases=aliases,
        statement_type=node.statement_type,
        display_order=node.display_order,
        parent_report_norm_id=node.parent_report_norm_id,
        child_report_norm_ids=child_ids,
        hierarchy_level=node.hierarchy_level,
        section_path=section_path,
        scopes=scopes,
    )


def _validated_base_nodes(
    projection: SchemaProjectionV2,
    policy: StructuralAliasOverlayPolicy,
) -> tuple[SchemaProjectionNodeV2, ...]:
    if type(projection) is not SchemaProjectionV2:
        raise StructuralAliasOverlayError("structural alias base projection has invalid type")
    if (
        type(projection.statement_type) is not str
        or type(projection.projection_sha256) is not str
        or type(projection.alias_authority) is not str
        or type(projection.nodes) not in (list, tuple)
    ):
        raise StructuralAliasOverlayError("structural alias base projection metadata is malformed")
    if len(projection.nodes) > _MAX_PROJECTION_NODES:
        raise StructuralAliasOverlayError("structural alias base projection exceeds node budget")
    raw_nodes = tuple(projection.nodes)
    nodes = tuple(_freeze_projection_node(node) for node in raw_nodes)
    if projection.statement_type != policy.statement_type:
        raise StructuralAliasOverlayError("structural alias base projection statement drifted")
    if projection.alias_authority != _EXPECTED_ALIAS_AUTHORITY:
        raise StructuralAliasOverlayError("structural alias base projection authority is unsafe")
    if len(nodes) != policy.base_node_count:
        raise StructuralAliasOverlayError("structural alias base projection node count drifted")
    if any(node.statement_type != policy.statement_type for node in nodes):
        raise StructuralAliasOverlayError("structural alias base projection has a foreign node")
    if len({node.report_norm_id for node in nodes}) != len(nodes):
        raise StructuralAliasOverlayError("structural alias base projection has duplicate IDs")
    if len({node.display_order for node in nodes}) != len(nodes):
        raise StructuralAliasOverlayError("structural alias base projection has duplicate order")
    if tuple(sorted(nodes, key=lambda item: item.display_order)) != nodes:
        raise StructuralAliasOverlayError(
            "structural alias base projection is not workbook ordered"
        )
    actual_digest = _projection_digest(nodes)
    if actual_digest != projection.projection_sha256:
        raise StructuralAliasOverlayError("structural alias base projection content/hash drifted")
    if actual_digest != policy.base_projection_sha256:
        raise StructuralAliasOverlayError(
            "structural alias base projection is not the pinned CDKT graph"
        )
    return nodes


def _collision_groups(
    nodes: Sequence[SchemaProjectionNodeV2],
) -> tuple[RetrievalKeyCollision, ...]:
    members: dict[str, set[int]] = defaultdict(set)
    for node in nodes:
        for text in (node.canonical_name, *node.structural_aliases):
            key = retrieval_key(text)
            if key:
                members[key].add(node.report_norm_id)
    return tuple(
        RetrievalKeyCollision(key, tuple(sorted(ids)))
        for key, ids in sorted(members.items())
        if len(ids) > 1
    )


def _collision_pairs(
    groups: Sequence[RetrievalKeyCollision],
) -> set[RetrievalKeyCollisionPair]:
    return {
        RetrievalKeyCollisionPair(group.retrieval_key, left, right)
        for group in groups
        for left, right in combinations(group.report_norm_ids, 2)
    }


def _raw_label_score(label: str, node: SchemaProjectionNodeV2) -> Decimal:
    left = retrieval_key(label)
    rights = tuple(retrieval_key(text) for text in (node.canonical_name, *node.structural_aliases))
    if not left or not any(rights):
        return Decimal(0)
    return Decimal(str(max(ratio(left, right) / 100.0 for right in rights if right)))


def _score_snapshot(
    alias_text: str,
    target_id: int,
    nodes: Sequence[SchemaProjectionNodeV2],
) -> tuple[Decimal, tuple[int, ...], Decimal, Decimal]:
    by_id = {node.report_norm_id: node for node in nodes}
    target_score = _raw_label_score(alias_text, by_id[target_id])
    alternatives = tuple(
        (_raw_label_score(alias_text, node), node.display_order, node.report_norm_id)
        for node in nodes
        if node.report_norm_id != target_id
    )
    runner_score = max(score for score, _order, _report_norm_id in alternatives)
    runner_ids = tuple(
        report_norm_id
        for score, _order, report_norm_id in sorted(alternatives, key=lambda item: item[1])
        if score == runner_score
    )
    return target_score, runner_ids, runner_score, target_score - runner_score


def _score_audit(
    candidate: StructuralAliasCandidate,
    base_nodes: Sequence[SchemaProjectionNodeV2],
    result_nodes: Sequence[SchemaProjectionNodeV2],
    policy: StructuralAliasOverlayPolicy,
) -> StructuralAliasScoreAudit:
    before = _score_snapshot(candidate.alias_text, candidate.report_norm_id, base_nodes)
    after = _score_snapshot(candidate.alias_text, candidate.report_norm_id, result_nodes)
    if after[0] != policy.target_score_must_equal:
        raise StructuralAliasOverlayError(
            f"candidate {candidate.candidate_id} does not produce an exact target score"
        )
    if after[3] < policy.minimum_role_neutral_runner_up_margin:
        raise StructuralAliasOverlayError(
            f"candidate {candidate.candidate_id} has insufficient raw all-node margin"
        )
    return StructuralAliasScoreAudit(
        candidate_id=candidate.candidate_id,
        report_norm_id=candidate.report_norm_id,
        alias_text=candidate.alias_text,
        alias_retrieval_key=retrieval_key(candidate.alias_text),
        before_target_score=before[0],
        before_runner_up_report_norm_ids=before[1],
        before_runner_up_score=before[2],
        before_margin=before[3],
        after_target_score=after[0],
        after_runner_up_report_norm_ids=after[1],
        after_runner_up_score=after[2],
        after_margin=after[3],
    )


def apply_structural_alias_overlay(
    base_projection: SchemaProjectionV2,
    policy: StructuralAliasOverlayPolicy,
) -> StructuralAliasOverlayResult:
    """Add authenticated calibration aliases without mutating the base graph.

    The overlay is lexical only. It cannot change canonical labels, workbook
    order, hierarchy, scope, or any other v2 structural field.
    """

    if type(policy) is not StructuralAliasOverlayPolicy:
        raise StructuralAliasOverlayError("structural alias in-memory policy has invalid type")
    if type(policy.source_bytes) is not bytes:
        raise StructuralAliasOverlayError("structural alias policy bytes have invalid type")
    canonical_policy = load_structural_alias_overlay_bytes(
        policy.source_bytes,
        source_path=policy.source_path,
    )
    if not _strict_policy_identity_equal(canonical_policy, policy):
        raise StructuralAliasOverlayError(
            "structural alias in-memory policy differs from its source bytes"
        )
    policy = canonical_policy

    base_nodes = _validated_base_nodes(base_projection, policy)
    by_id = {node.report_norm_id: node for node in base_nodes}
    additions: dict[int, str] = {}
    for candidate in policy.candidates:
        node = by_id.get(candidate.report_norm_id)
        if node is None:
            raise StructuralAliasOverlayError(
                f"candidate {candidate.candidate_id} targets an unknown ReportNormId"
            )
        alias_key = retrieval_key(candidate.alias_text)
        target_keys = {
            retrieval_key(text) for text in (node.canonical_name, *node.structural_aliases)
        }
        if alias_key in target_keys:
            raise StructuralAliasOverlayError(
                f"candidate {candidate.candidate_id} is redundant with its target"
            )
        additions[candidate.report_norm_id] = candidate.alias_text

    result_nodes = tuple(
        replace(node, structural_aliases=(*node.structural_aliases, additions[node.report_norm_id]))
        if node.report_norm_id in additions
        else node
        for node in base_nodes
    )
    base_collisions = _collision_groups(base_nodes)
    result_collisions = _collision_groups(result_nodes)
    new_collision_pairs = tuple(
        sorted(
            _collision_pairs(result_collisions) - _collision_pairs(base_collisions),
            key=lambda item: (
                item.retrieval_key,
                item.left_report_norm_id,
                item.right_report_norm_id,
            ),
        )
    )
    if new_collision_pairs:
        raise StructuralAliasOverlayError("structural alias overlay introduces a new collision")

    result_digest = _projection_digest(result_nodes)
    result_projection = replace(
        base_projection,
        nodes=result_nodes,
        projection_sha256=result_digest,
        alias_authority=_EXPECTED_PROVENANCE,
    )
    audits = tuple(
        _score_audit(candidate, base_nodes, result_nodes, policy) for candidate in policy.candidates
    )
    changed_ids = tuple(
        node.report_norm_id
        for before, node in zip(base_nodes, result_nodes, strict=True)
        if before != node
    )
    receipt = StructuralAliasOverlayReceipt(
        status=policy.status,
        statement_type=policy.statement_type,
        config_sha256=policy.config_sha256,
        config_size_bytes=len(policy.source_bytes),
        base_projection_sha256=base_projection.projection_sha256,
        result_projection_sha256=result_digest,
        node_count=len(result_nodes),
        changed_report_norm_ids=changed_ids,
        unchanged_node_count=len(result_nodes) - len(changed_ids),
        base_collision_groups=base_collisions,
        result_collision_groups=result_collisions,
        new_collision_pairs=new_collision_pairs,
        collision_delta_pair_count=len(new_collision_pairs),
        score_audits=audits,
        alias_authority=_EXPECTED_PROVENANCE,
        review_or_steward_approved=False,
        production_allowed=False,
        holdout_evidence_allowed=False,
        historical_alias_authority_allowed=False,
        numeric_period_or_value_features_allowed=False,
    )
    return StructuralAliasOverlayResult(projection=result_projection, receipt=receipt)
