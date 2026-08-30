#!/usr/bin/env python3
"""Run one externally pinned, bounded whole-table roll-forward repair frontier.

Dry-run is the default-safe operational boundary: it authenticates every input,
rebuilds the exact plans from the selected SQLite frontier, renders the bound PDF
pages, crops the declared tables, and writes immutable request artifacts.  The
OpenRouter mode adds at most one low, medium, and high sibling request per job,
persists accepted merged pages only in a caller-provided copy of the page store,
and emits an overlay for a later family run.  This runner never selects OFFICIAL.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.gemini_json_first_provider_v1 import (  # noqa: E402
    OPENROUTER_MODEL,
    OPENROUTER_PROVIDER,
    OPENROUTER_SERVICE_TIER,
    GeminiJsonFirstProviderV1Error,
    ProviderResultV1,
    call_gemini_json_first_v1,
    load_openrouter_api_key_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    READY,
    UNRESOLVED,
    compile_gemini_json_flat_family_specs_v1,
)
from bctc_ai.evaluation.gemini_json_rollforward_table_repair_v1 import (  # noqa: E402
    GeminiJsonRollforwardTableRepairV1Error,
    build_accounting_table_cell_repair_plans_v1,
    build_rollforward_table_repair_attempt_v1,
    build_rollforward_table_repair_overlay_v1,
    build_rollforward_table_repair_prompt_v1,
    build_rollforward_table_repair_spec_authority_v1,
    crop_rollforward_table_image_v1,
    decode_rollforward_table_repair_text_v1,
    load_rollforward_table_page_evidence_v1,
    merge_rollforward_table_repair_v1,
    resolve_rollforward_table_source_image_v1,
    rollforward_table_repair_plan_authority_v1,
    rollforward_table_repair_response_schema_v1,
    rollforward_table_repair_target_v1,
    validate_rollforward_source_image_resolver_implementation_v1,
    validate_rollforward_table_source_corroboration_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.storage.gemini_accounting_family_store_v1 import (  # noqa: E402
    enqueue_gemini_family_region_repair_plans_v1,
    record_gemini_family_region_repair_attempt_v1,
    resolved_gemini_family_region_repair_overlay_v1,
)
from bctc_ai.storage.gemini_family_effective_page_frontier_v1 import (  # noqa: E402
    apply_gemini_family_effective_page_frontier_v1,
    build_gemini_family_effective_page_frontier_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    ingest_financial_page_extraction_v1,
    initialize_region_repair_extension_v1,
    record_page_json_region_repair_v1,
)

FORMAT_VERSION = "GEMINI_JSON_ROLLFORWARD_TABLE_REPAIR_RUNNER_V1"
CONFIG_FORMAT_VERSION = "GEMINI_JSON_ROLLFORWARD_TABLE_REPAIR_RUNNER_CONFIG_V1"
ATTEMPT_ARTIFACT_MANIFEST_FORMAT_VERSION = (
    "GEMINI_JSON_ROLLFORWARD_TABLE_REPAIR_ATTEMPT_ARTIFACT_MANIFEST_V1"
)
ATTEMPT_ARTIFACT_AXIS_FORMAT_VERSION = (
    "GEMINI_JSON_ROLLFORWARD_TABLE_REPAIR_ATTEMPT_ARTIFACT_AXIS_V1"
)
CAPTURE_CHECKPOINT_FORMAT_VERSION = "GEMINI_JSON_ROLLFORWARD_TABLE_REPAIR_CAPTURE_CHECKPOINT_V1"
SEALED_OBSERVATION_ADOPTION_AUTHORITY_FORMAT_VERSION = (
    "GEMINI_JSON_ROLLFORWARD_SEALED_OBSERVATION_ADOPTION_AUTHORITY_V1"
)
SEALED_OBSERVATION_SOURCE_LINK_FORMAT_VERSION = (
    "GEMINI_JSON_ROLLFORWARD_SEALED_OBSERVATION_SOURCE_LINK_V1"
)
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_VERSION_ID = re.compile(r"^gfpstorev1:json:[0-9a-f]{64}$")
_FAMILY_RUN_ID = re.compile(r"^gjfafstorev1:run:[0-9a-f]{64}$")
_CORPUS_INDEX_ID = re.compile(r"^gjfccmiv1:index:[0-9a-f]{64}$")
_THINKING_LEVELS = ("low", "medium", "high")
RUNNER_IMPLEMENTATION_PATH = "scripts/experiments/run_gemini_json_rollforward_table_repair_v1.py"
PROJECTOR_IMPLEMENTATION_PATH = "src/bctc_ai/evaluation/gemini_json_rollforward_table_repair_v1.py"
PROJECTOR_IMPLEMENTATION_SHA256 = "b6176da21db3a6e3ab70bcc70684087510ac15171c2c798ac4e1b1e559a20fef"
DETERMINISTIC_PROJECTION_CONTRACT_VERSION = (
    "GEMINI_JSON_ROLLFORWARD_TARGET_OBSERVATION_PROJECTION_CONTRACT_V1"
)
_CONFIG_FIELDS = {
    "authority_kind",
    "authority_ref",
    "base_corpus_manifest_index_id",
    "expected_plan_count",
    "expected_selected_page_count",
    "expected_selected_page_frontier_sha256",
    "format_version",
    "repair_source_family_run_id",
    "source_image_resolver_implementation_path",
    "source_image_runtime",
    "table_repair_specs",
    "writable_page_store_ref_path",
    "writable_results_database_ref_path",
}


class RunGeminiJsonRollforwardTableRepairV1Error(RuntimeError):
    """The operational repair frontier is not exact, bounded, or immutable."""


@dataclass(frozen=True)
class _PinnedJson:
    path: Path
    raw: bytes
    sha256: str
    value: Any


@dataclass(frozen=True)
class _PreparedJob:
    ordinal: int
    plan: dict[str, Any]
    base_page_json: dict[str, Any]
    source_image: bytes
    source_resolution_receipt: dict[str, Any]
    crop_image: bytes
    crop_receipt: dict[str, Any]
    target: dict[str, Any]
    prompt: str
    response_schema: dict[str, Any]


@dataclass(frozen=True)
class _PreparedRun:
    compiled_specs: dict[str, Any]
    family_sweep: dict[str, Any]
    selected_ids: list[str]
    config: dict[str, Any]
    authority: dict[str, Any]
    repair_spec_authority: dict[str, Any]
    plans: list[dict[str, Any]]
    jobs: list[_PreparedJob]
    pinned_inputs: dict[str, _PinnedJson]
    baseline_run_receipt: dict[str, Any]
    projector_implementation_ref: dict[str, Any]
    runner_implementation_ref: dict[str, Any]


@dataclass(frozen=True)
class _ProviderObservation:
    result: ProviderResultV1 | None
    error: GeminiJsonFirstProviderV1Error | None
    elapsed_seconds: str


@dataclass(frozen=True)
class _SealedObservationAdoptionItem:
    job_id: str
    source_attempt: dict[str, Any]
    source_link: dict[str, Any]
    thinking_level: str
    observation: _ProviderObservation


@dataclass(frozen=True)
class _SealedObservationAdoption:
    authority: dict[str, Any]
    items_by_job: dict[str, list[_SealedObservationAdoptionItem]]


@dataclass(frozen=True)
class _SqliteBoundary:
    descriptor: int
    identity: tuple[int, int]
    initial_sha256: str
    initial_size_bytes: int
    label: str
    original_path: Path
    private_path: Path
    writable: bool


def _error(message: str) -> RunGeminiJsonRollforwardTableRepairV1Error:
    return RunGeminiJsonRollforwardTableRepairV1Error(message)


def _require_all_planned_jobs_resolved(result: Mapping[str, Any], *, disposition: str) -> None:
    job_count = result.get("job_count")
    if (
        result.get("disposition") != disposition
        or type(job_count) is not int
        or job_count <= 0
        or result.get("job_status_counts") != {"ABSTAINED": 0, "RESOLVED": job_count}
    ):
        raise _error("terminal repair result is not an all-planned-jobs-resolved frontier")


def _sha_file(path: Path) -> tuple[str, int]:
    digest = sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _sha_descriptor(descriptor: int) -> tuple[str, int]:
    digest = sha256()
    offset = 0
    while chunk := os.pread(descriptor, 1024 * 1024, offset):
        digest.update(chunk)
        offset += len(chunk)
    return digest.hexdigest(), offset


def _sqlite_sidecars(path: Path) -> tuple[Path, Path, Path]:
    return tuple(Path(str(path) + suffix) for suffix in ("-wal", "-shm", "-journal"))


def _reject_sqlite_sidecars(path: Path, *, label: str) -> None:
    if any(sidecar.exists() or sidecar.is_symlink() for sidecar in _sqlite_sidecars(path)):
        raise _error(f"{label} has an unbound SQLite sidecar")


def _regular_file(path: Path, *, label: str) -> Path:
    candidate = Path(path)
    descriptor_path = (
        len(candidate.parts) == 5
        and candidate.parts[:4] == ("/", "proc", "self", "fd")
        and candidate.parts[4].isdigit()
    )
    resolved = candidate.resolve()
    if (candidate.is_symlink() and not descriptor_path) or not resolved.is_file():
        raise _error(f"{label} must be one regular, non-symlink file")
    return candidate if descriptor_path else resolved


def _expected_hash(value: str, *, label: str) -> str:
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        raise _error(f"{label} must be one lowercase SHA-256")
    return value


def _copy_descriptor_to_new_file(
    descriptor: int,
    destination: Path,
    *,
    mode: int,
) -> tuple[str, int]:
    if not hasattr(os, "O_NOFOLLOW"):
        raise _error("this platform cannot establish a no-follow SQLite boundary")
    output_descriptor = os.open(
        destination,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
        mode,
    )
    digest = sha256()
    offset = 0
    try:
        while chunk := os.pread(descriptor, 1024 * 1024, offset):
            digest.update(chunk)
            written = 0
            while written < len(chunk):
                count = os.write(output_descriptor, chunk[written:])
                if count <= 0:
                    raise _error("private SQLite snapshot write made no progress")
                written += count
            offset += len(chunk)
        os.fsync(output_descriptor)
    finally:
        os.close(output_descriptor)
    os.chmod(destination, mode)
    return digest.hexdigest(), offset


def _establish_sqlite_boundary(
    path: Path,
    expected_sha256: str,
    *,
    label: str,
    private_path: Path,
    writable: bool,
    copy_to_private: bool = True,
) -> _SqliteBoundary:
    if not hasattr(os, "O_NOFOLLOW"):
        raise _error("this platform cannot establish a no-follow SQLite boundary")
    candidate = Path(path)
    if candidate.is_symlink():
        raise _error(f"{label} must be one regular, non-symlink file")
    try:
        resolved = candidate.resolve(strict=True)
        flags = os.O_CLOEXEC | os.O_NOFOLLOW | (os.O_RDWR if writable else os.O_RDONLY)
        descriptor = os.open(resolved, flags)
    except OSError as exc:
        raise _error(f"{label} cannot be opened through a no-follow file descriptor") from exc
    try:
        descriptor_stat = os.fstat(descriptor)
        path_stat = os.stat(resolved, follow_symlinks=False)
        identity = (descriptor_stat.st_dev, descriptor_stat.st_ino)
        if (
            not stat.S_ISREG(descriptor_stat.st_mode)
            or not stat.S_ISREG(path_stat.st_mode)
            or identity != (path_stat.st_dev, path_stat.st_ino)
        ):
            raise _error(f"{label} file identity changed while opening")
        _reject_sqlite_sidecars(resolved, label=label)
        expected = _expected_hash(expected_sha256, label=f"{label} expected SHA-256")
        if copy_to_private:
            actual, size = _copy_descriptor_to_new_file(
                descriptor,
                private_path,
                mode=0o600 if writable else 0o400,
            )
            working_path = private_path
        else:
            actual, size = _sha_descriptor(descriptor)
            working_path = Path(f"/proc/self/fd/{descriptor}")
        if actual != expected or size != descriptor_stat.st_size:
            raise _error(f"{label} bytes do not match the caller pin")
        if _sha_file(working_path) != (actual, size):
            raise _error(f"{label} stable view or work copy differs from its held descriptor")
        return _SqliteBoundary(
            descriptor=descriptor,
            identity=identity,
            initial_sha256=actual,
            initial_size_bytes=size,
            label=label,
            original_path=resolved,
            private_path=working_path,
            writable=writable,
        )
    except Exception:
        os.close(descriptor)
        raise


def _assert_sqlite_boundary_current(
    boundary: _SqliteBoundary,
    *,
    expected_sha256: str,
    expected_size_bytes: int,
) -> None:
    _reject_sqlite_sidecars(boundary.original_path, label=boundary.label)
    try:
        path_stat = os.stat(boundary.original_path, follow_symlinks=False)
        descriptor_stat = os.fstat(boundary.descriptor)
    except OSError as exc:
        raise _error(f"{boundary.label} path or held descriptor is no longer available") from exc
    if (
        not stat.S_ISREG(path_stat.st_mode)
        or not stat.S_ISREG(descriptor_stat.st_mode)
        or (path_stat.st_dev, path_stat.st_ino) != boundary.identity
        or (descriptor_stat.st_dev, descriptor_stat.st_ino) != boundary.identity
        or _sha_descriptor(boundary.descriptor) != (expected_sha256, expected_size_bytes)
    ):
        raise _error(f"{boundary.label} path, inode, or bytes changed across the stable boundary")


def _publish_private_sqlite(boundary: _SqliteBoundary) -> tuple[str, int]:
    if not boundary.writable:
        raise _error("a read-only SQLite snapshot cannot be published")
    _reject_sqlite_sidecars(boundary.private_path, label=f"private {boundary.label}")
    private_sha256, private_size = _sha_file(boundary.private_path)
    _assert_sqlite_boundary_current(
        boundary,
        expected_sha256=boundary.initial_sha256,
        expected_size_bytes=boundary.initial_size_bytes,
    )
    if (private_sha256, private_size) != (
        boundary.initial_sha256,
        boundary.initial_size_bytes,
    ):
        private_descriptor = os.open(
            boundary.private_path,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
        )
        try:
            os.ftruncate(boundary.descriptor, 0)
            offset = 0
            while chunk := os.pread(private_descriptor, 1024 * 1024, offset):
                written = 0
                while written < len(chunk):
                    count = os.pwrite(
                        boundary.descriptor,
                        chunk[written:],
                        offset + written,
                    )
                    if count <= 0:
                        raise _error(f"{boundary.label} publish made no progress")
                    written += count
                offset += len(chunk)
            if offset != private_size:
                raise _error(f"private {boundary.label} changed while publishing")
            os.fsync(boundary.descriptor)
        finally:
            os.close(private_descriptor)
    _assert_sqlite_boundary_current(
        boundary,
        expected_sha256=private_sha256,
        expected_size_bytes=private_size,
    )
    return private_sha256, private_size


def _overwrite_descriptor_from_descriptor(destination: int, source: int, *, label: str) -> None:
    os.ftruncate(destination, 0)
    offset = 0
    while chunk := os.pread(source, 1024 * 1024, offset):
        written = 0
        while written < len(chunk):
            count = os.pwrite(destination, chunk[written:], offset + written)
            if count <= 0:
                raise _error(f"{label} rollback made no progress")
            written += count
        offset += len(chunk)
    os.fsync(destination)


def _rollback_published_sqlite_pair(
    writable_store: _SqliteBoundary,
    writable_results: _SqliteBoundary,
    source_store: _SqliteBoundary,
    source_results: _SqliteBoundary,
) -> None:
    errors = []
    for writable, source in (
        (writable_store, source_store),
        (writable_results, source_results),
    ):
        try:
            _overwrite_descriptor_from_descriptor(
                writable.descriptor,
                source.descriptor,
                label=writable.label,
            )
            _assert_sqlite_boundary_current(
                writable,
                expected_sha256=writable.initial_sha256,
                expected_size_bytes=writable.initial_size_bytes,
            )
        except Exception as exc:  # pragma: no cover - catastrophic I/O is not safely maskable.
            errors.append(f"{writable.label}: {type(exc).__name__}: {exc}")
    if errors:
        raise _error("SQLite pair rollback failed: " + "; ".join(errors))


def _publish_private_sqlite_pair(
    writable_store: _SqliteBoundary,
    writable_results: _SqliteBoundary,
    source_store: _SqliteBoundary,
    source_results: _SqliteBoundary,
) -> tuple[tuple[str, int], tuple[str, int]]:
    """Publish both work databases or restore both caller files to their pinned baseline."""

    try:
        published_store = _publish_private_sqlite(writable_store)
        published_results = _publish_private_sqlite(writable_results)
    except Exception:
        _rollback_published_sqlite_pair(
            writable_store,
            writable_results,
            source_store,
            source_results,
        )
        raise
    return published_store, published_results


def _close_sqlite_boundaries(boundaries: Sequence[_SqliteBoundary]) -> None:
    for boundary in reversed(boundaries):
        try:
            os.close(boundary.descriptor)
        except OSError:
            pass


def _read_pinned_json(path: Path, expected_sha256: str, *, label: str) -> _PinnedJson:
    resolved = _regular_file(path, label=label)
    expected = _expected_hash(expected_sha256, label=f"{label} expected SHA-256")
    raw = resolved.read_bytes()
    actual = sha256(raw).hexdigest()
    if actual != expected:
        raise _error(f"{label} bytes do not match the caller-pinned SHA-256")
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"{label} is not valid JSON") from exc
    return _PinnedJson(path=resolved, raw=raw, sha256=actual, value=value)


def _validate_source_store(path: Path, expected_sha256: str) -> tuple[Path, str, int]:
    resolved = _regular_file(path, label="frozen source page store")
    _reject_sqlite_sidecars(resolved, label="frozen source page store")
    expected = _expected_hash(expected_sha256, label="source page-store expected SHA-256")
    actual, size = _sha_file(resolved)
    if actual != expected:
        raise _error("frozen source page-store bytes do not match the caller pin")
    return resolved, actual, size


def _validate_pinned_binary(
    path: Path,
    expected_sha256: str,
    *,
    label: str,
) -> tuple[Path, str, int]:
    resolved = _regular_file(path, label=label)
    _reject_sqlite_sidecars(resolved, label=label)
    expected = _expected_hash(expected_sha256, label=f"{label} expected SHA-256")
    actual, size = _sha_file(resolved)
    if actual != expected:
        raise _error(f"{label} bytes do not match the caller pin")
    return resolved, actual, size


def _validate_config(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _CONFIG_FIELDS:
        raise _error("repair-spec runner config fields drifted")
    if (
        value["format_version"] != CONFIG_FORMAT_VERSION
        or value["authority_kind"] not in {"PINNED_CONFIG", "PINNED_EVIDENCE"}
        or type(value["authority_ref"]) is not str
        or not value["authority_ref"]
        or type(value["expected_plan_count"]) is not int
        or value["expected_plan_count"] <= 0
        or type(value["expected_selected_page_count"]) is not int
        or value["expected_selected_page_count"] <= 0
        or _expected_hash(
            value["expected_selected_page_frontier_sha256"],
            label="configured selected page frontier SHA-256",
        )
        != value["expected_selected_page_frontier_sha256"]
        or type(value["base_corpus_manifest_index_id"]) is not str
        or _CORPUS_INDEX_ID.fullmatch(value["base_corpus_manifest_index_id"]) is None
        or type(value["repair_source_family_run_id"]) is not str
        or _FAMILY_RUN_ID.fullmatch(value["repair_source_family_run_id"]) is None
        or type(value["table_repair_specs"]) is not list
        or not value["table_repair_specs"]
        or len(value["table_repair_specs"]) != value["expected_plan_count"]
        or type(value["source_image_resolver_implementation_path"]) is not str
        or not value["source_image_resolver_implementation_path"]
        or type(value["source_image_runtime"]) is not dict
        or set(value["source_image_runtime"]) != {"mupdf_version", "pymupdf_version"}
        or any(
            type(value["source_image_runtime"][field]) is not str
            or not value["source_image_runtime"][field]
            for field in ("mupdf_version", "pymupdf_version")
        )
    ):
        raise _error("repair-spec runner config is invalid")
    relative = PurePosixPath(value["source_image_resolver_implementation_path"])
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise _error("repair-spec source-image resolver path is invalid")
    for field in ("writable_page_store_ref_path", "writable_results_database_ref_path"):
        if type(value[field]) is not str or not value[field]:
            raise _error("effective-frontier database reference path is invalid")
        reference = PurePosixPath(value[field])
        if reference.is_absolute() or ".." in reference.parts:
            raise _error("effective-frontier database reference path is invalid")
    if value["writable_page_store_ref_path"] == value["writable_results_database_ref_path"]:
        raise _error("effective-frontier page and results database refs collide")
    return json.loads(canonical_json_bytes_v1(value))


def _validate_selected_ids(value: Any, *, expected_count: int) -> list[str]:
    if (
        type(value) is not list
        or len(value) != expected_count
        or len(set(value)) != len(value)
        or any(type(item) is not str or _VERSION_ID.fullmatch(item) is None for item in value)
    ):
        raise _error("selected page JSON version frontier is not the exact configured axis")
    return list(value)


def _validate_selected_frontier_pin(selected_ids: Sequence[str], expected_sha256: str) -> None:
    if canonical_json_sha256_v1(list(selected_ids)) != expected_sha256:
        raise _error("selected page JSON version order differs from the external authority")


def _renderer_pin(workspace_root: Path, relative_path: str) -> tuple[str, int]:
    root_input = Path(workspace_root)
    root = root_input.resolve()
    if root_input.is_symlink() or not root.is_dir():
        raise _error("source workspace root must be one non-symlink directory")
    relative = PurePosixPath(relative_path)
    path = root.joinpath(*relative.parts).resolve()
    if not path.is_relative_to(root) or path.is_symlink() or not path.is_file():
        raise _error("pinned source-image resolver implementation is absent")
    return _sha_file(path)


def _runner_pin(workspace_root: Path, expected_sha256: str) -> dict[str, Any]:
    root_input = Path(workspace_root)
    root = root_input.resolve()
    if root_input.is_symlink() or not root.is_dir():
        raise _error("runner workspace root must be one non-symlink directory")
    expected_path = root.joinpath(*PurePosixPath(RUNNER_IMPLEMENTATION_PATH).parts).resolve()
    executed_path = Path(__file__).resolve()
    if (
        not expected_path.is_relative_to(root)
        or expected_path.is_symlink()
        or not expected_path.is_file()
        or executed_path != expected_path
    ):
        raise _error("executed repair runner differs from its workspace implementation path")
    actual, size = _sha_file(expected_path)
    if actual != _expected_hash(expected_sha256, label="runner implementation expected SHA-256"):
        raise _error("executed repair runner bytes differ from the caller pin")
    return {"path": RUNNER_IMPLEMENTATION_PATH, "sha256": actual, "size_bytes": size}


def _projector_pin(workspace_root: Path) -> dict[str, Any]:
    root = Path(workspace_root).resolve()
    expected = root.joinpath(*PurePosixPath(PROJECTOR_IMPLEMENTATION_PATH).parts).resolve()
    executed = Path(decode_rollforward_table_repair_text_v1.__code__.co_filename).resolve()
    if (
        not expected.is_relative_to(root)
        or expected.is_symlink()
        or not expected.is_file()
        or executed != expected
    ):
        raise _error("executed target-observation projector differs from its workspace path")
    actual, size = _sha_file(expected)
    if actual != PROJECTOR_IMPLEMENTATION_SHA256:
        raise _error("executed target-observation projector differs from its runner pin")
    return {"path": PROJECTOR_IMPLEMENTATION_PATH, "sha256": actual, "size_bytes": size}


def _deterministic_projection_schema_v1() -> dict[str, Any]:
    """Schema for stored algorithm output, distinct from the Gemini request schema."""

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "additionalProperties": False,
        "properties": {
            "format_version": {"type": "string"},
            "observations": {"type": "array"},
            "projection_diagnostics": {"type": "object"},
            "projection_sha256": {"pattern": "^[0-9a-f]{64}$", "type": "string"},
            "source_response": {"type": "object"},
        },
        "required": [
            "format_version",
            "observations",
            "projection_diagnostics",
            "projection_sha256",
            "source_response",
        ],
        "title": DETERMINISTIC_PROJECTION_CONTRACT_VERSION,
        "type": "object",
    }


def _validate_baseline_family_run(
    results_database: Path,
    *,
    family_sweep: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        connection = sqlite3.connect(f"file:{results_database}?mode=ro&immutable=1", uri=True)
        connection.row_factory = sqlite3.Row
        identity = connection.execute(
            "SELECT format_version FROM store_identity WHERE singleton=1"
        ).fetchone()
        row = connection.execute(
            "SELECT family_run_id,sweep_id,family_id,corpus_manifest_index_id,"
            "sweep_sha256,sweep_bytes FROM family_run WHERE family_run_id=?",
            (config["repair_source_family_run_id"],),
        ).fetchone()
    except sqlite3.DatabaseError as exc:
        raise _error("pinned source family-results database cannot be replayed") from exc
    finally:
        if "connection" in locals():
            connection.close()
    if identity is None or identity["format_version"] != "GEMINI_ACCOUNTING_FAMILY_STORE_V1":
        raise _error("pinned source family-results database identity drifted")
    if row is None:
        raise _error("configured repair source family run is absent")
    canonical_sweep = canonical_json_bytes_v1(dict(family_sweep)) + b"\n"
    if (
        row["family_run_id"] != config["repair_source_family_run_id"]
        or row["sweep_id"] != family_sweep.get("sweep_id")
        or row["family_id"] != family_sweep.get("family_id")
        or row["corpus_manifest_index_id"] != config["base_corpus_manifest_index_id"]
        or family_sweep.get("corpus_manifest_index_id") != config["base_corpus_manifest_index_id"]
        or row["sweep_sha256"] != sha256(canonical_sweep).hexdigest()
        or bytes(row["sweep_bytes"]) != canonical_sweep
    ):
        raise _error("configured family run does not bind the exact base sweep and corpus")
    return {
        "corpus_manifest_index_id": row["corpus_manifest_index_id"],
        "family_id": row["family_id"],
        "family_run_id": row["family_run_id"],
        "sweep_id": row["sweep_id"],
        "sweep_sha256": row["sweep_sha256"],
    }


def _prepare(
    *,
    sweep: _PinnedJson,
    selected: _PinnedJson,
    repair_config: _PinnedJson,
    source_page_store: Path,
    source_results_database: Path,
    workspace_root: Path,
    runner_implementation_sha256: str,
) -> _PreparedRun:
    if type(sweep.value) is not dict:
        raise _error("family sweep must be one JSON object")
    config = _validate_config(repair_config.value)
    selected_ids = _validate_selected_ids(
        selected.value,
        expected_count=config["expected_selected_page_count"],
    )
    _validate_selected_frontier_pin(
        selected_ids,
        config["expected_selected_page_frontier_sha256"],
    )
    baseline_run_receipt = _validate_baseline_family_run(
        source_results_database,
        family_sweep=sweep.value,
        config=config,
    )
    runner_implementation_ref = _runner_pin(
        workspace_root,
        runner_implementation_sha256,
    )
    projector_implementation_ref = _projector_pin(workspace_root)
    compiled_spec_sources = {
        "evaluation": sweep.value["specs"]["evaluation"]["value"],
        "schema_binding": sweep.value["specs"]["schema_binding"]["value"],
        "topology": sweep.value["specs"]["topology"]["value"],
    }
    compiled_specs = compile_gemini_json_flat_family_specs_v1(
        compiled_spec_sources["topology"],
        compiled_spec_sources["evaluation"],
        compiled_spec_sources["schema_binding"],
    )
    plans = build_accounting_table_cell_repair_plans_v1(
        compiled_specs=compiled_specs,
        family_sweep=sweep.value,
        page_store_path=source_page_store,
        selected_page_json_version_ids=selected_ids,
        table_repair_specs=config["table_repair_specs"],
    )
    if len(plans) != config["expected_plan_count"] or len(
        {plan["repair_job_id"] for plan in plans}
    ) != len(plans):
        raise _error("authoritative plan replay does not produce the exact configured job count")
    authority = rollforward_table_repair_plan_authority_v1(
        compiled_spec_sources=compiled_spec_sources,
        family_sweep=sweep.value,
        selected_page_json_version_ids=selected_ids,
        table_repair_specs=config["table_repair_specs"],
    )
    renderer_sha, renderer_size = _renderer_pin(
        workspace_root,
        config["source_image_resolver_implementation_path"],
    )
    repair_spec_authority = build_rollforward_table_repair_spec_authority_v1(
        authority_kind=config["authority_kind"],
        authority_ref=config["authority_ref"],
        authority_sha256=repair_config.sha256,
        source_image_resolver_implementation_path=config[
            "source_image_resolver_implementation_path"
        ],
        source_image_resolver_implementation_sha256=renderer_sha,
        source_image_resolver_implementation_size_bytes=renderer_size,
        source_image_resolver_mupdf_version=config["source_image_runtime"]["mupdf_version"],
        source_image_resolver_pymupdf_version=config["source_image_runtime"]["pymupdf_version"],
        table_repair_specs=config["table_repair_specs"],
        plans=plans,
    )
    validate_rollforward_source_image_resolver_implementation_v1(
        workspace_root,
        resolver=repair_spec_authority["source_image_resolver"],
    )
    evidence = load_rollforward_table_page_evidence_v1(
        source_page_store,
        page_json_version_ids=[plan["base_page_json_version_id"] for plan in plans],
    )
    evidence_by_version = {item["base_page_json_version_id"]: item for item in evidence}
    schema = rollforward_table_repair_response_schema_v1()
    jobs = []
    for ordinal, plan in enumerate(plans, start=1):
        base = evidence_by_version[plan["base_page_json_version_id"]]["page_json"]
        target = rollforward_table_repair_target_v1(base, plan=plan)
        prompt = build_rollforward_table_repair_prompt_v1(
            base_page_json_version_id=plan["base_page_json_version_id"],
            target=target,
        )
        if (
            sha256(prompt.encode("utf-8")).hexdigest() != plan["request_contract"]["prompt_sha256"]
            or canonical_json_sha256_v1(schema)
            != plan["request_contract"]["response_schema_sha256"]
        ):
            raise _error("prepared request does not replay the authoritative plan")
        source_image, source_receipt = resolve_rollforward_table_source_image_v1(
            workspace_root,
            plan=plan,
            authority=authority,
            repair_spec_authority=repair_spec_authority,
            page_store_path=source_page_store,
            _prevalidated_plan_axis=plans,
        )
        crop_image, crop_receipt = crop_rollforward_table_image_v1(
            source_image,
            plan=plan,
            authority=authority,
            repair_spec_authority=repair_spec_authority,
            page_store_path=source_page_store,
            _prevalidated_plan_axis=plans,
        )
        jobs.append(
            _PreparedJob(
                ordinal=ordinal,
                plan=plan,
                base_page_json=base,
                source_image=source_image,
                source_resolution_receipt=source_receipt,
                crop_image=crop_image,
                crop_receipt=crop_receipt,
                target=target,
                prompt=prompt,
                response_schema=schema,
            )
        )
    return _PreparedRun(
        compiled_specs=compiled_specs,
        family_sweep=sweep.value,
        selected_ids=selected_ids,
        config=config,
        authority=authority,
        repair_spec_authority=repair_spec_authority,
        plans=plans,
        jobs=jobs,
        pinned_inputs={
            "family-sweep.json": sweep,
            "selected-page-json-version-ids.json": selected,
            "repair-spec-config.json": repair_config,
        },
        baseline_run_receipt=baseline_run_receipt,
        projector_implementation_ref=projector_implementation_ref,
        runner_implementation_ref=runner_implementation_ref,
    )


def _claim_output(path: Path) -> Path:
    candidate = Path(path)
    if candidate.is_symlink():
        raise _error("artifact output cannot be a symlink")
    if candidate.exists():
        if not candidate.is_dir() or any(candidate.iterdir()):
            raise _error("artifact output already exists and is not empty")
    else:
        candidate.mkdir(parents=True, mode=0o700)
    return candidate.resolve()


def _write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o444)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def _write_json(path: Path, value: Any) -> None:
    _write_new(path, canonical_json_bytes_v1(value) + b"\n")


def _ref(output: Path, path: Path, payload: bytes) -> dict[str, Any]:
    return {
        "path": path.relative_to(output).as_posix(),
        "sha256": sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _authenticated_artifact_ref(output: Path, reference: Mapping[str, Any]) -> Path:
    if type(reference) is not dict or set(reference) != {"path", "sha256", "size_bytes"}:
        raise _error("repair artifact content reference fields drifted")
    relative = PurePosixPath(reference["path"])
    if (
        relative.is_absolute()
        or not relative.parts
        or ".." in relative.parts
        or type(reference["sha256"]) is not str
        or _HEX64.fullmatch(reference["sha256"]) is None
        or type(reference["size_bytes"]) is not int
        or reference["size_bytes"] <= 0
    ):
        raise _error("repair artifact content reference is invalid")
    path = output.joinpath(*relative.parts)
    cursor = output
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise _error("repair artifact content reference crosses a symlink")
    resolved = path.resolve()
    if not resolved.is_relative_to(output) or not resolved.is_file():
        raise _error("repair artifact content reference is absent")
    actual_sha, actual_size = _sha_file(resolved)
    if (actual_sha, actual_size) != (reference["sha256"], reference["size_bytes"]):
        raise _error("repair artifact content reference does not authenticate")
    return resolved


def _validate_attempt_artifact_manifest(
    output: Path,
    manifest: Any,
) -> dict[str, Any]:
    if type(manifest) is not dict or set(manifest) != {
        "artifacts",
        "attempt_id",
        "format_version",
        "manifest_sha256",
        "repair_job_id",
    }:
        raise _error("attempt artifact manifest fields drifted")
    if (
        manifest["format_version"] != ATTEMPT_ARTIFACT_MANIFEST_FORMAT_VERSION
        or type(manifest["attempt_id"]) is not str
        or not manifest["attempt_id"].startswith("gjfrtav1:attempt:")
        or type(manifest["repair_job_id"]) is not str
        or not manifest["repair_job_id"].startswith("gjfrrqv1:job:")
        or type(manifest["artifacts"]) is not dict
        or not manifest["artifacts"]
        or any(type(name) is not str or not name for name in manifest["artifacts"])
    ):
        raise _error("attempt artifact manifest is invalid")
    required = {
        "attempt.json",
        "observation.json",
        "provider-attempts.json",
        "provider.json",
        "request.json",
        "usage.json",
        "validation.json",
    }
    if not required <= set(manifest["artifacts"]):
        raise _error("attempt artifact manifest omits one required artifact")
    material = {key: manifest[key] for key in manifest if key != "manifest_sha256"}
    if manifest["manifest_sha256"] != canonical_json_sha256_v1(material):
        raise _error("attempt artifact manifest identity does not replay")
    for reference in manifest["artifacts"].values():
        _authenticated_artifact_ref(output, reference)
    return json.loads(canonical_json_bytes_v1(manifest))


def _seal_attempt_artifacts(
    output: Path,
    attempt_root: Path,
    attempt: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    artifacts = {}
    for path in sorted(attempt_root.iterdir(), key=lambda item: item.name):
        if path.is_symlink() or not path.is_file():
            raise _error("attempt artifact set contains a non-regular entry")
        payload = path.read_bytes()
        artifacts[path.name] = _ref(output, path, payload)
    material = {
        "artifacts": artifacts,
        "attempt_id": attempt["attempt_id"],
        "format_version": ATTEMPT_ARTIFACT_MANIFEST_FORMAT_VERSION,
        "repair_job_id": attempt["repair_job_id"],
    }
    manifest = {**material, "manifest_sha256": canonical_json_sha256_v1(material)}
    checked = _validate_attempt_artifact_manifest(output, manifest)
    payload = canonical_json_bytes_v1(checked) + b"\n"
    path = attempt_root / "attempt-artifact-manifest.json"
    _write_new(path, payload)
    return checked, _ref(output, path, payload)


def _json_artifact(output: Path, reference: Mapping[str, Any], *, label: str) -> Any:
    path = _authenticated_artifact_ref(output, reference)
    try:
        return json.loads(path.read_bytes())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"{label} is not valid JSON") from exc


def _provider_result_from_sealed_artifacts(
    output: Path,
    artifacts: Mapping[str, Mapping[str, Any]],
) -> ProviderResultV1:
    required = {
        "provider-attempts.json",
        "provider-envelope.bin",
        "provider-result.json",
        "table-response.json",
    }
    if not required <= set(artifacts):
        raise _error("sealed resolved observation omits provider result artifacts")
    provider = _json_artifact(
        output,
        artifacts["provider-result.json"],
        label="sealed provider result",
    )
    attempts = _json_artifact(
        output,
        artifacts["provider-attempts.json"],
        label="sealed provider attempts",
    )
    if (
        type(provider) is not dict
        or set(provider)
        != {
            "provider_model",
            "provider_name",
            "response_id_sha256",
            "service_tier",
            "usage",
        }
        or type(attempts) is not list
    ):
        raise _error("sealed provider result contract drifted")
    envelope_path = _authenticated_artifact_ref(
        output,
        artifacts["provider-envelope.bin"],
    )
    response_path = _authenticated_artifact_ref(
        output,
        artifacts["table-response.json"],
    )
    try:
        response_text = response_path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _error("sealed table response is not UTF-8") from exc
    return ProviderResultV1(
        output_text=response_text,
        raw_response_bytes=envelope_path.read_bytes(),
        provider_name=provider["provider_name"],
        provider_model=provider["provider_model"],
        service_tier=provider["service_tier"],
        attempts=tuple(attempts),
        usage=provider["usage"],
        response_id_sha256=provider["response_id_sha256"],
    )


def _validate_pre_db_apply_journal(output: Path, journal: Any) -> dict[str, Any]:
    if type(journal) is not dict or set(journal) != {
        "artifacts",
        "attempt_ordinal",
        "base_page_json_version_id",
        "format_version",
        "journal_sha256",
        "repair_job_id",
        "state",
        "thinking_level",
    }:
        raise _error("pre-database apply journal fields drifted")
    material = {key: journal[key] for key in journal if key != "journal_sha256"}
    if (
        journal["format_version"] != "GEMINI_JSON_ROLLFORWARD_TABLE_REPAIR_PRE_DB_APPLY_V1"
        or journal["state"] != "VALIDATED_PENDING_DATABASE_APPLY"
        or type(journal["artifacts"]) is not dict
        or journal["journal_sha256"] != canonical_json_sha256_v1(material)
    ):
        raise _error("pre-database apply journal identity drifted")
    for reference in journal["artifacts"].values():
        _authenticated_artifact_ref(output, reference)
    _provider_result_from_sealed_artifacts(output, journal["artifacts"])
    return json.loads(canonical_json_bytes_v1(journal))


def _validate_capture_checkpoint(output: Path, checkpoint: Any) -> dict[str, Any]:
    if type(checkpoint) is not dict or set(checkpoint) != {
        "attempt_artifact_manifests",
        "attempt_manifest_axis_sha256",
        "capture_checkpoint_sha256",
        "checkpoint_ordinal",
        "format_version",
        "job_states",
        "previous_checkpoint_ref",
        "run_contract_sha256",
    }:
        raise _error("capture checkpoint fields drifted")
    material = {key: checkpoint[key] for key in checkpoint if key != "capture_checkpoint_sha256"}
    if (
        checkpoint["format_version"] != CAPTURE_CHECKPOINT_FORMAT_VERSION
        or type(checkpoint["checkpoint_ordinal"]) is not int
        or checkpoint["checkpoint_ordinal"] <= 0
        or type(checkpoint["attempt_artifact_manifests"]) is not list
        or not checkpoint["attempt_artifact_manifests"]
        or checkpoint["attempt_manifest_axis_sha256"]
        != canonical_json_sha256_v1(checkpoint["attempt_artifact_manifests"])
        or checkpoint["capture_checkpoint_sha256"] != canonical_json_sha256_v1(material)
    ):
        raise _error("capture checkpoint identity drifted")
    for entry in checkpoint["attempt_artifact_manifests"]:
        manifest = _json_artifact(
            output,
            entry["attempt_artifact_manifest_ref"],
            label="checkpointed attempt artifact manifest",
        )
        checked = _validate_attempt_artifact_manifest(output, manifest)
        if (
            checked["attempt_id"] != entry["attempt_id"]
            or checked["manifest_sha256"] != entry["manifest_sha256"]
        ):
            raise _error("capture checkpoint manifest axis differs from content")
    previous = checkpoint["previous_checkpoint_ref"]
    if checkpoint["checkpoint_ordinal"] == 1:
        if previous is not None:
            raise _error("first capture checkpoint unexpectedly has a predecessor")
    else:
        if type(previous) is not dict:
            raise _error("capture checkpoint predecessor is absent")
        prior = _validate_capture_checkpoint(
            output,
            _json_artifact(
                output,
                previous,
                label="prior capture checkpoint",
            ),
        )
        if (
            prior["checkpoint_ordinal"] != checkpoint["checkpoint_ordinal"] - 1
            or prior["attempt_artifact_manifests"] != checkpoint["attempt_artifact_manifests"][:-1]
        ):
            raise _error("capture checkpoint predecessor chain drifted")
    return json.loads(canonical_json_bytes_v1(checkpoint))


def _write_capture_checkpoint(
    output: Path,
    *,
    attempt_artifact_manifests: Sequence[Mapping[str, Any]],
    attempts_by_job: Mapping[str, Sequence[Mapping[str, Any]]],
    previous_checkpoint_ref: Mapping[str, Any] | None,
    run_contract_sha256: str,
) -> dict[str, Any]:
    ordinal = len(attempt_artifact_manifests)
    job_states = [
        {
            "attempt_count": len(attempts),
            "next_status": attempts[-1]["next_status"] if attempts else "PENDING",
            "repair_job_id": job_id,
        }
        for job_id, attempts in attempts_by_job.items()
    ]
    material = {
        "attempt_artifact_manifests": json.loads(
            canonical_json_bytes_v1(list(attempt_artifact_manifests))
        ),
        "attempt_manifest_axis_sha256": canonical_json_sha256_v1(list(attempt_artifact_manifests)),
        "checkpoint_ordinal": ordinal,
        "format_version": CAPTURE_CHECKPOINT_FORMAT_VERSION,
        "job_states": job_states,
        "previous_checkpoint_ref": (
            None
            if previous_checkpoint_ref is None
            else json.loads(canonical_json_bytes_v1(dict(previous_checkpoint_ref)))
        ),
        "run_contract_sha256": run_contract_sha256,
    }
    checkpoint = {
        **material,
        "capture_checkpoint_sha256": canonical_json_sha256_v1(material),
    }
    checked = _validate_capture_checkpoint(output, checkpoint)
    payload = canonical_json_bytes_v1(checked) + b"\n"
    path = output / "capture-checkpoints" / f"checkpoint-{ordinal:03d}.json"
    _write_new(path, payload)
    return _ref(output, path, payload)


def _write_static_artifacts(
    output: Path,
    prepared: _PreparedRun,
    *,
    mode: str,
    source_store_sha256: str,
    source_store_size_bytes: int,
    source_results_database_sha256: str,
    source_results_database_size_bytes: int,
    effective_artifact_root: Path,
    contract_extensions: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, bytes], dict[str, bytes]]:
    input_refs = {}
    for name, pinned in prepared.pinned_inputs.items():
        path = output / "inputs" / name
        _write_new(path, pinned.raw)
        input_refs[name] = _ref(output, path, pinned.raw)
    authority_payload = canonical_json_bytes_v1(prepared.authority) + b"\n"
    authority_path = output / "authority" / "plan-replay-authority.json"
    _write_new(authority_path, authority_payload)
    repair_authority_payload = canonical_json_bytes_v1(prepared.repair_spec_authority) + b"\n"
    repair_authority_path = output / "authority" / "repair-spec-authority.json"
    _write_new(repair_authority_path, repair_authority_payload)
    plans_payload = canonical_json_bytes_v1(prepared.plans) + b"\n"
    plans_path = output / "authority" / "plan-axis.json"
    _write_new(plans_path, plans_payload)
    baseline_payload = canonical_json_bytes_v1(prepared.baseline_run_receipt) + b"\n"
    baseline_path = output / "authority" / "baseline-family-run-receipt.json"
    _write_new(baseline_path, baseline_payload)
    source_artifacts: dict[str, bytes] = {}
    crop_artifacts: dict[str, bytes] = {}
    job_refs = []
    for job in prepared.jobs:
        job_root = output / "jobs" / f"job-{job.ordinal:03d}"
        artifacts: dict[str, dict[str, Any]] = {}
        for name, payload in (
            ("plan.json", canonical_json_bytes_v1(job.plan) + b"\n"),
            ("source-image.png", job.source_image),
            (
                "source-resolution-receipt.json",
                canonical_json_bytes_v1(job.source_resolution_receipt) + b"\n",
            ),
            ("crop-image.png", job.crop_image),
            ("crop-receipt.json", canonical_json_bytes_v1(job.crop_receipt) + b"\n"),
            ("prompt.txt", job.prompt.encode("utf-8")),
            ("response-schema.json", canonical_json_bytes_v1(job.response_schema) + b"\n"),
        ):
            path = job_root / name
            _write_new(path, payload)
            artifacts[name] = _ref(output, path, payload)
        source_artifacts[sha256(job.source_image).hexdigest()] = job.source_image
        crop_artifacts[sha256(job.crop_image).hexdigest()] = job.crop_image
        job_refs.append(
            {
                "artifacts": artifacts,
                "document_ordinal": job.plan["document_ordinal"],
                "physical_page": job.plan["physical_page"],
                "repair_job_id": job.plan["repair_job_id"],
            }
        )
    contract = {
        "authority_artifacts": {
            "plan_axis": _ref(output, plans_path, plans_payload),
            "plan_replay": _ref(output, authority_path, authority_payload),
            "repair_spec": _ref(output, repair_authority_path, repair_authority_payload),
            "source_family_run": _ref(output, baseline_path, baseline_payload),
        },
        "expected_plan_count": prepared.config["expected_plan_count"],
        "expected_selected_page_count": prepared.config["expected_selected_page_count"],
        "effective_page_frontier_artifact_root": str(effective_artifact_root),
        "format_version": FORMAT_VERSION,
        "input_artifacts": input_refs,
        "jobs": job_refs,
        "mode": mode,
        "official_selection": "NOT_PERFORMED",
        "plan_axis_sha256": canonical_json_sha256_v1(prepared.plans),
        "projector_implementation_ref": prepared.projector_implementation_ref,
        "deterministic_projection_schema_sha256": canonical_json_sha256_v1(
            _deterministic_projection_schema_v1()
        ),
        "provider_failure_recovery": (
            {
                "database_apply_is_cross_store": True,
                "on_incomplete": (
                    "DISCARD_BOTH_WRITABLE_DATABASE_COPIES_AND_REPLAY_THE_SEALED_"
                    "ATTEMPT_AXIS_TO_FRESH_EXACT_COPIES_WITHOUT_PROVIDER_RECALL"
                ),
                "provider_recall_on_incomplete": "FORBIDDEN",
            }
            if mode != "SEALED_RESPONSE_REVALIDATION"
            else {
                "database_apply_is_cross_store": True,
                "on_incomplete": "DISCARD_BOTH_WORK_DATABASES_WITHOUT_PUBLISH",
                "provider_recall_on_incomplete": "NOT_APPLICABLE_PROVIDER_CALL_COUNT_ZERO",
            }
        ),
        "repair_spec_authority_manifest_sha256": prepared.repair_spec_authority["manifest_sha256"],
        "runner_implementation_ref": prepared.runner_implementation_ref,
        "source_family_results_database": {
            "sha256": source_results_database_sha256,
            "size_bytes": source_results_database_size_bytes,
        },
        "source_page_store": {
            "sha256": source_store_sha256,
            "size_bytes": source_store_size_bytes,
        },
    }
    if contract_extensions is not None:
        if type(contract_extensions) is not dict or set(contract) & set(contract_extensions):
            raise _error("run-contract extensions collide with the base contract")
        contract = {**contract, **json.loads(canonical_json_bytes_v1(contract_extensions))}
    _write_json(output / "run-contract.json", contract)
    return contract, source_artifacts, crop_artifacts


def _request_material(job: _PreparedJob, thinking_level: str) -> dict[str, Any]:
    return {
        "allow_fallbacks": False,
        "crop_image_sha256": job.crop_receipt["crop_image_sha256"],
        "execution_policy": "OPENROUTER_PILOT",
        "output_contract_mode": "JSON_SCHEMA",
        "prompt_sha256": job.plan["request_contract"]["prompt_sha256"],
        "repair_job_id": job.plan["repair_job_id"],
        "requested_model": OPENROUTER_MODEL,
        "requested_provider": OPENROUTER_PROVIDER,
        "response_schema_sha256": job.plan["request_contract"]["response_schema_sha256"],
        "service_tier": OPENROUTER_SERVICE_TIER,
        "thinking_level": thinking_level,
    }


def _call_provider(
    job: _PreparedJob,
    *,
    thinking_level: str,
    api_key: str,
    timeout_seconds: int,
    provider_call: Callable[..., ProviderResultV1],
) -> _ProviderObservation:
    started = time.perf_counter()
    try:
        result = provider_call(
            google_api_keys=None,
            openrouter_api_key=api_key,
            image=job.crop_image,
            media_type="image/png",
            prompt=job.prompt,
            response_schema=job.response_schema,
            output_contract_mode="JSON_SCHEMA",
            execution_policy="OPENROUTER_PILOT",
            timeout_seconds=timeout_seconds,
            openrouter_retries=1,
            thinking_level=thinking_level,
        )
    except GeminiJsonFirstProviderV1Error as exc:
        return _ProviderObservation(
            result=None,
            error=exc,
            elapsed_seconds=format(time.perf_counter() - started, ".6f"),
        )
    except Exception as exc:  # noqa: BLE001 - convert a billed opaque provider failure to ledger
        failure = GeminiJsonFirstProviderV1Error(
            "provider call raised one undeclared exception; details are intentionally redacted"
        )
        failure.__cause__ = exc
        return _ProviderObservation(
            result=None,
            error=failure,
            elapsed_seconds=format(time.perf_counter() - started, ".6f"),
        )
    if not isinstance(result, ProviderResultV1):
        return _ProviderObservation(
            result=None,
            error=GeminiJsonFirstProviderV1Error("provider returned an undeclared result type"),
            elapsed_seconds=format(time.perf_counter() - started, ".6f"),
        )
    return _ProviderObservation(
        result=result,
        error=None,
        elapsed_seconds=format(time.perf_counter() - started, ".6f"),
    )


def _repair_usage(result: ProviderResultV1 | None) -> dict[str, Any]:
    if result is None:
        return {
            "actual_cost_usd": "0",
            "cached_input_tokens": 0,
            "cost_disposition": "UNBILLED_PROVIDER_FAILURE",
            "input_tokens": 0,
            "output_tokens": 0,
            "thought_tokens": 0,
            "total_tokens": 0,
        }
    usage = result.usage
    required = {
        "actual_cost_usd",
        "billing_disposition",
        "cached_input_tokens",
        "input_tokens",
        "output_tokens",
        "thought_tokens",
        "total_tokens",
    }
    if type(usage) is not dict or not required <= set(usage):
        raise _error("OpenRouter result has no complete usage accounting")
    return {
        "actual_cost_usd": usage["actual_cost_usd"],
        "cached_input_tokens": usage["cached_input_tokens"],
        "cost_disposition": usage["billing_disposition"],
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "thought_tokens": usage["thought_tokens"],
        "total_tokens": usage["total_tokens"],
    }


def _provider_identity(
    result: ProviderResultV1 | None,
    *,
    request_id_sha256: str,
) -> dict[str, Any]:
    return {
        "provider_model": result.provider_model if result is not None else OPENROUTER_MODEL,
        "provider_name": "openrouter",
        "request_id_sha256": request_id_sha256,
        "response_id_sha256": result.response_id_sha256 if result is not None else None,
        "service_tier": result.service_tier if result is not None else OPENROUTER_SERVICE_TIER,
    }


def _response_ref(output: Path, path: Path, payload: bytes) -> dict[str, Any]:
    reference = _ref(output, path, payload)
    if reference["size_bytes"] <= 0:
        raise _error("provider response artifact is empty")
    return reference


def _mirror_family_attempt(
    writable_results_database: Path,
    attempt: Mapping[str, Any],
    *,
    page_json_version_id_override: str | None = None,
) -> dict[str, Any]:
    mirrored = record_gemini_family_region_repair_attempt_v1(
        writable_results_database,
        repair_job_id=attempt["repair_job_id"],
        thinking_level=attempt["thinking_level"],
        outcome=attempt["outcome"],
        page_json_version_id=(
            attempt["observed_page_json_version_id"]
            if page_json_version_id_override is None
            else page_json_version_id_override
        ),
        usage=attempt["usage"],
        reasons=attempt["validation"]["reason_codes"],
    )
    if (
        mirrored["repair_job_id"] != attempt["repair_job_id"]
        or mirrored["thinking_level"] != attempt["thinking_level"]
        or mirrored["outcome"] != attempt["outcome"]
        or mirrored["attempt_ordinal"] != attempt["attempt_ordinal"]
        or mirrored["next_status"] != attempt["next_status"]
    ):
        raise _error("standard family-results attempt differs from the audited custom ledger")
    return dict(attempt)


def _finalize_attempt(
    *,
    output: Path,
    attempt_root: Path,
    writable_results_database: Path,
    attempt: Mapping[str, Any],
    attempt_artifact_manifests: list[dict[str, Any]],
    mirror_family_results: bool,
) -> dict[str, Any]:
    manifest, manifest_ref = _seal_attempt_artifacts(output, attempt_root, attempt)
    attempt_artifact_manifests.append(
        {
            "attempt_artifact_manifest_ref": manifest_ref,
            "attempt_id": manifest["attempt_id"],
            "attempt_ordinal": attempt["attempt_ordinal"],
            "manifest_sha256": manifest["manifest_sha256"],
            "repair_job_id": manifest["repair_job_id"],
            "thinking_level": attempt["thinking_level"],
        }
    )
    return (
        _mirror_family_attempt(writable_results_database, attempt)
        if mirror_family_results
        else dict(attempt)
    )


def _repair_candidate_input_status(prepared: _PreparedRun, job: _PreparedJob) -> str:
    matches = []
    for trial in prepared.family_sweep["trials"]:
        for candidate in trial.get("candidates", []):
            if candidate.get("candidate_id") == job.plan["candidate_id"]:
                matches.append((trial, candidate))
    if len(matches) != 1:
        raise _error("repair job does not bind one source candidate")
    trial, candidate = matches[0]
    status = candidate.get("status")
    if (
        status not in {READY, UNRESOLVED}
        or trial.get("status") != status
        or trial.get("document_ordinal") != job.plan["document_ordinal"]
        or candidate.get("family_id") != job.plan["family_id"]
        or canonical_json_sha256_v1(candidate) != job.plan["candidate_semantic_replay_sha256"]
    ):
        raise _error("repair source candidate status/semantic replay drifted")
    return status


def _validated_prior_page_hashes(
    page_store_path: Path, prior_attempts: Sequence[Mapping[str, Any]]
) -> list[str]:
    version_ids = [
        attempt["observed_page_json_version_id"]
        for attempt in prior_attempts
        if attempt["outcome"] == "VALIDATED_OBSERVATION_PENDING_CONSENSUS"
    ]
    if not version_ids:
        return []
    evidence = load_rollforward_table_page_evidence_v1(
        page_store_path, page_json_version_ids=version_ids
    )
    return [canonical_json_sha256_v1(item["page_json"]) for item in evidence]


def _persist_observation(
    *,
    output: Path,
    prepared: _PreparedRun,
    job: _PreparedJob,
    thinking_level: str,
    observation: _ProviderObservation,
    writable_page_store: Path,
    writable_results_database: Path,
    prior_attempts: Sequence[Mapping[str, Any]],
    response_artifacts: dict[str, bytes],
    attempt_artifact_manifests: list[dict[str, Any]],
    mirror_family_results: bool = True,
    sealed_source_link: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    attempt_ordinal = len(prior_attempts) + 1
    attempt_root = (
        output
        / "jobs"
        / f"job-{job.ordinal:03d}"
        / f"attempt-{attempt_ordinal:02d}-{thinking_level}"
    )
    request = _request_material(job, thinking_level)
    request_id = canonical_json_sha256_v1(request)
    _write_json(attempt_root / "request.json", {**request, "request_id_sha256": request_id})
    result = observation.result
    usage = _repair_usage(result)
    provider = _provider_identity(result, request_id_sha256=request_id)
    _write_json(attempt_root / "usage.json", usage)
    _write_json(attempt_root / "provider.json", provider)
    _write_json(
        attempt_root / "observation.json",
        {"elapsed_seconds": observation.elapsed_seconds},
    )
    if sealed_source_link is not None:
        link = dict(sealed_source_link)
        material = {key: link[key] for key in link if key != "link_sha256"}
        if (
            type(sealed_source_link) is not dict
            or link.get("format_version") != SEALED_OBSERVATION_SOURCE_LINK_FORMAT_VERSION
            or link.get("link_sha256") != canonical_json_sha256_v1(material)
        ):
            raise _error("sealed observation source link identity drifted")
        _write_json(attempt_root / "sealed-source-link.json", link)
    raw_response: bytes | None = None
    response_artifact_ref = None
    if result is None:
        error = observation.error
        assert error is not None
        _write_json(
            attempt_root / "provider-attempts.json",
            list(getattr(error, "attempts", ())),
        )
        failure_raw = getattr(error, "raw_response_bytes", None)
        if type(failure_raw) is bytes and failure_raw:
            envelope_path = attempt_root / "provider-envelope.bin"
            _write_new(envelope_path, failure_raw)
            raw_response = failure_raw
            response_artifact_ref = _response_ref(output, envelope_path, failure_raw)
            response_artifacts[sha256(failure_raw).hexdigest()] = failure_raw
        validation_details = {
            "error_message": str(error),
            "error_type": type(error).__name__,
            "reason_codes": ["PROVIDER_FAILURE"],
            "status": "FAIL",
        }
        _write_json(attempt_root / "validation.json", validation_details)
        attempt = build_rollforward_table_repair_attempt_v1(
            plan=job.plan,
            authority=prepared.authority,
            repair_spec_authority=prepared.repair_spec_authority,
            page_store_path=writable_page_store,
            prior_attempts=prior_attempts,
            thinking_level=thinking_level,
            outcome="PROVIDER_OR_VALIDATION_FAILURE",
            observed_page_json_version_id=None,
            repair_receipt=None,
            crop_receipt=job.crop_receipt,
            source_image_bytes=job.source_image,
            crop_image_bytes=job.crop_image,
            response_artifact_ref=response_artifact_ref,
            raw_response_bytes=raw_response,
            validation={"reason_codes": ["PROVIDER_FAILURE"], "status": "FAIL"},
            usage=usage,
            provider=provider,
            elapsed_seconds=observation.elapsed_seconds,
            _prevalidated_plan_axis=prepared.plans,
        )
        _write_json(attempt_root / "attempt.json", attempt)
        return _finalize_attempt(
            output=output,
            attempt_root=attempt_root,
            writable_results_database=writable_results_database,
            attempt=attempt,
            attempt_artifact_manifests=attempt_artifact_manifests,
            mirror_family_results=mirror_family_results,
        )
    if type(result.raw_response_bytes) is not bytes or not result.raw_response_bytes:
        raise _error("OpenRouter result has no immutable provider envelope")
    if type(result.output_text) is not str or not result.output_text:
        raise _error("OpenRouter result has no table response text")
    envelope_path = attempt_root / "provider-envelope.bin"
    _write_new(envelope_path, result.raw_response_bytes)
    response_bytes = result.output_text.encode("utf-8")
    response_path = attempt_root / "table-response.json"
    _write_new(response_path, response_bytes)
    response_artifact_ref = _response_ref(output, response_path, response_bytes)
    response_artifacts[sha256(response_bytes).hexdigest()] = response_bytes
    _write_json(attempt_root / "provider-attempts.json", list(result.attempts))
    _write_json(
        attempt_root / "provider-result.json",
        {
            "provider_model": result.provider_model,
            "provider_name": result.provider_name,
            "response_id_sha256": result.response_id_sha256,
            "service_tier": result.service_tier,
            "usage": result.usage,
        },
    )
    try:
        decoded = decode_rollforward_table_repair_text_v1(result.output_text, target=job.target)
    except GeminiJsonRollforwardTableRepairV1Error as exc:
        validation_details = {
            "error_message": str(exc),
            "error_type": type(exc).__name__,
            "reason_codes": ["TABLE_REPAIR_VALIDATION_FAILED"],
            "status": "FAIL",
        }
        _write_json(attempt_root / "validation.json", validation_details)
        attempt = build_rollforward_table_repair_attempt_v1(
            plan=job.plan,
            authority=prepared.authority,
            repair_spec_authority=prepared.repair_spec_authority,
            page_store_path=writable_page_store,
            prior_attempts=prior_attempts,
            thinking_level=thinking_level,
            outcome="RETRYABLE_VALIDATION_FAILURE",
            observed_page_json_version_id=None,
            repair_receipt=None,
            crop_receipt=job.crop_receipt,
            source_image_bytes=job.source_image,
            crop_image_bytes=job.crop_image,
            response_artifact_ref=response_artifact_ref,
            raw_response_bytes=response_bytes,
            validation={
                "reason_codes": ["TABLE_REPAIR_VALIDATION_FAILED"],
                "status": "FAIL",
            },
            usage=usage,
            provider=provider,
            elapsed_seconds=observation.elapsed_seconds,
            _prevalidated_plan_axis=prepared.plans,
        )
        _write_json(attempt_root / "attempt.json", attempt)
        return _finalize_attempt(
            output=output,
            attempt_root=attempt_root,
            writable_results_database=writable_results_database,
            attempt=attempt,
            attempt_artifact_manifests=attempt_artifact_manifests,
            mirror_family_results=mirror_family_results,
        )
    candidate_status = _repair_candidate_input_status(prepared, job)
    prior_hashes = _validated_prior_page_hashes(writable_page_store, prior_attempts)
    try:
        merged, receipt = merge_rollforward_table_repair_v1(
            job.base_page_json,
            plan=job.plan,
            repair=decoded,
            page_store_path=writable_page_store,
            authority=prepared.authority,
            repair_spec_authority=prepared.repair_spec_authority,
            _prevalidated_plan_axis=prepared.plans,
        )
    except GeminiJsonRollforwardTableRepairV1Error as repair_exc:
        corroboration = None
        if candidate_status == READY:
            try:
                corroboration = validate_rollforward_table_source_corroboration_v1(
                    job.base_page_json,
                    plan=job.plan,
                    repair=decoded,
                    page_store_path=writable_page_store,
                    authority=prepared.authority,
                    repair_spec_authority=prepared.repair_spec_authority,
                    _prevalidated_plan_axis=prepared.plans,
                )
            except GeminiJsonRollforwardTableRepairV1Error:
                corroboration = None
        if corroboration is None:
            validation_details = {
                "error_message": str(repair_exc),
                "error_type": type(repair_exc).__name__,
                "reason_codes": ["TABLE_REPAIR_VALIDATION_FAILED"],
                "status": "FAIL",
            }
            _write_json(attempt_root / "validation.json", validation_details)
            attempt = build_rollforward_table_repair_attempt_v1(
                plan=job.plan,
                authority=prepared.authority,
                repair_spec_authority=prepared.repair_spec_authority,
                page_store_path=writable_page_store,
                prior_attempts=prior_attempts,
                thinking_level=thinking_level,
                outcome="RETRYABLE_VALIDATION_FAILURE",
                observed_page_json_version_id=None,
                repair_receipt=None,
                crop_receipt=job.crop_receipt,
                source_image_bytes=job.source_image,
                crop_image_bytes=job.crop_image,
                response_artifact_ref=response_artifact_ref,
                raw_response_bytes=response_bytes,
                validation={
                    "reason_codes": ["TABLE_REPAIR_VALIDATION_FAILED"],
                    "status": "FAIL",
                },
                usage=usage,
                provider=provider,
                elapsed_seconds=observation.elapsed_seconds,
                _prevalidated_plan_axis=prepared.plans,
            )
            _write_json(attempt_root / "attempt.json", attempt)
            return _finalize_attempt(
                output=output,
                attempt_root=attempt_root,
                writable_results_database=writable_results_database,
                attempt=attempt,
                attempt_artifact_manifests=attempt_artifact_manifests,
                mirror_family_results=mirror_family_results,
            )
        base_sha = canonical_json_sha256_v1(job.base_page_json)
        outcome = (
            "SOURCE_CORROBORATED_NO_CHANGE"
            if not prior_hashes or base_sha in prior_hashes
            else "VALIDATED_OBSERVATION_PENDING_CONSENSUS"
        )
        _write_json(attempt_root / "source-corroboration-receipt.json", corroboration)
        _write_json(
            attempt_root / "validation.json",
            {"reason_codes": [], "status": "PASS"},
        )
        attempt = build_rollforward_table_repair_attempt_v1(
            plan=job.plan,
            authority=prepared.authority,
            repair_spec_authority=prepared.repair_spec_authority,
            page_store_path=writable_page_store,
            prior_attempts=prior_attempts,
            thinking_level=thinking_level,
            outcome=outcome,
            observed_page_json_version_id=job.plan["base_page_json_version_id"],
            repair_receipt=corroboration,
            crop_receipt=job.crop_receipt,
            source_image_bytes=job.source_image,
            crop_image_bytes=job.crop_image,
            response_artifact_ref=response_artifact_ref,
            raw_response_bytes=response_bytes,
            validation={"reason_codes": [], "status": "PASS"},
            usage=usage,
            provider=provider,
            elapsed_seconds=observation.elapsed_seconds,
            _prevalidated_plan_axis=prepared.plans,
        )
        _write_json(attempt_root / "attempt.json", attempt)
        return _finalize_attempt(
            output=output,
            attempt_root=attempt_root,
            writable_results_database=writable_results_database,
            attempt=attempt,
            attempt_artifact_manifests=attempt_artifact_manifests,
            mirror_family_results=mirror_family_results,
        )
    merged_sha = canonical_json_sha256_v1(merged)
    outcome = (
        "RESOLVED"
        if candidate_status == UNRESOLVED or merged_sha in prior_hashes
        else "VALIDATED_OBSERVATION_PENDING_CONSENSUS"
    )
    merged_payload = canonical_json_bytes_v1(merged) + b"\n"
    merged_path = attempt_root / "merged-page.json"
    _write_new(merged_path, merged_payload)
    receipt_payload = canonical_json_bytes_v1(receipt) + b"\n"
    receipt_path = attempt_root / "repair-receipt.json"
    _write_new(receipt_path, receipt_payload)
    validation_payload = canonical_json_bytes_v1({"reason_codes": [], "status": "PASS"}) + b"\n"
    validation_path = attempt_root / "validation.json"
    _write_new(validation_path, validation_payload)
    pre_db_artifacts = {}
    pre_db_paths = [
        attempt_root / "provider-attempts.json",
        attempt_root / "provider-envelope.bin",
        attempt_root / "provider-result.json",
        attempt_root / "provider.json",
        attempt_root / "observation.json",
        attempt_root / "request.json",
        attempt_root / "table-response.json",
        attempt_root / "usage.json",
        validation_path,
        merged_path,
        receipt_path,
    ]
    sealed_link_path = attempt_root / "sealed-source-link.json"
    if sealed_link_path.is_file():
        pre_db_paths.append(sealed_link_path)
    for path in pre_db_paths:
        payload = path.read_bytes()
        pre_db_artifacts[path.name] = _ref(output, path, payload)
    pre_db_material = {
        "artifacts": pre_db_artifacts,
        "attempt_ordinal": attempt_ordinal,
        "base_page_json_version_id": job.plan["base_page_json_version_id"],
        "format_version": "GEMINI_JSON_ROLLFORWARD_TABLE_REPAIR_PRE_DB_APPLY_V1",
        "repair_job_id": job.plan["repair_job_id"],
        "state": "VALIDATED_PENDING_DATABASE_APPLY",
        "thinking_level": thinking_level,
    }
    _write_json(
        attempt_root / "pre-db-apply.json",
        {**pre_db_material, "journal_sha256": canonical_json_sha256_v1(pre_db_material)},
    )
    binding = job.plan["source_binding"]
    identities = ingest_financial_page_extraction_v1(
        writable_page_store,
        document={
            "source_logical_name": binding["source_logical_name"],
            "source_sha256": binding["source_sha256"],
            "source_size_bytes": binding["source_size_bytes"],
        },
        page={
            "physical_page": binding["physical_page"],
            "image_sha256": binding["image_sha256"],
            "image_size_bytes": binding["image_size_bytes"],
            "pixel_width": binding["pixel_width"],
            "pixel_height": binding["pixel_height"],
            "render_dpi": binding["render_dpi"],
            "media_type": binding["media_type"],
        },
        prompt_variant="rollforward-table-cells",
        output_contract_mode="JSON_SCHEMA",
        prompt_sha256=job.plan["request_contract"]["prompt_sha256"],
        response_schema_sha256=job.plan["request_contract"]["response_schema_sha256"],
        requested_model=OPENROUTER_MODEL,
        requested_service_tier=OPENROUTER_SERVICE_TIER,
        thinking_level=thinking_level,
        provider_result=result,
        page_json=merged,
    )
    lineage = record_page_json_region_repair_v1(
        writable_page_store,
        merged_page_json_version_id=identities["page_json_version_id"],
        receipt=receipt,
    )
    _write_json(attempt_root / "ingest-identities.json", identities)
    _write_json(attempt_root / "region-lineage.json", lineage)
    attempt = build_rollforward_table_repair_attempt_v1(
        plan=job.plan,
        authority=prepared.authority,
        repair_spec_authority=prepared.repair_spec_authority,
        page_store_path=writable_page_store,
        prior_attempts=prior_attempts,
        thinking_level=thinking_level,
        outcome=outcome,
        observed_page_json_version_id=lineage["observed_page_json_version_id"],
        repair_receipt=receipt,
        crop_receipt=job.crop_receipt,
        source_image_bytes=job.source_image,
        crop_image_bytes=job.crop_image,
        response_artifact_ref=response_artifact_ref,
        raw_response_bytes=response_bytes,
        validation={"reason_codes": [], "status": "PASS"},
        usage=usage,
        provider=provider,
        elapsed_seconds=observation.elapsed_seconds,
        _prevalidated_plan_axis=prepared.plans,
    )
    _write_json(attempt_root / "attempt.json", attempt)
    return _finalize_attempt(
        output=output,
        attempt_root=attempt_root,
        writable_results_database=writable_results_database,
        attempt=attempt,
        attempt_artifact_manifests=attempt_artifact_manifests,
        mirror_family_results=mirror_family_results,
    )


def _apply_sealed_resolved_observation(
    *,
    sealed_output: Path,
    artifacts: Mapping[str, Mapping[str, Any]],
    prepared: _PreparedRun,
    job: _PreparedJob,
    writable_page_store: Path,
) -> tuple[ProviderResultV1, dict[str, Any], dict[str, Any], bytes]:
    required = {"merged-page.json", "repair-receipt.json", "table-response.json"}
    if not required <= set(artifacts):
        raise _error("sealed resolved observation omits validated merge artifacts")
    result = _provider_result_from_sealed_artifacts(sealed_output, artifacts)
    merged = _json_artifact(
        sealed_output,
        artifacts["merged-page.json"],
        label="sealed merged page",
    )
    receipt = _json_artifact(
        sealed_output,
        artifacts["repair-receipt.json"],
        label="sealed repair receipt",
    )
    decoded = decode_rollforward_table_repair_text_v1(result.output_text, target=job.target)
    rebuilt_merged, rebuilt_receipt = merge_rollforward_table_repair_v1(
        job.base_page_json,
        plan=job.plan,
        repair=decoded,
        page_store_path=writable_page_store,
        authority=prepared.authority,
        repair_spec_authority=prepared.repair_spec_authority,
        _prevalidated_plan_axis=prepared.plans,
    )
    if not same_typed_json_v1(merged, rebuilt_merged) or not same_typed_json_v1(
        receipt, rebuilt_receipt
    ):
        raise _error("sealed validated merge does not replay against the fresh page store")
    binding = job.plan["source_binding"]
    identities = ingest_financial_page_extraction_v1(
        writable_page_store,
        document={
            "source_logical_name": binding["source_logical_name"],
            "source_sha256": binding["source_sha256"],
            "source_size_bytes": binding["source_size_bytes"],
        },
        page={
            "physical_page": binding["physical_page"],
            "image_sha256": binding["image_sha256"],
            "image_size_bytes": binding["image_size_bytes"],
            "pixel_width": binding["pixel_width"],
            "pixel_height": binding["pixel_height"],
            "render_dpi": binding["render_dpi"],
            "media_type": binding["media_type"],
        },
        prompt_variant="rollforward-table-cells",
        output_contract_mode="JSON_SCHEMA",
        prompt_sha256=job.plan["request_contract"]["prompt_sha256"],
        response_schema_sha256=job.plan["request_contract"]["response_schema_sha256"],
        requested_model=OPENROUTER_MODEL,
        requested_service_tier=OPENROUTER_SERVICE_TIER,
        thinking_level=_json_artifact(
            sealed_output,
            artifacts["request.json"],
            label="sealed provider request",
        )["thinking_level"],
        provider_result=result,
        page_json=merged,
    )
    lineage = record_page_json_region_repair_v1(
        writable_page_store,
        merged_page_json_version_id=identities["page_json_version_id"],
        receipt=receipt,
    )
    captured_database_artifacts = {
        "ingest-identities.json",
        "region-lineage.json",
    }
    present_database_artifacts = captured_database_artifacts & set(artifacts)
    if present_database_artifacts and present_database_artifacts != captured_database_artifacts:
        raise _error("captured database apply artifacts are partial")
    if present_database_artifacts:
        captured_identities = _json_artifact(
            sealed_output,
            artifacts["ingest-identities.json"],
            label="captured ingest identities",
        )
        captured_lineage = _json_artifact(
            sealed_output,
            artifacts["region-lineage.json"],
            label="captured region lineage",
        )
        if not same_typed_json_v1(identities, captured_identities) or not same_typed_json_v1(
            lineage, captured_lineage
        ):
            raise _error("captured ingest identities or region lineage do not exact-replay")
    response_bytes = _authenticated_artifact_ref(
        sealed_output,
        artifacts["table-response.json"],
    ).read_bytes()
    return result, receipt, lineage, response_bytes


def _replay_sealed_source_corroboration(
    *,
    sealed_output: Path,
    artifacts: Mapping[str, Mapping[str, Any]],
    prepared: _PreparedRun,
    job: _PreparedJob,
    writable_page_store: Path,
) -> tuple[dict[str, Any], bytes]:
    required = {"source-corroboration-receipt.json", "table-response.json"}
    if not required <= set(artifacts):
        raise _error("sealed source corroboration omits its receipt or response")
    result = _provider_result_from_sealed_artifacts(sealed_output, artifacts)
    receipt = _json_artifact(
        sealed_output,
        artifacts["source-corroboration-receipt.json"],
        label="sealed source corroboration receipt",
    )
    decoded = decode_rollforward_table_repair_text_v1(result.output_text, target=job.target)
    rebuilt = validate_rollforward_table_source_corroboration_v1(
        job.base_page_json,
        plan=job.plan,
        repair=decoded,
        page_store_path=writable_page_store,
        authority=prepared.authority,
        repair_spec_authority=prepared.repair_spec_authority,
        _prevalidated_plan_axis=prepared.plans,
    )
    if not same_typed_json_v1(receipt, rebuilt):
        raise _error("sealed source corroboration does not replay against the fresh page store")
    response_bytes = _authenticated_artifact_ref(
        sealed_output, artifacts["table-response.json"]
    ).read_bytes()
    return receipt, response_bytes


def _validate_writable_copy(
    source: Path,
    writable: Path,
    source_sha256: str,
    *,
    label: str,
) -> Path:
    resolved = _regular_file(writable, label=label)
    _reject_sqlite_sidecars(resolved, label=label)
    try:
        if os.path.samefile(source, resolved):
            raise _error(f"{label} is the frozen source file or one hard link to it")
    except OSError as exc:
        raise _error("page-store file identity cannot be compared") from exc
    actual, _size = _sha_file(resolved)
    if actual != source_sha256:
        raise _error(f"{label} is not an exact byte copy of the frozen source")
    if not os.access(resolved, os.W_OK):
        raise _error(f"{label} is not writable")
    return resolved


def _validate_artifact_root(path: Path) -> Path:
    candidate = Path(path)
    resolved = candidate.resolve()
    if candidate.is_symlink() or not resolved.is_dir():
        raise _error("effective-frontier artifact root must be one non-symlink directory")
    return resolved


def _assert_frozen_database_unchanged(
    path: Path,
    expected: tuple[str, int],
    *,
    label: str,
) -> None:
    _reject_sqlite_sidecars(path, label=label)
    if _sha_file(path) != expected:
        raise _error(f"{label} changed during repair execution")


def _bind_effective_frontier_database_ref(
    artifact_root: Path,
    reference_path: str,
    writable_database: Path,
    *,
    label: str,
    expected_identity: tuple[int, int] | None = None,
) -> None:
    relative = PurePosixPath(reference_path)
    candidate = artifact_root.joinpath(*relative.parts)
    cursor = artifact_root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise _error(f"{label} reference crosses a symlink")
    resolved = candidate.resolve()
    if not resolved.is_relative_to(artifact_root) or not resolved.is_file():
        raise _error(f"{label} reference is absent from the pinned artifact root")
    try:
        if expected_identity is None:
            matches = os.path.samefile(resolved, writable_database)
        else:
            reference_stat = os.stat(resolved, follow_symlinks=False)
            matches = (
                stat.S_ISREG(reference_stat.st_mode)
                and (reference_stat.st_dev, reference_stat.st_ino) == expected_identity
            )
        if not matches:
            raise _error(f"{label} reference does not identify the writable database")
    except OSError as exc:
        raise _error(f"{label} reference identity cannot be compared") from exc


def _bind_published_database_refs(
    *,
    artifact_root: Path,
    repair_spec_config_path: Path,
    repair_spec_config_sha256: str,
    writable_store_boundary: _SqliteBoundary,
    writable_results_boundary: _SqliteBoundary,
    label_prefix: str,
) -> None:
    config = _validate_config(
        _read_pinned_json(
            repair_spec_config_path,
            repair_spec_config_sha256,
            label="external repair-spec config",
        ).value
    )
    effective_artifact_root = _validate_artifact_root(artifact_root)
    _bind_effective_frontier_database_ref(
        effective_artifact_root,
        config["writable_page_store_ref_path"],
        writable_store_boundary.original_path,
        label=f"{label_prefix} page database",
        expected_identity=writable_store_boundary.identity,
    )
    _bind_effective_frontier_database_ref(
        effective_artifact_root,
        config["writable_results_database_ref_path"],
        writable_results_boundary.original_path,
        label=f"{label_prefix} results database",
        expected_identity=writable_results_boundary.identity,
    )


def _run_rollforward_table_repair_on_private_sqlite_v1(
    *,
    family_sweep_path: Path,
    family_sweep_sha256: str,
    selected_page_ids_path: Path,
    selected_page_ids_sha256: str,
    source_page_store: Path,
    source_page_store_sha256: str,
    source_results_database: Path,
    source_results_database_sha256: str,
    repair_spec_config_path: Path,
    repair_spec_config_sha256: str,
    workspace_root: Path,
    runner_implementation_sha256: str,
    artifact_root: Path,
    artifact_dir: Path,
    dry_run: bool,
    writable_page_store: Path | None = None,
    writable_results_database: Path | None = None,
    writable_page_store_ref_identity: tuple[int, int] | None = None,
    writable_results_database_ref_identity: tuple[int, int] | None = None,
    openrouter_api_key: str | None = None,
    workers: int = 6,
    timeout_seconds: int = 900,
    provider_call: Callable[..., ProviderResultV1] = call_gemini_json_first_v1,
    sealed_observation_artifact_dir: Path | None = None,
    sealed_observation_run_result_sha256: str | None = None,
    sealed_observation_git_commit: str | None = None,
) -> dict[str, Any]:
    """Execute one fresh dry-run or bounded OpenRouter repair frontier."""

    if type(dry_run) is not bool or type(workers) is not int or not 1 <= workers <= 6:
        raise _error("repair mode or worker bound is invalid")
    if type(timeout_seconds) is not int or timeout_seconds < 60:
        raise _error("provider timeout must be at least 60 seconds")
    if dry_run:
        if any(
            value is not None
            for value in (
                writable_page_store,
                writable_results_database,
                openrouter_api_key,
                sealed_observation_artifact_dir,
                sealed_observation_run_result_sha256,
                sealed_observation_git_commit,
            )
        ):
            raise _error("dry-run must not receive provider or writable-store authority")
    elif (
        writable_page_store is None
        or writable_results_database is None
        or type(openrouter_api_key) is not str
        or len(openrouter_api_key) < 20
    ):
        raise _error("OpenRouter mode requires two writable database copies and a credential")
    adoption_values = (
        sealed_observation_artifact_dir,
        sealed_observation_run_result_sha256,
    )
    if any(value is not None for value in adoption_values) and not all(
        value is not None for value in adoption_values
    ):
        raise _error("sealed observation adoption requires its artifact root and run-result pin")
    source_store, source_sha, source_size = _validate_source_store(
        source_page_store,
        source_page_store_sha256,
    )
    source_results, source_results_sha, source_results_size = _validate_pinned_binary(
        source_results_database,
        source_results_database_sha256,
        label="frozen source family-results database",
    )
    effective_artifact_root = _validate_artifact_root(artifact_root)
    writable_store = None
    writable_results = None
    if not dry_run:
        assert writable_page_store is not None and writable_results_database is not None
        writable_store = _validate_writable_copy(
            source_store,
            writable_page_store,
            source_sha,
            label="writable page-store copy",
        )
        writable_results = _validate_writable_copy(
            source_results,
            writable_results_database,
            source_results_sha,
            label="writable family-results database copy",
        )
    sweep = _read_pinned_json(
        family_sweep_path,
        family_sweep_sha256,
        label="base family sweep",
    )
    selected = _read_pinned_json(
        selected_page_ids_path,
        selected_page_ids_sha256,
        label="selected page JSON version IDs",
    )
    repair_config = _read_pinned_json(
        repair_spec_config_path,
        repair_spec_config_sha256,
        label="external repair-spec config",
    )
    prepared = _prepare(
        sweep=sweep,
        selected=selected,
        repair_config=repair_config,
        source_page_store=source_store,
        source_results_database=source_results,
        workspace_root=workspace_root,
        runner_implementation_sha256=runner_implementation_sha256,
    )
    sealed_adoption = None
    if sealed_observation_artifact_dir is not None:
        assert sealed_observation_run_result_sha256 is not None
        sealed_adoption = _validate_sealed_observation_adoption_source_v1(
            sealed_artifact_dir=sealed_observation_artifact_dir,
            sealed_run_result_sha256=sealed_observation_run_result_sha256,
            sealed_git_commit=sealed_observation_git_commit,
            prepared=prepared,
            workspace_root=workspace_root,
            source_sha=source_sha,
            source_size=source_size,
            source_results_sha=source_results_sha,
            source_results_size=source_results_size,
        )
    if writable_store is not None and writable_results is not None:
        _bind_effective_frontier_database_ref(
            effective_artifact_root,
            prepared.config["writable_page_store_ref_path"],
            writable_store,
            label="effective-frontier page database",
            expected_identity=writable_page_store_ref_identity,
        )
        _bind_effective_frontier_database_ref(
            effective_artifact_root,
            prepared.config["writable_results_database_ref_path"],
            writable_results,
            label="effective-frontier results database",
            expected_identity=writable_results_database_ref_identity,
        )
    _assert_frozen_database_unchanged(
        source_store,
        (source_sha, source_size),
        label="frozen source page store",
    )
    _assert_frozen_database_unchanged(
        source_results,
        (source_results_sha, source_results_size),
        label="frozen source family-results database",
    )
    if writable_store is not None:
        rebuilt = build_accounting_table_cell_repair_plans_v1(
            compiled_specs=prepared.compiled_specs,
            family_sweep=prepared.family_sweep,
            page_store_path=writable_store,
            selected_page_json_version_ids=prepared.selected_ids,
            table_repair_specs=prepared.config["table_repair_specs"],
        )
        if not same_typed_json_v1(rebuilt, prepared.plans):
            raise _error("writable page-store copy does not replay the frozen plan axis")
    output = _claim_output(artifact_dir)
    mode = "DRY_RUN" if dry_run else "OPENROUTER_BOUNDED"
    contract, source_artifacts, crop_artifacts = _write_static_artifacts(
        output,
        prepared,
        mode=mode,
        source_store_sha256=source_sha,
        source_store_size_bytes=source_size,
        source_results_database_sha256=source_results_sha,
        source_results_database_size_bytes=source_results_size,
        effective_artifact_root=effective_artifact_root,
        contract_extensions=(
            None
            if sealed_adoption is None
            else {"sealed_observation_adoption_authority": sealed_adoption.authority}
        ),
    )
    run_contract_payload = canonical_json_bytes_v1(contract) + b"\n"
    run_contract_sha256 = sha256(run_contract_payload).hexdigest()
    if dry_run:
        result = {
            "disposition": "DRY_RUN_PREPARED",
            "format_version": FORMAT_VERSION,
            "job_count": len(prepared.jobs),
            "mode": mode,
            "official_selection": "NOT_PERFORMED",
            "plan_axis_sha256": contract["plan_axis_sha256"],
            "run_contract_sha256": run_contract_sha256,
            "selected_page_count": len(prepared.selected_ids),
            "source_page_store_sha256": source_sha,
        }
        _write_json(output / "run-result.json", result)
        _assert_frozen_database_unchanged(
            source_store,
            (source_sha, source_size),
            label="frozen source page store",
        )
        _assert_frozen_database_unchanged(
            source_results,
            (source_results_sha, source_results_size),
            label="frozen source family-results database",
        )
        return result
    assert (
        writable_store is not None
        and writable_results is not None
        and openrouter_api_key is not None
    )
    initialize_region_repair_extension_v1(writable_store)
    enqueued = enqueue_gemini_family_region_repair_plans_v1(
        writable_results,
        family_run_id=prepared.config["repair_source_family_run_id"],
        plans=prepared.plans,
    )
    if enqueued != [plan["repair_job_id"] for plan in prepared.plans]:
        raise _error("standard family-results queue does not preserve the authoritative plan axis")
    attempts_by_job: dict[str, list[dict[str, Any]]] = {
        job.plan["repair_job_id"]: [] for job in prepared.jobs
    }
    response_artifacts: dict[str, bytes] = {}
    attempt_artifact_manifests: list[dict[str, Any]] = []
    capture_checkpoint_ref: dict[str, Any] | None = None
    capture_failures: list[dict[str, Any]] = []
    reused_sealed_observation_count = 0
    new_provider_call_count = 0
    with tempfile.TemporaryDirectory(
        prefix="family13-table-repair-execution-",
        dir=output.parent,
    ):
        # One private page/results pair is the entire transaction.  Provider capture,
        # validation, lineage, and canonical attempt recording all happen on that pair;
        # the public targets remain byte-identical until the all-resolved publish gate.
        capture_store = writable_store
        if sealed_adoption is not None:
            for job in prepared.jobs:
                job_id = job.plan["repair_job_id"]
                for source_item in sealed_adoption.items_by_job[job_id]:
                    prior = attempts_by_job[job_id]
                    if prior and prior[-1]["next_status"] != "PENDING":
                        break
                    if source_item.thinking_level != _THINKING_LEVELS[len(prior)]:
                        raise _error("sealed observation sibling tier differs from current state")
                    attempt = _persist_observation(
                        output=output,
                        prepared=prepared,
                        job=job,
                        thinking_level=source_item.thinking_level,
                        observation=source_item.observation,
                        writable_page_store=capture_store,
                        writable_results_database=source_results,
                        prior_attempts=prior,
                        response_artifacts=response_artifacts,
                        attempt_artifact_manifests=attempt_artifact_manifests,
                        mirror_family_results=False,
                        sealed_source_link=source_item.source_link,
                    )
                    attempts_by_job[job_id].append(attempt)
                    reused_sealed_observation_count += 1
                    capture_checkpoint_ref = _write_capture_checkpoint(
                        output,
                        attempt_artifact_manifests=attempt_artifact_manifests,
                        attempts_by_job=attempts_by_job,
                        previous_checkpoint_ref=capture_checkpoint_ref,
                        run_contract_sha256=run_contract_sha256,
                    )
        for tier_index, thinking_level in enumerate(_THINKING_LEVELS):
            active = [
                job
                for job in prepared.jobs
                if len(attempts_by_job[job.plan["repair_job_id"]]) == tier_index
                and (
                    not attempts_by_job[job.plan["repair_job_id"]]
                    or attempts_by_job[job.plan["repair_job_id"]][-1]["next_status"] == "PENDING"
                )
            ]
            if not active:
                continue
            new_provider_call_count += len(active)
            with ThreadPoolExecutor(max_workers=min(workers, len(active))) as executor:
                future_to_job = {
                    executor.submit(
                        _call_provider,
                        job,
                        thinking_level=thinking_level,
                        api_key=openrouter_api_key,
                        timeout_seconds=timeout_seconds,
                        provider_call=provider_call,
                    ): job
                    for job in active
                }
                for future in as_completed(future_to_job):
                    job = future_to_job[future]
                    job_id = job.plan["repair_job_id"]
                    try:
                        observation = future.result()
                    except Exception as exc:  # noqa: BLE001 - preserve every billed sibling
                        failure = GeminiJsonFirstProviderV1Error(
                            "provider worker raised one undeclared exception; details are redacted"
                        )
                        failure.__cause__ = exc
                        observation = _ProviderObservation(
                            result=None,
                            error=failure,
                            elapsed_seconds="0",
                        )
                    try:
                        attempt = _persist_observation(
                            output=output,
                            prepared=prepared,
                            job=job,
                            thinking_level=thinking_level,
                            observation=observation,
                            writable_page_store=capture_store,
                            writable_results_database=source_results,
                            prior_attempts=attempts_by_job[job_id],
                            response_artifacts=response_artifacts,
                            attempt_artifact_manifests=attempt_artifact_manifests,
                            mirror_family_results=False,
                        )
                    except Exception as exc:  # noqa: BLE001 - harvest billed siblings first
                        capture_failures.append(
                            {
                                "error_type": type(exc).__name__,
                                "repair_job_id": job_id,
                                "thinking_level": thinking_level,
                            }
                        )
                        continue
                    attempts_by_job[job_id].append(attempt)
                    capture_checkpoint_ref = _write_capture_checkpoint(
                        output,
                        attempt_artifact_manifests=attempt_artifact_manifests,
                        attempts_by_job=attempts_by_job,
                        previous_checkpoint_ref=capture_checkpoint_ref,
                        run_contract_sha256=run_contract_sha256,
                    )
            if capture_failures:
                break
    attempts = [
        attempt for job in prepared.jobs for attempt in attempts_by_job[job.plan["repair_job_id"]]
    ]
    job_order = {job.plan["repair_job_id"]: ordinal for ordinal, job in enumerate(prepared.jobs)}
    attempt_artifact_manifests.sort(
        key=lambda item: (
            job_order[item["repair_job_id"]],
            item["attempt_ordinal"],
        )
    )
    attempt_axis_material = {
        "format_version": ATTEMPT_ARTIFACT_AXIS_FORMAT_VERSION,
        "manifests": attempt_artifact_manifests,
    }
    attempt_axis = {
        **attempt_axis_material,
        "manifest_axis_sha256": canonical_json_sha256_v1(attempt_artifact_manifests),
    }
    attempt_axis_payload = canonical_json_bytes_v1(attempt_axis) + b"\n"
    attempt_axis_path = output / "attempt-artifact-axis.json"
    _write_new(attempt_axis_path, attempt_axis_payload)
    attempt_axis_ref = _ref(output, attempt_axis_path, attempt_axis_payload)
    if capture_failures:
        recovery_journals = []
        for path in sorted(output.glob("jobs/job-*/attempt-*/pre-db-apply.json")):
            payload = path.read_bytes()
            recovery_journals.append(_ref(output, path, payload))
        incomplete = {
            "attempt_artifact_axis": attempt_axis_ref,
            "capture_failures": capture_failures,
            "capture_checkpoint": capture_checkpoint_ref,
            "disposition": "REPAIR_CAPTURE_INCOMPLETE",
            "format_version": FORMAT_VERSION,
            "mode": mode,
            "new_provider_call_count": new_provider_call_count,
            "official_selection": "NOT_PERFORMED",
            "provider_recall": "AUDITED_CONTINUATION_REQUIRED",
            "recovery_action": (
                "REVIEW_SEALED_ATTEMPTS_AND_CONTINUE_ONLY_MISSING_SIBLING_TIERS_"
                "WITHOUT_RECALLING_ANY_SEALED_PROVIDER_OBSERVATION"
            ),
            "recovery_journals": recovery_journals,
            "reused_sealed_observation_count": reused_sealed_observation_count,
            "run_contract_sha256": run_contract_sha256,
        }
        _write_json(output / "run-result.json", incomplete)
        _assert_frozen_database_unchanged(
            source_store,
            (source_sha, source_size),
            label="frozen source page store",
        )
        _assert_frozen_database_unchanged(
            source_results,
            (source_results_sha, source_results_size),
            label="frozen source family-results database",
        )
        return incomplete
    if any(
        not attempts_by_job[job.plan["repair_job_id"]]
        or attempts_by_job[job.plan["repair_job_id"]][-1]["next_status"]
        not in {"RESOLVED", "ABSTAINED"}
        for job in prepared.jobs
    ):
        raise _error("sealed capture phase did not reach one terminal attempt per job")
    terminal_status_counts = {
        status: sum(
            attempts_by_job[job.plan["repair_job_id"]][-1]["next_status"] == status
            for job in prepared.jobs
        )
        for status in ("ABSTAINED", "RESOLVED")
    }
    if terminal_status_counts != {"ABSTAINED": 0, "RESOLVED": len(prepared.jobs)}:
        incomplete = {
            "attempt_artifact_axis": attempt_axis_ref,
            "capture_checkpoint": capture_checkpoint_ref,
            "disposition": "REPAIR_FRONTIER_INCOMPLETE",
            "format_version": FORMAT_VERSION,
            "job_status_counts": terminal_status_counts,
            "mode": mode,
            "new_provider_call_count": new_provider_call_count,
            "official_selection": "NOT_PERFORMED",
            "provider_recall": "FORBIDDEN",
            "recovery_action": (
                "REVALIDATE_AUTHENTICATED_SEALED_RESPONSES_ON_ONE_FRESH_BASELINE_"
                "DATABASE_PAIR_WITHOUT_PROVIDER_RECALL"
            ),
            "reused_sealed_observation_count": reused_sealed_observation_count,
            "run_contract_sha256": run_contract_sha256,
        }
        _write_json(output / "run-result.json", incomplete)
        return incomplete
    manifest_artifacts = {}
    for entry in attempt_artifact_manifests:
        manifest = _validate_attempt_artifact_manifest(
            output,
            _json_artifact(
                output,
                entry["attempt_artifact_manifest_ref"],
                label="captured attempt artifact manifest",
            ),
        )
        manifest_artifacts[manifest["attempt_id"]] = manifest["artifacts"]
    apply_failures: list[dict[str, Any]] = []
    for job in prepared.jobs:
        for attempt in attempts_by_job[job.plan["repair_job_id"]]:
            try:
                if attempt["outcome"] == "RESOLVED":
                    _result, receipt, lineage, _response_bytes = _apply_sealed_resolved_observation(
                        sealed_output=output,
                        artifacts=manifest_artifacts[attempt["attempt_id"]],
                        prepared=prepared,
                        job=job,
                        writable_page_store=writable_store,
                    )
                    if (
                        attempt["observed_page_json_version_id"]
                        != lineage["observed_page_json_version_id"]
                        or attempt["repair_receipt_sha256"]
                        != sha256(canonical_json_bytes_v1(receipt) + b"\n").hexdigest()
                    ):
                        raise _error("captured resolved attempt differs from caller database apply")
                    _mirror_family_attempt(
                        writable_results,
                        attempt,
                        page_json_version_id_override=lineage["merged_page_json_version_id"],
                    )
                else:
                    _mirror_family_attempt(writable_results, attempt)
            except Exception as exc:  # noqa: BLE001 - all provider observations are sealed
                apply_failures.append(
                    {
                        "attempt_ordinal": attempt["attempt_ordinal"],
                        "error_type": type(exc).__name__,
                        "repair_job_id": attempt["repair_job_id"],
                    }
                )
    if apply_failures:
        recovery_journals = []
        for path in sorted(output.glob("jobs/job-*/attempt-*/pre-db-apply.json")):
            payload = path.read_bytes()
            recovery_journals.append(_ref(output, path, payload))
        incomplete = {
            "attempt_artifact_axis": attempt_axis_ref,
            "capture_checkpoint": capture_checkpoint_ref,
            "disposition": "REPAIR_FRONTIER_INCOMPLETE",
            "failed_database_apply_jobs": apply_failures,
            "format_version": FORMAT_VERSION,
            "mode": mode,
            "new_provider_call_count": new_provider_call_count,
            "official_selection": "NOT_PERFORMED",
            "provider_recall": "FORBIDDEN",
            "recovery_action": (
                "DISCARD_BOTH_WRITABLE_DATABASE_COPIES_AND_REPLAY_SEALED_ATTEMPT_"
                "ARTIFACTS_TO_FRESH_EXACT_COPIES"
            ),
            "recovery_journals": recovery_journals,
            "reused_sealed_observation_count": reused_sealed_observation_count,
            "run_contract_sha256": run_contract_sha256,
        }
        _write_json(output / "run-result.json", incomplete)
        _assert_frozen_database_unchanged(
            source_store,
            (source_sha, source_size),
            label="frozen source page store",
        )
        _assert_frozen_database_unchanged(
            source_results,
            (source_results_sha, source_results_size),
            label="frozen source family-results database",
        )
        return incomplete
    overlay = build_rollforward_table_repair_overlay_v1(
        family_run_id=prepared.config["repair_source_family_run_id"],
        plans=prepared.plans,
        attempts=attempts,
        page_store_path=writable_store,
        authority=prepared.authority,
        repair_spec_authority=prepared.repair_spec_authority,
        source_image_artifacts_by_sha256=source_artifacts,
        crop_image_artifacts_by_sha256=crop_artifacts,
        response_artifacts_by_sha256=response_artifacts,
    )
    replacement_job_ids = {
        attempts_by_job[job.plan["repair_job_id"]][-1]["repair_job_id"]
        for job in prepared.jobs
        if attempts_by_job[job.plan["repair_job_id"]][-1]["outcome"] == "RESOLVED"
    }
    source_no_change_job_ids = sorted(
        attempts_by_job[job.plan["repair_job_id"]][-1]["repair_job_id"]
        for job in prepared.jobs
        if attempts_by_job[job.plan["repair_job_id"]][-1]["outcome"]
        == "SOURCE_CORROBORATED_NO_CHANGE"
    )
    if (
        overlay.get("job_status_counts") != {"ABSTAINED": 0, "RESOLVED": len(prepared.jobs)}
        or len(overlay.get("replacements", [])) != len(replacement_job_ids)
        or {item.get("repair_job_id") for item in overlay.get("replacements", [])}
        != replacement_job_ids
    ):
        raise _error("complete repair frontier replacement axis differs from correction outcomes")
    overlay_payload = canonical_json_bytes_v1(overlay) + b"\n"
    overlay_path = output / "repair-overlay.json"
    _write_new(overlay_path, overlay_payload)
    overlay_ref = _ref(output, overlay_path, overlay_payload)
    standard_overlay = resolved_gemini_family_region_repair_overlay_v1(
        writable_results,
        family_run_id=prepared.config["repair_source_family_run_id"],
    )
    expected_standard_replacements = [
        {
            key: replacement[key]
            for key in (
                "base_page_json_version_id",
                "candidate_id",
                "document_ordinal",
                "physical_page",
                "repair_job_id",
                "selected_page_json_version_id",
            )
        }
        for replacement in overlay["replacements"]
    ]
    if (
        standard_overlay["family_id"] != overlay["family_id"]
        or standard_overlay["repair_source_family_run_id"] != overlay["repair_source_family_run_id"]
        or standard_overlay["job_status_counts"] != overlay["job_status_counts"]
        or standard_overlay["replacements"] != expected_standard_replacements
        or standard_overlay["source_corroborated_no_change_job_ids"] != source_no_change_job_ids
    ):
        raise _error("standard family-results overlay differs from the audited repair overlay")
    _bind_effective_frontier_database_ref(
        effective_artifact_root,
        prepared.config["writable_page_store_ref_path"],
        writable_store,
        label="effective-frontier page database",
        expected_identity=writable_page_store_ref_identity,
    )
    _bind_effective_frontier_database_ref(
        effective_artifact_root,
        prepared.config["writable_results_database_ref_path"],
        writable_results,
        label="effective-frontier results database",
        expected_identity=writable_results_database_ref_identity,
    )
    _reject_sqlite_sidecars(writable_store, label="writable page-store copy")
    _reject_sqlite_sidecars(writable_results, label="writable family-results database copy")
    writable_sha, writable_size = _sha_file(writable_store)
    writable_results_sha, writable_results_size = _sha_file(writable_results)
    effective_frontier = build_gemini_family_effective_page_frontier_v1(
        base_corpus_manifest_index_id=prepared.config["base_corpus_manifest_index_id"],
        base_page_json_version_ids=prepared.selected_ids,
        database_ref={
            "path": prepared.config["writable_page_store_ref_path"],
            "sha256": writable_sha,
            "size_bytes": writable_size,
        },
        family_id=overlay["family_id"],
        job_status_counts=overlay["job_status_counts"],
        repair_source_family_run_id=prepared.config["repair_source_family_run_id"],
        replacements=overlay["replacements"],
        results_database_ref={
            "path": prepared.config["writable_results_database_ref_path"],
            "sha256": writable_results_sha,
            "size_bytes": writable_results_size,
        },
        source_corroborated_no_change_job_ids=source_no_change_job_ids,
    )
    checked_frontier, effective_ids = apply_gemini_family_effective_page_frontier_v1(
        effective_frontier,
        base_page_json_version_ids=prepared.selected_ids,
    )
    if checked_frontier != effective_frontier or len(effective_ids) != len(prepared.selected_ids):
        raise _error("standard effective page frontier does not replay its exact ordered axis")
    frontier_payload = canonical_json_bytes_v1(effective_frontier) + b"\n"
    frontier_path = output / "effective-page-frontier.json"
    _write_new(frontier_path, frontier_payload)
    frontier_ref = _ref(output, frontier_path, frontier_payload)
    result = {
        "attempt_count": len(attempts),
        "attempt_artifact_axis": attempt_axis_ref,
        "capture_checkpoint": capture_checkpoint_ref,
        "disposition": "REPAIR_FRONTIER_COMPLETE",
        "format_version": FORMAT_VERSION,
        "job_count": len(prepared.jobs),
        "job_status_counts": overlay["job_status_counts"],
        "effective_page_frontier": frontier_ref,
        "effective_page_frontier_id": effective_frontier["effective_page_frontier_id"],
        "mode": mode,
        "new_provider_call_count": new_provider_call_count,
        "official_selection": "NOT_PERFORMED",
        "overlay_id": overlay["overlay_id"],
        "repair_overlay": overlay_ref,
        "plan_axis_sha256": contract["plan_axis_sha256"],
        "run_contract_sha256": run_contract_sha256,
        "reused_sealed_observation_count": reused_sealed_observation_count,
        "selected_page_count": len(prepared.selected_ids),
        "source_page_store_sha256": source_sha,
        "writable_page_store": {"sha256": writable_sha, "size_bytes": writable_size},
        "writable_results_database": {
            "sha256": writable_results_sha,
            "size_bytes": writable_results_size,
        },
    }
    _assert_frozen_database_unchanged(
        source_store,
        (source_sha, source_size),
        label="frozen source page store",
    )
    _assert_frozen_database_unchanged(
        source_results,
        (source_results_sha, source_results_size),
        label="frozen source family-results database",
    )
    return result


def run_rollforward_table_repair_v1(
    *,
    family_sweep_path: Path,
    family_sweep_sha256: str,
    selected_page_ids_path: Path,
    selected_page_ids_sha256: str,
    source_page_store: Path,
    source_page_store_sha256: str,
    source_results_database: Path,
    source_results_database_sha256: str,
    repair_spec_config_path: Path,
    repair_spec_config_sha256: str,
    workspace_root: Path,
    runner_implementation_sha256: str,
    artifact_root: Path,
    artifact_dir: Path,
    dry_run: bool,
    writable_page_store: Path | None = None,
    writable_results_database: Path | None = None,
    openrouter_api_key: str | None = None,
    workers: int = 6,
    timeout_seconds: int = 900,
    provider_call: Callable[..., ProviderResultV1] = call_gemini_json_first_v1,
    sealed_observation_artifact_dir: Path | None = None,
    sealed_observation_run_result_sha256: str | None = None,
    sealed_observation_git_commit: str | None = None,
) -> dict[str, Any]:
    """Run from held read-only sources with exactly one private page/results work pair."""

    boundaries: list[_SqliteBoundary] = []
    with tempfile.TemporaryDirectory(prefix="family13-table-repair-sqlite-boundary-") as directory:
        private_root = Path(directory)
        try:
            source_store_boundary = _establish_sqlite_boundary(
                source_page_store,
                source_page_store_sha256,
                label="frozen source page store",
                private_path=private_root / "source-page-store.sqlite3",
                writable=False,
                copy_to_private=False,
            )
            boundaries.append(source_store_boundary)
            source_results_boundary = _establish_sqlite_boundary(
                source_results_database,
                source_results_database_sha256,
                label="frozen source family-results database",
                private_path=private_root / "source-family-results.sqlite3",
                writable=False,
                copy_to_private=False,
            )
            boundaries.append(source_results_boundary)
            writable_store_boundary = None
            writable_results_boundary = None
            if not dry_run and writable_page_store is not None:
                writable_store_boundary = _establish_sqlite_boundary(
                    writable_page_store,
                    source_page_store_sha256,
                    label="writable page-store copy",
                    private_path=private_root / "writable-page-store.sqlite3",
                    writable=True,
                )
                boundaries.append(writable_store_boundary)
                if writable_store_boundary.identity == source_store_boundary.identity:
                    raise _error(
                        "writable page-store copy is the frozen source file or one hard link to it"
                    )
            if not dry_run and writable_results_database is not None:
                writable_results_boundary = _establish_sqlite_boundary(
                    writable_results_database,
                    source_results_database_sha256,
                    label="writable family-results database copy",
                    private_path=private_root / "writable-family-results.sqlite3",
                    writable=True,
                )
                boundaries.append(writable_results_boundary)
                if writable_results_boundary.identity == source_results_boundary.identity:
                    raise _error(
                        "writable family-results database copy is the frozen source file or "
                        "one hard link to it"
                    )
            result = _run_rollforward_table_repair_on_private_sqlite_v1(
                family_sweep_path=family_sweep_path,
                family_sweep_sha256=family_sweep_sha256,
                selected_page_ids_path=selected_page_ids_path,
                selected_page_ids_sha256=selected_page_ids_sha256,
                source_page_store=source_store_boundary.private_path,
                source_page_store_sha256=source_page_store_sha256,
                source_results_database=source_results_boundary.private_path,
                source_results_database_sha256=source_results_database_sha256,
                repair_spec_config_path=repair_spec_config_path,
                repair_spec_config_sha256=repair_spec_config_sha256,
                workspace_root=workspace_root,
                runner_implementation_sha256=runner_implementation_sha256,
                artifact_root=artifact_root,
                artifact_dir=artifact_dir,
                dry_run=dry_run,
                writable_page_store=(
                    None
                    if writable_store_boundary is None
                    else writable_store_boundary.private_path
                ),
                writable_results_database=(
                    None
                    if writable_results_boundary is None
                    else writable_results_boundary.private_path
                ),
                writable_page_store_ref_identity=(
                    None if writable_store_boundary is None else writable_store_boundary.identity
                ),
                writable_results_database_ref_identity=(
                    None
                    if writable_results_boundary is None
                    else writable_results_boundary.identity
                ),
                openrouter_api_key=openrouter_api_key,
                workers=workers,
                timeout_seconds=timeout_seconds,
                provider_call=provider_call,
                sealed_observation_artifact_dir=sealed_observation_artifact_dir,
                sealed_observation_run_result_sha256=(sealed_observation_run_result_sha256),
                sealed_observation_git_commit=sealed_observation_git_commit,
            )
            _assert_sqlite_boundary_current(
                source_store_boundary,
                expected_sha256=source_store_boundary.initial_sha256,
                expected_size_bytes=source_store_boundary.initial_size_bytes,
            )
            _assert_sqlite_boundary_current(
                source_results_boundary,
                expected_sha256=source_results_boundary.initial_sha256,
                expected_size_bytes=source_results_boundary.initial_size_bytes,
            )
            if writable_store_boundary is not None and writable_results_boundary is not None:
                _assert_sqlite_boundary_current(
                    writable_store_boundary,
                    expected_sha256=writable_store_boundary.initial_sha256,
                    expected_size_bytes=writable_store_boundary.initial_size_bytes,
                )
                _assert_sqlite_boundary_current(
                    writable_results_boundary,
                    expected_sha256=writable_results_boundary.initial_sha256,
                    expected_size_bytes=writable_results_boundary.initial_size_bytes,
                )
                if result.get("disposition") == "REPAIR_FRONTIER_COMPLETE":
                    _require_all_planned_jobs_resolved(
                        result,
                        disposition="REPAIR_FRONTIER_COMPLETE",
                    )
                    _bind_published_database_refs(
                        artifact_root=artifact_root,
                        repair_spec_config_path=repair_spec_config_path,
                        repair_spec_config_sha256=repair_spec_config_sha256,
                        writable_store_boundary=writable_store_boundary,
                        writable_results_boundary=writable_results_boundary,
                        label_prefix="published effective-frontier",
                    )
                    published = False
                    try:
                        published_store, published_results = _publish_private_sqlite_pair(
                            writable_store_boundary,
                            writable_results_boundary,
                            source_store_boundary,
                            source_results_boundary,
                        )
                        published = True
                        if result.get("writable_page_store") != {
                            "sha256": published_store[0],
                            "size_bytes": published_store[1],
                        }:
                            raise _error("published page-store bytes differ from the run result")
                        if result.get("writable_results_database") != {
                            "sha256": published_results[0],
                            "size_bytes": published_results[1],
                        }:
                            raise _error(
                                "published family-results bytes differ from the run result"
                            )
                        _assert_sqlite_boundary_current(
                            source_store_boundary,
                            expected_sha256=source_store_boundary.initial_sha256,
                            expected_size_bytes=source_store_boundary.initial_size_bytes,
                        )
                        _assert_sqlite_boundary_current(
                            source_results_boundary,
                            expected_sha256=source_results_boundary.initial_sha256,
                            expected_size_bytes=source_results_boundary.initial_size_bytes,
                        )
                        _write_json(Path(artifact_dir).resolve() / "run-result.json", result)
                    except Exception:
                        if published:
                            _rollback_published_sqlite_pair(
                                writable_store_boundary,
                                writable_results_boundary,
                                source_store_boundary,
                                source_results_boundary,
                            )
                        (Path(artifact_dir).resolve() / "run-result.json").unlink(missing_ok=True)
                        raise
                elif result.get("disposition") not in {
                    "REPAIR_CAPTURE_INCOMPLETE",
                    "REPAIR_FRONTIER_INCOMPLETE",
                }:
                    raise _error("bounded provider run returned an unknown terminal disposition")
            return result
        finally:
            _close_sqlite_boundaries(boundaries)


def _legacy_plan_semantic_projection(plan: Any) -> dict[str, Any]:
    if type(plan) is not dict or type(plan.get("repair_job_id")) is not str:
        raise _error("quarantined legacy plan is invalid")
    material = {key: plan[key] for key in plan if key != "repair_job_id"}
    if plan["repair_job_id"] != "gjfrrqv1:job:" + canonical_json_sha256_v1(material):
        raise _error("quarantined legacy plan identity does not replay")
    excluded = {"acceptance_policy", "repair_job_id", "request_contract"}
    return {key: plan[key] for key in sorted(plan) if key not in excluded}


def _validate_quarantined_legacy_attempt(
    sealed_output: Path,
    *,
    entry: Mapping[str, Any],
    manifest: Mapping[str, Any],
    legacy_plan: Mapping[str, Any],
) -> dict[str, Any]:
    artifacts = manifest["artifacts"]
    attempt = _json_artifact(
        sealed_output,
        artifacts["attempt.json"],
        label="quarantined legacy repair attempt",
    )
    if type(attempt) is not dict or type(attempt.get("attempt_id")) is not str:
        raise _error("quarantined legacy attempt is invalid")
    material = {key: attempt[key] for key in attempt if key != "attempt_id"}
    if (
        attempt["attempt_id"] != "gjfrtav1:attempt:" + canonical_json_sha256_v1(material)
        or attempt["attempt_id"] != entry["attempt_id"]
        or attempt.get("repair_job_id") != legacy_plan["repair_job_id"]
        or attempt.get("repair_job_id") != manifest["repair_job_id"]
        or attempt.get("attempt_ordinal") != entry["attempt_ordinal"]
        or attempt.get("thinking_level") != entry["thinking_level"]
        or attempt.get("thinking_level") != _THINKING_LEVELS[attempt.get("attempt_ordinal", 0) - 1]
        or attempt.get("sibling_base_page_json_version_id")
        != legacy_plan["base_page_json_version_id"]
        or attempt.get("request_contract_sha256")
        != canonical_json_sha256_v1(legacy_plan["request_contract"])
        or attempt.get("outcome")
        not in {
            "PROVIDER_OR_VALIDATION_FAILURE",
            "RESOLVED",
            "RETRYABLE_VALIDATION_FAILURE",
        }
        or attempt.get("next_status") not in {"ABSTAINED", "PENDING", "RESOLVED"}
    ):
        raise _error("quarantined legacy attempt lineage is incoherent")
    for artifact_name, attempt_field in (
        ("provider.json", "provider"),
        ("usage.json", "usage"),
    ):
        if not same_typed_json_v1(
            _json_artifact(
                sealed_output,
                artifacts[artifact_name],
                label=f"quarantined legacy {artifact_name}",
            ),
            attempt[attempt_field],
        ):
            raise _error("quarantined legacy attempt artifacts disagree")
    legacy_validation = _json_artifact(
        sealed_output,
        artifacts["validation.json"],
        label="quarantined legacy validation.json",
    )
    if (
        type(legacy_validation) is not dict
        or {
            "reason_codes": legacy_validation.get("reason_codes"),
            "status": legacy_validation.get("status"),
        }
        != attempt["validation"]
    ):
        raise _error("quarantined legacy validation summary disagrees")
    response_ref = attempt.get("response_artifact_ref")
    manifest_response_ref = artifacts.get("table-response.json") or artifacts.get(
        "provider-envelope.bin"
    )
    if (response_ref is None) != (manifest_response_ref is None) or (
        response_ref is not None and response_ref != manifest_response_ref
    ):
        raise _error("quarantined legacy response authority is incoherent")
    return attempt


def _authenticate_sealed_implementation_ref_v1(
    *,
    reference: Any,
    expected_path: str,
    workspace_root: Path,
    git_commit: str | None,
    current_reference: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        type(reference) is not dict
        or set(reference) != {"path", "sha256", "size_bytes"}
        or reference.get("path") != expected_path
        or type(reference.get("sha256")) is not str
        or _HEX64.fullmatch(reference["sha256"]) is None
        or type(reference.get("size_bytes")) is not int
        or reference["size_bytes"] <= 0
    ):
        raise _error("sealed observation implementation reference drifted")
    if git_commit is None:
        if not same_typed_json_v1(reference, current_reference):
            raise _error("sealed observation implementation differs without a pinned Git commit")
        return json.loads(canonical_json_bytes_v1(reference))
    if type(git_commit) is not str or re.fullmatch(r"[0-9a-f]{40}", git_commit) is None:
        raise _error("sealed observation Git commit must be one full lowercase object ID")
    root = workspace_root.resolve()
    try:
        resolved = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "rev-parse",
                "--verify",
                f"{git_commit}^{{commit}}",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        blob = subprocess.run(
            ["git", "-C", str(root), "show", f"{git_commit}:{expected_path}"],
            check=True,
            capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise _error("sealed observation Git implementation authority cannot be resolved") from exc
    if (
        resolved != git_commit
        or sha256(blob).hexdigest() != reference["sha256"]
        or len(blob) != reference["size_bytes"]
    ):
        raise _error("sealed observation implementation differs from the pinned Git blob")
    return json.loads(canonical_json_bytes_v1(reference))


def _sealed_failure_observation_v1(
    sealed_output: Path,
    artifacts: Mapping[str, Mapping[str, Any]],
) -> _ProviderObservation:
    provider_attempts = _json_artifact(
        sealed_output,
        artifacts["provider-attempts.json"],
        label="sealed failed provider attempts",
    )
    observation = _json_artifact(
        sealed_output,
        artifacts["observation.json"],
        label="sealed failed provider observation",
    )
    if (
        type(provider_attempts) is not list
        or type(observation) is not dict
        or set(observation) != {"elapsed_seconds"}
        or type(observation["elapsed_seconds"]) is not str
    ):
        raise _error("sealed failed provider observation contract drifted")
    error = GeminiJsonFirstProviderV1Error(
        "authenticated sealed provider observation did not contain usable output"
    )
    error.attempts = tuple(provider_attempts)
    envelope_ref = artifacts.get("provider-envelope.bin")
    error.raw_response_bytes = (
        None
        if envelope_ref is None
        else _authenticated_artifact_ref(sealed_output, envelope_ref).read_bytes()
    )
    return _ProviderObservation(
        result=None,
        error=error,
        elapsed_seconds=observation["elapsed_seconds"],
    )


def _validate_sealed_observation_adoption_source_v1(
    *,
    sealed_artifact_dir: Path,
    sealed_run_result_sha256: str,
    sealed_git_commit: str | None,
    prepared: _PreparedRun,
    workspace_root: Path,
    source_sha: str,
    source_size: int,
    source_results_sha: str,
    source_results_size: int,
) -> _SealedObservationAdoption:
    sealed_input = Path(sealed_artifact_dir)
    sealed_output = sealed_input.resolve()
    if sealed_input.is_symlink() or not sealed_output.is_dir():
        raise _error("sealed observation artifact directory is absent or a symlink")
    sealed_result = _read_pinned_json(
        sealed_output / "run-result.json",
        sealed_run_result_sha256,
        label="sealed observation run result",
    ).value
    if (
        type(sealed_result) is not dict
        or sealed_result.get("format_version") != FORMAT_VERSION
        or sealed_result.get("mode") != "OPENROUTER_BOUNDED"
        or sealed_result.get("official_selection") != "NOT_PERFORMED"
        or sealed_result.get("disposition")
        not in {
            "REPAIR_CAPTURE_INCOMPLETE",
            "REPAIR_FRONTIER_COMPLETE",
            "REPAIR_FRONTIER_INCOMPLETE",
        }
    ):
        raise _error("sealed observation source is not one bounded non-OFFICIAL run")
    contract_path = sealed_output / "run-contract.json"
    contract_raw = contract_path.read_bytes()
    if sha256(contract_raw).hexdigest() != sealed_result.get("run_contract_sha256"):
        raise _error("sealed observation run contract differs from its result")
    try:
        contract = json.loads(contract_raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("sealed observation run contract is not valid JSON") from exc
    if (
        type(contract) is not dict
        or contract.get("format_version") != FORMAT_VERSION
        or contract.get("mode") != "OPENROUTER_BOUNDED"
        or contract.get("official_selection") != "NOT_PERFORMED"
        or contract.get("expected_plan_count") != len(prepared.plans)
        or contract.get("expected_selected_page_count") != len(prepared.selected_ids)
        or contract.get("plan_axis_sha256") != canonical_json_sha256_v1(prepared.plans)
        or contract.get("source_page_store") != {"sha256": source_sha, "size_bytes": source_size}
        or contract.get("source_family_results_database")
        != {"sha256": source_results_sha, "size_bytes": source_results_size}
    ):
        raise _error("sealed observation run contract differs from the current authority")
    runner_ref = _authenticate_sealed_implementation_ref_v1(
        reference=contract.get("runner_implementation_ref"),
        expected_path=RUNNER_IMPLEMENTATION_PATH,
        workspace_root=workspace_root,
        git_commit=sealed_git_commit,
        current_reference=prepared.runner_implementation_ref,
    )
    projector_ref = _authenticate_sealed_implementation_ref_v1(
        reference=contract.get("projector_implementation_ref"),
        expected_path=PROJECTOR_IMPLEMENTATION_PATH,
        workspace_root=workspace_root,
        git_commit=sealed_git_commit,
        current_reference=prepared.projector_implementation_ref,
    )
    expected_inputs = {name: pinned for name, pinned in prepared.pinned_inputs.items()}
    if set(contract.get("input_artifacts", {})) != set(expected_inputs):
        raise _error("sealed observation input artifact axis is incomplete")
    for name, pinned in expected_inputs.items():
        reference = contract["input_artifacts"][name]
        path = _authenticated_artifact_ref(sealed_output, reference)
        if path.read_bytes() != pinned.raw:
            raise _error("sealed observation pinned input differs from the current input")
    authority_refs = contract.get("authority_artifacts")
    if type(authority_refs) is not dict or set(authority_refs) != {
        "plan_axis",
        "plan_replay",
        "repair_spec",
        "source_family_run",
    }:
        raise _error("sealed observation authority artifact axis drifted")
    source_plans = _json_artifact(
        sealed_output,
        authority_refs["plan_axis"],
        label="sealed observation plan axis",
    )
    if (
        not same_typed_json_v1(source_plans, prepared.plans)
        or not same_typed_json_v1(
            _json_artifact(
                sealed_output,
                authority_refs["plan_replay"],
                label="sealed observation plan replay authority",
            ),
            prepared.authority,
        )
        or not same_typed_json_v1(
            _json_artifact(
                sealed_output,
                authority_refs["repair_spec"],
                label="sealed observation repair-spec authority",
            ),
            prepared.repair_spec_authority,
        )
        or not same_typed_json_v1(
            _json_artifact(
                sealed_output,
                authority_refs["source_family_run"],
                label="sealed observation baseline family run",
            ),
            prepared.baseline_run_receipt,
        )
    ):
        raise _error("sealed observation source authority does not exact-replay")
    jobs_by_id = {job.plan["repair_job_id"]: job for job in prepared.jobs}
    contract_jobs = contract.get("jobs")
    if type(contract_jobs) is not list or len(contract_jobs) != len(prepared.jobs):
        raise _error("sealed observation static job axis drifted")
    expected_static_names = {
        "crop-image.png",
        "crop-receipt.json",
        "plan.json",
        "prompt.txt",
        "response-schema.json",
        "source-image.png",
        "source-resolution-receipt.json",
    }
    for contract_job in contract_jobs:
        if type(contract_job) is not dict:
            raise _error("sealed observation static job is invalid")
        job = jobs_by_id.get(contract_job.get("repair_job_id"))
        artifacts = contract_job.get("artifacts")
        if job is None or type(artifacts) is not dict or set(artifacts) != expected_static_names:
            raise _error("sealed observation static job does not bind the current plan")
        expected_payloads = {
            "crop-image.png": job.crop_image,
            "crop-receipt.json": canonical_json_bytes_v1(job.crop_receipt) + b"\n",
            "plan.json": canonical_json_bytes_v1(job.plan) + b"\n",
            "prompt.txt": job.prompt.encode("utf-8"),
            "response-schema.json": canonical_json_bytes_v1(job.response_schema) + b"\n",
            "source-image.png": job.source_image,
            "source-resolution-receipt.json": (
                canonical_json_bytes_v1(job.source_resolution_receipt) + b"\n"
            ),
        }
        if (
            contract_job.get("document_ordinal") != job.plan["document_ordinal"]
            or contract_job.get("physical_page") != job.plan["physical_page"]
        ):
            raise _error("sealed observation static job locator drifted")
        for name, expected in expected_payloads.items():
            if _authenticated_artifact_ref(sealed_output, artifacts[name]).read_bytes() != expected:
                raise _error("sealed observation static request artifact drifted")
    axis = _json_artifact(
        sealed_output,
        sealed_result.get("attempt_artifact_axis"),
        label="sealed observation attempt artifact axis",
    )
    if (
        type(axis) is not dict
        or axis.get("format_version") != ATTEMPT_ARTIFACT_AXIS_FORMAT_VERSION
        or type(axis.get("manifests")) is not list
        or axis.get("manifest_axis_sha256") != canonical_json_sha256_v1(axis.get("manifests"))
    ):
        raise _error("sealed observation attempt artifact axis identity drifted")
    checkpoint = _validate_capture_checkpoint(
        sealed_output,
        _json_artifact(
            sealed_output,
            sealed_result.get("capture_checkpoint"),
            label="sealed observation terminal checkpoint",
        ),
    )
    if checkpoint["run_contract_sha256"] != sealed_result["run_contract_sha256"] or sorted(
        checkpoint["attempt_artifact_manifests"],
        key=lambda item: item["attempt_id"],
    ) != sorted(axis["manifests"], key=lambda item: item["attempt_id"]):
        raise _error("sealed observation checkpoint differs from its attempt axis")
    items_by_job: dict[str, list[_SealedObservationAdoptionItem]] = {
        job_id: [] for job_id in jobs_by_id
    }
    source_attempt_ids: list[str] = []
    source_usage_axis: list[dict[str, Any]] = []
    source_job_order = {job.plan["repair_job_id"]: index for index, job in enumerate(prepared.jobs)}
    if any(
        type(entry) is not dict or entry.get("repair_job_id") not in source_job_order
        for entry in axis["manifests"]
    ):
        raise _error("sealed observation attempt names an unknown repair job")
    for entry in sorted(
        axis["manifests"],
        key=lambda item: (
            source_job_order[item["repair_job_id"]],
            item["attempt_ordinal"],
        ),
    ):
        job = jobs_by_id.get(entry.get("repair_job_id"))
        if job is None:
            raise _error("sealed observation attempt names an unknown repair job")
        manifest = _validate_attempt_artifact_manifest(
            sealed_output,
            _json_artifact(
                sealed_output,
                entry["attempt_artifact_manifest_ref"],
                label="sealed observation attempt manifest",
            ),
        )
        attempt = _validate_quarantined_legacy_attempt(
            sealed_output,
            entry=entry,
            manifest=manifest,
            legacy_plan=job.plan,
        )
        expected_ordinal = len(items_by_job[attempt["repair_job_id"]]) + 1
        if attempt["attempt_ordinal"] != expected_ordinal:
            raise _error("sealed observation sibling attempt axis is noncontiguous")
        request = _json_artifact(
            sealed_output,
            manifest["artifacts"]["request.json"],
            label="sealed observation provider request",
        )
        expected_request = _request_material(job, attempt["thinking_level"])
        expected_request_id = canonical_json_sha256_v1(expected_request)
        if request != {**expected_request, "request_id_sha256": expected_request_id}:
            raise _error("sealed observation provider request differs from the current plan")
        artifacts = manifest["artifacts"]
        observation_record = _json_artifact(
            sealed_output,
            artifacts["observation.json"],
            label="sealed provider observation timing",
        )
        if (
            type(observation_record) is not dict
            or set(observation_record) != {"elapsed_seconds"}
            or type(observation_record["elapsed_seconds"]) is not str
        ):
            raise _error("sealed provider observation timing drifted")
        if {
            "provider-attempts.json",
            "provider-envelope.bin",
            "provider-result.json",
            "table-response.json",
        } <= set(artifacts):
            observation = _ProviderObservation(
                result=_provider_result_from_sealed_artifacts(sealed_output, artifacts),
                error=None,
                elapsed_seconds=observation_record["elapsed_seconds"],
            )
        else:
            observation = _sealed_failure_observation_v1(sealed_output, artifacts)
        source_attempt_ids.append(attempt["attempt_id"])
        source_usage_axis.append({"attempt_id": attempt["attempt_id"], "usage": attempt["usage"]})
        link_material = {
            "adoption_authority_sha256": None,
            "format_version": SEALED_OBSERVATION_SOURCE_LINK_FORMAT_VERSION,
            "source_attempt_id": attempt["attempt_id"],
            "source_attempt_manifest_sha256": manifest["manifest_sha256"],
            "source_attempt_ordinal": attempt["attempt_ordinal"],
            "source_attempt_outcome": attempt["outcome"],
            "source_git_commit": sealed_git_commit,
            "source_repair_job_id": attempt["repair_job_id"],
            "source_response_artifact_ref": attempt.get("response_artifact_ref"),
            "source_run_result_sha256": sealed_run_result_sha256,
        }
        items_by_job[attempt["repair_job_id"]].append(
            _SealedObservationAdoptionItem(
                job_id=attempt["repair_job_id"],
                source_attempt=attempt,
                source_link=link_material,
                thinking_level=attempt["thinking_level"],
                observation=observation,
            )
        )
    expected_job_states = [
        {
            "attempt_count": len(items_by_job[job_id]),
            "next_status": (
                items_by_job[job_id][-1].source_attempt["next_status"]
                if items_by_job[job_id]
                else "PENDING"
            ),
            "repair_job_id": job_id,
        }
        for job_id in jobs_by_id
    ]
    if checkpoint["job_states"] != expected_job_states:
        raise _error("sealed observation checkpoint job state differs from its attempts")
    terminal_counts = {
        status: sum(
            item["next_status"] == status
            for item in (
                attempts[-1].source_attempt for attempts in items_by_job.values() if attempts
            )
        )
        for status in ("ABSTAINED", "RESOLVED")
    }
    if (
        sealed_result.get("job_status_counts") is not None
        and sealed_result["job_status_counts"] != terminal_counts
    ):
        raise _error("sealed observation result status counts differ from its attempts")
    material = {
        "authenticity": {
            "current_runner_revalidates_every_response": True,
            "historical_implementation_is_authenticated_by_git": sealed_git_commit is not None,
            "provider_recall_for_sealed_attempts": "FORBIDDEN",
        },
        "format_version": SEALED_OBSERVATION_ADOPTION_AUTHORITY_FORMAT_VERSION,
        "source_artifact_root": str(sealed_output),
        "source_attempt_axis_sha256": axis["manifest_axis_sha256"],
        "source_attempt_count": len(source_attempt_ids),
        "source_attempt_ids": source_attempt_ids,
        "source_capture_checkpoint_sha256": checkpoint["capture_checkpoint_sha256"],
        "source_git_commit": sealed_git_commit,
        "source_plan_axis_sha256": canonical_json_sha256_v1(source_plans),
        "source_projector_implementation_ref": projector_ref,
        "source_run_contract_sha256": sealed_result["run_contract_sha256"],
        "source_run_result_sha256": sealed_run_result_sha256,
        "source_runner_implementation_ref": runner_ref,
        "source_usage_axis": source_usage_axis,
        "source_usage_axis_sha256": canonical_json_sha256_v1(source_usage_axis),
    }
    authority = {
        **material,
        "adoption_authority_sha256": canonical_json_sha256_v1(material),
    }
    bound_items = {}
    for job_id, items in items_by_job.items():
        bound = []
        for item in items:
            link_material = {
                **item.source_link,
                "adoption_authority_sha256": authority["adoption_authority_sha256"],
            }
            link = {**link_material, "link_sha256": canonical_json_sha256_v1(link_material)}
            bound.append(
                _SealedObservationAdoptionItem(
                    job_id=item.job_id,
                    source_attempt=item.source_attempt,
                    source_link=link,
                    thinking_level=item.thinking_level,
                    observation=item.observation,
                )
            )
        bound_items[job_id] = bound
    return _SealedObservationAdoption(authority=authority, items_by_job=bound_items)


def _validate_quarantined_legacy_source_v1(
    *,
    sealed_output: Path,
    sealed_result: Mapping[str, Any],
    contract: Mapping[str, Any],
    prepared: _PreparedRun,
    source_sha: str,
    source_size: int,
    source_results_sha: str,
    source_results_size: int,
    page_store_path: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    expected_count = len(prepared.jobs)
    if (
        sealed_result.get("disposition") != "REPAIR_FRONTIER_COMPLETE"
        or sealed_result.get("job_count") != expected_count
        or sealed_result.get("job_status_counts") != {"ABSTAINED": 3, "RESOLVED": 3}
        or sealed_result.get("official_selection") != "NOT_PERFORMED"
    ):
        raise _error("sealed source is not the exact quarantined mixed-status legacy root")
    if (
        contract.get("format_version") != FORMAT_VERSION
        or contract.get("mode") != "OPENROUTER_BOUNDED"
        or contract.get("official_selection") != "NOT_PERFORMED"
        or contract.get("expected_plan_count") != expected_count
        or contract.get("expected_selected_page_count") != len(prepared.selected_ids)
        or contract.get("source_page_store") != {"sha256": source_sha, "size_bytes": source_size}
        or contract.get("source_family_results_database")
        != {"sha256": source_results_sha, "size_bytes": source_results_size}
    ):
        raise _error("quarantined legacy contract differs from the current pinned baseline")
    legacy_runner_ref = contract.get("runner_implementation_ref")
    if (
        type(legacy_runner_ref) is not dict
        or set(legacy_runner_ref) != {"path", "sha256", "size_bytes"}
        or legacy_runner_ref.get("path") != RUNNER_IMPLEMENTATION_PATH
        or _expected_hash(
            legacy_runner_ref.get("sha256"),
            label="quarantined legacy runner implementation SHA-256",
        )
        != legacy_runner_ref["sha256"]
        or type(legacy_runner_ref.get("size_bytes")) is not int
        or legacy_runner_ref["size_bytes"] <= 0
    ):
        raise _error("quarantined legacy runner implementation reference drifted")
    expected_inputs = {
        name: {"sha256": pinned.sha256, "size_bytes": len(pinned.raw)}
        for name, pinned in prepared.pinned_inputs.items()
    }
    for name, reference in contract.get("input_artifacts", {}).items():
        if name not in expected_inputs:
            raise _error("quarantined legacy contract contains an unknown pinned input")
        path = _authenticated_artifact_ref(sealed_output, reference)
        if (reference["sha256"], reference["size_bytes"]) != (
            expected_inputs[name]["sha256"],
            expected_inputs[name]["size_bytes"],
        ) or path.read_bytes() != prepared.pinned_inputs[name].raw:
            raise _error("quarantined legacy input differs from the current pin")
    if set(contract.get("input_artifacts", {})) != set(expected_inputs):
        raise _error("quarantined legacy input authority is incomplete")
    authority_refs = contract.get("authority_artifacts")
    if type(authority_refs) is not dict or set(authority_refs) != {
        "plan_axis",
        "plan_replay",
        "repair_spec",
        "source_family_run",
    }:
        raise _error("quarantined legacy authority artifact axis drifted")
    legacy_plans = _json_artifact(
        sealed_output,
        authority_refs["plan_axis"],
        label="quarantined legacy plan axis",
    )
    legacy_replay_authority = _json_artifact(
        sealed_output,
        authority_refs["plan_replay"],
        label="quarantined legacy plan replay authority",
    )
    legacy_repair_authority = _json_artifact(
        sealed_output,
        authority_refs["repair_spec"],
        label="quarantined legacy repair-spec authority",
    )
    legacy_baseline = _json_artifact(
        sealed_output,
        authority_refs["source_family_run"],
        label="quarantined legacy family-run authority",
    )
    if (
        type(legacy_plans) is not list
        or len(legacy_plans) != expected_count
        or contract.get("plan_axis_sha256") != canonical_json_sha256_v1(legacy_plans)
        or legacy_replay_authority != prepared.authority
        or legacy_baseline != prepared.baseline_run_receipt
    ):
        raise _error("quarantined legacy plan authority does not replay")
    legacy_repair_authority_fields = {
        "authority",
        "authenticity",
        "format_version",
        "manifest_sha256",
        "plan_axis_sha256",
        "repair_spec_axis_sha256",
        "source_image_bindings",
        "source_image_bindings_sha256",
        "source_image_resolver",
    }
    legacy_repair_authority_material = (
        {
            key: legacy_repair_authority[key]
            for key in legacy_repair_authority
            if key != "manifest_sha256"
        }
        if type(legacy_repair_authority) is dict
        else {}
    )
    if (
        type(legacy_repair_authority) is not dict
        or set(legacy_repair_authority) != legacy_repair_authority_fields
        or type(legacy_repair_authority.get("source_image_bindings")) is not list
        or legacy_repair_authority.get("manifest_sha256")
        != canonical_json_sha256_v1(legacy_repair_authority_material)
        or legacy_repair_authority.get("plan_axis_sha256") != canonical_json_sha256_v1(legacy_plans)
        or legacy_repair_authority.get("repair_spec_axis_sha256")
        != canonical_json_sha256_v1(prepared.config["table_repair_specs"])
        or legacy_repair_authority.get("source_image_bindings_sha256")
        != canonical_json_sha256_v1(legacy_repair_authority.get("source_image_bindings"))
    ):
        raise _error("quarantined legacy repair-spec authority identity drifted")
    legacy_by_semantic = {
        canonical_json_sha256_v1(_legacy_plan_semantic_projection(plan)): plan
        for plan in legacy_plans
    }
    new_by_semantic = {
        canonical_json_sha256_v1(_legacy_plan_semantic_projection(plan)): job
        for plan, job in zip(prepared.plans, prepared.jobs, strict=True)
    }
    if set(legacy_by_semantic) != set(new_by_semantic) or len(legacy_by_semantic) != expected_count:
        raise _error("quarantined legacy and minimal-observation plan semantics differ")
    old_binding_axis = [
        {key: value for key, value in binding.items() if key != "repair_job_id"}
        for binding in legacy_repair_authority.get("source_image_bindings", [])
    ]
    new_binding_axis = [
        {key: value for key, value in binding.items() if key != "repair_job_id"}
        for binding in prepared.repair_spec_authority["source_image_bindings"]
    ]
    for field in (
        "authenticity",
        "authority",
        "format_version",
        "repair_spec_axis_sha256",
        "source_image_resolver",
    ):
        if legacy_repair_authority.get(field) != prepared.repair_spec_authority[field]:
            raise _error("quarantined legacy repair-spec authority differs semantically")
    if old_binding_axis != new_binding_axis:
        raise _error("quarantined legacy source-image binding axis differs")
    contract_jobs = contract.get("jobs")
    if type(contract_jobs) is not list or len(contract_jobs) != expected_count:
        raise _error("quarantined legacy job artifact axis is invalid")
    old_job_to_new: dict[str, _PreparedJob] = {}
    legacy_static_artifacts_by_job: dict[str, dict[str, Any]] = {}
    expected_static_artifact_names = {
        "crop-image.png",
        "crop-receipt.json",
        "plan.json",
        "prompt.txt",
        "response-schema.json",
        "source-image.png",
        "source-resolution-receipt.json",
    }
    for legacy_plan, contract_job in zip(legacy_plans, contract_jobs, strict=True):
        if (
            type(contract_job) is not dict
            or contract_job.get("repair_job_id") != legacy_plan["repair_job_id"]
            or contract_job.get("document_ordinal") != legacy_plan["document_ordinal"]
            or contract_job.get("physical_page") != legacy_plan["physical_page"]
        ):
            raise _error("quarantined legacy job axis differs from its plans")
        artifacts = contract_job.get("artifacts")
        if type(artifacts) is not dict or set(artifacts) != expected_static_artifact_names:
            raise _error("quarantined legacy static job artifact axis drifted")
        for reference in artifacts.values():
            _authenticated_artifact_ref(sealed_output, reference)
        stored_plan = _json_artifact(
            sealed_output,
            artifacts["plan.json"],
            label="quarantined legacy job plan",
        )
        if stored_plan != legacy_plan:
            raise _error("quarantined legacy static job plan differs")
        prompt_path = _authenticated_artifact_ref(sealed_output, artifacts["prompt.txt"])
        schema = _json_artifact(
            sealed_output,
            artifacts["response-schema.json"],
            label="quarantined legacy response schema",
        )
        if (
            sha256(prompt_path.read_bytes()).hexdigest()
            != legacy_plan["request_contract"]["prompt_sha256"]
            or canonical_json_sha256_v1(schema)
            != legacy_plan["request_contract"]["response_schema_sha256"]
        ):
            raise _error("quarantined legacy prompt/schema differs from its request contract")
        semantic = canonical_json_sha256_v1(_legacy_plan_semantic_projection(legacy_plan))
        new_job = new_by_semantic[semantic]
        if (
            artifacts["source-image.png"]["sha256"] != sha256(new_job.source_image).hexdigest()
            or artifacts["crop-image.png"]["sha256"] != sha256(new_job.crop_image).hexdigest()
        ):
            raise _error("quarantined legacy source/crop pixels differ from current replay")
        old_job_to_new[legacy_plan["repair_job_id"]] = new_job
        legacy_static_artifacts_by_job[legacy_plan["repair_job_id"]] = artifacts

    axis = _json_artifact(
        sealed_output,
        sealed_result.get("attempt_artifact_axis"),
        label="quarantined legacy attempt artifact axis",
    )
    if (
        type(axis) is not dict
        or axis.get("format_version") != ATTEMPT_ARTIFACT_AXIS_FORMAT_VERSION
        or axis.get("manifest_axis_sha256") != canonical_json_sha256_v1(axis.get("manifests"))
        or sealed_result["attempt_artifact_axis"]["sha256"]
        != sha256((sealed_output / "attempt-artifact-axis.json").read_bytes()).hexdigest()
    ):
        raise _error("quarantined legacy attempt axis identity drifted")
    checkpoint = _validate_capture_checkpoint(
        sealed_output,
        _json_artifact(
            sealed_output,
            sealed_result.get("capture_checkpoint"),
            label="quarantined legacy terminal checkpoint",
        ),
    )
    if (
        checkpoint["run_contract_sha256"] != sealed_result["run_contract_sha256"]
        or sorted(checkpoint["attempt_artifact_manifests"], key=lambda item: item["attempt_id"])
        != sorted(axis["manifests"], key=lambda item: item["attempt_id"])
        or checkpoint["checkpoint_ordinal"] != len(axis["manifests"])
        or {state["next_status"] for state in checkpoint["job_states"]} != {"ABSTAINED", "RESOLVED"}
        or {
            status: sum(state["next_status"] == status for state in checkpoint["job_states"])
            for status in ("ABSTAINED", "RESOLVED")
        }
        != sealed_result["job_status_counts"]
    ):
        raise _error("quarantined legacy checkpoint does not prove the mixed-status contradiction")
    plan_by_old_id = {plan["repair_job_id"]: plan for plan in legacy_plans}
    attempts_by_old_job: dict[str, list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]] = {
        job_id: [] for job_id in plan_by_old_id
    }
    for entry in axis["manifests"]:
        manifest = _validate_attempt_artifact_manifest(
            sealed_output,
            _json_artifact(
                sealed_output,
                entry["attempt_artifact_manifest_ref"],
                label="quarantined legacy attempt manifest",
            ),
        )
        if (
            entry["manifest_sha256"] != manifest["manifest_sha256"]
            or entry["repair_job_id"] not in plan_by_old_id
        ):
            raise _error("quarantined legacy manifest axis differs from its content")
        attempt = _validate_quarantined_legacy_attempt(
            sealed_output,
            entry=entry,
            manifest=manifest,
            legacy_plan=plan_by_old_id[entry["repair_job_id"]],
        )
        attempts_by_old_job[entry["repair_job_id"]].append((attempt, manifest, dict(entry)))
    selected = []
    for old_job_id, old_attempts in attempts_by_old_job.items():
        old_attempts.sort(key=lambda item: item[0]["attempt_ordinal"])
        state = next(
            item for item in checkpoint["job_states"] if item["repair_job_id"] == old_job_id
        )
        if (
            [item[0]["attempt_ordinal"] for item in old_attempts]
            != list(range(1, len(old_attempts) + 1))
            or len(old_attempts) != state["attempt_count"]
            or old_attempts[-1][0]["next_status"] != state["next_status"]
        ):
            raise _error("quarantined legacy per-job attempt frontier is incoherent")
        new_job = old_job_to_new[old_job_id]
        chosen = None
        rejection_hashes = []
        for attempt, manifest, entry in old_attempts:
            artifacts = manifest["artifacts"]
            if not {
                "provider-attempts.json",
                "provider-envelope.bin",
                "provider-result.json",
                "request.json",
                "table-response.json",
            } <= set(artifacts):
                continue
            provider_result = _provider_result_from_sealed_artifacts(sealed_output, artifacts)
            request = _json_artifact(
                sealed_output,
                artifacts["request.json"],
                label="quarantined legacy provider request",
            )
            legacy_plan = plan_by_old_id[old_job_id]
            expected_request_fields = {
                "allow_fallbacks",
                "crop_image_sha256",
                "execution_policy",
                "output_contract_mode",
                "prompt_sha256",
                "repair_job_id",
                "request_id_sha256",
                "requested_model",
                "requested_provider",
                "response_schema_sha256",
                "service_tier",
                "thinking_level",
            }
            request_material = (
                {key: request[key] for key in request if key != "request_id_sha256"}
                if type(request) is dict
                else {}
            )
            if (
                type(request) is not dict
                or set(request) != expected_request_fields
                or request.get("request_id_sha256") != canonical_json_sha256_v1(request_material)
                or request.get("repair_job_id") != old_job_id
                or request.get("thinking_level") != attempt["thinking_level"]
                or request.get("crop_image_sha256")
                != legacy_static_artifacts_by_job[old_job_id]["crop-image.png"]["sha256"]
                or request.get("allow_fallbacks") is not False
                or request.get("execution_policy") != "OPENROUTER_PILOT"
                or request.get("output_contract_mode") != "JSON_SCHEMA"
                or request.get("requested_model") != OPENROUTER_MODEL
                or request.get("requested_provider") != OPENROUTER_PROVIDER
                or request.get("service_tier") != OPENROUTER_SERVICE_TIER
                or request.get("prompt_sha256") != legacy_plan["request_contract"]["prompt_sha256"]
                or request.get("response_schema_sha256")
                != legacy_plan["request_contract"]["response_schema_sha256"]
                or request.get("request_id_sha256") != attempt["provider"]["request_id_sha256"]
                or provider_result.provider_model != attempt["provider"]["provider_model"]
                or provider_result.response_id_sha256 != attempt["provider"]["response_id_sha256"]
                or provider_result.service_tier != attempt["provider"]["service_tier"]
                or provider_result.provider_name.casefold() != "google"
                or attempt["provider"].get("provider_name") != "openrouter"
                or _repair_usage(provider_result) != attempt["usage"]
            ):
                raise _error("quarantined legacy provider request/result lineage drifted")
            response_bytes = _authenticated_artifact_ref(
                sealed_output, artifacts["table-response.json"]
            ).read_bytes()
            try:
                decoded = decode_rollforward_table_repair_text_v1(
                    response_bytes.decode("utf-8"), target=new_job.target
                )
                merge_rollforward_table_repair_v1(
                    new_job.base_page_json,
                    plan=new_job.plan,
                    repair=decoded,
                    page_store_path=page_store_path,
                    authority=prepared.authority,
                    repair_spec_authority=prepared.repair_spec_authority,
                    _prevalidated_plan_axis=prepared.plans,
                )
            except (UnicodeDecodeError, GeminiJsonRollforwardTableRepairV1Error):
                rejection_hashes.append(artifacts["table-response.json"]["sha256"])
                continue
            chosen = {
                "artifacts": artifacts,
                "legacy_attempt": attempt,
                "legacy_entry": entry,
                "legacy_manifest": manifest,
                "legacy_static_artifacts": legacy_static_artifacts_by_job[old_job_id],
                "new_job": new_job,
                "rejected_earlier_response_sha256": rejection_hashes,
            }
            break
        if chosen is None:
            raise _error("quarantined legacy job has no projection-valid sealed response")
        selected.append(chosen)
    selected.sort(key=lambda item: item["new_job"].ordinal)
    authority_material = {
        "deterministic_projection_schema_sha256": canonical_json_sha256_v1(
            _deterministic_projection_schema_v1()
        ),
        "format_version": "GEMINI_JSON_ROLLFORWARD_LEGACY_REVALIDATION_AUTHORITY_V1",
        "legacy_attempt_axis_sha256": sealed_result["attempt_artifact_axis"]["sha256"],
        "legacy_capture_checkpoint_sha256": sealed_result["capture_checkpoint"]["sha256"],
        "legacy_job_status_counts": sealed_result["job_status_counts"],
        "legacy_run_contract_sha256": sealed_result["run_contract_sha256"],
        "legacy_run_result_sha256": sha256(
            (sealed_output / "run-result.json").read_bytes()
        ).hexdigest(),
        "legacy_runner_implementation_ref": legacy_runner_ref,
        "plan_semantic_mapping": [
            {
                "legacy_repair_job_id": item["legacy_attempt"]["repair_job_id"],
                "minimal_repair_job_id": item["new_job"].plan["repair_job_id"],
                "semantic_sha256": canonical_json_sha256_v1(
                    _legacy_plan_semantic_projection(item["new_job"].plan)
                ),
                "selected_legacy_attempt_id": item["legacy_attempt"]["attempt_id"],
                "selected_legacy_attempt_ordinal": item["legacy_attempt"]["attempt_ordinal"],
                "selected_legacy_prompt_sha256": item["legacy_static_artifacts"]["prompt.txt"][
                    "sha256"
                ],
                "selected_legacy_response_schema_artifact_sha256": item["legacy_static_artifacts"][
                    "response-schema.json"
                ]["sha256"],
                "selected_response_sha256": item["artifacts"]["table-response.json"]["sha256"],
            }
            for item in selected
        ],
        "provider_call_count": 0,
        "projector_implementation_ref": prepared.projector_implementation_ref,
        "quarantine_reason": "FALSE_COMPLETE_WITH_MIXED_RESOLVED_AND_ABSTAINED_JOBS",
    }
    return selected, {
        **authority_material,
        "authority_sha256": canonical_json_sha256_v1(authority_material),
    }


def _execute_quarantined_legacy_revalidation_v1(
    *,
    sealed_output: Path,
    selected: Sequence[Mapping[str, Any]],
    source_authority: Mapping[str, Any],
    prepared: _PreparedRun,
    replay_artifact_dir: Path,
    effective_artifact_root: Path,
    writable_store: Path,
    writable_results: Path,
    source_sha: str,
    source_size: int,
    source_results_sha: str,
    source_results_size: int,
) -> dict[str, Any]:
    output = _claim_output(replay_artifact_dir)
    source_authority_payload = canonical_json_bytes_v1(dict(source_authority)) + b"\n"
    source_authority_path = output / "authority" / "legacy-revalidation-authority.json"
    _write_new(source_authority_path, source_authority_payload)
    source_authority_ref = _ref(output, source_authority_path, source_authority_payload)
    contract, source_artifacts, crop_artifacts = _write_static_artifacts(
        output,
        prepared,
        mode="SEALED_RESPONSE_REVALIDATION",
        source_store_sha256=source_sha,
        source_store_size_bytes=source_size,
        source_results_database_sha256=source_results_sha,
        source_results_database_size_bytes=source_results_size,
        effective_artifact_root=effective_artifact_root,
        contract_extensions={
            "legacy_revalidation_authority": source_authority_ref,
            "provider_call_count": 0,
        },
    )
    contract_sha = sha256((output / "run-contract.json").read_bytes()).hexdigest()
    initialize_region_repair_extension_v1(writable_store)
    enqueued = enqueue_gemini_family_region_repair_plans_v1(
        writable_results,
        family_run_id=prepared.config["repair_source_family_run_id"],
        plans=prepared.plans,
    )
    if enqueued != [plan["repair_job_id"] for plan in prepared.plans]:
        raise _error("legacy revalidation queue does not preserve the minimal plan axis")
    derived_records = []
    derived_record_refs = []
    replacements = []
    for selected_item in selected:
        job = selected_item["new_job"]
        legacy_attempt = selected_item["legacy_attempt"]
        legacy_manifest = selected_item["legacy_manifest"]
        response_ref = selected_item["artifacts"]["table-response.json"]
        response_bytes = _authenticated_artifact_ref(sealed_output, response_ref).read_bytes()
        try:
            decoded = decode_rollforward_table_repair_text_v1(
                response_bytes.decode("utf-8"), target=job.target
            )
        except UnicodeDecodeError as exc:
            raise _error("selected quarantined legacy response is not UTF-8") from exc
        merged, receipt = merge_rollforward_table_repair_v1(
            job.base_page_json,
            plan=job.plan,
            repair=decoded,
            page_store_path=writable_store,
            authority=prepared.authority,
            repair_spec_authority=prepared.repair_spec_authority,
            _prevalidated_plan_axis=prepared.plans,
        )
        source_link = {
            "deterministic_projection_contract_version": (
                DETERMINISTIC_PROJECTION_CONTRACT_VERSION
            ),
            "deterministic_projection_schema_sha256": canonical_json_sha256_v1(
                _deterministic_projection_schema_v1()
            ),
            "format_version": "GEMINI_JSON_ROLLFORWARD_DERIVED_REVALIDATION_SOURCE_V1",
            "legacy_attempt_id": legacy_attempt["attempt_id"],
            "legacy_attempt_ordinal": legacy_attempt["attempt_ordinal"],
            "legacy_manifest_sha256": legacy_manifest["manifest_sha256"],
            "legacy_provider": legacy_attempt["provider"],
            "legacy_provider_artifact_refs": {
                name: selected_item["artifacts"][name]
                for name in (
                    "provider-attempts.json",
                    "provider-envelope.bin",
                    "provider-result.json",
                    "request.json",
                    "table-response.json",
                )
            },
            "legacy_repair_job_id": legacy_attempt["repair_job_id"],
            "legacy_request_contract_sha256": legacy_attempt["request_contract_sha256"],
            "legacy_response_ref": response_ref,
            "legacy_static_request_artifact_refs": {
                name: selected_item["legacy_static_artifacts"][name]
                for name in ("prompt.txt", "response-schema.json")
            },
            "legacy_thinking_level": legacy_attempt["thinking_level"],
            "legacy_usage": legacy_attempt["usage"],
            "legacy_revalidation_authority_sha256": source_authority["authority_sha256"],
            "minimal_repair_job_id": job.plan["repair_job_id"],
            "minimal_response_projection_sha256": decoded["projection_sha256"],
            "provider_call_count": 0,
            "projector_implementation_ref": prepared.projector_implementation_ref,
            "rejected_earlier_response_sha256": selected_item["rejected_earlier_response_sha256"],
            "usage_reaccounted": False,
        }
        derived_envelope = canonical_json_bytes_v1(
            {
                "base_page_json_version_id": job.plan["base_page_json_version_id"],
                "merged_page_json_sha256": canonical_json_sha256_v1(merged),
                "repair_id": receipt["repair_id"],
                "source": source_link,
            }
        )
        derived_provider_result = ProviderResultV1(
            output_text=canonical_json_bytes_v1(decoded).decode("utf-8"),
            raw_response_bytes=derived_envelope + b"\n",
            provider_name="SEALED_RESPONSE_REVALIDATION",
            provider_model="algorithm/rollforward-target-observation-projector-v1",
            service_tier="offline",
            attempts=(),
            usage={
                "actual_cost_usd": "0",
                "billing_disposition": "NO_PROVIDER_CALL_SEALED_REVALIDATION",
                "cached_input_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "thought_tokens": 0,
                "total_tokens": 0,
            },
            response_id_sha256=sha256(derived_envelope).hexdigest(),
        )
        binding = job.plan["source_binding"]
        identities = ingest_financial_page_extraction_v1(
            writable_store,
            document={
                "source_logical_name": binding["source_logical_name"],
                "source_sha256": binding["source_sha256"],
                "source_size_bytes": binding["source_size_bytes"],
            },
            page={
                "physical_page": binding["physical_page"],
                "image_sha256": binding["image_sha256"],
                "image_size_bytes": binding["image_size_bytes"],
                "pixel_width": binding["pixel_width"],
                "pixel_height": binding["pixel_height"],
                "render_dpi": binding["render_dpi"],
                "media_type": binding["media_type"],
            },
            prompt_variant="sealed-legacy-target-observation-revalidation",
            output_contract_mode="DETERMINISTIC_PROJECTION",
            prompt_sha256=canonical_json_sha256_v1(
                {
                    "legacy_revalidation_authority_sha256": source_authority["authority_sha256"],
                    "minimal_repair_job_id": job.plan["repair_job_id"],
                    "projection_sha256": decoded["projection_sha256"],
                }
            ),
            response_schema_sha256=canonical_json_sha256_v1(_deterministic_projection_schema_v1()),
            requested_model="algorithm/rollforward-target-observation-projector-v1",
            requested_service_tier="offline",
            thinking_level="deterministic",
            provider_result=derived_provider_result,
            page_json=merged,
        )
        lineage = record_page_json_region_repair_v1(
            writable_store,
            merged_page_json_version_id=identities["page_json_version_id"],
            receipt=receipt,
        )
        standard_attempt = record_gemini_family_region_repair_attempt_v1(
            writable_results,
            repair_job_id=job.plan["repair_job_id"],
            thinking_level="low",
            outcome="STABLE_SOURCE_EVIDENCE",
            page_json_version_id=lineage["observed_page_json_version_id"],
            usage=None,
            reasons=["AUTHENTICATED_SEALED_RESPONSE_REVALIDATED_WITHOUT_PROVIDER_CALL"],
        )
        if standard_attempt != {
            "attempt_ordinal": 1,
            "next_status": "RESOLVED",
            "outcome": "STABLE_SOURCE_EVIDENCE",
            "repair_job_id": job.plan["repair_job_id"],
            "thinking_level": "low",
        }:
            raise _error("legacy revalidation stable-evidence queue transition drifted")
        record_material = {
            "format_version": "GEMINI_JSON_ROLLFORWARD_DERIVED_REVALIDATION_RECORD_V1",
            "identities": identities,
            "lineage": lineage,
            "receipt": receipt,
            "source": source_link,
            "standard_attempt": standard_attempt,
        }
        record = {
            **record_material,
            "record_sha256": canonical_json_sha256_v1(record_material),
        }
        record_payload = canonical_json_bytes_v1(record) + b"\n"
        record_path = output / "derived-revalidations" / f"job-{job.ordinal:03d}.json"
        _write_new(record_path, record_payload)
        derived_records.append(record)
        derived_record_refs.append(_ref(output, record_path, record_payload))
        replacements.append(
            {
                "base_page_json_version_id": job.plan["base_page_json_version_id"],
                "candidate_id": job.plan["candidate_id"],
                "document_ordinal": job.plan["document_ordinal"],
                "physical_page": job.plan["physical_page"],
                "repair_id": receipt["repair_id"],
                "repair_job_id": job.plan["repair_job_id"],
                "repair_receipt_sha256": lineage["repair_receipt_sha256"],
                "selected_page_json_version_id": lineage["observed_page_json_version_id"],
            }
        )
    expected_counts = {"ABSTAINED": 0, "RESOLVED": len(prepared.jobs)}
    if len(replacements) != len(prepared.jobs) or {
        item["repair_job_id"] for item in replacements
    } != {job.plan["repair_job_id"] for job in prepared.jobs}:
        raise _error("legacy revalidation is not one resolved replacement per planned job")
    derived_axis_material = {
        "format_version": "GEMINI_JSON_ROLLFORWARD_DERIVED_REVALIDATION_AXIS_V1",
        "record_refs": derived_record_refs,
        "record_sha256_axis": [record["record_sha256"] for record in derived_records],
    }
    derived_axis = {
        **derived_axis_material,
        "axis_sha256": canonical_json_sha256_v1(derived_axis_material),
    }
    derived_axis_payload = canonical_json_bytes_v1(derived_axis) + b"\n"
    derived_axis_path = output / "derived-revalidation-axis.json"
    _write_new(derived_axis_path, derived_axis_payload)
    derived_axis_ref = _ref(output, derived_axis_path, derived_axis_payload)
    overlay_material = {
        "derived_revalidation_axis_sha256": derived_axis["axis_sha256"],
        "family_id": prepared.plans[0]["family_id"],
        "format_version": "GEMINI_JSON_ROLLFORWARD_TABLE_REVALIDATION_OVERLAY_V1",
        "job_status_counts": expected_counts,
        "provider_call_count": 0,
        "repair_source_family_run_id": prepared.config["repair_source_family_run_id"],
        "repair_spec_authority": prepared.repair_spec_authority,
        "replacements": replacements,
    }
    overlay = {
        **overlay_material,
        "overlay_id": "gjfrtrov1:overlay:" + canonical_json_sha256_v1(overlay_material),
    }
    standard_overlay = resolved_gemini_family_region_repair_overlay_v1(
        writable_results,
        family_run_id=prepared.config["repair_source_family_run_id"],
    )
    expected_standard = [
        {
            key: replacement[key]
            for key in (
                "base_page_json_version_id",
                "candidate_id",
                "document_ordinal",
                "physical_page",
                "repair_job_id",
                "selected_page_json_version_id",
            )
        }
        for replacement in overlay["replacements"]
    ]
    if (
        standard_overlay.get("job_status_counts") != expected_counts
        or standard_overlay.get("replacements") != expected_standard
    ):
        raise _error("legacy revalidation standard/audited overlays differ")
    overlay_payload = canonical_json_bytes_v1(overlay) + b"\n"
    overlay_path = output / "repair-overlay.json"
    _write_new(overlay_path, overlay_payload)
    overlay_ref = _ref(output, overlay_path, overlay_payload)
    _reject_sqlite_sidecars(writable_store, label="legacy revalidation page work database")
    _reject_sqlite_sidecars(writable_results, label="legacy revalidation results work database")
    writable_sha, writable_size = _sha_file(writable_store)
    writable_results_sha, writable_results_size = _sha_file(writable_results)
    frontier = build_gemini_family_effective_page_frontier_v1(
        base_corpus_manifest_index_id=prepared.config["base_corpus_manifest_index_id"],
        base_page_json_version_ids=prepared.selected_ids,
        database_ref={
            "path": prepared.config["writable_page_store_ref_path"],
            "sha256": writable_sha,
            "size_bytes": writable_size,
        },
        family_id=overlay["family_id"],
        job_status_counts=overlay["job_status_counts"],
        repair_source_family_run_id=prepared.config["repair_source_family_run_id"],
        replacements=overlay["replacements"],
        results_database_ref={
            "path": prepared.config["writable_results_database_ref_path"],
            "sha256": writable_results_sha,
            "size_bytes": writable_results_size,
        },
    )
    checked_frontier, effective_ids = apply_gemini_family_effective_page_frontier_v1(
        frontier,
        base_page_json_version_ids=prepared.selected_ids,
    )
    if checked_frontier != frontier or len(effective_ids) != len(prepared.selected_ids):
        raise _error("legacy revalidation effective frontier does not replay")
    frontier_payload = canonical_json_bytes_v1(frontier) + b"\n"
    frontier_path = output / "effective-page-frontier.json"
    _write_new(frontier_path, frontier_payload)
    frontier_ref = _ref(output, frontier_path, frontier_payload)
    return {
        "derived_revalidation_axis": derived_axis_ref,
        "derived_revalidation_records": derived_record_refs,
        "disposition": "REPAIR_FRONTIER_RECOVERED",
        "effective_page_frontier": frontier_ref,
        "effective_page_frontier_id": frontier["effective_page_frontier_id"],
        "format_version": FORMAT_VERSION,
        "job_count": len(prepared.jobs),
        "job_status_counts": expected_counts,
        "legacy_revalidation_authority": source_authority_ref,
        "official_selection": "NOT_PERFORMED",
        "overlay_id": overlay["overlay_id"],
        "provider_call_count": 0,
        "repair_overlay": overlay_ref,
        "run_contract_sha256": contract_sha,
        "writable_page_store": {"sha256": writable_sha, "size_bytes": writable_size},
        "writable_results_database": {
            "sha256": writable_results_sha,
            "size_bytes": writable_results_size,
        },
    }


def _replay_sealed_rollforward_table_repair_on_private_sqlite_v1(
    *,
    family_sweep_path: Path,
    family_sweep_sha256: str,
    selected_page_ids_path: Path,
    selected_page_ids_sha256: str,
    source_page_store: Path,
    source_page_store_sha256: str,
    source_results_database: Path,
    source_results_database_sha256: str,
    repair_spec_config_path: Path,
    repair_spec_config_sha256: str,
    workspace_root: Path,
    runner_implementation_sha256: str,
    artifact_root: Path,
    sealed_artifact_dir: Path,
    sealed_run_result_sha256: str,
    replay_artifact_dir: Path,
    writable_page_store: Path,
    writable_results_database: Path,
    writable_page_store_ref_identity: tuple[int, int] | None = None,
    writable_results_database_ref_identity: tuple[int, int] | None = None,
) -> dict[str, Any]:
    """Replay sealed provider observations onto fresh DB copies without a provider call."""

    source_store, source_sha, source_size = _validate_source_store(
        source_page_store,
        source_page_store_sha256,
    )
    source_results, source_results_sha, source_results_size = _validate_pinned_binary(
        source_results_database,
        source_results_database_sha256,
        label="frozen source family-results database",
    )
    effective_artifact_root = _validate_artifact_root(artifact_root)
    writable_store = _validate_writable_copy(
        source_store,
        writable_page_store,
        source_sha,
        label="fresh replay page-store copy",
    )
    writable_results = _validate_writable_copy(
        source_results,
        writable_results_database,
        source_results_sha,
        label="fresh replay family-results database copy",
    )
    sweep = _read_pinned_json(
        family_sweep_path,
        family_sweep_sha256,
        label="base family sweep",
    )
    selected = _read_pinned_json(
        selected_page_ids_path,
        selected_page_ids_sha256,
        label="selected page JSON version IDs",
    )
    repair_config = _read_pinned_json(
        repair_spec_config_path,
        repair_spec_config_sha256,
        label="external repair-spec config",
    )
    prepared = _prepare(
        sweep=sweep,
        selected=selected,
        repair_config=repair_config,
        source_page_store=source_store,
        source_results_database=source_results,
        workspace_root=workspace_root,
        runner_implementation_sha256=runner_implementation_sha256,
    )
    _bind_effective_frontier_database_ref(
        effective_artifact_root,
        prepared.config["writable_page_store_ref_path"],
        writable_store,
        label="effective-frontier replay page database",
        expected_identity=writable_page_store_ref_identity,
    )
    _bind_effective_frontier_database_ref(
        effective_artifact_root,
        prepared.config["writable_results_database_ref_path"],
        writable_results,
        label="effective-frontier replay results database",
        expected_identity=writable_results_database_ref_identity,
    )
    sealed_input = Path(sealed_artifact_dir)
    sealed_output = sealed_input.resolve()
    if sealed_input.is_symlink() or not sealed_output.is_dir():
        raise _error("sealed incomplete artifact directory is absent or a symlink")
    sealed_result = _read_pinned_json(
        sealed_output / "run-result.json",
        sealed_run_result_sha256,
        label="sealed incomplete run result",
    ).value
    standard_incomplete = (
        type(sealed_result) is dict
        and sealed_result.get("disposition") == "REPAIR_FRONTIER_INCOMPLETE"
        and sealed_result.get("provider_recall") == "FORBIDDEN"
    )
    quarantined_legacy = (
        type(sealed_result) is dict
        and sealed_result.get("disposition") == "REPAIR_FRONTIER_COMPLETE"
        and sealed_result.get("job_status_counts") == {"ABSTAINED": 3, "RESOLVED": 3}
    )
    if not standard_incomplete and not quarantined_legacy:
        raise _error("sealed replay source is neither incomplete nor the quarantined legacy root")
    contract_path = _regular_file(
        sealed_output / "run-contract.json",
        label="sealed run contract",
    )
    contract_raw = contract_path.read_bytes()
    if sha256(contract_raw).hexdigest() != sealed_result.get("run_contract_sha256"):
        raise _error("sealed run contract does not match the incomplete result")
    try:
        contract = json.loads(contract_raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("sealed run contract is invalid JSON") from exc
    if quarantined_legacy:
        selected_legacy, legacy_authority = _validate_quarantined_legacy_source_v1(
            sealed_output=sealed_output,
            sealed_result=sealed_result,
            contract=contract,
            prepared=prepared,
            source_sha=source_sha,
            source_size=source_size,
            source_results_sha=source_results_sha,
            source_results_size=source_results_size,
            page_store_path=writable_store,
        )
        return _execute_quarantined_legacy_revalidation_v1(
            sealed_output=sealed_output,
            selected=selected_legacy,
            source_authority=legacy_authority,
            prepared=prepared,
            replay_artifact_dir=replay_artifact_dir,
            effective_artifact_root=effective_artifact_root,
            writable_store=writable_store,
            writable_results=writable_results,
            source_sha=source_sha,
            source_size=source_size,
            source_results_sha=source_results_sha,
            source_results_size=source_results_size,
        )
    if (
        contract.get("format_version") != FORMAT_VERSION
        or contract.get("mode") != "OPENROUTER_BOUNDED"
        or contract.get("plan_axis_sha256") != canonical_json_sha256_v1(prepared.plans)
        or contract.get("runner_implementation_ref") != prepared.runner_implementation_ref
        or contract.get("projector_implementation_ref") != prepared.projector_implementation_ref
        or contract.get("deterministic_projection_schema_sha256")
        != canonical_json_sha256_v1(_deterministic_projection_schema_v1())
        or contract.get("source_page_store") != {"sha256": source_sha, "size_bytes": source_size}
        or contract.get("source_family_results_database")
        != {"sha256": source_results_sha, "size_bytes": source_results_size}
    ):
        raise _error("sealed run contract differs from the authoritative replay")
    static_refs = [*contract["authority_artifacts"].values(), *contract["input_artifacts"].values()]
    for job_ref in contract["jobs"]:
        static_refs.extend(job_ref["artifacts"].values())
    for reference in static_refs:
        _authenticated_artifact_ref(sealed_output, reference)
    axis_ref = sealed_result.get("attempt_artifact_axis")
    axis = _json_artifact(
        sealed_output,
        axis_ref,
        label="sealed attempt artifact axis",
    )
    if (
        type(axis) is not dict
        or axis.get("format_version") != ATTEMPT_ARTIFACT_AXIS_FORMAT_VERSION
        or type(axis.get("manifests")) is not list
        or axis.get("manifest_axis_sha256") != canonical_json_sha256_v1(axis.get("manifests"))
    ):
        raise _error("sealed attempt artifact axis identity drifted")
    checkpoint = _validate_capture_checkpoint(
        sealed_output,
        _json_artifact(
            sealed_output,
            sealed_result.get("capture_checkpoint"),
            label="terminal capture checkpoint",
        ),
    )
    if (
        checkpoint["run_contract_sha256"] != sealed_result["run_contract_sha256"]
        or sorted(
            checkpoint["attempt_artifact_manifests"],
            key=lambda item: item["attempt_id"],
        )
        != sorted(axis["manifests"], key=lambda item: item["attempt_id"])
        or any(
            state["next_status"] not in {"RESOLVED", "ABSTAINED"}
            for state in checkpoint["job_states"]
        )
    ):
        raise _error("terminal capture checkpoint differs from sealed attempt axis")
    attempt_records: dict[tuple[str, int], tuple[dict[str, Any], dict[str, Any]]] = {}
    for entry in axis["manifests"]:
        manifest = _json_artifact(
            sealed_output,
            entry["attempt_artifact_manifest_ref"],
            label="sealed attempt artifact manifest",
        )
        checked_manifest = _validate_attempt_artifact_manifest(sealed_output, manifest)
        if (
            entry["manifest_sha256"] != checked_manifest["manifest_sha256"]
            or entry["attempt_id"] != checked_manifest["attempt_id"]
            or entry["repair_job_id"] != checked_manifest["repair_job_id"]
        ):
            raise _error("sealed attempt manifest axis differs from its content")
        attempt = _json_artifact(
            sealed_output,
            checked_manifest["artifacts"]["attempt.json"],
            label="sealed repair attempt",
        )
        key = (attempt["repair_job_id"], attempt["attempt_ordinal"])
        if (
            key in attempt_records
            or attempt["attempt_id"] != entry["attempt_id"]
            or attempt["thinking_level"] != entry["thinking_level"]
        ):
            raise _error("sealed repair attempt axis is duplicate or inconsistent")
        attempt_records[key] = (attempt, checked_manifest["artifacts"])
    journals: dict[tuple[str, int], dict[str, Any]] = {}
    for reference in sealed_result.get("recovery_journals", []):
        journal = _validate_pre_db_apply_journal(
            sealed_output,
            _json_artifact(
                sealed_output,
                reference,
                label="sealed pre-database apply journal",
            ),
        )
        key = (journal["repair_job_id"], journal["attempt_ordinal"])
        if key in journals:
            raise _error("sealed pre-database apply journal axis is duplicate")
        journals[key] = journal
    if not attempt_records and not journals:
        raise _error("sealed incomplete run contains no replayable observation")
    output = _claim_output(replay_artifact_dir)
    initialize_region_repair_extension_v1(writable_store)
    enqueued = enqueue_gemini_family_region_repair_plans_v1(
        writable_results,
        family_run_id=prepared.config["repair_source_family_run_id"],
        plans=prepared.plans,
    )
    if enqueued != [plan["repair_job_id"] for plan in prepared.plans]:
        raise _error("replay results queue does not preserve the authoritative plan axis")
    jobs = {job.plan["repair_job_id"]: job for job in prepared.jobs}
    job_order = {job.plan["repair_job_id"]: job.ordinal for job in prepared.jobs}
    attempts_by_job: dict[str, list[dict[str, Any]]] = {job_id: [] for job_id in jobs}
    response_artifacts: dict[str, bytes] = {}
    replayed_attempt_refs = []
    keys = sorted(
        set(attempt_records) | set(journals),
        key=lambda item: (job_order.get(item[0], 10**9), item[1]),
    )
    for key in keys:
        job_id, attempt_ordinal = key
        job = jobs.get(job_id)
        standard_page_override = None
        if job is None:
            raise _error("sealed observation names a job outside the authoritative axis")
        if key in attempt_records:
            attempt, artifacts = attempt_records[key]
            if attempt["repair_id"] is not None and attempt["outcome"] in {
                "RESOLVED",
                "VALIDATED_OBSERVATION_PENDING_CONSENSUS",
            }:
                _result, receipt, lineage, response_bytes = _apply_sealed_resolved_observation(
                    sealed_output=sealed_output,
                    artifacts=artifacts,
                    prepared=prepared,
                    job=job,
                    writable_page_store=writable_store,
                )
                if (
                    attempt["observed_page_json_version_id"]
                    != lineage["observed_page_json_version_id"]
                    or attempt["repair_receipt_sha256"]
                    != sha256(canonical_json_bytes_v1(receipt) + b"\n").hexdigest()
                ):
                    raise _error("sealed correction attempt differs from fresh database replay")
                response_artifacts[sha256(response_bytes).hexdigest()] = response_bytes
                if attempt["outcome"] == "RESOLVED":
                    standard_page_override = lineage["merged_page_json_version_id"]
            elif attempt["repair_id"] is None and attempt["outcome"] in {
                "SOURCE_CORROBORATED_NO_CHANGE",
                "VALIDATED_OBSERVATION_PENDING_CONSENSUS",
            }:
                receipt, response_bytes = _replay_sealed_source_corroboration(
                    sealed_output=sealed_output,
                    artifacts=artifacts,
                    prepared=prepared,
                    job=job,
                    writable_page_store=writable_store,
                )
                if (
                    attempt["observed_page_json_version_id"]
                    != job.plan["base_page_json_version_id"]
                    or attempt["repair_receipt_sha256"]
                    != sha256(canonical_json_bytes_v1(receipt) + b"\n").hexdigest()
                ):
                    raise _error("sealed source no-change attempt differs from fresh replay")
                response_artifacts[sha256(response_bytes).hexdigest()] = response_bytes
            reference = attempt.get("response_artifact_ref")
            if reference is not None:
                response = _authenticated_artifact_ref(sealed_output, reference).read_bytes()
                response_artifacts[sha256(response).hexdigest()] = response
        else:
            journal = journals[key]
            artifacts = journal["artifacts"]
            _result, receipt, lineage, response_bytes = _apply_sealed_resolved_observation(
                sealed_output=sealed_output,
                artifacts=artifacts,
                prepared=prepared,
                job=job,
                writable_page_store=writable_store,
            )
            usage = _json_artifact(
                sealed_output,
                artifacts["usage.json"],
                label="sealed repair usage",
            )
            provider = _json_artifact(
                sealed_output,
                artifacts["provider.json"],
                label="sealed repair provider identity",
            )
            observation = _json_artifact(
                sealed_output,
                artifacts["observation.json"],
                label="sealed provider observation",
            )
            attempt = build_rollforward_table_repair_attempt_v1(
                plan=job.plan,
                authority=prepared.authority,
                repair_spec_authority=prepared.repair_spec_authority,
                page_store_path=writable_store,
                prior_attempts=attempts_by_job[job_id],
                thinking_level=journal["thinking_level"],
                outcome="RESOLVED",
                observed_page_json_version_id=lineage["observed_page_json_version_id"],
                repair_receipt=receipt,
                crop_receipt=job.crop_receipt,
                source_image_bytes=job.source_image,
                crop_image_bytes=job.crop_image,
                response_artifact_ref=artifacts["table-response.json"],
                raw_response_bytes=response_bytes,
                validation={"reason_codes": [], "status": "PASS"},
                usage=usage,
                provider=provider,
                elapsed_seconds=observation["elapsed_seconds"],
                _prevalidated_plan_axis=prepared.plans,
            )
            recovered_path = (
                output
                / "recovered-attempts"
                / f"job-{job.ordinal:03d}"
                / (f"attempt-{attempt_ordinal:02d}.json")
            )
            recovered_payload = canonical_json_bytes_v1(attempt) + b"\n"
            _write_new(recovered_path, recovered_payload)
            replayed_attempt_refs.append(_ref(output, recovered_path, recovered_payload))
            response_artifacts[sha256(response_bytes).hexdigest()] = response_bytes
        if attempt["attempt_ordinal"] != len(attempts_by_job[job_id]) + 1:
            raise _error("sealed replay attempt ordinal is noncontiguous")
        _mirror_family_attempt(
            writable_results,
            attempt,
            page_json_version_id_override=standard_page_override,
        )
        attempts_by_job[job_id].append(attempt)
    attempts = [
        attempt for job in prepared.jobs for attempt in attempts_by_job[job.plan["repair_job_id"]]
    ]
    overlay = build_rollforward_table_repair_overlay_v1(
        family_run_id=prepared.config["repair_source_family_run_id"],
        plans=prepared.plans,
        attempts=attempts,
        page_store_path=writable_store,
        authority=prepared.authority,
        repair_spec_authority=prepared.repair_spec_authority,
        source_image_artifacts_by_sha256={
            sha256(job.source_image).hexdigest(): job.source_image for job in prepared.jobs
        },
        crop_image_artifacts_by_sha256={
            sha256(job.crop_image).hexdigest(): job.crop_image for job in prepared.jobs
        },
        response_artifacts_by_sha256=response_artifacts,
    )
    standard_overlay = resolved_gemini_family_region_repair_overlay_v1(
        writable_results,
        family_run_id=prepared.config["repair_source_family_run_id"],
    )
    expected_replacements = [
        {
            key: replacement[key]
            for key in (
                "base_page_json_version_id",
                "candidate_id",
                "document_ordinal",
                "physical_page",
                "repair_job_id",
                "selected_page_json_version_id",
            )
        }
        for replacement in overlay["replacements"]
    ]
    expected_counts = {"ABSTAINED": 0, "RESOLVED": len(prepared.jobs)}
    replacement_job_ids = {
        attempts_by_job[job.plan["repair_job_id"]][-1]["repair_job_id"]
        for job in prepared.jobs
        if attempts_by_job[job.plan["repair_job_id"]][-1]["outcome"] == "RESOLVED"
    }
    source_no_change_job_ids = sorted(
        attempts_by_job[job.plan["repair_job_id"]][-1]["repair_job_id"]
        for job in prepared.jobs
        if attempts_by_job[job.plan["repair_job_id"]][-1]["outcome"]
        == "SOURCE_CORROBORATED_NO_CHANGE"
    )
    if (
        overlay.get("job_status_counts") != expected_counts
        or len(overlay.get("replacements", [])) != len(replacement_job_ids)
        or {item.get("repair_job_id") for item in overlay.get("replacements", [])}
        != replacement_job_ids
        or standard_overlay["job_status_counts"] != overlay["job_status_counts"]
        or standard_overlay["replacements"] != expected_replacements
        or standard_overlay["source_corroborated_no_change_job_ids"] != source_no_change_job_ids
    ):
        raise _error("fresh replay standard overlay differs from the audited overlay")
    _bind_effective_frontier_database_ref(
        effective_artifact_root,
        prepared.config["writable_page_store_ref_path"],
        writable_store,
        label="effective-frontier replay page database",
        expected_identity=writable_page_store_ref_identity,
    )
    _bind_effective_frontier_database_ref(
        effective_artifact_root,
        prepared.config["writable_results_database_ref_path"],
        writable_results,
        label="effective-frontier replay results database",
        expected_identity=writable_results_database_ref_identity,
    )
    _reject_sqlite_sidecars(writable_store, label="fresh replay page-store copy")
    _reject_sqlite_sidecars(
        writable_results,
        label="fresh replay family-results database copy",
    )
    writable_sha, writable_size = _sha_file(writable_store)
    writable_results_sha, writable_results_size = _sha_file(writable_results)
    frontier = build_gemini_family_effective_page_frontier_v1(
        base_corpus_manifest_index_id=prepared.config["base_corpus_manifest_index_id"],
        base_page_json_version_ids=prepared.selected_ids,
        database_ref={
            "path": prepared.config["writable_page_store_ref_path"],
            "sha256": writable_sha,
            "size_bytes": writable_size,
        },
        family_id=overlay["family_id"],
        job_status_counts=overlay["job_status_counts"],
        repair_source_family_run_id=prepared.config["repair_source_family_run_id"],
        replacements=overlay["replacements"],
        results_database_ref={
            "path": prepared.config["writable_results_database_ref_path"],
            "sha256": writable_results_sha,
            "size_bytes": writable_results_size,
        },
        source_corroborated_no_change_job_ids=source_no_change_job_ids,
    )
    checked_frontier, effective_ids = apply_gemini_family_effective_page_frontier_v1(
        frontier,
        base_page_json_version_ids=prepared.selected_ids,
    )
    if checked_frontier != frontier or len(effective_ids) != len(prepared.selected_ids):
        raise _error("fresh replay effective frontier does not replay exactly")
    overlay_payload = canonical_json_bytes_v1(overlay) + b"\n"
    overlay_path = output / "repair-overlay.json"
    _write_new(overlay_path, overlay_payload)
    frontier_payload = canonical_json_bytes_v1(frontier) + b"\n"
    frontier_path = output / "effective-page-frontier.json"
    _write_new(frontier_path, frontier_payload)
    result = {
        "disposition": "REPAIR_FRONTIER_RECOVERED",
        "effective_page_frontier_id": frontier["effective_page_frontier_id"],
        "format_version": FORMAT_VERSION,
        "job_count": len(prepared.jobs),
        "job_status_counts": overlay["job_status_counts"],
        "official_selection": "NOT_PERFORMED",
        "overlay_id": overlay["overlay_id"],
        "provider_call_count": 0,
        "recovered_attempt_artifacts": replayed_attempt_refs,
        "sealed_run_result_sha256": sealed_run_result_sha256,
        "writable_page_store": {"sha256": writable_sha, "size_bytes": writable_size},
        "writable_results_database": {
            "sha256": writable_results_sha,
            "size_bytes": writable_results_size,
        },
    }
    _assert_frozen_database_unchanged(
        source_store,
        (source_sha, source_size),
        label="frozen source page store",
    )
    _assert_frozen_database_unchanged(
        source_results,
        (source_results_sha, source_results_size),
        label="frozen source family-results database",
    )
    return result


def replay_sealed_rollforward_table_repair_v1(
    *,
    family_sweep_path: Path,
    family_sweep_sha256: str,
    selected_page_ids_path: Path,
    selected_page_ids_sha256: str,
    source_page_store: Path,
    source_page_store_sha256: str,
    source_results_database: Path,
    source_results_database_sha256: str,
    repair_spec_config_path: Path,
    repair_spec_config_sha256: str,
    workspace_root: Path,
    runner_implementation_sha256: str,
    artifact_root: Path,
    sealed_artifact_dir: Path,
    sealed_run_result_sha256: str,
    replay_artifact_dir: Path,
    writable_page_store: Path,
    writable_results_database: Path,
) -> dict[str, Any]:
    """Replay sealed artifacts on exactly one private page/results work pair."""

    boundaries: list[_SqliteBoundary] = []
    with tempfile.TemporaryDirectory(prefix="family13-table-repair-replay-sqlite-") as directory:
        private_root = Path(directory)
        try:
            source_store_boundary = _establish_sqlite_boundary(
                source_page_store,
                source_page_store_sha256,
                label="frozen source page store",
                private_path=private_root / "source-page-store.sqlite3",
                writable=False,
                copy_to_private=False,
            )
            boundaries.append(source_store_boundary)
            source_results_boundary = _establish_sqlite_boundary(
                source_results_database,
                source_results_database_sha256,
                label="frozen source family-results database",
                private_path=private_root / "source-family-results.sqlite3",
                writable=False,
                copy_to_private=False,
            )
            boundaries.append(source_results_boundary)
            writable_store_boundary = _establish_sqlite_boundary(
                writable_page_store,
                source_page_store_sha256,
                label="fresh replay page-store copy",
                private_path=private_root / "writable-page-store.sqlite3",
                writable=True,
            )
            boundaries.append(writable_store_boundary)
            if writable_store_boundary.identity == source_store_boundary.identity:
                raise _error(
                    "fresh replay page-store copy is the frozen source file or one hard link to it"
                )
            writable_results_boundary = _establish_sqlite_boundary(
                writable_results_database,
                source_results_database_sha256,
                label="fresh replay family-results database copy",
                private_path=private_root / "writable-family-results.sqlite3",
                writable=True,
            )
            boundaries.append(writable_results_boundary)
            if writable_results_boundary.identity == source_results_boundary.identity:
                raise _error(
                    "fresh replay family-results database copy is the frozen source file or "
                    "one hard link to it"
                )
            result = _replay_sealed_rollforward_table_repair_on_private_sqlite_v1(
                family_sweep_path=family_sweep_path,
                family_sweep_sha256=family_sweep_sha256,
                selected_page_ids_path=selected_page_ids_path,
                selected_page_ids_sha256=selected_page_ids_sha256,
                source_page_store=source_store_boundary.private_path,
                source_page_store_sha256=source_page_store_sha256,
                source_results_database=source_results_boundary.private_path,
                source_results_database_sha256=source_results_database_sha256,
                repair_spec_config_path=repair_spec_config_path,
                repair_spec_config_sha256=repair_spec_config_sha256,
                workspace_root=workspace_root,
                runner_implementation_sha256=runner_implementation_sha256,
                artifact_root=artifact_root,
                sealed_artifact_dir=sealed_artifact_dir,
                sealed_run_result_sha256=sealed_run_result_sha256,
                replay_artifact_dir=replay_artifact_dir,
                writable_page_store=writable_store_boundary.private_path,
                writable_results_database=writable_results_boundary.private_path,
                writable_page_store_ref_identity=writable_store_boundary.identity,
                writable_results_database_ref_identity=writable_results_boundary.identity,
            )
            _assert_sqlite_boundary_current(
                source_store_boundary,
                expected_sha256=source_store_boundary.initial_sha256,
                expected_size_bytes=source_store_boundary.initial_size_bytes,
            )
            _assert_sqlite_boundary_current(
                source_results_boundary,
                expected_sha256=source_results_boundary.initial_sha256,
                expected_size_bytes=source_results_boundary.initial_size_bytes,
            )
            _assert_sqlite_boundary_current(
                writable_store_boundary,
                expected_sha256=writable_store_boundary.initial_sha256,
                expected_size_bytes=writable_store_boundary.initial_size_bytes,
            )
            _assert_sqlite_boundary_current(
                writable_results_boundary,
                expected_sha256=writable_results_boundary.initial_sha256,
                expected_size_bytes=writable_results_boundary.initial_size_bytes,
            )
            _require_all_planned_jobs_resolved(
                result,
                disposition="REPAIR_FRONTIER_RECOVERED",
            )
            _bind_published_database_refs(
                artifact_root=artifact_root,
                repair_spec_config_path=repair_spec_config_path,
                repair_spec_config_sha256=repair_spec_config_sha256,
                writable_store_boundary=writable_store_boundary,
                writable_results_boundary=writable_results_boundary,
                label_prefix="published replay effective-frontier",
            )
            published = False
            try:
                published_store, published_results = _publish_private_sqlite_pair(
                    writable_store_boundary,
                    writable_results_boundary,
                    source_store_boundary,
                    source_results_boundary,
                )
                published = True
                if result.get("writable_page_store") != {
                    "sha256": published_store[0],
                    "size_bytes": published_store[1],
                }:
                    raise _error("published replay page-store bytes differ from the run result")
                if result.get("writable_results_database") != {
                    "sha256": published_results[0],
                    "size_bytes": published_results[1],
                }:
                    raise _error("published replay family-results bytes differ from the run result")
                _assert_sqlite_boundary_current(
                    source_store_boundary,
                    expected_sha256=source_store_boundary.initial_sha256,
                    expected_size_bytes=source_store_boundary.initial_size_bytes,
                )
                _assert_sqlite_boundary_current(
                    source_results_boundary,
                    expected_sha256=source_results_boundary.initial_sha256,
                    expected_size_bytes=source_results_boundary.initial_size_bytes,
                )
                _write_json(Path(replay_artifact_dir).resolve() / "run-result.json", result)
            except Exception:
                if published:
                    _rollback_published_sqlite_pair(
                        writable_store_boundary,
                        writable_results_boundary,
                        source_store_boundary,
                        source_results_boundary,
                    )
                (Path(replay_artifact_dir).resolve() / "run-result.json").unlink(missing_ok=True)
                raise
            return result
        finally:
            _close_sqlite_boundaries(boundaries)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family-sweep", type=Path, required=True)
    parser.add_argument("--family-sweep-sha256", required=True)
    parser.add_argument("--selected-page-ids", type=Path, required=True)
    parser.add_argument("--selected-page-ids-sha256", required=True)
    parser.add_argument("--source-page-store", type=Path, required=True)
    parser.add_argument("--source-page-store-sha256", required=True)
    parser.add_argument("--source-results-database", type=Path, required=True)
    parser.add_argument("--source-results-database-sha256", required=True)
    parser.add_argument("--repair-spec-config", type=Path, required=True)
    parser.add_argument("--repair-spec-config-sha256", required=True)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--runner-implementation-sha256", required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--openrouter", action="store_true")
    mode.add_argument("--replay-sealed", action="store_true")
    parser.add_argument("--writable-page-store", type=Path)
    parser.add_argument("--writable-results-database", type=Path)
    parser.add_argument("--sealed-run-result-sha256")
    parser.add_argument("--replay-artifact-dir", type=Path)
    parser.add_argument("--sealed-observation-artifact-dir", type=Path)
    parser.add_argument("--sealed-observation-run-result-sha256")
    parser.add_argument("--sealed-observation-git-commit")
    parser.add_argument(
        "--openrouter-key-file",
        type=Path,
        default=ROOT / "docs/experiments/openrouter",
    )
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.replay_sealed:
        if (
            args.writable_page_store is None
            or args.writable_results_database is None
            or args.sealed_run_result_sha256 is None
            or args.replay_artifact_dir is None
        ):
            raise _error(
                "sealed replay requires fresh writable DB copies, a pinned run result, "
                "and a fresh replay artifact directory"
            )
        result = replay_sealed_rollforward_table_repair_v1(
            family_sweep_path=args.family_sweep,
            family_sweep_sha256=args.family_sweep_sha256,
            selected_page_ids_path=args.selected_page_ids,
            selected_page_ids_sha256=args.selected_page_ids_sha256,
            source_page_store=args.source_page_store,
            source_page_store_sha256=args.source_page_store_sha256,
            source_results_database=args.source_results_database,
            source_results_database_sha256=args.source_results_database_sha256,
            repair_spec_config_path=args.repair_spec_config,
            repair_spec_config_sha256=args.repair_spec_config_sha256,
            workspace_root=args.workspace_root,
            runner_implementation_sha256=args.runner_implementation_sha256,
            artifact_root=args.artifact_root,
            sealed_artifact_dir=args.artifact_dir,
            sealed_run_result_sha256=args.sealed_run_result_sha256,
            replay_artifact_dir=args.replay_artifact_dir,
            writable_page_store=args.writable_page_store,
            writable_results_database=args.writable_results_database,
        )
        print(canonical_json_bytes_v1(result).decode("utf-8"))
        return 0
    api_key = load_openrouter_api_key_v1(args.openrouter_key_file) if args.openrouter else None
    result = run_rollforward_table_repair_v1(
        family_sweep_path=args.family_sweep,
        family_sweep_sha256=args.family_sweep_sha256,
        selected_page_ids_path=args.selected_page_ids,
        selected_page_ids_sha256=args.selected_page_ids_sha256,
        source_page_store=args.source_page_store,
        source_page_store_sha256=args.source_page_store_sha256,
        source_results_database=args.source_results_database,
        source_results_database_sha256=args.source_results_database_sha256,
        repair_spec_config_path=args.repair_spec_config,
        repair_spec_config_sha256=args.repair_spec_config_sha256,
        workspace_root=args.workspace_root,
        runner_implementation_sha256=args.runner_implementation_sha256,
        artifact_root=args.artifact_root,
        artifact_dir=args.artifact_dir,
        dry_run=args.dry_run,
        writable_page_store=args.writable_page_store,
        writable_results_database=args.writable_results_database,
        openrouter_api_key=api_key,
        workers=args.workers,
        timeout_seconds=args.timeout_seconds,
        sealed_observation_artifact_dir=args.sealed_observation_artifact_dir,
        sealed_observation_run_result_sha256=(args.sealed_observation_run_result_sha256),
        sealed_observation_git_commit=args.sealed_observation_git_commit,
    )
    print(canonical_json_bytes_v1(result).decode("utf-8"))
    return (
        2
        if result.get("disposition") in {"REPAIR_CAPTURE_INCOMPLETE", "REPAIR_FRONTIER_INCOMPLETE"}
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
