from __future__ import annotations

import hashlib
import stat
from pathlib import Path
from typing import Any

from bctc_ai.evaluation import (
    accounting_owner_local_branchless_oracle_v1 as owner_v1,
)
from bctc_ai.evaluation.accounting_family_topology_v1 import (
    AccountingFamilyTopologyV1Error,
    build_accounting_family_topology_scan_v1,
)
from bctc_ai.evaluation.provision_movement_family13_region_query_v1 import (
    FAMILY_ID,
    build_provision_movement_family13_topology_spec_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "ProvisionMovementFamily13FullStructuralOracleV1Error",
    "build_provision_movement_family13_full_structural_oracle_v1",
    "validate_provision_movement_family13_full_structural_oracle_replay_v1",
]

FORMAT_VERSION = "PROVISION_MOVEMENT_FAMILY13_FULL_STRUCTURAL_ORACLE_V1"
CLAIM_BOUNDARY = (
    "SUPPLIED_CONTIGUOUS_SOURCE_PAGE_AXIS_STRUCTURAL_PROPOSAL_ONLY_"
    "NO_COMPLETE_DOCUMENT_OR_ABSENCE_NUMERIC_SIGN_UNIT_SCHEMA_MAPPING_EXPORT_AUTHORITY"
)
DEPENDENCY_REFS = {
    "family13_adapter_ref": {
        "path": "src/bctc_ai/evaluation/provision_movement_family13_region_query_v1.py",
        "sha256": "68027613245fe66d5ebddb8a90599c18e1c72a72891af345caa6e77b5f000800",
        "size_bytes": 14_815,
    },
    "owner_local_oracle_ref": {
        "path": "src/bctc_ai/evaluation/accounting_owner_local_branchless_oracle_v1.py",
        "sha256": "30f61c8bd7b658ee58a9dd2b4f274426b72695b6bd419615782f7c666426d51d",
        "size_bytes": 18_638,
    },
    "topology_engine_ref": {
        "path": "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
        "sha256": "409cd254f7a43f641f3f3728b05e45ba79d9fe607bcd0837984575b09642b5c0",
        "size_bytes": 79_501,
    },
}
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_AUTHORITY = {
    "absence_authority": False,
    "complete_document_authority": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "schema_authority": False,
    "sign_authority": False,
    "unit_authority": False,
    "zero_evidence_is_document_absence": False,
}
_RESULT_FIELDS = set(
    "authority claim_boundary dependency_refs evidence_binding family_id format_version "
    "metrics owner_local_oracle result_id status structural_region topology_scan".split()
)
_LANE_ROLES = (
    "GENERAL_PROVISION_LANE",
    "SPECIFIC_PROVISION_LANE",
    "MARGIN_ADVANCE_PROVISION_LANE",
)
_CORE_ROLES = (
    "OPENING_BALANCE_ROW",
    "PROVISION_OR_REVERSAL_ROW",
    "CLOSING_BALANCE_ROW",
)
_EXACT_MATCH_KINDS = {
    "EXACT_ACCENTLESS_ALIAS",
    "EXACT_ACCENTLESS_ALIAS_AFTER_ENUMERATION_PREFIX",
}


class ProvisionMovementFamily13FullStructuralOracleV1Error(ValueError):
    """The Family-13 source packet, dependency, result, or replay drifted."""


def _error(message: str) -> ProvisionMovementFamily13FullStructuralOracleV1Error:
    return ProvisionMovementFamily13FullStructuralOracleV1Error(message)


def _verified_dependencies() -> dict[str, Any]:
    observed = {}
    for name, reference in sorted(DEPENDENCY_REFS.items()):
        path = _PROJECT_ROOT / reference["path"]
        try:
            before = path.lstat()
            if path.is_symlink() or not stat.S_ISREG(before.st_mode):
                raise _error(f"Family-13 {name} is not one regular nofollow file")
            payload = path.read_bytes()
            after = path.lstat()
        except OSError as exc:
            raise _error(f"Family-13 {name} cannot be read stably") from exc
        identity = lambda item: (  # noqa: E731
            item.st_dev,
            item.st_ino,
            item.st_mode,
            item.st_size,
            item.st_mtime_ns,
        )
        if identity(before) != identity(after) or len(payload) != before.st_size:
            raise _error(f"Family-13 {name} changed during stable read")
        observed[name] = {
            "path": reference["path"],
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }
    if not same_typed_json_v1(observed, DEPENDENCY_REFS):
        raise _error("Family-13 structural-oracle dependency content reference drifted")
    return canonical_clone_v1(observed)


def _source_axis(value: Any) -> list[dict[str, Any]]:
    if type(value) is not list or not value:
        raise _error("Family-13 requires one non-empty exact source-page list")
    if any(type(page) is not dict or "page_sequence" not in page for page in value):
        raise _error("Family-13 source-page packet fields drifted")
    sequences = [page["page_sequence"] for page in value]
    if any(type(sequence) is not int for sequence in sequences):
        raise _error("Family-13 page sequence must be one exact integer")
    if sorted(sequences) != list(range(1, len(value) + 1)):
        raise _error("Family-13 page sequence must cover exactly 1..N without gaps")
    return sorted(value, key=lambda page: page["page_sequence"])


def _topology_pages(source_pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "lines": sorted(
                (canonical_clone_v1(line) for line in page["lines"]),
                key=lambda line: line["source_line_index"],
            ),
            "page_sequence": page["page_sequence"],
        }
        for page in source_pages
    ]


def _owner_spec(topology_spec: dict[str, Any]) -> dict[str, Any]:
    children = {child["role"]: child for child in topology_spec["children"]}
    aliases = lambda role: [  # noqa: E731
        alias for matcher in children[role]["matchers"] for alias in matcher["aliases"]
    ]
    return {
        "explicit_branch_aliases": [alias for role in _LANE_ROLES for alias in aliases(role)],
        "family_id": FAMILY_ID,
        "format_version": owner_v1.SPEC_FORMAT_VERSION,
        "hard_veto_aliases": topology_spec["hard_negative_aliases"],
        "limits": {
            "continuation_page_budget": 1,
            "max_label_line_span": 3,
            "max_owner_distance_lines": 96,
        },
        "owner_aliases": topology_spec["parent"]["aliases"],
        "role_axis": [{"aliases": aliases(role), "role": role} for role in _CORE_ROLES],
        "structural_reset_aliases": topology_spec["structural_reset_aliases"],
    }


def _exact_explicit_region(topology_scan: dict[str, Any]) -> dict[str, Any] | None:
    if len(topology_scan["regions"]) != 1 or topology_scan["near_regions"]:
        return None
    region = topology_scan["regions"][0]
    matches = {item["role"]: item for item in region["child_matches"]}
    required = {*_CORE_ROLES, *(role for role in _LANE_ROLES if role in matches)}
    if (
        region["parent_resolution"] != "EXPLICIT_PARENT"
        or region["parent_match"]["match_kind"] not in _EXACT_MATCH_KINDS
        or not set(_CORE_ROLES) <= matches.keys()
        or not any(role in matches for role in _LANE_ROLES)
        or any(matches[role]["match_kind"] not in _EXACT_MATCH_KINDS for role in required)
        or not topology_scan["uniqueness"]["minimal_role_combination_proved"]
    ):
        return None
    return region


def _build(source_pages: Any) -> dict[str, Any]:
    dependencies = _verified_dependencies()
    pages = _source_axis(source_pages)
    topology_spec = build_provision_movement_family13_topology_spec_v1()
    owner_spec = _owner_spec(topology_spec)
    try:
        owner_oracle = owner_v1.build_accounting_owner_local_branchless_oracle_v1(pages, owner_spec)
        topology_scan = build_accounting_family_topology_scan_v1(
            _topology_pages(pages), topology_spec
        )
    except (
        owner_v1.AccountingOwnerLocalBranchlessOracleV1Error,
        AccountingFamilyTopologyV1Error,
    ) as exc:
        raise _error(str(exc)) from exc
    region = _exact_explicit_region(topology_scan)
    oracle_zero = not owner_oracle["challengers"]
    ready = region is not None and oracle_zero
    core_hits = topology_scan["metrics"]["core_semantic_anchor_hit_count"]
    topology_zero = (
        topology_scan["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
        and type(core_hits) is int
        and core_hits == 0
        and not topology_scan["regions"]
        and not topology_scan["near_regions"]
    )
    status = (
        "STRUCTURAL_READY_PROPOSAL_ONLY"
        if ready
        else "NOT_OBSERVED_PROPOSAL_ONLY"
        if topology_zero and oracle_zero
        else "UNRESOLVED_STRUCTURAL_CHALLENGER_PROPOSAL_ONLY"
    )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "dependency_refs": dependencies,
        "evidence_binding": {
            "canonical_page_evidence_sha256": owner_oracle["evidence_binding"][
                "canonical_page_evidence_sha256"
            ],
            "owner_oracle_result_id": owner_oracle["result_id"],
            "topology_scan_id": topology_scan["scan_id"],
        },
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "metrics": {
            "owner_local_challenger_count": len(owner_oracle["challengers"]),
            "source_page_count": len(pages),
            "topology_complete_region_count": len(topology_scan["regions"]),
            "topology_near_region_count": len(topology_scan["near_regions"]),
        },
        "owner_local_oracle": owner_oracle,
        "status": status,
        "structural_region": canonical_clone_v1(region) if ready else None,
        "topology_scan": topology_scan,
    }
    return {
        **material,
        "result_id": "pmf13fsov1:result:" + canonical_json_sha256_v1(material),
    }


def build_provision_movement_family13_full_structural_oracle_v1(
    source_pages: Any,
) -> dict[str, Any]:
    return _build(source_pages)


def validate_provision_movement_family13_full_structural_oracle_replay_v1(
    value: Any, source_pages: Any
) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _RESULT_FIELDS
        or value.get("format_version") != FORMAT_VERSION
        or value.get("family_id") != FAMILY_ID
        or value.get("claim_boundary") != CLAIM_BOUNDARY
        or not same_typed_json_v1(value.get("authority"), _AUTHORITY)
    ):
        raise _error("Family-13 structural-oracle result identity drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id", None)
    if identity != "pmf13fsov1:result:" + canonical_json_sha256_v1(material):
        raise _error("Family-13 structural-oracle content identity drifted")
    rebuilt = _build(source_pages)
    if not same_typed_json_v1(value, rebuilt):
        raise _error("Family-13 structural-oracle result does not replay exactly")
    return rebuilt
