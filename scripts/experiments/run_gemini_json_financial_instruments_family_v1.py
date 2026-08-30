#!/usr/bin/env python3
"""Run Family47 financial instruments over the authenticated 140-document corpus."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bctc_ai.evaluation.gemini_json_equity_matrix_accounting_family_v1 import (  # noqa: E402
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    build_gemini_json_equity_matrix_region_query_receipt_v1,
    evaluate_gemini_json_equity_matrix_family_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_json_bytes_v1,
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
    validate_selected_equity_matrix_family_query_evidence_v1,
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


class RunGeminiJsonFinancialInstrumentsFamilyV1Error(RuntimeError):
    """The Family47 corpus, graph, comparator, or persistence boundary drifted."""


def _error(message: str) -> RunGeminiJsonFinancialInstrumentsFamilyV1Error:
    return RunGeminiJsonFinancialInstrumentsFamilyV1Error(message)


AUDIT_FORMAT_VERSION = "GEMINI_JSON_FINANCIAL_INSTRUMENTS_EXPERIMENTAL_AUDIT_V1"
PINNED_CORPUS_MANIFEST_INDEX_ID = (
    "gjfccmiv1:index:61be9e5dc44a261d2dbf3f396b9624e29cb4ae591ea0a7fdb83051352e7b60e3"
)
PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256 = (
    "601be9fc2a894af2ce4f4c982d5347521a6268a46c075d9cc96f9828baef8ae8"
)
PINNED_RELEASE_METRICS = {
    "document_count": 140,
    "mapping_count": 1408,
    "not_observed_count": 74,
    "ready_count": 66,
    "unresolved_count": 0,
}
PINNED_QUERY_RECEIPT = {
    "accepted_cluster_axis_sha256": (
        "59039ebdf3f65b4115209ba85d6209683e5e9e1166f377c01d43121fc2b803a4"
    ),
    "accepted_cluster_count": 66,
    "accepted_fragment_count": 68,
    "candidate_disposition_axis_sha256": (
        "5b34b20c5b3042e2b873b794210a89217e3a03b3dd5ebb63eaa110b97ad6e507"
    ),
    "candidate_disposition_count": 140,
    "disposition_counts": {NOT_OBSERVED: 74, READY: 66, UNRESOLVED: 0},
    "query_policy_sha256": "31f66ad305a47a75b155eff2966a35095da481a654dd0f52a0874b849a326746",
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
    "equation_count": 1293,
    "historical_exact_mapping_count": 105,
    "historical_mapping_mismatch_count": 0,
    "legacy_absence_superseded_count": 2,
    "mapping_count": 1408,
    "table_receipt_count": 68,
    "unavailable_fair_value_count": 917,
    "unresolved_document_count": 0,
}
PINNED_AXIS_COUNTS = {
    "clusters": 66,
    "equations": 1293,
    "historical_documents": 16,
    "historical_mappings": 105,
    "mappings": 1408,
    "table_receipts": 68,
    "unavailable_fair_values": 917,
    "unresolved_documents": 0,
}
PINNED_AXIS_SHA256 = {
    "clusters": "4f17251211df68b943392f68d5571012e7ba25a724d9afe2a0d11f689234f470",
    "equations": "cd7965070b0981c1d4d0b7364f0c7ead0f890b313cae33c67d8d0c2f62650f4e",
    "historical_documents": ("efb7db53d5790c5cf3fae88a11fb43062ca29e75999775cbbb35f39278e51c23"),
    "historical_mappings": ("36ceca16c116fb4d649786589bcd4c5f6be74bdc0808bbea465dea38774927b7"),
    "mappings": "2880d69c40d3e3f3277db35b502cfb37836e0d8267247a116f52a364248d6fc3",
    "table_receipts": ("8c73e6a5381cc5f78ea6d59ecc7c2867a3add1ed306371531f761d23824d51f5"),
    "unavailable_fair_values": ("c3020e2831786239d00a7917b66ab80ad545b9e36f65056cdae6475871925e69"),
    "unresolved_documents": ("37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570"),
}
PINNED_HISTORICAL_ORACLES = [
    {
        "format_version": "FINANCIAL_INSTRUMENTS_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": (
            "docs/experiments/E-0099-financial-instruments-8bank-codex-verified-mapping-v1.json"
        ),
        "sha256": "204b5d34f0e537d6174a2ef2e828e63134ab0f40263ec2518f25a5737e2bbab0",
        "size_bytes": 117263,
    },
    {
        "format_version": "ANNUAL_2025_FINANCIAL_INSTRUMENTS_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": (
            "docs/experiments/"
            "E-0154-annual-2025-financial-instruments-8bank-codex-verified-mapping-v1.json"
        ),
        "sha256": "fad1524be804e2c620446d104454d1f0c3c8f4598c6053a6a2592d287c0a59d2",
        "size_bytes": 86133,
    },
]


def _historical_oracles() -> list[tuple[dict[str, Any], dict[str, Any]]]:
    result = []
    for reference in PINNED_HISTORICAL_ORACLES:
        path = ROOT / reference["path"]
        value = _json(path)
        payload = path.read_bytes()
        if (
            sha256(payload).hexdigest() != reference["sha256"]
            or len(payload) != reference["size_bytes"]
            or value.get("format_version") != reference["format_version"]
            or type(value.get("trials")) is not list
            or len(value["trials"]) != 8
        ):
            raise _error("Family47 historical oracle drifted")
        result.append((dict(reference), value))
    return result


def _historical_axes(
    trials: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    by_source = {trial["source_sha256"]: trial for trial in trials}
    if len(by_source) != len(trials):
        raise _error("Family47 current trial source axis is ambiguous")
    documents = []
    mappings = []
    oracle_refs = []
    for oracle_ref, oracle in _historical_oracles():
        oracle_refs.append(oracle_ref)
        for oracle_trial in oracle["trials"]:
            source_sha256 = oracle_trial.get("source_pdf_sha256")
            trial = by_source.get(source_sha256)
            historical = oracle_trial.get("verified_mappings")
            if trial is None or type(historical) is not list:
                raise _error("Family47 historical source does not join one current trial")
            candidate = trial["candidates"][0] if len(trial["candidates"]) == 1 else None
            current_by_id = (
                {mapping["report_norm_id"]: mapping for mapping in candidate.get("mappings", [])}
                if type(candidate) is dict
                else {}
            )
            if historical:
                disposition = "EXACT" if trial["status"] == READY else "CURRENT_UNRESOLVED"
            elif trial["status"] == NOT_OBSERVED:
                disposition = "EXACT_LEGACY_DETAILED_TABLE_ABSENCE"
            elif trial["status"] == READY:
                disposition = "AUTHENTICATED_GEMINI_TABLE_SUPERSEDES_LEGACY_ABSENCE"
            else:
                disposition = "CURRENT_UNRESOLVED"
            documents.append(
                {
                    "current_document_ordinal": trial["document_ordinal"],
                    "current_status": trial["status"],
                    "disposition": disposition,
                    "document_provenance": oracle_trial.get("document_provenance"),
                    "historical_mapping_count": len(historical),
                    "historical_status": oracle_trial.get("status"),
                    "oracle_format_version": oracle["format_version"],
                    "source_sha256": source_sha256,
                }
            )
            for historical_mapping in historical:
                binding = historical_mapping.get("schema_binding")
                report_norm_id = binding.get("report_norm_id") if type(binding) is dict else None
                historical_values = historical_mapping.get("values")
                current = current_by_id.get(report_norm_id)
                if type(report_norm_id) is not int or type(historical_values) is not list:
                    raise _error("Family47 historical mapping axis is invalid")
                historical_axis = [
                    {
                        "axis_role": value["axis_role"],
                        "coefficient": value["normalized_value"],
                    }
                    for value in historical_values
                ]
                current_axis = (
                    [
                        {
                            "axis_role": value["axis_role"],
                            "coefficient": value["coefficient"],
                        }
                        for value in current["values"]
                        if value["period_role"] == "CURRENT_PERIOD"
                    ]
                    if type(current) is dict
                    else []
                )
                exact = (
                    type(current) is dict
                    and current.get("role") == historical_mapping.get("role")
                    and same_typed_json_v1(current_axis, historical_axis)
                )
                mappings.append(
                    {
                        "current_axis": current_axis,
                        "current_role": current.get("role") if type(current) is dict else None,
                        "current_status": trial["status"],
                        "disposition": "EXACT" if exact else "MISMATCH",
                        "document_provenance": oracle_trial.get("document_provenance"),
                        "historical_axis": historical_axis,
                        "historical_report_norm_id": report_norm_id,
                        "historical_role": historical_mapping.get("role"),
                        "oracle_format_version": oracle["format_version"],
                        "source_sha256": source_sha256,
                    }
                )
    return documents, mappings, oracle_refs


def _audit_axes(
    trials: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    clusters = []
    equations = []
    mappings = []
    table_receipts = []
    unavailable_fair_values = []
    unresolved_documents = []
    for trial in trials:
        document = {
            "document_ordinal": trial["document_ordinal"],
            "source_logical_name": trial["source_logical_name"],
            "source_sha256": trial["source_sha256"],
        }
        if trial["status"] == NOT_OBSERVED:
            continue
        candidate = trial["candidates"][0] if len(trial["candidates"]) == 1 else None
        if trial["status"] != READY or type(candidate) is not dict:
            unresolved_documents.append(
                {
                    **document,
                    "candidate_id": candidate.get("candidate_id") if candidate else None,
                    "reasons": trial["reasons"],
                }
            )
            continue
        closure = candidate["closure_receipt"]
        clusters.append(
            {
                **document,
                "candidate_id": candidate["candidate_id"],
                "component_regions": candidate["component_regions"],
                "period_assignments": closure["period_assignments"],
                "unit_receipt": closure["unit_receipt"],
            }
        )
        for mapping in candidate["mappings"]:
            mappings.append({**document, "mapping": mapping})
        for equation in closure["equations"]:
            equations.append({**document, "equation": equation})
        for receipt in closure["table_receipts"]:
            table_receipts.append({**document, "table_receipt": receipt})
            for row in receipt["resolved_rows"]:
                fair = row["fair_value_cell"]
                if type(fair) is dict and fair["state"] == "SOURCE_EXPLICIT_FAIR_VALUE_UNAVAILABLE":
                    unavailable_fair_values.append(
                        {
                            **document,
                            "branch": row["branch"],
                            "cell_ref": fair["cell_ref"],
                            "role": row["role"],
                            "source_text": fair["source_text"],
                        }
                    )
    historical_documents, historical_mappings, oracle_refs = _historical_axes(trials)
    return {
        "clusters": clusters,
        "equations": equations,
        "historical_documents": historical_documents,
        "historical_mappings": historical_mappings,
        "mappings": mappings,
        "table_receipts": table_receipts,
        "unavailable_fair_values": unavailable_fair_values,
        "unresolved_documents": unresolved_documents,
    }, oracle_refs


def build_financial_instruments_experimental_audit_v1(
    *,
    sweep: Mapping[str, Any],
    sweep_output: Path,
    selected_page_json_version_ids: Sequence[str],
    indexed_query_evidence: Mapping[str, Any],
    trials: Sequence[Mapping[str, Any]],
    spec_refs: Mapping[str, Any],
) -> dict[str, Any]:
    axes, oracle_refs = _audit_axes(trials)
    axis_counts = {name: len(axis) for name, axis in axes.items()}
    axis_sha256 = {name: canonical_json_sha256_v1(axis) for name, axis in axes.items()}
    audit_metrics = {
        "equation_count": axis_counts["equations"],
        "historical_exact_mapping_count": sum(
            item["disposition"] == "EXACT" for item in axes["historical_mappings"]
        ),
        "historical_mapping_mismatch_count": sum(
            item["disposition"] != "EXACT" for item in axes["historical_mappings"]
        ),
        "legacy_absence_superseded_count": sum(
            item["disposition"] == "AUTHENTICATED_GEMINI_TABLE_SUPERSEDES_LEGACY_ABSENCE"
            for item in axes["historical_documents"]
        ),
        "mapping_count": axis_counts["mappings"],
        "table_receipt_count": axis_counts["table_receipts"],
        "unavailable_fair_value_count": axis_counts["unavailable_fair_values"],
        "unresolved_document_count": axis_counts["unresolved_documents"],
    }
    sweep_payload = canonical_json_bytes_v1(sweep)
    material = {
        "axes": axes,
        "axis_counts": axis_counts,
        "axis_sha256": axis_sha256,
        "audit_metrics": audit_metrics,
        "claim_boundary": (
            "AUTHENTICATED_SELECTED_GEMINI_JSON_SQLITE_CANDIDATE_REPLAY_EXACT_"
            "BOOK_FAIR_GRAPH_AND_HISTORICAL_VALUE_COMPARATOR_ONLY_NO_PROVIDER_"
            "NO_GEOMETRY_NO_CANONICAL_EXPORT_AUTHORITY"
        ),
        "format_version": AUDIT_FORMAT_VERSION,
        "historical_oracle_refs": oracle_refs,
        "query_evidence_id": indexed_query_evidence["query_evidence_id"],
        "query_receipt": indexed_query_evidence["query_receipt"],
        "selected_page_json_frontier_sha256": canonical_json_sha256_v1(
            list(selected_page_json_version_ids)
        ),
        "spec_refs": dict(spec_refs),
        "state": "EXPERIMENTAL_AUDIT_COMPLETE",
        "sweep_ref": {
            "path": sweep_output.name,
            "sha256": sha256(sweep_payload).hexdigest(),
            "size_bytes": len(sweep_payload),
            "sweep_id": sweep["sweep_id"],
        },
    }
    return {
        **material,
        "audit_id": "gjfieav1:audit:" + canonical_json_sha256_v1(material),
    }


def validate_financial_instruments_experimental_audit_content_v1(
    value: Any,
) -> dict[str, Any]:
    fields = {
        "audit_id",
        "axes",
        "axis_counts",
        "axis_sha256",
        "audit_metrics",
        "claim_boundary",
        "format_version",
        "historical_oracle_refs",
        "query_evidence_id",
        "query_receipt",
        "selected_page_json_frontier_sha256",
        "spec_refs",
        "state",
        "sweep_ref",
    }
    axis_names = {
        "clusters",
        "equations",
        "historical_documents",
        "historical_mappings",
        "mappings",
        "table_receipts",
        "unavailable_fair_values",
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
        raise _error("Family47 experimental audit shape drifted")
    counts = {name: len(axis) for name, axis in value["axes"].items()}
    hashes = {name: canonical_json_sha256_v1(axis) for name, axis in value["axes"].items()}
    material = {key: value[key] for key in fields - {"audit_id"}}
    if (
        value.get("axis_counts") != counts
        or value.get("axis_sha256") != hashes
        or value.get("audit_id") != "gjfieav1:audit:" + canonical_json_sha256_v1(material)
    ):
        raise _error("Family47 experimental audit seal drifted")
    return json.loads(canonical_json_bytes_v1(value))


def validate_financial_instruments_experimental_audit_replay_v1(
    value: Any,
    *,
    database: Path,
    sweep: Mapping[str, Any],
    sweep_output: Path,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
    spec_refs: Mapping[str, Any],
) -> dict[str, Any]:
    checked_sweep = validate_gemini_json_flat_family_sweep_v1(sweep)
    embedded = compile_gemini_json_flat_family_specs_v1(
        checked_sweep["specs"]["topology"]["value"],
        checked_sweep["specs"]["evaluation"]["value"],
        checked_sweep["specs"]["schema_binding"]["value"],
    )
    if not same_typed_json_v1(embedded, compiled_specs):
        raise _error("Family47 embedded and caller compiled specs differ")
    validate_selected_equity_matrix_family_candidate_replays_v1(
        database,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=embedded,
        indexed_query_evidence=checked_sweep["indexed_query_evidence"],
        trials=checked_sweep["trials"],
    )
    expected = build_financial_instruments_experimental_audit_v1(
        sweep=checked_sweep,
        sweep_output=sweep_output,
        selected_page_json_version_ids=selected_page_json_version_ids,
        indexed_query_evidence=checked_sweep["indexed_query_evidence"],
        trials=checked_sweep["trials"],
        spec_refs=spec_refs,
    )
    validate_financial_instruments_experimental_audit_content_v1(value)
    if not same_typed_json_v1(value, expected):
        raise _error("Family47 experimental audit does not replay exactly")
    return expected


def _assert_release_pins(
    *,
    index: Mapping[str, Any],
    selected_ids: Sequence[str],
    sweep: Mapping[str, Any],
    indexed: Mapping[str, Any],
    audit: Mapping[str, Any],
) -> None:
    actual = {
        "audit_metrics": audit["audit_metrics"],
        "axis_counts": audit["axis_counts"],
        "axis_sha256": audit["axis_sha256"],
        "corpus_manifest_index_id": index["corpus_manifest_index_id"],
        "query_receipt": indexed["query_receipt"],
        "selected_page_json_frontier_sha256": canonical_json_sha256_v1(list(selected_ids)),
        "sweep_metrics": sweep["metrics"],
    }
    if (
        actual["corpus_manifest_index_id"] != PINNED_CORPUS_MANIFEST_INDEX_ID
        or actual["selected_page_json_frontier_sha256"] != PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256
        or not same_typed_json_v1(actual["sweep_metrics"], PINNED_RELEASE_METRICS)
        or not same_typed_json_v1(actual["query_receipt"], PINNED_QUERY_RECEIPT)
        or not same_typed_json_v1(actual["audit_metrics"], PINNED_AUDIT_METRICS)
        or actual["axis_counts"] != PINNED_AXIS_COUNTS
        or actual["axis_sha256"] != PINNED_AXIS_SHA256
    ):
        raise _error(
            "Family47 frozen corpus release pins drifted; actual="
            + json.dumps(actual, ensure_ascii=False, sort_keys=True)
        )


def run(args: argparse.Namespace) -> dict[str, Any]:
    index = validate_current_corpus_manifest_index_v1(_json(args.corpus_index))
    artifact_root = args.artifact_root.resolve()
    source_database = _content_ref(artifact_root, index["database_ref"])
    selected_ids = _selected_page_axis(index=index, artifact_root=artifact_root)
    topology = _json(args.topology_spec)
    evaluation = _json(args.evaluation_spec)
    schema = _json(args.schema_binding_spec)
    compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
    if compiled.get("family_id") != "FINANCIAL_INSTRUMENTS":
        raise _error("Family47 runner received a different family triplet")
    spec_refs = {
        "evaluation": _file_ref(args.evaluation_spec, root=ROOT),
        "schema_binding": _file_ref(args.schema_binding_spec, root=ROOT),
        "topology": _file_ref(args.topology_spec, root=ROOT),
    }
    with _authenticated_sqlite_snapshot(
        source_database, reference=index["database_ref"]
    ) as database_guard:
        database = database_guard.path
        indexed = query_selected_equity_matrix_family_regions_v1(
            database,
            selected_page_json_version_ids=selected_ids,
            compiled_specs=compiled,
        )
        validate_selected_equity_matrix_family_query_evidence_v1(
            database,
            selected_page_json_version_ids=selected_ids,
            compiled_specs=compiled,
            indexed_query_evidence=indexed,
        )
        pages = _load_selected_pages_by_document(
            database,
            selected_ids=selected_ids,
            selected_page_axis=indexed["selected_page_axis"],
        )
        candidates = {}
        for cluster in indexed["accepted_clusters"]:
            regions = cluster["component_regions"]
            candidates[cluster["document_ordinal"]] = (
                evaluate_gemini_json_equity_matrix_family_cluster_v1(
                    regions=regions,
                    page_json_by_version=pages[cluster["document_ordinal"]],
                    compiled_specs=compiled,
                    query_receipt=build_gemini_json_equity_matrix_region_query_receipt_v1(
                        regions, owner_receipt=cluster["owner_receipt"]
                    ),
                    document_unit_context_evidence=cluster["document_unit_context_evidence"],
                )
            )
        trials = _trials(indexed=indexed, candidates_by_ordinal=candidates)
        sweep = build_gemini_json_flat_family_sweep_v1(
            corpus_manifest_index_id=index["corpus_manifest_index_id"],
            topology_spec=topology,
            evaluation_spec=evaluation,
            schema_binding_spec=schema,
            trials=trials,
            indexed_query_evidence=indexed,
        )
        validate_gemini_json_flat_family_sweep_v1(sweep)
        validate_selected_equity_matrix_family_candidate_replays_v1(
            database,
            selected_page_json_version_ids=selected_ids,
            compiled_specs=compiled,
            indexed_query_evidence=indexed,
            trials=trials,
        )
        audit = build_financial_instruments_experimental_audit_v1(
            sweep=sweep,
            sweep_output=args.output,
            selected_page_json_version_ids=selected_ids,
            indexed_query_evidence=indexed,
            trials=trials,
            spec_refs=spec_refs,
        )
        validate_financial_instruments_experimental_audit_replay_v1(
            audit,
            database=database,
            sweep=sweep,
            sweep_output=args.output,
            selected_page_json_version_ids=selected_ids,
            compiled_specs=compiled,
            spec_refs=spec_refs,
        )
        _assert_release_pins(
            index=index,
            selected_ids=selected_ids,
            sweep=sweep,
            indexed=indexed,
            audit=audit,
        )
        database_guard.validate()
        audit_output = args.output.with_suffix(".audit.json")
        _write_once(args.output, sweep)
        _write_once(audit_output, audit)
        implementation_paths = (
            ROOT / "scripts/experiments/run_gemini_json_financial_instruments_family_v1.py",
            ROOT / "scripts/experiments/run_gemini_json_equity_matrix_accounting_family_v1.py",
            ROOT / "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
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
        if not same_typed_json_v1(
            load_gemini_accounting_family_sweep_v1(args.results_database, stored["family_run_id"]),
            sweep,
        ):
            raise _error("stored Family47 sweep differs from authenticated evaluation")
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
    result = run(_parser().parse_args())
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
