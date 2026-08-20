"""Authenticate and join the all-filing VietOCR semantic proposal axis.

The model-facing archive deliberately contains no filing, bank, page, period,
scope or schema metadata.  Only after the fixed reader has completed does this
module join its exact ordered proposal stream back to the private source axis.
It publishes one immutable document object per filing so family-first sweeps can
stream all filings without loading the complete corpus into memory.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
import shutil
import tempfile
import unicodedata
import weakref
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bctc_ai.evaluation import family_first_semantic_label_archive_v1 as archive_v1
from bctc_ai.ocr import family_first_vietocr_runner_v1 as runner_v1
from bctc_ai.ocr import vietocr_all_line_runner_v3 as runtime_v3
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "AuthenticatedFamilyFirstSemanticIndexV1",
    "FamilyFirstSemanticIndexV1Error",
    "authenticate_family_first_semantic_index_v1",
    "finalize_authenticated_family_first_semantic_index_v1",
    "project_authenticated_family_first_semantic_index_v1",
    "read_authenticated_family_first_semantic_document_v1",
    "read_authenticated_family_first_structure_document_v1",
]


INDEX_ROOT = Path("output/calibration/family-first-vietocr-semantic-cache-v1/verified-index")
MANIFEST_PATH = INDEX_ROOT / "semantic-index-manifest.json"
RECEIPT_PATH = INDEX_ROOT / "verification-receipt.json"
DOCUMENT_ROOT = INDEX_ROOT / "documents"
FORMAT_VERSION = "FAMILY_FIRST_VIETOCR_SEMANTIC_INDEX_V1"
DOCUMENT_FORMAT_VERSION = "FAMILY_FIRST_VIETOCR_SEMANTIC_DOCUMENT_V1"
RECEIPT_FORMAT_VERSION = "FAMILY_FIRST_VIETOCR_SEMANTIC_INDEX_RECEIPT_V1"
LINE_FORMAT_VERSION = "FAMILY_FIRST_VIETOCR_SEMANTIC_LINE_V1"
STATE = "VERIFIED_COMPLETE_ORDERED_VIETOCR_TRANSFORMER_PROPOSALS"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_AUTHORITY = {
    "accounting_authority": False,
    "all_empty_predictions_preserved": True,
    "geometry_authority": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "old_detector_or_native_transcript_used_as_semantic_text": False,
    "ordered_semantic_proposal_authority": True,
    "schema_authority": False,
    "semantic_text_source": "FRESH_VIETOCR_VGG_TRANSFORMER_0_3_13",
}
_LINE_FIELDS = {
    "accentless_text",
    "crop_ref",
    "format_version",
    "line_ordinal",
    "mean_decoded_character_probability",
    "processed_height",
    "processed_width",
    "sample_id",
    "source_bbox_raw_pixels",
    "vietocr_text",
    "vietocr_text_nfc",
}
_PAGE_FIELDS = {"line_count", "lines", "physical_page"}
_DOCUMENT_FIELDS = {
    "document_id",
    "document_ordinal",
    "format_version",
    "line_count",
    "page_count",
    "pages",
    "private_provenance",
    "source_pdf_ref",
}
_MANIFEST_FIELDS = {
    "archive_id",
    "authority",
    "batch_id",
    "documents",
    "format_version",
    "index_id",
    "metrics",
    "plan_id",
    "run_id",
    "state",
}


class FamilyFirstSemanticIndexV1Error(RuntimeError):
    """The reader run, source join, or immutable semantic index drifted."""


def _error(message: str) -> FamilyFirstSemanticIndexV1Error:
    return FamilyFirstSemanticIndexV1Error(message)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _ref(value: Any, label: str) -> dict[str, Any]:
    try:
        return canonical_clone_v1(archive_v1._ref(value, label))
    except archive_v1.FamilyFirstSemanticLabelArchiveV1Error as exc:
        raise _error(f"{label} reference drifted") from exc


def _matches(payload: bytes, reference: Any, label: str) -> None:
    expected = _ref(reference, label)
    if len(payload) != expected["size_bytes"] or _sha(payload) != expected["sha256"]:
        raise _error(f"{label} bytes differ from their content reference")


def _root_bytes(root: Path, relative: str | Path, label: str) -> bytes:
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


def _normalize_text(value: str) -> tuple[str, str]:
    nfc = unicodedata.normalize("NFC", value)
    decomposed = unicodedata.normalize("NFD", nfc.casefold())
    accentless = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    accentless = accentless.replace("đ", "d")
    return nfc, " ".join(accentless.split())


def _png_dimensions(payload: bytes) -> tuple[int, int]:
    if len(payload) < 24 or payload[:8] != b"\x89PNG\r\n\x1a\n":
        raise _error("authenticated semantic crop is not one PNG byte snapshot")
    if payload[12:16] != b"IHDR" or int.from_bytes(payload[8:12], "big") != 13:
        raise _error("authenticated semantic crop PNG header drifted")
    width = int.from_bytes(payload[16:20], "big")
    height = int.from_bytes(payload[20:24], "big")
    if width <= 0 or height <= 0:
        raise _error("authenticated semantic crop PNG dimensions drifted")
    return width, height


def _processed_dimensions(payload: bytes) -> tuple[int, int]:
    width, height = _png_dimensions(payload)
    scaled_width = (32 * width) // height
    rounded_width = ((scaled_width + 9) // 10) * 10
    return max(32, min(512, rounded_width)), 32


def _git_ledger(root: Path, run_git: Any) -> str:
    head = archive_v1._clean_head(root)
    if (
        type(run_git) is not dict
        or set(run_git) != {"commit", "dirty", "implementation_refs", "source_tree_oid"}
        or type(run_git["commit"]) is not str
        or _COMMIT.fullmatch(run_git["commit"]) is None
        or type(run_git["dirty"]) is not bool
        or run_git["dirty"] is not False
        or type(run_git["source_tree_oid"]) is not str
        or _COMMIT.fullmatch(run_git["source_tree_oid"]) is None
        or type(run_git["implementation_refs"]) is not list
    ):
        raise _error("formal VietOCR Git binding drifted")
    run_commit = run_git["commit"]
    try:
        archive_v1._git(root, "merge-base", "--is-ancestor", run_commit, head)
    except archive_v1.FamilyFirstSemanticLabelArchiveV1Error as exc:
        raise _error("formal VietOCR commit is not an ancestor of current HEAD") from exc
    expected_paths = [path.as_posix() for path in runner_v1._TRUST_PATHS]
    observed_paths = [
        item.get("path") if type(item) is dict else None for item in run_git["implementation_refs"]
    ]
    if observed_paths != expected_paths:
        raise _error("formal VietOCR trust-closure path denominator drifted")
    for raw_reference in run_git["implementation_refs"]:
        reference = _ref(raw_reference, "formal VietOCR trust file")
        committed = archive_v1._git(root, "show", f"{run_commit}:{reference['path']}")
        current = archive_v1._git(root, "show", f"{head}:{reference['path']}")
        disk = _root_bytes(root, reference["path"], "formal VietOCR trust file")
        _matches(committed, reference, "formal VietOCR committed trust file")
        if committed != current or committed != disk:
            raise _error("formal VietOCR trust file changed on the descendant chain")
    run_tree = (
        archive_v1._git(root, "rev-parse", f"{run_commit}:src/bctc_ai")
        .decode("ascii", errors="strict")
        .strip()
    )
    if run_tree != run_git["source_tree_oid"]:
        raise _error("formal VietOCR source-tree identity drifted at its run commit")
    if archive_v1._clean_head(root) != head:
        raise _error("Git HEAD/worktree changed during formal VietOCR ledger replay")
    return head


def _proposal_iterator(payload: bytes, expected_count: int) -> Iterator[dict[str, Any]]:
    stream = io.BytesIO(payload)
    count = 0
    while line := stream.readline():
        count += 1
        if not line.endswith(b"\n"):
            raise _error("formal VietOCR proposal JSONL has one incomplete final line")
        try:
            value = json.loads(line.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _error("formal VietOCR proposal JSONL is not strict JSON") from exc
        try:
            proposal = runner_v1._validate_result(value, count)
        except runner_v1.FamilyFirstVietOCRRunnerV1Error as exc:
            raise _error("formal VietOCR proposal contract drifted") from exc
        if line != canonical_json_bytes_v1(proposal):
            raise _error("formal VietOCR proposal JSONL line is not canonical")
        yield proposal
    if count != expected_count:
        raise _error("formal VietOCR proposal denominator drifted")


def _validate_run(
    root: Path,
    projection: dict[str, Any],
) -> tuple[dict[str, Any], bytes, bytes, str]:
    run_path = runner_v1.RUN_ROOT / runner_v1._RUN_NAME
    attempt_path = runner_v1.RUN_ROOT / runner_v1._ATTEMPT_NAME
    proposal_path = runner_v1.RUN_ROOT / runner_v1._PROPOSAL_NAME
    if _directory_listing(root, runner_v1.RUN_ROOT, "formal VietOCR run root") != sorted(
        [runner_v1._ATTEMPT_NAME, runner_v1._PROPOSAL_NAME, runner_v1._RUN_NAME]
    ):
        raise _error("formal VietOCR run output listing drifted")
    run_payload = _root_bytes(root, run_path, "formal VietOCR run manifest")
    attempt_payload = _root_bytes(root, attempt_path, "formal VietOCR attempt")
    proposal_payload = _root_bytes(root, proposal_path, "formal VietOCR proposals")
    run = _canonical_object(run_payload, "formal VietOCR run manifest")
    attempt = _canonical_object(attempt_payload, "formal VietOCR attempt")
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
    expected_attempt_fields = {
        "attempt_id",
        "claim_boundary",
        "format_version",
        "preflight",
        "started_at",
        "state",
    }
    if (
        set(run) != expected_run_fields
        or set(attempt) != expected_attempt_fields
        or run["format_version"] != runner_v1.RUN_FORMAT_VERSION
        or run["experiment_id"] != runner_v1.EXPERIMENT_ID
        or run["state"] != "REFERENCE_BLIND_SEMANTIC_PROPOSAL_RUN_COMPLETE"
        or attempt["format_version"] != runner_v1.ATTEMPT_FORMAT_VERSION
        or attempt["claim_boundary"]
        != "ONE_REFERENCE_BLIND_SEMANTIC_PROPOSAL_ATTEMPT_NO_RESUME_OR_RETRY"
        or attempt["state"] != "FORMAL_ATTEMPT_STARTED_NO_RESUME_OR_RETRY"
        or run["attempt_id"] != attempt["attempt_id"]
        or run["started_at"] != attempt["started_at"]
        or not same_typed_json_v1(run["git_binding"], attempt["preflight"].get("git_binding"))
        or not same_typed_json_v1(run["execution_policy"], runner_v1._EXECUTION_POLICY)
        or not same_typed_json_v1(run["safety"], runner_v1._SAFETY)
    ):
        raise _error("formal VietOCR run/attempt identity drifted")
    preflight = attempt["preflight"]
    expected_input = {
        "archive_id": projection["archive_id"],
        "batch_id": projection["batch_id"],
        "plan_id": projection["plan_id"],
        "sample_count": projection["sample_count"],
    }
    if (
        type(preflight) is not dict
        or set(preflight)
        != {
            "archive_id",
            "batch_id",
            "configuration_ref",
            "execution_policy",
            "experiment_id",
            "git_binding",
            "plan_id",
            "runtime_artifacts",
            "sample_count",
        }
        or preflight.get("archive_id") != projection["archive_id"]
        or preflight.get("batch_id") != projection["batch_id"]
        or preflight.get("plan_id") != projection["plan_id"]
        or preflight.get("sample_count") != projection["sample_count"]
        or type(preflight.get("sample_count")) is not int
        or preflight.get("experiment_id") != runner_v1.EXPERIMENT_ID
        or not same_typed_json_v1(preflight.get("execution_policy"), runner_v1._EXECUTION_POLICY)
        or not same_typed_json_v1(run["input"], expected_input)
        or attempt["attempt_id"] != "ffvocrv1:attempt:" + canonical_json_sha256_v1(preflight)
    ):
        raise _error("formal VietOCR input/preflight binding drifted")
    run_material = canonical_clone_v1(run)
    run_id = run_material.pop("run_id")
    if run_id != "ffvocrv1:run:" + canonical_json_sha256_v1(run_material):
        raise _error("formal VietOCR run hash identity drifted")
    artifacts = run["artifacts"]
    if type(artifacts) is not dict or set(artifacts) != {"attempt", "semantic_proposals"}:
        raise _error("formal VietOCR artifact set drifted")
    if artifacts["attempt"].get("path") != attempt_path.as_posix():
        raise _error("formal VietOCR attempt path drifted")
    if artifacts["semantic_proposals"].get("path") != proposal_path.as_posix():
        raise _error("formal VietOCR proposal path drifted")
    _matches(attempt_payload, artifacts["attempt"], "formal VietOCR attempt")
    _matches(proposal_payload, artifacts["semantic_proposals"], "formal VietOCR proposals")
    proposal_count = null_count = empty_count = 0
    for proposal in _proposal_iterator(proposal_payload, projection["sample_count"]):
        proposal_count += 1
        null_count += proposal["mean_decoded_character_probability"] is None
        empty_count += proposal["raw_prediction"] == ""
    metrics = run["metrics"]
    if (
        type(metrics) is not dict
        or set(metrics)
        != {
            "empty_prediction_count",
            "model_load_seconds",
            "null_probability_count",
            "peak_gpu_memory_allocated_mib",
            "peak_gpu_memory_reserved_mib",
            "sample_count",
            "total_wall_seconds",
        }
        or metrics["sample_count"] != proposal_count
        or type(metrics["sample_count"]) is not int
        or metrics["empty_prediction_count"] != empty_count
        or type(metrics["empty_prediction_count"]) is not int
        or metrics["null_probability_count"] != null_count
        or type(metrics["null_probability_count"]) is not int
        or any(
            type(metrics[key]) is not float or not math.isfinite(metrics[key]) or metrics[key] < 0
            for key in (
                "model_load_seconds",
                "peak_gpu_memory_allocated_mib",
                "peak_gpu_memory_reserved_mib",
                "total_wall_seconds",
            )
        )
    ):
        raise _error("formal VietOCR metrics drifted")
    kernel_metrics = {
        key: metrics[key]
        for key in (
            "model_load_seconds",
            "peak_gpu_memory_allocated_mib",
            "peak_gpu_memory_reserved_mib",
            "total_wall_seconds",
        )
    }
    runtime = run["runtime"]
    if type(runtime) is not dict or set(runtime) != {
        "artifacts",
        "compute_capability",
        "cuda_runtime",
        "device_name",
        "packages",
        "python_major_minor",
        "runtime_root",
    }:
        raise _error("formal VietOCR runtime fields drifted")
    kernel_runtime = canonical_clone_v1(runtime)
    runtime_artifacts = kernel_runtime.pop("artifacts")
    try:
        runner_v1._validate_kernel_outputs(
            kernel_runtime,
            run["execution_counts"],
            kernel_metrics,
            sample_count=proposal_count,
        )
    except runner_v1.FamilyFirstVietOCRRunnerV1Error as exc:
        raise _error("formal VietOCR runtime/count evidence drifted") from exc
    if not same_typed_json_v1(runtime_artifacts, preflight["runtime_artifacts"]):
        raise _error("formal VietOCR runtime artifact binding drifted")
    if preflight.get("configuration_ref", {}).get("path") != runner_v1.CONFIG_PATH.as_posix():
        raise _error("formal VietOCR configuration path drifted")
    config_payload = _root_bytes(root, runner_v1.CONFIG_PATH, "pinned VietOCR configuration")
    _matches(config_payload, preflight["configuration_ref"], "pinned VietOCR configuration")
    try:
        config = runtime_v3._validate_config(config_payload)
        snapshots, current_runtime_artifacts = runtime_v3._snapshot_runtime(config)
        runtime_v3._verify_wheel_overlay(
            snapshots["wheel"], runtime_v3.RUNTIME_ROOT / config["runtime"]["site_packages"]
        )
    except Exception as exc:
        raise _error("pinned VietOCR configuration semantics drifted") from exc
    if not same_typed_json_v1(current_runtime_artifacts, runtime_artifacts):
        raise _error("formal VietOCR runtime artifact bytes drifted after inference")
    head = _git_ledger(root, run["git_binding"])
    if archive_v1._clean_head(root) != head:
        raise _error("Git HEAD/worktree changed during formal VietOCR run validation")
    return run, run_payload, proposal_payload, head


def _line(
    private: dict[str, Any],
    public: dict[str, Any],
    proposal: dict[str, Any],
    crop: dict[str, Any],
) -> dict[str, Any]:
    if (
        private["sample_id"] != public["sample_id"]
        or proposal["sample_id"] != public["sample_id"]
        or crop["sample_id"] != public["sample_id"]
        or proposal["crop_sha256"] != public["crop_ref"]["sha256"]
        or crop["crop_sha256"] != public["crop_ref"]["sha256"]
    ):
        raise _error("private/public/crop/proposal semantic axis diverged")
    width, height = _processed_dimensions(crop["crop_png_bytes"])
    if proposal["processed_width"] != width or proposal["processed_height"] != height:
        raise _error("VietOCR processed dimensions differ from authenticated crop pixels")
    nfc, accentless = _normalize_text(proposal["raw_prediction"])
    return {
        "accentless_text": accentless,
        "crop_ref": canonical_clone_v1(public["crop_ref"]),
        "format_version": LINE_FORMAT_VERSION,
        "line_ordinal": private["line_ordinal"],
        "mean_decoded_character_probability": proposal["mean_decoded_character_probability"],
        "processed_height": height,
        "processed_width": width,
        "sample_id": public["sample_id"],
        "source_bbox_raw_pixels": canonical_clone_v1(private["source_bbox_raw_pixels"]),
        "vietocr_text": proposal["raw_prediction"],
        "vietocr_text_nfc": nfc,
    }


def _validate_line(value: Any, expected_ordinal: int) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _LINE_FIELDS
        or value["format_version"] != LINE_FORMAT_VERSION
        or type(value["line_ordinal"]) is not int
        or value["line_ordinal"] != expected_ordinal
        or type(value["sample_id"]) is not str
        or type(value["vietocr_text"]) is not str
        or type(value["vietocr_text_nfc"]) is not str
        or type(value["accentless_text"]) is not str
        or type(value["processed_width"]) is not int
        or value["processed_width"] <= 0
        or type(value["processed_height"]) is not int
        or value["processed_height"] != 32
        or type(value["source_bbox_raw_pixels"]) is not list
        or len(value["source_bbox_raw_pixels"]) != 4
        or any(type(item) is not int for item in value["source_bbox_raw_pixels"])
    ):
        raise _error("semantic index line contract drifted")
    probability = value["mean_decoded_character_probability"]
    if probability is not None and (
        type(probability) is not float
        or not math.isfinite(probability)
        or not 0 <= probability <= 1
    ):
        raise _error("semantic index line probability drifted")
    _ref(value["crop_ref"], "semantic index crop")
    nfc, accentless = _normalize_text(value["vietocr_text"])
    if value["vietocr_text_nfc"] != nfc or value["accentless_text"] != accentless:
        raise _error("semantic index normalized text drifted")
    return canonical_clone_v1(value)


def _validate_document(value: Any, expected: dict[str, Any]) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _DOCUMENT_FIELDS
        or value["format_version"] != DOCUMENT_FORMAT_VERSION
        or value["document_ordinal"] != expected["document_ordinal"]
        or type(value["document_ordinal"]) is not int
        or value["page_count"] != expected["page_count"]
        or type(value["page_count"]) is not int
        or not same_typed_json_v1(value["private_provenance"], expected["private_provenance"])
        or not same_typed_json_v1(value["source_pdf_ref"], expected["source_pdf_ref"])
        or type(value["line_count"]) is not int
        or value["line_count"] <= 0
        or type(value["pages"]) is not list
        or len(value["pages"]) != value["page_count"]
    ):
        raise _error("semantic index document contract drifted")
    cursor = 0
    for physical_page, page in enumerate(value["pages"], 1):
        if (
            type(page) is not dict
            or set(page) != _PAGE_FIELDS
            or page["physical_page"] != physical_page
            or type(page["line_count"]) is not int
            or page["line_count"] < 0
            or type(page["lines"]) is not list
            or len(page["lines"]) != page["line_count"]
        ):
            raise _error("semantic index page contract drifted")
        for line_ordinal, line in enumerate(page["lines"]):
            _validate_line(line, line_ordinal)
            cursor += 1
    if cursor != value["line_count"]:
        raise _error("semantic index document line denominator drifted")
    material = canonical_clone_v1(value)
    document_id = material.pop("document_id")
    if document_id != "ffsiv1:document:" + canonical_json_sha256_v1(material):
        raise _error("semantic index document hash identity drifted")
    return canonical_clone_v1(value)


def _validate_manifest(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _MANIFEST_FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["state"] != STATE
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["documents"]) is not list
        or type(value["metrics"]) is not dict
    ):
        raise _error("semantic index manifest contract drifted")
    metrics = value["metrics"]
    if (
        set(metrics)
        != {
            "document_count",
            "empty_prediction_count",
            "line_count_vector",
            "null_probability_count",
            "page_count",
            "page_count_vector",
            "sample_count",
            "semantic_axis_sha256",
        }
        or type(metrics["document_count"]) is not int
        or metrics["document_count"] != len(value["documents"])
        or type(metrics["sample_count"]) is not int
        or metrics["sample_count"] <= 0
        or type(metrics["page_count"]) is not int
        or type(metrics["page_count_vector"]) is not list
        or type(metrics["line_count_vector"]) is not list
        or any(type(item) is not int or item <= 0 for item in metrics["page_count_vector"])
        or any(type(item) is not int or item <= 0 for item in metrics["line_count_vector"])
        or sum(metrics["page_count_vector"]) != metrics["page_count"]
        or sum(metrics["line_count_vector"]) != metrics["sample_count"]
        or type(metrics["empty_prediction_count"]) is not int
        or type(metrics["null_probability_count"]) is not int
        or type(metrics["semantic_axis_sha256"]) is not str
        or _SHA256.fullmatch(metrics["semantic_axis_sha256"]) is None
    ):
        raise _error("semantic index manifest metrics drifted")
    for ordinal, document in enumerate(value["documents"], 1):
        if (
            type(document) is not dict
            or set(document)
            != {"content_ref", "document_id", "document_ordinal", "line_count", "page_count"}
            or document["document_ordinal"] != ordinal
            or type(document["line_count"]) is not int
            or document["line_count"] != metrics["line_count_vector"][ordinal - 1]
            or type(document["page_count"]) is not int
            or document["page_count"] != metrics["page_count_vector"][ordinal - 1]
        ):
            raise _error("semantic index manifest document axis drifted")
        reference = _ref(document["content_ref"], "semantic index document")
        expected_path = (DOCUMENT_ROOT / f"document-{ordinal:04d}.json").as_posix()
        if reference["path"] != expected_path:
            raise _error("semantic index document path drifted")
    material = canonical_clone_v1(value)
    index_id = material.pop("index_id")
    if index_id != "ffsiv1:index:" + canonical_json_sha256_v1(material):
        raise _error("semantic index manifest hash identity drifted")
    return canonical_clone_v1(value)


def _crop_iterator(session: Any) -> Iterator[dict[str, Any]]:
    while True:
        chunk = archive_v1.read_authenticated_family_first_semantic_label_chunk_v1(
            session, maximum_samples=1024
        )
        if not chunk:
            return
        yield from chunk


def _write_exclusive(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o444)
    try:
        archive_v1._write_all(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _build_index_stage(
    root: Path,
    stage: Path,
    archive_capability: archive_v1.AuthenticatedFamilyFirstSemanticLabelArchiveV1,
    archive_manifest: dict[str, Any],
    batch: dict[str, Any],
    plan: dict[str, Any],
    private_index: dict[str, Any],
    run: dict[str, Any],
    proposal_payload: bytes,
) -> dict[str, Any]:
    documents_directory = stage / "documents"
    documents_directory.mkdir(mode=0o755)
    session = archive_v1.open_authenticated_family_first_semantic_label_reader_session_v1(
        archive_capability
    )
    crops = _crop_iterator(session)
    proposals = _proposal_iterator(proposal_payload, batch["sample_count"])
    private_samples = private_index["samples"]
    public_samples = batch["samples"]
    cursor = 0
    document_refs: list[dict[str, Any]] = []
    line_count_vector: list[int] = []
    page_count_vector: list[int] = []
    semantic_axis = hashlib.sha256()
    null_count = 0
    empty_count = 0
    for document in plan["documents"]:
        ordinal = document["document_ordinal"]
        pages: list[dict[str, Any]] = []
        document_line_count = 0
        for physical_page in range(1, document["page_count"] + 1):
            lines: list[dict[str, Any]] = []
            line_ordinal = 0
            while cursor < len(private_samples):
                private = private_samples[cursor]
                if (
                    private["document_ordinal"] != ordinal
                    or private["physical_page"] != physical_page
                ):
                    break
                public = public_samples[cursor]
                try:
                    proposal = next(proposals)
                    crop = next(crops)
                except StopIteration as exc:
                    raise _error(
                        "semantic proposal/crop stream ended before its source axis"
                    ) from exc
                line = _line(private, public, proposal, crop)
                if line["line_ordinal"] != line_ordinal:
                    raise _error("semantic source line ordinal drifted within its page")
                lines.append(line)
                semantic_axis.update(
                    canonical_json_bytes_v1(
                        {
                            "crop_sha256": line["crop_ref"]["sha256"],
                            "mean_decoded_character_probability": line[
                                "mean_decoded_character_probability"
                            ],
                            "sample_id": line["sample_id"],
                            "vietocr_text": line["vietocr_text"],
                        }
                    )
                )
                null_count += line["mean_decoded_character_probability"] is None
                empty_count += line["vietocr_text"] == ""
                cursor += 1
                line_ordinal += 1
                document_line_count += 1
            pages.append(
                {
                    "line_count": len(lines),
                    "lines": lines,
                    "physical_page": physical_page,
                }
            )
        material = {
            "document_ordinal": ordinal,
            "format_version": DOCUMENT_FORMAT_VERSION,
            "line_count": document_line_count,
            "page_count": document["page_count"],
            "pages": pages,
            "private_provenance": canonical_clone_v1(document["private_provenance"]),
            "source_pdf_ref": canonical_clone_v1(document["source_pdf_ref"]),
        }
        document_value = _validate_document(
            {
                **material,
                "document_id": "ffsiv1:document:" + canonical_json_sha256_v1(material),
            },
            document,
        )
        payload = canonical_json_bytes_v1(document_value)
        name = f"document-{ordinal:04d}.json"
        _write_exclusive(documents_directory / name, payload)
        document_refs.append(
            {
                "content_ref": {
                    "path": (DOCUMENT_ROOT / name).as_posix(),
                    "sha256": _sha(payload),
                    "size_bytes": len(payload),
                },
                "document_id": document_value["document_id"],
                "document_ordinal": ordinal,
                "line_count": document_line_count,
                "page_count": document["page_count"],
            }
        )
        line_count_vector.append(document_line_count)
        page_count_vector.append(document["page_count"])
    if cursor != batch["sample_count"]:
        raise _error("semantic source axis retained an unjoined sample")
    try:
        next(proposals)
    except StopIteration:
        pass
    else:
        raise _error("semantic proposal stream retained an unjoined sample")
    try:
        next(crops)
    except StopIteration:
        pass
    else:
        raise _error("authenticated crop stream retained an unjoined sample")
    material = {
        "archive_id": archive_manifest["archive_id"],
        "authority": canonical_clone_v1(_AUTHORITY),
        "batch_id": batch["batch_id"],
        "documents": document_refs,
        "format_version": FORMAT_VERSION,
        "metrics": {
            "document_count": len(document_refs),
            "empty_prediction_count": empty_count,
            "line_count_vector": line_count_vector,
            "null_probability_count": null_count,
            "page_count": sum(page_count_vector),
            "page_count_vector": page_count_vector,
            "sample_count": cursor,
            "semantic_axis_sha256": semantic_axis.hexdigest(),
        },
        "plan_id": plan["plan_id"],
        "run_id": run["run_id"],
        "state": STATE,
    }
    manifest = _validate_manifest(
        {**material, "index_id": "ffsiv1:index:" + canonical_json_sha256_v1(material)}
    )
    manifest_payload = canonical_json_bytes_v1(manifest)
    _write_exclusive(stage / MANIFEST_PATH.name, manifest_payload)
    receipt = {
        "format_version": RECEIPT_FORMAT_VERSION,
        "index_id": manifest["index_id"],
        "manifest_ref": {
            "path": MANIFEST_PATH.as_posix(),
            "sha256": _sha(manifest_payload),
            "size_bytes": len(manifest_payload),
        },
        "metrics": canonical_clone_v1(manifest["metrics"]),
        "state": "VERIFIED_INDEX_PUBLISHED_NO_OVERWRITE",
    }
    _write_exclusive(stage / RECEIPT_PATH.name, canonical_json_bytes_v1(receipt))
    for directory in (documents_directory, stage):
        descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    return manifest


def finalize_authenticated_family_first_semantic_index_v1(
    project_root: Path,
    archive_capability: archive_v1.AuthenticatedFamilyFirstSemanticLabelArchiveV1,
) -> dict[str, Any]:
    """Join and publish the fixed all-filing matcher index exactly once."""

    root = archive_v1._root(project_root)
    archive_state, archive_manifest, batch, plan, private_index = archive_v1._archive_payloads(
        archive_capability
    )
    if archive_state.root != root:
        raise _error("semantic archive belongs to another project root")
    projection = {
        "archive_id": archive_manifest["archive_id"],
        "batch_id": batch["batch_id"],
        "plan_id": plan["plan_id"],
        "sample_count": batch["sample_count"],
    }
    run, _run_payload, proposal_payload, captured_head = _validate_run(root, projection)
    destination = root / INDEX_ROOT
    if destination.exists() or destination.is_symlink():
        raise _error("fixed family-first semantic index already exists")
    parent = destination.parent
    parent.mkdir(parents=True, exist_ok=True)
    stage: Path | None = Path(tempfile.mkdtemp(prefix=".verified-index-", dir=parent))
    stage_stat = stage.stat(follow_symlinks=False)
    try:
        assert stage is not None
        manifest = _build_index_stage(
            root,
            stage,
            archive_capability,
            archive_manifest,
            batch,
            plan,
            private_index,
            run,
            proposal_payload,
        )
        if archive_v1._clean_head(root) != captured_head:
            raise _error("Git HEAD/worktree changed before semantic index publication")
        archive_v1._rename_noreplace(parent, stage.name, destination.name)
        stage = None
        if archive_v1._clean_head(root) != captured_head:
            raise _error("Git HEAD/worktree changed while publishing semantic index")
        return manifest
    finally:
        if stage is not None and stage.exists():
            current = stage.stat(follow_symlinks=False)
            if (current.st_dev, current.st_ino) == (stage_stat.st_dev, stage_stat.st_ino):
                shutil.rmtree(stage)


@dataclass(frozen=True)
class _IndexState:
    root: Path
    archive: archive_v1.AuthenticatedFamilyFirstSemanticLabelArchiveV1
    manifest_payload: bytes
    plan_documents_payload: bytes
    run_manifest_payload: bytes


class AuthenticatedFamilyFirstSemanticIndexV1:
    """Opaque exact matcher-facing index handle."""

    __slots__ = ("__weakref__",)

    def __new__(cls, token: object | None = None) -> AuthenticatedFamilyFirstSemanticIndexV1:
        if token is not _MINT:
            raise TypeError("family-first semantic index handles cannot be constructed")
        return super().__new__(cls)

    def __copy__(self) -> None:
        raise TypeError("family-first semantic index handles cannot be copied")

    def __deepcopy__(self, _memo: dict[int, Any]) -> None:
        raise TypeError("family-first semantic index handles cannot be copied")

    def __reduce__(self) -> None:
        raise TypeError("family-first semantic index handles cannot be pickled")


_MINT = object()
_INDICES: weakref.WeakKeyDictionary[AuthenticatedFamilyFirstSemanticIndexV1, _IndexState] = (
    weakref.WeakKeyDictionary()
)


def _authenticate_payloads(
    root: Path,
    archive_capability: archive_v1.AuthenticatedFamilyFirstSemanticLabelArchiveV1,
) -> tuple[dict[str, Any], bytes, bytes, bytes]:
    archive_state, archive_manifest, batch, plan, _private_index = archive_v1._archive_payloads(
        archive_capability
    )
    if archive_state.root != root:
        raise _error("semantic archive belongs to another project root")
    projection = {
        "archive_id": archive_manifest["archive_id"],
        "batch_id": batch["batch_id"],
        "plan_id": plan["plan_id"],
        "sample_count": batch["sample_count"],
    }
    run, run_payload, _proposal_payload, captured_head = _validate_run(root, projection)
    manifest_payload = _root_bytes(root, MANIFEST_PATH, "semantic index manifest")
    manifest = _validate_manifest(_canonical_object(manifest_payload, "semantic index manifest"))
    if (
        manifest["archive_id"] != projection["archive_id"]
        or manifest["batch_id"] != projection["batch_id"]
        or manifest["plan_id"] != projection["plan_id"]
        or manifest["run_id"] != run["run_id"]
        or manifest["metrics"]["sample_count"] != projection["sample_count"]
        or len(manifest["documents"]) != len(plan["documents"])
    ):
        raise _error("semantic index input lineage drifted")
    semantic_axis = hashlib.sha256()
    for reference, expected_document in zip(manifest["documents"], plan["documents"], strict=True):
        payload = _root_bytes(root, reference["content_ref"]["path"], "semantic index document")
        _matches(payload, reference["content_ref"], "semantic index document")
        document = _validate_document(
            _canonical_object(payload, "semantic index document"), expected_document
        )
        if document["document_id"] != reference["document_id"]:
            raise _error("semantic index document ID/ref cross-link drifted")
        for page in document["pages"]:
            for line in page["lines"]:
                semantic_axis.update(
                    canonical_json_bytes_v1(
                        {
                            "crop_sha256": line["crop_ref"]["sha256"],
                            "mean_decoded_character_probability": line[
                                "mean_decoded_character_probability"
                            ],
                            "sample_id": line["sample_id"],
                            "vietocr_text": line["vietocr_text"],
                        }
                    )
                )
    if semantic_axis.hexdigest() != manifest["metrics"]["semantic_axis_sha256"]:
        raise _error("semantic index ordered semantic axis drifted")
    receipt_payload = _root_bytes(root, RECEIPT_PATH, "semantic index receipt")
    receipt = _canonical_object(receipt_payload, "semantic index receipt")
    expected_receipt = {
        "format_version": RECEIPT_FORMAT_VERSION,
        "index_id": manifest["index_id"],
        "manifest_ref": {
            "path": MANIFEST_PATH.as_posix(),
            "sha256": _sha(manifest_payload),
            "size_bytes": len(manifest_payload),
        },
        "metrics": manifest["metrics"],
        "state": "VERIFIED_INDEX_PUBLISHED_NO_OVERWRITE",
    }
    if not same_typed_json_v1(receipt, expected_receipt):
        raise _error("semantic index verification receipt drifted")
    if archive_v1._clean_head(root) != captured_head:
        raise _error("Git HEAD/worktree changed during semantic index authentication")
    plan_documents_payload = canonical_json_bytes_v1({"documents": plan["documents"]})
    return manifest, manifest_payload, plan_documents_payload, run_payload


def authenticate_family_first_semantic_index_v1(
    project_root: Path,
    archive_capability: archive_v1.AuthenticatedFamilyFirstSemanticLabelArchiveV1,
) -> AuthenticatedFamilyFirstSemanticIndexV1:
    """Authenticate every document and mint one opaque matcher-facing handle."""

    root = archive_v1._root(project_root)
    _manifest, manifest_payload, plan_documents_payload, run_payload = _authenticate_payloads(
        root, archive_capability
    )
    capability = AuthenticatedFamilyFirstSemanticIndexV1(_MINT)
    _INDICES[capability] = _IndexState(
        root, archive_capability, manifest_payload, plan_documents_payload, run_payload
    )
    return capability


def _live_index(
    capability: Any,
) -> tuple[_IndexState, dict[str, Any]]:
    if type(capability) is not AuthenticatedFamilyFirstSemanticIndexV1:
        raise _error("one exact live family-first semantic index handle is required")
    state = _INDICES.get(capability)
    if state is None:
        raise _error("family-first semantic index handle is not live")
    live_manifest = _root_bytes(state.root, MANIFEST_PATH, "semantic index manifest")
    live_run = _root_bytes(
        state.root,
        runner_v1.RUN_ROOT / runner_v1._RUN_NAME,
        "formal VietOCR run manifest",
    )
    if live_manifest != state.manifest_payload or live_run != state.run_manifest_payload:
        raise _error("semantic index/run manifest changed after authentication")
    manifest = _validate_manifest(_canonical_object(live_manifest, "semantic index manifest"))
    run = _canonical_object(live_run, "formal VietOCR run manifest")
    _git_ledger(state.root, run["git_binding"])
    return state, manifest


def project_authenticated_family_first_semantic_index_v1(
    capability: AuthenticatedFamilyFirstSemanticIndexV1,
) -> dict[str, Any]:
    """Return only corpus identity and denominators, without source or text."""

    _state, manifest = _live_index(capability)
    return {
        "authority": canonical_clone_v1(_AUTHORITY),
        "format_version": FORMAT_VERSION,
        "index_id": manifest["index_id"],
        "metrics": canonical_clone_v1(manifest["metrics"]),
        "state": manifest["state"],
    }


def read_authenticated_family_first_semantic_document_v1(
    capability: AuthenticatedFamilyFirstSemanticIndexV1,
    *,
    document_ordinal: int,
) -> dict[str, Any]:
    """Read one exact source-bound semantic document for generic family sweeps."""

    state, manifest = _live_index(capability)
    if (
        type(document_ordinal) is not int
        or not 1 <= document_ordinal <= manifest["metrics"]["document_count"]
    ):
        raise _error("semantic index document ordinal lies outside the corpus")
    reference = manifest["documents"][document_ordinal - 1]
    payload = _root_bytes(state.root, reference["content_ref"]["path"], "semantic index document")
    _matches(payload, reference["content_ref"], "semantic index document")
    document = _canonical_object(payload, "semantic index document")
    plan_documents = _canonical_object(
        state.plan_documents_payload, "semantic index plan document snapshot"
    )["documents"]
    document = _validate_document(document, plan_documents[document_ordinal - 1])
    if document["document_id"] != reference["document_id"]:
        raise _error("semantic index document identity drifted")
    return document


def read_authenticated_family_first_structure_document_v1(
    capability: AuthenticatedFamilyFirstSemanticIndexV1,
    *,
    document_ordinal: int,
) -> dict[str, Any]:
    """Project one bank-blind complete-document axis for shared structure engines."""

    document = read_authenticated_family_first_semantic_document_v1(
        capability, document_ordinal=document_ordinal
    )
    pages = []
    for page in document["pages"]:
        pages.append(
            {
                "lines": [
                    {
                        "bbox": canonical_clone_v1(line["source_bbox_raw_pixels"]),
                        "source_line_index": line["line_ordinal"],
                        "source_text": None,
                        "vietocr_text": line["vietocr_text"],
                    }
                    for line in page["lines"]
                ],
                "page_sequence": page["physical_page"],
            }
        )
    return {
        "document_id": document["document_id"],
        "document_ordinal": document["document_ordinal"],
        "page_count": document["page_count"],
        "pages": pages,
    }
