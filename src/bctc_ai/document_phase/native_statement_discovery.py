from __future__ import annotations

import copy
import json
import math
import os
import re
import subprocess
import tempfile
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.hashing import sha256_bytes, sha256_file, stable_records_hash
from bctc_ai.document_phase.multisignal_statement_discovery_v4 import (
    discover_statement_pages_v4,
    load_multisignal_statement_config_v4,
)
from bctc_ai.document_phase.statement_locator import OCRLine, OCRPage, StatementLocatorError
from bctc_ai.ocr.native_text_quality_v2 import (
    assess_native_text_quality_v2,
    extract_pdf_text_v2,
    load_native_text_quality_v2_config,
)
from bctc_ai.ocr.pdf_text import PDFTextPage, PDFWord

POLICY_RELATIVE_PATH = Path("config/document_phase/native-statement-discovery-v1.yaml")

_POLICY_NAME = "REGISTERED_NATIVE_TEXT_STATEMENT_DISCOVERY_V1"
_OUTPUT_FORMAT = "REGISTERED_NATIVE_TEXT_STATEMENT_DISCOVERY_RESULT_V1"
_CLAIM_BOUNDARY = "STATEMENT_PAGE_DISCOVERY_ONLY"
_ADAPTED_DISCOVERY_POLICY = "NATIVE_TEXT_MULTI_SIGNAL_ORDERED_DOCUMENT_DISCOVERY_V1"
_BASE_GEOMETRY_AUTHORITY = "PP_OCRV6_WORD_BOXES"
_NATIVE_GEOMETRY_AUTHORITY = "PYMUPDF_NATIVE_TEXT_WORDS"
_SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_GIT_COMMIT = re.compile(r"^[0-9a-f]{40}$")
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
_CONFIG_CHAIN = (
    (
        "config/document_phase/statement-discovery-v3.yaml",
        "f8188fdf53b8f3907ab89d5407bcea178fe927dfe02ccad291a79d1b5f1ba182",
    ),
    (
        "config/document_phase/statement-locator-v2.yaml",
        "503f3fdb62dd5dcd1a460200750edfe18d7cf50039b62278666e572c6cccb730",
    ),
    (
        "config/document_phase/statement-locator-v1.yaml",
        "d25ff6da2a1ce48428b4ab1ac20a31b989a27849d93326ae839507dce2ff107e",
    ),
)
_IMPLEMENTATION_PATHS = (
    "src/bctc_ai/ocr/pdf_text.py",
    "src/bctc_ai/ocr/native_text_quality_v2.py",
    "src/bctc_ai/document_phase/statement_locator.py",
    "src/bctc_ai/document_phase/statement_locator_v2.py",
    "src/bctc_ai/document_phase/multisignal_statement_discovery.py",
    "src/bctc_ai/document_phase/multisignal_statement_discovery_v4.py",
    "src/bctc_ai/document_phase/native_statement_discovery.py",
)


class NativeStatementDiscoveryError(RuntimeError):
    pass


@dataclass(frozen=True)
class NativeStatementDiscoveryPublication:
    path: Path
    sha256: str
    size_bytes: int
    payload: dict[str, Any]


def _resolve_under_root(project_root: Path, raw_path: str, label: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path or Path(raw_path).is_absolute():
        raise NativeStatementDiscoveryError(f"{label} must be a project-relative path")
    path = (project_root / raw_path).resolve()
    try:
        path.relative_to(project_root)
    except ValueError as exc:
        raise NativeStatementDiscoveryError(f"{label} escapes the project root") from exc
    return path


def _read_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise NativeStatementDiscoveryError(f"cannot read {label}: {path}") from exc
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise NativeStatementDiscoveryError(
                f"{label} line {line_number} is invalid JSON"
            ) from exc
        if not isinstance(record, dict):
            raise NativeStatementDiscoveryError(f"{label} line {line_number} must be a JSON object")
        records.append(record)
    return records


def _validate_identity_file(project_root: Path, raw: Any, label: str) -> tuple[Path, str]:
    if not isinstance(raw, dict) or set(raw) != {"path", "sha256"}:
        raise NativeStatementDiscoveryError(f"{label} identity must contain path and sha256")
    path = _resolve_under_root(project_root, raw["path"], label)
    expected = raw["sha256"]
    if not isinstance(expected, str) or len(expected) != 64 or not path.is_file():
        raise NativeStatementDiscoveryError(f"{label} identity is invalid or absent")
    if sha256_file(path) != expected:
        raise NativeStatementDiscoveryError(f"{label} hash drifted")
    return path, expected


def load_native_statement_discovery_policy(
    path: Path,
    project_root: Path,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    path = path.resolve()
    expected_path = (project_root / POLICY_RELATIVE_PATH).resolve()
    if path != expected_path:
        raise NativeStatementDiscoveryError(
            f"native statement discovery requires canonical policy {POLICY_RELATIVE_PATH}"
        )
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise NativeStatementDiscoveryError(f"cannot load native discovery policy: {path}") from exc
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
        raise NativeStatementDiscoveryError("native discovery policy identity drifted")
    if set(payload.get("allowed_dataset_roles", ())) != _ALLOWED_ROLES:
        raise NativeStatementDiscoveryError("native discovery allowed-role policy drifted")
    if set(payload.get("forbidden_dataset_roles", ())) != _FORBIDDEN_ROLES:
        raise NativeStatementDiscoveryError("native discovery forbidden-role policy drifted")

    quality = payload.get("native_text_quality_config")
    discovery = payload.get("statement_discovery_config")
    _validate_identity_file(project_root, quality, "native-text quality config")
    _validate_identity_file(
        project_root,
        {"path": discovery.get("path"), "sha256": discovery.get("sha256")}
        if isinstance(discovery, dict)
        else discovery,
        "statement-discovery config",
    )
    expected_discovery = {
        "engine": "MULTISIGNAL_V4_SCORING_REUSE",
        "adapted_policy": _ADAPTED_DISCOVERY_POLICY,
        "base_geometry_authority": _BASE_GEOMETRY_AUTHORITY,
        "geometry_authority": _NATIVE_GEOMETRY_AUTHORITY,
        "geometry_evidence_source": "PYMUPDF_NATIVE_TEXT_GEOMETRY",
        "authority_override_scope": "GEOMETRY_SOURCE_ONLY",
    }
    if not isinstance(discovery, dict) or any(
        discovery.get(key) != value for key, value in expected_discovery.items()
    ):
        raise NativeStatementDiscoveryError("native discovery geometry-authority policy drifted")
    raw_chain = payload.get("statement_discovery_config_chain")
    if not isinstance(raw_chain, list) or len(raw_chain) != len(_CONFIG_CHAIN):
        raise NativeStatementDiscoveryError("statement-discovery config chain is incomplete")
    chain = tuple(
        (item.get("path"), item.get("sha256")) for item in raw_chain if isinstance(item, dict)
    )
    if chain != _CONFIG_CHAIN:
        raise NativeStatementDiscoveryError("statement-discovery config chain drifted")
    for index, item in enumerate(raw_chain):
        _validate_identity_file(
            project_root, item, f"statement-discovery config chain item {index}"
        )

    native_gate = payload.get("native_text_gate")
    expected_gate = {
        "usable_status": "USABLE_TEXT_LAYER",
        "require_all_pages_usable": True,
        "non_usable_page_action": "FAIL_CLOSED_OCR_REQUIRED",
        "require_usable_selected_statement_pages": True,
        "require_usable_notes_boundary_page": True,
    }
    if native_gate != expected_gate:
        raise NativeStatementDiscoveryError("native-text gate policy drifted")
    isolation = payload.get("role_isolation")
    if not isinstance(isolation, dict):
        raise NativeStatementDiscoveryError("native discovery isolation policy is absent")
    expected_allowed_inputs = {
        "SOURCE_PDF",
        "SOURCE_REGISTRY",
        "DATASET_ROLE_REGISTRY",
        "THIS_POLICY",
        "NATIVE_TEXT_QUALITY_CONFIG",
        "STATEMENT_DISCOVERY_CONFIG",
    }
    if set(isolation.get("runtime_input_allowlist", ())) != expected_allowed_inputs:
        raise NativeStatementDiscoveryError("native discovery runtime-input allowlist drifted")
    if any(
        isolation.get(key) is not False
        for key in (
            "prior_answer_artifacts_allowed",
            "historical_values_allowed",
            "role_a_outputs_allowed",
        )
    ):
        raise NativeStatementDiscoveryError("native discovery answer isolation was weakened")
    fragments = isolation.get("forbidden_path_fragments")
    if (
        not isinstance(fragments, list)
        or not fragments
        or any(
            not isinstance(fragment, str) or not fragment.startswith("/") for fragment in fragments
        )
    ):
        raise NativeStatementDiscoveryError("native discovery forbidden-path policy is invalid")
    output = payload.get("output")
    if output != {
        "format": _OUTPUT_FORMAT,
        "exclusive_no_overwrite": True,
        "absolute_project_paths_allowed": False,
        "source_visible_text_preserved_verbatim": True,
        "deterministic_json": True,
        "role_directories": _ROLE_DIRECTORIES,
    }:
        raise NativeStatementDiscoveryError("native discovery output contract drifted")
    return copy.deepcopy(payload)


def _words_to_line(words: list[PDFWord]) -> OCRLine:
    ordered = sorted(words, key=lambda item: (item.word_number, item.bbox_points.x0))
    return OCRLine(
        text=" ".join(word.raw_text for word in ordered),
        bbox=(
            min(word.bbox_points.x0 for word in ordered),
            min(word.bbox_points.y0 for word in ordered),
            max(word.bbox_points.x1 for word in ordered),
            max(word.bbox_points.y1 for word in ordered),
        ),
        # Native PDF words are source text, not an OCR confidence estimate.
        # A score of one means only that this line is present in the text layer.
        score=1.0,
    )


def pdf_text_page_to_ocr_page(page: PDFTextPage, usable: bool) -> OCRPage:
    if page.page < 1 or page.width_points <= 0 or page.height_points <= 0:
        raise NativeStatementDiscoveryError("native PDF page identity/dimensions are invalid")
    lines: tuple[OCRLine, ...] = ()
    if usable:
        groups: OrderedDict[tuple[int, int], list[PDFWord]] = OrderedDict()
        for word in page.words:
            groups.setdefault((word.block_number, word.line_number), []).append(word)
        ordered_groups = sorted(
            groups.items(),
            key=lambda item: (
                min(word.bbox_points.y0 for word in item[1]),
                min(word.bbox_points.x0 for word in item[1]),
                item[0][0],
                item[0][1],
            ),
        )
        lines = tuple(_words_to_line(words) for _, words in ordered_groups if words)
    return OCRPage(
        page=page.page,
        width=math.ceil(page.width_points),
        height=math.ceil(page.height_points),
        lines=lines,
    )


def _registered_source(
    project_root: Path,
    source_pdf: Path,
    policy: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], str, str]:
    source_pdf = source_pdf.resolve()
    try:
        relative = source_pdf.relative_to(project_root).as_posix()
    except ValueError as exc:
        raise NativeStatementDiscoveryError("source PDF must be inside the project root") from exc
    if not source_pdf.is_file() or source_pdf.suffix.casefold() != ".pdf":
        raise NativeStatementDiscoveryError("registered source PDF is absent or not a PDF")
    source_registry_path = _resolve_under_root(
        project_root, policy["source_registry"], "source registry"
    )
    role_registry_path = _resolve_under_root(
        project_root, policy["dataset_role_registry"], "dataset-role registry"
    )
    source_records = _read_jsonl(source_registry_path, "source registry")
    matches = [record for record in source_records if record.get("relative_path") == relative]
    if len(matches) != 1:
        raise NativeStatementDiscoveryError(
            f"source PDF must have exactly one registry record; found {len(matches)}"
        )
    source_record = matches[0]
    digest = sha256_file(source_pdf)
    expected_document_id = f"sha256:{digest}"
    if (
        source_record.get("sha256") != digest
        or source_record.get("document_id") != expected_document_id
        or source_record.get("size_bytes") != source_pdf.stat().st_size
        or source_record.get("kind") != "PDF"
        or source_record.get("state") != "REGISTERED"
        or source_record.get("hash_verified_stable") is not True
    ):
        raise NativeStatementDiscoveryError("source PDF registry identity drifted")
    role_records = _read_jsonl(role_registry_path, "dataset-role registry")
    role_matches = [
        record for record in role_records if record.get("document_id") == expected_document_id
    ]
    if len(role_matches) != 1:
        raise NativeStatementDiscoveryError(
            f"source PDF must have exactly one role record; found {len(role_matches)}"
        )
    role_record = role_matches[0]
    role = role_record.get("dataset_role")
    if role in _FORBIDDEN_ROLES:
        raise NativeStatementDiscoveryError(
            f"source PDF dataset role {role} is forbidden for this development runner"
        )
    if (
        role not in _ALLOWED_ROLES
        or role_record.get("source_path") != relative
        or role_record.get("immutable") is not True
    ):
        raise NativeStatementDiscoveryError("source PDF dataset role is not eligible")
    return source_record, role_record, digest, relative


def _identity_record(project_root: Path, path: Path, kind: str) -> dict[str, Any]:
    path = path.resolve()
    try:
        relative = path.relative_to(project_root).as_posix()
    except ValueError as exc:
        raise NativeStatementDiscoveryError(f"runtime input escapes project root: {path}") from exc
    return {
        "kind": kind,
        "path": relative,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _git(project_root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise NativeStatementDiscoveryError(
            f"git {' '.join(arguments)} failed: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def _current_git_state(project_root: Path) -> dict[str, Any]:
    return {
        "commit": _git(project_root, "rev-parse", "HEAD"),
        "dirty": bool(_git(project_root, "status", "--porcelain", "--untracked-files=all")),
    }


def _validate_git_state(git_state: dict[str, Any]) -> dict[str, Any]:
    commit = git_state.get("commit") if isinstance(git_state, dict) else None
    dirty = git_state.get("dirty") if isinstance(git_state, dict) else None
    if (
        not isinstance(commit, str)
        or _GIT_COMMIT.fullmatch(commit) is None
        or type(dirty) is not bool
    ):
        raise NativeStatementDiscoveryError("native discovery Git state is invalid")
    if dirty:
        raise NativeStatementDiscoveryError("refusing native discovery from a dirty worktree")
    return {"commit": commit, "dirty": False}


def _adapted_discovery_config(
    project_root: Path,
    policy: dict[str, Any],
) -> tuple[dict[str, Any], Path]:
    identity = policy["statement_discovery_config"]
    config_path = _resolve_under_root(project_root, identity["path"], "statement discovery config")
    try:
        config = load_multisignal_statement_config_v4(config_path)
    except StatementLocatorError as exc:
        raise NativeStatementDiscoveryError("cannot load base statement-discovery engine") from exc
    if config.get("geometry_authority") != identity["base_geometry_authority"]:
        raise NativeStatementDiscoveryError("base statement-discovery geometry authority drifted")
    adapted = copy.deepcopy(config)
    adapted["policy"] = identity["adapted_policy"]
    adapted["base_policy"] = config["policy"]
    adapted["base_geometry_authority"] = config["geometry_authority"]
    adapted["geometry_authority"] = identity["geometry_authority"]
    adapted["geometry_evidence_source"] = identity["geometry_evidence_source"]
    adapted["geometry_authority_override_scope"] = identity["authority_override_scope"]
    return adapted, config_path


def _canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


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
            raise NativeStatementDiscoveryError(f"implementation module is absent: {raw_path}")
        records.append(
            {"path": raw_path, "sha256": sha256_file(path), "size_bytes": path.stat().st_size}
        )
    return records


def build_registered_native_statement_discovery(
    project_root: Path,
    source_pdf: Path,
    policy_path: Path,
    run_id: str,
    git_state: dict[str, Any],
) -> dict[str, Any]:
    project_root = project_root.resolve()
    source_pdf = source_pdf.resolve()
    if not _SAFE_RUN_ID.fullmatch(run_id):
        raise NativeStatementDiscoveryError("native discovery run_id is invalid")
    code = _validate_git_state(git_state)
    policy = load_native_statement_discovery_policy(policy_path, project_root)
    quality_identity = policy["native_text_quality_config"]
    quality_path = _resolve_under_root(
        project_root, quality_identity["path"], "native-text quality config"
    )
    discovery_path = _resolve_under_root(
        project_root,
        policy["statement_discovery_config"]["path"],
        "statement discovery config",
    )
    source_registry_path = _resolve_under_root(
        project_root, policy["source_registry"], "source registry"
    )
    role_registry_path = _resolve_under_root(
        project_root, policy["dataset_role_registry"], "dataset-role registry"
    )
    chain_paths = [
        _resolve_under_root(project_root, raw_path, "statement-discovery config chain")
        for raw_path, _ in _CONFIG_CHAIN
    ]
    runtime_input_paths = [
        (source_pdf, "SOURCE_PDF"),
        (source_registry_path, "SOURCE_REGISTRY"),
        (role_registry_path, "DATASET_ROLE_REGISTRY"),
        (policy_path, "THIS_POLICY"),
        (quality_path, "NATIVE_TEXT_QUALITY_CONFIG"),
        (discovery_path, "STATEMENT_DISCOVERY_CONFIG"),
        *((path, "STATEMENT_DISCOVERY_CONFIG") for path in chain_paths),
    ]
    runtime_inputs = _runtime_input_ledger(project_root, runtime_input_paths)
    implementation = _implementation_ledger(project_root)

    source_record, role_record, source_sha256, source_relative = _registered_source(
        project_root, source_pdf, policy
    )
    source_identity = next(record for record in runtime_inputs if record["kind"] == "SOURCE_PDF")
    if (
        source_identity["sha256"] != source_sha256
        or source_identity["size_bytes"] != source_record["size_bytes"]
    ):
        raise NativeStatementDiscoveryError("source PDF changed during registry validation")

    quality_config = load_native_text_quality_v2_config(quality_path)
    discovery_config, loaded_discovery_path = _adapted_discovery_config(project_root, policy)
    if loaded_discovery_path != discovery_path:
        raise NativeStatementDiscoveryError("statement-discovery config resolver is inconsistent")

    pages = extract_pdf_text_v2(source_pdf, config=quality_config)
    if not pages or tuple(page.page for page in pages) != tuple(range(1, len(pages) + 1)):
        raise NativeStatementDiscoveryError("native discovery requires every PDF page in order")
    page_records: list[dict[str, Any]] = []
    geometry_pages: list[OCRPage] = []
    ocr_required_pages: list[int] = []
    for page in pages:
        assessment = assess_native_text_quality_v2(page.words, quality_config)
        usable = assessment.status == policy["native_text_gate"]["usable_status"]
        if not usable:
            ocr_required_pages.append(page.page)
        geometry = pdf_text_page_to_ocr_page(page, usable=usable)
        geometry_pages.append(geometry)
        page_records.append(
            {
                "page": page.page,
                "width_points": page.width_points,
                "height_points": page.height_points,
                "rotation": page.rotation,
                "word_count": len(page.words),
                "line_count": len(geometry.lines),
                "text_quality": assessment.status,
                "corruption_markers": list(assessment.corruption_markers),
                "quality_assessment": assessment.to_dict(),
                "native_line_sha256": stable_records_hash(
                    json.dumps(
                        {
                            "text": line.text,
                            "bbox": list(line.bbox),
                            "source_text_present": line.score == 1.0,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    for line in geometry.lines
                ),
            }
        )
    if ocr_required_pages and policy["native_text_gate"]["require_all_pages_usable"]:
        raise NativeStatementDiscoveryError(
            "native text is not usable on every page; OCR required for pages "
            + ",".join(str(page) for page in ocr_required_pages)
        )

    try:
        discovery = discover_statement_pages_v4(tuple(geometry_pages), discovery_config)
    except StatementLocatorError as exc:
        raise NativeStatementDiscoveryError("native statement discovery failed") from exc
    if discovery.get("geometry_authority") != _NATIVE_GEOMETRY_AUTHORITY:
        raise NativeStatementDiscoveryError("native geometry authority was not preserved")

    final_runtime_inputs = _runtime_input_ledger(project_root, runtime_input_paths)
    if final_runtime_inputs != runtime_inputs:
        raise NativeStatementDiscoveryError("runtime input bytes changed during discovery")
    final_implementation = _implementation_ledger(project_root)
    if final_implementation != implementation:
        raise NativeStatementDiscoveryError("implementation bytes changed during discovery")
    allowed_kinds = set(policy["role_isolation"]["runtime_input_allowlist"])
    if any(record["kind"] not in allowed_kinds for record in runtime_inputs):
        raise NativeStatementDiscoveryError("runtime input ledger contains a forbidden input kind")
    normalized_paths = [f"/{record['path'].casefold().strip('/')}" for record in runtime_inputs]
    forbidden_fragments = [
        fragment.casefold() for fragment in policy["role_isolation"]["forbidden_path_fragments"]
    ]
    if any(fragment in path for path in normalized_paths for fragment in forbidden_fragments):
        raise NativeStatementDiscoveryError("runtime input ledger contains a forbidden path")

    final_status = (
        "ACCEPTED_NATIVE_TEXT_STATEMENT_DISCOVERY"
        if discovery.get("status") == "ACCEPTED_MULTI_SIGNAL_STATEMENT_BLOCK"
        else "UNRESOLVED_NATIVE_TEXT_STATEMENT_DISCOVERY"
    )
    payload: dict[str, Any] = {
        "format_version": _OUTPUT_FORMAT,
        "policy": policy["policy"],
        "claim_boundary": policy["claim_boundary"],
        "status": final_status,
        "run_id": run_id,
        "source": {
            "document_id": source_record["document_id"],
            "relative_path": source_relative,
            "sha256": source_sha256,
            "size_bytes": source_record["size_bytes"],
            "bank": source_record.get("bank"),
            "year": source_record.get("year"),
            "dataset_role": role_record["dataset_role"],
            "registry_state": source_record["state"],
            "hash_verified_stable": source_record["hash_verified_stable"],
            "immutable_role_assignment": role_record["immutable"],
        },
        "code": {**code, "implementation": implementation},
        "authority": {
            "geometry": _NATIVE_GEOMETRY_AUTHORITY,
            "base_scoring_engine": "MULTISIGNAL_STATEMENT_DISCOVERY_V4",
            "base_geometry_authority": _BASE_GEOMETRY_AUTHORITY,
            "evidence_source": "PYMUPDF_NATIVE_TEXT_GEOMETRY",
            "override_scope": "GEOMETRY_SOURCE_ONLY",
            "semantic_reader": None,
        },
        "isolation": {
            "prior_answer_artifacts_loaded": False,
            "historical_values_loaded": False,
            "role_a_outputs_loaded": False,
            "bank_identity_used_for_scoring": False,
            "filename_identity_used_for_scoring": False,
            "page_number_rules_used_for_scoring": False,
            "runtime_input_policy": "EXACT_DECLARED_PROJECT_INPUT_LEDGER",
        },
        "inputs": {
            "runtime_read_ledger": runtime_inputs,
            "runtime_read_ledger_sha256": stable_records_hash(
                json.dumps(record, ensure_ascii=False, sort_keys=True) for record in runtime_inputs
            ),
        },
        "native_text": {
            "page_count": len(page_records),
            "usable_page_count": len(page_records) - len(ocr_required_pages),
            "ocr_required_pages": ocr_required_pages,
            "all_pages_usable": not ocr_required_pages,
            "pages": page_records,
        },
        "discovery": discovery,
    }
    # Re-parse the deterministic bytes to ensure the returned object is JSON-safe
    # and independent of dataclass or enum representations.
    return json.loads(_canonical_json_bytes(payload))


def _write_exclusive(path: Path, payload: bytes) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise NativeStatementDiscoveryError(f"refusing to overwrite native discovery: {path}")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o644)
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise NativeStatementDiscoveryError(
                f"refusing to overwrite native discovery: {path}"
            ) from exc
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)
    if sha256_file(path) != sha256_bytes(payload):
        raise NativeStatementDiscoveryError("native discovery output hash mismatch")


def publish_registered_native_statement_discovery(
    project_root: Path,
    source_pdf: Path,
    policy_path: Path,
    run_id: str,
    output_path: Path,
) -> NativeStatementDiscoveryPublication:
    project_root = project_root.resolve()
    output_path = output_path.resolve()
    try:
        output_path.relative_to(project_root)
    except ValueError as exc:
        raise NativeStatementDiscoveryError(
            "native discovery output must stay in project root"
        ) from exc
    state = _current_git_state(project_root)
    payload = build_registered_native_statement_discovery(
        project_root,
        source_pdf,
        policy_path,
        run_id,
        state,
    )
    role = payload["source"]["dataset_role"]
    allowed_directory = (project_root / _ROLE_DIRECTORIES[role]).resolve()
    try:
        output_path.relative_to(allowed_directory)
    except ValueError as exc:
        raise NativeStatementDiscoveryError(
            f"native discovery output for {role} must stay under {_ROLE_DIRECTORIES[role]}"
        ) from exc
    encoded = _canonical_json_bytes(payload)
    _write_exclusive(output_path, encoded)
    return NativeStatementDiscoveryPublication(
        path=output_path,
        sha256=sha256_bytes(encoded),
        size_bytes=len(encoded),
        payload=payload,
    )
