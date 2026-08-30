#!/usr/bin/env python3
"""Run Family51 exchange-rate matrices over the authenticated 140-document corpus."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bctc_ai.evaluation.gemini_json_equity_matrix_accounting_family_v1 import (  # noqa: E402
    READY,
    build_gemini_json_equity_matrix_region_query_receipt_v1,
    evaluate_gemini_json_equity_matrix_family_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.storage.gemini_accounting_family_store_v1 import (  # noqa: E402
    ingest_gemini_accounting_family_sweep_v1,
    load_gemini_accounting_family_sweep_v1,
    record_gemini_accounting_family_export_v1,
)
from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import (  # noqa: E402
    validate_current_corpus_manifest_index_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    query_selected_equity_matrix_family_regions_v1,
    validate_selected_equity_matrix_family_candidate_replays_v1,
)
from scripts.experiments.run_gemini_json_equity_matrix_accounting_family_v1 import (  # noqa: E402
    _authenticated_sqlite_snapshot,
    _content_ref,
    _file_ref,
    _json,
    _load_selected_pages_by_document,
    _selected_page_axis,
    _trials,
    _write_once,
)


class RunGeminiJsonExchangeRateFamilyV1Error(RuntimeError):
    """The Family51 source, category matrix, comparator, or store boundary drifted."""


def _error(message: str) -> RunGeminiJsonExchangeRateFamilyV1Error:
    return RunGeminiJsonExchangeRateFamilyV1Error(message)


AUDIT_FORMAT_VERSION = "GEMINI_JSON_EXCHANGE_RATE_EXPERIMENTAL_AUDIT_V1"
PINNED_CORPUS_MANIFEST_INDEX_ID = (
    "gjfccmiv1:index:61be9e5dc44a261d2dbf3f396b9624e29cb4ae591ea0a7fdb83051352e7b60e3"
)
PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256 = (
    "601be9fc2a894af2ce4f4c982d5347521a6268a46c075d9cc96f9828baef8ae8"
)
PINNED_RELEASE_METRICS = {
    "document_count": 140,
    "mapping_count": 976,
    "not_observed_count": 42,
    "ready_count": 98,
    "unresolved_count": 0,
}
PINNED_QUERY_RECEIPT = {
    "accepted_cluster_axis_sha256": (
        "76a176b8faaa54bb26d7b3bac7f107fe5513385b60a2d52ce0edb1d569fd6bb3"
    ),
    "accepted_cluster_count": 98,
    "accepted_fragment_count": 98,
    "candidate_disposition_axis_sha256": (
        "ed0ef46a41789436a70cf626cd49472e238cc0468ec23576892770baeafbfce3"
    ),
    "candidate_disposition_count": 140,
    "disposition_counts": {
        "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY": 42,
        "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY": 98,
        "UNRESOLVED_GEMINI_JSON_FAMILY": 0,
    },
    "query_policy_sha256": "98c1643bae115bff23ff86aae531c658a4d756c6501a87ab32daa96e8b96071d",
    "selected_document_axis_sha256": (
        "54df769ecd6875cc8a7d242d46f6e57bf2a94ac349ad0109db72f3cd6af62e4c"
    ),
    "selected_document_count": 140,
    "selected_page_axis_sha256": (
        "04d461370f74243e4f6e01c27b688afabf6c0e86d9fa6ec5dc12b7ef20c1810c"
    ),
    "selected_page_count": 8947,
    "selected_page_json_frontier_sha256": PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256,
}
PINNED_AUDIT_METRICS = {
    "category_row_count": 1201,
    "denominator_receipt_count": 98,
    "historical_mapping_exact_count": 100,
    "historical_mapping_mismatch_count": 0,
    "historical_mapping_source_superseded_count": 1,
    "historical_source_only_exact_count": 34,
    "historical_source_only_mismatch_count": 0,
    "mapping_count": 976,
    "mapping_value_count": 1756,
    "period_assignment_count": 196,
    "source_only_cell_count": 646,
    "source_only_row_count": 323,
    "unresolved_document_count": 0,
}
PINNED_AXIS_COUNTS = {
    "category_rows": 1201,
    "clusters": 98,
    "denominator_receipts": 98,
    "historical_documents": 16,
    "historical_mappings": 101,
    "historical_source_only": 34,
    "mappings": 976,
    "period_assignments": 196,
    "source_only_cells": 646,
    "source_only_rows": 323,
    "unresolved_documents": 0,
}
PINNED_AXIS_SHA256 = {
    "category_rows": "f19e166832ff34635e47ed6b75b42813146fbdb0f517e9adbfc83c81fffe17c4",
    "clusters": "1e724bc42140c084f03c026cb77480ef9680ccb17ea47d4b504d58227af14b27",
    "denominator_receipts": ("9d4f2c3e17bfd653def6984bb3885bdddf4879c2fabc92a42971eb9e9ce116cf"),
    "historical_documents": ("5e4aea131e2fb8ce6a1fd19aba2bf12574e4cb7ddf2d96ea60d0972b6aa98fe2"),
    "historical_mappings": ("7f8e5e2a9ca4e6b56978f1fe603659d36cc03a7c2f840fe2dc0fe4e0aaa06c0b"),
    "historical_source_only": ("7e13453b1f9a021699f2a3ce051e25b2a183d4bac40f8298e864806767e62cc5"),
    "mappings": "8d1d36dad1a6bcf6538d38ef588901049a4587bab113ff6603eb05aa516902ad",
    "period_assignments": ("f308060b670e4680f8379242268a9be5a988fbc1ec3a71d6215bf0809e250688"),
    "source_only_cells": ("9d4b70cee921a37d4afff8d0ef673b1616a67f34bc2488ea47379bdef967d200"),
    "source_only_rows": ("f7e7de4bae1a1386d52fd140c7762dad3854333be2d0a9d6ad54e6ee83145e9f"),
    "unresolved_documents": ("37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570"),
}
PINNED_HISTORICAL_ORACLES = [
    {
        "format_version": "EXCHANGE_RATE_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": "docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json",
        "sha256": "42d990e585f13a3dab0d9ad983198b89962d3ffb9342ba9e5815b52d015704f0",
        "size_bytes": 122396,
    },
    {
        "format_version": "ANNUAL_2025_EXCHANGE_RATE_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": (
            "docs/experiments/E-0158-annual-2025-exchange-rate-8bank-codex-verified-mapping-v1.json"
        ),
        "sha256": "3d3dd84d2b6b8d1ae48252573271d3ef12bb7b4517e48c07d4783c356478056b",
        "size_bytes": 133041,
    },
]


def _historical_oracles() -> list[tuple[dict[str, Any], dict[str, Any]]]:
    result = []
    for reference in PINNED_HISTORICAL_ORACLES:
        path = ROOT / reference["path"]
        actual = _file_ref(path, root=ROOT)
        if not same_typed_json_v1(actual, {key: reference[key] for key in actual}):
            raise _error("Family51 historical oracle reference drifted")
        value = _json(path)
        if value.get("format_version") != reference["format_version"]:
            raise _error("Family51 historical oracle format drifted")
        result.append((value, canonical_clone_v1(reference)))
    return result


def _candidate_by_source(trials: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    result = {}
    for trial in trials:
        source_sha256 = trial["source_sha256"]
        if source_sha256 in result:
            raise _error("Family51 trial source axis is not unique")
        result[source_sha256] = trial
    return result


def _mapping_axis(candidate: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result = {}
    for mapping in candidate["mappings"]:
        role = mapping["role"]
        if role == "FAMILY":
            continue
        if role in result:
            raise _error("Family51 candidate repeats one mapped category role")
        result[role] = mapping
    return result


def _historical_axes(
    *, trials: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    current = _candidate_by_source(trials)
    documents = []
    mappings = []
    source_only = []
    oracle_refs = []
    for oracle, reference in _historical_oracles():
        oracle_refs.append(reference)
        oracle_kind = oracle["format_version"]
        for item in oracle["trials"]:
            source_sha256 = item["source_pdf_sha256"]
            trial = current.get(source_sha256)
            historical_ready = item["status"].startswith("VERIFIED_BY_CODEX")
            current_ready = trial is not None and trial["status"] == READY
            if historical_ready and not current_ready:
                disposition = "CURRENT_UNRESOLVED"
            elif not historical_ready and current_ready:
                disposition = "CURRENT_SOURCE_SUPERSEDES_HISTORICAL_ABSENCE"
            elif not historical_ready:
                disposition = "HISTORICAL_ABSENCE_STILL_NOT_OBSERVED"
            else:
                disposition = "EXACT"
            document = {
                "current_document_ordinal": (
                    trial["document_ordinal"] if trial is not None else None
                ),
                "current_status": trial["status"] if trial is not None else None,
                "disposition": disposition,
                "historical_document_ordinal": item["document_ordinal"],
                "historical_status": item["status"],
                "oracle_format_version": oracle_kind,
                "source_sha256": source_sha256,
            }
            documents.append(document)
            candidate = (
                trial["candidates"][0] if current_ready and len(trial["candidates"]) == 1 else None
            )
            current_mappings = _mapping_axis(candidate) if candidate is not None else {}
            current_source_values = (
                {
                    row["role"]: {
                        value["axis_role"]: value["coefficient"] for value in row["values"]
                    }
                    for row in candidate["closure_receipt"]["source_only_category_axis"]
                }
                if candidate is not None
                else {}
            )
            for historical in item["verified_mappings"]:
                role = historical["code"]
                current_mapping = current_mappings.get(role)
                historical_values = {
                    value["axis"]: value["normalized_value_cents"] for value in historical["values"]
                }
                current_values = (
                    {
                        value["axis_role"]: value["coefficient"]
                        for value in current_mapping["values"]
                    }
                    if current_mapping is not None
                    else {}
                )
                current_report_norm_id = (
                    current_mapping["report_norm_id"] if current_mapping is not None else None
                )
                historical_report_norm_id = historical["schema_binding"]["report_norm_id"]
                displaced_role = next(
                    (
                        source_role
                        for source_role, source_values in current_source_values.items()
                        if source_values == historical_values
                    ),
                    None,
                )
                if (
                    current_values == historical_values
                    and current_report_norm_id == historical_report_norm_id
                ):
                    mapping_disposition = "EXACT"
                elif displaced_role is not None:
                    mapping_disposition = (
                        "HISTORICAL_VALUE_BOUND_TO_DIFFERENT_VISIBLE_ROLE_SUPERSEDED"
                    )
                else:
                    mapping_disposition = "MISMATCH"
                mappings.append(
                    {
                        **document,
                        "current_values": current_values,
                        "current_report_norm_id": current_report_norm_id,
                        "displaced_visible_source_role": displaced_role,
                        "disposition": mapping_disposition,
                        "historical_values": historical_values,
                        "report_norm_id": historical_report_norm_id,
                        "role": role,
                    }
                )
            current_source_roles = (
                {row["role"] for row in candidate["closure_receipt"]["source_only_category_axis"]}
                if candidate is not None
                else set()
            )
            for historical in item["verified_source_only_rows"]:
                role = historical.get("code") or historical.get("label")
                normalized_role = (
                    f"SOURCE_{role}" if role and not role.startswith("SOURCE_") else role
                )
                historical_values = {
                    value["axis"]: value["normalized_value_cents"] for value in historical["values"]
                }
                current_values = current_source_values.get(normalized_role)
                source_only.append(
                    {
                        **document,
                        "current_values": current_values,
                        "disposition": (
                            "EXACT"
                            if normalized_role in current_source_roles
                            and current_values == historical_values
                            else "MISMATCH"
                        ),
                        "historical_values": historical_values,
                        "role": normalized_role,
                    }
                )
    return {
        "historical_documents": documents,
        "historical_mappings": mappings,
        "historical_source_only": source_only,
    }, oracle_refs


def _audit_axes(
    *, sweep: Mapping[str, Any], compiled_specs: Mapping[str, Any]
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    trials = sweep["trials"]
    clusters = []
    category_rows = []
    denominator_receipts = []
    mappings = []
    period_assignments = []
    source_only_cells = []
    source_only_rows = []
    unresolved_documents = []
    for trial in trials:
        document = {
            "document_ordinal": trial["document_ordinal"],
            "source_logical_name": trial["source_logical_name"],
            "source_sha256": trial["source_sha256"],
        }
        if trial["status"] != READY:
            if trial["status"] != "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY":
                unresolved_documents.append({**document, "reasons": trial["reasons"]})
            continue
        if len(trial["candidates"]) != 1:
            raise _error("READY Family51 trial does not have exactly one candidate")
        candidate = trial["candidates"][0]
        closure = candidate["closure_receipt"]
        clusters.append(
            {
                **document,
                "candidate_id": candidate["candidate_id"],
                "component_regions": candidate["component_regions"],
                "query_receipt_sha256": canonical_json_sha256_v1(closure["query_receipt"]),
            }
        )
        locator = candidate["component_regions"][0]
        for row in closure["category_axis"]:
            category_rows.append({**document, **locator, **row})
        denominator_receipts.append(
            {**document, **locator, "receipt": closure["rate_denominator_receipt"]}
        )
        for assignment in closure["period_assignments"]:
            period_assignments.append({**document, **locator, **assignment})
        for mapping in candidate["mappings"]:
            mappings.append(
                {
                    **document,
                    "coefficients": [value["coefficient"] for value in mapping["values"]],
                    "period_dates": [value["period_date"] for value in mapping["values"]],
                    "report_norm_id": mapping["report_norm_id"],
                    "role": mapping["role"],
                    "row_id": mapping["row_id"],
                    "states": [value["state"] for value in mapping["values"]],
                    "unit": mapping["unit"],
                }
            )
        for row in closure["source_only_category_axis"]:
            source_only_rows.append(
                {
                    **document,
                    **locator,
                    "label_exact": row["label_exact"],
                    "role": row["role"],
                    "row_id": row["row_id"],
                    "source_order": row["source_order"],
                }
            )
            for cell in row["cells"]:
                source_only_cells.append(
                    {
                        **document,
                        "cell_ref": cell["cell_ref"],
                        "coefficient": cell["coefficient"],
                        "role": row["role"],
                        "source_text": cell["source_text"],
                        "state": cell["state"],
                    }
                )
    historical, oracle_refs = _historical_axes(trials=trials)
    return {
        "category_rows": category_rows,
        "clusters": clusters,
        "denominator_receipts": denominator_receipts,
        **historical,
        "mappings": mappings,
        "period_assignments": period_assignments,
        "source_only_cells": source_only_cells,
        "source_only_rows": source_only_rows,
        "unresolved_documents": unresolved_documents,
    }, oracle_refs


def _audit_metrics(axes: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, int]:
    return {
        "category_row_count": len(axes["category_rows"]),
        "denominator_receipt_count": len(axes["denominator_receipts"]),
        "historical_mapping_exact_count": sum(
            item["disposition"] == "EXACT" for item in axes["historical_mappings"]
        ),
        "historical_mapping_mismatch_count": sum(
            item["disposition"] == "MISMATCH" for item in axes["historical_mappings"]
        ),
        "historical_mapping_source_superseded_count": sum(
            item["disposition"] == "HISTORICAL_VALUE_BOUND_TO_DIFFERENT_VISIBLE_ROLE_SUPERSEDED"
            for item in axes["historical_mappings"]
        ),
        "historical_source_only_exact_count": sum(
            item["disposition"] == "EXACT" for item in axes["historical_source_only"]
        ),
        "historical_source_only_mismatch_count": sum(
            item["disposition"] != "EXACT" for item in axes["historical_source_only"]
        ),
        "mapping_count": len(axes["mappings"]),
        "mapping_value_count": sum(len(item["coefficients"]) for item in axes["mappings"]),
        "period_assignment_count": len(axes["period_assignments"]),
        "source_only_cell_count": len(axes["source_only_cells"]),
        "source_only_row_count": len(axes["source_only_rows"]),
        "unresolved_document_count": len(axes["unresolved_documents"]),
    }


def build_exchange_rate_experimental_audit_v1(
    *, sweep: Mapping[str, Any], compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    validate_gemini_json_flat_family_sweep_v1(sweep)
    axes, oracle_refs = _audit_axes(sweep=sweep, compiled_specs=compiled_specs)
    axis_counts = {name: len(axis) for name, axis in axes.items()}
    axis_sha256 = {name: canonical_json_sha256_v1(axis) for name, axis in axes.items()}
    audit_metrics = _audit_metrics(axes)
    material = {
        "audit_metrics": audit_metrics,
        "axes": axes,
        "axis_counts": axis_counts,
        "axis_sha256": axis_sha256,
        "claim_boundary": (
            "AUTHENTICATED_SELECTED_GEMINI_JSON_SQLITE_CATEGORY_PERIOD_MATRIX_REPLAY_"
            "AND_HISTORICAL_VALUE_COMPARATOR_ONLY_NO_PROVIDER_NO_GEOMETRY"
        ),
        "format_version": AUDIT_FORMAT_VERSION,
        "historical_oracle_refs": oracle_refs,
        "query_evidence_id": sweep["indexed_query_evidence"]["query_evidence_id"],
        "query_receipt": sweep["indexed_query_evidence"]["query_receipt"],
        "state": "EXPERIMENTAL_AUDIT_COMPLETE",
        "sweep_id": sweep["sweep_id"],
    }
    return {**material, "audit_id": "gjxerav1:audit:" + canonical_json_sha256_v1(material)}


def validate_exchange_rate_experimental_audit_content_v1(value: Any) -> dict[str, Any]:
    fields = {
        "audit_id",
        "audit_metrics",
        "axes",
        "axis_counts",
        "axis_sha256",
        "claim_boundary",
        "format_version",
        "historical_oracle_refs",
        "query_evidence_id",
        "query_receipt",
        "state",
        "sweep_id",
    }
    axis_names = {
        "category_rows",
        "clusters",
        "denominator_receipts",
        "historical_documents",
        "historical_mappings",
        "historical_source_only",
        "mappings",
        "period_assignments",
        "source_only_cells",
        "source_only_rows",
        "unresolved_documents",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value.get("format_version") != AUDIT_FORMAT_VERSION
        or value.get("state") != "EXPERIMENTAL_AUDIT_COMPLETE"
        or type(value.get("axes")) is not dict
        or set(value["axes"]) != axis_names
        or any(type(axis) is not list for axis in value["axes"].values())
    ):
        raise _error("Family51 experimental audit shape drifted")
    counts = {name: len(axis) for name, axis in value["axes"].items()}
    hashes = {name: canonical_json_sha256_v1(axis) for name, axis in value["axes"].items()}
    if value.get("axis_counts") != counts or value.get("axis_sha256") != hashes:
        raise _error("Family51 experimental audit axis seal drifted")
    if value.get("audit_metrics") != _audit_metrics(value["axes"]):
        raise _error("Family51 experimental audit metrics drifted")
    material = {key: value[key] for key in fields - {"audit_id"}}
    if value.get("audit_id") != "gjxerav1:audit:" + canonical_json_sha256_v1(material):
        raise _error("Family51 experimental audit identity drifted")
    return canonical_clone_v1(value)


def validate_exchange_rate_experimental_audit_replay_v1(
    value: Any,
    *,
    sweep: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
    source_database: Path,
    selected_page_json_version_ids: Sequence[str],
) -> dict[str, Any]:
    checked = validate_gemini_json_flat_family_sweep_v1(sweep)
    embedded = compile_gemini_json_flat_family_specs_v1(
        checked["specs"]["topology"]["value"],
        checked["specs"]["evaluation"]["value"],
        checked["specs"]["schema_binding"]["value"],
    )
    if not same_typed_json_v1(embedded, compiled_specs):
        raise _error("Family51 caller and embedded compiled specs differ")
    validate_selected_equity_matrix_family_candidate_replays_v1(
        source_database,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=embedded,
        indexed_query_evidence=checked["indexed_query_evidence"],
        trials=checked["trials"],
    )
    expected = build_exchange_rate_experimental_audit_v1(sweep=checked, compiled_specs=embedded)
    validate_exchange_rate_experimental_audit_content_v1(value)
    if not same_typed_json_v1(value, expected):
        raise _error("Family51 experimental audit does not replay exactly")
    return expected


def build_exchange_rate_experimental_bundle_v1(
    *,
    corpus_manifest_index_id: str,
    database: Path,
    selected_ids: Sequence[str],
    topology: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    schema: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
    if (
        compiled.get("family_id") != "EXCHANGE_RATE"
        or compiled.get("exchange_rate_mode") is not True
    ):
        raise _error("Family51 runner received a different family triplet")
    indexed = query_selected_equity_matrix_family_regions_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
    )
    pages = _load_selected_pages_by_document(
        database,
        selected_ids=selected_ids,
        selected_page_axis=indexed["selected_page_axis"],
    )
    candidates = {}
    for cluster in indexed["accepted_clusters"]:
        ordinal = cluster["document_ordinal"]
        regions = cluster["component_regions"]
        candidates[ordinal] = evaluate_gemini_json_equity_matrix_family_cluster_v1(
            regions=regions,
            page_json_by_version=pages[ordinal],
            compiled_specs=compiled,
            query_receipt=build_gemini_json_equity_matrix_region_query_receipt_v1(
                regions, owner_receipt=cluster["owner_receipt"]
            ),
            document_unit_context_evidence=cluster["document_unit_context_evidence"],
        )
    trials = _trials(indexed=indexed, candidates_by_ordinal=candidates)
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id=corpus_manifest_index_id,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        indexed_query_evidence=indexed,
        trials=trials,
    )
    validate_gemini_json_flat_family_sweep_v1(sweep)
    audit = build_exchange_rate_experimental_audit_v1(sweep=sweep, compiled_specs=compiled)
    validate_exchange_rate_experimental_audit_replay_v1(
        audit,
        sweep=sweep,
        compiled_specs=compiled,
        source_database=database,
        selected_page_json_version_ids=selected_ids,
    )
    return sweep, audit, compiled


def _assert_release_pins(
    *, sweep: Mapping[str, Any], audit: Mapping[str, Any], selected_ids: Sequence[str]
) -> None:
    if not PINNED_RELEASE_METRICS:
        raise _error("Family51 release pins have not been frozen")
    if (
        sweep["corpus_manifest_index_id"] != PINNED_CORPUS_MANIFEST_INDEX_ID
        or canonical_json_sha256_v1(list(selected_ids)) != PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256
        or not same_typed_json_v1(sweep["metrics"], PINNED_RELEASE_METRICS)
        or not same_typed_json_v1(
            sweep["indexed_query_evidence"]["query_receipt"], PINNED_QUERY_RECEIPT
        )
        or not same_typed_json_v1(audit["audit_metrics"], PINNED_AUDIT_METRICS)
        or not same_typed_json_v1(audit["axis_counts"], PINNED_AXIS_COUNTS)
        or not same_typed_json_v1(audit["axis_sha256"], PINNED_AXIS_SHA256)
    ):
        raise _error("Family51 frozen corpus release pins drifted")


def run(args: argparse.Namespace) -> dict[str, Any]:
    index = validate_current_corpus_manifest_index_v1(_json(args.corpus_index))
    artifact_root = args.artifact_root.resolve()
    source_database = _content_ref(artifact_root, index["database_ref"])
    selected_ids = _selected_page_axis(index=index, artifact_root=artifact_root)
    topology = _json(args.topology_spec)
    evaluation = _json(args.evaluation_spec)
    schema = _json(args.schema_binding_spec)
    with _authenticated_sqlite_snapshot(
        source_database, reference=index["database_ref"]
    ) as database_guard:
        database = database_guard.path
        sweep, audit, _compiled = build_exchange_rate_experimental_bundle_v1(
            corpus_manifest_index_id=index["corpus_manifest_index_id"],
            database=database,
            selected_ids=selected_ids,
            topology=topology,
            evaluation=evaluation,
            schema=schema,
        )
        _assert_release_pins(sweep=sweep, audit=audit, selected_ids=selected_ids)
        _write_once(args.output, sweep)
        audit_output = args.output.with_suffix(".audit.json")
        _write_once(audit_output, audit)
        implementation_paths = (
            ROOT / "scripts/experiments/run_gemini_json_exchange_rate_family_v1.py",
            ROOT / "src/bctc_ai/evaluation/gemini_json_categorical_period_matrix_v1.py",
            ROOT / "src/bctc_ai/evaluation/gemini_json_equity_matrix_accounting_family_v1.py",
            ROOT / "src/bctc_ai/evaluation/gemini_json_flat_accounting_family_v1.py",
            ROOT / "src/bctc_ai/storage/gemini_accounting_family_store_v1.py",
            ROOT / "src/bctc_ai/storage/gemini_financial_page_store_v1.py",
        )
        stored = ingest_gemini_accounting_family_sweep_v1(
            args.results_database,
            sweep=sweep,
            corpus_index_ref=_file_ref(args.corpus_index),
            implementation_refs=[_file_ref(path, root=ROOT) for path in implementation_paths],
            run_kind=args.run_kind,
            source_page_database=database,
            selected_page_json_version_ids=selected_ids,
            corpus_artifact_root=artifact_root,
        )
        stored_sweep = load_gemini_accounting_family_sweep_v1(
            args.results_database, stored["family_run_id"]
        )
        if not same_typed_json_v1(stored_sweep, sweep):
            raise _error("stored Family51 sweep differs from authenticated evaluation")
        output_ref = record_gemini_accounting_family_export_v1(
            args.results_database,
            family_run_id=stored["family_run_id"],
            output_path=args.output,
        )
        database_guard.validate()
    return {
        "audit_id": audit["audit_id"],
        "audit_output": str(audit_output),
        "axis_counts": audit["axis_counts"],
        "axis_sha256": audit["axis_sha256"],
        "disposition": "SUCCEEDED",
        "family_run_id": stored["family_run_id"],
        "metrics": sweep["metrics"],
        "output": str(args.output),
        "output_ref": output_ref,
        "results_database": str(args.results_database),
        "run_kind": args.run_kind,
        "sweep_id": sweep["sweep_id"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-index", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--topology-spec", type=Path, required=True)
    parser.add_argument("--evaluation-spec", type=Path, required=True)
    parser.add_argument("--schema-binding-spec", type=Path, required=True)
    parser.add_argument("--results-database", type=Path, required=True)
    parser.add_argument("--run-kind", choices=("EXPERIMENTAL", "OFFICIAL"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    print(json.dumps(run(_parser().parse_args()), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
