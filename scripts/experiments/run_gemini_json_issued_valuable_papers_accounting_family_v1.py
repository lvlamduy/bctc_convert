#!/usr/bin/env python3
"""Run issued valuable papers over one authenticated selected-JSON corpus."""

from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts/experiments") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts/experiments"))

import run_gemini_json_multitable_hierarchical_accounting_family_v1 as generic  # noqa: E402

from bctc_ai.evaluation.gemini_json_first_page_render_v1 import (  # noqa: E402
    render_full_pdf_page_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    build_gemini_json_flat_family_sweep_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.evaluation.gemini_json_issued_valuable_papers_family_v1 import (  # noqa: E402
    adapt_gemini_json_issued_valuable_papers_indexed_query_evidence_v1,
    bind_gemini_json_issued_valuable_papers_source_repairs_v1,
    build_gemini_json_issued_valuable_papers_region_query_receipt_v1,
    compile_gemini_json_issued_valuable_papers_family_specs_v1,
    evaluate_gemini_json_issued_valuable_papers_family_cluster_v1,
    validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (  # noqa: E402
    READY,
)
from bctc_ai.evaluation.historical_comparator_policy_v1 import (  # noqa: E402
    DISJOINT_EXPANSION,
    EXACT_HISTORICAL_COMPARISON,
    NOT_APPLICABLE_DISJOINT_CORPUS,
    STRICT_RELEASE,
    audit_historical_comparator_policy_v1,
)
from bctc_ai.evaluation.historical_comparator_policy_v1 import (  # noqa: E402
    FORMAT_VERSION as HISTORICAL_COMPARATOR_POLICY_FORMAT_VERSION,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (  # noqa: E402
    validate_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_clone_v1,
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
    query_selected_multitable_hierarchical_family_regions_v1,
)


class RunGeminiJsonIssuedValuablePapersAccountingFamilyV1Error(RuntimeError):
    """The authenticated corpus, policy, result, or replay boundary drifted."""


def _error(message: str) -> RunGeminiJsonIssuedValuablePapersAccountingFamilyV1Error:
    return RunGeminiJsonIssuedValuablePapersAccountingFamilyV1Error(message)


AUDIT_FORMAT_VERSION = "GEMINI_JSON_ISSUED_VALUABLE_PAPERS_EXPERIMENTAL_AUDIT_V1"
FAMILY_ID = "ISSUED_VALUABLE_PAPERS"
PINNED_HISTORICAL_ORACLES = generic.PINNED_ISSUED_VALUABLE_PAPERS_HISTORICAL_ORACLES
PINNED_HISTORICAL_ORACLE_TRIAL_COUNT = 8
SOURCE_REPAIR_SPEC_PATH = (
    ROOT
    / "data/registered/gemini_json_issued_valuable_papers_source_repairs_v1.json"
)


def _authenticate_source_repairs_v1(
    *, repairs: list[dict[str, Any]], source_pdf_root: Path
) -> list[dict[str, Any]]:
    """Replay every registered full-page render and RGB crop binding."""

    root = source_pdf_root.resolve()
    source_payloads: dict[tuple[str, str, int], bytes] = {}
    render_cache: dict[tuple[str, int], tuple[bytes, dict[str, Any]]] = {}
    checked = []
    for repair in repairs:
        source = repair["source"]
        locator = repair["locator"]
        logical_name = source["source_logical_name"]
        path = (root / logical_name).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise _error("issued-paper repair source path is unavailable")
        source_key = (
            logical_name,
            source["source_sha256"],
            source["source_size_bytes"],
        )
        payload = source_payloads.get(source_key)
        if payload is None:
            payload = path.read_bytes()
            if (
                len(payload) != source["source_size_bytes"]
                or sha256(payload).hexdigest() != source["source_sha256"]
            ):
                raise _error("issued-paper repair source artifact drifted")
            source_payloads[source_key] = payload
        cache_key = (logical_name, locator["physical_page"])
        cached = render_cache.get(cache_key)
        if cached is None:
            with fitz.open(stream=payload, filetype="pdf") as document:
                if locator["physical_page"] > len(document):
                    raise _error("issued-paper repair physical page is outside its PDF")
                rendered = render_full_pdf_page_v1(
                    document[locator["physical_page"] - 1],
                    physical_page=locator["physical_page"],
                    dpi=300,
                    source_sha256=source["source_sha256"],
                )
            cached = rendered.image, rendered.receipt
            render_cache[cache_key] = cached
        image_bytes, render_receipt = cached
        expected_render = repair["render"]
        with Image.open(BytesIO(image_bytes)) as image:
            image.load()
            rgb = image.convert("RGB")
            bbox = repair["crop_evidence"]["bbox_pixels_xyxy"]
            crop = rgb.crop(tuple(bbox))
            actual_render = {
                "image_sha256": sha256(image_bytes).hexdigest(),
                "image_size_bytes": len(image_bytes),
                "media_type": "image/png",
                "physical_page": locator["physical_page"],
                "pixel_height": rgb.height,
                "pixel_width": rgb.width,
                "render_dpi": 300,
                "render_receipt_sha256": canonical_json_sha256_v1(render_receipt),
            }
            actual_crop = {
                "bbox_pixels_xyxy": bbox,
                "pixel_height": crop.height,
                "pixel_width": crop.width,
                "rgb_sha256": sha256(crop.tobytes()).hexdigest(),
            }
        if actual_render != expected_render or actual_crop != repair["crop_evidence"]:
            raise _error("issued-paper repair render or crop evidence drifted")
        checked.append(canonical_clone_v1(repair))
    return checked


def replay_issued_valuable_papers_trials_from_source_v1(
    *,
    source_page_database: Path,
    selected_page_json_version_ids: tuple[str, ...],
    compiled_specs: dict[str, Any],
    indexed_query_evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    """Re-query, evaluate, and replay the complete Family-25 trial axis."""

    source_repairs = generic._json(SOURCE_REPAIR_SPEC_PATH)
    family_compiled = bind_gemini_json_issued_valuable_papers_source_repairs_v1(
        compiled_specs,
        source_repairs,
    )
    raw_indexed = query_selected_multitable_hierarchical_family_regions_v1(
        source_page_database,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=family_compiled,
    )
    page_json_by_document = generic._load_selected_pages_by_document(
        source_page_database,
        selected_ids=list(selected_page_json_version_ids),
        selected_page_axis=raw_indexed["selected_page_axis"],
    )
    adapted_indexed, _receipts = (
        adapt_gemini_json_issued_valuable_papers_indexed_query_evidence_v1(
            raw_indexed,
            page_json_by_document=page_json_by_document,
            compiled_specs=family_compiled,
        )
    )
    if not same_typed_json_v1(adapted_indexed, indexed_query_evidence):
        raise _error(
            "issued-paper source replay rebuilt different indexed query evidence"
        )

    candidates_by_ordinal = {}
    for cluster in adapted_indexed["accepted_clusters"]:
        ordinal = cluster["document_ordinal"]
        regions = cluster["component_regions"]
        candidate = evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(
            regions=regions,
            page_json_by_version=page_json_by_document[ordinal],
            compiled_specs=family_compiled,
            query_receipt=(
                build_gemini_json_issued_valuable_papers_region_query_receipt_v1(
                    regions
                )
            ),
        )
        candidates_by_ordinal[ordinal] = (
            validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(
                candidate,
                regions=regions,
                page_json_by_version=page_json_by_document[ordinal],
                compiled_specs=family_compiled,
                query_receipt=(
                    build_gemini_json_issued_valuable_papers_region_query_receipt_v1(
                        regions
                    )
                ),
            )
        )
    return generic._trials(
        indexed=adapted_indexed,
        candidates_by_ordinal=candidates_by_ordinal,
    )


def _normalised_historical_oracle_rows(
    *, compiled_specs: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    refs: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for oracle_ref_index, (reference, oracle) in enumerate(
        generic._historical_oracles(compiled_specs=compiled_specs)
    ):
        trials = oracle.get("trials")
        if type(trials) is not list or not trials:
            raise _error("issued-paper historical oracle trial axis is absent")
        refs.append({**reference, "expected_trial_count": len(trials)})
        for trial in trials:
            if type(trial) is not dict:
                raise _error("issued-paper historical oracle trial is invalid")
            source_sha256 = trial.get("source_pdf_sha256")
            if type(source_sha256) is not str:
                raise _error("issued-paper historical oracle source identity is absent")
            rows.append(
                {
                    "oracle_ref_index": oracle_ref_index,
                    "source_sha256": source_sha256,
                }
            )
    return refs, rows


def _semantic_axes(*, trials: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    mappings: list[dict[str, Any]] = []
    equations: list[dict[str, Any]] = []
    clusters: list[dict[str, Any]] = []
    residual_trials: list[dict[str, Any]] = []
    source_only_rows: list[dict[str, Any]] = []
    for trial in trials:
        candidates = trial.get("candidates")
        if trial.get("status") != READY or type(candidates) is not list or len(candidates) != 1:
            residual_trials.append(
                {
                    "document_ordinal": trial["document_ordinal"],
                    "reasons": canonical_clone_v1(trial["reasons"]),
                    "source_logical_name": trial["source_logical_name"],
                    "source_sha256": trial["source_sha256"],
                    "status": trial["status"],
                }
            )
            continue
        candidate = candidates[0]
        document = {
            "document_ordinal": trial["document_ordinal"],
            "source_logical_name": trial["source_logical_name"],
            "source_sha256": trial["source_sha256"],
        }
        clusters.append(
            {
                **document,
                "component_regions": candidate["component_regions"],
                "query_receipt_sha256": canonical_json_sha256_v1(
                    candidate["closure_receipt"]["query_receipt"]
                ),
            }
        )
        for mapping in candidate["mappings"]:
            record = {
                **document,
                "coefficients": [value["coefficient"] for value in mapping["values"]],
                "report_norm_id": mapping["report_norm_id"],
                "role": mapping["role"],
                "row_id": mapping["row_id"],
                "states": [value["state"] for value in mapping["values"]],
                "unit": mapping["unit"],
            }
            decimal_cells = [
                value
                for value in mapping["values"]
                if "decimal_scale" in value or "normalized_decimal" in value
            ]
            if decimal_cells:
                if len(decimal_cells) != len(mapping["values"]):
                    raise _error("issued-paper decimal mapping axis is incomplete")
                record.update(
                    {
                        "decimal_scales": [value["decimal_scale"] for value in decimal_cells],
                        "normalized_decimals": [
                            value["normalized_decimal"] for value in decimal_cells
                        ],
                    }
                )
            mappings.append(record)
        for equation in candidate["closure_receipt"]["equations"]:
            equations.append({**document, "equation": equation})
        for source_only in candidate["closure_receipt"].get(
            "source_only_unmapped_rows", []
        ):
            source_only_rows.append(
                {**document, "source_only_row": canonical_clone_v1(source_only)}
            )
    return {
        "clusters": clusters,
        "equations": equations,
        "mappings": mappings,
        "residual_trials": residual_trials,
        "source_only_rows": source_only_rows,
    }


def _historical_comparator(
    *,
    policy: str,
    index: dict[str, Any],
    selected_page_json_version_ids: list[str],
    indexed_query_evidence: dict[str, Any],
    trials: list[dict[str, Any]],
    compiled_specs: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    refs, oracle_rows = _normalised_historical_oracle_rows(compiled_specs=compiled_specs)
    comparator: list[dict[str, Any]] = []
    records_by_source: dict[str, list[dict[str, Any]]] = {}
    if policy == STRICT_RELEASE:
        comparator, legacy_refs = generic._historical_comparator_axis(
            trials=trials, compiled_specs=compiled_specs
        )
        if legacy_refs != [
            {key: ref[key] for key in ref if key != "expected_trial_count"} for ref in refs
        ]:
            raise _error("issued-paper historical oracle references disagree")
        for record in comparator:
            source_sha256 = record.get("source_sha256")
            if type(source_sha256) is not str:
                raise _error("issued-paper historical comparator source is absent")
            records_by_source.setdefault(source_sha256, []).append(record)
        if not comparator or any(record.get("disposition") != "EXACT" for record in comparator):
            raise _error("issued-paper strict historical comparison is not exact")

    source_by_ordinal = {
        document["document_ordinal"]: document["source_sha256"]
        for document in indexed_query_evidence["selected_document_axis"]
    }
    candidate_sources = [
        source_by_ordinal[cluster["document_ordinal"]]
        for cluster in indexed_query_evidence["accepted_clusters"]
    ]
    replay_sources = [trial["source_sha256"] for trial in trials if trial["candidates"]]
    if len(candidate_sources) != len(replay_sources) or set(candidate_sources) != set(
        replay_sources
    ):
        raise _error("issued-paper indexed candidate/replay axes drifted")

    def strict_compare(oracle_row: dict[str, Any], current_trial: dict[str, Any]) -> dict[str, Any]:
        source_sha256 = oracle_row["source_sha256"]
        records = records_by_source.get(source_sha256)
        if (
            current_trial.get("source_sha256") != source_sha256
            or not records
            or any(record.get("disposition") != "EXACT" for record in records)
        ):
            return {"disposition": "MISMATCH"}
        return {
            "axis_sha256": canonical_json_sha256_v1(records),
            "disposition": EXACT_HISTORICAL_COMPARISON,
            "record_count": len(records),
        }

    receipt = audit_historical_comparator_policy_v1(
        policy=policy,
        pinned_oracle_refs=refs,
        normalized_oracle_rows=oracle_rows,
        current_manifest_index_id=index["corpus_manifest_index_id"],
        current_manifest_source_sha256s=[
            document["source_sha256"] for document in index["documents"]
        ],
        current_manifest_page_json_version_ids=selected_page_json_version_ids,
        current_trials=trials,
        current_candidate_source_sha256s=candidate_sources,
        current_replay_source_sha256s=replay_sources,
        current_selected_page_json_version_ids=selected_page_json_version_ids,
        strict_compare=strict_compare if policy == STRICT_RELEASE else None,
    )
    return comparator, receipt


def build_issued_valuable_papers_experimental_audit_v1(
    *,
    sweep: dict[str, Any],
    sweep_output: Path,
    historical_comparator_policy: str,
    index: dict[str, Any],
    selected_page_json_version_ids: list[str],
    indexed_query_evidence: dict[str, Any],
    query_recovery_receipts: list[dict[str, Any]],
    source_repair_authentication: list[dict[str, Any]],
    source_observation_contract: dict[str, Any],
    trials: list[dict[str, Any]],
    compiled_specs: dict[str, Any],
    spec_refs: dict[str, Any],
) -> dict[str, Any]:
    """Seal semantic axes and the authenticated historical-corpus relation."""

    if sweep.get("corpus_manifest_index_id") != index.get("corpus_manifest_index_id"):
        raise _error("issued-paper sweep/current manifest identity drifted")
    axes = _semantic_axes(trials=trials)
    axes["query_recoveries"] = canonical_clone_v1(query_recovery_receipts)
    axes["source_repairs"] = canonical_clone_v1(source_repair_authentication)
    comparator, policy_receipt = _historical_comparator(
        policy=historical_comparator_policy,
        index=index,
        selected_page_json_version_ids=selected_page_json_version_ids,
        indexed_query_evidence=indexed_query_evidence,
        trials=trials,
        compiled_specs=compiled_specs,
    )
    axes["historical_comparator"] = comparator
    axis_counts = {name: len(axis) for name, axis in axes.items()}
    axis_sha256 = {name: canonical_json_sha256_v1(axis) for name, axis in axes.items()}
    sweep_payload = canonical_json_bytes_v1(sweep)
    material = {
        "axes": axes,
        "axis_counts": axis_counts,
        "axis_sha256": axis_sha256,
        "audit_metrics": {
            "equation_count": axis_counts["equations"],
            "historical_comparator_exact_count": (
                sum(record["disposition"] == "EXACT" for record in comparator)
                if historical_comparator_policy == STRICT_RELEASE
                else None
            ),
            "mapping_count": axis_counts["mappings"],
            "residual_trial_count": axis_counts["residual_trials"],
            "source_repair_count": axis_counts["source_repairs"],
            "source_only_row_count": axis_counts["source_only_rows"],
        },
        "claim_boundary": (
            "AUTHENTICATED_SELECTED_GEMINI_JSON_SQLITE_REPLAY_RESIDUAL_AND_SOURCE_ONLY_"
            "INVENTORY_AND_HISTORICAL_ROLE_VALUE_COMPARATOR_ONLY_NO_PROVIDER_NO_"
            "GEOMETRY_NO_CANONICAL_EXPORT_AUTHORITY"
        ),
        "format_version": AUDIT_FORMAT_VERSION,
        "historical_comparator_policy_receipt": policy_receipt,
        "query_evidence_id": indexed_query_evidence["query_evidence_id"],
        "query_receipt": indexed_query_evidence["query_receipt"],
        "selected_page_json_frontier_sha256": canonical_json_sha256_v1(
            selected_page_json_version_ids
        ),
        "source_observation_contract": canonical_clone_v1(source_observation_contract),
        "spec_refs": canonical_clone_v1(spec_refs),
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
        "audit_id": "gjivpfeav1:audit:" + canonical_json_sha256_v1(material),
    }


def validate_issued_valuable_papers_experimental_audit_content_v1(
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
        "historical_comparator_policy_receipt",
        "query_evidence_id",
        "query_receipt",
        "selected_page_json_frontier_sha256",
        "source_observation_contract",
        "spec_refs",
        "state",
        "sweep_ref",
    }
    axis_names = {
        "clusters",
        "equations",
        "historical_comparator",
        "mappings",
        "query_recoveries",
        "residual_trials",
        "source_repairs",
        "source_only_rows",
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
        raise _error("issued-paper experimental audit shape drifted")
    counts = {name: len(axis) for name, axis in value["axes"].items()}
    hashes = {name: canonical_json_sha256_v1(axis) for name, axis in value["axes"].items()}
    if value.get("axis_counts") != counts or value.get("axis_sha256") != hashes:
        raise _error("issued-paper experimental audit axis seal drifted")
    receipt = value.get("historical_comparator_policy_receipt")
    policy = receipt.get("policy") if type(receipt) is dict else None
    disposition = receipt.get("disposition") if type(receipt) is dict else None
    comparator = value["axes"]["historical_comparator"]
    metrics = value.get("audit_metrics")
    query_receipt = value.get("query_receipt")
    current_axis = receipt.get("current_axis_validation") if type(receipt) is dict else None
    oracle_authentication = receipt.get("oracle_authentication") if type(receipt) is dict else None
    observation_contract = value.get("source_observation_contract")
    expected_oracle_refs = [
        {**reference, "expected_trial_count": PINNED_HISTORICAL_ORACLE_TRIAL_COUNT}
        for reference in PINNED_HISTORICAL_ORACLES
    ]
    if (
        type(receipt) is not dict
        or receipt.get("format_version") != HISTORICAL_COMPARATOR_POLICY_FORMAT_VERSION
        or policy not in {STRICT_RELEASE, DISJOINT_EXPANSION}
        or type(metrics) is not dict
        or type(query_receipt) is not dict
        or type(current_axis) is not dict
        or type(oracle_authentication) is not dict
        or type(observation_contract) is not dict
        or observation_contract.get("status") != "PASS"
        or observation_contract.get("violation_count") != 0
        or oracle_authentication.get("refs") != expected_oracle_refs
        or oracle_authentication.get("artifact_count") != len(expected_oracle_refs)
        or oracle_authentication.get("source_count")
        != len(expected_oracle_refs) * PINNED_HISTORICAL_ORACLE_TRIAL_COUNT
        or current_axis.get("manifest_document_count")
        != query_receipt.get("selected_document_count")
        or current_axis.get("trial_source_count") != query_receipt.get("selected_document_count")
        or current_axis.get("candidate_source_count") != query_receipt.get("accepted_cluster_count")
        or current_axis.get("replay_source_count") != query_receipt.get("accepted_cluster_count")
        or current_axis.get("selected_page_json_version_count")
        != query_receipt.get("selected_page_count")
        or metrics.get("mapping_count") != counts["mappings"]
        or metrics.get("equation_count") != counts["equations"]
        or metrics.get("residual_trial_count") != counts["residual_trials"]
        or metrics.get("source_repair_count") != counts["source_repairs"]
        or metrics.get("source_only_row_count") != counts["source_only_rows"]
    ):
        raise _error("issued-paper historical comparator policy receipt drifted")
    if policy == STRICT_RELEASE:
        if (
            disposition != EXACT_HISTORICAL_COMPARISON
            or not comparator
            or metrics.get("historical_comparator_exact_count") != len(comparator)
            or any(record.get("disposition") != "EXACT" for record in comparator)
        ):
            raise _error("issued-paper strict comparator audit drifted")
    elif (
        disposition != NOT_APPLICABLE_DISJOINT_CORPUS
        or comparator
        or receipt.get("comparison_axis") != []
        or receipt.get("corpus_relation", {}).get("overlap_count") != 0
        or metrics.get("historical_comparator_exact_count") is not None
    ):
        raise _error("issued-paper disjoint comparator audit drifted")
    material = {key: value[key] for key in fields - {"audit_id"}}
    if value.get("audit_id") != "gjivpfeav1:audit:" + canonical_json_sha256_v1(material):
        raise _error("issued-paper experimental audit identity drifted")
    return json.loads(canonical_json_bytes_v1(value))


def _run_with_authenticated_database(
    args: argparse.Namespace,
    *,
    index: dict[str, Any],
    database_guard: Any,
    selected_ids: list[str],
    topology: dict[str, Any],
    evaluation: dict[str, Any],
    schema: dict[str, Any],
    compiled: dict[str, Any],
    spec_refs: dict[str, Any],
    source_repair_authentication: list[dict[str, Any]],
) -> dict[str, Any]:
    database = database_guard.path
    indexed = query_selected_multitable_hierarchical_family_regions_v1(
        database, selected_page_json_version_ids=selected_ids, compiled_specs=compiled
    )
    page_json_by_document = generic._load_selected_pages_by_document(
        database,
        selected_ids=selected_ids,
        selected_page_axis=indexed["selected_page_axis"],
    )
    indexed, query_recovery_receipts = (
        adapt_gemini_json_issued_valuable_papers_indexed_query_evidence_v1(
            indexed,
            page_json_by_document=page_json_by_document,
            compiled_specs=compiled,
        )
    )
    candidates_by_ordinal = {}
    for cluster in indexed["accepted_clusters"]:
        regions = cluster["component_regions"]
        candidates_by_ordinal[cluster["document_ordinal"]] = (
            evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(
                regions=regions,
                page_json_by_version=page_json_by_document[cluster["document_ordinal"]],
                compiled_specs=compiled,
                query_receipt=build_gemini_json_issued_valuable_papers_region_query_receipt_v1(
                    regions
                ),
            )
        )
    trials = generic._trials(indexed=indexed, candidates_by_ordinal=candidates_by_ordinal)
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id=index["corpus_manifest_index_id"],
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=trials,
        indexed_query_evidence=indexed,
    )
    validate_gemini_json_flat_family_sweep_v1(sweep)
    source_observation_contract = validate_source_observation_mapping_contract_v1(sweep)
    replayed_candidates_by_ordinal = {}
    for cluster in indexed["accepted_clusters"]:
        ordinal = cluster["document_ordinal"]
        regions = cluster["component_regions"]
        replayed_candidates_by_ordinal[ordinal] = (
            validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(
                candidates_by_ordinal[ordinal],
                regions=regions,
                page_json_by_version=page_json_by_document[ordinal],
                compiled_specs=compiled,
                query_receipt=(
                    build_gemini_json_issued_valuable_papers_region_query_receipt_v1(
                        regions
                    )
                ),
            )
        )
    replayed_trials = generic._trials(
        indexed=indexed, candidates_by_ordinal=replayed_candidates_by_ordinal
    )
    if not same_typed_json_v1(replayed_trials, trials):
        raise _error("issued-paper SQLite candidate replay returned a different trial axis")
    audit = build_issued_valuable_papers_experimental_audit_v1(
        sweep=sweep,
        sweep_output=args.output,
        historical_comparator_policy=args.historical_comparator_policy,
        index=index,
        selected_page_json_version_ids=selected_ids,
        indexed_query_evidence=indexed,
        query_recovery_receipts=query_recovery_receipts,
        source_repair_authentication=source_repair_authentication,
        source_observation_contract=source_observation_contract,
        trials=trials,
        compiled_specs=compiled,
        spec_refs=spec_refs,
    )
    validate_issued_valuable_papers_experimental_audit_content_v1(audit)
    database_guard.validate()
    audit_output = args.output.with_suffix(".audit.json")
    generic._write_once(args.output, sweep)
    generic._write_once(audit_output, audit)
    implementation_paths = (
        ROOT
        / "scripts/experiments/run_gemini_json_issued_valuable_papers_accounting_family_v1.py",
        ROOT
        / "scripts/experiments/run_gemini_json_multitable_hierarchical_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
        ROOT
        / "src/bctc_ai/evaluation/gemini_json_issued_valuable_papers_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_flat_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/historical_comparator_policy_v1.py",
        ROOT / "src/bctc_ai/evaluation/source_observation_mapping_contract_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_accounting_family_store_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_financial_page_store_v1.py",
        SOURCE_REPAIR_SPEC_PATH,
    )
    implementation_refs = [
        generic._file_ref(path, root=ROOT) for path in implementation_paths
    ]
    runner_ref = generic._file_ref(
        ROOT
        / "scripts/experiments/run_gemini_json_issued_valuable_papers_accounting_family_v1.py",
        root=ROOT,
    )
    stored = ingest_gemini_accounting_family_sweep_v1(
        args.results_database,
        sweep=sweep,
        corpus_index_ref=generic._file_ref(args.corpus_index),
        implementation_refs=implementation_refs,
        run_kind=args.run_kind,
        source_page_database=database,
        selected_page_json_version_ids=selected_ids,
        corpus_artifact_root=args.artifact_root.resolve(),
        source_replay_adapter=replay_issued_valuable_papers_trials_from_source_v1,
        source_replay_adapter_ref=runner_ref,
    )
    stored_sweep = load_gemini_accounting_family_sweep_v1(
        args.results_database, stored["family_run_id"]
    )
    if not same_typed_json_v1(stored_sweep, sweep):
        raise _error("stored issued-paper sweep differs from authenticated evaluation")
    validate_source_observation_mapping_contract_v1(stored_sweep)
    output_ref = record_gemini_accounting_family_export_v1(
        args.results_database, family_run_id=stored["family_run_id"], output_path=args.output
    )
    database_guard.validate()
    return {
        "audit_id": audit["audit_id"],
        "audit_output": str(audit_output),
        "axis_counts": audit["axis_counts"],
        "axis_sha256": audit["axis_sha256"],
        "disposition": "SUCCEEDED",
        "family_run_id": stored["family_run_id"],
        "historical_comparator_policy": args.historical_comparator_policy,
        "metrics": sweep["metrics"],
        "output": str(args.output),
        "output_ref": output_ref,
        "results_database": str(args.results_database),
        "run_kind": args.run_kind,
        "sweep_id": sweep["sweep_id"],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.run_kind == "OFFICIAL" and args.historical_comparator_policy != STRICT_RELEASE:
        raise _error("OFFICIAL issued-paper run requires STRICT_RELEASE policy")
    if args.historical_comparator_policy == DISJOINT_EXPANSION and args.run_kind != "EXPERIMENTAL":
        raise _error("issued-paper expansion run must be EXPERIMENTAL")
    if args.source_repair_spec.resolve() != SOURCE_REPAIR_SPEC_PATH.resolve():
        raise _error("issued-paper run requires the registered source-repair artifact")
    index = validate_current_corpus_manifest_index_v1(generic._json(args.corpus_index))
    artifact_root = args.artifact_root.resolve()
    database = generic._content_ref(artifact_root, index["database_ref"])
    selected_ids = generic._selected_page_axis(index=index, artifact_root=artifact_root)
    topology = generic._json(args.topology_spec)
    evaluation = generic._json(args.evaluation_spec)
    schema = generic._json(args.schema_binding_spec)
    source_repairs = generic._json(args.source_repair_spec)
    compiled = compile_gemini_json_issued_valuable_papers_family_specs_v1(
        topology, evaluation, schema, source_repairs
    )
    if compiled["topology"]["family_id"] != FAMILY_ID:
        raise _error("runner received a non-issued-paper family")
    spec_refs = {
        "evaluation": generic._file_ref(args.evaluation_spec, root=ROOT),
        "schema_binding": generic._file_ref(args.schema_binding_spec, root=ROOT),
        "source_repair": generic._file_ref(args.source_repair_spec, root=ROOT),
        "topology": generic._file_ref(args.topology_spec, root=ROOT),
    }
    source_repair_authentication = _authenticate_source_repairs_v1(
        repairs=compiled["issued_valuable_papers_source_repairs"],
        source_pdf_root=args.source_pdf_root,
    )
    with generic._authenticated_sqlite_snapshot(
        database, reference=index["database_ref"]
    ) as database_guard:
        return _run_with_authenticated_database(
            args,
            index=index,
            database_guard=database_guard,
            selected_ids=selected_ids,
            topology=topology,
            evaluation=evaluation,
            schema=schema,
            compiled=compiled,
            spec_refs=spec_refs,
            source_repair_authentication=source_repair_authentication,
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-index", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--topology-spec", type=Path, required=True)
    parser.add_argument("--evaluation-spec", type=Path, required=True)
    parser.add_argument("--schema-binding-spec", type=Path, required=True)
    parser.add_argument("--source-repair-spec", type=Path, required=True)
    parser.add_argument("--source-pdf-root", type=Path, required=True)
    parser.add_argument("--results-database", type=Path, required=True)
    parser.add_argument("--run-kind", choices=("EXPERIMENTAL", "OFFICIAL"), required=True)
    parser.add_argument(
        "--historical-comparator-policy",
        choices=(STRICT_RELEASE, DISJOINT_EXPANSION),
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    print(json.dumps(run(_parser().parse_args()), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
