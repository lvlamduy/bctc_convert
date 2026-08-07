from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from rapidfuzz.fuzz import ratio

from bctc_ai.core.text import normalize_text, retrieval_key
from bctc_ai.schema.registry import SchemaItem

_EXPECTED_MODE = "ANCHORED_INTERVAL_K_BEST_MONOTONE_DP_FAIL_CLOSED"
_UNKNOWN = "UNKNOWN"


class OrderedSubgraphV2Error(ValueError):
    """Raised when v2 input or policy evidence violates its sealed contract."""


class SourceRowRole(StrEnum):
    UNKNOWN = "UNKNOWN"
    DETAIL = "DETAIL"
    GROUP = "GROUP"
    TOTAL = "TOTAL"
    SECTION = "SECTION"


class SourceRelationType(StrEnum):
    UNKNOWN = "UNKNOWN"
    DIRECT_PARENT = "DIRECT_PARENT"


class MappingRunStatus(StrEnum):
    RESOLVED = "RESOLVED"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"


class RowMappingStatus(StrEnum):
    RESOLVED_ANCHOR = "RESOLVED_ANCHOR"
    RESOLVED_PATH = "RESOLVED_PATH"
    NO_ADMISSIBLE_PAIR = "NO_ADMISSIBLE_PAIR"
    BEST_PATH_SKIPPED = "BEST_PATH_SKIPPED"
    AMBIGUOUS_ACROSS_PATHS = "AMBIGUOUS_ACROSS_PATHS"
    OUT_OF_SCOPE_FOR_TARGET_TEMPLATE = "OUT_OF_SCOPE_FOR_TARGET_TEMPLATE"


@dataclass(frozen=True)
class OrderedSubgraphV2Policy:
    version: int
    mode: str
    calibration_status: str
    ordering_authority: str
    minimum_anchor_stream_score: float
    minimum_anchor_stream_margin: float
    minimum_anchor_streams: int
    minimum_strong_label_score: float
    minimum_parent_relaxed_label_score: float
    parent_relaxed_relation_type: str
    minimum_interval_margin: float
    beam_width: int
    returned_path_limit: int
    parent_corroboration_gain: float
    trailing_aggregate_ids: tuple[int, ...]
    source_path: Path
    source_bytes: bytes = field(repr=False)
    policy_sha256: str


@dataclass(frozen=True)
class SchemaProjectionNodeV2:
    """History-free workbook/hierarchy/scope projection consumed by v2."""

    report_norm_id: int
    canonical_name: str
    structural_aliases: tuple[str, ...]
    statement_type: str
    display_order: int
    parent_report_norm_id: int | None
    child_report_norm_ids: tuple[int, ...]
    hierarchy_level: int | None
    section_path: tuple[int, ...]
    scopes: tuple[str, ...]


@dataclass(frozen=True)
class SchemaProjectionV2:
    statement_type: str
    nodes: tuple[SchemaProjectionNodeV2, ...]
    projection_sha256: str
    alias_authority: str = "CANONICAL_AND_STRUCTURAL_ALIASES_ONLY"

    def by_id(self) -> dict[int, SchemaProjectionNodeV2]:
        return {node.report_norm_id: node for node in self.nodes}


@dataclass(frozen=True)
class SourceStructureRowV2:
    """Sealed structural row plus independent semantic-reader proposals.

    The mapper deliberately has no value, period, history, human-review, or
    source-path fields. ``labels_by_reader`` is the only semantic input.
    """

    row_id: str
    order: int
    labels_by_reader: Mapping[str, str]
    row_role: str = SourceRowRole.UNKNOWN.value
    parent_row_id: str | None = None
    relation_type: str = SourceRelationType.UNKNOWN.value
    report_scope: str = _UNKNOWN
    target_template_in_scope: bool = True


@dataclass(frozen=True)
class ReaderScoreDiagnostic:
    reader_id: str
    report_norm_id: int
    score: float


@dataclass(frozen=True)
class AnchorStreamDiagnostic:
    reader_id: str
    best_report_norm_id: int | None
    best_score: float | None
    runner_up_report_norm_id: int | None
    runner_up_score: float | None
    margin: float | None
    valid: bool
    reason: str


@dataclass(frozen=True)
class AnchorDiagnostic:
    row_id: str
    status: str
    selected_report_norm_id: int | None
    stream_diagnostics: tuple[AnchorStreamDiagnostic, ...]
    reason: str
    constraint_report_norm_id: int | None = None
    counterfactual_margin: float | None = None
    selection_allowed: bool = False
    aggregate_label_score: float | None = None
    counterfactual_alternative_report_norm_id: int | None = None
    counterfactual_alternative_aggregate_label_score: float | None = None


@dataclass(frozen=True)
class CandidatePairDiagnostic:
    row_id: str
    report_norm_id: int
    aggregate_label_score: float
    reader_scores: tuple[ReaderScoreDiagnostic, ...]
    admissibility: str
    role_compatibility: str
    scope_compatibility: str
    requires_mapped_direct_parent: bool
    evidence_baseline: float
    base_evidence_gain: float


@dataclass(frozen=True)
class PathMatchDiagnostic:
    row_id: str
    report_norm_id: int
    row_order: int
    schema_display_order: int
    aggregate_label_score: float
    admissibility: str
    evidence_gain: float
    direct_parent_corroborated: bool


@dataclass(frozen=True)
class RankedPathDiagnostic:
    rank: int
    total_score: float
    adjacency_tiebreak_count: int
    matches: tuple[PathMatchDiagnostic, ...]
    skipped_row_ids: tuple[str, ...]
    skipped_report_norm_ids: tuple[int, ...]
    structural_issues: tuple[str, ...]


@dataclass(frozen=True)
class CounterfactualDiagnostic:
    row_id: str
    selected_report_norm_id: int
    selected_path_score: float
    alternative_path_score: float
    alternative_report_norm_id: int | None
    alternative_skips_row: bool
    exclusion_margin: float
    stable: bool


@dataclass(frozen=True)
class IntervalDiagnostic:
    interval_index: int
    previous_anchor_row_id: str | None
    previous_anchor_report_norm_id: int | None
    next_anchor_row_id: str | None
    next_anchor_report_norm_id: int | None
    row_ids: tuple[str, ...]
    report_norm_ids: tuple[int, ...]
    status: str
    automatic_selection_allowed: bool
    best_path: RankedPathDiagnostic
    runner_up_path: RankedPathDiagnostic | None
    score_margin: float | None
    ranked_paths: tuple[RankedPathDiagnostic, ...]
    counterfactuals: tuple[CounterfactualDiagnostic, ...]
    candidate_pairs: tuple[CandidatePairDiagnostic, ...]
    structural_issues: tuple[str, ...]
    main_search_pruned_states: int
    counterfactual_search_pruned_states: int
    search_exhaustive: bool
    reason: str


@dataclass(frozen=True)
class RowMappingRecordV2:
    row_id: str
    status: str
    selected_report_norm_id: int | None
    candidate_report_norm_ids: tuple[int, ...]
    interval_index: int | None
    reason: str


@dataclass(frozen=True)
class SchemaDispositionV2:
    report_norm_id: int
    status: str
    selected_row_id: str | None
    candidate_row_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class SearchStatsV2:
    algorithm: str
    intervals: int
    dp_cells: int
    generated_states: int
    retained_states: int
    pruned_states: int
    main_search_pruned_states: int
    counterfactual_search_pruned_states: int
    counterfactual_searches: int
    beam_width_per_dp_cell: int


@dataclass(frozen=True)
class OrderedSubgraphV2Result:
    status: MappingRunStatus
    automatic_selection_allowed: bool
    anchors: tuple[AnchorDiagnostic, ...]
    intervals: tuple[IntervalDiagnostic, ...]
    best_path: RankedPathDiagnostic
    runner_up_path: RankedPathDiagnostic | None
    score_margin: float | None
    ranked_paths: tuple[RankedPathDiagnostic, ...]
    row_mappings: tuple[RowMappingRecordV2, ...]
    schema_dispositions: tuple[SchemaDispositionV2, ...]
    reason: str
    schema_projection_sha256: str
    schema_alias_authority: str
    policy_sha256: str
    search: SearchStatsV2

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class _AnchorProposal:
    row_id: str
    report_norm_id: int
    stream_diagnostics: tuple[AnchorStreamDiagnostic, ...]


@dataclass(frozen=True)
class _Interval:
    index: int
    previous_anchor: _AnchorProposal | None
    next_anchor: _AnchorProposal | None
    rows: tuple[SourceStructureRowV2, ...]
    nodes: tuple[SchemaProjectionNodeV2, ...]


@dataclass(frozen=True)
class _PathState:
    score: Decimal
    adjacency_count: int
    matches: tuple[PathMatchDiagnostic, ...]
    matched_indices: tuple[tuple[int, int], ...]
    structural_issues: tuple[str, ...] = ()

    @property
    def signature(self) -> tuple[tuple[str, int], ...]:
        return tuple((item.row_id, item.report_norm_id) for item in self.matches)


@dataclass(frozen=True)
class _SearchOutcome:
    paths: tuple[RankedPathDiagnostic, ...]
    raw_scores: tuple[Decimal, ...]
    dp_cells: int
    generated_states: int
    retained_states: int
    pruned_states: int


@dataclass(frozen=True)
class _CandidatePair:
    diagnostic: CandidatePairDiagnostic
    raw_base_evidence_gain: Decimal


def _mapping(payload: Mapping[str, Any], key: str, source: Path) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise OrderedSubgraphV2Error(f"ordered-subgraph v2 policy has invalid {key}: {source}")
    return value


def _bounded_float(
    payload: Mapping[str, Any],
    key: str,
    source: Path,
    *,
    minimum: float,
    maximum: float,
) -> float:
    value = payload.get(key)
    if isinstance(value, bool):
        raise OrderedSubgraphV2Error(f"ordered-subgraph v2 policy has invalid {key}: {source}")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise OrderedSubgraphV2Error(
            f"ordered-subgraph v2 policy has invalid {key}: {source}"
        ) from exc
    if not minimum <= numeric <= maximum:
        raise OrderedSubgraphV2Error(f"ordered-subgraph v2 policy has out-of-range {key}: {source}")
    return numeric


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def load_ordered_subgraph_v2_policy(path: Path) -> OrderedSubgraphV2Policy:
    """Load policy fields and identity from one immutable byte snapshot."""

    resolved = path.resolve()
    return load_ordered_subgraph_v2_policy_bytes(
        resolved.read_bytes(),
        source_path=resolved,
    )


def load_ordered_subgraph_v2_policy_bytes(
    source_bytes: bytes,
    *,
    source_path: Path,
) -> OrderedSubgraphV2Policy:
    """Parse policy semantics and SHA-256 from the exact same bytes."""

    if not isinstance(source_bytes, bytes):
        raise OrderedSubgraphV2Error("ordered-subgraph v2 policy bytes are invalid")
    try:
        policy_text = source_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise OrderedSubgraphV2Error(
            f"ordered-subgraph v2 policy is not UTF-8: {source_path}"
        ) from exc
    payload: dict[str, Any] = yaml.safe_load(policy_text) or {}
    path = source_path
    anchors = _mapping(payload, "anchor_prepass", path)
    candidates = _mapping(payload, "candidate_admissibility", path)
    scopes = _mapping(payload, "scope_gate", path)
    parents = _mapping(payload, "parent_orphan_gate", path)
    search = _mapping(payload, "search", path)
    objective = _mapping(payload, "objective", path)
    acceptance = _mapping(payload, "acceptance_gates", path)

    forbidden_flags = (
        "numeric_report_norm_id_sort_allowed",
        "numeric_features_allowed",
        "value_features_allowed",
        "period_features_allowed",
        "historical_features_allowed",
        "human_review_features_allowed",
    )
    identity_is_safe = (
        payload.get("version") == 2
        and payload.get("mode") == _EXPECTED_MODE
        and payload.get("ordering_authority") == "WORKBOOK_DISPLAY_ORDER_ONLY"
        and payload.get("policy_bytes_authority")
        == "SINGLE_IMMUTABLE_BYTE_SNAPSHOT_FOR_PARSE_AND_SHA256"
        and all(payload.get(flag) is False for flag in forbidden_flags)
        and anchors.get("require_stream_agreement") is True
        and anchors.get("require_one_to_one") is True
        and anchors.get("require_global_monotonicity") is True
        and anchors.get("require_role_compatibility") is True
        and anchors.get("require_direct_parent_compatibility") is True
        and anchors.get("require_earlier_schema_parent_compatibility") is True
        and candidates.get("unknown_role_behavior") == "NEUTRAL_NO_BONUS"
        and candidates.get("reader_aggregation") == "MAX_PER_READER_LABEL_SCORE_NO_VOTE_BONUS"
        and candidates.get("parent_relaxed_relation_type") == SourceRelationType.DIRECT_PARENT.value
        and candidates.get("threshold_comparison") == "RAW_UNROUNDED_SCORE_DIAGNOSTIC_ROUNDING_ONLY"
        and scopes.get("unknown_scope_behavior") == "NEUTRAL_NO_BONUS"
        and scopes.get("reject_known_known_conflict") is True
        and parents.get("explicit_direct_parent_is_hard_constraint") is True
        and parents.get("earlier_schema_parent_inside_active_interval_is_hard_constraint") is True
        and parents.get("out_of_interval_schema_parent_behavior") == "NEUTRAL"
        and objective.get("direct_parent_gain_baseline") == "MINIMUM_PARENT_RELAXED_LABEL_SCORE"
        and objective.get("adjacency_behavior") == "TIE_BREAK_ONLY_AFTER_ADMISSIBILITY"
        and acceptance.get("require_zero_structural_issues") is True
        and acceptance.get("require_pair_exclusion_counterfactual_stability") is True
        and acceptance.get("require_zero_beam_pruning") is True
        and acceptance.get("margin_comparison") == "RAW_UNROUNDED_SCORE_DIAGNOSTIC_ROUNDING_ONLY"
    )
    if not identity_is_safe:
        raise OrderedSubgraphV2Error(f"ordered-subgraph v2 policy identity is unsafe: {path}")
    for zero_key in ("skip_baseline", "coverage_reward", "cardinality_reward"):
        if _bounded_float(objective, zero_key, path, minimum=0, maximum=0) != 0:
            raise OrderedSubgraphV2Error(
                f"ordered-subgraph v2 {zero_key} must remain exactly zero: {path}"
            )
    minimum_streams = anchors.get("minimum_independent_valid_streams")
    beam_width = search.get("beam_width_per_dp_cell")
    returned_paths = search.get("returned_path_limit")
    if (
        isinstance(minimum_streams, bool)
        or not isinstance(minimum_streams, int)
        or minimum_streams < 2
        or isinstance(beam_width, bool)
        or not isinstance(beam_width, int)
        or beam_width < 2
        or isinstance(returned_paths, bool)
        or not isinstance(returned_paths, int)
        or returned_paths < 2
        or returned_paths > beam_width
    ):
        raise OrderedSubgraphV2Error(f"ordered-subgraph v2 search/stream counts are unsafe: {path}")
    raw_trailing = parents.get("trailing_aggregate_report_norm_ids")
    if (
        not isinstance(raw_trailing, list)
        or not raw_trailing
        or any(isinstance(item, bool) or not isinstance(item, int) for item in raw_trailing)
        or len(raw_trailing) != len(set(raw_trailing))
    ):
        raise OrderedSubgraphV2Error(
            f"ordered-subgraph v2 trailing aggregate exceptions are invalid: {path}"
        )
    minimum_strong_label_score = _bounded_float(
        candidates,
        "minimum_strong_aggregate_label_score",
        path,
        minimum=0,
        maximum=1,
    )
    minimum_parent_relaxed_label_score = _bounded_float(
        candidates,
        "minimum_parent_relaxed_aggregate_label_score",
        path,
        minimum=0,
        maximum=1,
    )
    if minimum_parent_relaxed_label_score > minimum_strong_label_score:
        raise OrderedSubgraphV2Error(
            f"ordered-subgraph v2 parent-relaxed threshold exceeds strong threshold: {path}"
        )
    return OrderedSubgraphV2Policy(
        version=2,
        mode=_EXPECTED_MODE,
        calibration_status=str(payload.get("calibration_status", "")),
        ordering_authority="WORKBOOK_DISPLAY_ORDER_ONLY",
        minimum_anchor_stream_score=_bounded_float(
            anchors, "minimum_stream_score", path, minimum=0, maximum=1
        ),
        minimum_anchor_stream_margin=_bounded_float(
            anchors, "minimum_stream_runner_up_margin", path, minimum=0, maximum=1
        ),
        minimum_anchor_streams=minimum_streams,
        minimum_strong_label_score=minimum_strong_label_score,
        minimum_parent_relaxed_label_score=minimum_parent_relaxed_label_score,
        parent_relaxed_relation_type=str(candidates.get("parent_relaxed_relation_type", "")),
        minimum_interval_margin=_bounded_float(
            acceptance,
            "minimum_interval_best_runner_up_margin",
            path,
            minimum=0,
            maximum=1,
        ),
        beam_width=beam_width,
        returned_path_limit=returned_paths,
        parent_corroboration_gain=_bounded_float(
            objective, "parent_corroboration_gain", path, minimum=0, maximum=1
        ),
        trailing_aggregate_ids=tuple(raw_trailing),
        source_path=path,
        source_bytes=source_bytes,
        policy_sha256=_sha256_bytes(source_bytes),
    )


def build_schema_projection_v2(
    schema: Sequence[SchemaItem], statement_type: str
) -> SchemaProjectionV2:
    """Build an explicit history-free mapping projection from loaded schema.

    Only workbook canonical names and hierarchy-reference structural aliases
    cross this boundary. ``historical_aliases`` is deliberately never read.
    """

    items = sorted(
        (item for item in schema if item.statement_type == statement_type),
        key=lambda item: item.display_order,
    )
    if not items:
        raise OrderedSubgraphV2Error(
            f"schema projection has no rows for statement {statement_type}"
        )
    ids = {item.schema_id for item in items}
    if len(ids) != len(items) or len({item.display_order for item in items}) != len(items):
        raise OrderedSubgraphV2Error("schema projection IDs/display orders are not unique")
    for item in items:
        if item.parent_id is not None and item.parent_id not in ids:
            raise OrderedSubgraphV2Error(
                f"schema projection item {item.schema_id} has out-of-projection parent {item.parent_id}"
            )
        if any(child not in ids for child in item.children):
            raise OrderedSubgraphV2Error(
                f"schema projection item {item.schema_id} has out-of-projection child"
            )
    expected_children: dict[int, list[int]] = {item.schema_id: [] for item in items}
    for item in items:
        if item.parent_id is not None:
            expected_children[item.parent_id].append(item.schema_id)
    for item in items:
        if tuple(item.children) != tuple(expected_children[item.schema_id]):
            raise OrderedSubgraphV2Error(
                f"schema projection hierarchy edges drift at {item.schema_id}"
            )
    by_id = {item.schema_id: item for item in items}

    def section_path(item: SchemaItem) -> tuple[int, ...]:
        path = [item.schema_id]
        seen = {item.schema_id}
        current = item
        while current.parent_id is not None:
            if current.parent_id in seen:
                raise OrderedSubgraphV2Error(
                    f"schema projection hierarchy cycle containing {current.parent_id}"
                )
            seen.add(current.parent_id)
            path.append(current.parent_id)
            current = by_id[current.parent_id]
        return tuple(reversed(path))

    nodes = tuple(
        SchemaProjectionNodeV2(
            report_norm_id=item.schema_id,
            canonical_name=item.canonical_name,
            structural_aliases=tuple(
                dict.fromkeys(
                    alias
                    for alias in item.structural_aliases
                    if normalize_text(alias)
                    and retrieval_key(alias) != retrieval_key(item.canonical_name)
                )
            ),
            statement_type=item.statement_type,
            display_order=item.display_order,
            parent_report_norm_id=item.parent_id,
            child_report_norm_ids=tuple(item.children),
            hierarchy_level=item.hierarchy_level,
            section_path=section_path(item),
            scopes=tuple(item.scope),
        )
        for item in items
    )
    digest = _projection_digest(nodes)
    return SchemaProjectionV2(
        statement_type=statement_type,
        nodes=nodes,
        projection_sha256=digest,
    )


def _projection_digest(nodes: Sequence[SchemaProjectionNodeV2]) -> str:
    serialized = [asdict(node) for node in nodes]
    return hashlib.sha256(
        json.dumps(serialized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _raw_score(score: float) -> Decimal:
    """Preserve the recognizer's unrounded score for all decision gates."""

    return Decimal(str(score))


def _diagnostic_score(score: Decimal) -> float:
    return round(float(score), 6)


def _label_similarity(label: str, node: SchemaProjectionNodeV2) -> float:
    # Projection construction admits canonical workbook text plus explicit
    # structural aliases only. Historical aliases never enter this type.
    left = retrieval_key(label)
    rights = tuple(retrieval_key(item) for item in (node.canonical_name, *node.structural_aliases))
    if not left or not any(rights):
        return 0.0
    return max(ratio(left, right) / 100.0 for right in rights if right)


def _schema_role(node: SchemaProjectionNodeV2) -> SourceRowRole:
    key = retrieval_key(node.canonical_name)
    if key == "tong" or key.startswith("tong "):
        return SourceRowRole.TOTAL
    letters = "".join(
        character for character in normalize_text(node.canonical_name) if character.isalpha()
    )
    if letters and letters.isupper():
        return SourceRowRole.SECTION
    if node.child_report_norm_ids:
        return SourceRowRole.GROUP
    return SourceRowRole.DETAIL


def _role(row: SourceStructureRowV2) -> SourceRowRole:
    aliases = {
        "PARENT": SourceRowRole.GROUP,
        "SECTION_HEADING": SourceRowRole.SECTION,
    }
    try:
        raw = str(row.row_role).upper()
        return aliases[raw] if raw in aliases else SourceRowRole(raw)
    except ValueError as exc:
        raise OrderedSubgraphV2Error(
            f"row {row.row_id} has unsupported row_role={row.row_role!r}"
        ) from exc


def _relation(row: SourceStructureRowV2) -> SourceRelationType:
    aliases = {
        "PHYSICAL_PARENT": SourceRelationType.DIRECT_PARENT,
        "SECTION_MEMBER": SourceRelationType.UNKNOWN,
        "NONE": SourceRelationType.UNKNOWN,
    }
    try:
        raw = str(row.relation_type).upper()
        return aliases[raw] if raw in aliases else SourceRelationType(raw)
    except ValueError as exc:
        raise OrderedSubgraphV2Error(
            f"row {row.row_id} has unsupported relation_type={row.relation_type!r}"
        ) from exc


def _roles_compatible(row: SourceStructureRowV2, node: SchemaProjectionNodeV2) -> tuple[bool, str]:
    source = _role(row)
    target = _schema_role(node)
    if source is SourceRowRole.UNKNOWN:
        return True, "UNKNOWN_ROLE_NEUTRAL"
    if source is not target:
        return False, f"KNOWN_ROLE_CONFLICT_{source.value}_VS_{target.value}"
    return True, f"KNOWN_ROLE_COMPATIBLE_{source.value}"


def _scope_compatible(row: SourceStructureRowV2, node: SchemaProjectionNodeV2) -> tuple[bool, str]:
    source = str(row.report_scope).upper()
    if source == _UNKNOWN:
        return True, "UNKNOWN_SCOPE_NEUTRAL"
    known_node_scopes = {
        str(scope).upper() for scope in node.scopes if str(scope).upper() != _UNKNOWN
    }
    if not known_node_scopes:
        return True, "SCHEMA_SCOPE_UNSPECIFIED_NEUTRAL"
    if source not in known_node_scopes:
        return False, "KNOWN_SCOPE_CONFLICT"
    return True, "KNOWN_SCOPE_COMPATIBLE_NO_BONUS"


def _ordered_projection_nodes(
    projection: SchemaProjectionV2,
) -> tuple[SchemaProjectionNodeV2, ...]:
    if projection.alias_authority != "CANONICAL_AND_STRUCTURAL_ALIASES_ONLY":
        raise OrderedSubgraphV2Error("schema projection alias authority is unsafe")
    nodes = tuple(sorted(projection.nodes, key=lambda item: item.display_order))
    if not nodes:
        raise OrderedSubgraphV2Error("ordered-subgraph v2 requires a non-empty schema graph")
    if len({item.report_norm_id for item in nodes}) != len(nodes):
        raise OrderedSubgraphV2Error("schema graph has duplicate ReportNormIds")
    if len({item.display_order for item in nodes}) != len(nodes):
        raise OrderedSubgraphV2Error("schema graph has duplicate workbook display orders")
    if any(item.statement_type != projection.statement_type for item in nodes):
        raise OrderedSubgraphV2Error("schema graph contains a foreign statement node")
    if _projection_digest(nodes) != projection.projection_sha256:
        raise OrderedSubgraphV2Error("schema projection content/hash identity drifted")
    return nodes


def _validated_rows(
    rows: Sequence[SourceStructureRowV2], projection: SchemaProjectionV2
) -> tuple[SourceStructureRowV2, ...]:
    ordered = tuple(sorted(rows, key=lambda item: item.order))
    if not ordered:
        raise OrderedSubgraphV2Error("ordered-subgraph v2 requires at least one source row")
    if len({item.row_id for item in ordered}) != len(ordered):
        raise OrderedSubgraphV2Error("source rows have duplicate row IDs")
    if len({item.order for item in ordered}) != len(ordered):
        raise OrderedSubgraphV2Error("source rows have duplicate order values")
    by_id = {item.row_id: item for item in ordered}
    known_scopes: set[str] = set()
    for row in ordered:
        if not row.row_id or not isinstance(row.labels_by_reader, Mapping):
            raise OrderedSubgraphV2Error("source row identity/labels are invalid")
        _role(row)
        relation = _relation(row)
        labels = list(row.labels_by_reader.items())
        if any(
            not isinstance(reader, str) or not reader or not isinstance(label, str)
            for reader, label in labels
        ):
            raise OrderedSubgraphV2Error(f"row {row.row_id} has invalid reader proposals")
        if relation is SourceRelationType.DIRECT_PARENT and row.parent_row_id is None:
            raise OrderedSubgraphV2Error(
                f"row {row.row_id} declares DIRECT_PARENT without parent_row_id"
            )
        if row.parent_row_id is not None:
            parent = by_id.get(row.parent_row_id)
            if parent is None or parent.order >= row.order:
                raise OrderedSubgraphV2Error(
                    f"row {row.row_id} has missing or non-earlier parent {row.parent_row_id}"
                )
        scope = str(row.report_scope).upper()
        if not scope:
            raise OrderedSubgraphV2Error(f"row {row.row_id} has an empty report scope")
        if scope != _UNKNOWN:
            known_scopes.add(scope)
    if len(known_scopes) > 1:
        raise OrderedSubgraphV2Error(
            f"source rows contain conflicting known report scopes: {sorted(known_scopes)}"
        )
    return ordered


def _stream_anchor_diagnostic(
    reader_id: str,
    label: str,
    row: SourceStructureRowV2,
    nodes: tuple[SchemaProjectionNodeV2, ...],
    policy: OrderedSubgraphV2Policy,
) -> AnchorStreamDiagnostic:
    scored: list[tuple[Decimal, int, int]] = []
    for node in nodes:
        role_ok, _ = _roles_compatible(row, node)
        scope_ok, _ = _scope_compatible(row, node)
        if role_ok and scope_ok:
            scored.append(
                (
                    _raw_score(_label_similarity(label, node)),
                    node.display_order,
                    node.report_norm_id,
                )
            )
    scored.sort(key=lambda item: (-item[0], item[1]))
    if not normalize_text(label) or not scored:
        return AnchorStreamDiagnostic(
            reader_id, None, None, None, None, None, False, "empty label or no compatible node"
        )
    best = scored[0]
    runner = scored[1] if len(scored) > 1 else None
    margin = best[0] - runner[0] if runner is not None else best[0]
    minimum_score = _raw_score(policy.minimum_anchor_stream_score)
    minimum_margin = _raw_score(policy.minimum_anchor_stream_margin)
    valid = best[0] >= minimum_score and margin >= minimum_margin
    reasons = []
    if best[0] < minimum_score:
        reasons.append("stream score below anchor gate")
    if margin < minimum_margin:
        reasons.append("stream runner-up margin below anchor gate")
    if valid:
        reasons.append("stream independently passes score and margin")
    return AnchorStreamDiagnostic(
        reader_id=reader_id,
        best_report_norm_id=best[2],
        best_score=_diagnostic_score(best[0]),
        runner_up_report_norm_id=None if runner is None else runner[2],
        runner_up_score=None if runner is None else _diagnostic_score(runner[0]),
        margin=_diagnostic_score(margin),
        valid=valid,
        reason="; ".join(reasons),
    )


def _anchor_prepass(
    rows: tuple[SourceStructureRowV2, ...],
    nodes: tuple[SchemaProjectionNodeV2, ...],
    policy: OrderedSubgraphV2Policy,
) -> tuple[tuple[AnchorDiagnostic, ...], tuple[_AnchorProposal, ...], bool, tuple[str, ...]]:
    provisional: list[_AnchorProposal] = []
    conflict_reasons: list[str] = []
    diagnostics_by_row: dict[str, AnchorDiagnostic] = {}
    for row in rows:
        streams = tuple(
            _stream_anchor_diagnostic(reader, label, row, nodes, policy)
            for reader, label in sorted(row.labels_by_reader.items())
        )
        valid = [item for item in streams if item.valid]
        valid_ids = {item.best_report_norm_id for item in valid}
        if not row.target_template_in_scope:
            status = "OUT_OF_SCOPE"
            reason = "row is outside the target template"
            selected = None
        elif len(valid) < policy.minimum_anchor_streams:
            status = "INSUFFICIENT_INDEPENDENT_STREAMS"
            reason = "fewer than two independent streams pass score and margin"
            selected = None
        elif len(valid_ids) != 1:
            status = "STREAM_CONFLICT"
            reason = "independently valid reader streams disagree on ReportNormId"
            selected = None
            conflict_reasons.append(f"anchor reader-stream conflict at row {row.row_id}")
        else:
            selected = next(iter(valid_ids))
            status = "PROVISIONAL_ANCHOR"
            reason = "two or more independent streams agree"
            provisional.append(_AnchorProposal(row.row_id, selected, streams))
        diagnostics_by_row[row.row_id] = AnchorDiagnostic(
            row_id=row.row_id,
            status=status,
            selected_report_norm_id=None,
            stream_diagnostics=streams,
            reason=reason,
            constraint_report_norm_id=selected,
        )

    row_by_id = {row.row_id: row for row in rows}
    node_by_id = {node.report_norm_id: node for node in nodes}
    # Anchor eligibility is transitively parent-grounded. A strong child label
    # must not turn its earlier, still-unmapped schema parent into an
    # out-of-interval neutral merely by creating a new interval boundary.
    while True:
        proposal_by_row = {item.row_id: item for item in provisional}
        excluded_children: set[str] = set()
        for item in provisional:
            row = row_by_id[item.row_id]
            if _relation(row) is not SourceRelationType.DIRECT_PARENT:
                continue
            parent = proposal_by_row.get(row.parent_row_id or "")
            if parent is None:
                excluded_children.add(row.row_id)
                diagnostics_by_row[row.row_id] = replace(
                    diagnostics_by_row[row.row_id],
                    status="DIRECT_PARENT_NOT_ANCHORED",
                    selected_report_norm_id=None,
                    reason=(
                        "child cannot anchor because its sealed direct-parent "
                        "ancestor chain is not fully anchored"
                    ),
                )
                continue
            node = node_by_id[item.report_norm_id]
            if node.parent_report_norm_id != parent.report_norm_id:
                excluded_children.add(row.row_id)
                conflict_reasons.append(f"anchor parent conflict at row {row.row_id}")
                diagnostics_by_row[row.row_id] = replace(
                    diagnostics_by_row[row.row_id],
                    status="DIRECT_PARENT_CONFLICT",
                    selected_report_norm_id=None,
                    reason="anchor candidate conflicts with its sealed direct parent mapping",
                )
        proposals_by_schema: dict[int, list[_AnchorProposal]] = {}
        for item in provisional:
            proposals_by_schema.setdefault(item.report_norm_id, []).append(item)
        for item in provisional:
            if item.row_id in excluded_children:
                continue
            row = row_by_id[item.row_id]
            node = node_by_id[item.report_norm_id]
            parent_id = node.parent_report_norm_id
            if parent_id is None or parent_id in policy.trailing_aggregate_ids:
                continue
            parent_node = node_by_id[parent_id]
            if parent_node.display_order >= node.display_order:
                continue
            earlier_parent_anchor = any(
                row_by_id[parent.row_id].order < row.order
                for parent in proposals_by_schema.get(parent_id, ())
            )
            if earlier_parent_anchor:
                continue
            excluded_children.add(row.row_id)
            diagnostics_by_row[row.row_id] = replace(
                diagnostics_by_row[row.row_id],
                status="EARLIER_SCHEMA_PARENT_NOT_ANCHORED",
                selected_report_norm_id=None,
                reason=(
                    "child cannot anchor because its earlier schema parent is not "
                    "grounded by an earlier compatible anchor"
                ),
            )
        if not excluded_children:
            break
        provisional = [item for item in provisional if item.row_id not in excluded_children]

    by_schema: dict[int, list[_AnchorProposal]] = {}
    for item in provisional:
        by_schema.setdefault(item.report_norm_id, []).append(item)
    duplicate_rows = {
        item.row_id for group in by_schema.values() if len(group) > 1 for item in group
    }
    if duplicate_rows:
        conflict_reasons.append("anchor candidates violate one-to-one assignment")
        for row_id in duplicate_rows:
            diagnostics_by_row[row_id] = replace(
                diagnostics_by_row[row_id],
                status="ONE_TO_ONE_CONFLICT",
                selected_report_norm_id=None,
                reason="multiple source rows claim the same anchor ReportNormId",
            )

    ordered_provisional = sorted(provisional, key=lambda item: row_by_id[item.row_id].order)
    crossing_rows: set[str] = set()
    for left, right in zip(ordered_provisional, ordered_provisional[1:], strict=False):
        if (
            node_by_id[left.report_norm_id].display_order
            > node_by_id[right.report_norm_id].display_order
        ):
            crossing_rows.update((left.row_id, right.row_id))
    if crossing_rows:
        conflict_reasons.append("anchor candidates cross workbook display order")
        for row_id in crossing_rows:
            diagnostics_by_row[row_id] = replace(
                diagnostics_by_row[row_id],
                status="MONOTONICITY_CONFLICT",
                selected_report_norm_id=None,
                reason="anchor candidate crosses another anchor in workbook display order",
            )

    global_conflict = bool(conflict_reasons or duplicate_rows or crossing_rows)
    accepted: tuple[_AnchorProposal, ...]
    if global_conflict:
        accepted = ()
        for item in provisional:
            current = diagnostics_by_row[item.row_id]
            if current.status == "PROVISIONAL_ANCHOR":
                diagnostics_by_row[item.row_id] = replace(
                    current,
                    status="WITHHELD_DUE_GLOBAL_ANCHOR_CONFLICT",
                    selected_report_norm_id=None,
                    reason="all anchors are withheld because the anchor set is inconsistent",
                )
    else:
        accepted = tuple(ordered_provisional)
        for item in accepted:
            diagnostics_by_row[item.row_id] = replace(
                diagnostics_by_row[item.row_id],
                status="ACCEPTED_CONSTRAINT_PENDING_INTERVAL_GATES",
                selected_report_norm_id=None,
                reason=(
                    "two-stream anchor is a one-to-one monotone constraint; "
                    "selection awaits adjacent-interval and exclusion gates"
                ),
            )
    diagnostics = tuple(diagnostics_by_row[row.row_id] for row in rows)
    return diagnostics, accepted, global_conflict, tuple(conflict_reasons)


def _partition_intervals(
    rows: tuple[SourceStructureRowV2, ...],
    nodes: tuple[SchemaProjectionNodeV2, ...],
    anchors: tuple[_AnchorProposal, ...],
) -> tuple[_Interval, ...]:
    row_index = {row.row_id: index for index, row in enumerate(rows)}
    node_index = {node.report_norm_id: index for index, node in enumerate(nodes)}
    boundaries: list[tuple[_AnchorProposal | None, int, int]] = [(None, -1, -1)]
    boundaries.extend(
        (anchor, row_index[anchor.row_id], node_index[anchor.report_norm_id]) for anchor in anchors
    )
    result: list[_Interval] = []
    for index, (previous, previous_row, previous_node) in enumerate(boundaries):
        following = (
            boundaries[index + 1] if index + 1 < len(boundaries) else (None, len(rows), len(nodes))
        )
        next_anchor, next_row, next_node = following
        result.append(
            _Interval(
                index=index,
                previous_anchor=previous,
                next_anchor=next_anchor,
                rows=rows[previous_row + 1 : next_row],
                nodes=nodes[previous_node + 1 : next_node],
            )
        )
    return tuple(result)


def _raw_reader_pair_scores(
    row: SourceStructureRowV2, node: SchemaProjectionNodeV2
) -> tuple[tuple[str, Decimal], ...]:
    return tuple(
        (reader, _raw_score(_label_similarity(label, node)))
        for reader, label in sorted(row.labels_by_reader.items())
        if normalize_text(label)
    )


def _candidate_pairs(
    interval: _Interval,
    policy: OrderedSubgraphV2Policy,
) -> dict[tuple[int, int], _CandidatePair]:
    result: dict[tuple[int, int], _CandidatePair] = {}
    minimum_strong = _raw_score(policy.minimum_strong_label_score)
    minimum_parent_relaxed = _raw_score(policy.minimum_parent_relaxed_label_score)
    for row_index, row in enumerate(interval.rows):
        if not row.target_template_in_scope:
            continue
        for node_index, node in enumerate(interval.nodes):
            role_ok, role_reason = _roles_compatible(row, node)
            scope_ok, scope_reason = _scope_compatible(row, node)
            if not role_ok or not scope_ok:
                continue
            raw_reader_scores = _raw_reader_pair_scores(row, node)
            reader_scores = tuple(
                ReaderScoreDiagnostic(
                    reader,
                    node.report_norm_id,
                    _diagnostic_score(score),
                )
                for reader, score in raw_reader_scores
            )
            aggregate = max((score for _reader, score in raw_reader_scores), default=Decimal(0))
            direct_parent = _relation(row) is SourceRelationType.DIRECT_PARENT
            if aggregate >= minimum_strong:
                admissibility = (
                    "STRONG_LABEL_PENDING_MAPPED_DIRECT_PARENT" if direct_parent else "STRONG_LABEL"
                )
                # All candidates for a sealed direct-parent row share one
                # baseline so crossing the strong threshold cannot lower gain.
                baseline = minimum_parent_relaxed if direct_parent else minimum_strong
                requires_parent = direct_parent
            elif (
                aggregate >= minimum_parent_relaxed
                and direct_parent
                and policy.parent_relaxed_relation_type == SourceRelationType.DIRECT_PARENT.value
            ):
                admissibility = "PARENT_RELAXED_PENDING"
                baseline = minimum_parent_relaxed
                requires_parent = True
            else:
                continue
            raw_gain = aggregate - baseline
            diagnostic = CandidatePairDiagnostic(
                row_id=row.row_id,
                report_norm_id=node.report_norm_id,
                aggregate_label_score=_diagnostic_score(aggregate),
                reader_scores=reader_scores,
                admissibility=admissibility,
                role_compatibility=role_reason,
                scope_compatibility=scope_reason,
                requires_mapped_direct_parent=requires_parent,
                evidence_baseline=_diagnostic_score(baseline),
                base_evidence_gain=_diagnostic_score(raw_gain),
            )
            result[(row_index, node_index)] = _CandidatePair(
                diagnostic=diagnostic,
                raw_base_evidence_gain=raw_gain,
            )
    return result


def _mapped_by_row(state: _PathState, resolved_before: Mapping[str, int]) -> dict[str, int]:
    mapped = dict(resolved_before)
    mapped.update((item.row_id, item.report_norm_id) for item in state.matches)
    return mapped


def _parent_gate(
    *,
    row: SourceStructureRowV2,
    node: SchemaProjectionNodeV2,
    state: _PathState,
    interval: _Interval,
    resolved_before: Mapping[str, int],
    policy: OrderedSubgraphV2Policy,
) -> tuple[bool, bool, str | None]:
    mapped = _mapped_by_row(state, resolved_before)
    interval_node_by_id = {item.report_norm_id: item for item in interval.nodes}
    if _relation(row) is SourceRelationType.DIRECT_PARENT:
        parent_row_id = row.parent_row_id or ""
        mapped_parent = mapped.get(parent_row_id)
        if mapped_parent is None:
            return False, False, "sealed direct parent is not actually mapped"
        if node.parent_report_norm_id != mapped_parent:
            return False, False, "sealed direct parent maps to a different schema parent"
        return True, True, None

    if node.parent_report_norm_id in policy.trailing_aggregate_ids:
        return True, False, None

    parent = interval_node_by_id.get(node.parent_report_norm_id)
    if parent is not None and parent.display_order < node.display_order:
        if node.parent_report_norm_id not in mapped.values():
            return False, False, "earlier schema parent inside active interval is not mapped"
        # With no sealed source edge, a mapped schema parent satisfies only the
        # orphan gate. UNKNOWN parent structure remains neutral and gets no gain.
        return True, False, None
    return True, False, None


def _transition_match(
    state: _PathState,
    *,
    row_index: int,
    node_index: int,
    interval: _Interval,
    candidate: _CandidatePair,
    resolved_before: Mapping[str, int],
    policy: OrderedSubgraphV2Policy,
) -> _PathState | None:
    row = interval.rows[row_index]
    node = interval.nodes[node_index]
    allowed, parent_corroborated, _ = _parent_gate(
        row=row,
        node=node,
        state=state,
        interval=interval,
        resolved_before=resolved_before,
        policy=policy,
    )
    if not allowed:
        return None
    diagnostic = candidate.diagnostic
    gain = candidate.raw_base_evidence_gain
    admissibility = diagnostic.admissibility
    if parent_corroborated:
        gain += _raw_score(policy.parent_corroboration_gain)
        if admissibility == "PARENT_RELAXED_PENDING":
            admissibility = "PARENT_RELAXED_BY_MAPPED_DIRECT_PARENT"
        elif admissibility == "STRONG_LABEL_PENDING_MAPPED_DIRECT_PARENT":
            admissibility = "STRONG_LABEL_WITH_MAPPED_DIRECT_PARENT"
    elif admissibility in {
        "PARENT_RELAXED_PENDING",
        "STRONG_LABEL_PENDING_MAPPED_DIRECT_PARENT",
    }:
        return None
    adjacent = 0
    if state.matched_indices:
        previous_row, previous_node = state.matched_indices[-1]
        if row_index == previous_row + 1 and node_index == previous_node + 1:
            adjacent = 1
    match = PathMatchDiagnostic(
        row_id=row.row_id,
        report_norm_id=node.report_norm_id,
        row_order=row.order,
        schema_display_order=node.display_order,
        aggregate_label_score=diagnostic.aggregate_label_score,
        admissibility=admissibility,
        evidence_gain=_diagnostic_score(gain),
        direct_parent_corroborated=parent_corroborated,
    )
    return _PathState(
        score=state.score + gain,
        adjacency_count=state.adjacency_count + adjacent,
        matches=(*state.matches, match),
        matched_indices=(*state.matched_indices, (row_index, node_index)),
        structural_issues=state.structural_issues,
    )


def _retain_best(states: Sequence[_PathState], limit: int) -> tuple[tuple[_PathState, ...], int]:
    by_signature: dict[tuple[tuple[str, int], ...], _PathState] = {}
    for state in states:
        previous = by_signature.get(state.signature)
        if previous is None or (
            state.score,
            state.adjacency_count,
            tuple(-len(issue) for issue in state.structural_issues),
        ) > (
            previous.score,
            previous.adjacency_count,
            tuple(-len(issue) for issue in previous.structural_issues),
        ):
            by_signature[state.signature] = state
    ordered = tuple(
        sorted(
            by_signature.values(),
            key=lambda item: (
                -item.score,
                -item.adjacency_count,
                len(item.structural_issues),
                item.signature,
            ),
        )[:limit]
    )
    return ordered, max(0, len(by_signature) - limit)


def _materialize_path(
    state: _PathState,
    rank: int,
    interval: _Interval,
) -> RankedPathDiagnostic:
    matched_rows = {item.row_id for item in state.matches}
    matched_nodes = {item.report_norm_id for item in state.matches}
    return RankedPathDiagnostic(
        rank=rank,
        total_score=_diagnostic_score(state.score),
        adjacency_tiebreak_count=state.adjacency_count,
        matches=state.matches,
        skipped_row_ids=tuple(
            row.row_id for row in interval.rows if row.row_id not in matched_rows
        ),
        skipped_report_norm_ids=tuple(
            node.report_norm_id
            for node in interval.nodes
            if node.report_norm_id not in matched_nodes
        ),
        structural_issues=state.structural_issues,
    )


def _search_interval(
    interval: _Interval,
    candidates: Mapping[tuple[int, int], _CandidatePair],
    resolved_before: Mapping[str, int],
    policy: OrderedSubgraphV2Policy,
    *,
    excluded_pair: tuple[str, int] | None = None,
) -> _SearchOutcome:
    row_count = len(interval.rows)
    node_count = len(interval.nodes)
    grid: list[list[tuple[_PathState, ...]]] = [
        [tuple() for _ in range(node_count + 1)] for _ in range(row_count + 1)
    ]
    grid[0][0] = (_PathState(Decimal(0), 0, (), ()),)
    generated = 1
    retained = 1
    pruned = 0
    for row_prefix in range(row_count + 1):
        for node_prefix in range(node_count + 1):
            if row_prefix == 0 and node_prefix == 0:
                continue
            proposed: list[_PathState] = []
            if row_prefix > 0:
                proposed.extend(grid[row_prefix - 1][node_prefix])
            if node_prefix > 0:
                proposed.extend(grid[row_prefix][node_prefix - 1])
            if row_prefix > 0 and node_prefix > 0:
                candidate = candidates.get((row_prefix - 1, node_prefix - 1))
                if candidate is not None and excluded_pair != (
                    candidate.diagnostic.row_id,
                    candidate.diagnostic.report_norm_id,
                ):
                    for state in grid[row_prefix - 1][node_prefix - 1]:
                        matched = _transition_match(
                            state,
                            row_index=row_prefix - 1,
                            node_index=node_prefix - 1,
                            interval=interval,
                            candidate=candidate,
                            resolved_before=resolved_before,
                            policy=policy,
                        )
                        if matched is not None:
                            proposed.append(matched)
            generated += len(proposed)
            kept, cell_pruned = _retain_best(proposed, policy.beam_width)
            grid[row_prefix][node_prefix] = kept
            pruned += cell_pruned
            retained += len(grid[row_prefix][node_prefix])
    terminal = grid[row_count][node_count]
    retained_terminal = terminal[: policy.returned_path_limit]
    paths = tuple(
        _materialize_path(state, rank, interval)
        for rank, state in enumerate(retained_terminal, start=1)
    )
    if not paths:
        raise OrderedSubgraphV2Error("interval DP produced no path despite zero-cost skips")
    return _SearchOutcome(
        paths=paths,
        raw_scores=tuple(state.score for state in retained_terminal),
        dp_cells=(row_count + 1) * (node_count + 1),
        generated_states=generated,
        retained_states=retained,
        pruned_states=pruned,
    )


def _alternative_report_norm_id(path: RankedPathDiagnostic, row_id: str) -> int | None:
    return next(
        (item.report_norm_id for item in path.matches if item.row_id == row_id),
        None,
    )


def _evaluate_interval(
    interval: _Interval,
    resolved_before: Mapping[str, int],
    policy: OrderedSubgraphV2Policy,
    *,
    forced_ambiguous: bool,
) -> tuple[IntervalDiagnostic, tuple[_SearchOutcome, ...]]:
    candidates = _candidate_pairs(interval, policy)
    outcome = _search_interval(interval, candidates, resolved_before, policy)
    best = outcome.paths[0]
    best_raw_score = outcome.raw_scores[0]
    runner = outcome.paths[1] if len(outcome.paths) > 1 else None
    runner_raw_score = outcome.raw_scores[1] if len(outcome.raw_scores) > 1 else None
    raw_margin = None if runner_raw_score is None else best_raw_score - runner_raw_score
    margin = None if raw_margin is None else _diagnostic_score(raw_margin)
    minimum_margin = _raw_score(policy.minimum_interval_margin)
    counterfactuals: list[CounterfactualDiagnostic] = []
    counterfactual_outcomes: list[_SearchOutcome] = []
    for selected in best.matches:
        counterfactual_outcome = _search_interval(
            interval,
            candidates,
            resolved_before,
            policy,
            excluded_pair=(selected.row_id, selected.report_norm_id),
        )
        counterfactual_outcomes.append(counterfactual_outcome)
        alternative = counterfactual_outcome.paths[0]
        alternative_raw_score = counterfactual_outcome.raw_scores[0]
        alternative_id = _alternative_report_norm_id(alternative, selected.row_id)
        raw_exclusion_margin = best_raw_score - alternative_raw_score
        exclusion_margin = _diagnostic_score(raw_exclusion_margin)
        counterfactuals.append(
            CounterfactualDiagnostic(
                row_id=selected.row_id,
                selected_report_norm_id=selected.report_norm_id,
                selected_path_score=best.total_score,
                alternative_path_score=alternative.total_score,
                alternative_report_norm_id=alternative_id,
                alternative_skips_row=alternative_id is None,
                exclusion_margin=exclusion_margin,
                stable=raw_exclusion_margin >= minimum_margin,
            )
        )
    main_pruned = outcome.pruned_states
    counterfactual_pruned = sum(item.pruned_states for item in counterfactual_outcomes)
    pruning_issues = []
    if main_pruned:
        pruning_issues.append(f"MAIN_SEARCH_BEAM_PRUNED_{main_pruned}_STATES")
    if counterfactual_pruned:
        pruning_issues.append(f"COUNTERFACTUAL_SEARCH_BEAM_PRUNED_{counterfactual_pruned}_STATES")
    issues = tuple(dict.fromkeys((*best.structural_issues, *pruning_issues)))
    if forced_ambiguous:
        status = RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value
        accepted = False
        reason = "anchor conflicts/crossings force the active interval to abstain"
    elif main_pruned or counterfactual_pruned:
        status = RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value
        accepted = False
        reason = "beam pruning prevents an exhaustive k-best/counterfactual certificate"
    elif not candidates:
        status = RowMappingStatus.NO_ADMISSIBLE_PAIR.value
        accepted = True
        reason = "no row/schema pair passes strong or mapped-direct-parent admissibility"
    elif not best.matches:
        status = RowMappingStatus.BEST_PATH_SKIPPED.value
        accepted = True
        reason = "admissible pairs do not improve on the zero skip baseline"
    elif (
        runner is None
        or raw_margin is None
        or raw_margin < minimum_margin
        or issues
        or any(not item.stable for item in counterfactuals)
    ):
        status = RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value
        accepted = False
        reason = "k-best margin, structural, or pair-exclusion stability gate failed"
    else:
        status = RowMappingStatus.RESOLVED_PATH.value
        accepted = True
        reason = "interval path and every selected-pair counterfactual are decisive"
    diagnostic = IntervalDiagnostic(
        interval_index=interval.index,
        previous_anchor_row_id=None
        if interval.previous_anchor is None
        else interval.previous_anchor.row_id,
        previous_anchor_report_norm_id=(
            None if interval.previous_anchor is None else interval.previous_anchor.report_norm_id
        ),
        next_anchor_row_id=None if interval.next_anchor is None else interval.next_anchor.row_id,
        next_anchor_report_norm_id=(
            None if interval.next_anchor is None else interval.next_anchor.report_norm_id
        ),
        row_ids=tuple(row.row_id for row in interval.rows),
        report_norm_ids=tuple(node.report_norm_id for node in interval.nodes),
        status=status,
        automatic_selection_allowed=accepted,
        best_path=best,
        runner_up_path=runner,
        score_margin=margin,
        ranked_paths=outcome.paths,
        counterfactuals=tuple(counterfactuals),
        candidate_pairs=tuple(
            sorted(
                (item.diagnostic for item in candidates.values()),
                key=lambda item: (
                    next(row.order for row in interval.rows if row.row_id == item.row_id),
                    next(
                        node.display_order
                        for node in interval.nodes
                        if node.report_norm_id == item.report_norm_id
                    ),
                ),
            )
        ),
        structural_issues=issues,
        main_search_pruned_states=main_pruned,
        counterfactual_search_pruned_states=counterfactual_pruned,
        search_exhaustive=not (main_pruned or counterfactual_pruned),
        reason=reason,
    )
    return diagnostic, (outcome, *counterfactual_outcomes)


def _anchor_aggregate_counterfactual(
    diagnostic: AnchorDiagnostic,
    row: SourceStructureRowV2,
    nodes: tuple[SchemaProjectionNodeV2, ...],
) -> tuple[float, int | None, float | None, float, Decimal]:
    """Compare the selected anchor pair with every compatible aggregate alternative."""

    scored: list[tuple[Decimal, int, int]] = []
    for node in nodes:
        role_ok, _ = _roles_compatible(row, node)
        scope_ok, _ = _scope_compatible(row, node)
        if not role_ok or not scope_ok:
            continue
        aggregate = max(
            (_raw_score(_label_similarity(label, node)) for label in row.labels_by_reader.values()),
            default=Decimal(0),
        )
        scored.append((aggregate, node.display_order, node.report_norm_id))
    selected_id = diagnostic.constraint_report_norm_id
    selected_score = next(
        (score for score, _order, report_norm_id in scored if report_norm_id == selected_id),
        None,
    )
    if selected_score is None:
        raise OrderedSubgraphV2Error(
            f"anchor {diagnostic.row_id} has no compatible aggregate selected pair"
        )
    alternatives = sorted(
        (item for item in scored if item[2] != selected_id),
        key=lambda item: (-item[0], item[1]),
    )
    best_alternative = alternatives[0] if alternatives else None
    alternative_score = None if best_alternative is None else best_alternative[0]
    margin = selected_score if alternative_score is None else selected_score - alternative_score
    return (
        _diagnostic_score(selected_score),
        None if best_alternative is None else best_alternative[2],
        None if alternative_score is None else _diagnostic_score(alternative_score),
        _diagnostic_score(margin),
        margin,
    )


def _finalize_anchor_selections(
    diagnostics: tuple[AnchorDiagnostic, ...],
    anchors: tuple[_AnchorProposal, ...],
    intervals: tuple[IntervalDiagnostic, ...],
    rows: tuple[SourceStructureRowV2, ...],
    nodes: tuple[SchemaProjectionNodeV2, ...],
    policy: OrderedSubgraphV2Policy,
) -> tuple[AnchorDiagnostic, ...]:
    """Promote constraints only after interval and aggregate-exclusion gates."""

    anchor_position = {anchor.row_id: index for index, anchor in enumerate(anchors)}
    row_by_id = {row.row_id: row for row in rows}
    result: list[AnchorDiagnostic] = []
    for diagnostic in diagnostics:
        position = anchor_position.get(diagnostic.row_id)
        if position is None:
            result.append(diagnostic)
            continue
        (
            aggregate_score,
            alternative_id,
            alternative_score,
            counterfactual_margin,
            raw_counterfactual_margin,
        ) = _anchor_aggregate_counterfactual(
            diagnostic,
            row_by_id[diagnostic.row_id],
            nodes,
        )
        adjacent = (intervals[position], intervals[position + 1])
        intervals_accepted = all(item.automatic_selection_allowed for item in adjacent)
        stable = raw_counterfactual_margin >= _raw_score(policy.minimum_interval_margin)
        if intervals_accepted and stable:
            result.append(
                replace(
                    diagnostic,
                    status=RowMappingStatus.RESOLVED_ANCHOR.value,
                    selected_report_norm_id=diagnostic.constraint_report_norm_id,
                    counterfactual_margin=counterfactual_margin,
                    selection_allowed=True,
                    aggregate_label_score=aggregate_score,
                    counterfactual_alternative_report_norm_id=alternative_id,
                    counterfactual_alternative_aggregate_label_score=alternative_score,
                    reason=(
                        "two-stream constraint, both adjacent intervals, and all-reader "
                        "aggregate pair-exclusion counterfactual are decisive"
                    ),
                )
            )
        else:
            result.append(
                replace(
                    diagnostic,
                    status=RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value,
                    selected_report_norm_id=None,
                    counterfactual_margin=counterfactual_margin,
                    selection_allowed=False,
                    aggregate_label_score=aggregate_score,
                    counterfactual_alternative_report_norm_id=alternative_id,
                    counterfactual_alternative_aggregate_label_score=alternative_score,
                    reason=(
                        "anchor remains a search constraint but cannot be selected because "
                        "an adjacent interval or all-reader aggregate pair-exclusion "
                        "counterfactual is ambiguous"
                    ),
                )
            )
    return tuple(result)


def _close_unselected_anchor_boundaries(
    diagnostics: tuple[AnchorDiagnostic, ...],
    anchors: tuple[_AnchorProposal, ...],
    intervals: tuple[IntervalDiagnostic, ...],
    rows: tuple[SourceStructureRowV2, ...],
    nodes: tuple[SchemaProjectionNodeV2, ...],
    policy: OrderedSubgraphV2Policy,
) -> tuple[tuple[AnchorDiagnostic, ...], tuple[IntervalDiagnostic, ...]]:
    """Withhold intervals conditioned on an anchor that has no final selection."""

    current_intervals = intervals
    while True:
        finalized = _finalize_anchor_selections(
            diagnostics,
            anchors,
            current_intervals,
            rows,
            nodes,
            policy,
        )
        finalized_by_row = {item.row_id: item for item in finalized}
        invalid_boundaries = {
            position
            for position, anchor in enumerate(anchors)
            if finalized_by_row[anchor.row_id].selected_report_norm_id is None
        }
        invalid_interval_indices = {
            interval_index
            for position in invalid_boundaries
            for interval_index in (position, position + 1)
        }
        changed = False
        updated: list[IntervalDiagnostic] = []
        for interval in current_intervals:
            if (
                interval.interval_index not in invalid_interval_indices
                or not interval.automatic_selection_allowed
            ):
                updated.append(interval)
                continue
            changed = True
            issue = "UNSELECTED_ANCHOR_BOUNDARY_CONDITION"
            updated.append(
                replace(
                    interval,
                    status=RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value,
                    automatic_selection_allowed=False,
                    structural_issues=tuple(dict.fromkeys((*interval.structural_issues, issue))),
                    reason=(
                        "interval was searched under an anchor boundary that did not "
                        "receive final selection"
                    ),
                )
            )
        current_intervals = tuple(updated)
        if not changed:
            return finalized, current_intervals


def _anchor_path_match(
    anchor: _AnchorProposal,
    rows: Mapping[str, SourceStructureRowV2],
    nodes: Mapping[int, SchemaProjectionNodeV2],
    policy: OrderedSubgraphV2Policy,
) -> PathMatchDiagnostic:
    row = rows[anchor.row_id]
    node = nodes[anchor.report_norm_id]
    aggregate = max(
        (_label_similarity(label, node) for label in row.labels_by_reader.values()),
        default=0.0,
    )
    direct_parent = _relation(row) is SourceRelationType.DIRECT_PARENT
    baseline = (
        policy.minimum_parent_relaxed_label_score
        if direct_parent
        else policy.minimum_strong_label_score
    )
    gain = aggregate - baseline
    if direct_parent:
        gain += policy.parent_corroboration_gain
    return PathMatchDiagnostic(
        row_id=row.row_id,
        report_norm_id=node.report_norm_id,
        row_order=row.order,
        schema_display_order=node.display_order,
        aggregate_label_score=round(aggregate, 6),
        admissibility=(
            "TWO_STREAM_DECISIVE_ANCHOR_WITH_MAPPED_DIRECT_PARENT"
            if direct_parent
            else "TWO_STREAM_DECISIVE_ANCHOR"
        ),
        evidence_gain=round(gain, 6),
        direct_parent_corroborated=direct_parent,
    )


def _global_paths(
    rows: tuple[SourceStructureRowV2, ...],
    nodes: tuple[SchemaProjectionNodeV2, ...],
    anchors: tuple[_AnchorProposal, ...],
    intervals: tuple[IntervalDiagnostic, ...],
    interval_outcomes: tuple[_SearchOutcome, ...],
    policy: OrderedSubgraphV2Policy,
) -> tuple[tuple[RankedPathDiagnostic, ...], tuple[Decimal, ...]]:
    row_by_id = {item.row_id: item for item in rows}
    node_by_id = {item.report_norm_id: item for item in nodes}
    anchor_matches = tuple(
        _anchor_path_match(item, row_by_id, node_by_id, policy) for item in anchors
    )
    combinations: list[tuple[Decimal, int, tuple[PathMatchDiagnostic, ...]]] = [
        (Decimal(0), 0, anchor_matches)
    ]
    for interval, outcome in zip(intervals, interval_outcomes, strict=True):
        proposed: list[tuple[Decimal, int, tuple[PathMatchDiagnostic, ...]]] = []
        for score, adjacency, matches in combinations:
            for path, raw_path_score in zip(
                interval.ranked_paths,
                outcome.raw_scores,
                strict=True,
            ):
                proposed.append(
                    (
                        score + raw_path_score,
                        adjacency + path.adjacency_tiebreak_count,
                        (*matches, *path.matches),
                    )
                )
        deduplicated: dict[
            tuple[tuple[str, int], ...], tuple[Decimal, int, tuple[PathMatchDiagnostic, ...]]
        ] = {}
        for item in proposed:
            signature = tuple((match.row_id, match.report_norm_id) for match in item[2])
            old = deduplicated.get(signature)
            if old is None or item[:2] > old[:2]:
                deduplicated[signature] = item
        combinations = sorted(
            deduplicated.values(),
            key=lambda item: (
                -item[0],
                -item[1],
                tuple((match.row_id, match.report_norm_id) for match in item[2]),
            ),
        )[: policy.returned_path_limit]
    materialized: list[RankedPathDiagnostic] = []
    for rank, (score, adjacency, raw_matches) in enumerate(combinations, start=1):
        matches = tuple(sorted(raw_matches, key=lambda item: item.row_order))
        matched_rows = {item.row_id for item in matches}
        matched_nodes = {item.report_norm_id for item in matches}
        materialized.append(
            RankedPathDiagnostic(
                rank=rank,
                total_score=_diagnostic_score(score),
                adjacency_tiebreak_count=adjacency,
                matches=matches,
                skipped_row_ids=tuple(
                    item.row_id for item in rows if item.row_id not in matched_rows
                ),
                skipped_report_norm_ids=tuple(
                    item.report_norm_id
                    for item in nodes
                    if item.report_norm_id not in matched_nodes
                ),
                structural_issues=(),
            )
        )
    return tuple(materialized), tuple(item[0] for item in combinations)


def _row_mapping_records(
    rows: tuple[SourceStructureRowV2, ...],
    nodes: tuple[SchemaProjectionNodeV2, ...],
    anchor_diagnostics: tuple[AnchorDiagnostic, ...],
    intervals: tuple[IntervalDiagnostic, ...],
    policy: OrderedSubgraphV2Policy,
) -> tuple[RowMappingRecordV2, ...]:
    node_by_id = {item.report_norm_id: item for item in nodes}
    anchor_by_row = {
        item.row_id: item
        for item in anchor_diagnostics
        if item.constraint_report_norm_id is not None
        and item.status
        in {
            RowMappingStatus.RESOLVED_ANCHOR.value,
            RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value,
        }
    }
    interval_by_row = {row_id: interval for interval in intervals for row_id in interval.row_ids}
    results: list[RowMappingRecordV2] = []
    for row in rows:
        if not row.target_template_in_scope:
            results.append(
                RowMappingRecordV2(
                    row.row_id,
                    RowMappingStatus.OUT_OF_SCOPE_FOR_TARGET_TEMPLATE.value,
                    None,
                    (),
                    None
                    if row.row_id in anchor_by_row
                    else interval_by_row[row.row_id].interval_index,
                    "source structure excludes this visible row from the target template",
                )
            )
            continue
        if row.row_id in anchor_by_row:
            anchor = anchor_by_row[row.row_id]
            selected = anchor.selected_report_norm_id
            status = (
                RowMappingStatus.RESOLVED_ANCHOR
                if selected is not None
                else RowMappingStatus.AMBIGUOUS_ACROSS_PATHS
            )
            candidate_ids = [anchor.constraint_report_norm_id]
            alternative_id = anchor.counterfactual_alternative_report_norm_id
            alternative_is_strong = False
            if alternative_id is not None:
                alternative_node = node_by_id[alternative_id]
                raw_alternative_score = max(
                    (
                        _raw_score(_label_similarity(label, alternative_node))
                        for label in row.labels_by_reader.values()
                    ),
                    default=Decimal(0),
                )
                alternative_is_strong = raw_alternative_score >= _raw_score(
                    policy.minimum_strong_label_score
                )
            if selected is None and alternative_id is not None and alternative_is_strong:
                candidate_ids.append(alternative_id)
            results.append(
                RowMappingRecordV2(
                    row.row_id,
                    status.value,
                    selected,
                    tuple(dict.fromkeys(candidate_ids)),
                    None,
                    anchor.reason,
                )
            )
            continue
        interval = interval_by_row[row.row_id]
        candidate_ids = tuple(
            dict.fromkeys(
                item.report_norm_id
                for item in interval.candidate_pairs
                if item.row_id == row.row_id
            )
        )
        selected_in_best = next(
            (
                item.report_norm_id
                for item in interval.best_path.matches
                if item.row_id == row.row_id
            ),
            None,
        )
        if not candidate_ids:
            status = RowMappingStatus.NO_ADMISSIBLE_PAIR
            selected = None
            reason = "no candidate passes label, role, scope, and parent admissibility"
        elif interval.status == RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value:
            status = RowMappingStatus.AMBIGUOUS_ACROSS_PATHS
            selected = None
            reason = "interval is ambiguous; best-path ID is retained only in diagnostics"
        elif selected_in_best is None:
            status = RowMappingStatus.BEST_PATH_SKIPPED
            selected = None
            reason = "zero-baseline best path retains this admissible row as unmatched"
        else:
            status = RowMappingStatus.RESOLVED_PATH
            selected = selected_in_best
            reason = "decisive interval path selected this row/ReportNormId pair"
        results.append(
            RowMappingRecordV2(
                row.row_id,
                status.value,
                selected,
                candidate_ids,
                interval.interval_index,
                reason,
            )
        )
    return tuple(results)


def _enforce_selected_direct_parent_closure(
    source_rows: tuple[SourceStructureRowV2, ...],
    nodes: tuple[SchemaProjectionNodeV2, ...],
    records: tuple[RowMappingRecordV2, ...],
) -> tuple[tuple[RowMappingRecordV2, ...], dict[str, str]]:
    """Null selected descendants until every direct-parent dependency is selected."""

    records_by_row = {item.row_id: item for item in records}
    node_by_id = {item.report_norm_id: item for item in nodes}
    invalidated: dict[str, str] = {}
    while True:
        changed = False
        for row in source_rows:
            if _relation(row) is not SourceRelationType.DIRECT_PARENT:
                continue
            record = records_by_row[row.row_id]
            if record.selected_report_norm_id is None:
                continue
            parent_record = records_by_row[row.parent_row_id or ""]
            parent_selected = parent_record.selected_report_norm_id
            child_node = node_by_id[record.selected_report_norm_id]
            if parent_selected is None:
                reason = (
                    "selected mapping was withheld because its sealed direct parent "
                    "has no final selected ReportNormId"
                )
            elif child_node.parent_report_norm_id != parent_selected:
                reason = (
                    "selected mapping was withheld because its schema parent differs "
                    "from the final selected direct-parent ReportNormId"
                )
            else:
                continue
            invalidated[row.row_id] = reason
            records_by_row[row.row_id] = replace(
                record,
                status=RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value,
                selected_report_norm_id=None,
                reason=reason,
            )
            changed = True
        if not changed:
            break
    return tuple(records_by_row[row.row_id] for row in source_rows), invalidated


def _withhold_dependency_invalidated_anchors(
    diagnostics: tuple[AnchorDiagnostic, ...], invalidated: Mapping[str, str]
) -> tuple[AnchorDiagnostic, ...]:
    return tuple(
        replace(
            item,
            status=RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value,
            selected_report_norm_id=None,
            selection_allowed=False,
            reason=invalidated[item.row_id],
        )
        if item.row_id in invalidated and item.selected_report_norm_id is not None
        else item
        for item in diagnostics
    )


def _schema_dispositions(
    nodes: tuple[SchemaProjectionNodeV2, ...],
    rows: tuple[RowMappingRecordV2, ...],
) -> tuple[SchemaDispositionV2, ...]:
    selected = {
        row.selected_report_norm_id: row.row_id
        for row in rows
        if row.selected_report_norm_id is not None
    }
    candidates: dict[int, list[str]] = {}
    statuses: dict[int, set[str]] = {}
    for row in rows:
        for schema_id in row.candidate_report_norm_ids:
            candidates.setdefault(schema_id, []).append(row.row_id)
            statuses.setdefault(schema_id, set()).add(row.status)
    result: list[SchemaDispositionV2] = []
    for node in nodes:
        selected_row = selected.get(node.report_norm_id)
        candidate_rows = tuple(dict.fromkeys(candidates.get(node.report_norm_id, [])))
        candidate_statuses = statuses.get(node.report_norm_id, set())
        if selected_row is not None:
            status = "MAPPED"
            reason = "a decisive anchor or interval path selected this schema node"
        elif RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value in candidate_statuses:
            status = RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value
            reason = "candidate schema node participates in an ambiguous interval"
        elif candidate_rows:
            status = "UNMATCHED_SCHEMA_NODE_WITH_SKIPPED_CANDIDATES"
            reason = "admissible candidates exist but zero-baseline best path did not select them"
        else:
            status = "UNMATCHED_SCHEMA_NODE"
            reason = "mapping-only evidence does not establish a matching visible row"
        result.append(
            SchemaDispositionV2(
                node.report_norm_id,
                status,
                selected_row,
                candidate_rows,
                reason,
            )
        )
    return tuple(result)


def align_ordered_subgraph_v2(
    rows: Sequence[SourceStructureRowV2],
    projection: SchemaProjectionV2,
    *,
    policy: OrderedSubgraphV2Policy,
) -> OrderedSubgraphV2Result:
    """Map sealed source structure and reader labels to workbook-ordered IDs.

    V2 deliberately accepts in-memory evidence only. It cannot discover or open
    upstream experiment, review, history, period, or numeric artifacts.
    """

    canonical_policy = load_ordered_subgraph_v2_policy_bytes(
        policy.source_bytes,
        source_path=policy.source_path,
    )
    if canonical_policy != policy:
        raise OrderedSubgraphV2Error("in-memory mapping policy differs from its source bytes")
    ordered_rows = _validated_rows(rows, projection)
    nodes = _ordered_projection_nodes(projection)
    diagnostics, anchors, anchor_conflict, conflict_reasons = _anchor_prepass(
        ordered_rows, nodes, policy
    )
    intervals = _partition_intervals(ordered_rows, nodes, anchors)
    resolved: dict[str, int] = {item.row_id: item.report_norm_id for item in anchors}
    interval_results: list[IntervalDiagnostic] = []
    primary_outcomes: list[_SearchOutcome] = []
    dp_cells = generated = retained = counterfactual_searches = 0
    main_pruned = counterfactual_pruned = 0
    for interval in intervals:
        diagnostic, search_outcomes = _evaluate_interval(
            interval,
            resolved,
            policy,
            forced_ambiguous=anchor_conflict,
        )
        interval_results.append(diagnostic)
        primary_outcome, *counterfactual_outcomes = search_outcomes
        primary_outcomes.append(primary_outcome)
        for outcome in search_outcomes:
            dp_cells += outcome.dp_cells
            generated += outcome.generated_states
            retained += outcome.retained_states
        counterfactual_searches += len(counterfactual_outcomes)
        main_pruned += primary_outcome.pruned_states
        counterfactual_pruned += sum(outcome.pruned_states for outcome in counterfactual_outcomes)
        if diagnostic.status == RowMappingStatus.RESOLVED_PATH.value:
            resolved.update(
                (item.row_id, item.report_norm_id) for item in diagnostic.best_path.matches
            )
    frozen_intervals = tuple(interval_results)
    finalized_anchors, frozen_intervals = _close_unselected_anchor_boundaries(
        diagnostics,
        anchors,
        frozen_intervals,
        ordered_rows,
        nodes,
        policy,
    )
    row_mappings = _row_mapping_records(
        ordered_rows,
        nodes,
        finalized_anchors,
        frozen_intervals,
        policy,
    )
    row_mappings, dependency_invalidated = _enforce_selected_direct_parent_closure(
        ordered_rows,
        nodes,
        row_mappings,
    )
    finalized_anchors = _withhold_dependency_invalidated_anchors(
        finalized_anchors,
        dependency_invalidated,
    )
    schema_dispositions = _schema_dispositions(nodes, row_mappings)
    global_paths, global_raw_scores = _global_paths(
        ordered_rows,
        nodes,
        anchors,
        frozen_intervals,
        tuple(primary_outcomes),
        policy,
    )
    best = global_paths[0]
    runner = global_paths[1] if len(global_paths) > 1 else None
    margin = (
        None
        if len(global_raw_scores) < 2
        else _diagnostic_score(global_raw_scores[0] - global_raw_scores[1])
    )
    ambiguous = (
        anchor_conflict
        or any(
            item.constraint_report_norm_id is not None
            and item.status == RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value
            for item in finalized_anchors
        )
        or any(
            item.status == RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value
            for item in frozen_intervals
        )
        or bool(dependency_invalidated)
    )
    status = MappingRunStatus.AMBIGUOUS_MAPPING if ambiguous else MappingRunStatus.RESOLVED
    reason_parts = list(conflict_reasons)
    if dependency_invalidated:
        reason_parts.append(
            "selected direct-parent dependency closure withheld rows: "
            + ", ".join(sorted(dependency_invalidated))
        )
    if ambiguous:
        reason_parts.append("one or more anchored intervals fail decisive fail-closed gates")
    else:
        reason_parts.append("all selected IDs are decisive; unmatched evidence is retained")
    if _sha256_bytes(policy.source_bytes) != policy.policy_sha256:
        raise OrderedSubgraphV2Error("mapping policy bytes/hash identity drifted")
    return OrderedSubgraphV2Result(
        status=status,
        automatic_selection_allowed=not ambiguous,
        anchors=finalized_anchors,
        intervals=frozen_intervals,
        best_path=best,
        runner_up_path=runner,
        score_margin=margin,
        ranked_paths=global_paths,
        row_mappings=row_mappings,
        schema_dispositions=schema_dispositions,
        reason="; ".join(reason_parts),
        schema_projection_sha256=projection.projection_sha256,
        schema_alias_authority=projection.alias_authority,
        policy_sha256=policy.policy_sha256,
        search=SearchStatsV2(
            algorithm=policy.mode,
            intervals=len(intervals),
            dp_cells=dp_cells,
            generated_states=generated,
            retained_states=retained,
            pruned_states=main_pruned + counterfactual_pruned,
            main_search_pruned_states=main_pruned,
            counterfactual_search_pruned_states=counterfactual_pruned,
            counterfactual_searches=counterfactual_searches,
            beam_width_per_dp_cell=policy.beam_width,
        ),
    )


def result_json(result: OrderedSubgraphV2Result) -> str:
    """Return canonical UTF-8-safe JSON for an already computed result."""

    return json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
