"""Exact visible-row additive closure for generic accounting tables.

The input row axis is rebuilt from the complete document before use.  This
stage sums only roles declared ``ADDITIVE_CHILD`` and compares those sums with
complete *visible* trailing numeric rows.  It never supplies a missing cell,
changes a recognizer token, chooses a period/unit, or maps a schema row.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.evaluation.accounting_family_row_axis_v1 import (
    AccountingFamilyRowAxisV1Error,
    validate_accounting_family_row_axis_replay_v1,
)
from bctc_ai.evaluation.accounting_family_topology_v1 import _spec as _topology_spec
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "AccountingAdditiveTableClosureV1Error",
    "build_accounting_additive_table_closure_v1",
    "validate_accounting_additive_table_closure_replay_v1",
]


FORMAT_VERSION = "ACCOUNTING_ADDITIVE_TABLE_CLOSURE_V1"
FORMAT_VERSION_V2 = "ACCOUNTING_ADDITIVE_TABLE_CLOSURE_V2"
CLAIM_BOUNDARY = (
    "EXACT_VISIBLE_ADDITIVE_CHILD_SUM_TO_UNIQUE_VISIBLE_TRAILING_TOTAL_"
    "CORROBORATION_ONLY_NO_DIGIT_REPAIR_MISSING_CELL_PERIOD_UNIT_POPULATION_"
    "SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
CLAIM_BOUNDARY_V2 = (
    "EXACT_VISIBLE_DECLARED_SOURCE_GROUP_REPRESENTATIVE_OR_ADDITIVE_CHILD_SUM_TO_"
    "UNIQUE_VISIBLE_TRAILING_TOTAL_CORROBORATION_ONLY_NO_DIGIT_REPAIR_MISSING_"
    "CELL_PERIOD_UNIT_POPULATION_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "accounting_equation_can_change_or_supply_digits": False,
    "accounting_relation_corroboration_only": True,
    "blank_token_means_zero": False,
    "dash_only_token_means_zero": True,
    "mapping_authority": False,
    "missing_cells_synthesized": False,
    "numeric_authority": False,
    "period_or_unit_authority": False,
    "raw_record_self_authenticating": False,
    "schema_authority": False,
    "unique_visible_total_required": True,
}
_RESULT_FIELDS = {
    "additive_roles",
    "claim_boundary",
    "closure_id",
    "exact_total_candidates",
    "family_id",
    "format_version",
    "lane_sums",
    "metrics",
    "row_axis_id",
    "safety",
    "status",
    "unresolved_reasons",
}
_RESULT_FIELDS_V2 = {*_RESULT_FIELDS, "source_group_equivalences"}
_EQUIVALENCE_FIELDS = {"component_roles", "group_role"}
_NUMBER_FIELDS = {"coefficient", "percentage_mark_present", "scale"}
_LANE_SUM_FIELDS = {
    "component_sample_ids",
    "component_values",
    "column_ordinal",
    "sum_value",
}
_CANDIDATE_FIELDS = {"candidate_ordinal", "page_sequence", "sample_ids", "values"}
_METRIC_FIELDS = {
    "additive_role_count",
    "exact_total_candidate_count",
    "lane_count",
    "visible_trailing_candidate_count",
}


class AccountingAdditiveTableClosureV1Error(ValueError):
    """The row-axis replay, equation, scalar type, or result identity drifted."""


def _error(message: str) -> AccountingAdditiveTableClosureV1Error:
    return AccountingAdditiveTableClosureV1Error(message)


def _number(value: Mapping[str, Any]) -> dict[str, Any] | None:
    parsed = value["parsed_token"]
    if parsed["classification"] not in {
        "DASH_ZERO",
        "MIXED_GROUPED_INTEGER_CANDIDATE",
        "SIGNED_NUMBER",
    }:
        return None
    coefficient = parsed["coefficient"]
    scale = parsed["scale"]
    percentage = parsed["percentage_mark_present"]
    if (
        type(coefficient) is not int
        or type(scale) is not int
        or scale < 0
        or type(percentage) is not bool
    ):
        raise _error("visible numeric token scalar types drifted")
    return {
        "coefficient": coefficient,
        "percentage_mark_present": percentage,
        "scale": scale,
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


def _sum_numbers(values: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    if not values:
        return None
    percentages = {value["percentage_mark_present"] for value in values}
    if len(percentages) != 1:
        return None
    scale = max(value["scale"] for value in values)
    coefficient = sum(value["coefficient"] * (10 ** (scale - value["scale"])) for value in values)
    return _canonical_number(coefficient, scale, next(iter(percentages)))


def _numbers_equal(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    if left["percentage_mark_present"] is not right["percentage_mark_present"]:
        return False
    scale = max(left["scale"], right["scale"])
    return left["coefficient"] * (10 ** (scale - left["scale"])) == right["coefficient"] * (
        10 ** (scale - right["scale"])
    )


def _lane_axis(rows: Sequence[Mapping[str, Any]]) -> list[int] | None:
    axes = []
    for row in rows:
        visible = [value["column_ordinal"] for value in row["values"]]
        axis = sorted({*visible, *row["missing_column_ordinals"]})
        if (
            row["status"] != "VISIBLE_VALUE_LANES_BOUND"
            or row["missing_column_ordinals"]
            or visible != axis
            or axis != list(range(len(axis)))
        ):
            return None
        axes.append(axis)
    return axes[0] if axes and all(axis == axes[0] for axis in axes) else None


def _lane_sums(
    rows: Sequence[Mapping[str, Any]], lane_axis: Sequence[int]
) -> list[dict[str, Any]] | None:
    result = []
    for lane in lane_axis:
        cells = [
            next(value for value in row["values"] if value["column_ordinal"] == lane)
            for row in rows
        ]
        numbers = [_number(cell) for cell in cells]
        if any(number is None for number in numbers):
            return None
        parsed = [number for number in numbers if number is not None]
        total = _sum_numbers(parsed)
        if total is None:
            return None
        result.append(
            {
                "column_ordinal": lane,
                "component_sample_ids": [cell["sample_id"] for cell in cells],
                "component_values": parsed,
                "sum_value": total,
            }
        )
    return result


def _exact_candidates(
    trailing: Sequence[Mapping[str, Any]],
    lane_axis: Sequence[int],
    lane_sums: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    exact = []
    for candidate in trailing:
        values = candidate["values"]
        if (
            candidate["status"] != "COMPLETE_VISIBLE_TRAILING_VALUE_ROW"
            or candidate["missing_column_ordinals"]
            or [value["column_ordinal"] for value in values] != list(lane_axis)
        ):
            continue
        parsed = [_number(value) for value in values]
        if any(number is None for number in parsed):
            continue
        numbers = [number for number in parsed if number is not None]
        if not all(
            _numbers_equal(lane_sum["sum_value"], number)
            for lane_sum, number in zip(lane_sums, numbers, strict=True)
        ):
            continue
        exact.append(
            {
                "candidate_ordinal": candidate["candidate_ordinal"],
                "page_sequence": candidate["page_sequence"],
                "sample_ids": [value["sample_id"] for value in values],
                "values": numbers,
            }
        )
    return exact


def _source_group_equivalences(value: Any, family_topology_spec: Any) -> list[dict[str, Any]]:
    if type(value) is not list:
        raise _error("source-group equivalences must be one exact list")
    try:
        compiled = _topology_spec(family_topology_spec)
    except (ValueError, RuntimeError) as exc:
        raise _error("source-group equivalence topology specification drifted") from exc
    role_kinds = {child["role"]: child["role_kind"] for child in compiled["children"]}
    result = []
    seen_groups: set[str] = set()
    seen_components: set[str] = set()
    for item in value:
        if (
            type(item) is not dict
            or set(item) != _EQUIVALENCE_FIELDS
            or type(item["group_role"]) is not str
            or not item["group_role"]
            or type(item["component_roles"]) is not list
            or not item["component_roles"]
            or any(type(role) is not str or not role for role in item["component_roles"])
            or len(item["component_roles"]) != len(set(item["component_roles"]))
            or item["group_role"] in item["component_roles"]
            or item["group_role"] in seen_groups
            or any(role in seen_components for role in item["component_roles"])
            or role_kinds.get(item["group_role"]) != "SOURCE_ONLY_GROUP_PARENT"
            or any(role_kinds.get(role) != "ADDITIVE_CHILD" for role in item["component_roles"])
        ):
            raise _error("source-group equivalence contract drifted")
        seen_groups.add(item["group_role"])
        seen_components.update(item["component_roles"])
        result.append(canonical_clone_v1(item))
    return result


def _numbers_by_lane(row: Mapping[str, Any]) -> tuple[list[int], list[dict[str, Any]]] | None:
    axis = _lane_axis([row])
    if axis is None:
        return None
    numbers = [
        _number(next(value for value in row["values"] if value["column_ordinal"] == lane))
        for lane in axis
    ]
    if any(number is None for number in numbers):
        return None
    return list(axis), [number for number in numbers if number is not None]


def _select_additive_rows(
    rows: Sequence[Mapping[str, Any]],
    equivalences: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    selected = [canonical_clone_v1(row) for row in rows if row["role_kind"] == "ADDITIVE_CHILD"]
    by_role = {row["role"]: row for row in rows}
    reasons = []
    for equivalence in equivalences:
        group = by_role.get(equivalence["group_role"])
        if group is None:
            continue
        components = [by_role[role] for role in equivalence["component_roles"] if role in by_role]
        if components and len(components) != len(equivalence["component_roles"]):
            reasons.append(
                "SOURCE_GROUP_EQUIVALENCE_PARTIAL_COMPONENT_POPULATION:" + equivalence["group_role"]
            )
            continue
        if components:
            group_axis = _numbers_by_lane(group)
            component_axis = _lane_axis(components)
            component_sums = (
                _lane_sums(components, component_axis) if component_axis is not None else None
            )
            if (
                group_axis is None
                or component_axis is None
                or component_sums is None
                or group_axis[0] != list(component_axis)
                or not all(
                    _numbers_equal(group_number, lane_sum["sum_value"])
                    for group_number, lane_sum in zip(group_axis[1], component_sums, strict=True)
                )
            ):
                reasons.append(
                    "SOURCE_GROUP_PARENT_NOT_EXACT_SUM_OF_DECLARED_COMPONENTS:"
                    + equivalence["group_role"]
                )
                continue
            component_roles = set(equivalence["component_roles"])
            selected = [row for row in selected if row["role"] not in component_roles]
        selected.append(canonical_clone_v1(group))
    role_order = {row["role"]: ordinal for ordinal, row in enumerate(rows)}
    selected.sort(key=lambda row: role_order[row["role"]])
    return selected, reasons


def _result_metrics(
    additive_roles: Sequence[str],
    lane_sums: Sequence[Mapping[str, Any]],
    exact: Sequence[Mapping[str, Any]],
    trailing_count: int,
) -> dict[str, int]:
    return {
        "additive_role_count": len(additive_roles),
        "exact_total_candidate_count": len(exact),
        "lane_count": len(lane_sums),
        "visible_trailing_candidate_count": trailing_count,
    }


def _validate_number(value: Any) -> None:
    if (
        type(value) is not dict
        or set(value) != _NUMBER_FIELDS
        or type(value["coefficient"]) is not int
        or type(value["scale"]) is not int
        or value["scale"] < 0
        or type(value["percentage_mark_present"]) is not bool
    ):
        raise _error("closure number record drifted")


def _validate_result(value: Any) -> dict[str, Any]:
    is_v2 = type(value) is dict and value.get("format_version") == FORMAT_VERSION_V2
    expected_fields = _RESULT_FIELDS_V2 if is_v2 else _RESULT_FIELDS
    expected_boundary = CLAIM_BOUNDARY_V2 if is_v2 else CLAIM_BOUNDARY
    if (
        type(value) is not dict
        or set(value) != expected_fields
        or value["format_version"] not in {FORMAT_VERSION, FORMAT_VERSION_V2}
        or value["claim_boundary"] != expected_boundary
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["family_id"]) is not str
        or not value["family_id"]
        or type(value["row_axis_id"]) is not str
        or not value["row_axis_id"].startswith("afrav1:axis:")
        or type(value["status"]) is not str
        or type(value["additive_roles"]) is not list
        or any(type(role) is not str or not role for role in value["additive_roles"])
        or type(value["lane_sums"]) is not list
        or type(value["exact_total_candidates"]) is not list
        or type(value["unresolved_reasons"]) is not list
        or any(type(reason) is not str or not reason for reason in value["unresolved_reasons"])
        or type(value.get("metrics")) is not dict
        or set(value["metrics"]) != _METRIC_FIELDS
        or any(type(metric) is not int or metric < 0 for metric in value["metrics"].values())
    ):
        raise _error("additive closure result contract drifted")
    if is_v2 and (
        type(value["source_group_equivalences"]) is not list
        or not value["source_group_equivalences"]
        or any(
            type(item) is not dict
            or set(item) != _EQUIVALENCE_FIELDS
            or type(item["group_role"]) is not str
            or not item["group_role"]
            or type(item["component_roles"]) is not list
            or not item["component_roles"]
            or any(type(role) is not str or not role for role in item["component_roles"])
            for item in value["source_group_equivalences"]
        )
    ):
        raise _error("additive closure source-group equivalence record drifted")
    for expected_lane, lane_sum in enumerate(value["lane_sums"]):
        if (
            type(lane_sum) is not dict
            or set(lane_sum) != _LANE_SUM_FIELDS
            or lane_sum["column_ordinal"] != expected_lane
            or type(lane_sum["component_sample_ids"]) is not list
            or any(type(item) is not str or not item for item in lane_sum["component_sample_ids"])
            or type(lane_sum["component_values"]) is not list
        ):
            raise _error("additive closure lane sum drifted")
        for number in [*lane_sum["component_values"], lane_sum["sum_value"]]:
            _validate_number(number)
    for candidate in value["exact_total_candidates"]:
        if (
            type(candidate) is not dict
            or set(candidate) != _CANDIDATE_FIELDS
            or type(candidate["candidate_ordinal"]) is not int
            or candidate["candidate_ordinal"] < 0
            or type(candidate["page_sequence"]) is not int
            or candidate["page_sequence"] <= 0
            or type(candidate["sample_ids"]) is not list
            or any(type(item) is not str or not item for item in candidate["sample_ids"])
            or type(candidate["values"]) is not list
        ):
            raise _error("additive closure exact candidate drifted")
        for number in candidate["values"]:
            _validate_number(number)
    expected_metrics = _result_metrics(
        value["additive_roles"],
        value["lane_sums"],
        value["exact_total_candidates"],
        value["metrics"]["visible_trailing_candidate_count"],
    )
    if not same_typed_json_v1(value["metrics"], expected_metrics):
        raise _error("additive closure metrics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("closure_id")
    identity_prefix = "aatcv2:closure:" if is_v2 else "aatcv1:closure:"
    if identity != identity_prefix + canonical_json_sha256_v1(material):
        raise _error("additive closure identity drifted")
    return canonical_clone_v1(value)


def build_accounting_additive_table_closure_v1(
    row_axis: Any,
    pages: Any,
    family_topology_spec: Any,
    *,
    source_group_equivalences: Any = (),
    visible_dash_rescues: Any = (),
) -> dict[str, Any]:
    """Corroborate exactly one visible trailing total across every numeric lane."""

    try:
        axis = validate_accounting_family_row_axis_replay_v1(
            row_axis,
            pages,
            family_topology_spec,
            visible_dash_rescues=visible_dash_rescues,
        )
    except AccountingFamilyRowAxisV1Error as exc:
        raise _error("additive closure row-axis replay failed") from exc
    raw_equivalences = [] if source_group_equivalences == () else source_group_equivalences
    equivalences = _source_group_equivalences(raw_equivalences, family_topology_spec)
    additive_rows, equivalence_reasons = _select_additive_rows(axis["rows"], equivalences)
    roles = [row["role"] for row in additive_rows]
    lane_axis = _lane_axis(additive_rows)
    sums = _lane_sums(additive_rows, lane_axis) if lane_axis is not None else None
    exact = (
        _exact_candidates(axis["trailing_value_rows"], lane_axis, sums)
        if lane_axis is not None and sums is not None
        else []
    )
    reasons = list(equivalence_reasons)
    if axis["topology_status"] != "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL":
        reasons.append("TOPOLOGY_NOT_UNIQUE_ACCEPTED_PROPOSAL")
    if not additive_rows:
        reasons.append("NO_ADDITIVE_CHILD_ROWS")
    elif lane_axis is None or sums is None:
        reasons.append("ADDITIVE_CHILD_LANES_INCOMPLETE_OR_NUMERIC_TOKEN_UNRESOLVED")
    elif not axis["trailing_value_rows"]:
        reasons.append("NO_VISIBLE_TRAILING_TOTAL_CANDIDATE")
    elif not exact:
        reasons.append("NO_TRAILING_ROW_EQUALS_VISIBLE_COMPONENT_SUMS_ON_EVERY_LANE")
    elif len(exact) > 1:
        reasons.append("MULTIPLE_TRAILING_ROWS_EQUAL_VISIBLE_COMPONENT_SUMS")
    status = (
        "CORROBORATED_EXACT_UNIQUE_TRAILING_TOTAL"
        if len(exact) == 1 and not reasons
        else "UNRESOLVED_ADDITIVE_TABLE_CLOSURE"
    )
    material = {
        "additive_roles": roles,
        "claim_boundary": CLAIM_BOUNDARY_V2 if equivalences else CLAIM_BOUNDARY,
        "exact_total_candidates": exact,
        "family_id": axis["family_id"],
        "format_version": FORMAT_VERSION_V2 if equivalences else FORMAT_VERSION,
        "lane_sums": sums or [],
        "metrics": _result_metrics(roles, sums or [], exact, len(axis["trailing_value_rows"])),
        "row_axis_id": axis["row_axis_id"],
        "safety": canonical_clone_v1(_SAFETY),
        "status": status,
        "unresolved_reasons": reasons,
    }
    if equivalences:
        material["source_group_equivalences"] = equivalences
    identity_prefix = "aatcv2:closure:" if equivalences else "aatcv1:closure:"
    return _validate_result(
        {**material, "closure_id": identity_prefix + canonical_json_sha256_v1(material)}
    )


def validate_accounting_additive_table_closure_replay_v1(
    value: Any,
    row_axis: Any,
    pages: Any,
    family_topology_spec: Any,
    *,
    source_group_equivalences: Any = (),
    visible_dash_rescues: Any = (),
) -> dict[str, Any]:
    """Reject any equation/result drift by exact complete-input reconstruction."""

    persisted = _validate_result(value)
    expected = build_accounting_additive_table_closure_v1(
        row_axis,
        pages,
        family_topology_spec,
        source_group_equivalences=source_group_equivalences,
        visible_dash_rescues=visible_dash_rescues,
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("additive closure does not replay exactly")
    return persisted
