"""Crash-bounded reference-blind PP-OCRv6 numeric cache.

The V1 all-axis runner made one process responsible for 667k recognitions.  A
process-level termination therefore discarded many hours even though the
reader axis and recognizer were sound.  V2 partitions that same immutable,
anonymous axis into deterministic contiguous shards.  Only a completed shard
directory is authoritative; an interrupted hidden stage is neither a result
nor a resumable partial output.  Once every shard is present, a separate
aggregate publication proves exact, gap-free, ordered coverage.

Sharding changes lifecycle only.  The recognizer still receives no bank,
filing, page, label, period, unit, family, schema, expected value or accounting
equation.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bctc_ai.evaluation import family_first_semantic_label_archive_v1 as archive_v1
from bctc_ai.ocr import family_first_ppocrv6_numeric_runner_v1 as runner_v1
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
    "AGGREGATE_ROOT",
    "CACHE_ROOT",
    "SHARD_SIZE",
    "FamilyFirstPPocrV6NumericShardedRunnerV2Error",
    "aggregate_authenticated_family_first_ppocrv6_numeric_v2",
    "project_authenticated_family_first_ppocrv6_numeric_shards_v2",
    "run_authenticated_family_first_ppocrv6_numeric_missing_shards_v2",
    "run_authenticated_family_first_ppocrv6_numeric_shard_v2",
]


CACHE_ROOT = Path("output/calibration/family-first-ppocrv6-numeric-cache-v2")
SHARDS_ROOT = CACHE_ROOT / "shards"
AGGREGATE_ROOT = CACHE_ROOT / "aggregate"
SHARD_SIZE = 2048
EXPERIMENT_ID = "FAMILY_FIRST_ALL_FILING_PPOCRV6_NUMERIC_SHARDED_CACHE_V2"
SHARD_FORMAT_VERSION = "FAMILY_FIRST_PPOCRV6_NUMERIC_COMPLETED_SHARD_V2"
AGGREGATE_FORMAT_VERSION = "FAMILY_FIRST_PPOCRV6_NUMERIC_AGGREGATE_V2"
PROPOSAL_FORMAT_VERSION = runner_v1.PROPOSAL_FORMAT_VERSION
_PROPOSAL_NAME = "numeric-proposals.jsonl"
_SHARD_MANIFEST_NAME = "shard_manifest.json"
_AGGREGATE_MANIFEST_NAME = "aggregate_manifest.json"
_CONFIG_PATH = runner_v1._CONFIG_PATH
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_TRUST_PATHS = tuple(
    sorted(
        {
            *(
                path
                for path in runner_v1._TRUST_PATHS
                if path.as_posix()
                not in {
                    "src/bctc_ai/evaluation/family_first_ppocrv6_numeric_index_v1.py",
                    "scripts/experiments/run_family_first_ppocrv6_numeric_v1.py",
                }
            ),
            Path("src/bctc_ai/ocr/family_first_ppocrv6_numeric_sharded_runner_v2.py"),
            Path("src/bctc_ai/evaluation/family_first_ppocrv6_numeric_index_v2.py"),
            Path("scripts/experiments/run_family_first_ppocrv6_numeric_v2.py"),
        },
        key=lambda item: item.as_posix(),
    )
)
_EXECUTION_POLICY = {
    "accounting_equation_available_to_reader": False,
    "bank_file_page_period_scope_available_to_reader": False,
    "batch_size": 64,
    "completed_shard_reuse": True,
    "cpu_threads": 16,
    "device": "cpu",
    "expected_value_available_to_reader": False,
    "family_or_schema_available_to_reader": False,
    "geometry_available_to_reader": False,
    "label_or_owner_available_to_reader": False,
    "mkldnn": False,
    "network_permitted": False,
    "precision": "fp32",
    "prior_incomplete_stage_access": False,
    "resume_within_shard": False,
    "shard_size": SHARD_SIZE,
}
_SAFETY = {
    **runner_v1._SAFETY,
    "completed_shard_is_authoritative_only_after_atomic_publication": True,
    "historical_incomplete_stage_absence_attestation": False,
    "quality_selection_absence_attestation": False,
    "retry_absence_attestation": False,
    "single_physical_execution_attestation": False,
}


class FamilyFirstPPocrV6NumericShardedRunnerV2Error(RuntimeError):
    """One shard, the complete shard axis, or its aggregate drifted."""


def _error(message: str) -> FamilyFirstPPocrV6NumericShardedRunnerV2Error:
    return FamilyFirstPPocrV6NumericShardedRunnerV2Error(message)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _shard_count(sample_count: int) -> int:
    if type(sample_count) is not int or sample_count <= 0:
        raise _error("numeric shard denominator must be one positive exact integer")
    return (sample_count + SHARD_SIZE - 1) // SHARD_SIZE


def _range(sample_count: int, shard_ordinal: int) -> tuple[int, int, int, int]:
    count = _shard_count(sample_count)
    if type(shard_ordinal) is not int or not 1 <= shard_ordinal <= count:
        raise _error("numeric shard ordinal lies outside the fixed shard axis")
    first = (shard_ordinal - 1) * SHARD_SIZE + 1
    last = min(shard_ordinal * SHARD_SIZE, sample_count)
    return first, last, last - first + 1, count


def _shard_name(shard_ordinal: int) -> str:
    return f"shard-{shard_ordinal:06d}"


def _git_binding(root: Path) -> dict[str, Any]:
    if runtime_v3._git(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise _error("formal numeric shard execution requires one clean Git worktree")
    commit = runtime_v3._git(root, "rev-parse", "HEAD").decode("ascii").strip()
    tree = runtime_v3._git(root, "rev-parse", "HEAD:src/bctc_ai").decode("ascii").strip()
    if _COMMIT.fullmatch(commit) is None or _COMMIT.fullmatch(tree) is None:
        raise _error("formal numeric shard Git identity is malformed")
    return {
        "commit": commit,
        "dirty": False,
        "implementation_refs": [
            runtime_v3._tracked_ref(root, path, f"numeric V2 trust file {path}")
            for path in _TRUST_PATHS
        ],
        "source_tree_oid": tree,
    }


def _git_ledger(root: Path, binding: Any) -> str:
    """Authenticate a completed-shard commit on one clean descendant HEAD."""

    head = archive_v1._clean_head(root)
    expected_paths = [path.as_posix() for path in _TRUST_PATHS]
    if (
        type(binding) is not dict
        or set(binding) != {"commit", "dirty", "implementation_refs", "source_tree_oid"}
        or type(binding["commit"]) is not str
        or _COMMIT.fullmatch(binding["commit"]) is None
        or binding["dirty"] is not False
        or type(binding["source_tree_oid"]) is not str
        or _COMMIT.fullmatch(binding["source_tree_oid"]) is None
        or type(binding["implementation_refs"]) is not list
        or [
            item.get("path") if type(item) is dict else None
            for item in binding["implementation_refs"]
        ]
        != expected_paths
    ):
        raise _error("numeric V2 Git binding drifted")
    run_commit = binding["commit"]
    try:
        archive_v1._git(root, "merge-base", "--is-ancestor", run_commit, head)
    except archive_v1.FamilyFirstSemanticLabelArchiveV1Error as exc:
        raise _error("numeric V2 run commit is not an ancestor of HEAD") from exc
    for raw in binding["implementation_refs"]:
        try:
            reference = archive_v1._ref(raw, "numeric V2 trust file")
        except archive_v1.FamilyFirstSemanticLabelArchiveV1Error as exc:
            raise _error("numeric V2 trust-file reference drifted") from exc
        committed = archive_v1._git(root, "show", f"{run_commit}:{reference['path']}")
        current = archive_v1._git(root, "show", f"{head}:{reference['path']}")
        disk = _root_bytes(root, Path(reference["path"]), "numeric V2 trust file")
        if (
            len(committed) != reference["size_bytes"]
            or _sha(committed) != reference["sha256"]
            or committed != current
            or committed != disk
        ):
            raise _error("numeric V2 trust file changed on the descendant chain")
    run_tree = (
        archive_v1._git(root, "rev-parse", f"{run_commit}:src/bctc_ai")
        .decode("ascii", errors="strict")
        .strip()
    )
    if run_tree != binding["source_tree_oid"]:
        raise _error("numeric V2 source-tree identity drifted at its run commit")
    if archive_v1._clean_head(root) != head:
        raise _error("Git HEAD/worktree changed during numeric V2 ledger replay")
    return head


def _root_bytes(root: Path, relative: Path, label: str) -> bytes:
    try:
        return archive_v1._root_bytes(root, relative, label)
    except archive_v1.FamilyFirstSemanticLabelArchiveV1Error as exc:
        raise _error(f"cannot read stable nofollow {label}") from exc


def _canonical_object(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"{label} is not strict JSON") from exc
    if type(value) is not dict or payload != canonical_json_bytes_v1(value):
        raise _error(f"{label} is not one canonical JSON object")
    return value


def _ref(payload: bytes, path: Path) -> dict[str, Any]:
    return {"path": path.as_posix(), "sha256": _sha(payload), "size_bytes": len(payload)}


def _matches(payload: bytes, raw: Any, path: Path, label: str) -> None:
    try:
        reference = archive_v1._ref(raw, label)
    except archive_v1.FamilyFirstSemanticLabelArchiveV1Error as exc:
        raise _error(f"{label} reference drifted") from exc
    if (
        reference["path"] != path.as_posix()
        or reference["size_bytes"] != len(payload)
        or reference["sha256"] != _sha(payload)
    ):
        raise _error(f"{label} bytes/path differ from their content reference")


def _configuration_ref(root: Path) -> tuple[bytes, dict[str, Any]]:
    payload = runtime_v3._stable_bytes(root / _CONFIG_PATH, "numeric runtime config")
    return payload, _ref(payload, _CONFIG_PATH)


def _cache_fds(root: Path) -> tuple[int, int]:
    calibration = root / "output/calibration"
    if not calibration.is_dir() or calibration.is_symlink():
        raise _error("fixed output/calibration root is unsafe")
    calibration_fd = os.open(calibration, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        try:
            os.mkdir(CACHE_ROOT.name, 0o700, dir_fd=calibration_fd)
            os.fsync(calibration_fd)
        except FileExistsError:
            pass
        cache_fd = os.open(
            CACHE_ROOT.name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=calibration_fd,
        )
    finally:
        os.close(calibration_fd)
    try:
        try:
            os.mkdir(SHARDS_ROOT.name, 0o700, dir_fd=cache_fd)
            os.fsync(cache_fd)
        except FileExistsError:
            pass
        shards_fd = os.open(
            SHARDS_ROOT.name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=cache_fd,
        )
    except BaseException:
        os.close(cache_fd)
        raise
    return cache_fd, shards_fd


def _stage(shards_fd: int, shard_ordinal: int) -> tuple[str, int, tuple[int, int]]:
    for _attempt in range(128):
        name = f".{_shard_name(shard_ordinal)}-stage-{secrets.token_hex(8)}"
        try:
            os.mkdir(name, 0o700, dir_fd=shards_fd)
            break
        except FileExistsError:
            continue
    else:
        raise _error("cannot allocate one private numeric shard stage")
    descriptor = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=shards_fd)
    opened = os.fstat(descriptor)
    return name, descriptor, (opened.st_dev, opened.st_ino)


def _cleanup_stage(shards_fd: int, name: str, identity: tuple[int, int]) -> None:
    """Remove only the exact stage created by this live invocation."""

    try:
        named = os.stat(name, dir_fd=shards_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    if (named.st_dev, named.st_ino) != identity:
        return
    descriptor = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=shards_fd)
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != identity:
            return
        for leaf in (_PROPOSAL_NAME, _SHARD_MANIFEST_NAME):
            try:
                os.unlink(leaf, dir_fd=descriptor)
            except FileNotFoundError:
                pass
        if os.listdir(descriptor):
            return
    finally:
        os.close(descriptor)
    try:
        named = os.stat(name, dir_fd=shards_fd, follow_symlinks=False)
        if (named.st_dev, named.st_ino) == identity:
            os.rmdir(name, dir_fd=shards_fd)
    except FileNotFoundError:
        pass


def _readback_jsonl(
    descriptor: int,
    *,
    first_sample_ordinal: int,
    expected_count: int,
) -> tuple[str, int, int]:
    os.lseek(descriptor, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    buffer = b""
    count = 0
    empty_count = 0
    size = 0
    while chunk := os.read(descriptor, 1024 * 1024):
        digest.update(chunk)
        size += len(chunk)
        buffer += chunk
        lines = buffer.split(b"\n")
        buffer = lines.pop()
        for line in lines:
            ordinal = first_sample_ordinal + count
            try:
                raw = json.loads(line.decode("utf-8", errors="strict"))
                proposal = runner_v1._validate_result(raw, ordinal)
            except (
                UnicodeDecodeError,
                json.JSONDecodeError,
                runner_v1.FamilyFirstPPocrV6NumericRunnerV1Error,
            ) as exc:
                raise _error("numeric shard proposal JSONL readback drifted") from exc
            if line + b"\n" != canonical_json_bytes_v1(proposal):
                raise _error("numeric shard proposal line is not canonical")
            empty_count += proposal["raw_prediction"] == ""
            count += 1
    if buffer or count != expected_count:
        raise _error("numeric shard proposal denominator/trailing bytes drifted")
    return digest.hexdigest(), size, empty_count


def _expected_counts(sample_count: int, *, final_shard: bool) -> dict[str, int]:
    return {
        "formal_run_count": 1,
        "model_build_count": 1,
        "reader_chunk_call_count": (sample_count + 4095) // 4096 + int(final_shard),
        "recognizer_predict_call_count": (sample_count + 63) // 64,
        "result_count": sample_count,
    }


def _validate_runtime(value: Any, model: dict[str, Any]) -> dict[str, Any]:
    expected_packages = {"paddleocr": "3.7.0", "paddlepaddle": "3.3.0"}
    if (
        type(value) is not dict
        or set(value) != {"device", "model", "packages", "precision"}
        or value["device"] != "cpu"
        or value["precision"] != "fp32"
        or not same_typed_json_v1(value["model"], model)
        or not same_typed_json_v1(value["packages"], expected_packages)
    ):
        raise _error("numeric shard runtime identity drifted")
    return canonical_clone_v1(value)


def _context(
    root: Path,
    archive_capability: archive_v1.AuthenticatedFamilyFirstSemanticLabelArchiveV1,
    model_cache: Path,
    *,
    open_reader: bool,
    pinned_git: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state, manifest, batch, plan, _private = archive_v1._archive_payloads(archive_capability)
    if state.root != root:
        raise _error("numeric archive belongs to another project root")
    projection = {
        "archive_id": manifest["archive_id"],
        "batch_id": batch["batch_id"],
        "plan_id": plan["plan_id"],
        "sample_count": batch["sample_count"],
    }
    session = None
    if open_reader:
        live_projection, session = (
            archive_v1.open_authenticated_family_first_semantic_label_reader_snapshot_v1(
                root, archive_capability
            )
        )
        for field in ("archive_id", "batch_id", "plan_id", "sample_count"):
            if live_projection[field] != projection[field]:
                raise _error("numeric shard archive snapshot projection drifted")
    config_payload, config_ref = _configuration_ref(root)
    model, _directory = kernel_v1._recognizer_projection(root, model_cache)
    git = _git_binding(root) if pinned_git is None else canonical_clone_v1(pinned_git)
    if pinned_git is not None:
        _git_ledger(root, git)
    return {
        "archive": archive_capability,
        "batch": batch,
        "config_payload": config_payload,
        "config_ref": config_ref,
        "git": git,
        "model": model,
        "model_cache": model_cache,
        "projection": projection,
        "session": session,
        "strict_git_head": pinned_git is None,
    }


def _assert_context(root: Path, context: dict[str, Any]) -> None:
    live_model, _directory = kernel_v1._recognizer_projection(root, context["model_cache"])
    config_payload, config_ref = _configuration_ref(root)
    if (
        not same_typed_json_v1(live_model, context["model"])
        or config_payload != context["config_payload"]
        or not same_typed_json_v1(config_ref, context["config_ref"])
    ):
        raise _error("numeric shard code/config/model/Git changed during execution")
    if context["strict_git_head"]:
        if not same_typed_json_v1(_git_binding(root), context["git"]):
            raise _error("numeric shard Git HEAD changed during execution")
    else:
        _git_ledger(root, context["git"])


def _shard_material(
    *,
    context: dict[str, Any],
    shard_ordinal: int,
    first: int,
    last: int,
    count: int,
    shard_count: int,
    proposal_ref: dict[str, Any],
    runtime: dict[str, Any],
    execution_counts: dict[str, int],
    metrics: dict[str, Any],
    started_at: str,
    completed_at: str,
) -> dict[str, Any]:
    projection = context["projection"]
    return {
        "artifacts": {"numeric_proposals": canonical_clone_v1(proposal_ref)},
        "claim_boundary": (
            "ONE_ATOMICALLY_COMPLETED_CONTIGUOUS_REFERENCE_BLIND_NUMERIC_SHARD_"
            "NO_SINGLE_PHYSICAL_ATTEMPT_OR_RETRY_ABSENCE_ATTESTATION"
        ),
        "completed_at": completed_at,
        "execution_counts": canonical_clone_v1(execution_counts),
        "execution_policy": canonical_clone_v1(_EXECUTION_POLICY),
        "experiment_id": EXPERIMENT_ID,
        "first_sample_ordinal": first,
        "format_version": SHARD_FORMAT_VERSION,
        "git_binding": canonical_clone_v1(context["git"]),
        "input": {
            "archive_id": projection["archive_id"],
            "batch_id": projection["batch_id"],
            "configuration_ref": canonical_clone_v1(context["config_ref"]),
            "plan_id": projection["plan_id"],
            "sample_count": projection["sample_count"],
        },
        "last_sample_ordinal": last,
        "metrics": canonical_clone_v1(metrics),
        "runtime": canonical_clone_v1(runtime),
        "safety": canonical_clone_v1(_SAFETY),
        "sample_count": count,
        "shard_count": shard_count,
        "shard_ordinal": shard_ordinal,
        "started_at": started_at,
        "state": "ATOMIC_COMPLETED_REFERENCE_BLIND_PPOCRV6_NUMERIC_SHARD",
    }


def _run_shard(
    root: Path,
    context: dict[str, Any],
    *,
    shard_ordinal: int,
) -> dict[str, Any]:
    projection = context["projection"]
    first, last, count, shard_count = _range(projection["sample_count"], shard_ordinal)
    final_shard = last == projection["sample_count"]
    cache_fd, shards_fd = _cache_fds(root)
    stage_name = ""
    stage_fd = -1
    stage_identity: tuple[int, int] | None = None
    proposal_fd = -1
    try:
        official_name = _shard_name(shard_ordinal)
        try:
            os.stat(official_name, dir_fd=shards_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise _error("official numeric shard already exists")
        stage_name, stage_fd, stage_identity = _stage(shards_fd, shard_ordinal)
        proposal_fd = os.open(
            _PROPOSAL_NAME,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o400,
            dir_fd=stage_fd,
        )
        emitted = 0

        def sink(raw: dict[str, Any]) -> None:
            nonlocal emitted
            ordinal = first + emitted
            try:
                proposal = runner_v1._validate_result(raw, ordinal)
            except runner_v1.FamilyFirstPPocrV6NumericRunnerV1Error as exc:
                raise _error("numeric shard recognizer proposal drifted") from exc
            file_ops_v1._write_all(proposal_fd, canonical_json_bytes_v1(proposal))
            emitted += 1

        started_at = datetime.now(UTC).isoformat()
        runtime, counts, kernel_metrics = (
            kernel_v1.execute_authenticated_ppocrv6_numeric_reference_blind_v1(
                root,
                context["session"],
                expected_sample_count=count,
                model_cache=context["model_cache"],
                result_sink=sink,
                batch_size=_EXECUTION_POLICY["batch_size"],
                cpu_threads=_EXECUTION_POLICY["cpu_threads"],
                first_sample_ordinal=first,
                require_archive_end=final_shard,
            )
        )
        expected_counts = _expected_counts(count, final_shard=final_shard)
        if type(counts) is not dict or not same_typed_json_v1(counts, expected_counts):
            raise _error("numeric shard execution counts drifted")
        runtime = _validate_runtime(runtime, context["model"])
        if (
            type(kernel_metrics) is not dict
            or set(kernel_metrics) != {"model_load_seconds", "total_wall_seconds"}
            or any(
                type(value) is not float or not math.isfinite(value) or value < 0
                for value in kernel_metrics.values()
            )
            or kernel_metrics["total_wall_seconds"] < kernel_metrics["model_load_seconds"]
        ):
            raise _error("numeric shard runtime metrics drifted")
        os.fsync(proposal_fd)
        proposal_sha, proposal_size, empty_count = _readback_jsonl(
            proposal_fd,
            first_sample_ordinal=first,
            expected_count=count,
        )
        if emitted != count:
            raise _error("numeric shard sink denominator drifted")
        _assert_context(root, context)
        proposal_path = SHARDS_ROOT / official_name / _PROPOSAL_NAME
        proposal_ref = {
            "path": proposal_path.as_posix(),
            "sha256": proposal_sha,
            "size_bytes": proposal_size,
        }
        metrics = {
            **kernel_metrics,
            "empty_prediction_count": empty_count,
            "sample_count": emitted,
        }
        material = _shard_material(
            context=context,
            shard_ordinal=shard_ordinal,
            first=first,
            last=last,
            count=count,
            shard_count=shard_count,
            proposal_ref=proposal_ref,
            runtime=runtime,
            execution_counts=counts,
            metrics=metrics,
            started_at=started_at,
            completed_at=datetime.now(UTC).isoformat(),
        )
        manifest = {
            **material,
            "shard_id": "ffpnsv2:shard:" + canonical_json_sha256_v1(material),
        }
        file_ops_v1._write_exclusive(
            stage_fd, _SHARD_MANIFEST_NAME, canonical_json_bytes_v1(manifest)
        )
        os.fsync(stage_fd)
        if sorted(os.listdir(stage_fd)) != sorted([_PROPOSAL_NAME, _SHARD_MANIFEST_NAME]):
            raise _error("numeric shard stage listing drifted")
        _assert_context(root, context)
        os.close(proposal_fd)
        proposal_fd = -1
        os.close(stage_fd)
        stage_fd = -1
        file_ops_v1._rename_noreplace_fd(shards_fd, stage_name, official_name)
        named = os.stat(official_name, dir_fd=shards_fd, follow_symlinks=False)
        if stage_identity is None or (named.st_dev, named.st_ino) != stage_identity:
            raise _error("published numeric shard inode differs from its completed stage")
        stage_name = ""
        _assert_context(root, context)
        return manifest
    finally:
        if proposal_fd >= 0:
            os.close(proposal_fd)
        if stage_fd >= 0:
            os.close(stage_fd)
        if stage_name and stage_identity is not None:
            _cleanup_stage(shards_fd, stage_name, stage_identity)
        os.close(shards_fd)
        os.close(cache_fd)


def _proposal_iterator(
    payload: bytes,
    *,
    first_sample_ordinal: int,
    expected_count: int,
):
    offset = 0
    count = 0
    while offset < len(payload):
        end = payload.find(b"\n", offset)
        if end < 0:
            raise _error("numeric shard JSONL has one incomplete final line")
        raw = payload[offset : end + 1]
        ordinal = first_sample_ordinal + count
        try:
            value = json.loads(raw.decode("utf-8", errors="strict"))
            proposal = runner_v1._validate_result(value, ordinal)
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
            runner_v1.FamilyFirstPPocrV6NumericRunnerV1Error,
        ) as exc:
            raise _error("numeric shard JSONL proposal drifted") from exc
        if raw != canonical_json_bytes_v1(proposal):
            raise _error("numeric shard JSONL proposal is not canonical")
        yield offset, end + 1, proposal
        count += 1
        offset = end + 1
    if count != expected_count:
        raise _error("numeric shard JSONL denominator drifted")


def _directory_listing(root: Path, relative: Path, label: str) -> list[str]:
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in relative.parts:
            child = os.open(
                part,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = child
        return sorted(os.listdir(descriptor))
    except OSError as exc:
        raise _error(f"cannot inspect stable nofollow {label}") from exc
    finally:
        os.close(descriptor)


def _validate_shard(
    root: Path,
    context: dict[str, Any],
    shard_ordinal: int,
) -> tuple[dict[str, Any], bytes, bytes]:
    projection = context["projection"]
    first, last, count, shard_count = _range(projection["sample_count"], shard_ordinal)
    shard_root = SHARDS_ROOT / _shard_name(shard_ordinal)
    if _directory_listing(root, shard_root, "numeric shard") != sorted(
        [_PROPOSAL_NAME, _SHARD_MANIFEST_NAME]
    ):
        raise _error("completed numeric shard directory listing drifted")
    proposal_payload = _root_bytes(root, shard_root / _PROPOSAL_NAME, "numeric shard proposals")
    manifest_payload = _root_bytes(
        root, shard_root / _SHARD_MANIFEST_NAME, "numeric shard manifest"
    )
    manifest = _canonical_object(manifest_payload, "numeric shard manifest")
    expected_fields = {
        "artifacts",
        "claim_boundary",
        "completed_at",
        "execution_counts",
        "execution_policy",
        "experiment_id",
        "first_sample_ordinal",
        "format_version",
        "git_binding",
        "input",
        "last_sample_ordinal",
        "metrics",
        "runtime",
        "safety",
        "sample_count",
        "shard_count",
        "shard_id",
        "shard_ordinal",
        "started_at",
        "state",
    }
    material = canonical_clone_v1(manifest)
    shard_id = material.pop("shard_id", None)
    expected_input = {
        "archive_id": projection["archive_id"],
        "batch_id": projection["batch_id"],
        "configuration_ref": canonical_clone_v1(context["config_ref"]),
        "plan_id": projection["plan_id"],
        "sample_count": projection["sample_count"],
    }
    final_shard = last == projection["sample_count"]
    if (
        set(manifest) != expected_fields
        or manifest["format_version"] != SHARD_FORMAT_VERSION
        or manifest["experiment_id"] != EXPERIMENT_ID
        or manifest["state"] != "ATOMIC_COMPLETED_REFERENCE_BLIND_PPOCRV6_NUMERIC_SHARD"
        or shard_id != "ffpnsv2:shard:" + canonical_json_sha256_v1(material)
        or type(manifest["started_at"]) is not str
        or not manifest["started_at"]
        or type(manifest["completed_at"]) is not str
        or not manifest["completed_at"]
        or manifest["shard_ordinal"] != shard_ordinal
        or manifest["shard_count"] != shard_count
        or manifest["first_sample_ordinal"] != first
        or manifest["last_sample_ordinal"] != last
        or manifest["sample_count"] != count
        or not same_typed_json_v1(manifest["input"], expected_input)
        or not same_typed_json_v1(manifest["execution_policy"], _EXECUTION_POLICY)
        or not same_typed_json_v1(manifest["safety"], _SAFETY)
        or not same_typed_json_v1(manifest["git_binding"], context["git"])
        or not same_typed_json_v1(
            manifest["execution_counts"], _expected_counts(count, final_shard=final_shard)
        )
    ):
        raise _error("completed numeric shard contract/lineage drifted")
    _validate_runtime(manifest["runtime"], context["model"])
    metrics = manifest["metrics"]
    if (
        type(metrics) is not dict
        or set(metrics)
        != {
            "empty_prediction_count",
            "model_load_seconds",
            "sample_count",
            "total_wall_seconds",
        }
        or type(metrics["empty_prediction_count"]) is not int
        or not 0 <= metrics["empty_prediction_count"] <= count
        or metrics["sample_count"] != count
        or type(metrics["model_load_seconds"]) is not float
        or type(metrics["total_wall_seconds"]) is not float
        or not math.isfinite(metrics["model_load_seconds"])
        or not math.isfinite(metrics["total_wall_seconds"])
        or not 0 <= metrics["model_load_seconds"] <= metrics["total_wall_seconds"]
    ):
        raise _error("completed numeric shard metrics drifted")
    if type(manifest["artifacts"]) is not dict or set(manifest["artifacts"]) != {
        "numeric_proposals"
    }:
        raise _error("completed numeric shard artifact shape drifted")
    _matches(
        proposal_payload,
        manifest["artifacts"]["numeric_proposals"],
        shard_root / _PROPOSAL_NAME,
        "numeric shard proposals",
    )
    empty_count = 0
    observed = 0
    for _start, _stop, proposal in _proposal_iterator(
        proposal_payload,
        first_sample_ordinal=first,
        expected_count=count,
    ):
        sample = context["batch"]["samples"][first - 1 + observed]
        if (
            proposal["sample_id"] != sample["sample_id"]
            or proposal["crop_sha256"] != sample["crop_ref"]["sha256"]
        ):
            raise _error("completed numeric shard proposal/crop axis cross-link drifted")
        empty_count += proposal["raw_prediction"] == ""
        observed += 1
    if empty_count != metrics["empty_prediction_count"] or observed != count:
        raise _error("completed numeric shard output metrics drifted")
    return manifest, manifest_payload, proposal_payload


def run_authenticated_family_first_ppocrv6_numeric_shard_v2(
    project_root: Path,
    archive_capability: archive_v1.AuthenticatedFamilyFirstSemanticLabelArchiveV1,
    *,
    model_cache: Path,
    shard_ordinal: int,
) -> dict[str, Any]:
    """Run and atomically publish one missing fixed shard."""

    root = runtime_v3._resolve_root(project_root)
    if not isinstance(model_cache, Path):
        raise _error("numeric V2 model cache must be one pathlib Path")
    context = _context(root, archive_capability, model_cache, open_reader=True)
    return _run_shard(root, context, shard_ordinal=shard_ordinal)


def run_authenticated_family_first_ppocrv6_numeric_missing_shards_v2(
    project_root: Path,
    archive_capability: archive_v1.AuthenticatedFamilyFirstSemanticLabelArchiveV1,
    *,
    model_cache: Path,
    maximum_new_shards: int | None = None,
) -> dict[str, Any]:
    """Validate completed shards and run missing shards using one sealed snapshot.

    Restarting this orchestrator is intentionally allowed.  It never resumes an
    incomplete shard and never reads hidden stages; it only reuses directories
    that pass the complete shard validator.
    """

    root = runtime_v3._resolve_root(project_root)
    if not isinstance(model_cache, Path):
        raise _error("numeric V2 model cache must be one pathlib Path")
    if maximum_new_shards is not None and (
        type(maximum_new_shards) is not int or maximum_new_shards <= 0
    ):
        raise _error("maximum new shard count must be one positive exact integer or null")
    context = _context(root, archive_capability, model_cache, open_reader=True)
    total = _shard_count(context["projection"]["sample_count"])
    completed: list[int] = []
    created: list[int] = []
    for ordinal in range(1, total + 1):
        path = root / SHARDS_ROOT / _shard_name(ordinal)
        if os.path.lexists(path):
            _validate_shard(root, context, ordinal)
            completed.append(ordinal)
            continue
        if maximum_new_shards is not None and len(created) >= maximum_new_shards:
            continue
        _run_shard(root, context, shard_ordinal=ordinal)
        _validate_shard(root, context, ordinal)
        completed.append(ordinal)
        created.append(ordinal)
    _assert_context(root, context)
    return {
        "completed_shard_count": len(completed),
        "created_shard_count": len(created),
        "format_version": "FAMILY_FIRST_PPOCRV6_NUMERIC_SHARD_PROGRESS_V2",
        "remaining_shard_count": total - len(completed),
        "sample_count": context["projection"]["sample_count"],
        "shard_count": total,
        "state": "NUMERIC_SHARD_AXIS_COMPLETE" if len(completed) == total else "IN_PROGRESS",
    }


def project_authenticated_family_first_ppocrv6_numeric_shards_v2(
    project_root: Path,
    archive_capability: archive_v1.AuthenticatedFamilyFirstSemanticLabelArchiveV1,
    *,
    model_cache: Path,
) -> dict[str, Any]:
    """Validate and count the currently completed official shard prefix/set."""

    root = runtime_v3._resolve_root(project_root)
    if not isinstance(model_cache, Path):
        raise _error("numeric V2 model cache must be one pathlib Path")
    context = _context(root, archive_capability, model_cache, open_reader=False)
    total = _shard_count(context["projection"]["sample_count"])
    completed = []
    for ordinal in range(1, total + 1):
        if os.path.lexists(root / SHARDS_ROOT / _shard_name(ordinal)):
            _validate_shard(root, context, ordinal)
            completed.append(ordinal)
    _assert_context(root, context)
    return {
        "completed_shard_count": len(completed),
        "format_version": "FAMILY_FIRST_PPOCRV6_NUMERIC_SHARD_PROGRESS_V2",
        "remaining_shard_count": total - len(completed),
        "sample_count": context["projection"]["sample_count"],
        "shard_count": total,
        "state": "NUMERIC_SHARD_AXIS_COMPLETE" if len(completed) == total else "IN_PROGRESS",
    }


def _aggregate_material(
    *,
    context: dict[str, Any],
    proposal_ref: dict[str, Any],
    shard_manifest_refs: list[dict[str, Any]],
    shard_axis_sha256: str,
    empty_prediction_count: int,
) -> dict[str, Any]:
    projection = context["projection"]
    return {
        "artifacts": {
            "numeric_proposals": canonical_clone_v1(proposal_ref),
            "shard_manifests": canonical_clone_v1(shard_manifest_refs),
        },
        "authority": {
            "all_shard_outputs_preserved": True,
            "complete_contiguous_archive_axis_authenticated": True,
            "mapping_authority": False,
            "numeric_recognition_proposal_only": True,
            "quality_selection_absence_attestation": False,
            "retry_absence_attestation": False,
            "single_physical_execution_attestation": False,
        },
        "claim_boundary": (
            "COMPLETE_GAP_FREE_ORDERED_AGGREGATE_OF_ATOMIC_REFERENCE_BLIND_NUMERIC_"
            "SHARDS_NO_MAPPING_OR_ACCOUNTING_OR_PHYSICAL_ATTEMPT_HISTORY_AUTHORITY"
        ),
        "experiment_id": EXPERIMENT_ID,
        "format_version": AGGREGATE_FORMAT_VERSION,
        "git_binding": canonical_clone_v1(context["git"]),
        "input": {
            "archive_id": projection["archive_id"],
            "batch_id": projection["batch_id"],
            "configuration_ref": canonical_clone_v1(context["config_ref"]),
            "model": canonical_clone_v1(context["model"]),
            "plan_id": projection["plan_id"],
        },
        "metrics": {
            "empty_prediction_count": empty_prediction_count,
            "sample_count": projection["sample_count"],
            "shard_count": _shard_count(projection["sample_count"]),
        },
        "shard_axis_sha256": shard_axis_sha256,
        "state": "COMPLETE_ORDERED_PPOCRV6_NUMERIC_SHARD_AGGREGATE",
    }


def aggregate_authenticated_family_first_ppocrv6_numeric_v2(
    project_root: Path,
    archive_capability: archive_v1.AuthenticatedFamilyFirstSemanticLabelArchiveV1,
    *,
    model_cache: Path,
) -> dict[str, Any]:
    """Publish one aggregate only after all official shards replay exactly."""

    root = runtime_v3._resolve_root(project_root)
    if not isinstance(model_cache, Path):
        raise _error("numeric V2 model cache must be one pathlib Path")
    if os.path.lexists(root / AGGREGATE_ROOT):
        raise _error("fixed numeric V2 aggregate already exists")
    context = _context(root, archive_capability, model_cache, open_reader=False)
    total = _shard_count(context["projection"]["sample_count"])
    cache_fd, shards_fd = _cache_fds(root)
    stage_name = f".aggregate-stage-{secrets.token_hex(8)}"
    stage_fd = -1
    stage_identity: tuple[int, int] | None = None
    proposal_fd = -1
    try:
        os.mkdir(stage_name, 0o700, dir_fd=cache_fd)
        stage_fd = os.open(
            stage_name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=cache_fd
        )
        stage_stat = os.fstat(stage_fd)
        stage_identity = (stage_stat.st_dev, stage_stat.st_ino)
        proposal_fd = os.open(
            _PROPOSAL_NAME,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o400,
            dir_fd=stage_fd,
        )
        proposal_digest = hashlib.sha256()
        proposal_size = 0
        empty_count = 0
        global_count = 0
        shard_axis = hashlib.sha256()
        shard_refs: list[dict[str, Any]] = []
        for ordinal in range(1, total + 1):
            manifest, manifest_payload, proposal_payload = _validate_shard(root, context, ordinal)
            shard_path = SHARDS_ROOT / _shard_name(ordinal) / _SHARD_MANIFEST_NAME
            manifest_ref = _ref(manifest_payload, shard_path)
            shard_refs.append(manifest_ref)
            shard_axis.update(canonical_json_bytes_v1(manifest_ref))
            file_ops_v1._write_all(proposal_fd, proposal_payload)
            proposal_digest.update(proposal_payload)
            proposal_size += len(proposal_payload)
            empty_count += manifest["metrics"]["empty_prediction_count"]
            global_count += manifest["sample_count"]
        if global_count != context["projection"]["sample_count"]:
            raise _error("numeric shard aggregate denominator drifted")
        os.fsync(proposal_fd)
        proposal_path = AGGREGATE_ROOT / _PROPOSAL_NAME
        proposal_ref = {
            "path": proposal_path.as_posix(),
            "sha256": proposal_digest.hexdigest(),
            "size_bytes": proposal_size,
        }
        material = _aggregate_material(
            context=context,
            proposal_ref=proposal_ref,
            shard_manifest_refs=shard_refs,
            shard_axis_sha256=shard_axis.hexdigest(),
            empty_prediction_count=empty_count,
        )
        aggregate = {
            **material,
            "aggregate_id": "ffpnav2:aggregate:" + canonical_json_sha256_v1(material),
        }
        file_ops_v1._write_exclusive(
            stage_fd, _AGGREGATE_MANIFEST_NAME, canonical_json_bytes_v1(aggregate)
        )
        os.fsync(stage_fd)
        if sorted(os.listdir(stage_fd)) != sorted([_PROPOSAL_NAME, _AGGREGATE_MANIFEST_NAME]):
            raise _error("numeric aggregate stage listing drifted")
        _assert_context(root, context)
        os.close(proposal_fd)
        proposal_fd = -1
        os.close(stage_fd)
        stage_fd = -1
        file_ops_v1._rename_noreplace_fd(cache_fd, stage_name, AGGREGATE_ROOT.name)
        named = os.stat(AGGREGATE_ROOT.name, dir_fd=cache_fd, follow_symlinks=False)
        if stage_identity is None or (named.st_dev, named.st_ino) != stage_identity:
            raise _error("published numeric aggregate inode differs from its completed stage")
        stage_name = ""
        _assert_context(root, context)
        return aggregate
    finally:
        if proposal_fd >= 0:
            os.close(proposal_fd)
        if stage_fd >= 0:
            os.close(stage_fd)
        if stage_name and stage_identity is not None:
            try:
                named = os.stat(stage_name, dir_fd=cache_fd, follow_symlinks=False)
                if (named.st_dev, named.st_ino) == stage_identity:
                    descriptor = os.open(
                        stage_name,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                        dir_fd=cache_fd,
                    )
                    try:
                        for leaf in (_PROPOSAL_NAME, _AGGREGATE_MANIFEST_NAME):
                            try:
                                os.unlink(leaf, dir_fd=descriptor)
                            except FileNotFoundError:
                                pass
                    finally:
                        os.close(descriptor)
                    os.rmdir(stage_name, dir_fd=cache_fd)
            except FileNotFoundError:
                pass
        os.close(shards_fd)
        os.close(cache_fd)


def validate_authenticated_family_first_ppocrv6_numeric_aggregate_v2(
    project_root: Path,
    archive_capability: archive_v1.AuthenticatedFamilyFirstSemanticLabelArchiveV1,
    *,
    model_cache: Path,
) -> tuple[dict[str, Any], bytes, bytes, tuple[tuple[int, int], ...]]:
    """Replay all shard manifests and the complete aggregate proposal axis."""

    root = runtime_v3._resolve_root(project_root)
    if _directory_listing(root, AGGREGATE_ROOT, "numeric aggregate") != sorted(
        [_PROPOSAL_NAME, _AGGREGATE_MANIFEST_NAME]
    ):
        raise _error("numeric aggregate directory listing drifted")
    proposal_payload = _root_bytes(root, AGGREGATE_ROOT / _PROPOSAL_NAME, "numeric aggregate")
    manifest_payload = _root_bytes(
        root, AGGREGATE_ROOT / _AGGREGATE_MANIFEST_NAME, "numeric aggregate manifest"
    )
    aggregate = _canonical_object(manifest_payload, "numeric aggregate manifest")
    context = _context(
        root,
        archive_capability,
        model_cache,
        open_reader=False,
        pinned_git=aggregate.get("git_binding"),
    )
    total = _shard_count(context["projection"]["sample_count"])
    shard_refs = []
    shard_axis = hashlib.sha256()
    empty_count = 0
    for ordinal in range(1, total + 1):
        manifest, raw, _proposals = _validate_shard(root, context, ordinal)
        reference = _ref(raw, SHARDS_ROOT / _shard_name(ordinal) / _SHARD_MANIFEST_NAME)
        shard_refs.append(reference)
        shard_axis.update(canonical_json_bytes_v1(reference))
        empty_count += manifest["metrics"]["empty_prediction_count"]
    expected_proposal_ref = _ref(proposal_payload, AGGREGATE_ROOT / _PROPOSAL_NAME)
    expected_material = _aggregate_material(
        context=context,
        proposal_ref=expected_proposal_ref,
        shard_manifest_refs=shard_refs,
        shard_axis_sha256=shard_axis.hexdigest(),
        empty_prediction_count=empty_count,
    )
    expected = {
        **expected_material,
        "aggregate_id": "ffpnav2:aggregate:" + canonical_json_sha256_v1(expected_material),
    }
    if not same_typed_json_v1(aggregate, expected):
        raise _error("numeric aggregate does not replay from its complete shard axis")
    offsets: list[tuple[int, int]] = []
    empty_observed = 0
    for start, stop, proposal in _proposal_iterator(
        proposal_payload,
        first_sample_ordinal=1,
        expected_count=context["projection"]["sample_count"],
    ):
        sample = context["batch"]["samples"][len(offsets)]
        if (
            proposal["sample_id"] != sample["sample_id"]
            or proposal["crop_sha256"] != sample["crop_ref"]["sha256"]
        ):
            raise _error("numeric aggregate proposal/crop axis cross-link drifted")
        empty_observed += proposal["raw_prediction"] == ""
        offsets.append((start, stop))
    if empty_observed != empty_count:
        raise _error("numeric aggregate empty-output denominator drifted")
    _assert_context(root, context)
    return aggregate, manifest_payload, proposal_payload, tuple(offsets)
