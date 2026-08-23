"""Append-stable, family-bounded TM schema identity for loan currency.

Only the customer-loan currency branch and its two mapping-eligible leaves are
authenticated.  Global schema hashes, workbook row positions, display order,
and unrelated siblings are deliberately outside the identity so later schema
appends do not invalidate a verified Family 10 result.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import load_all
from bctc_ai.schema.tm_context import (
    TM_CONTEXT_POLICY_RELATIVE_PATH,
    build_tm_schema_context,
    load_tm_context_policy,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "LoanCurrencyBoundedSchemaV1Error",
    "build_live_loan_currency_bounded_schema_projection_v1",
    "build_loan_currency_bounded_schema_projection_v1",
    "validate_loan_currency_bounded_schema_projection_replay_v1",
    "validate_loan_currency_bounded_schema_projection_v1",
]


FORMAT_VERSION = "LOAN_CURRENCY_BOUNDED_TM_SCHEMA_PROJECTION_V1"
FAMILY_ID = "LOAN_CURRENCY_CLASSIFICATION"
CLAIM_BOUNDARY = (
    "LIVE_TM_SCHEMA_SEMANTIC_IDENTITY_EDGES_CONTEXT_ELIGIBILITY_AND_CLOSED_FAMILY_"
    "POPULATION_ONLY_NO_GLOBAL_SCHEMA_REVISION_FILE_HASH_DISPLAY_ORDER_SOURCE_MAPPING_"
    "VALUE_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_EXPECTED_NAMES = {
    716: "Cho vay khách hàng",
    756: "Phân tích theo loại hình tiền tệ",
    757: "+ Cho vay bằng đồng Việt Nam",
    758: "+ Cho vay bằng ngoại tệ và vàng",
}
_EXPECTED_PARENTS = {716: 560, 756: 716, 757: 756, 758: 756}
_EXPECTED_PATHS = {
    716: (560, 716),
    756: (560, 716, 756),
    757: (560, 716, 756, 757),
    758: (560, 716, 756, 758),
}
_EXPECTED_LEVELS = {716: 1, 756: 2, 757: 3, 758: 3}
_ROLE_IDS = {
    "VND_LOANS": 757,
    "FOREIGN_CURRENCY_AND_GOLD_LOANS": 758,
}
_TARGET_IDS = frozenset(_EXPECTED_NAMES)
_MAPPED_CHILD_IDS = frozenset(_ROLE_IDS.values())
_SAFETY = {
    "absolute_display_order_in_identity": False,
    "additional_source_population_has_report_norm_id": False,
    "global_schema_file_hashes_in_identity": False,
    "global_schema_item_count_in_identity": False,
    "global_schema_revision_in_identity": False,
    "new_unclassified_mapping_eligible_child_fails_closed": True,
    "parent_716_emitted_as_mapping": False,
    "parent_756_emitted_as_mapping": False,
    "source_totals_have_report_norm_id": False,
}


class LoanCurrencyBoundedSchemaV1Error(ValueError):
    """The bounded loan-currency schema identity or exact replay drifted."""


def _error(message: str) -> LoanCurrencyBoundedSchemaV1Error:
    return LoanCurrencyBoundedSchemaV1Error(message)


def _by_id(values: Mapping[int, Any] | Sequence[Any], attribute: str) -> dict[int, Any]:
    if isinstance(values, Mapping):
        result = dict(values)
    elif not isinstance(values, (str, bytes, bytearray)) and isinstance(values, Sequence):
        result = {}
        for value in values:
            identifier = getattr(value, attribute, None)
            if type(identifier) is not int or identifier in result:
                raise _error("bounded schema input has a missing or duplicate identity")
            result[identifier] = value
    else:
        raise _error("bounded schema input must be one mapping or sequence")
    if any(type(identifier) is not int for identifier in result):
        raise _error("bounded schema input identifiers drifted")
    return result


def _list(value: Any, label: str) -> list[Any]:
    if type(value) is not list:
        raise _error(f"{label} drifted")
    return list(value)


def _node(schema: Any, context: Any, *, disposition: str) -> dict[str, Any]:
    identifier = getattr(schema, "schema_id", None)
    expected_name = _EXPECTED_NAMES.get(identifier)
    expected_parent = _EXPECTED_PARENTS.get(identifier)
    if (
        expected_name is None
        or getattr(schema, "canonical_name", None) != expected_name
        or getattr(schema, "statement_type", None) != "TM"
        or getattr(schema, "parent_id", None) != expected_parent
        or getattr(context, "report_norm_id", None) != identifier
        or getattr(context, "canonical_name", None) != expected_name
        or getattr(context, "statement_type", None) != "TM"
        or getattr(context, "parent_report_norm_id", None) != expected_parent
        or getattr(context, "context_status", None) != "RESOLVED"
        or getattr(context, "mapping_eligible", None) is not True
        or getattr(context, "section", None) != "BALANCE_SHEET_NOTES"
        or getattr(context, "section_root_id", None) != 560
        or getattr(context, "note_family_root_id", None) != 716
        or tuple(getattr(context, "ancestor_path", ())) != _EXPECTED_PATHS[identifier]
        or getattr(context, "derived_hierarchy_level", None) != _EXPECTED_LEVELS[identifier]
    ):
        raise _error(f"bounded TM identity/context drifted for ReportNormId {identifier}")
    scopes = _list(getattr(schema, "scope", None), "bounded schema scope")
    periods = _list(getattr(schema, "allowed_period_type", None), "bounded schema period policy")
    signs = _list(getattr(schema, "allowed_sign", None), "bounded schema sign policy")
    if scopes != ["SEPARATE", "CONSOLIDATED"] or periods != ["SNAPSHOT", "DURATION"]:
        raise _error(f"bounded TM scope/period policy drifted for ReportNormId {identifier}")
    if signs != ["POSITIVE", "NEGATIVE", "ZERO"]:
        raise _error(f"bounded TM sign policy drifted for ReportNormId {identifier}")
    return {
        "allowed_period_types": periods,
        "allowed_scopes": scopes,
        "allowed_signs": signs,
        "ancestor_path": list(_EXPECTED_PATHS[identifier]),
        "canonical_name": expected_name,
        "context_status": "RESOLVED",
        "disposition": disposition,
        "hierarchy_level": _EXPECTED_LEVELS[identifier],
        "mapping_eligible": True,
        "note_family_root_report_norm_id": 716,
        "parent_report_norm_id": expected_parent,
        "report_norm_id": identifier,
        "section": "BALANCE_SHEET_NOTES",
        "section_root_report_norm_id": 560,
        "statement_type": "TM",
    }


def _expected_projected_node(identifier: int, *, disposition: str) -> dict[str, Any]:
    return {
        "allowed_period_types": ["SNAPSHOT", "DURATION"],
        "allowed_scopes": ["SEPARATE", "CONSOLIDATED"],
        "allowed_signs": ["POSITIVE", "NEGATIVE", "ZERO"],
        "ancestor_path": list(_EXPECTED_PATHS[identifier]),
        "canonical_name": _EXPECTED_NAMES[identifier],
        "context_status": "RESOLVED",
        "disposition": disposition,
        "hierarchy_level": _EXPECTED_LEVELS[identifier],
        "mapping_eligible": True,
        "note_family_root_report_norm_id": 716,
        "parent_report_norm_id": _EXPECTED_PARENTS[identifier],
        "report_norm_id": identifier,
        "section": "BALANCE_SHEET_NOTES",
        "section_root_report_norm_id": 560,
        "statement_type": "TM",
    }


def _validate_projection(value: Any) -> dict[str, Any]:
    fields = {
        "accounting_population_policy",
        "claim_boundary",
        "family_context",
        "family_id",
        "format_version",
        "mapped_roles",
        "owner_context",
        "projection_id",
        "safety",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error("bounded loan-currency schema projection fields drifted")
    expected_owner = _expected_projected_node(716, disposition="OWNER_CONTEXT_ONLY_NOT_EMITTED")
    expected_family = _expected_projected_node(756, disposition="FAMILY_CONTEXT_ONLY_NOT_EMITTED")
    expected_roles = [
        {
            **_expected_projected_node(
                identifier, disposition="REQUIRED_VALUE_MAPPING_WITHIN_ACCEPTED_REGION"
            ),
            "presence": "REQUIRED_WITHIN_ACCEPTED_REGION",
            "role": role,
        }
        for role, identifier in _ROLE_IDS.items()
    ]
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["safety"] != _SAFETY
        or not same_typed_json_v1(value["owner_context"], expected_owner)
        or not same_typed_json_v1(value["family_context"], expected_family)
        or not same_typed_json_v1(value["mapped_roles"], expected_roles)
    ):
        raise _error("bounded loan-currency schema projection contract drifted")
    expected_policy = {
        "additional_source_population_report_norm_ids": [],
        "grand_total_report_norm_id": None,
        "mapped_parent_report_norm_ids": [],
        "source_core_total_report_norm_id": None,
        "strict_mapped_report_norm_ids": [757, 758],
    }
    if value["accounting_population_policy"] != expected_policy:
        raise _error("bounded loan-currency accounting population policy drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("projection_id")
    if identity != "lcbspv1:projection:" + canonical_json_sha256_v1(material):
        raise _error("bounded loan-currency schema projection identity drifted")
    return canonical_clone_v1(value)


def build_loan_currency_bounded_schema_projection_v1(
    schema_items: Mapping[int, Any] | Sequence[Any],
    tm_contexts: Mapping[int, Any] | Sequence[Any],
) -> dict[str, Any]:
    """Project and validate only the live schema slice governing Family 10."""

    schema = _by_id(schema_items, "schema_id")
    contexts = _by_id(tm_contexts, "report_norm_id")
    if not _TARGET_IDS <= schema.keys() or not _TARGET_IDS <= contexts.keys():
        raise _error("bounded loan-currency target schema/context is incomplete")
    if 756 not in _list(getattr(schema[716], "children", None), "owner children"):
        raise _error("loan-currency family is not a child of customer loans")
    direct_children = _list(getattr(schema[756], "children", None), "family children")
    if not _MAPPED_CHILD_IDS <= set(direct_children):
        raise _error("loan-currency family lacks one required classified child")
    for child_id in direct_children:
        if child_id in _MAPPED_CHILD_IDS:
            continue
        context = contexts.get(child_id)
        if context is None or getattr(context, "mapping_eligible", None) is not False:
            raise _error(
                f"unclassified mapping-eligible child {child_id} appeared under ReportNormId 756"
            )
    owner = _node(schema[716], contexts[716], disposition="OWNER_CONTEXT_ONLY_NOT_EMITTED")
    family = _node(schema[756], contexts[756], disposition="FAMILY_CONTEXT_ONLY_NOT_EMITTED")
    mapped_roles = [
        {
            **_node(
                schema[identifier],
                contexts[identifier],
                disposition="REQUIRED_VALUE_MAPPING_WITHIN_ACCEPTED_REGION",
            ),
            "presence": "REQUIRED_WITHIN_ACCEPTED_REGION",
            "role": role,
        }
        for role, identifier in _ROLE_IDS.items()
    ]
    material = {
        "accounting_population_policy": {
            "additional_source_population_report_norm_ids": [],
            "grand_total_report_norm_id": None,
            "mapped_parent_report_norm_ids": [],
            "source_core_total_report_norm_id": None,
            "strict_mapped_report_norm_ids": [757, 758],
        },
        "claim_boundary": CLAIM_BOUNDARY,
        "family_context": family,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "mapped_roles": mapped_roles,
        "owner_context": owner,
        "safety": canonical_clone_v1(_SAFETY),
    }
    return _validate_projection(
        {**material, "projection_id": "lcbspv1:projection:" + canonical_json_sha256_v1(material)}
    )


def build_live_loan_currency_bounded_schema_projection_v1(project_root: Path) -> dict[str, Any]:
    """Build the bounded projection from today's live schema."""

    if not isinstance(project_root, Path):
        raise _error("live bounded schema root must be one pathlib Path")
    root = project_root.resolve()
    try:
        _, schema = load_all(root / "template", root)
        _, hierarchy = load_hierarchy_reference(
            root / "config/schemas/hierarchy_reference.yaml", root, schema
        )
        apply_hierarchy_reference(schema, hierarchy)
        contexts = build_tm_schema_context(
            schema, load_tm_context_policy(root / TM_CONTEXT_POLICY_RELATIVE_PATH)
        )
    except (OSError, ValueError) as exc:
        raise _error("live bounded loan-currency schema could not be reconstructed") from exc
    return build_loan_currency_bounded_schema_projection_v1(schema, contexts)


def validate_loan_currency_bounded_schema_projection_v1(value: Any) -> dict[str, Any]:
    """Validate one content-addressed bounded projection."""

    return _validate_projection(value)


def validate_loan_currency_bounded_schema_projection_replay_v1(
    value: Any,
    schema_items: Mapping[int, Any] | Sequence[Any],
    tm_contexts: Mapping[int, Any] | Sequence[Any],
) -> dict[str, Any]:
    """Rebuild the bounded projection and require exact typed equality."""

    persisted = _validate_projection(value)
    rebuilt = build_loan_currency_bounded_schema_projection_v1(schema_items, tm_contexts)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("bounded loan-currency schema projection does not replay exactly")
    return rebuilt
