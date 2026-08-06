from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from rapidfuzz.fuzz import ratio

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.text import normalize_text, retrieval_key
from bctc_ai.evaluation.reader_outputs import reader_row_to_dict
from bctc_ai.validation.reader_agreement import (
    ReaderRow,
    align_ordered_reader_rows,
)


class SemanticGeometryFusionV2Error(RuntimeError):
    pass


@dataclass(frozen=True)
class SemanticGeometryFusionV2Config:
    gap_penalty: float
    candidate_merge_penalty: float
    reference_merge_penalty: float
    minimum_output_label_similarity: float
    minimum_split_segment_similarity: float
    minimum_split_mean_similarity: float
    minimum_split_runner_up_margin: float
    minimum_trimmed_similarity: float
    minimum_trimmed_gain: float
    minimum_trimmed_runner_up_margin: float
    maximum_trimmed_token_fraction: float


@dataclass(frozen=True)
class LabelSegmentationEvidence:
    action: str
    geometry_indices: tuple[int, ...]
    semantic_indices: tuple[int, ...]
    source_label: str
    proposed_labels: tuple[str, ...]
    token_ranges: tuple[tuple[int, int], ...]
    similarities: tuple[float, ...]
    mean_similarity: float
    runner_up_mean_similarity: float | None
    score_margin: float | None
    dropped_token_indices: tuple[int, ...]


@dataclass(frozen=True)
class IgnoredSemanticRowEvidence:
    semantic_index: int
    source_row_ids: tuple[str, ...]
    label: str
    note_reference: str | None
    matching_geometry_indices: tuple[int, ...]
    reason: str


@dataclass(frozen=True)
class FusedSemanticGeometryRowV2:
    row: ReaderRow
    geometry_index: int
    semantic_label_indices: tuple[int, ...]
    semantic_value_indices: tuple[int, ...]
    geometry_source_row_ids: tuple[str, ...]
    semantic_label_source_row_ids: tuple[str, ...]
    semantic_value_source_row_ids: tuple[str, ...]
    label_similarity: float
    semantic_numeric_fingerprint_observed: bool
    geometry_cells_unmodified: bool
    geometry_note_unmodified: bool
    action: str
    token_range: tuple[int, int] | None


@dataclass(frozen=True)
class SemanticGeometryFusionV2Result:
    status: str
    rows: tuple[FusedSemanticGeometryRowV2, ...]
    segmentations: tuple[LabelSegmentationEvidence, ...]
    ignored_semantic_rows: tuple[IgnoredSemanticRowEvidence, ...]
    alignment_action_counts: tuple[tuple[str, int], ...]
    unresolved_reasons: tuple[str, ...]
    geometry_cells_unmodified: bool
    automatic_acceptance: bool
    confidence_effect: str

    @property
    def reader_rows(self) -> tuple[ReaderRow, ...]:
        return tuple(item.row for item in self.rows)


@dataclass(frozen=True)
class _LabelProposal:
    geometry_index: int
    semantic_indices: tuple[int, ...]
    label: str
    similarity: float
    action: str
    token_range: tuple[int, int] | None


def _number(payload: dict[str, Any], name: str) -> float:
    value = payload.get(name)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 1:
        raise SemanticGeometryFusionV2Error(f"invalid v2 fusion threshold: {name}")
    return float(value)


def load_semantic_geometry_fusion_v2_config(path: Path) -> SemanticGeometryFusionV2Config:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, yaml.YAMLError) as exc:
        raise SemanticGeometryFusionV2Error(f"cannot read v2 fusion config: {path}") from exc
    if not isinstance(payload, dict) or payload.get("version") != 2:
        raise SemanticGeometryFusionV2Error("semantic-geometry fusion config must be version 2")
    if payload.get("algorithm") != "ORDERED_LABEL_SEGMENTATION_ON_FIXED_GEOMETRY_GRID_V2":
        raise SemanticGeometryFusionV2Error("unexpected v2 semantic-geometry algorithm")
    alignment = payload.get("alignment")
    segmentation = payload.get("label_segmentation")
    extra = payload.get("extra_semantic_row")
    safety = payload.get("safety")
    if not isinstance(alignment, dict) or not isinstance(segmentation, dict):
        raise SemanticGeometryFusionV2Error("v2 fusion config lacks alignment settings")
    if extra != {
        "require_empty_label": True,
        "require_exact_observed_numeric_fingerprint": True,
        "require_note_match_when_present": True,
    }:
        raise SemanticGeometryFusionV2Error("extra-row safety contract drifted")
    if not isinstance(safety, dict) or not safety or any(bool(value) for value in safety.values()):
        raise SemanticGeometryFusionV2Error("v2 fusion config grants forbidden authority")
    gap_penalty = alignment.get("gap_penalty")
    candidate_penalty = alignment.get("candidate_merge_penalty")
    reference_penalty = alignment.get("reference_merge_penalty")
    if (
        not isinstance(gap_penalty, (int, float))
        or isinstance(gap_penalty, bool)
        or gap_penalty <= 0
        or not isinstance(candidate_penalty, (int, float))
        or isinstance(candidate_penalty, bool)
        or candidate_penalty < 0
        or not isinstance(reference_penalty, (int, float))
        or isinstance(reference_penalty, bool)
        or reference_penalty < 0
    ):
        raise SemanticGeometryFusionV2Error("invalid v2 alignment penalty")
    return SemanticGeometryFusionV2Config(
        gap_penalty=float(gap_penalty),
        candidate_merge_penalty=float(candidate_penalty),
        reference_merge_penalty=float(reference_penalty),
        minimum_output_label_similarity=_number(segmentation, "minimum_output_label_similarity"),
        minimum_split_segment_similarity=_number(segmentation, "minimum_split_segment_similarity"),
        minimum_split_mean_similarity=_number(segmentation, "minimum_split_mean_similarity"),
        minimum_split_runner_up_margin=_number(segmentation, "minimum_split_runner_up_margin"),
        minimum_trimmed_similarity=_number(segmentation, "minimum_trimmed_similarity"),
        minimum_trimmed_gain=_number(segmentation, "minimum_trimmed_gain"),
        minimum_trimmed_runner_up_margin=_number(segmentation, "minimum_trimmed_runner_up_margin"),
        maximum_trimmed_token_fraction=_number(segmentation, "maximum_trimmed_token_fraction"),
    )


def _label_similarity(left: str, right: str) -> float:
    left_key = retrieval_key(left)
    right_key = retrieval_key(right)
    if not left_key and not right_key:
        return 1.0
    if not left_key or not right_key:
        return 0.0
    return ratio(left_key, right_key) / 100.0


def _has_observed_cells(row: ReaderRow) -> bool:
    return any(cell.observation is not ObservationKind.BLANK for cell in row.cells)


def _numeric_fingerprint_exact(geometry: ReaderRow, semantic: ReaderRow) -> bool:
    if not geometry.cells or len(geometry.cells) != len(semantic.cells):
        return False
    if not _has_observed_cells(geometry):
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


def _split_two_labels(
    geometry_rows: tuple[ReaderRow, ReaderRow],
    semantic_label: str,
    geometry_indices: tuple[int, int],
    semantic_indices: tuple[int, ...],
    config: SemanticGeometryFusionV2Config,
) -> tuple[tuple[_LabelProposal, _LabelProposal], LabelSegmentationEvidence] | None:
    tokens = normalize_text(semantic_label).split()
    if len(tokens) < 2:
        return None
    candidates = []
    for boundary in range(1, len(tokens)):
        labels = (" ".join(tokens[:boundary]), " ".join(tokens[boundary:]))
        similarities = tuple(
            _label_similarity(geometry.label, label)
            for geometry, label in zip(geometry_rows, labels, strict=True)
        )
        candidates.append((sum(similarities) / 2, boundary, similarities, labels))
    candidates.sort(key=lambda item: (item[0], min(item[2]), -item[1]), reverse=True)
    best = candidates[0]
    runner_up = candidates[1] if len(candidates) > 1 else None
    margin = best[0] - runner_up[0] if runner_up is not None else None
    if (
        best[0] < config.minimum_split_mean_similarity
        or min(best[2]) < config.minimum_split_segment_similarity
        or (margin is not None and margin < config.minimum_split_runner_up_margin)
    ):
        return None
    boundary = best[1]
    proposals = tuple(
        _LabelProposal(
            geometry_index=geometry_index,
            semantic_indices=semantic_indices,
            label=label,
            similarity=similarity,
            action="SPLIT_COLLAPSED_SEMANTIC_LABEL_1_TO_2",
            token_range=token_range,
        )
        for geometry_index, label, similarity, token_range in zip(
            geometry_indices,
            best[3],
            best[2],
            ((0, boundary), (boundary, len(tokens))),
            strict=True,
        )
    )
    evidence = LabelSegmentationEvidence(
        action="SPLIT_COLLAPSED_SEMANTIC_LABEL_1_TO_2",
        geometry_indices=geometry_indices,
        semantic_indices=semantic_indices,
        source_label=semantic_label,
        proposed_labels=best[3],
        token_ranges=((0, boundary), (boundary, len(tokens))),
        similarities=tuple(round(value, 6) for value in best[2]),
        mean_similarity=round(best[0], 6),
        runner_up_mean_similarity=(round(runner_up[0], 6) if runner_up is not None else None),
        score_margin=round(margin, 6) if margin is not None else None,
        dropped_token_indices=(),
    )
    return proposals, evidence


def _trim_duplicate_edge_tokens(
    geometry_label: str,
    semantic_label: str,
    geometry_index: int,
    semantic_indices: tuple[int, ...],
    config: SemanticGeometryFusionV2Config,
) -> tuple[_LabelProposal, LabelSegmentationEvidence | None]:
    normalized = normalize_text(semantic_label)
    tokens = normalized.split()
    full_similarity = _label_similarity(geometry_label, normalized)
    if len(tokens) < 2:
        return (
            _LabelProposal(
                geometry_index,
                semantic_indices,
                normalized,
                full_similarity,
                "ONE_TO_ONE",
                None,
            ),
            None,
        )
    candidates = []
    for start in range(len(tokens)):
        for end in range(start + 1, len(tokens) + 1):
            if start != 0 and end != len(tokens):
                continue
            label = " ".join(tokens[start:end])
            candidates.append((_label_similarity(geometry_label, label), start, end, label))
    candidates.sort(
        key=lambda item: (item[0], item[2] - item[1], -item[1]),
        reverse=True,
    )
    best = candidates[0]
    runner_up = next(
        (item for item in candidates[1:] if (item[1], item[2]) != (0, len(tokens))),
        None,
    )
    dropped = tuple(index for index in range(len(tokens)) if not best[1] <= index < best[2])
    dropped_fraction = len(dropped) / len(tokens)
    runner_margin = best[0] - runner_up[0] if runner_up is not None else None
    may_trim = (
        bool(dropped)
        and best[0] >= config.minimum_trimmed_similarity
        and best[0] - full_similarity >= config.minimum_trimmed_gain
        and dropped_fraction <= config.maximum_trimmed_token_fraction
        and (runner_margin is None or runner_margin >= config.minimum_trimmed_runner_up_margin)
    )
    if not may_trim:
        return (
            _LabelProposal(
                geometry_index,
                semantic_indices,
                normalized,
                full_similarity,
                "ONE_TO_ONE",
                None,
            ),
            None,
        )
    proposal = _LabelProposal(
        geometry_index=geometry_index,
        semantic_indices=semantic_indices,
        label=best[3],
        similarity=best[0],
        action="TRIM_DUPLICATE_EDGE_TOKENS",
        token_range=(best[1], best[2]),
    )
    evidence = LabelSegmentationEvidence(
        action="TRIM_DUPLICATE_EDGE_TOKENS",
        geometry_indices=(geometry_index,),
        semantic_indices=semantic_indices,
        source_label=semantic_label,
        proposed_labels=(best[3],),
        token_ranges=((best[1], best[2]),),
        similarities=(round(best[0], 6),),
        mean_similarity=round(best[0], 6),
        runner_up_mean_similarity=(round(runner_up[0], 6) if runner_up is not None else None),
        score_margin=round(runner_margin, 6) if runner_margin is not None else None,
        dropped_token_indices=dropped,
    )
    return proposal, evidence


def _unresolved(
    action_counts: Counter[str],
    reasons: list[str],
    ignored: list[IgnoredSemanticRowEvidence] | None = None,
) -> SemanticGeometryFusionV2Result:
    return SemanticGeometryFusionV2Result(
        status="UNRESOLVED_SEMANTIC_GEOMETRY_FUSION_V2",
        rows=(),
        segmentations=(),
        ignored_semantic_rows=tuple(ignored or ()),
        alignment_action_counts=tuple(sorted(action_counts.items())),
        unresolved_reasons=tuple(reasons),
        geometry_cells_unmodified=True,
        automatic_acceptance=False,
        confidence_effect="NONE",
    )


def fuse_ordered_semantic_labels_onto_geometry_rows_v2(
    geometry_rows: tuple[ReaderRow, ...],
    semantic_rows: tuple[ReaderRow, ...],
    config: SemanticGeometryFusionV2Config,
) -> SemanticGeometryFusionV2Result:
    """Segment collapsed semantic labels over an immutable geometry row grid.

    Alignment uses only document order and normalized label text. Values can
    verify that a label-empty semantic row is displaced evidence, but never
    affect the alignment path or replace a geometry cell.
    """

    if not geometry_rows or not semantic_rows:
        return _unresolved(Counter(), ["both geometry and semantic rows are required"])
    alignment = align_ordered_reader_rows(
        geometry_rows,
        semantic_rows,
        gap_penalty=config.gap_penalty,
        candidate_merge_penalty=config.candidate_merge_penalty,
        reference_merge_penalty=config.reference_merge_penalty,
    )
    action_counts = Counter(step.action for step in alignment)
    proposals: dict[int, _LabelProposal] = {}
    segmentations: list[LabelSegmentationEvidence] = []
    ignored: list[IgnoredSemanticRowEvidence] = []
    reasons: list[str] = []

    for step in alignment:
        if step.action == "MISSING_CANDIDATE":
            reasons.append(
                f"geometry rows {step.reference_indices} have no semantic label proposal"
            )
            continue
        if step.action == "EXTRA_CANDIDATE":
            semantic_index = step.candidate_indices[0]
            semantic = semantic_rows[semantic_index]
            matching = tuple(
                index
                for index, geometry in enumerate(geometry_rows)
                if _numeric_fingerprint_exact(geometry, semantic)
            )
            note_matches = semantic.note_reference is None or any(
                geometry_rows[index].note_reference is not None
                and retrieval_key(geometry_rows[index].note_reference or "")
                == retrieval_key(semantic.note_reference)
                for index in matching
            )
            if normalize_text(semantic.label) or not matching or not note_matches:
                reasons.append(
                    f"extra semantic row {semantic_index} lacks safe blank-label fingerprint evidence"
                )
                continue
            ignored.append(
                IgnoredSemanticRowEvidence(
                    semantic_index=semantic_index,
                    source_row_ids=semantic.source_row_ids,
                    label=semantic.label,
                    note_reference=semantic.note_reference,
                    matching_geometry_indices=matching,
                    reason="BLANK_LABEL_DISPLACED_NUMERIC_FINGERPRINT_ONLY",
                )
            )
            continue
        if step.action == "MERGE_REFERENCE":
            if len(step.reference_indices) != 2 or len(step.candidate_indices) != 1:
                reasons.append("only explicit two-geometry-row label splits are supported")
                continue
            geometry_pair = tuple(geometry_rows[index] for index in step.reference_indices)
            split = _split_two_labels(
                geometry_pair,
                semantic_rows[step.candidate_indices[0]].label,
                step.reference_indices,
                step.candidate_indices,
                config,
            )
            if split is None:
                reasons.append(
                    f"collapsed semantic label {step.candidate_indices} has no decisive split"
                )
                continue
            split_proposals, evidence = split
            for proposal in split_proposals:
                proposals[proposal.geometry_index] = proposal
            segmentations.append(evidence)
            continue
        if step.action == "MERGE_CANDIDATE":
            geometry_index = step.reference_indices[0]
            if step.candidate is None:
                reasons.append("merged semantic label proposal is absent")
                continue
            proposals[geometry_index] = _LabelProposal(
                geometry_index=geometry_index,
                semantic_indices=step.candidate_indices,
                label=step.candidate.label,
                similarity=float(step.semantic_similarity or 0.0),
                action="MERGE_ADJACENT_SEMANTIC_LABEL_FRAGMENTS",
                token_range=None,
            )
            segmentations.append(
                LabelSegmentationEvidence(
                    action="MERGE_ADJACENT_SEMANTIC_LABEL_FRAGMENTS",
                    geometry_indices=(geometry_index,),
                    semantic_indices=step.candidate_indices,
                    source_label=" | ".join(
                        semantic_rows[index].label for index in step.candidate_indices
                    ),
                    proposed_labels=(step.candidate.label,),
                    token_ranges=(),
                    similarities=(float(step.semantic_similarity or 0.0),),
                    mean_similarity=float(step.semantic_similarity or 0.0),
                    runner_up_mean_similarity=None,
                    score_margin=None,
                    dropped_token_indices=(),
                )
            )
            continue
        if step.action != "MATCH":
            reasons.append(f"unsupported alignment action: {step.action}")
            continue
        geometry_index = step.reference_indices[0]
        candidate_index = step.candidate_indices[0]
        proposal, evidence = _trim_duplicate_edge_tokens(
            geometry_rows[geometry_index].label,
            semantic_rows[candidate_index].label,
            geometry_index,
            (candidate_index,),
            config,
        )
        proposals[geometry_index] = proposal
        if evidence is not None:
            segmentations.append(evidence)

    expected_indices = set(range(len(geometry_rows)))
    missing = sorted(expected_indices - proposals.keys())
    if missing:
        reasons.append(
            "no semantic label proposal for geometry rows: " + ",".join(map(str, missing))
        )
    low_similarity = sorted(
        index
        for index, proposal in proposals.items()
        if proposal.similarity < config.minimum_output_label_similarity
    )
    if low_similarity:
        reasons.append(
            "fused label similarity below threshold for geometry rows: "
            + ",".join(map(str, low_similarity))
        )
    if reasons:
        return _unresolved(action_counts, reasons, ignored)

    fused_rows = []
    for geometry_index, geometry in enumerate(geometry_rows):
        proposal = proposals[geometry_index]
        value_indices = tuple(
            index
            for index, semantic in enumerate(semantic_rows)
            if _numeric_fingerprint_exact(geometry, semantic)
        )
        fused_rows.append(
            FusedSemanticGeometryRowV2(
                row=ReaderRow(
                    source_row_ids=geometry.source_row_ids,
                    label=proposal.label,
                    note_reference=geometry.note_reference,
                    cells=geometry.cells,
                ),
                geometry_index=geometry_index,
                semantic_label_indices=proposal.semantic_indices,
                semantic_value_indices=value_indices,
                geometry_source_row_ids=geometry.source_row_ids,
                semantic_label_source_row_ids=_source_ids(semantic_rows, proposal.semantic_indices),
                semantic_value_source_row_ids=_source_ids(semantic_rows, value_indices),
                label_similarity=round(proposal.similarity, 6),
                semantic_numeric_fingerprint_observed=bool(value_indices),
                geometry_cells_unmodified=True,
                geometry_note_unmodified=True,
                action=proposal.action,
                token_range=proposal.token_range,
            )
        )
    if any(
        item.row.cells is not geometry_rows[item.geometry_index].cells
        or item.row.source_row_ids != geometry_rows[item.geometry_index].source_row_ids
        or item.row.note_reference != geometry_rows[item.geometry_index].note_reference
        for item in fused_rows
    ):
        raise AssertionError("v2 fusion mutated geometry-authoritative evidence")
    return SemanticGeometryFusionV2Result(
        status="FUSED_ORDERED_SEMANTIC_LABELS_ON_FIXED_GEOMETRY_GRID_V2",
        rows=tuple(fused_rows),
        segmentations=tuple(segmentations),
        ignored_semantic_rows=tuple(ignored),
        alignment_action_counts=tuple(sorted(action_counts.items())),
        unresolved_reasons=(),
        geometry_cells_unmodified=True,
        automatic_acceptance=False,
        confidence_effect="NONE",
    )


def semantic_geometry_fusion_v2_to_dict(
    result: SemanticGeometryFusionV2Result,
) -> dict[str, Any]:
    return {
        "status": result.status,
        "policy": {
            "alignment_features": ["DOCUMENT_ORDER", "NORMALIZED_LABEL_TEXT"],
            "values_or_notes_affect_alignment": False,
            "numeric_fingerprints_gate_ignored_blank_label_rows_only": True,
            "fixed_grid_source": "GEOMETRY_READER",
            "semantic_values_have_output_authority": False,
            "geometry_cells_unmodified": result.geometry_cells_unmodified,
            "automatic_acceptance": result.automatic_acceptance,
            "confidence_effect": result.confidence_effect,
        },
        "alignment_action_counts": dict(result.alignment_action_counts),
        "unresolved_reasons": list(result.unresolved_reasons),
        "segmentations": [
            {
                "action": item.action,
                "geometry_indices": list(item.geometry_indices),
                "semantic_indices": list(item.semantic_indices),
                "source_label": item.source_label,
                "proposed_labels": list(item.proposed_labels),
                "token_ranges": [list(value) for value in item.token_ranges],
                "similarities": list(item.similarities),
                "mean_similarity": item.mean_similarity,
                "runner_up_mean_similarity": item.runner_up_mean_similarity,
                "score_margin": item.score_margin,
                "dropped_token_indices": list(item.dropped_token_indices),
            }
            for item in result.segmentations
        ],
        "ignored_semantic_rows": [
            {
                "semantic_index": item.semantic_index,
                "source_row_ids": list(item.source_row_ids),
                "label": item.label,
                "note_reference": item.note_reference,
                "matching_geometry_indices": list(item.matching_geometry_indices),
                "reason": item.reason,
            }
            for item in result.ignored_semantic_rows
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
                "semantic_numeric_fingerprint_observed": (
                    item.semantic_numeric_fingerprint_observed
                ),
                "geometry_cells_unmodified": item.geometry_cells_unmodified,
                "geometry_note_unmodified": item.geometry_note_unmodified,
                "action": item.action,
                "token_range": list(item.token_range) if item.token_range else None,
                "row": reader_row_to_dict(item.row),
            }
            for item in result.rows
        ],
    }
