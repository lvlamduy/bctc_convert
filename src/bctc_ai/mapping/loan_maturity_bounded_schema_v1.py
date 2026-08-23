"""Append-stable, family-bounded TM schema identity for loan maturity.

The projection deliberately authenticates only the semantic nodes and edges
that can affect this family.  Universal-schema counters, authority file hashes,
and workbook display positions are excluded, so an unrelated append cannot
invalidate a previously verified maturity result.
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
    "LoanMaturityBoundedSchemaV1Error",
    "build_live_loan_maturity_bounded_schema_projection_v1",
    "build_loan_maturity_bounded_schema_projection_v1",
    "validate_loan_maturity_bounded_schema_projection_replay_v1",
    "validate_loan_maturity_bounded_schema_projection_v1",
]


FORMAT_VERSION = "LOAN_MATURITY_BOUNDED_TM_SCHEMA_PROJECTION_V1"
FAMILY_ID = "LOAN_MATURITY_BUCKETS"
CLAIM_BOUNDARY = (
    "LIVE_TM_SCHEMA_SEMANTIC_IDENTITY_EDGES_CONTEXT_ELIGIBILITY_AND_CLOSED_FAMILY_"
    "POPULATION_ONLY_NO_GLOBAL_SCHEMA_REVISION_FILE_HASH_DISPLAY_ORDER_SOURCE_MAPPING_"
    "VALUE_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_EXPECTED_NAMES = {
    716: "Cho vay khách hàng",
    752: "Phân tích dư nợ theo thời gian đáo hạn",
    753: "+ Ngắn hạn",
    754: "+ Trung hạn",
    755: "+ Dài hạn",
    5747: "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
    1944: "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
}
_EXPECTED_PARENTS = {716: 560, 752: 716, 753: 752, 754: 752, 755: 752, 5747: 752, 1944: None}
_ROLE_IDS = {"SHORT_TERM": 753, "MEDIUM_TERM": 754, "LONG_TERM": 755}
_TARGET_IDS = frozenset(_EXPECTED_NAMES)
_MAPPED_CHILD_IDS = frozenset((*_ROLE_IDS.values(), 5747))
_SAFETY = {
    "absolute_display_order_in_identity": False,
    "global_schema_file_hashes_in_identity": False,
    "global_schema_item_count_in_identity": False,
    "global_schema_revision_in_identity": False,
    "new_unclassified_mapping_eligible_child_fails_closed": True,
    "parent_716_emitted_as_mapping": False,
    "parent_752_emitted_as_mapping": False,
    "source_totals_have_report_norm_id": False,
}


class LoanMaturityBoundedSchemaV1Error(ValueError):
    """The bounded maturity schema identity or exact replay drifted."""


def _error(message: str) -> LoanMaturityBoundedSchemaV1Error:
    return LoanMaturityBoundedSchemaV1Error(message)


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
    parent = _EXPECTED_PARENTS.get(identifier)
    if (
        expected_name is None
        or getattr(schema, "canonical_name", None) != expected_name
        or getattr(schema, "statement_type", None) != "TM"
        or getattr(schema, "parent_id", None) != parent
        or getattr(context, "report_norm_id", None) != identifier
        or getattr(context, "canonical_name", None) != expected_name
        or getattr(context, "statement_type", None) != "TM"
        or getattr(context, "parent_report_norm_id", None) != parent
    ):
        raise _error(f"bounded TM identity drifted for ReportNormId {identifier}")
    eligible = identifier != 1944
    expected_context_status = "RESOLVED" if eligible else "UNRESOLVED_ORPHAN"
    expected_section = "BALANCE_SHEET_NOTES" if eligible else None
    expected_section_root = 560 if eligible else None
    expected_family_root = 716 if eligible else None
    expected_path = {
        716: (560, 716),
        752: (560, 716, 752),
        753: (560, 716, 752, 753),
        754: (560, 716, 752, 754),
        755: (560, 716, 752, 755),
        5747: (560, 716, 752, 5747),
        1944: (1944,),
    }[identifier]
    expected_level = {716: 1, 752: 2, 753: 3, 754: 3, 755: 3, 5747: 3, 1944: None}[identifier]
    if (
        getattr(context, "context_status", None) != expected_context_status
        or getattr(context, "mapping_eligible", None) is not eligible
        or getattr(context, "section", None) != expected_section
        or getattr(context, "section_root_id", None) != expected_section_root
        or getattr(context, "note_family_root_id", None) != expected_family_root
        or tuple(getattr(context, "ancestor_path", ())) != expected_path
        or getattr(context, "derived_hierarchy_level", None) != expected_level
    ):
        raise _error(f"bounded TM context drifted for ReportNormId {identifier}")
    scope = _list(getattr(schema, "scope", None), "bounded schema scope")
    periods = _list(getattr(schema, "allowed_period_type", None), "bounded schema period policy")
    signs = _list(getattr(schema, "allowed_sign", None), "bounded schema sign policy")
    if scope != ["SEPARATE", "CONSOLIDATED"] or periods != ["SNAPSHOT", "DURATION"]:
        raise _error(f"bounded TM scope/period policy drifted for ReportNormId {identifier}")
    if signs != ["POSITIVE", "NEGATIVE", "ZERO"]:
        raise _error(f"bounded TM sign policy drifted for ReportNormId {identifier}")
    return {
        "allowed_period_types": periods,
        "allowed_scopes": scope,
        "allowed_signs": signs,
        "ancestor_path": list(expected_path),
        "canonical_name": expected_name,
        "context_status": expected_context_status,
        "disposition": disposition,
        "hierarchy_level": expected_level,
        "mapping_eligible": eligible,
        "note_family_root_report_norm_id": expected_family_root,
        "parent_report_norm_id": parent,
        "report_norm_id": identifier,
        "section": expected_section,
        "section_root_report_norm_id": expected_section_root,
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
        "negative_context",
        "owner_context",
        "projection_id",
        "safety",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error("bounded maturity schema projection fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["safety"] != _SAFETY
    ):
        raise _error("bounded maturity schema projection contract drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("projection_id")
    if identity != "lmbspv1:projection:" + canonical_json_sha256_v1(material):
        raise _error("bounded maturity schema projection identity drifted")
    if [item.get("role") for item in value["mapped_roles"]] != [
        "SHORT_TERM",
        "MEDIUM_TERM",
        "LONG_TERM",
        "MARGIN_AND_SECURITIES_ADVANCE",
    ]:
        raise _error("bounded maturity mapped-role order drifted")
    if [item.get("report_norm_id") for item in value["mapped_roles"]] != [753, 754, 755, 5747]:
        raise _error("bounded maturity mapped identities drifted")
    if (
        value["owner_context"].get("report_norm_id") != 716
        or value["family_context"].get("report_norm_id") != 752
    ):
        raise _error("bounded maturity context identities drifted")
    if [item.get("report_norm_id") for item in value["negative_context"]] != [1944]:
        raise _error("bounded maturity negative identity drifted")
    return canonical_clone_v1(value)


def build_loan_maturity_bounded_schema_projection_v1(
    schema_items: Mapping[int, Any] | Sequence[Any],
    tm_contexts: Mapping[int, Any] | Sequence[Any],
) -> dict[str, Any]:
    """Project and validate only the live schema slice governing Family 9."""

    schema = _by_id(schema_items, "schema_id")
    contexts = _by_id(tm_contexts, "report_norm_id")
    if not _TARGET_IDS <= schema.keys() or not _TARGET_IDS <= contexts.keys():
        raise _error("bounded maturity target schema/context is incomplete")
    if 752 not in _list(getattr(schema[716], "children", None), "owner children"):
        raise _error("loan-maturity family is not a child of customer loans")
    direct_children = _list(getattr(schema[752], "children", None), "family children")
    if not _MAPPED_CHILD_IDS <= set(direct_children):
        raise _error("loan-maturity family lacks one required classified child")
    for child_id in direct_children:
        if child_id in _MAPPED_CHILD_IDS:
            continue
        context = contexts.get(child_id)
        if context is None or getattr(context, "mapping_eligible", None) is not False:
            raise _error(
                f"unclassified mapping-eligible child {child_id} appeared under ReportNormId 752"
            )
    owner = _node(schema[716], contexts[716], disposition="OWNER_CONTEXT_ONLY_NOT_EMITTED")
    family = _node(schema[752], contexts[752], disposition="FAMILY_CONTEXT_ONLY_NOT_EMITTED")
    roles = []
    for role, identifier in _ROLE_IDS.items():
        roles.append(
            {
                **_node(
                    schema[identifier], contexts[identifier], disposition="REQUIRED_VALUE_MAPPING"
                ),
                "presence": "REQUIRED",
                "role": role,
            }
        )
    roles.append(
        {
            **_node(schema[5747], contexts[5747], disposition="OPTIONAL_VALUE_MAPPING"),
            "presence": "OPTIONAL_WHEN_SOURCE_VISIBLE",
            "role": "MARGIN_AND_SECURITIES_ADVANCE",
        }
    )
    negative = _node(
        schema[1944], contexts[1944], disposition="NEGATIVE_ORPHAN_NEVER_MAP_IN_FAMILY_9"
    )
    material = {
        "accounting_population_policy": {
            "additional_source_population_report_norm_id": None,
            "grand_total_report_norm_id": None,
            "mapped_parent_report_norm_ids": [],
            "optional_margin_report_norm_id": 5747,
            "percentage_companion_report_norm_id": None,
            "source_core_subtotal_report_norm_id": None,
            "strict_core_report_norm_ids": [753, 754, 755],
        },
        "claim_boundary": CLAIM_BOUNDARY,
        "family_context": family,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "mapped_roles": roles,
        "negative_context": [negative],
        "owner_context": owner,
        "safety": canonical_clone_v1(_SAFETY),
    }
    return _validate_projection(
        {**material, "projection_id": "lmbspv1:projection:" + canonical_json_sha256_v1(material)}
    )


def build_live_loan_maturity_bounded_schema_projection_v1(project_root: Path) -> dict[str, Any]:
    """Build the bounded projection from today's live schema without global identity coupling."""

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
        raise _error("live bounded maturity schema could not be reconstructed") from exc
    return build_loan_maturity_bounded_schema_projection_v1(schema, contexts)


def validate_loan_maturity_bounded_schema_projection_v1(value: Any) -> dict[str, Any]:
    """Validate one content-addressed bounded projection."""

    return _validate_projection(value)


def validate_loan_maturity_bounded_schema_projection_replay_v1(
    value: Any,
    schema_items: Mapping[int, Any] | Sequence[Any],
    tm_contexts: Mapping[int, Any] | Sequence[Any],
) -> dict[str, Any]:
    """Rebuild the bounded projection and require exact typed equality."""

    persisted = _validate_projection(value)
    rebuilt = build_loan_maturity_bounded_schema_projection_v1(schema_items, tm_contexts)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("bounded maturity schema projection does not replay exactly")
    return rebuilt
