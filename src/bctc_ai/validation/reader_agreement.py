from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz.fuzz import ratio

from bctc_ai.core.text import ParsedNumber, normalize_text, retrieval_key


@dataclass(frozen=True)
class ReaderRow:
    source_row_ids: tuple[str, ...]
    label: str
    note_reference: str | None
    cells: tuple[ParsedNumber, ...]


@dataclass(frozen=True)
class AlignmentStep:
    action: str
    reference_indices: tuple[int, ...]
    candidate_indices: tuple[int, ...]
    reference: ReaderRow | None
    candidate: ReaderRow | None
    semantic_similarity: float | None
    label_exact: bool | None
    semantic_key_exact: bool | None


def combine_reader_rows(rows: tuple[ReaderRow, ...]) -> ReaderRow:
    if not rows:
        raise ValueError("cannot combine an empty row sequence")
    labels = [normalize_text(row.label) for row in rows if normalize_text(row.label)]
    notes = {
        normalize_text(row.note_reference)
        for row in rows
        if row.note_reference and normalize_text(row.note_reference)
    }
    width = max((len(row.cells) for row in rows), default=0)
    combined_cells: list[ParsedNumber] = []
    for index in range(width):
        observed = [
            row.cells[index]
            for row in rows
            if index < len(row.cells) and row.cells[index].observation.value != "BLANK"
        ]
        if not observed:
            observed = [row.cells[index] for row in rows if index < len(row.cells)]
        if not observed:
            continue
        first = observed[0]
        if any(
            cell.value != first.value or cell.observation is not first.observation
            for cell in observed[1:]
        ):
            raise ValueError("cannot combine rows with conflicting cells on the same axis")
        combined_cells.append(first)
    return ReaderRow(
        source_row_ids=tuple(source_id for row in rows for source_id in row.source_row_ids),
        label=normalize_text(" ".join(labels)),
        note_reference=next(iter(notes)) if len(notes) == 1 else None,
        cells=tuple(combined_cells),
    )


def _label_similarity(reference: ReaderRow, candidate: ReaderRow) -> float:
    left = retrieval_key(reference.label)
    right = retrieval_key(candidate.label)
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return ratio(left, right) / 100.0


def _label_cost(reference: ReaderRow, candidate: ReaderRow) -> float:
    similarity = _label_similarity(reference, candidate)
    cost = 1.0 - similarity
    if similarity < 0.45:
        cost += 0.6
    return cost


def _has_row_evidence(row: ReaderRow) -> bool:
    return bool(row.note_reference) or any(
        cell.observation.value != "BLANK" for cell in row.cells
    )


def _may_merge_candidate_pair(rows: tuple[ReaderRow, ReaderRow]) -> bool:
    return bool(rows[0].label and rows[1].label) and (
        _has_row_evidence(rows[0]) != _has_row_evidence(rows[1])
    )


def _step(
    action: str,
    reference_indices: tuple[int, ...],
    candidate_indices: tuple[int, ...],
    reference: ReaderRow | None,
    candidate: ReaderRow | None,
) -> AlignmentStep:
    if reference is None or candidate is None:
        return AlignmentStep(
            action,
            reference_indices,
            candidate_indices,
            reference,
            candidate,
            None,
            None,
            None,
        )
    return AlignmentStep(
        action,
        reference_indices,
        candidate_indices,
        reference,
        candidate,
        round(_label_similarity(reference, candidate), 6),
        normalize_text(reference.label).casefold() == normalize_text(candidate.label).casefold(),
        retrieval_key(reference.label) == retrieval_key(candidate.label),
    )


def align_ordered_reader_rows(
    reference_rows: tuple[ReaderRow, ...],
    candidate_rows: tuple[ReaderRow, ...],
    *,
    gap_penalty: float = 0.65,
    candidate_merge_penalty: float = 0.05,
) -> tuple[AlignmentStep, ...]:
    """Align two independent readers using row order and labels only.

    Candidate pairs may propose one logical wrapped row. Values and notes are
    deliberately excluded from the path score; they remain independent evidence
    measured after alignment.
    """

    if gap_penalty <= 0 or candidate_merge_penalty < 0:
        raise ValueError("alignment penalties must be non-negative and gap must be positive")
    reference_count = len(reference_rows)
    candidate_count = len(candidate_rows)
    costs = [[float("inf")] * (candidate_count + 1) for _ in range(reference_count + 1)]
    previous: list[list[tuple[int, int, str] | None]] = [
        [None] * (candidate_count + 1) for _ in range(reference_count + 1)
    ]
    costs[0][0] = 0.0
    priorities = {"MATCH": 0, "MERGE_CANDIDATE": 1, "MISSING_CANDIDATE": 2, "EXTRA_CANDIDATE": 3}

    def update(i: int, j: int, cost: float, state: tuple[int, int, str]) -> None:
        current = costs[i][j]
        current_state = previous[i][j]
        if cost < current - 1e-12 or (
            abs(cost - current) <= 1e-12
            and current_state is not None
            and priorities[state[2]] < priorities[current_state[2]]
        ):
            costs[i][j] = cost
            previous[i][j] = state

    for i in range(reference_count + 1):
        for j in range(candidate_count + 1):
            base = costs[i][j]
            if base == float("inf"):
                continue
            if i < reference_count and j < candidate_count:
                update(
                    i + 1,
                    j + 1,
                    base + _label_cost(reference_rows[i], candidate_rows[j]),
                    (i, j, "MATCH"),
                )
            if i < reference_count and j + 1 < candidate_count:
                pair = candidate_rows[j : j + 2]
                try:
                    combined = combine_reader_rows(pair) if _may_merge_candidate_pair(pair) else None
                except ValueError:
                    combined = None
                if combined is not None:
                    update(
                        i + 1,
                        j + 2,
                        base
                        + _label_cost(reference_rows[i], combined)
                        + candidate_merge_penalty,
                        (i, j, "MERGE_CANDIDATE"),
                    )
            if i < reference_count:
                update(i + 1, j, base + gap_penalty, (i, j, "MISSING_CANDIDATE"))
            if j < candidate_count:
                update(i, j + 1, base + gap_penalty, (i, j, "EXTRA_CANDIDATE"))

    i = reference_count
    j = candidate_count
    aligned: list[AlignmentStep] = []
    while i or j:
        state = previous[i][j]
        if state is None:
            raise RuntimeError(f"ordered alignment has no predecessor at {(i, j)}")
        previous_i, previous_j, action = state
        if action == "MATCH":
            reference = reference_rows[previous_i]
            candidate = candidate_rows[previous_j]
            aligned.append(
                _step(action, (previous_i,), (previous_j,), reference, candidate)
            )
        elif action == "MERGE_CANDIDATE":
            reference = reference_rows[previous_i]
            candidate = combine_reader_rows(candidate_rows[previous_j:j])
            aligned.append(
                _step(
                    action,
                    (previous_i,),
                    tuple(range(previous_j, j)),
                    reference,
                    candidate,
                )
            )
        elif action == "MISSING_CANDIDATE":
            aligned.append(
                _step(action, (previous_i,), (), reference_rows[previous_i], None)
            )
        elif action == "EXTRA_CANDIDATE":
            aligned.append(
                _step(action, (), (previous_j,), None, candidate_rows[previous_j])
            )
        else:
            raise AssertionError(f"unknown alignment action: {action}")
        i, j = previous_i, previous_j
    return tuple(reversed(aligned))
