"""Generic live schema binding for one completed family evidence sweep.

The mapper contains no bank, filing, page, year, family label, or ReportNormId
logic.  A declarative binding spec connects semantic roles to the current TM
schema graph, either directly or by an exact sum of observed source roles,
only after the shared topology, geometry, numeric, period, unit, and accounting
gates have all admitted a trial.  Every aggregate retains its component crops;
the exact live evidence sweep is rebuilt on every public replay.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from bctc_ai.evaluation import family_first_accounting_evidence_sweep_v1 as evidence_v1
from bctc_ai.evaluation import family_first_ppocrv6_numeric_index_v3 as numeric_v3
from bctc_ai.evaluation import family_first_semantic_index_v1 as semantic_v1
from bctc_ai.evaluation import family_first_semantic_label_archive_v1 as archive_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "SPEC_FORMAT_VERSION",
    "SPEC_FORMAT_VERSION_V2",
    "FamilyFirstAccountingSchemaMappingV1Error",
    "build_authenticated_family_first_accounting_schema_mapping_v1",
    "validate_authenticated_family_first_accounting_schema_mapping_replay_v1",
]


FORMAT_VERSION = "FAMILY_FIRST_ACCOUNTING_SCHEMA_MAPPING_V1"
SPEC_FORMAT_VERSION = "ACCOUNTING_FAMILY_SCHEMA_BINDING_SPEC_V1"
SPEC_FORMAT_VERSION_V2 = "ACCOUNTING_FAMILY_SCHEMA_BINDING_SPEC_V2"
SCHEMA_GRAPH_PATH = Path("reference/schemas/schema_graph.jsonl")
CLAIM_BOUNDARY = (
    "LIVE_REPLAYED_FAMILY_EVIDENCE_TO_TRACKED_TM_SCHEMA_DIRECT_PARENT_CHILD_BINDING_"
    "VERIFIED_BY_CODEX_ONLY_AFTER_TOPOLOGY_GEOMETRY_PERIOD_UNIT_PIXEL_BOUND_PPOCRV6_"
    "NUMERIC_ACCOUNTING_SOURCE_SCOPE_SCHEMA_PERIOD_TYPE_AND_SIGN_GATES_NO_BANK_PAGE_"
    "YEAR_ROUTING_NO_SCHEMA_CREATION_CANONICALIZATION_EXPORT_OR_PRODUCTION_AUTHORITY"
)
_AUTHORITY = {
    "bank_file_page_period_scope_used_for_mapping_or_routing": False,
    "canonical_export_authority": False,
    "family_behavior_declarative": True,
    "mapping_verified_by_codex_after_all_evidence_gates": True,
    "new_schema_identity_creation_authority": False,
    "not_observed_authority": False,
    "persisted_result_self_authenticating": False,
    "production_authority": False,
    "public_exact_live_replay_required": True,
    "schema_binding_uses_tracked_graph_parent_child_relations": True,
    "schema_period_type_and_sign_compatibility_required": True,
    "source_scope_schema_compatibility_required": True,
}
_SPEC_FIELDS = {
    "family_id",
    "family_report_norm_id",
    "format_version",
    "role_bindings",
}
_SPEC_V2_FIELDS = {*_SPEC_FIELDS, "aggregate_role_bindings"}
_ROLE_BINDING_FIELDS = {"report_norm_id", "role"}
_AGGREGATE_ROLE_BINDING_FIELDS = {
    "operation",
    "report_norm_id",
    "role",
    "source_roles",
}
_AGGREGATE_OPERATIONS = {"SUM_OBSERVED_SOURCE_ROLES"}
_SOURCE_SCOPE_TO_SCHEMA_SCOPE = {
    "CONSOLIDATED": "CONSOLIDATED",
    "PARENT_OR_SEPARATE": "SEPARATE",
}
_PERIOD_SEMANTICS_TO_SCHEMA_TYPE = {
    "BALANCE_COMPARATIVE": "SNAPSHOT",
    "CURRENT_ROLLFORWARD": "DURATION",
}
_RESULT_FIELDS = {
    "authority",
    "claim_boundary",
    "evidence_sweep_id",
    "family_id",
    "format_version",
    "mapping_id",
    "metrics",
    "schema_binding_spec",
    "schema_graph_ref",
    "state",
    "trials",
}
_TRIAL_FIELDS = {
    "document_ordinal",
    "mapping_status",
    "mappings",
    "private_provenance",
    "source_pdf_ref",
    "unresolved_reasons",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class FamilyFirstAccountingSchemaMappingV1Error(ValueError):
    """The live evidence, declarative schema binding, or tracked graph drifted."""


def _error(message: str) -> FamilyFirstAccountingSchemaMappingV1Error:
    return FamilyFirstAccountingSchemaMappingV1Error(message)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _schema_spec(value: Any, family_spec: Any) -> dict[str, Any]:
    if (
        type(family_spec) is not dict
        or type(family_spec.get("family_id")) is not str
        or type(family_spec.get("children")) is not list
    ):
        raise _error("family topology specification is malformed")
    family_roles = [child.get("role") for child in family_spec["children"]]
    if (
        not family_roles
        or any(type(role) is not str or not role for role in family_roles)
        or len(family_roles) != len(set(family_roles))
    ):
        raise _error("family topology role axis is malformed")
    if type(value) is not dict or (set(value) != _SPEC_FIELDS and set(value) != _SPEC_V2_FIELDS):
        raise _error("family schema-binding specification fields drifted")
    spec_version = value["format_version"]
    if spec_version not in {SPEC_FORMAT_VERSION, SPEC_FORMAT_VERSION_V2} or (
        (spec_version == SPEC_FORMAT_VERSION) is not (set(value) == _SPEC_FIELDS)
    ):
        raise _error("family schema-binding specification version drifted")
    if (
        type(value["family_id"]) is not str
        or value["family_id"] != family_spec["family_id"]
        or type(value["family_report_norm_id"]) is not int
        or value["family_report_norm_id"] <= 0
        or type(value["role_bindings"]) is not list
    ):
        raise _error("family schema-binding specification drifted")
    direct = []
    for raw in value["role_bindings"]:
        if (
            type(raw) is not dict
            or set(raw) != _ROLE_BINDING_FIELDS
            or type(raw["role"]) is not str
            or not raw["role"]
            or type(raw["report_norm_id"]) is not int
            or raw["report_norm_id"] <= 0
        ):
            raise _error("family schema role binding drifted")
        direct.append(canonical_clone_v1(raw))
    aggregates = []
    if spec_version == SPEC_FORMAT_VERSION_V2:
        if type(value["aggregate_role_bindings"]) is not list:
            raise _error("aggregate schema role bindings must be one exact list")
        for raw in value["aggregate_role_bindings"]:
            if (
                type(raw) is not dict
                or set(raw) != _AGGREGATE_ROLE_BINDING_FIELDS
                or type(raw["operation"]) is not str
                or raw["operation"] not in _AGGREGATE_OPERATIONS
                or type(raw["report_norm_id"]) is not int
                or raw["report_norm_id"] <= 0
                or type(raw["role"]) is not str
                or not raw["role"]
                or type(raw["source_roles"]) is not list
                or len(raw["source_roles"]) < 2
                or any(type(role) is not str or not role for role in raw["source_roles"])
                or len(raw["source_roles"]) != len(set(raw["source_roles"]))
            ):
                raise _error("aggregate family schema role binding drifted")
            aggregates.append(canonical_clone_v1(raw))
    direct_roles = [item["role"] for item in direct]
    aggregate_source_roles = [role for item in aggregates for role in item["source_roles"]]
    target_roles = [*direct_roles, *(item["role"] for item in aggregates)]
    target_ids = [
        *(item["report_norm_id"] for item in direct),
        *(item["report_norm_id"] for item in aggregates),
    ]
    role_order = {role: ordinal for ordinal, role in enumerate(family_roles)}
    if (
        any(role not in role_order for role in [*direct_roles, *aggregate_source_roles])
        or len([*direct_roles, *aggregate_source_roles])
        != len(set([*direct_roles, *aggregate_source_roles]))
        or set([*direct_roles, *aggregate_source_roles]) != set(family_roles)
        or direct_roles != sorted(direct_roles, key=role_order.__getitem__)
        or any(
            item["source_roles"] != sorted(item["source_roles"], key=role_order.__getitem__)
            for item in aggregates
        )
        or any(item["role"] in family_roles for item in aggregates)
        or len(target_roles) != len(set(target_roles))
        or len(target_ids) != len(set(target_ids))
        or value["family_report_norm_id"] in target_ids
    ):
        raise _error("family schema binding must cover the exact declarative role axis")
    if spec_version == SPEC_FORMAT_VERSION and direct_roles != family_roles:
        raise _error("V1 family schema binding must directly cover every role")
    return canonical_clone_v1(value)


def _schema_graph(root: Path) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    try:
        payload = archive_v1._root_bytes(root, SCHEMA_GRAPH_PATH, "tracked TM schema graph")
    except archive_v1.FamilyFirstSemanticLabelArchiveV1Error as exc:
        raise _error("cannot read the tracked TM schema graph") from exc
    nodes: dict[int, dict[str, Any]] = {}
    for ordinal, raw in enumerate(payload.splitlines(), 1):
        try:
            node = json.loads(raw.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _error(f"tracked schema graph line {ordinal} is not strict JSON") from exc
        schema_id = node.get("schema_id") if type(node) is dict else None
        if type(schema_id) is not int or schema_id <= 0 or schema_id in nodes:
            raise _error("tracked schema graph identity axis drifted")
        nodes[schema_id] = node
    if not nodes:
        raise _error("tracked schema graph is empty")
    return nodes, {
        "path": SCHEMA_GRAPH_PATH.as_posix(),
        "sha256": _sha(payload),
        "size_bytes": len(payload),
    }


def _bind_schema(
    nodes: dict[int, dict[str, Any]], spec: dict[str, Any]
) -> tuple[
    dict[str, Any],
    dict[str, dict[str, Any]],
    list[tuple[dict[str, Any], dict[str, Any]]],
]:
    parent = nodes.get(spec["family_report_norm_id"])
    if (
        type(parent) is not dict
        or parent.get("statement_type") != "TM"
        or type(parent.get("canonical_name")) is not str
        or type(parent.get("children")) is not list
        or not _schema_contract_axes_are_closed(parent)
    ):
        raise _error("family ReportNormId is not one live TM schema parent")
    by_role: dict[str, dict[str, Any]] = {}
    aggregate_bindings: list[tuple[dict[str, Any], dict[str, Any]]] = []
    bindings = [
        *spec["role_bindings"],
        *spec.get("aggregate_role_bindings", []),
    ]
    for binding in bindings:
        node = nodes.get(binding["report_norm_id"])
        if (
            type(node) is not dict
            or node.get("statement_type") != "TM"
            or node.get("parent_id") != parent["schema_id"]
            or binding["report_norm_id"] not in parent["children"]
            or type(node.get("canonical_name")) is not str
            or not node["canonical_name"]
            or not _schema_contract_axes_are_closed(node)
        ):
            raise _error("role ReportNormId is not a direct live child of its family")
        if "source_roles" in binding:
            aggregate_bindings.append((binding, node))
        else:
            by_role[binding["role"]] = node
    return parent, by_role, aggregate_bindings


def _schema_contract_axes_are_closed(node: dict[str, Any]) -> bool:
    return (
        type(node.get("scope")) is list
        and bool(node["scope"])
        and all(item in {"CONSOLIDATED", "SEPARATE"} for item in node["scope"])
        and len(node["scope"]) == len(set(node["scope"]))
        and type(node.get("allowed_period_type")) is list
        and bool(node["allowed_period_type"])
        and all(item in {"DURATION", "SNAPSHOT"} for item in node["allowed_period_type"])
        and len(node["allowed_period_type"]) == len(set(node["allowed_period_type"]))
        and type(node.get("allowed_sign")) is list
        and bool(node["allowed_sign"])
        and all(item in {"NEGATIVE", "POSITIVE", "ZERO"} for item in node["allowed_sign"])
        and len(node["allowed_sign"]) == len(set(node["allowed_sign"]))
    )


def _context_by_column(trial: dict[str, Any]) -> dict[int, dict[str, Any]]:
    context = trial["column_context"]
    if (
        type(context) is not dict
        or context.get("status") != "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
        or type(context.get("period_axis")) is not list
        or type(context.get("unit_axis")) is not list
    ):
        raise _error("schema-ready trial lost its resolved period/unit context")
    periods = {item["column_ordinal"]: item for item in context["period_axis"]}
    units = {item["column_ordinal"]: item for item in context["unit_axis"]}
    if set(periods) != set(units):
        raise _error("schema-ready period and unit axes differ")
    return {
        ordinal: {
            "currency": units[ordinal]["currency"],
            "magnitude_power10": units[ordinal]["magnitude_power10"],
            "period": periods[ordinal]["resolved_period"],
            "unit_kind": units[ordinal]["unit_kind"],
        }
        for ordinal in sorted(periods)
    }


def _cell(value: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    token = value.get("parsed_token")
    if (
        type(token) is not dict
        or token.get("classification") not in {"DASH_ZERO", "SIGNED_NUMBER"}
        or type(token.get("coefficient")) is not int
        or type(token.get("scale")) is not int
        or type(value.get("sample_id")) is not str
        or type(value.get("crop_ref")) is not dict
        or type(value.get("bbox")) is not list
    ):
        raise _error("schema-ready numeric cell is not one exact pixel-bound value")
    return {
        "column_ordinal": value["column_ordinal"],
        "crop_ref": canonical_clone_v1(value["crop_ref"]),
        "currency": context["currency"],
        "magnitude_power10": context["magnitude_power10"],
        "numeric_value": {
            "coefficient": token["coefficient"],
            "scale": token["scale"],
        },
        "page_sequence": value["page_sequence"],
        "period": context["period"],
        "raw_pixel_bbox": canonical_clone_v1(value["bbox"]),
        "raw_prediction": value["raw_prediction"],
        "sample_id": value["sample_id"],
        "source_zero_kind": ("VISIBLE_DASH" if token["classification"] == "DASH_ZERO" else None),
        "unit_kind": context["unit_kind"],
    }


def _row_mapping(
    row: dict[str, Any], node: dict[str, Any], contexts: dict[int, dict[str, Any]]
) -> dict[str, Any]:
    values = row.get("values")
    if (
        type(values) is not list
        or set(value.get("column_ordinal") for value in values) != set(contexts)
        or row.get("status") != "VISIBLE_VALUE_LANES_BOUND"
    ):
        raise _error("schema-ready role row does not cover its complete column axis")
    material = {
        "canonical_name": node["canonical_name"],
        "mapping_kind": "DIRECT_DECLARATIVE_ROLE_TO_LIVE_SCHEMA_CHILD",
        "report_norm_id": node["schema_id"],
        "role": row["role"],
        "source_surface": row["label_match"]["surface"],
        "values": [
            _cell(value, contexts[value["column_ordinal"]])
            for value in sorted(values, key=lambda item: item["column_ordinal"])
        ],
    }
    return {
        **material,
        "item_mapping_id": "ffasmv1:item:" + canonical_json_sha256_v1(material),
    }


def _sum_row_values(values: list[dict[str, Any]]) -> dict[str, int]:
    tokens = [value.get("parsed_token") for value in values]
    if (
        not tokens
        or any(
            type(token) is not dict
            or token.get("classification") not in {"DASH_ZERO", "SIGNED_NUMBER"}
            or type(token.get("coefficient")) is not int
            or type(token.get("scale")) is not int
            or token["scale"] < 0
            or type(token.get("percentage_mark_present")) is not bool
            for token in tokens
        )
        or len({token["percentage_mark_present"] for token in tokens}) != 1
    ):
        raise _error("aggregate schema role retained incompatible numeric components")
    scale = max(token["scale"] for token in tokens)
    coefficient = sum(token["coefficient"] * (10 ** (scale - token["scale"])) for token in tokens)
    while scale > 0 and coefficient % 10 == 0:
        coefficient //= 10
        scale -= 1
    return {"coefficient": coefficient, "scale": scale}


def _aggregate_mapping(
    rows: list[dict[str, Any]],
    binding: dict[str, Any],
    node: dict[str, Any],
    contexts: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    by_role = {row["role"]: row for row in rows}
    components = []
    for role in binding["source_roles"]:
        row = by_role.get(role)
        if row is None:
            continue
        values = row.get("values")
        if (
            type(values) is not list
            or set(value.get("column_ordinal") for value in values) != set(contexts)
            or row.get("status") != "VISIBLE_VALUE_LANES_BOUND"
        ):
            raise _error("aggregate schema source role does not cover its complete column axis")
        components.append(
            {
                "role": role,
                "source_surface": row["label_match"]["surface"],
                "values": [
                    _cell(value, contexts[value["column_ordinal"]])
                    for value in sorted(values, key=lambda item: item["column_ordinal"])
                ],
            }
        )
    if not components:
        raise _error("aggregate schema mapping requires at least one observed source role")
    values = []
    for column_ordinal, context in contexts.items():
        raw_components = [
            next(
                value
                for value in by_role[component["role"]]["values"]
                if value["column_ordinal"] == column_ordinal
            )
            for component in components
        ]
        values.append(
            {
                "column_ordinal": column_ordinal,
                "currency": context["currency"],
                "magnitude_power10": context["magnitude_power10"],
                "numeric_value": _sum_row_values(raw_components),
                "period": context["period"],
                "source_component_sample_ids": [value["sample_id"] for value in raw_components],
                "unit_kind": context["unit_kind"],
            }
        )
    material = {
        "canonical_name": node["canonical_name"],
        "mapping_kind": "SUM_OBSERVED_SOURCE_ROLES_TO_LIVE_SCHEMA_CHILD",
        "report_norm_id": node["schema_id"],
        "role": binding["role"],
        "source_components": components,
        "source_surface": None,
        "values": values,
    }
    return {
        **material,
        "item_mapping_id": "ffasmv1:item:" + canonical_json_sha256_v1(material),
    }


def _total_mapping(
    trial: dict[str, Any], node: dict[str, Any], contexts: dict[int, dict[str, Any]]
) -> dict[str, Any]:
    closure = trial["additive_closure"]
    row_axis = trial["row_axis"]
    if (
        type(closure) is not dict
        or closure.get("status") != "CORROBORATED_EXACT_UNIQUE_TRAILING_TOTAL"
        or type(closure.get("exact_total_candidates")) is not list
        or len(closure["exact_total_candidates"]) != 1
    ):
        raise _error("schema-ready family total lost exact additive closure")
    ordinal = closure["exact_total_candidates"][0]["candidate_ordinal"]
    candidates = [
        row for row in row_axis["trailing_value_rows"] if row.get("candidate_ordinal") == ordinal
    ]
    if len(candidates) != 1 or candidates[0].get("status") != "COMPLETE_VISIBLE_TRAILING_VALUE_ROW":
        raise _error("schema-ready total row does not replay from its closure candidate")
    values = candidates[0]["values"]
    if set(value.get("column_ordinal") for value in values) != set(contexts):
        raise _error("schema-ready total row does not cover its complete column axis")
    material = {
        "canonical_name": node["canonical_name"],
        "mapping_kind": "EXACT_VISIBLE_ADDITIVE_FAMILY_TOTAL_TO_LIVE_SCHEMA_PARENT",
        "report_norm_id": node["schema_id"],
        "role": "FAMILY_TOTAL",
        "source_surface": None,
        "values": [
            _cell(value, contexts[value["column_ordinal"]])
            for value in sorted(values, key=lambda item: item["column_ordinal"])
        ],
    }
    return {
        **material,
        "item_mapping_id": "ffasmv1:item:" + canonical_json_sha256_v1(material),
    }


def _trial(
    trial: dict[str, Any],
    parent: dict[str, Any],
    by_role: dict[str, dict[str, Any]],
    aggregate_bindings: list[tuple[dict[str, Any], dict[str, Any]]],
    *,
    schema_period_type: str,
) -> dict[str, Any]:
    base = {
        "document_ordinal": trial["document_ordinal"],
        "private_provenance": canonical_clone_v1(trial["private_provenance"]),
        "source_pdf_ref": canonical_clone_v1(trial["source_pdf_ref"]),
    }
    if trial["evidence_status"] == "NOT_OBSERVED_PROPOSAL_ONLY":
        return {
            **base,
            "mapping_status": "NOT_OBSERVED_PROPOSAL_ONLY",
            "mappings": [],
            "unresolved_reasons": [],
        }
    if trial["evidence_status"] != "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY":
        return {
            **base,
            "mapping_status": "UNRESOLVED",
            "mappings": [],
            "unresolved_reasons": canonical_clone_v1(trial["unresolved_reasons"]),
        }
    contexts = _context_by_column(trial)
    rows = trial["row_axis"]["rows"]
    aggregate_by_source = {
        source_role: (binding, node)
        for binding, node in aggregate_bindings
        for source_role in binding["source_roles"]
    }
    if (
        type(rows) is not list
        or len(rows) != len({row.get("role") for row in rows})
        or any(
            row.get("role") not in by_role and row.get("role") not in aggregate_by_source
            for row in rows
        )
    ):
        raise _error("schema-ready trial retained an unknown or duplicate semantic role")
    mappings = []
    emitted_aggregates: set[str] = set()
    for row in rows:
        role = row["role"]
        if role in by_role:
            mappings.append(_row_mapping(row, by_role[role], contexts))
            continue
        binding, node = aggregate_by_source[role]
        if binding["role"] in emitted_aggregates:
            continue
        emitted_aggregates.add(binding["role"])
        mappings.append(_aggregate_mapping(rows, binding, node, contexts))
    mappings.append(_total_mapping(trial, parent, contexts))
    source_scope = _SOURCE_SCOPE_TO_SCHEMA_SCOPE.get(trial["private_provenance"].get("scope"))
    nodes = {parent["schema_id"]: parent}
    nodes.update({node["schema_id"]: node for node in by_role.values()})
    nodes.update({node["schema_id"]: node for _, node in aggregate_bindings})
    compatibility_reasons = []
    for mapping in mappings:
        node = nodes[mapping["report_norm_id"]]
        if source_scope is None or source_scope not in node["scope"]:
            compatibility_reasons.append(
                f"SCHEMA_SCOPE_NOT_ALLOWED:{node['schema_id']}:{source_scope or 'UNRESOLVED'}"
            )
        if schema_period_type not in node["allowed_period_type"]:
            compatibility_reasons.append(
                f"SCHEMA_PERIOD_TYPE_NOT_ALLOWED:{node['schema_id']}:{schema_period_type}"
            )
        for value in mapping["values"]:
            coefficient = value["numeric_value"]["coefficient"]
            sign = "ZERO" if coefficient == 0 else "POSITIVE" if coefficient > 0 else "NEGATIVE"
            if sign not in node["allowed_sign"]:
                compatibility_reasons.append(f"SCHEMA_SIGN_NOT_ALLOWED:{node['schema_id']}:{sign}")
    if compatibility_reasons:
        return {
            **base,
            "mapping_status": "UNRESOLVED",
            "mappings": [],
            "unresolved_reasons": list(dict.fromkeys(compatibility_reasons)),
        }
    return {
        **base,
        "mapping_status": "VERIFIED_BY_CODEX",
        "mappings": mappings,
        "unresolved_reasons": [],
    }


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "document_count": len(trials),
        "not_observed_proposal_count": sum(
            trial["mapping_status"] == "NOT_OBSERVED_PROPOSAL_ONLY" for trial in trials
        ),
        "unresolved_document_count": sum(
            trial["mapping_status"] == "UNRESOLVED" for trial in trials
        ),
        "verified_document_count": sum(
            trial["mapping_status"] == "VERIFIED_BY_CODEX" for trial in trials
        ),
        "verified_mapping_count": sum(
            len(trial["mappings"])
            for trial in trials
            if trial["mapping_status"] == "VERIFIED_BY_CODEX"
        ),
    }


def _validate(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _RESULT_FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "FAMILY_FIRST_ACCOUNTING_SCHEMA_MAPPING_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["family_id"]) is not str
        or not value["family_id"]
        or type(value["evidence_sweep_id"]) is not str
        or not value["evidence_sweep_id"].startswith("ffaesv1:sweep:")
        or type(value["schema_graph_ref"]) is not dict
        or set(value["schema_graph_ref"]) != {"path", "sha256", "size_bytes"}
        or value["schema_graph_ref"]["path"] != SCHEMA_GRAPH_PATH.as_posix()
        or type(value["schema_graph_ref"]["sha256"]) is not str
        or _SHA256.fullmatch(value["schema_graph_ref"]["sha256"]) is None
        or type(value["schema_graph_ref"]["size_bytes"]) is not int
        or value["schema_graph_ref"]["size_bytes"] <= 0
        or type(value["schema_binding_spec"]) is not dict
        or set(value["schema_binding_spec"]) != {"sha256", "value"}
        or value["schema_binding_spec"]["sha256"]
        != canonical_json_sha256_v1(value["schema_binding_spec"]["value"])
        or type(value["trials"]) is not list
    ):
        raise _error("family-first schema mapping shape drifted")
    for ordinal, trial in enumerate(value["trials"], 1):
        if (
            type(trial) is not dict
            or set(trial) != _TRIAL_FIELDS
            or trial["document_ordinal"] != ordinal
            or trial["mapping_status"]
            not in {"NOT_OBSERVED_PROPOSAL_ONLY", "UNRESOLVED", "VERIFIED_BY_CODEX"}
            or type(trial["mappings"]) is not list
            or type(trial["unresolved_reasons"]) is not list
        ):
            raise _error("family-first schema mapping trial axis drifted")
    if type(value["metrics"]) is not dict or not same_typed_json_v1(
        value["metrics"], _metrics(value["trials"])
    ):
        raise _error("family-first schema mapping metrics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("mapping_id")
    if identity != "ffasmv1:mapping:" + canonical_json_sha256_v1(material):
        raise _error("family-first schema mapping identity drifted")
    return canonical_clone_v1(value)


def build_authenticated_family_first_accounting_schema_mapping_v1(
    project_root: Path,
    semantic_index_capability: semantic_v1.AuthenticatedFamilyFirstSemanticIndexV1,
    numeric_index_capability: numeric_v3.AuthenticatedFamilyFirstPPocrV6NumericIndexV3,
    family_spec: Any,
    evaluation_spec: Any,
    schema_binding_spec: Any,
) -> dict[str, Any]:
    """Rebuild live family evidence and bind admitted roles to the tracked schema."""

    root = archive_v1._root(project_root)
    spec = _schema_spec(schema_binding_spec, family_spec)
    nodes, graph_ref = _schema_graph(root)
    parent, by_role, aggregate_bindings = _bind_schema(nodes, spec)
    sweep = evidence_v1.build_authenticated_family_first_accounting_evidence_sweep_v1(
        semantic_index_capability,
        numeric_index_capability,
        family_spec,
        evaluation_spec,
    )
    if sweep["family_id"] != spec["family_id"]:
        raise _error("family evidence and schema binding identify different families")
    try:
        period_semantics = sweep["evaluation_spec"]["value"]["period_semantics"]
        schema_period_type = _PERIOD_SEMANTICS_TO_SCHEMA_TYPE[period_semantics]
    except (KeyError, TypeError) as exc:
        raise _error("family evidence lost its resolved schema period type") from exc
    trials = [
        _trial(
            trial,
            parent,
            by_role,
            aggregate_bindings,
            schema_period_type=schema_period_type,
        )
        for trial in sweep["trials"]
    ]
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "evidence_sweep_id": sweep["sweep_id"],
        "family_id": spec["family_id"],
        "format_version": FORMAT_VERSION,
        "metrics": _metrics(trials),
        "schema_binding_spec": {
            "sha256": canonical_json_sha256_v1(spec),
            "value": spec,
        },
        "schema_graph_ref": graph_ref,
        "state": "FAMILY_FIRST_ACCOUNTING_SCHEMA_MAPPING_COMPLETE",
        "trials": trials,
    }
    return _validate(
        {**material, "mapping_id": "ffasmv1:mapping:" + canonical_json_sha256_v1(material)}
    )


def validate_authenticated_family_first_accounting_schema_mapping_replay_v1(
    value: Any,
    project_root: Path,
    semantic_index_capability: semantic_v1.AuthenticatedFamilyFirstSemanticIndexV1,
    numeric_index_capability: numeric_v3.AuthenticatedFamilyFirstPPocrV6NumericIndexV3,
    family_spec: Any,
    evaluation_spec: Any,
    schema_binding_spec: Any,
) -> dict[str, Any]:
    """Exact-rebuild the mapping from live OCR indices and tracked schema bytes."""

    persisted = _validate(value)
    expected = build_authenticated_family_first_accounting_schema_mapping_v1(
        project_root,
        semantic_index_capability,
        numeric_index_capability,
        family_spec,
        evaluation_spec,
        schema_binding_spec,
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("family-first schema mapping does not replay exactly")
    return persisted
