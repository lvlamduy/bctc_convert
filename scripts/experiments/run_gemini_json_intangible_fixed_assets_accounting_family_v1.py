#!/usr/bin/env python3
"""Run Family 20 over an authenticated local JSON corpus.

This family-specific runner keeps the generic fixed-asset evaluator and audit
contract, but makes the corpus relationship explicit.  Expansion runs must be
disjoint from the pinned eight-bank oracle.  Strict runs additionally compare
the complete per-source status and mapping projection with a byte-pinned
Family 20 release sweep.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.gemini_json_fixed_asset_rollforward_family_v1 import (  # noqa: E402
    build_gemini_json_fixed_asset_rollforward_region_query_receipt_v1,
    compile_gemini_json_fixed_asset_rollforward_family_specs_v1,
    evaluate_gemini_json_fixed_asset_rollforward_family_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    build_gemini_json_flat_family_sweep_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.evaluation.historical_comparator_policy_v1 import (  # noqa: E402
    DISJOINT_EXPANSION,
    EXACT_HISTORICAL_COMPARISON,
    NOT_APPLICABLE_DISJOINT_CORPUS,
    STRICT_RELEASE,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
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
    query_selected_fixed_asset_rollforward_family_regions_v1,
    validate_selected_fixed_asset_rollforward_family_candidate_replays_v1,
    validate_selected_fixed_asset_rollforward_family_query_evidence_v1,
)
from scripts.experiments import (  # noqa: E402
    run_gemini_json_fixed_asset_rollforward_accounting_family_v1 as generic_runner,
)


class RunGeminiJsonIntangibleFixedAssetsAccountingFamilyV1Error(RuntimeError):
    """The Family 20 corpus, policy, or exact regression boundary drifted."""


def _error(message: str) -> RunGeminiJsonIntangibleFixedAssetsAccountingFamilyV1Error:
    return RunGeminiJsonIntangibleFixedAssetsAccountingFamilyV1Error(message)


FAMILY_ID = "INTANGIBLE_FIXED_ASSETS_ROLLFORWARD"
PINNED_STRICT_REGRESSION_SWEEP_SHA256 = (
    "976674f8c46fa88a4e26fdbf764b5338535d7351ebdf97c29134b59e89015de0"
)
PINNED_STRICT_REGRESSION_SWEEP_SIZE_BYTES = 9_899_478
STRICT_REGRESSION_FORMAT_VERSION = (
    "INTANGIBLE_FIXED_ASSETS_STRICT_RELEASE_SEMANTIC_REGRESSION_RECEIPT_V1"
)


def _family_id(value: Mapping[str, Any]) -> Any:
    return value.get("topology", {}).get("family_id")


def _mapping_projection(mapping: Any) -> dict[str, Any]:
    if type(mapping) is not dict or type(mapping.get("item_mapping_id")) is not str:
        raise _error("Family 20 regression mapping shape drifted")
    # The identifier seals the complete mapping object and may legitimately
    # change when a declarative spec gains aliases.  Every semantic/source
    # field remains in this projection and must compare byte-exactly.
    return {key: value for key, value in mapping.items() if key != "item_mapping_id"}


def _semantic_trial_axis(sweep: Mapping[str, Any]) -> list[dict[str, Any]]:
    if sweep.get("family_id") != FAMILY_ID or type(sweep.get("trials")) is not list:
        raise _error("strict regression sweep is not Family 20")
    axis = []
    seen = set()
    for trial in sweep["trials"]:
        if type(trial) is not dict:
            raise _error("Family 20 regression trial shape drifted")
        source_sha256 = trial.get("source_sha256")
        mappings = trial.get("mappings")
        reasons = trial.get("reasons")
        if (
            type(source_sha256) is not str
            or source_sha256 in seen
            or type(trial.get("source_logical_name")) is not str
            or type(trial.get("status")) is not str
            or type(mappings) is not list
            or type(reasons) is not list
        ):
            raise _error("Family 20 regression source axis is invalid")
        seen.add(source_sha256)
        axis.append(
            {
                "mappings": [_mapping_projection(item) for item in mappings],
                "reasons": reasons,
                "source_logical_name": trial["source_logical_name"],
                "source_sha256": source_sha256,
                "status": trial["status"],
            }
        )
    return axis


def _strict_regression_receipt(
    *, sweep: Mapping[str, Any], baseline_path: Path | None
) -> dict[str, Any]:
    if baseline_path is None:
        raise _error("STRICT_RELEASE requires --strict-regression-sweep")
    try:
        baseline_ref = generic_runner._file_ref(baseline_path)
        baseline = generic_runner._json(baseline_path)
    except generic_runner.RunGeminiJsonFixedAssetRollforwardAccountingFamilyV1Error as exc:
        raise _error("Family 20 strict regression sweep does not authenticate") from exc
    if (
        baseline_ref["sha256"] != PINNED_STRICT_REGRESSION_SWEEP_SHA256
        or baseline_ref["size_bytes"] != PINNED_STRICT_REGRESSION_SWEEP_SIZE_BYTES
    ):
        raise _error("Family 20 strict regression sweep bytes drifted")
    expected_axis = _semantic_trial_axis(baseline)
    actual_axis = _semantic_trial_axis(sweep)
    if not same_typed_json_v1(actual_axis, expected_axis):
        raise _error("Family 20 strict release semantic regression is not exact")
    material = {
        "baseline_ref": baseline_ref,
        "disposition": "EXACT_SEMANTIC_TRIAL_AXIS",
        "format_version": STRICT_REGRESSION_FORMAT_VERSION,
        "semantic_trial_axis_sha256": canonical_json_sha256_v1(actual_axis),
        "source_count": len(actual_axis),
    }
    return {
        **material,
        "receipt_id": "f20srsv1:receipt:" + canonical_json_sha256_v1(material),
    }


def _assert_policy_receipt(*, audit: Mapping[str, Any], policy: str) -> None:
    receipt = audit.get("historical_comparator_policy_receipt")
    if type(receipt) is not dict or receipt.get("policy") != policy:
        raise _error("Family 20 historical comparator policy receipt is absent")
    if policy == DISJOINT_EXPANSION:
        if (
            receipt.get("disposition") != NOT_APPLICABLE_DISJOINT_CORPUS
            or receipt.get("comparison_axis") != []
            or receipt.get("corpus_relation", {}).get("overlap_count") != 0
            or audit.get("axes", {}).get("historical_comparator") != []
        ):
            raise _error("Family 20 expansion corpus is not exactly disjoint")
        return
    if policy != STRICT_RELEASE or receipt.get("disposition") != EXACT_HISTORICAL_COMPARISON:
        raise _error("Family 20 strict historical comparator is not exact")


def _implementation_refs() -> list[dict[str, Any]]:
    paths = (
        ROOT
        / "scripts/experiments/run_gemini_json_intangible_fixed_assets_accounting_family_v1.py",
        ROOT
        / "scripts/experiments/run_gemini_json_fixed_asset_rollforward_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_fixed_asset_rollforward_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_flat_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/historical_comparator_policy_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_accounting_family_store_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_financial_page_store_v1.py",
    )
    return [generic_runner._file_ref(path, root=ROOT) for path in paths]


def _run_with_authenticated_database(
    args: argparse.Namespace,
    *,
    index: Mapping[str, Any],
    database_guard: Any,
    selected_ids: Sequence[str],
    topology: dict[str, Any],
    evaluation: dict[str, Any],
    schema: dict[str, Any],
    compiled: dict[str, Any],
    spec_refs: dict[str, Any],
) -> dict[str, Any]:
    database = database_guard.path
    indexed = query_selected_fixed_asset_rollforward_family_regions_v1(
        database, selected_page_json_version_ids=selected_ids, compiled_specs=compiled
    )
    validate_selected_fixed_asset_rollforward_family_query_evidence_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
        indexed_query_evidence=indexed,
    )
    pages = generic_runner._load_selected_pages_by_document(
        database,
        selected_ids=selected_ids,
        selected_page_axis=indexed["selected_page_axis"],
    )
    candidates_by_ordinal = {}
    for cluster in indexed["accepted_clusters"]:
        ordinal = cluster["document_ordinal"]
        regions = cluster["component_regions"]
        controls = cluster["control_regions"]
        candidates_by_ordinal[ordinal] = (
            evaluate_gemini_json_fixed_asset_rollforward_family_cluster_v1(
                regions=regions,
                control_regions=controls,
                page_json_by_version=pages[ordinal],
                compiled_specs=compiled,
                query_receipt=build_gemini_json_fixed_asset_rollforward_region_query_receipt_v1(
                    regions, control_regions=controls
                ),
            )
        )
    trials = generic_runner._trials(indexed=indexed, candidates_by_ordinal=candidates_by_ordinal)
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id=index["corpus_manifest_index_id"],
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=trials,
        indexed_query_evidence=indexed,
    )
    validate_gemini_json_flat_family_sweep_v1(sweep)
    validate_selected_fixed_asset_rollforward_family_candidate_replays_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
        indexed_query_evidence=indexed,
        trials=trials,
    )
    source_sha256s = [document["source_sha256"] for document in index["documents"]]
    audit = generic_runner.build_fixed_asset_rollforward_experimental_audit_v1(
        sweep=sweep,
        sweep_output=args.output,
        historical_comparator_policy=args.historical_comparator_policy,
        current_manifest_index_id=index["corpus_manifest_index_id"],
        current_manifest_source_sha256s=source_sha256s,
        selected_page_json_version_ids=selected_ids,
        indexed_query_evidence=indexed,
        trials=trials,
        compiled_specs=compiled,
        spec_refs=spec_refs,
    )
    generic_runner.validate_fixed_asset_rollforward_experimental_audit_replay_v1(
        audit,
        database=database,
        sweep=sweep,
        sweep_output=args.output,
        historical_comparator_policy=args.historical_comparator_policy,
        current_manifest_index_id=index["corpus_manifest_index_id"],
        current_manifest_source_sha256s=source_sha256s,
        selected_page_json_version_ids=selected_ids,
        indexed_query_evidence=indexed,
        trials=trials,
        compiled_specs=compiled,
        spec_refs=spec_refs,
    )
    _assert_policy_receipt(audit=audit, policy=args.historical_comparator_policy)
    regression_receipt = (
        _strict_regression_receipt(sweep=sweep, baseline_path=args.strict_regression_sweep)
        if args.historical_comparator_policy == STRICT_RELEASE
        else None
    )
    database_guard.validate()
    audit_output = args.output.with_suffix(".audit.json")
    generic_runner._write_once(args.output, sweep)
    generic_runner._write_once(audit_output, audit)
    stored = ingest_gemini_accounting_family_sweep_v1(
        args.results_database,
        sweep=sweep,
        corpus_index_ref=generic_runner._file_ref(args.corpus_index),
        implementation_refs=_implementation_refs(),
        run_kind=args.run_kind,
        source_page_database=database,
        selected_page_json_version_ids=selected_ids,
        corpus_artifact_root=args.artifact_root.resolve(),
    )
    stored_sweep = load_gemini_accounting_family_sweep_v1(
        args.results_database, stored["family_run_id"]
    )
    if not same_typed_json_v1(stored_sweep, sweep):
        raise _error("stored Family 20 sweep differs from authenticated evaluation")
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
        "historical_comparator_policy": args.historical_comparator_policy,
        "metrics": sweep["metrics"],
        "output": str(args.output),
        "output_ref": output_ref,
        "results_database": str(args.results_database),
        "run_kind": args.run_kind,
        "strict_regression_receipt": regression_receipt,
        "sweep_id": sweep["sweep_id"],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    policy = args.historical_comparator_policy
    if args.run_kind == "OFFICIAL" and policy != STRICT_RELEASE:
        raise _error("OFFICIAL Family 20 run requires STRICT_RELEASE")
    if policy == DISJOINT_EXPANSION and args.run_kind != "EXPERIMENTAL":
        raise _error("Family 20 expansion run must be EXPERIMENTAL")
    if policy == DISJOINT_EXPANSION and args.strict_regression_sweep is not None:
        raise _error("Family 20 expansion run cannot claim a strict regression sweep")
    index = validate_current_corpus_manifest_index_v1(generic_runner._json(args.corpus_index))
    artifact_root = args.artifact_root.resolve()
    database = generic_runner._content_ref(artifact_root, index["database_ref"])
    selected_ids = generic_runner._selected_page_axis(index=index, artifact_root=artifact_root)
    topology = generic_runner._json(args.topology_spec)
    evaluation = generic_runner._json(args.evaluation_spec)
    schema = generic_runner._json(args.schema_binding_spec)
    compiled = compile_gemini_json_fixed_asset_rollforward_family_specs_v1(
        topology, evaluation, schema
    )
    if _family_id(compiled) != FAMILY_ID:
        raise _error("runner accepts only INTANGIBLE_FIXED_ASSETS_ROLLFORWARD")
    spec_refs = {
        "evaluation": generic_runner._file_ref(args.evaluation_spec, root=ROOT),
        "schema_binding": generic_runner._file_ref(args.schema_binding_spec, root=ROOT),
        "topology": generic_runner._file_ref(args.topology_spec, root=ROOT),
    }
    with generic_runner._authenticated_sqlite_snapshot(
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
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-index", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--topology-spec", type=Path, required=True)
    parser.add_argument("--evaluation-spec", type=Path, required=True)
    parser.add_argument("--schema-binding-spec", type=Path, required=True)
    parser.add_argument("--results-database", type=Path, required=True)
    parser.add_argument("--run-kind", choices=("EXPERIMENTAL", "OFFICIAL"), required=True)
    parser.add_argument(
        "--historical-comparator-policy",
        choices=(STRICT_RELEASE, DISJOINT_EXPANSION),
        required=True,
    )
    parser.add_argument("--strict-regression-sweep", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    print(json.dumps(run(_parser().parse_args()), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
