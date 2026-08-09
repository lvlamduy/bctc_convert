from __future__ import annotations

import copy
import errno
import json
import math
import os
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, is_dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any

import fitz
import yaml

from bctc_ai.core.hashing import sha256_bytes, sha256_file, stable_records_hash
from bctc_ai.core.text import retrieval_key
from bctc_ai.ocr.native_text_quality_v2 import (
    assess_native_text_quality_v2,
    load_native_text_quality_v2_config,
)
from bctc_ai.tables.geometry import build_text_runs, load_geometry_config
from bctc_ai.tables.native_tm_regions import (
    NativeTMPageRegions,
    NativeTMRegionError,
    discover_native_tm_regions,
    extract_visible_native_text_page,
    load_native_tm_region_policy,
    resolve_region_blank_slots,
)

POLICY_RELATIVE_PATH = Path("config/document_phase/native-tm-document-artifact-v1.yaml")

_POLICY_NAME = "REGISTERED_NATIVE_TM_FULL_DOCUMENT_ARTIFACT_V1"
_CLAIM_BOUNDARY = "SOURCE_VISIBLE_NATIVE_TM_INVENTORY_ONLY"
_OUTPUT_FORMAT = "REGISTERED_NATIVE_TM_FULL_DOCUMENT_ARTIFACT_RESULT_V1"
_COMPLETE_STATUS = "COMPLETE_NATIVE_TM_FULL_DOCUMENT_ARTIFACT"
_PARTIAL_STATUS = "PARTIAL_NATIVE_TM_FULL_DOCUMENT_ARTIFACT"
_DISCOVERY_FORMAT = "REGISTERED_NATIVE_TEXT_STATEMENT_DISCOVERY_RESULT_V1"
_DISCOVERY_POLICY = "REGISTERED_NATIVE_TEXT_STATEMENT_DISCOVERY_V1"
_DISCOVERY_CLAIM = "STATEMENT_PAGE_DISCOVERY_ONLY"
_DISCOVERY_STATUS = "ACCEPTED_NATIVE_TEXT_STATEMENT_DISCOVERY"
_DATASET_ROLE = "LOGIC_DEVELOPMENT"
_OUTPUT_DIRECTORY = "output/development"
_V1_FORBIDDEN_PATH_FRAGMENTS = (
    "/reference/",
    "/role-a/",
    "/role_a/",
    "/schema/",
    "/schemas/",
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
_DISCOVERY_PRODUCER_POLICY_PATH = "config/document_phase/native-statement-discovery-v1.yaml"
_DISCOVERY_CONFIG_PATHS = (
    "config/document_phase/statement-discovery-v3.yaml",
    "config/document_phase/statement-discovery-v4.yaml",
    "config/document_phase/statement-locator-v1.yaml",
    "config/document_phase/statement-locator-v2.yaml",
)
_CLASSIFICATIONS = (
    "QUANTITATIVE_TM",
    "QUALITATIVE_TM_CONTEXT",
    "NON_TM",
    "UNASSESSED",
)
_TM_CLASSIFICATIONS = frozenset(_CLASSIFICATIONS[:2])
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_CONFIG_KINDS = (
    "NATIVE_TM_REGION_POLICY",
    "GEOMETRY_CONFIG",
    "NATIVE_TEXT_QUALITY_CONFIG",
)
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
)
_V1_REPLAY_IMPLEMENTATION_PATHS = _IMPLEMENTATION_PATHS
_DISCOVERY_IMPLEMENTATION_PATHS = (
    "src/bctc_ai/ocr/pdf_text.py",
    "src/bctc_ai/ocr/native_text_quality_v2.py",
    "src/bctc_ai/document_phase/statement_locator.py",
    "src/bctc_ai/document_phase/statement_locator_v2.py",
    "src/bctc_ai/document_phase/multisignal_statement_discovery.py",
    "src/bctc_ai/document_phase/multisignal_statement_discovery_v4.py",
    "src/bctc_ai/document_phase/native_statement_discovery.py",
)


class NativeTMDocumentArtifactError(RuntimeError):
    """A registered full-document native TM artifact failed closed."""


@dataclass(frozen=True)
class NativeTMDocumentArtifactPublication:
    path: Path
    sha256: str
    size_bytes: int
    payload: dict[str, Any]


@dataclass(frozen=True)
class _ExclusivePublicationGuard:
    path: Path
    relative_path: str
    basename: str
    parent_descriptor: int
    output_descriptor: int
    identity: os.stat_result


@dataclass(frozen=True)
class _ArtifactReadGuard:
    project_root: Path
    path: Path
    relative_path: str
    basename: str
    parent_descriptor: int
    parent_identity: os.stat_result
    artifact_descriptor: int
    identity: os.stat_result
    payload: bytes


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
        raise NativeTMDocumentArtifactError("native TM artifact is not JSON-safe") from exc
    return (encoded + "\n").encode("utf-8")


def _canonical_record_sha256(value: Any) -> str:
    return sha256_bytes(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    )


def _json_value(value: Any) -> Any:
    if is_dataclass(value):
        return _json_value(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_value(child) for key, child in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(child) for child in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise NativeTMDocumentArtifactError("native TM evidence contains a non-finite number")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise NativeTMDocumentArtifactError(
        f"native TM evidence contains unsupported type {type(value).__name__}"
    )


def _canonical_relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise NativeTMDocumentArtifactError(f"{label} must be a canonical relative POSIX path")
    candidate = PurePosixPath(value)
    if (
        candidate.is_absolute()
        or re.match(r"^[A-Za-z]:", value)
        or candidate.as_posix() != value
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise NativeTMDocumentArtifactError(f"{label} must be a canonical relative POSIX path")
    return value


def _resolve_under_root(project_root: Path, raw_path: str | Path, label: str) -> Path:
    relative = _canonical_relative_path(Path(raw_path).as_posix(), label)
    resolved = (project_root / relative).resolve()
    try:
        resolved.relative_to(project_root)
    except ValueError as exc:
        raise NativeTMDocumentArtifactError(f"{label} escapes the project root") from exc
    return resolved


def _relative_path(project_root: Path, path: Path, label: str) -> str:
    try:
        relative = path.resolve().relative_to(project_root).as_posix()
    except ValueError as exc:
        raise NativeTMDocumentArtifactError(f"{label} must stay inside the project root") from exc
    return _canonical_relative_path(relative, label)


def _read_stable_bytes(path: Path, label: str) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise NativeTMDocumentArtifactError(f"cannot open {label}: {path}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise NativeTMDocumentArtifactError(f"{label} is not a regular file")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            block = os.read(descriptor, min(remaining, 1024 * 1024))
            if not block:
                raise NativeTMDocumentArtifactError(f"{label} was truncated while being read")
            chunks.append(block)
            remaining -= len(block)
        if os.read(descriptor, 1):
            raise NativeTMDocumentArtifactError(f"{label} grew while being read")
        payload = b"".join(chunks)
        after = os.fstat(descriptor)
        linked = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise NativeTMDocumentArtifactError(f"cannot read {label}: {path}") from exc
    finally:
        os.close(descriptor)
    before_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    linked_identity = (linked.st_dev, linked.st_ino, linked.st_size, linked.st_mtime_ns)
    if (
        before_identity != after_identity
        or after_identity != linked_identity
        or len(payload) != after.st_size
    ):
        raise NativeTMDocumentArtifactError(f"{label} changed while being read")
    return payload


def _read_jsonl_bytes(payload: bytes, label: str) -> list[dict[str, Any]]:
    try:
        lines = payload.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise NativeTMDocumentArtifactError(f"{label} is not UTF-8") from exc
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise NativeTMDocumentArtifactError(
                f"{label} line {line_number} is invalid JSON"
            ) from exc
        if not isinstance(record, dict):
            raise NativeTMDocumentArtifactError(f"{label} line {line_number} is not an object")
        records.append(record)
    return records


def _yaml_bytes(payload: bytes, label: str) -> dict[str, Any]:
    try:
        parsed = yaml.safe_load(payload.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise NativeTMDocumentArtifactError(f"cannot decode {label}") from exc
    if not isinstance(parsed, dict):
        raise NativeTMDocumentArtifactError(f"{label} must be a YAML object")
    return parsed


def _require_exact(value: Any, expected: Any, label: str) -> None:
    if value != expected:
        raise NativeTMDocumentArtifactError(f"{label} contract drifted")


def _validate_policy_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise NativeTMDocumentArtifactError("native TM document policy must be an object")
    expected_top = {
        "version",
        "policy",
        "claim_boundary",
        "source_registry",
        "dataset_role_registry",
        "required_dataset_role",
        "require_clean_git",
        "accepted_statement_discovery",
        "configuration",
        "classification",
        "completeness",
        "role_isolation",
        "output",
    }
    if set(payload) != expected_top:
        raise NativeTMDocumentArtifactError("native TM document policy fields drifted")
    _require_exact(
        {
            key: payload[key]
            for key in (
                "version",
                "policy",
                "claim_boundary",
                "source_registry",
                "dataset_role_registry",
                "required_dataset_role",
                "require_clean_git",
            )
        },
        {
            "version": 1,
            "policy": _POLICY_NAME,
            "claim_boundary": _CLAIM_BOUNDARY,
            "source_registry": "data/registered/source_registry.jsonl",
            "dataset_role_registry": "data/registered/dataset_roles.jsonl",
            "required_dataset_role": _DATASET_ROLE,
            "require_clean_git": True,
        },
        "native TM document policy identity",
    )
    _require_exact(
        payload["accepted_statement_discovery"],
        {
            "format_version": _DISCOVERY_FORMAT,
            "policy": _DISCOVERY_POLICY,
            "claim_boundary": _DISCOVERY_CLAIM,
            "status": _DISCOVERY_STATUS,
            "required_dataset_role": _DATASET_ROLE,
            "producer_policy_path": _DISCOVERY_PRODUCER_POLICY_PATH,
            "runtime_input_policy": "EXACT_DECLARED_PROJECT_INPUT_LEDGER",
            "require_exact_runtime_read_ledger": True,
            "runtime_input_kind_counts": {
                "DATASET_ROLE_REGISTRY": 1,
                "NATIVE_TEXT_QUALITY_CONFIG": 1,
                "SOURCE_PDF": 1,
                "SOURCE_REGISTRY": 1,
                "STATEMENT_DISCOVERY_CONFIG": 4,
                "THIS_POLICY": 1,
            },
            "trusted_sha256_required": True,
            "notes_boundary_authority": "ACCEPTED_DISCOVERY_BLOCK_NOTES_BOUNDARY",
            "require_full_pdf_page_denominator": True,
            "require_source_identity_equality": True,
        },
        "accepted statement-discovery policy",
    )
    configuration = payload["configuration"]
    if not isinstance(configuration, dict) or set(configuration) != {
        "native_tm_region_policy",
        "geometry_config",
        "native_text_quality_config",
    }:
        raise NativeTMDocumentArtifactError("native TM configuration inventory drifted")
    expected_paths = {
        "native_tm_region_policy": "config/tables/native-tm-regions-v1.yaml",
        "geometry_config": "config/tables/geometry-v2.yaml",
        "native_text_quality_config": "config/ocr/native-text-quality-v2.yaml",
    }
    for name, expected_path in expected_paths.items():
        identity = configuration.get(name)
        if (
            not isinstance(identity, dict)
            or set(identity) != {"path", "sha256"}
            or identity.get("path") != expected_path
            or not isinstance(identity.get("sha256"), str)
            or _SHA256.fullmatch(identity["sha256"]) is None
        ):
            raise NativeTMDocumentArtifactError(f"{name} identity is invalid")
        _canonical_relative_path(identity["path"], name)
    _require_exact(
        payload["classification"],
        {
            "classes": list(_CLASSIFICATIONS),
            "pre_notes_boundary": "NON_TM",
            "quantitative_requires_discovered_region": True,
            "region_without_tm_authority": "UNASSESSED",
            "unmatched_post_boundary": "UNASSESSED",
            "top_band_height_ratio": 0.30,
            "tm_header_retrieval_phrases": [
                "thuyet minh bao cao tai chinh",
                "notes to the financial statements",
            ],
            "continuation_retrieval_phrases": ["tiep theo", "continued"],
            "continuation_requires_immediately_preceding_tm_page": True,
            "generic_note_heading_retrieval_regex": (
                r"^(?:(?:thuyet minh|note)(?: so)? )?[0-9]{1,4}(?: |$).*[a-z]"
            ),
            "generic_note_heading_minimum_alpha_tokens": 2,
        },
        "native TM page classification policy",
    )
    _require_exact(
        payload["completeness"],
        {
            "page_denominator": "ALL_PDF_PAGES",
            "every_page_requires_explicit_classification": True,
            "every_usable_page_requires_region_assessment": True,
            "unresolved_inter_table_ownership_blocks_completion": True,
            "table_on_unassessed_page_blocks_completion": True,
            "full_document_complete_rule": (
                "EVERY_PAGE_CLASSIFIED_AND_ALL_TABLE_OWNERSHIP_BOUNDED"
            ),
            "partial_artifact_publication_allowed": True,
        },
        "native TM completeness policy",
    )
    _require_exact(
        payload["role_isolation"],
        {
            "runtime_input_allowlist": [
                "SOURCE_PDF",
                "SOURCE_REGISTRY",
                "DATASET_ROLE_REGISTRY",
                "ACCEPTED_STATEMENT_DISCOVERY",
                "THIS_POLICY",
                "NATIVE_TM_REGION_POLICY",
                "GEOMETRY_CONFIG",
                "NATIVE_TEXT_QUALITY_CONFIG",
            ],
            "prior_answer_artifacts_allowed": False,
            "historical_values_allowed": False,
            "role_a_outputs_allowed": False,
            "reference_outputs_allowed": False,
            "schema_inputs_allowed": False,
            "bank_identity_used_for_routing": False,
            "filename_identity_used_for_routing": False,
            "page_number_rules_used_for_routing": False,
            "note_number_rules_used_for_routing": False,
            "expected_count_rules_used_for_routing": False,
            "forbidden_path_fragments": list(_V1_FORBIDDEN_PATH_FRAGMENTS),
        },
        "native TM role isolation",
    )
    _require_exact(
        payload["output"],
        {
            "format": _OUTPUT_FORMAT,
            "complete_status": _COMPLETE_STATUS,
            "partial_status": _PARTIAL_STATUS,
            "canonical_json": True,
            "exclusive_no_overwrite": True,
            "rollback_after_failed_strict_replay": True,
            "absolute_project_paths_allowed": False,
            "output_directory": _OUTPUT_DIRECTORY,
            "preserve_all_native_region_evidence": True,
        },
        "native TM output policy",
    )
    return copy.deepcopy(payload)


def load_native_tm_document_artifact_policy(
    path: Path,
    project_root: Path,
) -> dict[str, Any]:
    """Load the one canonical, source-only full-document TM policy."""

    project_root = project_root.resolve()
    path = path.resolve()
    if path != (project_root / POLICY_RELATIVE_PATH).resolve():
        raise NativeTMDocumentArtifactError(
            f"native TM artifact requires canonical policy {POLICY_RELATIVE_PATH}"
        )
    source_bytes = _read_stable_bytes(path, "native TM document policy")
    policy = _validate_policy_payload(_yaml_bytes(source_bytes, "native TM document policy"))
    _validate_path_isolation(
        [
            POLICY_RELATIVE_PATH.as_posix(),
            policy["source_registry"],
            policy["dataset_role_registry"],
            *(identity["path"] for identity in policy["configuration"].values()),
            *_IMPLEMENTATION_PATHS,
        ],
        policy,
    )
    for identity in policy["configuration"].values():
        config_path = _resolve_under_root(project_root, identity["path"], "configuration")
        if sha256_file(config_path) != identity["sha256"]:
            raise NativeTMDocumentArtifactError(
                f"pinned native TM configuration hash drifted: {identity['path']}"
            )
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
        raise NativeTMDocumentArtifactError(f"git {' '.join(arguments)} failed: {stderr.strip()}")
    return result.stdout


def _current_git_state(project_root: Path) -> dict[str, Any]:
    commit = str(_git(project_root, "rev-parse", "HEAD")).strip()
    dirty = bool(str(_git(project_root, "status", "--porcelain", "--untracked-files=all")).strip())
    if _GIT_COMMIT.fullmatch(commit) is None or dirty:
        raise NativeTMDocumentArtifactError(
            "native TM artifact requires the clean, identified current HEAD"
        )
    return {"commit": commit, "dirty": False}


def _git_file_bytes(project_root: Path, commit: str, raw_path: str) -> bytes:
    if _GIT_COMMIT.fullmatch(commit) is None:
        raise NativeTMDocumentArtifactError("producer commit is invalid")
    relative = _canonical_relative_path(raw_path, "producer snapshot path")
    return bytes(_git(project_root, "show", f"{commit}:{relative}", binary=True))


def _file_identity(path: Path, project_root: Path, kind: str) -> dict[str, Any]:
    payload = _read_stable_bytes(path, kind)
    return {
        "kind": kind,
        "path": _relative_path(project_root, path, kind),
        "sha256": sha256_bytes(payload),
        "size_bytes": len(payload),
    }


def _file_identity_at_commit(
    project_root: Path,
    commit: str,
    raw_path: str,
    *,
    kind: str | None = None,
) -> dict[str, Any]:
    payload = _git_file_bytes(project_root, commit, raw_path)
    record = {
        "path": raw_path,
        "sha256": sha256_bytes(payload),
        "size_bytes": len(payload),
    }
    return {"kind": kind, **record} if kind is not None else record


def _implementation_ledger(project_root: Path) -> list[dict[str, Any]]:
    return [
        {
            key: value
            for key, value in _file_identity(
                _resolve_under_root(project_root, raw_path, "implementation module"),
                project_root,
                "IMPLEMENTATION",
            ).items()
            if key != "kind"
        }
        for raw_path in _IMPLEMENTATION_PATHS
    ]


def _implementation_ledger_at_commit(project_root: Path, commit: str) -> list[dict[str, Any]]:
    return [
        _file_identity_at_commit(project_root, commit, raw_path)
        for raw_path in _IMPLEMENTATION_PATHS
    ]


def _validate_path_isolation(paths: Sequence[str], policy: Mapping[str, Any]) -> None:
    fragments = tuple(
        str(item).casefold() for item in policy["role_isolation"]["forbidden_path_fragments"]
    )
    for raw_path in paths:
        relative = _canonical_relative_path(raw_path, "runtime path")
        normalized = "/" + relative.casefold().strip("/")
        if any(fragment in normalized for fragment in fragments):
            raise NativeTMDocumentArtifactError(
                f"runtime path is forbidden by role isolation: {relative}"
            )


def _registered_source_from_bytes(
    *,
    project_root: Path,
    source_pdf: Path,
    source_registry_bytes: bytes,
    role_registry_bytes: bytes,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    source_pdf = source_pdf.resolve()
    relative = _relative_path(project_root, source_pdf, "source PDF")
    if source_pdf.suffix.casefold() != ".pdf":
        raise NativeTMDocumentArtifactError("registered source must be a PDF")
    source_bytes = _read_stable_bytes(source_pdf, "source PDF")
    digest = sha256_bytes(source_bytes)
    source_records = _read_jsonl_bytes(source_registry_bytes, "source registry")
    source_matches = [
        record for record in source_records if record.get("relative_path") == relative
    ]
    if len(source_matches) != 1:
        raise NativeTMDocumentArtifactError(
            "source PDF must resolve to exactly one source-registry record"
        )
    source_record = source_matches[0]
    document_id = f"sha256:{digest}"
    if (
        source_record.get("document_id") != document_id
        or source_record.get("sha256") != digest
        or source_record.get("size_bytes") != len(source_bytes)
        or source_record.get("kind") != "PDF"
        or source_record.get("state") != "REGISTERED"
        or source_record.get("hash_verified_stable") is not True
    ):
        raise NativeTMDocumentArtifactError("source-registry identity drifted")
    role_records = _read_jsonl_bytes(role_registry_bytes, "dataset-role registry")
    role_matches = [record for record in role_records if record.get("document_id") == document_id]
    if len(role_matches) != 1:
        raise NativeTMDocumentArtifactError(
            "source PDF must resolve to exactly one dataset-role record"
        )
    role_record = role_matches[0]
    if (
        role_record.get("dataset_role") != _DATASET_ROLE
        or role_record.get("source_path") != relative
        or role_record.get("immutable") is not True
    ):
        raise NativeTMDocumentArtifactError(
            "native TM document stage accepts immutable LOGIC_DEVELOPMENT sources only"
        )
    source_identity = {
        "document_id": document_id,
        "relative_path": relative,
        "sha256": digest,
        "size_bytes": len(source_bytes),
        "dataset_role": _DATASET_ROLE,
        "registry_state": "REGISTERED",
        "hash_verified_stable": True,
        "immutable_role_assignment": True,
        "source_registry_record_sha256": _canonical_record_sha256(source_record),
        "dataset_role_registry_record_sha256": _canonical_record_sha256(role_record),
    }
    return source_record, role_record, source_identity


def _discovery_producer_policy_paths(
    *,
    project_root: Path,
    producer_commit: str,
) -> tuple[str, str, str, tuple[str, ...]]:
    policy_bytes = _git_file_bytes(project_root, producer_commit, _DISCOVERY_PRODUCER_POLICY_PATH)
    producer_policy = _yaml_bytes(policy_bytes, "producer statement-discovery policy")
    required_identity = {
        "version": 1,
        "policy": _DISCOVERY_POLICY,
        "claim_boundary": _DISCOVERY_CLAIM,
        "source_registry": "data/registered/source_registry.jsonl",
        "dataset_role_registry": "data/registered/dataset_roles.jsonl",
        "require_clean_git": True,
        "require_registered_pdf": True,
        "require_hash_verified_stable": True,
    }
    if any(producer_policy.get(key) != value for key, value in required_identity.items()):
        raise NativeTMDocumentArtifactError("statement-discovery producer policy identity drifted")
    if _DATASET_ROLE not in producer_policy.get("allowed_dataset_roles", []) or producer_policy.get(
        "forbidden_dataset_roles"
    ) != ["UNTOUCHED_HOLDOUT"]:
        raise NativeTMDocumentArtifactError("statement-discovery producer role policy is invalid")
    isolation = producer_policy.get("role_isolation")
    if not isinstance(isolation, dict) or set(isolation.get("runtime_input_allowlist", [])) != {
        "SOURCE_PDF",
        "SOURCE_REGISTRY",
        "DATASET_ROLE_REGISTRY",
        "THIS_POLICY",
        "NATIVE_TEXT_QUALITY_CONFIG",
        "STATEMENT_DISCOVERY_CONFIG",
    }:
        raise NativeTMDocumentArtifactError(
            "statement-discovery producer runtime-input policy drifted"
        )
    quality = producer_policy.get("native_text_quality_config")
    primary = producer_policy.get("statement_discovery_config")
    chain = producer_policy.get("statement_discovery_config_chain")
    if (
        not isinstance(quality, dict)
        or quality.get("path") != "config/ocr/native-text-quality-v2.yaml"
        or not isinstance(primary, dict)
        or primary.get("path") != "config/document_phase/statement-discovery-v4.yaml"
        or not isinstance(chain, list)
        or [item.get("path") for item in chain if isinstance(item, dict)]
        != [
            "config/document_phase/statement-discovery-v3.yaml",
            "config/document_phase/statement-locator-v2.yaml",
            "config/document_phase/statement-locator-v1.yaml",
        ]
    ):
        raise NativeTMDocumentArtifactError(
            "statement-discovery producer configuration inventory drifted"
        )
    identities = [quality, primary, *chain]
    for identity in identities:
        path = _canonical_relative_path(
            identity.get("path"), "statement-discovery producer configuration"
        )
        if (
            not isinstance(identity.get("sha256"), str)
            or _SHA256.fullmatch(identity["sha256"]) is None
            or _file_identity_at_commit(project_root, producer_commit, path)["sha256"]
            != identity["sha256"]
        ):
            raise NativeTMDocumentArtifactError(
                "statement-discovery producer configuration hash drifted"
            )
    config_paths = tuple(sorted(identity["path"] for identity in [primary, *chain]))
    if config_paths != _DISCOVERY_CONFIG_PATHS:
        raise NativeTMDocumentArtifactError(
            "statement-discovery producer configuration paths drifted"
        )
    return (
        producer_policy["source_registry"],
        producer_policy["dataset_role_registry"],
        quality["path"],
        config_paths,
    )


def _validate_discovery_runtime_inputs(
    *,
    project_root: Path,
    source_pdf: Path,
    payload: Mapping[str, Any],
    producer_commit: str,
    expected_source: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    inputs = payload.get("inputs")
    if not isinstance(inputs, dict) or set(inputs) != {
        "runtime_read_ledger",
        "runtime_read_ledger_sha256",
    }:
        raise NativeTMDocumentArtifactError(
            "accepted statement-discovery runtime ledger envelope is invalid"
        )
    ledger = inputs["runtime_read_ledger"]
    if not isinstance(ledger, list) or any(
        not isinstance(record, dict)
        or set(record) != {"kind", "path", "sha256", "size_bytes"}
        or not isinstance(record.get("kind"), str)
        or not isinstance(record.get("path"), str)
        or not isinstance(record.get("sha256"), str)
        or _SHA256.fullmatch(record["sha256"]) is None
        or isinstance(record.get("size_bytes"), bool)
        or not isinstance(record.get("size_bytes"), int)
        or record["size_bytes"] < 0
        for record in ledger
    ):
        raise NativeTMDocumentArtifactError(
            "accepted statement-discovery runtime ledger records are invalid"
        )
    if ledger != sorted(ledger, key=lambda record: (record["kind"], record["path"])):
        raise NativeTMDocumentArtifactError(
            "accepted statement-discovery runtime ledger order drifted"
        )
    for record in ledger:
        _canonical_relative_path(record["path"], "accepted statement-discovery runtime path")
    _validate_path_isolation([record["path"] for record in ledger], policy)
    expected_counts = policy["accepted_statement_discovery"]["runtime_input_kind_counts"]
    if Counter(record["kind"] for record in ledger) != Counter(expected_counts):
        raise NativeTMDocumentArtifactError(
            "accepted statement-discovery runtime ledger inventory drifted"
        )
    expected_hash = stable_records_hash(
        json.dumps(record, ensure_ascii=False, sort_keys=True) for record in ledger
    )
    if inputs["runtime_read_ledger_sha256"] != expected_hash:
        raise NativeTMDocumentArtifactError(
            "accepted statement-discovery runtime ledger hash drifted"
        )
    source_registry, role_registry, quality_path, config_paths = _discovery_producer_policy_paths(
        project_root=project_root,
        producer_commit=producer_commit,
    )
    tracked = [
        ("DATASET_ROLE_REGISTRY", role_registry),
        ("NATIVE_TEXT_QUALITY_CONFIG", quality_path),
        ("SOURCE_REGISTRY", source_registry),
        *(("STATEMENT_DISCOVERY_CONFIG", path) for path in config_paths),
        ("THIS_POLICY", _DISCOVERY_PRODUCER_POLICY_PATH),
    ]
    expected_ledger = [
        _file_identity_at_commit(project_root, producer_commit, path, kind=kind)
        for kind, path in tracked
    ]
    expected_ledger.append(
        {
            "kind": "SOURCE_PDF",
            "path": expected_source["relative_path"],
            "sha256": expected_source["sha256"],
            "size_bytes": expected_source["size_bytes"],
        }
    )
    expected_ledger.sort(key=lambda record: (record["kind"], record["path"]))
    if ledger != expected_ledger:
        raise NativeTMDocumentArtifactError(
            "accepted statement-discovery runtime ledger differs from producer inputs"
        )
    source_registry_bytes = _git_file_bytes(project_root, producer_commit, source_registry)
    role_registry_bytes = _git_file_bytes(project_root, producer_commit, role_registry)
    source_record, role_record, producer_source = _registered_source_from_bytes(
        project_root=project_root,
        source_pdf=source_pdf,
        source_registry_bytes=source_registry_bytes,
        role_registry_bytes=role_registry_bytes,
    )
    if producer_source != expected_source:
        raise NativeTMDocumentArtifactError(
            "statement-discovery producer source identity differs from artifact source"
        )
    expected_discovery_source = {
        "document_id": source_record["document_id"],
        "relative_path": expected_source["relative_path"],
        "sha256": expected_source["sha256"],
        "size_bytes": expected_source["size_bytes"],
        "bank": source_record.get("bank"),
        "year": source_record.get("year"),
        "dataset_role": role_record["dataset_role"],
        "registry_state": source_record["state"],
        "hash_verified_stable": source_record["hash_verified_stable"],
        "immutable_role_assignment": role_record["immutable"],
    }
    return expected_discovery_source


def _preflight_discovery_path_isolation(
    *,
    project_root: Path,
    path: Path,
    expected_sha256: str,
    policy: Mapping[str, Any],
) -> None:
    relative = _relative_path(project_root, path, "accepted statement discovery")
    _validate_path_isolation([relative], policy)
    encoded = _read_stable_bytes(path, "accepted statement discovery")
    if _SHA256.fullmatch(expected_sha256) is None or sha256_bytes(encoded) != expected_sha256:
        raise NativeTMDocumentArtifactError(
            "accepted statement discovery does not match its trusted SHA-256"
        )
    try:
        payload = json.loads(encoded)
    except json.JSONDecodeError as exc:
        raise NativeTMDocumentArtifactError("accepted statement discovery is invalid JSON") from exc
    if not isinstance(payload, dict) or encoded != _canonical_json_bytes(payload):
        raise NativeTMDocumentArtifactError("accepted statement discovery is not canonical JSON")
    inputs = payload.get("inputs")
    ledger = inputs.get("runtime_read_ledger") if isinstance(inputs, dict) else None
    implementation = (
        payload.get("code", {}).get("implementation")
        if isinstance(payload.get("code"), dict)
        else None
    )
    if (
        not isinstance(ledger, list)
        or not isinstance(implementation, list)
        or any(
            not isinstance(record, dict) or not isinstance(record.get("path"), str)
            for record in [*ledger, *implementation]
        )
    ):
        raise NativeTMDocumentArtifactError("accepted statement-discovery path ledger is invalid")
    _validate_path_isolation([record["path"] for record in [*ledger, *implementation]], policy)


def _strict_load_statement_discovery(
    *,
    project_root: Path,
    source_pdf: Path,
    path: Path,
    expected_sha256: str,
    expected_source: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes, int, dict[int, dict[str, Any]]]:
    if _SHA256.fullmatch(expected_sha256) is None:
        raise NativeTMDocumentArtifactError("trusted statement-discovery SHA-256 is invalid")
    relative = _relative_path(project_root, path, "accepted statement discovery")
    _validate_path_isolation([relative], policy)
    try:
        path.resolve().relative_to((project_root / _OUTPUT_DIRECTORY).resolve())
    except ValueError as exc:
        raise NativeTMDocumentArtifactError(
            "accepted LOGIC_DEVELOPMENT discovery must stay under output/development"
        ) from exc
    encoded = _read_stable_bytes(path, "accepted statement discovery")
    if sha256_bytes(encoded) != expected_sha256:
        raise NativeTMDocumentArtifactError(
            "accepted statement discovery does not match its trusted SHA-256"
        )
    try:
        payload = json.loads(encoded)
    except json.JSONDecodeError as exc:
        raise NativeTMDocumentArtifactError("accepted statement discovery is invalid JSON") from exc
    if not isinstance(payload, dict) or encoded != _canonical_json_bytes(payload):
        raise NativeTMDocumentArtifactError("accepted statement discovery is not canonical JSON")
    required_top = {
        "format_version",
        "policy",
        "claim_boundary",
        "status",
        "run_id",
        "source",
        "code",
        "authority",
        "isolation",
        "inputs",
        "native_text",
        "discovery",
    }
    if set(payload) != required_top:
        raise NativeTMDocumentArtifactError("accepted statement discovery envelope drifted")
    expected_contract = policy["accepted_statement_discovery"]
    for key in ("format_version", "policy", "claim_boundary", "status"):
        if payload.get(key) != expected_contract[key]:
            raise NativeTMDocumentArtifactError(f"accepted statement discovery {key} is invalid")
    if (
        not isinstance(payload.get("run_id"), str)
        or _SAFE_RUN_ID.fullmatch(payload["run_id"]) is None
    ):
        raise NativeTMDocumentArtifactError("accepted statement discovery run_id is invalid")
    code = payload.get("code")
    if (
        not isinstance(code, dict)
        or set(code) != {"commit", "dirty", "implementation"}
        or code.get("dirty") is not False
        or not isinstance(code.get("commit"), str)
        or _GIT_COMMIT.fullmatch(code["commit"]) is None
    ):
        raise NativeTMDocumentArtifactError(
            "accepted statement discovery producer identity is invalid"
        )
    implementation = code.get("implementation")
    if not isinstance(implementation, list) or any(
        not isinstance(record, dict)
        or set(record) != {"path", "sha256", "size_bytes"}
        or not isinstance(record.get("path"), str)
        for record in implementation
    ):
        raise NativeTMDocumentArtifactError(
            "accepted statement-discovery implementation ledger is invalid"
        )
    _validate_path_isolation([record["path"] for record in implementation], policy)
    expected_discovery_implementation = [
        _file_identity_at_commit(project_root, code["commit"], raw_path)
        for raw_path in _DISCOVERY_IMPLEMENTATION_PATHS
    ]
    if implementation != expected_discovery_implementation:
        raise NativeTMDocumentArtifactError(
            "accepted statement-discovery implementation ledger differs from its producer commit"
        )
    expected_discovery_source = _validate_discovery_runtime_inputs(
        project_root=project_root,
        source_pdf=source_pdf,
        payload=payload,
        producer_commit=code["commit"],
        expected_source=expected_source,
        policy=policy,
    )
    source = payload.get("source")
    if source != expected_discovery_source:
        raise NativeTMDocumentArtifactError(
            "accepted statement discovery source identity differs from the registered source"
        )
    if payload.get("authority") != {
        "geometry": "PYMUPDF_NATIVE_TEXT_WORDS",
        "base_scoring_engine": "MULTISIGNAL_STATEMENT_DISCOVERY_V4",
        "base_geometry_authority": "PP_OCRV6_WORD_BOXES",
        "evidence_source": "PYMUPDF_NATIVE_TEXT_GEOMETRY",
        "override_scope": "GEOMETRY_SOURCE_ONLY",
        "semantic_reader": None,
    }:
        raise NativeTMDocumentArtifactError(
            "accepted statement-discovery authority contract drifted"
        )
    if payload.get("isolation") != {
        "prior_answer_artifacts_loaded": False,
        "historical_values_loaded": False,
        "role_a_outputs_loaded": False,
        "bank_identity_used_for_scoring": False,
        "filename_identity_used_for_scoring": False,
        "page_number_rules_used_for_scoring": False,
        "runtime_input_policy": "EXACT_DECLARED_PROJECT_INPUT_LEDGER",
    }:
        raise NativeTMDocumentArtifactError("accepted statement-discovery role isolation drifted")
    native_text = payload.get("native_text")
    if not isinstance(native_text, dict):
        raise NativeTMDocumentArtifactError(
            "accepted statement discovery page denominator is absent"
        )
    page_count = native_text.get("page_count")
    pages = native_text.get("pages")
    if (
        isinstance(page_count, bool)
        or not isinstance(page_count, int)
        or page_count < 1
        or not isinstance(pages, list)
        or len(pages) != page_count
        or [page.get("page") for page in pages if isinstance(page, dict)]
        != list(range(1, page_count + 1))
        or native_text.get("all_pages_usable") is not True
        or native_text.get("usable_page_count") != page_count
        or native_text.get("ocr_required_pages") != []
    ):
        raise NativeTMDocumentArtifactError(
            "accepted statement discovery does not cover every usable PDF page"
        )
    discovery = payload.get("discovery")
    if (
        not isinstance(discovery, dict)
        or discovery.get("status") != "ACCEPTED_MULTI_SIGNAL_STATEMENT_BLOCK"
        or discovery.get("observed_pages") != list(range(1, page_count + 1))
        or discovery.get("geometry_authority") != "PYMUPDF_NATIVE_TEXT_WORDS"
        or not isinstance(discovery.get("block"), dict)
    ):
        raise NativeTMDocumentArtifactError(
            "accepted statement discovery lacks a full native-text document contract"
        )
    block = discovery["block"]
    boundary = block.get("notes_boundary_page")
    if (
        isinstance(boundary, bool)
        or not isinstance(boundary, int)
        or not 1 <= boundary <= page_count
    ):
        raise NativeTMDocumentArtifactError("accepted notes boundary is invalid")
    block_start = block.get("start_page")
    block_end = block.get("end_page")
    if (
        isinstance(block_start, bool)
        or not isinstance(block_start, int)
        or isinstance(block_end, bool)
        or not isinstance(block_end, int)
        or not 1 <= block_start <= block_end < boundary
    ):
        raise NativeTMDocumentArtifactError(
            "accepted main-statement block does not end before the notes boundary"
        )
    page_contracts = block.get("page_contracts", [])
    if not isinstance(page_contracts, list) or any(
        not isinstance(contract, dict)
        or isinstance(contract.get("page"), bool)
        or not isinstance(contract.get("page"), int)
        or contract["page"] >= boundary
        for contract in page_contracts
    ):
        raise NativeTMDocumentArtifactError(
            "accepted main-statement page contract crosses the notes boundary"
        )
    signals = discovery.get("page_signals")
    if (
        not isinstance(signals, list)
        or len(signals) != page_count
        or [signal.get("page") for signal in signals if isinstance(signal, dict)]
        != list(range(1, page_count + 1))
    ):
        raise NativeTMDocumentArtifactError(
            "accepted statement discovery page signals do not cover the PDF"
        )
    signal_by_page = {int(signal["page"]): signal for signal in signals}
    boundary_signal = signal_by_page[boundary]
    candidates = boundary_signal.get("candidates")
    tm_candidates = (
        [
            candidate
            for candidate in candidates
            if isinstance(candidate, dict) and candidate.get("page_type") == "TM"
        ]
        if isinstance(candidates, list)
        else []
    )
    if (
        boundary_signal.get("notes_structure") is not True
        or "TM" not in boundary_signal.get("form_types", [])
        or not any(candidate.get("locally_accepted") is True for candidate in tm_candidates)
    ):
        raise NativeTMDocumentArtifactError(
            "accepted notes boundary lacks source-visible local TM evidence"
        )
    if _read_stable_bytes(path, "accepted statement discovery") != encoded:
        raise NativeTMDocumentArtifactError(
            "accepted statement discovery changed during strict load"
        )
    return copy.deepcopy(payload), encoded, boundary, copy.deepcopy(signal_by_page)


def _load_config_from_bytes(
    payload: bytes,
    loader: Callable[[Path], Any],
    label: str,
) -> Any:
    descriptor, name = tempfile.mkstemp(prefix="native-tm-config-", suffix=".yaml")
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            if stream.write(payload) != len(payload):
                raise NativeTMDocumentArtifactError(f"temporary {label} write was incomplete")
            stream.flush()
        try:
            return loader(temporary)
        except Exception as exc:
            raise NativeTMDocumentArtifactError(f"cannot load producer {label}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def _configuration_materials(
    config_bytes_by_kind: Mapping[str, bytes],
) -> tuple[Any, Any, dict[str, Any]]:
    if set(config_bytes_by_kind) != set(_CONFIG_KINDS):
        raise NativeTMDocumentArtifactError("native TM configuration byte inventory is incomplete")
    region_policy = _load_config_from_bytes(
        config_bytes_by_kind["NATIVE_TM_REGION_POLICY"],
        load_native_tm_region_policy,
        "native TM region policy",
    )
    geometry_config = _load_config_from_bytes(
        config_bytes_by_kind["GEOMETRY_CONFIG"],
        load_geometry_config,
        "geometry config",
    )
    quality_config = _load_config_from_bytes(
        config_bytes_by_kind["NATIVE_TEXT_QUALITY_CONFIG"],
        load_native_text_quality_v2_config,
        "native-text quality config",
    )
    return region_policy, geometry_config, quality_config


def _producer_snapshots(
    *,
    policy_path: str,
    policy_bytes: bytes,
    policy: Mapping[str, Any],
    config_records: Sequence[dict[str, Any]],
    config_bytes_by_kind: Mapping[str, bytes],
) -> dict[str, Any]:
    configurations = []
    for record in config_records:
        kind = str(record["kind"])
        configurations.append(
            {
                **record,
                "payload_sha256": _canonical_record_sha256(
                    _yaml_bytes(config_bytes_by_kind[kind], kind)
                ),
                "payload": _yaml_bytes(config_bytes_by_kind[kind], kind),
            }
        )
    return {
        "policy": {
            "path": policy_path,
            "sha256": sha256_bytes(policy_bytes),
            "size_bytes": len(policy_bytes),
            "payload_sha256": _canonical_record_sha256(policy),
            "payload": copy.deepcopy(dict(policy)),
        },
        "configurations": configurations,
    }


def _run_evidence(run: Any) -> dict[str, Any]:
    return {
        "run_id": run.run_id,
        "raw_text": run.raw_text,
        "normalized_text": run.normalized_text,
        "retrieval_key": retrieval_key(run.raw_text),
        "bbox": _json_value(run.bbox),
        "block_number": run.block_number,
        "line_number": run.line_number,
    }


def _matching_phrase_runs(
    runs: Sequence[Any],
    phrases: Sequence[str],
    *,
    maximum_y: float,
) -> list[Any]:
    return [
        run
        for run in runs
        if run.bbox.y0 <= maximum_y
        and any(phrase in retrieval_key(run.raw_text) for phrase in phrases)
    ]


def _generic_note_heading_runs(
    runs: Sequence[Any],
    *,
    pattern: re.Pattern[str],
    minimum_alpha_tokens: int,
) -> list[Any]:
    candidates = []
    for run in runs:
        key = retrieval_key(run.raw_text)
        if pattern.fullmatch(key) is None:
            continue
        alpha_tokens = sum(any(character.isalpha() for character in token) for token in key.split())
        if alpha_tokens >= minimum_alpha_tokens:
            candidates.append(run)
    return candidates


def _visible_words_sha256(words: Sequence[Any]) -> str:
    return stable_records_hash(
        json.dumps(
            {
                "raw_text": word.raw_text,
                "normalized_text": word.normalized_text,
                "bbox": _json_value(word.bbox_points),
                "block_number": word.block_number,
                "line_number": word.line_number,
                "word_number": word.word_number,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        for word in words
    )


def _empty_region_evidence(
    *,
    page_number: int,
    status: str,
    excluded_spans: Sequence[Any],
    unassigned_runs: Sequence[Any],
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "page": page_number,
        "assessment_status": status,
        "regions": [],
        "inter_table_contexts": [],
        "unit_group_diagnostics": [],
        "excluded_spans": _json_value(excluded_spans),
        "unassigned_page_runs": _json_value(unassigned_runs),
        "error": error,
    }


def _serialize_regions(regions: NativeTMPageRegions) -> dict[str, Any]:
    serialized = _json_value(regions)
    if not isinstance(serialized, dict):
        raise NativeTMDocumentArtifactError("native TM page regions did not serialize as an object")
    return {"assessment_status": "ASSESSED", **serialized, "error": None}


def _build_pages(
    *,
    source_pdf: Path,
    source_sha256: str,
    boundary: int,
    signal_by_page: Mapping[int, dict[str, Any]],
    policy: Mapping[str, Any],
    region_policy: Any,
    geometry_config: Any,
    quality_config: Mapping[str, Any],
) -> list[dict[str, Any]]:
    classification_policy = policy["classification"]
    tm_phrases = tuple(classification_policy["tm_header_retrieval_phrases"])
    continuation_phrases = tuple(classification_policy["continuation_retrieval_phrases"])
    note_heading_pattern = re.compile(classification_policy["generic_note_heading_retrieval_regex"])
    pages: list[dict[str, Any]] = []
    preceding_tm = False
    try:
        document = fitz.open(source_pdf)
    except Exception as exc:
        raise NativeTMDocumentArtifactError("cannot open registered source PDF") from exc
    with document:
        if document.page_count < 1:
            raise NativeTMDocumentArtifactError("registered source PDF has no pages")
        for index in range(document.page_count):
            fitz_page = document[index]
            page_number = index + 1
            try:
                visible = extract_visible_native_text_page(
                    fitz_page,
                    region_policy,
                    native_text_quality_config=dict(quality_config),
                )
            except Exception as exc:
                raise NativeTMDocumentArtifactError(
                    f"visible native text extraction failed on PDF page {page_number}"
                ) from exc
            page = visible.page
            if page.page != page_number:
                raise NativeTMDocumentArtifactError("native PDF page identity is not contiguous")
            assessment = assess_native_text_quality_v2(page.words, dict(quality_config))
            runs = build_text_runs(
                page.words,
                gap_height_factor=geometry_config.run_separation_gap_height_factor,
                financial_gap_height_factor=(
                    geometry_config.financial_token_separation_gap_height_factor
                ),
            )
            top_y = page.height_points * float(classification_policy["top_band_height_ratio"])
            tm_header_runs = _matching_phrase_runs(runs, tm_phrases, maximum_y=top_y)
            continuation_runs = _matching_phrase_runs(runs, continuation_phrases, maximum_y=top_y)
            note_heading_runs = _generic_note_heading_runs(
                runs,
                pattern=note_heading_pattern,
                minimum_alpha_tokens=int(
                    classification_policy["generic_note_heading_minimum_alpha_tokens"]
                ),
            )
            region_error: str | None = None
            if assessment.status == "USABLE_TEXT_LAYER":
                try:
                    discovered = discover_native_tm_regions(
                        page,
                        geometry_config=geometry_config,
                        policy=region_policy,
                        table_id_prefix=f"source-{source_sha256[:16]}",
                        excluded_spans=visible.excluded_spans,
                    )
                    discovered = replace(
                        discovered,
                        regions=tuple(
                            resolve_region_blank_slots(fitz_page, region, region_policy)
                            for region in discovered.regions
                        ),
                    )
                    region_evidence = _serialize_regions(discovered)
                except NativeTMRegionError as exc:
                    region_error = str(exc)
                    region_evidence = _empty_region_evidence(
                        page_number=page_number,
                        status="UNRESOLVED_REGION_DISCOVERY_ERROR",
                        excluded_spans=visible.excluded_spans,
                        unassigned_runs=runs,
                        error=region_error,
                    )
            else:
                region_evidence = _empty_region_evidence(
                    page_number=page_number,
                    status="NOT_ASSESSED_UNUSABLE_NATIVE_TEXT",
                    excluded_spans=visible.excluded_spans,
                    unassigned_runs=runs,
                )
            regions = region_evidence["regions"]
            signal = signal_by_page.get(page_number, {})
            notes_structure = signal.get("notes_structure") is True
            evidence: list[dict[str, Any]] = []
            tm_authority = False
            continuation_authority = False
            if page_number < boundary:
                classification = "NON_TM"
                evidence.append(
                    {
                        "kind": "TRUSTED_PRE_NOTES_BOUNDARY",
                        "notes_boundary_page": boundary,
                        "authority": "ACCEPTED_STATEMENT_DISCOVERY",
                    }
                )
            elif assessment.status != "USABLE_TEXT_LAYER" or region_error is not None:
                classification = "UNASSESSED"
                evidence.append(
                    {
                        "kind": (
                            "UNUSABLE_NATIVE_TEXT"
                            if assessment.status != "USABLE_TEXT_LAYER"
                            else "REGION_DISCOVERY_ERROR"
                        )
                    }
                )
            else:
                if page_number == boundary:
                    tm_authority = True
                    evidence.append(
                        {
                            "kind": "TRUSTED_SOURCE_VISIBLE_NOTES_BOUNDARY",
                            "authority": "ACCEPTED_STATEMENT_DISCOVERY",
                            "notes_structure": notes_structure,
                        }
                    )
                if tm_header_runs:
                    tm_authority = True
                    evidence.append(
                        {
                            "kind": "SOURCE_VISIBLE_TM_HEADER",
                            "runs": [_run_evidence(run) for run in tm_header_runs],
                        }
                    )
                if page_number > boundary and preceding_tm:
                    if continuation_runs:
                        continuation_authority = True
                        evidence.append(
                            {
                                "kind": "SOURCE_VISIBLE_CONTINUATION_MARKER",
                                "runs": [_run_evidence(run) for run in continuation_runs],
                            }
                        )
                    elif note_heading_runs and notes_structure:
                        continuation_authority = True
                        evidence.append(
                            {
                                "kind": "SOURCE_VISIBLE_NOTE_HEADING_WITH_NOTES_STRUCTURE",
                                "runs": [_run_evidence(run) for run in note_heading_runs],
                            }
                        )
                tm_candidate = tm_authority or continuation_authority
                if not tm_candidate:
                    classification = "UNASSESSED"
                    evidence.append(
                        {
                            "kind": "NO_SOURCE_VISIBLE_TM_OR_CONTINUATION_AUTHORITY",
                            "discovered_region_count": len(regions),
                            "region_is_not_tm_routing_authority": True,
                        }
                    )
                elif regions:
                    classification = "QUANTITATIVE_TM"
                else:
                    classification = "QUALITATIVE_TM_CONTEXT"
            preceding_tm = classification in _TM_CLASSIFICATIONS
            pages.append(
                {
                    "page": page_number,
                    "width_points": page.width_points,
                    "height_points": page.height_points,
                    "rotation": page.rotation,
                    "quality": _json_value(assessment),
                    "visible_native_word_count": len(page.words),
                    "visible_native_words_sha256": _visible_words_sha256(page.words),
                    "classification": classification,
                    "classification_status": (
                        "ASSESSED" if classification != "UNASSESSED" else "UNASSESSED"
                    ),
                    "classification_evidence": evidence,
                    "source_visible_tm_header_runs": [_run_evidence(run) for run in tm_header_runs],
                    "source_visible_continuation_runs": [
                        _run_evidence(run) for run in continuation_runs
                    ],
                    "source_visible_note_heading_candidates": [
                        _run_evidence(run) for run in note_heading_runs
                    ],
                    "native_tm_regions": region_evidence,
                }
            )
    return pages


def _note_inventory(pages: Sequence[dict[str, Any]], boundary: int) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for page in pages:
        if int(page["page"]) < boundary:
            continue
        for candidate in page["source_visible_note_heading_candidates"]:
            records.append(
                {
                    "note_id": f"source-note-heading-{len(records) + 1:04d}",
                    "page": page["page"],
                    "source_run_id": candidate["run_id"],
                    "raw_heading": candidate["raw_text"],
                    "normalized_heading": candidate["normalized_text"],
                    "heading_bbox": candidate["bbox"],
                    "inventory_status": "SOURCE_VISIBLE_GENERIC_HEADING_CANDIDATE",
                    "accounting_identity": None,
                    "number_used_for_routing": False,
                }
            )
    unassessed_post_boundary = [
        page["page"]
        for page in pages
        if page["page"] >= boundary and page["classification"] == "UNASSESSED"
    ]
    return {
        "status": (
            "COMPLETE_SOURCE_VISIBLE_NOTE_HEADING_INVENTORY"
            if not unassessed_post_boundary
            else "PARTIAL_SOURCE_VISIBLE_NOTE_HEADING_INVENTORY"
        ),
        "claim_boundary": "GENERIC_SOURCE_HEADING_CANDIDATES_WITHOUT_NOTE_NUMBER_ROUTING",
        "candidate_count": len(records),
        "unassessed_post_boundary_pages": unassessed_post_boundary,
        "records": records,
    }


def _table_inventory(pages: Sequence[dict[str, Any]]) -> dict[str, Any]:
    table_records: list[dict[str, Any]] = []
    context_records: list[dict[str, Any]] = []
    assessed_every_page = True
    for page in pages:
        regions = page["native_tm_regions"]
        if regions["assessment_status"] != "ASSESSED":
            assessed_every_page = False
        for region in regions["regions"]:
            classification = page["classification"]
            ownership_status = (
                "BOUNDED_TM_TABLE_REGION"
                if classification in _TM_CLASSIFICATIONS
                else "BOUNDED_NON_TM_TABLE_REGION"
                if classification == "NON_TM"
                else "UNRESOLVED_PAGE_CLASSIFICATION"
            )
            table_records.append(
                {
                    "table_id": region["table_id"],
                    "page": region["page"],
                    "table_order": region["table_order"],
                    "region_bbox": region["region_bbox"],
                    "page_classification": classification,
                    "ownership_status": ownership_status,
                    "header_binding_count": len(region["header_bindings"]),
                    "row_count": len(region["rows"]),
                    "grid_slot_count": len(region["grid_slots"]),
                    "scalar_disclosure_count": len(region["scalar_disclosures"]),
                    "outside_financial_span_row_count": len(region["outside_financial_span_rows"]),
                    "unassigned_run_count": len(region["unassigned_runs"]),
                    "region_record_sha256": _canonical_record_sha256(region),
                }
            )
        for context in regions["inter_table_contexts"]:
            context_records.append(
                {
                    "page": context["page"],
                    "preceding_table_id": context["preceding_table_id"],
                    "following_table_id": context["following_table_id"],
                    "ownership_status": context["ownership_status"],
                    "context_record_sha256": _canonical_record_sha256(context),
                }
            )
    table_ids = [record["table_id"] for record in table_records]
    if len(table_ids) != len(set(table_ids)):
        raise NativeTMDocumentArtifactError("native TM table inventory repeats a table ID")
    unresolved_tables = [
        record["table_id"]
        for record in table_records
        if not record["ownership_status"].startswith("BOUNDED_")
    ]
    unresolved_contexts = [
        record
        for record in context_records
        if record["ownership_status"] != "BOUNDED_INTER_TABLE_OWNERSHIP"
    ]
    all_bounded = assessed_every_page and not unresolved_tables and not unresolved_contexts
    return {
        "status": (
            "COMPLETE_BOUNDED_TABLE_INVENTORY"
            if all_bounded
            else "PARTIAL_OR_UNRESOLVED_TABLE_INVENTORY"
        ),
        "table_count": len(table_records),
        "inter_table_context_count": len(context_records),
        "unresolved_table_ids": unresolved_tables,
        "unresolved_inter_table_context_count": len(unresolved_contexts),
        "all_page_region_assessments_complete": assessed_every_page,
        "all_table_ownership_bounded": all_bounded,
        "records": table_records,
        "inter_table_contexts": context_records,
    }


def _build_core(
    *,
    project_root: Path,
    source_pdf: Path,
    discovery_path: Path,
    discovery_sha256: str,
    policy_relative: str,
    policy_bytes: bytes,
    policy: Mapping[str, Any],
    config_records: Sequence[dict[str, Any]],
    config_bytes_by_kind: Mapping[str, bytes],
    source_registry_bytes: bytes,
    role_registry_bytes: bytes,
    runtime_inputs: Sequence[dict[str, Any]],
    implementation: Sequence[dict[str, Any]],
    producer_commit: str,
    run_id: str,
) -> dict[str, Any]:
    if _SAFE_RUN_ID.fullmatch(run_id) is None:
        raise NativeTMDocumentArtifactError("native TM artifact run_id is invalid")
    policy = _validate_policy_payload(policy)
    runtime_inputs = [copy.deepcopy(record) for record in runtime_inputs]
    if any(
        not isinstance(record, dict)
        or set(record) != {"kind", "path", "sha256", "size_bytes"}
        or not isinstance(record.get("kind"), str)
        or not isinstance(record.get("path"), str)
        for record in runtime_inputs
    ) or runtime_inputs != sorted(
        runtime_inputs, key=lambda record: (record["kind"], record["path"])
    ):
        raise NativeTMDocumentArtifactError("native TM runtime ledger order drifted")
    allowed_kinds = set(policy["role_isolation"]["runtime_input_allowlist"])
    if {record["kind"] for record in runtime_inputs} != allowed_kinds:
        raise NativeTMDocumentArtifactError("native TM runtime input inventory is incomplete")
    if any(
        not isinstance(record, dict) or not isinstance(record.get("path"), str)
        for record in implementation
    ):
        raise NativeTMDocumentArtifactError("native TM implementation ledger is invalid")
    _validate_path_isolation(
        [record["path"] for record in runtime_inputs]
        + [record["path"] for record in implementation],
        policy,
    )
    _preflight_discovery_path_isolation(
        project_root=project_root,
        path=discovery_path,
        expected_sha256=discovery_sha256,
        policy=policy,
    )
    _source_record, _role_record, source_identity = _registered_source_from_bytes(
        project_root=project_root,
        source_pdf=source_pdf,
        source_registry_bytes=source_registry_bytes,
        role_registry_bytes=role_registry_bytes,
    )
    discovery_payload, discovery_bytes, boundary, signal_by_page = _strict_load_statement_discovery(
        project_root=project_root,
        source_pdf=source_pdf,
        path=discovery_path,
        expected_sha256=discovery_sha256,
        expected_source=source_identity,
        policy=policy,
    )
    region_policy, geometry_config, quality_config = _configuration_materials(config_bytes_by_kind)
    pages = _build_pages(
        source_pdf=source_pdf,
        source_sha256=source_identity["sha256"],
        boundary=boundary,
        signal_by_page=signal_by_page,
        policy=policy,
        region_policy=region_policy,
        geometry_config=geometry_config,
        quality_config=quality_config,
    )
    discovery_page_count = discovery_payload["native_text"]["page_count"]
    if len(pages) != discovery_page_count or [page["page"] for page in pages] != list(
        range(1, discovery_page_count + 1)
    ):
        raise NativeTMDocumentArtifactError(
            "source PDF page denominator differs from accepted discovery"
        )
    note_inventory = _note_inventory(pages, boundary)
    table_inventory = _table_inventory(pages)
    classification_counts = Counter(page["classification"] for page in pages)
    unassessed_pages = [page["page"] for page in pages if page["classification"] == "UNASSESSED"]
    every_page_classified = not unassessed_pages
    full_document_complete = (
        every_page_classified and table_inventory["all_table_ownership_bounded"]
    )
    status = _COMPLETE_STATUS if full_document_complete else _PARTIAL_STATUS
    discovery_relative = _relative_path(
        project_root, discovery_path, "accepted statement discovery"
    )
    payload: dict[str, Any] = {
        "format_version": _OUTPUT_FORMAT,
        "policy": _POLICY_NAME,
        "claim_boundary": _CLAIM_BOUNDARY,
        "status": status,
        "run_id": run_id,
        "source": source_identity,
        "statement_discovery": {
            "path": discovery_relative,
            "sha256": discovery_sha256,
            "size_bytes": len(discovery_bytes),
            "format_version": discovery_payload["format_version"],
            "policy": discovery_payload["policy"],
            "claim_boundary": discovery_payload["claim_boundary"],
            "status": discovery_payload["status"],
            "run_id": discovery_payload["run_id"],
            "producer_git_commit": discovery_payload["code"]["commit"],
            "notes_boundary_page": boundary,
            "full_pdf_page_denominator": discovery_page_count,
        },
        "code": {
            "commit": producer_commit,
            "dirty": False,
            "implementation": copy.deepcopy(list(implementation)),
        },
        "authority": {
            "notes_boundary": "TRUSTED_ACCEPTED_STATEMENT_DISCOVERY",
            "geometry": "PYMUPDF_VISIBLE_NATIVE_TEXT",
            "table_regions": "NATIVE_TM_LOCAL_TABLE_REGIONS_V1",
            "page_classification": "SOURCE_VISIBLE_GENERIC_EVIDENCE_AFTER_NOTES_BOUNDARY",
            "schema_mapper": None,
            "semantic_reader": None,
        },
        "isolation": {
            "prior_answer_artifacts_loaded": False,
            "historical_values_loaded": False,
            "role_a_outputs_loaded": False,
            "reference_outputs_loaded": False,
            "schema_inputs_loaded": False,
            "bank_identity_used_for_routing": False,
            "filename_identity_used_for_routing": False,
            "fixed_page_rules_used_for_routing": False,
            "note_number_used_for_routing": False,
            "expected_counts_used_for_routing": False,
        },
        "inputs": {
            "runtime_read_ledger": runtime_inputs,
            "runtime_read_ledger_sha256": stable_records_hash(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                for record in runtime_inputs
            ),
        },
        "producer_snapshots": _producer_snapshots(
            policy_path=policy_relative,
            policy_bytes=policy_bytes,
            policy=policy,
            config_records=config_records,
            config_bytes_by_kind=config_bytes_by_kind,
        ),
        "completeness": {
            "page_denominator": "ALL_PDF_PAGES",
            "pdf_page_count": len(pages),
            "page_classification_record_count": len(pages),
            "assessed_classification_count": len(pages) - len(unassessed_pages),
            "classification_counts": {
                classification: classification_counts[classification]
                for classification in _CLASSIFICATIONS
            },
            "unassessed_pages": unassessed_pages,
            "every_page_classified": every_page_classified,
            "all_table_ownership_bounded": table_inventory["all_table_ownership_bounded"],
            "full_document_complete": full_document_complete,
            "completion_rule": ("EVERY_PAGE_CLASSIFIED_AND_ALL_TABLE_OWNERSHIP_BOUNDED"),
        },
        "note_inventory": note_inventory,
        "table_inventory": table_inventory,
        "pages": pages,
    }
    return json.loads(_canonical_json_bytes(payload))


def _runtime_inputs_current(
    *,
    project_root: Path,
    source_pdf: Path,
    discovery_path: Path,
    policy_path: Path,
    policy: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, bytes]]:
    paths = {
        "SOURCE_PDF": source_pdf,
        "SOURCE_REGISTRY": _resolve_under_root(
            project_root, policy["source_registry"], "source registry"
        ),
        "DATASET_ROLE_REGISTRY": _resolve_under_root(
            project_root, policy["dataset_role_registry"], "dataset-role registry"
        ),
        "ACCEPTED_STATEMENT_DISCOVERY": discovery_path,
        "THIS_POLICY": policy_path,
        "NATIVE_TM_REGION_POLICY": _resolve_under_root(
            project_root,
            policy["configuration"]["native_tm_region_policy"]["path"],
            "native TM region policy",
        ),
        "GEOMETRY_CONFIG": _resolve_under_root(
            project_root,
            policy["configuration"]["geometry_config"]["path"],
            "geometry config",
        ),
        "NATIVE_TEXT_QUALITY_CONFIG": _resolve_under_root(
            project_root,
            policy["configuration"]["native_text_quality_config"]["path"],
            "native-text quality config",
        ),
    }
    records = [_file_identity(path, project_root, kind) for kind, path in paths.items()]
    records.sort(key=lambda record: (record["kind"], record["path"]))
    bytes_by_kind = {kind: _read_stable_bytes(path, kind) for kind, path in paths.items()}
    return records, bytes_by_kind


def _config_records_from_runtime(
    runtime_inputs: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_kind = {record["kind"]: record for record in runtime_inputs}
    return [copy.deepcopy(by_kind[kind]) for kind in _CONFIG_KINDS]


def build_registered_native_tm_document_artifact(
    project_root: Path,
    source_pdf: Path,
    discovery_path: Path,
    discovery_sha256: str,
    policy_path: Path,
    run_id: str,
) -> dict[str, Any]:
    """Build a registered full-PDF native quantitative-TM inventory.

    The accepted statement discovery supplies only the source-visible notes
    boundary.  Local table geometry is never allowed to move that boundary or
    to relabel a main-statement page as TM.
    """

    project_root = project_root.resolve()
    source_pdf = source_pdf.resolve()
    discovery_path = discovery_path.resolve()
    policy_path = policy_path.resolve()
    code = _current_git_state(project_root)
    policy = load_native_tm_document_artifact_policy(policy_path, project_root)
    _validate_path_isolation(
        [
            _relative_path(project_root, source_pdf, "source PDF"),
            _relative_path(project_root, discovery_path, "accepted statement discovery"),
            _relative_path(project_root, policy_path, "native TM document policy"),
        ],
        policy,
    )
    _preflight_discovery_path_isolation(
        project_root=project_root,
        path=discovery_path,
        expected_sha256=discovery_sha256,
        policy=policy,
    )
    runtime_inputs, input_bytes = _runtime_inputs_current(
        project_root=project_root,
        source_pdf=source_pdf,
        discovery_path=discovery_path,
        policy_path=policy_path,
        policy=policy,
    )
    implementation = _implementation_ledger(project_root)
    committed_implementation = _implementation_ledger_at_commit(project_root, code["commit"])
    if implementation != committed_implementation:
        raise NativeTMDocumentArtifactError(
            "native TM implementation differs from the clean producer HEAD"
        )
    tracked_kinds = {
        "SOURCE_REGISTRY",
        "DATASET_ROLE_REGISTRY",
        "THIS_POLICY",
        *_CONFIG_KINDS,
    }
    by_kind = {record["kind"]: record for record in runtime_inputs}
    for kind in tracked_kinds:
        expected = _file_identity_at_commit(
            project_root, code["commit"], by_kind[kind]["path"], kind=kind
        )
        if by_kind[kind] != expected:
            raise NativeTMDocumentArtifactError(f"{kind} differs from the clean producer HEAD")
    config_bytes = {kind: input_bytes[kind] for kind in _CONFIG_KINDS}
    payload = _build_core(
        project_root=project_root,
        source_pdf=source_pdf,
        discovery_path=discovery_path,
        discovery_sha256=discovery_sha256,
        policy_relative=POLICY_RELATIVE_PATH.as_posix(),
        policy_bytes=input_bytes["THIS_POLICY"],
        policy=policy,
        config_records=_config_records_from_runtime(runtime_inputs),
        config_bytes_by_kind=config_bytes,
        source_registry_bytes=input_bytes["SOURCE_REGISTRY"],
        role_registry_bytes=input_bytes["DATASET_ROLE_REGISTRY"],
        runtime_inputs=runtime_inputs,
        implementation=implementation,
        producer_commit=code["commit"],
        run_id=run_id,
    )
    final_runtime, _ = _runtime_inputs_current(
        project_root=project_root,
        source_pdf=source_pdf,
        discovery_path=discovery_path,
        policy_path=policy_path,
        policy=policy,
    )
    if final_runtime != runtime_inputs:
        raise NativeTMDocumentArtifactError("native TM runtime inputs changed during build")
    if _implementation_ledger(project_root) != implementation:
        raise NativeTMDocumentArtifactError("native TM implementation changed during build")
    final_state = _current_git_state(project_root)
    if final_state != code:
        raise NativeTMDocumentArtifactError("producer HEAD changed during native TM build")
    return payload


_PRODUCER_REPLAY_BOOTSTRAP = r"""
import pathlib
import sys

source_tree = pathlib.Path(sys.argv[1]).resolve()
repository = pathlib.Path(sys.argv[2]).resolve()
sys.path.insert(0, str(source_tree / "src"))
from bctc_ai.document_phase import native_tm_document_artifact as producer

expected_module = (
    source_tree / "src/bctc_ai/document_phase/native_tm_document_artifact.py"
).resolve()
if pathlib.Path(producer.__file__).resolve() != expected_module:
    raise RuntimeError("producer replay imported outside its isolated source tree")
payload = producer.build_registered_native_tm_document_artifact(
    repository,
    repository / sys.argv[3],
    repository / sys.argv[4],
    sys.argv[5],
    repository / producer.POLICY_RELATIVE_PATH,
    sys.argv[6],
)
sys.stdout.buffer.write(producer._canonical_json_bytes(payload))
"""


def _lexical_project_path(project_root: Path, raw_path: Path, label: str) -> tuple[Path, str]:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        try:
            relative = candidate.relative_to(project_root).as_posix()
        except ValueError as exc:
            raise NativeTMDocumentArtifactError(
                f"{label} must stay inside the project root"
            ) from exc
    else:
        relative = candidate.as_posix()
    relative = _canonical_relative_path(relative, label)
    return project_root.joinpath(*PurePosixPath(relative).parts), relative


def _write_new_file(path: Path, payload: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, mode)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise NativeTMDocumentArtifactError(
                    "isolated producer replay file write was incomplete"
                )
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _install_replay_input(clone_root: Path, relative: str, payload: bytes, label: str) -> None:
    destination = _resolve_under_root(clone_root, relative, label)
    if destination.exists():
        if _read_stable_bytes(destination, label) != payload:
            raise NativeTMDocumentArtifactError(
                f"producer-commit {label} differs from replay input"
            )
        return
    _write_new_file(destination, payload)


def _isolated_subprocess_environment() -> dict[str, str]:
    environment = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
    }
    return environment


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
        raise NativeTMDocumentArtifactError(
            "producer-commit isolated replay process failed"
        ) from exc
    if result.returncode != 0:
        raise NativeTMDocumentArtifactError("producer-commit isolated replay process failed")
    return result.stdout


def _validate_v1_replay_implementation(
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
        raise NativeTMDocumentArtifactError("native TM artifact producer identity is invalid")
    implementation = code["implementation"]
    if [record.get("path") for record in implementation if isinstance(record, dict)] != list(
        _V1_REPLAY_IMPLEMENTATION_PATHS
    ):
        raise NativeTMDocumentArtifactError("native TM artifact V1 implementation manifest drifted")
    expected = [
        _file_identity_at_commit(project_root, code["commit"], relative)
        for relative in _V1_REPLAY_IMPLEMENTATION_PATHS
    ]
    if implementation != expected:
        raise NativeTMDocumentArtifactError(
            "native TM artifact implementation is not bound to its producer commit"
        )
    return code["commit"], copy.deepcopy(implementation)


def _validate_v1_artifact_location(
    *,
    project_root: Path,
    producer_commit: str,
    payload: Mapping[str, Any],
    artifact_relative: str,
) -> None:
    policy_bytes = _git_file_bytes(project_root, producer_commit, POLICY_RELATIVE_PATH.as_posix())
    producer_policy = _yaml_bytes(policy_bytes, "producer native TM policy")
    snapshots = payload.get("producer_snapshots")
    policy_snapshot = snapshots.get("policy") if isinstance(snapshots, dict) else None
    expected_snapshot = {
        "path": POLICY_RELATIVE_PATH.as_posix(),
        "sha256": sha256_bytes(policy_bytes),
        "size_bytes": len(policy_bytes),
        "payload_sha256": _canonical_record_sha256(producer_policy),
        "payload": producer_policy,
    }
    if policy_snapshot != expected_snapshot:
        raise NativeTMDocumentArtifactError("native TM artifact producer policy snapshot drifted")
    role_isolation = producer_policy.get("role_isolation")
    output = producer_policy.get("output")
    if (
        producer_policy.get("version") != 1
        or producer_policy.get("policy") != _POLICY_NAME
        or producer_policy.get("claim_boundary") != _CLAIM_BOUNDARY
        or not isinstance(role_isolation, dict)
        or role_isolation.get("forbidden_path_fragments") != list(_V1_FORBIDDEN_PATH_FRAGMENTS)
        or not isinstance(output, dict)
        or output.get("format") != _OUTPUT_FORMAT
        or output.get("output_directory") != _OUTPUT_DIRECTORY
    ):
        raise NativeTMDocumentArtifactError(
            "native TM artifact producer V1 isolation policy drifted"
        )
    normalized = "/" + artifact_relative.casefold().strip("/")
    if any(fragment in normalized for fragment in _V1_FORBIDDEN_PATH_FRAGMENTS):
        raise NativeTMDocumentArtifactError(
            f"registered native TM artifact path is forbidden: {artifact_relative}"
        )


def _producer_commit_replay(
    *,
    project_root: Path,
    producer_commit: str,
    implementation: Sequence[dict[str, Any]],
    source_relative: str,
    source_bytes: bytes,
    discovery_relative: str,
    discovery_bytes: bytes,
    discovery_sha256: str,
    run_id: str,
) -> bytes:
    temporary_root = Path(tempfile.mkdtemp(prefix="native-tm-producer-replay-"))
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
        _install_replay_input(clone_root, source_relative, source_bytes, "source PDF")
        _install_replay_input(
            clone_root,
            discovery_relative,
            discovery_bytes,
            "accepted statement discovery",
        )
        status = _run_checked_process(
            ("git", "status", "--porcelain", "--untracked-files=all"),
            cwd=clone_root,
            environment=environment,
        )
        if status.strip():
            raise NativeTMDocumentArtifactError(
                "producer-commit replay repository is not clean after input restoration"
            )
        replay_tree = temporary_root / "isolated-source"
        for record in implementation:
            relative = record["path"]
            module_bytes = _git_file_bytes(project_root, producer_commit, relative)
            _write_new_file(replay_tree.joinpath(*PurePosixPath(relative).parts), module_bytes)
        return _run_checked_process(
            (
                sys.executable,
                "-I",
                "-c",
                _PRODUCER_REPLAY_BOOTSTRAP,
                str(replay_tree),
                str(clone_root),
                source_relative,
                discovery_relative,
                discovery_sha256,
                run_id,
            ),
            cwd=temporary_root,
            environment=environment,
        )
    finally:
        try:
            shutil.rmtree(temporary_root, ignore_errors=True)
        except Exception:
            pass


def _load_registered_native_tm_document_artifact_held(
    guard: _ArtifactReadGuard,
    *,
    project_root: Path,
    expected_sha256: str,
) -> dict[str, Any]:
    artifact_relative = guard.relative_path
    encoded = guard.payload
    if sha256_bytes(encoded) != expected_sha256:
        raise NativeTMDocumentArtifactError("native TM artifact does not match its trusted SHA-256")
    try:
        payload = json.loads(encoded)
    except json.JSONDecodeError as exc:
        raise NativeTMDocumentArtifactError("native TM artifact is invalid JSON") from exc
    if not isinstance(payload, dict) or encoded != _canonical_json_bytes(payload):
        raise NativeTMDocumentArtifactError("native TM artifact is not canonical JSON")
    if payload.get("format_version") != _OUTPUT_FORMAT:
        raise NativeTMDocumentArtifactError("native TM artifact format is invalid")
    producer_commit, implementation = _validate_v1_replay_implementation(
        project_root, payload.get("code")
    )
    _validate_v1_artifact_location(
        project_root=project_root,
        producer_commit=producer_commit,
        payload=payload,
        artifact_relative=artifact_relative,
    )
    run_id = payload.get("run_id")
    source = payload.get("source")
    discovery = payload.get("statement_discovery")
    if (
        not isinstance(run_id, str)
        or _SAFE_RUN_ID.fullmatch(run_id) is None
        or not isinstance(source, dict)
        or not isinstance(source.get("relative_path"), str)
        or not isinstance(source.get("sha256"), str)
        or _SHA256.fullmatch(source["sha256"]) is None
        or isinstance(source.get("size_bytes"), bool)
        or not isinstance(source.get("size_bytes"), int)
        or not isinstance(discovery, dict)
        or not isinstance(discovery.get("path"), str)
        or not isinstance(discovery.get("sha256"), str)
        or _SHA256.fullmatch(discovery["sha256"]) is None
        or isinstance(discovery.get("size_bytes"), bool)
        or not isinstance(discovery.get("size_bytes"), int)
    ):
        raise NativeTMDocumentArtifactError("native TM artifact replay provenance is invalid")
    source_relative = _canonical_relative_path(
        source["relative_path"], "native TM artifact source path"
    )
    discovery_relative = _canonical_relative_path(
        discovery["path"], "native TM artifact discovery path"
    )
    source_pdf = _resolve_under_root(project_root, source_relative, "source PDF")
    discovery_path = _resolve_under_root(
        project_root, discovery_relative, "accepted statement discovery"
    )
    source_bytes = _read_stable_bytes(source_pdf, "source PDF")
    discovery_bytes = _read_stable_bytes(discovery_path, "accepted statement discovery")
    if (
        len(source_bytes) != source["size_bytes"]
        or sha256_bytes(source_bytes) != source["sha256"]
        or len(discovery_bytes) != discovery["size_bytes"]
        or sha256_bytes(discovery_bytes) != discovery["sha256"]
    ):
        raise NativeTMDocumentArtifactError(
            "native TM artifact replay inputs are absent or drifted"
        )
    replay_bytes = _producer_commit_replay(
        project_root=project_root,
        producer_commit=producer_commit,
        implementation=implementation,
        source_relative=source_relative,
        source_bytes=source_bytes,
        discovery_relative=discovery_relative,
        discovery_bytes=discovery_bytes,
        discovery_sha256=discovery["sha256"],
        run_id=run_id,
    )
    if replay_bytes != encoded:
        raise NativeTMDocumentArtifactError(
            "native TM artifact differs from producer-commit deterministic replay"
        )
    if (
        _read_stable_bytes(source_pdf, "source PDF") != source_bytes
        or _read_stable_bytes(discovery_path, "accepted statement discovery") != discovery_bytes
    ):
        raise NativeTMDocumentArtifactError("native TM replay inputs changed during strict replay")
    _revalidate_artifact_read_guard(guard)
    return copy.deepcopy(payload)


def _directory_open_flags() -> int:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    return flags


def _open_parent_directory(
    project_root: Path,
    relative_parent: PurePosixPath,
    *,
    create: bool = True,
) -> int:
    descriptor = os.open(project_root, _directory_open_flags())
    try:
        for part in relative_parent.parts:
            if create:
                try:
                    os.mkdir(part, 0o755, dir_fd=descriptor)
                    os.fsync(descriptor)
                except FileExistsError:
                    pass
            child = os.open(part, _directory_open_flags(), dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _same_inode(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        stat.S_ISREG(left.st_mode)
        and stat.S_ISREG(right.st_mode)
        and (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)
    )


def _artifact_stat_identity(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _read_artifact_descriptor(descriptor: int, label: str) -> tuple[bytes, os.stat_result]:
    before = os.fstat(descriptor)
    if not stat.S_ISREG(before.st_mode):
        raise NativeTMDocumentArtifactError(f"{label} is not a regular file")
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    remaining = before.st_size
    while remaining:
        block = os.read(descriptor, min(remaining, 1024 * 1024))
        if not block:
            raise NativeTMDocumentArtifactError(f"{label} was truncated while being read")
        chunks.append(block)
        remaining -= len(block)
    if os.read(descriptor, 1):
        raise NativeTMDocumentArtifactError(f"{label} grew while being read")
    after = os.fstat(descriptor)
    if _artifact_stat_identity(before) != _artifact_stat_identity(after):
        raise NativeTMDocumentArtifactError(f"{label} changed while being read")
    return b"".join(chunks), after


def _open_artifact_read_guard(project_root: Path, path: Path, relative: str) -> _ArtifactReadGuard:
    relative_path = PurePosixPath(relative)
    parent_descriptor: int | None = None
    artifact_descriptor: int | None = None
    completed = False
    try:
        parent_descriptor = _open_parent_directory(project_root, relative_path.parent, create=False)
        parent_identity = os.fstat(parent_descriptor)
        artifact_descriptor = os.open(
            relative_path.name,
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0),
            dir_fd=parent_descriptor,
        )
        payload, identity = _read_artifact_descriptor(
            artifact_descriptor, "registered native TM artifact"
        )
        linked = os.stat(
            relative_path.name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        if not _same_inode(identity, linked) or _artifact_stat_identity(
            identity
        ) != _artifact_stat_identity(linked):
            raise NativeTMDocumentArtifactError(
                "registered native TM artifact name changed while opening"
            )
        guard = _ArtifactReadGuard(
            project_root=project_root,
            path=path,
            relative_path=relative,
            basename=relative_path.name,
            parent_descriptor=parent_descriptor,
            parent_identity=parent_identity,
            artifact_descriptor=artifact_descriptor,
            identity=identity,
            payload=payload,
        )
        completed = True
        return guard
    except NativeTMDocumentArtifactError:
        raise
    except OSError as exc:
        raise NativeTMDocumentArtifactError(
            "registered native TM artifact path contains a symlink or is unreadable"
        ) from exc
    finally:
        if artifact_descriptor is not None and not completed:
            try:
                os.close(artifact_descriptor)
            except OSError:
                pass
        if parent_descriptor is not None and not completed:
            try:
                os.close(parent_descriptor)
            except OSError:
                pass


def _revalidate_artifact_read_guard(guard: _ArtifactReadGuard) -> None:
    payload, descriptor_identity = _read_artifact_descriptor(
        guard.artifact_descriptor, "registered native TM artifact"
    )
    revalidated_parent: int | None = None
    try:
        revalidated_parent = _open_parent_directory(
            guard.project_root,
            PurePosixPath(guard.relative_path).parent,
            create=False,
        )
        current_parent = os.fstat(revalidated_parent)
        linked = os.stat(
            guard.basename,
            dir_fd=revalidated_parent,
            follow_symlinks=False,
        )
    except OSError as exc:
        raise NativeTMDocumentArtifactError(
            "registered native TM artifact name changed during strict replay"
        ) from exc
    finally:
        if revalidated_parent is not None:
            try:
                os.close(revalidated_parent)
            except OSError:
                pass
    if (
        payload != guard.payload
        or (current_parent.st_dev, current_parent.st_ino)
        != (guard.parent_identity.st_dev, guard.parent_identity.st_ino)
        or _artifact_stat_identity(descriptor_identity) != _artifact_stat_identity(guard.identity)
        or not _same_inode(descriptor_identity, linked)
        or _artifact_stat_identity(descriptor_identity) != _artifact_stat_identity(linked)
    ):
        raise NativeTMDocumentArtifactError(
            "registered native TM artifact changed during strict replay"
        )


def _close_artifact_read_guard(guard: _ArtifactReadGuard) -> None:
    for descriptor in (guard.artifact_descriptor, guard.parent_descriptor):
        try:
            os.close(descriptor)
        except OSError:
            pass


def load_registered_native_tm_document_artifact(
    path: Path,
    *,
    project_root: Path,
    expected_sha256: str,
) -> dict[str, Any]:
    """Trusted-SHA load using an fd-held isolated producer-commit replay."""

    project_root = project_root.resolve()
    path, artifact_relative = _lexical_project_path(
        project_root, path, "registered native TM artifact"
    )
    if _SHA256.fullmatch(expected_sha256) is None:
        raise NativeTMDocumentArtifactError("trusted native TM artifact SHA-256 is invalid")
    if not artifact_relative.startswith(f"{_OUTPUT_DIRECTORY}/"):
        raise NativeTMDocumentArtifactError(
            "LOGIC_DEVELOPMENT native TM artifact must stay under output/development"
        )
    guard = _open_artifact_read_guard(project_root, path, artifact_relative)
    try:
        return _load_registered_native_tm_document_artifact_held(
            guard,
            project_root=project_root,
            expected_sha256=expected_sha256,
        )
    finally:
        _close_artifact_read_guard(guard)


def _read_output_descriptor(descriptor: int, size: int) -> bytes:
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        block = os.read(descriptor, min(remaining, 1024 * 1024))
        if not block:
            raise NativeTMDocumentArtifactError("native TM published descriptor was truncated")
        chunks.append(block)
        remaining -= len(block)
    if os.read(descriptor, 1):
        raise NativeTMDocumentArtifactError("native TM published descriptor grew during validation")
    return b"".join(chunks)


def _close_guard_best_effort(guard: _ExclusivePublicationGuard) -> None:
    for descriptor in (guard.output_descriptor, guard.parent_descriptor):
        try:
            os.close(descriptor)
        except OSError:
            pass


def _rollback_publication(guard: _ExclusivePublicationGuard, cause: BaseException) -> None:
    quarantine_name: str | None = None
    quarantine_descriptor: int | None = None
    captured_name = "captured-output"
    captured_descriptor: int | None = None
    foreign_captured = False
    try:
        for _attempt in range(256):
            candidate = f".{guard.basename}.rollback-{secrets.token_hex(12)}"
            try:
                os.mkdir(candidate, 0o700, dir_fd=guard.parent_descriptor)
            except FileExistsError:
                continue
            quarantine_name = candidate
            break
        if quarantine_name is None:
            raise NativeTMDocumentArtifactError("cannot allocate native TM rollback quarantine")
        quarantine_descriptor = os.open(
            quarantine_name,
            _directory_open_flags(),
            dir_fd=guard.parent_descriptor,
        )
        try:
            os.rename(
                guard.basename,
                captured_name,
                src_dir_fd=guard.parent_descriptor,
                dst_dir_fd=quarantine_descriptor,
            )
        except FileNotFoundError:
            return
        try:
            captured_descriptor = os.open(
                captured_name,
                os.O_RDONLY
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_NONBLOCK", 0),
                dir_fd=quarantine_descriptor,
            )
            captured_identity = os.fstat(captured_descriptor)
            foreign_captured = not _same_inode(guard.identity, captured_identity)
        except OSError:
            foreign_captured = True
        if foreign_captured:
            try:
                os.link(
                    captured_name,
                    guard.basename,
                    src_dir_fd=quarantine_descriptor,
                    dst_dir_fd=guard.parent_descriptor,
                    follow_symlinks=False,
                )
            except OSError as exc:
                raise NativeTMDocumentArtifactError(
                    "native TM rollback preserved a foreign replacement in quarantine"
                ) from exc
            os.fsync(guard.parent_descriptor)
            os.unlink(captured_name, dir_fd=quarantine_descriptor)
            os.fsync(quarantine_descriptor)
            foreign_captured = False
            raise NativeTMDocumentArtifactError(
                "refusing to roll back a changed native TM artifact; replacement restored"
            ) from cause
        os.unlink(captured_name, dir_fd=quarantine_descriptor)
        os.fsync(quarantine_descriptor)
        os.fsync(guard.parent_descriptor)
    except NativeTMDocumentArtifactError:
        raise
    except BaseException as exc:
        raise NativeTMDocumentArtifactError(
            f"native TM strict-replay rollback failed: {exc}"
        ) from cause
    finally:
        if captured_descriptor is not None:
            try:
                os.close(captured_descriptor)
            except OSError:
                pass
        if quarantine_descriptor is not None:
            try:
                os.close(quarantine_descriptor)
            except OSError:
                pass
        if quarantine_name is not None and not foreign_captured:
            try:
                os.rmdir(quarantine_name, dir_fd=guard.parent_descriptor)
                os.fsync(guard.parent_descriptor)
            except OSError:
                pass


def _write_exclusive(project_root: Path, path: Path, payload: bytes) -> _ExclusivePublicationGuard:
    path, relative = _lexical_project_path(project_root, path, "native TM output")
    relative_path = PurePosixPath(relative)
    parent_descriptor = _open_parent_directory(project_root, relative_path.parent)
    flags = (
        os.O_RDWR
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        output_descriptor = os.open(
            relative_path.name,
            flags,
            0o644,
            dir_fd=parent_descriptor,
        )
    except OSError as exc:
        os.close(parent_descriptor)
        if exc.errno == errno.EEXIST:
            raise NativeTMDocumentArtifactError(
                f"refusing to overwrite native TM artifact: {relative}"
            ) from exc
        raise NativeTMDocumentArtifactError(
            f"cannot exclusively create native TM artifact: {relative}"
        ) from exc
    identity = os.fstat(output_descriptor)
    guard = _ExclusivePublicationGuard(
        path=path,
        relative_path=relative,
        basename=relative_path.name,
        parent_descriptor=parent_descriptor,
        output_descriptor=output_descriptor,
        identity=identity,
    )
    try:
        if not stat.S_ISREG(identity.st_mode):
            raise NativeTMDocumentArtifactError("native TM output descriptor is not a regular file")
        view = memoryview(payload)
        while view:
            written = os.write(output_descriptor, view)
            if written <= 0:
                raise NativeTMDocumentArtifactError(
                    "native TM artifact output write was incomplete"
                )
            view = view[written:]
        os.fchmod(output_descriptor, 0o644)
        os.fsync(output_descriptor)
        final_descriptor = os.fstat(output_descriptor)
        linked = os.stat(
            relative_path.name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        if (
            not _same_inode(identity, final_descriptor)
            or not _same_inode(final_descriptor, linked)
            or final_descriptor.st_size != len(payload)
            or _read_output_descriptor(output_descriptor, len(payload)) != payload
        ):
            raise NativeTMDocumentArtifactError(
                "native TM published output identity or bytes drifted"
            )
        os.fsync(parent_descriptor)
        return guard
    except BaseException as publication_error:
        try:
            _rollback_publication(guard, publication_error)
        finally:
            _close_guard_best_effort(guard)
        raise


def publish_registered_native_tm_document_artifact(
    project_root: Path,
    source_pdf: Path,
    discovery_path: Path,
    discovery_sha256: str,
    policy_path: Path,
    run_id: str,
    output_path: Path,
) -> NativeTMDocumentArtifactPublication:
    """Build, exclusively publish, strict-replay, and return one artifact."""

    project_root = project_root.resolve()
    output_path, output_relative = _lexical_project_path(
        project_root, output_path, "native TM output"
    )
    if not output_relative.startswith(f"{_OUTPUT_DIRECTORY}/"):
        raise NativeTMDocumentArtifactError(
            "LOGIC_DEVELOPMENT native TM output must stay under output/development"
        )
    policy = load_native_tm_document_artifact_policy(policy_path.resolve(), project_root)
    _validate_path_isolation([output_relative], policy)
    payload = build_registered_native_tm_document_artifact(
        project_root,
        source_pdf,
        discovery_path,
        discovery_sha256,
        policy_path,
        run_id,
    )
    encoded = _canonical_json_bytes(payload)
    guard = _write_exclusive(project_root, output_path, encoded)
    digest = sha256_bytes(encoded)
    try:
        replayed = load_registered_native_tm_document_artifact(
            output_path,
            project_root=project_root,
            expected_sha256=digest,
        )
        if replayed != payload:
            raise NativeTMDocumentArtifactError("published native TM artifact replay drifted")
    except BaseException as exc:
        try:
            _rollback_publication(guard, exc)
        finally:
            _close_guard_best_effort(guard)
        raise
    _close_guard_best_effort(guard)
    return NativeTMDocumentArtifactPublication(
        path=output_path,
        sha256=digest,
        size_bytes=len(encoded),
        payload=payload,
    )


__all__ = [
    "POLICY_RELATIVE_PATH",
    "NativeTMDocumentArtifactError",
    "NativeTMDocumentArtifactPublication",
    "build_registered_native_tm_document_artifact",
    "load_native_tm_document_artifact_policy",
    "load_registered_native_tm_document_artifact",
    "publish_registered_native_tm_document_artifact",
]
