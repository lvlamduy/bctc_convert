from __future__ import annotations

import fcntl
import json
import os
import re
import secrets
import socket
import stat
import subprocess
from collections import Counter, defaultdict
from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from copy import deepcopy
from math import isfinite
from pathlib import Path
from threading import RLock
from typing import Any

import fitz
import yaml

from bctc_ai.core.hashing import sha256_bytes
from bctc_ai.corpus import wave1_role_b_sentinel as sentinel
from bctc_ai.corpus.wave1_role_b_word_box_normalization import (
    WORD_BOX_NORMALIZATION_POLICY,
    WaveOneRoleBWordBoxNormalizationError,
    model_neutral_result_from_normalized_payload,
    normalize_ppocrv6_word_boxes,
    validate_normalization_authority,
)
from bctc_ai.ocr.causal_native_text_evidence_v2 import (
    CausalNativeTextEvidenceError,
    build_causal_native_text_evidence_v2,
    validate_causal_native_text_evidence_v2_envelopes,
    validate_causal_native_text_evidence_v2_replay,
)
from bctc_ai.ocr.ppocrv6_page_session import validate_ppocrv6_payload
from bctc_ai.rendering.page_reader import (
    public_coordinate_authority,
    render_composited_displayed_page,
)


class WaveOneRoleBFullReaderError(RuntimeError):
    """The authenticated Wave-1 full reader cannot proceed fail-closed."""


POLICY_RELATIVE_PATH = Path("config/corpus/bank-corpus-wave-1-role-b-full-reader-v3.yaml")
POLICY_SHA256 = "cfc41174c60bca03139a3ecf11e009c4e4d322364f3583ce2da8f492627ce941"
POLICY_SIZE_BYTES = 7_623
SEALED_PLAN_RELATIVE_PATH = sentinel.SEALED_PLAN_RELATIVE_PATH
SEALED_PLAN_SHA256 = sentinel.SEALED_PLAN_SHA256
SEALED_PLAN_SIZE_BYTES = sentinel.SEALED_PLAN_SIZE_BYTES
PRODUCER_GIT_COMMIT = sentinel.PRODUCER_GIT_COMMIT
EXECUTION_PLAN_SHA256 = sentinel.EXECUTION_PLAN_SHA256
SENTINEL_SHA256 = sentinel.SENTINEL_SHA256
SELECTION_RECEIPT_SHA256 = sentinel.SELECTION_RECEIPT_SHA256
OUTPUT_RELATIVE_ROOT = Path("output/development/bank-corpus-wave-1-role-b-page-reader-v1/full-v3")

FAILED_V2_ARCHIVE_RELATIVE_ROOT = Path(
    "output/development/bank-corpus-wave-1-role-b-page-reader-v1/"
    "full-v2-failed-after-1359-checkpoints-c0b126f-9e55fa6d"
)
FAILED_V2_RECEIPT_RELATIVE_PATH = Path(
    "output/development/bank-corpus-wave-1-role-b-page-reader-v1/"
    "full-v2-failed-after-1359-checkpoints-c0b126f-9e55fa6d-incident.json"
)
FAILED_V2_RECEIPT_SHA256 = "c55b9c443584cc603000f05b1a98c7abc6c45828a914a694f6db8395eb336748"
FAILED_V2_RECEIPT_SIZE_BYTES = 3_859_012
FAILED_V2_INCIDENT_IDENTITY_SHA256 = (
    "ab14bf5c7df9a0a416944bc7853465c88a65255354f0c3841e9fa3b5bf2368fb"
)
FAILED_V2_PORTABLE_MANIFEST_SHA256 = (
    "9e55fa6d22fab24f14dc51ba0f54f143519fc4be32ecb64f46cdf1e413b6f2b8"
)
FAILED_V2_LIVE_MANIFEST_SHA256 = "7867c60d4971806cbd29d493cca7b53ad26d1243be2a90c406c6e6fa143fa6bb"
FAILED_V2_CONTROL_SHA256 = "198bc717b4cffda605bf598b83cd1c7ca391f4969e5d5ae26a0e8687cd07d440"
FAILED_V2_CONTROL_SIZE_BYTES = 4_608_592
FAILED_V2_CONTROL_IDENTITY_SHA256 = (
    "5f4f00d40900be2765b6f873b268cd09c28026245157d2bdb0b293eb24a64be1"
)
FAILED_V2_PRODUCER_COMMIT = "c0b126fbc7bb312683dc0caaae79e42bc3378a22"
FAILED_V2_IMPLEMENTATION_LEDGER_SHA256 = (
    "f240b430c34ec878a5d0ab3333d2af7f4b607316332a002a898f07978b409778"
)
FAILED_V2_CHECKPOINT_SET_SHA256 = "61bdd2e42d8d3453a1ef959ec29cfbc4fee266943fc4cc5de74526db5b61f3fe"
FAILED_V2_MISSING_REQUEST_SET_SHA256 = (
    "4fb91da5d72b3963d4eee70a36c6cc786a332dc406db9a929bd34334f79cda92"
)

V3_IMPLEMENTATION_RELATIVE_PATHS = (
    POLICY_RELATIVE_PATH,
    Path("config/corpus/bank-corpus-wave-1-role-b-page-reader-v1.yaml"),
    Path("config/corpus/bank-corpus-wave-1-role-b-sentinel-v1.yaml"),
    Path("config/ocr/causal-native-text-v1.yaml"),
    Path("config/ocr/native-text-quality-v2.yaml"),
    Path("config/ocr/causal-native-text-evidence-v2.yaml"),
    Path("src/bctc_ai/__init__.py"),
    Path("src/bctc_ai/core/__init__.py"),
    Path("src/bctc_ai/core/coordinates.py"),
    Path("src/bctc_ai/core/contracts.py"),
    Path("src/bctc_ai/core/hashing.py"),
    Path("src/bctc_ai/core/text.py"),
    Path("src/bctc_ai/corpus/__init__.py"),
    Path("src/bctc_ai/corpus/wave1_pre_ocr_structure.py"),
    Path("src/bctc_ai/corpus/wave1_role_b_page_reader.py"),
    Path("src/bctc_ai/corpus/wave1_role_b_sentinel.py"),
    Path("src/bctc_ai/corpus/wave1_role_b_word_box_normalization.py"),
    Path("src/bctc_ai/corpus/wave1_role_b_full_reader_v3.py"),
    Path("src/bctc_ai/ocr/__init__.py"),
    Path("src/bctc_ai/ocr/_causal_visibility_core.py"),
    Path("src/bctc_ai/ocr/causal_native_text.py"),
    Path("src/bctc_ai/ocr/causal_native_text_evidence_v1.py"),
    Path("src/bctc_ai/ocr/causal_native_text_evidence_v2.py"),
    Path("src/bctc_ai/ocr/native_text_quality_v2.py"),
    Path("src/bctc_ai/ocr/pdf_text.py"),
    Path("src/bctc_ai/ocr/ppocrv6_page_session.py"),
    Path("src/bctc_ai/rendering/__init__.py"),
    Path("src/bctc_ai/rendering/page_reader.py"),
    Path("src/bctc_ai/storage/__init__.py"),
    Path("src/bctc_ai/storage/content_store.py"),
    Path("scripts/corpus/run_wave1_role_b_page_reader.py"),
    Path("scripts/corpus/run_wave1_role_b_full_reader_v3.py"),
)

_SHA256 = frozenset("0123456789abcdef")
_OCR_ROUTE = "DOMINANT_RASTER_OCR"
_NATIVE_ROUTE = "CAUSAL_NATIVE_TEXT"
_NATIVE_TERMINAL = frozenset(
    {
        "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
        "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY",
        "UNRESOLVED_NATIVE_TEXT_QUALITY",
        "UNRESOLVED_CAUSAL_NATIVE_LINE_CONTIGUITY",
    }
)
_COMPLETE_STATUS = "COMPLETE_AUTHENTICATED_WAVE_1_PAGE_READS"
_V3_OUTPUT_READ_BINDING: ContextVar[
    tuple[
        Path,
        dict[str, list[Any]],
        dict[str, list[Any]],
        dict[str, int],
    ]
    | None
] = ContextVar("wave1_role_b_full_reader_v3_output_read_binding", default=None)
_V3_ARCHIVE_READ_BINDING: ContextVar[
    tuple[
        Path,
        dict[str, list[Any]],
        dict[str, list[Any]],
        dict[str, int],
    ]
    | None
] = ContextVar("wave1_role_b_full_reader_v3_archive_read_binding", default=None)
_V3_ARCHIVE_RECEIPT_READ_BINDING: ContextVar[tuple[Path, int, list[Any]] | None] = ContextVar(
    "wave1_role_b_full_reader_v3_archive_receipt_read_binding", default=None
)
_V3_SHARED_OUTPUT_PARENT_BINDING: ContextVar[tuple[Path, int, tuple[int, int, int]] | None] = (
    ContextVar("wave1_role_b_full_reader_v3_shared_output_parent", default=None)
)
_V3_OUTPUT_MUTATION_BINDING: ContextVar[
    tuple[Path, int, int, int, tuple[int, ...], tuple[int, ...]] | None
] = ContextVar("wave1_role_b_full_reader_v3_output_mutation_binding", default=None)
_V3_OUTPUT_SNAPSHOT_BINDING: ContextVar[tuple[Path, int] | None] = ContextVar(
    "wave1_role_b_full_reader_v3_output_snapshot_binding", default=None
)
_V3_CONTROL_COMMIT_MARKER: ContextVar[bool] = ContextVar(
    "wave1_role_b_full_reader_v3_control_commit_marker", default=False
)
_V3_MUTATION_LOCK = RLock()
_ZERO_INTERPRETATION = {
    "statement_classification_count": 0,
    "table_classification_count": 0,
    "row_reconstruction_count": 0,
    "cell_interpretation_count": 0,
    "absence_declaration_count": 0,
}


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


def _same_typed_json(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(
            _same_typed_json(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _same_typed_json(a, b) for a, b in zip(left, right, strict=True)
        )
    try:
        return left == right and _canonical_bytes(left) == _canonical_bytes(right)
    except (TypeError, ValueError):
        return False


def _v3_cleanup_attempt(errors: list[BaseException], action: Callable[[], Any]) -> None:
    """Attempt one cleanup action without suppressing later cleanup actions."""

    try:
        action()
    except BaseException as error:
        errors.append(error)


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _SHA256


def _json_object(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as error:
        raise WaveOneRoleBFullReaderError(f"{label} is invalid JSON") from error
    if not isinstance(value, dict) or _canonical_bytes(value) != payload:
        raise WaveOneRoleBFullReaderError(f"{label} is not a canonical JSON object")
    return value


def _stable_bytes(path: Path, label: str) -> bytes:
    try:
        return sentinel._stable_bytes(path, label)  # noqa: SLF001 - authenticated substrate
    except sentinel.WaveOneRoleBSentinelError as error:
        raise WaveOneRoleBFullReaderError(str(error)) from error


def _project_path(project_root: Path, relative: str | Path, label: str) -> Path:
    try:
        return sentinel._project_path(  # noqa: SLF001 - authenticated substrate
            project_root, relative, label
        )
    except sentinel.WaveOneRoleBSentinelError as error:
        raise WaveOneRoleBFullReaderError(str(error)) from error


# V3 is an independent authority chain.  It imports no V1/V2 full-reader
# executor and has no OCR-worker or inference surface.


def _git_blob(project_root: Path, commit: str, relative: str) -> bytes:
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise WaveOneRoleBFullReaderError("historical Git commit is malformed")
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != relative:
        raise WaveOneRoleBFullReaderError("historical Git path is unsafe")
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative}", "--"],
        cwd=project_root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise WaveOneRoleBFullReaderError("historical Git blob is unavailable")
    return result.stdout


def _validate_nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise WaveOneRoleBFullReaderError(f"{label} is not a nonnegative integer")
    return value


def _v2_result_safety() -> dict[str, bool]:
    return {
        "bank_registry_metadata_used": False,
        "filename_metadata_used": False,
        "role_a_used": False,
        "schema_used": False,
        "mapping_used": False,
        "historical_values_used": False,
        "statement_classified": False,
        "table_classified": False,
        "rows_reconstructed": False,
        "cells_interpreted": False,
        "absence_claimed": False,
    }


@contextmanager
def _v3_network_denied() -> Iterator[None]:
    originals = {
        "create_connection": socket.create_connection,
        "getaddrinfo": socket.getaddrinfo,
        "connect": socket.socket.connect,
        "connect_ex": socket.socket.connect_ex,
    }

    def denied(*_args: Any, **_kwargs: Any) -> Any:
        raise WaveOneRoleBFullReaderError("network access is denied for V3 native evidence")

    socket.create_connection = denied
    socket.getaddrinfo = denied
    socket.socket.connect = denied
    socket.socket.connect_ex = denied
    try:
        yield
    finally:
        replaced = (
            socket.create_connection is not denied
            or socket.getaddrinfo is not denied
            or socket.socket.connect is not denied
            or socket.socket.connect_ex is not denied
        )
        socket.create_connection = originals["create_connection"]
        socket.getaddrinfo = originals["getaddrinfo"]
        socket.socket.connect = originals["connect"]
        socket.socket.connect_ex = originals["connect_ex"]
        if replaced:
            raise WaveOneRoleBFullReaderError("V3 network denial guard was replaced")


def _restore_in_memory_coordinate_authority(public: Any) -> dict[str, Any]:
    if not isinstance(public, dict):
        raise WaveOneRoleBFullReaderError("public coordinate authority is malformed")
    authority = deepcopy(public)
    for public_key, private_key in (
        ("pixel_to_unrotated_mpt", "_pixel_to_unrotated_matrix"),
        ("unrotated_mpt_to_pixel", "_unrotated_to_pixel_matrix"),
    ):
        matrix = public.get(public_key)
        if (
            not isinstance(matrix, list)
            or len(matrix) != 3
            or any(not isinstance(row, list) or len(row) != 3 for row in matrix)
        ):
            raise WaveOneRoleBFullReaderError("coordinate matrix shape drifted")
        restored = []
        for row in matrix:
            restored_row = []
            for coefficient in row:
                if (
                    not isinstance(coefficient, dict)
                    or set(coefficient) != {"numerator", "denominator"}
                    or type(coefficient["numerator"]) is not int
                    or type(coefficient["denominator"]) is not int
                    or coefficient["denominator"] <= 0
                ):
                    raise WaveOneRoleBFullReaderError("coordinate rational coefficient drifted")
                restored_row.append((coefficient["numerator"], coefficient["denominator"]))
            restored.append(tuple(restored_row))
        authority[private_key] = tuple(restored)
    return authority


def _normalization_authority(control: dict[str, Any]) -> dict[str, Any]:
    contract = control.get("word_box_normalization")
    implementation = control.get("executor_implementation_ledger")
    if (
        not isinstance(contract, dict)
        or set(contract)
        != {
            "policy",
            "policy_sha256",
            "normalization_producer_implementation_ledger_sha256",
        }
        or not isinstance(implementation, dict)
        or contract["normalization_producer_implementation_ledger_sha256"]
        != implementation.get("sha256")
    ):
        raise WaveOneRoleBFullReaderError("historical normalization authority drifted")
    try:
        return validate_normalization_authority(
            {**contract, "control_identity_sha256": control.get("control_identity_sha256")}
        )
    except RuntimeError as error:
        raise WaveOneRoleBFullReaderError("historical normalization authority drifted") from error


def _validate_ppocrv6_schema_except_word_geometry(
    payload: dict[str, Any], *, pixel_width: int, pixel_height: int
) -> dict[str, int]:
    """Validate the full PP payload while substituting only word-box geometry."""

    if not isinstance(payload, dict):
        raise WaveOneRoleBFullReaderError("raw PP-OCR payload is not an object")
    exact_keys = {
        "dt_polys",
        "model_settings",
        "page_index",
        "rec_boxes",
        "rec_polys",
        "rec_scores",
        "rec_texts",
        "return_word_box",
        "text_det_params",
        "text_rec_score_thresh",
        "text_type",
        "text_word",
        "text_word_boxes",
        "textline_orientation_angles",
    }
    if set(payload) != exact_keys:
        raise WaveOneRoleBFullReaderError("raw PP-OCR archived provider field set drifted")
    required_axes = (
        "rec_texts",
        "rec_scores",
        "rec_polys",
        "rec_boxes",
        "text_word_boxes",
        "text_word",
    )
    if payload.get("return_word_box") is not True or any(
        not isinstance(payload.get(key), list) for key in required_axes
    ):
        raise WaveOneRoleBFullReaderError(
            "raw PP-OCR payload is not schema-valid before geometry normalization"
        )
    counts = {key: len(payload[key]) for key in required_axes}
    if len(set(counts.values())) != 1:
        raise WaveOneRoleBFullReaderError("raw PP-OCR line axes are inconsistent")
    sanitized = deepcopy(payload)
    for line_index in range(counts["rec_texts"]):
        boxes = payload["text_word_boxes"][line_index]
        words = payload["text_word"][line_index]
        line_box = payload["rec_boxes"][line_index]
        if (
            not isinstance(boxes, list)
            or not isinstance(words, list)
            or len(boxes) != len(words)
            or not isinstance(line_box, list)
            or len(line_box) != 4
        ):
            raise WaveOneRoleBFullReaderError("raw PP-OCR word axes are malformed")
        replacement = []
        for box, word in zip(boxes, words, strict=True):
            if (
                not isinstance(word, str)
                or not isinstance(box, list)
                or len(box) != 4
                or any(
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not isfinite(value)
                    for value in box
                )
                or not box[0] < box[2]
                or not box[1] < box[3]
            ):
                raise WaveOneRoleBFullReaderError("raw PP-OCR word-box schema drifted")
            replacement.append(deepcopy(line_box))
        sanitized["text_word_boxes"][line_index] = replacement
    try:
        return validate_ppocrv6_payload(
            sanitized, pixel_width=pixel_width, pixel_height=pixel_height
        )
    except RuntimeError as error:
        raise WaveOneRoleBFullReaderError(
            "raw PP-OCR payload has a non-word-geometry structural failure"
        ) from error


def _full_request_records(sealed: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    ordinal = 0
    for document in sorted(sealed.get("documents", []), key=lambda item: item["document_id"]):
        document_id = document.get("document_id")
        pages = document.get("pages")
        if (
            document_id != f"sha256:{document.get('sha256')}"
            or not isinstance(pages, list)
            or len(pages) != document.get("page_count")
        ):
            raise WaveOneRoleBFullReaderError("sealed document identity drifted")
        request_hashes = []
        for page in sorted(pages, key=lambda item: item["page"]):
            ordinal += 1
            request = page.get("request")
            request_sha = page.get("request_sha256")
            route = page.get("route")
            if (
                route not in {_OCR_ROUTE, _NATIVE_ROUTE}
                or not isinstance(request, dict)
                or _canonical_sha256(request) != request_sha
                or request_sha in seen
                or request.get("route") != route
                or request.get("source_sha256") != document["sha256"]
                or request.get("source_size_bytes") != document["size_bytes"]
                or request.get("physical_page") != page.get("page")
                or any(
                    request.get(key) is not False
                    for key in (
                        "bank_identity_used",
                        "filename_used",
                        "role_a_used",
                        "schema_used",
                        "historical_values_used",
                    )
                )
            ):
                raise WaveOneRoleBFullReaderError("sealed page request identity drifted")
            seen.add(request_sha)
            request_hashes.append(request_sha)
            records.append(
                {
                    "request_ordinal": ordinal,
                    "document_id": document_id,
                    "source_sha256": document["sha256"],
                    "source_size_bytes": document["size_bytes"],
                    "physical_page": page["page"],
                    "route": route,
                    "request_sha256": request_sha,
                    "request": request,
                }
            )
        if _canonical_sha256(request_hashes) != document.get("request_set_sha256"):
            raise WaveOneRoleBFullReaderError("sealed document request set drifted")
    if len(records) != 1_449 or Counter(item["route"] for item in records) != {
        _OCR_ROUTE: 1_356,
        _NATIVE_ROUTE: 93,
    }:
        raise WaveOneRoleBFullReaderError("sealed full request accounting drifted")
    return records


def _v2_checkpoint_payload(
    control: dict[str, Any],
    document_id: str,
    record: dict[str, Any],
    generation: int,
    previous_sha256: str | None,
) -> dict[str, Any]:
    return {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_FULL_PAGE_DELTA_CHECKPOINT_V1",
        "status": "COMPLETE_ONE_AUTHENTICATED_PAGE_REQUEST",
        "claim_boundary": "ONE_EXACT_SEALED_PAGE_REQUEST_ACCOUNTING_ONLY",
        "sealed_plan_sha256": SEALED_PLAN_SHA256,
        "control_identity_sha256": control["control_identity_sha256"],
        "document_id": document_id,
        "source_sha256": document_id.removeprefix("sha256:"),
        "generation": generation,
        "previous_checkpoint_sha256": previous_sha256,
        "page_record": record,
    }


def _v2_document_completion_order(control: dict[str, Any], document_id: str) -> list[str]:
    sentinel_hashes = set(control["sentinel_request_sha256s"])
    matches = [
        document for document in control["documents"] if document["document_id"] == document_id
    ]
    if len(matches) != 1:
        raise WaveOneRoleBFullReaderError("historical completion-order document drifted")
    pages = matches[0]["pages"]
    stages = (
        [page for page in pages if page["request_sha256"] in sentinel_hashes],
        [
            page
            for page in pages
            if page["route"] == _OCR_ROUTE and page["request_sha256"] not in sentinel_hashes
        ],
        [page for page in pages if page["route"] == _NATIVE_ROUTE],
    )
    ordered = [
        page["request_sha256"]
        for stage in stages
        for page in sorted(stage, key=lambda item: item["request_ordinal"])
    ]
    if len(ordered) != len(pages) or len(set(ordered)) != len(pages):
        raise WaveOneRoleBFullReaderError("historical completion order drifted")
    return ordered


def _v3_retained_output_root_fd(project_root: Path) -> int | None:
    mutation = _V3_OUTPUT_MUTATION_BINDING.get()
    if mutation is not None:
        bound_root, _parent_fd, root_fd, _locks_fd, _root_token, _locks_token = mutation
        if bound_root != project_root:
            raise WaveOneRoleBFullReaderError("V3 retained output root project binding drifted")
        return root_fd
    snapshot = _V3_OUTPUT_SNAPSHOT_BINDING.get()
    if snapshot is not None:
        bound_root, root_fd = snapshot
        if bound_root != project_root:
            raise WaveOneRoleBFullReaderError(
                "V3 retained read-only output root project binding drifted"
            )
        return root_fd
    return None


@contextmanager
def _v3_held_output_directory(
    project_root: Path, relative: Path, *, create: bool
) -> Iterator[tuple[Path, int]]:
    """Open one output directory from the retained output-root generation."""

    try:
        below_root = relative.relative_to(OUTPUT_RELATIVE_ROOT)
    except ValueError as error:
        raise WaveOneRoleBFullReaderError(
            "V3 output directory is outside the full-v3 root"
        ) from error
    if any(part in {"", ".", ".."} for part in below_root.parts):
        raise WaveOneRoleBFullReaderError("V3 output directory path is invalid")
    retained_root_fd = _v3_retained_output_root_fd(project_root)
    if retained_root_fd is None:
        try:
            with sentinel._held_directory(  # noqa: SLF001 - no retained generation
                project_root, relative, create=create
            ) as value:
                yield value
            return
        except sentinel.WaveOneRoleBSentinelError as error:
            raise WaveOneRoleBFullReaderError(str(error)) from error

    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = os.dup(retained_root_fd)
    try:
        opened_root = os.fstat(descriptor)
        retained_identity = os.fstat(retained_root_fd)
        if not stat.S_ISDIR(opened_root.st_mode) or (
            opened_root.st_dev,
            opened_root.st_ino,
            opened_root.st_mode,
        ) != (
            retained_identity.st_dev,
            retained_identity.st_ino,
            retained_identity.st_mode,
        ):
            raise WaveOneRoleBFullReaderError("V3 retained output root descriptor drifted")
        for part in below_root.parts:
            child = -1
            try:
                child = os.open(part, flags, dir_fd=descriptor)
            except FileNotFoundError:
                if not create:
                    raise WaveOneRoleBFullReaderError("V3 output directory is absent") from None
                os.mkdir(part, 0o755, dir_fd=descriptor)
                os.fsync(descriptor)
                child = os.open(part, flags, dir_fd=descriptor)
            try:
                opened = os.fstat(child)
                named = os.stat(part, dir_fd=descriptor, follow_symlinks=False)
                if (
                    not stat.S_ISDIR(opened.st_mode)
                    or stat.S_IMODE(opened.st_mode) != 0o755
                    or (opened.st_dev, opened.st_ino, opened.st_mode)
                    != (named.st_dev, named.st_ino, named.st_mode)
                ):
                    raise WaveOneRoleBFullReaderError(
                        "V3 retained output directory topology drifted"
                    )
                os.close(descriptor)
                descriptor = child
                child = -1
            finally:
                if child >= 0:
                    os.close(child)
        yield project_root / relative, descriptor
    except OSError as error:
        raise WaveOneRoleBFullReaderError(
            "V3 retained output directory operation failed"
        ) from error
    finally:
        os.close(descriptor)


def _v3_publish_exclusive_at(directory_fd: int, filename: str, payload: bytes) -> None:
    if not filename or "/" in filename or "\\" in filename or filename in {".", ".."}:
        raise WaveOneRoleBFullReaderError("V3 immutable publication name is invalid")
    try:
        existing_payload, existing = sentinel._hash_open_at(  # noqa: SLF001
            directory_fd, filename
        )
    except FileNotFoundError:
        existing_payload = None
        existing = None
    if existing_payload is not None:
        if (
            existing_payload != payload
            or stat.S_IMODE(existing.st_mode) != 0o444
            or existing.st_nlink != 1
        ):
            raise WaveOneRoleBFullReaderError("existing immutable V3 publication conflicts")
        return
    temporary_name = f".{filename}.{secrets.token_hex(16)}.tmp"
    descriptor = -1
    owned_identity: tuple[int, int] | None = None
    try:
        descriptor = os.open(
            temporary_name,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=directory_fd,
        )
        owned = os.fstat(descriptor)
        owned_identity = owned.st_dev, owned.st_ino
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
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
                follow_symlinks=False,
            )
        except FileExistsError:
            pass
        published, published_identity = sentinel._hash_open_at(  # noqa: SLF001
            directory_fd, filename
        )
        if (
            published != payload
            or stat.S_IMODE(published_identity.st_mode) != 0o444
            or published_identity.st_nlink != 2
            or (
                published_identity.st_dev,
                published_identity.st_ino,
                published_identity.st_size,
            )
            != (exact.st_dev, exact.st_ino, len(payload))
        ):
            raise WaveOneRoleBFullReaderError("V3 immutable publication link conflicted")
        os.fsync(directory_fd)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if owned_identity is not None:
            try:
                observed = os.stat(temporary_name, dir_fd=directory_fd, follow_symlinks=False)
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
                os.unlink(temporary_name, dir_fd=directory_fd)
                os.fsync(directory_fd)
    final_payload, final_identity = sentinel._hash_open_at(  # noqa: SLF001
        directory_fd, filename
    )
    if (
        final_payload != payload
        or stat.S_IMODE(final_identity.st_mode) != 0o444
        or final_identity.st_nlink != 1
    ):
        raise WaveOneRoleBFullReaderError("V3 immutable publication final identity drifted")


def _publish_exclusive(project_root: Path, directory: Path, filename: str, payload: bytes) -> Path:
    _v3_assert_output_mutation_ancestry(project_root, "V3 immutable publication")
    try:
        with _v3_held_output_directory(project_root, directory, create=True) as (
            published_directory,
            directory_fd,
        ):
            _v3_publish_exclusive_at(directory_fd, filename, payload)
            published = published_directory / filename
    except sentinel.WaveOneRoleBSentinelError as error:
        raise WaveOneRoleBFullReaderError(str(error)) from error
    except OSError as error:
        raise WaveOneRoleBFullReaderError("V3 immutable publication failed") from error
    _v3_assert_output_mutation_ancestry(project_root, "V3 immutable publication completion")
    return published


def _v3_preflight_output_temporaries(
    project_root: Path,
    document_ids: list[str],
    *,
    stage: str = "run",
) -> tuple[str | None, list[list[Any]] | None]:
    """Classify one exact output snapshot and return that same authenticated view."""

    if stage not in {"control", "run", "finalize"}:
        raise WaveOneRoleBFullReaderError("V3 output preflight stage is invalid")
    _v3_assert_output_mutation_ancestry(project_root, "V3 output preflight")
    root = project_root / OUTPUT_RELATIVE_ROOT
    if _v3_retained_output_root_fd(project_root) is None:
        try:
            os.stat(root, follow_symlinks=False)
        except FileNotFoundError:
            return None, None
    manifest = _v3_output_live_manifest(project_root)
    directories = {item[1]: item for item in manifest if item[0] == "d"}
    files = {item[1]: item for item in manifest if item[0] == "f"}
    if len(directories) + len(files) != len(manifest) or "." not in directories:
        raise WaveOneRoleBFullReaderError("V3 output preflight manifest drifted")
    expected_documents = {item.removeprefix("sha256:") for item in document_ids}

    def parts(relative: str) -> tuple[str, ...]:
        return () if relative == "." else Path(relative).parts

    def directory_allowed(relative: str) -> bool:
        item = parts(relative)
        return (
            not item
            or item
            in {
                ("locks",),
                ("locks", "documents"),
                ("objects",),
                ("objects", "sha256"),
                ("checkpoints",),
                ("documents",),
            }
            or (
                len(item) == 3
                and item[:2] == ("objects", "sha256")
                and re.fullmatch(r"[0-9a-f]{2}", item[2]) is not None
            )
            or (len(item) == 2 and item[0] == "checkpoints" and item[1] in expected_documents)
        )

    for relative, record in directories.items():
        if not directory_allowed(relative) or record[2] != 0o755:
            raise WaveOneRoleBFullReaderError("V3 output hierarchy contains a foreign directory")
        parent_parts = parts(relative)
        child_directory_count = sum(
            len(parts(candidate)) == len(parent_parts) + 1
            and parts(candidate)[: len(parent_parts)] == parent_parts
            for candidate in directories
            if candidate != relative
        )
        if record[3] != 2 + child_directory_count:
            raise WaveOneRoleBFullReaderError("V3 output directory link topology drifted")

    temporary_records: list[tuple[str, list[Any], str]] = []
    ordinary_records: list[tuple[str, list[Any]]] = []
    lock_paths: set[str] = set()
    temporary_grammar = re.compile(r"\.(?P<final>[^/\\]+\.(?:json|png))\.[0-9a-f]{32}\.tmp")

    def final_location_allowed(relative: str) -> bool:
        item = parts(relative)
        return (
            (
                len(item) == 1
                and item[0]
                in {
                    "full-reader-execution-control.json",
                    "full-reader-aggregate.json",
                }
            )
            or (
                len(item) == 2
                and item[0] == "documents"
                and item[1].endswith(".json")
                and item[1].removesuffix(".json") in expected_documents
            )
            or (
                len(item) == 3
                and item[0] == "checkpoints"
                and item[1] in expected_documents
                and re.fullmatch(r"[0-9]{4}-[0-9a-f]{64}\.json", item[2]) is not None
            )
            or (
                len(item) == 4
                and item[:2] == ("objects", "sha256")
                and re.fullmatch(r"[0-9a-f]{2}", item[2]) is not None
                and re.fullmatch(rf"{item[2]}[0-9a-f]{{62}}\.(?:json|png)", item[3]) is not None
            )
        )

    for relative, record in files.items():
        item = parts(relative)
        if item == ("locks", "full-reader-execution.lease") or (
            len(item) == 3
            and item[:2] == ("locks", "documents")
            and item[2].endswith(".lock")
            and item[2].removesuffix(".lock") in expected_documents
        ):
            if record[2:5] != [0o600, 1, 0]:
                raise WaveOneRoleBFullReaderError("V3 output lock file drifted")
            lock_paths.add(relative)
            continue
        match = temporary_grammar.fullmatch(item[-1] if item else "")
        if match is not None:
            final_relative = (
                Path(*item[:-1]) / match.group("final") if item[:-1] else Path(match.group("final"))
            ).as_posix()
            if not final_location_allowed(final_relative):
                raise WaveOneRoleBFullReaderError(
                    "V3 output temporary target or location is foreign"
                )
            temporary_records.append((relative, record, final_relative))
            continue
        if not final_location_allowed(relative):
            raise WaveOneRoleBFullReaderError("V3 output hierarchy contains a foreign regular file")
        ordinary_records.append((relative, record))
    if len(temporary_records) > 1:
        raise WaveOneRoleBFullReaderError("V3 output contains multiple publication temporaries")
    temporary_relative = None
    final_relative = None
    paired_final = None
    if temporary_records:
        temporary_relative, temporary_record, final_relative = temporary_records[0]
        paired_final = files.get(final_relative)
        if paired_final is None:
            if temporary_record[2] not in {0o600, 0o444} or temporary_record[3] != 1:
                raise WaveOneRoleBFullReaderError("V3 standalone temporary topology drifted")
        elif (
            temporary_record[2] != 0o444
            or paired_final[2] != 0o444
            or temporary_record[3] != 2
            or paired_final[3] != 2
            or temporary_record[4:] != paired_final[4:]
        ):
            raise WaveOneRoleBFullReaderError("V3 linked temporary topology drifted")
    for relative, record in ordinary_records:
        if record[2] != 0o444 or record[3] != (2 if relative == final_relative else 1):
            raise WaveOneRoleBFullReaderError("V3 published output file topology drifted")

    checkpoint_final_count = sum(
        len(parts(relative)) == 3 and parts(relative)[0] == "checkpoints"
        for relative, _record in ordinary_records
    )
    index_final_names = {
        parts(relative)[1]
        for relative, _record in ordinary_records
        if len(parts(relative)) == 2 and parts(relative)[0] == "documents"
    }
    expected_index_names = {f"{item}.json" for item in expected_documents}
    aggregate_final_present = "full-reader-aggregate.json" in files
    empty_object_prefix_present = any(
        parts(relative)[:1] == ("objects",) and not record[9]
        for relative, record in directories.items()
    )
    if index_final_names and checkpoint_final_count != 1_449:
        raise WaveOneRoleBFullReaderError("V3 document indexes exist before all checkpoints")
    if aggregate_final_present and (
        checkpoint_final_count != 1_449 or index_final_names != expected_index_names
    ):
        raise WaveOneRoleBFullReaderError(
            "V3 aggregate exists before exact checkpoint and index completion"
        )
    if empty_object_prefix_present and (
        checkpoint_final_count == 1_449 or index_final_names or aggregate_final_present
    ):
        raise WaveOneRoleBFullReaderError(
            "V3 empty object crash prefix crossed the completion phase"
        )
    if (
        stage == "control"
        and temporary_relative is None
        and "full-reader-execution-control.json" not in files
        and (
            set(directories) != {".", "locks"}
            or set(files) != {"locks/full-reader-execution.lease"}
            or lock_paths != {"locks/full-reader-execution.lease"}
        )
    ):
        raise WaveOneRoleBFullReaderError(
            "missing V3 control may be published only from the exact bootstrap state"
        )
    if temporary_relative is not None and final_relative is not None:
        final_parts = parts(final_relative)
        if final_relative == "full-reader-execution-control.json":
            allowed_control_directories = {".", "locks"}
            allowed_control_files = {
                "locks/full-reader-execution.lease",
                temporary_relative,
            }
            if paired_final is not None:
                allowed_control_files.add(final_relative)
            if (
                set(directories) != allowed_control_directories
                or set(files) != allowed_control_files
                or lock_paths != {"locks/full-reader-execution.lease"}
            ):
                raise WaveOneRoleBFullReaderError(
                    "V3 control publication transition crossed a later phase"
                )
            if stage == "finalize":
                raise WaveOneRoleBFullReaderError(
                    "V3 finalize rejects a control publication transition"
                )
            if stage == "run" and paired_final is None:
                raise WaveOneRoleBFullReaderError(
                    "standalone V3 control temporary requires the control command"
                )
        elif final_relative == "full-reader-aggregate.json":
            if stage != "finalize":
                raise WaveOneRoleBFullReaderError("V3 aggregate temporary belongs to finalize")
            if checkpoint_final_count != 1_449 or index_final_names != expected_index_names:
                raise WaveOneRoleBFullReaderError(
                    "V3 aggregate temporary precedes exact completion"
                )
        else:
            if stage != "run":
                raise WaveOneRoleBFullReaderError(
                    "V3 run temporary belongs to a different command stage"
                )
            if final_parts[:1] in {("objects",), ("checkpoints",)} and (
                index_final_names or aggregate_final_present
            ):
                raise WaveOneRoleBFullReaderError(
                    "V3 evidence temporary crossed the index or aggregate phase"
                )
            if (
                len(final_parts) == 2
                and final_parts[0] == "documents"
                and checkpoint_final_count != 1_449
            ):
                raise WaveOneRoleBFullReaderError(
                    "V3 document-index temporary exists before all checkpoints"
                )
            if len(final_parts) == 2 and final_parts[0] == "documents" and aggregate_final_present:
                raise WaveOneRoleBFullReaderError(
                    "V3 document-index temporary crossed aggregate publication"
                )
    confirmation = _v3_output_live_manifest(project_root)
    if not _same_typed_json(confirmation, manifest):
        raise WaveOneRoleBFullReaderError(
            "V3 output changed between preflight classification and return"
        )
    return temporary_relative, manifest


def _v3_publication_pair_path(project_root: Path, temporary_relative: str | None) -> str | None:
    """Return the output-relative final path only for an existing proven pair."""

    if temporary_relative is None:
        return None
    temporary = Path(temporary_relative)
    match = re.fullmatch(
        r"\.(?P<final>[^/\\]+\.(?:json|png))\.[0-9a-f]{32}\.tmp",
        temporary.name,
    )
    if match is None:
        raise WaveOneRoleBFullReaderError("V3 publication temporary name drifted")
    final_relative = temporary.parent / match.group("final")
    try:
        with _v3_held_output_directory(
            project_root,
            OUTPUT_RELATIVE_ROOT / temporary.parent,
            create=False,
        ) as (_directory, directory_fd):
            try:
                os.stat(
                    match.group("final"),
                    dir_fd=directory_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                return None
    except WaveOneRoleBFullReaderError as error:
        if "is absent" in str(error):
            return None
        raise
    return final_relative.as_posix()


def _v3_publication_target_path(temporary_relative: str | None) -> str | None:
    if temporary_relative is None:
        return None
    temporary = Path(temporary_relative)
    match = re.fullmatch(
        r"\.(?P<final>[^/\\]+\.(?:json|png))\.[0-9a-f]{32}\.tmp",
        temporary.name,
    )
    if match is None:
        raise WaveOneRoleBFullReaderError("V3 publication temporary name drifted")
    return (temporary.parent / match.group("final")).as_posix()


def _v3_recover_publication_directory(
    project_root: Path,
    relative: Path,
    *,
    create: bool,
    allowed_final: Callable[[str], bool] | None = None,
    validate_payload: Callable[[str, bytes], bool] | None = None,
    expected_output_manifest: list[list[Any]] | None = None,
) -> None:
    if _V3_OUTPUT_READ_BINDING.get() is not None:
        raise WaveOneRoleBFullReaderError(
            "V3 publication recovery cannot mutate a bound read snapshot"
        )
    _v3_assert_output_mutation_ancestry(project_root, "V3 publication recovery")
    grammar = re.compile(r"^\.(?P<final>[^/\\]+\.(?:json|png))\.[0-9a-f]{32}\.tmp$")
    if expected_output_manifest is not None and not _same_typed_json(
        _v3_output_live_manifest(project_root), expected_output_manifest
    ):
        raise WaveOneRoleBFullReaderError("V3 output changed after publication preflight")
    try:
        with _v3_held_output_directory(project_root, relative, create=create) as (
            _directory,
            directory_fd,
        ):
            if expected_output_manifest is not None:
                output_relative = relative.relative_to(OUTPUT_RELATIVE_ROOT)
                manifest_name = output_relative.as_posix()
                expected_directory = [
                    item
                    for item in expected_output_manifest
                    if item[0] == "d" and item[1] == manifest_name
                ]
                if len(expected_directory) != 1:
                    raise WaveOneRoleBFullReaderError(
                        "V3 recovery directory is absent from preflight manifest"
                    )
                expected = expected_directory[0]
                opened = os.fstat(directory_fd)
                if (
                    stat.S_IMODE(opened.st_mode) != expected[2]
                    or opened.st_nlink != expected[3]
                    or opened.st_size != expected[4]
                    or opened.st_mtime_ns != expected[5]
                    or opened.st_ctime_ns != expected[6]
                    or opened.st_dev != expected[7]
                    or opened.st_ino != expected[8]
                    or sorted(os.listdir(directory_fd)) != expected[9]
                ):
                    raise WaveOneRoleBFullReaderError(
                        "V3 recovery directory changed after preflight"
                    )
            names = sorted(os.listdir(directory_fd))
            manifest_files = (
                {item[1]: item for item in expected_output_manifest if item[0] == "f"}
                if expected_output_manifest is not None
                else {}
            )

            def assert_preflight_file(name: str) -> tuple[bytes, os.stat_result]:
                payload, identity = sentinel._hash_open_at(  # noqa: SLF001
                    directory_fd, name
                )
                if expected_output_manifest is None:
                    return payload, identity
                output_relative = relative.relative_to(OUTPUT_RELATIVE_ROOT)
                child_relative = (
                    output_relative / name if output_relative.parts else Path(name)
                ).as_posix()
                expected_file = manifest_files.get(child_relative)
                observed_file = [
                    "f",
                    child_relative,
                    stat.S_IMODE(identity.st_mode),
                    identity.st_nlink,
                    identity.st_size,
                    sha256_bytes(payload),
                    identity.st_mtime_ns,
                    identity.st_ctime_ns,
                    identity.st_dev,
                    identity.st_ino,
                ]
                if expected_file is None or not _same_typed_json(observed_file, expected_file):
                    raise WaveOneRoleBFullReaderError(
                        "V3 publication entry changed after preflight"
                    )
                return payload, identity

            temporary_names = [name for name in names if name.endswith(".tmp")]
            if not temporary_names:
                return
            if len(temporary_names) != 1:
                raise WaveOneRoleBFullReaderError(
                    "V3 publication directory contains multiple temporaries"
                )
            matches = []
            finals: set[str] = set()
            for name in temporary_names:
                match = grammar.fullmatch(name)
                if match is None:
                    raise WaveOneRoleBFullReaderError(
                        "V3 publication directory contains a malformed temporary"
                    )
                final = match.group("final")
                if final in finals:
                    raise WaveOneRoleBFullReaderError(
                        "V3 publication target has multiple temporaries"
                    )
                finals.add(final)
                matches.append((name, final))
            changed = False
            recovered: list[tuple[str, bytes]] = []
            for temporary_name, final_name in matches:
                if allowed_final is None or not allowed_final(final_name):
                    raise WaveOneRoleBFullReaderError(
                        "V3 publication temporary targets a foreign name"
                    )
                _temporary_payload, temporary = assert_preflight_file(temporary_name)
                if (
                    not stat.S_ISREG(temporary.st_mode)
                    or stat.S_IMODE(temporary.st_mode) not in {0o600, 0o444}
                    or temporary.st_nlink not in {1, 2}
                ):
                    raise WaveOneRoleBFullReaderError("V3 publication temporary topology drifted")
                if final_name in names:
                    _final_payload, final = assert_preflight_file(final_name)
                else:
                    final = None
                if final is not None:
                    if (
                        stat.S_IMODE(temporary.st_mode) != 0o444
                        or not stat.S_ISREG(final.st_mode)
                        or stat.S_IMODE(final.st_mode) != 0o444
                        or temporary.st_nlink != 2
                        or final.st_nlink != 2
                        or (
                            temporary.st_dev,
                            temporary.st_ino,
                            temporary.st_size,
                            temporary.st_mtime_ns,
                            temporary.st_ctime_ns,
                        )
                        != (
                            final.st_dev,
                            final.st_ino,
                            final.st_size,
                            final.st_mtime_ns,
                            final.st_ctime_ns,
                        )
                    ):
                        raise WaveOneRoleBFullReaderError(
                            "V3 linked publication pair topology drifted"
                        )
                    payload, opened = assert_preflight_file(final_name)
                    if (opened.st_dev, opened.st_ino) != (final.st_dev, final.st_ino) or (
                        validate_payload is not None and not validate_payload(final_name, payload)
                    ):
                        raise WaveOneRoleBFullReaderError(
                            "V3 linked publication pair content drifted"
                        )
                    os.unlink(temporary_name, dir_fd=directory_fd)
                    changed = True
                    recovered.append((final_name, payload))
                    continue
                if temporary.st_nlink != 1:
                    raise WaveOneRoleBFullReaderError(
                        "V3 standalone publication temporary has unexplained links"
                    )
                os.unlink(temporary_name, dir_fd=directory_fd)
                changed = True
            if changed:
                os.fsync(directory_fd)
            if any(name.endswith(".tmp") for name in os.listdir(directory_fd)):
                raise WaveOneRoleBFullReaderError(
                    "V3 publication directory recovery left a temporary"
                )
            for final_name, expected_payload in recovered:
                final_payload, final_identity = sentinel._hash_open_at(  # noqa: SLF001
                    directory_fd, final_name
                )
                if (
                    stat.S_IMODE(final_identity.st_mode) != 0o444
                    or final_identity.st_nlink != 1
                    or final_payload != expected_payload
                    or validate_payload is None
                    or not validate_payload(final_name, final_payload)
                ):
                    raise WaveOneRoleBFullReaderError(
                        "V3 recovered publication final identity drifted"
                    )
    except OSError as error:
        raise WaveOneRoleBFullReaderError("V3 publication recovery failed") from error
    _v3_assert_output_mutation_ancestry(project_root, "V3 publication recovery completion")


def _put_object(project_root: Path, payload: bytes, *, suffix: str) -> dict[str, Any]:
    _v3_assert_output_mutation_ancestry(project_root, "V3 object publication")
    if suffix not in {".json", ".png"}:
        raise WaveOneRoleBFullReaderError("V3 object suffix is not allowed")
    digest = sha256_bytes(payload)
    relative_directory = OUTPUT_RELATIVE_ROOT / "objects" / "sha256" / digest[:2]
    filename = f"{digest}{suffix}"
    _v3_recover_publication_directory(
        project_root,
        relative_directory,
        create=True,
        allowed_final=lambda candidate: candidate == filename,
        validate_payload=lambda candidate, candidate_payload: (
            candidate == filename
            and candidate_payload == payload
            and sha256_bytes(candidate_payload) == digest
        ),
    )
    try:
        with _v3_held_output_directory(project_root, relative_directory, create=True) as (
            directory,
            directory_fd,
        ):
            try:
                existing_payload, existing = sentinel._hash_open_at(  # noqa: SLF001
                    directory_fd, filename
                )
            except FileNotFoundError:
                existing_payload = None
                existing = None
            if existing_payload is not None:
                if (
                    existing_payload != payload
                    or stat.S_IMODE(existing.st_mode) != 0o444
                    or existing.st_nlink != 1
                    or existing.st_size != len(payload)
                    or sha256_bytes(existing_payload) != digest
                ):
                    raise WaveOneRoleBFullReaderError("existing immutable V3 object conflicts")
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
                    os.link(
                        temporary,
                        filename,
                        src_dir_fd=directory_fd,
                        dst_dir_fd=directory_fd,
                        follow_symlinks=False,
                    )
                    published, published_identity = sentinel._hash_open_at(  # noqa: SLF001
                        directory_fd, filename
                    )
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
                        raise WaveOneRoleBFullReaderError(
                            "immutable V3 object publication conflicted"
                        )
                    os.fsync(directory_fd)
                finally:
                    if descriptor >= 0:
                        os.close(descriptor)
                    if owned_identity is not None:
                        try:
                            observed = os.stat(
                                temporary,
                                dir_fd=directory_fd,
                                follow_symlinks=False,
                            )
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
            final_payload, final_identity = sentinel._hash_open_at(  # noqa: SLF001
                directory_fd, filename
            )
            if (
                final_payload != payload
                or stat.S_IMODE(final_identity.st_mode) != 0o444
                or final_identity.st_nlink != 1
                or final_identity.st_size != len(payload)
            ):
                raise WaveOneRoleBFullReaderError("immutable V3 object final link identity drifted")
            relative = (Path("objects/sha256") / digest[:2] / filename).as_posix()
            expected_path = project_root / OUTPUT_RELATIVE_ROOT / relative
            if (directory / filename) != expected_path:
                raise WaveOneRoleBFullReaderError("V3 object root projection drifted")
            _v3_assert_output_mutation_ancestry(project_root, "V3 object publication completion")
            return {
                "path": relative,
                "sha256": digest,
                "size_bytes": len(payload),
            }
    except sentinel.WaveOneRoleBSentinelError as error:
        raise WaveOneRoleBFullReaderError(str(error)) from error
    except (FileExistsError, OSError) as error:
        raise WaveOneRoleBFullReaderError("V3 object publication failed") from error


def _v3_load_policy(project_root: Path) -> dict[str, Any]:
    path = _project_path(project_root, POLICY_RELATIVE_PATH, "V3 full-reader policy")
    payload = _stable_bytes(path, "V3 full-reader policy")
    if (
        POLICY_SIZE_BYTES <= 0
        or len(payload) != POLICY_SIZE_BYTES
        or sha256_bytes(payload) != POLICY_SHA256
    ):
        raise WaveOneRoleBFullReaderError("V3 full-reader policy byte identity drifted")
    try:
        policy = yaml.safe_load(payload)
    except yaml.YAMLError as error:
        raise WaveOneRoleBFullReaderError("V3 full-reader policy is invalid YAML") from error
    required = {
        "version",
        "policy",
        "claim_boundary",
        "sealed_plan",
        "failed_v2_authority",
        "ocr_adoption",
        "native_reader",
        "execution",
        "safety",
        "expected",
        "output",
    }
    if (
        not isinstance(policy, dict)
        or set(policy) != required
        or policy.get("version") != 3
        or policy.get("policy") != "BANK_CORPUS_WAVE_1_ROLE_B_FULL_PAGE_READER_V3"
        or policy.get("claim_boundary")
        != "EXACT_SEALED_WAVE_1_SOURCE_VISIBLE_PAGE_TEXT_AND_GEOMETRY_ONLY"
    ):
        raise WaveOneRoleBFullReaderError("V3 full-reader policy fields drifted")
    exact_authority = {
        "archive_root": FAILED_V2_ARCHIVE_RELATIVE_ROOT.as_posix(),
        "receipt_path": FAILED_V2_RECEIPT_RELATIVE_PATH.as_posix(),
        "receipt_sha256": FAILED_V2_RECEIPT_SHA256,
        "receipt_size_bytes": FAILED_V2_RECEIPT_SIZE_BYTES,
        "incident_identity_sha256": FAILED_V2_INCIDENT_IDENTITY_SHA256,
        "receipt_status": (
            "IMMUTABLY_PRESERVED_FAILED_AFTER_COMPLETE_OCR_AND_THREE_NATIVE_CHECKPOINTS"
        ),
        "archive_portable_manifest_sha256": FAILED_V2_PORTABLE_MANIFEST_SHA256,
        "archive_live_manifest_sha256": FAILED_V2_LIVE_MANIFEST_SHA256,
        "archive_record_count": 8_658,
        "archive_file_count": 8_170,
        "archive_directory_count": 488,
        "archive_logical_bytes": 3_726_130_042,
        "control_filename": "full-reader-execution-control.json",
        "control_sha256": FAILED_V2_CONTROL_SHA256,
        "control_size_bytes": FAILED_V2_CONTROL_SIZE_BYTES,
        "control_identity_sha256": FAILED_V2_CONTROL_IDENTITY_SHA256,
        "producer_git_commit": FAILED_V2_PRODUCER_COMMIT,
        "producer_implementation_ledger_sha256": (FAILED_V2_IMPLEMENTATION_LEDGER_SHA256),
        "producer_implementation_ledger_record_count": 31,
        "checkpoint_count": 1_359,
        "checkpoint_canonical_sha256_set_sha256": FAILED_V2_CHECKPOINT_SET_SHA256,
        "content_addressed_object_count": 4_074,
        "missing_request_count": 90,
        "missing_request_set_sha256": FAILED_V2_MISSING_REQUEST_SET_SHA256,
        "aggregate_must_be_absent": True,
        "document_indexes_must_be_absent": True,
        "publication_temporaries_must_be_absent": True,
        "active_processes_and_held_locks_must_be_zero": True,
    }
    exact_ocr = {
        "route": _OCR_ROUTE,
        "selected_request_count": 1_356,
        "excluded_native_checkpoint_count": 3,
        "copied_evidence_object_count": 4_068,
        "copied_objects_per_request": 3,
        "copy_semantics": "BYTE_COPY_NEW_INODE_NO_HARDLINK_V1",
        "source_bytes_mode_mtime_inode_unchanged_required": True,
        "source_checkpoint_is_authority_only": True,
        "source_page_record_relabel_allowed": False,
        "v3_control_bound_record_required": True,
        "v3_control_bound_checkpoint_required": True,
        "original_status_preserved": True,
        "original_origin_preserved": True,
        "complete_status_count": 1_299,
        "geometry_terminal_status_count": 57,
        "line_axis_count": 96_369,
        "nonempty_line_axis_count": 96_304,
        "exact_empty_line_axis_count": 65,
        "word_token_count": 1_313_842,
        "nonempty_word_token_count": 1_313_842,
        "corrected_page_count": 20,
        "corrected_box_count": 22,
        "corrected_edge_count": 22,
        "quarantine_count": 0,
    }
    exact_expected = {
        "document_count": 27,
        "request_count": 1_449,
        "ocr_request_count": 1_356,
        "native_request_count": 93,
        "adopted_ocr_request_count": 1_356,
        "fresh_native_request_count": 93,
        "copied_ocr_object_count": 4_068,
        "final_object_count": 4_254,
        **_ZERO_INTERPRETATION,
    }
    exact_native = {
        "route": _NATIVE_ROUTE,
        "provider": "PYMUPDF_CAUSAL_NATIVE_TEXT_VISIBILITY_V1",
        "provider_runtime_ledger_sha256": (
            "57a50855a2669f07b0f9606a59de70f574615cdc490f7130f7bf2e2abce744e0"
        ),
        "evidence_adapter_path": "src/bctc_ai/ocr/causal_native_text_evidence_v2.py",
        "evidence_adapter_sha256": (
            "cc7a8fdf8c8e1332848b5c2583b8b2d4e0fa02e7a60567f2ac464c2ac35e5023"
        ),
        "evidence_adapter_size_bytes": 71_590,
        "causal_policy_path": "config/ocr/causal-native-text-v1.yaml",
        "causal_policy_sha256": (
            "4c6df806a7ded7d7a6c5241f1c523c7b9cbbf24829332293d8aa783a3044d647"
        ),
        "causal_policy_size_bytes": 876,
        "quality_policy_path": "config/ocr/native-text-quality-v2.yaml",
        "quality_policy_sha256": (
            "af0d735ea026abc7b189da46d36f103d1390687325324ecc1a325ba6ab51a660"
        ),
        "quality_policy_size_bytes": 596,
        "native_ordering_policy_identity": {
            "path": "config/ocr/causal-native-text-evidence-v2.yaml",
            "sha256": ("ec249629e83944f03d25b30d5df29ddfbcd9bc250b06d3ed9cc6d60e2533c309"),
            "size_bytes": 1_305,
        },
        "execution": "FRESH_ALL_93_REQUESTS_WITH_NATIVE_EVIDENCE_ADAPTER_V2",
        "request_count": 93,
        "archived_native_checkpoint_adoption_allowed": False,
        "archived_native_object_adoption_allowed": False,
        "page_level_execution": True,
        "source_bytes_held_and_authenticated": True,
        "ocr_fallback_allowed": False,
        "network_allowed": False,
        "unresolved_is_terminal_source_accounting": True,
        "terminal_line_contiguity_disposition_required": True,
        "terminal_statuses": [
            "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
            "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY",
            "UNRESOLVED_NATIVE_TEXT_QUALITY",
            "UNRESOLVED_CAUSAL_NATIVE_LINE_CONTIGUITY",
        ],
    }
    exact_execution = {
        "ocr_worker_allowed": False,
        "ocr_inference_allowed": False,
        "network_allowed": False,
        "request_scope": "EXACT_ALL_1449_SEALED_WAVE_1_PAGE_REQUESTS",
        "per_document_locking": "FLOCK_EXCLUSIVE_NOFOLLOW",
        "checkpoint": "ONE_IMMUTABLE_CONSTANT_SIZE_CANONICAL_CHECKPOINT_PER_PAGE",
        "checkpoint_order": (
            "OCR_REQUEST_ORDINAL_ASC_THEN_NATIVE_REQUEST_ORDINAL_ASC_PER_DOCUMENT"
        ),
        "document_index": "DETERMINISTIC_FINAL_INDEX_AFTER_ALL_DOCUMENT_REQUESTS",
        "orphan_adoption": "FULL_V3_CONTROL_BOUND_REQUEST_IDENTITY_ONLY",
        "completed_resume_native_read_count": 0,
        "minimum_free_space_bytes": 53_687_091_200,
        "required_process_umask": "0022",
        "timestamps_in_deterministic_evidence_allowed": False,
        "timing_observation_enabled": False,
        "overwrite_allowed": False,
    }
    exact_safety = {
        "production_authentication_bypass_allowed": False,
        "injectable_production_provider_allowed": False,
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
        "failed_v2_archive_mutation_allowed": False,
    }
    exact_output = {
        "root": OUTPUT_RELATIVE_ROOT.as_posix(),
        "control_filename": "full-reader-execution-control.json",
        "object_directory": "objects",
        "checkpoint_directory": "checkpoints",
        "document_index_directory": "documents",
        "lock_directory": "locks",
        "aggregate_filename": "full-reader-aggregate.json",
        "canonical_json": True,
        "exclusive_no_overwrite": True,
    }
    if (
        not _same_typed_json(policy.get("failed_v2_authority"), exact_authority)
        or not _same_typed_json(policy.get("ocr_adoption"), exact_ocr)
        or not _same_typed_json(policy.get("native_reader"), exact_native)
        or not _same_typed_json(policy.get("execution"), exact_execution)
        or not _same_typed_json(policy.get("safety"), exact_safety)
        or not _same_typed_json(policy.get("expected"), exact_expected)
        or not _same_typed_json(policy.get("output"), exact_output)
    ):
        raise WaveOneRoleBFullReaderError("V3 policy authority or accounting drifted")
    for path_key, sha_key, size_key in (
        (
            "evidence_adapter_path",
            "evidence_adapter_sha256",
            "evidence_adapter_size_bytes",
        ),
        ("causal_policy_path", "causal_policy_sha256", "causal_policy_size_bytes"),
        ("quality_policy_path", "quality_policy_sha256", "quality_policy_size_bytes"),
    ):
        candidate = _stable_bytes(
            _project_path(project_root, exact_native[path_key], f"V3 native {path_key}"),
            f"V3 native {path_key}",
        )
        if sha256_bytes(candidate) != exact_native[sha_key] or (
            size_key is not None and len(candidate) != exact_native[size_key]
        ):
            raise WaveOneRoleBFullReaderError("V3 native dependency byte identity drifted")
    return policy


def _v3_implementation_ledger(project_root: Path, commit: str) -> dict[str, Any]:
    try:
        return sentinel._implementation_ledger(  # noqa: SLF001 - authenticated substrate
            project_root, commit, V3_IMPLEMENTATION_RELATIVE_PATHS
        )
    except sentinel.WaveOneRoleBSentinelError as error:
        raise WaveOneRoleBFullReaderError(str(error)) from error


@contextmanager
def _v3_bind_output_reads(project_root: Path, manifest: list[list[Any]]) -> Iterator[None]:
    file_tokens = {
        item[1]: item
        for item in manifest
        if isinstance(item, list) and len(item) == 10 and item[0] == "f"
    }
    if len(file_tokens) != sum(item[0] == "f" for item in manifest):
        raise WaveOneRoleBFullReaderError("V3 output manifest file set drifted")
    directory_tokens = {
        item[1]: item
        for item in manifest
        if isinstance(item, list) and len(item) == 10 and item[0] == "d"
    }
    if (
        len(directory_tokens) != sum(item[0] == "d" for item in manifest)
        or set(file_tokens).intersection(directory_tokens)
        or "." not in directory_tokens
        or len(file_tokens) + len(directory_tokens) != len(manifest)
    ):
        raise WaveOneRoleBFullReaderError("V3 output manifest directory set drifted")
    output_root = project_root / OUTPUT_RELATIVE_ROOT
    directory_fds: dict[str, int] = {}
    stack = ExitStack()
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )

    def observed_directory(
        relative: str, descriptor: int, parent_fd: int | None, name: str | None
    ) -> list[Any]:
        before = os.fstat(descriptor)
        names = sorted(os.listdir(descriptor))
        after = os.fstat(descriptor)
        if parent_fd is None:
            named = os.stat(output_root, follow_symlinks=False)
        else:
            assert name is not None
            named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        identity = lambda item: (  # noqa: E731 - immutable directory identity
            item.st_dev,
            item.st_ino,
            item.st_mode,
            item.st_nlink,
            item.st_size,
            item.st_mtime_ns,
            item.st_ctime_ns,
        )
        if (
            not stat.S_ISDIR(before.st_mode)
            or identity(before) != identity(after)
            or identity(after) != identity(named)
        ):
            raise WaveOneRoleBFullReaderError("V3 bound output directory identity drifted")
        return [
            "d",
            relative,
            stat.S_IMODE(after.st_mode),
            after.st_nlink,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
            after.st_dev,
            after.st_ino,
            names,
        ]

    try:
        retained_root_fd = _v3_retained_output_root_fd(project_root)
        root_fd = (
            os.open(output_root, flags) if retained_root_fd is None else os.dup(retained_root_fd)
        )
        stack.callback(os.close, root_fd)
        if not _same_typed_json(
            observed_directory(".", root_fd, None, None), directory_tokens["."]
        ):
            raise WaveOneRoleBFullReaderError("V3 output root differs from the bound snapshot")
        directory_fds["."] = root_fd
        for relative in sorted(
            (item for item in directory_tokens if item != "."),
            key=lambda item: (item.count("/"), item),
        ):
            relative_path = Path(relative)
            parent = relative_path.parent.as_posix()
            parent_fd = directory_fds.get(parent)
            if parent_fd is None:
                raise WaveOneRoleBFullReaderError("V3 output manifest directory parent is absent")
            descriptor = os.open(relative_path.name, flags, dir_fd=parent_fd)
            stack.callback(os.close, descriptor)
            if not _same_typed_json(
                observed_directory(relative, descriptor, parent_fd, relative_path.name),
                directory_tokens[relative],
            ):
                raise WaveOneRoleBFullReaderError(
                    "V3 output directory differs from the bound snapshot"
                )
            directory_fds[relative] = descriptor
    except OSError as error:
        stack.close()
        raise WaveOneRoleBFullReaderError(
            "V3 output snapshot directories cannot be bound safely"
        ) from error
    except BaseException:
        stack.close()
        raise

    token = _V3_OUTPUT_READ_BINDING.set((output_root, file_tokens, directory_tokens, directory_fds))
    try:
        yield
    finally:
        try:
            for relative in sorted(
                directory_tokens,
                key=lambda item: (item.count("/"), item),
                reverse=True,
            ):
                relative_path = Path(relative)
                if relative == ".":
                    parent_fd = None
                    name = None
                else:
                    parent_fd = directory_fds.get(relative_path.parent.as_posix())
                    name = relative_path.name
                    if parent_fd is None:
                        raise WaveOneRoleBFullReaderError(
                            "V3 bound output directory parent disappeared"
                        )
                if not _same_typed_json(
                    observed_directory(relative, directory_fds[relative], parent_fd, name),
                    directory_tokens[relative],
                ):
                    raise WaveOneRoleBFullReaderError(
                        "V3 bound output directory changed before release"
                    )
        except OSError as error:
            raise WaveOneRoleBFullReaderError(
                "V3 bound output directory cannot be revalidated"
            ) from error
        finally:
            _V3_OUTPUT_READ_BINDING.reset(token)
            stack.close()


def _v3_manifest_has_file(manifest: list[list[Any]], relative: str) -> bool:
    matches = [item for item in manifest if item[0] == "f" and item[1] == relative]
    if len(matches) > 1:
        raise WaveOneRoleBFullReaderError("V3 output manifest contains a duplicate file")
    return bool(matches)


def _v3_bound_output_file_present(path: Path) -> bool | None:
    binding = _V3_OUTPUT_READ_BINDING.get()
    if binding is None:
        return None
    output_root, file_tokens, _directory_tokens, _directory_fds = binding
    try:
        relative = path.relative_to(output_root).as_posix()
    except ValueError:
        return None
    return relative in file_tokens


def _v3_assert_bound_output_read(
    path: Path, payload: bytes, identity: os.stat_result, label: str
) -> None:
    binding = _V3_OUTPUT_READ_BINDING.get()
    if binding is None:
        return
    output_root, file_tokens, _directory_tokens, directory_fds = binding
    try:
        relative = path.relative_to(output_root).as_posix()
    except ValueError:
        return
    expected = file_tokens.get(relative)
    if expected is None:
        raise WaveOneRoleBFullReaderError(f"{label} was absent from the bound output snapshot")
    relative_path = Path(relative)
    parent_fd = directory_fds.get(relative_path.parent.as_posix())
    if parent_fd is None:
        raise WaveOneRoleBFullReaderError(f"{label} bound output parent directory is absent")
    try:
        named = os.stat(relative_path.name, dir_fd=parent_fd, follow_symlinks=False)
        absolute_named = os.stat(path, follow_symlinks=False)
    except OSError as error:
        raise WaveOneRoleBFullReaderError(f"{label} bound output pathname changed") from error
    observed = [
        "f",
        relative,
        stat.S_IMODE(identity.st_mode),
        identity.st_nlink,
        identity.st_size,
        sha256_bytes(payload),
        identity.st_mtime_ns,
        identity.st_ctime_ns,
        identity.st_dev,
        identity.st_ino,
    ]
    named_observed = [
        "f",
        relative,
        stat.S_IMODE(named.st_mode),
        named.st_nlink,
        named.st_size,
        sha256_bytes(payload),
        named.st_mtime_ns,
        named.st_ctime_ns,
        named.st_dev,
        named.st_ino,
    ]
    absolute_observed = [
        "f",
        relative,
        stat.S_IMODE(absolute_named.st_mode),
        absolute_named.st_nlink,
        absolute_named.st_size,
        sha256_bytes(payload),
        absolute_named.st_mtime_ns,
        absolute_named.st_ctime_ns,
        absolute_named.st_dev,
        absolute_named.st_ino,
    ]
    if (
        not stat.S_ISREG(named.st_mode)
        or not stat.S_ISREG(absolute_named.st_mode)
        or not _same_typed_json(observed, expected)
        or not _same_typed_json(named_observed, expected)
        or not _same_typed_json(absolute_observed, expected)
    ):
        raise WaveOneRoleBFullReaderError(f"{label} differs from the bound output snapshot")


def _v3_bound_output_directory(path: Path) -> tuple[bool, int | None]:
    binding = _V3_OUTPUT_READ_BINDING.get()
    if binding is None:
        return False, None
    output_root, _file_tokens, _directory_tokens, directory_fds = binding
    try:
        relative = path.relative_to(output_root).as_posix()
    except ValueError:
        return False, None
    return True, directory_fds.get(relative)


def _v3_require_bound_output() -> tuple[
    Path,
    dict[str, list[Any]],
    dict[str, list[Any]],
    dict[str, int],
]:
    binding = _V3_OUTPUT_READ_BINDING.get()
    if binding is None:
        raise WaveOneRoleBFullReaderError("V3 semantic output replay requires a bound snapshot")
    return binding


def _v3_require_bound_archive() -> tuple[
    Path,
    dict[str, list[Any]],
    dict[str, list[Any]],
    dict[str, int],
]:
    binding = _V3_ARCHIVE_READ_BINDING.get()
    if binding is None:
        raise WaveOneRoleBFullReaderError(
            "failed V2 archive replay requires a held archive generation"
        )
    return binding


def _v3_assert_bound_archive_read(
    path: Path, payload: bytes, identity: os.stat_result, label: str
) -> None:
    binding = _V3_ARCHIVE_READ_BINDING.get()
    if binding is None:
        return
    archive_root, file_tokens, _directory_tokens, directory_fds = binding
    try:
        relative = path.relative_to(archive_root).as_posix()
    except ValueError:
        return
    expected = file_tokens.get(relative)
    relative_path = Path(relative)
    parent_fd = directory_fds.get(relative_path.parent.as_posix())
    if expected is None or parent_fd is None:
        raise WaveOneRoleBFullReaderError(f"{label} was absent from the held failed-V2 archive")
    try:
        named = os.stat(relative_path.name, dir_fd=parent_fd, follow_symlinks=False)
        absolute_named = os.stat(path, follow_symlinks=False)
    except OSError as error:
        raise WaveOneRoleBFullReaderError(f"{label} archive pathname changed") from error

    def observed(item: os.stat_result) -> list[Any]:
        return [
            "f",
            relative,
            stat.S_IMODE(item.st_mode),
            item.st_nlink,
            item.st_size,
            item.st_mtime_ns,
            item.st_ctime_ns,
            item.st_dev,
            item.st_ino,
        ]

    if (
        not stat.S_ISREG(identity.st_mode)
        or not stat.S_ISREG(named.st_mode)
        or not stat.S_ISREG(absolute_named.st_mode)
        or not _same_typed_json(observed(identity), expected)
        or not _same_typed_json(observed(named), expected)
        or not _same_typed_json(observed(absolute_named), expected)
        or len(payload) != identity.st_size
    ):
        raise WaveOneRoleBFullReaderError(
            f"{label} differs from the held failed-V2 archive generation"
        )


def _v3_assert_bound_archive_receipt_read(
    path: Path, payload: bytes, identity: os.stat_result, label: str
) -> None:
    binding = _V3_ARCHIVE_RECEIPT_READ_BINDING.get()
    if binding is None:
        return
    expected_path, parent_fd, expected = binding
    if path != expected_path:
        return
    named = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
    absolute_named = os.stat(path, follow_symlinks=False)

    def observed(item: os.stat_result) -> list[Any]:
        return [
            "f",
            path.name,
            stat.S_IMODE(item.st_mode),
            item.st_nlink,
            item.st_size,
            item.st_mtime_ns,
            item.st_ctime_ns,
            item.st_dev,
            item.st_ino,
        ]

    if (
        not stat.S_ISREG(identity.st_mode)
        or not stat.S_ISREG(named.st_mode)
        or not stat.S_ISREG(absolute_named.st_mode)
        or not _same_typed_json(observed(identity), expected)
        or not _same_typed_json(observed(named), expected)
        or not _same_typed_json(observed(absolute_named), expected)
        or len(payload) != identity.st_size
    ):
        raise WaveOneRoleBFullReaderError(
            f"{label} differs from the held failed-V2 receipt generation"
        )


def _v3_read_nofollow(
    path: Path, label: str, *, expected_nlink: int = 1
) -> tuple[bytes, os.stat_result]:
    if expected_nlink not in {1, 2}:
        raise WaveOneRoleBFullReaderError(f"{label} expected link count is invalid")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    bound_parent_fd = None
    bound_name = None
    archive_bound = False
    archive_receipt_bound = False
    retained_output_context = None
    binding = _V3_OUTPUT_READ_BINDING.get()
    if binding is not None:
        output_root, file_tokens, _directory_tokens, directory_fds = binding
        try:
            relative = path.relative_to(output_root).as_posix()
        except ValueError:
            relative = None
        if relative is not None:
            if relative not in file_tokens:
                raise WaveOneRoleBFullReaderError(
                    f"{label} was absent from the bound output snapshot"
                )
            relative_path = Path(relative)
            bound_parent_fd = directory_fds.get(relative_path.parent.as_posix())
            bound_name = relative_path.name
            if bound_parent_fd is None:
                raise WaveOneRoleBFullReaderError(
                    f"{label} bound output parent directory is absent"
                )
    if bound_parent_fd is None:
        archive_binding = _V3_ARCHIVE_READ_BINDING.get()
        if archive_binding is not None:
            archive_root, archive_files, _archive_directories, archive_fds = archive_binding
            try:
                archive_relative = path.relative_to(archive_root).as_posix()
            except ValueError:
                archive_relative = None
            if archive_relative is not None:
                if archive_relative not in archive_files:
                    raise WaveOneRoleBFullReaderError(
                        f"{label} was absent from the held failed-V2 archive"
                    )
                archive_path = Path(archive_relative)
                bound_parent_fd = archive_fds.get(archive_path.parent.as_posix())
                bound_name = archive_path.name
                archive_bound = True
                if bound_parent_fd is None:
                    raise WaveOneRoleBFullReaderError(f"{label} archive parent directory is absent")
    if bound_parent_fd is None:
        receipt_binding = _V3_ARCHIVE_RECEIPT_READ_BINDING.get()
        if receipt_binding is not None and path == receipt_binding[0]:
            bound_parent_fd = receipt_binding[1]
            bound_name = path.name
            archive_receipt_bound = True
    mutation_binding = _V3_OUTPUT_MUTATION_BINDING.get()
    if bound_parent_fd is None and mutation_binding is not None:
        bound_project_root = mutation_binding[0]
        output_root = bound_project_root / OUTPUT_RELATIVE_ROOT
        try:
            output_relative = path.relative_to(output_root)
        except ValueError:
            output_relative = None
        if output_relative is not None:
            retained_output_context = _v3_held_output_directory(
                bound_project_root,
                OUTPUT_RELATIVE_ROOT / output_relative.parent,
                create=False,
            )
            _directory, bound_parent_fd = retained_output_context.__enter__()
            bound_name = output_relative.name
    try:
        if bound_parent_fd is None:
            descriptor = os.open(path, flags)
        else:
            assert bound_name is not None
            descriptor = os.open(bound_name, flags, dir_fd=bound_parent_fd)
    except OSError as error:
        if retained_output_context is not None:
            retained_output_context.__exit__(None, None, None)
        raise WaveOneRoleBFullReaderError(f"{label} cannot be opened safely") from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != expected_nlink:
            raise WaveOneRoleBFullReaderError(f"{label} is not an immutable regular file")
        chunks = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        try:
            if bound_parent_fd is None:
                named = os.stat(path, follow_symlinks=False)
            else:
                assert bound_name is not None
                named = os.stat(bound_name, dir_fd=bound_parent_fd, follow_symlinks=False)
        except OSError as error:
            raise WaveOneRoleBFullReaderError(f"{label} pathname changed") from error
        identity = lambda item: (  # noqa: E731 - compact immutable identity projection
            item.st_dev,
            item.st_ino,
            item.st_mode,
            item.st_nlink,
            item.st_size,
            item.st_mtime_ns,
            item.st_ctime_ns,
        )
        if identity(before) != identity(after) or identity(after) != identity(named):
            raise WaveOneRoleBFullReaderError(f"{label} changed while being read")
        payload = b"".join(chunks)
        if len(payload) != after.st_size:
            raise WaveOneRoleBFullReaderError(f"{label} byte count drifted")
        _v3_assert_bound_output_read(path, payload, after, label)
        if archive_bound:
            _v3_assert_bound_archive_read(path, payload, after, label)
        if archive_receipt_bound:
            _v3_assert_bound_archive_receipt_read(path, payload, after, label)
        return payload, after
    finally:
        os.close(descriptor)
        if retained_output_context is not None:
            retained_output_context.__exit__(None, None, None)


@contextmanager
def _v3_failed_archive_locks(
    project_root: Path, document_ids: list[str]
) -> Iterator[tuple[tuple[str, int, tuple[int, int]], ...]]:
    if (
        len(document_ids) != 27
        or len(set(document_ids)) != 27
        or any(
            not isinstance(item, str)
            or not item.startswith("sha256:")
            or not _is_sha256(item.removeprefix("sha256:"))
            for item in document_ids
        )
    ):
        raise WaveOneRoleBFullReaderError("failed V2 archive lock document set drifted")
    archive_root = _project_path(
        project_root, FAILED_V2_ARCHIVE_RELATIVE_ROOT, "failed V2 archive root"
    )
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    project_fd = parent_fd = archive_fd = lock_fd = document_fd = -1
    ancestor_fds: list[int] = []
    ancestor_bindings: list[tuple[int, int, str, tuple[int, ...], frozenset[str]]] = []
    directory_fds: dict[str, int] = {}
    directory_tokens: dict[str, list[Any]] = {}
    file_tokens: dict[str, list[Any]] = {}
    receipt_token: list[Any] | None = None
    opened_directory_fds: list[int] = []
    held: list[tuple[str, int, tuple[int, int], int, str]] = []

    def ancestry_token(item: os.stat_result) -> tuple[int, ...]:
        return (
            item.st_dev,
            item.st_ino,
            item.st_mode,
            item.st_nlink,
            item.st_size,
            item.st_mtime_ns,
            item.st_ctime_ns,
        )

    def bind_ancestor(parent_descriptor: int, name: str) -> int:
        descriptor = os.open(name, flags, dir_fd=parent_descriptor)
        promoted = False
        try:
            opened = os.fstat(descriptor)
            named = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
            if not stat.S_ISDIR(opened.st_mode) or ancestry_token(opened) != ancestry_token(named):
                raise WaveOneRoleBFullReaderError("failed V2 archive ancestor generation drifted")
            names = frozenset(os.listdir(descriptor))
            ancestor_fds.append(descriptor)
            ancestor_bindings.append(
                (
                    parent_descriptor,
                    descriptor,
                    name,
                    ancestry_token(opened),
                    names,
                )
            )
            promoted = True
            return descriptor
        finally:
            if not promoted:
                os.close(descriptor)

    def validate_ancestry() -> None:
        for parent_descriptor, descriptor, name, expected, _names in ancestor_bindings:
            opened = os.fstat(descriptor)
            named = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
            if (
                ancestry_token(opened)[:3] != expected[:3]
                or ancestry_token(named)[:3] != expected[:3]
            ):
                raise WaveOneRoleBFullReaderError("failed V2 archive ancestor changed while held")
        if receipt_token is not None:
            receipt_identity = os.stat(
                FAILED_V2_RECEIPT_RELATIVE_PATH.name,
                dir_fd=parent_fd,
                follow_symlinks=False,
            )
            observed_receipt = [
                "f",
                FAILED_V2_RECEIPT_RELATIVE_PATH.name,
                stat.S_IMODE(receipt_identity.st_mode),
                receipt_identity.st_nlink,
                receipt_identity.st_size,
                receipt_identity.st_mtime_ns,
                receipt_identity.st_ctime_ns,
                receipt_identity.st_dev,
                receipt_identity.st_ino,
            ]
            if not _same_typed_json(observed_receipt, receipt_token):
                raise WaveOneRoleBFullReaderError(
                    "failed V2 incident receipt changed while archive was held"
                )

    def directory_record(
        relative: str,
        descriptor: int,
        parent_descriptor: int,
        name: str,
    ) -> list[Any]:
        before = os.fstat(descriptor)
        names = sorted(os.listdir(descriptor))
        after = os.fstat(descriptor)
        named = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
        identity = lambda item: (  # noqa: E731 - exact held directory token
            item.st_dev,
            item.st_ino,
            item.st_mode,
            item.st_nlink,
            item.st_size,
            item.st_mtime_ns,
            item.st_ctime_ns,
        )
        if (
            not stat.S_ISDIR(before.st_mode)
            or identity(before) != identity(after)
            or identity(after) != identity(named)
        ):
            raise WaveOneRoleBFullReaderError("failed V2 archive directory generation drifted")
        return [
            "d",
            relative,
            stat.S_IMODE(after.st_mode),
            after.st_nlink,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
            after.st_dev,
            after.st_ino,
            names,
        ]

    def file_record(relative: str, identity: os.stat_result) -> list[Any]:
        return [
            "f",
            relative,
            stat.S_IMODE(identity.st_mode),
            identity.st_nlink,
            identity.st_size,
            identity.st_mtime_ns,
            identity.st_ctime_ns,
            identity.st_dev,
            identity.st_ino,
        ]

    def visit(
        relative: str,
        descriptor: int,
        parent_descriptor: int,
        name: str,
    ) -> None:
        record = directory_record(relative, descriptor, parent_descriptor, name)
        directory_tokens[relative] = record
        for child_name in record[9]:
            child = os.stat(child_name, dir_fd=descriptor, follow_symlinks=False)
            child_relative = (
                Path(child_name) if relative == "." else Path(relative) / child_name
            ).as_posix()
            if stat.S_ISDIR(child.st_mode):
                child_fd = directory_fds.get(child_relative)
                if child_fd is None:
                    child_fd = os.open(child_name, flags, dir_fd=descriptor)
                    directory_fds[child_relative] = child_fd
                    opened_directory_fds.append(child_fd)
                visit(child_relative, child_fd, descriptor, child_name)
                continue
            if not stat.S_ISREG(child.st_mode) or child.st_nlink != 1:
                raise WaveOneRoleBFullReaderError(
                    "failed V2 archive contains a special or linked entry"
                )
            file_tokens[child_relative] = file_record(child_relative, child)

    def validate_bound_generation() -> None:
        for relative in sorted(
            directory_tokens,
            key=lambda item: (item.count("/"), item),
            reverse=True,
        ):
            relative_path = Path(relative)
            if relative == ".":
                parent_descriptor = parent_fd
                name = FAILED_V2_ARCHIVE_RELATIVE_ROOT.name
            else:
                parent_descriptor = directory_fds.get(relative_path.parent.as_posix())
                name = relative_path.name
                if parent_descriptor is None:
                    raise WaveOneRoleBFullReaderError(
                        "failed V2 archive parent generation is absent"
                    )
            if not _same_typed_json(
                directory_record(
                    relative,
                    directory_fds[relative],
                    parent_descriptor,
                    name,
                ),
                directory_tokens[relative],
            ):
                raise WaveOneRoleBFullReaderError("failed V2 archive directory changed while held")
        for relative, expected in file_tokens.items():
            relative_path = Path(relative)
            parent_descriptor = directory_fds.get(relative_path.parent.as_posix())
            if parent_descriptor is None:
                raise WaveOneRoleBFullReaderError(
                    "failed V2 archive file parent generation is absent"
                )
            observed = os.stat(
                relative_path.name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
            if not _same_typed_json(file_record(relative, observed), expected):
                raise WaveOneRoleBFullReaderError(
                    "failed V2 archive file identity changed while held"
                )

    try:
        project_fd = os.open(project_root, flags)
        current_parent_fd = project_fd
        for component in FAILED_V2_ARCHIVE_RELATIVE_ROOT.parent.parts:
            current_parent_fd = bind_ancestor(current_parent_fd, component)
        parent_fd = current_parent_fd
        archive_fd = os.open(FAILED_V2_ARCHIVE_RELATIVE_ROOT.name, flags, dir_fd=parent_fd)
        opened_directory_fds.append(archive_fd)
        lock_fd = os.open("locks", flags, dir_fd=archive_fd)
        opened_directory_fds.append(lock_fd)
        document_fd = os.open("documents", flags, dir_fd=lock_fd)
        opened_directory_fds.append(document_fd)
        directory_fds.update({".": archive_fd, "locks": lock_fd, "locks/documents": document_fd})
        expected_document_names = {f"{item.removeprefix('sha256:')}.lock" for item in document_ids}
        if set(os.listdir(lock_fd)) != {"documents", "full-reader-execution.lease"}:
            raise WaveOneRoleBFullReaderError("failed V2 archive lock root has foreign entries")
        if set(os.listdir(document_fd)) != expected_document_names:
            raise WaveOneRoleBFullReaderError("failed V2 archive document-lock names drifted")
        targets = [(lock_fd, "full-reader-execution.lease")]
        targets.extend((document_fd, name) for name in sorted(expected_document_names))
        for directory_fd, name in targets:
            descriptor = os.open(
                name,
                os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_fd,
            )
            try:
                before = os.fstat(descriptor)
                named = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                if (
                    not stat.S_ISREG(before.st_mode)
                    or stat.S_IMODE(before.st_mode) != 0o600
                    or before.st_nlink != 1
                    or before.st_size != 0
                    or (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino)
                ):
                    raise WaveOneRoleBFullReaderError("failed V2 archive lock topology drifted")
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError as error:
                    raise WaveOneRoleBFullReaderError(
                        "failed V2 archive is actively held by another process"
                    ) from error
                acquired = os.fstat(descriptor)
                acquired_named = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                if (
                    not stat.S_ISREG(acquired.st_mode)
                    or stat.S_IMODE(acquired.st_mode) != 0o600
                    or acquired.st_nlink != 1
                    or acquired.st_size != 0
                    or (acquired.st_dev, acquired.st_ino) != (before.st_dev, before.st_ino)
                    or (acquired_named.st_dev, acquired_named.st_ino)
                    != (before.st_dev, before.st_ino)
                ):
                    raise WaveOneRoleBFullReaderError(
                        "failed V2 archive lock changed during acquisition"
                    )
                held.append(
                    (
                        name,
                        descriptor,
                        (before.st_dev, before.st_ino),
                        directory_fd,
                        ("global" if name == "full-reader-execution.lease" else "document"),
                    )
                )
            except BaseException:
                if all(item[1] != descriptor for item in held):
                    os.close(descriptor)
                raise
        visit(
            ".",
            archive_fd,
            parent_fd,
            FAILED_V2_ARCHIVE_RELATIVE_ROOT.name,
        )
        receipt_identity = os.stat(
            FAILED_V2_RECEIPT_RELATIVE_PATH.name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
        receipt_token = [
            "f",
            FAILED_V2_RECEIPT_RELATIVE_PATH.name,
            stat.S_IMODE(receipt_identity.st_mode),
            receipt_identity.st_nlink,
            receipt_identity.st_size,
            receipt_identity.st_mtime_ns,
            receipt_identity.st_ctime_ns,
            receipt_identity.st_dev,
            receipt_identity.st_ino,
        ]
        if (
            not stat.S_ISREG(receipt_identity.st_mode)
            or receipt_identity.st_nlink != 1
            or stat.S_IMODE(receipt_identity.st_mode) != 0o444
        ):
            raise WaveOneRoleBFullReaderError("failed V2 incident receipt topology drifted")
        lock_token = directory_tokens.get("locks")
        document_token = directory_tokens.get("locks/documents")
        if (
            lock_token is None
            or lock_token[2] != 0o755
            or lock_token[3] != 3
            or set(lock_token[9]) != {"documents", "full-reader-execution.lease"}
            or document_token is None
            or document_token[2] != 0o755
            or document_token[3] != 2
            or set(document_token[9]) != expected_document_names
        ):
            raise WaveOneRoleBFullReaderError("failed V2 archive lock directory authority drifted")
        validate_bound_generation()
        validate_ancestry()
        binding_token = _V3_ARCHIVE_READ_BINDING.set(
            (archive_root, file_tokens, directory_tokens, directory_fds)
        )
        receipt_binding_token = _V3_ARCHIVE_RECEIPT_READ_BINDING.set(
            (
                project_root / FAILED_V2_RECEIPT_RELATIVE_PATH,
                parent_fd,
                receipt_token,
            )
        )
        shared_parent_token = _V3_SHARED_OUTPUT_PARENT_BINDING.set(
            (
                project_root,
                parent_fd,
                (
                    os.fstat(parent_fd).st_dev,
                    os.fstat(parent_fd).st_ino,
                    os.fstat(parent_fd).st_mode,
                ),
            )
        )
        yield tuple(
            (kind, descriptor, identity)
            for _name, descriptor, identity, _directory_fd, kind in held
        )
        validate_bound_generation()
        validate_ancestry()
        for name, descriptor, identity, directory_fd, _kind in held:
            after = os.fstat(descriptor)
            named_after = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            if (
                not stat.S_ISREG(after.st_mode)
                or stat.S_IMODE(after.st_mode) != 0o600
                or after.st_nlink != 1
                or after.st_size != 0
                or (after.st_dev, after.st_ino) != identity
                or (named_after.st_dev, named_after.st_ino) != identity
            ):
                raise WaveOneRoleBFullReaderError("held failed V2 archive lock changed")
        validate_bound_generation()
        validate_ancestry()
    except OSError as error:
        raise WaveOneRoleBFullReaderError("failed V2 archive lock hierarchy drifted") from error
    finally:
        cleanup_errors: list[BaseException] = []
        if "shared_parent_token" in locals():
            _v3_cleanup_attempt(
                cleanup_errors,
                lambda: _V3_SHARED_OUTPUT_PARENT_BINDING.reset(shared_parent_token),
            )
        if "receipt_binding_token" in locals():
            _v3_cleanup_attempt(
                cleanup_errors,
                lambda: _V3_ARCHIVE_RECEIPT_READ_BINDING.reset(receipt_binding_token),
            )
        if "binding_token" in locals():
            _v3_cleanup_attempt(
                cleanup_errors,
                lambda: _V3_ARCHIVE_READ_BINDING.reset(binding_token),
            )
        for _name, descriptor, _identity, _directory_fd, _kind in reversed(held):
            _v3_cleanup_attempt(
                cleanup_errors,
                lambda descriptor_to_unlock=descriptor: fcntl.flock(
                    descriptor_to_unlock, fcntl.LOCK_UN
                ),
            )
            _v3_cleanup_attempt(
                cleanup_errors,
                lambda descriptor_to_close=descriptor: os.close(descriptor_to_close),
            )
        for descriptor in reversed(opened_directory_fds):
            _v3_cleanup_attempt(
                cleanup_errors,
                lambda descriptor_to_close=descriptor: os.close(descriptor_to_close),
            )
        for descriptor in reversed(ancestor_fds):
            _v3_cleanup_attempt(
                cleanup_errors,
                lambda descriptor_to_close=descriptor: os.close(descriptor_to_close),
            )
        if project_fd >= 0:
            _v3_cleanup_attempt(cleanup_errors, lambda: os.close(project_fd))
        if cleanup_errors:
            raise cleanup_errors[0]


def _v3_archive_manifests(
    archive_root: Path,
) -> tuple[list[list[Any]], list[list[Any]], os.stat_result]:
    bound_root, file_tokens, directory_tokens, directory_fds = _v3_require_bound_archive()
    if bound_root != archive_root or "." not in directory_fds:
        raise WaveOneRoleBFullReaderError("failed V2 archive manifest binding root drifted")
    root_before = os.fstat(directory_fds["."])
    portable: list[list[Any]] = []
    live: list[list[Any]] = []
    for relative in sorted(set(directory_tokens) | set(file_tokens)):
        if relative == ".":
            continue
        directory = directory_tokens.get(relative)
        if directory is not None:
            portable.append(["d", relative, directory[2], directory[3]])
            live.append(
                [
                    "d",
                    relative,
                    directory[2],
                    directory[3],
                    directory[7],
                    directory[8],
                    directory[5],
                ]
            )
            continue
        expected = file_tokens[relative]
        path = archive_root / relative
        payload, stable = _v3_read_nofollow(path, f"failed V2 archive file {relative}")
        digest = sha256_bytes(payload)
        if expected[2] != stat.S_IMODE(stable.st_mode) or expected[3] != 1:
            raise WaveOneRoleBFullReaderError(
                "failed V2 archive file topology drifted during manifest replay"
            )
        portable.append(["f", relative, expected[2], expected[3], len(payload), digest])
        live.append(
            [
                "f",
                relative,
                expected[2],
                stable.st_nlink,
                len(payload),
                digest,
                stable.st_dev,
                stable.st_ino,
                stable.st_mtime_ns,
            ]
        )
    root_after = os.fstat(directory_fds["."])
    root_identity = lambda item: (  # noqa: E731 - compact immutable identity projection
        item.st_dev,
        item.st_ino,
        item.st_mode,
        item.st_nlink,
        item.st_size,
        item.st_mtime_ns,
    )
    if root_identity(root_before) != root_identity(root_after):
        raise WaveOneRoleBFullReaderError("failed V2 archive root changed during scan")
    return portable, live, root_after


def _v3_validate_historical_ledger(project_root: Path, control: dict[str, Any]) -> None:
    executor = control.get("executor_git")
    ledger = control.get("executor_implementation_ledger")
    if (
        not isinstance(executor, dict)
        or set(executor) != {"commit", "dirty"}
        or executor.get("commit") != FAILED_V2_PRODUCER_COMMIT
        or executor.get("dirty") is not False
        or not isinstance(ledger, dict)
        or set(ledger) != {"records", "sha256"}
        or ledger.get("sha256") != FAILED_V2_IMPLEMENTATION_LEDGER_SHA256
        or not isinstance(ledger.get("records"), list)
        or len(ledger["records"]) != 31
        or _canonical_sha256(ledger["records"]) != ledger["sha256"]
    ):
        raise WaveOneRoleBFullReaderError("failed V2 producer authority drifted")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", FAILED_V2_PRODUCER_COMMIT, "HEAD"],
        cwd=project_root,
        check=False,
        capture_output=True,
    )
    if ancestor.returncode != 0:
        raise WaveOneRoleBFullReaderError("failed V2 producer is not an ancestor")
    seen: set[str] = set()
    for record in ledger["records"]:
        if (
            not isinstance(record, dict)
            or set(record) != {"kind", "path", "phase", "sha256", "size_bytes"}
            or record.get("kind") != "IMPLEMENTATION"
            or record.get("phase") != "READ"
            or not isinstance(record.get("path"), str)
            or not _is_sha256(record.get("sha256"))
            or type(record.get("size_bytes")) is not int
            or record["size_bytes"] < 0
            or record["path"] in seen
        ):
            raise WaveOneRoleBFullReaderError("failed V2 implementation ledger drifted")
        relative = Path(record["path"])
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or relative.as_posix() != record["path"]
        ):
            raise WaveOneRoleBFullReaderError("failed V2 ledger path is unsafe")
        seen.add(record["path"])
        historical = _git_blob(project_root, FAILED_V2_PRODUCER_COMMIT, record["path"])
        current = _stable_bytes(
            _project_path(project_root, relative, "failed V2 implementation path"),
            "failed V2 implementation path",
        )
        if (
            len(historical) != record["size_bytes"]
            or sha256_bytes(historical) != record["sha256"]
            or current != historical
        ):
            raise WaveOneRoleBFullReaderError(
                "failed V2 historical implementation byte replay drifted"
            )


def _v3_authenticate_failed_archive(
    project_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], Path, dict[str, list[Any]]]:
    receipt_path = _project_path(
        project_root, FAILED_V2_RECEIPT_RELATIVE_PATH, "failed V2 incident receipt"
    )
    receipt_payload, receipt_stat = _v3_read_nofollow(receipt_path, "failed V2 incident receipt")
    if (
        len(receipt_payload) != FAILED_V2_RECEIPT_SIZE_BYTES
        or sha256_bytes(receipt_payload) != FAILED_V2_RECEIPT_SHA256
        or stat.S_IMODE(receipt_stat.st_mode) != 0o444
    ):
        raise WaveOneRoleBFullReaderError("failed V2 incident receipt identity drifted")
    receipt = _json_object(receipt_payload, "failed V2 incident receipt")
    if (
        receipt.get("format_version")
        != "BANK_CORPUS_WAVE_1_ROLE_B_FULL_V2_FAILED_NATIVE_ORDER_INCIDENT_V1"
        or receipt.get("status")
        != "IMMUTABLY_PRESERVED_FAILED_AFTER_COMPLETE_OCR_AND_THREE_NATIVE_CHECKPOINTS"
        or receipt.get("incident_identity_sha256") != FAILED_V2_INCIDENT_IDENTITY_SHA256
        or _canonical_sha256(
            {key: value for key, value in receipt.items() if key != "incident_identity_sha256"}
        )
        != FAILED_V2_INCIDENT_IDENTITY_SHA256
    ):
        raise WaveOneRoleBFullReaderError("failed V2 incident receipt logical identity drifted")
    archive = receipt.get("archive")
    authority = receipt.get("authority")
    accounting = receipt.get("accounting")
    execution_state = receipt.get("execution_state")
    safety = receipt.get("safety")
    if not all(
        isinstance(item, dict) for item in (archive, authority, accounting, execution_state, safety)
    ):
        raise WaveOneRoleBFullReaderError("failed V2 incident receipt sections drifted")
    required_receipt_facts = (
        archive.get("archived_relative_path") == FAILED_V2_ARCHIVE_RELATIVE_ROOT.as_posix()
        and archive.get("portable_manifest_sha256") == FAILED_V2_PORTABLE_MANIFEST_SHA256
        and archive.get("live_manifest_sha256") == FAILED_V2_LIVE_MANIFEST_SHA256
        and archive.get("record_count") == 8_658
        and archive.get("file_count") == 8_170
        and archive.get("directory_count") == 488
        and archive.get("logical_bytes") == 3_726_130_042
        and accounting.get("checkpoint_count") == 1_359
        and accounting.get("content_addressed_object_count") == 4_074
        and accounting.get("checkpoint_canonical_sha256_set_sha256")
        == FAILED_V2_CHECKPOINT_SET_SHA256
        and accounting.get("missing_request_count") == 90
        and accounting.get("missing_request_set_sha256") == FAILED_V2_MISSING_REQUEST_SET_SHA256
        and execution_state.get("full_reader_aggregate_present") is False
        and execution_state.get("document_indexes_present") is False
        and execution_state.get("supervisor_process_count") == 0
        and execution_state.get("worker_process_count") == 0
        and execution_state.get("held_execution_lease_count") == 0
        and execution_state.get("held_document_lock_count") == 0
        and safety.get("archive_bytes_modified") is False
        and safety.get("archive_entries_deleted") is False
        and safety.get("failed_native_objects_adopted_into_future_run") is False
        and authority.get("producer_git", {}).get("commit") == FAILED_V2_PRODUCER_COMMIT
        and authority.get("producer_git", {}).get("dirty") is False
        and authority.get("producer_implementation_ledger_sha256")
        == FAILED_V2_IMPLEMENTATION_LEDGER_SHA256
        and authority.get("producer_implementation_ledger_record_count") == 31
    )
    if not required_receipt_facts:
        raise WaveOneRoleBFullReaderError("failed V2 incident receipt facts drifted")
    archive_root = _project_path(
        project_root, FAILED_V2_ARCHIVE_RELATIVE_ROOT, "failed V2 archive root"
    )
    portable, live, root_stat = _v3_archive_manifests(archive_root)
    root_claim = archive.get("root_identity")
    if (
        not _same_typed_json(portable, archive.get("portable_manifest"))
        or not _same_typed_json(live, archive.get("live_manifest"))
        or _canonical_sha256(portable) != FAILED_V2_PORTABLE_MANIFEST_SHA256
        or _canonical_sha256(live) != FAILED_V2_LIVE_MANIFEST_SHA256
        or not isinstance(root_claim, dict)
        or root_claim
        != {
            "device": root_stat.st_dev,
            "inode": root_stat.st_ino,
            "link_count": root_stat.st_nlink,
            "mode": stat.S_IMODE(root_stat.st_mode),
            "mtime_ns": root_stat.st_mtime_ns,
            "size_bytes": root_stat.st_size,
        }
    ):
        raise WaveOneRoleBFullReaderError("failed V2 archive manifest replay drifted")
    manifest_index = {record[1]: record for record in live}
    control_payload, control_stat = _v3_read_nofollow(
        archive_root / "full-reader-execution-control.json", "failed V2 execution control"
    )
    if (
        len(control_payload) != FAILED_V2_CONTROL_SIZE_BYTES
        or sha256_bytes(control_payload) != FAILED_V2_CONTROL_SHA256
        or stat.S_IMODE(control_stat.st_mode) != 0o444
    ):
        raise WaveOneRoleBFullReaderError("failed V2 execution control artifact drifted")
    control = _json_object(control_payload, "failed V2 execution control")
    if (
        control.get("format_version") != "BANK_CORPUS_WAVE_1_ROLE_B_FULL_READER_CONTROL_V2"
        or control.get("status") != "READY_FOR_AUTHENTICATED_WAVE_1_FULL_PAGE_READ"
        or control.get("control_identity_sha256") != FAILED_V2_CONTROL_IDENTITY_SHA256
        or _canonical_sha256(
            {key: value for key, value in control.items() if key != "control_identity_sha256"}
        )
        != FAILED_V2_CONTROL_IDENTITY_SHA256
    ):
        raise WaveOneRoleBFullReaderError("failed V2 execution control logical identity drifted")
    _v3_validate_historical_ledger(project_root, control)
    return receipt, control, archive_root, manifest_index


def _v3_read_archive_ref(
    archive_root: Path,
    manifest_index: dict[str, list[Any]],
    reference: Any,
    suffix: str,
    label: str,
) -> tuple[bytes, os.stat_result]:
    if (
        not isinstance(reference, dict)
        or set(reference) != {"path", "sha256", "size_bytes"}
        or not _is_sha256(reference.get("sha256"))
        or type(reference.get("size_bytes")) is not int
        or reference["size_bytes"] < 0
    ):
        raise WaveOneRoleBFullReaderError(f"{label} reference fields drifted")
    expected_path = (
        Path("objects/sha256") / reference["sha256"][:2] / f"{reference['sha256']}{suffix}"
    ).as_posix()
    if reference["path"] != expected_path:
        raise WaveOneRoleBFullReaderError(f"{label} reference path drifted")
    manifest = manifest_index.get(expected_path)
    if (
        not isinstance(manifest, list)
        or len(manifest) != 9
        or manifest[0] != "f"
        or manifest[2] != 0o444
        or manifest[3] != 1
        or manifest[4] != reference["size_bytes"]
        or manifest[5] != reference["sha256"]
    ):
        raise WaveOneRoleBFullReaderError(f"{label} is not bound by the failed archive")
    payload, identity = _v3_read_nofollow(archive_root / expected_path, label)
    if (
        stat.S_IMODE(identity.st_mode) != 0o444
        or len(payload) != reference["size_bytes"]
        or sha256_bytes(payload) != reference["sha256"]
        or (identity.st_dev, identity.st_ino, identity.st_mtime_ns)
        != (manifest[6], manifest[7], manifest[8])
    ):
        raise WaveOneRoleBFullReaderError(f"{label} byte or topology identity drifted")
    return payload, identity


def _v3_historical_page_shape(record: Any, expected: dict[str, Any]) -> None:
    required = {
        "format_version",
        "request_ordinal",
        "document_id",
        "source_sha256",
        "source_size_bytes",
        "physical_page",
        "route",
        "request_sha256",
        "request",
        "status",
        "origin",
        "render_ref",
        "backend_payload_ref",
        "result_ref",
        "line_count",
        "word_token_count",
        "unresolved",
        "quarantined_span_count",
        "word_box_correction_count",
        "word_box_corrected_edge_count",
        *_ZERO_INTERPRETATION,
    }
    if not isinstance(record, dict) or set(record) != required:
        raise WaveOneRoleBFullReaderError("failed V2 page record fields drifted")
    for key in (
        "request_ordinal",
        "source_size_bytes",
        "physical_page",
        "line_count",
        "word_token_count",
        "quarantined_span_count",
        "word_box_correction_count",
        "word_box_corrected_edge_count",
        *_ZERO_INTERPRETATION,
    ):
        _validate_nonnegative_int(record[key], f"failed V2 page record {key}")
    if (
        record["format_version"] != "BANK_CORPUS_WAVE_1_ROLE_B_FULL_PAGE_RECORD_V1"
        or any(
            not _same_typed_json(record.get(key), expected.get(key))
            for key in (
                "request_ordinal",
                "document_id",
                "source_sha256",
                "source_size_bytes",
                "physical_page",
                "route",
                "request_sha256",
                "request",
            )
        )
        or any(record[key] != 0 for key in _ZERO_INTERPRETATION)
        or not isinstance(record["unresolved"], bool)
    ):
        raise WaveOneRoleBFullReaderError("failed V2 page request identity drifted")


def _v3_validate_historical_complete_ocr(
    v2_control: dict[str, Any],
    expected: dict[str, Any],
    record: dict[str, Any],
    render_payload: bytes,
    backend: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, int]:
    del render_payload  # its ref/hash/mode/topology were authenticated before this replay
    render_ref = record["render_ref"]
    if (
        set(backend)
        != {
            "format_version",
            "claim_boundary",
            "request_sha256",
            "request",
            "provider_identity_sha256",
            "render_ref",
            "raw_provider_payload",
            "word_box_normalization_ledger",
        }
        or backend.get("format_version") != "BANK_CORPUS_WAVE_1_PPOCRV6_BACKEND_PAYLOAD_V2"
        or backend.get("claim_boundary")
        != (
            "RAW_PINNED_PROVIDER_PAYLOAD_AND_BOUND_WORD_BOX_NORMALIZATION_LEDGER_"
            "FOR_ONE_EXACT_PAGE_REQUEST_ONLY"
        )
        or backend.get("request_sha256") != expected["request_sha256"]
        or not _same_typed_json(backend.get("request"), expected["request"])
        or not _same_typed_json(backend.get("render_ref"), render_ref)
        or backend.get("provider_identity_sha256")
        != expected["request"]["provider_identity_sha256"]
    ):
        raise WaveOneRoleBFullReaderError("failed V2 OCR backend identity drifted")
    result_keys = {
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
        "word_box_normalization_ledger",
        "coordinate_authority",
        "lines",
        "words",
        "metrics",
        "source_blank_claimed",
        "safety",
    }
    if (
        set(result) != result_keys
        or result.get("format_version") != "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V2"
        or result.get("status") != "OCR_WORD_BOX_READ_COMPLETE"
        or result.get("claim_boundary") != "SOURCE_VISIBLE_PAGE_TEXT_AND_GEOMETRY_EVIDENCE_ONLY"
        or result.get("request_sha256") != expected["request_sha256"]
        or not _same_typed_json(result.get("request"), expected["request"])
        or result.get("source_sha256") != expected["source_sha256"]
        or result.get("source_size_bytes") != expected["source_size_bytes"]
        or result.get("physical_page") != expected["physical_page"]
        or result.get("route") != _OCR_ROUTE
        or result.get("provider_identity_sha256") != expected["request"]["provider_identity_sha256"]
        or result.get("render_runtime_identity_sha256")
        != expected["request"]["render_runtime_identity_sha256"]
        or not _same_typed_json(result.get("input_render_ref"), render_ref)
        or not _same_typed_json(result.get("backend_payload_ref"), record["backend_payload_ref"])
        or result.get("source_blank_claimed") is not False
        or not _same_typed_json(result.get("safety"), _v2_result_safety())
    ):
        raise WaveOneRoleBFullReaderError("failed V2 OCR result identity drifted")
    dimensions = result.get("coordinate_authority", {}).get("pixel_dimensions")
    if (
        not isinstance(dimensions, list)
        or len(dimensions) != 2
        or any(type(value) is not int or value <= 0 for value in dimensions)
    ):
        raise WaveOneRoleBFullReaderError("failed V2 OCR pixel dimensions drifted")
    raw = backend.get("raw_provider_payload")
    if not isinstance(raw, dict):
        raise WaveOneRoleBFullReaderError("failed V2 OCR raw payload is absent")
    if record["origin"] == "AUTHENTICATED_SUCCESSFUL_SENTINEL_BYTE_COPY":
        authority = {
            "policy": WORD_BOX_NORMALIZATION_POLICY,
            "policy_sha256": ("cc7c35d71011541a207c4a6e0ff581142d218cc7392f1d7e7d33d4828a50891c"),
            "normalization_producer_implementation_ledger_sha256": (
                "4d704753e514f1ae6c9ca68628ccb462359089ada03385129629e69a882d442f"
            ),
            "control_identity_sha256": (
                "6bdc9e2285cf3af62c03a343b7f4e2ba5dc62a4ed4ee78c9d1fea3797ee2e472"
            ),
        }
    elif record["origin"] == "PINNED_PPOCRV6_FULL_READER":
        authority = _normalization_authority(v2_control)
    else:
        raise WaveOneRoleBFullReaderError("failed V2 OCR origin drifted")
    try:
        normalized, replay = normalize_ppocrv6_word_boxes(
            raw,
            pixel_width=dimensions[0],
            pixel_height=dimensions[1],
            authority=authority,
        )
    except WaveOneRoleBWordBoxNormalizationError as error:
        raise WaveOneRoleBFullReaderError("failed V2 complete OCR no longer normalizes") from error
    if not _same_typed_json(
        backend.get("word_box_normalization_ledger"), replay
    ) or not _same_typed_json(result.get("word_box_normalization_ledger"), replay):
        raise WaveOneRoleBFullReaderError("failed V2 normalization ledger replay drifted")
    counts = validate_ppocrv6_payload(
        normalized, pixel_width=dimensions[0], pixel_height=dimensions[1]
    )
    neutral = model_neutral_result_from_normalized_payload(
        normalized,
        coordinate_authority=_restore_in_memory_coordinate_authority(
            result["coordinate_authority"]
        ),
    )
    for key in ("status", "coordinate_authority", "lines", "words", "metrics"):
        if not _same_typed_json(result.get(key), neutral.get(key)):
            raise WaveOneRoleBFullReaderError("failed V2 OCR projection replay drifted")
    lines = result.get("lines")
    words = result.get("words")
    if not isinstance(lines, list) or not isinstance(words, list):
        raise WaveOneRoleBFullReaderError("failed V2 OCR projected axes drifted")
    nonempty_lines = sum(
        isinstance(line, dict) and isinstance(line.get("raw_text"), str) and line["raw_text"] != ""
        for line in lines
    )
    exact_empty_lines = sum(
        isinstance(line, dict) and isinstance(line.get("raw_text"), str) and line["raw_text"] == ""
        for line in lines
    )
    if (
        nonempty_lines + exact_empty_lines != len(lines)
        or any(
            not isinstance(word, dict)
            or not isinstance(word.get("raw_text"), str)
            or word["raw_text"] == ""
            for word in words
        )
        or counts["line_count"] != record["line_count"]
        or counts["word_token_count"] != record["word_token_count"]
        or replay["correction_count"] != record["word_box_correction_count"]
        or replay["corrected_edge_count"] != record["word_box_corrected_edge_count"]
    ):
        raise WaveOneRoleBFullReaderError("failed V2 OCR accounting drifted")
    return {
        "line_axis_count": len(lines),
        "nonempty_line_axis_count": nonempty_lines,
        "exact_empty_line_axis_count": exact_empty_lines,
        "word_token_count": len(words),
    }


def _v3_validate_historical_unresolved_ocr(
    v2_control: dict[str, Any],
    expected: dict[str, Any],
    record: dict[str, Any],
    backend: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, int]:
    if record["origin"] not in {
        "AUTHENTICATED_SUCCESSFUL_SENTINEL_BYTE_COPY",
        "PINNED_PPOCRV6_FULL_READER",
    }:
        raise WaveOneRoleBFullReaderError("failed V2 unresolved OCR origin drifted")
    backend_keys = {
        "format_version",
        "claim_boundary",
        "request_sha256",
        "request",
        "provider_identity_sha256",
        "render_ref",
        "raw_provider_payload",
        "word_box_normalization_ledger",
        "normalization_failure",
    }
    result_keys = {
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
        "normalization_failure",
        "coordinate_authority",
        "lines",
        "words",
        "metrics",
        "ocr_fallback_used",
        "source_blank_claimed",
        "safety",
    }
    if (
        set(backend) != backend_keys
        or backend.get("format_version") != "BANK_CORPUS_WAVE_1_PPOCRV6_BACKEND_PAYLOAD_V3"
        or backend.get("claim_boundary")
        != "RAW_PINNED_PROVIDER_PAYLOAD_WITH_TERMINAL_BOUNDED_WORD_BOX_GEOMETRY_FAILURE"
        or backend.get("request_sha256") != expected["request_sha256"]
        or not _same_typed_json(backend.get("request"), expected["request"])
        or not _same_typed_json(backend.get("render_ref"), record["render_ref"])
        or backend.get("provider_identity_sha256")
        != expected["request"]["provider_identity_sha256"]
        or backend.get("word_box_normalization_ledger") is not None
        or set(result) != result_keys
        or result.get("format_version") != "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V3"
        or result.get("status") != "UNRESOLVED_OCR_WORD_BOX_GEOMETRY"
        or result.get("claim_boundary")
        != "SOURCE_VISIBLE_PAGE_RAW_OCR_EVIDENCE_WITH_UNRESOLVED_GEOMETRY"
        or result.get("request_sha256") != expected["request_sha256"]
        or not _same_typed_json(result.get("request"), expected["request"])
        or result.get("source_sha256") != expected["source_sha256"]
        or result.get("source_size_bytes") != expected["source_size_bytes"]
        or result.get("physical_page") != expected["physical_page"]
        or result.get("route") != _OCR_ROUTE
        or result.get("provider_identity_sha256") != expected["request"]["provider_identity_sha256"]
        or result.get("render_runtime_identity_sha256")
        != expected["request"]["render_runtime_identity_sha256"]
        or not _same_typed_json(result.get("input_render_ref"), record["render_ref"])
        or not _same_typed_json(result.get("backend_payload_ref"), record["backend_payload_ref"])
        or not _same_typed_json(
            result.get("normalization_failure"), backend.get("normalization_failure")
        )
        or result.get("lines") != []
        or result.get("words") != []
        or result.get("metrics") != {"line_count": 0, "word_token_count": 0}
        or result.get("ocr_fallback_used") is not False
        or result.get("source_blank_claimed") is not False
        or not _same_typed_json(result.get("safety"), _v2_result_safety())
    ):
        raise WaveOneRoleBFullReaderError("failed V2 unresolved OCR envelope drifted")
    raw = backend.get("raw_provider_payload")
    dimensions = result.get("coordinate_authority", {}).get("pixel_dimensions")
    if (
        not isinstance(raw, dict)
        or not isinstance(dimensions, list)
        or len(dimensions) != 2
        or any(type(value) is not int or value <= 0 for value in dimensions)
    ):
        raise WaveOneRoleBFullReaderError("failed V2 unresolved OCR authority drifted")
    _validate_ppocrv6_schema_except_word_geometry(
        raw, pixel_width=dimensions[0], pixel_height=dimensions[1]
    )
    try:
        normalize_ppocrv6_word_boxes(
            raw,
            pixel_width=dimensions[0],
            pixel_height=dimensions[1],
            authority=_normalization_authority(v2_control),
        )
    except WaveOneRoleBWordBoxNormalizationError:
        pass
    else:
        raise WaveOneRoleBFullReaderError("failed V2 terminal OCR is now normalizable")
    expected_failure = {
        "format_version": "BANK_CORPUS_WAVE_1_PPOCRV6_NORMALIZATION_FAILURE_V1",
        "status": "UNRESOLVED_OCR_WORD_BOX_GEOMETRY",
        "reason": "BOUNDED_WORD_BOX_NORMALIZATION_INVARIANT_FAILED",
        "policy_sha256": v2_control["word_box_normalization"]["policy_sha256"],
        "control_identity_sha256": v2_control["control_identity_sha256"],
        "normalization_producer_implementation_ledger_sha256": v2_control["word_box_normalization"][
            "normalization_producer_implementation_ledger_sha256"
        ],
        "pixel_dimensions": dimensions,
        "raw_payload_sha256": _canonical_sha256(raw),
    }
    if not _same_typed_json(backend.get("normalization_failure"), expected_failure) or any(
        record[key] != 0
        for key in (
            "line_count",
            "word_token_count",
            "word_box_correction_count",
            "word_box_corrected_edge_count",
        )
    ):
        raise WaveOneRoleBFullReaderError("failed V2 unresolved OCR ledger drifted")
    return {
        "line_axis_count": 0,
        "nonempty_line_axis_count": 0,
        "exact_empty_line_axis_count": 0,
        "word_token_count": 0,
    }


def _v3_validate_historical_native_shape(
    archive_root: Path,
    manifest_index: dict[str, list[Any]],
    record: dict[str, Any],
) -> None:
    if (
        record["route"] != _NATIVE_ROUTE
        or record["origin"] != "SEALED_CAUSAL_NATIVE_TEXT_GATE"
        or record["status"]
        not in {
            "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
            "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY",
            "UNRESOLVED_NATIVE_TEXT_QUALITY",
        }
        or record["unresolved"] != (record["status"] != "CAUSAL_NATIVE_TEXT_READ_COMPLETE")
        or record["render_ref"] is not None
        or record["word_box_correction_count"] != 0
        or record["word_box_corrected_edge_count"] != 0
    ):
        raise WaveOneRoleBFullReaderError("failed V2 native checkpoint envelope drifted")
    backend_payload, _ = _v3_read_archive_ref(
        archive_root,
        manifest_index,
        record["backend_payload_ref"],
        ".json",
        "excluded failed V2 native backend",
    )
    result_payload, _ = _v3_read_archive_ref(
        archive_root,
        manifest_index,
        record["result_ref"],
        ".json",
        "excluded failed V2 native result",
    )
    backend = _json_object(backend_payload, "excluded failed V2 native backend")
    result = _json_object(result_payload, "excluded failed V2 native result")
    if (
        backend.get("format_version") != "BANK_CORPUS_WAVE_1_CAUSAL_NATIVE_BACKEND_PAYLOAD_V1"
        or result.get("format_version")
        != "BANK_CORPUS_WAVE_1_ROLE_B_CAUSAL_NATIVE_PAGE_READ_RESULT_V1"
        or result.get("request_sha256") != record["request_sha256"]
        or result.get("backend_payload_sha256") != record["backend_payload_ref"]["sha256"]
        or result.get("status") != record["status"]
    ):
        raise WaveOneRoleBFullReaderError("excluded failed V2 native evidence drifted")


def _v3_scan_failed_checkpoints(
    sealed: dict[str, Any],
    receipt: dict[str, Any],
    v2_control: dict[str, Any],
    archive_root: Path,
    manifest_index: dict[str, list[Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    expected_records = _full_request_records(sealed)
    expected_index = {record["request_sha256"]: record for record in expected_records}
    control_records = [
        page for document in v2_control.get("documents", []) for page in document.get("pages", [])
    ]
    if (
        len(control_records) != 1_449
        or len({record.get("request_sha256") for record in control_records}) != 1_449
        or any(
            not _same_typed_json(record, expected_index.get(record.get("request_sha256")))
            for record in control_records
        )
    ):
        raise WaveOneRoleBFullReaderError("failed V2 control request projection drifted")
    bound_root, _bound_files, bound_directories, _bound_fds = _v3_require_bound_archive()
    checkpoint_root = archive_root / "checkpoints"
    checkpoint_token = bound_directories.get("checkpoints")
    expected_checkpoint_documents = {
        item["document_id"].removeprefix("sha256:") for item in v2_control["documents"]
    }
    if (
        bound_root != archive_root
        or checkpoint_token is None
        or set(checkpoint_token[9]) != expected_checkpoint_documents
    ):
        raise WaveOneRoleBFullReaderError("failed V2 checkpoint root drifted")
    grammar = re.compile(r"^(?P<generation>[0-9]{4})-(?P<sha>[0-9a-f]{64})\.json$")
    checkpoint_hashes: list[str] = []
    seen_requests: set[str] = set()
    ocr_authorities: list[dict[str, Any]] = []
    excluded_native: list[dict[str, Any]] = []
    aggregate_metrics = Counter()
    for document in sorted(v2_control["documents"], key=lambda item: item["document_id"]):
        document_id = document["document_id"]
        directory = checkpoint_root / document_id.removeprefix("sha256:")
        directory_relative = (Path("checkpoints") / document_id.removeprefix("sha256:")).as_posix()
        directory_token = bound_directories.get(directory_relative)
        if directory_token is None:
            raise WaveOneRoleBFullReaderError("failed V2 document checkpoint directory drifted")
        names = directory_token[9]
        if any(grammar.fullmatch(name) is None for name in names):
            raise WaveOneRoleBFullReaderError("failed V2 checkpoint directory has foreign entry")
        order = _v2_document_completion_order(v2_control, document_id)
        previous = None
        for generation, name in enumerate(names, start=1):
            match = grammar.fullmatch(name)
            assert match is not None
            relative = (Path("checkpoints") / document_id.removeprefix("sha256:") / name).as_posix()
            manifest = manifest_index.get(relative)
            payload, identity = _v3_read_nofollow(directory / name, "failed V2 checkpoint")
            digest = sha256_bytes(payload)
            checkpoint = _json_object(payload, "failed V2 checkpoint")
            record = checkpoint.get("page_record")
            request_sha = record.get("request_sha256") if isinstance(record, dict) else None
            expected = expected_index.get(request_sha)
            if (
                not isinstance(manifest, list)
                or len(manifest) != 9
                or manifest[0] != "f"
                or manifest[2] != 0o444
                or manifest[3] != 1
                or manifest[4] != len(payload)
                or manifest[5] != digest
                or (manifest[6], manifest[7], manifest[8])
                != (identity.st_dev, identity.st_ino, identity.st_mtime_ns)
                or int(match.group("generation")) != generation
                or match.group("sha") != digest
                or expected is None
                or request_sha in seen_requests
                or generation > len(order)
                or request_sha != order[generation - 1]
                or not _same_typed_json(
                    checkpoint,
                    _v2_checkpoint_payload(v2_control, document_id, record, generation, previous),
                )
            ):
                raise WaveOneRoleBFullReaderError("failed V2 checkpoint chain drifted")
            _v3_historical_page_shape(record, expected)
            refs: dict[str, dict[str, Any]] = {}
            ref_payloads: dict[str, bytes] = {}
            ref_stats: dict[str, os.stat_result] = {}
            if record["route"] == _OCR_ROUTE:
                for key, suffix in (
                    ("render_ref", ".png"),
                    ("backend_payload_ref", ".json"),
                    ("result_ref", ".json"),
                ):
                    reference = record[key]
                    ref_payloads[key], ref_stats[key] = _v3_read_archive_ref(
                        archive_root,
                        manifest_index,
                        reference,
                        suffix,
                        f"failed V2 OCR {key}",
                    )
                    refs[key] = deepcopy(reference)
                backend = _json_object(ref_payloads["backend_payload_ref"], "failed V2 OCR backend")
                result = _json_object(ref_payloads["result_ref"], "failed V2 OCR result")
                if record["status"] == "OCR_WORD_BOX_READ_COMPLETE":
                    if record["unresolved"] is not False or record["quarantined_span_count"] != 0:
                        raise WaveOneRoleBFullReaderError("failed V2 complete OCR status drifted")
                    metrics = _v3_validate_historical_complete_ocr(
                        v2_control,
                        expected,
                        record,
                        ref_payloads["render_ref"],
                        backend,
                        result,
                    )
                    aggregate_metrics["complete_status_count"] += 1
                elif record["status"] == "UNRESOLVED_OCR_WORD_BOX_GEOMETRY":
                    if record["unresolved"] is not True or record["quarantined_span_count"] != 0:
                        raise WaveOneRoleBFullReaderError("failed V2 terminal OCR status drifted")
                    metrics = _v3_validate_historical_unresolved_ocr(
                        v2_control, expected, record, backend, result
                    )
                    aggregate_metrics["geometry_terminal_status_count"] += 1
                else:
                    raise WaveOneRoleBFullReaderError("failed V2 OCR status drifted")
                aggregate_metrics.update(metrics)
                aggregate_metrics["corrected_box_count"] += record["word_box_correction_count"]
                aggregate_metrics["corrected_edge_count"] += record["word_box_corrected_edge_count"]
                aggregate_metrics["corrected_page_count"] += int(
                    record["word_box_correction_count"] > 0
                )
                ocr_authorities.append(
                    {
                        "request": expected,
                        "source_checkpoint_sha256": digest,
                        "source_checkpoint_size_bytes": len(payload),
                        "source_checkpoint_generation": generation,
                        "source_page_record_sha256": _canonical_sha256(record),
                        "source_status": record["status"],
                        "source_origin": record["origin"],
                        "source_unresolved": record["unresolved"],
                        "source_refs": refs,
                        "source_ref_identities": {
                            key: {
                                "device": ref_stats[key].st_dev,
                                "inode": ref_stats[key].st_ino,
                                "mode": stat.S_IMODE(ref_stats[key].st_mode),
                                "link_count": ref_stats[key].st_nlink,
                                "size_bytes": ref_stats[key].st_size,
                                "mtime_ns": ref_stats[key].st_mtime_ns,
                            }
                            for key in refs
                        },
                        "metrics": metrics,
                        "word_box_correction_count": record["word_box_correction_count"],
                        "word_box_corrected_edge_count": record["word_box_corrected_edge_count"],
                    }
                )
            elif record["route"] == _NATIVE_ROUTE:
                _v3_validate_historical_native_shape(archive_root, manifest_index, record)
                excluded_native.append(
                    {
                        "request_sha256": request_sha,
                        "source_checkpoint_sha256": digest,
                        "source_page_record_sha256": _canonical_sha256(record),
                        "source_status": record["status"],
                    }
                )
            else:
                raise WaveOneRoleBFullReaderError("failed V2 checkpoint route drifted")
            seen_requests.add(request_sha)
            checkpoint_hashes.append(digest)
            previous = digest
    if (
        len(checkpoint_hashes) != 1_359
        or _canonical_sha256(sorted(checkpoint_hashes)) != FAILED_V2_CHECKPOINT_SET_SHA256
        or len(seen_requests) != 1_359
        or len(ocr_authorities) != 1_356
        or len(excluded_native) != 3
        or {item["request"]["request_sha256"] for item in ocr_authorities}
        != {item["request_sha256"] for item in expected_records if item["route"] == _OCR_ROUTE}
    ):
        raise WaveOneRoleBFullReaderError("failed V2 checkpoint route partition drifted")
    missing = sorted(set(expected_index) - seen_requests)
    if (
        len(missing) != 90
        or _canonical_sha256(missing) != FAILED_V2_MISSING_REQUEST_SET_SHA256
        or any(expected_index[item]["route"] != _NATIVE_ROUTE for item in missing)
    ):
        raise WaveOneRoleBFullReaderError("failed V2 missing native request set drifted")
    expected_metrics = {
        "complete_status_count": 1_299,
        "geometry_terminal_status_count": 57,
        "line_axis_count": 96_369,
        "nonempty_line_axis_count": 96_304,
        "exact_empty_line_axis_count": 65,
        "word_token_count": 1_313_842,
        "corrected_page_count": 20,
        "corrected_box_count": 22,
        "corrected_edge_count": 22,
    }
    if dict(aggregate_metrics) != expected_metrics:
        raise WaveOneRoleBFullReaderError("failed V2 OCR source accounting drifted")
    if receipt.get("accounting", {}).get("route_counts") != {
        _OCR_ROUTE: 1_356,
        _NATIVE_ROUTE: 3,
    }:
        raise WaveOneRoleBFullReaderError("failed V2 receipt route counts drifted")
    return (
        sorted(ocr_authorities, key=lambda item: item["request"]["request_ordinal"]),
        sorted(excluded_native, key=lambda item: item["request_sha256"]),
        expected_metrics,
    )


def _v3_authenticate_plan(
    project_root: Path,
    model_cache: Path,
    *,
    require_clean_executor: bool,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    project_root = project_root.resolve()
    policy = _v3_load_policy(project_root)
    try:
        sealed, _sentinel_policy, authority = sentinel._authenticate_sealed_plan(  # noqa: SLF001
            project_root,
            model_cache.resolve(),
            require_clean_executor=require_clean_executor,
        )
    except sentinel.WaveOneRoleBSentinelError as error:
        raise WaveOneRoleBFullReaderError(str(error)) from error
    anchors = {
        "route_plan_sha256": ("82b4b387754060419da37a1616336bf32d6a9248945cfc3974b936dbeace609d"),
        "input_ledger_sha256": ("7a83f8ff7fa007832578f586b01715a7023e21bc9bf9840f6d4cd301c4df927e"),
        "execution_plan_sha256": EXECUTION_PLAN_SHA256,
        "sentinel_sha256": SENTINEL_SHA256,
        "selection_receipt_sha256": SELECTION_RECEIPT_SHA256,
    }
    if any(sealed.get(key) != value for key, value in anchors.items()):
        raise WaveOneRoleBFullReaderError("V3 sealed plan anchor drifted")
    if (
        sealed.get("implementation_ledger", {}).get("sha256")
        != "694b44b5dfd56324473c85693b634710b910c95bf101d158aadac0a5076a4ec2"
        or sealed.get("ppocrv6_runtime_model_ledger", {}).get("sha256")
        != "58049a9bd187b2991716b6c2eac9d33679bb3785027a28dddd20a210e3ea234a"
        or sealed.get("render_runtime_ledger", {}).get("sha256")
        != "7850768660fa7aead1d83592e83cde09c8b52e480c5d33b73c40e7f3b837eb80"
        or sealed.get("causal_native_runtime_ledger", {}).get("sha256")
        != "57a50855a2669f07b0f9606a59de70f574615cdc490f7130f7bf2e2abce744e0"
    ):
        raise WaveOneRoleBFullReaderError("V3 sealed runtime ledger drifted")
    exact_plan = {
        "path": SEALED_PLAN_RELATIVE_PATH.as_posix(),
        "sha256": SEALED_PLAN_SHA256,
        "size_bytes": SEALED_PLAN_SIZE_BYTES,
        "producer_git_commit": PRODUCER_GIT_COMMIT,
        "execution_plan_sha256": EXECUTION_PLAN_SHA256,
        "route_plan_sha256": anchors["route_plan_sha256"],
        "input_ledger_sha256": anchors["input_ledger_sha256"],
        "implementation_ledger_sha256": sealed["implementation_ledger"]["sha256"],
        "ppocrv6_runtime_model_ledger_sha256": sealed["ppocrv6_runtime_model_ledger"]["sha256"],
        "render_runtime_ledger_sha256": sealed["render_runtime_ledger"]["sha256"],
        "causal_native_runtime_ledger_sha256": sealed["causal_native_runtime_ledger"]["sha256"],
        "sentinel_sha256": SENTINEL_SHA256,
        "selection_receipt_sha256": SELECTION_RECEIPT_SHA256,
    }
    if not _same_typed_json(policy.get("sealed_plan"), exact_plan):
        raise WaveOneRoleBFullReaderError("V3 policy sealed-plan projection drifted")
    ledger = _v3_implementation_ledger(project_root, authority["git"]["commit"])
    return sealed, policy, {"git": authority["git"], "implementation_ledger": ledger}


def _v3_documents(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["document_id"]].append(record)
    documents = []
    for document_id in sorted(grouped):
        pages = [
            {
                key: record[key]
                for key in (
                    "request_ordinal",
                    "document_id",
                    "source_sha256",
                    "source_size_bytes",
                    "physical_page",
                    "route",
                    "request_sha256",
                    "request",
                )
            }
            for record in sorted(grouped[document_id], key=lambda item: item["request_ordinal"])
        ]
        documents.append(
            {
                "document_id": document_id,
                "source_sha256": pages[0]["source_sha256"],
                "source_size_bytes": pages[0]["source_size_bytes"],
                "request_count": len(pages),
                "request_set_sha256": _canonical_sha256([page["request_sha256"] for page in pages]),
                "pages": pages,
            }
        )
    if len(documents) != 27 or sum(item["request_count"] for item in documents) != 1_449:
        raise WaveOneRoleBFullReaderError("V3 document request projection drifted")
    return documents


def _v3_build_authenticated_control_held(
    project_root: Path, *, model_cache: Path
) -> dict[str, Any]:
    """Build the exact V3 control without publishing or reading new native pages."""

    project_root = project_root.resolve()
    sealed, policy, executor = _v3_authenticate_plan(
        project_root, model_cache.resolve(), require_clean_executor=True
    )
    receipt, v2_control, archive_root, manifest_index = _v3_authenticate_failed_archive(
        project_root
    )
    ocr_authorities, excluded_native, ocr_metrics = _v3_scan_failed_checkpoints(
        sealed, receipt, v2_control, archive_root, manifest_index
    )
    records = _full_request_records(sealed)
    ocr_hashes = [item["request"]["request_sha256"] for item in ocr_authorities]
    excluded_hashes = sorted(item["request_sha256"] for item in excluded_native)
    native_identity = policy.get("native_reader", {}).get("native_ordering_policy_identity")
    if (
        not isinstance(native_identity, dict)
        or set(native_identity) != {"path", "sha256", "size_bytes"}
        or native_identity.get("path") != "config/ocr/causal-native-text-evidence-v2.yaml"
        or not _is_sha256(native_identity.get("sha256"))
        or type(native_identity.get("size_bytes")) is not int
        or native_identity["size_bytes"] <= 0
    ):
        raise WaveOneRoleBFullReaderError("V3 native ordering policy identity drifted")
    native_policy_bytes = _stable_bytes(
        _project_path(
            project_root,
            native_identity["path"],
            "V3 native ordering policy",
        ),
        "V3 native ordering policy",
    )
    if (
        len(native_policy_bytes) != native_identity["size_bytes"]
        or sha256_bytes(native_policy_bytes) != native_identity["sha256"]
    ):
        raise WaveOneRoleBFullReaderError("V3 native ordering policy bytes drifted")
    control = {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_FULL_READER_CONTROL_V3",
        "status": ("READY_FOR_AUTHENTICATED_FAILED_V2_OCR_ADOPTION_AND_FRESH_NATIVE_READS"),
        "claim_boundary": policy["claim_boundary"],
        "sealed_plan": policy["sealed_plan"],
        "executor_git": executor["git"],
        "executor_implementation_ledger": executor["implementation_ledger"],
        "failed_v2_authority": {
            "archive_root": FAILED_V2_ARCHIVE_RELATIVE_ROOT.as_posix(),
            "receipt": {
                "path": FAILED_V2_RECEIPT_RELATIVE_PATH.as_posix(),
                "sha256": FAILED_V2_RECEIPT_SHA256,
                "size_bytes": FAILED_V2_RECEIPT_SIZE_BYTES,
                "incident_identity_sha256": FAILED_V2_INCIDENT_IDENTITY_SHA256,
            },
            "archive_portable_manifest_sha256": FAILED_V2_PORTABLE_MANIFEST_SHA256,
            "archive_live_manifest_sha256": FAILED_V2_LIVE_MANIFEST_SHA256,
            "control_sha256": FAILED_V2_CONTROL_SHA256,
            "control_size_bytes": FAILED_V2_CONTROL_SIZE_BYTES,
            "control_identity_sha256": FAILED_V2_CONTROL_IDENTITY_SHA256,
            "producer_git_commit": FAILED_V2_PRODUCER_COMMIT,
            "producer_implementation_ledger_sha256": (FAILED_V2_IMPLEMENTATION_LEDGER_SHA256),
            "producer_implementation_ledger_record_count": 31,
            "checkpoint_count": 1_359,
            "checkpoint_canonical_sha256_set_sha256": FAILED_V2_CHECKPOINT_SET_SHA256,
            "selected_ocr_request_count": 1_356,
            "selected_ocr_request_set_sha256": _canonical_sha256(ocr_hashes),
            "excluded_native_checkpoint_count": 3,
            "excluded_native_request_set_sha256": _canonical_sha256(excluded_hashes),
            "copied_evidence_object_count": 4_068,
            "source_checkpoint_is_authority_only": True,
            "source_checkpoint_or_page_record_relabel_allowed": False,
            "copy_semantics": "BYTE_COPY_NEW_INODE_NO_HARDLINK_V1",
        },
        "ocr_adoption_accounting": deepcopy(ocr_metrics),
        "native_reader_contract": {
            "route": _NATIVE_ROUTE,
            "provider": "PYMUPDF_CAUSAL_NATIVE_TEXT_VISIBILITY_V1",
            "provider_runtime_ledger_sha256": sealed["causal_native_runtime_ledger"]["sha256"],
            "provider_runtime_ledger": deepcopy(sealed["causal_native_runtime_ledger"]),
            "evidence_adapter_path": ("src/bctc_ai/ocr/causal_native_text_evidence_v2.py"),
            "evidence_adapter_sha256": policy["native_reader"]["evidence_adapter_sha256"],
            "evidence_adapter_size_bytes": policy["native_reader"]["evidence_adapter_size_bytes"],
            "causal_policy_path": "config/ocr/causal-native-text-v1.yaml",
            "quality_policy_path": "config/ocr/native-text-quality-v2.yaml",
            "native_ordering_policy_identity": deepcopy(native_identity),
            "fresh_request_count": 93,
            "archived_native_adoption_allowed": False,
            "ocr_fallback_allowed": False,
            "network_allowed": False,
            "terminal_statuses": [
                "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
                "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY",
                "UNRESOLVED_NATIVE_TEXT_QUALITY",
                "UNRESOLVED_CAUSAL_NATIVE_LINE_CONTIGUITY",
            ],
        },
        "documents": _v3_documents(records),
        "accounting": {
            "document_count": 27,
            "request_count": 1_449,
            "ocr_request_count": 1_356,
            "native_request_count": 93,
            "required_ocr_adoption_count": 1_356,
            "required_fresh_native_read_count": 93,
            "required_ocr_object_copy_count": 4_068,
            "planned_final_object_count": 4_254,
            **_ZERO_INTERPRETATION,
        },
        "execution_contract": {
            "ocr_worker_allowed": False,
            "ocr_inference_allowed": False,
            "network_allowed": False,
            "checkpoint": "ONE_IMMUTABLE_CONSTANT_SIZE_CANONICAL_CHECKPOINT_PER_PAGE",
            "checkpoint_order": (
                "OCR_REQUEST_ORDINAL_ASC_THEN_NATIVE_REQUEST_ORDINAL_ASC_PER_DOCUMENT"
            ),
            "document_index": "DETERMINISTIC_FINAL_INDEX_AFTER_ALL_DOCUMENT_REQUESTS",
            "orphan_adoption": "FULL_V3_CONTROL_BOUND_REQUEST_IDENTITY_ONLY",
            "minimum_free_space_bytes": policy["execution"]["minimum_free_space_bytes"],
            "required_process_umask": policy["execution"]["required_process_umask"],
            "timestamps_in_deterministic_evidence": False,
        },
        "safety": {
            "source_locator_excluded_from_page_requests": True,
            "bank_registry_metadata_used": False,
            "filename_metadata_used": False,
            "role_a_used": False,
            "schema_used": False,
            "mapping_used": False,
            "historical_values_used": False,
            "semantic_interpretation_attempted": False,
            "absence_claimed": False,
            "source_visible_text_preserved_verbatim": True,
            "failed_v2_archive_mutated": False,
            "archived_native_evidence_adopted": False,
        },
    }
    control["control_identity_sha256"] = _canonical_sha256(control)
    return control


def build_authenticated_control(project_root: Path, *, model_cache: Path) -> dict[str, Any]:
    """Read-only authenticated control build while every failed-V2 lock is held."""

    project_root = project_root.resolve()
    sealed, _policy, _executor = _v3_authenticate_plan(
        project_root, model_cache.resolve(), require_clean_executor=True
    )
    document_ids = sorted(item["document_id"] for item in sealed["documents"])
    with _v3_failed_archive_locks(project_root, document_ids) as held:
        if len(held) != 28:
            raise WaveOneRoleBFullReaderError("failed V2 archive lock count drifted")
        return _v3_build_authenticated_control_held(project_root, model_cache=model_cache.resolve())


def _v3_control_index(control: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = [page for document in control["documents"] for page in document["pages"]]
    index = {record["request_sha256"]: record for record in records}
    if len(records) != 1_449 or len(index) != 1_449:
        raise WaveOneRoleBFullReaderError("V3 control request index drifted")
    return index


def _v3_copy_archive_object(
    project_root: Path,
    archive_root: Path,
    manifest_index: dict[str, list[Any]],
    reference: dict[str, Any],
    suffix: str,
    expected_source_identity: dict[str, Any],
) -> dict[str, Any]:
    payload, source_before = _v3_read_archive_ref(
        archive_root,
        manifest_index,
        reference,
        suffix,
        "failed V2 OCR source object",
    )
    source_projection = {
        "device": source_before.st_dev,
        "inode": source_before.st_ino,
        "mode": stat.S_IMODE(source_before.st_mode),
        "link_count": source_before.st_nlink,
        "size_bytes": source_before.st_size,
        "mtime_ns": source_before.st_mtime_ns,
    }
    if not _same_typed_json(source_projection, expected_source_identity):
        raise WaveOneRoleBFullReaderError("failed V2 source object identity changed")
    copied = _put_object(project_root, payload, suffix=suffix)
    if not _same_typed_json(copied, reference):
        raise WaveOneRoleBFullReaderError("V3 copied object content identity drifted")
    destination_path = _project_path(
        project_root,
        OUTPUT_RELATIVE_ROOT / copied["path"],
        "V3 copied evidence object",
    )
    destination_payload, destination = _v3_read_nofollow(
        destination_path, "V3 copied evidence object"
    )
    source_payload_after, source_after = _v3_read_archive_ref(
        archive_root,
        manifest_index,
        reference,
        suffix,
        "failed V2 OCR source object after copy",
    )
    if (
        destination_payload != payload
        or source_payload_after != payload
        or stat.S_IMODE(destination.st_mode) != 0o444
        or destination.st_nlink != 1
        or (destination.st_dev, destination.st_ino) == (source_before.st_dev, source_before.st_ino)
        or (
            source_after.st_dev,
            source_after.st_ino,
            stat.S_IMODE(source_after.st_mode),
            source_after.st_nlink,
            source_after.st_size,
            source_after.st_mtime_ns,
        )
        != (
            source_before.st_dev,
            source_before.st_ino,
            stat.S_IMODE(source_before.st_mode),
            source_before.st_nlink,
            source_before.st_size,
            source_before.st_mtime_ns,
        )
    ):
        raise WaveOneRoleBFullReaderError("V3 evidence byte-copy topology drifted")
    return copied


def _v3_ocr_page_record(
    control: dict[str, Any],
    authority: dict[str, Any],
    copied_refs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    expected = authority["request"]
    metrics = authority["metrics"]
    return {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_FULL_PAGE_RECORD_V2",
        **{
            key: deepcopy(expected[key])
            for key in (
                "request_ordinal",
                "document_id",
                "source_sha256",
                "source_size_bytes",
                "physical_page",
                "route",
                "request_sha256",
                "request",
            )
        },
        "status": authority["source_status"],
        "origin": "AUTHENTICATED_FAILED_V2_OCR_EVIDENCE_BYTE_COPY",
        "upstream_status": authority["source_status"],
        "upstream_origin": authority["source_origin"],
        "upstream_unresolved": authority["source_unresolved"],
        "render_ref": deepcopy(copied_refs["render_ref"]),
        "backend_payload_ref": deepcopy(copied_refs["backend_payload_ref"]),
        "result_ref": deepcopy(copied_refs["result_ref"]),
        "upstream_v2_adoption": {
            "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_FAILED_V2_OCR_ADOPTION_V1",
            "incident_identity_sha256": FAILED_V2_INCIDENT_IDENTITY_SHA256,
            "archive_portable_manifest_sha256": FAILED_V2_PORTABLE_MANIFEST_SHA256,
            "archive_live_manifest_sha256": FAILED_V2_LIVE_MANIFEST_SHA256,
            "source_control_identity_sha256": FAILED_V2_CONTROL_IDENTITY_SHA256,
            "source_checkpoint_sha256": authority["source_checkpoint_sha256"],
            "source_checkpoint_size_bytes": authority["source_checkpoint_size_bytes"],
            "source_checkpoint_generation": authority["source_checkpoint_generation"],
            "source_page_record_sha256": authority["source_page_record_sha256"],
            "source_status": authority["source_status"],
            "source_origin": authority["source_origin"],
            "source_unresolved": authority["source_unresolved"],
            "source_refs": deepcopy(authority["source_refs"]),
            "copy_semantics": "BYTE_COPY_NEW_INODE_NO_HARDLINK_V1",
            "source_checkpoint_or_page_record_relabelled": False,
            "destination_control_identity_sha256": control["control_identity_sha256"],
        },
        "line_axis_count": metrics["line_axis_count"],
        "nonempty_line_axis_count": metrics["nonempty_line_axis_count"],
        "exact_empty_line_axis_count": metrics["exact_empty_line_axis_count"],
        "accepted_line_count": metrics["nonempty_line_axis_count"],
        "word_token_count": metrics["word_token_count"],
        "unresolved": authority["source_unresolved"],
        "quarantined_span_count": 0,
        "ordering_quarantined_raw_line_run_count": 0,
        "ordering_quarantined_raw_word_count": 0,
        "noncontiguous_line_identity_count": 0,
        "word_box_correction_count": authority["word_box_correction_count"],
        "word_box_corrected_edge_count": authority["word_box_corrected_edge_count"],
        **_ZERO_INTERPRETATION,
    }


def _v3_native_page_record(
    control: dict[str, Any],
    expected: dict[str, Any],
    backend_ref: dict[str, Any],
    result_ref: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    metrics = result.get("metrics")
    if not isinstance(metrics, dict):
        raise WaveOneRoleBFullReaderError("V3 native result metrics are absent")
    status = result.get("status")
    complete = status == "CAUSAL_NATIVE_TEXT_READ_COMPLETE"
    expected_metric_keys = {
        "line_count",
        "word_token_count",
        "ghost_quarantined_span_count",
        "ordering_quarantined_raw_line_run_count",
        "ordering_quarantined_raw_word_count",
        "noncontiguous_line_identity_count",
    }
    if set(metrics) != expected_metric_keys:
        raise WaveOneRoleBFullReaderError("V3 native result metric fields drifted")
    line_count = metrics["line_count"]
    word_count = metrics["word_token_count"]
    quarantined = metrics["ghost_quarantined_span_count"]
    for value, label in (
        (line_count, "native accepted line count"),
        (word_count, "native accepted word count"),
        (quarantined, "native quarantine count"),
        (
            metrics["ordering_quarantined_raw_line_run_count"],
            "native ordering-quarantined line-run count",
        ),
        (
            metrics["ordering_quarantined_raw_word_count"],
            "native ordering-quarantined word count",
        ),
        (
            metrics["noncontiguous_line_identity_count"],
            "native noncontiguous-line identity count",
        ),
    ):
        _validate_nonnegative_int(value, label)
    return {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_FULL_PAGE_RECORD_V2",
        **{
            key: deepcopy(expected[key])
            for key in (
                "request_ordinal",
                "document_id",
                "source_sha256",
                "source_size_bytes",
                "physical_page",
                "route",
                "request_sha256",
                "request",
            )
        },
        "status": status,
        "origin": "FRESH_SEALED_CAUSAL_NATIVE_TEXT_GATE_V2",
        "upstream_status": None,
        "upstream_origin": None,
        "upstream_unresolved": None,
        "render_ref": None,
        "backend_payload_ref": deepcopy(backend_ref),
        "result_ref": deepcopy(result_ref),
        "upstream_v2_adoption": None,
        "line_axis_count": line_count,
        "nonempty_line_axis_count": line_count,
        "exact_empty_line_axis_count": 0,
        "accepted_line_count": line_count,
        "word_token_count": word_count,
        "unresolved": not complete,
        "quarantined_span_count": quarantined,
        "ordering_quarantined_raw_line_run_count": metrics[
            "ordering_quarantined_raw_line_run_count"
        ],
        "ordering_quarantined_raw_word_count": metrics["ordering_quarantined_raw_word_count"],
        "noncontiguous_line_identity_count": metrics["noncontiguous_line_identity_count"],
        "word_box_correction_count": 0,
        "word_box_corrected_edge_count": 0,
        **_ZERO_INTERPRETATION,
    }


def _v3_checkpoint_payload(
    control: dict[str, Any],
    document_id: str,
    record: dict[str, Any],
    generation: int,
    previous_sha256: str | None,
) -> dict[str, Any]:
    return {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_FULL_PAGE_DELTA_CHECKPOINT_V2",
        "status": "COMPLETE_ONE_AUTHENTICATED_V3_PAGE_REQUEST",
        "claim_boundary": "ONE_EXACT_SEALED_PAGE_REQUEST_ACCOUNTING_ONLY",
        "sealed_plan_sha256": SEALED_PLAN_SHA256,
        "control_identity_sha256": control["control_identity_sha256"],
        "document_id": document_id,
        "source_sha256": document_id.removeprefix("sha256:"),
        "generation": generation,
        "previous_checkpoint_sha256": previous_sha256,
        "page_record": record,
    }


def _v3_document_completion_order(control: dict[str, Any], document_id: str) -> list[str]:
    matches = [
        document for document in control["documents"] if document["document_id"] == document_id
    ]
    if len(matches) != 1:
        raise WaveOneRoleBFullReaderError("V3 completion-order document drifted")
    pages = matches[0]["pages"]
    ordered = [
        page["request_sha256"]
        for route in (_OCR_ROUTE, _NATIVE_ROUTE)
        for page in sorted(
            (item for item in pages if item["route"] == route),
            key=lambda item: item["request_ordinal"],
        )
    ]
    if len(ordered) != len(pages) or len(set(ordered)) != len(pages):
        raise WaveOneRoleBFullReaderError("V3 completion order drifted")
    return ordered


def _v3_publish_checkpoint(
    project_root: Path,
    control: dict[str, Any],
    document_id: str,
    record: dict[str, Any],
    generation: int,
    previous_sha256: str | None,
) -> str:
    checkpoint = _v3_checkpoint_payload(control, document_id, record, generation, previous_sha256)
    payload = _canonical_bytes(checkpoint)
    digest = sha256_bytes(payload)
    directory = OUTPUT_RELATIVE_ROOT / "checkpoints" / document_id.removeprefix("sha256:")
    filename = f"{generation:04d}-{digest}.json"
    _v3_recover_publication_directory(
        project_root,
        directory,
        create=True,
        allowed_final=lambda candidate: candidate == filename,
        validate_payload=lambda candidate, candidate_payload: (
            candidate == filename and candidate_payload == payload
        ),
    )
    _publish_exclusive(
        project_root,
        directory,
        filename,
        payload,
    )
    return digest


def _v3_read_object(
    project_root: Path,
    reference: Any,
    suffix: str,
    label: str,
    *,
    publication_pair_path: str | None = None,
) -> tuple[bytes, os.stat_result]:
    if (
        not isinstance(reference, dict)
        or set(reference) != {"path", "sha256", "size_bytes"}
        or not _is_sha256(reference.get("sha256"))
        or type(reference.get("size_bytes")) is not int
        or reference["size_bytes"] < 0
        or reference.get("path")
        != (
            Path("objects/sha256") / reference["sha256"][:2] / f"{reference['sha256']}{suffix}"
        ).as_posix()
    ):
        raise WaveOneRoleBFullReaderError(f"{label} reference drifted")
    path = _project_path(project_root, OUTPUT_RELATIVE_ROOT / reference["path"], label)
    payload, identity = _v3_read_nofollow(
        path,
        label,
        expected_nlink=(2 if reference["path"] == publication_pair_path else 1),
    )
    if (
        stat.S_IMODE(identity.st_mode) != 0o444
        or identity.st_nlink != (2 if reference["path"] == publication_pair_path else 1)
        or len(payload) != reference["size_bytes"]
        or sha256_bytes(payload) != reference["sha256"]
    ):
        raise WaveOneRoleBFullReaderError(f"{label} object identity drifted")
    return payload, identity


def _v3_validate_ocr_page_record(
    project_root: Path,
    control: dict[str, Any],
    record: dict[str, Any],
    authority: dict[str, Any],
    archive_root: Path,
    manifest_index: dict[str, list[Any]],
    *,
    publication_pair_path: str | None = None,
) -> None:
    expected_record = _v3_ocr_page_record(
        control,
        authority,
        {
            key: deepcopy(authority["source_refs"][key])
            for key in ("render_ref", "backend_payload_ref", "result_ref")
        },
    )
    if not _same_typed_json(record, expected_record):
        raise WaveOneRoleBFullReaderError("V3 OCR adoption record drifted")
    destination_inodes: set[tuple[int, int]] = set()
    for key, suffix in (
        ("render_ref", ".png"),
        ("backend_payload_ref", ".json"),
        ("result_ref", ".json"),
    ):
        destination_payload, destination = _v3_read_object(
            project_root,
            record[key],
            suffix,
            f"V3 OCR {key}",
            publication_pair_path=publication_pair_path,
        )
        source_payload, source = _v3_read_archive_ref(
            archive_root,
            manifest_index,
            authority["source_refs"][key],
            suffix,
            f"failed V2 OCR {key} replay",
        )
        if (
            destination_payload != source_payload
            or (destination.st_dev, destination.st_ino) == (source.st_dev, source.st_ino)
            or (destination.st_dev, destination.st_ino) in destination_inodes
        ):
            raise WaveOneRoleBFullReaderError("V3 OCR copy identity or inode drifted")
        destination_inodes.add((destination.st_dev, destination.st_ino))


def _v3_validate_native_page_record_shape(
    project_root: Path,
    control: dict[str, Any],
    record: dict[str, Any],
    *,
    publication_pair_path: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    backend_payload, _ = _v3_read_object(
        project_root,
        record.get("backend_payload_ref"),
        ".json",
        "V3 native backend",
        publication_pair_path=publication_pair_path,
    )
    result_payload, _ = _v3_read_object(
        project_root,
        record.get("result_ref"),
        ".json",
        "V3 native result",
        publication_pair_path=publication_pair_path,
    )
    backend = _json_object(backend_payload, "V3 native backend")
    result = _json_object(result_payload, "V3 native result")
    expected = _v3_control_index(control).get(record.get("request_sha256"))
    if expected is None:
        raise WaveOneRoleBFullReaderError("V3 native request is foreign")
    backend_hash = record["backend_payload_ref"]["sha256"]
    expected_record = _v3_native_page_record(
        control, expected, record["backend_payload_ref"], record["result_ref"], result
    )
    if (
        not _same_typed_json(record, expected_record)
        or result.get("backend_payload_sha256") != backend_hash
    ):
        raise WaveOneRoleBFullReaderError("V3 native evidence envelope drifted")
    try:
        validate_causal_native_text_evidence_v2_envelopes(
            request=expected["request"],
            request_sha256=expected["request_sha256"],
            document_id=expected["document_id"],
            source_sha256=expected["source_sha256"],
            source_size_bytes=expected["source_size_bytes"],
            physical_page=expected["physical_page"],
            provider_runtime_ledger=control["native_reader_contract"]["provider_runtime_ledger"],
            native_ordering_policy_identity=control["native_reader_contract"][
                "native_ordering_policy_identity"
            ],
            full_control_identity_sha256=control["control_identity_sha256"],
            backend=backend,
            result=result,
        )
    except CausalNativeTextEvidenceError as error:
        raise WaveOneRoleBFullReaderError("V3 native evidence envelope drifted") from error
    return backend, result


def _v3_validate_page_record(
    project_root: Path,
    control: dict[str, Any],
    record: Any,
    expected: dict[str, Any],
    ocr_authority_index: dict[str, dict[str, Any]],
    archive_root: Path,
    manifest_index: dict[str, list[Any]],
    *,
    publication_pair_path: str | None = None,
) -> None:
    required = {
        "format_version",
        "request_ordinal",
        "document_id",
        "source_sha256",
        "source_size_bytes",
        "physical_page",
        "route",
        "request_sha256",
        "request",
        "status",
        "origin",
        "upstream_status",
        "upstream_origin",
        "upstream_unresolved",
        "render_ref",
        "backend_payload_ref",
        "result_ref",
        "upstream_v2_adoption",
        "line_axis_count",
        "nonempty_line_axis_count",
        "exact_empty_line_axis_count",
        "accepted_line_count",
        "word_token_count",
        "unresolved",
        "quarantined_span_count",
        "ordering_quarantined_raw_line_run_count",
        "ordering_quarantined_raw_word_count",
        "noncontiguous_line_identity_count",
        "word_box_correction_count",
        "word_box_corrected_edge_count",
        *_ZERO_INTERPRETATION,
    }
    if not isinstance(record, dict) or set(record) != required:
        raise WaveOneRoleBFullReaderError("V3 page record fields drifted")
    for key in (
        "request_ordinal",
        "source_size_bytes",
        "physical_page",
        "line_axis_count",
        "nonempty_line_axis_count",
        "exact_empty_line_axis_count",
        "accepted_line_count",
        "word_token_count",
        "quarantined_span_count",
        "ordering_quarantined_raw_line_run_count",
        "ordering_quarantined_raw_word_count",
        "noncontiguous_line_identity_count",
        "word_box_correction_count",
        "word_box_corrected_edge_count",
        *_ZERO_INTERPRETATION,
    ):
        _validate_nonnegative_int(record[key], f"V3 page record {key}")
    if (
        record["format_version"] != "BANK_CORPUS_WAVE_1_ROLE_B_FULL_PAGE_RECORD_V2"
        or any(
            not _same_typed_json(record.get(key), expected.get(key))
            for key in (
                "request_ordinal",
                "document_id",
                "source_sha256",
                "source_size_bytes",
                "physical_page",
                "route",
                "request_sha256",
                "request",
            )
        )
        or record["line_axis_count"]
        != record["nonempty_line_axis_count"] + record["exact_empty_line_axis_count"]
        or record["accepted_line_count"] != record["nonempty_line_axis_count"]
        or any(record[key] != 0 for key in _ZERO_INTERPRETATION)
        or not isinstance(record["unresolved"], bool)
    ):
        raise WaveOneRoleBFullReaderError("V3 page record identity or accounting drifted")
    if record["route"] == _OCR_ROUTE:
        authority = ocr_authority_index.get(record["request_sha256"])
        if authority is None:
            raise WaveOneRoleBFullReaderError("V3 OCR adoption lacks historical authority")
        _v3_validate_ocr_page_record(
            project_root,
            control,
            record,
            authority,
            archive_root,
            manifest_index,
            publication_pair_path=publication_pair_path,
        )
    elif record["route"] == _NATIVE_ROUTE:
        if record["request_sha256"] in ocr_authority_index:
            raise WaveOneRoleBFullReaderError("V3 native record crossed OCR authority")
        _v3_validate_native_page_record_shape(
            project_root,
            control,
            record,
            publication_pair_path=publication_pair_path,
        )
    else:
        raise WaveOneRoleBFullReaderError("V3 page route drifted")


def _v3_load_document_checkpoints(
    project_root: Path,
    control: dict[str, Any],
    document_id: str,
    ocr_authority_index: dict[str, dict[str, Any]],
    archive_root: Path,
    manifest_index: dict[str, list[Any]],
    *,
    recover_temporaries: bool,
    publication_pair_path: str | None = None,
    expected_output_manifest: list[list[Any]] | None = None,
    observe_temporary: bool = False,
) -> tuple[list[dict[str, Any]], str | None]:
    relative = OUTPUT_RELATIVE_ROOT / "checkpoints" / document_id.removeprefix("sha256:")
    directory_path = project_root / relative
    bound, bound_directory_fd = _v3_bound_output_directory(directory_path)
    context = None
    if bound:
        if bound_directory_fd is None:
            return [], None
        directory_fd = bound_directory_fd
    else:
        try:
            context = _v3_held_output_directory(project_root, relative, create=False)
            _directory, directory_fd = context.__enter__()
        except WaveOneRoleBFullReaderError as error:
            if "is absent" in str(error):
                return [], None
            raise
    try:
        grammar = re.compile(r"^(?P<generation>[0-9]{4})-(?P<sha>[0-9a-f]{64})\.json$")
        interrupted = re.compile(r"^\.[0-9]{4}-[0-9a-f]{64}\.json\.[0-9a-f]{32}\.tmp$")
        names = []
        temporary_names = []
        for name in sorted(os.listdir(directory_fd)):
            if interrupted.fullmatch(name):
                if not recover_temporaries and not observe_temporary:
                    raise WaveOneRoleBFullReaderError("V3 checkpoint publication is incomplete")
                temporary_names.append(name)
                continue
            if grammar.fullmatch(name) is None:
                raise WaveOneRoleBFullReaderError(
                    "V3 checkpoint directory contains a foreign entry"
                )
            names.append(name)
        if len(temporary_names) > 1:
            raise WaveOneRoleBFullReaderError("V3 checkpoint directory has multiple temporaries")
        paired_final_name = None
        if temporary_names:
            temporary_match = re.fullmatch(
                r"^\.(?P<final>[0-9]{4}-[0-9a-f]{64}\.json)\."
                r"[0-9a-f]{32}\.tmp$",
                temporary_names[0],
            )
            assert temporary_match is not None
            candidate_name = temporary_match.group("final")
            if candidate_name in names:
                temporary_identity = os.stat(
                    temporary_names[0],
                    dir_fd=directory_fd,
                    follow_symlinks=False,
                )
                final_identity = os.stat(
                    candidate_name,
                    dir_fd=directory_fd,
                    follow_symlinks=False,
                )
                if (
                    not stat.S_ISREG(temporary_identity.st_mode)
                    or not stat.S_ISREG(final_identity.st_mode)
                    or stat.S_IMODE(temporary_identity.st_mode) != 0o444
                    or stat.S_IMODE(final_identity.st_mode) != 0o444
                    or temporary_identity.st_nlink != 2
                    or final_identity.st_nlink != 2
                    or (
                        temporary_identity.st_dev,
                        temporary_identity.st_ino,
                        temporary_identity.st_size,
                        temporary_identity.st_mtime_ns,
                        temporary_identity.st_ctime_ns,
                    )
                    != (
                        final_identity.st_dev,
                        final_identity.st_ino,
                        final_identity.st_size,
                        final_identity.st_mtime_ns,
                        final_identity.st_ctime_ns,
                    )
                ):
                    raise WaveOneRoleBFullReaderError(
                        "V3 linked checkpoint publication topology drifted"
                    )
                paired_final_name = candidate_name
        expected_index = _v3_control_index(control)
        order = _v3_document_completion_order(control, document_id)
        records: list[dict[str, Any]] = []
        previous = None
        seen: set[str] = set()
        validated_payloads: dict[str, bytes] = {}
        for generation, name in enumerate(names, start=1):
            match = grammar.fullmatch(name)
            assert match is not None
            payload, identity = _v3_read_nofollow(
                directory_path / name,
                "V3 page checkpoint",
                expected_nlink=(2 if name == paired_final_name else 1),
            )
            digest = sha256_bytes(payload)
            checkpoint = _json_object(payload, "V3 page checkpoint")
            record = checkpoint.get("page_record")
            request_sha = record.get("request_sha256") if isinstance(record, dict) else None
            expected = expected_index.get(request_sha)
            if (
                int(match.group("generation")) != generation
                or match.group("sha") != digest
                or stat.S_IMODE(identity.st_mode) != 0o444
                or identity.st_nlink != (2 if name == paired_final_name else 1)
                or expected is None
                or request_sha in seen
                or generation > len(order)
                or request_sha != order[generation - 1]
                or not _same_typed_json(
                    checkpoint,
                    _v3_checkpoint_payload(control, document_id, record, generation, previous),
                )
            ):
                raise WaveOneRoleBFullReaderError("V3 checkpoint chain drifted")
            _v3_validate_page_record(
                project_root,
                control,
                record,
                expected,
                ocr_authority_index,
                archive_root,
                manifest_index,
                publication_pair_path=publication_pair_path,
            )
            records.append(record)
            seen.add(request_sha)
            previous = digest
            validated_payloads[name] = payload
        if temporary_names:
            temporary_match = re.fullmatch(
                r"^\.(?P<final>[0-9]{4}-[0-9a-f]{64}\.json)\.[0-9a-f]{32}\.tmp$",
                temporary_names[0],
            )
            assert temporary_match is not None
            candidate_final = temporary_match.group("final")
            candidate_match = grammar.fullmatch(candidate_final)
            assert candidate_match is not None

            def candidate_allowed(name: str) -> bool:
                if name != candidate_final:
                    return False
                if name in validated_payloads:
                    return True
                return int(candidate_match.group("generation")) == len(records) + 1

            def candidate_valid(name: str, payload: bytes) -> bool:
                if name in validated_payloads:
                    return payload == validated_payloads[name]
                if (
                    sha256_bytes(payload) != candidate_match.group("sha")
                    or int(candidate_match.group("generation")) != len(records) + 1
                ):
                    return False
                try:
                    checkpoint = _json_object(payload, "V3 interrupted checkpoint")
                    record = checkpoint.get("page_record")
                    if (
                        not isinstance(record, dict)
                        or len(records) >= len(order)
                        or record.get("request_sha256") != order[len(records)]
                        or not _same_typed_json(
                            checkpoint,
                            _v3_checkpoint_payload(
                                control,
                                document_id,
                                record,
                                len(records) + 1,
                                previous,
                            ),
                        )
                    ):
                        return False
                    expected = expected_index.get(record["request_sha256"])
                    if expected is None:
                        return False
                    _v3_validate_page_record(
                        project_root,
                        control,
                        record,
                        expected,
                        ocr_authority_index,
                        archive_root,
                        manifest_index,
                        publication_pair_path=publication_pair_path,
                    )
                except WaveOneRoleBFullReaderError:
                    return False
                return True

            _v3_recover_publication_directory(
                project_root,
                relative,
                create=False,
                allowed_final=candidate_allowed,
                validate_payload=candidate_valid,
                expected_output_manifest=expected_output_manifest,
            ) if recover_temporaries else None
            if observe_temporary:
                temporary_payload, temporary_identity = _v3_read_nofollow(
                    directory_path / temporary_names[0],
                    "V3 checkpoint publication temporary",
                    expected_nlink=(2 if paired_final_name is not None else 1),
                )
                if (
                    stat.S_IMODE(temporary_identity.st_mode) not in {0o600, 0o444}
                    or temporary_identity.st_nlink not in {1, 2}
                    or (
                        temporary_identity.st_nlink == 2
                        and not candidate_valid(candidate_final, temporary_payload)
                    )
                ):
                    raise WaveOneRoleBFullReaderError("V3 observed checkpoint temporary drifted")
                return records, previous
            return records, previous
        return records, previous
    finally:
        if context is not None:
            context.__exit__(None, None, None)


def _v3_append_checkpoint(
    project_root: Path,
    control: dict[str, Any],
    records_by_document: dict[str, list[dict[str, Any]]],
    heads_by_document: dict[str, str | None],
    record: dict[str, Any],
    ocr_authority_index: dict[str, dict[str, Any]],
    archive_root: Path,
    manifest_index: dict[str, list[Any]],
) -> None:
    document_id = record["document_id"]
    records = records_by_document[document_id]
    if any(item["request_sha256"] == record["request_sha256"] for item in records):
        raise WaveOneRoleBFullReaderError("V3 page request is already checkpointed")
    order = _v3_document_completion_order(control, document_id)
    if len(records) >= len(order) or record["request_sha256"] != order[len(records)]:
        raise WaveOneRoleBFullReaderError("V3 checkpoint violates deterministic per-document order")
    expected = _v3_control_index(control)[record["request_sha256"]]
    _v3_validate_page_record(
        project_root,
        control,
        record,
        expected,
        ocr_authority_index,
        archive_root,
        manifest_index,
    )
    head = _v3_publish_checkpoint(
        project_root,
        control,
        document_id,
        record,
        len(records) + 1,
        heads_by_document[document_id],
    )
    records.append(record)
    heads_by_document[document_id] = head


def _v3_lock_identity(
    descriptor: int, directory_fd: int, name: str, *, mode: int
) -> tuple[int, int]:
    opened = os.fstat(descriptor)
    named = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    if (
        not stat.S_ISREG(opened.st_mode)
        or stat.S_IMODE(opened.st_mode) != mode
        or opened.st_nlink != 1
        or opened.st_size != 0
        or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
    ):
        raise WaveOneRoleBFullReaderError("V3 lock identity drifted")
    return opened.st_dev, opened.st_ino


def _v3_read_process_umask() -> str:
    path = Path("/proc/self/status")
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
    except OSError as error:
        raise WaveOneRoleBFullReaderError("V3 process umask authority cannot be opened") from error
    try:
        before = os.fstat(descriptor)
        chunks = []
        while chunk := os.read(descriptor, 64 * 1024):
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if not stat.S_ISREG(before.st_mode) or (before.st_dev, before.st_ino, before.st_mode) != (
        after.st_dev,
        after.st_ino,
        after.st_mode,
    ):
        raise WaveOneRoleBFullReaderError("V3 process umask authority drifted")
    try:
        text = b"".join(chunks).decode("ascii")
    except UnicodeDecodeError as error:
        raise WaveOneRoleBFullReaderError("V3 process umask authority is not ASCII") from error
    matches = re.findall(r"(?m)^Umask:\s*([0-7]{4})\s*$", text)
    if len(matches) != 1:
        raise WaveOneRoleBFullReaderError("V3 process umask authority is malformed")
    return matches[0]


@contextmanager
def _v3_mutation_entry() -> Iterator[None]:
    with _V3_MUTATION_LOCK:
        if _v3_read_process_umask() != "0022":
            raise WaveOneRoleBFullReaderError("V3 mutating commands require process umask 0022")
        yield


def _v3_assert_output_mutation_ancestry(project_root: Path, label: str) -> None:
    binding = _V3_OUTPUT_MUTATION_BINDING.get()
    if binding is None:
        return
    (
        bound_project_root,
        parent_fd,
        root_fd,
        lock_fd,
        expected_root,
        expected_locks,
    ) = binding
    if bound_project_root != project_root:
        raise WaveOneRoleBFullReaderError(f"{label} project root binding drifted")

    def identity(item: os.stat_result) -> tuple[int, ...]:
        return item.st_dev, item.st_ino, item.st_mode

    root_opened = os.fstat(root_fd)
    root_named = os.stat(
        OUTPUT_RELATIVE_ROOT.name,
        dir_fd=parent_fd,
        follow_symlinks=False,
    )
    locks_opened = os.fstat(lock_fd)
    locks_named = os.stat("locks", dir_fd=root_fd, follow_symlinks=False)
    absolute_root = os.stat(project_root / OUTPUT_RELATIVE_ROOT, follow_symlinks=False)
    absolute_locks = os.stat(project_root / OUTPUT_RELATIVE_ROOT / "locks", follow_symlinks=False)
    if (
        not stat.S_ISDIR(root_opened.st_mode)
        or not stat.S_ISDIR(locks_opened.st_mode)
        or identity(root_opened) != expected_root
        or identity(root_named) != expected_root
        or identity(absolute_root) != expected_root
        or identity(locks_opened) != expected_locks
        or identity(locks_named) != expected_locks
        or identity(absolute_locks) != expected_locks
    ):
        raise WaveOneRoleBFullReaderError(f"{label} output ancestry generation drifted")


@contextmanager
def _v3_execution_lease(project_root: Path, *, create: bool) -> Iterator[int]:
    shared_parent = _V3_SHARED_OUTPUT_PARENT_BINDING.get()
    parent = project_root / OUTPUT_RELATIVE_ROOT.parent
    if shared_parent is None:
        parent = _project_path(
            project_root, OUTPUT_RELATIVE_ROOT.parent, "V3 output bootstrap parent"
        )
    elif shared_parent[0] != project_root:
        raise WaveOneRoleBFullReaderError(
            "V3 output bootstrap shared parent project binding drifted"
        )
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    parent_fd = root_fd = directory_fd = descriptor = -1
    parent_locked = root_locked = lease_locked = False
    created_root = created_locks = created_lease = False
    identity = None
    root_generation = None
    lock_generation = None
    owned_root_generation = None
    owned_lock_generation = None
    owned_lease_identity = None
    mutation_binding_token = None
    control_marker_token = None

    def directory_identity(item: os.stat_result) -> tuple[int, ...]:
        return (
            item.st_dev,
            item.st_ino,
            item.st_mode,
        )

    def checked_directory(
        descriptor_to_check: int,
        parent_descriptor: int,
        name: str,
        label: str,
    ) -> tuple[int, ...]:
        opened = os.fstat(descriptor_to_check)
        named = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
        if (
            not stat.S_ISDIR(opened.st_mode)
            or stat.S_IMODE(opened.st_mode) != 0o755
            or directory_identity(opened) != directory_identity(named)
        ):
            raise WaveOneRoleBFullReaderError(f"{label} topology drifted")
        return directory_identity(opened)

    def capture_owned_directory(
        parent_descriptor: int,
        name: str,
        label: str,
    ) -> tuple[int, ...]:
        observed = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
        if not stat.S_ISDIR(observed.st_mode) or stat.S_IMODE(observed.st_mode) != 0o755:
            raise WaveOneRoleBFullReaderError(f"{label} creation topology drifted")
        return directory_identity(observed)

    def capture_owned_lease(
        lease_descriptor: int,
        lock_descriptor: int,
    ) -> tuple[int, int]:
        opened = os.fstat(lease_descriptor)
        named = os.stat(
            "full-reader-execution.lease",
            dir_fd=lock_descriptor,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISREG(opened.st_mode)
            or stat.S_IMODE(opened.st_mode) != 0o600
            or opened.st_nlink != 1
            or opened.st_size != 0
            or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
        ):
            raise WaveOneRoleBFullReaderError("owned V3 bootstrap lease identity drifted")
        return opened.st_dev, opened.st_ino

    def rollback_owned_bootstrap() -> None:
        nonlocal created_root, created_locks, created_lease, lease_locked
        cleanup_root_fd = root_fd
        cleanup_lock_fd = directory_fd
        cleanup_lease_fd = descriptor
        close_root = close_locks = close_lease = False
        cleanup_lease_locked = lease_locked
        try:
            if created_root and cleanup_root_fd < 0:
                cleanup_root_fd = os.open(
                    OUTPUT_RELATIVE_ROOT.name,
                    directory_flags,
                    dir_fd=parent_fd,
                )
                close_root = True
            if (created_locks or created_lease) and cleanup_lock_fd < 0:
                cleanup_lock_fd = os.open("locks", directory_flags, dir_fd=cleanup_root_fd)
                close_locks = True
            if created_lease and cleanup_lease_fd < 0:
                cleanup_lease_fd = os.open(
                    "full-reader-execution.lease",
                    os.O_RDWR | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                    dir_fd=cleanup_lock_fd,
                )
                close_lease = True

            # Authenticate the complete owned ancestry before the first mutation.
            if created_root and (
                owned_root_generation is None
                or checked_directory(
                    cleanup_root_fd,
                    parent_fd,
                    OUTPUT_RELATIVE_ROOT.name,
                    "owned V3 output root",
                )
                != owned_root_generation
            ):
                raise WaveOneRoleBFullReaderError("owned V3 bootstrap root changed before rollback")
            if created_locks and (
                owned_lock_generation is None
                or checked_directory(
                    cleanup_lock_fd,
                    cleanup_root_fd,
                    "locks",
                    "owned V3 lock root",
                )
                != owned_lock_generation
            ):
                raise WaveOneRoleBFullReaderError(
                    "owned V3 bootstrap lock root changed before rollback"
                )
            if created_lease:
                current = _v3_lock_identity(
                    cleanup_lease_fd,
                    cleanup_lock_fd,
                    "full-reader-execution.lease",
                    mode=0o600,
                )
                if owned_lease_identity is None or current != owned_lease_identity:
                    raise WaveOneRoleBFullReaderError(
                        "owned V3 bootstrap lease changed before rollback"
                    )
                if not cleanup_lease_locked:
                    try:
                        fcntl.flock(cleanup_lease_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError as error:
                        raise WaveOneRoleBFullReaderError(
                            "owned V3 bootstrap lease cannot be reacquired for rollback"
                        ) from error
                    cleanup_lease_locked = True

            if created_lease:
                os.unlink("full-reader-execution.lease", dir_fd=cleanup_lock_fd)
                os.fsync(cleanup_lock_fd)
                created_lease = False
            if created_locks and not os.listdir(cleanup_lock_fd):
                os.rmdir("locks", dir_fd=cleanup_root_fd)
                os.fsync(cleanup_root_fd)
                created_locks = False
            if created_root and not os.listdir(cleanup_root_fd):
                os.rmdir(OUTPUT_RELATIVE_ROOT.name, dir_fd=parent_fd)
                os.fsync(parent_fd)
                created_root = False
        finally:
            if close_lease and cleanup_lease_fd >= 0:
                try:
                    if cleanup_lease_locked:
                        fcntl.flock(cleanup_lease_fd, fcntl.LOCK_UN)
                finally:
                    os.close(cleanup_lease_fd)
            if close_locks and cleanup_lock_fd >= 0:
                os.close(cleanup_lock_fd)
            if close_root and cleanup_root_fd >= 0:
                os.close(cleanup_root_fd)

    try:
        parent_fd = (
            os.open(parent, directory_flags) if shared_parent is None else os.dup(shared_parent[1])
        )
        parent_identity = os.fstat(parent_fd)
        if (
            not stat.S_ISDIR(parent_identity.st_mode)
            or stat.S_IMODE(parent_identity.st_mode) != 0o755
            or (
                shared_parent is not None
                and (
                    parent_identity.st_dev,
                    parent_identity.st_ino,
                    parent_identity.st_mode,
                )
                != shared_parent[2]
            )
        ):
            raise WaveOneRoleBFullReaderError("V3 output bootstrap parent topology drifted")
        try:
            fcntl.flock(parent_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise WaveOneRoleBFullReaderError(
                "V3 output bootstrap parent is already held"
            ) from error
        parent_locked = True
        parent_names_before = set(os.listdir(parent_fd))
        if OUTPUT_RELATIVE_ROOT.name not in parent_names_before:
            if not create:
                raise WaveOneRoleBFullReaderError("V3 output root is absent")
            os.mkdir(OUTPUT_RELATIVE_ROOT.name, 0o755, dir_fd=parent_fd)
            created_root = True
            try:
                owned_root_generation = capture_owned_directory(
                    parent_fd,
                    OUTPUT_RELATIVE_ROOT.name,
                    "owned V3 output root",
                )
            except BaseException:
                # Preserve enough exact ownership to unwind a one-shot failure
                # between mkdirat and the normal retained-directory open.
                try:
                    owned_root_generation = capture_owned_directory(
                        parent_fd,
                        OUTPUT_RELATIVE_ROOT.name,
                        "owned V3 output root",
                    )
                except BaseException:
                    pass
                raise
            os.fsync(parent_fd)
        root_fd = os.open(OUTPUT_RELATIVE_ROOT.name, directory_flags, dir_fd=parent_fd)
        try:
            fcntl.flock(root_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise WaveOneRoleBFullReaderError("V3 output root is already held") from error
        root_locked = True
        root_generation = checked_directory(
            root_fd, parent_fd, OUTPUT_RELATIVE_ROOT.name, "V3 output root"
        )
        root_names = set(os.listdir(root_fd))
        if "locks" not in root_names:
            if not create or root_names:
                raise WaveOneRoleBFullReaderError(
                    "V3 output without locks is not a bootstrap state"
                )
            os.mkdir("locks", 0o755, dir_fd=root_fd)
            created_locks = True
            try:
                owned_lock_generation = capture_owned_directory(
                    root_fd,
                    "locks",
                    "owned V3 lock root",
                )
            except BaseException:
                # As above, authenticate the just-created empty directory for
                # rollback without ever adopting a different generation.
                try:
                    owned_lock_generation = capture_owned_directory(
                        root_fd,
                        "locks",
                        "owned V3 lock root",
                    )
                except BaseException:
                    pass
                raise
            os.fsync(root_fd)
        directory_fd = os.open("locks", directory_flags, dir_fd=root_fd)
        lock_generation = checked_directory(directory_fd, root_fd, "locks", "V3 output lock root")
        lock_names = set(os.listdir(directory_fd))
        if "full-reader-execution.lease" not in lock_names:
            if not create or lock_names or set(os.listdir(root_fd)) != {"locks"}:
                raise WaveOneRoleBFullReaderError(
                    "V3 output missing lease is not a bootstrap state"
                )
            descriptor = os.open(
                "full-reader-execution.lease",
                os.O_RDWR
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=directory_fd,
            )
            created_lease = True
            try:
                owned_lease_identity = capture_owned_lease(descriptor, directory_fd)
            except BaseException:
                # The retained descriptor is already exact ownership authority;
                # retry once to preserve its token for exception rollback.
                try:
                    owned_lease_identity = capture_owned_lease(descriptor, directory_fd)
                except BaseException:
                    pass
                raise
            os.fsync(descriptor)
            identity = _v3_lock_identity(
                descriptor,
                directory_fd,
                "full-reader-execution.lease",
                mode=0o600,
            )
            os.fsync(directory_fd)
        else:
            descriptor = os.open(
                "full-reader-execution.lease",
                os.O_RDWR | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_fd,
            )
        if identity is None:
            identity = _v3_lock_identity(
                descriptor,
                directory_fd,
                "full-reader-execution.lease",
                mode=0o600,
            )
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise WaveOneRoleBFullReaderError("V3 execution lease is already held") from error
        lease_locked = True
        acquired = _v3_lock_identity(
            descriptor, directory_fd, "full-reader-execution.lease", mode=0o600
        )
        if acquired != identity:
            raise WaveOneRoleBFullReaderError("V3 lease changed during acquisition")
        checked_directory(directory_fd, root_fd, "locks", "V3 output lock root")
        checked_directory(root_fd, parent_fd, OUTPUT_RELATIVE_ROOT.name, "V3 output root")
        expected_parent_names = parent_names_before | (
            {OUTPUT_RELATIVE_ROOT.name} if created_root else set()
        )
        if set(os.listdir(parent_fd)) != expected_parent_names:
            raise WaveOneRoleBFullReaderError(
                "V3 output bootstrap parent changed during acquisition"
            )
        parent_after_bootstrap = os.fstat(parent_fd)
        parent_names_after_bootstrap = set(os.listdir(parent_fd))
        parent_token = (
            parent_after_bootstrap.st_dev,
            parent_after_bootstrap.st_ino,
            parent_after_bootstrap.st_mode,
            parent_after_bootstrap.st_nlink,
            parent_after_bootstrap.st_size,
            parent_after_bootstrap.st_mtime_ns,
            parent_after_bootstrap.st_ctime_ns,
        )
        mutation_binding_token = _V3_OUTPUT_MUTATION_BINDING.set(
            (
                project_root,
                parent_fd,
                root_fd,
                directory_fd,
                root_generation,
                lock_generation,
            )
        )
        control_marker_token = _V3_CONTROL_COMMIT_MARKER.set(False)
        _v3_assert_output_mutation_ancestry(project_root, "V3 execution lease acquisition")
        yield descriptor
        _v3_assert_output_mutation_ancestry(project_root, "V3 execution lease release")
        checked_directory(directory_fd, root_fd, "locks", "held V3 lock root")
        checked_directory(root_fd, parent_fd, OUTPUT_RELATIVE_ROOT.name, "held V3 output root")
        parent_after_body = os.fstat(parent_fd)
        parent_named_after_body = os.stat(parent, follow_symlinks=False)
        observed_parent_token = (
            parent_after_body.st_dev,
            parent_after_body.st_ino,
            parent_after_body.st_mode,
            parent_after_body.st_nlink,
            parent_after_body.st_size,
            parent_after_body.st_mtime_ns,
            parent_after_body.st_ctime_ns,
        )
        named_parent_token = (
            parent_named_after_body.st_dev,
            parent_named_after_body.st_ino,
            parent_named_after_body.st_mode,
            parent_named_after_body.st_nlink,
            parent_named_after_body.st_size,
            parent_named_after_body.st_mtime_ns,
            parent_named_after_body.st_ctime_ns,
        )
        if (
            observed_parent_token != parent_token
            or named_parent_token != parent_token
            or set(os.listdir(parent_fd)) != parent_names_after_bootstrap
        ):
            raise WaveOneRoleBFullReaderError(
                "V3 output bootstrap parent changed while the lease was held"
            )
        if (
            _v3_lock_identity(
                descriptor,
                directory_fd,
                "full-reader-execution.lease",
                mode=0o600,
            )
            != identity
        ):
            raise WaveOneRoleBFullReaderError("held V3 execution lease changed")
    except OSError as error:
        raise WaveOneRoleBFullReaderError("V3 execution lease operation failed") from error
    finally:
        cleanup_errors: list[BaseException] = []
        if (created_root or created_locks or created_lease) and not _V3_CONTROL_COMMIT_MARKER.get():
            _v3_cleanup_attempt(cleanup_errors, rollback_owned_bootstrap)
        if descriptor >= 0:
            if lease_locked:
                _v3_cleanup_attempt(
                    cleanup_errors,
                    lambda: fcntl.flock(descriptor, fcntl.LOCK_UN),
                )
            _v3_cleanup_attempt(cleanup_errors, lambda: os.close(descriptor))
        if mutation_binding_token is not None:
            _v3_cleanup_attempt(
                cleanup_errors,
                lambda: _V3_OUTPUT_MUTATION_BINDING.reset(mutation_binding_token),
            )
        if control_marker_token is not None:
            _v3_cleanup_attempt(
                cleanup_errors,
                lambda: _V3_CONTROL_COMMIT_MARKER.reset(control_marker_token),
            )
        for opened in (directory_fd, root_fd):
            if opened >= 0:
                if opened == root_fd and root_locked:
                    _v3_cleanup_attempt(
                        cleanup_errors,
                        lambda descriptor_to_unlock=opened: fcntl.flock(
                            descriptor_to_unlock, fcntl.LOCK_UN
                        ),
                    )
                _v3_cleanup_attempt(
                    cleanup_errors,
                    lambda descriptor_to_close=opened: os.close(descriptor_to_close),
                )
        if parent_fd >= 0:
            if parent_locked:
                _v3_cleanup_attempt(
                    cleanup_errors,
                    lambda: fcntl.flock(parent_fd, fcntl.LOCK_UN),
                )
            _v3_cleanup_attempt(cleanup_errors, lambda: os.close(parent_fd))
        if cleanup_errors:
            raise cleanup_errors[0]


@contextmanager
def _v3_read_only_output_snapshot(project_root: Path, document_ids: list[str]) -> Iterator[None]:
    """Hold a non-mutating shared global lease across one exact output replay."""

    if len(document_ids) != 27 or len(set(document_ids)) != 27:
        raise WaveOneRoleBFullReaderError("V3 read-only document lock set drifted")
    expected_document_locks = {f"{item.removeprefix('sha256:')}.lock" for item in document_ids}
    if any(
        not item.startswith("sha256:") or not _is_sha256(item.removeprefix("sha256:"))
        for item in document_ids
    ):
        raise WaveOneRoleBFullReaderError("V3 read-only document lock name drifted")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    parent_fd = root_fd = locks_fd = documents_fd = descriptor = -1
    parent_locked = root_locked = lease_locked = False
    snapshot_token = None
    root_token = locks_token = documents_token = None
    lease_identity = None
    root_names: set[str] | None = None

    def directory_token(item: os.stat_result) -> tuple[int, ...]:
        return (
            item.st_dev,
            item.st_ino,
            item.st_mode,
            item.st_nlink,
            item.st_size,
            item.st_mtime_ns,
            item.st_ctime_ns,
        )

    def checked_directory(
        opened_fd: int,
        parent_fd: int | None,
        name: str | None,
        expected_names: set[str],
    ) -> tuple[int, ...]:
        opened = os.fstat(opened_fd)
        if parent_fd is None:
            named = os.stat(
                OUTPUT_RELATIVE_ROOT.name,
                dir_fd=output_parent_fd,
                follow_symlinks=False,
            )
        else:
            assert name is not None
            named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        token = directory_token(opened)
        if (
            not stat.S_ISDIR(opened.st_mode)
            or stat.S_IMODE(opened.st_mode) != 0o755
            or directory_token(named) != token
            or set(os.listdir(opened_fd)) != expected_names
        ):
            raise WaveOneRoleBFullReaderError("V3 read-only output directory generation drifted")
        return token

    def validate_lock_files() -> None:
        nonlocal lease_identity
        observed = _v3_lock_identity(
            descriptor,
            locks_fd,
            "full-reader-execution.lease",
            mode=0o600,
        )
        if lease_identity is None:
            lease_identity = observed
        elif observed != lease_identity:
            raise WaveOneRoleBFullReaderError("held V3 read-only lease changed")
        for name in sorted(expected_document_locks):
            lock_fd = os.open(
                name,
                os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=documents_fd,
            )
            try:
                _v3_lock_identity(lock_fd, documents_fd, name, mode=0o600)
            finally:
                os.close(lock_fd)

    output_parent_fd = -1
    parent_token = None
    parent_names: set[str] | None = None
    shared_parent = _V3_SHARED_OUTPUT_PARENT_BINDING.get()
    if shared_parent is not None and shared_parent[0] != project_root:
        raise WaveOneRoleBFullReaderError(
            "V3 read-only shared output parent project binding drifted"
        )
    try:
        output_parent_fd = (
            os.open(project_root / OUTPUT_RELATIVE_ROOT.parent, flags)
            if shared_parent is None
            else os.dup(shared_parent[1])
        )
        parent_fd = output_parent_fd
        try:
            fcntl.flock(parent_fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise WaveOneRoleBFullReaderError(
                "V3 output bootstrap parent is held by a mutating command"
            ) from error
        parent_locked = True
        parent_identity = os.fstat(parent_fd)
        if (
            shared_parent is not None
            and (
                parent_identity.st_dev,
                parent_identity.st_ino,
                parent_identity.st_mode,
            )
            != shared_parent[2]
        ):
            raise WaveOneRoleBFullReaderError(
                "V3 read-only shared output parent generation drifted"
            )
        parent_token = directory_token(parent_identity)
        parent_names = set(os.listdir(parent_fd))
        root_fd = os.open(OUTPUT_RELATIVE_ROOT.name, flags, dir_fd=parent_fd)
        try:
            fcntl.flock(root_fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise WaveOneRoleBFullReaderError(
                "V3 output root is held by an active mutating command"
            ) from error
        root_locked = True
        locks_fd = os.open("locks", flags, dir_fd=root_fd)
        documents_fd = os.open("documents", flags, dir_fd=locks_fd)
        descriptor = os.open(
            "full-reader-execution.lease",
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=locks_fd,
        )
        try:
            fcntl.flock(descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise WaveOneRoleBFullReaderError(
                "V3 output is held by an active mutating command"
            ) from error
        lease_locked = True
        observed_root_names = set(os.listdir(root_fd))
        allowed_root_names = {
            "locks",
            "objects",
            "checkpoints",
            "documents",
            "full-reader-execution-control.json",
        }
        if "full-reader-aggregate.json" in observed_root_names:
            allowed_root_names.add("full-reader-aggregate.json")
        if observed_root_names != allowed_root_names:
            raise WaveOneRoleBFullReaderError("V3 read-only output root name set drifted")
        root_names = observed_root_names
        root_token = checked_directory(
            root_fd,
            None,
            None,
            root_names,
        )
        locks_token = checked_directory(
            locks_fd,
            root_fd,
            "locks",
            {"full-reader-execution.lease", "documents"},
        )
        documents_token = checked_directory(
            documents_fd,
            locks_fd,
            "documents",
            expected_document_locks,
        )
        validate_lock_files()
        snapshot_token = _V3_OUTPUT_SNAPSHOT_BINDING.set((project_root, root_fd))
        yield
        validate_lock_files()
        if (
            parent_token is None
            or parent_names is None
            or directory_token(os.fstat(parent_fd)) != parent_token
            or set(os.listdir(parent_fd)) != parent_names
            or root_names is None
            or checked_directory(root_fd, None, None, root_names) != root_token
            or checked_directory(
                locks_fd,
                root_fd,
                "locks",
                {"full-reader-execution.lease", "documents"},
            )
            != locks_token
            or checked_directory(
                documents_fd,
                locks_fd,
                "documents",
                expected_document_locks,
            )
            != documents_token
        ):
            raise WaveOneRoleBFullReaderError("held V3 read-only output generation changed")
    except OSError as error:
        raise WaveOneRoleBFullReaderError(
            "V3 read-only output snapshot operation failed"
        ) from error
    finally:
        cleanup_errors: list[BaseException] = []
        if snapshot_token is not None:
            _v3_cleanup_attempt(
                cleanup_errors,
                lambda: _V3_OUTPUT_SNAPSHOT_BINDING.reset(snapshot_token),
            )
        if descriptor >= 0:
            if lease_locked:
                _v3_cleanup_attempt(
                    cleanup_errors,
                    lambda: fcntl.flock(descriptor, fcntl.LOCK_UN),
                )
            _v3_cleanup_attempt(cleanup_errors, lambda: os.close(descriptor))
        for opened in (documents_fd, locks_fd):
            if opened >= 0:
                _v3_cleanup_attempt(
                    cleanup_errors,
                    lambda descriptor_to_close=opened: os.close(descriptor_to_close),
                )
        if root_fd >= 0:
            if root_locked:
                _v3_cleanup_attempt(
                    cleanup_errors,
                    lambda: fcntl.flock(root_fd, fcntl.LOCK_UN),
                )
            _v3_cleanup_attempt(cleanup_errors, lambda: os.close(root_fd))
        if parent_fd >= 0:
            if parent_locked:
                _v3_cleanup_attempt(
                    cleanup_errors,
                    lambda: fcntl.flock(parent_fd, fcntl.LOCK_UN),
                )
            _v3_cleanup_attempt(cleanup_errors, lambda: os.close(parent_fd))
        if cleanup_errors:
            raise cleanup_errors[0]


def _v3_output_live_manifest(project_root: Path) -> list[list[Any]]:
    """Build a nofollow, fd-relative identity+content manifest of full-v3."""

    _v3_assert_output_mutation_ancestry(project_root, "V3 output manifest")
    root = project_root / OUTPUT_RELATIVE_ROOT
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        retained_root_fd = _v3_retained_output_root_fd(project_root)
        root_fd = os.open(root, flags) if retained_root_fd is None else os.dup(retained_root_fd)
    except OSError as error:
        raise WaveOneRoleBFullReaderError(
            "V3 output manifest root cannot be opened safely"
        ) from error
    records: list[list[Any]] = []

    def directory_token(identity: os.stat_result) -> tuple[int, ...]:
        return (
            identity.st_dev,
            identity.st_ino,
            identity.st_mode,
            identity.st_nlink,
            identity.st_size,
            identity.st_mtime_ns,
            identity.st_ctime_ns,
        )

    def visit(
        descriptor: int,
        relative: Path,
        parent_fd: int | None,
        parent_name: str | None,
    ) -> None:
        before = os.fstat(descriptor)
        names = sorted(os.listdir(descriptor))
        after_names = os.fstat(descriptor)
        if not stat.S_ISDIR(before.st_mode) or directory_token(before) != directory_token(
            after_names
        ):
            raise WaveOneRoleBFullReaderError(
                "V3 output directory changed during manifest enumeration"
            )
        if parent_fd is None:
            named = os.stat(root, follow_symlinks=False)
        else:
            assert parent_name is not None
            named = os.stat(parent_name, dir_fd=parent_fd, follow_symlinks=False)
        if directory_token(named) != directory_token(before):
            raise WaveOneRoleBFullReaderError("V3 output directory pathname binding drifted")
        records.append(
            [
                "d",
                relative.as_posix(),
                stat.S_IMODE(before.st_mode),
                before.st_nlink,
                before.st_size,
                before.st_mtime_ns,
                before.st_ctime_ns,
                before.st_dev,
                before.st_ino,
                names,
            ]
        )
        for name in names:
            named_identity = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            child_relative = relative / name if relative.parts else Path(name)
            if stat.S_ISDIR(named_identity.st_mode):
                child_fd = os.open(name, flags, dir_fd=descriptor)
                try:
                    child_opened = os.fstat(child_fd)
                    if directory_token(child_opened) != directory_token(named_identity):
                        raise WaveOneRoleBFullReaderError(
                            "V3 output child directory binding drifted"
                        )
                    visit(child_fd, child_relative, descriptor, name)
                finally:
                    os.close(child_fd)
                continue
            if not stat.S_ISREG(named_identity.st_mode):
                if stat.S_ISLNK(named_identity.st_mode):
                    raise WaveOneRoleBFullReaderError("V3 output manifest encountered a symlink")
                raise WaveOneRoleBFullReaderError("V3 output manifest encountered a special entry")
            file_fd = os.open(
                name,
                os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=descriptor,
            )
            try:
                file_before = os.fstat(file_fd)
                chunks = []
                while chunk := os.read(file_fd, 1024 * 1024):
                    chunks.append(chunk)
                payload = b"".join(chunks)
                file_after = os.fstat(file_fd)
                file_named_after = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
                file_token = lambda item: (  # noqa: E731
                    item.st_dev,
                    item.st_ino,
                    item.st_mode,
                    item.st_nlink,
                    item.st_size,
                    item.st_mtime_ns,
                    item.st_ctime_ns,
                )
                if (
                    not stat.S_ISREG(file_before.st_mode)
                    or file_token(file_before) != file_token(file_after)
                    or file_token(file_after) != file_token(file_named_after)
                    or len(payload) != file_after.st_size
                ):
                    raise WaveOneRoleBFullReaderError("V3 output file changed during manifest read")
                records.append(
                    [
                        "f",
                        child_relative.as_posix(),
                        stat.S_IMODE(file_after.st_mode),
                        file_after.st_nlink,
                        file_after.st_size,
                        sha256_bytes(payload),
                        file_after.st_mtime_ns,
                        file_after.st_ctime_ns,
                        file_after.st_dev,
                        file_after.st_ino,
                    ]
                )
            finally:
                os.close(file_fd)
        final = os.fstat(descriptor)
        if directory_token(final) != directory_token(before):
            raise WaveOneRoleBFullReaderError(
                "V3 output directory changed during manifest traversal"
            )

    try:
        visit(root_fd, Path(), None, None)
    except OSError as error:
        raise WaveOneRoleBFullReaderError("V3 output manifest traversal failed") from error
    finally:
        os.close(root_fd)
    _v3_assert_output_mutation_ancestry(project_root, "V3 output manifest completion")
    return records


@contextmanager
def _v3_document_locks(project_root: Path, document_ids: list[str]) -> Iterator[None]:
    _v3_assert_output_mutation_ancestry(project_root, "V3 document-lock acquisition")
    try:
        context = _v3_held_output_directory(
            project_root, OUTPUT_RELATIVE_ROOT / "locks" / "documents", create=True
        )
        _directory, directory_fd = context.__enter__()
    except WaveOneRoleBFullReaderError:
        raise
    held: list[tuple[str, int, tuple[int, int]]] = []
    try:
        if len(document_ids) != 27 or len(set(document_ids)) != 27:
            raise WaveOneRoleBFullReaderError("V3 document lock set drifted")
        for document_id in sorted(document_ids):
            source_sha = document_id.removeprefix("sha256:")
            if not _is_sha256(source_sha):
                raise WaveOneRoleBFullReaderError("V3 document lock name drifted")
            name = f"{source_sha}.lock"
            try:
                descriptor = os.open(
                    name,
                    os.O_RDWR
                    | os.O_CREAT
                    | os.O_EXCL
                    | getattr(os, "O_CLOEXEC", 0)
                    | getattr(os, "O_NOFOLLOW", 0),
                    0o600,
                    dir_fd=directory_fd,
                )
            except FileExistsError:
                descriptor = os.open(
                    name,
                    os.O_RDWR | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                    dir_fd=directory_fd,
                )
            try:
                identity = _v3_lock_identity(descriptor, directory_fd, name, mode=0o600)
                os.fsync(descriptor)
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError as error:
                    raise WaveOneRoleBFullReaderError(
                        "a V3 document lock is already held"
                    ) from error
                if _v3_lock_identity(descriptor, directory_fd, name, mode=0o600) != identity:
                    raise WaveOneRoleBFullReaderError("V3 document lock changed during acquisition")
                held.append((name, descriptor, identity))
            except BaseException:
                if all(item[1] != descriptor for item in held):
                    os.close(descriptor)
                raise
        os.fsync(directory_fd)
        yield
        _v3_assert_output_mutation_ancestry(project_root, "V3 document-lock release")
        for name, descriptor, identity in held:
            if _v3_lock_identity(descriptor, directory_fd, name, mode=0o600) != identity:
                raise WaveOneRoleBFullReaderError("held V3 document lock changed")
    except OSError as error:
        raise WaveOneRoleBFullReaderError("V3 document lock operation failed") from error
    finally:
        cleanup_errors: list[BaseException] = []
        for _name, descriptor, _identity in reversed(held):
            _v3_cleanup_attempt(
                cleanup_errors,
                lambda descriptor_to_unlock=descriptor: fcntl.flock(
                    descriptor_to_unlock, fcntl.LOCK_UN
                ),
            )
            _v3_cleanup_attempt(
                cleanup_errors,
                lambda descriptor_to_close=descriptor: os.close(descriptor_to_close),
            )
        _v3_cleanup_attempt(cleanup_errors, lambda: context.__exit__(None, None, None))
        if cleanup_errors:
            raise cleanup_errors[0]


def _v3_validate_output_lock_topology(project_root: Path, document_ids: list[str]) -> None:
    binding = _V3_OUTPUT_READ_BINDING.get()
    expected_document_locks = {f"{item.removeprefix('sha256:')}.lock" for item in document_ids}
    if binding is not None:
        output_root, file_tokens, directory_tokens, _directory_fds = binding
        if output_root != project_root / OUTPUT_RELATIVE_ROOT:
            raise WaveOneRoleBFullReaderError("V3 lock binding root drifted")
        lock_root_token = directory_tokens.get("locks")
        documents_token = directory_tokens.get("locks/documents")
        if (
            lock_root_token is None
            or documents_token is None
            or lock_root_token[2] != 0o755
            or lock_root_token[3] != 3
            or set(lock_root_token[9]) != {"full-reader-execution.lease", "documents"}
            or documents_token[2] != 0o755
            or documents_token[3] != 2
            or set(documents_token[9]) != expected_document_locks
        ):
            raise WaveOneRoleBFullReaderError("V3 bound output lock topology drifted")
        expected_lock_paths = {"locks/full-reader-execution.lease"} | {
            f"locks/documents/{name}" for name in expected_document_locks
        }
        observed_lock_paths = {
            relative for relative in file_tokens if Path(relative).parts[:1] == ("locks",)
        }
        if observed_lock_paths != expected_lock_paths or any(
            file_tokens[relative][2:5] != [0o600, 1, 0] for relative in expected_lock_paths
        ):
            raise WaveOneRoleBFullReaderError("V3 bound output lock file topology drifted")
        return
    with (
        _v3_held_output_directory(project_root, OUTPUT_RELATIVE_ROOT / "locks", create=False) as (
            _lock_root,
            lock_fd,
        ),
        _v3_held_output_directory(
            project_root,
            OUTPUT_RELATIVE_ROOT / "locks" / "documents",
            create=False,
        ) as (_documents_root, documents_fd),
    ):
        if (
            set(os.listdir(lock_fd)) != {"full-reader-execution.lease", "documents"}
            or set(os.listdir(documents_fd)) != expected_document_locks
        ):
            raise WaveOneRoleBFullReaderError("V3 output lock name set drifted")
        root_stat = os.fstat(lock_fd)
        documents_stat = os.fstat(documents_fd)
        if (
            not stat.S_ISDIR(root_stat.st_mode)
            or stat.S_IMODE(root_stat.st_mode) != 0o755
            or root_stat.st_nlink != 3
            or not stat.S_ISDIR(documents_stat.st_mode)
            or stat.S_IMODE(documents_stat.st_mode) != 0o755
            or documents_stat.st_nlink != 2
        ):
            raise WaveOneRoleBFullReaderError("V3 output lock directory topology drifted")
        for directory_fd, name in [
            (lock_fd, "full-reader-execution.lease"),
            *((documents_fd, item) for item in sorted(expected_document_locks)),
        ]:
            descriptor = os.open(
                name,
                os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_fd,
            )
            try:
                _v3_lock_identity(descriptor, directory_fd, name, mode=0o600)
            finally:
                os.close(descriptor)


def _v3_output_lock_state(project_root: Path, document_ids: list[str]) -> str:
    _v3_assert_output_mutation_ancestry(project_root, "V3 output-lock state")
    with (
        _v3_held_output_directory(project_root, OUTPUT_RELATIVE_ROOT, create=False) as (
            _output_root,
            root_fd,
        ),
        _v3_held_output_directory(project_root, OUTPUT_RELATIVE_ROOT / "locks", create=False) as (
            _lock_root,
            lock_fd,
        ),
    ):
        names = set(os.listdir(lock_fd))
        if "full-reader-execution.lease" not in names:
            raise WaveOneRoleBFullReaderError("V3 output global lease is missing")
        global_fd = os.open(
            "full-reader-execution.lease",
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=lock_fd,
        )
        try:
            _v3_lock_identity(
                global_fd,
                lock_fd,
                "full-reader-execution.lease",
                mode=0o600,
            )
        finally:
            os.close(global_fd)
        if names == {"full-reader-execution.lease"}:
            if set(os.listdir(root_fd)) != {
                "full-reader-execution-control.json",
                "locks",
            }:
                raise WaveOneRoleBFullReaderError(
                    "V3 control-only lock state crossed an evidence phase"
                )
            return "CONTROL_ONLY_BOOTSTRAP"
        if names == {"full-reader-execution.lease", "documents"}:
            with _v3_held_output_directory(
                project_root,
                OUTPUT_RELATIVE_ROOT / "locks" / "documents",
                create=False,
            ) as (_documents_root, documents_fd):
                documents_identity = os.fstat(documents_fd)
                expected_names = {f"{item.removeprefix('sha256:')}.lock" for item in document_ids}
                observed_names = set(os.listdir(documents_fd))
                if (
                    not stat.S_ISDIR(documents_identity.st_mode)
                    or stat.S_IMODE(documents_identity.st_mode) != 0o755
                    or documents_identity.st_nlink != 2
                    or not observed_names <= expected_names
                ):
                    raise WaveOneRoleBFullReaderError(
                        "V3 output document-lock bootstrap topology drifted"
                    )
                for name in sorted(observed_names):
                    descriptor = os.open(
                        name,
                        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                        dir_fd=documents_fd,
                    )
                    try:
                        _v3_lock_identity(descriptor, documents_fd, name, mode=0o600)
                    finally:
                        os.close(descriptor)
                if observed_names == expected_names:
                    _v3_validate_output_lock_topology(project_root, document_ids)
                    return "FULL_LOCK_SET"
                if set(os.listdir(root_fd)) != {
                    "full-reader-execution-control.json",
                    "locks",
                }:
                    raise WaveOneRoleBFullReaderError(
                        "partial V3 lock bootstrap exists after evidence publication"
                    )
                return "PARTIAL_LOCK_BOOTSTRAP"
        raise WaveOneRoleBFullReaderError("V3 output lock root has a partial or foreign state")


def _v3_ensure_capacity(project_root: Path, minimum_bytes: int) -> None:
    if type(minimum_bytes) is not int or minimum_bytes <= 0:
        raise WaveOneRoleBFullReaderError("V3 capacity threshold drifted")
    try:
        available = os.statvfs(project_root).f_bavail * os.statvfs(project_root).f_frsize
    except OSError as error:
        raise WaveOneRoleBFullReaderError("V3 filesystem capacity cannot be read") from error
    if available < minimum_bytes:
        raise WaveOneRoleBFullReaderError("V3 requires at least the sealed free-space minimum")


def _v3_load_published_control(project_root: Path) -> dict[str, Any]:
    control_path = project_root / OUTPUT_RELATIVE_ROOT / "full-reader-execution-control.json"
    payload, identity = _v3_read_nofollow(control_path, "published V3 full-reader control")
    control = _json_object(payload, "published V3 full-reader control")
    logical = control.get("control_identity_sha256")
    if (
        stat.S_IMODE(identity.st_mode) != 0o444
        or identity.st_nlink != 1
        or control.get("format_version") != "BANK_CORPUS_WAVE_1_ROLE_B_FULL_READER_CONTROL_V3"
        or control.get("status")
        != "READY_FOR_AUTHENTICATED_FAILED_V2_OCR_ADOPTION_AND_FRESH_NATIVE_READS"
        or not _is_sha256(logical)
        or _canonical_sha256(
            {key: value for key, value in control.items() if key != "control_identity_sha256"}
        )
        != logical
    ):
        raise WaveOneRoleBFullReaderError("published V3 control identity drifted")
    return control


def _v3_validate_published_executor(project_root: Path, published: dict[str, Any]) -> None:
    git = published.get("executor_git")
    ledger = published.get("executor_implementation_ledger")
    if (
        not isinstance(git, dict)
        or set(git) != {"commit", "dirty"}
        or re.fullmatch(r"[0-9a-f]{40}", git.get("commit", "")) is None
        or git.get("dirty") is not False
        or not isinstance(ledger, dict)
        or set(ledger) != {"records", "sha256"}
        or not isinstance(ledger.get("records"), list)
        or _canonical_sha256(ledger["records"]) != ledger.get("sha256")
    ):
        raise WaveOneRoleBFullReaderError("published V3 executor authority drifted")
    try:
        current_git = sentinel._git_identity(project_root, require_clean=True)  # noqa: SLF001
    except sentinel.WaveOneRoleBSentinelError as error:
        raise WaveOneRoleBFullReaderError(str(error)) from error
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", git["commit"], current_git["commit"]],
        cwd=project_root,
        check=False,
        capture_output=True,
    )
    if ancestor.returncode != 0:
        raise WaveOneRoleBFullReaderError("published V3 producer is not an ancestor")
    expected_paths = {item.as_posix() for item in V3_IMPLEMENTATION_RELATIVE_PATHS}
    records = ledger["records"]
    if (
        len(records) != len(expected_paths)
        or {item.get("path") for item in records if isinstance(item, dict)} != expected_paths
    ):
        raise WaveOneRoleBFullReaderError("published V3 ledger path set drifted")
    for record in records:
        if (
            not isinstance(record, dict)
            or set(record) != {"phase", "kind", "path", "sha256", "size_bytes"}
            or record["phase"] != "READ"
            or record["kind"] != "IMPLEMENTATION"
            or not _is_sha256(record["sha256"])
            or type(record["size_bytes"]) is not int
            or record["size_bytes"] < 0
        ):
            raise WaveOneRoleBFullReaderError("published V3 ledger record drifted")
        historical = _git_blob(project_root, git["commit"], record["path"])
        current = _stable_bytes(
            _project_path(project_root, record["path"], "V3 implementation path"),
            "V3 implementation path",
        )
        if (
            len(historical) != record["size_bytes"]
            or sha256_bytes(historical) != record["sha256"]
            or current != historical
        ):
            raise WaveOneRoleBFullReaderError("V3 implementation differs from producer")


def publish_authenticated_control(project_root: Path, *, model_cache: Path) -> dict[str, Any]:
    with _v3_mutation_entry():
        return _publish_authenticated_control_mutating(project_root, model_cache=model_cache)


def _publish_authenticated_control_mutating(
    project_root: Path, *, model_cache: Path
) -> dict[str, Any]:
    project_root = project_root.resolve()
    model_cache = model_cache.resolve()
    sealed, policy, _executor = _v3_authenticate_plan(
        project_root, model_cache, require_clean_executor=True
    )
    document_ids = sorted(item["document_id"] for item in sealed["documents"])
    with _v3_failed_archive_locks(project_root, document_ids):
        control = _v3_build_authenticated_control_held(project_root, model_cache=model_cache)
        _v3_ensure_capacity(project_root, policy["execution"]["minimum_free_space_bytes"])
        with _v3_execution_lease(project_root, create=True):
            _interrupted_relative, preflight_manifest = _v3_preflight_output_temporaries(
                project_root, document_ids, stage="control"
            )
            control_payload = _canonical_bytes(control)
            _v3_recover_publication_directory(
                project_root,
                OUTPUT_RELATIVE_ROOT,
                create=True,
                allowed_final=lambda candidate: candidate == "full-reader-execution-control.json",
                validate_payload=lambda candidate, payload: (
                    candidate == "full-reader-execution-control.json" and payload == control_payload
                ),
                expected_output_manifest=preflight_manifest,
            )
            _publish_exclusive(
                project_root,
                OUTPUT_RELATIVE_ROOT,
                "full-reader-execution-control.json",
                control_payload,
            )
            # Publication is the durable commit point.  A later replay failure must
            # retain the exact lease topology needed to authenticate/recover it.
            _V3_CONTROL_COMMIT_MARKER.set(True)
            published_manifest_before = _v3_output_live_manifest(project_root)
            with _v3_bind_output_reads(project_root, published_manifest_before):
                observed = _v3_load_published_control(project_root)
                replay = _v3_build_authenticated_control_held(project_root, model_cache=model_cache)
            published_manifest_after = _v3_output_live_manifest(project_root)
            if (
                not _same_typed_json(observed, control)
                or not _same_typed_json(replay, control)
                or not _same_typed_json(published_manifest_after, published_manifest_before)
            ):
                raise WaveOneRoleBFullReaderError("V3 control replay changed after publication")
            return control


def _v3_replay_published_control_held(
    project_root: Path, model_cache: Path, published: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    _v3_validate_published_executor(project_root, published)
    sealed, _policy, current_executor = _v3_authenticate_plan(
        project_root, model_cache, require_clean_executor=True
    )
    candidate = _v3_build_authenticated_control_held(project_root, model_cache=model_cache)
    if not _same_typed_json(
        current_executor["implementation_ledger"],
        published.get("executor_implementation_ledger"),
    ):
        raise WaveOneRoleBFullReaderError("published V3 implementation ledger drifted")
    candidate["executor_git"] = deepcopy(published["executor_git"])
    candidate.pop("control_identity_sha256", None)
    candidate["control_identity_sha256"] = _canonical_sha256(candidate)
    if not _same_typed_json(candidate, published):
        raise WaveOneRoleBFullReaderError("published V3 control replay drifted")
    receipt, v2_control, archive_root, manifest_index = _v3_authenticate_failed_archive(
        project_root
    )
    ocr_authorities, excluded_native, _metrics = _v3_scan_failed_checkpoints(
        sealed, receipt, v2_control, archive_root, manifest_index
    )
    if len(excluded_native) != 3:
        raise WaveOneRoleBFullReaderError("published V3 excluded-native authority drifted")
    return (
        sealed,
        {item["request"]["request_sha256"]: item for item in ocr_authorities},
        {
            "receipt": receipt,
            "v2_control": v2_control,
            "archive_root": archive_root,
            "manifest_index": manifest_index,
        },
    )


def _v3_context_valid_control_payload(
    project_root: Path, model_cache: Path, payload: bytes
) -> bool:
    try:
        candidate = _json_object(payload, "interrupted V3 full-reader control")
        logical = candidate.get("control_identity_sha256")
        if (
            candidate.get("format_version") != "BANK_CORPUS_WAVE_1_ROLE_B_FULL_READER_CONTROL_V3"
            or not _is_sha256(logical)
            or _canonical_sha256(
                {key: value for key, value in candidate.items() if key != "control_identity_sha256"}
            )
            != logical
        ):
            return False
        _v3_replay_published_control_held(project_root, model_cache, candidate)
    except WaveOneRoleBFullReaderError:
        return False
    return True


def _v3_context_valid_aggregate_payload(project_root: Path, payload: bytes) -> bool:
    try:
        candidate = _json_object(payload, "interrupted V3 aggregate")
        logical = candidate.get("aggregate_identity_sha256")
        published_control = _v3_load_published_control(project_root)
        if (
            candidate.get("format_version") != "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READS_V2"
            or not _is_sha256(logical)
            or _canonical_sha256(
                {
                    key: value
                    for key, value in candidate.items()
                    if key != "aggregate_identity_sha256"
                }
            )
            != logical
            or candidate.get("sealed_plan", {}).get("sha256") != SEALED_PLAN_SHA256
            or candidate.get("control", {}).get("identity_sha256")
            != published_control["control_identity_sha256"]
            or candidate.get("failed_v2_authority", {}).get("archive_portable_manifest_sha256")
            != FAILED_V2_PORTABLE_MANIFEST_SHA256
        ):
            return False
    except WaveOneRoleBFullReaderError:
        return False
    return True


def _v3_sealed_documents(sealed: dict[str, Any]) -> dict[str, dict[str, Any]]:
    documents = {item["document_id"]: item for item in sealed.get("documents", [])}
    if len(documents) != 27:
        raise WaveOneRoleBFullReaderError("V3 sealed document index drifted")
    return documents


def _v3_source_payload(project_root: Path, document: dict[str, Any]) -> tuple[Path, bytes]:
    path = _project_path(
        project_root, document["relative_path"], "receipt-bound selected source PDF"
    )
    payload = _stable_bytes(path, "receipt-bound selected source PDF")
    if (
        len(payload) != document["size_bytes"]
        or sha256_bytes(payload) != document["sha256"]
        or document["document_id"] != f"sha256:{document['sha256']}"
    ):
        raise WaveOneRoleBFullReaderError("V3 source PDF identity drifted")
    return path, payload


def _v3_native_paths(project_root: Path, control: dict[str, Any]) -> tuple[Path, Path]:
    contract = control["native_reader_contract"]
    return (
        _project_path(project_root, contract["causal_policy_path"], "causal native policy"),
        _project_path(project_root, contract["quality_policy_path"], "native quality policy"),
    )


def _v3_build_native_payloads(
    project_root: Path,
    sealed: dict[str, Any],
    control: dict[str, Any],
    expected: dict[str, Any],
    source_bytes: bytes,
) -> tuple[dict[str, Any], dict[str, Any]]:
    causal_path, quality_path = _v3_native_paths(project_root, control)
    try:
        with _v3_network_denied():
            backend, result = build_causal_native_text_evidence_v2(
                request=expected["request"],
                request_sha256=expected["request_sha256"],
                source_bytes=source_bytes,
                document_id=expected["document_id"],
                physical_page=expected["physical_page"],
                provider_runtime_ledger=sealed["causal_native_runtime_ledger"],
                causal_policy_path=causal_path,
                quality_policy_path=quality_path,
                full_control_identity_sha256=control["control_identity_sha256"],
                native_ordering_policy_identity=control["native_reader_contract"][
                    "native_ordering_policy_identity"
                ],
            )
    except CausalNativeTextEvidenceError as error:
        raise WaveOneRoleBFullReaderError(
            "V3 causal native evidence construction failed"
        ) from error
    return backend, result


def _v3_publish_native_payloads(
    project_root: Path,
    control: dict[str, Any],
    expected: dict[str, Any],
    backend: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    backend_ref = _put_object(project_root, _canonical_bytes(backend), suffix=".json")
    if result.get("backend_payload_sha256") != backend_ref["sha256"]:
        raise WaveOneRoleBFullReaderError("V3 native backend/result binding drifted")
    result_ref = _put_object(project_root, _canonical_bytes(result), suffix=".json")
    record = _v3_native_page_record(control, expected, backend_ref, result_ref, result)
    _v3_validate_native_page_record_shape(project_root, control, record)
    return record


def _v3_build_native_record(
    project_root: Path,
    sealed: dict[str, Any],
    control: dict[str, Any],
    expected: dict[str, Any],
    source_bytes: bytes,
) -> dict[str, Any]:
    backend, result = _v3_build_native_payloads(
        project_root, sealed, control, expected, source_bytes
    )
    return _v3_publish_native_payloads(project_root, control, expected, backend, result)


def _v3_replay_native_record(
    project_root: Path,
    sealed: dict[str, Any],
    control: dict[str, Any],
    record: dict[str, Any],
    source_bytes: bytes,
    *,
    publication_pair_path: str | None = None,
) -> None:
    backend, result = _v3_validate_native_page_record_shape(
        project_root,
        control,
        record,
        publication_pair_path=publication_pair_path,
    )
    causal_path, quality_path = _v3_native_paths(project_root, control)
    try:
        with _v3_network_denied():
            validate_causal_native_text_evidence_v2_replay(
                request=record["request"],
                request_sha256=record["request_sha256"],
                source_bytes=source_bytes,
                document_id=record["document_id"],
                physical_page=record["physical_page"],
                provider_runtime_ledger=sealed["causal_native_runtime_ledger"],
                causal_policy_path=causal_path,
                quality_policy_path=quality_path,
                full_control_identity_sha256=control["control_identity_sha256"],
                native_ordering_policy_identity=control["native_reader_contract"][
                    "native_ordering_policy_identity"
                ],
                backend=backend,
                result=result,
            )
    except CausalNativeTextEvidenceError as error:
        raise WaveOneRoleBFullReaderError("V3 causal native source replay failed") from error


def _v3_document_index_payload(
    control: dict[str, Any],
    document_id: str,
    records: list[dict[str, Any]],
    head: str,
) -> dict[str, Any]:
    if [item["request_sha256"] for item in records] != _v3_document_completion_order(
        control, document_id
    ):
        raise WaveOneRoleBFullReaderError("V3 document index is incomplete")
    ordered = sorted(records, key=lambda item: item["request_ordinal"])
    return {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_FULL_DOCUMENT_INDEX_V2",
        "status": "COMPLETE_DOCUMENT_PAGE_REQUEST_ACCOUNTING",
        "claim_boundary": "SOURCE_VISIBLE_PAGE_TEXT_AND_GEOMETRY_EVIDENCE_ONLY",
        "sealed_plan_sha256": SEALED_PLAN_SHA256,
        "control_identity_sha256": control["control_identity_sha256"],
        "document_id": document_id,
        "source_sha256": document_id.removeprefix("sha256:"),
        "final_checkpoint_sha256": head,
        "request_count": len(records),
        "request_set_sha256": _canonical_sha256([item["request_sha256"] for item in ordered]),
        "page_records": ordered,
        "accounting": {
            "source_accounted_page_count": len(records),
            "ocr_page_count": sum(item["route"] == _OCR_ROUTE for item in records),
            "native_page_count": sum(item["route"] == _NATIVE_ROUTE for item in records),
            "unresolved_page_count": sum(item["unresolved"] for item in records),
            "line_axis_count": sum(item["line_axis_count"] for item in records),
            "nonempty_line_axis_count": sum(item["nonempty_line_axis_count"] for item in records),
            "exact_empty_line_axis_count": sum(
                item["exact_empty_line_axis_count"] for item in records
            ),
            "accepted_line_count": sum(item["accepted_line_count"] for item in records),
            "word_token_count": sum(item["word_token_count"] for item in records),
            "quarantined_span_count": sum(item["quarantined_span_count"] for item in records),
            "ordering_quarantined_raw_line_run_count": sum(
                item["ordering_quarantined_raw_line_run_count"] for item in records
            ),
            "ordering_quarantined_raw_word_count": sum(
                item["ordering_quarantined_raw_word_count"] for item in records
            ),
            "noncontiguous_line_identity_count": sum(
                item["noncontiguous_line_identity_count"] for item in records
            ),
            **_ZERO_INTERPRETATION,
        },
    }


def _v3_publish_document_indexes(
    project_root: Path,
    control: dict[str, Any],
    records_by_document: dict[str, list[dict[str, Any]]],
    heads_by_document: dict[str, str | None],
) -> list[dict[str, Any]]:
    candidates = []
    for document_id in sorted(records_by_document):
        head = heads_by_document[document_id]
        if head is None:
            raise WaveOneRoleBFullReaderError("complete V3 document lacks checkpoint head")
        document = _v3_document_index_payload(
            control, document_id, records_by_document[document_id], head
        )
        payload = _canonical_bytes(document)
        digest = sha256_bytes(payload)
        filename = f"{document_id.removeprefix('sha256:')}.json"
        candidates.append((document_id, filename, payload, digest))
    expected_payloads = {filename: payload for _doc, filename, payload, _sha in candidates}
    document_directory = project_root / OUTPUT_RELATIVE_ROOT / "documents"
    manifest_before = _v3_output_live_manifest(project_root)
    directory_records = [
        item for item in manifest_before if item[0] == "d" and item[1] == "documents"
    ]
    if len(directory_records) > 1:
        raise WaveOneRoleBFullReaderError("V3 document-index directory manifest drifted")
    with _v3_bind_output_reads(project_root, manifest_before):
        if directory_records:
            bound, directory_fd = _v3_bound_output_directory(document_directory)
            if not bound or directory_fd is None:
                raise WaveOneRoleBFullReaderError("V3 document-index directory was not bound")
            names = directory_records[0][9]
            if names != sorted(os.listdir(directory_fd)):
                raise WaveOneRoleBFullReaderError("V3 document-index directory name set drifted")
            temporary_names = [name for name in names if name.endswith(".tmp")]
            if len(temporary_names) > 1:
                raise WaveOneRoleBFullReaderError(
                    "V3 document-index directory has multiple temporaries"
                )
            paired_final = None
            if temporary_names:
                match = re.fullmatch(
                    r"\.(?P<final>[0-9a-f]{64}\.json)\.[0-9a-f]{32}\.tmp",
                    temporary_names[0],
                )
                if match is None or match.group("final") not in expected_payloads:
                    raise WaveOneRoleBFullReaderError("V3 document-index temporary target drifted")
                if match.group("final") in names:
                    paired_final = match.group("final")
            for name in names:
                if name.endswith(".tmp"):
                    continue
                expected_payload = expected_payloads.get(name)
                if expected_payload is None:
                    raise WaveOneRoleBFullReaderError(
                        "V3 document-index directory has a foreign entry"
                    )
                payload, identity = _v3_read_nofollow(
                    document_directory / name,
                    "preexisting V3 document index",
                    expected_nlink=(2 if name == paired_final else 1),
                )
                if stat.S_IMODE(identity.st_mode) != 0o444 or payload != expected_payload:
                    raise WaveOneRoleBFullReaderError(
                        "preexisting V3 document index differs from candidate"
                    )
    if not _same_typed_json(_v3_output_live_manifest(project_root), manifest_before):
        raise WaveOneRoleBFullReaderError("V3 output changed during document-index prevalidation")
    if directory_records:
        _v3_recover_publication_directory(
            project_root,
            OUTPUT_RELATIVE_ROOT / "documents",
            create=False,
            allowed_final=lambda candidate: candidate in expected_payloads,
            validate_payload=lambda candidate, payload: (
                candidate in expected_payloads and payload == expected_payloads[candidate]
            ),
            expected_output_manifest=manifest_before,
        )
    references = []
    for document_id, filename, payload, digest in candidates:
        _publish_exclusive(project_root, OUTPUT_RELATIVE_ROOT / "documents", filename, payload)
        references.append(
            {
                "document_id": document_id,
                "path": (Path("documents") / filename).as_posix(),
                "sha256": digest,
                "size_bytes": len(payload),
            }
        )
    if len(references) != 27:
        raise WaveOneRoleBFullReaderError("V3 document index count drifted")
    return references


def _v3_recover_object_publications(
    project_root: Path,
    allowed_paths: set[str],
    *,
    publication_temporary_path: str | None = None,
    expected_output_manifest: list[list[Any]] | None = None,
) -> None:
    if expected_output_manifest is None:
        raise WaveOneRoleBFullReaderError(
            "V3 object recovery requires an authenticated stage manifest"
        )
    if not _same_typed_json(_v3_output_live_manifest(project_root), expected_output_manifest):
        raise WaveOneRoleBFullReaderError("V3 output changed before object recovery")
    directories = {item[1]: item for item in expected_output_manifest if item[0] == "d"}
    objects_record = directories.get("objects")
    if objects_record is None:
        return
    object_names = set(objects_record[9])
    if not object_names:
        _v3_prune_empty_object_prefixes(project_root)
        return
    if object_names != {"sha256"}:
        raise WaveOneRoleBFullReaderError("V3 object hierarchy has a foreign entry")
    sha_record = directories.get("objects/sha256")
    if sha_record is None:
        raise WaveOneRoleBFullReaderError("V3 object root topology drifted")
    for bucket_name in sha_record[9]:
        if re.fullmatch(r"[0-9a-f]{2}", bucket_name) is None:
            raise WaveOneRoleBFullReaderError("V3 object root has a foreign bucket")
        final_grammar = re.compile(rf"(?P<sha>{bucket_name}[0-9a-f]{{62}})\.(?:json|png)")

        def allowed(
            candidate: str,
            grammar: re.Pattern[str] = final_grammar,
            current_bucket_name: str = bucket_name,
        ) -> bool:
            return (
                grammar.fullmatch(candidate) is not None
                and (Path("objects/sha256") / current_bucket_name / candidate).as_posix()
                in allowed_paths
            )

        def valid(
            candidate: str,
            payload: bytes,
            grammar: re.Pattern[str] = final_grammar,
        ) -> bool:
            match = grammar.fullmatch(candidate)
            return match is not None and sha256_bytes(payload) == match.group("sha")

        bucket_output_relative = Path("objects/sha256") / bucket_name
        target_bucket = (
            Path(publication_temporary_path).parent
            if publication_temporary_path is not None
            else None
        )
        if target_bucket == bucket_output_relative:
            _v3_recover_publication_directory(
                project_root,
                OUTPUT_RELATIVE_ROOT / bucket_output_relative,
                create=False,
                allowed_final=allowed,
                validate_payload=valid,
                expected_output_manifest=expected_output_manifest,
            )
        try:
            with _v3_held_output_directory(
                project_root,
                OUTPUT_RELATIVE_ROOT / bucket_output_relative,
                create=False,
            ) as (_directory, directory_fd):
                for name in os.listdir(directory_fd):
                    if not allowed(name):
                        raise WaveOneRoleBFullReaderError(
                            "V3 object CAS bucket contains a foreign entry"
                        )
                    payload, identity = sentinel._hash_open_at(  # noqa: SLF001
                        directory_fd, name
                    )
                    if (
                        stat.S_IMODE(identity.st_mode) != 0o444
                        or identity.st_nlink != 1
                        or not valid(name, payload)
                    ):
                        raise WaveOneRoleBFullReaderError("V3 object CAS entry identity drifted")
        except WaveOneRoleBFullReaderError:
            raise
    _v3_prune_empty_object_prefixes(project_root)


def _v3_prune_empty_object_prefixes(project_root: Path) -> None:
    """Remove only exact empty CAS crash-prefix directories under the held EX lease."""

    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        with _v3_held_output_directory(project_root, OUTPUT_RELATIVE_ROOT, create=False) as (
            _output_root,
            output_fd,
        ):
            try:
                objects_fd = os.open("objects", directory_flags, dir_fd=output_fd)
            except FileNotFoundError:
                return
            try:
                if set(os.listdir(objects_fd)) - {"sha256"}:
                    raise WaveOneRoleBFullReaderError("V3 object prefix contains a foreign entry")
                if "sha256" not in os.listdir(objects_fd):
                    if os.listdir(objects_fd):
                        raise WaveOneRoleBFullReaderError("V3 object prefix topology drifted")
                else:
                    sha_fd = os.open("sha256", directory_flags, dir_fd=objects_fd)
                    try:
                        for name in sorted(os.listdir(sha_fd)):
                            if re.fullmatch(r"[0-9a-f]{2}", name) is None:
                                raise WaveOneRoleBFullReaderError(
                                    "V3 object prefix has a foreign bucket"
                                )
                            bucket_fd = os.open(name, directory_flags, dir_fd=sha_fd)
                            try:
                                identity = os.fstat(bucket_fd)
                                named = os.stat(name, dir_fd=sha_fd, follow_symlinks=False)
                                empty = not os.listdir(bucket_fd)
                                if empty and (
                                    not stat.S_ISDIR(identity.st_mode)
                                    or stat.S_IMODE(identity.st_mode) != 0o755
                                    or identity.st_nlink != 2
                                    or (identity.st_dev, identity.st_ino)
                                    != (named.st_dev, named.st_ino)
                                ):
                                    raise WaveOneRoleBFullReaderError(
                                        "V3 empty object bucket topology drifted"
                                    )
                            finally:
                                os.close(bucket_fd)
                            if empty:
                                os.rmdir(name, dir_fd=sha_fd)
                                os.fsync(sha_fd)
                        sha_empty = not os.listdir(sha_fd)
                        sha_identity = os.fstat(sha_fd)
                    finally:
                        os.close(sha_fd)
                    if sha_empty:
                        if (
                            not stat.S_ISDIR(sha_identity.st_mode)
                            or stat.S_IMODE(sha_identity.st_mode) != 0o755
                            or sha_identity.st_nlink != 2
                        ):
                            raise WaveOneRoleBFullReaderError(
                                "V3 empty object hash root topology drifted"
                            )
                        os.rmdir("sha256", dir_fd=objects_fd)
                        os.fsync(objects_fd)
                objects_empty = not os.listdir(objects_fd)
                objects_identity = os.fstat(objects_fd)
            finally:
                os.close(objects_fd)
            if objects_empty:
                if (
                    not stat.S_ISDIR(objects_identity.st_mode)
                    or stat.S_IMODE(objects_identity.st_mode) != 0o755
                    or objects_identity.st_nlink != 2
                ):
                    raise WaveOneRoleBFullReaderError("V3 empty object prefix topology drifted")
                os.rmdir("objects", dir_fd=output_fd)
                os.fsync(output_fd)
    except OSError as error:
        raise WaveOneRoleBFullReaderError("V3 empty object prefix recovery failed") from error


def _v3_scan_native_orphans(
    project_root: Path,
    control: dict[str, Any],
    checkpointed_native_refs: dict[str, tuple[dict[str, Any], dict[str, Any]]],
    *,
    publication_pair_path: str | None = None,
) -> dict[str, dict[str, Any]]:
    root = project_root / OUTPUT_RELATIVE_ROOT / "objects" / "sha256"
    output_root, file_tokens, directory_tokens, _directory_fds = _v3_require_bound_output()
    if output_root != project_root / OUTPUT_RELATIVE_ROOT:
        raise WaveOneRoleBFullReaderError("V3 orphan scan binding root drifted")
    if "objects/sha256" not in directory_tokens:
        return {}
    expected_index = _v3_control_index(control)
    observed: dict[str, dict[str, Any]] = {}
    json_paths = sorted(
        relative
        for relative in file_tokens
        if Path(relative).parts[:2] == ("objects", "sha256")
        and Path(relative).suffix == ".json"
        and not Path(relative).name.endswith(".tmp")
    )
    for relative_path in json_paths:
        path = output_root / relative_path
        expected_nlink = 2 if relative_path == publication_pair_path else 1
        payload, identity = _v3_read_nofollow(
            path,
            "V3 JSON object during orphan scan",
            expected_nlink=expected_nlink,
        )
        if stat.S_IMODE(identity.st_mode) != 0o444 or identity.st_nlink != expected_nlink:
            raise WaveOneRoleBFullReaderError("V3 orphan object topology drifted")
        value = _json_object(payload, "V3 JSON object during orphan scan")
        if value.get("format_version") != (
            "BANK_CORPUS_WAVE_1_ROLE_B_CAUSAL_NATIVE_PAGE_READ_RESULT_V2"
        ):
            continue
        request_sha = value.get("request_sha256")
        expected = expected_index.get(request_sha)
        if expected is None or expected["route"] != _NATIVE_ROUTE or request_sha in observed:
            raise WaveOneRoleBFullReaderError("V3 native result orphan is foreign or duplicate")
        result_sha = sha256_bytes(payload)
        if path.name != f"{result_sha}.json" or path.parent.name != result_sha[:2]:
            raise WaveOneRoleBFullReaderError("V3 native result orphan CAS path drifted")
        backend_sha = value.get("backend_payload_sha256")
        if not _is_sha256(backend_sha):
            raise WaveOneRoleBFullReaderError("V3 native result orphan backend hash drifted")
        backend_path = root / backend_sha[:2] / f"{backend_sha}.json"
        backend_payload, backend_identity = _v3_read_nofollow(
            backend_path,
            "V3 native orphan backend",
            expected_nlink=(
                2
                if (
                    backend_path.relative_to(project_root / OUTPUT_RELATIVE_ROOT).as_posix()
                    == publication_pair_path
                )
                else 1
            ),
        )
        if (
            stat.S_IMODE(backend_identity.st_mode) != 0o444
            or backend_identity.st_nlink
            != (
                2
                if (
                    backend_path.relative_to(project_root / OUTPUT_RELATIVE_ROOT).as_posix()
                    == publication_pair_path
                )
                else 1
            )
            or sha256_bytes(backend_payload) != backend_sha
        ):
            raise WaveOneRoleBFullReaderError("V3 native orphan backend identity drifted")
        backend_ref = {
            "path": (Path("objects/sha256") / backend_sha[:2] / f"{backend_sha}.json").as_posix(),
            "sha256": backend_sha,
            "size_bytes": len(backend_payload),
        }
        result_ref = {
            "path": (Path("objects/sha256") / result_sha[:2] / f"{result_sha}.json").as_posix(),
            "sha256": result_sha,
            "size_bytes": len(payload),
        }
        checkpointed_refs = checkpointed_native_refs.get(request_sha)
        if checkpointed_refs is not None:
            if not _same_typed_json(
                checkpointed_refs,
                (backend_ref, result_ref),
            ):
                raise WaveOneRoleBFullReaderError(
                    "V3 checkpointed native request has an alternate CAS result"
                )
            continue
        record = _v3_native_page_record(control, expected, backend_ref, result_ref, value)
        _v3_validate_native_page_record_shape(
            project_root,
            control,
            record,
            publication_pair_path=publication_pair_path,
        )
        observed[request_sha] = record
    return observed


def _v3_validate_partial_cas_authority(
    project_root: Path,
    control: dict[str, Any],
    allowed_paths: set[str],
    checkpointed_request_hashes: set[str],
    *,
    publication_pair_path: str | None = None,
    publication_temporary_path: str | None = None,
) -> dict[str, dict[str, Any]]:
    output_root, file_tokens, directory_tokens, _directory_fds = _v3_require_bound_output()
    if output_root != project_root / OUTPUT_RELATIVE_ROOT:
        raise WaveOneRoleBFullReaderError("V3 partial CAS binding root drifted")
    if "objects/sha256" not in directory_tokens:
        return {}
    expected_index = _v3_control_index(control)
    lone_backend_requests: set[str] = set()
    lone_backends: dict[str, dict[str, Any]] = {}
    backend_fields = {
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
        "ordering_policy_identity",
        "coordinate_authority",
        "raw_causal_native_wrapper_payload",
        "ordering_receipt",
        "ocr_fallback_used",
        "source_blank_claimed",
        "safety",
    }
    for relative in sorted(
        item for item in file_tokens if Path(item).parts[:2] == ("objects", "sha256")
    ):
        if relative == publication_temporary_path:
            continue
        path = output_root / relative
        expected_nlink = 2 if relative == publication_pair_path else 1
        payload, stable = _v3_read_nofollow(
            path,
            "V3 partial CAS entry",
            expected_nlink=expected_nlink,
        )
        digest = sha256_bytes(payload)
        if (
            not stat.S_ISREG(stable.st_mode)
            or stat.S_IMODE(stable.st_mode) != 0o444
            or stable.st_nlink != expected_nlink
            or path.parent.name != digest[:2]
            or path.name not in {f"{digest}.json", f"{digest}.png"}
        ):
            raise WaveOneRoleBFullReaderError("V3 partial CAS topology drifted")
        if relative in allowed_paths:
            continue
        if path.suffix != ".json":
            raise WaveOneRoleBFullReaderError("V3 partial CAS contains an unreferenced object")
        backend = _json_object(payload, "V3 lone native backend candidate")
        request_sha = backend.get("request_sha256")
        expected = expected_index.get(request_sha)
        if (
            set(backend) != backend_fields
            or backend.get("format_version")
            != "BANK_CORPUS_WAVE_1_CAUSAL_NATIVE_BACKEND_PAYLOAD_V2"
            or backend.get("claim_boundary")
            != (
                "AUTHENTICATED_CAUSAL_NATIVE_WRAPPER_AND_VISUAL_ORDER_EVIDENCE_"
                "FOR_ONE_EXACT_PAGE_REQUEST_ONLY"
            )
            or expected is None
            or expected["route"] != _NATIVE_ROUTE
            or request_sha in checkpointed_request_hashes
            or request_sha in lone_backend_requests
            or backend.get("document_id") != expected["document_id"]
            or backend.get("source_sha256") != expected["source_sha256"]
            or backend.get("source_size_bytes") != expected["source_size_bytes"]
            or backend.get("physical_page") != expected["physical_page"]
            or backend.get("route") != _NATIVE_ROUTE
            or not _same_typed_json(backend.get("request"), expected["request"])
            or backend.get("full_control_identity_sha256") != control["control_identity_sha256"]
            or backend.get("provider_identity_sha256")
            != expected["request"]["provider_identity_sha256"]
            or not _same_typed_json(
                backend.get("ordering_policy_identity"),
                control["native_reader_contract"]["native_ordering_policy_identity"],
            )
            or backend.get("status") not in _NATIVE_TERMINAL
            or backend.get("ocr_fallback_used") is not False
            or backend.get("source_blank_claimed") is not False
        ):
            raise WaveOneRoleBFullReaderError("V3 partial CAS contains a foreign native backend")
        lone_backend_requests.add(request_sha)
        allowed_paths.add(relative)
        lone_backends[request_sha] = {
            "path": relative,
            "payload": payload,
            "backend": backend,
        }
    return lone_backends


def _v3_read_partial_run_state(
    project_root: Path,
    control: dict[str, Any],
    document_ids: list[str],
    ocr_authority_index: dict[str, dict[str, Any]],
    archive_root: Path,
    manifest_index: dict[str, list[Any]],
    *,
    publication_pair_path: str | None,
    publication_target_path: str | None,
    publication_temporary_path: str | None,
    output_manifest: list[list[Any]],
) -> tuple[
    dict[str, list[dict[str, Any]]],
    dict[str, str | None],
    set[str],
    dict[str, dict[str, Any]],
    set[str],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    with _v3_bind_output_reads(project_root, output_manifest):
        records_by_document: dict[str, list[dict[str, Any]]] = {}
        heads_by_document: dict[str, str | None] = {}
        for document_id in document_ids:
            records, head = _v3_load_document_checkpoints(
                project_root,
                control,
                document_id,
                ocr_authority_index,
                archive_root,
                manifest_index,
                recover_temporaries=False,
                publication_pair_path=publication_pair_path,
                expected_output_manifest=output_manifest,
                observe_temporary=True,
            )
            records_by_document[document_id] = records
            heads_by_document[document_id] = head
        completed = {
            item["request_sha256"] for records in records_by_document.values() for item in records
        }
        expected_index = _v3_control_index(control)
        if not completed <= set(expected_index):
            raise WaveOneRoleBFullReaderError("V3 checkpoints contain foreign requests")
        allowed_object_paths = {
            reference["path"]
            for authority in ocr_authority_index.values()
            for reference in authority["source_refs"].values()
        }
        allowed_object_paths.update(
            reference["path"]
            for records in records_by_document.values()
            for record in records
            for key in ("render_ref", "backend_payload_ref", "result_ref")
            if (reference := record[key]) is not None
        )
        checkpointed_native_refs = {
            item["request_sha256"]: (
                item["backend_payload_ref"],
                item["result_ref"],
            )
            for records in records_by_document.values()
            for item in records
            if item["route"] == _NATIVE_ROUTE
        }
        orphans = _v3_scan_native_orphans(
            project_root,
            control,
            checkpointed_native_refs,
            publication_pair_path=publication_pair_path,
        )
        allowed_object_paths.update(
            reference["path"]
            for record in orphans.values()
            for reference in (
                record["backend_payload_ref"],
                record["result_ref"],
            )
        )
        if (
            publication_pair_path is None
            and publication_target_path is not None
            and publication_target_path.startswith("objects/sha256/")
        ):
            allowed_object_paths.add(publication_target_path)
        lone_backends = _v3_validate_partial_cas_authority(
            project_root,
            control,
            allowed_object_paths,
            completed,
            publication_pair_path=publication_pair_path,
            publication_temporary_path=publication_temporary_path,
        )
        residue_requests = set(orphans) | set(lone_backends)
        completed_ocr_count = sum(
            expected_index[request_sha]["route"] == _OCR_ROUTE for request_sha in completed
        )
        missing_native = _v3_pending_native_schedule(expected_index, completed)
        if len(residue_requests) > 1 or (
            residue_requests
            and (
                completed_ocr_count != 1_356
                or not missing_native
                or residue_requests != {missing_native[0]["request_sha256"]}
            )
        ):
            raise WaveOneRoleBFullReaderError(
                "V3 native CAS residue violates the singular next-request order"
            )
    return (
        records_by_document,
        heads_by_document,
        completed,
        expected_index,
        allowed_object_paths,
        orphans,
        lone_backends,
    )


def _v3_pending_native_schedule(
    expected_index: dict[str, dict[str, Any]], completed: set[str]
) -> list[dict[str, Any]]:
    return sorted(
        (
            item
            for item in expected_index.values()
            if item["route"] == _NATIVE_ROUTE and item["request_sha256"] not in completed
        ),
        key=lambda item: item["request_ordinal"],
    )


def _v3_replay_partial_native_state(
    project_root: Path,
    sealed: dict[str, Any],
    control: dict[str, Any],
    records_by_document: dict[str, list[dict[str, Any]]],
    orphans: dict[str, dict[str, Any]],
    lone_backends: dict[str, dict[str, Any]],
    *,
    publication_pair_path: str | None,
    output_manifest: list[list[Any]],
) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    native_records = [
        item
        for records in records_by_document.values()
        for item in records
        if item["route"] == _NATIVE_ROUTE
    ] + list(orphans.values())
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in native_records:
        grouped[record["document_id"]].append(record)
    documents = _v3_sealed_documents(sealed)
    expected_index = _v3_control_index(control)
    prebuilt: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    with _v3_bind_output_reads(project_root, output_manifest):
        for document_id in sorted(
            set(grouped)
            | {expected_index[request_sha]["document_id"] for request_sha in lone_backends}
        ):
            source_path, source_bytes = _v3_source_payload(project_root, documents[document_id])
            for record in sorted(
                grouped[document_id],
                key=lambda item: item["request_ordinal"],
            ):
                _v3_replay_native_record(
                    project_root,
                    sealed,
                    control,
                    record,
                    source_bytes,
                    publication_pair_path=publication_pair_path,
                )
            for request_sha, candidate in lone_backends.items():
                expected = expected_index[request_sha]
                if expected["document_id"] != document_id:
                    continue
                backend, result = _v3_build_native_payloads(
                    project_root,
                    sealed,
                    control,
                    expected,
                    source_bytes,
                )
                if _canonical_bytes(backend) != candidate["payload"]:
                    raise WaveOneRoleBFullReaderError(
                        "V3 lone native backend differs from source replay"
                    )
                prebuilt[request_sha] = (backend, result)
            if _stable_bytes(source_path, "receipt-bound selected source PDF") != source_bytes:
                raise WaveOneRoleBFullReaderError("V3 source changed during resume native replay")
    if set(prebuilt) != set(lone_backends):
        raise WaveOneRoleBFullReaderError("V3 lone native backend source replay accounting drifted")
    return prebuilt


def run_authenticated_full_reader(project_root: Path, *, model_cache: Path) -> dict[str, Any]:
    with _v3_mutation_entry():
        return _run_authenticated_full_reader_mutating(project_root, model_cache=model_cache)


def _run_authenticated_full_reader_mutating(
    project_root: Path, *, model_cache: Path
) -> dict[str, Any]:
    """Adopt authenticated OCR evidence and freshly read all native requests."""

    project_root = project_root.resolve()
    model_cache = model_cache.resolve()
    initial_sealed, policy, _executor = _v3_authenticate_plan(
        project_root, model_cache, require_clean_executor=True
    )
    document_ids = sorted(item["document_id"] for item in initial_sealed["documents"])
    with _v3_failed_archive_locks(project_root, document_ids):
        with ExitStack() as output_locks:
            output_locks.enter_context(_v3_execution_lease(project_root, create=False))
            interrupted_relative, preflight_manifest = _v3_preflight_output_temporaries(
                project_root, document_ids, stage="run"
            )
            publication_pair_path = _v3_publication_pair_path(project_root, interrupted_relative)
            publication_target_path = _v3_publication_target_path(interrupted_relative)
            _v3_recover_publication_directory(
                project_root,
                OUTPUT_RELATIVE_ROOT,
                create=False,
                allowed_final=lambda candidate: candidate == "full-reader-execution-control.json",
                validate_payload=lambda candidate, payload: (
                    candidate == "full-reader-execution-control.json"
                    and _v3_context_valid_control_payload(project_root, model_cache, payload)
                ),
                expected_output_manifest=preflight_manifest,
            )
            if publication_target_path == "full-reader-execution-control.json":
                interrupted_relative = None
                publication_pair_path = None
                publication_target_path = None
                preflight_manifest = _v3_output_live_manifest(project_root)
            if preflight_manifest is None:
                raise WaveOneRoleBFullReaderError("V3 run output snapshot is absent")
            with _v3_bind_output_reads(project_root, preflight_manifest):
                control = _v3_load_published_control(project_root)
                sealed, ocr_authority_index, failed = _v3_replay_published_control_held(
                    project_root, model_cache, control
                )
            if not _same_typed_json(_v3_output_live_manifest(project_root), preflight_manifest):
                raise WaveOneRoleBFullReaderError("V3 output changed during control replay")
            archive_root = failed["archive_root"]
            manifest_index = failed["manifest_index"]
            _v3_ensure_capacity(project_root, policy["execution"]["minimum_free_space_bytes"])
            lock_state = _v3_output_lock_state(project_root, document_ids)
            if lock_state not in {
                "CONTROL_ONLY_BOOTSTRAP",
                "PARTIAL_LOCK_BOOTSTRAP",
                "FULL_LOCK_SET",
            }:
                raise WaveOneRoleBFullReaderError("V3 output lock state drifted")
            output_locks.enter_context(_v3_document_locks(project_root, document_ids))
            _v3_validate_output_lock_topology(project_root, document_ids)
            (
                repeated_interrupted_relative,
                preflight_manifest,
            ) = _v3_preflight_output_temporaries(project_root, document_ids, stage="run")
            if repeated_interrupted_relative != interrupted_relative:
                raise WaveOneRoleBFullReaderError(
                    "V3 run publication state changed during lock acquisition"
                )
            assert preflight_manifest is not None
            with _v3_bind_output_reads(project_root, preflight_manifest):
                rebound_control = _v3_load_published_control(project_root)
            if not _same_typed_json(rebound_control, control):
                raise WaveOneRoleBFullReaderError(
                    "V3 control changed during document-lock acquisition"
                )
            _v3_ensure_capacity(project_root, policy["execution"]["minimum_free_space_bytes"])
            (
                records_by_document,
                heads_by_document,
                completed,
                expected_index,
                allowed_object_paths,
                orphans,
                lone_backends,
            ) = _v3_read_partial_run_state(
                project_root,
                control,
                document_ids,
                ocr_authority_index,
                archive_root,
                manifest_index,
                publication_pair_path=publication_pair_path,
                publication_target_path=publication_target_path,
                publication_temporary_path=interrupted_relative,
                output_manifest=preflight_manifest,
            )
            prebuilt_native_payloads: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
            if len(completed) != 1_449:
                prebuilt_native_payloads = _v3_replay_partial_native_state(
                    project_root,
                    sealed,
                    control,
                    records_by_document,
                    orphans,
                    lone_backends,
                    publication_pair_path=publication_pair_path,
                    output_manifest=preflight_manifest,
                )
            if publication_target_path is not None and publication_target_path.startswith(
                "checkpoints/"
            ):
                target_parts = Path(publication_target_path).parts
                if len(target_parts) != 3:
                    raise WaveOneRoleBFullReaderError("V3 checkpoint recovery target drifted")
                checkpoint_document_id = f"sha256:{target_parts[1]}"
                checkpoint_name = target_parts[2]
                checkpoint_match = re.fullmatch(
                    r"[0-9]{4}-(?P<sha>[0-9a-f]{64})\.json",
                    checkpoint_name,
                )
                if checkpoint_match is None:
                    raise WaveOneRoleBFullReaderError("V3 checkpoint recovery filename drifted")
                _v3_recover_publication_directory(
                    project_root,
                    OUTPUT_RELATIVE_ROOT / Path(*target_parts[:-1]),
                    create=False,
                    allowed_final=lambda candidate: candidate == checkpoint_name,
                    validate_payload=lambda candidate, payload: (
                        candidate == checkpoint_name
                        and sha256_bytes(payload) == checkpoint_match.group("sha")
                    ),
                    expected_output_manifest=preflight_manifest,
                )
                recovered_manifest = _v3_output_live_manifest(project_root)
                with _v3_bind_output_reads(project_root, recovered_manifest):
                    recovered_records, recovered_head = _v3_load_document_checkpoints(
                        project_root,
                        control,
                        checkpoint_document_id,
                        ocr_authority_index,
                        archive_root,
                        manifest_index,
                        recover_temporaries=False,
                        expected_output_manifest=recovered_manifest,
                        observe_temporary=False,
                    )
                if (
                    not _same_typed_json(
                        recovered_records,
                        records_by_document[checkpoint_document_id],
                    )
                    or recovered_head != heads_by_document[checkpoint_document_id]
                ):
                    raise WaveOneRoleBFullReaderError(
                        "V3 checkpoint recovery changed authenticated accounting"
                    )
                interrupted_relative = None
                publication_pair_path = None
                publication_target_path = None
                preflight_manifest = recovered_manifest
            _v3_recover_object_publications(
                project_root,
                allowed_object_paths,
                publication_temporary_path=interrupted_relative,
                expected_output_manifest=preflight_manifest,
            )
            if len(completed) == 1_449:
                if orphans:
                    raise WaveOneRoleBFullReaderError(
                        "completed V3 execution has an uncheckpointed native orphan"
                    )
                indexes = _v3_publish_document_indexes(
                    project_root,
                    control,
                    records_by_document,
                    heads_by_document,
                )
                completed_manifest_before = _v3_output_live_manifest(project_root)
                aggregate_present = _v3_manifest_has_file(
                    completed_manifest_before, "full-reader-aggregate.json"
                )
                with _v3_bind_output_reads(project_root, completed_manifest_before):
                    bound_control = _v3_load_published_control(project_root)
                    if not _same_typed_json(bound_control, control):
                        raise WaveOneRoleBFullReaderError(
                            "V3 control changed before structural resume replay"
                        )
                    aggregate = _v3_build_aggregate_held(
                        project_root,
                        model_cache,
                        bound_control,
                        deep_source_replay=False,
                    )
                completed_manifest_after = _v3_output_live_manifest(project_root)
                if not _same_typed_json(completed_manifest_after, completed_manifest_before):
                    raise WaveOneRoleBFullReaderError(
                        "completed V3 output changed during structural replay"
                    )
                return {
                    "status": (
                        "COMPLETE_V3_PAGE_REQUEST_EXECUTION_RESUME_WITH_ZERO_NEW_"
                        "NATIVE_EVIDENCE_BUILDS"
                    ),
                    "control_identity_sha256": control["control_identity_sha256"],
                    "aggregate_identity_sha256": aggregate["aggregate_identity_sha256"],
                    "authenticated_published_aggregate_present": aggregate_present,
                    "checkpoint_count": 1_449,
                    "ocr_adopted_during_command": 0,
                    "native_read_during_command": 0,
                    "native_orphan_adopted_during_command": 0,
                    "document_index_count": len(indexes),
                    "output_live_manifest_sha256": _canonical_sha256(completed_manifest_after),
                }
            documents = _v3_sealed_documents(sealed)
            adopted_ocr_count = 0
            copied_object_hashes: set[str] = set()
            for authority in sorted(
                ocr_authority_index.values(),
                key=lambda item: item["request"]["request_ordinal"],
            ):
                request_sha = authority["request"]["request_sha256"]
                if request_sha in completed:
                    copied_object_hashes.update(
                        reference["sha256"] for reference in authority["source_refs"].values()
                    )
                    continue
                _v3_ensure_capacity(project_root, policy["execution"]["minimum_free_space_bytes"])
                copied_refs = {}
                for key, suffix in (
                    ("render_ref", ".png"),
                    ("backend_payload_ref", ".json"),
                    ("result_ref", ".json"),
                ):
                    copied_refs[key] = _v3_copy_archive_object(
                        project_root,
                        archive_root,
                        manifest_index,
                        authority["source_refs"][key],
                        suffix,
                        authority["source_ref_identities"][key],
                    )
                    copied_object_hashes.add(copied_refs[key]["sha256"])
                record = _v3_ocr_page_record(control, authority, copied_refs)
                _v3_append_checkpoint(
                    project_root,
                    control,
                    records_by_document,
                    heads_by_document,
                    record,
                    ocr_authority_index,
                    archive_root,
                    manifest_index,
                )
                completed.add(request_sha)
                adopted_ocr_count += 1
            if len(copied_object_hashes) != 4_068:
                raise WaveOneRoleBFullReaderError("V3 OCR copied-object count drifted")
            completed_ocr = {
                request_sha
                for request_sha in completed
                if expected_index[request_sha]["route"] == _OCR_ROUTE
            }
            if completed_ocr != set(ocr_authority_index):
                raise WaveOneRoleBFullReaderError("V3 OCR adoption is incomplete")
            _v3_ensure_capacity(project_root, policy["execution"]["minimum_free_space_bytes"])
            native_new = 0
            native_orphan_adopted = 0
            native_requests = _v3_pending_native_schedule(expected_index, completed)
            held_sources: dict[str, tuple[Path, bytes]] = {}
            for expected in native_requests:
                document_id = expected["document_id"]
                _v3_ensure_capacity(project_root, policy["execution"]["minimum_free_space_bytes"])
                if document_id not in held_sources:
                    held_sources[document_id] = _v3_source_payload(
                        project_root, documents[document_id]
                    )
                _source_path, source_bytes = held_sources[document_id]
                request_sha = expected["request_sha256"]
                orphan = orphans.get(request_sha)
                prebuilt = prebuilt_native_payloads.get(request_sha)
                if orphan is not None:
                    record = orphan
                    native_orphan_adopted += 1
                elif prebuilt is not None:
                    record = _v3_publish_native_payloads(
                        project_root,
                        control,
                        expected,
                        prebuilt[0],
                        prebuilt[1],
                    )
                    native_new += 1
                else:
                    record = _v3_build_native_record(
                        project_root, sealed, control, expected, source_bytes
                    )
                    native_new += 1
                _v3_append_checkpoint(
                    project_root,
                    control,
                    records_by_document,
                    heads_by_document,
                    record,
                    ocr_authority_index,
                    archive_root,
                    manifest_index,
                )
                completed.add(request_sha)
            for source_path, source_bytes in held_sources.values():
                if _stable_bytes(source_path, "receipt-bound selected source PDF") != source_bytes:
                    raise WaveOneRoleBFullReaderError("V3 source changed during native reads")
            if len(completed) != 1_449:
                raise WaveOneRoleBFullReaderError("V3 did not checkpoint all requests")
            indexes = _v3_publish_document_indexes(
                project_root, control, records_by_document, heads_by_document
            )
            final_manifest_before = _v3_output_live_manifest(project_root)
            with _v3_bind_output_reads(project_root, final_manifest_before):
                structural_aggregate = _v3_build_aggregate_held(
                    project_root,
                    model_cache,
                    control,
                    deep_source_replay=False,
                )
            final_manifest_after = _v3_output_live_manifest(project_root)
            if not _same_typed_json(final_manifest_after, final_manifest_before):
                raise WaveOneRoleBFullReaderError(
                    "V3 output changed during final structural replay"
                )
            return {
                "status": "COMPLETE_V3_PAGE_REQUEST_EXECUTION",
                "control_identity_sha256": control["control_identity_sha256"],
                "checkpoint_count": 1_449,
                "ocr_adopted_during_command": adopted_ocr_count,
                "native_read_during_command": native_new,
                "native_orphan_adopted_during_command": native_orphan_adopted,
                "document_index_count": len(indexes),
                "authenticated_published_aggregate_present": False,
                "aggregate_identity_sha256": structural_aggregate["aggregate_identity_sha256"],
                "output_live_manifest_sha256": _canonical_sha256(final_manifest_after),
            }


def _v3_read_document_index(project_root: Path, reference: dict[str, Any]) -> dict[str, Any]:
    if (
        not isinstance(reference, dict)
        or set(reference) != {"document_id", "path", "sha256", "size_bytes"}
        or reference.get("path")
        != f"documents/{reference.get('document_id', '').removeprefix('sha256:')}.json"
    ):
        raise WaveOneRoleBFullReaderError("V3 document index reference drifted")
    path = _project_path(
        project_root, OUTPUT_RELATIVE_ROOT / reference["path"], "V3 document index"
    )
    payload, identity = _v3_read_nofollow(path, "V3 document index")
    if (
        stat.S_IMODE(identity.st_mode) != 0o444
        or identity.st_nlink != 1
        or len(payload) != reference["size_bytes"]
        or sha256_bytes(payload) != reference["sha256"]
    ):
        raise WaveOneRoleBFullReaderError("V3 document index object drifted")
    return _json_object(payload, "V3 document index")


def _v3_validate_checkpoint_and_index_topology(project_root: Path, control: dict[str, Any]) -> None:
    output_root, file_tokens, directory_tokens, _directory_fds = _v3_require_bound_output()
    if output_root != project_root / OUTPUT_RELATIVE_ROOT:
        raise WaveOneRoleBFullReaderError("V3 topology binding root drifted")
    document_ids = sorted(item["document_id"] for item in control["documents"])
    expected_document_names = {item.removeprefix("sha256:") for item in document_ids}
    checkpoint_root = directory_tokens.get("checkpoints")
    document_root = directory_tokens.get("documents")
    if (
        checkpoint_root is None
        or document_root is None
        or set(checkpoint_root[9]) != expected_document_names
    ):
        raise WaveOneRoleBFullReaderError("V3 checkpoint document-directory set drifted")
    observed_checkpoint_directories = {
        Path(relative).parts[1]
        for relative in directory_tokens
        if len(Path(relative).parts) == 2 and Path(relative).parts[0] == "checkpoints"
    }
    if observed_checkpoint_directories != expected_document_names:
        raise WaveOneRoleBFullReaderError("V3 checkpoint child-directory set drifted")
    for document_id in document_ids:
        source_sha = document_id.removeprefix("sha256:")
        relative = f"checkpoints/{source_sha}"
        directory = directory_tokens.get(relative)
        expected_count = len(_v3_document_completion_order(control, document_id))
        if (
            directory is None
            or directory[2] != 0o755
            or directory[3] != 2
            or len(directory[9]) != expected_count
        ):
            raise WaveOneRoleBFullReaderError("V3 checkpoint document directory topology drifted")
        for name in directory[9]:
            token = file_tokens.get(f"{relative}/{name}")
            if (
                re.fullmatch(r"[0-9]{4}-[0-9a-f]{64}\.json", name) is None
                or token is None
                or token[2] != 0o444
                or token[3] != 1
            ):
                raise WaveOneRoleBFullReaderError("V3 checkpoint file topology drifted")
    expected_indexes = {f"{item}.json" for item in expected_document_names}
    if set(document_root[9]) != expected_indexes:
        raise WaveOneRoleBFullReaderError("V3 document-index filename set drifted")
    for name in expected_indexes:
        token = file_tokens.get(f"documents/{name}")
        if token is None or token[2] != 0o444 or token[3] != 1:
            raise WaveOneRoleBFullReaderError("V3 document-index topology drifted")


@contextmanager
def _v3_final_directory_snapshot(
    project_root: Path, records: list[dict[str, Any]]
) -> Iterator[None]:
    output_root, _file_tokens, directory_tokens, _directory_fds = _v3_require_bound_output()
    if output_root != project_root / OUTPUT_RELATIVE_ROOT:
        raise WaveOneRoleBFullReaderError("V3 final snapshot binding root drifted")
    bucket_names = {
        reference["sha256"][:2]
        for record in records
        for key in ("render_ref", "backend_payload_ref", "result_ref")
        if (reference := record[key]) is not None
    }
    document_names = {record["document_id"].removeprefix("sha256:") for record in records}
    expected_links = {
        ".": 6,
        "locks": 3,
        "locks/documents": 2,
        "objects": 3,
        "objects/sha256": 2 + len(bucket_names),
        "checkpoints": 29,
        "documents": 2,
        **{f"objects/sha256/{bucket}": 2 for bucket in bucket_names},
        **{f"checkpoints/{document}": 2 for document in document_names},
    }
    if set(directory_tokens) != set(expected_links):
        raise WaveOneRoleBFullReaderError("V3 final output directory set drifted")
    for relative, links in expected_links.items():
        token = directory_tokens[relative]
        if token[2] != 0o755 or token[3] != links:
            raise WaveOneRoleBFullReaderError("V3 final output directory topology drifted")
    yield


def _v3_output_inventory(
    project_root: Path,
    records: list[dict[str, Any]],
    *,
    aggregate_allowed: bool,
    ignored_root_temporary: str | None = None,
) -> dict[str, int]:
    with _v3_final_directory_snapshot(project_root, records):
        return _v3_output_inventory_bound(
            project_root,
            records,
            aggregate_allowed=aggregate_allowed,
            ignored_root_temporary=ignored_root_temporary,
        )


def _v3_output_inventory_bound(
    project_root: Path,
    records: list[dict[str, Any]],
    *,
    aggregate_allowed: bool,
    ignored_root_temporary: str | None = None,
) -> dict[str, int]:
    output_root, file_tokens, directory_tokens, _directory_fds = _v3_require_bound_output()
    if output_root != project_root / OUTPUT_RELATIVE_ROOT:
        raise WaveOneRoleBFullReaderError("V3 inventory binding root drifted")
    expected_root = {
        "full-reader-execution-control.json",
        "locks",
        "objects",
        "checkpoints",
        "documents",
    }
    if aggregate_allowed:
        expected_root.add("full-reader-aggregate.json")
    root_token = directory_tokens.get(".")
    if root_token is None:
        raise WaveOneRoleBFullReaderError("V3 output root token is absent")
    names = set(root_token[9])
    if ignored_root_temporary is not None:
        if ignored_root_temporary not in names:
            raise WaveOneRoleBFullReaderError("expected V3 root publication temporary is absent")
        names.remove(ignored_root_temporary)
    if names not in (expected_root, expected_root - {"full-reader-aggregate.json"}):
        raise WaveOneRoleBFullReaderError("V3 output root contains a foreign entry")
    references = []
    for record in records:
        for key in ("render_ref", "backend_payload_ref", "result_ref"):
            reference = record[key]
            if reference is not None:
                references.append(reference)
    referenced_paths = {reference["path"] for reference in references}
    referenced_hashes = {reference["sha256"] for reference in references}
    if (
        len(references) != 4_254
        or len(referenced_paths) != 4_254
        or len(referenced_hashes) != 4_254
    ):
        raise WaveOneRoleBFullReaderError("V3 evidence reference count drifted")
    expected_bucket_files: dict[str, set[str]] = defaultdict(set)
    for reference in references:
        relative = Path(reference["path"])
        expected_bucket_files[relative.parent.name].add(relative.name)
    objects_parent = directory_tokens.get("objects")
    object_root = directory_tokens.get("objects/sha256")
    if (
        objects_parent is None
        or set(objects_parent[9]) != {"sha256"}
        or object_root is None
        or set(object_root[9]) != set(expected_bucket_files)
    ):
        raise WaveOneRoleBFullReaderError("V3 object CAS bucket set drifted")
    for bucket, expected_files in expected_bucket_files.items():
        bucket_token = directory_tokens.get(f"objects/sha256/{bucket}")
        if (
            bucket_token is None
            or bucket_token[2] != 0o755
            or bucket_token[3] != 2
            or set(bucket_token[9]) != expected_files
        ):
            raise WaveOneRoleBFullReaderError("V3 object CAS bucket topology drifted")
    observed_paths = set()
    observed_inodes = set()
    object_files = {
        relative: token
        for relative, token in file_tokens.items()
        if Path(relative).parts[:2] == ("objects", "sha256")
    }
    for relative, token in sorted(object_files.items()):
        path = output_root / relative
        relative_path = Path(relative)
        if (
            len(relative_path.parts) != 4
            or token[2] != 0o444
            or token[3] != 1
            or re.fullmatch(r"[0-9a-f]{64}\.(?:json|png)", relative_path.name) is None
            or relative_path.parent.name != relative_path.name[:2]
        ):
            raise WaveOneRoleBFullReaderError("V3 object CAS file topology drifted")
        payload, stable = _v3_read_nofollow(path, "V3 object inventory entry")
        digest = sha256_bytes(payload)
        if relative_path.name not in {f"{digest}.json", f"{digest}.png"}:
            raise WaveOneRoleBFullReaderError("V3 object CAS content drifted")
        observed_paths.add(relative)
        inode = (stable.st_dev, stable.st_ino)
        if inode in observed_inodes:
            raise WaveOneRoleBFullReaderError("V3 object CAS contains a hardlink")
        observed_inodes.add(inode)
    if observed_paths != referenced_paths or len(observed_inodes) != 4_254:
        raise WaveOneRoleBFullReaderError("V3 object CAS accounting drifted")
    return {
        "referenced_object_count": len(references),
        "unique_object_count": len(observed_paths),
    }


def _v3_replay_all_ocr_renders(
    project_root: Path,
    sealed: dict[str, Any],
    records: list[dict[str, Any]],
) -> None:
    ocr_records = [item for item in records if item["route"] == _OCR_ROUTE]
    if len(ocr_records) != 1_356:
        raise WaveOneRoleBFullReaderError("V3 OCR rerender request count drifted")
    documents = _v3_sealed_documents(sealed)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in ocr_records:
        grouped[record["document_id"]].append(record)
    for document_id in sorted(grouped):
        source_path, source_bytes = _v3_source_payload(project_root, documents[document_id])
        pdf = fitz.open(stream=source_bytes, filetype="pdf")
        try:
            for record in sorted(grouped[document_id], key=lambda item: item["request_ordinal"]):
                dpi = record["request"]["render_specification"]["dpi"]
                rendered = render_composited_displayed_page(
                    pdf.load_page(record["physical_page"] - 1), dpi=dpi
                )
                expected_ref = {
                    "path": (
                        Path("objects/sha256") / rendered.sha256[:2] / f"{rendered.sha256}.png"
                    ).as_posix(),
                    "sha256": rendered.sha256,
                    "size_bytes": rendered.size_bytes,
                }
                stored, _ = _v3_read_object(
                    project_root, expected_ref, ".png", "V3 OCR rerender object"
                )
                result_payload, _ = _v3_read_object(
                    project_root,
                    record["result_ref"],
                    ".json",
                    "V3 OCR rerender result",
                )
                result = _json_object(result_payload, "V3 OCR rerender result")
                if (
                    stored != rendered.payload
                    or not _same_typed_json(record["render_ref"], expected_ref)
                    or not _same_typed_json(
                        result.get("coordinate_authority"),
                        public_coordinate_authority(rendered.coordinate_authority),
                    )
                ):
                    raise WaveOneRoleBFullReaderError(
                        "V3 OCR render differs from authenticated source"
                    )
        finally:
            pdf.close()
        if _stable_bytes(source_path, "receipt-bound selected source PDF") != source_bytes:
            raise WaveOneRoleBFullReaderError("V3 source changed during OCR rerender")


def _v3_replay_all_native(
    project_root: Path,
    sealed: dict[str, Any],
    control: dict[str, Any],
    records: list[dict[str, Any]],
) -> None:
    native_records = [item for item in records if item["route"] == _NATIVE_ROUTE]
    if len(native_records) != 93:
        raise WaveOneRoleBFullReaderError("V3 native replay request count drifted")
    documents = _v3_sealed_documents(sealed)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in native_records:
        grouped[record["document_id"]].append(record)
    for document_id in sorted(grouped):
        source_path, source_bytes = _v3_source_payload(project_root, documents[document_id])
        for record in sorted(grouped[document_id], key=lambda item: item["request_ordinal"]):
            _v3_replay_native_record(project_root, sealed, control, record, source_bytes)
        if _stable_bytes(source_path, "receipt-bound selected source PDF") != source_bytes:
            raise WaveOneRoleBFullReaderError("V3 source changed during native replay")


def _v3_build_aggregate_held(
    project_root: Path,
    model_cache: Path,
    control: dict[str, Any],
    *,
    deep_source_replay: bool,
    aggregate_publication_temporary: str | None = None,
) -> dict[str, Any]:
    sealed, ocr_authority_index, failed = _v3_replay_published_control_held(
        project_root, model_cache, control
    )
    archive_root = failed["archive_root"]
    manifest_index = failed["manifest_index"]
    document_ids = sorted(item["document_id"] for item in sealed["documents"])
    _v3_validate_output_lock_topology(project_root, document_ids)
    _v3_validate_checkpoint_and_index_topology(project_root, control)
    records = []
    document_references = []
    for document_id in document_ids:
        document_records, head = _v3_load_document_checkpoints(
            project_root,
            control,
            document_id,
            ocr_authority_index,
            archive_root,
            manifest_index,
            recover_temporaries=False,
        )
        if head is None:
            raise WaveOneRoleBFullReaderError("complete V3 document lacks a checkpoint")
        expected_document = _v3_document_index_payload(control, document_id, document_records, head)
        payload = _canonical_bytes(expected_document)
        filename = f"{document_id.removeprefix('sha256:')}.json"
        reference = {
            "document_id": document_id,
            "path": (Path("documents") / filename).as_posix(),
            "sha256": sha256_bytes(payload),
            "size_bytes": len(payload),
        }
        observed_document = _v3_read_document_index(project_root, reference)
        if not _same_typed_json(observed_document, expected_document):
            raise WaveOneRoleBFullReaderError("V3 document index replay drifted")
        records.extend(document_records)
        document_references.append(reference)
    records.sort(key=lambda item: item["request_ordinal"])
    expected_index = _v3_control_index(control)
    if (
        len(records) != 1_449
        or [item["request_ordinal"] for item in records] != list(range(1, 1_450))
        or {item["request_sha256"] for item in records} != set(expected_index)
    ):
        raise WaveOneRoleBFullReaderError("V3 full request accounting drifted")
    if deep_source_replay:
        _v3_replay_all_ocr_renders(project_root, sealed, records)
        _v3_replay_all_native(project_root, sealed, control, records)
    inventory = _v3_output_inventory(
        project_root,
        records,
        aggregate_allowed=True,
        ignored_root_temporary=aggregate_publication_temporary,
    )
    outcomes = Counter(item["status"] for item in records)
    routes = Counter(item["route"] for item in records)
    origins = Counter(item["origin"] for item in records)
    if (
        routes != {_OCR_ROUTE: 1_356, _NATIVE_ROUTE: 93}
        or origins
        != {
            "AUTHENTICATED_FAILED_V2_OCR_EVIDENCE_BYTE_COPY": 1_356,
            "FRESH_SEALED_CAUSAL_NATIVE_TEXT_GATE_V2": 93,
        }
        or outcomes["OCR_WORD_BOX_READ_COMPLETE"] != 1_299
        or outcomes["UNRESOLVED_OCR_WORD_BOX_GEOMETRY"] != 57
    ):
        raise WaveOneRoleBFullReaderError("V3 route/origin/OCR outcome partition drifted")
    ocr_records = [item for item in records if item["route"] == _OCR_ROUTE]
    native_records = [item for item in records if item["route"] == _NATIVE_ROUTE]
    ocr_dpi = Counter(item["request"]["render_specification"]["dpi"] for item in ocr_records)
    native_dpi = Counter(
        "NOT_APPLICABLE"
        if item["request"].get("render_specification") is None
        else "UNEXPECTED_RENDER_SPECIFICATION"
        for item in native_records
    )
    ocr_upstream_origins = Counter(item["upstream_origin"] for item in ocr_records)
    native_outcomes = Counter(item["status"] for item in native_records)
    if (
        sum(item["line_axis_count"] for item in ocr_records) != 96_369
        or sum(item["nonempty_line_axis_count"] for item in ocr_records) != 96_304
        or sum(item["exact_empty_line_axis_count"] for item in ocr_records) != 65
        or sum(item["accepted_line_count"] for item in ocr_records) != 96_304
        or sum(item["word_token_count"] for item in ocr_records) != 1_313_842
        or sum(item["word_box_correction_count"] for item in ocr_records) != 22
        or sum(item["word_box_corrected_edge_count"] for item in ocr_records) != 22
        or ocr_dpi != {200: 1_250, 300: 106}
        or native_dpi != {"NOT_APPLICABLE": 93}
        or ocr_upstream_origins
        != {
            "AUTHENTICATED_SUCCESSFUL_SENTINEL_BYTE_COPY": 24,
            "PINNED_PPOCRV6_FULL_READER": 1_332,
        }
        or sum(outcomes.values()) != 1_449
        or set(native_outcomes) - _NATIVE_TERMINAL
        or sum(native_outcomes.values()) != 93
    ):
        raise WaveOneRoleBFullReaderError(
            "V3 source route, DPI, origin, or outcome accounting drifted"
        )
    unresolved = sum(item["unresolved"] for item in records)
    status = (
        _COMPLETE_STATUS
        if unresolved == 0
        else "COMPLETE_WAVE_1_PAGE_REQUEST_ACCOUNTING_WITH_UNRESOLVED_READS"
    )
    aggregate = {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READS_V2",
        "status": status,
        "claim_boundary": control["claim_boundary"],
        "sealed_plan": control["sealed_plan"],
        "control": {
            "identity_sha256": control["control_identity_sha256"],
            "artifact": {
                "path": "full-reader-execution-control.json",
                "sha256": sha256_bytes(_canonical_bytes(control)),
                "size_bytes": len(_canonical_bytes(control)),
            },
        },
        "failed_v2_authority": deepcopy(control["failed_v2_authority"]),
        "executor_git": deepcopy(control["executor_git"]),
        "executor_implementation_ledger": deepcopy(control["executor_implementation_ledger"]),
        "native_reader_contract": deepcopy(control["native_reader_contract"]),
        "document_indexes": document_references,
        "page_records": records,
        "accounting": {
            "document_count": 27,
            "request_count": 1_449,
            "source_accounted_page_count": 1_449,
            "ocr_page_count": routes[_OCR_ROUTE],
            "native_page_count": routes[_NATIVE_ROUTE],
            "failed_v2_ocr_adopted_page_count": 1_356,
            "fresh_native_page_count": 93,
            "archived_native_adopted_page_count": 0,
            "missing_request_count": 0,
            "duplicate_request_count": 0,
            "foreign_request_count": 0,
            "terminal_unresolved_page_count": unresolved,
            "line_axis_count": sum(item["line_axis_count"] for item in records),
            "nonempty_line_axis_count": sum(item["nonempty_line_axis_count"] for item in records),
            "exact_empty_line_axis_count": sum(
                item["exact_empty_line_axis_count"] for item in records
            ),
            "accepted_line_count": sum(item["accepted_line_count"] for item in records),
            "word_token_count": sum(item["word_token_count"] for item in records),
            "quarantined_span_count": sum(item["quarantined_span_count"] for item in records),
            "ordering_quarantined_raw_line_run_count": sum(
                item["ordering_quarantined_raw_line_run_count"] for item in records
            ),
            "ordering_quarantined_raw_word_count": sum(
                item["ordering_quarantined_raw_word_count"] for item in records
            ),
            "noncontiguous_line_identity_count": sum(
                item["noncontiguous_line_identity_count"] for item in records
            ),
            "outcome_counts": dict(sorted(outcomes.items())),
            "route_outcome_counts": {
                route: dict(
                    sorted(
                        Counter(
                            item["status"] for item in records if item["route"] == route
                        ).items()
                    )
                )
                for route in (_OCR_ROUTE, _NATIVE_ROUTE)
            },
            "origin_counts": dict(sorted(origins.items())),
            "route_dpi_counts": {
                _OCR_ROUTE: {"200": ocr_dpi[200], "300": ocr_dpi[300]},
                _NATIVE_ROUTE: {"NOT_APPLICABLE": native_dpi["NOT_APPLICABLE"]},
            },
            "ocr_upstream_origin_counts": dict(sorted(ocr_upstream_origins.items())),
            **inventory,
            **_ZERO_INTERPRETATION,
        },
        "ocr_adoption_accounting": {
            "line_axis_count": 96_369,
            "nonempty_line_axis_count": 96_304,
            "exact_empty_line_axis_count": 65,
            "accepted_line_count": 96_304,
            "word_token_count": 1_313_842,
            "complete_page_count": 1_299,
            "terminal_geometry_page_count": 57,
            "corrected_page_count": 20,
            "corrected_word_box_count": 22,
            "corrected_edge_count": 22,
            "copied_object_count": 4_068,
            "source_status_and_origin_preserved": True,
        },
        "native_accounting": {
            "request_count": 93,
            "line_axis_count": sum(item["line_axis_count"] for item in native_records),
            "word_token_count": sum(item["word_token_count"] for item in native_records),
            "quarantined_span_count": sum(
                item["quarantined_span_count"] for item in native_records
            ),
            "ordering_quarantined_raw_line_run_count": sum(
                item["ordering_quarantined_raw_line_run_count"] for item in native_records
            ),
            "ordering_quarantined_raw_word_count": sum(
                item["ordering_quarantined_raw_word_count"] for item in native_records
            ),
            "noncontiguous_line_identity_count": sum(
                item["noncontiguous_line_identity_count"] for item in native_records
            ),
            "ocr_fallback_count": 0,
        },
        "safety": {
            "bank_registry_metadata_used": False,
            "filename_metadata_used": False,
            "role_a_used": False,
            "schema_used": False,
            "mapping_used": False,
            "historical_values_used": False,
            "semantic_interpretation_attempted": False,
            "absence_claimed": False,
            "ocr_inference_used": False,
            "network_used": False,
            "archived_native_evidence_adopted": False,
            **_ZERO_INTERPRETATION,
        },
    }
    aggregate["aggregate_identity_sha256"] = _canonical_sha256(aggregate)
    aggregate_path = project_root / OUTPUT_RELATIVE_ROOT / "full-reader-aggregate.json"
    bound_aggregate_present = _v3_bound_output_file_present(aggregate_path)
    if bound_aggregate_present is None:
        raise WaveOneRoleBFullReaderError(
            "V3 aggregate construction requires a bound output snapshot"
        )
    if bound_aggregate_present:
        payload, identity = _v3_read_nofollow(
            aggregate_path,
            "published V3 aggregate",
            expected_nlink=(2 if aggregate_publication_temporary is not None else 1),
        )
        if (
            stat.S_IMODE(identity.st_mode) != 0o444
            or identity.st_nlink != (2 if aggregate_publication_temporary is not None else 1)
            or payload != _canonical_bytes(aggregate)
        ):
            raise WaveOneRoleBFullReaderError("published V3 aggregate drifted")
    return aggregate


def _v3_verify_held(
    project_root: Path, model_cache: Path, control: dict[str, Any]
) -> dict[str, Any]:
    """Build the exact aggregate and replay every selected source deeply."""

    return _v3_build_aggregate_held(
        project_root,
        model_cache,
        control,
        deep_source_replay=True,
    )


def verify_authenticated_full_reader(project_root: Path, *, model_cache: Path) -> dict[str, Any]:
    """Strictly read-only source/object/checkpoint/index/aggregate replay."""

    project_root = project_root.resolve()
    model_cache = model_cache.resolve()
    sealed, _policy, _executor = _v3_authenticate_plan(
        project_root, model_cache, require_clean_executor=True
    )
    document_ids = sorted(item["document_id"] for item in sealed["documents"])
    with _v3_failed_archive_locks(project_root, document_ids):
        with _v3_read_only_output_snapshot(project_root, document_ids):
            manifest_before = _v3_output_live_manifest(project_root)
            aggregate_present = _v3_manifest_has_file(manifest_before, "full-reader-aggregate.json")
            with _v3_bind_output_reads(project_root, manifest_before):
                control = _v3_load_published_control(project_root)
                aggregate = _v3_verify_held(project_root, model_cache, control)
            manifest_after = _v3_output_live_manifest(project_root)
            if not _same_typed_json(manifest_after, manifest_before):
                raise WaveOneRoleBFullReaderError("V3 output changed during read-only verification")
            return {
                "format_version": ("BANK_CORPUS_WAVE_1_ROLE_B_FULL_READER_VERIFICATION_V3"),
                "status": "COMPLETE_AUTHENTICATED_V3_VERIFICATION",
                "authenticated_published_aggregate_present": aggregate_present,
                "output_live_manifest_sha256": _canonical_sha256(manifest_after),
                "aggregate": aggregate,
            }


def finalize_authenticated_full_reader(project_root: Path, *, model_cache: Path) -> dict[str, Any]:
    with _v3_mutation_entry():
        return _finalize_authenticated_full_reader_mutating(project_root, model_cache=model_cache)


def _finalize_authenticated_full_reader_mutating(
    project_root: Path, *, model_cache: Path
) -> dict[str, Any]:
    project_root = project_root.resolve()
    model_cache = model_cache.resolve()
    sealed, policy, _executor = _v3_authenticate_plan(
        project_root, model_cache, require_clean_executor=True
    )
    document_ids = sorted(item["document_id"] for item in sealed["documents"])
    with _v3_failed_archive_locks(project_root, document_ids):
        with ExitStack() as output_locks:
            output_locks.enter_context(_v3_execution_lease(project_root, create=False))
            (
                interrupted_relative,
                preflight_manifest,
            ) = _v3_preflight_output_temporaries(project_root, document_ids, stage="finalize")
            if _v3_output_lock_state(project_root, document_ids) != "FULL_LOCK_SET":
                raise WaveOneRoleBFullReaderError(
                    "V3 finalize requires the complete output lock topology"
                )
            output_locks.enter_context(_v3_document_locks(project_root, document_ids))
            _v3_validate_output_lock_topology(project_root, document_ids)
            (
                repeated_interrupted_relative,
                preflight_manifest,
            ) = _v3_preflight_output_temporaries(project_root, document_ids, stage="finalize")
            if repeated_interrupted_relative != interrupted_relative:
                raise WaveOneRoleBFullReaderError(
                    "V3 finalize publication state changed during lock acquisition"
                )
            _v3_ensure_capacity(project_root, policy["execution"]["minimum_free_space_bytes"])
            aggregate_temporary_name = None
            if interrupted_relative is not None:
                interrupted_target = _v3_publication_target_path(interrupted_relative)
                if interrupted_target != "full-reader-aggregate.json":
                    raise WaveOneRoleBFullReaderError("V3 finalize temporary target drifted")
            if interrupted_relative is not None:
                interrupted = project_root / OUTPUT_RELATIVE_ROOT / interrupted_relative
                aggregate_temporary_name = interrupted.name
            candidate_manifest_before = _v3_output_live_manifest(project_root)
            with _v3_bind_output_reads(project_root, candidate_manifest_before):
                control = _v3_load_published_control(project_root)
                aggregate = _v3_build_aggregate_held(
                    project_root,
                    model_cache,
                    control,
                    deep_source_replay=True,
                    aggregate_publication_temporary=aggregate_temporary_name,
                )
            candidate_manifest_after = _v3_output_live_manifest(project_root)
            if not _same_typed_json(candidate_manifest_after, candidate_manifest_before):
                raise WaveOneRoleBFullReaderError(
                    "V3 output changed while building the aggregate candidate"
                )
            if aggregate_temporary_name is not None:
                aggregate_payload = _canonical_bytes(aggregate)
                _v3_recover_publication_directory(
                    project_root,
                    OUTPUT_RELATIVE_ROOT,
                    create=False,
                    allowed_final=lambda candidate: candidate == "full-reader-aggregate.json",
                    validate_payload=lambda candidate, payload: (
                        candidate == "full-reader-aggregate.json" and payload == aggregate_payload
                    ),
                    expected_output_manifest=preflight_manifest,
                )
            _publish_exclusive(
                project_root,
                OUTPUT_RELATIVE_ROOT,
                "full-reader-aggregate.json",
                _canonical_bytes(aggregate),
            )
            published_manifest_before = _v3_output_live_manifest(project_root)
            with _v3_bind_output_reads(project_root, published_manifest_before):
                replay = _v3_verify_held(project_root, model_cache, control)
            published_manifest_after = _v3_output_live_manifest(project_root)
            if not _same_typed_json(replay, aggregate):
                raise WaveOneRoleBFullReaderError("V3 aggregate replay changed after publication")
            if not _same_typed_json(published_manifest_after, published_manifest_before):
                raise WaveOneRoleBFullReaderError(
                    "V3 output changed during post-publication replay"
                )
            return aggregate
