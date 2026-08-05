from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.text import retrieval_key


class CashFlowMethod(StrEnum):
    DIRECT = "DIRECT"
    INDIRECT = "INDIRECT"
    BOTH = "BOTH"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class CashFlowRules:
    version: int
    authority: str
    semantic_authority_status: str
    maximum_anchor_distance: int
    label_sequences: dict[CashFlowMethod, tuple[tuple[str, ...], ...]]
    schema_order_blocks: dict[CashFlowMethod, tuple[tuple[int, int], ...]]
    source_path: Path


@dataclass(frozen=True)
class CashFlowEvidence:
    method: CashFlowMethod
    indirect_anchor_positions: tuple[int, ...] | None
    direct_anchor_positions: tuple[int, ...] | None
    reason: str
    semantic_high_confidence_allowed: bool


def load_cash_flow_rules(path: Path) -> CashFlowRules:
    """Load semantic branch rules so bank-specific aliases remain data, not code."""
    payload: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    version = payload.get("version")
    branches = payload.get("branches")
    maximum_distance = payload.get("maximum_anchor_distance")
    if not isinstance(version, int) or not isinstance(branches, dict):
        raise ValueError(f"invalid cash-flow rule file: {path}")
    if not isinstance(maximum_distance, int) or maximum_distance < 1:
        raise ValueError(f"invalid maximum_anchor_distance: {path}")

    sequences: dict[CashFlowMethod, tuple[tuple[str, ...], ...]] = {}
    schema_order_blocks: dict[CashFlowMethod, tuple[tuple[int, int], ...]] = {}
    for method in (CashFlowMethod.DIRECT, CashFlowMethod.INDIRECT):
        branch = branches.get(method.value)
        if not isinstance(branch, dict):
            raise ValueError(f"missing {method.value} branch: {path}")
        raw_sequences = branch.get("label_anchor_sequences")
        raw_blocks = branch.get("schema_order_blocks")
        if not isinstance(raw_sequences, list) or not raw_sequences:
            raise ValueError(f"missing {method.value} label sequences: {path}")
        if not isinstance(raw_blocks, list) or not raw_blocks:
            raise ValueError(f"missing {method.value} schema order blocks: {path}")
        blocks: list[tuple[int, int]] = []
        for block in raw_blocks:
            if (
                not isinstance(block, list)
                or len(block) != 2
                or not all(isinstance(value, int) for value in block)
            ):
                raise ValueError(f"invalid {method.value} schema order block: {path}")
            blocks.append((block[0], block[1]))
        normalized: list[tuple[str, ...]] = []
        for sequence in raw_sequences:
            if not isinstance(sequence, list) or len(sequence) < 2:
                raise ValueError(f"invalid {method.value} label sequence: {path}")
            keys = tuple(retrieval_key(str(label)) for label in sequence)
            if any(not key for key in keys):
                raise ValueError(f"empty {method.value} label anchor: {path}")
            normalized.append(keys)
        sequences[method] = tuple(normalized)
        schema_order_blocks[method] = tuple(blocks)

    return CashFlowRules(
        version=version,
        authority=str(payload.get("authority", "UNSPECIFIED")),
        semantic_authority_status=str(payload.get("semantic_authority_status", "UNSPECIFIED")),
        maximum_anchor_distance=maximum_distance,
        label_sequences=sequences,
        schema_order_blocks=schema_order_blocks,
        source_path=path.resolve(),
    )


def assign_cash_flow_schema_branches(
    ordered_schema_ids: list[int],
    rules: CashFlowRules,
) -> dict[int, CashFlowMethod]:
    """Assign contiguous blocks by workbook position, never by numeric ID range."""
    if len(ordered_schema_ids) != len(set(ordered_schema_ids)):
        raise ValueError("cash-flow schema order contains duplicate IDs")
    positions = {schema_id: index for index, schema_id in enumerate(ordered_schema_ids)}
    assignments: dict[int, CashFlowMethod] = {}
    for method, blocks in rules.schema_order_blocks.items():
        for start_id, end_id in blocks:
            if start_id not in positions or end_id not in positions:
                raise ValueError(f"cash-flow order block endpoint missing: {start_id} -> {end_id}")
            start, end = positions[start_id], positions[end_id]
            if start > end:
                raise ValueError(
                    f"cash-flow order block is reversed in workbook: {start_id} -> {end_id}"
                )
            for schema_id in ordered_schema_ids[start : end + 1]:
                previous = assignments.get(schema_id)
                if previous is not None:
                    raise ValueError(
                        f"cash-flow schema ID {schema_id} assigned to {previous} and {method}"
                    )
                assignments[schema_id] = method
    missing = [schema_id for schema_id in ordered_schema_ids if schema_id not in assignments]
    if missing:
        raise ValueError(f"cash-flow schema order blocks leave IDs unassigned: {missing}")
    return assignments


def _ordered_sequence(
    label_keys: list[str],
    anchors: tuple[str, ...],
    *,
    maximum_distance: int,
) -> tuple[int, ...] | None:
    """Find anchors in order within a bounded local block, allowing intervening rows."""
    for start_index, key in enumerate(label_keys):
        if anchors[0] not in key:
            continue
        positions = [start_index]
        previous = start_index
        matched = True
        for anchor in anchors[1:]:
            limit = min(len(label_keys), previous + maximum_distance + 1)
            next_index = next(
                (index for index in range(previous + 1, limit) if anchor in label_keys[index]),
                None,
            )
            if next_index is None:
                matched = False
                break
            positions.append(next_index)
            previous = next_index
        if matched:
            return tuple(positions)
    return None


def _first_matching_sequence(
    label_keys: list[str],
    sequences: tuple[tuple[str, ...], ...],
    *,
    maximum_distance: int,
) -> tuple[int, ...] | None:
    for sequence in sequences:
        positions = _ordered_sequence(
            label_keys,
            sequence,
            maximum_distance=maximum_distance,
        )
        if positions is not None:
            return positions
    return None


def classify_cash_flow_method(
    labels: list[str],
    rules: CashFlowRules | None,
) -> CashFlowEvidence:
    if rules is None:
        return CashFlowEvidence(
            CashFlowMethod.UNKNOWN,
            None,
            None,
            "cash-flow rules missing; classification is fail-closed",
            False,
        )

    label_keys = [retrieval_key(label) for label in labels]
    indirect = _first_matching_sequence(
        label_keys,
        rules.label_sequences[CashFlowMethod.INDIRECT],
        maximum_distance=rules.maximum_anchor_distance,
    )
    direct = _first_matching_sequence(
        label_keys,
        rules.label_sequences[CashFlowMethod.DIRECT],
        maximum_distance=rules.maximum_anchor_distance,
    )
    if indirect and direct:
        method = CashFlowMethod.BOTH
        reason = "both configured ordered anchor sequences observed"
    elif indirect:
        method = CashFlowMethod.INDIRECT
        reason = "configured indirect ordered anchor sequence observed"
    elif direct:
        method = CashFlowMethod.DIRECT
        reason = "configured direct ordered anchor sequence observed"
    else:
        method = CashFlowMethod.UNKNOWN
        reason = "neither configured ordered anchor sequence is sufficiently observed"
    semantic_allowed = rules.semantic_authority_status == "RESOLVED"
    if not semantic_allowed:
        reason += f"; semantic status={rules.semantic_authority_status}, acceptance fail-closed"
    return CashFlowEvidence(method, indirect, direct, reason, semantic_allowed)
