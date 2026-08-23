#!/usr/bin/env python3
"""Build/replay the fixed 140-filing customer-loan industry schema sweep."""

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
from scripts.experiments import (  # noqa: E402
    loan_industry_numeric_conflict_evidence_v1 as conflict_v1,
)
from scripts.experiments import (  # noqa: E402
    loan_industry_numeric_row_reconciliation_v1 as numeric_v1,
)
from scripts.experiments import loan_industry_variant_graph_v1 as graph_v1  # noqa: E402
from scripts.experiments.loan_type_missing_cell_evidence_v1 import (  # noqa: E402
    _matcher_pages,
)

FORMAT_VERSION = "FAMILY_FIRST_LOAN_INDUSTRY_140_FILING_SCHEMA_SWEEP_V1"
CLAIM_BOUNDARY = (
    "FIXED_140_FILING_AUTHENTICATED_COMPLETE_DOCUMENT_UNIQUE_LOAN_INDUSTRY_"
    "VARIABLE_GRAPH_FRESH_VIETOCR_LABEL_PPOCRV6_NUMBER_BOUNDED_PIXEL_VIETOCR_"
    "HOSTED_GEMMA4_CONFLICT_CONSENSUS_ACCOUNTING_AND_LIVE_TM_SCHEMA_MAPPING_"
    "ONLY_NO_EXPORT_OR_PRODUCTION_AUTHORITY"
)
OUTPUT_PATH = Path(
    "output/calibration/family-first-loan-industry-140-filing-schema-sweep-v1/result.json"
)
CHALLENGER_PATH = Path(
    "docs/experiments/E-0165-family-first-loan-industry-hosted-gemma4-numeric-challenger-v1.json"
)
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_document_unique_structural_region_required": True,
    "fresh_vietocr_used_for_semantic_labels": True,
    "gemma4_used_as_sole_numeric_authority": False,
    "mapping_decided_by_text_similarity_alone": False,
    "percentage_lanes_preserved_as_corroboration": True,
    "ppocrv6_used_for_primary_numeric_cells": True,
    "public_exact_live_replay_required": True,
    "schema_mapping_authority_bounded_to_this_family": True,
    "source_rounding_residual_may_rewrite_a_visible_cell": False,
    "whole_document_absence_is_bounded_to_each_filing": True,
}
_ROLE_TO_SCHEMA_ID = {
    "ACCOMMODATION_FOOD": 738,
    "ADMIN_SUPPORT": 743,
    "AGRICULTURE_FORESTRY_FISHERY": 728,
    "ARTS_ENTERTAINMENT": 5720,
    "BROAD_SERVICES": 6060,
    "COMBINED_TRADE_SERVICES": 6073,
    "CONSTRUCTION": 732,
    "EDUCATION": 737,
    "FINANCE_BANKING_INSURANCE": 741,
    "FOREIGN_BRANCH_LOANS": 6058,
    "HEALTH_SOCIAL_WORK": 5719,
    "HOUSEHOLD_EMPLOYMENT_SELF_USE": 5722,
    "INFORMATION_COMMUNICATION": 740,
    "MANUFACTURING": 733,
    "MARGIN_AND_SECURITIES_ADVANCE": 5749,
    "MINING": 729,
    "OTHER_INDUSTRIES": 745,
    "OTHER_SERVICES": 5721,
    "PERSONAL_COMMUNITY_SERVICES": 739,
    "PERSONAL_HOUSING_LOANS": 6059,
    "PROFESSIONAL_SCIENCE_TECHNOLOGY": 742,
    "PUBLIC_ADMIN_DEFENCE_SOCIAL_SECURITY": 745,
    "REAL_ESTATE": 735,
    "TRADE_REPAIR": 734,
    "TRANSPORT_STORAGE": 736,
    "UTILITIES": 730,
    "WATER_WASTE": 731,
}
_IMPLEMENTATION_PATHS = (
    Path("scripts/experiments/loan_industry_variant_graph_v1.py"),
    Path("scripts/experiments/loan_industry_numeric_row_reconciliation_v1.py"),
    Path("scripts/experiments/loan_industry_numeric_conflict_evidence_v1.py"),
    Path("scripts/experiments/build_family_first_loan_industry_140_filing_schema_sweep_v1.py"),
)


class FamilyFirstLoanIndustry140FilingSchemaSweepV1Error(ValueError):
    """The live document, graph, numeric evidence, schema, or output drifted."""


def _error(message: str) -> FamilyFirstLoanIndustry140FilingSchemaSweepV1Error:
    return FamilyFirstLoanIndustry140FilingSchemaSweepV1Error(message)


def _stable_ref(root: Path, relative: Path) -> dict[str, Any]:
    path = root / relative
    try:
        before = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(before.st_mode):
            raise _error(f"input is not one regular nofollow file: {relative}")
        payload = path.read_bytes()
        after = path.lstat()
    except OSError as exc:
        raise _error(f"cannot read stable input: {relative}") from exc

    def identity(item: os.stat_result) -> tuple[int, int, int, int, int]:
        return (item.st_dev, item.st_ino, item.st_mode, item.st_size, item.st_mtime_ns)

    if identity(before) != identity(after) or len(payload) != before.st_size:
        raise _error(f"input changed during read: {relative}")
    return {
        "path": relative.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _strict_challenger(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    reference = _stable_ref(root, CHALLENGER_PATH)
    try:
        payload = (root / CHALLENGER_PATH).read_bytes()
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=lambda pairs: _unique_object(pairs),
            parse_constant=lambda raw: (_ for _ in ()).throw(
                ValueError(f"non-finite challenger JSON: {raw}")
            ),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise _error("loan-industry challenger is not strict UTF-8 JSON") from exc
    if (
        len(payload) != reference["size_bytes"]
        or hashlib.sha256(payload).hexdigest() != reference["sha256"]
        or not same_typed_json_v1(_stable_ref(root, CHALLENGER_PATH), reference)
    ):
        raise _error("loan-industry challenger changed during strict read")
    return conflict_v1.validate_loan_industry_hosted_gemma4_challenger_v1(value), reference


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _period_for_lane(graph: dict[str, Any], lane: int) -> dict[str, Any]:
    candidates = sorted(
        graph["period_axis"],
        key=lambda item: (
            abs(item["x_center_x2"] - graph["lane_centers_x2"][lane]),
            item["x_center_x2"],
        ),
    )
    if not candidates:
        raise _error("industry money lane has no visible period axis")
    return canonical_clone_v1(candidates[0])


def _schema_projection(schema_by_id: dict[int, Any]) -> dict[int, dict[str, Any]]:
    expected = {727, *_ROLE_TO_SCHEMA_ID.values()}
    result = {}
    for schema_id in expected:
        node = schema_by_id.get(schema_id)
        if node is None:
            raise _error(f"required live industry schema node is absent: {schema_id}")
        result[schema_id] = {
            "canonical_name": node.canonical_name,
            "display_order": node.display_order,
            "parent_id": node.parent_id,
            "report_norm_id": schema_id,
            "statement_type": node.statement_type,
        }
    if (
        result[727]["statement_type"] != "TM"
        or result[727]["parent_id"] != 716
        or any(result[item]["parent_id"] != 727 for item in expected - {727})
    ):
        raise _error("live loan-industry schema hierarchy drifted")
    return result


def _mapping_rows(
    evidence: dict[str, Any],
    graph: dict[str, Any],
    schema: dict[int, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    money_lanes = [
        index for index, lane_type in enumerate(evidence["lane_types"]) if lane_type == "MONEY"
    ]
    if not money_lanes:
        raise _error("industry graph has no money lane")
    periods = [_period_for_lane(graph, lane) for lane in money_lanes]
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in (*evidence["rows"], *evidence["unmodelled_additive_rows"]):
        schema_id = _ROLE_TO_SCHEMA_ID.get(row["role"])
        if schema_id is None:
            raise _error(f"accepted industry source role has no schema disposition: {row['role']}")
        values = [row["cells"][lane]["parsed_value"] for lane in money_lanes]
        if any(type(value) is not int for value in values):
            raise _error("verified industry source row retains one unresolved money value")
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
                    sum(component["values"][lane] for component in components)
                    for lane in range(len(money_lanes))
                ],
            }
        )
    totals = [evidence["total"][lane]["parsed_value"] for lane in money_lanes]
    if any(type(value) is not int for value in totals):
        raise _error("industry visible total retains one unresolved money value")
    checks_by_lane = {item["lane_index"]: item for item in evidence["accounting_checks"]}
    mapping_checks = []
    for output_lane, source_lane in enumerate(money_lanes):
        mapped_sum = sum(item["values"][output_lane] for item in mappings)
        residual = mapped_sum - totals[output_lane]
        check = checks_by_lane.get(source_lane)
        if check is None or check["residual"] != residual:
            raise _error("industry mapping residual differs from numeric evidence")
        if check["status"] == "EXACT_PP_NUMERIC_EQUATION" and residual == 0:
            status = "EXACT_VISIBLE_CHILDREN_TO_PARENT_TOTAL"
        elif check["status"] == "CORROBORATED_ROUNDED_SOURCE_EQUATION":
            status = "CORROBORATED_PRINTED_SOURCE_ROUNDING_WITH_EXACT_PERCENT_COMPANION"
        else:
            raise _error("industry mapping does not have an admissible accounting check")
        mapping_checks.append(
            {
                "mapped_child_sum": mapped_sum,
                "money_lane_index": source_lane,
                "printed_parent_total": totals[output_lane],
                "residual": residual,
                "status": status,
            }
        )
    parent = {
        **canonical_clone_v1(schema[727]),
        "period_axis": canonical_clone_v1(periods),
        "source_owner": canonical_clone_v1(graph["customer_loan_context"]),
        "status": "VERIFIED_BY_CODEX",
        "values": totals,
    }
    return parent, mappings, mapping_checks


def _trial(
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    ordinal: int,
    schema: dict[int, dict[str, Any]],
    challenger: dict[str, Any],
    root: Path,
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
    graph_result = graph_v1.build_loan_industry_variant_graph_document_v1(
        matcher_pages, enable_extended_annual_variants=True
    )
    common = {
        "document": canonical_clone_v1(packet),
        "graph_result_id": graph_result["result_id"],
    }
    if graph_result["status"] == "UNRESOLVED_NO_COMPLETE_REGION":
        if graph_result["graphs"] or graph_result["near_regions"]:
            raise _error("industry absence retains one candidate branch region")
        return {
            **common,
            "absence_evidence": {
                "complete_branch_table_region_count": 0,
                "near_region_count": 0,
                "page_count_scanned": packet["page_count"],
                "status": "COMPLETE_DOCUMENT_NO_INDUSTRY_BRANCH_REGION",
                "whole_document_family_absence_claim": True,
            },
            "accounting_mapping_checks": [],
            "graph": None,
            "mapped_children": [],
            "mapped_parent": None,
            "numeric_conflict_evidence": None,
            "numeric_evidence": None,
            "page_sequence": None,
            "status": "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT",
        }
    if graph_result["status"] != "ACCEPTED_UNIQUE_VARIANT_GRAPH":
        raise _error(f"document {ordinal} has ambiguous industry regions")
    graph = graph_result["graphs"][0]
    base = numeric_v1.build_loan_industry_numeric_row_reconciliation_v1(matcher_pages)
    conflict = None
    if base["status"] in {
        "PP_NUMERIC_EXACT",
        "PP_NUMERIC_CORROBORATED_WITH_ROUNDING_TOLERANCE",
    }:
        evidence = base
    elif any(
        line["sample_id"] == challenger["observation"]["sample_id"]
        for page in snapshot["joined_pages"]
        for line in page["lines"]
    ):
        conflict = conflict_v1.build_loan_industry_numeric_conflict_evidence_v1(
            base, snapshot["joined_pages"], challenger, root
        )
        evidence = conflict
    else:
        raise _error(f"document {ordinal} retains unresolved industry numeric evidence")
    parent, mappings, mapping_checks = _mapping_rows(evidence, graph, schema)
    return {
        **common,
        "absence_evidence": None,
        "accounting_mapping_checks": mapping_checks,
        "graph": canonical_clone_v1(graph),
        "mapped_children": mappings,
        "mapped_parent": parent,
        "numeric_conflict_evidence": canonical_clone_v1(conflict),
        "numeric_evidence": canonical_clone_v1(base),
        "page_sequence": graph["page_sequence"],
        "status": "VERIFIED_BY_CODEX",
    }


def build_authenticated_family_first_loan_industry_140_filing_schema_sweep_v1(
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    project_root: Path,
) -> dict[str, Any]:
    """Build all 140 trials from the exact live document evidence store."""

    if not isinstance(project_root, Path):
        raise _error("loan-industry sweep project root must be one pathlib Path")
    root = project_root.resolve()
    store_projection = store_v1.project_authenticated_family_first_document_evidence_store_v1(
        capability
    )
    if store_projection["metrics"]["document_count"] != 140:
        raise _error("loan-industry sweep requires the fixed 140-filing denominator")
    challenger, challenger_ref = _strict_challenger(root)
    schema_authority, schema_by_id = _authority_snapshot(root)
    schema = _schema_projection(schema_by_id)
    trials = [_trial(capability, ordinal, schema, challenger, root) for ordinal in range(1, 141)]
    verified = [trial for trial in trials if trial["status"] == "VERIFIED_BY_CODEX"]
    absent = [
        trial for trial in trials if trial["status"] == "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT"
    ]
    if len(verified) + len(absent) != 140:
        raise _error("loan-industry sweep has a non-terminal trial")
    implementation_refs = {path.name: _stable_ref(root, path) for path in _IMPLEMENTATION_PATHS}
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "inputs": {
            "document_evidence_store": store_projection,
            "hosted_gemma4_numeric_challenger": challenger_ref,
            "hosted_gemma4_numeric_challenger_evaluation_id": challenger["evaluation_id"],
            "implementation_refs": implementation_refs,
            "schema_authority": schema_authority,
            "schema_projection": [schema[item] for item in sorted(schema)],
        },
        "metrics": {
            "confirmed_absent_trial_count": len(absent),
            "document_count": 140,
            "hosted_gemma4_consensus_rescue_count": sum(
                trial["numeric_conflict_evidence"] is not None for trial in verified
            ),
            "mapped_child_record_count": sum(len(trial["mapped_children"]) for trial in verified),
            "numeric_exact_or_corroborated_trial_count": len(verified),
            "source_rounding_corroborated_trial_count": sum(
                trial["numeric_evidence"]["status"]
                == "PP_NUMERIC_CORROBORATED_WITH_ROUNDING_TOLERANCE"
                for trial in verified
            ),
            "structure_unique_trial_count": len(verified),
            "verified_present_trial_count": len(verified),
        },
        "state": "COMPLETE",
        "trials": trials,
    }
    return {**material, "sweep_id": "li140v1:sweep:" + canonical_json_sha256_v1(material)}


def validate_authenticated_family_first_loan_industry_140_filing_schema_sweep_replay_v1(
    value: Any,
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    project_root: Path,
) -> dict[str, Any]:
    expected = build_authenticated_family_first_loan_industry_140_filing_schema_sweep_v1(
        capability, project_root
    )
    if not same_typed_json_v1(value, expected):
        raise _error("loan-industry 140-filing schema sweep does not replay exactly")
    return expected


def _strict_result(path: Path) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
        value = json.loads(payload.decode("utf-8", errors="strict"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("persisted loan-industry sweep is not strict JSON") from exc
    if type(value) is not dict or payload != canonical_json_bytes_v1(value) + b"\n":
        raise _error("persisted loan-industry sweep is not canonical JSON plus LF")
    return value


def _write_exclusive(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o444)
    try:
        view = memoryview(payload)
        while view:
            count = os.write(descriptor, view)
            if count <= 0:
                raise _error("loan-industry sweep write made no progress")
            view = view[count:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def run_family_first_loan_industry_140_filing_schema_sweep_v1(
    project_root: Path, *, command: str
) -> dict[str, Any]:
    if command not in {"build", "verify"}:
        raise _error("loan-industry sweep command drifted")
    root = project_root.resolve()
    output = root / OUTPUT_PATH
    if command == "build" and output.exists():
        raise _error("loan-industry sweep destination already exists")
    persisted = _strict_result(output) if command == "verify" else None
    capability = store_v1.authenticate_family_first_document_evidence_store_v1(root)
    result = build_authenticated_family_first_loan_industry_140_filing_schema_sweep_v1(
        capability, root
    )
    if command == "build":
        _write_exclusive(output, canonical_json_bytes_v1(result) + b"\n")
    elif not same_typed_json_v1(persisted, result):
        raise _error("persisted loan-industry sweep differs from live exact replay")
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
            run_family_first_loan_industry_140_filing_schema_sweep_v1(
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
