"""Authenticate the all-line PP-OCRv6 numeric cache and expose selected cells.

The persisted reader output remains one complete anonymous sample axis.  This
module authenticates that axis, joins source geometry only after inference, and
allows a family evaluator to request a sorted set of exact source-line cells.
Only those selected immutable crops are parsed into typed numeric evidence.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import weakref
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bctc_ai.evaluation import family_first_numeric_cell_evidence_v1 as evidence_v1
from bctc_ai.evaluation import family_first_semantic_label_archive_v1 as archive_v1
from bctc_ai.ocr import family_first_ppocrv6_numeric_runner_v1 as runner_v1
from bctc_ai.ocr import ppocrv6_numeric_reference_blind_kernel_v1 as kernel_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "AuthenticatedFamilyFirstPPocrV6NumericIndexV1",
    "FamilyFirstPPocrV6NumericIndexV1Error",
    "authenticate_family_first_ppocrv6_numeric_index_v1",
    "finalize_authenticated_family_first_ppocrv6_numeric_index_v1",
    "project_authenticated_family_first_ppocrv6_numeric_index_v1",
    "read_authenticated_family_first_ppocrv6_numeric_document_v1",
    "read_authenticated_family_first_ppocrv6_numeric_evidence_batch_v1",
]


INDEX_ROOT = Path("output/calibration/family-first-ppocrv6-numeric-cache-v1/verified-index")
RECEIPT_PATH = INDEX_ROOT / "verification-receipt.json"
FORMAT_VERSION = "FAMILY_FIRST_PPOCRV6_NUMERIC_INDEX_RECEIPT_V1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_RECEIPT_FIELDS = {
    "archive_id",
    "authority",
    "batch_id",
    "format_version",
    "metrics",
    "numeric_axis_sha256",
    "plan_id",
    "proposal_ref",
    "receipt_id",
    "run_id",
    "run_ref",
    "state",
}
_AUTHORITY = {
    "accounting_authority": False,
    "all_reader_outputs_preserved": True,
    "blank_means_zero": False,
    "crop_bound_numeric_recognition_evidence_available": True,
    "dash_may_be_typed_as_zero_only_after_selected_crop_replay": True,
    "mapping_authority": False,
    "period_or_unit_authority": False,
    "schema_authority": False,
    "semantic_text_authority": False,
}
_SELECTION_FIELDS = {"document_ordinal", "line_ordinal", "physical_page"}


class FamilyFirstPPocrV6NumericIndexV1Error(RuntimeError):
    """The numeric run, archive join, selected crop, or receipt drifted."""


def _error(message: str) -> FamilyFirstPPocrV6NumericIndexV1Error:
    return FamilyFirstPPocrV6NumericIndexV1Error(message)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


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


def _matches(payload: bytes, reference: Any, label: str) -> None:
    try:
        expected = archive_v1._ref(reference, label)
    except archive_v1.FamilyFirstSemanticLabelArchiveV1Error as exc:
        raise _error(f"{label} reference drifted") from exc
    if len(payload) != expected["size_bytes"] or _sha(payload) != expected["sha256"]:
        raise _error(f"{label} bytes differ from their content reference")


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


def _git_ledger(root: Path, binding: Any) -> str:
    head = archive_v1._clean_head(root)
    expected_paths = [
        runner_v1._ARCHIVE_PATH.as_posix(),
        runner_v1._KERNEL_PATH.as_posix(),
        runner_v1._IMPLEMENTATION_PATH.as_posix(),
        runner_v1._ORCHESTRATOR_PATH.as_posix(),
        runner_v1._INDEX_PATH.as_posix(),
        runner_v1._CONFIG_PATH.as_posix(),
    ]
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
        raise _error("formal numeric Git binding drifted")
    run_commit = binding["commit"]
    try:
        archive_v1._git(root, "merge-base", "--is-ancestor", run_commit, head)
    except archive_v1.FamilyFirstSemanticLabelArchiveV1Error as exc:
        raise _error("formal numeric run commit is not an ancestor of HEAD") from exc
    for raw in binding["implementation_refs"]:
        reference = archive_v1._ref(raw, "formal numeric trust file")
        committed = archive_v1._git(root, "show", f"{run_commit}:{reference['path']}")
        current = archive_v1._git(root, "show", f"{head}:{reference['path']}")
        disk = _root_bytes(root, Path(reference["path"]), "formal numeric trust file")
        _matches(committed, reference, "formal numeric committed trust file")
        if committed != current or committed != disk:
            raise _error("formal numeric trust file changed on the descendant chain")
    run_tree = (
        archive_v1._git(root, "rev-parse", f"{run_commit}:src/bctc_ai")
        .decode("ascii", errors="strict")
        .strip()
    )
    current_tree = (
        archive_v1._git(root, "rev-parse", f"{head}:src/bctc_ai")
        .decode("ascii", errors="strict")
        .strip()
    )
    if run_tree != binding["source_tree_oid"] or current_tree != run_tree:
        raise _error("formal numeric source tree changed after inference")
    if archive_v1._clean_head(root) != head:
        raise _error("Git HEAD/worktree changed during numeric ledger replay")
    return head


def _proposal_iterator(payload: bytes, expected_count: int):
    offset = 0
    ordinal = 0
    while offset < len(payload):
        end = payload.find(b"\n", offset)
        if end < 0:
            raise _error("numeric proposal JSONL has one incomplete final line")
        raw = payload[offset : end + 1]
        ordinal += 1
        try:
            value = json.loads(raw.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _error("numeric proposal JSONL is not strict JSON") from exc
        try:
            proposal = runner_v1._validate_result(value, ordinal)
        except runner_v1.FamilyFirstPPocrV6NumericRunnerV1Error as exc:
            raise _error("numeric proposal shape drifted") from exc
        if raw != canonical_json_bytes_v1(proposal):
            raise _error("numeric proposal JSONL line is not canonical")
        yield offset, end + 1, proposal
        offset = end + 1
    if ordinal != expected_count:
        raise _error("numeric proposal JSONL denominator drifted")


def _validate_run(
    root: Path,
    archive_state: Any,
    archive_manifest: dict[str, Any],
    batch: dict[str, Any],
    plan: dict[str, Any],
) -> tuple[dict[str, Any], bytes, bytes, str, list[tuple[int, int]]]:
    expected_listing = sorted(
        [runner_v1._ATTEMPT_NAME, runner_v1._PROPOSAL_NAME, runner_v1._RUN_NAME]
    )
    if _directory_listing(root, runner_v1.RUN_ROOT, "numeric run root") != expected_listing:
        raise _error("formal numeric run directory listing drifted")
    attempt_payload = _root_bytes(
        root, runner_v1.RUN_ROOT / runner_v1._ATTEMPT_NAME, "numeric attempt"
    )
    proposal_payload = _root_bytes(
        root, runner_v1.RUN_ROOT / runner_v1._PROPOSAL_NAME, "numeric proposals"
    )
    run_payload = _root_bytes(
        root, runner_v1.RUN_ROOT / runner_v1._RUN_NAME, "numeric run manifest"
    )
    attempt = _canonical_object(attempt_payload, "numeric attempt")
    run = _canonical_object(run_payload, "numeric run manifest")
    if (
        set(attempt)
        != {"attempt_id", "claim_boundary", "format_version", "preflight", "started_at", "state"}
        or attempt["format_version"] != runner_v1.ATTEMPT_FORMAT_VERSION
        or attempt["state"] != "FORMAL_ATTEMPT_STARTED_NO_RESUME"
        or type(attempt["preflight"]) is not dict
    ):
        raise _error("formal numeric attempt contract drifted")
    preflight = attempt["preflight"]
    if attempt["attempt_id"] != "ffpnrv1:attempt:" + canonical_json_sha256_v1(preflight):
        raise _error("formal numeric attempt identity drifted")
    expected_run_fields = {
        "artifacts",
        "attempt_id",
        "completed_at",
        "execution_counts",
        "execution_policy",
        "experiment_id",
        "format_version",
        "git_binding",
        "input",
        "metrics",
        "run_id",
        "runtime",
        "safety",
        "started_at",
        "state",
    }
    if (
        set(run) != expected_run_fields
        or run["format_version"] != runner_v1.RUN_FORMAT_VERSION
        or run["experiment_id"] != runner_v1.EXPERIMENT_ID
        or run["state"] != "REFERENCE_BLIND_PPOCRV6_NUMERIC_PROPOSAL_RUN_COMPLETE"
        or run["attempt_id"] != attempt["attempt_id"]
        or run["started_at"] != attempt["started_at"]
        or not same_typed_json_v1(run["execution_policy"], runner_v1._EXECUTION_POLICY)
        or not same_typed_json_v1(run["safety"], runner_v1._SAFETY)
    ):
        raise _error("formal numeric run identity/policy drifted")
    material = canonical_clone_v1(run)
    run_id = material.pop("run_id")
    if run_id != "ffpnrv1:run:" + canonical_json_sha256_v1(material):
        raise _error("formal numeric run hash identity drifted")
    projection = {
        "archive_id": archive_manifest["archive_id"],
        "batch_id": batch["batch_id"],
        "plan_id": plan["plan_id"],
        "sample_count": batch["sample_count"],
    }
    if not same_typed_json_v1(run["input"], projection):
        raise _error("formal numeric archive input lineage drifted")
    expected_preflight_fields = {
        "archive_id",
        "batch_id",
        "configuration_ref",
        "execution_policy",
        "experiment_id",
        "git_binding",
        "model",
        "plan_id",
        "sample_count",
    }
    if (
        set(preflight) != expected_preflight_fields
        or preflight["archive_id"] != projection["archive_id"]
        or preflight["batch_id"] != projection["batch_id"]
        or preflight["plan_id"] != projection["plan_id"]
        or preflight["sample_count"] != projection["sample_count"]
        or preflight["experiment_id"] != runner_v1.EXPERIMENT_ID
        or not same_typed_json_v1(preflight["execution_policy"], runner_v1._EXECUTION_POLICY)
        or not same_typed_json_v1(preflight["git_binding"], run["git_binding"])
        or type(preflight["configuration_ref"]) is not dict
        or preflight["configuration_ref"].get("path") != runner_v1._CONFIG_PATH.as_posix()
    ):
        raise _error("formal numeric preflight cross-link drifted")
    if type(run["artifacts"]) is not dict or set(run["artifacts"]) != {
        "attempt",
        "numeric_proposals",
    }:
        raise _error("formal numeric artifact denominator drifted")
    _matches(attempt_payload, run["artifacts"]["attempt"], "numeric attempt")
    _matches(proposal_payload, run["artifacts"]["numeric_proposals"], "numeric proposals")
    if (
        run["artifacts"]["attempt"]["path"]
        != f"{runner_v1.RUN_ROOT.as_posix()}/{runner_v1._ATTEMPT_NAME}"
        or run["artifacts"]["numeric_proposals"]["path"]
        != f"{runner_v1.RUN_ROOT.as_posix()}/{runner_v1._PROPOSAL_NAME}"
    ):
        raise _error("formal numeric artifact path drifted")
    metric_subset = {
        "model_load_seconds": run["metrics"].get("model_load_seconds"),
        "total_wall_seconds": run["metrics"].get("total_wall_seconds"),
    }
    runtime, counts, metrics = runner_v1._validate_kernel_outputs(
        run["runtime"], run["execution_counts"], metric_subset, sample_count=batch["sample_count"]
    )
    if (
        not same_typed_json_v1(runtime, run["runtime"])
        or not same_typed_json_v1(counts, run["execution_counts"])
        or type(run["metrics"]) is not dict
        or set(run["metrics"])
        != {"empty_prediction_count", "model_load_seconds", "sample_count", "total_wall_seconds"}
        or type(run["metrics"]["empty_prediction_count"]) is not int
        or not 0 <= run["metrics"]["empty_prediction_count"] <= batch["sample_count"]
        or type(run["metrics"]["sample_count"]) is not int
        or run["metrics"]["sample_count"] != batch["sample_count"]
    ):
        raise _error("formal numeric runtime/metrics cross-link drifted")
    head = _git_ledger(root, run["git_binding"])
    configuration_payload = _root_bytes(root, runner_v1._CONFIG_PATH, "numeric runtime config")
    _matches(configuration_payload, preflight["configuration_ref"], "numeric runtime config")
    live_model, _directory = kernel_v1._recognizer_projection(root, archive_state.model_cache)
    if not same_typed_json_v1(live_model, preflight["model"]) or not same_typed_json_v1(
        live_model, run["runtime"]["model"]
    ):
        raise _error("formal numeric recognizer model lineage drifted")
    empty_count = 0
    offsets: list[tuple[int, int]] = []
    for start, stop, proposal in _proposal_iterator(proposal_payload, batch["sample_count"]):
        sample = batch["samples"][len(offsets)]
        if (
            proposal["sample_id"] != sample["sample_id"]
            or proposal["crop_sha256"] != sample["crop_ref"]["sha256"]
        ):
            raise _error("formal numeric proposal/crop axis cross-link drifted")
        empty_count += proposal["raw_prediction"] == ""
        offsets.append((start, stop))
    if empty_count != run["metrics"]["empty_prediction_count"]:
        raise _error("formal numeric empty-output denominator drifted")
    if (
        _root_bytes(root, runner_v1.RUN_ROOT / runner_v1._RUN_NAME, "numeric run manifest")
        != run_payload
        or _root_bytes(root, runner_v1.RUN_ROOT / runner_v1._PROPOSAL_NAME, "numeric proposals")
        != proposal_payload
        or archive_v1._clean_head(root) != head
    ):
        raise _error("formal numeric artifacts/Git changed during authentication")
    return run, run_payload, proposal_payload, head, offsets


def _metrics(plan: dict[str, Any], batch: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_count": len(plan["documents"]),
        "empty_prediction_count": run["metrics"]["empty_prediction_count"],
        "page_count": sum(item["page_count"] for item in plan["documents"]),
        "sample_count": batch["sample_count"],
    }


def _receipt(
    archive_manifest: dict[str, Any],
    batch: dict[str, Any],
    plan: dict[str, Any],
    run: dict[str, Any],
    run_payload: bytes,
    proposal_payload: bytes,
) -> dict[str, Any]:
    axis = hashlib.sha256()
    for _start, _stop, proposal in _proposal_iterator(proposal_payload, batch["sample_count"]):
        axis.update(
            canonical_json_bytes_v1(
                {
                    "crop_sha256": proposal["crop_sha256"],
                    "raw_prediction": proposal["raw_prediction"],
                    "reader_score": proposal["reader_score"],
                    "sample_id": proposal["sample_id"],
                }
            )
        )
    material = {
        "archive_id": archive_manifest["archive_id"],
        "authority": canonical_clone_v1(_AUTHORITY),
        "batch_id": batch["batch_id"],
        "format_version": FORMAT_VERSION,
        "metrics": _metrics(plan, batch, run),
        "numeric_axis_sha256": axis.hexdigest(),
        "plan_id": plan["plan_id"],
        "proposal_ref": canonical_clone_v1(run["artifacts"]["numeric_proposals"]),
        "run_id": run["run_id"],
        "run_ref": {
            "path": f"{runner_v1.RUN_ROOT.as_posix()}/{runner_v1._RUN_NAME}",
            "sha256": _sha(run_payload),
            "size_bytes": len(run_payload),
        },
        "state": "VERIFIED_COMPLETE_ORDERED_PPOCRV6_NUMERIC_PROPOSAL_AXIS",
    }
    return _validate_receipt(
        {**material, "receipt_id": "ffpniv1:receipt:" + canonical_json_sha256_v1(material)}
    )


def _validate_receipt(value: Any) -> dict[str, Any]:
    metrics = value.get("metrics") if type(value) is dict else None
    if (
        type(value) is not dict
        or set(value) != _RECEIPT_FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["state"] != "VERIFIED_COMPLETE_ORDERED_PPOCRV6_NUMERIC_PROPOSAL_AXIS"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(metrics) is not dict
        or set(metrics)
        != {"document_count", "empty_prediction_count", "page_count", "sample_count"}
        or any(type(metrics[field]) is not int for field in metrics)
        or metrics["document_count"] <= 0
        or metrics["page_count"] <= 0
        or metrics["sample_count"] <= 0
        or not 0 <= metrics["empty_prediction_count"] <= metrics["sample_count"]
        or type(value["numeric_axis_sha256"]) is not str
        or _SHA256.fullmatch(value["numeric_axis_sha256"]) is None
        or type(value["archive_id"]) is not str
        or not value["archive_id"].startswith("ffslav1:archive:")
        or type(value["batch_id"]) is not str
        or not value["batch_id"].startswith("ffslcv1:batch:")
        or type(value["plan_id"]) is not str
        or not value["plan_id"].startswith("ffslpv1:plan:")
        or type(value["run_id"]) is not str
        or not value["run_id"].startswith("ffpnrv1:run:")
    ):
        raise _error("numeric index receipt contract drifted")
    try:
        archive_v1._ref(value["proposal_ref"], "numeric proposal receipt ref")
        archive_v1._ref(value["run_ref"], "numeric run receipt ref")
    except archive_v1.FamilyFirstSemanticLabelArchiveV1Error as exc:
        raise _error("numeric index receipt artifact reference drifted") from exc
    material = canonical_clone_v1(value)
    receipt_id = material.pop("receipt_id")
    if receipt_id != "ffpniv1:receipt:" + canonical_json_sha256_v1(material):
        raise _error("numeric index receipt identity drifted")
    return canonical_clone_v1(value)


def finalize_authenticated_family_first_ppocrv6_numeric_index_v1(
    project_root: Path,
    archive_capability: archive_v1.AuthenticatedFamilyFirstSemanticLabelArchiveV1,
) -> dict[str, Any]:
    """Validate the complete run and publish one no-replace receipt."""

    root = archive_v1._root(project_root)
    state, archive_manifest, batch, plan, _private = archive_v1._archive_payloads(
        archive_capability
    )
    if state.root != root:
        raise _error("numeric archive belongs to another project root")
    run, run_payload, proposal_payload, head, _offsets = _validate_run(
        root, state, archive_manifest, batch, plan
    )
    receipt = _receipt(archive_manifest, batch, plan, run, run_payload, proposal_payload)
    destination = root / INDEX_ROOT
    if destination.exists() or destination.is_symlink():
        raise _error("fixed PP-OCRv6 numeric index already exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage: Path | None = Path(tempfile.mkdtemp(prefix=".numeric-index-", dir=destination.parent))
    stage_stat = stage.stat(follow_symlinks=False)
    try:
        assert stage is not None
        payload = canonical_json_bytes_v1(receipt)
        archive_v1._write_exclusive(stage / RECEIPT_PATH.name, payload)
        descriptor = os.open(stage, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        if archive_v1._clean_head(root) != head:
            raise _error("Git changed before numeric index publication")
        archive_v1._rename_noreplace(destination.parent, stage.name, destination.name)
        stage = None
        if archive_v1._clean_head(root) != head:
            raise _error("Git changed while publishing the numeric index")
        return receipt
    finally:
        if stage is not None and stage.exists():
            current = stage.stat(follow_symlinks=False)
            if (current.st_dev, current.st_ino) == (stage_stat.st_dev, stage_stat.st_ino):
                shutil.rmtree(stage)


@dataclass(frozen=True)
class _IndexState:
    root: Path
    archive: archive_v1.AuthenticatedFamilyFirstSemanticLabelArchiveV1
    receipt_payload: bytes
    run_payload: bytes
    proposal_payload: bytes
    offsets: tuple[tuple[int, int], ...]


class AuthenticatedFamilyFirstPPocrV6NumericIndexV1:
    """Opaque complete numeric-proposal-axis handle."""

    __slots__ = ("__weakref__",)

    def __new__(cls, token: object | None = None):
        if token is not _MINT:
            raise TypeError("family-first numeric index handles cannot be constructed")
        return super().__new__(cls)

    def __copy__(self) -> None:
        raise TypeError("family-first numeric index handles cannot be copied")

    def __deepcopy__(self, _memo: dict[int, Any]) -> None:
        raise TypeError("family-first numeric index handles cannot be copied")

    def __reduce__(self) -> None:
        raise TypeError("family-first numeric index handles cannot be pickled")


_MINT = object()
_INDICES: weakref.WeakKeyDictionary[AuthenticatedFamilyFirstPPocrV6NumericIndexV1, _IndexState] = (
    weakref.WeakKeyDictionary()
)


def authenticate_family_first_ppocrv6_numeric_index_v1(
    project_root: Path,
    archive_capability: archive_v1.AuthenticatedFamilyFirstSemanticLabelArchiveV1,
) -> AuthenticatedFamilyFirstPPocrV6NumericIndexV1:
    """Replay every input and mint one opaque numeric-index handle."""

    root = archive_v1._root(project_root)
    state, archive_manifest, batch, plan, _private = archive_v1._archive_payloads(
        archive_capability
    )
    if state.root != root:
        raise _error("numeric archive belongs to another project root")
    run, run_payload, proposal_payload, _head, offsets = _validate_run(
        root, state, archive_manifest, batch, plan
    )
    receipt_payload = _root_bytes(root, RECEIPT_PATH, "numeric index receipt")
    persisted = _validate_receipt(_canonical_object(receipt_payload, "numeric index receipt"))
    expected = _receipt(archive_manifest, batch, plan, run, run_payload, proposal_payload)
    if not same_typed_json_v1(persisted, expected):
        raise _error("numeric index receipt does not replay exactly")
    capability = AuthenticatedFamilyFirstPPocrV6NumericIndexV1(_MINT)
    _INDICES[capability] = _IndexState(
        root,
        archive_capability,
        receipt_payload,
        run_payload,
        proposal_payload,
        tuple(offsets),
    )
    return capability


def _live_index(
    capability: Any,
) -> tuple[_IndexState, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    if type(capability) is not AuthenticatedFamilyFirstPPocrV6NumericIndexV1:
        raise _error("one exact live family-first numeric index handle is required")
    state = _INDICES.get(capability)
    if state is None:
        raise _error("family-first numeric index handle is not live")
    archive_state, archive_manifest, batch, plan, private = archive_v1._archive_payloads(
        state.archive
    )
    receipt_payload = _root_bytes(state.root, RECEIPT_PATH, "numeric index receipt")
    run_payload = _root_bytes(
        state.root, runner_v1.RUN_ROOT / runner_v1._RUN_NAME, "numeric run manifest"
    )
    proposal_payload = _root_bytes(
        state.root, runner_v1.RUN_ROOT / runner_v1._PROPOSAL_NAME, "numeric proposals"
    )
    if (
        archive_state.root != state.root
        or receipt_payload != state.receipt_payload
        or run_payload != state.run_payload
        or proposal_payload != state.proposal_payload
    ):
        raise _error("numeric index/run artifacts changed after authentication")
    run = _canonical_object(run_payload, "numeric run manifest")
    _git_ledger(state.root, run["git_binding"])
    return (
        state,
        _validate_receipt(_canonical_object(receipt_payload, "numeric receipt")),
        batch,
        plan,
        private,
    )


def project_authenticated_family_first_ppocrv6_numeric_index_v1(
    capability: AuthenticatedFamilyFirstPPocrV6NumericIndexV1,
) -> dict[str, Any]:
    """Project identities and denominators without numeric strings/provenance."""

    _state, receipt, _batch, _plan, _private = _live_index(capability)
    return {
        "authority": canonical_clone_v1(_AUTHORITY),
        "format_version": FORMAT_VERSION,
        "metrics": canonical_clone_v1(receipt["metrics"]),
        "receipt_id": receipt["receipt_id"],
        "run_id": receipt["run_id"],
        "state": receipt["state"],
    }


def _proposal_at(state: _IndexState, ordinal: int) -> dict[str, Any]:
    start, stop = state.offsets[ordinal - 1]
    raw = state.proposal_payload[start:stop]
    value = json.loads(raw.decode("utf-8", errors="strict"))
    return runner_v1._validate_result(value, ordinal)


def _document_range(private: dict[str, Any], document_ordinal: int) -> tuple[int, int]:
    starts = [
        index
        for index, item in enumerate(private["samples"])
        if item["document_ordinal"] == document_ordinal
    ]
    if not starts:
        raise _error("numeric source document retained no samples")
    return starts[0], starts[-1] + 1


def read_authenticated_family_first_ppocrv6_numeric_document_v1(
    capability: AuthenticatedFamilyFirstPPocrV6NumericIndexV1,
    *,
    document_ordinal: int,
) -> dict[str, Any]:
    """Read one complete source-bound raw numeric-recognition proposal axis."""

    state, receipt, batch, plan, private = _live_index(capability)
    if (
        type(document_ordinal) is not int
        or not 1 <= document_ordinal <= receipt["metrics"]["document_count"]
    ):
        raise _error("numeric document ordinal lies outside the corpus")
    start, stop = _document_range(private, document_ordinal)
    lines = []
    for zero_index in range(start, stop):
        source = private["samples"][zero_index]
        public = batch["samples"][zero_index]
        proposal = _proposal_at(state, zero_index + 1)
        lines.append(
            {
                "crop_ref": canonical_clone_v1(public["crop_ref"]),
                "line_ordinal": source["line_ordinal"],
                "physical_page": source["physical_page"],
                "raw_prediction": proposal["raw_prediction"],
                "reader_score": proposal["reader_score"],
                "sample_id": source["sample_id"],
                "source_bbox_raw_pixels": canonical_clone_v1(source["source_bbox_raw_pixels"]),
            }
        )
    document = plan["documents"][document_ordinal - 1]
    return {
        "document_ordinal": document_ordinal,
        "lines": lines,
        "private_provenance": canonical_clone_v1(document["private_provenance"]),
        "source_pdf_ref": canonical_clone_v1(document["source_pdf_ref"]),
    }


def _selections(value: Any) -> tuple[tuple[int, int, int], ...]:
    if type(value) is not tuple or not value:
        raise _error("numeric evidence selection must be one non-empty exact tuple")
    result = []
    for raw in value:
        if (
            type(raw) is not dict
            or set(raw) != _SELECTION_FIELDS
            or type(raw["document_ordinal"]) is not int
            or raw["document_ordinal"] <= 0
            or type(raw["physical_page"]) is not int
            or raw["physical_page"] <= 0
            or type(raw["line_ordinal"]) is not int
            or raw["line_ordinal"] < 0
        ):
            raise _error("numeric evidence selection locator drifted")
        result.append((raw["document_ordinal"], raw["physical_page"], raw["line_ordinal"]))
    if result != sorted(set(result)):
        raise _error("numeric evidence selections must be unique and source-ordered")
    return tuple(result)


def read_authenticated_family_first_ppocrv6_numeric_evidence_batch_v1(
    capability: AuthenticatedFamilyFirstPPocrV6NumericIndexV1,
    *,
    selections: tuple[dict[str, int], ...],
) -> tuple[dict[str, Any], ...]:
    """Rebuild typed crop-bound evidence for selected source lines in one scan."""

    locators = _selections(selections)
    state, _receipt_value, batch, _plan, private = _live_index(capability)
    by_locator = {
        (item["document_ordinal"], item["physical_page"], item["line_ordinal"]): index
        for index, item in enumerate(private["samples"])
    }
    try:
        targets = {locator: by_locator[locator] for locator in locators}
    except KeyError as exc:
        raise _error("numeric evidence selection does not identify one source line") from exc
    target_indices = {index: locator for locator, index in targets.items()}
    session = archive_v1.open_authenticated_family_first_semantic_label_reader_session_v1(
        state.archive
    )
    cursor = 0
    built: dict[tuple[int, int, int], dict[str, Any]] = {}
    final_target = max(target_indices)
    while cursor <= final_target:
        chunk = archive_v1.read_authenticated_family_first_semantic_label_chunk_v1(
            session, maximum_samples=min(4096, final_target + 1 - cursor)
        )
        if not chunk:
            raise _error("authenticated crop stream ended before numeric selections")
        for crop in chunk:
            if cursor in target_indices:
                source = private["samples"][cursor]
                public = batch["samples"][cursor]
                proposal = _proposal_at(state, cursor + 1)
                if (
                    crop["sample_id"] != source["sample_id"]
                    or crop["crop_sha256"] != public["crop_ref"]["sha256"]
                    or proposal["crop_sha256"] != crop["crop_sha256"]
                ):
                    raise _error("selected numeric crop/source/proposal cross-link drifted")
                provider = {
                    "input_path": None,
                    "page_index": None,
                    "rec_score": proposal["reader_score"],
                    "rec_text": proposal["raw_prediction"],
                }
                evidence = evidence_v1.build_family_first_ppocrv6_numeric_cell_evidence_v1(
                    crop_png_bytes=crop["crop_png_bytes"], recognizer_payload=provider
                )
                locator = target_indices[cursor]
                built[locator] = {
                    "document_ordinal": locator[0],
                    "evidence": evidence,
                    "line_ordinal": locator[2],
                    "physical_page": locator[1],
                    "sample_id": source["sample_id"],
                    "source_bbox_raw_pixels": canonical_clone_v1(source["source_bbox_raw_pixels"]),
                }
            cursor += 1
    if set(built) != set(locators):
        raise _error("numeric evidence batch did not retain every selection")
    return tuple(built[locator] for locator in locators)
