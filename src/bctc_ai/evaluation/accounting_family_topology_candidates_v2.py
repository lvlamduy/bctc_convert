"""Replayable authority for every complete family-topology candidate.

The sealed topology V1 engine intentionally removes a complete candidate when
another complete candidate exposes a strict superset of its semantic roles.
That is useful for its historical uniqueness contract, but a downstream V4
evidence comparator must first prove that a summary and a richer note describe
the same typed period, unit, and visible root total.  This add-only adapter
reuses V1's exact page/spec parsing, hit construction, boundary logic, and
candidate construction while retaining the complete axis immediately before
that legacy semantic-role pruning step.

No caller-provided candidate is trusted.  Public selection, occurrence
enumeration, and coextensive-parent projection all exact-rebuild this envelope
from the complete document pages and family spec before selecting one exact
region.  The sealed V1 engine and the existing coextensive projector are
content-pinned dependencies.
"""

from __future__ import annotations

import hashlib
import os
import stat
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bctc_ai.evaluation import accounting_family_coextensive_parent_total_v1 as total_v1
from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "AccountingFamilyTopologyCandidatesV2Error",
    "bind_accounting_family_topology_candidate_v2",
    "build_accounting_family_topology_candidates_v2",
    "enumerate_accounting_family_role_occurrences_v2",
    "project_accounting_family_coextensive_parent_total_candidate_v2",
    "validate_accounting_family_topology_candidates_replay_v2",
]


FORMAT_VERSION = "ACCOUNTING_FAMILY_TOPOLOGY_CANDIDATES_V2"
CLAIM_BOUNDARY = (
    "COMPLETE_DOCUMENT_EXACT_V1_SEMANTIC_TOPOLOGY_CANDIDATES_BEFORE_LEGACY_"
    "ROLE_SUPERSET_PRUNING_FOR_DOWNSTREAM_PERIOD_UNIT_VISIBLE_ROOT_TOTAL_"
    "EVIDENCE_ADJUDICATION_ONLY_NO_BANK_PAGE_NUMERIC_SCHEMA_OR_MAPPING_AUTHORITY"
)
_SAFETY = {
    "bank_file_page_period_scope_used_for_routing": False,
    "caller_candidate_authority": False,
    "legacy_topology_v1_bytes_changed": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "persisted_result_self_authenticating": False,
    "role_superset_alone_can_select_candidate": False,
    "schema_authority": False,
    "whole_document_exact_replay_required": True,
}
_RESULT_FIELDS = {
    "claim_boundary",
    "dependency_content_refs",
    "family_id",
    "format_version",
    "input_binding",
    "metrics",
    "near_regions",
    "regions",
    "result_id",
    "safety",
    "status",
    "uniqueness",
}
_INPUT_BINDING_FIELDS = {
    "document_pages_sha256",
    "family_spec_sha256",
    "legacy_topology_scan_id",
}
_METRIC_FIELDS = {
    "complete_region_count",
    "core_semantic_anchor_hit_count",
    "explicit_parent_region_count",
    "implied_parent_region_count",
    "legacy_complete_region_count",
    "legacy_pruned_complete_region_count",
    "near_region_count",
    "reordered_complete_region_count",
    "semantic_anchor_hit_count",
}
_UNIQUENESS_FIELDS = {
    "complete_region_count",
    "minimal_role_combination_proved",
}
_STATUSES = {
    "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL",
    "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY",
    "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS",
    "UNRESOLVED_NO_COMPLETE_REGION",
}
_MAX_COMPLETE_REGIONS = 16_384
_MAX_NEAR_REGIONS = 65_536
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEPENDENCIES = {
    "coextensive_parent_total_projector_v1": {
        "path": "src/bctc_ai/evaluation/accounting_family_coextensive_parent_total_v1.py",
        "sha256": "31a7e42e85c6b16689a1148a1ccb3d02cee18f85139b6f800bed3aa309b48e68",
        "size_bytes": 14_722,
    },
    "topology_v1": {
        "path": "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
        "sha256": "5ef1890af46826e6ac7cfd10b88e136878fbb4ad569abdb78452ad8fde60da7e",
        "size_bytes": 75_614,
    },
}


class AccountingFamilyTopologyCandidatesV2Error(ValueError):
    """The dependency, complete input, candidate axis, or replay drifted."""


def _error(message: str) -> AccountingFamilyTopologyCandidatesV2Error:
    return AccountingFamilyTopologyCandidatesV2Error(message)


@dataclass(frozen=True, slots=True, eq=False)
class _PreparedAccountingFamilyTopologyCandidateBindingV2:
    """One process-local candidate binding produced by the retained hit scan."""

    document_pages_sha256: str
    family_spec_sha256: str
    prepared_binding_sha256: str
    topology_candidates_id: str
    topology_region_sha256: str
    _binding: dict[str, Any] = field(repr=False, compare=False)
    seal: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True, eq=False)
class _PreparedAccountingFamilyTopologyCandidatesV2:
    """Sealed same-turn V1/V2 authority derived by one document hit scan."""

    document_pages_sha256: str
    family_spec_sha256: str
    legacy_topology_scan_id: str
    prepared_context_sha256: str
    topology_candidates_id: str
    _bindings: tuple[_PreparedAccountingFamilyTopologyCandidateBindingV2, ...] = field(
        repr=False, compare=False
    )
    _legacy_topology_scan: dict[str, Any] = field(repr=False, compare=False)
    _topology_candidates: dict[str, Any] = field(repr=False, compare=False)
    seal: object = field(repr=False, compare=False)


_PREPARED_TOPOLOGY_SEAL = object()


def _stable_dependency_ref(expected: Mapping[str, Any]) -> dict[str, Any]:
    path = _PROJECT_ROOT / expected["path"]
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = -1
    try:
        descriptor = os.open(path, flags)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise _error("topology-candidate dependency is not one regular nofollow file")
        chunks = []
        while chunk := os.read(descriptor, 1 << 20):
            chunks.append(chunk)
        after = os.fstat(descriptor)
    except OSError as exc:
        raise _error("topology-candidate dependency cannot be read stable nofollow") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    identity = lambda item: (  # noqa: E731
        item.st_dev,
        item.st_ino,
        item.st_mode,
        item.st_size,
        item.st_mtime_ns,
        item.st_ctime_ns,
    )
    payload = b"".join(chunks)
    observed = {
        "path": expected["path"],
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    if (
        identity(before) != identity(after)
        or len(payload) != before.st_size
        or not same_typed_json_v1(observed, expected)
    ):
        raise _error("topology-candidate dependency content reference drifted")
    return observed


def _dependency_refs() -> dict[str, dict[str, Any]]:
    return {
        name: _stable_dependency_ref(expected) for name, expected in sorted(_DEPENDENCIES.items())
    }


def _region_sort_key(region: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        region["cluster_start_document_line_ordinal"],
        region["cluster_end_document_line_ordinal_exclusive"],
        region["page_sequence"],
        canonical_json_sha256_v1(region),
    )


def _candidate_axes(
    pages: Sequence[Mapping[str, Any]], spec: Mapping[str, Any]
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
    dict[str, Any],
]:
    prepared_hits = topology_v1._document_hits(pages, spec)
    hits, line_by_document_ordinal, page_end_exclusive = prepared_hits
    explicit = topology_v1._explicit_candidates(
        hits,
        spec,
        line_by_document_ordinal=line_by_document_ordinal,
        page_end_exclusive=page_end_exclusive,
    )
    candidates = [
        *explicit,
        *topology_v1._implied_candidates(
            hits,
            spec,
            explicit,
            line_by_document_ordinal=line_by_document_ordinal,
            page_end_exclusive=page_end_exclusive,
        ),
    ]
    complete = [candidate for candidate in candidates if not candidate["unresolved_reasons"]]
    for candidate in complete:
        candidate["minimal_unique_anchor"] = topology_v1._minimal_unique_anchors(
            candidate,
            candidates,
            spec["parent"]["role"],
        )
    complete.sort(key=_region_sort_key)
    near = [candidate for candidate in candidates if candidate["unresolved_reasons"]]
    near.sort(key=_region_sort_key)
    legacy_scan = topology_v1._build_validated_scan(
        pages,
        spec,
        prepared_hits=prepared_hits,
    )
    return (
        complete,
        near,
        legacy_scan,
        {
            "explicit": explicit,
            "hits": hits,
        },
    )


def _core_semantic_anchor_hit_count(
    spec: Mapping[str, Any],
    explicit: Sequence[Mapping[str, Any]],
    hits: Mapping[str, Any],
) -> int:
    core_roles = {
        role for combination in spec["required_role_combinations"] for role in combination
    }
    if spec["presence_evidence_mode"] == "WITHIN_EXPLICIT_PARENT_CLUSTER":
        scoped_core_hits = {
            (record["role"], record["document_line_ordinal"])
            for candidate in explicit
            if any(
                record["role_kind"] != "SOURCE_ONLY_GROUP_PARENT"
                for record in candidate["child_matches"]
            )
            for record in candidate["child_matches"]
            if record["role"] in core_roles
        }
        return len(scoped_core_hits)
    return sum(len(hits["children"][role]) for role in core_roles)


def _build_material_from_candidate_axes(
    *,
    document_pages: Any,
    family_spec: Any,
    spec: Mapping[str, Any],
    complete: Sequence[Mapping[str, Any]],
    near: Sequence[Mapping[str, Any]],
    legacy_scan: Mapping[str, Any],
    axes: Mapping[str, Any],
    dependencies: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if len(complete) > _MAX_COMPLETE_REGIONS or len(near) > _MAX_NEAR_REGIONS:
        raise _error("topology-candidate bounded region denominator exceeded")
    hits = axes["hits"]
    explicit = axes["explicit"]
    semantic_anchor_hit_count = len(hits["parents"]) + sum(
        len(records) for records in hits["children"].values()
    )
    core_anchor_count = _core_semantic_anchor_hit_count(spec, explicit, hits)
    unique = len(complete) == 1 and complete[0]["minimal_unique_anchor"] is not None
    metrics = {
        "complete_region_count": len(complete),
        "core_semantic_anchor_hit_count": core_anchor_count,
        "explicit_parent_region_count": sum(
            region["parent_resolution"] == "EXPLICIT_PARENT" for region in complete
        ),
        "implied_parent_region_count": sum(
            region["parent_resolution"] == "IMPLIED_BY_REQUIRED_CHILD_CLUSTER"
            for region in complete
        ),
        "legacy_complete_region_count": len(legacy_scan["regions"]),
        "legacy_pruned_complete_region_count": len(complete) - len(legacy_scan["regions"]),
        "near_region_count": len(near),
        "reordered_complete_region_count": sum(
            not region["preferred_sibling_order_preserved"] for region in complete
        ),
        "semantic_anchor_hit_count": semantic_anchor_hit_count,
    }
    if metrics["legacy_pruned_complete_region_count"] < 0:
        raise _error("legacy topology retained more candidates than the pre-pruning axis")
    return {
        "claim_boundary": CLAIM_BOUNDARY,
        "dependency_content_refs": dependencies,
        "family_id": spec["family_id"],
        "format_version": FORMAT_VERSION,
        "input_binding": {
            "document_pages_sha256": canonical_json_sha256_v1(document_pages),
            "family_spec_sha256": canonical_json_sha256_v1(family_spec),
            "legacy_topology_scan_id": legacy_scan["scan_id"],
        },
        "metrics": metrics,
        "near_regions": canonical_clone_v1(near),
        "regions": canonical_clone_v1(complete),
        "safety": canonical_clone_v1(_SAFETY),
        "status": (
            "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
            if unique
            else "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
            if core_anchor_count == 0
            else "UNRESOLVED_NO_COMPLETE_REGION"
            if not complete
            else "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS"
        ),
        "uniqueness": {
            "complete_region_count": len(complete),
            "minimal_role_combination_proved": unique,
        },
    }


def _build_material(document_pages: Any, family_spec: Any) -> dict[str, Any]:
    dependencies = _dependency_refs()
    try:
        pages = topology_v1._pages(document_pages)
        spec = topology_v1._spec(family_spec)
        complete, near, legacy_scan, axes = _candidate_axes(pages, spec)
    except (ValueError, RuntimeError) as exc:
        raise _error("topology-candidate complete document or family spec drifted") from exc
    return _build_material_from_candidate_axes(
        document_pages=document_pages,
        family_spec=family_spec,
        spec=spec,
        complete=complete,
        near=near,
        legacy_scan=legacy_scan,
        axes=axes,
        dependencies=dependencies,
    )


def _validate_result(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _RESULT_FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or not same_typed_json_v1(value["dependency_content_refs"], _dependency_refs())
        or type(value["family_id"]) is not str
        or not value["family_id"]
        or type(value["input_binding"]) is not dict
        or set(value["input_binding"]) != _INPUT_BINDING_FIELDS
        or type(value["metrics"]) is not dict
        or set(value["metrics"]) != _METRIC_FIELDS
        or any(type(metric) is not int or metric < 0 for metric in value["metrics"].values())
        or type(value["regions"]) is not list
        or len(value["regions"]) > _MAX_COMPLETE_REGIONS
        or any(type(region) is not dict for region in value["regions"])
        or type(value["near_regions"]) is not list
        or len(value["near_regions"]) > _MAX_NEAR_REGIONS
        or any(type(region) is not dict for region in value["near_regions"])
        or value["status"] not in _STATUSES
        or type(value["uniqueness"]) is not dict
        or set(value["uniqueness"]) != _UNIQUENESS_FIELDS
    ):
        raise _error("topology-candidate result contract drifted")
    binding = value["input_binding"]
    if (
        any(
            type(binding[field]) is not str
            or len(binding[field]) != 64
            or any(character not in "0123456789abcdef" for character in binding[field])
            for field in ("document_pages_sha256", "family_spec_sha256")
        )
        or type(binding["legacy_topology_scan_id"]) is not str
        or not binding["legacy_topology_scan_id"].startswith("aftv1:scan:")
        or value["metrics"]["complete_region_count"] != len(value["regions"])
        or value["metrics"]["near_region_count"] != len(value["near_regions"])
        or value["uniqueness"]["complete_region_count"] != len(value["regions"])
        or type(value["uniqueness"]["minimal_role_combination_proved"]) is not bool
        or any(region.get("unresolved_reasons") != [] for region in value["regions"])
        or any(not region.get("unresolved_reasons") for region in value["near_regions"])
        or value["regions"] != sorted(value["regions"], key=_region_sort_key)
        or value["near_regions"] != sorted(value["near_regions"], key=_region_sort_key)
        or len({canonical_json_sha256_v1(region) for region in value["regions"]})
        != len(value["regions"])
    ):
        raise _error("topology-candidate axes or input binding drifted")
    material = canonical_clone_v1(value)
    result_id = material.pop("result_id")
    if result_id != "aftcv2:result:" + canonical_json_sha256_v1(material):
        raise _error("topology-candidate result identity drifted")
    return canonical_clone_v1(value)


def build_accounting_family_topology_candidates_v2(
    document_pages: Any,
    family_spec: Any,
) -> dict[str, Any]:
    """Retain every complete V1-built candidate before role-superset pruning."""

    material = _build_material(document_pages, family_spec)
    return _validate_result(
        {
            **material,
            "result_id": "aftcv2:result:" + canonical_json_sha256_v1(material),
        }
    )


def validate_accounting_family_topology_candidates_replay_v2(
    value: Any,
    document_pages: Any,
    family_spec: Any,
) -> dict[str, Any]:
    """Exact-rebuild the complete pre-pruning candidate axis from source."""

    persisted = _validate_result(value)
    expected = build_accounting_family_topology_candidates_v2(document_pages, family_spec)
    if not same_typed_json_v1(persisted, expected):
        raise _error("topology-candidate result does not replay exactly")
    return persisted


def _selected_replayed_candidate(
    document_pages: Any,
    family_spec: Any,
    topology_candidates: Any,
    topology_region: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    persisted = validate_accounting_family_topology_candidates_replay_v2(
        topology_candidates,
        document_pages,
        family_spec,
    )
    if type(topology_region) is not dict:
        raise _error("topology candidate selection must be one exact region object")
    selected = [
        region for region in persisted["regions"] if same_typed_json_v1(region, topology_region)
    ]
    if len(selected) != 1:
        raise _error("selected region is not one exact replayed complete candidate")
    try:
        pages = topology_v1._pages(document_pages)
        spec = topology_v1._spec(family_spec)
        hits, _line_axis, _page_axis = topology_v1._document_hits(pages, spec)
        occurrences = topology_v1._child_records_in_range(
            hits["children"],
            spec,
            retain_all_occurrences=True,
            start=selected[0]["cluster_start_document_line_ordinal"],
            stop=selected[0]["cluster_end_document_line_ordinal_exclusive"],
        )
    except (ValueError, RuntimeError) as exc:
        raise _error("selected topology candidate occurrence replay drifted") from exc
    return canonical_clone_v1(selected[0]), canonical_clone_v1(occurrences), spec


def _project_coextensive_total(
    selected: Mapping[str, Any],
    spec: Mapping[str, Any],
) -> dict[str, Any]:
    region = canonical_clone_v1(selected)
    try:
        total = total_v1._eligible_total_role(spec)
    except total_v1.AccountingFamilyCoextensiveParentTotalV1Error as exc:
        raise _error("coextensive topology-candidate TOTAL declaration drifted") from exc
    parent = region["parent_match"]
    if (
        total is None
        or parent is None
        or not parent["match_kind"].startswith("EXACT_ACCENTLESS")
        or any(match["role"] == total["role"] for match in region["child_matches"])
    ):
        return region
    record = {
        **canonical_clone_v1(parent),
        "preferred_ordinal": total["preferred_ordinal"],
        "presence": total["presence"],
        "role": total["role"],
        "role_kind": total["role_kind"],
    }
    if spec["spec_format_version"] == topology_v1.SPEC_FORMAT_VERSION_V3:
        record["matched_within_role"] = None
    region["child_matches"].append(record)
    region["child_matches"].sort(
        key=lambda item: (
            item["document_line_ordinal"],
            item["preferred_ordinal"],
            item["end_document_line_ordinal"],
            item["role"],
        )
    )
    region["observed_roles"] = [item["role"] for item in region["child_matches"]]
    region["preferred_sibling_order_preserved"] = region["observed_roles"] == [
        item["role"]
        for item in sorted(region["child_matches"], key=lambda item: item["preferred_ordinal"])
    ]
    return region


def _prepared_binding_material(
    binding: Mapping[str, Any],
    *,
    document_pages_sha256: str,
    family_spec_sha256: str,
    topology_candidates_id: str,
    topology_region_sha256: str,
) -> dict[str, Any]:
    return {
        "binding_sha256": canonical_json_sha256_v1(binding),
        "document_pages_sha256": document_pages_sha256,
        "family_spec_sha256": family_spec_sha256,
        "topology_candidates_id": topology_candidates_id,
        "topology_region_sha256": topology_region_sha256,
    }


def _prepare_candidate_binding(
    *,
    document_pages_sha256: str,
    family_spec_sha256: str,
    topology_candidates_id: str,
    topology_region: Mapping[str, Any],
    occurrences: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any],
) -> _PreparedAccountingFamilyTopologyCandidateBindingV2:
    selected = canonical_clone_v1(topology_region)
    binding = {
        "effective_topology_region": _project_coextensive_total(selected, spec),
        "role_occurrences": canonical_clone_v1(occurrences),
        "topology_candidates_id": topology_candidates_id,
        "topology_region": selected,
    }
    region_sha256 = canonical_json_sha256_v1(selected)
    material = _prepared_binding_material(
        binding,
        document_pages_sha256=document_pages_sha256,
        family_spec_sha256=family_spec_sha256,
        topology_candidates_id=topology_candidates_id,
        topology_region_sha256=region_sha256,
    )
    return _PreparedAccountingFamilyTopologyCandidateBindingV2(
        document_pages_sha256=document_pages_sha256,
        family_spec_sha256=family_spec_sha256,
        prepared_binding_sha256=canonical_json_sha256_v1(material),
        topology_candidates_id=topology_candidates_id,
        topology_region_sha256=region_sha256,
        _binding=binding,
        seal=_PREPARED_TOPOLOGY_SEAL,
    )


def _prepared_accounting_family_topology_candidate_binding_content_v2(
    value: Any,
    *,
    topology_candidates: Mapping[str, Any],
    topology_region: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one sealed same-turn binding without replaying the document."""

    if (
        type(value) is not _PreparedAccountingFamilyTopologyCandidateBindingV2
        or value.seal is not _PREPARED_TOPOLOGY_SEAL
        or type(topology_candidates) is not dict
        or type(topology_region) is not dict
        or value.topology_candidates_id != topology_candidates.get("result_id")
        or value.topology_region_sha256 != canonical_json_sha256_v1(topology_region)
    ):
        raise _error("prepared topology-candidate binding identity drifted")
    binding = value._binding  # noqa: SLF001
    material = _prepared_binding_material(
        binding,
        document_pages_sha256=value.document_pages_sha256,
        family_spec_sha256=value.family_spec_sha256,
        topology_candidates_id=value.topology_candidates_id,
        topology_region_sha256=value.topology_region_sha256,
    )
    if (
        value.prepared_binding_sha256 != canonical_json_sha256_v1(material)
        or binding.get("topology_candidates_id") != value.topology_candidates_id
        or not same_typed_json_v1(binding.get("topology_region"), topology_region)
    ):
        raise _error("prepared topology-candidate binding content drifted")
    return canonical_clone_v1(binding)


def _validate_prepared_accounting_family_topology_candidate_binding_v2(
    value: Any,
    *,
    document_pages: Any,
    family_spec: Any,
    topology_candidates: Mapping[str, Any],
    topology_region: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind a sealed candidate to the current exact pages and family spec."""

    if (
        type(value) is not _PreparedAccountingFamilyTopologyCandidateBindingV2
        or value.document_pages_sha256 != canonical_json_sha256_v1(document_pages)
        or value.family_spec_sha256 != canonical_json_sha256_v1(family_spec)
    ):
        raise _error("prepared topology-candidate source binding drifted")
    return _prepared_accounting_family_topology_candidate_binding_content_v2(
        value,
        topology_candidates=topology_candidates,
        topology_region=topology_region,
    )


def _prepared_context_material(
    *,
    document_pages_sha256: str,
    family_spec_sha256: str,
    legacy_topology_scan: Mapping[str, Any],
    topology_candidates: Mapping[str, Any],
    bindings: Sequence[_PreparedAccountingFamilyTopologyCandidateBindingV2],
) -> dict[str, Any]:
    return {
        "binding_sha256_axis": [binding.prepared_binding_sha256 for binding in bindings],
        "document_pages_sha256": document_pages_sha256,
        "family_spec_sha256": family_spec_sha256,
        "legacy_topology_scan_sha256": canonical_json_sha256_v1(legacy_topology_scan),
        "topology_candidates_sha256": canonical_json_sha256_v1(topology_candidates),
    }


def _prepare_accounting_family_topology_candidates_v2(
    document_pages: Any,
    family_spec: Any,
) -> _PreparedAccountingFamilyTopologyCandidatesV2:
    """Build V1 scan, V2 envelope, and all bindings from one retained hit scan."""

    dependencies = _dependency_refs()
    try:
        pages = topology_v1._pages(document_pages)
        spec = topology_v1._spec(family_spec)
        complete, near, legacy_scan, axes = _candidate_axes(pages, spec)
    except (ValueError, RuntimeError) as exc:
        raise _error("prepared topology-candidate source authority drifted") from exc
    material = _build_material_from_candidate_axes(
        document_pages=document_pages,
        family_spec=family_spec,
        spec=spec,
        complete=complete,
        near=near,
        legacy_scan=legacy_scan,
        axes=axes,
        dependencies=dependencies,
    )
    topology_candidates = _validate_result(
        {
            **material,
            "result_id": "aftcv2:result:" + canonical_json_sha256_v1(material),
        }
    )
    document_sha256 = topology_candidates["input_binding"]["document_pages_sha256"]
    family_sha256 = topology_candidates["input_binding"]["family_spec_sha256"]
    hits = axes["hits"]
    bindings = []
    for region in complete:
        try:
            occurrences = topology_v1._child_records_in_range(
                hits["children"],
                spec,
                retain_all_occurrences=True,
                start=region["cluster_start_document_line_ordinal"],
                stop=region["cluster_end_document_line_ordinal_exclusive"],
            )
        except (ValueError, RuntimeError) as exc:
            raise _error("prepared topology-candidate occurrence binding drifted") from exc
        bindings.append(
            _prepare_candidate_binding(
                document_pages_sha256=document_sha256,
                family_spec_sha256=family_sha256,
                topology_candidates_id=topology_candidates["result_id"],
                topology_region=region,
                occurrences=occurrences,
                spec=spec,
            )
        )
    binding_axis = tuple(bindings)
    context_material = _prepared_context_material(
        document_pages_sha256=document_sha256,
        family_spec_sha256=family_sha256,
        legacy_topology_scan=legacy_scan,
        topology_candidates=topology_candidates,
        bindings=binding_axis,
    )
    return _PreparedAccountingFamilyTopologyCandidatesV2(
        document_pages_sha256=document_sha256,
        family_spec_sha256=family_sha256,
        legacy_topology_scan_id=legacy_scan["scan_id"],
        prepared_context_sha256=canonical_json_sha256_v1(context_material),
        topology_candidates_id=topology_candidates["result_id"],
        _bindings=binding_axis,
        _legacy_topology_scan=legacy_scan,
        _topology_candidates=topology_candidates,
        seal=_PREPARED_TOPOLOGY_SEAL,
    )


def _prepared_accounting_family_topology_authority_v2(
    value: Any,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    tuple[_PreparedAccountingFamilyTopologyCandidateBindingV2, ...],
]:
    """Open a sealed same-turn authority; persisted data still uses public replay."""

    if (
        type(value) is not _PreparedAccountingFamilyTopologyCandidatesV2
        or value.seal is not _PREPARED_TOPOLOGY_SEAL
    ):
        raise _error("prepared topology-candidate context identity drifted")
    legacy_scan = value._legacy_topology_scan  # noqa: SLF001
    topology_candidates = value._topology_candidates  # noqa: SLF001
    bindings = value._bindings  # noqa: SLF001
    if (
        type(legacy_scan) is not dict
        or type(topology_candidates) is not dict
        or type(bindings) is not tuple
        or value.legacy_topology_scan_id != legacy_scan.get("scan_id")
        or value.topology_candidates_id != topology_candidates.get("result_id")
        or topology_candidates.get("input_binding", {}).get("document_pages_sha256")
        != value.document_pages_sha256
        or topology_candidates.get("input_binding", {}).get("family_spec_sha256")
        != value.family_spec_sha256
        or topology_candidates.get("input_binding", {}).get("legacy_topology_scan_id")
        != value.legacy_topology_scan_id
        or len(bindings) != len(topology_candidates.get("regions", ()))
    ):
        raise _error("prepared topology-candidate context binding drifted")
    for binding, region in zip(bindings, topology_candidates["regions"], strict=True):
        if (
            binding.document_pages_sha256 != value.document_pages_sha256
            or binding.family_spec_sha256 != value.family_spec_sha256
        ):
            raise _error("prepared topology-candidate binding source axis drifted")
        _prepared_accounting_family_topology_candidate_binding_content_v2(
            binding,
            topology_candidates=topology_candidates,
            topology_region=region,
        )
    context_material = _prepared_context_material(
        document_pages_sha256=value.document_pages_sha256,
        family_spec_sha256=value.family_spec_sha256,
        legacy_topology_scan=legacy_scan,
        topology_candidates=topology_candidates,
        bindings=bindings,
    )
    if value.prepared_context_sha256 != canonical_json_sha256_v1(context_material):
        raise _error("prepared topology-candidate context content drifted")
    return legacy_scan, topology_candidates, bindings


def bind_accounting_family_topology_candidate_v2(
    document_pages: Any,
    family_spec: Any,
    topology_candidates: Any,
    topology_region: Any,
) -> dict[str, Any]:
    """Replay and bind one candidate, all occurrences, and its owner total."""

    selected, occurrences, spec = _selected_replayed_candidate(
        document_pages,
        family_spec,
        topology_candidates,
        topology_region,
    )
    return {
        "effective_topology_region": _project_coextensive_total(selected, spec),
        "role_occurrences": occurrences,
        "topology_candidates_id": topology_candidates["result_id"],
        "topology_region": selected,
    }


def enumerate_accounting_family_role_occurrences_v2(
    document_pages: Any,
    family_spec: Any,
    topology_candidates: Any,
    topology_region: Any,
) -> list[dict[str, Any]]:
    """Return all role occurrences from one exact replayed V2 candidate."""

    return bind_accounting_family_topology_candidate_v2(
        document_pages,
        family_spec,
        topology_candidates,
        topology_region,
    )["role_occurrences"]


def project_accounting_family_coextensive_parent_total_candidate_v2(
    document_pages: Any,
    family_spec: Any,
    topology_candidates: Any,
    topology_region: Any,
) -> dict[str, Any]:
    """Project an exact owner-row total only after candidate-source replay."""

    return bind_accounting_family_topology_candidate_v2(
        document_pages,
        family_spec,
        topology_candidates,
        topology_region,
    )["effective_topology_region"]
