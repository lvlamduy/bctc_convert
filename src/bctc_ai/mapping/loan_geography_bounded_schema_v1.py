"""Append-stable TM schema identity for customer-loan geography totals.

The current source-total contract emits only the domestic and foreign totals
under ReportNormId 759.  The five existing domestic-region descendants are
authenticated as known schema context, but are deliberately outside this
contract until source evidence exercises those more detailed populations.

Only semantic node identities, hierarchy edges, TM context, eligibility and
the closed relevant child populations enter the projection identity.  Global
schema hashes, workbook positions, display order and unrelated appends do not.
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
    "LoanGeographyBoundedSchemaV1Error",
    "build_live_loan_geography_bounded_schema_projection_v1",
    "build_loan_geography_bounded_schema_projection_v1",
    "validate_loan_geography_bounded_schema_projection_replay_v1",
    "validate_loan_geography_bounded_schema_projection_v1",
]


FORMAT_VERSION = "LOAN_GEOGRAPHY_BOUNDED_TM_SCHEMA_PROJECTION_V1"
FAMILY_ID = "LOAN_GEOGRAPHIC_CLASSIFICATION"
CLAIM_BOUNDARY = (
    "LIVE_TM_SCHEMA_SEMANTIC_IDENTITY_EDGES_CONTEXT_ELIGIBILITY_CLOSED_DIRECT_"
    "AND_NESTED_FAMILY_POPULATIONS_CURRENT_DOMESTIC_FOREIGN_SOURCE_TOTAL_"
    "CONTRACT_ONLY_NO_GLOBAL_SCHEMA_REVISION_FILE_HASH_DISPLAY_ORDER_TOPOLOGY_"
    "SOURCE_MAPPING_VALUE_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)

_EXPECTED_NAMES = {
    716: "Cho vay khách hàng",
    759: "Phân tích theo khu vực địa lý",
    5752: "+ Trong nước",
    760: "+ Thành phố Hồ Chí Minh",
    761: "+ Đồng bằng sông Cửu Long",
    762: "+ Miền Trung và Tây nguyên",
    763: "+ Miền Bắc",
    764: "+ Miền Đông nam bộ",
    765: "+ Nước ngoài",
}
_EXPECTED_PARENTS = {
    716: 560,
    759: 716,
    5752: 759,
    760: 5752,
    761: 5752,
    762: 5752,
    763: 5752,
    764: 5752,
    765: 759,
}
_EXPECTED_PATHS = {
    716: (560, 716),
    759: (560, 716, 759),
    5752: (560, 716, 759, 5752),
    760: (560, 716, 759, 5752, 760),
    761: (560, 716, 759, 5752, 761),
    762: (560, 716, 759, 5752, 762),
    763: (560, 716, 759, 5752, 763),
    764: (560, 716, 759, 5752, 764),
    765: (560, 716, 759, 765),
}
_EXPECTED_LEVELS = {716: 1, 759: 2, 5752: 3, 760: 4, 761: 4, 762: 4, 763: 4, 764: 4, 765: 3}
_MAPPED_ROLE_IDS = {"DOMESTIC_TOTAL": 5752, "FOREIGN_TOTAL": 765}
_KNOWN_NESTED_ROLE_IDS = {
    "HO_CHI_MINH_CITY": 760,
    "MEKONG_DELTA": 761,
    "CENTRAL_AND_CENTRAL_HIGHLANDS": 762,
    "NORTH": 763,
    "SOUTHEAST": 764,
}
_TARGET_IDS = frozenset(_EXPECTED_NAMES)
_DIRECT_CHILD_IDS = frozenset(_MAPPED_ROLE_IDS.values())
_NESTED_CHILD_IDS = frozenset(_KNOWN_NESTED_ROLE_IDS.values())
_SAFETY = {
    "absolute_display_order_in_identity": False,
    "broad_or_mixed_geography_population_can_be_narrowed": False,
    "family_parent_759_emitted_as_mapping": False,
    "global_schema_file_hashes_in_identity": False,
    "global_schema_item_count_in_identity": False,
    "global_schema_revision_in_identity": False,
    "known_nested_domestic_descendants_emitted_in_current_contract": False,
    "new_unclassified_mapping_eligible_descendant_fails_closed": True,
    "owner_716_emitted_as_mapping": False,
    "source_customer_loan_grand_total_emitted_as_mapping": False,
    "topology_graph_depends_on_schema_ids": False,
}


class LoanGeographyBoundedSchemaV1Error(ValueError):
    """The bounded geography schema identity or exact replay drifted."""


def _error(message: str) -> LoanGeographyBoundedSchemaV1Error:
    return LoanGeographyBoundedSchemaV1Error(message)


def _by_id(values: Mapping[int, Any] | Sequence[Any], attribute: str) -> dict[int, Any]:
    if isinstance(values, Mapping):
        result = dict(values)
        if any(
            type(identifier) is not int or getattr(value, attribute, None) != identifier
            for identifier, value in result.items()
        ):
            raise _error("bounded schema mapping identities drifted")
        return result
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise _error("bounded schema input must be one mapping or sequence")
    result: dict[int, Any] = {}
    for value in values:
        identifier = getattr(value, attribute, None)
        if type(identifier) is not int or identifier in result:
            raise _error("bounded schema input has a missing or duplicate identity")
        result[identifier] = value
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


def _expected_node(identifier: int, *, disposition: str) -> dict[str, Any]:
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
        "known_nested_domestic_descendants",
        "mapped_roles",
        "owner_context",
        "projection_id",
        "safety",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error("bounded loan-geography schema projection fields drifted")
    expected_roles = [
        {
            **_expected_node(
                identifier,
                disposition="REQUIRED_SOURCE_TOTAL_MAPPING_WITHIN_ACCEPTED_REGION",
            ),
            "presence": "REQUIRED_WITHIN_CURRENT_SOURCE_TOTAL_CONTRACT",
            "role": role,
        }
        for role, identifier in _MAPPED_ROLE_IDS.items()
    ]
    expected_nested = [
        {
            **_expected_node(
                identifier,
                disposition="KNOWN_NESTED_DOMESTIC_DESCENDANT_OUTSIDE_CURRENT_CONTRACT",
            ),
            "presence": "NOT_EXERCISED_BY_CURRENT_SOURCE_TOTAL_CONTRACT",
            "role": role,
        }
        for role, identifier in _KNOWN_NESTED_ROLE_IDS.items()
    ]
    expected_policy = {
        "context_only_owner_report_norm_id": 716,
        "family_parent_report_norm_id": 759,
        "known_nested_domestic_report_norm_ids": [760, 761, 762, 763, 764],
        "mapped_parent_report_norm_ids": [],
        "source_customer_loan_grand_total_report_norm_id": None,
        "strict_source_total_report_norm_ids": [5752, 765],
    }
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["safety"] != _SAFETY
        or not same_typed_json_v1(
            value["owner_context"],
            _expected_node(716, disposition="OWNER_CONTEXT_ONLY_NOT_EMITTED"),
        )
        or not same_typed_json_v1(
            value["family_context"],
            _expected_node(759, disposition="FAMILY_CONTEXT_ONLY_NOT_EMITTED"),
        )
        or not same_typed_json_v1(value["mapped_roles"], expected_roles)
        or not same_typed_json_v1(value["known_nested_domestic_descendants"], expected_nested)
        or not same_typed_json_v1(value["accounting_population_policy"], expected_policy)
    ):
        raise _error("bounded loan-geography schema projection contract drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("projection_id")
    if identity != "lgbspv1:projection:" + canonical_json_sha256_v1(material):
        raise _error("bounded loan-geography schema projection identity drifted")
    return canonical_clone_v1(value)


def _reject_unclassified_eligible_children(
    schema: Mapping[int, Any],
    contexts: Mapping[int, Any],
    *,
    parent_id: int,
    classified_ids: frozenset[int],
) -> None:
    children = _list(getattr(schema[parent_id], "children", None), "bounded family children")
    if not classified_ids <= set(children):
        raise _error(f"ReportNormId {parent_id} lacks one classified geography child")
    for child_id in children:
        if type(child_id) is not int:
            raise _error(f"ReportNormId {parent_id} child identity drifted")
        if child_id in classified_ids:
            continue
        context = contexts.get(child_id)
        if context is None or getattr(context, "mapping_eligible", None) is not False:
            raise _error(
                f"unclassified mapping-eligible child {child_id} appeared under "
                f"ReportNormId {parent_id}"
            )


def build_loan_geography_bounded_schema_projection_v1(
    schema_items: Mapping[int, Any] | Sequence[Any],
    tm_contexts: Mapping[int, Any] | Sequence[Any],
) -> dict[str, Any]:
    """Project only the live schema slice governing Family 11."""

    schema = _by_id(schema_items, "schema_id")
    contexts = _by_id(tm_contexts, "report_norm_id")
    if not _TARGET_IDS <= schema.keys() or not _TARGET_IDS <= contexts.keys():
        raise _error("bounded loan-geography target schema/context is incomplete")
    owner_children = _list(getattr(schema[716], "children", None), "owner children")
    if 759 not in owner_children:
        raise _error("loan-geography family is not a child of customer loans")
    _reject_unclassified_eligible_children(
        schema, contexts, parent_id=759, classified_ids=_DIRECT_CHILD_IDS
    )
    _reject_unclassified_eligible_children(
        schema, contexts, parent_id=5752, classified_ids=_NESTED_CHILD_IDS
    )
    _reject_unclassified_eligible_children(
        schema, contexts, parent_id=765, classified_ids=frozenset()
    )

    owner = _node(schema[716], contexts[716], disposition="OWNER_CONTEXT_ONLY_NOT_EMITTED")
    family = _node(schema[759], contexts[759], disposition="FAMILY_CONTEXT_ONLY_NOT_EMITTED")
    mapped_roles = [
        {
            **_node(
                schema[identifier],
                contexts[identifier],
                disposition="REQUIRED_SOURCE_TOTAL_MAPPING_WITHIN_ACCEPTED_REGION",
            ),
            "presence": "REQUIRED_WITHIN_CURRENT_SOURCE_TOTAL_CONTRACT",
            "role": role,
        }
        for role, identifier in _MAPPED_ROLE_IDS.items()
    ]
    nested = [
        {
            **_node(
                schema[identifier],
                contexts[identifier],
                disposition="KNOWN_NESTED_DOMESTIC_DESCENDANT_OUTSIDE_CURRENT_CONTRACT",
            ),
            "presence": "NOT_EXERCISED_BY_CURRENT_SOURCE_TOTAL_CONTRACT",
            "role": role,
        }
        for role, identifier in _KNOWN_NESTED_ROLE_IDS.items()
    ]
    material = {
        "accounting_population_policy": {
            "context_only_owner_report_norm_id": 716,
            "family_parent_report_norm_id": 759,
            "known_nested_domestic_report_norm_ids": [760, 761, 762, 763, 764],
            "mapped_parent_report_norm_ids": [],
            "source_customer_loan_grand_total_report_norm_id": None,
            "strict_source_total_report_norm_ids": [5752, 765],
        },
        "claim_boundary": CLAIM_BOUNDARY,
        "family_context": family,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "known_nested_domestic_descendants": nested,
        "mapped_roles": mapped_roles,
        "owner_context": owner,
        "safety": canonical_clone_v1(_SAFETY),
    }
    return _validate_projection(
        {**material, "projection_id": "lgbspv1:projection:" + canonical_json_sha256_v1(material)}
    )


def build_live_loan_geography_bounded_schema_projection_v1(project_root: Path) -> dict[str, Any]:
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
        raise _error("live bounded loan-geography schema could not be reconstructed") from exc
    return build_loan_geography_bounded_schema_projection_v1(schema, contexts)


def validate_loan_geography_bounded_schema_projection_v1(value: Any) -> dict[str, Any]:
    """Validate one content-addressed bounded projection."""

    return _validate_projection(value)


def validate_loan_geography_bounded_schema_projection_replay_v1(
    value: Any,
    schema_items: Mapping[int, Any] | Sequence[Any],
    tm_contexts: Mapping[int, Any] | Sequence[Any],
) -> dict[str, Any]:
    """Rebuild the bounded projection and require exact typed equality."""

    persisted = _validate_projection(value)
    rebuilt = build_loan_geography_bounded_schema_projection_v1(schema_items, tm_contexts)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("bounded loan-geography schema projection does not replay exactly")
    return rebuilt
