"""Authenticate the sole tracked V3 VietOCR run and expose text proposals.

This module has no caller-selected artifact paths, hashes, or Git commits.  It
accepts an opaque live freeze capability, reads one fixed completed run, and
trusts that run only after a fixed post-run selection file has been added to
Git.  The receipt grants Vietnamese text-proposal authority only.
"""

from __future__ import annotations

import hashlib
import math
import os
import pickle
import re
import stat
import subprocess
import unicodedata
import weakref
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.vietocr_all_line_freezer_v3 import (
    EXPECTED_LINE_COUNT_VECTOR,
    EXPECTED_SAMPLE_COUNT,
    AuthenticatedVietOCRAllLineFreezeV3,
    assert_authenticated_vietocr_all_line_freeze_project_root_v3,
    read_authenticated_vietocr_all_line_snapshot_v3,
)
from bctc_ai.ocr.vietocr_all_line_runner_v3 import (
    _EXECUTION_POLICY,
    _EXPECTED_ARTIFACTS,
    _EXPECTED_PACKAGES,
    _SAFETY,
    ATTEMPT_FORMAT_VERSION,
    CONFIG_PATH,
    EXPERIMENT_ID,
    RESULT_FORMAT_VERSION,
    RUN_FORMAT_VERSION,
    RUN_ROOT,
    _validate_config,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    decode_canonical_json_bytes_v1,
    same_typed_json_v1,
)

__all__ = [
    "SELECTION_PATH",
    "AuthenticatedVietOCRAllLineRunV3",
    "AuthenticatedVietOCRSemanticReceiptV3",
    "VietOCRSemanticReceiptV3Error",
    "authenticate_tracked_vietocr_all_line_run_v3",
    "build_authenticated_vietocr_semantic_receipt_v3",
    "build_vietocr_all_line_run_selection_v3",
    "project_authenticated_vietocr_semantic_receipt_v3",
    "read_authenticated_vietocr_semantic_page_v3",
    "read_authenticated_vietocr_semantic_proposals_v3",
]


class VietOCRSemanticReceiptV3Error(RuntimeError):
    """The V3 frozen run, tracked selection, or receipt failed exact replay."""


SELECTION_PATH = Path("docs/experiments/loan-maturity-8bank-vietocr-all-line-run-selection-v3.json")
ATTEMPT_PATH = RUN_ROOT / "attempt.json"
RESULT_PATH = RUN_ROOT / "ocr_result.json"
RUN_PATH = RUN_ROOT / "run_manifest.json"
SELECTION_FORMAT_VERSION = "BCTC_AI_VIETOCR_ALL_LINE_RUN_SELECTION_V3"
RECEIPT_FORMAT_VERSION = "BCTC_AI_VIETOCR_ALL_LINE_SEMANTIC_RECEIPT_V3"
SELECTION_STATE = "POST_RUN_SOLE_FIXED_OUTPUT_SELECTED"
RECEIPT_STATE = "REPLAY_AUTHENTICATED_SEMANTIC_PROPOSALS_READY"
CLAIM_BOUNDARY = (
    "REPLAY_AUTHENTICATED_FIXED_SELECTED_VIETOCR_VIETNAMESE_TEXT_PROPOSALS_ONLY_"
    "NO_HISTORICAL_ATTEMPT_RETRY_OR_QUALITY_SELECTION_ABSENCE_ATTESTATION_"
    "NO_NUMERIC_GEOMETRY_PERIOD_UNIT_SCOPE_ACCOUNTING_SCHEMA_OR_MAPPING_AUTHORITY"
)
_RUNNER_PATH = Path("src/bctc_ai/ocr/vietocr_all_line_runner_v3.py")
_FREEZER_PATH = Path("src/bctc_ai/evaluation/vietocr_all_line_freezer_v3.py")
_RECEIPT_PATH = Path("src/bctc_ai/source_structure/vietocr_semantic_receipt_v3.py")
_ORCHESTRATOR_PATH = Path("scripts/experiments/run_vietocr_all_line_8bank_v3.py")
_SHA = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SAMPLE = re.compile(r"^(page-[0-9]{4})-line-([0-9]{4})$")
_PIN_FIELDS = {"path", "sha256", "size_bytes"}
_SAFETY_RECEIPT = {
    **_SAFETY,
    "reader_output_is_proposal_only": True,
    "source_transcript_used_for_semantic_identity": False,
}
_SELECTION_AUTHORITY = {
    "caller_selected_artifact_pins": False,
    "hardware_execution_attestation": False,
    "historical_attempt_absence_attestation": False,
    "quality_selection_absence_attestation": False,
    "retry_absence_attestation": False,
    "semantic_proposal_selection_only": True,
}
_SELECTION_POLICY = (
    "FIXED_CURRENT_COMPLETED_OUTPUT_SELECTED_POST_RUN_"
    "NO_HISTORICAL_ATTEMPT_RETRY_OR_QUALITY_SELECTION_ABSENCE_ATTESTATION"
)


def _error(message: str) -> VietOCRSemanticReceiptV3Error:
    return VietOCRSemanticReceiptV3Error(message)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _exact(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise _error(f"{label} fields drifted")
    return value


def _integer(value: Any, expected: int, label: str) -> int:
    if type(value) is not int or value != expected:
        raise _error(f"{label} drifted")
    return value


def _resolve_root(value: Path) -> Path:
    if not isinstance(value, Path):
        raise _error("project root must be a pathlib Path")
    root = value.resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise _error("project root is unsafe")
    try:
        git_top = Path(_git(root, "rev-parse", "--show-toplevel").decode("utf-8").strip())
    except UnicodeDecodeError as exc:
        raise _error("Git top-level path is not UTF-8") from exc
    if not git_top.is_absolute() or git_top.resolve(strict=True) != root:
        raise _error("project root must exactly equal the Git top-level directory")
    return root


def _stable_bytes(root: Path, relative: Path, label: str) -> bytes:
    if relative.is_absolute() or ".." in relative.parts:
        raise _error(f"{label} path is unsafe")
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    file_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    current = os.open(root, directory_flags)
    descriptor: int | None = None
    try:
        for part in relative.parts[:-1]:
            following = os.open(part, directory_flags, dir_fd=current)
            os.close(current)
            current = following
        descriptor = os.open(relative.parts[-1], file_flags, dir_fd=current)
    except OSError as exc:
        os.close(current)
        raise _error(f"cannot open nofollow {label}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise _error(f"{label} is not a regular file")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)
        if (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            raise _error(f"{label} changed during read")
        payload = b"".join(chunks)
        if len(payload) != before.st_size:
            raise _error(f"{label} stable-read size drifted")
        return payload
    finally:
        os.close(descriptor)
        os.close(current)


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = decode_canonical_json_bytes_v1(payload)
    except ValueError as exc:
        raise _error(f"{label} is not canonical duplicate-free JSON") from exc
    if type(value) is not dict:
        raise _error(f"{label} must be a JSON object")
    return value


def _pin(path: Path, payload: bytes) -> dict[str, Any]:
    return {"path": path.as_posix(), "sha256": _sha(payload), "size_bytes": len(payload)}


def _validate_pin(value: Any, path: Path, payload: bytes, label: str) -> dict[str, Any]:
    record = _exact(value, _PIN_FIELDS, label)
    if not same_typed_json_v1(record, _pin(path, payload)):
        raise _error(f"{label} byte identity drifted")
    return record


def _git(root: Path, *args: str) -> bytes:
    try:
        return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True).stdout
    except subprocess.CalledProcessError as exc:
        raise _error(f"Git provenance check failed: {' '.join(args)}") from exc


def _clean_head(root: Path) -> str:
    if _git(root, "status", "--porcelain", "--untracked-files=normal"):
        raise _error("V3 selection replay requires a clean Git worktree")
    head = _git(root, "rev-parse", "HEAD").decode().strip()
    if _COMMIT.fullmatch(head) is None:
        raise _error("current Git commit is malformed")
    return head


def _is_ancestor(root: Path, ancestor: str, descendant: str, label: str) -> None:
    try:
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        raise _error(f"{label} ancestry is invalid") from exc


def _selection_id(value: dict[str, Any]) -> str:
    material = canonical_clone_v1(value)
    material.pop("selection_id", None)
    return f"voalsv3:selection:{canonical_json_sha256_v1(material)}"


def _result_id(value: dict[str, Any]) -> str:
    material = canonical_clone_v1(value)
    material.pop("result_id", None)
    return f"voalrv3:result:{canonical_json_sha256_v1(material)}"


def _run_id(value: dict[str, Any]) -> str:
    material = canonical_clone_v1(value)
    material.pop("run_id", None)
    return f"voalrv3:run:{canonical_json_sha256_v1(material)}"


def _validate_datetime(value: Any, label: str) -> str:
    if type(value) is not str:
        raise _error(f"{label} must be one timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise _error(f"{label} is malformed") from exc
    if parsed.tzinfo is None:
        raise _error(f"{label} must be timezone-aware")
    return value


def _validate_attempt(
    value: Any,
    freeze_id: str,
    run_commit: str,
    root: Path,
) -> dict[str, Any]:
    attempt = _exact(
        value,
        {"attempt_id", "claim_boundary", "format_version", "preflight", "started_at", "state"},
        "V3 attempt",
    )
    preflight = _exact(
        attempt["preflight"],
        {
            "configuration_ref",
            "execution_policy",
            "experiment_id",
            "freeze_id",
            "git_binding",
            "line_count_vector",
            "page_count",
            "runtime_artifacts",
            "sample_count",
        },
        "V3 attempt preflight",
    )
    git = _exact(
        preflight["git_binding"],
        {"commit", "dirty", "implementation_refs", "source_tree_oid"},
        "V3 attempt Git binding",
    )
    configuration_payload = _stable_bytes(root, CONFIG_PATH, "V3 attempt configuration")
    _validate_config(configuration_payload)
    _validate_pin(
        preflight["configuration_ref"],
        CONFIG_PATH,
        configuration_payload,
        "V3 attempt configuration",
    )
    if _git(root, "show", f"{run_commit}:{CONFIG_PATH.as_posix()}") != configuration_payload:
        raise _error("V3 attempt configuration differs from the run commit")
    implementation_refs = git["implementation_refs"]
    if type(implementation_refs) is not list or len(implementation_refs) != 4:
        raise _error("V3 attempt implementation ledger drifted")
    expected_implementation_paths = [
        _FREEZER_PATH.as_posix(),
        _RUNNER_PATH.as_posix(),
        _ORCHESTRATOR_PATH.as_posix(),
        CONFIG_PATH.as_posix(),
    ]
    for record, path_text in zip(implementation_refs, expected_implementation_paths, strict=True):
        path = Path(path_text)
        payload = _stable_bytes(root, path, f"V3 attempt implementation {path}")
        _validate_pin(record, path, payload, "V3 attempt implementation ref")
        if _git(root, "show", f"{run_commit}:{path.as_posix()}") != payload:
            raise _error(f"V3 attempt implementation differs from run commit: {path}")
    runtime_artifacts = _exact(
        preflight["runtime_artifacts"], set(_EXPECTED_ARTIFACTS), "V3 attempt runtime artifacts"
    )
    for name, (digest, size) in _EXPECTED_ARTIFACTS.items():
        record = _exact(runtime_artifacts[name], _PIN_FIELDS, f"V3 attempt runtime {name}")
        if (
            record["path"]
            != {
                "base_config": "artifacts/base.yml",
                "model_config": "artifacts/vgg-transformer.yml",
                "weights": "artifacts/vgg_transformer.pth",
                "wheel": "artifacts/vietocr-0.3.13-py3-none-any.whl",
            }[name]
            or record["sha256"] != digest
            or record["size_bytes"] != size
        ):
            raise _error(f"V3 attempt runtime artifact drifted: {name}")
    if (
        attempt["format_version"] != ATTEMPT_FORMAT_VERSION
        or attempt["claim_boundary"] != "FRESH_REFERENCE_BLIND_SEMANTIC_PROPOSAL_ATTEMPT_ONLY"
        or attempt["state"] != "FORMAL_ATTEMPT_STARTED_NO_RESUME_OR_RETRY"
        or preflight["experiment_id"] != EXPERIMENT_ID
        or preflight["freeze_id"] != freeze_id
        or not same_typed_json_v1(preflight["line_count_vector"], list(EXPECTED_LINE_COUNT_VECTOR))
        or not same_typed_json_v1(preflight["execution_policy"], _EXECUTION_POLICY)
        or git["commit"] != run_commit
        or git["dirty"] is not False
        or _COMMIT.fullmatch(git["source_tree_oid"]) is None
    ):
        raise _error("V3 attempt identity or policy drifted")
    _integer(preflight["page_count"], 8, "V3 attempt page count")
    _integer(preflight["sample_count"], EXPECTED_SAMPLE_COUNT, "V3 attempt sample count")
    _validate_datetime(attempt["started_at"], "V3 attempt start")
    material = canonical_clone_v1(preflight)
    expected_id = f"voalrv3:attempt:{canonical_json_sha256_v1(material)}"
    if attempt["attempt_id"] != expected_id:
        raise _error("V3 attempt ID drifted")
    return attempt


def _png_dimensions(payload: Any) -> tuple[int, int]:
    if type(payload) is not bytes or len(payload) < 24 or payload[:8] != b"\x89PNG\r\n\x1a\n":
        raise _error("authenticated crop is not one PNG byte snapshot")
    if payload[12:16] != b"IHDR" or int.from_bytes(payload[8:12], "big") != 13:
        raise _error("authenticated crop PNG header drifted")
    width = int.from_bytes(payload[16:20], "big")
    height = int.from_bytes(payload[20:24], "big")
    if width <= 0 or height <= 0:
        raise _error("authenticated crop PNG dimensions drifted")
    return width, height


def _expected_processed_dimensions(crop_payload: bytes) -> tuple[int, int]:
    width, height = _png_dimensions(crop_payload)
    scaled_width = (32 * width) // height
    rounded_width = ((scaled_width + 9) // 10) * 10
    return max(32, min(512, rounded_width)), 32


def _validate_result(
    value: Any,
    freeze_id: str,
    batch: tuple[dict[str, Any], ...],
    attempt_id: str,
) -> dict[str, Any]:
    result = _exact(
        value,
        {
            "attempt_id",
            "dataset_role",
            "evidence_role",
            "experiment_id",
            "format_version",
            "freeze_id",
            "line_count_vector",
            "page_count",
            "reference_text_available_to_reader",
            "result_id",
            "sample_count",
            "samples",
            "state",
        },
        "V3 OCR result",
    )
    if (
        result["format_version"] != RESULT_FORMAT_VERSION
        or result["experiment_id"] != EXPERIMENT_ID
        or result["state"] != "REFERENCE_BLIND_LINE_INFERENCE_COMPLETE"
        or result["dataset_role"] != "LOGIC_DEVELOPMENT_AND_CALIBRATION"
        or result["evidence_role"] != "INDEPENDENT_VIETNAMESE_SEMANTIC_PROPOSAL_ONLY"
        or result["attempt_id"] != attempt_id
        or result["freeze_id"] != freeze_id
        or not same_typed_json_v1(result["line_count_vector"], list(EXPECTED_LINE_COUNT_VECTOR))
        or result["reference_text_available_to_reader"] is not False
        or type(result["samples"]) is not list
        or len(result["samples"]) != EXPECTED_SAMPLE_COUNT
    ):
        raise _error("V3 OCR result identity or denominator drifted")
    _integer(result["page_count"], 8, "V3 result page count")
    _integer(result["sample_count"], EXPECTED_SAMPLE_COUNT, "V3 result sample count")
    fields = {
        "crop_sha256",
        "mean_decoded_character_probability",
        "page_id",
        "processed_height",
        "processed_width",
        "raw_prediction",
        "sample_id",
    }
    for proposal, source in zip(result["samples"], batch, strict=True):
        expected_width, expected_height = _expected_processed_dimensions(source["crop_png_bytes"])
        if (
            type(proposal) is not dict
            or set(proposal) != fields
            or proposal["sample_id"] != source["sample_id"]
            or proposal["page_id"] != source["page_id"]
            or proposal["crop_sha256"] != source["crop_sha256"]
            or type(proposal["raw_prediction"]) is not str
            or type(proposal["processed_width"]) is not int
            or proposal["processed_width"] != expected_width
            or type(proposal["processed_height"]) is not int
            or proposal["processed_height"] != expected_height
            or len(proposal["raw_prediction"]) > 129
            or type(proposal["mean_decoded_character_probability"]) is not float
            or not math.isfinite(proposal["mean_decoded_character_probability"])
            or not 0.0 <= proposal["mean_decoded_character_probability"] <= 1.0
        ):
            raise _error("V3 OCR proposal differs from its authenticated crop")
    if result["result_id"] != _result_id(result):
        raise _error("V3 OCR result ID drifted")
    return result


def _validate_run(
    value: Any,
    attempt: dict[str, Any],
    result: dict[str, Any],
    attempt_raw: bytes,
    result_raw: bytes,
) -> dict[str, Any]:
    run = _exact(
        value,
        {
            "artifacts",
            "attempt_id",
            "completed_at",
            "configuration",
            "execution_counts",
            "execution_policy",
            "experiment_id",
            "format_version",
            "git_binding",
            "input",
            "metrics",
            "result_id",
            "run_id",
            "runtime",
            "safety",
            "started_at",
            "state",
        },
        "V3 run manifest",
    )
    if (
        run["format_version"] != RUN_FORMAT_VERSION
        or run["experiment_id"] != EXPERIMENT_ID
        or run["state"] != "FRESH_SINGLE_RUN_COMPLETE"
        or run["attempt_id"] != attempt["attempt_id"]
        or run["result_id"] != result["result_id"]
        or not same_typed_json_v1(run["execution_policy"], _EXECUTION_POLICY)
        or not same_typed_json_v1(run["safety"], _SAFETY)
        or run["started_at"] != attempt["started_at"]
        or not same_typed_json_v1(run["git_binding"], attempt["preflight"]["git_binding"])
        or not same_typed_json_v1(run["configuration"], attempt["preflight"]["configuration_ref"])
    ):
        raise _error("V3 run identity, policy, or safety drifted")
    _validate_datetime(run["completed_at"], "V3 run completion")
    if datetime.fromisoformat(run["completed_at"]) < datetime.fromisoformat(run["started_at"]):
        raise _error("V3 run timestamps are reversed")
    artifacts = _exact(run["artifacts"], {"attempt", "ocr_result"}, "V3 run artifacts")
    _validate_pin(artifacts["attempt"], ATTEMPT_PATH, attempt_raw, "V3 attempt pin")
    _validate_pin(artifacts["ocr_result"], RESULT_PATH, result_raw, "V3 result pin")
    expected_counts = {
        "authenticated_batch_accessor_call_count": 1,
        "checkpoint_deserialization_count": 1,
        "formal_run_count": 1,
        "model_build_count": 1,
        "process_input_count": EXPECTED_SAMPLE_COUNT,
        "reader_request_count": 1,
        "result_count": EXPECTED_SAMPLE_COUNT,
        "state_dict_load_count": 1,
        "translate_call_count": EXPECTED_SAMPLE_COUNT,
    }
    if not same_typed_json_v1(run["execution_counts"], expected_counts):
        raise _error("V3 execution counts drifted")
    input_record = _exact(
        run["input"],
        {"freeze_id", "line_count_vector", "page_count", "sample_count"},
        "V3 run input",
    )
    if input_record["freeze_id"] != result["freeze_id"] or not same_typed_json_v1(
        input_record["line_count_vector"], list(EXPECTED_LINE_COUNT_VECTOR)
    ):
        raise _error("V3 run input binding drifted")
    _integer(input_record["page_count"], 8, "V3 run page count")
    _integer(input_record["sample_count"], EXPECTED_SAMPLE_COUNT, "V3 run sample count")
    runtime = _exact(
        run["runtime"],
        {
            "artifacts",
            "compute_capability",
            "cuda_runtime",
            "device_name",
            "packages",
            "python_major_minor",
            "runtime_root",
        },
        "V3 runtime",
    )
    if (
        runtime["compute_capability"] != "8.9"
        or runtime["cuda_runtime"] != "13.0"
        or runtime["device_name"] != "NVIDIA GeForce RTX 4090"
        or not same_typed_json_v1(runtime["packages"], _EXPECTED_PACKAGES)
        or runtime["python_major_minor"] != "3.11"
        or runtime["runtime_root"] != "/workspace/bctc-ai-runtime/vietocr-0.3.13"
    ):
        raise _error("V3 runtime identity drifted")
    if type(runtime["artifacts"]) is not dict or set(runtime["artifacts"]) != set(
        _EXPECTED_ARTIFACTS
    ):
        raise _error("V3 runtime artifact names drifted")
    for name, (digest, size) in _EXPECTED_ARTIFACTS.items():
        record = _exact(runtime["artifacts"][name], _PIN_FIELDS, f"V3 runtime {name}")
        if (
            record["path"]
            != {
                "base_config": "artifacts/base.yml",
                "model_config": "artifacts/vgg-transformer.yml",
                "weights": "artifacts/vgg_transformer.pth",
                "wheel": "artifacts/vietocr-0.3.13-py3-none-any.whl",
            }[name]
            or record["sha256"] != digest
            or record["size_bytes"] != size
        ):
            raise _error(f"V3 runtime artifact identity drifted: {name}")
    metric_fields = {
        "model_load_seconds",
        "peak_gpu_memory_allocated_mib",
        "peak_gpu_memory_reserved_mib",
        "total_wall_seconds",
    }
    metrics = _exact(run["metrics"], metric_fields, "V3 run metrics")
    if any(
        type(item) is not float or not math.isfinite(item) or item < 0 for item in metrics.values()
    ):
        raise _error("V3 run metrics drifted")
    if run["run_id"] != _run_id(run):
        raise _error("V3 run ID drifted")
    return run


def _load_completed_run(
    root: Path, freeze: AuthenticatedVietOCRAllLineFreezeV3
) -> tuple[
    dict[str, Any],
    tuple[dict[str, Any], ...],
    bytes,
    dict[str, Any],
    bytes,
    dict[str, Any],
    bytes,
    dict[str, Any],
]:
    if type(freeze) is not AuthenticatedVietOCRAllLineFreezeV3:
        raise _error("V3 run replay requires the exact live freeze capability")
    projection, batch = read_authenticated_vietocr_all_line_snapshot_v3(freeze)
    attempt_raw = _stable_bytes(root, ATTEMPT_PATH, "V3 attempt")
    result_raw = _stable_bytes(root, RESULT_PATH, "V3 OCR result")
    run_raw = _stable_bytes(root, RUN_PATH, "V3 run manifest")
    run_unchecked = _strict_json(run_raw, "V3 run manifest")
    git = _exact(
        run_unchecked.get("git_binding"),
        {"commit", "dirty", "implementation_refs", "source_tree_oid"},
        "V3 run Git binding",
    )
    run_commit = git["commit"]
    if _COMMIT.fullmatch(run_commit) is None or git["dirty"] is not False:
        raise _error("V3 run Git commit is malformed or dirty")
    attempt = _validate_attempt(
        _strict_json(attempt_raw, "V3 attempt"), projection["freeze_id"], run_commit, root
    )
    result = _validate_result(
        _strict_json(result_raw, "V3 OCR result"),
        projection["freeze_id"],
        batch,
        attempt["attempt_id"],
    )
    run = _validate_run(run_unchecked, attempt, result, attempt_raw, result_raw)
    return projection, batch, attempt_raw, attempt, result_raw, result, run_raw, run


def build_vietocr_all_line_run_selection_v3(
    project_root: Path,
    freeze_capability: AuthenticatedVietOCRAllLineFreezeV3,
) -> dict[str, Any]:
    """Build, but never publish, the fixed post-run selection payload."""

    root = _resolve_root(project_root)
    assert_authenticated_vietocr_all_line_freeze_project_root_v3(root, freeze_capability)
    head = _clean_head(root)
    projection, _batch, attempt_raw, attempt, result_raw, result, run_raw, run = (
        _load_completed_run(root, freeze_capability)
    )
    run_commit = run["git_binding"]["commit"]
    if head != run_commit or (root / SELECTION_PATH).exists():
        raise _error(
            "selection must be built once at the exact clean run commit before publication"
        )
    material = {
        "artifacts": {
            "attempt": _pin(ATTEMPT_PATH, attempt_raw),
            "ocr_result": _pin(RESULT_PATH, result_raw),
            "run_manifest": _pin(RUN_PATH, run_raw),
        },
        "authority": canonical_clone_v1(_SELECTION_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "experiment_id": EXPERIMENT_ID,
        "format_version": SELECTION_FORMAT_VERSION,
        "freeze_id": projection["freeze_id"],
        "line_count_vector": list(EXPECTED_LINE_COUNT_VECTOR),
        "page_count": 8,
        "result_id": result["result_id"],
        "run_commit": run_commit,
        "run_id": run["run_id"],
        "sample_count": EXPECTED_SAMPLE_COUNT,
        "selection_policy": _SELECTION_POLICY,
        "source_tree_oid": run["git_binding"]["source_tree_oid"],
        "state": SELECTION_STATE,
    }
    selection = {**material, "selection_id": _selection_id(material)}
    if _clean_head(root) != head:
        raise _error("Git HEAD or worktree changed while building V3 selection")
    return selection


def _validate_selection(
    value: Any,
    projection: dict[str, Any],
    attempt_raw: bytes,
    result_raw: bytes,
    result: dict[str, Any],
    run_raw: bytes,
    run: dict[str, Any],
) -> dict[str, Any]:
    selection = _exact(
        value,
        {
            "artifacts",
            "authority",
            "claim_boundary",
            "experiment_id",
            "format_version",
            "freeze_id",
            "line_count_vector",
            "page_count",
            "result_id",
            "run_commit",
            "run_id",
            "sample_count",
            "selection_id",
            "selection_policy",
            "source_tree_oid",
            "state",
        },
        "V3 tracked selection",
    )
    if (
        selection["format_version"] != SELECTION_FORMAT_VERSION
        or selection["state"] != SELECTION_STATE
        or selection["claim_boundary"] != CLAIM_BOUNDARY
        or selection["experiment_id"] != EXPERIMENT_ID
        or selection["selection_policy"] != _SELECTION_POLICY
        or selection["freeze_id"] != projection["freeze_id"]
        or not same_typed_json_v1(selection["line_count_vector"], list(EXPECTED_LINE_COUNT_VECTOR))
        or selection["result_id"] != result["result_id"]
        or selection["run_commit"] != run["git_binding"]["commit"]
        or selection["run_id"] != run["run_id"]
        or selection["source_tree_oid"] != run["git_binding"]["source_tree_oid"]
        or not same_typed_json_v1(selection["authority"], _SELECTION_AUTHORITY)
    ):
        raise _error("V3 tracked selection identity or boundary drifted")
    _integer(selection["page_count"], 8, "selection page count")
    _integer(selection["sample_count"], EXPECTED_SAMPLE_COUNT, "selection sample count")
    artifacts = _exact(
        selection["artifacts"], {"attempt", "ocr_result", "run_manifest"}, "selection artifacts"
    )
    _validate_pin(artifacts["attempt"], ATTEMPT_PATH, attempt_raw, "selection attempt")
    _validate_pin(artifacts["ocr_result"], RESULT_PATH, result_raw, "selection result")
    _validate_pin(artifacts["run_manifest"], RUN_PATH, run_raw, "selection run")
    if selection["selection_id"] != _selection_id(selection):
        raise _error("V3 tracked selection ID drifted")
    return selection


def _verify_selection_git(
    root: Path, selection_raw: bytes, selection: dict[str, Any]
) -> dict[str, Any]:
    head = _clean_head(root)
    run_commit = selection["run_commit"]
    additions = [
        item
        for item in _git(
            root,
            "log",
            "--all",
            "--diff-filter=A",
            "--format=%H",
            "--",
            SELECTION_PATH.as_posix(),
        )
        .decode()
        .splitlines()
        if item
    ]
    if len(additions) != 1 or _COMMIT.fullmatch(additions[0]) is None:
        raise _error("V3 selection path does not have one unique Git ADD commit")
    selection_commit = additions[0]
    parents = _git(root, "show", "-s", "--format=%P", selection_commit).decode().split()
    if parents != [run_commit]:
        raise _error("V3 selection commit is not the direct non-merge child of the run commit")
    changed = [
        line
        for line in _git(
            root,
            "diff-tree",
            "--no-commit-id",
            "--name-status",
            "-r",
            selection_commit,
        )
        .decode("utf-8")
        .splitlines()
        if line
    ]
    if changed != [f"A\t{SELECTION_PATH.as_posix()}"]:
        raise _error("V3 selection commit must add only the fixed selection artifact")
    _is_ancestor(root, selection_commit, head, "selection-to-consumer")
    committed = _git(root, "show", f"{selection_commit}:{SELECTION_PATH.as_posix()}")
    at_head = _git(root, "show", f"{head}:{SELECTION_PATH.as_posix()}")
    if committed != selection_raw or at_head != selection_raw:
        raise _error("V3 selection bytes differ across selection commit, HEAD, and disk")
    run_tree = _git(root, "rev-parse", f"{run_commit}:src/bctc_ai").decode().strip()
    selection_tree = _git(root, "rev-parse", f"{selection_commit}:src/bctc_ai").decode().strip()
    head_tree = _git(root, "rev-parse", f"{head}:src/bctc_ai").decode().strip()
    if (
        run_tree != selection_tree
        or run_tree != head_tree
        or run_tree != selection["source_tree_oid"]
    ):
        raise _error("V3 source tree changed across run, selection, or replay")
    records = []
    for path in (
        _FREEZER_PATH,
        _RUNNER_PATH,
        _RECEIPT_PATH,
        _ORCHESTRATOR_PATH,
        CONFIG_PATH,
    ):
        current = _stable_bytes(root, path, f"V3 trust closure {path}")
        if any(
            _git(root, "show", f"{commit}:{path.as_posix()}") != current
            for commit in (run_commit, selection_commit, head)
        ):
            raise _error(f"V3 trust-closure blob drifted: {path}")
        records.append(_pin(path, current))
    return {
        "clean_consumer_head_validated_but_not_persisted": True,
        "consumer_head": head,
        "entrypoints": records,
        "run_commit": run_commit,
        "selection_commit": selection_commit,
        "source_tree_oid": run_tree,
    }


@dataclass(frozen=True, slots=True)
class _AuthenticatedRunStateV3:
    root: Path
    freeze: AuthenticatedVietOCRAllLineFreezeV3
    projection_payload: bytes
    batch_metadata_payload: bytes
    crop_payloads: tuple[bytes, ...]
    attempt_payload: bytes
    result_payload: bytes
    run_payload: bytes
    selection_payload: bytes
    lineage_payload: bytes
    digest: str


@dataclass(frozen=True, slots=True)
class _AuthenticatedReceiptStateV3:
    run_capability: AuthenticatedVietOCRAllLineRunV3
    projection_payload: bytes
    digest: str


def _state_digest(*payloads: bytes) -> str:
    material = bytearray()
    for payload in payloads:
        material.extend(len(payload).to_bytes(8, "big"))
        material.extend(payload)
    return _sha(bytes(material))


class AuthenticatedVietOCRAllLineRunV3:
    __slots__ = ("__weakref__",)

    def __init__(self, token: object) -> None:
        if token is not _TOKEN:
            raise _error("authenticated V3 run capabilities can only be minted by replay")

    def __copy__(self) -> Any:
        raise _error("authenticated V3 run capabilities cannot be copied")

    __deepcopy__ = __copy__

    def __reduce__(self) -> Any:
        raise pickle.PicklingError("authenticated V3 run capabilities cannot be serialized")


class AuthenticatedVietOCRSemanticReceiptV3:
    __slots__ = ("__weakref__",)

    def __init__(self, token: object) -> None:
        if token is not _TOKEN:
            raise _error("authenticated V3 semantic receipts can only be minted by replay")

    def __copy__(self) -> Any:
        raise _error("authenticated V3 semantic receipts cannot be copied")

    __deepcopy__ = __copy__

    def __reduce__(self) -> Any:
        raise pickle.PicklingError("authenticated V3 semantic receipts cannot be serialized")


_TOKEN = object()
_RUNS: weakref.WeakKeyDictionary[AuthenticatedVietOCRAllLineRunV3, _AuthenticatedRunStateV3] = (
    weakref.WeakKeyDictionary()
)
_RECEIPTS: weakref.WeakKeyDictionary[
    AuthenticatedVietOCRSemanticReceiptV3, _AuthenticatedReceiptStateV3
] = weakref.WeakKeyDictionary()


def authenticate_tracked_vietocr_all_line_run_v3(
    project_root: Path,
    freeze_capability: AuthenticatedVietOCRAllLineFreezeV3,
) -> AuthenticatedVietOCRAllLineRunV3:
    """Authenticate the fixed tracked selection and mint an opaque run handle."""

    root = _resolve_root(project_root)
    assert_authenticated_vietocr_all_line_freeze_project_root_v3(root, freeze_capability)
    projection, batch, attempt_raw, attempt, result_raw, result, run_raw, run = _load_completed_run(
        root, freeze_capability
    )
    selection_raw = _stable_bytes(root, SELECTION_PATH, "V3 tracked selection")
    selection = _validate_selection(
        _strict_json(selection_raw, "V3 tracked selection"),
        projection,
        attempt_raw,
        result_raw,
        result,
        run_raw,
        run,
    )
    lineage = _verify_selection_git(root, selection_raw, selection)
    # Final reread closes path-swap windows before capability mint.
    for path, expected, label in (
        (ATTEMPT_PATH, attempt_raw, "V3 attempt"),
        (RESULT_PATH, result_raw, "V3 OCR result"),
        (RUN_PATH, run_raw, "V3 run manifest"),
        (SELECTION_PATH, selection_raw, "V3 tracked selection"),
    ):
        if _stable_bytes(root, path, label) != expected:
            raise _error(f"{label} changed during authentication")
    replay_projection, replay_batch = read_authenticated_vietocr_all_line_snapshot_v3(
        freeze_capability
    )
    if not same_typed_json_v1(projection, replay_projection) or replay_batch != batch:
        raise _error("V3 freeze snapshot changed during run authentication")
    final_head = _clean_head(root)
    if final_head != lineage["consumer_head"]:
        raise _error("V3 consumer Git head changed during authentication")
    projection_payload = canonical_json_bytes_v1(projection)
    batch_metadata = [
        {key: value for key, value in item.items() if key != "crop_png_bytes"} for item in batch
    ]
    batch_metadata_payload = canonical_json_bytes_v1(batch_metadata)
    crop_payloads = tuple(bytes(item["crop_png_bytes"]) for item in batch)
    lineage_payload = canonical_json_bytes_v1(lineage)
    digest = _state_digest(
        projection_payload,
        batch_metadata_payload,
        *crop_payloads,
        attempt_raw,
        result_raw,
        run_raw,
        selection_raw,
        lineage_payload,
    )
    state = _AuthenticatedRunStateV3(
        root=root,
        freeze=freeze_capability,
        projection_payload=projection_payload,
        batch_metadata_payload=batch_metadata_payload,
        crop_payloads=crop_payloads,
        attempt_payload=attempt_raw,
        result_payload=result_raw,
        run_payload=run_raw,
        selection_payload=selection_raw,
        lineage_payload=lineage_payload,
        digest=digest,
    )
    capability = AuthenticatedVietOCRAllLineRunV3(_TOKEN)
    _RUNS[capability] = state
    return capability


def _run_payload(capability: AuthenticatedVietOCRAllLineRunV3) -> dict[str, Any]:
    if type(capability) is not AuthenticatedVietOCRAllLineRunV3:
        raise _error("V3 run capability is not an exact opaque handle")
    try:
        state = _RUNS[capability]
    except KeyError as exc:
        raise _error("V3 run capability is unknown or expired") from exc
    payloads = (
        state.projection_payload,
        state.batch_metadata_payload,
        *state.crop_payloads,
        state.attempt_payload,
        state.result_payload,
        state.run_payload,
        state.selection_payload,
        state.lineage_payload,
    )
    if _state_digest(*payloads) != state.digest:
        raise _error("V3 authenticated run state digest drifted")
    projection = _strict_json(state.projection_payload, "stored V3 freeze projection")
    batch_metadata = decode_canonical_json_bytes_v1(state.batch_metadata_payload)
    if type(batch_metadata) is not list or len(batch_metadata) != EXPECTED_SAMPLE_COUNT:
        raise _error("stored V3 authenticated batch drifted")
    if len(state.crop_payloads) != EXPECTED_SAMPLE_COUNT:
        raise _error("stored V3 crop payload denominator drifted")
    batch = tuple(
        {**metadata, "crop_png_bytes": bytes(crop)}
        for metadata, crop in zip(batch_metadata, state.crop_payloads, strict=True)
    )
    attempt = _strict_json(state.attempt_payload, "stored V3 attempt")
    result = _strict_json(state.result_payload, "stored V3 result")
    run = _strict_json(state.run_payload, "stored V3 run")
    selection = _strict_json(state.selection_payload, "stored V3 selection")
    lineage = _strict_json(state.lineage_payload, "stored V3 lineage")

    # Every public use replays external trust roots and exact selected bytes.
    if _stable_bytes(state.root, ATTEMPT_PATH, "V3 attempt") != state.attempt_payload:
        raise _error("V3 attempt changed after authentication")
    if _stable_bytes(state.root, RESULT_PATH, "V3 OCR result") != state.result_payload:
        raise _error("V3 result changed after authentication")
    if _stable_bytes(state.root, RUN_PATH, "V3 run manifest") != state.run_payload:
        raise _error("V3 run changed after authentication")
    if _stable_bytes(state.root, SELECTION_PATH, "V3 tracked selection") != state.selection_payload:
        raise _error("V3 selection changed after authentication")
    replay_projection, replay_batch = read_authenticated_vietocr_all_line_snapshot_v3(state.freeze)
    if not same_typed_json_v1(replay_projection, projection) or replay_batch != batch:
        raise _error("V3 freeze changed after run authentication")
    replay_lineage = _verify_selection_git(state.root, state.selection_payload, selection)
    if not same_typed_json_v1(replay_lineage, lineage):
        raise _error("V3 selection lineage changed after authentication")
    head = _clean_head(state.root)
    if head != replay_lineage["consumer_head"]:
        raise _error("V3 consumer Git head changed during capability replay")
    return {
        "batch": batch,
        "freeze": state.freeze,
        "lineage": lineage,
        "projection": projection,
        "attempt": attempt,
        "result": result,
        "run": run,
        "selection": selection,
    }


def _receipt_projection(payload: dict[str, Any]) -> dict[str, Any]:
    material = {
        "authority": _SAFETY_RECEIPT,
        "claim_boundary": CLAIM_BOUNDARY,
        "experiment_id": EXPERIMENT_ID,
        "format_version": RECEIPT_FORMAT_VERSION,
        "freeze_id": payload["projection"]["freeze_id"],
        "line_count_vector": list(EXPECTED_LINE_COUNT_VECTOR),
        "page_count": 8,
        "result_id": payload["result"]["result_id"],
        "run_id": payload["run"]["run_id"],
        "sample_count": EXPECTED_SAMPLE_COUNT,
        "selection_id": payload["selection"]["selection_id"],
        "state": RECEIPT_STATE,
    }
    return {**material, "receipt_id": f"voalsrv3:receipt:{canonical_json_sha256_v1(material)}"}


def build_authenticated_vietocr_semantic_receipt_v3(
    run_capability: AuthenticatedVietOCRAllLineRunV3,
) -> AuthenticatedVietOCRSemanticReceiptV3:
    payload = _run_payload(run_capability)
    projection_payload = canonical_json_bytes_v1(_receipt_projection(payload))
    receipt = AuthenticatedVietOCRSemanticReceiptV3(_TOKEN)
    _RECEIPTS[receipt] = _AuthenticatedReceiptStateV3(
        run_capability=run_capability,
        projection_payload=projection_payload,
        digest=_sha(projection_payload),
    )
    return receipt


def _receipt_payload(capability: AuthenticatedVietOCRSemanticReceiptV3) -> dict[str, Any]:
    if type(capability) is not AuthenticatedVietOCRSemanticReceiptV3:
        raise _error("V3 semantic receipt is not an exact opaque handle")
    try:
        state = _RECEIPTS[capability]
    except KeyError as exc:
        raise _error("V3 semantic receipt is unknown or expired") from exc
    if _sha(state.projection_payload) != state.digest:
        raise _error("V3 semantic receipt state digest drifted")
    projection = _strict_json(state.projection_payload, "stored V3 receipt projection")
    run = _run_payload(state.run_capability)
    if not same_typed_json_v1(projection, _receipt_projection(run)):
        raise _error("V3 semantic receipt projection drifted")
    return {"run_capability": state.run_capability, "projection": projection}


def project_authenticated_vietocr_semantic_receipt_v3(
    receipt_capability: AuthenticatedVietOCRSemanticReceiptV3,
) -> dict[str, Any]:
    return canonical_clone_v1(_receipt_payload(receipt_capability)["projection"])


def read_authenticated_vietocr_semantic_proposals_v3(
    receipt_capability: AuthenticatedVietOCRSemanticReceiptV3,
) -> tuple[dict[str, Any], ...]:
    payload = _receipt_payload(receipt_capability)
    run = _run_payload(payload["run_capability"])
    proposals = []
    for item in run["result"]["samples"]:
        match = _SAMPLE.fullmatch(item["sample_id"])
        if match is None:
            raise _error("V3 semantic sample ID drifted")
        proposals.append(
            {
                "crop_sha256": item["crop_sha256"],
                "line_index": int(match.group(2)),
                "mean_decoded_character_probability": item["mean_decoded_character_probability"],
                "normalized_prediction": unicodedata.normalize("NFC", item["raw_prediction"]),
                "page_id": item["page_id"],
                "processed_height": item["processed_height"],
                "processed_width": item["processed_width"],
                "raw_prediction": item["raw_prediction"],
                "sample_id": item["sample_id"],
            }
        )
    return tuple(proposals)


def read_authenticated_vietocr_semantic_page_v3(
    receipt_capability: AuthenticatedVietOCRSemanticReceiptV3,
    page_ordinal: int,
) -> tuple[dict[str, Any], ...]:
    if type(page_ordinal) is not int or not 1 <= page_ordinal <= 8:
        raise _error("V3 semantic page ordinal must be one integer from 1 through 8")
    page_id = f"page-{page_ordinal:04d}"
    records = tuple(
        item
        for item in read_authenticated_vietocr_semantic_proposals_v3(receipt_capability)
        if item["page_id"] == page_id
    )
    if len(records) != EXPECTED_LINE_COUNT_VECTOR[page_ordinal - 1]:
        raise _error("V3 semantic page denominator drifted")
    return records
