#!/usr/bin/env python3
"""Build the fail-closed Family-12 structural and flat-table numeric terminal."""

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

from bctc_ai.evaluation import accounting_additive_table_closure_v1 as additive_v1  # noqa: E402
from bctc_ai.evaluation import accounting_family_column_context_v1 as column_v1  # noqa: E402
from bctc_ai.evaluation import accounting_family_row_axis_v1 as row_v1  # noqa: E402
from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1  # noqa: E402
from bctc_ai.evaluation import (  # noqa: E402
    authenticated_semantic_region_snapshot_v1 as snapshot_v1,
)
from bctc_ai.evaluation import loan_enterprise_family12_graph_v1 as graph_v1  # noqa: E402
from bctc_ai.evaluation.family_first_numeric_cell_evidence_v1 import (  # noqa: E402
    parse_visible_financial_numeric_token_v1,
)
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
    "SCHEMA_JOIN_EXACT_PPOCRV6_VIETOCR_TYPED_CELL_AGREEMENT_AND_UNIQUE_VISIBLE_"
    "FLAT_ADDITIVE_TOTAL_MONEY_MAPPING_ONLY_PERCENT_EVIDENCE_RETAINED_WITH_DASH_"
    "MISSING_SOURCE_GROUP_AND_NONADDITIVE_6058_CONFLICTS_FAIL_CLOSED_NO_CORPUS_"
    "ABSENCE_BACKSOLVE_CANONICALIZATION_OR_EXPORT_AUTHORITY"
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
    "graph_region numeric_stage reason row_axis schema_binding_proposals sparse_topology_replays "
    "structural_disposition terminal_disposition trial_id whole_graph whole_graph_binding "
    "whole_topology_scan".split()
)
_NUMERIC_STAGE_FIELDS = {
    "accounting_closure",
    "mapped_rows",
    "numeric_cells",
    "status",
    "unresolved_reasons",
}
_NUMERIC_CELL_FIELDS = set(
    "column_ordinal emission_eligible normalized_number period ppocrv6_parsed_token "
    "ppocrv6_surface sample_id source_role unit verification_status vietocr_parsed_token "
    "vietocr_surface".split()
)
_MAPPED_ROW_FIELDS = set(
    "graph_binding_id money_cells report_norm_id schema_parent_report_norm_id "
    "schema_proposal_id source_role status".split()
)
_MAPPED_CELL_FIELDS = set(
    "column_ordinal normalized_number period sample_id unit value_status".split()
)
_TYPED_NUMBER_FIELDS = {
    "coefficient",
    "explicit_sign_kind",
    "negative_parentheses",
    "percentage_mark_present",
    "scale",
    "sign",
}
_UNIT_FIELDS = {"currency", "magnitude_power10", "unit_kind"}
_SCHEMA_PROPOSAL_FIELDS = set(
    "evidence_proposal_id graph_binding_id proposal_id report_norm_id "
    "schema_parent_report_norm_id schema_projection_id status".split()
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
    "exact_flat_table_mapping_authority_bounded_to_family12": True,
    "exact_flat_table_numeric_authority_bounded_to_family12": True,
    "mapping_authority": False,
    "numeric_authority": False,
    "percent_companion_mapping_authority": False,
    "public_exact_replay_required": True,
    "schema_join_is_mapping_authority": False,
    "snapshot_self_hash_is_authentication_authority": False,
    "source_group_or_nonadditive_6058_mapping_without_nested_closure": False,
    "structural_exact_is_complete_family_mapping": False,
    "textual_dash_without_authenticated_pixel_evidence_is_zero": False,
}
_NUMERIC_PLACEHOLDER = {
    "accounting_closure": None,
    "mapped_rows": [],
    "numeric_cells": [],
    "status": "NOT_RUN_REQUIRED_FOR_FAMILY12_COMPLETION",
    "unresolved_reasons": [],
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


def _typed_number(parsed: Mapping[str, Any]) -> dict[str, Any] | None:
    if parsed.get("classification") != "SIGNED_NUMBER":
        return None
    token = parsed.get("normalized_token")
    if type(token) is not str:
        return None
    stripped = token.strip()
    if stripped.startswith("("):
        sign_kind = "PARENTHESES"
    elif stripped.startswith("+"):
        sign_kind = "EXPLICIT_PLUS"
    elif stripped.startswith(("-", "−")):
        sign_kind = "EXPLICIT_MINUS"
    else:
        sign_kind = "UNSIGNED"
    return {
        "coefficient": parsed.get("coefficient"),
        "explicit_sign_kind": sign_kind,
        "negative_parentheses": parsed.get("negative_parentheses"),
        "percentage_mark_present": parsed.get("percentage_mark_present"),
        "scale": parsed.get("scale"),
        "sign": parsed.get("sign"),
    }


def _numeric_cells(
    row_axis: Mapping[str, Any],
    context: Mapping[str, Any],
    closure: Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    lines = {
        line["sample_id"]: line
        for page in pages
        for line in page["lines"]
        if type(line) is dict and type(line.get("sample_id")) is str
    }
    periods = {item["column_ordinal"]: item for item in context["period_axis"]}
    units = {item["column_ordinal"]: item for item in context["unit_axis"]}
    sources = [(row["role"], value) for row in row_axis["rows"] for value in row["values"]]
    exact_totals = closure.get("exact_total_candidates")
    if type(exact_totals) is list and len(exact_totals) == 1:
        total_ids = set(exact_totals[0]["sample_ids"])
        sources.extend(
            (None, value)
            for row in row_axis["trailing_value_rows"]
            for value in row["values"]
            if value["sample_id"] in total_ids
        )
    cells = []
    reasons = []
    seen: set[str] = set()
    for role, value in sources:
        sample_id = value["sample_id"]
        column = value["column_ordinal"]
        line = lines.get(sample_id)
        if sample_id in seen:
            reasons.append("NUMERIC_SOURCE_CELL_REUSED:" + sample_id)
            continue
        seen.add(sample_id)
        if line is None or column not in periods or column not in units:
            reasons.append("NUMERIC_SOURCE_OR_CONTEXT_BINDING_ABSENT:" + sample_id)
            continue
        pp_surface = line["numeric_recognition"]["raw_prediction"]
        viet_surface = line["vietocr_text"]
        pp = parse_visible_financial_numeric_token_v1(pp_surface)
        viet = parse_visible_financial_numeric_token_v1(viet_surface)
        if value["raw_prediction"] != pp_surface or not same_typed_json_v1(
            value["parsed_token"], pp
        ):
            raise _error("Family-12 row-axis numeric source binding drifted")
        pp_number = _typed_number(pp)
        viet_number = _typed_number(viet)
        if pp.get("classification") == "DASH_ZERO" or viet.get("classification") == "DASH_ZERO":
            status = "UNRESOLVED_AUTHENTICATED_PIXEL_DASH_EVIDENCE_REQUIRED"
            number = None
            reasons.append("PIXEL_DASH_EVIDENCE_REQUIRED:" + sample_id)
        elif pp_number is None or not same_typed_json_v1(pp_number, viet_number):
            status = "UNRESOLVED_PPOCRV6_VIETOCR_TYPED_TOKEN_CONFLICT"
            number = None
            reasons.append("PPOCRV6_VIETOCR_TYPED_TOKEN_CONFLICT:" + sample_id)
        elif units[column]["unit_kind"] == "MONEY" and pp_number["percentage_mark_present"]:
            status = "UNRESOLVED_MONEY_LANE_HAS_PERCENTAGE_TOKEN"
            number = None
            reasons.append("MONEY_LANE_PERCENTAGE_TOKEN_CONFLICT:" + sample_id)
        else:
            status = "EXACT_TYPED_PPOCRV6_VIETOCR_AGREEMENT"
            number = pp_number
        cells.append(
            {
                "column_ordinal": column,
                "emission_eligible": role is not None and units[column]["unit_kind"] == "MONEY",
                "normalized_number": canonical_clone_v1(number),
                "period": periods[column]["resolved_period"],
                "ppocrv6_parsed_token": canonical_clone_v1(pp),
                "ppocrv6_surface": pp_surface,
                "sample_id": sample_id,
                "source_role": role,
                "unit": {
                    key: units[column][key]
                    for key in ("currency", "magnitude_power10", "unit_kind")
                },
                "verification_status": status,
                "vietocr_parsed_token": canonical_clone_v1(viet),
                "vietocr_surface": viet_surface,
            }
        )
    return cells, list(dict.fromkeys(reasons))


def _label_source_locations(
    row: Mapping[str, Any], page_binding: Sequence[Mapping[str, Any]]
) -> set[tuple[int, int]]:
    match = row["label_match"]
    physical = {item["local_page_sequence"]: item["physical_page"] for item in page_binding}.get(
        match["page_sequence"]
    )
    indices = match.get("source_line_indices")
    if indices is None:
        indices = list(range(match["source_line_index"], match["end_source_line_index"] + 1))
    return {(physical, index) for index in indices} if physical is not None else set()


def _mapped_rows(
    graph_region: Mapping[str, Any],
    schema_proposals: Sequence[Mapping[str, Any]],
    row_axis: Mapping[str, Any],
    page_binding: Sequence[Mapping[str, Any]],
    cells: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    graph_rows = {row["proposal_id"]: row for row in graph_region["row_proposals"]}
    rows_by_locations: dict[frozenset[tuple[int, int]], list[Mapping[str, Any]]] = {}
    for row in row_axis["rows"]:
        locations = frozenset(_label_source_locations(row, page_binding))
        rows_by_locations.setdefault(locations, []).append(row)
    cell_by_id = {cell["sample_id"]: cell for cell in cells}
    mapped = []
    reasons = []
    for proposal in schema_proposals:
        binding = next(
            (
                item
                for item in graph_region["binding_proposals"]
                if item["binding_id"] == proposal["graph_binding_id"]
            ),
            None,
        )
        graph_row = graph_rows.get(binding["evidence_proposal_id"]) if binding is not None else None
        locations = (
            frozenset(
                (item["page_sequence"], item["source_line_index"]) for item in graph_row["evidence"]
            )
            if graph_row is not None
            else frozenset()
        )
        candidates = rows_by_locations.get(locations, [])
        report_norm_id = proposal["report_norm_id"]
        if report_norm_id == 6058:
            reasons.append("NESTED_SOURCE_GROUP_CLOSURE_REQUIRED_FOR_REPORT_NORM_ID_6058")
            continue
        if (
            binding is None
            or graph_row is None
            or graph_row.get("report_norm_id") != report_norm_id
            or graph_row.get("schema_parent_report_norm_id")
            != proposal["schema_parent_report_norm_id"]
            or len(candidates) != 1
        ):
            reasons.append("GRAPH_ROW_TO_ROW_AXIS_SOURCE_BINDING_UNRESOLVED:" + str(report_norm_id))
            continue
        row = candidates[0]
        money = [
            cell_by_id.get(value["sample_id"])
            for value in row["values"]
            if cell_by_id.get(value["sample_id"], {}).get("unit", {}).get("unit_kind") == "MONEY"
        ]
        if (
            not money
            or any(cell is None or cell["normalized_number"] is None for cell in money)
            or row["missing_column_ordinals"]
        ):
            reasons.append("MAPPED_MONEY_ROW_NUMERIC_AXIS_UNRESOLVED:" + str(report_norm_id))
            continue
        mapped.append(
            {
                "graph_binding_id": binding["binding_id"],
                "money_cells": [
                    {
                        "column_ordinal": cell["column_ordinal"],
                        "normalized_number": canonical_clone_v1(cell["normalized_number"]),
                        "period": cell["period"],
                        "sample_id": cell["sample_id"],
                        "unit": canonical_clone_v1(cell["unit"]),
                        "value_status": (
                            "OBSERVED_ZERO"
                            if cell["normalized_number"]["coefficient"] == 0
                            else "OBSERVED_VALUE"
                        ),
                    }
                    for cell in money
                    if cell is not None
                ],
                "report_norm_id": report_norm_id,
                "schema_parent_report_norm_id": proposal["schema_parent_report_norm_id"],
                "schema_proposal_id": proposal["proposal_id"],
                "source_role": row["role"],
                "status": "EXACT_FLAT_TABLE_MONEY_MAPPING",
            }
        )
    return mapped, list(dict.fromkeys(reasons))


def _flat_population_reasons(
    graph_region: Mapping[str, Any],
    schema_proposals: Sequence[Mapping[str, Any]],
    row_axis: Mapping[str, Any],
    page_binding: Sequence[Mapping[str, Any]],
) -> list[str]:
    rows = graph_region.get("row_proposals")
    bindings = graph_region.get("binding_proposals")
    axis_rows = row_axis.get("rows")
    if type(rows) is not list or type(bindings) is not list or type(axis_rows) is not list:
        return ["NESTED_OR_SOURCE_ONLY_ROW_REQUIRES_DECLARED_CLOSURE"]

    graph_by_id = {
        row.get("proposal_id"): row
        for row in rows
        if type(row) is dict and type(row.get("proposal_id")) is str
    }
    binding_by_evidence = {
        binding.get("evidence_proposal_id"): binding
        for binding in bindings
        if type(binding) is dict and type(binding.get("evidence_proposal_id")) is str
    }
    schema_by_evidence = {
        proposal.get("evidence_proposal_id"): proposal
        for proposal in schema_proposals
        if type(proposal) is dict and type(proposal.get("evidence_proposal_id")) is str
    }
    graph_ids = [row.get("proposal_id") for row in rows if type(row) is dict]
    binding_ids = [
        binding.get("evidence_proposal_id") for binding in bindings if type(binding) is dict
    ]
    schema_ids = [
        proposal.get("evidence_proposal_id")
        for proposal in schema_proposals
        if type(proposal) is dict
    ]
    axis_locations = [frozenset(_label_source_locations(row, page_binding)) for row in axis_rows]
    graph_locations = [
        frozenset(
            (item.get("page_sequence"), item.get("source_line_index"))
            for item in row.get("evidence", [])
            if type(item) is dict
        )
        for row in rows
    ]
    invalid = (
        any(row.get("role_kind") != "ADDITIVE_CHILD" for row in axis_rows)
        or len(axis_rows) != len(rows)
        or len(rows) != len(schema_proposals)
        or not all(axis_locations)
        or not all(graph_locations)
        or len(set(axis_locations)) != len(axis_locations)
        or len(set(graph_locations)) != len(graph_locations)
        or set(axis_locations) != set(graph_locations)
        or any(
            type(item.get("page_sequence")) is not int
            or type(item.get("source_line_index")) is not int
            for row in rows
            for item in row.get("evidence", [])
            if type(item) is dict
        )
        or len(graph_by_id) != len(rows)
        or len(binding_by_evidence) != len(bindings)
        or len(schema_by_evidence) != len(schema_proposals)
        or len(set(graph_ids)) != len(graph_ids)
        or len(set(binding_ids)) != len(binding_ids)
        or len(set(schema_ids)) != len(schema_ids)
        or len({binding.get("binding_id") for binding in bindings}) != len(bindings)
        or len({proposal.get("proposal_id") for proposal in schema_proposals})
        != len(schema_proposals)
        or {proposal.get("graph_binding_id") for proposal in schema_proposals}
        != {binding.get("binding_id") for binding in bindings}
        or set(graph_ids) != set(binding_ids)
        or set(graph_ids) != set(schema_ids)
        or any(
            type(row.get("report_norm_id")) is not int
            or type(row.get("schema_parent_report_norm_id")) is not int
            or row.get("status") != "SCHEMA_ROW_TEXT_AND_GEOMETRY_PROPOSAL_REQUIRES_REPLAY"
            or row.get("report_norm_id") == 6058
            for row in rows
        )
    )
    for evidence_id, row in graph_by_id.items():
        binding = binding_by_evidence.get(evidence_id)
        proposal = schema_by_evidence.get(evidence_id)
        invalid = invalid or (
            binding is None
            or proposal is None
            or binding.get("status") != "UNIQUE_SCHEMA_BINDING_PROPOSAL_NO_MAPPING_AUTHORITY"
            or proposal.get("status") != "LIVE_SCHEMA_IDENTITY_JOIN_PROPOSAL_ONLY_AWAITS_NUMERIC"
            or proposal.get("graph_binding_id") != binding.get("binding_id")
            or proposal.get("report_norm_id") != row.get("report_norm_id")
            or proposal.get("schema_parent_report_norm_id")
            != row.get("schema_parent_report_norm_id")
            or binding.get("report_norm_id") != row.get("report_norm_id")
            or binding.get("schema_parent_report_norm_id")
            != row.get("schema_parent_report_norm_id")
        )
    return ["NESTED_OR_SOURCE_ONLY_ROW_REQUIRES_DECLARED_CLOSURE"] if invalid else []


def _numeric_gate(
    row_axis: Mapping[str, Any],
    context: Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any],
    graph_region: Mapping[str, Any],
    schema_proposals: Sequence[Mapping[str, Any]],
    page_binding: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    reasons = _flat_population_reasons(graph_region, schema_proposals, row_axis, page_binding)
    try:
        closure = additive_v1.build_accounting_additive_table_closure_v1(row_axis, pages, spec)
    except ValueError as exc:
        closure = None
        reasons.append("ADDITIVE_CLOSURE_REPLAY_ERROR:" + type(exc).__name__)
    if closure is not None and closure["status"] != "CORROBORATED_EXACT_UNIQUE_TRAILING_TOTAL":
        reasons.extend("ADDITIVE_CLOSURE:" + item for item in closure["unresolved_reasons"])
    if closure is not None and closure.get("row_axis_id") != row_axis.get("row_axis_id"):
        reasons.append("ADDITIVE_CLOSURE_ROW_AXIS_BINDING_DRIFT")
    cells, cell_reasons = _numeric_cells(row_axis, context, closure or {}, pages)
    mapped, mapping_reasons = _mapped_rows(
        graph_region, schema_proposals, row_axis, page_binding, cells
    )
    reasons.extend(cell_reasons)
    reasons.extend(mapping_reasons)
    if row_axis["metrics"]["missing_lane_count"]:
        reasons.append("VISIBLE_ROW_LANES_MISSING_AUTHENTICATED_PIXEL_OR_NUMERIC_BINDING")
    if len(mapped) != len(schema_proposals):
        reasons.append("SCHEMA_BINDING_PROPOSAL_DENOMINATOR_NOT_EXACTLY_MAPPED")
    reasons = list(dict.fromkeys(reasons))
    return {
        "accounting_closure": canonical_clone_v1(closure),
        "mapped_rows": [] if reasons else mapped,
        "numeric_cells": cells,
        "status": (
            "EXACT_FLAT_TABLE_NUMERIC_ACCOUNTING_AND_SCHEMA_BOUND"
            if not reasons and mapped
            else "UNRESOLVED_NUMERIC_ACCOUNTING_OR_SCHEMA_GATES"
        ),
        "unresolved_reasons": reasons,
    }


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
    graph_region_output = None
    numeric_stage = canonical_clone_v1(_NUMERIC_PLACEHOLDER)
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
                    graph_region_output = canonical_clone_v1(graph_region)
                    numeric_stage = _numeric_gate(
                        row_axis,
                        context,
                        pages,
                        spec,
                        graph_region,
                        schema_proposals,
                        run["page_binding"],
                    )
                    if numeric_stage["status"] == (
                        "EXACT_FLAT_TABLE_NUMERIC_ACCOUNTING_AND_SCHEMA_BOUND"
                    ):
                        terminal = "EXACT_FLAT_TABLE"
                        reason = (
                            "UNIQUE_GRAPH_TOPOLOGY_ROW_PERIOD_UNIT_TYPED_NUMERIC_"
                            "VISIBLE_ADDITIVE_CLOSURE_AND_SCHEMA_BINDING"
                        )
                    else:
                        terminal = "UNRESOLVED"
                        reason = "NUMERIC_ACCOUNTING_OR_SCHEMA_GATE_UNRESOLVED"
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
        "graph_region": graph_region_output,
        "numeric_stage": canonical_clone_v1(numeric_stage),
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
            key: terminal.get(key, 0) for key in ("EXACT_FLAT_TABLE", "NOT_OBSERVED", "UNRESOLVED")
        },
        "exact_flat_table_mapped_money_cell_count": sum(
            len(row["money_cells"])
            for trial in trials
            for row in trial["numeric_stage"]["mapped_rows"]
        ),
        "exact_flat_table_mapped_row_count": sum(
            len(trial["numeric_stage"]["mapped_rows"]) for trial in trials
        ),
        "whole_document_hydration_count": sum(
            trial["whole_topology_scan"] is not None for trial in trials
        ),
    }


def _valid_typed_number(value: Any) -> bool:
    return bool(
        type(value) is dict
        and set(value) == _TYPED_NUMBER_FIELDS
        and type(value["coefficient"]) is int
        and type(value["scale"]) is int
        and value["scale"] >= 0
        and type(value["sign"]) is int
        and value["sign"] in {-1, 0, 1}
        and type(value["negative_parentheses"]) is bool
        and type(value["percentage_mark_present"]) is bool
        and value["explicit_sign_kind"]
        in {"UNSIGNED", "EXPLICIT_PLUS", "EXPLICIT_MINUS", "PARENTHESES"}
    )


def _valid_unit(value: Any) -> bool:
    if type(value) is not dict or set(value) != _UNIT_FIELDS:
        return False
    if value["unit_kind"] == "MONEY":
        return bool(
            type(value["currency"]) is str
            and value["currency"]
            and type(value["magnitude_power10"]) is int
            and value["magnitude_power10"] >= 0
        )
    return bool(
        value["unit_kind"] == "PERCENT"
        and value["currency"] is None
        and value["magnitude_power10"] is None
    )


def _valid_numeric_stage(value: Any) -> bool:
    if (
        type(value) is not dict
        or set(value) != _NUMERIC_STAGE_FIELDS
        or value["status"]
        not in {
            "EXACT_FLAT_TABLE_NUMERIC_ACCOUNTING_AND_SCHEMA_BOUND",
            "NOT_RUN_REQUIRED_FOR_FAMILY12_COMPLETION",
            "UNRESOLVED_NUMERIC_ACCOUNTING_OR_SCHEMA_GATES",
        }
        or type(value["mapped_rows"]) is not list
        or type(value["numeric_cells"]) is not list
        or type(value["unresolved_reasons"]) is not list
        or any(type(item) is not str or not item for item in value["unresolved_reasons"])
    ):
        return False
    exact = value["status"] == "EXACT_FLAT_TABLE_NUMERIC_ACCOUNTING_AND_SCHEMA_BOUND"
    if exact:
        try:
            closure = additive_v1._validate_result(value["accounting_closure"])
        except ValueError:
            return False
        if closure["status"] != "CORROBORATED_EXACT_UNIQUE_TRAILING_TOTAL":
            return False
    cells_by_id = {}
    for cell in value["numeric_cells"]:
        if type(cell) is not dict or set(cell) != _NUMERIC_CELL_FIELDS:
            return False
        unit = cell["unit"]
        sample_id = cell["sample_id"]
        source_role = cell["source_role"]
        normalized = cell["normalized_number"]
        verification = cell["verification_status"]
        if (
            not _valid_unit(unit)
            or type(sample_id) is not str
            or not sample_id
            or sample_id in cells_by_id
            or type(cell["column_ordinal"]) is not int
            or cell["column_ordinal"] < 0
            or type(cell["period"]) is not str
            or not cell["period"]
            or (source_role is not None and (type(source_role) is not str or not source_role))
            or type(cell["emission_eligible"]) is not bool
            or cell["emission_eligible"]
            is not (source_role is not None and unit["unit_kind"] == "MONEY")
            or type(cell["ppocrv6_surface"]) is not str
            or type(cell["vietocr_surface"]) is not str
            or (normalized is not None and not _valid_typed_number(normalized))
            or verification
            not in {
                "EXACT_TYPED_PPOCRV6_VIETOCR_AGREEMENT",
                "UNRESOLVED_AUTHENTICATED_PIXEL_DASH_EVIDENCE_REQUIRED",
                "UNRESOLVED_MONEY_LANE_HAS_PERCENTAGE_TOKEN",
                "UNRESOLVED_PPOCRV6_VIETOCR_TYPED_TOKEN_CONFLICT",
            }
            or not same_typed_json_v1(
                cell["ppocrv6_parsed_token"],
                parse_visible_financial_numeric_token_v1(cell["ppocrv6_surface"]),
            )
            or not same_typed_json_v1(
                cell["vietocr_parsed_token"],
                parse_visible_financial_numeric_token_v1(cell["vietocr_surface"]),
            )
            or (
                verification == "EXACT_TYPED_PPOCRV6_VIETOCR_AGREEMENT"
                and (
                    not same_typed_json_v1(normalized, _typed_number(cell["ppocrv6_parsed_token"]))
                    or not same_typed_json_v1(
                        normalized, _typed_number(cell["vietocr_parsed_token"])
                    )
                )
            )
            or (verification != "EXACT_TYPED_PPOCRV6_VIETOCR_AGREEMENT" and normalized is not None)
            or (exact and verification != "EXACT_TYPED_PPOCRV6_VIETOCR_AGREEMENT")
        ):
            return False
        cells_by_id[sample_id] = cell
    for row in value["mapped_rows"]:
        if (
            type(row) is not dict
            or set(row) != _MAPPED_ROW_FIELDS
            or type(row["report_norm_id"]) is not int
            or row["report_norm_id"] == 6058
            or type(row["schema_parent_report_norm_id"]) is not int
            or type(row["graph_binding_id"]) is not str
            or not row["graph_binding_id"]
            or type(row["schema_proposal_id"]) is not str
            or not row["schema_proposal_id"]
            or type(row["source_role"]) is not str
            or not row["source_role"]
            or row["status"] != "EXACT_FLAT_TABLE_MONEY_MAPPING"
            or type(row["money_cells"]) is not list
            or not row["money_cells"]
        ):
            return False
        for mapped_cell in row["money_cells"]:
            if (
                type(mapped_cell) is not dict
                or set(mapped_cell) != _MAPPED_CELL_FIELDS
                or not _valid_typed_number(mapped_cell["normalized_number"])
                or not _valid_unit(mapped_cell["unit"])
                or mapped_cell["unit"]["unit_kind"] != "MONEY"
                or mapped_cell["value_status"]
                != (
                    "OBSERVED_ZERO"
                    if mapped_cell["normalized_number"]["coefficient"] == 0
                    else "OBSERVED_VALUE"
                )
            ):
                return False
            source = cells_by_id.get(mapped_cell["sample_id"])
            if (
                source is None
                or not source["emission_eligible"]
                or not same_typed_json_v1(
                    {
                        key: source[key]
                        for key in (
                            "column_ordinal",
                            "normalized_number",
                            "period",
                            "sample_id",
                            "unit",
                        )
                    },
                    {
                        key: mapped_cell[key]
                        for key in (
                            "column_ordinal",
                            "normalized_number",
                            "period",
                            "sample_id",
                            "unit",
                        )
                    },
                )
            ):
                return False
    unresolved = value["status"] == "UNRESOLVED_NUMERIC_ACCOUNTING_OR_SCHEMA_GATES"
    return bool(
        (not exact or (value["accounting_closure"] is not None and value["mapped_rows"]))
        and (not exact or not value["unresolved_reasons"])
        and (not unresolved or (value["unresolved_reasons"] and not value["mapped_rows"]))
        and (
            value["status"] != "NOT_RUN_REQUIRED_FOR_FAMILY12_COMPLETION"
            or same_typed_json_v1(value, _NUMERIC_PLACEHOLDER)
        )
    )


def _valid_schema_proposal(value: Any, projection_id: Any) -> bool:
    if (
        type(value) is not dict
        or set(value) != _SCHEMA_PROPOSAL_FIELDS
        or value["schema_projection_id"] != projection_id
        or type(value["report_norm_id"]) is not int
        or type(value["schema_parent_report_norm_id"]) is not int
        or value["status"] != "LIVE_SCHEMA_IDENTITY_JOIN_PROPOSAL_ONLY_AWAITS_NUMERIC"
    ):
        return False
    material = {key: item for key, item in value.items() if key != "proposal_id"}
    return value["proposal_id"] == "lef12s140v1:schema:" + canonical_json_sha256_v1(material)


def _valid_exact_trial_crosslinks(trial: Mapping[str, Any], projection_id: Any) -> bool:
    axis = trial["row_axis"]
    context = trial["column_context"]
    region = trial["graph_region"]
    stage = trial["numeric_stage"]
    proposals = trial["schema_binding_proposals"]
    replays = trial.get("sparse_topology_replays")
    page_binding = (
        replays[0].get("page_binding", [])
        if type(replays) is list and len(replays) == 1 and type(replays[0]) is dict
        else []
    )
    if (
        type(axis) is not dict
        or type(context) is not dict
        or type(region) is not dict
        or stage["accounting_closure"].get("row_axis_id") != axis.get("row_axis_id")
        or context.get("row_axis_id") != axis.get("row_axis_id")
        or _flat_population_reasons(region, proposals, axis, page_binding)
        or any(not _valid_schema_proposal(item, projection_id) for item in proposals)
    ):
        return False
    periods = {item.get("column_ordinal"): item for item in context.get("period_axis", [])}
    units = {item.get("column_ordinal"): item for item in context.get("unit_axis", [])}
    bindings = {item.get("binding_id"): item for item in region.get("binding_proposals", [])}
    rows = {item.get("proposal_id"): item for item in region.get("row_proposals", [])}
    schema = {item["proposal_id"]: item for item in proposals}
    mapped = {item["schema_proposal_id"]: item for item in stage["mapped_rows"]}
    if (
        len(periods) != len(context["period_axis"])
        or len(units) != len(context["unit_axis"])
        or len(bindings) != len(region["binding_proposals"])
        or len(rows) != len(region["row_proposals"])
        or len(schema) != len(proposals)
        or len(mapped) != len(stage["mapped_rows"])
        or set(mapped) != set(schema)
    ):
        return False
    for cell in stage["numeric_cells"]:
        period = periods.get(cell["column_ordinal"])
        unit = units.get(cell["column_ordinal"])
        if (
            period is None
            or unit is None
            or cell["period"] != period.get("resolved_period")
            or not same_typed_json_v1(cell["unit"], {key: unit.get(key) for key in _UNIT_FIELDS})
        ):
            return False
    for proposal_id, mapped_row in mapped.items():
        proposal = schema[proposal_id]
        binding = bindings.get(proposal["graph_binding_id"])
        graph_row = rows.get(proposal["evidence_proposal_id"])
        expected = (
            proposal["report_norm_id"],
            proposal["schema_parent_report_norm_id"],
        )
        if (
            binding is None
            or graph_row is None
            or mapped_row["graph_binding_id"] != proposal["graph_binding_id"]
            or (mapped_row["report_norm_id"], mapped_row["schema_parent_report_norm_id"])
            != expected
            or (binding.get("report_norm_id"), binding.get("schema_parent_report_norm_id"))
            != expected
            or (graph_row.get("report_norm_id"), graph_row.get("schema_parent_report_norm_id"))
            != expected
            or binding.get("evidence_proposal_id") != proposal["evidence_proposal_id"]
        ):
            return False
    return True


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
        or value["state"] != "INCOMPLETE_PIXEL_AND_SOURCE_GROUP_STAGE"
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
    schema_projection_id = inputs["bounded_schema_projection"]["projection_id"]
    schema_pairs = {
        (item["report_norm_id"], item["parent_report_norm_id"])
        for item in inputs["bounded_schema_projection"]["mapped_leaves"]
    }
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
            or terminal not in {"EXACT_FLAT_TABLE", "NOT_OBSERVED", "UNRESOLVED"}
            or not _valid_numeric_stage(trial["numeric_stage"])
            or any(
                not _valid_schema_proposal(item, schema_projection_id)
                or (item["report_norm_id"], item["schema_parent_report_norm_id"])
                not in schema_pairs
                for item in trial["schema_binding_proposals"]
            )
            or not same_typed_json_v1(trial["absence_stage"], _absence_placeholder(structural))
            or (structural == "NOT_OBSERVED") is not (terminal == "NOT_OBSERVED")
            or (terminal == "EXACT_FLAT_TABLE")
            is not (
                structural == "EXACT"
                and trial["numeric_stage"]["status"]
                == "EXACT_FLAT_TABLE_NUMERIC_ACCOUNTING_AND_SCHEMA_BOUND"
            )
            or (
                structural != "EXACT"
                and not same_typed_json_v1(trial["numeric_stage"], _NUMERIC_PLACEHOLDER)
            )
            or (
                structural == "EXACT"
                and terminal == "UNRESOLVED"
                and trial["numeric_stage"]["status"]
                != "UNRESOLVED_NUMERIC_ACCOUNTING_OR_SCHEMA_GATES"
            )
            or (
                terminal == "EXACT_FLAT_TABLE"
                and not _valid_exact_trial_crosslinks(trial, schema_projection_id)
            )
            or (structural == "EXACT" and not trial["schema_binding_proposals"])
            or (structural != "EXACT" and trial["schema_binding_proposals"])
            or (structural == "EXACT") is not (type(trial["graph_region"]) is dict)
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
        "state": "INCOMPLETE_PIXEL_AND_SOURCE_GROUP_STAGE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "lef12s140v1:sweep:" + canonical_json_sha256_v1(material)}
    )


def validate_family_first_loan_enterprise_140_filing_schema_sweep_v1(
    value: Any,
) -> dict[str, Any]:
    """Validate non-authoritative shape; exact acceptance requires public input replay."""

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
