"""Phase-separated E-0038 exact mapping and deterministic one-file sealing."""

from __future__ import annotations

import errno
import hashlib
import json
import os
import platform
import re
import secrets
import stat
import subprocess
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from importlib.metadata import version as package_distribution_version
from pathlib import Path
from typing import Any, cast

import yaml
from yaml.constructor import ConstructorError
from yaml.events import AliasEvent

from bctc_ai.evaluation.e0037_sealed_mapping import (
    E0037SealedMappingError,
    _open_or_create_parent_directory,
    _StableFile,
    _validate_mapping_only_payload,
)
from bctc_ai.evaluation.e0037_sealed_mapping import (
    _read_stable_file as _read_stable_file_e0037,
)
from bctc_ai.mapping.e0038_exact_search import (
    E0038ExactSearchOutcome,
    run_e0038_exact_search,
)
from bctc_ai.mapping.ordered_subgraph_v2 import (
    SchemaProjectionNodeV2,
    SchemaProjectionV2,
    SourceStructureRowV2,
    load_ordered_subgraph_v2_policy_bytes,
)
from bctc_ai.mapping.structural_alias_overlay import (
    apply_structural_alias_overlay,
    load_structural_alias_overlay_bytes,
)


class E0038ExactMappingError(RuntimeError):
    """Raised when E-0038 cannot preserve its sealed calibration contract."""


CONTROL_RELATIVE_PATH = Path("config/experiments/e0038-mbb-cdkt-exact-mapping.yaml")
MAPPING_ONLY_RELATIVE_PATH = Path(
    "output/calibration/e0038-mbb-cdkt-exact-mapping/mapping_only.json"
)
MAPPING_SEAL_RELATIVE_PATH = Path("docs/experiments/E-0038-mbb-cdkt-exact-mapping-seal.json")
E0037_MAPPING_ONLY_RELATIVE_PATH = Path(
    "output/calibration/e0037-mbb-cdkt-sealed-evidence-mapping/mapping_only.json"
)
E0037_MAPPING_SEAL_RELATIVE_PATH = Path("docs/experiments/E-0037-mbb-cdkt-mapping-only-seal.json")
S3_REGISTRY_RELATIVE_PATH = Path("data/registered/s3_artifact_snapshot_registry.jsonl")

MAPPING_ONLY_STATE = "E0038_EXACT_MAPPING_ONLY_CALIBRATION_HYPOTHESIS_SEALED_BEFORE_REVIEW"
MAPPING_SEAL_STATE = "E0038_EXACT_MAPPING_HASH_SEALED_BEFORE_REVIEW"
BASE_ALIAS_AUTHORITY = "CANONICAL_AND_STRUCTURAL_ALIASES_ONLY"
OVERLAY_ALIAS_AUTHORITY = "E0038_CALIBRATION_FAILURE_HYPOTHESIS"
BASE_PROJECTION_SHA256 = "7025ca729c01a3f2030af38e9745a0ee8d72b1dad60c8d4e3b7cf749e5eb860c"
RESULT_PROJECTION_SHA256 = "d0934db910063bdb98db83f02bc2444fc1fe6e1dce7e1ebc7e09c7d36e434283"
SOURCE_ROWS_SHA256 = "43242aa3e777810e7fe28b43eba25940818cac8568ba954f10e6f673da167c09"
SEALED_INTERVALS_SHA256 = "e0e02daaa015329976d264e3fbd223b3d71bf91f138321f2d6e194ad763f5c83"
SOURCE_ROW_IDS_SHA256 = "b4fe87949522195ded7beae958cb5235aa36805db102b0f49675e29d855863d0"
SCHEMA_IDS_SHA256 = "c8467e5ae646924500548cacab46b7e1e8440106c110997da31eed349014edbb"
ALIAS_RECEIPT_SHA256 = "768867b636c137b26804e6bcfb4230491e07d91299160e4071b8ac72664aa7b9"
MAPPING_RESULT_SHA256 = "45133c4c6a441327afc611d6cce6c4711b7fe18b945339d854944817b90a9e86"
EXACT_PLAN_SHA256 = "6047288ca4bb69cb31ffad8a08a419b1232c04d8c9227dba657c1ce023e1641a"
EXACT_OUTCOME_REASON = (
    "immutable ordered-subgraph v2 completed with interval identity parity and zero "
    "main/counterfactual pruning; mapping acceptance remains governed by the unchanged v2 gates"
)
EXACT_OUTCOME_REASON_SHA256 = "c8be4502af2eaade4e302440a4f2ddd7e8e40e8dda176917bb37fc23aa91a165"
E0037_MAPPING_ONLY_SHA256 = "e18f6b20825f93b20023c0d89caca1737481008b244696594852ca9fa972f99e"
E0037_MAPPING_ONLY_SIZE = 646393
E0037_MAPPING_SEAL_SHA256 = "665aa1b3ac96881df0a4cd7b2f7da2425c3635ad1e8ea024e299b668c79ed0e5"
E0037_MAPPING_SEAL_SIZE = 6016
S3_REGISTRY_SHA256 = "25da6b205a775d87eca8e4ffe55e3f762ee64e92cbb7190c2834708a7de0d78d"
S3_REGISTRY_SIZE = 6050
S3_SNAPSHOT_ID = "20260807T170440Z-e0037-source-and-mapping-seal-e18f6b20825f"
S3_SNAPSHOT_RECORD_SHA256 = "829ac8f0220ffa1c42ccbb65659e44ea7f062c44ee203ec4a91ef091e98cb067"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_GIT_COMMIT = re.compile(r"[0-9a-f]{40}")

_MAPPING_ONLY_CLAIM = (
    "E-0038 is an MBB CDKT calibration-only mechanism run over the exact hash-sealed "
    "E-0037 mapping-only evidence. Its two ID-scoped aliases are unapproved calibration "
    "hypotheses, not schema authority or review evidence. Exact-search completion records "
    "deterministic zero-pruning behavior under pinned inputs; it does not establish mapping "
    "accuracy, schema correctness, period, unit, numeric truth, accounting validity, Excel "
    "correctness, holdout performance, or production readiness."
)
_MAPPING_SEAL_CLAIM = (
    "This artifact hash-seals exactly one E-0038 mapping-only file after deterministic "
    "replay from a clean Git commit and before review access. It adds no schema, "
    "mapping-accuracy, numeric, period, unit, accounting, Excel, holdout, or production "
    "claim."
)
_E0037_SEAL_CLAIM = (
    "This artifact seals the E-0037 mapping-only bytes before any E-0030 period/unit or "
    "E-0034 numeric/status evidence is opened. It does not add, rerun, repair, or reinterpret "
    "a mapping and makes no numeric, accounting, Excel, holdout, or production claim."
)
_FORBIDDEN_INPUTS = [
    "E_0030_PERIOD_OR_UNIT_METADATA",
    "E_0033_ROWS_LABELS_GEOMETRY_OR_CELLS",
    "E_0034_NUMERIC_VALUES_SIGNS_BLANKS_DASHES_OR_STATUS",
    "HUMAN_REVIEW_LABELS_IDS_VALUES_OR_PERIOD_ANSWERS",
    "REVIEWED_READER_EVALUATION_ARTIFACTS",
    "HISTORICAL_OR_MONGODB_LABELS_ALIASES_IDS_OR_VALUES",
    "QWEN_RAW_OUTPUT_REJECTED_OUTPUT_OR_TOKEN_STREAM",
    "NUMERIC_VALUE_FEATURES",
    "PERIOD_OR_UNIT_FEATURES",
]
_VALIDATION_ORDER = [
    "CONTROL_AND_IMPLEMENTATION",
    "E0037_MAPPING_SEAL",
    "S3_REGISTRY_RESTORE_RECORD",
    "E0037_MAPPING_ONLY_BYTES",
]
_PUBLICATION = {
    "canonical_paths_only": True,
    "atomic_exclusive_no_overwrite": True,
    "clean_git_required_before_and_immediately_before_publication": True,
    "stable_input_identity_recheck_required": True,
    "exact_input_and_implementation_hash_ledgers_required": True,
    "mapping_only_sealed_before_review_access": True,
    "deterministic_sealer_replay_required": True,
    "exact_one_file_seal_inventory_required": True,
    "tracked_ledger_head_blob_binding_required": True,
    "fresh_canonical_input_revalidation_required": True,
    "post_link_canonical_parent_and_file_revalidation_required": True,
    "mapping_directory_exact_inventory_required": True,
}
_INPUT_PATHS = {
    "e0037_mapping_only": E0037_MAPPING_ONLY_RELATIVE_PATH,
    "e0037_mapping_seal": E0037_MAPPING_SEAL_RELATIVE_PATH,
    "s3_snapshot_registry": S3_REGISTRY_RELATIVE_PATH,
    "e0037_mapping_policy": Path("config/mapping/ordered-subgraph-v2.yaml"),
    "e0038_exact_mapping_policy": Path("config/mapping/ordered-subgraph-v2-exact-e0038.yaml"),
    "e0038_alias_policy": Path("config/mapping/e0038-cdkt-structural-alias-candidates.yaml"),
}
_IMPLEMENTATION_PATHS = {
    "text_normalization": Path("src/bctc_ai/core/text.py"),
    "mapper": Path("src/bctc_ai/mapping/ordered_subgraph_v2.py"),
    "exact_search_helper": Path("src/bctc_ai/mapping/e0038_exact_search.py"),
    "alias_overlay": Path("src/bctc_ai/mapping/structural_alias_overlay.py"),
    "stable_io_and_e0037_payload_validator": Path("src/bctc_ai/evaluation/e0037_sealed_mapping.py"),
    "integration": Path("src/bctc_ai/evaluation/e0038_exact_mapping.py"),
    "capture_script": Path("scripts/experiments/capture_e0038_mbb_cdkt_exact_mapping.py"),
    "seal_script": Path("scripts/experiments/capture_e0038_mbb_cdkt_exact_mapping_seal.py"),
}
_RUNTIME_PATHS = {
    "project_metadata": Path("pyproject.toml"),
    "dependency_lock": Path("uv.lock"),
}
_RUNTIME_VERSIONS = {
    "python": "3.11.10",
    "rapidfuzz": "3.14.5",
    "pyyaml": "6.0.3",
}


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""

    def compose_node(self, parent: yaml.Node | None, index: int | None) -> yaml.Node:
        if self.check_event(AliasEvent):
            event = self.peek_event()
            raise ConstructorError(
                "while composing E-0038 control",
                getattr(event, "start_mark", None),
                "YAML aliases are forbidden",
                getattr(event, "start_mark", None),
            )
        return super().compose_node(parent, index)


def _construct_unique_mapping(
    loader: _UniqueKeySafeLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in result
        except TypeError as exc:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable mapping key",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)

StableReader = Callable[..., _StableFile]


@dataclass(frozen=True)
class _Prerequisites:
    control: dict[str, Any]
    control_stable: _StableFile
    implementation_stable: dict[str, _StableFile]
    policy_stable: dict[str, _StableFile]
    runtime_stable: dict[str, _StableFile]


@dataclass(frozen=True)
class _E0037Authority:
    prerequisites: _Prerequisites
    seal_stable: _StableFile
    seal: dict[str, Any]
    registry_stable: _StableFile
    s3_record: dict[str, Any]
    mapping_stable: _StableFile
    mapping: dict[str, Any]


def _exact_keys(value: object, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise E0038ExactMappingError(f"{label} keyset drifted")
    return cast(dict[str, Any], value)


def _decode_json_object(payload: bytes, label: str) -> dict[str, Any]:
    def reject_nonfinite(value: str) -> None:
        raise ValueError(f"non-finite JSON constant: {value}")

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        decoded = json.loads(
            payload.decode("utf-8"),
            parse_constant=reject_nonfinite,
            object_pairs_hook=reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise E0038ExactMappingError(f"cannot decode {label} as strict JSON") from exc
    if not isinstance(decoded, dict):
        raise E0038ExactMappingError(f"{label} must be a JSON object")
    return decoded


def _decode_control(payload: bytes) -> dict[str, Any]:
    try:
        decoded = yaml.load(payload.decode("utf-8"), Loader=_UniqueKeySafeLoader)
    except (UnicodeDecodeError, yaml.YAMLError, ValueError, RecursionError) as exc:
        raise E0038ExactMappingError("cannot decode E-0038 control") from exc
    if not isinstance(decoded, dict):
        raise E0038ExactMappingError("E-0038 control must be a YAML object")
    return decoded


def _artifact_record(
    value: object,
    label: str,
    *,
    expected_path: Path | None = None,
) -> dict[str, Any]:
    record = _exact_keys(value, {"path", "sha256", "size_bytes"}, label)
    path = record.get("path")
    digest = record.get("sha256")
    size = record.get("size_bytes")
    if (
        not isinstance(path, str)
        or not path
        or Path(path).is_absolute()
        or ".." in Path(path).parts
        or not isinstance(digest, str)
        or _SHA256.fullmatch(digest) is None
        or type(size) is not int
        or size < 0
        or (expected_path is not None and path != expected_path.as_posix())
    ):
        raise E0038ExactMappingError(f"{label} artifact identity is invalid")
    return record


def _canonical_path(project_root: Path, relative: Path, expected: Path, label: str) -> Path:
    if relative.is_absolute() or relative.as_posix() != expected.as_posix():
        raise E0038ExactMappingError(f"{label} must use canonical path {expected}")
    cursor = project_root
    for part in relative.parts:
        cursor /= part
        if cursor.is_symlink():
            raise E0038ExactMappingError(f"{label} path contains a symlink")
    resolved = (project_root / relative).resolve()
    if not resolved.is_relative_to(project_root):
        raise E0038ExactMappingError(f"{label} path escapes project root")
    return resolved


def _stat_identity(value: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _open_existing_parent_directory(
    project_root: Path,
    relative: Path,
    label: str,
) -> tuple[int, str]:
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise E0038ExactMappingError(f"unsafe project-relative path for {label}")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        current = os.open(project_root, flags)
    except OSError as exc:
        raise E0038ExactMappingError(f"cannot open project root for {label}") from exc
    try:
        for part in relative.parts[:-1]:
            try:
                following = os.open(part, flags, dir_fd=current)
            except OSError as exc:
                raise E0038ExactMappingError(
                    f"cannot traverse fresh canonical path for {label}"
                ) from exc
            os.close(current)
            current = following
        return current, relative.parts[-1]
    except Exception:
        os.close(current)
        raise


def _read_from_fresh_canonical_path(
    project_root: Path,
    path: Path,
    label: str,
    *,
    expected_size: int | None,
    maximum_size: int,
) -> _StableFile:
    if not path.is_relative_to(project_root):
        raise E0038ExactMappingError(f"{label} path escapes project root")
    relative = path.relative_to(project_root)
    parent, final_name = _open_existing_parent_directory(project_root, relative, label)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        try:
            descriptor = os.open(final_name, flags, dir_fd=parent)
        except OSError as exc:
            raise E0038ExactMappingError(f"cannot open fresh canonical {label}") from exc
        chunks: list[bytes] = []
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                raise E0038ExactMappingError(f"fresh canonical {label} is not regular")
            if before.st_size > maximum_size:
                raise E0038ExactMappingError(f"fresh canonical {label} exceeds size bound")
            if expected_size is not None and before.st_size != expected_size:
                raise E0038ExactMappingError(f"fresh canonical {label} size drifted")
            remaining = before.st_size
            while remaining:
                block = os.read(descriptor, min(1024 * 1024, remaining))
                if not block:
                    break
                chunks.append(block)
                remaining -= len(block)
            growth = os.read(descriptor, 1)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        final = os.stat(final_name, dir_fd=parent, follow_symlinks=False)
    except Exception:
        os.close(parent)
        raise
    os.close(parent)
    payload = b"".join(chunks)
    identity = _stat_identity(before)
    if (
        identity != _stat_identity(after)
        or identity != _stat_identity(final)
        or remaining != 0
        or growth
        or len(payload) != before.st_size
    ):
        raise E0038ExactMappingError(f"fresh canonical {label} changed during read")

    # Reopen the canonical chain once more after the read. This detects a parent
    # directory that was detached or replaced while the first descriptor was held.
    recheck_parent, recheck_name = _open_existing_parent_directory(
        project_root,
        relative,
        f"{label} post-read recheck",
    )
    try:
        recheck = os.stat(recheck_name, dir_fd=recheck_parent, follow_symlinks=False)
    except OSError as exc:
        raise E0038ExactMappingError(f"cannot revalidate canonical identity for {label}") from exc
    finally:
        os.close(recheck_parent)
    if _stat_identity(recheck) != identity:
        raise E0038ExactMappingError(f"canonical identity changed after reading {label}")
    return _StableFile(
        path=project_root / relative,
        payload=payload,
        identity=identity,
        artifact={
            "path": relative.as_posix(),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        },
    )


def _read_stable_file(
    project_root: Path,
    path: Path,
    label: str,
    *,
    expected_size: int | None = None,
    maximum_size: int = 64 * 1024 * 1024,
) -> _StableFile:
    """Add fresh canonical-path binding to the inherited stable descriptor read."""

    inherited = _read_stable_file_e0037(
        project_root,
        path,
        label,
        expected_size=expected_size,
        maximum_size=maximum_size,
    )
    fresh = _read_from_fresh_canonical_path(
        project_root,
        path,
        label,
        expected_size=expected_size,
        maximum_size=maximum_size,
    )
    if (
        inherited.identity != fresh.identity
        or inherited.artifact != fresh.artifact
        or inherited.payload != fresh.payload
    ):
        raise E0038ExactMappingError(
            f"{label} inherited read differs from its fresh canonical identity"
        )
    return fresh


def _stable_read(
    reader: StableReader,
    project_root: Path,
    path: Path,
    label: str,
    *,
    expected_size: int | None = None,
    maximum_size: int,
) -> _StableFile:
    try:
        return reader(
            project_root,
            path,
            label,
            expected_size=expected_size,
            maximum_size=maximum_size,
        )
    except (E0037SealedMappingError, OSError, ValueError) as exc:
        raise E0038ExactMappingError(f"cannot stable-read {label}") from exc


def _verify_record(
    reader: StableReader,
    project_root: Path,
    record: object,
    label: str,
    *,
    expected_path: Path,
    maximum_size: int,
) -> _StableFile:
    identity = _artifact_record(record, label, expected_path=expected_path)
    path = _canonical_path(project_root, expected_path, expected_path, label)
    stable = _stable_read(
        reader,
        project_root,
        path,
        label,
        expected_size=cast(int, identity["size_bytes"]),
        maximum_size=maximum_size,
    )
    if stable.artifact != identity:
        raise E0038ExactMappingError(f"{label} differs from its pinned identity")
    return stable


def _assert_unchanged(
    reader: StableReader,
    project_root: Path,
    original: _StableFile,
    label: str,
) -> None:
    current = _stable_read(
        reader,
        project_root,
        original.path,
        label,
        expected_size=cast(int, original.artifact["size_bytes"]),
        maximum_size=max(cast(int, original.artifact["size_bytes"]), 1),
    )
    if current.identity != original.identity or current.artifact != original.artifact:
        raise E0038ExactMappingError(f"{label} changed after validation")


def _load_control(
    project_root: Path,
    config_path: Path,
    reader: StableReader,
) -> tuple[dict[str, Any], _StableFile]:
    control_path = _canonical_path(
        project_root,
        config_path,
        CONTROL_RELATIVE_PATH,
        "E-0038 control",
    )
    stable = _stable_read(
        reader,
        project_root,
        control_path,
        "E-0038 control",
        maximum_size=1024 * 1024,
    )
    control = _decode_control(stable.payload)
    _exact_keys(
        control,
        {
            "version",
            "experiment_id",
            "dataset_role",
            "design",
            "state",
            "phase_outputs",
            "input_authority",
            "implementation",
            "runtime_authority",
            "mapping_contract",
            "validation_order",
            "forbidden_inputs",
            "publication",
            "claim_boundaries",
        },
        "E-0038 control",
    )
    if (
        control.get("version") != 1
        or control.get("experiment_id") != "E-0038"
        or control.get("dataset_role") != "CALIBRATION"
        or control.get("design")
        != "SEALED_E0037_MAPPING_RECONSTRUCTION_ALIAS_OVERLAY_EXACT_SEARCH_THEN_HASH_SEAL"
        or control.get("state") != "READY_FOR_MAPPING_ONLY_THEN_HASH_SEAL"
    ):
        raise E0038ExactMappingError("E-0038 control identity drifted")
    outputs = _exact_keys(
        control.get("phase_outputs"),
        {"mapping_only", "mapping_seal"},
        "E-0038 phase outputs",
    )
    if outputs.get("mapping_only") != {
        "path": MAPPING_ONLY_RELATIVE_PATH.as_posix(),
        "required_state": MAPPING_ONLY_STATE,
        "encoding": "UTF8_JSON_SORTED_KEYS_INDENT2_NEWLINE_NO_NAN_V1",
    } or outputs.get("mapping_seal") != {
        "path": MAPPING_SEAL_RELATIVE_PATH.as_posix(),
        "required_state": MAPPING_SEAL_STATE,
        "encoding": "UTF8_JSON_SORTED_KEYS_INDENT2_NEWLINE_NO_NAN_V1",
        "inventory_file_count": 1,
        "inventory_paths": [MAPPING_ONLY_RELATIVE_PATH.as_posix()],
    }:
        raise E0038ExactMappingError("E-0038 canonical output contract drifted")

    inputs = _exact_keys(
        control.get("input_authority"),
        {*_INPUT_PATHS, "s3_snapshot"},
        "E-0038 input authority",
    )
    for name, expected_path in _INPUT_PATHS.items():
        _artifact_record(inputs.get(name), f"E-0038 input {name}", expected_path=expected_path)
    if (
        inputs["e0037_mapping_only"]
        != {
            "path": E0037_MAPPING_ONLY_RELATIVE_PATH.as_posix(),
            "sha256": E0037_MAPPING_ONLY_SHA256,
            "size_bytes": E0037_MAPPING_ONLY_SIZE,
        }
        or inputs["e0037_mapping_seal"]
        != {
            "path": E0037_MAPPING_SEAL_RELATIVE_PATH.as_posix(),
            "sha256": E0037_MAPPING_SEAL_SHA256,
            "size_bytes": E0037_MAPPING_SEAL_SIZE,
        }
        or inputs["s3_snapshot_registry"]
        != {
            "path": S3_REGISTRY_RELATIVE_PATH.as_posix(),
            "sha256": S3_REGISTRY_SHA256,
            "size_bytes": S3_REGISTRY_SIZE,
        }
    ):
        raise E0038ExactMappingError("E-0037 mapping/restore authority identity drifted")
    snapshot = inputs.get("s3_snapshot")
    probe = snapshot.get("hydrate_probe") if isinstance(snapshot, dict) else None
    logical_paths = probe.get("logical_paths") if isinstance(probe, dict) else None
    if (
        not isinstance(snapshot, dict)
        or not isinstance(probe, dict)
        or not isinstance(logical_paths, list)
        or snapshot.get("artifact_snapshot_id") != S3_SNAPSHOT_ID
        or snapshot.get("restore_verified") is not True
        or snapshot.get("policy") != "S3_BOUNDED_ARTIFACT_SNAPSHOT_V1"
        or snapshot.get("file_count") != 2
        or probe.get("status") != "PASS"
        or probe.get("sealed_hashes_match") is not True
        or E0037_MAPPING_ONLY_RELATIVE_PATH.as_posix() not in logical_paths
        or _canonical_sha256(snapshot) != S3_SNAPSHOT_RECORD_SHA256
    ):
        raise E0038ExactMappingError("E-0038 S3 snapshot authority drifted")

    implementation = _exact_keys(
        control.get("implementation"),
        set(_IMPLEMENTATION_PATHS),
        "E-0038 implementation registry",
    )
    for name, expected_path in _IMPLEMENTATION_PATHS.items():
        _artifact_record(
            implementation.get(name),
            f"E-0038 implementation {name}",
            expected_path=expected_path,
        )
    runtime = _exact_keys(
        control.get("runtime_authority"),
        {"artifacts", "versions"},
        "E-0038 runtime authority",
    )
    runtime_artifacts = _exact_keys(
        runtime.get("artifacts"),
        set(_RUNTIME_PATHS),
        "E-0038 runtime artifact registry",
    )
    for name, expected_path in _RUNTIME_PATHS.items():
        _artifact_record(
            runtime_artifacts.get(name),
            f"E-0038 runtime artifact {name}",
            expected_path=expected_path,
        )
    if runtime.get("versions") != _RUNTIME_VERSIONS:
        raise E0038ExactMappingError("E-0038 runtime version authority drifted")
    contract = control.get("mapping_contract")
    if contract != {
        "source_row_count": 64,
        "source_rows_sha256": SOURCE_ROWS_SHA256,
        "source_row_ids_sha256": SOURCE_ROW_IDS_SHA256,
        "base_schema_node_count": 77,
        "schema_ids_sha256": SCHEMA_IDS_SHA256,
        "sealed_e0037_interval_count": 40,
        "sealed_e0037_intervals_sha256": SEALED_INTERVALS_SHA256,
        "base_projection_sha256": BASE_PROJECTION_SHA256,
        "result_projection_sha256": RESULT_PROJECTION_SHA256,
        "alias_receipt_sha256": ALIAS_RECEIPT_SHA256,
        "mapping_result_sha256": MAPPING_RESULT_SHA256,
        "exact_plan_sha256": EXACT_PLAN_SHA256,
        "exact_outcome_reason_sha256": EXACT_OUTCOME_REASON_SHA256,
        "changed_report_norm_ids": [4375, 5699],
        "base_alias_authority": BASE_ALIAS_AUTHORITY,
        "overlay_alias_authority": OVERLAY_ALIAS_AUTHORITY,
        "internal_mapper_compatibility_authority": BASE_ALIAS_AUTHORITY,
        "alias_policy_loaded_from_one_immutable_byte_snapshot": True,
        "full_sealed_interval_chain_required": True,
        "raw_projection_published": False,
        "raw_core_result_published_without_overlay_receipt": False,
        "exact_search_resource_cap_semantics": (
            "RETAINED_SIGNATURE_CERTIFICATE_BOUND_NOT_GENERATED_STATE_OR_TOTAL_COMPUTE_CAP"
        ),
        "actual_generated_and_retained_states_recorded": True,
        "result_input_binding_required": True,
    }:
        raise E0038ExactMappingError("E-0038 mapping contract drifted")
    if control.get("validation_order") != _VALIDATION_ORDER:
        raise E0038ExactMappingError("E-0038 pre-mapping validation order drifted")
    if control.get("forbidden_inputs") != _FORBIDDEN_INPUTS:
        raise E0038ExactMappingError("E-0038 forbidden-input contract drifted")
    if control.get("publication") != _PUBLICATION:
        raise E0038ExactMappingError("E-0038 publication contract drifted")
    if control.get("claim_boundaries") != {
        "mapping_only": _MAPPING_ONLY_CLAIM,
        "mapping_seal": _MAPPING_SEAL_CLAIM,
    }:
        raise E0038ExactMappingError("E-0038 claim boundaries drifted")
    return control, stable


def _load_prerequisites(
    project_root: Path,
    config_path: Path,
    reader: StableReader,
) -> _Prerequisites:
    """Validate control, every implementation, and every policy before data access."""

    control, control_stable = _load_control(project_root, config_path, reader)
    implementation_records = cast(dict[str, Any], control["implementation"])
    implementation_stable = {
        name: _verify_record(
            reader,
            project_root,
            implementation_records[name],
            f"E-0038 implementation {name}",
            expected_path=path,
            maximum_size=8 * 1024 * 1024,
        )
        for name, path in _IMPLEMENTATION_PATHS.items()
    }
    input_records = cast(dict[str, Any], control["input_authority"])
    policy_stable = {
        name: _verify_record(
            reader,
            project_root,
            input_records[name],
            f"E-0038 policy {name}",
            expected_path=_INPUT_PATHS[name],
            maximum_size=1024 * 1024,
        )
        for name in (
            "e0037_mapping_policy",
            "e0038_exact_mapping_policy",
            "e0038_alias_policy",
        )
    }
    runtime_records = cast(
        dict[str, Any],
        cast(dict[str, Any], control["runtime_authority"])["artifacts"],
    )
    runtime_stable = {
        name: _verify_record(
            reader,
            project_root,
            runtime_records[name],
            f"E-0038 runtime artifact {name}",
            expected_path=path,
            maximum_size=8 * 1024 * 1024,
        )
        for name, path in _RUNTIME_PATHS.items()
    }
    observed_versions = {
        "python": platform.python_version(),
        "rapidfuzz": package_distribution_version("rapidfuzz"),
        "pyyaml": package_distribution_version("PyYAML"),
    }
    if observed_versions != _RUNTIME_VERSIONS:
        raise E0038ExactMappingError("E-0038 runtime package versions drifted")
    return _Prerequisites(
        control=control,
        control_stable=control_stable,
        implementation_stable=implementation_stable,
        policy_stable=policy_stable,
        runtime_stable=runtime_stable,
    )


def _validate_artifact_ledger(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise E0038ExactMappingError(f"{label} must be an artifact ledger")
    for name, record in value.items():
        if not isinstance(name, str) or not name:
            raise E0038ExactMappingError(f"{label} has an invalid name")
        validated = _artifact_record(record, f"{label} {name}")
        lowered = cast(str, validated["path"]).casefold()
        if any(
            token in lowered
            for token in (
                "e-0030",
                "e0030",
                "e_0030",
                "e-0033",
                "e0033",
                "e_0033",
                "e-0034",
                "e0034",
                "e_0034",
                "review",
                "human",
                "qwen",
                "histor",
                "mongo",
                "numeric",
                "period",
                "unit",
            )
        ):
            raise E0038ExactMappingError(f"{label} contains a forbidden path")
    return value


def _validate_e0037_seal_before_mapping_open(
    seal: dict[str, Any],
    control: Mapping[str, Any],
) -> None:
    _exact_keys(
        seal,
        {
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
        },
        "E-0037 mapping seal",
    )
    expected_mapping = cast(dict[str, Any], control["input_authority"])["e0037_mapping_only"]
    if (
        seal.get("format_version") != 1
        or seal.get("experiment_id") != "E-0037"
        or seal.get("dataset_role") != "CALIBRATION"
        or seal.get("state") != "MAPPING_ONLY_HASH_SEALED_BEFORE_POSTJOIN"
        or seal.get("seal_git_dirty") is not False
        or _GIT_COMMIT.fullmatch(str(seal.get("seal_git_commit", ""))) is None
        or _GIT_COMMIT.fullmatch(str(seal.get("mapping_capture_git_commit", ""))) is None
        or seal.get("mapping_capture_git_commit") != seal.get("seal_git_commit")
        or seal.get("mapping_only") != expected_mapping
        or seal.get("schema_projection_sha256") != BASE_PROJECTION_SHA256
        or seal.get("row_count") != 64
        or seal.get("schema_disposition_count") != 77
        or seal.get("row_mapping_status_counts")
        != {"AMBIGUOUS_ACROSS_PATHS": 60, "NO_ADMISSIBLE_PAIR": 4}
    ):
        raise E0038ExactMappingError("E-0037 mapping seal identity drifted")
    if seal.get("postjoin_access") != {
        "mapping_only_validated_before_postjoin_access": True,
        "deterministic_mapping_replay_invocation_count": 1,
        "deterministic_mapping_replay_byte_equal": True,
        "e0030_opened": False,
        "e0033_opened": False,
        "e0034_opened": False,
        "mapper_replay_used_to_change_mapping": False,
    }:
        raise E0038ExactMappingError("E-0037 seal access proof drifted")
    if (
        seal.get("authority")
        != {
            "mapping_output_hash_identity": True,
            "numeric_value_or_status": False,
            "period_or_unit": False,
            "review_or_history": False,
            "accounting_or_excel": False,
        }
        or seal.get("claim_boundary") != _E0037_SEAL_CLAIM
    ):
        raise E0038ExactMappingError("E-0037 seal authority drifted")
    ledger = _exact_keys(
        seal.get("input_hash_ledger"),
        {
            "control",
            "mapping_only",
            "authentication_replay_inputs",
            "authentication_replay_implementation",
        },
        "E-0037 seal input ledger",
    )
    if ledger.get("mapping_only") != expected_mapping:
        raise E0038ExactMappingError("E-0037 seal mapping linkage drifted")
    _artifact_record(ledger.get("control"), "E-0037 seal control")
    replay_inputs = _validate_artifact_ledger(
        ledger.get("authentication_replay_inputs"),
        "E-0037 replay input ledger",
    )
    replay_implementation = _validate_artifact_ledger(
        ledger.get("authentication_replay_implementation"),
        "E-0037 replay implementation ledger",
    )
    if set(replay_inputs) != {
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
    } or set(replay_implementation) != {
        "source_structure_validator",
        "mapper",
        "integration",
        "capture_script",
    }:
        raise E0038ExactMappingError("E-0037 seal replay inventory drifted")


def _load_unique_s3_record(
    registry_bytes: bytes,
    expected: Mapping[str, Any],
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    try:
        text = registry_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise E0038ExactMappingError("S3 registry is not UTF-8") from exc
    lines = text.splitlines()
    if not lines or len(lines) > 1024 or any(not line.strip() for line in lines):
        raise E0038ExactMappingError("S3 registry line inventory is invalid")
    for index, line in enumerate(lines, start=1):
        record = _decode_json_object(line.encode("utf-8"), f"S3 registry line {index}")
        records.append(record)
    matches = [record for record in records if record.get("artifact_snapshot_id") == S3_SNAPSHOT_ID]
    if len(matches) != 1 or matches[0] != dict(expected):
        raise E0038ExactMappingError("S3 registry snapshot is absent, duplicated, or drifted")
    record = matches[0]
    probe = record.get("hydrate_probe")
    logical_paths = probe.get("logical_paths") if isinstance(probe, dict) else None
    if (
        record.get("restore_verified") is not True
        or not isinstance(probe, dict)
        or not isinstance(logical_paths, list)
        or probe.get("status") != "PASS"
        or probe.get("sealed_hashes_match") is not True
        or probe.get("restored_file_count") != record.get("file_count")
        or probe.get("reused_file_count_on_second_hydrate") != record.get("file_count")
        or E0037_MAPPING_ONLY_RELATIVE_PATH.as_posix() not in logical_paths
    ):
        raise E0038ExactMappingError("S3 registry snapshot lacks a passing restore proof")
    return record


def _load_e0037_authority(
    project_root: Path,
    prerequisites: _Prerequisites,
    reader: StableReader,
) -> _E0037Authority:
    """Open the mapping bytes only after seal and S3 recovery evidence validate."""

    inputs = cast(dict[str, Any], prerequisites.control["input_authority"])

    # Phase 1 after control/implementation: validate the committed E-0037 seal.
    seal_stable = _verify_record(
        reader,
        project_root,
        inputs["e0037_mapping_seal"],
        "E-0037 mapping seal",
        expected_path=E0037_MAPPING_SEAL_RELATIVE_PATH,
        maximum_size=1024 * 1024,
    )
    seal = _decode_json_object(seal_stable.payload, "E-0037 mapping seal")
    _validate_e0037_seal_before_mapping_open(seal, prerequisites.control)

    # Phase 2: require the unique registered S3 snapshot and restore PASS.
    registry_stable = _verify_record(
        reader,
        project_root,
        inputs["s3_snapshot_registry"],
        "S3 artifact snapshot registry",
        expected_path=S3_REGISTRY_RELATIVE_PATH,
        maximum_size=4 * 1024 * 1024,
    )
    s3_record = _load_unique_s3_record(
        registry_stable.payload,
        cast(dict[str, Any], inputs["s3_snapshot"]),
    )

    # Phase 3, deliberately last: stable O_NOFOLLOW read of mapping bytes.
    mapping_stable = _verify_record(
        reader,
        project_root,
        inputs["e0037_mapping_only"],
        "E-0037 mapping-only bytes",
        expected_path=E0037_MAPPING_ONLY_RELATIVE_PATH,
        maximum_size=4 * 1024 * 1024,
    )
    mapping = _decode_json_object(mapping_stable.payload, "E-0037 mapping-only bytes")
    try:
        rows, dispositions = _validate_mapping_only_payload(mapping)
    except (E0037SealedMappingError, TypeError, ValueError) as exc:
        raise E0038ExactMappingError("E-0037 mapping-only payload failed validation") from exc
    if len(rows) != 64 or len(dispositions) != 77:
        raise E0038ExactMappingError("E-0037 mapping-only cardinality drifted")
    ledger = cast(dict[str, Any], seal["input_hash_ledger"])
    if (
        mapping.get("capture_git_commit") != seal.get("mapping_capture_git_commit")
        or mapping.get("input_hash_ledger") != ledger["authentication_replay_inputs"]
        or mapping.get("implementation_hash_ledger")
        != ledger["authentication_replay_implementation"]
        or mapping.get("schema_projection", {}).get("projection_sha256") != BASE_PROJECTION_SHA256
    ):
        raise E0038ExactMappingError("E-0037 mapping-only/seal linkage drifted")
    return _E0037Authority(
        prerequisites=prerequisites,
        seal_stable=seal_stable,
        seal=seal,
        registry_stable=registry_stable,
        s3_record=s3_record,
        mapping_stable=mapping_stable,
        mapping=mapping,
    )


def _reconstruct_rows(mapping: Mapping[str, Any]) -> tuple[SourceStructureRowV2, ...]:
    raw_rows = mapping.get("rows")
    if not isinstance(raw_rows, list) or len(raw_rows) != 64:
        raise E0038ExactMappingError("E-0037 reconstruction requires exactly 64 rows")
    rows: list[SourceStructureRowV2] = []
    for expected_order, raw in enumerate(raw_rows):
        if not isinstance(raw, dict):
            raise E0038ExactMappingError("E-0037 reconstruction row is not an object")
        structure = raw.get("source_structure")
        labels = raw.get("semantic_proposals")
        if not isinstance(structure, dict) or not isinstance(labels, dict):
            raise E0038ExactMappingError("E-0037 reconstruction row evidence is absent")
        row_id = raw.get("row_id")
        relation = structure.get("mapper_relation_type")
        parent = structure.get("physical_parent_row_id")
        if (
            not isinstance(row_id, str)
            or not row_id
            or raw.get("source_order") != expected_order
            or relation not in {"UNKNOWN", "DIRECT_PARENT"}
            or (relation == "DIRECT_PARENT" and not isinstance(parent, str))
            or (relation == "UNKNOWN" and parent is not None)
        ):
            raise E0038ExactMappingError("E-0037 reconstructed row structure drifted")
        rows.append(
            SourceStructureRowV2(
                row_id=row_id,
                order=expected_order,
                labels_by_reader=dict(sorted(cast(dict[str, str], labels).items())),
                row_role=cast(str, structure["row_role"]),
                parent_row_id=cast(str | None, parent),
                relation_type=cast(str, relation),
                report_scope=cast(str, structure["report_scope"]),
                target_template_in_scope=cast(bool, structure["target_template_in_scope"]),
            )
        )
    if len({row.row_id for row in rows}) != 64:
        raise E0038ExactMappingError("E-0037 reconstructed row IDs are not unique")
    return tuple(rows)


def _reconstruct_base_projection(mapping: Mapping[str, Any]) -> SchemaProjectionV2:
    raw_projection = mapping.get("schema_projection")
    if not isinstance(raw_projection, dict):
        raise E0038ExactMappingError("E-0037 base projection is absent")
    raw_nodes = raw_projection.get("nodes")
    if not isinstance(raw_nodes, list) or len(raw_nodes) != 77:
        raise E0038ExactMappingError("E-0037 base projection must contain 77 nodes")
    nodes = tuple(
        SchemaProjectionNodeV2(
            report_norm_id=cast(int, raw["report_norm_id"]),
            canonical_name=cast(str, raw["display_name"]),
            structural_aliases=tuple(cast(list[str], raw["structural_aliases"])),
            statement_type="CDKT",
            display_order=cast(int, raw["display_order"]),
            parent_report_norm_id=cast(int | None, raw["parent_report_norm_id"]),
            child_report_norm_ids=tuple(cast(list[int], raw["child_report_norm_ids"])),
            hierarchy_level=cast(int | None, raw["hierarchy_level"]),
            section_path=tuple(cast(list[int], raw["section_path"])),
            scopes=tuple(cast(list[str], raw["scopes"])),
        )
        for raw in raw_nodes
        if isinstance(raw, dict)
    )
    if len(nodes) != 77:
        raise E0038ExactMappingError("E-0037 base projection node reconstruction failed")
    projection = SchemaProjectionV2(
        statement_type="CDKT",
        nodes=nodes,
        projection_sha256=cast(str, raw_projection["projection_sha256"]),
        alias_authority=cast(str, raw_projection["alias_authority"]),
    )
    if (
        projection.projection_sha256 != BASE_PROJECTION_SHA256
        or projection.alias_authority != BASE_ALIAS_AUTHORITY
    ):
        raise E0038ExactMappingError("E-0037 base projection identity drifted")
    return projection


def _reconstruct_sealed_intervals(mapping: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    raw_mapping = mapping.get("mapping")
    if not isinstance(raw_mapping, dict):
        raise E0038ExactMappingError("E-0037 mapping diagnostics are absent")
    intervals = raw_mapping.get("intervals")
    if not isinstance(intervals, list) or len(intervals) != 40:
        raise E0038ExactMappingError("E-0037 full sealed interval chain must have 40 entries")
    keys = (
        "interval_index",
        "previous_anchor_row_id",
        "previous_anchor_report_norm_id",
        "next_anchor_row_id",
        "next_anchor_report_norm_id",
        "row_ids",
        "report_norm_ids",
    )
    result: list[dict[str, Any]] = []
    for expected_index, interval in enumerate(intervals):
        if not isinstance(interval, dict) or interval.get("interval_index") != expected_index:
            raise E0038ExactMappingError("E-0037 sealed interval order drifted")
        result.append({key: interval.get(key) for key in keys})
    return tuple(result)


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _source_rows_digest(rows: Sequence[SourceStructureRowV2]) -> str:
    return _canonical_sha256(
        [
            {
                "labels_by_reader": sorted(row.labels_by_reader.items()),
                "order": row.order,
                "parent_row_id": row.parent_row_id,
                "relation_type": row.relation_type,
                "report_scope": row.report_scope,
                "row_id": row.row_id,
                "row_role": row.row_role,
                "target_template_in_scope": row.target_template_in_scope,
            }
            for row in rows
        ]
    )


def _internal_mapper_projection(
    overlay_projection: SchemaProjectionV2,
    receipt: Mapping[str, Any],
) -> SchemaProjectionV2:
    """Create the only mapper-compatible view; never expose it as an artifact."""

    if (
        overlay_projection.alias_authority != OVERLAY_ALIAS_AUTHORITY
        or receipt.get("alias_authority") != OVERLAY_ALIAS_AUTHORITY
        or receipt.get("result_projection_sha256") != RESULT_PROJECTION_SHA256
        or receipt.get("base_projection_sha256") != BASE_PROJECTION_SHA256
        or receipt.get("changed_report_norm_ids") != [4375, 5699]
        or receipt.get("collision_delta_pair_count") != 0
        or receipt.get("review_or_steward_approved") is not False
        or receipt.get("production_allowed") is not False
        or receipt.get("holdout_evidence_allowed") is not False
        or receipt.get("historical_alias_authority_allowed") is not False
        or receipt.get("numeric_period_or_value_features_allowed") is not False
    ):
        raise E0038ExactMappingError("E-0038 alias overlay receipt authority drifted")
    frozen_nodes = tuple(
        SchemaProjectionNodeV2(
            report_norm_id=node.report_norm_id,
            canonical_name=node.canonical_name,
            structural_aliases=tuple(node.structural_aliases),
            statement_type=node.statement_type,
            display_order=node.display_order,
            parent_report_norm_id=node.parent_report_norm_id,
            child_report_norm_ids=tuple(node.child_report_norm_ids),
            hierarchy_level=node.hierarchy_level,
            section_path=tuple(node.section_path),
            scopes=tuple(node.scopes),
        )
        for node in overlay_projection.nodes
    )
    return SchemaProjectionV2(
        statement_type=overlay_projection.statement_type,
        nodes=frozen_nodes,
        projection_sha256=overlay_projection.projection_sha256,
        alias_authority=BASE_ALIAS_AUTHORITY,
    )


def _outcome_bundle(
    outcome: E0038ExactSearchOutcome,
    alias_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    result_payload: dict[str, Any] | None = None
    internal_result_authority: str | None = None
    if outcome.result is not None:
        result_payload = outcome.result.to_dict()
        internal_result_authority = cast(
            str | None,
            result_payload.pop("schema_alias_authority", None),
        )
        if (
            internal_result_authority != BASE_ALIAS_AUTHORITY
            or result_payload.get("schema_projection_sha256") != RESULT_PROJECTION_SHA256
        ):
            raise E0038ExactMappingError("exact core returned a different projection identity")
    return {
        "alias_overlay_receipt": dict(alias_receipt),
        "alias_overlay_receipt_sha256": _canonical_sha256(alias_receipt),
        "effective_schema_alias_authority": OVERLAY_ALIAS_AUTHORITY,
        "mapper_compatibility_adapter": {
            "applied_in_memory_only": True,
            "internal_alias_authority": BASE_ALIAS_AUTHORITY,
            "core_result_internal_alias_authority": internal_result_authority,
            "node_content_or_projection_digest_changed": False,
            "raw_projection_published": False,
            "raw_core_result_published_without_overlay_receipt": False,
        },
        "exact_search": {
            "status": str(outcome.status),
            "reason": outcome.reason,
            "align_invocation_count": outcome.align_invocation_count,
            "main_search_pruned_states": outcome.main_search_pruned_states,
            "counterfactual_search_pruned_states": outcome.counterfactual_search_pruned_states,
            "plan": asdict(outcome.plan),
            "plan_sha256": _canonical_sha256(asdict(outcome.plan)),
            "reason_sha256": _canonical_sha256(outcome.reason),
            "resource_semantics": {
                "planned_retained_signature_work_bound": outcome.plan.total_signature_work_bound,
                "retained_signature_certificate_cap": outcome.plan.total_signature_work_cap,
                "cap_is_not_a_generated_state_or_total_compute_cap": True,
                "actual_generated_states": (
                    None if outcome.result is None else outcome.result.search.generated_states
                ),
                "actual_retained_states": (
                    None if outcome.result is None else outcome.result.search.retained_states
                ),
            },
            "mapping_result_sha256": (
                None if result_payload is None else _canonical_sha256(result_payload)
            ),
            "mapping_result_without_internal_alias_authority": result_payload,
        },
    }


def _encoded_json(payload: Mapping[str, Any]) -> bytes:
    try:
        return (
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise E0038ExactMappingError("E-0038 payload is not canonical JSON data") from exc


def _same_inode(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        stat.S_ISREG(left.st_mode)
        and stat.S_ISREG(right.st_mode)
        and left.st_dev == right.st_dev
        and left.st_ino == right.st_ino
        and left.st_size == right.st_size
    )


def _rollback_published_link(
    parent_descriptor: int,
    final_name: str,
    published_identity: os.stat_result,
) -> None:
    try:
        current = os.stat(final_name, dir_fd=parent_descriptor, follow_symlinks=False)
    except FileNotFoundError:
        return
    if not _same_inode(current, published_identity):
        raise E0038ExactMappingError(
            "cannot safely roll back E-0038 publication after identity replacement"
        )
    os.unlink(final_name, dir_fd=parent_descriptor)
    os.fsync(parent_descriptor)


def _exclusive_publish_json(
    project_root: Path,
    path: Path,
    payload: Mapping[str, Any],
    *,
    exclusive_parent_inventory: tuple[str, ...] | None = None,
) -> str:
    """Publish exclusively, then bind the link back to the fresh canonical path."""

    if not path.is_relative_to(project_root):
        raise E0038ExactMappingError("E-0038 output path escapes project root")
    relative = path.relative_to(project_root)
    try:
        parent, final_name = _open_or_create_parent_directory(
            project_root,
            relative,
            "E-0038 output",
        )
    except E0037SealedMappingError as exc:
        raise E0038ExactMappingError("cannot open E-0038 output parent") from exc
    encoded = _encoded_json(payload)
    digest = hashlib.sha256(encoded).hexdigest()
    temporary_name = f".{final_name}.{secrets.token_hex(16)}"
    temporary_created = False
    published_identity: os.stat_result | None = None
    try:
        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        try:
            descriptor = os.open(temporary_name, flags, 0o600, dir_fd=parent)
            temporary_created = True
        except OSError as exc:
            raise E0038ExactMappingError("cannot create temporary E-0038 artifact") from exc
        try:
            view = memoryview(encoded)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise E0038ExactMappingError("short write for temporary E-0038 artifact")
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.chmod(temporary_name, 0o644, dir_fd=parent, follow_symlinks=False)
        temporary_identity = os.stat(
            temporary_name,
            dir_fd=parent,
            follow_symlinks=False,
        )
        try:
            os.link(
                temporary_name,
                final_name,
                src_dir_fd=parent,
                dst_dir_fd=parent,
                follow_symlinks=False,
            )
        except OSError as exc:
            if exc.errno == errno.EEXIST:
                raise E0038ExactMappingError(
                    f"refusing to overwrite E-0038 artifact: {path}"
                ) from exc
            raise E0038ExactMappingError("cannot link E-0038 artifact") from exc
        published_identity = os.stat(final_name, dir_fd=parent, follow_symlinks=False)
        if not _same_inode(temporary_identity, published_identity):
            raise E0038ExactMappingError("E-0038 linked artifact identity mismatch")

        os.unlink(temporary_name, dir_fd=parent)
        temporary_created = False
        os.fsync(parent)

        # A held dirfd is insufficient: the directory may have been renamed and
        # replaced. Reopen the complete canonical chain and compare parent+file.
        fresh_parent, fresh_name = _open_existing_parent_directory(
            project_root,
            relative,
            "E-0038 published artifact",
        )
        try:
            held_parent = os.fstat(parent)
            canonical_parent = os.fstat(fresh_parent)
            canonical_file = os.stat(fresh_name, dir_fd=fresh_parent, follow_symlinks=False)
            canonical_inventory = tuple(sorted(os.listdir(fresh_parent)))
        finally:
            os.close(fresh_parent)
        if (
            not stat.S_ISDIR(held_parent.st_mode)
            or not stat.S_ISDIR(canonical_parent.st_mode)
            or (held_parent.st_dev, held_parent.st_ino)
            != (canonical_parent.st_dev, canonical_parent.st_ino)
            or not _same_inode(published_identity, canonical_file)
            or (
                exclusive_parent_inventory is not None
                and canonical_inventory != tuple(sorted(exclusive_parent_inventory))
            )
        ):
            raise E0038ExactMappingError(
                "E-0038 published parent/file detached from canonical path"
            )
        canonical = _read_from_fresh_canonical_path(
            project_root,
            path,
            "E-0038 published artifact",
            expected_size=len(encoded),
            maximum_size=max(len(encoded), 1),
        )
        if canonical.payload != encoded or canonical.artifact["sha256"] != digest:
            raise E0038ExactMappingError("E-0038 published bytes failed canonical revalidation")
        final_parent, _final_name = _open_existing_parent_directory(
            project_root,
            relative,
            "E-0038 final publication inventory",
        )
        try:
            final_parent_identity = os.fstat(final_parent)
            final_inventory = tuple(sorted(os.listdir(final_parent)))
        finally:
            os.close(final_parent)
        if (final_parent_identity.st_dev, final_parent_identity.st_ino) != (
            held_parent.st_dev,
            held_parent.st_ino,
        ) or (
            exclusive_parent_inventory is not None
            and final_inventory != tuple(sorted(exclusive_parent_inventory))
        ):
            raise E0038ExactMappingError("E-0038 final canonical inventory drifted")
        os.fsync(parent)
    except Exception as exc:
        if published_identity is not None:
            _rollback_published_link(parent, final_name, published_identity)
        if isinstance(exc, E0038ExactMappingError):
            raise
        raise E0038ExactMappingError("E-0038 publication revalidation failed") from exc
    finally:
        if temporary_created:
            try:
                os.unlink(temporary_name, dir_fd=parent)
                os.fsync(parent)
            except FileNotFoundError:
                pass
        os.close(parent)
    return digest


def _sanitized_git_environment() -> dict[str, str]:
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment["GIT_CONFIG_NOSYSTEM"] = "1"
    environment["GIT_CONFIG_GLOBAL"] = os.devnull
    return environment


def _git_bytes(project_root: Path, *arguments: str) -> bytes:
    try:
        return subprocess.run(
            ["git", "-C", str(project_root), *arguments],
            cwd=project_root,
            check=True,
            capture_output=True,
            env=_sanitized_git_environment(),
        ).stdout
    except subprocess.CalledProcessError as exc:
        raise E0038ExactMappingError("cannot query Git for E-0038") from exc


def _git(project_root: Path, *arguments: str) -> str:
    try:
        return _git_bytes(project_root, *arguments).decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise E0038ExactMappingError("Git returned non-UTF-8 metadata for E-0038") from exc


def _assert_git_root(project_root: Path) -> None:
    top_level = _git(project_root, "rev-parse", "--show-toplevel")
    if Path(top_level).resolve() != project_root.resolve():
        raise E0038ExactMappingError("Git top-level differs from the E-0038 project root")


def _git_commit(project_root: Path) -> str:
    _assert_git_root(project_root)
    commit = _git(project_root, "rev-parse", "--verify", "HEAD^{commit}")
    if _GIT_COMMIT.fullmatch(commit) is None:
        raise E0038ExactMappingError("cannot resolve E-0038 Git commit")
    return commit


def _clean_git_commit(project_root: Path) -> str:
    commit = _git_commit(project_root)
    index_records = [
        record for record in _git_bytes(project_root, "ls-files", "-v", "-z").split(b"\0") if record
    ]
    if not index_records or any(not record.startswith(b"H ") for record in index_records):
        raise E0038ExactMappingError(
            "E-0038 publication rejects non-normal Git index flags anywhere in the tree"
        )
    if _git(
        project_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--ignore-submodules=none",
    ):
        raise E0038ExactMappingError("E-0038 publication requires a clean Git worktree")
    if _git_commit(project_root) != commit:
        raise E0038ExactMappingError("Git HEAD changed during E-0038 clean-tree validation")
    return commit


def _assert_tracked_record_matches_head(
    project_root: Path,
    record: object,
    *,
    name: str,
    expected_path: Path,
    reader: StableReader = _read_stable_file,
) -> None:
    stable = _verify_record(
        reader,
        project_root,
        record,
        f"E-0038 HEAD-bound {name}",
        expected_path=expected_path,
        maximum_size=8 * 1024 * 1024,
    )
    _assert_git_root(project_root)
    blob = _git_bytes(
        project_root,
        "cat-file",
        "blob",
        f"HEAD:{expected_path.as_posix()}",
    )
    if blob != stable.payload or hashlib.sha256(blob).hexdigest() != stable.artifact["sha256"]:
        raise E0038ExactMappingError(f"{name} worktree bytes differ from the HEAD blob")


def _assert_payload_ledgers_match_head(
    project_root: Path,
    payload: Mapping[str, Any],
    reader: StableReader = _read_stable_file,
) -> None:
    input_paths = {"control": CONTROL_RELATIVE_PATH, **_INPUT_PATHS}
    tracked_paths: list[Path] = []
    inputs = cast(dict[str, Any], payload["input_hash_ledger"])
    for name, record in inputs.items():
        if name == "e0037_mapping_only":
            continue
        tracked_paths.append(input_paths[name])
        _assert_tracked_record_matches_head(
            project_root,
            record,
            name=f"input {name}",
            expected_path=input_paths[name],
            reader=reader,
        )
    implementations = cast(dict[str, Any], payload["implementation_hash_ledger"])
    for name, record in implementations.items():
        tracked_paths.append(_IMPLEMENTATION_PATHS[name])
        _assert_tracked_record_matches_head(
            project_root,
            record,
            name=f"implementation {name}",
            expected_path=_IMPLEMENTATION_PATHS[name],
            reader=reader,
        )
    runtime = cast(dict[str, Any], payload["runtime_hash_ledger"])
    for name, record in runtime.items():
        tracked_paths.append(_RUNTIME_PATHS[name])
        _assert_tracked_record_matches_head(
            project_root,
            record,
            name=f"runtime artifact {name}",
            expected_path=_RUNTIME_PATHS[name],
            reader=reader,
        )
    expected_index_records = {b"H " + path.as_posix().encode("utf-8") for path in tracked_paths}
    raw_records = _git_bytes(
        project_root,
        "ls-files",
        "-v",
        "-z",
        "--",
        *(path.as_posix() for path in tracked_paths),
    ).split(b"\0")
    actual_index_records = {record for record in raw_records if record}
    if actual_index_records != expected_index_records:
        raise E0038ExactMappingError(
            "E-0038 tracked ledgers are absent or use non-normal Git index flags"
        )


def _validate_commit(commit: str) -> str:
    if not isinstance(commit, str) or _GIT_COMMIT.fullmatch(commit) is None:
        raise E0038ExactMappingError("E-0038 capture commit is invalid")
    return commit


def build_e0038_mapping_only(
    project_root: Path,
    *,
    capture_git_commit: str,
    config_path: Path = CONTROL_RELATIVE_PATH,
    _reader: StableReader | None = None,
) -> dict[str, Any]:
    """Build the deterministic mapping payload in memory without publishing it."""

    root = project_root.resolve()
    commit = _validate_commit(capture_git_commit)
    reader = _read_stable_file if _reader is None else _reader
    prerequisites = _load_prerequisites(root, config_path, reader)
    authority = _load_e0037_authority(root, prerequisites, reader)
    rows = _reconstruct_rows(authority.mapping)
    if _source_rows_digest(rows) != SOURCE_ROWS_SHA256:
        raise E0038ExactMappingError("E-0037 reconstructed source-row evidence digest drifted")
    source_row_ids = [row.row_id for row in rows]
    if _canonical_sha256(source_row_ids) != SOURCE_ROW_IDS_SHA256:
        raise E0038ExactMappingError("E-0037 reconstructed source-row ID inventory drifted")
    base_projection = _reconstruct_base_projection(authority.mapping)
    schema_ids = [node.report_norm_id for node in base_projection.nodes]
    if _canonical_sha256(schema_ids) != SCHEMA_IDS_SHA256:
        raise E0038ExactMappingError("E-0037 reconstructed schema ID inventory drifted")
    sealed_intervals = _reconstruct_sealed_intervals(authority.mapping)
    if _canonical_sha256(sealed_intervals) != SEALED_INTERVALS_SHA256:
        raise E0038ExactMappingError("E-0037 sealed interval-chain digest drifted")

    base_policy_stable = prerequisites.policy_stable["e0037_mapping_policy"]
    exact_policy_stable = prerequisites.policy_stable["e0038_exact_mapping_policy"]
    alias_policy_stable = prerequisites.policy_stable["e0038_alias_policy"]
    base_policy = load_ordered_subgraph_v2_policy_bytes(
        base_policy_stable.payload,
        source_path=Path(cast(str, base_policy_stable.artifact["path"])),
    )
    exact_policy = load_ordered_subgraph_v2_policy_bytes(
        exact_policy_stable.payload,
        source_path=Path(cast(str, exact_policy_stable.artifact["path"])),
    )
    alias_policy = load_structural_alias_overlay_bytes(
        alias_policy_stable.payload,
        source_path=Path(cast(str, alias_policy_stable.artifact["path"])),
    )
    overlay = apply_structural_alias_overlay(base_projection, alias_policy)
    alias_receipt = overlay.receipt.to_dict()
    if alias_receipt.get("config_sha256") != alias_policy_stable.artifact["sha256"]:
        raise E0038ExactMappingError("alias receipt/config byte identity drifted")
    if _canonical_sha256(alias_receipt) != ALIAS_RECEIPT_SHA256:
        raise E0038ExactMappingError("full E-0038 alias receipt digest drifted")
    mapper_projection = _internal_mapper_projection(overlay.projection, alias_receipt)
    outcome = run_e0038_exact_search(
        rows,
        mapper_projection,
        base_projection=base_projection,
        sealed_interval_diagnostics=sealed_intervals,
        e0037_policy=base_policy,
        exact_policy=exact_policy,
    )
    bundle = _outcome_bundle(outcome, alias_receipt)
    result = outcome.result
    row_status_counts = (
        {}
        if result is None
        else dict(sorted(Counter(item.status for item in result.row_mappings).items()))
    )
    schema_status_counts = (
        {}
        if result is None
        else dict(sorted(Counter(item.status for item in result.schema_dispositions).items()))
    )
    payload = {
        "format_version": 1,
        "experiment_id": "E-0038",
        "dataset_role": "CALIBRATION",
        "state": MAPPING_ONLY_STATE,
        "capture_git_commit": commit,
        "capture_git_dirty": False,
        "input_hash_ledger": {
            "control": prerequisites.control_stable.artifact,
            "e0037_mapping_seal": authority.seal_stable.artifact,
            "s3_snapshot_registry": authority.registry_stable.artifact,
            "e0037_mapping_only": authority.mapping_stable.artifact,
            **{name: stable.artifact for name, stable in prerequisites.policy_stable.items()},
        },
        "implementation_hash_ledger": {
            name: stable.artifact for name, stable in prerequisites.implementation_stable.items()
        },
        "runtime_hash_ledger": {
            name: stable.artifact for name, stable in prerequisites.runtime_stable.items()
        },
        "runtime_versions": dict(_RUNTIME_VERSIONS),
        "e0037_input_authority": {
            "mapping_only_sha256": authority.mapping_stable.artifact["sha256"],
            "mapping_seal_sha256": authority.seal_stable.artifact["sha256"],
            "s3_snapshot_id": authority.s3_record["artifact_snapshot_id"],
            "s3_registry_record_sha256": _canonical_sha256(authority.s3_record),
            "s3_restore_verified": True,
            "s3_hydrate_probe_status": "PASS",
        },
        "reconstruction": {
            "source_row_count": len(rows),
            "source_row_ids": source_row_ids,
            "source_row_ids_sha256": _canonical_sha256(source_row_ids),
            "source_rows_sha256": _source_rows_digest(rows),
            "base_schema_node_count": len(base_projection.nodes),
            "base_schema_report_norm_ids": schema_ids,
            "base_schema_report_norm_ids_sha256": _canonical_sha256(schema_ids),
            "base_projection_sha256": base_projection.projection_sha256,
            "base_alias_authority": base_projection.alias_authority,
            "sealed_e0037_interval_count": len(sealed_intervals),
            "sealed_e0037_intervals_sha256": _canonical_sha256(sealed_intervals),
            "sealed_e0037_intervals": list(sealed_intervals),
        },
        "exact_mapping_bundle": bundle,
        "result_input_binding": {
            "source_rows_sha256": SOURCE_ROWS_SHA256,
            "source_row_ids_sha256": SOURCE_ROW_IDS_SHA256,
            "schema_ids_sha256": SCHEMA_IDS_SHA256,
            "sealed_e0037_intervals_sha256": SEALED_INTERVALS_SHA256,
            "base_projection_sha256": BASE_PROJECTION_SHA256,
            "result_projection_sha256": RESULT_PROJECTION_SHA256,
            "alias_receipt_sha256": ALIAS_RECEIPT_SHA256,
            "mapping_result_sha256": MAPPING_RESULT_SHA256,
            "exact_plan_sha256": EXACT_PLAN_SHA256,
            "exact_outcome_reason_sha256": EXACT_OUTCOME_REASON_SHA256,
            "e0037_mapping_only_sha256": authority.mapping_stable.artifact["sha256"],
            "e0037_mapping_seal_sha256": authority.seal_stable.artifact["sha256"],
            "s3_snapshot_record_sha256": _canonical_sha256(authority.s3_record),
            "policy_sha256": {
                name: stable.artifact["sha256"]
                for name, stable in prerequisites.policy_stable.items()
            },
            "implementation_sha256": {
                name: stable.artifact["sha256"]
                for name, stable in prerequisites.implementation_stable.items()
            },
            "runtime_artifact_sha256": {
                name: stable.artifact["sha256"]
                for name, stable in prerequisites.runtime_stable.items()
            },
            "runtime_versions": dict(_RUNTIME_VERSIONS),
        },
        "metrics": {
            "source_row_count": len(rows),
            "schema_node_count": len(base_projection.nodes),
            "sealed_e0037_interval_count": len(sealed_intervals),
            "exact_interval_count": len(outcome.plan.interval_bounds),
            "align_invocation_count": outcome.align_invocation_count,
            "row_mapping_status_counts": row_status_counts,
            "schema_disposition_status_counts": schema_status_counts,
            "selected_row_count": (
                0
                if result is None
                else sum(item.selected_report_norm_id is not None for item in result.row_mappings)
            ),
        },
        "access_contract": {
            "validation_order": _VALIDATION_ORDER,
            "control_and_implementation_validated_before_mapping_open": True,
            "e0037_seal_validated_before_mapping_open": True,
            "s3_registry_restore_pass_validated_before_mapping_open": True,
            "e0037_mapping_only_open_count": 1,
            "alias_overlay_invocation_count": 1,
            "exact_core_invocation_count": 1,
            "align_invocation_count": outcome.align_invocation_count,
            "e0030_opened": False,
            "e0033_opened": False,
            "e0034_opened": False,
            "review_or_human_labels_opened": False,
            "history_or_mongodb_opened": False,
            "qwen_raw_or_rejected_output_opened": False,
            "numeric_period_or_unit_features_passed": False,
            "fresh_canonical_input_identity_revalidated": True,
            "tracked_ledger_head_blob_binding_required_before_publication": True,
            "empty_mapping_directory_required_before_publication": True,
        },
        "authority": {
            "e0037_mapping_hash_and_restore_identity": True,
            "alias_candidates_are_calibration_hypotheses": True,
            "exact_zero_pruning_mechanism_evidence": outcome.result is not None,
            "schema_authority": False,
            "mapping_accuracy": False,
            "review_or_steward_approval": False,
            "numeric_value_or_status": False,
            "period_or_unit": False,
            "accounting_or_excel": False,
            "holdout_or_production": False,
        },
        "claim_boundary": _MAPPING_ONLY_CLAIM,
    }

    # Recheck every input after the exact search; no publication may use stale bytes.
    for label, stable in (
        ("E-0038 control", prerequisites.control_stable),
        *(prerequisites.implementation_stable.items()),
        *(prerequisites.policy_stable.items()),
        *(prerequisites.runtime_stable.items()),
        ("E-0037 mapping seal", authority.seal_stable),
        ("S3 artifact snapshot registry", authority.registry_stable),
        ("E-0037 mapping-only bytes", authority.mapping_stable),
    ):
        _assert_unchanged(reader, root, stable, str(label))
    normalized_payload = _decode_json_object(
        _encoded_json(payload),
        "constructed E-0038 mapping-only payload",
    )
    _validate_e0038_mapping_payload(
        normalized_payload,
        prerequisites.control,
        expected_control_artifact=prerequisites.control_stable.artifact,
        expected_git_commit=commit,
    )
    return normalized_payload


def _validate_e0038_mapping_payload(
    payload: Mapping[str, Any],
    control: Mapping[str, Any],
    *,
    expected_control_artifact: Mapping[str, Any],
    expected_git_commit: str,
) -> None:
    validated_git_commit = _validate_commit(expected_git_commit)
    _exact_keys(
        payload,
        {
            "format_version",
            "experiment_id",
            "dataset_role",
            "state",
            "capture_git_commit",
            "capture_git_dirty",
            "input_hash_ledger",
            "implementation_hash_ledger",
            "runtime_hash_ledger",
            "runtime_versions",
            "e0037_input_authority",
            "reconstruction",
            "exact_mapping_bundle",
            "result_input_binding",
            "metrics",
            "access_contract",
            "authority",
            "claim_boundary",
        },
        "E-0038 mapping-only payload",
    )
    if (
        payload.get("format_version") != 1
        or payload.get("experiment_id") != "E-0038"
        or payload.get("dataset_role") != "CALIBRATION"
        or payload.get("state") != MAPPING_ONLY_STATE
        or payload.get("capture_git_dirty") is not False
        or payload.get("capture_git_commit") != validated_git_commit
        or payload.get("claim_boundary") != _MAPPING_ONLY_CLAIM
    ):
        raise E0038ExactMappingError("E-0038 mapping-only identity drifted")

    input_ledger = _exact_keys(
        payload.get("input_hash_ledger"),
        {
            "control",
            "e0037_mapping_seal",
            "s3_snapshot_registry",
            "e0037_mapping_only",
            "e0037_mapping_policy",
            "e0038_exact_mapping_policy",
            "e0038_alias_policy",
        },
        "E-0038 mapping input ledger",
    )
    validated_control_artifact = _artifact_record(
        expected_control_artifact,
        "E-0038 expected mapping control",
        expected_path=CONTROL_RELATIVE_PATH,
    )
    if input_ledger.get("control") != validated_control_artifact:
        raise E0038ExactMappingError("E-0038 mapping control identity drifted")
    _artifact_record(
        input_ledger["control"],
        "E-0038 mapping control",
        expected_path=CONTROL_RELATIVE_PATH,
    )
    expected_inputs = cast(dict[str, Any], control["input_authority"])
    for name in set(input_ledger) - {"control"}:
        if input_ledger[name] != expected_inputs[name]:
            raise E0038ExactMappingError(f"E-0038 mapping input linkage drifted: {name}")
        _artifact_record(
            input_ledger[name],
            f"E-0038 mapping input {name}",
            expected_path=_INPUT_PATHS[name],
        )
    implementation_ledger = _exact_keys(
        payload.get("implementation_hash_ledger"),
        set(_IMPLEMENTATION_PATHS),
        "E-0038 mapping implementation ledger",
    )
    if implementation_ledger != control.get("implementation"):
        raise E0038ExactMappingError("E-0038 mapping implementation linkage drifted")
    for name, path in _IMPLEMENTATION_PATHS.items():
        _artifact_record(
            implementation_ledger[name],
            f"E-0038 mapping implementation {name}",
            expected_path=path,
        )
    runtime_ledger = _exact_keys(
        payload.get("runtime_hash_ledger"),
        set(_RUNTIME_PATHS),
        "E-0038 mapping runtime ledger",
    )
    runtime_control = cast(dict[str, Any], control["runtime_authority"])
    if runtime_ledger != runtime_control.get("artifacts"):
        raise E0038ExactMappingError("E-0038 mapping runtime artifact linkage drifted")
    for name, path in _RUNTIME_PATHS.items():
        _artifact_record(
            runtime_ledger[name],
            f"E-0038 mapping runtime artifact {name}",
            expected_path=path,
        )
    if payload.get("runtime_versions") != _RUNTIME_VERSIONS:
        raise E0038ExactMappingError("E-0038 mapping runtime versions drifted")

    e0037 = _exact_keys(
        payload.get("e0037_input_authority"),
        {
            "mapping_only_sha256",
            "mapping_seal_sha256",
            "s3_snapshot_id",
            "s3_registry_record_sha256",
            "s3_restore_verified",
            "s3_hydrate_probe_status",
        },
        "E-0038 upstream authority receipt",
    )
    if (
        e0037.get("mapping_only_sha256") != E0037_MAPPING_ONLY_SHA256
        or e0037.get("mapping_seal_sha256") != E0037_MAPPING_SEAL_SHA256
        or e0037.get("s3_snapshot_id") != S3_SNAPSHOT_ID
        or e0037.get("s3_registry_record_sha256") != S3_SNAPSHOT_RECORD_SHA256
        or e0037.get("s3_restore_verified") is not True
        or e0037.get("s3_hydrate_probe_status") != "PASS"
    ):
        raise E0038ExactMappingError("E-0038 upstream authority receipt drifted")

    reconstruction = _exact_keys(
        payload.get("reconstruction"),
        {
            "source_row_count",
            "source_row_ids",
            "source_row_ids_sha256",
            "source_rows_sha256",
            "base_schema_node_count",
            "base_schema_report_norm_ids",
            "base_schema_report_norm_ids_sha256",
            "base_projection_sha256",
            "base_alias_authority",
            "sealed_e0037_interval_count",
            "sealed_e0037_intervals_sha256",
            "sealed_e0037_intervals",
        },
        "E-0038 reconstruction receipt",
    )
    row_ids = reconstruction.get("source_row_ids")
    schema_ids = reconstruction.get("base_schema_report_norm_ids")
    intervals = reconstruction.get("sealed_e0037_intervals")
    if (
        reconstruction.get("source_row_count") != 64
        or not isinstance(row_ids, list)
        or len(row_ids) != 64
        or len(set(row_ids)) != 64
        or any(not isinstance(item, str) or not item for item in row_ids)
        or reconstruction.get("source_row_ids_sha256") != SOURCE_ROW_IDS_SHA256
        or _canonical_sha256(row_ids) != SOURCE_ROW_IDS_SHA256
        or reconstruction.get("source_rows_sha256") != SOURCE_ROWS_SHA256
        or reconstruction.get("base_schema_node_count") != 77
        or not isinstance(schema_ids, list)
        or len(schema_ids) != 77
        or len(set(schema_ids)) != 77
        or any(type(item) is not int or item <= 0 for item in schema_ids)
        or reconstruction.get("base_schema_report_norm_ids_sha256") != SCHEMA_IDS_SHA256
        or _canonical_sha256(schema_ids) != SCHEMA_IDS_SHA256
        or reconstruction.get("base_projection_sha256") != BASE_PROJECTION_SHA256
        or reconstruction.get("base_alias_authority") != BASE_ALIAS_AUTHORITY
        or reconstruction.get("sealed_e0037_interval_count") != 40
        or not isinstance(intervals, list)
        or len(intervals) != 40
        or reconstruction.get("sealed_e0037_intervals_sha256") != SEALED_INTERVALS_SHA256
        or _canonical_sha256(intervals) != SEALED_INTERVALS_SHA256
    ):
        raise E0038ExactMappingError("E-0038 reconstruction receipt drifted")

    result_input_binding = _exact_keys(
        payload.get("result_input_binding"),
        {
            "source_rows_sha256",
            "source_row_ids_sha256",
            "schema_ids_sha256",
            "sealed_e0037_intervals_sha256",
            "base_projection_sha256",
            "result_projection_sha256",
            "alias_receipt_sha256",
            "mapping_result_sha256",
            "exact_plan_sha256",
            "exact_outcome_reason_sha256",
            "e0037_mapping_only_sha256",
            "e0037_mapping_seal_sha256",
            "s3_snapshot_record_sha256",
            "policy_sha256",
            "implementation_sha256",
            "runtime_artifact_sha256",
            "runtime_versions",
        },
        "E-0038 result input binding",
    )
    expected_result_input_binding = {
        "source_rows_sha256": SOURCE_ROWS_SHA256,
        "source_row_ids_sha256": SOURCE_ROW_IDS_SHA256,
        "schema_ids_sha256": SCHEMA_IDS_SHA256,
        "sealed_e0037_intervals_sha256": SEALED_INTERVALS_SHA256,
        "base_projection_sha256": BASE_PROJECTION_SHA256,
        "result_projection_sha256": RESULT_PROJECTION_SHA256,
        "alias_receipt_sha256": ALIAS_RECEIPT_SHA256,
        "mapping_result_sha256": MAPPING_RESULT_SHA256,
        "exact_plan_sha256": EXACT_PLAN_SHA256,
        "exact_outcome_reason_sha256": EXACT_OUTCOME_REASON_SHA256,
        "e0037_mapping_only_sha256": input_ledger["e0037_mapping_only"]["sha256"],
        "e0037_mapping_seal_sha256": input_ledger["e0037_mapping_seal"]["sha256"],
        "s3_snapshot_record_sha256": S3_SNAPSHOT_RECORD_SHA256,
        "policy_sha256": {
            name: input_ledger[name]["sha256"]
            for name in (
                "e0037_mapping_policy",
                "e0038_exact_mapping_policy",
                "e0038_alias_policy",
            )
        },
        "implementation_sha256": {
            name: implementation_ledger[name]["sha256"] for name in _IMPLEMENTATION_PATHS
        },
        "runtime_artifact_sha256": {
            name: runtime_ledger[name]["sha256"] for name in _RUNTIME_PATHS
        },
        "runtime_versions": _RUNTIME_VERSIONS,
    }
    if result_input_binding != expected_result_input_binding:
        raise E0038ExactMappingError("E-0038 result/input hash binding drifted")

    bundle = _exact_keys(
        payload.get("exact_mapping_bundle"),
        {
            "alias_overlay_receipt",
            "alias_overlay_receipt_sha256",
            "effective_schema_alias_authority",
            "mapper_compatibility_adapter",
            "exact_search",
        },
        "E-0038 exact mapping bundle",
    )
    receipt = _exact_keys(
        bundle.get("alias_overlay_receipt"),
        {
            "status",
            "statement_type",
            "config_sha256",
            "config_size_bytes",
            "base_projection_sha256",
            "result_projection_sha256",
            "node_count",
            "changed_report_norm_ids",
            "unchanged_node_count",
            "base_collision_groups",
            "result_collision_groups",
            "new_collision_pairs",
            "collision_delta_pair_count",
            "score_audits",
            "alias_authority",
            "review_or_steward_approved",
            "production_allowed",
            "holdout_evidence_allowed",
            "historical_alias_authority_allowed",
            "numeric_period_or_value_features_allowed",
        },
        "E-0038 alias overlay receipt",
    )
    if (
        receipt.get("status") != "CALIBRATION_HYPOTHESIS_NOT_SCHEMA_AUTHORITY"
        or receipt.get("statement_type") != "CDKT"
        or receipt.get("config_sha256") != input_ledger["e0038_alias_policy"]["sha256"]
        or receipt.get("config_size_bytes") != input_ledger["e0038_alias_policy"]["size_bytes"]
        or receipt.get("base_projection_sha256") != BASE_PROJECTION_SHA256
        or receipt.get("result_projection_sha256") != RESULT_PROJECTION_SHA256
        or receipt.get("node_count") != 77
        or receipt.get("changed_report_norm_ids") != [4375, 5699]
        or receipt.get("unchanged_node_count") != 75
        or receipt.get("alias_authority") != OVERLAY_ALIAS_AUTHORITY
        or receipt.get("review_or_steward_approved") is not False
        or receipt.get("production_allowed") is not False
        or receipt.get("holdout_evidence_allowed") is not False
        or receipt.get("historical_alias_authority_allowed") is not False
        or receipt.get("numeric_period_or_value_features_allowed") is not False
        or not isinstance(receipt.get("base_collision_groups"), list)
        or receipt.get("result_collision_groups") != receipt.get("base_collision_groups")
        or receipt.get("new_collision_pairs") != []
        or receipt.get("collision_delta_pair_count") != 0
        or not isinstance(receipt.get("score_audits"), list)
        or len(cast(list[object], receipt["score_audits"])) != 2
        or bundle.get("alias_overlay_receipt_sha256") != ALIAS_RECEIPT_SHA256
        or _canonical_sha256(receipt) != ALIAS_RECEIPT_SHA256
        or bundle.get("effective_schema_alias_authority") != OVERLAY_ALIAS_AUTHORITY
    ):
        raise E0038ExactMappingError("E-0038 alias receipt linkage drifted")
    adapter = bundle.get("mapper_compatibility_adapter")
    if (
        not isinstance(adapter, dict)
        or adapter
        != {
            "applied_in_memory_only": True,
            "internal_alias_authority": BASE_ALIAS_AUTHORITY,
            "core_result_internal_alias_authority": adapter.get(
                "core_result_internal_alias_authority"
            ),
            "node_content_or_projection_digest_changed": False,
            "raw_projection_published": False,
            "raw_core_result_published_without_overlay_receipt": False,
        }
        or adapter.get("core_result_internal_alias_authority") != BASE_ALIAS_AUTHORITY
    ):
        raise E0038ExactMappingError("E-0038 internal authority adapter drifted")

    exact = _exact_keys(
        bundle.get("exact_search"),
        {
            "status",
            "reason",
            "align_invocation_count",
            "main_search_pruned_states",
            "counterfactual_search_pruned_states",
            "plan",
            "plan_sha256",
            "reason_sha256",
            "resource_semantics",
            "mapping_result_sha256",
            "mapping_result_without_internal_alias_authority",
        },
        "E-0038 exact-search receipt",
    )
    if (
        exact.get("status") != "EXACT_SEARCH_COMPLETE"
        or exact.get("reason") != EXACT_OUTCOME_REASON
        or exact.get("reason_sha256") != EXACT_OUTCOME_REASON_SHA256
        or _canonical_sha256(exact.get("reason")) != EXACT_OUTCOME_REASON_SHA256
        or exact.get("align_invocation_count") != 1
        or exact.get("main_search_pruned_states") != 0
        or exact.get("counterfactual_search_pruned_states") != 0
        or not isinstance(exact.get("plan"), dict)
    ):
        raise E0038ExactMappingError("E-0038 exact-search certificate drifted")
    plan = _exact_keys(
        exact["plan"],
        {
            "status",
            "reason",
            "interval_bounds",
            "maximum_monotone_signature_bound",
            "total_dp_cells",
            "total_cell_signature_sum_bound",
            "total_signature_work_bound",
            "e0037_bound_limit",
            "hard_cap",
            "total_signature_work_cap",
        },
        "E-0038 exact-search plan",
    )
    interval_bounds = plan.get("interval_bounds")
    if (
        exact.get("plan_sha256") != EXACT_PLAN_SHA256
        or _canonical_sha256(plan) != EXACT_PLAN_SHA256
        or plan.get("status") is not None
        or not isinstance(plan.get("reason"), str)
        or not plan.get("reason")
        or not isinstance(interval_bounds, list)
        or len(interval_bounds) != 42
        or plan.get("maximum_monotone_signature_bound") != 5005
        or plan.get("total_dp_cells") != 187
        or plan.get("total_cell_signature_sum_bound") != 19669
        or plan.get("total_signature_work_bound") != 136661
        or plan.get("e0037_bound_limit") != 5005
        or plan.get("hard_cap") != 8192
        or plan.get("total_signature_work_cap") != 150000
    ):
        raise E0038ExactMappingError("E-0038 exact-search plan values drifted")
    resources = _exact_keys(
        exact.get("resource_semantics"),
        {
            "planned_retained_signature_work_bound",
            "retained_signature_certificate_cap",
            "cap_is_not_a_generated_state_or_total_compute_cap",
            "actual_generated_states",
            "actual_retained_states",
        },
        "E-0038 exact-search resource semantics",
    )
    mapping_result = exact.get("mapping_result_without_internal_alias_authority")
    if mapping_result is not None and not isinstance(mapping_result, dict):
        raise E0038ExactMappingError("E-0038 mapping result is malformed")
    mapping_search = mapping_result.get("search") if isinstance(mapping_result, dict) else None
    if mapping_result is not None and not isinstance(mapping_search, dict):
        raise E0038ExactMappingError("E-0038 mapping search receipt is malformed")
    if resources != {
        "planned_retained_signature_work_bound": 136661,
        "retained_signature_certificate_cap": 150000,
        "cap_is_not_a_generated_state_or_total_compute_cap": True,
        "actual_generated_states": 9977,
        "actual_retained_states": 6833,
    }:
        raise E0038ExactMappingError("E-0038 resource semantics drifted")
    if mapping_result is None:
        raise E0038ExactMappingError("E-0038 exact result is unexpectedly absent")
    else:
        if (
            exact.get("mapping_result_sha256") != MAPPING_RESULT_SHA256
            or _canonical_sha256(mapping_result) != MAPPING_RESULT_SHA256
        ):
            raise E0038ExactMappingError("E-0038 full mapping-result digest drifted")
        _exact_keys(
            mapping_result,
            {
                "status",
                "automatic_selection_allowed",
                "anchors",
                "intervals",
                "best_path",
                "runner_up_path",
                "score_margin",
                "ranked_paths",
                "row_mappings",
                "schema_dispositions",
                "reason",
                "schema_projection_sha256",
                "policy_sha256",
                "search",
            },
            "E-0038 mapping result without internal alias authority",
        )
        row_mappings = mapping_result.get("row_mappings")
        schema_dispositions = mapping_result.get("schema_dispositions")
        result_intervals = mapping_result.get("intervals")
        if (
            "schema_alias_authority" in mapping_result
            or adapter.get("core_result_internal_alias_authority") != BASE_ALIAS_AUTHORITY
            or mapping_result.get("status") != "RESOLVED"
            or mapping_result.get("automatic_selection_allowed") is not True
            or mapping_result.get("schema_projection_sha256") != RESULT_PROJECTION_SHA256
            or mapping_result.get("policy_sha256")
            != input_ledger["e0038_exact_mapping_policy"]["sha256"]
            or not isinstance(row_mappings, list)
            or len(row_mappings) != 64
            or not isinstance(schema_dispositions, list)
            or len(schema_dispositions) != 77
            or not isinstance(result_intervals, list)
            or len(result_intervals) != 42
        ):
            raise E0038ExactMappingError("E-0038 mapping result linkage drifted")
        for index, record in enumerate(cast(list[object], row_mappings)):
            validated = _exact_keys(
                record,
                {
                    "row_id",
                    "status",
                    "selected_report_norm_id",
                    "candidate_report_norm_ids",
                    "interval_index",
                    "reason",
                },
                f"E-0038 row mapping {index}",
            )
            if validated.get("row_id") != cast(list[str], row_ids)[index]:
                raise E0038ExactMappingError("E-0038 result/source row order drifted")
        for index, record in enumerate(cast(list[object], schema_dispositions)):
            validated = _exact_keys(
                record,
                {
                    "report_norm_id",
                    "status",
                    "selected_row_id",
                    "candidate_row_ids",
                    "reason",
                },
                f"E-0038 schema disposition {index}",
            )
            if validated.get("report_norm_id") != cast(list[int], schema_ids)[index]:
                raise E0038ExactMappingError("E-0038 result/schema order drifted")
        expected_search = {
            "algorithm": "ANCHORED_INTERVAL_K_BEST_MONOTONE_DP_FAIL_CLOSED",
            "intervals": 42,
            "dp_cells": 675,
            "generated_states": 9977,
            "retained_states": 6833,
            "pruned_states": 0,
            "main_search_pruned_states": 0,
            "counterfactual_search_pruned_states": 0,
            "counterfactual_searches": 17,
            "beam_width_per_dp_cell": 8192,
        }
        if mapping_search != expected_search:
            raise E0038ExactMappingError("E-0038 exact result search counters drifted")

    row_records = cast(list[dict[str, Any]], mapping_result["row_mappings"])
    schema_records = cast(list[dict[str, Any]], mapping_result["schema_dispositions"])
    expected_metrics = {
        "source_row_count": 64,
        "schema_node_count": 77,
        "sealed_e0037_interval_count": 40,
        "exact_interval_count": 42,
        "align_invocation_count": 1,
        "row_mapping_status_counts": dict(
            sorted(Counter(record["status"] for record in row_records).items())
        ),
        "schema_disposition_status_counts": dict(
            sorted(Counter(record["status"] for record in schema_records).items())
        ),
        "selected_row_count": sum(
            record["selected_report_norm_id"] is not None for record in row_records
        ),
    }
    if payload.get("metrics") != expected_metrics:
        raise E0038ExactMappingError("E-0038 mapping metrics drifted")
    access = payload.get("access_contract")
    expected_access = {
        "validation_order": _VALIDATION_ORDER,
        "control_and_implementation_validated_before_mapping_open": True,
        "e0037_seal_validated_before_mapping_open": True,
        "s3_registry_restore_pass_validated_before_mapping_open": True,
        "e0037_mapping_only_open_count": 1,
        "alias_overlay_invocation_count": 1,
        "exact_core_invocation_count": 1,
        "align_invocation_count": exact.get("align_invocation_count"),
        "e0030_opened": False,
        "e0033_opened": False,
        "e0034_opened": False,
        "review_or_human_labels_opened": False,
        "history_or_mongodb_opened": False,
        "qwen_raw_or_rejected_output_opened": False,
        "numeric_period_or_unit_features_passed": False,
        "fresh_canonical_input_identity_revalidated": True,
        "tracked_ledger_head_blob_binding_required_before_publication": True,
        "empty_mapping_directory_required_before_publication": True,
    }
    if access != expected_access:
        raise E0038ExactMappingError("E-0038 mapping access contract drifted")
    expected_authority = {
        "e0037_mapping_hash_and_restore_identity": True,
        "alias_candidates_are_calibration_hypotheses": True,
        "exact_zero_pruning_mechanism_evidence": mapping_result is not None,
        "schema_authority": False,
        "mapping_accuracy": False,
        "review_or_steward_approval": False,
        "numeric_value_or_status": False,
        "period_or_unit": False,
        "accounting_or_excel": False,
        "holdout_or_production": False,
    }
    if payload.get("authority") != expected_authority:
        raise E0038ExactMappingError("E-0038 mapping authority drifted")


def _recheck_payload_ledgers(
    project_root: Path,
    payload: Mapping[str, Any],
    reader: StableReader,
) -> None:
    input_paths = {"control": CONTROL_RELATIVE_PATH, **_INPUT_PATHS}
    for name, record in cast(dict[str, Any], payload["input_hash_ledger"]).items():
        _verify_record(
            reader,
            project_root,
            record,
            f"E-0038 immediate input recheck {name}",
            expected_path=input_paths[name],
            maximum_size=8 * 1024 * 1024,
        )
    for name, record in cast(dict[str, Any], payload["implementation_hash_ledger"]).items():
        _verify_record(
            reader,
            project_root,
            record,
            f"E-0038 immediate implementation recheck {name}",
            expected_path=_IMPLEMENTATION_PATHS[name],
            maximum_size=8 * 1024 * 1024,
        )
    for name, record in cast(dict[str, Any], payload["runtime_hash_ledger"]).items():
        _verify_record(
            reader,
            project_root,
            record,
            f"E-0038 immediate runtime recheck {name}",
            expected_path=_RUNTIME_PATHS[name],
            maximum_size=8 * 1024 * 1024,
        )


def _mapping_output_inventory(
    project_root: Path,
    *,
    require_mapping: bool,
) -> tuple[str, ...]:
    relative_directory = MAPPING_ONLY_RELATIVE_PATH.parent
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        current = os.open(project_root, flags)
    except OSError as exc:
        raise E0038ExactMappingError("cannot open project root for mapping inventory") from exc
    try:
        for part in relative_directory.parts:
            try:
                following = os.open(part, flags, dir_fd=current)
            except OSError as exc:
                if exc.errno == errno.ENOENT and not require_mapping:
                    return ()
                raise E0038ExactMappingError(
                    "cannot traverse canonical E-0038 mapping inventory"
                ) from exc
            os.close(current)
            current = following
        inventory = tuple(sorted(os.listdir(current)))
        expected = (MAPPING_ONLY_RELATIVE_PATH.name,) if require_mapping else ()
        if inventory != expected:
            raise E0038ExactMappingError(
                "E-0038 mapping directory does not have the exact one-file inventory"
            )
        if require_mapping:
            item = os.stat(
                MAPPING_ONLY_RELATIVE_PATH.name,
                dir_fd=current,
                follow_symlinks=False,
            )
            if not stat.S_ISREG(item.st_mode):
                raise E0038ExactMappingError("E-0038 mapping inventory item is not regular")
        return inventory
    finally:
        os.close(current)


def dry_run_e0038_mapping_only(
    project_root: Path,
    *,
    config_path: Path = CONTROL_RELATIVE_PATH,
) -> dict[str, Any]:
    """Execute all mapping logic in memory without requiring a clean worktree."""

    root = project_root.resolve()
    return build_e0038_mapping_only(
        root,
        capture_git_commit=_git_commit(root),
        config_path=config_path,
    )


def capture_e0038_mapping_only(
    project_root: Path,
    *,
    config_path: Path = CONTROL_RELATIVE_PATH,
    output_path: Path = MAPPING_ONLY_RELATIVE_PATH,
) -> dict[str, Any]:
    """Publish mapping-only bytes atomically from a clean Git commit."""

    root = project_root.resolve()
    _mapping_output_inventory(root, require_mapping=False)
    commit = _clean_git_commit(root)
    output = _canonical_path(root, output_path, MAPPING_ONLY_RELATIVE_PATH, "mapping output")
    if output.exists() or output.is_symlink():
        raise E0038ExactMappingError(f"refusing to overwrite E-0038 artifact: {output}")
    payload = build_e0038_mapping_only(
        root,
        capture_git_commit=commit,
        config_path=config_path,
    )
    _recheck_payload_ledgers(root, payload, _read_stable_file)
    _assert_payload_ledgers_match_head(root, payload)
    if _clean_git_commit(root) != commit:
        raise E0038ExactMappingError("Git commit changed during E-0038 mapping capture")
    _exclusive_publish_json(
        root,
        output,
        payload,
        exclusive_parent_inventory=(MAPPING_ONLY_RELATIVE_PATH.name,),
    )
    return payload


def _validate_e0038_mapping_seal_payload(
    payload: Mapping[str, Any],
    control: Mapping[str, Any],
    *,
    expected_control_artifact: Mapping[str, Any],
    expected_mapping_artifact: Mapping[str, Any],
    expected_git_commit: str,
) -> None:
    validated_git_commit = _validate_commit(expected_git_commit)
    _exact_keys(
        payload,
        {
            "format_version",
            "experiment_id",
            "dataset_role",
            "state",
            "seal_git_commit",
            "seal_git_dirty",
            "mapping_capture_git_commit",
            "inventory",
            "mapping_status",
            "result_projection_sha256",
            "input_hash_ledger",
            "replay",
            "access_contract",
            "authority",
            "claim_boundary",
        },
        "E-0038 mapping seal payload",
    )
    if (
        payload.get("format_version") != 1
        or payload.get("experiment_id") != "E-0038"
        or payload.get("dataset_role") != "CALIBRATION"
        or payload.get("state") != MAPPING_SEAL_STATE
        or payload.get("seal_git_dirty") is not False
        or payload.get("seal_git_commit") != validated_git_commit
        or payload.get("mapping_capture_git_commit") != validated_git_commit
        or payload.get("mapping_status") != "EXACT_SEARCH_COMPLETE"
        or payload.get("result_projection_sha256") != RESULT_PROJECTION_SHA256
        or payload.get("claim_boundary") != _MAPPING_SEAL_CLAIM
    ):
        raise E0038ExactMappingError("E-0038 mapping seal identity drifted")
    inventory = _exact_keys(
        payload.get("inventory"),
        {"file_count", "files"},
        "E-0038 seal inventory",
    )
    if (
        inventory.get("file_count") != 1
        or not isinstance(inventory.get("files"), list)
        or len(inventory["files"]) != 1
        or _artifact_record(
            inventory["files"][0],
            "E-0038 sealed mapping file",
            expected_path=MAPPING_ONLY_RELATIVE_PATH,
        )
        != inventory["files"][0]
    ):
        raise E0038ExactMappingError("E-0038 exact one-file inventory drifted")
    validated_mapping_artifact = _artifact_record(
        expected_mapping_artifact,
        "E-0038 expected sealed mapping file",
        expected_path=MAPPING_ONLY_RELATIVE_PATH,
    )
    if inventory["files"][0] != validated_mapping_artifact:
        raise E0038ExactMappingError("E-0038 seal expected mapping identity drifted")
    ledger = _exact_keys(
        payload.get("input_hash_ledger"),
        {
            "control",
            "mapping_only",
            "deterministic_replay_inputs",
            "deterministic_replay_implementation",
            "deterministic_replay_runtime",
            "deterministic_replay_runtime_versions",
        },
        "E-0038 seal input ledger",
    )
    if (
        ledger.get("mapping_only") != inventory["files"][0]
        or ledger.get("mapping_only") != validated_mapping_artifact
    ):
        raise E0038ExactMappingError("E-0038 seal inventory/hash ledger drifted")
    validated_control_artifact = _artifact_record(
        expected_control_artifact,
        "E-0038 expected seal control",
        expected_path=CONTROL_RELATIVE_PATH,
    )
    if ledger.get("control") != validated_control_artifact:
        raise E0038ExactMappingError("E-0038 seal outer control identity drifted")
    _artifact_record(
        ledger["control"],
        "E-0038 seal control",
        expected_path=CONTROL_RELATIVE_PATH,
    )
    if not isinstance(ledger.get("deterministic_replay_inputs"), dict) or not isinstance(
        ledger.get("deterministic_replay_implementation"), dict
    ):
        raise E0038ExactMappingError("E-0038 seal replay ledgers are absent")
    replay_inputs = _exact_keys(
        ledger["deterministic_replay_inputs"],
        {
            "control",
            "e0037_mapping_seal",
            "s3_snapshot_registry",
            "e0037_mapping_only",
            "e0037_mapping_policy",
            "e0038_exact_mapping_policy",
            "e0038_alias_policy",
        },
        "E-0038 seal deterministic input ledger",
    )
    _artifact_record(
        replay_inputs["control"],
        "E-0038 seal deterministic control",
        expected_path=CONTROL_RELATIVE_PATH,
    )
    if replay_inputs["control"] != validated_control_artifact:
        raise E0038ExactMappingError("E-0038 seal replay control identity drifted")
    control_inputs = cast(dict[str, Any], control["input_authority"])
    if any(
        replay_inputs[name] != control_inputs[name] for name in replay_inputs if name != "control"
    ):
        raise E0038ExactMappingError("E-0038 seal deterministic input linkage drifted")
    if ledger.get("deterministic_replay_implementation") != control.get("implementation"):
        raise E0038ExactMappingError("E-0038 seal deterministic implementation drifted")
    if (
        ledger.get("deterministic_replay_runtime")
        != cast(dict[str, Any], control["runtime_authority"])["artifacts"]
        or ledger.get("deterministic_replay_runtime_versions") != _RUNTIME_VERSIONS
    ):
        raise E0038ExactMappingError("E-0038 seal runtime linkage drifted")
    replay = payload.get("replay")
    if replay != {
        "deterministic_replay_invocation_count": 1,
        "exact_byte_equality": True,
        "mapping_core_result_used_to_change_published_mapping": False,
        "clean_git_commit_equal": True,
        "tracked_ledger_head_blob_binding_required": True,
    }:
        raise E0038ExactMappingError("E-0038 deterministic replay receipt drifted")
    if payload.get("access_contract") != {
        "mapping_only_validated_before_replay": True,
        "review_opened": False,
        "history_opened": False,
        "e0030_opened": False,
        "e0033_opened": False,
        "e0034_opened": False,
        "qwen_raw_or_rejected_output_opened": False,
        "numeric_period_or_unit_features_passed": False,
        "fresh_canonical_mapping_identity_revalidated": True,
        "exact_mapping_directory_inventory_validated_twice": True,
    }:
        raise E0038ExactMappingError("E-0038 seal access contract drifted")
    if payload.get("authority") != {
        "exact_one_file_hash_identity": True,
        "deterministic_replay_byte_identity": True,
        "schema_authority": False,
        "mapping_accuracy": False,
        "review_or_steward_approval": False,
        "numeric_period_or_unit": False,
        "accounting_excel_holdout_or_production": False,
    }:
        raise E0038ExactMappingError("E-0038 seal authority drifted")
    if control.get("claim_boundaries", {}).get("mapping_seal") != _MAPPING_SEAL_CLAIM:
        raise E0038ExactMappingError("E-0038 control/seal claim linkage drifted")


def _assemble_mapping_seal(
    *,
    commit: str,
    control_stable: _StableFile,
    mapping_stable: _StableFile,
    mapping_payload: Mapping[str, Any],
) -> dict[str, Any]:
    bundle = cast(dict[str, Any], mapping_payload["exact_mapping_bundle"])
    exact = cast(dict[str, Any], bundle["exact_search"])
    payload = {
        "format_version": 1,
        "experiment_id": "E-0038",
        "dataset_role": "CALIBRATION",
        "state": MAPPING_SEAL_STATE,
        "seal_git_commit": commit,
        "seal_git_dirty": False,
        "mapping_capture_git_commit": mapping_payload["capture_git_commit"],
        "inventory": {
            "file_count": 1,
            "files": [mapping_stable.artifact],
        },
        "mapping_status": exact["status"],
        "result_projection_sha256": RESULT_PROJECTION_SHA256,
        "input_hash_ledger": {
            "control": control_stable.artifact,
            "mapping_only": mapping_stable.artifact,
            "deterministic_replay_inputs": mapping_payload["input_hash_ledger"],
            "deterministic_replay_implementation": mapping_payload["implementation_hash_ledger"],
            "deterministic_replay_runtime": mapping_payload["runtime_hash_ledger"],
            "deterministic_replay_runtime_versions": mapping_payload["runtime_versions"],
        },
        "replay": {
            "deterministic_replay_invocation_count": 1,
            "exact_byte_equality": True,
            "mapping_core_result_used_to_change_published_mapping": False,
            "clean_git_commit_equal": True,
            "tracked_ledger_head_blob_binding_required": True,
        },
        "access_contract": {
            "mapping_only_validated_before_replay": True,
            "review_opened": False,
            "history_opened": False,
            "e0030_opened": False,
            "e0033_opened": False,
            "e0034_opened": False,
            "qwen_raw_or_rejected_output_opened": False,
            "numeric_period_or_unit_features_passed": False,
            "fresh_canonical_mapping_identity_revalidated": True,
            "exact_mapping_directory_inventory_validated_twice": True,
        },
        "authority": {
            "exact_one_file_hash_identity": True,
            "deterministic_replay_byte_identity": True,
            "schema_authority": False,
            "mapping_accuracy": False,
            "review_or_steward_approval": False,
            "numeric_period_or_unit": False,
            "accounting_excel_holdout_or_production": False,
        },
        "claim_boundary": _MAPPING_SEAL_CLAIM,
    }
    return payload


def capture_e0038_mapping_seal(
    project_root: Path,
    *,
    config_path: Path = CONTROL_RELATIVE_PATH,
    mapping_only_path: Path = MAPPING_ONLY_RELATIVE_PATH,
    output_path: Path = MAPPING_SEAL_RELATIVE_PATH,
) -> dict[str, Any]:
    """Replay and hash-seal exactly one mapping file before review access."""

    root = project_root.resolve()
    commit = _clean_git_commit(root)
    _mapping_output_inventory(root, require_mapping=True)
    reader = _read_stable_file
    prerequisites = _load_prerequisites(root, config_path, reader)
    mapping_path = _canonical_path(
        root,
        mapping_only_path,
        MAPPING_ONLY_RELATIVE_PATH,
        "mapping-only artifact",
    )
    output = _canonical_path(root, output_path, MAPPING_SEAL_RELATIVE_PATH, "mapping seal")
    if output.exists() or output.is_symlink():
        raise E0038ExactMappingError(f"refusing to overwrite E-0038 artifact: {output}")
    mapping_stable = _stable_read(
        reader,
        root,
        mapping_path,
        "E-0038 mapping-only artifact",
        maximum_size=16 * 1024 * 1024,
    )
    mapping_payload = _decode_json_object(
        mapping_stable.payload,
        "E-0038 mapping-only artifact",
    )
    _validate_e0038_mapping_payload(
        mapping_payload,
        prerequisites.control,
        expected_control_artifact=prerequisites.control_stable.artifact,
        expected_git_commit=commit,
    )
    if mapping_payload.get("capture_git_commit") != commit:
        raise E0038ExactMappingError("E-0038 mapping and seal Git commits differ")

    replay_payload = build_e0038_mapping_only(
        root,
        capture_git_commit=commit,
        config_path=config_path,
    )
    replay_bytes = _encoded_json(replay_payload)
    if replay_payload != mapping_payload or replay_bytes != mapping_stable.payload:
        raise E0038ExactMappingError("E-0038 deterministic replay bytes differ")
    if replay_payload["input_hash_ledger"]["control"] != prerequisites.control_stable.artifact:
        raise E0038ExactMappingError("E-0038 replay used a different control identity")

    seal_payload = _assemble_mapping_seal(
        commit=commit,
        control_stable=prerequisites.control_stable,
        mapping_stable=mapping_stable,
        mapping_payload=mapping_payload,
    )
    _validate_e0038_mapping_seal_payload(
        seal_payload,
        prerequisites.control,
        expected_control_artifact=prerequisites.control_stable.artifact,
        expected_mapping_artifact=mapping_stable.artifact,
        expected_git_commit=commit,
    )
    _assert_unchanged(reader, root, mapping_stable, "E-0038 mapping-only artifact")
    _assert_unchanged(reader, root, prerequisites.control_stable, "E-0038 control")
    _recheck_payload_ledgers(root, mapping_payload, reader)
    _assert_payload_ledgers_match_head(root, mapping_payload, reader)
    _mapping_output_inventory(root, require_mapping=True)
    if _clean_git_commit(root) != commit:
        raise E0038ExactMappingError("Git commit changed during E-0038 mapping sealing")
    _exclusive_publish_json(root, output, seal_payload)
    return seal_payload
