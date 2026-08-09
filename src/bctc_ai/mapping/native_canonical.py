from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import tempfile
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from rapidfuzz.fuzz import ratio

from bctc_ai.core.hashing import sha256_bytes, sha256_file, stable_records_hash
from bctc_ai.core.text import normalize_text, retrieval_key
from bctc_ai.mapping.lctt import (
    CashFlowEvidence,
    CashFlowMethod,
    CashFlowRules,
    classify_cash_flow_method,
)
from bctc_ai.mapping.ordered_subgraph_v2 import (
    SchemaProjectionNodeV2,
    SchemaProjectionV2,
    build_schema_projection_v2,
)
from bctc_ai.rows.native_statement import load_registered_native_statement_rows
from bctc_ai.schema.coverage import (
    SchemaCoverageContract,
    SchemaCoverageTarget,
    SchemaSearchEvidence,
    evaluate_mandatory_search,
    load_schema_coverage,
)
from bctc_ai.schema.hierarchy import (
    HierarchyItem,
    HierarchyRegistry,
    apply_hierarchy_reference,
    load_hierarchy_reference,
)
from bctc_ai.schema.registry import SchemaItem, load_all, load_schema_contract

POLICY_RELATIVE_PATH = Path("config/mapping/native-canonical-v1.yaml")
ROWS_POLICY_RELATIVE_PATH = Path("config/rows/native-statement-rows-v1.yaml")

_POLICY_NAME = "REGISTERED_NATIVE_CANONICAL_MAPPING_V1"
_CLAIM_BOUNDARY = "SOURCE_ROW_CANONICAL_DISPOSITIONS_AND_SCHEMA_GAP_PROPOSALS"
_OUTPUT_FORMAT = "REGISTERED_NATIVE_CANONICAL_MAPPING_RESULT_V1"
_OUTPUT_STATUS = "ACCEPTED_NATIVE_CANONICAL_MAPPING"
_INPUT_FORMAT = "REGISTERED_NATIVE_STATEMENT_ROWS_RESULT_V1"
_INPUT_POLICY = "REGISTERED_NATIVE_STATEMENT_ROWS_V1"
_INPUT_CLAIM = "UNMAPPED_SOURCE_ROWS_AND_CELLS_ONLY"
_INPUT_STATUS = "ACCEPTED_NATIVE_STATEMENT_ROWS"
_DISPOSITIONS = (
    "EXISTING_ITEM",
    "NEW_ITEM_PROPOSAL",
    "AMBIGUOUS",
    "UNRESOLVED",
    "STRUCTURAL",
)
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
_ALIAS_PROPOSAL_TYPES = (
    "SOURCE_WORDING",
    "BANK_WORDING",
    "REGULATORY_WORDING",
    "ABBREVIATION",
    "PUNCTUATION",
    "OCR_VARIANT",
)
_STATEMENT_TYPES = ("CDKT", "KQKD", "LCTT", "TM")
_ALLOWED_ROLES = {"LOGIC_DEVELOPMENT", "CALIBRATION", "VALIDATION", "PRODUCTION_INPUT"}
_FORBIDDEN_ROLES = {"UNTOUCHED_HOLDOUT"}
_ROLE_DIRECTORIES = {
    "LOGIC_DEVELOPMENT": "output/development",
    "CALIBRATION": "output/calibration",
    "VALIDATION": "output/validation",
    "PRODUCTION_INPUT": "output/production",
}
_SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_IMPLEMENTATION_PATHS = (
    "src/bctc_ai/core/hashing.py",
    "src/bctc_ai/core/text.py",
    "src/bctc_ai/mapping/lctt.py",
    "src/bctc_ai/mapping/ordered_subgraph_v2.py",
    "src/bctc_ai/mapping/native_canonical.py",
    "src/bctc_ai/rows/native_statement.py",
    "src/bctc_ai/schema/append_only.py",
    "src/bctc_ai/schema/business_update.py",
    "src/bctc_ai/schema/coverage.py",
    "src/bctc_ai/schema/hierarchy.py",
    "src/bctc_ai/schema/registry.py",
    "src/bctc_ai/schema/xlsx_reader.py",
)
_STRUCTURAL_ENUMERATOR = re.compile(r"^\s*(?:(?:[IVXLCDM]+|[A-ZĐ]|\d+)\s*[.)-])\s*", re.IGNORECASE)
_TRAILING_FORMULA = re.compile(r"\s*\([IVXLCDM0-9+\-]+\)\s*$", re.IGNORECASE)
_ACCOUNTING_ABBREVIATIONS = {
    "tscd": "tai san co dinh",
    "nhnn": "ngan hang nha nuoc",
    "tctd": "to chuc tin dung",
    "tndn": "thu nhap doanh nghiep",
    "hdkd": "hoat dong kinh doanh",
    "gtcg": "giay to co gia",
}
_AUDITED_TERMINAL_AGGREGATE_MATCH_BASIS = (
    "AUDITED_FORMULA_UNIQUE_TERMINAL_AGGREGATE_COMPLETE_TOPOLOGY_EXACT_SUM"
)


class NativeCanonicalMappingError(RuntimeError):
    """Raised when a native-row mapping input or invariant is unsafe."""


def _audited_terminal_aggregate_enabled(policy: Mapping[str, Any]) -> bool:
    mapping = policy.get("mapping")
    return bool(
        isinstance(mapping, Mapping)
        and _AUDITED_TERMINAL_AGGREGATE_MATCH_BASIS in mapping.get("automatic_match_authority", ())
    )


def _compressed_hierarchy_enabled(policy: Mapping[str, Any]) -> bool:
    mapping = policy.get("mapping")
    return bool(
        isinstance(mapping, Mapping)
        and mapping.get(
            "compressed_hierarchy_edge_allowed_only_through_unobserved_schema_intermediates"
        )
        is True
    )


@dataclass(frozen=True)
class NativeCanonicalMappingPublication:
    path: Path
    sha256: str
    size_bytes: int
    payload: dict[str, Any]


@dataclass(frozen=True)
class _SourceRow:
    row: dict[str, Any]
    page_record: dict[str, Any]
    order: int
    page_order: int
    statement_type: str
    scope: str
    within_financial_table_span: bool

    @property
    def row_id(self) -> str:
        return str(self.row["row_id"])

    @property
    def label(self) -> str:
        return normalize_text(str(self.row.get("normalized_label", "")))


@dataclass(frozen=True)
class _Candidate:
    report_norm_id: int
    match_basis: str
    matched_label: str
    alias_authority_type: str | None = None
    alias_authority_evidence_sha256: str | None = None


@dataclass(frozen=True)
class _AcceptedAlias:
    statement_type: str
    report_norm_id: int
    alias: str
    authority_type: str
    authority_evidence: dict[str, Any]

    @property
    def authority_evidence_sha256(self) -> str:
        return _record_hash(self.authority_evidence)


@dataclass(frozen=True)
class _AuditedFormula:
    statement_type: str
    schema_id: int
    operator: str
    component_schema_ids: tuple[int, ...]
    audit_path: str
    audit_sha256: str
    audit_status: str
    record_index: int
    record_sha256: str

    @property
    def authority_evidence(self) -> dict[str, Any]:
        return {
            "audit_path": self.audit_path,
            "audit_sha256": self.audit_sha256,
            "audit_status": self.audit_status,
            "record_index": self.record_index,
            "record_sha256": self.record_sha256,
        }

    @property
    def authority_evidence_sha256(self) -> str:
        return _record_hash(self.authority_evidence)


@dataclass(frozen=True)
class _ObservedBlock:
    statement_type: str
    presentation_scope: str
    pages: tuple[int, ...]
    exhaustive: bool
    evidence: dict[str, Any]


@dataclass(frozen=True)
class _PathResolution:
    selected: Mapping[str, _Candidate]
    ambiguous: Mapping[str, tuple[int, ...]]
    all_candidates: Mapping[str, tuple[_Candidate, ...]]
    maximum_cardinality: int


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def _resolve_under_root(project_root: Path, raw_path: str | Path, label: str) -> Path:
    raw = Path(raw_path)
    if raw.is_absolute():
        path = raw.resolve()
    else:
        if not str(raw):
            raise NativeCanonicalMappingError(f"{label} path is empty")
        path = (project_root / raw).resolve()
    try:
        path.relative_to(project_root)
    except ValueError as exc:
        raise NativeCanonicalMappingError(f"{label} escapes the project root") from exc
    return path


def _relative_path(project_root: Path, path: Path, label: str) -> str:
    try:
        return path.resolve().relative_to(project_root).as_posix()
    except ValueError as exc:
        raise NativeCanonicalMappingError(f"{label} must stay inside the project root") from exc


def _identity(path: Path, project_root: Path, kind: str) -> dict[str, Any]:
    if not path.is_file():
        raise NativeCanonicalMappingError(f"required {kind} input is absent")
    result = {
        "kind": kind,
        "path": _relative_path(project_root, path, kind),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }
    return result


def _validate_pinned_identity(
    project_root: Path, raw: Any, label: str
) -> tuple[Path, dict[str, Any]]:
    if not isinstance(raw, dict) or set(raw) != {"path", "sha256"}:
        raise NativeCanonicalMappingError(f"{label} identity must contain path and sha256")
    path = _resolve_under_root(project_root, str(raw["path"]), label)
    digest = raw["sha256"]
    if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
        raise NativeCanonicalMappingError(f"{label} SHA-256 is not pinned")
    identity = _identity(path, project_root, label)
    if identity["sha256"] != digest:
        raise NativeCanonicalMappingError(f"{label} hash drifted")
    return path, identity


def _require_exact(value: Any, expected: Mapping[str, Any], label: str) -> None:
    if value != dict(expected):
        raise NativeCanonicalMappingError(f"{label} contract drifted")


def load_native_canonical_mapping_policy(path: Path, project_root: Path) -> dict[str, Any]:
    """Load the sole mapping policy and reject any source-specific rule surface."""

    project_root = project_root.resolve()
    path = path.resolve()
    if path != (project_root / POLICY_RELATIVE_PATH).resolve():
        raise NativeCanonicalMappingError(
            f"native canonical mapping requires canonical policy {POLICY_RELATIVE_PATH}"
        )
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise NativeCanonicalMappingError("cannot load native canonical mapping policy") from exc
    if not isinstance(payload, dict):
        raise NativeCanonicalMappingError("native canonical mapping policy must be an object")
    _require_exact(
        {key: payload.get(key) for key in ("version", "policy", "claim_boundary")},
        {"version": 1, "policy": _POLICY_NAME, "claim_boundary": _CLAIM_BOUNDARY},
        "native canonical mapping identity",
    )
    _require_exact(
        payload.get("accepted_input"),
        {
            "format_version": _INPUT_FORMAT,
            "policy": _INPUT_POLICY,
            "claim_boundary": _INPUT_CLAIM,
            "status": _INPUT_STATUS,
            "trusted_sha256_required": True,
            "denominator": "ALL_RECONSTRUCTED_SOURCE_ROWS",
        },
        "native canonical accepted-input",
    )
    if set(payload.get("allowed_dataset_roles", ())) != _ALLOWED_ROLES:
        raise NativeCanonicalMappingError("native canonical allowed roles drifted")
    if set(payload.get("forbidden_dataset_roles", ())) != _FORBIDDEN_ROLES:
        raise NativeCanonicalMappingError("native canonical forbidden roles drifted")
    if payload.get("role_directories") != _ROLE_DIRECTORIES:
        raise NativeCanonicalMappingError("native canonical role directories drifted")

    schema = payload.get("schema_authority")
    if not isinstance(schema, dict):
        raise NativeCanonicalMappingError("native canonical schema authority is absent")
    if (
        schema.get("schema_name") != "UNIVERSAL_BANK_BCTC_SCHEMA"
        or schema.get("schema_strategy") != "SOURCE_EVIDENCE_DRIVEN_APPEND_ONLY_SUPERSET"
    ):
        raise NativeCanonicalMappingError("native canonical schema strategy drifted")
    for key in (
        "source_config",
        "hierarchy_config",
        "schema_registry",
        "hierarchy_registry",
        "coverage_config",
        "coverage_registry",
    ):
        _validate_pinned_identity(project_root, schema.get(key), key.replace("_", " "))
    if (
        not isinstance(schema.get("revision"), str)
        or not isinstance(schema.get("item_count"), int)
        or schema["item_count"] < 1
        or not isinstance(schema.get("counts"), dict)
        or tuple(schema["counts"]) != _STATEMENT_TYPES
        or sum(schema["counts"].values()) != schema["item_count"]
        or not isinstance(schema.get("high_watermark"), int)
        or schema["high_watermark"] < 1
        or _SHA256.fullmatch(str(schema.get("graph_sha256", ""))) is None
        or _SHA256.fullmatch(str(schema.get("ordered_canonical_projection_sha256", ""))) is None
    ):
        raise NativeCanonicalMappingError("native canonical schema revision identity is invalid")
    projection_hashes = schema.get("statement_projection_sha256")
    if (
        not isinstance(projection_hashes, dict)
        or tuple(projection_hashes) != _STATEMENT_TYPES
        or any(_SHA256.fullmatch(str(value)) is None for value in projection_hashes.values())
    ):
        raise NativeCanonicalMappingError("native canonical statement projections are not pinned")

    mapping = payload.get("mapping")
    if not isinstance(mapping, dict):
        raise NativeCanonicalMappingError("native canonical mapping rules are absent")
    expected_mapping = {
        "statement_types": list(_STATEMENT_TYPES),
        "automatic_match_authority": [
            "CANONICAL_RETRIEVAL_KEY_EXACT",
            "ACCEPTED_STRUCTURAL_ALIAS_RETRIEVAL_KEY_EXACT",
            "ACCEPTED_ACCOUNTING_ABBREVIATION_NORMALIZATION",
            "REPEATED_PARENT_DETAIL_WITH_COMPLETE_HIERARCHY_AND_EQUATION",
            _AUDITED_TERMINAL_AGGREGATE_MATCH_BASIS,
        ],
        "accepted_alias_authority_types": [
            "USER_SUPPLIED_HIERARCHY_LABEL",
            "AUDITED_SCHEMA_ALIAS",
        ],
        "untyped_structural_aliases_mapping_eligible": False,
        "accepted_accounting_abbreviations": {
            "tscđ": "tài sản cố định",
            "nhnn": "ngân hàng nhà nước",
            "tctd": "tổ chức tín dụng",
            "tndn": "thu nhập doanh nghiệp",
            "hđkd": "hoạt động kinh doanh",
            "gtcg": "giấy tờ có giá",
        },
        "historical_aliases_allowed": False,
        "same_run_alias_proposals_mapping_eligible": False,
        "numeric_report_norm_id_order_allowed": False,
        "order_authority": "WORKBOOK_DISPLAY_ORDER",
        "path_algorithm": "MAXIMUM_CARDINALITY_MONOTONE_SKIP_CAPABLE_EXACT_MATCH",
        "require_one_disposition_per_source_row": True,
        "require_one_to_one_existing_item_mapping": True,
        "require_hierarchy_consistency_when_both_source_parent_and_schema_parent_are_observed": True,
        "compressed_hierarchy_edge_allowed_only_through_unobserved_schema_intermediates": True,
        "off_balance_sheet_rows_are_accounting_items": True,
        "section_header_is_not_automatically_structural": True,
        "unmatched_label_only_parent_with_distinct_accounting_children": "NEW_ITEM_PROPOSAL",
        "repeated_or_childless_label_only_heading": "STRUCTURAL",
        "outside_financial_table_span_row": "UNRESOLVED",
        "unlabeled_numeric_row": ("UNRESOLVED_UNLESS_AUDITED_FORMULA_UNIQUE_TERMINAL_AGGREGATE"),
        "audited_formula_terminal_aggregate": {
            "formula_authority": "HASH_BOUND_APPROVED_BUSINESS_UPDATE_AUDIT_RECORD",
            "operator": "SUM",
            "target_topology": "NON_ROOT_PARENT_WITH_EXACT_ORDERED_DIRECT_CHILDREN",
            "source_topology": (
                "UNIQUE_UNLABELED_TERMINAL_AFTER_CONTIGUOUS_COMPLETE_DESCENDANT_INTERVAL"
            ),
            "scope_rule": "SAME_STATEMENT_PRESENTATION_SCOPE_PHYSICAL_TABLE_AND_AXES",
            "selection_stage": "BOUNDED_POST_MONOTONE_PATH_PROMOTION",
            "arithmetic_rule": "EXACT_EVERY_AXIS_CORROBORATION_OR_VETO_ONLY",
        },
        "unmatched_labeled_value_row": "NEW_ITEM_PROPOSAL",
        "fuzzy_similarity_can_map": False,
        "alias_proposal_threshold": 0.96,
        "alias_proposal_minimum_margin": 0.10,
        "alias_proposal_maximum_token_symmetric_difference": 1,
        "alias_proposal_types": list(_ALIAS_PROPOSAL_TYPES),
        "ocr_variant_mapping_eligible": False,
        "equations_can_select_mapping": False,
        "equations_may_only_corroborate_or_veto_complete_structure": True,
        "equation_rounding_tolerance_source_units": 1,
        "non_additive_child_prefixes": ["trong đó", "of which"],
        "new_items_allocate_report_norm_id": False,
        "minimum_document_schema_coverage": 0,
    }
    _require_exact(mapping, expected_mapping, "native canonical mapping rules")
    _require_exact(
        payload.get("cash_flow"),
        {
            "classifier": "CONFIGURED_ORDERED_LABEL_ANCHORS",
            "cross_branch_mapping": "FORBIDDEN",
            "opposite_branch_not_applicable_only_when_method_proven": True,
        },
        "native canonical cash-flow rules",
    )
    _require_exact(
        payload.get("coverage"),
        {
            "role": "ROLE_B",
            "universal_schema_is_superset": True,
            "statement_scope_exhaustiveness_requires_accepted_complete_chain": True,
            "not_observed_requires_independently_complete_statement_scope_block": True,
            "structural_scope_root_without_row": "BLANK_WITH_SCOPE_EVIDENCE",
            "unknown_or_unassigned_statement_scope_outcome": "UNRESOLVED",
            "unprocessed_statement_outcome": "UNRESOLVED",
            "absent_item_in_exhaustively_observed_block": "NOT_OBSERVED",
            "terminal_outcomes": list(_TERMINAL_OUTCOMES),
        },
        "native canonical coverage",
    )
    _require_exact(
        payload.get("role_isolation"),
        {
            "prior_answer_artifacts_allowed": False,
            "historical_values_allowed": False,
            "historical_aliases_allowed": False,
            "role_a_outputs_allowed": False,
            "human_review_outputs_allowed": False,
            "source_bank_identity_used_for_mapping": False,
            "filename_identity_used_for_mapping": False,
            "page_number_rules_used_for_mapping": False,
            "source_row_count_rules_used_for_mapping": False,
        },
        "native canonical role isolation",
    )
    _require_exact(
        payload.get("output"),
        {
            "format": _OUTPUT_FORMAT,
            "status": _OUTPUT_STATUS,
            "dispositions": list(_DISPOSITIONS),
            "canonical_json": True,
            "exclusive_no_overwrite": True,
            "absolute_project_paths_allowed": False,
            "source_cells_preserved_by_hash_bound_join": True,
        },
        "native canonical output",
    )

    # A generic production policy may name statements and accounting concepts,
    # but never a bank, source file, page, row ordinal, or expected document count.
    forbidden_keys = {
        "bank",
        "filename",
        "file_name",
        "pdf",
        "page",
        "row_id",
        "row_count",
        "expected_source_count",
    }

    def walk(value: Any) -> Iterable[str]:
        if isinstance(value, dict):
            for key, child in value.items():
                yield str(key).casefold()
                yield from walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk(child)

    if forbidden_keys & set(walk(payload)):
        raise NativeCanonicalMappingError("native canonical policy contains a source-specific rule")
    return copy.deepcopy(payload)


def _git(project_root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise NativeCanonicalMappingError(
            f"git {' '.join(arguments)} failed: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def _current_git_state(project_root: Path) -> dict[str, Any]:
    result = {
        "commit": _git(project_root, "rev-parse", "HEAD"),
        "dirty": bool(_git(project_root, "status", "--porcelain", "--untracked-files=all")),
    }
    return result


def _validate_git_state(state: Any) -> dict[str, Any]:
    if (
        not isinstance(state, dict)
        or set(state) != {"commit", "dirty"}
        or not isinstance(state.get("commit"), str)
        or _GIT_COMMIT.fullmatch(state["commit"]) is None
        or state.get("dirty") is not False
    ):
        raise NativeCanonicalMappingError(
            "native canonical mapping requires a clean, identified Git commit"
        )
    return {"commit": state["commit"], "dirty": False}


def _file_identity_at_commit(project_root: Path, commit: str, raw_path: str) -> dict[str, Any]:
    if _GIT_COMMIT.fullmatch(commit) is None:
        raise NativeCanonicalMappingError("native canonical producer commit is invalid")
    result = subprocess.run(
        ["git", "show", f"{commit}:{raw_path}"],
        cwd=project_root,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise NativeCanonicalMappingError(
            f"native canonical producer commit lacks implementation input: {raw_path}"
        )
    return {
        "path": raw_path,
        "sha256": sha256_bytes(result.stdout),
        "size_bytes": len(result.stdout),
    }


def _yaml_payload_at_commit(project_root: Path, commit: str, raw_path: str) -> dict[str, Any]:
    if _GIT_COMMIT.fullmatch(commit) is None:
        raise NativeCanonicalMappingError("producer commit is invalid")
    result = subprocess.run(
        ["git", "show", f"{commit}:{raw_path}"],
        cwd=project_root,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise NativeCanonicalMappingError(
            f"producer commit lacks versioned policy input: {raw_path}"
        )
    try:
        payload = yaml.safe_load(result.stdout.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise NativeCanonicalMappingError("producer policy snapshot cannot be decoded") from exc
    if not isinstance(payload, dict):
        raise NativeCanonicalMappingError("producer policy snapshot is not an object")
    return payload


def _json_payload_at_commit(project_root: Path, commit: str, raw_path: str) -> dict[str, Any]:
    if _GIT_COMMIT.fullmatch(commit) is None:
        raise NativeCanonicalMappingError("producer commit is invalid")
    result = subprocess.run(
        ["git", "show", f"{commit}:{raw_path}"],
        cwd=project_root,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise NativeCanonicalMappingError(f"producer commit lacks versioned JSON input: {raw_path}")
    try:
        payload = json.loads(result.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NativeCanonicalMappingError("producer JSON snapshot cannot be decoded") from exc
    if not isinstance(payload, dict):
        raise NativeCanonicalMappingError("producer JSON snapshot is not an object")
    return payload


def _implementation_ledger(project_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for raw_path in _IMPLEMENTATION_PATHS:
        path = _resolve_under_root(project_root, raw_path, "mapping implementation")
        identity = _identity(path, project_root, "IMPLEMENTATION")
        records.append({key: identity[key] for key in ("path", "sha256", "size_bytes")})
    return records


def _implementation_ledger_at_commit(project_root: Path, commit: str) -> list[dict[str, Any]]:
    return [_file_identity_at_commit(project_root, commit, path) for path in _IMPLEMENTATION_PATHS]


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise NativeCanonicalMappingError(f"cannot read {label}") from exc
    if not isinstance(payload, dict):
        raise NativeCanonicalMappingError(f"{label} must be a JSON object")
    return payload


def _canonical_project_relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise NativeCanonicalMappingError(f"{label} must be a canonical relative POSIX path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or re.match(r"^[A-Za-z]:", value)
        or path.as_posix() != value
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise NativeCanonicalMappingError(f"{label} must be a canonical relative POSIX path")
    return value


def _schema_runtime_path_specs(
    policy: Mapping[str, Any],
    source_config: Mapping[str, Any],
    hierarchy_config: Mapping[str, Any],
) -> list[tuple[str, str]]:
    """Return the exact schema read inventory without consulting mutable files."""

    authority = policy.get("schema_authority")
    if not isinstance(authority, Mapping):
        raise NativeCanonicalMappingError("schema authority is absent from producer policy")

    def authority_path(key: str) -> str:
        record = authority.get(key)
        if not isinstance(record, Mapping):
            raise NativeCanonicalMappingError(f"producer schema authority lacks {key}")
        return _canonical_project_relative_path(record.get("path"), key.replace("_", " "))

    specs: list[tuple[str, str]] = [
        (authority_path("source_config"), "SCHEMA_SOURCE_CONFIG"),
        (authority_path("hierarchy_config"), "HIERARCHY_CONFIG"),
    ]
    sources = source_config.get("sources")
    if not isinstance(sources, Mapping):
        raise NativeCanonicalMappingError("schema workbook source configuration is invalid")
    for statement, relative in sources.items():
        if statement not in _STATEMENT_TYPES:
            raise NativeCanonicalMappingError("schema workbook statement is invalid")
        specs.append(
            (
                _canonical_project_relative_path(relative, "schema workbook"),
                "SCHEMA_WORKBOOK",
            )
        )

    base = source_config.get("base_schema")
    base_workbooks = base.get("workbooks") if isinstance(base, Mapping) else None
    if not isinstance(base_workbooks, Mapping):
        raise NativeCanonicalMappingError("BASE_SCHEMA workbook identities are absent")
    for statement, record in base_workbooks.items():
        if statement not in _STATEMENT_TYPES or not isinstance(record, Mapping):
            raise NativeCanonicalMappingError("BASE_SCHEMA workbook identity is invalid")
        specs.append(
            (
                _canonical_project_relative_path(record.get("path"), "BASE_SCHEMA workbook"),
                "BASE_SCHEMA_WORKBOOK",
            )
        )

    specs.append(
        (
            _canonical_project_relative_path(
                source_config.get("cash_flow_rules"), "cash-flow rules"
            ),
            "CASH_FLOW_RULES",
        )
    )
    for config_key, kind in (
        ("approved_append_audits", "SCHEMA_APPEND_AUDIT"),
        ("approved_business_update_audits", "SCHEMA_BUSINESS_UPDATE_AUDIT"),
    ):
        audit_paths = source_config.get(config_key, [])
        if not isinstance(audit_paths, list):
            raise NativeCanonicalMappingError(f"{config_key} is invalid")
        specs.extend(
            (_canonical_project_relative_path(raw_path, config_key), kind)
            for raw_path in audit_paths
        )

    hierarchy_root = hierarchy_config.get("root")
    hierarchy_sources = hierarchy_config.get("sources")
    if not isinstance(hierarchy_root, str) or not isinstance(hierarchy_sources, Mapping):
        raise NativeCanonicalMappingError("hierarchy workbook source configuration is invalid")
    hierarchy_root = _canonical_project_relative_path(hierarchy_root, "hierarchy root")
    for statement, record in hierarchy_sources.items():
        if statement not in _STATEMENT_TYPES or not isinstance(record, Mapping):
            raise NativeCanonicalMappingError("hierarchy workbook identity is invalid")
        source_name = _canonical_project_relative_path(record.get("path"), "hierarchy workbook")
        joined = (PurePosixPath(hierarchy_root) / PurePosixPath(source_name)).as_posix()
        specs.append(
            (
                _canonical_project_relative_path(joined, "hierarchy workbook"),
                "HIERARCHY_WORKBOOK",
            )
        )

    for key, kind in (
        ("schema_registry", "SCHEMA_REGISTRY"),
        ("hierarchy_registry", "HIERARCHY_REGISTRY"),
        ("coverage_config", "SCHEMA_COVERAGE_CONFIG"),
        ("coverage_registry", "SCHEMA_COVERAGE_REGISTRY"),
    ):
        specs.append((authority_path(key), kind))
    if len(specs) != len(set(specs)):
        raise NativeCanonicalMappingError("schema runtime inventory repeats a kind/path")
    return specs


def _schema_runtime_paths(project_root: Path, policy: Mapping[str, Any]) -> list[tuple[Path, str]]:
    """Enumerate every current schema/hierarchy file opened by the stage.

    The schema loaders internally re-open these paths. Taking identities before
    and after mapping makes that otherwise implicit read set explicit and
    catches time-of-check/time-of-use drift.
    """

    authority = policy["schema_authority"]
    source_config_path = _resolve_under_root(
        project_root, authority["source_config"]["path"], "schema source config"
    )
    hierarchy_config_path = _resolve_under_root(
        project_root, authority["hierarchy_config"]["path"], "hierarchy config"
    )
    try:
        source_config = yaml.safe_load(source_config_path.read_text(encoding="utf-8")) or {}
        hierarchy_config = yaml.safe_load(hierarchy_config_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise NativeCanonicalMappingError("cannot inspect schema input graph") from exc
    if not isinstance(source_config, dict) or not isinstance(hierarchy_config, dict):
        raise NativeCanonicalMappingError("schema input graph configs are invalid")

    return [
        (_resolve_under_root(project_root, raw_path, kind), kind)
        for raw_path, kind in _schema_runtime_path_specs(policy, source_config, hierarchy_config)
    ]


def _runtime_ledger(
    project_root: Path,
    rows_path: Path,
    policy_path: Path,
    rows_policy_path: Path,
    policy: Mapping[str, Any],
    row_payload: Mapping[str, Any],
) -> list[dict[str, Any]]:
    records = [
        _identity(rows_path, project_root, "REGISTERED_NATIVE_STATEMENT_ROWS"),
        _identity(policy_path, project_root, "THIS_POLICY"),
        _identity(rows_policy_path, project_root, "NATIVE_STATEMENT_ROWS_POLICY"),
    ]
    records.extend(
        _identity(path, project_root, kind)
        for path, kind in _schema_runtime_paths(project_root, policy)
    )
    upstream = row_payload.get("inputs", {}).get("runtime_read_ledger")
    if not isinstance(upstream, list):
        raise NativeCanonicalMappingError("native-row upstream runtime ledger is absent")
    for record in upstream:
        if not isinstance(record, dict) or set(record) != {"kind", "path", "sha256", "size_bytes"}:
            raise NativeCanonicalMappingError("native-row upstream runtime ledger is malformed")
        records.append(
            {
                "kind": f"UPSTREAM_{record['kind']}",
                "path": record["path"],
                "sha256": record["sha256"],
                "size_bytes": record["size_bytes"],
            }
        )
    records.sort(key=lambda item: (item["kind"], item["path"]))
    if len({(record["kind"], record["path"]) for record in records}) != len(records):
        raise NativeCanonicalMappingError("native canonical runtime ledger repeats an identity")
    return records


def _universal_canonical_projection_hash(items: Sequence[SchemaItem]) -> str:
    return stable_records_hash(
        json.dumps(
            {
                "statement_type": item.statement_type,
                "report_norm_id": item.schema_id,
                "canonical_name": item.canonical_name,
                "display_order": item.display_order,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        for item in items
    )


def _accepted_alias_projection(
    aliases: Sequence[_AcceptedAlias],
) -> list[dict[str, Any]]:
    return [
        {
            "statement_type": alias.statement_type,
            "report_norm_id": alias.report_norm_id,
            "alias": alias.alias,
            "authority_type": alias.authority_type,
            "authority_evidence_sha256": alias.authority_evidence_sha256,
        }
        for alias in aliases
    ]


def _structural_alias_key(value: str) -> str:
    structural = _STRUCTURAL_ENUMERATOR.sub("", normalize_text(value))
    structural = _TRAILING_FORMULA.sub("", structural)
    return retrieval_key(structural)


def _load_accepted_alias_authority(
    project_root: Path,
    source_config: Mapping[str, Any],
    schema_items: Sequence[SchemaItem],
    hierarchy_registry: HierarchyRegistry,
    hierarchy_items: Sequence[HierarchyItem],
) -> tuple[_AcceptedAlias, ...]:
    """Build typed, evidence-bound alias authority without trusting list membership alone."""

    schema_by_key = {(item.statement_type, item.schema_id): item for item in schema_items}
    hierarchy_workbook_by_statement = {
        workbook.statement_type: workbook for workbook in hierarchy_registry.workbooks
    }
    aliases: list[_AcceptedAlias] = []
    for reference in hierarchy_items:
        item = schema_by_key.get((reference.statement_type, reference.schema_id))
        if item is None:
            raise NativeCanonicalMappingError("hierarchy alias points outside universal schema")
        if retrieval_key(reference.label) == retrieval_key(item.canonical_name):
            continue
        if normalize_text(reference.label) not in {
            normalize_text(alias) for alias in item.structural_aliases
        }:
            raise NativeCanonicalMappingError(
                "typed hierarchy alias is absent from the applied schema projection"
            )
        aliases.append(
            _AcceptedAlias(
                statement_type=reference.statement_type,
                report_norm_id=reference.schema_id,
                alias=normalize_text(reference.label),
                authority_type="USER_SUPPLIED_HIERARCHY_LABEL",
                authority_evidence={
                    "hierarchy_authority": hierarchy_registry.authority,
                    "hierarchy_status": hierarchy_registry.status,
                    "source_path": reference.source_path,
                    "source_workbook_sha256": hierarchy_workbook_by_statement[
                        reference.statement_type
                    ].sha256,
                    "source_row": reference.source_row,
                },
            )
        )

    raw_audits = source_config.get("approved_business_update_audits", [])
    if not isinstance(raw_audits, list) or any(not isinstance(path, str) for path in raw_audits):
        raise NativeCanonicalMappingError("approved business-update audit list is malformed")
    for raw_path in raw_audits:
        audit_path = _resolve_under_root(
            project_root, raw_path, "approved business-update alias audit"
        )
        audit = _read_json(audit_path, "approved business-update alias audit")
        if audit.get("status") != "APPLIED_AND_VERIFIED":
            raise NativeCanonicalMappingError("business-update alias audit is not accepted")
        changes = audit.get("structural_alias_changes")
        if not isinstance(changes, list):
            raise NativeCanonicalMappingError("business-update alias audit has no typed changes")
        audit_identity = _identity(audit_path, project_root, "SCHEMA_BUSINESS_UPDATE_AUDIT")
        for change_index, change in enumerate(changes):
            if not isinstance(change, dict):
                raise NativeCanonicalMappingError("business-update alias change is malformed")
            added = change.get("added_to_structural_aliases")
            if type(added) is not bool:
                raise NativeCanonicalMappingError("business-update alias decision is untyped")
            if not added:
                continue
            statement = change.get("statement_type")
            schema_id = change.get("schema_id")
            alias = normalize_text(str(change.get("alias", "")))
            item = schema_by_key.get((statement, schema_id))
            if item is None or not alias:
                raise NativeCanonicalMappingError(
                    "accepted business-update alias points outside universal schema"
                )
            if alias not in {normalize_text(value) for value in item.structural_aliases}:
                raise NativeCanonicalMappingError(
                    "accepted business-update alias is absent from applied schema projection"
                )
            aliases.append(
                _AcceptedAlias(
                    statement_type=str(statement),
                    report_norm_id=int(schema_id),
                    alias=alias,
                    authority_type="AUDITED_SCHEMA_ALIAS",
                    authority_evidence={
                        "audit_path": audit_identity["path"],
                        "audit_sha256": audit_identity["sha256"],
                        "audit_status": audit["status"],
                        "change_index": change_index,
                        "disposition": change.get("disposition"),
                        "provenance": change.get("provenance"),
                        "source_evidence": change.get("evidence"),
                    },
                )
            )

    # One normalized alias for one item can be supported by more than one
    # accepted source. Prefer the audited schema decision over the supporting
    # hierarchy label while retaining the evidence hash in the immutable receipt.
    priority = {"AUDITED_SCHEMA_ALIAS": 0, "USER_SUPPLIED_HIERARCHY_LABEL": 1}
    selected: dict[tuple[str, int, str], _AcceptedAlias] = {}
    for alias in aliases:
        key = (
            alias.statement_type,
            alias.report_norm_id,
            _structural_alias_key(alias.alias),
        )
        previous = selected.get(key)
        if previous is None or priority[alias.authority_type] < priority[previous.authority_type]:
            selected[key] = alias
    ordered = tuple(
        sorted(
            selected.values(),
            key=lambda alias: (
                _STATEMENT_TYPES.index(alias.statement_type),
                schema_by_key[(alias.statement_type, alias.report_norm_id)].display_order,
                retrieval_key(alias.alias),
            ),
        )
    )
    for alias in ordered:
        if alias.authority_type not in priority or not alias.authority_evidence_sha256:
            raise NativeCanonicalMappingError("accepted alias authority is incomplete")
    return ordered


def _audited_formula_projection(
    formulas: Sequence[_AuditedFormula],
) -> list[dict[str, Any]]:
    return [
        {
            "statement_type": formula.statement_type,
            "schema_id": formula.schema_id,
            "operator": formula.operator,
            "component_schema_ids": list(formula.component_schema_ids),
            "authority_evidence": copy.deepcopy(formula.authority_evidence),
            "authority_evidence_sha256": formula.authority_evidence_sha256,
        }
        for formula in formulas
    ]


def _load_audited_formula_authority(
    project_root: Path,
    source_config: Mapping[str, Any],
    schema_items: Sequence[SchemaItem],
) -> tuple[_AuditedFormula, ...]:
    """Load hash-bound formula records from accepted schema-migration audits."""

    schema_by_key = {(item.statement_type, item.schema_id): item for item in schema_items}
    raw_audits = source_config.get("approved_business_update_audits", [])
    if not isinstance(raw_audits, list) or any(not isinstance(path, str) for path in raw_audits):
        raise NativeCanonicalMappingError(
            "approved business-update formula audit list is malformed"
        )
    formulas: list[_AuditedFormula] = []
    seen: set[tuple[str, int]] = set()
    for raw_path in raw_audits:
        audit_path = _resolve_under_root(
            project_root, raw_path, "approved business-update formula audit"
        )
        audit = _read_json(audit_path, "approved business-update formula audit")
        if audit.get("status") != "APPLIED_AND_VERIFIED":
            raise NativeCanonicalMappingError("business-update formula audit is not accepted")
        audit_identity = _identity(audit_path, project_root, "SCHEMA_BUSINESS_UPDATE_AUDIT")
        records = audit.get("business_formulas")
        if not isinstance(records, list):
            raise NativeCanonicalMappingError("business-update audit has no formula authority")
        for record_index, record in enumerate(records):
            if not isinstance(record, dict):
                raise NativeCanonicalMappingError("audited business formula is malformed")
            if record.get("operator") != "SUM":
                continue
            if (
                set(record) != {"statement_type", "schema_id", "operator", "component_schema_ids"}
                or record.get("statement_type") not in _STATEMENT_TYPES
                or type(record.get("schema_id")) is not int
                or record.get("operator") != "SUM"
                or not isinstance(record.get("component_schema_ids"), list)
                or not record["component_schema_ids"]
                or any(type(value) is not int for value in record["component_schema_ids"])
                or len(record["component_schema_ids"]) != len(set(record["component_schema_ids"]))
            ):
                raise NativeCanonicalMappingError("audited business formula is malformed")
            statement = str(record["statement_type"])
            schema_id = int(record["schema_id"])
            components = tuple(int(value) for value in record["component_schema_ids"])
            if (statement, schema_id) not in schema_by_key or any(
                (statement, component_id) not in schema_by_key for component_id in components
            ):
                raise NativeCanonicalMappingError("audited formula points outside universal schema")
            key = (statement, schema_id)
            if key in seen:
                raise NativeCanonicalMappingError("audited formula authority repeats a target")
            seen.add(key)
            formulas.append(
                _AuditedFormula(
                    statement_type=statement,
                    schema_id=schema_id,
                    operator=str(record["operator"]),
                    component_schema_ids=components,
                    audit_path=str(audit_identity["path"]),
                    audit_sha256=str(audit_identity["sha256"]),
                    audit_status=str(audit["status"]),
                    record_index=record_index,
                    record_sha256=_record_hash(record),
                )
            )
    return tuple(
        sorted(
            formulas,
            key=lambda formula: (
                _STATEMENT_TYPES.index(formula.statement_type),
                schema_by_key[(formula.statement_type, formula.schema_id)].display_order,
                formula.schema_id,
            ),
        )
    )


def _schema_snapshot_items(items: Sequence[SchemaItem]) -> list[dict[str, Any]]:
    return [
        {
            "schema_id": item.schema_id,
            "canonical_name": item.canonical_name,
            "normalized_name": item.normalized_name,
            "statement_type": item.statement_type,
            "display_order": item.display_order,
            "notes_section": item.notes_section,
            "parent_id": item.parent_id,
            "children": list(item.children),
            "siblings": list(item.siblings),
            "previous_id": item.previous_id,
            "next_id": item.next_id,
            "allowed_period_type": list(item.allowed_period_type),
            "allowed_unit": list(item.allowed_unit),
            "allowed_sign": list(item.allowed_sign),
            "scope": list(item.scope),
            "cash_flow_branch": item.cash_flow_branch,
            "hierarchy_level": item.hierarchy_level,
            "hierarchy_source": item.hierarchy_source,
            "structural_aliases": list(item.structural_aliases),
            "source_workbook": item.source_workbook,
            "source_row": item.source_row,
        }
        for item in items
    ]


def _coverage_snapshot(coverage: SchemaCoverageContract) -> dict[str, Any]:
    return {
        "version": coverage.version,
        "config_path": coverage.config_path,
        "config_sha256": coverage.config_sha256,
        "selection": coverage.selection,
        "order_authority": coverage.order_authority,
        "targets": [asdict(target) for target in coverage.targets],
        "consumers": {key: list(value) for key, value in coverage.consumers.items()},
        "mandatory_search_roles": list(coverage.mandatory_search_roles),
        "terminal_outcomes": list(coverage.terminal_outcomes),
        "completion_rule": coverage.completion_rule,
        "ordered_targets_sha256": coverage.ordered_targets_sha256,
    }


def _cash_flow_rules_snapshot(rules: CashFlowRules, project_root: Path) -> dict[str, Any]:
    return {
        "version": rules.version,
        "authority": rules.authority,
        "semantic_authority_status": rules.semantic_authority_status,
        "maximum_anchor_distance": rules.maximum_anchor_distance,
        "label_sequences": {
            method.value: [list(sequence) for sequence in rules.label_sequences[method]]
            for method in (CashFlowMethod.DIRECT, CashFlowMethod.INDIRECT)
        },
        "schema_order_blocks": {
            method.value: [list(block) for block in rules.schema_order_blocks[method]]
            for method in (CashFlowMethod.DIRECT, CashFlowMethod.INDIRECT)
        },
        "source_path": _relative_path(project_root, rules.source_path, "cash-flow rules"),
    }


def _producer_snapshots(
    *,
    project_root: Path,
    policy_path: Path,
    policy: Mapping[str, Any],
    schema_items: Sequence[SchemaItem],
    accepted_aliases: Sequence[_AcceptedAlias],
    audited_formulas: Sequence[_AuditedFormula] = (),
    coverage: SchemaCoverageContract,
    cash_flow_rules: CashFlowRules,
) -> dict[str, Any]:
    schema_snapshot = _schema_snapshot_items(schema_items)
    alias_snapshot = [
        {
            **record,
            "authority_evidence": copy.deepcopy(alias.authority_evidence),
        }
        for record, alias in zip(
            _accepted_alias_projection(accepted_aliases), accepted_aliases, strict=True
        )
    ]
    formula_snapshot = _audited_formula_projection(audited_formulas)
    coverage_snapshot = _coverage_snapshot(coverage)
    cash_snapshot = _cash_flow_rules_snapshot(cash_flow_rules, project_root)
    policy_snapshot = copy.deepcopy(dict(policy))
    result = {
        "policy": {
            "path": _relative_path(project_root, policy_path, "mapping policy"),
            "source_sha256": sha256_file(policy_path),
            "canonical_payload_sha256": _record_hash(policy_snapshot),
            "payload": policy_snapshot,
        },
        "schema": {
            "items_sha256": _record_hash(schema_snapshot),
            "items": schema_snapshot,
        },
        "accepted_aliases": {
            "records_sha256": _record_hash(alias_snapshot),
            "records": alias_snapshot,
        },
        "coverage": {
            "payload_sha256": _record_hash(coverage_snapshot),
            "payload": coverage_snapshot,
        },
        "cash_flow_rules": {
            "payload_sha256": _record_hash(cash_snapshot),
            "payload": cash_snapshot,
        },
    }
    if _audited_terminal_aggregate_enabled(policy):
        result["audited_formulas"] = {
            "records_sha256": _record_hash(formula_snapshot),
            "records": formula_snapshot,
        }
    return result


def _load_producer_snapshots(
    snapshots: Any,
    *,
    project_root: Path,
    producer_commit: str,
) -> tuple[
    dict[str, Any],
    list[SchemaItem],
    tuple[_AcceptedAlias, ...],
    tuple[_AuditedFormula, ...],
    SchemaCoverageContract,
    CashFlowRules,
]:
    if not isinstance(snapshots, dict):
        raise NativeCanonicalMappingError("producer-versioned snapshots are malformed")
    policy_record = snapshots["policy"]
    if not isinstance(policy_record, dict) or set(policy_record) != {
        "path",
        "source_sha256",
        "canonical_payload_sha256",
        "payload",
    }:
        raise NativeCanonicalMappingError("producer policy snapshot is malformed")
    policy_payload = policy_record["payload"]
    if (
        not isinstance(policy_payload, dict)
        or _record_hash(policy_payload) != policy_record["canonical_payload_sha256"]
        or policy_payload.get("policy") != _POLICY_NAME
        or policy_payload.get("claim_boundary") != _CLAIM_BOUNDARY
        or policy_payload.get("accepted_input", {}).get("denominator")
        != "ALL_RECONSTRUCTED_SOURCE_ROWS"
    ):
        raise NativeCanonicalMappingError("producer policy snapshot drifted")
    formula_enabled = _audited_terminal_aggregate_enabled(policy_payload)
    expected_snapshot_keys = {
        "policy",
        "schema",
        "accepted_aliases",
        "coverage",
        "cash_flow_rules",
    }
    if formula_enabled:
        expected_snapshot_keys.add("audited_formulas")
    if set(snapshots) != expected_snapshot_keys:
        raise NativeCanonicalMappingError("producer-versioned snapshots are malformed")
    committed_policy = _file_identity_at_commit(
        project_root, producer_commit, str(policy_record["path"])
    )
    if (
        committed_policy["sha256"] != policy_record["source_sha256"]
        or _yaml_payload_at_commit(project_root, producer_commit, str(policy_record["path"]))
        != policy_payload
    ):
        raise NativeCanonicalMappingError("producer policy differs from producer commit")
    approved_formula_audit_paths: frozenset[str] = frozenset()
    if formula_enabled:
        schema_authority = policy_payload.get("schema_authority")
        source_config_record = (
            schema_authority.get("source_config") if isinstance(schema_authority, Mapping) else None
        )
        if (
            not isinstance(source_config_record, Mapping)
            or not isinstance(source_config_record.get("path"), str)
            or not isinstance(source_config_record.get("sha256"), str)
        ):
            raise NativeCanonicalMappingError(
                "producer formula authority lacks schema source configuration"
            )
        source_config_path = _canonical_project_relative_path(
            source_config_record["path"], "producer schema source config"
        )
        committed_source_identity = _file_identity_at_commit(
            project_root, producer_commit, source_config_path
        )
        committed_source_config = _yaml_payload_at_commit(
            project_root, producer_commit, source_config_path
        )
        raw_approved = committed_source_config.get("approved_business_update_audits")
        if (
            committed_source_identity.get("sha256") != source_config_record["sha256"]
            or not isinstance(raw_approved, list)
            or any(not isinstance(path, str) for path in raw_approved)
        ):
            raise NativeCanonicalMappingError("producer approved formula-audit inventory drifted")
        approved_formula_audit_paths = frozenset(
            _canonical_project_relative_path(path, "approved producer formula audit")
            for path in raw_approved
        )

    schema_record = snapshots["schema"]
    raw_items = schema_record.get("items") if isinstance(schema_record, dict) else None
    if not isinstance(raw_items, list) or schema_record.get("items_sha256") != _record_hash(
        raw_items
    ):
        raise NativeCanonicalMappingError("producer schema snapshot drifted")
    try:
        schema_items = [SchemaItem(**record) for record in raw_items]
    except (TypeError, ValueError) as exc:
        raise NativeCanonicalMappingError("producer schema item snapshot is invalid") from exc
    if len({item.schema_id for item in schema_items}) != len(schema_items):
        raise NativeCanonicalMappingError("producer schema snapshot repeats ReportNormIds")

    alias_record = snapshots["accepted_aliases"]
    raw_aliases = alias_record.get("records") if isinstance(alias_record, dict) else None
    if not isinstance(raw_aliases, list) or alias_record.get("records_sha256") != _record_hash(
        raw_aliases
    ):
        raise NativeCanonicalMappingError("producer alias snapshot drifted")
    accepted_aliases: list[_AcceptedAlias] = []
    schema_by_key = {(item.statement_type, item.schema_id): item for item in schema_items}
    for record in raw_aliases:
        if (
            not isinstance(record, dict)
            or record.get("statement_type") not in _STATEMENT_TYPES
            or type(record.get("report_norm_id")) is not int
            or not isinstance(record.get("alias"), str)
            or not isinstance(record.get("authority_type"), str)
            or not isinstance(record.get("authority_evidence"), dict)
        ):
            raise NativeCanonicalMappingError("producer alias record is malformed")
        alias = _AcceptedAlias(
            statement_type=str(record.get("statement_type")),
            report_norm_id=int(record.get("report_norm_id")),
            alias=str(record.get("alias")),
            authority_type=str(record.get("authority_type")),
            authority_evidence=copy.deepcopy(record.get("authority_evidence")),
        )
        if (
            alias.authority_evidence_sha256 != record.get("authority_evidence_sha256")
            or alias.authority_type not in {"USER_SUPPLIED_HIERARCHY_LABEL", "AUDITED_SCHEMA_ALIAS"}
            or not normalize_text(alias.alias)
            or (alias.statement_type, alias.report_norm_id) not in schema_by_key
            or normalize_text(alias.alias)
            not in {
                normalize_text(value)
                for value in schema_by_key[
                    (alias.statement_type, alias.report_norm_id)
                ].structural_aliases
            }
        ):
            raise NativeCanonicalMappingError("producer alias authority drifted")
        accepted_aliases.append(alias)

    formula_record = snapshots.get(
        "audited_formulas", {"records_sha256": _record_hash([]), "records": []}
    )
    raw_formulas = formula_record.get("records") if isinstance(formula_record, dict) else None
    if not isinstance(raw_formulas, list) or formula_record.get("records_sha256") != _record_hash(
        raw_formulas
    ):
        raise NativeCanonicalMappingError("producer audited-formula snapshot drifted")
    audited_formulas: list[_AuditedFormula] = []
    formula_targets: set[tuple[str, int]] = set()
    committed_formula_audits: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for record in raw_formulas:
        evidence = record.get("authority_evidence") if isinstance(record, dict) else None
        components = record.get("component_schema_ids") if isinstance(record, dict) else None
        if (
            not isinstance(record, dict)
            or record.get("statement_type") not in _STATEMENT_TYPES
            or type(record.get("schema_id")) is not int
            or record.get("operator") != "SUM"
            or not isinstance(components, list)
            or not components
            or any(type(value) is not int for value in components)
            or len(components) != len(set(components))
            or not isinstance(evidence, dict)
            or set(evidence)
            != {
                "audit_path",
                "audit_sha256",
                "audit_status",
                "record_index",
                "record_sha256",
            }
        ):
            raise NativeCanonicalMappingError("producer audited-formula record is malformed")
        formula = _AuditedFormula(
            statement_type=str(record["statement_type"]),
            schema_id=int(record["schema_id"]),
            operator=str(record["operator"]),
            component_schema_ids=tuple(int(value) for value in components),
            audit_path=str(evidence["audit_path"]),
            audit_sha256=str(evidence["audit_sha256"]),
            audit_status=str(evidence["audit_status"]),
            record_index=int(evidence["record_index"]),
            record_sha256=str(evidence["record_sha256"]),
        )
        try:
            audit_path = _canonical_project_relative_path(
                formula.audit_path, "producer formula audit"
            )
        except NativeCanonicalMappingError:
            raise
        if audit_path not in committed_formula_audits:
            committed_identity = _file_identity_at_commit(project_root, producer_commit, audit_path)
            committed_audit = _json_payload_at_commit(project_root, producer_commit, audit_path)
            committed_formula_audits[audit_path] = (committed_identity, committed_audit)
        committed_identity, committed_audit = committed_formula_audits[audit_path]
        committed_records = committed_audit.get("business_formulas")
        expected_record = {
            "statement_type": formula.statement_type,
            "schema_id": formula.schema_id,
            "operator": formula.operator,
            "component_schema_ids": list(formula.component_schema_ids),
        }
        key = (formula.statement_type, formula.schema_id)
        if (
            key in formula_targets
            or key not in schema_by_key
            or any(
                (formula.statement_type, component_id) not in schema_by_key
                for component_id in formula.component_schema_ids
            )
            or formula.audit_status != "APPLIED_AND_VERIFIED"
            or _SHA256.fullmatch(formula.audit_sha256) is None
            or _SHA256.fullmatch(formula.record_sha256) is None
            or formula.record_index < 0
            or audit_path not in approved_formula_audit_paths
            or formula.authority_evidence_sha256 != record.get("authority_evidence_sha256")
            or committed_identity.get("sha256") != formula.audit_sha256
            or committed_audit.get("status") != formula.audit_status
            or not isinstance(committed_records, list)
            or formula.record_index >= len(committed_records)
            or committed_records[formula.record_index] != expected_record
            or _record_hash(expected_record) != formula.record_sha256
        ):
            raise NativeCanonicalMappingError("producer audited-formula authority drifted")
        formula_targets.add(key)
        audited_formulas.append(formula)

    coverage_record = snapshots["coverage"]
    raw_coverage = coverage_record.get("payload") if isinstance(coverage_record, dict) else None
    if not isinstance(raw_coverage, dict) or coverage_record.get("payload_sha256") != _record_hash(
        raw_coverage
    ):
        raise NativeCanonicalMappingError("producer coverage snapshot drifted")
    try:
        coverage = SchemaCoverageContract(
            version=int(raw_coverage["version"]),
            config_path=str(raw_coverage["config_path"]),
            config_sha256=str(raw_coverage["config_sha256"]),
            selection=str(raw_coverage["selection"]),
            order_authority=str(raw_coverage["order_authority"]),
            targets=tuple(SchemaCoverageTarget(**target) for target in raw_coverage["targets"]),
            consumers={
                str(key): tuple(int(value) for value in values)
                for key, values in raw_coverage["consumers"].items()
            },
            mandatory_search_roles=tuple(raw_coverage["mandatory_search_roles"]),
            terminal_outcomes=tuple(raw_coverage["terminal_outcomes"]),
            completion_rule=str(raw_coverage["completion_rule"]),
            ordered_targets_sha256=str(raw_coverage["ordered_targets_sha256"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise NativeCanonicalMappingError("producer coverage snapshot is invalid") from exc

    cash_record = snapshots["cash_flow_rules"]
    raw_cash = cash_record.get("payload") if isinstance(cash_record, dict) else None
    if not isinstance(raw_cash, dict) or cash_record.get("payload_sha256") != _record_hash(
        raw_cash
    ):
        raise NativeCanonicalMappingError("producer cash-flow snapshot drifted")
    try:
        cash_flow_rules = CashFlowRules(
            version=int(raw_cash["version"]),
            authority=str(raw_cash["authority"]),
            semantic_authority_status=str(raw_cash["semantic_authority_status"]),
            maximum_anchor_distance=int(raw_cash["maximum_anchor_distance"]),
            label_sequences={
                method: tuple(
                    tuple(str(label) for label in sequence)
                    for sequence in raw_cash["label_sequences"][method.value]
                )
                for method in (CashFlowMethod.DIRECT, CashFlowMethod.INDIRECT)
            },
            schema_order_blocks={
                method: tuple(
                    tuple(int(value) for value in block)
                    for block in raw_cash["schema_order_blocks"][method.value]
                )
                for method in (CashFlowMethod.DIRECT, CashFlowMethod.INDIRECT)
            },
            source_path=_resolve_under_root(
                project_root, str(raw_cash["source_path"]), "producer cash-flow rules"
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise NativeCanonicalMappingError("producer cash-flow snapshot is invalid") from exc
    return (
        policy_payload,
        schema_items,
        tuple(accepted_aliases),
        tuple(audited_formulas),
        coverage,
        cash_flow_rules,
    )


def _validate_snapshot_schema_identity(
    policy: Mapping[str, Any],
    schema_identity: Any,
    schema_items: Sequence[SchemaItem],
    accepted_aliases: Sequence[_AcceptedAlias],
    audited_formulas: Sequence[_AuditedFormula],
    coverage: SchemaCoverageContract,
) -> None:
    if not isinstance(schema_identity, dict):
        raise NativeCanonicalMappingError("producer schema identity is malformed")
    authority = policy.get("schema_authority")
    if not isinstance(authority, dict):
        raise NativeCanonicalMappingError("producer schema policy authority is missing")
    counts = {
        statement: sum(item.statement_type == statement for item in schema_items)
        for statement in _STATEMENT_TYPES
    }
    projections = {
        statement: build_schema_projection_v2(list(schema_items), statement)
        for statement in _STATEMENT_TYPES
    }
    expected_targets = tuple(
        SchemaCoverageTarget(
            schema_id=item.schema_id,
            canonical_name=item.canonical_name,
            statement_type=item.statement_type,
            display_order=item.display_order,
            source_workbook=item.source_workbook,
            source_row=item.source_row,
        )
        for item in schema_items
    )
    expected_target_hash = stable_records_hash(
        json.dumps(asdict(target), ensure_ascii=False, sort_keys=True)
        for target in expected_targets
    )
    if (
        coverage.targets != expected_targets
        or coverage.ordered_targets_sha256 != expected_target_hash
        or set(coverage.consumers)
        != {"ROLE_A", "ROLE_B", "EXCEL_OUTPUT", "EVALUATION", "MANDATORY_SEARCH"}
        or any(
            tuple(values) != tuple(item.schema_id for item in schema_items)
            for values in coverage.consumers.values()
        )
        or coverage.mandatory_search_roles != ("ROLE_A", "ROLE_B")
        or not set(_TERMINAL_OUTCOMES) <= set(coverage.terminal_outcomes)
        or coverage.completion_rule != "EXACTLY_ONE_TERMINAL_OUTCOME_PER_SCHEMA_ID_PER_DOCUMENT"
    ):
        raise NativeCanonicalMappingError("producer coverage/schema projection drifted")
    if (
        schema_identity.get("schema_name") != authority.get("schema_name")
        or schema_identity.get("schema_strategy") != authority.get("schema_strategy")
        or schema_identity.get("revision") != authority.get("revision")
        or schema_identity.get("item_count") != len(schema_items)
        or schema_identity.get("counts") != counts
        or schema_identity.get("high_watermark") != max(item.schema_id for item in schema_items)
        or len(schema_items) != authority.get("item_count")
        or counts != authority.get("counts")
        or max(item.schema_id for item in schema_items) != authority.get("high_watermark")
        or schema_identity.get("graph_sha256") != authority.get("graph_sha256")
        or schema_identity.get("ordered_canonical_projection_sha256")
        != _universal_canonical_projection_hash(schema_items)
        or schema_identity.get("ordered_canonical_projection_sha256")
        != authority.get("ordered_canonical_projection_sha256")
        or schema_identity.get("statement_projection_sha256")
        != {statement: projections[statement].projection_sha256 for statement in _STATEMENT_TYPES}
        or schema_identity.get("statement_projection_sha256")
        != authority.get("statement_projection_sha256")
    ):
        raise NativeCanonicalMappingError("producer schema snapshot identity drifted")
    alias_projection = _accepted_alias_projection(accepted_aliases)
    if (
        schema_identity.get("alias_authority") != "CANONICAL_AND_TYPED_ACCEPTED_ALIASES_ONLY"
        or schema_identity.get("accepted_alias_count") != len(accepted_aliases)
        or schema_identity.get("accepted_alias_authority_sha256")
        != stable_records_hash(
            json.dumps(record, ensure_ascii=False, sort_keys=True) for record in alias_projection
        )
        or schema_identity.get("accepted_alias_authority_types")
        != sorted({alias.authority_type for alias in accepted_aliases})
        or schema_identity.get("historical_aliases_loaded") is not False
    ):
        raise NativeCanonicalMappingError("producer accepted-alias identity drifted")
    if _audited_terminal_aggregate_enabled(policy):
        formula_projection = _audited_formula_projection(audited_formulas)
        if (
            schema_identity.get("audited_formula_count") != len(audited_formulas)
            or schema_identity.get("audited_formula_authority_sha256")
            != stable_records_hash(
                json.dumps(record, ensure_ascii=False, sort_keys=True)
                for record in formula_projection
            )
            or schema_identity.get("audited_formula_authority")
            != "HASH_BOUND_APPROVED_BUSINESS_UPDATE_AUDIT_RECORDS"
        ):
            raise NativeCanonicalMappingError("producer audited-formula identity drifted")
    elif any(
        key in schema_identity
        for key in (
            "audited_formula_count",
            "audited_formula_authority_sha256",
            "audited_formula_authority",
        )
    ):
        raise NativeCanonicalMappingError("legacy producer unexpectedly cites formula authority")
    expected_coverage = {
        "target_count": len(coverage.targets),
        "ordered_targets_sha256": coverage.ordered_targets_sha256,
        "minimum_document_schema_coverage": 0,
    }
    if schema_identity.get("coverage") != expected_coverage:
        raise NativeCanonicalMappingError("producer coverage identity drifted")


def _validate_embedded_runtime_ledger(
    inputs: Any,
    *,
    project_root: Path,
    producer_commit: str,
    rows_path: Path,
    rows_sha256: str,
    policy_snapshot: Mapping[str, Any],
    row_payload: Mapping[str, Any],
) -> None:
    if not isinstance(inputs, dict) or set(inputs) != {
        "runtime_read_ledger",
        "runtime_read_ledger_sha256",
    }:
        raise NativeCanonicalMappingError("producer runtime ledger envelope is malformed")
    ledger = inputs["runtime_read_ledger"]
    if (
        not isinstance(ledger, list)
        or any(
            not isinstance(record, dict) or set(record) != {"kind", "path", "sha256", "size_bytes"}
            for record in ledger
        )
        or inputs["runtime_read_ledger_sha256"]
        != stable_records_hash(
            json.dumps(record, ensure_ascii=False, sort_keys=True) for record in ledger
        )
    ):
        raise NativeCanonicalMappingError("producer runtime ledger drifted")
    if len({(record["kind"], record["path"]) for record in ledger}) != len(ledger):
        raise NativeCanonicalMappingError("producer runtime ledger repeats an identity")
    expected = _expected_runtime_ledger_at_commit(
        project_root=project_root,
        producer_commit=producer_commit,
        rows_path=rows_path,
        rows_sha256=rows_sha256,
        policy_snapshot=policy_snapshot,
        row_payload=row_payload,
    )
    if ledger != expected:
        raise NativeCanonicalMappingError(
            "producer runtime ledger inventory or producer-commit identity drifted"
        )


def _committed_runtime_identity(
    project_root: Path,
    producer_commit: str,
    raw_path: str,
    kind: str,
) -> dict[str, Any]:
    raw_path = _canonical_project_relative_path(raw_path, f"{kind} producer path")
    return {
        "kind": kind,
        **_file_identity_at_commit(project_root, producer_commit, raw_path),
    }


def _validate_runtime_record_shape(record: Any, label: str) -> dict[str, Any]:
    if (
        not isinstance(record, dict)
        or set(record) != {"kind", "path", "sha256", "size_bytes"}
        or not isinstance(record.get("kind"), str)
        or not record["kind"]
        or _SHA256.fullmatch(str(record.get("sha256", ""))) is None
        or type(record.get("size_bytes")) is not int
        or record["size_bytes"] < 0
    ):
        raise NativeCanonicalMappingError(f"{label} runtime identity is malformed")
    _canonical_project_relative_path(record.get("path"), f"{label} runtime path")
    return copy.deepcopy(record)


def _expected_runtime_ledger_at_commit(
    *,
    project_root: Path,
    producer_commit: str,
    rows_path: Path,
    rows_sha256: str,
    policy_snapshot: Mapping[str, Any],
    row_payload: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Reconstruct the producer read inventory exclusively from its commit/snapshots."""

    if _GIT_COMMIT.fullmatch(producer_commit) is None:
        raise NativeCanonicalMappingError("runtime-ledger producer commit is invalid")
    if (
        not isinstance(policy_snapshot, Mapping)
        or not isinstance(policy_snapshot.get("path"), str)
        or not isinstance(policy_snapshot.get("source_sha256"), str)
        or not isinstance(policy_snapshot.get("payload"), Mapping)
    ):
        raise NativeCanonicalMappingError("runtime-ledger producer policy snapshot is malformed")
    policy_payload = policy_snapshot["payload"]
    policy_path = _canonical_project_relative_path(
        policy_snapshot["path"], "producer mapping policy"
    )
    committed_policy = _committed_runtime_identity(
        project_root, producer_commit, policy_path, "THIS_POLICY"
    )
    if (
        committed_policy["sha256"] != policy_snapshot["source_sha256"]
        or _yaml_payload_at_commit(project_root, producer_commit, policy_path) != policy_payload
    ):
        raise NativeCanonicalMappingError(
            "runtime-ledger mapping policy differs from producer snapshot"
        )

    authority = policy_payload.get("schema_authority")
    if not isinstance(authority, Mapping):
        raise NativeCanonicalMappingError("producer policy schema authority is malformed")
    source_record = authority.get("source_config")
    hierarchy_record = authority.get("hierarchy_config")
    if not isinstance(source_record, Mapping) or not isinstance(hierarchy_record, Mapping):
        raise NativeCanonicalMappingError("producer schema config identities are malformed")
    source_config_path = _canonical_project_relative_path(
        source_record.get("path"), "producer schema source config"
    )
    hierarchy_config_path = _canonical_project_relative_path(
        hierarchy_record.get("path"), "producer hierarchy config"
    )
    source_config = _yaml_payload_at_commit(project_root, producer_commit, source_config_path)
    hierarchy_config = _yaml_payload_at_commit(project_root, producer_commit, hierarchy_config_path)

    records: list[dict[str, Any]] = [
        {
            "kind": "REGISTERED_NATIVE_STATEMENT_ROWS",
            "path": _relative_path(project_root, rows_path, "native-row artifact"),
            "sha256": rows_sha256,
            "size_bytes": rows_path.stat().st_size,
        },
        committed_policy,
        _committed_runtime_identity(
            project_root,
            producer_commit,
            ROWS_POLICY_RELATIVE_PATH.as_posix(),
            "NATIVE_STATEMENT_ROWS_POLICY",
        ),
    ]
    for raw_path, kind in _schema_runtime_path_specs(
        policy_payload, source_config, hierarchy_config
    ):
        records.append(_committed_runtime_identity(project_root, producer_commit, raw_path, kind))

    # The six policy-pinned schema identities must describe the exact bytes in
    # the producer commit; deriving them from today's schema would make a valid
    # historical artifact unloadable after append-only schema evolution.
    for key in (
        "source_config",
        "hierarchy_config",
        "schema_registry",
        "hierarchy_registry",
        "coverage_config",
        "coverage_registry",
    ):
        pinned = authority.get(key)
        if not isinstance(pinned, Mapping):
            raise NativeCanonicalMappingError(f"producer policy lacks pinned {key}")
        committed = _file_identity_at_commit(
            project_root,
            producer_commit,
            _canonical_project_relative_path(pinned.get("path"), key.replace("_", " ")),
        )
        if committed["sha256"] != pinned.get("sha256"):
            raise NativeCanonicalMappingError(f"producer-commit {key} differs from its policy pin")

    base = source_config.get("base_schema")
    base_workbooks = base.get("workbooks") if isinstance(base, Mapping) else None
    if not isinstance(base_workbooks, Mapping):
        raise NativeCanonicalMappingError("producer BASE_SCHEMA inventory is malformed")
    for statement, workbook in base_workbooks.items():
        if statement not in _STATEMENT_TYPES or not isinstance(workbook, Mapping):
            raise NativeCanonicalMappingError("producer BASE_SCHEMA identity is malformed")
        committed = _file_identity_at_commit(
            project_root,
            producer_commit,
            _canonical_project_relative_path(workbook.get("path"), "producer BASE_SCHEMA workbook"),
        )
        if committed["sha256"] != workbook.get("sha256"):
            raise NativeCanonicalMappingError(
                "producer BASE_SCHEMA workbook differs from its config pin"
            )

    upstream_inputs = row_payload.get("inputs")
    upstream = (
        upstream_inputs.get("runtime_read_ledger") if isinstance(upstream_inputs, Mapping) else None
    )
    upstream_hash = (
        upstream_inputs.get("runtime_read_ledger_sha256")
        if isinstance(upstream_inputs, Mapping)
        else None
    )
    if not isinstance(upstream, list) or upstream_hash != stable_records_hash(
        json.dumps(record, ensure_ascii=False, sort_keys=True) for record in upstream
    ):
        raise NativeCanonicalMappingError("strict native-row upstream ledger is malformed")
    for record in upstream:
        validated = _validate_runtime_record_shape(record, "native-row upstream")
        records.append({**validated, "kind": f"UPSTREAM_{validated['kind']}"})

    records.sort(key=lambda item: (item["kind"], item["path"]))
    if len({(record["kind"], record["path"]) for record in records}) != len(records):
        raise NativeCanonicalMappingError("expected producer runtime inventory repeats an identity")
    return records


def _load_schema_bundle(
    project_root: Path, policy: Mapping[str, Any]
) -> tuple[
    list[SchemaItem],
    dict[str, SchemaProjectionV2],
    SchemaCoverageContract,
    tuple[_AcceptedAlias, ...],
    dict[str, Any],
]:
    authority = policy["schema_authority"]
    source_config_path = _resolve_under_root(
        project_root, authority["source_config"]["path"], "schema source config"
    )
    source_config = yaml.safe_load(source_config_path.read_text(encoding="utf-8")) or {}
    try:
        workbooks, items = load_all(project_root / "template", project_root)
        hierarchy_registry, hierarchy_items = load_hierarchy_reference(
            _resolve_under_root(
                project_root, authority["hierarchy_config"]["path"], "hierarchy config"
            ),
            project_root,
            items,
        )
        apply_hierarchy_reference(items, hierarchy_items)
        accepted_aliases = _load_accepted_alias_authority(
            project_root,
            source_config,
            items,
            hierarchy_registry,
            hierarchy_items,
        )
        audited_formulas = _load_audited_formula_authority(
            project_root,
            source_config,
            items,
        )
        projections = {
            statement: build_schema_projection_v2(items, statement)
            for statement in _STATEMENT_TYPES
        }
        coverage = load_schema_coverage(project_root, schema_items=items)
        contract = load_schema_contract(project_root)
    except (OSError, ValueError) as exc:
        raise NativeCanonicalMappingError("cannot load mapping-safe universal schema") from exc

    registry = _read_json(
        _resolve_under_root(project_root, authority["schema_registry"]["path"], "schema registry"),
        "schema registry",
    )
    registered_hierarchy = _read_json(
        _resolve_under_root(
            project_root, authority["hierarchy_registry"]["path"], "hierarchy registry"
        ),
        "hierarchy registry",
    )
    registered_coverage = _read_json(
        _resolve_under_root(
            project_root, authority["coverage_registry"]["path"], "coverage registry"
        ),
        "coverage registry",
    )
    expected_hierarchy_registry = json.loads(_canonical_json_bytes(hierarchy_registry.to_dict()))
    expected_coverage_registry = json.loads(_canonical_json_bytes(coverage.to_registry()))
    if registered_hierarchy != expected_hierarchy_registry:
        raise NativeCanonicalMappingError("registered hierarchy differs from current source inputs")
    if registered_coverage != expected_coverage_registry:
        raise NativeCanonicalMappingError(
            "registered coverage differs from current universal schema"
        )

    expected_universal = {
        "revision": authority["revision"],
        "item_count": authority["item_count"],
        "counts": authority["counts"],
        "high_watermark": authority["high_watermark"],
    }
    if (
        contract.get("schema_name") != authority["schema_name"]
        or contract.get("schema_strategy") != authority["schema_strategy"]
    ):
        raise NativeCanonicalMappingError("loaded schema strategy differs from mapping policy")
    if contract.get("universal_schema") != expected_universal:
        raise NativeCanonicalMappingError("loaded universal schema revision differs from policy")
    counts = {
        statement: sum(item.statement_type == statement for item in items)
        for statement in _STATEMENT_TYPES
    }
    if (
        len(items) != authority["item_count"]
        or counts != authority["counts"]
        or max(item.schema_id for item in items) != authority["high_watermark"]
    ):
        raise NativeCanonicalMappingError("loaded universal schema denominator drifted")
    workbook_records = [asdict(workbook) for workbook in workbooks]
    universal = registry.get("universal_schema")
    if (
        registry.get("schema_name") != authority["schema_name"]
        or registry.get("schema_strategy") != authority["schema_strategy"]
        or registry.get("total_items") != len(items)
        or registry.get("counts") != counts
        or not isinstance(universal, dict)
        or universal.get("revision") != authority["revision"]
        or universal.get("item_count") != len(items)
        or universal.get("counts") != counts
        or universal.get("high_watermark") != authority["high_watermark"]
        or universal.get("workbooks") != workbook_records
        or registry.get("graph_sha256") != authority["graph_sha256"]
        or universal.get("schema_graph_sha256") != authority["graph_sha256"]
        or universal.get("universal_schema_sha256") != authority["graph_sha256"]
    ):
        raise NativeCanonicalMappingError("registered universal schema identity drifted")
    canonical_hash = _universal_canonical_projection_hash(items)
    if (
        canonical_hash != authority["ordered_canonical_projection_sha256"]
        or universal.get("ordered_canonical_projection_sha256") != canonical_hash
    ):
        raise NativeCanonicalMappingError("universal canonical projection hash drifted")
    expected_projection_hashes = authority["statement_projection_sha256"]
    if any(
        projections[statement].projection_sha256 != expected_projection_hashes[statement]
        for statement in _STATEMENT_TYPES
    ):
        raise NativeCanonicalMappingError("mapping-safe statement projection hash drifted")

    cash_flow_path = source_config.get("cash_flow_rules")
    if not isinstance(cash_flow_path, str):
        raise NativeCanonicalMappingError("universal schema cash-flow rules are absent")
    from bctc_ai.mapping.lctt import load_cash_flow_rules

    try:
        cash_flow_rules = load_cash_flow_rules(
            _resolve_under_root(project_root, cash_flow_path, "cash-flow rules")
        )
    except (OSError, ValueError) as exc:
        raise NativeCanonicalMappingError("cannot load cash-flow method rules") from exc
    identity = {
        "schema_name": authority["schema_name"],
        "schema_strategy": authority["schema_strategy"],
        "revision": authority["revision"],
        "item_count": len(items),
        "counts": counts,
        "high_watermark": authority["high_watermark"],
        "graph_sha256": authority["graph_sha256"],
        "ordered_canonical_projection_sha256": canonical_hash,
        "statement_projection_sha256": {
            statement: projections[statement].projection_sha256 for statement in _STATEMENT_TYPES
        },
        "workbooks": workbook_records,
        "hierarchy": hierarchy_registry.to_dict(),
        "coverage": {
            "target_count": len(coverage.targets),
            "ordered_targets_sha256": coverage.ordered_targets_sha256,
            "minimum_document_schema_coverage": 0,
        },
        "alias_authority": "CANONICAL_AND_TYPED_ACCEPTED_ALIASES_ONLY",
        "accepted_alias_count": len(accepted_aliases),
        "accepted_alias_authority_sha256": stable_records_hash(
            json.dumps(record, ensure_ascii=False, sort_keys=True)
            for record in _accepted_alias_projection(accepted_aliases)
        ),
        "accepted_alias_authority_types": sorted(
            {alias.authority_type for alias in accepted_aliases}
        ),
        "historical_aliases_loaded": False,
        "audited_formula_authority": ("HASH_BOUND_APPROVED_BUSINESS_UPDATE_AUDIT_RECORDS"),
        "audited_formula_count": len(audited_formulas),
        "audited_formula_authority_sha256": stable_records_hash(
            json.dumps(record, ensure_ascii=False, sort_keys=True)
            for record in _audited_formula_projection(audited_formulas)
        ),
    }
    # The evidence is classified after source rows are available. Returning the
    # rules through this private carrier avoids loading a second rule surface.
    identity["_cash_flow_rules"] = cash_flow_rules
    identity["_audited_formulas"] = audited_formulas
    return items, projections, coverage, accepted_aliases, identity


def _source_rows(row_payload: Mapping[str, Any]) -> tuple[_SourceRow, ...]:
    pages = row_payload.get("pages")
    if not isinstance(pages, list) or not pages:
        raise NativeCanonicalMappingError("native-row artifact has no selected pages")
    result: list[_SourceRow] = []
    global_order = 0
    for page in pages:
        if not isinstance(page, dict):
            raise NativeCanonicalMappingError("native-row page record is malformed")
        statement = page.get("statement_type")
        scope = page.get("scope")
        rows = page.get("rows")
        outside = page.get("outside_financial_table_span_rows")
        if (
            statement not in _STATEMENT_TYPES
            or not isinstance(scope, str)
            or not isinstance(rows, list)
            or not isinstance(outside, list)
        ):
            raise NativeCanonicalMappingError("native-row statement/scope block is malformed")
        merged = [(row, True) for row in rows] + [(row, False) for row in outside]

        def row_ordinal(record: tuple[Any, bool]) -> int:
            row = record[0]
            if not isinstance(row, dict) or not isinstance(row.get("row_id"), str):
                raise NativeCanonicalMappingError("native source row is malformed")
            try:
                return int(row["row_id"].rsplit(":row-", 1)[1])
            except (IndexError, ValueError) as exc:
                raise NativeCanonicalMappingError("native source row ordinal is malformed") from exc

        merged.sort(key=row_ordinal)
        for row, within_span in merged:
            if not isinstance(row, dict):
                raise NativeCanonicalMappingError("native source row is malformed")
            global_order += 1
            page_order = row_ordinal((row, within_span))
            result.append(
                _SourceRow(
                    row=copy.deepcopy(row),
                    page_record=page,
                    order=global_order,
                    page_order=page_order,
                    statement_type=statement,
                    scope=scope,
                    within_financial_table_span=within_span,
                )
            )
    row_ids = [item.row_id for item in result]
    expected_count = sum(
        int(page.get("reconstructed_row_count", -1)) for page in pages if isinstance(page, dict)
    )
    if len(result) != expected_count or len(row_ids) != len(set(row_ids)):
        raise NativeCanonicalMappingError("native source-row denominator is inconsistent")
    return tuple(result)


def _active_projection_nodes(
    projection: SchemaProjectionV2,
    *,
    lctt_method: CashFlowEvidence | None,
) -> tuple[SchemaProjectionNodeV2, ...]:
    nodes = tuple(sorted(projection.nodes, key=lambda item: item.display_order))
    if projection.statement_type != "LCTT" or lctt_method is None:
        return nodes
    if lctt_method.method not in {CashFlowMethod.DIRECT, CashFlowMethod.INDIRECT}:
        return nodes
    # Branch metadata was assigned from explicit workbook blocks. The observed
    # label sequence gates cross-branch matching, while NOT_APPLICABLE remains
    # separately gated by semantic_high_confidence_allowed.
    method = lctt_method.method.value
    return tuple(
        node for node in nodes if getattr(node, "statement_type", None) == "LCTT" and method
    )


def _candidate_index(
    projection: SchemaProjectionV2,
    schema_by_id: Mapping[int, SchemaItem],
    *,
    lctt_method: CashFlowEvidence | None,
    accepted_aliases: Sequence[_AcceptedAlias],
) -> tuple[tuple[SchemaProjectionNodeV2, ...], dict[str, tuple[_Candidate, ...]]]:
    nodes = tuple(sorted(projection.nodes, key=lambda item: item.display_order))
    if (
        projection.statement_type == "LCTT"
        and lctt_method is not None
        and lctt_method.semantic_high_confidence_allowed
        and lctt_method.method
        in {
            CashFlowMethod.DIRECT,
            CashFlowMethod.INDIRECT,
        }
    ):
        nodes = tuple(
            node
            for node in nodes
            if schema_by_id[node.report_norm_id].cash_flow_branch == lctt_method.method.value
        )
    index: dict[str, list[_Candidate]] = defaultdict(list)

    def add_variant(
        node: SchemaProjectionNodeV2,
        label: str,
        basis: str,
        alias_authority: _AcceptedAlias | None = None,
    ) -> None:
        raw_key = retrieval_key(label)
        if not raw_key:
            return
        index[raw_key].append(
            _Candidate(
                node.report_norm_id,
                basis,
                label,
                None if alias_authority is None else alias_authority.authority_type,
                (None if alias_authority is None else alias_authority.authority_evidence_sha256),
            )
        )
        expanded_key = _expand_accounting_abbreviations(raw_key)
        if expanded_key != raw_key:
            index[expanded_key].append(
                _Candidate(
                    node.report_norm_id,
                    "ACCEPTED_ACCOUNTING_ABBREVIATION_NORMALIZATION",
                    label,
                    None if alias_authority is None else alias_authority.authority_type,
                    (
                        None
                        if alias_authority is None
                        else alias_authority.authority_evidence_sha256
                    ),
                )
            )

    aliases_by_id: dict[int, list[_AcceptedAlias]] = defaultdict(list)
    node_ids = {node.report_norm_id for node in nodes}
    for alias in accepted_aliases:
        if alias.statement_type != projection.statement_type:
            continue
        if alias.report_norm_id not in node_ids:
            # A typed alias on the proven opposite LCTT branch is valid schema
            # authority but cannot enter this document's candidate path.
            if alias.report_norm_id not in schema_by_id:
                raise NativeCanonicalMappingError("typed alias targets an absent schema item")
            continue
        aliases_by_id[alias.report_norm_id].append(alias)

    for node in nodes:
        canonical_key = retrieval_key(node.canonical_name)
        if not canonical_key:
            raise NativeCanonicalMappingError("schema projection contains a blank canonical key")
        add_variant(node, node.canonical_name, "CANONICAL_RETRIEVAL_KEY_EXACT")
        for accepted_alias in aliases_by_id[node.report_norm_id]:
            structural = _STRUCTURAL_ENUMERATOR.sub("", normalize_text(accepted_alias.alias))
            structural = _TRAILING_FORMULA.sub("", structural)
            alias_key = retrieval_key(structural)
            if not alias_key or alias_key == canonical_key:
                continue
            add_variant(
                node,
                structural,
                "ACCEPTED_STRUCTURAL_ALIAS_RETRIEVAL_KEY_EXACT",
                accepted_alias,
            )
    frozen: dict[str, tuple[_Candidate, ...]] = {}
    display = {node.report_norm_id: node.display_order for node in nodes}
    for key, candidates in index.items():
        by_id: dict[int, _Candidate] = {}
        for candidate in candidates:
            previous = by_id.get(candidate.report_norm_id)
            if previous is None or previous.match_basis.startswith("ACCEPTED_"):
                by_id[candidate.report_norm_id] = candidate
        frozen[key] = tuple(sorted(by_id.values(), key=lambda item: display[item.report_norm_id]))
    return nodes, frozen


def _expand_accounting_abbreviations(key: str) -> str:
    return " ".join(_ACCOUNTING_ABBREVIATIONS.get(token, token) for token in key.split())


def _accepted_alias_index(
    accepted_aliases: Sequence[_AcceptedAlias],
) -> dict[tuple[str, int, str], _AcceptedAlias]:
    result: dict[tuple[str, int, str], _AcceptedAlias] = {}
    for alias in accepted_aliases:
        key = (alias.statement_type, alias.report_norm_id, _structural_alias_key(alias.alias))
        if key in result:
            raise NativeCanonicalMappingError("accepted alias snapshot repeats an item key")
        result[key] = alias
    return result


def _validate_mapping_alias_authority(
    record: Mapping[str, Any],
    source_row: _SourceRow,
    item: SchemaItem,
    accepted_alias_by_key: Mapping[tuple[str, int, str], _AcceptedAlias],
) -> None:
    alias_type = record.get("alias_authority_type")
    alias_hash = record.get("alias_authority_evidence_sha256")
    match_basis = record.get("match_basis")
    matched_label = str(record.get("matched_schema_label") or "")
    typed_alias = accepted_alias_by_key.get(
        (source_row.statement_type, item.schema_id, retrieval_key(matched_label))
    )
    if match_basis == "ACCEPTED_STRUCTURAL_ALIAS_RETRIEVAL_KEY_EXACT":
        if (
            typed_alias is None
            or alias_type != typed_alias.authority_type
            or alias_hash != typed_alias.authority_evidence_sha256
        ):
            raise NativeCanonicalMappingError(
                "accepted alias mapping lacks typed evidence authority"
            )
    elif match_basis == "ACCEPTED_ACCOUNTING_ABBREVIATION_NORMALIZATION":
        if alias_type is None and alias_hash is None:
            if typed_alias is not None and retrieval_key(matched_label) != retrieval_key(
                item.canonical_name
            ):
                raise NativeCanonicalMappingError("alias-derived abbreviation lost typed authority")
        elif (
            typed_alias is None
            or alias_type != typed_alias.authority_type
            or alias_hash != typed_alias.authority_evidence_sha256
        ):
            raise NativeCanonicalMappingError(
                "abbreviation mapping cites the wrong alias authority"
            )
    elif alias_type is not None or alias_hash is not None:
        raise NativeCanonicalMappingError("non-alias mapping cites an alias authority")


def _presentation_scope_compatible(row: _SourceRow, item: SchemaItem) -> bool:
    if row.statement_type != "CDKT":
        return True
    item_is_off_balance = item.notes_section == "OFF_BALANCE_SHEET"
    if row.scope == "OFF_BALANCE_SHEET":
        return item_is_off_balance
    if row.scope == "MAIN_STATEMENT":
        return not item_is_off_balance
    return False


def _lcs_table(
    rows: Sequence[_SourceRow],
    nodes: Sequence[SchemaProjectionNodeV2],
    candidate_ids: Mapping[str, set[int]],
) -> list[list[int]]:
    table = [[0] * (len(nodes) + 1) for _ in range(len(rows) + 1)]
    for row_index, row in enumerate(rows, start=1):
        allowed = candidate_ids[row.row_id]
        for node_index, node in enumerate(nodes, start=1):
            best = max(table[row_index - 1][node_index], table[row_index][node_index - 1])
            if node.report_norm_id in allowed:
                best = max(best, table[row_index - 1][node_index - 1] + 1)
            table[row_index][node_index] = best
    return table


def _suffix_lcs_table(
    rows: Sequence[_SourceRow],
    nodes: Sequence[SchemaProjectionNodeV2],
    candidate_ids: Mapping[str, set[int]],
) -> list[list[int]]:
    table = [[0] * (len(nodes) + 1) for _ in range(len(rows) + 1)]
    for row_index in range(len(rows) - 1, -1, -1):
        allowed = candidate_ids[rows[row_index].row_id]
        for node_index in range(len(nodes) - 1, -1, -1):
            best = max(table[row_index + 1][node_index], table[row_index][node_index + 1])
            if nodes[node_index].report_norm_id in allowed:
                best = max(best, table[row_index + 1][node_index + 1] + 1)
            table[row_index][node_index] = best
    return table


def _resolve_monotone_exact_path(
    rows: Sequence[_SourceRow],
    projection: SchemaProjectionV2,
    schema_by_id: Mapping[int, SchemaItem],
    *,
    lctt_method: CashFlowEvidence | None,
    accepted_aliases: Sequence[_AcceptedAlias],
    allow_value_derived_repeated_parent_detail: bool = True,
) -> _PathResolution:
    nodes, index = _candidate_index(
        projection,
        schema_by_id,
        lctt_method=lctt_method,
        accepted_aliases=accepted_aliases,
    )
    mutable_candidates: dict[str, list[_Candidate]] = {}
    for row in rows:
        if not row.label:
            mutable_candidates[row.row_id] = []
            continue
        raw_key = retrieval_key(row.label)
        expanded_source_key = _expand_accounting_abbreviations(raw_key)
        keys = (raw_key,) if expanded_source_key == raw_key else (raw_key, expanded_source_key)
        by_id: dict[int, _Candidate] = {}
        for key in keys:
            for candidate in index.get(key, ()):
                if not _presentation_scope_compatible(row, schema_by_id[candidate.report_norm_id]):
                    continue
                source_candidate = candidate
                if key != raw_key and candidate.match_basis in {
                    "CANONICAL_RETRIEVAL_KEY_EXACT",
                    "ACCEPTED_STRUCTURAL_ALIAS_RETRIEVAL_KEY_EXACT",
                }:
                    # The schema-side label may already use the expanded words.
                    # In that case the candidate index correctly finds the item,
                    # but the immutable receipt must still disclose that the
                    # source label was transformed before it matched.
                    source_candidate = replace(
                        candidate,
                        match_basis="ACCEPTED_ACCOUNTING_ABBREVIATION_NORMALIZATION",
                    )
                previous = by_id.get(candidate.report_norm_id)
                if previous is None or (
                    previous.match_basis == "ACCEPTED_ACCOUNTING_ABBREVIATION_NORMALIZATION"
                    and source_candidate.match_basis
                    != "ACCEPTED_ACCOUNTING_ABBREVIATION_NORMALIZATION"
                ):
                    by_id[candidate.report_norm_id] = source_candidate
        mutable_candidates[row.row_id] = list(by_id.values())
    source_parents = _infer_source_parent_ids(rows)
    rows_by_id = {row.row_id: row for row in rows}
    nodes_by_id = {node.report_norm_id: node for node in nodes}
    # Some statements print a gross/detail child with exactly the same label as
    # its parent. That is not an alias: the two rows are distinct accounting
    # identities. Admit the detail child only when the visible indentation,
    # complete sibling inventory, and source arithmetic jointly corroborate the
    # direct schema hierarchy. Arithmetic never invents a target on its own.
    for row in rows if allow_value_derived_repeated_parent_detail else ():
        parent_row_id = source_parents[row.row_id]
        if parent_row_id is None or retrieval_key(row.label) != retrieval_key(
            rows_by_id[parent_row_id].label
        ):
            continue
        parent_candidates = {
            candidate.report_norm_id for candidate in mutable_candidates[parent_row_id]
        }
        if len(parent_candidates) != 1:
            continue
        parent_id = next(iter(parent_candidates))
        parent_node = nodes_by_id.get(parent_id)
        if parent_node is None or not parent_node.child_report_norm_ids:
            continue
        parent_tokens = set(retrieval_key(parent_node.canonical_name).split())
        detail_candidates = []
        for child_id in parent_node.child_report_norm_ids:
            child_node = nodes_by_id.get(child_id)
            if child_node is None:
                continue
            child_tokens = set(retrieval_key(child_node.canonical_name).split())
            if parent_tokens <= child_tokens and len(child_tokens - parent_tokens) <= 2:
                detail_candidates.append(child_node)
        if len(detail_candidates) != 1:
            continue
        direct_children = _direct_source_children(rows_by_id[parent_row_id], rows, source_parents)
        if len(direct_children) != len(parent_node.child_report_norm_ids):
            continue
        equation = _sum_equation(
            rows_by_id[parent_row_id],
            direct_children,
            equation_type="REPEATED_PARENT_DETAIL_SOURCE_HIERARCHY",
            complete_structure=True,
        )
        if equation is None or not str(equation["status"]).startswith("PASS"):
            continue
        inferred = detail_candidates[0]
        other_source_rows = [child for child in direct_children if child.row_id != row.row_id]
        other_schema_children = set(parent_node.child_report_norm_ids) - {inferred.report_norm_id}
        if {
            candidate.report_norm_id
            for child in other_source_rows
            for candidate in mutable_candidates[child.row_id]
            if candidate.report_norm_id in other_schema_children
        } != other_schema_children:
            continue
        mutable_candidates[row.row_id].append(
            _Candidate(
                report_norm_id=inferred.report_norm_id,
                match_basis="REPEATED_PARENT_DETAIL_WITH_COMPLETE_HIERARCHY_AND_EQUATION",
                matched_label=inferred.canonical_name,
            )
        )
    all_candidates = {row.row_id: tuple(mutable_candidates[row.row_id]) for row in rows}
    # A shared DIRECT/INDIRECT cash-flow label is not safe mapping authority
    # until the statement method is semantically proven.  Exclude every such
    # row from the path optimization so surrounding monotone anchors cannot
    # silently choose one branch; retain the complete candidates for the
    # explicit AMBIGUOUS disposition and receipt.
    cash_flow_branch_proven = bool(
        projection.statement_type == "LCTT"
        and lctt_method is not None
        and lctt_method.semantic_high_confidence_allowed
        and lctt_method.method in {CashFlowMethod.DIRECT, CashFlowMethod.INDIRECT}
    )
    forced_cross_branch_ambiguity = {
        row_id
        for row_id, candidates in all_candidates.items()
        if projection.statement_type == "LCTT"
        and not cash_flow_branch_proven
        and len(
            {
                schema_by_id[candidate.report_norm_id].cash_flow_branch
                for candidate in candidates
                if schema_by_id[candidate.report_norm_id].cash_flow_branch
                in {CashFlowMethod.DIRECT.value, CashFlowMethod.INDIRECT.value}
            }
        )
        > 1
    }
    candidate_ids = {
        row_id: (
            set()
            if row_id in forced_cross_branch_ambiguity
            else {candidate.report_norm_id for candidate in candidates}
        )
        for row_id, candidates in all_candidates.items()
    }
    prefix = _lcs_table(rows, nodes, candidate_ids)
    suffix = _suffix_lcs_table(rows, nodes, candidate_ids)
    optimum = prefix[-1][-1]
    node_position = {node.report_norm_id: index for index, node in enumerate(nodes)}
    selected: dict[str, _Candidate] = {}
    ambiguous: dict[str, tuple[int, ...]] = {}
    for row_index, row in enumerate(rows):
        if row.row_id in forced_cross_branch_ambiguity:
            ambiguous[row.row_id] = tuple(
                candidate.report_norm_id for candidate in all_candidates[row.row_id]
            )
            continue
        possible: list[_Candidate] = []
        for candidate in all_candidates[row.row_id]:
            position = node_position[candidate.report_norm_id]
            if prefix[row_index][position] + 1 + suffix[row_index + 1][position + 1] == optimum:
                possible.append(candidate)
        skippable = any(
            prefix[row_index][position] + suffix[row_index + 1][position] == optimum
            for position in range(len(nodes) + 1)
        )
        if len(possible) == 1 and not skippable:
            selected[row.row_id] = possible[0]
        elif possible or all_candidates[row.row_id]:
            ambiguous[row.row_id] = tuple(
                candidate.report_norm_id for candidate in possible or all_candidates[row.row_id]
            )
    if len({candidate.report_norm_id for candidate in selected.values()}) != len(selected):
        raise NativeCanonicalMappingError("monotone exact path violates one-to-one mapping")
    ordered_selected = [
        (row.order, schema_by_id[selected[row.row_id].report_norm_id].display_order)
        for row in rows
        if row.row_id in selected
    ]
    if any(
        right[1] <= left[1]
        for left, right in zip(ordered_selected, ordered_selected[1:], strict=False)
    ):
        raise NativeCanonicalMappingError("selected canonical path is not strictly monotone")
    return _PathResolution(selected, ambiguous, all_candidates, optimum)


def _infer_source_parent_ids(rows: Sequence[_SourceRow]) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    page_stack: list[_SourceRow] = []
    active_page: int | None = None
    for row in rows:
        page = int(row.row["page"])
        if page != active_page:
            page_stack = []
            active_page = page
        indentation = float(row.row.get("indentation", 0.0))
        while page_stack and float(page_stack[-1].row.get("indentation", 0.0)) >= indentation - 0.5:
            page_stack.pop()
        result[row.row_id] = page_stack[-1].row_id if page_stack else None
        if row.label:
            page_stack.append(row)
    return result


def _is_distinct_accounting_parent(
    row: _SourceRow,
    rows: Sequence[_SourceRow],
    source_parents: Mapping[str, str | None],
) -> bool:
    """Separate a genuine visible group from repeated/childless layout headings."""

    if not row.label or row.row.get("cells"):
        return False
    key = retrieval_key(row.label)
    same_page_labels = [
        candidate
        for candidate in rows
        if candidate.row.get("page") == row.row.get("page")
        and retrieval_key(candidate.label) == key
    ]
    if len(same_page_labels) != 1:
        return False
    children = _direct_source_children(row, rows, source_parents)
    accounting_children = [
        child
        for child in children
        if child.label
        and (
            bool(child.row.get("cells"))
            or child.row.get("row_type") in {"DATA_ROW", "TOTAL_ROW", "SUBTOTAL_ROW"}
        )
        and retrieval_key(child.label) != key
    ]
    return bool(accounting_children)


def _observed_hierarchy_conflicts(
    rows: Sequence[_SourceRow],
    selected: Mapping[str, _Candidate],
    schema_by_id: Mapping[int, SchemaItem],
    ambiguous: Mapping[str, Sequence[int]] | None = None,
    *,
    allow_compressed_unobserved_intermediates: bool = False,
) -> tuple[dict[str, str | None], list[dict[str, Any]]]:
    parents = _infer_source_parent_ids(rows)
    conflicts: list[dict[str, Any]] = []
    observed_schema_ids = {candidate.report_norm_id for candidate in selected.values()}
    ambiguous_schema_ids = {
        schema_id for candidates in (ambiguous or {}).values() for schema_id in candidates
    }

    def unobserved_intermediate_path(target_id: int, ancestor_id: int) -> tuple[int, ...] | None:
        intermediates: list[int] = []
        seen = {target_id}
        current = schema_by_id[target_id]
        while current.parent_id is not None:
            parent_id = current.parent_id
            if parent_id in seen or parent_id not in schema_by_id:
                raise NativeCanonicalMappingError("schema hierarchy is cyclic or dangling")
            if parent_id == ancestor_id:
                return tuple(reversed(intermediates))
            intermediates.append(parent_id)
            seen.add(parent_id)
            current = schema_by_id[parent_id]
        return None

    for row in rows:
        source_parent_id = parents[row.row_id]
        if row.row_id not in selected or source_parent_id not in selected:
            continue
        target_id = selected[row.row_id].report_norm_id
        target_parent = selected[source_parent_id].report_norm_id
        if schema_by_id[target_id].parent_id == target_parent:
            continue
        intermediates = unobserved_intermediate_path(target_id, target_parent)
        compressed_edge_allowed = (
            allow_compressed_unobserved_intermediates
            and bool(intermediates)
            and not (set(intermediates) & (observed_schema_ids | ambiguous_schema_ids))
        )
        if not compressed_edge_allowed:
            conflicts.append(
                {
                    "conflict_type": "OBSERVED_HIERARCHY_CONFLICT",
                    "affected_row_ids": [row.row_id],
                    "source_parent_row_id": source_parent_id,
                    "candidate_report_norm_ids": [target_id],
                    "candidate_schema_parent_report_norm_id": schema_by_id[target_id].parent_id,
                    "observed_parent_report_norm_id": target_parent,
                    "schema_intermediate_report_norm_ids": (
                        [] if intermediates is None else list(intermediates)
                    ),
                    "resolution": "DEMOTE_AFFECTED_CHILD_TO_AMBIGUOUS",
                }
            )
    return parents, conflicts


def _record_hash(value: Any) -> str:
    return sha256_bytes(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def _row_join(row: _SourceRow, rows_sha256: str) -> dict[str, Any]:
    cells = row.row.get("cells")
    if not isinstance(cells, list):
        raise NativeCanonicalMappingError("source row cell payload is malformed")
    cell_ids = []
    for cell in cells:
        if not isinstance(cell, dict) or cell.get("provenance", {}).get("row_id") != row.row_id:
            raise NativeCanonicalMappingError("source cell cannot be joined to its row")
        axis_id = cell.get("axis_id")
        if not isinstance(axis_id, str) or not axis_id:
            raise NativeCanonicalMappingError("source cell axis identity is invalid")
        cell_ids.append(f"{row.row_id}:{axis_id}")
    if len(cell_ids) != len(set(cell_ids)):
        raise NativeCanonicalMappingError("source row repeats a cell axis")
    return {
        "native_rows_sha256": rows_sha256,
        "row_id": row.row_id,
        "source_row_sha256": _record_hash(row.row),
        "source_cells_sha256": _record_hash(cells),
        "source_cell_ids": cell_ids,
        "source_cell_count": len(cells),
    }


def _nearest_fuzzy_candidates(
    row: _SourceRow,
    projection: SchemaProjectionV2,
    schema_by_id: Mapping[int, SchemaItem],
    *,
    lctt_method: CashFlowEvidence | None,
    accepted_aliases: Sequence[_AcceptedAlias],
    limit: int = 3,
) -> list[dict[str, Any]]:
    key = retrieval_key(row.label)
    if not key:
        return []
    scored: list[tuple[float, int, str, str]] = []
    aliases_by_id: dict[int, list[_AcceptedAlias]] = defaultdict(list)
    for alias in accepted_aliases:
        if alias.statement_type == projection.statement_type:
            aliases_by_id[alias.report_norm_id].append(alias)
    for node in projection.nodes:
        item = schema_by_id[node.report_norm_id]
        if (
            row.statement_type == "LCTT"
            and lctt_method is not None
            and lctt_method.semantic_high_confidence_allowed
            and lctt_method.method in {CashFlowMethod.DIRECT, CashFlowMethod.INDIRECT}
            and item.cash_flow_branch != lctt_method.method.value
        ):
            continue
        if not _presentation_scope_compatible(row, item):
            continue
        variants = (("CANONICAL", node.canonical_name),) + tuple(
            (
                f"ACCEPTED_ALIAS:{alias.authority_type}",
                alias.alias,
            )
            for alias in aliases_by_id[node.report_norm_id]
        )
        best = max(
            (
                ratio(key, retrieval_key(label)) / 100.0,
                kind,
                label,
            )
            for kind, label in variants
            if retrieval_key(label)
        )
        scored.append((best[0], node.report_norm_id, best[1], best[2]))
    scored.sort(key=lambda item: (-item[0], schema_by_id[item[1]].display_order))
    return [
        {
            "report_norm_id": report_norm_id,
            "canonical_name": schema_by_id[report_norm_id].canonical_name,
            "similarity": round(score, 6),
            "diagnostic_variant_kind": kind,
            "diagnostic_variant": label,
            "mapping_authority": False,
        }
        for score, report_norm_id, kind, label in scored[:limit]
    ]


def _alias_proposal(
    row: _SourceRow,
    fuzzy: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any],
) -> dict[str, Any] | None:
    if not fuzzy:
        return None
    mapping = policy["mapping"]
    best = fuzzy[0]
    runner_score = float(fuzzy[1]["similarity"]) if len(fuzzy) > 1 else 0.0
    source_tokens = set(retrieval_key(row.label).split())
    target_tokens = set(retrieval_key(str(best["diagnostic_variant"])).split())
    if (
        float(best["similarity"]) < mapping["alias_proposal_threshold"]
        or float(best["similarity"]) - runner_score < mapping["alias_proposal_minimum_margin"]
        or len(source_tokens ^ target_tokens)
        > mapping["alias_proposal_maximum_token_symmetric_difference"]
    ):
        return None
    raw = normalize_text(str(row.row.get("raw_label", "")))
    target = normalize_text(str(best["diagnostic_variant"]))
    if retrieval_key(raw) == retrieval_key(target):
        proposal_type = "PUNCTUATION"
    elif any(token.isupper() and 1 < len(token) <= 8 for token in raw.split()):
        proposal_type = "ABBREVIATION"
    else:
        proposal_type = "SOURCE_WORDING"
    proposal_key = f"alias-{_record_hash([row.row_id, best['report_norm_id'], raw])[:24]}"
    return {
        "proposal_key": proposal_key,
        "row_id": row.row_id,
        "candidate_report_norm_id": best["report_norm_id"],
        "candidate_canonical_name": best["canonical_name"],
        "proposed_alias": raw,
        "proposal_type": proposal_type,
        "similarity": best["similarity"],
        "runner_up_similarity": round(runner_score, 6),
        "mapping_eligible_this_run": False,
        "status": "PROPOSED_NEEDS_REVIEW",
        "reason": "near wording is recorded separately; same-run alias authority is forbidden",
    }


def _decimal_cells(row: _SourceRow) -> dict[str, Decimal] | None:
    result: dict[str, Decimal] = {}
    cells = row.row.get("cells")
    if not isinstance(cells, list) or not cells:
        return None
    for cell in cells:
        if not isinstance(cell, dict) or cell.get("source_status") not in {
            "OBSERVED_VALUE",
            "OBSERVED_ZERO",
        }:
            return None
        value = cell.get("value")
        axis = cell.get("axis_id")
        if not isinstance(value, str) or not isinstance(axis, str) or axis in result:
            return None
        try:
            result[axis] = Decimal(value)
        except InvalidOperation:
            return None
    return result


def _sum_equation(
    total: _SourceRow,
    components: Sequence[_SourceRow],
    *,
    equation_type: str,
    complete_structure: bool,
) -> dict[str, Any] | None:
    total_values = _decimal_cells(total)
    component_values = [_decimal_cells(component) for component in components]
    if total_values is None or not components or any(values is None for values in component_values):
        return None
    if any(set(values or {}) != set(total_values) for values in component_values):
        return None
    sums = {axis: sum((values or {})[axis] for values in component_values) for axis in total_values}
    residuals = {axis: total_values[axis] - sums[axis] for axis in total_values}
    exact = all(value == 0 for value in residuals.values())
    within_rounding = all(abs(value) <= 1 for value in residuals.values())
    return {
        "equation_type": equation_type,
        "total_row_id": total.row_id,
        "component_row_ids": [component.row_id for component in components],
        "axes": [
            {
                "axis_id": axis,
                "reported_total": str(total_values[axis]),
                "component_sum": str(sums[axis]),
                "residual": str(residuals[axis]),
            }
            for axis in sorted(total_values)
        ],
        "complete_structure": complete_structure,
        "status": (
            "PASS"
            if exact
            else "PASS_WITHIN_ONE_SOURCE_UNIT_ROUNDING"
            if within_rounding
            else "CONFLICT"
        ),
        "mapping_authority": False,
        "use": "CORROBORATION_OR_COMPLETE_STRUCTURE_VETO_ONLY",
    }


def _direct_source_children(
    parent: _SourceRow,
    rows: Sequence[_SourceRow],
    source_parents: Mapping[str, str | None],
) -> list[_SourceRow]:
    return [row for row in rows if source_parents.get(row.row_id) == parent.row_id]


def _equation_evidence(
    rows: Sequence[_SourceRow],
    selected: Mapping[str, _Candidate],
    dispositions_by_row: Mapping[str, str],
    schema_by_id: Mapping[int, SchemaItem],
    source_parents: Mapping[str, str | None],
    *,
    allow_compressed_unobserved_intermediates: bool = False,
    suppressed_unlabeled_total_row_ids: frozenset[str] = frozenset(),
) -> tuple[list[dict[str, Any]], dict[str, list[int]]]:
    equations: list[dict[str, Any]] = []
    equation_indexes_by_row: dict[str, list[int]] = defaultdict(list)
    rows_by_id = {row.row_id: row for row in rows}
    selected_row_by_schema = {
        candidate.report_norm_id: rows_by_id[row_id] for row_id, candidate in selected.items()
    }

    def observed_frontier(schema_id: int, trail: frozenset[int]) -> tuple[int, ...] | None:
        if schema_id in trail:
            raise NativeCanonicalMappingError("schema hierarchy is cyclic")
        if schema_id in selected_row_by_schema:
            return (schema_id,)
        children = tuple(schema_by_id[schema_id].children)
        if not children:
            return None
        frontier: list[int] = []
        for child_id in children:
            branch = observed_frontier(child_id, trail | {schema_id})
            if branch is None:
                return None
            frontier.extend(branch)
        return tuple(frontier)

    for row_id, candidate in selected.items():
        node = schema_by_id[candidate.report_norm_id]
        children = _direct_source_children(rows_by_id[row_id], rows, source_parents)
        mapped_children = [child for child in children if child.row_id in selected]
        if any(
            retrieval_key(child.label).startswith(("trong do", "of which"))
            for child in mapped_children
        ):
            continue
        child_ids = tuple(selected[child.row_id].report_norm_id for child in mapped_children)
        frontier: list[int] = []
        complete = bool(node.children)
        if allow_compressed_unobserved_intermediates:
            for child_id in node.children:
                branch = observed_frontier(child_id, frozenset({node.schema_id}))
                if branch is None:
                    complete = False
                    break
                frontier.extend(branch)
        else:
            frontier.extend(node.children)
        complete = complete and child_ids == tuple(frontier)
        if not complete:
            continue
        direct = child_ids == tuple(node.children)
        equation = _sum_equation(
            rows_by_id[row_id],
            mapped_children,
            equation_type=(
                "MAPPED_PARENT_EQUALS_ALL_MAPPED_SCHEMA_CHILDREN"
                if direct
                else "MAPPED_PARENT_EQUALS_COMPLETE_OBSERVED_SCHEMA_FRONTIER"
            ),
            complete_structure=True,
        )
        if equation is None:
            continue
        if not direct:
            equation["compressed_unobserved_schema_nodes"] = sorted(
                set(node.children) - set(child_ids)
            )
        equations.append(equation)
        index = len(equations) - 1
        equation_indexes_by_row[row_id].append(index)
        for child in mapped_children:
            equation_indexes_by_row[child.row_id].append(index)

    # A visible unlabeled total is never mapped by arithmetic. When its values
    # equal the mapped children of one unobserved schema root, retain that fact
    # as validation evidence while leaving the row UNRESOLVED.
    for row in rows:
        if (
            row.label
            or row.row_id in suppressed_unlabeled_total_row_ids
            or dispositions_by_row.get(row.row_id) != "UNRESOLVED"
        ):
            continue
        same_page = [candidate for candidate in rows if candidate.row["page"] == row.row["page"]]
        groups: dict[int, list[_SourceRow]] = defaultdict(list)
        for candidate_row in same_page:
            mapped = selected.get(candidate_row.row_id)
            if mapped is None:
                continue
            parent_id = schema_by_id[mapped.report_norm_id].parent_id
            if parent_id is not None and parent_id not in selected_row_by_schema:
                groups[parent_id].append(candidate_row)
        for root_id, components in sorted(groups.items()):
            if len(components) < 2:
                continue
            equation = _sum_equation(
                row,
                components,
                equation_type="UNLABELED_TOTAL_EQUALS_UNOBSERVED_SCHEMA_ROOT_CHILDREN",
                complete_structure=(
                    set(schema_by_id[root_id].children)
                    == {selected[item.row_id].report_norm_id for item in components}
                ),
            )
            if equation is None or not str(equation["status"]).startswith("PASS"):
                continue
            equation["unobserved_root_report_norm_id"] = root_id
            equations.append(equation)
            index = len(equations) - 1
            equation_indexes_by_row[row.row_id].append(index)
            for component in components:
                equation_indexes_by_row[component.row_id].append(index)
            break
    return equations, dict(equation_indexes_by_row)


def _common_schema_ancestor(
    left_id: int,
    right_id: int,
    schema_by_id: Mapping[int, SchemaItem],
) -> int | None:
    def path(schema_id: int) -> list[int]:
        result = [schema_id]
        seen = {schema_id}
        current = schema_by_id[schema_id]
        while current.parent_id is not None:
            if current.parent_id in seen or current.parent_id not in schema_by_id:
                raise NativeCanonicalMappingError("schema ancestor path is cyclic or dangling")
            seen.add(current.parent_id)
            result.append(current.parent_id)
            current = schema_by_id[current.parent_id]
        return list(reversed(result))

    common = None
    for left, right in zip(path(left_id), path(right_id), strict=False):
        if left != right:
            break
        common = left
    return common


def _nearest_selected(
    rows: Sequence[_SourceRow],
    index: int,
    selected: Mapping[str, _Candidate],
    *,
    direction: int,
) -> int | None:
    cursor = index + direction
    while 0 <= cursor < len(rows):
        candidate = rows[cursor]
        if candidate.statement_type != rows[index].statement_type:
            break
        if candidate.row_id in selected:
            return selected[candidate.row_id].report_norm_id
        cursor += direction
    return None


def _active_section_parent(
    rows: Sequence[_SourceRow], index: int, selected: Mapping[str, _Candidate]
) -> int | None:
    page = rows[index].row["page"]
    for cursor in range(index - 1, -1, -1):
        candidate = rows[cursor]
        if candidate.row["page"] != page:
            break
        if candidate.row.get("row_type") == "SECTION_HEADER":
            mapped = selected.get(candidate.row_id)
            return None if mapped is None else mapped.report_norm_id
    return None


def _proposal_parent(
    rows: Sequence[_SourceRow],
    index: int,
    selected: Mapping[str, _Candidate],
    proposal_by_row: Mapping[str, dict[str, Any]],
    source_parents: Mapping[str, str | None],
    schema_by_id: Mapping[int, SchemaItem],
) -> dict[str, Any]:
    row = rows[index]
    source_parent = source_parents.get(row.row_id)
    if source_parent in proposal_by_row:
        proposal = proposal_by_row[source_parent]
        return {
            "kind": "NEW_ITEM_PROPOSAL",
            "proposal_key": proposal["proposal_key"],
            "report_norm_id": None,
            "canonical_name": proposal["canonical_label"],
        }
    if source_parent in selected:
        parent_id = selected[source_parent].report_norm_id
        return {
            "kind": "EXISTING_ITEM",
            "proposal_key": None,
            "report_norm_id": parent_id,
            "canonical_name": schema_by_id[parent_id].canonical_name,
        }
    section_parent = _active_section_parent(rows, index, selected)
    if section_parent is not None:
        return {
            "kind": "EXISTING_ITEM",
            "proposal_key": None,
            "report_norm_id": section_parent,
            "canonical_name": schema_by_id[section_parent].canonical_name,
        }
    previous_id = _nearest_selected(rows, index, selected, direction=-1)
    next_id = _nearest_selected(rows, index, selected, direction=1)
    if previous_id is not None and next_id is not None:
        common = _common_schema_ancestor(previous_id, next_id, schema_by_id)
        if common is not None and common not in {previous_id, next_id}:
            return {
                "kind": "EXISTING_ITEM",
                "proposal_key": None,
                "report_norm_id": common,
                "canonical_name": schema_by_id[common].canonical_name,
            }
    return {
        "kind": "UNRESOLVED",
        "proposal_key": None,
        "report_norm_id": None,
        "canonical_name": None,
    }


def _proposal_level(
    parent: Mapping[str, Any],
    proposal_by_key: Mapping[str, Mapping[str, Any]],
    schema_by_id: Mapping[int, SchemaItem],
) -> int | None:
    if parent["kind"] == "EXISTING_ITEM":
        level = schema_by_id[int(parent["report_norm_id"])].hierarchy_level
        return None if level is None else level + 1
    if parent["kind"] == "NEW_ITEM_PROPOSAL":
        proposal = proposal_by_key.get(str(parent["proposal_key"]))
        level = None if proposal is None else proposal.get("hierarchy_level")
        return None if not isinstance(level, int) else level + 1
    return None


def _source_status_for_schema(row: _SourceRow) -> str:
    cells = row.row.get("cells")
    if not isinstance(cells, list) or not cells:
        return "BLANK"
    statuses = {cell.get("source_status") for cell in cells if isinstance(cell, dict)}
    for status in ("OBSERVED_VALUE", "OBSERVED_ZERO", "DASH", "BLANK"):
        if status in statuses:
            return status
    return "UNRESOLVED"


def _accepted_local_or_bounded_contract(
    contract: Mapping[str, Any],
    page_by_number: Mapping[int, Mapping[str, Any]],
) -> bool:
    if contract.get("locally_accepted") is True:
        return (
            contract.get("inferred_from_page") is None
            and contract.get("inference_direction") is None
            and contract.get("inference_checks") == []
        )
    inferred_from = contract.get("inferred_from_page")
    checks = contract.get("inference_checks")
    direction = contract.get("inference_direction")
    if (
        contract.get("locally_accepted") is not False
        or contract.get("scope") != "MAIN_STATEMENT"
        or type(inferred_from) is not int
        or not isinstance(checks, list)
        or not checks
        or any(not isinstance(check, str) or not check for check in checks)
        or direction not in {"FORWARD_FROM_PREVIOUS", "BACKWARD_FROM_NEXT"}
    ):
        return False
    check_set = set(checks)
    base_checks = {"ACCOUNTING_ROWS", "NUMERIC_GEOMETRY", "SHARED_NUMERIC_AXES"}
    compatibility_checks = {
        "SHARED_PERIOD_AXIS",
        "SHARED_UNIT",
        "CONTINUATION_MARKER",
        "TABLE_EDGE_CONTINUITY",
    }
    metadata_or_edge = (
        {"SHARED_PERIOD_AXIS", "SHARED_UNIT"} <= check_set
        or (
            "CONTINUATION_MARKER" in check_set
            and bool({"SHARED_PERIOD_AXIS", "SHARED_UNIT"} & check_set)
        )
        or "TABLE_EDGE_CONTINUITY" in check_set
    )
    page = int(contract["page"])
    expected_direction = (
        "FORWARD_FROM_PREVIOUS"
        if inferred_from == page - 1
        else "BACKWARD_FROM_NEXT"
        if inferred_from == page + 1
        else None
    )
    source = page_by_number.get(inferred_from)
    return bool(
        base_checks <= check_set
        and check_set <= base_checks | compatibility_checks
        and len(check_set) == len(checks)
        and metadata_or_edge
        and direction == expected_direction
        and source is not None
        and source.get("discovery_contract", {}).get("locally_accepted") is True
        and source.get("statement_type") == contract.get("statement_type")
        and source.get("scope") == "MAIN_STATEMENT"
    )


def _observed_blocks(
    row_payload: Mapping[str, Any],
) -> dict[tuple[str, str], tuple[_ObservedBlock, ...]]:
    pages = row_payload.get("pages")
    if not isinstance(pages, list) or not pages:
        raise NativeCanonicalMappingError("native-row artifact has no pages for block audit")
    page_by_number: dict[int, Mapping[str, Any]] = {}
    ordered: list[tuple[int, str, str, Mapping[str, Any]]] = []
    for page in pages:
        if not isinstance(page, dict) or type(page.get("page")) is not int:
            raise NativeCanonicalMappingError("native-row block page identity is malformed")
        page_number = int(page["page"])
        if page_number in page_by_number:
            raise NativeCanonicalMappingError("native-row block repeats a page")
        statement = page.get("statement_type")
        scope = page.get("scope")
        contract = page.get("discovery_contract")
        if (
            statement not in _STATEMENT_TYPES
            or not isinstance(scope, str)
            or not isinstance(contract, dict)
            or contract.get("page") != page_number
            or contract.get("statement_type") != statement
            or contract.get("scope") != scope
        ):
            raise NativeCanonicalMappingError("native-row discovery block contract drifted")
        page_by_number[page_number] = page
        ordered.append((page_number, str(statement), scope, contract))
    ordered.sort(key=lambda record: record[0])
    ordered_position = {record[0]: index for index, record in enumerate(ordered)}

    groups: list[list[tuple[int, str, str, Mapping[str, Any]]]] = []
    for record in ordered:
        if not groups or groups[-1][-1][1:3] != record[1:3]:
            groups.append([record])
        else:
            groups[-1].append(record)

    blocks: dict[tuple[str, str], list[_ObservedBlock]] = defaultdict(list)
    for group in groups:
        statement, scope = group[0][1:3]
        page_numbers = tuple(record[0] for record in group)
        reasons: list[str] = []
        for page_number, _, _, contract in group:
            signals = contract.get("independent_signal_groups")
            if not _accepted_local_or_bounded_contract(contract, page_by_number):
                reasons.append(
                    f"page {page_number} is neither locally accepted nor boundedly inferred"
                )
            if not isinstance(signals, list) or "ACCOUNTING_ROWS" not in signals:
                reasons.append(f"page {page_number} lacks accounting-row evidence")
            page = page_by_number[page_number]
            rows = page.get("rows")
            outside = page.get("outside_financial_table_span_rows")
            reconstructed = page.get("reconstructed_row_count")
            if (
                not isinstance(rows, list)
                or not isinstance(outside, list)
                or type(reconstructed) is not int
                or reconstructed != len(rows) + len(outside)
            ):
                reasons.append(f"page {page_number} row denominator is incomplete")
        for left, right in zip(group, group[1:], strict=False):
            if (
                left[3].get("continuation_to_page") != right[0]
                or right[3].get("continuation_from_page") != left[0]
            ):
                reasons.append(f"internal continuation link {left[0]}->{right[0]} is incomplete")
        first_from = group[0][3].get("continuation_from_page")
        first_position = ordered_position[group[0][0]]
        previous_selected = ordered[first_position - 1] if first_position else None
        if (
            previous_selected is not None
            and previous_selected[1] == statement
            and previous_selected[2] != scope
            and first_from != previous_selected[0]
        ):
            reasons.append("cross-scope block start lacks a reciprocal continuation")
        if first_from is not None:
            previous = page_by_number.get(first_from)
            if (
                previous is None
                or (previous.get("statement_type"), previous.get("scope"))
                == (
                    statement,
                    scope,
                )
                or previous.get("discovery_contract", {}).get("continuation_to_page") != group[0][0]
            ):
                reasons.append("block start is not independently bounded")
        last_to = group[-1][3].get("continuation_to_page")
        last_position = ordered_position[group[-1][0]]
        next_selected = ordered[last_position + 1] if last_position + 1 < len(ordered) else None
        if (
            next_selected is not None
            and next_selected[1] == statement
            and next_selected[2] != scope
            and last_to != next_selected[0]
        ):
            reasons.append("cross-scope block end lacks a reciprocal continuation")
        if last_to is not None:
            following = page_by_number.get(last_to)
            if (
                following is None
                or (following.get("statement_type"), following.get("scope"))
                == (
                    statement,
                    scope,
                )
                or following.get("discovery_contract", {}).get("continuation_from_page")
                != group[-1][0]
            ):
                reasons.append("block end is not independently bounded")
        evidence = {
            "statement": statement,
            "presentation_scope": scope,
            "pages": list(page_numbers),
            "independent_signal_groups_by_page": {
                str(record[0]): list(record[3]["independent_signal_groups"]) for record in group
            },
            "discovery_contract_sha256": _record_hash([record[3] for record in group]),
            "exhaustive": not reasons,
            "reasons": reasons,
        }
        blocks[(statement, scope)].append(
            _ObservedBlock(statement, scope, page_numbers, not reasons, evidence)
        )
    return {key: tuple(value) for key, value in blocks.items()}


def _complete_block(
    blocks: Mapping[tuple[str, str], Sequence[_ObservedBlock]],
    statement: str,
    presentation_scope: str | None,
) -> _ObservedBlock | None:
    if presentation_scope is None:
        return None
    candidates = blocks.get((statement, presentation_scope), ())
    if len(candidates) != 1 or not candidates[0].exhaustive:
        return None
    return candidates[0]


def _promote_audited_terminal_aggregate(
    rows: Sequence[_SourceRow],
    selected: Mapping[str, _Candidate],
    schema_by_id: Mapping[int, SchemaItem],
    audited_formulas: Sequence[_AuditedFormula],
    blocks: Mapping[tuple[str, str], Sequence[_ObservedBlock]],
    blocked_schema_ids: frozenset[int] = frozenset(),
) -> tuple[
    dict[str, _Candidate],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, tuple[int, ...]],
]:
    """Select one terminal unlabeled aggregate from topology, then veto on non-exact arithmetic."""

    value_independent_component_bases = {
        "CANONICAL_RETRIEVAL_KEY_EXACT",
        "ACCEPTED_STRUCTURAL_ALIAS_RETRIEVAL_KEY_EXACT",
        "ACCEPTED_ACCOUNTING_ABBREVIATION_NORMALIZATION",
    }

    selected_row_by_schema = {
        candidate.report_norm_id: row
        for row in rows
        if (candidate := selected.get(row.row_id)) is not None
    }
    selected_schema_ids = set(selected_row_by_schema)

    def descendants(schema_id: int, trail: frozenset[int] = frozenset()) -> tuple[int, ...]:
        if schema_id in trail:
            raise NativeCanonicalMappingError("schema hierarchy is cyclic")
        result: list[int] = []
        for child_id in schema_by_id[schema_id].children:
            result.append(child_id)
            result.extend(descendants(child_id, trail | {schema_id}))
        return tuple(result)

    def numeric_axis_signature(row: _SourceRow) -> tuple[str, ...] | None:
        cells = row.row.get("cells")
        if not isinstance(cells, list) or not cells:
            return None
        axes: list[str] = []
        for cell in cells:
            if (
                not isinstance(cell, dict)
                or cell.get("source_status") not in {"OBSERVED_VALUE", "OBSERVED_ZERO"}
                or not isinstance(cell.get("axis_id"), str)
                or not cell["axis_id"]
            ):
                return None
            axes.append(str(cell["axis_id"]))
        return tuple(axes) if len(axes) == len(set(axes)) else None

    def physical_table_id(row: _SourceRow) -> str | None:
        provenance = row.row.get("provenance")
        cells = row.row.get("cells")
        if not isinstance(provenance, dict) or not isinstance(cells, list):
            return None
        table_id = provenance.get("table_id")
        if not isinstance(table_id, str) or not table_id:
            return None
        for cell in cells:
            cell_provenance = cell.get("provenance") if isinstance(cell, dict) else None
            if (
                not isinstance(cell_provenance, dict)
                or cell_provenance.get("table_id") != table_id
                or cell_provenance.get("row_id") != row.row_id
            ):
                return None
        return table_id

    topology_candidates: list[
        tuple[
            _AuditedFormula, SchemaItem, _SourceRow, tuple[_SourceRow, ...], tuple[_SourceRow, ...]
        ]
    ] = []
    for formula in audited_formulas:
        if formula.operator != "SUM":
            continue
        target = schema_by_id.get(formula.schema_id)
        if (
            target is None
            or target.statement_type != formula.statement_type
            or target.parent_id is None
            or target.hierarchy_level is None
            or target.hierarchy_level <= 0
            or len(formula.component_schema_ids) < 2
            or tuple(target.children) != formula.component_schema_ids
            or target.schema_id in selected_schema_ids
            or target.schema_id in blocked_schema_ids
            or bool(set(formula.component_schema_ids) & blocked_schema_ids)
        ):
            continue
        component_rows = tuple(
            selected_row_by_schema[component_id]
            for component_id in formula.component_schema_ids
            if component_id in selected_row_by_schema
        )
        if len(component_rows) != len(formula.component_schema_ids):
            continue
        if any(
            selected[row.row_id].match_basis not in value_independent_component_bases
            for row in component_rows
        ):
            continue
        scopes = {row.scope for row in component_rows}
        pages = {int(row.row["page"]) for row in component_rows}
        table_ids = {physical_table_id(row) for row in component_rows}
        if len(scopes) != 1 or len(pages) != 1 or None in table_ids or len(table_ids) != 1:
            continue
        scope = next(iter(scopes))
        page = next(iter(pages))
        table_id = next(iter(table_ids))
        block = _complete_block(blocks, formula.statement_type, scope)
        if block is None or page != block.pages[-1]:
            continue
        descendant_ids = set(descendants(target.schema_id))
        descendant_rows = tuple(
            row
            for row in rows
            if row.row_id in selected and selected[row.row_id].report_norm_id in descendant_ids
        )
        if not descendant_rows or any(
            row.statement_type != formula.statement_type
            or row.scope != scope
            or int(row.row["page"]) != page
            or physical_table_id(row) != table_id
            or selected[row.row_id].match_basis not in value_independent_component_bases
            for row in descendant_rows
        ):
            continue
        if target.display_order <= max(
            schema_by_id[selected[row.row_id].report_norm_id].display_order
            for row in descendant_rows
        ):
            continue
        block_rows = tuple(
            row
            for row in rows
            if row.statement_type == formula.statement_type
            and row.scope == scope
            and int(row.row["page"]) in block.pages
        )
        if not block_rows:
            continue
        terminal = block_rows[-1]
        if (
            terminal.label
            or numeric_axis_signature(terminal) is None
            or physical_table_id(terminal) != table_id
        ):
            continue
        terminal_position = len(block_rows) - 1
        interval = block_rows[terminal_position - len(descendant_rows) : terminal_position]
        if (
            terminal_position < len(descendant_rows)
            or tuple(row.row_id for row in interval) != tuple(row.row_id for row in descendant_rows)
            or any(physical_table_id(row) != table_id for row in interval)
            or any(row.order >= terminal.order for row in descendant_rows)
        ):
            continue
        terminal_axes = numeric_axis_signature(terminal)
        if terminal_axes is None or any(
            numeric_axis_signature(row) != terminal_axes for row in descendant_rows
        ):
            continue
        topology_candidates.append((formula, target, terminal, component_rows, descendant_rows))

    # Uniqueness is decided per terminal source row solely from schema topology,
    # audited formula authority, source ordering/scope, and axis shape. Values are
    # inspected only after that candidate set has been frozen.
    grouped: dict[str, list[tuple[Any, ...]]] = defaultdict(list)
    for candidate_record in topology_candidates:
        grouped[candidate_record[2].row_id].append(candidate_record)

    promotions: dict[str, _Candidate] = {}
    receipts: dict[str, dict[str, Any]] = {}
    equations: dict[str, dict[str, Any]] = {}
    ambiguities: dict[str, tuple[int, ...]] = {}
    for terminal_row_id, candidate_records in grouped.items():
        candidate_records.sort(key=lambda record: record[1].display_order)
        pre_value_records = [
            {
                "target_report_norm_id": target.schema_id,
                "statement_type": formula.statement_type,
                "presentation_scope": terminal.scope,
                "physical_table_id": physical_table_id(terminal),
                "block_evidence_sha256": _record_hash(
                    blocks[(formula.statement_type, terminal.scope)][0].evidence
                ),
                "axis_signature": list(numeric_axis_signature(terminal) or ()),
                "target_parent_report_norm_id": target.parent_id,
                "target_hierarchy_level": target.hierarchy_level,
                "target_display_order": target.display_order,
                "direct_child_report_norm_ids": list(formula.component_schema_ids),
                "direct_child_source_row_ids": [row.row_id for row in _component_rows],
                "formula_authority_evidence_sha256": formula.authority_evidence_sha256,
                "terminal_source_row_id": terminal.row_id,
                "contiguous_descendant_source_row_ids": [row.row_id for row in descendant_rows],
            }
            for formula, target, terminal, _component_rows, descendant_rows in candidate_records
        ]
        candidate_set_sha256 = _record_hash(pre_value_records)
        candidate_ids = tuple(record[1].schema_id for record in candidate_records)
        if len(candidate_records) != 1:
            ambiguities[terminal_row_id] = candidate_ids
            receipts[terminal_row_id] = {
                "match_basis": None,
                "selection_status": "AMBIGUOUS_MULTIPLE_PRE_VALUE_TOPOLOGY_CANDIDATES",
                "pre_value_topology_candidate_report_norm_ids": list(candidate_ids),
                "pre_value_topology_candidate_set_sha256": candidate_set_sha256,
                "formula_authorities": [
                    {
                        **copy.deepcopy(formula.authority_evidence),
                        "authority_evidence_sha256": formula.authority_evidence_sha256,
                    }
                    for formula, *_rest in candidate_records
                ],
                "equation_used_for_target_selection": False,
                "equation_used_as_acceptance_gate": False,
                "exact_tolerance_source_units": 0,
                "equation_evidence_index": None,
            }
            continue

        formula, target, terminal, component_rows, descendant_rows = candidate_records[0]
        equation = _sum_equation(
            terminal,
            component_rows,
            equation_type="AUDITED_FORMULA_TERMINAL_AGGREGATE_EXACT_SUM",
            complete_structure=True,
        )
        if equation is not None:
            equation.update(
                {
                    "target_report_norm_id": target.schema_id,
                    "audited_formula_operator": formula.operator,
                    "audited_formula_component_report_norm_ids": list(formula.component_schema_ids),
                    "formula_authority": copy.deepcopy(formula.authority_evidence),
                    "formula_authority_evidence_sha256": (formula.authority_evidence_sha256),
                }
            )
            equations[terminal_row_id] = equation
        accepted = equation is not None and equation.get("status") == "PASS"
        receipts[terminal_row_id] = {
            "match_basis": (_AUDITED_TERMINAL_AGGREGATE_MATCH_BASIS if accepted else None),
            "selection_status": (
                "ACCEPTED_EXACT_EVERY_AXIS" if accepted else "VETOED_NOT_EXACT_EVERY_AXIS"
            ),
            "pre_value_topology_candidate_report_norm_ids": [target.schema_id],
            "pre_value_topology_candidate_set_sha256": candidate_set_sha256,
            "topology": {
                "statement": formula.statement_type,
                "presentation_scope": terminal.scope,
                "page": int(terminal.row["page"]),
                "physical_table_id": physical_table_id(terminal),
                "block_evidence_sha256": _record_hash(
                    blocks[(formula.statement_type, terminal.scope)][0].evidence
                ),
                "axis_signature": list(numeric_axis_signature(terminal) or ()),
                "target_parent_report_norm_id": target.parent_id,
                "target_hierarchy_level": target.hierarchy_level,
                "target_display_order": target.display_order,
                "direct_child_report_norm_ids": list(formula.component_schema_ids),
                "direct_child_source_row_ids": [row.row_id for row in component_rows],
                "contiguous_descendant_source_row_ids": [row.row_id for row in descendant_rows],
                "terminal_source_row_id": terminal.row_id,
                "terminal_unlabeled": True,
                "complete_exhaustive_block": True,
                "unique_topology_candidate_count": 1,
            },
            "formula_authority": copy.deepcopy(formula.authority_evidence),
            "formula_authority_evidence_sha256": formula.authority_evidence_sha256,
            "equation_used_for_target_selection": False,
            "equation_used_as_acceptance_gate": True,
            "dependency_validation_status": (
                "PASS_FROZEN_VALUE_INDEPENDENT_DESCENDANTS_RETAINED"
                if accepted
                else "NOT_RUN_EQUATION_VETOED"
            ),
            "exact_tolerance_source_units": 0,
            "equation_status": None if equation is None else equation["status"],
            "equation_axes": [] if equation is None else copy.deepcopy(equation["axes"]),
            "equation_evidence_index": None,
        }
        if accepted:
            promotions[terminal_row_id] = _Candidate(
                report_norm_id=target.schema_id,
                match_basis=_AUDITED_TERMINAL_AGGREGATE_MATCH_BASIS,
                matched_label=target.canonical_name,
            )
    return promotions, receipts, equations, ambiguities


def _schema_presentation_scopes(
    rows: Sequence[_SourceRow],
    schema_items: Sequence[SchemaItem],
    mapped_row_by_id: Mapping[int, _SourceRow],
) -> dict[int, str]:
    schema_by_id = {item.schema_id: item for item in schema_items}
    assigned: dict[int, str] = {}
    for schema_id, row in mapped_row_by_id.items():
        previous = assigned.get(schema_id)
        if previous is not None and previous != row.scope:
            raise NativeCanonicalMappingError("schema item spans conflicting source scopes")
        assigned[schema_id] = row.scope

    # A parent inherits a presentation scope only when every observed descendant
    # underneath it agrees. This is how an unprinted OFF_BALANCE root is located
    # without inventing a source row.
    changed = True
    while changed:
        changed = False
        for item in schema_items:
            if item.schema_id in assigned or not item.children:
                continue
            observed_children = [child for child in item.children if child in assigned]
            child_scopes = {assigned[child] for child in observed_children}
            if len(observed_children) == len(item.children) and len(child_scopes) == 1:
                assigned[item.schema_id] = next(iter(child_scopes))
                changed = True

    scopes_by_statement: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if row.within_financial_table_span:
            scopes_by_statement[row.statement_type].add(row.scope)
    for statement in _STATEMENT_TYPES:
        statement_items = [item for item in schema_items if item.statement_type == statement]
        observed_scopes = scopes_by_statement.get(statement, set())
        ranges: list[tuple[int, int, str]] = []
        for scope in sorted(observed_scopes):
            orders = [
                schema_by_id[schema_id].display_order
                for schema_id, assigned_scope in assigned.items()
                if assigned_scope == scope and schema_by_id[schema_id].statement_type == statement
            ]
            if orders:
                ranges.append((min(orders), max(orders), scope))
        ranges.sort()
        if any(left[1] >= right[0] for left, right in zip(ranges, ranges[1:], strict=False)):
            raise NativeCanonicalMappingError("source presentation-scope schema ranges overlap")
        for item in statement_items:
            matching = [scope for start, end, scope in ranges if start <= item.display_order <= end]
            if len(matching) > 1:
                raise NativeCanonicalMappingError("schema item has conflicting presentation scopes")
            if matching:
                assigned.setdefault(item.schema_id, matching[0])
    return assigned


def _structural_scope_roots(
    schema_items: Sequence[SchemaItem],
    mapped_row_by_id: Mapping[int, _SourceRow],
    blocks: Mapping[tuple[str, str], Sequence[_ObservedBlock]],
) -> dict[int, _ObservedBlock]:
    schema_by_id = {item.schema_id: item for item in schema_items}
    result: dict[int, _ObservedBlock] = {}
    for statement, scope in blocks:
        block = _complete_block(blocks, statement, scope)
        if block is None or scope == "MAIN_STATEMENT":
            continue
        mapped_ids = sorted(
            schema_id
            for schema_id, row in mapped_row_by_id.items()
            if row.statement_type == statement and row.scope == scope
        )
        if not mapped_ids:
            continue
        ancestor = mapped_ids[0]
        for schema_id in mapped_ids[1:]:
            common = _common_schema_ancestor(ancestor, schema_id, schema_by_id)
            if common is None:
                ancestor = -1
                break
            ancestor = common
        while ancestor > 0 and schema_by_id[ancestor].parent_id is not None:
            ancestor = int(schema_by_id[ancestor].parent_id)
        if (
            ancestor > 0
            and schema_by_id[ancestor].hierarchy_level in {None, 0}
            and ancestor not in mapped_row_by_id
        ):
            result[ancestor] = block
    return result


def _document_reporting_scope(row_payload: Mapping[str, Any]) -> str:
    # This upstream format has no accepted report-title scope binding. Bank and
    # filename wording are expressly forbidden as mapping authority.
    del row_payload
    return "UNKNOWN"


def _schema_disposition_records(
    *,
    row_payload: Mapping[str, Any],
    rows: Sequence[_SourceRow],
    schema_items: Sequence[SchemaItem],
    mapped_row_by_id: Mapping[int, _SourceRow],
    ambiguous_candidate_rows: Mapping[int, Sequence[str]],
    lctt_method: CashFlowEvidence,
) -> list[dict[str, Any]]:
    blocks = _observed_blocks(row_payload)
    assigned_scopes = _schema_presentation_scopes(rows, schema_items, mapped_row_by_id)
    structural_roots = _structural_scope_roots(schema_items, mapped_row_by_id, blocks)
    reporting_scope = _document_reporting_scope(row_payload)
    records: list[dict[str, Any]] = []
    for item in schema_items:
        mapped_row = mapped_row_by_id.get(item.schema_id)
        presentation_scope = assigned_scopes.get(item.schema_id)
        block = _complete_block(blocks, item.statement_type, presentation_scope)
        candidate_rows = sorted(set(ambiguous_candidate_rows.get(item.schema_id, ())))
        scope_evidence: dict[str, Any] | None = None
        if mapped_row is not None:
            # An accepted one-to-one source owner outranks another row that only
            # cites this item as a non-owning ambiguous candidate. Retain those
            # candidate row IDs diagnostically instead of aborting or demoting
            # the observed schema value.
            terminal = _source_status_for_schema(mapped_row)
            source_row_id = mapped_row.row_id
            basis = "SOURCE_ROW"
        elif candidate_rows:
            terminal = "AMBIGUOUS"
            source_row_id = None
            basis = "AMBIGUOUS_SOURCE_CANDIDATE"
        elif item.schema_id in structural_roots:
            structural_block = structural_roots[item.schema_id]
            terminal = "BLANK"
            source_row_id = None
            basis = "OBSERVED_STRUCTURAL_SCOPE_ROOT"
            scope_evidence = copy.deepcopy(structural_block.evidence)
        elif (
            item.statement_type == "LCTT"
            and lctt_method.semantic_high_confidence_allowed
            and lctt_method.method in {CashFlowMethod.DIRECT, CashFlowMethod.INDIRECT}
            and item.cash_flow_branch != lctt_method.method.value
        ):
            terminal = "NOT_APPLICABLE"
            source_row_id = None
            basis = "PROVEN_CASH_FLOW_METHOD"
        elif block is None:
            terminal = "UNRESOLVED"
            source_row_id = None
            basis = "INSUFFICIENT_STATEMENT_SCOPE_EXHAUSTIVENESS"
        elif reporting_scope == "UNKNOWN" and set(item.scope) != {
            "SEPARATE",
            "CONSOLIDATED",
        }:
            terminal = "UNRESOLVED"
            source_row_id = None
            basis = "UNKNOWN_DOCUMENT_REPORTING_SCOPE"
        elif reporting_scope != "UNKNOWN" and reporting_scope not in set(item.scope):
            terminal = "NOT_APPLICABLE"
            source_row_id = None
            basis = "PROVEN_DOCUMENT_REPORTING_SCOPE"
        else:
            terminal = "NOT_OBSERVED"
            source_row_id = None
            basis = "EXHAUSTIVE_STATEMENT_SCOPE_BLOCK_ABSENCE"
        records.append(
            {
                "report_norm_id": item.schema_id,
                "canonical_name": item.canonical_name,
                "statement": item.statement_type,
                "display_order": item.display_order,
                "parent_report_norm_id": item.parent_id,
                "hierarchy_level": item.hierarchy_level,
                "applicable_scope": list(item.scope),
                "document_reporting_scope": reporting_scope,
                "source_statement_scope": presentation_scope,
                "block_exhaustive": block is not None,
                "block_evidence_sha256": (None if block is None else _record_hash(block.evidence)),
                "terminal_outcome": terminal,
                "observation_basis": basis,
                "source_row_id": source_row_id,
                "candidate_source_row_ids": candidate_rows,
                "source_scope_evidence": scope_evidence,
            }
        )
    return records


def _role_b_coverage_evaluation(
    coverage: SchemaCoverageContract,
    document_id: str,
    schema_dispositions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    # evaluate_mandatory_search is reused without fabricating Role-A evidence.
    # A role-scoped derivative is explicit in the receipt and retains the exact
    # universal target denominator and terminal vocabulary.
    role_scoped = replace(coverage, mandatory_search_roles=("ROLE_B",))
    evidence = [
        SchemaSearchEvidence(
            document_id=document_id,
            role="ROLE_B",
            schema_id=int(record["report_norm_id"]),
            terminal_outcome=str(record["terminal_outcome"]),
        )
        for record in schema_dispositions
    ]
    result = evaluate_mandatory_search(role_scoped, document_id, evidence).to_dict()
    result["evaluation_scope"] = "ROLE_B_ONLY_NO_ROLE_A_OUTPUT_LOADED"
    result["source_contract_roles"] = list(coverage.mandatory_search_roles)
    return result


def resolve_native_canonical_mapping(
    row_payload: Mapping[str, Any],
    *,
    rows_sha256: str,
    schema_items: Sequence[SchemaItem],
    projections: Mapping[str, SchemaProjectionV2],
    coverage: SchemaCoverageContract,
    cash_flow_rules: Any,
    accepted_aliases: Sequence[_AcceptedAlias],
    audited_formulas: Sequence[_AuditedFormula] = (),
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve every reconstructed source row without mutating schema authority."""

    if _SHA256.fullmatch(rows_sha256) is None:
        raise NativeCanonicalMappingError("trusted native-row SHA-256 is invalid")
    rows = _source_rows(row_payload)
    mapping_rows = tuple(row for row in rows if row.within_financial_table_span)
    schema_by_id = {item.schema_id: item for item in schema_items}
    if len(schema_by_id) != len(schema_items):
        raise NativeCanonicalMappingError("universal schema contains duplicate ReportNormIds")
    if set(projections) != set(_STATEMENT_TYPES):
        raise NativeCanonicalMappingError("mapping-safe statement projections are incomplete")
    lctt_rows = [row for row in mapping_rows if row.statement_type == "LCTT"]
    lctt_method = (
        classify_cash_flow_method([row.label for row in lctt_rows], cash_flow_rules)
        if lctt_rows
        else CashFlowEvidence(
            CashFlowMethod.UNKNOWN,
            None,
            None,
            "no LCTT block was observed",
            False,
        )
    )

    selected: dict[str, _Candidate] = {}
    ambiguous: dict[str, tuple[int, ...]] = {}
    all_candidates: dict[str, tuple[_Candidate, ...]] = {}
    aggregate_base_selected: dict[str, _Candidate] = {}
    aggregate_base_ambiguous: dict[str, tuple[int, ...]] = {}
    path_summaries: dict[str, Any] = {}
    conflicts: list[dict[str, Any]] = []
    conflict_indexes_by_row: dict[str, list[int]] = defaultdict(list)
    for statement in _STATEMENT_TYPES:
        statement_rows = [row for row in mapping_rows if row.statement_type == statement]
        if not statement_rows:
            path_summaries[statement] = {
                "source_row_count": 0,
                "maximum_cardinality": 0,
                "projection_item_count": len(projections[statement].nodes),
                "projection_sha256": projections[statement].projection_sha256,
            }
            continue
        resolution = _resolve_monotone_exact_path(
            statement_rows,
            projections[statement],
            schema_by_id,
            lctt_method=lctt_method if statement == "LCTT" else None,
            accepted_aliases=accepted_aliases,
        )
        if _audited_terminal_aggregate_enabled(policy):
            base_resolution = _resolve_monotone_exact_path(
                statement_rows,
                projections[statement],
                schema_by_id,
                lctt_method=lctt_method if statement == "LCTT" else None,
                accepted_aliases=accepted_aliases,
                allow_value_derived_repeated_parent_detail=False,
            )
            aggregate_base_selected.update(base_resolution.selected)
            aggregate_base_ambiguous.update(base_resolution.ambiguous)
        selected.update(resolution.selected)
        ambiguous.update(resolution.ambiguous)
        all_candidates.update(resolution.all_candidates)
        path_summaries[statement] = {
            "source_row_count": len(statement_rows),
            "maximum_cardinality": resolution.maximum_cardinality,
            "projection_item_count": len(projections[statement].nodes),
            "projection_sha256": projections[statement].projection_sha256,
        }
        _, hierarchy_conflicts = _observed_hierarchy_conflicts(
            statement_rows,
            resolution.selected,
            schema_by_id,
            resolution.ambiguous,
            allow_compressed_unobserved_intermediates=_compressed_hierarchy_enabled(policy),
        )
        for conflict in hierarchy_conflicts:
            row_id = str(conflict["affected_row_ids"][0])
            selected_candidate = selected.pop(row_id)
            ambiguous[row_id] = tuple(
                sorted(set(ambiguous.get(row_id, ())) | {selected_candidate.report_norm_id})
            )
            conflicts.append(conflict)
            conflict_indexes_by_row[row_id].append(len(conflicts) - 1)
        path_summaries[statement]["localized_hierarchy_conflict_count"] = len(hierarchy_conflicts)

    rows_by_id = {row.row_id: row for row in rows}
    source_parents = _infer_source_parent_ids(mapping_rows)
    source_parents.update({row.row_id: None for row in rows if not row.within_financial_table_span})
    aggregate_receipts: dict[str, dict[str, Any]] = {}
    aggregate_equations: dict[str, dict[str, Any]] = {}
    promotions: dict[str, _Candidate] = {}
    value_independent_selected: dict[str, _Candidate] = {}
    if _audited_terminal_aggregate_enabled(policy):
        for summary in path_summaries.values():
            summary["post_path_audited_terminal_aggregate_promotion_count"] = 0
        value_independent_selected = {
            row_id: candidate
            for row_id, candidate in aggregate_base_selected.items()
            if selected.get(row_id) == candidate
        }
        promotions, aggregate_receipts, aggregate_equations, aggregate_ambiguities = (
            _promote_audited_terminal_aggregate(
                mapping_rows,
                value_independent_selected,
                schema_by_id,
                audited_formulas,
                _observed_blocks(row_payload),
                frozenset(
                    schema_id
                    for candidate_ids in (
                        *ambiguous.values(),
                        *aggregate_base_ambiguous.values(),
                    )
                    for schema_id in candidate_ids
                ),
            )
        )
        for row_id, candidate_ids in aggregate_ambiguities.items():
            ambiguous[row_id] = candidate_ids
        for row_id, receipt in aggregate_receipts.items():
            if row_id in promotions or row_id in aggregate_ambiguities:
                continue
            all_candidates[row_id] = tuple(
                _Candidate(
                    report_norm_id=schema_id,
                    match_basis="AUDITED_FORMULA_TERMINAL_AGGREGATE_TOPOLOGY_CANDIDATE",
                    matched_label=schema_by_id[schema_id].canonical_name,
                )
                for schema_id in receipt["pre_value_topology_candidate_report_norm_ids"]
            )
        for row_id, candidate in promotions.items():
            if row_id in selected or candidate.report_norm_id in {
                value.report_norm_id for value in selected.values()
            }:
                raise NativeCanonicalMappingError(
                    "post-path aggregate promotion violates one-to-one mapping"
                )
            selected[row_id] = candidate
            all_candidates[row_id] = (candidate,)
            path_summaries[rows_by_id[row_id].statement_type][
                "post_path_audited_terminal_aggregate_promotion_count"
            ] += 1
        if len({candidate.report_norm_id for candidate in selected.values()}) != len(selected):
            raise NativeCanonicalMappingError(
                "post-path aggregate promotion violates one-to-one mapping"
            )
        for statement in _STATEMENT_TYPES:
            ordered = [
                (
                    row.order,
                    schema_by_id[selected[row.row_id].report_norm_id].display_order,
                )
                for row in mapping_rows
                if row.statement_type == statement and row.row_id in selected
            ]
            if any(right[1] <= left[1] for left, right in zip(ordered, ordered[1:], strict=False)):
                raise NativeCanonicalMappingError(
                    "post-path aggregate promotion violates strict monotonicity"
                )
    dispositions_by_row: dict[str, str] = {}
    alias_proposals: list[dict[str, Any]] = []
    fuzzy_by_row: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not row.within_financial_table_span:
            dispositions_by_row[row.row_id] = "UNRESOLVED"
        elif row.row_id in selected:
            dispositions_by_row[row.row_id] = "EXISTING_ITEM"
        elif row.row_id in ambiguous:
            dispositions_by_row[row.row_id] = "AMBIGUOUS"
        elif not row.label:
            dispositions_by_row[row.row_id] = "UNRESOLVED"
        elif row.row.get("row_type") == "SECTION_HEADER" or not row.row.get("cells"):
            dispositions_by_row[row.row_id] = (
                "NEW_ITEM_PROPOSAL"
                if _is_distinct_accounting_parent(row, mapping_rows, source_parents)
                else "STRUCTURAL"
            )
        else:
            fuzzy = _nearest_fuzzy_candidates(
                row,
                projections[row.statement_type],
                schema_by_id,
                lctt_method=lctt_method if row.statement_type == "LCTT" else None,
                accepted_aliases=accepted_aliases,
            )
            fuzzy_by_row[row.row_id] = fuzzy
            alias = _alias_proposal(row, fuzzy, policy)
            if alias is not None:
                alias_proposals.append(alias)
                ambiguous[row.row_id] = (int(alias["candidate_report_norm_id"]),)
                dispositions_by_row[row.row_id] = "AMBIGUOUS"
            else:
                dispositions_by_row[row.row_id] = "NEW_ITEM_PROPOSAL"

    equations, equation_indexes = _equation_evidence(
        mapping_rows,
        selected,
        dispositions_by_row,
        schema_by_id,
        source_parents,
        allow_compressed_unobserved_intermediates=_compressed_hierarchy_enabled(policy),
        suppressed_unlabeled_total_row_ids=frozenset(aggregate_receipts),
    )
    for row_id, equation in aggregate_equations.items():
        equations.append(equation)
        equation_index = len(equations) - 1
        equation_indexes.setdefault(row_id, []).append(equation_index)
        aggregate_receipts[row_id]["equation_evidence_index"] = equation_index
        for component_row_id in equation["component_row_ids"]:
            equation_indexes.setdefault(str(component_row_id), []).append(equation_index)
    for equation_index, equation in enumerate(equations):
        if (
            equation.get("equation_type") == "AUDITED_FORMULA_TERMINAL_AGGREGATE_EXACT_SUM"
            or equation.get("status") != "CONFLICT"
            or equation.get("complete_structure") is not True
        ):
            continue
        affected = [
            str(equation["total_row_id"]),
            *(str(row_id) for row_id in equation["component_row_ids"]),
        ]
        candidate_ids: list[int] = []
        for row_id in affected:
            candidate = selected.pop(row_id, None)
            if candidate is None:
                continue
            candidate_ids.append(candidate.report_norm_id)
            ambiguous[row_id] = tuple(
                sorted(set(ambiguous.get(row_id, ())) | {candidate.report_norm_id})
            )
            dispositions_by_row[row_id] = "AMBIGUOUS"
        if not candidate_ids:
            continue
        conflict = {
            "conflict_type": "COMPLETE_STRUCTURE_EQUATION_CONFLICT",
            "affected_row_ids": affected,
            "candidate_report_norm_ids": sorted(candidate_ids),
            "equation_evidence_index": equation_index,
            "resolution": "DEMOTE_AFFECTED_MAPPINGS_TO_AMBIGUOUS",
        }
        conflicts.append(conflict)
        conflict_index = len(conflicts) - 1
        for row_id in affected:
            conflict_indexes_by_row[row_id].append(conflict_index)
    for row_id, promoted_candidate in promotions.items():
        receipt = aggregate_receipts[row_id]
        topology = receipt["topology"]
        dependency_row_ids = tuple(
            dict.fromkeys(
                [
                    *topology["direct_child_source_row_ids"],
                    *topology["contiguous_descendant_source_row_ids"],
                ]
            )
        )
        dependencies_retained = all(
            dependency_row_id in selected
            and selected[dependency_row_id] == value_independent_selected.get(dependency_row_id)
            for dependency_row_id in dependency_row_ids
        )
        if dependencies_retained and selected.get(row_id) == promoted_candidate:
            continue
        receipt["match_basis"] = None
        receipt["selection_status"] = "VETOED_DEPENDENCY_MAPPING_DEMOTED"
        receipt["dependency_validation_status"] = (
            "FAIL_FROZEN_VALUE_INDEPENDENT_DESCENDANT_NOT_RETAINED"
        )
        if selected.get(row_id) == promoted_candidate:
            selected.pop(row_id)
            dispositions_by_row[row_id] = "UNRESOLVED"
        path_summaries[rows_by_id[row_id].statement_type][
            "post_path_audited_terminal_aggregate_promotion_count"
        ] -= 1
    new_item_proposals: list[dict[str, Any]] = []
    proposal_by_row: dict[str, dict[str, Any]] = {}
    proposal_by_key: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        if dispositions_by_row[row.row_id] != "NEW_ITEM_PROPOSAL":
            continue
        parent = _proposal_parent(
            rows,
            index,
            selected,
            proposal_by_row,
            source_parents,
            schema_by_id,
        )
        proposal_key = f"schema-gap-{_record_hash([rows_sha256, row.row_id, row.label])[:24]}"
        previous_id = _nearest_selected(rows, index, selected, direction=-1)
        next_id = _nearest_selected(rows, index, selected, direction=1)
        child_rows = _direct_source_children(row, mapping_rows, source_parents)
        source_equation = _sum_equation(
            row,
            child_rows,
            equation_type="PROPOSED_PARENT_EQUALS_VISIBLE_SOURCE_CHILDREN",
            complete_structure=False,
        )
        proposal = {
            "proposal_key": proposal_key,
            "status": "PROPOSED_NEEDS_USER_REVIEW",
            "report_norm_id": None,
            "canonical_label": row.label,
            "statement": row.statement_type,
            "section": parent.get("canonical_name"),
            "parent": parent,
            "hierarchy_level": _proposal_level(parent, proposal_by_key, schema_by_id),
            "display_order_anchors": {
                "insert_after_report_norm_id": previous_id,
                "insert_before_report_norm_id": next_id,
            },
            "source_evidence": {
                "row_id": row.row_id,
                "page": row.row["page"],
                "visible_label": row.row.get("raw_label"),
                "note_reference": row.row.get("note_reference"),
                "values": [
                    {
                        "axis_id": cell["axis_id"],
                        "raw_text": cell["raw_text"],
                        "value": cell["value"],
                        "source_status": cell["source_status"],
                    }
                    for cell in row.row["cells"]
                ],
                "previous_mapped_report_norm_id": previous_id,
                "next_mapped_report_norm_id": next_id,
                "visible_source_parent_row_id": source_parents.get(row.row_id),
            },
            "reason_existing_items_are_insufficient": (
                "no canonical or accepted structural alias has an exact accounting-label key; "
                "the visible accounting row/group is preserved as a schema-gap proposal, never "
                "force-mapped"
            ),
            "nearest_existing_candidates_diagnostic_only": fuzzy_by_row.get(row.row_id, []),
            "equation_evidence": source_equation,
            "possible_aliases": [],
            "allocation_authority": False,
        }
        new_item_proposals.append(proposal)
        proposal_by_row[row.row_id] = proposal
        proposal_by_key[proposal_key] = proposal

    dispositions: list[dict[str, Any]] = []
    for row in rows:
        status = dispositions_by_row[row.row_id]
        match = selected.get(row.row_id)
        candidate_ids = (
            [candidate.report_norm_id for candidate in all_candidates.get(row.row_id, ())]
            if status != "AMBIGUOUS"
            else list(ambiguous.get(row.row_id, ()))
        )
        target = None if match is None else schema_by_id[match.report_norm_id]
        dispositions.append(
            {
                "row_id": row.row_id,
                "source_order": row.order,
                "page": row.row["page"],
                "page_row_order": row.page_order,
                "statement": row.statement_type,
                "scope": row.scope,
                "within_financial_table_span": row.within_financial_table_span,
                "row_type": row.row.get("row_type"),
                "raw_label": row.row.get("raw_label"),
                "normalized_label": row.label,
                "indentation": row.row.get("indentation"),
                "disposition": status,
                "selected_report_norm_id": None if match is None else match.report_norm_id,
                "selected_canonical_name": None if target is None else target.canonical_name,
                "candidate_report_norm_ids": candidate_ids,
                "match_basis": None if match is None else match.match_basis,
                "matched_schema_label": None if match is None else match.matched_label,
                "alias_authority_type": (None if match is None else match.alias_authority_type),
                "alias_authority_evidence_sha256": (
                    None if match is None else match.alias_authority_evidence_sha256
                ),
                "source_parent_row_id": source_parents.get(row.row_id),
                "schema_parent_report_norm_id": None if target is None else target.parent_id,
                "schema_hierarchy_level": None if target is None else target.hierarchy_level,
                "schema_display_order": None if target is None else target.display_order,
                "equation_evidence_indexes": equation_indexes.get(row.row_id, []),
                **(
                    {"aggregate_match_receipt": aggregate_receipts.get(row.row_id)}
                    if _audited_terminal_aggregate_enabled(policy)
                    else {}
                ),
                "conflict_evidence_indexes": conflict_indexes_by_row.get(row.row_id, []),
                "source_cell_join": _row_join(row, rows_sha256),
                "reason": {
                    "EXISTING_ITEM": (
                        "audited formula plus unique terminal aggregate topology, with exact "
                        "per-axis arithmetic corroboration"
                        if match is not None
                        and match.match_basis == _AUDITED_TERMINAL_AGGREGATE_MATCH_BASIS
                        else "accepted history-free schema label plus unique monotone path"
                    ),
                    "NEW_ITEM_PROPOSAL": (
                        "visible accounting row/group has no authorized exact item"
                    ),
                    "AMBIGUOUS": "more than one safe interpretation remains; no mapping selected",
                    "UNRESOLVED": (
                        "source row is outside the accepted financial-table span or lacks a label "
                        "that can establish accounting identity"
                    ),
                    "STRUCTURAL": (
                        "visible repeated or childless heading has no accepted schema identity"
                    ),
                }[status],
            }
        )

    if [record["row_id"] for record in dispositions] != [row.row_id for row in rows]:
        raise NativeCanonicalMappingError("source disposition order/denominator drifted")
    if len(dispositions) != len({record["row_id"] for record in dispositions}):
        raise NativeCanonicalMappingError("source row received more than one disposition")
    selected_ids = [
        record["selected_report_norm_id"]
        for record in dispositions
        if record["disposition"] == "EXISTING_ITEM"
    ]
    if len(selected_ids) != len(set(selected_ids)):
        raise NativeCanonicalMappingError("canonical item was assigned to multiple source rows")
    if any(
        record["selected_report_norm_id"] is not None
        for record in dispositions
        if record["disposition"] != "EXISTING_ITEM"
    ):
        raise NativeCanonicalMappingError("non-existing disposition accidentally grants an ID")

    mapped_row_by_id = {
        int(record["selected_report_norm_id"]): rows_by_id[str(record["row_id"])]
        for record in dispositions
        if record["disposition"] == "EXISTING_ITEM"
    }
    ambiguous_candidate_rows: dict[int, list[str]] = defaultdict(list)
    for row_id, candidate_ids in ambiguous.items():
        for candidate_id in candidate_ids:
            ambiguous_candidate_rows[candidate_id].append(row_id)
    schema_dispositions = _schema_disposition_records(
        row_payload=row_payload,
        rows=rows,
        schema_items=schema_items,
        mapped_row_by_id=mapped_row_by_id,
        ambiguous_candidate_rows=ambiguous_candidate_rows,
        lctt_method=lctt_method,
    )
    if len(schema_dispositions) != len(schema_items):
        raise NativeCanonicalMappingError("universal schema disposition denominator drifted")
    mandatory = _role_b_coverage_evaluation(
        coverage,
        str(row_payload["source"]["document_id"]),
        schema_dispositions,
    )
    if mandatory["status"] != "PASS":
        raise NativeCanonicalMappingError("Role-B universal mandatory search is incomplete")
    disposition_counts = Counter(record["disposition"] for record in dispositions)
    if set(disposition_counts) - set(_DISPOSITIONS):
        raise NativeCanonicalMappingError("unknown source disposition was emitted")
    accounted = sum(disposition_counts.values())
    summary = {
        "visible_source_items": len(rows),
        "financial_table_span_source_items": len(mapping_rows),
        "outside_financial_table_span_source_items": len(rows) - len(mapping_rows),
        "mapped_to_existing_canonical_items": disposition_counts["EXISTING_ITEM"],
        "new_schema_item_proposals": disposition_counts["NEW_ITEM_PROPOSAL"],
        "ambiguous": disposition_counts["AMBIGUOUS"],
        "unresolved": disposition_counts["UNRESOLVED"],
        "structural": disposition_counts["STRUCTURAL"],
        "source_items_successfully_accounted_for": accounted,
        "source_item_accounting_denominator": len(rows),
        "source_disposition_counts": {
            status: disposition_counts[status] for status in _DISPOSITIONS
        },
        "alias_proposal_count": len(alias_proposals),
        "equation_count": len(equations),
        "localized_conflict_count": len(conflicts),
        "universal_schema_item_count": len(schema_items),
        "universal_schema_counts": {
            statement: sum(item.statement_type == statement for item in schema_items)
            for statement in _STATEMENT_TYPES
        },
    }
    if accounted != len(rows):
        raise NativeCanonicalMappingError("not every visible source item was accounted for")
    return {
        "lctt_method": {
            "method": lctt_method.method.value,
            "indirect_anchor_positions": lctt_method.indirect_anchor_positions,
            "direct_anchor_positions": lctt_method.direct_anchor_positions,
            "reason": lctt_method.reason,
            "semantic_high_confidence_allowed": lctt_method.semantic_high_confidence_allowed,
            "opposite_branch_not_applicable_applied": bool(
                lctt_method.semantic_high_confidence_allowed
                and lctt_method.method in {CashFlowMethod.DIRECT, CashFlowMethod.INDIRECT}
            ),
        },
        "path_summaries": path_summaries,
        "source_dispositions": dispositions,
        "new_item_proposals": new_item_proposals,
        "alias_proposals": alias_proposals,
        "equations": equations,
        "conflicts": conflicts,
        "schema_dispositions": schema_dispositions,
        "mandatory_search": mandatory,
        "summary": summary,
    }


def build_registered_native_canonical_mapping(
    project_root: Path,
    rows_path: Path,
    rows_sha256: str,
    policy_path: Path,
    rows_policy_path: Path,
    run_id: str,
    git_state: Mapping[str, Any],
) -> dict[str, Any]:
    project_root = project_root.resolve()
    rows_path = rows_path.resolve()
    policy_path = policy_path.resolve()
    rows_policy_path = rows_policy_path.resolve()
    if not isinstance(run_id, str) or _SAFE_RUN_ID.fullmatch(run_id) is None:
        raise NativeCanonicalMappingError("native canonical run_id is invalid")
    if _SHA256.fullmatch(rows_sha256) is None:
        raise NativeCanonicalMappingError("trusted native-row SHA-256 is invalid")
    code = _validate_git_state(dict(git_state))
    initial_policy_identity = _identity(policy_path, project_root, "THIS_POLICY")
    policy = load_native_canonical_mapping_policy(policy_path, project_root)
    try:
        row_payload = load_registered_native_statement_rows(
            rows_path,
            project_root=project_root,
            expected_sha256=rows_sha256,
            policy_path=rows_policy_path,
        )
    except Exception as exc:
        raise NativeCanonicalMappingError("registered native-row input failed strict load") from exc
    role = row_payload.get("source", {}).get("dataset_role")
    if role not in _ALLOWED_ROLES:
        raise NativeCanonicalMappingError("native-row dataset role is not mapping-eligible")
    allowed_directory = (project_root / _ROLE_DIRECTORIES[str(role)]).resolve()
    try:
        rows_path.relative_to(allowed_directory)
    except ValueError as exc:
        raise NativeCanonicalMappingError(
            "native-row artifact is in the wrong role directory"
        ) from exc

    runtime_inputs = _runtime_ledger(
        project_root,
        rows_path,
        policy_path,
        rows_policy_path,
        policy,
        row_payload,
    )
    if (
        next(record for record in runtime_inputs if record["kind"] == "THIS_POLICY")
        != initial_policy_identity
    ):
        raise NativeCanonicalMappingError("native canonical policy changed while loading")
    implementation = _implementation_ledger(project_root)
    items, projections, coverage, accepted_aliases, schema_identity = _load_schema_bundle(
        project_root, policy
    )
    cash_flow_rules = schema_identity.pop("_cash_flow_rules")
    audited_formulas = schema_identity.pop("_audited_formulas")
    producer_snapshots = _producer_snapshots(
        project_root=project_root,
        policy_path=policy_path,
        policy=policy,
        schema_items=items,
        accepted_aliases=accepted_aliases,
        audited_formulas=audited_formulas,
        coverage=coverage,
        cash_flow_rules=cash_flow_rules,
    )
    resolved = resolve_native_canonical_mapping(
        row_payload,
        rows_sha256=rows_sha256,
        schema_items=items,
        projections=projections,
        coverage=coverage,
        cash_flow_rules=cash_flow_rules,
        accepted_aliases=accepted_aliases,
        audited_formulas=audited_formulas,
        policy=policy,
    )
    final_runtime_inputs = _runtime_ledger(
        project_root,
        rows_path,
        policy_path,
        rows_policy_path,
        policy,
        row_payload,
    )
    if final_runtime_inputs != runtime_inputs:
        raise NativeCanonicalMappingError("native canonical runtime inputs changed during mapping")
    if _implementation_ledger(project_root) != implementation:
        raise NativeCanonicalMappingError("native canonical implementation changed during mapping")

    rows_relative = _relative_path(project_root, rows_path, "native-row artifact")
    source = copy.deepcopy(row_payload["source"])
    payload: dict[str, Any] = {
        "format_version": _OUTPUT_FORMAT,
        "policy": _POLICY_NAME,
        "claim_boundary": _CLAIM_BOUNDARY,
        "status": _OUTPUT_STATUS,
        "run_id": run_id,
        "source": source,
        "native_rows": {
            "path": rows_relative,
            "sha256": rows_sha256,
            "size_bytes": rows_path.stat().st_size,
            "format_version": row_payload["format_version"],
            "policy": row_payload["policy"],
            "claim_boundary": row_payload["claim_boundary"],
            "status": row_payload["status"],
            "run_id": row_payload["run_id"],
            "producer_git_commit": row_payload["code"]["commit"],
            "denominator": "ALL_RECONSTRUCTED_SOURCE_ROWS",
        },
        "schema": schema_identity,
        "producer_snapshots": producer_snapshots,
        "code": {**code, "implementation": implementation},
        "authority": {
            "canonical_labels": "CURRENT_UNIVERSAL_SCHEMA_WORKBOOKS",
            "aliases": "CURRENT_TYPED_ACCEPTED_ALIAS_AUTHORITY_ONLY",
            "ordering": "WORKBOOK_DISPLAY_ORDER",
            "hierarchy": "CURRENT_VALIDATED_SCHEMA_GRAPH",
            **(
                {"business_formulas": ("HASH_BOUND_APPROVED_BUSINESS_UPDATE_AUDIT_RECORDS")}
                if _audited_terminal_aggregate_enabled(policy)
                else {}
            ),
            "source_rows_and_cells": "TRUSTED_REGISTERED_NATIVE_ROWS_SHA256_JOIN",
            "historical_values": None,
            "role_a": None,
            "human_review": None,
        },
        "isolation": {
            "prior_answer_artifacts_loaded": False,
            "historical_values_loaded": False,
            "historical_aliases_loaded": False,
            "role_a_outputs_loaded": False,
            "human_review_outputs_loaded": False,
            "bank_identity_used_for_mapping": False,
            "filename_identity_used_for_mapping": False,
            "page_number_rules_used_for_mapping": False,
            "source_row_count_rules_used_for_mapping": False,
            "same_run_alias_proposals_mapping_eligible": False,
            "new_item_proposals_allocate_report_norm_id": False,
        },
        "inputs": {
            "runtime_read_ledger": runtime_inputs,
            "runtime_read_ledger_sha256": stable_records_hash(
                json.dumps(record, ensure_ascii=False, sort_keys=True) for record in runtime_inputs
            ),
        },
        **resolved,
    }
    return json.loads(_canonical_json_bytes(payload))


def _validate_loaded_mapping(
    payload: Mapping[str, Any],
    *,
    row_payload: Mapping[str, Any],
    rows_sha256: str,
    schema_items: Sequence[SchemaItem],
    accepted_aliases: Sequence[_AcceptedAlias],
    audited_formulas: Sequence[_AuditedFormula],
    coverage: SchemaCoverageContract,
    cash_flow_rules: Any,
    policy: Mapping[str, Any],
) -> None:
    expected_keys = {
        "format_version",
        "policy",
        "claim_boundary",
        "status",
        "run_id",
        "source",
        "native_rows",
        "schema",
        "producer_snapshots",
        "code",
        "authority",
        "isolation",
        "inputs",
        "lctt_method",
        "path_summaries",
        "source_dispositions",
        "new_item_proposals",
        "alias_proposals",
        "equations",
        "conflicts",
        "schema_dispositions",
        "mandatory_search",
        "summary",
    }
    if set(payload) != expected_keys:
        raise NativeCanonicalMappingError("native canonical artifact fields are invalid")
    if any(
        payload.get(key) != value
        for key, value in {
            "format_version": _OUTPUT_FORMAT,
            "policy": _POLICY_NAME,
            "claim_boundary": _CLAIM_BOUNDARY,
            "status": _OUTPUT_STATUS,
        }.items()
    ):
        raise NativeCanonicalMappingError("native canonical artifact identity is invalid")
    if payload.get("source") != row_payload.get("source"):
        raise NativeCanonicalMappingError("native canonical source envelope drifted")
    expected_authority = {
        "canonical_labels": "CURRENT_UNIVERSAL_SCHEMA_WORKBOOKS",
        "aliases": "CURRENT_TYPED_ACCEPTED_ALIAS_AUTHORITY_ONLY",
        "ordering": "WORKBOOK_DISPLAY_ORDER",
        "hierarchy": "CURRENT_VALIDATED_SCHEMA_GRAPH",
        "source_rows_and_cells": "TRUSTED_REGISTERED_NATIVE_ROWS_SHA256_JOIN",
        "historical_values": None,
        "role_a": None,
        "human_review": None,
    }
    if _audited_terminal_aggregate_enabled(policy):
        expected_authority["business_formulas"] = (
            "HASH_BOUND_APPROVED_BUSINESS_UPDATE_AUDIT_RECORDS"
        )
    if payload.get("authority") != expected_authority:
        raise NativeCanonicalMappingError("native canonical authority receipt drifted")
    if payload.get("isolation") != {
        "prior_answer_artifacts_loaded": False,
        "historical_values_loaded": False,
        "historical_aliases_loaded": False,
        "role_a_outputs_loaded": False,
        "human_review_outputs_loaded": False,
        "bank_identity_used_for_mapping": False,
        "filename_identity_used_for_mapping": False,
        "page_number_rules_used_for_mapping": False,
        "source_row_count_rules_used_for_mapping": False,
        "same_run_alias_proposals_mapping_eligible": False,
        "new_item_proposals_allocate_report_norm_id": False,
    }:
        raise NativeCanonicalMappingError("native canonical isolation receipt drifted")
    dispositions = payload.get("source_dispositions")
    source_rows = _source_rows(row_payload)
    if not isinstance(dispositions, list) or len(dispositions) != len(source_rows):
        raise NativeCanonicalMappingError("native canonical source denominator drifted")
    source_by_id = {row.row_id: row for row in source_rows}
    path_summaries = payload.get("path_summaries")
    projections = {
        statement: build_schema_projection_v2(list(schema_items), statement)
        for statement in _STATEMENT_TYPES
    }
    if not isinstance(path_summaries, dict) or tuple(path_summaries) != _STATEMENT_TYPES:
        raise NativeCanonicalMappingError("native canonical path summaries are malformed")
    for statement in _STATEMENT_TYPES:
        summary = path_summaries[statement]
        expected_source_count = sum(
            row.statement_type == statement and row.within_financial_table_span
            for row in source_rows
        )
        expected_summary_keys = {
            "source_row_count",
            "maximum_cardinality",
            "projection_item_count",
            "projection_sha256",
        }
        if expected_source_count > 0:
            expected_summary_keys.add("localized_hierarchy_conflict_count")
        if _audited_terminal_aggregate_enabled(policy):
            expected_summary_keys.add("post_path_audited_terminal_aggregate_promotion_count")
        if (
            not isinstance(summary, dict)
            or set(summary) != expected_summary_keys
            or summary.get("source_row_count") != expected_source_count
            or summary.get("projection_item_count") != len(projections[statement].nodes)
            or summary.get("projection_sha256") != projections[statement].projection_sha256
            or type(summary.get("maximum_cardinality")) is not int
            or not 0 <= summary["maximum_cardinality"] <= expected_source_count
            or (
                expected_source_count > 0
                and (
                    type(summary["localized_hierarchy_conflict_count"]) is not int
                    or summary["localized_hierarchy_conflict_count"] < 0
                )
            )
            or (
                _audited_terminal_aggregate_enabled(policy)
                and (
                    type(summary["post_path_audited_terminal_aggregate_promotion_count"]) is not int
                    or summary["post_path_audited_terminal_aggregate_promotion_count"] < 0
                )
            )
        ):
            raise NativeCanonicalMappingError("native canonical path summary drifted")
    lctt_rows = [
        row
        for row in source_rows
        if row.statement_type == "LCTT" and row.within_financial_table_span
    ]
    lctt_method = (
        classify_cash_flow_method([row.label for row in lctt_rows], cash_flow_rules)
        if lctt_rows
        else CashFlowEvidence(
            CashFlowMethod.UNKNOWN,
            None,
            None,
            "no LCTT block was observed",
            False,
        )
    )
    expected_lctt_method = {
        "method": lctt_method.method.value,
        "indirect_anchor_positions": lctt_method.indirect_anchor_positions,
        "direct_anchor_positions": lctt_method.direct_anchor_positions,
        "reason": lctt_method.reason,
        "semantic_high_confidence_allowed": lctt_method.semantic_high_confidence_allowed,
        "opposite_branch_not_applicable_applied": bool(
            lctt_method.semantic_high_confidence_allowed
            and lctt_method.method in {CashFlowMethod.DIRECT, CashFlowMethod.INDIRECT}
        ),
    }
    if payload.get("lctt_method") != json.loads(_canonical_json_bytes(expected_lctt_method)):
        raise NativeCanonicalMappingError("native canonical cash-flow method receipt drifted")
    schema_by_id = {item.schema_id: item for item in schema_items}
    accepted_alias_by_key = _accepted_alias_index(accepted_aliases)
    selected_ids: set[int] = set()
    equations = payload.get("equations")
    if not isinstance(equations, list) or any(not isinstance(item, dict) for item in equations):
        raise NativeCanonicalMappingError("native canonical equation evidence is malformed")
    conflicts = payload.get("conflicts")
    if not isinstance(conflicts, list) or any(not isinstance(item, dict) for item in conflicts):
        raise NativeCanonicalMappingError("native canonical conflict evidence is malformed")
    allowed_match_bases = {
        "CANONICAL_RETRIEVAL_KEY_EXACT",
        "ACCEPTED_STRUCTURAL_ALIAS_RETRIEVAL_KEY_EXACT",
        "ACCEPTED_ACCOUNTING_ABBREVIATION_NORMALIZATION",
        "REPEATED_PARENT_DETAIL_WITH_COMPLETE_HIERARCHY_AND_EQUATION",
    }
    if _audited_terminal_aggregate_enabled(policy):
        allowed_match_bases.add(_AUDITED_TERMINAL_AGGREGATE_MATCH_BASIS)
    audited_formula_by_id = {formula.schema_id: formula for formula in audited_formulas}
    for expected_order, record in enumerate(dispositions, start=1):
        if not isinstance(record, dict) or record.get("source_order") != expected_order:
            raise NativeCanonicalMappingError("native canonical disposition order drifted")
        if _audited_terminal_aggregate_enabled(policy) != ("aggregate_match_receipt" in record):
            raise NativeCanonicalMappingError("native canonical aggregate receipt version drifted")
        row_id = record.get("row_id")
        if row_id not in source_by_id or record.get("disposition") not in _DISPOSITIONS:
            raise NativeCanonicalMappingError("native canonical disposition identity is invalid")
        source_row = source_by_id[row_id]
        expected_source_fields = {
            "page": source_row.row["page"],
            "page_row_order": source_row.page_order,
            "statement": source_row.statement_type,
            "scope": source_row.scope,
            "within_financial_table_span": source_row.within_financial_table_span,
            "row_type": source_row.row.get("row_type"),
            "raw_label": source_row.row.get("raw_label"),
            "normalized_label": source_row.label,
            "indentation": source_row.row.get("indentation"),
        }
        if any(record.get(key) != value for key, value in expected_source_fields.items()):
            raise NativeCanonicalMappingError("native canonical source row projection drifted")
        if record.get("source_cell_join") != _row_join(source_by_id[row_id], rows_sha256):
            raise NativeCanonicalMappingError("native canonical source-cell join drifted")
        if not source_row.within_financial_table_span and (
            record.get("disposition") != "UNRESOLVED"
            or record.get("candidate_report_norm_ids") != []
        ):
            raise NativeCanonicalMappingError(
                "outside-span source row was silently mapped or discarded"
            )
        candidate_ids_record = record.get("candidate_report_norm_ids")
        if (
            not isinstance(candidate_ids_record, list)
            or len(candidate_ids_record) != len(set(candidate_ids_record))
            or any(
                not isinstance(candidate_id, int) or candidate_id not in schema_by_id
                for candidate_id in candidate_ids_record
            )
        ):
            raise NativeCanonicalMappingError("native canonical candidate receipt drifted")
        indexes = record.get("equation_evidence_indexes")
        if (
            not isinstance(indexes, list)
            or any(
                not isinstance(index, int) or not 0 <= index < len(equations) for index in indexes
            )
            or len(indexes) != len(set(indexes))
        ):
            raise NativeCanonicalMappingError("native canonical equation join drifted")
        conflict_indexes = record.get("conflict_evidence_indexes")
        if (
            not isinstance(conflict_indexes, list)
            or any(
                not isinstance(index, int) or not 0 <= index < len(conflicts)
                for index in conflict_indexes
            )
            or len(conflict_indexes) != len(set(conflict_indexes))
            or any(
                row_id not in conflicts[index].get("affected_row_ids", ())
                for index in conflict_indexes
            )
        ):
            raise NativeCanonicalMappingError("native canonical conflict join drifted")
        aggregate_receipt = record.get("aggregate_match_receipt")
        if aggregate_receipt is not None:
            receipt_candidates = (
                aggregate_receipt.get("pre_value_topology_candidate_report_norm_ids")
                if isinstance(aggregate_receipt, dict)
                else None
            )
            if (
                not isinstance(aggregate_receipt, dict)
                or not isinstance(receipt_candidates, list)
                or not receipt_candidates
                or len(receipt_candidates) != len(set(receipt_candidates))
                or any(schema_id not in audited_formula_by_id for schema_id in receipt_candidates)
                or _SHA256.fullmatch(
                    str(aggregate_receipt.get("pre_value_topology_candidate_set_sha256", ""))
                )
                is None
                or aggregate_receipt.get("equation_used_for_target_selection") is not False
                or aggregate_receipt.get("exact_tolerance_source_units") != 0
            ):
                raise NativeCanonicalMappingError(
                    "native canonical aggregate topology receipt drifted"
                )
            receipt_equation_index = aggregate_receipt.get("equation_evidence_index")
            if receipt_equation_index is not None:
                if receipt_equation_index not in indexes:
                    raise NativeCanonicalMappingError(
                        "native canonical aggregate equation receipt is unjoined"
                    )
                receipt_equation = equations[receipt_equation_index]
                if (
                    len(receipt_candidates) != 1
                    or receipt_equation.get("equation_type")
                    != "AUDITED_FORMULA_TERMINAL_AGGREGATE_EXACT_SUM"
                    or receipt_equation.get("total_row_id") != row_id
                    or receipt_equation.get("target_report_norm_id") != receipt_candidates[0]
                    or receipt_equation.get("audited_formula_component_report_norm_ids")
                    != list(audited_formula_by_id[receipt_candidates[0]].component_schema_ids)
                    or receipt_equation.get("formula_authority_evidence_sha256")
                    != audited_formula_by_id[receipt_candidates[0]].authority_evidence_sha256
                    or aggregate_receipt.get("equation_status") != receipt_equation.get("status")
                    or aggregate_receipt.get("equation_axes") != receipt_equation.get("axes")
                ):
                    raise NativeCanonicalMappingError(
                        "native canonical aggregate formula/equation receipt drifted"
                    )
            if len(receipt_candidates) == 1 and "topology" in aggregate_receipt:
                formula = audited_formula_by_id[receipt_candidates[0]]
                topology = aggregate_receipt.get("topology")
                source_provenance = source_row.row.get("provenance")
                source_cells = source_row.row.get("cells")
                if (
                    not isinstance(topology, dict)
                    or topology.get("statement") != source_row.statement_type
                    or topology.get("presentation_scope") != source_row.scope
                    or topology.get("page") != source_row.row["page"]
                    or not isinstance(source_provenance, dict)
                    or topology.get("physical_table_id") != source_provenance.get("table_id")
                    or _SHA256.fullmatch(str(topology.get("block_evidence_sha256", ""))) is None
                    or not isinstance(source_cells, list)
                    or topology.get("axis_signature")
                    != [cell.get("axis_id") for cell in source_cells]
                    or topology.get("direct_child_report_norm_ids")
                    != list(formula.component_schema_ids)
                    or aggregate_receipt.get("formula_authority_evidence_sha256")
                    != formula.authority_evidence_sha256
                ):
                    raise NativeCanonicalMappingError(
                        "native canonical aggregate topology/formula join drifted"
                    )
        selected_id = record.get("selected_report_norm_id")
        if record["disposition"] == "EXISTING_ITEM":
            if (
                not isinstance(selected_id, int)
                or selected_id not in schema_by_id
                or selected_id in selected_ids
            ):
                raise NativeCanonicalMappingError("native canonical one-to-one mapping drifted")
            selected_ids.add(selected_id)
            item = schema_by_id[selected_id]
            if (
                item.statement_type != source_row.statement_type
                or record.get("selected_canonical_name") != item.canonical_name
                or record.get("schema_parent_report_norm_id") != item.parent_id
                or record.get("schema_hierarchy_level") != item.hierarchy_level
                or record.get("schema_display_order") != item.display_order
                or record.get("match_basis") not in allowed_match_bases
            ):
                raise NativeCanonicalMappingError("native canonical selected target drifted")
            aggregate_receipt = record.get("aggregate_match_receipt")
            if record.get("match_basis") == _AUDITED_TERMINAL_AGGREGATE_MATCH_BASIS:
                if (
                    not isinstance(aggregate_receipt, dict)
                    or aggregate_receipt.get("match_basis")
                    != _AUDITED_TERMINAL_AGGREGATE_MATCH_BASIS
                    or aggregate_receipt.get("selection_status") != "ACCEPTED_EXACT_EVERY_AXIS"
                    or aggregate_receipt.get("pre_value_topology_candidate_report_norm_ids")
                    != [selected_id]
                    or aggregate_receipt.get("equation_used_for_target_selection") is not False
                    or aggregate_receipt.get("equation_used_as_acceptance_gate") is not True
                    or aggregate_receipt.get("exact_tolerance_source_units") != 0
                    or aggregate_receipt.get("equation_evidence_index") not in indexes
                ):
                    raise NativeCanonicalMappingError(
                        "native canonical aggregate match receipt drifted"
                    )
            elif aggregate_receipt is not None:
                raise NativeCanonicalMappingError(
                    "ordinary existing mapping cites aggregate authority"
                )
            _validate_mapping_alias_authority(record, source_row, item, accepted_alias_by_key)
        elif selected_id is not None:
            raise NativeCanonicalMappingError("non-existing disposition grants ReportNormId")
    if [record["row_id"] for record in dispositions] != [row.row_id for row in source_rows]:
        raise NativeCanonicalMappingError("native canonical disposition order is not source order")
    dispositions_by_id = {str(record["row_id"]): record for record in dispositions}
    for conflict in conflicts:
        if conflict.get("conflict_type") not in {
            "OBSERVED_HIERARCHY_CONFLICT",
            "COMPLETE_STRUCTURE_EQUATION_CONFLICT",
        }:
            raise NativeCanonicalMappingError("native canonical conflict type is invalid")
        affected = conflict.get("affected_row_ids")
        candidate_ids = conflict.get("candidate_report_norm_ids")
        if (
            not isinstance(affected, list)
            or not affected
            or len(affected) != len(set(affected))
            or any(row_id not in dispositions_by_id for row_id in affected)
            or not isinstance(candidate_ids, list)
            or not candidate_ids
            or any(
                not isinstance(candidate_id, int) or candidate_id not in schema_by_id
                for candidate_id in candidate_ids
            )
            or any(dispositions_by_id[row_id]["disposition"] != "AMBIGUOUS" for row_id in affected)
            or not set(candidate_ids)
            <= {
                candidate_id
                for row_id in affected
                for candidate_id in dispositions_by_id[row_id]["candidate_report_norm_ids"]
            }
        ):
            raise NativeCanonicalMappingError("localized conflict was not safely demoted")

    proposals = payload.get("new_item_proposals")
    if not isinstance(proposals, list) or len(proposals) != sum(
        record["disposition"] == "NEW_ITEM_PROPOSAL" for record in dispositions
    ):
        raise NativeCanonicalMappingError(
            "native canonical schema-gap proposal denominator drifted"
        )
    if any(proposal.get("report_norm_id") is not None for proposal in proposals):
        raise NativeCanonicalMappingError("schema-gap proposal allocated a ReportNormId")
    proposed_rows = {
        proposal.get("source_evidence", {}).get("row_id")
        for proposal in proposals
        if isinstance(proposal, dict) and isinstance(proposal.get("source_evidence"), dict)
    }
    expected_proposed_rows = {
        str(record["row_id"])
        for record in dispositions
        if record["disposition"] == "NEW_ITEM_PROPOSAL"
    }
    if proposed_rows != expected_proposed_rows or len(proposed_rows) != len(proposals):
        raise NativeCanonicalMappingError("native canonical schema-gap/source join drifted")
    aliases = payload.get("alias_proposals")
    if (
        not isinstance(aliases, list)
        or any(not isinstance(alias, dict) for alias in aliases)
        or any(
            alias.get("proposal_type") not in _ALIAS_PROPOSAL_TYPES
            or alias.get("mapping_eligible_this_run") is not False
            for alias in aliases
        )
    ):
        raise NativeCanonicalMappingError("native canonical alias proposal contract drifted")

    schema_records = payload.get("schema_dispositions")
    if not isinstance(schema_records, list) or len(schema_records) != len(schema_items):
        raise NativeCanonicalMappingError("native canonical schema denominator drifted")
    if [record.get("report_norm_id") for record in schema_records] != [
        item.schema_id for item in schema_items
    ]:
        raise NativeCanonicalMappingError("native canonical schema disposition order drifted")
    if any(record.get("terminal_outcome") not in _TERMINAL_OUTCOMES for record in schema_records):
        raise NativeCanonicalMappingError("native canonical terminal outcome is invalid")
    mapped_row_by_id = {
        int(record["selected_report_norm_id"]): source_by_id[str(record["row_id"])]
        for record in dispositions
        if record["disposition"] == "EXISTING_ITEM"
    }
    ambiguous_candidate_rows: dict[int, list[str]] = defaultdict(list)
    for record in dispositions:
        if record["disposition"] != "AMBIGUOUS":
            continue
        candidate_ids = record.get("candidate_report_norm_ids")
        if not isinstance(candidate_ids, list) or not candidate_ids:
            raise NativeCanonicalMappingError("ambiguous source row has no candidate IDs")
        for candidate_id in candidate_ids:
            if not isinstance(candidate_id, int) or candidate_id not in schema_by_id:
                raise NativeCanonicalMappingError("ambiguous source candidate is invalid")
            ambiguous_candidate_rows[candidate_id].append(str(record["row_id"]))
    expected_schema_records = _schema_disposition_records(
        row_payload=row_payload,
        rows=source_rows,
        schema_items=schema_items,
        mapped_row_by_id=mapped_row_by_id,
        ambiguous_candidate_rows=ambiguous_candidate_rows,
        lctt_method=lctt_method,
    )
    if schema_records != expected_schema_records:
        raise NativeCanonicalMappingError("native canonical schema dispositions drifted")
    mandatory = json.loads(
        _canonical_json_bytes(
            _role_b_coverage_evaluation(
                coverage,
                str(row_payload["source"]["document_id"]),
                schema_records,
            )
        )
    )
    if payload.get("mandatory_search") != mandatory or mandatory["status"] != "PASS":
        raise NativeCanonicalMappingError("native canonical mandatory-search receipt drifted")
    counts = Counter(record["disposition"] for record in dispositions)
    summary = payload.get("summary")
    expected_counts = {status: counts[status] for status in _DISPOSITIONS}
    if (
        not isinstance(summary, dict)
        or summary.get("visible_source_items") != len(dispositions)
        or summary.get("financial_table_span_source_items")
        != sum(row.within_financial_table_span for row in source_rows)
        or summary.get("outside_financial_table_span_source_items")
        != sum(not row.within_financial_table_span for row in source_rows)
        or summary.get("source_items_successfully_accounted_for") != len(dispositions)
        or summary.get("source_item_accounting_denominator") != len(dispositions)
        or summary.get("mapped_to_existing_canonical_items") != counts["EXISTING_ITEM"]
        or summary.get("new_schema_item_proposals") != counts["NEW_ITEM_PROPOSAL"]
        or summary.get("ambiguous") != counts["AMBIGUOUS"]
        or summary.get("unresolved") != counts["UNRESOLVED"]
        or summary.get("structural") != counts["STRUCTURAL"]
        or summary.get("source_disposition_counts") != expected_counts
        or summary.get("alias_proposal_count") != len(aliases)
        or summary.get("equation_count") != len(equations)
        or summary.get("localized_conflict_count") != len(conflicts)
        or summary.get("universal_schema_item_count") != len(schema_items)
        or summary.get("universal_schema_counts")
        != {
            statement: sum(item.statement_type == statement for item in schema_items)
            for statement in _STATEMENT_TYPES
        }
    ):
        raise NativeCanonicalMappingError("native canonical summary drifted")
    replay = resolve_native_canonical_mapping(
        row_payload,
        rows_sha256=rows_sha256,
        schema_items=schema_items,
        projections=projections,
        coverage=coverage,
        cash_flow_rules=cash_flow_rules,
        accepted_aliases=accepted_aliases,
        audited_formulas=audited_formulas,
        policy=policy,
    )
    canonical_replay = json.loads(_canonical_json_bytes(replay))
    if any(payload.get(key) != value for key, value in canonical_replay.items()):
        raise NativeCanonicalMappingError(
            "native canonical producer-versioned semantic replay drifted"
        )


def load_registered_native_canonical_mapping(
    path: Path,
    *,
    project_root: Path,
    expected_sha256: str,
    policy_path: Path | None = None,
    rows_policy_path: Path | None = None,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    path = path.resolve()
    policy_path = (policy_path or project_root / POLICY_RELATIVE_PATH).resolve()
    rows_policy_path = (rows_policy_path or project_root / ROWS_POLICY_RELATIVE_PATH).resolve()
    if _SHA256.fullmatch(expected_sha256) is None:
        raise NativeCanonicalMappingError("trusted native canonical SHA-256 is invalid")
    if policy_path != (project_root / POLICY_RELATIVE_PATH).resolve():
        raise NativeCanonicalMappingError(
            f"native canonical mapping requires canonical policy path {POLICY_RELATIVE_PATH}"
        )
    try:
        encoded = path.read_bytes()
        payload = json.loads(encoded)
    except (OSError, json.JSONDecodeError) as exc:
        raise NativeCanonicalMappingError("cannot load native canonical artifact") from exc
    if sha256_bytes(encoded) != expected_sha256:
        raise NativeCanonicalMappingError(
            "native canonical artifact does not match trusted SHA-256"
        )
    if not isinstance(payload, dict) or encoded != _canonical_json_bytes(payload):
        raise NativeCanonicalMappingError("native canonical artifact is not canonical JSON")
    code = payload.get("code")
    if (
        not isinstance(code, dict)
        or set(code) != {"commit", "dirty", "implementation"}
        or code.get("dirty") is not False
        or not isinstance(code.get("implementation"), list)
        or code["implementation"] != _implementation_ledger_at_commit(project_root, code["commit"])
    ):
        raise NativeCanonicalMappingError("native canonical producer code identity drifted")
    (
        policy,
        items,
        accepted_aliases,
        audited_formulas,
        coverage,
        cash_flow_rules,
    ) = _load_producer_snapshots(
        payload.get("producer_snapshots"),
        project_root=project_root,
        producer_commit=code["commit"],
    )
    _validate_snapshot_schema_identity(
        policy,
        payload.get("schema"),
        items,
        accepted_aliases,
        audited_formulas,
        coverage,
    )
    native_rows = payload.get("native_rows")
    if not isinstance(native_rows, dict) or not isinstance(native_rows.get("path"), str):
        raise NativeCanonicalMappingError("native canonical native-row provenance is invalid")
    rows_path = _resolve_under_root(project_root, native_rows["path"], "native-row provenance")
    rows_sha256 = native_rows.get("sha256")
    if not isinstance(rows_sha256, str) or _SHA256.fullmatch(rows_sha256) is None:
        raise NativeCanonicalMappingError("native canonical native-row SHA-256 is invalid")
    try:
        row_payload = load_registered_native_statement_rows(
            rows_path,
            project_root=project_root,
            expected_sha256=rows_sha256,
            policy_path=rows_policy_path,
        )
    except Exception as exc:
        raise NativeCanonicalMappingError(
            "native canonical upstream rows failed strict load"
        ) from exc
    expected_native_rows = {
        "path": native_rows["path"],
        "sha256": rows_sha256,
        "size_bytes": rows_path.stat().st_size,
        "format_version": row_payload["format_version"],
        "policy": row_payload["policy"],
        "claim_boundary": row_payload["claim_boundary"],
        "status": row_payload["status"],
        "run_id": row_payload["run_id"],
        "producer_git_commit": row_payload["code"]["commit"],
        "denominator": "ALL_RECONSTRUCTED_SOURCE_ROWS",
    }
    if native_rows != expected_native_rows:
        raise NativeCanonicalMappingError("native canonical upstream row envelope drifted")
    _validate_embedded_runtime_ledger(
        payload.get("inputs"),
        project_root=project_root,
        producer_commit=code["commit"],
        rows_path=rows_path,
        rows_sha256=rows_sha256,
        policy_snapshot=payload["producer_snapshots"]["policy"],
        row_payload=row_payload,
    )
    _validate_loaded_mapping(
        payload,
        row_payload=row_payload,
        rows_sha256=rows_sha256,
        schema_items=items,
        accepted_aliases=accepted_aliases,
        audited_formulas=audited_formulas,
        coverage=coverage,
        cash_flow_rules=cash_flow_rules,
        policy=policy,
    )
    final = path.read_bytes()
    if final != encoded:
        raise NativeCanonicalMappingError("native canonical artifact changed during strict load")
    return copy.deepcopy(payload)


def _write_exclusive(path: Path, payload: bytes) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise NativeCanonicalMappingError(f"refusing to overwrite native canonical output: {path}")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    linked_identity: tuple[int, int] | None = None
    try:
        with os.fdopen(descriptor, "wb") as stream:
            if stream.write(payload) != len(payload):
                raise NativeCanonicalMappingError("native canonical output write was incomplete")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o644)
        temporary_stat = temporary.stat(follow_symlinks=False)
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise NativeCanonicalMappingError(
                f"refusing to overwrite native canonical output: {path}"
            ) from exc
        linked_identity = (temporary_stat.st_dev, temporary_stat.st_ino)
        published = path.stat(follow_symlinks=False)
        if (published.st_dev, published.st_ino) != linked_identity:
            raise NativeCanonicalMappingError("native canonical published inode changed")
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        if sha256_file(path) != sha256_bytes(payload):
            raise NativeCanonicalMappingError("native canonical output hash mismatch")
        published = path.stat(follow_symlinks=False)
        if (published.st_dev, published.st_ino) != linked_identity:
            raise NativeCanonicalMappingError("native canonical published inode changed")
    except BaseException as publication_error:
        rollback_error: BaseException | None = None
        if linked_identity is not None:
            try:
                current = path.stat(follow_symlinks=False)
            except FileNotFoundError:
                current = None
            except BaseException as exc:
                current = None
                rollback_error = exc
            if current is not None:
                if (current.st_dev, current.st_ino) != linked_identity:
                    rollback_error = NativeCanonicalMappingError(
                        "refusing to roll back a changed native canonical output"
                    )
                else:
                    try:
                        path.unlink()
                    except BaseException as exc:
                        rollback_error = exc
            try:
                directory = os.open(path.parent, os.O_RDONLY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
            except BaseException as exc:
                rollback_error = rollback_error or exc
        if rollback_error is not None:
            raise NativeCanonicalMappingError(
                f"native canonical publication rollback was incomplete: {rollback_error}"
            ) from publication_error
        raise
    finally:
        temporary.unlink(missing_ok=True)


def publish_registered_native_canonical_mapping(
    project_root: Path,
    rows_path: Path,
    rows_sha256: str,
    policy_path: Path,
    rows_policy_path: Path,
    run_id: str,
    output_path: Path,
) -> NativeCanonicalMappingPublication:
    project_root = project_root.resolve()
    output_path = output_path.resolve()
    _relative_path(project_root, output_path, "native canonical output")
    state = _current_git_state(project_root)
    payload = build_registered_native_canonical_mapping(
        project_root,
        rows_path.resolve(),
        rows_sha256,
        policy_path.resolve(),
        rows_policy_path.resolve(),
        run_id,
        state,
    )
    role = payload["source"]["dataset_role"]
    allowed_directory = (project_root / _ROLE_DIRECTORIES[role]).resolve()
    try:
        output_path.relative_to(allowed_directory)
    except ValueError as exc:
        raise NativeCanonicalMappingError(
            f"native canonical output for {role} must stay under {_ROLE_DIRECTORIES[role]}"
        ) from exc
    encoded = _canonical_json_bytes(payload)
    _write_exclusive(output_path, encoded)
    published_stat = output_path.stat(follow_symlinks=False)
    published_identity = (published_stat.st_dev, published_stat.st_ino)

    def rollback_owned_output(cause: BaseException) -> None:
        try:
            current = output_path.stat(follow_symlinks=False)
        except FileNotFoundError:
            return
        except BaseException as rollback_exc:
            raise NativeCanonicalMappingError(
                f"native canonical strict-load rollback inspection failed: {rollback_exc}"
            ) from cause
        if (current.st_dev, current.st_ino) != published_identity:
            raise NativeCanonicalMappingError(
                "refusing to roll back a changed native canonical output"
            ) from cause
        try:
            output_path.unlink()
            directory = os.open(output_path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except BaseException as rollback_exc:
            raise NativeCanonicalMappingError(
                f"native canonical strict-load rollback failed: {rollback_exc}"
            ) from cause

    digest = sha256_bytes(encoded)
    try:
        loaded = load_registered_native_canonical_mapping(
            output_path,
            project_root=project_root,
            expected_sha256=digest,
            policy_path=policy_path,
            rows_policy_path=rows_policy_path,
        )
    except BaseException as exc:
        # The exclusive writer owns this inode. A failed post-publication strict
        # replay must not leave a partially accepted artifact behind.
        rollback_owned_output(exc)
        raise
    if loaded != payload:
        drift = NativeCanonicalMappingError("published native canonical artifact replay drifted")
        rollback_owned_output(drift)
        raise drift
    return NativeCanonicalMappingPublication(
        path=output_path,
        sha256=digest,
        size_bytes=len(encoded),
        payload=payload,
    )
