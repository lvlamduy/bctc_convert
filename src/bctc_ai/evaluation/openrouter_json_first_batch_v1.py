"""OpenRouter Batch transport for Gemini JSON-first financial pages."""

from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from typing import Any

from bctc_ai.evaluation.gemini_json_first_batch_v1 import InlinePageRequestV1
from bctc_ai.evaluation.gemini_json_first_provider_v1 import (
    GOOGLE_THINKING_LEVELS,
    OPENROUTER_MODEL,
    ProviderResultV1,
    _openrouter_response_v1,
    _post_json_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1

FORMAT_VERSION = "OPENROUTER_JSON_FIRST_BATCH_V1"
OPENROUTER_BATCH_ENDPOINT = "https://openrouter.ai/api/beta/batches"
OPENROUTER_BATCH_PROVIDER = "google-vertex"
OPENROUTER_BATCH_INPUT_USD_PER_MILLION = Decimal("0.1875")
OPENROUTER_BATCH_OUTPUT_USD_PER_MILLION = Decimal("0.9375")
ACTIVE_OPENROUTER_BATCH_STATUSES = frozenset({"validating", "in_progress"})
TERMINAL_OPENROUTER_BATCH_STATUSES = frozenset({"completed", "failed", "cancelled", "expired"})


class OpenRouterJsonFirstBatchV1Error(RuntimeError):
    """The OpenRouter batch request or response contract drifted."""


@dataclass(frozen=True)
class OpenRouterBatchSubmissionV1:
    batch_name: str
    state: str
    raw_response_bytes: bytes
    elapsed_seconds: str
    credential_slot: str


@dataclass(frozen=True)
class CompletedOpenRouterBatchV1:
    batch_name: str
    state: str
    provider_results: dict[str, ProviderResultV1]
    failures: dict[str, dict[str, Any]]
    raw_operation_bytes: bytes


def _json_object(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise OpenRouterJsonFirstBatchV1Error(f"{label} is not JSON") from exc
    if type(value) is not dict:
        raise OpenRouterJsonFirstBatchV1Error(f"{label} is not one JSON object")
    return value


def _request_id(value: Any) -> str:
    if type(value) is not str or not value or len(value) > 128:
        raise OpenRouterJsonFirstBatchV1Error("OpenRouter batch request ID is invalid")
    return value


def build_openrouter_batch_body_v1(*, requests: Sequence[InlinePageRequestV1]) -> dict[str, Any]:
    """Build one Gemini 3.7 Flash Batch request pinned to Google Vertex."""

    if not requests:
        raise OpenRouterJsonFirstBatchV1Error("OpenRouter batch has no requests")
    request_ids = [_request_id(request.request_id) for request in requests]
    if len(set(request_ids)) != len(request_ids):
        raise OpenRouterJsonFirstBatchV1Error("OpenRouter batch request IDs must be unique")
    output = []
    for request in requests:
        if request.thinking_level not in GOOGLE_THINKING_LEVELS:
            raise OpenRouterJsonFirstBatchV1Error("OpenRouter batch thinking level is invalid")
        if (request.image is None) == (request.file_uri is None):
            raise OpenRouterJsonFirstBatchV1Error(
                "OpenRouter batch requires exactly one inline image or public HTTPS URL"
            )
        if request.file_uri is not None and not request.file_uri.startswith("https://"):
            raise OpenRouterJsonFirstBatchV1Error("OpenRouter batch image URL is invalid")
        image_url = (
            "data:"
            + request.media_type
            + ";base64,"
            + base64.b64encode(request.image).decode("ascii")
            if request.image is not None
            else request.file_uri
        )
        body: dict[str, Any] = {
            "max_tokens": 65536,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": request.prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                    ],
                }
            ],
            "model": OPENROUTER_MODEL,
            "provider": {
                "allow_fallbacks": False,
                "data_collection": "deny",
                "only": [OPENROUTER_BATCH_PROVIDER],
                "require_parameters": True,
            },
            "reasoning": {"effort": request.thinking_level},
        }
        if request.output_contract_mode == "JSON_SCHEMA":
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "financial_page_json_v1",
                    "schema": request.response_schema,
                    "strict": True,
                },
            }
        elif request.output_contract_mode != "PROMPT_JSON":
            raise OpenRouterJsonFirstBatchV1Error("output contract mode is invalid")
        output.append({"body": body, "custom_id": request.request_id})
    return {
        "endpoint": "/v1/chat/completions",
        "model": OPENROUTER_MODEL,
        "requests": output,
    }


def summarize_openrouter_batch_v1(raw: bytes) -> dict[str, Any]:
    value = _json_object(raw, "OpenRouter batch response")
    batch_name = value.get("id")
    status = value.get("status")
    counts = value.get("request_counts")
    if type(batch_name) is not str or not batch_name.startswith("batch-"):
        raise OpenRouterJsonFirstBatchV1Error("OpenRouter batch ID drifted")
    if status not in ACTIVE_OPENROUTER_BATCH_STATUSES | TERMINAL_OPENROUTER_BATCH_STATUSES:
        raise OpenRouterJsonFirstBatchV1Error("OpenRouter batch status drifted")
    if type(counts) is not dict:
        raise OpenRouterJsonFirstBatchV1Error("OpenRouter batch counts are absent")
    total = counts.get("total")
    completed = counts.get("completed")
    failed = counts.get("failed")
    if any(type(item) is not int or item < 0 for item in (total, completed, failed)):
        raise OpenRouterJsonFirstBatchV1Error("OpenRouter batch counts drifted")
    pending = total - completed - failed
    if total <= 0 or pending < 0:
        raise OpenRouterJsonFirstBatchV1Error("OpenRouter batch counts are inconsistent")
    state = {
        "validating": "BATCH_STATE_PENDING",
        "in_progress": "BATCH_STATE_RUNNING",
        "completed": "BATCH_STATE_SUCCEEDED",
        "failed": "BATCH_STATE_FAILED",
        "cancelled": "BATCH_STATE_CANCELLED",
        "expired": "BATCH_STATE_EXPIRED",
    }[status]
    done = status in TERMINAL_OPENROUTER_BATCH_STATUSES
    return {
        "batch_name": batch_name,
        "done": done,
        "failed_request_count": failed,
        "pending_request_count": pending,
        "request_count": total,
        "state": state,
        "successful_request_count": completed,
    }


def submit_openrouter_batch_v1(
    *,
    api_key: str,
    requests: Sequence[InlinePageRequestV1],
    timeout_seconds: int = 120,
    transport: Callable[[str, dict[str, str], dict[str, Any], int], bytes] = _post_json_v1,
) -> OpenRouterBatchSubmissionV1:
    if type(api_key) is not str or len(api_key) < 20:
        raise OpenRouterJsonFirstBatchV1Error("OpenRouter API key is invalid")
    body = build_openrouter_batch_body_v1(requests=requests)
    started = time.perf_counter()
    raw = transport(
        OPENROUTER_BATCH_ENDPOINT,
        {"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
        body,
        timeout_seconds,
    )
    summary = summarize_openrouter_batch_v1(raw)
    if summary["done"]:
        raise OpenRouterJsonFirstBatchV1Error("new OpenRouter batch is unexpectedly terminal")
    return OpenRouterBatchSubmissionV1(
        batch_name=summary["batch_name"],
        state=summary["state"],
        raw_response_bytes=raw,
        elapsed_seconds=format(time.perf_counter() - started, ".3f"),
        credential_slot="OPENROUTER_SLOT_1",
    )


def _get_openrouter_batch_v1(url: str, headers: dict[str, str], timeout_seconds: int) -> bytes:
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        exc.read()
        raise OpenRouterJsonFirstBatchV1Error(
            f"OpenRouter batch poll returned HTTP {exc.code}"
        ) from exc
    except (TimeoutError, urllib.error.URLError, ConnectionError) as exc:
        raise OpenRouterJsonFirstBatchV1Error("OpenRouter batch poll failed or timed out") from exc


def poll_openrouter_batch_v1(
    *,
    api_key: str,
    batch_name: str,
    timeout_seconds: int = 60,
    transport: Callable[[str, dict[str, str], int], bytes] = _get_openrouter_batch_v1,
) -> bytes:
    if type(api_key) is not str or len(api_key) < 20:
        raise OpenRouterJsonFirstBatchV1Error("OpenRouter API key is invalid")
    if type(batch_name) is not str or not batch_name.startswith("batch-"):
        raise OpenRouterJsonFirstBatchV1Error("OpenRouter batch ID is invalid")
    raw = transport(
        OPENROUTER_BATCH_ENDPOINT + "/" + batch_name,
        {"Authorization": "Bearer " + api_key},
        timeout_seconds,
    )
    if summarize_openrouter_batch_v1(raw)["batch_name"] != batch_name:
        raise OpenRouterJsonFirstBatchV1Error("OpenRouter polled batch identity drifted")
    return raw


def _batch_cost(input_tokens: int, output_tokens: int) -> Decimal:
    return (
        Decimal(input_tokens) * OPENROUTER_BATCH_INPUT_USD_PER_MILLION
        + Decimal(output_tokens) * OPENROUTER_BATCH_OUTPUT_USD_PER_MILLION
    ) / Decimal(1_000_000)


def decode_completed_openrouter_batch_v1(
    *, raw: bytes, expected_request_ids: Sequence[str], elapsed_seconds: str
) -> CompletedOpenRouterBatchV1:
    value = _json_object(raw, "completed OpenRouter batch")
    summary = summarize_openrouter_batch_v1(raw)
    if summary["state"] != "BATCH_STATE_SUCCEEDED":
        raise OpenRouterJsonFirstBatchV1Error("OpenRouter batch did not succeed")
    expected = [_request_id(item) for item in expected_request_ids]
    results = value.get("results")
    if type(results) is not list:
        raise OpenRouterJsonFirstBatchV1Error("OpenRouter batch results are absent")
    by_id: dict[str, dict[str, Any]] = {}
    for item in results:
        if type(item) is not dict:
            raise OpenRouterJsonFirstBatchV1Error("OpenRouter batch result drifted")
        request_id = _request_id(item.get("custom_id"))
        if request_id in by_id:
            raise OpenRouterJsonFirstBatchV1Error("OpenRouter batch result ID is duplicate")
        by_id[request_id] = item
    if set(by_id) != set(expected):
        raise OpenRouterJsonFirstBatchV1Error("OpenRouter batch request-ID set drifted")
    provider_results: dict[str, ProviderResultV1] = {}
    failures: dict[str, dict[str, Any]] = {}
    allocated_cost = Decimal(0)
    for request_id in expected:
        item = by_id[request_id]
        error = item.get("error")
        response = item.get("response")
        if error is not None:
            if type(error) is not dict:
                raise OpenRouterJsonFirstBatchV1Error("OpenRouter batch error drifted")
            failures[request_id] = json.loads(canonical_json_bytes_v1(error))
            continue
        if type(response) is not dict or response.get("status_code") != 200:
            raise OpenRouterJsonFirstBatchV1Error("OpenRouter batch response status drifted")
        if item.get("id") != response.get("request_id") or type(response.get("body")) is not dict:
            raise OpenRouterJsonFirstBatchV1Error("OpenRouter batch response identity drifted")
        body = json.loads(canonical_json_bytes_v1(response["body"]))
        usage = body.get("usage")
        if type(usage) is not dict:
            raise OpenRouterJsonFirstBatchV1Error("OpenRouter per-request usage is absent")
        input_tokens = usage.get("prompt_tokens")
        output_tokens = usage.get("completion_tokens")
        if any(type(token) is not int or token < 0 for token in (input_tokens, output_tokens)):
            raise OpenRouterJsonFirstBatchV1Error("OpenRouter per-request token count drifted")
        cost = _batch_cost(input_tokens, output_tokens)
        allocated_cost += cost
        body["usage"]["cost"] = float(cost)
        body_raw = canonical_json_bytes_v1(body) + b"\n"
        text, response_id, model, _, parsed_usage = _openrouter_response_v1(body_raw)
        parsed_usage["actual_cost_usd"] = format(cost, ".12f")
        parsed_usage["billing_disposition"] = "BILLED_ACTUAL_ALLOCATED_BATCH"
        parsed_usage["pricing"] = {
            "currency": "USD",
            "input_usd_per_million": str(OPENROUTER_BATCH_INPUT_USD_PER_MILLION),
            "output_usd_per_million": str(OPENROUTER_BATCH_OUTPUT_USD_PER_MILLION),
            "service_tier": "batch",
        }
        attempt = {
            "attempt_ordinal": 1,
            "credential_slot": "OPENROUTER_SLOT_1",
            "elapsed_seconds": elapsed_seconds,
            "http_status": 200,
            "outcome": "COMPLETED_BATCH",
            "provider": "OPENROUTER_BATCH",
            "usage": json.loads(canonical_json_bytes_v1(parsed_usage)),
        }
        provider_results[request_id] = ProviderResultV1(
            output_text=text,
            raw_response_bytes=body_raw,
            provider_name="OPENROUTER_BATCH",
            provider_model=model,
            service_tier="batch",
            attempts=(attempt,),
            usage=parsed_usage,
            response_id_sha256=sha256(response_id.encode()).hexdigest(),
        )
    top_usage = value.get("usage")
    if type(top_usage) is not dict or type(top_usage.get("cost")) not in {int, float}:
        raise OpenRouterJsonFirstBatchV1Error("OpenRouter batch total cost is absent")
    if allocated_cost != Decimal(str(top_usage["cost"])):
        raise OpenRouterJsonFirstBatchV1Error("OpenRouter batch allocated cost does not close")
    return CompletedOpenRouterBatchV1(
        batch_name=summary["batch_name"],
        state=summary["state"],
        provider_results=provider_results,
        failures=failures,
        raw_operation_bytes=raw,
    )
