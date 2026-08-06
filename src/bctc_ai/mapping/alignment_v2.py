from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from rapidfuzz.fuzz import ratio

from bctc_ai.core.text import normalize_text, retrieval_key
from bctc_ai.mapping.scope import ScopePolicy, classify_mapping_scopes
from bctc_ai.schema.registry import SchemaItem

_EXPECTED_PRIORITY = (
    "exact_table_and_statement_context",
    "parent_child_relationship",
    "previous_and_next_rows",
    "indentation_and_numbering",
    "exact_or_normalized_label",
    "same_bank_historical_reference",
    "cross_bank_historical_reference",
)


class MappingDecisionStatus(StrEnum):
    RESOLVED = "RESOLVED"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"
    OUT_OF_SCOPE_FOR_TARGET_TEMPLATE = "OUT_OF_SCOPE_FOR_TARGET_TEMPLATE"


@dataclass(frozen=True)
class StructuralRankingPolicy:
    version: int
    mode: str
    priority: tuple[str, ...]
    minimum_label_similarity: float
    minimum_label_gap_when_label_decides: float
    maximum_history_score: float
    scope_policy_path: str
    source_path: Path


@dataclass(frozen=True)
class ObservedRowV2:
    row_id: str
    label: str
    order: int
    statement_type: str
    scope: str
    section_heading: str | None = None
    section_schema_id: int | None = None
    parent_schema_id: int | None = None
    parent_label: str | None = None
    previous_schema_id: int | None = None
    previous_label: str | None = None
    next_schema_id: int | None = None
    next_label: str | None = None
    indentation_level: int | None = None
    numbering: str | None = None
    target_template_in_scope: bool = True


@dataclass(frozen=True)
class StructuralFeatures:
    table_statement_context: int
    parent_child: int
    previous_next: int
    indentation_numbering: int
    exact_label: int
    normalized_label_similarity: float
    same_bank_history: float
    cross_bank_history: float
    verified_structure_conflict: bool
    evidence: tuple[str, ...]

    @property
    def priority_key(self) -> tuple[int, int, int, int, int, float, float, float]:
        return (
            self.table_statement_context,
            self.parent_child,
            self.previous_next,
            self.indentation_numbering,
            self.exact_label,
            round(self.normalized_label_similarity, 6),
            round(self.same_bank_history, 6),
            round(self.cross_bank_history, 6),
        )


@dataclass(frozen=True)
class StructuralCandidate:
    row_id: str
    schema_id: int
    canonical_name: str
    features: StructuralFeatures


@dataclass(frozen=True)
class StructuralRankingResult:
    row_id: str
    status: MappingDecisionStatus
    recommended_schema_id: int | None
    automatic_selection_allowed: bool
    candidates: tuple[StructuralCandidate, ...]
    reason: str


@dataclass(frozen=True)
class MappingSequenceValidation:
    valid: bool
    schema_id_sequence: tuple[int, ...]
    display_order_sequence: tuple[int, ...]
    violations: tuple[str, ...]


def load_structural_ranking_policy(path: Path) -> StructuralRankingPolicy:
    payload: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    history = payload.get("history_policy")
    priority = payload.get("priority")
    if (
        payload.get("version") != 2
        or payload.get("mode") != "LEXICOGRAPHIC_FAIL_CLOSED"
        or tuple(priority or ()) != _EXPECTED_PRIORITY
        or not isinstance(history, dict)
    ):
        raise ValueError(f"invalid structural ranking v2 identity: {path}")
    if (
        history.get("same_bank") != "REVIEW_TIE_BREAK_ONLY"
        or history.get("cross_bank") != "REVIEW_TIE_BREAK_ONLY"
        or history.get("may_override_verified_structure") is not False
        or history.get("may_use_numeric_value_for_mapping") is not False
    ):
        raise ValueError(f"historical evidence policy is unsafe: {path}")
    minimum_similarity = float(payload.get("minimum_label_similarity", -1))
    minimum_gap = float(payload.get("minimum_label_gap_when_label_decides", -1))
    maximum_history = float(payload.get("maximum_history_score", -1))
    if not 0 <= minimum_similarity <= 1 or not 0 <= minimum_gap <= 1:
        raise ValueError(f"invalid label thresholds: {path}")
    if maximum_history != 1.0:
        raise ValueError(f"history scores must remain normalized to [0, 1]: {path}")
    scope_path = payload.get("scope_policy")
    if not isinstance(scope_path, str) or not scope_path:
        raise ValueError(f"structural ranking has no scope policy: {path}")
    return StructuralRankingPolicy(
        version=2,
        mode=str(payload["mode"]),
        priority=tuple(priority),
        minimum_label_similarity=minimum_similarity,
        minimum_label_gap_when_label_decides=minimum_gap,
        maximum_history_score=maximum_history,
        scope_policy_path=scope_path,
        source_path=path.resolve(),
    )


def _similarity(left: str, right: str) -> float:
    return ratio(retrieval_key(left), retrieval_key(right)) / 100.0


def _candidate_labels(item: SchemaItem) -> tuple[str, ...]:
    labels = [item.canonical_name, *item.structural_aliases, *item.historical_aliases]
    return tuple(dict.fromkeys(label for label in labels if label))


def _label_features(label: str, item: SchemaItem) -> tuple[int, float]:
    labels = _candidate_labels(item)
    raw = normalize_text(label).casefold()
    raw_exact = any(raw == normalize_text(candidate).casefold() for candidate in labels)
    key = retrieval_key(label)
    key_exact = any(key == retrieval_key(candidate) for candidate in labels)
    similarity = max((_similarity(label, candidate) for candidate in labels), default=0.0)
    return (2 if raw_exact else 1 if key_exact else 0), similarity


def _ancestor_ids(item: SchemaItem, by_id: Mapping[int, SchemaItem]) -> set[int]:
    result: set[int] = set()
    current = item
    while current.parent_id is not None:
        if current.parent_id in result:
            raise ValueError(f"schema hierarchy cycle containing {current.parent_id}")
        result.add(current.parent_id)
        parent = by_id.get(current.parent_id)
        if parent is None:
            break
        current = parent
    return result


def _context_score(
    row: ObservedRowV2,
    item: SchemaItem,
    by_id: Mapping[int, SchemaItem],
) -> tuple[int, bool, list[str]]:
    evidence = ["statement type matched"]
    conflict = False
    score = 1
    if row.scope and item.scope and row.scope not in item.scope:
        conflict = True
        score = -2
        evidence.append("candidate scope conflicts with verified table scope")
    if row.section_schema_id is not None:
        inside = item.schema_id == row.section_schema_id or row.section_schema_id in _ancestor_ids(
            item, by_id
        )
        if inside:
            score = max(score, 2)
            evidence.append("candidate belongs to verified schema section")
        else:
            score = -2
            conflict = True
            evidence.append("candidate lies outside verified schema section")
    return score, conflict, evidence


def _parent_score(
    row: ObservedRowV2,
    item: SchemaItem,
    by_id: Mapping[int, SchemaItem],
) -> tuple[int, bool, list[str]]:
    if row.parent_schema_id is not None:
        if item.parent_id == row.parent_schema_id:
            return 3, False, ["candidate matches verified parent schema ID"]
        return -3, True, ["candidate conflicts with verified parent schema ID"]
    if row.parent_label:
        parent = by_id.get(item.parent_id) if item.parent_id is not None else None
        if parent is None:
            return -1, False, ["candidate has no parent for observed parent label"]
        similarity = max(
            (_similarity(row.parent_label, label) for label in _candidate_labels(parent)),
            default=0.0,
        )
        if similarity >= 0.90:
            return 2, False, ["candidate parent strongly matches observed parent label"]
        if similarity >= 0.65:
            return 1, False, ["candidate parent partially matches observed parent label"]
        return -1, False, ["candidate parent label does not match observed parent"]
    return 0, False, ["parent evidence unavailable"]


def _neighbor_side_score(
    observed_id: int | None,
    observed_label: str | None,
    item: SchemaItem,
    *,
    side: str,
    by_id: Mapping[int, SchemaItem],
) -> tuple[int, bool]:
    if observed_id is not None:
        candidate_id = item.previous_id if side == "previous" else item.next_id
        if observed_id == candidate_id:
            return 3, False
        anchor = by_id.get(observed_id)
        if anchor is None:
            return -3, True
        order_compatible = (
            anchor.display_order < item.display_order
            if side == "previous"
            else item.display_order < anchor.display_order
        )
        # A visible neighbor can skip a schema row that is absent from the PDF.
        # Direction in workbook order therefore remains useful even when the
        # IDs are not immediate template neighbors.
        return (1, False) if order_compatible else (-3, True)
    if observed_label:
        candidate_id = item.previous_id if side == "previous" else item.next_id
        candidate = by_id.get(candidate_id) if candidate_id is not None else None
        similarity = _similarity(observed_label, candidate.canonical_name) if candidate else 0.0
        if similarity >= 0.90:
            return 1, False
        if similarity < 0.45:
            return -1, False
    return 0, False


def _neighbor_score(
    row: ObservedRowV2,
    item: SchemaItem,
    by_id: Mapping[int, SchemaItem],
) -> tuple[int, bool, list[str]]:
    previous, previous_conflict = _neighbor_side_score(
        row.previous_schema_id,
        row.previous_label,
        item,
        side="previous",
        by_id=by_id,
    )
    following, following_conflict = _neighbor_side_score(
        row.next_schema_id,
        row.next_label,
        item,
        side="next",
        by_id=by_id,
    )
    known_sides = sum(
        value is not None
        for value in (
            row.previous_schema_id or row.previous_label,
            row.next_schema_id or row.next_label,
        )
    )
    if known_sides == 0:
        return 0, False, ["neighbor evidence unavailable"]
    return (
        previous + following,
        previous_conflict or following_conflict,
        [f"previous/next structural score={previous + following}"],
    )


def _indent_number_score(
    row: ObservedRowV2,
    item: SchemaItem,
    schema_numbering: Mapping[int, str],
) -> tuple[int, list[str]]:
    score = 0
    evidence = []
    if row.indentation_level is not None and item.hierarchy_level is not None:
        distance = abs(row.indentation_level - item.hierarchy_level)
        score += 2 if distance == 0 else 0 if distance == 1 else -1
        evidence.append(f"hierarchy indentation distance={distance}")
    if row.numbering:
        candidate_numbering = schema_numbering.get(item.schema_id)
        if candidate_numbering:
            score += 1 if retrieval_key(row.numbering) == retrieval_key(candidate_numbering) else -1
            evidence.append("numbering compared with schema-side structural metadata")
    return score, evidence or ["indentation/numbering evidence unavailable"]


def _history_score(value: float | None, maximum: float) -> float:
    if value is None:
        return 0.0
    numeric = float(value)
    if not 0 <= numeric <= maximum:
        raise ValueError("historical candidate scores must be normalized to [0, 1]")
    return numeric


def _features(
    row: ObservedRowV2,
    item: SchemaItem,
    by_id: Mapping[int, SchemaItem],
    *,
    schema_numbering: Mapping[int, str],
    same_bank_history: Mapping[int, float],
    cross_bank_history: Mapping[int, float],
    policy: StructuralRankingPolicy,
) -> StructuralFeatures:
    context, context_conflict, context_evidence = _context_score(row, item, by_id)
    parent, parent_conflict, parent_evidence = _parent_score(row, item, by_id)
    neighbors, neighbor_conflict, neighbor_evidence = _neighbor_score(row, item, by_id)
    indent, indent_evidence = _indent_number_score(row, item, schema_numbering)
    exact, similarity = _label_features(row.label, item)
    evidence = (
        *context_evidence,
        *parent_evidence,
        *neighbor_evidence,
        *indent_evidence,
        f"label similarity={similarity:.6f}",
        "historical features are final review-only tie-breakers",
        "numeric values are not mapping features",
    )
    return StructuralFeatures(
        table_statement_context=context,
        parent_child=parent,
        previous_next=neighbors,
        indentation_numbering=indent,
        exact_label=exact,
        normalized_label_similarity=similarity,
        same_bank_history=_history_score(
            same_bank_history.get(item.schema_id), policy.maximum_history_score
        ),
        cross_bank_history=_history_score(
            cross_bank_history.get(item.schema_id), policy.maximum_history_score
        ),
        verified_structure_conflict=context_conflict or parent_conflict or neighbor_conflict,
        evidence=tuple(evidence),
    )


def _first_difference(left: tuple[object, ...], right: tuple[object, ...]) -> int | None:
    return next(
        (index for index, pair in enumerate(zip(left, right, strict=True)) if pair[0] != pair[1]),
        None,
    )


def rank_structural_candidates(
    row: ObservedRowV2,
    schema: list[SchemaItem],
    *,
    policy: StructuralRankingPolicy,
    scope_policy: ScopePolicy | None,
    schema_numbering: Mapping[int, str] | None = None,
    same_bank_history: Mapping[int, float] | None = None,
    cross_bank_history: Mapping[int, float] | None = None,
    limit: int = 20,
) -> StructuralRankingResult:
    """Rank one visible row without allowing names/history to override structure."""

    if limit < 1:
        raise ValueError("candidate limit must be positive")
    scope = classify_mapping_scopes(
        [(row.statement_type, row.label)],
        scope_policy,
        initial_section_label=row.section_heading,
    )[0]
    if not row.target_template_in_scope or not scope.allowed:
        return StructuralRankingResult(
            row_id=row.row_id,
            status=MappingDecisionStatus.OUT_OF_SCOPE_FOR_TARGET_TEMPLATE,
            recommended_schema_id=None,
            automatic_selection_allowed=False,
            candidates=(),
            reason="visible row is excluded from the requested target template",
        )

    by_id = {item.schema_id: item for item in schema}
    numbering = schema_numbering or {}
    same_history = same_bank_history or {}
    cross_history = cross_bank_history or {}
    candidates = [
        StructuralCandidate(
            row_id=row.row_id,
            schema_id=item.schema_id,
            canonical_name=item.canonical_name,
            features=_features(
                row,
                item,
                by_id,
                schema_numbering=numbering,
                same_bank_history=same_history,
                cross_bank_history=cross_history,
                policy=policy,
            ),
        )
        for item in sorted(
            (candidate for candidate in schema if candidate.statement_type == row.statement_type),
            key=lambda candidate: candidate.display_order,
        )
    ]
    candidates.sort(key=lambda candidate: candidate.features.priority_key, reverse=True)
    if not candidates:
        return StructuralRankingResult(
            row.row_id,
            MappingDecisionStatus.AMBIGUOUS_MAPPING,
            None,
            False,
            (),
            "no schema candidate exists in the verified statement",
        )
    top = candidates[0]
    visible_candidates = tuple(candidates[:limit])
    if top.features.verified_structure_conflict:
        return StructuralRankingResult(
            row.row_id,
            MappingDecisionStatus.AMBIGUOUS_MAPPING,
            top.schema_id,
            False,
            visible_candidates,
            "best label/history candidate still conflicts with verified structure",
        )
    if len(candidates) == 1:
        decisive_index = 0
        second = None
    else:
        second = candidates[1]
        decisive_index = _first_difference(
            top.features.priority_key,
            second.features.priority_key,
        )
    if decisive_index is None:
        return StructuralRankingResult(
            row.row_id,
            MappingDecisionStatus.AMBIGUOUS_MAPPING,
            None,
            False,
            visible_candidates,
            "top candidates are indistinguishable on all permitted evidence",
        )
    # Indices 6 and 7 are same-bank and cross-bank evidence. They can order the
    # review list but cannot resolve the mapping automatically.
    if decisive_index >= 6:
        return StructuralRankingResult(
            row.row_id,
            MappingDecisionStatus.AMBIGUOUS_MAPPING,
            top.schema_id,
            False,
            visible_candidates,
            "historical evidence is the first discriminator and is review-only",
        )
    if top.features.normalized_label_similarity < policy.minimum_label_similarity:
        return StructuralRankingResult(
            row.row_id,
            MappingDecisionStatus.AMBIGUOUS_MAPPING,
            top.schema_id,
            False,
            visible_candidates,
            "top candidate label evidence is below the fail-closed minimum",
        )
    if decisive_index in {4, 5} and second is not None:
        label_gap = (
            top.features.normalized_label_similarity - second.features.normalized_label_similarity
        )
        if (
            top.features.exact_label == second.features.exact_label
            and label_gap < policy.minimum_label_gap_when_label_decides
        ):
            return StructuralRankingResult(
                row.row_id,
                MappingDecisionStatus.AMBIGUOUS_MAPPING,
                top.schema_id,
                False,
                visible_candidates,
                "label-only candidate gap is insufficient",
            )
    return StructuralRankingResult(
        row.row_id,
        MappingDecisionStatus.RESOLVED,
        top.schema_id,
        True,
        visible_candidates,
        "resolved lexicographically before any historical tie-breaker",
    )


def validate_mapping_sequence(
    rows: list[ObservedRowV2],
    selected_schema_ids: Mapping[str, int],
    schema: list[SchemaItem],
) -> MappingSequenceValidation:
    """Gate a mapped row sequence using template order, never numeric ID order."""

    by_id = {item.schema_id: item for item in schema}
    violations: list[str] = []
    row_ids = [row.row_id for row in rows]
    if len(row_ids) != len(set(row_ids)):
        violations.append("observed row IDs are not unique")
    row_orders = [row.order for row in rows]
    if len(row_orders) != len(set(row_orders)):
        violations.append("observed physical row orders are not unique")
    unknown_rows = sorted(set(selected_schema_ids) - set(row_ids))
    if unknown_rows:
        violations.append(f"mappings reference unknown observed rows: {unknown_rows}")

    ordered_rows = sorted(rows, key=lambda row: row.order)
    selected_items: list[SchemaItem] = []
    selected_ids: list[int] = []
    for row in ordered_rows:
        schema_id = selected_schema_ids.get(row.row_id)
        if schema_id is None:
            continue
        item = by_id.get(schema_id)
        if item is None:
            violations.append(f"row {row.row_id} maps to unknown schema ID {schema_id}")
            continue
        if item.statement_type != row.statement_type:
            violations.append(
                f"row {row.row_id} statement {row.statement_type} conflicts with schema {schema_id}"
            )
        selected_items.append(item)
        selected_ids.append(schema_id)

    if len(selected_ids) != len(set(selected_ids)):
        violations.append("one schema ID is assigned to more than one visible row")
    display_orders = [item.display_order for item in selected_items]
    if any(left >= right for left, right in zip(display_orders, display_orders[1:], strict=False)):
        violations.append(
            "mapped sequence violates source-workbook display_order; numeric ID order is irrelevant"
        )
    return MappingSequenceValidation(
        valid=not violations,
        schema_id_sequence=tuple(selected_ids),
        display_order_sequence=tuple(display_orders),
        violations=tuple(violations),
    )
