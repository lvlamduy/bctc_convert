from __future__ import annotations

import copy
import json
import math
import os
import re
import subprocess
import tempfile
from collections import Counter
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.axes.header_binding import HeaderBinding, bind_value_headers
from bctc_ai.core.contracts import BoundingBox, ObservationKind, RowType
from bctc_ai.core.hashing import sha256_bytes, sha256_file, stable_records_hash
from bctc_ai.core.text import normalize_text, parse_financial_number
from bctc_ai.ocr.native_text_quality_v2 import (
    extract_pdf_text_v2,
    load_native_text_quality_v2_config,
)
from bctc_ai.rows.pdf_statement import (
    GeometryCell,
    StatementRow,
    financial_table_span,
    reconstruct_statement_rows,
)
from bctc_ai.tables.geometry import (
    ColumnAxis,
    PageGeometry,
    TextRun,
    analyze_page_geometry,
    load_geometry_config,
)

POLICY_RELATIVE_PATH = Path("config/rows/native-statement-rows-v1.yaml")

_POLICY_NAME = "REGISTERED_NATIVE_STATEMENT_ROWS_V1"
_OUTPUT_FORMAT = "REGISTERED_NATIVE_STATEMENT_ROWS_RESULT_V1"
_OUTPUT_STATUS = "ACCEPTED_NATIVE_STATEMENT_ROWS"
_CLAIM_BOUNDARY = "UNMAPPED_SOURCE_ROWS_AND_CELLS_ONLY"
_NATIVE_GEOMETRY_AUTHORITY = "PYMUPDF_NATIVE_TEXT_WORDS"
_NATIVE_GEOMETRY_EVIDENCE = "PYMUPDF_NATIVE_TEXT_GEOMETRY"
_SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_GIT_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_ROLES = {
    "LOGIC_DEVELOPMENT",
    "CALIBRATION",
    "VALIDATION",
    "PRODUCTION_INPUT",
}
_FORBIDDEN_ROLES = {"UNTOUCHED_HOLDOUT"}
_ROLE_DIRECTORIES = {
    "LOGIC_DEVELOPMENT": "output/development",
    "CALIBRATION": "output/calibration",
    "VALIDATION": "output/validation",
    "PRODUCTION_INPUT": "output/production",
}
_IMPLEMENTATION_PATHS = (
    "src/bctc_ai/core/contracts.py",
    "src/bctc_ai/core/text.py",
    "src/bctc_ai/ocr/pdf_text.py",
    "src/bctc_ai/ocr/native_text_quality_v2.py",
    "src/bctc_ai/tables/geometry.py",
    "src/bctc_ai/rows/pdf_statement.py",
    "src/bctc_ai/axes/header_binding.py",
    "src/bctc_ai/rows/native_statement.py",
)


class NativeStatementRowsError(RuntimeError):
    pass


@dataclass(frozen=True)
class NativeStatementRowsPublication:
    path: Path
    sha256: str
    size_bytes: int
    payload: dict[str, Any]


def _resolve_under_root(project_root: Path, raw_path: str, label: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path or Path(raw_path).is_absolute():
        raise NativeStatementRowsError(f"{label} must be a project-relative path")
    path = (project_root / raw_path).resolve()
    try:
        path.relative_to(project_root)
    except ValueError as exc:
        raise NativeStatementRowsError(f"{label} escapes the project root") from exc
    return path


def _relative_path(project_root: Path, path: Path, label: str) -> str:
    try:
        return path.resolve().relative_to(project_root).as_posix()
    except ValueError as exc:
        raise NativeStatementRowsError(f"{label} must stay inside the project root") from exc


def _validate_identity_file(project_root: Path, raw: Any, label: str) -> tuple[Path, str]:
    if not isinstance(raw, dict) or set(raw) != {"path", "sha256"}:
        raise NativeStatementRowsError(f"{label} identity must contain path and sha256")
    path = _resolve_under_root(project_root, raw["path"], label)
    expected = raw["sha256"]
    if not isinstance(expected, str) or len(expected) != 64 or not path.is_file():
        raise NativeStatementRowsError(f"{label} identity is invalid or absent")
    if sha256_file(path) != expected:
        raise NativeStatementRowsError(f"{label} hash drifted")
    return path, expected


def load_native_statement_rows_policy(path: Path, project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    path = path.resolve()
    if path != (project_root / POLICY_RELATIVE_PATH).resolve():
        raise NativeStatementRowsError(
            f"native statement rows require canonical policy {POLICY_RELATIVE_PATH}"
        )
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise NativeStatementRowsError(f"cannot load native statement rows policy: {path}") from exc
    identities = {
        "version": 1,
        "policy": _POLICY_NAME,
        "claim_boundary": _CLAIM_BOUNDARY,
        "source_registry": "data/registered/source_registry.jsonl",
        "dataset_role_registry": "data/registered/dataset_roles.jsonl",
        "require_clean_git": True,
        "require_registered_pdf": True,
        "require_hash_verified_stable": True,
    }
    if not isinstance(payload, dict) or any(
        payload.get(key) != value for key, value in identities.items()
    ):
        raise NativeStatementRowsError("native statement rows policy identity drifted")
    if set(payload.get("allowed_dataset_roles", ())) != _ALLOWED_ROLES:
        raise NativeStatementRowsError("native statement rows allowed-role policy drifted")
    if set(payload.get("forbidden_dataset_roles", ())) != _FORBIDDEN_ROLES:
        raise NativeStatementRowsError("native statement rows forbidden-role policy drifted")

    _validate_identity_file(
        project_root, payload.get("native_text_quality_config"), "native-text quality config"
    )
    _validate_identity_file(project_root, payload.get("geometry_config"), "geometry config")
    if payload.get("accepted_statement_discovery") != {
        "format_version": "REGISTERED_NATIVE_TEXT_STATEMENT_DISCOVERY_RESULT_V1",
        "policy": "REGISTERED_NATIVE_TEXT_STATEMENT_DISCOVERY_V1",
        "claim_boundary": "STATEMENT_PAGE_DISCOVERY_ONLY",
        "status": "ACCEPTED_NATIVE_TEXT_STATEMENT_DISCOVERY",
        "inner_policy": "NATIVE_TEXT_MULTI_SIGNAL_ORDERED_DOCUMENT_DISCOVERY_V1",
        "inner_status": "ACCEPTED_MULTI_SIGNAL_STATEMENT_BLOCK",
        "geometry_authority": _NATIVE_GEOMETRY_AUTHORITY,
        "evidence_source": _NATIVE_GEOMETRY_EVIDENCE,
    }:
        raise NativeStatementRowsError("accepted statement-discovery contract drifted")
    if payload.get("page_selection") != {
        "main_statement_types": ["CDKT", "KQKD", "LCTT"],
        "main_scope": "MAIN_STATEMENT",
        "require_mapping_eligible": True,
        "include_recognized_cdkt_off_balance": True,
        "off_balance_statement_type": "CDKT",
        "off_balance_scope": "OFF_BALANCE_SHEET",
        "require_local_or_bounded_inference": True,
        "allow_bounded_inferred_page_contracts": True,
        "notes_pages_allowed": False,
    }:
        raise NativeStatementRowsError("native statement page-selection policy drifted")
    if payload.get("row_reconstruction") != {
        "extractor": "NATIVE_TEXT_QUALITY_V2_SELECTED_PAGES_ONLY",
        "geometry": "GEOMETRY_V2_NATIVE_WORD_BOXES",
        "row_assembler": "PDF_STATEMENT_ROWS",
        "table_span": "FINANCIAL_TABLE_SPAN",
        "header_binding": "AXIS_LOCAL_VISIBLE_HEADER_BINDING",
        "preserve_section_headers": True,
        "preserve_unlabeled_numeric_rows": True,
        "preserve_rows_outside_financial_span_for_audit": True,
    }:
        raise NativeStatementRowsError("native statement row-reconstruction policy drifted")
    isolation = payload.get("role_isolation")
    if not isinstance(isolation, dict):
        raise NativeStatementRowsError("native statement rows isolation policy is absent")
    expected_input_kinds = {
        "SOURCE_PDF",
        "SOURCE_REGISTRY",
        "DATASET_ROLE_REGISTRY",
        "ACCEPTED_STATEMENT_DISCOVERY",
        "THIS_POLICY",
        "NATIVE_TEXT_QUALITY_CONFIG",
        "GEOMETRY_CONFIG",
    }
    if set(isolation.get("runtime_input_allowlist", ())) != expected_input_kinds:
        raise NativeStatementRowsError("native statement rows runtime-input allowlist drifted")
    if any(
        isolation.get(key) is not False
        for key in (
            "prior_answer_artifacts_allowed",
            "historical_values_allowed",
            "role_a_outputs_allowed",
            "schema_inputs_allowed",
            "template_inputs_allowed",
        )
    ):
        raise NativeStatementRowsError("native statement rows answer isolation was weakened")
    fragments = isolation.get("forbidden_path_fragments")
    if (
        not isinstance(fragments, list)
        or not fragments
        or any(
            not isinstance(fragment, str) or not fragment.startswith("/") for fragment in fragments
        )
    ):
        raise NativeStatementRowsError("native statement rows forbidden-path policy is invalid")
    if payload.get("output") != {
        "format": _OUTPUT_FORMAT,
        "status": _OUTPUT_STATUS,
        "exclusive_no_overwrite": True,
        "absolute_project_paths_allowed": False,
        "source_visible_text_preserved_verbatim": True,
        "deterministic_json": True,
        "role_directories": _ROLE_DIRECTORIES,
    }:
        raise NativeStatementRowsError("native statement rows output contract drifted")
    return copy.deepcopy(payload)


def _read_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise NativeStatementRowsError(f"cannot read {label}: {path}") from exc
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise NativeStatementRowsError(f"{label} line {line_number} is invalid JSON") from exc
        if not isinstance(record, dict):
            raise NativeStatementRowsError(f"{label} line {line_number} must be a JSON object")
        records.append(record)
    return records


def _registered_source(
    project_root: Path,
    source_pdf: Path,
    policy: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], str, str]:
    source_pdf = source_pdf.resolve()
    source_relative = _relative_path(project_root, source_pdf, "source PDF")
    if not source_pdf.is_file() or source_pdf.suffix.casefold() != ".pdf":
        raise NativeStatementRowsError("registered source PDF is absent or not a PDF")
    source_registry_path = _resolve_under_root(
        project_root, policy["source_registry"], "source registry"
    )
    role_registry_path = _resolve_under_root(
        project_root, policy["dataset_role_registry"], "dataset-role registry"
    )
    source_matches = [
        record
        for record in _read_jsonl(source_registry_path, "source registry")
        if record.get("relative_path") == source_relative
    ]
    if len(source_matches) != 1:
        raise NativeStatementRowsError(
            f"source PDF must have exactly one registry record; found {len(source_matches)}"
        )
    source_record = source_matches[0]
    source_sha256 = sha256_file(source_pdf)
    document_id = f"sha256:{source_sha256}"
    if (
        source_record.get("sha256") != source_sha256
        or source_record.get("document_id") != document_id
        or source_record.get("size_bytes") != source_pdf.stat().st_size
        or source_record.get("kind") != "PDF"
        or source_record.get("state") != "REGISTERED"
        or source_record.get("hash_verified_stable") is not True
    ):
        raise NativeStatementRowsError("source PDF registry identity drifted")
    role_matches = [
        record
        for record in _read_jsonl(role_registry_path, "dataset-role registry")
        if record.get("document_id") == document_id
    ]
    if len(role_matches) != 1:
        raise NativeStatementRowsError(
            f"source PDF must have exactly one role record; found {len(role_matches)}"
        )
    role_record = role_matches[0]
    role = role_record.get("dataset_role")
    if role in _FORBIDDEN_ROLES:
        raise NativeStatementRowsError(
            f"source PDF dataset role {role} is forbidden for this runner"
        )
    if (
        role not in _ALLOWED_ROLES
        or role_record.get("source_path") != source_relative
        or role_record.get("immutable") is not True
    ):
        raise NativeStatementRowsError("source PDF dataset role is not eligible")
    return source_record, role_record, source_sha256, source_relative


def _git(project_root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise NativeStatementRowsError(f"git {' '.join(arguments)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _current_git_state(project_root: Path) -> dict[str, Any]:
    return {
        "commit": _git(project_root, "rev-parse", "HEAD"),
        "dirty": bool(_git(project_root, "status", "--porcelain", "--untracked-files=all")),
    }


def _file_identity_at_commit(
    project_root: Path,
    commit: str,
    raw_path: str,
) -> dict[str, Any]:
    if _GIT_COMMIT.fullmatch(commit) is None:
        raise NativeStatementRowsError("native statement rows producer commit is invalid")
    result = subprocess.run(
        ["git", "show", f"{commit}:{raw_path}"],
        cwd=project_root,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise NativeStatementRowsError(
            f"native statement rows producer commit lacks tracked input: {raw_path}"
        )
    return {
        "path": raw_path,
        "sha256": sha256_bytes(result.stdout),
        "size_bytes": len(result.stdout),
    }


def _implementation_ledger_at_commit(
    project_root: Path,
    commit: str,
) -> list[dict[str, Any]]:
    return [
        _file_identity_at_commit(project_root, commit, raw_path)
        for raw_path in _IMPLEMENTATION_PATHS
    ]


def _validate_git_state(git_state: dict[str, Any]) -> dict[str, Any]:
    commit = git_state.get("commit") if isinstance(git_state, dict) else None
    dirty = git_state.get("dirty") if isinstance(git_state, dict) else None
    if (
        not isinstance(commit, str)
        or _GIT_COMMIT.fullmatch(commit) is None
        or type(dirty) is not bool
    ):
        raise NativeStatementRowsError("native statement rows Git state is invalid")
    if dirty:
        raise NativeStatementRowsError("refusing native statement rows from a dirty worktree")
    return {"commit": commit, "dirty": False}


def _identity_record(project_root: Path, path: Path, kind: str) -> dict[str, Any]:
    path = path.resolve()
    relative = _relative_path(project_root, path, "runtime input")
    if not path.is_file():
        raise NativeStatementRowsError(f"runtime input is absent: {relative}")
    return {
        "kind": kind,
        "path": relative,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _runtime_input_ledger(
    project_root: Path,
    inputs: list[tuple[Path, str]],
) -> list[dict[str, Any]]:
    records = [_identity_record(project_root, path, kind) for path, kind in inputs]
    records.sort(key=lambda item: (item["kind"], item["path"]))
    return records


def _implementation_ledger(project_root: Path) -> list[dict[str, Any]]:
    records = []
    for raw_path in _IMPLEMENTATION_PATHS:
        path = _resolve_under_root(project_root, raw_path, "implementation module")
        if not path.is_file():
            raise NativeStatementRowsError(f"implementation module is absent: {raw_path}")
        records.append(
            {"path": raw_path, "sha256": sha256_file(path), "size_bytes": path.stat().st_size}
        )
    return records


def _load_discovery_bytes(path: Path) -> tuple[bytes, dict[str, Any]]:
    try:
        encoded = path.read_bytes()
        payload = json.loads(encoded)
    except (OSError, json.JSONDecodeError) as exc:
        raise NativeStatementRowsError(f"cannot load accepted statement discovery: {path}") from exc
    if not isinstance(payload, dict):
        raise NativeStatementRowsError("accepted statement discovery must be a JSON object")
    return encoded, payload


def _validate_path_isolation(relative_paths: list[str], policy: dict[str, Any]) -> None:
    normalized_paths = [f"/{path.casefold().strip('/')}" for path in relative_paths]
    forbidden = [
        fragment.casefold() for fragment in policy["role_isolation"]["forbidden_path_fragments"]
    ]
    if any(fragment in path for path in normalized_paths for fragment in forbidden):
        raise NativeStatementRowsError("runtime input ledger contains a forbidden path")


def _validate_discovery_contract(
    discovery: dict[str, Any],
    *,
    policy: dict[str, Any],
    source_record: dict[str, Any],
    role_record: dict[str, Any],
    source_relative: str,
    source_sha256: str,
) -> list[dict[str, Any]]:
    expected = policy["accepted_statement_discovery"]
    if any(
        discovery.get(key) != expected[key]
        for key in ("format_version", "policy", "claim_boundary", "status")
    ):
        raise NativeStatementRowsError("statement discovery outer acceptance contract is invalid")
    authority = discovery.get("authority")
    if (
        not isinstance(authority, dict)
        or authority.get("geometry") != expected["geometry_authority"]
        or authority.get("evidence_source") != expected["evidence_source"]
        or authority.get("semantic_reader") is not None
    ):
        raise NativeStatementRowsError("statement discovery native authority is invalid")
    inner = discovery.get("discovery")
    if (
        not isinstance(inner, dict)
        or inner.get("policy") != expected["inner_policy"]
        or inner.get("status") != expected["inner_status"]
        or inner.get("geometry_authority") != expected["geometry_authority"]
    ):
        raise NativeStatementRowsError("statement discovery inner acceptance contract is invalid")
    isolation = discovery.get("isolation")
    if not isinstance(isolation, dict) or any(
        isolation.get(key) is not False
        for key in (
            "prior_answer_artifacts_loaded",
            "historical_values_loaded",
            "role_a_outputs_loaded",
            "bank_identity_used_for_scoring",
            "filename_identity_used_for_scoring",
            "page_number_rules_used_for_scoring",
        )
    ):
        raise NativeStatementRowsError("statement discovery isolation contract is invalid")
    source = discovery.get("source")
    if not isinstance(source, dict) or any(
        source.get(key) != value
        for key, value in {
            "document_id": source_record["document_id"],
            "relative_path": source_relative,
            "sha256": source_sha256,
            "size_bytes": source_record["size_bytes"],
            "dataset_role": role_record["dataset_role"],
            "registry_state": "REGISTERED",
            "hash_verified_stable": True,
            "immutable_role_assignment": True,
        }.items()
    ):
        raise NativeStatementRowsError("statement discovery source identity does not match PDF")
    discovery_code = discovery.get("code")
    if (
        not isinstance(discovery_code, dict)
        or _GIT_COMMIT.fullmatch(str(discovery_code.get("commit", ""))) is None
        or discovery_code.get("dirty") is not False
    ):
        raise NativeStatementRowsError("statement discovery was not produced from clean code")
    native_text = discovery.get("native_text")
    if (
        not isinstance(native_text, dict)
        or native_text.get("all_pages_usable") is not True
        or native_text.get("ocr_required_pages") != []
    ):
        raise NativeStatementRowsError("statement discovery does not authorize native-only rows")

    block = inner.get("block")
    contracts = block.get("page_contracts") if isinstance(block, dict) else None
    if not isinstance(contracts, list) or not contracts:
        raise NativeStatementRowsError("statement discovery has no accepted page contracts")
    page_selection = policy["page_selection"]
    main_types = set(page_selection["main_statement_types"])
    selected: list[dict[str, Any]] = []
    seen_pages: set[int] = set()
    for raw in contracts:
        if not isinstance(raw, dict):
            raise NativeStatementRowsError("statement page contract must be an object")
        page = raw.get("page")
        statement_type = raw.get("statement_type")
        scope = raw.get("scope")
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            raise NativeStatementRowsError("statement page contract has an invalid page")
        is_main = (
            statement_type in main_types
            and scope == page_selection["main_scope"]
            and raw.get("mapping_eligible") is True
        )
        is_off_balance = (
            statement_type == page_selection["off_balance_statement_type"]
            and scope == page_selection["off_balance_scope"]
            and raw.get("mapping_eligible") is False
        )
        if not is_main and not is_off_balance:
            raise NativeStatementRowsError("accepted block contains an unsupported page contract")
        locally_accepted = raw.get("locally_accepted") is True
        inference_checks = raw.get("inference_checks")
        inferred_from_page = raw.get("inferred_from_page")
        inference_direction = raw.get("inference_direction")
        bounded_inference = (
            raw.get("locally_accepted") is False
            and scope == page_selection["main_scope"]
            and isinstance(inferred_from_page, int)
            and not isinstance(inferred_from_page, bool)
            and inferred_from_page >= 1
            and isinstance(inference_checks, list)
            and bool(inference_checks)
            and all(isinstance(check, str) and check for check in inference_checks)
            and inference_direction
            in {
                "FORWARD_FROM_PREVIOUS",
                "BACKWARD_FROM_NEXT",
            }
        )
        if bounded_inference:
            check_set = set(inference_checks)
            base_checks = {
                "ACCOUNTING_ROWS",
                "NUMERIC_GEOMETRY",
                "SHARED_NUMERIC_AXES",
            }
            compatibility_checks = {
                "SHARED_PERIOD_AXIS",
                "SHARED_UNIT",
                "CONTINUATION_MARKER",
                "TABLE_EDGE_CONTINUITY",
            }
            allowed_checks = base_checks | compatibility_checks
            metadata_or_edge = (
                {"SHARED_PERIOD_AXIS", "SHARED_UNIT"} <= check_set
                or (
                    "CONTINUATION_MARKER" in check_set
                    and bool({"SHARED_PERIOD_AXIS", "SHARED_UNIT"} & check_set)
                )
                or "TABLE_EDGE_CONTINUITY" in check_set
            )
            bounded_inference = (
                base_checks <= check_set
                and check_set <= allowed_checks
                and len(check_set) == len(inference_checks)
                and metadata_or_edge
            )
        if not locally_accepted and not bounded_inference:
            raise NativeStatementRowsError(
                "selected statement page is neither locally accepted nor boundedly inferred"
            )
        if locally_accepted and (
            inferred_from_page is not None
            or inference_direction is not None
            or inference_checks != []
        ):
            raise NativeStatementRowsError(
                "locally accepted statement page carries unexpected inference evidence"
            )
        if page in seen_pages:
            raise NativeStatementRowsError("selected statement page contracts are not unique")
        seen_pages.add(page)
        selected.append(copy.deepcopy(raw))
    if not selected:
        raise NativeStatementRowsError("statement discovery selected no row-extraction pages")

    contracts_by_page = {int(contract["page"]): contract for contract in selected}
    for contract in selected:
        if contract["locally_accepted"] is True:
            continue
        page = int(contract["page"])
        inferred_from_page = int(contract["inferred_from_page"])
        source_contract = contracts_by_page.get(inferred_from_page)
        if (
            source_contract is None
            or source_contract.get("locally_accepted") is not True
            or source_contract.get("statement_type") != contract.get("statement_type")
            or source_contract.get("scope") != page_selection["main_scope"]
        ):
            raise NativeStatementRowsError(
                "bounded statement-page inference has no local same-statement source"
            )
        expected_direction = (
            "FORWARD_FROM_PREVIOUS"
            if inferred_from_page == page - 1
            else "BACKWARD_FROM_NEXT"
            if inferred_from_page == page + 1
            else None
        )
        if contract.get("inference_direction") != expected_direction:
            raise NativeStatementRowsError(
                "bounded statement-page inference is not adjacent/direction-consistent"
            )

    selected_main_pages = sorted(
        int(contract["page"])
        for contract in selected
        if contract["scope"] == page_selection["main_scope"]
    )
    declared_main_pages = block.get("mapping_eligible_pages")
    if declared_main_pages != selected_main_pages:
        raise NativeStatementRowsError("statement discovery mapping-eligible page list drifted")
    declared_by_type = block.get("mapping_eligible_pages_by_statement_type")
    expected_by_type = {
        statement_type: sorted(
            int(contract["page"])
            for contract in selected
            if contract["scope"] == page_selection["main_scope"]
            and contract["statement_type"] == statement_type
        )
        for statement_type in page_selection["main_statement_types"]
    }
    if declared_by_type != expected_by_type:
        raise NativeStatementRowsError("statement discovery typed page list drifted")
    off_balance_pages = sorted(
        int(contract["page"])
        for contract in selected
        if contract["scope"] == page_selection["off_balance_scope"]
    )
    if block.get("off_balance_excluded_pages") != off_balance_pages:
        raise NativeStatementRowsError("statement discovery off-balance page list drifted")
    recognized_by_type = block.get("recognized_pages_by_statement_type")
    expected_recognized_by_type = {
        statement_type: sorted(
            int(contract["page"])
            for contract in selected
            if contract["statement_type"] == statement_type
        )
        for statement_type in page_selection["main_statement_types"]
    }
    if recognized_by_type != expected_recognized_by_type:
        raise NativeStatementRowsError("statement discovery recognized-page list drifted")
    notes_boundary_page = block.get("notes_boundary_page")
    if (
        isinstance(notes_boundary_page, bool)
        or not isinstance(notes_boundary_page, int)
        or notes_boundary_page <= max(seen_pages)
        or notes_boundary_page in seen_pages
    ):
        raise NativeStatementRowsError(
            "statement discovery notes boundary overlaps statement pages"
        )
    page_quality = native_text.get("pages")
    if not isinstance(page_quality, list):
        raise NativeStatementRowsError("statement discovery native page ledger is invalid")
    quality_by_page = {item.get("page"): item for item in page_quality if isinstance(item, dict)}
    if any(
        quality_by_page.get(contract["page"], {}).get("text_quality") != "USABLE_TEXT_LAYER"
        for contract in selected
    ):
        raise NativeStatementRowsError("a selected statement page lacks usable native text")
    return sorted(selected, key=lambda item: int(item["page"]))


def _bbox(box: BoundingBox | None) -> dict[str, float] | None:
    if box is None:
        return None
    return {"x0": box.x0, "y0": box.y0, "x1": box.x1, "y1": box.y1}


def _date(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _decimal(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _source_status(observation: ObservationKind) -> str:
    return {
        ObservationKind.VALUE: "OBSERVED_VALUE",
        ObservationKind.ZERO: "OBSERVED_ZERO",
        ObservationKind.DASH: "DASH",
        ObservationKind.BLANK: "BLANK",
        ObservationKind.NOT_APPLICABLE: "NOT_APPLICABLE",
        ObservationKind.INVALID: "UNRESOLVED",
    }[observation]


def _matching_raw_runs(geometry: PageGeometry, boxes: tuple[BoundingBox, ...]) -> list[TextRun]:
    result: list[TextRun] = []
    for box in boxes:
        match = next((run for run in geometry.runs if run.bbox == box), None)
        if match is None:
            raise NativeStatementRowsError(
                f"page {geometry.page} row provenance does not resolve to a native text run"
            )
        result.append(match)
    return result


def _serialize_axis(axis: ColumnAxis) -> dict[str, Any]:
    return {
        "axis_id": axis.axis_id,
        "role": axis.role.value,
        "right_edge": axis.right_edge,
        "left_edge": axis.left_edge,
        "sample_count": axis.sample_count,
        "source": axis.source,
    }


def _serialize_header(binding: HeaderBinding) -> dict[str, Any]:
    return {
        "axis_id": binding.axis_id,
        "raw_header": binding.raw_header,
        "header_bbox": _bbox(binding.header_bbox),
        "unit": binding.unit,
        "unit_multiplier": binding.unit_multiplier,
        "unit_bbox": _bbox(binding.unit_bbox),
        "period_start": _date(binding.period_start),
        "period_end": _date(binding.period_end),
        "period_type": binding.period_type,
        "duration_months": binding.duration_months,
        "current_or_comparative": binding.current_or_comparative,
        "restated": binding.restated,
        "confidence": binding.confidence,
        "evidence": list(binding.evidence),
    }


def _serialize_cell(
    cell: GeometryCell,
    *,
    document_sha256: str,
    page: int,
    table_id: str,
    row_id: str,
) -> dict[str, Any]:
    return {
        "axis_id": cell.axis_id,
        "raw_text": cell.raw_text,
        "normalized_text": cell.parsed.normalized_text,
        "value": _decimal(cell.parsed.value),
        "observation": cell.parsed.observation.value,
        "source_status": _source_status(cell.parsed.observation),
        "sign_evidence": cell.parsed.sign_evidence,
        "parse_reason": cell.parsed.reason,
        "bbox": _bbox(cell.bbox),
        "run_id": cell.run_id,
        "axis_distance": cell.axis_distance,
        "provenance": {
            "document_sha256": document_sha256,
            "page": page,
            "table_id": table_id,
            "row_id": row_id,
            "column_id": cell.axis_id,
            "value_bbox": _bbox(cell.bbox),
        },
    }


def _serialize_row(
    row: StatementRow,
    *,
    geometry: PageGeometry,
    document_sha256: str,
    table_id: str,
    within_financial_table_span: bool,
) -> dict[str, Any]:
    raw_label_runs = _matching_raw_runs(geometry, row.label_boxes)
    raw_note_runs = _matching_raw_runs(
        geometry, (row.note_bbox,) if row.note_bbox is not None else ()
    )
    return {
        "row_id": row.row_id,
        "page": row.page,
        "row_type": row.row_type.value,
        "source_status": "OBSERVED_ROW",
        "raw_label": " ".join(run.raw_text for run in raw_label_runs),
        "normalized_label": row.label,
        "label_bboxes": [_bbox(box) for box in row.label_boxes],
        "raw_note_reference": " ".join(run.raw_text for run in raw_note_runs) or None,
        "note_reference": row.note_reference,
        "note_bbox": _bbox(row.note_bbox),
        "cells": [
            _serialize_cell(
                cell,
                document_sha256=document_sha256,
                page=row.page,
                table_id=table_id,
                row_id=row.row_id,
            )
            for cell in row.cells
        ],
        "y0": row.y0,
        "y1": row.y1,
        "indentation": row.indentation,
        "within_financial_table_span": within_financial_table_span,
        "warnings": list(row.warnings),
        "provenance": {
            "document_sha256": document_sha256,
            "page": row.page,
            "table_id": table_id,
            "row_id": row.row_id,
            "label_bboxes": [_bbox(box) for box in row.label_boxes],
            "note_bbox": _bbox(row.note_bbox),
        },
    }


def _canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def build_registered_native_statement_rows(
    project_root: Path,
    source_pdf: Path,
    discovery_path: Path,
    discovery_sha256: str,
    policy_path: Path,
    run_id: str,
    git_state: dict[str, Any],
) -> dict[str, Any]:
    project_root = project_root.resolve()
    source_pdf = source_pdf.resolve()
    discovery_path = discovery_path.resolve()
    policy_path = policy_path.resolve()
    if not _SAFE_RUN_ID.fullmatch(run_id):
        raise NativeStatementRowsError("native statement rows run_id is invalid")
    if _SHA256.fullmatch(discovery_sha256) is None:
        raise NativeStatementRowsError("trusted statement discovery SHA-256 is invalid")
    code = _validate_git_state(git_state)
    initial_policy_identity = _identity_record(project_root, policy_path, "THIS_POLICY")
    policy = load_native_statement_rows_policy(policy_path, project_root)
    quality_path = _resolve_under_root(
        project_root,
        policy["native_text_quality_config"]["path"],
        "native-text quality config",
    )
    geometry_path = _resolve_under_root(
        project_root, policy["geometry_config"]["path"], "geometry config"
    )
    source_registry_path = _resolve_under_root(
        project_root, policy["source_registry"], "source registry"
    )
    role_registry_path = _resolve_under_root(
        project_root, policy["dataset_role_registry"], "dataset-role registry"
    )
    discovery_relative = _relative_path(
        project_root, discovery_path, "accepted statement discovery"
    )
    runtime_input_paths = [
        (source_pdf, "SOURCE_PDF"),
        (source_registry_path, "SOURCE_REGISTRY"),
        (role_registry_path, "DATASET_ROLE_REGISTRY"),
        (discovery_path, "ACCEPTED_STATEMENT_DISCOVERY"),
        (policy_path, "THIS_POLICY"),
        (quality_path, "NATIVE_TEXT_QUALITY_CONFIG"),
        (geometry_path, "GEOMETRY_CONFIG"),
    ]
    runtime_inputs = _runtime_input_ledger(project_root, runtime_input_paths)
    implementation = _implementation_ledger(project_root)
    policy_identity = next(record for record in runtime_inputs if record["kind"] == "THIS_POLICY")
    if policy_identity != initial_policy_identity:
        raise NativeStatementRowsError("native statement rows policy changed while it was loaded")
    expected_config_hashes = {
        "NATIVE_TEXT_QUALITY_CONFIG": policy["native_text_quality_config"]["sha256"],
        "GEOMETRY_CONFIG": policy["geometry_config"]["sha256"],
    }
    if any(
        record["sha256"] != expected_config_hashes[record["kind"]]
        for record in runtime_inputs
        if record["kind"] in expected_config_hashes
    ):
        raise NativeStatementRowsError("a pinned native statement rows config changed before use")
    allowed_kinds = set(policy["role_isolation"]["runtime_input_allowlist"])
    if any(record["kind"] not in allowed_kinds for record in runtime_inputs):
        raise NativeStatementRowsError("runtime input ledger contains a forbidden input kind")
    _validate_path_isolation([record["path"] for record in runtime_inputs], policy)

    source_record, role_record, source_sha256, source_relative = _registered_source(
        project_root, source_pdf, policy
    )
    source_identity = next(record for record in runtime_inputs if record["kind"] == "SOURCE_PDF")
    if (
        source_identity["sha256"] != source_sha256
        or source_identity["size_bytes"] != source_record["size_bytes"]
    ):
        raise NativeStatementRowsError("source PDF changed during registry validation")
    role = role_record["dataset_role"]
    allowed_discovery_directory = (project_root / _ROLE_DIRECTORIES[role]).resolve()
    try:
        discovery_path.relative_to(allowed_discovery_directory)
    except ValueError as exc:
        raise NativeStatementRowsError(
            f"statement discovery for {role} must stay under {_ROLE_DIRECTORIES[role]}"
        ) from exc

    discovery_bytes, discovery = _load_discovery_bytes(discovery_path)
    discovery_identity = next(
        record for record in runtime_inputs if record["kind"] == "ACCEPTED_STATEMENT_DISCOVERY"
    )
    if (
        discovery_identity["sha256"] != discovery_sha256
        or sha256_bytes(discovery_bytes) != discovery_sha256
    ):
        raise NativeStatementRowsError("statement discovery does not match its trusted SHA-256")
    contracts = _validate_discovery_contract(
        discovery,
        policy=policy,
        source_record=source_record,
        role_record=role_record,
        source_relative=source_relative,
        source_sha256=source_sha256,
    )

    quality_config = load_native_text_quality_v2_config(quality_path)
    geometry_config = load_geometry_config(geometry_path)
    selected_pages = {int(contract["page"]) for contract in contracts}
    extracted_pages = extract_pdf_text_v2(
        source_pdf,
        config=quality_config,
        page_numbers=selected_pages,
    )
    if {page.page for page in extracted_pages} != selected_pages or len(extracted_pages) != len(
        selected_pages
    ):
        raise NativeStatementRowsError("native v2 extraction did not return every selected page")
    extracted_by_page = {page.page: page for page in extracted_pages}

    page_records: list[dict[str, Any]] = []
    source_status_counts: Counter[str] = Counter()
    statement_page_counts: Counter[str] = Counter()
    row_count = 0
    cell_count = 0
    section_header_count = 0
    unlabeled_numeric_row_count = 0
    for contract in contracts:
        page_number = int(contract["page"])
        page = extracted_by_page[page_number]
        if page.text_quality != "USABLE_TEXT_LAYER":
            raise NativeStatementRowsError(
                f"selected page {page_number} is not usable native text; OCR is required"
            )
        try:
            geometry = analyze_page_geometry(page, geometry_config)
            reconstructed = reconstruct_statement_rows(
                geometry,
                geometry_config,
                table_id=(
                    f"native-{source_sha256[:16]}-"
                    f"{str(contract['statement_type']).casefold()}-"
                    f"{str(contract['scope']).casefold().replace('_', '-')}-page-{page_number:04d}"
                ),
            )
            table_rows = financial_table_span(reconstructed)
            bindings = bind_value_headers(geometry, geometry_config)
        except ValueError as exc:
            raise NativeStatementRowsError(
                f"native row reconstruction failed on selected page {page_number}: {exc}"
            ) from exc
        if not table_rows:
            raise NativeStatementRowsError(
                f"selected statement page {page_number} has no defensible financial table span"
            )
        table_id = table_rows[0].row_id.rsplit(":row-", 1)[0]
        table_row_ids = {row.row_id for row in table_rows}
        serialized_rows = [
            _serialize_row(
                row,
                geometry=geometry,
                document_sha256=source_sha256,
                table_id=table_id,
                within_financial_table_span=True,
            )
            for row in table_rows
        ]
        outside_rows = [
            _serialize_row(
                row,
                geometry=geometry,
                document_sha256=source_sha256,
                table_id=table_id,
                within_financial_table_span=False,
            )
            for row in reconstructed
            if row.row_id not in table_row_ids
        ]
        for row in serialized_rows:
            row_count += 1
            if row["row_type"] == "SECTION_HEADER":
                section_header_count += 1
            if not row["normalized_label"] and row["cells"]:
                unlabeled_numeric_row_count += 1
            for cell in row["cells"]:
                cell_count += 1
                source_status_counts[cell["source_status"]] += 1
        statement_page_counts[str(contract["statement_type"])] += 1
        native_word_records = [
            json.dumps(
                {
                    "raw_text": word.raw_text,
                    "bbox": _bbox(word.bbox_points),
                    "block_number": word.block_number,
                    "line_number": word.line_number,
                    "word_number": word.word_number,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            for word in page.words
        ]
        page_records.append(
            {
                "page": page_number,
                "statement_type": contract["statement_type"],
                "scope": contract["scope"],
                "discovery_contract": contract,
                "text_quality": page.text_quality,
                "corruption_markers": list(page.corruption_markers),
                "width_points": page.width_points,
                "height_points": page.height_points,
                "rotation": page.rotation,
                "native_word_count": len(page.words),
                "native_words_sha256": stable_records_hash(native_word_records),
                "geometry": {
                    "authority": _NATIVE_GEOMETRY_AUTHORITY,
                    "data_start_y": geometry.data_start_y,
                    "data_end_y": geometry.data_end_y,
                    "label_right_boundary": geometry.label_right_boundary,
                    "edge_tolerance": geometry.edge_tolerance,
                    "axes": [_serialize_axis(axis) for axis in geometry.axes],
                    "unit_run_ids": list(geometry.unit_run_ids),
                    "warnings": list(geometry.warnings),
                },
                "headers": [_serialize_header(binding) for binding in bindings],
                "rows": serialized_rows,
                "outside_financial_table_span_rows": outside_rows,
                "reconstructed_row_count": len(reconstructed),
                "financial_table_span_row_count": len(table_rows),
                "outside_financial_table_span_row_count": len(outside_rows),
            }
        )

    final_runtime_inputs = _runtime_input_ledger(project_root, runtime_input_paths)
    if final_runtime_inputs != runtime_inputs:
        raise NativeStatementRowsError("runtime input bytes changed during row extraction")
    final_implementation = _implementation_ledger(project_root)
    if final_implementation != implementation:
        raise NativeStatementRowsError("implementation bytes changed during row extraction")

    payload: dict[str, Any] = {
        "format_version": _OUTPUT_FORMAT,
        "policy": policy["policy"],
        "claim_boundary": policy["claim_boundary"],
        "status": policy["output"]["status"],
        "run_id": run_id,
        "source": {
            "document_id": source_record["document_id"],
            "relative_path": source_relative,
            "sha256": source_sha256,
            "size_bytes": source_record["size_bytes"],
            "bank": source_record.get("bank"),
            "year": source_record.get("year"),
            "dataset_role": role,
            "registry_state": source_record["state"],
            "hash_verified_stable": source_record["hash_verified_stable"],
            "immutable_role_assignment": role_record["immutable"],
        },
        "statement_discovery": {
            "path": discovery_relative,
            "sha256": discovery_identity["sha256"],
            "size_bytes": discovery_identity["size_bytes"],
            "format_version": discovery["format_version"],
            "status": discovery["status"],
            "run_id": discovery.get("run_id"),
            "producer_git_commit": discovery["code"]["commit"],
        },
        "code": {**code, "implementation": implementation},
        "authority": {
            "geometry": _NATIVE_GEOMETRY_AUTHORITY,
            "evidence_source": _NATIVE_GEOMETRY_EVIDENCE,
            "row_reconstruction": policy["row_reconstruction"]["row_assembler"],
            "financial_table_span": policy["row_reconstruction"]["table_span"],
            "header_binding": policy["row_reconstruction"]["header_binding"],
            "semantic_reader": None,
            "schema_mapper": None,
        },
        "isolation": {
            "prior_answer_artifacts_loaded": False,
            "historical_values_loaded": False,
            "role_a_outputs_loaded": False,
            "schema_inputs_loaded": False,
            "template_inputs_loaded": False,
            "bank_identity_used_for_row_reconstruction": False,
            "filename_identity_used_for_row_reconstruction": False,
            "page_number_rules_used_for_row_reconstruction": False,
            "runtime_input_policy": "EXACT_DECLARED_PROJECT_INPUT_LEDGER",
        },
        "inputs": {
            "runtime_read_ledger": runtime_inputs,
            "runtime_read_ledger_sha256": stable_records_hash(
                json.dumps(record, ensure_ascii=False, sort_keys=True) for record in runtime_inputs
            ),
        },
        "selection": {
            "policy": "ACCEPTED_DISCOVERY_CONTRACTS_ONLY",
            "selected_pages": sorted(selected_pages),
            "selected_page_count": len(selected_pages),
            "statement_page_counts": dict(sorted(statement_page_counts.items())),
            "notes_pages_selected": 0,
        },
        "summary": {
            "page_count": len(page_records),
            "pages_sha256": stable_records_hash(
                json.dumps(page, ensure_ascii=False, sort_keys=True) for page in page_records
            ),
            "financial_table_span_row_count": row_count,
            "cell_count": cell_count,
            "section_header_count": section_header_count,
            "unlabeled_numeric_row_count": unlabeled_numeric_row_count,
            "cell_source_status_counts": dict(sorted(source_status_counts.items())),
            "schema_items_created": 0,
            "schema_items_mapped": 0,
        },
        "pages": page_records,
    }
    return json.loads(_canonical_json_bytes(payload))


def _require_exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise NativeStatementRowsError(f"{label} fields are invalid")
    return value


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise NativeStatementRowsError(f"{label} must be numeric")
    converted = float(value)
    if not math.isfinite(converted):
        raise NativeStatementRowsError(f"{label} must be finite")
    return converted


def _validate_serialized_bbox(
    value: Any,
    label: str,
    *,
    nullable: bool = False,
    width_points: float | None = None,
    height_points: float | None = None,
) -> tuple[float, float, float, float] | None:
    if value is None and nullable:
        return None
    if not isinstance(value, dict) or set(value) != {"x0", "y0", "x1", "y1"}:
        raise NativeStatementRowsError(f"{label} bbox is invalid")
    coordinates = tuple(
        _finite_number(value[key], f"{label} bbox coordinate") for key in ("x0", "y0", "x1", "y1")
    )
    if coordinates[2] < coordinates[0] or coordinates[3] < coordinates[1]:
        raise NativeStatementRowsError(f"{label} bbox is inverted")
    if (
        coordinates[0] < 0
        or coordinates[1] < 0
        or (width_points is not None and coordinates[2] > width_points)
        or (height_points is not None and coordinates[3] > height_points)
    ):
        raise NativeStatementRowsError(f"{label} bbox escapes its PDF page")
    return coordinates


def _validate_serialized_header(
    header: Any,
    *,
    value_axis_ids: set[str],
    width_points: float,
    height_points: float,
) -> str:
    header = _require_exact_keys(
        header,
        {
            "axis_id",
            "raw_header",
            "header_bbox",
            "unit",
            "unit_multiplier",
            "unit_bbox",
            "period_start",
            "period_end",
            "period_type",
            "duration_months",
            "current_or_comparative",
            "restated",
            "confidence",
            "evidence",
        },
        "native statement header",
    )
    axis_id = header["axis_id"]
    if axis_id not in value_axis_ids or not isinstance(header["raw_header"], str):
        raise NativeStatementRowsError("native statement header axis/text is invalid")
    _validate_serialized_bbox(
        header["header_bbox"],
        "header",
        nullable=True,
        width_points=width_points,
        height_points=height_points,
    )
    _validate_serialized_bbox(
        header["unit_bbox"],
        "header unit",
        nullable=True,
        width_points=width_points,
        height_points=height_points,
    )
    unit = header["unit"]
    multiplier = header["unit_multiplier"]
    if unit is not None and not isinstance(unit, str):
        raise NativeStatementRowsError("native statement header unit is invalid")
    if multiplier is not None and (
        isinstance(multiplier, bool) or not isinstance(multiplier, int) or multiplier < 1
    ):
        raise NativeStatementRowsError("native statement header unit multiplier is invalid")
    if (unit is None) != (multiplier is None):
        raise NativeStatementRowsError("native statement header unit fields are inconsistent")
    parsed_dates: dict[str, date | None] = {}
    for key in ("period_start", "period_end"):
        raw = header[key]
        if raw is None:
            parsed_dates[key] = None
        elif isinstance(raw, str):
            try:
                parsed_dates[key] = date.fromisoformat(raw)
            except ValueError as exc:
                raise NativeStatementRowsError(
                    "native statement header period date is invalid"
                ) from exc
        else:
            raise NativeStatementRowsError("native statement header period date is invalid")
    if (
        parsed_dates["period_start"] is not None
        and parsed_dates["period_end"] is not None
        and parsed_dates["period_start"] > parsed_dates["period_end"]
    ):
        raise NativeStatementRowsError("native statement header period range is inverted")
    if header["period_type"] not in {None, "SNAPSHOT", "DURATION", "YTD"}:
        raise NativeStatementRowsError("native statement header period type is invalid")
    duration = header["duration_months"]
    if duration is not None and (
        isinstance(duration, bool) or not isinstance(duration, int) or not 1 <= duration <= 120
    ):
        raise NativeStatementRowsError("native statement header duration is invalid")
    if header["current_or_comparative"] not in {None, "CURRENT", "COMPARATIVE"}:
        raise NativeStatementRowsError("native statement header period role is invalid")
    if type(header["restated"]) is not bool:
        raise NativeStatementRowsError("native statement header restated flag is invalid")
    confidence = _finite_number(header["confidence"], "native statement header confidence")
    if not 0 <= confidence <= 1:
        raise NativeStatementRowsError("native statement header confidence is invalid")
    evidence = header["evidence"]
    if not isinstance(evidence, list) or any(
        not isinstance(item, str) or not item for item in evidence
    ):
        raise NativeStatementRowsError("native statement header evidence is invalid")
    return axis_id


def _validate_serialized_cell(
    cell: Any,
    *,
    source_sha256: str,
    page: int,
    row_id: str,
    table_id: str,
    value_axis_ids: set[str],
    width_points: float,
    height_points: float,
) -> str:
    cell = _require_exact_keys(
        cell,
        {
            "axis_id",
            "raw_text",
            "normalized_text",
            "value",
            "observation",
            "source_status",
            "sign_evidence",
            "parse_reason",
            "bbox",
            "run_id",
            "axis_distance",
            "provenance",
        },
        "native statement cell",
    )
    if cell["axis_id"] not in value_axis_ids:
        raise NativeStatementRowsError("native statement cell value-axis identity is invalid")
    observation_raw = cell.get("observation")
    try:
        observation = ObservationKind(observation_raw)
    except (TypeError, ValueError) as exc:
        raise NativeStatementRowsError("native statement cell observation is invalid") from exc
    if cell.get("source_status") != _source_status(observation):
        raise NativeStatementRowsError("native statement cell source status is inconsistent")
    if not isinstance(cell.get("raw_text"), str) or not isinstance(
        cell.get("normalized_text"), str
    ):
        raise NativeStatementRowsError("native statement cell raw/normalized text is invalid")
    value = cell["value"]
    parsed_value: Decimal | None = None
    if value is not None:
        if not isinstance(value, str):
            raise NativeStatementRowsError("native statement Decimal must be serialized as text")
        try:
            parsed_value = Decimal(value)
        except Exception as exc:
            raise NativeStatementRowsError("native statement Decimal is invalid") from exc
    if observation is ObservationKind.VALUE and (parsed_value is None or parsed_value == 0):
        raise NativeStatementRowsError("OBSERVED_VALUE cell has an invalid Decimal")
    if observation is ObservationKind.ZERO and parsed_value != 0:
        raise NativeStatementRowsError("OBSERVED_ZERO cell has an invalid Decimal")
    if observation not in {ObservationKind.VALUE, ObservationKind.ZERO} and value is not None:
        raise NativeStatementRowsError("non-value cell unexpectedly carries a Decimal")
    parsed_from_raw = parse_financial_number(cell["raw_text"])
    expected_parse = {
        "normalized_text": parsed_from_raw.normalized_text,
        "value": _decimal(parsed_from_raw.value),
        "observation": parsed_from_raw.observation.value,
        "source_status": _source_status(parsed_from_raw.observation),
        "sign_evidence": parsed_from_raw.sign_evidence,
        "parse_reason": parsed_from_raw.reason,
    }
    if any(cell[key] != expected for key, expected in expected_parse.items()):
        raise NativeStatementRowsError("native statement cell parse fields are inconsistent")
    cell_bbox = _validate_serialized_bbox(
        cell["bbox"],
        "cell",
        width_points=width_points,
        height_points=height_points,
    )
    if not isinstance(cell["run_id"], str) or not cell["run_id"]:
        raise NativeStatementRowsError("native statement cell run ID is invalid")
    if _finite_number(cell["axis_distance"], "native statement cell axis distance") < 0:
        raise NativeStatementRowsError("native statement cell axis distance is invalid")
    provenance = _require_exact_keys(
        cell["provenance"],
        {
            "document_sha256",
            "page",
            "table_id",
            "row_id",
            "column_id",
            "value_bbox",
        },
        "native statement cell provenance",
    )
    if (
        provenance.get("document_sha256") != source_sha256
        or provenance.get("page") != page
        or provenance.get("table_id") != table_id
        or provenance.get("row_id") != row_id
        or provenance.get("column_id") != cell.get("axis_id")
    ):
        raise NativeStatementRowsError("native statement cell provenance is invalid")
    provenance_bbox = _validate_serialized_bbox(
        provenance["value_bbox"],
        "cell provenance",
        width_points=width_points,
        height_points=height_points,
    )
    if provenance_bbox != cell_bbox:
        raise NativeStatementRowsError("native statement cell bbox provenance is inconsistent")
    return cell["source_status"]


def _validate_serialized_row(
    row: Any,
    *,
    source_sha256: str,
    page: int,
    within_span: bool,
    table_id: str,
    value_axis_ids: set[str],
    width_points: float,
    height_points: float,
) -> tuple[int, int, int, Counter[str]]:
    row = _require_exact_keys(
        row,
        {
            "row_id",
            "page",
            "row_type",
            "source_status",
            "raw_label",
            "normalized_label",
            "label_bboxes",
            "raw_note_reference",
            "note_reference",
            "note_bbox",
            "cells",
            "y0",
            "y1",
            "indentation",
            "within_financial_table_span",
            "warnings",
            "provenance",
        },
        "native statement row",
    )
    if row.get("page") != page:
        raise NativeStatementRowsError("native statement row page identity is invalid")
    try:
        RowType(row["row_type"])
    except (TypeError, ValueError) as exc:
        raise NativeStatementRowsError("native statement row type is invalid") from exc
    if row.get("source_status") != "OBSERVED_ROW":
        raise NativeStatementRowsError("native statement row source status is invalid")
    if row.get("within_financial_table_span") is not within_span:
        raise NativeStatementRowsError("native statement row span status is invalid")
    if not isinstance(row.get("raw_label"), str) or not isinstance(
        row.get("normalized_label"), str
    ):
        raise NativeStatementRowsError("native statement row label is invalid")
    if row["normalized_label"] != normalize_text(row["raw_label"]):
        raise NativeStatementRowsError("native statement row raw/normalized label is inconsistent")
    label_boxes = row.get("label_bboxes")
    if not isinstance(label_boxes, list):
        raise NativeStatementRowsError("native statement row label boxes are invalid")
    for box in label_boxes:
        _validate_serialized_bbox(
            box,
            "row label",
            width_points=width_points,
            height_points=height_points,
        )
    note_bbox = _validate_serialized_bbox(
        row.get("note_bbox"),
        "row note",
        nullable=True,
        width_points=width_points,
        height_points=height_points,
    )
    raw_note = row["raw_note_reference"]
    normalized_note = row["note_reference"]
    if note_bbox is None:
        if raw_note is not None or normalized_note is not None:
            raise NativeStatementRowsError("native statement row note provenance is inconsistent")
    elif (
        not isinstance(raw_note, str) or not raw_note or normalized_note != normalize_text(raw_note)
    ):
        raise NativeStatementRowsError("native statement row note text is inconsistent")
    row_id = row.get("row_id")
    if not isinstance(row_id, str) or not row_id:
        raise NativeStatementRowsError("native statement row ID is invalid")
    provenance = _require_exact_keys(
        row["provenance"],
        {
            "document_sha256",
            "page",
            "table_id",
            "row_id",
            "label_bboxes",
            "note_bbox",
        },
        "native statement row provenance",
    )
    if (
        provenance.get("document_sha256") != source_sha256
        or provenance.get("page") != page
        or provenance.get("table_id") != table_id
        or provenance.get("row_id") != row_id
        or provenance.get("label_bboxes") != label_boxes
        or provenance.get("note_bbox") != row.get("note_bbox")
    ):
        raise NativeStatementRowsError("native statement row provenance is invalid")
    y0 = _finite_number(row["y0"], "native statement row y0")
    y1 = _finite_number(row["y1"], "native statement row y1")
    indentation = _finite_number(row["indentation"], "native statement row indentation")
    if not 0 <= y0 <= y1 <= height_points or not 0 <= indentation <= width_points:
        raise NativeStatementRowsError("native statement row geometry is invalid")
    warnings = row["warnings"]
    if not isinstance(warnings, list) or any(not isinstance(item, str) for item in warnings):
        raise NativeStatementRowsError("native statement row warnings are invalid")
    cells = row.get("cells")
    if not isinstance(cells, list):
        raise NativeStatementRowsError("native statement row cells are invalid")
    statuses: Counter[str] = Counter(
        _validate_serialized_cell(
            cell,
            source_sha256=source_sha256,
            page=page,
            row_id=row_id,
            table_id=table_id,
            value_axis_ids=value_axis_ids,
            width_points=width_points,
            height_points=height_points,
        )
        for cell in cells
    )
    section_header = int(row.get("row_type") == "SECTION_HEADER")
    unlabeled_numeric = int(not row["normalized_label"] and bool(cells))
    return (
        1,
        len(cells),
        section_header,
        statuses + Counter({"__UNLABELED_NUMERIC_ROWS__": unlabeled_numeric}),
    )


def load_registered_native_statement_rows(
    path: Path,
    *,
    project_root: Path,
    expected_sha256: str,
    policy_path: Path | None = None,
) -> dict[str, Any]:
    """Load a deterministic native-row artifact through its strict source contract."""

    project_root = project_root.resolve()
    path = path.resolve()
    policy_path = (policy_path or project_root / POLICY_RELATIVE_PATH).resolve()
    policy = load_native_statement_rows_policy(policy_path, project_root)
    if _SHA256.fullmatch(expected_sha256) is None:
        raise NativeStatementRowsError("trusted native statement rows SHA-256 is invalid")
    relative = _relative_path(project_root, path, "native statement rows artifact")
    _validate_path_isolation([relative], policy)
    try:
        encoded = path.read_bytes()
        payload = json.loads(encoded)
    except (OSError, json.JSONDecodeError) as exc:
        raise NativeStatementRowsError(
            f"cannot load native statement rows artifact: {path}"
        ) from exc
    if sha256_bytes(encoded) != expected_sha256:
        raise NativeStatementRowsError(
            "native statement rows artifact does not match its trusted SHA-256"
        )
    if not isinstance(payload, dict) or encoded != _canonical_json_bytes(payload):
        raise NativeStatementRowsError("native statement rows artifact is not canonical JSON")
    _require_exact_keys(
        payload,
        {
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
            "selection",
            "summary",
            "pages",
        },
        "native statement rows artifact",
    )
    if any(
        payload.get(key) != value
        for key, value in {
            "format_version": _OUTPUT_FORMAT,
            "policy": _POLICY_NAME,
            "claim_boundary": _CLAIM_BOUNDARY,
            "status": _OUTPUT_STATUS,
        }.items()
    ):
        raise NativeStatementRowsError("native statement rows artifact identity is invalid")
    run_id = payload.get("run_id")
    if not isinstance(run_id, str) or _SAFE_RUN_ID.fullmatch(run_id) is None:
        raise NativeStatementRowsError("native statement rows artifact run_id is invalid")
    code = payload.get("code")
    if (
        not isinstance(code, dict)
        or set(code) != {"commit", "dirty", "implementation"}
        or code.get("dirty") is not False
        or not isinstance(code.get("commit"), str)
        or not isinstance(code.get("implementation"), list)
    ):
        raise NativeStatementRowsError("native statement rows producer code identity is invalid")
    committed_implementation = _implementation_ledger_at_commit(project_root, code["commit"])
    if code["implementation"] != committed_implementation:
        raise NativeStatementRowsError(
            "native statement rows implementation does not match its producer commit"
        )
    source = _require_exact_keys(
        payload.get("source"),
        {
            "document_id",
            "relative_path",
            "sha256",
            "size_bytes",
            "bank",
            "year",
            "dataset_role",
            "registry_state",
            "hash_verified_stable",
            "immutable_role_assignment",
        },
        "native statement rows source identity",
    )
    role = source.get("dataset_role")
    if role not in _ALLOWED_ROLES:
        raise NativeStatementRowsError("native statement rows dataset role is invalid")
    allowed_directory = (project_root / _ROLE_DIRECTORIES[role]).resolve()
    try:
        path.relative_to(allowed_directory)
    except ValueError as exc:
        raise NativeStatementRowsError(
            f"native statement rows for {role} must stay under {_ROLE_DIRECTORIES[role]}"
        ) from exc
    source_sha256 = source.get("sha256")
    source_relative = source.get("relative_path")
    if (
        not isinstance(source_sha256, str)
        or _SHA256.fullmatch(source_sha256) is None
        or source.get("document_id") != f"sha256:{source_sha256}"
        or not isinstance(source_relative, str)
        or isinstance(source.get("size_bytes"), bool)
        or not isinstance(source.get("size_bytes"), int)
        or source["size_bytes"] < 1
        or source.get("registry_state") != "REGISTERED"
        or source.get("hash_verified_stable") is not True
        or source.get("immutable_role_assignment") is not True
    ):
        raise NativeStatementRowsError("native statement rows source identity is invalid")
    source_path = _resolve_under_root(project_root, source_relative, "source PDF")
    if (
        not source_path.is_file()
        or source_path.stat().st_size != source["size_bytes"]
        or sha256_file(source_path) != source_sha256
    ):
        raise NativeStatementRowsError("native statement rows source PDF is absent or drifted")
    source_record, role_record, registered_sha256, registered_relative = _registered_source(
        project_root, source_path, policy
    )
    expected_source = {
        "document_id": source_record["document_id"],
        "relative_path": registered_relative,
        "sha256": registered_sha256,
        "size_bytes": source_record["size_bytes"],
        "bank": source_record.get("bank"),
        "year": source_record.get("year"),
        "dataset_role": role_record["dataset_role"],
        "registry_state": source_record["state"],
        "hash_verified_stable": source_record["hash_verified_stable"],
        "immutable_role_assignment": role_record["immutable"],
    }
    if source != expected_source:
        raise NativeStatementRowsError("native statement rows source registry binding is invalid")
    discovery = _require_exact_keys(
        payload.get("statement_discovery"),
        {
            "path",
            "sha256",
            "size_bytes",
            "format_version",
            "status",
            "run_id",
            "producer_git_commit",
        },
        "native statement rows discovery provenance",
    )
    if not isinstance(discovery.get("path"), str):
        raise NativeStatementRowsError("native statement rows discovery path is invalid")
    discovery_path = _resolve_under_root(
        project_root, discovery["path"], "statement discovery provenance"
    )
    try:
        discovery_path.relative_to(allowed_directory)
    except ValueError as exc:
        raise NativeStatementRowsError(
            f"statement discovery for {role} must stay under {_ROLE_DIRECTORIES[role]}"
        ) from exc
    discovery_bytes, discovery_payload = _load_discovery_bytes(discovery_path)
    if (
        _SHA256.fullmatch(str(discovery.get("sha256", ""))) is None
        or discovery.get("size_bytes") != len(discovery_bytes)
        or sha256_bytes(discovery_bytes) != discovery.get("sha256")
        or discovery.get("format_version")
        != policy["accepted_statement_discovery"]["format_version"]
        or discovery.get("status") != policy["accepted_statement_discovery"]["status"]
    ):
        raise NativeStatementRowsError("native statement rows discovery provenance drifted")
    expected_discovery = {
        "path": discovery["path"],
        "sha256": sha256_bytes(discovery_bytes),
        "size_bytes": len(discovery_bytes),
        "format_version": discovery_payload.get("format_version"),
        "status": discovery_payload.get("status"),
        "run_id": discovery_payload.get("run_id"),
        "producer_git_commit": (
            discovery_payload.get("code", {}).get("commit")
            if isinstance(discovery_payload.get("code"), dict)
            else None
        ),
    }
    if discovery != expected_discovery:
        raise NativeStatementRowsError("native statement rows discovery envelope is inconsistent")
    selected_contracts = _validate_discovery_contract(
        discovery_payload,
        policy=policy,
        source_record=source_record,
        role_record=role_record,
        source_relative=source_relative,
        source_sha256=source_sha256,
    )
    expected_authority = {
        "geometry": _NATIVE_GEOMETRY_AUTHORITY,
        "evidence_source": _NATIVE_GEOMETRY_EVIDENCE,
        "row_reconstruction": policy["row_reconstruction"]["row_assembler"],
        "financial_table_span": policy["row_reconstruction"]["table_span"],
        "header_binding": policy["row_reconstruction"]["header_binding"],
        "semantic_reader": None,
        "schema_mapper": None,
    }
    if payload.get("authority") != expected_authority:
        raise NativeStatementRowsError("native statement rows authority contract is invalid")
    expected_isolation = {
        "prior_answer_artifacts_loaded": False,
        "historical_values_loaded": False,
        "role_a_outputs_loaded": False,
        "schema_inputs_loaded": False,
        "template_inputs_loaded": False,
        "bank_identity_used_for_row_reconstruction": False,
        "filename_identity_used_for_row_reconstruction": False,
        "page_number_rules_used_for_row_reconstruction": False,
        "runtime_input_policy": "EXACT_DECLARED_PROJECT_INPUT_LEDGER",
    }
    if payload.get("isolation") != expected_isolation:
        raise NativeStatementRowsError("native statement rows isolation contract is invalid")
    inputs = _require_exact_keys(
        payload.get("inputs"),
        {"runtime_read_ledger", "runtime_read_ledger_sha256"},
        "native statement rows input ledger",
    )
    runtime_ledger = inputs["runtime_read_ledger"]
    if not isinstance(runtime_ledger, list) or len(runtime_ledger) != 7:
        raise NativeStatementRowsError("native statement rows runtime ledger is incomplete")
    for record in runtime_ledger:
        _require_exact_keys(
            record,
            {"kind", "path", "sha256", "size_bytes"},
            "native statement rows runtime input",
        )
        if (
            not isinstance(record["kind"], str)
            or not isinstance(record["path"], str)
            or _SHA256.fullmatch(str(record["sha256"])) is None
            or isinstance(record["size_bytes"], bool)
            or not isinstance(record["size_bytes"], int)
            or record["size_bytes"] < 0
        ):
            raise NativeStatementRowsError(
                "native statement rows runtime input identity is invalid"
            )
        _resolve_under_root(project_root, record["path"], "runtime input ledger path")
    if runtime_ledger != sorted(runtime_ledger, key=lambda item: (item["kind"], item["path"])):
        raise NativeStatementRowsError("native statement rows runtime ledger order is invalid")
    if inputs["runtime_read_ledger_sha256"] != stable_records_hash(
        json.dumps(record, ensure_ascii=False, sort_keys=True) for record in runtime_ledger
    ):
        raise NativeStatementRowsError("native statement rows runtime ledger hash is invalid")
    expected_kinds = set(policy["role_isolation"]["runtime_input_allowlist"])
    by_kind: dict[str, dict[str, Any]] = {}
    for record in runtime_ledger:
        if record["kind"] in by_kind:
            raise NativeStatementRowsError("native statement rows runtime input kind is duplicated")
        by_kind[record["kind"]] = record
    if set(by_kind) != expected_kinds:
        raise NativeStatementRowsError("native statement rows runtime input kinds are invalid")
    _validate_path_isolation([record["path"] for record in runtime_ledger], policy)
    expected_paths = {
        "SOURCE_PDF": source_relative,
        "SOURCE_REGISTRY": policy["source_registry"],
        "DATASET_ROLE_REGISTRY": policy["dataset_role_registry"],
        "ACCEPTED_STATEMENT_DISCOVERY": discovery["path"],
        "THIS_POLICY": POLICY_RELATIVE_PATH.as_posix(),
        "NATIVE_TEXT_QUALITY_CONFIG": policy["native_text_quality_config"]["path"],
        "GEOMETRY_CONFIG": policy["geometry_config"]["path"],
    }
    if any(by_kind[kind]["path"] != value for kind, value in expected_paths.items()):
        raise NativeStatementRowsError("native statement rows runtime input paths are invalid")
    if (
        by_kind["SOURCE_PDF"]["sha256"] != source_sha256
        or by_kind["SOURCE_PDF"]["size_bytes"] != source["size_bytes"]
        or by_kind["ACCEPTED_STATEMENT_DISCOVERY"]["sha256"] != discovery["sha256"]
        or by_kind["ACCEPTED_STATEMENT_DISCOVERY"]["size_bytes"] != discovery["size_bytes"]
    ):
        raise NativeStatementRowsError("native statement rows runtime evidence binding is invalid")
    for kind in (
        "SOURCE_REGISTRY",
        "DATASET_ROLE_REGISTRY",
        "THIS_POLICY",
        "NATIVE_TEXT_QUALITY_CONFIG",
        "GEOMETRY_CONFIG",
    ):
        committed = _file_identity_at_commit(project_root, code["commit"], expected_paths[kind])
        if by_kind[kind] != {"kind": kind, **committed}:
            raise NativeStatementRowsError(
                "native statement rows tracked runtime input does not match producer commit"
            )
    pages = payload.get("pages")
    selection = payload.get("selection")
    summary = payload.get("summary")
    if (
        not isinstance(pages, list)
        or not isinstance(selection, dict)
        or not isinstance(summary, dict)
    ):
        raise NativeStatementRowsError("native statement rows page/summary contract is invalid")
    _require_exact_keys(
        selection,
        {
            "policy",
            "selected_pages",
            "selected_page_count",
            "statement_page_counts",
            "notes_pages_selected",
        },
        "native statement rows selection",
    )
    contract_by_page = {int(contract["page"]): contract for contract in selected_contracts}
    expected_selected_pages = sorted(contract_by_page)
    expected_statement_counts = dict(
        sorted(Counter(str(contract["statement_type"]) for contract in selected_contracts).items())
    )
    expected_selection = {
        "policy": "ACCEPTED_DISCOVERY_CONTRACTS_ONLY",
        "selected_pages": expected_selected_pages,
        "selected_page_count": len(expected_selected_pages),
        "statement_page_counts": expected_statement_counts,
        "notes_pages_selected": 0,
    }
    if selection != expected_selection:
        raise NativeStatementRowsError("native statement rows selection contract is inconsistent")
    page_numbers = [page.get("page") for page in pages if isinstance(page, dict)]
    if (
        len(page_numbers) != len(pages)
        or page_numbers != sorted(set(page_numbers))
        or page_numbers != selection.get("selected_pages")
        or len(pages) != selection.get("selected_page_count")
    ):
        raise NativeStatementRowsError("native statement rows selected-page identity is invalid")

    row_ids: set[str] = set()
    row_count = 0
    cell_count = 0
    section_header_count = 0
    unlabeled_numeric_count = 0
    status_counts: Counter[str] = Counter()
    for page in pages:
        page = _require_exact_keys(
            page,
            {
                "page",
                "statement_type",
                "scope",
                "discovery_contract",
                "text_quality",
                "corruption_markers",
                "width_points",
                "height_points",
                "rotation",
                "native_word_count",
                "native_words_sha256",
                "geometry",
                "headers",
                "rows",
                "outside_financial_table_span_rows",
                "reconstructed_row_count",
                "financial_table_span_row_count",
                "outside_financial_table_span_row_count",
            },
            "native statement rows page",
        )
        page_number = page["page"]
        contract = contract_by_page.get(page_number)
        if (
            contract is None
            or page["discovery_contract"] != contract
            or page["statement_type"] != contract["statement_type"]
            or page["scope"] != contract["scope"]
        ):
            raise NativeStatementRowsError(
                "native statement rows page discovery contract is inconsistent"
            )
        if page.get("text_quality") != "USABLE_TEXT_LAYER":
            raise NativeStatementRowsError("native statement rows page is not usable native text")
        corruption_markers = page["corruption_markers"]
        if not isinstance(corruption_markers, list) or any(
            not isinstance(marker, str) for marker in corruption_markers
        ):
            raise NativeStatementRowsError("native statement rows corruption markers are invalid")
        width_points = _finite_number(page["width_points"], "native statement page width")
        height_points = _finite_number(page["height_points"], "native statement page height")
        if width_points <= 0 or height_points <= 0:
            raise NativeStatementRowsError("native statement page dimensions are invalid")
        if (
            isinstance(page["rotation"], bool)
            or not isinstance(page["rotation"], int)
            or page["rotation"] not in {0, 90, 180, 270}
            or isinstance(page["native_word_count"], bool)
            or not isinstance(page["native_word_count"], int)
            or page["native_word_count"] < 0
            or _SHA256.fullmatch(str(page["native_words_sha256"])) is None
        ):
            raise NativeStatementRowsError("native statement page word identity is invalid")
        geometry = _require_exact_keys(
            page["geometry"],
            {
                "authority",
                "data_start_y",
                "data_end_y",
                "label_right_boundary",
                "edge_tolerance",
                "axes",
                "unit_run_ids",
                "warnings",
            },
            "native statement page geometry",
        )
        data_start_y = _finite_number(geometry["data_start_y"], "geometry data start")
        data_end_y = _finite_number(geometry["data_end_y"], "geometry data end")
        label_boundary = _finite_number(geometry["label_right_boundary"], "geometry label boundary")
        edge_tolerance = _finite_number(geometry["edge_tolerance"], "geometry edge tolerance")
        if (
            geometry["authority"] != _NATIVE_GEOMETRY_AUTHORITY
            or not 0 <= data_start_y < data_end_y <= height_points
            or not 0 <= label_boundary <= width_points
            or edge_tolerance <= 0
        ):
            raise NativeStatementRowsError("native statement page geometry is invalid")
        axes = geometry["axes"]
        if not isinstance(axes, list) or not axes:
            raise NativeStatementRowsError("native statement page axes are absent")
        axis_ids: set[str] = set()
        value_axis_ids: set[str] = set()
        for axis in axes:
            axis = _require_exact_keys(
                axis,
                {"axis_id", "role", "right_edge", "left_edge", "sample_count", "source"},
                "native statement page axis",
            )
            axis_id = axis["axis_id"]
            if not isinstance(axis_id, str) or not axis_id or axis_id in axis_ids:
                raise NativeStatementRowsError("native statement page axis ID is invalid")
            axis_ids.add(axis_id)
            if axis["role"] not in {"NOTE_REFERENCE", "VALUE"}:
                raise NativeStatementRowsError("native statement page axis role is invalid")
            left_edge = _finite_number(axis["left_edge"], "axis left edge")
            right_edge = _finite_number(axis["right_edge"], "axis right edge")
            if (
                not 0 <= left_edge <= right_edge <= width_points
                or isinstance(axis["sample_count"], bool)
                or not isinstance(axis["sample_count"], int)
                or axis["sample_count"] < 1
                or not isinstance(axis["source"], str)
                or not axis["source"]
            ):
                raise NativeStatementRowsError("native statement page axis geometry is invalid")
            if axis["role"] == "VALUE":
                value_axis_ids.add(axis_id)
        if not value_axis_ids:
            raise NativeStatementRowsError("native statement page has no value axis")
        unit_run_ids = geometry["unit_run_ids"]
        geometry_warnings = geometry["warnings"]
        if (
            not isinstance(unit_run_ids, list)
            or len(set(unit_run_ids)) != len(unit_run_ids)
            or any(not isinstance(item, str) or not item for item in unit_run_ids)
            or not isinstance(geometry_warnings, list)
            or any(not isinstance(item, str) for item in geometry_warnings)
        ):
            raise NativeStatementRowsError("native statement page geometry evidence is invalid")
        headers = page["headers"]
        if not isinstance(headers, list):
            raise NativeStatementRowsError("native statement page headers are invalid")
        header_axis_ids = {
            _validate_serialized_header(
                header,
                value_axis_ids=value_axis_ids,
                width_points=width_points,
                height_points=height_points,
            )
            for header in headers
        }
        if len(header_axis_ids) != len(headers) or header_axis_ids != value_axis_ids:
            raise NativeStatementRowsError(
                "native statement page headers do not bind each value axis exactly once"
            )
        rows = page.get("rows")
        outside = page.get("outside_financial_table_span_rows")
        if not isinstance(rows, list) or not rows or not isinstance(outside, list):
            raise NativeStatementRowsError("native statement rows page row lists are invalid")
        count_fields = (
            "financial_table_span_row_count",
            "outside_financial_table_span_row_count",
            "reconstructed_row_count",
        )
        if any(
            isinstance(page[field], bool) or not isinstance(page[field], int) or page[field] < 0
            for field in count_fields
        ):
            raise NativeStatementRowsError("native statement rows page counts are invalid")
        if (
            len(rows) != page["financial_table_span_row_count"]
            or len(outside) != page["outside_financial_table_span_row_count"]
        ):
            raise NativeStatementRowsError("native statement rows page row counts are invalid")
        if len(rows) + len(outside) != page["reconstructed_row_count"]:
            raise NativeStatementRowsError("native statement reconstructed row count is invalid")
        table_id = (
            f"native-{source_sha256[:16]}-"
            f"{str(contract['statement_type']).casefold()}-"
            f"{str(contract['scope']).casefold().replace('_', '-')}-page-{page_number:04d}"
        )
        row_id_pattern = re.compile(rf"^{re.escape(table_id)}:row-(?P<ordinal>[0-9]{{4}})$")
        page_ordinals: list[int] = []
        for within_span, records in ((True, rows), (False, outside)):
            for row in records:
                counts = _validate_serialized_row(
                    row,
                    source_sha256=source_sha256,
                    page=page_number,
                    within_span=within_span,
                    table_id=table_id,
                    value_axis_ids=value_axis_ids,
                    width_points=width_points,
                    height_points=height_points,
                )
                row_id = row["row_id"]
                match = row_id_pattern.fullmatch(row_id)
                if match is None:
                    raise NativeStatementRowsError(
                        "native statement row ID/table provenance is invalid"
                    )
                page_ordinals.append(int(match.group("ordinal")))
                if row_id in row_ids:
                    raise NativeStatementRowsError("native statement row IDs are not unique")
                row_ids.add(row_id)
                if within_span:
                    row_count += counts[0]
                    cell_count += counts[1]
                    section_header_count += counts[2]
                    unlabeled_numeric_count += counts[3].pop("__UNLABELED_NUMERIC_ROWS__", 0)
                    status_counts.update(counts[3])
        if sorted(page_ordinals) != list(range(1, page["reconstructed_row_count"] + 1)):
            raise NativeStatementRowsError(
                "native statement row ordinals do not cover reconstructed source order"
            )
    expected_summary = {
        "page_count": len(pages),
        "pages_sha256": stable_records_hash(
            json.dumps(page, ensure_ascii=False, sort_keys=True) for page in pages
        ),
        "financial_table_span_row_count": row_count,
        "cell_count": cell_count,
        "section_header_count": section_header_count,
        "unlabeled_numeric_row_count": unlabeled_numeric_count,
        "cell_source_status_counts": dict(sorted(status_counts.items())),
        "schema_items_created": 0,
        "schema_items_mapped": 0,
    }
    if summary != expected_summary:
        raise NativeStatementRowsError("native statement rows summary is inconsistent")
    try:
        final_encoded = path.read_bytes()
    except OSError as exc:
        raise NativeStatementRowsError(
            "native statement rows artifact disappeared during load"
        ) from exc
    if final_encoded != encoded:
        raise NativeStatementRowsError("native statement rows artifact changed during load")
    return copy.deepcopy(payload)


def _write_exclusive(path: Path, payload: bytes) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise NativeStatementRowsError(f"refusing to overwrite native statement rows: {path}")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    linked_identity: tuple[int, int] | None = None
    try:
        with os.fdopen(descriptor, "wb") as stream:
            if stream.write(payload) != len(payload):
                raise NativeStatementRowsError("native statement rows output write was incomplete")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o644)
        temporary_stat = temporary.stat()
        try:
            os.link(temporary, path)
            linked_identity = (temporary_stat.st_dev, temporary_stat.st_ino)
        except FileExistsError as exc:
            raise NativeStatementRowsError(
                f"refusing to overwrite native statement rows: {path}"
            ) from exc
        published_stat = path.stat(follow_symlinks=False)
        if (published_stat.st_dev, published_stat.st_ino) != linked_identity:
            raise NativeStatementRowsError("native statement rows published inode changed")
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        if sha256_file(path) != sha256_bytes(payload):
            raise NativeStatementRowsError("native statement rows output hash mismatch")
        final_stat = path.stat(follow_symlinks=False)
        if (final_stat.st_dev, final_stat.st_ino) != linked_identity:
            raise NativeStatementRowsError("native statement rows published inode changed")
    except BaseException as publication_error:
        rollback_error: BaseException | None = None
        if linked_identity is not None:
            try:
                current = path.stat(follow_symlinks=False)
            except FileNotFoundError:
                current = None
            except BaseException as exc:
                rollback_error = exc
                current = None
            if current is not None:
                if (current.st_dev, current.st_ino) != linked_identity:
                    rollback_error = NativeStatementRowsError(
                        "refusing to roll back a changed native statement rows output"
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
            raise NativeStatementRowsError(
                f"native statement rows publication rollback was incomplete: {rollback_error}"
            ) from publication_error
        raise
    finally:
        temporary.unlink(missing_ok=True)


def publish_registered_native_statement_rows(
    project_root: Path,
    source_pdf: Path,
    discovery_path: Path,
    discovery_sha256: str,
    policy_path: Path,
    run_id: str,
    output_path: Path,
) -> NativeStatementRowsPublication:
    project_root = project_root.resolve()
    output_path = output_path.resolve()
    _relative_path(project_root, output_path, "native statement rows output")
    state = _current_git_state(project_root)
    payload = build_registered_native_statement_rows(
        project_root,
        source_pdf,
        discovery_path,
        discovery_sha256,
        policy_path,
        run_id,
        state,
    )
    role = payload["source"]["dataset_role"]
    allowed_directory = (project_root / _ROLE_DIRECTORIES[role]).resolve()
    try:
        output_path.relative_to(allowed_directory)
    except ValueError as exc:
        raise NativeStatementRowsError(
            f"native statement rows output for {role} must stay under {_ROLE_DIRECTORIES[role]}"
        ) from exc
    output_relative = _relative_path(project_root, output_path, "native statement rows output")
    _validate_path_isolation(
        [output_relative], load_native_statement_rows_policy(policy_path, project_root)
    )
    encoded = _canonical_json_bytes(payload)
    _write_exclusive(output_path, encoded)
    return NativeStatementRowsPublication(
        path=output_path,
        sha256=sha256_bytes(encoded),
        size_bytes=len(encoded),
        payload=payload,
    )
