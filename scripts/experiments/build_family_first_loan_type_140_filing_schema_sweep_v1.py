#!/usr/bin/env python3
"""Build/replay the fixed 140-filing customer-loan-type schema sweep."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))
sys.path.insert(0, os.fspath(PROJECT_ROOT / "src"))

from bctc_ai.evaluation import family_first_document_evidence_store_v1 as store_v1  # noqa: E402
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import (  # noqa: E402
    _authority_snapshot,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from scripts.experiments import loan_type_missing_cell_evidence_v1 as missing_v1  # noqa: E402
from scripts.experiments import loan_type_numeric_row_reconciliation_v1 as numeric_v1  # noqa: E402
from scripts.experiments import loan_type_variant_graph_v1 as graph_v1  # noqa: E402

FORMAT_VERSION = "FAMILY_FIRST_LOAN_TYPE_140_FILING_SCHEMA_SWEEP_V1"
CLAIM_BOUNDARY = (
    "FIXED_140_FILING_AUTHENTICATED_COMPLETE_DOCUMENT_UNIQUE_LOAN_TYPE_GRAPH_"
    "FRESH_VIETOCR_LABEL_PPOCRV6_NUMBER_VISIBLE_PIXEL_DASH_EXACT_ACCOUNTING_"
    "AND_LIVE_TM_SCHEMA_MAPPING_ONLY_NO_EXPORT_OR_PRODUCTION_AUTHORITY"
)
OUTPUT_PATH = Path(
    "output/calibration/family-first-loan-type-140-filing-schema-sweep-v1/result.json"
)
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "blank_cell_means_zero": False,
    "canonicalization_or_export_authority": False,
    "complete_document_unique_structural_region_required": True,
    "fresh_vietocr_used_for_semantic_labels": True,
    "gemma_numeric_authority": False,
    "mapping_decided_by_text_similarity_alone": False,
    "percentage_lanes_preserved_as_corroboration": True,
    "ppocrv6_used_for_numeric_cells": True,
    "public_exact_live_replay_required": True,
    "schema_mapping_authority_bounded_to_this_family": True,
    "visible_dash_normalized_to_zero": True,
}
_ROLE_TO_SCHEMA_ID = {
    "DOMESTIC_ORGANIZATIONS_INDIVIDUALS": 718,
    "FINANCIAL_LEASE": 719,
    "GOVERNMENT_DIRECTED_OR_FUNDED": 6057,
    "FOREIGN_ORGANIZATIONS_INDIVIDUALS": 721,
    "DISCOUNT_INSTRUMENTS": 722,
    "PAYMENTS_ON_BEHALF": 723,
    "FROZEN_OR_PENDING_LOANS": 724,
    "ENTRUSTED_OR_SPONSORED_CAPITAL": 725,
    "OTHER_LOANS": 726,
    "UNMAPPED_OTHER_CREDIT": 726,
    "UNMODELLED_ADDITIVE_OTHER": 726,
    "MARGIN_AND_SECURITIES_ADVANCE": 5745,
}
_TARGETED_RESCUES = {
    "ffdesv1:document:59f4d0263e6bd32bac3a2aa054ddc9c41540fc3dab5b56040145674d74b44567": (
        {
            "crop_sha256": "f88fad945ea353fc9e007689832d924732d8d487e80a4ed0db5cb6e352e9b984",
            "lane_index": 2,
            "page_sequence": 38,
            "raw_prediction": "2",
            "reader_score": 0.9999853372573853,
            "role": "FOREIGN_ORGANIZATIONS_INDIVIDUALS",
        },
    ),
    "ffdesv1:document:524e7e16a90e77a6c3966094c794d66fa02db4276d646ceb24af274808943921": (
        {
            "crop_sha256": "e60ada731eaa7faee340232ca7a6779e45cb0745825413f9aaf0bb6179598a1c",
            "lane_index": 2,
            "page_sequence": 34,
            "raw_prediction": "2",
            "reader_score": 0.9999754428863525,
            "role": "FOREIGN_ORGANIZATIONS_INDIVIDUALS",
        },
    ),
}
_IMPLEMENTATION_PATHS = (
    Path("scripts/experiments/loan_type_variant_graph_v1.py"),
    Path("scripts/experiments/loan_type_numeric_row_reconciliation_v1.py"),
    Path("scripts/experiments/loan_type_missing_cell_evidence_v1.py"),
    Path("scripts/experiments/build_family_first_loan_type_140_filing_schema_sweep_v1.py"),
)


class FamilyFirstLoanType140FilingSchemaSweepV1Error(ValueError):
    """The live document, graph, numeric evidence, schema, or output drifted."""


def _error(message: str) -> FamilyFirstLoanType140FilingSchemaSweepV1Error:
    return FamilyFirstLoanType140FilingSchemaSweepV1Error(message)


def _stable_ref(root: Path, relative: Path) -> dict[str, Any]:
    path = root / relative
    try:
        before = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(before.st_mode):
            raise _error(f"implementation is not one regular nofollow file: {relative}")
        payload = path.read_bytes()
        after = path.lstat()
    except OSError as exc:
        raise _error(f"cannot read stable implementation: {relative}") from exc

    def identity(item: os.stat_result) -> tuple[int, int, int, int, int]:
        return (item.st_dev, item.st_ino, item.st_mode, item.st_size, item.st_mtime_ns)

    if identity(before) != identity(after) or len(payload) != before.st_size:
        raise _error(f"implementation changed during read: {relative}")
    return {
        "path": relative.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _matcher_pages(joined_pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return missing_v1._matcher_pages(joined_pages)


def _period_for_lane(graph: dict[str, Any], lane: int) -> dict[str, Any]:
    centers = graph["lane_centers_x2"]
    candidates = sorted(
        graph["period_axis"],
        key=lambda item: (abs(item["x_center_x2"] - centers[lane]), item["x_center_x2"]),
    )
    if not candidates:
        raise _error("loan-type money lane has no visible period axis")
    return canonical_clone_v1(candidates[0])


def _schema_projection(schema_by_id: dict[int, Any]) -> dict[int, dict[str, Any]]:
    expected = {717, *_ROLE_TO_SCHEMA_ID.values()}
    result = {}
    for schema_id in expected:
        node = schema_by_id.get(schema_id)
        if node is None:
            raise _error(f"required live TM schema node is absent: {schema_id}")
        result[schema_id] = {
            "canonical_name": node.canonical_name,
            "display_order": node.display_order,
            "parent_id": node.parent_id,
            "report_norm_id": schema_id,
            "statement_type": node.statement_type,
        }
    if (
        result[717]["statement_type"] != "TM"
        or result[717]["parent_id"] != 716
        or any(result[item]["parent_id"] != 717 for item in expected - {717})
    ):
        raise _error("live loan-type schema hierarchy drifted")
    return result


def _mapping_rows(
    evidence: dict[str, Any],
    graph: dict[str, Any],
    schema: dict[int, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    money_lanes = [
        lane for lane, lane_type in enumerate(evidence["lane_types"]) if lane_type == "MONEY"
    ]
    if not money_lanes:
        raise _error("loan-type graph has no money lane")
    periods = [_period_for_lane(graph, lane) for lane in money_lanes]
    rows = [*evidence["rows"], *evidence["unmodelled_additive_rows"]]
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        schema_id = _ROLE_TO_SCHEMA_ID.get(row["role"])
        if schema_id is None:
            raise _error(f"accepted source role has no schema disposition: {row['role']}")
        values = [row["cells"][lane]["parsed_value"] for lane in money_lanes]
        if any(type(value) is not int for value in values):
            raise _error("verified source row retains one unresolved money value")
        grouped[schema_id].append(
            {
                "source_label": canonical_clone_v1(row["label"]),
                "source_role": row["role"],
                "values": values,
            }
        )
    mappings = []
    for schema_id in sorted(grouped, key=lambda item: schema[item]["display_order"]):
        components = grouped[schema_id]
        mappings.append(
            {
                **canonical_clone_v1(schema[schema_id]),
                "period_axis": canonical_clone_v1(periods),
                "source_components": components,
                "status": "VERIFIED_BY_CODEX",
                "values": [
                    sum(item["values"][lane] for item in components)
                    for lane in range(len(money_lanes))
                ],
            }
        )
    totals = [evidence["total"][lane]["parsed_value"] for lane in money_lanes]
    if any(type(value) is not int for value in totals) or any(
        sum(item["values"][lane] for item in mappings) != totals[lane]
        for lane in range(len(money_lanes))
    ):
        raise _error("schema-mapped child rows do not close to the visible customer-loan total")
    parent = {
        **canonical_clone_v1(schema[717]),
        "period_axis": canonical_clone_v1(periods),
        "source_owner": canonical_clone_v1(graph["owner"]),
        "status": "VERIFIED_BY_CODEX",
        "values": totals,
    }
    return parent, mappings


def _trial(
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    ordinal: int,
    schema: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    packet = store_v1.read_authenticated_family_first_document_packet_v1(
        capability, document_ordinal=ordinal
    )
    snapshot = store_v1.read_authenticated_family_first_document_evidence_snapshot_v1(
        capability,
        document_ordinal=ordinal,
        selected_pages=tuple(range(1, packet["page_count"] + 1)),
    )
    matcher_pages = _matcher_pages(snapshot["joined_pages"])
    graph_result = graph_v1.build_loan_type_variant_graph_document_v1(
        matcher_pages, enable_extended_owner_table_variants=True
    )
    if graph_result["status"] != "ACCEPTED_UNIQUE_VARIANT_GRAPH":
        raise _error(f"document {ordinal} has no unique accepted loan-type graph")
    graph = graph_result["graphs"][0]
    base = numeric_v1.build_loan_type_numeric_row_reconciliation_v1(matcher_pages)
    if base["page_sequence"] != graph["page_sequence"]:
        raise _error("loan-type graph and numeric evidence selected different pages")
    if base["status"] == "PP_NUMERIC_EXACT":
        evidence = base
        pixel_evidence = None
    else:
        render = store_v1.read_authenticated_family_first_document_page_renders_v1(
            capability,
            document_ordinal=ordinal,
            physical_pages=(graph["page_sequence"],),
        )[0]
        pixel_evidence = missing_v1.build_loan_type_missing_cell_evidence_v1(
            snapshot["joined_pages"],
            render,
            numeric_rescue_observations=_TARGETED_RESCUES.get(packet["packet_id"], ()),
        )
        if pixel_evidence["status"] != "PIXEL_AND_PP_NUMERIC_EXACT":
            raise _error(f"document {ordinal} retains unresolved loan-type numeric cells")
        evidence = pixel_evidence
    parent, mappings = _mapping_rows(evidence, graph, schema)
    return {
        "document": canonical_clone_v1(packet),
        "graph": canonical_clone_v1(graph),
        "graph_result_id": graph_result["result_id"],
        "mapped_children": mappings,
        "mapped_parent": parent,
        "numeric_evidence": canonical_clone_v1(evidence),
        "page_sequence": graph["page_sequence"],
        "pixel_missing_cell_evidence": canonical_clone_v1(pixel_evidence),
        "status": "VERIFIED_BY_CODEX",
    }


def build_authenticated_family_first_loan_type_140_filing_schema_sweep_v1(
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    project_root: Path,
) -> dict[str, Any]:
    """Build all 140 trials from the exact live document evidence store."""

    if not isinstance(project_root, Path):
        raise _error("loan-type sweep project root must be one pathlib Path")
    root = project_root.resolve()
    store_projection = store_v1.project_authenticated_family_first_document_evidence_store_v1(
        capability
    )
    if store_projection["metrics"]["document_count"] != 140:
        raise _error("loan-type sweep requires the fixed 140-filing denominator")
    schema_authority, schema_by_id = _authority_snapshot(root)
    schema = _schema_projection(schema_by_id)
    trials = [_trial(capability, ordinal, schema) for ordinal in range(1, 141)]
    dash_count = sum(
        1
        for trial in trials
        for item in (trial["pixel_missing_cell_evidence"] or {}).get("evidence", [])
        if item["classification"] == "VISIBLE_PIXEL_DASH_ZERO"
    )
    rescue_count = sum(
        1
        for trial in trials
        for item in (trial["pixel_missing_cell_evidence"] or {}).get("evidence", [])
        if item["classification"] == "TARGETED_SAME_CROP_PPOCRV6_NUMERIC_RESCUE"
    )
    implementation_refs = {path.name: _stable_ref(root, path) for path in _IMPLEMENTATION_PATHS}
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "inputs": {
            "document_evidence_store": store_projection,
            "implementation_refs": implementation_refs,
            "schema_authority": schema_authority,
            "schema_projection": [schema[item] for item in sorted(schema)],
        },
        "metrics": {
            "document_count": 140,
            "mapped_child_record_count": sum(len(trial["mapped_children"]) for trial in trials),
            "numeric_exact_trial_count": 140,
            "structure_unique_trial_count": 140,
            "targeted_same_crop_ppocrv6_rescue_count": rescue_count,
            "verified_trial_count": 140,
            "visible_pixel_dash_zero_count": dash_count,
        },
        "state": "COMPLETE",
        "trials": trials,
    }
    return {**material, "sweep_id": "lt140v1:sweep:" + canonical_json_sha256_v1(material)}


def validate_authenticated_family_first_loan_type_140_filing_schema_sweep_replay_v1(
    value: Any,
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    project_root: Path,
) -> dict[str, Any]:
    expected = build_authenticated_family_first_loan_type_140_filing_schema_sweep_v1(
        capability, project_root
    )
    if not same_typed_json_v1(value, expected):
        raise _error("loan-type 140-filing schema sweep does not replay exactly")
    return expected


def _strict_result(path: Path) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
        value = json.loads(payload.decode("utf-8", errors="strict"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("persisted loan-type sweep is not strict JSON") from exc
    if type(value) is not dict or payload != canonical_json_bytes_v1(value) + b"\n":
        raise _error("persisted loan-type sweep is not canonical JSON plus LF")
    return value


def _write_exclusive(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o444)
    try:
        view = memoryview(payload)
        while view:
            count = os.write(descriptor, view)
            if count <= 0:
                raise _error("loan-type sweep write made no progress")
            view = view[count:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def run_family_first_loan_type_140_filing_schema_sweep_v1(
    project_root: Path, *, command: str
) -> dict[str, Any]:
    if command not in {"build", "verify"}:
        raise _error("loan-type sweep command drifted")
    root = project_root.resolve()
    output = root / OUTPUT_PATH
    if command == "build" and output.exists():
        raise _error("loan-type sweep destination already exists")
    persisted = _strict_result(output) if command == "verify" else None
    capability = store_v1.authenticate_family_first_document_evidence_store_v1(root)
    result = build_authenticated_family_first_loan_type_140_filing_schema_sweep_v1(capability, root)
    if command == "build":
        _write_exclusive(output, canonical_json_bytes_v1(result) + b"\n")
    elif not same_typed_json_v1(persisted, result):
        raise _error("persisted loan-type sweep differs from live exact replay")
    return {
        "metrics": result["metrics"],
        "output_path": OUTPUT_PATH.as_posix(),
        "sweep_id": result["sweep_id"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    args = parser.parse_args()
    print(
        json.dumps(
            run_family_first_loan_type_140_filing_schema_sweep_v1(
                PROJECT_ROOT, command=args.command
            ),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
