from __future__ import annotations

from dataclasses import dataclass, field

from rapidfuzz.fuzz import ratio

from bctc_ai.core.text import retrieval_key


@dataclass(frozen=True)
class TableFragment:
    table_id: str
    page: int
    header_labels: tuple[str, ...]
    column_centers: tuple[float, ...]
    unit: str | None
    period_labels: tuple[str, ...]
    notes_section: str | None
    parent_section: str | None
    starts_with_repeated_header: bool = False
    previous_row_incomplete: bool = False
    first_row_continuation_hint: bool = False


@dataclass(frozen=True)
class ContinuationEvidence:
    page_adjacent: bool
    header_similarity: float
    column_axis_similarity: float
    unit_match: bool | None
    period_similarity: float
    notes_section_match: bool | None
    parent_section_match: bool | None
    row_continuation: bool

    @property
    def independent_signal_count(self) -> int:
        return sum(
            (
                self.header_similarity >= 0.75,
                self.column_axis_similarity >= 0.80,
                self.unit_match is True,
                self.period_similarity >= 0.75,
                self.notes_section_match is True,
                self.parent_section_match is True,
                self.row_continuation,
            )
        )

    @property
    def score(self) -> float:
        return (
            0.10 * float(self.page_adjacent)
            + 0.22 * self.header_similarity
            + 0.22 * self.column_axis_similarity
            + 0.10 * float(self.unit_match is True)
            + 0.12 * self.period_similarity
            + 0.09 * float(self.notes_section_match is True)
            + 0.07 * float(self.parent_section_match is True)
            + 0.08 * float(self.row_continuation)
        )


@dataclass(frozen=True)
class ContinuationEdge:
    previous_table_id: str
    next_table_id: str
    accepted: bool
    evidence: ContinuationEvidence
    reason: str


@dataclass
class ContinuationGraph:
    fragments: dict[str, TableFragment] = field(default_factory=dict)
    edges: list[ContinuationEdge] = field(default_factory=list)

    def accepted_successor(self, table_id: str) -> str | None:
        accepted = [
            edge.next_table_id
            for edge in self.edges
            if edge.previous_table_id == table_id and edge.accepted
        ]
        if len(accepted) > 1:
            raise ValueError(f"ambiguous continuation successors for {table_id}: {accepted}")
        return accepted[0] if accepted else None


def _sequence_similarity(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    if not left or not right:
        return 0.0
    left_key = " | ".join(retrieval_key(item) for item in left)
    right_key = " | ".join(retrieval_key(item) for item in right)
    return ratio(left_key, right_key) / 100.0


def _axis_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    left_min, left_max = min(left), max(left)
    right_min, right_max = min(right), max(right)
    left_span = max(left_max - left_min, 1e-6)
    right_span = max(right_max - right_min, 1e-6)
    normalized_left = [(value - left_min) / left_span for value in left]
    normalized_right = [(value - right_min) / right_span for value in right]
    mean_distance = sum(
        abs(left_value - right_value)
        for left_value, right_value in zip(normalized_left, normalized_right, strict=True)
    ) / len(left)
    return max(0.0, 1.0 - mean_distance)


def continuation_evidence(
    previous: TableFragment, following: TableFragment
) -> ContinuationEvidence:
    return ContinuationEvidence(
        page_adjacent=following.page == previous.page + 1,
        header_similarity=_sequence_similarity(previous.header_labels, following.header_labels),
        column_axis_similarity=_axis_similarity(previous.column_centers, following.column_centers),
        unit_match=(previous.unit == following.unit) if previous.unit and following.unit else None,
        period_similarity=_sequence_similarity(previous.period_labels, following.period_labels),
        notes_section_match=(previous.notes_section == following.notes_section)
        if previous.notes_section and following.notes_section
        else None,
        parent_section_match=(previous.parent_section == following.parent_section)
        if previous.parent_section and following.parent_section
        else None,
        row_continuation=previous.previous_row_incomplete and following.first_row_continuation_hint,
    )


def build_continuation_graph(
    fragments: list[TableFragment], *, minimum_score: float = 0.66
) -> ContinuationGraph:
    ordered = sorted(fragments, key=lambda item: (item.page, item.table_id))
    graph = ContinuationGraph({fragment.table_id: fragment for fragment in ordered})
    for previous, following in zip(ordered, ordered[1:], strict=False):
        evidence = continuation_evidence(previous, following)
        accepted = (
            evidence.page_adjacent
            and evidence.independent_signal_count >= 2
            and evidence.score >= minimum_score
        )
        graph.edges.append(
            ContinuationEdge(
                previous_table_id=previous.table_id,
                next_table_id=following.table_id,
                accepted=accepted,
                evidence=evidence,
                reason=(
                    "adjacency plus multiple independent continuation signals"
                    if accepted
                    else "insufficient evidence; adjacency alone cannot merge tables"
                ),
            )
        )
    return graph
