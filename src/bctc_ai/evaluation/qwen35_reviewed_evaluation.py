from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import subprocess
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.hashing import sha256_file
from bctc_ai.evaluation.line_recognition_metrics import score_reader
from bctc_ai.ocr.logical_row_label_reader_contract import (
    LogicalRowLabelReaderContractError,
    validate_logical_row_label_reader_request,
)


class Qwen35ReviewedEvaluationError(RuntimeError):
    """Raised when the sealed Qwen challenger cannot be reviewed safely."""


_CANONICAL_CONTROL = Path("config/experiments/e0036-qwen-reviewed-evaluation.yaml")
_CANONICAL_OUTPUT = Path("docs/experiments/E-0036-qwen-reviewed-evaluation.json")
_EVALUATOR = Path("src/bctc_ai/evaluation/qwen35_reviewed_evaluation.py")
_CAPTURE_SCRIPT = Path("scripts/experiments/capture_e0036_qwen_reviewed_evaluation.py")
_CONTROL_STATE = "READY_FOR_QWEN_REVIEWED_EVALUATION"
_OUTPUT_STATE = "QWEN_REVIEWED_EVALUATION_COMPLETE"
_QWEN_SEAL_STATE = "QWEN_OUTPUT_HASH_SEALED_BEFORE_REVIEW_ACCESS"
_QWEN_RESULT_STATE = "REFERENCE_BLIND_LOGICAL_ROW_LABEL_INFERENCE_COMPLETE"
_BASELINE_STATE = "BASELINES_REVIEWED_QWEN_TRIGGERED"
_VALID_PROPOSAL_STATUS = "PARSED_SEMANTIC_PROPOSAL_ONLY"
_EXPECTED_REJECTION_STATUS = "REJECT_TOKEN_BUDGET_EXHAUSTED"
_DECISION = "REJECT_CURRENT_PINNED_CONFIGURATION_NO_VALID_SEMANTIC_PROPOSALS"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_GIT_COMMIT = re.compile(r"[0-9a-f]{40}")
_FIXED_REVIEWED_IDENTITIES = (
    ("page-0003-row-018-label", 4317),
    ("page-0003-row-019-label", 4354),
    ("page-0003-row-034-label", 4357),
    ("page-0003-row-035-label", 4335),
    ("page-0003-row-036-label", 4366),
    ("page-0004-row-009-label", 4336),
)
_CONTROL_KEYS = {
    "version",
    "experiment_id",
    "dataset_role",
    "state",
    "frozen_inputs",
    "implementation",
    "output",
}
_FROZEN_INPUT_KEYS = {
    "qwen_output_seal",
    "baseline_reviewed_evaluation",
    "e0036_control",
}
_IMPLEMENTATION_KEYS = {"evaluator", "capture_script"}
_RESULT_KEYS = {
    "format_version",
    "experiment_id",
    "reader",
    "state",
    "dataset_role",
    "evidence_role",
    "reference_text_available_to_reader",
    "sample_count",
    "samples",
    "authority",
}
_SAMPLE_KEYS = {
    "sample_id",
    "category",
    "crop_path",
    "crop_sha256",
    "crop_width",
    "crop_height",
    "input_token_count",
    "visual_token_count",
    "generated_token_ids",
    "forbidden_generated_control_token_ids",
    "raw_generated_output",
    "raw_output",
    "nonempty_line_count",
    "generated_token_count",
    "terminated_by_eos",
    "status",
    "proposal_text",
    "reader_score",
    "reader_score_available",
    "inference_seconds",
}


@dataclass(frozen=True)
class _StableFile:
    path: Path
    payload: bytes
    identity: tuple[int, int, int, int, int, int]
    artifact: dict[str, Any]


def _git(project_root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _resolve(project_root: Path, value: Path | str, label: str) -> Path:
    raw = Path(value)
    if raw.is_absolute() or not raw.parts or ".." in raw.parts:
        raise Qwen35ReviewedEvaluationError(f"unsafe project-relative {label} path: {value}")
    cursor = project_root
    for part in raw.parts:
        cursor /= part
        if cursor.is_symlink():
            raise Qwen35ReviewedEvaluationError(f"{label} path contains a symlink: {value}")
    resolved = (project_root / raw).resolve()
    if not resolved.is_relative_to(project_root):
        raise Qwen35ReviewedEvaluationError(f"{label} path escapes project root: {value}")
    return resolved


def _canonical_argument(
    project_root: Path,
    supplied: Path,
    expected: Path,
    label: str,
) -> Path:
    if supplied.is_absolute() or supplied.as_posix() != expected.as_posix():
        raise Qwen35ReviewedEvaluationError(
            f"{label} must use canonical path: {expected.as_posix()}"
        )
    supplied_path = _resolve(project_root, supplied, label)
    expected_path = _resolve(project_root, expected, label)
    if supplied_path != expected_path:
        raise Qwen35ReviewedEvaluationError(
            f"{label} must use canonical path: {expected.as_posix()}"
        )
    return supplied_path


def _load_json_bytes(payload_bytes: bytes, path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Qwen35ReviewedEvaluationError(f"cannot load {label}: {path}") from error
    if not isinstance(payload, dict):
        raise Qwen35ReviewedEvaluationError(f"{label} must be an object")
    return payload


def _load_yaml_bytes(payload_bytes: bytes, path: Path, label: str) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(payload_bytes.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as error:
        raise Qwen35ReviewedEvaluationError(f"cannot load {label}: {path}") from error
    if not isinstance(payload, dict):
        raise Qwen35ReviewedEvaluationError(f"{label} must be an object")
    return payload


def _stat_identity(value: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _read_stable_file(project_root: Path, path: Path, label: str) -> _StableFile:
    if not path.is_relative_to(project_root):
        raise Qwen35ReviewedEvaluationError(f"{label} path escapes project root")
    relative = path.relative_to(project_root)
    safe_path = _resolve(project_root, relative, label)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(safe_path, flags)
    except OSError as error:
        raise Qwen35ReviewedEvaluationError(f"cannot open {label}: {safe_path}") from error
    chunks: list[bytes] = []
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise Qwen35ReviewedEvaluationError(f"{label} must be a regular file")
        while block := os.read(descriptor, 1024 * 1024):
            chunks.append(block)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    payload = b"".join(chunks)
    if _stat_identity(before) != _stat_identity(after) or len(payload) != before.st_size:
        raise Qwen35ReviewedEvaluationError(f"{label} changed while being read")
    return _StableFile(
        path=safe_path,
        payload=payload,
        identity=_stat_identity(before),
        artifact={
            "path": relative.as_posix(),
            "size_bytes": before.st_size,
            "sha256": hashlib.sha256(payload).hexdigest(),
        },
    )


def _verify_artifact_record(
    project_root: Path,
    record: object,
    label: str,
    *,
    expected_path: Path | None = None,
) -> _StableFile:
    if not isinstance(record, dict) or set(record) != {"path", "size_bytes", "sha256"}:
        raise Qwen35ReviewedEvaluationError(f"{label} identity is invalid")
    if (
        not isinstance(record["path"], str)
        or not isinstance(record["size_bytes"], int)
        or isinstance(record["size_bytes"], bool)
        or record["size_bytes"] < 0
        or not isinstance(record["sha256"], str)
        or _SHA256.fullmatch(record["sha256"]) is None
    ):
        raise Qwen35ReviewedEvaluationError(f"{label} identity is invalid")
    path = _resolve(project_root, record["path"], label)
    if expected_path is not None:
        if record["path"] != expected_path.as_posix() or path != _resolve(
            project_root, expected_path, label
        ):
            raise Qwen35ReviewedEvaluationError(f"{label} path is noncanonical")
    stable = _read_stable_file(project_root, path, label)
    if stable.artifact != record:
        raise Qwen35ReviewedEvaluationError(f"{label} is absent or hash-drifted")
    return stable


def _assert_stable_file_unchanged(project_root: Path, original: _StableFile, label: str) -> None:
    current = _read_stable_file(project_root, original.path, label)
    if current.identity != original.identity or current.artifact != original.artifact:
        raise Qwen35ReviewedEvaluationError(f"{label} changed after validation")


def _validate_control(
    project_root: Path,
    control: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if (
        set(control) != _CONTROL_KEYS
        or control.get("version") != 1
        or control.get("experiment_id") != "E-0036"
        or control.get("dataset_role") != "CALIBRATION"
        or control.get("state") != _CONTROL_STATE
    ):
        raise Qwen35ReviewedEvaluationError("Qwen reviewed-evaluation control drifted")
    frozen = control.get("frozen_inputs")
    implementation = control.get("implementation")
    output = control.get("output")
    if not isinstance(frozen, dict) or set(frozen) != _FROZEN_INPUT_KEYS:
        raise Qwen35ReviewedEvaluationError("Qwen frozen-input registry drifted")
    if not isinstance(implementation, dict) or set(implementation) != _IMPLEMENTATION_KEYS:
        raise Qwen35ReviewedEvaluationError("Qwen evaluation implementation registry drifted")
    if not isinstance(output, dict) or set(output) != {"path"}:
        raise Qwen35ReviewedEvaluationError("Qwen reviewed-evaluation output control drifted")
    if output["path"] != _CANONICAL_OUTPUT.as_posix():
        raise Qwen35ReviewedEvaluationError("Qwen reviewed-evaluation output is noncanonical")
    _verify_artifact_record(
        project_root,
        implementation["evaluator"],
        "Qwen reviewed evaluator",
        expected_path=_EVALUATOR,
    )
    _verify_artifact_record(
        project_root,
        implementation["capture_script"],
        "Qwen reviewed-evaluation capture script",
        expected_path=_CAPTURE_SCRIPT,
    )
    return frozen, implementation, output


def _validate_s3_seal(seal: dict[str, Any]) -> dict[str, Any]:
    reader = seal.get("reader")
    snapshot = seal.get("s3_artifact_snapshot")
    hydrate = snapshot.get("hydrate_probe") if isinstance(snapshot, dict) else None
    result_record = reader.get("result") if isinstance(reader, dict) else None
    manifest_record = reader.get("manifest") if isinstance(reader, dict) else None
    expected_total_bytes = (
        result_record.get("size_bytes", -1) + manifest_record.get("size_bytes", -1)
        if isinstance(result_record, dict) and isinstance(manifest_record, dict)
        else -1
    )
    if (
        seal.get("format_version") != 1
        or seal.get("experiment_id") != "E-0036"
        or seal.get("dataset_role") != "CALIBRATION"
        or seal.get("state") != _QWEN_SEAL_STATE
        or seal.get("seal_git_dirty") is not False
        or seal.get("exact_output_file_count") != 2
        or seal.get("same_ordered_sample_ids_as_request") is not True
        or seal.get("reference_or_human_review_loaded_by_sealer") is not False
        or seal.get("evaluation_allowed_only_after_this_seal") is not True
        or not isinstance(reader, dict)
        or reader.get("reader") != "QWEN3_5_27B_GPTQ_INT4"
        or reader.get("sample_count") != 64
        or reader.get("reference_text_available_to_reader") is not False
        or reader.get("human_review_available_to_reader") is not False
        or reader.get("all_authority_flags") is not False
        or not isinstance(snapshot, dict)
        or not isinstance(snapshot.get("artifact_snapshot_id"), str)
        or not snapshot["artifact_snapshot_id"]
        or snapshot.get("file_count") != 2
        or snapshot.get("uploaded_object_count") != 2
        or snapshot.get("total_bytes") != expected_total_bytes
        or snapshot.get("restore_verified") is not True
        or not isinstance(hydrate, dict)
        or hydrate.get("status") != "PASS"
        or hydrate.get("restored_file_count") != 2
        or hydrate.get("seal_hashes_match") is not True
        or hydrate.get("existing_target_no_overwrite_refused") is not True
        or hydrate.get("logical_path") != reader.get("output_directory")
    ):
        raise Qwen35ReviewedEvaluationError(
            "Qwen output seal or S3 restore/hydrate evidence is incomplete"
        )
    for key in ("manifest", "run_record"):
        record = snapshot.get(key)
        if (
            not isinstance(record, dict)
            or set(record) != {"key", "sha256"}
            or not isinstance(record.get("key"), str)
            or not record["key"]
            or not isinstance(record.get("sha256"), str)
            or _SHA256.fullmatch(record["sha256"]) is None
        ):
            raise Qwen35ReviewedEvaluationError(f"Qwen S3 {key} identity is invalid")
    return {
        "qwen_output_hash_sealed_before_review": True,
        "exact_output_file_count": 2,
        "same_ordered_sample_ids_as_request": True,
        "s3_artifact_snapshot_id": snapshot["artifact_snapshot_id"],
        "s3_file_count": snapshot["file_count"],
        "s3_restore_verified": True,
        "s3_hydrate_probe_status": "PASS",
        "s3_hydrate_restored_file_count": hydrate["restored_file_count"],
        "s3_hydrate_seal_hashes_match": True,
        "s3_hydrate_existing_target_no_overwrite_refused": True,
    }


def _validate_output_inventory(
    project_root: Path, seal: dict[str, Any]
) -> tuple[Path, tuple[int, int, int, int, int, int]]:
    reader = seal["reader"]
    output_directory = _resolve(
        project_root, reader.get("output_directory", ""), "Qwen output directory"
    )
    try:
        directory_stat = output_directory.lstat()
    except OSError as error:
        raise Qwen35ReviewedEvaluationError("Qwen output directory is absent or unsafe") from error
    if output_directory.is_symlink() or not stat.S_ISDIR(directory_stat.st_mode):
        raise Qwen35ReviewedEvaluationError("Qwen output directory is absent or unsafe")
    entries = list(output_directory.iterdir())
    if {entry.name for entry in entries} != {"ocr_result.json", "run_manifest.json"} or any(
        entry.is_symlink() or not entry.is_file() for entry in entries
    ):
        raise Qwen35ReviewedEvaluationError("Qwen output is not the exact two-file set")
    return output_directory, _stat_identity(directory_stat)


def _validate_result_samples(
    result: dict[str, Any],
    request_samples: list[dict[str, str]],
) -> list[dict[str, Any]]:
    raw_samples = result.get("samples")
    authority = result.get("authority")
    if (
        set(result) != _RESULT_KEYS
        or result.get("format_version") != 1
        or result.get("experiment_id") != "E-0036"
        or result.get("reader") != "QWEN3_5_27B_GPTQ_INT4"
        or result.get("state") != _QWEN_RESULT_STATE
        or result.get("dataset_role") != "CALIBRATION"
        or result.get("reference_text_available_to_reader") is not False
        or result.get("sample_count") != 64
        or not isinstance(authority, dict)
        or not authority
        or any(value is not False for value in authority.values())
        or not isinstance(raw_samples, list)
        or len(raw_samples) != 64
    ):
        raise Qwen35ReviewedEvaluationError("sealed Qwen result identity drifted")
    samples: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw, request_sample in zip(raw_samples, request_samples, strict=True):
        if not isinstance(raw, dict) or set(raw) != _SAMPLE_KEYS:
            raise Qwen35ReviewedEvaluationError("sealed Qwen sample structure drifted")
        sample_id = raw.get("sample_id")
        status = raw.get("status")
        proposal = raw.get("proposal_text")
        token_ids = raw.get("generated_token_ids")
        if (
            sample_id != request_sample["sample_id"]
            or sample_id in seen
            or raw.get("category") != request_sample["category"]
            or raw.get("crop_path") != request_sample["crop_path"]
            or raw.get("crop_sha256") != request_sample["crop_sha256"]
            or not isinstance(status, str)
            or not isinstance(proposal, str)
            or not isinstance(raw.get("raw_output"), str)
            or not isinstance(raw.get("raw_generated_output"), str)
            or not isinstance(token_ids, list)
            or any(
                not isinstance(token_id, int) or isinstance(token_id, bool)
                for token_id in token_ids
            )
            or raw.get("generated_token_count") != len(token_ids)
            or not isinstance(raw.get("inference_seconds"), (int, float))
            or isinstance(raw.get("inference_seconds"), bool)
            or not math.isfinite(float(raw["inference_seconds"]))
            or float(raw["inference_seconds"]) < 0
        ):
            raise Qwen35ReviewedEvaluationError(
                f"sealed Qwen sample identity drifted: {request_sample['sample_id']}"
            )
        if status == _VALID_PROPOSAL_STATUS:
            if not proposal.strip():
                raise Qwen35ReviewedEvaluationError(
                    f"accepted Qwen sample has an empty proposal: {sample_id}"
                )
        elif not status.startswith("REJECT_") or proposal != "":
            raise Qwen35ReviewedEvaluationError(
                f"rejected Qwen sample must expose an empty proposal: {sample_id}"
            )
        seen.add(str(sample_id))
        samples.append(raw)
    return samples


def summarize_generation_degeneracy(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize raw generation separately from label scoring or mapping."""

    if not samples:
        raise Qwen35ReviewedEvaluationError("cannot summarize an empty Qwen output")
    sequences: list[tuple[int, ...]] = []
    raw_outputs: list[str] = []
    raw_generated_outputs: list[str] = []
    for sample in samples:
        token_ids = sample.get("generated_token_ids")
        raw_output = sample.get("raw_output")
        raw_generated_output = sample.get("raw_generated_output")
        if (
            not isinstance(token_ids, list)
            or any(not isinstance(value, int) or isinstance(value, bool) for value in token_ids)
            or not isinstance(raw_output, str)
            or not isinstance(raw_generated_output, str)
        ):
            raise Qwen35ReviewedEvaluationError("Qwen degeneracy input is invalid")
        sequences.append(tuple(token_ids))
        raw_outputs.append(raw_output)
        raw_generated_outputs.append(raw_generated_output)
    unique_sequences = set(sequences)
    unique_raw = set(raw_outputs)
    unique_raw_generated = set(raw_generated_outputs)
    repeated_token_id: int | None = None
    repeated_token_count_per_sample: int | None = None
    if (
        len(unique_sequences) == 1
        and sequences[0]
        and len(set(sequences[0])) == 1
        and all(sequence == sequences[0] for sequence in sequences)
    ):
        repeated_token_id = sequences[0][0]
        repeated_token_count_per_sample = len(sequences[0])
    return {
        "sample_count": len(samples),
        "unique_generated_token_sequence_count": len(unique_sequences),
        "unique_raw_output_count": len(unique_raw),
        "unique_raw_generated_output_count": len(unique_raw_generated),
        "single_repeated_token_sequence_across_all_samples": repeated_token_id is not None,
        "repeated_token_id": repeated_token_id,
        "repeated_token_count_per_sample": repeated_token_count_per_sample,
        "repeated_token_total_count": (
            None
            if repeated_token_count_per_sample is None
            else repeated_token_count_per_sample * len(samples)
        ),
        "unique_raw_output_sha256": (
            hashlib.sha256(raw_outputs[0].encode("utf-8")).hexdigest()
            if len(unique_raw) == 1
            else None
        ),
        "unique_raw_generated_output_sha256": (
            hashlib.sha256(raw_generated_outputs[0].encode("utf-8")).hexdigest()
            if len(unique_raw_generated) == 1
            else None
        ),
        "raw_output_used_for_label_scoring": False,
        "raw_output_used_for_mapping": False,
    }


def extract_fixed_reviewed_rows(baseline: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract the six frozen references and IDs from the prior reviewed artifact."""

    human_review = baseline.get("human_review")
    bindings = human_review.get("row_bindings") if isinstance(human_review, dict) else None
    readers = baseline.get("reader_evaluations")
    conditional_qwen = baseline.get("conditional_qwen")
    if (
        baseline.get("format_version") != 1
        or baseline.get("experiment_id") != "E-0036"
        or baseline.get("dataset_role") != "CALIBRATION"
        or baseline.get("state") != _BASELINE_STATE
        or not isinstance(human_review, dict)
        or human_review.get("reviewed_row_count") != 6
        or not isinstance(bindings, list)
        or len(bindings) != 6
        or not isinstance(readers, dict)
        or set(readers) != {"vietocr", "deepseek_ocr2"}
        or not isinstance(conditional_qwen, dict)
        or conditional_qwen.get("triggered") is not True
        or conditional_qwen.get("decision") != "RUN_QWEN_SAME_REQUEST"
    ):
        raise Qwen35ReviewedEvaluationError("baseline reviewed evaluation drifted")
    reference_by_reader: dict[str, dict[str, str]] = {}
    for reader_key, reader in readers.items():
        label_samples = (
            reader.get("labels", {}).get("samples") if isinstance(reader, dict) else None
        )
        if not isinstance(label_samples, list) or len(label_samples) != 6:
            raise Qwen35ReviewedEvaluationError(
                f"baseline {reader_key} reviewed label denominator drifted"
            )
        references: dict[str, str] = {}
        for sample in label_samples:
            if (
                not isinstance(sample, dict)
                or not isinstance(sample.get("sample_id"), str)
                or not isinstance(sample.get("reference"), str)
                or not sample["reference"]
                or sample["sample_id"] in references
            ):
                raise Qwen35ReviewedEvaluationError(
                    f"baseline {reader_key} reviewed reference drifted"
                )
            references[sample["sample_id"]] = sample["reference"]
        reference_by_reader[reader_key] = references
    rows: list[dict[str, Any]] = []
    seen_samples: set[str] = set()
    seen_ids: set[int] = set()
    for binding in bindings:
        if not isinstance(binding, dict):
            raise Qwen35ReviewedEvaluationError("baseline reviewed row binding is invalid")
        sample_id = binding.get("sample_id")
        reviewed_id = binding.get("reviewed_item_id")
        if (
            not isinstance(sample_id, str)
            or sample_id in seen_samples
            or not isinstance(reviewed_id, int)
            or isinstance(reviewed_id, bool)
            or reviewed_id in seen_ids
        ):
            raise Qwen35ReviewedEvaluationError("baseline reviewed row identity drifted")
        references = {
            reference_by_reader[reader_key].get(sample_id) for reader_key in sorted(readers)
        }
        if None in references or len(references) != 1:
            raise Qwen35ReviewedEvaluationError(
                f"baseline readers disagree on reviewed reference: {sample_id}"
            )
        rows.append(
            {
                "sample_id": sample_id,
                "reviewed_report_norm_id": reviewed_id,
                "reference": references.pop(),
            }
        )
        seen_samples.add(sample_id)
        seen_ids.add(reviewed_id)
    identities = tuple((str(row["sample_id"]), int(row["reviewed_report_norm_id"])) for row in rows)
    if identities != _FIXED_REVIEWED_IDENTITIES:
        raise Qwen35ReviewedEvaluationError("fixed six reviewed row identities drifted")
    return rows


def evaluate_reviewed_proposals(
    samples: list[dict[str, Any]],
    reviewed_rows: list[dict[str, Any]],
    *,
    document_key: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Score only proposal_text and keep every rejected output out of mapping."""

    if len(samples) != 64 or len(reviewed_rows) != 6:
        raise Qwen35ReviewedEvaluationError("Qwen reviewed denominator drifted")
    samples_by_id: dict[str, dict[str, Any]] = {}
    status_counts: Counter[str] = Counter()
    valid_sample_ids: list[str] = []
    for sample in samples:
        sample_id = sample.get("sample_id")
        status = sample.get("status")
        proposal = sample.get("proposal_text")
        if (
            not isinstance(sample_id, str)
            or sample_id in samples_by_id
            or not isinstance(status, str)
            or not isinstance(proposal, str)
        ):
            raise Qwen35ReviewedEvaluationError("Qwen proposal input is invalid")
        eligible = status == _VALID_PROPOSAL_STATUS and bool(proposal.strip())
        if status == _VALID_PROPOSAL_STATUS and not eligible:
            raise Qwen35ReviewedEvaluationError("accepted Qwen proposal is empty")
        if status != _VALID_PROPOSAL_STATUS and (
            not status.startswith("REJECT_") or proposal != ""
        ):
            raise Qwen35ReviewedEvaluationError("rejected Qwen outputs must have an empty proposal")
        if eligible:
            valid_sample_ids.append(sample_id)
        status_counts[status] += 1
        samples_by_id[sample_id] = sample
    score_inputs: list[dict[str, str]] = []
    reviewed_output_rows: list[dict[str, Any]] = []
    reviewed_valid_count = 0
    for reviewed in reviewed_rows:
        sample_id = reviewed.get("sample_id")
        sample = samples_by_id.get(str(sample_id))
        if sample is None:
            raise Qwen35ReviewedEvaluationError(f"reviewed Qwen sample is absent: {sample_id}")
        eligible = sample_id in valid_sample_ids
        reviewed_valid_count += int(eligible)
        proposal = str(sample["proposal_text"])
        score_inputs.append(
            {
                "sample_id": str(sample_id),
                "document": document_key,
                "category": "LOGICAL_ROW_LABEL",
                "reference": str(reviewed["reference"]),
                "prediction": proposal,
            }
        )
        reviewed_output_rows.append(
            {
                "sample_id": sample_id,
                "reviewed_report_norm_id": reviewed["reviewed_report_norm_id"],
                "reference": reviewed["reference"],
                "status": sample["status"],
                "proposal_text": proposal,
                "valid_semantic_proposal": eligible,
                "mapped_report_norm_id": None,
                "mapping_abstained": True,
            }
        )
    all_row_coverage = {
        "sample_count": len(samples),
        "valid_semantic_proposal_count": len(valid_sample_ids),
        "rejected_sample_count": len(samples) - len(valid_sample_ids),
        "valid_semantic_proposal_rate": len(valid_sample_ids) / len(samples),
        "status_counts": dict(sorted(status_counts.items())),
        "rejected_proposal_text_empty_count": sum(
            sample["status"] != _VALID_PROPOSAL_STATUS and sample["proposal_text"] == ""
            for sample in samples
        ),
        "mapping_eligible_sample_ids": valid_sample_ids,
    }
    fixed_denominator_score = score_reader(score_inputs, title_categories=set())
    reviewed_evaluation = {
        "reviewed_row_count": len(reviewed_rows),
        "valid_semantic_proposal_count": reviewed_valid_count,
        "rejected_sample_count": len(reviewed_rows) - reviewed_valid_count,
        "valid_semantic_proposal_rate": reviewed_valid_count / len(reviewed_rows),
        "proposal_field_scored": "proposal_text",
        "rejected_proposals_scored_as_empty": True,
        "rejected_raw_output_used_for_scoring": False,
        "fixed_denominator_failure_score": fixed_denominator_score,
        "accepted_only_label_metrics": {
            "status": (
                "NOT_SCORABLE_NO_VALID_PROPOSALS" if reviewed_valid_count == 0 else "SCORABLE"
            ),
            "sample_count": reviewed_valid_count,
            "metrics": None,
        },
        "rows": reviewed_output_rows,
    }
    if valid_sample_ids:
        mapping_status = "NOT_RUN_INCOMPLETE_VALID_PROPOSAL_SEQUENCE"
    else:
        mapping_status = "NOT_RUN_NO_VALID_PROPOSALS"
    mapping = {
        "status": mapping_status,
        "invoked": False,
        "requires_complete_64_sample_valid_proposal_sequence": True,
        "mapping_input_sample_count": 0,
        "rejected_sample_ids_passed_to_mapping": [],
        "best_path": None,
        "runner_up_path": None,
        "score_margin": None,
        "automatically_accepted_reviewed_count": 0,
        "reviewed_mapping_abstention_count": len(reviewed_rows),
        "reviewed_rows": [
            {
                "sample_id": row["sample_id"],
                "reviewed_report_norm_id": row["reviewed_report_norm_id"],
                "mapped_report_norm_id": None,
                "abstained": True,
            }
            for row in reviewed_output_rows
        ],
        "rejected_raw_output_used_for_mapping": False,
    }
    return all_row_coverage, reviewed_evaluation, mapping


def _baseline_comparison(baseline: dict[str, Any], qwen_exact_count: int) -> dict[str, Any]:
    comparisons: dict[str, Any] = {}
    for reader_key in ("vietocr", "deepseek_ocr2"):
        reader = baseline["reader_evaluations"][reader_key]
        aggregate = reader["labels"]["aggregate"]
        mapping = reader["mapping"]
        comparisons[reader_key] = {
            "reader": reader["reader"],
            "reviewed_exact_line_count": aggregate["exact_line_count"],
            "reviewed_line_count": aggregate["line_count"],
            "mapping_status": mapping["status"],
            "reviewed_best_path_exact_count": mapping["reviewed_best_path_exact_count"],
            "reviewed_automatically_accepted_exact_count": mapping[
                "reviewed_automatically_accepted_exact_count"
            ],
            "reviewed_mapping_abstention_count": mapping["reviewed_mapping_abstention_count"],
        }
    return {
        "same_fixed_six_reviewed_rows": True,
        "qwen_reviewed_exact_line_count": qwen_exact_count,
        "baseline_readers": comparisons,
        "qwen_exact_line_count_exceeds_any_baseline": any(
            qwen_exact_count > int(value["reviewed_exact_line_count"])
            for value in comparisons.values()
        ),
    }


def _exclusive_atomic_write_json(destination: Path, payload: dict[str, Any]) -> None:
    serialized = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", dir=destination.parent
    )
    temporary = Path(temporary_name)
    directory_fd = os.open(destination.parent, os.O_RDONLY)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o644)
        try:
            os.link(temporary, destination)
        except FileExistsError as error:
            raise Qwen35ReviewedEvaluationError(
                f"refusing to overwrite Qwen reviewed evaluation: {destination}"
            ) from error
        os.fsync(directory_fd)
        if sha256_file(destination) != hashlib.sha256(serialized).hexdigest():
            raise Qwen35ReviewedEvaluationError(
                "Qwen reviewed evaluation hash mismatch after publication"
            )
    finally:
        os.close(directory_fd)
        temporary.unlink(missing_ok=True)


def capture_qwen35_reviewed_evaluation(
    project_root: Path,
    *,
    config_path: Path = _CANONICAL_CONTROL,
    output_path: Path = _CANONICAL_OUTPUT,
) -> dict[str, Any]:
    """Evaluate the sealed Qwen proposal field against the fixed six reviewed rows."""

    project_root = project_root.resolve()
    control_path = _canonical_argument(
        project_root, config_path, _CANONICAL_CONTROL, "Qwen reviewed-evaluation control"
    )
    destination = _canonical_argument(
        project_root, output_path, _CANONICAL_OUTPUT, "Qwen reviewed-evaluation output"
    )
    if destination.exists():
        raise Qwen35ReviewedEvaluationError(
            f"refusing to overwrite Qwen reviewed evaluation: {destination}"
        )
    if _git(project_root, "status", "--porcelain"):
        raise Qwen35ReviewedEvaluationError(
            "formal E-0036 Qwen reviewed evaluation requires clean Git"
        )
    evaluation_commit = _git(project_root, "rev-parse", "HEAD")
    if _GIT_COMMIT.fullmatch(evaluation_commit) is None:
        raise Qwen35ReviewedEvaluationError("evaluation Git commit identity is invalid")
    control_file = _read_stable_file(project_root, control_path, "Qwen reviewed-evaluation control")
    control = _load_yaml_bytes(
        control_file.payload, control_path, "Qwen reviewed-evaluation control"
    )
    frozen, implementation, _output = _validate_control(project_root, control)
    tracked_files = [control_file]

    # The output seal and its S3 restore/hydrate proof are deliberately opened
    # and validated before the baseline artifact exposes reviewed references.
    seal_file = _verify_artifact_record(
        project_root, frozen["qwen_output_seal"], "Qwen output seal"
    )
    tracked_files.append(seal_file)
    seal = _load_json_bytes(seal_file.payload, seal_file.path, "Qwen output seal")
    seal_and_s3 = _validate_s3_seal(seal)
    output_directory, output_directory_identity = _validate_output_inventory(project_root, seal)
    request_file = _verify_artifact_record(project_root, seal.get("request"), "sealed Qwen request")
    tracked_files.append(request_file)
    request = _load_json_bytes(request_file.payload, request_file.path, "sealed Qwen request")
    try:
        request_samples = validate_logical_row_label_reader_request(request)
    except LogicalRowLabelReaderContractError as error:
        raise Qwen35ReviewedEvaluationError(str(error)) from error
    result_file = _verify_artifact_record(
        project_root, seal["reader"].get("result"), "sealed Qwen result"
    )
    manifest_file = _verify_artifact_record(
        project_root, seal["reader"].get("manifest"), "sealed Qwen manifest"
    )
    if (
        result_file.path != output_directory / "ocr_result.json"
        or manifest_file.path != output_directory / "run_manifest.json"
    ):
        raise Qwen35ReviewedEvaluationError(
            "Qwen sealed file records do not identify the exact output inventory"
        )
    tracked_files.extend((result_file, manifest_file))
    result = _load_json_bytes(result_file.payload, result_file.path, "sealed Qwen result")
    manifest = _load_json_bytes(manifest_file.payload, manifest_file.path, "sealed Qwen manifest")
    samples = _validate_result_samples(result, request_samples)
    status_counts = dict(sorted(Counter(str(sample["status"]) for sample in samples).items()))
    if seal["reader"].get("status_counts") != status_counts:
        raise Qwen35ReviewedEvaluationError("Qwen seal status counts drifted")
    if manifest.get("metrics") != seal["reader"].get("metrics"):
        raise Qwen35ReviewedEvaluationError("Qwen sealed runtime metrics drifted")

    e0036_file = _verify_artifact_record(
        project_root, frozen["e0036_control"], "frozen E-0036 control"
    )
    tracked_files.append(e0036_file)
    e0036_control = _load_yaml_bytes(e0036_file.payload, e0036_file.path, "frozen E-0036 control")
    qwen_control = e0036_control.get("conditional_qwen_challenger")
    if (
        e0036_control.get("version") != 1
        or e0036_control.get("experiment_id") != "E-0036"
        or e0036_control.get("dataset_role") != "CALIBRATION"
        or not isinstance(qwen_control, dict)
        or qwen_control.get("required_same_request_sha256") != request_file.artifact["sha256"]
        or qwen_control.get("output_seal_path") != seal_file.artifact["path"]
        or qwen_control.get("reviewed_evaluation_requires_qwen_output_seal") is not True
        or qwen_control.get("exact_output_files") != ["ocr_result.json", "run_manifest.json"]
    ):
        raise Qwen35ReviewedEvaluationError("frozen E-0036 Qwen control drifted")

    baseline_file = _verify_artifact_record(
        project_root,
        frozen["baseline_reviewed_evaluation"],
        "baseline reviewed evaluation",
    )
    tracked_files.append(baseline_file)
    baseline = _load_json_bytes(
        baseline_file.payload, baseline_file.path, "baseline reviewed evaluation"
    )
    if (
        baseline.get("request") != request_file.artifact
        or baseline.get("conditional_qwen", {}).get("required_same_request_sha256")
        != request_file.artifact["sha256"]
    ):
        raise Qwen35ReviewedEvaluationError("baseline and Qwen request identities differ")
    reviewed_rows = extract_fixed_reviewed_rows(baseline)
    document_key = str(baseline["human_review"]["document_key"])
    coverage, reviewed_evaluation, mapping = evaluate_reviewed_proposals(
        samples,
        reviewed_rows,
        document_key=document_key,
    )
    degeneracy = summarize_generation_degeneracy(samples)
    aggregate = reviewed_evaluation["fixed_denominator_failure_score"]["aggregate"]
    if (
        coverage["valid_semantic_proposal_count"] != 0
        or coverage["rejected_sample_count"] != 64
        or coverage["status_counts"] != {_EXPECTED_REJECTION_STATUS: 64}
        or reviewed_evaluation["valid_semantic_proposal_count"] != 0
        or reviewed_evaluation["rejected_sample_count"] != 6
        or mapping["status"] != "NOT_RUN_NO_VALID_PROPOSALS"
        or mapping["reviewed_mapping_abstention_count"] != 6
        or degeneracy["unique_generated_token_sequence_count"] != 1
        or degeneracy["unique_raw_output_count"] != 1
        or degeneracy["unique_raw_generated_output_count"] != 1
        or degeneracy["repeated_token_id"] != 163749
        or degeneracy["repeated_token_count_per_sample"] != 96
        or aggregate["exact_line_count"] != 0
        or aggregate["line_count"] != 6
        or aggregate["reference_character_count"] != 145
        or aggregate["character_edit_distance"] != 145
        or aggregate["deletion_count"] != 145
        or aggregate["character_error_rate"] != 1.0
        or aggregate["reference_word_count"] != 35
        or aggregate["word_edit_distance"] != 35
        or aggregate["word_error_rate"] != 1.0
        or aggregate["empty_prediction_count"] != 6
    ):
        raise Qwen35ReviewedEvaluationError(
            "sealed Qwen observation differs from the pinned no-valid-proposal outcome"
        )

    evaluator_file = _verify_artifact_record(
        project_root,
        implementation["evaluator"],
        "Qwen reviewed evaluator",
        expected_path=_EVALUATOR,
    )
    capture_file = _verify_artifact_record(
        project_root,
        implementation["capture_script"],
        "Qwen reviewed-evaluation capture script",
        expected_path=_CAPTURE_SCRIPT,
    )
    tracked_files.extend((evaluator_file, capture_file))
    payload: dict[str, Any] = {
        "identity": {
            "format_version": 1,
            "experiment_id": "E-0036",
            "dataset_role": "CALIBRATION",
            "evaluation_git_commit": evaluation_commit,
            "evaluation_git_dirty": False,
            "control": control_file.artifact,
            "evaluator": evaluator_file.artifact,
            "capture_script": capture_file.artifact,
        },
        "state": _OUTPUT_STATE,
        "input_artifacts": {
            "qwen_output_seal": seal_file.artifact,
            "qwen_request": request_file.artifact,
            "qwen_result": result_file.artifact,
            "qwen_manifest": manifest_file.artifact,
            "baseline_reviewed_evaluation": baseline_file.artifact,
            "e0036_control": e0036_file.artifact,
        },
        "seal_and_s3_verification": seal_and_s3,
        "review_access_order": {
            "qwen_output_seal_validated_before_baseline_review_open": True,
            "s3_restore_and_hydrate_validated_before_baseline_review_open": True,
            "baseline_reviewed_evaluation_is_only_review_source": True,
            "human_review_registry_or_dataset_loaded_directly": False,
            "mapping_completed_before_review_access": False,
            "mapping_not_invoked_because_no_valid_proposals": True,
        },
        "all_row_proposal_coverage": coverage,
        "reviewed_row_evaluation": reviewed_evaluation,
        "mapping_disposition": mapping,
        "baseline_comparison": _baseline_comparison(baseline, int(aggregate["exact_line_count"])),
        "runtime_metrics": {
            "source": "QWEN_OUTPUT_SEAL_READER_METRICS",
            "sealed_metrics": seal["reader"]["metrics"],
            "generation_degeneracy": degeneracy,
        },
        "decision": _DECISION,
        "model_family_conclusion": "NOT_ESTABLISHED",
        "authority": {
            "label_truth": False,
            "rejected_raw_output_as_label": False,
            "geometry": False,
            "numeric_value_sign_blank_dash_or_status": False,
            "period_unit_scope_or_statement_type": False,
            "report_norm_id_or_schema_mapping": False,
            "mapping_best_path_or_automatic_acceptance": False,
            "automatic_model_promotion": False,
            "model_family_rejection": False,
            "holdout_or_production_accuracy": False,
        },
        "claim_boundary": (
            "This calibration-only evaluation scores only the sealed proposal_text field on "
            "the same six pre-existing reviewed MBB rows. All 64 outputs from the current "
            "pinned Qwen configuration were structurally rejected and therefore contribute "
            "empty proposals; their raw generated text is diagnostic only and is never scored "
            "or mapped. The decision rejects this exact pinned configuration, not the Qwen "
            "model family, and grants no label, mapping, numeric, accounting, holdout or "
            "production authority."
        ),
    }
    if destination.exists():
        raise Qwen35ReviewedEvaluationError(
            f"refusing to overwrite Qwen reviewed evaluation: {destination}"
        )
    if _git(project_root, "rev-parse", "HEAD") != evaluation_commit or _git(
        project_root, "status", "--porcelain"
    ):
        raise Qwen35ReviewedEvaluationError(
            "Git code drifted during formal Qwen reviewed evaluation"
        )
    for stable_file in tracked_files:
        _assert_stable_file_unchanged(
            project_root, stable_file, f"rechecked {stable_file.artifact['path']}"
        )
    final_output_directory, final_output_directory_identity = _validate_output_inventory(
        project_root, seal
    )
    if (
        final_output_directory != output_directory
        or final_output_directory_identity != output_directory_identity
    ):
        raise Qwen35ReviewedEvaluationError(
            "Qwen output directory changed during reviewed evaluation"
        )
    _exclusive_atomic_write_json(destination, payload)
    return payload


__all__ = [
    "Qwen35ReviewedEvaluationError",
    "capture_qwen35_reviewed_evaluation",
    "evaluate_reviewed_proposals",
    "extract_fixed_reviewed_rows",
    "summarize_generation_degeneracy",
]
