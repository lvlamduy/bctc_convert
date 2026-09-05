"""Exact, stable source-reference identity normalization.

This helper deliberately knows nothing about family roles, numeric values, or
mapping seals.  It removes only byte-identical canonical JSON references and
keeps the first occurrence of every distinct physical source identity.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    SourceStructureContractError,
    canonical_json_bytes_v1,
    decode_canonical_json_bytes_v1,
)

__all__ = [
    "SourceReferenceIdentityV1Error",
    "stable_unique_source_refs_v1",
]


class SourceReferenceIdentityV1Error(ValueError):
    """Raised when a source-reference axis is not canonical JSON objects."""


def stable_unique_source_refs_v1(
    source_refs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Return cloned first occurrences keyed by exact canonical JSON bytes."""

    if not isinstance(source_refs, Sequence) or isinstance(source_refs, (str, bytes, bytearray)):
        raise SourceReferenceIdentityV1Error("source refs must be a sequence")
    seen: set[bytes] = set()
    unique: list[dict[str, Any]] = []
    for index, source_ref in enumerate(source_refs):
        if type(source_ref) is not dict:
            raise SourceReferenceIdentityV1Error(f"source ref {index} must be an exact JSON object")
        try:
            identity = canonical_json_bytes_v1(source_ref)
        except SourceStructureContractError as exc:
            raise SourceReferenceIdentityV1Error(
                f"source ref {index} is not canonical JSON"
            ) from exc
        if identity in seen:
            continue
        seen.add(identity)
        clone = decode_canonical_json_bytes_v1(identity)
        if type(clone) is not dict:  # Defensive: canonical input above is an object.
            raise SourceReferenceIdentityV1Error(f"source ref {index} did not decode to an object")
        unique.append(clone)
    return unique
