"""Project an explicitly declared family total onto its exact owner row.

The sealed topology V1 engine intentionally admits ordinary child roles only
strictly after an explicit parent.  Some primary statements instead print the
family balance on that same owner row.  This add-only projection handles that
layout without changing topology discovery: a caller must opt in by declaring
one ``TOTAL`` child whose exact normalized aliases cover the complete parent
alias vocabulary, and the selected parent itself must be an exact match.

The projection neither discovers a region nor broadens its boundary.  It only
adds one role record cloned from the already selected, byte-identical parent
source locator.  Fuzzy parent matches, partial alias overlap, contextual total
roles, and multiple eligible total roles fail closed.
"""

from __future__ import annotations

from typing import Any

from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.source_structure.contracts_v1 import canonical_clone_v1, same_typed_json_v1

__all__ = [
    "AccountingFamilyCoextensiveParentTotalV1Error",
    "project_accounting_family_coextensive_parent_total_region_v1",
]


class AccountingFamilyCoextensiveParentTotalV1Error(ValueError):
    """The topology scan, selected region, or declarative opt-in drifted."""


def _error(message: str) -> AccountingFamilyCoextensiveParentTotalV1Error:
    return AccountingFamilyCoextensiveParentTotalV1Error(message)


def _eligible_total_role(spec: dict[str, Any]) -> dict[str, Any] | None:
    """Return the unique exact parent-covering, context-free ``TOTAL`` role."""

    parent_aliases = set(spec["parent"]["aliases"])
    eligible = []
    for child in spec["children"]:
        if child["role_kind"] != "TOTAL":
            continue
        aliases = {
            alias
            for matcher in child["matchers"]
            if matcher["within_role"] is None
            for alias in matcher["aliases"]
        }
        if parent_aliases <= aliases:
            eligible.append(child)
    if len(eligible) > 1:
        raise _error("multiple TOTAL roles cover the complete parent alias vocabulary")
    return eligible[0] if eligible else None


def project_accounting_family_coextensive_parent_total_region_v1(
    family_topology_spec: Any,
    topology_scan: Any,
    topology_region: Any,
) -> dict[str, Any]:
    """Add one exact coextensive parent-row total to a selected V1 region.

    ``topology_region`` must be one exact complete region from the supplied
    authenticated V1 scan.  Returning a region rather than a modified scan
    keeps V1 scan identity and replay byte-exact; an add-only downstream row
    axis may consume this effective region while retaining the original scan
    as its discovery authority.
    """

    try:
        scan = topology_v1._validate_result(topology_scan)
        spec = topology_v1._spec(family_topology_spec)
    except topology_v1.AccountingFamilyTopologyV1Error as exc:
        raise _error("coextensive total topology input drifted") from exc
    if scan["family_id"] != spec["family_id"] or type(topology_region) is not dict:
        raise _error("coextensive total topology family/region drifted")
    selected = [region for region in scan["regions"] if same_typed_json_v1(region, topology_region)]
    if len(selected) != 1:
        raise _error("coextensive total region is not one exact complete scan candidate")

    region = canonical_clone_v1(selected[0])
    total = _eligible_total_role(spec)
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
