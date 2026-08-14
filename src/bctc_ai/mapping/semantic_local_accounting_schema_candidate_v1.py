"""Replay-authenticated TM schema candidates for Semantic Accounting Graph v2.

This seam deliberately stops before mapping.  It binds typed graph roles to a
small, frozen branch of the supplied TM schema and preserves unresolved schema
children.  It does not decide the source statement/scope, materialize values,
canonicalize observations, or authorize export.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from typing import Any

from bctc_ai.core.hashing import sha256_file
from bctc_ai.mapping.ordered_subgraph_v2 import build_schema_projection_v2
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import SchemaItem, load_all, load_schema_contract
from bctc_ai.schema.tm_context import (
    TM_CONTEXT_POLICY_RELATIVE_PATH,
    build_tm_schema_context,
    load_tm_context_policy,
    tm_context_projection_sha256,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.source_structure.local_accounting_graph_v1 import (
    FamilySpecV1,
    local_accounting_family_spec_sha256_v1,
)
from bctc_ai.source_structure.semantic_local_accounting_graph_v2 import (
    validate_semantic_local_accounting_graph_replay_v2,
)

__all__ = [
    "CLAIM_BOUNDARY",
    "FORMAT_VERSION",
    "SAFETY",
    "SemanticLocalAccountingSchemaCandidateV1Error",
    "build_semantic_local_accounting_schema_candidate_v1",
    "validate_semantic_local_accounting_schema_candidate_replay_v1",
]


FORMAT_VERSION = "BANK_CORPUS_SEMANTIC_LOCAL_ACCOUNTING_SCHEMA_CANDIDATE_V1"
CLAIM_BOUNDARY = (
    "REPLAY_AUTHENTICATED_TYPED_GRAPH_TO_TM_SCHEMA_CANDIDATES_ONLY_NO_SOURCE_STATEMENT_"
    "SCOPE_PERIOD_TYPE_MAPPING_CANONICALIZATION_VALUE_MATERIALIZATION_ABSENCE_OR_EXPORT_AUTHORITY"
)
READY_STATUS = "CANDIDATE_SET_READY"
UNRESOLVED_STATUS = "UNRESOLVED_GRAPH_NOT_ACCEPTED"
_SUPPORTED_FAMILY_ID = "LOAN_MATURITY_BUCKETS"
_SUPPORTED_FAMILY_SPEC_SHA256 = "2184e8f9adc3439e06b68adac426060ef876795b8bb1dc4bb4754e6da12b0e06"
_SCHEMA_ROLE_BINDINGS: tuple[tuple[str, str, int, str], ...] = (
    ("ACCOUNTING_ROLE", "OWNER_LABEL", 716, "SCHEMA_CONTEXT_CANDIDATE"),
    ("ACCOUNTING_ROLE", "BRANCH_LABEL", 752, "STRUCTURAL_SCHEMA_CANDIDATE"),
    ("LOGICAL_ROW", "SHORT_TERM", 753, "VALUE_ROW_SCHEMA_CANDIDATE"),
    ("LOGICAL_ROW", "MEDIUM_TERM", 754, "VALUE_ROW_SCHEMA_CANDIDATE"),
    ("LOGICAL_ROW", "LONG_TERM", 755, "VALUE_ROW_SCHEMA_CANDIDATE"),
)
_EXPECTED_SCHEMA_NAMES = {
    560: "I. THÔNG TIN BỔ SUNG CHO CÁC KHOẢN MỤC TRÌNH BÀY TRONG BẢNG CÂN ĐỐI KẾ TOÁN",
    716: "Cho vay khách hàng",
    752: "Phân tích dư nợ theo thời gian đáo hạn",
    753: "+ Ngắn hạn",
    754: "+ Trung hạn",
    755: "+ Dài hạn",
    5747: "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
    1944: "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
}
_EXPECTED_PARENTS = {
    560: None,
    716: 560,
    752: 716,
    753: 752,
    754: 752,
    755: 752,
    5747: 752,
    1944: None,
}
_EXPECTED_CHILDREN = {
    716: [717, 727, 746, 752, 756, 759, 766],
    752: [753, 754, 755, 5747],
}
_EXPECTED_DISPLAY_ORDERS = {
    560: 0,
    716: 157,
    752: 204,
    753: 205,
    754: 206,
    755: 207,
    5747: 208,
    1944: 1709,
}
_EXPECTED_AUTHORITY_HASHES = {
    "schema_registry": (
        "data/registered/schema_registry.json",
        "a06b8b8c222a0ad372e8f265df136a0f9426458d5c6b8ca104f7b1511ea009ee",
    ),
    "schema_graph": (
        "reference/schemas/schema_graph.jsonl",
        "5c90e38c91a2a83f6162430083147491899dd3141d3466102c71d394fb31a880",
    ),
    "schema_sources": (
        "config/schemas/sources.yaml",
        "049a6efe2b83892c6c3838504d307215950bf95626f5e3525e639d95d2732ee7",
    ),
    "hierarchy_config": (
        "config/schemas/hierarchy_reference.yaml",
        "45b232090a3346b07b55c890cae7c31b453cabbd005d1e460d855e04e8defece",
    ),
    "hierarchy_registry": (
        "data/registered/hierarchy_registry.json",
        "18a07990930ac98b47cf2a0358728c30990fb4c96adbf25ff452d7a5df696c3a",
    ),
    "tm_hierarchy_workbook": (
        "vst_level/vst_bank_detailed_notes_sheet.xlsx",
        "6f322f7ba3b1b737643d21890b9bd51ea00224cea6ac65cfa41036d68ccd885b",
    ),
    "tm_context_policy": (
        "config/schemas/tm-context-v1.yaml",
        "50b0e7fcd5fbb54b45f6643d1d9c577de6013fdd04b748c620c755c54ee55e0a",
    ),
    "schema_coverage_registry": (
        "data/registered/schema_coverage_registry.json",
        "a743b35e5bfe23ca275131cd752a84333225f20be2581d36ce65532fc4eca07a",
    ),
    "tm_workbook": (
        "template/Bank_TM_ReportNormId.v2.xlsx",
        "8912e6cbd279f33d507f1bef2235e46328ddcca97ed382d9ddd3fe453cee08d8",
    ),
}
_EXPECTED_TM_CONTEXT_SHA256 = "e737e371158efbba023bc3b0e2fe20d6f7996df21dcb51e6accd6293e16257d7"
_EXPECTED_TM_SCHEMA_PROJECTION_SHA256 = (
    "4384238aa0e02035ab2f78e7671460fc03b2d2f25433d0eb9e327e8b7c545229"
)
_SAFETY_ITEMS: tuple[tuple[str, bool], ...] = (
    ("typed_graph_roles_only", True),
    ("raw_text_used_for_schema_routing", False),
    ("fuzzy_text_used_for_schema_routing", False),
    ("numeric_values_used_for_schema_routing", False),
    ("bank_page_note_identity_used_for_schema_routing", False),
    ("source_statement_type_authority", False),
    ("source_report_scope_authority", False),
    ("canonical_period_type_authority", False),
    ("schema_mapping_authority", False),
    ("canonicalization_authority", False),
    ("value_materialization_authority", False),
    ("absence_authority", False),
    ("export_authority", False),
)
SAFETY: Mapping[str, bool] = MappingProxyType(dict(_SAFETY_ITEMS))
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class SemanticLocalAccountingSchemaCandidateV1Error(ValueError):
    """The graph, schema authority, candidate set, or exact replay drifted."""


def _error(message: str) -> SemanticLocalAccountingSchemaCandidateV1Error:
    return SemanticLocalAccountingSchemaCandidateV1Error(message)


def _fixed_safety() -> dict[str, bool]:
    return dict(_SAFETY_ITEMS)


def _authority_snapshot(project_root: Path) -> tuple[dict[str, Any], dict[int, SchemaItem]]:
    root = project_root.resolve()
    refs: dict[str, dict[str, Any]] = {}
    for name, (relative, expected_sha256) in _EXPECTED_AUTHORITY_HASHES.items():
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise _error(f"{name} authority escapes project root") from exc
        if not path.is_file() or sha256_file(path) != expected_sha256:
            raise _error(f"{name} authority is missing or hash-drifted")
        refs[name] = {
            "path": relative,
            "sha256": expected_sha256,
            "size_bytes": path.stat().st_size,
        }
    try:
        contract = load_schema_contract(root)
        _, schema = load_all(root / "template", root)
        _, hierarchy = load_hierarchy_reference(
            root / "config/schemas/hierarchy_reference.yaml", root, schema
        )
        apply_hierarchy_reference(schema, hierarchy)
        policy = load_tm_context_policy(root / TM_CONTEXT_POLICY_RELATIVE_PATH)
        contexts = build_tm_schema_context(schema, policy)
    except (OSError, ValueError) as exc:
        raise _error("mapping-safe TM schema authority could not be reconstructed") from exc
    universal = contract.get("universal_schema")
    if universal != {
        "revision": "UNIVERSAL_BANK_BCTC_SCHEMA@6065",
        "item_count": 1944,
        "counts": {"CDKT": 99, "KQKD": 25, "LCTT": 110, "TM": 1710},
        "high_watermark": 6065,
    }:
        raise _error("universal schema revision or denominator drifted")
    if tm_context_projection_sha256(contexts) != _EXPECTED_TM_CONTEXT_SHA256:
        raise _error("TM context projection hash drifted")
    tm_projection_sha256 = build_schema_projection_v2(schema, "TM").projection_sha256
    if tm_projection_sha256 != _EXPECTED_TM_SCHEMA_PROJECTION_SHA256:
        raise _error("TM schema projection hash drifted")
    by_id = {item.schema_id: item for item in schema}
    context_by_id = {context.report_norm_id: context for context in contexts}
    for schema_id, name in _EXPECTED_SCHEMA_NAMES.items():
        item = by_id.get(schema_id)
        if (
            item is None
            or item.canonical_name != name
            or item.statement_type != "TM"
            or item.parent_id != _EXPECTED_PARENTS[schema_id]
            or item.display_order != _EXPECTED_DISPLAY_ORDERS[schema_id]
        ):
            raise _error(f"TM schema identity/hierarchy drifted for ReportNormId {schema_id}")
    for schema_id, children in _EXPECTED_CHILDREN.items():
        if by_id[schema_id].children != children:
            raise _error(f"TM schema child order drifted for ReportNormId {schema_id}")
    if any(
        not context_by_id[schema_id].mapping_eligible
        or context_by_id[schema_id].context_status != "RESOLVED"
        for schema_id in (560, 716, 752, 753, 754, 755, 5747)
    ):
        raise _error("target TM schema context is not mapping-eligible")
    orphan = context_by_id[1944]
    if orphan.mapping_eligible or orphan.context_status != "UNRESOLVED_ORPHAN":
        raise _error("TM orphan 1944 unexpectedly became mapping-eligible")
    return (
        {
            "schema_name": "UNIVERSAL_BANK_BCTC_SCHEMA",
            "schema_revision": universal["revision"],
            "schema_item_count": universal["item_count"],
            "tm_item_count": universal["counts"]["TM"],
            "order_authority": "WORKBOOK_DISPLAY_ORDER",
            "tm_schema_projection_sha256": _EXPECTED_TM_SCHEMA_PROJECTION_SHA256,
            "tm_context_projection_sha256": _EXPECTED_TM_CONTEXT_SHA256,
            "refs": refs,
        },
        by_id,
    )


def _graph_nodes_by_typed_role(
    graph: Mapping[str, Any],
) -> dict[tuple[str, str], Mapping[str, Any]]:
    result: dict[tuple[str, str], Mapping[str, Any]] = {}
    for node in graph["nodes"]:
        kind = node["kind"]
        role = None
        if kind == "ACCOUNTING_ROLE":
            role = node["attributes"]["accounting_role"]
        elif kind == "LOGICAL_ROW":
            role = node["attributes"]["row_role"]
        if role is None:
            continue
        key = (kind, role)
        if key in result:
            raise _error(f"semantic graph repeats typed role {kind}/{role}")
        result[key] = node
    return result


def _build_payload(
    graph: Mapping[str, Any], authority: dict[str, Any], by_id: dict[int, SchemaItem]
) -> dict[str, Any]:
    accepted = graph["status"] == "ACCEPTED_WITHIN_SUPPLIED_FAMILY_COLLISION_SCOPE"
    if (
        graph["family_id"] != _SUPPORTED_FAMILY_ID
        or graph["family_spec_sha256"] != _SUPPORTED_FAMILY_SPEC_SHA256
    ):
        raise _error("schema-candidate v1 supports only the exact frozen loan-maturity family")
    role_nodes = _graph_nodes_by_typed_role(graph) if accepted else {}
    candidates: list[dict[str, Any]] = []
    if accepted:
        expected_keys = {(kind, role) for kind, role, _, _ in _SCHEMA_ROLE_BINDINGS}
        if set(role_nodes) - {("LOGICAL_ROW", "TOTAL")} != expected_keys:
            raise _error("accepted graph typed roles differ from the strict maturity core")
        total = role_nodes.get(("LOGICAL_ROW", "TOTAL"))
        if (
            total is None
            or total["attributes"]["total_resolution"] != "IMMEDIATE_UNLABELED_NUMERIC_ROW"
        ):
            raise _error("accepted graph lacks its source-only unlabeled total")
        for kind, role, schema_id, disposition in _SCHEMA_ROLE_BINDINGS:
            node = role_nodes[(kind, role)]
            item = by_id[schema_id]
            candidates.append(
                {
                    "graph_node_id": node["node_id"],
                    "graph_node_kind": kind,
                    "typed_role": role,
                    "candidate_report_norm_ids": [schema_id],
                    "candidate_schema_namespace": "TM",
                    "canonical_name": item.canonical_name,
                    "display_order": item.display_order,
                    "disposition": disposition,
                }
            )
        candidates.append(
            {
                "graph_node_id": total["node_id"],
                "graph_node_kind": "LOGICAL_ROW",
                "typed_role": "TOTAL",
                "candidate_report_norm_ids": [],
                "candidate_schema_namespace": None,
                "canonical_name": None,
                "display_order": None,
                "disposition": "SOURCE_ONLY_VALIDATION",
            }
        )
    payload = {
        "format_version": FORMAT_VERSION,
        "claim_boundary": CLAIM_BOUNDARY,
        "status": READY_STATUS if accepted else UNRESOLVED_STATUS,
        "semantic_graph_id": graph["graph_id"],
        "semantic_graph_sha256": canonical_json_sha256_v1(graph),
        "family_id": graph["family_id"],
        "family_spec_sha256": graph["family_spec_sha256"],
        "supplied_family_collision_scope_spec_sha256_by_id": canonical_clone_v1(
            graph["supplied_family_collision_scope_spec_sha256_by_id"]
        ),
        "schema_authority": authority,
        "source_semantics": {
            "statement_type": None,
            "report_scope": None,
            "canonical_period_type": None,
        },
        "role_candidates": candidates,
        "unassessed_schema_children": (
            [
                {
                    "report_norm_id": 5747,
                    "parent_report_norm_id": 752,
                    "canonical_name": by_id[5747].canonical_name,
                    "display_order": by_id[5747].display_order,
                    "disposition": "UNASSESSED_SCHEMA_CHILD",
                }
            ]
            if accepted
            else []
        ),
        "metrics": {
            "candidate_role_count": len(candidates),
            "singleton_schema_candidate_count": sum(
                len(item["candidate_report_norm_ids"]) == 1 for item in candidates
            ),
            "source_only_validation_role_count": sum(
                item["disposition"] == "SOURCE_ONLY_VALIDATION" for item in candidates
            ),
            "unassessed_schema_child_count": 1 if accepted else 0,
        },
        "readiness": {
            "schema_candidate_set_ready": accepted,
            "schema_mapping_ready": False,
            "canonicalization_eligible": False,
            "export_eligible": False,
        },
        "safety": _fixed_safety(),
    }
    payload["candidate_set_id"] = f"slascv1:candidate:{canonical_json_sha256_v1(payload)}"
    return payload


def _validate_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _error("schema candidate payload must be one object")
    expected_top = {
        "format_version",
        "claim_boundary",
        "candidate_set_id",
        "status",
        "semantic_graph_id",
        "semantic_graph_sha256",
        "family_id",
        "family_spec_sha256",
        "supplied_family_collision_scope_spec_sha256_by_id",
        "schema_authority",
        "source_semantics",
        "role_candidates",
        "unassessed_schema_children",
        "metrics",
        "readiness",
        "safety",
    }
    if (
        set(value) != expected_top
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
    ):
        raise _error("schema candidate top-level contract drifted")
    clone = canonical_clone_v1(value)
    candidate_set_id = clone.pop("candidate_set_id")
    if candidate_set_id != f"slascv1:candidate:{canonical_json_sha256_v1(clone)}":
        raise _error("schema candidate identity drifted")
    if value["safety"] != _fixed_safety():
        raise _error("schema candidate safety boundary drifted")
    return canonical_clone_v1(value)


def build_semantic_local_accounting_schema_candidate_v1(
    project_root: Path,
    semantic_graph_v2: Any,
    source_projection_v2: Any,
    semantic_page_binding_v2: Any,
    authenticated_transformer_receipt_v2: Any,
    family_spec: FamilySpecV1,
    family_specs_for_collision_scope: Sequence[FamilySpecV1],
) -> dict[str, Any]:
    """Build candidate-only TM role bindings after exact graph replay."""

    if type(family_spec) is not FamilySpecV1:
        raise _error("schema candidate target must be one exact FamilySpecV1")
    if local_accounting_family_spec_sha256_v1(family_spec) != _SUPPORTED_FAMILY_SPEC_SHA256:
        raise _error("schema candidate target family spec is unsupported or drifted")
    try:
        graph = validate_semantic_local_accounting_graph_replay_v2(
            semantic_graph_v2,
            source_projection_v2,
            semantic_page_binding_v2,
            authenticated_transformer_receipt_v2,
            family_spec,
            family_specs_for_collision_scope,
        )
    except ValueError as exc:
        raise _error("semantic graph failed exact authenticated replay") from exc
    authority, by_id = _authority_snapshot(project_root)
    return _validate_payload(_build_payload(graph, authority, by_id))


def validate_semantic_local_accounting_schema_candidate_replay_v1(
    value: Any,
    project_root: Path,
    semantic_graph_v2: Any,
    source_projection_v2: Any,
    semantic_page_binding_v2: Any,
    authenticated_transformer_receipt_v2: Any,
    family_spec: FamilySpecV1,
    family_specs_for_collision_scope: Sequence[FamilySpecV1],
) -> dict[str, Any]:
    """Validate shape and rebuild the exact candidate artifact from authorities."""

    persisted = _validate_payload(value)
    rebuilt = build_semantic_local_accounting_schema_candidate_v1(
        project_root,
        semantic_graph_v2,
        source_projection_v2,
        semantic_page_binding_v2,
        authenticated_transformer_receipt_v2,
        family_spec,
        family_specs_for_collision_scope,
    )
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("schema candidate artifact does not replay from exact authorities")
    return canonical_clone_v1(rebuilt)
