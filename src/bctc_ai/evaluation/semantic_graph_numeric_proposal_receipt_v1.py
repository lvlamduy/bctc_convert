"""Replay-authenticated numeric proposals for Semantic Accounting Graph v2.

This is the only authority bridge from a v3 semantic-graph crop registry to
numeric proposal fusion.  The public generic numeric verifier intentionally
rejects v3 registries.  Here, exact externally pinned artifact bytes are
validated, the registry and its upstream graph are replayed, and an opaque
in-memory receipt is minted before the package-private fusion function may be
called.

The resulting artifact has numeric-candidate authority only.  In particular it
does not grant geometry, period, unit, scope, statement, schema, ReportNormId,
or export authority.
"""

from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
import tempfile
import weakref
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from bctc_ai.core.hashing import sha256_bytes
from bctc_ai.evaluation.numeric_cell_verification import (
    NumericCellVerificationError,
    _verify_numeric_cell_proposals,
)
from bctc_ai.evaluation.semantic_graph_numeric_cell_crops_v1 import (
    CLAIM_BOUNDARY as CROP_CLAIM_BOUNDARY,
)
from bctc_ai.evaluation.semantic_graph_numeric_cell_crops_v1 import (
    GEOMETRY_AUTHORITY as CROP_GEOMETRY_AUTHORITY,
)
from bctc_ai.evaluation.semantic_graph_numeric_cell_crops_v1 import (
    POLICY as CROP_POLICY,
)
from bctc_ai.evaluation.semantic_graph_numeric_cell_crops_v1 import (
    validate_semantic_graph_numeric_cell_crop_registry_replay_v1,
)
from bctc_ai.ocr.numeric_cell_reader import (
    classify_numeric_prediction,
    load_numeric_reader_config,
    verify_numeric_reader_model,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.source_structure.local_accounting_graph_v1 import FamilySpecV1

__all__ = [
    "ArtifactPinV1",
    "AuthenticatedSemanticGraphNumericProposalReceiptV1",
    "SemanticGraphNumericProposalReceiptV1Error",
    "authenticate_semantic_graph_numeric_proposals_v1",
    "validate_semantic_graph_numeric_verification_replay_v1",
    "verify_semantic_graph_numeric_proposals_v1",
]


FORMAT_VERSION = 1
POLICY = "REPLAY_AUTHENTICATED_SEMANTIC_GRAPH_NUMERIC_PROPOSALS_V1"
AUTHORITY = "BOUNDED_FROZEN_HISTORICAL_NUMERIC_CANDIDATE_VERIFICATION_ONLY"
CLAIM_BOUNDARY = (
    "EXTERNALLY_SELECTED_FROZEN_HISTORICAL_EIGHT_CELL_NUMERIC_PROPOSAL_BYTES_"
    "WITH_EXACT_SOURCE_REPLAY_ONLY_NO_HARDWARE_OR_MODEL_EXECUTION_ATTESTATION_"
    "NO_GEOMETRY_PERIOD_UNIT_SCOPE_STATEMENT_SCHEMA_REPORT_NORM_ID_OR_EXPORT_AUTHORITY"
)
_SHA256 = re.compile(r"[0-9a-f]{64}")
_COMMIT = re.compile(r"[0-9a-f]{40}")
_CONFIG_PATH = Path("config/models/numeric-recognizer-v1.toml")
_ENTRYPOINT_PATHS = (
    _CONFIG_PATH,
    Path("scripts/models/run_numeric_cell_recognizer.py"),
)
_SOURCE_TREE_PATH = Path("src/bctc_ai")
_PREDICTION_FIELDS = {
    "cell_id",
    "crop_path",
    "crop_sha256",
    "proposal_status",
    "raw_prediction",
    "reader_score",
}
_PROPOSAL_STATUSES = {
    "EMPTY_PROPOSAL",
    "NUMERIC_CHARACTERS_ONLY_PROPOSAL",
    "REJECT_NON_NUMERIC_CHARACTERS",
}
_RUN_FIELDS = {
    "artifacts",
    "code",
    "completed_at",
    "confidence_policy",
    "configuration",
    "crop_registry",
    "dataset_role",
    "evidence_role",
    "format_version",
    "metrics",
    "runtime",
    "started_at",
    "state",
}
_SELECTION_FIELDS = {
    "artifacts",
    "cell_count",
    "claim_boundary",
    "format_version",
    "run_commit",
    "state",
}
_SELECTION_STATE = "FROZEN_NUMERIC_PROPOSAL_SELECTION_AUTHORITY"
_SELECTION_CLAIM_BOUNDARY = (
    "SELECTS_EXACT_PERSISTED_NUMERIC_PROPOSAL_ARTIFACT_BYTES_ONLY_"
    "NO_NUMERIC_TRUTH_GEOMETRY_PERIOD_UNIT_SCOPE_STATEMENT_SCHEMA_OR_EXPORT_AUTHORITY"
)
_RESULT_FIELDS = {
    "authority",
    "cells",
    "claim_boundary",
    "format_version",
    "inputs",
    "metrics",
    "policy",
    "safety",
    "status",
    "verification_id",
}
_RESULT_CELL_FIELDS = {
    "axis_id",
    "axis_ordinal",
    "cell_id",
    "challenger",
    "crop_path",
    "crop_sha256",
    "crop_size_bytes",
    "decision",
    "final_value_status",
    "normalized_numeric_value",
    "page",
    "primary",
    "row_ordinal",
    "selected_raw_value",
    "source_atom_id",
    "source_evidence_node_id",
    "source_graph_node_id",
    "source_line_index",
    "verification_status",
}
_RESULT_INPUT_FIELDS = {
    "authenticated_receipt_id",
    "expected_run_commit",
    "expected_selection_authority_commit",
    "historical_run_lineage",
    "pins",
    "semantic_graph",
    "semantic_page_binding_sha256",
    "source_projection_sha256",
}
_RESULT_METRIC_FIELDS = {
    "authenticated_cell_count",
    "automatic_reader_overwrite_count",
    "blank_cell_count",
    "blank_to_zero_or_value_promotion_count",
    "cell_count",
    "exact_eight_cell_agreement",
    "observed_cell_count",
    "observed_exact_agreement_rate",
    "primary_observation_counts",
    "reader_proposal_status_counts",
    "reader_score_decision_use_count",
    "unresolved_observed_cell_count",
    "verification_status_counts",
    "verified_observed_cell_count",
}
_PRIMARY_FIELDS = {
    "normalized_text",
    "observation",
    "raw_text",
    "sign_evidence",
    "value",
    "visual_punctuation_evidence",
}
_CHALLENGER_FIELDS = {
    "parse_reason",
    "parsed_observation",
    "parsed_value",
    "proposal_status",
    "raw_text",
    "reader_score",
    "sign_evidence",
}
_SAFETY = {
    "accounting_or_family_role_authority": False,
    "automatic_reader_overwrite_authority": False,
    "geometry_authority": False,
    "hardware_or_model_execution_attestation": False,
    "period_or_unit_or_scope_authority": False,
    "reader_score_decision_authority": False,
    "report_norm_id_or_schema_authority": False,
    "statement_or_export_authority": False,
}


class SemanticGraphNumericProposalReceiptV1Error(ValueError):
    """Pinned numeric proposal evidence or its replay lineage drifted."""


def _error(message: str) -> SemanticGraphNumericProposalReceiptV1Error:
    return SemanticGraphNumericProposalReceiptV1Error(message)


@dataclass(frozen=True, slots=True)
class ArtifactPinV1:
    """An external byte identity supplied independently by the caller."""

    path: Path
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.path, Path)
            or self.path.is_absolute()
            or self.path == Path(".")
            or ".." in self.path.parts
            or self.path.as_posix() != str(self.path)
            or _SHA256.fullmatch(self.sha256) is None
            or type(self.size_bytes) is not int
            or self.size_bytes < 1
        ):
            raise _error("artifact pin is not one exact project-relative byte identity")


class AuthenticatedSemanticGraphNumericProposalReceiptV1:
    """Opaque capability minted only after exact artifact and graph replay."""

    __slots__ = ("__weakref__",)

    def __new__(cls, token: object | None = None) -> Any:
        if token is not _MINT_TOKEN:
            raise TypeError("authenticated numeric proposal receipts are opaque")
        return super().__new__(cls)

    def __repr__(self) -> str:
        return "<AuthenticatedSemanticGraphNumericProposalReceiptV1 opaque>"


@dataclass(frozen=True, slots=True)
class _ReceiptPayload:
    project_root: Path
    registry_path: Path
    registry_bytes: bytes
    registry: dict[str, Any]
    crop_bytes_by_path: dict[str, bytes]
    predictions: list[dict[str, Any]]
    run_manifest: dict[str, Any]
    pins: dict[str, dict[str, Any]]
    historical_run_lineage: dict[str, Any]
    expected_run_commit: str
    selection_authority_commit: str
    receipt_id: str


_MINT_TOKEN = object()
_RECEIPTS: weakref.WeakKeyDictionary[
    AuthenticatedSemanticGraphNumericProposalReceiptV1, _ReceiptPayload
] = weakref.WeakKeyDictionary()


def _exact_dict(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise _error(f"{label} fields drifted")
    return value


def _strict_json(raw: bytes, label: str) -> Any:
    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise _error(f"{label} contains a duplicate JSON key")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise _error(f"{label} contains non-finite JSON number {value}")

    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=pairs_hook,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"{label} is not strict UTF-8 JSON") from exc


def _resolve_artifact(root: Path, relative: Path, label: str) -> Path:
    candidate = root / relative
    cursor = root
    for part in relative.parts:
        cursor /= part
        if cursor.is_symlink():
            raise _error(f"{label} path contains a symlink")
    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise _error(f"{label} escapes the project or is not a file")
    return resolved


def _stable_bytes(path: Path, label: str) -> bytes:
    try:
        before = path.stat()
        first = path.read_bytes()
        second = path.read_bytes()
        after = path.stat()
    except OSError as exc:
        raise _error(f"{label} cannot be read") from exc
    if (
        first != second
        or before.st_size != len(first)
        or after.st_size != len(first)
        or before.st_mtime_ns != after.st_mtime_ns
    ):
        raise _error(f"{label} changed while read")
    return first


def _make_in_project_replay_directory(root: Path, prefix: str) -> Path:
    """Create an unpredictable real directory directly under resolved root."""

    if not root.is_absolute() or not root.is_dir() or root.is_symlink():
        raise _error("numeric proposal replay project root is unsafe")
    try:
        directory = Path(tempfile.mkdtemp(prefix=prefix, dir=root))
        resolved = directory.resolve(strict=True)
    except OSError as exc:
        raise _error("numeric proposal replay directory cannot be created") from exc
    if directory.is_symlink() or resolved.parent != root or not resolved.is_dir():
        shutil.rmtree(directory, ignore_errors=True)
        raise _error("numeric proposal replay directory escaped project root")
    return resolved


def _read_pin(root: Path, pin: ArtifactPinV1, label: str) -> tuple[Path, bytes]:
    path = _resolve_artifact(root, pin.path, label)
    raw = _stable_bytes(path, label)
    if len(raw) != pin.size_bytes or sha256_bytes(raw) != pin.sha256:
        raise _error(f"{label} differs from its external byte pin")
    return path, raw


def _pin_record(pin: ArtifactPinV1) -> dict[str, Any]:
    return {
        "path": pin.path.as_posix(),
        "sha256": pin.sha256,
        "size_bytes": pin.size_bytes,
    }


def _git(root: Path, *args: str) -> bytes:
    try:
        return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True).stdout
    except subprocess.CalledProcessError as exc:
        raise _error(f"git provenance check failed: {' '.join(args)}") from exc


def _verify_git_execution_ledger(
    root: Path,
    run_commit: str,
    selection_commit: str,
    selection_path: Path,
    selection_raw: bytes,
) -> dict[str, Any]:
    if _COMMIT.fullmatch(run_commit) is None or _COMMIT.fullmatch(selection_commit) is None:
        raise _error("numeric reader run commit is not a full lowercase Git object ID")
    for commit, label in ((run_commit, "run"), (selection_commit, "selection authority")):
        resolved = _git(root, "rev-parse", "--verify", f"{commit}^{{commit}}").decode().strip()
        if resolved != commit:
            raise _error(f"numeric {label} commit does not resolve exactly")
    head = _git(root, "rev-parse", "HEAD").decode().strip()
    if _COMMIT.fullmatch(head) is None or _git(root, "status", "--porcelain"):
        raise _error("numeric selection authority requires a clean committed consumer HEAD")
    for ancestor, descendant, label in (
        (run_commit, selection_commit, "run-to-selection"),
        (selection_commit, head, "selection-to-consumer"),
    ):
        try:
            subprocess.run(
                ["git", "merge-base", "--is-ancestor", ancestor, descendant],
                cwd=root,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as exc:
            raise _error(f"numeric {label} commit ancestry is invalid") from exc
    run_tree = (
        _git(root, "rev-parse", f"{run_commit}:{_SOURCE_TREE_PATH.as_posix()}").decode().strip()
    )
    selection_tree = (
        _git(root, "rev-parse", f"{selection_commit}:{_SOURCE_TREE_PATH.as_posix()}")
        .decode()
        .strip()
    )
    head_tree = _git(root, "rev-parse", f"{head}:{_SOURCE_TREE_PATH.as_posix()}").decode().strip()
    if run_tree != selection_tree or run_tree != head_tree or _COMMIT.fullmatch(run_tree) is None:
        raise _error("bctc_ai source tree changed across run, selection, or replay")
    records = []
    for relative in _ENTRYPOINT_PATHS:
        path = _resolve_artifact(root, relative, "numeric implementation")
        current = _stable_bytes(path, f"numeric implementation {relative.as_posix()}")
        run_bytes = _git(root, "show", f"{run_commit}:{relative.as_posix()}")
        selection_bytes = _git(root, "show", f"{selection_commit}:{relative.as_posix()}")
        head_bytes = _git(root, "show", f"{head}:{relative.as_posix()}")
        if current != run_bytes or current != selection_bytes or current != head_bytes:
            raise _error(f"numeric entrypoint differs across run/selection/replay: {relative}")
        records.append(
            {
                "path": relative.as_posix(),
                "size_bytes": len(current),
                "sha256": sha256_bytes(current),
            }
        )
    selection_committed = _git(root, "show", f"{selection_commit}:{selection_path.as_posix()}")
    selection_at_head = _git(root, "show", f"{head}:{selection_path.as_posix()}")
    if selection_committed != selection_raw or selection_at_head != selection_raw:
        raise _error("selection authority bytes differ across selection and replay commits")
    return {
        "entrypoints": records,
        "selection_authority_commit": selection_commit,
        "clean_descendant_replay_validated_but_not_persisted": True,
        "source_tree": {
            "git_object_id": run_tree,
            "path": _SOURCE_TREE_PATH.as_posix(),
        },
    }


def _validate_selection_authority(
    value: Any,
    *,
    registry: ArtifactPinV1,
    predictions: ArtifactPinV1,
    run_manifest: ArtifactPinV1,
    expected_run_commit: str,
) -> dict[str, Any]:
    value = _exact_dict(value, _SELECTION_FIELDS, "numeric selection authority")
    artifacts = _exact_dict(
        value["artifacts"], {"predictions", "registry", "run_manifest"}, "selection artifacts"
    )
    for key, pin in (
        ("registry", registry),
        ("predictions", predictions),
        ("run_manifest", run_manifest),
    ):
        _exact_dict(artifacts[key], {"path", "sha256", "size_bytes"}, f"selection {key} pin")
        if not same_typed_json_v1(artifacts[key], _pin_record(pin)):
            raise _error(f"selection authority {key} pin differs from external pin")
    if (
        type(value["format_version"]) is not int
        or value["format_version"] != 1
        or value["state"] != _SELECTION_STATE
        or value["claim_boundary"] != _SELECTION_CLAIM_BOUNDARY
        or value["run_commit"] != expected_run_commit
        or type(value["cell_count"]) is not int
        or value["cell_count"] != 8
    ):
        raise _error("numeric selection authority identity or denominator drifted")
    return canonical_clone_v1(value)


def _validate_config_and_model(
    root: Path, model_cache: Path, run: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    config, config_path = load_numeric_reader_config(root, _CONFIG_PATH)
    expected_config_fields = {
        "allowed_semantics",
        "authority",
        "device",
        "forbidden_authority",
        "model",
        "network_during_inference",
        "policy",
        "precision",
        "runtime_paddleocr",
        "runtime_paddlepaddle",
        "runtime_paddlex",
        "runtime_python",
        "version",
    }
    expected_model_fields = {
        "cache_directory",
        "files",
        "license",
        "published_accuracy",
        "published_accuracy_scope",
        "repo_id",
        "revision",
        "weights_file",
        "weights_sha256",
        "weights_size_bytes",
    }
    if set(config) != expected_config_fields or set(config["model"]) != expected_model_fields:
        raise _error("numeric reader configuration schema drifted")
    config_raw = _stable_bytes(config_path, "numeric reader configuration")
    configuration = _exact_dict(
        run["configuration"],
        {"batch_size", "cpu_threads", "device", "network_policy", "path", "precision", "sha256"},
        "numeric run configuration",
    )
    if (
        configuration["path"] != _CONFIG_PATH.as_posix()
        or configuration["sha256"] != sha256_bytes(config_raw)
        or configuration["network_policy"] != "PROCESS_SOCKET_CONNECT_DENIED"
        or configuration["device"] != config["device"] != "cpu"
        or configuration["precision"] != config["precision"] != "fp32"
        or type(configuration["batch_size"]) is not int
        or configuration["batch_size"] < 1
        or type(configuration["cpu_threads"]) is not int
        or configuration["cpu_threads"] < 1
        or config["network_during_inference"] is not False
    ):
        raise _error("numeric reader configuration identity drifted")
    model_directory = model_cache.resolve() / "official_models" / config["model"]["cache_directory"]
    if model_cache.is_symlink() or model_directory.is_symlink():
        raise _error("numeric model cache may not be a symlink")
    runtime = _exact_dict(
        run["runtime"],
        {"model", "paddle_device", "paddleocr", "paddlepaddle", "paddlex"},
        "runtime",
    )
    try:
        model_record = verify_numeric_reader_model(model_directory, config)
    except (OSError, RuntimeError, ValueError) as exc:
        raise _error("numeric reader model snapshot cannot be authenticated") from exc
    expected_model_files = {item["path"] for item in config["model"]["files"]}
    actual_model_files = {
        path.relative_to(model_directory).as_posix()
        for path in model_directory.rglob("*")
        if path.is_file()
    }
    if (
        any(path.is_symlink() for path in model_directory.rglob("*"))
        or actual_model_files != expected_model_files
        or not same_typed_json_v1(runtime["model"], model_record)
    ):
        raise _error("numeric reader model snapshot drifted")
    if (
        runtime["paddlepaddle"] != config["runtime_paddlepaddle"]
        or runtime["paddleocr"] != config["runtime_paddleocr"]
        or runtime["paddlex"] != config["runtime_paddlex"]
        or runtime["paddle_device"] != "cpu"
    ):
        raise _error("numeric reader package or device provenance drifted")
    return config, model_record


def _validate_predictions(
    value: Any, registry: dict[str, Any], registry_directory: Path
) -> list[dict[str, Any]]:
    if type(value) is not list or len(value) != len(registry["cells"]):
        raise _error("numeric predictions changed the exact registry denominator")
    result: list[dict[str, Any]] = []
    for ordinal, (prediction, cell) in enumerate(zip(value, registry["cells"], strict=True)):
        _exact_dict(prediction, _PREDICTION_FIELDS, f"numeric prediction {ordinal}")
        score = prediction["reader_score"]
        crop_path = (registry_directory / cell["crop_path"]).resolve()
        if (
            prediction["cell_id"] != cell["cell_id"]
            or prediction["crop_path"] != crop_path.as_posix()
            or prediction["crop_sha256"] != cell["crop_sha256"]
            or type(prediction["raw_prediction"]) is not str
            or type(score) not in {int, float}
            or not math.isfinite(float(score))
            or not 0 <= float(score) <= 1
            or prediction["proposal_status"]
            != classify_numeric_prediction(prediction["raw_prediction"])
        ):
            raise _error(f"numeric prediction identity, order, or raw status drifted: {ordinal}")
        result.append(canonical_clone_v1(prediction))
    return result


def _aware_timestamp(value: Any, label: str) -> datetime:
    if type(value) is not str:
        raise _error(f"{label} is not a timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise _error(f"{label} is not an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise _error(f"{label} lacks a UTC offset")
    return parsed


def _validate_run_manifest(
    run: Any,
    *,
    root: Path,
    run_path: Path,
    predictions_pin: ArtifactPinV1,
    predictions_path: Path,
    registry_pin: ArtifactPinV1,
    registry: dict[str, Any],
    expected_run_commit: str,
) -> dict[str, Any]:
    run = _exact_dict(run, _RUN_FIELDS, "numeric run manifest")
    code = _exact_dict(run["code"], {"commit", "dirty"}, "numeric run code")
    crop_registry = _exact_dict(
        run["crop_registry"],
        {"cell_count", "path", "recognizer_input_fields", "sha256"},
        "numeric run crop registry",
    )
    artifacts = _exact_dict(run["artifacts"], {"predictions"}, "numeric run artifacts")
    prediction_ref = _exact_dict(
        artifacts["predictions"], {"path", "sha256", "size_bytes"}, "prediction artifact ref"
    )
    metrics = _exact_dict(
        run["metrics"],
        {"cell_count", "model_load_session_count", "proposal_status_counts", "wall_seconds"},
        "numeric run metrics",
    )
    if run_path.parent != predictions_path.parent:
        raise _error("numeric predictions are not beside their run manifest")
    expected_crop_registry = {
        "path": registry_pin.path.as_posix(),
        "sha256": registry_pin.sha256,
        "cell_count": len(registry["cells"]),
        "recognizer_input_fields": ["crop_path"],
    }
    expected_prediction_ref = {
        "path": predictions_path.relative_to(run_path.parent).as_posix(),
        "size_bytes": predictions_pin.size_bytes,
        "sha256": predictions_pin.sha256,
    }
    status_counts = metrics["proposal_status_counts"]
    if (
        type(run["format_version"]) is not int
        or run["format_version"] != 1
        or run["state"] != "NUMERIC_CELL_PROPOSALS_COMPLETE"
        or run["dataset_role"] != "CALIBRATION"
        or run["evidence_role"] != "INDEPENDENT_NUMERIC_CELL_PROPOSAL_ONLY"
        or run["confidence_policy"] != "NO_AUTOMATIC_TRUTH_MAPPING_OR_CONFIDENCE_PROMOTION"
        or not same_typed_json_v1(code, {"commit": expected_run_commit, "dirty": False})
        or not same_typed_json_v1(crop_registry, expected_crop_registry)
        or not same_typed_json_v1(prediction_ref, expected_prediction_ref)
        or type(metrics["cell_count"]) is not int
        or metrics["cell_count"] != len(registry["cells"])
        or type(metrics["model_load_session_count"]) is not int
        or metrics["model_load_session_count"] != 1
        or type(metrics["wall_seconds"]) not in {int, float}
        or not math.isfinite(float(metrics["wall_seconds"]))
        or metrics["wall_seconds"] < 0
        or type(status_counts) is not dict
        or not status_counts
        or not set(status_counts).issubset(_PROPOSAL_STATUSES)
        or any(type(count) is not int or count < 1 for count in status_counts.values())
        or sum(status_counts.values()) != len(registry["cells"])
    ):
        raise _error("numeric run identity, lineage, or denominator drifted")
    started = _aware_timestamp(run["started_at"], "numeric run start")
    completed = _aware_timestamp(run["completed_at"], "numeric run completion")
    if completed < started:
        raise _error("numeric run completion predates its start")
    expected_files = {run_path.name, predictions_path.name}
    actual_files = {item.name for item in run_path.parent.iterdir()}
    if (
        run_path.name != "run_manifest.json"
        or predictions_path.name != "predictions.json"
        or actual_files != expected_files
        or any(item.is_symlink() or not item.is_file() for item in run_path.parent.iterdir())
    ):
        raise _error("numeric run directory contains an unsafe or undeclared artifact")
    return canonical_clone_v1(run)


def _snapshot_registry_crops(registry: dict[str, Any], registry_path: Path) -> dict[str, bytes]:
    directory = registry_path.parent
    expected_paths = {cell["crop_path"] for cell in registry["cells"]}
    if any(
        type(relative) is not str
        or Path(relative).is_absolute()
        or ".." in Path(relative).parts
        or not relative.startswith("crops/")
        for relative in expected_paths
    ):
        raise _error("numeric registry contains an unsafe crop path")
    entries = {item.name for item in directory.iterdir()}
    if entries != {"crop_registry.json", "crops"} or (directory / "crops").is_symlink():
        raise _error("numeric registry directory contains undeclared artifacts")
    actual_paths = {
        item.relative_to(directory).as_posix()
        for item in (directory / "crops").rglob("*")
        if item.is_file()
    }
    if actual_paths != expected_paths or any(
        item.is_symlink() for item in (directory / "crops").rglob("*")
    ):
        raise _error("numeric registry crop set drifted")
    snapshots: dict[str, bytes] = {}
    for cell in registry["cells"]:
        relative = cell["crop_path"]
        path = (directory / relative).resolve(strict=True)
        raw = _stable_bytes(path, f"numeric crop {cell['cell_id']}")
        if len(raw) != cell["crop_size_bytes"] or sha256_bytes(raw) != cell["crop_sha256"]:
            raise _error(f"numeric crop bytes drifted: {cell['cell_id']}")
        snapshots[relative] = raw
    return snapshots


def _replay_registry_snapshot(
    payload: _ReceiptPayload,
    semantic_graph_v2: Any,
    source_projection_v2: Any,
    semantic_page_binding_v2: Any,
    authenticated_transformer_receipt_v2: Any,
    family_spec: FamilySpecV1,
    family_specs_for_collision_scope: tuple[FamilySpecV1, ...],
) -> dict[str, Any]:
    temporary = _make_in_project_replay_directory(
        payload.project_root, ".numeric-proposal-receipt-replay-"
    )
    try:
        (temporary / "crops").mkdir()
        (temporary / "crop_registry.json").write_bytes(payload.registry_bytes)
        for relative, raw in payload.crop_bytes_by_path.items():
            target = temporary / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        try:
            return validate_semantic_graph_numeric_cell_crop_registry_replay_v1(
                canonical_clone_v1(payload.registry),
                temporary,
                payload.project_root,
                semantic_graph_v2,
                source_projection_v2,
                semantic_page_binding_v2,
                authenticated_transformer_receipt_v2,
                family_spec,
                family_specs_for_collision_scope,
            )
        except ValueError as exc:
            raise _error("semantic graph numeric registry replay failed") from exc
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def _receipt_payload(
    receipt: AuthenticatedSemanticGraphNumericProposalReceiptV1,
) -> _ReceiptPayload:
    if type(receipt) is not AuthenticatedSemanticGraphNumericProposalReceiptV1:
        raise _error("numeric proposal receipt is not an opaque authenticated capability")
    try:
        return _RECEIPTS[receipt]
    except KeyError as exc:
        raise _error("numeric proposal receipt was not minted by this process") from exc


def authenticate_semantic_graph_numeric_proposals_v1(
    project_root: Path,
    *,
    registry: ArtifactPinV1,
    predictions: ArtifactPinV1,
    run_manifest: ArtifactPinV1,
    selection_authority: ArtifactPinV1,
    expected_run_commit: str,
    expected_selection_authority_commit: str,
    model_cache: Path,
    semantic_graph_v2: Any,
    source_projection_v2: Any,
    semantic_page_binding_v2: Any,
    authenticated_transformer_receipt_v2: Any,
    family_spec: FamilySpecV1,
    family_specs_for_collision_scope: tuple[FamilySpecV1, ...],
) -> AuthenticatedSemanticGraphNumericProposalReceiptV1:
    """Authenticate pinned persisted proposals and mint an opaque receipt."""

    root = project_root.resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise _error("project root is unsafe")
    if len({registry.path, predictions.path, run_manifest.path, selection_authority.path}) != 4:
        raise _error("numeric artifact pins must address four distinct files")
    registry_path, registry_raw = _read_pin(root, registry, "numeric crop registry")
    predictions_path, predictions_raw = _read_pin(root, predictions, "numeric predictions")
    run_path, run_raw = _read_pin(root, run_manifest, "numeric run manifest")
    selection_path, selection_raw = _read_pin(
        root, selection_authority, "numeric selection authority"
    )
    if registry_path.name != "crop_registry.json":
        raise _error("numeric crop registry filename drifted")
    registry_value = _strict_json(registry_raw, "numeric crop registry")
    predictions_value = _strict_json(predictions_raw, "numeric predictions")
    run_value = _strict_json(run_raw, "numeric run manifest")
    selection_value = _validate_selection_authority(
        _strict_json(selection_raw, "numeric selection authority"),
        registry=registry,
        predictions=predictions,
        run_manifest=run_manifest,
        expected_run_commit=expected_run_commit,
    )
    try:
        replayed = validate_semantic_graph_numeric_cell_crop_registry_replay_v1(
            registry_value,
            registry_path.parent,
            root,
            semantic_graph_v2,
            source_projection_v2,
            semantic_page_binding_v2,
            authenticated_transformer_receipt_v2,
            family_spec,
            family_specs_for_collision_scope,
        )
    except ValueError as exc:
        raise _error("semantic graph numeric crop registry failed exact replay") from exc
    if (
        replayed.get("format_version") != 3
        or replayed.get("policy") != CROP_POLICY
        or replayed.get("geometry_authority") != CROP_GEOMETRY_AUTHORITY
        or replayed.get("claim_boundary") != CROP_CLAIM_BOUNDARY
        or replayed.get("metrics", {}).get("cell_count") != 8
        or len(replayed.get("cells", ())) != 8
    ):
        raise _error("numeric proposal v1 requires the exact eight-cell v3 crop seam")
    crop_snapshots = _snapshot_registry_crops(replayed, registry_path)
    prediction_records = _validate_predictions(predictions_value, replayed, registry_path.parent)
    run_record = _validate_run_manifest(
        run_value,
        root=root,
        run_path=run_path,
        predictions_pin=predictions,
        predictions_path=predictions_path,
        registry_pin=registry,
        registry=replayed,
        expected_run_commit=expected_run_commit,
    )
    expected_counts = dict(
        sorted(Counter(item["proposal_status"] for item in prediction_records).items())
    )
    if run_record["metrics"]["proposal_status_counts"] != expected_counts:
        raise _error("numeric run proposal-status denominator drifted")
    historical_run_lineage = _verify_git_execution_ledger(
        root,
        expected_run_commit,
        expected_selection_authority_commit,
        selection_authority.path,
        selection_raw,
    )
    _, model = _validate_config_and_model(root, model_cache, run_record)
    # Re-read every externally pinned artifact after replay/model checks.  This
    # prevents a path swap during authentication from entering the receipt.
    for pin, expected, label in (
        (registry, registry_raw, "numeric crop registry"),
        (predictions, predictions_raw, "numeric predictions"),
        (run_manifest, run_raw, "numeric run manifest"),
        (selection_authority, selection_raw, "numeric selection authority"),
    ):
        _, current = _read_pin(root, pin, label)
        if current != expected:
            raise _error(f"{label} changed during authentication")
    if _snapshot_registry_crops(replayed, registry_path) != crop_snapshots:
        raise _error("numeric crop bytes changed during authentication")
    pins = {
        "predictions": _pin_record(predictions),
        "registry": {**_pin_record(registry), "registry_id": replayed["registry_id"]},
        "run_manifest": _pin_record(run_manifest),
        "selection_authority": _pin_record(selection_authority),
    }
    receipt_material = {
        "expected_run_commit": expected_run_commit,
        "expected_selection_authority_commit": expected_selection_authority_commit,
        "historical_run_lineage": historical_run_lineage,
        "model": model,
        "pins": pins,
        "semantic_graph": replayed["semantic_graph"],
        "source_projection_sha256": replayed["source_projection_sha256"],
        "semantic_page_binding_sha256": replayed["semantic_page_binding_sha256"],
    }
    receipt_id = f"sgnpav1:receipt:{canonical_json_sha256_v1(receipt_material)}"
    payload = _ReceiptPayload(
        project_root=root,
        registry_path=registry_path,
        registry_bytes=bytes(registry_raw),
        registry=canonical_clone_v1(replayed),
        crop_bytes_by_path=dict(crop_snapshots),
        predictions=canonical_clone_v1(prediction_records),
        run_manifest=canonical_clone_v1(run_record),
        pins=canonical_clone_v1(pins),
        historical_run_lineage=canonical_clone_v1(
            {"code": historical_run_lineage, "model": model, "selection": selection_value}
        ),
        expected_run_commit=expected_run_commit,
        selection_authority_commit=expected_selection_authority_commit,
        receipt_id=receipt_id,
    )
    receipt = AuthenticatedSemanticGraphNumericProposalReceiptV1(_MINT_TOKEN)
    _RECEIPTS[receipt] = payload
    return receipt


def _verification_id(value: dict[str, Any]) -> str:
    payload = canonical_clone_v1(value)
    payload.pop("verification_id", None)
    return f"sgnpvv1:verification:{canonical_json_sha256_v1(payload)}"


def _build_verification(payload: _ReceiptPayload) -> dict[str, Any]:
    try:
        fused = _verify_numeric_cell_proposals(
            canonical_clone_v1(payload.registry),
            canonical_clone_v1(payload.predictions),
            allow_semantic_graph_v3=True,
        )
    except NumericCellVerificationError as exc:
        raise _error("authenticated numeric proposal fusion failed") from exc
    fused_by_id = {cell["cell_id"]: cell for cell in fused["cells"]}
    records = []
    for source in payload.registry["cells"]:
        fused_cell = fused_by_id[source["cell_id"]]
        record = {
            "cell_id": source["cell_id"],
            "page": source["page"],
            "row_ordinal": source["row_ordinal"],
            "axis_ordinal": source["axis_ordinal"],
            "axis_id": source["axis_id"],
            "source_graph_node_id": source["source_graph_node_id"],
            "source_evidence_node_id": source["source_evidence_node_id"],
            "source_atom_id": source["source_atom_id"],
            "source_line_index": source["source_line_index"],
            "crop_path": source["crop_path"],
            "crop_size_bytes": source["crop_size_bytes"],
            "crop_sha256": source["crop_sha256"],
            "primary": fused_cell["primary"],
            "challenger": fused_cell["challenger"],
            "verification_status": fused_cell["verification_status"],
            "decision": fused_cell["decision"],
            "selected_raw_value": fused_cell["selected_raw_value"],
            "normalized_numeric_value": fused_cell["normalized_numeric_value"],
            "final_value_status": fused_cell["final_value_status"],
        }
        _exact_dict(record, _RESULT_CELL_FIELDS, "numeric verification cell")
        records.append(record)
    verified = sum(cell["verification_status"] == "VERIFIED_OBSERVED_VALUE" for cell in records)
    metrics = canonical_clone_v1(fused["metrics"])
    metrics["authenticated_cell_count"] = len(records)
    metrics["exact_eight_cell_agreement"] = verified == 8
    result = {
        "format_version": FORMAT_VERSION,
        "policy": POLICY,
        "authority": AUTHORITY,
        "claim_boundary": CLAIM_BOUNDARY,
        "status": (
            "COMPLETE_WITH_EXACT_EIGHT_CELL_AGREEMENT"
            if verified == 8
            else "COMPLETE_WITH_UNRESOLVED_NUMERIC_CANDIDATES"
        ),
        "inputs": {
            "authenticated_receipt_id": payload.receipt_id,
            "expected_run_commit": payload.expected_run_commit,
            "expected_selection_authority_commit": payload.selection_authority_commit,
            "historical_run_lineage": canonical_clone_v1(payload.historical_run_lineage),
            "pins": canonical_clone_v1(payload.pins),
            "semantic_graph": canonical_clone_v1(payload.registry["semantic_graph"]),
            "semantic_page_binding_sha256": payload.registry["semantic_page_binding_sha256"],
            "source_projection_sha256": payload.registry["source_projection_sha256"],
        },
        "metrics": metrics,
        "safety": dict(_SAFETY),
        "cells": records,
    }
    result["verification_id"] = _verification_id(result)
    return _validate_result(result)


def _validate_result(value: Any) -> dict[str, Any]:
    value = _exact_dict(value, _RESULT_FIELDS, "numeric verification result")
    inputs = _exact_dict(value["inputs"], _RESULT_INPUT_FIELDS, "verification inputs")
    historical = _exact_dict(
        inputs["historical_run_lineage"],
        {"code", "model", "selection"},
        "historical run lineage",
    )
    _exact_dict(
        historical["code"],
        {
            "clean_descendant_replay_validated_but_not_persisted",
            "entrypoints",
            "selection_authority_commit",
            "source_tree",
        },
        "historical code lineage",
    )
    _exact_dict(historical["selection"], _SELECTION_FIELDS, "historical selection authority")
    _exact_dict(inputs["semantic_graph"], {"graph_id", "sha256"}, "semantic graph ref")
    pins = _exact_dict(
        inputs["pins"],
        {"predictions", "registry", "run_manifest", "selection_authority"},
        "verification pins",
    )
    _exact_dict(pins["predictions"], {"path", "sha256", "size_bytes"}, "prediction pin")
    _exact_dict(pins["run_manifest"], {"path", "sha256", "size_bytes"}, "run pin")
    _exact_dict(
        pins["selection_authority"],
        {"path", "sha256", "size_bytes"},
        "selection authority pin",
    )
    _exact_dict(pins["registry"], {"path", "registry_id", "sha256", "size_bytes"}, "registry pin")
    _exact_dict(value["metrics"], _RESULT_METRIC_FIELDS, "verification metrics")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["policy"] != POLICY
        or value["authority"] != AUTHORITY
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["safety"] != _SAFETY
        or value["verification_id"] != _verification_id(value)
        or type(value["cells"]) is not list
        or len(value["cells"]) != 8
        or any(
            type(cell) is not dict or set(cell) != _RESULT_CELL_FIELDS for cell in value["cells"]
        )
    ):
        raise _error("numeric verification result shape or identity drifted")
    for cell in value["cells"]:
        _exact_dict(cell["primary"], _PRIMARY_FIELDS, "verification primary")
        challenger = _exact_dict(cell["challenger"], _CHALLENGER_FIELDS, "verification challenger")
        if (
            type(challenger["reader_score"]) is not float
            or not math.isfinite(challenger["reader_score"])
            or not 0 <= challenger["reader_score"] <= 1
        ):
            raise _error("verification challenger score is invalid")
    return canonical_clone_v1(value)


def verify_semantic_graph_numeric_proposals_v1(
    receipt: AuthenticatedSemanticGraphNumericProposalReceiptV1,
    project_root: Path,
    *,
    semantic_graph_v2: Any,
    source_projection_v2: Any,
    semantic_page_binding_v2: Any,
    authenticated_transformer_receipt_v2: Any,
    family_spec: FamilySpecV1,
    family_specs_for_collision_scope: tuple[FamilySpecV1, ...],
) -> dict[str, Any]:
    """Replay the opaque receipt inputs and fuse exact numeric candidates."""

    payload = _receipt_payload(receipt)
    if project_root.resolve(strict=True) != payload.project_root:
        raise _error("numeric proposal receipt belongs to another project root")
    replayed = _replay_registry_snapshot(
        payload,
        semantic_graph_v2,
        source_projection_v2,
        semantic_page_binding_v2,
        authenticated_transformer_receipt_v2,
        family_spec,
        family_specs_for_collision_scope,
    )
    if not same_typed_json_v1(replayed, payload.registry):
        raise _error("numeric proposal receipt registry differs from replay")
    return _build_verification(payload)


def validate_semantic_graph_numeric_verification_replay_v1(
    persisted: Any,
    receipt: AuthenticatedSemanticGraphNumericProposalReceiptV1,
    project_root: Path,
    *,
    semantic_graph_v2: Any,
    source_projection_v2: Any,
    semantic_page_binding_v2: Any,
    authenticated_transformer_receipt_v2: Any,
    family_spec: FamilySpecV1,
    family_specs_for_collision_scope: tuple[FamilySpecV1, ...],
) -> dict[str, Any]:
    """Typed-compare a persisted result with a fresh opaque-receipt replay."""

    candidate = _validate_result(persisted)
    replayed = verify_semantic_graph_numeric_proposals_v1(
        receipt,
        project_root,
        semantic_graph_v2=semantic_graph_v2,
        source_projection_v2=source_projection_v2,
        semantic_page_binding_v2=semantic_page_binding_v2,
        authenticated_transformer_receipt_v2=authenticated_transformer_receipt_v2,
        family_spec=family_spec,
        family_specs_for_collision_scope=family_specs_for_collision_scope,
    )
    if not same_typed_json_v1(candidate, replayed):
        raise _error("persisted numeric verification differs from exact receipt replay")
    return replayed
