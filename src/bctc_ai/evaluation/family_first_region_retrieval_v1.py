"""Authenticated region-first retrieval over the sealed family-first OCR sidecar.

The existing OCR query cache is already an immutable, content-referenced
SQLite sidecar with an FTS5 trigram index over the exact VietOCR and accentless
surfaces.  Building another corpus-wide copy for every family would add no
evidence and would multiply both disk use and invalidation work.  This module
therefore executes a schema-neutral query directly against that authenticated
sidecar, constructs only the bounded one-to-three-line occurrences around SQL
hits, and emits one deterministic outcome for every document (including zero
hits).

Retrieval is deliberately not mapping authority.  Exact, accentless, trigram
probe, and bounded-edit channels can only shortlist pages.  A zero hit either
falls back to every page in the document or remains explicitly unresolved; it
can never establish that a financial-statement family is absent.  Likewise, a
cached or self-rehashed receipt is not trusted: public replay always recomputes
it from the live authenticated document store.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import re
import sqlite3
import sys
import unicodedata
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from rapidfuzz.distance import Levenshtein

from bctc_ai.evaluation import family_first_document_evidence_store_v1 as store_v1
from bctc_ai.evaluation import family_first_ocr_query_cache_v1 as cache_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "QUERY_SPEC_FORMAT_VERSION",
    "RECEIPT_FORMAT_VERSION",
    "FamilyFirstRegionRetrievalV1Error",
    "family_first_historical_variant_verification_id_v2",
    "family_first_region_query_spec_id_v1",
    "family_first_region_query_spec_id_v2",
    "retrieve_authenticated_family_first_regions_v1",
    "retrieve_authenticated_family_first_regions_v2",
    "validate_family_first_region_query_spec_v1",
    "validate_family_first_region_query_spec_v2",
    "validate_replayed_authenticated_family_first_region_receipt_v1",
    "validate_replayed_authenticated_family_first_region_receipt_v2",
]


FORMAT_VERSION = "FAMILY_FIRST_REGION_RETRIEVAL_ENGINE_V2"
QUERY_SPEC_FORMAT_VERSION = "FAMILY_FIRST_REGION_QUERY_SPEC_V2"
RECEIPT_FORMAT_VERSION = "FAMILY_FIRST_REGION_RETRIEVAL_RECEIPT_V2"
CLAIM_BOUNDARY = (
    "AUTHENTICATED_IMMUTABLE_SQLITE_EXACT_ACCENTLESS_FTS5_TRIGRAM_AND_"
    "BOUNDED_EDIT_REGION_SHORTLIST_COMPLETE_DOCUMENT_DENOMINATOR_ONLY_NO_"
    "ABSENCE_MAPPING_NUMERIC_ACCOUNTING_SCHEMA_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "absence_authority": False,
    "accounting_authority": False,
    "cache_or_receipt_self_authenticating": False,
    "complete_document_outcome_denominator": True,
    "historical_variant_semantic_assignment_authority": False,
    "historical_variant_support_presence_is_mapping_authority": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "schema_authority": False,
    "shortlist_authority": True,
    "source_database_must_be_authenticated": True,
}
_FAMILY_ID = re.compile(r"^[A-Z][A-Z0-9_]{2,127}$")
_ANCHOR_ID = re.compile(r"^[A-Z][A-Z0-9_]{1,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ANCHOR_ROLES = {"CONTEXT", "HARD_NEGATIVE", "OWNER", "TARGET"}
_ZERO_HIT_POLICIES = {
    "FULL_DOCUMENT_FALLBACK",
}
_QUERY_SPEC_FIELDS = {
    "anchors",
    "family_id",
    "format_version",
    "max_hit_lines",
    "max_selected_pages_per_document",
    "local_required_groups",
    "neighbor_pages_after",
    "neighbor_pages_before",
    "seed_groups",
    "semantic_assignment_adapter_ref",
    "structural_reset_fragments",
    "structural_reset_max_line_ordinal",
    "window_line_span",
    "zero_hit_policy",
}
_ANCHOR_FIELDS = {
    "anchor_id",
    "canonical_alias_id",
    "fts_probes",
    "max_edit_distance",
    "role",
    "surface",
    "verified_historical_variants",
}
_VARIANT_FIELDS = {
    "alias_id",
    "support_refs",
    "surface",
    "verification_ref",
}
_SUPPORT_REF_FIELDS = {"document_id", "physical_page", "sample_ids"}
_CONTENT_REF_FIELDS = {"path", "sha256", "size_bytes"}
_VARIANT_KINDS = {"CANONICAL", "VERIFIED_HISTORICAL_VARIANT"}
_SEED_GROUP_FIELDS = {
    "anchor_ids",
    "group_id",
    "mode",
    "page_relation",
    "priority",
}
_LOCAL_GROUP_FIELDS = _SEED_GROUP_FIELDS - {"priority"}
_GROUP_MODES = {"ALL", "ANY"}
_PAGE_RELATIONS = {"SAME_OR_ADJACENT_PAGE", "SAME_PAGE"}
_FORBIDDEN_ROUTING_FIELDS = {
    "assurance",
    "bank",
    "document_ordinal",
    "filename",
    "page",
    "period",
    "scope",
    "source_path",
    "year",
}
_CHANNEL_ORDER = {
    "EXACT_UNICODE": 0,
    "EXACT_ACCENTLESS": 1,
    "BOUNDED_EDIT": 2,
    "FTS5_TRIGRAM_PROBE": 3,
    "FTS5_RARE_TRIGRAM_SEED": 4,
}
_NON_ALNUM = re.compile(r"[^0-9a-z]+")
_RARE_TRIGRAM_MAX_LINE_FREQUENCY = 2_500
_RARE_TRIGRAM_MAX_PAGE_FREQUENCY = 2_000
_RARE_TRIGRAM_MAX_SELECTED_PER_ANCHOR = 4
_RARE_TRIGRAM_MIN_SELECTED_PER_ANCHOR = 2
_RARE_TRIGRAM_MIN_OVERLAP = 1
_RARE_TRIGRAM_MAX_UNION_HITS = 5_000


class FamilyFirstRegionRetrievalV1Error(RuntimeError):
    """The query, authenticated source, shortlist, or replay receipt drifted."""


def _error(message: str) -> FamilyFirstRegionRetrievalV1Error:
    return FamilyFirstRegionRetrievalV1Error(message)


def _strict_int(value: Any, label: str, *, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise _error(f"{label} drifted")
    return value


def _nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def _accentless(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", _nfc(value).casefold())
    raw = "".join(character for character in decomposed if not unicodedata.combining(character))
    raw = raw.replace("đ", "d")
    return " ".join(raw.split())


def _comparison_key(value: str) -> str:
    """Normalize punctuation only for local scoring, never for source storage."""

    return " ".join(_NON_ALNUM.sub(" ", _accentless(value)).split())


def _comparison_key_from_accentless(value: str) -> str:
    return " ".join(_NON_ALNUM.sub(" ", value.casefold()).split())


def _compiled_anchor(anchor: Mapping[str, Any]) -> dict[str, Any]:
    if "_aliases" in anchor:
        return dict(anchor)
    aliases = []
    for alias in _anchor_aliases(anchor):
        probe_surfaces = (
            anchor["fts_probes"] if alias["kind"] == "CANONICAL" else [alias["surface"]]
        )
        aliases.append(
            {
                **alias,
                "_probe_keys": tuple(_comparison_key(item) for item in probe_surfaces),
                "_surface_key": _comparison_key(alias["surface"]),
                "_surface_nfc_casefold": _nfc(alias["surface"]).casefold(),
            }
        )
    surface_key = aliases[0]["_surface_key"]
    probe_keys = aliases[0]["_probe_keys"]
    tokens = {
        token
        for alias in aliases
        for value in (alias["_surface_key"], *alias["_probe_keys"])
        for token in value.split()
        if len(token) >= 4
    }
    if not tokens:
        tokens = {
            token
            for alias in aliases
            for value in (alias["_surface_key"], *alias["_probe_keys"])
            for token in value.split()
            if len(token) >= 3
        }
    return {
        **anchor,
        "_aliases": tuple(aliases),
        "_probe_keys": probe_keys,
        "_surface_key": surface_key,
        "_surface_nfc_casefold": _nfc(anchor["surface"]).casefold(),
        "_trigger_tokens": frozenset(tokens),
    }


def _enriched_row(value: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(value)
    row["_accentless_key"] = _comparison_key_from_accentless(row["accentless_text"])
    row["_unicode_nfc_casefold"] = _nfc(row["vietocr_text"]).casefold()
    row["_tokens"] = frozenset(row["_accentless_key"].split())
    return row


def _string_list(
    value: Any,
    label: str,
    *,
    minimum_length: int = 1,
    allow_empty: bool = False,
) -> list[str]:
    if (
        type(value) is not list
        or (not value and not allow_empty)
        or any(type(item) is not str or len(item.strip()) < minimum_length for item in value)
    ):
        raise _error(f"{label} drifted")
    result = [" ".join(item.split()) for item in value]
    if result != sorted(set(result)):
        raise _error(f"{label} must be sorted and unique")
    return result


def _support_ref(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _SUPPORT_REF_FIELDS:
        raise _error("historical alias support reference fields drifted")
    document_id = value["document_id"]
    physical_page = value["physical_page"]
    sample_ids = value["sample_ids"]
    if (
        type(document_id) is not str
        or not document_id
        or type(physical_page) is not int
        or physical_page <= 0
        or type(sample_ids) is not list
        or not sample_ids
        or len(sample_ids) > 3
        or len(sample_ids) != len(set(sample_ids))
        or any(type(item) is not str or not item for item in sample_ids)
    ):
        raise _error("historical alias support reference identity drifted")
    return {
        "document_id": document_id,
        "physical_page": physical_page,
        "sample_ids": list(sample_ids),
    }


def _content_ref(value: Any, label: str) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _CONTENT_REF_FIELDS
        or type(value["path"]) is not str
        or not value["path"]
        or Path(value["path"]).is_absolute()
        or ".." in Path(value["path"]).parts
        or type(value["sha256"]) is not str
        or _SHA256.fullmatch(value["sha256"]) is None
        or type(value["size_bytes"]) is not int
        or value["size_bytes"] <= 0
    ):
        raise _error(f"{label} content reference drifted")
    return dict(value)


def family_first_historical_variant_verification_id_v2(
    *,
    anchor_id: str,
    alias_id: str,
    surface: str,
    support_refs: Any,
) -> str:
    """Bind a reviewed historical alias to one semantic anchor and evidence set."""

    if (
        type(anchor_id) is not str
        or _ANCHOR_ID.fullmatch(anchor_id) is None
        or type(alias_id) is not str
        or _ANCHOR_ID.fullmatch(alias_id) is None
        or type(surface) is not str
        or len(surface.strip()) < 3
        or surface != " ".join(surface.split())
        or type(support_refs) is not list
        or not support_refs
    ):
        raise _error("historical alias verification material drifted")
    supports = [_support_ref(item) for item in support_refs]
    if supports != sorted(
        supports,
        key=lambda item: (
            item["document_id"],
            item["physical_page"],
            item["sample_ids"],
        ),
    ):
        raise _error("historical alias support references must be sorted")
    material = {
        "alias_id": alias_id,
        "anchor_id": anchor_id,
        "kind": "VERIFIED_HISTORICAL_VARIANT",
        "support_refs": supports,
        "surface": surface,
    }
    return "fffrrv2:variant-verification:" + canonical_json_sha256_v1(material)


def _historical_variant(value: Any, anchor_id: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _VARIANT_FIELDS:
        raise _error("historical alias fields drifted")
    alias_id = value["alias_id"]
    surface = value["surface"]
    support_refs = value["support_refs"]
    if (
        type(alias_id) is not str
        or _ANCHOR_ID.fullmatch(alias_id) is None
        or type(surface) is not str
        or len(surface.strip()) < 3
        or surface != " ".join(surface.split())
        or type(support_refs) is not list
        or not support_refs
    ):
        raise _error("historical alias identity drifted")
    supports = [_support_ref(item) for item in support_refs]
    if supports != sorted(
        supports,
        key=lambda item: (
            item["document_id"],
            item["physical_page"],
            item["sample_ids"],
        ),
    ):
        raise _error("historical alias support references must be sorted")
    expected = family_first_historical_variant_verification_id_v2(
        anchor_id=anchor_id,
        alias_id=alias_id,
        surface=surface,
        support_refs=supports,
    )
    if value["verification_ref"] != expected:
        raise _error("historical alias verification reference does not bind its anchor")
    return {
        "alias_id": alias_id,
        "support_refs": supports,
        "surface": surface,
        "verification_ref": expected,
    }


def _anchor(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _ANCHOR_FIELDS:
        raise _error("region query anchor fields drifted")
    anchor_id = value["anchor_id"]
    canonical_alias_id = value["canonical_alias_id"]
    role = value["role"]
    surface = value["surface"]
    if (
        type(anchor_id) is not str
        or _ANCHOR_ID.fullmatch(anchor_id) is None
        or type(canonical_alias_id) is not str
        or _ANCHOR_ID.fullmatch(canonical_alias_id) is None
        or role not in _ANCHOR_ROLES
        or type(surface) is not str
        or len(surface.strip()) < 3
        or surface != " ".join(surface.split())
    ):
        raise _error("region query anchor identity drifted")
    probes = _string_list(value["fts_probes"], "region query FTS probes", minimum_length=3)
    distance = _strict_int(
        value["max_edit_distance"],
        "region query bounded edit distance",
        minimum=0,
        maximum=2,
    )
    # Every bounded edit decision must be reached through at least one explicit
    # SQL probe.  The probe may be a stable rare substring of a longer label.
    if distance and not probes:
        raise _error("bounded edit anchor has no SQL retrieval probe")
    variants_raw = value["verified_historical_variants"]
    if type(variants_raw) is not list:
        raise _error("historical aliases must be one sorted list")
    variants = [_historical_variant(item, anchor_id) for item in variants_raw]
    alias_ids = [canonical_alias_id, *(item["alias_id"] for item in variants)]
    if alias_ids != [canonical_alias_id, *sorted(alias_ids[1:])] or len(alias_ids) != len(
        set(alias_ids)
    ):
        raise _error("anchor alias ids must be sorted and unique")
    return {
        "anchor_id": anchor_id,
        "canonical_alias_id": canonical_alias_id,
        "fts_probes": probes,
        "max_edit_distance": distance,
        "role": role,
        "surface": surface,
        "verified_historical_variants": variants,
    }


def _anchor_aliases(anchor: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "alias_id": anchor["canonical_alias_id"],
            "kind": "CANONICAL",
            "support_refs": [],
            "surface": anchor["surface"],
            "verification_ref": None,
        },
        *[
            {
                **variant,
                "kind": "VERIFIED_HISTORICAL_VARIANT",
            }
            for variant in anchor["verified_historical_variants"]
        ],
    ]


def _group(
    value: Any,
    *,
    known_anchor_ids: set[str],
    seed: bool,
) -> dict[str, Any]:
    fields = _SEED_GROUP_FIELDS if seed else _LOCAL_GROUP_FIELDS
    label = "seed" if seed else "local-required"
    if type(value) is not dict or set(value) != fields:
        raise _error(f"region query {label} group fields drifted")
    group_id = value["group_id"]
    anchor_ids = value["anchor_ids"]
    if (
        type(group_id) is not str
        or _ANCHOR_ID.fullmatch(group_id) is None
        or type(anchor_ids) is not list
        or not anchor_ids
        or anchor_ids != sorted(set(anchor_ids))
        or any(type(item) is not str or item not in known_anchor_ids for item in anchor_ids)
        or value["mode"] not in _GROUP_MODES
        or value["page_relation"] not in _PAGE_RELATIONS
        or (value["mode"] == "ALL" and len(anchor_ids) < 2)
    ):
        raise _error(f"region query {label} group identity drifted")
    result = {
        "anchor_ids": list(anchor_ids),
        "group_id": group_id,
        "mode": value["mode"],
        "page_relation": value["page_relation"],
    }
    if seed:
        result["priority"] = _strict_int(
            value["priority"],
            "region query seed priority",
            minimum=1,
            maximum=100,
        )
    return result


def validate_family_first_region_query_spec_v1(value: Any) -> dict[str, Any]:
    """Validate one bank/page/period-blind, deterministic retrieval contract."""

    if type(value) is not dict:
        raise _error("region query spec fields drifted")
    if set(value) & _FORBIDDEN_ROUTING_FIELDS:
        raise _error("filing-specific routing fields are forbidden")
    if set(value) != _QUERY_SPEC_FIELDS:
        raise _error("region query spec fields drifted")
    family_id = value["family_id"]
    if (
        value["format_version"] != QUERY_SPEC_FORMAT_VERSION
        or type(family_id) is not str
        or _FAMILY_ID.fullmatch(family_id) is None
        or value["zero_hit_policy"] not in _ZERO_HIT_POLICIES
    ):
        raise _error("region query spec identity drifted")
    anchors_raw = value["anchors"]
    if type(anchors_raw) is not list or not anchors_raw:
        raise _error("region query must contain at least one anchor")
    anchors = [_anchor(item) for item in anchors_raw]
    ids = [item["anchor_id"] for item in anchors]
    if ids != sorted(set(ids)):
        raise _error("region query anchor ids must be sorted and unique")
    alias_owners: dict[str, tuple[str, str]] = {}
    alias_ids = []
    for anchor in anchors:
        for alias in _anchor_aliases(anchor):
            alias_ids.append(alias["alias_id"])
            normalized = _comparison_key(alias["surface"])
            prior = alias_owners.get(normalized)
            current = (anchor["anchor_id"], _nfc(alias["surface"]))
            if prior is not None and prior != current:
                raise _error("accentless alias collision is ambiguous across semantic anchors")
            alias_owners[normalized] = current
    if len(alias_ids) != len(set(alias_ids)):
        raise _error("region query alias ids must be globally unique")
    if not any(item["role"] in {"OWNER", "TARGET"} for item in anchors):
        raise _error("region query needs an owner or target anchor")
    known_ids = set(ids)
    seed_groups_raw = value["seed_groups"]
    local_groups_raw = value["local_required_groups"]
    if type(seed_groups_raw) is not list or not seed_groups_raw:
        raise _error("region query needs at least one declarative seed group")
    if type(local_groups_raw) is not list:
        raise _error("region query local-required groups drifted")
    seed_groups = [_group(item, known_anchor_ids=known_ids, seed=True) for item in seed_groups_raw]
    local_groups = [
        _group(item, known_anchor_ids=known_ids, seed=False) for item in local_groups_raw
    ]
    if [item["group_id"] for item in seed_groups] != sorted(
        {item["group_id"] for item in seed_groups}
    ) or [item["group_id"] for item in local_groups] != sorted(
        {item["group_id"] for item in local_groups}
    ):
        raise _error("region query group ids must be sorted and unique")
    anchors_by_id = {item["anchor_id"]: item for item in anchors}
    for group in seed_groups:
        if group["mode"] == "ANY" and not any(
            anchors_by_id[anchor_id]["role"] in {"OWNER", "TARGET"}
            for anchor_id in group["anchor_ids"]
        ):
            raise _error("single-channel seed groups require an owner or target anchor")
    normalized_surfaces = [_comparison_key(item["surface"]) for item in anchors]
    if any(len(item) < 3 for item in normalized_surfaces):
        raise _error("region query normalized anchor is too short")
    adapter_ref_raw = value["semantic_assignment_adapter_ref"]
    has_historical_variants = any(anchor["verified_historical_variants"] for anchor in anchors)
    if adapter_ref_raw is None:
        if has_historical_variants:
            raise _error("historical aliases require a semantic-assignment adapter ref")
        adapter_ref = None
    else:
        adapter_ref = _content_ref(
            adapter_ref_raw,
            "historical alias semantic-assignment adapter",
        )
    return canonical_clone_v1(
        {
            "anchors": anchors,
            "family_id": family_id,
            "format_version": QUERY_SPEC_FORMAT_VERSION,
            "local_required_groups": local_groups,
            "max_hit_lines": _strict_int(
                value["max_hit_lines"],
                "region query hit-line budget",
                minimum=1,
                maximum=100_000,
            ),
            "max_selected_pages_per_document": _strict_int(
                value["max_selected_pages_per_document"],
                "region query selected-page budget",
                minimum=1,
                maximum=10_000,
            ),
            "neighbor_pages_after": _strict_int(
                value["neighbor_pages_after"],
                "region query following-page radius",
                minimum=0,
                maximum=5,
            ),
            "neighbor_pages_before": _strict_int(
                value["neighbor_pages_before"],
                "region query preceding-page radius",
                minimum=0,
                maximum=5,
            ),
            "seed_groups": seed_groups,
            "semantic_assignment_adapter_ref": adapter_ref,
            "structural_reset_fragments": _string_list(
                value["structural_reset_fragments"],
                "region query structural reset fragments",
                minimum_length=3,
                allow_empty=True,
            ),
            "structural_reset_max_line_ordinal": _strict_int(
                value["structural_reset_max_line_ordinal"],
                "region query structural reset line boundary",
                minimum=0,
                maximum=5,
            ),
            "window_line_span": _strict_int(
                value["window_line_span"],
                "region query line-window span",
                minimum=1,
                maximum=3,
            ),
            "zero_hit_policy": value["zero_hit_policy"],
        }
    )


def family_first_region_query_spec_id_v1(value: Any) -> str:
    spec = validate_family_first_region_query_spec_v1(value)
    return "fffrrv2:query:" + canonical_json_sha256_v1(spec)


def _fts_phrase(value: str) -> str:
    normalized = " ".join(value.split())
    if len(normalized) < 3:
        raise _error("FTS5 trigram probe is too short")
    return '"' + normalized.replace('"', '""') + '"'


def _fts_query(spec: Mapping[str, Any]) -> str:
    fragments = set()
    for anchor in spec["anchors"]:
        for alias in _anchor_aliases(anchor):
            fragments.add(_nfc(alias["surface"]))
            fragments.add(_accentless(alias["surface"]))
        for probe in anchor["fts_probes"]:
            fragments.add(_nfc(probe))
            fragments.add(_accentless(probe))
    return " OR ".join(_fts_phrase(item) for item in sorted(fragments) if len(item) >= 3)


def _anchor_fts_query(anchor: Mapping[str, Any]) -> str:
    return _fts_query({"anchors": [anchor]})


def _accentless_character_trigrams(value: str) -> list[tuple[str, int]]:
    """Return unique normalized 3-grams with their first stable position."""

    surface = _comparison_key(value)
    result: dict[str, int] = {}
    for position in range(len(surface) - 2):
        gram = surface[position : position + 3]
        # Whitespace-bearing grams are both overly common in financial text
        # and are altered by FTS query whitespace normalization.  Compact
        # alphanumeric trigrams retain the intended OCR-error recovery signal.
        if not gram.isalnum():
            continue
        result.setdefault(gram, position)
    return sorted(result.items())


def _rare_trigram_line_frequencies(
    connection: Any,
    anchors: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    grams = sorted(
        {
            gram
            for anchor in anchors
            for gram, _position in _accentless_character_trigrams(anchor["surface"])
        }
    )
    if not grams:
        return {}
    # TEMP is intentionally untracked and connection-scoped.  The immutable
    # authenticated main database remains read-only; fts5vocab reads the pinned
    # main.line_search index and avoids one aggregate scan per trigram.
    connection.execute(
        "CREATE VIRTUAL TABLE temp.fffrrv2_line_vocab USING fts5vocab(main, line_search, 'row')"
    )
    placeholders = ",".join("?" for _gram in grams)
    rows = connection.execute(
        f"SELECT term, doc FROM temp.fffrrv2_line_vocab "
        f"WHERE term IN ({placeholders}) ORDER BY term",
        tuple(grams),
    ).fetchall()
    result = {row["term"]: row["doc"] for row in rows}
    if any(
        type(term) is not str or type(count) is not int or count <= 0
        for term, count in result.items()
    ):
        raise _error("FTS5 vocabulary line-frequency axis drifted")
    return result


def _rare_trigram_seed_plan(
    anchor: Mapping[str, Any],
    line_frequencies: Mapping[str, int],
) -> dict[str, Any]:
    """Choose only bounded low-frequency seed grams from one declared alias.

    Individual 3-grams are never mapping evidence.  They are a deterministic
    recall channel for the case where one OCR edit prevents every exact FTS
    phrase from firing.  The later one-to-three-line window must still prove a
    bounded edit against the complete alias.
    """

    candidates = []
    for gram, position in _accentless_character_trigrams(anchor["surface"]):
        line_frequency = line_frequencies.get(gram, 0)
        candidates.append(
            {
                "document_frequency": 0,
                "gram": gram,
                "line_frequency": line_frequency,
                "page_frequency": 0,
                "position": position,
            }
        )
    eligible = [
        item
        for item in candidates
        if 0 < item["line_frequency"] <= _RARE_TRIGRAM_MAX_LINE_FREQUENCY
    ]
    eligible.sort(
        key=lambda item: (
            item["line_frequency"],
            item["gram"],
        )
    )
    # Spread selected grams so one substitution cannot destroy every trigger.
    selected = []
    for item in eligible:
        if all(abs(item["position"] - prior["position"]) >= 3 for prior in selected):
            selected.append(item)
        if len(selected) == _RARE_TRIGRAM_MAX_SELECTED_PER_ANCHOR:
            break
    if len(selected) < _RARE_TRIGRAM_MIN_SELECTED_PER_ANCHOR:
        selected = []
    selected_public = [
        {
            "document_frequency": item["document_frequency"],
            "gram": item["gram"],
            "line_frequency": item["line_frequency"],
            "page_frequency": item["page_frequency"],
            "position": item["position"],
        }
        for item in selected
    ]
    material = {
        "alias_id": anchor["canonical_alias_id"],
        "anchor_id": anchor["anchor_id"],
        "candidate_gram_count": len(candidates),
        "channel": "FTS5_RARE_TRIGRAM_SEED",
        "minimum_overlap_count": _RARE_TRIGRAM_MIN_OVERLAP,
        "policy": {
            "max_line_frequency": _RARE_TRIGRAM_MAX_LINE_FREQUENCY,
            "max_page_frequency": _RARE_TRIGRAM_MAX_PAGE_FREQUENCY,
            "max_selected_grams": _RARE_TRIGRAM_MAX_SELECTED_PER_ANCHOR,
            "max_union_hit_lines": _RARE_TRIGRAM_MAX_UNION_HITS,
            "min_selected_grams": _RARE_TRIGRAM_MIN_SELECTED_PER_ANCHOR,
        },
        "selected_grams": selected_public,
        "status": "SELECTED" if selected_public else "NO_DF_BOUNDED_GRAM_SET",
        "union_hit_line_count": 0,
    }
    return material


def _finalize_rare_trigram_seed_plan(
    plan: dict[str, Any],
    hit_context_rows: Sequence[Mapping[str, Any]],
) -> None:
    hit_rows: dict[tuple[int, int, int], Mapping[str, Any]] = {}
    for row in hit_context_rows:
        if (
            row["context_physical_page"] == row["physical_page"]
            and row["line_ordinal"] == row["hit_line_ordinal"]
        ):
            locator = (
                row["document_ordinal"],
                row["physical_page"],
                row["line_ordinal"],
            )
            hit_rows[locator] = row
    retained = []
    for item in plan["selected_grams"]:
        matched = [
            (locator, row)
            for locator, row in hit_rows.items()
            if item["gram"] in _comparison_key_from_accentless(row["accentless_text"])
        ]
        item["document_frequency"] = len({locator[0] for locator, _row in matched})
        item["page_frequency"] = len({(locator[0], locator[1]) for locator, _row in matched})
        observed_line_frequency = len(matched)
        if observed_line_frequency != item["line_frequency"]:
            raise _error("FTS5 vocabulary and hydrated trigram line frequencies differ")
        if item["page_frequency"] <= _RARE_TRIGRAM_MAX_PAGE_FREQUENCY:
            retained.append(item)
    plan["selected_grams"] = retained
    if len(retained) < _RARE_TRIGRAM_MIN_SELECTED_PER_ANCHOR:
        plan["selected_grams"] = []
        plan["status"] = "NO_DF_BOUNDED_GRAM_SET"


def _rare_trigram_query(plan: Mapping[str, Any]) -> str | None:
    grams = [item["gram"] for item in plan["selected_grams"]]
    if not grams:
        return None
    return " OR ".join(_fts_phrase(gram) for gram in grams)


def _bounded_substring_distance(text: str, pattern: str, maximum: int) -> int | None:
    """Return a proved edit distance over bounded token-aligned substrings.

    Comparing every character start made a broad OCR probe quadratic in the
    Python layer.  Financial-statement labels are word sequences, so candidates
    are limited to contiguous token spans whose token and character lengths can
    still satisfy the declared edit bound.  A missing OCR space remains one
    deletion (for example ``chovay`` versus ``cho vay``).
    """

    if maximum <= 0 or not text or not pattern:
        return None
    if pattern in text:
        return 0
    text_tokens = text.split()
    pattern_tokens = pattern.split()
    low = max(1, len(pattern_tokens) - maximum)
    high = min(len(text_tokens), len(pattern_tokens) + maximum)
    best: int | None = None
    for token_count in range(low, high + 1):
        for start in range(0, len(text_tokens) - token_count + 1):
            candidate = " ".join(text_tokens[start : start + token_count])
            if abs(len(candidate) - len(pattern)) > maximum:
                continue
            distance = Levenshtein.distance(
                pattern,
                candidate,
                score_cutoff=maximum,
            )
            if distance <= maximum and (best is None or distance < best):
                best = distance
                if best == 1:
                    return best
    return best


def _bbox_union(rows: Sequence[Mapping[str, Any]]) -> list[int]:
    return [
        min(row["bbox_left"] for row in rows),
        min(row["bbox_top"] for row in rows),
        max(row["bbox_right"] for row in rows),
        max(row["bbox_bottom"] for row in rows),
    ]


def _matching_channels(
    anchor: Mapping[str, Any],
    unicode_text: str,
    accentless_text: str,
    *,
    unicode_nfc_casefold: str | None = None,
    accentless_key: str | None = None,
    rare_trigram_evidence: Mapping[str, Any] | None = None,
) -> tuple[list[str], int | None, dict[str, Any] | None]:
    compiled = _compiled_anchor(anchor)
    text_nfc = unicode_nfc_casefold or _nfc(unicode_text).casefold()
    text_key = accentless_key or _comparison_key(accentless_text)
    matches = []
    for alias in compiled["_aliases"]:
        channels = []
        if alias["_surface_nfc_casefold"] in text_nfc:
            channels.append("EXACT_UNICODE")
        if alias["_surface_key"] in text_key:
            channels.append("EXACT_ACCENTLESS")
        probe_hit = any(probe in text_key for probe in alias["_probe_keys"])
        if probe_hit:
            channels.append("FTS5_TRIGRAM_PROBE")
        rare_hit = (
            rare_trigram_evidence is not None
            and rare_trigram_evidence["alias_id"] == alias["alias_id"]
            and rare_trigram_evidence["overlap_count"]
            >= rare_trigram_evidence["minimum_overlap_count"]
        )
        if rare_hit:
            channels.append("FTS5_RARE_TRIGRAM_SEED")
        if "EXACT_UNICODE" in channels or "EXACT_ACCENTLESS" in channels:
            distance = 0
        elif probe_hit or rare_hit:
            distance = _bounded_substring_distance(
                text_key,
                alias["_surface_key"],
                anchor["max_edit_distance"],
            )
            if distance is not None and distance > 0:
                channels.append("BOUNDED_EDIT")
        else:
            distance = None
        channels = sorted(set(channels), key=_CHANNEL_ORDER.__getitem__)
        if not _channels_prove_anchor(channels):
            continue
        public_alias = {
            key: alias[key]
            for key in (
                "alias_id",
                "kind",
                "support_refs",
                "surface",
                "verification_ref",
            )
        }
        matches.append((channels, distance, public_alias))
    if not matches:
        return [], None, None
    channels, distance, matched_alias = min(
        matches,
        key=lambda item: (
            min(_CHANNEL_ORDER[channel] for channel in item[0]),
            item[1] if item[1] is not None else 999,
            item[2]["kind"] != "CANONICAL",
            item[2]["alias_id"],
        ),
    )
    return channels, distance, matched_alias


def _channels_prove_anchor(channels: Sequence[str]) -> bool:
    return bool({"EXACT_UNICODE", "EXACT_ACCENTLESS", "BOUNDED_EDIT"} & set(channels))


def _window_is_contiguous(
    rows: Sequence[Mapping[str, Any]], reset_pages: set[tuple[int, int]]
) -> bool:
    for previous, following in zip(rows, rows[1:], strict=False):
        if previous["physical_page"] == following["physical_page"]:
            if following["line_ordinal"] != previous["line_ordinal"] + 1:
                return False
            continue
        if (
            following["physical_page"] != previous["physical_page"] + 1
            or previous["line_ordinal"] != previous["page_line_count"] - 1
            or following["line_ordinal"] != 0
            or (following["document_ordinal"], following["physical_page"]) in reset_pages
        ):
            return False
    return True


def _window_candidates(
    rows: Sequence[Mapping[str, Any]],
    hit_locator: tuple[int, int],
    maximum_span: int,
    reset_pages: set[tuple[int, int]],
) -> list[list[Mapping[str, Any]]]:
    ordered = sorted(rows, key=lambda row: (row["physical_page"], row["line_ordinal"]))
    hit_indices = [
        index
        for index, row in enumerate(ordered)
        if (row["physical_page"], row["line_ordinal"]) == hit_locator
    ]
    if len(hit_indices) != 1:
        raise _error("retrieval hit locator is absent or duplicated in its local context")
    hit_index = hit_indices[0]
    windows = []
    for span in range(1, maximum_span + 1):
        for start in range(hit_index - span + 1, hit_index + 1):
            if start < 0 or start + span > len(ordered):
                continue
            window = ordered[start : start + span]
            if _window_is_contiguous(window, reset_pages):
                windows.append(window)
    return windows


def _occurrence_fragments(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: list[list[Mapping[str, Any]]] = []
    for row in rows:
        if not grouped or grouped[-1][-1]["physical_page"] != row["physical_page"]:
            grouped.append([row])
        else:
            grouped[-1].append(row)
    return [
        {
            "accentless_text": " ".join(row["accentless_text"] for row in fragment),
            "bbox": _bbox_union(fragment),
            "end_line_ordinal": fragment[-1]["line_ordinal"],
            "physical_page": fragment[0]["physical_page"],
            "sample_ids": [row["sample_id"] for row in fragment],
            "start_line_ordinal": fragment[0]["line_ordinal"],
            "vietocr_text": " ".join(row["vietocr_text"] for row in fragment),
        }
        for fragment in grouped
    ]


def _occurrence_from_window(
    anchor: Mapping[str, Any],
    window: Sequence[Mapping[str, Any]],
    unicode_text: str,
    accentless_text: str,
    channels: Sequence[str],
    edit_distance: int | None,
    matched_alias: Mapping[str, Any],
    *,
    rare_trigram_evidence: Mapping[str, Any] | None = None,
    stage: str,
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    document_ordinal = window[0]["document_ordinal"]
    fragments = _occurrence_fragments(window)
    start_locator = {
        "line_ordinal": window[0]["line_ordinal"],
        "physical_page": window[0]["physical_page"],
    }
    end_locator = {
        "line_ordinal": window[-1]["line_ordinal"],
        "physical_page": window[-1]["physical_page"],
    }
    key = (
        document_ordinal,
        start_locator["physical_page"],
        start_locator["line_ordinal"],
        end_locator["physical_page"],
        end_locator["line_ordinal"],
        anchor["anchor_id"],
    )
    material = {
        "anchor_id": anchor["anchor_id"],
        "anchor_role": anchor["role"],
        "channels": list(channels),
        "document_ordinal": document_ordinal,
        "edit_distance": edit_distance,
        "end_locator": end_locator,
        "fragments": fragments,
        "joined_accentless_text": _accentless(accentless_text),
        "joined_vietocr_text": unicode_text,
        "matched_alias_id": matched_alias["alias_id"],
        "matched_alias_kind": matched_alias["kind"],
        "matched_alias_provenance": {
            "support_refs": canonical_clone_v1(matched_alias["support_refs"]),
            "support_evidence_verified": (
                True if matched_alias["kind"] == "VERIFIED_HISTORICAL_VARIANT" else None
            ),
            "verification_ref": matched_alias["verification_ref"],
        },
        "matched_alias_surface": matched_alias["surface"],
        "rare_trigram_evidence": (
            canonical_clone_v1(rare_trigram_evidence) if rare_trigram_evidence is not None else None
        ),
        "stage": stage,
        "start_locator": start_locator,
    }
    return key, {
        **material,
        "occurrence_id": "fffrrv2:occurrence:" + canonical_json_sha256_v1(material),
    }


def _occurrences(
    spec: Mapping[str, Any],
    hit_context_rows: Sequence[Mapping[str, Any]],
    reset_pages: set[tuple[int, int]],
    *,
    rare_trigram_plan: Mapping[str, Any] | None = None,
    stage: str = "GLOBAL_FTS5_SEED",
) -> list[dict[str, Any]]:
    contexts: dict[tuple[int, int, int], dict[tuple[int, int], Mapping[str, Any]]] = {}
    for row in hit_context_rows:
        key = (row["document_ordinal"], row["physical_page"], row["hit_line_ordinal"])
        locator = (row["context_physical_page"], row["line_ordinal"])
        context_row = dict(row)
        context_row["physical_page"] = context_row.pop("context_physical_page")
        contexts.setdefault(key, {})[locator] = _enriched_row(context_row)
    deduplicated: dict[tuple[Any, ...], dict[str, Any]] = {}
    for (_document_ordinal, hit_page, hit_ordinal), local in sorted(contexts.items()):
        rows = [local[item] for item in sorted(local)]
        windows = [
            (
                window,
                " ".join(row["vietocr_text"] for row in window),
                " ".join(row["accentless_text"] for row in window),
                " ".join(row["_unicode_nfc_casefold"] for row in window),
                " ".join(row["_accentless_key"] for row in window),
            )
            for window in _window_candidates(
                rows,
                (hit_page, hit_ordinal),
                spec["window_line_span"],
                reset_pages,
            )
        ]
        for raw_anchor in spec["anchors"]:
            anchor = _compiled_anchor(raw_anchor)
            matched_windows = []
            for (
                window,
                unicode_text,
                accentless_text,
                unicode_key,
                accentless_key,
            ) in windows:
                rare_evidence = None
                if rare_trigram_plan is not None:
                    selected_grams = [item["gram"] for item in rare_trigram_plan["selected_grams"]]
                    observed_grams = sorted(
                        gram for gram in selected_grams if gram in accentless_key
                    )
                    rare_evidence = {
                        "alias_id": rare_trigram_plan["alias_id"],
                        "minimum_overlap_count": rare_trigram_plan["minimum_overlap_count"],
                        "observed_grams": observed_grams,
                        "overlap_count": len(observed_grams),
                        "selected_grams": selected_grams,
                    }
                channels, edit_distance, matched_alias = _matching_channels(
                    anchor,
                    unicode_text,
                    accentless_text,
                    unicode_nfc_casefold=unicode_key,
                    accentless_key=accentless_key,
                    rare_trigram_evidence=rare_evidence,
                )
                if not _channels_prove_anchor(channels):
                    continue
                if matched_alias is None:
                    raise _error("proved anchor match lost its alias provenance")
                matched_windows.append(
                    (
                        window,
                        unicode_text,
                        accentless_text,
                        channels,
                        edit_distance,
                        matched_alias,
                        rare_evidence,
                    )
                )
            if not matched_windows:
                continue
            (
                window,
                unicode_text,
                accentless_text,
                channels,
                edit_distance,
                matched_alias,
                rare_evidence,
            ) = min(
                matched_windows,
                key=lambda item: (
                    min(_CHANNEL_ORDER[channel] for channel in item[3]),
                    len(item[0]),
                    item[0][0]["physical_page"],
                    item[0][0]["line_ordinal"],
                ),
            )
            key, occurrence = _occurrence_from_window(
                anchor,
                window,
                unicode_text,
                accentless_text,
                channels,
                edit_distance,
                matched_alias,
                rare_trigram_evidence=rare_evidence,
                stage=stage,
            )
            prior = deduplicated.get(key)
            if prior is None or len(occurrence["channels"]) > len(prior["channels"]):
                deduplicated[key] = occurrence
    return sorted(
        deduplicated.values(),
        key=lambda item: (
            item["document_ordinal"],
            item["start_locator"]["physical_page"],
            item["start_locator"]["line_ordinal"],
            item["end_locator"]["physical_page"],
            item["end_locator"]["line_ordinal"],
            item["anchor_id"],
        ),
    )


def _verify_semantic_assignment_adapter_ref(
    state: Any,
    spec: Mapping[str, Any],
) -> None:
    reference = spec["semantic_assignment_adapter_ref"]
    if reference is None:
        return
    path = state.root / reference["path"]
    payload = store_v1._stable_bytes(path, "historical alias semantic-assignment adapter")
    if (
        len(payload) != reference["size_bytes"]
        or hashlib.sha256(payload).hexdigest() != reference["sha256"]
    ):
        raise _error("historical alias semantic-assignment adapter content drifted")


def _verify_historical_variant_supports(
    connection: Any,
    spec: Mapping[str, Any],
) -> list[dict[str, Any]]:
    documents = {
        row["document_id"]: row["document_ordinal"]
        for row in connection.execute(
            "SELECT document_id, document_ordinal FROM documents ORDER BY document_ordinal"
        ).fetchall()
    }
    results = []
    for anchor in spec["anchors"]:
        for variant in anchor["verified_historical_variants"]:
            observed_supports = []
            for support in variant["support_refs"]:
                document_ordinal = documents.get(support["document_id"])
                if document_ordinal is None:
                    raise _error("historical alias support document is absent")
                placeholders = ",".join("?" for _sample_id in support["sample_ids"])
                rows = connection.execute(
                    "SELECT sample_id, document_ordinal, physical_page, line_ordinal, "
                    "bbox_left, bbox_top, bbox_right, bbox_bottom, "
                    "vietocr_text, accentless_text FROM lines "
                    f"WHERE sample_id IN ({placeholders}) "
                    "ORDER BY document_ordinal, physical_page, line_ordinal",
                    tuple(support["sample_ids"]),
                ).fetchall()
                if (
                    len(rows) != len(support["sample_ids"])
                    or [row["sample_id"] for row in rows] != support["sample_ids"]
                    or any(
                        row["document_ordinal"] != document_ordinal
                        or row["physical_page"] != support["physical_page"]
                        for row in rows
                    )
                    or any(
                        following["line_ordinal"] != previous["line_ordinal"] + 1
                        for previous, following in zip(rows, rows[1:], strict=False)
                    )
                ):
                    raise _error("historical alias support is not one bound 1-3 line window")
                joined_raw = " ".join(row["vietocr_text"] for row in rows)
                joined_accentless = " ".join(row["accentless_text"] for row in rows)
                channels = []
                if _nfc(variant["surface"]).casefold() in _nfc(joined_raw).casefold():
                    channels.append("EXACT_UNICODE")
                if _comparison_key(variant["surface"]) in _comparison_key(joined_accentless):
                    channels.append("EXACT_ACCENTLESS")
                if not channels:
                    raise _error("historical alias surface is absent from its support window")
                observed_supports.append(
                    {
                        "channels": channels,
                        "document_id": support["document_id"],
                        "joined_accentless_text": _accentless(joined_accentless),
                        "joined_vietocr_text": joined_raw,
                        "observed_locators": [
                            {
                                "bbox": [
                                    row["bbox_left"],
                                    row["bbox_top"],
                                    row["bbox_right"],
                                    row["bbox_bottom"],
                                ],
                                "line_ordinal": row["line_ordinal"],
                                "physical_page": row["physical_page"],
                                "sample_id": row["sample_id"],
                            }
                            for row in rows
                        ],
                        "physical_page": support["physical_page"],
                    }
                )
            results.append(
                {
                    "alias_id": variant["alias_id"],
                    "anchor_id": anchor["anchor_id"],
                    "observed_supports": observed_supports,
                    "semantic_assignment_authority": False,
                    "support_evidence_verified": True,
                    "verification_ref": variant["verification_ref"],
                }
            )
    return results


def _source_documents(connection: Any, state: Any) -> list[dict[str, Any]]:
    rows = [
        dict(row) for row in connection.execute("SELECT * FROM documents ORDER BY document_ordinal")
    ]
    packets = state.manifest["documents"]
    if len(rows) != len(packets) or len(rows) != state.manifest["metrics"]["document_count"]:
        raise _error("retrieval source document denominator drifted")
    for ordinal, (row, packet) in enumerate(zip(rows, packets, strict=True), 1):
        if (
            row["document_ordinal"] != ordinal
            or packet["document_ordinal"] != ordinal
            or row["document_id"] != packet["document_id"]
            or row["page_count"] != packet["page_count"]
            or row["line_count"] != packet["line_count"]
        ):
            raise _error("retrieval source document/packet axis drifted")
    return rows


def _hit_context_rows(
    connection: Any,
    query: str,
    maximum_span: int,
    page_line_counts: Mapping[tuple[int, int], int],
) -> tuple[int, list[dict[str, Any]]]:
    hits = connection.execute(
        "SELECT l.line_id, l.document_ordinal, l.physical_page, l.line_ordinal "
        "FROM line_search s JOIN lines l ON l.line_id = s.rowid "
        "WHERE line_search MATCH ? "
        "ORDER BY l.document_ordinal, l.physical_page, l.line_ordinal",
        (query,),
    ).fetchall()
    if not hits:
        return 0, []
    radius = maximum_span - 1
    context_locators_by_hit: list[list[tuple[int, int, int]]] = []
    required_locators: set[tuple[int, int, int]] = set()
    for hit in hits:
        document_ordinal = hit["document_ordinal"]
        page = hit["physical_page"]
        line = hit["line_ordinal"]
        current_count = page_line_counts.get((document_ordinal, page))
        if current_count is None or not 0 <= line < current_count:
            raise _error("FTS5 hit lies outside the authenticated page axis")
        locators = {
            (document_ordinal, page, ordinal)
            for ordinal in range(max(0, line - radius), min(current_count, line + radius + 1))
        }
        previous_count = page_line_counts.get((document_ordinal, page - 1))
        if radius and previous_count is not None:
            locators.update(
                (document_ordinal, page - 1, ordinal)
                for ordinal in range(max(0, previous_count - radius), previous_count)
            )
        following_count = page_line_counts.get((document_ordinal, page + 1))
        if radius and following_count is not None:
            locators.update(
                (document_ordinal, page + 1, ordinal)
                for ordinal in range(min(radius, following_count))
            )
        ordered = sorted(locators)
        context_locators_by_hit.append(ordered)
        required_locators.update(ordered)

    rows_by_locator: dict[tuple[int, int, int], dict[str, Any]] = {}
    ordered_required = sorted(required_locators)
    chunk_size = 5_000
    for offset in range(0, len(ordered_required), chunk_size):
        chunk = ordered_required[offset : offset + chunk_size]
        placeholders = ",".join("(?, ?, ?)" for _locator in chunk)
        parameters = tuple(component for locator in chunk for component in locator)
        rows = connection.execute(
            "SELECT l.document_ordinal, l.physical_page, l.line_ordinal, "
            "p.line_count AS page_line_count, l.sample_id, "
            "l.bbox_left, l.bbox_top, l.bbox_right, l.bbox_bottom, "
            "l.vietocr_text, l.accentless_text FROM lines l JOIN pages p "
            "ON p.document_ordinal = l.document_ordinal "
            "AND p.physical_page = l.physical_page "
            f"WHERE (l.document_ordinal, l.physical_page, l.line_ordinal) "
            f"IN (VALUES {placeholders})",
            parameters,
        ).fetchall()
        for row in rows:
            locator = (
                row["document_ordinal"],
                row["physical_page"],
                row["line_ordinal"],
            )
            rows_by_locator[locator] = dict(row)
    if set(rows_by_locator) != required_locators:
        raise _error("bounded FTS5 context hydration lost an authenticated source row")

    result = []
    for hit, locators in zip(hits, context_locators_by_hit, strict=True):
        for locator in locators:
            row = dict(rows_by_locator[locator])
            row["context_physical_page"] = row.pop("physical_page")
            row["hit_line_id"] = hit["line_id"]
            row["hit_line_ordinal"] = hit["line_ordinal"]
            row["physical_page"] = hit["physical_page"]
            result.append(row)
    return len(hits), result


def _structural_reset_pages(
    connection: Any,
    spec: Mapping[str, Any],
    hit_context_rows: Sequence[Mapping[str, Any]],
) -> set[tuple[int, int]]:
    fragments = [_comparison_key(item) for item in spec["structural_reset_fragments"]]
    if not fragments or not hit_context_rows:
        return set()
    radius = max(spec["neighbor_pages_before"], spec["neighbor_pages_after"], 1)
    pages_by_document: dict[int, set[int]] = {}
    for row in hit_context_rows:
        document_ordinal = row["document_ordinal"]
        hit_page = row["physical_page"]
        pages_by_document.setdefault(document_ordinal, set()).update(
            range(max(1, hit_page - radius), hit_page + radius + 1)
        )
    resets: set[tuple[int, int]] = set()
    for document_ordinal, raw_pages in sorted(pages_by_document.items()):
        document = connection.execute(
            "SELECT page_count FROM documents WHERE document_ordinal = ?",
            (document_ordinal,),
        ).fetchone()
        if document is None:
            raise _error("structural-reset query document disappeared")
        pages = sorted(page for page in raw_pages if page <= document["page_count"])
        placeholders = ",".join("?" for _page in pages)
        rows = connection.execute(
            "SELECT physical_page, line_ordinal, vietocr_text, accentless_text "
            "FROM lines WHERE document_ordinal = ? "
            f"AND physical_page IN ({placeholders}) AND line_ordinal <= ? "
            "ORDER BY physical_page, line_ordinal",
            (
                document_ordinal,
                *pages,
                spec["structural_reset_max_line_ordinal"],
            ),
        ).fetchall()
        for row in rows:
            key = _comparison_key(row["accentless_text"] or row["vietocr_text"])
            if any(fragment in key for fragment in fragments):
                resets.add((document_ordinal, row["physical_page"]))
    return resets


def _occurrence_page_sets(
    occurrences: Sequence[Mapping[str, Any]],
) -> dict[str, set[int]]:
    result: dict[str, set[int]] = {}
    for occurrence in occurrences:
        result.setdefault(occurrence["anchor_id"], set()).update(
            fragment["physical_page"] for fragment in occurrence["fragments"]
        )
    return result


def _group_result(
    group: Mapping[str, Any],
    occurrences: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    pages_by_anchor = _occurrence_page_sets(occurrences)
    observed_anchor_ids = sorted(
        anchor_id for anchor_id in group["anchor_ids"] if pages_by_anchor.get(anchor_id)
    )
    seed_pages: set[int] = set()
    candidate_page_clusters: set[tuple[int, ...]] = set()
    if group["mode"] == "ANY":
        for anchor_id in observed_anchor_ids:
            seed_pages.update(pages_by_anchor[anchor_id])
            candidate_page_clusters.update((page,) for page in pages_by_anchor[anchor_id])
        satisfied = bool(seed_pages)
    else:
        satisfied = False
        if len(observed_anchor_ids) == len(group["anchor_ids"]):
            if group["page_relation"] == "SAME_PAGE":
                common = set.intersection(
                    *(pages_by_anchor[anchor_id] for anchor_id in group["anchor_ids"])
                )
                seed_pages.update(common)
                candidate_page_clusters.update((page,) for page in common)
            else:
                all_pages = sorted(
                    set().union(*(pages_by_anchor[anchor_id] for anchor_id in group["anchor_ids"]))
                )
                for start in all_pages:
                    window = {start, start + 1}
                    if all(
                        pages_by_anchor[anchor_id] & window for anchor_id in group["anchor_ids"]
                    ):
                        cluster = set()
                        for anchor_id in group["anchor_ids"]:
                            observed = pages_by_anchor[anchor_id] & window
                            seed_pages.update(observed)
                            cluster.update(observed)
                        candidate_page_clusters.add(tuple(sorted(cluster)))
            satisfied = bool(seed_pages)
    result = {
        "candidate_page_clusters": [list(cluster) for cluster in sorted(candidate_page_clusters)],
        "group_id": group["group_id"],
        "mode": group["mode"],
        "observed_anchor_ids": observed_anchor_ids,
        "page_relation": group["page_relation"],
        "seed_pages": sorted(seed_pages),
        "status": "SATISFIED" if satisfied else "NOT_SATISFIED",
    }
    if "priority" in group:
        result["priority"] = group["priority"]
    return result


def _chosen_seed_groups(
    spec: Mapping[str, Any],
    occurrences: Sequence[Mapping[str, Any]],
    overflow_anchor_ids: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[int]]:
    results = []
    for group in spec["seed_groups"]:
        result = _group_result(group, occurrences)
        overflow = sorted(set(group["anchor_ids"]) & overflow_anchor_ids)
        if overflow:
            result["overflow_anchor_ids"] = overflow
            result["seed_pages"] = []
            result["candidate_page_clusters"] = []
            result["status"] = "UNAVAILABLE_ANCHOR_QUERY_OVERFLOW"
        else:
            result["overflow_anchor_ids"] = []
        results.append(result)
    if any(item["status"] == "UNAVAILABLE_ANCHOR_QUERY_OVERFLOW" for item in results):
        return results, [], set()
    satisfied = [item for item in results if item["status"] == "SATISFIED"]
    if not satisfied:
        return results, [], set()
    # Priority controls deterministic evaluation order, never candidate
    # coverage.  A lower-priority co-occurrence group can expose a second table
    # whose owner label was OCR-damaged even when a primary owner hit exists in
    # the same filing, so every satisfied group contributes pages.
    chosen = sorted(satisfied, key=lambda item: (item["priority"], item["group_id"]))
    pages = set().union(*(set(item["seed_pages"]) for item in chosen))
    return results, canonical_clone_v1(chosen), pages


def _local_rows(
    connection: Any,
    document_ordinal: int,
    selected_pages: Sequence[int],
) -> list[dict[str, Any]]:
    if not selected_pages:
        return []
    placeholders = ",".join("?" for _page in selected_pages)
    rows = connection.execute(
        "SELECT l.document_ordinal, l.physical_page, l.line_ordinal, "
        "p.line_count AS page_line_count, l.sample_id, "
        "l.bbox_left, l.bbox_top, l.bbox_right, l.bbox_bottom, "
        "l.vietocr_text, l.accentless_text FROM lines l JOIN pages p "
        "ON p.document_ordinal = l.document_ordinal "
        "AND p.physical_page = l.physical_page "
        "WHERE l.document_ordinal = ? "
        f"AND l.physical_page IN ({placeholders}) "
        "ORDER BY l.physical_page, l.line_ordinal",
        (document_ordinal, *selected_pages),
    ).fetchall()
    return [dict(row) for row in rows]


def _local_occurrences(
    spec: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    reset_pages: set[tuple[int, int]],
) -> list[dict[str, Any]]:
    deduplicated: dict[tuple[Any, ...], dict[str, Any]] = {}
    required_anchor_ids = {
        anchor_id for group in spec["local_required_groups"] for anchor_id in group["anchor_ids"]
    }
    anchors = [
        _compiled_anchor(item)
        for item in spec["anchors"]
        if item["anchor_id"] in required_anchor_ids
    ]
    if not anchors:
        return []
    trigger_owners: dict[str, set[str]] = {}
    for anchor in anchors:
        for token in anchor["_trigger_tokens"]:
            trigger_owners.setdefault(token, set()).add(anchor["anchor_id"])
    unique_triggers = {
        anchor["anchor_id"]: (
            {token for token in anchor["_trigger_tokens"] if len(trigger_owners[token]) == 1}
            or anchor["_trigger_tokens"]
        )
        for anchor in anchors
    }
    enriched_rows: dict[int, dict[str, Any]] = {}

    def enriched(index: int) -> dict[str, Any]:
        if index not in enriched_rows:
            enriched_rows[index] = _enriched_row(rows[index])
        return enriched_rows[index]

    for hit_index, hit in enumerate(rows):
        raw_accentless = hit["accentless_text"].casefold()
        candidate_anchors = [
            anchor
            for anchor in anchors
            if any(
                alias["_surface_key"] in raw_accentless
                or any(probe in raw_accentless for probe in alias["_probe_keys"])
                for alias in anchor["_aliases"]
            )
            or any(token in raw_accentless for token in unique_triggers[anchor["anchor_id"]])
        ]
        if not candidate_anchors:
            continue
        for anchor in candidate_anchors:
            matched_windows = []
            for span in range(1, spec["window_line_span"] + 1):
                for start in range(hit_index - span + 1, hit_index + 1):
                    if start < 0 or start + span > len(rows):
                        continue
                    window = [enriched(index) for index in range(start, start + span)]
                    if not _window_is_contiguous(window, reset_pages):
                        continue
                    unicode_text = " ".join(row["vietocr_text"] for row in window)
                    accentless_text = " ".join(row["accentless_text"] for row in window)
                    unicode_key = " ".join(row["_unicode_nfc_casefold"] for row in window)
                    accentless_key = " ".join(row["_accentless_key"] for row in window)
                    channels, edit_distance, matched_alias = _matching_channels(
                        anchor,
                        unicode_text,
                        accentless_text,
                        unicode_nfc_casefold=unicode_key,
                        accentless_key=accentless_key,
                    )
                    if not _channels_prove_anchor(channels):
                        continue
                    if matched_alias is None:
                        raise _error("proved local match lost its alias provenance")
                    matched_windows.append(
                        (
                            window,
                            unicode_text,
                            accentless_text,
                            channels,
                            edit_distance,
                            matched_alias,
                        )
                    )
            if not matched_windows:
                continue
            (
                window,
                unicode_text,
                accentless_text,
                channels,
                edit_distance,
                matched_alias,
            ) = min(
                matched_windows,
                key=lambda item: (
                    min(_CHANNEL_ORDER[channel] for channel in item[3]),
                    len(item[0]),
                    item[0][0]["physical_page"],
                    item[0][0]["line_ordinal"],
                ),
            )
            key, occurrence = _occurrence_from_window(
                anchor,
                window,
                unicode_text,
                accentless_text,
                channels,
                edit_distance,
                matched_alias,
                stage="LOCAL_SELECTED_PAGE_VALIDATION",
            )
            prior = deduplicated.get(key)
            if prior is None or len(occurrence["channels"]) > len(prior["channels"]):
                deduplicated[key] = occurrence
    # Do not retain a longer occurrence when the same anchor already matched a
    # strict subwindow. This keeps local receipt size bounded and explainable.
    ordered = sorted(
        deduplicated.values(),
        key=lambda item: (
            item["document_ordinal"],
            item["anchor_id"],
            sum(len(fragment["sample_ids"]) for fragment in item["fragments"]),
            item["start_locator"]["physical_page"],
            item["start_locator"]["line_ordinal"],
            item["end_locator"]["physical_page"],
            item["end_locator"]["line_ordinal"],
        ),
    )
    minimal = []
    for occurrence in ordered:
        start_locator = (
            occurrence["start_locator"]["physical_page"],
            occurrence["start_locator"]["line_ordinal"],
        )
        end_locator = (
            occurrence["end_locator"]["physical_page"],
            occurrence["end_locator"]["line_ordinal"],
        )
        if any(
            prior["anchor_id"] == occurrence["anchor_id"]
            and (
                prior["start_locator"]["physical_page"],
                prior["start_locator"]["line_ordinal"],
            )
            >= start_locator
            and (
                prior["end_locator"]["physical_page"],
                prior["end_locator"]["line_ordinal"],
            )
            <= end_locator
            for prior in minimal
        ):
            continue
        minimal.append(occurrence)
    return sorted(
        minimal,
        key=lambda item: (
            item["document_ordinal"],
            item["start_locator"]["physical_page"],
            item["start_locator"]["line_ordinal"],
            item["end_locator"]["physical_page"],
            item["end_locator"]["line_ordinal"],
            item["anchor_id"],
        ),
    )


def _page_selection(
    document: Mapping[str, Any],
    occurrences: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any],
    *,
    global_overflow: bool,
    reset_pages: set[tuple[int, int]],
) -> tuple[list[int], str, list[dict[str, Any]], list[dict[str, Any]], bool]:
    page_count = document["page_count"]
    document_ordinal = document["document_ordinal"]
    hit_pages = sorted(
        {fragment["physical_page"] for item in occurrences for fragment in item["fragments"]}
    )
    reasons: dict[int, set[str]] = {}
    for item in occurrences:
        for fragment in item["fragments"]:
            reasons.setdefault(fragment["physical_page"], set()).add(
                "ANCHOR_" + item["anchor_role"]
            )
    if global_overflow:
        pages = list(range(1, page_count + 1))
        mode = "FULL_DOCUMENT_FALLBACK_QUERY_OVERFLOW"
        return pages, mode, [], [], True
    if not hit_pages:
        pages = list(range(1, page_count + 1))
        mode = "FULL_DOCUMENT_FALLBACK_ZERO_VALIDATED_HITS"
        return pages, mode, [], [], True
    blocked: list[dict[str, Any]] = []
    for hit_page in hit_pages:
        current = hit_page
        for offset in range(1, spec["neighbor_pages_before"] + 1):
            page = hit_page - offset
            if page < 1:
                break
            if (document_ordinal, current) in reset_pages:
                blocked.append(
                    {
                        "direction": "BEFORE",
                        "from_page": current,
                        "physical_page": page,
                        "reason": "STRUCTURAL_RESET_AT_CURRENT_PAGE_START",
                    }
                )
                break
            reasons.setdefault(page, set()).add("NEIGHBOR_BEFORE")
            current = page
        current = hit_page
        for offset in range(1, spec["neighbor_pages_after"] + 1):
            page = hit_page + offset
            if page > page_count:
                break
            if (document_ordinal, page) in reset_pages:
                blocked.append(
                    {
                        "direction": "AFTER",
                        "from_page": current,
                        "physical_page": page,
                        "reason": "STRUCTURAL_RESET_AT_CANDIDATE_PAGE_START",
                    }
                )
                break
            reasons.setdefault(page, set()).add("NEIGHBOR_AFTER")
            current = page
    pages = sorted(reasons)
    if len(pages) > spec["max_selected_pages_per_document"]:
        pages = list(range(1, page_count + 1))
        return pages, "FULL_DOCUMENT_FALLBACK_PAGE_BUDGET", [], blocked, True
    explanation = [{"physical_page": page, "reasons": sorted(reasons[page])} for page in pages]
    return pages, "INDEXED_LOCAL_REGION", explanation, blocked, False


def _validate_candidate_regions(
    document: Mapping[str, Any],
    chosen_groups: Sequence[Mapping[str, Any]],
    seed_occurrences: Sequence[Mapping[str, Any]],
    local_occurrences: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any],
    reset_pages: set[tuple[int, int]],
) -> dict[str, Any]:
    group_specs = {item["group_id"]: item for item in spec["seed_groups"]}
    region_results = []
    accepted_pages: set[int] = set()
    accepted_group_ids: set[str] = set()
    explanations: dict[int, set[str]] = {}
    blocked: list[dict[str, Any]] = []
    page_budget_fallback = False
    for chosen in chosen_groups:
        group = group_specs[chosen["group_id"]]
        for cluster in chosen["candidate_page_clusters"]:
            cluster_pages = set(cluster)
            cluster_seed_occurrences = [
                item
                for item in seed_occurrences
                if item["anchor_id"] in group["anchor_ids"]
                and any(
                    fragment["physical_page"] in cluster_pages for fragment in item["fragments"]
                )
            ]
            (
                region_pages,
                selection_mode,
                region_explanations,
                region_blocked,
                requires_full_document_review,
            ) = _page_selection(
                document,
                cluster_seed_occurrences,
                spec,
                global_overflow=False,
                reset_pages=reset_pages,
            )
            region_local_occurrences = [
                item
                for item in local_occurrences
                if any(fragment["physical_page"] in region_pages for fragment in item["fragments"])
            ]
            local_results = [
                _group_result(local_group, region_local_occurrences)
                for local_group in spec["local_required_groups"]
            ]
            accepted = not requires_full_document_review and all(
                item["status"] == "SATISFIED" for item in local_results
            )
            status = (
                "ACCEPTED_LOCAL_REQUIRED_GROUPS" if accepted else "REJECTED_LOCAL_REQUIRED_GROUPS"
            )
            if requires_full_document_review:
                status = "REQUIRES_FULL_DOCUMENT_FALLBACK_PAGE_BUDGET"
                page_budget_fallback = True
            region_results.append(
                {
                    "group_id": chosen["group_id"],
                    "local_required_group_results": local_results,
                    "region_pages": region_pages,
                    "seed_pages": list(cluster),
                    "selection_mode": selection_mode,
                    "status": status,
                }
            )
            if not accepted:
                continue
            accepted_group_ids.add(chosen["group_id"])
            accepted_pages.update(region_pages)
            blocked.extend(region_blocked)
            for explanation in region_explanations:
                explanations.setdefault(explanation["physical_page"], set()).update(
                    explanation["reasons"]
                )
    if len(accepted_pages) > spec["max_selected_pages_per_document"]:
        page_budget_fallback = True
    accepted_seed_occurrences = [
        item
        for item in seed_occurrences
        if any(fragment["physical_page"] in accepted_pages for fragment in item["fragments"])
    ]
    accepted_local_occurrences = [
        item
        for item in local_occurrences
        if any(fragment["physical_page"] in accepted_pages for fragment in item["fragments"])
    ]
    return {
        "accepted_group_ids": sorted(accepted_group_ids),
        "blocked_expansions": sorted(
            {canonical_json_sha256_v1(item): item for item in blocked}.values(),
            key=lambda item: (
                item["physical_page"],
                item["direction"],
                item["from_page"],
            ),
        ),
        "local_occurrences": accepted_local_occurrences,
        "page_budget_fallback": page_budget_fallback,
        "page_explanations": [
            {"physical_page": page, "reasons": sorted(reasons)}
            for page, reasons in sorted(explanations.items())
        ],
        "region_results": region_results,
        "seed_occurrences": accepted_seed_occurrences,
        "selected_pages": sorted(accepted_pages),
    }


def _engine_ref(root: Path) -> dict[str, Any]:
    path = Path(__file__).resolve()
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise _error("retrieval engine implementation lies outside the project root") from exc
    payload = store_v1._stable_bytes(path, "region retrieval implementation")
    return {
        "path": relative.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _runtime_determinants(connection: Any) -> dict[str, Any]:
    compile_options = sorted(
        row[0] for row in connection.execute("PRAGMA compile_options").fetchall()
    )
    fts_sql = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'line_search'"
    ).fetchone()
    if fts_sql is None or type(fts_sql[0]) is not str or "tokenize='trigram'" not in fts_sql[0]:
        raise _error("authenticated OCR sidecar is not the pinned FTS5 trigram index")
    try:
        rapidfuzz_version = importlib.metadata.version("RapidFuzz")
    except importlib.metadata.PackageNotFoundError as exc:
        raise _error("RapidFuzz runtime distribution is absent") from exc
    primitive_module = sys.modules.get(Levenshtein.distance.__module__)
    primitive_path_raw = getattr(primitive_module, "__file__", None)
    wrapper_path_raw = getattr(Levenshtein, "__file__", None)
    if type(primitive_path_raw) is not str or type(wrapper_path_raw) is not str:
        raise _error("RapidFuzz edit primitive has no file-backed runtime closure")

    def runtime_ref(path_raw: str, module: str) -> dict[str, Any]:
        path = Path(path_raw)
        try:
            before = path.stat(follow_symlinks=False)
            if path.is_symlink() or not path.is_file():
                raise _error("RapidFuzz runtime closure is not one regular file")
            payload = path.read_bytes()
            after = path.stat(follow_symlinks=False)
        except OSError as exc:
            raise _error("cannot bind RapidFuzz runtime closure") from exc

        def identity(value: Any) -> tuple[int, int, int, int, int]:
            return (
                value.st_dev,
                value.st_ino,
                value.st_mode,
                value.st_size,
                value.st_mtime_ns,
            )

        if identity(before) != identity(after) or len(payload) != before.st_size:
            raise _error("RapidFuzz runtime closure changed while being hashed")
        return {
            "filename": path.name,
            "module": module,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }

    return {
        "fts5_table_sql_sha256": hashlib.sha256(fts_sql[0].encode("utf-8")).hexdigest(),
        "fts5vocab_mode": "row",
        "fts5vocab_source": "main.line_search",
        "rapidfuzz_distribution_version": rapidfuzz_version,
        "rapidfuzz_edit_primitive": "rapidfuzz.distance.Levenshtein.distance",
        "rapidfuzz_primitive_ref": runtime_ref(
            primitive_path_raw,
            Levenshtein.distance.__module__,
        ),
        "rapidfuzz_wrapper_ref": runtime_ref(
            wrapper_path_raw,
            "rapidfuzz.distance.Levenshtein",
        ),
        "sqlite_compile_options_sha256": canonical_json_sha256_v1(compile_options),
        "sqlite_version": sqlite3.sqlite_version,
    }


def _source_binding(
    state: Any,
    engine_ref: Mapping[str, Any],
    spec: Mapping[str, Any],
    runtime_determinants: Mapping[str, Any],
) -> dict[str, Any]:
    database_ref = state.manifest["database_ref"]
    return {
        "database_ref": canonical_clone_v1(database_ref),
        "engine_ref": canonical_clone_v1(engine_ref),
        "manifest_id": state.manifest["manifest_id"],
        "query_spec_id": family_first_region_query_spec_id_v1(spec),
        "runtime_determinants": canonical_clone_v1(runtime_determinants),
    }


def _retrieve_from_state(
    state: Any,
    query_spec: Any,
    *,
    engine_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """Deterministic core kept separate for read-only benchmark fixtures."""

    spec = validate_family_first_region_query_spec_v1(query_spec)
    _verify_semantic_assignment_adapter_ref(state, spec)
    anchors_by_id = {item["anchor_id"]: item for item in spec["anchors"]}
    seed_anchor_ids = sorted(
        {anchor_id for group in spec["seed_groups"] for anchor_id in group["anchor_ids"]}
    )
    raw_counts: dict[str, int] = {}
    rare_counts: dict[str, int] = {}
    contexts_by_anchor: dict[str, list[dict[str, Any]]] = {}
    rare_contexts_by_anchor: dict[str, list[dict[str, Any]]] = {}
    rare_plans_by_anchor: dict[str, dict[str, Any]] = {}
    overflow_anchor_ids: set[str] = set()
    with cache_v1._connect(state.database_path) as connection:
        runtime_determinants = _runtime_determinants(connection)
        documents = _source_documents(connection, state)
        historical_variant_support_verifications = _verify_historical_variant_supports(
            connection, spec
        )
        page_line_counts = {
            (row["document_ordinal"], row["physical_page"]): row["line_count"]
            for row in connection.execute(
                "SELECT document_ordinal, physical_page, line_count FROM pages "
                "ORDER BY document_ordinal, physical_page"
            ).fetchall()
        }
        rare_line_frequencies = _rare_trigram_line_frequencies(
            connection,
            [anchors_by_id[anchor_id] for anchor_id in seed_anchor_ids],
        )
        for anchor_id in seed_anchor_ids:
            query = _anchor_fts_query(anchors_by_id[anchor_id])
            count = connection.execute(
                "SELECT COUNT(*) FROM line_search WHERE line_search MATCH ?",
                (query,),
            ).fetchone()[0]
            if type(count) is not int or count < 0:
                raise _error("per-anchor FTS5 hit denominator drifted")
            raw_counts[anchor_id] = count
            if count > spec["max_hit_lines"]:
                overflow_anchor_ids.add(anchor_id)
                contexts_by_anchor[anchor_id] = []
            else:
                confirmed_count, rows = _hit_context_rows(
                    connection,
                    query,
                    spec["window_line_span"],
                    page_line_counts,
                )
                if confirmed_count != count:
                    raise _error("per-anchor FTS5 hit denominator changed during retrieval")
                contexts_by_anchor[anchor_id] = rows

            rare_plan = _rare_trigram_seed_plan(
                anchors_by_id[anchor_id],
                rare_line_frequencies,
            )
            rare_query = _rare_trigram_query(rare_plan)
            rare_contexts_by_anchor[anchor_id] = []
            if rare_query is not None:
                rare_count = connection.execute(
                    "SELECT COUNT(*) FROM line_search WHERE line_search MATCH ?",
                    (rare_query,),
                ).fetchone()[0]
                if type(rare_count) is not int or rare_count < 0:
                    raise _error("rare-trigram union hit denominator drifted")
                rare_counts[anchor_id] = rare_count
                rare_plan["union_hit_line_count"] = rare_count
                rare_budget = min(
                    spec["max_hit_lines"],
                    _RARE_TRIGRAM_MAX_UNION_HITS,
                )
                if rare_count > rare_budget:
                    rare_plan["status"] = "UNAVAILABLE_UNION_QUERY_OVERFLOW"
                else:
                    confirmed_count, rare_rows = _hit_context_rows(
                        connection,
                        rare_query,
                        spec["window_line_span"],
                        page_line_counts,
                    )
                    if confirmed_count != rare_count:
                        raise _error("rare-trigram union hit denominator changed during retrieval")
                    _finalize_rare_trigram_seed_plan(rare_plan, rare_rows)
                    if rare_plan["selected_grams"]:
                        rare_contexts_by_anchor[anchor_id] = rare_rows
                        rare_plan["status"] = "QUERIED"
            else:
                rare_counts[anchor_id] = 0
            rare_plans_by_anchor[anchor_id] = rare_plan
        all_context_rows = [
            row
            for anchor_id in seed_anchor_ids
            for row in (contexts_by_anchor[anchor_id] + rare_contexts_by_anchor[anchor_id])
        ]
        reset_pages = _structural_reset_pages(connection, spec, all_context_rows)
        seed_occurrences = []
        for anchor_id in seed_anchor_ids:
            if anchor_id in overflow_anchor_ids:
                continue
            seed_occurrences.extend(
                _occurrences(
                    {
                        "anchors": [anchors_by_id[anchor_id]],
                        "window_line_span": spec["window_line_span"],
                    },
                    contexts_by_anchor[anchor_id],
                    reset_pages,
                )
            )
            if rare_plans_by_anchor[anchor_id]["status"] == "QUERIED":
                seed_occurrences.extend(
                    _occurrences(
                        {
                            "anchors": [anchors_by_id[anchor_id]],
                            "window_line_span": spec["window_line_span"],
                        },
                        rare_contexts_by_anchor[anchor_id],
                        reset_pages,
                        rare_trigram_plan=rare_plans_by_anchor[anchor_id],
                        stage="GLOBAL_RARE_TRIGRAM_SEED",
                    )
                )
        deduplicated_seed_occurrences: dict[tuple[Any, ...], dict[str, Any]] = {}
        for item in seed_occurrences:
            key = (
                item["document_ordinal"],
                item["start_locator"]["physical_page"],
                item["start_locator"]["line_ordinal"],
                item["end_locator"]["physical_page"],
                item["end_locator"]["line_ordinal"],
                item["anchor_id"],
            )
            prior = deduplicated_seed_occurrences.get(key)
            rank = (
                not bool({"EXACT_UNICODE", "EXACT_ACCENTLESS"} & set(item["channels"])),
                item["edit_distance"] if item["edit_distance"] is not None else 999,
                item["stage"],
            )
            prior_rank = (
                (
                    not bool({"EXACT_UNICODE", "EXACT_ACCENTLESS"} & set(prior["channels"])),
                    prior["edit_distance"] if prior["edit_distance"] is not None else 999,
                    prior["stage"],
                )
                if prior is not None
                else None
            )
            if prior is None or rank < prior_rank:
                deduplicated_seed_occurrences[key] = item
        seed_occurrences = sorted(
            deduplicated_seed_occurrences.values(),
            key=lambda item: (
                item["document_ordinal"],
                item["start_locator"]["physical_page"],
                item["start_locator"]["line_ordinal"],
                item["anchor_id"],
            ),
        )
        seed_by_document: dict[int, list[dict[str, Any]]] = {}
        for occurrence in seed_occurrences:
            seed_by_document.setdefault(occurrence["document_ordinal"], []).append(occurrence)

        outcomes = []
        fallback_count = 0
        zero_count = 0
        selected_page_count = 0
        local_occurrence_count = 0
        local_occurrences_all = []
        for document, packet in zip(documents, state.manifest["documents"], strict=True):
            ordinal = document["document_ordinal"]
            document_seed_occurrences = seed_by_document.get(ordinal, [])
            seed_group_results, chosen_groups, chosen_seed_pages = _chosen_seed_groups(
                spec,
                document_seed_occurrences,
                overflow_anchor_ids,
            )
            if not chosen_groups:
                pages = list(range(1, document["page_count"] + 1))
                explanations: list[dict[str, Any]] = []
                blocked_expansions: list[dict[str, Any]] = []
                requires_full_document_review = True
                mode = (
                    "FULL_DOCUMENT_FALLBACK_SEED_QUERY_OVERFLOW"
                    if any(
                        item["status"] == "UNAVAILABLE_ANCHOR_QUERY_OVERFLOW"
                        for item in seed_group_results
                    )
                    else "FULL_DOCUMENT_FALLBACK_NO_VALID_SEED_GROUP"
                )
                fallback_reason = mode
                chosen_seed_occurrences: list[dict[str, Any]] = []
                local_occurrences: list[dict[str, Any]] = []
                candidate_region_results: list[dict[str, Any]] = []
                local_group_results = [
                    {
                        **_group_result(group, []),
                        "status": "NOT_EVALUATED_NO_VALID_SEED_GROUP",
                    }
                    for group in spec["local_required_groups"]
                ]
                zero_count += 1
            else:
                chosen_anchor_ids = {
                    anchor_id
                    for group in chosen_groups
                    for anchor_id in next(
                        item["anchor_ids"]
                        for item in spec["seed_groups"]
                        if item["group_id"] == group["group_id"]
                    )
                }
                chosen_seed_occurrences = [
                    item
                    for item in document_seed_occurrences
                    if item["anchor_id"] in chosen_anchor_ids
                    and any(
                        fragment["physical_page"] in chosen_seed_pages
                        for fragment in item["fragments"]
                    )
                ]
                (
                    pages,
                    mode,
                    explanations,
                    blocked_expansions,
                    requires_full_document_review,
                ) = _page_selection(
                    document,
                    chosen_seed_occurrences,
                    spec,
                    global_overflow=False,
                    reset_pages=reset_pages,
                )
                fallback_reason = mode if mode.startswith("FULL_DOCUMENT_FALLBACK") else None
                if requires_full_document_review:
                    local_occurrences = []
                    candidate_region_results = []
                    local_group_results = [
                        {
                            **_group_result(group, []),
                            "status": "NOT_EVALUATED_PAGE_BUDGET_FALLBACK",
                        }
                        for group in spec["local_required_groups"]
                    ]
                else:
                    provisional_local_occurrences = _local_occurrences(
                        spec,
                        _local_rows(connection, ordinal, pages),
                        reset_pages,
                    )
                    region_validation = _validate_candidate_regions(
                        document,
                        chosen_groups,
                        chosen_seed_occurrences,
                        provisional_local_occurrences,
                        spec,
                        reset_pages,
                    )
                    candidate_region_results = region_validation["region_results"]
                    if region_validation["page_budget_fallback"]:
                        mode = "FULL_DOCUMENT_FALLBACK_CANDIDATE_REGION_PAGE_BUDGET"
                        pages = list(range(1, document["page_count"] + 1))
                        explanations = []
                        blocked_expansions = []
                        requires_full_document_review = True
                        fallback_reason = mode
                        local_occurrences = []
                    elif not region_validation["selected_pages"]:
                        mode = "FULL_DOCUMENT_FALLBACK_NO_LOCALLY_VALIDATED_REGION"
                        pages = list(range(1, document["page_count"] + 1))
                        explanations = []
                        blocked_expansions = []
                        requires_full_document_review = True
                        fallback_reason = mode
                        local_occurrences = []
                    else:
                        accepted_group_ids = set(region_validation["accepted_group_ids"])
                        chosen_groups = [
                            item for item in chosen_groups if item["group_id"] in accepted_group_ids
                        ]
                        pages = region_validation["selected_pages"]
                        explanations = region_validation["page_explanations"]
                        blocked_expansions = region_validation["blocked_expansions"]
                        chosen_seed_occurrences = region_validation["seed_occurrences"]
                        local_occurrences = region_validation["local_occurrences"]
                        mode = "INDEXED_LOCALLY_VALIDATED_CANDIDATE_REGIONS"
                        requires_full_document_review = False
                        fallback_reason = None
                    local_group_results = [
                        _group_result(group, local_occurrences)
                        for group in spec["local_required_groups"]
                    ]
                if mode.startswith("FULL_DOCUMENT_FALLBACK") and fallback_reason is None:
                    pages = list(range(1, document["page_count"] + 1))
                    explanations = []
                    requires_full_document_review = True
                    fallback_reason = mode
            if mode.startswith("FULL_DOCUMENT_FALLBACK"):
                fallback_count += 1
            selected_page_count += len(pages)
            local_occurrence_count += len(local_occurrences)
            local_occurrences_all.extend(local_occurrences)
            material = {
                "blocked_expansions": blocked_expansions,
                "chosen_seed_groups": chosen_groups,
                "candidate_region_results": candidate_region_results,
                "coverage_status": "PROVEN_COMPLETE_FOR_DECLARED_SPEC",
                "document_evidence_root_sha256": packet["document_evidence_root_sha256"],
                "document_id": document["document_id"],
                "document_line_count": document["line_count"],
                "document_ordinal": ordinal,
                "document_packet_id": packet["packet_id"],
                "document_page_count": document["page_count"],
                "fallback_reason": fallback_reason,
                "index_outcome": (
                    "NONZERO_VALID_SEED_GROUP" if chosen_groups else "ZERO_VALID_SEED_GROUP"
                ),
                "local_occurrences": canonical_clone_v1(local_occurrences),
                "local_required_group_results": local_group_results,
                "page_explanations": explanations,
                "requires_full_document_review": requires_full_document_review,
                "seed_group_results": seed_group_results,
                "seed_occurrences": canonical_clone_v1(chosen_seed_occurrences),
                "selected_pages": pages,
                "selection_mode": mode,
                "structural_reset_pages": sorted(
                    page for reset_document, page in reset_pages if reset_document == ordinal
                ),
            }
            outcomes.append(
                {
                    **material,
                    "outcome_id": "fffrrv2:document:" + canonical_json_sha256_v1(material),
                }
            )
    anchor_statistics = []
    for anchor in spec["anchors"]:
        anchor_id = anchor["anchor_id"]
        seed_observed = [item for item in seed_occurrences if item["anchor_id"] == anchor_id]
        local_observed = [item for item in local_occurrences_all if item["anchor_id"] == anchor_id]
        anchor_statistics.append(
            {
                "anchor_id": anchor_id,
                "global_query_executed": anchor_id in seed_anchor_ids,
                "global_query_overflow": anchor_id in overflow_anchor_ids,
                "local_document_frequency": len(
                    {item["document_ordinal"] for item in local_observed}
                ),
                "local_occurrence_count": len(local_observed),
                "local_page_frequency": len(
                    {
                        (item["document_ordinal"], fragment["physical_page"])
                        for item in local_observed
                        for fragment in item["fragments"]
                    }
                ),
                "raw_fts_hit_line_count": raw_counts.get(anchor_id),
                "raw_rare_trigram_hit_line_count": rare_counts.get(anchor_id),
                "rare_trigram_seed_plan": canonical_clone_v1(
                    rare_plans_by_anchor.get(
                        anchor_id,
                        {
                            "anchor_id": anchor_id,
                            "status": "NOT_A_GLOBAL_SEED_ANCHOR",
                        },
                    )
                ),
                "seed_document_frequency": len(
                    {item["document_ordinal"] for item in seed_observed}
                ),
                "seed_occurrence_count": len(seed_observed),
                "seed_page_frequency": len(
                    {
                        (item["document_ordinal"], fragment["physical_page"])
                        for item in seed_observed
                        for fragment in item["fragments"]
                    }
                ),
            }
        )
    metrics = {
        "document_count": len(outcomes),
        "fallback_document_count": fallback_count,
        "occurrence_count": local_occurrence_count,
        "raw_fts_hit_line_count": sum(raw_counts.values()),
        "raw_rare_trigram_hit_line_count": sum(rare_counts.values()),
        "selected_page_count": selected_page_count,
        "seed_occurrence_count": len(seed_occurrences),
        "source_line_count": sum(item["line_count"] for item in documents),
        "source_page_count": sum(item["page_count"] for item in documents),
        "zero_validated_hit_document_count": zero_count,
    }
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": outcomes,
        "family_id": spec["family_id"],
        "format_version": RECEIPT_FORMAT_VERSION,
        "metrics": metrics,
        "planner": {
            "anchor_statistics": anchor_statistics,
            "historical_variant_support_verifications": (historical_variant_support_verifications),
            "seed_anchor_ids": seed_anchor_ids,
            "strategy": ("DECLARATIVE_ALL_SATISFIED_SEED_GROUP_COVERAGE_THEN_LOCAL_VALIDATION"),
        },
        "query_spec": spec,
        "source_binding": _source_binding(
            state,
            engine_ref,
            spec,
            runtime_determinants,
        ),
        "state": "DIRECT_RECOMPUTED_COMPLETE_DOCUMENT_REGION_SHORTLIST",
    }
    return {
        **material,
        "receipt_id": "fffrrv2:receipt:" + canonical_json_sha256_v1(material),
    }


def _validate_receipt_shape(value: Any) -> dict[str, Any]:
    fields = {
        "authority",
        "claim_boundary",
        "documents",
        "family_id",
        "format_version",
        "metrics",
        "planner",
        "query_spec",
        "receipt_id",
        "source_binding",
        "state",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error("region retrieval receipt fields drifted")
    spec = validate_family_first_region_query_spec_v1(value["query_spec"])
    documents = value["documents"]
    metrics = value["metrics"]
    binding = value["source_binding"]
    planner = value["planner"]
    if (
        value["format_version"] != RECEIPT_FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "DIRECT_RECOMPUTED_COMPLETE_DOCUMENT_REGION_SHORTLIST"
        or value["family_id"] != spec["family_id"]
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(documents) is not list
        or not documents
        or type(metrics) is not dict
        or set(metrics)
        != {
            "document_count",
            "fallback_document_count",
            "occurrence_count",
            "raw_fts_hit_line_count",
            "raw_rare_trigram_hit_line_count",
            "selected_page_count",
            "seed_occurrence_count",
            "source_line_count",
            "source_page_count",
            "zero_validated_hit_document_count",
        }
        or type(binding) is not dict
        or set(binding)
        != {
            "database_ref",
            "engine_ref",
            "manifest_id",
            "query_spec_id",
            "runtime_determinants",
        }
        or binding["query_spec_id"] != family_first_region_query_spec_id_v1(spec)
        or type(planner) is not dict
        or set(planner)
        != {
            "anchor_statistics",
            "historical_variant_support_verifications",
            "seed_anchor_ids",
            "strategy",
        }
        or planner["strategy"]
        != "DECLARATIVE_ALL_SATISFIED_SEED_GROUP_COVERAGE_THEN_LOCAL_VALIDATION"
    ):
        raise _error("region retrieval receipt identity/denominator drifted")
    if any(type(item) is not int or item < 0 for item in metrics.values()):
        raise _error("region retrieval receipt metrics drifted")
    if metrics["document_count"] != len(documents):
        raise _error("region retrieval document denominator drifted")
    for ordinal, document in enumerate(documents, 1):
        if (
            type(document) is not dict
            or document.get("document_ordinal") != ordinal
            or document.get("coverage_status") != "PROVEN_COMPLETE_FOR_DECLARED_SPEC"
            or type(document.get("selected_pages")) is not list
            or document["selected_pages"] != sorted(set(document["selected_pages"]))
            or any(type(page) is not int or page <= 0 for page in document["selected_pages"])
            or type(document.get("seed_occurrences")) is not list
            or type(document.get("local_occurrences")) is not list
            or type(document.get("blocked_expansions")) is not list
            or type(document.get("structural_reset_pages")) is not list
            or type(document.get("outcome_id")) is not str
            or not document["outcome_id"].startswith("fffrrv2:document:")
        ):
            raise _error("region retrieval document outcome drifted")
        material = canonical_clone_v1(document)
        outcome_id = material.pop("outcome_id")
        if outcome_id != "fffrrv2:document:" + canonical_json_sha256_v1(material):
            raise _error("region retrieval document outcome hash drifted")
        for occurrence in document["seed_occurrences"] + document["local_occurrences"]:
            if (
                type(occurrence) is not dict
                or type(occurrence.get("fragments")) is not list
                or not occurrence["fragments"]
                or any(
                    type(fragment) is not dict
                    or type(fragment.get("physical_page")) is not int
                    or type(fragment.get("bbox")) is not list
                    for fragment in occurrence["fragments"]
                )
            ):
                raise _error("region retrieval occurrence fragments drifted")
            occurrence_material = canonical_clone_v1(occurrence)
            occurrence_id = occurrence_material.pop("occurrence_id", None)
            if occurrence_id != (
                "fffrrv2:occurrence:" + canonical_json_sha256_v1(occurrence_material)
            ):
                raise _error("region retrieval occurrence identity drifted")
    material = canonical_clone_v1(value)
    receipt_id = material.pop("receipt_id")
    if receipt_id != "fffrrv2:receipt:" + canonical_json_sha256_v1(material):
        raise _error("region retrieval receipt hash drifted")
    return canonical_clone_v1(value)


def retrieve_authenticated_family_first_regions_v1(
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    query_spec: Any,
) -> dict[str, Any]:
    """Query every document from the authenticated sidecar and return a receipt."""

    try:
        state = store_v1._live_store(capability)
    except store_v1.FamilyFirstDocumentEvidenceStoreV1Error as exc:
        raise _error("one live authenticated document evidence store is required") from exc
    engine_ref = _engine_ref(state.root)
    result = _validate_receipt_shape(_retrieve_from_state(state, query_spec, engine_ref=engine_ref))
    try:
        final = store_v1._live_store(capability)
    except store_v1.FamilyFirstDocumentEvidenceStoreV1Error as exc:
        raise _error("authenticated document store changed during region retrieval") from exc
    _verify_semantic_assignment_adapter_ref(
        state,
        validate_family_first_region_query_spec_v1(query_spec),
    )
    if final is not state or _engine_ref(state.root) != engine_ref:
        raise _error("authenticated source or retrieval engine changed during query")
    return result


def validate_replayed_authenticated_family_first_region_receipt_v1(
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    query_spec: Any,
    receipt: Any,
) -> dict[str, Any]:
    """Reject even coherently self-rehashed receipts unless direct SQL replays."""

    observed = _validate_receipt_shape(receipt)
    expected = retrieve_authenticated_family_first_regions_v1(capability, query_spec)
    if not same_typed_json_v1(observed, expected):
        raise _error("region retrieval receipt does not replay from authenticated SQLite")
    return observed


# The module path is retained for in-flight consumers, while the public V2
# names make the bumped query/receipt contract explicit.
validate_family_first_region_query_spec_v2 = validate_family_first_region_query_spec_v1
family_first_region_query_spec_id_v2 = family_first_region_query_spec_id_v1
retrieve_authenticated_family_first_regions_v2 = retrieve_authenticated_family_first_regions_v1
validate_replayed_authenticated_family_first_region_receipt_v2 = (
    validate_replayed_authenticated_family_first_region_receipt_v1
)
