from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import fitz
import yaml

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.evaluation.holdout_freeze import validate_holdout_freeze
from bctc_ai.storage.content_store import content_path


class HoldoutExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class RoleBExecutionValidation:
    experiment_id: str
    phase: str
    frozen_git_commit: str
    role_b_path: str
    role_b_sha256: str
    role_b_size_bytes: int
    role_b_page_count: int
    role_b_text_layer_chars_first_five_pages: tuple[int, ...]
    role_a_path: str
    role_a_locally_present: bool
    role_a_immutable_path: str
    role_a_immutable_locally_present: bool
    role_a_holdout_output_count: int
    output_root: str
    output_root_exists: bool
    execution_file_count: int
    execution_files_sha256: dict[str, str]
    allowed_next_action: str


def _git(project_root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=check,
        capture_output=True,
        text=False,
    )


def _safe_path(project_root: Path, value: str) -> Path:
    path = (project_root / value).resolve()
    try:
        path.relative_to(project_root)
    except ValueError as exc:
        raise HoldoutExecutionError(f"path escapes project root: {value}") from exc
    return path


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (FileNotFoundError, yaml.YAMLError) as exc:
        raise HoldoutExecutionError(f"cannot read Role B execution control: {path}") from exc
    if not isinstance(payload, dict):
        raise HoldoutExecutionError("Role B execution control must be a mapping")
    return payload


def _git_file_sha256(project_root: Path, commit: str, relative_path: str) -> str:
    result = _git(project_root, "show", f"{commit}:{relative_path}", check=False)
    if result.returncode != 0:
        raise HoldoutExecutionError(f"execution file is absent at frozen commit: {relative_path}")
    return hashlib.sha256(result.stdout).hexdigest()


def _verify_pre_access_artifact(project_root: Path, upstream: dict[str, Any]) -> None:
    artifact_path = _safe_path(project_root, str(upstream.get("pre_access_artifact", "")))
    expected_digest = str(upstream.get("pre_access_artifact_sha256", ""))
    if not artifact_path.is_file() or sha256_file(artifact_path) != expected_digest:
        raise HoldoutExecutionError("E-0022 pre-access artifact is absent or hash-drifted")
    try:
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HoldoutExecutionError("E-0022 pre-access artifact is invalid JSON") from exc
    if (
        artifact.get("state") != "PRE_ACCESS_HOLDOUT_FREEZE_VERIFIED"
        or artifact.get("all_sources_locally_absent") is not True
        or artifact.get("role_a_access_permitted") is not False
        or artifact.get("allowed_next_action") != "HYDRATE_ROLE_B_SOURCE_ONLY"
    ):
        raise HoldoutExecutionError("E-0022 pre-access artifact safety contract drifted")


def validate_role_b_execution_control(
    project_root: Path,
    config_path: Path,
) -> RoleBExecutionValidation:
    project_root = project_root.resolve()
    config_path = config_path.resolve()
    payload = _load_yaml(config_path)
    expected_identity = {
        "version": 1,
        "experiment_id": "E-0022",
        "phase": "ROLE_B_EXECUTION_CONTROL_AFTER_AUTHORIZED_HYDRATION_BEFORE_PREPROCESSING",
        "dataset_role": "UNTOUCHED_HOLDOUT",
        "source_access_before_control": "ROLE_B_PAGE_COUNT_AND_TEXT_LAYER_PRESENCE_ONLY",
        "threshold_or_page_selection_tuning_performed": False,
        "role_a_access_permitted": False,
        "allowed_next_action": "PREPROCESS_ROLE_B_FULL_DOCUMENT",
    }
    drift = {
        key: {"expected": expected, "actual": payload.get(key)}
        for key, expected in expected_identity.items()
        if payload.get(key) != expected
    }
    if drift:
        raise HoldoutExecutionError(f"Role B execution identity/safety drifted: {drift}")
    upstream = payload.get("upstream")
    role_b = payload.get("role_b")
    role_a = payload.get("role_a")
    execution = payload.get("execution")
    files = payload.get("execution_files_at_frozen_commit")
    if not all(isinstance(item, dict) for item in (upstream, role_b, role_a, execution, files)):
        raise HoldoutExecutionError("Role B execution control sections are incomplete")
    assert isinstance(upstream, dict)
    assert isinstance(role_b, dict)
    assert isinstance(role_a, dict)
    assert isinstance(execution, dict)
    assert isinstance(files, dict)
    _verify_pre_access_artifact(project_root, upstream)
    suite_path = _safe_path(project_root, str(upstream.get("suite_config", "")))
    frozen = validate_holdout_freeze(project_root, suite_path, require_sources_absent=False)
    frozen_commit = str(upstream.get("frozen_git_commit", ""))
    if frozen.frozen_git_commit != frozen_commit:
        raise HoldoutExecutionError("execution control frozen commit differs from pre-access gate")
    frozen_sources = {source.fixture_role: source for source in frozen.sources}
    frozen_role_b = frozen_sources.get("ROLE_B_SOURCE")
    frozen_role_a = frozen_sources.get("ROLE_A_SOURCE")
    if frozen_role_b is None or frozen_role_a is None:
        raise HoldoutExecutionError("pre-access source roles are incomplete")
    expected_role_b_control = {
        "path": frozen_role_b.logical_path,
        "sha256": frozen_role_b.sha256,
        "size_bytes": frozen_role_b.size_bytes,
    }
    if any(role_b.get(key) != value for key, value in expected_role_b_control.items()):
        raise HoldoutExecutionError("Role B control differs from the pre-access frozen source")
    expected_role_a_control = {
        "path": frozen_role_a.logical_path,
        "sha256": frozen_role_a.sha256,
    }
    if any(role_a.get(key) != value for key, value in expected_role_a_control.items()):
        raise HoldoutExecutionError("Role A control differs from the pre-access frozen source")

    role_b_path_value = str(role_b.get("path", ""))
    role_b_path = _safe_path(project_root, role_b_path_value)
    role_b_digest = str(role_b.get("sha256", ""))
    role_b_size = int(role_b.get("size_bytes", -1))
    if (
        not role_b_path.is_file()
        or role_b_path.stat().st_size != role_b_size
        or sha256_file(role_b_path) != role_b_digest
    ):
        raise HoldoutExecutionError("authorized Role B source is absent or hash-drifted")
    role_a_path_value = str(role_a.get("path", ""))
    role_a_path = _safe_path(project_root, role_a_path_value)
    if role_a.get("required_local_state") != "ABSENT_UNTIL_ROLE_B_SEALED":
        raise HoldoutExecutionError("Role A local-state gate drifted")
    if role_a_path.exists():
        raise HoldoutExecutionError("Role A source access is forbidden before Role B seal")
    role_a_immutable = content_path(
        project_root / "data" / "immutable",
        frozen_role_a.sha256,
        Path(frozen_role_a.logical_path).suffix,
    )
    if role_a_immutable.exists():
        raise HoldoutExecutionError("Role A immutable source exists before Role B seal")
    holdout_root = project_root / "output" / "holdout"
    role_a_outputs = (
        sorted(holdout_root.glob(f"*/{frozen_role_a.sha256[:20]}")) if holdout_root.is_dir() else []
    )
    if role_a_outputs:
        raise HoldoutExecutionError("Role A holdout output exists before Role B seal")

    with fitz.open(role_b_path) as document:
        page_count = document.page_count
        text_counts = tuple(
            len(document[index].get_text()) for index in range(min(5, document.page_count))
        )
    if page_count != int(role_b.get("expected_page_count", -1)):
        raise HoldoutExecutionError("Role B page count differs from the execution control")
    if list(text_counts) != role_b.get("expected_text_layer_chars_first_five_pages"):
        raise HoldoutExecutionError("Role B initial text-layer evidence drifted")

    expected_execution = {
        "run_id": "e0022-acb-q1-2026-role-b",
        "output_root": (f"output/holdout/e0022-acb-q1-2026-role-b/{frozen_role_b.sha256[:20]}"),
        "preprocess_dpi": 300,
        "preprocess_pages": "FULL_DOCUMENT_NO_PRESELECTED_PAGE_NUMBERS",
        "discovery_reader": "PP_OCRV6_WORD_BOX_FULL_DOCUMENT",
        "final_semantic_reader": "PADDLEOCR_VL_ON_DISCOVERED_MAIN_STATEMENT_PAGES_ONLY",
        "historical_reference_permitted": False,
        "role_a_source_or_result_permitted": False,
    }
    if any(execution.get(key) != value for key, value in expected_execution.items()):
        raise HoldoutExecutionError("Role B execution evidence policy drifted")
    output_root_value = str(execution.get("output_root", ""))
    output_root = _safe_path(project_root, output_root_value)
    if output_root.exists():
        raise HoldoutExecutionError("Role B output root already exists before preprocessing")

    verified_files: dict[str, str] = {}
    for relative_path, expected_digest in files.items():
        relative = str(relative_path)
        digest = str(expected_digest)
        local_path = _safe_path(project_root, relative)
        if not local_path.is_file() or sha256_file(local_path) != digest:
            raise HoldoutExecutionError(f"Role B execution file drifted locally: {relative}")
        if _git_file_sha256(project_root, frozen_commit, relative) != digest:
            raise HoldoutExecutionError(
                f"Role B execution file drifted at frozen commit: {relative}"
            )
        verified_files[relative] = digest
    return RoleBExecutionValidation(
        experiment_id="E-0022",
        phase=str(payload["phase"]),
        frozen_git_commit=frozen_commit,
        role_b_path=role_b_path_value,
        role_b_sha256=role_b_digest,
        role_b_size_bytes=role_b_size,
        role_b_page_count=page_count,
        role_b_text_layer_chars_first_five_pages=text_counts,
        role_a_path=role_a_path_value,
        role_a_locally_present=False,
        role_a_immutable_path=role_a_immutable.relative_to(project_root).as_posix(),
        role_a_immutable_locally_present=False,
        role_a_holdout_output_count=0,
        output_root=output_root_value,
        output_root_exists=False,
        execution_file_count=len(verified_files),
        execution_files_sha256=dict(sorted(verified_files.items())),
        allowed_next_action="PREPROCESS_ROLE_B_FULL_DOCUMENT",
    )


def capture_role_b_execution_control(
    project_root: Path,
    *,
    config_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain").stdout.strip():
        raise HoldoutExecutionError("formal Role B execution control requires a clean worktree")
    config = config_path if config_path.is_absolute() else project_root / config_path
    output = output_path if output_path.is_absolute() else project_root / output_path
    output = output.resolve()
    try:
        output.relative_to(project_root)
    except ValueError as exc:
        raise HoldoutExecutionError("Role B control artifact must remain inside project") from exc
    if output.exists():
        raise HoldoutExecutionError(f"refusing to overwrite Role B control artifact: {output}")
    validation = validate_role_b_execution_control(project_root, config.resolve())
    payload = {
        "format_version": 1,
        "experiment_id": "E-0022",
        "state": "ROLE_B_EXECUTION_READY",
        "dataset_role": "UNTOUCHED_HOLDOUT",
        "capture_git_commit": _git(project_root, "rev-parse", "HEAD").stdout.decode().strip(),
        "capture_git_dirty": False,
        "configuration": {
            "path": config.resolve().relative_to(project_root).as_posix(),
            "sha256": sha256_file(config),
        },
        "validation": asdict(validation),
        "role_a_access_permitted": False,
        "threshold_or_page_selection_tuning_performed": False,
        "allowed_next_action": "PREPROCESS_ROLE_B_FULL_DOCUMENT",
        "claim_boundary": (
            "Role B input/execution readiness only; no OCR, mapping, value or accuracy claim."
        ),
    }
    atomic_write_json(output, payload)
    return payload
