from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from rapidfuzz.fuzz import ratio

from bctc_ai.core.text import normalize_text, retrieval_key
from bctc_ai.mapping.alignment_v2 import MappingDecisionStatus
from bctc_ai.mapping.scope import ScopePolicy, classify_mapping_scopes
from bctc_ai.schema.registry import SchemaItem

_SCORE_SCALE = 1_000_000
_EXPECTED_MODE = "K_BEST_MONOTONE_DYNAMIC_PROGRAMMING_FAIL_CLOSED"


@dataclass(frozen=True)
class OrderedSubgraphPolicy:
    version: int
    mode: str
    calibration_status: str
    ordering_authority: str
    beam_width: int
    returned_path_limit: int
    minimum_candidate_similarity: float
    minimum_pair_score: float
    parent_label_similarity: float
    section_label_similarity: float
    minimum_matches: int
    minimum_mean_pair_score: float
    minimum_path_margin: float
    default_minimum_schema_coverage: float
    maximum_indentation_distance: int
    require_zero_structural_issues: bool
    scoring: Mapping[str, float]
    source_path: Path


@dataclass(frozen=True)
class SchemaGraphNode:
    schema_id: int
    canonical_name: str
    normalized_label: str
    aliases: tuple[str, ...]
    statement_type: str
    display_order: int
    parent_id: int | None
    children: tuple[int, ...]
    hierarchy_level: int | None
    previous_id: int | None
    next_id: int | None
    section_path: tuple[int, ...]
    scopes: tuple[str, ...]
    cash_flow_branch: str | None


@dataclass(frozen=True)
class SchemaGraph:
    statement_type: str
    nodes: tuple[SchemaGraphNode, ...]
    graph_sha256: str

    def by_id(self) -> dict[int, SchemaGraphNode]:
        return {node.schema_id: node for node in self.nodes}


@dataclass(frozen=True)
class PdfGraphRow:
    row_id: str
    label: str
    order: int
    statement_type: str
    scope: str
    section_heading: str | None = None
    section_schema_id: int | None = None
    table_id: str | None = None
    parent_row_id: str | None = None
    parent_schema_id: int | None = None
    parent_label: str | None = None
    previous_schema_id: int | None = None
    next_schema_id: int | None = None
    indentation_level: int | None = None
    numbering: str | None = None
    target_template_in_scope: bool = True


@dataclass(frozen=True)
class MappingBlockContext:
    statement_type: str
    scope: str
    table_id: str
    schema_cluster_ids: tuple[int, ...]
    section_schema_id: int | None = None
    section_heading: str | None = None
    cash_flow_branch: str | None = None
    previous_anchor_schema_id: int | None = None
    next_anchor_schema_id: int | None = None
    block_is_exhaustive_for_schema_cluster: bool = False
    minimum_schema_coverage: float | None = None


@dataclass(frozen=True)
class PairFeatures:
    exact_label: bool
    label_similarity: float
    accounting_semantic_similarity: float | None
    parent_similarity: float | None
    section_similarity: float | None
    indentation_distance: int | None
    numbering_match: bool | None
    local_score: float
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ClusterMatch:
    row_id: str
    schema_id: int
    pdf_order: int
    schema_display_order: int
    pair_score: float
    features: PairFeatures


@dataclass(frozen=True)
class AlignmentPath:
    rank: int
    total_score: float
    mean_pair_score: float
    matches: tuple[ClusterMatch, ...]
    skipped_pdf_row_ids: tuple[str, ...]
    skipped_schema_ids: tuple[int, ...]
    schema_coverage: float
    structural_issues: tuple[str, ...]


@dataclass(frozen=True)
class RowDisposition:
    row_id: str
    status: str
    schema_id: int | None
    reason: str


@dataclass(frozen=True)
class SchemaDisposition:
    schema_id: int
    status: str
    row_id: str | None
    reason: str


@dataclass(frozen=True)
class SearchStats:
    algorithm: str
    pdf_rows: int
    schema_nodes: int
    dp_cells: int
    beam_width_per_cell: int
    generated_states: int
    retained_states: int


@dataclass(frozen=True)
class OrderedSubgraphResult:
    status: MappingDecisionStatus
    automatic_selection_allowed: bool
    best_path: AlignmentPath | None
    runner_up_path: AlignmentPath | None
    score_margin: float | None
    ranked_paths: tuple[AlignmentPath, ...]
    row_dispositions: tuple[RowDisposition, ...]
    schema_dispositions: tuple[SchemaDisposition, ...]
    reason: str
    graph_sha256: str
    search: SearchStats


@dataclass(frozen=True)
class _PathState:
    score_units: int
    matches: tuple[ClusterMatch, ...]
    matched_indices: tuple[tuple[int, int], ...]
    structural_issues: tuple[str, ...]

    @property
    def signature(self) -> tuple[tuple[str, int], ...]:
        return tuple((match.row_id, match.schema_id) for match in self.matches)


def _mapping(payload: Mapping[str, Any], key: str, source: Path) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"ordered-subgraph policy has invalid {key}: {source}")
    return value


def _bounded_float(
    payload: Mapping[str, Any], key: str, source: Path, *, minimum: float, maximum: float
) -> float:
    try:
        value = float(payload[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"ordered-subgraph policy has invalid {key}: {source}") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"ordered-subgraph policy has out-of-range {key}: {source}")
    return value


def load_ordered_subgraph_policy(path: Path) -> OrderedSubgraphPolicy:
    payload: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    search = _mapping(payload, "search", path)
    candidates = _mapping(payload, "candidate_gates", path)
    acceptance = _mapping(payload, "acceptance_gates", path)
    scoring = _mapping(payload, "scoring", path)
    if (
        payload.get("version") != 1
        or payload.get("mode") != _EXPECTED_MODE
        or payload.get("ordering_authority") != "WORKBOOK_DISPLAY_ORDER_ONLY"
        or payload.get("numeric_report_norm_id_sort_allowed") is not False
        or payload.get("value_features_allowed") is not False
        or payload.get("historical_features_allowed") is not False
    ):
        raise ValueError(f"ordered-subgraph policy identity is unsafe: {path}")
    required_scores = {
        "pdf_row_skip_penalty",
        "out_of_scope_pdf_row_skip_penalty",
        "schema_row_skip_penalty",
        "label_similarity_weight",
        "accounting_semantic_similarity_weight",
        "exact_label_bonus",
        "statement_context_bonus",
        "section_context_bonus",
        "parent_exact_bonus",
        "parent_label_similarity_weight",
        "neighbor_immediate_bonus",
        "neighbor_direction_bonus",
        "indentation_exact_bonus",
        "indentation_near_bonus",
        "indentation_conflict_penalty",
        "numbering_exact_bonus",
        "numbering_conflict_penalty",
        "adjacent_schema_bonus",
        "sibling_consistency_bonus",
        "child_consistency_bonus",
        "unresolved_parent_penalty",
        "gap_imbalance_penalty",
    }
    if set(scoring) != required_scores:
        raise ValueError(f"ordered-subgraph scoring keys drifted: {path}")
    numeric_scoring = {key: float(value) for key, value in scoring.items()}
    if any(
        numeric_scoring[key] > 0
        for key in (
            "pdf_row_skip_penalty",
            "out_of_scope_pdf_row_skip_penalty",
            "schema_row_skip_penalty",
            "indentation_conflict_penalty",
            "numbering_conflict_penalty",
            "unresolved_parent_penalty",
            "gap_imbalance_penalty",
        )
    ):
        raise ValueError(f"ordered-subgraph penalties must be non-positive: {path}")
    beam_width = int(search.get("beam_width_per_dp_cell", 0))
    returned_paths = int(search.get("returned_path_limit", 0))
    minimum_matches = int(acceptance.get("minimum_matches", 0))
    maximum_indent = int(acceptance.get("maximum_indentation_distance", -1))
    if beam_width < 2 or returned_paths < 2 or returned_paths > beam_width:
        raise ValueError(f"ordered-subgraph beam/path limits are unsafe: {path}")
    if minimum_matches < 1 or maximum_indent < 0:
        raise ValueError(f"ordered-subgraph acceptance counts are unsafe: {path}")
    return OrderedSubgraphPolicy(
        version=1,
        mode=_EXPECTED_MODE,
        calibration_status=str(payload.get("calibration_status", "")),
        ordering_authority="WORKBOOK_DISPLAY_ORDER_ONLY",
        beam_width=beam_width,
        returned_path_limit=returned_paths,
        minimum_candidate_similarity=_bounded_float(
            candidates,
            "minimum_label_or_accounting_semantic_similarity",
            path,
            minimum=0,
            maximum=1,
        ),
        minimum_pair_score=_bounded_float(
            candidates, "minimum_pair_score", path, minimum=0, maximum=10
        ),
        parent_label_similarity=_bounded_float(
            candidates, "parent_label_similarity", path, minimum=0, maximum=1
        ),
        section_label_similarity=_bounded_float(
            candidates, "section_label_similarity", path, minimum=0, maximum=1
        ),
        minimum_matches=minimum_matches,
        minimum_mean_pair_score=_bounded_float(
            acceptance, "minimum_mean_pair_score", path, minimum=0, maximum=10
        ),
        minimum_path_margin=_bounded_float(
            acceptance, "minimum_best_runner_up_margin", path, minimum=0, maximum=10
        ),
        default_minimum_schema_coverage=_bounded_float(
            acceptance, "default_minimum_schema_coverage", path, minimum=0, maximum=1
        ),
        maximum_indentation_distance=maximum_indent,
        require_zero_structural_issues=(acceptance.get("require_zero_structural_issues") is True),
        scoring=numeric_scoring,
        source_path=path.resolve(),
    )


def _section_path(item: SchemaItem, by_id: Mapping[int, SchemaItem]) -> tuple[int, ...]:
    result = [item.schema_id]
    seen = {item.schema_id}
    current = item
    while current.parent_id is not None:
        if current.parent_id in seen:
            raise ValueError(f"schema hierarchy cycle containing {current.parent_id}")
        parent = by_id.get(current.parent_id)
        if parent is None:
            raise ValueError(
                f"schema item {current.schema_id} has missing parent {current.parent_id}"
            )
        result.append(parent.schema_id)
        seen.add(parent.schema_id)
        current = parent
    return tuple(reversed(result))


def build_schema_graph(schema: Sequence[SchemaItem], statement_type: str) -> SchemaGraph:
    statement_items = [item for item in schema if item.statement_type == statement_type]
    statement_items.sort(key=lambda item: item.display_order)
    if not statement_items:
        raise ValueError(f"schema statement has no rows: {statement_type}")
    ids = [item.schema_id for item in statement_items]
    orders = [item.display_order for item in statement_items]
    if len(ids) != len(set(ids)) or len(orders) != len(set(orders)):
        raise ValueError(f"schema graph IDs/display orders are not unique: {statement_type}")
    by_id = {item.schema_id: item for item in statement_items}
    nodes: list[SchemaGraphNode] = []
    for index, item in enumerate(statement_items):
        expected_previous = statement_items[index - 1].schema_id if index else None
        expected_next = (
            statement_items[index + 1].schema_id if index + 1 < len(statement_items) else None
        )
        if item.previous_id != expected_previous or item.next_id != expected_next:
            raise ValueError(f"schema workbook-neighbor drift at {statement_type}:{item.schema_id}")
        aliases = tuple(
            dict.fromkeys(
                label
                for label in (
                    item.canonical_name,
                    *item.structural_aliases,
                    *item.historical_aliases,
                )
                if normalize_text(label)
            )
        )
        nodes.append(
            SchemaGraphNode(
                schema_id=item.schema_id,
                canonical_name=item.canonical_name,
                normalized_label=item.normalized_name,
                aliases=aliases,
                statement_type=item.statement_type,
                display_order=item.display_order,
                parent_id=item.parent_id,
                children=tuple(item.children),
                hierarchy_level=item.hierarchy_level,
                previous_id=item.previous_id,
                next_id=item.next_id,
                section_path=_section_path(item, by_id),
                scopes=tuple(item.scope),
                cash_flow_branch=item.cash_flow_branch,
            )
        )
    serialized = [
        {
            "schema_id": node.schema_id,
            "canonical_name": node.canonical_name,
            "normalized_label": node.normalized_label,
            "statement_type": node.statement_type,
            "display_order": node.display_order,
            "parent_id": node.parent_id,
            "children": node.children,
            "hierarchy_level": node.hierarchy_level,
            "previous_id": node.previous_id,
            "next_id": node.next_id,
            "section_path": node.section_path,
        }
        for node in nodes
    ]
    digest = hashlib.sha256(
        json.dumps(serialized, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return SchemaGraph(statement_type=statement_type, nodes=tuple(nodes), graph_sha256=digest)


def _similarity(left: str, right: str) -> float:
    return ratio(retrieval_key(left), retrieval_key(right)) / 100.0


def _node_label_similarity(label: str, node: SchemaGraphNode) -> tuple[bool, float]:
    normalized = normalize_text(label).casefold()
    exact = any(normalized == normalize_text(alias).casefold() for alias in node.aliases)
    similarity = max((_similarity(label, alias) for alias in node.aliases), default=0.0)
    return exact, similarity


def _score_units(value: float) -> int:
    return round(value * _SCORE_SCALE)


def _score_value(units: int) -> float:
    return round(units / _SCORE_SCALE, 6)


def _candidate_nodes(
    graph: SchemaGraph,
    context: MappingBlockContext,
) -> tuple[SchemaGraphNode, ...]:
    by_id = graph.by_id()
    missing = [schema_id for schema_id in context.schema_cluster_ids if schema_id not in by_id]
    if missing:
        raise ValueError(f"schema cluster contains unknown IDs: {missing}")
    if len(context.schema_cluster_ids) != len(set(context.schema_cluster_ids)):
        raise ValueError("schema cluster IDs are duplicated")
    previous = by_id.get(context.previous_anchor_schema_id)
    following = by_id.get(context.next_anchor_schema_id)
    if context.previous_anchor_schema_id is not None and previous is None:
        raise ValueError("previous schema anchor is unknown")
    if context.next_anchor_schema_id is not None and following is None:
        raise ValueError("next schema anchor is unknown")
    if previous and following and previous.display_order >= following.display_order:
        raise ValueError("schema anchors violate workbook display order")
    selected = []
    for schema_id in context.schema_cluster_ids:
        node = by_id[schema_id]
        if previous and node.display_order <= previous.display_order:
            raise ValueError(f"schema cluster ID {schema_id} is not after the previous anchor")
        if following and node.display_order >= following.display_order:
            raise ValueError(f"schema cluster ID {schema_id} is not before the next anchor")
        if (
            context.section_schema_id is not None
            and context.section_schema_id not in node.section_path
        ):
            raise ValueError(f"schema cluster ID {schema_id} lies outside the verified section")
        if context.cash_flow_branch and node.cash_flow_branch != context.cash_flow_branch:
            raise ValueError(f"schema cluster ID {schema_id} lies outside the cash-flow branch")
        if context.scope and node.scopes and context.scope not in node.scopes:
            raise ValueError(f"schema cluster ID {schema_id} conflicts with report scope")
        selected.append(node)
    selected.sort(key=lambda node: node.display_order)
    return tuple(selected)


def _validate_rows(
    rows: Sequence[PdfGraphRow], graph: SchemaGraph, context: MappingBlockContext
) -> tuple[PdfGraphRow, ...]:
    if graph.statement_type != context.statement_type:
        raise ValueError("schema graph and block statement differ")
    ordered = tuple(sorted(rows, key=lambda row: row.order))
    if len({row.row_id for row in ordered}) != len(ordered):
        raise ValueError("PDF graph row IDs are not unique")
    if len({row.order for row in ordered}) != len(ordered):
        raise ValueError("PDF graph row orders are not unique")
    known_row_ids = {row.row_id for row in ordered}
    for row in ordered:
        if row.statement_type != context.statement_type:
            raise ValueError(f"row {row.row_id} belongs to another statement")
        if row.scope != context.scope:
            raise ValueError(f"row {row.row_id} conflicts with verified report scope")
        if row.table_id is not None and row.table_id != context.table_id:
            raise ValueError(f"row {row.row_id} belongs to another table")
        if row.parent_row_id is not None and row.parent_row_id not in known_row_ids:
            raise ValueError(f"row {row.row_id} references an unknown PDF parent")
        if row.parent_row_id == row.row_id:
            raise ValueError(f"row {row.row_id} is its own parent")
        if row.parent_row_id is not None:
            parent = next(
                candidate for candidate in ordered if candidate.row_id == row.parent_row_id
            )
            if parent.order >= row.order:
                raise ValueError(f"row {row.row_id} has a non-preceding PDF parent")
    return ordered


def _semantic_score(
    scores: Mapping[tuple[str, int], float], row_id: str, schema_id: int
) -> float | None:
    value = scores.get((row_id, schema_id))
    if value is None:
        return None
    numeric = float(value)
    if not 0 <= numeric <= 1:
        raise ValueError("accounting semantic similarities must be normalized to [0, 1]")
    return numeric


def _parent_node(node: SchemaGraphNode, graph_by_id: Mapping[int, SchemaGraphNode]):
    return graph_by_id.get(node.parent_id) if node.parent_id is not None else None


def _base_pair_features(
    row: PdfGraphRow,
    node: SchemaGraphNode,
    *,
    graph_by_id: Mapping[int, SchemaGraphNode],
    context: MappingBlockContext,
    policy: OrderedSubgraphPolicy,
    semantic_scores: Mapping[tuple[str, int], float],
    schema_numbering: Mapping[int, str],
) -> tuple[PairFeatures, tuple[str, ...]] | None:
    if row.section_schema_id is not None and row.section_schema_id not in node.section_path:
        return None
    if row.parent_schema_id is not None and node.parent_id != row.parent_schema_id:
        return None
    previous = graph_by_id.get(row.previous_schema_id)
    following = graph_by_id.get(row.next_schema_id)
    if row.previous_schema_id is not None and previous is None:
        raise ValueError(f"row {row.row_id} has an unknown previous schema anchor")
    if row.next_schema_id is not None and following is None:
        raise ValueError(f"row {row.row_id} has an unknown next schema anchor")
    if previous and node.display_order <= previous.display_order:
        return None
    if following and node.display_order >= following.display_order:
        return None

    exact, label_similarity = _node_label_similarity(row.label, node)
    semantic_similarity = _semantic_score(semantic_scores, row.row_id, node.schema_id)
    candidate_similarity = max(label_similarity, semantic_similarity or 0.0)
    if candidate_similarity < policy.minimum_candidate_similarity:
        return None
    scoring = policy.scoring
    score = scoring["statement_context_bonus"]
    evidence = ["statement and table context matched"]
    issues: list[str] = []
    score += scoring["label_similarity_weight"] * label_similarity
    if exact:
        score += scoring["exact_label_bonus"]
        evidence.append("source-normalized label matched exactly")
    if semantic_similarity is not None:
        score += scoring["accounting_semantic_similarity_weight"] * semantic_similarity
        evidence.append("external accounting-semantic proposal scored; no value/history used")

    section_similarity: float | None = None
    section_heading = row.section_heading or context.section_heading
    if context.section_schema_id is not None or row.section_schema_id is not None:
        score += scoring["section_context_bonus"]
        evidence.append("candidate belongs to verified schema section")
    elif section_heading:
        ancestor_nodes = [graph_by_id[schema_id] for schema_id in node.section_path]
        section_similarity = max(
            (_similarity(section_heading, ancestor.canonical_name) for ancestor in ancestor_nodes),
            default=0.0,
        )
        if section_similarity >= policy.section_label_similarity:
            score += scoring["section_context_bonus"] * section_similarity
            evidence.append("candidate ancestor matches observed section heading")
        else:
            issues.append(f"row {row.row_id}: section heading is not structurally corroborated")

    parent = _parent_node(node, graph_by_id)
    parent_similarity: float | None = None
    if row.parent_schema_id is not None:
        score += scoring["parent_exact_bonus"]
        evidence.append("candidate matches verified parent schema ID")
    elif row.parent_label:
        parent_similarity = (
            _node_label_similarity(row.parent_label, parent)[1] if parent is not None else 0.0
        )
        score += scoring["parent_label_similarity_weight"] * parent_similarity
        if parent_similarity >= policy.parent_label_similarity:
            evidence.append("candidate parent matches observed parent label")
        else:
            issues.append(f"row {row.row_id}: parent label is not structurally corroborated")

    if previous:
        if node.previous_id == previous.schema_id:
            score += scoring["neighbor_immediate_bonus"]
            evidence.append("candidate immediately follows verified previous anchor")
        else:
            score += scoring["neighbor_direction_bonus"]
            evidence.append("candidate follows previous anchor in workbook order")
    if following:
        if node.next_id == following.schema_id:
            score += scoring["neighbor_immediate_bonus"]
            evidence.append("candidate immediately precedes verified next anchor")
        else:
            score += scoring["neighbor_direction_bonus"]
            evidence.append("candidate precedes next anchor in workbook order")

    indentation_distance: int | None = None
    if row.indentation_level is not None and node.hierarchy_level is not None:
        indentation_distance = abs(row.indentation_level - node.hierarchy_level)
        if indentation_distance == 0:
            score += scoring["indentation_exact_bonus"]
        elif indentation_distance == 1:
            score += scoring["indentation_near_bonus"]
        else:
            score += scoring["indentation_conflict_penalty"] * indentation_distance
            issues.append(
                f"row {row.row_id}: indentation/hierarchy distance={indentation_distance}"
            )
    numbering_match: bool | None = None
    if row.numbering and node.schema_id in schema_numbering:
        numbering_match = retrieval_key(row.numbering) == retrieval_key(
            schema_numbering[node.schema_id]
        )
        if numbering_match:
            score += scoring["numbering_exact_bonus"]
            evidence.append("row numbering matches schema structural metadata")
        else:
            score += scoring["numbering_conflict_penalty"]
            issues.append(f"row {row.row_id}: numbering conflicts with schema metadata")
    if score < policy.minimum_pair_score:
        return None
    return (
        PairFeatures(
            exact_label=exact,
            label_similarity=round(label_similarity, 6),
            accounting_semantic_similarity=(
                None if semantic_similarity is None else round(semantic_similarity, 6)
            ),
            parent_similarity=(None if parent_similarity is None else round(parent_similarity, 6)),
            section_similarity=(
                None if section_similarity is None else round(section_similarity, 6)
            ),
            indentation_distance=indentation_distance,
            numbering_match=numbering_match,
            local_score=round(score, 6),
            evidence=tuple(evidence),
        ),
        tuple(issues),
    )


def _transition_match(
    state: _PathState,
    *,
    row_index: int,
    schema_index: int,
    rows: tuple[PdfGraphRow, ...],
    nodes: tuple[SchemaGraphNode, ...],
    graph_by_id: Mapping[int, SchemaGraphNode],
    base: tuple[PairFeatures, tuple[str, ...]],
    policy: OrderedSubgraphPolicy,
) -> _PathState | None:
    row = rows[row_index]
    node = nodes[schema_index]
    features, base_issues = base
    score = features.local_score
    evidence = list(features.evidence)
    issues = list(base_issues)
    mapped_by_row = {match.row_id: match.schema_id for match in state.matches}
    row_by_id = {candidate.row_id: candidate for candidate in rows}
    scoring = policy.scoring

    if row.parent_row_id is not None:
        mapped_parent_id = mapped_by_row.get(row.parent_row_id)
        if mapped_parent_id is not None:
            if node.parent_id != mapped_parent_id:
                return None
            score += scoring["parent_exact_bonus"]
            evidence.append("PDF parent row and schema parent are jointly aligned")
        else:
            observed_parent = row_by_id[row.parent_row_id]
            parent = _parent_node(node, graph_by_id)
            parent_similarity = (
                _node_label_similarity(observed_parent.label, parent)[1]
                if parent is not None
                else 0.0
            )
            if parent_similarity >= policy.parent_label_similarity:
                score += scoring["parent_label_similarity_weight"] * parent_similarity
                evidence.append("unmapped PDF parent label corroborates schema parent")
            else:
                score += scoring["unresolved_parent_penalty"]
                issues.append(f"row {row.row_id}: PDF parent row is not resolved")

    if state.matches:
        last_row_index, last_schema_index = state.matched_indices[-1]
        last_row = rows[last_row_index]
        last_node = nodes[last_schema_index]
        pdf_distance = row_index - last_row_index
        schema_distance = schema_index - last_schema_index
        score += scoring["gap_imbalance_penalty"] * abs(pdf_distance - schema_distance)
        if pdf_distance == 1 and node.previous_id == last_node.schema_id:
            score += scoring["adjacent_schema_bonus"]
            evidence.append("adjacent PDF rows match adjacent workbook rows")
        if (
            row.indentation_level is not None
            and last_row.indentation_level is not None
            and node.parent_id is not None
        ):
            if row.indentation_level == last_row.indentation_level:
                if node.parent_id == last_node.parent_id:
                    score += scoring["sibling_consistency_bonus"]
                    evidence.append("same-indentation rows map as schema siblings")
                elif pdf_distance == 1:
                    issues.append(f"row {row.row_id}: same-indentation sibling relation conflicts")
            elif row.indentation_level == last_row.indentation_level + 1:
                if node.parent_id == last_node.schema_id:
                    score += scoring["child_consistency_bonus"]
                    evidence.append("indentation transition maps as parent-child")
                elif pdf_distance == 1:
                    issues.append(f"row {row.row_id}: child indentation relation conflicts")

    final_features = PairFeatures(
        exact_label=features.exact_label,
        label_similarity=features.label_similarity,
        accounting_semantic_similarity=features.accounting_semantic_similarity,
        parent_similarity=features.parent_similarity,
        section_similarity=features.section_similarity,
        indentation_distance=features.indentation_distance,
        numbering_match=features.numbering_match,
        local_score=round(score, 6),
        evidence=tuple(evidence),
    )
    match = ClusterMatch(
        row_id=row.row_id,
        schema_id=node.schema_id,
        pdf_order=row.order,
        schema_display_order=node.display_order,
        pair_score=round(score, 6),
        features=final_features,
    )
    return _PathState(
        score_units=state.score_units + _score_units(score),
        matches=(*state.matches, match),
        matched_indices=(*state.matched_indices, (row_index, schema_index)),
        structural_issues=tuple(dict.fromkeys((*state.structural_issues, *issues))),
    )


def _retain_best(states: Sequence[_PathState], beam_width: int) -> tuple[_PathState, ...]:
    by_signature: dict[tuple[tuple[str, int], ...], _PathState] = {}
    for state in states:
        previous = by_signature.get(state.signature)
        if previous is None or state.score_units > previous.score_units:
            by_signature[state.signature] = state
    ordered = sorted(
        by_signature.values(),
        key=lambda state: (-state.score_units, -len(state.matches), state.signature),
    )
    return tuple(ordered[:beam_width])


def _materialize_path(
    state: _PathState,
    rank: int,
    rows: tuple[PdfGraphRow, ...],
    nodes: tuple[SchemaGraphNode, ...],
) -> AlignmentPath:
    matched_rows = {match.row_id for match in state.matches}
    matched_schema = {match.schema_id for match in state.matches}
    return AlignmentPath(
        rank=rank,
        total_score=_score_value(state.score_units),
        mean_pair_score=(
            round(sum(match.pair_score for match in state.matches) / len(state.matches), 6)
            if state.matches
            else 0.0
        ),
        matches=state.matches,
        skipped_pdf_row_ids=tuple(row.row_id for row in rows if row.row_id not in matched_rows),
        skipped_schema_ids=tuple(
            node.schema_id for node in nodes if node.schema_id not in matched_schema
        ),
        schema_coverage=round(len(matched_schema) / len(nodes), 6) if nodes else 0.0,
        structural_issues=state.structural_issues,
    )


def _dispositions(
    *,
    status: MappingDecisionStatus,
    best: AlignmentPath | None,
    rows: tuple[PdfGraphRow, ...],
    nodes: tuple[SchemaGraphNode, ...],
    allowed_by_row: Mapping[str, bool],
    context: MappingBlockContext,
) -> tuple[tuple[RowDisposition, ...], tuple[SchemaDisposition, ...]]:
    matched_by_row = {match.row_id: match.schema_id for match in best.matches} if best else {}
    matched_by_schema = {schema_id: row_id for row_id, schema_id in matched_by_row.items()}
    row_results = []
    for row in rows:
        schema_id = matched_by_row.get(row.row_id)
        if not allowed_by_row[row.row_id]:
            row_results.append(
                RowDisposition(
                    row.row_id,
                    MappingDecisionStatus.OUT_OF_SCOPE_FOR_TARGET_TEMPLATE.value,
                    None,
                    "visible row is excluded by target-template scope",
                )
            )
        elif schema_id is not None:
            row_results.append(
                RowDisposition(
                    row.row_id,
                    status.value,
                    schema_id,
                    "cluster path selected this row/schema pair",
                )
            )
        else:
            row_results.append(
                RowDisposition(
                    row.row_id,
                    "UNMATCHED_PDF_ROW_RETAINED",
                    None,
                    "row was not forced into the smaller schema cluster",
                )
            )
    schema_results = []
    for node in nodes:
        row_id = matched_by_schema.get(node.schema_id)
        if row_id is not None:
            schema_results.append(
                SchemaDisposition(
                    node.schema_id,
                    status.value,
                    row_id,
                    "cluster path selected this schema/PDF-row pair",
                )
            )
        elif (
            status is MappingDecisionStatus.RESOLVED
            and context.block_is_exhaustive_for_schema_cluster
        ):
            schema_results.append(
                SchemaDisposition(
                    node.schema_id,
                    "NOT_OBSERVED",
                    None,
                    "exhaustive visible block contains no aligned row for this schema node",
                )
            )
        else:
            schema_results.append(
                SchemaDisposition(
                    node.schema_id,
                    "UNMATCHED_SCHEMA_NODE_IN_BLOCK",
                    None,
                    "block evidence is insufficient to assert document-level absence",
                )
            )
    return tuple(row_results), tuple(schema_results)


def align_ordered_subgraph(
    rows: Sequence[PdfGraphRow],
    graph: SchemaGraph,
    *,
    context: MappingBlockContext,
    policy: OrderedSubgraphPolicy,
    scope_policy: ScopePolicy | None,
    accounting_semantic_scores: Mapping[tuple[str, int], float] | None = None,
    schema_numbering: Mapping[int, str] | None = None,
) -> OrderedSubgraphResult:
    """Align one PDF block to an ordered schema cluster without forced row matches."""

    ordered_rows = _validate_rows(rows, graph, context)
    nodes = _candidate_nodes(graph, context)
    empty_stats = SearchStats(
        policy.mode, len(ordered_rows), len(nodes), 0, policy.beam_width, 0, 0
    )
    if scope_policy is None:
        return OrderedSubgraphResult(
            MappingDecisionStatus.AMBIGUOUS_MAPPING,
            False,
            None,
            None,
            None,
            (),
            tuple(
                RowDisposition(
                    row.row_id,
                    MappingDecisionStatus.AMBIGUOUS_MAPPING.value,
                    None,
                    "scope policy is unavailable",
                )
                for row in ordered_rows
            ),
            tuple(
                SchemaDisposition(
                    node.schema_id,
                    "UNMATCHED_SCHEMA_NODE_IN_BLOCK",
                    None,
                    "scope policy is unavailable",
                )
                for node in nodes
            ),
            "scope policy is required for fail-closed cluster alignment",
            graph.graph_sha256,
            empty_stats,
        )
    if not ordered_rows or not nodes:
        raise ValueError("ordered-subgraph alignment requires non-empty PDF and schema clusters")

    scopes = classify_mapping_scopes(
        [(row.statement_type, row.label) for row in ordered_rows],
        scope_policy,
        initial_section_label=context.section_heading,
    )
    allowed_by_row = {
        row.row_id: row.target_template_in_scope and decision.allowed
        for row, decision in zip(ordered_rows, scopes, strict=True)
    }
    semantic_scores = accounting_semantic_scores or {}
    graph_by_id = graph.by_id()
    numbering = schema_numbering or {}
    unknown_numbering_ids = sorted(set(numbering) - set(graph_by_id))
    if unknown_numbering_ids:
        raise ValueError(f"schema numbering references unknown IDs: {unknown_numbering_ids}")
    base_pairs: dict[tuple[int, int], tuple[PairFeatures, tuple[str, ...]]] = {}
    for row_index, row in enumerate(ordered_rows):
        if not allowed_by_row[row.row_id]:
            continue
        for schema_index, node in enumerate(nodes):
            features = _base_pair_features(
                row,
                node,
                graph_by_id=graph_by_id,
                context=context,
                policy=policy,
                semantic_scores=semantic_scores,
                schema_numbering=numbering,
            )
            if features is not None:
                base_pairs[(row_index, schema_index)] = features

    row_count, schema_count = len(ordered_rows), len(nodes)
    grid: list[list[tuple[_PathState, ...]]] = [
        [tuple() for _ in range(schema_count + 1)] for _ in range(row_count + 1)
    ]
    grid[0][0] = (_PathState(0, (), (), ()),)
    generated_states = 1
    retained_states = 1
    for row_prefix in range(row_count + 1):
        for schema_prefix in range(schema_count + 1):
            if row_prefix == 0 and schema_prefix == 0:
                continue
            proposed: list[_PathState] = []
            if row_prefix > 0:
                row = ordered_rows[row_prefix - 1]
                penalty_key = (
                    "pdf_row_skip_penalty"
                    if allowed_by_row[row.row_id]
                    else "out_of_scope_pdf_row_skip_penalty"
                )
                penalty = _score_units(policy.scoring[penalty_key])
                proposed.extend(
                    _PathState(
                        state.score_units + penalty,
                        state.matches,
                        state.matched_indices,
                        state.structural_issues,
                    )
                    for state in grid[row_prefix - 1][schema_prefix]
                )
            if schema_prefix > 0:
                penalty = _score_units(policy.scoring["schema_row_skip_penalty"])
                proposed.extend(
                    _PathState(
                        state.score_units + penalty,
                        state.matches,
                        state.matched_indices,
                        state.structural_issues,
                    )
                    for state in grid[row_prefix][schema_prefix - 1]
                )
            if row_prefix > 0 and schema_prefix > 0:
                base = base_pairs.get((row_prefix - 1, schema_prefix - 1))
                if base is not None:
                    for state in grid[row_prefix - 1][schema_prefix - 1]:
                        matched = _transition_match(
                            state,
                            row_index=row_prefix - 1,
                            schema_index=schema_prefix - 1,
                            rows=ordered_rows,
                            nodes=nodes,
                            graph_by_id=graph_by_id,
                            base=base,
                            policy=policy,
                        )
                        if matched is not None:
                            proposed.append(matched)
            generated_states += len(proposed)
            grid[row_prefix][schema_prefix] = _retain_best(proposed, policy.beam_width)
            retained_states += len(grid[row_prefix][schema_prefix])

    terminal = grid[row_count][schema_count]
    paths = tuple(
        _materialize_path(state, rank, ordered_rows, nodes)
        for rank, state in enumerate(terminal[: policy.returned_path_limit], start=1)
    )
    best = paths[0] if paths else None
    runner_up = paths[1] if len(paths) > 1 else None
    margin = (
        round(best.total_score - runner_up.total_score, 6)
        if best is not None and runner_up is not None
        else None
    )
    minimum_coverage = (
        policy.default_minimum_schema_coverage
        if context.minimum_schema_coverage is None
        else context.minimum_schema_coverage
    )
    if not 0 <= minimum_coverage <= 1:
        raise ValueError("minimum schema coverage must be in [0, 1]")
    reasons = []
    accepted = best is not None
    if best is None or len(best.matches) < policy.minimum_matches:
        accepted = False
        reasons.append("best path has too few matched rows")
    if best is not None and best.mean_pair_score < policy.minimum_mean_pair_score:
        accepted = False
        reasons.append("best path mean pair score is below the acceptance gate")
    if best is not None and best.schema_coverage < minimum_coverage:
        accepted = False
        reasons.append("best path schema-cluster coverage is below the acceptance gate")
    if runner_up is None or margin is None or margin < policy.minimum_path_margin:
        accepted = False
        reasons.append("best path has no decisive margin over a distinct runner-up")
    if best is not None and policy.require_zero_structural_issues and best.structural_issues:
        accepted = False
        reasons.append("best path retains structural inconsistencies")
    if best is not None and any(
        match.features.indentation_distance is not None
        and match.features.indentation_distance > policy.maximum_indentation_distance
        for match in best.matches
    ):
        accepted = False
        reasons.append("best path exceeds the indentation-distance gate")
    all_out_of_scope = all(not allowed for allowed in allowed_by_row.values())
    status = (
        MappingDecisionStatus.OUT_OF_SCOPE_FOR_TARGET_TEMPLATE
        if all_out_of_scope
        else MappingDecisionStatus.RESOLVED
        if accepted
        else MappingDecisionStatus.AMBIGUOUS_MAPPING
    )
    if accepted:
        reasons.append("ordered cluster is structurally consistent with a decisive path margin")
    elif all_out_of_scope:
        reasons.append("all visible rows are outside the requested target template")
    row_dispositions, schema_dispositions = _dispositions(
        status=status,
        best=best,
        rows=ordered_rows,
        nodes=nodes,
        allowed_by_row=allowed_by_row,
        context=context,
    )
    return OrderedSubgraphResult(
        status=status,
        automatic_selection_allowed=accepted,
        best_path=best,
        runner_up_path=runner_up,
        score_margin=margin,
        ranked_paths=paths,
        row_dispositions=row_dispositions,
        schema_dispositions=schema_dispositions,
        reason="; ".join(reasons),
        graph_sha256=graph.graph_sha256,
        search=SearchStats(
            algorithm=policy.mode,
            pdf_rows=row_count,
            schema_nodes=schema_count,
            dp_cells=(row_count + 1) * (schema_count + 1),
            beam_width_per_cell=policy.beam_width,
            generated_states=generated_states,
            retained_states=retained_states,
        ),
    )
