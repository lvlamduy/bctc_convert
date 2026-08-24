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

from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.source_structure.contracts_v1 import canonical_clone_v1, same_typed_json_v1

__all__ = [
    "AccountingFamilyCoextensiveParentTotalV1Error",
    "project_accounting_family_coextensive_parent_total_region_v1",
    "project_accounting_family_coextensive_structural_numeric_rows_v1",
]


COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_STATUS = "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_ALREADY_OWNED"
COEXTENSIVE_PRECEDING_NUMERIC_AMBIGUITY_STATUS = (
    "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_AMBIGUOUS_OWNERSHIP_VETO"
)


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


def _complete_values(row: Mapping[str, Any]) -> list[Mapping[str, Any]] | None:
    values = row.get("values")
    if (
        row.get("status") != "VISIBLE_VALUE_LANES_BOUND"
        or type(values) is not list
        or not values
        or [value.get("column_ordinal") for value in values] != list(range(len(values)))
    ):
        return None
    return values


def _number(value: Mapping[str, Any]) -> tuple[int, int, bool] | None:
    parsed = value.get("parsed_token")
    if (
        type(parsed) is not dict
        or type(parsed.get("coefficient")) is not int
        or type(parsed.get("scale")) is not int
        or parsed["scale"] < 0
        or type(parsed.get("percentage_mark_present")) is not bool
    ):
        return None
    return (
        parsed["coefficient"],
        parsed["scale"],
        parsed["percentage_mark_present"],
    )


def _exact_component_sum(
    visible_values: Sequence[Mapping[str, Any]],
    component_rows: Sequence[Mapping[str, Any]],
) -> bool:
    component_axes = [_complete_values(row) for row in component_rows]
    if any(axis is None for axis in component_axes):
        return False
    axes = [axis for axis in component_axes if axis is not None]
    if not axes or any(len(axis) != len(visible_values) for axis in axes):
        return False
    for lane, visible in enumerate(visible_values):
        visible_number = _number(visible)
        component_numbers = [_number(axis[lane]) for axis in axes]
        if visible_number is None or any(number is None for number in component_numbers):
            return False
        numbers = [number for number in component_numbers if number is not None]
        percentages = {number[2] for number in numbers}
        if len(percentages) != 1 or visible_number[2] not in percentages:
            return False
        scale = max(visible_number[1], *(number[1] for number in numbers))
        visible_coefficient = visible_number[0] * 10 ** (scale - visible_number[1])
        component_coefficient = sum(number[0] * 10 ** (scale - number[1]) for number in numbers)
        if visible_coefficient != component_coefficient:
            return False
    return True


def _values_follow_label(row: Mapping[str, Any]) -> bool:
    values = _complete_values(row)
    label_end = row.get("label_match", {}).get("end_source_line_index")
    return (
        values is not None
        and type(label_end) is int
        and all(
            type(value.get("line_ordinal")) is int and value["line_ordinal"] > label_end
            for value in values
        )
    )


def project_accounting_family_coextensive_structural_numeric_rows_v1(
    row_axis: Any,
    role_matches: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Remove a preceding scope subtotal stolen by the next group label.

    Provider order can place one complete, unlabeled subtotal immediately
    before the next structural heading. Weak vertical contact can then bind
    that numeric row to the *next* heading even though it is the exact sum of
    the preceding sibling scope. This add-only projector removes that false
    numeric projection while retaining both structural occurrences.

    The gate is deliberately conjunctive and exact. The candidate numeric
    lanes must precede the next heading, have negative row affinity, equal the
    complete sum of at least two direct additive children of the nearest prior
    sibling scope, and disagree with the local provider orientation of the
    next scope (whose complete children follow their own labels). If the row
    also equals the complete next-scope sum, its ownership is ambiguous: the
    source row is retained and a typed veto is emitted. A genuine values-
    before-label table, a separately printed subtotal, an incomplete scope, or
    any one-unit source conflict is retained for ordinary accounting
    adjudication rather than suppressed.
    """

    if type(row_axis) is not dict or type(role_matches) is not list:
        raise _error("coextensive structural numeric projection input drifted")
    projected = canonical_clone_v1(row_axis)
    matches = canonical_clone_v1(role_matches)
    if any(type(match) is not dict for match in matches):
        raise _error("coextensive structural role match axis drifted")
    rows = projected.get("rows")
    if type(rows) is not list:
        raise _error("coextensive structural row axis drifted")
    rows_by_occurrence = {
        row.get("label_match", {}).get("occurrence_id"): row
        for row in rows
        if type(row) is dict and type(row.get("label_match", {}).get("occurrence_id")) is str
    }
    receipts: list[dict[str, Any]] = []
    removed_occurrences: set[str] = set()
    for row in rows:
        label = row.get("label_match", {}) if type(row) is dict else {}
        occurrence_id = label.get("occurrence_id")
        values = _complete_values(row) if type(row) is dict else None
        label_start = label.get("source_line_index")
        if (
            row.get("role_kind") != "STRUCTURAL_GROUP"
            or type(occurrence_id) is not str
            or values is None
            or type(label_start) is not int
            or not all(
                type(value.get("line_ordinal")) is int
                and value["line_ordinal"] < label_start
                and type(value.get("row_affinity")) is float
                and value["row_affinity"] < 0
                for value in values
            )
            or max(value["line_ordinal"] for value in values) + 1 != label_start
        ):
            continue

        current_children = [
            match
            for match in matches
            if match.get("scope_owner_occurrence_id") == occurrence_id
            and match.get("role_kind") == "ADDITIVE_CHILD"
            and match.get("page_sequence") == label.get("page_sequence")
            and type(match.get("document_line_ordinal")) is int
            and match["document_line_ordinal"] > label.get("end_document_line_ordinal", -1)
        ]
        current_child_rows = [
            rows_by_occurrence.get(match.get("occurrence_id")) for match in current_children
        ]
        if (
            not current_children
            or any(child is None for child in current_child_rows)
            or not all(
                _values_follow_label(child) for child in current_child_rows if child is not None
            )
        ):
            continue
        current_scope_exact = _exact_component_sum(
            values,
            [child for child in current_child_rows if child is not None],
        )

        prior_siblings = [
            match
            for match in matches
            if match.get("role_kind") == "STRUCTURAL_GROUP"
            and match.get("scope_owner_occurrence_id") == label.get("scope_owner_occurrence_id")
            and match.get("page_sequence") == label.get("page_sequence")
            and type(match.get("end_document_line_ordinal")) is int
            and match["end_document_line_ordinal"] < label.get("document_line_ordinal", -1)
        ]
        if not prior_siblings:
            continue
        owner = max(
            prior_siblings,
            key=lambda match: (
                match["end_document_line_ordinal"],
                match.get("document_line_ordinal", -1),
            ),
        )
        owner_id = owner.get("occurrence_id")
        owner_children = [
            match
            for match in matches
            if match.get("scope_owner_occurrence_id") == owner_id
            and match.get("role_kind") == "ADDITIVE_CHILD"
            and match.get("page_sequence") == label.get("page_sequence")
        ]
        owner_child_rows = [
            rows_by_occurrence.get(match.get("occurrence_id")) for match in owner_children
        ]
        if (
            type(owner_id) is not str
            or len(owner_children) < 2
            or any(child is None for child in owner_child_rows)
            or not all(
                _values_follow_label(child)
                and max(value["line_ordinal"] for value in _complete_values(child) or [])
                < min(value["line_ordinal"] for value in values)
                for child in owner_child_rows
                if child is not None
            )
            or not _exact_component_sum(
                values,
                [child for child in owner_child_rows if child is not None],
            )
        ):
            continue
        source_sample_ids = [value.get("sample_id") for value in values]
        if any(type(sample_id) is not str or not sample_id for sample_id in source_sample_ids):
            continue
        status = (
            COEXTENSIVE_PRECEDING_NUMERIC_AMBIGUITY_STATUS
            if current_scope_exact
            else COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_STATUS
        )
        if not current_scope_exact:
            removed_occurrences.add(occurrence_id)
        receipts.append(
            {
                "owner_component_occurrence_ids": [
                    match["occurrence_id"] for match in owner_children
                ],
                "owner_occurrence_id": owner_id,
                "owner_role": owner["role"],
                "projected_occurrence_id": occurrence_id,
                "projected_role": row["role"],
                "source_record": canonical_clone_v1(row),
                "source_sample_ids": source_sample_ids,
                "status": status,
            }
        )
    projected["rows"] = [
        row
        for row in rows
        if row.get("label_match", {}).get("occurrence_id") not in removed_occurrences
    ]
    return projected, receipts
