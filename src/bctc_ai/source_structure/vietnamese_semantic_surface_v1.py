"""Candidate-only Vietnamese semantic surfaces for local accounting families.

The contract preserves the OCR transcript as NFC UTF-8 text.  It offers exact
Vietnamese-surface candidates and an accentless comparison-key shortlist, but
neither output is accounting identity or structural acceptance authority.
There is deliberately no spelling repair, fuzzy edit matching, or accent
restoration in this layer.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from bctc_ai.source_structure.local_accounting_graph_v1 import (
    FamilySpecV1,
    local_accounting_family_spec_sha256_v1,
    parse_local_accounting_period_v1,
    parse_local_accounting_unit_v1,
)

__all__ = [
    "CompiledVietnameseFamilyAliasIndexV1",
    "VietnameseAliasCandidateV1",
    "VietnameseAliasCollisionV1",
    "VietnameseSemanticSurfaceContractError",
    "VietnameseSemanticSurfaceProposalV1",
    "compile_vietnamese_family_alias_index_v1",
    "propose_vietnamese_semantic_surface_v1",
]


class VietnameseSemanticSurfaceContractError(ValueError):
    """The closed candidate-only Vietnamese surface contract was crossed."""


MatchKindV1 = Literal["EXACT_VIETNAMESE_SURFACE", "ACCENTLESS_ALIAS_ONLY"]


@dataclass(frozen=True)
class VietnameseAliasCandidateV1:
    family_id: str
    family_spec_sha256: str
    family_spec_json_pointer: str
    role_kind: str
    role: str
    alias_text_nfc: str
    normalized_vietnamese_surface: str
    accentless_comparison_key: str
    observed_comparison_key: str
    presentation_normalization: str
    match_kind: MatchKindV1
    semantic_identity_authority: bool = False
    structure_acceptance_authority: bool = False


@dataclass(frozen=True)
class VietnameseAliasCollisionV1:
    comparison_scope: str
    accentless_comparison_key: str
    candidates: tuple[VietnameseAliasCandidateV1, ...]


@dataclass(frozen=True, init=False)
class CompiledVietnameseFamilyAliasIndexV1:
    family_spec_sha256_by_id: MappingProxyType
    alias_count: int
    exact_vietnamese_surface_index: MappingProxyType
    accentless_comparison_key_index: MappingProxyType
    child_row_presentation_key_index: MappingProxyType
    collision_count: int
    collisions: tuple[VietnameseAliasCollisionV1, ...]
    accentless_key_shortlist_only: bool = True
    semantic_identity_authority: bool = False
    structure_acceptance_authority: bool = False
    automatic_correction_enabled: bool = False
    fuzzy_edit_matching_enabled: bool = False

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise VietnameseSemanticSurfaceContractError(
            "alias indexes must be created by the V1 compiler"
        )


@dataclass(frozen=True)
class VietnameseSemanticSurfaceProposalV1:
    raw_transcript_nfc: str
    normalized_vietnamese_surface: str
    accentless_comparison_key: str
    comparison_keys_consulted: tuple[str, ...]
    presentation_prefix_removed: bool
    status: str
    protected_context_kind: str | None
    candidates: tuple[VietnameseAliasCandidateV1, ...]
    collision_set: tuple[VietnameseAliasCandidateV1, ...]
    accentless_key_shortlist_only: bool
    semantic_identity_authority: bool
    structure_acceptance_authority: bool
    independent_local_topology_required: bool
    automatic_correction_applied: bool
    fuzzy_edit_matching_used: bool


@dataclass(frozen=True)
class _AliasClaimV1:
    family_id: str
    family_spec_sha256: str
    family_spec_json_pointer: str
    role_kind: str
    role: str
    alias_text_nfc: str
    normalized_vietnamese_surface: str
    accentless_comparison_key: str


_WHITESPACE_RE = re.compile(r"\s+")
_SURFACE_PUNCTUATION_RE = re.compile(r"(?:[^\w%]|_)+", re.UNICODE)
_ACCENTLESS_PUNCTUATION_RE = re.compile(r"[^a-z0-9%]+")
_PRESENTATION_PREFIX_RE = re.compile(
    r"^(?:(?:\(?\d{1,3}(?:\.\d{1,3})*\)?(?:[.)]|\s*-)?|"
    r"[ivxlcdm]+[.)]|[a-z][.)])\s+)+",
    re.IGNORECASE,
)
_DATE_RE = re.compile(r"(?<!\d)\d{1,2}[./-]\d{1,2}[./-]\d{4}(?!\d)")
_YEAR_RE = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
_NUMERIC_RE = re.compile(r"[-+]?\(?\s*\d[\d.,\s\u00a0\u202f]*\s*%?\s*\)?")


def _nfc(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value)
    try:
        normalized.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise VietnameseSemanticSurfaceContractError(
            "Vietnamese semantic surfaces must be valid UTF-8 text"
        ) from exc
    return normalized


def _surface(value: str) -> str:
    normalized = _nfc(value).casefold()
    normalized = _SURFACE_PUNCTUATION_RE.sub(" ", normalized)
    return _WHITESPACE_RE.sub(" ", normalized).strip(" _")


def _presentation_surface(value: str) -> tuple[str, bool]:
    normalized = _nfc(value).casefold().strip()
    body = _PRESENTATION_PREFIX_RE.sub("", normalized)
    return _surface(body), body != normalized


def _accentless_key(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", _nfc(value).casefold())
    without_marks = "".join(
        character for character in decomposed if unicodedata.category(character) != "Mn"
    )
    without_marks = without_marks.replace("đ", "d")
    normalized = _ACCENTLESS_PUNCTUATION_RE.sub(" ", without_marks)
    return _WHITESPACE_RE.sub(" ", normalized).strip()


def _candidate(
    claim: _AliasClaimV1,
    match_kind: MatchKindV1,
    *,
    observed_comparison_key: str | None = None,
    presentation_normalization: str = "NONE",
) -> VietnameseAliasCandidateV1:
    return VietnameseAliasCandidateV1(
        family_id=claim.family_id,
        family_spec_sha256=claim.family_spec_sha256,
        family_spec_json_pointer=claim.family_spec_json_pointer,
        role_kind=claim.role_kind,
        role=claim.role,
        alias_text_nfc=claim.alias_text_nfc,
        normalized_vietnamese_surface=claim.normalized_vietnamese_surface,
        accentless_comparison_key=claim.accentless_comparison_key,
        observed_comparison_key=(
            claim.accentless_comparison_key
            if observed_comparison_key is None
            else observed_comparison_key
        ),
        presentation_normalization=presentation_normalization,
        match_kind=match_kind,
    )


def _claim_sort_key(claim: _AliasClaimV1) -> tuple[str, ...]:
    return (
        claim.family_id,
        claim.role_kind,
        claim.role,
        claim.normalized_vietnamese_surface,
        claim.family_spec_json_pointer,
    )


def _candidate_sort_key(candidate: VietnameseAliasCandidateV1) -> tuple[str, ...]:
    return (
        candidate.family_id,
        candidate.role_kind,
        candidate.role,
        candidate.normalized_vietnamese_surface,
        candidate.family_spec_json_pointer,
    )


def _without_leading_debt_row_token(key: str) -> tuple[str, bool]:
    tokens = key.split()
    if len(tokens) > 1 and tokens[0] == "no":
        return " ".join(tokens[1:]), True
    return key, False


def _family_alias_claims(spec: FamilySpecV1, digest: str) -> list[_AliasClaimV1]:
    axes: list[tuple[str, str, Sequence[str], str]] = [
        ("OWNER", "OWNER", spec.owner_aliases, "/owner_aliases"),
        ("BRANCH", "BRANCH", spec.branch_aliases, "/branch_aliases"),
    ]
    axes.extend(
        ("ORDERED_CHILD", child.role, child.aliases, f"/ordered_children/{index}/aliases")
        for index, child in enumerate(spec.ordered_children)
    )
    axes.extend(
        ("OPTIONAL_CHILD", child.role, child.aliases, f"/optional_children/{index}/aliases")
        for index, child in enumerate(spec.optional_children)
    )
    axes.append(("TOTAL", "TOTAL", spec.total_aliases, "/total_aliases"))
    claims = []
    for role_kind, role, aliases, pointer in axes:
        for alias_index, alias in enumerate(aliases):
            alias_nfc = _nfc(alias)
            surface = _surface(alias_nfc)
            key = _accentless_key(surface)
            if not surface or not key:
                raise VietnameseSemanticSurfaceContractError(
                    "family aliases must have non-empty Vietnamese surfaces and comparison keys"
                )
            claims.append(
                _AliasClaimV1(
                    family_id=spec.family_id,
                    family_spec_sha256=digest,
                    family_spec_json_pointer=f"{pointer}/{alias_index}",
                    role_kind=role_kind,
                    role=role,
                    alias_text_nfc=alias_nfc,
                    normalized_vietnamese_surface=surface,
                    accentless_comparison_key=key,
                )
            )
    return claims


def compile_vietnamese_family_alias_index_v1(
    family_specs: Sequence[FamilySpecV1],
) -> CompiledVietnameseFamilyAliasIndexV1:
    """Compile all family aliases into exact and accentless read-only indexes."""

    if isinstance(family_specs, (str, bytes, bytearray)) or not isinstance(family_specs, Sequence):
        raise VietnameseSemanticSurfaceContractError(
            "family specs must be an ordered sequence of FamilySpecV1 values"
        )
    if not family_specs:
        raise VietnameseSemanticSurfaceContractError("at least one FamilySpecV1 is required")
    seen_families: set[str] = set()
    claims: list[_AliasClaimV1] = []
    digests: dict[str, str] = {}
    for spec in family_specs:
        if type(spec) is not FamilySpecV1:
            raise VietnameseSemanticSurfaceContractError(
                "family specs must contain only exact FamilySpecV1 values"
            )
        if spec.family_id in seen_families:
            raise VietnameseSemanticSurfaceContractError("family identities must be unique")
        seen_families.add(spec.family_id)
        try:
            digest = local_accounting_family_spec_sha256_v1(spec)
        except (TypeError, ValueError) as exc:
            raise VietnameseSemanticSurfaceContractError(
                "family spec failed the structural FamilySpecV1 contract"
            ) from exc
        digests[spec.family_id] = digest
        claims.extend(_family_alias_claims(spec, digest))

    exact: dict[str, list[_AliasClaimV1]] = defaultdict(list)
    accentless: dict[str, list[_AliasClaimV1]] = defaultdict(list)
    child_row_presentation: dict[str, list[_AliasClaimV1]] = defaultdict(list)
    unique_claims: dict[tuple[str, ...], _AliasClaimV1] = {}
    for claim in claims:
        identity = _claim_sort_key(claim)
        unique_claims[identity] = claim
    for claim in sorted(unique_claims.values(), key=_claim_sort_key):
        exact[claim.normalized_vietnamese_surface].append(claim)
        accentless[claim.accentless_comparison_key].append(claim)
        if claim.role_kind in {"ORDERED_CHILD", "OPTIONAL_CHILD"}:
            presentation_key, _removed = _without_leading_debt_row_token(
                claim.accentless_comparison_key
            )
            child_row_presentation[presentation_key].append(claim)

    exact_index = MappingProxyType({key: tuple(value) for key, value in sorted(exact.items())})
    accentless_index = MappingProxyType(
        {key: tuple(value) for key, value in sorted(accentless.items())}
    )
    child_row_presentation_index = MappingProxyType(
        {key: tuple(value) for key, value in sorted(child_row_presentation.items())}
    )
    collisions = tuple(
        sorted(
            (
                VietnameseAliasCollisionV1(
                    comparison_scope=scope,
                    accentless_comparison_key=key,
                    candidates=tuple(
                        _candidate(
                            claim,
                            "ACCENTLESS_ALIAS_ONLY",
                            observed_comparison_key=key,
                            presentation_normalization=(
                                "NONE"
                                if scope == "FULL_ACCENTLESS_KEY"
                                else "LEADING_DEBT_ROW_PRESENTATION_PREFIX"
                            ),
                        )
                        for claim in posting
                    ),
                )
                for scope, index in (
                    ("FULL_ACCENTLESS_KEY", accentless_index),
                    ("CHILD_ROW_PRESENTATION_KEY", child_row_presentation_index),
                )
                for key, posting in index.items()
                if len(posting) > 1
            ),
            key=lambda collision: (
                collision.comparison_scope,
                collision.accentless_comparison_key,
            ),
        )
    )
    compiled = object.__new__(CompiledVietnameseFamilyAliasIndexV1)
    fields = {
        "family_spec_sha256_by_id": MappingProxyType(dict(sorted(digests.items()))),
        "alias_count": len(unique_claims),
        "exact_vietnamese_surface_index": exact_index,
        "accentless_comparison_key_index": accentless_index,
        "child_row_presentation_key_index": child_row_presentation_index,
        "collision_count": len(collisions),
        "collisions": collisions,
        "accentless_key_shortlist_only": True,
        "semantic_identity_authority": False,
        "structure_acceptance_authority": False,
        "automatic_correction_enabled": False,
        "fuzzy_edit_matching_enabled": False,
    }
    for name, value in fields.items():
        object.__setattr__(compiled, name, value)
    return compiled


def _protected_context(raw_nfc: str, key: str) -> str | None:
    stripped = raw_nfc.strip()
    if (
        parse_local_accounting_period_v1(stripped) is not None
        or _DATE_RE.search(stripped)
        or (
            _YEAR_RE.search(stripped)
            and any(token in key.split() for token in ("nam", "quy", "thang", "ngay"))
        )
    ):
        return "PROTECTED_PERIOD_CONTEXT"
    if (
        parse_local_accounting_unit_v1(stripped) is not None
        or stripped == "%"
        or key in {"phan tram", "don vi phan tram", "dvt phan tram"}
        or re.fullmatch(
            r"(?:(?:don vi(?: tinh)?|dvt) )?(?:(?:nghin|ngan|trieu|ty) )?"
            r"(?:vnd|dong|dong viet nam)",
            key,
        )
        is not None
    ):
        return "PROTECTED_UNIT_CONTEXT"
    if stripped in {"-", "−", "–", "—"} or _NUMERIC_RE.fullmatch(stripped) is not None:
        return "PROTECTED_NUMERIC_CONTEXT"
    return None


def _comparison_keys(surface: str) -> tuple[tuple[str, str], ...]:
    full_key = _accentless_key(surface)
    keys = [(full_key, "NONE")]
    # Vietnamese bank schedules often present maturity buckets as "Nợ ngắn
    # hạn" while the declarative role alias is "ngắn hạn".  This is a closed
    # structural presentation prefix, not spelling correction: only the exact
    # first accentless token "no" is removed and the full key always wins if
    # it has any posting.
    child_key, removed = _without_leading_debt_row_token(full_key)
    if removed:
        keys.append((child_key, "LEADING_DEBT_ROW_PRESENTATION_PREFIX"))
    return tuple(keys)


def propose_vietnamese_semantic_surface_v1(
    raw_transcript: str,
    compiled_index: CompiledVietnameseFamilyAliasIndexV1,
) -> VietnameseSemanticSurfaceProposalV1:
    """Return exact candidates or an unresolved accentless shortlist."""

    if type(raw_transcript) is not str:
        raise VietnameseSemanticSurfaceContractError(
            "raw Transformer transcript must be one exact string without metadata fields"
        )
    if type(compiled_index) is not CompiledVietnameseFamilyAliasIndexV1:
        raise VietnameseSemanticSurfaceContractError(
            "compiled index must be the exact V1 compiler result"
        )
    raw_nfc = _nfc(raw_transcript)
    surface, prefix_removed = _presentation_surface(raw_nfc)
    key = _accentless_key(surface)
    comparison_keys = _comparison_keys(surface)
    protected = _protected_context(raw_nfc, key)
    if protected is not None:
        return VietnameseSemanticSurfaceProposalV1(
            raw_transcript_nfc=raw_nfc,
            normalized_vietnamese_surface=surface,
            accentless_comparison_key=key,
            comparison_keys_consulted=tuple(item[0] for item in comparison_keys),
            presentation_prefix_removed=prefix_removed,
            status=protected,
            protected_context_kind=protected,
            candidates=(),
            collision_set=(),
            accentless_key_shortlist_only=True,
            semantic_identity_authority=False,
            structure_acceptance_authority=False,
            independent_local_topology_required=False,
            automatic_correction_applied=False,
            fuzzy_edit_matching_used=False,
        )

    posting: Sequence[_AliasClaimV1] = ()
    observed_comparison_key = key
    presentation_normalization = "NONE"
    posting = compiled_index.accentless_comparison_key_index.get(key, ())
    if not posting:
        child_key, observed_prefix_removed = _without_leading_debt_row_token(key)
        posting = compiled_index.child_row_presentation_key_index.get(child_key, ())
        if posting:
            observed_comparison_key = child_key
            presentation_normalization = "LEADING_DEBT_ROW_PRESENTATION_PREFIX"
            prefix_removed = (
                prefix_removed
                or observed_prefix_removed
                or any(claim.accentless_comparison_key != child_key for claim in posting)
            )
    exact_claims = set(compiled_index.exact_vietnamese_surface_index.get(surface, ()))
    candidates = tuple(
        sorted(
            (
                _candidate(
                    claim,
                    "EXACT_VIETNAMESE_SURFACE"
                    if claim in exact_claims
                    else "ACCENTLESS_ALIAS_ONLY",
                    observed_comparison_key=observed_comparison_key,
                    presentation_normalization=presentation_normalization,
                )
                for claim in posting
            ),
            key=_candidate_sort_key,
        )
    )
    if len(candidates) > 1:
        status = "UNRESOLVED_ALIAS_KEY_COLLISION"
        collision_set = candidates
    elif candidates and candidates[0].match_kind == "EXACT_VIETNAMESE_SURFACE":
        status = "EXACT_VIETNAMESE_SURFACE_CANDIDATE"
        collision_set = ()
    elif candidates:
        status = "UNRESOLVED_ACCENTLESS_ALIAS_CANDIDATE"
        collision_set = ()
    else:
        status = "NO_ALIAS_CANDIDATE"
        collision_set = ()
    return VietnameseSemanticSurfaceProposalV1(
        raw_transcript_nfc=raw_nfc,
        normalized_vietnamese_surface=surface,
        accentless_comparison_key=key,
        comparison_keys_consulted=tuple(item[0] for item in comparison_keys),
        presentation_prefix_removed=prefix_removed,
        status=status,
        protected_context_kind=None,
        candidates=candidates,
        collision_set=collision_set,
        accentless_key_shortlist_only=True,
        semantic_identity_authority=False,
        structure_acceptance_authority=False,
        independent_local_topology_required=bool(candidates),
        automatic_correction_applied=False,
        fuzzy_edit_matching_used=False,
    )
