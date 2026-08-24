#!/usr/bin/env python3
"""Build the non-numeric structural Family-12 terminal for the fixed 140 files."""

from __future__ import annotations

import os
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))
sys.path.insert(0, os.fspath(PROJECT_ROOT / "src"))

from bctc_ai.evaluation import accounting_family_column_context_v1 as column_v1  # noqa: E402
from bctc_ai.evaluation import accounting_family_row_axis_v1 as row_v1  # noqa: E402
from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1  # noqa: E402
from bctc_ai.evaluation import (  # noqa: E402
    authenticated_semantic_region_snapshot_v1 as snapshot_v1,
)
from bctc_ai.evaluation import loan_enterprise_family12_graph_v1 as graph_v1  # noqa: E402
from bctc_ai.evaluation.loan_enterprise_family12_spec_v1 import (  # noqa: E402
    FAMILY_ID,
    build_loan_enterprise_family12_topology_spec_v1,
)
from bctc_ai.mapping import loan_enterprise_bounded_schema_v1 as schema_v1  # noqa: E402
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FORMAT_VERSION = "FAMILY_FIRST_LOAN_ENTERPRISE_140_FILING_SCHEMA_SWEEP_V1"
INPUT_FORMAT_VERSION = "FAMILY_FIRST_LOAN_ENTERPRISE_140_FILING_STRUCTURAL_INPUT_V1"
CLAIM_BOUNDARY = (
    "FIXED_140_FILING_AUTHENTICATED_FAMILY12_REGION_GRAPH_BOUND_REGION_FIRST_"
    "SHARED_CONTINUATION_TOPOLOGY_ROW_AXIS_UNIQUE_PERIOD_UNIT_AND_LIVE_BOUNDED_"
    "SCHEMA_JOIN_STRUCTURAL_STAGE_ONLY_AWAITS_EXACT_NUMERIC_ACCOUNTING_AND_"
    "MAPPING_REPLAY_NO_CORPUS_ABSENCE_NUMERIC_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
_TARGET_DOCUMENT_COUNT = 140
_GRAPH_DOCUMENT_FORMAT_VERSION = "LOAN_ENTERPRISE_FAMILY12_AUTHENTICATED_SNAPSHOT_GRAPH_V1"
_GRAPH_DOCUMENT_FIELDS = set(
    "authority claim_boundary document_id document_ordinal evidence_binding family_id "
    "format_version graph metrics outcome result_id snapshot_projection_binding state".split()
)
_GRAPH_BATCH_FIELDS = set(
    "authority claim_boundary documents evidence_binding family_id format_version metrics "
    "result_id state".split()
)
_GRAPH_EVIDENCE_FIELDS = set(
    "document_evidence_root_sha256 document_packet_id manifest_id outcome_id projection_id "
    "query_selection_id query_spec_id receipt_id snapshot_id".split()
)
_OUTCOME_FIELDS = set(
    "fallback_reason requires_full_document_review selected_pages selection_mode".split()
)
_PROJECTION_BINDING_FIELDS = set(
    "line_bindings_sha256 metrics page_bindings_sha256 projection_id region_pages_sha256 "
    "source_binding".split()
)
_PACKET_FIELDS = {"full_snapshot", "graph_document", "sparse_snapshot"}
_INPUT_FIELDS = {"authenticated_graph_batch", "format_version", "structural_packets"}
_RESULT_INPUT_FIELDS = set(
    "bounded_schema_projection graph_batch_result_id manifest_id query_spec_id receipt_id "
    "topology_spec_sha256".split()
)
_TRIAL_FIELDS = set(
    "absence_stage column_context column_layout document_id document_ordinal graph_binding "
    "numeric_stage reason row_axis schema_binding_proposals sparse_topology_replays "
    "structural_disposition terminal_disposition trial_id whole_graph whole_graph_binding "
    "whole_topology_scan".split()
)
_RESULT_FIELDS = set(
    "authority claim_boundary family_id format_version inputs metrics result_id state trials".split()
)
_AUTHORITY = {
    "absence_mapping_or_export_authority": False,
    "authenticated_graph_batch_required": True,
    "bank_filename_note_page_period_year_or_ordinal_used_for_routing": False,
    "full_document_hydration_required_only_for_not_observed_proof": True,
    "graph_near_or_branchless_challenger_can_be_absence": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "schema_join_is_mapping_authority": False,
    "snapshot_self_hash_is_authentication_authority": False,
    "structural_exact_is_complete_family_mapping": False,
}
_NUMERIC_PLACEHOLDER = {
    "accounting_closure": None,
    "mapped_rows": [],
    "numeric_cells": [],
    "status": "NOT_RUN_REQUIRED_FOR_FAMILY12_COMPLETION",
}
_COLUMN_LAYOUTS = (["MONEY", "MONEY"], ["MONEY", "PERCENT", "MONEY", "PERCENT"])


def _absence_placeholder(disposition: str) -> dict[str, Any]:
    return {
        "absence_mapping_rows": [],
        "authority": False,
        "status": (
            "STRUCTURAL_NOT_OBSERVED_ONLY_NO_SCHEMA_ABSENCE_EMISSION"
            if disposition == "NOT_OBSERVED"
            else "NOT_APPLICABLE_NO_ABSENCE_AUTHORITY"
        ),
    }


class FamilyFirstLoanEnterprise140FilingSchemaSweepV1Error(ValueError):
    """The Family-12 structural input, replay, or terminal contract drifted."""


def _error(message: str) -> FamilyFirstLoanEnterprise140FilingSchemaSweepV1Error:
    return FamilyFirstLoanEnterprise140FilingSchemaSweepV1Error(message)


def _projection_binding(projection: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "line_bindings_sha256": canonical_json_sha256_v1(projection["line_bindings"]),
        "metrics": canonical_clone_v1(projection["metrics"]),
        "page_bindings_sha256": canonical_json_sha256_v1(projection["page_bindings"]),
        "projection_id": projection["projection_id"],
        "region_pages_sha256": canonical_json_sha256_v1(projection["region_pages"]),
        "source_binding": canonical_clone_v1(projection["source_binding"]),
    }


def _self_hashed(value: Any, fields: set[str], *, prefix: str, label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise _error(f"{label} fields drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if type(identity) is not str or identity != prefix + canonical_json_sha256_v1(material):
        raise _error(f"{label} content identity drifted")
    return canonical_clone_v1(value)


def _graph_batch(value: Any) -> dict[str, Any]:
    batch = _self_hashed(
        value,
        _GRAPH_BATCH_FIELDS,
        prefix="lef12asv1:batch:",
        label="Family-12 authenticated graph batch",
    )
    documents = batch["documents"]
    binding = batch["evidence_binding"]
    metrics = batch["metrics"]
    if (
        batch["format_version"] != graph_v1.AUTHENTICATED_BATCH_FORMAT_VERSION
        or batch["family_id"] != FAMILY_ID
        or batch["claim_boundary"] != graph_v1._AUTHENTICATED_BATCH_CLAIM_BOUNDARY
        or not same_typed_json_v1(batch["authority"], graph_v1._AUTHENTICATED_BATCH_AUTHORITY)
        or batch["state"] != "FAMILY12_AUTHENTICATED_CORPUS_GRAPH_PROPOSALS_ONLY"
        or type(documents) is not list
        or len(documents) != _TARGET_DOCUMENT_COUNT
        or type(binding) is not dict
        or set(binding) != {"manifest_id", "query_spec_id", "receipt_id"}
        or any(type(binding[key]) is not str or not binding[key] for key in binding)
        or type(metrics) is not dict
        or metrics.get("document_count") != _TARGET_DOCUMENT_COUNT
    ):
        raise _error("Family-12 authenticated graph denominator drifted")
    return batch


def _graph_document(
    value: Any,
    *,
    expected: Mapping[str, Any],
    ordinal: int,
    batch_binding: Mapping[str, Any],
    sparse_snapshot: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not same_typed_json_v1(value, expected):
        raise _error("structural packet graph document differs from authenticated batch")
    document = _self_hashed(
        value,
        _GRAPH_DOCUMENT_FIELDS,
        prefix="lef12asv1:document:",
        label="Family-12 authenticated graph document",
    )
    evidence = document["evidence_binding"]
    outcome = document["outcome"]
    projection_binding = document["snapshot_projection_binding"]
    if (
        document["format_version"] != _GRAPH_DOCUMENT_FORMAT_VERSION
        or document["family_id"] != FAMILY_ID
        or document["claim_boundary"] != graph_v1._AUTHENTICATED_DOCUMENT_CLAIM_BOUNDARY
        or not same_typed_json_v1(document["authority"], graph_v1._AUTHENTICATED_DOCUMENT_AUTHORITY)
        or document["document_ordinal"] != ordinal
        or type(document["document_id"]) is not str
        or not document["document_id"]
        or document["state"] != "FAMILY12_AUTHENTICATED_SELECTED_SNAPSHOT_GRAPH_PROPOSAL_ONLY"
        or type(evidence) is not dict
        or set(evidence) != _GRAPH_EVIDENCE_FIELDS
        or any(type(evidence[key]) is not str or not evidence[key] for key in evidence)
        or type(outcome) is not dict
        or set(outcome) != _OUTCOME_FIELDS
        or type(outcome["requires_full_document_review"]) is not bool
        or type(outcome["selection_mode"]) is not str
        or not outcome["selection_mode"]
        or type(outcome["selected_pages"]) is not list
        or not outcome["selected_pages"]
        or any(type(page) is not int or page <= 0 for page in outcome["selected_pages"])
        or outcome["selected_pages"] != sorted(set(outcome["selected_pages"]))
        or type(projection_binding) is not dict
        or set(projection_binding) != _PROJECTION_BINDING_FIELDS
        or evidence["manifest_id"] != batch_binding["manifest_id"]
        or evidence["query_spec_id"] != batch_binding["query_spec_id"]
        or evidence["receipt_id"] != batch_binding["receipt_id"]
    ):
        raise _error("Family-12 authenticated graph document binding drifted")
    projection = snapshot_v1.build_authenticated_semantic_region_snapshot_v1(sparse_snapshot)
    snapshot_v1.validate_authenticated_semantic_region_snapshot_replay_v1(
        projection, sparse_snapshot
    )
    source = projection["source_binding"]
    if (
        not same_typed_json_v1(_projection_binding(projection), projection_binding)
        or document["document_id"] != source["document_id"]
        or ordinal != source["document_ordinal"]
        or evidence["document_evidence_root_sha256"] != source["document_evidence_root_sha256"]
        or evidence["document_packet_id"] != source["document_packet_id"]
        or evidence["projection_id"] != projection["projection_id"]
        or evidence["query_selection_id"] != source["query_selection_id"]
        or evidence["snapshot_id"] != source["snapshot_id"]
        or outcome["selected_pages"] != source["selected_pages"]
        or not same_typed_json_v1(document["metrics"], projection["metrics"])
    ):
        raise _error("Family-12 sparse snapshot differs from its graph document")
    try:
        graph_v1.validate_loan_enterprise_family12_graph_replay_v1(
            document["graph"], projection["region_pages"]
        )
    except graph_v1.LoanEnterpriseFamily12GraphV1Error as exc:
        raise _error("Family-12 graph document does not replay from sparse pages") from exc
    return document, projection


def _selected_runs(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    pages = snapshot.get("joined_pages")
    if type(pages) is not list or not pages:
        raise _error("Family-12 joined page axis drifted")
    physical = [page.get("page_sequence") for page in pages if type(page) is dict]
    if len(physical) != len(pages) or physical != sorted(set(physical)):
        raise _error("Family-12 joined page identities repeat")
    grouped: list[list[Mapping[str, Any]]] = []
    for page in pages:
        if not grouped or page["page_sequence"] != grouped[-1][-1]["page_sequence"] + 1:
            grouped.append([])
        grouped[-1].append(page)
    result = []
    for group in grouped:
        rebound = []
        binding = []
        for local, page in enumerate(group, 1):
            rebound.append({**canonical_clone_v1(page), "page_sequence": local})
            binding.append({"local_page_sequence": local, "physical_page": page["page_sequence"]})
        result.append({"joined_pages": rebound, "page_binding": binding})
    return result


def _topology_pages(joined_pages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "lines": [
                {
                    "bbox": canonical_clone_v1(line["bbox"]),
                    "source_line_index": line["line_ordinal"],
                    "source_text": None,
                    "vietocr_text": line["vietocr_text"],
                }
                for line in page["lines"]
            ],
            "page_sequence": page["page_sequence"],
        }
        for page in joined_pages
    ]


def _scan(joined_pages: Sequence[Mapping[str, Any]], spec: Mapping[str, Any]) -> dict[str, Any]:
    pages = _topology_pages(joined_pages)
    scan = topology_v1.build_accounting_family_topology_scan_v1(pages, spec)
    topology_v1.validate_accounting_family_topology_scan_replay_v1(scan, pages, spec)
    return scan


def _graph_candidate(graph: Mapping[str, Any]) -> tuple[str, str]:
    regions = graph.get("regions")
    near = graph.get("near_regions")
    rescue = graph.get("branchless_rescue_challengers")
    absences = graph.get("bounded_absences")
    if any(type(axis) is not list for axis in (regions, near, rescue, absences)):
        raise _error("Family-12 graph disposition axes drifted")
    if near or rescue:
        return "UNRESOLVED", "GRAPH_RETAINS_NEAR_OR_BRANCHLESS_CHALLENGER"
    if len(regions) == 1 and not absences:
        return "EXACT", "GRAPH_HAS_ONE_UNIQUE_STRUCTURAL_REGION"
    if not regions and len(absences) == 1:
        return "NOT_OBSERVED", "GRAPH_HAS_BOUNDED_LOCAL_ZERO_TARGET"
    return "UNRESOLVED", "GRAPH_REGION_OR_ABSENCE_CARDINALITY_UNRESOLVED"


def _full_material(
    full_snapshot: Any,
    sparse_source: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    projection = snapshot_v1.build_authenticated_semantic_region_snapshot_v1(full_snapshot)
    snapshot_v1.validate_authenticated_semantic_region_snapshot_replay_v1(projection, full_snapshot)
    source = projection["source_binding"]
    identity_fields = set(
        "document_evidence_root_sha256 document_id document_line_count document_ordinal "
        "document_packet_id document_page_count manifest_id".split()
    )
    if any(source[key] != sparse_source[key] for key in identity_fields) or source[
        "selected_pages"
    ] != list(range(1, source["document_page_count"] + 1)):
        raise _error("Family-12 whole snapshot is not the same complete document")
    graph = graph_v1.build_loan_enterprise_family12_graph_v1(projection["region_pages"])
    graph_v1.validate_loan_enterprise_family12_graph_replay_v1(graph, projection["region_pages"])
    return canonical_clone_v1(full_snapshot["joined_pages"]), projection, graph


def _schema_binding_proposals(
    graph_region: Mapping[str, Any], schema: Mapping[str, Any]
) -> list[dict[str, Any]]:
    nodes = {node["report_norm_id"]: node for node in schema["mapped_leaves"]}
    bindings = graph_region.get("binding_proposals")
    if type(bindings) is not list or not bindings:
        raise _error("Family-12 exact graph region has no schema binding proposal")
    result = []
    seen: set[int] = set()
    for binding in bindings:
        report_norm_id = binding.get("report_norm_id") if type(binding) is dict else None
        node = nodes.get(report_norm_id)
        if (
            type(report_norm_id) is not int
            or report_norm_id in seen
            or node is None
            or binding.get("schema_parent_report_norm_id") != node["parent_report_norm_id"]
            or binding.get("status") != "UNIQUE_SCHEMA_BINDING_PROPOSAL_NO_MAPPING_AUTHORITY"
            or (report_norm_id == 6058 and node["parent_report_norm_id"] != 727)
        ):
            raise _error("Family-12 graph/live-schema leaf join drifted")
        seen.add(report_norm_id)
        material = {
            "evidence_proposal_id": binding["evidence_proposal_id"],
            "graph_binding_id": binding["binding_id"],
            "report_norm_id": report_norm_id,
            "schema_parent_report_norm_id": node["parent_report_norm_id"],
            "schema_projection_id": schema["projection_id"],
            "status": "LIVE_SCHEMA_IDENTITY_JOIN_PROPOSAL_ONLY_AWAITS_NUMERIC",
        }
        result.append(
            {
                **material,
                "proposal_id": "lef12s140v1:schema:" + canonical_json_sha256_v1(material),
            }
        )
    return result


def _context_is_resolved(context: Mapping[str, Any], layout: Sequence[str]) -> bool:
    periods = context.get("period_axis")
    units = context.get("unit_axis")
    count = len(layout)
    period_values = (
        [item.get("resolved_period") for item in periods] if type(periods) is list else []
    )
    period_layout_resolved = (
        bool(
            (count == 2 and len(set(period_values)) == 2)
            or (
                count == 4
                and period_values[0] == period_values[1]
                and period_values[2] == period_values[3]
                and period_values[0] != period_values[2]
            )
        )
        if len(period_values) == count
        else False
    )
    money = [item for item in units or [] if item.get("unit_kind") == "MONEY"]
    return bool(
        context.get("status") == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
        and context.get("metrics")
        == {"column_count": count, "period_column_count": count, "unit_column_count": count}
        and type(periods) is list
        and len(periods) == count
        and [item.get("column_ordinal") for item in periods] == list(range(count))
        and period_layout_resolved
        and all(item.get("evidence_locations") for item in periods)
        and type(units) is list
        and len(units) == count
        and [item.get("column_ordinal") for item in units] == list(range(count))
        and [item.get("unit_kind") for item in units] == list(layout)
        and all(item.get("evidence_locations") for item in units)
        and len({(item.get("currency"), item.get("magnitude_power10")) for item in money}) == 1
        and money
        and money[0].get("currency") is not None
        and type(money[0].get("magnitude_power10")) is int
    )


def _graph_binding(document: Mapping[str, Any]) -> dict[str, Any]:
    evidence = document["evidence_binding"]
    outcome = document["outcome"]
    return {
        "document_graph_result_id": document["result_id"],
        "document_packet_id": evidence["document_packet_id"],
        "outcome_id": evidence["outcome_id"],
        "query_spec_id": evidence["query_spec_id"],
        "receipt_id": evidence["receipt_id"],
        "selected_pages": canonical_clone_v1(outcome["selected_pages"]),
        "snapshot_id": evidence["snapshot_id"],
    }


def _zero_scan(scan: Mapping[str, Any]) -> bool:
    return bool(
        scan["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
        and scan["metrics"]["core_semantic_anchor_hit_count"] == 0
        and not scan["regions"]
        and not scan["near_regions"]
    )


def _column_gate(
    axis: Mapping[str, Any], pages: Sequence[Mapping[str, Any]], spec: Mapping[str, Any]
) -> tuple[dict[str, Any] | None, list[str] | None]:
    resolved = []
    for layout in _COLUMN_LAYOUTS:
        context = column_v1.build_accounting_family_column_context_v1(
            axis,
            pages,
            spec,
            period_semantics="BALANCE_COMPARATIVE",
            expected_lane_unit_kinds=layout,
        )
        column_v1.validate_accounting_family_column_context_replay_v1(
            context,
            axis,
            pages,
            spec,
            period_semantics="BALANCE_COMPARATIVE",
            expected_lane_unit_kinds=layout,
        )
        if _context_is_resolved(context, layout):
            resolved.append((context, list(layout)))
    return resolved[0] if len(resolved) == 1 else (None, None)


def _trial(
    document: Mapping[str, Any],
    sparse_snapshot: Mapping[str, Any],
    sparse_projection: Mapping[str, Any],
    full_snapshot: Any,
    spec: Mapping[str, Any],
    schema: Mapping[str, Any],
) -> dict[str, Any]:
    graph = document["graph"]
    candidate, reason = _graph_candidate(graph)
    if (candidate == "NOT_OBSERVED") is not (full_snapshot is not None):
        raise _error("whole snapshot is required only for one graph absence candidate")
    runs = _selected_runs(sparse_snapshot)
    sparse_replays: list[dict[str, Any]] = []
    whole_scan = None
    whole_graph = None
    whole_binding = None
    row_axis = None
    context = None
    layout = None
    schema_proposals: list[dict[str, Any]] = []
    disposition = "UNRESOLVED"
    terminal = "UNRESOLVED"

    if candidate == "NOT_OBSERVED":
        whole_pages, whole_projection, whole_graph = _full_material(
            full_snapshot, sparse_projection["source_binding"]
        )
        for run in runs:
            sparse_replays.append(
                {"page_binding": run["page_binding"], "scan": _scan(run["joined_pages"], spec)}
            )
        whole_scan = _scan(whole_pages, spec)
        whole_source = whole_projection["source_binding"]
        whole_binding = {
            "projection_id": whole_projection["projection_id"],
            "selected_pages": canonical_clone_v1(whole_source["selected_pages"]),
            "snapshot_id": whole_source["snapshot_id"],
        }
        if (
            all(_zero_scan(item["scan"]) for item in sparse_replays)
            and _zero_scan(whole_scan)
            and not whole_graph["regions"]
            and not whole_graph["near_regions"]
            and not whole_graph["branchless_rescue_challengers"]
            and len(whole_graph["bounded_absences"]) == 1
        ):
            disposition = terminal = "NOT_OBSERVED"
            reason = "SPARSE_AND_WHOLE_GRAPH_TOPOLOGY_ZERO_TARGET_NO_CHALLENGER"
        else:
            reason = "NOT_OBSERVED_REQUIRES_WHOLE_GRAPH_AND_TOPOLOGY_ZERO_REPLAY"
    elif candidate == "EXACT":
        graph_region = graph["regions"][0]
        graph_page = graph_region["branch"]["page_sequence"]
        selected = [
            run
            for run in runs
            if graph_page in {item["physical_page"] for item in run["page_binding"]}
        ]
        if len(selected) == 1:
            run = selected[0]
            sparse_scan = _scan(run["joined_pages"], spec)
            sparse_replays = [{"page_binding": run["page_binding"], "scan": sparse_scan}]
        else:
            sparse_scan = None
        if sparse_scan is not None and sparse_scan["status"] == (
            "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
        ):
            region = sparse_scan["regions"][0]
            anchor = region.get("minimal_unique_anchor")
            graph_local_page = next(
                item["local_page_sequence"]
                for item in run["page_binding"]
                if item["physical_page"] == graph_page
            )
            if (
                region.get("parent_resolution") == "EXPLICIT_PARENT"
                and type(anchor) is dict
                and anchor.get("combination_size") in {2, 3}
                and anchor.get("pair_before_triple_search") is True
                and region["page_sequence"]
                <= graph_local_page
                <= region["cluster_end_page_sequence_inclusive"]
            ):
                pages = run["joined_pages"]
                row_axis = row_v1.build_accounting_family_row_axis_v1(pages, spec)
                row_v1.validate_accounting_family_row_axis_replay_v1(row_axis, pages, spec)
                context, layout = _column_gate(row_axis, pages, spec)
                if (
                    row_axis["topology_scan_id"] == sparse_scan["scan_id"]
                    and row_axis["status"] == "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY"
                    and row_axis["metrics"]["missing_lane_count"] == 0
                    and context is not None
                    and context["row_axis_id"] == row_axis["row_axis_id"]
                ):
                    schema_proposals = _schema_binding_proposals(graph_region, schema)
                    disposition = "EXACT"
                    terminal = "STRUCTURALLY_READY_FOR_NUMERIC"
                    reason = "UNIQUE_GRAPH_TOPOLOGY_ROW_PERIOD_UNIT_AND_SCHEMA_IDENTITY_JOIN"
                else:
                    reason = "ROW_AXIS_OR_UNIQUE_PERIOD_UNIT_GATE_UNRESOLVED"
            else:
                reason = "GRAPH_AND_CONTINUATION_TOPOLOGY_REGION_DO_NOT_ALIGN"
        else:
            reason = "CONTINUATION_TOPOLOGY_IS_NOT_ONE_UNIQUE_PAIR_OR_TRIPLE"

    material = {
        "absence_stage": _absence_placeholder(disposition),
        "column_context": canonical_clone_v1(context),
        "column_layout": canonical_clone_v1(layout),
        "document_id": document["document_id"],
        "document_ordinal": document["document_ordinal"],
        "graph_binding": _graph_binding(document),
        "numeric_stage": canonical_clone_v1(_NUMERIC_PLACEHOLDER),
        "reason": reason,
        "row_axis": canonical_clone_v1(row_axis),
        "schema_binding_proposals": schema_proposals,
        "sparse_topology_replays": canonical_clone_v1(sparse_replays),
        "structural_disposition": disposition,
        "terminal_disposition": terminal,
        "whole_graph": canonical_clone_v1(whole_graph),
        "whole_graph_binding": canonical_clone_v1(whole_binding),
        "whole_topology_scan": canonical_clone_v1(whole_scan),
    }
    return {**material, "trial_id": "lef12s140v1:trial:" + canonical_json_sha256_v1(material)}


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    structural = Counter(trial["structural_disposition"] for trial in trials)
    terminal = Counter(trial["terminal_disposition"] for trial in trials)
    return {
        "document_count": len(trials),
        "schema_identity_join_proposal_count": sum(
            len(trial["schema_binding_proposals"]) for trial in trials
        ),
        "structural_disposition_counts": {
            key: structural.get(key, 0) for key in ("EXACT", "NOT_OBSERVED", "UNRESOLVED")
        },
        "terminal_disposition_counts": {
            key: terminal.get(key, 0)
            for key in ("NOT_OBSERVED", "STRUCTURALLY_READY_FOR_NUMERIC", "UNRESOLVED")
        },
        "whole_document_hydration_count": sum(
            trial["whole_topology_scan"] is not None for trial in trials
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("Family-12 structural terminal result fields drifted")
    trials = value["trials"]
    inputs = value["inputs"]
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or value["state"] != "INCOMPLETE_NUMERIC_STAGE"
        or type(trials) is not list
        or len(trials) != _TARGET_DOCUMENT_COUNT
        or [trial.get("document_ordinal") for trial in trials]
        != list(range(1, _TARGET_DOCUMENT_COUNT + 1))
        or type(inputs) is not dict
        or set(inputs) != _RESULT_INPUT_FIELDS
        or not same_typed_json_v1(value["metrics"], _metrics(trials))
    ):
        raise _error("Family-12 structural terminal denominator or identity drifted")
    schema_v1.validate_loan_enterprise_bounded_schema_projection_v1(
        inputs["bounded_schema_projection"]
    )
    for trial in trials:
        if type(trial) is not dict or set(trial) != _TRIAL_FIELDS:
            raise _error("Family-12 structural terminal trial fields drifted")
        material = canonical_clone_v1(trial)
        trial_id = material.pop("trial_id")
        if trial_id != "lef12s140v1:trial:" + canonical_json_sha256_v1(material):
            raise _error("Family-12 structural terminal trial identity drifted")
        structural = trial["structural_disposition"]
        terminal = trial["terminal_disposition"]
        if (
            structural not in {"EXACT", "NOT_OBSERVED", "UNRESOLVED"}
            or terminal not in {"NOT_OBSERVED", "STRUCTURALLY_READY_FOR_NUMERIC", "UNRESOLVED"}
            or not same_typed_json_v1(trial["numeric_stage"], _NUMERIC_PLACEHOLDER)
            or not same_typed_json_v1(trial["absence_stage"], _absence_placeholder(structural))
            or (structural == "EXACT") is not (terminal == "STRUCTURALLY_READY_FOR_NUMERIC")
            or (structural == "NOT_OBSERVED") is not (terminal == "NOT_OBSERVED")
            or (structural == "UNRESOLVED") is not (terminal == "UNRESOLVED")
            or (structural == "EXACT" and not trial["schema_binding_proposals"])
            or (structural != "EXACT" and trial["schema_binding_proposals"])
            or (structural == "NOT_OBSERVED" and trial["whole_topology_scan"] is None)
            or (structural == "NOT_OBSERVED" and trial["whole_graph"] is None)
            or type(trial["sparse_topology_replays"]) is not list
            or any(
                type(replay) is not dict
                or set(replay) != {"page_binding", "scan"}
                or type(replay["page_binding"]) is not list
                for replay in trial["sparse_topology_replays"]
            )
            or (
                structural == "EXACT"
                and (
                    trial["row_axis"] is None
                    or trial["column_context"] is None
                    or trial["column_layout"] not in _COLUMN_LAYOUTS
                    or len(trial["sparse_topology_replays"]) != 1
                    or trial["whole_graph"] is not None
                )
            )
        ):
            raise _error("Family-12 structural terminal authority boundary drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "lef12s140v1:sweep:" + canonical_json_sha256_v1(material):
        raise _error("Family-12 structural terminal content identity drifted")
    return canonical_clone_v1(value)


def build_family_first_loan_enterprise_140_filing_schema_sweep_v1(
    structural_input: Any,
    project_root: Path,
) -> dict[str, Any]:
    if not isinstance(project_root, Path):
        raise _error("Family-12 project root must be one pathlib Path")
    if type(structural_input) is not dict or set(structural_input) != _INPUT_FIELDS:
        raise _error("Family-12 structural input fields drifted")
    if structural_input["format_version"] != INPUT_FORMAT_VERSION:
        raise _error("Family-12 structural input version drifted")
    batch = _graph_batch(structural_input["authenticated_graph_batch"])
    packets = structural_input["structural_packets"]
    if type(packets) is not list or len(packets) != _TARGET_DOCUMENT_COUNT:
        raise _error("Family-12 structural packet denominator must be exactly 140")
    spec = build_loan_enterprise_family12_topology_spec_v1()
    schema = schema_v1.build_live_loan_enterprise_bounded_schema_projection_v1(
        project_root.resolve()
    )
    schema_v1.validate_loan_enterprise_bounded_schema_projection_v1(schema)
    trials = []
    for ordinal, (packet, expected_document) in enumerate(
        zip(packets, batch["documents"], strict=True), 1
    ):
        if type(packet) is not dict or set(packet) != _PACKET_FIELDS:
            raise _error("Family-12 structural packet fields drifted")
        document, sparse_projection = _graph_document(
            packet["graph_document"],
            expected=expected_document,
            ordinal=ordinal,
            batch_binding=batch["evidence_binding"],
            sparse_snapshot=packet["sparse_snapshot"],
        )
        trials.append(
            _trial(
                document,
                packet["sparse_snapshot"],
                sparse_projection,
                packet["full_snapshot"],
                spec,
                schema,
            )
        )
    binding = batch["evidence_binding"]
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "inputs": {
            "bounded_schema_projection": schema,
            "graph_batch_result_id": batch["result_id"],
            "manifest_id": binding["manifest_id"],
            "query_spec_id": binding["query_spec_id"],
            "receipt_id": binding["receipt_id"],
            "topology_spec_sha256": canonical_json_sha256_v1(spec),
        },
        "metrics": _metrics(trials),
        "state": "INCOMPLETE_NUMERIC_STAGE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "lef12s140v1:sweep:" + canonical_json_sha256_v1(material)}
    )


def validate_family_first_loan_enterprise_140_filing_schema_sweep_v1(
    value: Any,
) -> dict[str, Any]:
    """Validate only the non-authoritative structural shape and content IDs."""

    return _validate_result(value)


def validate_family_first_loan_enterprise_140_filing_schema_sweep_replay_v1(
    value: Any,
    structural_input: Any,
    project_root: Path,
) -> dict[str, Any]:
    """Rebuild from caller-authenticated inputs before accepting a persisted result."""

    persisted = _validate_result(value)
    rebuilt = build_family_first_loan_enterprise_140_filing_schema_sweep_v1(
        structural_input, project_root
    )
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("Family-12 structural terminal does not replay exactly")
    return persisted
