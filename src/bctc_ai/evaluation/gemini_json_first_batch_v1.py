"""Google Batch transport for Gemini JSON-first financial-page extraction."""

from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from bctc_ai.evaluation.gemini_json_first_provider_v1 import (
    GOOGLE_BATCH_SERVICE_TIER,
    GOOGLE_MODEL,
    GOOGLE_THINKING_LEVELS,
    GeminiJsonFirstProviderV1Error,
    ProviderResultV1,
    _google_generate_content_body_v1,
    _google_generate_content_response_v1,
    _post_json_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1

FORMAT_VERSION = "GEMINI_JSON_FIRST_BATCH_V1"
GOOGLE_BATCH_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    + GOOGLE_MODEL
    + ":batchGenerateContent"
)
GOOGLE_API_ROOT = "https://generativelanguage.googleapis.com/v1beta/"
GOOGLE_FILE_UPLOAD_ENDPOINT = "https://generativelanguage.googleapis.com/upload/v1beta/files"
GOOGLE_FILE_DOWNLOAD_ROOT = "https://generativelanguage.googleapis.com/download/v1beta/"
TERMINAL_BATCH_STATES = frozenset(
    {
        "BATCH_STATE_SUCCEEDED",
        "BATCH_STATE_FAILED",
        "BATCH_STATE_CANCELLED",
        "BATCH_STATE_EXPIRED",
    }
)
ACTIVE_BATCH_STATES = frozenset({"BATCH_STATE_PENDING", "BATCH_STATE_RUNNING"})


class GeminiJsonFirstBatchV1Error(RuntimeError):
    """The batch request, operation, or per-page response drifted."""


@dataclass(frozen=True)
class InlinePageRequestV1:
    request_id: str
    media_type: str
    prompt: str
    response_schema: dict[str, Any]
    output_contract_mode: str = "JSON_SCHEMA"
    thinking_level: str = "low"
    image: bytes | None = None
    file_uri: str | None = None


@dataclass(frozen=True)
class UploadedGoogleFileV1:
    name: str
    uri: str
    media_type: str
    size_bytes: int
    sha256: str
    expiration_time: str | None
    raw_response_bytes: bytes


@dataclass(frozen=True)
class BatchSubmissionV1:
    batch_name: str
    state: str
    raw_response_bytes: bytes
    elapsed_seconds: str
    credential_slot: str


@dataclass(frozen=True)
class CompletedBatchV1:
    batch_name: str
    state: str
    provider_results: dict[str, ProviderResultV1]
    failures: dict[str, dict[str, Any]]
    raw_operation_bytes: bytes


def _per_request_model_failure_v1(
    *, response: Mapping[str, Any], response_raw: bytes, error: Exception
) -> dict[str, Any]:
    """Return a bounded failure receipt for one transport-successful model response."""

    candidates = response.get("candidates")
    first = candidates[0] if type(candidates) is list and candidates else None
    finish_reason = first.get("finishReason") if type(first) is dict else None
    usage = response.get("usageMetadata")
    return {
        "error_message": str(error),
        "error_type": type(error).__name__,
        "finish_reason": finish_reason if type(finish_reason) is str else None,
        "provider_response_sha256": sha256(response_raw).hexdigest(),
        "usage_metadata": (
            json.loads(canonical_json_bytes_v1(usage)) if type(usage) is dict else None
        ),
    }


def _json_object(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise GeminiJsonFirstBatchV1Error(f"{label} is not JSON") from exc
    if type(value) is not dict:
        raise GeminiJsonFirstBatchV1Error(f"{label} is not one JSON object")
    return value


def _request_id(value: Any) -> str:
    if type(value) is not str or not value or len(value) > 128:
        raise GeminiJsonFirstBatchV1Error("batch request ID is invalid")
    if any(
        character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.:"
        for character in value
    ):
        raise GeminiJsonFirstBatchV1Error("batch request ID contains unsupported characters")
    return value


def build_google_inline_batch_body_v1(
    *, display_name: str, requests: Sequence[InlinePageRequestV1]
) -> dict[str, Any]:
    """Build one bounded inline batch body without provider or document routing."""

    if type(display_name) is not str or not display_name or len(display_name) > 128:
        raise GeminiJsonFirstBatchV1Error("batch display name is invalid")
    if not requests:
        raise GeminiJsonFirstBatchV1Error("batch requires at least one page request")
    request_ids = [_request_id(request.request_id) for request in requests]
    if len(set(request_ids)) != len(request_ids):
        raise GeminiJsonFirstBatchV1Error("batch request IDs must be unique")
    inlined = []
    for request in requests:
        if request.thinking_level not in GOOGLE_THINKING_LEVELS:
            raise GeminiJsonFirstBatchV1Error("batch thinking level is invalid")
        generate_request = _google_generate_content_body_v1(
            image=request.image,
            media_type=request.media_type,
            prompt=request.prompt,
            response_schema=request.response_schema,
            output_contract_mode=request.output_contract_mode,
            thinking_level=request.thinking_level,
            file_uri=request.file_uri,
        )
        generate_request["model"] = "models/" + GOOGLE_MODEL
        inlined.append(
            {
                "metadata": {"request_id": request.request_id},
                "request": generate_request,
            }
        )
    return {
        "batch": {
            "displayName": display_name,
            "inputConfig": {"requests": {"requests": inlined}},
            "model": "models/" + GOOGLE_MODEL,
        }
    }


def build_google_file_batch_body_v1(*, display_name: str, input_file_name: str) -> dict[str, Any]:
    """Build the official JSONL-backed Batch request used for multimodal pages."""

    if type(display_name) is not str or not display_name or len(display_name) > 128:
        raise GeminiJsonFirstBatchV1Error("batch display name is invalid")
    if (
        type(input_file_name) is not str
        or not input_file_name.startswith("files/")
        or len(input_file_name.split("/")) != 2
    ):
        raise GeminiJsonFirstBatchV1Error("batch input file name is invalid")
    return {
        "batch": {
            "displayName": display_name,
            "inputConfig": {"fileName": input_file_name},
            "model": "models/" + GOOGLE_MODEL,
        }
    }


def _start_file_upload_v1(
    url: str, headers: dict[str, str], body: bytes, timeout_seconds: int
) -> tuple[bytes, dict[str, str]]:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.read(), {key.lower(): value for key, value in response.headers.items()}
    except urllib.error.HTTPError as exc:
        exc.read()
        raise GeminiJsonFirstBatchV1Error(
            f"Google file upload start returned HTTP {exc.code}"
        ) from exc
    except (TimeoutError, urllib.error.URLError, ConnectionError) as exc:
        raise GeminiJsonFirstBatchV1Error("Google file upload start failed or timed out") from exc


def _finalize_file_upload_v1(
    url: str, headers: dict[str, str], payload: bytes, timeout_seconds: int
) -> bytes:
    request = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        exc.read()
        raise GeminiJsonFirstBatchV1Error(
            f"Google file upload finalize returned HTTP {exc.code}"
        ) from exc
    except (TimeoutError, urllib.error.URLError, ConnectionError) as exc:
        raise GeminiJsonFirstBatchV1Error(
            "Google file upload finalize failed or timed out"
        ) from exc


def upload_google_file_v1(
    *,
    api_key: str,
    payload: bytes,
    media_type: str,
    display_name: str,
    timeout_seconds: int = 120,
    start_transport: Callable[
        [str, dict[str, str], bytes, int], tuple[bytes, dict[str, str]]
    ] = _start_file_upload_v1,
    finalize_transport: Callable[
        [str, dict[str, str], bytes, int], bytes
    ] = _finalize_file_upload_v1,
) -> UploadedGoogleFileV1:
    """Upload one exact image through Google's resumable Files API and verify its SHA."""

    if type(api_key) is not str or len(api_key) < 20:
        raise GeminiJsonFirstBatchV1Error("Google API key slot is invalid")
    if not payload or media_type not in {"image/png", "image/jpeg", "application/jsonl"}:
        raise GeminiJsonFirstBatchV1Error(
            "uploaded file must be one nonempty PNG, JPEG, or JSONL payload"
        )
    if type(display_name) is not str or not display_name or len(display_name) > 512:
        raise GeminiJsonFirstBatchV1Error("uploaded file display name is invalid")
    start_body = canonical_json_bytes_v1({"file": {"displayName": display_name}})
    _, response_headers = start_transport(
        GOOGLE_FILE_UPLOAD_ENDPOINT,
        {
            "Content-Type": "application/json",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(len(payload)),
            "X-Goog-Upload-Header-Content-Type": media_type,
            "X-Goog-Upload-Protocol": "resumable",
            "x-goog-api-key": api_key,
        },
        start_body,
        timeout_seconds,
    )
    upload_url = response_headers.get("x-goog-upload-url")
    if type(upload_url) is not str or not upload_url.startswith("https://"):
        raise GeminiJsonFirstBatchV1Error("Google resumable upload URL is absent")
    raw = finalize_transport(
        upload_url,
        {
            "Content-Length": str(len(payload)),
            "X-Goog-Upload-Command": "upload, finalize",
            "X-Goog-Upload-Offset": "0",
        },
        payload,
        timeout_seconds,
    )
    response = _json_object(raw, "Google file upload response")
    file = response.get("file")
    if type(file) is not dict:
        raise GeminiJsonFirstBatchV1Error("Google file upload response has no file")
    name = file.get("name")
    uri = file.get("uri")
    returned_media_type = file.get("mimeType")
    size = file.get("sizeBytes")
    digest = file.get("sha256Hash")
    expiration = file.get("expirationTime")
    if type(name) is not str or not name.startswith("files/"):
        raise GeminiJsonFirstBatchV1Error("uploaded file name drifted")
    if type(uri) is not str or not uri.startswith("https://"):
        raise GeminiJsonFirstBatchV1Error("uploaded file URI drifted")
    if returned_media_type != media_type or type(size) is not str or not size.isdigit():
        raise GeminiJsonFirstBatchV1Error("uploaded file media type or size drifted")
    try:
        decoded_digest = base64.b64decode(digest, validate=True)
    except (TypeError, ValueError) as exc:
        raise GeminiJsonFirstBatchV1Error("uploaded file SHA-256 drifted") from exc
    if len(decoded_digest) == 32:
        returned_sha = decoded_digest.hex()
    elif len(decoded_digest) == 64:
        try:
            returned_sha = decoded_digest.decode("ascii").lower()
            bytes.fromhex(returned_sha)
        except (UnicodeDecodeError, ValueError) as exc:
            raise GeminiJsonFirstBatchV1Error("uploaded file SHA-256 drifted") from exc
    else:
        raise GeminiJsonFirstBatchV1Error("uploaded file SHA-256 drifted")
    expected_sha = sha256(payload).hexdigest()
    if int(size) != len(payload) or returned_sha != expected_sha:
        raise GeminiJsonFirstBatchV1Error("uploaded file bytes do not authenticate")
    if file.get("state") != "ACTIVE":
        raise GeminiJsonFirstBatchV1Error("uploaded file is not active")
    if expiration is not None and (type(expiration) is not str or not expiration):
        raise GeminiJsonFirstBatchV1Error("uploaded file expiration time drifted")
    return UploadedGoogleFileV1(
        name=name,
        uri=uri,
        media_type=media_type,
        size_bytes=len(payload),
        sha256=expected_sha,
        expiration_time=expiration,
        raw_response_bytes=raw,
    )


def _batch_resource(operation: Mapping[str, Any]) -> Mapping[str, Any]:
    metadata = operation.get("metadata")
    if type(metadata) is dict:
        return metadata
    response = operation.get("response")
    if type(response) is dict:
        return response
    raise GeminiJsonFirstBatchV1Error("batch operation has no resource metadata")


def _batch_output(operation: Mapping[str, Any], resource: Mapping[str, Any]) -> Mapping[str, Any]:
    response = operation.get("response")
    if type(response) is dict and ("inlinedResponses" in response or "responsesFile" in response):
        return response
    output = resource.get("output")
    if type(output) is dict:
        return output
    raise GeminiJsonFirstBatchV1Error("batch has no inline response output")


def _batch_identity(operation: Mapping[str, Any]) -> tuple[str, str]:
    name = operation.get("name")
    resource = _batch_resource(operation)
    resource_name = resource.get("name")
    state = resource.get("state")
    if type(name) is not str or not name.startswith("batches/"):
        raise GeminiJsonFirstBatchV1Error("batch operation name drifted")
    if resource_name != name:
        raise GeminiJsonFirstBatchV1Error("batch resource name does not match operation")
    if state not in ACTIVE_BATCH_STATES | TERMINAL_BATCH_STATES:
        raise GeminiJsonFirstBatchV1Error("batch state drifted")
    return name, state


def submit_google_inline_batch_v1(
    *,
    api_key: str,
    credential_slot: str,
    display_name: str,
    requests: Sequence[InlinePageRequestV1],
    timeout_seconds: int = 120,
    transport: Callable[[str, dict[str, str], dict[str, Any], int], bytes] = _post_json_v1,
) -> BatchSubmissionV1:
    """Submit exactly one Google inline batch and preserve its operation receipt."""

    if type(api_key) is not str or len(api_key) < 20:
        raise GeminiJsonFirstBatchV1Error("Google API key slot is invalid")
    if type(credential_slot) is not str or not credential_slot:
        raise GeminiJsonFirstBatchV1Error("credential slot is invalid")
    body = build_google_inline_batch_body_v1(display_name=display_name, requests=requests)
    started = time.perf_counter()
    raw = transport(
        GOOGLE_BATCH_ENDPOINT,
        {"Content-Type": "application/json", "x-goog-api-key": api_key},
        body,
        timeout_seconds,
    )
    operation = _json_object(raw, "batch submission response")
    name, state = _batch_identity(operation)
    if operation.get("done") is True or operation.get("error") is not None:
        raise GeminiJsonFirstBatchV1Error("new batch unexpectedly returned terminal operation")
    return BatchSubmissionV1(
        batch_name=name,
        state=state,
        raw_response_bytes=raw,
        elapsed_seconds=format(time.perf_counter() - started, ".3f"),
        credential_slot=credential_slot,
    )


def submit_google_file_batch_v1(
    *,
    api_key: str,
    credential_slot: str,
    display_name: str,
    input_file_name: str,
    timeout_seconds: int = 120,
    transport: Callable[[str, dict[str, str], dict[str, Any], int], bytes] = _post_json_v1,
) -> BatchSubmissionV1:
    """Submit a JSONL-backed Google batch without embedding the request corpus."""

    if type(api_key) is not str or len(api_key) < 20:
        raise GeminiJsonFirstBatchV1Error("Google API key slot is invalid")
    if type(credential_slot) is not str or not credential_slot:
        raise GeminiJsonFirstBatchV1Error("credential slot is invalid")
    body = build_google_file_batch_body_v1(
        display_name=display_name, input_file_name=input_file_name
    )
    started = time.perf_counter()
    raw = transport(
        GOOGLE_BATCH_ENDPOINT,
        {"Content-Type": "application/json", "x-goog-api-key": api_key},
        body,
        timeout_seconds,
    )
    operation = _json_object(raw, "batch submission response")
    name, state = _batch_identity(operation)
    if operation.get("done") is True or operation.get("error") is not None:
        raise GeminiJsonFirstBatchV1Error("new batch unexpectedly returned terminal operation")
    return BatchSubmissionV1(
        batch_name=name,
        state=state,
        raw_response_bytes=raw,
        elapsed_seconds=format(time.perf_counter() - started, ".3f"),
        credential_slot=credential_slot,
    )


def _get_batch_v1(url: str, headers: dict[str, str], timeout_seconds: int) -> bytes:
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        exc.read()
        raise GeminiJsonFirstBatchV1Error(f"Google batch poll returned HTTP {exc.code}") from exc
    except (TimeoutError, urllib.error.URLError, ConnectionError) as exc:
        raise GeminiJsonFirstBatchV1Error("Google batch poll failed or timed out") from exc


def poll_google_batch_v1(
    *,
    api_key: str,
    batch_name: str,
    timeout_seconds: int = 60,
    transport: Callable[[str, dict[str, str], int], bytes] = _get_batch_v1,
) -> bytes:
    """Fetch one batch operation; the caller controls polling cadence and duration."""

    if type(api_key) is not str or len(api_key) < 20:
        raise GeminiJsonFirstBatchV1Error("Google API key slot is invalid")
    if type(batch_name) is not str or not batch_name.startswith("batches/"):
        raise GeminiJsonFirstBatchV1Error("batch name is invalid")
    raw = transport(
        GOOGLE_API_ROOT + batch_name,
        {"x-goog-api-key": api_key},
        timeout_seconds,
    )
    operation = _json_object(raw, "batch poll response")
    name, _ = _batch_identity(operation)
    if name != batch_name:
        raise GeminiJsonFirstBatchV1Error("polled batch identity drifted")
    return raw


def download_google_file_v1(
    *,
    api_key: str,
    file_name: str,
    timeout_seconds: int = 120,
    transport: Callable[[str, dict[str, str], int], bytes] = _get_batch_v1,
) -> bytes:
    """Download an exact File API result payload from a completed batch."""

    if type(api_key) is not str or len(api_key) < 20:
        raise GeminiJsonFirstBatchV1Error("Google API key slot is invalid")
    if (
        type(file_name) is not str
        or not file_name.startswith("files/")
        or len(file_name.split("/")) != 2
    ):
        raise GeminiJsonFirstBatchV1Error("Google result file name is invalid")
    raw = transport(
        GOOGLE_FILE_DOWNLOAD_ROOT + file_name + ":download?alt=media",
        {"x-goog-api-key": api_key},
        timeout_seconds,
    )
    if not raw:
        raise GeminiJsonFirstBatchV1Error("Google result file is empty")
    return raw


def summarize_google_batch_operation_v1(raw_operation_bytes: bytes) -> dict[str, Any]:
    """Return the small authenticated progress projection used by the local store."""

    operation = _json_object(raw_operation_bytes, "batch operation")
    batch_name, state = _batch_identity(operation)
    resource = _batch_resource(operation)
    stats = resource.get("batchStats", {})
    if type(stats) is not dict:
        raise GeminiJsonFirstBatchV1Error("batch stats drifted")

    def count(field: str) -> int:
        value = stats.get(field, "0")
        if type(value) is not str or not value.isdigit():
            raise GeminiJsonFirstBatchV1Error("batch request count drifted")
        return int(value)

    request_count = count("requestCount")
    successful = count("successfulRequestCount")
    failed = count("failedRequestCount")
    pending = count("pendingRequestCount")
    if successful + failed + pending > request_count:
        raise GeminiJsonFirstBatchV1Error("batch request counts are inconsistent")
    done = operation.get("done") is True
    if done != (state in TERMINAL_BATCH_STATES):
        raise GeminiJsonFirstBatchV1Error("batch done flag disagrees with state")
    return {
        "batch_name": batch_name,
        "done": done,
        "failed_request_count": failed,
        "pending_request_count": pending,
        "request_count": request_count,
        "state": state,
        "successful_request_count": successful,
    }


def google_batch_responses_file_v1(raw_operation_bytes: bytes) -> str:
    """Return the authenticated output File name for a successful JSONL batch."""

    operation = _json_object(raw_operation_bytes, "completed batch operation")
    _, state = _batch_identity(operation)
    if state != "BATCH_STATE_SUCCEEDED" or operation.get("done") is not True:
        raise GeminiJsonFirstBatchV1Error("batch operation did not succeed")
    output = _batch_output(operation, _batch_resource(operation))
    file_name = output.get("responsesFile")
    if (
        type(file_name) is not str
        or not file_name.startswith("files/")
        or len(file_name.split("/")) != 2
    ):
        raise GeminiJsonFirstBatchV1Error("batch response file name drifted")
    return file_name


def decode_completed_google_inline_batch_v1(
    *,
    raw_operation_bytes: bytes,
    expected_request_ids: Sequence[str],
    credential_slot: str,
    elapsed_seconds: str,
) -> CompletedBatchV1:
    """Decode a terminal batch and bind every response to one expected request ID."""

    expected = [_request_id(value) for value in expected_request_ids]
    if not expected or len(set(expected)) != len(expected):
        raise GeminiJsonFirstBatchV1Error("expected batch request IDs are invalid")
    operation = _json_object(raw_operation_bytes, "completed batch operation")
    batch_name, state = _batch_identity(operation)
    if state != "BATCH_STATE_SUCCEEDED" or operation.get("done") is not True:
        raise GeminiJsonFirstBatchV1Error("batch operation did not succeed")
    resource = _batch_resource(operation)
    output = _batch_output(operation, resource)
    if type(output.get("inlinedResponses")) is not dict:
        raise GeminiJsonFirstBatchV1Error("batch has no inline response output")
    responses = output["inlinedResponses"].get("inlinedResponses")
    if type(responses) is not list:
        raise GeminiJsonFirstBatchV1Error("batch inline response array is absent")
    by_id: dict[str, dict[str, Any]] = {}
    for entry in responses:
        if type(entry) is not dict or type(entry.get("metadata")) is not dict:
            raise GeminiJsonFirstBatchV1Error("batch inline response metadata drifted")
        request_id = _request_id(entry["metadata"].get("request_id"))
        if request_id in by_id:
            raise GeminiJsonFirstBatchV1Error("batch returned duplicate request IDs")
        by_id[request_id] = entry
    if set(by_id) != set(expected):
        raise GeminiJsonFirstBatchV1Error("batch response request-ID set drifted")
    results: dict[str, ProviderResultV1] = {}
    failures: dict[str, dict[str, Any]] = {}
    for request_id in expected:
        entry = by_id[request_id]
        error = entry.get("error")
        response = entry.get("response")
        if error is not None:
            if type(error) is not dict or response is not None:
                raise GeminiJsonFirstBatchV1Error("batch failure envelope drifted")
            failures[request_id] = json.loads(canonical_json_bytes_v1(error))
            continue
        if type(response) is not dict:
            raise GeminiJsonFirstBatchV1Error("batch success response is absent")
        response_raw = canonical_json_bytes_v1(response) + b"\n"
        try:
            text, response_id, model, usage = _google_generate_content_response_v1(
                response_raw, service_tier=GOOGLE_BATCH_SERVICE_TIER
            )
        except GeminiJsonFirstProviderV1Error as exc:
            failures[request_id] = _per_request_model_failure_v1(
                response=response, response_raw=response_raw, error=exc
            )
            continue
        attempt = {
            "attempt_ordinal": 1,
            "credential_slot": credential_slot,
            "elapsed_seconds": elapsed_seconds,
            "http_status": 200,
            "outcome": "COMPLETED_BATCH",
            "provider": "GOOGLE_GEMINI_BATCH_API",
            "usage": json.loads(canonical_json_bytes_v1(usage)),
        }
        results[request_id] = ProviderResultV1(
            output_text=text,
            raw_response_bytes=response_raw,
            provider_name="GOOGLE_GEMINI_BATCH_API",
            provider_model=model,
            service_tier=GOOGLE_BATCH_SERVICE_TIER,
            attempts=(attempt,),
            usage=usage,
            response_id_sha256=sha256(response_id.encode("utf-8")).hexdigest(),
        )
    return CompletedBatchV1(
        batch_name=batch_name,
        state=state,
        provider_results=results,
        failures=failures,
        raw_operation_bytes=raw_operation_bytes,
    )


def decode_completed_google_file_batch_v1(
    *,
    raw_operation_bytes: bytes,
    raw_results_bytes: bytes,
    expected_request_ids: Sequence[str],
    credential_slot: str,
    elapsed_seconds: str,
) -> CompletedBatchV1:
    """Decode JSONL output while binding every line to its original page request."""

    expected = [_request_id(value) for value in expected_request_ids]
    if not expected or len(set(expected)) != len(expected):
        raise GeminiJsonFirstBatchV1Error("expected batch request IDs are invalid")
    operation = _json_object(raw_operation_bytes, "completed batch operation")
    batch_name, state = _batch_identity(operation)
    google_batch_responses_file_v1(raw_operation_bytes)
    by_id: dict[str, dict[str, Any]] = {}
    try:
        text = raw_results_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GeminiJsonFirstBatchV1Error("batch result JSONL is not UTF-8") from exc
    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        try:
            entry = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise GeminiJsonFirstBatchV1Error("batch result JSONL line is not JSON") from exc
        if type(entry) is not dict:
            raise GeminiJsonFirstBatchV1Error("batch result JSONL line is not one object")
        request_id = _request_id(entry.get("key"))
        if request_id in by_id:
            raise GeminiJsonFirstBatchV1Error("batch returned duplicate request IDs")
        by_id[request_id] = entry
    if set(by_id) != set(expected):
        raise GeminiJsonFirstBatchV1Error("batch response request-ID set drifted")
    results: dict[str, ProviderResultV1] = {}
    failures: dict[str, dict[str, Any]] = {}
    for request_id in expected:
        entry = by_id[request_id]
        error = entry.get("error")
        response = entry.get("response")
        if error is not None:
            if type(error) is not dict or response is not None:
                raise GeminiJsonFirstBatchV1Error("batch failure envelope drifted")
            failures[request_id] = json.loads(canonical_json_bytes_v1(error))
            continue
        if type(response) is not dict:
            raise GeminiJsonFirstBatchV1Error("batch success response is absent")
        response_raw = canonical_json_bytes_v1(response) + b"\n"
        try:
            output_text, response_id, model, usage = _google_generate_content_response_v1(
                response_raw, service_tier=GOOGLE_BATCH_SERVICE_TIER
            )
        except GeminiJsonFirstProviderV1Error as exc:
            failures[request_id] = _per_request_model_failure_v1(
                response=response, response_raw=response_raw, error=exc
            )
            continue
        attempt = {
            "attempt_ordinal": 1,
            "credential_slot": credential_slot,
            "elapsed_seconds": elapsed_seconds,
            "http_status": 200,
            "outcome": "COMPLETED_BATCH",
            "provider": "GOOGLE_GEMINI_BATCH_API",
            "usage": json.loads(canonical_json_bytes_v1(usage)),
        }
        results[request_id] = ProviderResultV1(
            output_text=output_text,
            raw_response_bytes=response_raw,
            provider_name="GOOGLE_GEMINI_BATCH_API",
            provider_model=model,
            service_tier=GOOGLE_BATCH_SERVICE_TIER,
            attempts=(attempt,),
            usage=usage,
            response_id_sha256=sha256(response_id.encode()).hexdigest(),
        )
    return CompletedBatchV1(
        batch_name=batch_name,
        state=state,
        provider_results=results,
        failures=failures,
        raw_operation_bytes=raw_operation_bytes,
    )
