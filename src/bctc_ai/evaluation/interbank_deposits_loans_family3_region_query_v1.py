"""Region-first shortlist policy for Family 3 interbank assets.

The authenticated generic retrieval engine owns OCR access, bounded windows,
reset fencing, fallback, and receipt replay.  This adapter only projects the
tracked V3 topology vocabulary into a bank-blind query.  It is deliberately
overinclusive: an explicit owner may seed a candidate, while a branchless
candidate needs two *different* structural child roles.  Every failed or
missing proof remains a full-document fallback; nothing here can prove
presence, absence, numbers, schema identity, or mapping.
"""

from __future__ import annotations

import hashlib
import json
import re
import stat
import unicodedata
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.source_structure.contracts_v1 import same_typed_json_v1

__all__ = [
    "FAMILY_ID",
    "INTERBANK_DEPOSITS_LOANS_FAMILY3_REGION_QUERY_SPEC_V2",
    "INTERBANK_DEPOSITS_LOANS_FAMILY3_REGION_QUERY_TRUST_CLOSURE_V1",
    "InterbankDepositsLoansFamily3RegionQueryV1Error",
    "build_interbank_deposits_loans_family3_region_query_spec_v2",
]


FAMILY_ID = "INTERBANK_DEPOSITS_AND_LOANS"
_QUERY_FORMAT = "FAMILY_FIRST_REGION_QUERY_SPEC_V2"
_TOPOLOGY_PATH = Path("config/families/tm-interbank-deposits-loans-topology-v3.json")
_ADAPTER_PATH = Path("src/bctc_ai/evaluation/interbank_deposits_loans_family3_region_query_v1.py")
_CORE_RESCUE_ROLES = {
    "DEMAND_DEPOSIT_GROUP",
    "INTERBANK_DEPOSIT_GROUP",
    "INTERBANK_LOAN_GROUP",
    "TERM_DEPOSIT_GROUP",
}
_ID_FRAGMENT = re.compile(r"[^A-Z0-9]+")

# Literal pins make a reordered or edited provider/config file an explicit
# trust-closure change.  The query itself binds this adapter's exact bytes.
INTERBANK_DEPOSITS_LOANS_FAMILY3_REGION_QUERY_TRUST_CLOSURE_V1 = {
    "anchor_normalization_engine_ref": {
        "path": "src/bctc_ai/evaluation/accounting_variant_graph_engine_v1.py",
        "sha256": "6fbd518a09418278e273b0a81eed4db98b013dcb70bcbdf31e81bf9b47058b50",
        "size_bytes": 36_599,
    },
    "shared_topology_engine_ref": {
        "path": "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
        "sha256": "65e88f2a28a214a71ba47ce2d237dbbc021d5be5d1cf34794aa9776908b2ed66",
        "size_bytes": 77_499,
    },
    "topology_spec_ref": {
        "path": "config/families/tm-interbank-deposits-loans-topology-v3.json",
        "sha256": "816573106c32e7fa133cc2d371d3b5ff89a10ce307ef148655e04fb00c4614e5",
        "size_bytes": 10_320,
    },
}


class InterbankDepositsLoansFamily3RegionQueryV1Error(ValueError):
    """The Family-3 shortlist policy or its pinned vocabulary drifted."""


def _error(message: str) -> InterbankDepositsLoansFamily3RegionQueryV1Error:
    return InterbankDepositsLoansFamily3RegionQueryV1Error(message)


def _surface(value: Any, label: str) -> str:
    if type(value) is not str:
        raise _error(f"Family-3 {label} surface drifted")
    observed = unicodedata.normalize("NFC", " ".join(value.split()))
    if len(observed) < 3:
        raise _error(f"Family-3 {label} surface drifted")
    return observed


def _stable_bytes(path: Path, label: str) -> bytes:
    try:
        before = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(before.st_mode):
            raise _error(f"Family-3 {label} is not one regular nofollow file")
        payload = path.read_bytes()
        after = path.lstat()
    except OSError as exc:
        raise _error(f"Family-3 {label} cannot be read stably") from exc
    before_identity = (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_size,
        before.st_mtime_ns,
    )
    after_identity = (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_size,
        after.st_mtime_ns,
    )
    if before_identity != after_identity or len(payload) != before.st_size:
        raise _error(f"Family-3 {label} changed during stable read")
    return payload


def _content_ref(project_root: Path, relative: Path, label: str) -> dict[str, Any]:
    payload = _stable_bytes(project_root / relative, label)
    return {
        "path": relative.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _verified_trust_closure(project_root: Path) -> None:
    observed = {
        name: _content_ref(project_root, Path(reference["path"]), name.replace("_", " "))
        for name, reference in sorted(
            INTERBANK_DEPOSITS_LOANS_FAMILY3_REGION_QUERY_TRUST_CLOSURE_V1.items()
        )
    }
    if not same_typed_json_v1(
        observed,
        INTERBANK_DEPOSITS_LOANS_FAMILY3_REGION_QUERY_TRUST_CLOSURE_V1,
    ):
        raise _error("Family-3 query topology trust closure drifted")


def _topology(project_root: Path) -> dict[str, Any]:
    _verified_trust_closure(project_root)
    try:
        observed = json.loads(_stable_bytes(project_root / _TOPOLOGY_PATH, "topology spec"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("Family-3 topology JSON drifted") from exc
    if (
        type(observed) is not dict
        or observed.get("family_id") != FAMILY_ID
        or observed.get("format_version") != "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V3"
        or type(observed.get("parent")) is not dict
        or type(observed.get("children")) is not list
        or type(observed.get("hard_negative_aliases")) is not list
        or type(observed.get("structural_reset_aliases")) is not list
    ):
        raise _error("Family-3 topology identity drifted")
    return observed


def _anchor(anchor_id: str, surface: str, role: str) -> dict[str, Any]:
    return {
        "anchor_id": anchor_id,
        "canonical_alias_id": anchor_id + "_CANONICAL",
        "fts_probes": [normalize_vietnamese_anchor_v1(surface)],
        "max_edit_distance": 0,
        "role": role,
        "surface": surface,
        "verified_historical_variants": [],
    }


def _anchor_id(prefix: str, ordinal: int) -> str:
    fragment = _ID_FRAGMENT.sub("_", prefix.upper()).strip("_")
    return f"{fragment}_{ordinal:02d}"


def _sorted_unique_surfaces(values: Sequence[Any], label: str) -> list[str]:
    by_key: dict[str, str] = {}
    for value in values:
        observed = _surface(value, label)
        normalized = normalize_vietnamese_anchor_v1(observed)
        prior = by_key.get(normalized)
        if prior is None or observed < prior:
            by_key[normalized] = observed
    return sorted(by_key.values())


def _child_surfaces(topology: Mapping[str, Any]) -> dict[str, list[str]]:
    raw: dict[str, list[str]] = {}
    for child in topology["children"]:
        if type(child) is not dict or type(child.get("role")) is not str:
            raise _error("Family-3 child topology drifted")
        matchers = child.get("matchers")
        if type(matchers) is not list or not matchers:
            raise _error("Family-3 child matcher topology drifted")
        values = []
        for matcher in matchers:
            if type(matcher) is not dict or type(matcher.get("aliases")) is not list:
                raise _error("Family-3 child matcher aliases drifted")
            values.extend(matcher["aliases"])
        surfaces = _sorted_unique_surfaces(values, child["role"])
        raw[child["role"]] = surfaces
    # A surface reused by a structural group and its detailed child is one
    # retrieval anchor, never two competing semantic claims.  Structural core
    # roles take deterministic ownership because only those roles participate
    # in branchless pair rescue; all remaining aliases are assigned once in
    # sorted role order.  Generic detailed aliases therefore cannot form a
    # rescue pair even though local owner validation may conservatively retain
    # their page for the downstream topology graph.
    role_order = sorted(raw, key=lambda role: (role not in _CORE_RESCUE_ROLES, role))
    claimed: set[str] = set()
    result = {}
    for role in role_order:
        retained = []
        for surface in raw[role]:
            normalized = normalize_vietnamese_anchor_v1(surface)
            if normalized in claimed:
                continue
            retained.append(surface)
            claimed.add(normalized)
        result[role] = retained
    return {role: result[role] for role in sorted(result)}


def _query_spec(project_root: Path) -> dict[str, Any]:
    topology = _topology(project_root)
    parent = topology["parent"]
    if type(parent.get("aliases")) is not list:
        raise _error("Family-3 parent aliases drifted")
    owner_surfaces = _sorted_unique_surfaces(parent["aliases"], "owner")
    child_surfaces = _child_surfaces(topology)
    hard_negative_surfaces = _sorted_unique_surfaces(
        topology["hard_negative_aliases"], "hard negative"
    )

    anchors = []
    owner_ids = []
    for ordinal, surface in enumerate(owner_surfaces, 1):
        anchor_id = _anchor_id("OWNER_INTERBANK_ASSETS", ordinal)
        owner_ids.append(anchor_id)
        anchors.append(_anchor(anchor_id, surface, "OWNER"))

    target_ids_by_role: dict[str, list[str]] = {}
    target_surfaces_by_id: dict[str, str] = {}
    for role, surfaces in child_surfaces.items():
        target_ids_by_role[role] = []
        for ordinal, surface in enumerate(surfaces, 1):
            anchor_id = _anchor_id(f"TARGET_{role}", ordinal)
            target_ids_by_role[role].append(anchor_id)
            target_surfaces_by_id[anchor_id] = surface
            anchors.append(_anchor(anchor_id, surface, "TARGET"))

    for ordinal, surface in enumerate(hard_negative_surfaces, 1):
        anchors.append(_anchor(_anchor_id("HARD_NEGATIVE", ordinal), surface, "HARD_NEGATIVE"))

    owner_keys = [normalize_vietnamese_anchor_v1(surface) for surface in owner_surfaces]
    owner_overlap_target_ids = {
        anchor_id
        for anchor_id, surface in target_surfaces_by_id.items()
        if any(normalize_vietnamese_anchor_v1(surface) in owner for owner in owner_keys)
    }
    rescue_groups = []
    rescue_roles = sorted(_CORE_RESCUE_ROLES)
    for left_index, left_role in enumerate(rescue_roles):
        for right_role in rescue_roles[left_index + 1 :]:
            for left_id in target_ids_by_role[left_role]:
                for right_id in target_ids_by_role[right_role]:
                    ids = sorted([left_id, right_id])
                    rescue_groups.append(
                        {
                            "anchor_ids": ids,
                            "group_id": f"DISTINCT_CORE_PAIR_{left_id}_{right_id}",
                            "mode": "ALL",
                            # A short child alias that is also a substring of
                            # the explicit owner cannot borrow an adjacent
                            # sibling across a reset.  Same-page pairing is
                            # still a safe overinclusive shortlist because the
                            # second role must be independently present there.
                            "page_relation": (
                                "SAME_PAGE"
                                if set(ids) & owner_overlap_target_ids
                                else "SAME_OR_ADJACENT_PAGE"
                            ),
                            "priority": 2,
                        }
                    )

    reset_surfaces = _sorted_unique_surfaces(
        [*topology["structural_reset_aliases"], *hard_negative_surfaces],
        "structural reset",
    )
    target_ids = sorted(
        anchor_id
        for anchor_id in target_surfaces_by_id
        if anchor_id not in owner_overlap_target_ids
    )
    return {
        "anchors": sorted(anchors, key=lambda item: item["anchor_id"]),
        "family_id": FAMILY_ID,
        "format_version": _QUERY_FORMAT,
        "local_required_groups": [
            {
                "anchor_ids": target_ids,
                "group_id": "DISTINCTIVE_FAMILY3_TARGET_LOCAL",
                "mode": "ANY",
                "page_relation": "SAME_OR_ADJACENT_PAGE",
            }
        ],
        "max_hit_lines": 100_000,
        "max_selected_pages_per_document": 32,
        "neighbor_pages_after": 1,
        "neighbor_pages_before": 1,
        "seed_groups": sorted(
            [
                {
                    "anchor_ids": sorted(owner_ids),
                    "group_id": "EXPLICIT_FAMILY3_OWNER",
                    "mode": "ANY",
                    "page_relation": "SAME_OR_ADJACENT_PAGE",
                    "priority": 1,
                },
                *rescue_groups,
            ],
            key=lambda item: item["group_id"],
        ),
        "semantic_assignment_adapter_ref": _content_ref(
            project_root, _ADAPTER_PATH, "query adapter"
        ),
        "structural_reset_fragments": reset_surfaces,
        "structural_reset_max_line_ordinal": 3,
        "window_line_span": 3,
        "zero_hit_policy": "FULL_DOCUMENT_FALLBACK",
    }


_PROJECT_ROOT = Path(__file__).resolve().parents[3]
INTERBANK_DEPOSITS_LOANS_FAMILY3_REGION_QUERY_SPEC_V2 = _query_spec(_PROJECT_ROOT)


def build_interbank_deposits_loans_family3_region_query_spec_v2(
    project_root: str | Path,
) -> dict[str, Any]:
    """Return the pinned V2 Family-3 retrieval shortlist specification."""

    observed = _query_spec(Path(project_root).resolve())
    if not same_typed_json_v1(
        observed,
        INTERBANK_DEPOSITS_LOANS_FAMILY3_REGION_QUERY_SPEC_V2,
    ):
        raise _error("Family-3 query differs from its loaded trust closure")
    from bctc_ai.evaluation.family_first_region_retrieval_v1 import (
        validate_family_first_region_query_spec_v2,
    )

    return validate_family_first_region_query_spec_v2(observed)
