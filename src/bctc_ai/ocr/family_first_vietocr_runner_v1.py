"""One fresh reference-blind VietOCR run over the all-filing semantic archive."""

from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import math
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.family_first_semantic_label_archive_v1 import (
    AuthenticatedFamilyFirstSemanticLabelArchiveV1,
    open_authenticated_family_first_semantic_label_reader_snapshot_v1,
)
from bctc_ai.ocr import vietocr_all_line_runner_v3 as runtime_v3
from bctc_ai.ocr.vietocr_reference_blind_kernel_v1 import (
    execute_authenticated_vietocr_reference_blind_v1,
    preflight_authenticated_vietocr_runtime_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "CONFIG_PATH",
    "RUN_ROOT",
    "FamilyFirstVietOCRRunnerV1Error",
    "run_authenticated_family_first_vietocr_v1",
]


CONFIG_PATH = runtime_v3.CONFIG_PATH
RUN_ROOT = Path("output/calibration/family-first-vietocr-semantic-cache-v1/fresh-run")
EXPERIMENT_ID = "FAMILY_FIRST_ALL_FILING_VIETOCR_SEMANTIC_CACHE_V1"
ATTEMPT_FORMAT_VERSION = "FAMILY_FIRST_VIETOCR_ATTEMPT_V1"
PROPOSAL_FORMAT_VERSION = "FAMILY_FIRST_VIETOCR_SEMANTIC_PROPOSAL_V1"
RUN_FORMAT_VERSION = "FAMILY_FIRST_VIETOCR_RUN_MANIFEST_V1"
_ATTEMPT_NAME = "attempt.json"
_INCOMPLETE_NAME = "semantic-proposals.jsonl.incomplete"
_PROPOSAL_NAME = "semantic-proposals.jsonl"
_RUN_NAME = "run_manifest.json"
_TRUST_PATHS = tuple(
    Path(value)
    for value in (
        "src/bctc_ai/core/contracts.py",
        "src/bctc_ai/core/coordinates.py",
        "src/bctc_ai/core/hashing.py",
        "src/bctc_ai/core/text.py",
        "src/bctc_ai/corpus/__init__.py",
        "src/bctc_ai/corpus/wave1_pre_ocr_structure.py",
        "src/bctc_ai/corpus/wave1_role_b_full_reader_v3.py",
        "src/bctc_ai/corpus/wave1_role_b_page_reader.py",
        "src/bctc_ai/corpus/wave1_role_b_sentinel.py",
        "src/bctc_ai/corpus/wave1_role_b_word_box_normalization.py",
        "src/bctc_ai/evaluation/__init__.py",
        "src/bctc_ai/evaluation/authenticated_line_pixel_hydration_v1.py",
        "src/bctc_ai/evaluation/family_first_filing_inventory_v1.py",
        "src/bctc_ai/evaluation/family_first_semantic_index_v1.py",
        "src/bctc_ai/evaluation/family_first_semantic_label_archive_v1.py",
        "src/bctc_ai/evaluation/family_first_semantic_label_freeze_v1.py",
        "src/bctc_ai/evaluation/family_first_semantic_label_plan_v1.py",
        "src/bctc_ai/evaluation/loan_maturity_8bank_panel_prerequisite_v1.py",
        "src/bctc_ai/evaluation/loan_maturity_8bank_ready_panel_v1.py",
        "src/bctc_ai/evaluation/vietocr_all_line_freezer_v3.py",
        "src/bctc_ai/ocr/__init__.py",
        "src/bctc_ai/ocr/_causal_visibility_core.py",
        "src/bctc_ai/ocr/causal_native_text.py",
        "src/bctc_ai/ocr/causal_native_text_evidence_v1.py",
        "src/bctc_ai/ocr/causal_native_text_evidence_v2.py",
        "src/bctc_ai/ocr/family_first_vietocr_runner_v1.py",
        "src/bctc_ai/ocr/native_text_quality_v2.py",
        "src/bctc_ai/ocr/pdf_text.py",
        "src/bctc_ai/ocr/ppocrv6_page_session.py",
        "src/bctc_ai/ocr/vietocr_all_line_runner_v3.py",
        "src/bctc_ai/ocr/vietocr_reference_blind_kernel_v1.py",
        "src/bctc_ai/rendering/page_reader.py",
        "src/bctc_ai/source_structure/__init__.py",
        "src/bctc_ai/source_structure/contracts_v1.py",
        "src/bctc_ai/source_structure/contracts_v2.py",
        "src/bctc_ai/source_structure/evidence_projection_v1.py",
        "src/bctc_ai/source_structure/evidence_projection_v2.py",
        "src/bctc_ai/source_structure/finalized_v3_survey_stream_v1.py",
        "scripts/experiments/run_family_first_vietocr_v1.py",
        "config/models/vietocr-0.3.13-vgg-transformer-all-line-v3.toml",
    )
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_RENAME_NOREPLACE = 1
_RESULT_FIELDS = {
    "crop_sha256",
    "format_version",
    "mean_decoded_character_probability",
    "processed_height",
    "processed_width",
    "raw_prediction",
    "sample_id",
}
_EXECUTION_POLICY = {
    "amp": False,
    "autocast": False,
    "backend": "PYTORCH_EAGER",
    "beam_search": False,
    "bf16": False,
    "cnn_pretrained_download": False,
    "fp16": False,
    "history_access": False,
    "human_review_access": False,
    "network_permitted": False,
    "onnx": False,
    "post_correction": False,
    "precision": "FP32",
    "prior_outputs": False,
    "reference_text_available_to_decoder": False,
    "resume": False,
    "retry_from_output": False,
    "tf32": False,
    "template_access": False,
    "torch_compile": False,
    "torchscript": False,
    "truth_access": False,
}
_SAFETY = {
    "accounting_authority": False,
    "automatic_post_correction": False,
    "automatic_truth_promotion": False,
    "bank_file_page_period_scope_available_to_reader": False,
    "geometry_authority": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "period_authority": False,
    "reference_text_available_to_reader": False,
    "report_norm_id_authority": False,
    "schema_authority": False,
    "scope_authority": False,
    "semantic_acceptance": False,
    "sign_authority": False,
    "unit_authority": False,
}


class FamilyFirstVietOCRRunnerV1Error(RuntimeError):
    """The fixed all-filing semantic proposal attempt cannot be established."""


def _error(message: str) -> FamilyFirstVietOCRRunnerV1Error:
    return FamilyFirstVietOCRRunnerV1Error(message)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _git_binding(root: Path) -> dict[str, Any]:
    status = runtime_v3._git(root, "status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise _error("formal family-first VietOCR requires one clean Git worktree")
    commit = runtime_v3._git(root, "rev-parse", "HEAD").decode("ascii").strip()
    tree = runtime_v3._git(root, "rev-parse", "HEAD:src/bctc_ai").decode("ascii").strip()
    if _COMMIT.fullmatch(commit) is None or _COMMIT.fullmatch(tree) is None:
        raise _error("formal family-first VietOCR Git identity is malformed")
    return {
        "commit": commit,
        "dirty": False,
        "implementation_refs": [
            runtime_v3._tracked_ref(root, path, f"family-first VietOCR trust file {path}")
            for path in _TRUST_PATHS
        ],
        "source_tree_oid": tree,
    }


def _write_all(descriptor: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        count = os.write(descriptor, view)
        if count <= 0:
            raise _error("formal VietOCR artifact write made no progress")
        view = view[count:]


def _write_exclusive(directory_fd: int, name: str, payload: bytes) -> None:
    descriptor = os.open(
        name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o444,
        dir_fd=directory_fd,
    )
    try:
        _write_all(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _rename_noreplace_fd(directory_fd: int, source: str, destination: str) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise _error("renameat2 is required for no-replace formal result publication")
    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    if (
        renameat2(
            directory_fd,
            os.fsencode(source),
            directory_fd,
            os.fsencode(destination),
            _RENAME_NOREPLACE,
        )
        != 0
    ):
        number = ctypes.get_errno()
        if number == errno.EEXIST:
            raise _error("formal VietOCR result appeared before no-replace publication")
        raise OSError(number, os.strerror(number), destination)
    os.fsync(directory_fd)


def _create_attempt_root(root: Path, attempt_payload: bytes) -> tuple[int, int, tuple[int, int]]:
    calibration = root / "output/calibration"
    if not calibration.is_dir() or calibration.is_symlink():
        raise _error("fixed output/calibration root is unsafe")
    calibration_fd = os.open(calibration, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        try:
            os.mkdir(RUN_ROOT.parent.name, 0o700, dir_fd=calibration_fd)
            os.fsync(calibration_fd)
        except FileExistsError:
            pass
        parent_fd = os.open(
            RUN_ROOT.parent.name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=calibration_fd,
        )
    finally:
        os.close(calibration_fd)
    try:
        os.mkdir(RUN_ROOT.name, 0o700, dir_fd=parent_fd)
        run_fd = os.open(
            RUN_ROOT.name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=parent_fd,
        )
        os.fsync(parent_fd)
    except BaseException:
        os.close(parent_fd)
        raise
    try:
        _write_exclusive(run_fd, _ATTEMPT_NAME, attempt_payload)
        os.fsync(run_fd)
    except BaseException:
        os.close(run_fd)
        os.close(parent_fd)
        raise
    opened = os.fstat(run_fd)
    identity = (opened.st_dev, opened.st_ino)
    named = os.stat(RUN_ROOT.name, dir_fd=parent_fd, follow_symlinks=False)
    if (named.st_dev, named.st_ino) != identity:
        os.close(run_fd)
        os.close(parent_fd)
        raise _error("formal family-first VietOCR run root changed during attempt creation")
    return run_fd, parent_fd, identity


def _validate_result(value: Any, expected_ordinal: int) -> dict[str, Any]:
    observed_fields = set(value) if type(value) is dict else set()
    if (
        type(value) is not dict
        or observed_fields not in (_RESULT_FIELDS, _RESULT_FIELDS - {"format_version"})
        or ("format_version" in value and value["format_version"] != PROPOSAL_FORMAT_VERSION)
        or value.get("sample_id") != f"sample-{expected_ordinal:09d}"
        or type(value.get("crop_sha256")) is not str
        or _SHA256.fullmatch(value["crop_sha256"]) is None
        or type(value.get("processed_width")) is not int
        or value["processed_width"] <= 0
        or type(value.get("processed_height")) is not int
        or value["processed_height"] <= 0
        or type(value.get("raw_prediction")) is not str
    ):
        raise _error("formal family-first VietOCR proposal fields drifted")
    probability = value.get("mean_decoded_character_probability")
    if probability is not None and (
        type(probability) is not float
        or not math.isfinite(probability)
        or not 0.0 <= probability <= 1.0
    ):
        raise _error("formal family-first VietOCR proposal probability drifted")
    result = canonical_clone_v1(value)
    result["format_version"] = PROPOSAL_FORMAT_VERSION
    if set(result) != _RESULT_FIELDS:
        raise _error("formal family-first VietOCR proposal closed schema drifted")
    return result


def _readback_jsonl(descriptor: int, expected_count: int) -> tuple[str, int, int, int]:
    os.lseek(descriptor, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    buffer = b""
    count = 0
    null_count = 0
    empty_count = 0
    total_size = 0
    while chunk := os.read(descriptor, 1024 * 1024):
        digest.update(chunk)
        total_size += len(chunk)
        buffer += chunk
        lines = buffer.split(b"\n")
        buffer = lines.pop()
        for line in lines:
            count += 1
            try:
                value = json.loads(line.decode("utf-8", errors="strict"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _error("formal VietOCR proposal JSONL readback is invalid") from exc
            proposal = _validate_result(value, count)
            if line + b"\n" != canonical_json_bytes_v1(proposal):
                raise _error("formal VietOCR proposal JSONL line is not canonical")
            null_count += proposal["mean_decoded_character_probability"] is None
            empty_count += proposal["raw_prediction"] == ""
    if buffer or count != expected_count:
        raise _error("formal VietOCR proposal JSONL denominator/trailing bytes drifted")
    return digest.hexdigest(), total_size, null_count, empty_count


def _validate_kernel_outputs(
    runtime: Any,
    counts: Any,
    metrics: Any,
    *,
    sample_count: int,
) -> tuple[dict[str, Any], dict[str, int], dict[str, float]]:
    expected_counts = {
        "checkpoint_deserialization_count": 1,
        "formal_run_count": 1,
        "model_build_count": 1,
        "process_input_count": sample_count,
        "reader_chunk_call_count": (sample_count + 255) // 256 + 1,
        "result_count": sample_count,
        "state_dict_load_count": 1,
        "translate_call_count": sample_count,
    }
    if (
        type(counts) is not dict
        or not same_typed_json_v1(counts, expected_counts)
        or any(type(value) is not int for value in counts.values())
    ):
        raise _error("formal family-first VietOCR execution counts drifted")
    expected_runtime_fields = {
        "compute_capability",
        "cuda_runtime",
        "device_name",
        "packages",
        "python_major_minor",
        "runtime_root",
    }
    if (
        type(runtime) is not dict
        or set(runtime) != expected_runtime_fields
        or runtime["compute_capability"] != "8.9"
        or runtime["cuda_runtime"] != "13.0"
        or runtime["device_name"] != "NVIDIA GeForce RTX 4090"
        or not same_typed_json_v1(runtime["packages"], runtime_v3._EXPECTED_PACKAGES)
        or runtime["python_major_minor"] != "3.11"
        or runtime["runtime_root"] != runtime_v3.RUNTIME_ROOT.as_posix()
    ):
        raise _error("formal family-first VietOCR runtime evidence drifted")
    metric_fields = {
        "model_load_seconds",
        "peak_gpu_memory_allocated_mib",
        "peak_gpu_memory_reserved_mib",
        "total_wall_seconds",
    }
    if (
        type(metrics) is not dict
        or set(metrics) != metric_fields
        or any(
            type(value) is not float or not math.isfinite(value) or value < 0.0
            for value in metrics.values()
        )
    ):
        raise _error("formal family-first VietOCR runtime metrics drifted")
    return canonical_clone_v1(runtime), canonical_clone_v1(counts), canonical_clone_v1(metrics)


def run_authenticated_family_first_vietocr_v1(
    project_root: Path,
    archive_capability: AuthenticatedFamilyFirstSemanticLabelArchiveV1,
) -> dict[str, Any]:
    """Execute the single fixed all-filing VGG Transformer attempt."""

    root = runtime_v3._resolve_root(project_root)
    if os.path.lexists(root / RUN_ROOT):
        raise _error("formal family-first VietOCR root exists; resume/retry is forbidden")
    git_before = _git_binding(root)
    config_payload = runtime_v3._stable_bytes(root / CONFIG_PATH, "pinned VietOCR configuration")
    preflight_runtime = preflight_authenticated_vietocr_runtime_v1(config_payload)
    projection, reader_session = open_authenticated_family_first_semantic_label_reader_snapshot_v1(
        root, archive_capability
    )
    preflight = {
        "archive_id": projection["archive_id"],
        "batch_id": projection["batch_id"],
        "configuration_ref": {
            "path": CONFIG_PATH.as_posix(),
            "sha256": _sha(config_payload),
            "size_bytes": len(config_payload),
        },
        "execution_policy": canonical_clone_v1(_EXECUTION_POLICY),
        "experiment_id": EXPERIMENT_ID,
        "git_binding": git_before,
        "plan_id": projection["plan_id"],
        "runtime_artifacts": preflight_runtime["runtime_artifacts"],
        "sample_count": projection["sample_count"],
    }
    attempt_id = "ffvocrv1:attempt:" + canonical_json_sha256_v1(preflight)
    started_at = datetime.now(UTC).isoformat()
    attempt = {
        "attempt_id": attempt_id,
        "claim_boundary": "ONE_REFERENCE_BLIND_SEMANTIC_PROPOSAL_ATTEMPT_NO_RESUME_OR_RETRY",
        "format_version": ATTEMPT_FORMAT_VERSION,
        "preflight": preflight,
        "started_at": started_at,
        "state": "FORMAL_ATTEMPT_STARTED_NO_RESUME_OR_RETRY",
    }
    attempt_payload = canonical_json_bytes_v1(attempt)
    run_fd, parent_fd, run_identity = _create_attempt_root(root, attempt_payload)
    proposal_fd = -1
    try:
        proposal_fd = os.open(
            _INCOMPLETE_NAME,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o400,
            dir_fd=run_fd,
        )
        emitted = 0

        def sink(raw: dict[str, Any]) -> None:
            nonlocal emitted
            proposal = _validate_result(raw, emitted + 1)
            _write_all(proposal_fd, canonical_json_bytes_v1(proposal))
            emitted += 1

        runtime, counts, metrics = execute_authenticated_vietocr_reference_blind_v1(
            root,
            reader_session,
            expected_sample_count=projection["sample_count"],
            config=preflight_runtime["configuration"],
            runtime_snapshots=preflight_runtime["snapshots"],
            result_sink=sink,
        )
        runtime, counts, metrics = _validate_kernel_outputs(
            runtime, counts, metrics, sample_count=projection["sample_count"]
        )
        os.fsync(proposal_fd)
        proposal_sha, proposal_size, null_count, empty_count = _readback_jsonl(
            proposal_fd, projection["sample_count"]
        )
        if emitted != projection["sample_count"] or counts["result_count"] != emitted:
            raise _error("formal VietOCR sink/model denominators drifted")
        current_runtime = preflight_authenticated_vietocr_runtime_v1(config_payload)
        if (
            current_runtime["snapshots"] != preflight_runtime["snapshots"]
            or current_runtime["runtime_artifacts"] != preflight_runtime["runtime_artifacts"]
            or runtime_v3._stable_bytes(root / CONFIG_PATH, "pinned VietOCR configuration")
            != config_payload
            or _git_binding(root) != git_before
        ):
            raise _error("formal VietOCR code/config/runtime/Git drifted during inference")
        _rename_noreplace_fd(run_fd, _INCOMPLETE_NAME, _PROPOSAL_NAME)
        proposal_ref = {
            "path": f"{RUN_ROOT.as_posix()}/{_PROPOSAL_NAME}",
            "sha256": proposal_sha,
            "size_bytes": proposal_size,
        }
        attempt_ref = {
            "path": f"{RUN_ROOT.as_posix()}/{_ATTEMPT_NAME}",
            "sha256": _sha(attempt_payload),
            "size_bytes": len(attempt_payload),
        }
        completed_at = datetime.now(UTC).isoformat()
        run_material = {
            "artifacts": {"attempt": attempt_ref, "semantic_proposals": proposal_ref},
            "attempt_id": attempt_id,
            "completed_at": completed_at,
            "execution_counts": counts,
            "execution_policy": canonical_clone_v1(_EXECUTION_POLICY),
            "experiment_id": EXPERIMENT_ID,
            "format_version": RUN_FORMAT_VERSION,
            "git_binding": git_before,
            "input": {
                "archive_id": projection["archive_id"],
                "batch_id": projection["batch_id"],
                "plan_id": projection["plan_id"],
                "sample_count": projection["sample_count"],
            },
            "metrics": {
                **metrics,
                "empty_prediction_count": empty_count,
                "null_probability_count": null_count,
                "sample_count": emitted,
            },
            "runtime": {
                **runtime,
                "artifacts": preflight_runtime["runtime_artifacts"],
            },
            "safety": canonical_clone_v1(_SAFETY),
            "started_at": started_at,
            "state": "REFERENCE_BLIND_SEMANTIC_PROPOSAL_RUN_COMPLETE",
        }
        run_id = "ffvocrv1:run:" + canonical_json_sha256_v1(run_material)
        manifest = {**run_material, "run_id": run_id}
        manifest_payload = canonical_json_bytes_v1(manifest)
        _write_exclusive(run_fd, _RUN_NAME, manifest_payload)
        os.fsync(run_fd)
        named = os.stat(RUN_ROOT.name, dir_fd=parent_fd, follow_symlinks=False)
        if (named.st_dev, named.st_ino) != run_identity:
            raise _error("official family-first VietOCR run root changed during inference")
        if sorted(os.listdir(run_fd)) != sorted([_ATTEMPT_NAME, _PROPOSAL_NAME, _RUN_NAME]):
            raise _error("formal family-first VietOCR output listing drifted")
        persisted_manifest = json.loads(
            runtime_v3._read_fd_bytes(run_fd, _RUN_NAME).decode("utf-8", errors="strict")
        )
        if not same_typed_json_v1(persisted_manifest, manifest):
            raise _error("formal family-first VietOCR manifest readback drifted")
        return canonical_clone_v1(manifest)
    finally:
        if proposal_fd >= 0:
            os.close(proposal_fd)
        os.close(run_fd)
        os.close(parent_fd)
