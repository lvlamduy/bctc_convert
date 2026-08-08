"""Formal, answer-free E-0040 mapping capture and deterministic sealing.

The module has one deliberately narrow data dependency: the exact E-0037
mapping-only bytes whose seal and bounded-S3 restore record are authenticated
before those bytes are opened.  It never imports a prior mapping experiment,
review flow, numeric/post-join flow, or history integration.  The E-0040 core
receives a scrubbed in-memory view containing only source structure, semantic
label proposals, and the 77-node base projection.
"""

from __future__ import annotations

import errno
import hashlib
import json
import math
import os
import platform
import re
import secrets
import stat
import subprocess
import sys
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib.metadata import version as package_distribution_version
from pathlib import Path
from typing import Any, cast

import yaml
from yaml.constructor import ConstructorError
from yaml.events import AliasEvent

from bctc_ai.mapping.e0040_calibration_challenger import (
    E0040ChallengerError,
    E0040ChallengerResult,
    align_e0040_calibration_challenger,
    load_e0040_policy_bytes,
    projection_from_sealed_mapping_payload,
    source_rows_from_sealed_mapping_payload,
)
from bctc_ai.mapping.ordered_subgraph_v2 import load_ordered_subgraph_v2_policy_bytes


class E0040FormalMappingError(RuntimeError):
    """Raised when the formal E-0040 contract cannot be proved safely."""


CONTROL_RELATIVE_PATH = Path("config/experiments/e0040-mbb-cdkt-formal-mapping.yaml")
MAPPING_ONLY_RELATIVE_PATH = Path(
    "output/calibration/e0040-mbb-cdkt-formal-mapping/mapping_only.json"
)
MAPPING_SEAL_RELATIVE_PATH = Path("docs/experiments/E-0040-mbb-cdkt-formal-mapping-seal.json")
E0037_MAPPING_ONLY_RELATIVE_PATH = Path(
    "output/calibration/e0037-mbb-cdkt-sealed-evidence-mapping/mapping_only.json"
)
E0037_MAPPING_SEAL_RELATIVE_PATH = Path("docs/experiments/E-0037-mbb-cdkt-mapping-only-seal.json")
S3_REGISTRY_RELATIVE_PATH = Path("data/registered/s3_artifact_snapshot_registry.jsonl")
E0040_POLICY_RELATIVE_PATH = Path("config/mapping/e0040-cdkt-semantic-normalization.yaml")
MAPPER_POLICY_RELATIVE_PATH = Path("config/mapping/e0040-ordered-subgraph-v2-exact.yaml")

MAPPING_ONLY_STATE = "E0040_GENERIC_CHALLENGER_MAPPING_ONLY_READY_FOR_HASH_SEAL"
MAPPING_SEAL_STATE = "E0040_GENERIC_CHALLENGER_MAPPING_HASH_SEALED"
BASE_PROJECTION_SHA256 = "7025ca729c01a3f2030af38e9745a0ee8d72b1dad60c8d4e3b7cf749e5eb860c"
RESULT_PROJECTION_SHA256 = "5c3c4a09650beda8eca21e5a00fe459e052ae7cc8d735359bc41a58a391da9b0"
E0040_POLICY_SHA256 = "eba3a1380f44f34958398edb13076dc3a87da95fc5ff347968a1a2c023e3995a"
E0040_POLICY_SIZE = 2185
MAPPER_POLICY_SHA256 = "2f18880339b8e2c04ec3ba900919f174f8af478515adfbfb0e43ff80ddd13268"
MAPPER_POLICY_SIZE = 2082
E0040_CORE_SHA256 = "c379ccf784868ec5b2f40714be00c402147b2b9a94e06b917a3e2cd6b926609b"
E0040_CORE_SIZE = 47333
MAPPER_SHA256 = "cf737243cbcecf919a2cf2012aa269655341b5c8c6b8c4038c76ed510a68b40a"
MAPPER_SIZE = 81923
E0037_MAPPING_ONLY_SHA256 = "e18f6b20825f93b20023c0d89caca1737481008b244696594852ca9fa972f99e"
E0037_MAPPING_ONLY_SIZE = 646393
E0037_MAPPING_SEAL_SHA256 = "665aa1b3ac96881df0a4cd7b2f7da2425c3635ad1e8ea024e299b668c79ed0e5"
E0037_MAPPING_SEAL_SIZE = 6016
S3_REGISTRY_SHA256 = "25da6b205a775d87eca8e4ffe55e3f762ee64e92cbb7190c2834708a7de0d78d"
S3_REGISTRY_SIZE = 6050
S3_SNAPSHOT_ID = "20260807T170440Z-e0037-source-and-mapping-seal-e18f6b20825f"
S3_SNAPSHOT_RECORD_SHA256 = "829ac8f0220ffa1c42ccbb65659e44ea7f062c44ee203ec4a91ef091e98cb067"
S3_SNAPSHOT_LINE_SHA256 = "b6034efbdb279bb793f1f641b29fd5b1efc26e348e272ee2802097f46c6b77d0"
S3_SNAPSHOT_LINE_SIZE = 1317
SOURCE_ROW_IDS_SHA256 = "b4fe87949522195ded7beae958cb5235aa36805db102b0f49675e29d855863d0"
SCHEMA_IDS_SHA256 = "c8467e5ae646924500548cacab46b7e1e8440106c110997da31eed349014edbb"
SCRUBBED_EVIDENCE_SHA256 = "5499f97323288ffff1ca9bf767aac3a24ec3a71ec0cfd69e6512a74f7cd3b1be"
SCRUBBED_EVIDENCE_SIZE = 51212
SOURCE_EVIDENCE_RECEIPT_SHA256 = "c7961f59ea0cb8850af3926579954abdc100731f183526337be442215759ff70"
CHALLENGER_RESULT_SHA256 = "2e49d8623692fde9fd4a5a87f9c2e2159941b0f3ded7b7b16dddac2ab1e85fbd"
CHALLENGER_RESULT_SIZE = 700869
BASELINE_PAIRS_SHA256 = "77167590e57381f8d724c713b4814e1fb2b64656643fad1f0d54dcc60f2eb416"
FINAL_PAIRS_SHA256 = "066c2c3352d65c067e7048ef55b46e6e990c3ad6a5aed94c2a1011eaba002c75"
FINAL_PAIRS_SIZE = 2014
FINAL_RESULT_SHA256 = "15edfc7e349a48cec62fd5bad4bcfc506dcf2c8272055620135b2cfe6d91a29d"
FINAL_RESULT_SIZE = 347961
NORMALIZATION_SHA256 = "09175c45fa93b4172c1f2fe1742b93a49aab3498119a451c4126f1be30b36088"
COLLISION_AUDIT_SHA256 = "f00504266416e99c574ed3f93204735eeec36c39f4c416c54073dfada21ce97a"

_SHA256 = re.compile(r"[0-9a-f]{64}")
_GIT_COMMIT = re.compile(r"[0-9a-f]{40}")
_MAX_JSON_BYTES = 16 * 1024 * 1024
_MAX_YAML_BYTES = 1024 * 1024
_MAX_REGISTRY_LINES = 1024

_MAPPING_ONLY_CLAIM = (
    "E-0040 is a calibration-only, answer-free CDKT mapping challenger over the exact "
    "sealed E-0037 source-structure and semantic-proposal evidence and its exact 77-node "
    "base projection. Generic semantic normalization and a bounded combined-parent role "
    "hypothesis produce machine mappings with exhaustive zero-pruning diagnostics. This "
    "does not establish schema authority, mapping accuracy, review approval, numeric or "
    "period truth, accounting validity, Excel correctness, holdout performance, or "
    "production readiness."
)
_MAPPING_SEAL_CLAIM = (
    "This artifact hash-seals exactly one E-0040 mapping-only file after deterministic "
    "byte-equal replay at the same clean mechanism commit. It adds no schema, mapping-"
    "accuracy, review, numeric, period, accounting, Excel, holdout, or production claim."
)
_E0037_SEAL_CLAIM = (
    "This artifact seals the E-0037 mapping-only bytes before any E-0030 period/unit or "
    "E-0034 numeric/status evidence is opened. It does not add, rerun, repair, or reinterpret "
    "a mapping and makes no numeric, accounting, Excel, holdout, or production claim."
)
_FORBIDDEN_INPUTS = [
    "E0038_E0039_MAPPING_OUTPUTS_OR_ALIASES",
    "REVIEW_OR_STEWARD_ANSWERS",
    "NUMERIC_STATUS_OR_POSTJOIN_ARTIFACTS",
    "PERIOD_UNIT_OR_SOURCE_SCOPE_ANSWER_FEATURES",
    "HISTORY_MONGODB_OR_LEDGER_FEATURES",
    "HOLDOUT_FEATURES_OR_LABELS",
    "QWEN_RAW_REJECTED_OUTPUT_OR_TOKEN_STREAM",
]
_VALIDATION_ORDER = [
    "CONTROL_IMPLEMENTATION_POLICY_RUNTIME",
    "E0037_MAPPING_SEAL",
    "S3_UNIQUE_RESTORE_RECORD",
    "E0037_MAPPING_ONLY_BYTES",
    "SCRUBBED_SOURCE_AND_BASE_PROJECTION",
    "E0040_CHALLENGER",
]
_PUBLICATION = {
    "canonical_paths_only": True,
    "exclusive_no_overwrite": True,
    "clean_git_before_and_immediately_before_publication": True,
    "tracked_ledgers_bound_to_head_blobs": True,
    "stable_nofollow_input_reads_and_identity_rechecks": True,
    "fresh_canonical_chain_revalidated_after_link": True,
    "mapping_directory_exact_one_file_inventory": True,
    "deterministic_sealer_byte_replay": True,
    "safe_identity_bound_rollback": True,
}
_INPUT_PATHS = {
    "e0037_mapping_seal": E0037_MAPPING_SEAL_RELATIVE_PATH,
    "s3_snapshot_registry": S3_REGISTRY_RELATIVE_PATH,
    "e0037_mapping_only": E0037_MAPPING_ONLY_RELATIVE_PATH,
    "e0040_policy": E0040_POLICY_RELATIVE_PATH,
    "e0040_mapper_policy": MAPPER_POLICY_RELATIVE_PATH,
}
_IMPLEMENTATION_PATHS = {
    "text_normalization": Path("src/bctc_ai/core/text.py"),
    "mapper": Path("src/bctc_ai/mapping/ordered_subgraph_v2.py"),
    "challenger": Path("src/bctc_ai/mapping/e0040_calibration_challenger.py"),
    "formal_integration": Path("src/bctc_ai/evaluation/e0040_formal_mapping.py"),
    "capture_script": Path("scripts/experiments/capture_e0040_mbb_cdkt_formal_mapping.py"),
    "seal_script": Path("scripts/experiments/capture_e0040_mbb_cdkt_formal_mapping_seal.py"),
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
_FORBIDDEN_PRELOADED_MODULES = frozenset(
    {
        "bctc_ai.evaluation.e0037_evidence_assembly",
        "bctc_ai.evaluation.e0037_sealed_mapping",
    }
)
_FORBIDDEN_PRELOADED_MODULE_TOKENS = (
    "e0038",
    "e0039",
    "e0041",
    "review",
    "holdout",
    "numeric",
    "mongodb",
    "qwen",
    "postjoin",
    "post_mapping",
)


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects aliases and duplicate keys."""

    def compose_node(self, parent: yaml.Node | None, index: int | None) -> yaml.Node:
        if self.check_event(AliasEvent):
            event = self.peek_event()
            raise ConstructorError(
                "while composing E-0040 formal control",
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


@dataclass(frozen=True)
class _StableFile:
    path: Path
    payload: bytes
    identity: tuple[int, int, int, int, int, int]
    artifact: dict[str, Any]


@dataclass(frozen=True)
class _Prerequisites:
    control: dict[str, Any]
    control_stable: _StableFile
    implementation_stable: dict[str, _StableFile]
    policy_stable: dict[str, _StableFile]
    runtime_stable: dict[str, _StableFile]


@dataclass(frozen=True)
class _E0037Authority:
    seal_stable: _StableFile
    seal: dict[str, Any]
    registry_stable: _StableFile
    s3_record: dict[str, Any]
    s3_line_artifact: dict[str, Any]
    mapping_stable: _StableFile
    mapping: dict[str, Any]


StableReader = Callable[..., _StableFile]


def _assert_answer_free_process() -> None:
    contaminated = sorted(
        name
        for name in sys.modules
        if name.startswith("bctc_ai.")
        and (
            name in _FORBIDDEN_PRELOADED_MODULES
            or any(token in name.casefold() for token in _FORBIDDEN_PRELOADED_MODULE_TOKENS)
        )
    )
    if contaminated:
        raise E0040FormalMappingError(
            "E-0040 formal process is contaminated by forbidden preloaded modules: "
            + ", ".join(contaminated)
        )


def _exact_keys(value: object, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise E0040FormalMappingError(f"{label} keyset drifted")
    return cast(dict[str, Any], value)


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _decode_json_object(payload: bytes, label: str) -> dict[str, Any]:
    if type(payload) is not bytes or not payload or len(payload) > _MAX_JSON_BYTES:
        raise E0040FormalMappingError(f"{label} byte size is invalid")
    try:
        decoded = json.loads(
            payload.decode("utf-8"),
            parse_constant=_reject_nonfinite,
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise E0040FormalMappingError(f"cannot decode {label} as strict JSON") from exc
    if not isinstance(decoded, dict):
        raise E0040FormalMappingError(f"{label} must be a JSON object")
    return decoded


def _decode_control(payload: bytes) -> dict[str, Any]:
    if type(payload) is not bytes or not payload or len(payload) > _MAX_YAML_BYTES:
        raise E0040FormalMappingError("E-0040 formal control byte size is invalid")
    try:
        decoded = yaml.load(payload.decode("utf-8"), Loader=_UniqueKeySafeLoader)
    except (UnicodeDecodeError, yaml.YAMLError, ValueError, RecursionError) as exc:
        raise E0040FormalMappingError("cannot decode E-0040 formal control") from exc
    if not isinstance(decoded, dict):
        raise E0040FormalMappingError("E-0040 formal control must be a YAML object")
    return decoded


def _canonical_compact_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise E0040FormalMappingError("value is not canonical finite JSON data") from exc


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_compact_bytes(value)).hexdigest()


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
    except (TypeError, ValueError, RecursionError) as exc:
        raise E0040FormalMappingError("E-0040 payload is not canonical finite JSON") from exc


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
        type(path) is not str
        or not path
        or Path(path).is_absolute()
        or ".." in Path(path).parts
        or type(digest) is not str
        or _SHA256.fullmatch(digest) is None
        or type(size) is not int
        or size < 0
        or (expected_path is not None and path != expected_path.as_posix())
    ):
        raise E0040FormalMappingError(f"{label} artifact identity is invalid")
    return record


def _stat_identity(value: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _canonical_input_path(
    project_root: Path,
    supplied: Path,
    expected: Path,
    label: str,
) -> Path:
    if supplied.is_absolute() or supplied.as_posix() != expected.as_posix():
        raise E0040FormalMappingError(f"{label} must use canonical path {expected}")
    if not project_root.is_absolute():
        raise E0040FormalMappingError("project root must be absolute")
    return project_root / expected


def _open_existing_parent_directory(
    project_root: Path,
    relative: Path,
    label: str,
) -> tuple[int, str]:
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise E0040FormalMappingError(f"unsafe project-relative path for {label}")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        current = os.open(project_root, flags)
    except OSError as exc:
        raise E0040FormalMappingError(f"cannot open project root for {label}") from exc
    try:
        for part in relative.parts[:-1]:
            try:
                following = os.open(part, flags, dir_fd=current)
            except OSError as exc:
                raise E0040FormalMappingError(
                    f"cannot traverse fresh canonical path for {label}"
                ) from exc
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
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise E0040FormalMappingError(f"unsafe project-relative output path for {label}")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        current = os.open(project_root, flags)
    except OSError as exc:
        raise E0040FormalMappingError(f"cannot open project root for {label}") from exc
    try:
        for part in relative.parts[:-1]:
            try:
                following = os.open(part, flags, dir_fd=current)
            except OSError as exc:
                if exc.errno != errno.ENOENT:
                    raise E0040FormalMappingError(
                        f"cannot traverse output path for {label}"
                    ) from exc
                try:
                    os.mkdir(part, 0o755, dir_fd=current)
                    os.fsync(current)
                except OSError as mkdir_exc:
                    if mkdir_exc.errno != errno.EEXIST:
                        raise E0040FormalMappingError(
                            f"cannot create output directory for {label}"
                        ) from mkdir_exc
                try:
                    following = os.open(part, flags, dir_fd=current)
                except OSError as open_exc:
                    raise E0040FormalMappingError(
                        f"cannot open created output directory for {label}"
                    ) from open_exc
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
        raise E0040FormalMappingError(f"{label} path escapes project root")
    if type(maximum_size) is not int or maximum_size <= 0:
        raise E0040FormalMappingError(f"{label} maximum size is invalid")
    relative = path.relative_to(project_root)
    parent, final_name = _open_existing_parent_directory(project_root, relative, label)
    held_parent_identity = _stat_identity(os.fstat(parent))
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    before: os.stat_result
    after: os.stat_result
    final: os.stat_result
    remaining = 0
    growth = b""
    chunks: list[bytes] = []
    try:
        try:
            descriptor = os.open(final_name, flags, dir_fd=parent)
        except OSError as exc:
            raise E0040FormalMappingError(f"cannot open fresh canonical {label}") from exc
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                raise E0040FormalMappingError(f"fresh canonical {label} is not regular")
            if before.st_size > maximum_size:
                raise E0040FormalMappingError(f"fresh canonical {label} exceeds size bound")
            if expected_size is not None and before.st_size != expected_size:
                raise E0040FormalMappingError(f"fresh canonical {label} size drifted")
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
    finally:
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
        raise E0040FormalMappingError(f"fresh canonical {label} changed during read")
    recheck_parent, recheck_name = _open_existing_parent_directory(
        project_root,
        relative,
        f"{label} post-read recheck",
    )
    try:
        recheck_parent_identity = _stat_identity(os.fstat(recheck_parent))
        recheck = os.stat(recheck_name, dir_fd=recheck_parent, follow_symlinks=False)
    except OSError as exc:
        raise E0040FormalMappingError(f"cannot revalidate canonical identity for {label}") from exc
    finally:
        os.close(recheck_parent)
    if recheck_parent_identity != held_parent_identity or _stat_identity(recheck) != identity:
        raise E0040FormalMappingError(f"canonical identity changed after reading {label}")
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
    except (OSError, ValueError, E0040FormalMappingError) as exc:
        if isinstance(exc, E0040FormalMappingError):
            raise
        raise E0040FormalMappingError(f"cannot stable-read {label}") from exc


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
    path = project_root / expected_path
    stable = _stable_read(
        reader,
        project_root,
        path,
        label,
        expected_size=cast(int, identity["size_bytes"]),
        maximum_size=maximum_size,
    )
    if stable.artifact != identity:
        raise E0040FormalMappingError(f"{label} differs from its pinned identity")
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
    if (
        current.identity != original.identity
        or current.artifact != original.artifact
        or current.payload != original.payload
    ):
        raise E0040FormalMappingError(f"{label} changed after validation")


def _assert_finite_tree(value: object, label: str, *, depth: int = 0) -> None:
    if depth > 128:
        raise E0040FormalMappingError(f"{label} exceeds nesting cap")
    if isinstance(value, float) and not math.isfinite(value):
        raise E0040FormalMappingError(f"{label} contains a non-finite number")
    if isinstance(value, dict):
        if len(value) > 100_000:
            raise E0040FormalMappingError(f"{label} mapping exceeds item cap")
        for key, item in value.items():
            if type(key) is not str:
                raise E0040FormalMappingError(f"{label} contains a non-string key")
            _assert_finite_tree(item, label, depth=depth + 1)
    elif isinstance(value, (list, tuple)):
        if len(value) > 100_000:
            raise E0040FormalMappingError(f"{label} sequence exceeds item cap")
        for item in value:
            _assert_finite_tree(item, label, depth=depth + 1)


def _expected_identity(path: Path, digest: str, size: int) -> dict[str, Any]:
    return {"path": path.as_posix(), "sha256": digest, "size_bytes": size}


def _assert_answer_free_formal_paths(control: Mapping[str, Any]) -> None:
    forbidden_tokens = (
        "e0038",
        "e-0038",
        "e0039",
        "e-0039",
        "review",
        "numeric",
        "postjoin",
        "post_join",
        "history",
        "holdout",
        "qwen",
    )
    ledgers: list[Mapping[str, Any]] = []
    for key in ("input_authority", "implementation"):
        value = control.get(key)
        if isinstance(value, Mapping):
            ledgers.append(value)
    runtime = control.get("runtime_authority")
    if isinstance(runtime, Mapping) and isinstance(runtime.get("artifacts"), Mapping):
        ledgers.append(cast(Mapping[str, Any], runtime["artifacts"]))
    for ledger in ledgers:
        for record in ledger.values():
            if not isinstance(record, Mapping):
                continue
            path = record.get("path")
            if type(path) is str and any(token in path.casefold() for token in forbidden_tokens):
                raise E0040FormalMappingError("formal ledger contains a forbidden path")


def _load_control(
    project_root: Path,
    config_path: Path,
    reader: StableReader,
) -> tuple[dict[str, Any], _StableFile]:
    control_path = _canonical_input_path(
        project_root,
        config_path,
        CONTROL_RELATIVE_PATH,
        "E-0040 formal control",
    )
    stable = _stable_read(
        reader,
        project_root,
        control_path,
        "E-0040 formal control",
        maximum_size=_MAX_YAML_BYTES,
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
            "limitations",
            "claim_boundaries",
        },
        "E-0040 formal control",
    )
    if (
        control.get("version") != 1
        or control.get("experiment_id") != "E-0040"
        or control.get("dataset_role") != "CALIBRATION"
        or control.get("design")
        != "SEALED_E0037_ANSWER_FREE_GENERIC_CHALLENGER_THEN_DETERMINISTIC_HASH_SEAL"
        or control.get("state") != "READY_FOR_MAPPING_ONLY_THEN_HASH_SEAL"
    ):
        raise E0040FormalMappingError("E-0040 formal control identity drifted")
    outputs = _exact_keys(
        control.get("phase_outputs"),
        {"mapping_only", "mapping_seal"},
        "E-0040 phase outputs",
    )
    if outputs != {
        "mapping_only": {
            "path": MAPPING_ONLY_RELATIVE_PATH.as_posix(),
            "required_state": MAPPING_ONLY_STATE,
            "encoding": "UTF8_JSON_SORTED_KEYS_INDENT2_NEWLINE_NO_NAN_V1",
        },
        "mapping_seal": {
            "path": MAPPING_SEAL_RELATIVE_PATH.as_posix(),
            "required_state": MAPPING_SEAL_STATE,
            "encoding": "UTF8_JSON_SORTED_KEYS_INDENT2_NEWLINE_NO_NAN_V1",
            "inventory_file_count": 1,
            "inventory_paths": [MAPPING_ONLY_RELATIVE_PATH.as_posix()],
        },
    }:
        raise E0040FormalMappingError("E-0040 phase-output contract drifted")

    inputs = _exact_keys(
        control.get("input_authority"),
        {*_INPUT_PATHS, "s3_snapshot"},
        "E-0040 input authority",
    )
    for name, expected_path in _INPUT_PATHS.items():
        _artifact_record(inputs.get(name), f"E-0040 input {name}", expected_path=expected_path)
    expected_inputs = {
        "e0037_mapping_seal": _expected_identity(
            E0037_MAPPING_SEAL_RELATIVE_PATH,
            E0037_MAPPING_SEAL_SHA256,
            E0037_MAPPING_SEAL_SIZE,
        ),
        "s3_snapshot_registry": _expected_identity(
            S3_REGISTRY_RELATIVE_PATH,
            S3_REGISTRY_SHA256,
            S3_REGISTRY_SIZE,
        ),
        "e0037_mapping_only": _expected_identity(
            E0037_MAPPING_ONLY_RELATIVE_PATH,
            E0037_MAPPING_ONLY_SHA256,
            E0037_MAPPING_ONLY_SIZE,
        ),
        "e0040_policy": _expected_identity(
            E0040_POLICY_RELATIVE_PATH,
            E0040_POLICY_SHA256,
            E0040_POLICY_SIZE,
        ),
        "e0040_mapper_policy": _expected_identity(
            MAPPER_POLICY_RELATIVE_PATH,
            MAPPER_POLICY_SHA256,
            MAPPER_POLICY_SIZE,
        ),
    }
    if any(inputs[name] != identity for name, identity in expected_inputs.items()):
        raise E0040FormalMappingError("E-0040 pinned input identity drifted")
    snapshot = inputs.get("s3_snapshot")
    if not isinstance(snapshot, dict) or _canonical_sha256(snapshot) != S3_SNAPSHOT_RECORD_SHA256:
        raise E0040FormalMappingError("E-0037 S3 snapshot record identity drifted")
    probe = snapshot.get("hydrate_probe")
    logical_paths = probe.get("logical_paths") if isinstance(probe, dict) else None
    manifest = snapshot.get("manifest")
    run_record = snapshot.get("run_record")
    if (
        snapshot.get("artifact_snapshot_id") != S3_SNAPSHOT_ID
        or snapshot.get("dataset_role") != "CALIBRATION"
        or snapshot.get("format_version") != 1
        or snapshot.get("file_count") != 2
        or snapshot.get("policy") != "S3_BOUNDED_ARTIFACT_SNAPSHOT_V1"
        or snapshot.get("restore_verified") is not True
        or not isinstance(probe, dict)
        or probe.get("status") != "PASS"
        or probe.get("sealed_hashes_match") is not True
        or probe.get("restored_file_count") != 2
        or probe.get("reused_file_count_on_second_hydrate") != 2
        or not isinstance(logical_paths, list)
        or E0037_MAPPING_ONLY_RELATIVE_PATH.as_posix() not in logical_paths
        or not isinstance(manifest, dict)
        or manifest.get("sha256")
        != "b7b2b5bd4249d93fc8bca2210228ffd000eb36e5ebc0bb7167dde4e774478c8c"
        or not isinstance(run_record, dict)
        or run_record.get("sha256")
        != "68b35baa1f3993021db5e550b87bd42af515076dd84e2e968248a27d02a22a34"
    ):
        raise E0040FormalMappingError("E-0037 S3 restore authority drifted")

    implementation = _exact_keys(
        control.get("implementation"),
        set(_IMPLEMENTATION_PATHS),
        "E-0040 implementation ledger",
    )
    for name, expected_path in _IMPLEMENTATION_PATHS.items():
        _artifact_record(
            implementation.get(name),
            f"E-0040 implementation {name}",
            expected_path=expected_path,
        )
    if implementation["challenger"] != _expected_identity(
        _IMPLEMENTATION_PATHS["challenger"], E0040_CORE_SHA256, E0040_CORE_SIZE
    ) or implementation["mapper"] != _expected_identity(
        _IMPLEMENTATION_PATHS["mapper"], MAPPER_SHA256, MAPPER_SIZE
    ):
        raise E0040FormalMappingError("E-0040 core implementation identity drifted")

    runtime = _exact_keys(
        control.get("runtime_authority"),
        {"artifacts", "versions"},
        "E-0040 runtime authority",
    )
    runtime_artifacts = _exact_keys(
        runtime.get("artifacts"),
        set(_RUNTIME_PATHS),
        "E-0040 runtime artifact ledger",
    )
    for name, expected_path in _RUNTIME_PATHS.items():
        _artifact_record(
            runtime_artifacts.get(name),
            f"E-0040 runtime artifact {name}",
            expected_path=expected_path,
        )
    if runtime.get("versions") != _RUNTIME_VERSIONS:
        raise E0040FormalMappingError("E-0040 runtime version authority drifted")

    contract = control.get("mapping_contract")
    if contract != {
        "source_row_count": 64,
        "source_row_ids_sha256": SOURCE_ROW_IDS_SHA256,
        "base_schema_node_count": 77,
        "schema_report_norm_ids_sha256": SCHEMA_IDS_SHA256,
        "base_projection_sha256": BASE_PROJECTION_SHA256,
        "scrubbed_answer_free_evidence_sha256": SCRUBBED_EVIDENCE_SHA256,
        "scrubbed_answer_free_evidence_size_bytes": SCRUBBED_EVIDENCE_SIZE,
        "source_evidence_receipt_sha256": SOURCE_EVIDENCE_RECEIPT_SHA256,
        "s3_registry_line_sha256": S3_SNAPSHOT_LINE_SHA256,
        "s3_registry_line_size_bytes": S3_SNAPSHOT_LINE_SIZE,
        "result_projection_sha256": RESULT_PROJECTION_SHA256,
        "challenger_result_sha256": CHALLENGER_RESULT_SHA256,
        "challenger_result_size_bytes": CHALLENGER_RESULT_SIZE,
        "baseline_selected_count": 59,
        "baseline_selected_pairs_sha256": BASELINE_PAIRS_SHA256,
        "final_selected_count": 61,
        "final_selected_pairs_sha256": FINAL_PAIRS_SHA256,
        "final_selected_pairs_size_bytes": FINAL_PAIRS_SIZE,
        "internal_role_repair_selected_count": 2,
        "source_only_structural_count": 3,
        "selected_anchor_count": 43,
        "selected_path_count": 18,
        "baseline_interval_count": 43,
        "final_interval_count": 44,
        "final_status_counts": {
            "NO_ADMISSIBLE_PAIR": 3,
            "RESOLVED_ANCHOR": 43,
            "RESOLVED_PATH": 18,
        },
        "normalization_changed_schema_node_count": 21,
        "normalization_derived_key_count": 33,
        "base_collision_pair_count": 6,
        "result_collision_pair_count": 6,
        "new_collision_pair_count": 0,
        "mapper_invocation_count": 2,
        "minimum_counterfactual_margin": 0.15,
        "all_intervals_exhaustive": True,
        "all_pruning_counts_zero": True,
        "final_result_sha256": FINAL_RESULT_SHA256,
        "final_result_size_bytes": FINAL_RESULT_SIZE,
        "normalization_sha256": NORMALIZATION_SHA256,
        "collision_audit_sha256": COLLISION_AUDIT_SHA256,
        "id_scoped_alias_invocation_count": 0,
        "bank_page_or_row_rule_invocation_count": 0,
    }:
        raise E0040FormalMappingError("E-0040 mapping contract drifted")
    if control.get("validation_order") != _VALIDATION_ORDER:
        raise E0040FormalMappingError("E-0040 validation order drifted")
    if control.get("forbidden_inputs") != _FORBIDDEN_INPUTS:
        raise E0040FormalMappingError("E-0040 forbidden-input contract drifted")
    if control.get("publication") != _PUBLICATION:
        raise E0040FormalMappingError("E-0040 publication contract drifted")
    limitations = control.get("limitations")
    if limitations != [
        "CALIBRATION_ONLY_SINGLE_BANK_SINGLE_PERIOD_DOCUMENT",
        "MACHINE_MAPPING_HYPOTHESES_NOT_SCHEMA_OR_REVIEW_AUTHORITY",
        "NO_NUMERIC_PERIOD_UNIT_SCOPE_ACCOUNTING_OR_EXCEL_AUTHORITY",
        "NO_BANK_OR_PERIOD_DISJOINT_HUMAN_LABELED_VALIDATION",
        "GENERIC_NORMALIZATION_COLLISION_PROOF_IS_BOUNDED_TO_77_NODE_CDKT_PROJECTION",
        "COMBINED_PARENT_ROLE_REPAIR_IS_A_BOUNDED_MACHINE_HYPOTHESIS",
        "NOT_HOLDOUT_OR_PRODUCTION_APPROVED",
    ]:
        raise E0040FormalMappingError("E-0040 limitations drifted")
    if control.get("claim_boundaries") != {
        "mapping_only": _MAPPING_ONLY_CLAIM,
        "mapping_seal": _MAPPING_SEAL_CLAIM,
    }:
        raise E0040FormalMappingError("E-0040 claim boundaries drifted")
    _assert_answer_free_formal_paths(control)
    return control, stable


def _load_prerequisites(
    project_root: Path,
    config_path: Path,
    reader: StableReader,
) -> _Prerequisites:
    control, control_stable = _load_control(project_root, config_path, reader)
    implementation_records = cast(dict[str, Any], control["implementation"])
    implementation_stable = {
        name: _verify_record(
            reader,
            project_root,
            implementation_records[name],
            f"E-0040 implementation {name}",
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
            f"E-0040 policy {name}",
            expected_path=_INPUT_PATHS[name],
            maximum_size=_MAX_YAML_BYTES,
        )
        for name in ("e0040_policy", "e0040_mapper_policy")
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
            f"E-0040 runtime artifact {name}",
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
        raise E0040FormalMappingError("E-0040 runtime packages drifted")
    return _Prerequisites(
        control=control,
        control_stable=control_stable,
        implementation_stable=implementation_stable,
        policy_stable=policy_stable,
        runtime_stable=runtime_stable,
    )


def _validate_artifact_ledger(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not value or len(value) > 128:
        raise E0040FormalMappingError(f"{label} must be a bounded artifact ledger")
    for name, record in value.items():
        if type(name) is not str or not name:
            raise E0040FormalMappingError(f"{label} has an invalid name")
        _artifact_record(record, f"{label} {name}")
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
    seal_commit = seal.get("seal_git_commit")
    capture_commit = seal.get("mapping_capture_git_commit")
    if (
        seal.get("format_version") != 1
        or seal.get("experiment_id") != "E-0037"
        or seal.get("dataset_role") != "CALIBRATION"
        or seal.get("state") != "MAPPING_ONLY_HASH_SEALED_BEFORE_POSTJOIN"
        or seal.get("seal_git_dirty") is not False
        or type(seal_commit) is not str
        or _GIT_COMMIT.fullmatch(seal_commit) is None
        or capture_commit != seal_commit
        or seal.get("mapping_only") != expected_mapping
        or seal.get("schema_projection_sha256") != BASE_PROJECTION_SHA256
        or seal.get("row_count") != 64
        or seal.get("schema_disposition_count") != 77
        or seal.get("row_mapping_status_counts")
        != {"AMBIGUOUS_ACROSS_PATHS": 60, "NO_ADMISSIBLE_PAIR": 4}
    ):
        raise E0040FormalMappingError("E-0037 mapping seal identity drifted")
    if seal.get("postjoin_access") != {
        "mapping_only_validated_before_postjoin_access": True,
        "deterministic_mapping_replay_invocation_count": 1,
        "deterministic_mapping_replay_byte_equal": True,
        "e0030_opened": False,
        "e0033_opened": False,
        "e0034_opened": False,
        "mapper_replay_used_to_change_mapping": False,
    }:
        raise E0040FormalMappingError("E-0037 seal access proof drifted")
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
        raise E0040FormalMappingError("E-0037 seal authority drifted")
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
        raise E0040FormalMappingError("E-0037 seal mapping linkage drifted")
    _artifact_record(ledger.get("control"), "E-0037 seal control")
    replay_inputs = _validate_artifact_ledger(
        ledger.get("authentication_replay_inputs"),
        "E-0037 authentication input ledger",
    )
    replay_implementation = _validate_artifact_ledger(
        ledger.get("authentication_replay_implementation"),
        "E-0037 authentication implementation ledger",
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
        raise E0040FormalMappingError("E-0037 seal replay inventory drifted")


def _load_unique_s3_record(
    registry_bytes: bytes,
    expected: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        lines = registry_bytes.splitlines(keepends=True)
    except (AttributeError, MemoryError) as exc:
        raise E0040FormalMappingError("S3 registry line inventory is invalid") from exc
    if (
        not lines
        or len(lines) > _MAX_REGISTRY_LINES
        or any(not line.strip() or not line.endswith(b"\n") for line in lines)
    ):
        raise E0040FormalMappingError("S3 registry line inventory is invalid")
    matches: list[tuple[int, bytes, dict[str, Any]]] = []
    for index, raw_line in enumerate(lines, start=1):
        record = _decode_json_object(raw_line[:-1], f"S3 registry line {index}")
        if record.get("artifact_snapshot_id") == S3_SNAPSHOT_ID:
            matches.append((index, raw_line, record))
    if len(matches) != 1:
        raise E0040FormalMappingError("S3 registry snapshot is absent or duplicated")
    line_number, raw_line, record = matches[0]
    if record != dict(expected) or _canonical_sha256(record) != S3_SNAPSHOT_RECORD_SHA256:
        raise E0040FormalMappingError("S3 registry snapshot record drifted")
    if (
        len(raw_line) != S3_SNAPSHOT_LINE_SIZE
        or hashlib.sha256(raw_line).hexdigest() != S3_SNAPSHOT_LINE_SHA256
    ):
        raise E0040FormalMappingError("S3 registry snapshot line identity drifted")
    probe = record.get("hydrate_probe")
    logical_paths = probe.get("logical_paths") if isinstance(probe, dict) else None
    if (
        record.get("restore_verified") is not True
        or not isinstance(probe, dict)
        or probe.get("status") != "PASS"
        or probe.get("sealed_hashes_match") is not True
        or probe.get("restored_file_count") != record.get("file_count")
        or probe.get("reused_file_count_on_second_hydrate") != record.get("file_count")
        or not isinstance(logical_paths, list)
        or E0037_MAPPING_ONLY_RELATIVE_PATH.as_posix() not in logical_paths
    ):
        raise E0040FormalMappingError("S3 registry snapshot lacks passing restore proof")
    return record, {
        "registry_path": S3_REGISTRY_RELATIVE_PATH.as_posix(),
        "line_number": line_number,
        "line_sha256": S3_SNAPSHOT_LINE_SHA256,
        "line_size_bytes": S3_SNAPSHOT_LINE_SIZE,
        "canonical_record_sha256": S3_SNAPSHOT_RECORD_SHA256,
    }


def _validate_e0037_mapping_envelope(
    mapping: dict[str, Any],
    seal: Mapping[str, Any],
) -> None:
    _exact_keys(
        mapping,
        {
            "access_contract",
            "authority",
            "capture_git_commit",
            "capture_git_dirty",
            "claim_boundary",
            "dataset_role",
            "experiment_id",
            "format_version",
            "implementation_hash_ledger",
            "input_hash_ledger",
            "mapping",
            "metrics",
            "rows",
            "schema_dispositions",
            "schema_projection",
            "semantic_proposals",
            "source_structure",
            "state",
        },
        "E-0037 mapping-only payload",
    )
    if (
        mapping.get("format_version") != 1
        or mapping.get("experiment_id") != "E-0037"
        or mapping.get("dataset_role") != "CALIBRATION"
        or mapping.get("state") != "MAPPING_ONLY_SEALED_BEFORE_NUMERIC_PERIOD_REVIEW_ACCESS"
        or mapping.get("capture_git_dirty") is not False
        or mapping.get("capture_git_commit") != seal.get("mapping_capture_git_commit")
    ):
        raise E0040FormalMappingError("E-0037 mapping-only envelope drifted")
    if mapping.get("access_contract") != {
        "e0030_opened": False,
        "e0033_opened": False,
        "e0034_opened": False,
        "e0035_and_e0036_sealed_label_evidence_opened": True,
        "exact_cdkt_workbook_hierarchy_scope_policy_opened": True,
        "mapping_function_invocation_count": 1,
        "numeric_or_period_features_passed_to_mapper": False,
        "qwen_result_or_rejected_raw_output_opened": False,
        "review_or_history_opened": False,
        "source_structure_opened": True,
    }:
        raise E0040FormalMappingError("E-0037 mapping-only access contract drifted")
    semantic = mapping.get("semantic_proposals")
    if semantic != {
        "qwen_proposal_count": 0,
        "rejected_raw_output_proposal_count": 0,
        "valid_proposal_counts": {"deepseek_ocr2": 51, "vietocr": 64},
    }:
        raise E0040FormalMappingError("E-0037 semantic proposal authority drifted")
    projection = mapping.get("schema_projection")
    rows = mapping.get("rows")
    if (
        not isinstance(projection, dict)
        or projection.get("projection_sha256") != BASE_PROJECTION_SHA256
        or projection.get("alias_authority") != "CANONICAL_AND_STRUCTURAL_ALIASES_ONLY"
        or projection.get("statement_type") != "CDKT"
        or projection.get("node_count") != 77
        or not isinstance(projection.get("nodes"), list)
        or len(projection["nodes"]) != 77
        or not isinstance(rows, list)
        or len(rows) != 64
    ):
        raise E0040FormalMappingError("E-0037 source/projection cardinality drifted")
    seal_ledger = cast(Mapping[str, Any], seal["input_hash_ledger"])
    if (
        mapping.get("input_hash_ledger") != seal_ledger["authentication_replay_inputs"]
        or mapping.get("implementation_hash_ledger")
        != seal_ledger["authentication_replay_implementation"]
    ):
        raise E0040FormalMappingError("E-0037 mapping-only/seal ledger linkage drifted")


def _load_e0037_authority(
    project_root: Path,
    prerequisites: _Prerequisites,
    reader: StableReader,
) -> _E0037Authority:
    """Authenticate seal and restore proof before opening mapping-only bytes."""

    inputs = cast(dict[str, Any], prerequisites.control["input_authority"])
    seal_stable = _verify_record(
        reader,
        project_root,
        inputs["e0037_mapping_seal"],
        "E-0037 mapping seal",
        expected_path=E0037_MAPPING_SEAL_RELATIVE_PATH,
        maximum_size=_MAX_YAML_BYTES,
    )
    seal = _decode_json_object(seal_stable.payload, "E-0037 mapping seal")
    _validate_e0037_seal_before_mapping_open(seal, prerequisites.control)

    registry_stable = _verify_record(
        reader,
        project_root,
        inputs["s3_snapshot_registry"],
        "S3 artifact snapshot registry",
        expected_path=S3_REGISTRY_RELATIVE_PATH,
        maximum_size=4 * 1024 * 1024,
    )
    s3_record, s3_line_artifact = _load_unique_s3_record(
        registry_stable.payload,
        cast(dict[str, Any], inputs["s3_snapshot"]),
    )

    mapping_stable = _verify_record(
        reader,
        project_root,
        inputs["e0037_mapping_only"],
        "E-0037 mapping-only bytes",
        expected_path=E0037_MAPPING_ONLY_RELATIVE_PATH,
        maximum_size=4 * 1024 * 1024,
    )
    mapping = _decode_json_object(mapping_stable.payload, "E-0037 mapping-only bytes")
    _validate_e0037_mapping_envelope(mapping, seal)
    return _E0037Authority(
        seal_stable=seal_stable,
        seal=seal,
        registry_stable=registry_stable,
        s3_record=s3_record,
        s3_line_artifact=s3_line_artifact,
        mapping_stable=mapping_stable,
        mapping=mapping,
    )


def _scrub_answer_free_payload(mapping: Mapping[str, Any]) -> dict[str, Any]:
    """Copy only fields admitted by the E-0040 core adapter."""

    raw_rows = mapping.get("rows")
    raw_projection = mapping.get("schema_projection")
    if not isinstance(raw_rows, list) or not isinstance(raw_projection, dict):
        raise E0040FormalMappingError("E-0037 answer-free evidence is absent")
    scrubbed_rows: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_rows):
        if not isinstance(raw, dict):
            raise E0040FormalMappingError(f"E-0037 source row {index} is invalid")
        structure = raw.get("source_structure")
        labels = raw.get("semantic_proposals")
        if not isinstance(structure, dict) or not isinstance(labels, dict):
            raise E0040FormalMappingError(f"E-0037 source row {index} is incomplete")
        if any(type(key) is not str or type(value) is not str for key, value in labels.items()):
            raise E0040FormalMappingError(f"E-0037 source labels {index} are invalid")
        if any("qwen" in key.casefold() for key in labels):
            raise E0040FormalMappingError("E-0037 source labels contain forbidden reader output")
        scrubbed_rows.append(
            {
                "row_id": raw.get("row_id"),
                "source_order": raw.get("source_order"),
                "semantic_proposals": dict(sorted(labels.items())),
                "source_structure": {
                    "child_set_complete": structure.get("child_set_complete"),
                    "mapper_relation_type": structure.get("mapper_relation_type"),
                    "physical_parent_row_id": structure.get("physical_parent_row_id"),
                    "report_scope": "UNKNOWN",
                    "row_role": structure.get("row_role"),
                    "target_template_in_scope": True,
                },
            }
        )
    raw_nodes = raw_projection.get("nodes")
    if not isinstance(raw_nodes, list):
        raise E0040FormalMappingError("E-0037 base projection nodes are absent")
    nodes: list[dict[str, Any]] = []
    admitted_node_keys = (
        "report_norm_id",
        "display_name",
        "structural_aliases",
        "display_order",
        "parent_report_norm_id",
        "child_report_norm_ids",
        "hierarchy_level",
        "section_path",
        "scopes",
    )
    for index, node in enumerate(raw_nodes):
        if not isinstance(node, dict):
            raise E0040FormalMappingError(f"E-0037 base projection node {index} is invalid")
        nodes.append({key: node.get(key) for key in admitted_node_keys})
    scrubbed = {
        "rows": scrubbed_rows,
        "schema_projection": {
            "alias_authority": raw_projection.get("alias_authority"),
            "nodes": nodes,
            "projection_sha256": raw_projection.get("projection_sha256"),
            "statement_type": raw_projection.get("statement_type"),
        },
    }
    _assert_finite_tree(scrubbed, "scrubbed E-0037 evidence")
    return scrubbed


def _validate_challenger_result(
    result: E0040ChallengerResult,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if type(result) is not E0040ChallengerResult:
        raise E0040FormalMappingError("E-0040 challenger returned an invalid type")
    payload = result.to_dict()
    _assert_finite_tree(payload, "E-0040 challenger result")
    compact = _canonical_compact_bytes(payload)
    if (
        len(compact) != CHALLENGER_RESULT_SIZE
        or hashlib.sha256(compact).hexdigest() != CHALLENGER_RESULT_SHA256
    ):
        raise E0040FormalMappingError("E-0040 challenger result identity drifted")
    if (
        result.policy_sha256 != E0040_POLICY_SHA256
        or result.mapper_policy_sha256 != MAPPER_POLICY_SHA256
        or result.mapper_invocation_count != 2
        or len(result.baseline_selected_pairs) != 59
        or len(result.final_selected_pairs) != 61
        or len(result.newly_selected_pairs) != 2
        or len(result.combined_parent_overrides) != 2
        or len(result.source_only_structural_rows) != 3
    ):
        raise E0040FormalMappingError("E-0040 challenger cardinality/identity drifted")
    if (
        len(set(result.baseline_selected_pairs)) != 59
        or len(set(result.final_selected_pairs)) != 61
        or len({row_id for row_id, _ in result.final_selected_pairs}) != 61
        or len({report_norm_id for _, report_norm_id in result.final_selected_pairs}) != 61
        or not set(result.baseline_selected_pairs).issubset(result.final_selected_pairs)
        or not set(result.newly_selected_pairs).issubset(result.final_selected_pairs)
        or set(result.newly_selected_pairs) & set(result.baseline_selected_pairs)
    ):
        raise E0040FormalMappingError("E-0040 selected-pair uniqueness/linkage drifted")
    baseline_sha = _canonical_sha256(result.baseline_selected_pairs)
    final_pairs_bytes = _canonical_compact_bytes(result.final_selected_pairs)
    if (
        baseline_sha != BASELINE_PAIRS_SHA256
        or len(final_pairs_bytes) != FINAL_PAIRS_SIZE
        or hashlib.sha256(final_pairs_bytes).hexdigest() != FINAL_PAIRS_SHA256
    ):
        raise E0040FormalMappingError("E-0040 selected-pair digest drifted")

    normalization = result.normalization
    collision = result.collision_audit
    if (
        normalization.statement_type != "CDKT"
        or normalization.bank_scope != "ALL_BANKS"
        or normalization.base_projection_sha256 != BASE_PROJECTION_SHA256
        or normalization.result_projection_sha256 != RESULT_PROJECTION_SHA256
        or normalization.changed_schema_node_count != 21
        or normalization.derived_key_count != 33
        or normalization.id_scoped_alias_invocation_count != 0
        or normalization.bank_page_or_row_rule_invocation_count != 0
        or normalization.input_alias_authority != "CANONICAL_AND_STRUCTURAL_ALIASES_ONLY"
        or normalization.mapper_carrier_alias_authority != "CANONICAL_AND_STRUCTURAL_ALIASES_ONLY"
        or _canonical_sha256(payload["normalization"]) != NORMALIZATION_SHA256
    ):
        raise E0040FormalMappingError("E-0040 normalization receipt drifted")
    if (
        collision.statement_type != "CDKT"
        or collision.node_count != 77
        or len(collision.base_collision_pairs) != 6
        or len(collision.result_collision_pairs) != 6
        or collision.result_collision_pairs != collision.base_collision_pairs
        or collision.new_collision_pairs
        or _canonical_sha256(payload["collision_audit"]) != COLLISION_AUDIT_SHA256
    ):
        raise E0040FormalMappingError("E-0040 collision receipt drifted")
    if Counter(item.observed_role for item in result.source_only_structural_rows) != {
        "SECTION": 2,
        "TOTAL": 1,
    } or any(
        item.selected_report_norm_id is not None
        or item.final_mapping_status != "NO_ADMISSIBLE_PAIR"
        or item.disposition != "SOURCE_ONLY_STRUCTURAL_ROW_HYPOTHESIS_UNMATCHED"
        for item in result.source_only_structural_rows
    ):
        raise E0040FormalMappingError("E-0040 source-only disposition drifted")
    if tuple(
        (item.row_id, item.target_report_norm_id) for item in result.combined_parent_overrides
    ) != result.newly_selected_pairs or any(
        item.observed_role != "DETAIL"
        or item.effective_role != "GROUP"
        or len(item.supporting_reader_ids) < 2
        or len(set(item.supporting_reader_ids)) != len(item.supporting_reader_ids)
        for item in result.combined_parent_overrides
    ):
        raise E0040FormalMappingError("E-0040 combined-parent proof drifted")

    for run_name, run, expected_interval_count in (
        ("baseline", result.baseline_result, 43),
        ("final", result.final_result, 44),
    ):
        if (
            run.schema_projection_sha256 != RESULT_PROJECTION_SHA256
            or run.schema_alias_authority != "CANONICAL_AND_STRUCTURAL_ALIASES_ONLY"
            or run.policy_sha256 != MAPPER_POLICY_SHA256
            or len(run.row_mappings) != 64
            or len(run.intervals) != expected_interval_count
            or not all(interval.search_exhaustive for interval in run.intervals)
            or any(
                interval.main_search_pruned_states != 0
                or interval.counterfactual_search_pruned_states != 0
                for interval in run.intervals
            )
            or run.search.pruned_states != 0
            or run.search.main_search_pruned_states != 0
            or run.search.counterfactual_search_pruned_states != 0
        ):
            raise E0040FormalMappingError(f"E-0040 {run_name} exhaustive-search proof drifted")

    final = result.final_result
    status_counts = dict(sorted(Counter(item.status for item in final.row_mappings).items()))
    if status_counts != {
        "NO_ADMISSIBLE_PAIR": 3,
        "RESOLVED_ANCHOR": 43,
        "RESOLVED_PATH": 18,
    }:
        raise E0040FormalMappingError("E-0040 final row status counts drifted")
    selected_anchors = tuple(
        anchor for anchor in final.anchors if anchor.selected_report_norm_id is not None
    )
    selected_path_matches = tuple(
        match for interval in final.intervals for match in interval.best_path.matches
    )
    path_counterfactuals = tuple(
        item for interval in final.intervals for item in interval.counterfactuals
    )
    if (
        len(selected_anchors) != 43
        or len(selected_path_matches) != 18
        or len(path_counterfactuals) != 18
        or any(
            not anchor.selection_allowed
            or anchor.counterfactual_margin is None
            or anchor.counterfactual_margin < 0.15
            for anchor in selected_anchors
        )
        or any(not item.stable or item.exclusion_margin < 0.15 for item in path_counterfactuals)
    ):
        raise E0040FormalMappingError("E-0040 anchor/path counterfactual proof drifted")
    final_result_bytes = _canonical_compact_bytes(payload["final_result"])
    if (
        len(final_result_bytes) != FINAL_RESULT_SIZE
        or hashlib.sha256(final_result_bytes).hexdigest() != FINAL_RESULT_SHA256
    ):
        raise E0040FormalMappingError("E-0040 final mapper result digest drifted")

    receipts = {
        "challenger_result_sha256": CHALLENGER_RESULT_SHA256,
        "challenger_result_size_bytes": CHALLENGER_RESULT_SIZE,
        "baseline_selected_pairs_sha256": baseline_sha,
        "final_selected_pairs_sha256": FINAL_PAIRS_SHA256,
        "final_selected_pairs_size_bytes": FINAL_PAIRS_SIZE,
        "final_result_sha256": FINAL_RESULT_SHA256,
        "final_result_size_bytes": FINAL_RESULT_SIZE,
        "normalization_sha256": NORMALIZATION_SHA256,
        "collision_audit_sha256": COLLISION_AUDIT_SHA256,
    }
    metrics = {
        "source_row_count": 64,
        "schema_node_count": 77,
        "baseline_selected_count": 59,
        "final_selected_count": 61,
        "internal_role_repair_selected_count": 2,
        "source_only_structural_count": 3,
        "selected_anchor_count": 43,
        "selected_path_count": 18,
        "baseline_interval_count": 43,
        "final_interval_count": 44,
        "final_row_status_counts": status_counts,
        "base_collision_pair_count": 6,
        "result_collision_pair_count": 6,
        "new_collision_pair_count": 0,
        "normalization_changed_schema_node_count": 21,
        "normalization_derived_key_count": 33,
        "mapper_invocation_count": 2,
        "all_intervals_exhaustive": True,
        "all_pruning_counts_zero": True,
    }
    return receipts, metrics


def _source_evidence_receipt(scrubbed: Mapping[str, Any]) -> dict[str, Any]:
    rows = cast(list[dict[str, Any]], scrubbed["rows"])
    projection = cast(dict[str, Any], scrubbed["schema_projection"])
    row_ids = [row["row_id"] for row in rows]
    schema_ids = [node["report_norm_id"] for node in projection["nodes"]]
    scrubbed_bytes = _canonical_compact_bytes(scrubbed)
    if (
        len(row_ids) != 64
        or len(set(row_ids)) != 64
        or _canonical_sha256(row_ids) != SOURCE_ROW_IDS_SHA256
        or len(schema_ids) != 77
        or len(set(schema_ids)) != 77
        or _canonical_sha256(schema_ids) != SCHEMA_IDS_SHA256
        or len(scrubbed_bytes) != SCRUBBED_EVIDENCE_SIZE
        or hashlib.sha256(scrubbed_bytes).hexdigest() != SCRUBBED_EVIDENCE_SHA256
    ):
        raise E0040FormalMappingError("E-0040 source/schema identity list drifted")
    receipt = {
        "source_row_count": 64,
        "source_row_ids_sha256": SOURCE_ROW_IDS_SHA256,
        "schema_node_count": 77,
        "schema_report_norm_ids_sha256": SCHEMA_IDS_SHA256,
        "scrubbed_answer_free_evidence_sha256": SCRUBBED_EVIDENCE_SHA256,
        "scrubbed_answer_free_evidence_size_bytes": SCRUBBED_EVIDENCE_SIZE,
        "base_projection_sha256": BASE_PROJECTION_SHA256,
        "admitted_fields": {
            "source": [
                "row_id",
                "source_order",
                "semantic_proposals",
                "child_set_complete",
                "mapper_relation_type",
                "physical_parent_row_id",
                "row_role",
            ],
            "schema": [
                "report_norm_id",
                "display_name",
                "structural_aliases",
                "display_order",
                "parent_report_norm_id",
                "child_report_norm_ids",
                "hierarchy_level",
                "section_path",
                "scopes",
                "statement_type",
                "projection_sha256",
                "alias_authority",
            ],
            "synthesized_neutral_source_fields": {
                "report_scope": "UNKNOWN",
                "target_template_in_scope": True,
            },
        },
        "prior_mapping_page_and_row_ordinal_fields_passed_to_core": False,
        "source_scope_fields_read": False,
        "source_scope_features_passed_to_core": False,
        "numeric_period_or_unit_answer_fields_passed_to_core": False,
    }
    if _canonical_sha256(receipt) != SOURCE_EVIDENCE_RECEIPT_SHA256:
        raise E0040FormalMappingError("E-0040 source evidence receipt identity drifted")
    return receipt


def _recheck_all_inputs(
    project_root: Path,
    prerequisites: _Prerequisites,
    authority: _E0037Authority,
    reader: StableReader,
) -> None:
    for label, stable in (
        ("E-0040 control", prerequisites.control_stable),
        *(
            (f"E-0040 implementation {name}", item)
            for name, item in prerequisites.implementation_stable.items()
        ),
        *((f"E-0040 policy {name}", item) for name, item in prerequisites.policy_stable.items()),
        *((f"E-0040 runtime {name}", item) for name, item in prerequisites.runtime_stable.items()),
        ("E-0037 mapping seal", authority.seal_stable),
        ("S3 snapshot registry", authority.registry_stable),
        ("E-0037 mapping-only", authority.mapping_stable),
    ):
        _assert_unchanged(reader, project_root, stable, label)


def build_e0040_mapping_only(
    project_root: Path,
    *,
    capture_git_commit: str,
    config_path: Path = CONTROL_RELATIVE_PATH,
    _reader: StableReader | None = None,
) -> dict[str, Any]:
    """Build and validate the formal mapping payload without publication."""

    _assert_answer_free_process()
    if type(capture_git_commit) is not str or _GIT_COMMIT.fullmatch(capture_git_commit) is None:
        raise E0040FormalMappingError("E-0040 capture Git commit is invalid")
    root = project_root.resolve()
    reader = _read_stable_file if _reader is None else _reader
    prerequisites = _load_prerequisites(root, config_path, reader)
    authority = _load_e0037_authority(root, prerequisites, reader)
    mapping_before = _canonical_sha256(authority.mapping)
    scrubbed = _scrub_answer_free_payload(authority.mapping)
    source_receipt = _source_evidence_receipt(scrubbed)
    try:
        policy_stable = prerequisites.policy_stable["e0040_policy"]
        mapper_policy_stable = prerequisites.policy_stable["e0040_mapper_policy"]
        policy = load_e0040_policy_bytes(
            policy_stable.payload,
            source_path=Path(cast(str, policy_stable.artifact["path"])),
        )
        mapper_policy = load_ordered_subgraph_v2_policy_bytes(
            mapper_policy_stable.payload,
            source_path=Path(cast(str, mapper_policy_stable.artifact["path"])),
        )
        rows = source_rows_from_sealed_mapping_payload(scrubbed)
        projection = projection_from_sealed_mapping_payload(scrubbed)
        result = align_e0040_calibration_challenger(
            rows,
            projection,
            policy=policy,
            mapper_policy=mapper_policy,
        )
    except (E0040ChallengerError, TypeError, ValueError) as exc:
        raise E0040FormalMappingError("E-0040 challenger execution failed closed") from exc
    result_receipts, metrics = _validate_challenger_result(result)
    if _canonical_sha256(authority.mapping) != mapping_before:
        raise E0040FormalMappingError("E-0037 mapping input mutated during E-0040 execution")

    payload: dict[str, Any] = {
        "format_version": 1,
        "experiment_id": "E-0040",
        "dataset_role": "CALIBRATION",
        "state": MAPPING_ONLY_STATE,
        "capture_git_commit": capture_git_commit,
        "capture_git_dirty": False,
        "input_hash_ledger": {
            "control": prerequisites.control_stable.artifact,
            "e0037_mapping_seal": authority.seal_stable.artifact,
            "s3_snapshot_registry": authority.registry_stable.artifact,
            "e0037_mapping_only": authority.mapping_stable.artifact,
            "e0040_policy": prerequisites.policy_stable["e0040_policy"].artifact,
            "e0040_mapper_policy": prerequisites.policy_stable["e0040_mapper_policy"].artifact,
        },
        "implementation_hash_ledger": {
            name: stable.artifact for name, stable in prerequisites.implementation_stable.items()
        },
        "runtime_hash_ledger": {
            name: stable.artifact for name, stable in prerequisites.runtime_stable.items()
        },
        "runtime_versions": dict(_RUNTIME_VERSIONS),
        "e0037_authority_receipt": {
            "mapping_only_sha256": E0037_MAPPING_ONLY_SHA256,
            "mapping_seal_sha256": E0037_MAPPING_SEAL_SHA256,
            "mapping_capture_git_commit": authority.seal["mapping_capture_git_commit"],
            "s3_snapshot_id": S3_SNAPSHOT_ID,
            "s3_snapshot_record_sha256": S3_SNAPSHOT_RECORD_SHA256,
            "s3_registry_line": authority.s3_line_artifact,
            "manifest_sha256": authority.s3_record["manifest"]["sha256"],
            "run_record_sha256": authority.s3_record["run_record"]["sha256"],
            "restore_verified": True,
        },
        "source_evidence_receipt": source_receipt,
        "result_receipts": result_receipts,
        "metrics": metrics,
        "challenger_result": result.to_dict(),
        "access_contract": {
            "validation_order": list(_VALIDATION_ORDER),
            "e0037_seal_validated_before_mapping_open": True,
            "unique_s3_restore_record_validated_before_mapping_open": True,
            "e0037_mapping_semantic_decode_count": 1,
            "e0037_mapping_stable_identity_read_count_per_build": 2,
            "e0037_source_structure_file_opened": False,
            "e0038_or_e0039_mapping_artifact_opened": False,
            "review_or_steward_answers_opened": False,
            "numeric_status_or_postjoin_artifact_opened": False,
            "period_unit_or_source_scope_answer_artifact_opened": False,
            "raw_source_report_scope_extracted_or_used": False,
            "schema_node_applicability_scopes_present": True,
            "history_or_mongodb_opened": False,
            "holdout_opened": False,
            "qwen_raw_rejected_or_token_output_opened": False,
            "prior_mapping_page_and_row_ordinal_fields_passed_to_core": False,
            "process_contamination_guard_passed": True,
            "stable_inputs_revalidated_after_mapping": True,
        },
        "limitations": list(prerequisites.control["limitations"]),
        "authority": {
            "mapping_output_hash_identity": True,
            "generic_normalization_and_role_repair_diagnostics": True,
            "schema_authority": False,
            "mapping_accuracy": False,
            "review_or_steward_approval": False,
            "numeric_period_unit_scope": False,
            "accounting_or_excel": False,
            "holdout_or_production": False,
        },
        "claim_boundary": _MAPPING_ONLY_CLAIM,
    }
    _assert_finite_tree(payload, "E-0040 formal mapping payload")
    _validate_mapping_before_replay(
        payload,
        prerequisites,
        expected_git_commit=capture_git_commit,
        encoded_bytes=_encoded_json(payload),
    )
    _recheck_all_inputs(root, prerequisites, authority, reader)
    _assert_answer_free_process()
    if _canonical_sha256(authority.mapping) != mapping_before:
        raise E0040FormalMappingError("E-0037 mapping input changed after E-0040 execution")
    return payload


def _sanitized_git_environment() -> dict[str, str]:
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment["GIT_CONFIG_NOSYSTEM"] = "1"
    environment["GIT_CONFIG_GLOBAL"] = os.devnull
    return environment


def _git_bytes(project_root: Path, *arguments: str) -> bytes:
    try:
        return subprocess.run(
            [
                "git",
                "-c",
                "core.fsmonitor=false",
                "-c",
                "core.untrackedCache=false",
                "-c",
                f"core.hooksPath={os.devnull}",
                "-C",
                str(project_root),
                *arguments,
            ],
            cwd=project_root,
            check=True,
            capture_output=True,
            env=_sanitized_git_environment(),
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise E0040FormalMappingError("cannot query Git for E-0040 formal capture") from exc


def _git(project_root: Path, *arguments: str) -> str:
    try:
        return _git_bytes(project_root, *arguments).decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise E0040FormalMappingError("Git returned non-UTF-8 metadata") from exc


def _assert_git_root(project_root: Path) -> None:
    top_level = _git(project_root, "rev-parse", "--show-toplevel")
    if Path(top_level).resolve() != project_root.resolve():
        raise E0040FormalMappingError("Git top-level differs from E-0040 project root")


def _git_commit(project_root: Path) -> str:
    _assert_git_root(project_root)
    commit = _git(project_root, "rev-parse", "--verify", "HEAD^{commit}")
    if _GIT_COMMIT.fullmatch(commit) is None:
        raise E0040FormalMappingError("cannot resolve E-0040 Git commit")
    return commit


def _clean_git_commit(project_root: Path) -> str:
    commit = _git_commit(project_root)
    index_records = [
        record for record in _git_bytes(project_root, "ls-files", "-v", "-z").split(b"\0") if record
    ]
    if not index_records or any(not record.startswith(b"H ") for record in index_records):
        raise E0040FormalMappingError(
            "E-0040 capture rejects non-normal Git index flags anywhere in the tree"
        )
    if _git_bytes(
        project_root,
        "status",
        "--porcelain=v2",
        "-z",
        "--untracked-files=all",
        "--ignore-submodules=none",
    ):
        raise E0040FormalMappingError("E-0040 capture requires a clean Git worktree")
    if _git_commit(project_root) != commit:
        raise E0040FormalMappingError("Git HEAD changed during clean-tree validation")
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
        f"E-0040 HEAD-bound {name}",
        expected_path=expected_path,
        maximum_size=8 * 1024 * 1024,
    )
    _assert_git_root(project_root)
    blob = _git_bytes(project_root, "cat-file", "blob", f"HEAD:{expected_path.as_posix()}")
    if blob != stable.payload or hashlib.sha256(blob).hexdigest() != stable.artifact["sha256"]:
        raise E0040FormalMappingError(f"{name} worktree bytes differ from the HEAD blob")


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
        path = input_paths[name]
        tracked_paths.append(path)
        _assert_tracked_record_matches_head(
            project_root,
            record,
            name=f"input {name}",
            expected_path=path,
            reader=reader,
        )
    implementations = cast(dict[str, Any], payload["implementation_hash_ledger"])
    for name, record in implementations.items():
        path = _IMPLEMENTATION_PATHS[name]
        tracked_paths.append(path)
        _assert_tracked_record_matches_head(
            project_root,
            record,
            name=f"implementation {name}",
            expected_path=path,
            reader=reader,
        )
    runtime = cast(dict[str, Any], payload["runtime_hash_ledger"])
    for name, record in runtime.items():
        path = _RUNTIME_PATHS[name]
        tracked_paths.append(path)
        _assert_tracked_record_matches_head(
            project_root,
            record,
            name=f"runtime {name}",
            expected_path=path,
            reader=reader,
        )
    expected_records = {b"H " + path.as_posix().encode("utf-8") for path in tracked_paths}
    raw = _git_bytes(
        project_root,
        "ls-files",
        "-v",
        "-z",
        "--",
        *(path.as_posix() for path in tracked_paths),
    )
    actual_records = {record for record in raw.split(b"\0") if record}
    if actual_records != expected_records:
        raise E0040FormalMappingError(
            "E-0040 tracked ledgers are absent or use non-normal index flags"
        )


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
            f"E-0040 immediate input recheck {name}",
            expected_path=input_paths[name],
            maximum_size=8 * 1024 * 1024,
        )
    for name, record in cast(dict[str, Any], payload["implementation_hash_ledger"]).items():
        _verify_record(
            reader,
            project_root,
            record,
            f"E-0040 immediate implementation recheck {name}",
            expected_path=_IMPLEMENTATION_PATHS[name],
            maximum_size=8 * 1024 * 1024,
        )
    for name, record in cast(dict[str, Any], payload["runtime_hash_ledger"]).items():
        _verify_record(
            reader,
            project_root,
            record,
            f"E-0040 immediate runtime recheck {name}",
            expected_path=_RUNTIME_PATHS[name],
            maximum_size=8 * 1024 * 1024,
        )


def _same_inode(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        stat.S_ISREG(left.st_mode)
        and stat.S_ISREG(right.st_mode)
        and left.st_dev == right.st_dev
        and left.st_ino == right.st_ino
        and left.st_size == right.st_size
    )


def _same_regular_file_identity(left: os.stat_result, right: os.stat_result) -> bool:
    """Compare unlink authority without treating mutable size as inode identity."""

    return (
        stat.S_ISREG(left.st_mode)
        and stat.S_ISREG(right.st_mode)
        and left.st_dev == right.st_dev
        and left.st_ino == right.st_ino
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
    if not _same_regular_file_identity(current, published_identity):
        raise E0040FormalMappingError(
            "cannot safely roll back E-0040 publication after identity replacement"
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
    """Link exclusively, then rebind parent, inode, bytes, and inventory."""

    if not path.is_relative_to(project_root):
        raise E0040FormalMappingError("E-0040 output path escapes project root")
    relative = path.relative_to(project_root)
    parent, final_name = _open_or_create_parent_directory(project_root, relative, "E-0040 output")
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
            raise E0040FormalMappingError("cannot create temporary E-0040 artifact") from exc
        try:
            view = memoryview(encoded)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise E0040FormalMappingError("short write for temporary E-0040 artifact")
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.chmod(temporary_name, 0o644, dir_fd=parent, follow_symlinks=False)
        temporary_identity = os.stat(temporary_name, dir_fd=parent, follow_symlinks=False)
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
                raise E0040FormalMappingError(
                    f"refusing to overwrite E-0040 artifact: {path}"
                ) from exc
            raise E0040FormalMappingError("cannot link E-0040 artifact") from exc
        published_identity = os.stat(final_name, dir_fd=parent, follow_symlinks=False)
        if not _same_inode(temporary_identity, published_identity):
            raise E0040FormalMappingError("E-0040 linked artifact identity mismatch")
        os.unlink(temporary_name, dir_fd=parent)
        temporary_created = False
        os.fsync(parent)

        fresh_parent, fresh_name = _open_existing_parent_directory(
            project_root,
            relative,
            "E-0040 published artifact",
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
            raise E0040FormalMappingError(
                "E-0040 published parent/file detached from canonical path"
            )
        canonical = _read_stable_file(
            project_root,
            path,
            "E-0040 published artifact",
            expected_size=len(encoded),
            maximum_size=max(len(encoded), 1),
        )
        if canonical.payload != encoded or canonical.artifact["sha256"] != digest:
            raise E0040FormalMappingError("E-0040 published bytes failed canonical revalidation")
        final_parent, _ = _open_existing_parent_directory(
            project_root,
            relative,
            "E-0040 final publication inventory",
        )
        try:
            final_parent_identity = os.fstat(final_parent)
            final_inventory = tuple(sorted(os.listdir(final_parent)))
            final_file_identity = os.stat(
                final_name,
                dir_fd=final_parent,
                follow_symlinks=False,
            )
        finally:
            os.close(final_parent)
        if (
            (final_parent_identity.st_dev, final_parent_identity.st_ino)
            != (
                held_parent.st_dev,
                held_parent.st_ino,
            )
            or (
                exclusive_parent_inventory is not None
                and final_inventory != tuple(sorted(exclusive_parent_inventory))
            )
            or not _same_inode(published_identity, final_file_identity)
        ):
            raise E0040FormalMappingError("E-0040 final canonical inventory drifted")
        final_canonical = _read_stable_file(
            project_root,
            path,
            "E-0040 final published artifact",
            expected_size=len(encoded),
            maximum_size=max(len(encoded), 1),
        )
        if (
            final_canonical.payload != encoded
            or final_canonical.artifact["sha256"] != digest
            or final_canonical.identity[0] != published_identity.st_dev
            or final_canonical.identity[1] != published_identity.st_ino
            or final_canonical.identity[3] != published_identity.st_size
        ):
            raise E0040FormalMappingError("E-0040 final published bytes/identity drifted")
    except Exception as exc:
        if published_identity is not None:
            _rollback_published_link(parent, final_name, published_identity)
        if isinstance(exc, E0040FormalMappingError):
            raise
        raise E0040FormalMappingError("E-0040 publication revalidation failed") from exc
    finally:
        if temporary_created:
            try:
                os.unlink(temporary_name, dir_fd=parent)
                os.fsync(parent)
            except FileNotFoundError:
                pass
        os.close(parent)
    return digest


def _mapping_output_inventory(project_root: Path, *, require_mapping: bool) -> tuple[str, ...]:
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
        raise E0040FormalMappingError("cannot open project root for mapping inventory") from exc
    try:
        for part in relative_directory.parts:
            try:
                following = os.open(part, flags, dir_fd=current)
            except OSError as exc:
                if exc.errno == errno.ENOENT and not require_mapping:
                    return ()
                raise E0040FormalMappingError(
                    "cannot traverse canonical E-0040 mapping inventory"
                ) from exc
            os.close(current)
            current = following
        inventory = tuple(sorted(os.listdir(current)))
        expected = (MAPPING_ONLY_RELATIVE_PATH.name,) if require_mapping else ()
        if inventory != expected:
            raise E0040FormalMappingError(
                "E-0040 mapping directory does not have the exact required inventory"
            )
        if require_mapping:
            item = os.stat(MAPPING_ONLY_RELATIVE_PATH.name, dir_fd=current, follow_symlinks=False)
            if not stat.S_ISREG(item.st_mode):
                raise E0040FormalMappingError("E-0040 mapping inventory item is not regular")
        return inventory
    finally:
        os.close(current)


def dry_run_e0040_mapping_only(
    project_root: Path,
    *,
    config_path: Path = CONTROL_RELATIVE_PATH,
) -> dict[str, Any]:
    """Execute the complete mapping logic in memory without publishing."""

    root = project_root.resolve()
    return build_e0040_mapping_only(
        root,
        capture_git_commit=_git_commit(root),
        config_path=config_path,
    )


def capture_e0040_mapping_only(
    project_root: Path,
    *,
    config_path: Path = CONTROL_RELATIVE_PATH,
    output_path: Path = MAPPING_ONLY_RELATIVE_PATH,
) -> dict[str, Any]:
    """Exclusively publish mapping-only bytes from a clean mechanism commit."""

    _assert_answer_free_process()
    root = project_root.resolve()
    _mapping_output_inventory(root, require_mapping=False)
    commit = _clean_git_commit(root)
    output = _canonical_input_path(root, output_path, MAPPING_ONLY_RELATIVE_PATH, "mapping output")
    payload = build_e0040_mapping_only(
        root,
        capture_git_commit=commit,
        config_path=config_path,
    )
    _recheck_payload_ledgers(root, payload, _read_stable_file)
    _assert_payload_ledgers_match_head(root, payload)
    _assert_answer_free_process()
    if _clean_git_commit(root) != commit:
        raise E0040FormalMappingError("Git commit changed during E-0040 mapping capture")
    _assert_answer_free_process()
    _assert_payload_ledgers_match_head(root, payload)
    _recheck_payload_ledgers(root, payload, _read_stable_file)
    _exclusive_publish_json(
        root,
        output,
        payload,
        exclusive_parent_inventory=(MAPPING_ONLY_RELATIVE_PATH.name,),
    )
    return payload


def _validate_mapping_before_replay(
    payload: Mapping[str, Any],
    prerequisites: _Prerequisites,
    *,
    expected_git_commit: str,
    encoded_bytes: bytes,
) -> None:
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
            "e0037_authority_receipt",
            "source_evidence_receipt",
            "result_receipts",
            "metrics",
            "challenger_result",
            "access_contract",
            "limitations",
            "authority",
            "claim_boundary",
        },
        "E-0040 mapping-only payload",
    )
    if (
        payload.get("format_version") != 1
        or payload.get("experiment_id") != "E-0040"
        or payload.get("dataset_role") != "CALIBRATION"
        or payload.get("state") != MAPPING_ONLY_STATE
        or payload.get("capture_git_commit") != expected_git_commit
        or payload.get("capture_git_dirty") is not False
        or payload.get("claim_boundary") != _MAPPING_ONLY_CLAIM
        or _encoded_json(payload) != encoded_bytes
    ):
        raise E0040FormalMappingError("E-0040 mapping-only envelope drifted before replay")
    inputs = _exact_keys(
        payload.get("input_hash_ledger"),
        {"control", *_INPUT_PATHS},
        "E-0040 mapping-only input ledger",
    )
    expected_inputs = cast(dict[str, Any], prerequisites.control["input_authority"])
    if inputs.get("control") != prerequisites.control_stable.artifact or any(
        inputs[name] != expected_inputs[name] for name in _INPUT_PATHS
    ):
        raise E0040FormalMappingError("E-0040 mapping-only input linkage drifted")
    if (
        payload.get("implementation_hash_ledger") != prerequisites.control.get("implementation")
        or payload.get("runtime_hash_ledger")
        != cast(dict[str, Any], prerequisites.control["runtime_authority"])["artifacts"]
    ):
        raise E0040FormalMappingError("E-0040 mapping-only implementation/runtime drifted")
    if payload.get("runtime_versions") != _RUNTIME_VERSIONS:
        raise E0040FormalMappingError("E-0040 mapping-only runtime versions drifted")
    receipts = payload.get("result_receipts")
    if receipts != {
        "challenger_result_sha256": CHALLENGER_RESULT_SHA256,
        "challenger_result_size_bytes": CHALLENGER_RESULT_SIZE,
        "baseline_selected_pairs_sha256": BASELINE_PAIRS_SHA256,
        "final_selected_pairs_sha256": FINAL_PAIRS_SHA256,
        "final_selected_pairs_size_bytes": FINAL_PAIRS_SIZE,
        "final_result_sha256": FINAL_RESULT_SHA256,
        "final_result_size_bytes": FINAL_RESULT_SIZE,
        "normalization_sha256": NORMALIZATION_SHA256,
        "collision_audit_sha256": COLLISION_AUDIT_SHA256,
    }:
        raise E0040FormalMappingError("E-0040 mapping-only result receipts drifted")
    challenger = payload.get("challenger_result")
    if (
        not isinstance(challenger, dict)
        or len(_canonical_compact_bytes(challenger)) != CHALLENGER_RESULT_SIZE
        or _canonical_sha256(challenger) != CHALLENGER_RESULT_SHA256
    ):
        raise E0040FormalMappingError("E-0040 embedded challenger result drifted")
    source_receipt = payload.get("source_evidence_receipt")
    if (
        not isinstance(source_receipt, dict)
        or _canonical_sha256(source_receipt) != SOURCE_EVIDENCE_RECEIPT_SHA256
    ):
        raise E0040FormalMappingError("E-0040 source evidence receipt drifted")
    metrics = payload.get("metrics")
    if metrics != {
        "source_row_count": 64,
        "schema_node_count": 77,
        "baseline_selected_count": 59,
        "final_selected_count": 61,
        "internal_role_repair_selected_count": 2,
        "source_only_structural_count": 3,
        "selected_anchor_count": 43,
        "selected_path_count": 18,
        "baseline_interval_count": 43,
        "final_interval_count": 44,
        "final_row_status_counts": {
            "NO_ADMISSIBLE_PAIR": 3,
            "RESOLVED_ANCHOR": 43,
            "RESOLVED_PATH": 18,
        },
        "base_collision_pair_count": 6,
        "result_collision_pair_count": 6,
        "new_collision_pair_count": 0,
        "normalization_changed_schema_node_count": 21,
        "normalization_derived_key_count": 33,
        "mapper_invocation_count": 2,
        "all_intervals_exhaustive": True,
        "all_pruning_counts_zero": True,
    }:
        raise E0040FormalMappingError("E-0040 mapping-only metrics drifted")
    access = payload.get("access_contract")
    if access != {
        "validation_order": list(_VALIDATION_ORDER),
        "e0037_seal_validated_before_mapping_open": True,
        "unique_s3_restore_record_validated_before_mapping_open": True,
        "e0037_mapping_semantic_decode_count": 1,
        "e0037_mapping_stable_identity_read_count_per_build": 2,
        "e0037_source_structure_file_opened": False,
        "e0038_or_e0039_mapping_artifact_opened": False,
        "review_or_steward_answers_opened": False,
        "numeric_status_or_postjoin_artifact_opened": False,
        "period_unit_or_source_scope_answer_artifact_opened": False,
        "raw_source_report_scope_extracted_or_used": False,
        "schema_node_applicability_scopes_present": True,
        "history_or_mongodb_opened": False,
        "holdout_opened": False,
        "qwen_raw_rejected_or_token_output_opened": False,
        "prior_mapping_page_and_row_ordinal_fields_passed_to_core": False,
        "process_contamination_guard_passed": True,
        "stable_inputs_revalidated_after_mapping": True,
    }:
        raise E0040FormalMappingError("E-0040 mapping-only answer-free receipt drifted")
    if payload.get("e0037_authority_receipt") != {
        "mapping_only_sha256": E0037_MAPPING_ONLY_SHA256,
        "mapping_seal_sha256": E0037_MAPPING_SEAL_SHA256,
        "mapping_capture_git_commit": "3dd2681133e939671f9c1818656804a7753fde8a",
        "s3_snapshot_id": S3_SNAPSHOT_ID,
        "s3_snapshot_record_sha256": S3_SNAPSHOT_RECORD_SHA256,
        "s3_registry_line": {
            "registry_path": S3_REGISTRY_RELATIVE_PATH.as_posix(),
            "line_number": 5,
            "line_sha256": S3_SNAPSHOT_LINE_SHA256,
            "line_size_bytes": S3_SNAPSHOT_LINE_SIZE,
            "canonical_record_sha256": S3_SNAPSHOT_RECORD_SHA256,
        },
        "manifest_sha256": "b7b2b5bd4249d93fc8bca2210228ffd000eb36e5ebc0bb7167dde4e774478c8c",
        "run_record_sha256": "68b35baa1f3993021db5e550b87bd42af515076dd84e2e968248a27d02a22a34",
        "restore_verified": True,
    }:
        raise E0040FormalMappingError("E-0040 E-0037 authority receipt drifted")
    if payload.get("limitations") != prerequisites.control.get("limitations"):
        raise E0040FormalMappingError("E-0040 mapping limitations drifted")
    if payload.get("authority") != {
        "mapping_output_hash_identity": True,
        "generic_normalization_and_role_repair_diagnostics": True,
        "schema_authority": False,
        "mapping_accuracy": False,
        "review_or_steward_approval": False,
        "numeric_period_unit_scope": False,
        "accounting_or_excel": False,
        "holdout_or_production": False,
    }:
        raise E0040FormalMappingError("E-0040 mapping authority drifted")


def _assert_exact_payload(
    actual: Mapping[str, Any],
    expected: Mapping[str, Any],
    label: str,
) -> None:
    if set(actual) != set(expected) or actual != expected:
        raise E0040FormalMappingError(f"{label} differs from deterministic replay")
    if _encoded_json(actual) != _encoded_json(expected):
        raise E0040FormalMappingError(f"{label} canonical bytes differ")


def _assemble_mapping_seal(
    *,
    commit: str,
    control_stable: _StableFile,
    mapping_stable: _StableFile,
    mapping_payload: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "format_version": 1,
        "experiment_id": "E-0040",
        "dataset_role": "CALIBRATION",
        "state": MAPPING_SEAL_STATE,
        "seal_git_commit": commit,
        "seal_git_dirty": False,
        "mapping_capture_git_commit": mapping_payload["capture_git_commit"],
        "inventory": {"file_count": 1, "files": [mapping_stable.artifact]},
        "mapping_status": "CHALLENGER_COMPLETE_61_SELECTED_3_SOURCE_ONLY",
        "result_projection_sha256": RESULT_PROJECTION_SHA256,
        "metrics": mapping_payload["metrics"],
        "result_receipts": mapping_payload["result_receipts"],
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
            "exact_object_equality": True,
            "exact_canonical_byte_equality": True,
            "mapping_core_result_used_to_change_published_mapping": False,
            "mapping_and_seal_clean_git_commit_equal": True,
            "tracked_ledger_head_blob_binding_required": True,
        },
        "access_contract": {
            "mapping_only_envelope_and_canonical_bytes_validated_before_replay": True,
            "mapping_only_stable_identity_read_count": 2,
            "mapping_directory_exact_inventory_validated_before_replay_and_publication": True,
            "answer_free_process_guarded_before_reads_and_publication": True,
            "e0038_or_e0039_mapping_artifact_opened": False,
            "review_or_steward_answers_opened": False,
            "numeric_status_or_postjoin_artifact_opened": False,
            "period_unit_or_source_scope_answer_artifact_opened": False,
            "history_or_mongodb_opened": False,
            "holdout_opened": False,
            "qwen_raw_rejected_or_token_output_opened": False,
        },
        "authority": {
            "exact_one_file_hash_identity": True,
            "deterministic_replay_byte_identity": True,
            "schema_authority": False,
            "mapping_accuracy": False,
            "review_or_steward_approval": False,
            "numeric_period_unit_scope": False,
            "accounting_excel_holdout_or_production": False,
        },
        "claim_boundary": _MAPPING_SEAL_CLAIM,
    }


def _validate_mapping_seal_payload(
    payload: Mapping[str, Any],
    prerequisites: _Prerequisites,
    *,
    mapping_stable: _StableFile,
    mapping_payload: Mapping[str, Any],
    expected_git_commit: str,
) -> None:
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
            "metrics",
            "result_receipts",
            "input_hash_ledger",
            "replay",
            "access_contract",
            "authority",
            "claim_boundary",
        },
        "E-0040 mapping seal payload",
    )
    _validate_mapping_before_replay(
        mapping_payload,
        prerequisites,
        expected_git_commit=expected_git_commit,
        encoded_bytes=mapping_stable.payload,
    )
    expected = _assemble_mapping_seal(
        commit=expected_git_commit,
        control_stable=prerequisites.control_stable,
        mapping_stable=mapping_stable,
        mapping_payload=mapping_payload,
    )
    _assert_exact_payload(payload, expected, "E-0040 mapping seal")
    inventory = _exact_keys(payload.get("inventory"), {"file_count", "files"}, "seal inventory")
    if inventory != {"file_count": 1, "files": [mapping_stable.artifact]}:
        raise E0040FormalMappingError("E-0040 mapping seal inventory drifted")
    _artifact_record(
        mapping_stable.artifact,
        "E-0040 sealed mapping artifact",
        expected_path=MAPPING_ONLY_RELATIVE_PATH,
    )
    if (
        payload.get("format_version") != 1
        or payload.get("experiment_id") != "E-0040"
        or payload.get("dataset_role") != "CALIBRATION"
        or payload.get("state") != MAPPING_SEAL_STATE
        or payload.get("seal_git_commit") != expected_git_commit
        or payload.get("mapping_capture_git_commit") != expected_git_commit
        or payload.get("seal_git_dirty") is not False
        or payload.get("mapping_status") != "CHALLENGER_COMPLETE_61_SELECTED_3_SOURCE_ONLY"
        or payload.get("result_projection_sha256") != RESULT_PROJECTION_SHA256
        or payload.get("metrics") != mapping_payload.get("metrics")
        or payload.get("result_receipts") != mapping_payload.get("result_receipts")
        or payload.get("claim_boundary") != _MAPPING_SEAL_CLAIM
    ):
        raise E0040FormalMappingError("E-0040 mapping seal identity/linkage drifted")


def capture_e0040_mapping_seal(
    project_root: Path,
    *,
    config_path: Path = CONTROL_RELATIVE_PATH,
    mapping_only_path: Path = MAPPING_ONLY_RELATIVE_PATH,
    output_path: Path = MAPPING_SEAL_RELATIVE_PATH,
) -> dict[str, Any]:
    """Replay and exclusively hash-seal the sole canonical mapping file."""

    _assert_answer_free_process()
    root = project_root.resolve()
    commit = _clean_git_commit(root)
    _mapping_output_inventory(root, require_mapping=True)
    reader = _read_stable_file
    prerequisites = _load_prerequisites(root, config_path, reader)
    mapping_path = _canonical_input_path(
        root,
        mapping_only_path,
        MAPPING_ONLY_RELATIVE_PATH,
        "E-0040 mapping-only artifact",
    )
    output = _canonical_input_path(
        root,
        output_path,
        MAPPING_SEAL_RELATIVE_PATH,
        "E-0040 mapping seal",
    )
    mapping_stable = _stable_read(
        reader,
        root,
        mapping_path,
        "E-0040 mapping-only artifact",
        maximum_size=_MAX_JSON_BYTES,
    )
    mapping_payload = _decode_json_object(mapping_stable.payload, "E-0040 mapping-only artifact")
    _validate_mapping_before_replay(
        mapping_payload,
        prerequisites,
        expected_git_commit=commit,
        encoded_bytes=mapping_stable.payload,
    )

    replay_payload = build_e0040_mapping_only(
        root,
        capture_git_commit=commit,
        config_path=config_path,
    )
    _assert_exact_payload(mapping_payload, replay_payload, "E-0040 mapping-only replay")
    if _encoded_json(replay_payload) != mapping_stable.payload:
        raise E0040FormalMappingError("E-0040 deterministic replay bytes differ")
    seal_payload = _assemble_mapping_seal(
        commit=commit,
        control_stable=prerequisites.control_stable,
        mapping_stable=mapping_stable,
        mapping_payload=mapping_payload,
    )
    _assert_finite_tree(seal_payload, "E-0040 mapping seal")
    _validate_mapping_seal_payload(
        seal_payload,
        prerequisites,
        mapping_stable=mapping_stable,
        mapping_payload=mapping_payload,
        expected_git_commit=commit,
    )
    _recheck_payload_ledgers(root, replay_payload, reader)
    _assert_payload_ledgers_match_head(root, replay_payload, reader)
    _assert_answer_free_process()
    if _clean_git_commit(root) != commit:
        raise E0040FormalMappingError("Git commit changed during E-0040 mapping sealing")
    _assert_answer_free_process()
    _assert_payload_ledgers_match_head(root, replay_payload, reader)
    _recheck_payload_ledgers(root, replay_payload, reader)
    _mapping_output_inventory(root, require_mapping=True)
    _assert_unchanged(reader, root, mapping_stable, "E-0040 mapping-only artifact")
    _exclusive_publish_json(root, output, seal_payload)
    return seal_payload
