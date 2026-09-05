#!/usr/bin/env python3
"""Produce F36 diagnostic evidence, never a release, audit substitute, or store run.

Run in a fresh standalone process with no concurrent code/config edits. Source
repairs are authenticated against their real PDF/render/crop evidence before
interpretation. Residual/manual PDF review and final-store acceptance are NOT
performed. No providers are called and no results/authority database is written.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SUPPORT_RELATIVE = "scripts/experiments/build_f36_source_row_coverage_from_sweep_v1.py"
RUNNER_RELATIVE = "scripts/experiments/run_gemini_json_operating_expense_accounting_family_v1.py"
CODE_RELATIVES = (
    "scripts/experiments/build_f36_diagnostic_from_corpus_v1.py",
    SUPPORT_RELATIVE,
    RUNNER_RELATIVE,
    "src/bctc_ai/evaluation/gemini_json_operating_expense_family_v1.py",
)
FORMAT_VERSION = "OPERATING_EXPENSE_OFFLINE_DIAGNOSTIC_V1"


class DiagnosticError(RuntimeError):
    """Stop without publishing when diagnostic inputs or replay drift."""


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _load_module(name: str, path: Path) -> ModuleType:
    if name in sys.modules:
        raise DiagnosticError("Use a fresh process; diagnostic runtime already imported")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise DiagnosticError(f"Cannot import the active runtime: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_support(root: Path) -> ModuleType:
    return _load_module("_f36_diagnostic_portable_support", root / SUPPORT_RELATIVE)


def _load_runner(root: Path, support: ModuleType) -> ModuleType:
    generic_name = "run_gemini_json_multitable_hierarchical_accounting_family_v1"
    if generic_name in sys.modules:
        raise DiagnosticError("Use a fresh process; generic runner already imported")
    support._load_runtime(root)
    sys.path.insert(0, str(root / "scripts/experiments"))
    runner = _load_module("_f36_diagnostic_bound_runner", root / RUNNER_RELATIVE)
    if Path(runner.generic.__file__).resolve() != root / support.GENERIC_RELATIVE:
        raise DiagnosticError("Generic runner came from a different checkout")
    support._verify_module_roots(root / "src")
    runner._assert_shared_pins_v1()
    return runner


def _evaluate(runner: ModuleType, index: dict, database: Path, selected_ids: list,
              specs: list, source_pdf_root: Path) -> dict:
    topology, evaluation, schema, repairs = specs
    compiled = runner.compile_gemini_json_operating_expense_family_specs_v1(*specs)
    base = runner.query_selected_multitable_hierarchical_family_regions_v1(
        database, selected_page_json_version_ids=selected_ids, compiled_specs=compiled
    )
    source_repair_authentication = runner._authenticate_source_repairs_v1(
        compiled_specs=compiled, index=index, selected_page_axis=base["selected_page_axis"],
        source_pdf_root=source_pdf_root,
    )
    pages = runner.generic._load_selected_pages_by_document(
        database, selected_ids=selected_ids, selected_page_axis=base["selected_page_axis"]
    )
    indexed = runner.build_gemini_json_operating_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base, page_json_by_document=pages, compiled_specs=compiled
    )
    trials = runner.build_gemini_json_operating_expense_trials_v1(
        indexed_query_evidence=indexed, page_json_by_document=pages, compiled_specs=compiled
    )
    runner.validate_gemini_json_operating_expense_replay_v1(
        indexed_query_evidence=indexed, trials=trials,
        page_json_by_document=pages, compiled_specs=compiled,
    )
    replayed = runner.replay_operating_expense_trials_from_source_v1(
        source_page_database=database, selected_page_json_version_ids=tuple(selected_ids),
        compiled_specs=runner.compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema),
        indexed_query_evidence=indexed,
    )
    if not runner.same_typed_json_v1(replayed, trials):
        raise DiagnosticError("Independent source replay returned different trials")
    sweep = runner.build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id=index["corpus_manifest_index_id"], topology_spec=topology,
        evaluation_spec=evaluation, schema_binding_spec=schema,
        trials=trials, indexed_query_evidence=indexed,
    )
    runner.validate_gemini_json_flat_family_sweep_v1(sweep)
    if sweep["family_id"] != "OPERATING_EXPENSE":
        raise DiagnosticError("Evaluated sweep family identity drifted")
    if sweep["metrics"].get("document_count") != len(index["documents"]):
        raise DiagnosticError("Current corpus document denominator drifted")
    observation = runner.validate_source_observation_mapping_contract_v1(sweep)
    coverage = runner.build_operating_expense_source_row_coverage_receipt_v1(
        indexed_query_evidence=indexed, trials=trials, page_json_by_document=dict(pages),
        compiled_specs=compiled, fail_on_violation=False,
    )
    if coverage["violation_count"] == 0:
        runner._validate_source_row_coverage_receipt_v1(coverage)
    return {
        "family_id": sweep["family_id"],
        "corpus_manifest_index_id": index["corpus_manifest_index_id"],
        "indexed_query_evidence": indexed,
        "trials": trials,
        "metrics": sweep["metrics"],
        "evaluated_sweep_metadata": {
            key: value for key, value in sweep.items()
            if key not in {"family_id", "corpus_manifest_index_id", "indexed_query_evidence",
                           "trials", "metrics"}
        },
        "evaluated_sweep_sha256": runner.canonical_json_sha256_v1(sweep),
        "source_row_coverage_receipt": coverage,
        "source_repair_authentication_receipt": source_repair_authentication,
        "source_observation_contract": observation,
        "gates": {
            "independent_source_replay": "PASS",
            "source_repair_authentication": "PASS",
            "source_row_coverage": "PASS" if coverage["violation_count"] == 0 else "FAIL",
            "pdf_residual_review": "NOT_PERFORMED",
            "manual_pdf_visible_row_review": "NOT_PERFORMED",
            "final_store_acceptance": "NOT_PERFORMED",
        },
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    root = args.repo_root.resolve(strict=True)
    if root != ROOT:
        raise DiagnosticError("--repo-root must be the checkout containing this producer")
    if os.path.lexists(args.output):
        raise DiagnosticError("Refusing to overwrite an existing output or symlink")
    code_hashes = {relative: _hash(root / relative) for relative in CODE_RELATIVES}
    support = _load_support(root)
    artifact_root, temporary_root, spec_paths = support._paths(args)
    source_pdf_root = args.source_pdf_root.resolve(strict=True)
    if not source_pdf_root.is_dir() or any(
        path.is_relative_to(source_pdf_root) for path in (args.output.resolve(), temporary_root)
    ):
        raise DiagnosticError("Source PDF root must be read-only and outside output/temp paths")
    # Independent replay deliberately reloads the runner's registered active config paths.
    for name, path in spec_paths.items():
        expected = root / f"config/families/tm-operating-expense-{name.replace('_', '-')}-v1.json"
        if path != expected.resolve():
            raise DiagnosticError("Diagnostic replay requires active registered family configs")
    runner = _load_runner(root, support)
    references: dict[str, dict[str, Any]] = {}
    index = runner.validate_current_corpus_manifest_index_v1(
        support._object(args.corpus_index, references)
    )
    runner._assert_current_corpus(index)
    specs = [support._object(spec_paths[name], references) for name in support.SPEC_NAMES]
    database = runner.generic._content_ref(artifact_root, index["database_ref"])
    selected_ids = runner.generic._selected_page_axis(index=index, artifact_root=artifact_root)
    # Keep explicit headroom after the one private SQLite snapshot; never spill into /tmp.
    if shutil.disk_usage(temporary_root).free < index["database_ref"]["size_bytes"] + 512 * 1024**2:
        raise DiagnosticError("Insufficient private temporary space for snapshot plus headroom")
    with support._temporary_directory_root(temporary_root), runner.generic._authenticated_sqlite_snapshot(
        database, reference=index["database_ref"]
    ) as guard:
        material = _evaluate(runner, index, guard.path, selected_ids, specs, source_pdf_root)
    for repair in material["source_repair_authentication_receipt"]["repair_axis"]:
        source = repair["source"]
        source_path = runner._source_path(source_pdf_root, source["source_logical_name"])
        references[str(source_path)] = {
            "sha256": source["source_sha256"], "size_bytes": source["source_size_bytes"]
        }
    material.update({
        "format_version": FORMAT_VERSION,
        "authority": {"diagnostic_only": True, "release_authority": False,
                      "canonical_mapping_authority": False, "results_store_written": False},
        "hashes": {"active_code_sha256": code_hashes, "frozen_sha256": support.FROZEN_SHA256,
                   "input_references": references},
    })
    diagnostic = {**material, "diagnostic_id":
                  "gjoefav1:offline-diagnostic:" + runner.canonical_json_sha256_v1(material)}
    payload = runner.canonical_json_bytes_v1(diagnostic)
    for path, reference in references.items():
        if _hash(Path(path)) != reference["sha256"]:
            raise DiagnosticError(f"Input changed during diagnostic: {path}")
    for relative, expected in {**code_hashes, **support.FROZEN_SHA256}.items():
        if _hash(root / relative) != expected:
            raise DiagnosticError(f"Active/frozen code changed during diagnostic: {relative}")
    support._write_new(args.output, payload)
    return {
        "diagnostic_id": diagnostic["diagnostic_id"], "output": str(args.output.resolve()),
        "output_sha256": hashlib.sha256(payload).hexdigest(), "output_size_bytes": len(payload),
        "metrics": diagnostic["metrics"], "gates": diagnostic["gates"],
        "coverage_violation_count": diagnostic["source_row_coverage_receipt"]["violation_count"],
        "release_authority": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repo-root", "corpus-index", "artifact-root", "source-pdf-root",
                 "temporary-root", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(build(args), sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print(f"FAIL-CLOSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
