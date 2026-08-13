"""Replay-authenticated semantic/topology proposals for Local Accounting Graph v1.

The adapter is deliberately candidate-only.  It scans the authenticated
primary LINE axis once, matches only declarative family vocabulary, and emits
complete line/topology dispositions.  It neither assembles a LAG observation
nor accepts accounting structure.  Validation rebuilds the complete artifact
from the exact V2 projection and exact inputs; embedded digests are receipts,
not authority.
"""

from __future__ import annotations

import re
import unicodedata
import weakref
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, NamedTuple

from bctc_ai.source_structure.contracts_v1 import (
    SourceStructureContractError,
    _normalized_financial_token_v1,
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    decode_canonical_json_bytes_v1,
    same_typed_json_v1,
)
from bctc_ai.source_structure.contracts_v2 import validate_source_evidence_projection_v2
from bctc_ai.source_structure.local_accounting_graph_v1 import (
    AxisLayoutSpecV1,
    FamilySpecV1,
    RowRoleSpecV1,
    local_accounting_family_spec_payload_v1,
    local_accounting_family_spec_sha256_v1,
    parse_local_accounting_period_v1,
    parse_local_accounting_unit_v1,
)

__all__ = [
    "DEFAULT_LOCAL_ACCOUNTING_TYPED_PROPOSAL_CONFIG_V1",
    "LOCAL_ACCOUNTING_TYPED_PROPOSAL_CLAIM_BOUNDARY_V1",
    "LOCAL_ACCOUNTING_TYPED_PROPOSAL_FORMAT_VERSION_V1",
    "LOCAL_ACCOUNTING_TYPED_PROPOSAL_GENERATOR_IDENTITY_V1",
    "LOCAL_ACCOUNTING_TYPED_PROPOSAL_SAFETY_V1",
    "CompiledLocalAccountingTypedProposalRegistryV1",
    "LocalAccountingTypedProposalConfigV1",
    "LocalAccountingTypedProposalContractError",
    "build_local_accounting_typed_proposal_set_v1",
    "build_local_accounting_typed_proposal_set_from_registry_v1",
    "compile_local_accounting_typed_proposal_registry_v1",
    "local_accounting_family_registry_payload_v1",
    "local_accounting_typed_proposal_config_payload_v1",
    "local_accounting_typed_proposal_config_sha256_v1",
    "validate_local_accounting_typed_proposal_set_v1",
    "validate_local_accounting_typed_proposal_set_from_registry_v1",
]


class LocalAccountingTypedProposalContractError(ValueError):
    """The candidate-only typed-proposal contract was crossed."""


LOCAL_ACCOUNTING_TYPED_PROPOSAL_FORMAT_VERSION_V1 = (
    "BANK_CORPUS_LOCAL_ACCOUNTING_TYPED_PROPOSAL_SET_V1"
)
LOCAL_ACCOUNTING_TYPED_PROPOSAL_CLAIM_BOUNDARY_V1 = (
    "SOURCE_BOUND_CANDIDATE_PROPOSALS_ONLY_NO_STRUCTURE_ACCEPTANCE_NO_LAG_"
    "OBSERVATION_ASSEMBLY_NO_SCHEMA_OR_ROLE_A_ROUTING"
)


def _generator_identity_payload() -> dict[str, Any]:
    return {
        "format_version": "LOCAL_ACCOUNTING_TYPED_PROPOSAL_GENERATOR_IDENTITY_V1",
        "revision": "SINGLE_PRIMARY_LINE_SCAN_COMPILED_VOCABULARY_ORDERED_EVENTS_V1",
        "source_axis": "AUTHENTICATED_PRIMARY_LINE_ONLY",
        "vocabulary_source": "EXACT_BOUND_FAMILY_SPEC_STRUCTURAL_ALIASES_ONLY",
        "family_shortlist_anchor": "BRANCH_ROLE_CANDIDATE",
        "topology_strategy": "ORDERED_EVENT_STATE_MACHINE_NO_CARTESIAN_PRODUCTS",
        "repair_strategy": "BOUNDED_EDIT_CANDIDATES_UNRESOLVED_ONLY",
        "forbidden_routing_inputs": [
            "bank_identity",
            "filename_identity",
            "physical_page_identity",
            "note_number",
            "role_a_reference",
            "schema_identity",
        ],
    }


def _safety_payload() -> dict[str, bool]:
    return {
        "candidate_proposals_only": True,
        "semantic_acceptance_claimed": False,
        "table_acceptance_claimed": False,
        "logical_row_acceptance_claimed": False,
        "axis_acceptance_claimed": False,
        "hierarchy_acceptance_claimed": False,
        "lag_observation_assembled": False,
        "lag_core_invoked": False,
        "schema_mapping_used": False,
        "role_a_used": False,
        "bank_filename_page_note_routing_used": False,
        "source_line_axis_scanned_once": True,
        "family_line_cartesian_product_used": False,
        "raw_source_text_mutated": False,
        "bounded_repair_used_for_acceptance": False,
        "numeric_period_unit_repair_attempted": False,
        "complete_eligible_line_dispositions": True,
        "complete_topology_candidate_dispositions": True,
        "topology_candidate_universe_exhaustiveness_claimed": False,
        "page_family_occurrence_exhaustiveness_claimed": False,
        "embedded_hashes_treated_as_authority": False,
        "deterministic_replay_validation_required": True,
    }


LOCAL_ACCOUNTING_TYPED_PROPOSAL_GENERATOR_IDENTITY_V1: Mapping[str, Any] = MappingProxyType(
    {
        **_generator_identity_payload(),
        "forbidden_routing_inputs": tuple(
            _generator_identity_payload()["forbidden_routing_inputs"]
        ),
    }
)
LOCAL_ACCOUNTING_TYPED_PROPOSAL_SAFETY_V1: Mapping[str, bool] = MappingProxyType(_safety_payload())


@dataclass(frozen=True)
class LocalAccountingTypedProposalConfigV1:
    """Generic bounds for candidate generation, never accounting identity."""

    maximum_edit_distance: int = 2
    minimum_repair_normalized_length: int = 7
    repair_ngram_size: int = 2
    retained_distance_band_count: int = 2
    maximum_owner_to_branch_line_gap: int = 40
    maximum_topology_candidate_line_span: int = 240
    maximum_exact_alias_candidate_fanout: int = 64
    maximum_fuzzy_alias_candidate_fanout: int = 64
    maximum_fuzzy_index_posting_visits_per_line: int = 4_096


_COMPILED_REGISTRY_CONSTRUCTION_TOKEN = object()


@dataclass(frozen=True, init=False)
class CompiledLocalAccountingTypedProposalRegistryV1:
    """Read-only handle for a compiler-owned reusable registry state.

    Page builders resolve the handle by object identity and use the separate
    compiler-owned state, never these inspectable receipt fields.  Copying or
    mutating a handle therefore cannot alter inference or replay authority.
    """

    family_specs: tuple[FamilySpecV1, ...]
    config: LocalAccountingTypedProposalConfigV1
    registry_payload_json: bytes
    registry_sha256: str
    bound_specs: tuple[tuple[FamilySpecV1, bytes, str], ...]
    alias_entries: tuple[_AliasEntry, ...]
    exact_index: Mapping[str, tuple[_AliasEntry, ...]]
    ngram_index: Mapping[str, tuple[_AliasEntry, ...]]
    _construction_token: object

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise LocalAccountingTypedProposalContractError(
            "compiled registries must be created by the versioned compiler"
        )


DEFAULT_LOCAL_ACCOUNTING_TYPED_PROPOSAL_CONFIG_V1 = LocalAccountingTypedProposalConfigV1()


class _AliasEntry(NamedTuple):
    entry_id: str
    family_id: str
    family_spec_sha256: str
    role_kind: str
    role: str
    alias_text: str
    normalized_alias: str


@dataclass(frozen=True)
class _CompiledRegistryStateV1:
    family_specs: tuple[FamilySpecV1, ...]
    config: LocalAccountingTypedProposalConfigV1
    bound_specs: tuple[tuple[FamilySpecV1, dict[str, Any], str], ...]
    spec_by_id: Mapping[str, tuple[FamilySpecV1, str]]
    alias_entries: tuple[_AliasEntry, ...]
    exact_index: Mapping[str, tuple[_AliasEntry, ...]]
    exact_family_index: Mapping[tuple[str, str], tuple[_AliasEntry, ...]]
    qgram_postings: Mapping[str, tuple[_AliasEntry, ...]]
    alias_qgram_counts: Mapping[str, tuple[tuple[str, int], ...]]
    registry_sha256: str
    registry_payload_sha256: str
    family_spec_binding_json: bytes
    config_payload_json: bytes
    config_sha256: str
    compiled_alias_axis_sha256: str


_COMPILED_REGISTRY_STATE_BY_HANDLE_ID: dict[
    int,
    tuple[
        weakref.ReferenceType[CompiledLocalAccountingTypedProposalRegistryV1],
        _CompiledRegistryStateV1,
    ],
] = {}


_ROLE_KIND_ORDER = {
    "OWNER": 0,
    "BRANCH": 1,
    "ORDERED_CHILD": 2,
    "OPTIONAL_CHILD": 3,
    "TOTAL": 4,
}
_PROPOSAL_PREFIX = "sslatpv1:semantic:"
_TOPOLOGY_PREFIX = "sslatpv1:topology:"
_SET_PREFIX = "sslatpv1:set:"
_NUMBERED_PRESENTATION_PREFIX_RE = re.compile(r"^(?:(?:[0-9]+|[ivxlcdm]+)\s+)+")


def _error(message: str) -> LocalAccountingTypedProposalContractError:
    return LocalAccountingTypedProposalContractError(message)


def _normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold().replace("đ", "d"))
    ascii_like = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9%]+", " ", ascii_like).split())


def _presentation_body(normalized: str) -> str:
    return _NUMBERED_PRESENTATION_PREFIX_RE.sub("", normalized)


def _validate_config(
    config: LocalAccountingTypedProposalConfigV1,
) -> LocalAccountingTypedProposalConfigV1:
    if type(config) is not LocalAccountingTypedProposalConfigV1:
        raise _error("generator config must be the exact V1 dataclass")
    integer_fields = (
        config.maximum_edit_distance,
        config.minimum_repair_normalized_length,
        config.repair_ngram_size,
        config.retained_distance_band_count,
        config.maximum_owner_to_branch_line_gap,
        config.maximum_topology_candidate_line_span,
        config.maximum_exact_alias_candidate_fanout,
        config.maximum_fuzzy_alias_candidate_fanout,
        config.maximum_fuzzy_index_posting_visits_per_line,
    )
    if any(type(item) is not int for item in integer_fields):
        raise _error("generator config fields must be plain integers")
    if not 0 <= config.maximum_edit_distance <= 3:
        raise _error("maximum edit distance is outside the bounded V1 range")
    if config.minimum_repair_normalized_length < 5:
        raise _error("minimum repair length is unsafe")
    if not 2 <= config.repair_ngram_size <= 4:
        raise _error("repair ngram size is outside the bounded V1 range")
    if config.retained_distance_band_count != 2:
        raise _error("V1 must retain both best and runner-up distance bands")
    if config.maximum_owner_to_branch_line_gap <= 0:
        raise _error("owner-to-branch gap must be positive")
    if config.maximum_topology_candidate_line_span < config.maximum_owner_to_branch_line_gap:
        raise _error("topology span cannot be smaller than owner-to-branch gap")
    if not 8 <= config.maximum_exact_alias_candidate_fanout <= 512:
        raise _error("exact alias candidate fanout bound is outside the V1 range")
    if not 8 <= config.maximum_fuzzy_alias_candidate_fanout <= 512:
        raise _error("fuzzy alias candidate fanout bound is outside the V1 range")
    if not 64 <= config.maximum_fuzzy_index_posting_visits_per_line <= 100_000:
        raise _error("fuzzy index posting-visit bound is outside the V1 range")
    if (
        config.minimum_repair_normalized_length - config.repair_ngram_size + 1
        <= config.repair_ngram_size * config.maximum_edit_distance
    ):
        raise _error("repair bounds cannot guarantee a shared q-gram")
    return config


def local_accounting_typed_proposal_config_payload_v1(
    config: LocalAccountingTypedProposalConfigV1,
) -> dict[str, Any]:
    """Return the canonical generic generator-config payload."""

    config = _validate_config(config)
    return {
        "format_version": "LOCAL_ACCOUNTING_TYPED_PROPOSAL_CONFIG_V1",
        "maximum_edit_distance": config.maximum_edit_distance,
        "minimum_repair_normalized_length": config.minimum_repair_normalized_length,
        "repair_ngram_size": config.repair_ngram_size,
        "retained_distance_band_count": config.retained_distance_band_count,
        "maximum_owner_to_branch_line_gap": config.maximum_owner_to_branch_line_gap,
        "maximum_topology_candidate_line_span": (config.maximum_topology_candidate_line_span),
        "maximum_exact_alias_candidate_fanout": (config.maximum_exact_alias_candidate_fanout),
        "maximum_fuzzy_alias_candidate_fanout": (config.maximum_fuzzy_alias_candidate_fanout),
        "maximum_fuzzy_index_posting_visits_per_line": (
            config.maximum_fuzzy_index_posting_visits_per_line
        ),
    }


def local_accounting_typed_proposal_config_sha256_v1(
    config: LocalAccountingTypedProposalConfigV1,
) -> str:
    """Return the canonical identity of the complete generic config."""

    return canonical_json_sha256_v1(local_accounting_typed_proposal_config_payload_v1(config))


def _config_from_payload(payload: Mapping[str, Any]) -> LocalAccountingTypedProposalConfigV1:
    return LocalAccountingTypedProposalConfigV1(
        maximum_edit_distance=payload["maximum_edit_distance"],
        minimum_repair_normalized_length=payload["minimum_repair_normalized_length"],
        repair_ngram_size=payload["repair_ngram_size"],
        retained_distance_band_count=payload["retained_distance_band_count"],
        maximum_owner_to_branch_line_gap=payload["maximum_owner_to_branch_line_gap"],
        maximum_topology_candidate_line_span=payload["maximum_topology_candidate_line_span"],
        maximum_exact_alias_candidate_fanout=payload["maximum_exact_alias_candidate_fanout"],
        maximum_fuzzy_alias_candidate_fanout=payload["maximum_fuzzy_alias_candidate_fanout"],
        maximum_fuzzy_index_posting_visits_per_line=payload[
            "maximum_fuzzy_index_posting_visits_per_line"
        ],
    )


def _bound_specs(specs: Sequence[FamilySpecV1]) -> list[tuple[FamilySpecV1, dict, str]]:
    if isinstance(specs, (str, bytes, bytearray)) or not isinstance(specs, Sequence):
        raise _error("family specs must be an ordered sequence")
    bound: list[tuple[FamilySpecV1, dict, str]] = []
    seen: set[str] = set()
    for spec in specs:
        if type(spec) is not FamilySpecV1:
            raise _error("family spec sequence contains a foreign type")
        try:
            payload = local_accounting_family_spec_payload_v1(spec)
            digest = local_accounting_family_spec_sha256_v1(spec)
        except (TypeError, ValueError) as error:
            raise _error("family spec failed the exact LAG registry contract") from error
        if spec.family_id in seen:
            raise _error("family spec identities must be unique")
        seen.add(spec.family_id)
        bound.append((spec, payload, digest))
    if not bound:
        raise _error("at least one exact family spec is required")
    return sorted(bound, key=lambda item: item[0].family_id)


def _family_spec_from_payload(payload: Mapping[str, Any]) -> FamilySpecV1:
    """Rebuild an internal immutable spec; never retain caller-owned objects."""

    return FamilySpecV1(
        family_id=payload["family_id"],
        owner_aliases=tuple(payload["owner_aliases"]),
        branch_aliases=tuple(payload["branch_aliases"]),
        ordered_children=tuple(
            RowRoleSpecV1(item["role"], tuple(item["aliases"]))
            for item in payload["ordered_children"]
        ),
        optional_children=tuple(
            RowRoleSpecV1(item["role"], tuple(item["aliases"]))
            for item in payload["optional_children"]
        ),
        total_aliases=tuple(payload["total_aliases"]),
        closure_child_roles=tuple(payload["closure_child_roles"]),
        axis_layout=AxisLayoutSpecV1(
            comparative_monetary_period_count=payload["axis_layout"][
                "comparative_monetary_period_count"
            ]
        ),
    )


def local_accounting_family_registry_payload_v1(
    specs: Sequence[FamilySpecV1],
) -> dict[str, Any]:
    """Build a versioned registry payload and cross-family collision receipt."""

    bound = _bound_specs(specs)
    alias_claims: dict[str, list[dict[str, str]]] = defaultdict(list)
    for spec, payload, digest in bound:
        for entry in _alias_entries(((spec, payload, digest),)):
            alias_claims[entry.normalized_alias].append(
                {
                    "family_id": entry.family_id,
                    "family_spec_sha256": entry.family_spec_sha256,
                    "role_kind": entry.role_kind,
                    "role": entry.role,
                }
            )
    collisions = [
        {
            "normalized_alias": alias,
            "claims": sorted(
                claims,
                key=lambda claim: (claim["family_id"], claim["role_kind"], claim["role"]),
            ),
        }
        for alias, claims in sorted(alias_claims.items())
        if len(claims) > 1
    ]
    return {
        "format_version": "LOCAL_ACCOUNTING_FAMILY_REGISTRY_V1",
        "family_specs": [payload for _spec, payload, _digest in bound],
        "collision_receipt": {
            "format_version": "LOCAL_ACCOUNTING_FAMILY_ALIAS_COLLISION_RECEIPT_V1",
            "collision_count": len(collisions),
            "collisions": collisions,
        },
    }


def _alias_entries(
    bound_specs: Sequence[tuple[FamilySpecV1, dict, str]],
) -> list[_AliasEntry]:
    entries: list[_AliasEntry] = []
    seen: set[tuple[str, str, str, str]] = set()
    for spec, _payload, spec_sha in bound_specs:
        axes: list[tuple[str, str, Sequence[str]]] = [
            ("OWNER", "OWNER", spec.owner_aliases),
            ("BRANCH", "BRANCH", spec.branch_aliases),
        ]
        axes.extend(("ORDERED_CHILD", item.role, item.aliases) for item in spec.ordered_children)
        axes.extend(("OPTIONAL_CHILD", item.role, item.aliases) for item in spec.optional_children)
        axes.append(("TOTAL", "TOTAL", spec.total_aliases))
        for role_kind, role, aliases in axes:
            for alias_text in aliases:
                normalized = _normalize_text(alias_text)
                key = (spec.family_id, role_kind, role, normalized)
                if not normalized or key in seen:
                    continue
                seen.add(key)
                identity = {
                    "family_id": spec.family_id,
                    "family_spec_sha256": spec_sha,
                    "role_kind": role_kind,
                    "role": role,
                    "normalized_alias": normalized,
                }
                entries.append(
                    _AliasEntry(
                        entry_id=("sslatpv1:alias:" + canonical_json_sha256_v1(identity)),
                        family_id=spec.family_id,
                        family_spec_sha256=spec_sha,
                        role_kind=role_kind,
                        role=role,
                        alias_text=alias_text,
                        normalized_alias=normalized,
                    )
                )
    return sorted(
        entries,
        key=lambda item: (
            item.normalized_alias,
            item.family_id,
            _ROLE_KIND_ORDER[item.role_kind],
            item.role,
            item.alias_text,
        ),
    )


def _ngrams(text: str, size: int) -> set[str]:
    compact = text.replace(" ", "")
    if len(compact) < size:
        return {compact} if compact else set()
    return {compact[index : index + size] for index in range(len(compact) - size + 1)}


def _ngram_counter(text: str, size: int) -> Counter[str]:
    compact = text.replace(" ", "")
    if len(compact) < size:
        return Counter({compact: 1}) if compact else Counter()
    return Counter(compact[index : index + size] for index in range(len(compact) - size + 1))


def _qgram_edit_lower_bound_allows(
    left_counts: Counter[str],
    right_counts: Mapping[str, int],
    *,
    size: int,
    maximum_edits: int,
) -> bool:
    """Safe q-gram necessary condition before bounded Levenshtein work."""
    distance = sum(
        abs(left_counts[gram] - right_counts.get(gram, 0))
        for gram in left_counts.keys() | right_counts.keys()
    )
    return distance <= 2 * size * maximum_edits


def _bounded_edit_distance(left: str, right: str, maximum: int) -> int | None:
    """Exact Levenshtein distance with a small fail-fast bound."""

    if abs(len(left) - len(right)) > maximum:
        return None
    previous = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current = [left_index]
        row_minimum = current[0]
        for right_index, right_char in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_char != right_char),
                )
            )
            row_minimum = min(row_minimum, current[-1])
        if row_minimum > maximum:
            return None
        previous = current
    distance = previous[-1]
    return distance if distance <= maximum else None


def _is_numeric(text: str) -> bool:
    try:
        _normalized_financial_token_v1(text)
    except (SourceStructureContractError, TypeError, ValueError):
        # Locale-ambiguous punctuation still makes this a numeric-looking
        # protected token.  It must stay unresolved, never enter OCR semantic
        # repair against accounting labels.
        token = text.strip()
        if token.startswith("(") and token.endswith(")"):
            token = token[1:-1].strip()
        if token.startswith(("+", "-")):
            token = token[1:]
        return bool(token) and re.fullmatch(r"[0-9., \u00a0\u202f]+", token) is not None
    return True


def _protected_value_context(text: str) -> str | None:
    stripped = text.strip()
    normalized = _normalize_text(text)
    if stripped in {"-", "−", "–", "—"}:
        return "PROTECTED_DASH_VALUE_CONTEXT"
    if normalized in {"na", "n a", "khong ap dung"}:
        return "PROTECTED_NOT_APPLICABLE_VALUE_CONTEXT"
    if re.fullmatch(
        r"[-+]?\(?\s*\d[\d.,\s\u00a0\u202f]*\s*%\s*\)?",
        stripped,
    ):
        return "PROTECTED_PERCENTAGE_VALUE_CONTEXT"
    if re.fullmatch(r"(?:(?:don vi(?: tinh)?|dvt) )?(?:%|phan tram)", normalized):
        return "PROTECTED_PERCENTAGE_UNIT_CONTEXT"
    return None


def _raw_span(atom: Mapping[str, Any], ordinal: int) -> dict[str, Any]:
    return {
        "source_atom_id": atom["source_local_id"],
        "source_ordinal": ordinal,
        "raw_text": atom["raw_text"],
        "canonical_bbox_mpt": canonical_clone_v1(atom["canonical_bbox_mpt"]),
    }


def _match_payload(
    entry: _AliasEntry,
    *,
    match_kind: str,
    edit_distance: int,
    matched_surface: str,
) -> dict[str, Any]:
    return {
        "alias_entry_id": entry.entry_id,
        "family_id": entry.family_id,
        "family_spec_sha256": entry.family_spec_sha256,
        "role_kind": entry.role_kind,
        "role": entry.role,
        "alias_text": entry.alias_text,
        "normalized_alias": entry.normalized_alias,
        "match_kind": match_kind,
        "edit_distance": edit_distance,
        "matched_surface": matched_surface,
    }


def _semantic_proposal(
    *,
    atom: Mapping[str, Any],
    ordinal: int,
    matches: list[dict[str, Any]],
) -> dict[str, Any]:
    exact = [item for item in matches if item["match_kind"] == "EXACT_ALIAS"]
    best_distance = min(item["edit_distance"] for item in matches)
    best = [item for item in matches if item["edit_distance"] == best_distance]
    if exact:
        status = (
            "UNIQUE_EXACT_ROLE_CANDIDATE" if len(exact) == 1 else "AMBIGUOUS_EXACT_ROLE_CANDIDATE"
        )
        proposed_text = exact[0]["alias_text"] if len(exact) == 1 else None
    else:
        status = (
            "UNRESOLVED_UNIQUE_REPAIR_CANDIDATE"
            if len(best) == 1
            else "UNRESOLVED_AMBIGUOUS_REPAIR_CANDIDATE"
        )
        proposed_text = best[0]["alias_text"] if len(best) == 1 else None
    raw_span = _raw_span(atom, ordinal)
    identity = {
        "raw_span": raw_span,
        "proposed_text": proposed_text,
        "proposal_status": status,
        "candidate_matches": matches,
    }
    return {
        "semantic_proposal_id": _PROPOSAL_PREFIX + canonical_json_sha256_v1(identity),
        **identity,
    }


def _deferred_exact_collision_proposal(
    *,
    atom: Mapping[str, Any],
    ordinal: int,
    exact_posting_fanout: int,
) -> dict[str, Any]:
    """Retain one common-label event without expanding registry-wide matches."""

    normalized = _normalize_text(atom["raw_text"])
    body = _presentation_body(normalized)
    identity = {
        "raw_span": _raw_span(atom, ordinal),
        "proposed_text": None,
        "proposal_status": "DEFERRED_EXACT_ALIAS_COLLISION",
        "candidate_matches": [],
        "exact_collision_receipt": {
            "normalized_surface": normalized,
            "presentation_body": body,
            "registry_exact_posting_fanout": exact_posting_fanout,
            "resolution_scope": "LOCAL_BRANCH_SHORTLIST_ONLY",
        },
    }
    return {
        "semantic_proposal_id": _PROPOSAL_PREFIX + canonical_json_sha256_v1(identity),
        **identity,
    }


def _match_sort_key(item: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        item["edit_distance"],
        item["family_id"],
        _ROLE_KIND_ORDER[item["role_kind"]],
        item["role"],
        item["normalized_alias"],
        item["alias_entry_id"],
    )


def _compile_vocabulary(
    entries: Sequence[_AliasEntry],
    *,
    ngram_size: int,
) -> tuple[
    dict[str, list[_AliasEntry]],
    dict[str, list[_AliasEntry]],
    dict[str, tuple[tuple[str, int], ...]],
]:
    exact: dict[str, list[_AliasEntry]] = defaultdict(list)
    postings: dict[str, list[_AliasEntry]] = defaultdict(list)
    alias_counts: dict[str, tuple[tuple[str, int], ...]] = {}
    for entry in entries:
        exact[entry.normalized_alias].append(entry)
        counter = _ngram_counter(entry.normalized_alias, ngram_size)
        alias_counts[entry.entry_id] = tuple(sorted(counter.items()))
        for gram in counter:
            postings[gram].append(entry)
    return dict(exact), dict(postings), alias_counts


def compile_local_accounting_typed_proposal_registry_v1(
    family_specs: Sequence[FamilySpecV1],
    generator_config: LocalAccountingTypedProposalConfigV1 = (
        DEFAULT_LOCAL_ACCOUNTING_TYPED_PROPOSAL_CONFIG_V1
    ),
) -> CompiledLocalAccountingTypedProposalRegistryV1:
    """Compile and bind a multi-family vocabulary once for reuse across pages."""

    caller_config = _validate_config(generator_config)
    config_payload = local_accounting_typed_proposal_config_payload_v1(caller_config)
    config = _config_from_payload(config_payload)
    caller_bound = _bound_specs(family_specs)
    bound = [
        (_family_spec_from_payload(payload), canonical_clone_v1(payload), digest)
        for _spec, payload, digest in caller_bound
    ]
    entries = _alias_entries(bound)
    exact, qgram_postings, alias_qgram_counts = _compile_vocabulary(
        entries, ngram_size=config.repair_ngram_size
    )
    exact_family_groups: dict[tuple[str, str], list[_AliasEntry]] = defaultdict(list)
    for entry in entries:
        exact_family_groups[(entry.normalized_alias, entry.family_id)].append(entry)
    registry_payload = local_accounting_family_registry_payload_v1(
        tuple(spec for spec, _payload, _digest in bound)
    )
    registry_bytes = canonical_json_bytes_v1(registry_payload)
    compiled = object.__new__(CompiledLocalAccountingTypedProposalRegistryV1)
    handle_bound = [
        (_family_spec_from_payload(payload), canonical_clone_v1(payload), digest)
        for _spec, payload, digest in bound
    ]
    handle_config = _config_from_payload(config_payload)
    values = {
        "family_specs": tuple(spec for spec, _payload, _digest in handle_bound),
        "config": handle_config,
        "registry_payload_json": registry_bytes,
        "registry_sha256": canonical_json_sha256_v1(registry_payload),
        "bound_specs": tuple(
            (spec, canonical_json_bytes_v1(payload), digest)
            for spec, payload, digest in handle_bound
        ),
        "alias_entries": tuple(entries),
        "exact_index": MappingProxyType({key: tuple(value) for key, value in exact.items()}),
        "ngram_index": MappingProxyType(
            {key: tuple(value) for key, value in qgram_postings.items()}
        ),
        "_construction_token": _COMPILED_REGISTRY_CONSTRUCTION_TOKEN,
    }
    for name, value in values.items():
        object.__setattr__(compiled, name, value)
    state_bound = tuple(
        (
            _family_spec_from_payload(payload),
            canonical_clone_v1(payload),
            digest,
        )
        for _spec, payload, digest in bound
    )
    registry_sha = canonical_json_sha256_v1(registry_payload)
    state = _CompiledRegistryStateV1(
        family_specs=tuple(spec for spec, _payload, _digest in state_bound),
        config=_config_from_payload(config_payload),
        bound_specs=state_bound,
        spec_by_id=MappingProxyType(
            {spec.family_id: (spec, digest) for spec, _payload, digest in state_bound}
        ),
        alias_entries=tuple(entries),
        exact_index=MappingProxyType({key: tuple(value) for key, value in exact.items()}),
        exact_family_index=MappingProxyType(
            {key: tuple(value) for key, value in sorted(exact_family_groups.items())}
        ),
        qgram_postings=MappingProxyType(
            {key: tuple(value) for key, value in qgram_postings.items()}
        ),
        alias_qgram_counts=MappingProxyType(alias_qgram_counts),
        registry_sha256=registry_sha,
        registry_payload_sha256=registry_sha,
        family_spec_binding_json=canonical_json_bytes_v1(
            {
                "format_version": "LOCAL_ACCOUNTING_FAMILY_REGISTRY_BINDING_V1",
                "family_count": len(state_bound),
                "registry_sha256": registry_sha,
                "registry_payload_sha256": registry_sha,
            }
        ),
        config_payload_json=canonical_json_bytes_v1(config_payload),
        config_sha256=canonical_json_sha256_v1(config_payload),
        compiled_alias_axis_sha256=canonical_json_sha256_v1([entry._asdict() for entry in entries]),
    )
    handle_id = id(compiled)

    def remove_state(
        reference: weakref.ReferenceType[CompiledLocalAccountingTypedProposalRegistryV1],
        *,
        expected_id: int = handle_id,
    ) -> None:
        current = _COMPILED_REGISTRY_STATE_BY_HANDLE_ID.get(expected_id)
        if current is not None and current[0] is reference:
            _COMPILED_REGISTRY_STATE_BY_HANDLE_ID.pop(expected_id, None)

    reference = weakref.ref(compiled, remove_state)
    _COMPILED_REGISTRY_STATE_BY_HANDLE_ID[handle_id] = (reference, state)
    return compiled


def _compiled_registry_state_v1(
    value: CompiledLocalAccountingTypedProposalRegistryV1,
) -> _CompiledRegistryStateV1:
    entry = _COMPILED_REGISTRY_STATE_BY_HANDLE_ID.get(id(value))
    if (
        type(value) is not CompiledLocalAccountingTypedProposalRegistryV1
        or entry is None
        or entry[0]() is not value
    ):
        raise _error("compiled registry was not created by the versioned compiler")
    return entry[1]


def _line_matches(
    *,
    raw_text: str,
    exact_index: Mapping[str, Sequence[_AliasEntry]],
    ngram_index: Mapping[str, Sequence[_AliasEntry]],
    alias_qgram_counts: Mapping[str, tuple[tuple[str, int], ...]],
    config: LocalAccountingTypedProposalConfigV1,
) -> tuple[list[dict[str, Any]], int, int, int, bool, bool, int, bool]:
    normalized = _normalize_text(raw_text)
    body = _presentation_body(normalized)
    # Common structural surfaces such as "total" can legitimately occur in
    # hundreds of family specifications.  Inspect posting sizes before
    # materializing per-family claims so one common line cannot expand with
    # registry breadth.  The sum is deliberately conservative when the
    # normalized and presentation-body postings overlap: false-closed is safer
    # than silently creating a family x line artifact.
    exact_posting_fanout = len(exact_index.get(normalized, ()))
    if body != normalized:
        exact_posting_fanout += len(exact_index.get(body, ()))
    if exact_posting_fanout > config.maximum_exact_alias_candidate_fanout:
        return [], 0, 0, 0, False, False, exact_posting_fanout, True
    entry_surface: dict[str, tuple[_AliasEntry, str]] = {}
    for entry in exact_index.get(normalized, ()):
        entry_surface[entry.entry_id] = (entry, normalized)
    if body != normalized:
        for entry in exact_index.get(body, ()):
            if entry.role_kind in {"OWNER", "BRANCH"}:
                entry_surface[entry.entry_id] = (entry, body)
    if entry_surface:
        return (
            sorted(
                [
                    _match_payload(
                        entry,
                        match_kind="EXACT_ALIAS",
                        edit_distance=0,
                        matched_surface=surface,
                    )
                    for entry, surface in entry_surface.values()
                ],
                key=_match_sort_key,
            ),
            0,
            0,
            0,
            False,
            False,
            exact_posting_fanout,
            False,
        )
    if (
        config.maximum_edit_distance == 0
        or len(normalized.replace(" ", "")) < config.minimum_repair_normalized_length
    ):
        return [], 0, 0, 0, False, False, 0, False

    candidate_by_id: dict[str, _AliasEntry] = {}
    posting_visits = 0
    surfaces = [normalized]
    if body != normalized:
        surfaces.append(body)
    for surface in surfaces:
        counter = _ngram_counter(surface, config.repair_ngram_size)
        shared: dict[str, _AliasEntry] = {}
        for gram in counter:
            posting = ngram_index.get(gram, ())
            for entry in posting:
                if posting_visits >= config.maximum_fuzzy_index_posting_visits_per_line:
                    return [], 0, 0, posting_visits, False, True, 0, False
                posting_visits += 1
                if abs(len(surface) - len(entry.normalized_alias)) <= (
                    config.maximum_edit_distance
                ):
                    shared[entry.entry_id] = entry
        for entry in shared.values():
            if (
                surface == body
                and body != normalized
                and entry.role_kind
                not in {
                    "OWNER",
                    "BRANCH",
                }
            ):
                continue
            if _qgram_edit_lower_bound_allows(
                counter,
                dict(alias_qgram_counts[entry.entry_id]),
                size=config.repair_ngram_size,
                maximum_edits=config.maximum_edit_distance,
            ):
                candidate_by_id[entry.entry_id] = entry

    candidate_fanout = len(candidate_by_id)
    if candidate_fanout > config.maximum_fuzzy_alias_candidate_fanout:
        return [], 0, candidate_fanout, posting_visits, True, False, 0, False

    evaluated = 0
    qualified: list[dict[str, Any]] = []
    for entry in candidate_by_id.values():
        allowed_surfaces = [normalized]
        if body != normalized and entry.role_kind in {"OWNER", "BRANCH"}:
            allowed_surfaces.append(body)
        distances: list[tuple[int, str]] = []
        for surface in allowed_surfaces:
            evaluated += 1
            distance = _bounded_edit_distance(
                surface, entry.normalized_alias, config.maximum_edit_distance
            )
            if distance is not None:
                distances.append((distance, surface))
        if distances:
            distance, surface = min(distances)
            qualified.append(
                _match_payload(
                    entry,
                    match_kind="BOUNDED_EDIT_CANDIDATE",
                    edit_distance=distance,
                    matched_surface=surface,
                )
            )
    if not qualified:
        return [], evaluated, candidate_fanout, posting_visits, False, False, 0, False
    distance_bands = sorted({item["edit_distance"] for item in qualified})[
        : config.retained_distance_band_count
    ]
    retained = [item for item in qualified if item["edit_distance"] in distance_bands]
    return (
        sorted(retained, key=_match_sort_key),
        evaluated,
        candidate_fanout,
        posting_visits,
        False,
        False,
        0,
        False,
    )


def _union_bbox(spans: Sequence[Mapping[str, Any]]) -> list[int]:
    boxes = [span["raw_span"]["canonical_bbox_mpt"] for span in spans]
    return [
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    ]


def _finalize_topology_candidate(
    *,
    family_spec: FamilySpecV1,
    family_spec_sha256: str,
    members: list[dict[str, Any]],
    orphan_branch: bool,
    maximum_span: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    family_matches_by_proposal: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    for proposal in members:
        matches = [
            item
            for item in proposal["candidate_matches"]
            if item["family_id"] == family_spec.family_id
        ]
        if matches:
            family_matches_by_proposal.append((proposal, matches))
    first_ordinal = family_matches_by_proposal[0][0]["raw_span"]["source_ordinal"]
    last_ordinal = family_matches_by_proposal[-1][0]["raw_span"]["source_ordinal"]
    member_roles: list[dict[str, Any]] = []
    exact_role_positions: dict[tuple[str, str], list[int]] = defaultdict(list)
    contains_repair = False
    contains_ambiguity = False
    for proposal, matches in family_matches_by_proposal:
        best_distance = min(item["edit_distance"] for item in matches)
        best = [item for item in matches if item["edit_distance"] == best_distance]
        contains_ambiguity = contains_ambiguity or len(best) != 1
        contains_repair = contains_repair or any(
            item["match_kind"] not in {"EXACT_ALIAS", "EXACT_ALIAS_AFTER_LOCAL_FRONTIER"}
            for item in matches
        )
        for match in matches:
            member_roles.append(
                {
                    "semantic_proposal_id": proposal["semantic_proposal_id"],
                    "source_ordinal": proposal["raw_span"]["source_ordinal"],
                    "role_kind": match["role_kind"],
                    "role": match["role"],
                    "match_kind": match["match_kind"],
                    "edit_distance": match["edit_distance"],
                    "alias_entry_id": match["alias_entry_id"],
                }
            )
            if match["match_kind"] in {
                "EXACT_ALIAS",
                "EXACT_ALIAS_AFTER_LOCAL_FRONTIER",
            }:
                exact_role_positions[(match["role_kind"], match["role"])].append(
                    proposal["raw_span"]["source_ordinal"]
                )

    required_keys = [
        ("OWNER", "OWNER"),
        ("BRANCH", "BRANCH"),
        *[("ORDERED_CHILD", row.role) for row in family_spec.ordered_children],
        ("TOTAL", "TOTAL"),
    ]
    missing = [
        role for role_kind, role in required_keys if not exact_role_positions[(role_kind, role)]
    ]
    repeated = [
        role
        for role_kind, role in required_keys
        if len(exact_role_positions[(role_kind, role)]) != 1
        and exact_role_positions[(role_kind, role)]
    ]
    unique_positions = [
        exact_role_positions[key][0] for key in required_keys if len(exact_role_positions[key]) == 1
    ]
    order_conflict = len(unique_positions) == len(required_keys) and unique_positions != sorted(
        unique_positions
    )
    span_exceeded = last_ordinal - first_ordinal + 1 > maximum_span
    exact_complete = not (
        orphan_branch
        or missing
        or repeated
        or order_conflict
        or span_exceeded
        or contains_repair
        or contains_ambiguity
    )
    if exact_complete:
        status = "EXACT_ORDERED_STRUCTURE_CANDIDATE"
        disposition = "RETAINED_FOR_BOUNDED_OBSERVATION_ASSEMBLY"
        reason = "COMPLETE_EXACT_ORDERED_FAMILY_VOCABULARY"
    elif contains_repair:
        status = "UNRESOLVED_REPAIR_TOPOLOGY_CANDIDATE"
        disposition = "RETAINED_UNRESOLVED"
        reason = "REPAIR_CANDIDATE_CANNOT_ACCEPT_STRUCTURE"
    else:
        status = "UNRESOLVED_INCOMPLETE_OR_AMBIGUOUS_TOPOLOGY_CANDIDATE"
        disposition = "RETAINED_UNRESOLVED"
        reason = "STRICT_ORDERED_CORE_NOT_PROVEN"
    identity = {
        "family_id": family_spec.family_id,
        "family_spec_sha256": family_spec_sha256,
        "source_ordinal_range": [first_ordinal, last_ordinal],
        "canonical_bbox_mpt": _union_bbox([item[0] for item in family_matches_by_proposal]),
        "semantic_proposal_ids": [
            proposal["semantic_proposal_id"] for proposal, _matches in family_matches_by_proposal
        ],
        "member_role_candidates": sorted(
            member_roles,
            key=lambda item: (
                item["source_ordinal"],
                _ROLE_KIND_ORDER[item["role_kind"]],
                item["role"],
                item["alias_entry_id"],
            ),
        ),
        "missing_required_roles": missing,
        "repeated_required_roles": repeated,
        "orphan_branch": orphan_branch,
        "order_conflict": order_conflict,
        "maximum_span_exceeded": span_exceeded,
        "contains_repair_candidates": contains_repair,
        "contains_ambiguous_role_candidates": contains_ambiguity,
        "candidate_status": status,
    }
    candidate_id = _TOPOLOGY_PREFIX + canonical_json_sha256_v1(identity)
    candidate = {"topology_candidate_id": candidate_id, **identity}
    candidate_disposition = {
        "topology_candidate_id": candidate_id,
        "disposition": disposition,
        "reason_code": reason,
    }
    return candidate, candidate_disposition


def _topology_candidates(
    *,
    proposals: Sequence[dict[str, Any]],
    spec_by_id: Mapping[str, tuple[FamilySpecV1, str]],
    exact_family_index: Mapping[tuple[str, str], tuple[_AliasEntry, ...]],
    config: LocalAccountingTypedProposalConfigV1,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    int,
    list[dict[str, Any]],
    int,
    int,
]:
    shortlisted: set[str] = set()
    proposal_families: list[tuple[dict[str, Any], set[str], set[str]]] = []
    exact_residual_roles_by_family: dict[str, set[str]] = defaultdict(set)
    residual_members_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    event_visits = 0
    for proposal in proposals:
        families: set[str] = set()
        residual_families: set[str] = set()
        for match in proposal["candidate_matches"]:
            family = match["family_id"]
            families.add(family)
            if match["role_kind"] == "BRANCH":
                shortlisted.add(family)
            if match["match_kind"] == "EXACT_ALIAS" and match["role_kind"] in {
                "OWNER",
                "ORDERED_CHILD",
                "TOTAL",
            }:
                residual_families.add(family)
                if match["role_kind"] in {"ORDERED_CHILD", "TOTAL"}:
                    exact_residual_roles_by_family[family].add(match["role"])
        proposal_families.append((proposal, families, residual_families))
        for family in sorted(residual_families):
            residual_members_by_family[family].append(proposal)
            event_visits += 1
    events_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    contextual_exact_proposals: list[dict[str, Any]] = []
    contextual_lookup_count = 0
    contextual_overflow_count = 0

    def resolve_collision(
        proposal: dict[str, Any],
        candidate_families: set[str],
        *,
        allowed_role_kinds: frozenset[str] | None = None,
    ) -> list[tuple[str, dict[str, Any]]]:
        nonlocal contextual_lookup_count, contextual_overflow_count
        collision = proposal["exact_collision_receipt"]
        surfaces = [collision["normalized_surface"]]
        if collision["presentation_body"] != collision["normalized_surface"]:
            surfaces.append(collision["presentation_body"])
        if len(candidate_families) > config.maximum_exact_alias_candidate_fanout:
            contextual_overflow_count += 1
            return []
        resolved_pairs: list[tuple[str, dict[str, Any]]] = []
        for family in sorted(candidate_families):
            contextual_lookup_count += 1
            resolved_by_id: dict[str, _AliasEntry] = {}
            for surface in surfaces:
                for entry in exact_family_index.get((surface, family), ()):
                    if allowed_role_kinds is not None and entry.role_kind not in allowed_role_kinds:
                        continue
                    if (
                        surface == collision["presentation_body"]
                        and surface != collision["normalized_surface"]
                        and entry.role_kind not in {"OWNER", "BRANCH"}
                    ):
                        continue
                    resolved_by_id[entry.entry_id] = entry
            if not resolved_by_id:
                continue
            if (
                sum(len(item[1]["candidate_matches"]) for item in resolved_pairs)
                + len(resolved_by_id)
                > config.maximum_exact_alias_candidate_fanout
            ):
                contextual_overflow_count += 1
                return []
            matches = sorted(
                (
                    _match_payload(
                        entry,
                        match_kind="EXACT_ALIAS_AFTER_LOCAL_FRONTIER",
                        edit_distance=0,
                        matched_surface=(
                            collision["normalized_surface"]
                            if entry.normalized_alias == collision["normalized_surface"]
                            else collision["presentation_body"]
                        ),
                    )
                    for entry in resolved_by_id.values()
                ),
                key=_match_sort_key,
            )
            resolved_identity = {
                "raw_span": canonical_clone_v1(proposal["raw_span"]),
                "proposed_text": matches[0]["alias_text"] if len(matches) == 1 else None,
                "proposal_status": (
                    "UNIQUE_EXACT_ROLE_CANDIDATE_AFTER_LOCAL_FRONTIER"
                    if len(matches) == 1
                    else "AMBIGUOUS_EXACT_ROLE_CANDIDATE_AFTER_LOCAL_FRONTIER"
                ),
                "candidate_matches": matches,
                "source_collision_proposal_id": proposal["semantic_proposal_id"],
            }
            resolved_pairs.append(
                (
                    family,
                    {
                        "semantic_proposal_id": (
                            _PROPOSAL_PREFIX + canonical_json_sha256_v1(resolved_identity)
                        ),
                        **resolved_identity,
                    },
                )
            )
        return resolved_pairs

    # One source-order pass.  A common exact label is resolved only against the
    # local active family frontier, never every branch elsewhere on the page.
    active_frontier: set[str] = set()
    pending_owner_frontier: set[str] = set()
    pending_owner_proposal: dict[str, dict[str, Any]] = {}
    pending_unanchored_collisions: list[dict[str, Any]] = []
    for proposal, families, _residual_families in proposal_families:
        ordinal = proposal["raw_span"]["source_ordinal"]
        pending_unanchored_collisions = [
            item
            for item in pending_unanchored_collisions
            if ordinal - item["raw_span"]["source_ordinal"]
            <= config.maximum_owner_to_branch_line_gap
        ]
        collision = proposal.get("exact_collision_receipt")
        resolved_pairs: list[tuple[str, dict[str, Any]]] = []
        if collision is not None:
            branch_pairs: list[tuple[str, dict[str, Any]]] = []
            if pending_owner_frontier:
                branch_pairs = resolve_collision(
                    proposal,
                    pending_owner_frontier,
                    allowed_role_kinds=frozenset({"BRANCH"}),
                )
                resolved_pairs.extend(branch_pairs)
            # A corroborated pending OWNER+BRANCH transition owns this source
            # event and resets the prior frontier.  Otherwise resolve the
            # event within the current active family.  Never spend separate
            # per-phase fanout budgets on the same line.
            if active_frontier and not branch_pairs:
                resolved_pairs.extend(
                    resolve_collision(
                        proposal,
                        active_frontier,
                        allowed_role_kinds=frozenset({"ORDERED_CHILD", "OPTIONAL_CHILD", "TOTAL"}),
                    )
                )
            if not active_frontier and not pending_owner_frontier:
                pending_unanchored_collisions.append(proposal)

        proposal_matches = list(proposal["candidate_matches"])
        direct_branch_families = {
            match["family_id"] for match in proposal_matches if match["role_kind"] == "BRANCH"
        }
        prebranch_resolved_pairs: list[tuple[str, dict[str, Any]]] = []
        if direct_branch_families and pending_unanchored_collisions:
            for pending_collision in pending_unanchored_collisions:
                prebranch_resolved_pairs.extend(
                    resolve_collision(
                        pending_collision,
                        direct_branch_families,
                        allowed_role_kinds=frozenset({"OWNER"}),
                    )
                )
            pending_unanchored_collisions = []
            resolved_pairs = prebranch_resolved_pairs + resolved_pairs
        resolved_matches = [
            match for _family, resolved in resolved_pairs for match in resolved["candidate_matches"]
        ]
        all_matches = proposal_matches + resolved_matches
        owner_families = {
            match["family_id"] for match in all_matches if match["role_kind"] == "OWNER"
        }
        branch_families = {
            match["family_id"] for match in all_matches if match["role_kind"] == "BRANCH"
        }
        if owner_families:
            pending_owner_frontier = owner_families
            pending_owner_proposal = {
                family: proposal
                for family in owner_families
                if any(
                    match["family_id"] == family and match["role_kind"] == "OWNER"
                    for match in proposal_matches
                )
            }
        if branch_families:
            active_frontier = (
                branch_families & pending_owner_frontier
                if pending_owner_frontier
                else branch_families
            ) or branch_families
            shortlisted.update(active_frontier)
            for family in sorted(active_frontier):
                contextual_owner = next(
                    (
                        resolved
                        for resolved_family, resolved in prebranch_resolved_pairs
                        if resolved_family == family
                        and any(
                            match["role_kind"] == "OWNER" for match in resolved["candidate_matches"]
                        )
                    ),
                    None,
                )
                owner_proposal = pending_owner_proposal.get(family) or contextual_owner
                if owner_proposal is not None:
                    events_by_family[family].append(owner_proposal)
                    event_visits += 1
                if collision is None and family in families:
                    events_by_family[family].append(proposal)
                    event_visits += 1
            pending_owner_frontier = set()
            pending_owner_proposal = {}
        elif not owner_families and collision is None:
            for family in sorted(families & active_frontier):
                events_by_family[family].append(proposal)
                event_visits += 1
        for family, resolved in resolved_pairs:
            contextual_exact_proposals.append(resolved)
            if family in active_frontier:
                events_by_family[family].append(resolved)
                event_visits += 1
        total_families = {
            match["family_id"] for match in all_matches if match["role_kind"] == "TOTAL"
        }
        if total_families & active_frontier and not branch_families:
            active_frontier = set()
            pending_owner_frontier = set()
            pending_owner_proposal = {}
    for events in events_by_family.values():
        events.sort(
            key=lambda item: (
                item["raw_span"]["source_ordinal"],
                item["semantic_proposal_id"],
            )
        )
    # A complete structural trace may disambiguate shared generic OWNER/TOTAL
    # labels, but two families with the exact same local role trace may not both
    # become exact merely by filtering the same proposals per family.
    complete_trace_families_by_signature: dict[tuple[tuple[int, str, int], ...], set[str]] = (
        defaultdict(set)
    )
    for family_id, events in events_by_family.items():
        trace: list[tuple[int, str, int]] = []
        spec = spec_by_id[family_id][0]
        child_position = {item.role: index for index, item in enumerate(spec.ordered_children)}
        optional_position = {item.role: index for index, item in enumerate(spec.optional_children)}
        for event in events:
            for match in event["candidate_matches"]:
                if match["family_id"] == family_id:
                    position = (
                        child_position.get(match["role"], -1)
                        if match["role_kind"] == "ORDERED_CHILD"
                        else optional_position.get(match["role"], -1)
                        if match["role_kind"] == "OPTIONAL_CHILD"
                        else 0
                    )
                    trace.append(
                        (
                            event["raw_span"]["source_ordinal"],
                            match["role_kind"],
                            position,
                        )
                    )
        complete_trace_families_by_signature[tuple(sorted(trace))].add(family_id)
    structurally_ambiguous_families = {
        family_id
        for families in complete_trace_families_by_signature.values()
        if len(families) > 1
        for family_id in families
    }
    residual_shortlisted = {
        family_id
        for family_id, roles in exact_residual_roles_by_family.items()
        if family_id not in shortlisted
        and roles
        >= {
            *(item.role for item in spec_by_id[family_id][0].ordered_children),
            "TOTAL",
        }
    }

    candidates: list[dict[str, Any]] = []
    dispositions: list[dict[str, Any]] = []
    for family_id in sorted(shortlisted):
        spec, spec_sha = spec_by_id[family_id]
        pending_owner: dict[str, Any] | None = None
        active: list[dict[str, Any]] | None = None
        orphan = False

        def finalize(
            family_spec: FamilySpecV1 = spec,
            family_spec_sha256: str = spec_sha,
        ) -> None:
            nonlocal active, orphan
            if active:
                candidate, disposition = _finalize_topology_candidate(
                    family_spec=family_spec,
                    family_spec_sha256=family_spec_sha256,
                    members=active,
                    orphan_branch=orphan,
                    maximum_span=config.maximum_topology_candidate_line_span,
                )
                if (
                    family_spec.family_id in structurally_ambiguous_families
                    and candidate["candidate_status"] == "EXACT_ORDERED_STRUCTURE_CANDIDATE"
                ):
                    candidate["contains_ambiguous_role_candidates"] = True
                    candidate["candidate_status"] = (
                        "UNRESOLVED_INCOMPLETE_OR_AMBIGUOUS_TOPOLOGY_CANDIDATE"
                    )
                    candidate["topology_candidate_id"] = (
                        _TOPOLOGY_PREFIX
                        + canonical_json_sha256_v1(
                            {
                                key: value
                                for key, value in candidate.items()
                                if key != "topology_candidate_id"
                            }
                        )
                    )
                    disposition = {
                        "topology_candidate_id": candidate["topology_candidate_id"],
                        "disposition": "RETAINED_UNRESOLVED",
                        "reason_code": "CROSS_FAMILY_LOCAL_TRACE_COLLISION",
                    }
                candidates.append(candidate)
                dispositions.append(disposition)
            active = None
            orphan = False

        for proposal in events_by_family[family_id]:
            family_matches = [
                item for item in proposal["candidate_matches"] if item["family_id"] == family_id
            ]
            role_kinds = {item["role_kind"] for item in family_matches}
            ordinal = proposal["raw_span"]["source_ordinal"]
            if "OWNER" in role_kinds:
                finalize()
                pending_owner = proposal
                continue
            if "BRANCH" in role_kinds:
                finalize()
                if (
                    pending_owner is not None
                    and ordinal - pending_owner["raw_span"]["source_ordinal"]
                    <= config.maximum_owner_to_branch_line_gap
                ):
                    active = [pending_owner, proposal]
                    orphan = False
                else:
                    active = [proposal]
                    orphan = True
                pending_owner = None
                continue
            if active is not None:
                active.append(proposal)
                if "TOTAL" in role_kinds:
                    finalize()
        finalize()
    for family_id in sorted(residual_shortlisted):
        spec, spec_sha = spec_by_id[family_id]
        residual_members = residual_members_by_family[family_id]
        candidate, disposition = _finalize_topology_candidate(
            family_spec=spec,
            family_spec_sha256=spec_sha,
            members=residual_members,
            orphan_branch=True,
            maximum_span=config.maximum_topology_candidate_line_span,
        )
        residual_is_unique = (
            candidate["missing_required_roles"] in (["BRANCH"], ["OWNER", "BRANCH"])
            and not candidate["repeated_required_roles"]
            and not candidate["order_conflict"]
            and not candidate["maximum_span_exceeded"]
        )
        missing_only_branch = candidate["missing_required_roles"] == ["BRANCH"]
        if residual_is_unique and missing_only_branch:
            residual_status = "UNRESOLVED_MISSING_BRANCH_FINGERPRINT"
            residual_reason = "COMPLETE_CHILD_FINGERPRINT_WITHOUT_LOCAL_BRANCH_ANCHOR"
        elif residual_is_unique:
            residual_status = "UNRESOLVED_CHILD_FINGERPRINT_MISSING_OWNER_AND_BRANCH"
            residual_reason = "COMPLETE_CHILD_FINGERPRINT_WITHOUT_OWNER_OR_BRANCH_ANCHOR"
        else:
            residual_status = "UNRESOLVED_RESIDUAL_FAMILY_FINGERPRINT"
            residual_reason = "AMBIGUOUS_OR_REPEATED_RESIDUAL_FAMILY_FINGERPRINT"
        candidate["candidate_status"] = residual_status
        candidate["topology_candidate_id"] = _TOPOLOGY_PREFIX + canonical_json_sha256_v1(
            {key: value for key, value in candidate.items() if key != "topology_candidate_id"}
        )
        disposition = {
            "topology_candidate_id": candidate["topology_candidate_id"],
            "disposition": "RETAINED_UNRESOLVED",
            "reason_code": residual_reason,
        }
        candidates.append(candidate)
        dispositions.append(disposition)
    candidates.sort(
        key=lambda item: (
            item["source_ordinal_range"][0],
            item["source_ordinal_range"][1],
            item["family_id"],
            item["topology_candidate_id"],
        )
    )
    disposition_by_id = {item["topology_candidate_id"]: item for item in dispositions}
    dispositions = [disposition_by_id[item["topology_candidate_id"]] for item in candidates]
    return (
        candidates,
        dispositions,
        event_visits,
        contextual_exact_proposals,
        contextual_lookup_count,
        contextual_overflow_count,
    )


def _build_from_validated(
    source: Mapping[str, Any],
    *,
    registry_state: _CompiledRegistryStateV1,
) -> dict[str, Any]:
    config = registry_state.config
    entries = registry_state.alias_entries
    exact_index = registry_state.exact_index
    ngram_index = registry_state.qgram_postings
    eligible_lines = list(
        enumerate(
            atom
            for atom in source["neutral_page_v1"]["atoms"]
            if atom.get("kind") == "LINE" and atom.get("authority") == "AUTHENTICATED_PRIMARY"
        )
    )
    proposals: list[dict[str, Any]] = []
    line_dispositions: list[dict[str, Any]] = []
    fuzzy_evaluations = 0
    exact_line_count = 0
    repair_line_count = 0
    protected_counts: dict[str, int] = defaultdict(int)
    maximum_fuzzy_fanout = 0
    total_fuzzy_fanout = 0
    fuzzy_fanout_overflow_count = 0
    fuzzy_index_posting_visits = 0
    fuzzy_index_posting_overflow_count = 0
    maximum_exact_fanout = 0
    total_exact_fanout = 0
    exact_fanout_overflow_count = 0
    for ordinal, atom in eligible_lines:  # The only source LINE-axis scan.
        raw_text = atom.get("raw_text")
        bbox = atom.get("canonical_bbox_mpt")
        if (
            type(raw_text) is not str
            or not raw_text
            or type(bbox) is not list
            or len(bbox) != 4
            or any(type(value) is not int for value in bbox)
        ):
            raise _error("eligible authenticated primary LINE semantics drifted")
        if parse_local_accounting_period_v1(raw_text) is not None:
            disposition = "PROTECTED_PERIOD_CONTEXT"
            reason = "STRICT_PERIOD_TOKEN_EXCLUDED_FROM_REPAIR"
            proposal = None
        elif parse_local_accounting_unit_v1(raw_text) is not None:
            disposition = "PROTECTED_UNIT_CONTEXT"
            reason = "STRICT_UNIT_TOKEN_EXCLUDED_FROM_REPAIR"
            proposal = None
        elif (protected_value_context := _protected_value_context(raw_text)) is not None:
            disposition = protected_value_context
            reason = "SOURCE_VISIBLE_VALUE_OR_UNIT_CONTEXT_EXCLUDED_FROM_REPAIR"
            proposal = None
        elif _is_numeric(raw_text):
            disposition = "PROTECTED_NUMERIC_CONTEXT"
            reason = "STRICT_NUMERIC_TOKEN_EXCLUDED_FROM_REPAIR"
            proposal = None
        else:
            (
                matches,
                evaluated,
                fanout,
                posting_visits,
                fanout_overflow,
                posting_overflow,
                exact_fanout,
                exact_fanout_overflow,
            ) = _line_matches(
                raw_text=raw_text,
                exact_index=exact_index,
                ngram_index=ngram_index,
                alias_qgram_counts=registry_state.alias_qgram_counts,
                config=config,
            )
            fuzzy_evaluations += evaluated
            fuzzy_index_posting_visits += posting_visits
            maximum_fuzzy_fanout = max(maximum_fuzzy_fanout, fanout)
            total_fuzzy_fanout += fanout
            fuzzy_fanout_overflow_count += fanout_overflow
            fuzzy_index_posting_overflow_count += posting_overflow
            maximum_exact_fanout = max(maximum_exact_fanout, exact_fanout)
            total_exact_fanout += exact_fanout
            exact_fanout_overflow_count += exact_fanout_overflow
            proposal = (
                _semantic_proposal(atom=atom, ordinal=ordinal, matches=matches) if matches else None
            )
            if exact_fanout_overflow:
                proposal = _deferred_exact_collision_proposal(
                    atom=atom,
                    ordinal=ordinal,
                    exact_posting_fanout=exact_fanout,
                )
                disposition = "RETAINED_UNRESOLVED_EXACT_ALIAS_FANOUT"
                reason = "DEFERRED_TO_LOCAL_BRANCH_SHORTLIST_RESOLUTION"
            elif posting_overflow:
                disposition = "RETAINED_UNRESOLVED_FUZZY_INDEX_WORK_BOUND"
                reason = "FUZZY_INDEX_POSTING_VISITS_EXCEEDED_BOUND"
            elif fanout_overflow:
                disposition = "RETAINED_UNRESOLVED_FUZZY_FANOUT"
                reason = "FUZZY_ALIAS_CANDIDATE_FANOUT_EXCEEDED_BOUND"
            elif proposal is None:
                disposition = "RETAINED_NO_VOCABULARY_MATCH"
                reason = "NO_BOUNDED_FAMILY_STRUCTURAL_VOCABULARY_CANDIDATE"
            elif all(item["match_kind"] == "EXACT_ALIAS" for item in proposal["candidate_matches"]):
                exact_line_count += 1
                if proposal["proposal_status"] == "UNIQUE_EXACT_ROLE_CANDIDATE":
                    disposition = "PROPOSED_EXACT_SEMANTIC_ROLE"
                    reason = "UNIQUE_EXACT_FAMILY_STRUCTURAL_ALIAS"
                else:
                    disposition = "RETAINED_AMBIGUOUS_EXACT_ROLE"
                    reason = "EXACT_ALIAS_COLLIDES_ACROSS_BOUND_FAMILY_ROLES"
            else:
                repair_line_count += 1
                disposition = "RETAINED_UNRESOLVED_REPAIR_CANDIDATE"
                reason = "BOUNDED_REPAIR_IS_CANDIDATE_EVIDENCE_NOT_ACCEPTANCE"
        protected_counts[disposition] += 1
        if proposal is not None:
            proposals.append(proposal)
        line_dispositions.append(
            {
                "source_atom_id": atom["source_local_id"],
                "source_ordinal": ordinal,
                "semantic_proposal_id": (
                    proposal["semantic_proposal_id"] if proposal is not None else None
                ),
                "disposition": disposition,
                "reason_code": reason,
            }
        )

    (
        topology,
        topology_dispositions,
        topology_event_visits,
        contextual_exact_proposals,
        contextual_exact_lookup_count,
        contextual_exact_overflow_count,
    ) = _topology_candidates(
        proposals=proposals,
        spec_by_id=registry_state.spec_by_id,
        exact_family_index=registry_state.exact_family_index,
        config=config,
    )
    generator_identity = _generator_identity_payload()
    eligible_axis = [
        {
            "source_atom_id": atom["source_local_id"],
            "source_ordinal": ordinal,
            "raw_text": atom["raw_text"],
            "canonical_bbox_mpt": atom["canonical_bbox_mpt"],
        }
        for ordinal, atom in eligible_lines
    ]
    receipts = {
        "format_version": "LOCAL_ACCOUNTING_TYPED_PROPOSAL_REPLAY_RECEIPT_V1",
        "eligible_primary_line_axis_sha256": canonical_json_sha256_v1(eligible_axis),
        "eligible_primary_line_id_sequence_sha256": canonical_json_sha256_v1(
            [item["source_atom_id"] for item in eligible_axis]
        ),
        "compiled_alias_axis_sha256": registry_state.compiled_alias_axis_sha256,
        "semantic_proposal_id_sequence_sha256": canonical_json_sha256_v1(
            [item["semantic_proposal_id"] for item in proposals]
        ),
        "contextual_exact_resolution_id_sequence_sha256": canonical_json_sha256_v1(
            [item["semantic_proposal_id"] for item in contextual_exact_proposals]
        ),
        "line_disposition_axis_sha256": canonical_json_sha256_v1(line_dispositions),
        "topology_candidate_id_sequence_sha256": canonical_json_sha256_v1(
            [item["topology_candidate_id"] for item in topology]
        ),
        "topology_disposition_axis_sha256": canonical_json_sha256_v1(topology_dispositions),
    }
    metrics = {
        "source_line_scan_passes": 1,
        "eligible_primary_line_count": len(eligible_lines),
        "eligible_primary_line_visit_count": len(eligible_lines),
        "compiled_family_count": len(registry_state.spec_by_id),
        "compiled_alias_count": len(entries),
        "registry_compile_passes_on_page": 0,
        "family_line_cartesian_evaluation_count": 0,
        "semantic_match_claim_count": sum(len(item["candidate_matches"]) for item in proposals)
        + sum(len(item["candidate_matches"]) for item in contextual_exact_proposals),
        "contextual_exact_resolution_proposal_count": len(contextual_exact_proposals),
        "contextual_exact_resolution_lookup_count": contextual_exact_lookup_count,
        "contextual_exact_resolution_overflow_line_count": (contextual_exact_overflow_count),
        "total_exact_alias_candidate_fanout": total_exact_fanout,
        "maximum_exact_alias_candidate_fanout": maximum_exact_fanout,
        "exact_alias_fanout_overflow_line_count": exact_fanout_overflow_count,
        "bounded_edit_distance_evaluation_count": fuzzy_evaluations,
        "total_fuzzy_alias_candidate_fanout": total_fuzzy_fanout,
        "maximum_fuzzy_alias_candidate_fanout": maximum_fuzzy_fanout,
        "fuzzy_alias_fanout_overflow_line_count": fuzzy_fanout_overflow_count,
        "fuzzy_index_posting_visit_count": fuzzy_index_posting_visits,
        "fuzzy_index_posting_overflow_line_count": (fuzzy_index_posting_overflow_count),
        "semantic_line_proposal_count": len(proposals),
        "exact_semantic_line_proposal_count": exact_line_count,
        "unresolved_repair_line_proposal_count": repair_line_count,
        "protected_period_line_count": protected_counts["PROTECTED_PERIOD_CONTEXT"],
        "protected_unit_line_count": protected_counts["PROTECTED_UNIT_CONTEXT"],
        "protected_numeric_line_count": protected_counts["PROTECTED_NUMERIC_CONTEXT"],
        "topology_event_visit_count": topology_event_visits,
        "topology_candidate_count": len(topology),
        "exact_ordered_topology_candidate_count": sum(
            item["candidate_status"] == "EXACT_ORDERED_STRUCTURE_CANDIDATE" for item in topology
        ),
        "unresolved_topology_candidate_count": sum(
            item["candidate_status"] != "EXACT_ORDERED_STRUCTURE_CANDIDATE" for item in topology
        ),
    }
    source_binding = {
        "source_local_page_id": source["source_local_page_id"],
        "source_projection_sha256": canonical_json_sha256_v1(source),
        "neutral_page_v1_sha256": source["neutral_page_v1_sha256"],
        "source_route": source["route"],
    }
    artifact_without_id = {
        "format_version": LOCAL_ACCOUNTING_TYPED_PROPOSAL_FORMAT_VERSION_V1,
        "claim_boundary": LOCAL_ACCOUNTING_TYPED_PROPOSAL_CLAIM_BOUNDARY_V1,
        "source_binding": source_binding,
        "family_spec_binding": decode_canonical_json_bytes_v1(
            registry_state.family_spec_binding_json
        ),
        "generator_binding": {
            "generator_identity": generator_identity,
            "generator_identity_sha256": canonical_json_sha256_v1(generator_identity),
        },
        "config_binding": {
            "config_payload": decode_canonical_json_bytes_v1(registry_state.config_payload_json),
            "config_sha256": registry_state.config_sha256,
        },
        "semantic_line_proposals": proposals,
        "contextual_exact_resolution_proposals": contextual_exact_proposals,
        "line_dispositions": line_dispositions,
        "topology_candidates": topology,
        "topology_dispositions": topology_dispositions,
        "replay_receipts": receipts,
        "metrics": metrics,
        "safety": _safety_payload(),
    }
    artifact_id = _SET_PREFIX + canonical_json_sha256_v1(artifact_without_id)
    return {"typed_proposal_set_id": artifact_id, **artifact_without_id}


def build_local_accounting_typed_proposal_set_v1(
    source_projection_v2: Mapping[str, Any],
    family_specs: Sequence[FamilySpecV1],
    generator_config: LocalAccountingTypedProposalConfigV1 = (
        DEFAULT_LOCAL_ACCOUNTING_TYPED_PROPOSAL_CONFIG_V1
    ),
) -> dict[str, Any]:
    """Build a candidate-only typed proposal set from one exact V2 page."""

    try:
        source = validate_source_evidence_projection_v2(source_projection_v2)
    except (TypeError, ValueError) as error:
        raise _error("source projection failed the exact V2 contract") from error
    compiled = compile_local_accounting_typed_proposal_registry_v1(family_specs, generator_config)
    if source["terminal"]:
        # Exact terminal projections have no eligible primary LINE authority;
        # retaining this explicit guard makes that boundary independently clear.
        if any(
            atom.get("kind") == "LINE" and atom.get("authority") == "AUTHENTICATED_PRIMARY"
            for atom in source["neutral_page_v1"]["atoms"]
        ):
            raise _error("terminal source exposes forbidden primary LINE authority")
    return _build_from_validated(source, registry_state=_compiled_registry_state_v1(compiled))


def build_local_accounting_typed_proposal_set_from_registry_v1(
    source_projection_v2: Mapping[str, Any],
    compiled_registry: CompiledLocalAccountingTypedProposalRegistryV1,
) -> dict[str, Any]:
    """Build one page from a registry compiled once for a multi-page sweep."""

    registry_state = _compiled_registry_state_v1(compiled_registry)
    try:
        source = validate_source_evidence_projection_v2(source_projection_v2)
    except (TypeError, ValueError) as error:
        raise _error("source projection failed the exact V2 contract") from error
    if source["terminal"] and any(
        atom.get("kind") == "LINE" and atom.get("authority") == "AUTHENTICATED_PRIMARY"
        for atom in source["neutral_page_v1"]["atoms"]
    ):
        raise _error("terminal source exposes forbidden primary LINE authority")
    return _build_from_validated(source, registry_state=registry_state)


def validate_local_accounting_typed_proposal_set_v1(
    value: Any,
    *,
    source_projection_v2: Mapping[str, Any],
    family_specs: Sequence[FamilySpecV1],
    generator_config: LocalAccountingTypedProposalConfigV1 = (
        DEFAULT_LOCAL_ACCOUNTING_TYPED_PROPOSAL_CONFIG_V1
    ),
) -> dict[str, Any]:
    """Replay and typed-compare the complete artifact; trust no embedded hash."""

    if not isinstance(value, Mapping):
        raise _error("typed proposal artifact must be a mapping")
    expected = build_local_accounting_typed_proposal_set_v1(
        source_projection_v2,
        family_specs,
        generator_config,
    )
    if not same_typed_json_v1(value, expected):
        raise _error("typed proposal artifact disagrees with deterministic replay")
    return canonical_clone_v1(expected)


def validate_local_accounting_typed_proposal_set_from_registry_v1(
    value: Any,
    *,
    source_projection_v2: Mapping[str, Any],
    compiled_registry: CompiledLocalAccountingTypedProposalRegistryV1,
) -> dict[str, Any]:
    """Replay one artifact against an already compiled multi-page registry."""

    if not isinstance(value, Mapping):
        raise _error("typed proposal artifact must be a mapping")
    expected = build_local_accounting_typed_proposal_set_from_registry_v1(
        source_projection_v2,
        compiled_registry,
    )
    if not same_typed_json_v1(value, expected):
        raise _error("typed proposal artifact disagrees with deterministic replay")
    return canonical_clone_v1(expected)
