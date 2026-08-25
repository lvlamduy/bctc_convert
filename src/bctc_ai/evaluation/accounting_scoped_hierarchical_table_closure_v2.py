"""Fail-closed accounting closure for repeated, locally scoped role rows.

The sealed hierarchical closure V1 intentionally requires one row per role.
This opt-in primitive handles a different source structure: the same semantic
child may repeat under the nearest repeated structural parent.  Local printed
subtotals are checked exactly or by the V2 integer display-unit rounding
receipt only against children bound to that exact parent
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
    "SPEC_FORMAT_VERSION_V2",
    "AccountingScopedHierarchicalTableClosureV2Error",
    "build_accounting_scoped_hierarchical_table_closure_v2",
    "validate_accounting_scoped_hierarchical_table_closure_replay_v2",
]


FORMAT_VERSION = "ACCOUNTING_SCOPED_HIERARCHICAL_TABLE_CLOSURE_V2"
SPEC_FORMAT_VERSION = "ACCOUNTING_SCOPED_HIERARCHICAL_CLOSURE_SPEC_V1"
SPEC_FORMAT_VERSION_V2 = "ACCOUNTING_SCOPED_HIERARCHICAL_CLOSURE_SPEC_V2"
CLAIM_BOUNDARY = (
    "VISIBLE_COMPLETE_ROLE_OCCURRENCES_NEAREST_PARENT_LOCAL_SUBTOTAL_AND_"
    "DECLARED_DISJOINT_SCOPE_AGGREGATION_WITH_EXHAUSTIVE_COMPONENT_ALTERNATIVES_"
    "EXACT_OR_INTEGER_DISPLAY_UNIT_ROUNDING_CORROBORATION_PRESERVING_PRINTED_VALUES_"
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
    "visible_mismatch_over_declared_rounding_bound_is_veto": True,
    "within_bound_rounding_never_changes_printed_source_digits": True,
}
_SPEC_FIELDS_V1 = {
    "equations",
    "family_id",
    "format_version",
    "repeated_role_policy",
}
_SPEC_FIELDS_V2 = {*_SPEC_FIELDS_V1, "source_role_policy"}
_REPEAT_POLICY_FIELDS = {"aggregate_roles", "local_subtotal_roles"}
_SOURCE_ROLE_POLICY_FIELDS = {
    "one_edit_role_or_scope_match_policy",
    "source_only_veto_roles",
}
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
_PRINTED_SOURCE_CELLS_KEY = "_printed_source_cells_by_lane"
_VISIBLE_SOURCE_POLICIES = {
    "ALLOW_ONLY_WHEN_NO_DECLARED_COMPONENT_ROLE_VISIBLE",
    "REQUIRE_EXHAUSTIVE_COMPONENTS",
}
_RESULT_FIELDS = {
    "authenticated_extreme_margin_furniture_evidence",
    "authenticated_existing_dash_evidence",
    "claim_boundary",
    "closure_id",
    "coextensive_structural_numeric_evidence",
    "coverage_receipt",
    "dependency_content_refs",
    "equations",
    "family_id",
    "format_version",
    "internal_unassigned_numeric_clusters",
    "metrics",
    "numeric_sample_universe",
    "occurrence_axis_binding",
    "occurrence_axis_id",
    "one_edit_exact_source_structural_proofs",
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
_EXTREME_MARGIN_FURNITURE_DISPOSITION = (
    "AUTHENTICATED_EXTREME_MARGIN_FURNITURE_EXCLUDED_FROM_ACCOUNTING_SOURCE"
)
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
_GLOBAL_EQUATION_FIELDS_V1 = {
    "component_roles_present",
    "residual_evidence",
    "result_role",
    "selected_trailing_candidate_ordinal",
    "status",
    "trailing_candidate_evidence",
}
_GLOBAL_EQUATION_FIELDS_V2 = {
    *_GLOBAL_EQUATION_FIELDS_V1,
    "rounding_evidence",
    "visible_result_roles",
}
_LOCAL_EQUATION_FIELDS_V1 = {
    "component_roles_present",
    "result_occurrence_id",
    "result_role",
    "status",
}
_LOCAL_EQUATION_FIELDS_V2 = {
    *_LOCAL_EQUATION_FIELDS_V1,
    "residual_evidence",
    "rounding_evidence",
}
_LOCAL_EQUATION_FIELDS_V3 = {
    *_LOCAL_EQUATION_FIELDS_V2,
    "local_trailing_subgroup_subtotal_receipt",
}
_COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_STATUS = "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_ALREADY_OWNED"
_COEXTENSIVE_PRECEDING_NUMERIC_AMBIGUITY_STATUS = (
    "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_AMBIGUOUS_OWNERSHIP_VETO"
)
_UNLABELED_EXACT_SUBTOTAL_CORROBORATION = "UNLABELED_EXACT_SUBTOTAL_CORROBORATION"
_UNLABELED_AMBIGUOUS_SUBTOTAL_DISPOSITION = "UNRESOLVED_AMBIGUOUS_UNLABELED_SUBTOTAL"
_UNLABELED_SUBTOTAL_DISPOSITIONS = {
    _UNLABELED_AMBIGUOUS_SUBTOTAL_DISPOSITION,
    _UNLABELED_EXACT_SUBTOTAL_CORROBORATION,
}
_UNLABELED_EXACT_SUBTOTAL_TARGET_ROLES = {
    "INTERBANK_DEPOSIT_GROUP",
    "INTERBANK_LOAN_GROUP",
}
_SEALED_DEPOSIT_SUBGROUP_COMPONENT_ROLES = {
    "DEMAND_DEPOSIT_GROUP": [
        "DEMAND_DEPOSIT_VND",
        "DEMAND_DEPOSIT_FOREIGN_CURRENCY",
    ],
    "TERM_DEPOSIT_GROUP": [
        "TERM_DEPOSIT_VND",
        "TERM_DEPOSIT_FOREIGN_CURRENCY",
    ],
}
_LOCAL_TRAILING_SUBGROUP_SUBTOTAL_CORROBORATION = "LOCAL_TRAILING_SUBGROUP_SUBTOTAL_CORROBORATION"
_LOCAL_TRAILING_SUBGROUP_TRUSTED_HIERARCHY_SPEC_SHA256 = (
    "5f7b7b082706d338d755d0d97332f8f7715556e34c12736752e508ebd6bacac5"
)
_LOCAL_TRAILING_SUBGROUP_TRUSTED_EQUATION_SPEC_SHA256 = (
    "e34e4ad6ba255b3cc713e74d7c401cbb060a3ae0139178e191c38bb28c8a56ef"
)
_LOCAL_TRAILING_SUBGROUP_TRUSTED_COMPONENT_ROLE_SETS = (
    ("INTERBANK_LOAN_VND", "INTERBANK_LOAN_FOREIGN_CURRENCY"),
    (
        "INTERBANK_LOAN_VND",
        "INTERBANK_LOAN_FOREIGN_CURRENCY",
        "INTERBANK_LOAN_PROVISION",
    ),
    (
        "INTERBANK_LOAN_VND",
        "INTERBANK_LOAN_FOREIGN_CURRENCY",
        "INTERBANK_LOAN_OTHER",
    ),
    (
        "INTERBANK_LOAN_VND",
        "INTERBANK_LOAN_FOREIGN_CURRENCY",
        "INTERBANK_LOAN_PROVISION",
        "INTERBANK_LOAN_OTHER",
    ),
    ("INTERBANK_LOAN_VND",),
    ("INTERBANK_LOAN_FOREIGN_CURRENCY",),
    ("INTERBANK_LOAN_VND", "INTERBANK_LOAN_PROVISION"),
    ("INTERBANK_LOAN_FOREIGN_CURRENCY", "INTERBANK_LOAN_PROVISION"),
    ("INTERBANK_LOAN_OTHER",),
    ("INTERBANK_LOAN_OTHER", "INTERBANK_LOAN_PROVISION"),
    ("INTERBANK_LOAN_VND", "INTERBANK_LOAN_OTHER"),
    ("INTERBANK_LOAN_FOREIGN_CURRENCY", "INTERBANK_LOAN_OTHER"),
    (
        "INTERBANK_LOAN_VND",
        "INTERBANK_LOAN_PROVISION",
        "INTERBANK_LOAN_OTHER",
    ),
    (
        "INTERBANK_LOAN_FOREIGN_CURRENCY",
        "INTERBANK_LOAN_PROVISION",
        "INTERBANK_LOAN_OTHER",
    ),
)
_LOCAL_TRAILING_SUBGROUP_RECEIPT_FIELDS = {
    "applicable_alternative_ordinals",
    "applicable_alternative_spec_sha256s",
    "alternative_value_axes",
    "boundary_occurrence_id",
    "boundary_role",
    "candidate_ordinal",
    "component_occurrence_ids",
    "component_roles",
    "component_sample_ids",
    "configured_alternative_role_sets",
    "descendant_occurrence_ids",
    "equation_spec_sha256",
    "hierarchy_spec_sha256",
    "interval",
    "nonadditive_occurrence_ids",
    "nonadditive_sample_ids",
    "missing_column_ordinals",
    "numeric_sample_universe_sha256",
    "observed_column_ordinals",
    "parent_occurrence_id",
    "receipt_id",
    "role_occurrence_axis_sha256",
    "row_axis_id",
    "source_record_sha256",
    "source_cluster_id",
    "source_row_kind",
    "source_sample_ids",
    "selection_kind",
    "status",
    "target_occurrence_id",
    "target_role",
}
_LOCAL_TRAILING_SUBGROUP_INTERVAL_FIELDS = {
    "candidate_first_document_line_ordinal",
    "candidate_first_source_line_index",
    "candidate_last_document_line_ordinal",
    "candidate_last_source_line_index",
    "last_descendant_document_line_ordinal",
    "last_descendant_source_line_index",
    "page_sequence",
    "subgroup_stop_document_line_ordinal_exclusive",
    "subgroup_stop_source_line_index_exclusive",
    "target_document_line_ordinal",
    "target_source_line_index",
    "topology_region_stop_document_line_ordinal_exclusive",
    "topology_region_stop_source_line_index_exclusive",
}
_LOCAL_TRAILING_SUBGROUP_ALTERNATIVE_FIELDS = {
    "alternative_ordinal",
    "alternative_spec_sha256",
    "component_occurrence_ids",
    "component_roles",
    "component_sample_ids",
    "values",
}
_LOCAL_TRAILING_SUBGROUP_RECEIPT_STATUS = (
    "EXACT_VISIBLE_LANES_UNLABELED_SUBGROUP_SELECTOR_BOUND_TO_SEALED_INTERVAL"
)
_UNLABELED_SOURCE_SUBTOTAL_DISPOSITIONS = {
    *_UNLABELED_SUBTOTAL_DISPOSITIONS,
    _LOCAL_TRAILING_SUBGROUP_SUBTOTAL_CORROBORATION,
}


def _local_trailing_subgroup_trusted_equation_spec() -> dict[str, Any]:
    """Return the exact ordered Family-3 loan equation authorized for this projector."""

    alternatives = []
    for ordinal, roles in enumerate(_LOCAL_TRAILING_SUBGROUP_TRUSTED_COMPONENT_ROLE_SETS):
        alternatives.append(
            {
                "component_roles": list(roles),
                "coverage_policy": "EXHAUSTIVE_COMPONENT_SET",
                "derivation_policy": (
                    "ALLOW_DERIVATION_FROM_EXHAUSTIVE_VISIBLE_COMPONENTS"
                    if ordinal < 4
                    else "VISIBLE_RESULT_CORROBORATION_ONLY"
                ),
            }
        )
    return {
        "component_role_alternatives": alternatives,
        "application_policy": "REQUIRED_WHEN_ANY_DECLARED_ROLE_VISIBLE",
        "result_role": "INTERBANK_LOAN_GROUP",
        "trailing_result_policy": "IGNORE",
        "visible_source_policy": "ALLOW_ONLY_WHEN_NO_DECLARED_COMPONENT_ROLE_VISIBLE",
        "visible_result_roles": [
            "INTERBANK_LOAN_GROUP",
            "EXPLICIT_INTERBANK_LOAN_TOTAL",
        ],
        "shared_component_roles": ["INTERBANK_LOAN_PROVISION"],
    }


_MAX_EQUATIONS = 128
_MAX_COVERAGE_RECORDS = 16_384
_MAX_RESOLVED_ROLES = 4_096
_GLOBAL_EQUATION_STATUSES = {
    "AMBIGUOUS_EXACT_COMPONENT_OWNERSHIP_VETO",
    "AMBIGUOUS_ROUNDING_COMPONENT_OWNERSHIP_VETO",
    "DERIVED_EXACT_EXHAUSTIVE_COMPONENT_SUM",
    "EXHAUSTIVE_COMPONENT_ALTERNATIVES_DISAGREE_VETO",
    "NOT_APPLICABLE_NO_SOURCE_OR_EXHAUSTIVE_COMPONENT_SET",
    "REQUIRED_EQUATION_INCOMPLETE_COMPONENT_SET_VETO",
    "TRAILING_NUMERIC_CHALLENGER_VETO",
    "VISIBLE_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS",
    "VISIBLE_RESULT_INCOMPLETE_COMPONENT_SET_VETO",
    "VISIBLE_RESULT_MISMATCH_VETO",
    "VISIBLE_RESULT_REQUIRED_FOR_COMPONENT_ALTERNATIVE_VETO",
    "VISIBLE_RESULT_ROUNDING_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS",
    "VISIBLE_SOURCE_ONLY_NO_DECLARED_COMPONENT_VISIBLE",
    "VISIBLE_TRAILING_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS",
    "VISIBLE_TRAILING_RESULT_ROUNDING_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS",
}
_LOCAL_EQUATION_STATUSES = {
    "LOCAL_AMBIGUOUS_EXACT_COMPONENT_OWNERSHIP_VETO",
    "LOCAL_AMBIGUOUS_ROUNDING_COMPONENT_OWNERSHIP_VETO",
    "LOCAL_SINGLE_SCOPE_WITHOUT_VISIBLE_SUBTOTAL_DEFERRED_TO_EXHAUSTIVE_GLOBAL_EQUATION",
    "LOCAL_SUBTOTAL_RESULT_MISSING_OR_INCOMPLETE_VETO",
    "LOCAL_SUBTOTAL_RESULT_PARTIAL_VALUE_LANES_VETO",
    "LOCAL_VISIBLE_SOURCE_ONLY_NO_DECLARED_COMPONENT_VISIBLE",
    "LOCAL_VISIBLE_SUBTOTAL_CORROBORATED_BY_EXACT_SCOPED_COMPONENTS",
    "LOCAL_VISIBLE_SUBTOTAL_INCOMPLETE_COMPONENT_SET_VETO",
    "LOCAL_VISIBLE_SUBTOTAL_MISMATCH_VETO",
    "LOCAL_VISIBLE_SUBTOTAL_ROUNDING_CORROBORATED_BY_EXHAUSTIVE_SCOPED_COMPONENTS",
    "LOCAL_TRAILING_SUBTOTAL_CORROBORATED_BY_EXACT_SCOPED_COMPONENTS",
}
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEPENDENCIES = {
    "occurrence_row_axis_v2": {
        "path": "src/bctc_ai/evaluation/accounting_family_occurrence_row_axis_v2.py",
        "sha256": "6529650a9565c3a37516604e6e1c2d2921fa068d0f46c0e13dbadc1334c52da5",
        "size_bytes": 325_584,
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
    version = value.get("format_version") if type(value) is dict else None
    expected_fields = (
        _SPEC_FIELDS_V1
        if version == SPEC_FORMAT_VERSION
        else _SPEC_FIELDS_V2
        if version == SPEC_FORMAT_VERSION_V2
        else None
    )
    if (
        type(value) is not dict
        or expected_fields is None
        or set(value) != expected_fields
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
    source_role_policy = (
        canonical_clone_v1(value["source_role_policy"])
        if version == SPEC_FORMAT_VERSION_V2
        else {
            "one_edit_role_or_scope_match_policy": "ALLOW",
            "source_only_veto_roles": [],
        }
    )
    if (
        type(source_role_policy) is not dict
        or set(source_role_policy) != _SOURCE_ROLE_POLICY_FIELDS
        or source_role_policy["one_edit_role_or_scope_match_policy"] not in {"ALLOW", "VETO"}
        or (
            version == SPEC_FORMAT_VERSION_V2
            and source_role_policy["one_edit_role_or_scope_match_policy"] != "VETO"
        )
        or type(source_role_policy["source_only_veto_roles"]) is not list
        or source_role_policy["source_only_veto_roles"]
        != sorted(set(source_role_policy["source_only_veto_roles"]))
        or any(role not in child_roles for role in source_role_policy["source_only_veto_roles"])
    ):
        raise _error("scoped hierarchical source-role policy drifted")
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
        "format_version": version,
        "repeated_role_policy": canonical_clone_v1(repeat),
        "role_kind_by_role": {child["role"]: child["role_kind"] for child in topology["children"]},
        "source_role_policy": source_role_policy,
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


def _source_role_vetoes(
    rows: Sequence[Mapping[str, Any]],
    role_occurrences: Sequence[Mapping[str, Any]],
    source_role_policy: Mapping[str, Any],
    one_edit_exact_source_structural_proofs: Mapping[str, Any],
) -> tuple[set[str], set[str], list[str]]:
    """Separate typed source evidence that is ineligible for schema closure."""

    source_only_roles = set(source_role_policy["source_only_veto_roles"])
    veto_one_edit = source_role_policy["one_edit_role_or_scope_match_policy"] == "VETO"
    occurrence_by_id = {occurrence["occurrence_id"]: occurrence for occurrence in role_occurrences}
    bound_retrieval_occurrence_ids = {
        check["occurrence_id"]
        for check in one_edit_exact_source_structural_proofs["checks"]
        if check["match_scope"] == "EXPANDED_OCCURRENCE"
        and check["status"] in occurrence_v2._ONE_EDIT_AUTHORITY_BOUND_STATUSES  # noqa: SLF001
    }
    family_parent_is_bound = any(
        check["match_scope"] == "FAMILY_PARENT"
        and check["status"] in occurrence_v2._ONE_EDIT_AUTHORITY_BOUND_STATUSES  # noqa: SLF001
        for check in one_edit_exact_source_structural_proofs["checks"]
    )
    source_only_occurrences: set[str] = set()
    one_edit_occurrences: set[str] = set()
    reasons: list[str] = []
    for row in rows:
        if not row.get("values"):
            continue
        occurrence_id = row.get("label_match", {}).get("occurrence_id")
        occurrence = occurrence_by_id.get(occurrence_id)
        if type(occurrence_id) is not str or type(occurrence) is not dict:
            raise _error("schema-eligibility source row lost its exact occurrence")
        role = row["role"]
        scope_binding = occurrence.get("source_scope_binding")
        ambiguous_wrapped_label = (
            type(scope_binding) is dict
            and scope_binding.get("status") == occurrence_v2._AMBIGUOUS_WRAPPED_LABEL_STATUS  # noqa: SLF001
        )
        if role in source_only_roles or ambiguous_wrapped_label:
            source_only_occurrences.add(occurrence_id)
            reasons.append(
                (
                    "SOURCE_ONLY_AMBIGUOUS_TOUCHING_WRAPPED_LABEL"
                    if ambiguous_wrapped_label
                    else "SOURCE_ONLY_SCHEMA_INELIGIBLE_ROLE"
                )
                + f":{role}:{occurrence_id}"
            )
        label_one_edit_unbound = (
            str(row["label_match"].get("match_kind", "")).startswith("ONE_EDIT_")
            and occurrence["retrieval_occurrence_id"] not in bound_retrieval_occurrence_ids
        )
        scope_one_edit_unbound = str(occurrence["scope_owner_match_kind"]).startswith(
            "ONE_EDIT_"
        ) and (
            (occurrence["scope_owner_role"] is None and not family_parent_is_bound)
            or (
                occurrence["scope_owner_role"] is not None
                and occurrence_by_id[occurrence["scope_owner_occurrence_id"]][
                    "retrieval_occurrence_id"
                ]
                not in bound_retrieval_occurrence_ids
            )
        )
        if veto_one_edit and (label_one_edit_unbound or scope_one_edit_unbound):
            one_edit_occurrences.add(occurrence_id)
            reasons.append(f"ONE_EDIT_ROLE_OR_SCOPE_MATCH_SCHEMA_INELIGIBLE:{role}:{occurrence_id}")
    return source_only_occurrences, one_edit_occurrences, reasons


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
        _PRINTED_SOURCE_CELLS_KEY: [
            [
                {
                    "classification": value["parsed_token"]["classification"],
                    "number": _number(value),
                    "source_sample_id": value["sample_id"],
                }
            ]
            for value in values
        ],
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
        _PRINTED_SOURCE_CELLS_KEY: [
            [
                {
                    "classification": value["parsed_token"]["classification"],
                    "number": _number(value),
                    "source_sample_id": value["sample_id"],
                }
            ]
            for value in values
        ],
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


def _printed_source_cells_by_lane(
    records: Sequence[Mapping[str, Any]],
) -> list[list[dict[str, Any]]]:
    axes = [record.get(_PRINTED_SOURCE_CELLS_KEY) for record in records]
    if (
        not axes
        or any(type(axis) is not list for axis in axes)
        or any(len(axis) != len(axes[0]) for axis in axes)
    ):
        raise _error("rounding component precision provenance axis drifted")
    result = []
    for lane in range(len(axes[0])):
        cells = [canonical_clone_v1(cell) for axis in axes for cell in axis[lane]]
        sample_ids = [cell.get("source_sample_id") for cell in cells]
        if (
            not cells
            or any(
                type(cell) is not dict
                or set(cell) != {"classification", "number", "source_sample_id"}
                or cell["classification"]
                not in {
                    "DASH_ZERO",
                    "MIXED_GROUPED_INTEGER_CANDIDATE",
                    "NOISE_SUFFIXED_GROUPED_INTEGER_CANDIDATE",
                    "SIGNED_NUMBER",
                }
                or type(cell["number"]) is not dict
                for cell in cells
            )
            or any(type(sample_id) is not str or not sample_id for sample_id in sample_ids)
            or len(sample_ids) != len(set(sample_ids))
        ):
            raise _error("rounding component precision provenance repeats or drifted")
        result.append(cells)
    return result


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


def _exact_numeric_value_signature(values: Sequence[Mapping[str, Any]]) -> str:
    """Key exact displayed numbers without conflating their source provenance."""

    return canonical_json_sha256_v1(
        [
            {
                "column_ordinal": value["column_ordinal"],
                "number": canonical_clone_v1(value["number"]),
            }
            for value in values
        ]
    )


def _unique_maximum_component_coverage(
    alternatives: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    if not alternatives:
        return None
    maximum = max(len(item["component_roles"]) for item in alternatives)
    strongest = [item for item in alternatives if len(item["component_roles"]) == maximum]
    return strongest[0] if len(strongest) == 1 else None


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


def _rounding_assessment(
    *,
    result_role: str,
    printed: Mapping[str, Any],
    component: Mapping[str, Any],
    component_roles: Sequence[str],
) -> dict[str, Any] | None:
    """Test one exhaustive printed sum in integer display-unit space.

    Every ``SIGNED_NUMBER`` source sample is one independently rounded printed
    component.  An authenticated ``DASH_ZERO`` remains exact visible zero but
    contributes no half-unit uncertainty.  The separately printed signed-number
    result contributes the final half-unit, giving the exact rational bound
    ``2 * abs(residual) <= numeric_component_count + 1``.  No value is replaced
    by the component sum and no floating-point tolerance enters.
    """

    residuals = _residuals(printed["values"], component["values"])
    source = printed.get("source")
    if residuals is None or source is None:
        return None
    candidate_ordinal = (
        source["record"]["candidate_ordinal"] if source["kind"] == "TRAILING_VALUE_ROW" else None
    )
    printed_result_owner = {
        "candidate_ordinal": candidate_ordinal,
        "occurrence_id": (
            source["record"]["label_match"]["occurrence_id"]
            if source["kind"] == "ROLE_ROW"
            else None
        ),
        "role": source["record"]["role"] if source["kind"] == "ROLE_ROW" else None,
        "source_kind": source["kind"],
    }
    lanes = []
    component_precision_axis = component.get(_PRINTED_SOURCE_CELLS_KEY)
    printed_precision_axis = printed.get(_PRINTED_SOURCE_CELLS_KEY)
    if (
        type(component_precision_axis) is not list
        or len(component_precision_axis) != len(residuals)
        or type(printed_precision_axis) is not list
        or len(printed_precision_axis) != len(residuals)
    ):
        return None
    for (
        residual,
        printed_value,
        component_value,
        printed_component_cells,
        printed_result_cells,
    ) in zip(
        residuals,
        printed["values"],
        component["values"],
        component_precision_axis,
        printed_precision_axis,
        strict=True,
    ):
        printed_number = printed_value["number"]
        component_number = component_value["number"]
        residual_number = residual["number"]
        printed_samples = printed_value["source_sample_ids"]
        component_samples = component_value["source_sample_ids"]
        if (
            type(printed_component_cells) is not list
            or type(printed_result_cells) is not list
            or len(printed_result_cells) != 1
        ):
            return None
        precision_sample_ids = [cell.get("source_sample_id") for cell in printed_component_cells]
        precision_numbers = [cell.get("number") for cell in printed_component_cells]
        if (
            printed_number["percentage_mark_present"]
            or component_number["percentage_mark_present"]
            or residual_number["percentage_mark_present"]
            or printed_number["scale"] != 0
            or component_number["scale"] != 0
            or residual_number["scale"] != 0
            or len(printed_samples) != 1
            or not component_samples
            or len(component_samples) != len(set(component_samples))
            or set(printed_samples) & set(component_samples)
            or precision_sample_ids != component_samples
            or any(
                cell.get("classification") not in {"DASH_ZERO", "SIGNED_NUMBER"}
                for cell in printed_component_cells
            )
            or printed_result_cells[0].get("classification") != "SIGNED_NUMBER"
            or any(
                type(number) is not dict
                or set(number) != {"coefficient", "percentage_mark_present", "scale"}
                or type(number["coefficient"]) is not int
                or number["percentage_mark_present"] is not False
                or number["scale"] != 0
                for number in precision_numbers
            )
            or any(
                cell["classification"] == "DASH_ZERO" and cell["number"]["coefficient"] != 0
                for cell in printed_component_cells
            )
            or (
                printed_number["coefficient"] != 0
                and component_number["coefficient"] != 0
                and (printed_number["coefficient"] > 0) is not (component_number["coefficient"] > 0)
            )
        ):
            return None
        component_count = sum(
            cell["classification"] == "SIGNED_NUMBER" for cell in printed_component_cells
        )
        if component_count < 1:
            return None
        twice_absolute_residual = 2 * abs(residual_number["coefficient"])
        bound = component_count + 1
        lanes.append(
            {
                "bound_component_count_plus_one": bound,
                "column_ordinal": residual["column_ordinal"],
                "independently_printed_component_count": component_count,
                "printed_component_cells": [
                    {
                        "number": canonical_clone_v1(cell["number"]),
                        "source_sample_id": cell["source_sample_id"],
                    }
                    for cell in printed_component_cells
                ],
                "printed_result_cell": {
                    "number": canonical_clone_v1(printed_number),
                    "source_sample_id": printed_samples[0],
                },
                "residual_number": canonical_clone_v1(residual_number),
                "status": (
                    "WITHIN_INTEGER_DISPLAY_UNIT_ROUNDING_BOUND"
                    if twice_absolute_residual <= bound
                    else "OVER_INTEGER_DISPLAY_UNIT_ROUNDING_BOUND"
                ),
                "twice_absolute_residual": twice_absolute_residual,
            }
        )
    within = all(lane["status"] == "WITHIN_INTEGER_DISPLAY_UNIT_ROUNDING_BOUND" for lane in lanes)
    return {
        "candidate_ordinal": candidate_ordinal,
        "component_roles": list(component_roles),
        "lanes": lanes,
        "policy": (
            "RESULT_AND_NON_DASH_COMPONENTS_SIGNED_INTEGER_DISPLAY_UNIT;"
            "AUTHENTICATED_DASH_ZERO_EXACT_ZERO_EXCLUDED_FROM_ROUNDING_COUNT;"
            "SAME_NONZERO_RESULT_SUM_SIGN;2*ABS(PRINTED_MINUS_COMPONENT_SUM)<="
            "INDEPENDENTLY_PRINTED_NUMERIC_COMPONENT_COUNT+1"
        ),
        "printed_result_owner": printed_result_owner,
        "result_role": result_role,
        "status": (
            "ROUNDING_BOUND_SATISFIED_ALL_LANES"
            if within
            else "ROUNDING_BOUND_EXCEEDED_AT_LEAST_ONE_LANE"
        ),
    }


def _aggregate_source_roles(
    rows: Sequence[Mapping[str, Any]],
    aggregate_roles: set[str],
    local_subtotal_roles: set[str],
    nonadditive_roles: set[str],
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
                and role not in nonadditive_roles
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
            source_resolutions = [record["resolution"] for record in records]
            resolved[role] = {
                _PRINTED_SOURCE_CELLS_KEY: _printed_source_cells_by_lane(source_resolutions),
                "component_roles": [],
                "resolution_kind": "DERIVED_EXACT_DISJOINT_OCCURRENCE_SUM",
                "role": role,
                "source": None,
                "values": _sum_records(source_resolutions),
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
        records = [resolved[role] for role in roles]
        printed_axes = [record.get(_PRINTED_SOURCE_CELLS_KEY) for record in records]
        printed_sample_ids = [
            cell.get("source_sample_id")
            for axis in printed_axes
            if type(axis) is list
            for lane in axis
            if type(lane) is list
            for cell in lane
            if type(cell) is dict
        ]
        if len(printed_sample_ids) != len(set(printed_sample_ids)):
            continue
        result.append(
            {
                _PRINTED_SOURCE_CELLS_KEY: _printed_source_cells_by_lane(records),
                "component_roles": list(roles),
                "derivation_policy": alternative["derivation_policy"],
                "values": _sum_records(records),
            }
        )
    return result


def _local_equations(
    equation: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    role_occurrences: Sequence[Mapping[str, Any]],
    *,
    allow_rounding: bool,
) -> tuple[list[dict[str, Any]], set[str], set[str], set[str], list[str]]:
    def equation_record(
        *,
        component_roles: Sequence[str],
        result_occurrence_id: str,
        status: str,
        residual_evidence: Sequence[Mapping[str, Any]] = (),
        rounding_evidence: Sequence[Mapping[str, Any]] = (),
    ) -> dict[str, Any]:
        result = {
            "component_roles_present": list(component_roles),
            "result_occurrence_id": result_occurrence_id,
            "result_role": equation["result_role"],
            "status": status,
        }
        if allow_rounding:
            result["residual_evidence"] = canonical_clone_v1(list(residual_evidence))
            result["rounding_evidence"] = canonical_clone_v1(list(rounding_evidence))
        return result

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
                equation_record(
                    component_roles=[],
                    result_occurrence_id=result_occurrence,
                    status="LOCAL_SUBTOTAL_RESULT_PARTIAL_VALUE_LANES_VETO",
                )
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
                    equation_record(
                        component_roles=[],
                        result_occurrence_id=result_occurrence,
                        status=(
                            "LOCAL_SINGLE_SCOPE_WITHOUT_VISIBLE_SUBTOTAL_"
                            "DEFERRED_TO_EXHAUSTIVE_GLOBAL_EQUATION"
                        ),
                    )
                )
                continue
            records.append(
                equation_record(
                    component_roles=[],
                    result_occurrence_id=result_occurrence,
                    status="LOCAL_SUBTOTAL_RESULT_MISSING_OR_INCOMPLETE_VETO",
                )
            )
            reasons.append(
                f"LOCAL_SUBTOTAL_RESULT_MISSING_OR_INCOMPLETE:"
                f"{equation['result_role']}:{result_occurrence}"
            )
            continue
        if result_row is not None and result_row["status"] != "VISIBLE_VALUE_LANES_BOUND":
            records.append(
                equation_record(
                    component_roles=[],
                    result_occurrence_id=result_occurrence,
                    status="LOCAL_SUBTOTAL_RESULT_MISSING_OR_INCOMPLETE_VETO",
                )
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
                    _PRINTED_SOURCE_CELLS_KEY: _printed_source_cells_by_lane(
                        [scoped_by_role[role][0] for role in roles]
                    ),
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
        residual_evidence = []
        rounding_evidence = []
        rounding_alternatives = []
        if allow_rounding and not exact:
            for alternative in alternatives:
                residual = _typed_residual_evidence(
                    result_role=equation["result_role"],
                    printed=visible,
                    component=alternative,
                    component_roles=alternative["component_roles"],
                )
                if residual is not None:
                    residual_evidence.append(residual)
                assessment = _rounding_assessment(
                    result_role=equation["result_role"],
                    printed=visible,
                    component=alternative,
                    component_roles=alternative["component_roles"],
                )
                if assessment is not None:
                    rounding_evidence.append(assessment)
                    rounding_alternatives.append((alternative, assessment))
        if exact:
            selected = _unique_maximum_component_coverage(exact)
            if selected is not None:
                status = "LOCAL_VISIBLE_SUBTOTAL_CORROBORATED_BY_EXACT_SCOPED_COMPONENTS"
                component_roles = selected["component_roles"]
                valid_results.add(result_occurrence)
                authorized_component_scopes.add(result_occurrence)
                covered_components.update(selected["component_occurrence_ids"])
            else:
                status = "LOCAL_AMBIGUOUS_EXACT_COMPONENT_OWNERSHIP_VETO"
                component_roles = []
                reasons.append(
                    f"LOCAL_AMBIGUOUS_EXACT_COMPONENT_OWNERSHIP:"
                    f"{equation['result_role']}:{result_occurrence}"
                )
        elif within_rounding := [
            item
            for item in rounding_alternatives
            if item[1]["status"] == "ROUNDING_BOUND_SATISFIED_ALL_LANES"
        ]:
            maximum = max(len(item[0]["component_roles"]) for item in within_rounding)
            strongest = [
                item for item in within_rounding if len(item[0]["component_roles"]) == maximum
            ]
            if len(strongest) == 1:
                selected = strongest[0][0]
                status = (
                    "LOCAL_VISIBLE_SUBTOTAL_ROUNDING_CORROBORATED_BY_EXHAUSTIVE_SCOPED_COMPONENTS"
                )
                component_roles = selected["component_roles"]
                valid_results.add(result_occurrence)
                authorized_component_scopes.add(result_occurrence)
                covered_components.update(selected["component_occurrence_ids"])
            else:
                status = "LOCAL_AMBIGUOUS_ROUNDING_COMPONENT_OWNERSHIP_VETO"
                component_roles = []
                reasons.append(
                    f"LOCAL_AMBIGUOUS_ROUNDING_COMPONENT_OWNERSHIP:"
                    f"{equation['result_role']}:{result_occurrence}"
                )
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
            # A component role shared with an ancestor equation is not part of
            # this local result frontier.  Keep its exact occurrence scope
            # eligible for the ancestor equation; that later equation must
            # still consume it exactly once or the global use-count gate vetoes
            # the closure.  Locally exclusive children continue through the
            # exhaustive subtotal paths above.
            authorized_component_scopes.add(result_occurrence)
        else:
            status = "LOCAL_VISIBLE_SUBTOTAL_INCOMPLETE_COMPONENT_SET_VETO"
            component_roles = []
            reasons.append(
                f"LOCAL_VISIBLE_RESULT_LACKS_EXHAUSTIVE_COMPONENT_SET:"
                f"{equation['result_role']}:{result_occurrence}"
            )
        records.append(
            equation_record(
                component_roles=component_roles,
                residual_evidence=residual_evidence,
                result_occurrence_id=result_occurrence,
                rounding_evidence=rounding_evidence,
                status=status,
            )
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
    *,
    allow_rounding: bool,
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
    rounding_evidence: list[dict[str, Any]] = []
    trailing_candidate_evidence: list[dict[str, Any]] = []
    selected_trailing_candidate_ordinal: int | None = None
    precomputed_trailing_residuals = False
    if visible_candidates and any(
        not _same_values(visible_candidates[0]["values"], item["values"])
        for item in visible_candidates[1:]
    ):
        reasons.append(f"VISIBLE_RESULT_ROLES_DISAGREE:{result_role}")
    visible = visible_candidates[0] if visible_candidates else None
    selected: dict[str, Any] | None = None
    selected_by_rounding = False
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
            rounding_alternatives = []
            for alternative in alternatives:
                evidence = _typed_residual_evidence(
                    result_role=result_role,
                    printed=visible,
                    component=alternative,
                    component_roles=alternative["component_roles"],
                )
                if evidence is not None:
                    residual_evidence.append(evidence)
                if allow_rounding:
                    assessment = _rounding_assessment(
                        result_role=result_role,
                        printed=visible,
                        component=alternative,
                        component_roles=alternative["component_roles"],
                    )
                    if assessment is not None:
                        rounding_evidence.append(assessment)
                        rounding_alternatives.append((alternative, assessment))
            within_rounding = [
                item
                for item in rounding_alternatives
                if item[1]["status"] == "ROUNDING_BOUND_SATISFIED_ALL_LANES"
            ]
            if within_rounding:
                maximum = max(len(item[0]["component_roles"]) for item in within_rounding)
                strongest = [
                    item for item in within_rounding if len(item[0]["component_roles"]) == maximum
                ]
                if len(strongest) == 1:
                    selected = strongest[0][0]
                    selected_by_rounding = True
                    status = "VISIBLE_RESULT_ROUNDING_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS"
                else:
                    status = "AMBIGUOUS_ROUNDING_COMPONENT_OWNERSHIP_VETO"
                    reasons.append(f"AMBIGUOUS_ROUNDING_COMPONENT_OWNERSHIP:{result_role}")
            else:
                status = "VISIBLE_RESULT_MISMATCH_VETO"
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
        rounding_pairs = []
        if (
            allow_rounding
            and claimed_trailing
            and alternatives
            and complete_trailing
            and not exact_pairs
        ):
            precomputed_trailing_residuals = True
            for alternative in alternatives:
                for row, candidate in complete_trailing:
                    evidence = _typed_residual_evidence(
                        result_role=result_role,
                        printed=candidate,
                        component=alternative,
                        component_roles=alternative["component_roles"],
                    )
                    if evidence is not None:
                        residual_evidence.append(evidence)
                    assessment = _rounding_assessment(
                        result_role=result_role,
                        printed=candidate,
                        component=alternative,
                        component_roles=alternative["component_roles"],
                    )
                    if assessment is not None:
                        rounding_evidence.append(assessment)
                        rounding_pairs.append((alternative, row, candidate, assessment))
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
        elif claimed_trailing and len(trailing_rows) == 1 and rounding_pairs:
            within_rounding = [
                item
                for item in rounding_pairs
                if item[3]["status"] == "ROUNDING_BOUND_SATISFIED_ALL_LANES"
            ]
            if within_rounding:
                maximum = max(len(item[0]["component_roles"]) for item in within_rounding)
                strongest = [
                    item for item in within_rounding if len(item[0]["component_roles"]) == maximum
                ]
                if len(strongest) == 1:
                    selected, selected_row, source, _assessment = strongest[0]
                    selected_by_rounding = True
                    selected_trailing_candidate_ordinal = selected_row["candidate_ordinal"]
                    status = (
                        "VISIBLE_TRAILING_RESULT_ROUNDING_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS"
                    )
                else:
                    status = "AMBIGUOUS_ROUNDING_COMPONENT_OWNERSHIP_VETO"
                    reasons.append(f"AMBIGUOUS_ROUNDING_COMPONENT_OWNERSHIP:{result_role}")
            else:
                status = "TRAILING_NUMERIC_CHALLENGER_VETO"
                reasons.append(f"TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM:{result_role}:0")
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
            numeric_signatures = {
                _exact_numeric_value_signature(item["values"]) for item in derivable
            }
            if len(numeric_signatures) == 1:
                strongest = _unique_maximum_component_coverage(derivable)
                if strongest is not None:
                    selected = strongest
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
                "SELECTED_ROUNDING_CORROBORATED_VISIBLE_TRAILING_ROOT_SOURCE"
                if is_selected and selected_by_rounding
                else "SELECTED_VISIBLE_TRAILING_ROOT_SOURCE"
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
                if (
                    row["status"] == "COMPLETE_VISIBLE_TRAILING_VALUE_ROW"
                    and not precomputed_trailing_residuals
                ):
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
                _PRINTED_SOURCE_CELLS_KEY: canonical_clone_v1(selected[_PRINTED_SOURCE_CELLS_KEY]),
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
                    "VISIBLE_TRAILING_TOTAL_ROUNDING_CORROBORATED_BY_COMPONENTS"
                    if source_kind == "TRAILING_VALUE_ROW" and selected_by_rounding
                    else "VISIBLE_TRAILING_TOTAL_CORROBORATED_BY_COMPONENTS"
                    if source_kind == "TRAILING_VALUE_ROW"
                    else "DERIVED_EXACT_DISJOINT_OCCURRENCE_SUM_CORROBORATED_BY_COMPONENTS"
                    if source_kind is None
                    else "VISIBLE_SOURCE_ROLE_ROUNDING_CORROBORATED_BY_COMPONENTS"
                    if selected_by_rounding
                    else "VISIBLE_SOURCE_ROLE_CORROBORATED_BY_COMPONENTS"
                ),
                "role": result_role,
            }
    record = {
        "component_roles_present": selected["component_roles"] if selected is not None else [],
        "residual_evidence": residual_evidence,
        "result_role": result_role,
        "selected_trailing_candidate_ordinal": selected_trailing_candidate_ordinal,
        "status": status,
        "trailing_candidate_evidence": trailing_candidate_evidence,
    }
    if allow_rounding:
        record["rounding_evidence"] = rounding_evidence
        record["visible_result_roles"] = canonical_clone_v1(equation["visible_result_roles"])
    return record, reasons


def _numeric_source_candidate_axis(
    numeric_sample_universe: Sequence[Mapping[str, Any]],
    internal_clusters: Sequence[Mapping[str, Any]],
    trailing_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Project unowned/trailing numeric rows without giving them semantic roles."""

    sample_by_id = {sample["sample_id"]: sample for sample in numeric_sample_universe}

    def candidate(
        *,
        key: tuple[str, str | int],
        row_kind: str,
        source_record: Mapping[str, Any],
        sample_ids: Sequence[str],
        source_complete: bool,
    ) -> dict[str, Any]:
        samples = [sample_by_id.get(sample_id) for sample_id in sample_ids]
        typed_samples = [sample for sample in samples if type(sample) is dict]
        columns = [sample["column_ordinal"] for sample in typed_samples]
        pages = {sample["page_sequence"] for sample in typed_samples}
        source_values = source_record.get("values", [])
        shared_fields = {
            "bbox",
            "column_center",
            "column_ordinal",
            "crop_ref",
            "line_ordinal",
            "page_sequence",
            "parsed_token",
            "raw_prediction",
            "reader_score",
            "sample_id",
        }
        source_values_match_universe = row_kind != "TRAILING_VALUE_ROW" or (
            type(source_values) is list
            and len(source_values) == len(typed_samples)
            and all(
                same_typed_json_v1(
                    {field: value.get(field) for field in shared_fields},
                    {field: sample.get(field) for field in shared_fields},
                )
                for value, sample in zip(source_values, typed_samples, strict=True)
            )
        )
        complete = (
            source_complete
            and len(typed_samples) == len(sample_ids)
            and bool(typed_samples)
            and len(pages) == 1
            and columns == list(range(len(columns)))
            and len(columns) == len(set(columns))
            and source_values_match_universe
            and all(
                sample["parsed_token"]["classification"] == "SIGNED_NUMBER"
                for sample in typed_samples
            )
        )
        values = [
            {
                "column_ordinal": sample["column_ordinal"],
                "number": _number(sample),
                "source_sample_ids": [sample["sample_id"]],
            }
            for sample in typed_samples
        ]
        return {
            "bottom": max((sample["bbox"][3] for sample in typed_samples), default=-1),
            "complete": complete,
            "key": key,
            "line_ordinal": min((sample["line_ordinal"] for sample in typed_samples), default=-1),
            "page_sequence": next(iter(pages)) if len(pages) == 1 else None,
            "row_kind": row_kind,
            "sample_ids": list(sample_ids),
            "source_record": canonical_clone_v1(source_record),
            "top": min((sample["bbox"][1] for sample in typed_samples), default=-1),
            "values": values,
        }

    result = []
    for cluster in internal_clusters:
        result.append(
            candidate(
                key=("cluster", cluster["cluster_id"]),
                row_kind="INTERNAL_UNASSIGNED_NUMERIC_CLUSTER",
                sample_ids=cluster["sample_ids"],
                source_complete=(
                    cluster["status"] == occurrence_v2._INTERNAL_UNASSIGNED_CLUSTER_STATUS
                    and cluster["label_lane_status"] == occurrence_v2._UNLABELED_LABEL_LANE_STATUS
                ),
                source_record=cluster,
            )
        )
    for trailing in trailing_rows:
        result.append(
            candidate(
                key=("trailing", trailing["candidate_ordinal"]),
                row_kind="TRAILING_VALUE_ROW",
                sample_ids=[value["sample_id"] for value in trailing["values"]],
                source_complete=(trailing["status"] == "COMPLETE_VISIBLE_TRAILING_VALUE_ROW"),
                source_record=trailing,
            )
        )
    return sorted(
        result,
        key=lambda item: (
            item["page_sequence"] if type(item["page_sequence"]) is int else 2**31,
            item["top"],
            item["line_ordinal"],
            str(item["key"]),
        ),
    )


def _occurrence_descends_from(
    occurrence: Mapping[str, Any],
    ancestor_occurrence_id: str,
    occurrence_by_id: Mapping[str, Mapping[str, Any]],
) -> bool:
    """Return true only for one acyclic, explicitly bound ownership chain."""

    owner = occurrence.get("scope_owner_occurrence_id")
    visited: set[str] = set()
    while type(owner) is str and owner:
        if owner == ancestor_occurrence_id:
            return True
        if owner in visited:
            return False
        visited.add(owner)
        parent = occurrence_by_id.get(owner)
        if type(parent) is not dict:
            return False
        owner = parent.get("scope_owner_occurrence_id")
    return False


def _local_trailing_subgroup_subtotal_receipt(
    *,
    accounting_rows: Sequence[Mapping[str, Any]],
    equation: Mapping[str, Any],
    family_id: str,
    hierarchy_spec_sha256: str,
    local_records: Sequence[Mapping[str, Any]],
    numeric_sample_universe: Sequence[Mapping[str, Any]],
    role_occurrences: Sequence[Mapping[str, Any]],
    row_axis: Mapping[str, Any],
    source_candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any] | None:
    """Prove one exact visible-lane subtotal selector for one sealed local scope.

    This is deliberately narrower than the legacy global unlabeled-subtotal
    projector.  It creates no role and performs no backsolve: a structural
    loan group may consume exactly one unlabeled physical numeric row only
    when that row closes the subgroup interval immediately after every owned
    descendant.  A partial row is selection-only: every omitted lane must be
    exactly identical across every competing exhaustive alternative.
    """

    target_role = equation.get("result_role")
    trusted_equation = _local_trailing_subgroup_trusted_equation_spec()
    equation_spec_sha256 = canonical_json_sha256_v1(equation)
    if (
        family_id != "INTERBANK_DEPOSITS_AND_LOANS"
        or target_role != "INTERBANK_LOAN_GROUP"
        or hierarchy_spec_sha256 != _LOCAL_TRAILING_SUBGROUP_TRUSTED_HIERARCHY_SPEC_SHA256
        or equation_spec_sha256 != _LOCAL_TRAILING_SUBGROUP_TRUSTED_EQUATION_SPEC_SHA256
        or not same_typed_json_v1(equation, trusted_equation)
    ):
        return None
    target_occurrences = [
        occurrence for occurrence in role_occurrences if occurrence.get("role") == target_role
    ]
    target_local_records = [
        record for record in local_records if record.get("result_role") == target_role
    ]
    if (
        len(target_occurrences) != 1
        or len(target_local_records) != 1
        or target_local_records[0].get("status")
        != "LOCAL_SINGLE_SCOPE_WITHOUT_VISIBLE_SUBTOTAL_DEFERRED_TO_EXHAUSTIVE_GLOBAL_EQUATION"
        or target_local_records[0].get("component_roles_present") != []
        or "rounding_evidence" not in target_local_records[0]
    ):
        return None
    target = target_occurrences[0]
    target_id = target.get("occurrence_id")
    target_match = target.get("label_match")
    parent_id = target.get("scope_owner_occurrence_id")
    region = row_axis.get("topology_region")
    parent_match = region.get("parent_match") if type(region) is dict else None
    if (
        type(target_id) is not str
        or type(parent_id) is not str
        or not parent_id.startswith("aforav2:root:")
        or target.get("role_kind") != "STRUCTURAL_GROUP"
        or target.get("has_bound_value_row") is not False
        or type(target_match) is not dict
        or not occurrence_v2._match_has_effective_exact_source_authority(  # noqa: SLF001
            target_match
        )
        or not str(target.get("scope_owner_match_kind", "")).startswith("EXACT_")
        or type(region) is not dict
        or type(parent_match) is not dict
        or not occurrence_v2._match_has_effective_exact_source_authority(  # noqa: SLF001
            parent_match
        )
        or region.get("page_sequence") != target_match.get("page_sequence")
    ):
        return None
    page_sequence = target_match["page_sequence"]
    stop_source = region.get("cluster_end_source_line_index_exclusive")
    stop_document = region.get("cluster_end_document_line_ordinal_exclusive")
    target_source = target_match.get("source_line_index")
    target_document = target_match.get("document_line_ordinal")
    if (
        any(
            type(item) is not int
            for item in (stop_source, stop_document, target_source, target_document)
        )
        or not target_source < stop_source
        or stop_document - target_document != stop_source - target_source
    ):
        return None

    occurrence_by_id = {
        occurrence.get("occurrence_id"): occurrence
        for occurrence in role_occurrences
        if type(occurrence.get("occurrence_id")) is str
    }
    if len(occurrence_by_id) != len(role_occurrences):
        return None
    descendants = [
        occurrence
        for occurrence in role_occurrences
        if _occurrence_descends_from(occurrence, target_id, occurrence_by_id)
    ]
    descendants.sort(
        key=lambda occurrence: (
            occurrence["label_match"]["document_line_ordinal"],
            occurrence["occurrence_id"],
        )
    )
    descendant_ids = [occurrence["occurrence_id"] for occurrence in descendants]
    if not descendants or any(
        occurrence.get("role_kind") not in {"ADDITIVE_CHILD", "NONADDITIVE_CHILD"}
        or type(occurrence.get("label_match")) is not dict
        or not occurrence_v2._match_has_effective_exact_source_authority(  # noqa: SLF001
            occurrence["label_match"]
        )
        or occurrence["label_match"].get("page_sequence") != page_sequence
        or not target_source < occurrence["label_match"].get("source_line_index", -1) < stop_source
        for occurrence in descendants
    ):
        return None
    interval_occurrences = [
        occurrence
        for occurrence in role_occurrences
        if occurrence.get("label_match", {}).get("page_sequence") == page_sequence
        and target_source
        < occurrence.get("label_match", {}).get("source_line_index", -1)
        < stop_source
    ]
    later_non_descendants = sorted(
        (
            occurrence
            for occurrence in interval_occurrences
            if occurrence["occurrence_id"] not in set(descendant_ids)
        ),
        key=lambda occurrence: (
            occurrence["label_match"]["source_line_index"],
            occurrence["occurrence_id"],
        ),
    )
    boundary = later_non_descendants[0] if later_non_descendants else None
    if boundary is not None and (
        boundary.get("role_kind") != "TOTAL"
        or boundary.get("scope_owner_occurrence_id") != parent_id
        or not occurrence_v2._match_has_effective_exact_source_authority(  # noqa: SLF001
            boundary.get("label_match", {})
        )
    ):
        return None
    subgroup_stop_source = (
        boundary["label_match"]["source_line_index"] if boundary is not None else stop_source
    )
    subgroup_stop_document = (
        boundary["label_match"]["document_line_ordinal"] if boundary is not None else stop_document
    )
    if (
        subgroup_stop_document - target_document != subgroup_stop_source - target_source
        or any(
            occurrence["occurrence_id"] not in set(descendant_ids)
            for occurrence in interval_occurrences
            if occurrence["label_match"]["source_line_index"] < subgroup_stop_source
        )
        or any(
            occurrence["label_match"]["source_line_index"] >= subgroup_stop_source
            for occurrence in descendants
        )
    ):
        return None

    rows_by_occurrence: dict[str, Mapping[str, Any]] = {}
    for row in accounting_rows:
        occurrence_id = row.get("label_match", {}).get("occurrence_id")
        if type(occurrence_id) is not str or occurrence_id in rows_by_occurrence:
            return None
        rows_by_occurrence[occurrence_id] = row
    descendant_rows = [rows_by_occurrence.get(occurrence_id) for occurrence_id in descendant_ids]
    if any(
        type(row) is not dict
        or row.get("status") != "VISIBLE_VALUE_LANES_BOUND"
        or not row.get("values")
        for row in descendant_rows
    ):
        return None
    additive = [
        occurrence for occurrence in descendants if occurrence["role_kind"] == "ADDITIVE_CHILD"
    ]
    nonadditive = [
        occurrence for occurrence in descendants if occurrence["role_kind"] == "NONADDITIVE_CHILD"
    ]
    additive_roles = [occurrence["role"] for occurrence in additive]
    if len(additive_roles) != len(set(additive_roles)):
        return None
    additive_by_role = {occurrence["role"]: occurrence for occurrence in additive}
    required_roles = set(additive_roles) - set(equation["shared_component_roles"])
    applicable_alternatives = []
    for alternative_ordinal, alternative in enumerate(equation["component_role_alternatives"]):
        roles = list(alternative["component_roles"])
        if not required_roles <= set(roles) or not all(role in additive_by_role for role in roles):
            continue
        occurrence_ids = [additive_by_role[role]["occurrence_id"] for role in roles]
        rows = [rows_by_occurrence[occurrence_id] for occurrence_id in occurrence_ids]
        applicable_alternatives.append(
            {
                "alternative_ordinal": alternative_ordinal,
                "alternative_spec_sha256": canonical_json_sha256_v1(alternative),
                "component_occurrence_ids": occurrence_ids,
                "component_roles": roles,
                "component_sample_ids": [
                    value["sample_id"] for row in rows for value in row["values"]
                ],
                "values": _sum_records([_source_resolution(row) for row in rows]),
            }
        )
    if not applicable_alternatives:
        return None

    sample_by_id = {
        sample.get("sample_id"): sample
        for sample in numeric_sample_universe
        if type(sample.get("sample_id")) is str
    }
    if len(sample_by_id) != len(numeric_sample_universe):
        return None

    def owned_sample_ids(occurrence_id: str) -> list[str]:
        return [value["sample_id"] for value in rows_by_occurrence[occurrence_id]["values"]]

    nonadditive_occurrence_ids = [occurrence["occurrence_id"] for occurrence in nonadditive]
    nonadditive_sample_ids = [
        sample_id
        for occurrence_id in nonadditive_occurrence_ids
        for sample_id in owned_sample_ids(occurrence_id)
    ]
    descendant_sample_ids = [
        sample_id
        for occurrence_id in descendant_ids
        for sample_id in owned_sample_ids(occurrence_id)
    ]
    if len(descendant_sample_ids) != len(set(descendant_sample_ids)) or any(
        type(sample_by_id.get(sample_id)) is not dict
        or sample_by_id[sample_id].get("owner_kind") != "ROLE_OCCURRENCE"
        or sample_by_id[sample_id].get("owner_id") != occurrence_id
        for occurrence_id in descendant_ids
        for sample_id in owned_sample_ids(occurrence_id)
    ):
        return None
    descendant_samples = [sample_by_id[sample_id] for sample_id in descendant_sample_ids]
    last_descendant_source = max(sample["line_ordinal"] for sample in descendant_samples)
    page_document_offset = target_document - target_source
    last_descendant_document = page_document_offset + last_descendant_source

    post_descendant_sources = []
    for source in source_candidates:
        source_samples = [sample_by_id.get(sample_id) for sample_id in source["sample_ids"]]
        if not source_samples or any(type(sample) is not dict for sample in source_samples):
            continue
        source_lines = [sample["line_ordinal"] for sample in source_samples]
        if (
            source.get("page_sequence") == page_sequence
            and min(source_lines) > last_descendant_source
            and max(source_lines) < subgroup_stop_source
        ):
            post_descendant_sources.append((source, source_samples))
    if len(post_descendant_sources) != 1:
        return None
    selected, selected_samples = post_descendant_sources[0]
    selected_lines = [sample["line_ordinal"] for sample in selected_samples]
    candidate_first_source = min(selected_lines)
    candidate_last_source = max(selected_lines)
    candidate_ordinal = (
        selected["source_record"].get("candidate_ordinal")
        if selected["row_kind"] == "TRAILING_VALUE_ROW"
        else None
    )
    source_cluster_id = (
        selected["source_record"].get("cluster_id")
        if selected["row_kind"] == "INTERNAL_UNASSIGNED_NUMERIC_CLUSTER"
        else None
    )
    observed_columns = [value["column_ordinal"] for value in selected["values"]]
    lane_axis = [value["column_ordinal"] for value in applicable_alternatives[0]["values"]]
    if any(
        [value["column_ordinal"] for value in alternative["values"]] != lane_axis
        for alternative in applicable_alternatives
    ):
        return None
    missing_columns = [lane for lane in lane_axis if lane not in set(observed_columns)]

    def exact_visible_lanes_match(alternative: Mapping[str, Any]) -> bool:
        by_lane = {value["column_ordinal"]: value for value in alternative["values"]}
        return all(
            value["column_ordinal"] in by_lane
            and same_typed_json_v1(value["number"], by_lane[value["column_ordinal"]]["number"])
            for value in selected["values"]
        )

    matching_alternatives = [
        alternative
        for alternative in applicable_alternatives
        if exact_visible_lanes_match(alternative)
    ]
    missing_lanes_are_nondiscriminating = all(
        len(
            {
                canonical_json_sha256_v1(alternative["values"][lane]["number"])
                for alternative in applicable_alternatives
            }
        )
        == 1
        for lane in missing_columns
    )
    if len(matching_alternatives) != 1:
        return None
    selected_alternative = matching_alternatives[0]
    component_roles = selected_alternative["component_roles"]
    component_occurrence_ids = selected_alternative["component_occurrence_ids"]
    component_sample_ids = selected_alternative["component_sample_ids"]
    component_sum = selected_alternative["values"]
    component_rows = [rows_by_occurrence[item] for item in component_occurrence_ids]
    selection_kind = (
        "COMPLETE_EXACT_ALL_LANES"
        if not missing_columns
        else "PARTIAL_EXACT_UNIQUE_VISIBLE_LANES_IDENTICAL_MISSING_LANES"
    )
    if (
        observed_columns != sorted(set(observed_columns))
        or not observed_columns
        or any(column not in lane_axis for column in observed_columns)
        or (missing_columns and len(applicable_alternatives) < 2)
        or (missing_columns and not missing_lanes_are_nondiscriminating)
        or (
            selected.get("row_kind") == "TRAILING_VALUE_ROW"
            and (type(candidate_ordinal) is not int or missing_columns or not selected["complete"])
        )
        or (
            selected.get("row_kind") == "INTERNAL_UNASSIGNED_NUMERIC_CLUSTER"
            and (
                type(source_cluster_id) is not str
                or selected["source_record"].get("status")
                != occurrence_v2._INTERNAL_UNASSIGNED_CLUSTER_STATUS
                or selected["source_record"].get("label_lane_status")
                != occurrence_v2._UNLABELED_LABEL_LANE_STATUS
            )
        )
        or selected.get("row_kind")
        not in {"TRAILING_VALUE_ROW", "INTERNAL_UNASSIGNED_NUMERIC_CLUSTER"}
        or candidate_first_source != last_descendant_source + 1
        or candidate_last_source != subgroup_stop_source - 1
        or page_document_offset + candidate_last_source != subgroup_stop_document - 1
        or max(sample["bbox"][1] for sample in selected_samples)
        >= min(sample["bbox"][3] for sample in selected_samples)
        or min(sample["bbox"][1] for sample in selected_samples)
        <= max(sample["bbox"][3] for sample in descendant_samples)
        or any(
            (
                sample.get("owner_kind") != "TRAILING_VALUE_ROW"
                or sample.get("owner_id") != f"aforav2:trailing:{candidate_ordinal}"
            )
            if selected["row_kind"] == "TRAILING_VALUE_ROW"
            else (
                sample.get("owner_kind") != "SOURCE_ONLY_INTERNAL_CLUSTER"
                or sample.get("owner_id") != source_cluster_id
            )
            for sample in selected_samples
        )
    ):
        return None

    interval = {
        "candidate_first_document_line_ordinal": page_document_offset + candidate_first_source,
        "candidate_first_source_line_index": candidate_first_source,
        "candidate_last_document_line_ordinal": page_document_offset + candidate_last_source,
        "candidate_last_source_line_index": candidate_last_source,
        "last_descendant_document_line_ordinal": last_descendant_document,
        "last_descendant_source_line_index": last_descendant_source,
        "page_sequence": page_sequence,
        "subgroup_stop_document_line_ordinal_exclusive": subgroup_stop_document,
        "subgroup_stop_source_line_index_exclusive": subgroup_stop_source,
        "target_document_line_ordinal": target_document,
        "target_source_line_index": target_source,
        "topology_region_stop_document_line_ordinal_exclusive": stop_document,
        "topology_region_stop_source_line_index_exclusive": stop_source,
    }
    receipt_material = {
        "applicable_alternative_ordinals": [
            alternative["alternative_ordinal"] for alternative in applicable_alternatives
        ],
        "applicable_alternative_spec_sha256s": [
            alternative["alternative_spec_sha256"] for alternative in applicable_alternatives
        ],
        "alternative_value_axes": canonical_clone_v1(applicable_alternatives),
        "boundary_occurrence_id": (boundary["occurrence_id"] if boundary is not None else None),
        "boundary_role": boundary["role"] if boundary is not None else None,
        "candidate_ordinal": candidate_ordinal,
        "component_occurrence_ids": component_occurrence_ids,
        "component_roles": component_roles,
        "component_sample_ids": component_sample_ids,
        "configured_alternative_role_sets": [
            list(roles) for roles in _LOCAL_TRAILING_SUBGROUP_TRUSTED_COMPONENT_ROLE_SETS
        ],
        "descendant_occurrence_ids": descendant_ids,
        "equation_spec_sha256": equation_spec_sha256,
        "hierarchy_spec_sha256": hierarchy_spec_sha256,
        "interval": interval,
        "nonadditive_occurrence_ids": nonadditive_occurrence_ids,
        "nonadditive_sample_ids": nonadditive_sample_ids,
        "missing_column_ordinals": missing_columns,
        "numeric_sample_universe_sha256": canonical_json_sha256_v1(numeric_sample_universe),
        "observed_column_ordinals": observed_columns,
        "parent_occurrence_id": parent_id,
        "role_occurrence_axis_sha256": canonical_json_sha256_v1(role_occurrences),
        "row_axis_id": row_axis["row_axis_id"],
        "source_cluster_id": source_cluster_id,
        "source_record_sha256": canonical_json_sha256_v1(selected["source_record"]),
        "source_row_kind": selected["row_kind"],
        "source_sample_ids": canonical_clone_v1(selected["sample_ids"]),
        "selection_kind": selection_kind,
        "status": _LOCAL_TRAILING_SUBGROUP_RECEIPT_STATUS,
        "target_occurrence_id": target_id,
        "target_role": target_role,
    }
    receipt = {
        **receipt_material,
        "receipt_id": "ashtcv2:local-trailing-subgroup-subtotal:"
        + canonical_json_sha256_v1(receipt_material),
    }
    return {
        "candidate_ordinal": candidate_ordinal,
        "disposition": _LOCAL_TRAILING_SUBGROUP_SUBTOTAL_CORROBORATION,
        "occurrence_id": target_id,
        "receipt": receipt,
        "resolution": {
            _PRINTED_SOURCE_CELLS_KEY: _printed_source_cells_by_lane(
                [_source_resolution(row) for row in component_rows]
            ),
            "component_roles": component_roles,
            "resolution_kind": "DERIVED_EXACT_LOCAL_TRAILING_SUBGROUP_SUBTOTAL",
            "role": target_role,
            "source": None,
            "values": canonical_clone_v1(component_sum),
        },
        "role": target_role,
        "row_kind": selected["row_kind"],
        "sample_ids": canonical_clone_v1(selected["sample_ids"]),
        "source_key": selected["key"],
        "source_record": canonical_clone_v1(selected["source_record"]),
    }


def _local_trailing_subgroup_has_equal_vector_collision(
    evidence: Mapping[str, Any],
    equations: Sequence[Mapping[str, Any]],
    resolved: Mapping[str, Mapping[str, Any]],
    role_occurrences: Sequence[Mapping[str, Any]],
) -> bool:
    """Reject a receipt whose vector can name another declared accounting result."""

    receipt = evidence["receipt"]
    target_role = evidence["role"]
    scratch = canonical_clone_v1(resolved)
    scratch[target_role] = canonical_clone_v1(evidence["resolution"])
    for _pass in range(len(equations) + 1):
        changed = False
        for equation in equations:
            alternatives = [
                {
                    "component_roles": alternative["component_roles"],
                    "values": _sum_records(
                        [scratch[role] for role in alternative["component_roles"]]
                    ),
                }
                for alternative in equation["component_role_alternatives"]
                if all(role in scratch for role in alternative["component_roles"])
            ]
            distinct = {
                _exact_numeric_value_signature(alternative["values"]): alternative
                for alternative in alternatives
            }
            result_role = equation["result_role"]
            if result_role not in scratch and len(distinct) == 1:
                selected = next(iter(distinct.values()))
                scratch[result_role] = {
                    "component_roles": selected["component_roles"],
                    "resolution_kind": "DERIVED_EXACT_COLLISION_PROJECTION",
                    "role": result_role,
                    "source": None,
                    "values": selected["values"],
                }
                changed = True
        if not changed:
            break
    excluded_roles = {
        target_role,
        *receipt["component_roles"],
        *(
            occurrence["role"]
            for occurrence in role_occurrences
            if occurrence.get("occurrence_id") in receipt["nonadditive_occurrence_ids"]
        ),
    }
    target_values = evidence["resolution"]["values"]
    if any(
        role not in excluded_roles and _same_values(record["values"], target_values)
        for role, record in scratch.items()
    ):
        return True
    return any(
        equation["result_role"] != target_role
        and any(
            all(role in scratch for role in alternative["component_roles"])
            and _same_values(
                _sum_records([scratch[role] for role in alternative["component_roles"]]),
                target_values,
            )
            for alternative in equation["component_role_alternatives"]
        )
        for equation in equations
    )


def _legacy_unlabeled_exact_subtotal_for_equation(
    *,
    family_id: str,
    equation_record: Mapping[str, Any],
    numeric_sample_universe: Sequence[Mapping[str, Any]],
    reserved_source_keys: set[tuple[str, str | int]],
    resolved_by_role: Mapping[str, Mapping[str, Any]],
    role_occurrences: Sequence[Mapping[str, Any]],
    source_candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any] | None:
    """Preserve the reviewed V4 deposit/loan subtotal path unchanged."""

    target_role = equation_record.get("result_role")
    target = resolved_by_role.get(target_role)
    if (
        family_id != "INTERBANK_DEPOSITS_AND_LOANS"
        or target_role not in _UNLABELED_EXACT_SUBTOTAL_TARGET_ROLES
        or equation_record.get("status") != "DERIVED_EXACT_EXHAUSTIVE_COMPONENT_SUM"
        or not equation_record.get("component_roles_present")
        or equation_record.get("selected_trailing_candidate_ordinal") is not None
        or type(target) is not dict
        or target.get("source") is not None
        or target.get("resolution_kind") != "DERIVED_EXACT_COMPONENT_SUM"
        or target.get("component_roles") != equation_record["component_roles_present"]
        or type(target.get("values")) is not list
        or not target["values"]
    ):
        return None
    target_occurrences = [
        occurrence
        for occurrence in role_occurrences
        if occurrence.get("role") == target_role
        and str(occurrence.get("label_match", {}).get("match_kind", "")).startswith("EXACT_")
    ]
    if len(target_occurrences) > 1 or (
        target_role == "INTERBANK_LOAN_GROUP" and len(target_occurrences) != 1
    ):
        return None
    target_occurrence = target_occurrences[0] if target_occurrences else None
    if target_occurrence is None and len(equation_record["component_roles_present"]) < 2:
        return None
    target_match = target_occurrence.get("label_match") if target_occurrence is not None else None
    target_bbox = target_match.get("source_label_bbox") if type(target_match) is dict else None
    if target_occurrence is not None and (
        type(target_bbox) is not list
        or len(target_bbox) != 4
        or any(type(item) is not int for item in target_bbox)
    ):
        return None
    component_sample_ids = list(
        dict.fromkeys(
            sample_id
            for value in target["values"]
            for sample_id in value.get("source_sample_ids", [])
        )
    )
    sample_by_id = {sample["sample_id"]: sample for sample in numeric_sample_universe}
    component_samples = [sample_by_id.get(sample_id) for sample_id in component_sample_ids]
    if (
        not component_sample_ids
        or any(type(sample) is not dict for sample in component_samples)
        or any(
            sample["owner_kind"] in {"SOURCE_ONLY_INTERNAL_CLUSTER", "TRAILING_VALUE_ROW"}
            for sample in component_samples
        )
        or len({sample["page_sequence"] for sample in component_samples}) != 1
    ):
        return None
    page_sequence = component_samples[0]["page_sequence"]
    if target_match is not None and target_match["page_sequence"] != page_sequence:
        return None
    component_top = max(sample["bbox"][1] for sample in component_samples)
    component_bottom = max(sample["bbox"][3] for sample in component_samples)
    if target_bbox is not None and target_bbox[1] >= component_top:
        return None

    boundary_top: int | None = None
    if target_role == "INTERBANK_DEPOSIT_GROUP":
        later_loan_groups = [
            occurrence
            for occurrence in role_occurrences
            if occurrence.get("role") == "INTERBANK_LOAN_GROUP"
            and str(occurrence.get("label_match", {}).get("match_kind", "")).startswith("EXACT_")
            and occurrence["label_match"]["page_sequence"] == page_sequence
            and occurrence["label_match"]["source_label_bbox"][1] > component_top
        ]
        if len(later_loan_groups) != 1:
            return None
        boundary_top = later_loan_groups[0]["label_match"]["source_label_bbox"][1]

    interval_sources = [
        source
        for source in source_candidates
        if source["key"] not in reserved_source_keys
        and source["page_sequence"] == page_sequence
        and source["top"] > component_top
        and source["bottom"] > component_bottom
        and (boundary_top is None or source["top"] < boundary_top)
    ]
    if not interval_sources:
        return None
    first_top = min(source["top"] for source in interval_sources)
    first_sources = [source for source in interval_sources if source["top"] == first_top]
    if len(first_sources) != 1:
        return None
    selected = first_sources[0]
    if not selected["complete"] or not _same_values(selected["values"], target["values"]):
        return None
    if any(
        source["key"] != selected["key"]
        and source["complete"]
        and _same_values(source["values"], target["values"])
        for source in interval_sources
    ):
        return None

    disposition = _UNLABELED_EXACT_SUBTOTAL_CORROBORATION
    if target_role == "INTERBANK_LOAN_GROUP":
        deposit = resolved_by_role.get("INTERBANK_DEPOSIT_GROUP")
        if type(deposit) is not dict:
            return None
        root_component_sets = [
            [deposit, target],
            *(
                [deposit, target, resolved_by_role[provision_role]]
                for provision_role in (
                    "TOTAL_INTERBANK_PROVISION",
                    "INTERBANK_DEPOSIT_PROVISION",
                    "INTERBANK_LOAN_PROVISION",
                )
                if provision_role in resolved_by_role
            ),
        ]
        root_value_axes = [_sum_records(records) for records in root_component_sets]
        later_root_candidates = [
            source
            for source in source_candidates
            if source["key"] not in reserved_source_keys
            and source["key"] != selected["key"]
            and source["page_sequence"] == page_sequence
            and source["top"] > selected["top"]
            and source["complete"]
            and any(_same_values(source["values"], values) for values in root_value_axes)
            and not _same_values(source["values"], target["values"])
        ]
        if len(later_root_candidates) != 1:
            if not later_root_candidates and any(
                _same_values(values, target["values"]) for values in root_value_axes
            ):
                disposition = _UNLABELED_AMBIGUOUS_SUBTOTAL_DISPOSITION
            else:
                return None

    candidate_top = selected["top"]
    if target_role == "INTERBANK_DEPOSIT_GROUP":
        later_target_semantics = [
            occurrence
            for occurrence in role_occurrences
            if occurrence.get("role") in occurrence_v2._DEPOSIT_SEMANTIC_INTERVAL_ROLES
            and occurrence["label_match"]["page_sequence"] == page_sequence
            and candidate_top < occurrence["label_match"]["source_label_bbox"][1] < boundary_top
        ]
    else:
        later_target_semantics = [
            occurrence
            for occurrence in role_occurrences
            if occurrence.get("role")
            in {
                *occurrence_v2._LOAN_SEMANTIC_INTERVAL_ROLES,
                "INTERBANK_LOAN_GROUP",
            }
            and occurrence["label_match"]["page_sequence"] == page_sequence
            and occurrence["label_match"]["source_label_bbox"][1] > candidate_top
        ]
    if later_target_semantics:
        return None
    return {
        "candidate_ordinal": (
            selected["source_record"].get("candidate_ordinal")
            if selected["row_kind"] == "TRAILING_VALUE_ROW"
            else None
        ),
        "disposition": disposition,
        "occurrence_id": (
            target_occurrence["occurrence_id"] if target_occurrence is not None else None
        ),
        "role": target_role,
        "row_kind": selected["row_kind"],
        "sample_ids": canonical_clone_v1(selected["sample_ids"]),
        "source_key": selected["key"],
        "source_record": canonical_clone_v1(selected["source_record"]),
    }


def _unlabeled_exact_subtotal_for_equation(
    *,
    family_id: str,
    equation_record: Mapping[str, Any],
    numeric_sample_universe: Sequence[Mapping[str, Any]],
    reserved_source_keys: set[tuple[str, str | int]],
    resolved_by_role: Mapping[str, Mapping[str, Any]],
    role_occurrences: Sequence[Mapping[str, Any]],
    source_candidates: Sequence[Mapping[str, Any]],
    authenticated_extreme_margin_furniture_evidence: Sequence[Mapping[str, Any]] = (),
    equation_records: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Recognize one exact printed subtotal as coverage/corroboration only.

    The target remains the exact component-derived record; this projector never
    creates a schema role.  Legacy deposit/loan rules remain isolated above.
    Demand and term subgroups require their exact declared child axis plus the
    typed, replayed explicit deposit-total control observed in the reviewed
    Family-3 layout.  Demand additionally requires the next exact term sibling
    as its sealed stop.  A partial, labeled, duplicate, mismatching, reordered,
    cross-parent, or out-of-interval row keeps its ordinary source-only veto.
    """

    target_role = equation_record.get("result_role")
    if target_role in _UNLABELED_EXACT_SUBTOTAL_TARGET_ROLES:
        return _legacy_unlabeled_exact_subtotal_for_equation(
            family_id=family_id,
            equation_record=equation_record,
            numeric_sample_universe=numeric_sample_universe,
            reserved_source_keys=reserved_source_keys,
            resolved_by_role=resolved_by_role,
            role_occurrences=role_occurrences,
            source_candidates=source_candidates,
        )
    if target_role not in _SEALED_DEPOSIT_SUBGROUP_COMPONENT_ROLES:
        return None
    expected_component_roles = _SEALED_DEPOSIT_SUBGROUP_COMPONENT_ROLES[target_role]
    target = resolved_by_role.get(target_role)
    if (
        family_id != "INTERBANK_DEPOSITS_AND_LOANS"
        or equation_record.get("status") != "DERIVED_EXACT_EXHAUSTIVE_COMPONENT_SUM"
        or equation_record.get("component_roles_present") != expected_component_roles
        or equation_record.get("selected_trailing_candidate_ordinal") is not None
        or type(target) is not dict
        or target.get("source") is not None
        or target.get("resolution_kind") != "DERIVED_EXACT_COMPONENT_SUM"
        or target.get("component_roles") != equation_record["component_roles_present"]
        or type(target.get("values")) is not list
        or not target["values"]
    ):
        return None
    all_target_occurrences = [
        occurrence for occurrence in role_occurrences if occurrence.get("role") == target_role
    ]
    target_occurrences = [
        occurrence
        for occurrence in all_target_occurrences
        if occurrence.get("role_kind") == "STRUCTURAL_GROUP"
        and occurrence_v2._match_has_effective_exact_source_authority(  # noqa: SLF001
            occurrence.get("label_match", {})
        )
    ]
    if (
        len(all_target_occurrences) != 1
        or len(target_occurrences) != 1
        or target_occurrences[0].get("has_bound_value_row") is not False
    ):
        return None
    target_occurrence = target_occurrences[0]
    target_match = target_occurrence.get("label_match")
    target_bbox = target_match.get("source_label_bbox") if type(target_match) is dict else None
    if (
        type(target_bbox) is not list
        or len(target_bbox) != 4
        or any(type(item) is not int for item in target_bbox)
    ):
        return None
    component_sample_ids = list(
        dict.fromkeys(
            sample_id
            for value in target["values"]
            for sample_id in value.get("source_sample_ids", [])
        )
    )
    sample_by_id = {sample["sample_id"]: sample for sample in numeric_sample_universe}
    component_samples = [sample_by_id.get(sample_id) for sample_id in component_sample_ids]
    if (
        not component_sample_ids
        or any(type(sample) is not dict for sample in component_samples)
        or any(
            sample["owner_kind"] in {"SOURCE_ONLY_INTERNAL_CLUSTER", "TRAILING_VALUE_ROW"}
            for sample in component_samples
        )
        or len({sample["page_sequence"] for sample in component_samples}) != 1
    ):
        return None
    page_sequence = component_samples[0]["page_sequence"]
    if target_match["page_sequence"] != page_sequence:
        return None
    component_top = max(sample["bbox"][1] for sample in component_samples)
    component_bottom = max(sample["bbox"][3] for sample in component_samples)
    if target_bbox is not None and target_bbox[1] >= component_top:
        return None

    occurrence_by_id = {
        occurrence["occurrence_id"]: occurrence
        for occurrence in role_occurrences
        if type(occurrence.get("occurrence_id")) is str
    }
    component_roles = set(equation_record["component_roles_present"])
    component_occurrences = [
        occurrence
        for occurrence in role_occurrences
        if occurrence.get("role") in component_roles
        and occurrence.get("label_match", {}).get("page_sequence") == page_sequence
    ]
    if any(
        len(
            [
                occurrence
                for occurrence in component_occurrences
                if occurrence["role"] == component_role
            ]
        )
        != 1
        or not occurrence_v2._match_has_effective_exact_source_authority(  # noqa: SLF001
            next(
                occurrence
                for occurrence in component_occurrences
                if occurrence["role"] == component_role
            )["label_match"]
        )
        for component_role in component_roles
    ):
        return None
    component_occurrence_ids = {occurrence["occurrence_id"] for occurrence in component_occurrences}

    def descends_from_target(occurrence: Mapping[str, Any]) -> bool:
        if target_occurrence is None:
            return False
        cursor = occurrence
        visited: set[str] = set()
        while type(owner_id := cursor.get("scope_owner_occurrence_id")) is str:
            if owner_id == target_occurrence["occurrence_id"]:
                return True
            if owner_id in visited or owner_id not in occurrence_by_id:
                return False
            visited.add(owner_id)
            cursor = occurrence_by_id[owner_id]
        return False

    component_owned_sample_ids = {
        sample["sample_id"]
        for sample in numeric_sample_universe
        if sample.get("owner_kind") == "ROLE_OCCURRENCE"
        and sample.get("owner_id") in component_occurrence_ids
    }
    if (
        any(not descends_from_target(occurrence) for occurrence in component_occurrences)
        or (
            target_role == "DEMAND_DEPOSIT_GROUP"
            and any(
                occurrence.get("scope_owner_occurrence_id") != target_occurrence["occurrence_id"]
                or occurrence.get("scope_owner_role") != target_role
                or occurrence.get("role_kind") != "ADDITIVE_CHILD"
                or occurrence.get("has_bound_value_row") is not True
                for occurrence in component_occurrences
            )
        )
        or set(component_sample_ids) != component_owned_sample_ids
    ):
        return None

    counterpart_role = (
        "TERM_DEPOSIT_GROUP" if target_role == "DEMAND_DEPOSIT_GROUP" else "DEMAND_DEPOSIT_GROUP"
    )
    counterpart = resolved_by_role.get(counterpart_role)
    if type(counterpart) is not dict or _same_values(
        counterpart.get("values", []), target["values"]
    ):
        return None

    term_boundary: Mapping[str, Any] | None = None
    if target_role == "DEMAND_DEPOSIT_GROUP":
        term_boundaries = [
            occurrence
            for occurrence in role_occurrences
            if occurrence.get("role") == "TERM_DEPOSIT_GROUP"
            and occurrence.get("role_kind") == "STRUCTURAL_GROUP"
            and occurrence.get("has_bound_value_row") is False
            and occurrence_v2._match_has_effective_exact_source_authority(  # noqa: SLF001
                occurrence.get("label_match", {})
            )
        ]
        if len(term_boundaries) != 1:
            return None
        term_boundary = term_boundaries[0]
        term_match = term_boundary["label_match"]
        target_parent_id = target_occurrence.get("scope_owner_occurrence_id")
        root_siblings_between = [
            occurrence
            for occurrence in role_occurrences
            if occurrence.get("scope_owner_occurrence_id") == target_parent_id
            and occurrence.get("label_match", {}).get("page_sequence") == page_sequence
            and target_match["document_line_ordinal"]
            < occurrence.get("label_match", {}).get("document_line_ordinal", -1)
            < term_match["document_line_ordinal"]
        ]
        if (
            type(target_parent_id) is not str
            or not target_parent_id.startswith("aforav2:root:")
            or target_occurrence.get("scope_owner_role") is not None
            or term_boundary.get("scope_owner_occurrence_id") != target_parent_id
            or term_boundary.get("scope_owner_role") is not None
            or term_match.get("page_sequence") != page_sequence
            or term_match.get("document_line_ordinal", -1) <= target_match["document_line_ordinal"]
            or root_siblings_between
        ):
            return None

    explicit_deposit_total_occurrences = [
        occurrence
        for occurrence in role_occurrences
        if occurrence.get("role")
        in {
            "EXPLICIT_INTERBANK_DEPOSIT_TOTAL",
            "EXPLICIT_INTERBANK_DEPOSIT_TOTAL_AMBIGUOUS",
        }
        and occurrence.get("label_match", {}).get("page_sequence") == page_sequence
    ]
    if (
        len(explicit_deposit_total_occurrences) != 1
        or explicit_deposit_total_occurrences[0].get("role") != "EXPLICIT_INTERBANK_DEPOSIT_TOTAL"
    ):
        return None
    deposit_boundary = explicit_deposit_total_occurrences[0]
    deposit_boundary_match = deposit_boundary["label_match"]
    deposit_boundary_bbox = deposit_boundary_match.get("source_label_bbox")
    boundary_binding = deposit_boundary.get("source_scope_binding")
    prior_deposit_groups = [
        occurrence
        for occurrence in role_occurrences
        if occurrence.get("role") == "INTERBANK_DEPOSIT_GROUP"
        and occurrence.get("label_match", {}).get("page_sequence") == page_sequence
        and occurrence["label_match"]["document_line_ordinal"]
        < target_match["document_line_ordinal"]
    ]
    nearest_deposit_ordinal = max(
        (occurrence["label_match"]["document_line_ordinal"] for occurrence in prior_deposit_groups),
        default=None,
    )
    nearest_deposit_groups = [
        occurrence
        for occurrence in prior_deposit_groups
        if occurrence["label_match"]["document_line_ordinal"] == nearest_deposit_ordinal
    ]
    deposit_owner = nearest_deposit_groups[0] if len(nearest_deposit_groups) == 1 else None
    target_root_scope_id = target_occurrence.get("scope_owner_occurrence_id")
    deposit_root_scope_id = (
        deposit_owner.get("scope_owner_occurrence_id") if type(deposit_owner) is dict else None
    )
    if (
        type(deposit_boundary_bbox) is not list
        or len(deposit_boundary_bbox) != 4
        or any(type(item) is not int for item in deposit_boundary_bbox)
        or deposit_boundary_bbox[1] <= component_top
        or not occurrence_v2._match_has_effective_exact_source_authority(  # noqa: SLF001
            deposit_boundary_match
        )
        or type(boundary_binding) is not dict
        or boundary_binding.get("status") != occurrence_v2._SOURCE_SCOPE_BINDING_STATUS  # noqa: SLF001
        or boundary_binding.get("binding_kind") != occurrence_v2._EXPLICIT_GROUP_TOTAL_BINDING_KIND  # noqa: SLF001
        or boundary_binding.get("source_scope_role") != "INTERBANK_DEPOSIT_GROUP"
        or boundary_binding.get("target_role") != "EXPLICIT_INTERBANK_DEPOSIT_TOTAL"
        or deposit_boundary.get("scope_owner_role") != "INTERBANK_DEPOSIT_GROUP"
        or deposit_owner is None
        or not occurrence_v2._match_has_effective_exact_source_authority(  # noqa: SLF001
            deposit_owner["label_match"]
        )
        or deposit_boundary.get("scope_owner_occurrence_id") != deposit_owner["occurrence_id"]
        or boundary_binding.get("geometry")
        != {
            "anchor_occurrence_id": deposit_owner["occurrence_id"],
            "status": occurrence_v2._EXPLICIT_GROUP_TOTAL_PARENT_GEOMETRY_STATUS,  # noqa: SLF001
        }
        or type(target_root_scope_id) is not str
        or not target_root_scope_id
        or target_root_scope_id != deposit_root_scope_id
        or target_occurrence.get("scope_owner_role") is not None
        or deposit_owner.get("scope_owner_role") is not None
        or not (
            deposit_owner["label_match"]["document_line_ordinal"]
            < target_match["document_line_ordinal"]
            < deposit_boundary_match["document_line_ordinal"]
        )
        or (
            term_boundary is not None
            and term_boundary["label_match"]["document_line_ordinal"]
            >= deposit_boundary_match["document_line_ordinal"]
        )
        or boundary_binding.get("interval", {}).get("start_document_line_ordinal")
        != deposit_owner["label_match"]["document_line_ordinal"]
        or deposit_boundary_match["document_line_ordinal"]
        >= boundary_binding.get("interval", {}).get("end_document_line_ordinal_exclusive", -1)
    ):
        return None
    selection_boundary = (
        term_boundary if target_role == "DEMAND_DEPOSIT_GROUP" else deposit_boundary
    )
    selection_boundary_match = selection_boundary["label_match"]
    selection_boundary_bbox = selection_boundary_match.get("source_label_bbox")
    if (
        type(selection_boundary_bbox) is not list
        or len(selection_boundary_bbox) != 4
        or any(type(item) is not int for item in selection_boundary_bbox)
        or selection_boundary_bbox[1] <= component_bottom
    ):
        return None
    boundary_top = selection_boundary_bbox[1]

    deposit = resolved_by_role.get("INTERBANK_DEPOSIT_GROUP")
    deposit_equations = [
        equation
        for equation in equation_records or ()
        if equation.get("result_role") == "INTERBANK_DEPOSIT_GROUP"
    ]
    boundary_samples = [
        sample
        for sample in numeric_sample_universe
        if sample.get("owner_kind") == "ROLE_OCCURRENCE"
        and sample.get("owner_id") == deposit_boundary["occurrence_id"]
    ]
    boundary_values = [
        {
            "column_ordinal": sample["column_ordinal"],
            "number": _number(sample),
            "source_sample_ids": [sample["sample_id"]],
        }
        for sample in sorted(boundary_samples, key=lambda sample: sample["column_ordinal"])
    ]
    if (
        type(deposit) is not dict
        or len(deposit_equations) != 1
        or deposit_equations[0].get("status")
        != "VISIBLE_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS"
        or not {
            "DEMAND_DEPOSIT_GROUP",
            "TERM_DEPOSIT_GROUP",
        }
        <= set(deposit_equations[0].get("component_roles_present", []))
        or deposit.get("resolution_kind") != "VISIBLE_SOURCE_ROLE_CORROBORATED_BY_COMPONENTS"
        or deposit.get("component_roles") != deposit_equations[0]["component_roles_present"]
        or deposit.get("source", {}).get("kind") != "ROLE_ROW"
        or deposit.get("source", {}).get("record", {}).get("status") != "VISIBLE_VALUE_LANES_BOUND"
        or deposit.get("source", {}).get("record", {}).get("label_match", {}).get("occurrence_id")
        != deposit_boundary["occurrence_id"]
        or deposit_boundary.get("has_bound_value_row") is not True
        or _same_values(deposit.get("values", []), target["values"])
        or not _same_values(boundary_values, deposit.get("values", []))
    ):
        return None

    interval_sources = [
        source
        for source in source_candidates
        if source["key"] not in reserved_source_keys
        and source["page_sequence"] == page_sequence
        and source["top"] > component_top
        and source["bottom"] > component_bottom
        and source["top"] < boundary_top
    ]
    if not interval_sources:
        return None
    first_top = min(source["top"] for source in interval_sources)
    first_sources = [source for source in interval_sources if source["top"] == first_top]
    if len(first_sources) != 1:
        return None
    selected = first_sources[0]
    if not selected["complete"] or not _same_values(selected["values"], target["values"]):
        return None
    if target_role != "INTERBANK_LOAN_GROUP" and len(interval_sources) != 1:
        return None
    if any(
        source["key"] != selected["key"] and _same_values(source["values"], target["values"])
        for source in interval_sources
    ):
        return None
    if target_role == "DEMAND_DEPOSIT_GROUP":
        selected_samples = [sample_by_id.get(sample_id) for sample_id in selected["sample_ids"]]
        selected_lines = sorted(
            sample["line_ordinal"] for sample in selected_samples if type(sample) is dict
        )
        component_lines = [sample["line_ordinal"] for sample in component_samples]
        source_record = selected["source_record"]
        source_cluster_id = source_record.get("cluster_id")
        boundary_source_line = selection_boundary_match.get("source_line_index")
        component_last_line = max(component_lines)
        if (
            selected["row_kind"] != "INTERNAL_UNASSIGNED_NUMERIC_CLUSTER"
            or type(source_cluster_id) is not str
            or source_record.get("status") != occurrence_v2._INTERNAL_UNASSIGNED_CLUSTER_STATUS
            or source_record.get("label_lane_status") != occurrence_v2._UNLABELED_LABEL_LANE_STATUS
            or len(selected_samples) != len(selected["sample_ids"])
            or any(type(sample) is not dict for sample in selected_samples)
            or any(
                sample.get("owner_kind") != "SOURCE_ONLY_INTERNAL_CLUSTER"
                or sample.get("owner_id") != source_cluster_id
                for sample in selected_samples
            )
            or type(boundary_source_line) is not int
            or selected_lines != list(range(min(selected_lines), max(selected_lines) + 1))
            or min(selected_lines) <= component_last_line
            or max(selected_lines) >= boundary_source_line
        ):
            return None
        intervening_line_ordinals = {
            *range(component_last_line + 1, min(selected_lines)),
            *range(max(selected_lines) + 1, boundary_source_line),
        }
        if intervening_line_ordinals:
            qualifying_furniture = [
                evidence
                for evidence in authenticated_extreme_margin_furniture_evidence
                if evidence.get("status") == occurrence_v2._EXTREME_MARGIN_FURNITURE_V2_STATUS
                and evidence.get("page_sequence") == page_sequence
                and set(evidence.get("margin_band", {}).get("qualifying_peer_line_ordinals", []))
                == intervening_line_ordinals
                and evidence.get("candidate_crop_proof", {})
                .get("source_line_record", {})
                .get("line_ordinal")
                == boundary_source_line + 1
                and (furniture_sample := sample_by_id.get(evidence.get("sample_id"))) is not None
                and furniture_sample.get("owner_kind")
                == occurrence_v2._EXTREME_MARGIN_FURNITURE_OWNER_KIND
                and furniture_sample.get("owner_id") == evidence.get("evidence_id")
            ]
            if len(qualifying_furniture) != 1:
                return None

    disposition = _UNLABELED_EXACT_SUBTOTAL_CORROBORATION
    if target_role == "INTERBANK_LOAN_GROUP":
        deposit = resolved_by_role.get("INTERBANK_DEPOSIT_GROUP")
        if type(deposit) is not dict:
            return None
        root_component_sets = [
            [deposit, target],
            *(
                [deposit, target, resolved_by_role[provision_role]]
                for provision_role in (
                    "TOTAL_INTERBANK_PROVISION",
                    "INTERBANK_DEPOSIT_PROVISION",
                    "INTERBANK_LOAN_PROVISION",
                )
                if provision_role in resolved_by_role
            ),
        ]
        root_value_axes = [_sum_records(records) for records in root_component_sets]
        later_root_candidates = [
            source
            for source in source_candidates
            if source["key"] not in reserved_source_keys
            and source["key"] != selected["key"]
            and source["page_sequence"] == page_sequence
            and source["top"] > selected["top"]
            and source["complete"]
            and any(_same_values(source["values"], values) for values in root_value_axes)
            and not _same_values(source["values"], target["values"])
        ]
        if len(later_root_candidates) != 1:
            if not later_root_candidates and any(
                _same_values(values, target["values"]) for values in root_value_axes
            ):
                disposition = _UNLABELED_AMBIGUOUS_SUBTOTAL_DISPOSITION
            else:
                return None

    candidate_top = selected["top"]
    later_target_semantics = [
        occurrence
        for occurrence in component_occurrences
        if occurrence["label_match"]["source_label_bbox"][1] > candidate_top
        and (
            boundary_top is None or occurrence["label_match"]["source_label_bbox"][1] < boundary_top
        )
    ]
    if later_target_semantics:
        return None
    return {
        "candidate_ordinal": (
            selected["source_record"].get("candidate_ordinal")
            if selected["row_kind"] == "TRAILING_VALUE_ROW"
            else None
        ),
        "disposition": disposition,
        "occurrence_id": (
            target_occurrence["occurrence_id"] if target_occurrence is not None else None
        ),
        "role": target_role,
        "row_kind": selected["row_kind"],
        "sample_ids": canonical_clone_v1(selected["sample_ids"]),
        "source_key": selected["key"],
        "source_record": canonical_clone_v1(selected["source_record"]),
    }


def _validate_unlabeled_exact_subtotal_receipts(value: Mapping[str, Any]) -> None:
    trailing_rows = [
        receipt["source_record"]
        for receipt in value["coverage_receipt"]
        if receipt["row_kind"] == "TRAILING_VALUE_ROW"
    ]
    source_candidates = _numeric_source_candidate_axis(
        value["numeric_sample_universe"],
        value["internal_unassigned_numeric_clusters"],
        trailing_rows,
    )
    resolved_by_role = {record["role"]: record for record in value["resolved_roles"]}
    reserved: set[tuple[str, str | int]] = set()
    expected_by_key: dict[tuple[str, str | int], Mapping[str, Any]] = {}
    for equation in value["equations"]["global"]:
        if equation["result_role"] in _SEALED_DEPOSIT_SUBGROUP_COMPONENT_ROLES:
            continue
        evidence = _unlabeled_exact_subtotal_for_equation(
            equation_record=equation,
            family_id=value["family_id"],
            numeric_sample_universe=value["numeric_sample_universe"],
            reserved_source_keys=reserved,
            resolved_by_role=resolved_by_role,
            role_occurrences=value["role_occurrences"],
            source_candidates=source_candidates,
            authenticated_extreme_margin_furniture_evidence=value[
                "authenticated_extreme_margin_furniture_evidence"
            ],
            equation_records=value["equations"]["global"],
        )
        if evidence is not None:
            reserved.add(evidence["source_key"])
            expected_by_key[evidence["source_key"]] = evidence
    for subgroup_role in _SEALED_DEPOSIT_SUBGROUP_COMPONENT_ROLES:
        subgroup_equations = [
            equation
            for equation in value["equations"]["global"]
            if equation["result_role"] == subgroup_role
        ]
        if len(subgroup_equations) != 1:
            continue
        subgroup_evidence = _unlabeled_exact_subtotal_for_equation(
            equation_record=subgroup_equations[0],
            family_id=value["family_id"],
            numeric_sample_universe=value["numeric_sample_universe"],
            reserved_source_keys=set(),
            resolved_by_role=resolved_by_role,
            role_occurrences=value["role_occurrences"],
            source_candidates=source_candidates,
            authenticated_extreme_margin_furniture_evidence=value[
                "authenticated_extreme_margin_furniture_evidence"
            ],
            equation_records=value["equations"]["global"],
        )
        if subgroup_evidence is not None:
            source_key = subgroup_evidence["source_key"]
            if source_key in expected_by_key:
                expected_by_key.pop(source_key)
            else:
                expected_by_key[source_key] = subgroup_evidence
    actual_by_key: dict[tuple[str, str | int], Mapping[str, Any]] = {}
    for receipt in value["coverage_receipt"]:
        if receipt["disposition"] not in _UNLABELED_SUBTOTAL_DISPOSITIONS:
            continue
        key = (
            ("cluster", receipt["source_record"].get("cluster_id"))
            if receipt["row_kind"] == "INTERNAL_UNASSIGNED_NUMERIC_CLUSTER"
            else ("trailing", receipt["candidate_ordinal"])
        )
        if key in actual_by_key:
            raise _error("unlabeled exact subtotal source is owned more than once")
        actual_by_key[key] = receipt
    if set(actual_by_key) != set(expected_by_key):
        raise _error("unlabeled exact subtotal designation did not replay")
    for key, expected in expected_by_key.items():
        actual = actual_by_key[key]
        expected_coverage_id = (
            "ashtcv2:coverage:unlabeled-exact-subtotal:"
            + expected["role"]
            + (
                f":trailing:{expected['candidate_ordinal']}"
                if expected["row_kind"] == "TRAILING_VALUE_ROW"
                else ":cluster:" + expected["source_record"]["cluster_id"]
            )
        )
        if (
            actual["coverage_id"] != expected_coverage_id
            or actual["disposition"] != expected["disposition"]
            or actual["candidate_ordinal"] != expected["candidate_ordinal"]
            or actual["occurrence_id"] != expected["occurrence_id"]
            or actual["role"] != expected["role"]
            or actual["row_kind"] != expected["row_kind"]
            or actual["sample_ids"] != expected["sample_ids"]
            or not same_typed_json_v1(actual["source_record"], expected["source_record"])
        ):
            raise _error("unlabeled exact subtotal receipt or boundary proof drifted")
        if expected["disposition"] == _UNLABELED_AMBIGUOUS_SUBTOTAL_DISPOSITION and (
            "AMBIGUOUS_UNLABELED_SUBTOTAL_SOURCE:"
            + expected["role"]
            + ":"
            + str(key[0])
            + ":"
            + str(key[1])
            not in value["unresolved_reasons"]
        ):
            raise _error("ambiguous unlabeled subtotal receipt did not veto closure")


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
        "covered_numeric_sample_count": sum(
            len(record["sample_ids"]) for record in coverage_receipt
        ),
        "resolved_role_count": len(resolved),
        "visible_corroborated_role_count": sum(
            record["resolution_kind"]
            in {
                "VISIBLE_SOURCE_ROLE_ROUNDING_CORROBORATED_BY_COMPONENTS",
                "VISIBLE_SOURCE_ROLE_CORROBORATED_BY_COMPONENTS",
                "VISIBLE_TRAILING_TOTAL_ROUNDING_CORROBORATED_BY_COMPONENTS",
                "VISIBLE_TRAILING_TOTAL_CORROBORATED_BY_COMPONENTS",
            }
            for record in resolved
        ),
        "unresolved_coverage_occurrence_count": sum(
            record["disposition"].startswith("UNRESOLVED")
            or record["disposition"].startswith("UNBOUND")
            for record in coverage_receipt
        ),
        "source_only_numeric_sample_count": sum(
            len(record["sample_ids"])
            for record in coverage_receipt
            if record["disposition"]
            in {
                "UNRESOLVED_OFF_LANE_NUMERIC_SOURCE_ONLY",
                "UNRESOLVED_SOURCE_ONLY_INTERNAL_NUMERIC_CLUSTER",
                "UNRESOLVED_SOURCE_ONLY_SCHEMA_INELIGIBLE_ROLE",
                _UNLABELED_AMBIGUOUS_SUBTOTAL_DISPOSITION,
            }
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


def _validate_residual_evidence_axis(evidence_axis: Any, *, result_role: str) -> None:
    if type(evidence_axis) is not list:
        raise _error("scoped hierarchical typed residual evidence axis drifted")
    keys = []
    for evidence in evidence_axis:
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
            or evidence["result_role"] != result_role
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
            or len(evidence["component_roles"]) != len(set(evidence["component_roles"]))
            or any(type(role) is not str or not role for role in evidence["component_roles"])
            or type(evidence["lanes"]) is not list
            or not evidence["lanes"]
        ):
            raise _error("scoped hierarchical typed residual evidence drifted")
        keys.append((evidence["candidate_ordinal"], tuple(evidence["component_roles"])))
        for expected_lane, lane in enumerate(evidence["lanes"]):
            component_number = lane.get("component_sum_number") if type(lane) is dict else None
            printed_number = lane.get("printed_result_number") if type(lane) is dict else None
            residual_number = lane.get("residual_number") if type(lane) is dict else None
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
                or component_number["percentage_mark_present"]
                is not printed_number["percentage_mark_present"]
                or not same_typed_json_v1(
                    residual_number,
                    _canonical_number(
                        printed_number["coefficient"]
                        * 10
                        ** max(
                            0,
                            component_number["scale"] - printed_number["scale"],
                        )
                        - component_number["coefficient"]
                        * 10
                        ** max(
                            0,
                            printed_number["scale"] - component_number["scale"],
                        ),
                        max(printed_number["scale"], component_number["scale"]),
                        printed_number["percentage_mark_present"],
                    ),
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
    if len(keys) != len(set(keys)):
        raise _error("scoped hierarchical residual evidence ownership repeats")


def _validate_rounding_evidence_axis(
    evidence_axis: Any,
    *,
    local_result_occurrence_id: str | None,
    numeric_sample_by_id: Mapping[str, Mapping[str, Any]],
    resolved_by_role: Mapping[str, Mapping[str, Any]],
    residual_axis: Sequence[Mapping[str, Any]],
    role_occurrence_by_id: Mapping[str, Mapping[str, Any]],
    result_role: str,
    visible_result_roles: set[str],
) -> None:
    if type(evidence_axis) is not list:
        raise _error("scoped hierarchical rounding evidence axis drifted")
    residual_by_key = {
        (evidence["candidate_ordinal"], tuple(evidence["component_roles"])): evidence
        for evidence in residual_axis
    }
    keys = []
    for evidence in evidence_axis:
        if (
            type(evidence) is not dict
            or set(evidence)
            != {
                "candidate_ordinal",
                "component_roles",
                "lanes",
                "policy",
                "printed_result_owner",
                "result_role",
                "status",
            }
            or evidence["result_role"] != result_role
            or type(evidence["printed_result_owner"]) is not dict
            or set(evidence["printed_result_owner"])
            != {"candidate_ordinal", "occurrence_id", "role", "source_kind"}
            or evidence["policy"]
            != (
                "RESULT_AND_NON_DASH_COMPONENTS_SIGNED_INTEGER_DISPLAY_UNIT;"
                "AUTHENTICATED_DASH_ZERO_EXACT_ZERO_EXCLUDED_FROM_ROUNDING_COUNT;"
                "SAME_NONZERO_RESULT_SUM_SIGN;2*ABS(PRINTED_MINUS_COMPONENT_SUM)<="
                "INDEPENDENTLY_PRINTED_NUMERIC_COMPONENT_COUNT+1"
            )
            or (
                evidence["candidate_ordinal"] is not None
                and (
                    type(evidence["candidate_ordinal"]) is not int
                    or evidence["candidate_ordinal"] < 0
                )
            )
            or type(evidence["component_roles"]) is not list
            or not evidence["component_roles"]
            or len(evidence["component_roles"]) != len(set(evidence["component_roles"]))
            or any(type(role) is not str or not role for role in evidence["component_roles"])
            or type(evidence["lanes"]) is not list
            or not evidence["lanes"]
            or evidence["status"]
            not in {
                "ROUNDING_BOUND_SATISFIED_ALL_LANES",
                "ROUNDING_BOUND_EXCEEDED_AT_LEAST_ONE_LANE",
            }
        ):
            raise _error("scoped hierarchical rounding assessment drifted")
        key = (evidence["candidate_ordinal"], tuple(evidence["component_roles"]))
        keys.append(key)
        residual = residual_by_key.get(key)
        if type(residual) is not dict or len(residual["lanes"]) != len(evidence["lanes"]):
            raise _error("rounding assessment lost its exact typed residual evidence")
        lane_statuses = []
        printed_owner = evidence["printed_result_owner"]
        if printed_owner["source_kind"] == "TRAILING_VALUE_ROW":
            printed_owner_valid = (
                printed_owner["candidate_ordinal"] == evidence["candidate_ordinal"]
                and type(printed_owner["candidate_ordinal"]) is int
                and printed_owner["occurrence_id"] is None
                and printed_owner["role"] is None
            )
        elif printed_owner["source_kind"] == "ROLE_ROW":
            owner_occurrence = role_occurrence_by_id.get(printed_owner["occurrence_id"])
            printed_owner_valid = (
                evidence["candidate_ordinal"] is None
                and printed_owner["candidate_ordinal"] is None
                and type(owner_occurrence) is dict
                and owner_occurrence.get("role") == printed_owner["role"]
                and printed_owner["role"] in visible_result_roles
                and (
                    local_result_occurrence_id is None
                    or printed_owner["occurrence_id"] == local_result_occurrence_id
                )
            )
        else:
            printed_owner_valid = False
        if not printed_owner_valid:
            raise _error("rounding printed result owner receipt drifted")
        for expected_lane, (lane, residual_lane) in enumerate(
            zip(evidence["lanes"], residual["lanes"], strict=True)
        ):
            number = lane.get("residual_number") if type(lane) is dict else None
            component_samples = residual_lane["component_source_sample_ids"]
            printed_samples = residual_lane["printed_result_source_sample_ids"]
            expected_source_count = len(component_samples)
            printed_component_cells = (
                lane.get("printed_component_cells") if type(lane) is dict else None
            )
            printed_result_cell = lane.get("printed_result_cell") if type(lane) is dict else None
            component_universe_samples = [
                numeric_sample_by_id.get(sample_id) for sample_id in component_samples
            ]
            component_classifications = [
                sample.get("parsed_token", {}).get("classification")
                if type(sample) is dict
                else None
                for sample in component_universe_samples
            ]
            numeric_component_count = sum(
                classification == "SIGNED_NUMBER" for classification in component_classifications
            )
            if (
                type(lane) is not dict
                or set(lane)
                != {
                    "bound_component_count_plus_one",
                    "column_ordinal",
                    "independently_printed_component_count",
                    "printed_component_cells",
                    "printed_result_cell",
                    "residual_number",
                    "status",
                    "twice_absolute_residual",
                }
                or lane["column_ordinal"] != expected_lane
                or type(number) is not dict
                or set(number) != {"coefficient", "percentage_mark_present", "scale"}
                or type(number["coefficient"]) is not int
                or number["percentage_mark_present"] is not False
                or number["scale"] != 0
                or not same_typed_json_v1(number, residual_lane["residual_number"])
                or residual_lane["component_sum_number"]["percentage_mark_present"] is not False
                or residual_lane["component_sum_number"]["scale"] != 0
                or residual_lane["printed_result_number"]["percentage_mark_present"] is not False
                or residual_lane["printed_result_number"]["scale"] != 0
                or len(printed_samples) != 1
                or set(printed_samples) & set(component_samples)
                or type(printed_component_cells) is not list
                or len(printed_component_cells) != expected_source_count
                or any(
                    type(cell) is not dict
                    or set(cell) != {"number", "source_sample_id"}
                    or type(cell["source_sample_id"]) is not str
                    or not cell["source_sample_id"]
                    or type(cell["number"]) is not dict
                    or set(cell["number"]) != {"coefficient", "percentage_mark_present", "scale"}
                    or type(cell["number"]["coefficient"]) is not int
                    or cell["number"]["percentage_mark_present"] is not False
                    or cell["number"]["scale"] != 0
                    for cell in printed_component_cells
                )
                or [cell["source_sample_id"] for cell in printed_component_cells]
                != component_samples
                or sum(cell["number"]["coefficient"] for cell in printed_component_cells)
                != residual_lane["component_sum_number"]["coefficient"]
                or type(printed_result_cell) is not dict
                or set(printed_result_cell) != {"number", "source_sample_id"}
                or printed_result_cell["source_sample_id"] != printed_samples[0]
                or not same_typed_json_v1(
                    printed_result_cell["number"], residual_lane["printed_result_number"]
                )
                or (
                    residual_lane["printed_result_number"]["coefficient"] != 0
                    and residual_lane["component_sum_number"]["coefficient"] != 0
                    and (residual_lane["printed_result_number"]["coefficient"] > 0)
                    is not (residual_lane["component_sum_number"]["coefficient"] > 0)
                )
                or type(lane["independently_printed_component_count"]) is not int
                or numeric_component_count < 1
                or any(
                    classification not in {"DASH_ZERO", "SIGNED_NUMBER"}
                    for classification in component_classifications
                )
                or lane["independently_printed_component_count"] != numeric_component_count
                or type(lane["bound_component_count_plus_one"]) is not int
                or lane["bound_component_count_plus_one"] != numeric_component_count + 1
                or type(lane["twice_absolute_residual"]) is not int
                or lane["twice_absolute_residual"] != 2 * abs(number["coefficient"])
                or lane["status"]
                != (
                    "WITHIN_INTEGER_DISPLAY_UNIT_ROUNDING_BOUND"
                    if lane["twice_absolute_residual"] <= lane["bound_component_count_plus_one"]
                    else "OVER_INTEGER_DISPLAY_UNIT_ROUNDING_BOUND"
                )
            ):
                raise _error("scoped hierarchical integer rounding lane drifted")
            component_ids = [cell["source_sample_id"] for cell in printed_component_cells]
            if local_result_occurrence_id is None:
                expected_component_ids = []
                for component_role in evidence["component_roles"]:
                    component_record = resolved_by_role.get(component_role)
                    component_values = (
                        component_record.get("values") if type(component_record) is dict else None
                    )
                    if type(component_values) is not list or expected_lane >= len(component_values):
                        raise _error("rounding component role lost its resolved source sample axis")
                    expected_component_ids.extend(
                        component_values[expected_lane]["source_sample_ids"]
                    )
            else:
                expected_component_ids = []
                for component_role in evidence["component_roles"]:
                    owners = [
                        occurrence
                        for occurrence in role_occurrence_by_id.values()
                        if occurrence.get("role") == component_role
                        and occurrence.get("scope_owner_occurrence_id")
                        == local_result_occurrence_id
                    ]
                    if len(owners) != 1:
                        raise _error("local rounding component scope is not one exact occurrence")
                    owner_id = owners[0]["occurrence_id"]
                    owned_lane_samples = [
                        sample["sample_id"]
                        for sample in numeric_sample_by_id.values()
                        if sample.get("owner_kind") == "ROLE_OCCURRENCE"
                        and sample.get("owner_id") == owner_id
                        and sample.get("column_ordinal") == expected_lane
                    ]
                    if len(owned_lane_samples) != 1:
                        raise _error(
                            "local rounding component occurrence lost one exact lane sample"
                        )
                    expected_component_ids.extend(owned_lane_samples)
            if component_ids != expected_component_ids:
                raise _error("rounding component count is not derived from selected source roles")
            for cell in printed_component_cells:
                sample = numeric_sample_by_id.get(cell["source_sample_id"])
                parsed = sample.get("parsed_token") if type(sample) is dict else None
                sample_number = (
                    {
                        "coefficient": parsed.get("coefficient"),
                        "percentage_mark_present": parsed.get("percentage_mark_present"),
                        "scale": parsed.get("scale"),
                    }
                    if type(parsed) is dict
                    else None
                )
                if (
                    type(sample) is not dict
                    or sample.get("column_ordinal") != expected_lane
                    or type(parsed) is not dict
                    or parsed.get("classification") not in {"DASH_ZERO", "SIGNED_NUMBER"}
                    or (
                        parsed.get("classification") == "DASH_ZERO"
                        and parsed.get("coefficient") != 0
                    )
                    or not same_typed_json_v1(cell["number"], sample_number)
                ):
                    raise _error("rounding printed cell differs from its numeric universe sample")
            result_sample_for_classification = numeric_sample_by_id.get(
                printed_result_cell["source_sample_id"]
            )
            result_parsed = (
                result_sample_for_classification.get("parsed_token")
                if type(result_sample_for_classification) is dict
                else None
            )
            result_sample_number = (
                {
                    "coefficient": result_parsed.get("coefficient"),
                    "percentage_mark_present": result_parsed.get("percentage_mark_present"),
                    "scale": result_parsed.get("scale"),
                }
                if type(result_parsed) is dict
                else None
            )
            if (
                type(result_sample_for_classification) is not dict
                or result_sample_for_classification.get("column_ordinal") != expected_lane
                or type(result_parsed) is not dict
                or result_parsed.get("classification") != "SIGNED_NUMBER"
                or not same_typed_json_v1(printed_result_cell["number"], result_sample_number)
            ):
                raise _error("rounding printed result is not one signed numeric universe sample")
            result_sample = numeric_sample_by_id[printed_result_cell["source_sample_id"]]
            if evidence["candidate_ordinal"] is not None:
                result_owner_valid = (
                    result_sample["owner_kind"] == "TRAILING_VALUE_ROW"
                    and result_sample["owner_id"]
                    == f"aforav2:trailing:{evidence['candidate_ordinal']}"
                )
            elif local_result_occurrence_id is not None:
                result_owner_valid = (
                    result_sample["owner_kind"] == "ROLE_OCCURRENCE"
                    and result_sample["owner_id"] == local_result_occurrence_id
                )
            else:
                result_record = resolved_by_role.get(result_role)
                result_values = result_record.get("values") if type(result_record) is dict else None
                selected_result_owner_valid = (
                    type(result_values) is list
                    and expected_lane < len(result_values)
                    and result_values[expected_lane]["source_sample_ids"]
                    == [printed_result_cell["source_sample_id"]]
                )
                declared_visible_owner_valid = (
                    result_sample["owner_kind"] == "ROLE_OCCURRENCE"
                    and result_sample["owner_id"] == printed_owner["occurrence_id"]
                )
                result_owner_valid = selected_result_owner_valid or declared_visible_owner_valid
            if not result_owner_valid:
                raise _error("rounding printed result lost its exact selected source owner")
            lane_statuses.append(lane["status"])
        expected_status = (
            "ROUNDING_BOUND_SATISFIED_ALL_LANES"
            if all(
                status == "WITHIN_INTEGER_DISPLAY_UNIT_ROUNDING_BOUND" for status in lane_statuses
            )
            else "ROUNDING_BOUND_EXCEEDED_AT_LEAST_ONE_LANE"
        )
        if evidence["status"] != expected_status:
            raise _error("scoped hierarchical integer rounding assessment drifted")
    if len(keys) != len(set(keys)):
        raise _error("scoped hierarchical rounding assessment ownership repeats")


def _validate_numeric_sample_coverage(value: Mapping[str, Any]) -> None:
    universe = value["numeric_sample_universe"]
    clusters = value["internal_unassigned_numeric_clusters"]
    if (
        type(universe) is not list
        or len(universe) > occurrence_v2._MAX_NUMERIC_SAMPLES
        or type(clusters) is not list
        or len(clusters) > _MAX_COVERAGE_RECORDS
    ):
        raise _error("scoped hierarchical numeric universe axis drifted")
    by_sample: dict[str, Mapping[str, Any]] = {}
    try:
        for sample in universe:
            occurrence_v2._validate_numeric_sample_record(sample)
            if sample["sample_id"] in by_sample:
                raise _error("scoped hierarchical numeric universe repeats one sample")
            by_sample[sample["sample_id"]] = sample
    except occurrence_v2.AccountingFamilyOccurrenceRowAxisV2Error as exc:
        raise _error("scoped hierarchical numeric universe record drifted") from exc
    if universe != sorted(
        universe,
        key=lambda record: (
            record["page_sequence"],
            record["line_ordinal"],
            record["column_ordinal"],
            record["sample_id"],
        ),
    ):
        raise _error("scoped hierarchical numeric universe source order drifted")

    cluster_by_id: dict[str, Mapping[str, Any]] = {}
    for cluster in clusters:
        if (
            type(cluster) is not dict
            or set(cluster) != occurrence_v2._INTERNAL_UNASSIGNED_CLUSTER_FIELDS
            or cluster.get("status")
            not in {
                occurrence_v2._INTERNAL_UNASSIGNED_CLUSTER_STATUS,
                occurrence_v2._OFF_LANE_NUMERIC_CLUSTER_STATUS,
            }
            or type(cluster.get("cluster_id")) is not str
            or type(cluster.get("page_sequence")) is not int
            or cluster["page_sequence"] <= 0
            or type(cluster.get("sample_ids")) is not list
            or not cluster["sample_ids"]
            or len(cluster["sample_ids"]) != len(set(cluster["sample_ids"]))
            or type(cluster.get("column_ordinals")) is not list
            or len(cluster["column_ordinals"]) != len(cluster["sample_ids"])
            or any(type(item) is not int or item < 0 for item in cluster["column_ordinals"])
            or cluster.get("label_lane_status")
            not in {
                occurrence_v2._UNLABELED_LABEL_LANE_STATUS,
                occurrence_v2._LABELED_LABEL_LANE_STATUS,
            }
            or type(cluster.get("same_row_label_evidence")) is not list
            or any(
                type(item) is not dict
                or set(item) != occurrence_v2._SAME_ROW_LABEL_EVIDENCE_FIELDS
                or type(item.get("bbox")) is not list
                or len(item["bbox"]) != 4
                or any(type(coordinate) is not int for coordinate in item["bbox"])
                or type(item.get("line_ordinal")) is not int
                or item["line_ordinal"] < 0
                or type(item.get("numeric_raw_prediction")) is not str
                or type(item.get("vietocr_text")) is not str
                for item in cluster["same_row_label_evidence"]
            )
            or (cluster["label_lane_status"] == occurrence_v2._UNLABELED_LABEL_LANE_STATUS)
            != (not cluster["same_row_label_evidence"])
        ):
            raise _error("scoped hierarchical internal numeric cluster drifted")
        try:
            occurrence_v2._validate_inspected_label_band(cluster, by_sample)  # noqa: SLF001
        except occurrence_v2.AccountingFamilyOccurrenceRowAxisV2Error as exc:
            raise _error("scoped hierarchical inspected label-band receipt drifted") from exc
        material = canonical_clone_v1(cluster)
        cluster_id = material.pop("cluster_id")
        if (
            cluster_id in cluster_by_id
            or cluster_id != "aforav2:unassigned:" + canonical_json_sha256_v1(material)
        ):
            raise _error("scoped hierarchical internal numeric cluster identity drifted")
        for sample_id, lane in zip(cluster["sample_ids"], cluster["column_ordinals"], strict=True):
            sample = by_sample.get(sample_id)
            if (
                type(sample) is not dict
                or sample["page_sequence"] != cluster["page_sequence"]
                or sample["column_ordinal"] != lane
                or sample["owner_kind"] != "SOURCE_ONLY_INTERNAL_CLUSTER"
                or sample["owner_id"] != cluster_id
            ):
                raise _error("scoped hierarchical internal cluster source ownership drifted")
        cluster_by_id[cluster_id] = cluster

    coextensive_by_projected = {
        item["projected_occurrence_id"]: item
        for item in value["coextensive_structural_numeric_evidence"]
        if item.get("status") == _COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_STATUS
    }
    furniture_by_id: dict[str, Mapping[str, Any]] = {}
    for evidence in value["authenticated_extreme_margin_furniture_evidence"]:
        status = evidence.get("status") if type(evidence) is dict else None
        expected_fields = (
            occurrence_v2._EXTREME_MARGIN_FURNITURE_FIELDS
            if status == occurrence_v2._EXTREME_MARGIN_FURNITURE_STATUS
            else occurrence_v2._EXTREME_MARGIN_FURNITURE_V2_FIELDS
            if status == occurrence_v2._EXTREME_MARGIN_FURNITURE_V2_STATUS
            else None
        )
        if (
            type(evidence) is not dict
            or expected_fields is None
            or set(evidence) != expected_fields
            or type(evidence.get("evidence_id")) is not str
        ):
            raise _error("scoped hierarchical extreme-margin furniture evidence drifted")
        material = canonical_clone_v1(evidence)
        evidence_id = material.pop("evidence_id")
        if (
            evidence_id in furniture_by_id
            or evidence_id
            != "aforav2:extreme-margin-furniture:" + canonical_json_sha256_v1(material)
        ):
            raise _error("scoped hierarchical extreme-margin furniture identity drifted")
        furniture_by_id[evidence_id] = evidence
    receipt_sample_ids: list[str] = []
    source_only_receipts: set[str] = set()
    for receipt in value["coverage_receipt"]:
        for sample_id in receipt["sample_ids"]:
            sample = by_sample.get(sample_id)
            if type(sample) is not dict:
                raise _error("coverage receipt cites a sample outside the numeric universe")
            if receipt["row_kind"] == "ROLE_ROW" and (
                sample["owner_kind"] != "ROLE_OCCURRENCE"
                or sample["owner_id"] != receipt["occurrence_id"]
            ):
                raise _error("role receipt differs from numeric universe ownership")
            if receipt["row_kind"] == "TRAILING_VALUE_ROW" and (
                sample["owner_kind"] != "TRAILING_VALUE_ROW"
                or sample["owner_id"] != f"aforav2:trailing:{receipt['candidate_ordinal']}"
            ):
                raise _error("trailing receipt differs from numeric universe ownership")
            if receipt["row_kind"] == "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE":
                evidence = coextensive_by_projected.get(receipt["occurrence_id"])
                if (
                    type(evidence) is not dict
                    or sample["owner_kind"] != "COEXTENSIVE_SCOPE_TOTAL_REFERENCE"
                    or sample["owner_id"] != evidence["owner_occurrence_id"]
                ):
                    raise _error("coextensive receipt differs from numeric universe ownership")
            if receipt["row_kind"] == "INTERNAL_UNASSIGNED_NUMERIC_CLUSTER" and (
                sample["owner_kind"] != "SOURCE_ONLY_INTERNAL_CLUSTER"
                or sample["owner_id"] != receipt["source_record"].get("cluster_id")
            ):
                raise _error("source-only receipt differs from numeric universe ownership")
            if receipt["row_kind"] == "AUTHENTICATED_EXTREME_MARGIN_FURNITURE":
                evidence = furniture_by_id.get(sample["owner_id"])
                if (
                    sample["owner_kind"] != occurrence_v2._EXTREME_MARGIN_FURNITURE_OWNER_KIND
                    or type(evidence) is not dict
                    or receipt["sample_ids"] != [evidence["sample_id"]]
                    or not same_typed_json_v1(receipt["source_record"], evidence)
                ):
                    raise _error("furniture receipt differs from numeric universe ownership")
            receipt_sample_ids.append(sample_id)
        if receipt["row_kind"] == "INTERNAL_UNASSIGNED_NUMERIC_CLUSTER":
            cluster_id = receipt["source_record"]["cluster_id"]
            cluster = cluster_by_id.get(cluster_id)
            expected_disposition = (
                "UNRESOLVED_OFF_LANE_NUMERIC_SOURCE_ONLY"
                if type(cluster) is dict
                and cluster["status"] == occurrence_v2._OFF_LANE_NUMERIC_CLUSTER_STATUS
                else "UNRESOLVED_SOURCE_ONLY_INTERNAL_NUMERIC_CLUSTER"
            )
            if (
                type(cluster) is not dict
                or not same_typed_json_v1(receipt["source_record"], cluster)
                or receipt["disposition"]
                not in {expected_disposition, *_UNLABELED_SOURCE_SUBTOTAL_DISPOSITIONS}
                or (
                    receipt["disposition"] in _UNLABELED_SOURCE_SUBTOTAL_DISPOSITIONS
                    and cluster["status"] != occurrence_v2._INTERNAL_UNASSIGNED_CLUSTER_STATUS
                )
            ):
                raise _error("numeric cluster status, source record, or disposition drifted")
            source_only_receipts.add(cluster_id)
    furniture_receipts = {
        receipt["source_record"]["evidence_id"]: receipt
        for receipt in value["coverage_receipt"]
        if receipt["row_kind"] == "AUTHENTICATED_EXTREME_MARGIN_FURNITURE"
    }
    if (
        len(receipt_sample_ids) != len(set(receipt_sample_ids))
        or set(receipt_sample_ids) != set(by_sample)
        or source_only_receipts != set(cluster_by_id)
        or set(furniture_receipts) != set(furniture_by_id)
        or any(
            receipt["coverage_id"] != "ashtcv2:coverage:extreme-margin-furniture:" + evidence_id
            or receipt["disposition"] != _EXTREME_MARGIN_FURNITURE_DISPOSITION
            or receipt["candidate_ordinal"] is not None
            or receipt["occurrence_id"] is not None
            or receipt["role"] is not None
            for evidence_id, receipt in furniture_receipts.items()
        )
    ):
        raise _error("numeric universe does not have exactly one owning coverage receipt")
    cluster_receipts = {
        receipt["source_record"]["cluster_id"]: receipt
        for receipt in value["coverage_receipt"]
        if receipt["row_kind"] == "INTERNAL_UNASSIGNED_NUMERIC_CLUSTER"
    }
    if any(
        receipt["disposition"] not in _UNLABELED_SOURCE_SUBTOTAL_DISPOSITIONS
        and (
            (
                "OFF_LANE_NUMERIC_SOURCE_ONLY_VETO:"
                if cluster["status"] == occurrence_v2._OFF_LANE_NUMERIC_CLUSTER_STATUS
                else "SOURCE_ONLY_INTERNAL_NUMERIC_CLUSTER_VETO:"
            )
            + cluster_id
            not in value["unresolved_reasons"]
        )
        for cluster_id, cluster in cluster_by_id.items()
        for receipt in [cluster_receipts[cluster_id]]
    ):
        raise _error("source-only numeric cluster did not veto closure")


def _exact_sum_matches(
    result_numbers: Sequence[Mapping[str, Any]],
    component_number_axes: Sequence[Sequence[Mapping[str, Any]]],
) -> bool:
    if (
        not result_numbers
        or not component_number_axes
        or any(len(axis) != len(result_numbers) for axis in component_number_axes)
    ):
        return False
    for lane, result in enumerate(result_numbers):
        components = [axis[lane] for axis in component_number_axes]
        if any(
            type(number) is not dict
            or set(number) != {"coefficient", "percentage_mark_present", "scale"}
            for number in [result, *components]
        ):
            return False
        percentages = {number["percentage_mark_present"] for number in [result, *components]}
        if len(percentages) != 1:
            return False
        scale = max(number["scale"] for number in [result, *components])
        component_sum = sum(
            number["coefficient"] * 10 ** (scale - number["scale"]) for number in components
        )
        if result["coefficient"] * 10 ** (scale - result["scale"]) != component_sum:
            return False
    return True


def _resolved_number_axis(record: Mapping[str, Any] | None) -> list[Mapping[str, Any]]:
    values = record.get("values") if type(record) is dict else None
    if type(values) is not list:
        return []
    return [value.get("number") for value in values]


def _occurrence_number_axis(
    occurrence_id: str, numeric_sample_by_id: Mapping[str, Mapping[str, Any]]
) -> list[Mapping[str, Any]]:
    samples = sorted(
        (
            sample
            for sample in numeric_sample_by_id.values()
            if sample.get("owner_kind") == "ROLE_OCCURRENCE"
            and sample.get("owner_id") == occurrence_id
        ),
        key=lambda sample: sample["column_ordinal"],
    )
    if [sample["column_ordinal"] for sample in samples] != list(range(len(samples))):
        return []
    return [
        {
            "coefficient": sample["parsed_token"]["coefficient"],
            "percentage_mark_present": sample["parsed_token"]["percentage_mark_present"],
            "scale": sample["parsed_token"]["scale"],
        }
        for sample in samples
    ]


def _global_equation_exact_arithmetic(
    equation: Mapping[str, Any], resolved_by_role: Mapping[str, Mapping[str, Any]]
) -> bool:
    result = resolved_by_role.get(equation["result_role"])
    components = [resolved_by_role.get(role) for role in equation["component_roles_present"]]
    if type(result) is not dict or any(type(component) is not dict for component in components):
        return False
    return _exact_sum_matches(
        _resolved_number_axis(result),
        [_resolved_number_axis(component) for component in components],
    )


def _resolved_source_owner(record: Mapping[str, Any]) -> dict[str, Any] | None:
    source = record.get("source")
    if type(source) is not dict or source.get("kind") not in {
        "ROLE_ROW",
        "TRAILING_VALUE_ROW",
    }:
        return None
    source_record = source.get("record")
    if type(source_record) is not dict:
        return None
    return {
        "candidate_ordinal": (
            source_record.get("candidate_ordinal")
            if source["kind"] == "TRAILING_VALUE_ROW"
            else None
        ),
        "occurrence_id": (
            source_record.get("label_match", {}).get("occurrence_id")
            if source["kind"] == "ROLE_ROW"
            else None
        ),
        "role": source_record.get("role") if source["kind"] == "ROLE_ROW" else None,
        "source_kind": source["kind"],
    }


def _local_equation_exact_arithmetic(
    equation: Mapping[str, Any],
    *,
    numeric_sample_by_id: Mapping[str, Mapping[str, Any]],
    role_occurrence_by_id: Mapping[str, Mapping[str, Any]],
) -> bool:
    result_occurrence_id = equation["result_occurrence_id"]
    component_axes = []
    for role in equation["component_roles_present"]:
        owners = [
            occurrence
            for occurrence in role_occurrence_by_id.values()
            if occurrence.get("role") == role
            and occurrence.get("scope_owner_occurrence_id") == result_occurrence_id
        ]
        if len(owners) != 1:
            return False
        component_axes.append(
            _occurrence_number_axis(owners[0]["occurrence_id"], numeric_sample_by_id)
        )
    return _exact_sum_matches(
        _occurrence_number_axis(result_occurrence_id, numeric_sample_by_id),
        component_axes,
    )


def _validate_local_trailing_subgroup_subtotal_receipt(
    equation: Mapping[str, Any],
    value: Mapping[str, Any],
    *,
    numeric_sample_by_id: Mapping[str, Mapping[str, Any]],
    resolved_by_role: Mapping[str, Mapping[str, Any]],
    role_occurrence_by_id: Mapping[str, Mapping[str, Any]],
) -> None:
    receipt = equation.get("local_trailing_subgroup_subtotal_receipt")
    interval = receipt.get("interval") if type(receipt) is dict else None
    trusted_equation = _local_trailing_subgroup_trusted_equation_spec()
    trusted_role_sets = [
        list(roles) for roles in _LOCAL_TRAILING_SUBGROUP_TRUSTED_COMPONENT_ROLE_SETS
    ]
    if (
        canonical_json_sha256_v1(trusted_equation)
        != _LOCAL_TRAILING_SUBGROUP_TRUSTED_EQUATION_SPEC_SHA256
    ):
        raise _error("local trailing subgroup trusted equation declaration drifted")
    if (
        type(receipt) is not dict
        or set(receipt) != _LOCAL_TRAILING_SUBGROUP_RECEIPT_FIELDS
        or type(interval) is not dict
        or set(interval) != _LOCAL_TRAILING_SUBGROUP_INTERVAL_FIELDS
        or receipt["status"] != _LOCAL_TRAILING_SUBGROUP_RECEIPT_STATUS
        or receipt["target_role"] != equation["result_role"]
        or receipt["target_occurrence_id"] != equation["result_occurrence_id"]
        or receipt["component_roles"] != equation["component_roles_present"]
        or receipt["hierarchy_spec_sha256"]
        != _LOCAL_TRAILING_SUBGROUP_TRUSTED_HIERARCHY_SPEC_SHA256
        or receipt["equation_spec_sha256"] != _LOCAL_TRAILING_SUBGROUP_TRUSTED_EQUATION_SPEC_SHA256
        or receipt["configured_alternative_role_sets"] != trusted_role_sets
        or receipt["row_axis_id"] != value["row_axis_id"]
        or receipt["numeric_sample_universe_sha256"]
        != canonical_json_sha256_v1(value["numeric_sample_universe"])
        or receipt["role_occurrence_axis_sha256"]
        != canonical_json_sha256_v1(value["role_occurrences"])
        or receipt["source_row_kind"]
        not in {"TRAILING_VALUE_ROW", "INTERNAL_UNASSIGNED_NUMERIC_CLUSTER"}
        or (
            receipt["source_row_kind"] == "TRAILING_VALUE_ROW"
            and (
                type(receipt["candidate_ordinal"]) is not int
                or receipt["candidate_ordinal"] < 0
                or receipt["source_cluster_id"] is not None
            )
        )
        or (
            receipt["source_row_kind"] == "INTERNAL_UNASSIGNED_NUMERIC_CLUSTER"
            and (
                receipt["candidate_ordinal"] is not None
                or type(receipt["source_cluster_id"]) is not str
                or not receipt["source_cluster_id"].startswith("aforav2:unassigned:")
            )
        )
        or receipt["selection_kind"]
        not in {
            "COMPLETE_EXACT_ALL_LANES",
            "PARTIAL_EXACT_UNIQUE_VISIBLE_LANES_IDENTICAL_MISSING_LANES",
        }
        or type(receipt["alternative_value_axes"]) is not list
        or not receipt["alternative_value_axes"]
        or type(receipt["applicable_alternative_ordinals"]) is not list
        or any(
            type(item) is not int or item < 0 for item in receipt["applicable_alternative_ordinals"]
        )
        or receipt["applicable_alternative_ordinals"]
        != sorted(set(receipt["applicable_alternative_ordinals"]))
        or type(receipt["applicable_alternative_spec_sha256s"]) is not list
        or any(
            type(item) is not str or len(item) != 64
            for item in receipt["applicable_alternative_spec_sha256s"]
        )
        or type(receipt["observed_column_ordinals"]) is not list
        or receipt["observed_column_ordinals"] != sorted(set(receipt["observed_column_ordinals"]))
        or not receipt["observed_column_ordinals"]
        or any(type(item) is not int or item < 0 for item in receipt["observed_column_ordinals"])
        or type(receipt["missing_column_ordinals"]) is not list
        or receipt["missing_column_ordinals"] != sorted(set(receipt["missing_column_ordinals"]))
        or any(type(item) is not int or item < 0 for item in receipt["missing_column_ordinals"])
        or bool(receipt["missing_column_ordinals"])
        is not receipt["selection_kind"].startswith("PARTIAL_")
        or (receipt["boundary_occurrence_id"] is None) is not (receipt["boundary_role"] is None)
        or (
            receipt["boundary_occurrence_id"] is not None
            and (
                type(receipt["boundary_occurrence_id"]) is not str
                or type(receipt["boundary_role"]) is not str
                or not receipt["boundary_role"]
            )
        )
        or any(
            type(receipt[field]) is not list
            or len(receipt[field]) != len(set(receipt[field]))
            or any(type(item) is not str or not item for item in receipt[field])
            for field in (
                "component_occurrence_ids",
                "component_roles",
                "component_sample_ids",
                "descendant_occurrence_ids",
                "nonadditive_occurrence_ids",
                "nonadditive_sample_ids",
                "source_sample_ids",
            )
        )
        or any(type(item) is not int for item in interval.values())
    ):
        raise _error("local trailing subgroup subtotal receipt shape or axis drifted")
    material = canonical_clone_v1(receipt)
    receipt_id = material.pop("receipt_id")
    if receipt_id != "ashtcv2:local-trailing-subgroup-subtotal:" + (
        canonical_json_sha256_v1(material)
    ):
        raise _error("local trailing subgroup subtotal receipt identity drifted")

    target = role_occurrence_by_id.get(receipt["target_occurrence_id"])
    target_match = target.get("label_match") if type(target) is dict else None
    if (
        value["family_id"] != "INTERBANK_DEPOSITS_AND_LOANS"
        or receipt["target_role"] != "INTERBANK_LOAN_GROUP"
        or type(target) is not dict
        or target.get("role") != receipt["target_role"]
        or target.get("role_kind") != "STRUCTURAL_GROUP"
        or target.get("has_bound_value_row") is not False
        or target.get("scope_owner_occurrence_id") != receipt["parent_occurrence_id"]
        or type(receipt["parent_occurrence_id"]) is not str
        or not receipt["parent_occurrence_id"].startswith("aforav2:root:")
        or type(target_match) is not dict
        or not occurrence_v2._match_has_effective_exact_source_authority(  # noqa: SLF001
            target_match
        )
        or not str(target.get("scope_owner_match_kind", "")).startswith("EXACT_")
        or interval["target_document_line_ordinal"] != target_match.get("document_line_ordinal")
        or interval["target_source_line_index"] != target_match.get("source_line_index")
        or interval["page_sequence"] != target_match.get("page_sequence")
    ):
        raise _error("local trailing subgroup target or parent binding drifted")

    descendants = [
        occurrence
        for occurrence in role_occurrence_by_id.values()
        if _occurrence_descends_from(
            occurrence, receipt["target_occurrence_id"], role_occurrence_by_id
        )
    ]
    descendants.sort(
        key=lambda occurrence: (
            occurrence["label_match"]["document_line_ordinal"],
            occurrence["occurrence_id"],
        )
    )
    additive = [
        occurrence for occurrence in descendants if occurrence.get("role_kind") == "ADDITIVE_CHILD"
    ]
    nonadditive = [
        occurrence
        for occurrence in descendants
        if occurrence.get("role_kind") == "NONADDITIVE_CHILD"
    ]
    additive_by_role = {occurrence["role"]: occurrence for occurrence in additive}
    if (
        [occurrence["occurrence_id"] for occurrence in descendants]
        != receipt["descendant_occurrence_ids"]
        or any(
            occurrence.get("role_kind") not in {"ADDITIVE_CHILD", "NONADDITIVE_CHILD"}
            or not occurrence_v2._match_has_effective_exact_source_authority(  # noqa: SLF001
                occurrence.get("label_match", {})
            )
            for occurrence in descendants
        )
        or len(additive_by_role) != len(additive)
        or not set(receipt["component_roles"]) <= set(additive_by_role)
        or receipt["component_occurrence_ids"]
        != [additive_by_role[role]["occurrence_id"] for role in receipt["component_roles"]]
        or receipt["nonadditive_occurrence_ids"]
        != [occurrence["occurrence_id"] for occurrence in nonadditive]
    ):
        raise _error("local trailing subgroup exhaustive descendant ownership drifted")
    boundary = (
        role_occurrence_by_id.get(receipt["boundary_occurrence_id"])
        if receipt["boundary_occurrence_id"] is not None
        else None
    )
    if boundary is not None and (
        boundary.get("role") != receipt["boundary_role"]
        or boundary.get("role_kind") != "TOTAL"
        or boundary.get("scope_owner_occurrence_id") != receipt["parent_occurrence_id"]
        or not occurrence_v2._match_has_effective_exact_source_authority(  # noqa: SLF001
            boundary.get("label_match", {})
        )
        or boundary["label_match"].get("source_line_index")
        != interval["subgroup_stop_source_line_index_exclusive"]
        or boundary["label_match"].get("document_line_ordinal")
        != interval["subgroup_stop_document_line_ordinal_exclusive"]
    ):
        raise _error("local trailing subgroup exact boundary binding drifted")
    if boundary is None and (
        interval["subgroup_stop_source_line_index_exclusive"]
        != interval["topology_region_stop_source_line_index_exclusive"]
        or interval["subgroup_stop_document_line_ordinal_exclusive"]
        != interval["topology_region_stop_document_line_ordinal_exclusive"]
    ):
        raise _error("local trailing subgroup topology stop binding drifted")

    def occurrence_samples(occurrence_id: str) -> list[Mapping[str, Any]]:
        return sorted(
            (
                sample
                for sample in numeric_sample_by_id.values()
                if sample.get("owner_kind") == "ROLE_OCCURRENCE"
                and sample.get("owner_id") == occurrence_id
            ),
            key=lambda sample: sample["column_ordinal"],
        )

    component_sample_axes = [
        occurrence_samples(occurrence_id) for occurrence_id in receipt["component_occurrence_ids"]
    ]
    nonadditive_sample_axes = [
        occurrence_samples(occurrence_id) for occurrence_id in receipt["nonadditive_occurrence_ids"]
    ]
    descendant_sample_axes = [
        occurrence_samples(occurrence_id) for occurrence_id in receipt["descendant_occurrence_ids"]
    ]
    if (
        any(
            not samples
            or [sample["column_ordinal"] for sample in samples] != list(range(len(samples)))
            for samples in descendant_sample_axes
        )
        or receipt["component_sample_ids"]
        != [sample["sample_id"] for samples in component_sample_axes for sample in samples]
        or receipt["nonadditive_sample_ids"]
        != [sample["sample_id"] for samples in nonadditive_sample_axes for sample in samples]
    ):
        raise _error("local trailing subgroup numeric ownership receipt drifted")

    def sample_resolution(samples: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        return {
            "values": [
                {
                    "column_ordinal": sample["column_ordinal"],
                    "number": {
                        "coefficient": sample["parsed_token"]["coefficient"],
                        "percentage_mark_present": sample["parsed_token"][
                            "percentage_mark_present"
                        ],
                        "scale": sample["parsed_token"]["scale"],
                    },
                    "source_sample_ids": [sample["sample_id"]],
                }
                for sample in samples
            ]
        }

    required_roles = set(additive_by_role) - set(trusted_equation["shared_component_roles"])
    expected_alternatives = []
    for alternative_ordinal, alternative_spec in enumerate(
        trusted_equation["component_role_alternatives"]
    ):
        roles = alternative_spec["component_roles"]
        if not required_roles <= set(roles) or not all(role in additive_by_role for role in roles):
            continue
        occurrence_ids = [additive_by_role[role]["occurrence_id"] for role in roles]
        component_samples = [
            sample["sample_id"]
            for occurrence_id in occurrence_ids
            for sample in occurrence_samples(occurrence_id)
        ]
        expected_alternatives.append(
            {
                "alternative_ordinal": alternative_ordinal,
                "alternative_spec_sha256": canonical_json_sha256_v1(alternative_spec),
                "component_occurrence_ids": occurrence_ids,
                "component_roles": canonical_clone_v1(roles),
                "component_sample_ids": component_samples,
                "values": _sum_records(
                    [
                        sample_resolution(occurrence_samples(occurrence_id))
                        for occurrence_id in occurrence_ids
                    ]
                ),
            }
        )
    expected_ordinals = [
        alternative["alternative_ordinal"] for alternative in expected_alternatives
    ]
    expected_spec_sha256s = [
        alternative["alternative_spec_sha256"] for alternative in expected_alternatives
    ]
    if (
        not expected_alternatives
        or (receipt["selection_kind"].startswith("PARTIAL_") and len(expected_alternatives) < 2)
        or receipt["applicable_alternative_ordinals"] != expected_ordinals
        or receipt["applicable_alternative_spec_sha256s"] != expected_spec_sha256s
        or not same_typed_json_v1(receipt["alternative_value_axes"], expected_alternatives)
    ):
        raise _error("local trailing subgroup complete alternative axis drifted")
    selected_receipts = [
        alternative
        for alternative in expected_alternatives
        if alternative["component_roles"] == receipt["component_roles"]
        and alternative["component_occurrence_ids"] == receipt["component_occurrence_ids"]
        and alternative["component_sample_ids"] == receipt["component_sample_ids"]
    ]
    if len(selected_receipts) != 1:
        raise _error("local trailing subgroup selected alternative receipt drifted")
    descendant_samples = [sample for samples in descendant_sample_axes for sample in samples]
    last_descendant_source = max(sample["line_ordinal"] for sample in descendant_samples)
    page_document_offset = (
        interval["target_document_line_ordinal"] - interval["target_source_line_index"]
    )
    if (
        interval["last_descendant_source_line_index"] != last_descendant_source
        or interval["last_descendant_document_line_ordinal"]
        != page_document_offset + last_descendant_source
        or interval["candidate_first_source_line_index"] != last_descendant_source + 1
        or interval["candidate_first_document_line_ordinal"]
        != page_document_offset + interval["candidate_first_source_line_index"]
        or interval["candidate_last_document_line_ordinal"]
        != page_document_offset + interval["candidate_last_source_line_index"]
        or interval["subgroup_stop_source_line_index_exclusive"]
        != interval["candidate_last_source_line_index"] + 1
        or interval["subgroup_stop_document_line_ordinal_exclusive"]
        != interval["candidate_last_document_line_ordinal"] + 1
        or interval["topology_region_stop_source_line_index_exclusive"]
        < interval["subgroup_stop_source_line_index_exclusive"]
        or interval["topology_region_stop_document_line_ordinal_exclusive"]
        - interval["target_document_line_ordinal"]
        != interval["topology_region_stop_source_line_index_exclusive"]
        - interval["target_source_line_index"]
    ):
        raise _error("local trailing subgroup sealed interval receipt drifted")

    coverage = [
        record
        for record in value["coverage_receipt"]
        if record.get("disposition") == _LOCAL_TRAILING_SUBGROUP_SUBTOTAL_CORROBORATION
        and record.get("candidate_ordinal") == receipt["candidate_ordinal"]
        and record.get("row_kind") == receipt["source_row_kind"]
        and (
            receipt["source_cluster_id"] is None
            or record.get("source_record", {}).get("cluster_id") == receipt["source_cluster_id"]
        )
    ]
    if len(coverage) != 1:
        raise _error("local trailing subgroup subtotal coverage is not unique")
    source_receipt = coverage[0]
    source_candidates = _numeric_source_candidate_axis(
        value["numeric_sample_universe"],
        [source_receipt["source_record"]]
        if receipt["source_row_kind"] == "INTERNAL_UNASSIGNED_NUMERIC_CLUSTER"
        else [],
        [source_receipt["source_record"]]
        if receipt["source_row_kind"] == "TRAILING_VALUE_ROW"
        else [],
    )
    source = source_candidates[0] if len(source_candidates) == 1 else None
    source_samples = [
        numeric_sample_by_id.get(sample_id) for sample_id in receipt["source_sample_ids"]
    ]
    if (
        type(source) is not dict
        or source["row_kind"] != receipt["source_row_kind"]
        or source["sample_ids"] != receipt["source_sample_ids"]
        or source_receipt["coverage_id"]
        != "ashtcv2:coverage:local-trailing-subgroup-subtotal:"
        + receipt["target_role"]
        + (
            f":trailing:{receipt['candidate_ordinal']}"
            if receipt["source_row_kind"] == "TRAILING_VALUE_ROW"
            else f":cluster:{receipt['source_cluster_id']}"
        )
        or source_receipt["occurrence_id"] != receipt["target_occurrence_id"]
        or source_receipt["role"] != receipt["target_role"]
        or source_receipt["sample_ids"] != receipt["source_sample_ids"]
        or source_receipt["row_kind"] != receipt["source_row_kind"]
        or receipt["source_record_sha256"]
        != canonical_json_sha256_v1(source_receipt["source_record"])
        or any(type(sample) is not dict for sample in source_samples)
        or min(sample["line_ordinal"] for sample in source_samples)
        != interval["candidate_first_source_line_index"]
        or max(sample["line_ordinal"] for sample in source_samples)
        != interval["candidate_last_source_line_index"]
        or [sample["column_ordinal"] for sample in source_samples]
        != receipt["observed_column_ordinals"]
        or max(sample["bbox"][1] for sample in source_samples)
        >= min(sample["bbox"][3] for sample in source_samples)
        or min(sample["bbox"][1] for sample in source_samples)
        <= max(sample["bbox"][3] for sample in descendant_samples)
    ):
        raise _error("local trailing subgroup subtotal source receipt drifted")

    lane_axis = [
        value["column_ordinal"] for value in receipt["alternative_value_axes"][0]["values"]
    ]
    if lane_axis != list(range(len(lane_axis))) or receipt["missing_column_ordinals"] != [
        lane for lane in lane_axis if lane not in set(receipt["observed_column_ordinals"])
    ]:
        raise _error("local trailing subgroup selector lane axis drifted")

    def alternative_matches_visible(alternative: Mapping[str, Any]) -> bool:
        by_lane = {
            value_record["column_ordinal"]: value_record for value_record in alternative["values"]
        }
        return all(
            source_value["column_ordinal"] in by_lane
            and same_typed_json_v1(
                source_value["number"], by_lane[source_value["column_ordinal"]]["number"]
            )
            for source_value in source["values"]
        )

    matching_alternatives = [
        alternative
        for alternative in receipt["alternative_value_axes"]
        if alternative_matches_visible(alternative)
    ]
    missing_lanes_are_nondiscriminating = all(
        len(
            {
                canonical_json_sha256_v1(alternative["values"][lane]["number"])
                for alternative in receipt["alternative_value_axes"]
            }
        )
        == 1
        for lane in receipt["missing_column_ordinals"]
    )
    selected_alternative = matching_alternatives[0] if len(matching_alternatives) == 1 else None
    if (
        type(selected_alternative) is not dict
        or selected_alternative["component_roles"] != receipt["component_roles"]
        or bool(receipt["missing_column_ordinals"])
        and not missing_lanes_are_nondiscriminating
        or receipt["selection_kind"] == "COMPLETE_EXACT_ALL_LANES"
        and (receipt["missing_column_ordinals"] or not source["complete"])
    ):
        raise _error("local trailing subgroup selector alternative became ambiguous")

    target_resolution = resolved_by_role.get(receipt["target_role"])
    target_global = [
        record
        for record in value["equations"]["global"]
        if record.get("result_role") == receipt["target_role"]
    ]
    if (
        type(target_resolution) is not dict
        or target_resolution.get("source") is not None
        or target_resolution.get("component_roles") != receipt["component_roles"]
        or not _same_values(target_resolution.get("values", []), selected_alternative["values"])
        or len(target_global) != 1
        or target_global[0].get("status") != "VISIBLE_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS"
        or target_global[0].get("component_roles_present") != receipt["component_roles"]
    ):
        raise _error("local trailing subgroup subtotal did not close its declared target")
    excluded_roles = {
        receipt["target_role"],
        *receipt["component_roles"],
        *(occurrence["role"] for occurrence in nonadditive),
    }
    if any(
        role not in excluded_roles and _same_values(record["values"], target_resolution["values"])
        for role, record in resolved_by_role.items()
    ):
        raise _error("local trailing subgroup subtotal has an equal-vector collision")


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
        or type(value["numeric_sample_universe"]) is not list
        or type(value["internal_unassigned_numeric_clusters"]) is not list
        or not same_typed_json_v1(value["dependency_content_refs"], _dependency_refs())
        or type(value["role_occurrences"]) is not list
        or type(value["authenticated_existing_dash_evidence"]) is not list
        or type(value["authenticated_extreme_margin_furniture_evidence"]) is not list
        or len(value["authenticated_extreme_margin_furniture_evidence"]) > _MAX_COVERAGE_RECORDS
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
    from bctc_ai.evaluation import (  # noqa: PLC0415
        accounting_family_one_edit_exact_authority_v1 as one_edit_v1,
    )

    try:
        one_edit_proofs = (
            one_edit_v1.validate_accounting_family_one_edit_exact_authority_receipt_shape_v1(
                value["one_edit_exact_source_structural_proofs"]
            )
        )
    except one_edit_v1.AccountingFamilyOneEditExactAuthorityV1Error as exc:
        raise _error("scoped hierarchical one-edit structural proof drifted") from exc
    if one_edit_proofs["family_id"] != value["family_id"]:
        raise _error("scoped hierarchical one-edit structural proof family drifted")
    roles = [record.get("role") for record in value["resolved_roles"]]
    if any(type(role) is not str or not role for role in roles) or len(roles) != len(set(roles)):
        raise _error("scoped hierarchical resolved role axis repeats or drifted")
    for record in value["resolved_roles"]:
        _validate_resolution_record(record)
    numeric_sample_by_id = {}
    try:
        for sample in value["numeric_sample_universe"]:
            occurrence_v2._validate_numeric_sample_record(sample)
            if sample["sample_id"] in numeric_sample_by_id:
                raise _error("scoped hierarchical numeric universe repeats one sample")
            numeric_sample_by_id[sample["sample_id"]] = sample
    except occurrence_v2.AccountingFamilyOccurrenceRowAxisV2Error as exc:
        raise _error("scoped hierarchical numeric universe record drifted") from exc
    resolved_by_role = {record["role"]: record for record in value["resolved_roles"]}
    role_occurrence_by_id = {
        occurrence.get("occurrence_id"): occurrence
        for occurrence in value["role_occurrences"]
        if type(occurrence) is dict and type(occurrence.get("occurrence_id")) is str
    }
    proof_check_by_retrieval_occurrence_id = {
        check["occurrence_id"]: check
        for check in one_edit_proofs["checks"]
        if check["match_scope"] == "EXPANDED_OCCURRENCE"
    }
    if any(
        "one_edit_exact_source_authority_check" in occurrence.get("label_match", {})
        and not same_typed_json_v1(
            occurrence["label_match"]["one_edit_exact_source_authority_check"],
            proof_check_by_retrieval_occurrence_id.get(occurrence.get("retrieval_occurrence_id")),
        )
        for occurrence in role_occurrence_by_id.values()
    ):
        raise _error("scoped hierarchical one-edit occurrence proof drifted")
    for equation in value["equations"]["global"]:
        if (
            type(equation) is not dict
            or set(equation) not in (_GLOBAL_EQUATION_FIELDS_V1, _GLOBAL_EQUATION_FIELDS_V2)
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
            or equation["status"] not in _GLOBAL_EQUATION_STATUSES
            or type(equation["trailing_candidate_evidence"]) is not list
            or (
                "visible_result_roles" in equation
                and (
                    type(equation["visible_result_roles"]) is not list
                    or len(equation["visible_result_roles"])
                    != len(set(equation["visible_result_roles"]))
                    or any(
                        type(role) is not str or not role
                        for role in equation["visible_result_roles"]
                    )
                )
            )
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
                    "SELECTED_ROUNDING_CORROBORATED_VISIBLE_TRAILING_ROOT_SOURCE",
                    "SELECTED_VISIBLE_TRAILING_ROOT_SOURCE",
                    "UNRESOLVED_PARTIAL_TRAILING_NUMERIC_CHALLENGER",
                    "UNRESOLVED_UNSELECTED_COMPLETE_TRAILING_NUMERIC_CHALLENGER",
                }
            ):
                raise _error("scoped hierarchical trailing challenger evidence drifted")
            trailing_ordinals.append(candidate["candidate_ordinal"])
            if candidate["status"] in {
                "SELECTED_ROUNDING_CORROBORATED_VISIBLE_TRAILING_ROOT_SOURCE",
                "SELECTED_VISIBLE_TRAILING_ROOT_SOURCE",
            }:
                selected_ordinals.append(candidate["candidate_ordinal"])
        if trailing_ordinals != sorted(set(trailing_ordinals)) or selected_ordinals != (
            []
            if equation["selected_trailing_candidate_ordinal"] is None
            else [equation["selected_trailing_candidate_ordinal"]]
        ):
            raise _error("scoped hierarchical selected trailing candidate axis drifted")
        _validate_residual_evidence_axis(
            equation["residual_evidence"], result_role=equation["result_role"]
        )
        if "rounding_evidence" in equation:
            _validate_rounding_evidence_axis(
                equation["rounding_evidence"],
                local_result_occurrence_id=None,
                numeric_sample_by_id=numeric_sample_by_id,
                resolved_by_role=resolved_by_role,
                residual_axis=equation["residual_evidence"],
                role_occurrence_by_id=role_occurrence_by_id,
                result_role=equation["result_role"],
                visible_result_roles={equation["result_role"], *equation["visible_result_roles"]},
            )
            satisfied = [
                evidence
                for evidence in equation["rounding_evidence"]
                if evidence["status"] == "ROUNDING_BOUND_SATISFIED_ALL_LANES"
                and evidence["component_roles"] == equation["component_roles_present"]
                and evidence["candidate_ordinal"] == equation["selected_trailing_candidate_ordinal"]
            ]
            if ("ROUNDING_CORROBORATED" in equation["status"] and len(satisfied) != 1) or (
                "ROUNDING_CORROBORATED" not in equation["status"]
                and any(
                    candidate["status"]
                    == "SELECTED_ROUNDING_CORROBORATED_VISIBLE_TRAILING_ROOT_SOURCE"
                    for candidate in equation["trailing_candidate_evidence"]
                )
            ):
                raise _error("scoped hierarchical rounding selection drifted")
        successful_global_kinds = {
            "DERIVED_EXACT_EXHAUSTIVE_COMPONENT_SUM": {"DERIVED_EXACT_COMPONENT_SUM"},
            "VISIBLE_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS": {
                "DERIVED_EXACT_DISJOINT_OCCURRENCE_SUM_CORROBORATED_BY_COMPONENTS",
                "VISIBLE_SOURCE_ROLE_CORROBORATED_BY_COMPONENTS",
            },
            "VISIBLE_RESULT_ROUNDING_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS": {
                "VISIBLE_SOURCE_ROLE_ROUNDING_CORROBORATED_BY_COMPONENTS"
            },
            "VISIBLE_TRAILING_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS": {
                "VISIBLE_TRAILING_TOTAL_CORROBORATED_BY_COMPONENTS"
            },
            "VISIBLE_TRAILING_RESULT_ROUNDING_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS": {
                "VISIBLE_TRAILING_TOTAL_ROUNDING_CORROBORATED_BY_COMPONENTS"
            },
        }
        expected_resolution_kinds = successful_global_kinds.get(equation["status"])
        if expected_resolution_kinds is not None:
            result_record = resolved_by_role.get(equation["result_role"])
            rounding_selected = "ROUNDING_CORROBORATED" in equation["status"]
            arithmetic_is_exact = _global_equation_exact_arithmetic(equation, resolved_by_role)
            selected_rounding = [
                evidence
                for evidence in equation.get("rounding_evidence", [])
                if evidence["status"] == "ROUNDING_BOUND_SATISFIED_ALL_LANES"
                and evidence["component_roles"] == equation["component_roles_present"]
                and evidence["candidate_ordinal"] == equation["selected_trailing_candidate_ordinal"]
            ]
            selected_rounding_has_nonzero_residual = len(selected_rounding) == 1 and any(
                lane["residual_number"]["coefficient"] != 0
                for lane in selected_rounding[0]["lanes"]
            )
            selected_rounding_owner_matches_result = len(
                selected_rounding
            ) == 1 and same_typed_json_v1(
                selected_rounding[0]["printed_result_owner"],
                _resolved_source_owner(result_record),
            )
            if (
                type(result_record) is not dict
                or result_record["resolution_kind"] not in expected_resolution_kinds
                or result_record["component_roles"] != equation["component_roles_present"]
                or arithmetic_is_exact is rounding_selected
                or (
                    rounding_selected
                    and (
                        not selected_rounding_has_nonzero_residual
                        or not selected_rounding_owner_matches_result
                    )
                )
                or (not rounding_selected and equation.get("rounding_evidence", []))
            ):
                raise _error("global equation status and resolved arithmetic authority drifted")
        else:
            result_record = resolved_by_role.get(equation["result_role"])
            selected_resolution_kinds = {
                kind for kinds in successful_global_kinds.values() for kind in kinds
            }
            if equation["component_roles_present"] or (
                type(result_record) is dict
                and result_record["resolution_kind"] in selected_resolution_kinds
                and result_record["component_roles"]
            ):
                raise _error("global failure status retained selected accounting authority")
    for equation in value["equations"]["local"]:
        if (
            type(equation) is not dict
            or set(equation)
            not in (
                _LOCAL_EQUATION_FIELDS_V1,
                _LOCAL_EQUATION_FIELDS_V2,
                _LOCAL_EQUATION_FIELDS_V3,
            )
            or type(equation["component_roles_present"]) is not list
            or type(equation["result_occurrence_id"]) is not str
            or not equation["result_occurrence_id"]
            or type(equation["result_role"]) is not str
            or not equation["result_role"]
            or equation["status"] not in _LOCAL_EQUATION_STATUSES
        ):
            raise _error("scoped hierarchical local equation record drifted")
        if "rounding_evidence" in equation:
            _validate_residual_evidence_axis(
                equation["residual_evidence"], result_role=equation["result_role"]
            )
            _validate_rounding_evidence_axis(
                equation["rounding_evidence"],
                local_result_occurrence_id=equation["result_occurrence_id"],
                numeric_sample_by_id=numeric_sample_by_id,
                resolved_by_role=resolved_by_role,
                residual_axis=equation["residual_evidence"],
                role_occurrence_by_id=role_occurrence_by_id,
                result_role=equation["result_role"],
                visible_result_roles={equation["result_role"]},
            )
            selected = [
                evidence
                for evidence in equation["rounding_evidence"]
                if evidence["status"] == "ROUNDING_BOUND_SATISFIED_ALL_LANES"
                and evidence["component_roles"] == equation["component_roles_present"]
            ]
            if "ROUNDING_CORROBORATED" in equation["status"] and len(selected) != 1:
                raise _error("scoped hierarchical local rounding selection drifted")
        if equation["status"] == (
            "LOCAL_TRAILING_SUBTOTAL_CORROBORATED_BY_EXACT_SCOPED_COMPONENTS"
        ):
            if equation.get("residual_evidence") or equation.get("rounding_evidence"):
                raise _error("local trailing exact subtotal retained rounding authority")
            _validate_local_trailing_subgroup_subtotal_receipt(
                equation,
                value,
                numeric_sample_by_id=numeric_sample_by_id,
                resolved_by_role=resolved_by_role,
                role_occurrence_by_id=role_occurrence_by_id,
            )
        elif equation["status"] in {
            "LOCAL_VISIBLE_SUBTOTAL_CORROBORATED_BY_EXACT_SCOPED_COMPONENTS",
            "LOCAL_VISIBLE_SUBTOTAL_ROUNDING_CORROBORATED_BY_EXHAUSTIVE_SCOPED_COMPONENTS",
        }:
            rounding_selected = "ROUNDING_CORROBORATED" in equation["status"]
            arithmetic_is_exact = _local_equation_exact_arithmetic(
                equation,
                numeric_sample_by_id=numeric_sample_by_id,
                role_occurrence_by_id=role_occurrence_by_id,
            )
            selected_rounding = [
                evidence
                for evidence in equation.get("rounding_evidence", [])
                if evidence["status"] == "ROUNDING_BOUND_SATISFIED_ALL_LANES"
                and evidence["component_roles"] == equation["component_roles_present"]
            ]
            selected_rounding_has_nonzero_residual = len(selected_rounding) == 1 and any(
                lane["residual_number"]["coefficient"] != 0
                for lane in selected_rounding[0]["lanes"]
            )
            if (
                arithmetic_is_exact is rounding_selected
                or (rounding_selected and not selected_rounding_has_nonzero_residual)
                or (not rounding_selected and equation.get("rounding_evidence", []))
            ):
                raise _error("local equation status and exact arithmetic authority drifted")
        elif equation["component_roles_present"]:
            raise _error("local failure status retained selected accounting authority")
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
        "SELECTED_ROUNDING_CORROBORATED_VISIBLE_TRAILING_ROOT_SOURCE",
        "SELECTED_VISIBLE_TRAILING_ROOT_SOURCE",
        "UNRESOLVED_PARTIAL_TRAILING_NUMERIC_CHALLENGER",
        "UNRESOLVED_UNSELECTED_COMPLETE_TRAILING_NUMERIC_CHALLENGER",
        "UNRESOLVED_UNCLAIMED_TRAILING_NUMERIC_CHALLENGER",
        "UNRESOLVED_SOURCE_ONLY_SCHEMA_INELIGIBLE_ROLE",
        "UNRESOLVED_ONE_EDIT_ROLE_OR_SCOPE_MATCH",
        "UNRESOLVED_ONE_EDIT_COEXTENSIVE_SOURCE_OR_OWNER",
        "UNRESOLVED_SOURCE_ONLY_INTERNAL_NUMERIC_CLUSTER",
        "UNRESOLVED_OFF_LANE_NUMERIC_SOURCE_ONLY",
        _EXTREME_MARGIN_FURNITURE_DISPOSITION,
        _UNLABELED_EXACT_SUBTOTAL_CORROBORATION,
        _UNLABELED_AMBIGUOUS_SUBTOTAL_DISPOSITION,
        _LOCAL_TRAILING_SUBGROUP_SUBTOTAL_CORROBORATION,
    }
    unlabeled_exact_subtotal_target_roles = {
        equation["result_role"]
        for equation in value["equations"]["global"]
        if equation["status"] == "DERIVED_EXACT_EXHAUSTIVE_COMPONENT_SUM"
        and equation["component_roles_present"]
    } & {
        *_UNLABELED_EXACT_SUBTOTAL_TARGET_ROLES,
        *_SEALED_DEPOSIT_SUBGROUP_COMPONENT_ROLES,
    }
    unlabeled_exact_subtotal_target_roles.update(
        equation["result_role"]
        for equation in value["equations"]["local"]
        if equation["status"] == "LOCAL_TRAILING_SUBTOTAL_CORROBORATED_BY_EXACT_SCOPED_COMPONENTS"
        and equation["component_roles_present"]
    )
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
                "AUTHENTICATED_EXTREME_MARGIN_FURNITURE",
                "INTERNAL_UNASSIGNED_NUMERIC_CLUSTER",
                "ROLE_ROW",
                "TRAILING_VALUE_ROW",
            }
            or (
                record["row_kind"] == "AUTHENTICATED_EXTREME_MARGIN_FURNITURE"
                and (
                    record["candidate_ordinal"] is not None
                    or record["occurrence_id"] is not None
                    or record["role"] is not None
                    or record["disposition"] != _EXTREME_MARGIN_FURNITURE_DISPOSITION
                    or record["source_record"].get("evidence_id")
                    not in {
                        evidence.get("evidence_id")
                        for evidence in value["authenticated_extreme_margin_furniture_evidence"]
                        if type(evidence) is dict
                    }
                )
            )
            or (
                record["row_kind"] == "INTERNAL_UNASSIGNED_NUMERIC_CLUSTER"
                and (
                    record["candidate_ordinal"] is not None
                    or (
                        record["disposition"] in _UNLABELED_SOURCE_SUBTOTAL_DISPOSITIONS
                        and (
                            (
                                record["occurrence_id"] is not None
                                and record["occurrence_id"] not in occurrence_ids
                            )
                            or record["role"] not in unlabeled_exact_subtotal_target_roles
                        )
                    )
                    or (
                        record["disposition"] not in _UNLABELED_SOURCE_SUBTOTAL_DISPOSITIONS
                        and (
                            record["occurrence_id"] is not None
                            or record["role"] is not None
                            or record["disposition"]
                            not in {
                                "UNRESOLVED_SOURCE_ONLY_INTERNAL_NUMERIC_CLUSTER",
                                "UNRESOLVED_OFF_LANE_NUMERIC_SOURCE_ONLY",
                            }
                        )
                    )
                    or record["source_record"].get("cluster_id")
                    not in {
                        cluster.get("cluster_id")
                        for cluster in value["internal_unassigned_numeric_clusters"]
                        if type(cluster) is dict
                    }
                )
            )
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
                    or record["disposition"]
                    not in {
                        "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_ALREADY_OWNED",
                        "UNRESOLVED_ONE_EDIT_COEXTENSIVE_SOURCE_OR_OWNER",
                    }
                )
            )
            or (
                record["row_kind"] == "TRAILING_VALUE_ROW"
                and (
                    type(record["candidate_ordinal"]) is not int
                    or record["candidate_ordinal"] < 0
                    or record["source_record"].get("candidate_ordinal")
                    != record["candidate_ordinal"]
                    or (
                        record["disposition"] in _UNLABELED_SOURCE_SUBTOTAL_DISPOSITIONS
                        and (
                            (
                                record["occurrence_id"] is not None
                                and record["occurrence_id"] not in occurrence_ids
                            )
                            or record["role"] not in unlabeled_exact_subtotal_target_roles
                        )
                    )
                    or (
                        record["disposition"] not in _UNLABELED_SOURCE_SUBTOTAL_DISPOSITIONS
                        and (record["occurrence_id"] is not None or record["role"] is not None)
                    )
                )
            )
            or record["sample_ids"]
            != (
                record["source_record"].get("sample_ids", [])
                if record["row_kind"] == "INTERNAL_UNASSIGNED_NUMERIC_CLUSTER"
                else [record["source_record"].get("sample_id")]
                if record["row_kind"] == "AUTHENTICATED_EXTREME_MARGIN_FURNITURE"
                else [item.get("sample_id") for item in record["source_record"].get("values", [])]
            )
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
    for receipt in value["coverage_receipt"]:
        if receipt["disposition"] == "UNRESOLVED_SOURCE_ONLY_SCHEMA_INELIGIBLE_ROLE":
            occurrence = occurrence_by_id.get(receipt["occurrence_id"])
            scope_binding = (
                occurrence.get("source_scope_binding") if type(occurrence) is dict else None
            )
            reason_prefix = (
                "SOURCE_ONLY_AMBIGUOUS_TOUCHING_WRAPPED_LABEL"
                if type(scope_binding) is dict
                and scope_binding.get("status") == occurrence_v2._AMBIGUOUS_WRAPPED_LABEL_STATUS  # noqa: SLF001
                else "SOURCE_ONLY_SCHEMA_INELIGIBLE_ROLE"
            )
            if (
                f"{reason_prefix}:{receipt['role']}:{receipt['occurrence_id']}"
                not in value["unresolved_reasons"]
            ):
                raise _error("source-only schema-ineligible receipt did not veto closure")
        if receipt["disposition"] == "UNRESOLVED_ONE_EDIT_ROLE_OR_SCOPE_MATCH":
            occurrence = occurrence_by_id.get(receipt["occurrence_id"])
            if (
                type(occurrence) is not dict
                or not (
                    str(
                        receipt["source_record"].get("label_match", {}).get("match_kind", "")
                    ).startswith("ONE_EDIT_")
                    or str(occurrence.get("scope_owner_match_kind", "")).startswith("ONE_EDIT_")
                )
                or (
                    f"ONE_EDIT_ROLE_OR_SCOPE_MATCH_SCHEMA_INELIGIBLE:{receipt['role']}:"
                    f"{receipt['occurrence_id']}" not in value["unresolved_reasons"]
                )
            ):
                raise _error("one-edit source receipt did not veto closure")
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
                expected_receipt["disposition"] == "UNRESOLVED_ONE_EDIT_COEXTENSIVE_SOURCE_OR_OWNER"
                and (
                    f"ONE_EDIT_COEXTENSIVE_SOURCE_OR_OWNER_SCHEMA_INELIGIBLE:"
                    f"{evidence['projected_role']}:{projected_id}"
                    not in value["unresolved_reasons"]
                )
            )
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
    _validate_unlabeled_exact_subtotal_receipts(value)
    _validate_numeric_sample_coverage(value)
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
            and disposition
            not in {
                "UNRESOLVED_UNCLAIMED_TRAILING_NUMERIC_CHALLENGER",
                *_UNLABELED_SOURCE_SUBTOTAL_DISPOSITIONS,
            }
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
    hierarchy_spec_sha256 = canonical_json_sha256_v1(spec)
    if axis["family_id"] != spec["family_id"]:
        raise _error("scoped hierarchy family differs from its occurrence axis")
    row_axis = axis["row_axis"]
    reasons = list(axis["unresolved_reasons"])
    numeric_rows = [row for row in row_axis["rows"] if row["values"]]
    source_only_occurrences, one_edit_occurrences, source_role_reasons = _source_role_vetoes(
        numeric_rows,
        axis["role_occurrences"],
        spec["source_role_policy"],
        axis["one_edit_exact_source_structural_proofs"],
    )
    reasons.extend(source_role_reasons)
    occurrence_by_id = {
        occurrence["occurrence_id"]: occurrence for occurrence in axis["role_occurrences"]
    }
    bound_one_edit_retrieval_occurrence_ids = {
        check["occurrence_id"]
        for check in axis["one_edit_exact_source_structural_proofs"]["checks"]
        if check["match_scope"] == "EXPANDED_OCCURRENCE"
        and check["status"] in occurrence_v2._ONE_EDIT_AUTHORITY_BOUND_STATUSES  # noqa: SLF001
    }
    bound_one_edit_family_parent = any(
        check["match_scope"] == "FAMILY_PARENT"
        and check["status"] in occurrence_v2._ONE_EDIT_AUTHORITY_BOUND_STATUSES  # noqa: SLF001
        for check in axis["one_edit_exact_source_structural_proofs"]["checks"]
    )

    def one_edit_source_or_owner_is_unbound(
        occurrence: Mapping[str, Any], *, source_match_kind: Any = None
    ) -> bool:
        source_unbound = str(source_match_kind).startswith("ONE_EDIT_") and (
            occurrence["retrieval_occurrence_id"] not in bound_one_edit_retrieval_occurrence_ids
        )
        label_unbound = str(occurrence["label_match"].get("match_kind", "")).startswith(
            "ONE_EDIT_"
        ) and (occurrence["retrieval_occurrence_id"] not in bound_one_edit_retrieval_occurrence_ids)
        owner_unbound = str(occurrence["scope_owner_match_kind"]).startswith("ONE_EDIT_") and (
            (occurrence["scope_owner_role"] is None and not bound_one_edit_family_parent)
            or (
                occurrence["scope_owner_role"] is not None
                and occurrence_by_id[occurrence["scope_owner_occurrence_id"]][
                    "retrieval_occurrence_id"
                ]
                not in bound_one_edit_retrieval_occurrence_ids
            )
        )
        return source_unbound or label_unbound or owner_unbound

    coextensive_one_edit_occurrences: set[str] = set()
    if spec["source_role_policy"]["one_edit_role_or_scope_match_policy"] == "VETO":
        for evidence in axis["coextensive_structural_numeric_evidence"]:
            if evidence["status"] != _COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_STATUS:
                continue
            projected = occurrence_by_id[evidence["projected_occurrence_id"]]
            owner = occurrence_by_id[evidence["owner_occurrence_id"]]
            if one_edit_source_or_owner_is_unbound(
                projected,
                source_match_kind=evidence["source_record"]["label_match"].get("match_kind"),
            ) or one_edit_source_or_owner_is_unbound(owner):
                occurrence_id = evidence["projected_occurrence_id"]
                coextensive_one_edit_occurrences.add(occurrence_id)
                reasons.append(
                    "ONE_EDIT_COEXTENSIVE_SOURCE_OR_OWNER_SCHEMA_INELIGIBLE:"
                    f"{evidence['projected_role']}:{occurrence_id}"
                )
    accounting_rows = [
        row
        for row in row_axis["rows"]
        if row["label_match"].get("occurrence_id")
        not in source_only_occurrences | one_edit_occurrences
    ]
    valued_rows = [row for row in accounting_rows if row["status"] == "VISIBLE_VALUE_LANES_BOUND"]
    aggregate_roles = set(spec["repeated_role_policy"]["aggregate_roles"])
    allow_rounding = spec["format_version"] == SPEC_FORMAT_VERSION_V2
    local_records = []
    local_roles = set(spec["repeated_role_policy"]["local_subtotal_roles"])
    locally_valid_results: set[str] = set()
    locally_authorized_component_scopes: set[str] = set()
    locally_covered_components: set[str] = set()
    source_candidates = _numeric_source_candidate_axis(
        axis["numeric_sample_universe"],
        axis["internal_unassigned_numeric_clusters"],
        row_axis["trailing_value_rows"],
    )
    provisional_local_trailing_subtotals: list[dict[str, Any]] = []
    for equation in spec["equations"]:
        if equation["result_role"] in local_roles:
            (
                records,
                valid_results,
                authorized_component_scopes,
                covered_components,
                local_reasons,
            ) = _local_equations(
                equation,
                accounting_rows,
                axis["role_occurrences"],
                allow_rounding=allow_rounding,
            )
            local_records.extend(records)
            locally_valid_results.update(valid_results)
            locally_authorized_component_scopes.update(authorized_component_scopes)
            locally_covered_components.update(covered_components)
            reasons.extend(local_reasons)
            local_trailing_subtotal = _local_trailing_subgroup_subtotal_receipt(
                accounting_rows=accounting_rows,
                equation=equation,
                family_id=spec["family_id"],
                hierarchy_spec_sha256=hierarchy_spec_sha256,
                local_records=records,
                numeric_sample_universe=axis["numeric_sample_universe"],
                role_occurrences=axis["role_occurrences"],
                row_axis=row_axis,
                source_candidates=source_candidates,
            )
            if local_trailing_subtotal is not None:
                provisional_local_trailing_subtotals.append(local_trailing_subtotal)
    resolved, _source_occurrences, repeated_reasons = _aggregate_source_roles(
        valued_rows,
        aggregate_roles,
        local_roles,
        {
            role
            for role, role_kind in spec["role_kind_by_role"].items()
            if role_kind == "NONADDITIVE_CHILD"
        },
        locally_valid_results,
        locally_authorized_component_scopes,
    )
    reasons.extend(repeated_reasons)
    reserved_unlabeled_source_keys: set[tuple[str, str | int]] = set()
    unlabeled_subtotal_by_source_key: dict[tuple[str, str | int], dict[str, Any]] = {}
    for evidence in provisional_local_trailing_subtotals:
        if _local_trailing_subgroup_has_equal_vector_collision(
            evidence,
            spec["equations"],
            resolved,
            axis["role_occurrences"],
        ):
            reasons.append(
                "LOCAL_TRAILING_SUBGROUP_SUBTOTAL_EQUAL_VECTOR_COLLISION_VETO:"
                + evidence["role"]
                + ":"
                + str(evidence["candidate_ordinal"])
            )
            continue
        matching_records = [
            record
            for record in local_records
            if record["result_occurrence_id"] == evidence["occurrence_id"]
            and record["result_role"] == evidence["role"]
        ]
        if len(matching_records) != 1 or evidence["source_key"] in (reserved_unlabeled_source_keys):
            raise _error("local trailing subgroup subtotal selection axis drifted")
        local_record = matching_records[0]
        local_record["component_roles_present"] = canonical_clone_v1(
            evidence["receipt"]["component_roles"]
        )
        local_record["local_trailing_subgroup_subtotal_receipt"] = canonical_clone_v1(
            evidence["receipt"]
        )
        local_record["status"] = "LOCAL_TRAILING_SUBTOTAL_CORROBORATED_BY_EXACT_SCOPED_COMPONENTS"
        locally_valid_results.add(evidence["occurrence_id"])
        locally_authorized_component_scopes.add(evidence["occurrence_id"])
        locally_covered_components.update(evidence["receipt"]["component_occurrence_ids"])
        resolved[evidence["role"]] = canonical_clone_v1(evidence["resolution"])
        reserved_unlabeled_source_keys.add(evidence["source_key"])
        unlabeled_subtotal_by_source_key[evidence["source_key"]] = evidence
    global_records = []
    for equation in spec["equations"]:
        available_trailing_rows = [
            row
            for row in row_axis["trailing_value_rows"]
            if ("trailing", row["candidate_ordinal"]) not in reserved_unlabeled_source_keys
        ]
        record, equation_reasons = _select_global_equation(
            equation,
            resolved,
            available_trailing_rows,
            allow_rounding=allow_rounding,
        )
        global_records.append(record)
        reasons.extend(equation_reasons)
        unlabeled_subtotal = (
            None
            if record["result_role"] in _SEALED_DEPOSIT_SUBGROUP_COMPONENT_ROLES
            else _unlabeled_exact_subtotal_for_equation(
                equation_record=record,
                family_id=spec["family_id"],
                numeric_sample_universe=axis["numeric_sample_universe"],
                reserved_source_keys=reserved_unlabeled_source_keys,
                resolved_by_role=resolved,
                role_occurrences=axis["role_occurrences"],
                source_candidates=source_candidates,
                authenticated_extreme_margin_furniture_evidence=axis[
                    "authenticated_extreme_margin_furniture_evidence"
                ],
            )
        )
        if unlabeled_subtotal is not None:
            source_key = unlabeled_subtotal["source_key"]
            reserved_unlabeled_source_keys.add(source_key)
            unlabeled_subtotal_by_source_key[source_key] = unlabeled_subtotal
            if unlabeled_subtotal["disposition"] == _UNLABELED_AMBIGUOUS_SUBTOTAL_DISPOSITION:
                reasons.append(
                    "AMBIGUOUS_UNLABELED_SUBTOTAL_SOURCE:"
                    + unlabeled_subtotal["role"]
                    + ":"
                    + str(source_key[0])
                    + ":"
                    + str(source_key[1])
                )
    for subgroup_role in _SEALED_DEPOSIT_SUBGROUP_COMPONENT_ROLES:
        subgroup_records = [
            record for record in global_records if record["result_role"] == subgroup_role
        ]
        if len(subgroup_records) == 1:
            subgroup_subtotal = _unlabeled_exact_subtotal_for_equation(
                equation_record=subgroup_records[0],
                family_id=spec["family_id"],
                numeric_sample_universe=axis["numeric_sample_universe"],
                reserved_source_keys=set(),
                resolved_by_role=resolved,
                role_occurrences=axis["role_occurrences"],
                source_candidates=source_candidates,
                authenticated_extreme_margin_furniture_evidence=axis[
                    "authenticated_extreme_margin_furniture_evidence"
                ],
                equation_records=global_records,
            )
        else:
            subgroup_subtotal = None
        if subgroup_subtotal is not None:
            source_key = subgroup_subtotal["source_key"]
            if source_key in unlabeled_subtotal_by_source_key:
                unlabeled_subtotal_by_source_key.pop(source_key)
                reserved_unlabeled_source_keys.discard(source_key)
                reasons.append(
                    "AMBIGUOUS_UNLABELED_SUBTOTAL_MULTI_EQUATION_CLAIM:"
                    + str(source_key[0])
                    + ":"
                    + str(source_key[1])
                )
            else:
                reserved_unlabeled_source_keys.add(source_key)
                unlabeled_subtotal_by_source_key[source_key] = subgroup_subtotal
    corroborated_occurrence_ids = {
        evidence["occurrence_id"]
        for evidence in unlabeled_subtotal_by_source_key.values()
        if evidence["disposition"]
        in {
            _UNLABELED_EXACT_SUBTOTAL_CORROBORATION,
            _LOCAL_TRAILING_SUBGROUP_SUBTOTAL_CORROBORATION,
        }
    }
    incomplete_rows = [
        row for row in row_axis["rows"] if row["status"] != "VISIBLE_VALUE_LANES_BOUND"
    ]
    if incomplete_rows and all(
        row["label_match"].get("occurrence_id") in corroborated_occurrence_ids and not row["values"]
        for row in incomplete_rows
    ):
        reasons = [
            reason
            for reason in reasons
            if reason != "VISIBLE_ROLE_OCCURRENCE_ROW_LANES_NOT_COMPLETE"
        ]
    elif axis["status"] != (
        "OCCURRENCE_ROW_AXIS_BOUND_WITH_AUTHENTICATED_EXISTING_DASHES_PROPOSAL_ONLY"
    ):
        reasons.append("VISIBLE_ROLE_OCCURRENCE_ROW_LANES_NOT_COMPLETE")
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
        if occurrence_id in source_only_occurrences:
            disposition = "UNRESOLVED_SOURCE_ONLY_SCHEMA_INELIGIBLE_ROLE"
        elif occurrence_id in one_edit_occurrences:
            disposition = "UNRESOLVED_ONE_EDIT_ROLE_OR_SCOPE_MATCH"
        elif row["status"] != "VISIBLE_VALUE_LANES_BOUND":
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
                "disposition": (
                    "UNRESOLVED_ONE_EDIT_COEXTENSIVE_SOURCE_OR_OWNER"
                    if occurrence_id in coextensive_one_edit_occurrences
                    else "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_ALREADY_OWNED"
                ),
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
        unlabeled_subtotal = unlabeled_subtotal_by_source_key.get(("trailing", ordinal))
        if unlabeled_subtotal is not None and ordinal in trailing_disposition_by_ordinal:
            raise _error("unlabeled subtotal is also claimed as a global trailing result")
        disposition = trailing_disposition_by_ordinal.get(
            ordinal, "UNRESOLVED_UNCLAIMED_TRAILING_NUMERIC_CHALLENGER"
        )
        if unlabeled_subtotal is not None:
            disposition = unlabeled_subtotal["disposition"]
        elif disposition == "UNRESOLVED_UNCLAIMED_TRAILING_NUMERIC_CHALLENGER":
            reasons.append(f"UNCLAIMED_TRAILING_NUMERIC_ROW:{ordinal}")
        coverage_receipt.append(
            {
                "candidate_ordinal": ordinal,
                "coverage_id": (
                    (
                        "ashtcv2:coverage:local-trailing-subgroup-subtotal:"
                        if unlabeled_subtotal is not None
                        and unlabeled_subtotal["disposition"]
                        == _LOCAL_TRAILING_SUBGROUP_SUBTOTAL_CORROBORATION
                        else "ashtcv2:coverage:unlabeled-exact-subtotal:"
                    )
                    + unlabeled_subtotal["role"]
                    + f":trailing:{ordinal}"
                    if unlabeled_subtotal is not None
                    else f"ashtcv2:coverage:trailing:{ordinal}"
                ),
                "disposition": disposition,
                "occurrence_id": (
                    unlabeled_subtotal["occurrence_id"] if unlabeled_subtotal is not None else None
                ),
                "role": unlabeled_subtotal["role"] if unlabeled_subtotal is not None else None,
                "row_kind": "TRAILING_VALUE_ROW",
                "sample_ids": [value["sample_id"] for value in trailing["values"]],
                "source_record": canonical_clone_v1(trailing),
            }
        )
    for cluster in axis["internal_unassigned_numeric_clusters"]:
        cluster_id = cluster["cluster_id"]
        off_lane = cluster["status"] == occurrence_v2._OFF_LANE_NUMERIC_CLUSTER_STATUS
        unlabeled_subtotal = unlabeled_subtotal_by_source_key.get(("cluster", cluster_id))
        if unlabeled_subtotal is None:
            reasons.append(
                (
                    "OFF_LANE_NUMERIC_SOURCE_ONLY_VETO:"
                    if off_lane
                    else "SOURCE_ONLY_INTERNAL_NUMERIC_CLUSTER_VETO:"
                )
                + cluster_id
            )
        coverage_receipt.append(
            {
                "candidate_ordinal": None,
                "coverage_id": (
                    (
                        "ashtcv2:coverage:local-trailing-subgroup-subtotal:"
                        if unlabeled_subtotal is not None
                        and unlabeled_subtotal["disposition"]
                        == _LOCAL_TRAILING_SUBGROUP_SUBTOTAL_CORROBORATION
                        else "ashtcv2:coverage:unlabeled-exact-subtotal:"
                    )
                    + unlabeled_subtotal["role"]
                    + ":cluster:"
                    + cluster_id
                    if unlabeled_subtotal is not None
                    else "ashtcv2:coverage:source-only:" + cluster_id
                ),
                "disposition": (
                    unlabeled_subtotal["disposition"]
                    if unlabeled_subtotal is not None
                    else "UNRESOLVED_OFF_LANE_NUMERIC_SOURCE_ONLY"
                    if off_lane
                    else "UNRESOLVED_SOURCE_ONLY_INTERNAL_NUMERIC_CLUSTER"
                ),
                "occurrence_id": (
                    unlabeled_subtotal["occurrence_id"] if unlabeled_subtotal is not None else None
                ),
                "role": unlabeled_subtotal["role"] if unlabeled_subtotal is not None else None,
                "row_kind": "INTERNAL_UNASSIGNED_NUMERIC_CLUSTER",
                "sample_ids": canonical_clone_v1(cluster["sample_ids"]),
                "source_record": canonical_clone_v1(cluster),
            }
        )
    for evidence in axis["authenticated_extreme_margin_furniture_evidence"]:
        evidence_id = evidence["evidence_id"]
        coverage_receipt.append(
            {
                "candidate_ordinal": None,
                "coverage_id": "ashtcv2:coverage:extreme-margin-furniture:" + evidence_id,
                "disposition": _EXTREME_MARGIN_FURNITURE_DISPOSITION,
                "occurrence_id": None,
                "role": None,
                "row_kind": "AUTHENTICATED_EXTREME_MARGIN_FURNITURE",
                "sample_ids": [evidence["sample_id"]],
                "source_record": canonical_clone_v1(evidence),
            }
        )
    reasons = list(dict.fromkeys(reasons))
    resolved_axis = []
    for record in resolved.values():
        public_record = canonical_clone_v1(record)
        public_record.pop(_PRINTED_SOURCE_CELLS_KEY, None)
        resolved_axis.append(public_record)
    equation_axis = {"global": global_records, "local": local_records}
    material = {
        "authenticated_extreme_margin_furniture_evidence": canonical_clone_v1(
            axis["authenticated_extreme_margin_furniture_evidence"]
        ),
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
        "internal_unassigned_numeric_clusters": canonical_clone_v1(
            axis["internal_unassigned_numeric_clusters"]
        ),
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
        "numeric_sample_universe": canonical_clone_v1(axis["numeric_sample_universe"]),
        "one_edit_exact_source_structural_proofs": canonical_clone_v1(
            axis["one_edit_exact_source_structural_proofs"]
        ),
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
    """Close exact-or-receipted-rounding subtotals and disjoint repeated roles."""

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
    """Rebuild exact-or-rounding local/global equations from the occurrence axis."""

    persisted = _validate_result(value)
    expected = build_accounting_scoped_hierarchical_table_closure_v2(
        occurrence_axis, family_topology_spec, hierarchy_spec
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("scoped hierarchical closure does not replay exactly")
    return persisted
