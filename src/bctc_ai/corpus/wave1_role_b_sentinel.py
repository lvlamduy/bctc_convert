from __future__ import annotations

import fcntl
import importlib.metadata
import json
import os
import re
import secrets
import stat
import subprocess
import time
from collections import Counter, defaultdict
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from math import isfinite
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO

import fitz
import yaml

from bctc_ai.core.hashing import sha256_bytes
from bctc_ai.corpus import wave1_role_b_page_reader as page_plan
from bctc_ai.ocr.ppocrv6_page_session import (
    model_neutral_page_result,
    validate_ppocrv6_payload,
)
from bctc_ai.rendering.page_reader import render_composited_displayed_page


class WaveOneRoleBSentinelError(RuntimeError):
    """The authenticated Wave-1 OCR sentinel cannot proceed fail-closed."""


POLICY_RELATIVE_PATH = Path("config/corpus/bank-corpus-wave-1-role-b-sentinel-v1.yaml")
SEALED_PLAN_RELATIVE_PATH = Path(
    "output/development/bank-corpus-wave-1-role-b-page-reader-v1/wave-1-role-b-page-read-plan.json"
)
OUTPUT_RELATIVE_ROOT = Path(
    "output/development/bank-corpus-wave-1-role-b-page-reader-v1/sentinel-v1"
)
SEALED_PLAN_SHA256 = "d056323fde832ec2865ef5ac28a3fb045537ef6ecf3c505a7b5b0bbb68ad29c3"
SEALED_PLAN_SIZE_BYTES = 3_587_505
PRODUCER_GIT_COMMIT = "da848666ef6a9492be990063d13348780467e4bd"
EXECUTION_PLAN_SHA256 = "8598c3132d5f9bbaadcac0545b79c6b38bf0d49b519ed4d2eb71f2b2bec21cab"
SENTINEL_SHA256 = "d9e1d359e19117af957c395604c11430fea5d1da25b5eecaf6a8e11c687e0a89"
SELECTION_RECEIPT_SHA256 = "832cea1bee22f0bb08c422490dd2afe4e23bc91c56cdee6db382b1bfdc744d28"

MILESTONE_B_IMPLEMENTATION_RELATIVE_PATHS = (
    POLICY_RELATIVE_PATH,
    Path("src/bctc_ai/__init__.py"),
    Path("src/bctc_ai/core/__init__.py"),
    Path("src/bctc_ai/core/coordinates.py"),
    Path("src/bctc_ai/core/hashing.py"),
    Path("src/bctc_ai/corpus/__init__.py"),
    Path("src/bctc_ai/corpus/wave1_pre_ocr_structure.py"),
    Path("src/bctc_ai/corpus/wave1_role_b_page_reader.py"),
    Path("src/bctc_ai/corpus/wave1_role_b_sentinel.py"),
    Path("src/bctc_ai/ocr/__init__.py"),
    Path("src/bctc_ai/ocr/ppocrv6_page_session.py"),
    Path("src/bctc_ai/rendering/__init__.py"),
    Path("src/bctc_ai/rendering/page_reader.py"),
    Path("scripts/models/run_ppocrv6_sentinel_worker.py"),
    Path("scripts/corpus/run_wave1_role_b_sentinel.py"),
)
_SHA256 = frozenset("0123456789abcdef")
_PRODUCTION_STATUS = "COMPLETE_AUTHENTICATED_WAVE_1_24_PAGE_OCR_SENTINEL"


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _canonical_sha256(value: Any) -> str:
    return sha256_bytes(_canonical_bytes(value))


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _SHA256


def _project_path(project_root: Path, relative: str | Path, label: str) -> Path:
    value = relative.as_posix() if isinstance(relative, Path) else relative
    pure = PurePosixPath(value)
    if not value or pure.is_absolute() or ".." in pure.parts or pure.as_posix() != value:
        raise WaveOneRoleBSentinelError(f"{label} is not a canonical project path")
    lexical = project_root / Path(*pure.parts)
    current = project_root
    for part in pure.parts:
        current /= part
        try:
            identity = current.stat(follow_symlinks=False)
        except FileNotFoundError:
            break
        if stat.S_ISLNK(identity.st_mode):
            raise WaveOneRoleBSentinelError(f"{label} traverses a symlink")
    if lexical.absolute() != lexical or not lexical.is_relative_to(project_root):
        raise WaveOneRoleBSentinelError(f"{label} escapes the project root")
    return lexical


def _stable_bytes(path: Path, label: str) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise WaveOneRoleBSentinelError(f"{label} cannot be opened without links") from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise WaveOneRoleBSentinelError(f"{label} is not a regular file")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        payload = b"".join(chunks)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    before_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if before_identity != after_identity or len(payload) != before.st_size:
        raise WaveOneRoleBSentinelError(f"{label} changed while being read")
    named = path.stat(follow_symlinks=False)
    if stat.S_ISLNK(named.st_mode) or (named.st_dev, named.st_ino, named.st_size) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
    ):
        raise WaveOneRoleBSentinelError(f"{label} name changed while being read")
    return payload


def _load_policy(project_root: Path) -> dict[str, Any]:
    path = _project_path(project_root, POLICY_RELATIVE_PATH, "sentinel policy")
    try:
        policy = yaml.safe_load(_stable_bytes(path, "sentinel policy"))
    except yaml.YAMLError as error:
        raise WaveOneRoleBSentinelError("sentinel policy is invalid YAML") from error
    expected = {
        "version": 1,
        "policy": "BANK_CORPUS_WAVE_1_ROLE_B_SENTINEL_EXECUTOR_V1",
        "claim_boundary": "EXACT_24_PAGE_OCR_SENTINEL_SOURCE_TEXT_AND_GEOMETRY_ONLY",
    }
    if (
        not isinstance(policy, dict)
        or set(policy)
        != {
            *expected,
            "sealed_plan",
            "sharding",
            "worker",
            "execution",
            "safety",
            "expected",
            "output",
        }
        or any(policy.get(key) != value for key, value in expected.items())
    ):
        raise WaveOneRoleBSentinelError("sentinel policy identity or root fields drifted")
    exact_sections = {
        "sealed_plan": {
            "path": SEALED_PLAN_RELATIVE_PATH.as_posix(),
            "sha256": SEALED_PLAN_SHA256,
            "size_bytes": SEALED_PLAN_SIZE_BYTES,
            "producer_git_commit": PRODUCER_GIT_COMMIT,
            "execution_plan_sha256": EXECUTION_PLAN_SHA256,
            "sentinel_sha256": SENTINEL_SHA256,
            "selection_receipt_sha256": SELECTION_RECEIPT_SHA256,
        },
        "sharding": {
            "shard_count": 2,
            "algorithm": "LPT_DOCUMENT_REQUEST_COUNT_THEN_DOCUMENT_ID_V1",
            "document_sort": "REQUEST_COUNT_DESC_DOCUMENT_ID_ASC",
            "assignment": "MIN_REQUEST_LOAD_THEN_SHARD_ID_ASC",
            "document_split_allowed": False,
            "bank_identity_used": False,
            "filename_used": False,
        },
        "worker": {
            "interpreter": ".gpu-venv/bin/python",
            "script": "scripts/models/run_ppocrv6_sentinel_worker.py",
            "process_count_initial_run": 2,
            "max_process_count": 2,
            "cpu_threads_per_process": 6,
            "one_long_lived_session_per_active_shard": True,
            "supervisor_crash_policy": "INHERITED_GLOBAL_FLOCK_EXECUTION_LEASE_V1",
            "global_execution_lease_filename": "sentinel-execution.lease",
            "orphan_worker_reconciliation": ("BLOCK_NEW_SUPERVISOR_UNTIL_INHERITED_LEASE_RELEASE"),
            "environment_scope": "PER_SHARD_PRIVATE_RUNTIME_ROOT",
            "protocol": "EXCLUSIVE_CANONICAL_JSON_RESPONSE_FILES_V1",
            "network_policy": "PYTHON_AUDIT_SOCKET_CONNECT_DENIED",
            "environment": {
                "PADDLE_PDX_CACHE_HOME": ".paddlex-cache",
                "PADDLE_PDX_MODEL_SOURCE": "huggingface",
                "PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK": "True",
                "FLAGS_allocator_strategy": "auto_growth",
                "OMP_NUM_THREADS": "6",
                "PYTHONHASHSEED": "0",
                "PYTHONNOUSERSITE": "1",
            },
            "isolated_runtime_directories": {
                "HOME": "home",
                "XDG_CACHE_HOME": "xdg-cache",
                "XDG_CONFIG_HOME": "xdg-config",
                "XDG_DATA_HOME": "xdg-data",
                "TMPDIR": "tmp",
            },
            "supervisor_environment": {
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
                "PYTHONUTF8": "1",
                "PYTHONCOERCECLOCALE": "0",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONSAFEPATH": "1",
                "PATH": ".gpu-venv/bin:/usr/bin:/bin",
            },
        },
        "execution": {
            "parent_renders_pages": True,
            "render_contract_source": "SEALED_PLAN_REQUEST",
            "request_scope": "EXACT_SEALED_SENTINEL_ONLY",
            "per_document_locking": "FLOCK_EXCLUSIVE_NOFOLLOW",
            "checkpoint": "IMMUTABLE_CANONICAL_GENERATION_AFTER_EVERY_PAGE",
            "orphan_adoption": "FULL_REQUEST_IDENTITY_ONLY",
            "completed_resume_inference_count": 0,
            "minimum_free_space_bytes": 53_687_091_200,
            "timestamps_in_deterministic_evidence_allowed": False,
            "timing_log": "SEPARATE_NON_IDENTITY_OBSERVATIONAL_JSONL",
            "overwrite_allowed": False,
        },
        "safety": {
            "production_authentication_bypass_allowed": False,
            "injectable_production_worker_allowed": False,
            "test_output_can_publish_production_status": False,
            "bank_registry_metadata_allowed_in_execution_decisions": False,
            "filename_metadata_allowed_in_execution_decisions": False,
            "role_a_inputs_allowed": False,
            "schema_inputs_allowed": False,
            "mapping_inputs_allowed": False,
            "historical_values_allowed": False,
            "source_visible_text_preserved_verbatim": True,
            "semantic_interpretation_allowed": False,
            "absence_declarations_allowed": False,
        },
        "expected": {
            "document_count": 14,
            "request_count": 24,
            "shard_count": 2,
            "requests_per_shard": [12, 12],
            "documents_per_shard": [7, 7],
        },
        "output": {
            "root": OUTPUT_RELATIVE_ROOT.as_posix(),
            "control_filename": "sentinel-execution-control.json",
            "object_directory": "objects",
            "checkpoint_directory": "checkpoints",
            "lock_directory": "locks",
            "runtime_directory": "runtime",
            "aggregate_filename": "sentinel-aggregate.json",
            "canonical_json": True,
            "exclusive_no_overwrite": True,
        },
    }
    if any(policy.get(section) != value for section, value in exact_sections.items()):
        raise WaveOneRoleBSentinelError("sentinel policy fields drifted")
    return policy


def _git_identity(project_root: Path, *, require_clean: bool) -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if require_clean and status.strip():
        raise WaveOneRoleBSentinelError("production sentinel requires a clean Git worktree")
    return {"commit": commit, "dirty": bool(status.strip())}


def _git_blob(project_root: Path, commit: str, relative: Path) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative.as_posix()}"],
        cwd=project_root,
        check=False,
        capture_output=True,
    )
    if result.returncode:
        raise WaveOneRoleBSentinelError(
            f"committed implementation is absent: {relative.as_posix()}"
        )
    return result.stdout


def _implementation_ledger(
    project_root: Path,
    commit: str,
    paths: tuple[Path, ...],
) -> dict[str, Any]:
    records = []
    for relative in sorted(set(paths), key=lambda item: item.as_posix()):
        path = _project_path(project_root, relative, "implementation")
        payload = _stable_bytes(path, f"implementation {relative.as_posix()}")
        if _git_blob(project_root, commit, relative) != payload:
            raise WaveOneRoleBSentinelError(
                f"implementation bytes differ from Git: {relative.as_posix()}"
            )
        records.append(
            {
                "phase": "READ",
                "kind": "IMPLEMENTATION",
                "path": relative.as_posix(),
                "sha256": sha256_bytes(payload),
                "size_bytes": len(payload),
            }
        )
    return {"records": records, "sha256": _canonical_sha256(records)}


def _require_producer_ancestor(project_root: Path, current_commit: str) -> None:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", PRODUCER_GIT_COMMIT, current_commit],
        cwd=project_root,
        check=False,
    )
    if result.returncode:
        raise WaveOneRoleBSentinelError("sealed-plan producer is not an ancestor of executor code")


def _reconstruct_sealed_a_plan(project_root: Path, model_cache: Path) -> dict[str, Any]:
    """Rebuild every sealed-plan byte without trusting its embedded identity fields."""

    a_policy = page_plan.load_wave_one_role_b_page_reader_policy(
        project_root / page_plan.POLICY_RELATIVE_PATH,
        project_root,
    )
    rebuilt = page_plan.build_wave_one_role_b_route_plan(
        project_root,
        project_root / page_plan.POLICY_RELATIVE_PATH,
    )
    implementation = page_plan.build_implementation_ledger(project_root, PRODUCER_GIT_COMMIT)
    runtime = page_plan.build_runtime_model_ledger(project_root, a_policy, model_cache)
    render = {
        "provider": "PYMUPDF_FULL_COMPOSITED_DISPLAYED_PAGE_RGB_V1",
        "pymupdf_distribution_version": importlib.metadata.version("pymupdf"),
        "pymupdf_binding_version": fitz.VersionBind,
        "pymupdf_runtime_versions": list(fitz.version),
        "render_contract": a_policy["render"],
        "implementation_ledger_sha256": implementation["sha256"],
    }
    render["sha256"] = _canonical_sha256(render)
    native_records = []
    for key in ("policy_path", "quality_policy_path"):
        relative = a_policy["readers"]["causal_native"][key]
        payload = _stable_bytes(
            _project_path(project_root, relative, "causal native configuration"),
            "causal native configuration",
        )
        native_records.append(
            {"path": relative, "sha256": sha256_bytes(payload), "size_bytes": len(payload)}
        )
    native = {
        "provider": "PYMUPDF_CAUSAL_NATIVE_TEXT_VISIBILITY_V1",
        "pymupdf_distribution_version": importlib.metadata.version("pymupdf"),
        "pymupdf_binding_version": fitz.VersionBind,
        "pymupdf_runtime_versions": list(fitz.version),
        "config_records": native_records,
        "ocr_fallback_allowed": False,
    }
    native["sha256"] = _canonical_sha256(native)
    for document in rebuilt["documents"]:
        request_hashes = []
        for page in document["pages"]:
            provider = (
                runtime["sha256"]
                if page["route"] == "DOMINANT_RASTER_OCR"
                else native["sha256"]
                if page["route"] == "CAUSAL_NATIVE_TEXT"
                else None
            )
            request = {
                "format_version": "BANK_CORPUS_WAVE_1_PAGE_READ_REQUEST_V1",
                "selection_receipt_sha256": rebuilt["selection_receipt_sha256"],
                "route_plan_sha256": rebuilt["route_plan_sha256"],
                "sentinel_sha256": rebuilt["sentinel_sha256"],
                "input_ledger_sha256": rebuilt["input_ledger_sha256"],
                "source_sha256": document["sha256"],
                "source_size_bytes": document["size_bytes"],
                "physical_page": page["page"],
                "pre_ocr_feature_fingerprint_sha256": page["pre_ocr_feature_fingerprint_sha256"],
                "route": page["route"],
                "render_specification": (
                    {
                        "source": a_policy["render"]["source"],
                        "dpi": page["render_dpi"],
                        "colorspace": "RGB",
                        "alpha": False,
                        "annotations": "INCLUDED",
                    }
                    if page["route"] == "DOMINANT_RASTER_OCR"
                    else None
                ),
                "git_commit": PRODUCER_GIT_COMMIT,
                "implementation_ledger_sha256": implementation["sha256"],
                "provider_identity_sha256": provider,
                "render_runtime_identity_sha256": (
                    render["sha256"] if page["route"] == "DOMINANT_RASTER_OCR" else None
                ),
                "bank_identity_used": False,
                "filename_used": False,
                "role_a_used": False,
                "schema_used": False,
                "historical_values_used": False,
            }
            page["request"] = request
            page["request_sha256"] = _canonical_sha256(request)
            request_hashes.append(page["request_sha256"])
        document["request_set_sha256"] = _canonical_sha256(request_hashes)
    producer_git = {"commit": PRODUCER_GIT_COMMIT, "dirty": False}
    rebuilt.update(
        status="READY_FOR_ROLE_B_PAGE_READ_EXECUTION",
        git=producer_git,
        implementation_ledger=implementation,
        ppocrv6_runtime_model_ledger=runtime,
        render_runtime_ledger=render,
        causal_native_runtime_ledger=native,
    )
    projection = {
        "selection_receipt_sha256": rebuilt["selection_receipt_sha256"],
        "route_plan_sha256": rebuilt["route_plan_sha256"],
        "sentinel_sha256": rebuilt["sentinel_sha256"],
        "input_ledger_sha256": rebuilt["input_ledger_sha256"],
        "git": producer_git,
        "implementation_ledger_sha256": implementation["sha256"],
        "ppocrv6_runtime_model_ledger_sha256": runtime["sha256"],
        "render_runtime_ledger_sha256": render["sha256"],
        "causal_native_runtime_ledger_sha256": native["sha256"],
        "document_request_sets": [
            {
                "document_id": document["document_id"],
                "request_set_sha256": document["request_set_sha256"],
            }
            for document in rebuilt["documents"]
        ],
    }
    rebuilt["execution_plan_sha256"] = _canonical_sha256(projection)
    return rebuilt


def _authenticate_sealed_plan(
    project_root: Path,
    model_cache: Path,
    *,
    require_clean_executor: bool,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    project_root = project_root.resolve()
    policy = _load_policy(project_root)
    git_before = _git_identity(project_root, require_clean=require_clean_executor)
    _require_producer_ancestor(project_root, git_before["commit"])
    sealed_payload = _stable_bytes(
        _project_path(project_root, SEALED_PLAN_RELATIVE_PATH, "sealed plan"),
        "sealed plan",
    )
    if len(sealed_payload) != SEALED_PLAN_SIZE_BYTES or sha256_bytes(sealed_payload) != (
        SEALED_PLAN_SHA256
    ):
        raise WaveOneRoleBSentinelError("sealed Milestone-A plan byte identity drifted")
    rebuilt = _reconstruct_sealed_a_plan(project_root, model_cache)
    if _canonical_bytes(rebuilt) != sealed_payload:
        raise WaveOneRoleBSentinelError("sealed Milestone-A plan full-byte replay failed")
    try:
        sealed = json.loads(sealed_payload)
    except json.JSONDecodeError as error:  # pragma: no cover - hash anchor is fixed
        raise WaveOneRoleBSentinelError("sealed plan is invalid JSON") from error
    if not isinstance(sealed, dict) or any(
        sealed.get(key) != value
        for key, value in (
            ("execution_plan_sha256", EXECUTION_PLAN_SHA256),
            ("sentinel_sha256", SENTINEL_SHA256),
            ("selection_receipt_sha256", SELECTION_RECEIPT_SHA256),
        )
    ):
        raise WaveOneRoleBSentinelError("sealed plan independent anchors drifted")
    implementation = _implementation_ledger(
        project_root,
        git_before["commit"],
        MILESTONE_B_IMPLEMENTATION_RELATIVE_PATHS,
    )
    git_after = _git_identity(project_root, require_clean=require_clean_executor)
    if git_after != git_before:
        raise WaveOneRoleBSentinelError("executor Git identity changed during authentication")
    return sealed, policy, {"git": git_before, "implementation_ledger": implementation}


def _sentinel_request_records(sealed: dict[str, Any]) -> list[dict[str, Any]]:
    by_document = {document["document_id"]: document for document in sealed["documents"]}
    records = []
    seen: set[str] = set()
    for sentinel in sealed["sentinel"]:
        document_id = sentinel["document_id"]
        document = by_document.get(document_id)
        if document is None:
            raise WaveOneRoleBSentinelError("sentinel references an unknown document")
        matches = [page for page in document["pages"] if page["page"] == sentinel["page"]]
        if len(matches) != 1:
            raise WaveOneRoleBSentinelError("sentinel page is not unique in sealed plan")
        page = matches[0]
        if (
            page["route"] != "DOMINANT_RASTER_OCR"
            or sentinel["route"] != "DOMINANT_RASTER_OCR"
            or page["request_sha256"] in seen
            or _canonical_sha256(page["request"]) != page["request_sha256"]
        ):
            raise WaveOneRoleBSentinelError("sentinel request identity is invalid")
        seen.add(page["request_sha256"])
        records.append(
            {
                "sentinel_ordinal": sentinel["sentinel_ordinal"],
                "document_id": document_id,
                "source_sha256": document["sha256"],
                "source_size_bytes": document["size_bytes"],
                "physical_page": page["page"],
                "request_sha256": page["request_sha256"],
                "request": page["request"],
            }
        )
    records.sort(key=lambda item: item["sentinel_ordinal"])
    if [item["sentinel_ordinal"] for item in records] != list(range(1, 25)):
        raise WaveOneRoleBSentinelError("sentinel ordinals are not the exact sequence 1..24")
    return records


def _assign_two_shards(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["document_id"]].append(record)
    shards = [
        {"shard_id": 0, "document_ids": [], "requests": []},
        {"shard_id": 1, "document_ids": [], "requests": []},
    ]
    for document_id in sorted(grouped, key=lambda key: (-len(grouped[key]), key)):
        shard = min(shards, key=lambda item: (len(item["requests"]), item["shard_id"]))
        shard["document_ids"].append(document_id)
        shard["requests"].extend(
            sorted(grouped[document_id], key=lambda item: item["sentinel_ordinal"])
        )
    for shard in shards:
        shard["document_ids"].sort()
        shard["requests"].sort(key=lambda item: item["sentinel_ordinal"])
        shard["document_count"] = len(shard["document_ids"])
        shard["request_count"] = len(shard["requests"])
        shard["request_set_sha256"] = _canonical_sha256(
            [record["request_sha256"] for record in shard["requests"]]
        )
    if [(item["document_count"], item["request_count"]) for item in shards] != [
        (7, 12),
        (7, 12),
    ]:
        raise WaveOneRoleBSentinelError("deterministic sentinel sharding drifted")
    return shards


def build_authenticated_control(
    project_root: Path,
    *,
    model_cache: Path,
) -> dict[str, Any]:
    """Build the production control; authentication is unconditional and non-injectable."""

    sealed, policy, executor = _authenticate_sealed_plan(
        project_root,
        model_cache,
        require_clean_executor=True,
    )
    records = _sentinel_request_records(sealed)
    shards = _assign_two_shards(records)
    worker_contract = {
        "interpreter": policy["worker"]["interpreter"],
        "script": policy["worker"]["script"],
        "process_count_initial_run": 2,
        "max_process_count": 2,
        "cpu_threads_per_process": 6,
        "protocol": policy["worker"]["protocol"],
        "network_policy": policy["worker"]["network_policy"],
        "environment": policy["worker"]["environment"],
        "isolated_runtime_directories": policy["worker"]["isolated_runtime_directories"],
        "supervisor_environment": policy["worker"]["supervisor_environment"],
        "supervisor_crash_policy": policy["worker"]["supervisor_crash_policy"],
        "global_execution_lease_filename": policy["worker"]["global_execution_lease_filename"],
        "orphan_worker_reconciliation": policy["worker"]["orphan_worker_reconciliation"],
        "environment_scope": policy["worker"]["environment_scope"],
        "arbitrary_inherited_environment_allowed": False,
    }
    control = {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_OCR_SENTINEL_CONTROL_V1",
        "status": "READY_FOR_AUTHENTICATED_24_PAGE_OCR_SENTINEL_EXECUTION",
        "claim_boundary": policy["claim_boundary"],
        "sealed_plan": {
            "path": SEALED_PLAN_RELATIVE_PATH.as_posix(),
            "sha256": SEALED_PLAN_SHA256,
            "size_bytes": SEALED_PLAN_SIZE_BYTES,
            "producer_git_commit": PRODUCER_GIT_COMMIT,
            "execution_plan_sha256": EXECUTION_PLAN_SHA256,
            "sentinel_sha256": SENTINEL_SHA256,
        },
        "executor_git": executor["git"],
        "executor_implementation_ledger": executor["implementation_ledger"],
        "worker_contract": worker_contract,
        "sharding": {
            "algorithm": policy["sharding"]["algorithm"],
            "document_split_allowed": False,
            "bank_identity_used": False,
            "filename_used": False,
            "shards": shards,
        },
        "accounting": {
            "document_count": len({record["document_id"] for record in records}),
            "request_count": len(records),
            "shard_count": len(shards),
            "requests_per_shard": [item["request_count"] for item in shards],
            "documents_per_shard": [item["document_count"] for item in shards],
        },
        "safety": {
            "request_scope": "EXACT_SEALED_SENTINEL_ONLY",
            "source_locator_excluded_from_control": True,
            "bank_registry_metadata_used": False,
            "filename_metadata_used": False,
            "role_a_used": False,
            "schema_used": False,
            "mapping_used": False,
            "historical_values_used": False,
            "semantic_interpretation_attempted": False,
            "absence_claimed": False,
            "source_visible_text_preserved_verbatim": True,
        },
    }
    control["control_identity_sha256"] = _canonical_sha256(control)
    return control


@contextmanager
def _held_directory(
    project_root: Path,
    relative: Path,
    *,
    create: bool,
) -> Iterator[tuple[Path, int]]:
    """Hold every directory component open and never follow a link."""

    project_root = project_root.resolve()
    pure = PurePosixPath(relative.as_posix())
    if pure.is_absolute() or ".." in pure.parts:
        raise WaveOneRoleBSentinelError("output hierarchy is not project-relative")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptors: list[int] = []
    identities: list[tuple[Path, tuple[int, int]]] = []
    current = project_root
    try:
        root_fd = os.open(project_root, flags)
        descriptors.append(root_fd)
        root_stat = os.fstat(root_fd)
        identities.append((project_root, (root_stat.st_dev, root_stat.st_ino)))
        for part in pure.parts:
            current /= part
            try:
                descriptor = os.open(part, flags, dir_fd=descriptors[-1])
            except FileNotFoundError:
                if not create:
                    raise WaveOneRoleBSentinelError(
                        f"required output directory is absent: {relative.as_posix()}"
                    ) from None
                try:
                    os.mkdir(part, 0o755, dir_fd=descriptors[-1])
                    os.fsync(descriptors[-1])
                except FileExistsError:
                    pass
                descriptor = os.open(part, flags, dir_fd=descriptors[-1])
            except OSError as error:
                raise WaveOneRoleBSentinelError(
                    f"output hierarchy cannot be opened without links: {current}"
                ) from error
            identity = os.fstat(descriptor)
            if not stat.S_ISDIR(identity.st_mode):
                os.close(descriptor)
                raise WaveOneRoleBSentinelError("output hierarchy contains a non-directory")
            descriptors.append(descriptor)
            identities.append((current, (identity.st_dev, identity.st_ino)))
        yield project_root / relative, descriptors[-1]
        for path, expected in identities:
            observed = path.stat(follow_symlinks=False)
            if stat.S_ISLNK(observed.st_mode) or (observed.st_dev, observed.st_ino) != expected:
                raise WaveOneRoleBSentinelError("output hierarchy changed while held")
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _hash_open_at(directory_fd: int, name: str) -> tuple[bytes, os.stat_result]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(name, flags, dir_fd=directory_fd)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise WaveOneRoleBSentinelError("published evidence name is not a regular file")
        chunks = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        payload = b"".join(chunks)
        after = os.fstat(descriptor)
        named = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        expected = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        if expected != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) or (
            named.st_dev,
            named.st_ino,
            named.st_size,
        ) != (after.st_dev, after.st_ino, after.st_size):
            raise WaveOneRoleBSentinelError("published evidence changed while being read")
        return payload, after
    finally:
        os.close(descriptor)


def _recover_owned_hardlink_temporaries(directory_fd: int) -> set[str]:
    """Recover only exact temp names hard-linked to their immutable final inode."""

    grammar = re.compile(r"^\.(?P<final>.+\.(?:json|png))\.[0-9a-f]{32}\.tmp$")
    standalone: set[str] = set()
    changed = False
    for name in sorted(os.listdir(directory_fd)):
        match = grammar.fullmatch(name)
        if match is None:
            continue
        temporary = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if not stat.S_ISREG(temporary.st_mode) or stat.S_IMODE(temporary.st_mode) not in {
            0o600,
            0o444,
        }:
            raise WaveOneRoleBSentinelError("publication temporary cannot be recovered safely")
        try:
            final = os.stat(match.group("final"), dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            final = None
        if final is not None and (temporary.st_dev, temporary.st_ino) == (
            final.st_dev,
            final.st_ino,
        ):
            if (
                stat.S_IMODE(temporary.st_mode) != 0o444
                or stat.S_IMODE(final.st_mode) != 0o444
                or temporary.st_nlink != 2
                or final.st_nlink != 2
                or temporary.st_size != final.st_size
            ):
                raise WaveOneRoleBSentinelError("linked publication temporary identity drifted")
            os.unlink(name, dir_fd=directory_fd)
            changed = True
        elif temporary.st_nlink != 1:
            raise WaveOneRoleBSentinelError("unexplained publication temporary hardlink exists")
        else:
            standalone.add(name)
    if changed:
        os.fsync(directory_fd)
    return standalone


def _publish_exclusive(
    project_root: Path,
    directory_relative: Path,
    filename: str,
    payload: bytes,
) -> Path:
    if not filename or "/" in filename or "\\" in filename or filename in {".", ".."}:
        raise WaveOneRoleBSentinelError("exclusive evidence filename is invalid")
    with _held_directory(project_root, directory_relative, create=True) as (directory, dir_fd):
        _recover_owned_hardlink_temporaries(dir_fd)
        try:
            existing_payload, existing = _hash_open_at(dir_fd, filename)
        except FileNotFoundError:
            existing_payload = None
            existing = None
        if existing_payload is not None:
            if (
                existing_payload != payload
                or stat.S_IMODE(existing.st_mode) != 0o444
                or existing.st_nlink != 1
            ):
                raise WaveOneRoleBSentinelError("existing evidence conflicts with exact bytes")
            return directory / filename
        temporary_name = f".{filename}.{secrets.token_hex(16)}.tmp"
        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        descriptor = -1
        owned_identity: tuple[int, int] | None = None
        try:
            descriptor = os.open(temporary_name, flags, 0o600, dir_fd=dir_fd)
            owned = os.fstat(descriptor)
            owned_identity = (owned.st_dev, owned.st_ino)
            offset = 0
            while offset < len(payload):
                offset += os.write(descriptor, payload[offset:])
            os.fsync(descriptor)
            os.fchmod(descriptor, 0o444)
            os.fsync(descriptor)
            exact = os.fstat(descriptor)
            try:
                os.link(
                    temporary_name,
                    filename,
                    src_dir_fd=dir_fd,
                    dst_dir_fd=dir_fd,
                    follow_symlinks=False,
                )
            except FileExistsError:
                pass
            published, published_stat = _hash_open_at(dir_fd, filename)
            if (
                published != payload
                or stat.S_IMODE(published_stat.st_mode) != 0o444
                or published_stat.st_nlink != 2
                or (published_stat.st_dev, published_stat.st_ino, published_stat.st_size)
                != (exact.st_dev, exact.st_ino, len(payload))
            ):
                raise WaveOneRoleBSentinelError("exclusive evidence publication conflicted")
            os.fsync(dir_fd)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            if owned_identity is not None:
                try:
                    observed = os.stat(temporary_name, dir_fd=dir_fd, follow_symlinks=False)
                except FileNotFoundError:
                    observed = None
                if observed is not None and (observed.st_dev, observed.st_ino) == owned_identity:
                    os.unlink(temporary_name, dir_fd=dir_fd)
                    os.fsync(dir_fd)
        final_payload, final_identity = _hash_open_at(dir_fd, filename)
        if (
            final_payload != payload
            or stat.S_IMODE(final_identity.st_mode) != 0o444
            or final_identity.st_nlink != 1
        ):
            raise WaveOneRoleBSentinelError("exclusive evidence final link identity drifted")
        return directory / filename


def publish_authenticated_control(
    project_root: Path,
    *,
    model_cache: Path,
) -> dict[str, Any]:
    control = build_authenticated_control(project_root, model_cache=model_cache)
    _ensure_capacity(project_root.resolve(), 53_687_091_200)
    _publish_exclusive(
        project_root.resolve(),
        OUTPUT_RELATIVE_ROOT,
        "sentinel-execution-control.json",
        _canonical_bytes(control),
    )
    return control


def _object_ref(output_root: Path, object_path: Path, digest: str, size: int) -> dict[str, Any]:
    relative = object_path.relative_to(output_root).as_posix()
    return {"path": relative, "sha256": digest, "size_bytes": size}


def _put_object(
    project_root: Path,
    payload: bytes,
    *,
    suffix: str,
) -> dict[str, Any]:
    if suffix not in {".json", ".png"}:
        raise WaveOneRoleBSentinelError("sentinel object suffix is not allowed")
    digest = sha256_bytes(payload)
    relative_directory = OUTPUT_RELATIVE_ROOT / "objects" / "sha256" / digest[:2]
    filename = f"{digest}{suffix}"
    with _held_directory(project_root, relative_directory, create=True) as (
        directory,
        directory_fd,
    ):
        _recover_owned_hardlink_temporaries(directory_fd)
        try:
            existing_payload, existing = _hash_open_at(directory_fd, filename)
        except FileNotFoundError:
            existing_payload = None
            existing = None
        if existing_payload is not None:
            if (
                existing_payload != payload
                or stat.S_IMODE(existing.st_mode) != 0o444
                or existing.st_nlink != 1
                or sha256_bytes(existing_payload) != digest
            ):
                raise WaveOneRoleBSentinelError("existing immutable object conflicts")
        else:
            temporary = f".{filename}.{secrets.token_hex(16)}.tmp"
            flags = (
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0)
            )
            descriptor = -1
            owned_identity: tuple[int, int] | None = None
            try:
                descriptor = os.open(temporary, flags, 0o600, dir_fd=directory_fd)
                identity = os.fstat(descriptor)
                owned_identity = (identity.st_dev, identity.st_ino)
                offset = 0
                while offset < len(payload):
                    offset += os.write(descriptor, payload[offset:])
                os.fsync(descriptor)
                os.fchmod(descriptor, 0o444)
                os.fsync(descriptor)
                owned = os.fstat(descriptor)
                try:
                    os.link(
                        temporary,
                        filename,
                        src_dir_fd=directory_fd,
                        dst_dir_fd=directory_fd,
                        follow_symlinks=False,
                    )
                except FileExistsError:
                    pass
                published, published_identity = _hash_open_at(directory_fd, filename)
                if (
                    published != payload
                    or stat.S_IMODE(published_identity.st_mode) != 0o444
                    or published_identity.st_nlink != 2
                    or (
                        published_identity.st_dev,
                        published_identity.st_ino,
                        published_identity.st_size,
                    )
                    != (owned.st_dev, owned.st_ino, len(payload))
                ):
                    raise WaveOneRoleBSentinelError("immutable object publication conflicted")
                os.fsync(directory_fd)
            finally:
                if descriptor >= 0:
                    os.close(descriptor)
                if owned_identity is not None:
                    try:
                        observed = os.stat(temporary, dir_fd=directory_fd, follow_symlinks=False)
                    except FileNotFoundError:
                        observed = None
                    if (
                        observed is not None
                        and (
                            observed.st_dev,
                            observed.st_ino,
                        )
                        == owned_identity
                    ):
                        os.unlink(temporary, dir_fd=directory_fd)
                        os.fsync(directory_fd)
        final_payload, final_identity = _hash_open_at(directory_fd, filename)
        if (
            final_payload != payload
            or stat.S_IMODE(final_identity.st_mode) != 0o444
            or final_identity.st_nlink != 1
        ):
            raise WaveOneRoleBSentinelError("immutable object final link identity drifted")
        object_path = directory / filename
        return _object_ref(project_root / OUTPUT_RELATIVE_ROOT, object_path, digest, len(payload))


def _read_object(project_root: Path, reference: dict[str, Any], suffix: str) -> bytes:
    if not isinstance(reference, dict) or set(reference) != {"path", "sha256", "size_bytes"}:
        raise WaveOneRoleBSentinelError("object reference fields drifted")
    digest = reference.get("sha256")
    size = reference.get("size_bytes")
    expected_path = f"objects/sha256/{str(digest)[:2]}/{digest}{suffix}"
    if (
        not _is_sha256(digest)
        or isinstance(size, bool)
        or not isinstance(size, int)
        or size < 0
        or reference.get("path") != expected_path
    ):
        raise WaveOneRoleBSentinelError("object reference identity is malformed")
    relative_directory = OUTPUT_RELATIVE_ROOT / "objects" / "sha256" / digest[:2]
    with _held_directory(project_root, relative_directory, create=False) as (
        _directory,
        directory_fd,
    ):
        payload, identity = _hash_open_at(directory_fd, f"{digest}{suffix}")
        if (
            len(payload) != size
            or sha256_bytes(payload) != digest
            or stat.S_IMODE(identity.st_mode) != 0o444
            or identity.st_nlink != 1
        ):
            raise WaveOneRoleBSentinelError("content-addressed evidence object drifted")
        return payload


def _json_object(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as error:
        raise WaveOneRoleBSentinelError(f"{label} is invalid JSON") from error
    if not isinstance(value, dict) or _canonical_bytes(value) != payload:
        raise WaveOneRoleBSentinelError(f"{label} is not a canonical JSON object")
    return value


def _control_index(control: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = [record for shard in control["sharding"]["shards"] for record in shard["requests"]]
    index = {record["request_sha256"]: record for record in records}
    if len(index) != 24:
        raise WaveOneRoleBSentinelError("control request set is not exactly 24 unique requests")
    return index


def _validate_result_record(
    project_root: Path,
    record: dict[str, Any],
    expected: dict[str, Any],
    render: dict[str, Any],
) -> None:
    required = {
        "sentinel_ordinal",
        "request_sha256",
        "status",
        "render_ref",
        "backend_payload_ref",
        "result_ref",
        "line_count",
        "word_token_count",
    }
    if not isinstance(record, dict) or set(record) != required:
        raise WaveOneRoleBSentinelError("checkpoint result record fields drifted")
    if (
        isinstance(record["line_count"], bool)
        or not isinstance(record["line_count"], int)
        or record["line_count"] < 0
        or isinstance(record["word_token_count"], bool)
        or not isinstance(record["word_token_count"], int)
        or record["word_token_count"] < 0
        or isinstance(record["sentinel_ordinal"], bool)
        or not isinstance(record["sentinel_ordinal"], int)
        or record["sentinel_ordinal"] < 1
        or record["sentinel_ordinal"] != expected["sentinel_ordinal"]
        or record["request_sha256"] != expected["request_sha256"]
        or record["status"] != "OCR_WORD_BOX_READ_COMPLETE"
    ):
        raise WaveOneRoleBSentinelError("checkpoint result request identity drifted")
    render_payload = _read_object(project_root, record["render_ref"], ".png")
    backend = _json_object(
        _read_object(project_root, record["backend_payload_ref"], ".json"),
        "backend payload evidence",
    )
    result = _json_object(
        _read_object(project_root, record["result_ref"], ".json"),
        "model-neutral result evidence",
    )
    if (
        set(backend)
        != {
            "format_version",
            "claim_boundary",
            "request_sha256",
            "request",
            "provider_identity_sha256",
            "render_ref",
            "payload",
        }
        or backend.get("format_version") != "BANK_CORPUS_WAVE_1_PPOCRV6_BACKEND_PAYLOAD_V1"
        or backend.get("claim_boundary")
        != "RAW_PINNED_PROVIDER_PAYLOAD_FOR_ONE_EXACT_PAGE_REQUEST_ONLY"
        or backend.get("request_sha256") != expected["request_sha256"]
        or _canonical_bytes(backend.get("request")) != _canonical_bytes(expected["request"])
        or backend.get("render_ref") != record["render_ref"]
        or backend.get("provider_identity_sha256")
        != expected["request"]["provider_identity_sha256"]
        or result.get("format_version") != "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V1"
        or result.get("claim_boundary") != "SOURCE_VISIBLE_PAGE_TEXT_AND_GEOMETRY_EVIDENCE_ONLY"
        or result.get("request_sha256") != expected["request_sha256"]
        or _canonical_bytes(result.get("request")) != _canonical_bytes(expected["request"])
        or result.get("source_sha256") != expected["source_sha256"]
        or isinstance(result.get("source_size_bytes"), bool)
        or not isinstance(result.get("source_size_bytes"), int)
        or result.get("source_size_bytes") != expected["source_size_bytes"]
        or isinstance(result.get("physical_page"), bool)
        or not isinstance(result.get("physical_page"), int)
        or result.get("physical_page") != expected["physical_page"]
        or result.get("route") != "DOMINANT_RASTER_OCR"
        or result.get("input_render_ref") != record["render_ref"]
        or result.get("backend_payload_ref") != record["backend_payload_ref"]
        or result.get("provider_identity_sha256") != expected["request"]["provider_identity_sha256"]
        or result.get("render_runtime_identity_sha256")
        != expected["request"]["render_runtime_identity_sha256"]
        or result.get("status") != "OCR_WORD_BOX_READ_COMPLETE"
        or result.get("metrics", {}).get("line_count") != record["line_count"]
        or result.get("metrics", {}).get("word_token_count") != record["word_token_count"]
        or result.get("source_blank_claimed") is not False
        or result.get("safety")
        != {
            "statement_classified": False,
            "table_classified": False,
            "rows_reconstructed": False,
            "cells_interpreted": False,
            "absence_claimed": False,
            "bank_registry_metadata_used": False,
            "filename_metadata_used": False,
            "role_a_used": False,
            "schema_used": False,
            "mapping_used": False,
            "historical_values_used": False,
        }
    ):
        raise WaveOneRoleBSentinelError("model-neutral result embedded identity drifted")
    if (
        sha256_bytes(render_payload) != record["render_ref"]["sha256"]
        or render_payload != render["payload"]
        or record["render_ref"] != render["ref"]
    ):
        raise WaveOneRoleBSentinelError("checkpoint render bytes drifted")
    dimensions = result.get("coordinate_authority", {}).get("pixel_dimensions")
    if not isinstance(dimensions, list) or len(dimensions) != 2:
        raise WaveOneRoleBSentinelError("result coordinate authority is incomplete")
    payload = backend.get("payload")
    if not isinstance(payload, dict):
        raise WaveOneRoleBSentinelError("backend PP-OCR payload is absent")
    geometry = validate_ppocrv6_payload(
        payload,
        pixel_width=dimensions[0],
        pixel_height=dimensions[1],
    )
    if geometry != {
        "line_count": record["line_count"],
        "word_token_count": record["word_token_count"],
    }:
        raise WaveOneRoleBSentinelError("backend and result geometry counts differ")
    recomputed = model_neutral_page_result(
        payload,
        coordinate_authority=render["coordinate_authority"],
    )
    exact_projection = {
        "status": result.get("status"),
        "coordinate_authority": result.get("coordinate_authority"),
        "lines": result.get("lines"),
        "words": result.get("words"),
        "metrics": result.get("metrics"),
        "source_blank_claimed": result.get("source_blank_claimed"),
    }
    if (
        set(result)
        != {
            "format_version",
            "status",
            "claim_boundary",
            "request_sha256",
            "request",
            "source_sha256",
            "source_size_bytes",
            "physical_page",
            "route",
            "provider_identity_sha256",
            "render_runtime_identity_sha256",
            "input_render_ref",
            "backend_payload_ref",
            "coordinate_authority",
            "lines",
            "words",
            "metrics",
            "source_blank_claimed",
            "safety",
        }
        or exact_projection != recomputed
    ):
        raise WaveOneRoleBSentinelError(
            "model-neutral result differs from deterministic backend projection"
        )


def _checkpoint_payload(
    control: dict[str, Any],
    document_id: str,
    records: list[dict[str, Any]],
    previous_sha256: str | None,
) -> dict[str, Any]:
    expected = sorted(
        (item for item in _control_index(control).values() if item["document_id"] == document_id),
        key=lambda item: item["sentinel_ordinal"],
    )
    completed = sorted(records, key=lambda item: item["sentinel_ordinal"])
    expected_hashes = [item["request_sha256"] for item in expected]
    completed_hashes = [item["request_sha256"] for item in completed]
    if len(completed_hashes) != len(set(completed_hashes)) or not set(completed_hashes) <= set(
        expected_hashes
    ):
        raise WaveOneRoleBSentinelError("checkpoint contains a foreign or duplicate request")
    return {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_SENTINEL_DOCUMENT_CHECKPOINT_V1",
        "status": (
            "COMPLETE_DOCUMENT_SENTINEL_REQUESTS"
            if set(completed_hashes) == set(expected_hashes)
            else "IN_PROGRESS_DOCUMENT_SENTINEL_REQUESTS"
        ),
        "claim_boundary": "EXACT_DOCUMENT_SENTINEL_REQUEST_ACCOUNTING_ONLY",
        "sealed_plan_sha256": SEALED_PLAN_SHA256,
        "control_identity_sha256": control["control_identity_sha256"],
        "document_id": document_id,
        "source_sha256": document_id.removeprefix("sha256:"),
        "expected_request_sha256s": expected_hashes,
        "generation": len(completed),
        "previous_checkpoint_sha256": previous_sha256,
        "completed": completed,
        "accounting": {
            "expected_request_count": len(expected),
            "completed_request_count": len(completed),
        },
    }


def _publish_checkpoint(
    project_root: Path,
    control: dict[str, Any],
    document_id: str,
    records: list[dict[str, Any]],
    previous_sha256: str | None,
) -> tuple[dict[str, Any], str]:
    checkpoint = _checkpoint_payload(control, document_id, records, previous_sha256)
    payload = _canonical_bytes(checkpoint)
    digest = sha256_bytes(payload)
    source_sha = document_id.removeprefix("sha256:")
    filename = f"{checkpoint['generation']:04d}-{digest}.json"
    _publish_exclusive(
        project_root,
        OUTPUT_RELATIVE_ROOT / "checkpoints" / source_sha,
        filename,
        payload,
    )
    return checkpoint, digest


def _load_document_checkpoint(
    project_root: Path,
    control: dict[str, Any],
    document_id: str,
    renders: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], str | None]:
    source_sha = document_id.removeprefix("sha256:")
    relative = OUTPUT_RELATIVE_ROOT / "checkpoints" / source_sha
    try:
        context = _held_directory(project_root, relative, create=False)
        held = context.__enter__()
    except WaveOneRoleBSentinelError as error:
        if "is absent" in str(error):
            return [], None
        raise
    try:
        _directory, directory_fd = held
        _recover_owned_hardlink_temporaries(directory_fd)
        raw_names = sorted(os.listdir(directory_fd))
        names = []
        interrupted_temporary = re.compile(r"^\.\d{4}-[0-9a-f]{64}\.json\.[0-9a-f]{32}\.tmp$")
        for name in raw_names:
            if interrupted_temporary.fullmatch(name):
                temporary = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                if (
                    not stat.S_ISREG(temporary.st_mode)
                    or stat.S_IMODE(temporary.st_mode) not in {0o600, 0o444}
                    or temporary.st_nlink != 1
                ):
                    raise WaveOneRoleBSentinelError(
                        "interrupted checkpoint temporary is not safely quarantinable"
                    )
                continue
            names.append(name)
        if any(
            not name.endswith(".json")
            or len(name) != 4 + 1 + 64 + 5
            or name[4] != "-"
            or not name[:4].isdigit()
            or not _is_sha256(name[5:-5])
            for name in names
        ):
            raise WaveOneRoleBSentinelError("checkpoint directory contains a foreign entry")
        expected_requests = {
            item["request_sha256"]: item
            for item in _control_index(control).values()
            if item["document_id"] == document_id
        }
        previous: str | None = None
        previous_completed: list[dict[str, Any]] = []
        for generation, name in enumerate(names, start=1):
            payload, identity = _hash_open_at(directory_fd, name)
            digest = sha256_bytes(payload)
            if (
                int(name[:4]) != generation
                or name[5:-5] != digest
                or stat.S_IMODE(identity.st_mode) != 0o444
                or identity.st_nlink != 1
            ):
                raise WaveOneRoleBSentinelError("checkpoint filename or mode drifted")
            checkpoint = _json_object(payload, "document checkpoint")
            expected_checkpoint = _checkpoint_payload(
                control,
                document_id,
                checkpoint.get("completed", []),
                previous,
            )
            if checkpoint != expected_checkpoint or checkpoint.get("generation") != generation:
                raise WaveOneRoleBSentinelError("checkpoint generation identity drifted")
            completed = checkpoint["completed"]
            if (
                len(completed) != len(previous_completed) + 1
                or completed[:-1] != previous_completed
            ):
                raise WaveOneRoleBSentinelError("checkpoint chain is not append-only by one page")
            for record in completed:
                expected = expected_requests.get(record.get("request_sha256"))
                if expected is None:
                    raise WaveOneRoleBSentinelError("checkpoint has a stale request")
                render = renders.get(record["request_sha256"])
                if render is None:
                    raise WaveOneRoleBSentinelError("checkpoint has no source rerender authority")
                _validate_result_record(project_root, record, expected, render)
            previous = digest
            previous_completed = completed
        return previous_completed, previous
    finally:
        context.__exit__(None, None, None)


def _scan_result_orphans(
    project_root: Path,
    control: dict[str, Any],
    document_id: str,
    completed: list[dict[str, Any]],
    renders: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    output_root = project_root / OUTPUT_RELATIVE_ROOT
    completed_hashes = {record["request_sha256"] for record in completed}
    expected = {
        item["request_sha256"]: item
        for item in _control_index(control).values()
        if item["document_id"] == document_id and item["request_sha256"] not in completed_hashes
    }
    if not expected:
        return []
    objects_root = OUTPUT_RELATIVE_ROOT / "objects" / "sha256"
    try:
        with _held_directory(project_root, objects_root, create=False) as (path, _fd):
            candidates = []
            for shard in sorted(path.iterdir()):
                shard_identity = shard.stat(follow_symlinks=False)
                if stat.S_ISLNK(shard_identity.st_mode) or not stat.S_ISDIR(shard_identity.st_mode):
                    raise WaveOneRoleBSentinelError("object store contains a foreign shard entry")
                with _held_directory(
                    project_root,
                    objects_root / shard.name,
                    create=False,
                ) as (held_shard, shard_fd):
                    _recover_owned_hardlink_temporaries(shard_fd)
                    for candidate in sorted(held_shard.iterdir()):
                        if candidate.suffix != ".json":
                            continue
                        identity = candidate.stat(follow_symlinks=False)
                        if stat.S_ISLNK(identity.st_mode) or not stat.S_ISREG(identity.st_mode):
                            raise WaveOneRoleBSentinelError(
                                "object store contains a foreign JSON entry"
                            )
                        candidates.append(candidate)
    except WaveOneRoleBSentinelError as error:
        if "is absent" in str(error):
            return []
        raise
    matches: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for candidate in candidates:
        name_digest = candidate.stem
        if not _is_sha256(name_digest):
            raise WaveOneRoleBSentinelError("content-addressed JSON filename is malformed")
        reference = {
            "path": candidate.relative_to(output_root).as_posix(),
            "sha256": name_digest,
            "size_bytes": candidate.stat(follow_symlinks=False).st_size,
        }
        payload = _read_object(project_root, reference, ".json")
        value = _json_object(payload, "content-addressed JSON object")
        if value.get("format_version") != "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V1":
            continue
        request_sha = value.get("request_sha256")
        if request_sha in expected:
            matches[request_sha].append((value, reference))
    adopted = []
    for request_sha, candidates_for_request in matches.items():
        if len(candidates_for_request) != 1:
            raise WaveOneRoleBSentinelError(
                "conflicting result objects exist for one full request identity"
            )
        result, result_ref = candidates_for_request[0]
        record = {
            "sentinel_ordinal": expected[request_sha]["sentinel_ordinal"],
            "request_sha256": request_sha,
            "status": result.get("status"),
            "render_ref": result.get("input_render_ref"),
            "backend_payload_ref": result.get("backend_payload_ref"),
            "result_ref": result_ref,
            "line_count": result.get("metrics", {}).get("line_count"),
            "word_token_count": result.get("metrics", {}).get("word_token_count"),
        }
        render = renders.get(request_sha)
        if render is None:
            raise WaveOneRoleBSentinelError("orphan has no source rerender authority")
        _validate_result_record(project_root, record, expected[request_sha], render)
        adopted.append(record)
    return sorted(adopted, key=lambda item: item["sentinel_ordinal"])


def _consume_worker_response(
    project_root: Path,
    control: dict[str, Any],
    expected: dict[str, Any],
    render: dict[str, Any],
    response_payload: bytes,
    *,
    execution_nonce: str,
    shard_id: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    response = _json_object(response_payload, "PP-OCR worker response")
    if not isinstance(response, dict) or set(response) != {
        "format_version",
        "execution_nonce",
        "shard_id",
        "request_sha256",
        "render_sha256",
        "provider_identity_sha256",
        "payload",
        "observational",
    }:
        raise WaveOneRoleBSentinelError("worker response fields drifted")
    observational = response["observational"]
    if (
        response["format_version"] != "BANK_CORPUS_WAVE_1_PPOCRV6_WORKER_RESPONSE_V1"
        or response["execution_nonce"] != execution_nonce
        or isinstance(response["shard_id"], bool)
        or not isinstance(response["shard_id"], int)
        or response["shard_id"] != shard_id
        or response["request_sha256"] != expected["request_sha256"]
        or response["render_sha256"] != render["ref"]["sha256"]
        or response["provider_identity_sha256"] != expected["request"]["provider_identity_sha256"]
        or not isinstance(observational, dict)
        or set(observational) != {"inference_wall_seconds", "model_load_wall_seconds"}
        or any(
            isinstance(observational[key], bool)
            or not isinstance(observational[key], (int, float))
            or not isfinite(observational[key])
            or observational[key] < 0
            for key in ("inference_wall_seconds", "model_load_wall_seconds")
        )
    ):
        raise WaveOneRoleBSentinelError("worker response identity drifted")
    payload = response["payload"]
    if not isinstance(payload, dict):
        raise WaveOneRoleBSentinelError("worker response lacks a PP-OCR payload")
    counts = validate_ppocrv6_payload(
        payload,
        pixel_width=render["pixel_width"],
        pixel_height=render["pixel_height"],
    )
    backend = {
        "format_version": "BANK_CORPUS_WAVE_1_PPOCRV6_BACKEND_PAYLOAD_V1",
        "claim_boundary": "RAW_PINNED_PROVIDER_PAYLOAD_FOR_ONE_EXACT_PAGE_REQUEST_ONLY",
        "request_sha256": expected["request_sha256"],
        "request": expected["request"],
        "provider_identity_sha256": expected["request"]["provider_identity_sha256"],
        "render_ref": render["ref"],
        "payload": payload,
    }
    backend_bytes = _canonical_bytes(backend)
    backend_ref = _put_object(project_root, backend_bytes, suffix=".json")
    neutral = model_neutral_page_result(
        payload,
        coordinate_authority=render["coordinate_authority"],
    )
    result = {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V1",
        "status": neutral["status"],
        "claim_boundary": "SOURCE_VISIBLE_PAGE_TEXT_AND_GEOMETRY_EVIDENCE_ONLY",
        "request_sha256": expected["request_sha256"],
        "request": expected["request"],
        "source_sha256": expected["source_sha256"],
        "source_size_bytes": expected["source_size_bytes"],
        "physical_page": expected["physical_page"],
        "route": "DOMINANT_RASTER_OCR",
        "provider_identity_sha256": expected["request"]["provider_identity_sha256"],
        "render_runtime_identity_sha256": expected["request"]["render_runtime_identity_sha256"],
        "input_render_ref": render["ref"],
        "backend_payload_ref": backend_ref,
        "coordinate_authority": neutral["coordinate_authority"],
        "lines": neutral["lines"],
        "words": neutral["words"],
        "metrics": neutral["metrics"],
        "source_blank_claimed": False,
        "safety": {
            "statement_classified": False,
            "table_classified": False,
            "rows_reconstructed": False,
            "cells_interpreted": False,
            "absence_claimed": False,
            "bank_registry_metadata_used": False,
            "filename_metadata_used": False,
            "role_a_used": False,
            "schema_used": False,
            "mapping_used": False,
            "historical_values_used": False,
        },
    }
    result_ref = _put_object(project_root, _canonical_bytes(result), suffix=".json")
    record = {
        "sentinel_ordinal": expected["sentinel_ordinal"],
        "request_sha256": expected["request_sha256"],
        "status": result["status"],
        "render_ref": render["ref"],
        "backend_payload_ref": backend_ref,
        "result_ref": result_ref,
        "line_count": counts["line_count"],
        "word_token_count": counts["word_token_count"],
    }
    _validate_result_record(project_root, record, expected, render)
    return record, observational


@contextmanager
def _document_locks(
    project_root: Path,
    document_ids: list[str],
    *,
    create: bool = True,
) -> Iterator[None]:
    descriptors: list[int] = []
    held: list[tuple[str, int, tuple[int, int]]] = []
    with _held_directory(
        project_root,
        OUTPUT_RELATIVE_ROOT / "locks",
        create=create,
    ) as (_directory, directory_fd):
        try:
            for document_id in sorted(document_ids):
                source_sha = document_id.removeprefix("sha256:")
                name = f"{source_sha}.lock"
                flags = os.O_RDWR | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
                if create:
                    flags |= os.O_CREAT
                descriptor = os.open(name, flags, 0o600, dir_fd=directory_fd)
                identity = os.fstat(descriptor)
                named = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                if (
                    not stat.S_ISREG(identity.st_mode)
                    or stat.S_IMODE(identity.st_mode) != 0o600
                    or identity.st_nlink != 1
                    or identity.st_size != 0
                    or (named.st_dev, named.st_ino) != (identity.st_dev, identity.st_ino)
                ):
                    os.close(descriptor)
                    raise WaveOneRoleBSentinelError("document lock identity drifted")
                fcntl.flock(descriptor, fcntl.LOCK_EX)
                acquired = os.fstat(descriptor)
                acquired_name = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                if (
                    not stat.S_ISREG(acquired.st_mode)
                    or stat.S_IMODE(acquired.st_mode) != 0o600
                    or acquired.st_nlink != 1
                    or acquired.st_size != 0
                    or (acquired_name.st_dev, acquired_name.st_ino)
                    != (acquired.st_dev, acquired.st_ino)
                ):
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                    os.close(descriptor)
                    raise WaveOneRoleBSentinelError(
                        "document lock name changed while waiting for flock"
                    )
                descriptors.append(descriptor)
                held.append((name, descriptor, (acquired.st_dev, acquired.st_ino)))
            yield
        finally:
            cleanup_error: WaveOneRoleBSentinelError | None = None
            for name, descriptor, expected_identity in reversed(held):
                observed = os.fstat(descriptor)
                try:
                    named = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                except FileNotFoundError:
                    named = None
                if cleanup_error is None and (
                    (observed.st_dev, observed.st_ino) != expected_identity
                    or named is None
                    or (named.st_dev, named.st_ino) != expected_identity
                    or stat.S_IMODE(observed.st_mode) != 0o600
                    or observed.st_nlink != 1
                    or observed.st_size != 0
                ):
                    cleanup_error = WaveOneRoleBSentinelError("held document lock identity drifted")
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                finally:
                    os.close(descriptor)
            descriptors.clear()
            if cleanup_error is not None:
                raise cleanup_error


@contextmanager
def _execution_lease(project_root: Path) -> Iterator[int]:
    """Hold one global flock; workers inherit its open file description."""

    name = "sentinel-execution.lease"
    with _held_directory(
        project_root,
        OUTPUT_RELATIVE_ROOT / "locks",
        create=True,
    ) as (_directory, directory_fd):
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(name, flags, 0o600, dir_fd=directory_fd)
        try:
            before = os.fstat(descriptor)
            named_before = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            if (
                not stat.S_ISREG(before.st_mode)
                or stat.S_IMODE(before.st_mode) != 0o600
                or before.st_nlink != 1
                or before.st_size != 0
                or (before.st_dev, before.st_ino) != (named_before.st_dev, named_before.st_ino)
            ):
                raise WaveOneRoleBSentinelError("global execution lease identity drifted")
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            acquired = os.fstat(descriptor)
            named_acquired = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            expected = (acquired.st_dev, acquired.st_ino)
            if (
                expected != (before.st_dev, before.st_ino)
                or expected != (named_acquired.st_dev, named_acquired.st_ino)
                or stat.S_IMODE(acquired.st_mode) != 0o600
                or acquired.st_nlink != 1
                or acquired.st_size != 0
            ):
                raise WaveOneRoleBSentinelError(
                    "global execution lease changed while waiting for flock"
                )
            yield descriptor
        finally:
            cleanup_error: WaveOneRoleBSentinelError | None = None
            observed = os.fstat(descriptor)
            try:
                named = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                named = None
            if (
                named is None
                or (observed.st_dev, observed.st_ino) != (named.st_dev, named.st_ino)
                or stat.S_IMODE(observed.st_mode) != 0o600
                or observed.st_nlink != 1
                or observed.st_size != 0
            ):
                cleanup_error = WaveOneRoleBSentinelError(
                    "held global execution lease identity drifted"
                )
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)
            if cleanup_error is not None:
                raise cleanup_error


def _render_exact_sentinel_sources(
    project_root: Path,
    sealed: dict[str, Any],
    control: dict[str, Any],
    *,
    require_existing: bool,
) -> dict[str, dict[str, Any]]:
    """Rerender every target from receipt-bound PDF bytes as lineage authority."""

    control_index = _control_index(control)
    by_document = {document["document_id"]: document for document in sealed["documents"]}
    requested_by_document: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for expected in control_index.values():
        requested_by_document[expected["document_id"]].append(expected)
    renders: dict[str, dict[str, Any]] = {}
    for document_id in sorted(requested_by_document):
        document = by_document.get(document_id)
        if document is None:
            raise WaveOneRoleBSentinelError("control source is absent from sealed plan")
        source_path = _project_path(project_root, document["relative_path"], "selected source PDF")
        source_payload = _stable_bytes(source_path, "receipt-bound selected source PDF")
        if (
            len(source_payload) != document["size_bytes"]
            or sha256_bytes(source_payload) != document["sha256"]
            or document_id != f"sha256:{document['sha256']}"
        ):
            raise WaveOneRoleBSentinelError("receipt-bound source PDF identity drifted")
        try:
            pdf = fitz.open(stream=source_payload, filetype="pdf")
        except Exception as error:
            raise WaveOneRoleBSentinelError("receipt-bound source PDF cannot be opened") from error
        try:
            if pdf.page_count != document["page_count"]:
                raise WaveOneRoleBSentinelError("receipt-bound source PDF page count drifted")
            for expected in sorted(
                requested_by_document[document_id],
                key=lambda item: item["sentinel_ordinal"],
            ):
                request = expected["request"]
                specification = request["render_specification"]
                if specification not in (
                    {
                        "source": "FULL_COMPOSITED_DISPLAYED_PDF_PAGE",
                        "dpi": 200,
                        "colorspace": "RGB",
                        "alpha": False,
                        "annotations": "INCLUDED",
                    },
                    {
                        "source": "FULL_COMPOSITED_DISPLAYED_PDF_PAGE",
                        "dpi": 300,
                        "colorspace": "RGB",
                        "alpha": False,
                        "annotations": "INCLUDED",
                    },
                ):
                    raise WaveOneRoleBSentinelError("sealed sentinel render contract drifted")
                page = pdf.load_page(expected["physical_page"] - 1)
                rendered = render_composited_displayed_page(page, dpi=specification["dpi"])
                render_ref = {
                    "path": (
                        Path("objects/sha256") / rendered.sha256[:2] / f"{rendered.sha256}.png"
                    ).as_posix(),
                    "sha256": rendered.sha256,
                    "size_bytes": rendered.size_bytes,
                }
                if require_existing:
                    observed = _read_object(project_root, render_ref, ".png")
                    if observed != rendered.payload:
                        raise WaveOneRoleBSentinelError("source rerender bytes drifted")
                renders[expected["request_sha256"]] = {
                    "payload": rendered.payload,
                    "ref": render_ref,
                    "pixel_width": rendered.pixel_width,
                    "pixel_height": rendered.pixel_height,
                    "dpi": rendered.dpi,
                    "coordinate_authority": rendered.coordinate_authority,
                }
        finally:
            pdf.close()
        source_after = _stable_bytes(source_path, "receipt-bound selected source PDF")
        if source_after != source_payload:
            raise WaveOneRoleBSentinelError("receipt-bound source changed during rendering")
    if set(renders) != set(control_index):
        raise WaveOneRoleBSentinelError("source rerender did not account for all 24 requests")
    return renders


def _publish_missing_render_objects(
    project_root: Path,
    renders: dict[str, dict[str, Any]],
    completed_request_sha256s: set[str],
) -> None:
    for request_sha, render in renders.items():
        if request_sha in completed_request_sha256s:
            continue
        reference = _put_object(project_root, render["payload"], suffix=".png")
        if reference != render["ref"]:
            raise WaveOneRoleBSentinelError("missing render publication identity drifted")


def _ensure_capacity(project_root: Path, minimum_bytes: int) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(project_root, flags)
    try:
        filesystem = os.fstatvfs(descriptor)
        available = filesystem.f_bavail * filesystem.f_frsize
    finally:
        os.close(descriptor)
    if available < minimum_bytes:
        raise WaveOneRoleBSentinelError(
            f"sentinel execution requires {minimum_bytes} free bytes; found {available}"
        )


def _create_runtime_root(project_root: Path, execution_nonce: str) -> Path:
    runtime_parent = OUTPUT_RELATIVE_ROOT / "runtime"
    name = f"execution-{execution_nonce}"
    with _held_directory(project_root, runtime_parent, create=True) as (
        _directory,
        directory_fd,
    ):
        try:
            os.mkdir(name, 0o700, dir_fd=directory_fd)
            os.fsync(directory_fd)
        except FileExistsError as error:
            raise WaveOneRoleBSentinelError(
                "fresh runtime nonce directory already exists"
            ) from error
        identity = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if not stat.S_ISDIR(identity.st_mode) or stat.S_IMODE(identity.st_mode) != 0o700:
            raise WaveOneRoleBSentinelError("runtime root mode or type drifted")
    root = project_root / runtime_parent / name
    relative_directories = [Path("shard-0/responses"), Path("shard-1/responses")]
    for shard_id in (0, 1):
        environment_root = Path(f"shard-{shard_id}/environment")
        relative_directories.extend(
            environment_root / relative
            for relative in (
                Path("home"),
                Path(".paddlex-cache"),
                Path("xdg-cache"),
                Path("xdg-config"),
                Path("xdg-data"),
                Path("tmp"),
            )
        )
    for relative in relative_directories:
        with _held_directory(
            project_root,
            runtime_parent / name / relative,
            create=True,
        ):
            pass
    return root


def _worker_environment(
    project_root: Path,
    runtime_root: Path,
    policy: dict[str, Any],
    shard_id: int,
) -> dict[str, str]:
    if shard_id not in {0, 1}:
        raise WaveOneRoleBSentinelError("worker environment shard is invalid")
    environment_root = runtime_root / f"shard-{shard_id}" / "environment"
    environment = dict(policy["worker"]["environment"])
    environment["PADDLE_PDX_CACHE_HOME"] = (environment_root / ".paddlex-cache").as_posix()
    for key, relative in policy["worker"]["isolated_runtime_directories"].items():
        environment[key] = (environment_root / relative).as_posix()
    for key, value in policy["worker"]["supervisor_environment"].items():
        if key == "PATH":
            first, *remaining = value.split(":")
            interpreter_bin = _project_path(project_root, first, "worker PATH")
            environment[key] = ":".join([interpreter_bin.as_posix(), *remaining])
        else:
            environment[key] = value
    if "PYTHONPATH" in environment or set(environment) != {
        "PADDLE_PDX_CACHE_HOME",
        "PADDLE_PDX_MODEL_SOURCE",
        "PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK",
        "FLAGS_allocator_strategy",
        "OMP_NUM_THREADS",
        "PYTHONHASHSEED",
        "PYTHONNOUSERSITE",
        "HOME",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "TMPDIR",
        "LANG",
        "LC_ALL",
        "PYTHONUTF8",
        "PYTHONCOERCECLOCALE",
        "PYTHONDONTWRITEBYTECODE",
        "PYTHONSAFEPATH",
        "PATH",
    }:
        raise WaveOneRoleBSentinelError("worker environment allowlist drifted")
    for key in (
        "PADDLE_PDX_CACHE_HOME",
        "HOME",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "TMPDIR",
    ):
        value = Path(environment[key])
        if not value.is_relative_to(environment_root):
            raise WaveOneRoleBSentinelError("isolated worker path escapes runtime root")
    return dict(sorted(environment.items()))


def _worker_model_contract(
    project_root: Path,
    model_cache: Path,
    sealed: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    runtime = sealed["ppocrv6_runtime_model_ledger"]
    configuration_records = [
        record for record in runtime["config_records"] if record["kind"] == "PPOCRV6_CONFIGURATION"
    ]
    if len(configuration_records) != 1:
        raise WaveOneRoleBSentinelError("sealed PP-OCR configuration record is not unique")
    record = configuration_records[0]
    configuration_path = _project_path(project_root, record["path"], "PP-OCR configuration")
    configuration = {
        "path": configuration_path.as_posix(),
        "sha256": record["sha256"],
        "size_bytes": record["size_bytes"],
    }
    models = []
    for model in runtime["models"]:
        locator = model["inventory"]["locator"]
        prefix = "MODEL_CACHE/"
        if not isinstance(locator, str) or not locator.startswith(prefix):
            raise WaveOneRoleBSentinelError("sealed model locator drifted")
        directory = model_cache.resolve() / locator.removeprefix(prefix)
        file_records = []
        locator_prefix = f"{locator}/"
        for file_record in model["inventory"]["files"]:
            path = file_record["path"]
            if not path.startswith(locator_prefix):
                raise WaveOneRoleBSentinelError("sealed model file locator drifted")
            file_records.append(
                {
                    "path": path.removeprefix(locator_prefix),
                    "sha256": file_record["sha256"],
                    "size_bytes": file_record["size_bytes"],
                }
            )
        models.append(
            {
                "key": model["key"],
                "directory": directory.as_posix(),
                "files": file_records,
            }
        )
    return configuration, models


def _build_worker_task(
    project_root: Path,
    model_cache: Path,
    sealed: dict[str, Any],
    shard_id: int,
    requests: list[dict[str, Any]],
    renders: dict[str, dict[str, Any]],
    execution_nonce: str,
    environment: dict[str, str],
    execution_lease_fd: int,
) -> dict[str, Any]:
    configuration, models = _worker_model_contract(project_root, model_cache, sealed)
    provider = sealed["ppocrv6_runtime_model_ledger"]["sha256"]
    lease = os.fstat(execution_lease_fd)
    if (
        not stat.S_ISREG(lease.st_mode)
        or stat.S_IMODE(lease.st_mode) != 0o600
        or lease.st_nlink != 1
        or lease.st_size != 0
    ):
        raise WaveOneRoleBSentinelError("inherited execution lease identity drifted")
    page_tasks = []
    for request in sorted(requests, key=lambda item: item["sentinel_ordinal"]):
        render = renders[request["request_sha256"]]
        image_path = project_root / OUTPUT_RELATIVE_ROOT / render["ref"]["path"]
        page_tasks.append(
            {
                "request_sha256": request["request_sha256"],
                "render_sha256": render["ref"]["sha256"],
                "render_size_bytes": render["ref"]["size_bytes"],
                "image_path": image_path.as_posix(),
                "pixel_width": render["pixel_width"],
                "pixel_height": render["pixel_height"],
                "response_filename": f"{request['request_sha256']}.response.json",
            }
        )
    return {
        "format_version": "BANK_CORPUS_WAVE_1_PPOCRV6_WORKER_TASK_V1",
        "protocol": "EXCLUSIVE_CANONICAL_JSON_RESPONSE_FILES_V1",
        "execution_nonce": execution_nonce,
        "shard_id": shard_id,
        "provider_identity_sha256": provider,
        "cpu_threads": 6,
        "expected_environment": environment,
        "execution_lease": {
            "fd": execution_lease_fd,
            "device": lease.st_dev,
            "inode": lease.st_ino,
        },
        "configuration": configuration,
        "models": models,
        "requests": page_tasks,
    }


def _open_runtime_log(project_root: Path, relative_directory: Path, name: str) -> BinaryIO:
    with _held_directory(project_root, relative_directory, create=False) as (
        _directory,
        directory_fd,
    ):
        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        descriptor = os.open(name, flags, 0o600, dir_fd=directory_fd)
        identity = os.fstat(descriptor)
        named = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if (identity.st_dev, identity.st_ino) != (named.st_dev, named.st_ino):
            os.close(descriptor)
            raise WaveOneRoleBSentinelError("runtime log identity drifted")
        return os.fdopen(descriptor, "wb", closefd=True)


def _append_observational_timing(
    project_root: Path,
    runtime_relative: Path,
    observation: dict[str, Any],
) -> None:
    payload = _canonical_bytes(observation)
    with _held_directory(project_root, runtime_relative, create=False) as (
        _directory,
        directory_fd,
    ):
        flags = (
            os.O_WRONLY
            | os.O_APPEND
            | os.O_CREAT
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        descriptor = os.open("timing-observations.jsonl", flags, 0o600, dir_fd=directory_fd)
        try:
            identity = os.fstat(descriptor)
            named = os.stat(
                "timing-observations.jsonl",
                dir_fd=directory_fd,
                follow_symlinks=False,
            )
            if (
                not stat.S_ISREG(identity.st_mode)
                or stat.S_IMODE(identity.st_mode) != 0o600
                or (identity.st_dev, identity.st_ino) != (named.st_dev, named.st_ino)
            ):
                raise WaveOneRoleBSentinelError("observational timing log identity drifted")
            os.write(descriptor, payload)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _read_response_at(directory_fd: int, filename: str) -> bytes | None:
    _recover_owned_hardlink_temporaries(directory_fd)
    try:
        payload, identity = _hash_open_at(directory_fd, filename)
    except FileNotFoundError:
        return None
    if stat.S_IMODE(identity.st_mode) != 0o444 or identity.st_nlink != 1:
        raise WaveOneRoleBSentinelError("worker response is not immutable")
    return payload


def _run_pinned_workers(
    project_root: Path,
    model_cache: Path,
    sealed: dict[str, Any],
    policy: dict[str, Any],
    control: dict[str, Any],
    renders: dict[str, dict[str, Any]],
    records_by_document: dict[str, list[dict[str, Any]]],
    checkpoint_by_document: dict[str, str | None],
    execution_lease_fd: int,
) -> dict[str, Any]:
    """Launch at most two pinned workers; no worker/session injection surface exists."""

    completed_hashes = {
        record["request_sha256"] for records in records_by_document.values() for record in records
    }
    missing_by_shard = {
        shard["shard_id"]: [
            request
            for request in shard["requests"]
            if request["request_sha256"] not in completed_hashes
        ]
        for shard in control["sharding"]["shards"]
    }
    active = {shard_id: requests for shard_id, requests in missing_by_shard.items() if requests}
    if not active:
        return {
            "status": "COMPLETE_RESUME_WITH_ZERO_INFERENCE",
            "worker_process_count": 0,
            "inference_request_count": 0,
            "observational_runtime_path": None,
        }
    if not 1 <= len(active) <= 2:
        raise WaveOneRoleBSentinelError("active worker count exceeds the sealed maximum")
    if not completed_hashes and (
        set(active) != {0, 1} or any(len(value) != 12 for value in active.values())
    ):
        raise WaveOneRoleBSentinelError("initial sentinel run must launch exact two 12-page shards")
    _ensure_capacity(project_root, policy["execution"]["minimum_free_space_bytes"])
    execution_nonce = secrets.token_hex(32)
    runtime_root = _create_runtime_root(project_root, execution_nonce)
    runtime_relative = runtime_root.relative_to(project_root)
    interpreter = project_root / policy["worker"]["interpreter"]
    script = _project_path(project_root, policy["worker"]["script"], "sentinel worker")
    expected_interpreter = sealed["ppocrv6_runtime_model_ledger"]
    interpreter_target = interpreter.resolve()
    interpreter_payload = _stable_bytes(interpreter_target, "isolated PP-OCR interpreter")
    if (
        sha256_bytes(interpreter_payload)
        != expected_interpreter["runtime_interpreter_target_sha256"]
        or len(interpreter_payload) != expected_interpreter["runtime_interpreter_target_size_bytes"]
    ):
        raise WaveOneRoleBSentinelError("isolated PP-OCR interpreter drifted before launch")
    process_records: dict[int, dict[str, Any]] = {}
    processes: dict[int, subprocess.Popen[bytes]] = {}
    open_logs: list[BinaryIO] = []
    response_contexts = ExitStack()
    try:
        response_directories: dict[int, tuple[Path, int]] = {}
        for shard_id, requests in sorted(active.items()):
            shard_relative = runtime_relative / f"shard-{shard_id}"
            environment = _worker_environment(
                project_root,
                runtime_root,
                policy,
                shard_id,
            )
            response_directories[shard_id] = response_contexts.enter_context(
                _held_directory(project_root, shard_relative / "responses", create=False)
            )
            task = _build_worker_task(
                project_root,
                model_cache,
                sealed,
                shard_id,
                requests,
                renders,
                execution_nonce,
                environment,
                execution_lease_fd,
            )
            task_path = _publish_exclusive(
                project_root,
                shard_relative,
                "task.json",
                _canonical_bytes(task),
            )
            stdout = _open_runtime_log(project_root, shard_relative, "stdout.log")
            stderr = _open_runtime_log(project_root, shard_relative, "stderr.log")
            open_logs.extend((stdout, stderr))
            process = subprocess.Popen(
                [
                    interpreter.as_posix(),
                    script.as_posix(),
                    "--task",
                    task_path.as_posix(),
                    "--response-directory",
                    response_directories[shard_id][0].as_posix(),
                ],
                cwd=project_root,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                close_fds=True,
                pass_fds=(execution_lease_fd,),
            )
            processes[shard_id] = process
            process_records[shard_id] = {
                "expected": {request["request_sha256"]: request for request in requests},
                "consumed": set(),
            }
        while True:
            made_progress = False
            for shard_id, process in sorted(processes.items()):
                state = process_records[shard_id]
                _response_path, response_fd = response_directories[shard_id]
                for request_sha, expected in state["expected"].items():
                    if request_sha in state["consumed"]:
                        continue
                    response = _read_response_at(response_fd, f"{request_sha}.response.json")
                    if response is None:
                        continue
                    record, observational = _consume_worker_response(
                        project_root,
                        control,
                        expected,
                        renders[request_sha],
                        response,
                        execution_nonce=execution_nonce,
                        shard_id=shard_id,
                    )
                    document_id = expected["document_id"]
                    records = records_by_document[document_id]
                    if any(item["request_sha256"] == request_sha for item in records):
                        raise WaveOneRoleBSentinelError(
                            "worker returned an already completed request"
                        )
                    records.append(record)
                    checkpoint, checkpoint_sha = _publish_checkpoint(
                        project_root,
                        control,
                        document_id,
                        records,
                        checkpoint_by_document[document_id],
                    )
                    if checkpoint["generation"] != len(records):
                        raise WaveOneRoleBSentinelError("per-page checkpoint generation drifted")
                    checkpoint_by_document[document_id] = checkpoint_sha
                    state["consumed"].add(request_sha)
                    _append_observational_timing(
                        project_root,
                        runtime_relative,
                        {
                            "kind": "NON_IDENTITY_OBSERVATIONAL_WORKER_TIMING",
                            "execution_nonce": execution_nonce,
                            "shard_id": shard_id,
                            "request_sha256": request_sha,
                            **observational,
                        },
                    )
                    made_progress = True
                return_code = process.poll()
                if return_code is not None and return_code != 0:
                    raise WaveOneRoleBSentinelError(
                        f"pinned PP-OCR worker shard {shard_id} failed: {return_code}"
                    )
            all_consumed = all(
                set(state["expected"]) == state["consumed"] for state in process_records.values()
            )
            all_exited = all(process.poll() is not None for process in processes.values())
            if all_consumed and all_exited:
                break
            if all_exited and not all_consumed:
                raise WaveOneRoleBSentinelError("worker exited without all exact responses")
            if not made_progress:
                time.sleep(0.05)
        if any(process.returncode != 0 for process in processes.values()):
            raise WaveOneRoleBSentinelError("one or more pinned workers failed")
        interpreter_after = _stable_bytes(
            interpreter_target,
            "isolated PP-OCR interpreter",
        )
        if interpreter_after != interpreter_payload:
            raise WaveOneRoleBSentinelError("isolated PP-OCR interpreter changed during run")
        return {
            "status": "COMPLETE_PINNED_WORKER_RESPONSES_CHECKPOINTED",
            "worker_process_count": len(processes),
            "inference_request_count": sum(len(value) for value in active.values()),
            "observational_runtime_path": runtime_relative.as_posix(),
        }
    except BaseException:
        for process in processes.values():
            if process.poll() is None:
                process.terminate()
        for process in processes.values():
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        raise
    finally:
        response_contexts.close()
        for stream in open_logs:
            stream.close()


def run_authenticated_sentinel(
    project_root: Path,
    *,
    model_cache: Path,
) -> dict[str, Any]:
    """Execute only the authenticated 24-page sentinel with the pinned workers."""

    project_root = project_root.resolve()
    sealed, policy, executor = _authenticate_sealed_plan(
        project_root,
        model_cache,
        require_clean_executor=True,
    )
    _ensure_capacity(project_root, policy["execution"]["minimum_free_space_bytes"])
    control = build_authenticated_control(project_root, model_cache=model_cache)
    if (
        control["executor_git"] != executor["git"]
        or control["executor_implementation_ledger"] != executor["implementation_ledger"]
    ):
        raise WaveOneRoleBSentinelError("control executor identity differs from run authority")
    _publish_exclusive(
        project_root,
        OUTPUT_RELATIVE_ROOT,
        "sentinel-execution-control.json",
        _canonical_bytes(control),
    )
    index = _control_index(control)
    document_ids = sorted({record["document_id"] for record in index.values()})
    with (
        _execution_lease(project_root) as execution_lease_fd,
        _document_locks(project_root, document_ids),
    ):
        renders = _render_exact_sentinel_sources(
            project_root,
            sealed,
            control,
            require_existing=False,
        )
        records_by_document: dict[str, list[dict[str, Any]]] = {}
        checkpoint_by_document: dict[str, str | None] = {}
        for document_id in document_ids:
            records, checkpoint = _load_document_checkpoint(
                project_root,
                control,
                document_id,
                renders,
            )
            records_by_document[document_id] = records
            checkpoint_by_document[document_id] = checkpoint
            adopted = _scan_result_orphans(
                project_root,
                control,
                document_id,
                records,
                renders,
            )
            for record in adopted:
                records.append(record)
                _checkpoint, checkpoint = _publish_checkpoint(
                    project_root,
                    control,
                    document_id,
                    records,
                    checkpoint,
                )
            checkpoint_by_document[document_id] = checkpoint
        completed_hashes = {
            record["request_sha256"]
            for records in records_by_document.values()
            for record in records
        }
        _publish_missing_render_objects(project_root, renders, completed_hashes)
        execution = _run_pinned_workers(
            project_root,
            model_cache,
            sealed,
            policy,
            control,
            renders,
            records_by_document,
            checkpoint_by_document,
            execution_lease_fd,
        )
        expected_hashes = set(index)
        completed_hashes = {
            record["request_sha256"]
            for records in records_by_document.values()
            for record in records
        }
        if completed_hashes != expected_hashes:
            raise WaveOneRoleBSentinelError("sentinel run did not checkpoint all 24 requests")
    sealed_after, policy_after, executor_after = _authenticate_sealed_plan(
        project_root,
        model_cache,
        require_clean_executor=True,
    )
    if (
        _canonical_bytes(sealed_after) != _canonical_bytes(sealed)
        or policy_after != policy
        or executor_after != executor
    ):
        raise WaveOneRoleBSentinelError(
            "authenticated plan, policy, or executor changed during sentinel execution"
        )
    return {
        "status": "COMPLETE_AUTHENTICATED_24_PAGE_OCR_SENTINEL_CHECKPOINTS",
        "control_identity_sha256": control["control_identity_sha256"],
        "request_count": 24,
        "worker_execution_status": execution["status"],
        "worker_process_count": execution["worker_process_count"],
        "inference_request_count": execution["inference_request_count"],
        "observational_runtime_path": execution["observational_runtime_path"],
    }


def _read_published_control(project_root: Path, expected: dict[str, Any]) -> None:
    with _held_directory(project_root, OUTPUT_RELATIVE_ROOT, create=False) as (
        _directory,
        directory_fd,
    ):
        payload, identity = _hash_open_at(
            directory_fd,
            "sentinel-execution-control.json",
        )
        if (
            payload != _canonical_bytes(expected)
            or stat.S_IMODE(identity.st_mode) != 0o444
            or identity.st_nlink != 1
        ):
            raise WaveOneRoleBSentinelError("published sentinel control drifted")


def _final_checkpoint_ref(
    project_root: Path,
    document_id: str,
    generation: int,
    digest: str,
) -> dict[str, Any]:
    source_sha = document_id.removeprefix("sha256:")
    filename = f"{generation:04d}-{digest}.json"
    relative = OUTPUT_RELATIVE_ROOT / "checkpoints" / source_sha
    with _held_directory(project_root, relative, create=False) as (_directory, directory_fd):
        payload, identity = _hash_open_at(directory_fd, filename)
        if (
            sha256_bytes(payload) != digest
            or stat.S_IMODE(identity.st_mode) != 0o444
            or identity.st_nlink != 1
        ):
            raise WaveOneRoleBSentinelError("final checkpoint receipt drifted")
    return {
        "path": (Path("checkpoints") / source_sha / filename).as_posix(),
        "sha256": digest,
        "size_bytes": len(payload),
    }


def verify_authenticated_sentinel(
    project_root: Path,
    *,
    model_cache: Path,
) -> dict[str, Any]:
    """Rehash, rerender, and replay every exact result before aggregation."""

    project_root = project_root.resolve()
    sealed, policy, executor = _authenticate_sealed_plan(
        project_root,
        model_cache,
        require_clean_executor=True,
    )
    control = build_authenticated_control(project_root, model_cache=model_cache)
    _read_published_control(project_root, control)
    index = _control_index(control)
    document_ids = sorted({record["document_id"] for record in index.values()})
    checkpoint_receipts = []
    result_records = []
    with _document_locks(project_root, document_ids, create=False):
        renders = _render_exact_sentinel_sources(
            project_root,
            sealed,
            control,
            require_existing=True,
        )
        for document_id in document_ids:
            records, checkpoint_sha = _load_document_checkpoint(
                project_root,
                control,
                document_id,
                renders,
            )
            expected = [
                request for request in index.values() if request["document_id"] == document_id
            ]
            if checkpoint_sha is None or {record["request_sha256"] for record in records} != {
                request["request_sha256"] for request in expected
            }:
                raise WaveOneRoleBSentinelError("document checkpoint is not source-complete")
            checkpoint_receipts.append(
                {
                    "document_id": document_id,
                    "source_sha256": document_id.removeprefix("sha256:"),
                    "request_count": len(records),
                    "checkpoint_ref": _final_checkpoint_ref(
                        project_root,
                        document_id,
                        len(records),
                        checkpoint_sha,
                    ),
                }
            )
            result_records.extend(records)
    result_records.sort(key=lambda item: item["sentinel_ordinal"])
    if (
        len(result_records) != 24
        or [record["sentinel_ordinal"] for record in result_records] != list(range(1, 25))
        or Counter(record["status"] for record in result_records)
        != {"OCR_WORD_BOX_READ_COMPLETE": 24}
    ):
        raise WaveOneRoleBSentinelError("aggregate result accounting drifted")
    aggregate = {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_OCR_SENTINEL_AGGREGATE_V1",
        "status": _PRODUCTION_STATUS,
        "claim_boundary": policy["claim_boundary"],
        "sealed_plan": control["sealed_plan"],
        "control": {
            "identity_sha256": control["control_identity_sha256"],
            "artifact": {
                "path": "sentinel-execution-control.json",
                "sha256": sha256_bytes(_canonical_bytes(control)),
                "size_bytes": len(_canonical_bytes(control)),
            },
        },
        "executor_git": executor["git"],
        "executor_implementation_ledger": executor["implementation_ledger"],
        "provider_identity_sha256": sealed["ppocrv6_runtime_model_ledger"]["sha256"],
        "render_runtime_identity_sha256": sealed["render_runtime_ledger"]["sha256"],
        "execution_contract": {
            "shard_count": 2,
            "requests_per_shard": [12, 12],
            "documents_per_shard": [7, 7],
            "max_process_count": 2,
            "one_long_lived_session_per_active_shard": True,
            "cpu_threads_per_process": 6,
            "resume_inference_count_when_complete": 0,
            "orphan_adoption": "FULL_REQUEST_IDENTITY_ONLY",
            "timings_in_identity": False,
        },
        "document_checkpoints": sorted(
            checkpoint_receipts,
            key=lambda item: item["document_id"],
        ),
        "results": result_records,
        "accounting": {
            "document_count": len(checkpoint_receipts),
            "request_count": len(result_records),
            "complete_result_count": sum(
                record["status"] == "OCR_WORD_BOX_READ_COMPLETE" for record in result_records
            ),
            "line_count": sum(record["line_count"] for record in result_records),
            "word_token_count": sum(record["word_token_count"] for record in result_records),
            "unresolved_count": 0,
        },
        "safety": {
            "bank_registry_metadata_used": False,
            "filename_metadata_used": False,
            "role_a_used": False,
            "schema_used": False,
            "mapping_used": False,
            "historical_values_used": False,
            "statement_classification_count": 0,
            "table_classification_count": 0,
            "row_reconstruction_count": 0,
            "cell_interpretation_count": 0,
            "absence_declaration_count": 0,
            "source_visible_text_preserved_verbatim": True,
        },
    }
    aggregate["aggregate_identity_sha256"] = _canonical_sha256(aggregate)
    sealed_after, _policy_after, executor_after = _authenticate_sealed_plan(
        project_root,
        model_cache,
        require_clean_executor=True,
    )
    if _canonical_bytes(sealed_after) != _canonical_bytes(sealed) or executor_after != executor:
        raise WaveOneRoleBSentinelError("authenticated inputs changed during aggregate replay")
    return aggregate


def finalize_authenticated_sentinel(
    project_root: Path,
    *,
    model_cache: Path,
) -> dict[str, Any]:
    aggregate = verify_authenticated_sentinel(project_root, model_cache=model_cache)
    _publish_exclusive(
        project_root.resolve(),
        OUTPUT_RELATIVE_ROOT,
        "sentinel-aggregate.json",
        _canonical_bytes(aggregate),
    )
    replay = verify_authenticated_sentinel(project_root, model_cache=model_cache)
    if replay != aggregate:
        raise WaveOneRoleBSentinelError("aggregate replay changed during publication")
    return aggregate
