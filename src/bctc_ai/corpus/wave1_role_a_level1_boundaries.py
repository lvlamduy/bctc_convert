from __future__ import annotations

import json
import os
import re
import stat
import subprocess
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from bctc_ai.core.hashing import sha256_bytes, sha256_file


class WaveOneRoleALevelOneReferenceError(ValueError):
    """The sealed structural reference cannot be used without guessing."""


POLICY_RELATIVE_PATH = Path("config/corpus/bank-corpus-wave-1-role-a-level-1-boundaries-v1.yaml")
REFERENCE_SOURCE_RELATIVE_PATH = Path(
    "data/registered/bank-corpus-wave-1-role-a-level-1-boundaries-v1.yaml"
)
IMPLEMENTATION_RELATIVE_PATH = Path("src/bctc_ai/corpus/wave1_role_a_level1_boundaries.py")
TEST_RELATIVE_PATH = Path("tests/unit/test_wave1_role_a_level1_boundaries.py")
OUTPUT_RELATIVE_PATH = Path(
    "output/development/bank-corpus-survey-v1/wave-1-role-a-level-1-statement-boundaries.json"
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_IDENTITY_FIELDS = {
    "document_id",
    "relative_path",
    "sha256",
    "size_bytes",
    "page_count",
}
_SEGMENT_KINDS = {
    "BLANK_INTERSTITIAL",
    "BLANK_TRAILING",
    "CDKT_MAIN",
    "COVER",
    "GOVERNANCE_GENERAL_INFORMATION",
    "KQKD",
    "LCTT",
    "OFF_BALANCE",
    "SUPPORTING_FRONT",
    "SUPPORTING_TRAILING",
    "TABLE_OF_CONTENTS",
    "TM",
}
_STATEMENT_BLOCK_TYPES = {"CDKT_MAIN", "OFF_BALANCE", "KQKD", "LCTT", "TM"}
_NONSTATEMENT_SEGMENT_KINDS = _SEGMENT_KINDS - _STATEMENT_BLOCK_TYPES
_SCOPE_STATUSES = {
    "OBSERVED_CONSOLIDATED",
    "OBSERVED_SEPARATE",
    "UNRESOLVED_SOURCE_UNQUALIFIED",
}
_LCTT_METHOD_STATUSES = {
    "DIRECT_EXPLICIT_TITLE",
    "DIRECT_INFERRED_VISIBLE_ROWS",
    "UNRESOLVED_NOT_PRINTED",
}
_PERIOD_CLASSIFICATIONS = {"Q1_2026", "Q2_2026"}
_DUPLICATE_STATUSES = {
    "NONE_OBSERVED",
    "MULTIPLE_FORMAL_SCALE_VARIANTS_OBSERVED",
}


def _canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _read_stable_bytes(path: Path, label: str) -> bytes:
    before = path.stat()
    payload = path.read_bytes()
    after = path.stat()
    before_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if before_identity != after_identity or len(payload) != before.st_size:
        raise WaveOneRoleALevelOneReferenceError(f"{label} changed while it was read")
    return payload


def _canonical_relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise WaveOneRoleALevelOneReferenceError(
            f"{label} must be a nonempty project-relative path"
        )
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise WaveOneRoleALevelOneReferenceError(f"{label} is not canonical")
    return value


def _resolve_under_root(project_root: Path, value: Any, label: str) -> Path:
    relative = _canonical_relative_path(value, label)
    path = (project_root / Path(*PurePosixPath(relative).parts)).resolve()
    if not path.is_relative_to(project_root):
        raise WaveOneRoleALevelOneReferenceError(f"{label} escapes the project root")
    return path


def _load_yaml_object(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = yaml.safe_load(payload)
    except yaml.YAMLError as error:
        raise WaveOneRoleALevelOneReferenceError(f"{label} is invalid YAML") from error
    if not isinstance(value, dict):
        raise WaveOneRoleALevelOneReferenceError(f"{label} must be an object")
    return value


def _load_json_object(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise WaveOneRoleALevelOneReferenceError(f"{label} is invalid JSON") from error
    if not isinstance(value, dict):
        raise WaveOneRoleALevelOneReferenceError(f"{label} must be an object")
    return value


def _require_exact_fields(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise WaveOneRoleALevelOneReferenceError(f"{label} fields drifted")
    return value


def _require_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WaveOneRoleALevelOneReferenceError(f"{label} must be a nonempty string")
    return value


def _validate_bound_specification(
    project_root: Path,
    specification: Any,
    *,
    label: str,
    expected_path: Path,
) -> dict[str, Any]:
    value = _require_exact_fields(
        specification,
        {"path", "sha256", "size_bytes", "format_version", "status", "claim_boundary"},
        label,
    )
    if value["path"] != expected_path.as_posix():
        raise WaveOneRoleALevelOneReferenceError(f"{label} path drifted")
    _resolve_under_root(project_root, value["path"], f"{label} path")
    if _SHA256.fullmatch(str(value["sha256"])) is None:
        raise WaveOneRoleALevelOneReferenceError(f"{label} sha256 is invalid")
    if not isinstance(value["size_bytes"], int) or value["size_bytes"] <= 0:
        raise WaveOneRoleALevelOneReferenceError(f"{label} size is invalid")
    for field in ("format_version", "status", "claim_boundary"):
        _require_nonempty_string(value[field], f"{label} {field}")
    return value


def load_wave_one_role_a_level_one_policy(path: Path, project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    canonical = (project_root / POLICY_RELATIVE_PATH).resolve()
    if path.resolve() != canonical:
        raise WaveOneRoleALevelOneReferenceError(
            f"Role-A Level-1 boundaries require canonical policy {POLICY_RELATIVE_PATH}"
        )
    policy = _load_yaml_object(_read_stable_bytes(path, "Role-A Level-1 policy"), "policy")
    _require_exact_fields(
        policy,
        {
            "version",
            "policy",
            "status",
            "claim_boundary",
            "authority",
            "upstream_binding",
            "reference_source",
            "identity_join",
            "page_partition",
            "safety",
            "expected_accounting",
            "output",
        },
        "policy",
    )
    if (
        policy["version"] != 1
        or policy["policy"] != "BANK_CORPUS_WAVE_1_ROLE_A_LEVEL_1_BOUNDARIES_POLICY_V1"
        or policy["status"] != "ROLE_A_LEVEL_1_MACHINE_REFERENCE"
        or policy["claim_boundary"] != "STRUCTURAL_BOUNDARIES_ONLY"
    ):
        raise WaveOneRoleALevelOneReferenceError("policy identity drifted")
    if policy["authority"] != {
        "reference_role": "ROLE_A",
        "evidence_authority": "VISIBLE_RENDERED_PIXELS",
        "page_basis": "ONE_BASED_PHYSICAL_PDF_PAGE",
        "human_gold": False,
        "role_b_output": False,
        "row_reference": False,
        "value_reference": False,
        "canonical_reference": False,
    }:
        raise WaveOneRoleALevelOneReferenceError("policy authority boundary drifted")

    upstream = _require_exact_fields(
        policy["upstream_binding"],
        {"mode", "selection_receipt_sha256", "inventory", "source_profile"},
        "upstream binding",
    )
    if upstream["mode"] != "EXACT_PUBLISHED_ARTIFACT_BYTES_READ_ONLY":
        raise WaveOneRoleALevelOneReferenceError("upstream binding mode drifted")
    if _SHA256.fullmatch(str(upstream["selection_receipt_sha256"])) is None:
        raise WaveOneRoleALevelOneReferenceError("selection receipt is invalid")
    _validate_bound_specification(
        project_root,
        upstream["inventory"],
        label="inventory binding",
        expected_path=Path("output/development/bank-corpus-survey-v1/corpus-inventory.json"),
    )
    _validate_bound_specification(
        project_root,
        upstream["source_profile"],
        label="source-profile binding",
        expected_path=Path("output/development/bank-corpus-survey-v1/wave-1-source-profile.json"),
    )
    _validate_bound_specification(
        project_root,
        policy["reference_source"],
        label="reference-source binding",
        expected_path=REFERENCE_SOURCE_RELATIVE_PATH,
    )

    identity = _require_exact_fields(
        policy["identity_join"],
        {
            "key",
            "expected_bank_count",
            "inventory_is_sole_source_for",
            "source_profile_is_sole_source_for",
            "require_exact_inventory_profile_identity_match",
            "source_records_must_not_contain_document_identity_fields",
        },
        "identity join",
    )
    if identity != {
        "key": "bank",
        "expected_bank_count": 27,
        "inventory_is_sole_source_for": [
            "document_id",
            "relative_path",
            "sha256",
            "size_bytes",
        ],
        "source_profile_is_sole_source_for": ["page_count"],
        "require_exact_inventory_profile_identity_match": True,
        "source_records_must_not_contain_document_identity_fields": True,
    }:
        raise WaveOneRoleALevelOneReferenceError("identity join contract drifted")

    partition = _require_exact_fields(
        policy["page_partition"],
        {
            "require_exact_physical_page_coverage",
            "first_page",
            "gaps_allowed",
            "primary_page_segment_overlap_allowed",
            "blank_and_supporting_pages_must_be_explicit",
            "statement_block_overlap_allowed_only_for_embedded_off_balance",
            "embedded_off_balance_rules",
            "standalone_off_balance_rules",
            "tm_subdivision_rules",
            "duplicate_presentation_rules",
        },
        "page partition",
    )
    if (
        partition["require_exact_physical_page_coverage"] is not True
        or partition["first_page"] != 1
        or partition["gaps_allowed"] is not False
        or partition["primary_page_segment_overlap_allowed"] is not False
        or partition["blank_and_supporting_pages_must_be_explicit"] is not True
        or partition["statement_block_overlap_allowed_only_for_embedded_off_balance"] is not True
    ):
        raise WaveOneRoleALevelOneReferenceError("primary page-partition gates drifted")
    embedded = partition["embedded_off_balance_rules"]
    if embedded != {
        "block_type": "OFF_BALANCE",
        "placement": "EMBEDDED_BOTTOM_REGION",
        "must_be_single_page": True,
        "must_name_parent_cdkt_block": True,
        "must_match_parent_copy_id": True,
        "must_be_contained_by_parent_cdkt_range": True,
        "must_match_parent_page_segment_embedded_page": True,
    }:
        raise WaveOneRoleALevelOneReferenceError("embedded off-balance gates drifted")
    if partition["standalone_off_balance_rules"] != {
        "placement": "STANDALONE_PAGE",
        "must_own_matching_primary_page_segment": True,
    }:
        raise WaveOneRoleALevelOneReferenceError("standalone off-balance gates drifted")
    if partition["tm_subdivision_rules"] != {
        "if_present_must_partition_tm_exactly": True,
        "overlap_allowed": False,
    }:
        raise WaveOneRoleALevelOneReferenceError("TM subdivision gates drifted")
    if partition["duplicate_presentation_rules"] != {
        "preserve_each_visible_formal_copy": True,
        "page_ownership_remains_single": True,
        "canonical_double_count_claim_allowed": False,
    }:
        raise WaveOneRoleALevelOneReferenceError("duplicate-presentation gates drifted")

    safety = policy["safety"]
    if not isinstance(safety, dict) or any(
        safety.get(field) is not expected
        for field, expected in {
            "schema_inputs_allowed": False,
            "canonical_mapping_allowed": False,
            "financial_value_read_claimed": False,
            "visible_row_accounting_claimed": False,
            "source_complete_claim_allowed": False,
            "canonical_complete_claim_allowed": False,
            "human_reviewed_gold_claim_allowed": False,
            "role_b_inference_claim_allowed": False,
            "bank_specific_parser_routing_allowed": False,
            "source_pdf_byte_revalidation_required_for_publication": True,
            "source_pdf_page_count_revalidation_required_for_publication": True,
            "fail_closed_on_unknown_field": True,
            "fail_closed_on_partition_or_overlap_error": True,
        }.items()
    ):
        raise WaveOneRoleALevelOneReferenceError("safety boundary drifted")
    if set(safety) != {
        "schema_inputs_allowed",
        "canonical_mapping_allowed",
        "financial_value_read_claimed",
        "visible_row_accounting_claimed",
        "source_complete_claim_allowed",
        "canonical_complete_claim_allowed",
        "human_reviewed_gold_claim_allowed",
        "role_b_inference_claim_allowed",
        "bank_specific_parser_routing_allowed",
        "source_pdf_byte_revalidation_required_for_publication",
        "source_pdf_page_count_revalidation_required_for_publication",
        "fail_closed_on_unknown_field",
        "fail_closed_on_partition_or_overlap_error",
    }:
        raise WaveOneRoleALevelOneReferenceError("safety fields drifted")

    expected = _require_exact_fields(
        policy["expected_accounting"],
        {
            "document_count",
            "physical_page_count",
            "statement_block_count",
            "embedded_off_balance_block_count",
            "duplicate_presentation_document_count",
            "scope_status_counts",
            "lctt_method_status_counts",
        },
        "expected accounting",
    )
    if expected["document_count"] != 27 or expected["physical_page_count"] != 1449:
        raise WaveOneRoleALevelOneReferenceError("expected corpus accounting drifted")

    output = _require_exact_fields(
        policy["output"],
        {
            "format_version",
            "status",
            "claim_boundary",
            "canonical_json",
            "exclusive_no_overwrite",
            "publication_requires_committed_clean_inputs",
            "required_committed_paths",
            "output_path",
        },
        "output contract",
    )
    if output != {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_A_LEVEL_1_BOUNDARIES_V1",
        "status": "ROLE_A_LEVEL_1_MACHINE_REFERENCE",
        "claim_boundary": "STRUCTURAL_BOUNDARIES_ONLY",
        "canonical_json": True,
        "exclusive_no_overwrite": True,
        "publication_requires_committed_clean_inputs": True,
        "required_committed_paths": [
            POLICY_RELATIVE_PATH.as_posix(),
            REFERENCE_SOURCE_RELATIVE_PATH.as_posix(),
            IMPLEMENTATION_RELATIVE_PATH.as_posix(),
            TEST_RELATIVE_PATH.as_posix(),
        ],
        "output_path": OUTPUT_RELATIVE_PATH.as_posix(),
    }:
        raise WaveOneRoleALevelOneReferenceError("output contract drifted")
    _resolve_under_root(project_root, output["output_path"], "output path")
    return policy


def _load_bound_json(
    project_root: Path, specification: dict[str, Any], label: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    path = _resolve_under_root(project_root, specification["path"], label)
    if path.is_symlink() or not path.is_file():
        raise WaveOneRoleALevelOneReferenceError(f"{label} is not a regular file")
    encoded = _read_stable_bytes(path, label)
    if (
        len(encoded) != specification["size_bytes"]
        or sha256_bytes(encoded) != specification["sha256"]
    ):
        raise WaveOneRoleALevelOneReferenceError(f"{label} byte identity drifted")
    payload = _load_json_object(encoded, label)
    for field in ("format_version", "status", "claim_boundary"):
        if payload.get(field) != specification[field]:
            raise WaveOneRoleALevelOneReferenceError(f"{label} {field} drifted")
    binding = {
        "binding_mode": "EXACT_PUBLISHED_ARTIFACT_BYTES_READ_ONLY",
        "rebuilt_by_this_run": False,
        **{field: specification[field] for field in specification},
    }
    return payload, binding


def _load_reference_source(
    project_root: Path, specification: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    path = _resolve_under_root(project_root, specification["path"], "reference source")
    if path.is_symlink() or not path.is_file():
        raise WaveOneRoleALevelOneReferenceError("reference source is not a regular file")
    encoded = _read_stable_bytes(path, "reference source")
    if (
        len(encoded) != specification["size_bytes"]
        or sha256_bytes(encoded) != specification["sha256"]
    ):
        raise WaveOneRoleALevelOneReferenceError("reference source byte identity drifted")
    payload = _load_yaml_object(encoded, "reference source")
    for field in ("format_version", "status", "claim_boundary"):
        if payload.get(field) != specification[field]:
            raise WaveOneRoleALevelOneReferenceError(f"reference source {field} drifted")
    return payload, {
        "binding_mode": "EXACT_REFERENCE_SOURCE_BYTES_READ_ONLY",
        **{field: specification[field] for field in specification},
    }


def _selection_receipt(selected: list[dict[str, Any]]) -> str:
    projection = [
        {
            key: record[key]
            for key in ("bank", "document_id", "sha256", "size_bytes", "relative_path")
        }
        for record in selected
    ]
    return sha256_bytes(_canonical_json_bytes(projection))


def _indexed_records(records: Any, label: str) -> dict[str, dict[str, Any]]:
    if not isinstance(records, list) or not records:
        raise WaveOneRoleALevelOneReferenceError(f"{label} must be a nonempty list")
    indexed: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise WaveOneRoleALevelOneReferenceError(f"{label} contains a non-object")
        bank = record.get("bank")
        if not isinstance(bank, str) or not bank or bank in indexed:
            raise WaveOneRoleALevelOneReferenceError(f"{label} bank keys are invalid")
        indexed[bank] = record
    return indexed


def _expand_page_segment(value: Any, bank: str) -> dict[str, Any]:
    if not isinstance(value, list) or len(value) != 5:
        raise WaveOneRoleALevelOneReferenceError(f"{bank} page-segment tuple is malformed")
    kind, start_page, end_page, copy_id, embedded_pages = value
    if kind not in _SEGMENT_KINDS:
        raise WaveOneRoleALevelOneReferenceError(f"{bank} page-segment kind is invalid")
    if (
        not isinstance(start_page, int)
        or isinstance(start_page, bool)
        or not isinstance(end_page, int)
        or isinstance(end_page, bool)
        or start_page < 1
        or end_page < start_page
    ):
        raise WaveOneRoleALevelOneReferenceError(f"{bank} page-segment range is invalid")
    if not isinstance(copy_id, str) or not copy_id:
        raise WaveOneRoleALevelOneReferenceError(f"{bank} page-segment copy ID is invalid")
    if kind in _NONSTATEMENT_SEGMENT_KINDS and copy_id != "NONE":
        raise WaveOneRoleALevelOneReferenceError(
            f"{bank} nonstatement page segment cannot carry a statement copy"
        )
    if kind in _STATEMENT_BLOCK_TYPES and copy_id == "NONE":
        raise WaveOneRoleALevelOneReferenceError(
            f"{bank} statement page segment requires a copy ID"
        )
    if (
        not isinstance(embedded_pages, list)
        or any(not isinstance(page, int) or isinstance(page, bool) for page in embedded_pages)
        or embedded_pages != sorted(set(embedded_pages))
        or any(page < start_page or page > end_page for page in embedded_pages)
        or (embedded_pages and kind != "CDKT_MAIN")
    ):
        raise WaveOneRoleALevelOneReferenceError(
            f"{bank} embedded off-balance page incidence is invalid"
        )
    return {
        "kind": kind,
        "start_page": start_page,
        "end_page": end_page,
        "copy_id": copy_id,
        "embedded_off_balance_pages": embedded_pages,
    }


def _expand_statement_block(value: Any, bank: str) -> dict[str, Any]:
    if not isinstance(value, list) or len(value) != 8:
        raise WaveOneRoleALevelOneReferenceError(f"{bank} statement-block tuple is malformed")
    (
        block_id,
        block_type,
        start_page,
        end_page,
        copy_id,
        placement,
        parent_block_id,
        visible_unit_override,
    ) = value
    if not isinstance(block_id, str) or not block_id:
        raise WaveOneRoleALevelOneReferenceError(f"{bank} block ID is invalid")
    if block_type not in _STATEMENT_BLOCK_TYPES:
        raise WaveOneRoleALevelOneReferenceError(f"{bank} statement-block type is invalid")
    if (
        not isinstance(start_page, int)
        or isinstance(start_page, bool)
        or not isinstance(end_page, int)
        or isinstance(end_page, bool)
        or start_page < 1
        or end_page < start_page
    ):
        raise WaveOneRoleALevelOneReferenceError(f"{bank} statement-block range is invalid")
    if not isinstance(copy_id, str) or not copy_id or copy_id == "NONE":
        raise WaveOneRoleALevelOneReferenceError(f"{bank} statement-block copy ID is invalid")
    if placement not in {"PAGE_SEQUENCE", "STANDALONE_PAGE", "EMBEDDED_BOTTOM_REGION"}:
        raise WaveOneRoleALevelOneReferenceError(f"{bank} block placement is invalid")
    if parent_block_id is not None and (
        not isinstance(parent_block_id, str) or not parent_block_id
    ):
        raise WaveOneRoleALevelOneReferenceError(f"{bank} parent block ID is invalid")
    if visible_unit_override is not None and (
        not isinstance(visible_unit_override, str) or not visible_unit_override
    ):
        raise WaveOneRoleALevelOneReferenceError(f"{bank} unit override is invalid")
    return {
        "block_id": block_id,
        "block_type": block_type,
        "start_page": start_page,
        "end_page": end_page,
        "copy_id": copy_id,
        "placement": placement,
        "parent_block_id": parent_block_id,
        "visible_unit_override": visible_unit_override,
    }


def _expand_tm_subdivision(value: Any, bank: str) -> dict[str, Any]:
    if not isinstance(value, list) or len(value) != 3:
        raise WaveOneRoleALevelOneReferenceError(f"{bank} TM-subdivision tuple is malformed")
    kind, start_page, end_page = value
    if (
        not isinstance(kind, str)
        or not kind
        or not isinstance(start_page, int)
        or isinstance(start_page, bool)
        or not isinstance(end_page, int)
        or isinstance(end_page, bool)
        or start_page < 1
        or end_page < start_page
    ):
        raise WaveOneRoleALevelOneReferenceError(f"{bank} TM subdivision is invalid")
    return {"kind": kind, "start_page": start_page, "end_page": end_page}


def _validate_metadata(record: dict[str, Any], bank: str) -> None:
    scope = _require_exact_fields(record["scope"], {"status", "evidence"}, f"{bank} scope")
    if scope["status"] not in _SCOPE_STATUSES:
        raise WaveOneRoleALevelOneReferenceError(f"{bank} scope status is invalid")
    _require_nonempty_string(scope["evidence"], f"{bank} scope evidence")

    unit = _require_exact_fields(
        record["unit"], {"normalized", "visible_labels", "evidence"}, f"{bank} unit"
    )
    _require_nonempty_string(unit["normalized"], f"{bank} normalized unit")
    if (
        not isinstance(unit["visible_labels"], list)
        or not unit["visible_labels"]
        or any(not isinstance(value, str) or not value for value in unit["visible_labels"])
    ):
        raise WaveOneRoleALevelOneReferenceError(f"{bank} visible unit labels are invalid")
    _require_nonempty_string(unit["evidence"], f"{bank} unit evidence")

    period = _require_exact_fields(
        record["reporting_period"],
        {
            "classification",
            "balance_axis_pattern",
            "income_axis_pattern",
            "cash_axis_pattern",
            "evidence",
        },
        f"{bank} reporting period",
    )
    if period["classification"] not in _PERIOD_CLASSIFICATIONS:
        raise WaveOneRoleALevelOneReferenceError(
            f"{bank} reporting-period classification is invalid"
        )
    for field in (
        "balance_axis_pattern",
        "income_axis_pattern",
        "cash_axis_pattern",
        "evidence",
    ):
        _require_nonempty_string(period[field], f"{bank} reporting period {field}")

    method = _require_exact_fields(
        record["lctt_method"], {"status", "evidence"}, f"{bank} LCTT method"
    )
    if method["status"] not in _LCTT_METHOD_STATUSES:
        raise WaveOneRoleALevelOneReferenceError(f"{bank} LCTT method status is invalid")
    _require_nonempty_string(method["evidence"], f"{bank} LCTT evidence")

    if not isinstance(record["form_codes"], list) or any(
        not isinstance(value, str) or not value for value in record["form_codes"]
    ):
        raise WaveOneRoleALevelOneReferenceError(f"{bank} form-code evidence is invalid")
    if not isinstance(record["notes"], list) or any(
        not isinstance(value, str) or not value for value in record["notes"]
    ):
        raise WaveOneRoleALevelOneReferenceError(f"{bank} notes are invalid")


def _validate_duplicate_presentation(
    duplicate: Any, blocks: list[dict[str, Any]], bank: str
) -> None:
    if not isinstance(duplicate, dict) or duplicate.get("status") not in _DUPLICATE_STATUSES:
        raise WaveOneRoleALevelOneReferenceError(f"{bank} duplicate-presentation status is invalid")
    if duplicate.get("canonical_double_count_claim") != "NOT_MADE":
        raise WaveOneRoleALevelOneReferenceError(
            f"{bank} canonical double-count claim is forbidden"
        )
    block_by_id = {block["block_id"]: block for block in blocks}
    if duplicate["status"] == "NONE_OBSERVED":
        if set(duplicate) != {"status", "canonical_double_count_claim"}:
            raise WaveOneRoleALevelOneReferenceError(f"{bank} nonduplicate fields are malformed")
        if any(block["copy_id"] != "PRIMARY" for block in blocks):
            raise WaveOneRoleALevelOneReferenceError(
                f"{bank} nonduplicate record contains a copied statement block"
            )
        return

    if set(duplicate) != {"status", "canonical_double_count_claim", "copy_groups"}:
        raise WaveOneRoleALevelOneReferenceError(f"{bank} duplicate fields are malformed")
    groups = duplicate["copy_groups"]
    if not isinstance(groups, list) or len(groups) < 2:
        raise WaveOneRoleALevelOneReferenceError(f"{bank} duplicate copy groups are missing")
    grouped_ids: set[str] = set()
    copy_ids: set[str] = set()
    for group in groups:
        value = _require_exact_fields(
            group, {"copy_id", "block_ids", "scale"}, f"{bank} duplicate copy group"
        )
        copy_id = _require_nonempty_string(value["copy_id"], f"{bank} duplicate copy ID")
        if copy_id in {"NONE", "PRIMARY"} or copy_id in copy_ids:
            raise WaveOneRoleALevelOneReferenceError(f"{bank} duplicate copy IDs are invalid")
        copy_ids.add(copy_id)
        _require_nonempty_string(value["scale"], f"{bank} duplicate scale")
        ids = value["block_ids"]
        if not isinstance(ids, list) or not ids or len(ids) != len(set(ids)):
            raise WaveOneRoleALevelOneReferenceError(f"{bank} duplicate block IDs are invalid")
        for block_id in ids:
            block = block_by_id.get(block_id)
            if block is None or block["copy_id"] != copy_id or block_id in grouped_ids:
                raise WaveOneRoleALevelOneReferenceError(
                    f"{bank} duplicate group does not bind exact copied blocks"
                )
            grouped_ids.add(block_id)
    copied_ids = {
        block["block_id"] for block in blocks if block["copy_id"] not in {"PRIMARY", "NONE"}
    }
    if grouped_ids != copied_ids:
        raise WaveOneRoleALevelOneReferenceError(
            f"{bank} duplicate copy groups do not account every copied block"
        )


def _validate_reference_record(record: dict[str, Any], page_count: int) -> dict[str, Any]:
    expected_fields = {
        "bank",
        "scope",
        "unit",
        "reporting_period",
        "lctt_method",
        "form_codes",
        "page_segments",
        "statement_blocks",
        "tm_subdivisions",
        "duplicate_presentation",
        "notes",
    }
    if not isinstance(record, dict) or set(record) != expected_fields:
        raise WaveOneRoleALevelOneReferenceError("reference record fields drifted")
    bank = _require_nonempty_string(record["bank"], "reference bank")
    if _SOURCE_IDENTITY_FIELDS & set(record):
        raise WaveOneRoleALevelOneReferenceError(
            f"{bank} reference source illegally contains document identity"
        )
    if not isinstance(page_count, int) or isinstance(page_count, bool) or page_count < 1:
        raise WaveOneRoleALevelOneReferenceError(f"{bank} page count is invalid")
    _validate_metadata(record, bank)

    if not isinstance(record["page_segments"], list) or not record["page_segments"]:
        raise WaveOneRoleALevelOneReferenceError(f"{bank} page partition is missing")
    segments = [_expand_page_segment(value, bank) for value in record["page_segments"]]
    expected_page = 1
    page_owner: dict[int, dict[str, Any]] = {}
    for segment in segments:
        if segment["start_page"] != expected_page:
            raise WaveOneRoleALevelOneReferenceError(
                f"{bank} primary page partition has a gap or overlap at page {expected_page}"
            )
        for page in range(segment["start_page"], segment["end_page"] + 1):
            page_owner[page] = segment
        expected_page = segment["end_page"] + 1
    if expected_page != page_count + 1 or set(page_owner) != set(range(1, page_count + 1)):
        raise WaveOneRoleALevelOneReferenceError(
            f"{bank} primary page partition does not cover 1..page_count"
        )

    if not isinstance(record["statement_blocks"], list) or not record["statement_blocks"]:
        raise WaveOneRoleALevelOneReferenceError(f"{bank} statement blocks are missing")
    blocks = [_expand_statement_block(value, bank) for value in record["statement_blocks"]]
    block_by_id = {block["block_id"]: block for block in blocks}
    if len(block_by_id) != len(blocks):
        raise WaveOneRoleALevelOneReferenceError(f"{bank} statement block IDs are duplicated")
    for block in blocks:
        if block["end_page"] > page_count:
            raise WaveOneRoleALevelOneReferenceError(f"{bank} statement block exceeds page count")
        if block["block_type"] == "OFF_BALANCE":
            if block["placement"] not in {"STANDALONE_PAGE", "EMBEDDED_BOTTOM_REGION"}:
                raise WaveOneRoleALevelOneReferenceError(f"{bank} off-balance placement is invalid")
        elif block["placement"] != "PAGE_SEQUENCE" or block["parent_block_id"] is not None:
            raise WaveOneRoleALevelOneReferenceError(
                f"{bank} non-off-balance block placement is invalid"
            )

        if block["placement"] == "STANDALONE_PAGE":
            if block["parent_block_id"] is not None:
                raise WaveOneRoleALevelOneReferenceError(
                    f"{bank} standalone off-balance block cannot have a parent"
                )
            for page in range(block["start_page"], block["end_page"] + 1):
                owner = page_owner[page]
                if owner["kind"] != "OFF_BALANCE" or owner["copy_id"] != block["copy_id"]:
                    raise WaveOneRoleALevelOneReferenceError(
                        f"{bank} standalone off-balance block does not own its page segment"
                    )
        elif block["placement"] == "EMBEDDED_BOTTOM_REGION":
            parent = block_by_id.get(block["parent_block_id"])
            if (
                block["start_page"] != block["end_page"]
                or parent is None
                or parent["block_type"] != "CDKT_MAIN"
                or parent["copy_id"] != block["copy_id"]
                or not (parent["start_page"] <= block["start_page"] <= parent["end_page"])
            ):
                raise WaveOneRoleALevelOneReferenceError(
                    f"{bank} embedded off-balance parent relationship is invalid"
                )
            owner = page_owner[block["start_page"]]
            if (
                owner["kind"] != "CDKT_MAIN"
                or owner["copy_id"] != block["copy_id"]
                or block["start_page"] not in owner["embedded_off_balance_pages"]
            ):
                raise WaveOneRoleALevelOneReferenceError(
                    f"{bank} embedded off-balance incidence is absent from page partition"
                )
        else:
            for page in range(block["start_page"], block["end_page"] + 1):
                owner = page_owner[page]
                if owner["kind"] != block["block_type"] or owner["copy_id"] != block["copy_id"]:
                    raise WaveOneRoleALevelOneReferenceError(
                        f"{bank} statement block does not match its primary page segment"
                    )

    for index, first in enumerate(blocks):
        first_pages = set(range(first["start_page"], first["end_page"] + 1))
        for second in blocks[index + 1 :]:
            overlap = first_pages & set(range(second["start_page"], second["end_page"] + 1))
            if not overlap:
                continue
            embedded, parent = (
                (first, second)
                if first["placement"] == "EMBEDDED_BOTTOM_REGION"
                else (second, first)
            )
            if (
                embedded["placement"] != "EMBEDDED_BOTTOM_REGION"
                or embedded["parent_block_id"] != parent["block_id"]
                or overlap != {embedded["start_page"]}
            ):
                raise WaveOneRoleALevelOneReferenceError(
                    f"{bank} statement blocks overlap without an embedded incidence"
                )

    for segment in segments:
        if segment["kind"] not in _STATEMENT_BLOCK_TYPES:
            continue
        for page in range(segment["start_page"], segment["end_page"] + 1):
            owners = [
                block
                for block in blocks
                if block["placement"] != "EMBEDDED_BOTTOM_REGION"
                and block["block_type"] == segment["kind"]
                and block["copy_id"] == segment["copy_id"]
                and block["start_page"] <= page <= block["end_page"]
            ]
            if len(owners) != 1:
                raise WaveOneRoleALevelOneReferenceError(
                    f"{bank} statement page is not owned by exactly one primary block"
                )
        declared_embedded = set(segment["embedded_off_balance_pages"])
        observed_embedded = {
            block["start_page"]
            for block in blocks
            if block["placement"] == "EMBEDDED_BOTTOM_REGION"
            and block["copy_id"] == segment["copy_id"]
            and segment["start_page"] <= block["start_page"] <= segment["end_page"]
            and block_by_id[block["parent_block_id"]]["block_type"] == segment["kind"]
        }
        if declared_embedded != observed_embedded:
            raise WaveOneRoleALevelOneReferenceError(
                f"{bank} embedded incidences do not match the primary page segment"
            )

    counts = Counter(block["block_type"] for block in blocks)
    if any(counts[block_type] < 1 for block_type in _STATEMENT_BLOCK_TYPES):
        raise WaveOneRoleALevelOneReferenceError(
            f"{bank} does not contain every required Level-1 statement block"
        )
    if counts["TM"] != 1:
        raise WaveOneRoleALevelOneReferenceError(f"{bank} must have exactly one TM block")

    if not isinstance(record["tm_subdivisions"], list):
        raise WaveOneRoleALevelOneReferenceError(f"{bank} TM subdivisions are invalid")
    subdivisions = [_expand_tm_subdivision(value, bank) for value in record["tm_subdivisions"]]
    if subdivisions:
        tm_block = next(block for block in blocks if block["block_type"] == "TM")
        expected_page = tm_block["start_page"]
        for subdivision in subdivisions:
            if subdivision["start_page"] != expected_page:
                raise WaveOneRoleALevelOneReferenceError(
                    f"{bank} TM subdivisions have a gap or overlap"
                )
            expected_page = subdivision["end_page"] + 1
        if expected_page != tm_block["end_page"] + 1:
            raise WaveOneRoleALevelOneReferenceError(
                f"{bank} TM subdivisions do not partition TM exactly"
            )

    _validate_duplicate_presentation(record["duplicate_presentation"], blocks, bank)
    return {
        "bank": bank,
        "scope": record["scope"],
        "unit": record["unit"],
        "reporting_period": record["reporting_period"],
        "lctt_method": record["lctt_method"],
        "form_codes": record["form_codes"],
        "page_segments": segments,
        "statement_blocks": blocks,
        "tm_subdivisions": subdivisions,
        "duplicate_presentation": record["duplicate_presentation"],
        "notes": record["notes"],
    }


def _validate_reference_source_header(source: dict[str, Any]) -> list[dict[str, Any]]:
    _require_exact_fields(
        source,
        {
            "version",
            "format_version",
            "status",
            "claim_boundary",
            "evidence_authority",
            "page_basis",
            "reference_role",
            "human_gold",
            "role_b_output",
            "row_reference",
            "value_reference",
            "canonical_reference",
            "tuple_contract",
            "records",
        },
        "reference source",
    )
    if (
        source["version"] != 1
        or source["format_version"] != "BANK_CORPUS_WAVE_1_ROLE_A_LEVEL_1_BOUNDARY_SOURCE_V1"
        or source["status"] != "ROLE_A_LEVEL_1_MACHINE_REFERENCE"
        or source["claim_boundary"] != "STRUCTURAL_BOUNDARIES_ONLY"
        or source["evidence_authority"] != "VISIBLE_RENDERED_PIXELS"
        or source["page_basis"] != "ONE_BASED_PHYSICAL_PDF_PAGE"
        or source["reference_role"] != "ROLE_A"
        or source["human_gold"] is not False
        or source["role_b_output"] is not False
        or source["row_reference"] is not False
        or source["value_reference"] is not False
        or source["canonical_reference"] is not False
    ):
        raise WaveOneRoleALevelOneReferenceError("reference source authority drifted")
    if source["tuple_contract"] != {
        "page_segment": [
            "kind",
            "start_page",
            "end_page",
            "copy_id",
            "embedded_off_balance_pages",
        ],
        "statement_block": [
            "block_id",
            "block_type",
            "start_page",
            "end_page",
            "copy_id",
            "placement",
            "parent_block_id",
            "visible_unit_override",
        ],
        "tm_subdivision": ["kind", "start_page", "end_page"],
    }:
        raise WaveOneRoleALevelOneReferenceError("reference tuple contract drifted")
    if not isinstance(source["records"], list):
        raise WaveOneRoleALevelOneReferenceError("reference records are missing")
    return source["records"]


def _verify_local_source_pdf(project_root: Path, source: dict[str, Any]) -> None:
    path = _resolve_under_root(project_root, source["relative_path"], "selected source PDF")
    if path.is_symlink() or not path.is_file():
        raise WaveOneRoleALevelOneReferenceError(
            f"{source['bank']} selected source PDF is not a regular local file"
        )
    before = path.stat()
    if before.st_size != source["size_bytes"] or sha256_file(path) != source["sha256"]:
        raise WaveOneRoleALevelOneReferenceError(
            f"{source['bank']} selected source PDF byte identity drifted"
        )
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise WaveOneRoleALevelOneReferenceError(
            f"{source['bank']} selected source PDF changed while hashing"
        )
    try:
        import fitz

        with fitz.open(path) as document:
            observed_page_count = document.page_count
    except Exception as error:
        raise WaveOneRoleALevelOneReferenceError(
            f"{source['bank']} selected source PDF page count could not be verified"
        ) from error
    if observed_page_count != source["page_count"]:
        raise WaveOneRoleALevelOneReferenceError(
            f"{source['bank']} selected source PDF page count drifted"
        )


def build_wave_one_role_a_level_one_boundaries(
    project_root: Path,
    policy_path: Path | None = None,
    *,
    verify_source_pdfs: bool = False,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    policy_path = policy_path or project_root / POLICY_RELATIVE_PATH
    policy = load_wave_one_role_a_level_one_policy(policy_path, project_root)

    inventory, inventory_binding = _load_bound_json(
        project_root, policy["upstream_binding"]["inventory"], "bound corpus inventory"
    )
    source_profile, profile_binding = _load_bound_json(
        project_root,
        policy["upstream_binding"]["source_profile"],
        "bound Wave-1 source profile",
    )
    source, source_binding = _load_reference_source(project_root, policy["reference_source"])
    source_records = _validate_reference_source_header(source)

    wave = inventory.get("wave_1")
    if not isinstance(wave, dict) or not isinstance(wave.get("selected_documents"), list):
        raise WaveOneRoleALevelOneReferenceError("inventory Wave-1 selection is malformed")
    selected = wave["selected_documents"]
    receipt = _selection_receipt(selected)
    expected_receipt = policy["upstream_binding"]["selection_receipt_sha256"]
    if receipt != expected_receipt or wave.get("selection_receipt_sha256") != expected_receipt:
        raise WaveOneRoleALevelOneReferenceError("inventory selection receipt drifted")
    if source_profile.get("selection_receipt_sha256") != expected_receipt:
        raise WaveOneRoleALevelOneReferenceError("source-profile selection receipt drifted")

    selected_by_bank = _indexed_records(selected, "inventory selected documents")
    profile_by_bank = _indexed_records(source_profile.get("profiles"), "source profiles")
    reference_by_bank = _indexed_records(source_records, "boundary references")
    expected_bank_count = policy["identity_join"]["expected_bank_count"]
    bank_set = set(selected_by_bank)
    if (
        len(bank_set) != expected_bank_count
        or set(profile_by_bank) != bank_set
        or set(reference_by_bank) != bank_set
    ):
        raise WaveOneRoleALevelOneReferenceError(
            "inventory, source profile, and boundary source do not have the same banks"
        )

    documents: list[dict[str, Any]] = []
    scope_counts: Counter[str] = Counter()
    method_counts: Counter[str] = Counter()
    segment_counts: Counter[str] = Counter()
    block_counts: Counter[str] = Counter()
    physical_page_count = 0
    unique_statement_page_count = 0
    statement_block_page_incidence_count = 0
    embedded_off_balance_count = 0
    duplicate_document_count = 0
    for bank in sorted(bank_set):
        selected_record = selected_by_bank[bank]
        profile = profile_by_bank[bank]
        for field in ("document_id", "relative_path", "sha256", "size_bytes"):
            if profile.get(field) != selected_record.get(field):
                raise WaveOneRoleALevelOneReferenceError(
                    f"{bank} inventory/source-profile identity drifted"
                )
        page_count = profile.get("page_count")
        if not isinstance(page_count, int) or isinstance(page_count, bool) or page_count < 1:
            raise WaveOneRoleALevelOneReferenceError(f"{bank} source-profile page count is invalid")
        if _SOURCE_IDENTITY_FIELDS & set(reference_by_bank[bank]):
            raise WaveOneRoleALevelOneReferenceError(
                f"{bank} boundary source contains forbidden identity fields"
            )
        structure = _validate_reference_record(reference_by_bank[bank], page_count)
        source_identity = {
            "bank": bank,
            "document_id": selected_record["document_id"],
            "relative_path": selected_record["relative_path"],
            "sha256": selected_record["sha256"],
            "size_bytes": selected_record["size_bytes"],
            "page_count": page_count,
            "identity_source": "BOUND_WAVE_1_INVENTORY_WITH_PAGE_COUNT_FROM_BOUND_SOURCE_PROFILE",
        }
        if verify_source_pdfs:
            _verify_local_source_pdf(project_root, source_identity)

        statement_pages = {
            page
            for block in structure["statement_blocks"]
            for page in range(block["start_page"], block["end_page"] + 1)
        }
        incidences = sum(
            block["end_page"] - block["start_page"] + 1 for block in structure["statement_blocks"]
        )
        document_accounting = {
            "physical_page_count": page_count,
            "partitioned_physical_page_count": sum(
                segment["end_page"] - segment["start_page"] + 1
                for segment in structure["page_segments"]
            ),
            "unique_statement_page_count": len(statement_pages),
            "statement_block_page_incidence_count": incidences,
            "statement_block_count": len(structure["statement_blocks"]),
            "embedded_off_balance_block_count": sum(
                block["placement"] == "EMBEDDED_BOTTOM_REGION"
                for block in structure["statement_blocks"]
            ),
        }
        documents.append(
            {
                "source": source_identity,
                **structure,
                "accounting": document_accounting,
                "reference_status": "ROLE_A_LEVEL_1_MACHINE_REFERENCE",
                "claim_boundary": "STRUCTURAL_BOUNDARIES_ONLY",
                "evidence_authority": "VISIBLE_RENDERED_PIXELS",
                "page_basis": "ONE_BASED_PHYSICAL_PDF_PAGE",
            }
        )
        physical_page_count += page_count
        unique_statement_page_count += len(statement_pages)
        statement_block_page_incidence_count += incidences
        embedded_off_balance_count += document_accounting["embedded_off_balance_block_count"]
        duplicate_document_count += (
            structure["duplicate_presentation"]["status"]
            == "MULTIPLE_FORMAL_SCALE_VARIANTS_OBSERVED"
        )
        scope_counts[structure["scope"]["status"]] += 1
        method_counts[structure["lctt_method"]["status"]] += 1
        segment_counts.update(segment["kind"] for segment in structure["page_segments"])
        block_counts.update(block["block_type"] for block in structure["statement_blocks"])

    accounting = {
        "document_count": len(documents),
        "physical_page_count": physical_page_count,
        "partitioned_physical_page_count": sum(
            document["accounting"]["partitioned_physical_page_count"] for document in documents
        ),
        "unique_statement_page_count": unique_statement_page_count,
        "statement_block_page_incidence_count": statement_block_page_incidence_count,
        "statement_block_count": sum(block_counts.values()),
        "statement_block_counts": dict(sorted(block_counts.items())),
        "page_segment_counts": dict(sorted(segment_counts.items())),
        "embedded_off_balance_block_count": embedded_off_balance_count,
        "duplicate_presentation_document_count": duplicate_document_count,
        "scope_status_counts": dict(sorted(scope_counts.items())),
        "lctt_method_status_counts": dict(sorted(method_counts.items())),
        "source_accounted_visible_row_count": 0,
        "source_accounted_visible_value_cell_count": 0,
        "canonical_mapped_row_count": 0,
        "human_gold_document_count": 0,
        "role_b_document_count": 0,
    }
    expected = policy["expected_accounting"]
    expected_projection = {
        key: accounting[key]
        for key in (
            "document_count",
            "physical_page_count",
            "statement_block_count",
            "embedded_off_balance_block_count",
            "duplicate_presentation_document_count",
            "scope_status_counts",
            "lctt_method_status_counts",
        )
    }
    if expected_projection != expected:
        raise WaveOneRoleALevelOneReferenceError(
            "built Role-A Level-1 accounting differs from the sealed policy"
        )
    if accounting["partitioned_physical_page_count"] != accounting["physical_page_count"]:
        raise WaveOneRoleALevelOneReferenceError("corpus physical-page partition is incomplete")

    implementation_path = project_root / IMPLEMENTATION_RELATIVE_PATH
    implementation_bytes = _read_stable_bytes(implementation_path, "Role-A Level-1 implementation")
    policy_bytes = _read_stable_bytes(policy_path, "Role-A Level-1 policy")
    return {
        "format_version": policy["output"]["format_version"],
        "status": policy["output"]["status"],
        "claim_boundary": policy["output"]["claim_boundary"],
        "authority": policy["authority"],
        "selection_receipt_sha256": expected_receipt,
        "upstream": {
            "inventory": inventory_binding,
            "source_profile": profile_binding,
        },
        "reference_source": source_binding,
        "policy": {
            "path": POLICY_RELATIVE_PATH.as_posix(),
            "sha256": sha256_bytes(policy_bytes),
            "size_bytes": len(policy_bytes),
        },
        "implementation": {
            "path": IMPLEMENTATION_RELATIVE_PATH.as_posix(),
            "sha256": sha256_bytes(implementation_bytes),
            "size_bytes": len(implementation_bytes),
        },
        "page_partition_contract": policy["page_partition"],
        "accounting": accounting,
        "documents": documents,
        "negative_claims": {
            "human_gold": False,
            "role_b_output": False,
            "source_complete_extraction": False,
            "visible_rows_accounted": False,
            "visible_values_accounted": False,
            "canonical_mapping_attempted": False,
            "canonical_completeness": False,
            "schema_used": False,
            "canonical_double_count_authorized": False,
        },
    }


def _assert_committed_clean_inputs(project_root: Path, relative_paths: list[str]) -> None:
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise WaveOneRoleALevelOneReferenceError(
            "publication requires a Git worktree with committed inputs"
        ) from error
    if Path(top).resolve() != project_root:
        raise WaveOneRoleALevelOneReferenceError(
            "publication project root is not the Git worktree root"
        )
    for relative in relative_paths:
        _canonical_relative_path(relative, "committed input")
        try:
            subprocess.run(
                ["git", "ls-files", "--error-unmatch", "--", relative],
                cwd=project_root,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "diff", "--quiet", "--", relative],
                cwd=project_root,
                check=True,
            )
            subprocess.run(
                ["git", "diff", "--cached", "--quiet", "--", relative],
                cwd=project_root,
                check=True,
            )
        except (OSError, subprocess.CalledProcessError) as error:
            raise WaveOneRoleALevelOneReferenceError(
                f"publication input is uncommitted or dirty: {relative}"
            ) from error


def _exclusive_write(path: Path, encoded: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    mode = path.stat().st_mode
    if not stat.S_ISREG(mode) or path.is_symlink():
        raise WaveOneRoleALevelOneReferenceError("published reference is not a regular file")


def publish_wave_one_role_a_level_one_boundaries(
    project_root: Path, output_path: Path | None = None
) -> tuple[Path, str, int]:
    project_root = project_root.resolve()
    policy_path = project_root / POLICY_RELATIVE_PATH
    policy = load_wave_one_role_a_level_one_policy(policy_path, project_root)
    _assert_committed_clean_inputs(project_root, policy["output"]["required_committed_paths"])
    canonical_output = (project_root / OUTPUT_RELATIVE_PATH).resolve()
    requested_output = (output_path or canonical_output).resolve()
    if requested_output != canonical_output:
        raise WaveOneRoleALevelOneReferenceError(
            f"publication requires canonical output {OUTPUT_RELATIVE_PATH}"
        )
    payload = build_wave_one_role_a_level_one_boundaries(
        project_root, policy_path, verify_source_pdfs=True
    )
    encoded = _canonical_json_bytes(payload)
    _exclusive_write(requested_output, encoded)
    return requested_output, sha256_bytes(encoded), len(encoded)
