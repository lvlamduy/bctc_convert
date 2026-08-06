from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.schema.registry import load_all


class HoldoutFreezeError(RuntimeError):
    pass


@dataclass(frozen=True)
class FrozenSourceEvidence:
    fixture_id: str
    fixture_role: str
    logical_path: str
    sha256: str
    size_bytes: int
    dataset_role: str
    role_assigned_at: str
    locally_present: bool
    s3_object_key: str


@dataclass(frozen=True)
class HoldoutFreezeValidation:
    experiment_id: str
    suite_id: str
    dataset_role: str
    frozen_at: str
    frozen_git_commit: str
    frozen_file_count: int
    frozen_files_sha256: dict[str, str]
    sources: tuple[FrozenSourceEvidence, ...]
    role_registry_sha256: str
    source_registry_sha256: str
    schema_item_count: int
    tm_1944_present: bool
    role_a_access_gate: str
    thresholds_reusable_for_retuning: bool


def _git(project_root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=check,
        capture_output=True,
        text=True,
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise HoldoutFreezeError(f"cannot read registry: {path}") from exc


def _parse_timestamp(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HoldoutFreezeError(f"invalid {field}: {value!r}") from exc
    if parsed.tzinfo is None:
        raise HoldoutFreezeError(f"{field} must be timezone-aware")
    return parsed


def _safe_path(project_root: Path, relative_path: str) -> Path:
    path = (project_root / relative_path).resolve()
    try:
        path.relative_to(project_root)
    except ValueError as exc:
        raise HoldoutFreezeError(f"path escapes project root: {relative_path}") from exc
    return path


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _git_file_sha256(project_root: Path, commit: str, relative_path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative_path}"],
        cwd=project_root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise HoldoutFreezeError(f"frozen Git object is missing: {commit}:{relative_path}")
    return _sha256_bytes(result.stdout)


def _load_payload(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, yaml.YAMLError) as exc:
        raise HoldoutFreezeError(f"cannot read holdout freeze: {path}") from exc
    if not isinstance(payload, dict):
        raise HoldoutFreezeError("holdout freeze must be a mapping")
    return payload


def validate_holdout_freeze(
    project_root: Path,
    config_path: Path,
    *,
    require_sources_absent: bool,
) -> HoldoutFreezeValidation:
    project_root = project_root.resolve()
    config_path = config_path.resolve()
    payload = _load_payload(config_path)
    required_identity = {
        "version": 1,
        "experiment_id": "E-0022",
        "dataset_role": "UNTOUCHED_HOLDOUT",
        "phase": "SOURCE_AND_PIPELINE_FREEZE_BEFORE_CONTENT_ACCESS",
        "content_inspected_before_role_assignment": False,
        "source_access_state_at_freeze": "BOTH_SOURCES_OFFLOADED_AND_ABSENT_LOCALLY",
        "role_a_access_before_role_b_seal": "FORBIDDEN",
        "threshold_changes_after_holdout_open": "FORBIDDEN_FOR_THIS_HOLDOUT",
    }
    mismatches = {
        key: {"expected": expected, "actual": payload.get(key)}
        for key, expected in required_identity.items()
        if payload.get(key) != expected
    }
    if mismatches:
        raise HoldoutFreezeError(f"holdout identity or safety drifted: {mismatches}")
    frozen_at = str(payload.get("frozen_at", ""))
    frozen_time = _parse_timestamp(frozen_at, "frozen_at")
    pairing = payload.get("pairing")
    if not isinstance(pairing, dict) or pairing != {
        "reference_fixture_id": "acb-q1-2026-consolidated-searchable",
        "candidate_fixture_id": "acb-q1-2026-consolidated-scan",
        "same_filing_assertion_basis": "FILENAME_METADATA_ONLY_NOT_CONTENT",
        "evaluation_scope": (
            "FULL_DOCUMENT_STATEMENT_DISCOVERY_THEN_ALL_DISCOVERED_CDKT_KQKD_LCTT_PAGES"
        ),
        "target_page_numbers_preselected": False,
        "page_pairing_uses": "VISUAL_FINGERPRINT_ONLY",
    }:
        raise HoldoutFreezeError("E-0022 pairing contract drifted")
    expected_execution = [
        "FREEZE_SOURCE_ROLES",
        "FREEZE_CODE_CONFIG_MODELS_AND_SCHEMA",
        "HYDRATE_ROLE_B_SOURCE_ONLY",
        "RUN_AND_SEAL_ROLE_B_FULL_DOCUMENT_DISCOVERY_AND_OCR",
        "HYDRATE_AND_OPEN_ROLE_A_SOURCE",
        "BUILD_AND_SEAL_ROLE_A_MACHINE_REFERENCE",
        "COMPARE_WITHOUT_THRESHOLD_CHANGES",
    ]
    if payload.get("execution_order") != expected_execution:
        raise HoldoutFreezeError("holdout execution order drifted")
    evidence_policy = payload.get("evidence_policy")
    expected_policy = {
        "role_b_can_read_role_a_source": False,
        "role_b_can_read_role_a_result": False,
        "role_b_can_use_historical_mongodb": False,
        "role_b_can_tune_frozen_thresholds": False,
        "compare_starts_after_role_b_complete": True,
        "reference_labels_available_to_role_b": False,
        "page_pairing_uses_text_or_values": False,
        "visible_pdf_remains_source_authority": True,
    }
    if evidence_policy != expected_policy:
        raise HoldoutFreezeError("holdout evidence policy drifted")

    frozen_pipeline = payload.get("frozen_pipeline")
    if not isinstance(frozen_pipeline, dict):
        raise HoldoutFreezeError("frozen pipeline is missing")
    frozen_commit = str(frozen_pipeline.get("git_commit", ""))
    if not frozen_commit:
        raise HoldoutFreezeError("frozen Git commit is missing")
    if _git(project_root, "cat-file", "-e", f"{frozen_commit}^{{commit}}", check=False).returncode:
        raise HoldoutFreezeError(f"frozen Git commit does not exist: {frozen_commit}")
    if _git(
        project_root, "merge-base", "--is-ancestor", frozen_commit, "HEAD", check=False
    ).returncode:
        raise HoldoutFreezeError("frozen pipeline commit is not an ancestor of HEAD")
    frozen_files: dict[str, str] = {}
    for group_name in ("config_files", "algorithm_files", "schema_workbooks"):
        group = frozen_pipeline.get(group_name)
        if not isinstance(group, dict) or not group:
            raise HoldoutFreezeError(f"frozen pipeline group is missing: {group_name}")
        for relative_path, expected_digest in group.items():
            relative = str(relative_path)
            digest = str(expected_digest)
            local_path = _safe_path(project_root, relative)
            if not local_path.is_file() or sha256_file(local_path) != digest:
                raise HoldoutFreezeError(f"frozen local file drifted: {relative}")
            if _git_file_sha256(project_root, frozen_commit, relative) != digest:
                raise HoldoutFreezeError(f"frozen Git file drifted: {relative}")
            if relative in frozen_files:
                raise HoldoutFreezeError(f"frozen path is duplicated: {relative}")
            frozen_files[relative] = digest

    source_registry_path = project_root / "data/registered/source_registry.jsonl"
    role_registry_path = project_root / "data/registered/dataset_roles.jsonl"
    source_registry = _read_jsonl(source_registry_path)
    role_registry = _read_jsonl(role_registry_path)
    source_by_path = {str(item.get("relative_path")): item for item in source_registry}
    role_by_document = {str(item.get("document_id")): item for item in role_registry}
    raw_sources = payload.get("sources")
    if not isinstance(raw_sources, list) or len(raw_sources) != 2:
        raise HoldoutFreezeError("E-0022 must freeze exactly two sources")
    source_evidence = []
    roles = set()
    for raw in raw_sources:
        if not isinstance(raw, dict):
            raise HoldoutFreezeError("invalid frozen source")
        logical_path = str(raw.get("path", ""))
        digest = str(raw.get("sha256", ""))
        size_bytes = int(raw.get("size_bytes", -1))
        fixture_role = str(raw.get("fixture_role", ""))
        roles.add(fixture_role)
        registered = source_by_path.get(logical_path)
        if (
            registered is None
            or registered.get("sha256") != digest
            or registered.get("size_bytes") != size_bytes
        ):
            raise HoldoutFreezeError(f"source registry mismatch: {logical_path}")
        document_id = f"sha256:{digest}"
        role = role_by_document.get(document_id)
        if (
            role is None
            or role.get("dataset_role") != "UNTOUCHED_HOLDOUT"
            or role.get("source_path") != logical_path
            or role.get("immutable") is not True
        ):
            raise HoldoutFreezeError(f"immutable holdout role mismatch: {logical_path}")
        assigned_at = str(role.get("assigned_at", ""))
        if assigned_at != str(raw.get("role_assigned_at", "")):
            raise HoldoutFreezeError(f"role timestamp drifted: {logical_path}")
        if _parse_timestamp(assigned_at, "role_assigned_at") > frozen_time:
            raise HoldoutFreezeError(f"role assigned after freeze: {logical_path}")
        local_path = _safe_path(project_root, logical_path)
        locally_present = local_path.is_file()
        if require_sources_absent and locally_present:
            raise HoldoutFreezeError(f"source was accessed before pre-access seal: {logical_path}")
        object_key = str(raw.get("s3_object_key", ""))
        if not object_key.endswith(digest):
            raise HoldoutFreezeError(f"content-addressed object key mismatch: {logical_path}")
        source_evidence.append(
            FrozenSourceEvidence(
                fixture_id=str(raw.get("fixture_id", "")),
                fixture_role=fixture_role,
                logical_path=logical_path,
                sha256=digest,
                size_bytes=size_bytes,
                dataset_role="UNTOUCHED_HOLDOUT",
                role_assigned_at=assigned_at,
                locally_present=locally_present,
                s3_object_key=object_key,
            )
        )
    if roles != {"ROLE_A_SOURCE", "ROLE_B_SOURCE"}:
        raise HoldoutFreezeError("E-0022 source roles are incomplete")

    _workbooks, schema_items = load_all(project_root / "template", project_root)
    tm_1944 = [item for item in schema_items if item.schema_id == 1944]
    if len(tm_1944) != 1 or tm_1944[0].canonical_name != (
        "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán"
    ):
        raise HoldoutFreezeError("TM ReportNormId 1944 is not preserved")
    return HoldoutFreezeValidation(
        experiment_id="E-0022",
        suite_id=str(payload.get("suite_id", "")),
        dataset_role="UNTOUCHED_HOLDOUT",
        frozen_at=frozen_at,
        frozen_git_commit=frozen_commit,
        frozen_file_count=len(frozen_files),
        frozen_files_sha256=dict(sorted(frozen_files.items())),
        sources=tuple(source_evidence),
        role_registry_sha256=sha256_file(role_registry_path),
        source_registry_sha256=sha256_file(source_registry_path),
        schema_item_count=len(schema_items),
        tm_1944_present=True,
        role_a_access_gate="FORBIDDEN_UNTIL_ROLE_B_SEALED",
        thresholds_reusable_for_retuning=False,
    )


def capture_pre_access_holdout_freeze(
    project_root: Path,
    *,
    config_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain").stdout.strip():
        raise HoldoutFreezeError("pre-access capture requires a clean Git worktree")
    output = output_path if output_path.is_absolute() else project_root / output_path
    output = output.resolve()
    try:
        output.relative_to(project_root)
    except ValueError as exc:
        raise HoldoutFreezeError("pre-access artifact must remain inside project root") from exc
    if output.exists():
        raise HoldoutFreezeError(f"refusing to overwrite pre-access artifact: {output}")
    config = config_path if config_path.is_absolute() else project_root / config_path
    validation = validate_holdout_freeze(
        project_root,
        config.resolve(),
        require_sources_absent=True,
    )
    payload = {
        "format_version": 1,
        "experiment_id": "E-0022",
        "state": "PRE_ACCESS_HOLDOUT_FREEZE_VERIFIED",
        "dataset_role": "UNTOUCHED_HOLDOUT",
        "capture_git_commit": _git(project_root, "rev-parse", "HEAD").stdout.strip(),
        "capture_git_dirty": False,
        "freeze_config": {
            "path": config.resolve().relative_to(project_root).as_posix(),
            "sha256": sha256_file(config),
        },
        "validation": asdict(validation),
        "source_content_read_by_capture": False,
        "all_sources_locally_absent": all(
            not source.locally_present for source in validation.sources
        ),
        "allowed_next_action": "HYDRATE_ROLE_B_SOURCE_ONLY",
        "role_a_access_permitted": False,
        "claim_boundary": (
            "This artifact proves registry/config/Git/hash gates and local absence before "
            "content access. It does not inspect PDF bytes and is not extraction accuracy."
        ),
    }
    atomic_write_json(output, payload)
    return payload
