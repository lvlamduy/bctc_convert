"""Generic recursive accounting closure for hierarchical note tables.

The primitive resolves a declarative role hierarchy from complete, visible
PP-OCRv6 numeric rows.  A role may be printed directly, derived from an exact
sum of child roles, or printed and independently corroborated by those child
roles.  Optional source rows remain optional; a visible mismatch is always a
veto and no equation may repair or invent a source digit.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation import accounting_family_row_axis_v1 as row_axis_v1
from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "SPEC_FORMAT_VERSION",
    "AccountingHierarchicalTableClosureV1Error",
    "build_accounting_hierarchical_table_closure_v1",
    "validate_accounting_hierarchical_table_closure_replay_v1",
]


FORMAT_VERSION = "ACCOUNTING_HIERARCHICAL_TABLE_CLOSURE_V1"
SPEC_FORMAT_VERSION = "ACCOUNTING_HIERARCHICAL_CLOSURE_SPEC_V1"
CLAIM_BOUNDARY = (
    "VISIBLE_SOURCE_ROLE_OR_EXACT_RECURSIVE_COMPONENT_SUM_WITH_OPTIONAL_VISIBLE_"
    "RESULT_AND_TRAILING_TOTAL_CORROBORATION_NO_DIGIT_REPAIR_MISSING_CELL_PERIOD_"
    "UNIT_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "accounting_equation_can_change_or_supply_source_digits": False,
    "accounting_relation_corroboration_or_derived_parent_only": True,
    "blank_token_means_zero": False,
    "dash_only_token_means_zero": True,
    "mapping_authority": False,
    "missing_cells_synthesized": False,
    "numeric_authority": False,
    "period_or_unit_authority": False,
    "schema_authority": False,
    "visible_mismatch_is_veto": True,
}
_SPEC_FIELDS = {"equations", "family_id", "format_version"}
_EQUATION_FIELDS = {
    "component_roles",
    "minimum_component_count",
    "result_role",
    "trailing_result_policy",
    "visible_result_roles",
}
_TRAILING_POLICIES = {"IGNORE", "CORROBORATE_IF_PRESENT"}
_RESULT_FIELDS = {
    "claim_boundary",
    "closure_id",
    "equations",
    "family_id",
    "format_version",
    "metrics",
    "resolved_roles",
    "row_axis_id",
    "safety",
    "status",
    "unresolved_reasons",
}


class AccountingHierarchicalTableClosureV1Error(ValueError):
    """The row axis, hierarchy specification, equation, or replay drifted."""


def _error(message: str) -> AccountingHierarchicalTableClosureV1Error:
    return AccountingHierarchicalTableClosureV1Error(message)


def _spec(value: Any, family_topology_spec: Any) -> dict[str, Any]:
    try:
        topology = topology_v1._spec(family_topology_spec)
    except (ValueError, RuntimeError) as exc:
        raise _error("hierarchical closure topology specification drifted") from exc
    if (
        type(value) is not dict
        or set(value) != _SPEC_FIELDS
        or value["format_version"] != SPEC_FORMAT_VERSION
        or value["family_id"] != topology["family_id"]
        or type(value["equations"]) is not list
        or not value["equations"]
    ):
        raise _error("hierarchical closure specification fields drifted")
    child_roles = {child["role"] for child in topology["children"]}
    known_roles = {topology["parent"]["role"], *child_roles}
    result_roles: set[str] = set()
    visible_roles: set[str] = set()
    equations = []
    for raw in value["equations"]:
        if (
            type(raw) is not dict
            or set(raw) != _EQUATION_FIELDS
            or type(raw["result_role"]) is not str
            or not raw["result_role"]
            or raw["result_role"] not in known_roles
            or raw["result_role"] in result_roles
            or type(raw["component_roles"]) is not list
            or not raw["component_roles"]
            or any(
                type(role) is not str or role not in known_roles for role in raw["component_roles"]
            )
            or len(raw["component_roles"]) != len(set(raw["component_roles"]))
            or raw["result_role"] in raw["component_roles"]
            or type(raw["minimum_component_count"]) is not int
            or not 1 <= raw["minimum_component_count"] <= len(raw["component_roles"])
            or type(raw["visible_result_roles"]) is not list
            or not raw["visible_result_roles"]
            or any(role not in child_roles for role in raw["visible_result_roles"])
            or len(raw["visible_result_roles"]) != len(set(raw["visible_result_roles"]))
            or any(role in visible_roles for role in raw["visible_result_roles"])
            or raw["trailing_result_policy"] not in _TRAILING_POLICIES
        ):
            raise _error("hierarchical closure equation contract drifted")
        # Recursive results must be defined before a later equation consumes
        # them. Every other component must be one declared source role.
        if any(
            role not in child_roles and role not in result_roles for role in raw["component_roles"]
        ):
            raise _error("hierarchical closure equations are not in dependency order")
        result_roles.add(raw["result_role"])
        visible_roles.update(raw["visible_result_roles"])
        equations.append(canonical_clone_v1(raw))
    return {
        "equations": equations,
        "family_id": topology["family_id"],
        "format_version": SPEC_FORMAT_VERSION,
    }


def _number(value: Mapping[str, Any]) -> dict[str, Any]:
    parsed = value.get("parsed_token")
    if (
        type(parsed) is not dict
        or parsed.get("classification") not in {"DASH_ZERO", "SIGNED_NUMBER"}
        or type(parsed.get("coefficient")) is not int
        or type(parsed.get("scale")) is not int
        or parsed["scale"] < 0
        or type(parsed.get("percentage_mark_present")) is not bool
        or type(value.get("sample_id")) is not str
        or not value["sample_id"]
    ):
        raise _error("hierarchical closure source cell is not one exact numeric token")
    return {
        "coefficient": parsed["coefficient"],
        "percentage_mark_present": parsed["percentage_mark_present"],
        "scale": parsed["scale"],
    }


def _canonical_number(coefficient: int, scale: int, percentage: bool) -> dict[str, Any]:
    while scale > 0 and coefficient % 10 == 0:
        coefficient //= 10
        scale -= 1
    return {
        "coefficient": coefficient,
        "percentage_mark_present": percentage,
        "scale": scale,
    }


def _equal(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    if left["percentage_mark_present"] is not right["percentage_mark_present"]:
        return False
    scale = max(left["scale"], right["scale"])
    return left["coefficient"] * (10 ** (scale - left["scale"])) == right["coefficient"] * (
        10 ** (scale - right["scale"])
    )


def _row_resolution(row: Mapping[str, Any]) -> dict[str, Any]:
    values = row.get("values")
    if (
        row.get("status") != "VISIBLE_VALUE_LANES_BOUND"
        or type(values) is not list
        or not values
        or [value.get("column_ordinal") for value in values] != list(range(len(values)))
    ):
        raise _error("hierarchical closure role row does not cover one complete lane axis")
    return {
        "component_roles": [],
        "resolution_kind": "VISIBLE_SOURCE_ROLE",
        "role": row["role"],
        "source": {"kind": "ROLE_ROW", "record": canonical_clone_v1(row)},
        "values": [
            {
                "column_ordinal": value["column_ordinal"],
                "number": _number(value),
                "source_sample_ids": [value["sample_id"]],
            }
            for value in values
        ],
    }


def _sum_components(
    roles: Sequence[str], resolved: Mapping[str, Mapping[str, Any]]
) -> list[dict[str, Any]]:
    records = [resolved[role] for role in roles]
    axes = [[value["column_ordinal"] for value in record["values"]] for record in records]
    if not axes or any(axis != axes[0] for axis in axes):
        raise _error("hierarchical closure component lane axes differ")
    result = []
    for lane in axes[0]:
        values = [
            next(value for value in record["values"] if value["column_ordinal"] == lane)
            for record in records
        ]
        percentages = {value["number"]["percentage_mark_present"] for value in values}
        if len(percentages) != 1:
            raise _error("hierarchical closure mixes money and percentage components")
        scale = max(value["number"]["scale"] for value in values)
        coefficient = sum(
            value["number"]["coefficient"] * (10 ** (scale - value["number"]["scale"]))
            for value in values
        )
        result.append(
            {
                "column_ordinal": lane,
                "number": _canonical_number(coefficient, scale, next(iter(percentages))),
                "source_sample_ids": list(
                    dict.fromkeys(
                        sample_id for value in values for sample_id in value["source_sample_ids"]
                    )
                ),
            }
        )
    return result


def _same_values(left: Sequence[Mapping[str, Any]], right: Sequence[Mapping[str, Any]]) -> bool:
    return [item["column_ordinal"] for item in left] == [
        item["column_ordinal"] for item in right
    ] and all(_equal(a["number"], b["number"]) for a, b in zip(left, right, strict=True))


def _trailing_resolution(candidate: Mapping[str, Any]) -> dict[str, Any]:
    values = candidate.get("values")
    if (
        candidate.get("status") != "COMPLETE_VISIBLE_TRAILING_VALUE_ROW"
        or type(values) is not list
        or not values
        or [value.get("column_ordinal") for value in values] != list(range(len(values)))
    ):
        raise _error("hierarchical closure trailing candidate axis drifted")
    return {
        "component_roles": [],
        "resolution_kind": "VISIBLE_TRAILING_TOTAL",
        "role": "",
        "source": {"kind": "TRAILING_VALUE_ROW", "record": canonical_clone_v1(candidate)},
        "values": [
            {
                "column_ordinal": value["column_ordinal"],
                "number": _number(value),
                "source_sample_ids": [value["sample_id"]],
            }
            for value in values
        ],
    }


def _metrics(
    resolved: Sequence[Mapping[str, Any]],
    equations: Sequence[Mapping[str, Any]],
    reasons: Sequence[str],
) -> dict[str, int]:
    return {
        "accounting_veto_count": len(reasons),
        "derived_role_count": sum(
            record["resolution_kind"] == "DERIVED_EXACT_COMPONENT_SUM" for record in resolved
        ),
        "equation_count": len(equations),
        "resolved_role_count": len(resolved),
        "visible_corroborated_role_count": sum(
            record["resolution_kind"]
            in {
                "VISIBLE_SOURCE_ROLE_CORROBORATED_BY_COMPONENTS",
                "VISIBLE_TRAILING_TOTAL_CORROBORATED_BY_COMPONENTS",
            }
            for record in resolved
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _RESULT_FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["family_id"]) is not str
        or not value["family_id"]
        or type(value["row_axis_id"]) is not str
        or not value["row_axis_id"].startswith("afrav1:axis:")
        or type(value["resolved_roles"]) is not list
        or type(value["equations"]) is not list
        or type(value["unresolved_reasons"]) is not list
        or value["status"]
        not in {
            "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO",
            "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO",
        }
        or not same_typed_json_v1(
            value["metrics"],
            _metrics(value["resolved_roles"], value["equations"], value["unresolved_reasons"]),
        )
    ):
        raise _error("hierarchical closure result contract drifted")
    roles = [record.get("role") for record in value["resolved_roles"]]
    if any(type(role) is not str or not role for role in roles) or len(roles) != len(set(roles)):
        raise _error("hierarchical closure resolved role axis drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("closure_id")
    if identity != "ahtcv1:closure:" + canonical_json_sha256_v1(material):
        raise _error("hierarchical closure identity drifted")
    return canonical_clone_v1(value)


def build_accounting_hierarchical_table_closure_v1(
    row_axis: Any,
    pages: Any,
    family_topology_spec: Any,
    hierarchy_spec: Any,
    *,
    visible_dash_rescues: Any = (),
) -> dict[str, Any]:
    """Resolve visible or exact-derived hierarchical accounting roles."""

    try:
        axis = row_axis_v1.validate_accounting_family_row_axis_replay_v1(
            row_axis,
            pages,
            family_topology_spec,
            visible_dash_rescues=visible_dash_rescues,
        )
    except row_axis_v1.AccountingFamilyRowAxisV1Error as exc:
        raise _error("hierarchical closure row-axis replay failed") from exc
    spec = _spec(hierarchy_spec, family_topology_spec)
    if axis["status"] != "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY":
        reasons = ["VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE"]
        resolved: dict[str, dict[str, Any]] = {}
    else:
        reasons = []
        resolved = {row["role"]: _row_resolution(row) for row in axis["rows"]}
        if len(resolved) != len(axis["rows"]):
            raise _error("hierarchical closure source roles repeat")
    equation_records = []
    for equation in spec["equations"]:
        result_role = equation["result_role"]
        component_roles = [role for role in equation["component_roles"] if role in resolved]
        components_complete = len(component_roles) >= equation["minimum_component_count"]
        component_sum = _sum_components(component_roles, resolved) if components_complete else None
        visible_candidates = [
            resolved[role] for role in equation["visible_result_roles"] if role in resolved
        ]
        if result_role in resolved and result_role not in equation["visible_result_roles"]:
            visible_candidates.insert(0, resolved[result_role])
        if visible_candidates and any(
            not _same_values(visible_candidates[0]["values"], candidate["values"])
            for candidate in visible_candidates[1:]
        ):
            reasons.append(f"VISIBLE_RESULT_ROLES_DISAGREE:{result_role}")
        visible = visible_candidates[0] if visible_candidates else None
        trailing = None
        if (
            component_sum is not None
            and not visible_candidates
            and equation["trailing_result_policy"] == "CORROBORATE_IF_PRESENT"
        ):
            trailing_rows = axis["trailing_value_rows"]
            if any(
                item.get("status")
                not in {
                    "COMPLETE_VISIBLE_TRAILING_VALUE_ROW",
                    "PARTIAL_TRAILING_VALUE_ROW_REQUIRES_PIXEL_RESCUE",
                }
                for item in trailing_rows
            ):
                raise _error("hierarchical closure trailing candidate status drifted")
            incomplete_count = sum(
                item["status"] == "PARTIAL_TRAILING_VALUE_ROW_REQUIRES_PIXEL_RESCUE"
                for item in trailing_rows
            )
            candidates = [
                _trailing_resolution(item)
                for item in trailing_rows
                if item["status"] == "COMPLETE_VISIBLE_TRAILING_VALUE_ROW"
            ]
            exact = [
                candidate
                for candidate in candidates
                if _same_values(candidate["values"], component_sum)
            ]
            if incomplete_count:
                reasons.append(
                    f"TRAILING_RESULT_INCOMPLETE_LANE_AXIS:{result_role}:{incomplete_count}"
                )
            elif candidates and len(exact) != 1:
                reasons.append(
                    f"TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM:{result_role}:{len(exact)}"
                )
            elif len(exact) == 1:
                trailing = exact[0]
        status = "NOT_APPLICABLE_NO_SOURCE_OR_COMPLETE_COMPONENT_SET"
        if visible is not None and component_sum is not None:
            if not _same_values(visible["values"], component_sum):
                reasons.append(f"VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM:{result_role}")
                status = "VISIBLE_RESULT_MISMATCH_VETO"
            else:
                status = "VISIBLE_RESULT_CORROBORATED_BY_COMPONENTS"
                resolved[result_role] = {
                    **canonical_clone_v1(visible),
                    "component_roles": list(component_roles),
                    "resolution_kind": "VISIBLE_SOURCE_ROLE_CORROBORATED_BY_COMPONENTS",
                    "role": result_role,
                }
        elif trailing is not None and component_sum is not None:
            status = "VISIBLE_TRAILING_RESULT_CORROBORATED_BY_COMPONENTS"
            resolved[result_role] = {
                **canonical_clone_v1(trailing),
                "component_roles": list(component_roles),
                "resolution_kind": "VISIBLE_TRAILING_TOTAL_CORROBORATED_BY_COMPONENTS",
                "role": result_role,
            }
        elif visible is not None:
            status = "VISIBLE_RESULT_RETAINED_WITH_INCOMPLETE_COMPONENT_SET"
            resolved[result_role] = {
                **canonical_clone_v1(visible),
                "component_roles": list(component_roles),
                "role": result_role,
            }
        elif component_sum is not None:
            status = "DERIVED_EXACT_COMPONENT_SUM"
            resolved[result_role] = {
                "component_roles": list(component_roles),
                "resolution_kind": "DERIVED_EXACT_COMPONENT_SUM",
                "role": result_role,
                "source": None,
                "values": component_sum,
            }
        equation_records.append(
            {
                "component_roles_present": list(component_roles),
                "result_role": result_role,
                "status": status,
            }
        )
    resolved_axis = [canonical_clone_v1(record) for record in resolved.values()]
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "equations": equation_records,
        "family_id": spec["family_id"],
        "format_version": FORMAT_VERSION,
        "metrics": _metrics(resolved_axis, equation_records, reasons),
        "resolved_roles": resolved_axis,
        "row_axis_id": axis["row_axis_id"],
        "safety": canonical_clone_v1(_SAFETY),
        "status": (
            "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
            if not reasons
            else "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
        ),
        "unresolved_reasons": list(dict.fromkeys(reasons)),
    }
    return _validate_result(
        {**material, "closure_id": "ahtcv1:closure:" + canonical_json_sha256_v1(material)}
    )


def validate_accounting_hierarchical_table_closure_replay_v1(
    value: Any,
    row_axis: Any,
    pages: Any,
    family_topology_spec: Any,
    hierarchy_spec: Any,
    *,
    visible_dash_rescues: Any = (),
) -> dict[str, Any]:
    """Exact-rebuild one hierarchical closure from visible source rows."""

    persisted = _validate_result(value)
    expected = build_accounting_hierarchical_table_closure_v1(
        row_axis,
        pages,
        family_topology_spec,
        hierarchy_spec,
        visible_dash_rescues=visible_dash_rescues,
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("hierarchical closure does not replay exactly")
    return persisted
