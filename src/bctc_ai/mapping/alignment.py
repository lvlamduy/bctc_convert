from __future__ import annotations

from dataclasses import dataclass, field

from rapidfuzz.fuzz import ratio

from bctc_ai.core.text import normalize_text, retrieval_key
from bctc_ai.mapping.scope import ScopePolicy, classify_mapping_scope
from bctc_ai.schema.registry import SchemaItem


@dataclass(frozen=True)
class ObservedRow:
    row_id: str
    label: str
    order: int
    statement_type: str
    parent_label: str | None = None
    section: str | None = None
    y_center: float | None = None
    note_reference: str | None = None


@dataclass(frozen=True)
class MatchFeatures:
    exact_label: float
    normalized_label: float
    accent_insensitive: float
    previous_context: float
    next_context: float
    parent_context: float
    relative_position: float
    statement_compatible: float
    scope_allowed: float

    @property
    def total(self) -> float:
        # Names retrieve candidates; ordered context and hierarchy disambiguate
        # duplicate names. No value feature is present by design.
        return (
            0.22 * self.exact_label
            + 0.18 * self.normalized_label
            + 0.12 * self.accent_insensitive
            + 0.13 * self.previous_context
            + 0.13 * self.next_context
            + 0.10 * self.parent_context
            + 0.07 * self.relative_position
            + 0.03 * self.statement_compatible
            + 0.02 * self.scope_allowed
        )


@dataclass(frozen=True)
class Candidate:
    row_id: str
    schema_id: int
    features: MatchFeatures
    score: float


@dataclass(frozen=True)
class AlignedMatch:
    row_id: str
    schema_id: int
    score: float
    candidate_gap: float
    features: MatchFeatures
    acceptance: str
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AlignmentResult:
    matches: list[AlignedMatch]
    unmatched_row_ids: list[str]
    unused_schema_ids: list[int]
    total_score: float


def _similarity(left: str, right: str) -> float:
    return ratio(left, right) / 100.0


def _candidate_features(
    rows: list[ObservedRow],
    row_index: int,
    schema: list[SchemaItem],
    schema_index: int,
    scope_policy: ScopePolicy,
) -> MatchFeatures:
    row = rows[row_index]
    item = schema[schema_index]
    raw_left = normalize_text(row.label).casefold()
    raw_right = normalize_text(item.canonical_name).casefold()
    key_left = retrieval_key(row.label)
    key_right = retrieval_key(item.canonical_name)
    previous_context = 0.0
    if row_index > 0 and schema_index > 0:
        previous_context = _similarity(
            retrieval_key(rows[row_index - 1].label),
            retrieval_key(schema[schema_index - 1].canonical_name),
        )
    next_context = 0.0
    if row_index + 1 < len(rows) and schema_index + 1 < len(schema):
        next_context = _similarity(
            retrieval_key(rows[row_index + 1].label),
            retrieval_key(schema[schema_index + 1].canonical_name),
        )
    parent_context = 0.0
    if row.parent_label and item.parent_id is not None:
        parent = next(
            (candidate for candidate in schema if candidate.schema_id == item.parent_id), None
        )
        if parent:
            parent_context = _similarity(retrieval_key(row.parent_label), parent.normalized_name)
    row_position = row_index / max(1, len(rows) - 1)
    schema_position = schema_index / max(1, len(schema) - 1)
    scope = classify_mapping_scope(row.statement_type, row.label, scope_policy)
    return MatchFeatures(
        exact_label=float(raw_left == raw_right),
        normalized_label=_similarity(raw_left, raw_right),
        accent_insensitive=_similarity(key_left, key_right),
        previous_context=previous_context,
        next_context=next_context,
        parent_context=parent_context,
        relative_position=max(0.0, 1.0 - abs(row_position - schema_position)),
        statement_compatible=float(row.statement_type == item.statement_type),
        scope_allowed=float(scope.allowed),
    )


def generate_candidates(
    rows: list[ObservedRow],
    schema: list[SchemaItem],
    *,
    scope_policy: ScopePolicy | None,
    limit: int = 20,
) -> dict[str, list[Candidate]]:
    result: dict[str, list[Candidate]] = {}
    for row_index, row in enumerate(rows):
        scope = classify_mapping_scope(row.statement_type, row.label, scope_policy)
        if not scope.allowed:
            result[row.row_id] = []
            continue
        candidates = []
        for schema_index, item in enumerate(schema):
            if item.statement_type != row.statement_type:
                continue
            if scope_policy is None:
                continue
            features = _candidate_features(
                rows,
                row_index,
                schema,
                schema_index,
                scope_policy,
            )
            candidate = Candidate(row.row_id, item.schema_id, features, features.total)
            candidates.append(candidate)
        candidates.sort(key=lambda candidate: (-candidate.score, candidate.schema_id))
        result[row.row_id] = candidates[:limit]
    return result


def align_ordered_rows(
    rows: list[ObservedRow],
    schema: list[SchemaItem],
    *,
    scope_policy: ScopePolicy | None,
    minimum_match_score: float = 0.35,
    row_gap_penalty: float = -0.18,
    schema_gap_penalty: float = -0.035,
    review_score: float = 0.62,
    medium_score: float = 0.76,
    minimum_gap: float = 0.08,
) -> AlignmentResult:
    if not rows or not schema:
        return AlignmentResult(
            [], [row.row_id for row in rows], [item.schema_id for item in schema], 0.0
        )
    candidates = generate_candidates(
        rows,
        schema,
        scope_policy=scope_policy,
        limit=len(schema),
    )
    by_pair = {
        (candidate.row_id, candidate.schema_id): candidate
        for row_candidates in candidates.values()
        for candidate in row_candidates
    }
    row_count, schema_count = len(rows), len(schema)
    scores = [[float("-inf")] * (schema_count + 1) for _ in range(row_count + 1)]
    trace: list[list[str | None]] = [[None] * (schema_count + 1) for _ in range(row_count + 1)]
    scores[0][0] = 0.0
    for row_index in range(1, row_count + 1):
        scores[row_index][0] = scores[row_index - 1][0] + row_gap_penalty
        trace[row_index][0] = "SKIP_ROW"
    for schema_index in range(1, schema_count + 1):
        scores[0][schema_index] = scores[0][schema_index - 1] + schema_gap_penalty
        trace[0][schema_index] = "SKIP_SCHEMA"

    for row_index in range(1, row_count + 1):
        for schema_index in range(1, schema_count + 1):
            candidate = by_pair.get(
                (rows[row_index - 1].row_id, schema[schema_index - 1].schema_id)
            )
            match_value = float("-inf")
            if candidate and candidate.score >= minimum_match_score:
                match_value = scores[row_index - 1][schema_index - 1] + candidate.score
            choices = {
                "MATCH": match_value,
                "SKIP_ROW": scores[row_index - 1][schema_index] + row_gap_penalty,
                "SKIP_SCHEMA": scores[row_index][schema_index - 1] + schema_gap_penalty,
            }
            operation, value = max(choices.items(), key=lambda item: item[1])
            scores[row_index][schema_index] = value
            trace[row_index][schema_index] = operation

    selected: list[Candidate] = []
    unmatched: list[str] = []
    row_index, schema_index = row_count, schema_count
    while row_index or schema_index:
        operation = trace[row_index][schema_index]
        if operation == "MATCH":
            selected.append(
                by_pair[(rows[row_index - 1].row_id, schema[schema_index - 1].schema_id)]
            )
            row_index -= 1
            schema_index -= 1
        elif operation == "SKIP_ROW":
            unmatched.append(rows[row_index - 1].row_id)
            row_index -= 1
        elif operation == "SKIP_SCHEMA":
            schema_index -= 1
        else:
            raise RuntimeError("alignment trace is incomplete")
    selected.reverse()
    unmatched.reverse()

    matches = []
    for candidate in selected:
        alternatives = candidates[candidate.row_id]
        second_score = next(
            (item.score for item in alternatives if item.schema_id != candidate.schema_id), 0.0
        )
        gap = candidate.score - second_score
        if candidate.score >= medium_score and gap >= minimum_gap:
            acceptance = "AUTO_VERIFIED_MEDIUM"
        elif candidate.score >= review_score:
            acceptance = "REVIEW_REQUIRED"
        else:
            acceptance = "UNRESOLVED"
        matches.append(
            AlignedMatch(
                row_id=candidate.row_id,
                schema_id=candidate.schema_id,
                score=round(candidate.score, 6),
                candidate_gap=round(gap, 6),
                features=candidate.features,
                acceptance=acceptance,
                reasons=[
                    "ordered dynamic-programming alignment",
                    "value similarity not used",
                    "high confidence intentionally unavailable before cell evidence gates",
                ],
            )
        )
    used = {match.schema_id for match in matches}
    return AlignmentResult(
        matches=matches,
        unmatched_row_ids=unmatched,
        unused_schema_ids=[item.schema_id for item in schema if item.schema_id not in used],
        total_score=round(scores[row_count][schema_count], 6),
    )
