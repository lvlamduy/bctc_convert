from __future__ import annotations

import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from bctc_ai.core.hashing import sha256_bytes, stable_records_hash
from bctc_ai.core.text import retrieval_key
from bctc_ai.document_phase import native_tm_document_artifact as _native_document

POLICY_RELATIVE_PATH = Path("config/rows/native-tm-observations-v1.yaml")

_POLICY_NAME = "REGISTERED_NATIVE_TM_OBSERVATIONS_V1"
_CLAIM_BOUNDARY = "SOURCE_ONLY_NATIVE_TM_OBSERVATION_FLATTENING"
_OUTPUT_FORMAT = "REGISTERED_NATIVE_TM_OBSERVATIONS_RESULT_V1"
_STATUS = "COMPLETE_NATIVE_TM_SOURCE_OBJECT_ACCOUNTING"
_OUTPUT_DIRECTORY = "output/development"
_NATIVE_DOCUMENT_FORMAT = "REGISTERED_NATIVE_TM_FULL_DOCUMENT_ARTIFACT_RESULT_V1"
_NATIVE_DOCUMENT_POLICY = "REGISTERED_NATIVE_TM_FULL_DOCUMENT_ARTIFACT_V1"
_NATIVE_DOCUMENT_CLAIM = "SOURCE_VISIBLE_NATIVE_TM_INVENTORY_ONLY"
_NATIVE_DOCUMENT_STATUSES = (
    "COMPLETE_NATIVE_TM_FULL_DOCUMENT_ARTIFACT",
    "PARTIAL_NATIVE_TM_FULL_DOCUMENT_ARTIFACT",
)
_NATIVE_DOCUMENT_POLICY_PATH = "config/document_phase/native-tm-document-artifact-v1.yaml"
_DATASET_ROLE = "LOGIC_DEVELOPMENT"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_VISIBLE_GRID_STATUSES = frozenset(
    {"OBSERVED_VALUE", "OBSERVED_ZERO", "DASH", "INVALID_SOURCE_MARKER"}
)
_NONVISIBLE_GRID_STATUSES = frozenset({"BLANK", "UNRESOLVED_EMPTY_SLOT"})
_GRID_STATUSES = _VISIBLE_GRID_STATUSES | _NONVISIBLE_GRID_STATUSES
_FORBIDDEN_PATH_FRAGMENTS = (
    "/reference/",
    "/role-a/",
    "/role_a/",
    "/schema/",
    "/schemas/",
    "/alias/",
    "/aliases/",
    "/mapping/",
    "/mappings/",
    "/human_review/",
    "/human-review/",
    "/review/",
    "/history/",
    "/holdout/",
    "/comparisons/",
    "/docs/experiments/",
    "/config/experiments/",
    "/output/holdout/",
)

# This manifest is deliberately frozen in V1.  A future current module must
# replay an old artifact from the old producer's exact source tree rather than
# silently widening the dependency set.
_IMPLEMENTATION_PATHS = (
    "src/bctc_ai/__init__.py",
    "src/bctc_ai/axes/__init__.py",
    "src/bctc_ai/core/contracts.py",
    "src/bctc_ai/core/__init__.py",
    "src/bctc_ai/core/hashing.py",
    "src/bctc_ai/core/text.py",
    "src/bctc_ai/document_phase/__init__.py",
    "src/bctc_ai/ocr/pdf_text.py",
    "src/bctc_ai/ocr/__init__.py",
    "src/bctc_ai/ocr/native_text_quality_v2.py",
    "src/bctc_ai/rows/__init__.py",
    "src/bctc_ai/tables/geometry.py",
    "src/bctc_ai/tables/__init__.py",
    "src/bctc_ai/axes/header_binding.py",
    "src/bctc_ai/rows/pdf_statement.py",
    "src/bctc_ai/tables/native_tm_regions.py",
    "src/bctc_ai/document_phase/native_tm_document_artifact.py",
    "src/bctc_ai/rows/native_tm_observations.py",
)


class NativeTMObservationsError(RuntimeError):
    """A registered source-only native TM observation artifact failed closed."""


@dataclass(frozen=True)
class NativeTMObservationsPublication:
    path: Path
    sha256: str
    size_bytes: int
    payload: dict[str, Any]


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    try:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise NativeTMObservationsError("native TM observations are not JSON-safe") from exc
    return (encoded + "\n").encode("utf-8")


def _canonical_record_sha256(value: Any) -> str:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise NativeTMObservationsError("native TM source record is not JSON-safe") from exc
    return sha256_bytes(encoded)


def _canonical_relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise NativeTMObservationsError(f"{label} must be a canonical relative POSIX path")
    candidate = PurePosixPath(value)
    if (
        candidate.is_absolute()
        or re.match(r"^[A-Za-z]:", value)
        or candidate.as_posix() != value
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise NativeTMObservationsError(f"{label} must be a canonical relative POSIX path")
    return value


def _resolve_under_root(project_root: Path, raw_path: str | Path, label: str) -> Path:
    relative = _canonical_relative_path(Path(raw_path).as_posix(), label)
    resolved = (project_root / relative).resolve()
    try:
        resolved.relative_to(project_root)
    except ValueError as exc:
        raise NativeTMObservationsError(f"{label} escapes the project root") from exc
    return resolved


def _relative_path(project_root: Path, path: Path, label: str) -> str:
    try:
        relative = path.resolve().relative_to(project_root).as_posix()
    except ValueError as exc:
        raise NativeTMObservationsError(f"{label} must stay inside the project root") from exc
    return _canonical_relative_path(relative, label)


def _lexical_project_path(project_root: Path, raw_path: Path, label: str) -> tuple[Path, str]:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        try:
            relative = candidate.relative_to(project_root).as_posix()
        except ValueError as exc:
            raise NativeTMObservationsError(f"{label} must stay inside the project root") from exc
    else:
        relative = candidate.as_posix()
    relative = _canonical_relative_path(relative, label)
    return project_root.joinpath(*PurePosixPath(relative).parts), relative


def _read_stable_bytes(path: Path, label: str) -> bytes:
    try:
        return _native_document._read_stable_bytes(path, label)
    except _native_document.NativeTMDocumentArtifactError as exc:
        raise NativeTMObservationsError(str(exc)) from exc


def _read_guarded_project_file(project_root: Path, path: Path, relative: str, label: str) -> bytes:
    try:
        guard = _native_document._open_artifact_read_guard(project_root, path, relative)
    except _native_document.NativeTMDocumentArtifactError as exc:
        raise NativeTMObservationsError(
            f"{label} path contains a symlink or is unreadable"
        ) from exc
    try:
        return bytes(guard.payload)
    finally:
        _native_document._close_artifact_read_guard(guard)


def _yaml_bytes(payload: bytes, label: str) -> dict[str, Any]:
    try:
        parsed = yaml.safe_load(payload.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise NativeTMObservationsError(f"cannot decode {label}") from exc
    if not isinstance(parsed, dict):
        raise NativeTMObservationsError(f"{label} must be a YAML object")
    return parsed


def _jsonl_bytes(payload: bytes, label: str) -> list[dict[str, Any]]:
    try:
        lines = payload.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise NativeTMObservationsError(f"{label} is not UTF-8") from exc
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise NativeTMObservationsError(f"{label} line {line_number} is invalid JSON") from exc
        if not isinstance(record, dict):
            raise NativeTMObservationsError(f"{label} line {line_number} is not an object")
        records.append(record)
    return records


def _require_exact(value: Any, expected: Any, label: str) -> None:
    if value != expected:
        raise NativeTMObservationsError(f"{label} contract drifted")


def _validate_policy_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise NativeTMObservationsError("native TM observations policy must be an object")
    if set(payload) != {
        "version",
        "policy",
        "claim_boundary",
        "require_clean_git",
        "accepted_native_tm_document",
        "flattening",
        "report_scope",
        "role_isolation",
        "output",
    }:
        raise NativeTMObservationsError("native TM observations policy fields drifted")
    _require_exact(
        {key: payload[key] for key in ("version", "policy", "claim_boundary", "require_clean_git")},
        {
            "version": 1,
            "policy": _POLICY_NAME,
            "claim_boundary": _CLAIM_BOUNDARY,
            "require_clean_git": True,
        },
        "native TM observations policy identity",
    )
    _require_exact(
        payload["accepted_native_tm_document"],
        {
            "format_version": _NATIVE_DOCUMENT_FORMAT,
            "policy": _NATIVE_DOCUMENT_POLICY,
            "claim_boundary": _NATIVE_DOCUMENT_CLAIM,
            "accepted_statuses": list(_NATIVE_DOCUMENT_STATUSES),
            "required_dataset_role": _DATASET_ROLE,
            "trusted_sha256_required": True,
            "strict_producer_commit_replay_required": True,
        },
        "accepted native TM document policy",
    )
    _require_exact(
        payload["flattening"],
        {
            "grains": ["PAGE", "CONTEXT", "ROW", "DIMENSION", "OBSERVATION"],
            "preserve_every_region": True,
            "preserve_every_page": True,
            "preserve_page_classification_and_visible_word_inventory": True,
            "outside_quantitative_tm_disposition": "OUTSIDE_QUANTITATIVE_TM",
            "preserve_every_region_row": True,
            "preserve_outside_financial_span_rows": True,
            "preserve_row_local_scalars": True,
            "preserve_every_grid_slot": True,
            "preserve_unresolved_empty_slots": True,
            "preserve_header_components_in_source_geometry_order": True,
            "preserve_header_binding_conflicts": True,
            "preserve_inter_table_contexts": True,
            "preserve_unassigned_page_runs": True,
            "preserve_excluded_spans": True,
            "preserve_detached_margin_runs": True,
            "preserve_region_unassigned_runs": True,
            "preserve_unit_group_diagnostics": True,
            "require_exactly_one_source_disposition": True,
            "row_dependent_bindings_materialized": False,
            "unresolved_bindings_coerced": False,
        },
        "native TM observations flattening policy",
    )
    _require_exact(
        payload["report_scope"],
        {
            "authority": "SOURCE_VISIBLE_TM_HEADER_RUNS_ONLY",
            "normalization": "RETRIEVAL_KEY",
            "consolidated_retrieval_lexemes": ["hop nhat"],
            "separate_retrieval_lexemes": ["rieng", "rieng le"],
            "require_every_header_classified": True,
            "require_unanimous_non_conflicting_headers": True,
            "unresolved_scope": "UNKNOWN",
        },
        "native TM report-scope policy",
    )
    _require_exact(
        payload["role_isolation"],
        {
            "direct_runtime_input_allowlist": [
                "NATIVE_TM_DOCUMENT_ARTIFACT",
                "THIS_POLICY",
            ],
            "prior_answer_artifacts_allowed": False,
            "historical_values_allowed": False,
            "role_a_outputs_allowed": False,
            "reference_outputs_allowed": False,
            "schema_inputs_allowed": False,
            "aliases_allowed": False,
            "mapping_inputs_allowed": False,
            "bank_identity_used_for_routing": False,
            "filename_identity_used_for_routing": False,
            "page_number_rules_used_for_routing": False,
            "note_number_rules_used_for_routing": False,
            "expected_count_rules_used_for_routing": False,
            "forbidden_path_fragments": list(_FORBIDDEN_PATH_FRAGMENTS),
        },
        "native TM observations role isolation",
    )
    _require_exact(
        payload["output"],
        {
            "format": _OUTPUT_FORMAT,
            "status": _STATUS,
            "canonical_json": True,
            "exclusive_no_overwrite": True,
            "rollback_after_failed_strict_replay": True,
            "absolute_project_paths_allowed": False,
            "output_directory": _OUTPUT_DIRECTORY,
            "source_object_accounting_required": True,
            "full_document_context_completion_required": False,
        },
        "native TM observations output policy",
    )
    return copy.deepcopy(payload)


def _validate_path_isolation(paths: Sequence[str], policy: Mapping[str, Any]) -> None:
    fragments = tuple(
        str(item).casefold() for item in policy["role_isolation"]["forbidden_path_fragments"]
    )
    for raw_path in paths:
        relative = _canonical_relative_path(raw_path, "runtime path")
        normalized = "/" + relative.casefold().strip("/")
        if any(fragment in normalized for fragment in fragments):
            raise NativeTMObservationsError(
                f"runtime path is forbidden by role isolation: {relative}"
            )


def load_native_tm_observations_policy(path: Path, project_root: Path) -> dict[str, Any]:
    """Load the one canonical generic source-only observation policy."""

    project_root = project_root.resolve()
    path, relative = _lexical_project_path(project_root, path, "native TM observations policy")
    if relative != POLICY_RELATIVE_PATH.as_posix():
        raise NativeTMObservationsError(
            f"native TM observations require canonical policy {POLICY_RELATIVE_PATH}"
        )
    policy = _validate_policy_payload(
        _yaml_bytes(
            _read_guarded_project_file(
                project_root, path, relative, "native TM observations policy"
            ),
            "policy",
        )
    )
    _validate_path_isolation([POLICY_RELATIVE_PATH.as_posix(), *_IMPLEMENTATION_PATHS], policy)
    return policy


def _git(project_root: Path, *arguments: str, binary: bool = False) -> str | bytes:
    result = subprocess.run(
        ["git", *arguments],
        cwd=project_root,
        capture_output=True,
        text=not binary,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace") if binary else str(result.stderr)
        raise NativeTMObservationsError(f"git {' '.join(arguments)} failed: {stderr.strip()}")
    return result.stdout


def _current_git_state(project_root: Path) -> dict[str, Any]:
    commit = str(_git(project_root, "rev-parse", "HEAD")).strip()
    dirty = bool(str(_git(project_root, "status", "--porcelain", "--untracked-files=all")).strip())
    if _GIT_COMMIT.fullmatch(commit) is None or dirty:
        raise NativeTMObservationsError(
            "native TM observations require the clean, identified current HEAD"
        )
    return {"commit": commit, "dirty": False}


def _git_file_bytes(project_root: Path, commit: str, raw_path: str) -> bytes:
    if _GIT_COMMIT.fullmatch(commit) is None:
        raise NativeTMObservationsError("native TM observations producer commit is invalid")
    relative = _canonical_relative_path(raw_path, "producer snapshot path")
    return bytes(_git(project_root, "show", f"{commit}:{relative}", binary=True))


def _file_identity(path: Path, project_root: Path, kind: str | None = None) -> dict[str, Any]:
    payload = _read_stable_bytes(path, kind or "runtime input")
    record: dict[str, Any] = {
        "path": _relative_path(project_root, path, kind or "runtime input"),
        "sha256": sha256_bytes(payload),
        "size_bytes": len(payload),
    }
    return {"kind": kind, **record} if kind is not None else record


def _file_identity_at_commit(
    project_root: Path,
    commit: str,
    raw_path: str,
    *,
    kind: str | None = None,
) -> dict[str, Any]:
    payload = _git_file_bytes(project_root, commit, raw_path)
    record: dict[str, Any] = {
        "path": raw_path,
        "sha256": sha256_bytes(payload),
        "size_bytes": len(payload),
    }
    return {"kind": kind, **record} if kind is not None else record


def _implementation_ledger(project_root: Path) -> list[dict[str, Any]]:
    return [
        _file_identity(
            _resolve_under_root(project_root, relative, "implementation module"), project_root
        )
        for relative in _IMPLEMENTATION_PATHS
    ]


def _implementation_ledger_at_commit(project_root: Path, commit: str) -> list[dict[str, Any]]:
    return [
        _file_identity_at_commit(project_root, commit, relative)
        for relative in _IMPLEMENTATION_PATHS
    ]


def _runtime_ledger_hash(records: Sequence[Mapping[str, Any]]) -> str:
    return stable_records_hash(
        json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for record in records
    )


def _as_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise NativeTMObservationsError(f"{label} must be an object")
    return value


def _as_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise NativeTMObservationsError(f"{label} must be a list")
    return value


def _as_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise NativeTMObservationsError(f"{label} must be a non-empty string")
    return value


def _as_integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise NativeTMObservationsError(f"{label} must be an integer")
    return value


def _validate_native_document(payload: Any, policy: Mapping[str, Any]) -> dict[str, Any]:
    document = _as_object(payload, "native TM document artifact")
    expected_top = {
        "format_version",
        "policy",
        "claim_boundary",
        "status",
        "run_id",
        "source",
        "statement_discovery",
        "code",
        "authority",
        "isolation",
        "inputs",
        "producer_snapshots",
        "completeness",
        "note_inventory",
        "table_inventory",
        "pages",
    }
    if set(document) != expected_top:
        raise NativeTMObservationsError("native TM document artifact envelope drifted")
    accepted = policy["accepted_native_tm_document"]
    for key in ("format_version", "policy", "claim_boundary"):
        if document.get(key) != accepted[key]:
            raise NativeTMObservationsError(f"native TM document {key} is invalid")
    if document.get("status") not in accepted["accepted_statuses"]:
        raise NativeTMObservationsError("native TM document status is invalid")
    if (
        not isinstance(document.get("run_id"), str)
        or _SAFE_RUN_ID.fullmatch(document["run_id"]) is None
    ):
        raise NativeTMObservationsError("native TM document run_id is invalid")
    source = _as_object(document.get("source"), "native TM document source")
    if source.get("dataset_role") != _DATASET_ROLE:
        raise NativeTMObservationsError(
            "native TM observations accept LOGIC_DEVELOPMENT sources only"
        )
    _canonical_relative_path(source.get("relative_path"), "native TM source path")
    if (
        not isinstance(source.get("sha256"), str)
        or _SHA256.fullmatch(source["sha256"]) is None
        or isinstance(source.get("size_bytes"), bool)
        or not isinstance(source.get("size_bytes"), int)
        or source["size_bytes"] < 0
    ):
        raise NativeTMObservationsError("native TM document source identity is invalid")
    code = _as_object(document.get("code"), "native TM document producer")
    if (
        not isinstance(code.get("commit"), str)
        or _GIT_COMMIT.fullmatch(code["commit"]) is None
        or code.get("dirty") is not False
    ):
        raise NativeTMObservationsError("native TM document producer identity is invalid")
    pages = _as_list(document.get("pages"), "native TM document pages")
    completeness = _as_object(document.get("completeness"), "native TM completeness")
    page_count = _as_integer(completeness.get("pdf_page_count"), "native TM PDF page count")
    if (
        page_count < 1
        or len(pages) != page_count
        or [page.get("page") for page in pages if isinstance(page, dict)]
        != list(range(1, page_count + 1))
    ):
        raise NativeTMObservationsError("native TM document page denominator drifted")
    return copy.deepcopy(document)


def _contains_token_phrase(text: str, phrase: str) -> bool:
    text_tokens = text.split()
    phrase_tokens = phrase.split()
    width = len(phrase_tokens)
    return width > 0 and any(
        text_tokens[index : index + width] == phrase_tokens
        for index in range(len(text_tokens) - width + 1)
    )


def _scope_binding(pages: Sequence[Mapping[str, Any]], policy: Mapping[str, Any]) -> dict[str, Any]:
    scope_policy = policy["report_scope"]
    consolidated = tuple(scope_policy["consolidated_retrieval_lexemes"])
    separate = tuple(scope_policy["separate_retrieval_lexemes"])
    evidence: list[dict[str, Any]] = []
    signals: list[str] = []
    evidence_keys: set[tuple[int, str]] = set()
    for page in pages:
        page_number = _as_integer(page.get("page"), "report-scope evidence page")
        runs = _as_list(page.get("source_visible_tm_header_runs"), "source-visible TM header runs")
        for raw_run in runs:
            run = _as_object(raw_run, "source-visible TM header run")
            raw_text = _as_string(run.get("raw_text"), "source-visible TM header text")
            key = retrieval_key(raw_text)
            has_consolidated = any(_contains_token_phrase(key, lexeme) for lexeme in consolidated)
            has_separate = any(_contains_token_phrase(key, lexeme) for lexeme in separate)
            if has_consolidated and has_separate:
                signal = "CONFLICT"
            elif has_consolidated:
                signal = "CONSOLIDATED"
            elif has_separate:
                signal = "SEPARATE"
            else:
                signal = "UNCLASSIFIED"
            signals.append(signal)
            run_id = _as_string(run.get("run_id"), "TM header run ID")
            natural_key = (page_number, run_id)
            if natural_key in evidence_keys:
                raise NativeTMObservationsError(
                    "report-scope evidence repeats a page/run natural identity"
                )
            evidence_keys.add(natural_key)
            evidence.append(
                {
                    "evidence_id": (f"REPORT_SCOPE_HEADER::page-{page_number:04d}::{run_id}"),
                    "page": page_number,
                    "scope_signal": signal,
                    "retrieval_key": key,
                    "source_run": copy.deepcopy(run),
                }
            )
    unique_signals = set(signals)
    if not signals:
        scope = scope_policy["unresolved_scope"]
        binding_status = "UNRESOLVED_NO_SOURCE_VISIBLE_TM_HEADER"
    elif unique_signals == {"CONSOLIDATED"}:
        scope = "CONSOLIDATED"
        binding_status = "RESOLVED_UNANIMOUS_SOURCE_VISIBLE_TM_HEADERS"
    elif unique_signals == {"SEPARATE"}:
        scope = "SEPARATE"
        binding_status = "RESOLVED_UNANIMOUS_SOURCE_VISIBLE_TM_HEADERS"
    elif "CONFLICT" in unique_signals or {"CONSOLIDATED", "SEPARATE"} <= unique_signals:
        scope = scope_policy["unresolved_scope"]
        binding_status = "UNRESOLVED_CONFLICTING_SOURCE_VISIBLE_TM_HEADERS"
    else:
        scope = scope_policy["unresolved_scope"]
        binding_status = "UNRESOLVED_UNCLASSIFIED_SOURCE_VISIBLE_TM_HEADERS"
    return {
        "scope": scope,
        "binding_status": binding_status,
        "authority": scope_policy["authority"],
        "normalization": scope_policy["normalization"],
        "source_header_run_count": len(evidence),
        "signal_counts": {
            signal: signals.count(signal)
            for signal in ("CONSOLIDATED", "SEPARATE", "CONFLICT", "UNCLASSIFIED")
        },
        "evidence_runs": evidence,
        "bank_identity_used": False,
        "filename_identity_used": False,
        "page_number_rules_used": False,
        "note_number_rules_used": False,
    }


def _source_geometry_order(run: Mapping[str, Any]) -> tuple[Any, ...]:
    bbox = _as_object(run.get("bbox"), "header component bbox")
    coordinates = []
    for key in ("y0", "x0", "y1", "x1"):
        value = bbox.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise NativeTMObservationsError("header component bbox is invalid")
        coordinates.append(float(value))
    return (
        *coordinates,
        run.get("block_number"),
        run.get("line_number"),
        run.get("run_id"),
    )


def _header_components(
    *,
    context_id: str,
    dimension_id: str,
    binding: Mapping[str, Any],
    region: Mapping[str, Any],
) -> list[dict[str, Any]]:
    runs_by_id: dict[str, dict[str, Any]] = {}
    geometry = _as_object(region.get("geometry"), "native TM region geometry")
    candidates = [
        *_as_list(geometry.get("runs"), "native TM region geometry runs"),
        *_as_list(region.get("header_runs"), "native TM region header runs"),
    ]
    for raw_run in candidates:
        run = _as_object(raw_run, "native TM source run")
        run_id = _as_string(run.get("run_id"), "native TM source run ID")
        prior = runs_by_id.get(run_id)
        if prior is not None and prior != run:
            raise NativeTMObservationsError(
                f"native TM source run {run_id} has conflicting serializations"
            )
        runs_by_id[run_id] = run
    source_ids = _as_list(binding.get("source_run_ids"), "header binding source run IDs")
    if any(not isinstance(run_id, str) or not run_id for run_id in source_ids):
        raise NativeTMObservationsError("header binding source run IDs are invalid")
    if len(source_ids) != len(set(source_ids)):
        raise NativeTMObservationsError("header binding repeats a source run ID")
    try:
        selected = [runs_by_id[run_id] for run_id in source_ids]
    except KeyError as exc:
        raise NativeTMObservationsError(
            "header binding references a missing source geometry run"
        ) from exc
    selected.sort(key=_source_geometry_order)
    return [
        {
            "component_id": (
                f"HEADER_COMPONENT::{dimension_id}::{ordinal:03d}::"
                f"{_as_string(run.get('run_id'), 'header component run ID')}"
            ),
            "component_order": ordinal,
            "context_id": context_id,
            "dimension_id": dimension_id,
            "run_id": run["run_id"],
            "raw_text": run.get("raw_text"),
            "normalized_text": run.get("normalized_text"),
            "bbox": copy.deepcopy(run.get("bbox")),
            "block_number": run.get("block_number"),
            "line_number": run.get("line_number"),
            "word_indices": copy.deepcopy(run.get("word_indices")),
            "semantic_component_kind": "UNAVAILABLE_IN_UPSTREAM_BINDING",
            "semantic_assignment_status": "NOT_MATERIALIZED",
            "source_owner_id": (
                f"SOURCE_RUN::GEOMETRY::{context_id.removeprefix('CONTEXT::')}::{run['run_id']}"
            ),
        }
        for ordinal, run in enumerate(selected, start=1)
    ]


def _binding_materialization(scope: Any, binding_status: Any, label: str) -> dict[str, str]:
    scope = _as_string(scope, f"{label} scope")
    binding_status = _as_string(binding_status, f"{label} binding status")
    if "CONFLICT" in binding_status:
        return {
            "resolution_status": "SOURCE_CONFLICT",
            "materialization_status": "NOT_MATERIALIZED",
            "row_override_status": "NOT_MATERIALIZED",
            "row_override_evidence_status": "NOT_SERIALIZED_BY_UPSTREAM_SOURCE_STAGE",
        }
    if scope == "ROW_DEPENDENT":
        return {
            "resolution_status": "ROW_DEPENDENT",
            "materialization_status": "NOT_MATERIALIZED",
            "row_override_status": "NOT_MATERIALIZED",
            "row_override_evidence_status": "NOT_SERIALIZED_BY_UPSTREAM_SOURCE_STAGE",
        }
    if scope == "UNRESOLVED":
        return {
            "resolution_status": "UNRESOLVED",
            "materialization_status": "NOT_MATERIALIZED",
            "row_override_status": "NOT_MATERIALIZED",
            "row_override_evidence_status": "NOT_SERIALIZED_BY_UPSTREAM_SOURCE_STAGE",
        }
    return {
        "resolution_status": "SOURCE_BINDING_RESOLVED",
        "materialization_status": "MATERIALIZED_AT_DIMENSION_GRAIN",
        "row_override_status": "NOT_APPLICABLE",
        "row_override_evidence_status": "NOT_SERIALIZED_BY_UPSTREAM_SOURCE_STAGE",
    }


def _context_id(table_id: str) -> str:
    return f"CONTEXT::{table_id}"


def _dimension_id(table_id: str, axis_id: str) -> str:
    return f"DIMENSION::{table_id}::{axis_id}"


def _grid_observation_id(row_id: str, axis_id: str) -> str:
    return f"OBSERVATION::GRID_SLOT::{row_id}::{axis_id}"


def _source_disposition_record(record: Mapping[str, Any]) -> dict[str, str]:
    return {
        "source_object_id": _as_string(record.get("source_object_id"), "source object ID"),
        "source_object_type": _as_string(record.get("record_type"), "source object record type"),
        "source_disposition": _as_string(
            record.get("source_disposition"), "source object disposition"
        ),
    }


def _register_run_owner(
    owners: dict[tuple[int, str], str],
    *,
    page: int,
    run_id: str,
    source_object_id: str,
) -> None:
    key = (page, run_id)
    if key in owners:
        raise NativeTMObservationsError(
            f"native TM source run {page}:{run_id} has more than one canonical owner"
        )
    owners[key] = source_object_id


_FULL_TEXT_RUN_KEYS = {
    "run_id",
    "raw_text",
    "normalized_text",
    "bbox",
    "block_number",
    "line_number",
    "word_indices",
}
_PAGE_EVIDENCE_RUN_KEYS = {
    "run_id",
    "raw_text",
    "normalized_text",
    "bbox",
    "block_number",
    "line_number",
    "retrieval_key",
}


def _full_run_reference_matches(reference: Mapping[str, Any], owner: Mapping[str, Any]) -> bool:
    return (
        set(reference) == _FULL_TEXT_RUN_KEYS
        and set(owner) == _FULL_TEXT_RUN_KEYS
        and dict(reference) == dict(owner)
    )


def _page_evidence_reference_matches(
    reference: Mapping[str, Any], owner: Mapping[str, Any]
) -> bool:
    shared_keys = _FULL_TEXT_RUN_KEYS - {"word_indices"}
    raw_text = reference.get("raw_text")
    return (
        set(reference) == _PAGE_EVIDENCE_RUN_KEYS
        and set(owner) == _FULL_TEXT_RUN_KEYS
        and isinstance(raw_text, str)
        and reference.get("retrieval_key") == retrieval_key(raw_text)
        and all(reference.get(key) == owner.get(key) for key in shared_keys)
    )


def _evidence_record(
    *,
    record_type: str,
    source_object_id: str,
    source_disposition: str,
    source_record: Mapping[str, Any],
    extra: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "record_type": record_type,
        "source_object_id": source_object_id,
        "source_disposition": source_disposition,
        **copy.deepcopy(dict(extra)),
        "source_record": copy.deepcopy(dict(source_record)),
        "source_record_sha256": _canonical_record_sha256(source_record),
    }


def _build_projection(
    *,
    native_document: Mapping[str, Any],
    native_document_identity: Mapping[str, Any],
    policy_relative: str,
    policy_bytes: bytes,
    policy: Mapping[str, Any],
    runtime_inputs: Sequence[dict[str, Any]],
    implementation: Sequence[dict[str, Any]],
    producer_commit: str,
    run_id: str,
) -> dict[str, Any]:
    if _SAFE_RUN_ID.fullmatch(run_id) is None:
        raise NativeTMObservationsError("native TM observations run_id is invalid")
    artifact_run_id = run_id
    policy = _validate_policy_payload(policy)
    document = _validate_native_document(native_document, policy)
    pages = document["pages"]
    runtime_inputs = copy.deepcopy(list(runtime_inputs))
    expected_kinds = set(policy["role_isolation"]["direct_runtime_input_allowlist"])
    if (
        runtime_inputs != sorted(runtime_inputs, key=lambda item: (item["kind"], item["path"]))
        or {item.get("kind") for item in runtime_inputs} != expected_kinds
        or any(
            not isinstance(item, dict) or set(item) != {"kind", "path", "sha256", "size_bytes"}
            for item in runtime_inputs
        )
    ):
        raise NativeTMObservationsError("native TM observations runtime ledger drifted")
    if [item.get("path") for item in implementation if isinstance(item, dict)] != list(
        _IMPLEMENTATION_PATHS
    ):
        raise NativeTMObservationsError("native TM observations implementation ledger drifted")
    _validate_path_isolation(
        [item["path"] for item in runtime_inputs] + [item["path"] for item in implementation],
        policy,
    )

    contexts: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    dimensions: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    source_evidence: dict[str, list[dict[str, Any]]] = {
        "inter_table_contexts": [],
        "geometry_runs": [],
        "inter_table_context_runs": [],
        "unassigned_page_runs": [],
        "excluded_spans": [],
        "detached_margin_runs": [],
        "unit_group_diagnostics": [],
    }
    source_references: dict[str, list[dict[str, Any]]] = {
        "region_unassigned_runs": [],
    }
    run_owner_by_key: dict[tuple[int, str], str] = {}
    unit_diagnostic_keys: set[tuple[int, tuple[str, ...]]] = set()
    excluded_span_keys: set[tuple[int, int, int, int, int]] = set()

    inter_context_ids_by_row: dict[str, list[str]] = {}
    inter_context_status_by_row: dict[str, set[str]] = {}
    context_row_seen: set[str] = set()
    for page in pages:
        page_number = _as_integer(page.get("page"), "native TM page number")
        page_classification = _as_string(
            page.get("classification"), "native TM page classification"
        )
        native_regions = _as_object(page.get("native_tm_regions"), "native TM page regions")
        inter_contexts = _as_list(
            native_regions.get("inter_table_contexts"), "native TM inter-table contexts"
        )
        for ordinal, raw_context in enumerate(inter_contexts, start=1):
            context = _as_object(raw_context, "native TM inter-table context")
            preceding = _as_string(
                context.get("preceding_table_id"), "preceding native TM table ID"
            )
            following = _as_string(
                context.get("following_table_id"), "following native TM table ID"
            )
            evidence_id = (
                f"INTER_TABLE_CONTEXT::page-{page_number:04d}::{preceding}::{following}::"
                f"{ordinal:03d}"
            )
            status = _as_string(context.get("ownership_status"), "inter-table ownership status")
            disposition = (
                "OUTSIDE_QUANTITATIVE_TM" if page_classification != "QUANTITATIVE_TM" else status
            )
            source_evidence["inter_table_contexts"].append(
                _evidence_record(
                    record_type="INTER_TABLE_CONTEXT",
                    source_object_id=evidence_id,
                    source_disposition=disposition,
                    source_record=context,
                    extra={
                        "evidence_id": evidence_id,
                        "page": page_number,
                        "page_classification": page_classification,
                    },
                )
            )
            for run_ordinal, raw_run in enumerate(
                _as_list(context.get("runs"), "inter-table context runs"), start=1
            ):
                run = _as_object(raw_run, "inter-table context run")
                run_id = _as_string(run.get("run_id"), "inter-table context run ID")
                run_object_id = (
                    f"SOURCE_RUN::INTER_TABLE_CONTEXT::{evidence_id}::{run_id}::{run_ordinal:03d}"
                )
                _register_run_owner(
                    run_owner_by_key,
                    page=page_number,
                    run_id=run_id,
                    source_object_id=run_object_id,
                )
                source_evidence["inter_table_context_runs"].append(
                    _evidence_record(
                        record_type="SOURCE_RUN",
                        source_object_id=run_object_id,
                        source_disposition=disposition,
                        source_record=run,
                        extra={
                            "evidence_id": run_object_id,
                            "source_owner_kind": "INTER_TABLE_CONTEXT",
                            "inter_table_context_id": evidence_id,
                            "page": page_number,
                            "run_id": run_id,
                            "run_ordinal": run_ordinal,
                        },
                    )
                )
            for context_row_ordinal, raw_row_id in enumerate(
                _as_list(
                    context.get("source_row_ids"),
                    "inter-table context source row IDs",
                )
            ):
                row_id = _as_string(raw_row_id, "inter-table context source row ID")
                if row_id in context_row_seen:
                    raise NativeTMObservationsError(
                        "inter-table context row identity is not uniquely owned"
                    )
                context_row_seen.add(row_id)
                inter_context_ids_by_row.setdefault(row_id, []).append(evidence_id)
                inter_context_status_by_row.setdefault(row_id, set()).add(status)
                row_object_id = f"ROW::{row_id}"
                rows.append(
                    {
                        "record_type": "ROW",
                        "source_object_id": row_object_id,
                        "source_disposition": disposition,
                        "row_source_kind": "INTER_TABLE_CONTEXT_ROW",
                        "context_id": None,
                        "inter_table_context_id": evidence_id,
                        "source_table_id": None,
                        "preceding_table_id": preceding,
                        "following_table_id": following,
                        "page": page_number,
                        "page_classification": page_classification,
                        "row_id": row_id,
                        "row_ordinal": None,
                        "label": None,
                        "label_boxes": [],
                        "source_cells": [],
                        "observation_ids": [],
                        "value_bearing": False,
                        "run_partition_status": "UNRESOLVED_CONTEXT_LEVEL_ONLY",
                        "source_order": {
                            "page": page_number,
                            "source_container_kind": "INTER_TABLE_CONTEXT",
                            "source_container_ordinal": ordinal - 1,
                            "row_ordinal_within_container": context_row_ordinal,
                            "cross_container_order_status": (
                                "NOT_SERIALIZED_BY_UPSTREAM_SOURCE_STAGE"
                            ),
                        },
                        "context_row_reference_sha256": _canonical_record_sha256(
                            {
                                "source_row_id": row_id,
                                "inter_table_context_id": evidence_id,
                            }
                        ),
                    }
                )

    for page in pages:
        page_number = _as_integer(page.get("page"), "native TM page number")
        page_classification = _as_string(
            page.get("classification"), "native TM page classification"
        )
        page_disposition = (
            "QUANTITATIVE_TM"
            if page_classification == "QUANTITATIVE_TM"
            else "OUTSIDE_QUANTITATIVE_TM"
        )
        native_regions = _as_object(page.get("native_tm_regions"), "native TM page regions")
        region_records = _as_list(native_regions.get("regions"), "native TM regions")
        for region_ordinal, raw_region in enumerate(region_records, start=1):
            region = _as_object(raw_region, "native TM region")
            table_id = _as_string(region.get("table_id"), "native TM table ID")
            context_id = _context_id(table_id)
            if region.get("page") != page_number:
                raise NativeTMObservationsError("native TM region page identity drifted")
            geometry = _as_object(region.get("geometry"), "native TM region geometry")
            axes = _as_list(geometry.get("axes"), "native TM region axes")
            geometry_runs = _as_list(geometry.get("runs"), "native TM region geometry runs")
            for run_ordinal, raw_run in enumerate(geometry_runs, start=1):
                run = _as_object(raw_run, "native TM region geometry run")
                run_id = _as_string(run.get("run_id"), "native TM geometry run ID")
                run_object_id = f"SOURCE_RUN::GEOMETRY::{table_id}::{run_id}"
                _register_run_owner(
                    run_owner_by_key,
                    page=page_number,
                    run_id=run_id,
                    source_object_id=run_object_id,
                )
                source_evidence["geometry_runs"].append(
                    _evidence_record(
                        record_type="SOURCE_RUN",
                        source_object_id=run_object_id,
                        source_disposition=page_disposition,
                        source_record=run,
                        extra={
                            "evidence_id": run_object_id,
                            "source_owner_kind": "REGION_GEOMETRY",
                            "context_id": context_id,
                            "page": page_number,
                            "run_id": run_id,
                            "run_ordinal": run_ordinal,
                        },
                    )
                )
            bindings = _as_list(region.get("header_bindings"), "native TM header bindings")
            binding_by_axis: dict[str, dict[str, Any]] = {}
            for raw_binding in bindings:
                binding = _as_object(raw_binding, "native TM header binding")
                axis_id = _as_string(binding.get("axis_id"), "header binding axis ID")
                if axis_id in binding_by_axis:
                    raise NativeTMObservationsError("native TM region repeats a header binding")
                binding_by_axis[axis_id] = binding
            dimension_ids: list[str] = []
            for axis_ordinal, raw_axis in enumerate(axes):
                axis = _as_object(raw_axis, "native TM source axis")
                axis_id = _as_string(axis.get("axis_id"), "native TM source axis ID")
                binding = binding_by_axis.pop(axis_id, None)
                if binding is None:
                    raise NativeTMObservationsError(
                        "native TM source axis has no exact header binding"
                    )
                raw_period_group_id = binding.get("period_group_id")
                period_group_id = (
                    None
                    if raw_period_group_id is None
                    else _as_string(raw_period_group_id, "native TM binding period-group ID")
                )
                dimension_id = _dimension_id(table_id, axis_id)
                dimension_ids.append(dimension_id)
                dimension = {
                    "record_type": "DIMENSION",
                    "source_object_id": dimension_id,
                    "source_disposition": page_disposition,
                    "dimension_id": dimension_id,
                    "context_id": context_id,
                    "source_table_id": table_id,
                    "page": page_number,
                    "page_classification": page_classification,
                    "axis_id": axis_id,
                    "axis_ordinal": axis_ordinal,
                    "axis": copy.deepcopy(axis),
                    **copy.deepcopy(binding),
                    "qualified_period_group_id": (
                        None
                        if period_group_id is None
                        else f"PERIOD_GROUP::{table_id}::{period_group_id}"
                    ),
                    "header_components": _header_components(
                        context_id=context_id,
                        dimension_id=dimension_id,
                        binding=binding,
                        region=region,
                    ),
                    "header_component_semantic_partition_status": (
                        "NOT_SERIALIZED_BY_UPSTREAM_SOURCE_STAGE"
                    ),
                    "period_materialization": _binding_materialization(
                        binding.get("period_scope"),
                        binding.get("binding_status"),
                        "period",
                    ),
                    "unit_materialization": _binding_materialization(
                        binding.get("unit_scope"),
                        binding.get("binding_status"),
                        "unit",
                    ),
                    "source_axis_record_sha256": _canonical_record_sha256(axis),
                    "source_binding_record_sha256": _canonical_record_sha256(binding),
                }
                dimensions.append(dimension)
            if binding_by_axis:
                raise NativeTMObservationsError("native TM header binding has no exact source axis")

            region_rows = _as_list(region.get("rows"), "native TM region rows")
            outside_rows = _as_list(
                region.get("outside_financial_span_rows"),
                "native TM outside-financial-span rows",
            )
            scalars = _as_list(region.get("scalar_disclosures"), "native TM scalar disclosures")
            grid_slots = _as_list(region.get("grid_slots"), "native TM grid slots")
            source_rows_by_id: dict[str, dict[str, Any]] = {}
            source_cells_by_key: dict[tuple[str, str], dict[str, Any]] = {}
            for raw_row in region_rows:
                row = _as_object(raw_row, "native TM region row")
                row_id = _as_string(row.get("row_id"), "native TM source row ID")
                if row_id in source_rows_by_id:
                    raise NativeTMObservationsError("native TM region repeats a source row ID")
                source_rows_by_id[row_id] = row
                for raw_cell in _as_list(row.get("cells"), "native TM row cells"):
                    cell = _as_object(raw_cell, "native TM source cell")
                    axis_id = _as_string(cell.get("axis_id"), "native TM cell axis ID")
                    key = (row_id, axis_id)
                    if key in source_cells_by_key:
                        raise NativeTMObservationsError("native TM row repeats an axis cell")
                    source_cells_by_key[key] = cell
            observation_ids_by_row: dict[str, list[str]] = {}
            context_observation_ids: list[str] = []
            for slot_ordinal, raw_slot in enumerate(grid_slots):
                slot = _as_object(raw_slot, "native TM grid slot")
                row_id = _as_string(slot.get("row_id"), "native TM grid-slot row ID")
                axis_id = _as_string(slot.get("axis_id"), "native TM grid-slot axis ID")
                if row_id not in source_rows_by_id:
                    raise NativeTMObservationsError("native TM grid slot references a missing row")
                if axis_id not in {axis["axis_id"] for axis in axes}:
                    raise NativeTMObservationsError("native TM grid slot references a missing axis")
                source_status = _as_string(slot.get("source_status"), "native TM grid-slot status")
                if source_status not in _GRID_STATUSES:
                    raise NativeTMObservationsError(
                        f"unsupported native TM grid-slot status: {source_status}"
                    )
                key = (row_id, axis_id)
                cell = source_cells_by_key.pop(key, None)
                visible_marker = source_status in _VISIBLE_GRID_STATUSES
                if visible_marker and cell is None:
                    raise NativeTMObservationsError(
                        "native TM visible grid-slot marker has no exact source cell"
                    )
                if source_status == "UNRESOLVED_EMPTY_SLOT" and cell is not None:
                    raise NativeTMObservationsError(
                        "unresolved native TM grid slot unexpectedly has a source cell"
                    )
                if cell is not None and (
                    cell.get("run_id") != slot.get("source_run_id")
                    or cell.get("raw_text") != slot.get("raw_text")
                ):
                    raise NativeTMObservationsError(
                        "native TM cell and grid-slot source identity differ"
                    )
                observation_id = _grid_observation_id(row_id, axis_id)
                raw_source_run_id = slot.get("source_run_id")
                source_run_owner_id = None
                if raw_source_run_id is not None:
                    source_run_id = _as_string(
                        raw_source_run_id, "native TM grid-slot source run ID"
                    )
                    source_run_owner_id = run_owner_by_key.get((page_number, source_run_id))
                    if source_run_owner_id is None:
                        raise NativeTMObservationsError(
                            "native TM grid slot has no canonical source-run owner"
                        )
                observation_ids_by_row.setdefault(row_id, []).append(observation_id)
                context_observation_ids.append(observation_id)
                parsed = copy.deepcopy(cell.get("parsed")) if cell is not None else None
                if source_status == "BLANK":
                    observation_kind = "BLANK"
                elif source_status == "UNRESOLVED_EMPTY_SLOT":
                    observation_kind = "UNRESOLVED_EMPTY_SLOT"
                else:
                    parsed_object = _as_object(parsed, "native TM parsed source cell")
                    observation_kind = _as_string(
                        parsed_object.get("observation"), "native TM observation kind"
                    )
                    expected_kind = {
                        "OBSERVED_VALUE": "VALUE",
                        "OBSERVED_ZERO": "ZERO",
                        "DASH": "DASH",
                        "INVALID_SOURCE_MARKER": "INVALID",
                    }[source_status]
                    if observation_kind != expected_kind:
                        raise NativeTMObservationsError(
                            "native TM cell and grid-slot status semantics differ"
                        )
                observations.append(
                    {
                        "record_type": "OBSERVATION",
                        "source_object_id": observation_id,
                        "source_disposition": page_disposition,
                        "observation_id": observation_id,
                        "observation_source_kind": "GRID_SLOT",
                        "context_id": context_id,
                        "row_id": row_id,
                        "dimension_id": _dimension_id(table_id, axis_id),
                        "source_table_id": table_id,
                        "page": page_number,
                        "page_classification": page_classification,
                        "slot_ordinal": slot_ordinal,
                        **copy.deepcopy(slot),
                        "observation_kind": observation_kind,
                        "is_visible_source_marker": visible_marker,
                        "source_cell_present": cell is not None,
                        "source_run_owner_id": source_run_owner_id,
                        "parsed": parsed,
                        "source_cell": copy.deepcopy(cell),
                        "dimension_binding_materialized_on_observation": False,
                        "source_slot_record_sha256": _canonical_record_sha256(slot),
                    }
                )
            if source_cells_by_key:
                raise NativeTMObservationsError(
                    "native TM source cell has no exact serialized grid slot"
                )

            context_row_ids: list[str] = []
            for row_ordinal, raw_row in enumerate(region_rows):
                row = _as_object(raw_row, "native TM region row")
                row_id = _as_string(row.get("row_id"), "native TM source row ID")
                source_object_id = f"ROW::{row_id}"
                context_row_ids.append(row_id)
                source_cells = _as_list(row.get("cells"), "native TM row cells")
                row_record = {
                    "record_type": "ROW",
                    "source_object_id": source_object_id,
                    "source_disposition": page_disposition,
                    "row_source_kind": "REGION_ROW",
                    "context_id": context_id,
                    "source_table_id": table_id,
                    "page_classification": page_classification,
                    "row_ordinal": row_ordinal,
                    **{key: copy.deepcopy(value) for key, value in row.items() if key != "cells"},
                    "source_cells": copy.deepcopy(source_cells),
                    "observation_ids": observation_ids_by_row.get(row_id, []),
                    "value_bearing": bool(source_cells),
                    "source_order": {
                        "page": page_number,
                        "source_container_kind": "TABLE_REGION",
                        "source_container_ordinal": region_ordinal - 1,
                        "row_ordinal_within_container": row_ordinal,
                        "cross_container_order_status": ("NOT_SERIALIZED_BY_UPSTREAM_SOURCE_STAGE"),
                    },
                    "source_record_sha256": _canonical_record_sha256(row),
                }
                rows.append(row_record)

            for outside_ordinal, raw_row in enumerate(outside_rows):
                row = _as_object(raw_row, "native TM outside-financial-span row")
                outside_cells = _as_list(
                    row.get("cells"), "native TM outside-financial-span row cells"
                )
                if outside_cells:
                    raise NativeTMObservationsError(
                        "outside-financial-span row cells cannot be dropped from positions"
                    )
                row_id = _as_string(row.get("row_id"), "outside-financial-span row ID")
                if row_id in source_rows_by_id:
                    raise NativeTMObservationsError(
                        "outside-financial-span row duplicates a region row"
                    )
                statuses = inter_context_status_by_row.get(row_id, set())
                memberships = inter_context_ids_by_row.get(row_id, [])
                if len(statuses) > 1:
                    raise NativeTMObservationsError(
                        "outside-financial-span row has conflicting context dispositions"
                    )
                if page_disposition == "OUTSIDE_QUANTITATIVE_TM":
                    disposition = page_disposition
                elif statuses:
                    disposition = next(iter(statuses))
                else:
                    disposition = "OUTSIDE_FINANCIAL_SPAN_ROW"
                source_object_id = f"ROW::{row_id}"
                context_row_ids.append(row_id)
                rows.append(
                    {
                        "record_type": "ROW",
                        "source_object_id": source_object_id,
                        "source_disposition": disposition,
                        "row_source_kind": "OUTSIDE_FINANCIAL_SPAN_ROW",
                        "context_id": context_id,
                        "source_table_id": table_id,
                        "page_classification": page_classification,
                        "row_ordinal": len(region_rows) + outside_ordinal,
                        **copy.deepcopy(row),
                        "source_cells": [],
                        "observation_ids": [],
                        "value_bearing": False,
                        "inter_table_context_ids": copy.deepcopy(memberships),
                        "source_order": {
                            "page": page_number,
                            "source_container_kind": "TABLE_REGION",
                            "source_container_ordinal": region_ordinal - 1,
                            "row_ordinal_within_container": (len(region_rows) + outside_ordinal),
                            "cross_container_order_status": (
                                "NOT_SERIALIZED_BY_UPSTREAM_SOURCE_STAGE"
                            ),
                        },
                        "source_record_sha256": _canonical_record_sha256(row),
                    }
                )

            for scalar_ordinal, raw_scalar in enumerate(scalars):
                scalar = _as_object(raw_scalar, "native TM scalar disclosure")
                scalar_id = _as_string(scalar.get("scalar_id"), "native TM scalar ID")
                row_id = _as_string(scalar.get("source_row_id"), "native TM scalar row ID")
                if row_id in source_rows_by_id:
                    raise NativeTMObservationsError("native TM scalar row duplicates a region row")
                source_object_id = f"ROW::{row_id}"
                observation_id = f"OBSERVATION::SCALAR::{scalar_id}"
                context_row_ids.append(row_id)
                context_observation_ids.append(observation_id)
                scalar_disposition = (
                    page_disposition
                    if page_disposition == "OUTSIDE_QUANTITATIVE_TM"
                    else "QUANTITATIVE_TM_ROW_LOCAL_SCALAR"
                )
                rows.append(
                    {
                        "record_type": "ROW",
                        "source_object_id": source_object_id,
                        "source_disposition": scalar_disposition,
                        "row_source_kind": "ROW_LOCAL_SCALAR",
                        "context_id": context_id,
                        "source_table_id": table_id,
                        "page": page_number,
                        "page_classification": page_classification,
                        "row_id": row_id,
                        "row_ordinal": len(region_rows) + len(outside_rows) + scalar_ordinal,
                        "label": scalar.get("label"),
                        "label_boxes": copy.deepcopy(scalar.get("label_boxes")),
                        "source_scalar_id": scalar_id,
                        "source_cells": [],
                        "observation_ids": [observation_id],
                        "value_bearing": True,
                        "source_order": {
                            "page": page_number,
                            "source_container_kind": "TABLE_REGION",
                            "source_container_ordinal": region_ordinal - 1,
                            "row_ordinal_within_container": (
                                len(region_rows) + len(outside_rows) + scalar_ordinal
                            ),
                            "cross_container_order_status": (
                                "NOT_SERIALIZED_BY_UPSTREAM_SOURCE_STAGE"
                            ),
                        },
                        "source_record_sha256": _canonical_record_sha256(scalar),
                    }
                )
                source_status = _as_string(
                    scalar.get("source_status"), "native TM scalar source status"
                )
                scalar_kind = {
                    "OBSERVED_VALUE": "VALUE",
                    "OBSERVED_ZERO": "ZERO",
                    "DASH": "DASH",
                    "INVALID_SOURCE_MARKER": "INVALID",
                }.get(source_status)
                if scalar_kind is None:
                    raise NativeTMObservationsError(
                        f"unsupported native TM scalar source status: {source_status}"
                    )
                observations.append(
                    {
                        "record_type": "OBSERVATION",
                        "source_object_id": observation_id,
                        "source_disposition": page_disposition,
                        "observation_id": observation_id,
                        "observation_source_kind": "ROW_LOCAL_SCALAR",
                        "context_id": context_id,
                        "row_id": row_id,
                        "dimension_id": None,
                        "source_table_id": table_id,
                        "page_classification": page_classification,
                        **copy.deepcopy(scalar),
                        "observation_kind": scalar_kind,
                        "is_visible_source_marker": True,
                        "dimension_binding_materialized_on_observation": False,
                        "value_run_owner_id": run_owner_by_key.get(
                            (
                                page_number,
                                _as_string(
                                    scalar.get("value_run_id"),
                                    "native TM scalar value run ID",
                                ),
                            )
                        ),
                        "unit_run_owner_id": run_owner_by_key.get(
                            (
                                page_number,
                                _as_string(
                                    scalar.get("unit_run_id"),
                                    "native TM scalar unit run ID",
                                ),
                            )
                        ),
                        "source_scalar_record_sha256": _canonical_record_sha256(scalar),
                    }
                )

            header_run_references: list[dict[str, Any]] = []
            header_run_ids_seen: set[str] = set()
            for raw_header_run in _as_list(
                region.get("header_runs"), "native TM region header runs"
            ):
                header_run = _as_object(raw_header_run, "native TM region header run")
                header_run_id = _as_string(
                    header_run.get("run_id"), "native TM region header run ID"
                )
                if header_run_id in header_run_ids_seen:
                    raise NativeTMObservationsError(
                        "native TM region repeats a header-run reference"
                    )
                header_run_ids_seen.add(header_run_id)
                owner_id = run_owner_by_key.get((page_number, header_run_id))
                if owner_id != f"SOURCE_RUN::GEOMETRY::{table_id}::{header_run_id}":
                    raise NativeTMObservationsError(
                        "native TM header run is not owned by its region geometry"
                    )
                header_run_references.append(
                    {
                        "reference_id": (f"HEADER_RUN_REFERENCE::{table_id}::{header_run_id}"),
                        "run_id": header_run_id,
                        "source_owner_id": owner_id,
                        "source_run": copy.deepcopy(header_run),
                    }
                )
            context = {
                "record_type": "CONTEXT",
                "source_object_id": context_id,
                "source_disposition": page_disposition,
                "context_id": context_id,
                "source_table_id": table_id,
                "page": page_number,
                "page_classification": page_classification,
                "page_classification_evidence": copy.deepcopy(page.get("classification_evidence")),
                "table_order": region.get("table_order"),
                "region_ordinal": region_ordinal,
                "region_bbox": copy.deepcopy(region.get("region_bbox")),
                "acceptance_signals": copy.deepcopy(region.get("acceptance_signals")),
                "header_runs": copy.deepcopy(region.get("header_runs")),
                "header_run_references": header_run_references,
                "geometry_metadata": {
                    key: copy.deepcopy(value)
                    for key, value in geometry.items()
                    if key not in {"axes", "runs"}
                },
                "geometry_run_count": len(_as_list(geometry.get("runs"), "geometry runs")),
                "geometry_runs_sha256": _canonical_record_sha256(geometry.get("runs")),
                "row_ids": context_row_ids,
                "dimension_ids": dimension_ids,
                "observation_ids": context_observation_ids,
                "source_region_record_sha256": _canonical_record_sha256(region),
            }
            contexts.append(context)

            for run_ordinal, raw_run in enumerate(
                _as_list(region.get("detached_margin_runs"), "detached margin runs"),
                start=1,
            ):
                run = _as_object(raw_run, "native TM detached margin run")
                run_id = _as_string(run.get("run_id"), "native TM detached run ID")
                source_object_id = f"SOURCE_RUN::DETACHED::{table_id}::{run_id}"
                _register_run_owner(
                    run_owner_by_key,
                    page=page_number,
                    run_id=run_id,
                    source_object_id=source_object_id,
                )
                source_evidence["detached_margin_runs"].append(
                    _evidence_record(
                        record_type="SOURCE_RUN",
                        source_object_id=source_object_id,
                        source_disposition=(
                            page_disposition
                            if page_disposition == "OUTSIDE_QUANTITATIVE_TM"
                            else "PRESERVED_DETACHED_MARGIN_RUN"
                        ),
                        source_record=run,
                        extra={
                            "evidence_id": source_object_id,
                            "source_owner_kind": "DETACHED_MARGIN_RUN",
                            "context_id": context_id,
                            "page": page_number,
                            "run_id": run_id,
                            "run_ordinal": run_ordinal,
                        },
                    )
                )
            for run_ordinal, raw_run in enumerate(
                _as_list(region.get("unassigned_runs"), "region unassigned runs"),
                start=1,
            ):
                run = _as_object(raw_run, "native TM region-unassigned run")
                run_id = _as_string(run.get("run_id"), "native TM region-unassigned run ID")
                reference_id = (
                    f"SOURCE_RUN_REFERENCE::REGION_UNASSIGNED::{table_id}::{run_id}::"
                    f"{run_ordinal:03d}"
                )
                source_references["region_unassigned_runs"].append(
                    {
                        "record_type": "SOURCE_RUN_REFERENCE",
                        "reference_id": reference_id,
                        "context_id": context_id,
                        "page": page_number,
                        "run_id": run_id,
                        "owner_source_object_id": None,
                        "source_run": copy.deepcopy(run),
                        "source_record_sha256": _canonical_record_sha256(run),
                    }
                )

        for run_ordinal, raw_run in enumerate(
            _as_list(native_regions.get("unassigned_page_runs"), "unassigned page runs"),
            start=1,
        ):
            run = _as_object(raw_run, "native TM unassigned page run")
            run_id = _as_string(run.get("run_id"), "native TM unassigned page run ID")
            source_object_id = (
                f"UNASSIGNED_PAGE_RUN::page-{page_number:04d}::{run_id}::{run_ordinal:04d}"
            )
            _register_run_owner(
                run_owner_by_key,
                page=page_number,
                run_id=run_id,
                source_object_id=source_object_id,
            )
            source_evidence["unassigned_page_runs"].append(
                _evidence_record(
                    record_type="UNASSIGNED_PAGE_RUN",
                    source_object_id=source_object_id,
                    source_disposition=(
                        "PRESERVED_UNASSIGNED_PAGE_RUN"
                        if page_classification == "QUANTITATIVE_TM"
                        else "OUTSIDE_QUANTITATIVE_TM"
                    ),
                    source_record=run,
                    extra={"evidence_id": source_object_id, "page": page_number},
                )
            )
        for raw_span in _as_list(native_regions.get("excluded_spans"), "excluded native spans"):
            span = _as_object(raw_span, "excluded native span")
            span_page = _as_integer(span.get("page"), "excluded native span page")
            block_number = _as_integer(
                span.get("block_number"), "excluded native span block number"
            )
            line_number = _as_integer(span.get("line_number"), "excluded native span line number")
            span_number = _as_integer(span.get("span_number"), "excluded native span number")
            render_sequence = _as_integer(
                span.get("render_sequence"), "excluded native span render sequence"
            )
            natural_key = (
                span_page,
                block_number,
                line_number,
                span_number,
                render_sequence,
            )
            if span_page != page_number or natural_key in excluded_span_keys:
                raise NativeTMObservationsError(
                    "excluded native span natural identity is invalid or repeated"
                )
            excluded_span_keys.add(natural_key)
            source_object_id = (
                f"EXCLUDED_SPAN::page-{page_number:04d}::b{block_number}:"
                f"l{line_number}:s{span_number}:r{render_sequence}"
            )
            source_evidence["excluded_spans"].append(
                _evidence_record(
                    record_type="EXCLUDED_SPAN",
                    source_object_id=source_object_id,
                    source_disposition=(
                        "PRESERVED_EXCLUDED_NATIVE_SPAN"
                        if page_classification == "QUANTITATIVE_TM"
                        else "OUTSIDE_QUANTITATIVE_TM"
                    ),
                    source_record=span,
                    extra={"evidence_id": source_object_id, "page": page_number},
                )
            )
        for _diagnostic_ordinal, raw_diagnostic in enumerate(
            _as_list(
                native_regions.get("unit_group_diagnostics"),
                "native TM unit-group diagnostics",
            ),
            start=1,
        ):
            diagnostic = _as_object(raw_diagnostic, "native TM unit-group diagnostic")
            unit_run_ids = tuple(
                _as_string(run_id, "unit-group diagnostic run ID")
                for run_id in _as_list(
                    diagnostic.get("unit_run_ids"), "unit-group diagnostic run IDs"
                )
            )
            natural_key = (page_number, unit_run_ids)
            if natural_key in unit_diagnostic_keys:
                raise NativeTMObservationsError(
                    "native TM unit-group diagnostic repeats its natural identity"
                )
            unit_diagnostic_keys.add(natural_key)
            unit_run_owner_ids: list[str] = []
            for unit_run_id in unit_run_ids:
                owner_id = run_owner_by_key.get((page_number, unit_run_id))
                if owner_id is None:
                    raise NativeTMObservationsError(
                        "unit-group diagnostic run has no canonical source-run owner"
                    )
                unit_run_owner_ids.append(owner_id)
            source_object_id = (
                f"UNIT_GROUP_DIAGNOSTIC::page-{page_number:04d}::{'|'.join(unit_run_ids)}"
            )
            source_evidence["unit_group_diagnostics"].append(
                _evidence_record(
                    record_type="UNIT_GROUP_DIAGNOSTIC",
                    source_object_id=source_object_id,
                    source_disposition=(
                        "PRESERVED_UNIT_GROUP_DIAGNOSTIC"
                        if page_classification == "QUANTITATIVE_TM"
                        else "OUTSIDE_QUANTITATIVE_TM"
                    ),
                    source_record=diagnostic,
                    extra={
                        "evidence_id": source_object_id,
                        "page": page_number,
                        "page_classification": page_classification,
                        "unit_run_owner_ids": unit_run_owner_ids,
                    },
                )
            )

    for reference in source_references["region_unassigned_runs"]:
        owner_id = run_owner_by_key.get((reference["page"], reference["run_id"]))
        if owner_id is None:
            raise NativeTMObservationsError(
                "region-unassigned source run has no canonical source-run owner"
            )
        reference["owner_source_object_id"] = owner_id

    evidence_records = [record for records in source_evidence.values() for record in records]
    evidence_by_id = {record["source_object_id"]: record for record in evidence_records}
    page_inventory: list[dict[str, Any]] = []
    page_alias_keys: dict[str, set[tuple[int, str]]] = {
        "source_visible_tm_header_runs": set(),
        "source_visible_continuation_runs": set(),
        "source_visible_note_heading_candidates": set(),
    }
    for page in pages:
        page_number = _as_integer(page.get("page"), "native TM page number")
        page_classification = _as_string(
            page.get("classification"), "native TM page classification"
        )
        native_regions = _as_object(page.get("native_tm_regions"), "native TM page regions")
        page_views: dict[str, list[dict[str, Any]]] = {}
        for view_name in page_alias_keys:
            references: list[dict[str, Any]] = []
            for raw_run in _as_list(page.get(view_name), f"native TM {view_name}"):
                run = _as_object(raw_run, f"native TM {view_name} run")
                run_id = _as_string(run.get("run_id"), f"native TM {view_name} run ID")
                natural_key = (page_number, run_id)
                if natural_key in page_alias_keys[view_name]:
                    raise NativeTMObservationsError(
                        f"native TM {view_name} repeats a page/run natural identity"
                    )
                page_alias_keys[view_name].add(natural_key)
                owner_id = run_owner_by_key.get(natural_key)
                owner = evidence_by_id.get(owner_id) if owner_id is not None else None
                if owner is None or not _page_evidence_reference_matches(
                    run, owner.get("source_record", {})
                ):
                    raise NativeTMObservationsError(
                        f"native TM {view_name} does not reference one canonical run owner"
                    )
                references.append(
                    {
                        "reference_id": (
                            f"PAGE_RUN_REFERENCE::{view_name}::page-{page_number:04d}::{run_id}"
                        ),
                        "page": page_number,
                        "run_id": run_id,
                        "source_owner_id": owner_id,
                        "source_run": copy.deepcopy(run),
                    }
                )
            page_views[view_name] = references
        source_object_id = f"PAGE_CONTEXT::page-{page_number:04d}"
        page_inventory.append(
            {
                "record_type": "PAGE_CONTEXT",
                "source_object_id": source_object_id,
                "source_disposition": (
                    "QUANTITATIVE_TM"
                    if page_classification == "QUANTITATIVE_TM"
                    else "OUTSIDE_QUANTITATIVE_TM"
                ),
                "page_id": source_object_id,
                "page": page_number,
                "width_points": page.get("width_points"),
                "height_points": page.get("height_points"),
                "rotation": page.get("rotation"),
                "quality": copy.deepcopy(page.get("quality")),
                "visible_native_word_count": page.get("visible_native_word_count"),
                "visible_native_words_sha256": page.get("visible_native_words_sha256"),
                "classification": page_classification,
                "classification_status": page.get("classification_status"),
                "classification_evidence": copy.deepcopy(page.get("classification_evidence")),
                **page_views,
                "native_tm_region_assessment": {
                    "page": native_regions.get("page"),
                    "assessment_status": native_regions.get("assessment_status"),
                    "error": native_regions.get("error"),
                    "region_count": len(
                        _as_list(native_regions.get("regions"), "native TM page regions")
                    ),
                    "inter_table_context_count": len(
                        _as_list(
                            native_regions.get("inter_table_contexts"),
                            "native TM page inter-table contexts",
                        )
                    ),
                    "unit_group_diagnostic_count": len(
                        _as_list(
                            native_regions.get("unit_group_diagnostics"),
                            "native TM page unit diagnostics",
                        )
                    ),
                    "excluded_span_count": len(
                        _as_list(
                            native_regions.get("excluded_spans"),
                            "native TM page excluded spans",
                        )
                    ),
                    "unassigned_page_run_count": len(
                        _as_list(
                            native_regions.get("unassigned_page_runs"),
                            "native TM page unassigned runs",
                        )
                    ),
                },
                "region_context_ids": [
                    _context_id(_as_string(region.get("table_id"), "native TM table ID"))
                    for region in _as_list(native_regions.get("regions"), "native TM page regions")
                ],
                "source_page_record_sha256": _canonical_record_sha256(page),
            }
        )
    row_source_order_keys: set[tuple[int, str, int, int]] = set()
    row_ids: set[str] = set()
    context_row_ownership_keys: set[tuple[str, str]] = set()
    for row in rows:
        row_id = _as_string(row.get("row_id"), "native TM row identity")
        if row_id in row_ids:
            raise NativeTMObservationsError(
                "native TM upstream row identity is not globally unique"
            )
        row_ids.add(row_id)
        source_table_id = row.get("source_table_id")
        if row["row_source_kind"] == "INTER_TABLE_CONTEXT_ROW":
            inter_table_context_id = _as_string(
                row.get("inter_table_context_id"),
                "native TM context-row owner identity",
            )
            ownership_key = (inter_table_context_id, row_id)
            if source_table_id is not None or ownership_key in context_row_ownership_keys:
                raise NativeTMObservationsError(
                    "native TM context row has a fabricated or repeated table ownership"
                )
            context_row_ownership_keys.add(ownership_key)
        else:
            source_table_id = _as_string(
                source_table_id, "native TM table-owned row table identity"
            )
            if not row_id.startswith(f"{source_table_id}:"):
                raise NativeTMObservationsError(
                    "native TM table-owned row identity lacks its source-table prefix"
                )
        source_order = _as_object(row.get("source_order"), "native TM row source order")
        order_key = (
            _as_integer(source_order.get("page"), "native TM row order page"),
            _as_string(
                source_order.get("source_container_kind"),
                "native TM row order container kind",
            ),
            _as_integer(
                source_order.get("source_container_ordinal"),
                "native TM row order container ordinal",
            ),
            _as_integer(
                source_order.get("row_ordinal_within_container"),
                "native TM within-container row ordinal",
            ),
        )
        if (
            order_key[0] != row["page"]
            or min(order_key[2:]) < 0
            or order_key in row_source_order_keys
            or source_order.get("cross_container_order_status")
            != "NOT_SERIALIZED_BY_UPSTREAM_SOURCE_STAGE"
        ):
            raise NativeTMObservationsError(
                "native TM row source-order coordinates are invalid or repeated"
            )
        row_source_order_keys.add(order_key)

    grid_observation_keys: set[tuple[str, str]] = set()
    scalar_ids: set[str] = set()
    for observation in observations:
        if observation["observation_source_kind"] == "GRID_SLOT":
            grid_key = (
                _as_string(observation.get("row_id"), "native TM grid row identity"),
                _as_string(observation.get("axis_id"), "native TM grid axis identity"),
            )
            if grid_key in grid_observation_keys:
                raise NativeTMObservationsError(
                    "native TM grid observation natural identity is repeated"
                )
            grid_observation_keys.add(grid_key)
            continue
        scalar_id = _as_string(
            observation.get("scalar_id"), "native TM scalar observation identity"
        )
        source_table_id = _as_string(
            observation.get("source_table_id"),
            "native TM scalar source-table identity",
        )
        if scalar_id in scalar_ids or not scalar_id.startswith(f"{source_table_id}:"):
            raise NativeTMObservationsError(
                "native TM scalar identity is repeated or lacks its source-table prefix"
            )
        scalar_ids.add(scalar_id)
    primary_records = [*page_inventory, *contexts, *rows, *dimensions, *observations]
    all_accounted_records = [*primary_records, *evidence_records]
    source_dispositions = [_source_disposition_record(record) for record in all_accounted_records]
    source_dispositions.sort(
        key=lambda item: (item["source_object_type"], item["source_object_id"])
    )
    disposition_ids = [item["source_object_id"] for item in source_dispositions]
    if len(disposition_ids) != len(set(disposition_ids)):
        raise NativeTMObservationsError("native TM source object identity is not unique")
    disposition_by_id = {
        item["source_object_id"]: item["source_disposition"] for item in source_dispositions
    }
    for observation in observations:
        if observation["observation_source_kind"] == "GRID_SLOT":
            owner_id = observation.get("source_run_owner_id")
            if owner_id is None:
                if observation.get("source_run_id") is not None:
                    raise NativeTMObservationsError(
                        "native TM grid-slot source run lost its canonical owner"
                    )
                continue
            owner = evidence_by_id.get(owner_id)
            source_run = owner.get("source_record") if owner is not None else None
            if not isinstance(source_run, dict) or (
                source_run.get("run_id") != observation.get("source_run_id")
                or source_run.get("raw_text") != observation.get("raw_text")
                or source_run.get("bbox") != observation.get("source_bbox")
            ):
                raise NativeTMObservationsError(
                    "native TM grid-slot source-run foreign key is not exact"
                )
            continue
        value_owner = evidence_by_id.get(observation.get("value_run_owner_id"))
        unit_owner = evidence_by_id.get(observation.get("unit_run_owner_id"))
        value_run = value_owner.get("source_record") if value_owner is not None else None
        unit_run = unit_owner.get("source_record") if unit_owner is not None else None
        if not isinstance(value_run, dict) or (
            value_run.get("run_id") != observation.get("value_run_id")
            or value_run.get("raw_text") != observation.get("raw_text")
            or value_run.get("bbox") != observation.get("value_bbox")
        ):
            raise NativeTMObservationsError("native TM scalar value-run foreign key is not exact")
        if not isinstance(unit_run, dict) or (
            unit_run.get("run_id") != observation.get("unit_run_id")
            or unit_run.get("raw_text") != observation.get("unit_raw_text")
            or unit_run.get("bbox") != observation.get("unit_bbox")
        ):
            raise NativeTMObservationsError("native TM scalar unit-run foreign key is not exact")
    expected_accepted_unit_groups: Counter[tuple[int, tuple[str, ...]]] = Counter()
    for context in contexts:
        expected_accepted_unit_groups[
            (
                context["page"],
                tuple(
                    _as_string(run_id, "native TM geometry unit run ID")
                    for run_id in _as_list(
                        context["geometry_metadata"].get("unit_run_ids"),
                        "native TM geometry unit run IDs",
                    )
                ),
            )
        ] += 1
    actual_accepted_unit_groups: Counter[tuple[int, tuple[str, ...]]] = Counter()
    for diagnostic_record in source_evidence["unit_group_diagnostics"]:
        diagnostic = diagnostic_record["source_record"]
        unit_run_ids = diagnostic.get("unit_run_ids")
        unit_texts = diagnostic.get("unit_texts")
        owner_ids = diagnostic_record["unit_run_owner_ids"]
        if (
            not isinstance(unit_run_ids, list)
            or not isinstance(unit_texts, list)
            or len(unit_run_ids) != len(unit_texts)
            or len(unit_run_ids) != len(owner_ids)
        ):
            raise NativeTMObservationsError(
                "native TM unit-group diagnostic evidence shape is invalid"
            )
        for run_id, unit_text, owner_id in zip(unit_run_ids, unit_texts, owner_ids, strict=True):
            owner = evidence_by_id.get(owner_id)
            source_run = owner.get("source_record") if owner is not None else None
            if not isinstance(source_run, dict) or (
                source_run.get("run_id") != run_id or source_run.get("raw_text") != unit_text
            ):
                raise NativeTMObservationsError(
                    "native TM unit-group diagnostic run foreign key is not exact"
                )
        accepted = diagnostic.get("accepted")
        if not isinstance(accepted, bool):
            raise NativeTMObservationsError(
                "native TM unit-group diagnostic acceptance is not boolean"
            )
        natural_group = (diagnostic_record["page"], tuple(unit_run_ids))
        if accepted:
            actual_accepted_unit_groups[natural_group] += 1
            if natural_group not in expected_accepted_unit_groups:
                raise NativeTMObservationsError(
                    "accepted unit-group diagnostic does not exactly equal one ordered "
                    "region geometry unit group"
                )
        elif natural_group in expected_accepted_unit_groups:
            raise NativeTMObservationsError(
                "region geometry unit group was reclassified as a rejected diagnostic"
            )
    if actual_accepted_unit_groups != expected_accepted_unit_groups:
        raise NativeTMObservationsError(
            "accepted unit-group diagnostics do not map one-to-one to region geometry"
        )
    for reference in source_references["region_unassigned_runs"]:
        owner_id = reference["owner_source_object_id"]
        owner = evidence_by_id.get(owner_id)
        if owner is None or not _full_run_reference_matches(
            reference["source_run"], owner.get("source_record", {})
        ):
            raise NativeTMObservationsError(
                "region-unassigned source-run reference differs from its canonical owner"
            )
        reference["owner_source_disposition"] = disposition_by_id[owner_id]

    for dimension in dimensions:
        for component in dimension["header_components"]:
            expected_owner = run_owner_by_key.get((dimension["page"], component["run_id"]))
            if expected_owner != component["source_owner_id"]:
                raise NativeTMObservationsError(
                    "header component does not reference its canonical geometry-run owner"
                )
    for context in contexts:
        for reference in context["header_run_references"]:
            owner = evidence_by_id.get(reference["source_owner_id"])
            if owner is None or not _full_run_reference_matches(
                reference["source_run"], owner.get("source_record", {})
            ):
                raise NativeTMObservationsError(
                    "native TM context header does not reference its canonical run owner"
                )

    qualified_period_groups: dict[str, tuple[str, str]] = {}
    period_group_axis_use_count = 0
    raw_period_group_ids: set[str] = set()
    for dimension in dimensions:
        period_group_id = dimension.get("period_group_id")
        qualified_period_group_id = dimension.get("qualified_period_group_id")
        if period_group_id is None:
            if qualified_period_group_id is not None:
                raise NativeTMObservationsError(
                    "dimension fabricated a qualified period group without a source group"
                )
            continue
        period_group_id = _as_string(period_group_id, "native TM dimension period-group ID")
        expected_qualified = f"PERIOD_GROUP::{dimension['source_table_id']}::{period_group_id}"
        if qualified_period_group_id != expected_qualified:
            raise NativeTMObservationsError(
                "dimension period-group identity is not table-qualified"
            )
        natural_key = (dimension["source_table_id"], period_group_id)
        prior = qualified_period_groups.setdefault(expected_qualified, natural_key)
        if prior != natural_key:
            raise NativeTMObservationsError(
                "qualified period-group identity aliases multiple natural keys"
            )
        period_group_axis_use_count += 1
        raw_period_group_ids.add(period_group_id)

    expected_page_ids: list[str] = []
    expected_context_ids: list[str] = []
    expected_row_ids: list[str] = []
    expected_dimension_ids: list[str] = []
    expected_observation_ids: list[str] = []
    expected_run_keys: list[tuple[int, str]] = []
    expected_evidence_counts: Counter[str] = Counter()
    expected_region_unassigned_reference_count = 0
    for page in pages:
        page_number = page["page"]
        expected_page_ids.append(f"PAGE_CONTEXT::page-{page_number:04d}")
        native_regions = page["native_tm_regions"]
        expected_evidence_counts["inter_table_contexts"] += len(
            native_regions["inter_table_contexts"]
        )
        expected_evidence_counts["unassigned_page_runs"] += len(
            native_regions["unassigned_page_runs"]
        )
        expected_evidence_counts["excluded_spans"] += len(native_regions["excluded_spans"])
        expected_evidence_counts["unit_group_diagnostics"] += len(
            native_regions["unit_group_diagnostics"]
        )
        for run in native_regions["unassigned_page_runs"]:
            expected_run_keys.append((page_number, run["run_id"]))
        for inter_context in native_regions["inter_table_contexts"]:
            expected_row_ids.extend(f"ROW::{row_id}" for row_id in inter_context["source_row_ids"])
            expected_evidence_counts["inter_table_context_runs"] += len(inter_context["runs"])
            expected_run_keys.extend((page_number, run["run_id"]) for run in inter_context["runs"])
        for region in native_regions["regions"]:
            table_id = region["table_id"]
            expected_context_ids.append(_context_id(table_id))
            expected_row_ids.extend(f"ROW::{row['row_id']}" for row in region["rows"])
            expected_row_ids.extend(
                f"ROW::{row['row_id']}" for row in region["outside_financial_span_rows"]
            )
            expected_row_ids.extend(
                f"ROW::{scalar['source_row_id']}" for scalar in region["scalar_disclosures"]
            )
            expected_dimension_ids.extend(
                _dimension_id(table_id, axis["axis_id"]) for axis in region["geometry"]["axes"]
            )
            expected_observation_ids.extend(
                _grid_observation_id(slot["row_id"], slot["axis_id"])
                for slot in region["grid_slots"]
            )
            expected_observation_ids.extend(
                f"OBSERVATION::SCALAR::{scalar['scalar_id']}"
                for scalar in region["scalar_disclosures"]
            )
            expected_evidence_counts["geometry_runs"] += len(region["geometry"]["runs"])
            expected_evidence_counts["detached_margin_runs"] += len(region["detached_margin_runs"])
            expected_region_unassigned_reference_count += len(region["unassigned_runs"])
            expected_run_keys.extend(
                (page_number, run["run_id"]) for run in region["geometry"]["runs"]
            )
            expected_run_keys.extend(
                (page_number, run["run_id"]) for run in region["detached_margin_runs"]
            )
    actual_primary_ids = {
        "PAGE_CONTEXT": [record["source_object_id"] for record in page_inventory],
        "CONTEXT": [record["source_object_id"] for record in contexts],
        "ROW": [record["source_object_id"] for record in rows],
        "DIMENSION": [record["source_object_id"] for record in dimensions],
        "OBSERVATION": [record["source_object_id"] for record in observations],
    }
    expected_primary_ids = {
        "PAGE_CONTEXT": expected_page_ids,
        "CONTEXT": expected_context_ids,
        "ROW": expected_row_ids,
        "DIMENSION": expected_dimension_ids,
        "OBSERVATION": expected_observation_ids,
    }
    for record_type, expected_ids in expected_primary_ids.items():
        actual_ids = actual_primary_ids[record_type]
        if (
            len(expected_ids) != len(set(expected_ids))
            or len(actual_ids) != len(set(actual_ids))
            or set(actual_ids) != set(expected_ids)
        ):
            raise NativeTMObservationsError(
                f"native TM {record_type.casefold()} source denominator is not exact"
            )
    for category, expected_count in expected_evidence_counts.items():
        if len(source_evidence[category]) != expected_count:
            raise NativeTMObservationsError(
                f"native TM {category} evidence denominator is not exact"
            )
    if len(source_references["region_unassigned_runs"]) != (
        expected_region_unassigned_reference_count
    ):
        raise NativeTMObservationsError(
            "native TM region-unassigned run-reference denominator is not exact"
        )
    if len(expected_run_keys) != len(set(expected_run_keys)) or set(expected_run_keys) != set(
        run_owner_by_key
    ):
        raise NativeTMObservationsError(
            "native TM canonical source-run owner partition is not exact"
        )

    owner_runs_by_page: dict[int, list[dict[str, Any]]] = {}
    for record in (
        *source_evidence["geometry_runs"],
        *source_evidence["detached_margin_runs"],
        *source_evidence["inter_table_context_runs"],
        *source_evidence["unassigned_page_runs"],
    ):
        owner_runs_by_page.setdefault(record["page"], []).append(record["source_record"])
    for page_record in page_inventory:
        word_indices = [
            index
            for run in owner_runs_by_page.get(page_record["page"], [])
            for index in _as_list(run.get("word_indices"), "native TM source-run word indices")
        ]
        visible_word_count = _as_integer(
            page_record.get("visible_native_word_count"), "visible native word count"
        )
        if (
            any(isinstance(index, bool) or not isinstance(index, int) for index in word_indices)
            or len(word_indices) != len(set(word_indices))
            or sorted(word_indices) != list(range(visible_word_count))
        ):
            raise NativeTMObservationsError(
                "native TM canonical source runs do not partition every visible word"
            )

    upstream_completeness = _as_object(
        document.get("completeness"), "native TM document completeness"
    )
    page_classification_counts = Counter(record["classification"] for record in page_inventory)
    if (
        upstream_completeness.get("pdf_page_count") != len(page_inventory)
        or upstream_completeness.get("page_classification_record_count") != len(page_inventory)
        or upstream_completeness.get("classification_counts")
        != {
            key: page_classification_counts[key]
            for key in ("QUANTITATIVE_TM", "QUALITATIVE_TM_CONTEXT", "NON_TM", "UNASSESSED")
        }
    ):
        raise NativeTMObservationsError(
            "native TM page inventory differs from upstream completeness"
        )
    upstream_table_inventory = _as_object(
        document.get("table_inventory"), "native TM upstream table inventory"
    )
    table_records = _as_list(
        upstream_table_inventory.get("records"), "native TM upstream table records"
    )
    table_by_id = {
        _as_string(record.get("table_id"), "upstream table ID"): record for record in table_records
    }
    if len(table_by_id) != len(table_records) or set(table_by_id) != {
        context["source_table_id"] for context in contexts
    }:
        raise NativeTMObservationsError(
            "native TM table contexts differ from the upstream table inventory"
        )
    for context in contexts:
        if table_by_id[context["source_table_id"]].get("region_record_sha256") != context.get(
            "source_region_record_sha256"
        ):
            raise NativeTMObservationsError(
                "native TM table context hash differs from upstream inventory"
            )
    upstream_inter_contexts = _as_list(
        upstream_table_inventory.get("inter_table_contexts"),
        "native TM upstream inter-table inventory",
    )
    projected_inter_contexts = source_evidence["inter_table_contexts"]
    projected_inter_by_key = {
        (
            record["source_record"]["page"],
            record["source_record"]["preceding_table_id"],
            record["source_record"]["following_table_id"],
        ): record
        for record in projected_inter_contexts
    }
    if len(projected_inter_by_key) != len(projected_inter_contexts) or len(
        upstream_inter_contexts
    ) != len(projected_inter_contexts):
        raise NativeTMObservationsError(
            "native TM inter-table contexts differ from upstream inventory"
        )
    for record in upstream_inter_contexts:
        key = (
            record.get("page"),
            record.get("preceding_table_id"),
            record.get("following_table_id"),
        )
        projected = projected_inter_by_key.get(key)
        if projected is None or record.get("context_record_sha256") != projected.get(
            "source_record_sha256"
        ):
            raise NativeTMObservationsError(
                "native TM inter-table context hash differs from upstream inventory"
            )

    upstream_note_inventory = _as_object(
        document.get("note_inventory"), "native TM upstream note inventory"
    )
    note_records = _as_list(
        upstream_note_inventory.get("records"), "native TM upstream note records"
    )
    note_alias_by_key = {
        (record["page"], record["run_id"]): record
        for page_record in page_inventory
        for record in page_record["source_visible_note_heading_candidates"]
    }
    if upstream_note_inventory.get("candidate_count") != len(note_records):
        raise NativeTMObservationsError("native TM upstream note inventory count drifted")
    for note in note_records:
        alias = note_alias_by_key.get((note.get("page"), note.get("source_run_id")))
        source_run = alias.get("source_run") if alias is not None else None
        if not isinstance(source_run, dict) or (
            source_run.get("raw_text") != note.get("raw_heading")
            or source_run.get("normalized_text") != note.get("normalized_heading")
            or source_run.get("bbox") != note.get("heading_bbox")
        ):
            raise NativeTMObservationsError(
                "native TM note inventory does not reference page source evidence"
            )

    quantitative_context_ids = {
        context["context_id"]
        for context in contexts
        if context["page_classification"] == "QUANTITATIVE_TM"
    }
    quantitative_rows = [row for row in rows if row["page_classification"] == "QUANTITATIVE_TM"]
    quantitative_dimensions = [
        dimension for dimension in dimensions if dimension["context_id"] in quantitative_context_ids
    ]
    quantitative_observations = [
        observation
        for observation in observations
        if observation["context_id"] in quantitative_context_ids
    ]
    quantitative_grid = [
        observation
        for observation in quantitative_observations
        if observation["observation_source_kind"] == "GRID_SLOT"
    ]
    quantitative_scalars = [
        observation
        for observation in quantitative_observations
        if observation["observation_source_kind"] == "ROW_LOCAL_SCALAR"
    ]
    quantitative_visible = [
        observation
        for observation in quantitative_observations
        if observation["is_visible_source_marker"] is True
    ]
    visible_status_counts = Counter(
        observation["source_status"] for observation in quantitative_visible
    )
    quantitative_grid_status_counts = Counter(
        observation["source_status"] for observation in quantitative_grid
    )
    quantitative_scalar_status_counts = Counter(
        observation["source_status"] for observation in quantitative_scalars
    )
    quantitative_position_status_counts = (
        quantitative_grid_status_counts + quantitative_scalar_status_counts
    )
    all_grid_status_counts = Counter(
        observation["source_status"]
        for observation in observations
        if observation["observation_source_kind"] == "GRID_SLOT"
    )
    all_scalars = [
        observation
        for observation in observations
        if observation["observation_source_kind"] == "ROW_LOCAL_SCALAR"
    ]
    all_scalar_status_counts = Counter(observation["source_status"] for observation in all_scalars)
    all_position_status_counts = all_grid_status_counts + all_scalar_status_counts
    all_visible_observations = [
        observation
        for observation in observations
        if observation["is_visible_source_marker"] is True
    ]
    observations_by_dimension: Counter[str] = Counter(
        observation["dimension_id"]
        for observation in quantitative_grid
        if isinstance(observation.get("dimension_id"), str)
    )
    visible_by_dimension: Counter[str] = Counter(
        observation["dimension_id"]
        for observation in quantitative_grid
        if observation["is_visible_source_marker"] is True
        and isinstance(observation.get("dimension_id"), str)
    )
    period_row_dependent_ids = {
        dimension["dimension_id"]
        for dimension in quantitative_dimensions
        if dimension["period_scope"] == "ROW_DEPENDENT"
    }
    period_unresolved_ids = {
        dimension["dimension_id"]
        for dimension in quantitative_dimensions
        if dimension["period_scope"] == "UNRESOLVED"
    }
    unit_row_dependent_ids = {
        dimension["dimension_id"]
        for dimension in quantitative_dimensions
        if dimension["unit_scope"] == "ROW_DEPENDENT"
    }
    conflict_dimension_ids = {
        dimension["dimension_id"]
        for dimension in quantitative_dimensions
        if dimension["binding_status"] == "RESOLVED_WITH_SOURCE_CONFLICT"
    }
    unit_diagnostic_records = source_evidence["unit_group_diagnostics"]
    quantitative_unit_diagnostics = [
        record
        for record in unit_diagnostic_records
        if record.get("page_classification") == "QUANTITATIVE_TM"
    ]
    region_header_alias_keys = {
        (context["page"], reference["run_id"])
        for context in contexts
        for reference in context["header_run_references"]
    }
    region_header_reference_count = sum(
        len(context["header_run_references"]) for context in contexts
    )
    binding_reference_count = sum(len(dimension["header_components"]) for dimension in dimensions)
    binding_alias_keys = {
        (dimension["page"], component["run_id"])
        for dimension in dimensions
        for component in dimension["header_components"]
    }
    all_alias_keys = set().union(
        region_header_alias_keys,
        binding_alias_keys,
        *page_alias_keys.values(),
    )
    upstream_completeness = _as_object(
        document.get("completeness"), "native TM document completeness"
    )
    unresolved_context_count = sum(
        record["source_record"].get("ownership_status") != "BOUNDED_INTER_TABLE_OWNERSHIP"
        for record in source_evidence["inter_table_contexts"]
    )
    source_accounting = {
        "source_object_accounting_complete": True,
        "full_document_context_complete": upstream_completeness.get("full_document_complete")
        is True,
        "quantitative_observation_status": (
            "COMPLETE_SOURCE_VISIBLE_QUANTITATIVE_OBSERVATION_ACCOUNTING"
        ),
        "document_context_status": (
            "COMPLETE_UPSTREAM_DOCUMENT_CONTEXT"
            if upstream_completeness.get("full_document_complete") is True
            else "INCOMPLETE_OR_UNRESOLVED_UPSTREAM_DOCUMENT_CONTEXT"
        ),
        "upstream_artifact_status": document["status"],
        "unresolved_inter_table_context_count": unresolved_context_count,
        "counts": {
            "context_record_count": len(contexts),
            "row_record_count": len(rows),
            "dimension_record_count": len(dimensions),
            "observation_record_count": len(observations),
            "page_record_count": len(page_inventory),
            "source_evidence_record_count": len(evidence_records),
            "source_disposition_count": len(source_dispositions),
            "quantitative_context_count": len(quantitative_context_ids),
            "outside_quantitative_tm_context_count": len(contexts) - len(quantitative_context_ids),
            "quantitative_region_row_count": sum(
                row["row_source_kind"] == "REGION_ROW" for row in quantitative_rows
            ),
            "quantitative_outside_financial_span_row_count": sum(
                row["row_source_kind"] == "OUTSIDE_FINANCIAL_SPAN_ROW" for row in quantitative_rows
            ),
            "quantitative_scalar_row_count": sum(
                row["row_source_kind"] == "ROW_LOCAL_SCALAR" for row in quantitative_rows
            ),
            "quantitative_inter_table_context_row_count": sum(
                row["row_source_kind"] == "INTER_TABLE_CONTEXT_ROW" for row in quantitative_rows
            ),
            "quantitative_value_bearing_row_count": sum(
                row["value_bearing"] for row in quantitative_rows
            ),
            "quantitative_dimension_count": len(quantitative_dimensions),
            "quantitative_grid_slot_count": len(quantitative_grid),
            "quantitative_observation_position_count": len(quantitative_observations),
            "quantitative_visible_observation_count": len(quantitative_visible),
            "quantitative_invalid_source_marker_count": visible_status_counts[
                "INVALID_SOURCE_MARKER"
            ],
            "row_local_scalar_observation_count": len(quantitative_scalars),
            "all_observation_position_count": len(observations),
            "all_visible_observation_count": len(all_visible_observations),
            "geometry_source_run_count": len(source_evidence["geometry_runs"]),
            "detached_margin_source_run_count": len(source_evidence["detached_margin_runs"]),
            "inter_table_context_source_run_count": len(
                source_evidence["inter_table_context_runs"]
            ),
            "unassigned_page_source_run_count": len(source_evidence["unassigned_page_runs"]),
            "canonical_source_run_count": len(run_owner_by_key),
            "region_unassigned_run_reference_count": len(
                source_references["region_unassigned_runs"]
            ),
            "unit_group_diagnostic_count": len(unit_diagnostic_records),
            "accepted_unit_group_diagnostic_count": sum(
                record["source_record"].get("accepted") is True
                for record in unit_diagnostic_records
            ),
            "rejected_unit_group_diagnostic_count": sum(
                record["source_record"].get("accepted") is False
                for record in unit_diagnostic_records
            ),
            "quantitative_unit_group_diagnostic_count": len(quantitative_unit_diagnostics),
            "quantitative_accepted_unit_group_diagnostic_count": sum(
                record["source_record"].get("accepted") is True
                for record in quantitative_unit_diagnostics
            ),
            "quantitative_rejected_unit_group_diagnostic_count": sum(
                record["source_record"].get("accepted") is False
                for record in quantitative_unit_diagnostics
            ),
        },
        "quantitative_visible_source_status_counts": {
            status: visible_status_counts[status]
            for status in (
                "OBSERVED_VALUE",
                "OBSERVED_ZERO",
                "DASH",
                "INVALID_SOURCE_MARKER",
            )
        },
        "quantitative_grid_slot_source_status_counts": {
            status: quantitative_grid_status_counts[status]
            for status in (
                "OBSERVED_VALUE",
                "OBSERVED_ZERO",
                "DASH",
                "INVALID_SOURCE_MARKER",
                "BLANK",
                "UNRESOLVED_EMPTY_SLOT",
            )
        },
        "quantitative_scalar_source_status_counts": {
            status: quantitative_scalar_status_counts[status]
            for status in (
                "OBSERVED_VALUE",
                "OBSERVED_ZERO",
                "DASH",
                "INVALID_SOURCE_MARKER",
            )
        },
        "quantitative_position_source_status_counts": {
            status: quantitative_position_status_counts[status]
            for status in (
                "OBSERVED_VALUE",
                "OBSERVED_ZERO",
                "DASH",
                "INVALID_SOURCE_MARKER",
                "BLANK",
                "UNRESOLVED_EMPTY_SLOT",
            )
        },
        "all_grid_slot_source_status_counts": {
            status: all_grid_status_counts[status]
            for status in (
                "OBSERVED_VALUE",
                "OBSERVED_ZERO",
                "DASH",
                "INVALID_SOURCE_MARKER",
                "BLANK",
                "UNRESOLVED_EMPTY_SLOT",
            )
        },
        "all_position_source_status_counts": {
            status: all_position_status_counts[status]
            for status in (
                "OBSERVED_VALUE",
                "OBSERVED_ZERO",
                "DASH",
                "INVALID_SOURCE_MARKER",
                "BLANK",
                "UNRESOLVED_EMPTY_SLOT",
            )
        },
        "binding_accounting": {
            "period_row_dependent_dimension_count": len(period_row_dependent_ids),
            "period_row_dependent_position_count": sum(
                observations_by_dimension[dimension_id] for dimension_id in period_row_dependent_ids
            ),
            "period_row_dependent_visible_observation_count": sum(
                visible_by_dimension[dimension_id] for dimension_id in period_row_dependent_ids
            ),
            "period_unresolved_dimension_count": len(period_unresolved_ids),
            "period_unresolved_position_count": sum(
                observations_by_dimension[dimension_id] for dimension_id in period_unresolved_ids
            ),
            "period_unresolved_visible_observation_count": sum(
                visible_by_dimension[dimension_id] for dimension_id in period_unresolved_ids
            ),
            "unit_row_dependent_dimension_count": len(unit_row_dependent_ids),
            "unit_row_dependent_position_count": sum(
                observations_by_dimension[dimension_id] for dimension_id in unit_row_dependent_ids
            ),
            "unit_row_dependent_visible_observation_count": sum(
                visible_by_dimension[dimension_id] for dimension_id in unit_row_dependent_ids
            ),
            "source_conflict_dimension_count": len(conflict_dimension_ids),
            "source_conflict_position_count": sum(
                observations_by_dimension[dimension_id] for dimension_id in conflict_dimension_ids
            ),
        },
        "source_run_alias_accounting": {
            "region_header_reference_count": region_header_reference_count,
            "binding_source_run_reference_count": binding_reference_count,
            "source_visible_tm_header_reference_count": len(
                page_alias_keys["source_visible_tm_header_runs"]
            ),
            "source_visible_continuation_reference_count": len(
                page_alias_keys["source_visible_continuation_runs"]
            ),
            "source_visible_note_heading_reference_count": len(
                page_alias_keys["source_visible_note_heading_candidates"]
            ),
            "unique_alias_page_run_count": len(all_alias_keys),
            "every_alias_references_one_canonical_source_run_owner": True,
        },
        "period_group_accounting": {
            "axis_use_count": period_group_axis_use_count,
            "qualified_natural_group_count": len(qualified_period_groups),
            "unqualified_source_id_count": len(raw_period_group_ids),
            "natural_key_fields": ["source_table_id", "period_group_id"],
            "qualified_identity_is_lossless": True,
        },
        "source_identity_accounting": {
            "globally_unique_upstream_row_id_count": len(row_ids),
            "globally_unique_upstream_scalar_id_count": len(scalar_ids),
            "unique_grid_observation_natural_key_count": len(grid_observation_keys),
            "unique_context_row_ownership_key_count": len(context_row_ownership_keys),
            "table_owned_id_prefix_consistency": True,
            "context_rows_have_no_fabricated_table_owner": True,
        },
        "reconciliations": {
            "every_context_has_one_disposition": True,
            "every_page_has_one_disposition": True,
            "every_row_has_one_disposition": True,
            "every_dimension_has_one_disposition": True,
            "every_observation_has_one_disposition": True,
            "every_preserved_evidence_record_has_one_disposition": True,
            "source_disposition_identity_is_unique": True,
            "canonical_source_run_owner_identity_is_unique": True,
            "canonical_source_runs_partition_every_visible_word": True,
            "region_unassigned_runs_reference_one_canonical_owner": True,
            "page_inventory_equals_upstream_page_denominator": True,
            "table_contexts_equal_upstream_table_inventory": True,
            "inter_table_contexts_equal_upstream_table_inventory": True,
            "note_inventory_references_page_source_evidence": True,
            "grid_cells_join_one_to_one_to_visible_slots": True,
            "row_dependent_bindings_not_materialized_on_observations": True,
            "unresolved_bindings_not_coerced": True,
        },
    }

    source = copy.deepcopy(document["source"])
    source_path = _canonical_relative_path(source["relative_path"], "native TM source path")
    policy_payload = copy.deepcopy(dict(policy))
    report_scope_binding = _scope_binding(pages, policy)
    if report_scope_binding["binding_status"] != ("RESOLVED_UNANIMOUS_SOURCE_VISIBLE_TM_HEADERS"):
        raise NativeTMObservationsError(
            "source-visible TM report scope is absent, unclassified, or conflicting"
        )
    for evidence in report_scope_binding["evidence_runs"]:
        run = evidence["source_run"]
        owner_id = run_owner_by_key.get((evidence["page"], run.get("run_id")))
        owner = evidence_by_id.get(owner_id) if owner_id is not None else None
        if owner is None or not _page_evidence_reference_matches(
            run, owner.get("source_record", {})
        ):
            raise NativeTMObservationsError(
                "report-scope header does not reference one canonical source-run owner"
            )
        evidence["source_owner_id"] = owner_id
        evidence["source_owner_disposition"] = disposition_by_id[owner_id]
    inherited_upstream_replay_provenance = {
        "inputs": copy.deepcopy(document["inputs"]),
        "inputs_sha256": _canonical_record_sha256(document["inputs"]),
        "implementation": copy.deepcopy(document["code"]["implementation"]),
        "implementation_sha256": _canonical_record_sha256(document["code"]["implementation"]),
        "producer_snapshots": copy.deepcopy(document["producer_snapshots"]),
        "producer_snapshots_sha256": _canonical_record_sha256(document["producer_snapshots"]),
        "inventories": {
            "completeness": copy.deepcopy(document["completeness"]),
            "completeness_sha256": _canonical_record_sha256(document["completeness"]),
            "note_inventory": copy.deepcopy(document["note_inventory"]),
            "note_inventory_sha256": _canonical_record_sha256(document["note_inventory"]),
            "table_inventory": copy.deepcopy(document["table_inventory"]),
            "table_inventory_sha256": _canonical_record_sha256(document["table_inventory"]),
        },
    }
    payload: dict[str, Any] = {
        "format_version": _OUTPUT_FORMAT,
        "policy": _POLICY_NAME,
        "claim_boundary": _CLAIM_BOUNDARY,
        "status": _STATUS,
        "run_id": artifact_run_id,
        "source": source,
        "native_tm_document": {
            **copy.deepcopy(dict(native_document_identity)),
            "format_version": document["format_version"],
            "policy": document["policy"],
            "claim_boundary": document["claim_boundary"],
            "status": document["status"],
            "run_id": document["run_id"],
            "producer_git_commit": document["code"]["commit"],
        },
        "code": {
            "commit": producer_commit,
            "dirty": False,
            "implementation": copy.deepcopy(list(implementation)),
        },
        "authority": {
            "source_document": "STRICT_TRUSTED_SHA_NATIVE_TM_DOCUMENT_ARTIFACT",
            "table_contexts": "UPSTREAM_SOURCE_VISIBLE_NATIVE_TM_REGIONS",
            "rows": "UPSTREAM_SOURCE_VISIBLE_REGION_AND_ROW_OWNERSHIP",
            "dimensions": "UPSTREAM_SOURCE_AXES_AND_HEADER_BINDINGS",
            "observations": "UPSTREAM_GRID_SLOTS_AND_ROW_LOCAL_SCALARS",
            "report_scope": "GENERIC_SOURCE_VISIBLE_TM_HEADER_TEXT",
            "schema": None,
            "aliases": None,
            "mapper": None,
            "semantic_reader": None,
        },
        "source_identity_contract": {
            "upstream_row_id_scope": "GLOBALLY_PRODUCER_QUALIFIED",
            "upstream_scalar_id_scope": "GLOBALLY_PRODUCER_QUALIFIED",
            "table_owned_id_prefix": "<source_table_id>:",
            "grid_observation_natural_key": ["row_id", "axis_id"],
            "scalar_observation_natural_key": ["scalar_id"],
            "context_row_ownership_natural_key": [
                "inter_table_context_id",
                "row_id",
            ],
            "context_row_table_owner_status": "NOT_FABRICATED",
        },
        "ordering": {
            "rows_list_position": "NON_AUTHORITATIVE_GROUPED_BY_EXTRACTION_PASS",
            "within_source_container_order": "AUTHORITATIVE",
            "cross_container_row_order": "NOT_SERIALIZED_BY_UPSTREAM_SOURCE_STAGE",
            "context_row_run_partition": "UNRESOLVED_CONTEXT_LEVEL_ONLY",
        },
        "isolation": {
            "prior_answer_artifacts_loaded": False,
            "historical_values_loaded": False,
            "role_a_outputs_loaded": False,
            "reference_outputs_loaded": False,
            "schema_inputs_loaded": False,
            "aliases_loaded": False,
            "mapping_inputs_loaded": False,
            "bank_identity_used_for_routing": False,
            "filename_identity_used_for_routing": False,
            "page_number_rules_used_for_routing": False,
            "note_number_rules_used_for_routing": False,
            "expected_counts_used_for_routing": False,
        },
        "non_decision_features": {
            "bank_identity": {
                "value": None,
                "status": "NOT_SERIALIZED_BY_NATIVE_TM_DOCUMENT",
                "usage": "PROVENANCE_ONLY",
                "used_for_routing": False,
            },
            "filename_identity": {
                "value": PurePosixPath(source_path).name,
                "usage": "PROVENANCE_ONLY",
                "used_for_routing": False,
            },
            "page_number": {
                "usage": "PROVENANCE_AND_STABLE_SOURCE_ID_ONLY",
                "used_for_routing": False,
            },
            "note_number": {
                "value": None,
                "usage": "PROVENANCE_ONLY",
                "used_for_routing": False,
            },
            "expected_counts": {
                "value": None,
                "usage": "POST_BUILD_REGRESSION_ONLY",
                "used_for_routing": False,
            },
        },
        "inputs": {
            "direct_runtime_input_ledger": runtime_inputs,
            "direct_runtime_input_ledger_sha256": _runtime_ledger_hash(runtime_inputs),
            "inherited_upstream_replay_provenance": inherited_upstream_replay_provenance,
        },
        "producer_snapshots": {
            "policy": {
                "path": policy_relative,
                "sha256": sha256_bytes(policy_bytes),
                "size_bytes": len(policy_bytes),
                "payload_sha256": _canonical_record_sha256(policy_payload),
                "payload": policy_payload,
            }
        },
        "report_scope_binding": report_scope_binding,
        "source_accounting": source_accounting,
        "page_inventory": page_inventory,
        "contexts": contexts,
        "rows": rows,
        "dimensions": dimensions,
        "observations": observations,
        "source_evidence": source_evidence,
        "source_references": source_references,
        "source_dispositions": source_dispositions,
    }
    return json.loads(_canonical_json_bytes(payload))


def build_registered_native_tm_observations(
    project_root: Path,
    native_tm_document_path: Path,
    native_tm_document_sha256: str,
    policy_path: Path,
    run_id: str,
) -> dict[str, Any]:
    """Strict-load and flatten one caller-supplied native TM document artifact."""

    project_root = project_root.resolve()
    native_tm_document_path, document_relative = _lexical_project_path(
        project_root, native_tm_document_path, "native TM document artifact"
    )
    policy_path, policy_relative = _lexical_project_path(
        project_root, policy_path, "native TM observations policy"
    )
    if _SHA256.fullmatch(native_tm_document_sha256) is None:
        raise NativeTMObservationsError("trusted native TM document SHA-256 is invalid")
    code = _current_git_state(project_root)
    policy = load_native_tm_observations_policy(policy_path, project_root)
    _validate_path_isolation([document_relative, policy_relative], policy)
    document_bytes = _read_guarded_project_file(
        project_root,
        native_tm_document_path,
        document_relative,
        "native TM document artifact",
    )
    if sha256_bytes(document_bytes) != native_tm_document_sha256:
        raise NativeTMObservationsError(
            "native TM document artifact does not match its trusted SHA-256"
        )
    try:
        native_document = _native_document.load_registered_native_tm_document_artifact(
            native_tm_document_path,
            project_root=project_root,
            expected_sha256=native_tm_document_sha256,
        )
    except _native_document.NativeTMDocumentArtifactError as exc:
        raise NativeTMObservationsError("strict native TM document artifact load failed") from exc
    policy_bytes = _read_guarded_project_file(
        project_root, policy_path, policy_relative, "native TM observations policy"
    )
    runtime_inputs = sorted(
        [
            _file_identity(native_tm_document_path, project_root, "NATIVE_TM_DOCUMENT_ARTIFACT"),
            _file_identity(policy_path, project_root, "THIS_POLICY"),
        ],
        key=lambda item: (item["kind"], item["path"]),
    )
    implementation = _implementation_ledger(project_root)
    committed_implementation = _implementation_ledger_at_commit(project_root, code["commit"])
    if implementation != committed_implementation:
        raise NativeTMObservationsError(
            "native TM observations implementation differs from the clean producer HEAD"
        )
    committed_policy = _file_identity_at_commit(
        project_root, code["commit"], policy_relative, kind="THIS_POLICY"
    )
    if next(item for item in runtime_inputs if item["kind"] == "THIS_POLICY") != committed_policy:
        raise NativeTMObservationsError(
            "native TM observations policy differs from the clean producer HEAD"
        )
    payload = _build_projection(
        native_document=native_document,
        native_document_identity={
            "path": document_relative,
            "sha256": native_tm_document_sha256,
            "size_bytes": len(document_bytes),
        },
        policy_relative=policy_relative,
        policy_bytes=policy_bytes,
        policy=policy,
        runtime_inputs=runtime_inputs,
        implementation=implementation,
        producer_commit=code["commit"],
        run_id=run_id,
    )
    if (
        _read_guarded_project_file(
            project_root,
            native_tm_document_path,
            document_relative,
            "native TM document artifact",
        )
        != document_bytes
    ):
        raise NativeTMObservationsError("native TM document artifact changed during build")
    if (
        _read_guarded_project_file(
            project_root, policy_path, policy_relative, "native TM observations policy"
        )
        != policy_bytes
    ):
        raise NativeTMObservationsError("native TM observations policy changed during build")
    if _implementation_ledger(project_root) != implementation:
        raise NativeTMObservationsError(
            "native TM observations implementation changed during build"
        )
    if _current_git_state(project_root) != code:
        raise NativeTMObservationsError("producer HEAD changed during native TM observations build")
    return payload


_PRODUCER_REPLAY_BOOTSTRAP = r"""
import pathlib
import sys

source_tree = pathlib.Path(sys.argv[1]).resolve()
repository = pathlib.Path(sys.argv[2]).resolve()
sys.path.insert(0, str(source_tree / "src"))
from bctc_ai.rows import native_tm_observations as producer

expected_module = (source_tree / "src/bctc_ai/rows/native_tm_observations.py").resolve()
if pathlib.Path(producer.__file__).resolve() != expected_module:
    raise RuntimeError("producer replay imported outside its isolated source tree")
payload = producer.build_registered_native_tm_observations(
    repository,
    repository / sys.argv[3],
    sys.argv[4],
    repository / producer.POLICY_RELATIVE_PATH,
    sys.argv[5],
)
sys.stdout.buffer.write(producer._canonical_json_bytes(payload))
"""


def _write_new_file(path: Path, payload: bytes, mode: int = 0o600) -> None:
    try:
        _native_document._write_new_file(path, payload, mode)
    except _native_document.NativeTMDocumentArtifactError as exc:
        raise NativeTMObservationsError(str(exc)) from exc


def _install_replay_input(clone_root: Path, relative: str, payload: bytes, label: str) -> None:
    destination = _resolve_under_root(clone_root, relative, label)
    if destination.exists():
        if _read_stable_bytes(destination, label) != payload:
            raise NativeTMObservationsError(f"producer-commit {label} differs from replay input")
        return
    _write_new_file(destination, payload)


def _isolated_subprocess_environment() -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
    }


def _run_checked_process(
    arguments: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    timeout: int = 900,
) -> bytes:
    try:
        result = subprocess.run(
            list(arguments),
            cwd=cwd,
            env=dict(environment),
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise NativeTMObservationsError(
            "native TM observations producer-commit replay process failed"
        ) from exc
    if result.returncode != 0:
        raise NativeTMObservationsError(
            "native TM observations producer-commit replay process failed"
        )
    return result.stdout


def _validate_replay_implementation(
    project_root: Path, code: Any
) -> tuple[str, list[dict[str, Any]]]:
    if (
        not isinstance(code, dict)
        or set(code) != {"commit", "dirty", "implementation"}
        or code.get("dirty") is not False
        or not isinstance(code.get("commit"), str)
        or _GIT_COMMIT.fullmatch(code["commit"]) is None
        or not isinstance(code.get("implementation"), list)
    ):
        raise NativeTMObservationsError("native TM observations producer identity is invalid")
    implementation = code["implementation"]
    if [item.get("path") for item in implementation if isinstance(item, dict)] != list(
        _IMPLEMENTATION_PATHS
    ):
        raise NativeTMObservationsError("native TM observations V1 implementation manifest drifted")
    expected = [
        _file_identity_at_commit(project_root, code["commit"], relative)
        for relative in _IMPLEMENTATION_PATHS
    ]
    if implementation != expected:
        raise NativeTMObservationsError(
            "native TM observations implementation is not bound to its producer commit"
        )
    return code["commit"], copy.deepcopy(implementation)


def _validate_artifact_location_and_policy(
    *,
    project_root: Path,
    producer_commit: str,
    payload: Mapping[str, Any],
    artifact_relative: str,
) -> dict[str, Any]:
    policy_bytes = _git_file_bytes(project_root, producer_commit, POLICY_RELATIVE_PATH.as_posix())
    producer_policy = _validate_policy_payload(
        _yaml_bytes(policy_bytes, "producer native TM observations policy")
    )
    expected_snapshot = {
        "path": POLICY_RELATIVE_PATH.as_posix(),
        "sha256": sha256_bytes(policy_bytes),
        "size_bytes": len(policy_bytes),
        "payload_sha256": _canonical_record_sha256(producer_policy),
        "payload": producer_policy,
    }
    snapshots = payload.get("producer_snapshots")
    if not isinstance(snapshots, dict) or snapshots != {"policy": expected_snapshot}:
        raise NativeTMObservationsError("native TM observations producer policy snapshot drifted")
    _validate_path_isolation([artifact_relative], producer_policy)
    return producer_policy


def _preflight_native_replay_lineage(
    *,
    project_root: Path,
    native_document_payload: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if (
        native_document_payload.get("format_version") != _NATIVE_DOCUMENT_FORMAT
        or native_document_payload.get("policy") != _NATIVE_DOCUMENT_POLICY
        or native_document_payload.get("claim_boundary") != _NATIVE_DOCUMENT_CLAIM
        or native_document_payload.get("status") not in _NATIVE_DOCUMENT_STATUSES
    ):
        raise NativeTMObservationsError("native TM replay input contract identity is invalid")
    code = _as_object(native_document_payload.get("code"), "native TM replay producer identity")
    native_producer_commit = _as_string(code.get("commit"), "native TM replay producer commit")
    if _GIT_COMMIT.fullmatch(native_producer_commit) is None or code.get("dirty") is not False:
        raise NativeTMObservationsError("native TM replay producer identity is invalid")
    policy_bytes = _git_file_bytes(
        project_root, native_producer_commit, _NATIVE_DOCUMENT_POLICY_PATH
    )
    native_policy = _yaml_bytes(policy_bytes, "native TM replay producer policy")
    if (
        native_policy.get("version") != 1
        or native_policy.get("policy") != _NATIVE_DOCUMENT_POLICY
        or native_policy.get("claim_boundary") != _NATIVE_DOCUMENT_CLAIM
        or native_policy.get("source_registry") != "data/registered/source_registry.jsonl"
        or native_policy.get("dataset_role_registry") != "data/registered/dataset_roles.jsonl"
        or native_policy.get("required_dataset_role") != _DATASET_ROLE
    ):
        raise NativeTMObservationsError("native TM replay producer registration policy is invalid")
    source_registry_path = native_policy["source_registry"]
    role_registry_path = native_policy["dataset_role_registry"]
    source_records = _jsonl_bytes(
        _git_file_bytes(project_root, native_producer_commit, source_registry_path),
        "native TM producer source registry",
    )
    role_records = _jsonl_bytes(
        _git_file_bytes(project_root, native_producer_commit, role_registry_path),
        "native TM producer dataset-role registry",
    )
    source = _as_object(native_document_payload.get("source"), "native TM replay source identity")
    source_relative = _canonical_relative_path(
        source.get("relative_path"), "native TM replay source path"
    )
    source_sha256 = _as_string(source.get("sha256"), "native TM replay source SHA-256")
    source_size = _as_integer(source.get("size_bytes"), "native TM replay source size")
    if (
        _SHA256.fullmatch(source_sha256) is None
        or source_size < 0
        or source.get("document_id") != f"sha256:{source_sha256}"
        or source.get("dataset_role") != _DATASET_ROLE
        or source.get("registry_state") != "REGISTERED"
        or source.get("hash_verified_stable") is not True
        or source.get("immutable_role_assignment") is not True
    ):
        raise NativeTMObservationsError("native TM replay source registration identity is invalid")
    matching_sources = [
        record for record in source_records if record.get("relative_path") == source_relative
    ]
    if len(matching_sources) != 1:
        raise NativeTMObservationsError(
            "native TM replay source is not uniquely registered at its producer commit"
        )
    source_record = matching_sources[0]
    if (
        source_record.get("document_id") != source["document_id"]
        or source_record.get("sha256") != source_sha256
        or source_record.get("size_bytes") != source_size
        or source_record.get("kind") != "PDF"
        or source_record.get("state") != "REGISTERED"
        or source_record.get("hash_verified_stable") is not True
        or source.get("source_registry_record_sha256") != _canonical_record_sha256(source_record)
    ):
        raise NativeTMObservationsError(
            "native TM replay source differs from its producer registry"
        )
    matching_roles = [
        record for record in role_records if record.get("document_id") == source["document_id"]
    ]
    if len(matching_roles) != 1:
        raise NativeTMObservationsError(
            "native TM replay source has no unique producer role assignment"
        )
    role_record = matching_roles[0]
    if (
        role_record.get("source_path") != source_relative
        or role_record.get("dataset_role") != _DATASET_ROLE
        or role_record.get("immutable") is not True
        or source.get("dataset_role_registry_record_sha256")
        != _canonical_record_sha256(role_record)
    ):
        raise NativeTMObservationsError(
            "native TM replay source role differs from its producer registry"
        )
    discovery = _as_object(
        native_document_payload.get("statement_discovery"), "native TM replay discovery"
    )
    discovery_relative = _canonical_relative_path(
        discovery.get("path"), "native TM replay discovery path"
    )
    discovery_sha256 = _as_string(discovery.get("sha256"), "native TM replay discovery SHA-256")
    discovery_size = _as_integer(discovery.get("size_bytes"), "native TM replay discovery size")
    if _SHA256.fullmatch(discovery_sha256) is None or discovery_size < 0:
        raise NativeTMObservationsError("native TM replay discovery identity is invalid")
    inputs = _as_object(native_document_payload.get("inputs"), "native TM replay inputs")
    ledger = _as_list(inputs.get("runtime_read_ledger"), "native TM replay input ledger")
    if (
        set(inputs) != {"runtime_read_ledger", "runtime_read_ledger_sha256"}
        or any(
            not isinstance(record, dict) or set(record) != {"kind", "path", "sha256", "size_bytes"}
            for record in ledger
        )
        or ledger != sorted(ledger, key=lambda record: (record["kind"], record["path"]))
        or inputs.get("runtime_read_ledger_sha256") != _runtime_ledger_hash(ledger)
    ):
        raise NativeTMObservationsError(
            "native TM replay input ledger envelope or digest is invalid"
        )
    source_entries = [record for record in ledger if record.get("kind") == "SOURCE_PDF"]
    discovery_entries = [
        record for record in ledger if record.get("kind") == "ACCEPTED_STATEMENT_DISCOVERY"
    ]
    registry_entries = [record for record in ledger if record.get("kind") == "SOURCE_REGISTRY"]
    role_entries = [record for record in ledger if record.get("kind") == "DATASET_ROLE_REGISTRY"]
    expected_source_entry = {
        "kind": "SOURCE_PDF",
        "path": source_relative,
        "sha256": source_sha256,
        "size_bytes": source_size,
    }
    expected_discovery_entry = {
        "kind": "ACCEPTED_STATEMENT_DISCOVERY",
        "path": discovery_relative,
        "sha256": discovery_sha256,
        "size_bytes": discovery_size,
    }
    if (
        source_entries != [expected_source_entry]
        or discovery_entries != [expected_discovery_entry]
        or registry_entries
        != [
            _file_identity_at_commit(
                project_root,
                native_producer_commit,
                source_registry_path,
                kind="SOURCE_REGISTRY",
            )
        ]
        or role_entries
        != [
            _file_identity_at_commit(
                project_root,
                native_producer_commit,
                role_registry_path,
                kind="DATASET_ROLE_REGISTRY",
            )
        ]
    ):
        raise NativeTMObservationsError(
            "native TM replay transitive paths are not authenticated by its producer ledger"
        )
    return copy.deepcopy(source), copy.deepcopy(discovery)


def _producer_commit_replay(
    *,
    project_root: Path,
    producer_commit: str,
    implementation: Sequence[dict[str, Any]],
    native_document_relative: str,
    native_document_bytes: bytes,
    native_document_sha256: str,
    native_document_payload: Mapping[str, Any],
    producer_policy: Mapping[str, Any],
    run_id: str,
) -> bytes:
    source, discovery = _preflight_native_replay_lineage(
        project_root=project_root,
        native_document_payload=native_document_payload,
    )
    source_relative = _canonical_relative_path(
        source.get("relative_path"), "native TM replay source path"
    )
    discovery_relative = _canonical_relative_path(
        discovery.get("path"), "native TM replay discovery path"
    )
    _validate_path_isolation(
        [source_relative, discovery_relative, native_document_relative], producer_policy
    )
    if not source_relative.casefold().endswith(".pdf"):
        raise NativeTMObservationsError("native TM replay source must be a PDF")
    if not discovery_relative.startswith(f"{_OUTPUT_DIRECTORY}/"):
        raise NativeTMObservationsError(
            "native TM replay discovery must stay under output/development"
        )
    source_path, _ = _lexical_project_path(
        project_root, Path(source_relative), "native TM replay source"
    )
    discovery_path, _ = _lexical_project_path(
        project_root, Path(discovery_relative), "native TM replay discovery"
    )
    try:
        source_guard = _native_document._open_artifact_read_guard(
            project_root, source_path, source_relative
        )
        try:
            discovery_guard = _native_document._open_artifact_read_guard(
                project_root, discovery_path, discovery_relative
            )
        except BaseException:
            _native_document._close_artifact_read_guard(source_guard)
            raise
    except _native_document.NativeTMDocumentArtifactError as exc:
        raise NativeTMObservationsError(
            "native TM transitive replay input path contains a symlink or is unreadable"
        ) from exc
    source_bytes = bytes(source_guard.payload)
    discovery_bytes = bytes(discovery_guard.payload)
    if (
        sha256_bytes(source_bytes) != source.get("sha256")
        or len(source_bytes) != source.get("size_bytes")
        or sha256_bytes(discovery_bytes) != discovery.get("sha256")
        or len(discovery_bytes) != discovery.get("size_bytes")
    ):
        _native_document._close_artifact_read_guard(discovery_guard)
        _native_document._close_artifact_read_guard(source_guard)
        raise NativeTMObservationsError(
            "native TM document transitive replay inputs are absent or drifted"
        )
    try:
        temporary_root = Path(tempfile.mkdtemp(prefix="native-tm-observations-replay-"))
    except BaseException:
        _native_document._close_artifact_read_guard(discovery_guard)
        _native_document._close_artifact_read_guard(source_guard)
        raise
    environment = _isolated_subprocess_environment()
    try:
        clone_root = temporary_root / "repository"
        _run_checked_process(
            (
                "git",
                "clone",
                "--quiet",
                "--no-checkout",
                "--no-hardlinks",
                "--",
                str(project_root),
                str(clone_root),
            ),
            cwd=temporary_root,
            environment=environment,
        )
        _run_checked_process(
            ("git", "checkout", "--quiet", "--detach", producer_commit),
            cwd=clone_root,
            environment=environment,
        )
        _install_replay_input(
            clone_root,
            native_document_relative,
            native_document_bytes,
            "native TM document artifact",
        )
        _install_replay_input(clone_root, source_relative, source_bytes, "native TM source PDF")
        _install_replay_input(
            clone_root,
            discovery_relative,
            discovery_bytes,
            "native TM statement discovery",
        )
        status = _run_checked_process(
            ("git", "status", "--porcelain", "--untracked-files=all"),
            cwd=clone_root,
            environment=environment,
        )
        if status.strip():
            raise NativeTMObservationsError(
                "producer-commit replay repository is not clean after input restoration"
            )
        replay_tree = temporary_root / "isolated-source"
        for record in implementation:
            relative = record["path"]
            _write_new_file(
                replay_tree.joinpath(*PurePosixPath(relative).parts),
                _git_file_bytes(project_root, producer_commit, relative),
            )
        replayed = _run_checked_process(
            (
                sys.executable,
                "-I",
                "-c",
                _PRODUCER_REPLAY_BOOTSTRAP,
                str(replay_tree),
                str(clone_root),
                native_document_relative,
                native_document_sha256,
                run_id,
            ),
            cwd=temporary_root,
            environment=environment,
        )
        try:
            _native_document._revalidate_artifact_read_guard(source_guard)
            _native_document._revalidate_artifact_read_guard(discovery_guard)
        except _native_document.NativeTMDocumentArtifactError as exc:
            raise NativeTMObservationsError(
                "native TM document transitive inputs changed during producer replay"
            ) from exc
        return replayed
    finally:
        _native_document._close_artifact_read_guard(discovery_guard)
        _native_document._close_artifact_read_guard(source_guard)
        try:
            shutil.rmtree(temporary_root, ignore_errors=True)
        except Exception:
            pass


def _load_registered_native_tm_observations_held(
    guard: Any,
    *,
    project_root: Path,
    expected_sha256: str,
    held_guards: list[Any],
) -> dict[str, Any]:
    encoded = guard.payload
    if sha256_bytes(encoded) != expected_sha256:
        raise NativeTMObservationsError(
            "native TM observations artifact does not match its trusted SHA-256"
        )
    try:
        payload = json.loads(encoded)
    except json.JSONDecodeError as exc:
        raise NativeTMObservationsError("native TM observations artifact is invalid JSON") from exc
    if not isinstance(payload, dict) or encoded != _canonical_json_bytes(payload):
        raise NativeTMObservationsError("native TM observations artifact is not canonical JSON")
    if payload.get("format_version") != _OUTPUT_FORMAT:
        raise NativeTMObservationsError("native TM observations artifact format is invalid")
    producer_commit, implementation = _validate_replay_implementation(
        project_root, payload.get("code")
    )
    producer_policy = _validate_artifact_location_and_policy(
        project_root=project_root,
        producer_commit=producer_commit,
        payload=payload,
        artifact_relative=guard.relative_path,
    )
    run_id = payload.get("run_id")
    native_identity = payload.get("native_tm_document")
    if (
        not isinstance(run_id, str)
        or _SAFE_RUN_ID.fullmatch(run_id) is None
        or not isinstance(native_identity, dict)
        or not isinstance(native_identity.get("path"), str)
        or not isinstance(native_identity.get("sha256"), str)
        or _SHA256.fullmatch(native_identity["sha256"]) is None
        or isinstance(native_identity.get("size_bytes"), bool)
        or not isinstance(native_identity.get("size_bytes"), int)
    ):
        raise NativeTMObservationsError("native TM observations replay provenance is invalid")
    native_relative = _canonical_relative_path(
        native_identity["path"], "native TM document artifact path"
    )
    _validate_path_isolation([native_relative], producer_policy)
    if not native_relative.startswith(f"{_OUTPUT_DIRECTORY}/"):
        raise NativeTMObservationsError(
            "native TM document artifact must stay under output/development"
        )
    native_path, _ = _lexical_project_path(
        project_root, Path(native_relative), "native TM document artifact"
    )
    try:
        native_guard = _native_document._open_artifact_read_guard(
            project_root, native_path, native_relative
        )
    except _native_document.NativeTMDocumentArtifactError as exc:
        raise NativeTMObservationsError(
            "native TM document artifact path contains a symlink or is unreadable"
        ) from exc
    held_guards.append(native_guard)
    native_bytes = bytes(native_guard.payload)
    if (
        len(native_bytes) != native_identity["size_bytes"]
        or sha256_bytes(native_bytes) != native_identity["sha256"]
    ):
        raise NativeTMObservationsError("native TM observations replay input is absent or drifted")
    try:
        native_payload = json.loads(native_bytes)
    except json.JSONDecodeError as exc:
        raise NativeTMObservationsError("native TM document replay input is invalid JSON") from exc
    if not isinstance(native_payload, dict) or native_bytes != _canonical_json_bytes(
        native_payload
    ):
        raise NativeTMObservationsError("native TM document replay input is not canonical JSON")
    native_code = _as_object(
        native_payload.get("code"), "native TM document replay producer identity"
    )
    runtime_inputs = payload.get("inputs")
    ledger = (
        runtime_inputs.get("direct_runtime_input_ledger")
        if isinstance(runtime_inputs, dict)
        else None
    )
    expected_ledger = sorted(
        [
            {
                "kind": "NATIVE_TM_DOCUMENT_ARTIFACT",
                "path": native_relative,
                "sha256": native_identity["sha256"],
                "size_bytes": native_identity["size_bytes"],
            },
            _file_identity_at_commit(
                project_root,
                producer_commit,
                POLICY_RELATIVE_PATH.as_posix(),
                kind="THIS_POLICY",
            ),
        ],
        key=lambda item: (item["kind"], item["path"]),
    )
    if (
        not isinstance(runtime_inputs, dict)
        or set(runtime_inputs)
        != {
            "direct_runtime_input_ledger",
            "direct_runtime_input_ledger_sha256",
            "inherited_upstream_replay_provenance",
        }
        or ledger != expected_ledger
        or runtime_inputs["direct_runtime_input_ledger_sha256"]
        != _runtime_ledger_hash(expected_ledger)
    ):
        raise NativeTMObservationsError("native TM observations runtime input ledger drifted")
    inherited = runtime_inputs["inherited_upstream_replay_provenance"]
    expected_inherited = {
        "inputs": copy.deepcopy(native_payload.get("inputs")),
        "inputs_sha256": _canonical_record_sha256(native_payload.get("inputs")),
        "implementation": copy.deepcopy(native_code.get("implementation")),
        "implementation_sha256": _canonical_record_sha256(native_code.get("implementation")),
        "producer_snapshots": copy.deepcopy(native_payload.get("producer_snapshots")),
        "producer_snapshots_sha256": _canonical_record_sha256(
            native_payload.get("producer_snapshots")
        ),
        "inventories": {
            "completeness": copy.deepcopy(native_payload.get("completeness")),
            "completeness_sha256": _canonical_record_sha256(native_payload.get("completeness")),
            "note_inventory": copy.deepcopy(native_payload.get("note_inventory")),
            "note_inventory_sha256": _canonical_record_sha256(native_payload.get("note_inventory")),
            "table_inventory": copy.deepcopy(native_payload.get("table_inventory")),
            "table_inventory_sha256": _canonical_record_sha256(
                native_payload.get("table_inventory")
            ),
        },
    }
    if inherited != expected_inherited:
        raise NativeTMObservationsError(
            "native TM observations inherited upstream provenance drifted"
        )
    replay_bytes = _producer_commit_replay(
        project_root=project_root,
        producer_commit=producer_commit,
        implementation=implementation,
        native_document_relative=native_relative,
        native_document_bytes=native_bytes,
        native_document_sha256=native_identity["sha256"],
        native_document_payload=native_payload,
        producer_policy=producer_policy,
        run_id=run_id,
    )
    if replay_bytes != encoded:
        raise NativeTMObservationsError(
            "native TM observations artifact differs from producer-commit deterministic replay"
        )
    try:
        _native_document._revalidate_artifact_read_guard(native_guard)
        _native_document._revalidate_artifact_read_guard(guard)
    except _native_document.NativeTMDocumentArtifactError as exc:
        raise NativeTMObservationsError(str(exc)) from exc
    return copy.deepcopy(payload)


def load_registered_native_tm_observations(
    path: Path,
    *,
    project_root: Path,
    expected_sha256: str,
) -> dict[str, Any]:
    """Trusted-SHA load using an fd-held isolated producer-commit replay."""

    project_root = project_root.resolve()
    path, relative = _lexical_project_path(
        project_root, path, "registered native TM observations artifact"
    )
    if _SHA256.fullmatch(expected_sha256) is None:
        raise NativeTMObservationsError("trusted native TM observations SHA-256 is invalid")
    if not relative.startswith(f"{_OUTPUT_DIRECTORY}/"):
        raise NativeTMObservationsError(
            "LOGIC_DEVELOPMENT native TM observations must stay under output/development"
        )
    try:
        guard = _native_document._open_artifact_read_guard(project_root, path, relative)
    except _native_document.NativeTMDocumentArtifactError as exc:
        raise NativeTMObservationsError(str(exc)) from exc
    held_guards = [guard]
    try:
        return _load_registered_native_tm_observations_held(
            guard,
            project_root=project_root,
            expected_sha256=expected_sha256,
            held_guards=held_guards,
        )
    finally:
        for held_guard in reversed(held_guards):
            _native_document._close_artifact_read_guard(held_guard)


def _rollback_publication(guard: Any, cause: BaseException) -> None:
    try:
        _native_document._rollback_publication(guard, cause)
    except _native_document.NativeTMDocumentArtifactError as exc:
        raise NativeTMObservationsError(str(exc)) from cause


def publish_registered_native_tm_observations(
    project_root: Path,
    native_tm_document_path: Path,
    native_tm_document_sha256: str,
    policy_path: Path,
    run_id: str,
    output_path: Path,
) -> NativeTMObservationsPublication:
    """Build, exclusively publish, strict-replay, and return one artifact."""

    project_root = project_root.resolve()
    output_path, output_relative = _lexical_project_path(
        project_root, output_path, "native TM observations output"
    )
    if not output_relative.startswith(f"{_OUTPUT_DIRECTORY}/"):
        raise NativeTMObservationsError(
            "LOGIC_DEVELOPMENT native TM observations output must stay under output/development"
        )
    policy = load_native_tm_observations_policy(policy_path, project_root)
    _validate_path_isolation([output_relative], policy)
    payload = build_registered_native_tm_observations(
        project_root,
        native_tm_document_path,
        native_tm_document_sha256,
        policy_path,
        run_id,
    )
    encoded = _canonical_json_bytes(payload)
    try:
        guard = _native_document._write_exclusive(project_root, output_path, encoded)
    except _native_document.NativeTMDocumentArtifactError as exc:
        raise NativeTMObservationsError(str(exc)) from exc
    digest = sha256_bytes(encoded)
    try:
        replayed = load_registered_native_tm_observations(
            output_path,
            project_root=project_root,
            expected_sha256=digest,
        )
        if replayed != payload:
            raise NativeTMObservationsError("published native TM observations replay drifted")
    except BaseException as exc:
        try:
            _rollback_publication(guard, exc)
        finally:
            _native_document._close_guard_best_effort(guard)
        raise
    _native_document._close_guard_best_effort(guard)
    return NativeTMObservationsPublication(
        path=output_path,
        sha256=digest,
        size_bytes=len(encoded),
        payload=payload,
    )


__all__ = [
    "POLICY_RELATIVE_PATH",
    "NativeTMObservationsError",
    "NativeTMObservationsPublication",
    "build_registered_native_tm_observations",
    "load_native_tm_observations_policy",
    "load_registered_native_tm_observations",
    "publish_registered_native_tm_observations",
]
