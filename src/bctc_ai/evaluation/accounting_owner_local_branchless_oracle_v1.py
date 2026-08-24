"""Reset-fenced, owner-local, proposal-only branchless challengers."""

from __future__ import annotations

import hashlib
import os
import stat
from bisect import bisect_right
from collections.abc import Mapping, Sequence
from itertools import combinations
from pathlib import Path
from typing import Any

from bctc_ai.evaluation import accounting_semantic_region_graph_v1 as semantic_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FORMAT_VERSION = "ACCOUNTING_OWNER_LOCAL_BRANCHLESS_ORACLE_V1"
SPEC_FORMAT_VERSION = "ACCOUNTING_OWNER_LOCAL_BRANCHLESS_SPEC_V1"
SEMANTIC_ENGINE_CONTENT_REF = {
    "path": "src/bctc_ai/evaluation/accounting_semantic_region_graph_v1.py",
    "sha256": "59542b4bab1c8c27efbc4b76b50bf829865237860b6fc67b43b2e6ccead1dccc",
    "size_bytes": 72_793,
}
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_MAX_CONTEXT_ALIASES = 64
_MAX_ROLE_AXIS = 64
_MAX_ROLE_ALIASES = 64
CLAIM_BOUNDARY = (
    "SOURCE_BOUND_CANONICAL_VISUAL_OWNER_LOCAL_RESET_FENCED_DISTINCT_ROLE_"
    "BRANCHLESS_CHALLENGER_PROPOSALS_ONLY_NO_ABSENCE_NUMERIC_SCHEMA_MAPPING_"
    "CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "absence_authority": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "pair_before_triple_uniqueness_evidence_only": True,
    "provider_serialization_controls_visual_order": False,
    "schema_authority": False,
    "zero_evidence_is_absence": False,
}
_SPEC_FIELDS = {
    "explicit_branch_aliases",
    "family_id",
    "format_version",
    "hard_veto_aliases",
    "limits",
    "owner_aliases",
    "role_axis",
    "structural_reset_aliases",
}
_LIMIT_FIELDS = {
    "continuation_page_budget",
    "max_label_line_span",
    "max_owner_distance_lines",
}


class AccountingOwnerLocalBranchlessOracleV1Error(ValueError):
    """The oracle specification, source axis, identity, or replay drifted."""


def _error(message: str) -> AccountingOwnerLocalBranchlessOracleV1Error:
    return AccountingOwnerLocalBranchlessOracleV1Error(message)


def _semantic_engine_ref() -> dict[str, Any]:
    relative = Path(SEMANTIC_ENGINE_CONTENT_REF["path"])
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    file_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    current, descriptor = -1, -1
    try:
        current = os.open(_PROJECT_ROOT, directory_flags)
        for part in relative.parts[:-1]:
            following = os.open(part, directory_flags, dir_fd=current)
            os.close(current)
            current = following
        descriptor = os.open(relative.parts[-1], file_flags, dir_fd=current)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise _error("semantic engine dependency is not one regular nofollow file")
        chunks = []
        while chunk := os.read(descriptor, 1 << 20):
            chunks.append(chunk)
        after = os.fstat(descriptor)
    except OSError as exc:
        raise _error("semantic engine dependency cannot be read stable nofollow") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if current >= 0:
            os.close(current)
    identity = lambda item: (  # noqa: E731
        item.st_dev,
        item.st_ino,
        item.st_mode,
        item.st_size,
        item.st_mtime_ns,
        item.st_ctime_ns,
    )
    payload = b"".join(chunks)
    if identity(before) != identity(after) or len(payload) != before.st_size:
        raise _error("semantic engine dependency changed during stable nofollow read")
    observed = {
        "path": relative.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    if not same_typed_json_v1(observed, SEMANTIC_ENGINE_CONTENT_REF):
        raise _error("semantic engine dependency content reference drifted")
    return canonical_clone_v1(observed)


def _spec(value: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    if (
        type(value) is not dict
        or set(value) != _SPEC_FIELDS
        or value.get("format_version") != SPEC_FORMAT_VERSION
        or type(value.get("limits")) is not dict
        or set(value["limits"]) != _LIMIT_FIELDS
        or type(value.get("role_axis")) is not list
        or not 2 <= len(value["role_axis"]) <= _MAX_ROLE_AXIS
        or any(
            type(value.get(key)) is not list or not 1 <= len(value[key]) <= _MAX_CONTEXT_ALIASES
            for key in ("explicit_branch_aliases", "owner_aliases", "hard_veto_aliases")
        )
        or type(value.get("structural_reset_aliases")) is not list
        or len(value["structural_reset_aliases"]) > _MAX_CONTEXT_ALIASES
    ):
        raise _error("owner-local branchless specification fields drifted")
    limits = value["limits"]
    if (
        type(limits["continuation_page_budget"]) is not int
        or limits["continuation_page_budget"] < 0
        or type(limits["max_label_line_span"]) is not int
        or not 1 <= limits["max_label_line_span"] <= 3
        or type(limits["max_owner_distance_lines"]) is not int
        or not 1 <= limits["max_owner_distance_lines"] <= 512
        or limits["continuation_page_budget"] > 8
    ):
        raise _error("owner-local branchless limits drifted")
    try:
        rows, seen = [], set()
        for item in value["role_axis"]:
            if (
                type(item) is not dict
                or set(item) != {"aliases", "role"}
                or type(item["aliases"]) is not list
                or not 1 <= len(item["aliases"]) <= _MAX_ROLE_ALIASES
            ):
                raise _error("owner-local branchless role fields drifted")
            role = semantic_v1._identifier(item["role"], "child role")
            if role in seen:
                raise _error("owner-local branchless child role repeats")
            seen.add(role)
            rows.append(
                {
                    "aliases": semantic_v1._aliases(item["aliases"], role),
                    "semantic_id": role,
                }
            )
        parsed = {
            "branch_aliases": semantic_v1._aliases(
                value["explicit_branch_aliases"], "explicit branch"
            ),
            "context_classes": [
                {
                    "aliases": semantic_v1._aliases(value["owner_aliases"], "owner"),
                    "allow_token_subsequence_fence": False,
                    "context_id": "OWNER_LOCAL_ORACLE_OWNER",
                    "disposition": "REQUIRED_OWNER",
                },
                {
                    "aliases": semantic_v1._aliases(value["hard_veto_aliases"], "hard veto"),
                    "allow_token_subsequence_fence": True,
                    "context_id": "OWNER_LOCAL_ORACLE_HARD_VETO",
                    "disposition": "HARD_VETO",
                },
            ],
            "family_id": semantic_v1._identifier(value["family_id"], "family ID"),
            "limits": {
                "branch_line_span": limits["max_label_line_span"],
                "context_line_span": limits["max_label_line_span"],
            },
            "row_axis": rows,
            "structural_reset_aliases": semantic_v1._aliases(
                value["structural_reset_aliases"], "structural reset", allow_empty=True
            ),
            "structural_reset_component_aliases": [],
        }
    except semantic_v1.AccountingSemanticRegionGraphV1Error as exc:
        raise _error(str(exc)) from exc
    return canonical_clone_v1(value), parsed


def _public_match(match: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: canonical_clone_v1(match[key])
        for key in ("evidence", "match_tier", "matched_aliases", "page_sequence", "surface")
    }


def _matches(
    pages: Sequence[Mapping[str, Any]], plans: Sequence[Mapping[str, Any]], spec: Mapping[str, Any]
) -> list[dict[str, Any]]:
    found = []
    for page_ordinal, (page, plan) in enumerate(zip(pages, plans, strict=True)):
        for start in range(len(page["lines"])):
            surfaces = semantic_v1._cohesive_nonvalue_surfaces(
                page["lines"], start, spec["limits"]["branch_line_span"], plan["fence_indices"]
            )
            if not surfaces:
                continue
            axes = [("EXPLICIT_BRANCH", spec["branch_aliases"])]
            axes.extend((row["semantic_id"], row["aliases"]) for row in spec["row_axis"])
            hits = []
            for semantic_id, aliases in axes:
                tier, surface, matched, _ = semantic_v1._best_alias_match(
                    surfaces, aliases, allow_bounded=False
                )
                if tier is not None and surface is not None:
                    hits.append((semantic_id, tier, surface, matched))
            role_ids = {item[0] for item in hits if item[0] != "EXPLICIT_BRANCH"}
            for semantic_id, tier, surface, aliases in hits:
                if semantic_id != "EXPLICIT_BRANCH" and len(role_ids) != 1:
                    continue
                span = max(index for index, item in enumerate(surfaces, 1) if item == surface)
                evidence = [
                    semantic_v1._line_evidence(line, page_sequence=page["page_sequence"])
                    for line in page["lines"][start : start + span]
                ]
                found.append(
                    {
                        "evidence": evidence,
                        "match_tier": tier,
                        "matched_aliases": sorted(aliases),
                        "page_ordinal": page_ordinal,
                        "page_sequence": page["page_sequence"],
                        "semantic_id": semantic_id,
                        "start": start,
                        "stop": start + span,
                        "surface": surface,
                    }
                )
    return found


def _local_components(component: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Split siblings without using their shared owner as a graph connector."""
    result = []
    current = {"branches": [], "explicit_taint": False, "roles": []}
    seen = set()
    matches = sorted(
        component["matches"],
        key=lambda item: (
            item["page_ordinal"],
            item["start"],
            item["semantic_id"] != "EXPLICIT_BRANCH",
            item["stop"],
        ),
    )
    for match in matches:
        role = match["semantic_id"]
        occupied = bool(current["branches"] or current["roles"])
        duplicate = role != "EXPLICIT_BRANCH" and role in seen
        if (role == "EXPLICIT_BRANCH" and occupied) or duplicate:
            taint = current["explicit_taint"] if duplicate else False
            result.append({**current, "owner": component["owner"]})
            current = {"branches": [], "explicit_taint": taint, "roles": []}
            seen = set()
        key = "branches" if role == "EXPLICIT_BRANCH" else "roles"
        current[key].append(match)
        if role == "EXPLICIT_BRANCH":
            current["explicit_taint"] = True
        else:
            seen.add(role)
    if current["branches"] or current["roles"]:
        result.append({**current, "owner": component["owner"]})
    return result


def _minimal_unique(
    index: int, clusters: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, Any] | None, int]:
    roles = clusters[index]["role_ids"]
    others = [set(item["role_ids"]) for other, item in enumerate(clusters) if other != index]
    triple_probes = 0
    for size in (2, 3):
        if len(roles) < size:
            continue
        for selected in combinations(roles, size):
            triple_probes += size == 3
            if not any(set(selected) <= other for other in others):
                return {
                    "combination_size": size,
                    "pair_before_triple_search": True,
                    "role_ids": list(selected),
                }, triple_probes
    return None, triple_probes


def _build(source_pages: Any, family_spec: Any) -> dict[str, Any]:
    semantic_engine_ref = _semantic_engine_ref()
    spec_value, spec = _spec(family_spec)
    try:
        pages = semantic_v1._pages(source_pages)
        plans, _comparisons, _metrics = semantic_v1._context_event_plan(pages, spec)
    except semantic_v1.AccountingSemanticRegionGraphV1Error as exc:
        raise _error(str(exc)) from exc
    offsets, total = [], 0
    for page in pages:
        offsets.append(total)
        total += len(page["lines"])
    contexts = sorted(
        (
            {**event, "page_ordinal": ordinal}
            for ordinal, plan in enumerate(plans)
            for event in plan["events"]
        ),
        key=lambda item: (item["page_ordinal"], item["stop"], item["start"]),
    )
    owners = [item for item in contexts if item["disposition"] == "REQUIRED_OWNER"]
    components = {item["context_event_id"]: {"matches": [], "owner": item} for item in owners}
    sequences = {page["page_sequence"] for page in pages}
    limits = spec_value["limits"]
    context_stops = [(item["page_ordinal"], item["stop"]) for item in contexts]
    for match in _matches(pages, plans, spec):
        context_index = bisect_right(context_stops, (match["page_ordinal"], match["start"])) - 1
        if context_index < 0 or contexts[context_index]["disposition"] != "REQUIRED_OWNER":
            continue
        owner = contexts[context_index]
        page_gap = match["page_sequence"] - owner["page_sequence"]
        bridge = set(range(owner["page_sequence"], match["page_sequence"] + 1))
        distance = (
            offsets[match["page_ordinal"]]
            + match["start"]
            - (offsets[owner["page_ordinal"]] + owner["stop"])
        )
        if (
            not 0 <= page_gap <= limits["continuation_page_budget"]
            or not bridge <= sequences
            or not 0 <= distance <= limits["max_owner_distance_lines"]
        ):
            continue
        components[owner["context_event_id"]]["matches"].append(match)
    local = [
        cluster for component in components.values() for cluster in _local_components(component)
    ]
    competitors, suppressed = [], 0
    for component in local:
        role_ids = sorted({item["semantic_id"] for item in component["roles"]})
        if len(role_ids) < 2:
            continue
        competitor = {**component, "role_ids": role_ids}
        competitors.append(competitor)
        if component["explicit_taint"]:
            suppressed += 1
    eligible = [
        (index, item) for index, item in enumerate(competitors) if not item["explicit_taint"]
    ]
    challengers, triple_probes = [], 0
    for index, component in eligible:
        role_ids = component["role_ids"]
        unique, probes = _minimal_unique(index, competitors)
        triple_probes += probes
        material = {
            "disposition": "UNRESOLVED",
            "minimal_uniqueness_evidence": unique,
            "observed_role_ids": role_ids,
            "owner": _public_match(component["owner"]),
            "page_sequences": sorted(
                {
                    component["owner"]["page_sequence"],
                    *(item["page_sequence"] for item in component["roles"]),
                }
            ),
            "role_matches": sorted(
                (
                    {**_public_match(item), "semantic_id": item["semantic_id"]}
                    for item in component["roles"]
                ),
                key=lambda item: (
                    item["page_sequence"],
                    item["evidence"][0]["bbox"],
                    item["evidence"][0]["source_line_index"],
                    item["semantic_id"],
                ),
            ),
            "status": "OWNER_LOCAL_BRANCHLESS_MULTIROLE_CHALLENGER_PROPOSAL_ONLY",
        }
        challengers.append(
            {
                **material,
                "challenger_id": "aolbov1:challenger:" + canonical_json_sha256_v1(material),
            }
        )
    challengers.sort(
        key=lambda item: (
            item["owner"]["page_sequence"],
            item["owner"]["evidence"][0]["bbox"],
            item["role_matches"][0]["evidence"][0]["bbox"],
            item["challenger_id"],
        )
    )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "bounded_absences": [],
        "challengers": challengers,
        "claim_boundary": CLAIM_BOUNDARY,
        "evidence_binding": {
            "canonical_page_evidence_sha256": canonical_json_sha256_v1(pages),
            "semantic_engine_content_ref": semantic_engine_ref,
            "spec_id": "aolbov1:spec:" + canonical_json_sha256_v1(spec_value),
        },
        "family_id": spec_value["family_id"],
        "format_version": FORMAT_VERSION,
        "metrics": {
            "challenger_count": len(challengers),
            "explicit_branch_suppressed_component_count": suppressed,
            "owner_component_count": len(owners),
            "pair_uniqueness_evidence_count": sum(
                item["minimal_uniqueness_evidence"] is not None
                and item["minimal_uniqueness_evidence"]["combination_size"] == 2
                for item in challengers
            ),
            "triple_combination_enumeration_count": triple_probes,
        },
        "status": "BRANCHLESS_CHALLENGERS_RETAINED_PROPOSAL_ONLY"
        if challengers
        else "ZERO_BRANCHLESS_CHALLENGER_PROPOSAL_ONLY",
    }
    return {**material, "result_id": "aolbov1:result:" + canonical_json_sha256_v1(material)}


def build_accounting_owner_local_branchless_oracle_v1(
    source_pages: Any, family_spec: Any
) -> dict[str, Any]:
    return _build(source_pages, family_spec)


def validate_accounting_owner_local_branchless_oracle_replay_v1(
    value: Any, source_pages: Any, family_spec: Any
) -> dict[str, Any]:
    if type(value) is not dict or value.get("format_version") != FORMAT_VERSION:
        raise _error("owner-local branchless result identity drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id", None)
    if identity != "aolbov1:result:" + canonical_json_sha256_v1(material):
        raise _error("owner-local branchless result content identity drifted")
    rebuilt = _build(source_pages, family_spec)
    if not same_typed_json_v1(value, rebuilt):
        raise _error("owner-local branchless result does not replay exactly")
    return rebuilt
