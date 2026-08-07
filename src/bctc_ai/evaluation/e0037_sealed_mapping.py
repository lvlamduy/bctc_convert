from __future__ import annotations

import ctypes
import errno
import fcntl
import hashlib
import json
import math
import os
import re
import secrets
import stat
import subprocess
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, cast

import yaml

from bctc_ai.mapping.ordered_subgraph import build_schema_graph
from bctc_ai.mapping.scope import ScopePolicy, classify_mapping_scopes, load_scope_policy
from bctc_ai.ocr.logical_row_label_reader_contract import (
    LogicalRowLabelReaderContractError,
    validate_logical_row_label_reader_request,
)
from bctc_ai.schema.hierarchy import _load_source, apply_hierarchy_reference
from bctc_ai.schema.registry import load_workbook


class E0037SealedMappingError(RuntimeError):
    """Raised when an E-0037 phase cannot preserve the sealed-evidence contract."""


CONTROL_RELATIVE_PATH = Path("config/experiments/e0037-mbb-cdkt-sealed-evidence-mapping.yaml")
SOURCE_STRUCTURE_RELATIVE_PATH = Path(
    "output/calibration/e0037-mbb-cdkt-sealed-evidence-mapping/source_structure.json"
)
MAPPING_ONLY_RELATIVE_PATH = Path(
    "output/calibration/e0037-mbb-cdkt-sealed-evidence-mapping/mapping_only.json"
)
MAPPING_SEAL_RELATIVE_PATH = Path("docs/experiments/E-0037-mbb-cdkt-mapping-only-seal.json")
POSTJOIN_RELATIVE_PATH = Path("docs/experiments/E-0037-mbb-cdkt-sealed-evidence-mapping.json")

SOURCE_STRUCTURE_STATE = "SOURCE_ONLY_STRUCTURE_SEALED_BEFORE_SCHEMA_ACCESS"
MAPPING_ONLY_STATE = "MAPPING_ONLY_SEALED_BEFORE_NUMERIC_PERIOD_REVIEW_ACCESS"
MAPPING_SEAL_STATE = "MAPPING_ONLY_HASH_SEALED_BEFORE_POSTJOIN"
POSTJOIN_STATE = "SEALED_MAPPING_POSTJOIN_ASSEMBLY_COMPLETE"

_SHA256 = re.compile(r"[0-9a-f]{64}")
_GIT_COMMIT = re.compile(r"[0-9a-f]{40}")
_SAMPLE_ID = re.compile(r"page-(?P<page>[0-9]{4})-row-(?P<row>[0-9]{3})-label")
_E0035_STATE = "FROZEN_ALL_LOGICAL_ROW_LABEL_CROPS_NO_SEMANTIC_INFERENCE"
_E0035_SEAL_STATUS = "PASS_REFERENCE_BLIND_ALL_LOGICAL_ROW_LABEL_CROPS_FROZEN"
_E0036_REQUEST_STATE = "READY_FOR_REFERENCE_BLIND_LOGICAL_ROW_LABEL_INFERENCE"
_E0036_READER_STATE = "REFERENCE_BLIND_LOGICAL_ROW_LABEL_INFERENCE_COMPLETE"
_E0036_BASELINE_SEAL_STATE = "BASELINE_OUTPUTS_HASH_SEALED_BEFORE_REVIEW_ACCESS"
_E0030_STATUS = "PASS_REFERENCE_BLIND_VISIBLE_HEADER_BINDING"
_E0034_STATUS = "PASS_REFERENCE_BLIND_INDEPENDENT_NUMERIC_VERIFICATION"
_EXPECTED_READERS = {
    "vietocr": ("VIETOCR_VGG_TRANSFORMER", "raw_prediction"),
    "deepseek_ocr2": ("DEEPSEEK_OCR_2", "proposal_text"),
}
_VALID_DEEPSEEK_STATUS = "PARSED_SEMANTIC_PROPOSAL_ONLY"
_ACCEPTED_MAPPING_STATUSES = frozenset({"RESOLVED_ANCHOR", "RESOLVED_PATH"})
_MFD_CLOEXEC = 0x0001
_MFD_ALLOW_SEALING = 0x0002
_F_ADD_SEALS = 1033
_F_GET_SEALS = 1034
_F_SEAL_SEAL = 0x0001
_F_SEAL_SHRINK = 0x0002
_F_SEAL_GROW = 0x0004
_F_SEAL_WRITE = 0x0008
_E0035_EXPECTED_PATHS = {
    "e0035_seal": Path("docs/experiments/E-0035-mbb-cdkt-logical-row-label-crops.json"),
    "e0035_crop_manifest": Path(
        "output/calibration/e0035-mbb-cdkt-logical-row-label-crops/"
        "a177792e8b98f340f562/crop_manifest.json"
    ),
}
_MAPPING_INPUT_EXPECTED_PATHS = {
    **_E0035_EXPECTED_PATHS,
    "e0036_request": Path("output/calibration/e0036-mbb-cdkt-semantic-label-readers/request.json"),
    "e0036_baseline_output_seal": Path(
        "docs/experiments/E-0036-mbb-cdkt-baseline-output-seal.json"
    ),
    "vietocr_result": Path(
        "output/calibration/e0036-mbb-cdkt-semantic-label-readers/vietocr-reader/ocr_result.json"
    ),
    "deepseek_result": Path(
        "output/calibration/e0036-mbb-cdkt-semantic-label-readers/deepseek-reader/ocr_result.json"
    ),
    "cdkt_workbook": Path("template/Bank_CDKT_ReportNormId.xlsx"),
    "hierarchy_config": Path("config/schemas/hierarchy_reference.yaml"),
    "cdkt_hierarchy_workbook": Path("vst_level/vst_bank_balance_sheet.xlsx"),
    "scope_policy": Path("config/mapping/scope_exclusions.yaml"),
    "mapping_policy": Path("config/mapping/ordered-subgraph-v2.yaml"),
}
_MAPPING_IMPLEMENTATION_EXPECTED_PATHS = {
    "source_structure_validator": Path("src/bctc_ai/evaluation/e0037_evidence_assembly.py"),
    "mapper": Path("src/bctc_ai/mapping/ordered_subgraph_v2.py"),
    "integration": Path("src/bctc_ai/evaluation/e0037_sealed_mapping.py"),
    "capture_script": Path("scripts/experiments/capture_e0037_mbb_cdkt_mapping.py"),
}
_POSTJOIN_INPUT_EXPECTED_PATHS = {
    "table_metadata": Path("docs/experiments/E-0030-mbb-cdkt-table-metadata.json"),
    "numeric_verification": Path("docs/experiments/E-0034-mbb-cdkt-numeric-verification-v2.json"),
}
_MAPPING_SEAL_POSTJOIN_ACCESS = {
    "mapping_only_validated_before_postjoin_access": True,
    "deterministic_mapping_replay_invocation_count": 1,
    "deterministic_mapping_replay_byte_equal": True,
    "e0030_opened": False,
    "e0033_opened": False,
    "e0034_opened": False,
    "mapper_replay_used_to_change_mapping": False,
}
_MAPPING_SEAL_AUTHORITY = {
    "mapping_output_hash_identity": True,
    "numeric_value_or_status": False,
    "period_or_unit": False,
    "review_or_history": False,
    "accounting_or_excel": False,
}
_MAPPING_SEAL_CLAIM_BOUNDARY = (
    "This artifact seals the E-0037 mapping-only bytes before any E-0030 period/unit "
    "or E-0034 numeric/status evidence is opened. It does not add, rerun, repair, or "
    "reinterpret a mapping and makes no numeric, accounting, Excel, holdout, or "
    "production claim."
)
_MAPPING_ONLY_CLAIM_BOUNDARY = (
    "E-0037 mapping-only is bounded MBB CDKT calibration evidence assembled without opening "
    "E-0030 authoritative period/unit evidence, E-0034 numeric/status evidence, review, or "
    "history artifacts; no period, unit, or numeric field or feature is passed to the mapper. "
    "It records source structure, sealed label proposals, workbook-order schema candidates, "
    "accepted mappings, ambiguities, and unmatched evidence. It does not establish period, "
    "unit, report scope, numeric truth, accounting validity, Excel correctness, holdout "
    "accuracy, or production readiness."
)
_SOURCE_PHASE_CLAIM_BOUNDARY = (
    "Seal A records deterministic source-only font-weight and slant evidence derived from "
    "registered crop pixels; casing and lexical row-role evidence derived from frozen E-0035 "
    "PP-OCR raw-label provenance; row-role proposals; and physical parent/section edges for "
    "the 64 E-0035 rows. Its exact canonical payload SHA-256 and size must be bound before "
    "schema access because payload-only validation cannot independently prove pixel or manifest "
    "derivation. It does not establish schema identity, mapping, period, unit, scope, numeric "
    "truth, accounting validity, Excel correctness, holdout accuracy, or production readiness; "
    "unsupported structure remains UNKNOWN."
)
_POSTJOIN_CLAIM_BOUNDARY = (
    "E-0037 postjoin may bind exact period axes and unit semantics from E-0030 only after the "
    "mapping-only seal. The final assembly must preserve accepted, ambiguous, unmatched, dash, "
    "blank, and challenger evidence and makes no bank-disjoint, period-disjoint, holdout, "
    "accounting, Excel-accuracy, or production-readiness claim."
)


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


def _clean_git_commit(project_root: Path) -> str:
    if _git(project_root, "status", "--porcelain"):
        raise E0037SealedMappingError("E-0037 publication requires a clean Git worktree")
    commit = _git(project_root, "rev-parse", "HEAD")
    if _GIT_COMMIT.fullmatch(commit) is None:
        raise E0037SealedMappingError("cannot resolve the exact E-0037 Git commit")
    return commit


def _resolve(project_root: Path, value: Path | str, label: str) -> Path:
    raw = Path(value)
    if raw.is_absolute() or not raw.parts or ".." in raw.parts:
        raise E0037SealedMappingError(f"unsafe project-relative {label} path: {value}")
    cursor = project_root
    for part in raw.parts:
        cursor /= part
        if cursor.is_symlink():
            raise E0037SealedMappingError(f"{label} path contains a symlink: {value}")
    resolved = (project_root / raw).resolve()
    if not resolved.is_relative_to(project_root):
        raise E0037SealedMappingError(f"{label} path escapes project root: {value}")
    return resolved


def _canonical_argument(
    project_root: Path,
    supplied: Path,
    expected: Path,
    label: str,
) -> Path:
    if supplied.is_absolute() or supplied.as_posix() != expected.as_posix():
        raise E0037SealedMappingError(f"{label} must use canonical path: {expected.as_posix()}")
    supplied_path = _resolve(project_root, supplied, label)
    expected_path = _resolve(project_root, expected, label)
    if supplied_path != expected_path:
        raise E0037SealedMappingError(f"{label} must use canonical path: {expected.as_posix()}")
    return supplied_path


def _stat_identity(value: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _open_parent_directory(
    project_root: Path,
    relative: Path,
    label: str,
) -> tuple[int, str]:
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        current = os.open(project_root, directory_flags)
    except OSError as error:
        raise E0037SealedMappingError(f"cannot open project root for {label}") from error
    try:
        for part in relative.parts[:-1]:
            try:
                following = os.open(part, directory_flags, dir_fd=current)
            except OSError as error:
                raise E0037SealedMappingError(
                    f"cannot traverse nofollow path for {label}: {relative}"
                ) from error
            os.close(current)
            current = following
        return current, relative.parts[-1]
    except Exception:
        os.close(current)
        raise


def _open_or_create_parent_directory(
    project_root: Path,
    relative: Path,
    label: str,
) -> tuple[int, str]:
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        current = os.open(project_root, directory_flags)
    except OSError as error:
        raise E0037SealedMappingError(f"cannot open project root for {label}") from error
    try:
        for part in relative.parts[:-1]:
            try:
                following = os.open(part, directory_flags, dir_fd=current)
            except OSError as error:
                if error.errno != errno.ENOENT:
                    raise E0037SealedMappingError(
                        f"cannot traverse nofollow output path for {label}: {relative}"
                    ) from error
                try:
                    os.mkdir(part, 0o755, dir_fd=current)
                    os.fsync(current)
                    following = os.open(part, directory_flags, dir_fd=current)
                except OSError as create_error:
                    raise E0037SealedMappingError(
                        f"cannot create output directory for {label}: {relative}"
                    ) from create_error
            os.close(current)
            current = following
        return current, relative.parts[-1]
    except Exception:
        os.close(current)
        raise


def _read_stable_file(
    project_root: Path,
    path: Path,
    label: str,
    *,
    expected_size: int | None = None,
    maximum_size: int = 64 * 1024 * 1024,
) -> _StableFile:
    if not path.is_relative_to(project_root):
        raise E0037SealedMappingError(f"{label} path escapes project root")
    relative = path.relative_to(project_root)
    safe_path = project_root.joinpath(*relative.parts)
    parent_descriptor, final_name = _open_parent_directory(project_root, relative, label)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(final_name, flags, dir_fd=parent_descriptor)
    except OSError as error:
        os.close(parent_descriptor)
        raise E0037SealedMappingError(f"cannot open {label}: {safe_path}") from error
    chunks: list[bytes] = []
    try:
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                raise E0037SealedMappingError(f"{label} must be a regular file")
            if before.st_size > maximum_size:
                raise E0037SealedMappingError(f"{label} exceeds its bounded read size")
            if expected_size is not None and before.st_size != expected_size:
                raise E0037SealedMappingError(f"{label} size drifted before read")
            remaining = before.st_size
            while remaining:
                block = os.read(descriptor, min(1024 * 1024, remaining))
                if not block:
                    break
                chunks.append(block)
                remaining -= len(block)
            growth_byte = os.read(descriptor, 1)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
    except Exception:
        os.close(parent_descriptor)
        raise
    try:
        final = os.stat(final_name, dir_fd=parent_descriptor, follow_symlinks=False)
    finally:
        os.close(parent_descriptor)
    payload = b"".join(chunks)
    if (
        _stat_identity(before) != _stat_identity(after)
        or _stat_identity(before) != _stat_identity(final)
        or remaining != 0
        or growth_byte
        or len(payload) != before.st_size
    ):
        raise E0037SealedMappingError(f"{label} changed while being read")
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


def _assert_stable_file_unchanged(
    project_root: Path,
    original: _StableFile,
    label: str,
) -> None:
    current = _read_stable_file(
        project_root,
        original.path,
        label,
        expected_size=cast(int, original.artifact["size_bytes"]),
    )
    if current.identity != original.identity or current.artifact != original.artifact:
        raise E0037SealedMappingError(f"{label} changed after validation")


@contextmanager
def _materialize_stable_payloads(
    project_root: Path,
    stable_inputs: Mapping[str, _StableFile],
    names: Sequence[str],
) -> Iterator[dict[str, Path]]:
    """Expose verified bytes through immutable, descriptor-anchored memfds."""

    if len(names) != len(set(names)) or any(name not in stable_inputs for name in names):
        raise E0037SealedMappingError("stable parser materialization set is invalid")
    if not Path("/proc/self/fd").is_dir():
        raise E0037SealedMappingError("immutable descriptor-backed parser inputs are unavailable")
    required_seals = _F_SEAL_SEAL | _F_SEAL_SHRINK | _F_SEAL_GROW | _F_SEAL_WRITE
    descriptors: dict[str, int] = {}
    materialized: dict[str, Path] = {}

    def verify(name: str, descriptor: int) -> None:
        source = stable_inputs[name]
        size = cast(int, source.artifact["size_bytes"])
        status = os.fstat(descriptor)
        chunks: list[bytes] = []
        offset = 0
        while offset < size:
            block = os.pread(descriptor, min(1024 * 1024, size - offset), offset)
            if not block:
                break
            chunks.append(block)
            offset += len(block)
        growth_byte = os.pread(descriptor, 1, size)
        actual_seals = fcntl.fcntl(descriptor, _F_GET_SEALS)
        if (
            not stat.S_ISREG(status.st_mode)
            or status.st_size != size
            or offset != size
            or growth_byte
            or actual_seals & required_seals != required_seals
            or hashlib.sha256(b"".join(chunks)).hexdigest() != source.artifact["sha256"]
        ):
            raise E0037SealedMappingError(
                f"immutable parser input differs from stable bytes: {name}"
            )

    try:
        for name in names:
            source = stable_inputs[name]
            try:
                if hasattr(os, "memfd_create"):
                    descriptor = os.memfd_create(  # type: ignore[attr-defined]
                        f"e0037-{name}",
                        flags=_MFD_ALLOW_SEALING | _MFD_CLOEXEC,
                    )
                else:
                    libc = ctypes.CDLL(None, use_errno=True)
                    memfd_create = libc.memfd_create
                    memfd_create.argtypes = [ctypes.c_char_p, ctypes.c_uint]
                    memfd_create.restype = ctypes.c_int
                    descriptor = memfd_create(
                        f"e0037-{name}".encode("ascii"),
                        _MFD_ALLOW_SEALING | _MFD_CLOEXEC,
                    )
                    if descriptor < 0:
                        error_number = ctypes.get_errno()
                        raise OSError(error_number, os.strerror(error_number))
            except (AttributeError, OSError) as error:
                raise E0037SealedMappingError(
                    f"cannot create immutable parser input: {name}"
                ) from error
            descriptors[name] = descriptor
            try:
                view = memoryview(source.payload)
                while view:
                    written = os.write(descriptor, view)
                    if written <= 0:
                        raise E0037SealedMappingError(
                            f"short write while materializing parser input: {name}"
                        )
                    view = view[written:]
                fcntl.fcntl(descriptor, _F_ADD_SEALS, required_seals)
            except OSError as error:
                raise E0037SealedMappingError(
                    f"cannot seal immutable parser input: {name}"
                ) from error
            verify(name, descriptor)
            materialized[name] = Path(f"/proc/self/fd/{descriptor}")
        yield materialized
        for name, descriptor in descriptors.items():
            verify(name, descriptor)
    finally:
        for descriptor in descriptors.values():
            os.close(descriptor)


def _load_json_bytes(payload: bytes, label: str) -> dict[str, Any]:
    def reject_nonfinite_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON constant: {value}")

    try:
        result = json.loads(
            payload.decode("utf-8"),
            parse_constant=reject_nonfinite_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise E0037SealedMappingError(f"cannot decode {label} as JSON") from error
    if not isinstance(result, dict):
        raise E0037SealedMappingError(f"{label} must be a JSON object")
    return result


def _load_yaml_bytes(payload: bytes, label: str) -> dict[str, Any]:
    try:
        result = yaml.safe_load(payload.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as error:
        raise E0037SealedMappingError(f"cannot decode {label} as YAML") from error
    if not isinstance(result, dict):
        raise E0037SealedMappingError(f"{label} must be a YAML object")
    return result


def _validate_artifact_record(record: object, label: str) -> dict[str, Any]:
    if not isinstance(record, dict) or set(record) != {"path", "size_bytes", "sha256"}:
        raise E0037SealedMappingError(f"{label} identity is invalid")
    path = record.get("path")
    size = record.get("size_bytes")
    digest = record.get("sha256")
    if (
        not isinstance(path, str)
        or not path
        or Path(path).is_absolute()
        or ".." in Path(path).parts
        or not isinstance(size, int)
        or isinstance(size, bool)
        or size < 0
        or not isinstance(digest, str)
        or _SHA256.fullmatch(digest) is None
    ):
        raise E0037SealedMappingError(f"{label} identity is invalid")
    return cast(dict[str, Any], record)


def _validate_exact_registry(
    records: object,
    expected_paths: Mapping[str, Path],
    label: str,
) -> dict[str, dict[str, Any]]:
    """Validate the complete allowlist without opening any registered path."""

    if not isinstance(records, dict) or set(records) != set(expected_paths):
        raise E0037SealedMappingError(f"{label} registry keyset drifted")
    validated: dict[str, dict[str, Any]] = {}
    for name, expected_path in expected_paths.items():
        record = _validate_artifact_record(records[name], f"{label} {name}")
        if record["path"] != expected_path.as_posix():
            raise E0037SealedMappingError(f"{label} {name} path is noncanonical")
        validated[name] = record
    return validated


def _verify_artifact_record(
    project_root: Path,
    record: object,
    label: str,
    *,
    expected_path: Path | None = None,
) -> _StableFile:
    identity = _validate_artifact_record(record, label)
    if expected_path is not None and identity["path"] != expected_path.as_posix():
        raise E0037SealedMappingError(f"{label} path is noncanonical")
    path = _resolve(project_root, identity["path"], label)
    stable = _read_stable_file(
        project_root,
        path,
        label,
        expected_size=cast(int, identity["size_bytes"]),
    )
    if stable.artifact != identity:
        raise E0037SealedMappingError(f"{label} is absent or hash-drifted")
    return stable


def _implementation_artifact(
    project_root: Path,
    record: object,
    label: str,
) -> _StableFile:
    if not isinstance(record, dict) or not isinstance(record.get("path"), str):
        raise E0037SealedMappingError(f"{label} implementation record is invalid")
    path = _resolve(project_root, record["path"], label)
    if set(record) != {"path", "size_bytes", "sha256"}:
        raise E0037SealedMappingError(f"{label} implementation must be hash-pinned")
    _validate_artifact_record(record, label)
    stable = _read_stable_file(
        project_root,
        path,
        label,
        expected_size=cast(int, record["size_bytes"]),
        maximum_size=8 * 1024 * 1024,
    )
    if stable.artifact != record:
        raise E0037SealedMappingError(f"{label} implementation is hash-drifted")
    return stable


def _load_control(
    project_root: Path,
    config_path: Path,
) -> tuple[dict[str, Any], _StableFile]:
    path = _canonical_argument(project_root, config_path, CONTROL_RELATIVE_PATH, "control")
    stable = _read_stable_file(
        project_root,
        path,
        "E-0037 control",
        maximum_size=1024 * 1024,
    )
    control = _load_yaml_bytes(stable.payload, "E-0037 control")
    required_top = {
        "version",
        "experiment_id",
        "dataset_role",
        "design",
        "state",
        "phase_outputs",
        "fixed_cardinality",
        "source_structure_phase",
        "mapping_only_phase",
        "mapping_seal_phase",
        "postjoin_phase",
        "forbidden_mapping_inputs",
        "publication",
        "phase_claim_boundaries",
    }
    if (
        set(control) != required_top
        or control.get("version") != 1
        or control.get("experiment_id") != "E-0037"
        or control.get("dataset_role") != "CALIBRATION"
        or control.get("design")
        != "SOURCE_ONLY_STRUCTURE_THEN_SEALED_MAPPING_THEN_NUMERIC_PERIOD_POSTJOIN"
        or control.get("state") != "READY_FOR_PHASE_SEPARATED_CAPTURE"
    ):
        raise E0037SealedMappingError("E-0037 control identity drifted")
    expected_outputs = {
        "source_structure": (SOURCE_STRUCTURE_RELATIVE_PATH, SOURCE_STRUCTURE_STATE),
        "mapping_only": (MAPPING_ONLY_RELATIVE_PATH, MAPPING_ONLY_STATE),
        "mapping_seal": (MAPPING_SEAL_RELATIVE_PATH, MAPPING_SEAL_STATE),
        "postjoin": (POSTJOIN_RELATIVE_PATH, POSTJOIN_STATE),
    }
    outputs = control.get("phase_outputs")
    if not isinstance(outputs, dict) or set(outputs) != set(expected_outputs):
        raise E0037SealedMappingError("E-0037 canonical phase outputs drifted")
    for name, (expected_path, expected_state) in expected_outputs.items():
        record = outputs.get(name)
        expected_record: dict[str, Any] = {
            "path": expected_path.as_posix(),
            "required_state": expected_state,
        }
        if name == "source_structure":
            expected_record.update(
                {
                    "canonical_payload": {
                        "encoding": "UTF8_JSON_SORTED_KEYS_COMPACT_NO_NAN_V1",
                        "sha256": (
                            "ef098a659f8b557ac3a801edccfc7c0848be9a512b47ba7c9278cd3873f70728"
                        ),
                        "size_bytes": 136042,
                    },
                    "published_bytes_equal_canonical_payload": True,
                }
            )
        if record != expected_record:
            raise E0037SealedMappingError(f"E-0037 {name} output contract drifted")
    cardinality = control.get("fixed_cardinality")
    if cardinality != {
        "page_rows": {3: 39, 4: 25},
        "row_count": 64,
        "schema_disposition_count": 77,
        "period_axis_count_per_page": 2,
        "cell_count": 128,
    }:
        raise E0037SealedMappingError("E-0037 fixed cardinality drifted")
    if control.get("phase_claim_boundaries") != {
        "source_structure": _SOURCE_PHASE_CLAIM_BOUNDARY,
        "mapping_only": _MAPPING_ONLY_CLAIM_BOUNDARY,
        "mapping_seal": _MAPPING_SEAL_CLAIM_BOUNDARY,
        "postjoin": _POSTJOIN_CLAIM_BOUNDARY,
    }:
        raise E0037SealedMappingError("E-0037 phase claim boundaries drifted")
    if control.get("forbidden_mapping_inputs") != [
        "E_0030_period_or_unit_metadata",
        "E_0033_rows_labels_geometry_or_cells",
        "E_0034_numeric_values_signs_blanks_dashes_or_status",
        "human_review_labels_ids_values_or_period_answers",
        "reviewed_reader_evaluation_artifacts",
        "historical_or_mongodb_labels_aliases_ids_or_values",
        "qwen_rejected_raw_output_or_token_stream",
        "numeric_report_norm_id_order",
    ]:
        raise E0037SealedMappingError("E-0037 forbidden mapping input contract drifted")
    if control.get("publication") != {
        "canonical_paths_only": True,
        "atomic_exclusive_no_overwrite": True,
        "clean_git_required_before_and_immediately_before_publication": True,
        "stable_input_identity_recheck_required": True,
        "exact_input_hash_ledger_required": True,
        "one_phase_per_process_required": True,
    }:
        raise E0037SealedMappingError("E-0037 publication gates are incomplete")
    return control, stable


def _phase_output_path(
    project_root: Path,
    control: Mapping[str, Any],
    phase: str,
    supplied: Path,
) -> Path:
    outputs = cast(Mapping[str, Mapping[str, str]], control["phase_outputs"])
    expected = Path(outputs[phase]["path"])
    return _canonical_argument(project_root, supplied, expected, f"{phase} output")


def _encoded_json(
    payload: Mapping[str, Any],
    *,
    canonical_compact: bool,
) -> bytes:
    if canonical_compact:
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def _exclusive_publish_json(
    project_root: Path,
    path: Path,
    payload: Mapping[str, Any],
    *,
    canonical_compact: bool = False,
) -> str:
    """Atomically publish one JSON artifact without replacing any existing path."""

    if not path.is_relative_to(project_root):
        raise E0037SealedMappingError("E-0037 output path escapes project root")
    relative = path.relative_to(project_root)
    parent_descriptor, final_name = _open_or_create_parent_directory(
        project_root,
        relative,
        "E-0037 output",
    )
    encoded = _encoded_json(payload, canonical_compact=canonical_compact)
    expected = hashlib.sha256(encoded).hexdigest()
    temporary_name = f".{final_name}.{secrets.token_hex(16)}"
    temporary_created = False
    try:
        try:
            descriptor = os.open(
                temporary_name,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=parent_descriptor,
            )
            temporary_created = True
        except OSError as error:
            raise E0037SealedMappingError(
                f"cannot create temporary E-0037 artifact: {path}"
            ) from error
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary_name, 0o644, dir_fd=parent_descriptor, follow_symlinks=False)
        temporary_identity = os.stat(
            temporary_name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        try:
            os.link(
                temporary_name,
                final_name,
                src_dir_fd=parent_descriptor,
                dst_dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
        except OSError as error:
            if error.errno == errno.EEXIST:
                raise E0037SealedMappingError(
                    f"refusing to overwrite E-0037 artifact: {path}"
                ) from error
            raise E0037SealedMappingError(f"cannot publish E-0037 artifact: {path}") from error
        os.fsync(parent_descriptor)
        flags = (
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        try:
            published_descriptor = os.open(final_name, flags, dir_fd=parent_descriptor)
        except OSError as error:
            raise E0037SealedMappingError(
                f"cannot verify published E-0037 artifact: {path}"
            ) from error
        chunks: list[bytes] = []
        try:
            before = os.fstat(published_descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_dev != temporary_identity.st_dev
                or before.st_ino != temporary_identity.st_ino
                or before.st_size != len(encoded)
            ):
                raise E0037SealedMappingError(
                    f"published E-0037 artifact identity mismatch: {path}"
                )
            remaining = before.st_size
            while remaining:
                block = os.read(published_descriptor, min(1024 * 1024, remaining))
                if not block:
                    break
                chunks.append(block)
                remaining -= len(block)
            growth_byte = os.read(published_descriptor, 1)
            after = os.fstat(published_descriptor)
        finally:
            os.close(published_descriptor)
        if _stat_identity(before) != _stat_identity(after) or remaining != 0 or growth_byte:
            raise E0037SealedMappingError(
                f"published E-0037 artifact changed during verification: {path}"
            )
        actual = hashlib.sha256(b"".join(chunks)).hexdigest()
        if actual != expected:
            raise E0037SealedMappingError(f"published E-0037 artifact hash mismatch: {path}")
    finally:
        if temporary_created:
            try:
                os.unlink(temporary_name, dir_fd=parent_descriptor)
                os.fsync(parent_descriptor)
            except FileNotFoundError:
                pass
        os.close(parent_descriptor)
    return expected


def _sample_coordinates(sample_id: str) -> tuple[int, int]:
    match = _SAMPLE_ID.fullmatch(sample_id)
    if match is None:
        raise E0037SealedMappingError(f"invalid E-0037 sample identity: {sample_id}")
    return int(match.group("page")), int(match.group("row"))


def _expected_sample_ids() -> list[str]:
    return [
        f"page-{page:04d}-row-{row:03d}-label"
        for page, count in ((3, 39), (4, 25))
        for row in range(count)
    ]


def _to_mapping(value: object, label: str) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        result = value.to_dict()  # type: ignore[union-attr]
    elif is_dataclass(value):
        result = asdict(value)
    elif isinstance(value, Mapping):
        result = dict(value)
    else:
        raise E0037SealedMappingError(f"{label} is not serializable")
    if not isinstance(result, dict):
        raise E0037SealedMappingError(f"{label} must serialize to an object")
    return result


def _verify_phase_records(
    project_root: Path,
    records: object,
    label: str,
) -> dict[str, _StableFile]:
    if not isinstance(records, dict) or not records:
        raise E0037SealedMappingError(f"{label} input registry is invalid")
    return {
        name: _verify_artifact_record(project_root, record, f"{label} {name}")
        for name, record in records.items()
    }


def _validate_e0035_inputs(
    seal: Mapping[str, Any],
    manifest: Mapping[str, Any],
    manifest_record: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if (
        seal.get("experiment_id") != "E-0035"
        or seal.get("status") != _E0035_SEAL_STATUS
        or seal.get("capture_git_dirty") is not False
        or seal.get("crop_manifest") != manifest_record
        or not isinstance(seal.get("gates"), dict)
        or not all(value is True for value in seal["gates"].values())
        or not isinstance(seal.get("reference_isolation"), dict)
        or not all(value is False for value in seal["reference_isolation"].values())
    ):
        raise E0037SealedMappingError("E-0035 seal is incomplete or drifted")
    samples = manifest.get("samples")
    if (
        manifest.get("experiment_id") != "E-0035"
        or manifest.get("state") != _E0035_STATE
        or manifest.get("sample_count") != 64
        or manifest.get("reference_text_available_to_decoder") is not False
        or not isinstance(samples, list)
        or len(samples) != 64
    ):
        raise E0037SealedMappingError("E-0035 crop manifest is incomplete or drifted")
    sample_objects = [cast(dict[str, Any], sample) for sample in samples]
    if not all(isinstance(sample, dict) for sample in sample_objects):
        raise E0037SealedMappingError("E-0035 samples must be objects")
    sample_ids = [sample.get("sample_id") for sample in sample_objects]
    if sample_ids != _expected_sample_ids():
        raise E0037SealedMappingError("E-0035 sample order or identity drifted")
    for sample in sample_objects:
        page, row = _sample_coordinates(cast(str, sample["sample_id"]))
        if (
            sample.get("page") != page
            or sample.get("row_ordinal") != row
            or not isinstance(sample.get("crop_path"), str)
            or not isinstance(sample.get("crop_sha256"), str)
            or _SHA256.fullmatch(cast(str, sample["crop_sha256"])) is None
        ):
            raise E0037SealedMappingError("E-0035 sample geometry identity drifted")
    return sample_objects


def _load_e0035_from_phase(
    project_root: Path,
    phase: Mapping[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    list[dict[str, Any]],
    dict[str, _StableFile],
]:
    raw_records = phase.get("permitted_inputs", phase.get("permitted_frozen_inputs"))
    permitted = _validate_exact_registry(
        raw_records,
        _E0035_EXPECTED_PATHS,
        "E-0037 E-0035",
    )
    stable = _verify_phase_records(project_root, permitted, "E-0037 E-0035")
    seal = _load_json_bytes(stable["e0035_seal"].payload, "E-0035 seal")
    manifest = _load_json_bytes(
        stable["e0035_crop_manifest"].payload,
        "E-0035 crop manifest",
    )
    samples = _validate_e0035_inputs(
        seal,
        manifest,
        stable["e0035_crop_manifest"].artifact,
    )
    return seal, manifest, samples, stable


def capture_e0037_source_structure(
    project_root: Path,
    *,
    config_path: Path = CONTROL_RELATIVE_PATH,
    output_path: Path = SOURCE_STRUCTURE_RELATIVE_PATH,
) -> dict[str, Any]:
    """Publish Seal A without opening schema, review, history, numeric or period inputs."""

    project_root = project_root.resolve()
    commit = _clean_git_commit(project_root)
    control, control_stable = _load_control(project_root, config_path)
    output = _phase_output_path(project_root, control, "source_structure", output_path)
    if output.exists() or output.is_symlink():
        raise E0037SealedMappingError(f"refusing to overwrite E-0037 artifact: {output}")
    phase = control.get("source_structure_phase")
    if (
        not isinstance(phase, dict)
        or phase.get("schema_template_or_history_access_allowed") is not False
    ):
        raise E0037SealedMappingError("E-0037 source-only phase contract drifted")
    _seal, _manifest, _samples, stable_inputs = _load_e0035_from_phase(
        project_root,
        phase,
    )
    implementation = _validate_exact_registry(
        phase.get("implementation"),
        {"source_assembler": Path("src/bctc_ai/evaluation/e0037_evidence_assembly.py")},
        "E-0037 source assembler",
    )
    source_impl = _implementation_artifact(
        project_root,
        implementation["source_assembler"],
        "E-0037 source assembler",
    )

    # Imported only in this phase. The source assembler contract has no schema
    # or mapper argument and returns deterministic source-only evidence.
    from bctc_ai.evaluation.e0037_evidence_assembly import (
        E0037SourceStructureError,
        assemble_source_only_structure,
        validate_source_only_structure,
    )

    result = assemble_source_only_structure(
        project_root,
        e0035_seal_path=Path(
            cast(Mapping[str, Any], phase["permitted_inputs"])["e0035_seal"]["path"]
        ),
    )
    if not isinstance(result, dict):
        raise E0037SealedMappingError("source assembler did not return an object")
    try:
        validate_source_only_structure(result)
    except (E0037SourceStructureError, TypeError, ValueError) as error:
        raise E0037SealedMappingError("source-only structure failed validation") from error
    if result.get("state") != SOURCE_STRUCTURE_STATE:
        raise E0037SealedMappingError("source-only structure state drifted")
    if result.get("claim_boundary") != control["phase_claim_boundaries"]["source_structure"]:
        raise E0037SealedMappingError("source-only claim boundary drifted")
    metrics = result.get("metrics")
    if not isinstance(metrics, dict) or metrics.get("row_count") != 64:
        raise E0037SealedMappingError("source-only structure row count drifted")
    authority = result.get("authority")
    if not isinstance(authority, dict) or any(
        value is not False
        for key, value in authority.items()
        if any(token in key for token in ("schema", "history", "numeric", "period", "review"))
    ):
        raise E0037SealedMappingError("source-only structure claims forbidden authority")

    for name, stable in stable_inputs.items():
        _assert_stable_file_unchanged(project_root, stable, f"E-0037 source input {name}")
    _assert_stable_file_unchanged(project_root, source_impl, "E-0037 source assembler")
    _assert_stable_file_unchanged(project_root, control_stable, "E-0037 control")
    if _clean_git_commit(project_root) != commit:
        raise E0037SealedMappingError("Git commit changed during source-only assembly")
    canonical_source = _encoded_json(result, canonical_compact=True)
    source_output_contract = cast(
        Mapping[str, Any],
        cast(Mapping[str, Any], control["phase_outputs"])["source_structure"],
    )
    canonical_contract = cast(Mapping[str, Any], source_output_contract["canonical_payload"])
    if (
        source_output_contract.get("published_bytes_equal_canonical_payload") is not True
        or len(canonical_source) != canonical_contract["size_bytes"]
        or hashlib.sha256(canonical_source).hexdigest() != canonical_contract["sha256"]
    ):
        raise E0037SealedMappingError("assembled Seal A differs from its committed hash")
    _exclusive_publish_json(project_root, output, result, canonical_compact=True)
    return result


def _validate_request_and_readers(
    request: Mapping[str, Any],
    baseline_seal: Mapping[str, Any],
    reader_payloads: Mapping[str, Mapping[str, Any]],
    stable_inputs: Mapping[str, _StableFile],
) -> tuple[list[str], dict[str, dict[str, str]], dict[str, int]]:
    try:
        request_samples = validate_logical_row_label_reader_request(dict(request))
    except LogicalRowLabelReaderContractError as error:
        raise E0037SealedMappingError(str(error)) from error
    sample_ids = [cast(str, sample["sample_id"]) for sample in request_samples]
    if (
        request.get("state") != _E0036_REQUEST_STATE
        or request.get("sample_count") != 64
        or request.get("reference_text_available_to_reader") is not False
        or sample_ids != _expected_sample_ids()
    ):
        raise E0037SealedMappingError("E-0036 request identity or order drifted")

    readers = baseline_seal.get("readers")
    snapshot = baseline_seal.get("s3_artifact_snapshot")
    if (
        baseline_seal.get("state") != _E0036_BASELINE_SEAL_STATE
        or baseline_seal.get("seal_git_dirty") is not False
        or baseline_seal.get("reference_or_human_review_loaded_by_sealer") is not False
        or baseline_seal.get("evaluation_allowed_only_after_this_seal") is not True
        or baseline_seal.get("same_ordered_sample_ids") is not True
        or baseline_seal.get("sample_count_per_reader") != 64
        or not isinstance(readers, dict)
        or set(readers) != set(_EXPECTED_READERS)
        or not isinstance(snapshot, dict)
        or snapshot.get("restore_verified") is not True
        or snapshot.get("hydrate_probe", {}).get("status") != "PASS"
    ):
        raise E0037SealedMappingError("E-0036 baseline output seal is incomplete")
    if baseline_seal.get("request") != stable_inputs["e0036_request"].artifact:
        raise E0037SealedMappingError("E-0036 request is not the baseline-sealed request")

    labels: dict[str, dict[str, str]] = {sample_id: {} for sample_id in sample_ids}
    proposal_counts: dict[str, int] = {}
    request_by_id = {cast(str, item["sample_id"]): item for item in request_samples}
    for key, (reader_name, proposal_field) in _EXPECTED_READERS.items():
        payload = reader_payloads.get(key)
        seal_reader = readers.get(key)
        if not isinstance(payload, Mapping) or not isinstance(seal_reader, Mapping):
            raise E0037SealedMappingError(f"sealed reader is absent: {key}")
        if seal_reader.get("result") != stable_inputs[f"{key.split('_')[0]}_result"].artifact:
            raise E0037SealedMappingError(f"{key} output is not hash-bound by the baseline seal")
        samples = payload.get("samples")
        authority = payload.get("authority")
        if (
            payload.get("state") != _E0036_READER_STATE
            or payload.get("reader") != reader_name
            or payload.get("sample_count") != 64
            or payload.get("reference_text_available_to_reader") is not False
            or not isinstance(samples, list)
            or len(samples) != 64
            or not isinstance(authority, Mapping)
            or any(value is not False for value in authority.values())
            or seal_reader.get("all_authority_flags") is not False
            or seal_reader.get("human_review_available_to_reader") is not False
        ):
            raise E0037SealedMappingError(f"{key} sealed-reader contract drifted")
        valid_count = 0
        for expected_id, sample in zip(sample_ids, samples, strict=True):
            if not isinstance(sample, Mapping) or sample.get("sample_id") != expected_id:
                raise E0037SealedMappingError(f"{key} sample identity or order drifted")
            request_sample = request_by_id[expected_id]
            if sample.get("crop_path") != request_sample.get("crop_path") or sample.get(
                "crop_sha256"
            ) != request_sample.get("crop_sha256"):
                raise E0037SealedMappingError(f"{key} sample crop identity drifted")
            if key == "deepseek_ocr2" and sample.get("status") != _VALID_DEEPSEEK_STATUS:
                # Rejected raw output is deliberately not copied into labels.
                continue
            proposal = sample.get(proposal_field)
            if not isinstance(proposal, str) or not proposal.strip():
                if key == "vietocr":
                    raise E0037SealedMappingError("VietOCR sealed proposal is empty")
                continue
            labels[expected_id][key] = proposal.strip()
            valid_count += 1
        proposal_counts[key] = valid_count
    if proposal_counts != {"vietocr": 64, "deepseek_ocr2": 51}:
        raise E0037SealedMappingError("sealed valid proposal counts drifted")
    if any("qwen" in reader_labels for reader_labels in labels.values()):
        raise E0037SealedMappingError("rejected Qwen output entered mapping proposals")
    return sample_ids, labels, proposal_counts


def _load_exact_cdkt_projection(
    project_root: Path,
    stable_inputs: Mapping[str, _StableFile],
    parser_paths: Mapping[str, Path],
) -> tuple[Any, dict[str, Any], ScopePolicy]:
    required = {
        "cdkt_workbook",
        "hierarchy_config",
        "cdkt_hierarchy_workbook",
        "scope_policy",
        "mapping_policy",
    }
    if not required.issubset(stable_inputs):
        raise E0037SealedMappingError("exact CDKT projection inputs are incomplete")
    if set(parser_paths) != {
        "cdkt_workbook",
        "cdkt_hierarchy_workbook",
        "scope_policy",
    }:
        raise E0037SealedMappingError("exact CDKT parser materialization set drifted")
    parser_root = parser_paths["cdkt_workbook"].parent
    if any(path.parent != parser_root for path in parser_paths.values()):
        raise E0037SealedMappingError("descriptor-backed parser roots drifted")
    hierarchy_control = _load_yaml_bytes(
        stable_inputs["hierarchy_config"].payload,
        "hierarchy control",
    )
    sources = hierarchy_control.get("sources")
    if (
        hierarchy_control.get("version") != 1
        or hierarchy_control.get("authority") != "USER_SUPPLIED_VST_LEVEL"
        or hierarchy_control.get("root") != "vst_level"
        or not isinstance(sources, dict)
        or not isinstance(sources.get("CDKT"), dict)
    ):
        raise E0037SealedMappingError("CDKT hierarchy control drifted")
    hierarchy_source = cast(dict[str, Any], sources["CDKT"])
    if (
        hierarchy_source.get("path") != "vst_bank_balance_sheet.xlsx"
        or hierarchy_source.get("coverage") != "FULL_STATEMENT"
        or stable_inputs["cdkt_hierarchy_workbook"].artifact["path"]
        != "vst_level/vst_bank_balance_sheet.xlsx"
    ):
        raise E0037SealedMappingError("exact CDKT hierarchy source drifted")

    # CDKT does not use cash-flow rules. Calling the statement-specific loader
    # avoids opening the KQKD/LCTT/TM workbooks that are outside this phase.
    workbook, schema = load_workbook(
        parser_paths["cdkt_workbook"],
        parser_root,
        statement="CDKT",
        cash_flow_rules=cast(Any, None),
    )
    hierarchy_workbook, hierarchy = _load_source(
        parser_paths["cdkt_hierarchy_workbook"],
        parser_root,
        "CDKT",
        hierarchy_source,
    )
    if (
        workbook.item_count != 77
        or workbook.sha256 != stable_inputs["cdkt_workbook"].artifact["sha256"]
        or hierarchy_workbook.item_count != 77
        or hierarchy_workbook.sha256 != stable_inputs["cdkt_hierarchy_workbook"].artifact["sha256"]
        or {item.schema_id for item in schema} != {item.schema_id for item in hierarchy}
    ):
        raise E0037SealedMappingError("exact CDKT workbook/hierarchy coverage drifted")
    if any(item.historical_aliases or item.historical_banks for item in schema):
        raise E0037SealedMappingError("historical aliases entered the exact CDKT projection")
    apply_hierarchy_reference(schema, hierarchy)
    expected_order = list(range(77))
    if [item.display_order for item in schema] != expected_order:
        raise E0037SealedMappingError("CDKT workbook display order is not contiguous")
    workbook_ids = [item.schema_id for item in schema]
    if workbook_ids == sorted(workbook_ids):
        raise E0037SealedMappingError("CDKT projection appears numerically sorted")
    graph = build_schema_graph(schema, "CDKT")
    if (
        len(graph.nodes) != 77
        or [node.schema_id for node in graph.nodes] != workbook_ids
        or [node.display_order for node in graph.nodes] != expected_order
    ):
        raise E0037SealedMappingError("CDKT graph reordered the supplied workbook")
    for item, node in zip(schema, graph.nodes, strict=True):
        allowed_aliases = tuple(
            dict.fromkeys(
                label for label in (item.canonical_name, *item.structural_aliases) if label.strip()
            )
        )
        if node.aliases != allowed_aliases:
            raise E0037SealedMappingError(
                f"CDKT graph alias projection drifted at {item.schema_id}"
            )

    from bctc_ai.mapping.ordered_subgraph_v2 import build_schema_projection_v2

    projection_v2 = build_schema_projection_v2(schema, "CDKT")
    if (
        len(projection_v2.nodes) != 77
        or [node.report_norm_id for node in projection_v2.nodes] != workbook_ids
        or [node.display_order for node in projection_v2.nodes] != expected_order
        or projection_v2.alias_authority != "CANONICAL_AND_STRUCTURAL_ALIASES_ONLY"
    ):
        raise E0037SealedMappingError("history-free CDKT v2 projection drifted")

    scope_policy = load_scope_policy(parser_paths["scope_policy"])
    if (
        scope_policy.version != 1
        or len(scope_policy.rules) != 1
        or scope_policy.rules[0].statement_type != "CDKT"
        or scope_policy.rules[0].action != "DO_NOT_MAP_TO_CDKT"
    ):
        raise E0037SealedMappingError("CDKT mapping scope policy drifted")
    for name in required:
        _assert_stable_file_unchanged(
            project_root,
            stable_inputs[name],
            f"E-0037 exact projection input {name}",
        )
    projection = {
        "statement_type": "CDKT",
        "node_count": 77,
        "projection_sha256": projection_v2.projection_sha256,
        "alias_authority": projection_v2.alias_authority,
        "graph_sha256": graph.graph_sha256,
        "order_authority": "WORKBOOK_DISPLAY_ORDER_ONLY",
        "numeric_report_norm_id_sort_used": False,
        "historical_alias_count": 0,
        "workbook": stable_inputs["cdkt_workbook"].artifact,
        "hierarchy_config": stable_inputs["hierarchy_config"].artifact,
        "hierarchy_workbook": stable_inputs["cdkt_hierarchy_workbook"].artifact,
        "scope_policy": stable_inputs["scope_policy"].artifact,
        "mapping_policy": stable_inputs["mapping_policy"].artifact,
        "nodes": [
            {
                "display_order": node.display_order,
                "report_norm_id": node.schema_id,
                "display_name": node.canonical_name,
                "structural_aliases": list(projected.structural_aliases),
                "parent_report_norm_id": projected.parent_report_norm_id,
                "child_report_norm_ids": list(projected.child_report_norm_ids),
                "hierarchy_level": projected.hierarchy_level,
                "section_path": list(projected.section_path),
                "scopes": list(projected.scopes),
                "previous_report_norm_id": node.previous_id,
                "next_report_norm_id": node.next_id,
            }
            for node, projected in zip(graph.nodes, projection_v2.nodes, strict=True)
        ],
    }
    return projection_v2, projection, scope_policy


def _mapping_is_accepted(status: object) -> bool:
    return isinstance(status, str) and status in _ACCEPTED_MAPPING_STATUSES


def _validate_mapping_row_evidence(
    row: Mapping[str, Any],
    expected_id: str,
    expected_order: int,
    mapping_status: str,
) -> None:
    if set(row) != {
        "row_id",
        "page",
        "row_ordinal",
        "source_order",
        "source_structure",
        "semantic_proposals",
        "mapping",
    }:
        raise E0037SealedMappingError(f"mapping row evidence keyset drifted for {expected_id}")
    page, row_ordinal = _sample_coordinates(expected_id)
    if (
        row.get("page") != page
        or row.get("row_ordinal") != row_ordinal
        or row.get("source_order") != expected_order
    ):
        raise E0037SealedMappingError(f"mapping row source identity drifted for {expected_id}")
    structure = row.get("source_structure")
    if not isinstance(structure, dict) or set(structure) != {
        "row_role",
        "source_relation_type",
        "mapper_relation_type",
        "physical_parent_row_id",
        "physical_section_id",
        "child_set_complete",
        "typography_role",
        "report_scope",
        "target_template_in_scope",
        "scope_policy_reason",
    }:
        raise E0037SealedMappingError(
            f"mapping row source structure keyset drifted for {expected_id}"
        )
    physical_parent = structure.get("physical_parent_row_id")
    section_parent = structure.get("physical_section_id")
    previous_ids = set(_expected_sample_ids()[:expected_order])
    if (
        structure.get("row_role") not in {"UNKNOWN", "DETAIL", "GROUP", "TOTAL", "SECTION"}
        or structure.get("typography_role")
        not in {"BOLD_ITALIC", "BOLD_UPRIGHT", "REGULAR_ITALIC", "REGULAR_UPRIGHT"}
        or structure.get("child_set_complete") != "UNKNOWN"
        or structure.get("report_scope") != "UNKNOWN"
        or not isinstance(structure.get("target_template_in_scope"), bool)
        or not isinstance(structure.get("scope_policy_reason"), str)
        or not structure["scope_policy_reason"]
        or (physical_parent is not None and physical_parent not in previous_ids)
        or (section_parent is not None and section_parent not in previous_ids)
    ):
        raise E0037SealedMappingError(
            f"mapping row source structure value drifted for {expected_id}"
        )
    if physical_parent is not None:
        expected_source_relation = "PHYSICAL_PARENT"
        expected_mapper_relation = "DIRECT_PARENT"
    elif section_parent is not None:
        expected_source_relation = "SECTION_MEMBER"
        expected_mapper_relation = "UNKNOWN"
    else:
        expected_source_relation = "NONE"
        expected_mapper_relation = "UNKNOWN"
    if (
        structure.get("source_relation_type") != expected_source_relation
        or structure.get("mapper_relation_type") != expected_mapper_relation
        or (mapping_status == "OUT_OF_SCOPE_FOR_TARGET_TEMPLATE")
        is structure["target_template_in_scope"]
    ):
        raise E0037SealedMappingError(
            f"mapping row relation/scope linkage drifted for {expected_id}"
        )
    proposals = row.get("semantic_proposals")
    if (
        not isinstance(proposals, dict)
        or not {"vietocr", "ppocrv6_source"}.issubset(proposals)
        or not set(proposals).issubset({"vietocr", "deepseek_ocr2", "ppocrv6_source"})
        or any(not isinstance(value, str) or not value.strip() for value in proposals.values())
    ):
        raise E0037SealedMappingError(
            f"mapping row semantic proposal firewall drifted for {expected_id}"
        )


def _validate_mapping_rows(
    rows: object,
    schema_dispositions: object,
    *,
    expected_graph_ids: Sequence[int] | None = None,
    require_evidence: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(rows, list) or len(rows) != 64:
        raise E0037SealedMappingError("mapping-only output must contain exactly 64 rows")
    row_objects: list[dict[str, Any]] = []
    allowed_row_statuses = {
        "RESOLVED_ANCHOR",
        "RESOLVED_PATH",
        "NO_ADMISSIBLE_PAIR",
        "BEST_PATH_SKIPPED",
        "AMBIGUOUS_ACROSS_PATHS",
        "OUT_OF_SCOPE_FOR_TARGET_TEMPLATE",
    }
    for expected_order, (expected_id, raw_row) in enumerate(
        zip(_expected_sample_ids(), rows, strict=True)
    ):
        if not isinstance(raw_row, dict) or raw_row.get("row_id") != expected_id:
            raise E0037SealedMappingError("mapping row identity or order drifted")
        mapping = raw_row.get("mapping")
        if not isinstance(mapping, dict) or set(mapping) != {
            "row_id",
            "status",
            "selected_report_norm_id",
            "candidate_report_norm_ids",
            "interval_index",
            "reason",
        }:
            raise E0037SealedMappingError(f"mapping disposition is absent for {expected_id}")
        status = mapping.get("status")
        selected = mapping.get("selected_report_norm_id")
        candidates = mapping.get("candidate_report_norm_ids")
        if (
            mapping.get("row_id") != expected_id
            or status not in allowed_row_statuses
            or not isinstance(mapping.get("reason"), str)
            or not mapping["reason"]
            or (
                mapping.get("interval_index") is not None
                and (
                    not isinstance(mapping["interval_index"], int)
                    or isinstance(mapping["interval_index"], bool)
                    or mapping["interval_index"] < 0
                )
            )
            or not isinstance(candidates, list)
            or any(not isinstance(value, int) or isinstance(value, bool) for value in candidates)
        ):
            raise E0037SealedMappingError(f"mapping candidate contract drifted for {expected_id}")
        if len(candidates) != len(set(candidates)):
            raise E0037SealedMappingError(f"duplicate mapping candidates for {expected_id}")
        if _mapping_is_accepted(status):
            if (
                not isinstance(selected, int)
                or isinstance(selected, bool)
                or selected not in candidates
            ):
                raise E0037SealedMappingError(
                    f"accepted row has no selected candidate: {expected_id}"
                )
        elif selected is not None:
            raise E0037SealedMappingError(
                f"non-accepted row leaked a selected ReportNormId: {expected_id}"
            )
        if "AMBIGUOUS" in status and not candidates:
            raise E0037SealedMappingError(
                f"ambiguous row did not preserve candidates: {expected_id}"
            )
        if expected_graph_ids is not None and any(
            candidate not in expected_graph_ids for candidate in candidates
        ):
            raise E0037SealedMappingError(f"mapping candidate is outside CDKT: {expected_id}")
        if require_evidence:
            _validate_mapping_row_evidence(
                raw_row,
                expected_id,
                expected_order,
                cast(str, status),
            )
        row_objects.append(raw_row)

    if not isinstance(schema_dispositions, list) or len(schema_dispositions) != 77:
        raise E0037SealedMappingError(
            "mapping-only output must contain exactly 77 schema dispositions"
        )
    schema_objects: list[dict[str, Any]] = []
    schema_ids: list[int] = []
    allowed_schema_statuses = {
        "MAPPED",
        "AMBIGUOUS_ACROSS_PATHS",
        "UNMATCHED_SCHEMA_NODE_WITH_SKIPPED_CANDIDATES",
        "UNMATCHED_SCHEMA_NODE",
    }
    for raw_disposition in schema_dispositions:
        if not isinstance(raw_disposition, dict) or set(raw_disposition) != {
            "report_norm_id",
            "status",
            "selected_row_id",
            "candidate_row_ids",
            "reason",
        }:
            raise E0037SealedMappingError("schema disposition must be an object")
        schema_id = raw_disposition.get("report_norm_id")
        candidate_rows = raw_disposition.get("candidate_row_ids")
        selected_row = raw_disposition.get("selected_row_id")
        if (
            not isinstance(schema_id, int)
            or isinstance(schema_id, bool)
            or raw_disposition.get("status") not in allowed_schema_statuses
            or not isinstance(candidate_rows, list)
            or len(candidate_rows) != len(set(candidate_rows))
            or any(row_id not in _expected_sample_ids() for row_id in candidate_rows)
            or (selected_row is not None and selected_row not in _expected_sample_ids())
            or not isinstance(raw_disposition.get("reason"), str)
            or not raw_disposition["reason"]
        ):
            raise E0037SealedMappingError("schema disposition has invalid ReportNormId")
        if raw_disposition["status"] == "MAPPED":
            if selected_row is None or selected_row not in candidate_rows:
                raise E0037SealedMappingError("mapped schema disposition has no selected row")
        elif selected_row is not None:
            raise E0037SealedMappingError("unmapped schema disposition leaked a selected row")
        schema_ids.append(schema_id)
        schema_objects.append(raw_disposition)
    if len(schema_ids) != len(set(schema_ids)):
        raise E0037SealedMappingError("schema dispositions contain duplicate ReportNormIds")
    if expected_graph_ids is not None and schema_ids != list(expected_graph_ids):
        raise E0037SealedMappingError(
            "schema dispositions do not follow exact workbook display order"
        )
    accepted_ids = [
        cast(int, row["mapping"]["selected_report_norm_id"])
        for row in row_objects
        if _mapping_is_accepted(row["mapping"]["status"])
    ]
    if len(accepted_ids) != len(set(accepted_ids)):
        raise E0037SealedMappingError("multiple accepted rows select one ReportNormId")
    rows_by_id = {row["row_id"]: row for row in row_objects}
    schema_by_id = {disposition["report_norm_id"]: disposition for disposition in schema_objects}
    for row in row_objects:
        for schema_id in row["mapping"]["candidate_report_norm_ids"]:
            if row["row_id"] not in schema_by_id[schema_id]["candidate_row_ids"]:
                raise E0037SealedMappingError("row/schema candidate linkage drifted")
        selected = row["mapping"]["selected_report_norm_id"]
        if selected is not None:
            disposition = schema_by_id[selected]
            if disposition["status"] != "MAPPED" or disposition["selected_row_id"] != row["row_id"]:
                raise E0037SealedMappingError("row/schema selected linkage drifted")
    for disposition in schema_objects:
        schema_id = disposition["report_norm_id"]
        expected_candidates = [
            row_id
            for row_id, row in rows_by_id.items()
            if schema_id in row["mapping"]["candidate_report_norm_ids"]
        ]
        if disposition["candidate_row_ids"] != expected_candidates:
            raise E0037SealedMappingError("schema/row candidate linkage drifted")
    return row_objects, schema_objects


def _jsonable(value: object) -> Any:
    try:
        return json.loads(json.dumps(value, ensure_ascii=False))
    except (TypeError, ValueError) as error:
        raise E0037SealedMappingError("E-0037 result is not JSON serializable") from error


def _source_row_id(row: Mapping[str, Any]) -> str:
    value = row.get("row_id", row.get("sample_id"))
    if not isinstance(value, str):
        raise E0037SealedMappingError("source-only row has no stable row identity")
    _sample_coordinates(value)
    return value


def _source_row_order(row: Mapping[str, Any]) -> int:
    value = row.get("source_order", row.get("order"))
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise E0037SealedMappingError("source-only row has no stable source order")
    return value


def _source_row_field(
    row: Mapping[str, Any],
    *names: str,
    default: object = None,
) -> object:
    for name in names:
        if name in row:
            return row[name]
    return default


def _build_mapper_rows(
    source_payload: Mapping[str, Any],
    sample_ids: Sequence[str],
    reader_labels: Mapping[str, Mapping[str, str]],
    scope_policy: ScopePolicy,
) -> tuple[list[Any], list[dict[str, Any]], dict[str, int]]:
    raw_rows = source_payload.get("rows")
    if not isinstance(raw_rows, list) or len(raw_rows) != 64:
        raise E0037SealedMappingError("Seal A must contain exactly 64 source rows")
    source_rows = [cast(dict[str, Any], row) for row in raw_rows]
    if not all(isinstance(row, dict) for row in source_rows):
        raise E0037SealedMappingError("Seal A source rows must be objects")
    source_ids = [_source_row_id(row) for row in source_rows]
    if source_ids != list(sample_ids):
        raise E0037SealedMappingError("Seal A row identity or order differs from E-0036")
    if [_source_row_order(row) for row in source_rows] != list(range(64)):
        raise E0037SealedMappingError("Seal A source order is not contiguous")

    raw_edges = source_payload.get("edges")
    if not isinstance(raw_edges, list):
        raise E0037SealedMappingError("Seal A structural edges are absent")
    edge_by_child_and_type: dict[tuple[str, str], str] = {}
    for edge in raw_edges:
        if not isinstance(edge, dict):
            raise E0037SealedMappingError("Seal A structural edge must be an object")
        parent = edge.get("parent_row_id")
        child = edge.get("child_row_id")
        relation = edge.get("relation_type")
        if (
            not isinstance(parent, str)
            or not isinstance(child, str)
            or relation not in {"PHYSICAL_PARENT", "SECTION_MEMBER"}
            or (child, cast(str, relation)) in edge_by_child_and_type
        ):
            raise E0037SealedMappingError("Seal A structural edge contract drifted")
        edge_by_child_and_type[(child, cast(str, relation))] = parent

    from bctc_ai.mapping.ordered_subgraph_v2 import SourceStructureRowV2

    primary_labels = [cast(str, reader_labels[row_id].get("vietocr", "")) for row_id in source_ids]
    scope_decisions = classify_mapping_scopes(
        [("CDKT", label) for label in primary_labels],
        scope_policy,
    )
    mapper_rows: list[SourceStructureRowV2] = []
    evidence_rows: list[dict[str, Any]] = []
    role_counts: Counter[str] = Counter()
    for row, row_id, scope_decision in zip(
        source_rows,
        source_ids,
        scope_decisions,
        strict=True,
    ):
        page, row_ordinal = _sample_coordinates(row_id)
        if row.get("page") != page or row.get("row_ordinal") != row_ordinal:
            raise E0037SealedMappingError(f"Seal A page/row binding drifted for {row_id}")
        labels = dict(reader_labels[row_id])
        raw_ppocr = _source_row_field(
            row,
            "raw_ppocr_label",
            "ppocr_text",
            "raw_label",
            default="",
        )
        if isinstance(raw_ppocr, str) and raw_ppocr.strip():
            labels["ppocrv6_source"] = raw_ppocr.strip()
        if not labels or "qwen" in labels:
            raise E0037SealedMappingError(f"invalid semantic proposal set for {row_id}")
        row_role = _source_row_field(
            row,
            "row_role",
            "typography_role",
            default="UNKNOWN",
        )
        physical_parent = _source_row_field(row, "physical_parent_row_id")
        section_parent = _source_row_field(row, "section_row_id")
        if physical_parent is not None:
            parent_row_id = physical_parent
            source_relation_type = "PHYSICAL_PARENT"
            mapper_relation_type = "DIRECT_PARENT"
        elif section_parent is not None:
            parent_row_id = None
            source_relation_type = "SECTION_MEMBER"
            mapper_relation_type = "UNKNOWN"
        else:
            parent_row_id = None
            source_relation_type = "NONE"
            mapper_relation_type = "UNKNOWN"
        if edge_by_child_and_type.get((row_id, "PHYSICAL_PARENT")) != physical_parent:
            raise E0037SealedMappingError(f"Seal A physical-parent edge drifted for {row_id}")
        if edge_by_child_and_type.get((row_id, "SECTION_MEMBER")) != section_parent:
            raise E0037SealedMappingError(f"Seal A section edge drifted for {row_id}")
        # Seal A intentionally has no authority to infer consolidated/separate
        # scope. The mapper therefore receives UNKNOWN, never the filename.
        report_scope = "UNKNOWN"
        if not isinstance(row_role, str):
            raise E0037SealedMappingError(f"Seal A structural enums drifted for {row_id}")
        if parent_row_id is not None and parent_row_id not in source_ids:
            raise E0037SealedMappingError(f"Seal A parent is unknown for {row_id}")
        if not isinstance(report_scope, str):
            raise E0037SealedMappingError(f"Seal A report scope drifted for {row_id}")
        source_in_scope = _source_row_field(
            row,
            "target_template_in_scope",
            default=True,
        )
        if not isinstance(source_in_scope, bool):
            raise E0037SealedMappingError(f"Seal A target-scope flag drifted for {row_id}")
        target_in_scope = source_in_scope and scope_decision.allowed
        role_counts[row_role] += 1
        mapper_rows.append(
            SourceStructureRowV2(
                row_id=row_id,
                order=_source_row_order(row),
                labels_by_reader=labels,
                row_role=row_role,
                parent_row_id=cast(str | None, parent_row_id),
                relation_type=mapper_relation_type,
                report_scope=report_scope,
                target_template_in_scope=target_in_scope,
            )
        )
        evidence_rows.append(
            {
                "row_id": row_id,
                "page": page,
                "row_ordinal": row_ordinal,
                "source_order": _source_row_order(row),
                "source_structure": {
                    "row_role": row_role,
                    "source_relation_type": source_relation_type,
                    "mapper_relation_type": mapper_relation_type,
                    "physical_parent_row_id": physical_parent,
                    "physical_section_id": section_parent,
                    "child_set_complete": _source_row_field(
                        row,
                        "child_set_complete",
                        default="UNKNOWN",
                    ),
                    "typography_role": _source_row_field(
                        row,
                        "typography_role",
                        default="UNKNOWN",
                    ),
                    "report_scope": report_scope,
                    "target_template_in_scope": target_in_scope,
                    "scope_policy_reason": scope_decision.reason,
                },
                "semantic_proposals": labels,
            }
        )
    return mapper_rows, evidence_rows, dict(sorted(role_counts.items()))


def capture_e0037_mapping_only(
    project_root: Path,
    *,
    config_path: Path = CONTROL_RELATIVE_PATH,
    source_structure_path: Path = SOURCE_STRUCTURE_RELATIVE_PATH,
    output_path: Path = MAPPING_ONLY_RELATIVE_PATH,
    _authentication_replay: bool = False,
) -> dict[str, Any]:
    """Run the mapper once without opening any period, numeric, review or history artifact."""

    project_root = project_root.resolve()
    commit = _clean_git_commit(project_root)
    control, control_stable = _load_control(project_root, config_path)
    output = _phase_output_path(project_root, control, "mapping_only", output_path)
    source_path = _canonical_argument(
        project_root,
        source_structure_path,
        SOURCE_STRUCTURE_RELATIVE_PATH,
        "source structure",
    )
    if not isinstance(_authentication_replay, bool):
        raise E0037SealedMappingError("invalid mapping authentication replay flag")
    if not _authentication_replay and (output.exists() or output.is_symlink()):
        raise E0037SealedMappingError(f"refusing to overwrite E-0037 artifact: {output}")
    phase = control.get("mapping_only_phase")
    if not isinstance(phase, dict):
        raise E0037SealedMappingError("E-0037 mapping-only phase contract drifted")
    schema_contract = phase.get("exact_schema_projection")
    if schema_contract != {
        "statement_type": "CDKT",
        "node_count": 77,
        "order_authority": "WORKBOOK_DISPLAY_ORDER_ONLY",
        "numeric_report_norm_id_sort_allowed": False,
        "historical_aliases_allowed": False,
        "projection_sha256": "7025ca729c01a3f2030af38e9745a0ee8d72b1dad60c8d4e3b7cf749e5eb860c",
    }:
        raise E0037SealedMappingError("E-0037 exact schema projection contract drifted")
    source_contract = cast(
        Mapping[str, Any],
        cast(Mapping[str, Any], control["phase_outputs"])["source_structure"],
    )
    source_stable = _read_stable_file(
        project_root,
        source_path,
        "E-0037 Seal A",
        expected_size=cast(int, source_contract["canonical_payload"]["size_bytes"]),
        maximum_size=1024 * 1024,
    )
    if source_stable.artifact != {
        "path": source_contract["path"],
        "size_bytes": source_contract["canonical_payload"]["size_bytes"],
        "sha256": source_contract["canonical_payload"]["sha256"],
    }:
        raise E0037SealedMappingError("E-0037 Seal A differs from its committed identity")
    implementation = _validate_exact_registry(
        phase.get("implementation"),
        _MAPPING_IMPLEMENTATION_EXPECTED_PATHS,
        "E-0037 mapping-only implementation",
    )
    implementation_stable = {
        name: _implementation_artifact(
            project_root,
            record,
            f"E-0037 implementation {name}",
        )
        for name, record in implementation.items()
    }
    source_payload = _load_json_bytes(source_stable.payload, "E-0037 Seal A")
    from bctc_ai.evaluation.e0037_evidence_assembly import (
        E0037SourceStructureError,
        validate_source_only_structure,
    )

    try:
        validate_source_only_structure(source_payload)
    except (E0037SourceStructureError, TypeError, ValueError) as error:
        raise E0037SealedMappingError("E-0037 Seal A failed validation") from error
    if source_payload.get("state") != SOURCE_STRUCTURE_STATE:
        raise E0037SealedMappingError("E-0037 Seal A state drifted")

    # Only after the exact committed Seal A bytes pass may schema policy and
    # reader inputs be opened.
    permitted = _validate_exact_registry(
        phase.get("permitted_frozen_inputs"),
        _MAPPING_INPUT_EXPECTED_PATHS,
        "E-0037 mapping-only input",
    )
    stable_inputs = _verify_phase_records(
        project_root,
        permitted,
        "E-0037 mapping-only",
    )

    e0035_seal = _load_json_bytes(stable_inputs["e0035_seal"].payload, "E-0035 seal")
    crop_manifest = _load_json_bytes(
        stable_inputs["e0035_crop_manifest"].payload,
        "E-0035 crop manifest",
    )
    crop_samples = _validate_e0035_inputs(
        e0035_seal,
        crop_manifest,
        stable_inputs["e0035_crop_manifest"].artifact,
    )
    request = _load_json_bytes(stable_inputs["e0036_request"].payload, "E-0036 request")
    baseline_seal = _load_json_bytes(
        stable_inputs["e0036_baseline_output_seal"].payload,
        "E-0036 baseline output seal",
    )
    reader_payloads = {
        "vietocr": _load_json_bytes(
            stable_inputs["vietocr_result"].payload,
            "sealed VietOCR result",
        ),
        "deepseek_ocr2": _load_json_bytes(
            stable_inputs["deepseek_result"].payload,
            "sealed DeepSeek result",
        ),
    }
    sample_ids, reader_labels, proposal_counts = _validate_request_and_readers(
        request,
        baseline_seal,
        reader_payloads,
        stable_inputs,
    )
    if [sample["sample_id"] for sample in crop_samples] != sample_ids:
        raise E0037SealedMappingError("E-0035/E-0036 ordered sample identity drifted")

    parser_input_names = (
        "cdkt_workbook",
        "cdkt_hierarchy_workbook",
        "scope_policy",
    )
    with _materialize_stable_payloads(
        project_root,
        stable_inputs,
        parser_input_names,
    ) as parser_paths:
        schema_projection, projection, scope_policy = _load_exact_cdkt_projection(
            project_root,
            stable_inputs,
            parser_paths,
        )
        if projection["projection_sha256"] != schema_contract["projection_sha256"]:
            raise E0037SealedMappingError("CDKT projection differs from the committed digest")
        mapper_rows, evidence_rows, role_counts = _build_mapper_rows(
            source_payload,
            sample_ids,
            reader_labels,
            scope_policy,
        )
        from bctc_ai.mapping.ordered_subgraph_v2 import (
            align_ordered_subgraph_v2,
            load_ordered_subgraph_v2_policy_bytes,
        )

        policy = load_ordered_subgraph_v2_policy_bytes(
            stable_inputs["mapping_policy"].payload,
            source_path=Path(stable_inputs["mapping_policy"].artifact["path"]),
        )
        result = align_ordered_subgraph_v2(mapper_rows, schema_projection, policy=policy)
    result_payload = cast(dict[str, Any], _jsonable(_to_mapping(result, "mapping result")))
    if (
        result_payload.get("schema_projection_sha256") != schema_projection.projection_sha256
        or result_payload.get("schema_alias_authority") != "CANONICAL_AND_STRUCTURAL_ALIASES_ONLY"
        or result_payload.get("policy_sha256") != stable_inputs["mapping_policy"].artifact["sha256"]
    ):
        raise E0037SealedMappingError("mapper returned a different CDKT projection identity")
    raw_row_mappings = result_payload.pop("row_mappings", None)
    raw_schema_dispositions = result_payload.pop("schema_dispositions", None)
    if not isinstance(raw_row_mappings, list) or len(raw_row_mappings) != 64:
        raise E0037SealedMappingError("mapper did not return one mapping per source row")
    by_row_id = {
        mapping.get("row_id"): mapping for mapping in raw_row_mappings if isinstance(mapping, dict)
    }
    if list(by_row_id) != sample_ids:
        raise E0037SealedMappingError("mapper row disposition identity or order drifted")
    rows = [
        {**evidence, "mapping": cast(dict[str, Any], by_row_id[evidence["row_id"]])}
        for evidence in evidence_rows
    ]
    graph_ids = [node.report_norm_id for node in schema_projection.nodes]
    rows, schema_dispositions = _validate_mapping_rows(
        rows,
        raw_schema_dispositions,
        expected_graph_ids=graph_ids,
        require_evidence=True,
    )
    accepted_count = sum(_mapping_is_accepted(row["mapping"]["status"]) for row in rows)
    ambiguous_count = sum("AMBIGUOUS" in row["mapping"]["status"] for row in rows)
    input_ledger = {
        "control": control_stable.artifact,
        "source_structure": source_stable.artifact,
        **{name: stable.artifact for name, stable in stable_inputs.items()},
    }
    payload = {
        "format_version": 1,
        "experiment_id": "E-0037",
        "dataset_role": "CALIBRATION",
        "state": MAPPING_ONLY_STATE,
        "capture_git_commit": commit,
        "capture_git_dirty": False,
        "source_structure": source_stable.artifact,
        "input_hash_ledger": input_ledger,
        "implementation_hash_ledger": {
            name: stable.artifact for name, stable in implementation_stable.items()
        },
        "access_contract": {
            "mapping_function_invocation_count": 1,
            "source_structure_opened": True,
            "e0035_and_e0036_sealed_label_evidence_opened": True,
            "exact_cdkt_workbook_hierarchy_scope_policy_opened": True,
            "e0030_opened": False,
            "e0033_opened": False,
            "e0034_opened": False,
            "review_or_history_opened": False,
            "qwen_result_or_rejected_raw_output_opened": False,
            "numeric_or_period_features_passed_to_mapper": False,
        },
        "schema_projection": projection,
        "semantic_proposals": {
            "valid_proposal_counts": proposal_counts,
            "qwen_proposal_count": 0,
            "rejected_raw_output_proposal_count": 0,
        },
        "mapping": result_payload,
        "rows": rows,
        "schema_dispositions": schema_dispositions,
        "metrics": {
            "row_count": 64,
            "schema_disposition_count": 77,
            "accepted_row_count": accepted_count,
            "ambiguous_row_count": ambiguous_count,
            "unselected_row_count": 64 - accepted_count,
            "source_row_role_counts": role_counts,
        },
        "authority": {
            "seal_a_is_bounded_structure_evidence_authority": True,
            "font_weight_slant_from_pixels_case_and_lexical_roles_from_e0035_provenance": True,
            "workbook_display_order_is_schema_order_authority": True,
            "semantic_readers_are_label_proposals_only": True,
            "numeric_value_or_status_authority": False,
            "period_or_unit_authority": False,
            "review_or_history_authority": False,
            "ambiguous_best_path_may_select_report_norm_id": False,
        },
        "claim_boundary": control["phase_claim_boundaries"]["mapping_only"],
    }

    for name, stable in stable_inputs.items():
        _assert_stable_file_unchanged(project_root, stable, f"mapping-only input {name}")
    for name, stable in implementation_stable.items():
        _assert_stable_file_unchanged(project_root, stable, f"implementation {name}")
    _assert_stable_file_unchanged(project_root, source_stable, "E-0037 Seal A")
    _assert_stable_file_unchanged(project_root, control_stable, "E-0037 control")
    if _clean_git_commit(project_root) != commit:
        raise E0037SealedMappingError("Git commit changed during mapping-only capture")
    if not _authentication_replay:
        _exclusive_publish_json(project_root, output, payload)
    return payload


def _validated_projection_ids(projection: object) -> list[int]:
    if not isinstance(projection, dict) or set(projection) != {
        "statement_type",
        "node_count",
        "projection_sha256",
        "alias_authority",
        "graph_sha256",
        "order_authority",
        "numeric_report_norm_id_sort_used",
        "historical_alias_count",
        "workbook",
        "hierarchy_config",
        "hierarchy_workbook",
        "scope_policy",
        "mapping_policy",
        "nodes",
    }:
        raise E0037SealedMappingError("mapping-only schema projection keyset drifted")
    if (
        projection.get("statement_type") != "CDKT"
        or projection.get("node_count") != 77
        or projection.get("order_authority") != "WORKBOOK_DISPLAY_ORDER_ONLY"
        or projection.get("numeric_report_norm_id_sort_used") is not False
        or projection.get("historical_alias_count") != 0
        or projection.get("alias_authority") != "CANONICAL_AND_STRUCTURAL_ALIASES_ONLY"
        or _SHA256.fullmatch(str(projection.get("graph_sha256", ""))) is None
        or not isinstance(projection.get("nodes"), list)
        or len(projection["nodes"]) != 77
    ):
        raise E0037SealedMappingError("mapping-only schema projection drifted")
    for name in (
        "workbook",
        "hierarchy_config",
        "hierarchy_workbook",
        "scope_policy",
        "mapping_policy",
    ):
        _validate_artifact_record(projection[name], f"mapping-only projection {name}")

    node_keys = {
        "display_order",
        "report_norm_id",
        "display_name",
        "structural_aliases",
        "parent_report_norm_id",
        "child_report_norm_ids",
        "hierarchy_level",
        "section_path",
        "scopes",
        "previous_report_norm_id",
        "next_report_norm_id",
    }
    nodes = cast(list[dict[str, Any]], projection["nodes"])
    projection_ids: list[int] = []
    serialized: list[dict[str, Any]] = []
    for expected_order, node in enumerate(nodes):
        if not isinstance(node, dict) or set(node) != node_keys:
            raise E0037SealedMappingError("mapping-only schema node keyset drifted")
        schema_id = node.get("report_norm_id")
        display_name = node.get("display_name")
        aliases = node.get("structural_aliases")
        parent = node.get("parent_report_norm_id")
        children = node.get("child_report_norm_ids")
        level = node.get("hierarchy_level")
        section_path = node.get("section_path")
        scopes = node.get("scopes")
        if (
            node.get("display_order") != expected_order
            or not isinstance(schema_id, int)
            or isinstance(schema_id, bool)
            or not isinstance(display_name, str)
            or not display_name.strip()
            or not isinstance(aliases, list)
            or any(not isinstance(alias, str) or not alias.strip() for alias in aliases)
            or len(aliases) != len(set(aliases))
            or (parent is not None and (not isinstance(parent, int) or isinstance(parent, bool)))
            or not isinstance(children, list)
            or any(not isinstance(child, int) or isinstance(child, bool) for child in children)
            or len(children) != len(set(children))
            or (level is not None and (not isinstance(level, int) or isinstance(level, bool)))
            or not isinstance(section_path, list)
            or not section_path
            or any(
                not isinstance(path_id, int) or isinstance(path_id, bool)
                for path_id in section_path
            )
            or section_path[-1] != schema_id
            or scopes != ["SEPARATE", "CONSOLIDATED"]
        ):
            raise E0037SealedMappingError("mapping-only schema node value drifted")
        projection_ids.append(schema_id)
        serialized.append(
            {
                "report_norm_id": schema_id,
                "canonical_name": display_name,
                "structural_aliases": aliases,
                "statement_type": "CDKT",
                "display_order": expected_order,
                "parent_report_norm_id": parent,
                "child_report_norm_ids": children,
                "hierarchy_level": level,
                "section_path": section_path,
                "scopes": scopes,
            }
        )
    if (
        len(set(projection_ids)) != 77
        or projection_ids == sorted(projection_ids)
        or projection_ids[64:67] != [4337, 4373, 4338]
    ):
        raise E0037SealedMappingError("mapping-only workbook order drifted")

    nodes_by_id = {node["report_norm_id"]: node for node in nodes}
    for index, node in enumerate(nodes):
        schema_id = cast(int, node["report_norm_id"])
        expected_previous = projection_ids[index - 1] if index else None
        expected_next = projection_ids[index + 1] if index + 1 < len(nodes) else None
        parent = node["parent_report_norm_id"]
        if (
            node["previous_report_norm_id"] != expected_previous
            or node["next_report_norm_id"] != expected_next
            or (parent is not None and parent not in nodes_by_id)
        ):
            raise E0037SealedMappingError("mapping-only schema neighbor/parent linkage drifted")
        expected_children = [
            candidate_id
            for candidate_id in projection_ids
            if nodes_by_id[candidate_id]["parent_report_norm_id"] == schema_id
        ]
        if node["child_report_norm_ids"] != expected_children:
            raise E0037SealedMappingError("mapping-only schema child linkage drifted")
        expected_path = [schema_id]
        seen = {schema_id}
        current_parent = parent
        while current_parent is not None:
            if current_parent in seen:
                raise E0037SealedMappingError("mapping-only schema hierarchy contains a cycle")
            seen.add(current_parent)
            expected_path.append(current_parent)
            current_parent = nodes_by_id[current_parent]["parent_report_norm_id"]
        if node["section_path"] != list(reversed(expected_path)):
            raise E0037SealedMappingError("mapping-only schema section path drifted")

    computed = hashlib.sha256(
        json.dumps(
            serialized,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    if (
        computed != "7025ca729c01a3f2030af38e9745a0ee8d72b1dad60c8d4e3b7cf749e5eb860c"
        or projection.get("projection_sha256") != computed
    ):
        raise E0037SealedMappingError("mapping-only schema projection digest drifted")
    return projection_ids


def _validate_mapping_only_payload(payload: Mapping[str, Any]) -> tuple[list[Any], list[Any]]:
    required = {
        "format_version",
        "experiment_id",
        "dataset_role",
        "state",
        "capture_git_commit",
        "capture_git_dirty",
        "source_structure",
        "input_hash_ledger",
        "implementation_hash_ledger",
        "access_contract",
        "schema_projection",
        "semantic_proposals",
        "mapping",
        "rows",
        "schema_dispositions",
        "metrics",
        "authority",
        "claim_boundary",
    }
    if (
        set(payload) != required
        or payload.get("format_version") != 1
        or payload.get("experiment_id") != "E-0037"
        or payload.get("dataset_role") != "CALIBRATION"
        or payload.get("state") != MAPPING_ONLY_STATE
        or payload.get("capture_git_dirty") is not False
        or _GIT_COMMIT.fullmatch(str(payload.get("capture_git_commit", ""))) is None
    ):
        raise E0037SealedMappingError("mapping-only artifact identity drifted")
    access = payload.get("access_contract")
    if not isinstance(access, dict) or access != {
        "mapping_function_invocation_count": 1,
        "source_structure_opened": True,
        "e0035_and_e0036_sealed_label_evidence_opened": True,
        "exact_cdkt_workbook_hierarchy_scope_policy_opened": True,
        "e0030_opened": False,
        "e0033_opened": False,
        "e0034_opened": False,
        "review_or_history_opened": False,
        "qwen_result_or_rejected_raw_output_opened": False,
        "numeric_or_period_features_passed_to_mapper": False,
    }:
        raise E0037SealedMappingError("mapping-only access contract drifted")
    projection = payload.get("schema_projection")
    projection_ids = _validated_projection_ids(projection)
    projection = cast(dict[str, Any], projection)
    mapping = payload.get("mapping")
    if (
        not isinstance(mapping, dict)
        or set(mapping)
        != {
            "status",
            "automatic_selection_allowed",
            "anchors",
            "intervals",
            "best_path",
            "runner_up_path",
            "score_margin",
            "ranked_paths",
            "reason",
            "schema_projection_sha256",
            "schema_alias_authority",
            "policy_sha256",
            "search",
        }
        or mapping.get("schema_projection_sha256") != projection["projection_sha256"]
        or mapping.get("schema_alias_authority") != projection["alias_authority"]
        or mapping.get("status") not in {"RESOLVED", "AMBIGUOUS_MAPPING"}
        or not isinstance(mapping.get("automatic_selection_allowed"), bool)
        or (mapping.get("status") == "AMBIGUOUS_MAPPING")
        != (mapping.get("automatic_selection_allowed") is False)
        or not isinstance(mapping.get("anchors"), list)
        or not isinstance(mapping.get("intervals"), list)
        or not isinstance(mapping.get("ranked_paths"), list)
        or not isinstance(mapping.get("search"), dict)
    ):
        raise E0037SealedMappingError("mapper/projection identity linkage drifted")
    semantic = payload.get("semantic_proposals")
    if not isinstance(semantic, dict) or semantic != {
        "valid_proposal_counts": {"vietocr": 64, "deepseek_ocr2": 51},
        "qwen_proposal_count": 0,
        "rejected_raw_output_proposal_count": 0,
    }:
        raise E0037SealedMappingError("mapping-only semantic proposal contract drifted")
    rows, dispositions = _validate_mapping_rows(
        payload.get("rows"),
        payload.get("schema_dispositions"),
        expected_graph_ids=cast(list[int], projection_ids),
        require_evidence=True,
    )
    if {
        reader: sum(reader in row["semantic_proposals"] for row in rows)
        for reader in ("vietocr", "deepseek_ocr2", "ppocrv6_source")
    } != {"vietocr": 64, "deepseek_ocr2": 51, "ppocrv6_source": 64}:
        raise E0037SealedMappingError("mapping-only per-row proposal counts drifted")
    rows_by_id = {row["row_id"]: row for row in rows}
    for anchor in mapping["anchors"]:
        if not isinstance(anchor, dict) or not isinstance(anchor.get("row_id"), str):
            raise E0037SealedMappingError("mapping anchor diagnostic drifted")
        row = rows_by_id.get(anchor["row_id"])
        if row is None:
            raise E0037SealedMappingError("mapping anchor references an unknown row")
        selected = anchor.get("selected_report_norm_id")
        if selected is not None and selected != row["mapping"]["selected_report_norm_id"]:
            raise E0037SealedMappingError("anchor diagnostic bypasses final row disposition")
    for interval in mapping["intervals"]:
        if (
            not isinstance(interval, dict)
            or not isinstance(interval.get("row_ids"), list)
            or not isinstance(interval.get("automatic_selection_allowed"), bool)
        ):
            raise E0037SealedMappingError("mapping interval diagnostic drifted")
        if interval["automatic_selection_allowed"] is False:
            for row_id in interval["row_ids"]:
                if (
                    row_id not in rows_by_id
                    or rows_by_id[row_id]["mapping"]["selected_report_norm_id"] is not None
                ):
                    raise E0037SealedMappingError(
                        "non-accepted interval leaked a selected ReportNormId"
                    )
    input_ledger = payload.get("input_hash_ledger")
    implementation_ledger = payload.get("implementation_hash_ledger")
    if (
        not isinstance(input_ledger, dict)
        or set(input_ledger)
        != {
            "control",
            "source_structure",
            "e0035_seal",
            "e0035_crop_manifest",
            "e0036_request",
            "e0036_baseline_output_seal",
            "vietocr_result",
            "deepseek_result",
            "cdkt_workbook",
            "hierarchy_config",
            "cdkt_hierarchy_workbook",
            "scope_policy",
            "mapping_policy",
        }
        or payload.get("source_structure") != input_ledger.get("source_structure")
        or projection.get("workbook") != input_ledger.get("cdkt_workbook")
        or projection.get("hierarchy_config") != input_ledger.get("hierarchy_config")
        or projection.get("hierarchy_workbook") != input_ledger.get("cdkt_hierarchy_workbook")
        or projection.get("scope_policy") != input_ledger.get("scope_policy")
        or projection.get("mapping_policy") != input_ledger.get("mapping_policy")
        or mapping.get("policy_sha256") != input_ledger.get("mapping_policy", {}).get("sha256")
        or not isinstance(implementation_ledger, dict)
        or set(implementation_ledger)
        != {"source_structure_validator", "mapper", "integration", "capture_script"}
    ):
        raise E0037SealedMappingError("mapping-only hash ledger cross-linkage drifted")
    for ledger in (input_ledger, implementation_ledger):
        for name, record in ledger.items():
            _validate_artifact_record(record, f"mapping-only ledger {name}")
            lowered = record["path"].casefold()
            if any(
                token in lowered
                for token in ("e-0030", "e-0033", "e-0034", "review", "qwen", "histor")
            ):
                raise E0037SealedMappingError("mapping-only ledger contains a forbidden path")
    metrics = payload.get("metrics")
    expected_role_counts = dict(
        sorted(Counter(row["source_structure"]["row_role"] for row in rows).items())
    )
    if (
        not isinstance(metrics, dict)
        or set(metrics)
        != {
            "row_count",
            "schema_disposition_count",
            "accepted_row_count",
            "ambiguous_row_count",
            "unselected_row_count",
            "source_row_role_counts",
        }
        or metrics.get("row_count") != 64
        or metrics.get("schema_disposition_count") != 77
        or metrics.get("accepted_row_count")
        != sum(_mapping_is_accepted(row["mapping"]["status"]) for row in rows)
        or metrics.get("ambiguous_row_count")
        != sum("AMBIGUOUS" in row["mapping"]["status"] for row in rows)
        or metrics.get("unselected_row_count") != 64 - metrics["accepted_row_count"]
        or metrics.get("source_row_role_counts") != expected_role_counts
    ):
        raise E0037SealedMappingError("mapping-only metrics drifted")
    if payload.get("authority") != {
        "seal_a_is_bounded_structure_evidence_authority": True,
        "font_weight_slant_from_pixels_case_and_lexical_roles_from_e0035_provenance": True,
        "workbook_display_order_is_schema_order_authority": True,
        "semantic_readers_are_label_proposals_only": True,
        "numeric_value_or_status_authority": False,
        "period_or_unit_authority": False,
        "review_or_history_authority": False,
        "ambiguous_best_path_may_select_report_norm_id": False,
    }:
        raise E0037SealedMappingError("mapping-only authority contract drifted")
    if payload.get("claim_boundary") != _MAPPING_ONLY_CLAIM_BOUNDARY:
        raise E0037SealedMappingError("mapping-only claim boundary drifted")
    return rows, dispositions


def capture_e0037_mapping_seal(
    project_root: Path,
    *,
    config_path: Path = CONTROL_RELATIVE_PATH,
    mapping_only_path: Path = MAPPING_ONLY_RELATIVE_PATH,
    output_path: Path = MAPPING_SEAL_RELATIVE_PATH,
) -> dict[str, Any]:
    """Hash-seal mapping-only output before post-join artifacts may be opened."""

    project_root = project_root.resolve()
    commit = _clean_git_commit(project_root)
    control, control_stable = _load_control(project_root, config_path)
    output = _phase_output_path(project_root, control, "mapping_seal", output_path)
    mapping_path = _canonical_argument(
        project_root,
        mapping_only_path,
        MAPPING_ONLY_RELATIVE_PATH,
        "mapping-only artifact",
    )
    if output.exists() or output.is_symlink():
        raise E0037SealedMappingError(f"refusing to overwrite E-0037 artifact: {output}")
    phase = control.get("mapping_seal_phase")
    if phase != {
        "permitted_dynamic_input": "mapping_only_output_plus_exact_deterministic_replay",
        "mapper_authentication_replay_required": True,
        "exact_replay_byte_equality_required": True,
        "postjoin_inputs_may_be_opened": False,
    }:
        raise E0037SealedMappingError("E-0037 mapping-seal phase contract drifted")

    # Deliberately no E-0030/E-0033/E-0034 verifier or loader is called here.
    mapping_stable = _read_stable_file(
        project_root,
        mapping_path,
        "E-0037 mapping-only artifact",
    )
    mapping_payload = _load_json_bytes(
        mapping_stable.payload,
        "E-0037 mapping-only artifact",
    )
    rows, dispositions = _validate_mapping_only_payload(mapping_payload)
    replay_payload = capture_e0037_mapping_only(
        project_root,
        config_path=config_path,
        source_structure_path=SOURCE_STRUCTURE_RELATIVE_PATH,
        output_path=MAPPING_ONLY_RELATIVE_PATH,
        _authentication_replay=True,
    )
    replay_bytes = _encoded_json(replay_payload, canonical_compact=False)
    if replay_payload != mapping_payload or replay_bytes != mapping_stable.payload:
        raise E0037SealedMappingError(
            "mapping-only bytes differ from the exact deterministic authentication replay"
        )
    if replay_payload.get("input_hash_ledger", {}).get("control") != control_stable.artifact:
        raise E0037SealedMappingError("authentication replay used a different control identity")
    status_counts = dict(sorted(Counter(row["mapping"]["status"] for row in rows).items()))
    payload = {
        "format_version": 1,
        "experiment_id": "E-0037",
        "dataset_role": "CALIBRATION",
        "state": MAPPING_SEAL_STATE,
        "seal_git_commit": commit,
        "seal_git_dirty": False,
        "mapping_only": mapping_stable.artifact,
        "mapping_capture_git_commit": mapping_payload["capture_git_commit"],
        "schema_projection_sha256": mapping_payload["schema_projection"]["projection_sha256"],
        "row_count": len(rows),
        "schema_disposition_count": len(dispositions),
        "row_mapping_status_counts": status_counts,
        "postjoin_access": _MAPPING_SEAL_POSTJOIN_ACCESS,
        "input_hash_ledger": {
            "control": control_stable.artifact,
            "mapping_only": mapping_stable.artifact,
            "authentication_replay_inputs": replay_payload["input_hash_ledger"],
            "authentication_replay_implementation": replay_payload["implementation_hash_ledger"],
        },
        "authority": _MAPPING_SEAL_AUTHORITY,
        "claim_boundary": control["phase_claim_boundaries"]["mapping_seal"],
    }
    _assert_stable_file_unchanged(project_root, mapping_stable, "mapping-only artifact")
    _assert_stable_file_unchanged(project_root, control_stable, "E-0037 control")
    if _clean_git_commit(project_root) != commit:
        raise E0037SealedMappingError("Git commit changed during mapping-only sealing")
    _exclusive_publish_json(project_root, output, payload)
    return payload


def _load_valid_mapping_seal_before_postjoin(
    project_root: Path,
    mapping_seal_path: Path,
    control: Mapping[str, Any],
    control_stable: _StableFile,
) -> tuple[_StableFile, dict[str, Any], _StableFile, dict[str, Any]]:
    seal_path = _canonical_argument(
        project_root,
        mapping_seal_path,
        MAPPING_SEAL_RELATIVE_PATH,
        "mapping-only seal",
    )
    seal_stable = _read_stable_file(project_root, seal_path, "E-0037 mapping-only seal")
    seal = _load_json_bytes(seal_stable.payload, "E-0037 mapping-only seal")
    mapping_phase = control.get("mapping_only_phase")
    if not isinstance(mapping_phase, dict):
        raise E0037SealedMappingError("current mapping-only phase contract is absent")
    current_mapping_inputs = _validate_exact_registry(
        mapping_phase.get("permitted_frozen_inputs"),
        _MAPPING_INPUT_EXPECTED_PATHS,
        "current mapping-only input",
    )
    current_mapping_implementation = _validate_exact_registry(
        mapping_phase.get("implementation"),
        _MAPPING_IMPLEMENTATION_EXPECTED_PATHS,
        "current mapping-only implementation",
    )
    source_contract = cast(
        Mapping[str, Any],
        cast(Mapping[str, Any], control["phase_outputs"])["source_structure"],
    )
    current_source_identity = {
        "path": source_contract["path"],
        "size_bytes": source_contract["canonical_payload"]["size_bytes"],
        "sha256": source_contract["canonical_payload"]["sha256"],
    }
    expected_keys = {
        "format_version",
        "experiment_id",
        "dataset_role",
        "state",
        "seal_git_commit",
        "seal_git_dirty",
        "mapping_only",
        "mapping_capture_git_commit",
        "schema_projection_sha256",
        "row_count",
        "schema_disposition_count",
        "row_mapping_status_counts",
        "postjoin_access",
        "input_hash_ledger",
        "authority",
        "claim_boundary",
    }
    input_ledger = seal.get("input_hash_ledger")
    replay_inputs = (
        input_ledger.get("authentication_replay_inputs") if isinstance(input_ledger, dict) else None
    )
    replay_implementation = (
        input_ledger.get("authentication_replay_implementation")
        if isinstance(input_ledger, dict)
        else None
    )
    if (
        set(seal) != expected_keys
        or seal.get("format_version") != 1
        or seal.get("experiment_id") != "E-0037"
        or seal.get("dataset_role") != "CALIBRATION"
        or seal.get("state") != MAPPING_SEAL_STATE
        or _GIT_COMMIT.fullmatch(str(seal.get("seal_git_commit", ""))) is None
        or seal.get("mapping_capture_git_commit") != seal.get("seal_git_commit")
        or seal.get("seal_git_dirty") is not False
        or seal.get("row_count") != 64
        or seal.get("schema_disposition_count") != 77
        or seal.get("postjoin_access") != _MAPPING_SEAL_POSTJOIN_ACCESS
        or seal.get("authority") != _MAPPING_SEAL_AUTHORITY
        or seal.get("claim_boundary") != _MAPPING_SEAL_CLAIM_BOUNDARY
        or not isinstance(input_ledger, dict)
        or set(input_ledger)
        != {
            "control",
            "mapping_only",
            "authentication_replay_inputs",
            "authentication_replay_implementation",
        }
        or input_ledger.get("control") != control_stable.artifact
        or input_ledger.get("mapping_only") != seal.get("mapping_only")
        or not isinstance(replay_inputs, dict)
        or set(replay_inputs) != {"control", "source_structure", *current_mapping_inputs}
        or replay_inputs.get("control") != control_stable.artifact
        or replay_inputs.get("source_structure") != current_source_identity
        or any(replay_inputs.get(name) != record for name, record in current_mapping_inputs.items())
        or not isinstance(replay_implementation, dict)
        or replay_implementation != current_mapping_implementation
    ):
        raise E0037SealedMappingError("mapping-only seal is incomplete")
    _validate_artifact_record(input_ledger["control"], "mapping-seal control ledger")
    _validate_artifact_record(input_ledger["mapping_only"], "mapping-seal mapping ledger")
    mapping_stable = _verify_artifact_record(
        project_root,
        seal.get("mapping_only"),
        "mapping-only artifact sealed before postjoin",
        expected_path=MAPPING_ONLY_RELATIVE_PATH,
    )
    mapping_payload = _load_json_bytes(mapping_stable.payload, "mapping-only artifact")
    rows, dispositions = _validate_mapping_only_payload(mapping_payload)
    expected_status_counts = dict(sorted(Counter(row["mapping"]["status"] for row in rows).items()))
    if (
        seal.get("schema_projection_sha256")
        != mapping_payload["schema_projection"]["projection_sha256"]
        or seal.get("mapping_capture_git_commit") != mapping_payload.get("capture_git_commit")
        or seal.get("row_count") != len(rows)
        or seal.get("schema_disposition_count") != len(dispositions)
        or seal.get("row_mapping_status_counts") != expected_status_counts
        or input_ledger["authentication_replay_inputs"] != mapping_payload["input_hash_ledger"]
        or input_ledger["authentication_replay_implementation"]
        != mapping_payload["implementation_hash_ledger"]
    ):
        raise E0037SealedMappingError("mapping-only seal linkage drifted")
    return seal_stable, seal, mapping_stable, mapping_payload


def _validate_e0030_axes(payload: Mapping[str, Any]) -> dict[tuple[int, int], dict[str, Any]]:
    after = payload.get("after")
    gates = payload.get("gates")
    isolation = payload.get("reference_isolation")
    if (
        payload.get("experiment_id") != "E-0030"
        or payload.get("status") != _E0030_STATUS
        or payload.get("capture_git_dirty") is not False
        or not isinstance(after, list)
        or len(after) != 2
        or not isinstance(gates, dict)
        or not gates
        or any(value is not True for value in gates.values())
        or not isinstance(isolation, dict)
        or any(value is not False for value in isolation.values())
    ):
        raise E0037SealedMappingError("E-0030 period/unit artifact is incomplete")
    axes: dict[tuple[int, int], dict[str, Any]] = {}
    semantic_bindings: dict[int, tuple[Any, ...]] = {}
    parsed_periods: dict[int, date] = {}
    axis_keys = {
        "axis_id",
        "axis_right_edge",
        "canonical_unit",
        "current_or_comparative",
        "distinct_semantics_margin",
        "evidence",
        "header_bbox",
        "header_line_index",
        "matched_unit_anchor",
        "ordinal",
        "period_end",
        "period_start",
        "period_type",
        "raw_period_header",
        "raw_unit_text",
        "unit_bbox",
        "unit_line_index",
        "unit_multiplier",
        "unit_similarity",
    }

    def finite_number(value: object) -> bool:
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
        )

    def valid_bbox(value: object) -> bool:
        return (
            isinstance(value, list)
            and len(value) == 4
            and all(finite_number(coordinate) for coordinate in value)
            and value[2] >= value[0]
            and value[3] >= value[1]
        )

    for expected_page, page_record in zip((3, 4), after, strict=True):
        if (
            not isinstance(page_record, dict)
            or page_record.get("page") != expected_page
            or page_record.get("binding_mode") != "LOCAL_VISIBLE_HEADERS"
            or not isinstance(page_record.get("axes"), list)
            or len(page_record["axes"]) != 2
        ):
            raise E0037SealedMappingError("E-0030 page/axis contract drifted")
        for expected_ordinal, axis in enumerate(page_record["axes"]):
            header_bbox = axis.get("header_bbox") if isinstance(axis, dict) else None
            unit_bbox = axis.get("unit_bbox") if isinstance(axis, dict) else None
            if (
                not isinstance(axis, dict)
                or set(axis) != axis_keys
                or axis.get("ordinal") != expected_ordinal
                or axis.get("axis_id") != f"value-{expected_ordinal + 1}"
                or not isinstance(axis.get("canonical_unit"), str)
                or not axis["canonical_unit"].strip()
                or not isinstance(axis.get("unit_multiplier"), int)
                or isinstance(axis.get("unit_multiplier"), bool)
                or axis["unit_multiplier"] <= 0
                or not isinstance(axis.get("raw_unit_text"), str)
                or not axis["raw_unit_text"].strip()
                or not isinstance(axis.get("matched_unit_anchor"), str)
                or not axis["matched_unit_anchor"].strip()
                or axis.get("period_type") != "SNAPSHOT"
                or axis.get("current_or_comparative")
                != ("CURRENT" if expected_ordinal == 0 else "COMPARATIVE")
                or not isinstance(axis.get("period_start"), str)
                or axis.get("period_end") != axis.get("period_start")
                or not isinstance(axis.get("raw_period_header"), str)
                or not axis["raw_period_header"]
                or not isinstance(axis.get("header_line_index"), int)
                or isinstance(axis.get("header_line_index"), bool)
                or axis["header_line_index"] < 0
                or not isinstance(axis.get("unit_line_index"), int)
                or isinstance(axis.get("unit_line_index"), bool)
                or axis["unit_line_index"] < 0
                or not finite_number(axis.get("axis_right_edge"))
                or not finite_number(axis.get("distinct_semantics_margin"))
                or not 0 <= axis["distinct_semantics_margin"] <= 1
                or not finite_number(axis.get("unit_similarity"))
                or not 0 <= axis["unit_similarity"] <= 1
                or not isinstance(axis.get("evidence"), list)
                or not axis["evidence"]
                or any(not isinstance(item, str) or not item.strip() for item in axis["evidence"])
                or not valid_bbox(header_bbox)
                or not valid_bbox(unit_bbox)
            ):
                raise E0037SealedMappingError("E-0030 visible axis semantics drifted")
            try:
                parsed = date.fromisoformat(axis["period_start"])
            except ValueError as error:
                raise E0037SealedMappingError("E-0030 period is not an ISO date") from error
            binding = (
                axis["period_start"],
                axis["period_end"],
                axis["current_or_comparative"],
                axis["canonical_unit"],
                axis["unit_multiplier"],
                axis["raw_unit_text"],
                axis["matched_unit_anchor"],
            )
            if (
                expected_ordinal in semantic_bindings
                and semantic_bindings[expected_ordinal] != binding
            ):
                raise E0037SealedMappingError("E-0030 axis semantics differ across pages")
            semantic_bindings[expected_ordinal] = binding
            parsed_periods[expected_ordinal] = parsed
            axes[(expected_page, expected_ordinal)] = axis
    if (
        len(axes) != 4
        or set(semantic_bindings) != {0, 1}
        or parsed_periods[0] <= parsed_periods[1]
        or semantic_bindings[0][3:] != semantic_bindings[1][3:]
    ):
        raise E0037SealedMappingError("E-0030 must bind exactly four local axes")
    return axes


def _postjoin_period_unit_summary(
    axes: Mapping[tuple[int, int], Mapping[str, Any]],
) -> dict[str, Any]:
    if set(axes) != {(3, 0), (3, 1), (4, 0), (4, 1)}:
        raise E0037SealedMappingError("postjoin period/unit axes are incomplete")
    current = axes[(3, 0)]
    comparative = axes[(3, 1)]
    return {
        "period_type": current["period_type"],
        "current_period_start": current["period_start"],
        "current_period_end": current["period_end"],
        "comparative_period_start": comparative["period_start"],
        "comparative_period_end": comparative["period_end"],
        "raw_unit_text": current["raw_unit_text"],
        "matched_unit_anchor": current["matched_unit_anchor"],
        "canonical_unit": current["canonical_unit"],
        "unit_multiplier": current["unit_multiplier"],
        "report_scope": "UNKNOWN",
    }


def _postjoin_dynamic_claim(summary: Mapping[str, Any]) -> str:
    return (
        "E-0037 final postjoin is a bounded MBB CDKT calibration assembly whose snapshot "
        f"axes {summary['current_period_end']} and {summary['comparative_period_end']} and "
        f"canonical unit {summary['canonical_unit']} with multiplier "
        f"{summary['unit_multiplier']} are bound from E-0030 only after the mapping-only "
        "seal. It preserves accepted, ambiguous, unmatched, dash, blank, and challenger "
        "evidence and makes no bank-disjoint, period-disjoint, holdout, accounting, "
        "Excel-accuracy, or production-readiness claim."
    )


def _validate_e0034_cells(
    payload: Mapping[str, Any],
    transitive_e0033: Mapping[str, Any],
) -> list[dict[str, Any]]:
    after = payload.get("after")
    gates = payload.get("gates")
    isolation = payload.get("reference_isolation")
    if (
        payload.get("experiment_id") != "E-0034"
        or payload.get("status") != _E0034_STATUS
        or payload.get("capture_git_dirty") is not False
        or not isinstance(after, dict)
        or not isinstance(after.get("cells"), list)
        or len(after["cells"]) != 128
        or not isinstance(gates, dict)
        or not gates
        or any(value is not True for value in gates.values())
        or not isinstance(isolation, dict)
        or any(value is not False for value in isolation.values())
    ):
        raise E0037SealedMappingError("E-0034 numeric artifact is incomplete")
    verified_inputs = payload.get("verified_inputs")
    if not isinstance(verified_inputs, dict):
        raise E0037SealedMappingError("E-0034 verified input ledger is absent")
    e0033_record = verified_inputs.get("e0033_row_contract")
    expected_transitive = {
        key: value for key, value in transitive_e0033.items() if key != "direct_open_allowed"
    }
    if (
        transitive_e0033.get("direct_open_allowed") is not False
        or e0033_record != expected_transitive
    ):
        raise E0037SealedMappingError("E-0034 does not bind the exact transitive E-0033 input")

    cells = [cast(dict[str, Any], cell) for cell in after["cells"]]
    expected_coordinates = [
        (page, row, axis)
        for page, count in ((3, 39), (4, 25))
        for row in range(count)
        for axis in range(2)
    ]
    actual_coordinates: list[tuple[int, int, int]] = []
    allowed_statuses = {
        "VERIFIED_OBSERVED_VALUE",
        "VERIFIED_OBSERVED_DASH",
        "UNRESOLVED_BLANK_PENDING_ROW_SEMANTICS",
        "UNRESOLVED_READER_DISAGREEMENT",
    }
    for cell in cells:
        if not isinstance(cell, dict):
            raise E0037SealedMappingError("E-0034 cell must be an object")
        page = cell.get("page")
        row = cell.get("row_ordinal")
        axis = cell.get("axis_ordinal")
        if (
            not isinstance(page, int)
            or isinstance(page, bool)
            or not isinstance(row, int)
            or isinstance(row, bool)
            or not isinstance(axis, int)
            or isinstance(axis, bool)
        ):
            raise E0037SealedMappingError("E-0034 cell coordinate is invalid")
        coordinate = (page, row, axis)
        actual_coordinates.append(cast(tuple[int, int, int], coordinate))
        expected_cell_id = f"page-{page:04d}-row-{row:03d}-axis-{axis + 1}"
        if (
            coordinate not in expected_coordinates
            or cell.get("cell_id") != expected_cell_id
            or cell.get("axis_id") != f"value-{axis + 1}"
            or cell.get("verification_status") not in allowed_statuses
            or not isinstance(cell.get("primary"), dict)
            or not isinstance(cell.get("challenger"), dict)
        ):
            raise E0037SealedMappingError("E-0034 cell identity/status drifted")
    if actual_coordinates != expected_coordinates:
        raise E0037SealedMappingError("E-0034 cell order or denominator drifted")
    status_counts = Counter(cell["verification_status"] for cell in cells)
    if status_counts != {
        "VERIFIED_OBSERVED_VALUE": 113,
        "VERIFIED_OBSERVED_DASH": 5,
        "UNRESOLVED_BLANK_PENDING_ROW_SEMANTICS": 9,
        "UNRESOLVED_READER_DISAGREEMENT": 1,
    }:
        raise E0037SealedMappingError("E-0034 verification status counts drifted")
    return cells


def _numeric_cell_status(cell: Mapping[str, Any]) -> tuple[str, str | None, str | None]:
    verification = cell["verification_status"]
    primary = cast(Mapping[str, Any], cell["primary"])
    if verification == "VERIFIED_OBSERVED_VALUE":
        normalized = cell.get("normalized_numeric_value")
        raw = cell.get("selected_raw_value")
        if (
            primary.get("observation") != "VALUE"
            or not isinstance(normalized, str)
            or not normalized
            or not isinstance(raw, str)
            or not raw
        ):
            raise E0037SealedMappingError("verified E-0034 value lacks exact selected evidence")
        status = "OBSERVED_ZERO" if normalized in {"0", "-0"} else "OBSERVED_VALUE"
        return status, raw, normalized
    if verification == "VERIFIED_OBSERVED_DASH":
        if primary.get("observation") != "DASH":
            raise E0037SealedMappingError("verified E-0034 dash lost its source observation")
        return "DASH", None, None
    if verification == "UNRESOLVED_BLANK_PENDING_ROW_SEMANTICS":
        if primary.get("observation") != "BLANK":
            raise E0037SealedMappingError("E-0034 blank status lacks blank source evidence")
        return "UNRESOLVED", None, None
    if verification == "UNRESOLVED_READER_DISAGREEMENT":
        return "UNRESOLVED", None, None
    raise E0037SealedMappingError(f"unsupported E-0034 verification status: {verification}")


def _normalize_embedded_project_paths(value: Any, project_root: Path) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, child in value.items():
            if isinstance(child, str) and key.endswith("path") and Path(child).is_absolute():
                try:
                    child = Path(child).resolve().relative_to(project_root).as_posix()
                except ValueError as error:
                    raise E0037SealedMappingError(
                        f"postjoin evidence path escapes project root: {child}"
                    ) from error
            result[key] = _normalize_embedded_project_paths(child, project_root)
        return result
    if isinstance(value, list):
        return [_normalize_embedded_project_paths(item, project_root) for item in value]
    return value


def _assemble_postjoin_cells(
    project_root: Path,
    mapping_rows: Sequence[Mapping[str, Any]],
    numeric_cells: Sequence[Mapping[str, Any]],
    axes: Mapping[tuple[int, int], Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows_by_id = {cast(str, row["row_id"]): row for row in mapping_rows}
    result: list[dict[str, Any]] = []
    for cell in numeric_cells:
        page = cast(int, cell["page"])
        row_ordinal = cast(int, cell["row_ordinal"])
        axis_ordinal = cast(int, cell["axis_ordinal"])
        row_id = f"page-{page:04d}-row-{row_ordinal:03d}-label"
        mapping = cast(Mapping[str, Any], rows_by_id[row_id]["mapping"])
        mapping_accepted = _mapping_is_accepted(mapping["status"])
        selected_report_norm_id = mapping["selected_report_norm_id"] if mapping_accepted else None
        cell_status, raw_value, normalized_value = _numeric_cell_status(cell)
        axis = axes[(page, axis_ordinal)]
        if not mapping_accepted:
            selected_raw_value = None
            selected_normalized_value = None
            output_status = (
                "AMBIGUOUS" if "AMBIGUOUS" in cast(str, mapping["status"]) else "UNRESOLVED"
            )
        else:
            selected_raw_value = raw_value
            selected_normalized_value = normalized_value
            output_status = cell_status
        canonical_unit_value: str | None = None
        if selected_normalized_value is not None:
            try:
                canonical = Decimal(selected_normalized_value) * Decimal(
                    cast(int, axis["unit_multiplier"])
                )
                if not canonical.is_finite() or canonical != canonical.to_integral_value():
                    raise E0037SealedMappingError(
                        f"non-integral canonical-unit value for {cell['cell_id']}"
                    )
            except (InvalidOperation, TypeError, ValueError) as error:
                raise E0037SealedMappingError(
                    f"cannot scale displayed-unit value for {cell['cell_id']}"
                ) from error
            canonical_unit_value = str(int(canonical))
        result.append(
            {
                "cell_id": cell["cell_id"],
                "row_id": row_id,
                "page": page,
                "row_ordinal": row_ordinal,
                "axis_ordinal": axis_ordinal,
                "period_axis": dict(axis),
                "report_scope": "UNKNOWN",
                "mapping_status": mapping["status"],
                "candidate_report_norm_ids": list(mapping["candidate_report_norm_ids"]),
                "selected_report_norm_id": selected_report_norm_id,
                "source_observation": cell["primary"]["observation"],
                "numeric_verification_status": cell["verification_status"],
                "cell_status": cell_status,
                "output_status": output_status,
                "selected_raw_value": selected_raw_value,
                "selected_normalized_value": selected_normalized_value,
                "displayed_unit_value": selected_normalized_value,
                "displayed_unit_raw_text": selected_raw_value,
                "displayed_unit": axis["raw_unit_text"],
                "canonical_unit": axis["canonical_unit"],
                "unit_multiplier": axis["unit_multiplier"],
                "canonical_unit_value": canonical_unit_value,
                "visible_raw_value": cell["primary"]["raw_text"],
                "numeric_evidence": _normalize_embedded_project_paths(
                    dict(cell),
                    project_root,
                ),
            }
        )
    if len(result) != 128:
        raise E0037SealedMappingError("postjoin did not retain exactly 128 cells")
    return result


def capture_e0037_postjoin(
    project_root: Path,
    *,
    config_path: Path = CONTROL_RELATIVE_PATH,
    mapping_seal_path: Path = MAPPING_SEAL_RELATIVE_PATH,
    output_path: Path = POSTJOIN_RELATIVE_PATH,
) -> dict[str, Any]:
    """Join frozen period/numeric evidence after validating the mapping-only seal."""

    project_root = project_root.resolve()
    commit = _clean_git_commit(project_root)
    control, control_stable = _load_control(project_root, config_path)
    output = _phase_output_path(project_root, control, "postjoin", output_path)
    if output.exists() or output.is_symlink():
        raise E0037SealedMappingError(f"refusing to overwrite E-0037 artifact: {output}")
    phase = control.get("postjoin_phase")
    if not isinstance(phase, dict) or phase.get("mapper_may_be_invoked") is not False:
        raise E0037SealedMappingError("E-0037 postjoin phase contract drifted")

    # Access order is deliberate: a complete mapping seal and its exact mapping
    # bytes are validated before either postjoin artifact is opened.
    seal_stable, _seal, mapping_stable, mapping_payload = _load_valid_mapping_seal_before_postjoin(
        project_root,
        mapping_seal_path,
        control,
        control_stable,
    )
    mapping_rows, schema_dispositions = _validate_mapping_only_payload(mapping_payload)

    transitive_e0033 = phase.get("transitive_e0033_binding")
    if (
        not isinstance(transitive_e0033, dict)
        or set(transitive_e0033) != {"path", "size_bytes", "sha256", "direct_open_allowed"}
        or transitive_e0033.get("direct_open_allowed") is not False
    ):
        raise E0037SealedMappingError("transitive E-0033 binding is absent or invalid")
    transitive_identity = {
        key: value for key, value in transitive_e0033.items() if key != "direct_open_allowed"
    }
    _validate_artifact_record(transitive_identity, "transitive E-0033 binding")
    if (
        transitive_identity["path"]
        != "docs/experiments/E-0033-mbb-cdkt-note-row-split-immutable.json"
    ):
        raise E0037SealedMappingError("transitive E-0033 path is noncanonical")
    permitted_postjoin = _validate_exact_registry(
        phase.get("permitted_frozen_inputs"),
        _POSTJOIN_INPUT_EXPECTED_PATHS,
        "E-0037 postjoin input",
    )
    stable_postjoin = _verify_phase_records(
        project_root,
        permitted_postjoin,
        "E-0037 postjoin",
    )
    table_metadata = _load_json_bytes(
        stable_postjoin["table_metadata"].payload,
        "E-0030 table metadata",
    )
    numeric_verification = _load_json_bytes(
        stable_postjoin["numeric_verification"].payload,
        "E-0034 numeric verification",
    )
    axes = _validate_e0030_axes(table_metadata)
    period_unit_summary = _postjoin_period_unit_summary(axes)
    numeric_cells = _validate_e0034_cells(numeric_verification, transitive_e0033)
    cells = _assemble_postjoin_cells(project_root, mapping_rows, numeric_cells, axes)
    mapping_status_counts = dict(
        sorted(Counter(row["mapping"]["status"] for row in mapping_rows).items())
    )
    cell_status_counts = dict(sorted(Counter(cell["cell_status"] for cell in cells).items()))
    numeric_verification_status_counts = dict(
        sorted(Counter(cell["numeric_verification_status"] for cell in cells).items())
    )
    output_status_counts = dict(sorted(Counter(cell["output_status"] for cell in cells).items()))
    if (
        set(output_status_counts) - {"OBSERVED_VALUE", "DASH", "UNRESOLVED", "AMBIGUOUS"}
        or sum(output_status_counts.values()) != 128
    ):
        raise E0037SealedMappingError("postjoin output status denominator drifted")
    payload = {
        "format_version": 1,
        "experiment_id": "E-0037",
        "dataset_role": "CALIBRATION",
        "state": POSTJOIN_STATE,
        "capture_git_commit": commit,
        "capture_git_dirty": False,
        "mapping_only_seal": seal_stable.artifact,
        "mapping_only": mapping_stable.artifact,
        "input_hash_ledger": {
            "control": control_stable.artifact,
            "mapping_only_seal": seal_stable.artifact,
            "mapping_only": mapping_stable.artifact,
            "table_metadata": stable_postjoin["table_metadata"].artifact,
            "numeric_verification": stable_postjoin["numeric_verification"].artifact,
            "transitive_e0033_not_opened": {
                key: value
                for key, value in transitive_e0033.items()
                if key != "direct_open_allowed"
            },
        },
        "access_order": {
            "mapping_only_seal_validated_before_postjoin_open": True,
            "mapping_only_hash_validated_before_postjoin_open": True,
            "e0030_opened_after_mapping_seal": True,
            "e0034_opened_after_mapping_seal": True,
            "e0033_opened_directly": False,
            "e0033_bound_transitively_through_e0034": True,
            "mapper_invocation_count": 0,
            "mapping_result_repaired_or_rerun": False,
            "review_or_history_opened": False,
        },
        "schema_projection": mapping_payload["schema_projection"],
        "report_scope": {
            "value": "UNKNOWN",
            "reason": "Seal A and mapping-only have no authority to infer scope from filename",
        },
        "period_unit_summary": period_unit_summary,
        "mapping": mapping_payload["mapping"],
        "rows": mapping_rows,
        "schema_dispositions": schema_dispositions,
        "cells": cells,
        "metrics": {
            "row_count": 64,
            "schema_disposition_count": 77,
            "cell_count": 128,
            "mapping_status_counts": mapping_status_counts,
            "cell_status_counts": cell_status_counts,
            "numeric_verification_status_counts": numeric_verification_status_counts,
            "output_status_counts": output_status_counts,
            "period_axis_count": 4,
            "transitive_e0033_binding_verified": True,
        },
        "authority": {
            "mapping_decision_bytes_unchanged_from_sealed_mapping_only": True,
            "period_unit_from_e0030_visible_headers": True,
            "numeric_evidence_from_e0034_independent_verification": True,
            "dash_preserved_distinct_from_zero": True,
            "blank_promoted_to_zero_or_value": False,
            "ambiguous_mapping_may_select_report_norm_id_or_value": False,
            "review_or_history_authority": False,
            "accounting_or_excel_claim": False,
        },
        "claim_boundary": _postjoin_dynamic_claim(period_unit_summary),
    }

    _assert_stable_file_unchanged(project_root, seal_stable, "mapping-only seal")
    _assert_stable_file_unchanged(project_root, mapping_stable, "mapping-only artifact")
    for name, stable in stable_postjoin.items():
        _assert_stable_file_unchanged(project_root, stable, f"postjoin input {name}")
    _assert_stable_file_unchanged(project_root, control_stable, "E-0037 control")
    if _clean_git_commit(project_root) != commit:
        raise E0037SealedMappingError("Git commit changed during E-0037 postjoin")
    _exclusive_publish_json(project_root, output, payload)
    return payload
