"""Caller-axis-only terminal structural proposals for accounting Family 3."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation import accounting_owner_local_branchless_oracle_v1 as owner_v1
from bctc_ai.evaluation import interbank_deposits_loans_family3_semantic_region_v1 as semantic_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FAMILY_ID = "INTERBANK_DEPOSITS_AND_LOANS"
FORMAT_VERSION = "INTERBANK_DEPOSITS_LOANS_FAMILY3_FULL_STRUCTURAL_ORACLE_V1"
CLAIM_BOUNDARY = (
    "CALLER_SUPPLIED_CONTIGUOUS_1_TO_N_COMPLETE_LOOKING_PHYSICAL_PAGE_AXIS_"
    "STRUCTURAL_PROPOSALS_ONLY_NO_AUTHENTICATED_FULL_DOCUMENT_COMPLETENESS_"
    "ABSENCE_ROW_NUMERIC_PERIOD_UNIT_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
TRUST_CLOSURE = {
    "accounting_topology_engine": {
        "path": "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
        "sha256": "65e88f2a28a214a71ba47ce2d237dbbc021d5be5d1cf34794aa9776908b2ed66",
        "size_bytes": 77_499,
    },
    "evaluation_config": {
        "path": "config/families/tm-interbank-deposits-loans-evaluation-v3.json",
        "sha256": "0db7cfe8efe522822abf0ab8b716182300d0314c75f26af3197357a966aa9772",
        "size_bytes": 2_280,
    },
    "owner_local_oracle": {
        "path": "src/bctc_ai/evaluation/accounting_owner_local_branchless_oracle_v1.py",
        "sha256": "30f61c8bd7b658ee58a9dd2b4f274426b72695b6bd419615782f7c666426d51d",
        "size_bytes": 18_638,
    },
    "semantic_adapter": {
        "path": "src/bctc_ai/evaluation/interbank_deposits_loans_family3_semantic_region_v1.py",
        "sha256": "4ed9b28ac14f84ae977d81e2824461239bcaec3b60453295ab3d065b50dff2c8",
        "size_bytes": 20_325,
    },
    "topology_config": {
        "path": "config/families/tm-interbank-deposits-loans-topology-v3.json",
        "sha256": "816573106c32e7fa133cc2d371d3b5ff89a10ce307ef148655e04fb00c4614e5",
        "size_bytes": 10_320,
    },
}
_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class InterbankDepositsLoansFamily3FullStructuralOracleV1Error(ValueError): ...


def _error(message: str) -> InterbankDepositsLoansFamily3FullStructuralOracleV1Error:
    return InterbankDepositsLoansFamily3FullStructuralOracleV1Error(message)


def _stable_ref(project_root: Path, expected: Mapping[str, Any]) -> tuple[dict[str, Any], bytes]:
    path = project_root / expected["path"]
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = -1
    try:
        descriptor = os.open(path, flags)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise _error("Family-3 terminal dependency is not one regular nofollow file")
        chunks = []
        while chunk := os.read(descriptor, 1 << 20):
            chunks.append(chunk)
        after = os.fstat(descriptor)
    except OSError as exc:
        raise _error("Family-3 terminal dependency cannot be read stable nofollow") from exc
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
        raise _error("Family-3 terminal dependency content reference drifted")
    return observed, payload


def _dependencies(project_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    refs, topology_payload = {}, None
    for name, expected in sorted(TRUST_CLOSURE.items()):
        observed, payload = _stable_ref(project_root, expected)
        refs[name] = observed
        if name == "topology_config":
            topology_payload = payload
    try:
        topology = json.loads(topology_payload)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("Family-3 pinned topology is not JSON") from exc
    if type(topology) is not dict:
        raise _error("Family-3 pinned topology root drifted")
    return refs, topology


def _page_axis(value: Any) -> list[int]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence) or not value:
        raise _error("Family-3 terminal requires one nonempty physical page sequence")
    sequences = [page.get("page_sequence") if type(page) is dict else None for page in value]
    if any(type(item) is not int for item in sequences) or sorted(sequences) != list(
        range(1, len(sequences) + 1)
    ):
        raise _error("Family-3 caller page axis must contain exactly page_sequence 1..N")
    return sorted(sequences)


def _topology_pages(value: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    projected = []
    for page in sorted(value, key=lambda item: item["page_sequence"]):
        lines = page.get("lines")
        if type(lines) is not list or any(
            type(line) is not dict or type(line.get("source_line_index")) is not int
            for line in lines
        ):
            raise _error("Family-3 topology source line axis drifted")
        projected.append(
            {
                "lines": sorted(
                    canonical_clone_v1(lines), key=lambda item: item["source_line_index"]
                ),
                "page_sequence": page["page_sequence"],
            }
        )
    return projected


def _oracle_spec(topology: Mapping[str, Any]) -> dict[str, Any]:
    try:
        child_aliases = semantic_v1._child_aliases(topology)
        heads = {item[0] for item in topology["required_role_combinations"]}
        explicit = semantic_v1._aliases(
            [
                alias
                for child in topology["children"]
                if child["role"] in heads
                for alias in child_aliases[child["role"]]
            ],
            "terminal explicit combo heads",
        )
        return {
            "explicit_branch_aliases": explicit,
            "family_id": topology["family_id"],
            "format_version": owner_v1.SPEC_FORMAT_VERSION,
            "hard_veto_aliases": semantic_v1._aliases(
                topology["hard_negative_aliases"], "terminal hard veto"
            ),
            "limits": {
                "continuation_page_budget": topology["limits"]["max_continuation_pages"],
                "max_label_line_span": topology["limits"]["max_label_line_span"],
                "max_owner_distance_lines": topology["limits"]["max_cluster_span_lines"],
            },
            "owner_aliases": semantic_v1._aliases(topology["parent"]["aliases"], "terminal owner"),
            "role_axis": [
                {"aliases": child_aliases[role], "role": role}
                for role in sorted(set(child_aliases) - heads)
            ],
            "structural_reset_aliases": semantic_v1._aliases(
                topology["structural_reset_aliases"], "terminal reset"
            ),
        }
    except (
        KeyError,
        TypeError,
        semantic_v1.InterbankDepositsLoansFamily3SemanticRegionV1Error,
    ) as exc:
        raise _error("Family-3 pinned topology cannot derive the owner-local oracle") from exc


def _selection(
    semantic: Mapping[str, Any],
    topology: Mapping[str, Any],
    topology_spec: Mapping[str, Any],
    topology_pages: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], dict[str, Any] | None, dict[str, Any]]:
    semantic_region = semantic["regions"][0] if len(semantic["regions"]) == 1 else None
    candidates = (
        [
            item
            for item in semantic_region["candidates"]
            if item["complete_required_role_combinations"]
        ]
        if semantic_region is not None
        else []
    )
    topology_region = topology["regions"][0] if len(topology["regions"]) == 1 else None
    semantic_locators = sorted(
        {locator for candidate in candidates for locator in candidate["evidence_equivalence_keys"]}
    )
    structural_roles = {
        role for combination in topology_spec["required_role_combinations"] for role in combination
    }
    source_indices = {
        page["page_sequence"]: [line["source_line_index"] for line in page["lines"]]
        for page in topology_pages
    }
    topology_locators = []
    if topology_region is not None:
        topology_locators = sorted(
            {
                f"p{match['page_sequence']}:l{index}"
                for match in topology_region["child_matches"]
                if match["role"] in structural_roles
                for index in source_indices[match["page_sequence"]]
                if match["source_line_index"] <= index <= match["end_source_line_index"]
            }
        )
    alignment = {
        "semantic_structural_locators": semantic_locators,
        "status": (
            "EXACT_NONEMPTY_STRUCTURAL_SOURCE_LOCATOR_ALIGNMENT"
            if semantic_locators and semantic_locators == topology_locators
            else "UNRESOLVED_STRUCTURAL_SOURCE_LOCATOR_MISMATCH"
        ),
        "topology_structural_locators": topology_locators,
    }
    return semantic_region, candidates, topology_region, alignment


def _build(pages: Any) -> dict[str, Any]:
    page_sequences = _page_axis(pages)
    dependency_refs, topology_spec = _dependencies(_PROJECT_ROOT)
    topology_pages = _topology_pages(pages)
    try:
        semantic = semantic_v1.build_interbank_deposits_loans_family3_semantic_region_v1(
            pages, _PROJECT_ROOT
        )
        topology = topology_v1.build_accounting_family_topology_scan_v1(
            topology_pages, topology_spec
        )
        oracle = owner_v1.build_accounting_owner_local_branchless_oracle_v1(
            pages, _oracle_spec(topology_spec)
        )
    except (
        semantic_v1.InterbankDepositsLoansFamily3SemanticRegionV1Error,
        topology_v1.AccountingFamilyTopologyV1Error,
        owner_v1.AccountingOwnerLocalBranchlessOracleV1Error,
    ) as exc:
        raise _error(str(exc)) from exc
    semantic_hash = semantic["evidence_binding"]["canonical_page_evidence_sha256"]
    oracle_hash = oracle["evidence_binding"]["canonical_page_evidence_sha256"]
    expected_config_refs = {
        "evaluation_spec_ref": dependency_refs["evaluation_config"],
        "topology_spec_ref": dependency_refs["topology_config"],
    }
    if (
        semantic_hash != oracle_hash
        or not same_typed_json_v1(
            semantic["evidence_binding"]["config_binding"], expected_config_refs
        )
        or {semantic["family_id"], topology["family_id"], oracle["family_id"]} != {FAMILY_ID}
    ):
        raise _error("Family-3 terminal replay evidence bindings disagree")
    semantic_metrics = semantic["metrics"]
    topology_metrics = topology["metrics"]
    oracle_zero = (
        oracle["status"] == "ZERO_BRANCHLESS_CHALLENGER_PROPOSAL_ONLY"
        and oracle["metrics"]["challenger_count"] == 0
        and oracle["challengers"] == []
    )
    semantic_zero = (
        semantic["status"] == "UNRESOLVED_NO_COMPLETE_EXPLICIT_STRUCTURE"
        and semantic_metrics["branch_candidate_count"] == 0
        and semantic_metrics["complete_evidence_cluster_count"] == 0
        and semantic_metrics["region_evidence_cluster_count"] == 0
        and semantic_metrics["near_region_count"] == 0
        and semantic_metrics["shared_semantic_candidate_count"] == 0
        and semantic["regions"] == []
        and semantic["near_regions"] == []
    )
    topology_zero = (
        topology["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
        and topology_metrics["complete_region_count"] == 0
        and topology_metrics["near_region_count"] == 0
        and topology_metrics["core_semantic_anchor_hit_count"] == 0
        and topology_metrics["semantic_anchor_hit_count"] == 0
        and topology["regions"] == []
        and topology["near_regions"] == []
    )
    semantic_region, candidates, topology_region, alignment = _selection(
        semantic, topology, topology_spec, topology_pages
    )
    semantic_ready = (
        semantic["status"] == "UNIQUE_EXPLICIT_STRUCTURE_PROPOSAL_REQUIRES_BRANCHLESS_ORACLE"
        and semantic_metrics["complete_evidence_cluster_count"] == 1
        and semantic_metrics["independent_near_region_count"] == 0
        and semantic_metrics["region_evidence_cluster_count"] == 1
        and semantic_region is not None
        and bool(candidates)
    )
    topology_ready = (
        topology["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
        and topology_metrics["complete_region_count"] == 1
        and topology_metrics["near_region_count"] == 0
        and topology["uniqueness"]["minimal_role_combination_proved"] is True
        and topology_region is not None
        and topology["near_regions"] == []
    )
    ready = (
        semantic_ready
        and topology_ready
        and oracle_zero
        and alignment["status"] == "EXACT_NONEMPTY_STRUCTURAL_SOURCE_LOCATOR_ALIGNMENT"
    )
    if ready:
        status, disposition = "STRUCTURAL_READY_PROPOSAL_ONLY", "PROPOSAL_ONLY"
    elif semantic_zero and topology_zero and oracle_zero:
        status, disposition = "NOT_OBSERVED_PROPOSAL_ONLY", "PROPOSAL_ONLY"
    else:
        status, disposition = "UNRESOLVED_STRUCTURAL_EVIDENCE", "UNRESOLVED"
    material = {
        "absence": {"authority": False, "bounded_absences": []},
        "claim_boundary": CLAIM_BOUNDARY,
        "disposition": disposition,
        "evidence_binding": {
            "canonical_page_evidence_sha256": semantic_hash,
            "dependency_content_refs": dependency_refs,
            "owner_local_oracle_result_id": oracle["result_id"],
            "owner_local_oracle_semantic_engine_content_ref": oracle["evidence_binding"][
                "semantic_engine_content_ref"
            ],
            "owner_local_oracle_spec_id": oracle["evidence_binding"]["spec_id"],
            "semantic_adapter_result_id": semantic["result_id"],
            "topology_scan_id": topology["scan_id"],
        },
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "input_axis": {
            "page_sequences": page_sequences,
            "status": "CALLER_SUPPLIED_CONTIGUOUS_1_TO_N_COMPLETE_LOOKING_ONLY",
        },
        "structural_metrics": {
            "explicit_complete_cluster_count": semantic_metrics["complete_evidence_cluster_count"],
            "independent_near_region_count": semantic_metrics["independent_near_region_count"],
            "oracle_branchless_challenger_count": oracle["metrics"]["challenger_count"],
            "semantic_region_cluster_count": semantic_metrics["region_evidence_cluster_count"],
            "topology_complete_region_count": topology_metrics["complete_region_count"],
            "topology_core_semantic_anchor_hit_count": topology_metrics[
                "core_semantic_anchor_hit_count"
            ],
            "topology_near_region_count": topology_metrics["near_region_count"],
            "topology_semantic_anchor_hit_count": topology_metrics["semantic_anchor_hit_count"],
        },
        "owner_local_oracle_proposal": canonical_clone_v1(oracle),
        "safety": {
            "absence_authority": False,
            "authenticated_input_authority": False,
            "document_completeness_authority": False,
            "mapping_authority": False,
            "numeric_authority": False,
            "period_or_unit_authority": False,
            "row_or_column_authority": False,
            "schema_authority": False,
        },
        "selected_structural_candidate_ids": (
            [item["candidate_id"] for item in candidates] if ready else []
        ),
        "selected_structural_candidates": canonical_clone_v1(candidates) if ready else [],
        "selected_structural_region": canonical_clone_v1(semantic_region) if ready else None,
        "selected_structural_region_id": semantic_region["region_id"] if ready else None,
        "selected_topology_region": canonical_clone_v1(topology_region) if ready else None,
        "selected_topology_region_sha256": (
            canonical_json_sha256_v1(topology_region) if ready else None
        ),
        "semantic_proposal": canonical_clone_v1(semantic),
        "source_locator_alignment": alignment,
        "status": status,
        "topology_proposal": canonical_clone_v1(topology),
    }
    return {**material, "result_id": "f3fsov1:result:" + canonical_json_sha256_v1(material)}


def build_interbank_deposits_loans_family3_full_structural_oracle_v1(
    pages: Any,
) -> dict[str, Any]:
    return _build(pages)


def validate_interbank_deposits_loans_family3_full_structural_oracle_replay_v1(
    value: Any, pages: Any
) -> dict[str, Any]:
    if type(value) is not dict or value.get("format_version") != FORMAT_VERSION:
        raise _error("Family-3 terminal result identity drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id", None)
    if identity != "f3fsov1:result:" + canonical_json_sha256_v1(material):
        raise _error("Family-3 terminal result content identity drifted")
    rebuilt = _build(pages)
    if not same_typed_json_v1(value, rebuilt):
        raise _error("Family-3 terminal result does not replay exactly")
    return rebuilt
