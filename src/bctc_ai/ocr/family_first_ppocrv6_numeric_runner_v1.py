"""One reference-blind PP-OCRv6 recognition cache over all detected lines."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bctc_ai.evaluation import family_first_semantic_label_archive_v1 as archive_v1
from bctc_ai.ocr import family_first_vietocr_runner_v1 as file_ops_v1
from bctc_ai.ocr import ppocrv6_numeric_reference_blind_kernel_v1 as kernel_v1
from bctc_ai.ocr import vietocr_all_line_runner_v3 as runtime_v3
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "RUN_ROOT",
    "FamilyFirstPPocrV6NumericRunnerV1Error",
    "run_authenticated_family_first_ppocrv6_numeric_v1",
]


RUN_ROOT = Path("output/calibration/family-first-ppocrv6-numeric-cache-v1/fresh-run")
EXPERIMENT_ID = "FAMILY_FIRST_ALL_FILING_PPOCRV6_NUMERIC_CACHE_V1"
ATTEMPT_FORMAT_VERSION = "FAMILY_FIRST_PPOCRV6_NUMERIC_ATTEMPT_V1"
PROPOSAL_FORMAT_VERSION = "FAMILY_FIRST_PPOCRV6_NUMERIC_PROPOSAL_V1"
RUN_FORMAT_VERSION = "FAMILY_FIRST_PPOCRV6_NUMERIC_RUN_MANIFEST_V1"
_ATTEMPT_NAME = "attempt.json"
_INCOMPLETE_NAME = "numeric-proposals.jsonl.incomplete"
_PROPOSAL_NAME = "numeric-proposals.jsonl"
_RUN_NAME = "run_manifest.json"
_CONFIG_PATH = Path("config/models/family-first-ocr-runtime-v1.toml")
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
        "src/bctc_ai/evaluation/family_first_numeric_cell_evidence_v1.py",
        "src/bctc_ai/evaluation/family_first_ppocrv6_numeric_index_v1.py",
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
        "src/bctc_ai/ocr/family_first_ppocrv6_numeric_runner_v1.py",
        "src/bctc_ai/ocr/family_first_vietocr_runner_v1.py",
        "src/bctc_ai/ocr/native_text_quality_v2.py",
        "src/bctc_ai/ocr/pdf_text.py",
        "src/bctc_ai/ocr/ppocrv6_numeric_reference_blind_kernel_v1.py",
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
        "scripts/experiments/run_family_first_ppocrv6_numeric_v1.py",
        "config/models/family-first-ocr-runtime-v1.toml",
    )
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_RESULT_FIELDS = {
    "crop_sha256",
    "format_version",
    "raw_prediction",
    "reader_score",
    "sample_id",
}
_EXECUTION_POLICY = {
    "accounting_equation_available_to_reader": False,
    "bank_file_page_period_scope_available_to_reader": False,
    "batch_size": 64,
    "cpu_threads": 16,
    "device": "cpu",
    "expected_value_available_to_reader": False,
    "family_or_schema_available_to_reader": False,
    "geometry_available_to_reader": False,
    "label_or_owner_available_to_reader": False,
    "mkldnn": False,
    "network_permitted": False,
    "precision": "fp32",
    "prior_output_access": False,
    "resume": False,
}
_SAFETY = {
    "accounting_authority": False,
    "automatic_digit_repair": False,
    "automatic_truth_promotion": False,
    "blank_token_means_zero": False,
    "dash_token_may_be_parsed_as_zero_by_later_typed_evidence": True,
    "geometry_authority": False,
    "mapping_authority": False,
    "numeric_recognition_proposal_only": True,
    "period_or_unit_authority": False,
    "schema_authority": False,
    "semantic_text_authority": False,
}


class FamilyFirstPPocrV6NumericRunnerV1Error(RuntimeError):
    """The fixed all-filing numeric proposal attempt cannot be established."""


def _error(message: str) -> FamilyFirstPPocrV6NumericRunnerV1Error:
    return FamilyFirstPPocrV6NumericRunnerV1Error(message)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _git_binding(root: Path) -> dict[str, Any]:
    if runtime_v3._git(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise _error("formal PP-OCRv6 numeric run requires one clean Git worktree")
    commit = runtime_v3._git(root, "rev-parse", "HEAD").decode("ascii").strip()
    tree = runtime_v3._git(root, "rev-parse", "HEAD:src/bctc_ai").decode("ascii").strip()
    if _COMMIT.fullmatch(commit) is None or _COMMIT.fullmatch(tree) is None:
        raise _error("formal PP-OCRv6 numeric Git identity is malformed")
    return {
        "commit": commit,
        "dirty": False,
        "implementation_refs": [
            runtime_v3._tracked_ref(root, path, f"numeric trust file {path}")
            for path in _TRUST_PATHS
        ],
        "source_tree_oid": tree,
    }


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
        file_ops_v1._write_exclusive(run_fd, _ATTEMPT_NAME, attempt_payload)
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
        raise _error("formal PP-OCRv6 numeric run root changed during attempt creation")
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
        or type(value.get("raw_prediction")) is not str
    ):
        raise _error("formal PP-OCRv6 numeric proposal fields drifted")
    score = value.get("reader_score")
    if type(score) is not float or not math.isfinite(score) or not 0 <= score <= 1:
        raise _error("formal PP-OCRv6 numeric proposal score drifted")
    result = canonical_clone_v1(value)
    result["format_version"] = PROPOSAL_FORMAT_VERSION
    if set(result) != _RESULT_FIELDS:
        raise _error("formal PP-OCRv6 numeric proposal closed schema drifted")
    return result


def _readback_jsonl(descriptor: int, expected_count: int) -> tuple[str, int, int]:
    os.lseek(descriptor, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    buffer = b""
    count = 0
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
                raise _error("formal PP-OCRv6 numeric JSONL readback is invalid") from exc
            proposal = _validate_result(value, count)
            if line + b"\n" != canonical_json_bytes_v1(proposal):
                raise _error("formal PP-OCRv6 numeric JSONL line is not canonical")
            empty_count += proposal["raw_prediction"] == ""
    if buffer or count != expected_count:
        raise _error("formal PP-OCRv6 numeric JSONL denominator/trailing bytes drifted")
    return digest.hexdigest(), total_size, empty_count


def _validate_kernel_outputs(
    runtime: Any,
    counts: Any,
    metrics: Any,
    *,
    sample_count: int,
) -> tuple[dict[str, Any], dict[str, int], dict[str, float]]:
    expected_counts = {
        "formal_run_count": 1,
        "model_build_count": 1,
        "reader_chunk_call_count": (sample_count + 4095) // 4096 + 1,
        "recognizer_predict_call_count": (sample_count + 63) // 64,
        "result_count": sample_count,
    }
    if type(counts) is not dict or not same_typed_json_v1(counts, expected_counts):
        raise _error("formal PP-OCRv6 numeric execution counts drifted")
    if (
        type(runtime) is not dict
        or set(runtime) != {"device", "model", "packages", "precision"}
        or runtime["device"] != "cpu"
        or runtime["precision"] != "fp32"
        or not same_typed_json_v1(
            runtime["packages"], {"paddleocr": "3.7.0", "paddlepaddle": "3.3.0"}
        )
        or type(runtime["model"]) is not dict
    ):
        raise _error("formal PP-OCRv6 numeric runtime evidence drifted")
    if (
        type(metrics) is not dict
        or set(metrics) != {"model_load_seconds", "total_wall_seconds"}
        or any(
            type(value) is not float or not math.isfinite(value) or value < 0
            for value in metrics.values()
        )
        or metrics["total_wall_seconds"] < metrics["model_load_seconds"]
    ):
        raise _error("formal PP-OCRv6 numeric runtime metrics drifted")
    return canonical_clone_v1(runtime), canonical_clone_v1(counts), canonical_clone_v1(metrics)


def run_authenticated_family_first_ppocrv6_numeric_v1(
    project_root: Path,
    archive_capability: archive_v1.AuthenticatedFamilyFirstSemanticLabelArchiveV1,
    *,
    model_cache: Path,
) -> dict[str, Any]:
    """Execute the fixed all-line numeric recognizer proposal cache once."""

    root = runtime_v3._resolve_root(project_root)
    if not isinstance(model_cache, Path):
        raise _error("formal PP-OCRv6 model cache must be one pathlib Path")
    if os.path.lexists(root / RUN_ROOT):
        raise _error("formal PP-OCRv6 numeric root exists; resume is forbidden")
    git_before = _git_binding(root)
    configuration_payload = runtime_v3._stable_bytes(root / _CONFIG_PATH, "numeric runtime config")
    model_projection, _model_directory = kernel_v1._recognizer_projection(root, model_cache)
    projection, reader_session = (
        archive_v1.open_authenticated_family_first_semantic_label_reader_snapshot_v1(
            root, archive_capability
        )
    )
    preflight = {
        "archive_id": projection["archive_id"],
        "batch_id": projection["batch_id"],
        "configuration_ref": {
            "path": _CONFIG_PATH.as_posix(),
            "sha256": _sha(configuration_payload),
            "size_bytes": len(configuration_payload),
        },
        "execution_policy": canonical_clone_v1(_EXECUTION_POLICY),
        "experiment_id": EXPERIMENT_ID,
        "git_binding": git_before,
        "model": model_projection,
        "plan_id": projection["plan_id"],
        "sample_count": projection["sample_count"],
    }
    attempt_id = "ffpnrv1:attempt:" + canonical_json_sha256_v1(preflight)
    started_at = datetime.now(UTC).isoformat()
    attempt = {
        "attempt_id": attempt_id,
        "claim_boundary": "REFERENCE_BLIND_NUMERIC_PROPOSAL_ATTEMPT_NO_RESUME",
        "format_version": ATTEMPT_FORMAT_VERSION,
        "preflight": preflight,
        "started_at": started_at,
        "state": "FORMAL_ATTEMPT_STARTED_NO_RESUME",
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
            file_ops_v1._write_all(proposal_fd, canonical_json_bytes_v1(proposal))
            emitted += 1

        runtime, counts, metrics = (
            kernel_v1.execute_authenticated_ppocrv6_numeric_reference_blind_v1(
                root,
                reader_session,
                expected_sample_count=projection["sample_count"],
                model_cache=model_cache,
                result_sink=sink,
                batch_size=_EXECUTION_POLICY["batch_size"],
                cpu_threads=_EXECUTION_POLICY["cpu_threads"],
            )
        )
        runtime, counts, metrics = _validate_kernel_outputs(
            runtime, counts, metrics, sample_count=projection["sample_count"]
        )
        os.fsync(proposal_fd)
        proposal_sha, proposal_size, empty_count = _readback_jsonl(
            proposal_fd, projection["sample_count"]
        )
        if emitted != projection["sample_count"]:
            raise _error("formal PP-OCRv6 numeric sink denominator drifted")
        live_model, _directory = kernel_v1._recognizer_projection(root, model_cache)
        if (
            live_model != model_projection
            or runtime_v3._stable_bytes(root / _CONFIG_PATH, "numeric runtime config")
            != configuration_payload
            or _git_binding(root) != git_before
        ):
            raise _error("formal PP-OCRv6 numeric code/config/model/Git drifted")
        file_ops_v1._rename_noreplace_fd(run_fd, _INCOMPLETE_NAME, _PROPOSAL_NAME)
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
        run_material = {
            "artifacts": {"attempt": attempt_ref, "numeric_proposals": proposal_ref},
            "attempt_id": attempt_id,
            "completed_at": datetime.now(UTC).isoformat(),
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
            "metrics": {**metrics, "empty_prediction_count": empty_count, "sample_count": emitted},
            "runtime": runtime,
            "safety": canonical_clone_v1(_SAFETY),
            "started_at": started_at,
            "state": "REFERENCE_BLIND_PPOCRV6_NUMERIC_PROPOSAL_RUN_COMPLETE",
        }
        manifest = {
            **run_material,
            "run_id": "ffpnrv1:run:" + canonical_json_sha256_v1(run_material),
        }
        manifest_payload = canonical_json_bytes_v1(manifest)
        file_ops_v1._write_exclusive(run_fd, _RUN_NAME, manifest_payload)
        os.fsync(run_fd)
        named = os.stat(RUN_ROOT.name, dir_fd=parent_fd, follow_symlinks=False)
        if (named.st_dev, named.st_ino) != run_identity:
            raise _error("official PP-OCRv6 numeric run root changed during inference")
        if sorted(os.listdir(run_fd)) != sorted([_ATTEMPT_NAME, _PROPOSAL_NAME, _RUN_NAME]):
            raise _error("formal PP-OCRv6 numeric output listing drifted")
        persisted = json.loads(
            runtime_v3._read_fd_bytes(run_fd, _RUN_NAME).decode("utf-8", errors="strict")
        )
        if not same_typed_json_v1(persisted, manifest):
            raise _error("formal PP-OCRv6 numeric manifest readback drifted")
        return canonical_clone_v1(manifest)
    finally:
        if proposal_fd >= 0:
            os.close(proposal_fd)
        os.close(run_fd)
        os.close(parent_fd)
