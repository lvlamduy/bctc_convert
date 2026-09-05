#!/usr/bin/env python3
"""Run Family 28 over one authenticated current selected-JSON corpus."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import Path
from typing import Any

import fitz

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts/experiments") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts/experiments"))

import run_gemini_json_multitable_hierarchical_accounting_family_v1 as generic  # noqa: E402

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.evaluation.gemini_json_interest_income_family_v1 import (  # noqa: E402
    FAMILY_ID,
    adapt_gemini_json_interest_income_indexed_query_evidence_v1,
    bind_gemini_json_interest_income_source_repair_artifact_v1,
    build_gemini_json_interest_income_region_query_receipt_v1,
    compile_gemini_json_interest_income_family_specs_v1,
    evaluate_gemini_json_interest_income_family_cluster_v1,
    validate_gemini_json_interest_income_family_candidate_replay_v1,
)
from bctc_ai.evaluation.historical_comparator_policy_v1 import (  # noqa: E402
    DISJOINT_EXPANSION,
    NOT_APPLICABLE_DISJOINT_CORPUS,
    audit_historical_comparator_policy_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (  # noqa: E402
    validate_source_observation_mapping_contract_v1,
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
    query_selected_multitable_hierarchical_family_regions_v1,
)

AUDIT_FORMAT_VERSION = "GEMINI_JSON_INTEREST_INCOME_EXPERIMENTAL_AUDIT_V1"
TOPOLOGY_SPEC_PATH = ROOT / "config/families/tm-interest-income-topology-v1.json"
EVALUATION_SPEC_PATH = ROOT / "config/families/tm-interest-income-evaluation-v1.json"
SCHEMA_BINDING_SPEC_PATH = ROOT / "config/families/tm-interest-income-schema-binding-v1.json"
SOURCE_REPAIR_PATH = ROOT / "data/registered/gemini_json_interest_income_source_repairs_v1.json"
ADAPTER_PATH = ROOT / "src/bctc_ai/evaluation/gemini_json_interest_income_family_v1.py"
SHARED_EVALUATOR_PATH = (
    ROOT / "src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py"
)
SHARED_RUNNER_PATH = (
    ROOT / "scripts/experiments/run_gemini_json_multitable_hierarchical_accounting_family_v1.py"
)
PINNED_SHARED_EVALUATOR_SHA256 = "bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2"
PINNED_SHARED_RUNNER_SHA256 = "d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5"
PINNED_CURRENT_CORPUS_INDEX_SHA256 = (
    "969ff5f80732c39e4b7543ca1f5c1e5b5b827260f19981ed02945fe0c7379219"
)
PINNED_CURRENT_CORPUS_INDEX_ID = (
    "gjfccmiv1:index:8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a"
)
PINNED_CURRENT_DOCUMENT_COUNT = 271
PINNED_CURRENT_SELECTED_PAGE_COUNT = 14_945


class RunGeminiJsonInterestIncomeV1Error(RuntimeError):
    """The Family-28 run, evidence, or replay boundary drifted."""


def _error(message: str) -> RunGeminiJsonInterestIncomeV1Error:
    return RunGeminiJsonInterestIncomeV1Error(message)


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _assert_shared_pins_v1() -> None:
    expected = {
        SHARED_EVALUATOR_PATH: PINNED_SHARED_EVALUATOR_SHA256,
        SHARED_RUNNER_PATH: PINNED_SHARED_RUNNER_SHA256,
    }
    drifted = [str(path) for path, digest in expected.items() if _sha256(path) != digest]
    if drifted:
        raise _error("Family-28 shared implementation pin drifted: " + ",".join(drifted))


def _assert_current_corpus(index: Mapping[str, Any]) -> None:
    documents = index.get("documents")
    if type(documents) is not list or not documents:
        raise _error("Family-28 conclusion corpus is empty")
    if any(
        "/2025/" not in document.get("relative_path", "")
        and "/2026/" not in document.get("relative_path", "")
        for document in documents
    ):
        raise _error("Family-28 conclusion corpus is outside the current reporting scope")
    summary = index.get("summary")
    if (
        index.get("corpus_manifest_index_id") != PINNED_CURRENT_CORPUS_INDEX_ID
        or len(documents) != PINNED_CURRENT_DOCUMENT_COUNT
        or type(summary) is not dict
        or summary.get("document_count") != PINNED_CURRENT_DOCUMENT_COUNT
        or summary.get("page_count") != PINNED_CURRENT_SELECTED_PAGE_COUNT
    ):
        raise _error("Family-28 conclusion requires the authenticated full271 corpus")


def _authenticate_source_repair_images_v1(
    *, repairs: Sequence[Mapping[str, Any]], source_pdf_root: Path
) -> list[dict[str, Any]]:
    """Re-render every registered page from its byte-authenticated source PDF."""

    root = source_pdf_root.resolve()
    if source_pdf_root.is_symlink() or not root.is_dir():
        raise _error("Family-28 source-PDF root is unavailable")
    payloads: dict[tuple[str, str], bytes] = {}
    rendered_pages: dict[tuple[str, int], dict[str, Any]] = {}
    checked = []
    for repair in repairs:
        logical_name = repair["source_logical_name"]
        source_sha256 = repair["source_sha256"]
        path = (root / logical_name).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise _error("Family-28 source-repair PDF path is unavailable")
        source_key = (logical_name, source_sha256)
        payload = payloads.get(source_key)
        if payload is None:
            payload = path.read_bytes()
            if sha256(payload).hexdigest() != source_sha256:
                raise _error("Family-28 source-repair PDF bytes drifted")
            payloads[source_key] = payload
        page_key = (logical_name, repair["physical_page"])
        actual = rendered_pages.get(page_key)
        if actual is None:
            try:
                with fitz.open(stream=payload, filetype="pdf") as document:
                    page_index = repair["physical_page"] - 1
                    if not (0 <= page_index < len(document)):
                        raise _error("Family-28 source-repair physical page is outside its PDF")
                    pixmap = document[page_index].get_pixmap(
                        dpi=300,
                        colorspace=fitz.csRGB,
                        alpha=False,
                    )
                    image = pixmap.tobytes("png")
            except (RuntimeError, ValueError) as exc:
                raise _error("Family-28 source-repair PDF cannot be rendered") from exc
            actual = {
                "height": pixmap.height,
                "media_type": "image/png",
                "render_dpi": 300,
                "sha256": sha256(image).hexdigest(),
                "size_bytes": len(image),
                "width": pixmap.width,
            }
            rendered_pages[page_key] = actual
        if not same_typed_json_v1(actual, repair["page_image"]):
            raise _error("Family-28 source-repair page render drifted")
        checked.append(canonical_clone_v1(repair))
    return checked


def _historical_policy_receipt_v1(
    *,
    index: Mapping[str, Any],
    selected_ids: Sequence[str],
    indexed: Mapping[str, Any],
    trials: Sequence[dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    references = []
    rows = []
    for reference_index, (reference, oracle) in enumerate(
        generic._historical_oracles(compiled_specs=compiled_specs)
    ):
        oracle_trials = oracle.get("trials")
        if type(oracle_trials) is not list or not oracle_trials:
            raise _error("Family-28 historical oracle trial denominator drifted")
        references.append({**reference, "expected_trial_count": len(oracle_trials)})
        for trial in oracle_trials:
            source_sha256 = trial.get("source_pdf_sha256")
            if type(source_sha256) is not str:
                raise _error("Family-28 historical oracle source identity is absent")
            rows.append(
                {
                    "oracle_ref_index": reference_index,
                    "source_sha256": source_sha256,
                }
            )
    source_by_ordinal = {
        document["document_ordinal"]: document["source_sha256"]
        for document in indexed["selected_document_axis"]
    }
    return audit_historical_comparator_policy_v1(
        policy=DISJOINT_EXPANSION,
        pinned_oracle_refs=references,
        normalized_oracle_rows=rows,
        current_manifest_index_id=index["corpus_manifest_index_id"],
        current_manifest_source_sha256s=[
            document["source_sha256"] for document in index["documents"]
        ],
        current_manifest_page_json_version_ids=list(selected_ids),
        current_trials=list(trials),
        current_candidate_source_sha256s=[
            source_by_ordinal[cluster["document_ordinal"]]
            for cluster in indexed["accepted_clusters"]
        ],
        current_replay_source_sha256s=[
            trial["source_sha256"] for trial in trials if trial["candidate_count"] == 1
        ],
        current_selected_page_json_version_ids=list(selected_ids),
        strict_compare=None,
    )


def _audit_axes(trials: Sequence[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    axes: dict[str, list[dict[str, Any]]] = {
        "cross_fragment_same_role_parent_equations": [],
        "equations": [],
        "mappings": [],
        "one_sided_continuations": [],
        "period_normalizations": [],
        "source_repairs": [],
        "trials": canonical_clone_v1(list(trials)),
        "unit_corroborations": [],
    }
    for trial in trials:
        candidates = trial.get("candidates")
        if type(candidates) is not list or len(candidates) != 1:
            continue
        candidate = candidates[0]
        axes["mappings"].extend(canonical_clone_v1(candidate.get("mappings", [])))
        closure = candidate.get("closure_receipt", {})
        axes["cross_fragment_same_role_parent_equations"].extend(
            canonical_clone_v1(
                closure.get("cross_fragment_same_role_parent_equation_receipts", [])
            )
        )
        axes["equations"].extend(canonical_clone_v1(closure.get("equations", [])))
        adapter = closure.get("interest_income_adapter_receipt")
        if type(adapter) is not dict:
            continue
        axes["one_sided_continuations"].extend(
            canonical_clone_v1(adapter["one_sided_continuation_receipts"])
        )
        axes["period_normalizations"].extend(
            canonical_clone_v1(adapter["period_normalization_receipts"])
        )
        axes["source_repairs"].extend(canonical_clone_v1(adapter["source_repair_receipts"]))
        axes["unit_corroborations"].extend(
            canonical_clone_v1(adapter["unit_corroboration_receipts"])
        )
    return axes


def build_interest_income_experimental_audit_v1(
    *,
    sweep: Mapping[str, Any],
    output: Path,
    indexed: Mapping[str, Any],
    trials: Sequence[dict[str, Any]],
    historical_receipt: Mapping[str, Any],
    observation_contract: Mapping[str, Any],
    query_recovery_receipts: Sequence[Mapping[str, Any]],
    source_repair_overlay: Mapping[str, Any],
    spec_refs: Mapping[str, Any],
) -> dict[str, Any]:
    axes = _audit_axes(trials)
    axes["query_recoveries"] = canonical_clone_v1(list(query_recovery_receipts))
    expected_repair_ids = sorted(repair["repair_id"] for repair in source_repair_overlay["repairs"])
    applied_repair_ids = sorted(receipt["repair_id"] for receipt in axes["source_repairs"])
    source_repair_application = {
        "applied_count": len(applied_repair_ids),
        "applied_repair_ids_sha256": canonical_json_sha256_v1(applied_repair_ids),
        "applied_unique_count": len(set(applied_repair_ids)),
        "expected_count": len(expected_repair_ids),
        "expected_repair_ids_sha256": canonical_json_sha256_v1(expected_repair_ids),
        "overlay_id": source_repair_overlay["overlay_id"],
    }
    material = {
        "axis_counts": {key: len(value) for key, value in axes.items()},
        "axis_sha256": {key: canonical_json_sha256_v1(value) for key, value in axes.items()},
        "family_id": FAMILY_ID,
        "format_version": AUDIT_FORMAT_VERSION,
        "historical_comparator_policy_receipt": canonical_clone_v1(historical_receipt),
        "indexed_query_receipt": canonical_clone_v1(indexed["query_receipt"]),
        "source_repair_application": source_repair_application,
        "source_observation_contract": canonical_clone_v1(observation_contract),
        "spec_refs": canonical_clone_v1(spec_refs),
        "sweep_id": sweep["sweep_id"],
        "sweep_output": str(output),
    }
    return {
        **material,
        "audit_id": "gjiifauditv1:audit:" + canonical_json_sha256_v1(material),
    }


def validate_interest_income_experimental_audit_v1(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or value.get("family_id") != FAMILY_ID
        or value.get("format_version") != AUDIT_FORMAT_VERSION
        or value.get("historical_comparator_policy_receipt", {}).get("policy") != DISJOINT_EXPANSION
        or value.get("historical_comparator_policy_receipt", {}).get("disposition")
        != NOT_APPLICABLE_DISJOINT_CORPUS
        or value.get("historical_comparator_policy_receipt", {})
        .get("corpus_relation", {})
        .get("overlap_count")
        != 0
        or value.get("source_observation_contract", {}).get("violation_count") != 0
        or value.get("source_repair_application", {}).get("expected_count") != 30
        or value.get("source_repair_application", {}).get("applied_count") != 30
        or value.get("source_repair_application", {}).get("applied_unique_count") != 30
        or value.get("source_repair_application", {}).get("expected_repair_ids_sha256")
        != value.get("source_repair_application", {}).get("applied_repair_ids_sha256")
        or value.get("axis_counts", {}).get("source_repairs") != 30
        or value.get("axis_counts", {}).get("query_recoveries") != 1
        or value.get("axis_counts", {}).get("one_sided_continuations") != 1
        or value.get("axis_counts", {}).get("cross_fragment_same_role_parent_equations") != 2
        or value.get("axis_counts", {}).get("period_normalizations") != 2
        or value.get("axis_counts", {}).get("unit_corroborations") != 58
    ):
        raise _error(
            "Family-28 experimental audit content is invalid: "
            + json.dumps(
                {
                    "axis_counts": value.get("axis_counts"),
                    "historical_comparator_policy_receipt": value.get(
                        "historical_comparator_policy_receipt"
                    ),
                    "source_observation_violation_count": value.get(
                        "source_observation_contract", {}
                    ).get("violation_count"),
                    "source_repair_application": value.get(
                        "source_repair_application"
                    ),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    material = {key: canonical_clone_v1(item) for key, item in value.items() if key != "audit_id"}
    if value.get("audit_id") != "gjiifauditv1:audit:" + canonical_json_sha256_v1(material):
        raise _error("Family-28 experimental audit identity drifted")
    return canonical_clone_v1(value)


def replay_interest_income_trials_from_source_v1(
    *,
    source_page_database: Path,
    selected_page_json_version_ids: tuple[str, ...],
    compiled_specs: dict[str, Any],
    indexed_query_evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    """Re-query and replay every candidate through the byte-bound adapter."""

    topology = generic._json(TOPOLOGY_SPEC_PATH)
    evaluation = generic._json(EVALUATION_SPEC_PATH)
    schema = generic._json(SCHEMA_BINDING_SPEC_PATH)
    generic_compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
    if not same_typed_json_v1(generic_compiled, compiled_specs):
        raise _error("Family-28 source replay declarative specs drifted")
    family_compiled = bind_gemini_json_interest_income_source_repair_artifact_v1(
        generic_compiled,
        generic._json(SOURCE_REPAIR_PATH),
    )
    raw_indexed = query_selected_multitable_hierarchical_family_regions_v1(
        source_page_database,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=family_compiled,
    )
    pages = generic._load_selected_pages_by_document(
        source_page_database,
        selected_ids=list(selected_page_json_version_ids),
        selected_page_axis=raw_indexed["selected_page_axis"],
    )
    indexed, _query_recovery_receipts = adapt_gemini_json_interest_income_indexed_query_evidence_v1(
        raw_indexed,
        page_json_by_document=pages,
        compiled_specs=family_compiled,
    )
    if not same_typed_json_v1(indexed, indexed_query_evidence):
        raise _error("Family-28 source replay rebuilt different query evidence")
    candidates = {}
    for cluster in indexed["accepted_clusters"]:
        ordinal = cluster["document_ordinal"]
        regions = cluster["component_regions"]
        receipt = build_gemini_json_interest_income_region_query_receipt_v1(regions)
        candidate = evaluate_gemini_json_interest_income_family_cluster_v1(
            regions=regions,
            page_json_by_version=pages[ordinal],
            compiled_specs=family_compiled,
            query_receipt=receipt,
        )
        candidates[ordinal] = validate_gemini_json_interest_income_family_candidate_replay_v1(
            candidate,
            regions=regions,
            page_json_by_version=pages[ordinal],
            compiled_specs=family_compiled,
            query_receipt=receipt,
        )
    return generic._trials(indexed=indexed, candidates_by_ordinal=candidates)


def _implementation_refs() -> list[dict[str, Any]]:
    paths = (
        ROOT / "scripts/experiments/run_gemini_json_interest_income_accounting_family_v1.py",
        ADAPTER_PATH,
        SHARED_EVALUATOR_PATH,
        SHARED_RUNNER_PATH,
        ROOT / "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_flat_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/historical_comparator_policy_v1.py",
        ROOT / "src/bctc_ai/evaluation/source_observation_mapping_contract_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_accounting_family_store_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_financial_page_store_v1.py",
        TOPOLOGY_SPEC_PATH,
        EVALUATION_SPEC_PATH,
        SCHEMA_BINDING_SPEC_PATH,
        SOURCE_REPAIR_PATH,
    )
    return [generic._file_ref(path, root=ROOT) for path in paths]


def _run_with_database(
    args: argparse.Namespace,
    *,
    index: Mapping[str, Any],
    database_guard: Any,
    selected_ids: list[str],
    topology: dict[str, Any],
    evaluation: dict[str, Any],
    schema: dict[str, Any],
    compiled: dict[str, Any],
    spec_refs: dict[str, Any],
) -> dict[str, Any]:
    database = database_guard.path
    raw_indexed = query_selected_multitable_hierarchical_family_regions_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
    )
    pages = generic._load_selected_pages_by_document(
        database,
        selected_ids=selected_ids,
        selected_page_axis=raw_indexed["selected_page_axis"],
    )
    indexed, query_recovery_receipts = adapt_gemini_json_interest_income_indexed_query_evidence_v1(
        raw_indexed,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    candidates = {}
    for cluster in indexed["accepted_clusters"]:
        ordinal = cluster["document_ordinal"]
        regions = cluster["component_regions"]
        receipt = build_gemini_json_interest_income_region_query_receipt_v1(regions)
        candidate = evaluate_gemini_json_interest_income_family_cluster_v1(
            regions=regions,
            page_json_by_version=pages[ordinal],
            compiled_specs=compiled,
            query_receipt=receipt,
        )
        candidates[ordinal] = validate_gemini_json_interest_income_family_candidate_replay_v1(
            candidate,
            regions=regions,
            page_json_by_version=pages[ordinal],
            compiled_specs=compiled,
            query_receipt=receipt,
        )
    trials = generic._trials(indexed=indexed, candidates_by_ordinal=candidates)
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id=index["corpus_manifest_index_id"],
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=trials,
        indexed_query_evidence=indexed,
    )
    validate_gemini_json_flat_family_sweep_v1(sweep)
    if sweep["metrics"].get("document_count") != len(index["documents"]) or any(
        sweep["metrics"].get(key) != expected
        for key, expected in (
            ("ready_count", len(index["documents"])),
            ("not_observed_count", 0),
            ("unresolved_count", 0),
        )
    ):
        nonready = [
            {
                "candidate_count": trial.get("candidate_count"),
                "document_ordinal": trial.get("document_ordinal"),
                "reasons": canonical_clone_v1(trial.get("reasons")),
                "source_logical_name": trial.get("source_logical_name"),
                "status": trial.get("status"),
            }
            for trial in trials
            if trial.get("status") != generic.READY
        ]
        raise _error(
            "Family-28 current corpus is not completely schema-mappable: "
            + json.dumps(
                {"metrics": sweep["metrics"], "nonready": nonready},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    observation_contract = validate_source_observation_mapping_contract_v1(sweep)
    historical_receipt = _historical_policy_receipt_v1(
        index=index,
        selected_ids=selected_ids,
        indexed=indexed,
        trials=trials,
        compiled_specs=compiled,
    )
    audit = build_interest_income_experimental_audit_v1(
        sweep=sweep,
        output=args.output,
        indexed=indexed,
        trials=trials,
        historical_receipt=historical_receipt,
        observation_contract=observation_contract,
        query_recovery_receipts=query_recovery_receipts,
        source_repair_overlay=compiled["interest_income_source_repair_overlay"],
        spec_refs=spec_refs,
    )
    validate_interest_income_experimental_audit_v1(audit)
    database_guard.validate()
    audit_output = args.output.with_suffix(".audit.json")
    runner_ref = generic._file_ref(
        ROOT / "scripts/experiments/run_gemini_json_interest_income_accounting_family_v1.py",
        root=ROOT,
    )
    stored = ingest_gemini_accounting_family_sweep_v1(
        args.results_database,
        sweep=sweep,
        corpus_index_ref=generic._file_ref(args.corpus_index),
        implementation_refs=_implementation_refs(),
        run_kind="EXPERIMENTAL",
        source_page_database=database,
        selected_page_json_version_ids=selected_ids,
        corpus_artifact_root=args.artifact_root.resolve(),
        source_replay_adapter=replay_interest_income_trials_from_source_v1,
        source_replay_adapter_ref=runner_ref,
    )
    stored_sweep = load_gemini_accounting_family_sweep_v1(
        args.results_database, stored["family_run_id"]
    )
    if not same_typed_json_v1(stored_sweep, sweep):
        raise _error("stored Family-28 sweep differs from authenticated evaluation")
    validate_source_observation_mapping_contract_v1(stored_sweep)
    database_guard.validate()
    generic._write_once(args.output, sweep)
    generic._write_once(audit_output, audit)
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
        "historical_comparator_policy": DISJOINT_EXPANSION,
        "metrics": sweep["metrics"],
        "output": str(args.output),
        "output_ref": output_ref,
        "results_database": str(args.results_database),
        "run_kind": "EXPERIMENTAL",
        "sweep_id": sweep["sweep_id"],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.historical_comparator_policy != DISJOINT_EXPANSION:
        raise _error("Family-28 current-corpus runner requires DISJOINT_EXPANSION")
    _assert_shared_pins_v1()
    if _sha256(args.corpus_index) != PINNED_CURRENT_CORPUS_INDEX_SHA256:
        raise _error("Family-28 current-corpus index bytes drifted")
    index = validate_current_corpus_manifest_index_v1(generic._json(args.corpus_index))
    _assert_current_corpus(index)
    artifact_root = args.artifact_root.resolve()
    database = generic._content_ref(artifact_root, index["database_ref"])
    selected_ids = generic._selected_page_axis(index=index, artifact_root=artifact_root)
    if (
        len(selected_ids) != PINNED_CURRENT_SELECTED_PAGE_COUNT
        or len(set(selected_ids)) != PINNED_CURRENT_SELECTED_PAGE_COUNT
    ):
        raise _error("Family-28 selected full271 page frontier drifted")
    topology = generic._json(args.topology_spec)
    evaluation = generic._json(args.evaluation_spec)
    schema = generic._json(args.schema_binding_spec)
    source_repairs = generic._json(args.source_repair_artifact)
    compiled = compile_gemini_json_interest_income_family_specs_v1(
        topology, evaluation, schema, source_repairs
    )
    checked_repairs = _authenticate_source_repair_images_v1(
        repairs=compiled["interest_income_source_repair_overlay"]["repairs"],
        source_pdf_root=args.source_pdf_root,
    )
    if not same_typed_json_v1(
        checked_repairs,
        compiled["interest_income_source_repair_overlay"]["repairs"],
    ):
        raise _error("Family-28 source-repair authentication axis drifted")
    spec_refs = {
        "evaluation": generic._file_ref(args.evaluation_spec, root=ROOT),
        "schema_binding": generic._file_ref(args.schema_binding_spec, root=ROOT),
        "source_repair_artifact": generic._file_ref(args.source_repair_artifact, root=ROOT),
        "topology": generic._file_ref(args.topology_spec, root=ROOT),
    }
    with generic._authenticated_sqlite_snapshot(
        database, reference=index["database_ref"]
    ) as database_guard:
        return _run_with_database(
            args,
            index=index,
            database_guard=database_guard,
            selected_ids=selected_ids,
            topology=topology,
            evaluation=evaluation,
            schema=schema,
            compiled=compiled,
            spec_refs=spec_refs,
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-index", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--source-pdf-root", type=Path, required=True)
    parser.add_argument("--topology-spec", type=Path, default=TOPOLOGY_SPEC_PATH)
    parser.add_argument("--evaluation-spec", type=Path, default=EVALUATION_SPEC_PATH)
    parser.add_argument("--schema-binding-spec", type=Path, default=SCHEMA_BINDING_SPEC_PATH)
    parser.add_argument("--source-repair-artifact", type=Path, default=SOURCE_REPAIR_PATH)
    parser.add_argument("--results-database", type=Path, required=True)
    parser.add_argument(
        "--historical-comparator-policy",
        choices=(DISJOINT_EXPANSION,),
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    print(json.dumps(run(_parser().parse_args()), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
