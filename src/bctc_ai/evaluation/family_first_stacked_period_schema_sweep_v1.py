"""Authenticated all-filing schema sweep for stacked or horizontal period tables."""

from __future__ import annotations

import hashlib
from typing import Any

from bctc_ai.evaluation import accounting_document_unit_context_v1 as unit_context_v1
from bctc_ai.evaluation import accounting_stacked_period_lane_axis_v1 as lane_axis_v1
from bctc_ai.evaluation import accounting_stacked_period_schema_mapping_v1 as schema_mapping_v1
from bctc_ai.evaluation import family_first_document_evidence_store_v1 as document_store_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "FamilyFirstStackedPeriodSchemaSweepV1Error",
    "build_authenticated_family_first_stacked_period_schema_sweep_v1",
    "validate_authenticated_family_first_stacked_period_schema_sweep_replay_v1",
]


FORMAT_VERSION = "FAMILY_FIRST_STACKED_PERIOD_SCHEMA_SWEEP_V1"
CLAIM_BOUNDARY = (
    "AUTHENTICATED_ALL_FILING_COMPLETE_DOCUMENT_TOPOLOGY_STACKED_OR_HORIZONTAL_"
    "VISIBLE_PERIOD_LANE_EXACT_TWO_READER_NUMERIC_CONSENSUS_ACCOUNTING_VETO_"
    "LOCAL_OR_REPEATED_DOCUMENT_UNIT_ACTUAL_DOCUMENT_SCOPE_TRACKED_SCHEMA_"
    "BOUNDED_VERIFIED_MAPPING_OR_REPORT_ABSENCE_NO_EXPORT_OR_CANONICAL_AUTHORITY"
)
_AUTHORITY = {
    "all_authenticated_documents_scanned_for_topology": True,
    "bank_file_note_page_year_used_for_matching_or_routing": False,
    "bounded_report_absence_authority": True,
    "bounded_schema_mapping_authority": True,
    "canonicalization_authority": False,
    "export_authority": False,
    "gemma4_used_as_sole_numeric_authority": False,
    "local_or_repeated_document_unit_required": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "schema_creation_authority": False,
    "text_similarity_alone_can_map": False,
}
_FIELDS = {
    "authority",
    "challenger_evidence",
    "claim_boundary",
    "family_id",
    "family_topology_spec",
    "format_version",
    "layout_spec",
    "metrics",
    "schema_binding_spec",
    "schema_graph_ref",
    "state",
    "store_projection",
    "sweep_id",
    "trials",
}
_TRIAL_FIELDS = {
    "document_ordinal",
    "document_packet",
    "lane_axis",
    "schema_mapping",
    "selected_page_span",
    "status",
    "topology_scan",
    "unit_context",
    "unresolved_reasons",
    "verified_mapping_count",
}
_METRIC_FIELDS = {
    "bounded_not_observed_count",
    "document_count",
    "numeric_challenger_rescue_count",
    "unresolved_document_count",
    "verified_document_count",
    "verified_mapping_count",
}
_CHALLENGER_TOP_FIELDS = {
    "authority",
    "claim_boundary",
    "decision",
    "evaluation_id",
    "format_version",
    "metrics",
    "observations",
    "prompt",
    "state",
}
_CHALLENGER_AUTHORITY = {
    "accounting_authority": False,
    "canonicalization_authority": False,
    "export_authority": False,
    "geometry_authority": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "raw_api_response_self_authenticating": False,
    "schema_authority": False,
    "tracked_response_digest_and_extracted_surface_only": True,
}


class FamilyFirstStackedPeriodSchemaSweepV1Error(ValueError):
    """A store, topology, period/lane, numeric, unit, scope, or schema gate drifted."""


def _error(message: str) -> FamilyFirstStackedPeriodSchemaSweepV1Error:
    return FamilyFirstStackedPeriodSchemaSweepV1Error(message)


def _challenger_evidence(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _CHALLENGER_TOP_FIELDS
        or value["format_version"]
        != "FAMILY_FIRST_DERIVATIVE_HOSTED_GEMMA4_NUMERIC_CHALLENGER_EVALUATION_V1"
        or value["state"] != "COMPLETE"
        or not same_typed_json_v1(value["authority"], _CHALLENGER_AUTHORITY)
        or type(value["prompt"]) is not dict
        or set(value["prompt"]) != {"sha256", "text"}
        or hashlib.sha256(value["prompt"]["text"].encode("utf-8")).hexdigest()
        != value["prompt"]["sha256"]
        or type(value["observations"]) is not list
        or len(value["observations"])
        != len({item.get("sample_id") for item in value["observations"] if type(item) is dict})
    ):
        raise _error("hosted numeric-challenger evidence drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("evaluation_id")
    if identity != "derivativegemma4v1:evaluation:" + canonical_json_sha256_v1(material):
        raise _error("hosted numeric-challenger evidence identity drifted")
    return canonical_clone_v1(value)


def _schema_nodes(value: Any) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    if type(value) not in {list, tuple} or not value:
        raise _error("stacked-period sweep requires the tracked schema graph")
    nodes = {}
    for raw in value:
        if (
            type(raw) is not dict
            or type(raw.get("schema_id")) is not int
            or raw["schema_id"] <= 0
            or type(raw.get("scope")) is not list
            or raw["schema_id"] in nodes
        ):
            raise _error("tracked schema graph node drifted")
        nodes[raw["schema_id"]] = canonical_clone_v1(raw)
    graph = list(value)
    return nodes, {"node_count": len(graph), "sha256": canonical_json_sha256_v1(graph)}


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "bounded_not_observed_count": sum(
            item["status"] == "NOT_OBSERVED_IN_BOUND_REPORT" for item in trials
        ),
        "document_count": len(trials),
        "numeric_challenger_rescue_count": sum(
            item["schema_mapping"]["metrics"]["numeric_challenger_rescue_count"]
            for item in trials
            if item["schema_mapping"] is not None
        ),
        "unresolved_document_count": sum(item["status"] == "UNRESOLVED" for item in trials),
        "verified_document_count": sum(item["status"] == "VERIFIED_BY_CODEX" for item in trials),
        "verified_mapping_count": sum(item["verified_mapping_count"] for item in trials),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "AUTHENTICATED_ALL_FILING_STACKED_PERIOD_SCHEMA_SWEEP_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["family_id"]) is not str
        or not value["family_id"]
        or type(value["trials"]) is not list
        or type(value["metrics"]) is not dict
        or set(value["metrics"]) != _METRIC_FIELDS
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("stacked-period all-filing sweep result drifted")
    for ordinal, trial in enumerate(value["trials"], 1):
        if (
            type(trial) is not dict
            or set(trial) != _TRIAL_FIELDS
            or trial["document_ordinal"] != ordinal
            or type(trial["document_packet"]) is not dict
            or type(trial["topology_scan"]) is not dict
            or type(trial["unresolved_reasons"]) is not list
            or any(type(item) is not str or not item for item in trial["unresolved_reasons"])
            or type(trial["verified_mapping_count"]) is not int
            or trial["verified_mapping_count"] < 0
        ):
            raise _error("stacked-period all-filing trial drifted")
        if trial["status"] == "VERIFIED_BY_CODEX":
            if (
                trial["lane_axis"] is None
                or trial["schema_mapping"] is None
                or trial["unit_context"] is None
                or trial["selected_page_span"] is None
                or trial["unresolved_reasons"]
                or trial["verified_mapping_count"]
                != trial["schema_mapping"]["metrics"]["mapping_proposal_count"]
                or trial["verified_mapping_count"] <= 0
            ):
                raise _error("verified stacked-period trial is incomplete")
        elif trial["status"] == "NOT_OBSERVED_IN_BOUND_REPORT":
            if (
                any(
                    trial[key] is not None
                    for key in ("lane_axis", "schema_mapping", "selected_page_span", "unit_context")
                )
                or trial["verified_mapping_count"] != 0
            ):
                raise _error("bounded-absence stacked-period trial exposes mapping evidence")
        elif trial["status"] != "UNRESOLVED":
            raise _error("stacked-period trial status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("sweep_id")
    if identity != "ffspssv1:sweep:" + canonical_json_sha256_v1(material):
        raise _error("stacked-period all-filing sweep identity drifted")
    return canonical_clone_v1(value)


def build_authenticated_family_first_stacked_period_schema_sweep_v1(
    document_store: document_store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    family_topology_spec: Any,
    layout_spec: Any,
    schema_binding_spec: Any,
    schema_graph: Any,
    challenger_evidence: Any,
    *,
    jobs: int = 12,
) -> dict[str, Any]:
    """Build one exact all-filing verified mapping/absence result."""

    store_projection = (
        document_store_v1.project_authenticated_family_first_document_evidence_store_v1(
            document_store
        )
    )
    challenger = _challenger_evidence(challenger_evidence)
    nodes, graph_ref = _schema_nodes(schema_graph)
    scans = document_store_v1.read_authenticated_family_first_topology_scans_v1(
        document_store, family_topology_spec, jobs=jobs
    )
    if len(scans) != store_projection["metrics"]["document_count"]:
        raise _error("stacked-period topology/document denominator differs")
    observations_by_sample = {item["sample_id"]: item for item in challenger["observations"]}
    trials = []
    for ordinal, scan in enumerate(scans, 1):
        packet = document_store_v1.read_authenticated_family_first_document_packet_v1(
            document_store, document_ordinal=ordinal
        )
        base = {
            "document_ordinal": ordinal,
            "document_packet": packet,
            "topology_scan": scan,
        }
        if scan["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY":
            trials.append(
                {
                    **base,
                    "lane_axis": None,
                    "schema_mapping": None,
                    "selected_page_span": None,
                    "status": "NOT_OBSERVED_IN_BOUND_REPORT",
                    "unit_context": None,
                    "unresolved_reasons": [],
                    "verified_mapping_count": 0,
                }
            )
            continue
        if scan["status"] != "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL" or len(scan["regions"]) != 1:
            trials.append(
                {
                    **base,
                    "lane_axis": None,
                    "schema_mapping": None,
                    "selected_page_span": None,
                    "status": "UNRESOLVED",
                    "unit_context": None,
                    "unresolved_reasons": ["TOPOLOGY_NOT_ONE_UNIQUE_COMPLETE_REGION"],
                    "verified_mapping_count": 0,
                }
            )
            continue
        region = scan["regions"][0]
        start = region["page_sequence"]
        stop = region["cluster_end_page_sequence_inclusive"]
        snapshot = document_store_v1.read_authenticated_family_first_document_evidence_snapshot_v1(
            document_store,
            document_ordinal=ordinal,
            selected_pages=tuple(range(start, stop + 1)),
        )
        pages = snapshot["joined_pages"]
        axis = lane_axis_v1.build_accounting_stacked_period_lane_axis_v1(
            pages, family_topology_spec, region, layout_spec
        )
        sample_ids = {
            line["sample_id"]
            for page in pages
            if start <= page["page_sequence"] <= stop
            for line in page["lines"]
        }
        observations = [
            observations_by_sample[sample_id]
            for sample_id in observations_by_sample
            if sample_id in sample_ids
        ]
        schema_mapping = schema_mapping_v1.build_accounting_stacked_period_schema_mapping_v1(
            pages,
            family_topology_spec,
            layout_spec,
            axis,
            schema_binding_spec,
            schema_graph,
            observations,
        )
        unit_context = unit_context_v1.build_accounting_document_unit_context_v1(pages, region)
        actual_scope = "CONSOLIDATED" if packet["scope"] == "CONSOLIDATED" else "SEPARATE"
        scope_failures = [
            item["report_norm_id"]
            for item in schema_mapping["mapping_proposals"]
            if item["report_norm_id"] not in nodes
            or actual_scope not in nodes[item["report_norm_id"]]["scope"]
        ]
        reasons = list(schema_mapping["unresolved_cells"])
        reason_strings = [
            "SCHEMA_MAPPING_UNRESOLVED:" + canonical_json_sha256_v1(item) for item in reasons
        ]
        if scope_failures:
            reason_strings.append("ACTUAL_DOCUMENT_SCOPE_NOT_ALLOWED_BY_TARGET_SCHEMA")
        verified_count = len(schema_mapping["mapping_proposals"]) if not reason_strings else 0
        trials.append(
            {
                **base,
                "lane_axis": axis,
                "schema_mapping": schema_mapping,
                "selected_page_span": [start, stop],
                "status": "VERIFIED_BY_CODEX" if not reason_strings else "UNRESOLVED",
                "unit_context": unit_context,
                "unresolved_reasons": reason_strings,
                "verified_mapping_count": verified_count,
            }
        )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "challenger_evidence": challenger,
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": family_topology_spec["family_id"],
        "family_topology_spec": canonical_clone_v1(family_topology_spec),
        "format_version": FORMAT_VERSION,
        "layout_spec": canonical_clone_v1(layout_spec),
        "metrics": _metrics(trials),
        "schema_binding_spec": canonical_clone_v1(schema_binding_spec),
        "schema_graph_ref": graph_ref,
        "state": "AUTHENTICATED_ALL_FILING_STACKED_PERIOD_SCHEMA_SWEEP_COMPLETE",
        "store_projection": store_projection,
        "trials": trials,
    }
    return _validate_result(
        {**material, "sweep_id": "ffspssv1:sweep:" + canonical_json_sha256_v1(material)}
    )


def validate_authenticated_family_first_stacked_period_schema_sweep_replay_v1(
    value: Any,
    document_store: document_store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    family_topology_spec: Any,
    layout_spec: Any,
    schema_binding_spec: Any,
    schema_graph: Any,
    challenger_evidence: Any,
    *,
    jobs: int = 12,
) -> dict[str, Any]:
    persisted = _validate_result(value)
    expected = build_authenticated_family_first_stacked_period_schema_sweep_v1(
        document_store,
        family_topology_spec,
        layout_spec,
        schema_binding_spec,
        schema_graph,
        challenger_evidence,
        jobs=jobs,
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("stacked-period all-filing sweep does not replay exactly")
    return persisted
