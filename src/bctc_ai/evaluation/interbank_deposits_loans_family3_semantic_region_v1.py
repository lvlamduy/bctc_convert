from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.accounting_semantic_region_graph_v1 import (
    SPEC_FORMAT_VERSION as SEMANTIC_SPEC_FORMAT_VERSION,
)
from bctc_ai.evaluation.accounting_semantic_region_graph_v1 import (
    AccountingSemanticRegionGraphV1Error,
    ScopedTableEnforcementV1,
    build_accounting_semantic_region_graph_v1,
)
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FAMILY_ID = "INTERBANK_DEPOSITS_AND_LOANS"
FORMAT_VERSION = "INTERBANK_DEPOSITS_LOANS_FAMILY3_SEMANTIC_REGION_ADAPTER_V1"
CLAIM_BOUNDARY = (
    "DECLARATIVE_FAMILY3_EXPLICIT_OWNER_BRANCH_CHILD_RESET_HARD_VETO_AND_SHARED_"
    "GEOMETRY_PROPOSALS_REQUIRES_FULL_DOCUMENT_BRANCHLESS_ORACLE_NO_NUMERIC_"
    "PERIOD_UNIT_SCHEMA_MAPPING_ABSENCE_OR_EXPORT_AUTHORITY"
)
_TOPOLOGY_PATH = Path("config/families/tm-interbank-deposits-loans-topology-v3.json")
_EVALUATION_PATH = Path("config/families/tm-interbank-deposits-loans-evaluation-v3.json")
_CONFIG_PINS = {
    _TOPOLOGY_PATH: ("816573106c32e7fa133cc2d371d3b5ff89a10ce307ef148655e04fb00c4614e5", 10_320),
    _EVALUATION_PATH: ("0db7cfe8efe522822abf0ab8b716182300d0314c75f26af3197357a966aa9772", 2_280),
}
_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class InterbankDepositsLoansFamily3SemanticRegionV1Error(ValueError): ...


def _error(message: str) -> InterbankDepositsLoansFamily3SemanticRegionV1Error:
    return InterbankDepositsLoansFamily3SemanticRegionV1Error(message)


def _config_json(project_root: Path, relative: Path, label: str) -> tuple[dict, dict]:
    path = project_root / relative
    try:
        payload = path.read_bytes()
        value = json.loads(payload)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"Family-3 {label} cannot be read as JSON") from exc
    if type(value) is not dict:
        raise _error(f"Family-3 {label} has no object root")
    reference = {
        "path": relative.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    if (reference["sha256"], reference["size_bytes"]) != _CONFIG_PINS[relative]:
        raise _error(f"Family-3 {label} literal config pin drifted")
    return value, reference


def _aliases(value: Any, label: str) -> list[str]:
    if type(value) is not list or not value:
        raise _error(f"Family-3 {label} aliases drifted")
    by_normalized: dict[str, str] = {}
    for item in value:
        if type(item) is not str or not item.strip():
            raise _error(f"Family-3 {label} alias drifted")
        normalized = normalize_vietnamese_anchor_v1(item)
        if not normalized:
            raise _error(f"Family-3 {label} alias normalized empty")
        prior = by_normalized.get(normalized)
        if prior is None or item < prior:
            by_normalized[normalized] = item
    return [by_normalized[key] for key in sorted(by_normalized)]


def _loaded_configs(project_root: Path) -> tuple[dict, dict]:
    topology, topology_ref = _config_json(project_root, _TOPOLOGY_PATH, "topology V3")
    _evaluation, evaluation_ref = _config_json(project_root, _EVALUATION_PATH, "evaluation V3")
    return topology, {"evaluation_spec_ref": evaluation_ref, "topology_spec_ref": topology_ref}


def _child_aliases(topology: Mapping[str, Any]) -> dict[str, list[str]]:
    return {
        child["role"]: _aliases(
            [alias for matcher in child["matchers"] for alias in matcher["aliases"]],
            child["role"],
        )
        for child in topology["children"]
    }


def _scoped_limits(topology: Mapping[str, Any]) -> dict[str, int]:
    span = topology["limits"]["max_cluster_span_lines"]
    return {
        "axis_tolerance_ppm": 120_000,
        "continuation_page_budget": 0,
        "max_owner_distance_lines": span,
        "max_role_gap_lines": span,
        "max_wrap_lines": topology["limits"]["max_label_line_span"],
        "minimum_cell_row_overlap_ppm": 400_000,
        "unlabeled_total_gap_jitter_ppm": 100_000,
        "unlabeled_total_max_gap_lines": min(4, span),
        "unlabeled_total_max_numeric_columns": 16,
        "unlabeled_total_min_numeric_columns": 2,
    }


def _policy(project_root: Path) -> dict[str, Any]:
    topology, refs = _loaded_configs(project_root)
    aliases = _child_aliases(topology)
    combinations = [list(item) for item in topology["required_role_combinations"]]
    structural_roles = sorted({role for item in combinations for role in item})
    owner_aliases = _aliases(topology["parent"]["aliases"], "owner")
    veto_aliases = _aliases(topology["hard_negative_aliases"], "hard negative")
    reset_aliases = _aliases(topology["structural_reset_aliases"], "structural reset")
    semantic_passes = []
    for combination in combinations:
        branch_role = combination[0]
        rows = {role: aliases[role] for role in combination[1:]}
        semantic_passes.append(
            {
                "branch_role": branch_role,
                "required_role_combination": combination,
                "semantic_spec": {
                    "branch_aliases": aliases[branch_role],
                    "context_classes": [
                        {
                            "aliases": owner_aliases,
                            "context_id": "FAMILY3_EXPLICIT_OWNER",
                            "disposition": "REQUIRED_OWNER",
                        },
                        {
                            "aliases": veto_aliases,
                            "allow_token_subsequence_fence": True,
                            "context_id": "FAMILY3_HARD_VETO",
                            "disposition": "HARD_VETO",
                        },
                    ],
                    "family_id": FAMILY_ID,
                    "format_version": SEMANTIC_SPEC_FORMAT_VERSION,
                    "limits": {
                        "branch_line_span": topology["limits"]["max_label_line_span"],
                        "context_line_span": topology["limits"]["max_label_line_span"],
                        "context_page_budget": topology["limits"]["max_continuation_pages"],
                        "maximum_body_lines_per_page": topology["limits"]["max_cluster_span_lines"],
                        "row_label_line_span": topology["limits"]["max_label_line_span"],
                    },
                    "required_owner_context_id": "FAMILY3_EXPLICIT_OWNER",
                    "row_axis": [
                        {
                            "aliases": rows[role],
                            "bounded_edit_on_exact_miss": False,
                            "semantic_id": role,
                        }
                        for role in sorted(rows)
                    ],
                    "scoped_table": {
                        "continuation_aliases": [],
                        "enforcement": ScopedTableEnforcementV1.REQUIRED_PROMOTION_GATE.value,
                        "hard_veto_scope_aliases": veto_aliases,
                        "layout_modes": ["ROLES_AS_ROWS"],
                        "limits": _scoped_limits(topology),
                        "require_trailing_total_for_roles_as_columns": False,
                        "trailing_total_aliases": [],
                    },
                    "source_only_ambiguities": [],
                    "structural_reset_aliases": reset_aliases,
                },
            }
        )
    material = {
        "config_binding": refs,
        "family_id": FAMILY_ID,
        "format_version": "INTERBANK_DEPOSITS_LOANS_FAMILY3_SEMANTIC_POLICY_V1",
        "required_role_combinations": combinations,
        "semantic_passes": semantic_passes,
        "structural_roles": structural_roles,
    }
    return {**material, "policy_id": "f3srv1:policy:" + canonical_json_sha256_v1(material)}


def _geometry_support(region: Mapping[str, Any], evidence: Sequence[Mapping[str, Any]]) -> bool:
    geometry = region["adaptive_geometry_v2"]
    atom_ids = {f"p{item['page_sequence']}:l{item['source_line_index']}" for item in evidence}
    row_ordinals = {
        band["row_ordinal"] for band in geometry["row_bands"] if atom_ids & set(band["atom_ids"])
    }
    return any(
        assignment["status"] == "ASSIGNED_TO_UNIQUE_ROW_LANE"
        and assignment["row_ordinal"] in row_ordinals
        for assignment in geometry["assignments"]
    )


def _equivalence_keys(
    branch: Mapping[str, Any], rows: Sequence[Mapping[str, Any]], structural_roles: set[str]
) -> list[str]:
    evidence = list(branch["evidence"])
    evidence.extend(
        item for row in rows if row["semantic_id"] in structural_roles for item in row["evidence"]
    )
    return sorted({f"p{item['page_sequence']}:l{item['source_line_index']}" for item in evidence})


def _candidate(
    region: Mapping[str, Any], semantic_pass: Mapping[str, Any], policy: Mapping[str, Any]
) -> dict[str, Any]:
    branch_role = semantic_pass["branch_role"]
    structural_roles = set(policy["structural_roles"])
    rows_by_role: dict[str, list[Mapping[str, Any]]] = {}
    for row in region["row_proposals"]:
        if row["semantic_id"] in structural_roles:
            rows_by_role.setdefault(row["semantic_id"], []).append(row)
    observed = {branch_role, *rows_by_role}
    declared = semantic_pass["required_role_combination"]
    matched = [declared] if set(declared) <= observed else []
    complete = []
    branch_supported = _geometry_support(region, region["branch"]["evidence"])
    for combination in matched:
        row_roles = [role for role in combination if role != branch_role]
        row_geometry = all(
            len(rows_by_role.get(role, [])) == 1
            and rows_by_role[role][0]["status"]
            == "SEMANTIC_ROW_TEXT_AND_GEOMETRY_PROPOSAL_REQUIRES_REPLAY"
            for role in row_roles
        )
        scoped_status = region["shared_scoped_table_v1"]["status"]
        scoped_complete = scoped_status == (
            "SHARED_SCOPED_TABLE_PROPOSAL_RETAINED_NO_MAPPING_AUTHORITY"
        ) or (len(combination) == 2 and scoped_status == "NOT_RUN_INSUFFICIENT_ROLE_TOPOLOGY")
        if branch_supported and row_geometry and scoped_complete and region["promotion_eligible"]:
            complete.append(combination)
    reasons = []
    if not matched:
        reasons.append("REQUIRED_STRUCTURAL_ROLE_COMBINATION_NOT_OBSERVED")
    elif not complete:
        reasons.append("REQUIRED_ROLE_SHARED_LANE_OR_GEOMETRY_NOT_COMPLETE")
    if region["body_limit_reached"]:
        reasons.append("DECLARED_BODY_LIMIT_REACHED")
    if region["shared_scoped_table_v1"]["status"] == "SHARED_SCOPED_TABLE_FAIL_CLOSED":
        reasons.append("SHARED_SCOPED_TABLE_FAILED_CLOSED")
    return {
        "_complete": bool(complete),
        "_locators": _equivalence_keys(region["branch"], region["row_proposals"], structural_roles),
        "branch_role": branch_role,
        "complete_required_role_combinations": canonical_clone_v1(complete),
        "matched_required_role_combinations": canonical_clone_v1(matched),
        "observed_structural_roles": sorted(observed),
        "shared_semantic_region": canonical_clone_v1(region),
        "unresolved_reasons": sorted(set(reasons)),
    }


def _clusters(candidates: Sequence[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    groups: list[tuple[set[str], list[dict[str, Any]]]] = []
    for candidate in sorted(
        candidates,
        key=lambda item: (item["shared_semantic_region"]["region_id"], item["branch_role"]),
    ):
        locators = set(candidate["_locators"])
        overlaps = [index for index, (seen, _items) in enumerate(groups) if seen & locators]
        if not overlaps:
            groups.append((locators, [candidate]))
            continue
        first = overlaps[0]
        groups[first][0].update(locators)
        groups[first][1].append(candidate)
        for index in reversed(overlaps[1:]):
            other_locators, other_items = groups.pop(index)
            groups[first][0].update(other_locators)
            groups[first][1].extend(other_items)
    return [items for _locators, items in groups]


def _build(region_pages: Sequence[Mapping[str, Any]], project_root: Path) -> dict[str, Any]:
    policy = _policy(project_root)
    candidates = []
    near_regions = []
    branch_count = 0
    page_evidence_sha256 = None
    for semantic_pass in policy["semantic_passes"]:
        try:
            shared = build_accounting_semantic_region_graph_v1(
                region_pages, semantic_pass["semantic_spec"]
            )
        except AccountingSemanticRegionGraphV1Error as exc:
            raise _error(str(exc)) from exc
        observed_page_sha = shared["evidence_binding"]["canonical_page_evidence_sha256"]
        if page_evidence_sha256 not in (None, observed_page_sha):
            raise _error("Family-3 shared semantic page evidence binding drifted across passes")
        page_evidence_sha256 = observed_page_sha
        branch_count += shared["metrics"]["branch_candidate_count"]
        candidates.extend(_candidate(region, semantic_pass, policy) for region in shared["regions"])
        near_regions.extend(
            {
                "branch_role": semantic_pass["branch_role"],
                "evidence_equivalence_keys": _equivalence_keys(
                    near["branch"],
                    near["source_only_row_proposals"],
                    set(policy["structural_roles"]),
                ),
                "shared_near_region": canonical_clone_v1(near),
            }
            for near in shared["near_regions"]
        )
    grouped = _clusters(candidates)
    complete_group_count = sum(any(item["_complete"] for item in group) for group in grouped)
    unresolved_competitor_count = sum(
        not any(item["_complete"] for item in group)
        and any(len(item["observed_structural_roles"]) >= 2 for item in group)
        for group in grouped
    )
    complete_keys = [
        {key for item in group for key in item["_locators"]}
        for group in grouped
        if any(item["_complete"] for item in group)
    ]
    independent_near_count = sum(
        not any(set(near["evidence_equivalence_keys"]) & keys for keys in complete_keys)
        for near in near_regions
    )
    conflict = (
        complete_group_count > 1
        or (complete_group_count == 1 and unresolved_competitor_count > 0)
        or (complete_group_count == 1 and independent_near_count > 0)
    )
    regions = []
    for group in grouped:
        group_complete = any(item["_complete"] for item in group)
        public_candidates = []
        for raw in group:
            complete = raw.pop("_complete")
            locators = raw.pop("_locators")
            if complete and not conflict:
                status = "EXPLICIT_STRUCTURE_PROPOSAL_REQUIRES_BRANCHLESS_ORACLE"
            elif complete:
                status = "EXPLICIT_STRUCTURE_BLOCKED_BY_COMPETING_REGION_EVIDENCE"
            else:
                status = "SHARED_LANE_GEOMETRY_OR_TOPOLOGY_INCOMPLETE"
            candidate_material = {
                **raw,
                "disposition": "UNRESOLVED",
                "evidence_equivalence_keys": locators,
                "status": status,
            }
            public_candidates.append(
                {
                    **candidate_material,
                    "candidate_id": "f3srv1:candidate:"
                    + canonical_json_sha256_v1(candidate_material),
                }
            )
        region_material = {
            "candidates": sorted(public_candidates, key=lambda item: item["candidate_id"]),
            "disposition": "UNRESOLVED",
            "status": (
                "UNIQUE_EXPLICIT_EVIDENCE_CLUSTER_REQUIRES_BRANCHLESS_ORACLE"
                if group_complete and not conflict
                else "EVIDENCE_CLUSTER_RETAINED_FAIL_CLOSED"
            ),
        }
        regions.append(
            {
                **region_material,
                "region_id": "f3srv1:region:" + canonical_json_sha256_v1(region_material),
            }
        )
    regions.sort(key=lambda item: item["region_id"])
    if complete_group_count > 1:
        status = "UNRESOLVED_MULTIPLE_EXPLICIT_COMPLETE_REGIONS"
    elif complete_group_count == 1 and conflict:
        status = "UNRESOLVED_COMPETING_EXPLICIT_REGION_PROPOSALS"
    elif complete_group_count == 1:
        status = "UNIQUE_EXPLICIT_STRUCTURE_PROPOSAL_REQUIRES_BRANCHLESS_ORACLE"
    else:
        status = "UNRESOLVED_NO_COMPLETE_EXPLICIT_STRUCTURE"
    blockers = [
        "ADAPTER_HAS_NO_ABSENCE_AUTHORITY",
        "BRANCHLESS_ORACLE_NOT_RUN_BLOCKS_ABSENCE",
    ]
    if branch_count == 0:
        blockers.append("ZERO_BRANCH_CANNOT_PROVE_ABSENCE")
    if regions or near_regions:
        blockers.append("SEMANTIC_OR_NEAR_REGION_EVIDENCE_BLOCKS_ABSENCE")
    material = {
        "absence": {
            "blockers": sorted(blockers),
            "bounded_absences": [],
            "status": "UNRESOLVED_NO_ABSENCE_AUTHORITY",
        },
        "branchless_evaluation_status": (
            "NOT_RUN_REQUIRES_RESET_FENCED_OWNER_LOCAL_SHARED_PRIMITIVE"
        ),
        "claim_boundary": CLAIM_BOUNDARY,
        "evidence_binding": {
            "canonical_page_evidence_sha256": page_evidence_sha256,
            "config_binding": canonical_clone_v1(policy["config_binding"]),
            "policy_id": policy["policy_id"],
        },
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "metrics": {
            "branch_candidate_count": branch_count,
            "complete_evidence_cluster_count": complete_group_count,
            "independent_near_region_count": independent_near_count,
            "near_region_count": len(near_regions),
            "region_evidence_cluster_count": len(regions),
            "shared_semantic_candidate_count": len(candidates),
            "unresolved_competitor_cluster_count": unresolved_competitor_count,
        },
        "near_regions": sorted(
            near_regions,
            key=lambda item: (item["shared_near_region"]["near_region_id"], item["branch_role"]),
        ),
        "regions": regions,
        "requires_full_document_branchless_oracle": True,
        "safety": {
            "absence_authority": False,
            "branchless_oracle_run": False,
            "evaluation_lane_kinds_used_as_numeric_authority": False,
            "family_completion_authority": False,
            "family_schema_or_report_norm_id_known": False,
            "mapping_authority": False,
            "multiple_complete_regions_can_select_nearest_or_last": False,
            "numeric_authority": False,
            "owner_only_evidence_can_merge_regions": False,
            "period_or_unit_authority": False,
            "reset_or_hard_veto_can_be_crossed": False,
        },
        "status": status,
    }
    return {**material, "result_id": "f3srv1:result:" + canonical_json_sha256_v1(material)}


def build_interbank_deposits_loans_family3_semantic_region_v1(
    region_pages: Sequence[Mapping[str, Any]],
    project_root: str | Path = _PROJECT_ROOT,
) -> dict[str, Any]:
    return _build(region_pages, Path(project_root).resolve())


def validate_interbank_deposits_loans_family3_semantic_region_replay_v1(
    value: Any,
    region_pages: Sequence[Mapping[str, Any]],
    project_root: str | Path = _PROJECT_ROOT,
) -> dict[str, Any]:
    if type(value) is not dict or value.get("format_version") != FORMAT_VERSION:
        raise _error("Family-3 semantic-region result identity drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id", None)
    if identity != "f3srv1:result:" + canonical_json_sha256_v1(material):
        raise _error("Family-3 semantic-region result content identity drifted")
    rebuilt = _build(region_pages, Path(project_root).resolve())
    if not same_typed_json_v1(value, rebuilt):
        raise _error("Family-3 semantic-region result does not replay exactly")
    return rebuilt
