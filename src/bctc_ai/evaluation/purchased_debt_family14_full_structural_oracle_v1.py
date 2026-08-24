"""Caller-axis-only structural proposals for purchased-debt Family 14."""

from __future__ import annotations

import hashlib
import stat
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.accounting_owner_local_branchless_oracle_v1 import (
    build_accounting_owner_local_branchless_oracle_v1,
)
from bctc_ai.evaluation.purchased_debt_family14_region_query_v1 import (
    build_purchased_debt_family14_topology_scan_v1,
    build_purchased_debt_family14_topology_spec_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "CLAIM_BOUNDARY",
    "DEPENDENCY_REFS_V1",
    "FORMAT_VERSION",
    "PurchasedDebtFamily14FullStructuralOracleV1Error",
    "build_purchased_debt_family14_full_structural_oracle_v1",
    "validate_purchased_debt_family14_full_structural_oracle_replay_v1",
]

FORMAT_VERSION = "PURCHASED_DEBT_FAMILY14_FULL_STRUCTURAL_ORACLE_V1"
CLAIM_BOUNDARY = (
    "CALLER_SUPPLIED_CONTIGUOUS_PAGE_AXIS_ONLY_PURCHASED_DEBT_TOPOLOGY_AND_"
    "OWNER_LOCAL_BRANCHLESS_STRUCTURAL_PROPOSALS_NO_AUTHENTICATION_COMPLETENESS_"
    "ABSENCE_PERIOD_UNIT_NUMERIC_EQUATION_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
DEPENDENCY_REFS_V1 = {
    "family14_topology_adapter_ref": {
        "path": "src/bctc_ai/evaluation/purchased_debt_family14_region_query_v1.py",
        "sha256": "e76a9bb2ff5e5d99cf4674f40167bc736c82a646f6b26b948cbabda9871f1ee0",
        "size_bytes": 15_380,
    },
    "owner_local_oracle_ref": {
        "path": "src/bctc_ai/evaluation/accounting_owner_local_branchless_oracle_v1.py",
        "sha256": "30f61c8bd7b658ee58a9dd2b4f274426b72695b6bd419615782f7c666426d51d",
        "size_bytes": 18_638,
    },
    "shared_topology_engine_ref": {
        "path": "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
        "sha256": "60da089b5df5a6ee9f53dac8569bc4a9484bf5816721fb992f8d4d09a43bc236",
        "size_bytes": 68_515,
    },
}
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_AUTHORITY = {
    "absence_authority": False,
    "authentication_authority": False,
    "caller_page_axis_completeness_authority": False,
    "equation_authority": False,
    "mapping_authority": False,
    "not_observed_is_absence": False,
    "numeric_authority": False,
    "schema_authority": False,
    "structural_proposal_authority": True,
}
_OBSERVATION_SCOPE = "CALLER_SUPPLIED_CONTIGUOUS_PAGE_AXIS_ONLY_NO_COMPLETENESS_PROOF"


class PurchasedDebtFamily14FullStructuralOracleV1Error(ValueError):
    """The Family-14 structural proposal or its dependency closure drifted."""


def _error(message: str) -> PurchasedDebtFamily14FullStructuralOracleV1Error:
    return PurchasedDebtFamily14FullStructuralOracleV1Error(message)


def _content_ref(relative: Path, label: str) -> dict[str, Any]:
    path = _PROJECT_ROOT / relative
    try:
        before = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(before.st_mode):
            raise _error(f"Family-14 structural {label} is not one regular nofollow file")
        payload = path.read_bytes()
        after = path.lstat()
    except OSError as exc:
        raise _error(f"Family-14 structural {label} cannot be read stably") from exc
    identity = lambda item: (  # noqa: E731
        item.st_dev,
        item.st_ino,
        item.st_mode,
        item.st_size,
        item.st_mtime_ns,
    )
    if identity(before) != identity(after) or len(payload) != before.st_size:
        raise _error(f"Family-14 structural {label} changed during stable read")
    return {
        "path": relative.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _dependency_refs() -> dict[str, Any]:
    observed = {
        name: _content_ref(Path(reference["path"]), name.replace("_", " "))
        for name, reference in sorted(DEPENDENCY_REFS_V1.items())
    }
    if not same_typed_json_v1(observed, DEPENDENCY_REFS_V1):
        raise _error("Family-14 structural dependency content reference drifted")
    return observed


def _page_projections(source_pages: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if (
        isinstance(source_pages, (str, bytes, bytearray))
        or not isinstance(source_pages, Sequence)
        or not source_pages
    ):
        raise _error("Family-14 structural oracle requires one nonempty page sequence")
    pages = []
    for raw_page in source_pages:
        if type(raw_page) is not dict or type(raw_page.get("page_sequence")) is not int:
            raise _error("Family-14 structural page axis drifted")
        lines = raw_page.get("lines")
        if type(lines) is not list or any(
            type(line) is not dict or type(line.get("source_line_index")) is not int
            for line in lines
        ):
            raise _error("Family-14 structural line axis drifted")
        pages.append(canonical_clone_v1(raw_page))
    pages.sort(key=lambda item: item["page_sequence"])
    if [page["page_sequence"] for page in pages] != list(range(1, len(pages) + 1)):
        raise _error("Family-14 structural page sequence must be exactly 1..N without gaps")
    topology_pages = [
        {
            "lines": sorted(page["lines"], key=lambda line: line["source_line_index"]),
            "page_sequence": page["page_sequence"],
        }
        for page in pages
    ]
    return topology_pages, pages


def _role_aliases(topology: Mapping[str, Any], role: str) -> list[str]:
    children = [item for item in topology["children"] if item["role"] == role]
    if len(children) != 1:
        raise _error(f"Family-14 structural topology role {role} drifted")
    return [alias for matcher in children[0]["matchers"] for alias in matcher["aliases"]]


def _owner_local_spec(topology: Mapping[str, Any]) -> dict[str, Any]:
    provision = [
        alias
        for alias in _role_aliases(topology, "PROVISION_BALANCE_ROW")
        if alias not in {"Dự phòng chung", "Dự phòng rủi ro"}
    ]
    return {
        "explicit_branch_aliases": _role_aliases(topology, "PURCHASE_VND_BALANCE_ROW"),
        "family_id": topology["family_id"],
        "format_version": "ACCOUNTING_OWNER_LOCAL_BRANCHLESS_SPEC_V1",
        "hard_veto_aliases": canonical_clone_v1(topology["hard_negative_aliases"]),
        "limits": {
            "continuation_page_budget": 1,
            "max_label_line_span": 3,
            "max_owner_distance_lines": 96,
        },
        "owner_aliases": canonical_clone_v1(topology["parent"]["aliases"]),
        "role_axis": [
            {"aliases": provision, "role": "PROVISION_BALANCE_ROW"},
            {
                "aliases": _role_aliases(topology, "PRINCIPAL_DETAIL_ROW"),
                "role": "PRINCIPAL_DETAIL_ROW",
            },
            {
                "aliases": _role_aliases(topology, "PURCHASE_FX_BALANCE_ROW"),
                "role": "PURCHASE_FX_BALANCE_ROW",
            },
            {
                "aliases": _role_aliases(topology, "INTEREST_DETAIL_ROW"),
                "role": "INTEREST_DETAIL_ROW",
            },
        ],
        "structural_reset_aliases": canonical_clone_v1(topology["structural_reset_aliases"]),
    }


def _build(source_pages: Any) -> dict[str, Any]:
    dependencies = _dependency_refs()
    topology_pages, oracle_pages = _page_projections(source_pages)
    topology_spec = build_purchased_debt_family14_topology_spec_v1()
    try:
        topology = build_purchased_debt_family14_topology_scan_v1(topology_pages)
        branchless = build_accounting_owner_local_branchless_oracle_v1(
            oracle_pages, _owner_local_spec(topology_spec)
        )
    except ValueError as exc:
        raise _error(f"Family-14 structural dependency rejected source: {exc}") from exc
    complete = topology["metrics"]["complete_region_count"]
    near = topology["metrics"]["near_region_count"]
    core_hits = topology["metrics"]["core_semantic_anchor_hit_count"]
    challengers = branchless["metrics"]["challenger_count"]
    topology_zero = (
        topology["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
        and all(type(count) is int and count == 0 for count in (complete, near, core_hits))
    )
    if complete == 1 and near == 0 and challengers == 0:
        status = "STRUCTURAL_READY_PROPOSAL_ONLY"
    elif challengers:
        status = "UNRESOLVED_BRANCHLESS_CHALLENGER_PROPOSAL_ONLY"
    elif topology_zero and type(challengers) is int and challengers == 0:
        status = "NOT_OBSERVED_PROPOSAL_ONLY"
    else:
        status = "UNRESOLVED_STRUCTURAL_AMBIGUITY_PROPOSAL_ONLY"
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "branchless_oracle_proposal": branchless,
        "claim_boundary": CLAIM_BOUNDARY,
        "dependency_refs": dependencies,
        "family_id": topology_spec["family_id"],
        "format_version": FORMAT_VERSION,
        "mappings": [],
        "metrics": {
            "branchless_challenger_count": challengers,
            "complete_topology_region_count": complete,
            "mapping_count": 0,
            "near_topology_region_count": near,
        },
        "observation_scope": _OBSERVATION_SCOPE,
        "status": status,
        "topology_proposal": topology,
    }
    return {
        **material,
        "result_id": "pdf14fsov1:result:" + canonical_json_sha256_v1(material),
    }


def build_purchased_debt_family14_full_structural_oracle_v1(
    source_pages: Any,
) -> dict[str, Any]:
    """Build one non-authoritative proposal over a caller-supplied page axis."""

    return _build(source_pages)


def validate_purchased_debt_family14_full_structural_oracle_replay_v1(
    value: Any, source_pages: Any
) -> dict[str, Any]:
    """Verify result identity, then rebuild both shared proposals exactly once."""

    if type(value) is not dict or value.get("format_version") != FORMAT_VERSION:
        raise _error("Family-14 structural result identity drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id", None)
    if identity != "pdf14fsov1:result:" + canonical_json_sha256_v1(material):
        raise _error("Family-14 structural result content identity drifted")
    rebuilt = _build(source_pages)
    if not same_typed_json_v1(value, rebuilt):
        raise _error("Family-14 structural result does not replay exactly")
    return rebuilt
