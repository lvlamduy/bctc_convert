"""Minimal pair-before-triple uniqueness over caller-bounded family candidates.

The resolver is deliberately family-neutral and evidence-only.  It compares
anchor sets from every supplied COMPLETE and NEAR topology candidate in one
caller-bound document scope.  It grants no text, numeric, mapping, retrieval,
or authentication authority.
"""

from __future__ import annotations

import itertools
import unicodedata
from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "AccountingMinimalUniqueAnchorResolutionV1Error",
    "AnchorCandidateDispositionV1",
    "build_accounting_minimal_unique_anchor_resolution_v1",
    "validate_accounting_minimal_unique_anchor_resolution_replay_v1",
]


FORMAT_VERSION = "ACCOUNTING_MINIMAL_UNIQUE_ANCHOR_RESOLUTION_V1"
CLAIM_BOUNDARY = (
    "CALLER_BOUNDED_COMPLETE_AND_NEAR_TOPOLOGY_PAIR_BEFORE_TRIPLE_"
    "UNIQUENESS_DIAGNOSTIC_ONLY_NO_TEXT_NUMERIC_MAPPING_RETRIEVAL_OR_AUTHORITY"
)


class AnchorCandidateDispositionV1(StrEnum):
    """Whether a candidate passed the caller's independent completeness gates."""

    COMPLETE = "COMPLETE"
    NEAR = "NEAR"


class AccountingMinimalUniqueAnchorResolutionV1Error(ValueError):
    """The candidate scope, result identity, or exact replay drifted."""


def _error(message: str) -> AccountingMinimalUniqueAnchorResolutionV1Error:
    return AccountingMinimalUniqueAnchorResolutionV1Error(message)


def _nfc(value: Any, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise _error(f"{label} must be one nonempty exact string")
    if value != unicodedata.normalize("NFC", value):
        raise _error(f"{label} must already be NFC-normalized")
    return value


def _candidates(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise _error("minimal-anchor candidates must be one non-string sequence")
    parsed = []
    seen_ids: set[str] = set()
    for raw in value:
        if type(raw) is not dict or set(raw) != {
            "candidate_id",
            "child_anchor_ids",
            "disposition",
            "parent_anchor_id",
        }:
            raise _error("minimal-anchor candidate fields drifted")
        candidate_id = _nfc(raw["candidate_id"], "candidate ID")
        if candidate_id in seen_ids:
            raise _error("minimal-anchor candidate ID repeats")
        seen_ids.add(candidate_id)
        try:
            disposition = AnchorCandidateDispositionV1(raw["disposition"]).value
        except (TypeError, ValueError) as error:
            raise _error("minimal-anchor candidate disposition drifted") from error
        parent = raw["parent_anchor_id"]
        if parent is not None:
            parent = _nfc(parent, "parent anchor ID")
        children = raw["child_anchor_ids"]
        if type(children) is not list:
            raise _error("minimal-anchor child IDs must be one list")
        normalized_children = [_nfc(item, "child anchor ID") for item in children]
        if len(normalized_children) != len(set(normalized_children)):
            raise _error("minimal-anchor child ID repeats inside one candidate")
        if parent is not None and parent in normalized_children:
            raise _error("minimal-anchor parent cannot repeat as one child")
        if parent is None and not normalized_children:
            raise _error("minimal-anchor candidate has no topology anchor")
        parsed.append(
            {
                "candidate_id": candidate_id,
                "child_anchor_ids": sorted(normalized_children),
                "disposition": disposition,
                "parent_anchor_id": parent,
            }
        )
    if not parsed:
        raise _error("minimal-anchor resolution requires at least one candidate")
    return sorted(parsed, key=lambda item: item["candidate_id"])


def _candidate_combinations(candidate: Mapping[str, Any]) -> list[tuple[str, ...]]:
    parent = candidate["parent_anchor_id"]
    children = candidate["child_anchor_ids"]
    pairs = []
    if parent is not None:
        pairs.extend((parent, child) for child in children)
    pairs.extend(itertools.combinations(children, 2))
    triples = []
    if parent is not None:
        triples.extend(
            (parent, *children_pair) for children_pair in itertools.combinations(children, 2)
        )
    triples.extend(itertools.combinations(children, 3))
    return [*pairs, *triples]


def _anchor_set(candidate: Mapping[str, Any]) -> set[str]:
    return {
        *candidate["child_anchor_ids"],
        *([candidate["parent_anchor_id"]] if candidate["parent_anchor_id"] is not None else []),
    }


def _resolution(
    candidate: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    combinations = _candidate_combinations(candidate)
    scope = [(item["candidate_id"], _anchor_set(item)) for item in candidates]
    best_anchor_ids: tuple[str, ...] = ()
    best_matching_ids: list[str] | None = None
    selected: tuple[str, ...] | None = None
    selected_matching_ids: list[str] = []
    searched_pairs = 0
    searched_triples = 0
    for combination in combinations:
        if len(combination) == 2:
            searched_pairs += 1
        else:
            searched_triples += 1
        matching_ids = [
            candidate_id for candidate_id, anchors in scope if set(combination) <= anchors
        ]
        if best_matching_ids is None or len(matching_ids) < len(best_matching_ids):
            best_anchor_ids = combination
            best_matching_ids = matching_ids
        if len(matching_ids) == 1:
            selected = combination
            selected_matching_ids = matching_ids
            break
    if selected is not None:
        matching_ids = selected_matching_ids
        status = "UNIQUE_MINIMAL_ANCHOR_COMBINATION"
    elif not combinations:
        candidate_anchors = _anchor_set(candidate)
        matching_ids = [
            candidate_id for candidate_id, anchors in scope if candidate_anchors <= anchors
        ]
        status = "UNRESOLVED_INSUFFICIENT_TWO_ANCHOR_COMBINATION"
    else:
        assert best_matching_ids is not None
        matching_ids = best_matching_ids
        status = "UNRESOLVED_NO_UNIQUE_PAIR_OR_TRIPLE_COMBINATION"
    return {
        "best_nonunique_anchor_ids": list(best_anchor_ids) if selected is None else [],
        "candidate_anchor_ids": sorted(_anchor_set(candidate)),
        "matching_candidate_ids": matching_ids,
        "matching_count": len(matching_ids),
        "parent_child_pairs_precede_child_child_pairs": True,
        "pair_combinations_exhausted_before_triples": True,
        "searched_pair_count": searched_pairs,
        "searched_triple_count": searched_triples,
        "selected_anchor_ids": list(selected or ()),
        "selected_size": len(selected) if selected is not None else None,
        "status": status,
    }


def _build(value: Any, document_scope_id: Any) -> dict[str, Any]:
    candidates = _candidates(value)
    scope_id = _nfc(document_scope_id, "document scope ID")
    resolved = [
        {**candidate, "resolution": _resolution(candidate, candidates)} for candidate in candidates
    ]
    material = {
        "candidate_ids": [item["candidate_id"] for item in candidates],
        "candidates": resolved,
        "claim_boundary": CLAIM_BOUNDARY,
        "document_scope_id": scope_id,
        "format_version": FORMAT_VERSION,
        "metrics": {
            "candidate_count": len(candidates),
            "complete_candidate_count": sum(
                item["disposition"] == AnchorCandidateDispositionV1.COMPLETE.value
                for item in candidates
            ),
            "near_candidate_count": sum(
                item["disposition"] == AnchorCandidateDispositionV1.NEAR.value
                for item in candidates
            ),
            "unique_complete_candidate_count": sum(
                item["disposition"] == AnchorCandidateDispositionV1.COMPLETE.value
                and resolved_item["resolution"]["status"] == "UNIQUE_MINIMAL_ANCHOR_COMBINATION"
                for item, resolved_item in zip(candidates, resolved, strict=True)
            ),
        },
        "safety": {
            "authentication_or_retrieval_authority": False,
            "complete_and_near_candidates_share_comparison_scope": True,
            "numeric_or_text_matching_authority": False,
            "parent_child_pairs_precede_child_child_pairs": True,
            "pair_combinations_exhausted_before_triples": True,
            "schema_mapping_authority": False,
        },
        "status": "MINIMAL_UNIQUE_ANCHOR_RESOLUTION_PROPOSAL_ONLY",
    }
    return {**material, "result_id": "amuarv1:result:" + canonical_json_sha256_v1(material)}


def build_accounting_minimal_unique_anchor_resolution_v1(
    candidates: Sequence[Mapping[str, Any]], *, document_scope_id: str
) -> dict[str, Any]:
    """Resolve minimal unique pair/triple anchors in one caller-bound scope."""

    return _build(candidates, document_scope_id)


def validate_accounting_minimal_unique_anchor_resolution_replay_v1(
    value: Any,
    candidates: Sequence[Mapping[str, Any]],
    *,
    document_scope_id: str,
) -> dict[str, Any]:
    """Rebuild the complete candidate comparison and every identity exactly."""

    if type(value) is not dict or value.get("format_version") != FORMAT_VERSION:
        raise _error("minimal-anchor result identity drifted")
    material = canonical_clone_v1(value)
    result_id = material.pop("result_id", None)
    if result_id != "amuarv1:result:" + canonical_json_sha256_v1(material):
        raise _error("minimal-anchor result content identity drifted")
    rebuilt = _build(candidates, document_scope_id)
    if not same_typed_json_v1(value, rebuilt):
        raise _error("minimal-anchor result does not replay exactly")
    return rebuilt
