"""Authenticate and consume the complete sharded PP-OCRv6 numeric axis."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import weakref
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bctc_ai.evaluation import family_first_numeric_cell_evidence_v1 as evidence_v1
from bctc_ai.evaluation import family_first_semantic_label_archive_v1 as archive_v1
from bctc_ai.ocr import family_first_ppocrv6_numeric_runner_v1 as runner_v1
from bctc_ai.ocr import family_first_ppocrv6_numeric_sharded_runner_v3 as runner_v3
from bctc_ai.ocr import family_first_vietocr_runner_v1 as file_ops_v1
from bctc_ai.ocr import ppocrv6_numeric_reference_blind_kernel_v1 as kernel_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "AuthenticatedFamilyFirstPPocrV6NumericIndexV3",
    "FamilyFirstPPocrV6NumericIndexV3Error",
    "authenticate_family_first_ppocrv6_numeric_index_v3",
    "finalize_authenticated_family_first_ppocrv6_numeric_index_v3",
    "project_authenticated_family_first_ppocrv6_numeric_index_v3",
    "read_authenticated_family_first_ppocrv6_numeric_document_v3",
    "read_authenticated_family_first_ppocrv6_numeric_evidence_batch_v3",
]


INDEX_ROOT = runner_v3.CACHE_ROOT / "verified-index"
RECEIPT_PATH = INDEX_ROOT / "verification-receipt.json"
FORMAT_VERSION = "FAMILY_FIRST_PPOCRV6_NUMERIC_INDEX_RECEIPT_V3"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_RECEIPT_FIELDS = {
    "aggregate_id",
    "aggregate_ref",
    "archive_id",
    "authority",
    "batch_id",
    "format_version",
    "metrics",
    "numeric_axis_sha256",
    "plan_id",
    "proposal_ref",
    "receipt_id",
    "state",
}
_AUTHORITY = {
    "accounting_authority": False,
    "all_reader_outputs_preserved": True,
    "blank_means_zero": False,
    "complete_contiguous_shard_aggregate_authenticated": True,
    "crop_bound_numeric_recognition_evidence_available": True,
    "dash_may_be_typed_as_zero_only_after_selected_crop_replay": True,
    "mapping_authority": False,
    "period_or_unit_authority": False,
    "quality_selection_absence_attestation": False,
    "retry_absence_attestation": False,
    "schema_authority": False,
    "semantic_text_authority": False,
    "single_physical_execution_attestation": False,
}
_SELECTION_FIELDS = {"document_ordinal", "line_ordinal", "physical_page"}


class FamilyFirstPPocrV6NumericIndexV3Error(RuntimeError):
    """The aggregate, source join, selected crop, or live receipt drifted."""


def _error(message: str) -> FamilyFirstPPocrV6NumericIndexV3Error:
    return FamilyFirstPPocrV6NumericIndexV3Error(message)


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


def _metrics(plan: dict[str, Any], aggregate: dict[str, Any]) -> dict[str, int]:
    return {
        "document_count": len(plan["documents"]),
        "empty_prediction_count": aggregate["metrics"]["empty_prediction_count"],
        "page_count": sum(item["page_count"] for item in plan["documents"]),
        "sample_count": aggregate["metrics"]["sample_count"],
        "shard_count": aggregate["metrics"]["shard_count"],
    }


def _axis(proposal_payload: bytes, sample_count: int) -> str:
    digest = hashlib.sha256()
    for _start, _stop, proposal in runner_v3._proposal_iterator(
        proposal_payload,
        first_sample_ordinal=1,
        expected_count=sample_count,
    ):
        digest.update(
            canonical_json_bytes_v1(
                {
                    "crop_sha256": proposal["crop_sha256"],
                    "raw_prediction": proposal["raw_prediction"],
                    "reader_score": proposal["reader_score"],
                    "sample_id": proposal["sample_id"],
                }
            )
        )
    return digest.hexdigest()


def _receipt(
    archive_manifest: dict[str, Any],
    batch: dict[str, Any],
    plan: dict[str, Any],
    aggregate: dict[str, Any],
    aggregate_payload: bytes,
    proposal_payload: bytes,
) -> dict[str, Any]:
    material = {
        "aggregate_id": aggregate["aggregate_id"],
        "aggregate_ref": {
            "path": (runner_v3.AGGREGATE_ROOT / runner_v3._AGGREGATE_MANIFEST_NAME).as_posix(),
            "sha256": _sha(aggregate_payload),
            "size_bytes": len(aggregate_payload),
        },
        "archive_id": archive_manifest["archive_id"],
        "authority": canonical_clone_v1(_AUTHORITY),
        "batch_id": batch["batch_id"],
        "format_version": FORMAT_VERSION,
        "metrics": _metrics(plan, aggregate),
        "numeric_axis_sha256": _axis(proposal_payload, batch["sample_count"]),
        "plan_id": plan["plan_id"],
        "proposal_ref": canonical_clone_v1(aggregate["artifacts"]["numeric_proposals"]),
        "state": "VERIFIED_COMPLETE_ORDERED_SHARDED_PPOCRV6_NUMERIC_PROPOSAL_AXIS",
    }
    return _validate_receipt(
        {**material, "receipt_id": "ffpniv3:receipt:" + canonical_json_sha256_v1(material)}
    )


def _validate_receipt(value: Any) -> dict[str, Any]:
    metrics = value.get("metrics") if type(value) is dict else None
    if (
        type(value) is not dict
        or set(value) != _RECEIPT_FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["state"] != "VERIFIED_COMPLETE_ORDERED_SHARDED_PPOCRV6_NUMERIC_PROPOSAL_AXIS"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(metrics) is not dict
        or set(metrics)
        != {
            "document_count",
            "empty_prediction_count",
            "page_count",
            "sample_count",
            "shard_count",
        }
        or any(type(metrics[field]) is not int for field in metrics)
        or metrics["document_count"] <= 0
        or metrics["page_count"] <= 0
        or metrics["sample_count"] <= 0
        or metrics["shard_count"] <= 0
        or not 0 <= metrics["empty_prediction_count"] <= metrics["sample_count"]
        or type(value["numeric_axis_sha256"]) is not str
        or _SHA256.fullmatch(value["numeric_axis_sha256"]) is None
        or type(value["aggregate_id"]) is not str
        or not value["aggregate_id"].startswith("ffpnav3:aggregate:")
        or type(value["archive_id"]) is not str
        or not value["archive_id"].startswith("ffslav1:archive:")
        or type(value["batch_id"]) is not str
        or not value["batch_id"].startswith("ffslcv1:batch:")
        or type(value["plan_id"]) is not str
        or not value["plan_id"].startswith("ffslpv1:plan:")
    ):
        raise _error("numeric V3 index receipt contract drifted")
    try:
        archive_v1._ref(value["aggregate_ref"], "numeric V3 aggregate receipt ref")
        archive_v1._ref(value["proposal_ref"], "numeric V3 proposal receipt ref")
    except archive_v1.FamilyFirstSemanticLabelArchiveV1Error as exc:
        raise _error("numeric V3 index artifact reference drifted") from exc
    material = canonical_clone_v1(value)
    receipt_id = material.pop("receipt_id")
    if receipt_id != "ffpniv3:receipt:" + canonical_json_sha256_v1(material):
        raise _error("numeric V3 index receipt identity drifted")
    return canonical_clone_v1(value)


def _publish_receipt(root: Path, payload: bytes) -> None:
    cache_fd, shards_fd = runner_v3._cache_fds(root)
    stage_name = f".index-stage-{secrets.token_hex(8)}"
    stage_identity: tuple[int, int] | None = None
    try:
        try:
            os.stat(INDEX_ROOT.name, dir_fd=cache_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise _error("fixed numeric V3 verified index already exists")
        os.mkdir(stage_name, 0o700, dir_fd=cache_fd)
        stage_fd = os.open(
            stage_name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=cache_fd
        )
        try:
            opened = os.fstat(stage_fd)
            stage_identity = (opened.st_dev, opened.st_ino)
            file_ops_v1._write_exclusive(stage_fd, RECEIPT_PATH.name, payload)
            os.fsync(stage_fd)
        finally:
            os.close(stage_fd)
        file_ops_v1._rename_noreplace_fd(cache_fd, stage_name, INDEX_ROOT.name)
        named = os.stat(INDEX_ROOT.name, dir_fd=cache_fd, follow_symlinks=False)
        if stage_identity is None or (named.st_dev, named.st_ino) != stage_identity:
            raise _error("published numeric V3 index inode differs from its completed stage")
        stage_name = ""
    finally:
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
                        try:
                            os.unlink(RECEIPT_PATH.name, dir_fd=descriptor)
                        except FileNotFoundError:
                            pass
                    finally:
                        os.close(descriptor)
                    os.rmdir(stage_name, dir_fd=cache_fd)
            except FileNotFoundError:
                pass
        os.close(shards_fd)
        os.close(cache_fd)


def finalize_authenticated_family_first_ppocrv6_numeric_index_v3(
    project_root: Path,
    archive_capability: archive_v1.AuthenticatedFamilyFirstSemanticLabelArchiveV1,
    *,
    model_cache: Path,
) -> dict[str, Any]:
    """Replay the complete shard aggregate and publish its no-replace receipt."""

    root = archive_v1._root(project_root)
    state, archive_manifest, batch, plan, _private = archive_v1._archive_payloads(
        archive_capability
    )
    if state.root != root:
        raise _error("numeric archive belongs to another project root")
    aggregate, aggregate_payload, proposal_payload, _offsets = (
        runner_v3.validate_authenticated_family_first_ppocrv6_numeric_aggregate_v3(
            root, archive_capability, model_cache=model_cache
        )
    )
    receipt = _receipt(
        archive_manifest,
        batch,
        plan,
        aggregate,
        aggregate_payload,
        proposal_payload,
    )
    _publish_receipt(root, canonical_json_bytes_v1(receipt))
    return receipt


@dataclass(frozen=True)
class _IndexState:
    root: Path
    archive: archive_v1.AuthenticatedFamilyFirstSemanticLabelArchiveV1
    model_cache: Path
    receipt_payload: bytes
    aggregate_payload: bytes
    proposal_payload: bytes
    offsets: tuple[tuple[int, int], ...]


class AuthenticatedFamilyFirstPPocrV6NumericIndexV3:
    """Opaque live handle for the complete sharded numeric proposal axis."""

    __slots__ = ("__weakref__",)

    def __new__(cls, token: object | None = None):
        if token is not _MINT:
            raise TypeError("family-first numeric V3 index handles cannot be constructed")
        return super().__new__(cls)

    def __copy__(self) -> None:
        raise TypeError("family-first numeric V3 index handles cannot be copied")

    def __deepcopy__(self, _memo: dict[int, Any]) -> None:
        raise TypeError("family-first numeric V3 index handles cannot be copied")

    def __reduce__(self) -> None:
        raise TypeError("family-first numeric V3 index handles cannot be pickled")


_MINT = object()
_INDICES: weakref.WeakKeyDictionary[AuthenticatedFamilyFirstPPocrV6NumericIndexV3, _IndexState] = (
    weakref.WeakKeyDictionary()
)


def authenticate_family_first_ppocrv6_numeric_index_v3(
    project_root: Path,
    archive_capability: archive_v1.AuthenticatedFamilyFirstSemanticLabelArchiveV1,
    *,
    model_cache: Path,
) -> AuthenticatedFamilyFirstPPocrV6NumericIndexV3:
    """Replay all shards, aggregate, receipt, archive, model and Git lineage."""

    root = archive_v1._root(project_root)
    state, archive_manifest, batch, plan, _private = archive_v1._archive_payloads(
        archive_capability
    )
    if state.root != root:
        raise _error("numeric archive belongs to another project root")
    aggregate, aggregate_payload, proposal_payload, offsets = (
        runner_v3.validate_authenticated_family_first_ppocrv6_numeric_aggregate_v3(
            root, archive_capability, model_cache=model_cache
        )
    )
    receipt_payload = _root_bytes(root, RECEIPT_PATH, "numeric V3 index receipt")
    persisted = _validate_receipt(_canonical_object(receipt_payload, "numeric V3 index receipt"))
    expected = _receipt(
        archive_manifest,
        batch,
        plan,
        aggregate,
        aggregate_payload,
        proposal_payload,
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("numeric V3 index receipt does not replay exactly")
    capability = AuthenticatedFamilyFirstPPocrV6NumericIndexV3(_MINT)
    _INDICES[capability] = _IndexState(
        root,
        archive_capability,
        model_cache.resolve(),
        receipt_payload,
        aggregate_payload,
        proposal_payload,
        offsets,
    )
    return capability


def _live_index(
    capability: Any,
) -> tuple[_IndexState, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    if type(capability) is not AuthenticatedFamilyFirstPPocrV6NumericIndexV3:
        raise _error("one exact live family-first numeric V3 index handle is required")
    state = _INDICES.get(capability)
    if state is None:
        raise _error("family-first numeric V3 index handle is not live")
    archive_state, _archive_manifest, batch, plan, private = archive_v1._archive_payloads(
        state.archive
    )
    receipt_payload = _root_bytes(state.root, RECEIPT_PATH, "numeric V3 index receipt")
    aggregate_payload = _root_bytes(
        state.root,
        runner_v3.AGGREGATE_ROOT / runner_v3._AGGREGATE_MANIFEST_NAME,
        "numeric V3 aggregate manifest",
    )
    proposal_payload = _root_bytes(
        state.root,
        runner_v3.AGGREGATE_ROOT / runner_v3._PROPOSAL_NAME,
        "numeric V3 aggregate proposals",
    )
    if (
        archive_state.root != state.root
        or receipt_payload != state.receipt_payload
        or aggregate_payload != state.aggregate_payload
        or proposal_payload != state.proposal_payload
    ):
        raise _error("numeric V3 live artifacts changed after authentication")
    receipt = _validate_receipt(_canonical_object(receipt_payload, "numeric V3 receipt"))
    aggregate = _canonical_object(aggregate_payload, "numeric V3 aggregate")
    runner_v3._git_ledger(state.root, aggregate.get("git_binding"))
    config_payload, config_ref = runner_v3._configuration_ref(state.root)
    live_model, _directory = kernel_v1._recognizer_projection(
        state.root,
        state.model_cache,
        paddle_distribution="paddlepaddle-gpu",
    )
    if (
        config_payload == b""
        or not same_typed_json_v1(config_ref, aggregate["input"]["configuration_ref"])
        or not same_typed_json_v1(live_model, aggregate["input"]["model"])
    ):
        raise _error("numeric V3 live config/model lineage drifted")
    return state, receipt, batch, plan, private


def project_authenticated_family_first_ppocrv6_numeric_index_v3(
    capability: AuthenticatedFamilyFirstPPocrV6NumericIndexV3,
) -> dict[str, Any]:
    """Project identities and denominators without numeric strings/provenance."""

    _state, receipt, _batch, _plan, _private = _live_index(capability)
    return {
        "authority": canonical_clone_v1(_AUTHORITY),
        "format_version": FORMAT_VERSION,
        "metrics": canonical_clone_v1(receipt["metrics"]),
        "receipt_id": receipt["receipt_id"],
        "state": receipt["state"],
    }


def _proposal_at(state: _IndexState, ordinal: int) -> dict[str, Any]:
    start, stop = state.offsets[ordinal - 1]
    raw = state.proposal_payload[start:stop]
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"))
        return runner_v1._validate_result(value, ordinal)
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        runner_v1.FamilyFirstPPocrV6NumericRunnerV1Error,
    ) as exc:
        raise _error("numeric V3 proposal snapshot drifted") from exc


def _document_range(private: dict[str, Any], document_ordinal: int) -> tuple[int, int]:
    starts = [
        index
        for index, item in enumerate(private["samples"])
        if item["document_ordinal"] == document_ordinal
    ]
    if not starts:
        raise _error("numeric V3 source document retained no samples")
    return starts[0], starts[-1] + 1


def read_authenticated_family_first_ppocrv6_numeric_document_v3(
    capability: AuthenticatedFamilyFirstPPocrV6NumericIndexV3,
    *,
    document_ordinal: int,
) -> dict[str, Any]:
    """Read one complete source-bound raw numeric-recognition proposal axis."""

    state, receipt, batch, plan, private = _live_index(capability)
    if (
        type(document_ordinal) is not int
        or not 1 <= document_ordinal <= receipt["metrics"]["document_count"]
    ):
        raise _error("numeric V3 document ordinal lies outside the corpus")
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
        raise _error("numeric V3 evidence selection must be one non-empty exact tuple")
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
            raise _error("numeric V3 evidence selection locator drifted")
        result.append((raw["document_ordinal"], raw["physical_page"], raw["line_ordinal"]))
    if result != sorted(set(result)):
        raise _error("numeric V3 evidence selections must be unique and source-ordered")
    return tuple(result)


def read_authenticated_family_first_ppocrv6_numeric_evidence_batch_v3(
    capability: AuthenticatedFamilyFirstPPocrV6NumericIndexV3,
    *,
    selections: tuple[dict[str, int], ...],
) -> tuple[dict[str, Any], ...]:
    """Rebuild typed crop-bound evidence for selected source lines."""

    locators = _selections(selections)
    state, _receipt_value, batch, _plan, private = _live_index(capability)
    by_locator = {
        (item["document_ordinal"], item["physical_page"], item["line_ordinal"]): index
        for index, item in enumerate(private["samples"])
    }
    try:
        targets = {locator: by_locator[locator] for locator in locators}
    except KeyError as exc:
        raise _error("numeric V3 evidence selection does not identify one source line") from exc
    target_indices = {index: locator for locator, index in targets.items()}
    first_target = min(target_indices)
    final_target = max(target_indices)
    session = archive_v1.open_authenticated_family_first_semantic_label_reader_session_v1(
        state.archive
    )
    kernel_v1._seek_authenticated_archive_reader_v1(session, first_sample_ordinal=first_target + 1)
    cursor = first_target
    built: dict[tuple[int, int, int], dict[str, Any]] = {}
    while cursor <= final_target:
        chunk = archive_v1.read_authenticated_family_first_semantic_label_chunk_v1(
            session, maximum_samples=min(4096, final_target + 1 - cursor)
        )
        if not chunk:
            raise _error("authenticated crop stream ended before numeric V3 selections")
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
                    raise _error("selected numeric V3 crop/source/proposal cross-link drifted")
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
        raise _error("numeric V3 evidence batch did not retain every selection")
    return tuple(built[locator] for locator in locators)
