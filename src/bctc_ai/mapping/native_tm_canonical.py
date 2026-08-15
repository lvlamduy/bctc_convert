from __future__ import annotations

import copy
import io
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

import yaml

from bctc_ai.core.hashing import sha256_bytes, stable_records_hash
from bctc_ai.core.text import normalize_text, retrieval_key
from bctc_ai.document_phase import native_tm_document_artifact as _native_document
from bctc_ai.rows import native_tm_observations as _native_observations

POLICY_RELATIVE_PATH = Path("config/mapping/native-tm-canonical-v1.yaml")

_POLICY_NAME = "REGISTERED_NATIVE_TM_CANONICAL_MAPPING_V1"
_CLAIM_BOUNDARY = "BOUNDED_SOURCE_EVIDENCE_TM_CANONICAL_MAPPING_ONLY"
_OUTPUT_FORMAT = "REGISTERED_NATIVE_TM_CANONICAL_MAPPING_RESULT_V1"
_OUTPUT_STATUS = "COMPLETE_NATIVE_TM_CANONICAL_DISPOSITION_ACCOUNTING"
_OUTPUT_DIRECTORY = "output/development"
_INPUT_FORMAT = "REGISTERED_NATIVE_TM_OBSERVATIONS_RESULT_V1"
_INPUT_POLICY = "REGISTERED_NATIVE_TM_OBSERVATIONS_V1"
_INPUT_CLAIM = "SOURCE_ONLY_NATIVE_TM_OBSERVATION_FLATTENING"
_INPUT_STATUS = "COMPLETE_NATIVE_TM_SOURCE_OBJECT_ACCOUNTING"
_OBSERVATION_POLICY_PATH = "config/rows/native-tm-observations-v1.yaml"
_NATIVE_DOCUMENT_FORMAT = "REGISTERED_NATIVE_TM_FULL_DOCUMENT_ARTIFACT_RESULT_V1"
_NATIVE_DOCUMENT_POLICY = "REGISTERED_NATIVE_TM_FULL_DOCUMENT_ARTIFACT_V1"
_NATIVE_DOCUMENT_CLAIM = "SOURCE_VISIBLE_NATIVE_TM_INVENTORY_ONLY"
_NATIVE_DOCUMENT_STATUSES = (
    "COMPLETE_NATIVE_TM_FULL_DOCUMENT_ARTIFACT",
    "PARTIAL_NATIVE_TM_FULL_DOCUMENT_ARTIFACT",
)
_NATIVE_DOCUMENT_POLICY_PATH = "config/document_phase/native-tm-document-artifact-v1.yaml"
_DISCOVERY_FORMAT = "REGISTERED_NATIVE_TEXT_STATEMENT_DISCOVERY_RESULT_V1"
_DISCOVERY_POLICY = "REGISTERED_NATIVE_TEXT_STATEMENT_DISCOVERY_V1"
_DISCOVERY_CLAIM = "STATEMENT_PAGE_DISCOVERY_ONLY"
_DISCOVERY_STATUS = "ACCEPTED_NATIVE_TEXT_STATEMENT_DISCOVERY"
_DATASET_ROLE = "LOGIC_DEVELOPMENT"
_STATEMENT_TYPE = "TM"
_SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_TERMINAL_OUTCOMES = (
    "OBSERVED_VALUE",
    "OBSERVED_ZERO",
    "DASH",
    "BLANK",
    "NOT_OBSERVED",
    "NOT_APPLICABLE",
    "AMBIGUOUS",
    "UNRESOLVED",
)
_ACCEPTED_ALIAS_TYPES = (
    "USER_SUPPLIED_HIERARCHY_LABEL",
    "AUDITED_SCHEMA_ALIAS",
)
_FORBIDDEN_PATH_FRAGMENTS = (
    "/role-a/",
    "/role_a/",
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
_OBSERVATION_FORBIDDEN_PATH_FRAGMENTS = (
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
_NATIVE_DOCUMENT_FORBIDDEN_PATH_FRAGMENTS = tuple(
    fragment
    for fragment in _OBSERVATION_FORBIDDEN_PATH_FRAGMENTS
    if fragment not in {"/alias/", "/aliases/", "/mapping/", "/mappings/"}
)
_NATIVE_DOCUMENT_IMPLEMENTATION_PATHS = (
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
_OBSERVATION_IMPLEMENTATION_PATHS = (
    *_NATIVE_DOCUMENT_IMPLEMENTATION_PATHS,
    "src/bctc_ai/rows/native_tm_observations.py",
)
_IMPLEMENTATION_PATHS = (
    *_OBSERVATION_IMPLEMENTATION_PATHS,
    "src/bctc_ai/mapping/__init__.py",
    "src/bctc_ai/mapping/native_tm_canonical.py",
)

_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_XLSX_NS = {"m": _MAIN_NS, "r": _REL_NS, "p": _PKG_REL_NS}


class NativeTMCanonicalMappingError(RuntimeError):
    """A registered native-TM canonical mapping failed closed."""


@dataclass(frozen=True)
class NativeTMCanonicalMappingPublication:
    path: Path
    sha256: str
    size_bytes: int
    payload: dict[str, Any]


@dataclass(frozen=True)
class _Candidate:
    report_norm_id: int
    match_basis: str
    matched_retrieval_key: str
    alias_authority_type: str | None
    alias_authority_evidence_sha256: str | None


@dataclass(frozen=True)
class _RootClaim:
    root_id: int
    context_id: str
    context: dict[str, Any]
    rows: tuple[dict[str, Any], ...]
    dimensions: tuple[dict[str, Any], ...]
    anchors: tuple[tuple[dict[str, Any], _Candidate], ...]
    source_object_ids: frozenset[str]


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
        raise NativeTMCanonicalMappingError("native TM canonical payload is not JSON-safe") from exc
    return (encoded + "\n").encode("utf-8")


def _record_sha256(value: Any) -> str:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise NativeTMCanonicalMappingError("native TM canonical record is not JSON-safe") from exc
    return sha256_bytes(encoded)


def _stable_records_sha256(records: Sequence[Mapping[str, Any]]) -> str:
    return stable_records_hash(
        json.dumps(
            record,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        for record in records
    )


def _runtime_ledger_sha256(records: Sequence[Mapping[str, Any]]) -> str:
    return _stable_records_sha256(records)


def _canonical_relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise NativeTMCanonicalMappingError(f"{label} is not a canonical project-relative path")
    candidate = PurePosixPath(value)
    if (
        candidate.is_absolute()
        or value != candidate.as_posix()
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise NativeTMCanonicalMappingError(f"{label} is not a canonical project-relative path")
    return value


def _lexical_project_path(project_root: Path, raw_path: Path, label: str) -> tuple[Path, str]:
    project_root = project_root.resolve()
    candidate = Path(raw_path)
    if candidate.is_absolute():
        try:
            relative = candidate.relative_to(project_root).as_posix()
        except ValueError as exc:
            raise NativeTMCanonicalMappingError(
                f"{label} must stay inside the project root"
            ) from exc
    else:
        relative = candidate.as_posix()
    relative = _canonical_relative_path(relative, label)
    return project_root.joinpath(*PurePosixPath(relative).parts), relative


def _validate_paths_against_fragments(
    paths: Sequence[str], fragments: Sequence[str], label: str
) -> None:
    for raw_path in paths:
        relative = _canonical_relative_path(raw_path, "runtime path")
        normalized = "/" + relative.casefold().strip("/")
        if any(fragment in normalized for fragment in fragments):
            raise NativeTMCanonicalMappingError(
                f"{label} path is forbidden by role isolation: {relative}"
            )


def _validate_path_isolation(paths: Sequence[str]) -> None:
    _validate_paths_against_fragments(paths, _FORBIDDEN_PATH_FRAGMENTS, "runtime")


def _open_guard(project_root: Path, path: Path, relative: str, label: str) -> Any:
    try:
        return _native_document._open_artifact_read_guard(project_root, path, relative)
    except _native_document.NativeTMDocumentArtifactError as exc:
        raise NativeTMCanonicalMappingError(
            f"{label} path contains a symlink or is unreadable"
        ) from exc


def _close_guard(guard: Any) -> None:
    _native_document._close_artifact_read_guard(guard)


def _revalidate_guard(guard: Any, label: str) -> None:
    try:
        _native_document._revalidate_artifact_read_guard(guard)
    except _native_document.NativeTMDocumentArtifactError as exc:
        raise NativeTMCanonicalMappingError(f"{label} changed during processing") from exc


def _identity_from_guard(guard: Any, kind: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "path": guard.relative_path,
        "sha256": sha256_bytes(guard.payload),
        "size_bytes": len(guard.payload),
    }


def _require_exact(value: Any, expected: Any, label: str) -> None:
    if value != expected:
        raise NativeTMCanonicalMappingError(f"{label} contract drifted")


def _validate_identity(value: Any, expected: Mapping[str, str], label: str) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {"path", "sha256"}:
        raise NativeTMCanonicalMappingError(f"{label} identity is invalid")
    _require_exact(value, dict(expected), label)
    return {"path": str(value["path"]), "sha256": str(value["sha256"])}


def _validate_policy_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise NativeTMCanonicalMappingError("native TM canonical policy must be an object")
    expected_top = {
        "version",
        "policy",
        "claim_boundary",
        "require_clean_git",
        "accepted_native_tm_observations",
        "schema_authority",
        "typed_alias_authority",
        "routing",
        "local_completion",
        "coverage",
        "role_isolation",
        "output",
    }
    if set(payload) != expected_top:
        raise NativeTMCanonicalMappingError("native TM canonical policy fields drifted")
    _require_exact(
        {key: payload[key] for key in ("version", "policy", "claim_boundary", "require_clean_git")},
        {
            "version": 1,
            "policy": _POLICY_NAME,
            "claim_boundary": _CLAIM_BOUNDARY,
            "require_clean_git": True,
        },
        "native TM canonical policy identity",
    )
    _require_exact(
        payload["accepted_native_tm_observations"],
        {
            "format_version": _INPUT_FORMAT,
            "policy": _INPUT_POLICY,
            "claim_boundary": _INPUT_CLAIM,
            "status": _INPUT_STATUS,
            "required_dataset_role": _DATASET_ROLE,
            "trusted_sha256_required": True,
            "strict_producer_commit_replay_required": True,
            "exact_source_accounting_required": True,
            "required_collections": [
                "page_inventory",
                "contexts",
                "rows",
                "dimensions",
                "observations",
                "source_evidence",
                "source_references",
                "source_dispositions",
            ],
        },
        "accepted native TM observations",
    )
    schema = payload["schema_authority"]
    if not isinstance(schema, dict) or set(schema) != {
        "schema_name",
        "revision",
        "statement_type",
        "item_count",
        "order_authority",
        "schema_registry",
        "schema_graph",
        "tm_projection_sha256",
        "tm_context_policy",
        "tm_context_projection_sha256",
        "coverage_registry",
    }:
        raise NativeTMCanonicalMappingError("native TM schema authority fields drifted")
    _require_exact(
        {
            key: schema[key]
            for key in (
                "schema_name",
                "revision",
                "statement_type",
                "item_count",
                "order_authority",
            )
        },
        {
            "schema_name": "UNIVERSAL_BANK_BCTC_SCHEMA",
            "revision": "UNIVERSAL_BANK_BCTC_SCHEMA@6068",
            "statement_type": _STATEMENT_TYPE,
            "item_count": 1713,
            "order_authority": "WORKBOOK_DISPLAY_ORDER",
        },
        "native TM schema denominator",
    )
    _validate_identity(
        schema["schema_registry"],
        {
            "path": "data/registered/schema_registry.json",
            "sha256": "e415a0e399e81441611233a822e27c78194cb36707457d1adf8db5d003b3ce40",
        },
        "schema registry",
    )
    _validate_identity(
        schema["schema_graph"],
        {
            "path": "reference/schemas/schema_graph.jsonl",
            "sha256": "c36e79dc2d802f4ab598a0d151277facbb36d04785c31c37bb44c8345075c00d",
        },
        "schema graph",
    )
    _validate_identity(
        schema["tm_context_policy"],
        {
            "path": "config/schemas/tm-context-v1.yaml",
            "sha256": "50b0e7fcd5fbb54b45f6643d1d9c577de6013fdd04b748c620c755c54ee55e0a",
        },
        "TM context policy",
    )
    _validate_identity(
        schema["coverage_registry"],
        {
            "path": "data/registered/schema_coverage_registry.json",
            "sha256": "84c5f22425f109b0c53d5bc0c2a0473d6823ff44dea5fc59febeda85553166f9",
        },
        "schema coverage registry",
    )
    _require_exact(
        {
            "tm_projection_sha256": schema["tm_projection_sha256"],
            "tm_context_projection_sha256": schema["tm_context_projection_sha256"],
        },
        {
            "tm_projection_sha256": "c42b05b78208633e91b251c41a07757255d0b34f8ea5639c484ac6a07cd7f1fb",
            "tm_context_projection_sha256": "834d6d69883bb2d6d25af7a83052535a545066a35b8e45462d1a1f96ce997e86",
        },
        "native TM schema projections",
    )
    aliases = payload["typed_alias_authority"]
    if not isinstance(aliases, dict) or set(aliases) != {
        "accepted_authority_types",
        "untyped_structural_aliases_mapping_eligible",
        "historical_aliases_allowed",
        "fuzzy_matching_allowed",
        "strip_structural_enumerators",
        "accounting_abbreviation_expansion_allowed",
        "schema_source_config",
        "hierarchy_config",
        "hierarchy_registry",
        "tm_hierarchy_workbook",
        "business_update_audits",
        "tm_projection_record_count",
        "tm_projection_sha256",
    }:
        raise NativeTMCanonicalMappingError("typed TM alias authority fields drifted")
    _require_exact(
        {
            key: aliases[key]
            for key in (
                "accepted_authority_types",
                "untyped_structural_aliases_mapping_eligible",
                "historical_aliases_allowed",
                "fuzzy_matching_allowed",
                "strip_structural_enumerators",
                "accounting_abbreviation_expansion_allowed",
                "tm_projection_record_count",
                "tm_projection_sha256",
            )
        },
        {
            "accepted_authority_types": list(_ACCEPTED_ALIAS_TYPES),
            "untyped_structural_aliases_mapping_eligible": False,
            "historical_aliases_allowed": False,
            "fuzzy_matching_allowed": False,
            "strip_structural_enumerators": False,
            "accounting_abbreviation_expansion_allowed": False,
            "tm_projection_record_count": 2,
            "tm_projection_sha256": "cea637baa097229d871656954f88902d4357915c44c9033f67372e70b9991ea1",
        },
        "typed TM alias behavior",
    )
    for key, expected in {
        "schema_source_config": (
            "config/schemas/sources.yaml",
            "19ae91ee8591d451077175b6ae29d310115314efe90f1b371f5e004991d5875a",
        ),
        "hierarchy_config": (
            "config/schemas/hierarchy_reference.yaml",
            "a537328481fe533f74035442b2be11815d4623bcfc3a35044b25d58468164c93",
        ),
        "hierarchy_registry": (
            "data/registered/hierarchy_registry.json",
            "f236f2ea971ffdd22a11dcfe993d1d944fbcf6a8c2fc4d4a60583eeb012b6fd8",
        ),
        "tm_hierarchy_workbook": (
            "vst_level/vst_bank_detailed_notes_sheet.xlsx",
            "6f322f7ba3b1b737643d21890b9bd51ea00224cea6ac65cfa41036d68ccd885b",
        ),
    }.items():
        _validate_identity(aliases[key], {"path": expected[0], "sha256": expected[1]}, key)
    _require_exact(
        aliases["business_update_audits"],
        [
            {
                "path": "data/registered/schema_business_update_5712_5713_5714_5718_6068.json",
                "sha256": "1163665d9c4e14a31cb83fd26549eae1e51c5fdf38ccbbd95cb3bbe42eba128a",
            }
        ],
        "typed alias business-update audits",
    )
    _require_exact(
        payload["routing"],
        {
            "statement_type": _STATEMENT_TYPE,
            "normalization": "RETRIEVAL_KEY_EXACT",
            "candidate_authorities": [
                "CANONICAL_RETRIEVAL_KEY_EXACT",
                "ACCEPTED_TYPED_ALIAS_RETRIEVAL_KEY_EXACT",
            ],
            "global_candidate_uniqueness_required": True,
            "minimum_distinct_direct_child_anchors": 3,
            "require_distinct_target_per_anchor": True,
            "require_unanimous_direct_parent": True,
            "require_parent_equals_note_family_root": True,
            "require_resolved_mapping_eligible_targets": True,
            "require_resolved_mapping_eligible_parent": True,
            "require_depth_one_family_subtree": True,
            "source_object_owned_by_at_most_one_root": True,
            "root_occurrence_policy": "UNIQUE_SOURCE_CONTEXT_PER_INFERRED_ROOT",
            "distinct_roots_evaluated_independently": True,
            "zero_accepted_roots_allowed": True,
            "table_title_used_for_routing": False,
            "equation_used_for_target_selection": False,
        },
        "native TM routing",
    )
    _require_exact(
        payload["local_completion"],
        {
            "require_quantitative_context": True,
            "require_every_context_row_accounted": True,
            "require_region_grid_rows_only": True,
            "require_exactly_one_unlabeled_terminal_row": True,
            "require_terminal_after_all_anchors": True,
            "require_resolved_compatible_dimensions": True,
            "require_exactly_one_observation_per_row_dimension": True,
            "accepted_observation_statuses": ["OBSERVED_VALUE", "OBSERVED_ZERO"],
            "unresolved_or_invalid_positions_block": True,
            "row_local_scalars_block": True,
            "attached_unassigned_or_detached_evidence_blocks": True,
            "cell_free_after_terminal_inter_table_context_blocks": False,
            "following_heading_used_for_routing": False,
            "full_document_completion_implied": False,
            "equation_tolerance_source_units": 0,
        },
        "native TM local completion",
    )
    _require_exact(
        payload["coverage"],
        {
            "statement_type": _STATEMENT_TYPE,
            "schema_item_count": 1713,
            "completion_rule": "EXACTLY_ONE_TERMINAL_OUTCOME_PER_SCHEMA_ID_PER_DOCUMENT",
            "terminal_outcomes": list(_TERMINAL_OUTCOMES),
            "outside_bounded_subtree_outcome": "UNRESOLVED",
            "outside_bounded_subtree_reason": "UNASSESSED_OUTSIDE_BOUNDED_TABLE_SUBTREE",
            "absent_direct_child_outcome": "NOT_OBSERVED",
            "absent_direct_child_reason": "ABSENT_FROM_LOCALLY_COMPLETE_BOUNDED_TABLE_SUBTREE",
        },
        "native TM coverage",
    )
    _require_exact(
        payload["role_isolation"],
        {
            "direct_runtime_input_kinds": [
                "NATIVE_TM_OBSERVATIONS_ARTIFACT",
                "THIS_POLICY",
                "UNIVERSAL_SCHEMA_REGISTRY",
                "UNIVERSAL_SCHEMA_GRAPH",
                "TM_CONTEXT_POLICY",
                "SCHEMA_COVERAGE_REGISTRY",
                "SCHEMA_SOURCE_CONFIG",
                "HIERARCHY_CONFIG",
                "HIERARCHY_REGISTRY",
                "TM_HIERARCHY_WORKBOOK",
                "SCHEMA_BUSINESS_UPDATE_AUDIT",
            ],
            "prior_answer_artifacts_allowed": False,
            "historical_values_allowed": False,
            "role_a_outputs_allowed": False,
            "human_review_outputs_allowed": False,
            "bank_identity_used_for_routing": False,
            "filename_identity_used_for_routing": False,
            "page_number_used_for_routing": False,
            "note_number_used_for_routing": False,
            "table_title_used_for_routing": False,
            "expected_source_counts_used_for_routing": False,
            "forbidden_path_fragments": list(_FORBIDDEN_PATH_FRAGMENTS),
        },
        "native TM role isolation",
    )
    _require_exact(
        payload["output"],
        {
            "format": _OUTPUT_FORMAT,
            "status": _OUTPUT_STATUS,
            "canonical_json": True,
            "output_directory": _OUTPUT_DIRECTORY,
            "exclusive_no_overwrite": True,
            "rollback_after_failed_strict_replay": True,
            "absolute_project_paths_allowed": False,
            "exact_source_object_dispositions_required": True,
            "exact_tm_schema_dispositions_required": True,
            "strict_producer_commit_replay_required": True,
        },
        "native TM canonical output",
    )
    return copy.deepcopy(payload)


def load_native_tm_canonical_mapping_policy(path: Path, project_root: Path) -> dict[str, Any]:
    """Load the sole V1 policy through a no-follow project-relative guard."""

    project_root = project_root.resolve()
    path, relative = _lexical_project_path(project_root, path, "native TM canonical policy")
    if relative != POLICY_RELATIVE_PATH.as_posix():
        raise NativeTMCanonicalMappingError(
            f"native TM canonical mapping requires {POLICY_RELATIVE_PATH.as_posix()}"
        )
    guard = _open_guard(project_root, path, relative, "native TM canonical policy")
    try:
        try:
            payload = yaml.safe_load(guard.payload.decode("utf-8"))
        except (UnicodeDecodeError, yaml.YAMLError) as exc:
            raise NativeTMCanonicalMappingError("cannot decode native TM canonical policy") from exc
        policy = _validate_policy_payload(payload)
        _validate_path_isolation([POLICY_RELATIVE_PATH.as_posix(), *_IMPLEMENTATION_PATHS])
        return policy
    finally:
        _close_guard(guard)


def _git(project_root: Path, *arguments: str, binary: bool = False) -> str | bytes:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=not binary,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise NativeTMCanonicalMappingError("cannot inspect native TM canonical git state") from exc
    return result.stdout


def _current_git_state(project_root: Path) -> dict[str, Any]:
    commit = str(_git(project_root, "rev-parse", "HEAD")).strip()
    dirty = bool(str(_git(project_root, "status", "--porcelain", "--untracked-files=all")).strip())
    if _GIT_COMMIT.fullmatch(commit) is None or dirty:
        raise NativeTMCanonicalMappingError("native TM canonical producer requires a clean HEAD")
    return {"commit": commit, "dirty": False}


def _git_file_bytes(project_root: Path, commit: str, relative: str) -> bytes:
    if _GIT_COMMIT.fullmatch(commit) is None:
        raise NativeTMCanonicalMappingError("producer git commit is invalid")
    relative = _canonical_relative_path(relative, "producer file path")
    result = _git(project_root, "show", f"{commit}:{relative}", binary=True)
    if not isinstance(result, bytes):
        raise NativeTMCanonicalMappingError("producer git file read was not binary")
    return result


def _file_identity_at_commit(
    project_root: Path, commit: str, relative: str, kind: str | None = None
) -> dict[str, Any]:
    payload = _git_file_bytes(project_root, commit, relative)
    record = {"path": relative, "sha256": sha256_bytes(payload), "size_bytes": len(payload)}
    return {"kind": kind, **record} if kind is not None else record


def _implementation_ledger(project_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for relative in _IMPLEMENTATION_PATHS:
        path, _ = _lexical_project_path(project_root, Path(relative), "implementation path")
        guard = _open_guard(project_root, path, relative, "implementation file")
        try:
            records.append(
                {
                    "path": relative,
                    "sha256": sha256_bytes(guard.payload),
                    "size_bytes": len(guard.payload),
                }
            )
        finally:
            _close_guard(guard)
    return records


def _implementation_ledger_at_commit(project_root: Path, commit: str) -> list[dict[str, Any]]:
    return [
        _file_identity_at_commit(project_root, commit, relative)
        for relative in _IMPLEMENTATION_PATHS
    ]


def _json_bytes(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NativeTMCanonicalMappingError(f"cannot decode {label}") from exc
    if not isinstance(value, dict):
        raise NativeTMCanonicalMappingError(f"{label} must be an object")
    return value


def _yaml_bytes(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = yaml.safe_load(payload.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise NativeTMCanonicalMappingError(f"cannot decode {label}") from exc
    if not isinstance(value, dict):
        raise NativeTMCanonicalMappingError(f"{label} must be an object")
    return value


def _jsonl_bytes(payload: bytes, label: str) -> list[dict[str, Any]]:
    try:
        lines = payload.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise NativeTMCanonicalMappingError(f"cannot decode {label}") from exc
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise NativeTMCanonicalMappingError(f"{label} line {line_number} is invalid") from exc
        if not isinstance(record, dict):
            raise NativeTMCanonicalMappingError(f"{label} line {line_number} is not an object")
        records.append(record)
    return records


def _authority_specs(policy: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    schema = policy["schema_authority"]
    aliases = policy["typed_alias_authority"]
    specs = [
        (
            "UNIVERSAL_SCHEMA_REGISTRY",
            schema["schema_registry"]["path"],
            schema["schema_registry"]["sha256"],
        ),
        (
            "UNIVERSAL_SCHEMA_GRAPH",
            schema["schema_graph"]["path"],
            schema["schema_graph"]["sha256"],
        ),
        (
            "TM_CONTEXT_POLICY",
            schema["tm_context_policy"]["path"],
            schema["tm_context_policy"]["sha256"],
        ),
        (
            "SCHEMA_COVERAGE_REGISTRY",
            schema["coverage_registry"]["path"],
            schema["coverage_registry"]["sha256"],
        ),
        (
            "SCHEMA_SOURCE_CONFIG",
            aliases["schema_source_config"]["path"],
            aliases["schema_source_config"]["sha256"],
        ),
        (
            "HIERARCHY_CONFIG",
            aliases["hierarchy_config"]["path"],
            aliases["hierarchy_config"]["sha256"],
        ),
        (
            "HIERARCHY_REGISTRY",
            aliases["hierarchy_registry"]["path"],
            aliases["hierarchy_registry"]["sha256"],
        ),
        (
            "TM_HIERARCHY_WORKBOOK",
            aliases["tm_hierarchy_workbook"]["path"],
            aliases["tm_hierarchy_workbook"]["sha256"],
        ),
    ]
    specs.extend(
        ("SCHEMA_BUSINESS_UPDATE_AUDIT", audit["path"], audit["sha256"])
        for audit in aliases["business_update_audits"]
    )
    return specs


def _open_runtime_authorities(
    project_root: Path, policy: Mapping[str, Any]
) -> tuple[list[Any], dict[str, bytes], list[dict[str, Any]]]:
    guards: list[Any] = []
    contents: dict[str, bytes] = {}
    ledger: list[dict[str, Any]] = []
    try:
        for kind, relative, expected_sha256 in _authority_specs(policy):
            relative = _canonical_relative_path(relative, f"{kind} path")
            path, _ = _lexical_project_path(project_root, Path(relative), f"{kind} path")
            guard = _open_guard(project_root, path, relative, kind)
            guards.append(guard)
            identity = _identity_from_guard(guard, kind)
            if identity["sha256"] != expected_sha256:
                raise NativeTMCanonicalMappingError(f"{kind} hash drifted")
            if relative in contents:
                raise NativeTMCanonicalMappingError("runtime authority path is repeated")
            contents[relative] = bytes(guard.payload)
            ledger.append(identity)
    except BaseException:
        for guard in reversed(guards):
            _close_guard(guard)
        raise
    ledger.sort(key=lambda record: (record["kind"], record["path"]))
    return guards, contents, ledger


def _validate_schema_registry(payload: Mapping[str, Any], policy: Mapping[str, Any]) -> None:
    schema = policy["schema_authority"]
    universal = payload.get("universal_schema")
    if (
        payload.get("schema_name") != schema["schema_name"]
        or payload.get("graph") != schema["schema_graph"]["path"]
        or payload.get("graph_sha256") != schema["schema_graph"]["sha256"]
        or payload.get("counts", {}).get(_STATEMENT_TYPE) != schema["item_count"]
        or not isinstance(universal, dict)
        or universal.get("revision") != schema["revision"]
        or universal.get("counts", {}).get(_STATEMENT_TYPE) != schema["item_count"]
        or universal.get("schema_graph_sha256") != schema["schema_graph"]["sha256"]
    ):
        raise NativeTMCanonicalMappingError("registered universal schema identity drifted")


def _load_tm_schema(
    graph_bytes: bytes,
    registry_bytes: bytes,
    coverage_bytes: bytes,
    policy: Mapping[str, Any],
) -> list[dict[str, Any]]:
    registry = _json_bytes(registry_bytes, "universal schema registry")
    _validate_schema_registry(registry, policy)
    records = _jsonl_bytes(graph_bytes, "universal schema graph")
    identifiers = [record.get("schema_id") for record in records]
    if any(
        isinstance(identifier, bool) or not isinstance(identifier, int)
        for identifier in identifiers
    ) or len(identifiers) != len(set(identifiers)):
        raise NativeTMCanonicalMappingError("universal schema graph IDs are invalid")
    tm_schema = [
        copy.deepcopy(record)
        for record in records
        if record.get("statement_type") == _STATEMENT_TYPE
    ]
    tm_schema.sort(key=lambda record: record.get("display_order", -1))
    expected_count = policy["schema_authority"]["item_count"]
    if (
        len(tm_schema) != expected_count
        or [record.get("display_order") for record in tm_schema] != list(range(expected_count))
        or any(not isinstance(record.get("canonical_name"), str) for record in tm_schema)
    ):
        raise NativeTMCanonicalMappingError("TM schema denominator or display order drifted")
    by_id = {record["schema_id"]: record for record in tm_schema}
    for record in tm_schema:
        parent_id = record.get("parent_id")
        children = record.get("children")
        if parent_id is not None and parent_id not in by_id:
            raise NativeTMCanonicalMappingError("TM schema contains a foreign parent")
        if not isinstance(children, list) or any(child not in by_id for child in children):
            raise NativeTMCanonicalMappingError("TM schema contains a foreign child")
        expected_children = [
            child["schema_id"]
            for child in tm_schema
            if child.get("parent_id") == record["schema_id"]
        ]
        if children != expected_children:
            raise NativeTMCanonicalMappingError("TM schema parent/child projection drifted")
    coverage = _json_bytes(coverage_bytes, "schema coverage registry")
    tm_coverage = coverage.get("by_statement", {}).get(_STATEMENT_TYPE)
    mandatory = coverage.get("mandatory_search")
    if (
        coverage.get("status") != "PASS_ALL_TEMPLATE_ITEMS_ENROLLED"
        or coverage.get("order_authority") != "WORKBOOK_DISPLAY_ORDER"
        or not isinstance(tm_coverage, dict)
        or tm_coverage.get("target_count") != expected_count
        or not isinstance(mandatory, dict)
        or mandatory.get("completion_rule")
        != "EXACTLY_ONE_TERMINAL_OUTCOME_PER_SCHEMA_ID_PER_DOCUMENT"
        or not set(_TERMINAL_OUTCOMES) <= set(mandatory.get("terminal_outcomes", []))
    ):
        raise NativeTMCanonicalMappingError("registered TM coverage contract drifted")
    return tm_schema


def _derive_tm_context(
    schema: Sequence[Mapping[str, Any]],
    context_policy_bytes: bytes,
    policy: Mapping[str, Any],
) -> list[dict[str, Any]]:
    raw = _yaml_bytes(context_policy_bytes, "TM context policy")
    if set(raw) != {
        "version",
        "policy",
        "statement_type",
        "order_authority",
        "section_roots",
        "resolved_context",
        "level_mismatch_items",
        "orphan_items",
    }:
        raise NativeTMCanonicalMappingError("TM context policy fields drifted")
    if (
        raw.get("version") != 1
        or raw.get("policy") != "UNIVERSAL_BANK_BCTC_TM_SCHEMA_CONTEXT_V1"
        or raw.get("statement_type") != _STATEMENT_TYPE
        or raw.get("order_authority") != "WORKBOOK_DISPLAY_ORDER"
    ):
        raise NativeTMCanonicalMappingError("TM context policy identity drifted")
    resolved = raw.get("resolved_context")
    if resolved != {"status": "RESOLVED", "mapping_eligible": True}:
        raise NativeTMCanonicalMappingError("TM resolved context policy was weakened")
    roots = raw.get("section_roots")
    mismatches = raw.get("level_mismatch_items")
    orphans = raw.get("orphan_items")
    if (
        not isinstance(roots, list)
        or not isinstance(mismatches, list)
        or not isinstance(orphans, list)
    ):
        raise NativeTMCanonicalMappingError("TM context policy lists are invalid")
    root_by_id = {entry.get("report_norm_id"): entry for entry in roots if isinstance(entry, dict)}
    mismatch_by_id = {
        entry.get("report_norm_id"): entry for entry in mismatches if isinstance(entry, dict)
    }
    orphan_by_id = {
        entry.get("report_norm_id"): entry for entry in orphans if isinstance(entry, dict)
    }
    if (
        len(root_by_id) != len(roots)
        or len(mismatch_by_id) != len(mismatches)
        or len(orphan_by_id) != len(orphans)
    ):
        raise NativeTMCanonicalMappingError("TM context policy repeats a ReportNormId")
    by_id = {int(record["schema_id"]): record for record in schema}
    path_cache: dict[int, tuple[int, ...]] = {}

    def ancestor_path(identifier: int) -> tuple[int, ...]:
        cached = path_cache.get(identifier)
        if cached is not None:
            return cached
        path: list[int] = []
        seen: set[int] = set()
        current = by_id[identifier]
        while True:
            current_id = int(current["schema_id"])
            if current_id in seen:
                raise NativeTMCanonicalMappingError("TM context hierarchy contains a cycle")
            seen.add(current_id)
            path.append(current_id)
            parent_id = current.get("parent_id")
            if parent_id is None:
                break
            current = by_id[int(parent_id)]
        result = tuple(reversed(path))
        path_cache[identifier] = result
        return result

    contexts: list[dict[str, Any]] = []
    for item in schema:
        identifier = int(item["schema_id"])
        path = ancestor_path(identifier)
        if identifier in orphan_by_id:
            orphan = orphan_by_id[identifier]
            if (
                item.get("canonical_name") != orphan.get("canonical_name")
                or item.get("parent_id") != orphan.get("expected_parent_report_norm_id")
                or item.get("hierarchy_level") != orphan.get("expected_hierarchy_level")
                or orphan.get("mapping_eligible") is not False
            ):
                raise NativeTMCanonicalMappingError("TM orphan context identity drifted")
            context_status = orphan.get("status")
            mapping_eligible = False
            section = None
            section_root_id = None
            note_family_root_id = None
            derived_level = None
        else:
            root = root_by_id.get(path[0])
            if root is None or item.get("canonical_name") is None:
                raise NativeTMCanonicalMappingError("TM item has no accounting-section context")
            section = root.get("section")
            section_root_id = path[0]
            note_family_root_id = path[1] if len(path) > 1 else None
            derived_level = len(path) - 1
            mismatch = mismatch_by_id.get(identifier)
            if mismatch is None:
                if item.get("hierarchy_level") != derived_level:
                    raise NativeTMCanonicalMappingError("TM hierarchy level drifted")
                context_status = "RESOLVED"
                mapping_eligible = True
            else:
                if (
                    item.get("canonical_name") != mismatch.get("canonical_name")
                    or item.get("parent_id") != mismatch.get("expected_parent_report_norm_id")
                    or item.get("hierarchy_level")
                    != mismatch.get("expected_declared_hierarchy_level")
                    or derived_level != mismatch.get("expected_derived_hierarchy_level")
                    or mismatch.get("mapping_eligible") is not False
                ):
                    raise NativeTMCanonicalMappingError("TM level-mismatch context drifted")
                context_status = mismatch.get("status")
                mapping_eligible = False
        contexts.append(
            {
                "report_norm_id": identifier,
                "canonical_name": item["canonical_name"],
                "statement_type": _STATEMENT_TYPE,
                "section": section,
                "section_root_id": section_root_id,
                "note_family_root_id": note_family_root_id,
                "ancestor_path": list(path),
                "parent_report_norm_id": item.get("parent_id"),
                "hierarchy_level": item.get("hierarchy_level"),
                "derived_hierarchy_level": derived_level,
                "display_order": item["display_order"],
                "context_status": context_status,
                "mapping_eligible": mapping_eligible,
            }
        )
    projection_sha256 = _stable_records_sha256(contexts)
    if projection_sha256 != policy["schema_authority"]["tm_context_projection_sha256"]:
        raise NativeTMCanonicalMappingError("TM context projection hash drifted")
    return contexts


def _xlsx_column(reference: str) -> str:
    match = re.match(r"([A-Z]+)", reference.upper())
    if match is None:
        raise NativeTMCanonicalMappingError("TM hierarchy workbook cell reference is invalid")
    return match.group(1)


def _xlsx_rows(payload: bytes) -> list[dict[str, str]]:
    try:
        with ZipFile(io.BytesIO(payload)) as archive:
            shared: list[str] = []
            if "xl/sharedStrings.xml" in archive.namelist():
                shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
                shared = [
                    "".join(node.text or "" for node in item.iter(f"{{{_MAIN_NS}}}t"))
                    for item in shared_root.findall("m:si", _XLSX_NS)
                ]
            workbook = ET.fromstring(archive.read("xl/workbook.xml"))
            relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            targets = {item.attrib["Id"]: item.attrib["Target"] for item in relationships}
            sheets = workbook.find("m:sheets", _XLSX_NS)
            if sheets is None or not list(sheets):
                raise NativeTMCanonicalMappingError("TM hierarchy workbook has no sheet")
            first_sheet = list(sheets)[0]
            relation_id = first_sheet.attrib[f"{{{_REL_NS}}}id"]
            target = targets[relation_id].lstrip("/")
            if not target.startswith("xl/"):
                target = posixpath.normpath(posixpath.join("xl", target))
            root = ET.fromstring(archive.read(target))
            rows: list[dict[str, str]] = []
            for row in root.findall(".//m:sheetData/m:row", _XLSX_NS):
                values: dict[str, str] = {}
                for cell in row.findall("m:c", _XLSX_NS):
                    reference = cell.attrib.get("r", "")
                    cell_type = cell.attrib.get("t")
                    value_node = cell.find("m:v", _XLSX_NS)
                    if cell_type == "inlineStr":
                        inline = cell.find("m:is", _XLSX_NS)
                        value = (
                            ""
                            if inline is None
                            else "".join(
                                node.text or "" for node in inline.iter(f"{{{_MAIN_NS}}}t")
                            )
                        )
                    elif value_node is None:
                        value = ""
                    elif cell_type == "s":
                        value = shared[int(value_node.text or "")]
                    else:
                        value = value_node.text or ""
                    values[_xlsx_column(reference)] = value
                if values:
                    rows.append(values)
            return rows
    except NativeTMCanonicalMappingError:
        raise
    except (BadZipFile, KeyError, IndexError, ValueError, ET.ParseError) as exc:
        raise NativeTMCanonicalMappingError("cannot decode TM hierarchy workbook") from exc


def _integer_text(value: str, label: str) -> int:
    try:
        numeric = Decimal(value.strip())
    except InvalidOperation as exc:
        raise NativeTMCanonicalMappingError(f"{label} is not numeric") from exc
    if numeric != numeric.to_integral_value():
        raise NativeTMCanonicalMappingError(f"{label} is not an integer")
    return int(numeric)


def _load_typed_aliases(
    schema: Sequence[Mapping[str, Any]],
    authority_bytes: Mapping[str, bytes],
    policy: Mapping[str, Any],
) -> list[dict[str, Any]]:
    aliases_policy = policy["typed_alias_authority"]
    source_config = _yaml_bytes(
        authority_bytes[aliases_policy["schema_source_config"]["path"]],
        "schema source config",
    )
    configured_audits = [record["path"] for record in aliases_policy["business_update_audits"]]
    if source_config.get("approved_business_update_audits") != configured_audits:
        raise NativeTMCanonicalMappingError("approved business-update alias audits drifted")
    hierarchy_config = _yaml_bytes(
        authority_bytes[aliases_policy["hierarchy_config"]["path"]],
        "hierarchy config",
    )
    sources = hierarchy_config.get("sources")
    tm_source = sources.get(_STATEMENT_TYPE) if isinstance(sources, dict) else None
    if (
        hierarchy_config.get("version") != 1
        or hierarchy_config.get("authority") != "USER_SUPPLIED_VST_LEVEL"
        or hierarchy_config.get("root") != "vst_level"
        or not isinstance(tm_source, dict)
        or tm_source.get("coverage") != "FULL_STATEMENT"
    ):
        raise NativeTMCanonicalMappingError("TM hierarchy configuration drifted")
    workbook_relative = aliases_policy["tm_hierarchy_workbook"]["path"]
    if f"{hierarchy_config['root']}/{tm_source.get('path')}" != workbook_relative:
        raise NativeTMCanonicalMappingError("TM hierarchy workbook path drifted")
    columns = tm_source.get("columns")
    if not isinstance(columns, dict) or set(columns) != {
        "label",
        "schema_id",
        "level",
        "parent_id",
    }:
        raise NativeTMCanonicalMappingError("TM hierarchy columns drifted")
    workbook_bytes = authority_bytes[workbook_relative]
    hierarchy_registry = _json_bytes(
        authority_bytes[aliases_policy["hierarchy_registry"]["path"]],
        "hierarchy registry",
    )
    tm_workbooks = [
        record
        for record in hierarchy_registry.get("workbooks", [])
        if isinstance(record, dict) and record.get("statement_type") == _STATEMENT_TYPE
    ]
    if (
        hierarchy_registry.get("authority") != "USER_SUPPLIED_VST_LEVEL"
        or hierarchy_registry.get("status")
        != "VALIDATED_SUPPORTING_REFERENCE_WITH_SCHEMA_ONLY_APPENDS"
        or len(tm_workbooks) != 1
        or tm_workbooks[0].get("path") != workbook_relative
        or tm_workbooks[0].get("sha256") != sha256_bytes(workbook_bytes)
        or tm_workbooks[0].get("schema_only_append_ids") != tm_source.get("schema_only_append_ids")
    ):
        raise NativeTMCanonicalMappingError("registered TM hierarchy authority drifted")
    rows = _xlsx_rows(workbook_bytes)
    if not rows:
        raise NativeTMCanonicalMappingError("TM hierarchy workbook is empty")
    header_to_letter = {
        normalize_text(value): letter for letter, value in rows[0].items() if normalize_text(value)
    }
    missing = [name for name in columns.values() if name not in header_to_letter]
    if missing:
        raise NativeTMCanonicalMappingError("TM hierarchy workbook columns are missing")
    by_id = {int(record["schema_id"]): record for record in schema}
    hierarchy_ids: set[int] = set()
    raw_aliases: list[dict[str, Any]] = []
    for row_number, raw_row in enumerate(rows[1:], start=2):
        values = {
            logical: normalize_text(raw_row.get(header_to_letter[column], ""))
            for logical, column in columns.items()
        }
        if not any(values.values()):
            continue
        identifier = _integer_text(values["schema_id"], "TM hierarchy schema ID")
        if identifier in hierarchy_ids or identifier not in by_id:
            raise NativeTMCanonicalMappingError("TM hierarchy identity is duplicated or foreign")
        hierarchy_ids.add(identifier)
        item = by_id[identifier]
        label = values["label"]
        if not label:
            raise NativeTMCanonicalMappingError("TM hierarchy label is blank")
        if retrieval_key(label) == retrieval_key(str(item["canonical_name"])):
            continue
        if normalize_text(label) not in {
            normalize_text(str(alias)) for alias in item.get("structural_aliases", [])
        }:
            raise NativeTMCanonicalMappingError(
                "typed hierarchy alias is absent from the applied TM schema"
            )
        evidence = {
            "hierarchy_authority": hierarchy_registry["authority"],
            "hierarchy_status": hierarchy_registry["status"],
            "source_path": workbook_relative,
            "source_workbook_sha256": sha256_bytes(workbook_bytes),
            "source_row": row_number,
        }
        raw_aliases.append(
            {
                "statement_type": _STATEMENT_TYPE,
                "report_norm_id": identifier,
                "alias": label,
                "authority_type": "USER_SUPPLIED_HIERARCHY_LABEL",
                "authority_evidence_sha256": _record_sha256(evidence),
            }
        )
    schema_only_ids = set(tm_source.get("schema_only_append_ids", []))
    if hierarchy_ids != set(by_id) - schema_only_ids:
        raise NativeTMCanonicalMappingError("TM hierarchy workbook coverage drifted")
    if tm_workbooks[0].get("item_count") != len(hierarchy_ids):
        raise NativeTMCanonicalMappingError("TM hierarchy workbook denominator drifted")

    for audit_relative in configured_audits:
        audit = _json_bytes(authority_bytes[audit_relative], "schema business-update audit")
        if audit.get("status") != "APPLIED_AND_VERIFIED":
            raise NativeTMCanonicalMappingError(
                "schema business-update alias audit is not accepted"
            )
        changes = audit.get("structural_alias_changes")
        if not isinstance(changes, list):
            raise NativeTMCanonicalMappingError("schema business-update alias audit is untyped")
        audit_sha256 = sha256_bytes(authority_bytes[audit_relative])
        for change_index, change in enumerate(changes):
            if (
                not isinstance(change, dict)
                or type(change.get("added_to_structural_aliases")) is not bool
            ):
                raise NativeTMCanonicalMappingError("schema alias audit decision is untyped")
            if (
                not change["added_to_structural_aliases"]
                or change.get("statement_type") != _STATEMENT_TYPE
            ):
                continue
            identifier = change.get("schema_id")
            alias = normalize_text(str(change.get("alias", "")))
            item = by_id.get(identifier)
            if (
                item is None
                or not alias
                or alias
                not in {normalize_text(str(value)) for value in item.get("structural_aliases", [])}
            ):
                raise NativeTMCanonicalMappingError(
                    "audited TM alias is absent from applied schema"
                )
            evidence = {
                "audit_path": audit_relative,
                "audit_sha256": audit_sha256,
                "audit_status": audit["status"],
                "change_index": change_index,
                "disposition": change.get("disposition"),
                "provenance": change.get("provenance"),
                "source_evidence": change.get("evidence"),
            }
            raw_aliases.append(
                {
                    "statement_type": _STATEMENT_TYPE,
                    "report_norm_id": identifier,
                    "alias": alias,
                    "authority_type": "AUDITED_SCHEMA_ALIAS",
                    "authority_evidence_sha256": _record_sha256(evidence),
                }
            )
    priority = {"AUDITED_SCHEMA_ALIAS": 0, "USER_SUPPLIED_HIERARCHY_LABEL": 1}
    selected: dict[tuple[int, str], dict[str, Any]] = {}
    for alias in raw_aliases:
        key = (int(alias["report_norm_id"]), retrieval_key(str(alias["alias"])))
        previous = selected.get(key)
        if (
            previous is None
            or priority[str(alias["authority_type"])] < priority[str(previous["authority_type"])]
        ):
            selected[key] = alias
    aliases = sorted(
        selected.values(),
        key=lambda alias: (
            by_id[int(alias["report_norm_id"])]["display_order"],
            retrieval_key(str(alias["alias"])),
        ),
    )
    alias_hash = stable_records_hash(
        json.dumps(record, ensure_ascii=False, sort_keys=True) for record in aliases
    )
    if (
        len(aliases) != aliases_policy["tm_projection_record_count"]
        or alias_hash != aliases_policy["tm_projection_sha256"]
        or any(alias["authority_type"] not in _ACCEPTED_ALIAS_TYPES for alias in aliases)
    ):
        raise NativeTMCanonicalMappingError("typed TM alias projection drifted")
    return aliases


def _load_authority_bundle(
    authority_bytes: Mapping[str, bytes], policy: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    schema_policy = policy["schema_authority"]
    schema = _load_tm_schema(
        authority_bytes[schema_policy["schema_graph"]["path"]],
        authority_bytes[schema_policy["schema_registry"]["path"]],
        authority_bytes[schema_policy["coverage_registry"]["path"]],
        policy,
    )
    contexts = _derive_tm_context(
        schema,
        authority_bytes[schema_policy["tm_context_policy"]["path"]],
        policy,
    )
    aliases = _load_typed_aliases(schema, authority_bytes, policy)
    identity = {
        "schema_name": schema_policy["schema_name"],
        "revision": schema_policy["revision"],
        "statement_type": _STATEMENT_TYPE,
        "item_count": len(schema),
        "order_authority": schema_policy["order_authority"],
        "schema_graph_sha256": schema_policy["schema_graph"]["sha256"],
        "tm_projection_sha256": schema_policy["tm_projection_sha256"],
        "tm_context_policy_sha256": schema_policy["tm_context_policy"]["sha256"],
        "tm_context_projection_sha256": _stable_records_sha256(contexts),
        "typed_alias_record_count": len(aliases),
        "typed_alias_projection_sha256": stable_records_hash(
            json.dumps(record, ensure_ascii=False, sort_keys=True) for record in aliases
        ),
        "accepted_alias_authority_types": list(_ACCEPTED_ALIAS_TYPES),
    }
    return schema, contexts, aliases, identity


def _producer_snapshots(
    *,
    policy_relative: str,
    policy_bytes: bytes,
    policy: Mapping[str, Any],
    schema: Sequence[Mapping[str, Any]],
    contexts: Sequence[Mapping[str, Any]],
    aliases: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    policy_payload = copy.deepcopy(dict(policy))
    schema_payload = copy.deepcopy(list(schema))
    context_payload = copy.deepcopy(list(contexts))
    alias_payload = copy.deepcopy(list(aliases))
    return {
        "policy": {
            "path": policy_relative,
            "sha256": sha256_bytes(policy_bytes),
            "size_bytes": len(policy_bytes),
            "payload_sha256": _record_sha256(policy_payload),
            "payload": policy_payload,
        },
        "tm_schema": {
            "record_count": len(schema_payload),
            "payload_sha256": _record_sha256(schema_payload),
            "records": schema_payload,
        },
        "tm_context": {
            "record_count": len(context_payload),
            "payload_sha256": _record_sha256(context_payload),
            "projection_sha256": _stable_records_sha256(context_payload),
            "records": context_payload,
        },
        "accepted_typed_aliases": {
            "record_count": len(alias_payload),
            "payload_sha256": _record_sha256(alias_payload),
            "projection_sha256": stable_records_hash(
                json.dumps(record, ensure_ascii=False, sort_keys=True) for record in alias_payload
            ),
            "records": alias_payload,
        },
    }


def _as_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise NativeTMCanonicalMappingError(f"{label} must be an object")
    return value


def _as_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise NativeTMCanonicalMappingError(f"{label} must be a list")
    return value


def _as_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise NativeTMCanonicalMappingError(f"{label} must be a non-empty string")
    return value


def _validate_observation_envelope(payload: Mapping[str, Any], policy: Mapping[str, Any]) -> None:
    accepted = policy["accepted_native_tm_observations"]
    if (
        payload.get("format_version") != accepted["format_version"]
        or payload.get("policy") != accepted["policy"]
        or payload.get("claim_boundary") != accepted["claim_boundary"]
        or payload.get("status") != accepted["status"]
        or payload.get("source", {}).get("dataset_role") != accepted["required_dataset_role"]
    ):
        raise NativeTMCanonicalMappingError("native TM observations contract identity drifted")
    for collection in accepted["required_collections"]:
        value = payload.get(collection)
        if collection in {"source_evidence", "source_references"}:
            if not isinstance(value, dict):
                raise NativeTMCanonicalMappingError(
                    f"native TM observations {collection} must be an object"
                )
        elif not isinstance(value, list):
            raise NativeTMCanonicalMappingError(
                f"native TM observations {collection} must be a list"
            )
    accounting = payload.get("source_accounting")
    if (
        not isinstance(accounting, dict)
        or accounting.get("source_object_accounting_complete") is not True
    ):
        raise NativeTMCanonicalMappingError("native TM source accounting is incomplete")
    scope = payload.get("report_scope_binding")
    if (
        not isinstance(scope, dict)
        or scope.get("binding_status") != "RESOLVED_UNANIMOUS_SOURCE_VISIBLE_TM_HEADERS"
        or scope.get("scope") not in {"CONSOLIDATED", "SEPARATE"}
    ):
        raise NativeTMCanonicalMappingError("native TM report scope is unresolved")


def _source_indices(payload: Mapping[str, Any]) -> dict[str, Any]:
    dispositions = _as_list(payload.get("source_dispositions"), "source dispositions")
    disposition_by_id: dict[str, dict[str, Any]] = {}
    for raw in dispositions:
        record = _as_object(raw, "source disposition")
        if set(record) != {"source_object_id", "source_object_type", "source_disposition"}:
            raise NativeTMCanonicalMappingError("upstream source disposition fields drifted")
        identifier = _as_string(record["source_object_id"], "source object ID")
        _as_string(record["source_object_type"], "source object type")
        _as_string(record["source_disposition"], "source object disposition")
        if identifier in disposition_by_id:
            raise NativeTMCanonicalMappingError("upstream source disposition is duplicated")
        disposition_by_id[identifier] = record
    collection_specs = (
        ("page_inventory", "PAGE_CONTEXT", "page_id"),
        ("contexts", "CONTEXT", "context_id"),
        ("rows", "ROW", "row_id"),
        ("dimensions", "DIMENSION", "dimension_id"),
        ("observations", "OBSERVATION", "observation_id"),
    )
    indices: dict[str, dict[str, dict[str, Any]]] = {}
    primary_source_ids: set[str] = set()
    for collection, record_type, key in collection_specs:
        index: dict[str, dict[str, Any]] = {}
        for raw in _as_list(payload.get(collection), collection):
            record = _as_object(raw, f"{collection} record")
            identifier = _as_string(record.get(key), f"{collection} {key}")
            source_object_id = _as_string(
                record.get("source_object_id"), f"{collection} source object ID"
            )
            if (
                identifier in index
                or source_object_id in primary_source_ids
                or record.get("record_type") != record_type
                or disposition_by_id.get(source_object_id)
                != {
                    "source_object_id": source_object_id,
                    "source_object_type": record_type,
                    "source_disposition": record.get("source_disposition"),
                }
            ):
                raise NativeTMCanonicalMappingError(f"{collection} identity is not exact")
            index[identifier] = record
            primary_source_ids.add(source_object_id)
        indices[collection] = index

    evidence = _as_object(payload.get("source_evidence"), "source evidence")
    evidence_by_id: dict[str, dict[str, Any]] = {}

    def register_evidence(value: Any, label: str) -> None:
        if isinstance(value, list):
            for ordinal, item in enumerate(value):
                register_evidence(item, f"{label}[{ordinal}]")
            return
        if not isinstance(value, dict):
            return
        if "source_object_id" in value:
            source_object_id = _as_string(
                value.get("source_object_id"), f"{label} source object ID"
            )
            record_type = _as_string(value.get("record_type"), f"{label} record type")
            source_disposition = _as_string(
                value.get("source_disposition"), f"{label} source disposition"
            )
            if (
                source_object_id in primary_source_ids
                or source_object_id in evidence_by_id
                or disposition_by_id.get(source_object_id)
                != {
                    "source_object_id": source_object_id,
                    "source_object_type": record_type,
                    "source_disposition": source_disposition,
                }
            ):
                raise NativeTMCanonicalMappingError(
                    "native TM source evidence accounting is not exact"
                )
            evidence_by_id[source_object_id] = value
        for key, item in value.items():
            if key != "source_object_id":
                register_evidence(item, f"{label}.{key}")

    for category, raw_records in evidence.items():
        if not isinstance(category, str) or not category:
            raise NativeTMCanonicalMappingError("native TM source evidence category is invalid")
        records = _as_list(raw_records, f"{category} evidence")
        for ordinal, raw in enumerate(records):
            record = _as_object(raw, f"{category} evidence record")
            if "source_object_id" not in record:
                raise NativeTMCanonicalMappingError(
                    "native TM source evidence record has no source object identity"
                )
            register_evidence(record, f"{category} evidence record {ordinal}")

    accounted_source_ids = primary_source_ids | set(evidence_by_id)
    if set(disposition_by_id) != accounted_source_ids:
        raise NativeTMCanonicalMappingError("native TM source object partition drifted")

    references = _as_object(payload.get("source_references"), "source references")
    reference_ids: set[str] = set()
    reference_records: list[dict[str, Any]] = []
    for category, raw_records in references.items():
        if not isinstance(category, str) or not category:
            raise NativeTMCanonicalMappingError("native TM source reference category is invalid")
        for raw in _as_list(raw_records, f"{category} source references"):
            record = _as_object(raw, f"{category} source reference")
            reference_id = _as_string(record.get("reference_id"), f"{category} source reference ID")
            if (
                record.get("record_type") != "SOURCE_RUN_REFERENCE"
                or reference_id in reference_ids
                or reference_id in accounted_source_ids
                or reference_id in disposition_by_id
            ):
                raise NativeTMCanonicalMappingError(
                    "native TM source reference identity is not exact"
                )
            reference_ids.add(reference_id)
            reference_records.append(record)

    owner_fields = {
        "owner_source_object_id",
        "source_owner_id",
        "source_run_owner_id",
        "unit_run_owner_id",
        "value_run_owner_id",
    }

    def validate_owner_references(value: Any, label: str) -> None:
        if isinstance(value, list):
            for ordinal, item in enumerate(value):
                validate_owner_references(item, f"{label}[{ordinal}]")
            return
        if not isinstance(value, dict):
            return
        for field in owner_fields:
            if field not in value or value[field] is None:
                continue
            owner_id = _as_string(value[field], f"{label} {field}")
            owner = disposition_by_id.get(owner_id)
            if owner_id not in evidence_by_id or owner is None:
                raise NativeTMCanonicalMappingError("native TM source reference owner is not exact")
            disposition_field = (
                "owner_source_disposition"
                if field == "owner_source_object_id"
                else "source_owner_disposition"
            )
            if (
                disposition_field in value
                and value[disposition_field] != owner["source_disposition"]
            ):
                raise NativeTMCanonicalMappingError(
                    "native TM source reference disposition is not exact"
                )
        if "unit_run_owner_ids" in value:
            owner_ids = _as_list(value["unit_run_owner_ids"], f"{label} unit-run owner IDs")
            for owner_id in owner_ids:
                if not isinstance(owner_id, str) or not owner_id or owner_id not in evidence_by_id:
                    raise NativeTMCanonicalMappingError(
                        "native TM source reference owner is not exact"
                    )
        for key, item in value.items():
            if key not in owner_fields | {"unit_run_owner_ids"}:
                validate_owner_references(item, f"{label}.{key}")

    for collection, index in indices.items():
        for record in index.values():
            validate_owner_references(record, f"{collection} record")
    for record in evidence_by_id.values():
        validate_owner_references(record, "source evidence record")
    for record in reference_records:
        validate_owner_references(record, "source reference record")
        if not any(field in record and record[field] is not None for field in owner_fields):
            raise NativeTMCanonicalMappingError("native TM source reference has no canonical owner")

    contexts = indices["contexts"]
    rows = indices["rows"]
    dimensions = indices["dimensions"]
    observations = indices["observations"]
    for context_id, context in contexts.items():
        row_ids = _as_list(context.get("row_ids"), "context row IDs")
        dimension_ids = _as_list(context.get("dimension_ids"), "context dimension IDs")
        observation_ids = _as_list(context.get("observation_ids"), "context observation IDs")
        if (
            len(row_ids) != len(set(row_ids))
            or len(dimension_ids) != len(set(dimension_ids))
            or len(observation_ids) != len(set(observation_ids))
            or any(row_id not in rows for row_id in row_ids)
            or any(dimension_id not in dimensions for dimension_id in dimension_ids)
            or any(observation_id not in observations for observation_id in observation_ids)
            or any(rows[row_id].get("context_id") != context_id for row_id in row_ids)
            or any(dimensions[item].get("context_id") != context_id for item in dimension_ids)
            or any(observations[item].get("context_id") != context_id for item in observation_ids)
        ):
            raise NativeTMCanonicalMappingError("native TM context foreign keys drifted")
    for row_id, row in rows.items():
        observation_ids = _as_list(row.get("observation_ids"), "row observation IDs")
        context_id = row.get("context_id")
        context = contexts.get(context_id)
        if (
            (
                context is None
                and not (
                    context_id is None
                    and row.get("row_source_kind") == "INTER_TABLE_CONTEXT_ROW"
                    and observation_ids == []
                )
            )
            or (context is not None and row_id not in context["row_ids"])
            or (
                context is not None and row.get("source_table_id") != context.get("source_table_id")
            )
            or len(observation_ids) != len(set(observation_ids))
            or any(
                observation_id not in observations
                or observations[observation_id].get("row_id") != row_id
                for observation_id in observation_ids
            )
        ):
            raise NativeTMCanonicalMappingError("native TM row foreign keys drifted")
    for dimension_id, dimension in dimensions.items():
        context = contexts.get(dimension.get("context_id"))
        if (
            context is None
            or dimension_id not in context["dimension_ids"]
            or dimension.get("source_table_id") != context.get("source_table_id")
        ):
            raise NativeTMCanonicalMappingError("native TM dimension foreign keys drifted")
    for observation_id, observation in observations.items():
        row_id = observation.get("row_id")
        dimension_id = observation.get("dimension_id")
        context = contexts.get(observation.get("context_id"))
        if (
            row_id not in rows
            or context is None
            or rows[row_id].get("context_id") != observation.get("context_id")
            or observation.get("source_table_id") != context.get("source_table_id")
            or observation_id not in context["observation_ids"]
            or observation_id not in rows[row_id]["observation_ids"]
            or (
                dimension_id is not None
                and (
                    dimension_id not in dimensions
                    or dimension_id not in context["dimension_ids"]
                    or dimensions[dimension_id].get("context_id") != observation.get("context_id")
                    or dimensions[dimension_id].get("source_table_id")
                    != observation.get("source_table_id")
                )
            )
        ):
            raise NativeTMCanonicalMappingError("native TM observation foreign keys drifted")
    return {
        **indices,
        "source_disposition_records": dispositions,
        "source_disposition_by_id": disposition_by_id,
        "source_evidence_by_id": evidence_by_id,
        "source_reference_ids": reference_ids,
    }


def _candidate_index(
    schema: Sequence[Mapping[str, Any]], aliases: Sequence[Mapping[str, Any]]
) -> dict[str, tuple[_Candidate, ...]]:
    by_id = {int(record["schema_id"]): record for record in schema}
    candidates: dict[str, list[_Candidate]] = defaultdict(list)
    for item in schema:
        key = retrieval_key(str(item["canonical_name"]))
        if key:
            candidates[key].append(
                _Candidate(
                    report_norm_id=int(item["schema_id"]),
                    match_basis="CANONICAL_RETRIEVAL_KEY_EXACT",
                    matched_retrieval_key=key,
                    alias_authority_type=None,
                    alias_authority_evidence_sha256=None,
                )
            )
    for alias in aliases:
        identifier = alias.get("report_norm_id")
        key = retrieval_key(str(alias.get("alias", "")))
        if (
            identifier not in by_id
            or alias.get("statement_type") != _STATEMENT_TYPE
            or alias.get("authority_type") not in _ACCEPTED_ALIAS_TYPES
            or not isinstance(alias.get("authority_evidence_sha256"), str)
            or _SHA256.fullmatch(alias["authority_evidence_sha256"]) is None
            or not key
        ):
            raise NativeTMCanonicalMappingError("typed alias candidate authority is invalid")
        candidates[key].append(
            _Candidate(
                report_norm_id=int(identifier),
                match_basis="ACCEPTED_TYPED_ALIAS_RETRIEVAL_KEY_EXACT",
                matched_retrieval_key=key,
                alias_authority_type=str(alias["authority_type"]),
                alias_authority_evidence_sha256=str(alias["authority_evidence_sha256"]),
            )
        )
    result: dict[str, tuple[_Candidate, ...]] = {}
    priority = {
        "CANONICAL_RETRIEVAL_KEY_EXACT": 0,
        "ACCEPTED_TYPED_ALIAS_RETRIEVAL_KEY_EXACT": 1,
    }
    for key, values in candidates.items():
        selected: dict[int, _Candidate] = {}
        for candidate in values:
            previous = selected.get(candidate.report_norm_id)
            if previous is None or priority[candidate.match_basis] < priority[previous.match_basis]:
                selected[candidate.report_norm_id] = candidate
        result[key] = tuple(
            sorted(
                selected.values(),
                key=lambda candidate: by_id[candidate.report_norm_id]["display_order"],
            )
        )
    return result


def _row_label(row: Mapping[str, Any]) -> str:
    label = row.get("label")
    return normalize_text(label) if isinstance(label, str) else ""


def _discover_root_claims(
    payload: Mapping[str, Any],
    indices: Mapping[str, Any],
    schema: Sequence[Mapping[str, Any]],
    contexts: Sequence[Mapping[str, Any]],
    aliases: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any],
) -> tuple[list[_RootClaim], dict[str, list[int]]]:
    del payload
    schema_by_id = {int(record["schema_id"]): record for record in schema}
    context_by_id = {int(record["report_norm_id"]): record for record in contexts}
    candidate_by_key = _candidate_index(schema, aliases)
    minimum = int(policy["routing"]["minimum_distinct_direct_child_anchors"])
    claims: list[_RootClaim] = []
    row_candidates: dict[str, list[int]] = {}
    rows_by_id = indices["rows"]
    dimensions_by_id = indices["dimensions"]
    observations_by_id = indices["observations"]
    for context in indices["contexts"].values():
        if (
            context.get("page_classification") != "QUANTITATIVE_TM"
            or context.get("source_disposition") != "QUANTITATIVE_TM"
        ):
            continue
        context_rows = tuple(
            sorted(
                (rows_by_id[row_id] for row_id in context["row_ids"]),
                key=lambda row: row.get("row_ordinal", -1),
            )
        )
        anchor_rows = [
            row
            for row in context_rows
            if row.get("row_source_kind") == "REGION_ROW"
            and row.get("value_bearing") is True
            and _row_label(row)
        ]
        if len(anchor_rows) < minimum:
            continue
        anchor_matches: list[tuple[dict[str, Any], _Candidate]] = []
        invalid = False
        for row in anchor_rows:
            candidates = candidate_by_key.get(retrieval_key(_row_label(row)), ())
            row_candidates[str(row["row_id"])] = [
                candidate.report_norm_id for candidate in candidates
            ]
            if len(candidates) != 1:
                invalid = True
                break
            anchor_matches.append((row, candidates[0]))
        if invalid:
            continue
        target_ids = [candidate.report_norm_id for _, candidate in anchor_matches]
        if len(target_ids) != len(set(target_ids)):
            continue
        target_contexts = [context_by_id.get(identifier) for identifier in target_ids]
        if any(
            item is None
            or item.get("context_status") != "RESOLVED"
            or item.get("mapping_eligible") is not True
            for item in target_contexts
        ):
            continue
        parents = {
            item.get("parent_report_norm_id") for item in target_contexts if item is not None
        }
        if len(parents) != 1 or None in parents:
            continue
        root_id = int(next(iter(parents)))
        root_context = context_by_id.get(root_id)
        root_schema = schema_by_id.get(root_id)
        if (
            root_context is None
            or root_schema is None
            or root_context.get("context_status") != "RESOLVED"
            or root_context.get("mapping_eligible") is not True
            or root_context.get("note_family_root_id") != root_id
            or any(item.get("note_family_root_id") != root_id for item in target_contexts)
        ):
            continue
        direct_children = list(root_schema.get("children", []))
        if (
            not direct_children
            or any(schema_by_id[child_id].get("children") for child_id in direct_children)
            or any(
                context_by_id[child_id].get("context_status") != "RESOLVED"
                or context_by_id[child_id].get("mapping_eligible") is not True
                for child_id in direct_children
            )
        ):
            continue
        source_object_ids = {
            str(context["source_object_id"]),
            *(str(row["source_object_id"]) for row in context_rows),
            *(
                str(dimensions_by_id[dimension_id]["source_object_id"])
                for dimension_id in context["dimension_ids"]
            ),
            *(
                str(observations_by_id[observation_id]["source_object_id"])
                for observation_id in context["observation_ids"]
            ),
        }
        owner_references: list[Any] = [
            reference.get("source_owner_id")
            for reference in _as_list(
                context.get("header_run_references", []), "context header-run references"
            )
            if isinstance(reference, dict)
        ]
        for dimension_id in context["dimension_ids"]:
            dimension = dimensions_by_id[dimension_id]
            owner_references.extend(
                component.get("source_owner_id")
                for component in _as_list(
                    dimension.get("header_components", []),
                    "dimension header components",
                )
                if isinstance(component, dict)
            )
        for owner_id in owner_references:
            if not isinstance(owner_id, str) or owner_id not in indices["source_disposition_by_id"]:
                raise NativeTMCanonicalMappingError(
                    "native TM header source owner is absent from source accounting"
                )
            source_object_ids.add(owner_id)
        for observation_id in context["observation_ids"]:
            observation = observations_by_id[observation_id]
            for owner_field in (
                "source_run_owner_id",
                "value_run_owner_id",
                "unit_run_owner_id",
            ):
                owner_id = observation.get(owner_field)
                if isinstance(owner_id, str) and owner_id:
                    if owner_id not in indices["source_disposition_by_id"]:
                        raise NativeTMCanonicalMappingError(
                            "native TM observation source owner is absent from source accounting"
                        )
                    source_object_ids.add(owner_id)
        claims.append(
            _RootClaim(
                root_id=root_id,
                context_id=str(context["context_id"]),
                context=context,
                rows=context_rows,
                dimensions=tuple(
                    dimensions_by_id[identifier] for identifier in context["dimension_ids"]
                ),
                anchors=tuple(anchor_matches),
                source_object_ids=frozenset(source_object_ids),
            )
        )
    return claims, row_candidates


def _decimal_value(observation: Mapping[str, Any]) -> Decimal:
    parsed = observation.get("parsed")
    if not isinstance(parsed, dict) or isinstance(parsed.get("value"), bool):
        raise NativeTMCanonicalMappingError("mapped observation has no exact decimal value")
    try:
        return Decimal(str(parsed["value"]))
    except InvalidOperation as exc:
        raise NativeTMCanonicalMappingError("mapped observation value is invalid") from exc


def _decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value, "f")


def _decimal_sign(value: Decimal) -> str:
    if value < 0:
        return "NEGATIVE"
    if value > 0:
        return "POSITIVE"
    return "ZERO"


def _dimension_materialization(dimension: Mapping[str, Any]) -> dict[str, Any] | None:
    period = dimension.get("period_materialization")
    unit = dimension.get("unit_materialization")
    if (
        dimension.get("binding_status") != "RESOLVED"
        or not isinstance(period, dict)
        or not isinstance(unit, dict)
        or period.get("resolution_status") != "SOURCE_BINDING_RESOLVED"
        or unit.get("resolution_status") != "SOURCE_BINDING_RESOLVED"
    ):
        return None
    period_type = dimension.get("period_type")
    unit_name = dimension.get("unit")
    multiplier = dimension.get("unit_multiplier")
    if (
        not isinstance(period_type, str)
        or not isinstance(unit_name, str)
        or not unit_name
        or isinstance(multiplier, bool)
        or not isinstance(multiplier, int)
        or multiplier <= 0
    ):
        return None
    return {
        "period_type": period_type,
        "period_start": dimension.get("period_start"),
        "period_end": dimension.get("period_end"),
        "as_of_date": dimension.get("period_end") if period_type == "SNAPSHOT" else None,
        "unit": unit_name,
        "unit_multiplier": multiplier,
    }


def _attached_context_blockers(
    payload: Mapping[str, Any], claim: _RootClaim, indices: Mapping[str, Any]
) -> tuple[list[str], list[dict[str, Any]]]:
    blockers: list[str] = []
    boundary_receipts: list[dict[str, Any]] = []
    evidence = _as_object(payload.get("source_evidence"), "source evidence")
    references = _as_object(payload.get("source_references"), "source references")
    for category in ("detached_margin_runs",):
        for raw in _as_list(evidence.get(category, []), f"{category} evidence"):
            record = _as_object(raw, f"{category} evidence record")
            if record.get("context_id") == claim.context_id:
                blockers.append("ATTACHED_DETACHED_OR_UNASSIGNED_SOURCE_EVIDENCE")
    for raw in _as_list(
        references.get("region_unassigned_runs", []), "region-unassigned references"
    ):
        record = _as_object(raw, "region-unassigned reference")
        if record.get("context_id") == claim.context_id:
            blockers.append("ATTACHED_DETACHED_OR_UNASSIGNED_SOURCE_EVIDENCE")
    source_table_id = claim.context.get("source_table_id")
    for raw in _as_list(evidence.get("inter_table_contexts", []), "inter-table context evidence"):
        record = _as_object(raw, "inter-table context evidence record")
        source_record = record.get("source_record")
        if (
            not isinstance(source_record, dict)
            or source_record.get("preceding_table_id") != source_table_id
        ):
            continue
        row_ids = source_record.get("source_row_ids")
        if not isinstance(row_ids, list):
            blockers.append("FOLLOWING_INTER_TABLE_CONTEXT_ACCOUNTING_INVALID")
            continue
        cell_free = True
        for row_id in row_ids:
            row = indices["rows"].get(row_id)
            if (
                row is None
                or row.get("value_bearing") is not False
                or row.get("observation_ids") != []
                or row.get("source_cells", []) != []
            ):
                cell_free = False
                break
        if not cell_free:
            blockers.append("FOLLOWING_INTER_TABLE_CONTEXT_HAS_VALUE_POSITION")
        boundary_receipts.append(
            {
                "evidence_id": record.get("evidence_id", record.get("source_object_id")),
                "ownership_status": source_record.get("ownership_status"),
                "source_row_ids": copy.deepcopy(row_ids),
                "cell_free_after_terminal": cell_free,
                "local_completeness_effect": "PERMITS" if cell_free else "BLOCKS",
                "heading_used_for_routing": False,
                "diagnostic_heading_resolution_required": False,
            }
        )
    return sorted(set(blockers)), boundary_receipts


def _schema_compatible(
    item: Mapping[str, Any], materialization: Mapping[str, Any], report_scope: str
) -> bool:
    allowed_periods = item.get("allowed_period_type")
    allowed_units = item.get("allowed_unit")
    scopes = item.get("scope")
    return (
        isinstance(allowed_periods, list)
        and materialization["period_type"] in allowed_periods
        and isinstance(allowed_units, list)
        and (not allowed_units or materialization["unit"] in allowed_units)
        and isinstance(scopes, list)
        and report_scope in scopes
    )


def _assess_unique_claim(
    payload: Mapping[str, Any],
    claim: _RootClaim,
    indices: Mapping[str, Any],
    schema_by_id: Mapping[int, Mapping[str, Any]],
) -> dict[str, Any]:
    blockers: list[str] = []
    rows = list(claim.rows)
    unlabeled = [row for row in rows if not _row_label(row)]
    terminal = unlabeled[0] if len(unlabeled) == 1 else None
    anchor_rows = [row for row, _candidate in claim.anchors]
    if len(unlabeled) != 1:
        blockers.append("TERMINAL_ROW_NOT_UNIQUE")
    if terminal is not None and rows[-1].get("row_id") != terminal.get("row_id"):
        blockers.append("TERMINAL_ROW_NOT_LAST")
    if any(
        row.get("row_source_kind") != "REGION_ROW" or row.get("value_bearing") is not True
        for row in rows
    ) or {str(row["row_id"]) for row in rows} != {
        *(str(row["row_id"]) for row in anchor_rows),
        *((str(terminal["row_id"]),) if terminal is not None else ()),
    }:
        blockers.append("CONTEXT_ROWS_NOT_EXACT_ANCHOR_TERMINAL_PARTITION")
    dimensions = list(claim.dimensions)
    materializations = [_dimension_materialization(dimension) for dimension in dimensions]
    if not dimensions or any(materialization is None for materialization in materializations):
        blockers.append("DIMENSION_BINDING_UNRESOLVED_OR_INVALID")
    dimension_keys = [
        (
            dimension.get("period_type"),
            dimension.get("period_start"),
            dimension.get("period_end"),
            dimension.get("unit"),
            dimension.get("unit_multiplier"),
        )
        for dimension in dimensions
    ]
    if len(dimension_keys) != len(set(dimension_keys)):
        blockers.append("DIMENSION_BINDING_DUPLICATED")
    report_scope = payload["report_scope_binding"]["scope"]
    mapped_ids = [claim.root_id, *schema_by_id[claim.root_id]["children"]]
    if any(
        materialization is not None
        and not _schema_compatible(schema_by_id[identifier], materialization, report_scope)
        for identifier in mapped_ids
        for materialization in materializations
    ):
        blockers.append("DIMENSION_OR_REPORT_SCOPE_INCOMPATIBLE_WITH_SCHEMA")
    observations_by_id = indices["observations"]
    observation_matrix: dict[tuple[str, str], dict[str, Any]] = {}
    expected_dimension_ids = {str(dimension["dimension_id"]) for dimension in dimensions}
    mapped_rows = [*anchor_rows, *((terminal,) if terminal is not None else ())]
    row_target_ids = {
        str(row["row_id"]): candidate.report_norm_id for row, candidate in claim.anchors
    }
    if terminal is not None:
        row_target_ids[str(terminal["row_id"])] = claim.root_id
    for row in mapped_rows:
        row_id = str(row["row_id"])
        row_observations = [observations_by_id[item] for item in row.get("observation_ids", [])]
        actual_dimensions = [observation.get("dimension_id") for observation in row_observations]
        if (
            len(actual_dimensions) != len(set(actual_dimensions))
            or set(actual_dimensions) != expected_dimension_ids
        ):
            blockers.append("ROW_DIMENSION_OBSERVATION_PARTITION_INCOMPLETE")
            continue
        for observation in row_observations:
            if (
                observation.get("observation_source_kind") != "GRID_SLOT"
                or observation.get("source_status") not in {"OBSERVED_VALUE", "OBSERVED_ZERO"}
                or observation.get("observation_kind") not in {"VALUE", "ZERO"}
            ):
                blockers.append("UNSUPPORTED_OR_UNRESOLVED_OBSERVATION_POSITION")
                continue
            try:
                value = _decimal_value(observation)
            except NativeTMCanonicalMappingError:
                blockers.append("UNSUPPORTED_OR_UNRESOLVED_OBSERVATION_POSITION")
                continue
            if (observation["source_status"] == "OBSERVED_ZERO") != (value == 0):
                blockers.append("UNSUPPORTED_OR_UNRESOLVED_OBSERVATION_POSITION")
                continue
            allowed_signs = schema_by_id[row_target_ids[row_id]].get("allowed_sign")
            if not isinstance(allowed_signs, list) or _decimal_sign(value) not in allowed_signs:
                blockers.append("VALUE_SIGN_INCOMPATIBLE_WITH_SCHEMA")
            observation_matrix[(row_id, str(observation["dimension_id"]))] = observation
    attached_blockers, boundary_receipts = _attached_context_blockers(payload, claim, indices)
    blockers.extend(attached_blockers)
    equation_checks: list[dict[str, Any]] = []
    if terminal is not None and not any(
        blocker
        in {
            "ROW_DIMENSION_OBSERVATION_PARTITION_INCOMPLETE",
            "UNSUPPORTED_OR_UNRESOLVED_OBSERVATION_POSITION",
            "DIMENSION_BINDING_UNRESOLVED_OR_INVALID",
        }
        for blocker in blockers
    ):
        terminal_row_id = str(terminal["row_id"])
        for dimension in dimensions:
            dimension_id = str(dimension["dimension_id"])
            components = [
                observation_matrix[(str(row["row_id"]), dimension_id)] for row in anchor_rows
            ]
            total_observation = observation_matrix[(terminal_row_id, dimension_id)]
            component_sum = sum((_decimal_value(item) for item in components), Decimal(0))
            reported_total = _decimal_value(total_observation)
            delta = reported_total - component_sum
            equation_checks.append(
                {
                    "equation_check_id": f"EQUATION::{claim.context_id}::{dimension_id}",
                    "context_id": claim.context_id,
                    "inferred_root_report_norm_id": claim.root_id,
                    "dimension_id": dimension_id,
                    "component_report_norm_ids": [
                        candidate.report_norm_id for _row, candidate in claim.anchors
                    ],
                    "component_observation_ids": [item["observation_id"] for item in components],
                    "terminal_observation_id": total_observation["observation_id"],
                    "component_sum_source_units": _decimal_text(component_sum),
                    "reported_total_source_units": _decimal_text(reported_total),
                    "delta_source_units": _decimal_text(delta),
                    "tolerance_source_units": "0",
                    "status": "EXACT" if delta == 0 else "MISMATCH",
                    "used_for_target_selection": False,
                    "used_as_post_lineage_veto": True,
                }
            )
            if delta != 0:
                blockers.append("EXACT_EQUATION_MISMATCH")
    return {
        "accepted": not blockers,
        "blockers": sorted(set(blockers)),
        "terminal": terminal,
        "materializations": materializations,
        "observation_matrix": observation_matrix,
        "equation_checks": equation_checks,
        "boundary_contexts": boundary_receipts,
    }


def _source_disposition_projection(
    indices: Mapping[str, Any], row_candidates: Mapping[str, list[int]]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    result: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    for upstream in indices["source_disposition_records"]:
        record = {
            "source_object_type": upstream["source_object_type"],
            "source_object_id": upstream["source_object_id"],
            "upstream_source_disposition": upstream["source_disposition"],
            "mapping_disposition": "UNRESOLVED",
            "reason": "UNASSESSED_OUTSIDE_BOUNDED_TABLE_SUBTREE",
            "context_id": None,
            "row_id": None,
            "dimension_id": None,
            "target_report_norm_id": None,
            "candidate_report_norm_ids": [],
            "match_basis": None,
            "matched_retrieval_key": None,
            "alias_authority_type": None,
            "alias_authority_evidence_sha256": None,
        }
        result.append(record)
        by_id[str(record["source_object_id"])] = record
    for context_id, context in indices["contexts"].items():
        by_id[str(context["source_object_id"])]["context_id"] = context_id
    for row_id, row in indices["rows"].items():
        by_id[str(row["source_object_id"])].update(
            {"context_id": row["context_id"], "row_id": row_id}
        )
    for dimension_id, dimension in indices["dimensions"].items():
        by_id[str(dimension["source_object_id"])].update(
            {"context_id": dimension["context_id"], "dimension_id": dimension_id}
        )
    for observation in indices["observations"].values():
        by_id[str(observation["source_object_id"])].update(
            {
                "context_id": observation["context_id"],
                "row_id": observation["row_id"],
                "dimension_id": observation.get("dimension_id"),
            }
        )
    for row_id, candidates in row_candidates.items():
        row = indices["rows"].get(row_id)
        if row is not None:
            by_id[str(row["source_object_id"])]["candidate_report_norm_ids"] = copy.deepcopy(
                candidates
            )
    result.sort(key=lambda record: (record["source_object_type"], record["source_object_id"]))
    return result, by_id


def _mark_claim_source_objects(
    claim: _RootClaim,
    source_by_id: Mapping[str, dict[str, Any]],
    *,
    disposition: str,
    reason: str,
) -> None:
    for source_object_id in claim.source_object_ids:
        record = source_by_id[source_object_id]
        record["mapping_disposition"] = disposition
        record["reason"] = reason
        record["context_id"] = claim.context_id


def _schema_disposition_projection(
    schema: Sequence[Mapping[str, Any]], contexts: Sequence[Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]]]:
    context_by_id = {int(record["report_norm_id"]): record for record in contexts}
    records: list[dict[str, Any]] = []
    by_id: dict[int, dict[str, Any]] = {}
    for item in schema:
        identifier = int(item["schema_id"])
        context = context_by_id[identifier]
        record = {
            "report_norm_id": identifier,
            "canonical_name": item["canonical_name"],
            "display_order": item["display_order"],
            "context_status": context["context_status"],
            "mapping_eligible": context["mapping_eligible"],
            "parent_report_norm_id": context["parent_report_norm_id"],
            "note_family_root_id": context["note_family_root_id"],
            "mapping_disposition": "UNRESOLVED",
            "terminal_outcome": "UNRESOLVED",
            "reason": "UNASSESSED_OUTSIDE_BOUNDED_TABLE_SUBTREE",
            "source_row_ids": [],
            "source_observation_ids": [],
        }
        records.append(record)
        by_id[identifier] = record
    return records, by_id


def _observation_outcome(observations: Sequence[Mapping[str, Any]]) -> str:
    return (
        "OBSERVED_ZERO"
        if observations
        and all(item.get("source_status") == "OBSERVED_ZERO" for item in observations)
        else "OBSERVED_VALUE"
    )


def _apply_accepted_claim(
    *,
    payload: Mapping[str, Any],
    claim: _RootClaim,
    assessment: Mapping[str, Any],
    indices: Mapping[str, Any],
    schema_by_id: Mapping[int, Mapping[str, Any]],
    source_by_id: Mapping[str, dict[str, Any]],
    schema_disposition_by_id: Mapping[int, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    _mark_claim_source_objects(
        claim,
        source_by_id,
        disposition="ASSESSED_BOUNDED_SUBTREE",
        reason="LOCALLY_COMPLETE_CORROBORATED_DIRECT_CHILD_BUNDLE",
    )
    context_source = source_by_id[str(claim.context["source_object_id"])]
    context_source["target_report_norm_id"] = claim.root_id
    for dimension in claim.dimensions:
        source = source_by_id[str(dimension["source_object_id"])]
        source["mapping_disposition"] = "ASSESSED_SUPPORTING_DIMENSION"
        source["reason"] = "RESOLVED_COMPATIBLE_BOUNDED_SUBTREE_DIMENSION"
        source["dimension_id"] = dimension["dimension_id"]
        source["target_report_norm_id"] = claim.root_id
    terminal = assessment["terminal"]
    if not isinstance(terminal, dict):
        raise NativeTMCanonicalMappingError("accepted root lost its terminal row")
    row_targets = {str(row["row_id"]): candidate for row, candidate in claim.anchors}
    row_targets[str(terminal["row_id"])] = _Candidate(
        report_norm_id=claim.root_id,
        match_basis="UNLABELED_TERMINAL_TOTAL_OF_DIRECT_CHILD_BUNDLE",
        matched_retrieval_key="",
        alias_authority_type=None,
        alias_authority_evidence_sha256=None,
    )
    canonical_observations: list[dict[str, Any]] = []
    report_scope = str(payload["report_scope_binding"]["scope"])
    observations_by_id = indices["observations"]
    dimensions_by_id = indices["dimensions"]
    for row in [*(row for row, _candidate in claim.anchors), terminal]:
        row_id = str(row["row_id"])
        candidate = row_targets[row_id]
        row_source = source_by_id[str(row["source_object_id"])]
        row_source.update(
            {
                "mapping_disposition": "MAPPED_EXISTING_ITEM",
                "reason": (
                    "GLOBALLY_UNIQUE_EXACT_DIRECT_CHILD_ANCHOR"
                    if row_id != terminal["row_id"]
                    else "UNLABELED_TERMINAL_TOTAL_OF_CORROBORATED_DIRECT_CHILD_BUNDLE"
                ),
                "row_id": row_id,
                "target_report_norm_id": candidate.report_norm_id,
                "candidate_report_norm_ids": [candidate.report_norm_id],
                "match_basis": candidate.match_basis,
                "matched_retrieval_key": candidate.matched_retrieval_key or None,
                "alias_authority_type": candidate.alias_authority_type,
                "alias_authority_evidence_sha256": candidate.alias_authority_evidence_sha256,
            }
        )
        mapped_observations = [observations_by_id[item] for item in row["observation_ids"]]
        schema_disposition = schema_disposition_by_id[candidate.report_norm_id]
        schema_disposition.update(
            {
                "mapping_disposition": "EXISTING_ITEM",
                "terminal_outcome": _observation_outcome(mapped_observations),
                "reason": row_source["reason"],
                "source_row_ids": [row_id],
                "source_observation_ids": [item["observation_id"] for item in mapped_observations],
            }
        )
        for observation in mapped_observations:
            dimension = dimensions_by_id[str(observation["dimension_id"])]
            materialization = _dimension_materialization(dimension)
            if materialization is None:
                raise NativeTMCanonicalMappingError("accepted observation lost its dimension")
            value = _decimal_value(observation)
            canonical_value = value * Decimal(materialization["unit_multiplier"])
            observation_source = source_by_id[str(observation["source_object_id"])]
            observation_source.update(
                {
                    "mapping_disposition": "MAPPED_EXISTING_ITEM",
                    "reason": row_source["reason"],
                    "context_id": claim.context_id,
                    "row_id": row_id,
                    "dimension_id": observation["dimension_id"],
                    "target_report_norm_id": candidate.report_norm_id,
                    "candidate_report_norm_ids": [candidate.report_norm_id],
                    "match_basis": candidate.match_basis,
                    "matched_retrieval_key": candidate.matched_retrieval_key or None,
                    "alias_authority_type": candidate.alias_authority_type,
                    "alias_authority_evidence_sha256": candidate.alias_authority_evidence_sha256,
                }
            )
            canonical_observations.append(
                {
                    "observation_id": observation["observation_id"],
                    "row_id": row_id,
                    "dimension_id": observation["dimension_id"],
                    "context_id": claim.context_id,
                    "report_norm_id": candidate.report_norm_id,
                    "terminal_outcome": (
                        "OBSERVED_ZERO"
                        if observation["source_status"] == "OBSERVED_ZERO"
                        else "OBSERVED_VALUE"
                    ),
                    "reported_value": _decimal_text(value),
                    "unit": materialization["unit"],
                    "unit_multiplier": materialization["unit_multiplier"],
                    "canonical_value": _decimal_text(canonical_value),
                    "period_type": materialization["period_type"],
                    "period_start": materialization["period_start"],
                    "period_end": materialization["period_end"],
                    "as_of_date": materialization["as_of_date"],
                    "presentation_scope": report_scope,
                    "match_basis": candidate.match_basis,
                    "source_record_sha256": observation.get(
                        "source_slot_record_sha256", _record_sha256(observation)
                    ),
                }
            )
    root_children = list(schema_by_id[claim.root_id]["children"])
    observed_children = sorted(
        (candidate.report_norm_id for _row, candidate in claim.anchors),
        key=lambda identifier: schema_by_id[identifier]["display_order"],
    )
    absent_children = [
        identifier for identifier in root_children if identifier not in observed_children
    ]
    for identifier in absent_children:
        schema_disposition_by_id[identifier].update(
            {
                "mapping_disposition": "LOCALLY_NOT_OBSERVED",
                "terminal_outcome": "NOT_OBSERVED",
                "reason": "ABSENT_FROM_LOCALLY_COMPLETE_BOUNDED_TABLE_SUBTREE",
                "source_row_ids": [],
                "source_observation_ids": [],
            }
        )
    accepted_subtree = {
        "inferred_root_report_norm_id": claim.root_id,
        "context_id": claim.context_id,
        "source_table_id": claim.context.get("source_table_id"),
        "anchor_row_ids": [row["row_id"] for row, _candidate in claim.anchors],
        "anchor_report_norm_ids": observed_children,
        "terminal_row_id": terminal["row_id"],
        "direct_child_report_norm_ids": root_children,
        "not_observed_direct_child_report_norm_ids": absent_children,
        "dimension_ids": [dimension["dimension_id"] for dimension in claim.dimensions],
        "equation_check_ids": [
            check["equation_check_id"] for check in assessment["equation_checks"]
        ],
        "boundary_contexts": copy.deepcopy(assessment["boundary_contexts"]),
        "local_completeness_status": "COMPLETE_BOUNDED_TABLE_SUBTREE",
        "document_context_complete": False,
    }
    return accepted_subtree, canonical_observations


def _resolve_native_tm_canonical_mapping(
    observation_payload: Mapping[str, Any],
    *,
    observations_sha256: str,
    tm_schema: Sequence[Mapping[str, Any]],
    tm_contexts: Sequence[Mapping[str, Any]],
    accepted_typed_aliases: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve independently qualified shallow TM families with complete accounting."""

    policy = _validate_policy_payload(copy.deepcopy(dict(policy)))
    if _SHA256.fullmatch(observations_sha256) is None:
        raise NativeTMCanonicalMappingError("trusted native TM observations SHA-256 is invalid")
    payload = copy.deepcopy(dict(observation_payload))
    _validate_observation_envelope(payload, policy)
    schema = copy.deepcopy(list(tm_schema))
    contexts = copy.deepcopy(list(tm_contexts))
    aliases = copy.deepcopy(list(accepted_typed_aliases))
    expected_count = policy["coverage"]["schema_item_count"]
    schema_ids = [item.get("schema_id") for item in schema]
    context_ids = [item.get("report_norm_id") for item in contexts]
    if (
        len(schema) != expected_count
        or len(contexts) != expected_count
        or [item.get("display_order") for item in schema] != list(range(expected_count))
        or [item.get("display_order") for item in contexts] != list(range(expected_count))
        or any(
            isinstance(identifier, bool) or not isinstance(identifier, int)
            for identifier in schema_ids
        )
        or any(
            isinstance(identifier, bool) or not isinstance(identifier, int)
            for identifier in context_ids
        )
        or len(set(schema_ids)) != expected_count
        or len(set(context_ids)) != expected_count
        or schema_ids != context_ids
    ):
        raise NativeTMCanonicalMappingError("TM schema/context denominator drifted")
    schema_by_id = {int(item["schema_id"]): item for item in schema}
    indices = _source_indices(payload)
    claims, row_candidates = _discover_root_claims(
        payload,
        indices,
        schema,
        contexts,
        aliases,
        policy,
    )
    source_dispositions, source_by_id = _source_disposition_projection(indices, row_candidates)
    schema_dispositions, schema_disposition_by_id = _schema_disposition_projection(schema, contexts)
    claims_by_root: dict[int, list[_RootClaim]] = defaultdict(list)
    for claim in claims:
        claims_by_root[claim.root_id].append(claim)
    collision_roots: set[int] = set()
    for index, left in enumerate(claims):
        for right in claims[index + 1 :]:
            if left.root_id != right.root_id and left.source_object_ids & right.source_object_ids:
                collision_roots.update((left.root_id, right.root_id))
    root_assessments: list[dict[str, Any]] = []
    accepted_subtrees: list[dict[str, Any]] = []
    canonical_observations: list[dict[str, Any]] = []
    equation_checks: list[dict[str, Any]] = []
    for root_id in sorted(
        claims_by_root, key=lambda identifier: schema_by_id[identifier]["display_order"]
    ):
        root_claims = sorted(claims_by_root[root_id], key=lambda claim: claim.context_id)
        base = {
            "inferred_root_report_norm_id": root_id,
            "claiming_context_ids": [claim.context_id for claim in root_claims],
            "claiming_source_table_ids": [
                claim.context.get("source_table_id") for claim in root_claims
            ],
            "accepted_context_id": None,
            "anchor_row_ids": [
                row["row_id"] for claim in root_claims for row, _candidate in claim.anchors
            ],
            "anchor_report_norm_ids": [
                candidate.report_norm_id
                for claim in root_claims
                for _row, candidate in claim.anchors
            ],
            "terminal_row_id": None,
            "equation_check_ids": [],
            "blockers": [],
        }
        if len(root_claims) > 1:
            reason = "AMBIGUOUS_MULTIPLE_CONTEXTS_CLAIM_ROOT"
            for claim in root_claims:
                _mark_claim_source_objects(
                    claim,
                    source_by_id,
                    disposition="AMBIGUOUS",
                    reason=reason,
                )
            for identifier in [root_id, *schema_by_id[root_id]["children"]]:
                schema_disposition_by_id[identifier]["reason"] = reason
            root_assessments.append(
                {**base, "status": "AMBIGUOUS_MULTIPLE_SOURCE_CONTEXTS", "blockers": [reason]}
            )
            continue
        claim = root_claims[0]
        if root_id in collision_roots:
            reason = "CROSS_ROOT_SOURCE_OWNERSHIP_COLLISION"
            _mark_claim_source_objects(
                claim,
                source_by_id,
                disposition="AMBIGUOUS",
                reason=reason,
            )
            for identifier in [root_id, *schema_by_id[root_id]["children"]]:
                schema_disposition_by_id[identifier]["reason"] = reason
            root_assessments.append(
                {**base, "status": "UNRESOLVED_SOURCE_OWNERSHIP_COLLISION", "blockers": [reason]}
            )
            continue
        assessment = _assess_unique_claim(payload, claim, indices, schema_by_id)
        equation_checks.extend(assessment["equation_checks"])
        if not assessment["accepted"]:
            reason = str(assessment["blockers"][0])
            _mark_claim_source_objects(
                claim,
                source_by_id,
                disposition="UNRESOLVED",
                reason=reason,
            )
            for identifier in [root_id, *schema_by_id[root_id]["children"]]:
                schema_disposition_by_id[identifier]["reason"] = reason
            terminal = assessment["terminal"]
            root_assessments.append(
                {
                    **base,
                    "status": "UNRESOLVED_LOCAL_COMPLETENESS_OR_EQUATION",
                    "terminal_row_id": terminal.get("row_id")
                    if isinstance(terminal, dict)
                    else None,
                    "equation_check_ids": [
                        check["equation_check_id"] for check in assessment["equation_checks"]
                    ],
                    "blockers": copy.deepcopy(assessment["blockers"]),
                }
            )
            continue
        accepted_subtree, mapped_observations = _apply_accepted_claim(
            payload=payload,
            claim=claim,
            assessment=assessment,
            indices=indices,
            schema_by_id=schema_by_id,
            source_by_id=source_by_id,
            schema_disposition_by_id=schema_disposition_by_id,
        )
        accepted_subtrees.append(accepted_subtree)
        canonical_observations.extend(mapped_observations)
        root_assessments.append(
            {
                **base,
                "status": "ACCEPTED",
                "accepted_context_id": claim.context_id,
                "terminal_row_id": accepted_subtree["terminal_row_id"],
                "equation_check_ids": accepted_subtree["equation_check_ids"],
                "blockers": [],
            }
        )
    canonical_observations.sort(
        key=lambda record: (
            schema_by_id[record["report_norm_id"]]["display_order"],
            indices["dimensions"][record["dimension_id"]].get("axis_ordinal", -1),
            record["observation_id"],
        )
    )
    disposition_ids = [record["report_norm_id"] for record in schema_dispositions]
    if (
        len(schema_dispositions) != expected_count
        or [record["display_order"] for record in schema_dispositions]
        != list(range(expected_count))
        or len(set(disposition_ids)) != expected_count
        or set(disposition_ids) != set(schema_ids)
    ):
        raise NativeTMCanonicalMappingError("TM schema dispositions are not complete and ordered")
    terminal_counts = Counter(record["terminal_outcome"] for record in schema_dispositions)
    if sum(terminal_counts.values()) != expected_count or not set(terminal_counts) <= set(
        _TERMINAL_OUTCOMES
    ):
        raise NativeTMCanonicalMappingError("TM terminal outcome partition drifted")
    if len(source_dispositions) != len(indices["source_disposition_records"]):
        raise NativeTMCanonicalMappingError("source-object mapping disposition denominator drifted")
    input_source_projection = copy.deepcopy(indices["source_disposition_records"])
    return {
        "routing_contract": {
            "candidate_authorities": copy.deepcopy(policy["routing"]["candidate_authorities"]),
            "minimum_distinct_direct_child_anchors": policy["routing"][
                "minimum_distinct_direct_child_anchors"
            ],
            "root_occurrence_policy": policy["routing"]["root_occurrence_policy"],
            "distinct_roots_evaluated_independently": True,
            "zero_accepted_roots_allowed": True,
            "equation_used_for_target_selection": False,
        },
        "root_assessments": root_assessments,
        "accepted_subtrees": accepted_subtrees,
        "source_accounting": {
            "upstream_source_object_count": len(input_source_projection),
            "mapping_source_disposition_count": len(source_dispositions),
            "upstream_source_dispositions_sha256": _record_sha256(input_source_projection),
            "mapping_source_dispositions_sha256": _record_sha256(source_dispositions),
            "exactly_one_mapping_disposition_per_upstream_source_object": True,
            "source_object_accounting_complete": True,
        },
        "source_dispositions": source_dispositions,
        "canonical_observations": canonical_observations,
        "schema_dispositions": schema_dispositions,
        "equation_checks": equation_checks,
        "coverage": {
            "statement_type": _STATEMENT_TYPE,
            "schema_item_count": expected_count,
            "schema_disposition_count": len(schema_dispositions),
            "terminal_outcome_counts": {
                outcome: terminal_counts.get(outcome, 0) for outcome in _TERMINAL_OUTCOMES
            },
            "reason_counts": dict(
                sorted(Counter(record["reason"] for record in schema_dispositions).items())
            ),
            "exactly_one_terminal_outcome_per_schema_id": True,
            "workbook_display_order_complete": True,
        },
        "completion": {
            "accepted_root_count": len(accepted_subtrees),
            "source_accounting_complete": True,
            "tm_schema_disposition_accounting_complete": True,
            "document_complete": False,
            "upstream_full_document_context_complete": payload["source_accounting"].get(
                "full_document_context_complete"
            )
            is True,
        },
    }


def _committed_runtime_identity(
    project_root: Path,
    producer_commit: str,
    record: Mapping[str, Any],
) -> dict[str, Any]:
    return _file_identity_at_commit(
        project_root,
        producer_commit,
        str(record["path"]),
        kind=str(record["kind"]),
    )


def build_registered_native_tm_canonical_mapping(
    project_root: Path,
    native_tm_observations_path: Path,
    native_tm_observations_sha256: str,
    policy_path: Path,
    run_id: str,
) -> dict[str, Any]:
    """Strict-load observations and build complete source/schema dispositions."""

    project_root = project_root.resolve()
    if not isinstance(run_id, str) or _SAFE_RUN_ID.fullmatch(run_id) is None:
        raise NativeTMCanonicalMappingError("native TM canonical run_id is invalid")
    if (
        not isinstance(native_tm_observations_sha256, str)
        or _SHA256.fullmatch(native_tm_observations_sha256) is None
    ):
        raise NativeTMCanonicalMappingError("trusted native TM observations SHA-256 is invalid")
    code = _current_git_state(project_root)
    policy_path, policy_relative = _lexical_project_path(
        project_root, policy_path, "native TM canonical policy"
    )
    if policy_relative != POLICY_RELATIVE_PATH.as_posix():
        raise NativeTMCanonicalMappingError(
            f"native TM canonical mapping requires {POLICY_RELATIVE_PATH.as_posix()}"
        )
    observations_path, observations_relative = _lexical_project_path(
        project_root,
        native_tm_observations_path,
        "registered native TM observations artifact",
    )
    if not observations_relative.startswith(f"{_OUTPUT_DIRECTORY}/"):
        raise NativeTMCanonicalMappingError(
            "LOGIC_DEVELOPMENT native TM observations must stay under output/development"
        )
    policy_guard = _open_guard(
        project_root, policy_path, policy_relative, "native TM canonical policy"
    )
    observations_guard: Any | None = None
    authority_guards: list[Any] = []
    try:
        policy = _validate_policy_payload(
            _yaml_bytes(policy_guard.payload, "native TM canonical policy")
        )
        _validate_path_isolation(
            [
                policy_relative,
                observations_relative,
                *_IMPLEMENTATION_PATHS,
                *(relative for _kind, relative, _digest in _authority_specs(policy)),
            ]
        )
        observations_guard = _open_guard(
            project_root,
            observations_path,
            observations_relative,
            "registered native TM observations artifact",
        )
        if sha256_bytes(observations_guard.payload) != native_tm_observations_sha256:
            raise NativeTMCanonicalMappingError(
                "native TM observations artifact does not match trusted SHA-256"
            )
        try:
            held_observation_payload = json.loads(observations_guard.payload)
        except json.JSONDecodeError as exc:
            raise NativeTMCanonicalMappingError(
                "native TM observations artifact is invalid JSON"
            ) from exc
        if not isinstance(
            held_observation_payload, dict
        ) or observations_guard.payload != _native_observations._canonical_json_bytes(
            held_observation_payload
        ):
            raise NativeTMCanonicalMappingError(
                "native TM observations artifact is not canonical JSON"
            )
        try:
            observation_payload = _native_observations.load_registered_native_tm_observations(
                observations_path,
                project_root=project_root,
                expected_sha256=native_tm_observations_sha256,
            )
        except Exception as exc:
            raise NativeTMCanonicalMappingError(
                "registered native TM observations failed strict load"
            ) from exc
        if observation_payload != held_observation_payload:
            raise NativeTMCanonicalMappingError(
                "strict native TM observations payload differs from held bytes"
            )
        authority_guards, authority_bytes, authority_ledger = _open_runtime_authorities(
            project_root, policy
        )
        schema, contexts, aliases, schema_identity = _load_authority_bundle(authority_bytes, policy)
        implementation = _implementation_ledger(project_root)
        if implementation != _implementation_ledger_at_commit(project_root, code["commit"]):
            raise NativeTMCanonicalMappingError(
                "native TM canonical implementation differs from clean producer HEAD"
            )
        policy_identity = _identity_from_guard(policy_guard, "THIS_POLICY")
        committed_policy = _committed_runtime_identity(
            project_root, code["commit"], policy_identity
        )
        if policy_identity != committed_policy:
            raise NativeTMCanonicalMappingError(
                "native TM canonical policy differs from clean producer HEAD"
            )
        for record in authority_ledger:
            if record != _committed_runtime_identity(project_root, code["commit"], record):
                raise NativeTMCanonicalMappingError(
                    "native TM canonical authority differs from clean producer HEAD"
                )
        runtime_inputs = sorted(
            [
                _identity_from_guard(observations_guard, "NATIVE_TM_OBSERVATIONS_ARTIFACT"),
                policy_identity,
                *authority_ledger,
            ],
            key=lambda record: (record["kind"], record["path"]),
        )
        snapshots = _producer_snapshots(
            policy_relative=policy_relative,
            policy_bytes=bytes(policy_guard.payload),
            policy=policy,
            schema=schema,
            contexts=contexts,
            aliases=aliases,
        )
        resolved = _resolve_native_tm_canonical_mapping(
            observation_payload,
            observations_sha256=native_tm_observations_sha256,
            tm_schema=schema,
            tm_contexts=contexts,
            accepted_typed_aliases=aliases,
            policy=policy,
        )
        inherited = {
            "inputs": copy.deepcopy(observation_payload.get("inputs")),
            "inputs_sha256": _record_sha256(observation_payload.get("inputs")),
            "implementation": copy.deepcopy(
                observation_payload.get("code", {}).get("implementation")
            ),
            "implementation_sha256": _record_sha256(
                observation_payload.get("code", {}).get("implementation")
            ),
            "producer_snapshots": copy.deepcopy(observation_payload.get("producer_snapshots")),
            "producer_snapshots_sha256": _record_sha256(
                observation_payload.get("producer_snapshots")
            ),
            "source_accounting": copy.deepcopy(observation_payload.get("source_accounting")),
            "source_accounting_sha256": _record_sha256(
                observation_payload.get("source_accounting")
            ),
        }
        source = copy.deepcopy(observation_payload["source"])
        payload: dict[str, Any] = {
            "format_version": _OUTPUT_FORMAT,
            "policy": _POLICY_NAME,
            "claim_boundary": _CLAIM_BOUNDARY,
            "status": _OUTPUT_STATUS,
            "run_id": run_id,
            "source": source,
            "native_tm_observations": {
                "path": observations_relative,
                "sha256": native_tm_observations_sha256,
                "size_bytes": len(observations_guard.payload),
                "format_version": observation_payload["format_version"],
                "policy": observation_payload["policy"],
                "claim_boundary": observation_payload["claim_boundary"],
                "status": observation_payload["status"],
                "run_id": observation_payload["run_id"],
                "producer_git_commit": observation_payload["code"]["commit"],
            },
            "schema": schema_identity,
            "code": {**code, "implementation": implementation},
            "authority": {
                "source_observations": "STRICT_TRUSTED_SHA_NATIVE_TM_OBSERVATIONS_ARTIFACT",
                "canonical_labels": "PINNED_UNIVERSAL_TM_SCHEMA_GRAPH",
                "hierarchy_context": "PINNED_TM_CONTEXT_PROJECTION",
                "aliases": "PINNED_TYPED_ACCEPTED_TM_ALIASES_ONLY",
                "ordering": "WORKBOOK_DISPLAY_ORDER",
                "equations": "POST_LINEAGE_CORROBORATION_OR_VETO_ONLY",
            },
            "isolation": {
                "prior_answer_artifacts_loaded": False,
                "historical_values_loaded": False,
                "role_a_outputs_loaded": False,
                "human_review_outputs_loaded": False,
                "bank_identity_used_for_routing": False,
                "filename_identity_used_for_routing": False,
                "page_number_used_for_routing": False,
                "note_number_used_for_routing": False,
                "table_title_used_for_routing": False,
                "expected_source_counts_used_for_routing": False,
                "enumerator_stripping_used": False,
                "accounting_abbreviation_expansion_used": False,
                "fuzzy_matching_used": False,
            },
            "non_decision_features": {
                "source_identity": "PROVENANCE_ONLY",
                "source_table_id": "GROUPING_AND_PROVENANCE_ONLY",
                "page_number": "UPSTREAM_STABLE_ID_AND_PROVENANCE_ONLY",
                "table_title": "PRESERVED_UPSTREAM_EVIDENCE_ONLY",
                "observed_counts": "POST_BUILD_ACCOUNTING_ONLY",
            },
            "inputs": {
                "direct_runtime_input_ledger": runtime_inputs,
                "direct_runtime_input_ledger_sha256": _runtime_ledger_sha256(runtime_inputs),
                "inherited_upstream_replay_provenance": inherited,
            },
            "producer_snapshots": snapshots,
            **resolved,
        }
        for guard, label in [
            (policy_guard, "native TM canonical policy"),
            (observations_guard, "native TM observations artifact"),
            *((guard, "native TM mapping authority") for guard in authority_guards),
        ]:
            _revalidate_guard(guard, label)
        if _implementation_ledger(project_root) != implementation:
            raise NativeTMCanonicalMappingError(
                "native TM canonical implementation changed during build"
            )
        if _current_git_state(project_root) != code:
            raise NativeTMCanonicalMappingError(
                "native TM canonical producer HEAD changed during build"
            )
        return json.loads(_canonical_json_bytes(payload))
    finally:
        for guard in reversed(authority_guards):
            _close_guard(guard)
        if observations_guard is not None:
            _close_guard(observations_guard)
        _close_guard(policy_guard)


_PRODUCER_REPLAY_BOOTSTRAP = r"""
import pathlib
import sys

source_tree = pathlib.Path(sys.argv[1]).resolve()
repository = pathlib.Path(sys.argv[2]).resolve()
sys.path.insert(0, str(source_tree / "src"))
from bctc_ai.mapping import native_tm_canonical as producer

expected_module = (source_tree / "src/bctc_ai/mapping/native_tm_canonical.py").resolve()
if pathlib.Path(producer.__file__).resolve() != expected_module:
    raise RuntimeError("producer replay imported outside its isolated source tree")
payload = producer.build_registered_native_tm_canonical_mapping(
    repository,
    repository / sys.argv[3],
    sys.argv[4],
    repository / producer.POLICY_RELATIVE_PATH,
    sys.argv[5],
)
sys.stdout.buffer.write(producer._canonical_json_bytes(payload))
"""


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
        raise NativeTMCanonicalMappingError(
            "native TM canonical producer-commit replay process failed"
        ) from exc
    if result.returncode != 0:
        raise NativeTMCanonicalMappingError(
            "native TM canonical producer-commit replay process failed"
        )
    return result.stdout


def _write_new_file(path: Path, payload: bytes) -> None:
    try:
        _native_document._write_new_file(path, payload)
    except _native_document.NativeTMDocumentArtifactError as exc:
        raise NativeTMCanonicalMappingError(str(exc)) from exc


def _install_replay_input(clone_root: Path, relative: str, payload: bytes, label: str) -> None:
    destination = clone_root.joinpath(*PurePosixPath(relative).parts)
    if destination.exists():
        guard = _open_guard(clone_root, destination, relative, label)
        try:
            if guard.payload != payload:
                raise NativeTMCanonicalMappingError(
                    f"producer-commit {label} differs from replay input"
                )
        finally:
            _close_guard(guard)
        return
    _write_new_file(destination, payload)


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
        or [record.get("path") for record in code["implementation"] if isinstance(record, dict)]
        != list(_IMPLEMENTATION_PATHS)
    ):
        raise NativeTMCanonicalMappingError("native TM canonical producer identity is invalid")
    expected = _implementation_ledger_at_commit(project_root, code["commit"])
    if code["implementation"] != expected:
        raise NativeTMCanonicalMappingError(
            "native TM canonical implementation is not bound to its producer commit"
        )
    return code["commit"], copy.deepcopy(code["implementation"])


def _reject_policy_selector_keys(value: Any, label: str) -> None:
    if isinstance(value, list):
        for item in value:
            _reject_policy_selector_keys(item, label)
        return
    if not isinstance(value, dict):
        return
    for raw_key, item in value.items():
        if not isinstance(raw_key, str):
            raise NativeTMCanonicalMappingError(f"{label} has a non-string policy key")
        key = raw_key.casefold().replace("-", "_")
        tokens = tuple(part for part in key.split("_") if part)
        token_set = set(tokens)
        if key.endswith(("_used_for_routing", "_rules_used_for_routing")):
            if item is not False:
                raise NativeTMCanonicalMappingError(
                    f"{label} enables a forbidden selector policy key"
                )
        elif (
            ("root" in token_set and bool({"id", "ids"} & token_set))
            or (
                tokens[:1] == ("source",)
                and bool(
                    {"title", "page", "pages", "note", "table", "bank", "filename", "file"}
                    & token_set
                )
            )
            or (tokens[:1] == ("expected",) and bool({"count", "counts"} & token_set))
            or ("bank" in token_set and bool({"id", "name"} & token_set))
            or ("table" in token_set and bool({"id", "ids", "title", "titles"} & token_set))
            or tokens in {("page",), ("note",), ("bank",), ("filename",), ("file",)}
        ):
            raise NativeTMCanonicalMappingError(f"{label} contains a forbidden selector policy key")
        _reject_policy_selector_keys(item, label)


def _require_policy_fields(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise NativeTMCanonicalMappingError(f"{label} fields drifted")
    return value


def _validate_policy_identity_shape(value: Any, label: str) -> None:
    if (
        not isinstance(value, dict)
        or set(value) != {"path", "sha256"}
        or not isinstance(value.get("path"), str)
        or not value["path"]
        or not isinstance(value.get("sha256"), str)
        or _SHA256.fullmatch(value["sha256"]) is None
    ):
        raise NativeTMCanonicalMappingError(f"{label} identity is invalid")


def _validate_replay_policy_minimum(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise NativeTMCanonicalMappingError("producer native TM canonical policy is invalid")
    _reject_policy_selector_keys(payload, "producer native TM canonical policy")
    _require_policy_fields(
        payload,
        {
            "version",
            "policy",
            "claim_boundary",
            "require_clean_git",
            "accepted_native_tm_observations",
            "schema_authority",
            "typed_alias_authority",
            "routing",
            "local_completion",
            "coverage",
            "role_isolation",
            "output",
        },
        "producer native TM canonical policy",
    )
    accepted = _require_policy_fields(
        payload.get("accepted_native_tm_observations"),
        {
            "format_version",
            "policy",
            "claim_boundary",
            "status",
            "required_dataset_role",
            "trusted_sha256_required",
            "strict_producer_commit_replay_required",
            "exact_source_accounting_required",
            "required_collections",
        },
        "producer accepted native TM observations",
    )
    schema = _require_policy_fields(
        payload.get("schema_authority"),
        {
            "schema_name",
            "revision",
            "statement_type",
            "item_count",
            "order_authority",
            "schema_registry",
            "schema_graph",
            "tm_projection_sha256",
            "tm_context_policy",
            "tm_context_projection_sha256",
            "coverage_registry",
        },
        "producer native TM schema authority",
    )
    aliases = _require_policy_fields(
        payload.get("typed_alias_authority"),
        {
            "accepted_authority_types",
            "untyped_structural_aliases_mapping_eligible",
            "historical_aliases_allowed",
            "fuzzy_matching_allowed",
            "strip_structural_enumerators",
            "accounting_abbreviation_expansion_allowed",
            "schema_source_config",
            "hierarchy_config",
            "hierarchy_registry",
            "tm_hierarchy_workbook",
            "business_update_audits",
            "tm_projection_record_count",
            "tm_projection_sha256",
        },
        "producer typed TM alias authority",
    )
    routing = _require_policy_fields(
        payload.get("routing"),
        {
            "statement_type",
            "normalization",
            "candidate_authorities",
            "global_candidate_uniqueness_required",
            "minimum_distinct_direct_child_anchors",
            "require_distinct_target_per_anchor",
            "require_unanimous_direct_parent",
            "require_parent_equals_note_family_root",
            "require_resolved_mapping_eligible_targets",
            "require_resolved_mapping_eligible_parent",
            "require_depth_one_family_subtree",
            "source_object_owned_by_at_most_one_root",
            "root_occurrence_policy",
            "distinct_roots_evaluated_independently",
            "zero_accepted_roots_allowed",
            "table_title_used_for_routing",
            "equation_used_for_target_selection",
        },
        "producer native TM routing",
    )
    completion = _require_policy_fields(
        payload.get("local_completion"),
        {
            "require_quantitative_context",
            "require_every_context_row_accounted",
            "require_region_grid_rows_only",
            "require_exactly_one_unlabeled_terminal_row",
            "require_terminal_after_all_anchors",
            "require_resolved_compatible_dimensions",
            "require_exactly_one_observation_per_row_dimension",
            "accepted_observation_statuses",
            "unresolved_or_invalid_positions_block",
            "row_local_scalars_block",
            "attached_unassigned_or_detached_evidence_blocks",
            "cell_free_after_terminal_inter_table_context_blocks",
            "following_heading_used_for_routing",
            "full_document_completion_implied",
            "equation_tolerance_source_units",
        },
        "producer native TM local completion",
    )
    coverage = _require_policy_fields(
        payload.get("coverage"),
        {
            "statement_type",
            "schema_item_count",
            "completion_rule",
            "terminal_outcomes",
            "outside_bounded_subtree_outcome",
            "outside_bounded_subtree_reason",
            "absent_direct_child_outcome",
            "absent_direct_child_reason",
        },
        "producer native TM coverage",
    )
    isolation = _require_policy_fields(
        payload.get("role_isolation"),
        {
            "direct_runtime_input_kinds",
            "prior_answer_artifacts_allowed",
            "historical_values_allowed",
            "role_a_outputs_allowed",
            "human_review_outputs_allowed",
            "bank_identity_used_for_routing",
            "filename_identity_used_for_routing",
            "page_number_used_for_routing",
            "note_number_used_for_routing",
            "table_title_used_for_routing",
            "expected_source_counts_used_for_routing",
            "forbidden_path_fragments",
        },
        "producer native TM role isolation",
    )
    output = _require_policy_fields(
        payload.get("output"),
        {
            "format",
            "status",
            "canonical_json",
            "output_directory",
            "exclusive_no_overwrite",
            "rollback_after_failed_strict_replay",
            "absolute_project_paths_allowed",
            "exact_source_object_dispositions_required",
            "exact_tm_schema_dispositions_required",
            "strict_producer_commit_replay_required",
        },
        "producer native TM output",
    )
    for name in ("schema_registry", "schema_graph", "tm_context_policy", "coverage_registry"):
        _validate_policy_identity_shape(schema[name], f"producer {name}")
    for name in (
        "schema_source_config",
        "hierarchy_config",
        "hierarchy_registry",
        "tm_hierarchy_workbook",
    ):
        _validate_policy_identity_shape(aliases[name], f"producer {name}")
    audits = aliases.get("business_update_audits")
    if not isinstance(audits, list) or not audits:
        raise NativeTMCanonicalMappingError(
            "producer typed alias business-update authority is invalid"
        )
    for audit in audits:
        _validate_policy_identity_shape(audit, "producer typed alias business-update audit")
    if (
        payload.get("version") != 1
        or payload.get("policy") != _POLICY_NAME
        or payload.get("claim_boundary") != _CLAIM_BOUNDARY
        or payload.get("require_clean_git") is not True
    ):
        raise NativeTMCanonicalMappingError("producer native TM canonical policy identity drifted")
    if (
        accepted.get("format_version") != _INPUT_FORMAT
        or accepted.get("policy") != _INPUT_POLICY
        or accepted.get("claim_boundary") != _INPUT_CLAIM
        or accepted.get("status") != _INPUT_STATUS
        or accepted.get("required_dataset_role") != _DATASET_ROLE
        or accepted.get("trusted_sha256_required") is not True
        or accepted.get("strict_producer_commit_replay_required") is not True
        or accepted.get("exact_source_accounting_required") is not True
        or accepted.get("required_collections")
        != [
            "page_inventory",
            "contexts",
            "rows",
            "dimensions",
            "observations",
            "source_evidence",
            "source_references",
            "source_dispositions",
        ]
        or not isinstance(schema, dict)
        or schema.get("statement_type") != _STATEMENT_TYPE
        or schema.get("item_count") != 1713
        or schema.get("order_authority") != "WORKBOOK_DISPLAY_ORDER"
        or not isinstance(aliases, dict)
        or aliases.get("accepted_authority_types") != list(_ACCEPTED_ALIAS_TYPES)
        or aliases.get("untyped_structural_aliases_mapping_eligible") is not False
        or aliases.get("historical_aliases_allowed") is not False
        or aliases.get("fuzzy_matching_allowed") is not False
        or aliases.get("strip_structural_enumerators") is not False
        or aliases.get("accounting_abbreviation_expansion_allowed") is not False
        or not isinstance(routing, dict)
        or routing.get("statement_type") != _STATEMENT_TYPE
        or routing.get("normalization") != "RETRIEVAL_KEY_EXACT"
        or routing.get("candidate_authorities")
        != [
            "CANONICAL_RETRIEVAL_KEY_EXACT",
            "ACCEPTED_TYPED_ALIAS_RETRIEVAL_KEY_EXACT",
        ]
        or routing.get("global_candidate_uniqueness_required") is not True
        or isinstance(routing.get("minimum_distinct_direct_child_anchors"), bool)
        or not isinstance(routing.get("minimum_distinct_direct_child_anchors"), int)
        or routing["minimum_distinct_direct_child_anchors"] < 3
        or routing.get("require_distinct_target_per_anchor") is not True
        or routing.get("require_unanimous_direct_parent") is not True
        or routing.get("require_parent_equals_note_family_root") is not True
        or routing.get("require_resolved_mapping_eligible_targets") is not True
        or routing.get("require_resolved_mapping_eligible_parent") is not True
        or routing.get("require_depth_one_family_subtree") is not True
        or routing.get("source_object_owned_by_at_most_one_root") is not True
        or routing.get("distinct_roots_evaluated_independently") is not True
        or routing.get("zero_accepted_roots_allowed") is not True
        or routing.get("root_occurrence_policy") != "UNIQUE_SOURCE_CONTEXT_PER_INFERRED_ROOT"
        or routing.get("table_title_used_for_routing") is not False
        or routing.get("equation_used_for_target_selection") is not False
        or not isinstance(completion, dict)
        or any(
            completion.get(key) is not True
            for key in (
                "require_quantitative_context",
                "require_every_context_row_accounted",
                "require_region_grid_rows_only",
                "require_exactly_one_unlabeled_terminal_row",
                "require_terminal_after_all_anchors",
                "require_resolved_compatible_dimensions",
                "require_exactly_one_observation_per_row_dimension",
                "unresolved_or_invalid_positions_block",
                "row_local_scalars_block",
                "attached_unassigned_or_detached_evidence_blocks",
            )
        )
        or completion.get("accepted_observation_statuses") != ["OBSERVED_VALUE", "OBSERVED_ZERO"]
        or completion.get("cell_free_after_terminal_inter_table_context_blocks") is not False
        or completion.get("following_heading_used_for_routing") is not False
        or completion.get("full_document_completion_implied") is not False
        or completion.get("equation_tolerance_source_units") != 0
        or not isinstance(coverage, dict)
        or coverage.get("statement_type") != _STATEMENT_TYPE
        or coverage.get("schema_item_count") != 1713
        or coverage.get("completion_rule")
        != "EXACTLY_ONE_TERMINAL_OUTCOME_PER_SCHEMA_ID_PER_DOCUMENT"
        or coverage.get("terminal_outcomes") != list(_TERMINAL_OUTCOMES)
        or coverage.get("outside_bounded_subtree_outcome") != "UNRESOLVED"
        or coverage.get("outside_bounded_subtree_reason")
        != "UNASSESSED_OUTSIDE_BOUNDED_TABLE_SUBTREE"
        or coverage.get("absent_direct_child_outcome") != "NOT_OBSERVED"
        or coverage.get("absent_direct_child_reason")
        != "ABSENT_FROM_LOCALLY_COMPLETE_BOUNDED_TABLE_SUBTREE"
        or not isinstance(isolation, dict)
        or isolation.get("direct_runtime_input_kinds")
        != [
            "NATIVE_TM_OBSERVATIONS_ARTIFACT",
            "THIS_POLICY",
            "UNIVERSAL_SCHEMA_REGISTRY",
            "UNIVERSAL_SCHEMA_GRAPH",
            "TM_CONTEXT_POLICY",
            "SCHEMA_COVERAGE_REGISTRY",
            "SCHEMA_SOURCE_CONFIG",
            "HIERARCHY_CONFIG",
            "HIERARCHY_REGISTRY",
            "TM_HIERARCHY_WORKBOOK",
            "SCHEMA_BUSINESS_UPDATE_AUDIT",
        ]
        or any(
            isolation.get(key) is not False
            for key in (
                "prior_answer_artifacts_allowed",
                "historical_values_allowed",
                "role_a_outputs_allowed",
                "human_review_outputs_allowed",
                "bank_identity_used_for_routing",
                "filename_identity_used_for_routing",
                "page_number_used_for_routing",
                "note_number_used_for_routing",
                "table_title_used_for_routing",
                "expected_source_counts_used_for_routing",
            )
        )
        or isolation.get("forbidden_path_fragments") != list(_FORBIDDEN_PATH_FRAGMENTS)
        or not isinstance(output, dict)
        or output.get("format") != _OUTPUT_FORMAT
        or output.get("status") != _OUTPUT_STATUS
        or output.get("output_directory") != _OUTPUT_DIRECTORY
        or output.get("canonical_json") is not True
        or output.get("exclusive_no_overwrite") is not True
        or output.get("rollback_after_failed_strict_replay") is not True
        or output.get("absolute_project_paths_allowed") is not False
        or output.get("exact_source_object_dispositions_required") is not True
        or output.get("exact_tm_schema_dispositions_required") is not True
        or output.get("strict_producer_commit_replay_required") is not True
    ):
        raise NativeTMCanonicalMappingError("producer native TM canonical policy was weakened")
    authority_paths = [
        _canonical_relative_path(relative, f"producer {kind} authority path")
        for kind, relative, _digest in _authority_specs(payload)
    ]
    if len(authority_paths) != len(set(authority_paths)):
        raise NativeTMCanonicalMappingError("producer authority path is repeated")
    _validate_paths_against_fragments(
        authority_paths,
        tuple(str(item).casefold() for item in isolation["forbidden_path_fragments"]),
        "producer authority",
    )
    return copy.deepcopy(payload)


def _validate_snapshot_envelope(
    snapshots: Any,
    *,
    producer_policy_bytes: bytes,
    producer_policy: Mapping[str, Any],
) -> None:
    if not isinstance(snapshots, dict) or set(snapshots) != {
        "policy",
        "tm_schema",
        "tm_context",
        "accepted_typed_aliases",
    }:
        raise NativeTMCanonicalMappingError("native TM canonical producer snapshots drifted")
    expected_policy = {
        "path": POLICY_RELATIVE_PATH.as_posix(),
        "sha256": sha256_bytes(producer_policy_bytes),
        "size_bytes": len(producer_policy_bytes),
        "payload_sha256": _record_sha256(producer_policy),
        "payload": copy.deepcopy(dict(producer_policy)),
    }
    if snapshots.get("policy") != expected_policy:
        raise NativeTMCanonicalMappingError("native TM canonical policy snapshot drifted")
    schema = snapshots.get("tm_schema")
    contexts = snapshots.get("tm_context")
    aliases = snapshots.get("accepted_typed_aliases")
    if (
        not isinstance(schema, dict)
        or set(schema) != {"record_count", "payload_sha256", "records"}
        or not isinstance(schema.get("records"), list)
        or schema.get("record_count") != len(schema["records"])
        or schema.get("payload_sha256") != _record_sha256(schema["records"])
        or not isinstance(contexts, dict)
        or set(contexts) != {"record_count", "payload_sha256", "projection_sha256", "records"}
        or not isinstance(contexts.get("records"), list)
        or contexts.get("record_count") != len(contexts["records"])
        or contexts.get("payload_sha256") != _record_sha256(contexts["records"])
        or contexts.get("projection_sha256") != _stable_records_sha256(contexts["records"])
        or not isinstance(aliases, dict)
        or set(aliases) != {"record_count", "payload_sha256", "projection_sha256", "records"}
        or not isinstance(aliases.get("records"), list)
        or aliases.get("record_count") != len(aliases["records"])
        or aliases.get("payload_sha256") != _record_sha256(aliases["records"])
        or aliases.get("projection_sha256")
        != stable_records_hash(
            json.dumps(record, ensure_ascii=False, sort_keys=True) for record in aliases["records"]
        )
        or schema.get("record_count") != producer_policy["coverage"]["schema_item_count"]
        or contexts.get("record_count") != schema.get("record_count")
    ):
        raise NativeTMCanonicalMappingError("native TM canonical authority snapshots drifted")


def _validate_committed_implementation(
    project_root: Path,
    code: Any,
    manifest: Sequence[str],
    label: str,
) -> tuple[str, list[dict[str, Any]]]:
    if (
        not isinstance(code, dict)
        or set(code) != {"commit", "dirty", "implementation"}
        or code.get("dirty") is not False
        or not isinstance(code.get("commit"), str)
        or _GIT_COMMIT.fullmatch(code["commit"]) is None
        or not isinstance(code.get("implementation"), list)
        or [record.get("path") for record in code["implementation"] if isinstance(record, dict)]
        != list(manifest)
    ):
        raise NativeTMCanonicalMappingError(f"{label} producer identity is invalid")
    expected = [
        _file_identity_at_commit(project_root, code["commit"], relative) for relative in manifest
    ]
    if code["implementation"] != expected:
        raise NativeTMCanonicalMappingError(
            f"{label} implementation is not bound to its producer commit"
        )
    return code["commit"], copy.deepcopy(code["implementation"])


def _policy_snapshot(
    *, path: str, policy_bytes: bytes, policy: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "path": path,
        "sha256": sha256_bytes(policy_bytes),
        "size_bytes": len(policy_bytes),
        "payload_sha256": _record_sha256(policy),
        "payload": copy.deepcopy(dict(policy)),
    }


def _validate_observation_replay_policy_minimum(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise NativeTMCanonicalMappingError("observation producer policy is invalid")
    _reject_policy_selector_keys(payload, "observation producer policy")
    _require_policy_fields(
        payload,
        {
            "version",
            "policy",
            "claim_boundary",
            "require_clean_git",
            "accepted_native_tm_document",
            "flattening",
            "report_scope",
            "role_isolation",
            "output",
        },
        "observation producer policy",
    )
    accepted = _require_policy_fields(
        payload.get("accepted_native_tm_document"),
        {
            "format_version",
            "policy",
            "claim_boundary",
            "accepted_statuses",
            "required_dataset_role",
            "trusted_sha256_required",
            "strict_producer_commit_replay_required",
        },
        "observation producer accepted native document",
    )
    flattening = _require_policy_fields(
        payload.get("flattening"),
        {
            "grains",
            "preserve_every_region",
            "preserve_every_page",
            "preserve_page_classification_and_visible_word_inventory",
            "outside_quantitative_tm_disposition",
            "preserve_every_region_row",
            "preserve_outside_financial_span_rows",
            "preserve_row_local_scalars",
            "preserve_every_grid_slot",
            "preserve_unresolved_empty_slots",
            "preserve_header_components_in_source_geometry_order",
            "preserve_header_binding_conflicts",
            "preserve_inter_table_contexts",
            "preserve_unassigned_page_runs",
            "preserve_excluded_spans",
            "preserve_detached_margin_runs",
            "preserve_region_unassigned_runs",
            "preserve_unit_group_diagnostics",
            "require_exactly_one_source_disposition",
            "row_dependent_bindings_materialized",
            "unresolved_bindings_coerced",
        },
        "observation producer flattening",
    )
    report_scope = _require_policy_fields(
        payload.get("report_scope"),
        {
            "authority",
            "normalization",
            "consolidated_retrieval_lexemes",
            "separate_retrieval_lexemes",
            "require_every_header_classified",
            "require_unanimous_non_conflicting_headers",
            "unresolved_scope",
        },
        "observation producer report scope",
    )
    isolation = _require_policy_fields(
        payload.get("role_isolation"),
        {
            "direct_runtime_input_allowlist",
            "prior_answer_artifacts_allowed",
            "historical_values_allowed",
            "role_a_outputs_allowed",
            "reference_outputs_allowed",
            "schema_inputs_allowed",
            "aliases_allowed",
            "mapping_inputs_allowed",
            "bank_identity_used_for_routing",
            "filename_identity_used_for_routing",
            "page_number_rules_used_for_routing",
            "note_number_rules_used_for_routing",
            "expected_count_rules_used_for_routing",
            "forbidden_path_fragments",
        },
        "observation producer role isolation",
    )
    output = _require_policy_fields(
        payload.get("output"),
        {
            "format",
            "status",
            "canonical_json",
            "exclusive_no_overwrite",
            "rollback_after_failed_strict_replay",
            "absolute_project_paths_allowed",
            "output_directory",
            "source_object_accounting_required",
            "full_document_context_completion_required",
        },
        "observation producer output",
    )
    if (
        payload.get("version") != 1
        or payload.get("policy") != _INPUT_POLICY
        or payload.get("claim_boundary") != _INPUT_CLAIM
        or payload.get("require_clean_git") is not True
        or not isinstance(accepted, dict)
        or accepted.get("format_version") != _NATIVE_DOCUMENT_FORMAT
        or accepted.get("policy") != _NATIVE_DOCUMENT_POLICY
        or accepted.get("claim_boundary") != _NATIVE_DOCUMENT_CLAIM
        or accepted.get("accepted_statuses") != list(_NATIVE_DOCUMENT_STATUSES)
        or accepted.get("required_dataset_role") != _DATASET_ROLE
        or accepted.get("trusted_sha256_required") is not True
        or accepted.get("strict_producer_commit_replay_required") is not True
        or flattening
        != {
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
        }
        or report_scope
        != {
            "authority": "SOURCE_VISIBLE_TM_HEADER_RUNS_ONLY",
            "normalization": "RETRIEVAL_KEY",
            "consolidated_retrieval_lexemes": ["hop nhat"],
            "separate_retrieval_lexemes": ["rieng", "rieng le"],
            "require_every_header_classified": True,
            "require_unanimous_non_conflicting_headers": True,
            "unresolved_scope": "UNKNOWN",
        }
        or isolation.get("direct_runtime_input_allowlist")
        != ["NATIVE_TM_DOCUMENT_ARTIFACT", "THIS_POLICY"]
        or any(
            isolation.get(key) is not False
            for key in (
                "prior_answer_artifacts_allowed",
                "historical_values_allowed",
                "role_a_outputs_allowed",
                "reference_outputs_allowed",
                "schema_inputs_allowed",
                "aliases_allowed",
                "mapping_inputs_allowed",
                "bank_identity_used_for_routing",
                "filename_identity_used_for_routing",
                "page_number_rules_used_for_routing",
                "note_number_rules_used_for_routing",
                "expected_count_rules_used_for_routing",
            )
        )
        or isolation.get("forbidden_path_fragments") != list(_OBSERVATION_FORBIDDEN_PATH_FRAGMENTS)
        or not isinstance(output, dict)
        or output.get("format") != _INPUT_FORMAT
        or output.get("status") != _INPUT_STATUS
        or output.get("canonical_json") is not True
        or output.get("exclusive_no_overwrite") is not True
        or output.get("rollback_after_failed_strict_replay") is not True
        or output.get("absolute_project_paths_allowed") is not False
        or output.get("output_directory") != _OUTPUT_DIRECTORY
        or output.get("source_object_accounting_required") is not True
        or output.get("full_document_context_completion_required") is not False
    ):
        raise NativeTMCanonicalMappingError("observation producer V1 policy was weakened")
    return copy.deepcopy(payload)


def _preflight_observation_replay_lineage(
    *,
    project_root: Path,
    observation_payload: Mapping[str, Any],
    observations_relative: str,
) -> dict[str, Any]:
    source = observation_payload.get("source")
    run_id = observation_payload.get("run_id")
    if (
        observation_payload.get("format_version") != _INPUT_FORMAT
        or observation_payload.get("policy") != _INPUT_POLICY
        or observation_payload.get("claim_boundary") != _INPUT_CLAIM
        or observation_payload.get("status") != _INPUT_STATUS
        or not isinstance(run_id, str)
        or _SAFE_RUN_ID.fullmatch(run_id) is None
        or not isinstance(source, dict)
        or source.get("dataset_role") != _DATASET_ROLE
    ):
        raise NativeTMCanonicalMappingError("native TM observations V1 envelope is invalid")
    producer_commit, implementation = _validate_committed_implementation(
        project_root,
        observation_payload.get("code"),
        _OBSERVATION_IMPLEMENTATION_PATHS,
        "native TM observations",
    )
    policy_bytes = _git_file_bytes(project_root, producer_commit, _OBSERVATION_POLICY_PATH)
    producer_policy = _validate_observation_replay_policy_minimum(
        _yaml_bytes(policy_bytes, "observation producer policy")
    )
    if observation_payload.get("producer_snapshots") != {
        "policy": _policy_snapshot(
            path=_OBSERVATION_POLICY_PATH,
            policy_bytes=policy_bytes,
            policy=producer_policy,
        )
    }:
        raise NativeTMCanonicalMappingError(
            "native TM observations producer policy snapshot drifted"
        )
    native_identity = observation_payload.get("native_tm_document")
    if (
        not isinstance(native_identity, dict)
        or set(native_identity)
        != {
            "path",
            "sha256",
            "size_bytes",
            "format_version",
            "policy",
            "claim_boundary",
            "status",
            "run_id",
            "producer_git_commit",
        }
        or native_identity.get("format_version") != _NATIVE_DOCUMENT_FORMAT
        or native_identity.get("policy") != _NATIVE_DOCUMENT_POLICY
        or native_identity.get("claim_boundary") != _NATIVE_DOCUMENT_CLAIM
        or native_identity.get("status") not in _NATIVE_DOCUMENT_STATUSES
        or not isinstance(native_identity.get("run_id"), str)
        or _SAFE_RUN_ID.fullmatch(native_identity["run_id"]) is None
        or not isinstance(native_identity.get("producer_git_commit"), str)
        or _GIT_COMMIT.fullmatch(native_identity["producer_git_commit"]) is None
        or not isinstance(native_identity.get("sha256"), str)
        or _SHA256.fullmatch(native_identity["sha256"]) is None
        or isinstance(native_identity.get("size_bytes"), bool)
        or not isinstance(native_identity.get("size_bytes"), int)
        or native_identity["size_bytes"] < 0
    ):
        raise NativeTMCanonicalMappingError("native TM observations document receipt is invalid")
    native_relative = _canonical_relative_path(
        native_identity.get("path"), "native TM document artifact path"
    )
    _validate_paths_against_fragments(
        [observations_relative, native_relative],
        _OBSERVATION_FORBIDDEN_PATH_FRAGMENTS,
        "observation producer",
    )
    if not observations_relative.startswith(
        f"{_OUTPUT_DIRECTORY}/"
    ) or not native_relative.startswith(f"{_OUTPUT_DIRECTORY}/"):
        raise NativeTMCanonicalMappingError(
            "native TM observation lineage must stay under output/development"
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
                _OBSERVATION_POLICY_PATH,
                kind="THIS_POLICY",
            ),
        ],
        key=lambda record: (record["kind"], record["path"]),
    )
    inputs = observation_payload.get("inputs")
    if (
        not isinstance(inputs, dict)
        or set(inputs)
        != {
            "direct_runtime_input_ledger",
            "direct_runtime_input_ledger_sha256",
            "inherited_upstream_replay_provenance",
        }
        or inputs.get("direct_runtime_input_ledger") != expected_ledger
        or inputs.get("direct_runtime_input_ledger_sha256")
        != _runtime_ledger_sha256(expected_ledger)
    ):
        raise NativeTMCanonicalMappingError(
            "native TM observations runtime receipt lineage drifted"
        )
    return {
        "producer_commit": producer_commit,
        "implementation": implementation,
        "producer_policy": producer_policy,
        "native_identity": copy.deepcopy(native_identity),
        "native_relative": native_relative,
    }


def _validate_native_replay_policy_minimum(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise NativeTMCanonicalMappingError("native document producer policy is invalid")
    _reject_policy_selector_keys(payload, "native document producer policy")
    _require_policy_fields(
        payload,
        {
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
        },
        "native document producer policy",
    )
    accepted = _require_policy_fields(
        payload.get("accepted_statement_discovery"),
        {
            "format_version",
            "policy",
            "claim_boundary",
            "status",
            "required_dataset_role",
            "producer_policy_path",
            "runtime_input_policy",
            "require_exact_runtime_read_ledger",
            "runtime_input_kind_counts",
            "trusted_sha256_required",
            "notes_boundary_authority",
            "require_full_pdf_page_denominator",
            "require_source_identity_equality",
        },
        "native document accepted statement discovery",
    )
    configuration = _require_policy_fields(
        payload.get("configuration"),
        {"native_tm_region_policy", "geometry_config", "native_text_quality_config"},
        "native document configuration",
    )
    classification = _require_policy_fields(
        payload.get("classification"),
        {
            "classes",
            "pre_notes_boundary",
            "quantitative_requires_discovered_region",
            "region_without_tm_authority",
            "unmatched_post_boundary",
            "top_band_height_ratio",
            "tm_header_retrieval_phrases",
            "continuation_retrieval_phrases",
            "continuation_requires_immediately_preceding_tm_page",
            "generic_note_heading_retrieval_regex",
            "generic_note_heading_minimum_alpha_tokens",
        },
        "native document classification",
    )
    completeness = _require_policy_fields(
        payload.get("completeness"),
        {
            "page_denominator",
            "every_page_requires_explicit_classification",
            "every_usable_page_requires_region_assessment",
            "unresolved_inter_table_ownership_blocks_completion",
            "table_on_unassessed_page_blocks_completion",
            "full_document_complete_rule",
            "partial_artifact_publication_allowed",
        },
        "native document completeness",
    )
    isolation = _require_policy_fields(
        payload.get("role_isolation"),
        {
            "runtime_input_allowlist",
            "prior_answer_artifacts_allowed",
            "historical_values_allowed",
            "role_a_outputs_allowed",
            "reference_outputs_allowed",
            "schema_inputs_allowed",
            "bank_identity_used_for_routing",
            "filename_identity_used_for_routing",
            "page_number_rules_used_for_routing",
            "note_number_rules_used_for_routing",
            "expected_count_rules_used_for_routing",
            "forbidden_path_fragments",
        },
        "native document role isolation",
    )
    output = _require_policy_fields(
        payload.get("output"),
        {
            "format",
            "complete_status",
            "partial_status",
            "canonical_json",
            "exclusive_no_overwrite",
            "rollback_after_failed_strict_replay",
            "absolute_project_paths_allowed",
            "output_directory",
            "preserve_all_native_region_evidence",
        },
        "native document output",
    )
    if (
        payload.get("version") != 1
        or payload.get("policy") != _NATIVE_DOCUMENT_POLICY
        or payload.get("claim_boundary") != _NATIVE_DOCUMENT_CLAIM
        or payload.get("source_registry") != "data/registered/source_registry.jsonl"
        or payload.get("dataset_role_registry") != "data/registered/dataset_roles.jsonl"
        or payload.get("required_dataset_role") != _DATASET_ROLE
        or payload.get("require_clean_git") is not True
        or not isinstance(accepted, dict)
        or accepted.get("format_version") != _DISCOVERY_FORMAT
        or accepted.get("policy") != _DISCOVERY_POLICY
        or accepted.get("claim_boundary") != _DISCOVERY_CLAIM
        or accepted.get("status") != _DISCOVERY_STATUS
        or accepted.get("required_dataset_role") != _DATASET_ROLE
        or accepted.get("producer_policy_path")
        != "config/document_phase/native-statement-discovery-v1.yaml"
        or accepted.get("runtime_input_policy") != "EXACT_DECLARED_PROJECT_INPUT_LEDGER"
        or accepted.get("require_exact_runtime_read_ledger") is not True
        or accepted.get("runtime_input_kind_counts")
        != {
            "DATASET_ROLE_REGISTRY": 1,
            "NATIVE_TEXT_QUALITY_CONFIG": 1,
            "SOURCE_PDF": 1,
            "SOURCE_REGISTRY": 1,
            "STATEMENT_DISCOVERY_CONFIG": 4,
            "THIS_POLICY": 1,
        }
        or accepted.get("trusted_sha256_required") is not True
        or accepted.get("notes_boundary_authority") != "ACCEPTED_DISCOVERY_BLOCK_NOTES_BOUNDARY"
        or accepted.get("require_full_pdf_page_denominator") is not True
        or accepted.get("require_source_identity_equality") is not True
        or any(
            not isinstance(configuration[key], dict)
            or set(configuration[key]) != {"path", "sha256"}
            or not isinstance(configuration[key]["path"], str)
            or not isinstance(configuration[key]["sha256"], str)
            or _SHA256.fullmatch(configuration[key]["sha256"]) is None
            for key in configuration
        )
        or classification
        != {
            "classes": [
                "QUANTITATIVE_TM",
                "QUALITATIVE_TM_CONTEXT",
                "NON_TM",
                "UNASSESSED",
            ],
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
        }
        or completeness
        != {
            "page_denominator": "ALL_PDF_PAGES",
            "every_page_requires_explicit_classification": True,
            "every_usable_page_requires_region_assessment": True,
            "unresolved_inter_table_ownership_blocks_completion": True,
            "table_on_unassessed_page_blocks_completion": True,
            "full_document_complete_rule": (
                "EVERY_PAGE_CLASSIFIED_AND_ALL_TABLE_OWNERSHIP_BOUNDED"
            ),
            "partial_artifact_publication_allowed": True,
        }
        or isolation.get("runtime_input_allowlist")
        != [
            "SOURCE_PDF",
            "SOURCE_REGISTRY",
            "DATASET_ROLE_REGISTRY",
            "ACCEPTED_STATEMENT_DISCOVERY",
            "THIS_POLICY",
            "NATIVE_TM_REGION_POLICY",
            "GEOMETRY_CONFIG",
            "NATIVE_TEXT_QUALITY_CONFIG",
        ]
        or isolation.get("forbidden_path_fragments")
        != list(_NATIVE_DOCUMENT_FORBIDDEN_PATH_FRAGMENTS)
        or any(
            isolation.get(key) is not False
            for key in (
                "prior_answer_artifacts_allowed",
                "historical_values_allowed",
                "role_a_outputs_allowed",
                "reference_outputs_allowed",
                "schema_inputs_allowed",
                "bank_identity_used_for_routing",
                "filename_identity_used_for_routing",
                "page_number_rules_used_for_routing",
                "note_number_rules_used_for_routing",
                "expected_count_rules_used_for_routing",
            )
        )
        or output.get("format") != _NATIVE_DOCUMENT_FORMAT
        or output.get("complete_status") != _NATIVE_DOCUMENT_STATUSES[0]
        or output.get("partial_status") != _NATIVE_DOCUMENT_STATUSES[1]
        or output.get("canonical_json") is not True
        or output.get("exclusive_no_overwrite") is not True
        or output.get("rollback_after_failed_strict_replay") is not True
        or output.get("absolute_project_paths_allowed") is not False
        or output.get("output_directory") != _OUTPUT_DIRECTORY
        or output.get("preserve_all_native_region_evidence") is not True
    ):
        raise NativeTMCanonicalMappingError("native document producer V1 policy was weakened")
    return copy.deepcopy(payload)


def _nonnegative_integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise NativeTMCanonicalMappingError(f"{label} must be a nonnegative integer")
    return value


def _preflight_native_replay_lineage(
    *,
    project_root: Path,
    observation_payload: Mapping[str, Any],
    observation_preflight: Mapping[str, Any],
    native_payload: Mapping[str, Any],
    native_bytes: bytes,
) -> tuple[dict[str, Any], dict[str, Any]]:
    native_identity = observation_preflight["native_identity"]
    if (
        native_payload.get("format_version") != _NATIVE_DOCUMENT_FORMAT
        or native_payload.get("policy") != _NATIVE_DOCUMENT_POLICY
        or native_payload.get("claim_boundary") != _NATIVE_DOCUMENT_CLAIM
        or native_payload.get("status") not in _NATIVE_DOCUMENT_STATUSES
        or not isinstance(native_payload.get("run_id"), str)
        or _SAFE_RUN_ID.fullmatch(native_payload["run_id"]) is None
    ):
        raise NativeTMCanonicalMappingError("native TM document V1 envelope is invalid")
    producer_commit, _implementation = _validate_committed_implementation(
        project_root,
        native_payload.get("code"),
        _NATIVE_DOCUMENT_IMPLEMENTATION_PATHS,
        "native TM document",
    )
    expected_native_identity = {
        "path": observation_preflight["native_relative"],
        "sha256": sha256_bytes(native_bytes),
        "size_bytes": len(native_bytes),
        "format_version": native_payload["format_version"],
        "policy": native_payload["policy"],
        "claim_boundary": native_payload["claim_boundary"],
        "status": native_payload["status"],
        "run_id": native_payload["run_id"],
        "producer_git_commit": producer_commit,
    }
    if native_identity != expected_native_identity:
        raise NativeTMCanonicalMappingError(
            "native TM observations document identity differs from held bytes"
        )
    source = _as_object(native_payload.get("source"), "native TM source provenance")
    if observation_payload.get("source") != source:
        raise NativeTMCanonicalMappingError(
            "native TM observations source differs from held document"
        )
    policy_bytes = _git_file_bytes(project_root, producer_commit, _NATIVE_DOCUMENT_POLICY_PATH)
    producer_policy = _validate_native_replay_policy_minimum(
        _yaml_bytes(policy_bytes, "native document producer policy")
    )
    snapshots = native_payload.get("producer_snapshots")
    if (
        not isinstance(snapshots, dict)
        or set(snapshots) != {"configurations", "policy"}
        or snapshots.get("policy")
        != _policy_snapshot(
            path=_NATIVE_DOCUMENT_POLICY_PATH,
            policy_bytes=policy_bytes,
            policy=producer_policy,
        )
    ):
        raise NativeTMCanonicalMappingError("native TM document producer policy snapshot drifted")
    source_relative = _canonical_relative_path(source.get("relative_path"), "native TM source path")
    source_sha256 = _as_string(source.get("sha256"), "native TM source SHA-256")
    source_size = _nonnegative_integer(source.get("size_bytes"), "native TM source size")
    if (
        _SHA256.fullmatch(source_sha256) is None
        or source.get("document_id") != f"sha256:{source_sha256}"
        or source.get("dataset_role") != _DATASET_ROLE
        or source.get("registry_state") != "REGISTERED"
        or source.get("hash_verified_stable") is not True
        or source.get("immutable_role_assignment") is not True
    ):
        raise NativeTMCanonicalMappingError("native TM source registration receipt is invalid")
    discovery = _as_object(
        native_payload.get("statement_discovery"), "native TM discovery provenance"
    )
    discovery_relative = _canonical_relative_path(discovery.get("path"), "native TM discovery path")
    discovery_sha256 = _as_string(discovery.get("sha256"), "native TM discovery SHA-256")
    discovery_size = _nonnegative_integer(discovery.get("size_bytes"), "native TM discovery size")
    if (
        _SHA256.fullmatch(discovery_sha256) is None
        or discovery.get("format_version") != _DISCOVERY_FORMAT
        or discovery.get("policy") != _DISCOVERY_POLICY
        or discovery.get("claim_boundary") != _DISCOVERY_CLAIM
        or discovery.get("status") != _DISCOVERY_STATUS
        or not isinstance(discovery.get("producer_git_commit"), str)
        or _GIT_COMMIT.fullmatch(discovery["producer_git_commit"]) is None
    ):
        raise NativeTMCanonicalMappingError("native TM discovery receipt is invalid")
    _validate_paths_against_fragments(
        [observation_preflight["native_relative"], source_relative, discovery_relative],
        _NATIVE_DOCUMENT_FORBIDDEN_PATH_FRAGMENTS,
        "native document producer",
    )
    if not source_relative.casefold().endswith(".pdf") or not discovery_relative.startswith(
        f"{_OUTPUT_DIRECTORY}/"
    ):
        raise NativeTMCanonicalMappingError("native TM transitive path role is invalid")
    source_registry_path = producer_policy["source_registry"]
    role_registry_path = producer_policy["dataset_role_registry"]
    source_records = _jsonl_bytes(
        _git_file_bytes(project_root, producer_commit, source_registry_path),
        "native producer source registry",
    )
    role_records = _jsonl_bytes(
        _git_file_bytes(project_root, producer_commit, role_registry_path),
        "native producer role registry",
    )
    matching_sources = [
        record for record in source_records if record.get("relative_path") == source_relative
    ]
    matching_roles = [
        record for record in role_records if record.get("document_id") == source["document_id"]
    ]
    if len(matching_sources) != 1 or len(matching_roles) != 1:
        raise NativeTMCanonicalMappingError("native TM source has no unique producer registration")
    source_record = matching_sources[0]
    role_record = matching_roles[0]
    if (
        source_record.get("document_id") != source["document_id"]
        or source_record.get("sha256") != source_sha256
        or source_record.get("size_bytes") != source_size
        or source_record.get("kind") != "PDF"
        or source_record.get("state") != "REGISTERED"
        or source_record.get("hash_verified_stable") is not True
        or source.get("source_registry_record_sha256") != _record_sha256(source_record)
        or role_record.get("source_path") != source_relative
        or role_record.get("dataset_role") != _DATASET_ROLE
        or role_record.get("immutable") is not True
        or source.get("dataset_role_registry_record_sha256") != _record_sha256(role_record)
    ):
        raise NativeTMCanonicalMappingError(
            "native TM source differs from its producer registration"
        )
    expected_ledger = [
        {
            "kind": "ACCEPTED_STATEMENT_DISCOVERY",
            "path": discovery_relative,
            "sha256": discovery_sha256,
            "size_bytes": discovery_size,
        },
        _file_identity_at_commit(
            project_root,
            producer_commit,
            role_registry_path,
            kind="DATASET_ROLE_REGISTRY",
        ),
        {
            "kind": "SOURCE_PDF",
            "path": source_relative,
            "sha256": source_sha256,
            "size_bytes": source_size,
        },
        _file_identity_at_commit(
            project_root,
            producer_commit,
            source_registry_path,
            kind="SOURCE_REGISTRY",
        ),
        _file_identity_at_commit(
            project_root,
            producer_commit,
            _NATIVE_DOCUMENT_POLICY_PATH,
            kind="THIS_POLICY",
        ),
    ]
    for key, kind in (
        ("native_tm_region_policy", "NATIVE_TM_REGION_POLICY"),
        ("geometry_config", "GEOMETRY_CONFIG"),
        ("native_text_quality_config", "NATIVE_TEXT_QUALITY_CONFIG"),
    ):
        configured = producer_policy["configuration"][key]
        identity = _file_identity_at_commit(
            project_root, producer_commit, configured["path"], kind=kind
        )
        if identity["sha256"] != configured["sha256"]:
            raise NativeTMCanonicalMappingError("native TM producer configuration hash drifted")
        expected_ledger.append(identity)
    expected_ledger.sort(key=lambda record: (record["kind"], record["path"]))
    inputs = native_payload.get("inputs")
    if (
        not isinstance(inputs, dict)
        or set(inputs) != {"runtime_read_ledger", "runtime_read_ledger_sha256"}
        or inputs.get("runtime_read_ledger") != expected_ledger
        or inputs.get("runtime_read_ledger_sha256") != _runtime_ledger_sha256(expected_ledger)
    ):
        raise NativeTMCanonicalMappingError("native TM document runtime receipt lineage drifted")
    inherited = observation_payload["inputs"]["inherited_upstream_replay_provenance"]
    expected_inherited = {
        "inputs": copy.deepcopy(native_payload.get("inputs")),
        "inputs_sha256": _record_sha256(native_payload.get("inputs")),
        "implementation": copy.deepcopy(native_payload.get("code", {}).get("implementation")),
        "implementation_sha256": _record_sha256(
            native_payload.get("code", {}).get("implementation")
        ),
        "producer_snapshots": copy.deepcopy(native_payload.get("producer_snapshots")),
        "producer_snapshots_sha256": _record_sha256(native_payload.get("producer_snapshots")),
        "inventories": {
            "completeness": copy.deepcopy(native_payload.get("completeness")),
            "completeness_sha256": _record_sha256(native_payload.get("completeness")),
            "note_inventory": copy.deepcopy(native_payload.get("note_inventory")),
            "note_inventory_sha256": _record_sha256(native_payload.get("note_inventory")),
            "table_inventory": copy.deepcopy(native_payload.get("table_inventory")),
            "table_inventory_sha256": _record_sha256(native_payload.get("table_inventory")),
        },
    }
    if inherited != expected_inherited:
        raise NativeTMCanonicalMappingError(
            "native TM observations inherited document receipt drifted"
        )
    return copy.deepcopy(source), copy.deepcopy(discovery)


def _open_transitive_replay_guards(
    project_root: Path,
    observation_payload: Mapping[str, Any],
    observation_preflight: Mapping[str, Any],
) -> tuple[list[Any], list[tuple[str, bytes, str]]]:
    guards: list[Any] = []
    installs: list[tuple[str, bytes, str]] = []
    try:
        native_relative = str(observation_preflight["native_relative"])
        native_path, _ = _lexical_project_path(
            project_root, Path(native_relative), "native TM document artifact"
        )
        native_guard = _open_guard(
            project_root, native_path, native_relative, "native TM document artifact"
        )
        guards.append(native_guard)
        native_identity = observation_preflight["native_identity"]
        if (
            sha256_bytes(native_guard.payload) != native_identity["sha256"]
            or len(native_guard.payload) != native_identity["size_bytes"]
        ):
            raise NativeTMCanonicalMappingError("native TM document replay input drifted")
        try:
            native_payload = json.loads(native_guard.payload)
        except json.JSONDecodeError as exc:
            raise NativeTMCanonicalMappingError(
                "native TM document replay input is invalid"
            ) from exc
        if not isinstance(native_payload, dict) or native_guard.payload != _canonical_json_bytes(
            native_payload
        ):
            raise NativeTMCanonicalMappingError(
                "native TM document replay input is not canonical JSON"
            )
        source, discovery = _preflight_native_replay_lineage(
            project_root=project_root,
            observation_payload=observation_payload,
            observation_preflight=observation_preflight,
            native_payload=native_payload,
            native_bytes=bytes(native_guard.payload),
        )
        for relative, digest, size, label in (
            (
                source["relative_path"],
                source["sha256"],
                source["size_bytes"],
                "native TM source PDF",
            ),
            (
                discovery["path"],
                discovery["sha256"],
                discovery["size_bytes"],
                "native TM statement discovery",
            ),
        ):
            path, _ = _lexical_project_path(project_root, Path(relative), label)
            guard = _open_guard(project_root, path, relative, label)
            guards.append(guard)
            if sha256_bytes(guard.payload) != digest or len(guard.payload) != size:
                raise NativeTMCanonicalMappingError(f"{label} replay input drifted")
            installs.append((relative, bytes(guard.payload), label))
        installs.insert(
            0, (native_relative, bytes(native_guard.payload), "native TM document artifact")
        )
        return guards, installs
    except BaseException:
        for guard in reversed(guards):
            _close_guard(guard)
        raise


def _producer_commit_replay(
    *,
    project_root: Path,
    producer_commit: str,
    implementation: Sequence[Mapping[str, Any]],
    observations_relative: str,
    observations_bytes: bytes,
    observations_sha256: str,
    transitive_installs: Sequence[tuple[str, bytes, str]],
    run_id: str,
) -> bytes:
    temporary_root = Path(tempfile.mkdtemp(prefix="native-tm-canonical-replay-"))
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
            observations_relative,
            observations_bytes,
            "native TM observations artifact",
        )
        for relative, payload, label in transitive_installs:
            _install_replay_input(clone_root, relative, payload, label)
        status = _run_checked_process(
            ("git", "status", "--porcelain", "--untracked-files=all"),
            cwd=clone_root,
            environment=environment,
        )
        if status.strip():
            raise NativeTMCanonicalMappingError(
                "producer-commit replay repository is not clean after input restoration"
            )
        replay_tree = temporary_root / "isolated-source"
        for record in implementation:
            relative = str(record["path"])
            _write_new_file(
                replay_tree.joinpath(*PurePosixPath(relative).parts),
                _git_file_bytes(project_root, producer_commit, relative),
            )
        return _run_checked_process(
            (
                sys.executable,
                "-I",
                "-c",
                _PRODUCER_REPLAY_BOOTSTRAP,
                str(replay_tree),
                str(clone_root),
                observations_relative,
                observations_sha256,
                run_id,
            ),
            cwd=temporary_root,
            environment=environment,
        )
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)


def _load_registered_native_tm_canonical_mapping_held(
    guard: Any,
    *,
    project_root: Path,
    expected_sha256: str,
) -> dict[str, Any]:
    encoded = bytes(guard.payload)
    if sha256_bytes(encoded) != expected_sha256:
        raise NativeTMCanonicalMappingError(
            "native TM canonical artifact does not match trusted SHA-256"
        )
    try:
        payload = json.loads(encoded)
    except json.JSONDecodeError as exc:
        raise NativeTMCanonicalMappingError("native TM canonical artifact is invalid JSON") from exc
    if not isinstance(payload, dict) or encoded != _canonical_json_bytes(payload):
        raise NativeTMCanonicalMappingError("native TM canonical artifact is not canonical JSON")
    expected_keys = {
        "format_version",
        "policy",
        "claim_boundary",
        "status",
        "run_id",
        "source",
        "native_tm_observations",
        "schema",
        "code",
        "authority",
        "isolation",
        "non_decision_features",
        "inputs",
        "producer_snapshots",
        "routing_contract",
        "root_assessments",
        "accepted_subtrees",
        "source_accounting",
        "source_dispositions",
        "canonical_observations",
        "schema_dispositions",
        "equation_checks",
        "coverage",
        "completion",
    }
    if set(payload) != expected_keys or {
        "format_version": payload.get("format_version"),
        "policy": payload.get("policy"),
        "claim_boundary": payload.get("claim_boundary"),
        "status": payload.get("status"),
    } != {
        "format_version": _OUTPUT_FORMAT,
        "policy": _POLICY_NAME,
        "claim_boundary": _CLAIM_BOUNDARY,
        "status": _OUTPUT_STATUS,
    }:
        raise NativeTMCanonicalMappingError("native TM canonical artifact envelope drifted")
    run_id = payload.get("run_id")
    if not isinstance(run_id, str) or _SAFE_RUN_ID.fullmatch(run_id) is None:
        raise NativeTMCanonicalMappingError("native TM canonical replay run_id is invalid")
    producer_commit, implementation = _validate_replay_implementation(
        project_root, payload.get("code")
    )
    producer_policy_bytes = _git_file_bytes(
        project_root, producer_commit, POLICY_RELATIVE_PATH.as_posix()
    )
    producer_policy = _validate_replay_policy_minimum(
        _yaml_bytes(producer_policy_bytes, "producer native TM canonical policy")
    )
    _validate_snapshot_envelope(
        payload.get("producer_snapshots"),
        producer_policy_bytes=producer_policy_bytes,
        producer_policy=producer_policy,
    )
    native_identity = payload.get("native_tm_observations")
    if (
        not isinstance(native_identity, dict)
        or set(native_identity)
        != {
            "path",
            "sha256",
            "size_bytes",
            "format_version",
            "policy",
            "claim_boundary",
            "status",
            "run_id",
            "producer_git_commit",
        }
        or not isinstance(native_identity.get("sha256"), str)
        or _SHA256.fullmatch(native_identity["sha256"]) is None
        or isinstance(native_identity.get("size_bytes"), bool)
        or not isinstance(native_identity.get("size_bytes"), int)
    ):
        raise NativeTMCanonicalMappingError("native TM observations replay provenance is invalid")
    observations_relative = _canonical_relative_path(
        native_identity.get("path"), "native TM observations artifact path"
    )
    _validate_path_isolation([observations_relative])
    if not observations_relative.startswith(f"{_OUTPUT_DIRECTORY}/"):
        raise NativeTMCanonicalMappingError(
            "native TM observations replay input must stay under output/development"
        )
    observations_path, _ = _lexical_project_path(
        project_root, Path(observations_relative), "native TM observations artifact"
    )
    observations_guard = _open_guard(
        project_root,
        observations_path,
        observations_relative,
        "native TM observations artifact",
    )
    transitive_guards: list[Any] = []
    try:
        observations_bytes = bytes(observations_guard.payload)
        if (
            sha256_bytes(observations_bytes) != native_identity["sha256"]
            or len(observations_bytes) != native_identity["size_bytes"]
        ):
            raise NativeTMCanonicalMappingError("native TM observations replay input drifted")
        try:
            held_observations = json.loads(observations_bytes)
        except json.JSONDecodeError as exc:
            raise NativeTMCanonicalMappingError(
                "native TM observations replay input is invalid JSON"
            ) from exc
        if not isinstance(held_observations, dict) or observations_bytes != _canonical_json_bytes(
            held_observations
        ):
            raise NativeTMCanonicalMappingError(
                "native TM observations replay input is not canonical JSON"
            )
        observation_payload = held_observations
        observation_preflight = _preflight_observation_replay_lineage(
            project_root=project_root,
            observation_payload=observation_payload,
            observations_relative=observations_relative,
        )
        expected_native_identity = {
            "path": observations_relative,
            "sha256": native_identity["sha256"],
            "size_bytes": len(observations_bytes),
            "format_version": observation_payload["format_version"],
            "policy": observation_payload["policy"],
            "claim_boundary": observation_payload["claim_boundary"],
            "status": observation_payload["status"],
            "run_id": observation_payload["run_id"],
            "producer_git_commit": observation_preflight["producer_commit"],
        }
        if native_identity != expected_native_identity:
            raise NativeTMCanonicalMappingError(
                "native TM canonical upstream observation envelope drifted"
            )
        inputs = payload.get("inputs")
        if not isinstance(inputs, dict) or set(inputs) != {
            "direct_runtime_input_ledger",
            "direct_runtime_input_ledger_sha256",
            "inherited_upstream_replay_provenance",
        }:
            raise NativeTMCanonicalMappingError("native TM canonical input envelope drifted")
        ledger = inputs["direct_runtime_input_ledger"]
        if not isinstance(ledger, list):
            raise NativeTMCanonicalMappingError("native TM canonical runtime ledger is invalid")
        expected_ledger = [
            {
                "kind": "NATIVE_TM_OBSERVATIONS_ARTIFACT",
                "path": observations_relative,
                "sha256": native_identity["sha256"],
                "size_bytes": native_identity["size_bytes"],
            },
            _file_identity_at_commit(
                project_root,
                producer_commit,
                POLICY_RELATIVE_PATH.as_posix(),
                kind="THIS_POLICY",
            ),
        ]
        for kind, relative, digest in _authority_specs(producer_policy):
            record = _file_identity_at_commit(project_root, producer_commit, relative, kind=kind)
            if record["sha256"] != digest:
                raise NativeTMCanonicalMappingError(
                    "producer native TM canonical authority hash drifted"
                )
            expected_ledger.append(record)
        expected_ledger.sort(key=lambda record: (record["kind"], record["path"]))
        if ledger != expected_ledger or inputs[
            "direct_runtime_input_ledger_sha256"
        ] != _runtime_ledger_sha256(expected_ledger):
            raise NativeTMCanonicalMappingError("native TM canonical runtime ledger drifted")
        inherited = {
            "inputs": copy.deepcopy(observation_payload.get("inputs")),
            "inputs_sha256": _record_sha256(observation_payload.get("inputs")),
            "implementation": copy.deepcopy(
                observation_payload.get("code", {}).get("implementation")
            ),
            "implementation_sha256": _record_sha256(
                observation_payload.get("code", {}).get("implementation")
            ),
            "producer_snapshots": copy.deepcopy(observation_payload.get("producer_snapshots")),
            "producer_snapshots_sha256": _record_sha256(
                observation_payload.get("producer_snapshots")
            ),
            "source_accounting": copy.deepcopy(observation_payload.get("source_accounting")),
            "source_accounting_sha256": _record_sha256(
                observation_payload.get("source_accounting")
            ),
        }
        if inputs["inherited_upstream_replay_provenance"] != inherited:
            raise NativeTMCanonicalMappingError(
                "native TM canonical inherited observation provenance drifted"
            )
        transitive_guards, transitive_installs = _open_transitive_replay_guards(
            project_root, observation_payload, observation_preflight
        )
        replayed = _producer_commit_replay(
            project_root=project_root,
            producer_commit=producer_commit,
            implementation=implementation,
            observations_relative=observations_relative,
            observations_bytes=observations_bytes,
            observations_sha256=native_identity["sha256"],
            transitive_installs=transitive_installs,
            run_id=run_id,
        )
        if replayed != encoded:
            raise NativeTMCanonicalMappingError(
                "native TM canonical artifact differs from producer-commit deterministic replay"
            )
        for held_guard, label in [
            (observations_guard, "native TM observations replay input"),
            *((item, "native TM transitive replay input") for item in transitive_guards),
            (guard, "native TM canonical artifact"),
        ]:
            _revalidate_guard(held_guard, label)
        return copy.deepcopy(payload)
    finally:
        for held_guard in reversed(transitive_guards):
            _close_guard(held_guard)
        _close_guard(observations_guard)


def load_registered_native_tm_canonical_mapping(
    path: Path,
    *,
    project_root: Path,
    expected_sha256: str,
) -> dict[str, Any]:
    """Trusted-SHA load with fd-held producer-commit replay."""

    project_root = project_root.resolve()
    path, relative = _lexical_project_path(
        project_root, path, "registered native TM canonical artifact"
    )
    if not isinstance(expected_sha256, str) or _SHA256.fullmatch(expected_sha256) is None:
        raise NativeTMCanonicalMappingError("trusted native TM canonical SHA-256 is invalid")
    _validate_path_isolation([relative])
    if not relative.startswith(f"{_OUTPUT_DIRECTORY}/"):
        raise NativeTMCanonicalMappingError(
            "LOGIC_DEVELOPMENT native TM canonical artifact must stay under output/development"
        )
    guard = _open_guard(project_root, path, relative, "native TM canonical artifact")
    try:
        return _load_registered_native_tm_canonical_mapping_held(
            guard,
            project_root=project_root,
            expected_sha256=expected_sha256,
        )
    finally:
        _close_guard(guard)


def _rollback_publication(guard: Any, cause: BaseException) -> None:
    try:
        _native_document._rollback_publication(guard, cause)
    except _native_document.NativeTMDocumentArtifactError as exc:
        raise NativeTMCanonicalMappingError(str(exc)) from cause


def publish_registered_native_tm_canonical_mapping(
    project_root: Path,
    native_tm_observations_path: Path,
    native_tm_observations_sha256: str,
    policy_path: Path,
    run_id: str,
    output_path: Path,
) -> NativeTMCanonicalMappingPublication:
    """Build, publish by direct O_EXCL, fsync, strict-replay, and return."""

    project_root = project_root.resolve()
    output_path, output_relative = _lexical_project_path(
        project_root, output_path, "native TM canonical output"
    )
    if not output_relative.startswith(f"{_OUTPUT_DIRECTORY}/"):
        raise NativeTMCanonicalMappingError(
            "LOGIC_DEVELOPMENT native TM canonical output must stay under output/development"
        )
    _validate_path_isolation([output_relative])
    payload = build_registered_native_tm_canonical_mapping(
        project_root,
        native_tm_observations_path,
        native_tm_observations_sha256,
        policy_path,
        run_id,
    )
    encoded = _canonical_json_bytes(payload)
    try:
        publication_guard = _native_document._write_exclusive(project_root, output_path, encoded)
    except _native_document.NativeTMDocumentArtifactError as exc:
        raise NativeTMCanonicalMappingError(str(exc)) from exc
    digest = sha256_bytes(encoded)
    try:
        replayed = load_registered_native_tm_canonical_mapping(
            output_path,
            project_root=project_root,
            expected_sha256=digest,
        )
        if replayed != payload:
            raise NativeTMCanonicalMappingError("published native TM canonical replay drifted")
    except BaseException as exc:
        try:
            _rollback_publication(publication_guard, exc)
        finally:
            _native_document._close_guard_best_effort(publication_guard)
        raise
    _native_document._close_guard_best_effort(publication_guard)
    return NativeTMCanonicalMappingPublication(
        path=output_path,
        sha256=digest,
        size_bytes=len(encoded),
        payload=payload,
    )


__all__ = [
    "POLICY_RELATIVE_PATH",
    "NativeTMCanonicalMappingError",
    "NativeTMCanonicalMappingPublication",
    "build_registered_native_tm_canonical_mapping",
    "load_native_tm_canonical_mapping_policy",
    "load_registered_native_tm_canonical_mapping",
    "publish_registered_native_tm_canonical_mapping",
]
