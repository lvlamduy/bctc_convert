#!/usr/bin/env python3
"""Run Family 29 over one authenticated current selected-JSON corpus."""

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
from bctc_ai.evaluation.gemini_json_interest_expense_family_v1 import (  # noqa: E402
    FAMILY_ID,
    build_gemini_json_interest_expense_indexed_query_evidence_v1,
    build_gemini_json_interest_expense_trials_v1,
    compile_gemini_json_interest_expense_family_specs_v1,
    validate_gemini_json_interest_expense_replay_v1,
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

AUDIT_FORMAT_VERSION = "GEMINI_JSON_INTEREST_EXPENSE_EXPERIMENTAL_AUDIT_V1"
TOPOLOGY_SPEC_PATH = ROOT / "config/families/tm-interest-expense-topology-v1.json"
EVALUATION_SPEC_PATH = ROOT / "config/families/tm-interest-expense-evaluation-v1.json"
SCHEMA_BINDING_SPEC_PATH = (
    ROOT / "config/families/tm-interest-expense-schema-binding-v1.json"
)
SOURCE_REPAIR_PATH = (
    ROOT / "config/families/tm-interest-expense-source-repair-v1.json"
)
ADAPTER_PATH = ROOT / "src/bctc_ai/evaluation/gemini_json_interest_expense_family_v1.py"
SHARED_EVALUATOR_PATH = (
    ROOT / "src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py"
)
SHARED_RUNNER_PATH = (
    ROOT
    / "scripts/experiments/run_gemini_json_multitable_hierarchical_accounting_family_v1.py"
)
# Updated only after the shared owner publishes one load-safe handoff.
PINNED_SHARED_EVALUATOR_SHA256 = (
    "bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2"
)
PINNED_SHARED_RUNNER_SHA256 = (
    "d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5"
)


class RunGeminiJsonInterestExpenseV1Error(RuntimeError):
    """The Family-29 run, authentication, evidence, or replay drifted."""


def _error(message: str) -> RunGeminiJsonInterestExpenseV1Error:
    return RunGeminiJsonInterestExpenseV1Error(message)


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
        raise _error("Family-29 shared implementation pin drifted: " + ",".join(drifted))


def _assert_current_corpus(index: Mapping[str, Any]) -> None:
    documents = index.get("documents")
    if type(documents) is not list or not documents:
        raise _error("Family-29 conclusion corpus is empty")
    if any(
        "/2025/" not in document.get("relative_path", "")
        and "/2026/" not in document.get("relative_path", "")
        for document in documents
    ):
        raise _error("Family-29 conclusion corpus is outside the current reporting scope")


def _source_table(
    page: Mapping[str, Any], *, section_id: str, table_id: str
) -> Mapping[str, Any]:
    try:
        return page["sections"][int(section_id[1:]) - 1]["tables"][
            int(table_id[1:]) - 1
        ]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise _error("Family-29 corroborating source table is invalid") from exc


def _render_authentication(
    *,
    document: Mapping[str, Any],
    physical_page: int,
    expected_render_sha256: str,
    source_pdf_root: Path,
    payload_cache: dict[str, bytes],
    render_cache: dict[tuple[str, int], str],
) -> dict[str, Any]:
    root = source_pdf_root.resolve()
    relative_path = document["relative_path"]
    source_sha256 = document["source_sha256"]
    path = (root / relative_path).resolve()
    if source_pdf_root.is_symlink() or not root.is_dir():
        raise _error("Family-29 source-PDF root is unavailable")
    if not path.is_relative_to(root) or not path.is_file():
        raise _error("Family-29 source-repair PDF path is unavailable")
    payload = payload_cache.get(source_sha256)
    if payload is None:
        payload = path.read_bytes()
        if (
            sha256(payload).hexdigest() != source_sha256
            or len(payload) != document["source_size_bytes"]
        ):
            raise _error("Family-29 source-repair PDF bytes drifted")
        payload_cache[source_sha256] = payload
    render_key = (source_sha256, physical_page)
    actual_render_sha256 = render_cache.get(render_key)
    if actual_render_sha256 is None:
        try:
            with fitz.open(stream=payload, filetype="pdf") as pdf:
                page_index = physical_page - 1
                if not (0 <= page_index < len(pdf)):
                    raise _error("Family-29 source-repair page is outside its PDF")
                pixmap = pdf[page_index].get_pixmap(
                    matrix=fitz.Matrix(2, 2), colorspace=fitz.csRGB, alpha=False
                )
                image = pixmap.tobytes("png")
        except (RuntimeError, ValueError) as exc:
            raise _error("Family-29 source-repair PDF cannot be rendered") from exc
        actual_render_sha256 = sha256(image).hexdigest()
        render_cache[render_key] = actual_render_sha256
    if actual_render_sha256 != expected_render_sha256:
        raise _error("Family-29 source-repair PDF render drifted")
    return {
        "physical_page": physical_page,
        "relative_path": relative_path,
        "render_sha256": actual_render_sha256,
        "source_sha256": source_sha256,
        "source_size_bytes": document["source_size_bytes"],
    }


def _authenticate_applicable_source_repairs_v1(
    *,
    repairs: Sequence[Mapping[str, Any]],
    index: Mapping[str, Any],
    indexed_query_evidence: Mapping[str, Any],
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    source_pdf_root: Path,
) -> list[dict[str, Any]]:
    """Bind every applicable repair to PDF bytes, render, and selected JSON."""

    manifest_by_sha = {item["source_sha256"]: item for item in index["documents"]}
    axis_by_sha = {
        item["source_sha256"]: item
        for item in indexed_query_evidence["selected_document_axis"]
    }
    page_axis = {
        (item["source_sha256"], item["page_json_version_id"]): item
        for item in indexed_query_evidence["selected_page_axis"]
    }
    payload_cache: dict[str, bytes] = {}
    render_cache: dict[tuple[str, int], str] = {}
    checked = []
    for repair in repairs:
        target_document = manifest_by_sha.get(repair["source_sha256"])
        if target_document is None:
            continue
        target_axis = axis_by_sha.get(repair["source_sha256"])
        if target_axis is None:
            raise _error("Family-29 repair target is absent from selected document axis")
        locator = repair["locator"]
        selected_page = page_axis.get(
            (repair["source_sha256"], locator["page_json_version_id"])
        )
        if selected_page is None or selected_page["physical_page"] != locator["physical_page"]:
            raise _error("Family-29 repair target selected-page binding drifted")
        target_auth = _render_authentication(
            document=target_document,
            physical_page=locator["physical_page"],
            expected_render_sha256=repair["pdf_page_render_sha256"],
            source_pdf_root=source_pdf_root,
            payload_cache=payload_cache,
            render_cache=render_cache,
        )
        corroboration_auth = None
        corroboration = repair.get("corroboration")
        if corroboration is not None:
            corroborating_document = manifest_by_sha.get(corroboration["source_sha256"])
            corroborating_axis = axis_by_sha.get(corroboration["source_sha256"])
            if (
                corroborating_document is None
                or corroborating_axis is None
                or corroborating_document["relative_path"]
                != corroboration["source_logical_name"]
            ):
                raise _error("Family-29 corroborating source is absent or drifted")
            corroborating_page_axis = page_axis.get(
                (
                    corroboration["source_sha256"],
                    corroboration["page_json_version_id"],
                )
            )
            if (
                corroborating_page_axis is None
                or corroborating_page_axis["physical_page"]
                != corroboration["physical_page"]
            ):
                raise _error("Family-29 corroborating selected-page binding drifted")
            pages = page_json_by_document.get(corroborating_axis["document_ordinal"])
            page = (
                pages.get(corroboration["page_json_version_id"])
                if type(pages) is dict
                else None
            )
            if type(page) is not dict:
                raise _error("Family-29 corroborating selected JSON is absent")
            table = _source_table(
                page,
                section_id=corroboration["section_id"],
                table_id=corroboration["table_id"],
            )
            rows = table.get("rows")
            columns = table.get("columns")
            row_ordinal = corroboration["row_ordinal"]
            column_ordinal = corroboration["column_ordinal"]
            values = (
                rows[row_ordinal - 1].get("values_exact")
                if type(rows) is list
                and 1 <= row_ordinal <= len(rows)
                and type(rows[row_ordinal - 1]) is dict
                else None
            )
            if (
                type(rows) is not list
                or not (1 <= row_ordinal <= len(rows))
                or type(columns) is not list
                or type(values) is not list
                or not (1 <= column_ordinal <= len(columns))
                or column_ordinal > len(values)
                or not same_typed_json_v1(
                    values[column_ordinal - 1],
                    corroboration["value_exact"],
                )
            ):
                raise _error("Family-29 corroborating selected JSON value drifted")
            corroboration_auth = _render_authentication(
                document=corroborating_document,
                physical_page=corroboration["physical_page"],
                expected_render_sha256=corroboration["pdf_page_render_sha256"],
                source_pdf_root=source_pdf_root,
                payload_cache=payload_cache,
                render_cache=render_cache,
            )
        material = {
            "corroboration_authentication": corroboration_auth,
            "repair_id": repair["repair_id"],
            "target_authentication": target_auth,
        }
        checked.append(
            {
                **material,
                "authentication_id": "gjiefarv1:auth:"
                + canonical_json_sha256_v1(material),
            }
        )
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
            raise _error("Family-29 historical oracle trial denominator drifted")
        references.append({**reference, "expected_trial_count": len(oracle_trials)})
        for trial in oracle_trials:
            source_sha256 = trial.get("source_pdf_sha256")
            if type(source_sha256) is not str:
                raise _error("Family-29 historical oracle source identity is absent")
            rows.append(
                {"oracle_ref_index": reference_index, "source_sha256": source_sha256}
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
            trial["source_sha256"]
            for trial in trials
            if trial["candidate_count"] == 1
        ],
        current_selected_page_json_version_ids=list(selected_ids),
        strict_compare=None,
    )


def _audit_axes(
    *, indexed: Mapping[str, Any], trials: Sequence[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    axes: dict[str, list[dict[str, Any]]] = {
        "equations": [],
        "mappings": [],
        "query_repairs": [],
        "source_repairs": [],
        "trials": canonical_clone_v1(list(trials)),
        "unit_corroborations": [],
    }
    for cluster in indexed["accepted_clusters"]:
        receipt = cluster.get("interest_expense_query_adapter_receipt")
        if type(receipt) is dict:
            axes["query_repairs"].append(canonical_clone_v1(receipt))
    for trial in trials:
        candidates = trial.get("candidates")
        if type(candidates) is not list or len(candidates) != 1:
            continue
        candidate = candidates[0]
        axes["mappings"].extend(canonical_clone_v1(candidate.get("mappings", [])))
        closure = candidate.get("closure_receipt", {})
        axes["equations"].extend(canonical_clone_v1(closure.get("equations", [])))
        adapter = closure.get("interest_expense_adapter_receipt")
        if type(adapter) is not dict:
            continue
        axes["source_repairs"].extend(
            canonical_clone_v1(adapter["source_repair_receipts"])
        )
        axes["unit_corroborations"].extend(
            canonical_clone_v1(adapter["unit_corroboration_receipts"])
        )
    return axes


def build_interest_expense_experimental_audit_v1(
    *,
    sweep: Mapping[str, Any],
    output: Path,
    indexed: Mapping[str, Any],
    trials: Sequence[dict[str, Any]],
    historical_receipt: Mapping[str, Any],
    observation_contract: Mapping[str, Any],
    source_authentications: Sequence[Mapping[str, Any]],
    spec_refs: Mapping[str, Any],
) -> dict[str, Any]:
    axes = _audit_axes(indexed=indexed, trials=trials)
    material = {
        "axis_counts": {key: len(value) for key, value in axes.items()},
        "axis_sha256": {
            key: canonical_json_sha256_v1(value) for key, value in axes.items()
        },
        "family_id": FAMILY_ID,
        "format_version": AUDIT_FORMAT_VERSION,
        "historical_comparator_policy_receipt": canonical_clone_v1(
            historical_receipt
        ),
        "indexed_query_receipt": canonical_clone_v1(indexed["query_receipt"]),
        "source_authentication_axis": canonical_clone_v1(
            list(source_authentications)
        ),
        "source_authentication_axis_sha256": canonical_json_sha256_v1(
            source_authentications
        ),
        "source_authentication_count": len(source_authentications),
        "source_observation_contract": canonical_clone_v1(observation_contract),
        "spec_refs": canonical_clone_v1(spec_refs),
        "sweep_id": sweep["sweep_id"],
        "sweep_output": str(output),
    }
    return {
        **material,
        "audit_id": "gjiefauditv1:audit:" + canonical_json_sha256_v1(material),
    }


def validate_interest_expense_experimental_audit_v1(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or value.get("family_id") != FAMILY_ID
        or value.get("format_version") != AUDIT_FORMAT_VERSION
        or value.get("historical_comparator_policy_receipt", {}).get("policy")
        != DISJOINT_EXPANSION
        or value.get("historical_comparator_policy_receipt", {}).get("disposition")
        != NOT_APPLICABLE_DISJOINT_CORPUS
        or value.get("historical_comparator_policy_receipt", {})
        .get("corpus_relation", {})
        .get("overlap_count")
        != 0
        or value.get("source_observation_contract", {}).get("violation_count") != 0
        or type(value.get("source_authentication_axis")) is not list
        or type(value.get("source_authentication_count")) is not int
        or value["source_authentication_count"]
        != len(value["source_authentication_axis"])
        or value.get("source_authentication_axis_sha256")
        != canonical_json_sha256_v1(value["source_authentication_axis"])
    ):
        raise _error("Family-29 experimental audit content is invalid")
    material = {
        key: canonical_clone_v1(item)
        for key, item in value.items()
        if key != "audit_id"
    }
    if value.get("audit_id") != "gjiefauditv1:audit:" + canonical_json_sha256_v1(
        material
    ):
        raise _error("Family-29 experimental audit identity drifted")
    return canonical_clone_v1(value)


def replay_interest_expense_trials_from_source_v1(
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
    generic_compiled = compile_gemini_json_flat_family_specs_v1(
        topology, evaluation, schema
    )
    if not same_typed_json_v1(generic_compiled, compiled_specs):
        raise _error("Family-29 source replay declarative specs drifted")
    family_compiled = compile_gemini_json_interest_expense_family_specs_v1(
        topology, evaluation, schema, generic._json(SOURCE_REPAIR_PATH)
    )
    base = query_selected_multitable_hierarchical_family_regions_v1(
        source_page_database,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=family_compiled,
    )
    pages = generic._load_selected_pages_by_document(
        source_page_database,
        selected_ids=list(selected_page_json_version_ids),
        selected_page_axis=base["selected_page_axis"],
    )
    indexed = build_gemini_json_interest_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base,
        page_json_by_document=pages,
        compiled_specs=family_compiled,
    )
    if not same_typed_json_v1(indexed, indexed_query_evidence):
        raise _error("Family-29 source replay rebuilt different query evidence")
    return build_gemini_json_interest_expense_trials_v1(
        indexed_query_evidence=indexed,
        page_json_by_document=pages,
        compiled_specs=family_compiled,
    )


def _implementation_refs() -> list[dict[str, Any]]:
    paths = (
        ROOT
        / "scripts/experiments/run_gemini_json_interest_expense_accounting_family_v1.py",
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
    base = query_selected_multitable_hierarchical_family_regions_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
    )
    pages = generic._load_selected_pages_by_document(
        database,
        selected_ids=selected_ids,
        selected_page_axis=base["selected_page_axis"],
    )
    source_authentications = _authenticate_applicable_source_repairs_v1(
        repairs=compiled["interest_expense_source_repairs"],
        index=index,
        indexed_query_evidence=base,
        page_json_by_document=pages,
        source_pdf_root=args.source_pdf_root,
    )
    indexed = build_gemini_json_interest_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    trials = build_gemini_json_interest_expense_trials_v1(
        indexed_query_evidence=indexed,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
    validate_gemini_json_interest_expense_replay_v1(
        base_indexed_query_evidence=base,
        indexed_query_evidence=indexed,
        trials=trials,
        page_json_by_document=pages,
        compiled_specs=compiled,
    )
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
        raise _error("Family-29 current corpus is not completely schema-mappable")
    observation_contract = validate_source_observation_mapping_contract_v1(sweep)
    historical_receipt = _historical_policy_receipt_v1(
        index=index,
        selected_ids=selected_ids,
        indexed=indexed,
        trials=trials,
        compiled_specs=compiled,
    )
    audit = build_interest_expense_experimental_audit_v1(
        sweep=sweep,
        output=args.output,
        indexed=indexed,
        trials=trials,
        historical_receipt=historical_receipt,
        observation_contract=observation_contract,
        source_authentications=source_authentications,
        spec_refs=spec_refs,
    )
    validate_interest_expense_experimental_audit_v1(audit)
    database_guard.validate()
    generic._write_once(args.output, sweep)
    audit_output = args.output.with_suffix(".audit.json")
    generic._write_once(audit_output, audit)
    runner_ref = generic._file_ref(
        ROOT
        / "scripts/experiments/run_gemini_json_interest_expense_accounting_family_v1.py",
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
        source_replay_adapter=replay_interest_expense_trials_from_source_v1,
        source_replay_adapter_ref=runner_ref,
    )
    stored_sweep = load_gemini_accounting_family_sweep_v1(
        args.results_database, stored["family_run_id"]
    )
    if not same_typed_json_v1(stored_sweep, sweep):
        raise _error("stored Family-29 sweep differs from authenticated evaluation")
    validate_source_observation_mapping_contract_v1(stored_sweep)
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
        "source_authentication_axis_sha256": audit[
            "source_authentication_axis_sha256"
        ],
        "source_authentication_count": audit["source_authentication_count"],
        "sweep_id": sweep["sweep_id"],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.historical_comparator_policy != DISJOINT_EXPANSION:
        raise _error("Family-29 current-corpus runner requires DISJOINT_EXPANSION")
    _assert_shared_pins_v1()
    index = validate_current_corpus_manifest_index_v1(generic._json(args.corpus_index))
    _assert_current_corpus(index)
    artifact_root = args.artifact_root.resolve()
    database = generic._content_ref(artifact_root, index["database_ref"])
    selected_ids = generic._selected_page_axis(index=index, artifact_root=artifact_root)
    topology = generic._json(args.topology_spec)
    evaluation = generic._json(args.evaluation_spec)
    schema = generic._json(args.schema_binding_spec)
    source_repairs = generic._json(args.source_repair_spec)
    compiled = compile_gemini_json_interest_expense_family_specs_v1(
        topology, evaluation, schema, source_repairs
    )
    spec_refs = {
        "evaluation": generic._file_ref(args.evaluation_spec, root=ROOT),
        "schema_binding": generic._file_ref(args.schema_binding_spec, root=ROOT),
        "source_repair_spec": generic._file_ref(args.source_repair_spec, root=ROOT),
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
    parser.add_argument(
        "--schema-binding-spec", type=Path, default=SCHEMA_BINDING_SPEC_PATH
    )
    parser.add_argument(
        "--source-repair-spec", type=Path, default=SOURCE_REPAIR_PATH
    )
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
