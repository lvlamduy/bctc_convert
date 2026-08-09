"""Authenticated evidence envelopes for sealed causal native page reads.

This module is an add-only adapter around :mod:`bctc_ai.ocr.causal_native_text`.
It does not alter the registered causal policy or visibility implementation.  Its
job is narrower: bind one sealed page request to authenticated PDF/config/runtime
bytes, serialize the source-visible result without leaking quarantined text, and
support a byte- and type-exact replay from the same authenticated inputs.

The causal core's internal paired rasters are deliberately not claimed here.  The
sealed public wrapper does not expose the exact rasters used by its decision, and
re-rendering a second pair would not prove that those were the decision inputs.
"""

from __future__ import annotations

import json
import os
import re
import stat
import tempfile
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from hashlib import sha256
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as distribution_version
from math import isfinite
from pathlib import Path
from typing import Any

import fitz

from bctc_ai.ocr.causal_native_text import (
    load_causal_native_text_policy,
    read_causal_native_text_page,
)

__all__ = [
    "BACKEND_FORMAT_VERSION",
    "CausalNativeTextEvidenceError",
    "RESULT_FORMAT_VERSION",
    "TERMINAL_STATUSES",
    "build_causal_native_text_evidence",
    "validate_causal_native_text_evidence_replay",
]


class CausalNativeTextEvidenceError(RuntimeError):
    """An authenticated causal-native page envelope cannot be established."""


BACKEND_FORMAT_VERSION = "BANK_CORPUS_WAVE_1_CAUSAL_NATIVE_BACKEND_PAYLOAD_V1"
RESULT_FORMAT_VERSION = "BANK_CORPUS_WAVE_1_ROLE_B_CAUSAL_NATIVE_PAGE_READ_RESULT_V1"
TERMINAL_STATUSES = frozenset(
    {
        "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
        "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY",
        "UNRESOLVED_NATIVE_TEXT_QUALITY",
    }
)

_ROUTE = "CAUSAL_NATIVE_TEXT"
_PROVIDER = "PYMUPDF_CAUSAL_NATIVE_TEXT_VISIBILITY_V1"
_CAUSAL_POLICY_RECORD_PATH = "config/ocr/causal-native-text-v1.yaml"
_QUALITY_POLICY_RECORD_PATH = "config/ocr/native-text-quality-v2.yaml"
_BACKEND_CLAIM_BOUNDARY = (
    "AUTHENTICATED_SEALED_CAUSAL_NATIVE_WRAPPER_OUTPUT_FOR_ONE_EXACT_PAGE_REQUEST_ONLY"
)
_RESULT_CLAIM_BOUNDARY = "SOURCE_VISIBLE_NATIVE_PAGE_TEXT_AND_GEOMETRY_EVIDENCE_ONLY"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SAFE_TYPE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")

_REQUEST_FIELDS = {
    "bank_identity_used",
    "filename_used",
    "format_version",
    "git_commit",
    "historical_values_used",
    "implementation_ledger_sha256",
    "input_ledger_sha256",
    "physical_page",
    "pre_ocr_feature_fingerprint_sha256",
    "provider_identity_sha256",
    "render_runtime_identity_sha256",
    "render_specification",
    "role_a_used",
    "route",
    "route_plan_sha256",
    "schema_used",
    "selection_receipt_sha256",
    "sentinel_sha256",
    "source_sha256",
    "source_size_bytes",
}
_PROVIDER_LEDGER_FIELDS = {
    "config_records",
    "ocr_fallback_allowed",
    "provider",
    "pymupdf_binding_version",
    "pymupdf_distribution_version",
    "pymupdf_runtime_versions",
    "sha256",
}
_CONFIG_RECORD_FIELDS = {"path", "sha256", "size_bytes"}
_WORD_FIELDS = {
    "raw_text",
    "score",
    "score_kind",
    "canonical_bbox_mpt",
    "block_number",
    "line_number",
    "word_number",
}
_LINE_FIELDS = {
    "raw_text",
    "score",
    "score_kind",
    "canonical_bbox_mpt",
    "block_number",
    "line_number",
    "words",
}
_QUARANTINED_FIELDS = {
    "page",
    "text_sha256",
    "nonwhitespace_character_count",
    "bbox_mpt",
    "block_number",
    "line_number",
    "span_number",
    "color",
    "alpha",
    "render_sequence",
    "occluding_sequence",
    "occluding_object_type",
    "reason",
}
_NORMALIZED_PAYLOAD_FIELDS = {
    "status",
    "failure_type",
    "native_text_quality",
    "corruption_markers",
    "lines",
    "words",
    "quarantined_spans",
    "ocr_fallback_used",
    "source_blank_claimed",
}
_BACKEND_FIELDS = {
    "format_version",
    "status",
    "claim_boundary",
    "document_id",
    "source_sha256",
    "source_size_bytes",
    "physical_page",
    "route",
    "request_sha256",
    "request",
    "full_control_identity_sha256",
    "provider_identity_sha256",
    "provider_runtime_ledger",
    "causal_native_policy_identity",
    "native_text_quality_policy_identity",
    "coordinate_authority",
    "causal_native_payload",
    "ocr_fallback_used",
    "source_blank_claimed",
    "safety",
}
_RESULT_FIELDS = {
    "format_version",
    "status",
    "claim_boundary",
    "document_id",
    "source_sha256",
    "source_size_bytes",
    "physical_page",
    "route",
    "request_sha256",
    "request",
    "full_control_identity_sha256",
    "provider_identity_sha256",
    "backend_payload_sha256",
    "coordinate_authority",
    "failure_type",
    "native_text_quality",
    "corruption_markers",
    "lines",
    "words",
    "quarantined_spans",
    "metrics",
    "ocr_fallback_used",
    "source_blank_claimed",
    "safety",
}


def _canonical_json_bytes(value: Any) -> bytes:
    _validate_json_tree(value)
    try:
        serialized = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError, UnicodeError) as error:
        raise CausalNativeTextEvidenceError("evidence is not canonical JSON") from error
    return (serialized + "\n").encode("utf-8")


def _canonical_json_sha256(value: Any) -> str:
    return sha256(_canonical_json_bytes(value)).hexdigest()


def _canonical_clone(value: Any) -> Any:
    return json.loads(_canonical_json_bytes(value))


def _validate_json_tree(value: Any) -> None:
    value_type = type(value)
    if value is None or value_type in {bool, int, str}:
        return
    if value_type is float:
        if not isfinite(value):
            raise CausalNativeTextEvidenceError("evidence contains a non-finite number")
        return
    if value_type is list:
        for item in value:
            _validate_json_tree(item)
        return
    if value_type is dict:
        if any(type(key) is not str for key in value):
            raise CausalNativeTextEvidenceError("evidence object keys must be strings")
        for item in value.values():
            _validate_json_tree(item)
        return
    raise CausalNativeTextEvidenceError("evidence contains a non-JSON value type")


def _same_typed_json(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(
            _same_typed_json(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _same_typed_json(left_item, right_item)
            for left_item, right_item in zip(left, right, strict=True)
        )
    return left == right


def _require_sha256(value: Any, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise CausalNativeTextEvidenceError(f"{label} is not a lowercase SHA-256")
    return value


def _require_nonnegative_integer(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise CausalNativeTextEvidenceError(f"{label} must be a non-negative integer")
    return value


def _require_positive_integer(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise CausalNativeTextEvidenceError(f"{label} must be a positive integer")
    return value


def _safety_boundary() -> dict[str, bool]:
    return {
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


def _coordinate_authority() -> dict[str, Any]:
    return {
        "canonical_coordinate_system": "UNROTATED_PDF_MILLI_POINTS_TOP_LEFT",
        "coordinate_unit": "MILLI_POINT",
        "geometry_source": "PYMUPDF_NATIVE_TEXT_WORD_GEOMETRY",
        "pdf_rotation_applied_to_coordinates": False,
    }


def _stable_regular_bytes(path: Path) -> bytes:
    if not isinstance(path, Path):
        raise CausalNativeTextEvidenceError("policy locator must be a Path")
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        named_before = path.stat(follow_symlinks=False)
        descriptor = os.open(path, flags)
    except OSError as error:
        raise CausalNativeTextEvidenceError("authenticated policy cannot be opened") from error
    try:
        opened_before = os.fstat(descriptor)
        if not stat.S_ISREG(named_before.st_mode) or not stat.S_ISREG(opened_before.st_mode):
            raise CausalNativeTextEvidenceError("authenticated policy is not a regular file")
        identity = (opened_before.st_dev, opened_before.st_ino, opened_before.st_size)
        if (named_before.st_dev, named_before.st_ino, named_before.st_size) != identity:
            raise CausalNativeTextEvidenceError("authenticated policy changed while opening")
        chunks: list[bytes] = []
        while block := os.read(descriptor, 1024 * 1024):
            chunks.append(block)
        opened_after = os.fstat(descriptor)
        named_after = path.stat(follow_symlinks=False)
        if (
            (opened_after.st_dev, opened_after.st_ino, opened_after.st_size) != identity
            or (named_after.st_dev, named_after.st_ino, named_after.st_size) != identity
            or stat.S_ISLNK(named_after.st_mode)
        ):
            raise CausalNativeTextEvidenceError("authenticated policy changed while reading")
        payload = b"".join(chunks)
        if len(payload) != opened_before.st_size:
            raise CausalNativeTextEvidenceError("authenticated policy size changed while reading")
        return payload
    except OSError as error:
        raise CausalNativeTextEvidenceError("authenticated policy cannot be read stably") from error
    finally:
        os.close(descriptor)


def _write_private_file(path: Path, payload: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise CausalNativeTextEvidenceError(
                    "authenticated policy copy could not be completed"
                )
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def _authenticated_policy_copies(
    causal_payload: bytes,
    quality_payload: bytes,
) -> Iterator[tuple[Path, Path]]:
    with tempfile.TemporaryDirectory(prefix="bctc-causal-native-policy-") as directory:
        root = Path(directory)
        causal_path = root / "causal-native-text-v1.yaml"
        quality_path = root / "native-text-quality-v2.yaml"
        _write_private_file(causal_path, causal_payload)
        _write_private_file(quality_path, quality_payload)
        if (
            sha256(_stable_regular_bytes(causal_path)).digest() != sha256(causal_payload).digest()
            or sha256(_stable_regular_bytes(quality_path)).digest()
            != sha256(quality_payload).digest()
        ):
            raise CausalNativeTextEvidenceError("authenticated policy copy drifted")
        yield causal_path, quality_path


def _validate_request(
    request: Mapping[str, Any],
    *,
    request_sha256: str,
    source_bytes: bytes,
    document_id: str,
    physical_page: int,
    provider_identity_sha256: str,
) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        raise CausalNativeTextEvidenceError("sealed request must be an object")
    request_copy = _canonical_clone(dict(request))
    if set(request_copy) != _REQUEST_FIELDS:
        raise CausalNativeTextEvidenceError("sealed request fields drifted")
    if request_copy["format_version"] != "BANK_CORPUS_WAVE_1_PAGE_READ_REQUEST_V1":
        raise CausalNativeTextEvidenceError("sealed request format drifted")
    if request_copy["route"] != _ROUTE:
        raise CausalNativeTextEvidenceError("sealed request route drifted")
    if request_copy["render_runtime_identity_sha256"] is not None:
        raise CausalNativeTextEvidenceError("native request has a render-runtime identity")
    if request_copy["render_specification"] is not None:
        raise CausalNativeTextEvidenceError("native request has an OCR render specification")
    for safety_key in (
        "bank_identity_used",
        "filename_used",
        "historical_values_used",
        "role_a_used",
        "schema_used",
    ):
        if request_copy[safety_key] is not False:
            raise CausalNativeTextEvidenceError("sealed request safety boundary drifted")
    if (
        type(request_copy["git_commit"]) is not str
        or _GIT_SHA1_RE.fullmatch(request_copy["git_commit"]) is None
    ):
        raise CausalNativeTextEvidenceError("sealed request Git identity drifted")
    for identity_key in (
        "implementation_ledger_sha256",
        "input_ledger_sha256",
        "pre_ocr_feature_fingerprint_sha256",
        "provider_identity_sha256",
        "route_plan_sha256",
        "selection_receipt_sha256",
        "sentinel_sha256",
        "source_sha256",
    ):
        _require_sha256(request_copy[identity_key], f"sealed request {identity_key}")
    if request_copy["provider_identity_sha256"] != provider_identity_sha256:
        raise CausalNativeTextEvidenceError("sealed request provider identity drifted")
    if request_copy["physical_page"] != physical_page:
        raise CausalNativeTextEvidenceError("sealed request physical page drifted")
    if request_copy["source_size_bytes"] != len(source_bytes):
        raise CausalNativeTextEvidenceError("sealed request source size drifted")
    observed_source_sha256 = sha256(source_bytes).hexdigest()
    if request_copy["source_sha256"] != observed_source_sha256:
        raise CausalNativeTextEvidenceError("sealed request source hash drifted")
    if document_id != f"sha256:{observed_source_sha256}":
        raise CausalNativeTextEvidenceError("document identity does not bind the source")
    _require_positive_integer(physical_page, "physical page")
    _require_positive_integer(request_copy["source_size_bytes"], "source size")
    _require_sha256(request_sha256, "request identity")
    if _canonical_json_sha256(request_copy) != request_sha256:
        raise CausalNativeTextEvidenceError("sealed request canonical hash drifted")
    return request_copy


def _runtime_versions() -> list[str | None]:
    runtime = getattr(fitz, "version", None)
    if not isinstance(runtime, tuple) or any(
        item is not None and type(item) is not str for item in runtime
    ):
        raise CausalNativeTextEvidenceError("PyMuPDF runtime version tuple is unavailable")
    return list(runtime)


def _validate_provider_runtime_ledger(
    provider_runtime_ledger: Mapping[str, Any],
    *,
    causal_policy_path: Path,
    quality_policy_path: Path,
) -> tuple[dict[str, Any], bytes, bytes, dict[str, Any], dict[str, Any]]:
    if not isinstance(provider_runtime_ledger, Mapping):
        raise CausalNativeTextEvidenceError("provider runtime ledger must be an object")
    ledger = _canonical_clone(dict(provider_runtime_ledger))
    if set(ledger) != _PROVIDER_LEDGER_FIELDS:
        raise CausalNativeTextEvidenceError("provider runtime ledger fields drifted")
    if ledger["provider"] != _PROVIDER or ledger["ocr_fallback_allowed"] is not False:
        raise CausalNativeTextEvidenceError("provider runtime safety boundary drifted")
    provider_identity = _require_sha256(ledger["sha256"], "provider runtime identity")
    identity_projection = {key: value for key, value in ledger.items() if key != "sha256"}
    if _canonical_json_sha256(identity_projection) != provider_identity:
        raise CausalNativeTextEvidenceError("provider runtime ledger identity drifted")
    binding_version = getattr(fitz, "VersionBind", None)
    try:
        installed_distribution = distribution_version("PyMuPDF")
    except PackageNotFoundError as error:
        raise CausalNativeTextEvidenceError(
            "PyMuPDF distribution identity is unavailable"
        ) from error
    if (
        type(binding_version) is not str
        or ledger["pymupdf_binding_version"] != binding_version
        or ledger["pymupdf_distribution_version"] != installed_distribution
        or not _same_typed_json(ledger["pymupdf_runtime_versions"], _runtime_versions())
    ):
        raise CausalNativeTextEvidenceError("PyMuPDF runtime identity drifted")
    config_records = ledger["config_records"]
    if type(config_records) is not list or len(config_records) != 2:
        raise CausalNativeTextEvidenceError("provider config ledger drifted")
    records: dict[str, dict[str, Any]] = {}
    for record in config_records:
        if type(record) is not dict or set(record) != _CONFIG_RECORD_FIELDS:
            raise CausalNativeTextEvidenceError("provider config record fields drifted")
        path = record["path"]
        if type(path) is not str or path in records:
            raise CausalNativeTextEvidenceError("provider config record path drifted")
        _require_sha256(record["sha256"], "provider config identity")
        _require_positive_integer(record["size_bytes"], "provider config size")
        records[path] = record
    if set(records) != {_CAUSAL_POLICY_RECORD_PATH, _QUALITY_POLICY_RECORD_PATH}:
        raise CausalNativeTextEvidenceError("provider config record set drifted")
    causal_bytes = _stable_regular_bytes(causal_policy_path)
    quality_bytes = _stable_regular_bytes(quality_policy_path)
    for record_path, payload in (
        (_CAUSAL_POLICY_RECORD_PATH, causal_bytes),
        (_QUALITY_POLICY_RECORD_PATH, quality_bytes),
    ):
        record = records[record_path]
        if record["size_bytes"] != len(payload) or record["sha256"] != sha256(payload).hexdigest():
            raise CausalNativeTextEvidenceError("provider config bytes drifted")
    return (
        ledger,
        causal_bytes,
        quality_bytes,
        _canonical_clone(records[_CAUSAL_POLICY_RECORD_PATH]),
        _canonical_clone(records[_QUALITY_POLICY_RECORD_PATH]),
    )


def _validate_bbox(value: Any, label: str) -> list[int]:
    if type(value) is not list or len(value) != 4 or any(type(item) is not int for item in value):
        raise CausalNativeTextEvidenceError(f"{label} must be four integer millipoints")
    if value[0] > value[2] or value[1] > value[3]:
        raise CausalNativeTextEvidenceError(f"{label} has inverted geometry")
    return value


def _validate_word(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _WORD_FIELDS:
        raise CausalNativeTextEvidenceError("native word fields drifted")
    raw_text = value["raw_text"]
    if (
        type(raw_text) is not str
        or not raw_text
        or not any(not character.isspace() for character in raw_text)
    ):
        raise CausalNativeTextEvidenceError("native word text is empty")
    if value["score"] is not None or value["score_kind"] != ("NATIVE_TEXT_NO_RECOGNITION_SCORE"):
        raise CausalNativeTextEvidenceError("native word score semantics drifted")
    _validate_bbox(value["canonical_bbox_mpt"], "native word bbox")
    for key in ("block_number", "line_number", "word_number"):
        _require_nonnegative_integer(value[key], f"native word {key}")
    return value


def _validate_lines_and_words(lines: Any, words: Any) -> None:
    if type(lines) is not list or type(words) is not list:
        raise CausalNativeTextEvidenceError("native text arrays drifted")
    for word in words:
        _validate_word(word)
    flattened: list[dict[str, Any]] = []
    previous_line_identity: tuple[int, int] | None = None
    for line in lines:
        if type(line) is not dict or set(line) != _LINE_FIELDS:
            raise CausalNativeTextEvidenceError("native line fields drifted")
        if line["score"] is not None or line["score_kind"] != ("NATIVE_TEXT_NO_RECOGNITION_SCORE"):
            raise CausalNativeTextEvidenceError("native line score semantics drifted")
        block_number = _require_nonnegative_integer(
            line["block_number"], "native line block_number"
        )
        line_number = _require_nonnegative_integer(line["line_number"], "native line line_number")
        line_identity = (block_number, line_number)
        if previous_line_identity is not None and line_identity <= previous_line_identity:
            raise CausalNativeTextEvidenceError("native line ordering drifted")
        previous_line_identity = line_identity
        line_words = line["words"]
        if type(line_words) is not list or not line_words:
            raise CausalNativeTextEvidenceError("native line has no words")
        previous_word_number: int | None = None
        for word in line_words:
            _validate_word(word)
            if (word["block_number"], word["line_number"]) != line_identity:
                raise CausalNativeTextEvidenceError("native word line identity drifted")
            if previous_word_number is not None and word["word_number"] <= previous_word_number:
                raise CausalNativeTextEvidenceError("native word ordering drifted")
            previous_word_number = word["word_number"]
        expected_text = " ".join(word["raw_text"] for word in line_words)
        if line["raw_text"] != expected_text:
            raise CausalNativeTextEvidenceError("native line text projection drifted")
        expected_bbox = [
            min(word["canonical_bbox_mpt"][0] for word in line_words),
            min(word["canonical_bbox_mpt"][1] for word in line_words),
            max(word["canonical_bbox_mpt"][2] for word in line_words),
            max(word["canonical_bbox_mpt"][3] for word in line_words),
        ]
        if not _same_typed_json(line["canonical_bbox_mpt"], expected_bbox):
            raise CausalNativeTextEvidenceError("native line geometry projection drifted")
        flattened.extend(line_words)
    if not _same_typed_json(flattened, words):
        raise CausalNativeTextEvidenceError("native line/word projection drifted")


def _validate_quarantined_spans(value: Any, *, physical_page: int) -> None:
    if type(value) is not list:
        raise CausalNativeTextEvidenceError("quarantined spans must be an array")
    for span in value:
        if type(span) is not dict or set(span) != _QUARANTINED_FIELDS:
            raise CausalNativeTextEvidenceError("quarantined span fields drifted")
        if span["page"] != physical_page:
            raise CausalNativeTextEvidenceError("quarantined span page drifted")
        _require_sha256(span["text_sha256"], "quarantined text identity")
        _require_nonnegative_integer(
            span["nonwhitespace_character_count"],
            "quarantined nonwhitespace character count",
        )
        _validate_bbox(span["bbox_mpt"], "quarantined span bbox")
        for key in (
            "block_number",
            "line_number",
            "span_number",
            "render_sequence",
        ):
            _require_nonnegative_integer(span[key], f"quarantined span {key}")
        if type(span["color"]) is not int or not 0 <= span["color"] <= 0xFFFFFF:
            raise CausalNativeTextEvidenceError("quarantined span color drifted")
        if type(span["alpha"]) is not int or not 0 <= span["alpha"] <= 255:
            raise CausalNativeTextEvidenceError("quarantined span alpha drifted")
        if span["occluding_sequence"] is not None:
            _require_nonnegative_integer(
                span["occluding_sequence"], "quarantined occluding sequence"
            )
        if (
            span["occluding_object_type"] is not None
            and type(span["occluding_object_type"]) is not str
        ):
            raise CausalNativeTextEvidenceError("quarantined object type drifted")
        if type(span["reason"]) is not str or not span["reason"]:
            raise CausalNativeTextEvidenceError("quarantined span reason drifted")


def _normalize_native_payload(raw_payload: Any, *, physical_page: int) -> dict[str, Any]:
    if type(raw_payload) is not dict:
        raise CausalNativeTextEvidenceError("sealed causal wrapper returned a non-object")
    status = raw_payload.get("status")
    if status not in TERMINAL_STATUSES:
        raise CausalNativeTextEvidenceError("sealed causal wrapper status drifted")
    if raw_payload.get("ocr_fallback_used") is not False:
        raise CausalNativeTextEvidenceError("sealed causal wrapper used an OCR fallback")
    if raw_payload.get("source_blank_claimed") is not False:
        raise CausalNativeTextEvidenceError("sealed causal wrapper claimed a blank source")
    if status == "CAUSAL_NATIVE_TEXT_READ_COMPLETE":
        expected_fields = {
            "status",
            "native_text_quality",
            "corruption_markers",
            "lines",
            "words",
            "quarantined_spans",
            "ocr_fallback_used",
            "source_blank_claimed",
        }
    elif status == "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY":
        expected_fields = {
            "status",
            "failure_type",
            "lines",
            "words",
            "quarantined_spans",
            "ocr_fallback_used",
            "source_blank_claimed",
        }
    else:
        expected_fields = {
            "status",
            "native_text_quality",
            "corruption_markers",
            "lines",
            "words",
            "quarantined_spans",
            "ocr_fallback_used",
            "source_blank_claimed",
        }
    if set(raw_payload) != expected_fields:
        raise CausalNativeTextEvidenceError("sealed causal wrapper fields drifted")

    lines = _canonical_clone(raw_payload["lines"])
    words = _canonical_clone(raw_payload["words"])
    quarantined = _canonical_clone(raw_payload["quarantined_spans"])
    _validate_lines_and_words(lines, words)
    _validate_quarantined_spans(quarantined, physical_page=physical_page)

    failure_type: str | None = None
    native_text_quality: str | None = None
    corruption_markers: list[str] = []
    if status == "CAUSAL_NATIVE_TEXT_READ_COMPLETE":
        if raw_payload["native_text_quality"] != "USABLE_TEXT_LAYER" or not words:
            raise CausalNativeTextEvidenceError("complete native result quality drifted")
        native_text_quality = "USABLE_TEXT_LAYER"
        corruption_markers = _canonical_clone(raw_payload["corruption_markers"])
    elif status == "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY":
        failure_type = raw_payload["failure_type"]
        if type(failure_type) is not str or _SAFE_TYPE_NAME_RE.fullmatch(failure_type) is None:
            raise CausalNativeTextEvidenceError("native visibility failure type drifted")
        if lines or words or quarantined:
            raise CausalNativeTextEvidenceError("unresolved visibility exposed page text")
    else:
        native_text_quality = raw_payload["native_text_quality"]
        if native_text_quality not in {"NO_TEXT_LAYER", "CORRUPT_TEXT_LAYER"}:
            raise CausalNativeTextEvidenceError("unresolved native quality drifted")
        corruption_markers = _canonical_clone(raw_payload["corruption_markers"])
        if lines or words:
            raise CausalNativeTextEvidenceError("unresolved native quality exposed accepted text")
    if type(corruption_markers) is not list or any(
        type(marker) is not str or not marker for marker in corruption_markers
    ):
        raise CausalNativeTextEvidenceError("native corruption markers drifted")
    if corruption_markers != sorted(set(corruption_markers)):
        raise CausalNativeTextEvidenceError("native corruption marker ordering drifted")

    normalized = {
        "status": status,
        "failure_type": failure_type,
        "native_text_quality": native_text_quality,
        "corruption_markers": corruption_markers,
        "lines": lines,
        "words": words,
        "quarantined_spans": quarantined,
        "ocr_fallback_used": False,
        "source_blank_claimed": False,
    }
    if set(normalized) != _NORMALIZED_PAYLOAD_FIELDS:
        raise AssertionError("normalized causal payload fields are not closed")
    return _validate_normalized_native_payload(normalized, physical_page=physical_page)


def _validate_normalized_native_payload(
    payload: Any,
    *,
    physical_page: int,
) -> dict[str, Any]:
    if type(payload) is not dict or set(payload) != _NORMALIZED_PAYLOAD_FIELDS:
        raise CausalNativeTextEvidenceError("normalized causal payload fields drifted")
    normalized = _canonical_clone(payload)
    status = normalized["status"]
    if status not in TERMINAL_STATUSES:
        raise CausalNativeTextEvidenceError("normalized causal payload status drifted")
    if (
        normalized["ocr_fallback_used"] is not False
        or normalized["source_blank_claimed"] is not False
    ):
        raise CausalNativeTextEvidenceError("normalized causal payload safety drifted")
    _validate_lines_and_words(normalized["lines"], normalized["words"])
    _validate_quarantined_spans(normalized["quarantined_spans"], physical_page=physical_page)
    markers = normalized["corruption_markers"]
    if type(markers) is not list or any(
        type(marker) is not str or not marker for marker in markers
    ):
        raise CausalNativeTextEvidenceError("native corruption markers drifted")
    if markers != sorted(set(markers)):
        raise CausalNativeTextEvidenceError("native corruption marker ordering drifted")
    if status == "CAUSAL_NATIVE_TEXT_READ_COMPLETE":
        if (
            normalized["failure_type"] is not None
            or normalized["native_text_quality"] != "USABLE_TEXT_LAYER"
            or not normalized["words"]
        ):
            raise CausalNativeTextEvidenceError("complete native result quality drifted")
    elif status == "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY":
        failure_type = normalized["failure_type"]
        if type(failure_type) is not str or _SAFE_TYPE_NAME_RE.fullmatch(failure_type) is None:
            raise CausalNativeTextEvidenceError("native visibility failure type drifted")
        if (
            normalized["native_text_quality"] is not None
            or markers
            or normalized["lines"]
            or normalized["words"]
            or normalized["quarantined_spans"]
        ):
            raise CausalNativeTextEvidenceError("unresolved visibility exposed page text")
    elif (
        normalized["failure_type"] is not None
        or normalized["native_text_quality"] not in {"NO_TEXT_LAYER", "CORRUPT_TEXT_LAYER"}
        or normalized["lines"]
        or normalized["words"]
    ):
        raise CausalNativeTextEvidenceError("unresolved native quality drifted")
    return normalized


def _build_envelopes(
    *,
    request: Mapping[str, Any],
    request_sha256: str,
    source_bytes: bytes,
    document_id: str,
    physical_page: int,
    provider_runtime_ledger: Mapping[str, Any],
    causal_policy_path: Path,
    quality_policy_path: Path,
    full_control_identity_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if type(source_bytes) is not bytes:
        raise CausalNativeTextEvidenceError("authenticated source must be immutable bytes")
    _require_sha256(full_control_identity_sha256, "full execution control identity")
    (
        provider_ledger,
        causal_policy_bytes,
        quality_policy_bytes,
        causal_policy_identity,
        quality_policy_identity,
    ) = _validate_provider_runtime_ledger(
        provider_runtime_ledger,
        causal_policy_path=causal_policy_path,
        quality_policy_path=quality_policy_path,
    )
    provider_identity = provider_ledger["sha256"]
    request_copy = _validate_request(
        request,
        request_sha256=request_sha256,
        source_bytes=source_bytes,
        document_id=document_id,
        physical_page=physical_page,
        provider_identity_sha256=provider_identity,
    )

    with _authenticated_policy_copies(
        causal_policy_bytes,
        quality_policy_bytes,
    ) as (authenticated_causal_path, authenticated_quality_path):
        try:
            policy = load_causal_native_text_policy(authenticated_causal_path)
        except Exception:
            raise CausalNativeTextEvidenceError(
                "authenticated causal-native policy cannot be loaded"
            ) from None
        try:
            document = fitz.open(stream=source_bytes, filetype="pdf")
        except Exception:
            raise CausalNativeTextEvidenceError("authenticated PDF cannot be opened") from None
        try:
            try:
                if document.page_count < physical_page:
                    raise CausalNativeTextEvidenceError(
                        "authenticated PDF does not contain the requested page"
                    )
                page = document.load_page(physical_page - 1)
                raw_payload = read_causal_native_text_page(
                    page,
                    policy=policy,
                    quality_policy_path=authenticated_quality_path,
                )
            except CausalNativeTextEvidenceError:
                raise
            except Exception:
                raise CausalNativeTextEvidenceError(
                    "sealed causal-native wrapper failed operationally"
                ) from None
        finally:
            document.close()
    normalized_payload = _normalize_native_payload(
        raw_payload,
        physical_page=physical_page,
    )

    source_sha256 = request_copy["source_sha256"]
    source_size_bytes = request_copy["source_size_bytes"]
    coordinate_authority = _coordinate_authority()
    safety = _safety_boundary()
    backend = {
        "format_version": BACKEND_FORMAT_VERSION,
        "status": normalized_payload["status"],
        "claim_boundary": _BACKEND_CLAIM_BOUNDARY,
        "document_id": document_id,
        "source_sha256": source_sha256,
        "source_size_bytes": source_size_bytes,
        "physical_page": physical_page,
        "route": _ROUTE,
        "request_sha256": request_sha256,
        "request": _canonical_clone(request_copy),
        "full_control_identity_sha256": full_control_identity_sha256,
        "provider_identity_sha256": provider_identity,
        "provider_runtime_ledger": _canonical_clone(provider_ledger),
        "causal_native_policy_identity": causal_policy_identity,
        "native_text_quality_policy_identity": quality_policy_identity,
        "coordinate_authority": _canonical_clone(coordinate_authority),
        "causal_native_payload": _canonical_clone(normalized_payload),
        "ocr_fallback_used": False,
        "source_blank_claimed": False,
        "safety": _canonical_clone(safety),
    }
    if set(backend) != _BACKEND_FIELDS:
        raise AssertionError("causal native backend fields are not closed")
    backend_sha256 = _canonical_json_sha256(backend)
    result = {
        "format_version": RESULT_FORMAT_VERSION,
        "status": normalized_payload["status"],
        "claim_boundary": _RESULT_CLAIM_BOUNDARY,
        "document_id": document_id,
        "source_sha256": source_sha256,
        "source_size_bytes": source_size_bytes,
        "physical_page": physical_page,
        "route": _ROUTE,
        "request_sha256": request_sha256,
        "request": _canonical_clone(request_copy),
        "full_control_identity_sha256": full_control_identity_sha256,
        "provider_identity_sha256": provider_identity,
        "backend_payload_sha256": backend_sha256,
        "coordinate_authority": _canonical_clone(coordinate_authority),
        "failure_type": normalized_payload["failure_type"],
        "native_text_quality": normalized_payload["native_text_quality"],
        "corruption_markers": _canonical_clone(normalized_payload["corruption_markers"]),
        "lines": _canonical_clone(normalized_payload["lines"]),
        "words": _canonical_clone(normalized_payload["words"]),
        "quarantined_spans": _canonical_clone(normalized_payload["quarantined_spans"]),
        "metrics": {
            "line_count": len(normalized_payload["lines"]),
            "word_token_count": len(normalized_payload["words"]),
            "quarantined_span_count": len(normalized_payload["quarantined_spans"]),
        },
        "ocr_fallback_used": False,
        "source_blank_claimed": False,
        "safety": _canonical_clone(safety),
    }
    if set(result) != _RESULT_FIELDS:
        raise AssertionError("causal native result fields are not closed")
    _canonical_json_bytes(backend)
    _canonical_json_bytes(result)
    return backend, result


def build_causal_native_text_evidence(
    *,
    request: Mapping[str, Any],
    request_sha256: str,
    source_bytes: bytes,
    document_id: str,
    physical_page: int,
    provider_runtime_ledger: Mapping[str, Any],
    causal_policy_path: Path,
    quality_policy_path: Path,
    full_control_identity_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build deterministic backend/result envelopes for one sealed native page.

    The caller authenticates which sealed request is in scope; this adapter then
    independently verifies its canonical hash, source bytes, provider ledger,
    live PyMuPDF runtime, and configuration bytes before invoking the frozen
    causal-native wrapper.
    """

    return _build_envelopes(
        request=request,
        request_sha256=request_sha256,
        source_bytes=source_bytes,
        document_id=document_id,
        physical_page=physical_page,
        provider_runtime_ledger=provider_runtime_ledger,
        causal_policy_path=causal_policy_path,
        quality_policy_path=quality_policy_path,
        full_control_identity_sha256=full_control_identity_sha256,
    )


def _validate_observed_envelopes(
    backend: Any,
    result: Any,
    *,
    physical_page: int,
) -> None:
    _validate_json_tree(backend)
    _validate_json_tree(result)
    if type(backend) is not dict or set(backend) != _BACKEND_FIELDS:
        raise CausalNativeTextEvidenceError("causal native backend fields drifted")
    if type(result) is not dict or set(result) != _RESULT_FIELDS:
        raise CausalNativeTextEvidenceError("causal native result fields drifted")
    if backend["format_version"] != BACKEND_FORMAT_VERSION:
        raise CausalNativeTextEvidenceError("causal native backend format drifted")
    if result["format_version"] != RESULT_FORMAT_VERSION:
        raise CausalNativeTextEvidenceError("causal native result format drifted")
    if backend["status"] not in TERMINAL_STATUSES or result["status"] != backend["status"]:
        raise CausalNativeTextEvidenceError("causal native envelope status drifted")
    if (
        backend["ocr_fallback_used"] is not False
        or result["ocr_fallback_used"] is not False
        or backend["source_blank_claimed"] is not False
        or result["source_blank_claimed"] is not False
    ):
        raise CausalNativeTextEvidenceError("causal native safety claims drifted")
    if not _same_typed_json(backend["safety"], _safety_boundary()) or not _same_typed_json(
        result["safety"], _safety_boundary()
    ):
        raise CausalNativeTextEvidenceError("causal native semantic boundary drifted")
    if not _same_typed_json(
        backend["coordinate_authority"], _coordinate_authority()
    ) or not _same_typed_json(result["coordinate_authority"], _coordinate_authority()):
        raise CausalNativeTextEvidenceError("causal native coordinate authority drifted")
    payload = backend["causal_native_payload"]
    normalized = _validate_normalized_native_payload(payload, physical_page=physical_page)
    if not _same_typed_json(payload, normalized):
        raise CausalNativeTextEvidenceError("causal native backend payload is not canonical")
    projection = {
        "status": normalized["status"],
        "failure_type": normalized["failure_type"],
        "native_text_quality": normalized["native_text_quality"],
        "corruption_markers": normalized["corruption_markers"],
        "lines": normalized["lines"],
        "words": normalized["words"],
        "quarantined_spans": normalized["quarantined_spans"],
        "ocr_fallback_used": False,
        "source_blank_claimed": False,
    }
    observed_projection = {key: result[key] for key in projection}
    if not _same_typed_json(observed_projection, projection):
        raise CausalNativeTextEvidenceError("causal native result projection drifted")
    expected_metrics = {
        "line_count": len(normalized["lines"]),
        "word_token_count": len(normalized["words"]),
        "quarantined_span_count": len(normalized["quarantined_spans"]),
    }
    if not _same_typed_json(result["metrics"], expected_metrics):
        raise CausalNativeTextEvidenceError("causal native result metrics drifted")
    backend_sha256 = _canonical_json_sha256(backend)
    if result["backend_payload_sha256"] != backend_sha256:
        raise CausalNativeTextEvidenceError("causal native backend hash binding drifted")


def validate_causal_native_text_evidence_replay(
    *,
    request: Mapping[str, Any],
    request_sha256: str,
    source_bytes: bytes,
    document_id: str,
    physical_page: int,
    provider_runtime_ledger: Mapping[str, Any],
    causal_policy_path: Path,
    quality_policy_path: Path,
    full_control_identity_sha256: str,
    backend: Mapping[str, Any],
    result: Mapping[str, Any],
) -> None:
    """Strictly replay and compare a causal-native evidence pair.

    Validation first checks closed schemas, types, semantic safety and the
    result-to-backend hash binding.  It then rebuilds from authenticated PDF and
    configuration bytes and requires both typed-tree and canonical-byte equality.
    """

    _validate_observed_envelopes(backend, result, physical_page=physical_page)
    expected_backend, expected_result = _build_envelopes(
        request=request,
        request_sha256=request_sha256,
        source_bytes=source_bytes,
        document_id=document_id,
        physical_page=physical_page,
        provider_runtime_ledger=provider_runtime_ledger,
        causal_policy_path=causal_policy_path,
        quality_policy_path=quality_policy_path,
        full_control_identity_sha256=full_control_identity_sha256,
    )
    if (
        not _same_typed_json(backend, expected_backend)
        or not _same_typed_json(result, expected_result)
        or _canonical_json_bytes(backend) != _canonical_json_bytes(expected_backend)
        or _canonical_json_bytes(result) != _canonical_json_bytes(expected_result)
    ):
        raise CausalNativeTextEvidenceError("causal native evidence replay drifted")
