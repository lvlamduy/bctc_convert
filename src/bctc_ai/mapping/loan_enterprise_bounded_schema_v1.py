"""Append-stable bounded TM schema projection for loan enterprise/customer type.

The projection closes the mapping-eligible leaf population directly beneath
ReportNormId 766 while retaining nearby lookalike branches as explicit
non-emitting context.  Global schema revisions, workbook positions, display
order, and unrelated appends do not enter the identity.

Every family leaf is optional per source document and may be emitted only when
its exact source semantics are proved.  A generic, truncated, or otherwise
ambiguous source row remains source-only; this projection never forces it to
the nearest schema label.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
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
    "LoanEnterpriseBoundedSchemaV1Error",
    "build_live_loan_enterprise_bounded_schema_projection_v1",
    "build_loan_enterprise_bounded_schema_projection_v1",
    "validate_loan_enterprise_bounded_schema_projection_replay_v1",
    "validate_loan_enterprise_bounded_schema_projection_v1",
]


FORMAT_VERSION = "LOAN_ENTERPRISE_BOUNDED_TM_SCHEMA_PROJECTION_V1"
FAMILY_ID = "LOAN_ENTERPRISE_OR_CUSTOMER_TYPE_CLASSIFICATION"
CLAIM_BOUNDARY = (
    "LIVE_TM_SCHEMA_EXACT_ENTERPRISE_LEAF_IDENTITIES_EDGES_CONTEXT_ELIGIBILITY_"
    "AND_CLOSED_REPORT_NORM_766_POPULATION_WITH_EXPLICIT_INDUSTRY_DEPOSIT_AND_"
    "RELATED_PARTY_LOOKALIKE_CONTEXT_ONLY_NO_GLOBAL_SCHEMA_REVISION_FILE_HASH_"
    "DISPLAY_ORDER_SOURCE_MATCHING_VALUE_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)


@dataclass(frozen=True)
class _NodeSpec:
    canonical_name: str
    parent_id: int | None
    ancestor_path: tuple[int, ...]
    hierarchy_level: int
    section: str
    section_root_id: int
    note_family_root_id: int | None


_NODE_SPECS = {
    716: _NodeSpec("Cho vay khách hàng", 560, (560, 716), 1, "BALANCE_SHEET_NOTES", 560, 716),
    727: _NodeSpec(
        "Phân tích theo ngành nghề kinh doanh",
        716,
        (560, 716, 727),
        2,
        "BALANCE_SHEET_NOTES",
        560,
        716,
    ),
    766: _NodeSpec(
        "Phân tích theo loại hình doanh nghiệp",
        716,
        (560, 716, 766),
        2,
        "BALANCE_SHEET_NOTES",
        560,
        716,
    ),
    767: _NodeSpec(
        "- Doanh nghiệp nhà nước",
        766,
        (560, 716, 766, 767),
        3,
        "BALANCE_SHEET_NOTES",
        560,
        716,
    ),
    768: _NodeSpec(
        "- Công ty TNHH",
        766,
        (560, 716, 766, 768),
        3,
        "BALANCE_SHEET_NOTES",
        560,
        716,
    ),
    769: _NodeSpec(
        "+ Công ty TNHH MTV vốn nhà nước 100%",
        766,
        (560, 716, 766, 769),
        3,
        "BALANCE_SHEET_NOTES",
        560,
        716,
    ),
    770: _NodeSpec(
        "Công ty TNHH MTV (hoặc trên MTV) vốn nhà nước trên 50%",
        766,
        (560, 716, 766, 770),
        3,
        "BALANCE_SHEET_NOTES",
        560,
        716,
    ),
    771: _NodeSpec(
        "+ Công ty TNHH khác",
        766,
        (560, 716, 766, 771),
        3,
        "BALANCE_SHEET_NOTES",
        560,
        716,
    ),
    772: _NodeSpec(
        "- Công ty cổ phần có vốn nhà nước trên 50%",
        766,
        (560, 716, 766, 772),
        3,
        "BALANCE_SHEET_NOTES",
        560,
        716,
    ),
    773: _NodeSpec(
        "- Công ty cổ phần khác",
        766,
        (560, 716, 766, 773),
        3,
        "BALANCE_SHEET_NOTES",
        560,
        716,
    ),
    774: _NodeSpec(
        "- Doanh nghiệp tư nhân",
        766,
        (560, 716, 766, 774),
        3,
        "BALANCE_SHEET_NOTES",
        560,
        716,
    ),
    775: _NodeSpec(
        "- Công ty CP, TNHH, DN tư nhân",
        766,
        (560, 716, 766, 775),
        3,
        "BALANCE_SHEET_NOTES",
        560,
        716,
    ),
    776: _NodeSpec(
        "- Hợp tác xã và liên hợp tác xã",
        766,
        (560, 716, 766, 776),
        3,
        "BALANCE_SHEET_NOTES",
        560,
        716,
    ),
    6074: _NodeSpec(
        "+ Hợp tác xã và công ty tư nhân",
        766,
        (560, 716, 766, 6074),
        3,
        "BALANCE_SHEET_NOTES",
        560,
        716,
    ),
    777: _NodeSpec(
        "- Công ty liên doanh, hợp doanh",
        766,
        (560, 716, 766, 777),
        3,
        "BALANCE_SHEET_NOTES",
        560,
        716,
    ),
    778: _NodeSpec(
        "- Công ty hợp danh",
        766,
        (560, 716, 766, 778),
        3,
        "BALANCE_SHEET_NOTES",
        560,
        716,
    ),
    779: _NodeSpec(
        "- Công ty vốn nước ngoài",
        766,
        (560, 716, 766, 779),
        3,
        "BALANCE_SHEET_NOTES",
        560,
        716,
    ),
    780: _NodeSpec(
        "- Hộ kinh doanh, cá nhân",
        766,
        (560, 716, 766, 780),
        3,
        "BALANCE_SHEET_NOTES",
        560,
        716,
    ),
    781: _NodeSpec(
        "- Dịch vụ hành chính sự nghiệp, Đảng, đoàn thể, hiệp hội",
        766,
        (560, 716, 766, 781),
        3,
        "BALANCE_SHEET_NOTES",
        560,
        716,
    ),
    782: _NodeSpec(
        "- Khác",
        766,
        (560, 716, 766, 782),
        3,
        "BALANCE_SHEET_NOTES",
        560,
        716,
    ),
    5748: _NodeSpec(
        "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
        766,
        (560, 716, 766, 5748),
        3,
        "BALANCE_SHEET_NOTES",
        560,
        716,
    ),
    6058: _NodeSpec(
        "+ Cho vay tại Chi nhánh và ngân hàng con nước ngoài",
        727,
        (560, 716, 727, 6058),
        3,
        "BALANCE_SHEET_NOTES",
        560,
        716,
    ),
    1055: _NodeSpec(
        "Tiền gửi của khách hàng",
        560,
        (560, 1055),
        1,
        "BALANCE_SHEET_NOTES",
        560,
        1055,
    ),
    1075: _NodeSpec(
        "Theo loại hình doanh nghiệp",
        1055,
        (560, 1055, 1075),
        2,
        "BALANCE_SHEET_NOTES",
        560,
        1055,
    ),
    1259: _NodeSpec(
        "IV. MỘT SỐ THÔNG TIN KHÁC",
        None,
        (1259,),
        0,
        "OTHER_QUANTITATIVE_NOTES",
        1259,
        None,
    ),
    5750: _NodeSpec(
        "Giao dịch với các bên liên quan",
        1259,
        (1259, 5750),
        1,
        "OTHER_QUANTITATIVE_NOTES",
        1259,
        5750,
    ),
    5751: _NodeSpec(
        "Giao dịch tiền gửi tại MB",
        5750,
        (1259, 5750, 5751),
        2,
        "OTHER_QUANTITATIVE_NOTES",
        1259,
        5750,
    ),
}

_CHILD_ROLE_IDS = (
    ("STATE_ENTERPRISE", 767),
    ("LIMITED_LIABILITY_COMPANY", 768),
    ("STATE_OWNED_SINGLE_MEMBER_LLC", 769),
    ("STATE_CONTROLLED_MULTI_MEMBER_LLC", 770),
    ("OTHER_LLC", 771),
    ("STATE_CONTROLLED_JOINT_STOCK", 772),
    ("OTHER_JOINT_STOCK", 773),
    ("PRIVATE_ENTERPRISE", 774),
    ("JOINT_STOCK_LLC_PRIVATE_COMBINED", 775),
    ("COOPERATIVE_AND_COOPERATIVE_UNION", 776),
    ("COOPERATIVE_AND_PRIVATE_ENTERPRISE_COMBINED", 6074),
    ("JOINT_VENTURE_AND_BUSINESS_COOPERATION", 777),
    ("PARTNERSHIP", 778),
    ("FOREIGN_CAPITAL_COMPANY", 779),
    ("HOUSEHOLD_INDIVIDUAL", 780),
    ("ADMIN_PUBLIC_PARTY_ASSOCIATION", 781),
    ("OTHER", 782),
    ("MARGIN_AND_SECURITIES_ADVANCE", 5748),
)
_CHILD_IDS = tuple(identifier for _role, identifier in _CHILD_ROLE_IDS)
_TARGET_IDS = frozenset(_NODE_SPECS)
_SAFETY = {
    "absolute_display_order_in_identity": False,
    "ambiguous_source_row_forced_to_nearest_schema_leaf": False,
    "deposit_analogue_emitted_by_family_12": False,
    "exact_leaf_source_semantics_required_for_emission": True,
    "family_parent_766_emitted_as_mapping": False,
    "global_schema_file_hashes_in_identity": False,
    "global_schema_item_count_in_identity": False,
    "global_schema_revision_in_identity": False,
    "industry_leaf_6058_emitted_as_child_of_766": False,
    "new_unclassified_mapping_eligible_child_fails_closed": True,
    "owner_716_emitted_as_mapping": False,
    "related_party_branch_emitted_by_family_12": False,
    "unrelated_schema_appends_change_projection_identity": False,
}


class LoanEnterpriseBoundedSchemaV1Error(ValueError):
    """The bounded enterprise schema identity or exact replay drifted."""


def _error(message: str) -> LoanEnterpriseBoundedSchemaV1Error:
    return LoanEnterpriseBoundedSchemaV1Error(message)


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
    if any(
        type(identifier) is not int or getattr(value, attribute, None) != identifier
        for identifier, value in result.items()
    ):
        raise _error("bounded schema mapping identities drifted")
    return result


def _list(value: Any, label: str) -> list[Any]:
    if type(value) is not list:
        raise _error(f"{label} drifted")
    return list(value)


def _expected_node(identifier: int, disposition: str) -> dict[str, Any]:
    spec = _NODE_SPECS[identifier]
    return {
        "allowed_period_types": ["SNAPSHOT", "DURATION"],
        "allowed_scopes": ["SEPARATE", "CONSOLIDATED"],
        "allowed_signs": ["POSITIVE", "NEGATIVE", "ZERO"],
        "ancestor_path": list(spec.ancestor_path),
        "canonical_name": spec.canonical_name,
        "context_status": "RESOLVED",
        "disposition": disposition,
        "hierarchy_level": spec.hierarchy_level,
        "mapping_eligible": True,
        "note_family_root_report_norm_id": spec.note_family_root_id,
        "parent_report_norm_id": spec.parent_id,
        "report_norm_id": identifier,
        "section": spec.section,
        "section_root_report_norm_id": spec.section_root_id,
        "statement_type": "TM",
    }


def _node(schema: Any, context: Any, identifier: int, disposition: str) -> dict[str, Any]:
    spec = _NODE_SPECS[identifier]
    if (
        getattr(schema, "schema_id", None) != identifier
        or getattr(schema, "canonical_name", None) != spec.canonical_name
        or getattr(schema, "statement_type", None) != "TM"
        or getattr(schema, "parent_id", None) != spec.parent_id
        or getattr(context, "report_norm_id", None) != identifier
        or getattr(context, "canonical_name", None) != spec.canonical_name
        or getattr(context, "statement_type", None) != "TM"
        or getattr(context, "parent_report_norm_id", None) != spec.parent_id
        or getattr(context, "context_status", None) != "RESOLVED"
        or getattr(context, "mapping_eligible", None) is not True
        or getattr(context, "section", None) != spec.section
        or getattr(context, "section_root_id", None) != spec.section_root_id
        or getattr(context, "note_family_root_id", None) != spec.note_family_root_id
        or tuple(getattr(context, "ancestor_path", ())) != spec.ancestor_path
        or getattr(context, "derived_hierarchy_level", None) != spec.hierarchy_level
    ):
        raise _error(f"bounded TM identity/context drifted for ReportNormId {identifier}")
    scopes = _list(getattr(schema, "scope", None), f"ReportNormId {identifier} scope")
    periods = _list(
        getattr(schema, "allowed_period_type", None), f"ReportNormId {identifier} period policy"
    )
    signs = _list(getattr(schema, "allowed_sign", None), f"ReportNormId {identifier} sign policy")
    if (
        scopes != ["SEPARATE", "CONSOLIDATED"]
        or periods != ["SNAPSHOT", "DURATION"]
        or signs != ["POSITIVE", "NEGATIVE", "ZERO"]
    ):
        raise _error(f"bounded TM value policy drifted for ReportNormId {identifier}")
    return _expected_node(identifier, disposition)


def _require_edge(schema: Mapping[int, Any], parent_id: int, child_id: int) -> None:
    children = _list(
        getattr(schema[parent_id], "children", None), f"ReportNormId {parent_id} children"
    )
    if len(children) != len(set(children)) or child_id not in children:
        raise _error(f"ReportNormId {parent_id} lacks required child {child_id}")


def _close_eligible_children(
    schema: Mapping[int, Any],
    contexts: Mapping[int, Any],
    parent_id: int,
    expected_ids: tuple[int, ...],
) -> None:
    children = _list(
        getattr(schema[parent_id], "children", None), f"ReportNormId {parent_id} children"
    )
    if len(children) != len(set(children)) or any(type(item) is not int for item in children):
        raise _error(f"ReportNormId {parent_id} child identities drifted")
    eligible: list[int] = []
    for child_id in children:
        context = contexts.get(child_id)
        state = None if context is None else getattr(context, "mapping_eligible", None)
        if state is True:
            eligible.append(child_id)
        elif state is not False:
            raise _error(
                f"unclassified child {child_id} under ReportNormId {parent_id} lacks explicit eligibility"
            )
    if eligible != list(expected_ids):
        missing = sorted(set(expected_ids) - set(eligible))
        added = sorted(set(eligible) - set(expected_ids))
        raise _error(
            f"ReportNormId {parent_id} eligible child population drifted; "
            f"missing={missing}, unclassified={added}"
        )


def _expected_material() -> dict[str, Any]:
    mapped = [
        {
            **_expected_node(identifier, "OPTIONAL_EXACT_SOURCE_LEAF_MAPPING"),
            "presence": "OPTIONAL_WHEN_EXACT_SOURCE_SEMANTICS_PROVEN",
            "role": role,
        }
        for role, identifier in _CHILD_ROLE_IDS
    ]
    return {
        "claim_boundary": CLAIM_BOUNDARY,
        "emission_policy": {
            "ambiguous_source_disposition": "RETAIN_SOURCE_ONLY_WITHOUT_FORCED_SCHEMA_ID",
            "cross_family_industry_context_report_norm_ids": [727, 6058],
            "deposit_analogue_context_report_norm_ids": [1055, 1075],
            "emittable_exact_leaf_report_norm_ids": list(_CHILD_IDS),
            "family_parent_report_norm_id": 766,
            "mapped_parent_report_norm_ids": [],
            "related_party_context_report_norm_ids": [1259, 5750, 5751],
            "required_per_document_report_norm_ids": [],
            "source_customer_loan_total_report_norm_id": None,
        },
        "excluded_context": {
            "cross_family_industry": [
                _expected_node(727, "INDUSTRY_FAMILY_CONTEXT_NOT_EMITTED"),
                _expected_node(6058, "INDUSTRY_LEAF_OUTSIDE_REPORT_NORM_766_NOT_EMITTED"),
            ],
            "customer_deposit_analogue": [
                _expected_node(1055, "CUSTOMER_DEPOSIT_OWNER_NOT_EMITTED"),
                _expected_node(1075, "CUSTOMER_DEPOSIT_TYPE_ANALOGUE_NOT_EMITTED"),
            ],
            "related_party": [
                _expected_node(1259, "OTHER_INFORMATION_SECTION_NOT_EMITTED"),
                _expected_node(5750, "RELATED_PARTY_FAMILY_NOT_EMITTED"),
                _expected_node(5751, "RELATED_PARTY_DEPOSIT_ROW_NOT_EMITTED"),
            ],
        },
        "family_context": _expected_node(766, "FAMILY_CONTEXT_ONLY_NOT_EMITTED"),
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "mapped_leaves": mapped,
        "owner_context": _expected_node(716, "OWNER_CONTEXT_ONLY_NOT_EMITTED"),
        "safety": canonical_clone_v1(_SAFETY),
    }


def _validate_projection(value: Any) -> dict[str, Any]:
    expected_fields = {*_expected_material(), "projection_id"}
    if type(value) is not dict or set(value) != expected_fields:
        raise _error("bounded loan-enterprise schema projection fields drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("projection_id")
    if not same_typed_json_v1(material, _expected_material()):
        raise _error("bounded loan-enterprise schema projection contract drifted")
    if identity != "lebspv1:projection:" + canonical_json_sha256_v1(material):
        raise _error("bounded loan-enterprise schema projection identity drifted")
    return canonical_clone_v1(value)


def build_loan_enterprise_bounded_schema_projection_v1(
    schema_items: Mapping[int, Any] | Sequence[Any],
    tm_contexts: Mapping[int, Any] | Sequence[Any],
) -> dict[str, Any]:
    """Project only the live schema slice governing Family 12."""

    schema = _by_id(schema_items, "schema_id")
    contexts = _by_id(tm_contexts, "report_norm_id")
    if not _TARGET_IDS <= schema.keys() or not _TARGET_IDS <= contexts.keys():
        raise _error("bounded loan-enterprise target schema/context is incomplete")

    _require_edge(schema, 716, 766)
    _close_eligible_children(schema, contexts, 766, _CHILD_IDS)
    for identifier in _CHILD_IDS:
        _close_eligible_children(schema, contexts, identifier, ())
    for parent_id, child_id in (
        (716, 727),
        (727, 6058),
        (560, 1055),
        (1055, 1075),
        (1259, 5750),
        (5750, 5751),
    ):
        if parent_id in schema:
            _require_edge(schema, parent_id, child_id)

    _node(schema[716], contexts[716], 716, "OWNER_CONTEXT_ONLY_NOT_EMITTED")
    _node(schema[766], contexts[766], 766, "FAMILY_CONTEXT_ONLY_NOT_EMITTED")
    for _role, identifier in _CHILD_ROLE_IDS:
        _node(
            schema[identifier],
            contexts[identifier],
            identifier,
            "OPTIONAL_EXACT_SOURCE_LEAF_MAPPING",
        )
    for identifier, disposition in (
        (727, "INDUSTRY_FAMILY_CONTEXT_NOT_EMITTED"),
        (6058, "INDUSTRY_LEAF_OUTSIDE_REPORT_NORM_766_NOT_EMITTED"),
        (1055, "CUSTOMER_DEPOSIT_OWNER_NOT_EMITTED"),
        (1075, "CUSTOMER_DEPOSIT_TYPE_ANALOGUE_NOT_EMITTED"),
        (1259, "OTHER_INFORMATION_SECTION_NOT_EMITTED"),
        (5750, "RELATED_PARTY_FAMILY_NOT_EMITTED"),
        (5751, "RELATED_PARTY_DEPOSIT_ROW_NOT_EMITTED"),
    ):
        _node(schema[identifier], contexts[identifier], identifier, disposition)

    material = _expected_material()
    return _validate_projection(
        {**material, "projection_id": "lebspv1:projection:" + canonical_json_sha256_v1(material)}
    )


def build_live_loan_enterprise_bounded_schema_projection_v1(project_root: Path) -> dict[str, Any]:
    """Build the bounded projection from the current live schema without corpus replay."""

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
        raise _error("live bounded loan-enterprise schema could not be reconstructed") from exc
    return build_loan_enterprise_bounded_schema_projection_v1(schema, contexts)


def validate_loan_enterprise_bounded_schema_projection_v1(value: Any) -> dict[str, Any]:
    """Validate one content-addressed bounded projection."""

    return _validate_projection(value)


def validate_loan_enterprise_bounded_schema_projection_replay_v1(
    value: Any,
    schema_items: Mapping[int, Any] | Sequence[Any],
    tm_contexts: Mapping[int, Any] | Sequence[Any],
) -> dict[str, Any]:
    """Rebuild the bounded projection and require exact typed equality."""

    persisted = _validate_projection(value)
    rebuilt = build_loan_enterprise_bounded_schema_projection_v1(schema_items, tm_contexts)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("bounded loan-enterprise schema projection does not replay exactly")
    return rebuilt
