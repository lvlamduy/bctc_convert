"""Fail-closed accounting closure for repeated, locally scoped role rows.

The sealed hierarchical closure V1 intentionally requires one row per role.
This opt-in primitive handles a different source structure: the same semantic
child may repeat under the nearest repeated structural parent.  Local printed
subtotals are checked only against children bound to that exact parent
occurrence; declared repeatable roles are then aggregated once across disjoint
scopes.  Every component alternative is exhaustive -- there is no
``minimum_component_count`` escape hatch and no source digit is backsolved.
"""

from __future__ import annotations

import hashlib
import os
import stat
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from bctc_ai.evaluation import accounting_family_occurrence_row_axis_v2 as occurrence_v2
from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "SPEC_FORMAT_VERSION",
    "AccountingScopedHierarchicalTableClosureV2Error",
    "build_accounting_scoped_hierarchical_table_closure_v2",
    "validate_accounting_scoped_hierarchical_table_closure_replay_v2",
]


FORMAT_VERSION = "ACCOUNTING_SCOPED_HIERARCHICAL_TABLE_CLOSURE_V2"
SPEC_FORMAT_VERSION = "ACCOUNTING_SCOPED_HIERARCHICAL_CLOSURE_SPEC_V1"
CLAIM_BOUNDARY = (
    "VISIBLE_COMPLETE_ROLE_OCCURRENCES_NEAREST_PARENT_LOCAL_SUBTOTAL_AND_"
    "DECLARED_DISJOINT_SCOPE_AGGREGATION_WITH_EXHAUSTIVE_COMPONENT_ALTERNATIVES_"
    "NO_DIGIT_REPAIR_BACKSOLVE_MISSING_CELL_PERIOD_UNIT_SCHEMA_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "accounting_equation_can_change_or_supply_source_digits": False,
    "all_component_alternatives_are_exhaustive": True,
    "blank_or_unproved_dash_means_zero": False,
    "local_subtotal_may_consume_other_parent_scope": False,
    "mapping_authority": False,
    "partial_component_set_can_derive_or_veto": False,
    "repeated_role_aggregation_requires_declaration": True,
    "schema_authority": False,
    "source_printed_residual_can_be_backsolved": False,
    "unbound_or_undeclared_repeated_rows_fail_closed": True,
    "visible_mismatch_is_veto": True,
}
_SPEC_FIELDS = {
    "equations",
    "family_id",
    "format_version",
    "repeated_role_policy",
}
_REPEAT_POLICY_FIELDS = {"aggregate_roles", "local_subtotal_roles"}
_EQUATION_FIELDS = {
    "application_policy",
    "component_role_alternatives",
    "result_role",
    "trailing_result_policy",
    "visible_source_policy",
    "visible_result_roles",
}
_ALTERNATIVE_FIELDS = {"component_roles", "coverage_policy", "derivation_policy"}
_DERIVATION_POLICIES = {
    "ALLOW_DERIVATION_FROM_EXHAUSTIVE_VISIBLE_COMPONENTS",
    "VISIBLE_RESULT_CORROBORATION_ONLY",
}
_TRAILING_POLICIES = {
    "IGNORE",
    "CORROBORATE_IF_PRESENT",
    "CORROBORATE_UNIQUE_MATCH_IF_PRESENT",
}
_APPLICATION_POLICY = "REQUIRED_WHEN_ANY_DECLARED_ROLE_VISIBLE"
_VISIBLE_SOURCE_POLICIES = {
    "ALLOW_ONLY_WHEN_NO_DECLARED_COMPONENT_ROLE_VISIBLE",
    "REQUIRE_EXHAUSTIVE_COMPONENTS",
}
_RESULT_FIELDS = {
    "authenticated_existing_dash_evidence",
    "claim_boundary",
    "closure_id",
    "coextensive_structural_numeric_evidence",
    "coverage_receipt",
    "dependency_content_refs",
    "equations",
    "family_id",
    "format_version",
    "metrics",
    "occurrence_axis_binding",
    "occurrence_axis_id",
    "resolved_roles",
    "role_occurrences",
    "row_axis_id",
    "safety",
    "status",
    "unresolved_reasons",
}
_COVERAGE_FIELDS = {
    "candidate_ordinal",
    "coverage_id",
    "disposition",
    "occurrence_id",
    "role",
    "row_kind",
    "sample_ids",
    "source_record",
}
_COEXTENSIVE_STRUCTURAL_NUMERIC_FIELDS = {
    "owner_component_occurrence_ids",
    "owner_occurrence_id",
    "owner_role",
    "projected_occurrence_id",
    "projected_role",
    "source_record",
    "source_sample_ids",
    "status",
}
_COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_STATUS = "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_ALREADY_OWNED"
_COEXTENSIVE_PRECEDING_NUMERIC_AMBIGUITY_STATUS = (
    "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_AMBIGUOUS_OWNERSHIP_VETO"
)
_MAX_EQUATIONS = 128
_MAX_COVERAGE_RECORDS = 16_384
_MAX_RESOLVED_ROLES = 4_096
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEPENDENCIES = {
    "occurrence_row_axis_v2": {
        "path": "src/bctc_ai/evaluation/accounting_family_occurrence_row_axis_v2.py",
        "sha256": "2cc337317371d1a3b60679eae8683258eeb4473a9324a3d41e084364be046bfc",
        "size_bytes": 57_243,
    },
    "topology_v1": {
        "path": "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
        "sha256": "60da089b5df5a6ee9f53dac8569bc4a9484bf5816721fb992f8d4d09a43bc236",
        "size_bytes": 68_515,
    },
}


class AccountingScopedHierarchicalTableClosureV2Error(ValueError):
    """The scope graph, exhaustive equation, numeric lane, or replay drifted."""


def _error(message: str) -> AccountingScopedHierarchicalTableClosureV2Error:
    return AccountingScopedHierarchicalTableClosureV2Error(message)


def _stable_dependency_ref(expected: Mapping[str, Any]) -> dict[str, Any]:
    path = _PROJECT_ROOT / expected["path"]
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = -1
    try:
        descriptor = os.open(path, flags)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise _error("scoped closure dependency is not one regular nofollow file")
        chunks = []
        while chunk := os.read(descriptor, 1 << 20):
            chunks.append(chunk)
        after = os.fstat(descriptor)
    except OSError as exc:
        raise _error("scoped closure dependency cannot be read stable nofollow") from exc
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
        raise _error("scoped closure dependency content reference drifted")
    return observed


def _dependency_refs() -> dict[str, dict[str, Any]]:
    return {
        name: _stable_dependency_ref(expected) for name, expected in sorted(_DEPENDENCIES.items())
    }


def _spec(value: Any, family_topology_spec: Any) -> dict[str, Any]:
    try:
        topology = topology_v1._spec(family_topology_spec)
    except (ValueError, RuntimeError) as exc:
        raise _error("scoped hierarchical topology specification drifted") from exc
    if (
        type(value) is not dict
        or set(value) != _SPEC_FIELDS
        or value["format_version"] != SPEC_FORMAT_VERSION
        or value["family_id"] != topology["family_id"]
        or type(value["equations"]) is not list
        or not value["equations"]
        or len(value["equations"]) > _MAX_EQUATIONS
        or type(value["repeated_role_policy"]) is not dict
        or set(value["repeated_role_policy"]) != _REPEAT_POLICY_FIELDS
    ):
        raise _error("scoped hierarchical specification fields drifted")
    child_roles = {child["role"] for child in topology["children"]}
    known_roles = {topology["parent"]["role"], *child_roles}
    repeat = value["repeated_role_policy"]
    for field in sorted(_REPEAT_POLICY_FIELDS):
        roles = repeat[field]
        if (
            type(roles) is not list
            or roles != sorted(set(roles))
            or any(role not in known_roles for role in roles)
        ):
            raise _error("scoped hierarchical repeated-role policy drifted")
    result_roles: set[str] = set()
    visible_roles: set[str] = set()
    trailing_equation_count = 0
    equations = []
    for raw in value["equations"]:
        if (
            type(raw) is not dict
            or set(raw) != _EQUATION_FIELDS
            or raw["result_role"] not in known_roles
            or raw["result_role"] in result_roles
            or raw["application_policy"] != _APPLICATION_POLICY
            or type(raw["visible_result_roles"]) is not list
            or not raw["visible_result_roles"]
            or len(raw["visible_result_roles"]) != len(set(raw["visible_result_roles"]))
            or any(role not in child_roles for role in raw["visible_result_roles"])
            or any(role in visible_roles for role in raw["visible_result_roles"])
            or raw["trailing_result_policy"] not in _TRAILING_POLICIES
            or raw["visible_source_policy"] not in _VISIBLE_SOURCE_POLICIES
            or type(raw["component_role_alternatives"]) is not list
            or not raw["component_role_alternatives"]
        ):
            raise _error("scoped hierarchical equation contract drifted")
        alternatives = []
        signatures: set[tuple[str, ...]] = set()
        for alternative in raw["component_role_alternatives"]:
            if (
                type(alternative) is not dict
                or set(alternative) != _ALTERNATIVE_FIELDS
                or alternative["coverage_policy"] != "EXHAUSTIVE_COMPONENT_SET"
                or alternative["derivation_policy"] not in _DERIVATION_POLICIES
                or type(alternative["component_roles"]) is not list
                or not alternative["component_roles"]
                or len(alternative["component_roles"]) != len(set(alternative["component_roles"]))
                or raw["result_role"] in alternative["component_roles"]
                or any(role not in known_roles for role in alternative["component_roles"])
            ):
                raise _error("scoped hierarchical exhaustive alternative drifted")
            signature = tuple(alternative["component_roles"])
            if signature in signatures:
                raise _error("scoped hierarchical component alternatives repeat")
            signatures.add(signature)
            alternatives.append(canonical_clone_v1(alternative))
        if any(
            role not in child_roles and role not in result_roles
            for alternative in alternatives
            for role in alternative["component_roles"]
        ):
            raise _error("scoped hierarchical equations are not in dependency order")
        result_roles.add(raw["result_role"])
        visible_roles.update(raw["visible_result_roles"])
        trailing_equation_count += raw["trailing_result_policy"] != "IGNORE"
        equations.append(
            {
                "component_role_alternatives": alternatives,
                "application_policy": raw["application_policy"],
                "result_role": raw["result_role"],
                "trailing_result_policy": raw["trailing_result_policy"],
                "visible_source_policy": raw["visible_source_policy"],
                "visible_result_roles": canonical_clone_v1(raw["visible_result_roles"]),
            }
        )
    if any(role not in result_roles for role in repeat["local_subtotal_roles"]):
        raise _error("local subtotal role has no declared equation")
    if trailing_equation_count > 1:
        raise _error("more than one scoped equation claims the trailing numeric axis")
    component_equation_counts: dict[str, int] = {}
    for equation in equations:
        for role in {
            role
            for alternative in equation["component_role_alternatives"]
            for role in alternative["component_roles"]
        }:
            component_equation_counts[role] = component_equation_counts.get(role, 0) + 1
    for equation in equations:
        equation["shared_component_roles"] = sorted(
            role
            for role in {
                role
                for alternative in equation["component_role_alternatives"]
                for role in alternative["component_roles"]
            }
            if component_equation_counts[role] > 1
        )
    return {
        "equations": equations,
        "family_id": topology["family_id"],
        "format_version": SPEC_FORMAT_VERSION,
        "repeated_role_policy": canonical_clone_v1(repeat),
        "role_kind_by_role": {child["role"]: child["role_kind"] for child in topology["children"]},
    }


def _number(value: Mapping[str, Any]) -> dict[str, Any]:
    parsed = value.get("parsed_token")
    if (
        type(parsed) is not dict
        or parsed.get("classification")
        not in {
            "DASH_ZERO",
            "MIXED_GROUPED_INTEGER_CANDIDATE",
            "NOISE_SUFFIXED_GROUPED_INTEGER_CANDIDATE",
            "SIGNED_NUMBER",
        }
        or type(parsed.get("coefficient")) is not int
        or type(parsed.get("scale")) is not int
        or parsed["scale"] < 0
        or type(parsed.get("percentage_mark_present")) is not bool
        or type(value.get("sample_id")) is not str
        or not value["sample_id"]
    ):
        raise _error("scoped hierarchical source cell is not one exact numeric token")
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
    return left["coefficient"] * 10 ** (scale - left["scale"]) == right["coefficient"] * 10 ** (
        scale - right["scale"]
    )


def _source_resolution(row: Mapping[str, Any]) -> dict[str, Any]:
    values = row.get("values")
    if (
        row.get("status") != "VISIBLE_VALUE_LANES_BOUND"
        or type(values) is not list
        or not values
        or [item.get("column_ordinal") for item in values] != list(range(len(values)))
    ):
        raise _error("scoped hierarchical role row does not cover one complete lane axis")
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


def _trailing_resolution(candidate: Mapping[str, Any]) -> dict[str, Any]:
    values = candidate.get("values")
    if (
        candidate.get("status") != "COMPLETE_VISIBLE_TRAILING_VALUE_ROW"
        or type(values) is not list
        or not values
        or [item.get("column_ordinal") for item in values] != list(range(len(values)))
    ):
        raise _error("scoped hierarchical trailing candidate axis drifted")
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


def _sum_records(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    axes = [[value["column_ordinal"] for value in record["values"]] for record in records]
    if not axes or any(axis != axes[0] for axis in axes):
        raise _error("scoped hierarchical component lane axes differ")
    result = []
    for lane in axes[0]:
        values = [
            next(value for value in record["values"] if value["column_ordinal"] == lane)
            for record in records
        ]
        percentages = {value["number"]["percentage_mark_present"] for value in values}
        if len(percentages) != 1:
            raise _error("scoped hierarchical equation mixes money and percentage lanes")
        scale = max(value["number"]["scale"] for value in values)
        coefficient = sum(
            value["number"]["coefficient"] * 10 ** (scale - value["number"]["scale"])
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


def _residuals(
    visible: Sequence[Mapping[str, Any]], components: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]] | None:
    if [item["column_ordinal"] for item in visible] != [
        item["column_ordinal"] for item in components
    ]:
        return None
    result = []
    for left, right in zip(visible, components, strict=True):
        a, b = left["number"], right["number"]
        if a["percentage_mark_present"] is not b["percentage_mark_present"]:
            return None
        scale = max(a["scale"], b["scale"])
        coefficient = a["coefficient"] * 10 ** (scale - a["scale"]) - b["coefficient"] * 10 ** (
            scale - b["scale"]
        )
        result.append(
            {
                "column_ordinal": left["column_ordinal"],
                "number": _canonical_number(coefficient, scale, a["percentage_mark_present"]),
            }
        )
    return result


def _typed_residual_evidence(
    *,
    result_role: str,
    printed: Mapping[str, Any],
    component: Mapping[str, Any],
    component_roles: Sequence[str],
) -> dict[str, Any] | None:
    residuals = _residuals(printed["values"], component["values"])
    if residuals is None:
        return None
    source = printed["source"]
    candidate_ordinal = (
        source["record"]["candidate_ordinal"]
        if source is not None and source["kind"] == "TRAILING_VALUE_ROW"
        else None
    )
    lanes = []
    for residual, visible_value, component_value in zip(
        residuals, printed["values"], component["values"], strict=True
    ):
        lanes.append(
            {
                "column_ordinal": residual["column_ordinal"],
                "component_source_sample_ids": canonical_clone_v1(
                    component_value["source_sample_ids"]
                ),
                "component_sum_number": canonical_clone_v1(component_value["number"]),
                "printed_result_number": canonical_clone_v1(visible_value["number"]),
                "printed_result_source_sample_ids": canonical_clone_v1(
                    visible_value["source_sample_ids"]
                ),
                "residual_number": canonical_clone_v1(residual["number"]),
            }
        )
    return {
        "candidate_ordinal": candidate_ordinal,
        "component_roles": list(component_roles),
        "convention": "PRINTED_RESULT_MINUS_EXHAUSTIVE_COMPONENT_SUM",
        "lanes": lanes,
        "result_role": result_role,
    }


def _aggregate_source_roles(
    rows: Sequence[Mapping[str, Any]],
    aggregate_roles: set[str],
    local_subtotal_roles: set[str],
    locally_valid_result_occurrences: set[str],
    locally_authorized_component_scopes: set[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]], list[str]]:
    occurrences: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        occurrence_id = row["label_match"].get("occurrence_id")
        scope_owner_id = row["label_match"].get("scope_owner_occurrence_id")
        if type(occurrence_id) is not str or type(scope_owner_id) is not str:
            raise _error("scoped source row lost occurrence or nearest-parent identity")
        occurrences.setdefault(row["role"], []).append(
            {
                "occurrence_id": occurrence_id,
                "resolution": _source_resolution(row),
                "scope_id": (
                    occurrence_id if row["role"] in local_subtotal_roles else scope_owner_id
                ),
                "scope_owner_role": row["label_match"].get("scope_owner_role"),
            }
        )
    resolved: dict[str, dict[str, Any]] = {}
    reasons = []
    for role, records in occurrences.items():
        occurrence_ids = [record["occurrence_id"] for record in records]
        scope_ids = [record["scope_id"] for record in records]
        if len(occurrence_ids) != len(set(occurrence_ids)):
            raise _error("same source role occurrence is present more than once")
        repeated_scope_is_not_disjoint = (
            len(records) > 1 and role in aggregate_roles and len(scope_ids) != len(set(scope_ids))
        )
        if repeated_scope_is_not_disjoint:
            reasons.append(f"REPEATED_ROLE_SCOPE_IS_NOT_DISJOINT:{role}")
        uncorroborated_local_scopes = sorted(
            {
                record["scope_id"]
                for record in records
                if record["scope_owner_role"] in local_subtotal_roles
                and record["scope_id"] not in locally_authorized_component_scopes
            }
        )
        if uncorroborated_local_scopes:
            reasons.extend(
                f"LOCAL_COMPONENT_SCOPE_LACKS_CORROBORATED_SUBTOTAL:{role}:{scope_id}"
                for scope_id in uncorroborated_local_scopes
            )
            continue
        if role in local_subtotal_roles and any(
            occurrence_id not in locally_valid_result_occurrences
            for occurrence_id in occurrence_ids
        ):
            reasons.append(f"LOCAL_SUBTOTAL_ROLE_HAS_UNCORROBORATED_OCCURRENCE:{role}")
            continue
        if len(records) == 1:
            resolved[role] = records[0]["resolution"]
        elif role not in aggregate_roles:
            reasons.append(f"UNDECLARED_REPEATED_VISIBLE_ROLE:{role}:{len(records)}")
        elif repeated_scope_is_not_disjoint:
            continue
        else:
            resolved[role] = {
                "component_roles": [],
                "resolution_kind": "DERIVED_EXACT_DISJOINT_OCCURRENCE_SUM",
                "role": role,
                "source": None,
                "values": _sum_records([record["resolution"] for record in records]),
            }
    return resolved, occurrences, reasons


def _complete_alternatives(
    alternatives: Sequence[Mapping[str, Any]],
    resolved: Mapping[str, Mapping[str, Any]],
    required_component_roles: set[str],
) -> list[dict[str, Any]]:
    result = []
    for alternative in alternatives:
        roles = alternative["component_roles"]
        if not required_component_roles <= set(roles) or not all(
            role in resolved for role in roles
        ):
            continue
        result.append(
            {
                "component_roles": list(roles),
                "derivation_policy": alternative["derivation_policy"],
                "values": _sum_records([resolved[role] for role in roles]),
            }
        )
    return result


def _local_equations(
    equation: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    role_occurrences: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], set[str], set[str], set[str], list[str]]:
    rows_by_occurrence: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        occurrence_id = row["label_match"].get("occurrence_id")
        if type(occurrence_id) is not str or occurrence_id in rows_by_occurrence:
            raise _error("local equation row occurrence axis repeats or drifted")
        rows_by_occurrence[occurrence_id] = row
    result_occurrences = [
        occurrence
        for occurrence in role_occurrences
        if occurrence["role"] == equation["result_role"]
    ]
    records = []
    reasons = []
    valid_results: set[str] = set()
    authorized_component_scopes: set[str] = set()
    covered_components: set[str] = set()
    component_universe = {
        role
        for alternative in equation["component_role_alternatives"]
        for role in alternative["component_roles"]
    }
    scoped_occurrences_by_result = {
        result_occurrence["occurrence_id"]: [
            occurrence
            for occurrence in role_occurrences
            if occurrence.get("scope_owner_occurrence_id") == result_occurrence["occurrence_id"]
            and occurrence["role"] in component_universe
        ]
        for result_occurrence in result_occurrences
    }
    active_component_scope_ids = {
        result_occurrence_id
        for result_occurrence_id, scoped_occurrences in scoped_occurrences_by_result.items()
        if any(
            rows_by_occurrence.get(occurrence["occurrence_id"], {}).get("values")
            for occurrence in scoped_occurrences
        )
    }
    active_local_scope_ids = active_component_scope_ids | {
        result_occurrence["occurrence_id"]
        for result_occurrence in result_occurrences
        if rows_by_occurrence.get(result_occurrence["occurrence_id"], {}).get("values")
    }
    for result_occurrence_record in result_occurrences:
        result_occurrence = result_occurrence_record.get("occurrence_id")
        if type(result_occurrence) is not str:
            raise _error("local subtotal occurrence lost its identity")
        scoped_occurrences = scoped_occurrences_by_result[result_occurrence]
        scoped_rows = [
            rows_by_occurrence[occurrence["occurrence_id"]]
            for occurrence in scoped_occurrences
            if occurrence["occurrence_id"] in rows_by_occurrence
        ]
        result_row = rows_by_occurrence.get(result_occurrence)
        has_valued_scoped_component = result_occurrence in active_component_scope_ids
        if (
            result_row is not None
            and result_row.get("values")
            and result_row.get("status") != "VISIBLE_VALUE_LANES_BOUND"
        ):
            records.append(
                {
                    "component_roles_present": [],
                    "result_occurrence_id": result_occurrence,
                    "result_role": equation["result_role"],
                    "status": "LOCAL_SUBTOTAL_RESULT_PARTIAL_VALUE_LANES_VETO",
                }
            )
            reasons.append(
                f"LOCAL_SUBTOTAL_RESULT_PARTIAL_VALUE_LANES:"
                f"{equation['result_role']}:{result_occurrence}"
            )
            continue
        if result_row is None and has_valued_scoped_component:
            if len(active_local_scope_ids) == 1:
                authorized_component_scopes.add(result_occurrence)
                records.append(
                    {
                        "component_roles_present": [],
                        "result_occurrence_id": result_occurrence,
                        "result_role": equation["result_role"],
                        "status": (
                            "LOCAL_SINGLE_SCOPE_WITHOUT_VISIBLE_SUBTOTAL_"
                            "DEFERRED_TO_EXHAUSTIVE_GLOBAL_EQUATION"
                        ),
                    }
                )
                continue
            records.append(
                {
                    "component_roles_present": [],
                    "result_occurrence_id": result_occurrence,
                    "result_role": equation["result_role"],
                    "status": "LOCAL_SUBTOTAL_RESULT_MISSING_OR_INCOMPLETE_VETO",
                }
            )
            reasons.append(
                f"LOCAL_SUBTOTAL_RESULT_MISSING_OR_INCOMPLETE:"
                f"{equation['result_role']}:{result_occurrence}"
            )
            continue
        if result_row is not None and result_row["status"] != "VISIBLE_VALUE_LANES_BOUND":
            records.append(
                {
                    "component_roles_present": [],
                    "result_occurrence_id": result_occurrence,
                    "result_role": equation["result_role"],
                    "status": "LOCAL_SUBTOTAL_RESULT_MISSING_OR_INCOMPLETE_VETO",
                }
            )
            reasons.append(
                f"LOCAL_SUBTOTAL_RESULT_MISSING_OR_INCOMPLETE:"
                f"{equation['result_role']}:{result_occurrence}"
            )
            continue
        if result_row is None:
            continue
        scoped_by_role: dict[str, list[dict[str, Any]]] = {}
        for row in scoped_rows:
            if row["status"] == "VISIBLE_VALUE_LANES_BOUND":
                scoped_by_role.setdefault(row["role"], []).append(_source_resolution(row))
        alternatives = []
        visible_component_roles = {row["role"] for row in scoped_rows if row["values"]}
        required_component_roles = visible_component_roles - set(equation["shared_component_roles"])
        visible_exclusive_component_roles = visible_component_roles - set(
            equation["shared_component_roles"]
        )
        for alternative in equation["component_role_alternatives"]:
            roles = alternative["component_roles"]
            if not required_component_roles <= set(roles) or not all(
                len(scoped_by_role.get(role, [])) == 1 for role in roles
            ):
                continue
            alternatives.append(
                {
                    "component_roles": list(roles),
                    "component_occurrence_ids": [
                        next(
                            row["label_match"]["occurrence_id"]
                            for row in scoped_rows
                            if row["role"] == role and row["status"] == "VISIBLE_VALUE_LANES_BOUND"
                        )
                        for role in roles
                    ],
                    "values": _sum_records([scoped_by_role[role][0] for role in roles]),
                }
            )
        visible = _source_resolution(result_row)
        exact = [item for item in alternatives if _same_values(visible["values"], item["values"])]
        if exact:
            selected = max(exact, key=lambda item: len(item["component_roles"]))
            status = "LOCAL_VISIBLE_SUBTOTAL_CORROBORATED_BY_EXACT_SCOPED_COMPONENTS"
            component_roles = selected["component_roles"]
            valid_results.add(result_occurrence)
            authorized_component_scopes.add(result_occurrence)
            covered_components.update(selected["component_occurrence_ids"])
        elif alternatives:
            status = "LOCAL_VISIBLE_SUBTOTAL_MISMATCH_VETO"
            component_roles = []
            reasons.append(
                f"LOCAL_VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM:{equation['result_role']}:"
                f"{result_occurrence}"
            )
        elif (
            not visible_exclusive_component_roles
            and equation["visible_source_policy"]
            == "ALLOW_ONLY_WHEN_NO_DECLARED_COMPONENT_ROLE_VISIBLE"
        ):
            status = "LOCAL_VISIBLE_SOURCE_ONLY_NO_DECLARED_COMPONENT_VISIBLE"
            component_roles = []
            valid_results.add(result_occurrence)
        else:
            status = "LOCAL_VISIBLE_SUBTOTAL_INCOMPLETE_COMPONENT_SET_VETO"
            component_roles = []
            reasons.append(
                f"LOCAL_VISIBLE_RESULT_LACKS_EXHAUSTIVE_COMPONENT_SET:"
                f"{equation['result_role']}:{result_occurrence}"
            )
        records.append(
            {
                "component_roles_present": component_roles,
                "result_occurrence_id": result_occurrence,
                "result_role": equation["result_role"],
                "status": status,
            }
        )
    return (
        records,
        valid_results,
        authorized_component_scopes,
        covered_components,
        reasons,
    )


def _select_global_equation(
    equation: Mapping[str, Any],
    resolved: dict[str, dict[str, Any]],
    trailing_rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    result_role = equation["result_role"]
    component_universe = {
        role
        for alternative in equation["component_role_alternatives"]
        for role in alternative["component_roles"]
    }
    required_component_roles = (component_universe - set(equation["shared_component_roles"])) & set(
        resolved
    )
    alternatives = _complete_alternatives(
        equation["component_role_alternatives"], resolved, required_component_roles
    )
    visible_candidates = [
        resolved[role] for role in equation["visible_result_roles"] if role in resolved
    ]
    if result_role in resolved and result_role not in equation["visible_result_roles"]:
        visible_candidates.insert(0, resolved[result_role])
    reasons: list[str] = []
    residual_evidence: list[dict[str, Any]] = []
    trailing_candidate_evidence: list[dict[str, Any]] = []
    selected_trailing_candidate_ordinal: int | None = None
    if visible_candidates and any(
        not _same_values(visible_candidates[0]["values"], item["values"])
        for item in visible_candidates[1:]
    ):
        reasons.append(f"VISIBLE_RESULT_ROLES_DISAGREE:{result_role}")
    visible = visible_candidates[0] if visible_candidates else None
    selected: dict[str, Any] | None = None
    source = visible
    status = "NOT_APPLICABLE_NO_SOURCE_OR_EXHAUSTIVE_COMPONENT_SET"
    if visible is not None:
        exact = [item for item in alternatives if _same_values(visible["values"], item["values"])]
        if exact:
            maximum = max(len(item["component_roles"]) for item in exact)
            strongest = [item for item in exact if len(item["component_roles"]) == maximum]
            if len(strongest) == 1:
                selected = strongest[0]
                status = "VISIBLE_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS"
            else:
                status = "AMBIGUOUS_EXACT_COMPONENT_OWNERSHIP_VETO"
                reasons.append(f"AMBIGUOUS_EXACT_COMPONENT_OWNERSHIP:{result_role}")
        elif alternatives:
            status = "VISIBLE_RESULT_MISMATCH_VETO"
            for alternative in alternatives:
                evidence = _typed_residual_evidence(
                    result_role=result_role,
                    printed=visible,
                    component=alternative,
                    component_roles=alternative["component_roles"],
                )
                if evidence is not None:
                    residual_evidence.append(evidence)
            reasons.append(f"VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM:{result_role}")
        elif (
            not ((component_universe - set(equation["shared_component_roles"])) & set(resolved))
            and equation["visible_source_policy"]
            == "ALLOW_ONLY_WHEN_NO_DECLARED_COMPONENT_ROLE_VISIBLE"
        ):
            status = "VISIBLE_SOURCE_ONLY_NO_DECLARED_COMPONENT_VISIBLE"
        else:
            status = "VISIBLE_RESULT_INCOMPLETE_COMPONENT_SET_VETO"
            reasons.append(f"VISIBLE_RESULT_LACKS_EXHAUSTIVE_COMPONENT_SET:{result_role}")
    else:
        claimed_trailing = equation["trailing_result_policy"] != "IGNORE"
        complete_trailing = [
            (row, _trailing_resolution(row))
            for row in trailing_rows
            if row["status"] == "COMPLETE_VISIBLE_TRAILING_VALUE_ROW"
        ]
        exact_pairs = [
            (alternative, row, candidate)
            for alternative in alternatives
            for row, candidate in complete_trailing
            if _same_values(alternative["values"], candidate["values"])
        ]
        exact_candidate_ordinals = {
            row["candidate_ordinal"] for _alternative, row, _candidate in exact_pairs
        }
        if claimed_trailing and len(trailing_rows) == 1 and len(exact_candidate_ordinals) == 1:
            exact = [
                (alternative, row, candidate)
                for alternative, row, candidate in exact_pairs
                if row["candidate_ordinal"] in exact_candidate_ordinals
            ]
            maximum = max(len(item[0]["component_roles"]) for item in exact)
            strongest = [item for item in exact if len(item[0]["component_roles"]) == maximum]
            if len(strongest) == 1:
                selected, selected_row, source = strongest[0]
                selected_trailing_candidate_ordinal = selected_row["candidate_ordinal"]
                status = "VISIBLE_TRAILING_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS"
            else:
                status = "AMBIGUOUS_EXACT_COMPONENT_OWNERSHIP_VETO"
                reasons.append(f"AMBIGUOUS_EXACT_COMPONENT_OWNERSHIP:{result_role}")
        elif claimed_trailing and trailing_rows:
            status = "TRAILING_NUMERIC_CHALLENGER_VETO"
            reasons.append(
                f"TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM:{result_role}:"
                f"{len(exact_candidate_ordinals)}"
            )
        elif alternatives and equation["trailing_result_policy"] != (
            "CORROBORATE_UNIQUE_MATCH_IF_PRESENT"
        ):
            derivable = [
                item
                for item in alternatives
                if item["derivation_policy"]
                == "ALLOW_DERIVATION_FROM_EXHAUSTIVE_VISIBLE_COMPONENTS"
            ]
            distinct = {canonical_json_sha256_v1(item["values"]): item for item in derivable}
            if len(distinct) == 1:
                strongest = [
                    item
                    for item in derivable
                    if len(item["component_roles"])
                    == max(len(entry["component_roles"]) for entry in derivable)
                ]
                if len(strongest) == 1:
                    selected = strongest[0]
                    source = None
                    status = "DERIVED_EXACT_EXHAUSTIVE_COMPONENT_SUM"
                else:
                    status = "AMBIGUOUS_EXACT_COMPONENT_OWNERSHIP_VETO"
                    reasons.append(f"AMBIGUOUS_EXACT_COMPONENT_OWNERSHIP:{result_role}")
            elif derivable:
                status = "EXHAUSTIVE_COMPONENT_ALTERNATIVES_DISAGREE_VETO"
                reasons.append(f"EXHAUSTIVE_COMPONENT_ALTERNATIVES_DISAGREE:{result_role}")
            else:
                status = "VISIBLE_RESULT_REQUIRED_FOR_COMPONENT_ALTERNATIVE_VETO"
                reasons.append(f"VISIBLE_RESULT_REQUIRED_FOR_COMPONENT_ALTERNATIVE:{result_role}")
        elif {
            result_role,
            *equation["visible_result_roles"],
            *component_universe,
        } & set(resolved):
            status = "REQUIRED_EQUATION_INCOMPLETE_COMPONENT_SET_VETO"
            reasons.append(f"REQUIRED_EQUATION_LACKS_EXHAUSTIVE_COMPONENT_SET:{result_role}")
    if equation["trailing_result_policy"] != "IGNORE":
        for row in trailing_rows:
            candidate_ordinal = row["candidate_ordinal"]
            is_selected = candidate_ordinal == selected_trailing_candidate_ordinal
            candidate_status = (
                "SELECTED_VISIBLE_TRAILING_ROOT_SOURCE"
                if is_selected
                else "UNRESOLVED_PARTIAL_TRAILING_NUMERIC_CHALLENGER"
                if row["status"] != "COMPLETE_VISIBLE_TRAILING_VALUE_ROW"
                else "UNRESOLVED_UNSELECTED_COMPLETE_TRAILING_NUMERIC_CHALLENGER"
            )
            trailing_candidate_evidence.append(
                {
                    "candidate_ordinal": candidate_ordinal,
                    "sample_ids": [value["sample_id"] for value in row["values"]],
                    "source_record": canonical_clone_v1(row),
                    "status": candidate_status,
                }
            )
            if not is_selected:
                reasons.append(f"{candidate_status}:{result_role}:{candidate_ordinal}")
                if row["status"] == "COMPLETE_VISIBLE_TRAILING_VALUE_ROW":
                    candidate = _trailing_resolution(row)
                    residual_evidence.extend(
                        evidence
                        for alternative in alternatives
                        if (
                            evidence := _typed_residual_evidence(
                                result_role=result_role,
                                printed=candidate,
                                component=alternative,
                                component_roles=alternative["component_roles"],
                            )
                        )
                        is not None
                    )
    if selected is not None:
        if source is None:
            resolved[result_role] = {
                "component_roles": selected["component_roles"],
                "resolution_kind": "DERIVED_EXACT_COMPONENT_SUM",
                "role": result_role,
                "source": None,
                "values": canonical_clone_v1(selected["values"]),
            }
        else:
            source_kind = source["source"]["kind"] if source["source"] is not None else None
            resolved[result_role] = {
                **canonical_clone_v1(source),
                "component_roles": selected["component_roles"],
                "resolution_kind": (
                    "VISIBLE_TRAILING_TOTAL_CORROBORATED_BY_COMPONENTS"
                    if source_kind == "TRAILING_VALUE_ROW"
                    else "DERIVED_EXACT_DISJOINT_OCCURRENCE_SUM_CORROBORATED_BY_COMPONENTS"
                    if source_kind is None
                    else "VISIBLE_SOURCE_ROLE_CORROBORATED_BY_COMPONENTS"
                ),
                "role": result_role,
            }
    return {
        "component_roles_present": selected["component_roles"] if selected is not None else [],
        "residual_evidence": residual_evidence,
        "result_role": result_role,
        "selected_trailing_candidate_ordinal": selected_trailing_candidate_ordinal,
        "status": status,
        "trailing_candidate_evidence": trailing_candidate_evidence,
    }, reasons


def _metrics(
    resolved: Sequence[Mapping[str, Any]],
    equations: Sequence[Mapping[str, Any]],
    local_equations: Sequence[Mapping[str, Any]],
    coverage_receipt: Sequence[Mapping[str, Any]],
    reasons: Sequence[str],
) -> dict[str, int]:
    return {
        "accounting_veto_count": len(reasons),
        "derived_role_count": sum(
            str(record["resolution_kind"]).startswith("DERIVED_EXACT") for record in resolved
        ),
        "equation_count": len(equations),
        "local_equation_count": len(local_equations),
        "covered_occurrence_count": len(coverage_receipt),
        "resolved_role_count": len(resolved),
        "visible_corroborated_role_count": sum(
            record["resolution_kind"]
            in {
                "VISIBLE_SOURCE_ROLE_CORROBORATED_BY_COMPONENTS",
                "VISIBLE_TRAILING_TOTAL_CORROBORATED_BY_COMPONENTS",
            }
            for record in resolved
        ),
        "unresolved_coverage_occurrence_count": sum(
            record["disposition"].startswith("UNRESOLVED")
            or record["disposition"].startswith("UNBOUND")
            for record in coverage_receipt
        ),
    }


def _validate_resolution_record(record: Any) -> None:
    if (
        type(record) is not dict
        or set(record) != {"component_roles", "resolution_kind", "role", "source", "values"}
        or type(record["role"]) is not str
        or not record["role"]
        or type(record["component_roles"]) is not list
        or len(record["component_roles"]) != len(set(record["component_roles"]))
        or any(type(role) is not str or not role for role in record["component_roles"])
        or type(record["resolution_kind"]) is not str
        or not record["resolution_kind"]
        or type(record["values"]) is not list
        or not record["values"]
    ):
        raise _error("scoped hierarchical resolved record drifted")
    source = record["source"]
    derived = record["resolution_kind"].startswith("DERIVED_EXACT")
    if (source is None) is not derived or (
        source is not None
        and (
            type(source) is not dict
            or set(source) != {"kind", "record"}
            or source["kind"] not in {"ROLE_ROW", "TRAILING_VALUE_ROW"}
            or type(source["record"]) is not dict
            or (
                source["kind"] == "ROLE_ROW"
                and source["record"].get("status") != "VISIBLE_VALUE_LANES_BOUND"
            )
            or (
                source["kind"] == "TRAILING_VALUE_ROW"
                and source["record"].get("status") != "COMPLETE_VISIBLE_TRAILING_VALUE_ROW"
            )
        )
    ):
        raise _error("scoped hierarchical resolved source authority drifted")
    source_values = source["record"].get("values") if source is not None else None
    for expected_lane, value in enumerate(record["values"]):
        if (
            type(value) is not dict
            or set(value) != {"column_ordinal", "number", "source_sample_ids"}
            or value["column_ordinal"] != expected_lane
            or type(value["number"]) is not dict
            or set(value["number"]) != {"coefficient", "percentage_mark_present", "scale"}
            or type(value["number"]["coefficient"]) is not int
            or type(value["number"]["percentage_mark_present"]) is not bool
            or type(value["number"]["scale"]) is not int
            or value["number"]["scale"] < 0
            or type(value["source_sample_ids"]) is not list
            or not value["source_sample_ids"]
            or len(value["source_sample_ids"]) != len(set(value["source_sample_ids"]))
            or any(type(item) is not str or not item for item in value["source_sample_ids"])
            or (
                source_values is not None
                and (
                    expected_lane >= len(source_values)
                    or value["source_sample_ids"] != [source_values[expected_lane].get("sample_id")]
                )
            )
        ):
            raise _error("scoped hierarchical resolved numeric lane drifted")
    if source_values is not None and len(source_values) != len(record["values"]):
        raise _error("scoped hierarchical resolved source lane axis differs")


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
        or type(value["occurrence_axis_id"]) is not str
        or not value["occurrence_axis_id"].startswith("aforav2:axis:")
        or type(value["resolved_roles"]) is not list
        or len(value["resolved_roles"]) > _MAX_RESOLVED_ROLES
        or type(value["coverage_receipt"]) is not list
        or len(value["coverage_receipt"]) > _MAX_COVERAGE_RECORDS
        or type(value["coextensive_structural_numeric_evidence"]) is not list
        or len(value["coextensive_structural_numeric_evidence"]) > _MAX_COVERAGE_RECORDS
        or not same_typed_json_v1(value["dependency_content_refs"], _dependency_refs())
        or type(value["role_occurrences"]) is not list
        or type(value["authenticated_existing_dash_evidence"]) is not list
        or type(value["occurrence_axis_binding"]) is not dict
        or set(value["occurrence_axis_binding"])
        != {
            "dependency_content_refs",
            "occurrence_axis_id",
            "topology_candidates_id",
            "topology_scan_id",
        }
        or value["occurrence_axis_binding"]["occurrence_axis_id"] != value["occurrence_axis_id"]
        or type(value["occurrence_axis_binding"]["dependency_content_refs"]) is not dict
        or (
            value["occurrence_axis_binding"]["topology_candidates_id"] is not None
            and (
                type(value["occurrence_axis_binding"]["topology_candidates_id"]) is not str
                or not value["occurrence_axis_binding"]["topology_candidates_id"].startswith(
                    "aftcv2:result:"
                )
            )
        )
        or type(value["occurrence_axis_binding"]["topology_scan_id"]) is not str
        or type(value["equations"]) is not dict
        or set(value["equations"]) != {"global", "local"}
        or type(value["unresolved_reasons"]) is not list
        or len(value["equations"].get("global", [])) > _MAX_EQUATIONS
        or len(value["equations"].get("local", [])) > _MAX_COVERAGE_RECORDS
        or any(type(reason) is not str or not reason for reason in value["unresolved_reasons"])
        or len(value["unresolved_reasons"]) != len(set(value["unresolved_reasons"]))
        or value["status"]
        not in {
            "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO",
            "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO",
        }
    ):
        raise _error("scoped hierarchical result contract drifted")
    roles = [record.get("role") for record in value["resolved_roles"]]
    if any(type(role) is not str or not role for role in roles) or len(roles) != len(set(roles)):
        raise _error("scoped hierarchical resolved role axis repeats or drifted")
    for record in value["resolved_roles"]:
        _validate_resolution_record(record)
    for equation in value["equations"]["global"]:
        if (
            type(equation) is not dict
            or set(equation)
            != {
                "component_roles_present",
                "residual_evidence",
                "result_role",
                "selected_trailing_candidate_ordinal",
                "status",
                "trailing_candidate_evidence",
            }
            or type(equation["component_roles_present"]) is not list
            or type(equation["residual_evidence"]) is not list
            or type(equation["result_role"]) is not str
            or not equation["result_role"]
            or (
                equation["selected_trailing_candidate_ordinal"] is not None
                and (
                    type(equation["selected_trailing_candidate_ordinal"]) is not int
                    or equation["selected_trailing_candidate_ordinal"] < 0
                )
            )
            or type(equation["status"]) is not str
            or not equation["status"]
            or type(equation["trailing_candidate_evidence"]) is not list
        ):
            raise _error("scoped hierarchical global equation record drifted")
        trailing_ordinals = []
        selected_ordinals = []
        for candidate in equation["trailing_candidate_evidence"]:
            if (
                type(candidate) is not dict
                or set(candidate) != {"candidate_ordinal", "sample_ids", "source_record", "status"}
                or type(candidate["candidate_ordinal"]) is not int
                or candidate["candidate_ordinal"] < 0
                or type(candidate["sample_ids"]) is not list
                or not candidate["sample_ids"]
                or len(candidate["sample_ids"]) != len(set(candidate["sample_ids"]))
                or any(type(item) is not str or not item for item in candidate["sample_ids"])
                or type(candidate["source_record"]) is not dict
                or candidate["source_record"].get("candidate_ordinal")
                != candidate["candidate_ordinal"]
                or candidate["sample_ids"]
                != [item.get("sample_id") for item in candidate["source_record"].get("values", [])]
                or candidate["status"]
                not in {
                    "SELECTED_VISIBLE_TRAILING_ROOT_SOURCE",
                    "UNRESOLVED_PARTIAL_TRAILING_NUMERIC_CHALLENGER",
                    "UNRESOLVED_UNSELECTED_COMPLETE_TRAILING_NUMERIC_CHALLENGER",
                }
            ):
                raise _error("scoped hierarchical trailing challenger evidence drifted")
            trailing_ordinals.append(candidate["candidate_ordinal"])
            if candidate["status"] == "SELECTED_VISIBLE_TRAILING_ROOT_SOURCE":
                selected_ordinals.append(candidate["candidate_ordinal"])
        if trailing_ordinals != sorted(set(trailing_ordinals)) or selected_ordinals != (
            []
            if equation["selected_trailing_candidate_ordinal"] is None
            else [equation["selected_trailing_candidate_ordinal"]]
        ):
            raise _error("scoped hierarchical selected trailing candidate axis drifted")
        for evidence in equation["residual_evidence"]:
            if (
                type(evidence) is not dict
                or set(evidence)
                != {
                    "candidate_ordinal",
                    "component_roles",
                    "convention",
                    "lanes",
                    "result_role",
                }
                or evidence["result_role"] != equation["result_role"]
                or evidence["convention"] != "PRINTED_RESULT_MINUS_EXHAUSTIVE_COMPONENT_SUM"
                or (
                    evidence["candidate_ordinal"] is not None
                    and (
                        type(evidence["candidate_ordinal"]) is not int
                        or evidence["candidate_ordinal"] < 0
                    )
                )
                or type(evidence["component_roles"]) is not list
                or not evidence["component_roles"]
                or type(evidence["lanes"]) is not list
                or not evidence["lanes"]
            ):
                raise _error("scoped hierarchical typed residual evidence drifted")
            for expected_lane, lane in enumerate(evidence["lanes"]):
                if (
                    type(lane) is not dict
                    or set(lane)
                    != {
                        "column_ordinal",
                        "component_source_sample_ids",
                        "component_sum_number",
                        "printed_result_number",
                        "printed_result_source_sample_ids",
                        "residual_number",
                    }
                    or lane["column_ordinal"] != expected_lane
                    or any(
                        type(number) is not dict
                        or set(number) != {"coefficient", "percentage_mark_present", "scale"}
                        or type(number["coefficient"]) is not int
                        or type(number["percentage_mark_present"]) is not bool
                        or type(number["scale"]) is not int
                        or number["scale"] < 0
                        for number in (
                            lane["component_sum_number"],
                            lane["printed_result_number"],
                            lane["residual_number"],
                        )
                    )
                    or any(
                        type(samples) is not list
                        or not samples
                        or len(samples) != len(set(samples))
                        or any(type(sample) is not str or not sample for sample in samples)
                        for samples in (
                            lane["component_source_sample_ids"],
                            lane["printed_result_source_sample_ids"],
                        )
                    )
                ):
                    raise _error("scoped hierarchical residual lane evidence drifted")
    for equation in value["equations"]["local"]:
        if (
            type(equation) is not dict
            or set(equation)
            != {
                "component_roles_present",
                "result_occurrence_id",
                "result_role",
                "status",
            }
            or type(equation["component_roles_present"]) is not list
            or type(equation["result_occurrence_id"]) is not str
            or not equation["result_occurrence_id"]
            or type(equation["result_role"]) is not str
            or not equation["result_role"]
            or type(equation["status"]) is not str
            or not equation["status"]
        ):
            raise _error("scoped hierarchical local equation record drifted")
    occurrence_ids = {record.get("occurrence_id") for record in value["role_occurrences"]}
    coverage_ids = [record.get("coverage_id") for record in value["coverage_receipt"]]
    role_coverage_occurrence_ids = [
        record.get("occurrence_id")
        for record in value["coverage_receipt"]
        if type(record) is dict
        and record.get("row_kind") in {"COEXTENSIVE_PRECEDING_NUMERIC_SOURCE", "ROLE_ROW"}
    ]
    trailing_coverage_ordinals = [
        record.get("candidate_ordinal")
        for record in value["coverage_receipt"]
        if type(record) is dict and record.get("row_kind") == "TRAILING_VALUE_ROW"
    ]
    allowed_dispositions = {
        "GLOBAL_HIERARCHY_SOURCE_OCCURRENCE",
        "LOCAL_EXHAUSTIVE_COMPONENT_OCCURRENCE",
        "LOCAL_SUBTOTAL_RESULT_OCCURRENCE",
        "NONADDITIVE_VISIBLE_SOURCE_ROLE",
        "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_ALREADY_OWNED",
        "UNBOUND_VISIBLE_ACCOUNTING_OCCURRENCE",
        "UNRESOLVED_PARTIAL_ROLE_NUMERIC_OCCURRENCE",
        "UNRESOLVED_HIERARCHY_SOURCE_OCCURRENCE",
        "SELECTED_VISIBLE_TRAILING_ROOT_SOURCE",
        "UNRESOLVED_PARTIAL_TRAILING_NUMERIC_CHALLENGER",
        "UNRESOLVED_UNSELECTED_COMPLETE_TRAILING_NUMERIC_CHALLENGER",
        "UNRESOLVED_UNCLAIMED_TRAILING_NUMERIC_CHALLENGER",
    }
    if (
        None in occurrence_ids
        or len(coverage_ids) != len(set(coverage_ids))
        or len(role_coverage_occurrence_ids) != len(set(role_coverage_occurrence_ids))
        or len(trailing_coverage_ordinals) != len(set(trailing_coverage_ordinals))
        or any(
            type(record) is not dict
            or set(record) != _COVERAGE_FIELDS
            or type(record["coverage_id"]) is not str
            or not record["coverage_id"]
            or record["disposition"] not in allowed_dispositions
            or type(record["sample_ids"]) is not list
            or not record["sample_ids"]
            or len(record["sample_ids"]) != len(set(record["sample_ids"]))
            or any(type(item) is not str or not item for item in record["sample_ids"])
            or type(record["source_record"]) is not dict
            or record["row_kind"]
            not in {
                "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE",
                "ROLE_ROW",
                "TRAILING_VALUE_ROW",
            }
            or (
                record["row_kind"] == "ROLE_ROW"
                and (
                    record["occurrence_id"] not in occurrence_ids
                    or record["candidate_ordinal"] is not None
                    or type(record["role"]) is not str
                    or not record["role"]
                    or record["source_record"].get("role") != record["role"]
                    or record["source_record"].get("label_match", {}).get("occurrence_id")
                    != record["occurrence_id"]
                )
            )
            or (
                record["row_kind"] == "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE"
                and (
                    record["occurrence_id"] not in occurrence_ids
                    or record["candidate_ordinal"] is not None
                    or type(record["role"]) is not str
                    or not record["role"]
                    or record["source_record"].get("role") != record["role"]
                    or record["source_record"].get("label_match", {}).get("occurrence_id")
                    != record["occurrence_id"]
                    or record["disposition"] != "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_ALREADY_OWNED"
                )
            )
            or (
                record["row_kind"] == "TRAILING_VALUE_ROW"
                and (
                    record["occurrence_id"] is not None
                    or record["role"] is not None
                    or type(record["candidate_ordinal"]) is not int
                    or record["candidate_ordinal"] < 0
                    or record["source_record"].get("candidate_ordinal")
                    != record["candidate_ordinal"]
                )
            )
            or record["sample_ids"]
            != [item.get("sample_id") for item in record["source_record"].get("values", [])]
            for record in value["coverage_receipt"]
        )
    ):
        raise _error("scoped hierarchical visible occurrence coverage receipt drifted")
    coextensive_receipts = {
        record["occurrence_id"]: record
        for record in value["coverage_receipt"]
        if record["row_kind"] == "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE"
    }
    role_receipts = {
        record["occurrence_id"]: record
        for record in value["coverage_receipt"]
        if record["row_kind"] == "ROLE_ROW"
    }
    occurrence_by_id = {
        record.get("occurrence_id"): record
        for record in value["role_occurrences"]
        if type(record) is dict and type(record.get("occurrence_id")) is str
    }
    coextensive_projected_ids: list[str] = []
    coextensive_sample_ids: list[str] = []
    owned_coextensive_ids: list[str] = []
    for evidence in value["coextensive_structural_numeric_evidence"]:
        if type(evidence) is not dict:
            raise _error("scoped hierarchical coextensive source receipt drifted")
        status = evidence.get("status")
        is_owned = status == _COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_STATUS
        is_ambiguous = status == _COEXTENSIVE_PRECEDING_NUMERIC_AMBIGUITY_STATUS
        projected_id = evidence.get("projected_occurrence_id")
        owner_id = evidence.get("owner_occurrence_id")
        projected = occurrence_by_id.get(projected_id)
        owner = occurrence_by_id.get(owner_id)
        component_ids = evidence.get("owner_component_occurrence_ids")
        source_record = evidence.get("source_record")
        source_values = source_record.get("values") if type(source_record) is dict else None
        source_label = source_record.get("label_match") if type(source_record) is dict else None
        source_sample_ids = evidence.get("source_sample_ids")
        expected_receipt = (
            coextensive_receipts.get(projected_id) if is_owned else role_receipts.get(projected_id)
        )
        if (
            set(evidence) != _COEXTENSIVE_STRUCTURAL_NUMERIC_FIELDS
            or not (is_owned or is_ambiguous)
            or type(projected_id) is not str
            or not projected_id
            or type(evidence.get("projected_role")) is not str
            or not evidence["projected_role"]
            or type(owner_id) is not str
            or not owner_id
            or type(evidence.get("owner_role")) is not str
            or not evidence["owner_role"]
            or type(projected) is not dict
            or projected.get("role_kind") != "STRUCTURAL_GROUP"
            or projected.get("role") != evidence["projected_role"]
            or projected.get("has_bound_value_row") is not is_ambiguous
            or type(owner) is not dict
            or owner.get("role_kind") != "STRUCTURAL_GROUP"
            or owner.get("role") != evidence["owner_role"]
            or type(component_ids) is not list
            or len(component_ids) < 2
            or any(
                type(component_id) is not str or not component_id for component_id in component_ids
            )
            or len(component_ids) != len(set(component_ids))
            or any(
                component_id not in occurrence_by_id
                or occurrence_by_id[component_id].get("role_kind") != "ADDITIVE_CHILD"
                or occurrence_by_id[component_id].get("scope_owner_occurrence_id") != owner_id
                for component_id in component_ids
            )
            or type(source_record) is not dict
            or source_record.get("status") != "VISIBLE_VALUE_LANES_BOUND"
            or source_record.get("role") != evidence["projected_role"]
            or type(source_label) is not dict
            or source_label.get("occurrence_id") != projected_id
            or type(source_values) is not list
            or not source_values
            or any(type(source_value) is not dict for source_value in source_values)
            or type(source_sample_ids) is not list
            or not source_sample_ids
            or any(type(sample_id) is not str or not sample_id for sample_id in source_sample_ids)
            or len(source_sample_ids) != len(set(source_sample_ids))
            or source_sample_ids
            != [source_value.get("sample_id") for source_value in source_values]
            or type(expected_receipt) is not dict
            or expected_receipt["role"] != evidence["projected_role"]
            or expected_receipt["sample_ids"] != source_sample_ids
            or not same_typed_json_v1(expected_receipt["source_record"], source_record)
            or (
                is_ambiguous
                and f"{_COEXTENSIVE_PRECEDING_NUMERIC_AMBIGUITY_STATUS}:{projected_id}"
                not in value["unresolved_reasons"]
            )
        ):
            raise _error("scoped hierarchical coextensive source receipt drifted")
        coextensive_projected_ids.append(projected_id)
        coextensive_sample_ids.extend(source_sample_ids)
        if is_owned:
            owned_coextensive_ids.append(projected_id)
    if (
        len(coextensive_projected_ids) != len(set(coextensive_projected_ids))
        or len(coextensive_sample_ids) != len(set(coextensive_sample_ids))
        or set(coextensive_receipts) != set(owned_coextensive_ids)
    ):
        raise _error("scoped hierarchical coextensive source receipt drifted")
    trailing_evidence = {
        candidate["candidate_ordinal"]: candidate["status"]
        for equation in value["equations"]["global"]
        for candidate in equation["trailing_candidate_evidence"]
    }
    trailing_receipts = {
        record["candidate_ordinal"]: record["disposition"]
        for record in value["coverage_receipt"]
        if record["row_kind"] == "TRAILING_VALUE_ROW"
    }
    if (
        any(
            ordinal not in trailing_receipts or trailing_receipts[ordinal] != status
            for ordinal, status in trailing_evidence.items()
        )
        or any(
            ordinal not in trailing_evidence
            and disposition != "UNRESOLVED_UNCLAIMED_TRAILING_NUMERIC_CHALLENGER"
            for ordinal, disposition in trailing_receipts.items()
        )
        or (not value["unresolved_reasons"])
        is not (value["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO")
    ):
        raise _error("scoped hierarchy status or trailing coverage binding drifted")
    if not same_typed_json_v1(
        value["metrics"],
        _metrics(
            value["resolved_roles"],
            value["equations"]["global"],
            value["equations"]["local"],
            value["coverage_receipt"],
            value["unresolved_reasons"],
        ),
    ):
        raise _error("scoped hierarchical metrics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("closure_id")
    if identity != "ashtcv2:closure:" + canonical_json_sha256_v1(material):
        raise _error("scoped hierarchical closure identity drifted")
    return canonical_clone_v1(value)


def _build(
    occurrence_axis: Any,
    family_topology_spec: Any,
    hierarchy_spec: Any,
) -> dict[str, Any]:
    try:
        axis = occurrence_v2._validate_result(occurrence_axis)
    except occurrence_v2.AccountingFamilyOccurrenceRowAxisV2Error as exc:
        raise _error("scoped hierarchical occurrence row-axis validation failed") from exc
    spec = _spec(hierarchy_spec, family_topology_spec)
    if axis["family_id"] != spec["family_id"]:
        raise _error("scoped hierarchy family differs from its occurrence axis")
    row_axis = axis["row_axis"]
    reasons = list(axis["unresolved_reasons"])
    numeric_rows = [row for row in row_axis["rows"] if row["values"]]
    valued_rows = [row for row in row_axis["rows"] if row["status"] == "VISIBLE_VALUE_LANES_BOUND"]
    if axis["status"] != (
        "OCCURRENCE_ROW_AXIS_BOUND_WITH_AUTHENTICATED_EXISTING_DASHES_PROPOSAL_ONLY"
    ):
        reasons.append("VISIBLE_ROLE_OCCURRENCE_ROW_LANES_NOT_COMPLETE")
    aggregate_roles = set(spec["repeated_role_policy"]["aggregate_roles"])
    local_records = []
    local_roles = set(spec["repeated_role_policy"]["local_subtotal_roles"])
    locally_valid_results: set[str] = set()
    locally_authorized_component_scopes: set[str] = set()
    locally_covered_components: set[str] = set()
    for equation in spec["equations"]:
        if equation["result_role"] in local_roles:
            (
                records,
                valid_results,
                authorized_component_scopes,
                covered_components,
                local_reasons,
            ) = _local_equations(equation, row_axis["rows"], axis["role_occurrences"])
            local_records.extend(records)
            locally_valid_results.update(valid_results)
            locally_authorized_component_scopes.update(authorized_component_scopes)
            locally_covered_components.update(covered_components)
            reasons.extend(local_reasons)
    resolved, _source_occurrences, repeated_reasons = _aggregate_source_roles(
        valued_rows,
        aggregate_roles,
        local_roles,
        locally_valid_results,
        locally_authorized_component_scopes,
    )
    reasons.extend(repeated_reasons)
    global_records = []
    for equation in spec["equations"]:
        record, equation_reasons = _select_global_equation(
            equation,
            resolved,
            row_axis["trailing_value_rows"],
        )
        global_records.append(record)
        reasons.extend(equation_reasons)
    equation_roles = {
        role
        for equation in spec["equations"]
        for role in {
            equation["result_role"],
            *equation["visible_result_roles"],
            *(
                role
                for alternative in equation["component_role_alternatives"]
                for role in alternative["component_roles"]
            ),
        }
    }
    equation_component_roles = {
        role
        for equation in spec["equations"]
        for alternative in equation["component_role_alternatives"]
        for role in alternative["component_roles"]
    }
    selected_component_use_count: dict[str, int] = {}
    for equation in global_records:
        for role in equation["component_roles_present"]:
            selected_component_use_count[role] = selected_component_use_count.get(role, 0) + 1
    accounting_component_roles = {
        role
        for role in equation_component_roles & ({*resolved, *(row["role"] for row in numeric_rows)})
        if spec["role_kind_by_role"].get(role) != "NONADDITIVE_CHILD"
    }
    invalid_component_use_roles = {
        role
        for role in accounting_component_roles
        if selected_component_use_count.get(role, 0) != 1
    }
    reasons.extend(
        f"ACCOUNTING_COMPONENT_ROLE_USE_COUNT_NOT_ONE:{role}:"
        f"{selected_component_use_count.get(role, 0)}"
        for role in sorted(invalid_component_use_roles)
    )
    trailing_disposition_by_ordinal: dict[int, str] = {}
    for equation in global_records:
        for candidate in equation["trailing_candidate_evidence"]:
            ordinal = candidate["candidate_ordinal"]
            if ordinal in trailing_disposition_by_ordinal:
                raise _error("more than one equation claimed one trailing numeric candidate")
            trailing_disposition_by_ordinal[ordinal] = candidate["status"]
    coverage_receipt = []
    coverage_occurrences: set[str] = set()
    for row in numeric_rows:
        occurrence_id = row["label_match"].get("occurrence_id")
        if type(occurrence_id) is not str or occurrence_id in coverage_occurrences:
            raise _error("valued occurrence coverage axis repeats or drifted")
        coverage_occurrences.add(occurrence_id)
        role = row["role"]
        role_kind = spec["role_kind_by_role"].get(role)
        if row["status"] != "VISIBLE_VALUE_LANES_BOUND":
            disposition = "UNRESOLVED_PARTIAL_ROLE_NUMERIC_OCCURRENCE"
            reasons.append(f"PARTIAL_VISIBLE_ACCOUNTING_ROW:{role}:{occurrence_id}")
        elif role_kind == "NONADDITIVE_CHILD":
            disposition = "NONADDITIVE_VISIBLE_SOURCE_ROLE"
        elif occurrence_id in locally_valid_results:
            disposition = "LOCAL_SUBTOTAL_RESULT_OCCURRENCE"
        elif occurrence_id in locally_covered_components:
            disposition = "LOCAL_EXHAUSTIVE_COMPONENT_OCCURRENCE"
        elif role not in equation_roles:
            disposition = "UNBOUND_VISIBLE_ACCOUNTING_OCCURRENCE"
            reasons.append(f"UNBOUND_VISIBLE_ACCOUNTING_ROW:{role}:{occurrence_id}")
        elif role in resolved and role not in invalid_component_use_roles:
            disposition = "GLOBAL_HIERARCHY_SOURCE_OCCURRENCE"
        else:
            disposition = "UNRESOLVED_HIERARCHY_SOURCE_OCCURRENCE"
            reasons.append(f"VISIBLE_ACCOUNTING_ROW_NOT_RESOLVED:{role}:{occurrence_id}")
        coverage_receipt.append(
            {
                "candidate_ordinal": None,
                "coverage_id": "ashtcv2:coverage:role:" + occurrence_id,
                "disposition": disposition,
                "occurrence_id": occurrence_id,
                "role": role,
                "row_kind": "ROLE_ROW",
                "sample_ids": [value["sample_id"] for value in row["values"]],
                "source_record": canonical_clone_v1(row),
            }
        )
    for evidence in axis["coextensive_structural_numeric_evidence"]:
        if evidence["status"] != "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_ALREADY_OWNED":
            continue
        occurrence_id = evidence["projected_occurrence_id"]
        if occurrence_id in coverage_occurrences:
            raise _error("coextensive numeric source repeats one valued occurrence receipt")
        coverage_occurrences.add(occurrence_id)
        coverage_receipt.append(
            {
                "candidate_ordinal": None,
                "coverage_id": "ashtcv2:coverage:coextensive:" + occurrence_id,
                "disposition": "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_ALREADY_OWNED",
                "occurrence_id": occurrence_id,
                "role": evidence["projected_role"],
                "row_kind": "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE",
                "sample_ids": canonical_clone_v1(evidence["source_sample_ids"]),
                "source_record": canonical_clone_v1(evidence["source_record"]),
            }
        )
    trailing_ordinals: set[int] = set()
    for trailing in row_axis["trailing_value_rows"]:
        ordinal = trailing["candidate_ordinal"]
        if ordinal in trailing_ordinals:
            raise _error("trailing numeric coverage axis repeats")
        trailing_ordinals.add(ordinal)
        disposition = trailing_disposition_by_ordinal.get(
            ordinal, "UNRESOLVED_UNCLAIMED_TRAILING_NUMERIC_CHALLENGER"
        )
        if disposition == "UNRESOLVED_UNCLAIMED_TRAILING_NUMERIC_CHALLENGER":
            reasons.append(f"UNCLAIMED_TRAILING_NUMERIC_ROW:{ordinal}")
        coverage_receipt.append(
            {
                "candidate_ordinal": ordinal,
                "coverage_id": f"ashtcv2:coverage:trailing:{ordinal}",
                "disposition": disposition,
                "occurrence_id": None,
                "role": None,
                "row_kind": "TRAILING_VALUE_ROW",
                "sample_ids": [value["sample_id"] for value in trailing["values"]],
                "source_record": canonical_clone_v1(trailing),
            }
        )
    reasons = list(dict.fromkeys(reasons))
    resolved_axis = [canonical_clone_v1(record) for record in resolved.values()]
    equation_axis = {"global": global_records, "local": local_records}
    material = {
        "authenticated_existing_dash_evidence": canonical_clone_v1(
            axis["authenticated_existing_dash_evidence"]
        ),
        "claim_boundary": CLAIM_BOUNDARY,
        "coextensive_structural_numeric_evidence": canonical_clone_v1(
            axis["coextensive_structural_numeric_evidence"]
        ),
        "coverage_receipt": coverage_receipt,
        "dependency_content_refs": _dependency_refs(),
        "equations": equation_axis,
        "family_id": spec["family_id"],
        "format_version": FORMAT_VERSION,
        "metrics": _metrics(
            resolved_axis, global_records, local_records, coverage_receipt, reasons
        ),
        "occurrence_axis_binding": {
            "dependency_content_refs": canonical_clone_v1(axis["dependency_content_refs"]),
            "occurrence_axis_id": axis["occurrence_axis_id"],
            "topology_candidates_id": axis["topology_candidates_id"],
            "topology_scan_id": axis["topology_scan_id"],
        },
        "occurrence_axis_id": axis["occurrence_axis_id"],
        "resolved_roles": resolved_axis,
        "role_occurrences": canonical_clone_v1(axis["role_occurrences"]),
        "row_axis_id": row_axis["row_axis_id"],
        "safety": canonical_clone_v1(_SAFETY),
        "status": (
            "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
            if not reasons
            else "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
        ),
        "unresolved_reasons": reasons,
    }
    return _validate_result(
        {
            **material,
            "closure_id": "ashtcv2:closure:" + canonical_json_sha256_v1(material),
        }
    )


def build_accounting_scoped_hierarchical_table_closure_v2(
    occurrence_axis: Any,
    family_topology_spec: Any,
    hierarchy_spec: Any,
) -> dict[str, Any]:
    """Close exact local subtotals and declared disjoint repeated roles."""

    return _build(occurrence_axis, family_topology_spec, hierarchy_spec)


def _build_accounting_scoped_hierarchical_table_closure_from_authenticated_axis_v2(
    occurrence_axis: Any,
    family_topology_spec: Any,
    hierarchy_spec: Any,
) -> dict[str, Any]:
    return _build(occurrence_axis, family_topology_spec, hierarchy_spec)


def validate_accounting_scoped_hierarchical_table_closure_replay_v2(
    value: Any,
    occurrence_axis: Any,
    family_topology_spec: Any,
    hierarchy_spec: Any,
) -> dict[str, Any]:
    """Rebuild exact local/global exhaustive equations from the occurrence axis."""

    persisted = _validate_result(value)
    expected = build_accounting_scoped_hierarchical_table_closure_v2(
        occurrence_axis, family_topology_spec, hierarchy_spec
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("scoped hierarchical closure does not replay exactly")
    return persisted
