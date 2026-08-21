"""Generic live schema binding for one completed family evidence sweep.

The mapper contains no bank, filing, page, year, family label, or ReportNormId
logic.  A declarative binding spec connects semantic roles to the current TM
schema graph only after the shared topology, geometry, numeric, period, unit,
and accounting gates have all admitted a trial.  The exact live evidence sweep
is rebuilt on every public replay.
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
    "FamilyFirstAccountingSchemaMappingV1Error",
    "build_authenticated_family_first_accounting_schema_mapping_v1",
    "validate_authenticated_family_first_accounting_schema_mapping_replay_v1",
]


FORMAT_VERSION = "FAMILY_FIRST_ACCOUNTING_SCHEMA_MAPPING_V1"
SPEC_FORMAT_VERSION = "ACCOUNTING_FAMILY_SCHEMA_BINDING_SPEC_V1"
SCHEMA_GRAPH_PATH = Path("reference/schemas/schema_graph.jsonl")
CLAIM_BOUNDARY = (
    "LIVE_REPLAYED_FAMILY_EVIDENCE_TO_TRACKED_TM_SCHEMA_DIRECT_PARENT_CHILD_BINDING_"
    "VERIFIED_BY_CODEX_ONLY_AFTER_TOPOLOGY_GEOMETRY_PERIOD_UNIT_PIXEL_BOUND_PPOCRV6_"
    "NUMERIC_AND_ACCOUNTING_GATES_NO_BANK_PAGE_YEAR_ROUTING_NO_SCHEMA_CREATION_"
    "CANONICALIZATION_EXPORT_OR_PRODUCTION_AUTHORITY"
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
}
_SPEC_FIELDS = {
    "family_id",
    "family_report_norm_id",
    "format_version",
    "role_bindings",
}
_ROLE_BINDING_FIELDS = {"report_norm_id", "role"}
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
    if (
        type(value) is not dict
        or set(value) != _SPEC_FIELDS
        or value["format_version"] != SPEC_FORMAT_VERSION
        or value["family_id"] != family_spec["family_id"]
        or type(value["family_report_norm_id"]) is not int
        or value["family_report_norm_id"] <= 0
        or type(value["role_bindings"]) is not list
        or len(value["role_bindings"]) != len(family_roles)
    ):
        raise _error("family schema-binding specification drifted")
    parsed = []
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
        parsed.append(canonical_clone_v1(raw))
    if (
        [item["role"] for item in parsed] != family_roles
        or len({item["report_norm_id"] for item in parsed}) != len(parsed)
        or value["family_report_norm_id"] in {item["report_norm_id"] for item in parsed}
    ):
        raise _error("family schema binding must cover the exact declarative role axis")
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
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    parent = nodes.get(spec["family_report_norm_id"])
    if (
        type(parent) is not dict
        or parent.get("statement_type") != "TM"
        or type(parent.get("canonical_name")) is not str
        or type(parent.get("children")) is not list
    ):
        raise _error("family ReportNormId is not one live TM schema parent")
    by_role: dict[str, dict[str, Any]] = {}
    for binding in spec["role_bindings"]:
        node = nodes.get(binding["report_norm_id"])
        if (
            type(node) is not dict
            or node.get("statement_type") != "TM"
            or node.get("parent_id") != parent["schema_id"]
            or binding["report_norm_id"] not in parent["children"]
            or type(node.get("canonical_name")) is not str
            or not node["canonical_name"]
        ):
            raise _error("role ReportNormId is not a direct live child of its family")
        by_role[binding["role"]] = node
    return parent, by_role


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
    trial: dict[str, Any], parent: dict[str, Any], by_role: dict[str, dict[str, Any]]
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
    if (
        type(rows) is not list
        or len(rows) != len({row.get("role") for row in rows})
        or any(row.get("role") not in by_role for row in rows)
    ):
        raise _error("schema-ready trial retained an unknown or duplicate semantic role")
    mappings = [_row_mapping(row, by_role[row["role"]], contexts) for row in rows]
    mappings.append(_total_mapping(trial, parent, contexts))
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
    parent, by_role = _bind_schema(nodes, spec)
    sweep = evidence_v1.build_authenticated_family_first_accounting_evidence_sweep_v1(
        semantic_index_capability,
        numeric_index_capability,
        family_spec,
        evaluation_spec,
    )
    if sweep["family_id"] != spec["family_id"]:
        raise _error("family evidence and schema binding identify different families")
    trials = [_trial(trial, parent, by_role) for trial in sweep["trials"]]
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
