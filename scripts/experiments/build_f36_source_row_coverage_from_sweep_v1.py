#!/usr/bin/env python3
"""Build F36 coverage offline using one explicitly bound worktree and DB snapshot.

Portable successor to archived build-f36-source-row-coverage-from-sweep-v1.py
(SHA-256 928536de0fb68a3729fb8576c8d38ca5f25e80d26291773053618d8b014d13de).
Coverage semantics remain in the family adapter. This tool does not certify
manual PDF review, run providers, update configuration, or write source stores.
Run as a fresh standalone CLI process with no concurrent code edits. The emitted
coverage receipt is not a full sweep replay or authenticated release certificate.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
GENERIC_RELATIVE = (
    "scripts/experiments/run_gemini_json_multitable_hierarchical_accounting_family_v1.py"
)
FROZEN_SHA256 = {
    GENERIC_RELATIVE: "d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5",
    "src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py":
        "bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2",
}
SPEC_NAMES = ("topology", "evaluation", "schema_binding", "source_repair")
ADAPTER_MODULE = "bctc_ai.evaluation.gemini_json_operating_expense_family_v1"
ACTIVE_CODE_RELATIVE = (
    "scripts/experiments/build_f36_source_row_coverage_from_sweep_v1.py",
    "src/bctc_ai/evaluation/gemini_json_operating_expense_family_v1.py",
)


class CoverageBuilderError(RuntimeError):
    """Fail closed when the active checkout, inputs, or output boundary drifts."""


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _object(path: Path, references: dict[str, dict[str, Any]]) -> dict[str, Any]:
    payload = path.read_bytes()
    value = json.loads(payload)
    if type(value) is not dict:
        raise CoverageBuilderError(f"Expected a JSON object: {path}")
    references[str(path.resolve())] = {
        "sha256": hashlib.sha256(payload).hexdigest(), "size_bytes": len(payload)
    }
    return value


def _verify_module_roots(source_root: Path) -> None:
    for name, module in tuple(sys.modules.items()):
        if name != "bctc_ai" and not name.startswith("bctc_ai."):
            continue
        location = getattr(module, "__file__", None)
        if not location or not Path(location).resolve().is_relative_to(source_root):
            raise CoverageBuilderError(f"Already imported project module from another checkout: {name}")


def _load_runtime(repo_root: Path) -> SimpleNamespace:
    root = repo_root.resolve(strict=True)
    if root != REPO_ROOT:
        raise CoverageBuilderError("--repo-root must identify the checkout containing this builder")
    for relative, expected in FROZEN_SHA256.items():
        if _hash(root / relative) != expected:
            raise CoverageBuilderError(f"Frozen runtime SHA-256 drift: {relative}")
    source_root = (root / "src").resolve(strict=True)
    _verify_module_roots(source_root)
    if ADAPTER_MODULE in sys.modules:
        raise CoverageBuilderError("Run coverage in a fresh process; family adapter already imported")
    sys.path.insert(0, str(source_root))
    adapter = importlib.import_module(ADAPTER_MODULE)
    contracts = importlib.import_module("bctc_ai.source_structure.contracts_v1")
    indexes = importlib.import_module("bctc_ai.storage.gemini_current_corpus_manifest_index_v1")
    name = "_f36_coverage_bound_generic_runner"
    spec = importlib.util.spec_from_file_location(name, root / GENERIC_RELATIVE)
    if spec is None or spec.loader is None:
        raise CoverageBuilderError("Cannot load the active frozen generic runner")
    generic = importlib.util.module_from_spec(spec)
    sys.modules[name] = generic
    spec.loader.exec_module(generic)
    _verify_module_roots(source_root)
    return SimpleNamespace(
        generic=generic,
        compile_specs=adapter.compile_gemini_json_operating_expense_family_specs_v1,
        build_coverage=adapter.build_operating_expense_source_row_coverage_receipt_v1,
        canonical_bytes=contracts.canonical_json_bytes_v1,
        validate_index=indexes.validate_current_corpus_manifest_index_v1,
    )


def _paths(args: argparse.Namespace) -> tuple[Path, Path, dict[str, Path]]:
    root = args.repo_root.resolve(strict=True)
    artifact_root = args.artifact_root.resolve(strict=True)
    temporary_root = args.temporary_root.resolve(strict=True)
    if root != REPO_ROOT:
        raise CoverageBuilderError("--repo-root must identify the checkout containing this builder")
    if not artifact_root.is_dir() or not temporary_root.is_dir():
        raise CoverageBuilderError("Artifact and temporary roots must be existing directories")
    for path in (args.output.resolve(), temporary_root):
        if path.is_relative_to(root) or path.is_relative_to(artifact_root):
            raise CoverageBuilderError("Output/temp paths must be outside the repository and corpus")
    if os.path.lexists(args.output):
        raise CoverageBuilderError("Refusing to overwrite an existing output or symlink")
    specs = {}
    for name in SPEC_NAMES:
        candidate = getattr(args, name, None)
        if candidate is None:
            candidate = root / f"config/families/tm-operating-expense-{name.replace('_', '-')}-v1.json"
        specs[name] = candidate.resolve(strict=True)
    return artifact_root, temporary_root, specs


@contextmanager
def _temporary_directory_root(root: Path):
    prior_tempdir = tempfile.tempdir
    prior_sqlite_tempdir = os.environ.get("SQLITE_TMPDIR")
    tempfile.tempdir = str(root)
    os.environ["SQLITE_TMPDIR"] = str(root)
    try:
        yield
    finally:
        tempfile.tempdir = prior_tempdir
        if prior_sqlite_tempdir is None:
            os.environ.pop("SQLITE_TMPDIR", None)
        else:
            os.environ["SQLITE_TMPDIR"] = prior_sqlite_tempdir


def _write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def build(args: argparse.Namespace) -> dict[str, Any]:
    artifact_root, temporary_root, spec_paths = _paths(args)
    code_sha256 = {relative: _hash(args.repo_root / relative) for relative in ACTIVE_CODE_RELATIVE}
    runtime = _load_runtime(args.repo_root)
    input_references: dict[str, dict[str, Any]] = {}
    sweep = _object(args.diagnostic, input_references)
    index = runtime.validate_index(_object(args.corpus_index, input_references))
    if sweep.get("family_id") != "OPERATING_EXPENSE":
        raise CoverageBuilderError("Diagnostic family mismatch")
    if sweep.get("corpus_manifest_index_id") != index["corpus_manifest_index_id"]:
        raise CoverageBuilderError("Diagnostic/index corpus mismatch")
    specs = [_object(spec_paths[name], input_references) for name in SPEC_NAMES]
    compiled = runtime.compile_specs(*specs)
    generic = runtime.generic
    database = generic._content_ref(artifact_root, index["database_ref"])
    selected_ids = generic._selected_page_axis(index=index, artifact_root=artifact_root)
    with _temporary_directory_root(temporary_root), generic._authenticated_sqlite_snapshot(
        database, reference=index["database_ref"]
    ) as guard:
        pages = generic._load_selected_pages_by_document(
            guard.path,
            selected_ids=selected_ids,
            selected_page_axis=sweep["indexed_query_evidence"]["selected_page_axis"],
        )
        receipt = runtime.build_coverage(
            indexed_query_evidence=sweep["indexed_query_evidence"],
            trials=sweep["trials"],
            page_json_by_document=pages,
            compiled_specs=compiled,
            fail_on_violation=True,
        )
    # Do not publish until the frozen snapshot's exit-time source checks also pass.
    for path, reference in input_references.items():
        if _hash(Path(path)) != reference["sha256"]:
            raise CoverageBuilderError(f"JSON input changed during coverage build: {path}")
    for relative, expected in FROZEN_SHA256.items():
        if _hash(args.repo_root / relative) != expected:
            raise CoverageBuilderError(f"Frozen runtime changed during coverage build: {relative}")
    payload = runtime.canonical_bytes(receipt)
    for relative, expected in code_sha256.items():
        if _hash(args.repo_root / relative) != expected:
            raise CoverageBuilderError(f"Active code changed during coverage build: {relative}")
    _write_new(args.output, payload)
    return {
        "candidate_table_total_rows": len(receipt["candidate_table_total_row_axis"]),
        "output": str(args.output.resolve()),
        "output_sha256": hashlib.sha256(payload).hexdigest(),
        "output_size_bytes": len(payload),
        "raw_target_like_rows": len(receipt["raw_target_like_row_axis"]),
        "receipt_id": receipt["receipt_id"],
        "source_rows": len(receipt["source_row_axis"]),
        "violations": receipt["violation_count"],
        "repo_root": str(args.repo_root.resolve()),
        "config_sha256": {
            name: input_references[str(path)]["sha256"] for name, path in spec_paths.items()
        },
        "input_references": input_references,
        "frozen_sha256": FROZEN_SHA256,
        "code_sha256": code_sha256,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in (
        "repo-root", "diagnostic", "corpus-index", "artifact-root", "temporary-root", "output"
    ):
        parser.add_argument(f"--{argument}", type=Path, required=True)
    for name in SPEC_NAMES:
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(build(args), sort_keys=True))
        return 0
    except (CoverageBuilderError, OSError, ValueError, KeyError, RuntimeError) as exc:
        print(f"FAIL-CLOSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
