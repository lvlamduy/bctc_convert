from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from rapidfuzz.fuzz import ratio

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.text import normalize_text, retrieval_key
from bctc_ai.evaluation.reader_outputs import reader_row_to_dict
from bctc_ai.validation.reader_agreement import ReaderRow


class SemanticGeometryFusionError(RuntimeError):
    pass


@dataclass(frozen=True)
class SemanticGeometryFusionConfig:
    minimum_concatenated_label_similarity: float
    minimum_shifted_label_similarity: float
    minimum_local_mean_score_gain: float
    minimum_output_label_similarity: float
    minimum_path_score_margin: float


@dataclass(frozen=True)
class OverflowShiftEvidence:
    geometry_indices: tuple[int, int]
    semantic_indices: tuple[int, int, int]
    ordinary_mean_similarity: float
    overflow_mean_similarity: float
    score_gain: float
    first_numeric_fingerprint_exact: bool
    second_numeric_fingerprint_exact: bool
    third_semantic_row_cells_blank: bool
    semantic_value_cells_unmodified: bool
    geometry_cells_unmodified: bool


@dataclass(frozen=True)
class FusedSemanticGeometryRow:
    row: ReaderRow
    geometry_index: int
    semantic_label_indices: tuple[int, ...]
    semantic_value_indices: tuple[int, ...]
    geometry_source_row_ids: tuple[str, ...]
    semantic_label_source_row_ids: tuple[str, ...]
    semantic_value_source_row_ids: tuple[str, ...]
    label_similarity: float
    semantic_value_fingerprint_exact: bool
    geometry_cells_unmodified: bool
    geometry_note_unmodified: bool
    action: str


@dataclass(frozen=True)
class SemanticGeometryFusionResult:
    status: str
    rows: tuple[FusedSemanticGeometryRow, ...]
    overflow_repairs: tuple[OverflowShiftEvidence, ...]
    unresolved_reasons: tuple[str, ...]
    best_path_mean_score: float | None
    second_path_mean_score: float | None
    path_score_margin: float | None
    geometry_cells_unmodified: bool
    automatic_acceptance: bool
    confidence_effect: str

    @property
    def reader_rows(self) -> tuple[ReaderRow, ...]:
        return tuple(item.row for item in self.rows)


@dataclass(frozen=True)
class _PathStep:
    action: str
    geometry_indices: tuple[int, ...]
    semantic_label_indices: tuple[tuple[int, ...], ...]
    semantic_value_indices: tuple[tuple[int, ...], ...]
    labels: tuple[str, ...]
    similarities: tuple[float, ...]
    overflow_evidence: OverflowShiftEvidence | None = None


@dataclass(frozen=True)
class _Path:
    score: float
    steps: tuple[_PathStep, ...]


def load_semantic_geometry_fusion_config(path: Path) -> SemanticGeometryFusionConfig:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, yaml.YAMLError) as exc:
        raise SemanticGeometryFusionError(f"cannot read fusion config: {path}") from exc
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise SemanticGeometryFusionError("semantic-geometry fusion config must be version 1")
    if payload.get("algorithm") != "FIXED_GEOMETRY_GRID_SEMANTIC_LABEL_FUSION_V1":
        raise SemanticGeometryFusionError("unexpected semantic-geometry fusion algorithm")
    overflow = payload.get("overflow_pattern")
    if not isinstance(overflow, dict) or overflow != {
        "semantic_rows_consumed": 3,
        "geometry_rows_produced": 2,
        "require_first_two_numeric_fingerprints_exact": True,
        "require_third_semantic_row_cells_blank": True,
        "require_all_three_labels_present": True,
    }:
        raise SemanticGeometryFusionError("overflow pattern safety contract drifted")
    safety = payload.get("safety")
    if not isinstance(safety, dict) or not safety or any(bool(value) for value in safety.values()):
        raise SemanticGeometryFusionError("fusion config grants forbidden output authority")
    values = {}
    for name in (
        "minimum_concatenated_label_similarity",
        "minimum_shifted_label_similarity",
        "minimum_local_mean_score_gain",
        "minimum_output_label_similarity",
        "minimum_path_score_margin",
    ):
        value = payload.get(name)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 1:
            raise SemanticGeometryFusionError(f"invalid fusion threshold: {name}")
        values[name] = float(value)
    return SemanticGeometryFusionConfig(**values)


def _label_similarity(left: str, right: str) -> float:
    left_key = retrieval_key(left)
    right_key = retrieval_key(right)
    if not left_key and not right_key:
        return 1.0
    if not left_key or not right_key:
        return 0.0
    return ratio(left_key, right_key) / 100.0


def _all_blank(row: ReaderRow) -> bool:
    return bool(row.cells) and all(cell.observation is ObservationKind.BLANK for cell in row.cells)


def _numeric_fingerprint_exact(
    geometry: ReaderRow,
    semantic: ReaderRow,
    *,
    require_observed: bool,
) -> bool:
    if not geometry.cells or len(geometry.cells) != len(semantic.cells):
        return False
    if require_observed and not any(
        cell.observation is not ObservationKind.BLANK for cell in geometry.cells
    ):
        return False
    if any(
        cell.observation is ObservationKind.INVALID
        for row in (geometry, semantic)
        for cell in row.cells
    ):
        return False
    return all(
        geometry_cell.observation is semantic_cell.observation
        and geometry_cell.value == semantic_cell.value
        for geometry_cell, semantic_cell in zip(
            geometry.cells,
            semantic.cells,
            strict=True,
        )
    )


def _source_ids(rows: tuple[ReaderRow, ...], indices: tuple[int, ...]) -> tuple[str, ...]:
    return tuple(source_id for index in indices for source_id in rows[index].source_row_ids)


def _overflow_step(
    geometry_rows: tuple[ReaderRow, ...],
    semantic_rows: tuple[ReaderRow, ...],
    geometry_index: int,
    semantic_index: int,
    config: SemanticGeometryFusionConfig,
) -> _PathStep | None:
    if geometry_index + 1 >= len(geometry_rows) or semantic_index + 2 >= len(semantic_rows):
        return None
    geometry_first, geometry_second = geometry_rows[geometry_index : geometry_index + 2]
    semantic_first, semantic_continuation, semantic_next = semantic_rows[
        semantic_index : semantic_index + 3
    ]
    if not all(
        normalize_text(row.label) for row in (semantic_first, semantic_continuation, semantic_next)
    ):
        return None
    first_fingerprint = _numeric_fingerprint_exact(
        geometry_first,
        semantic_first,
        require_observed=True,
    )
    second_fingerprint = _numeric_fingerprint_exact(
        geometry_second,
        semantic_continuation,
        require_observed=True,
    )
    third_blank = _all_blank(semantic_next)
    if not (first_fingerprint and second_fingerprint and third_blank):
        return None
    combined_label = normalize_text(f"{semantic_first.label} {semantic_continuation.label}")
    first_similarity = _label_similarity(geometry_first.label, combined_label)
    second_similarity = _label_similarity(geometry_second.label, semantic_next.label)
    ordinary_mean = (
        _label_similarity(geometry_first.label, semantic_first.label)
        + _label_similarity(geometry_second.label, semantic_continuation.label)
    ) / 2
    overflow_mean = (first_similarity + second_similarity) / 2
    gain = overflow_mean - ordinary_mean
    if (
        first_similarity < config.minimum_concatenated_label_similarity
        or second_similarity < config.minimum_shifted_label_similarity
        or gain < config.minimum_local_mean_score_gain
    ):
        return None
    evidence = OverflowShiftEvidence(
        geometry_indices=(geometry_index, geometry_index + 1),
        semantic_indices=(semantic_index, semantic_index + 1, semantic_index + 2),
        ordinary_mean_similarity=round(ordinary_mean, 6),
        overflow_mean_similarity=round(overflow_mean, 6),
        score_gain=round(gain, 6),
        first_numeric_fingerprint_exact=True,
        second_numeric_fingerprint_exact=True,
        third_semantic_row_cells_blank=True,
        semantic_value_cells_unmodified=True,
        geometry_cells_unmodified=True,
    )
    return _PathStep(
        action="OVERFLOW_SHIFT_3_TO_2",
        geometry_indices=(geometry_index, geometry_index + 1),
        semantic_label_indices=(
            (semantic_index, semantic_index + 1),
            (semantic_index + 2,),
        ),
        semantic_value_indices=((semantic_index,), (semantic_index + 1,)),
        labels=(combined_label, semantic_next.label),
        similarities=(first_similarity, second_similarity),
        overflow_evidence=evidence,
    )


def _retain_two_best(paths: list[_Path], candidate: _Path) -> None:
    signature = tuple(
        (step.action, step.geometry_indices, step.semantic_label_indices)
        for step in candidate.steps
    )
    for existing in paths:
        existing_signature = tuple(
            (step.action, step.geometry_indices, step.semantic_label_indices)
            for step in existing.steps
        )
        if signature == existing_signature:
            return
    paths.append(candidate)
    paths.sort(key=lambda item: item.score, reverse=True)
    del paths[2:]


def _unresolved(*reasons: str) -> SemanticGeometryFusionResult:
    return SemanticGeometryFusionResult(
        status="UNRESOLVED_SEMANTIC_GEOMETRY_FUSION",
        rows=(),
        overflow_repairs=(),
        unresolved_reasons=tuple(reasons),
        best_path_mean_score=None,
        second_path_mean_score=None,
        path_score_margin=None,
        geometry_cells_unmodified=True,
        automatic_acceptance=False,
        confidence_effect="NONE",
    )


def fuse_semantic_labels_onto_geometry_rows(
    geometry_rows: tuple[ReaderRow, ...],
    semantic_rows: tuple[ReaderRow, ...],
    config: SemanticGeometryFusionConfig,
) -> SemanticGeometryFusionResult:
    """Fuse Vietnamese labels onto a fixed geometry grid with fail-closed overflow repair.

    The dynamic program supports ordinary 1:1 label association and one explicit
    3-semantic-row to 2-geometry-row overflow pattern. Numeric fingerprints only
    gate the structural hypothesis; final cells, notes, row count, and source IDs
    always remain byte-for-byte/object-identical to the geometry proposal.
    """

    if not geometry_rows:
        return _unresolved("geometry row grid is empty")
    if not semantic_rows:
        return _unresolved("semantic row proposal is empty")
    if len(semantic_rows) < len(geometry_rows):
        return _unresolved("semantic proposal has fewer rows than the fixed geometry grid")

    geometry_count = len(geometry_rows)
    semantic_count = len(semantic_rows)
    states: dict[tuple[int, int], list[_Path]] = {(0, 0): [_Path(0.0, ())]}
    for geometry_index in range(geometry_count + 1):
        for semantic_index in range(semantic_count + 1):
            current_paths = states.get((geometry_index, semantic_index), ())
            for current in tuple(current_paths):
                if geometry_index < geometry_count and semantic_index < semantic_count:
                    similarity = _label_similarity(
                        geometry_rows[geometry_index].label,
                        semantic_rows[semantic_index].label,
                    )
                    step = _PathStep(
                        action="ONE_TO_ONE",
                        geometry_indices=(geometry_index,),
                        semantic_label_indices=((semantic_index,),),
                        semantic_value_indices=((semantic_index,),),
                        labels=(semantic_rows[semantic_index].label,),
                        similarities=(similarity,),
                    )
                    target = states.setdefault((geometry_index + 1, semantic_index + 1), [])
                    _retain_two_best(
                        target,
                        _Path(current.score + similarity, current.steps + (step,)),
                    )
                overflow = _overflow_step(
                    geometry_rows,
                    semantic_rows,
                    geometry_index,
                    semantic_index,
                    config,
                )
                if overflow is not None:
                    target = states.setdefault((geometry_index + 2, semantic_index + 3), [])
                    _retain_two_best(
                        target,
                        _Path(
                            current.score + sum(overflow.similarities),
                            current.steps + (overflow,),
                        ),
                    )

    terminal = states.get((geometry_count, semantic_count), [])
    if not terminal:
        return _unresolved(
            "row-count difference cannot be explained by a verified overflow pattern"
        )
    best = terminal[0]
    second = terminal[1] if len(terminal) > 1 else None
    best_mean = best.score / geometry_count
    second_mean = second.score / geometry_count if second is not None else None
    margin = best_mean - second_mean if second_mean is not None else None
    if margin is not None and margin < config.minimum_path_score_margin:
        return _unresolved(
            "best structural path does not exceed the runner-up by the configured margin"
        )

    fused_rows: list[FusedSemanticGeometryRow] = []
    repairs: list[OverflowShiftEvidence] = []
    low_similarity: list[int] = []
    for step in best.steps:
        if step.overflow_evidence is not None:
            repairs.append(step.overflow_evidence)
        for position, geometry_index in enumerate(step.geometry_indices):
            geometry = geometry_rows[geometry_index]
            label_indices = step.semantic_label_indices[position]
            value_indices = step.semantic_value_indices[position]
            similarity = step.similarities[position]
            if similarity < config.minimum_output_label_similarity:
                low_similarity.append(geometry_index)
            semantic_value = semantic_rows[value_indices[0]]
            fused_rows.append(
                FusedSemanticGeometryRow(
                    row=ReaderRow(
                        source_row_ids=geometry.source_row_ids,
                        label=normalize_text(step.labels[position]),
                        note_reference=geometry.note_reference,
                        cells=geometry.cells,
                    ),
                    geometry_index=geometry_index,
                    semantic_label_indices=label_indices,
                    semantic_value_indices=value_indices,
                    geometry_source_row_ids=geometry.source_row_ids,
                    semantic_label_source_row_ids=_source_ids(semantic_rows, label_indices),
                    semantic_value_source_row_ids=_source_ids(semantic_rows, value_indices),
                    label_similarity=round(similarity, 6),
                    semantic_value_fingerprint_exact=_numeric_fingerprint_exact(
                        geometry,
                        semantic_value,
                        require_observed=False,
                    ),
                    geometry_cells_unmodified=True,
                    geometry_note_unmodified=True,
                    action=step.action,
                )
            )
    if low_similarity:
        return _unresolved(
            "one or more fused labels fall below the minimum similarity: "
            + ",".join(map(str, low_similarity))
        )
    if len(fused_rows) != geometry_count:
        raise AssertionError("fusion changed the fixed geometry row count")
    if any(
        item.row.cells is not geometry_rows[item.geometry_index].cells
        or item.row.source_row_ids != geometry_rows[item.geometry_index].source_row_ids
        or item.row.note_reference != geometry_rows[item.geometry_index].note_reference
        for item in fused_rows
    ):
        raise AssertionError("fusion mutated geometry-authoritative evidence")
    return SemanticGeometryFusionResult(
        status="FUSED_SEMANTIC_LABELS_ON_FIXED_GEOMETRY_GRID",
        rows=tuple(fused_rows),
        overflow_repairs=tuple(repairs),
        unresolved_reasons=(),
        best_path_mean_score=round(best_mean, 6),
        second_path_mean_score=round(second_mean, 6) if second_mean is not None else None,
        path_score_margin=round(margin, 6) if margin is not None else None,
        geometry_cells_unmodified=True,
        automatic_acceptance=False,
        confidence_effect="NONE",
    )


def semantic_geometry_fusion_to_dict(result: SemanticGeometryFusionResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "policy": {
            "fixed_grid_source": "GEOMETRY_READER",
            "label_proposal_source": "SEMANTIC_READER",
            "numeric_fingerprints_gate_structure_only": True,
            "semantic_values_have_output_authority": False,
            "geometry_cells_unmodified": result.geometry_cells_unmodified,
            "automatic_acceptance": result.automatic_acceptance,
            "confidence_effect": result.confidence_effect,
        },
        "path": {
            "best_mean_score": result.best_path_mean_score,
            "second_mean_score": result.second_path_mean_score,
            "score_margin": result.path_score_margin,
        },
        "unresolved_reasons": list(result.unresolved_reasons),
        "overflow_repairs": [
            {
                "geometry_indices": list(item.geometry_indices),
                "semantic_indices": list(item.semantic_indices),
                "ordinary_mean_similarity": item.ordinary_mean_similarity,
                "overflow_mean_similarity": item.overflow_mean_similarity,
                "score_gain": item.score_gain,
                "first_numeric_fingerprint_exact": item.first_numeric_fingerprint_exact,
                "second_numeric_fingerprint_exact": item.second_numeric_fingerprint_exact,
                "third_semantic_row_cells_blank": item.third_semantic_row_cells_blank,
                "semantic_value_cells_unmodified": item.semantic_value_cells_unmodified,
                "geometry_cells_unmodified": item.geometry_cells_unmodified,
            }
            for item in result.overflow_repairs
        ],
        "rows": [
            {
                "geometry_index": item.geometry_index,
                "semantic_label_indices": list(item.semantic_label_indices),
                "semantic_value_indices": list(item.semantic_value_indices),
                "geometry_source_row_ids": list(item.geometry_source_row_ids),
                "semantic_label_source_row_ids": list(item.semantic_label_source_row_ids),
                "semantic_value_source_row_ids": list(item.semantic_value_source_row_ids),
                "label_similarity": item.label_similarity,
                "semantic_value_fingerprint_exact": item.semantic_value_fingerprint_exact,
                "geometry_cells_unmodified": item.geometry_cells_unmodified,
                "geometry_note_unmodified": item.geometry_note_unmodified,
                "action": item.action,
                "row": reader_row_to_dict(item.row),
            }
            for item in result.rows
        ],
    }
