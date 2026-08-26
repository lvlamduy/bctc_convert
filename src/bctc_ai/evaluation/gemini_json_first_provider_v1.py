"""Explicit provider policies for Gemini JSON-first page extraction.

Prompt pilots can use one pinned Google Vertex endpoint through OpenRouter or
an explicitly selected direct Google standard request.  A route never falls
through to another provider.  Corpus production uses a separate Google Batch
runner after the page contract is frozen.
"""

from __future__ import annotations

import base64
import http.client
import json
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any

from bctc_ai.source_structure.contracts_v1 import canonical_clone_v1

FORMAT_VERSION = "GEMINI_JSON_FIRST_PROVIDER_V1"
GOOGLE_MODEL = "gemini-3.7-flash"
GOOGLE_SERVICE_TIER = "flex"
GOOGLE_STANDARD_SERVICE_TIER = "standard"
GOOGLE_BATCH_SERVICE_TIER = "batch"
GOOGLE_OUTPUT_CONTRACT_MODES = frozenset({"JSON_SCHEMA", "PROMPT_JSON"})
EXECUTION_POLICIES = frozenset(
    {"OPENROUTER_PILOT", "GOOGLE_DIRECT_DIAGNOSTIC", "GOOGLE_DIRECT_STANDARD"}
)
OPENROUTER_MODEL = "google/gemini-3.7-flash"
OPENROUTER_PROVIDER = "google-vertex/global/flex"
OPENROUTER_SERVICE_TIER = "flex"
GOOGLE_FLEX_INPUT_USD_PER_MILLION = Decimal("0.375")
GOOGLE_FLEX_OUTPUT_USD_PER_MILLION = Decimal("1.875")
GOOGLE_STANDARD_INPUT_USD_PER_MILLION = Decimal("0.75")
GOOGLE_STANDARD_OUTPUT_USD_PER_MILLION = Decimal("3.75")

_GOOGLE_KEY = re.compile(r"^\s*GEMINI_API_KEY\s*=\s*[\"']?([^\"'\s]+)[\"']?\s*$", re.MULTILINE)
_OPENROUTER_KEY = re.compile(
    r"^\s*OPENROUTER_API_KEY\s*=\s*[\"']?([^\"'\s]+)[\"']?\s*$", re.MULTILINE
)


class GeminiJsonFirstProviderV1Error(RuntimeError):
    """The provider chain could not return an authenticated complete response."""

    raw_response_bytes: bytes | None = None
    attempts: tuple[dict[str, Any], ...] = ()


class _ProviderHttpError(GeminiJsonFirstProviderV1Error):
    def __init__(self, *, status: int, provider: str) -> None:
        super().__init__(f"{provider} returned HTTP {status}")
        self.status = status
        self.provider = provider


class _RetryableZeroUsageResponse(GeminiJsonFirstProviderV1Error):
    pass


class _ProviderConnectionError(GeminiJsonFirstProviderV1Error):
    pass


@dataclass(frozen=True)
class ProviderResultV1:
    output_text: str
    raw_response_bytes: bytes
    provider_name: str
    provider_model: str
    service_tier: str
    attempts: tuple[dict[str, Any], ...]
    usage: dict[str, Any]
    response_id_sha256: str


def replay_openrouter_provider_result_v1(
    raw_response_bytes: bytes,
    *,
    attempts: tuple[dict[str, Any], ...],
) -> ProviderResultV1:
    """Rebuild one already billed OpenRouter result without another API request."""

    if type(raw_response_bytes) is not bytes or not raw_response_bytes:
        raise GeminiJsonFirstProviderV1Error("OpenRouter replay response bytes are absent")
    if (
        type(attempts) is not tuple
        or not attempts
        or any(type(attempt) is not dict for attempt in attempts)
    ):
        raise GeminiJsonFirstProviderV1Error("OpenRouter replay attempts are invalid")
    text, response_id, model, provider, usage = _openrouter_response_v1(raw_response_bytes)
    envelope = _json_object(raw_response_bytes, "OpenRouter")
    if envelope.get("service_tier") != OPENROUTER_SERVICE_TIER:
        raise GeminiJsonFirstProviderV1Error("OpenRouter replay service tier drifted")
    return ProviderResultV1(
        output_text=text,
        raw_response_bytes=raw_response_bytes,
        provider_name=provider,
        provider_model=model,
        service_tier=OPENROUTER_SERVICE_TIER,
        attempts=tuple(canonical_clone_v1(list(attempts))),
        usage=usage,
        response_id_sha256=sha256(response_id.encode("utf-8")).hexdigest(),
    )


def replay_google_standard_provider_result_v1(
    raw_response_bytes: bytes,
    *,
    attempts: tuple[dict[str, Any], ...],
) -> ProviderResultV1:
    """Rebuild one already billed direct-Google standard result without a call."""

    if type(raw_response_bytes) is not bytes or not raw_response_bytes:
        raise GeminiJsonFirstProviderV1Error("Google replay response bytes are absent")
    if (
        type(attempts) is not tuple
        or not attempts
        or any(type(attempt) is not dict for attempt in attempts)
        or any(attempt.get("provider") != "GOOGLE_GEMINI_API" for attempt in attempts)
        or attempts[-1].get("outcome") != "COMPLETED"
    ):
        raise GeminiJsonFirstProviderV1Error("Google replay attempts are invalid")
    text, response_id, model, usage = _google_generate_content_response_v1(
        raw_response_bytes,
        service_tier=GOOGLE_STANDARD_SERVICE_TIER,
    )
    return ProviderResultV1(
        output_text=text,
        raw_response_bytes=raw_response_bytes,
        provider_name="GOOGLE_GEMINI_API",
        provider_model=model,
        service_tier=GOOGLE_STANDARD_SERVICE_TIER,
        attempts=tuple(canonical_clone_v1(list(attempts))),
        usage=usage,
        response_id_sha256=sha256(response_id.encode("utf-8")).hexdigest(),
    )


def _load_unique_keys(path: Path, pattern: re.Pattern[str], label: str) -> list[str]:
    if not path.is_file():
        raise GeminiJsonFirstProviderV1Error(f"{label} credential file is absent")
    mode = path.stat().st_mode & 0o777
    if mode & 0o077:
        raise GeminiJsonFirstProviderV1Error(f"{label} credential file must have mode 0600")
    values: list[str] = []
    for value in pattern.findall(path.read_text(encoding="utf-8")):
        if len(value) >= 20 and value not in values:
            values.append(value)
    if not values:
        raise GeminiJsonFirstProviderV1Error(f"{label} credential file contains no usable key")
    return values


def load_google_api_key_slots_v1(path: Path) -> list[str]:
    """Load ordered Google key slots from a protected local file."""

    return _load_unique_keys(path, _GOOGLE_KEY, "Google")


def load_openrouter_api_key_v1(path: Path) -> str:
    """Load the sole OpenRouter key from a protected local file."""

    values = _load_unique_keys(path, _OPENROUTER_KEY, "OpenRouter")
    if len(values) != 1:
        raise GeminiJsonFirstProviderV1Error(
            "OpenRouter credential file must contain exactly one key"
        )
    return values[0]


def _post_json_v1(
    url: str, headers: dict[str, str], body: dict[str, Any], timeout_seconds: int
) -> bytes:
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        provider = "GOOGLE" if "googleapis.com" in url else "OPENROUTER"
        # Provider error bodies may reflect request metadata.  Never include them.
        exc.read()
        raise _ProviderHttpError(status=exc.code, provider=provider) from exc
    except (TimeoutError, urllib.error.URLError, ConnectionError, http.client.HTTPException) as exc:
        raise _ProviderConnectionError("provider request failed or timed out") from exc


def _json_object(raw: bytes, provider: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise GeminiJsonFirstProviderV1Error(f"{provider} response is not JSON") from exc
    if type(value) is not dict:
        raise GeminiJsonFirstProviderV1Error(f"{provider} response is not one JSON object")
    return value


def _nonnegative_int(value: Any, label: str, *, optional: bool = False) -> int:
    if value is None and optional:
        return 0
    if type(value) is not int or value < 0:
        raise GeminiJsonFirstProviderV1Error(f"{label} token count drifted")
    return value


def _google_response_v1(raw: bytes, *, service_tier: str) -> tuple[str, str, str, dict[str, Any]]:
    response = _json_object(raw, "Google")
    if response.get("status") != "completed":
        raise GeminiJsonFirstProviderV1Error("Google interaction did not complete")
    response_id = response.get("id")
    model = response.get("model")
    steps = response.get("steps")
    usage = response.get("usage")
    if response_id is not None and (type(response_id) is not str or not response_id):
        raise GeminiJsonFirstProviderV1Error("Google response ID drifted")
    if type(model) is not str or not model:
        raise GeminiJsonFirstProviderV1Error("Google model identity is absent")
    if type(steps) is not list or type(usage) is not dict:
        raise GeminiJsonFirstProviderV1Error("Google response steps or usage are absent")
    text_parts: list[str] = []
    for step in steps:
        if type(step) is not dict or step.get("type") != "model_output":
            continue
        content = step.get("content")
        if type(content) is not list:
            raise GeminiJsonFirstProviderV1Error("Google model output content drifted")
        for part in content:
            if type(part) is dict and part.get("type") == "text":
                text = part.get("text")
                if type(text) is not str:
                    raise GeminiJsonFirstProviderV1Error("Google text output drifted")
                text_parts.append(text)
    if not text_parts:
        raise GeminiJsonFirstProviderV1Error("Google response contains no model text")
    input_tokens = _nonnegative_int(usage.get("total_input_tokens"), "Google input")
    output_tokens = _nonnegative_int(usage.get("total_output_tokens"), "Google output")
    thought_tokens = _nonnegative_int(
        usage.get("total_thought_tokens"), "Google thought", optional=True
    )
    cached_tokens = _nonnegative_int(
        usage.get("total_cached_tokens"), "Google cached", optional=True
    )
    total_tokens = _nonnegative_int(usage.get("total_tokens"), "Google total")
    if total_tokens < input_tokens + output_tokens:
        raise GeminiJsonFirstProviderV1Error("Google total token count is inconsistent")
    if service_tier == GOOGLE_SERVICE_TIER:
        input_price = GOOGLE_FLEX_INPUT_USD_PER_MILLION
        output_price = GOOGLE_FLEX_OUTPUT_USD_PER_MILLION
    elif service_tier == GOOGLE_STANDARD_SERVICE_TIER:
        input_price = GOOGLE_STANDARD_INPUT_USD_PER_MILLION
        output_price = GOOGLE_STANDARD_OUTPUT_USD_PER_MILLION
    else:
        raise GeminiJsonFirstProviderV1Error("Google service tier is invalid")
    estimated = (
        Decimal(input_tokens) * input_price + Decimal(output_tokens + thought_tokens) * output_price
    ) / Decimal(1_000_000)
    accounting = {
        "billing_disposition": "ESTIMATED_LIST_PRICE",
        "cached_input_tokens": cached_tokens,
        "estimated_cost_usd": format(estimated, ".12f"),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "thought_tokens": thought_tokens,
        "total_tokens": total_tokens,
        "pricing": {
            "currency": "USD",
            "effective_through": "2026-12-31",
            "input_usd_per_million": str(input_price),
            "output_including_thought_usd_per_million": str(output_price),
            "service_tier": service_tier,
        },
    }
    return "".join(text_parts), response_id or "", model, accounting


def _google_generate_content_response_v1(
    raw: bytes, *, service_tier: str
) -> tuple[str, str, str, dict[str, Any]]:
    response = _json_object(raw, "Google")
    candidates = response.get("candidates")
    usage = response.get("usageMetadata")
    response_id = response.get("responseId")
    model = response.get("modelVersion")
    if type(candidates) is not list or len(candidates) != 1 or type(candidates[0]) is not dict:
        raise GeminiJsonFirstProviderV1Error("Google candidate array drifted")
    candidate = candidates[0]
    if candidate.get("finishReason") != "STOP":
        raise GeminiJsonFirstProviderV1Error("Google response did not finish normally")
    content = candidate.get("content")
    if type(content) is not dict or type(content.get("parts")) is not list:
        raise GeminiJsonFirstProviderV1Error("Google response content is absent")
    text_parts = []
    for part in content["parts"]:
        if type(part) is dict and "text" in part:
            if type(part["text"]) is not str:
                raise GeminiJsonFirstProviderV1Error("Google text output drifted")
            text_parts.append(part["text"])
    if not text_parts:
        raise GeminiJsonFirstProviderV1Error("Google response contains no model text")
    if type(response_id) is not str or not response_id:
        raise GeminiJsonFirstProviderV1Error("Google response ID is absent")
    if type(model) is not str or not model:
        raise GeminiJsonFirstProviderV1Error("Google model identity is absent")
    if type(usage) is not dict:
        raise GeminiJsonFirstProviderV1Error("Google usage metadata is absent")
    input_tokens = _nonnegative_int(usage.get("promptTokenCount"), "Google input")
    output_tokens = _nonnegative_int(usage.get("candidatesTokenCount"), "Google output")
    thought_tokens = _nonnegative_int(
        usage.get("thoughtsTokenCount"), "Google thought", optional=True
    )
    cached_tokens = _nonnegative_int(
        usage.get("cachedContentTokenCount"), "Google cached", optional=True
    )
    total_tokens = _nonnegative_int(usage.get("totalTokenCount"), "Google total")
    if total_tokens < input_tokens + output_tokens:
        raise GeminiJsonFirstProviderV1Error("Google total token count is inconsistent")
    if service_tier == GOOGLE_STANDARD_SERVICE_TIER:
        input_price = GOOGLE_STANDARD_INPUT_USD_PER_MILLION
        output_price = GOOGLE_STANDARD_OUTPUT_USD_PER_MILLION
    elif service_tier == GOOGLE_BATCH_SERVICE_TIER:
        input_price = GOOGLE_FLEX_INPUT_USD_PER_MILLION
        output_price = GOOGLE_FLEX_OUTPUT_USD_PER_MILLION
    else:
        raise GeminiJsonFirstProviderV1Error("generateContent service tier is invalid")
    estimated = (
        Decimal(input_tokens) * input_price + Decimal(output_tokens + thought_tokens) * output_price
    ) / Decimal(1_000_000)
    accounting = {
        "billing_disposition": "ESTIMATED_LIST_PRICE",
        "cached_input_tokens": cached_tokens,
        "estimated_cost_usd": format(estimated, ".12f"),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "thought_tokens": thought_tokens,
        "total_tokens": total_tokens,
        "pricing": {
            "currency": "USD",
            "effective_through": "2026-12-31",
            "input_usd_per_million": str(input_price),
            "output_including_thought_usd_per_million": str(output_price),
            "service_tier": service_tier,
        },
    }
    return "".join(text_parts), response_id, model, accounting


def _openrouter_response_v1(raw: bytes) -> tuple[str, str, str, str, dict[str, Any]]:
    response = _json_object(raw, "OpenRouter")
    error = response.get("error")
    if type(error) is dict and type(error.get("code")) is int:
        raise _ProviderHttpError(status=error["code"], provider="OPENROUTER")
    choices = response.get("choices")
    usage = response.get("usage")
    if type(choices) is not list or len(choices) != 1 or type(choices[0]) is not dict:
        raise GeminiJsonFirstProviderV1Error("OpenRouter choice array drifted")
    choice = choices[0]
    message = choice.get("message")
    if choice.get("finish_reason") == "error" and type(usage) is dict:
        if usage.get("total_tokens") == 0 and usage.get("cost") == 0:
            raise _RetryableZeroUsageResponse(
                "OpenRouter provider returned an unbilled zero-usage error"
            )
    if choice.get("finish_reason") != "stop" or type(message) is not dict:
        raise GeminiJsonFirstProviderV1Error("OpenRouter response did not finish normally")
    text = message.get("content")
    response_id = response.get("id")
    model = response.get("model")
    provider = response.get("provider")
    if any(type(item) is not str or not item for item in (text, response_id, model, provider)):
        raise GeminiJsonFirstProviderV1Error("OpenRouter response identity or text is absent")
    if type(usage) is not dict:
        raise GeminiJsonFirstProviderV1Error("OpenRouter usage is absent")
    input_tokens = _nonnegative_int(usage.get("prompt_tokens"), "OpenRouter input")
    output_tokens = _nonnegative_int(usage.get("completion_tokens"), "OpenRouter output")
    total_tokens = _nonnegative_int(usage.get("total_tokens"), "OpenRouter total")
    if total_tokens != input_tokens + output_tokens:
        raise GeminiJsonFirstProviderV1Error("OpenRouter token equation does not close")
    cost = usage.get("cost")
    if type(cost) not in {int, float} or cost < 0:
        raise GeminiJsonFirstProviderV1Error("OpenRouter actual cost is absent")
    details = usage.get("completion_tokens_details")
    thought_tokens = 0
    if type(details) is dict and details.get("reasoning_tokens") is not None:
        thought_tokens = _nonnegative_int(
            details["reasoning_tokens"], "OpenRouter thought", optional=True
        )
    accounting = {
        "actual_cost_usd": format(Decimal(str(cost)), ".12f"),
        "billing_disposition": "BILLED_ACTUAL",
        "cached_input_tokens": 0,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "thought_tokens": thought_tokens,
        "total_tokens": total_tokens,
    }
    return text, response_id, model, provider, accounting


def _google_body_v1(
    *,
    image: bytes,
    media_type: str,
    prompt: str,
    response_schema: dict[str, Any],
    output_contract_mode: str,
    service_tier: str,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "generation_config": {"thinking_level": "low"},
        "input": [
            {"type": "text", "text": prompt},
            {
                "type": "image",
                "data": base64.b64encode(image).decode("ascii"),
                "mime_type": media_type,
            },
        ],
        "model": GOOGLE_MODEL,
        "store": False,
    }
    if service_tier == GOOGLE_SERVICE_TIER:
        body["service_tier"] = service_tier
    elif service_tier != GOOGLE_STANDARD_SERVICE_TIER:
        raise GeminiJsonFirstProviderV1Error("Google service tier is invalid")
    if output_contract_mode == "JSON_SCHEMA":
        body["response_format"] = {
            "type": "text",
            "mime_type": "application/json",
            "schema": response_schema,
        }
    return body


def _google_generate_content_body_v1(
    *,
    image: bytes | None,
    media_type: str,
    prompt: str,
    response_schema: dict[str, Any],
    output_contract_mode: str,
    file_uri: str | None = None,
) -> dict[str, Any]:
    if (image is None) == (file_uri is None):
        raise GeminiJsonFirstProviderV1Error(
            "generateContent requires exactly one inline image or uploaded file URI"
        )
    if file_uri is not None and (type(file_uri) is not str or not file_uri.startswith("https://")):
        raise GeminiJsonFirstProviderV1Error("uploaded file URI is invalid")
    generation_config: dict[str, Any] = {
        "maxOutputTokens": 65536,
        "responseMimeType": "application/json",
        "temperature": 0,
        "thinkingConfig": {"thinkingLevel": "LOW"},
    }
    if output_contract_mode == "JSON_SCHEMA":
        generation_config["responseJsonSchema"] = response_schema
    media_part = (
        {
            "inlineData": {
                "data": base64.b64encode(image).decode("ascii"),
                "mimeType": media_type,
            }
        }
        if image is not None
        else {"fileData": {"fileUri": file_uri, "mimeType": media_type}}
    )
    return {
        "contents": [
            {
                "parts": [media_part, {"text": prompt}],
                "role": "user",
            }
        ],
        "generationConfig": generation_config,
        "store": False,
    }


def _openrouter_body_v1(
    *,
    image: bytes,
    media_type: str,
    prompt: str,
    response_schema: dict[str, Any],
    output_contract_mode: str,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "max_tokens": 65536,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:"
                            + media_type
                            + ";base64,"
                            + base64.b64encode(image).decode("ascii")
                        },
                    },
                ],
            }
        ],
        "model": OPENROUTER_MODEL,
        "provider": {
            "allow_fallbacks": False,
            "data_collection": "deny",
            "only": [OPENROUTER_PROVIDER],
            "require_parameters": True,
        },
        "reasoning": {"effort": "low"},
        "seed": 0,
        "usage": {"include": True},
    }
    if output_contract_mode == "JSON_SCHEMA":
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "financial_page_json_v1",
                "strict": True,
                "schema": response_schema,
            },
        }
    return body


def _attempt(
    *,
    ordinal: int,
    provider: str,
    slot: str,
    elapsed: float,
    outcome: str,
    http_status: int | None,
    usage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "attempt_ordinal": ordinal,
        "credential_slot": slot,
        "elapsed_seconds": format(elapsed, ".3f"),
        "http_status": http_status,
        "outcome": outcome,
        "provider": provider,
        "usage": canonical_clone_v1(usage) if usage is not None else None,
    }


def call_gemini_json_first_v1(
    *,
    google_api_keys: list[str] | None,
    google_credential_slots: list[str] | None = None,
    openrouter_api_key: str | None,
    image: bytes,
    media_type: str,
    prompt: str,
    response_schema: dict[str, Any],
    output_contract_mode: str = "JSON_SCHEMA",
    execution_policy: str = "OPENROUTER_PILOT",
    timeout_seconds: int = 900,
    flex_retries_per_slot: int = 2,
    openrouter_retries: int = 2,
    retry_delay_seconds: float = 5.0,
    transport: Callable[[str, dict[str, str], dict[str, Any], int], bytes] = _post_json_v1,
    sleep: Callable[[float], None] = time.sleep,
    on_attempt: Callable[[dict[str, Any]], None] | None = None,
) -> ProviderResultV1:
    """Call exactly the provider route named by the explicit execution policy."""

    if execution_policy not in EXECUTION_POLICIES:
        raise GeminiJsonFirstProviderV1Error("execution policy is invalid")
    if media_type not in {"image/png", "image/jpeg"} or not image:
        raise GeminiJsonFirstProviderV1Error("one nonempty PNG or JPEG input is required")
    if type(prompt) is not str or not prompt:
        raise GeminiJsonFirstProviderV1Error("prompt must be nonempty")
    if output_contract_mode not in GOOGLE_OUTPUT_CONTRACT_MODES:
        raise GeminiJsonFirstProviderV1Error("output contract mode is invalid")
    if (
        timeout_seconds < 60
        or flex_retries_per_slot < 1
        or openrouter_retries < 1
        or retry_delay_seconds < 0
    ):
        raise GeminiJsonFirstProviderV1Error("provider retry policy is invalid")
    attempts: list[dict[str, Any]] = []

    def record_attempt(attempt: dict[str, Any]) -> None:
        attempts.append(attempt)
        if on_attempt is not None:
            on_attempt(canonical_clone_v1(attempt))

    if execution_policy in {"GOOGLE_DIRECT_DIAGNOSTIC", "GOOGLE_DIRECT_STANDARD"}:
        if not google_api_keys or any(
            type(key) is not str or len(key) < 20 for key in google_api_keys
        ):
            raise GeminiJsonFirstProviderV1Error(
                "Google direct execution requires one or more API key slots"
            )
        if google_credential_slots is None:
            google_credential_slots = [
                f"GOOGLE_SLOT_{index}" for index in range(1, len(google_api_keys) + 1)
            ]
        if len(google_credential_slots) != len(google_api_keys) or any(
            type(slot) is not str or not slot.startswith("GOOGLE_SLOT_")
            for slot in google_credential_slots
        ):
            raise GeminiJsonFirstProviderV1Error("Google credential slot labels drifted")
        google_service_tier = (
            GOOGLE_SERVICE_TIER
            if execution_policy == "GOOGLE_DIRECT_DIAGNOSTIC"
            else GOOGLE_STANDARD_SERVICE_TIER
        )
        if execution_policy == "GOOGLE_DIRECT_STANDARD":
            google_body = _google_generate_content_body_v1(
                image=image,
                media_type=media_type,
                prompt=prompt,
                response_schema=response_schema,
                output_contract_mode=output_contract_mode,
            )
            google_url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                + GOOGLE_MODEL
                + ":generateContent"
            )
        else:
            google_body = _google_body_v1(
                image=image,
                media_type=media_type,
                prompt=prompt,
                response_schema=response_schema,
                output_contract_mode=output_contract_mode,
                service_tier=google_service_tier,
            )
            google_url = "https://generativelanguage.googleapis.com/v1beta/interactions"
        for api_key, credential_slot in zip(google_api_keys, google_credential_slots, strict=True):
            for retry_index in range(flex_retries_per_slot):
                started = time.perf_counter()
                raw: bytes | None = None
                try:
                    raw = transport(
                        google_url,
                        {
                            "Content-Type": "application/json",
                            "x-goog-api-key": api_key,
                            **(
                                {"Api-Revision": "2026-05-20"}
                                if execution_policy == "GOOGLE_DIRECT_DIAGNOSTIC"
                                else {}
                            ),
                        },
                        google_body,
                        timeout_seconds,
                    )
                    if execution_policy == "GOOGLE_DIRECT_STANDARD":
                        text, response_id, model, usage = _google_generate_content_response_v1(
                            raw, service_tier=google_service_tier
                        )
                    else:
                        text, response_id, model, usage = _google_response_v1(
                            raw, service_tier=google_service_tier
                        )
                except _ProviderConnectionError:
                    record_attempt(
                        _attempt(
                            ordinal=len(attempts) + 1,
                            provider="GOOGLE_GEMINI_API",
                            slot=credential_slot,
                            elapsed=time.perf_counter() - started,
                            outcome="TRANSPORT_TIMEOUT_OR_CONNECTION_ERROR",
                            http_status=None,
                        )
                    )
                    if retry_index + 1 < flex_retries_per_slot:
                        sleep(retry_delay_seconds * (2**retry_index))
                        continue
                    break
                except _ProviderHttpError as exc:
                    elapsed = time.perf_counter() - started
                    outcome = (
                        "QUOTA_OR_RATE_LIMIT"
                        if exc.status == 429
                        else "CAPACITY_SHED"
                        if exc.status == 503
                        else "TRANSIENT_PROVIDER_ERROR"
                        if exc.status in {500, 502, 504}
                        else "NON_EXHAUSTION_HTTP_ERROR"
                    )
                    record_attempt(
                        _attempt(
                            ordinal=len(attempts) + 1,
                            provider="GOOGLE_GEMINI_API",
                            slot=credential_slot,
                            elapsed=elapsed,
                            outcome=outcome,
                            http_status=exc.status,
                        )
                    )
                    if (
                        exc.status in {429, 500, 502, 503, 504}
                        and retry_index + 1 < flex_retries_per_slot
                    ):
                        sleep(retry_delay_seconds * (2**retry_index))
                        continue
                    break
                except GeminiJsonFirstProviderV1Error as exc:
                    record_attempt(
                        _attempt(
                            ordinal=len(attempts) + 1,
                            provider="GOOGLE_GEMINI_API",
                            slot=credential_slot,
                            elapsed=time.perf_counter() - started,
                            outcome="INVALID_OR_UNVERIFIABLE_RESPONSE",
                            http_status=200,
                        )
                    )
                    exc.raw_response_bytes = raw
                    exc.attempts = tuple(attempts)
                    raise
                record_attempt(
                    _attempt(
                        ordinal=len(attempts) + 1,
                        provider="GOOGLE_GEMINI_API",
                        slot=credential_slot,
                        elapsed=time.perf_counter() - started,
                        outcome="COMPLETED",
                        http_status=200,
                        usage=usage,
                    )
                )
                return ProviderResultV1(
                    output_text=text,
                    raw_response_bytes=raw,
                    provider_name="GOOGLE_GEMINI_API",
                    provider_model=model,
                    service_tier=google_service_tier,
                    attempts=tuple(attempts),
                    usage=usage,
                    response_id_sha256=(
                        sha256(response_id.encode("utf-8")).hexdigest()
                        if response_id
                        else sha256(raw).hexdigest()
                    ),
                )
        failure = GeminiJsonFirstProviderV1Error(
            "direct Google execution ended without a complete response; no fallback is allowed"
        )
        failure.attempts = tuple(attempts)
        raise failure
    if google_api_keys:
        raise GeminiJsonFirstProviderV1Error(
            "OpenRouter pilot must not receive direct Google credentials"
        )
    if openrouter_api_key is None:
        raise GeminiJsonFirstProviderV1Error("OpenRouter pilot credential is absent")
    body = _openrouter_body_v1(
        image=image,
        media_type=media_type,
        prompt=prompt,
        response_schema=response_schema,
        output_contract_mode=output_contract_mode,
    )
    for retry_index in range(openrouter_retries):
        started = time.perf_counter()
        raw: bytes | None = None
        try:
            raw = transport(
                "https://openrouter.ai/api/v1/chat/completions",
                {
                    "Authorization": "Bearer " + openrouter_api_key,
                    "Content-Type": "application/json",
                    "X-OpenRouter-Title": "bctc-ai Gemini JSON-first",
                },
                body,
                timeout_seconds,
            )
            text, response_id, model, provider, usage = _openrouter_response_v1(raw)
        except _ProviderConnectionError:
            record_attempt(
                _attempt(
                    ordinal=len(attempts) + 1,
                    provider="OPENROUTER",
                    slot="OPENROUTER_SLOT_1",
                    elapsed=time.perf_counter() - started,
                    outcome="TRANSPORT_TIMEOUT_OR_CONNECTION_ERROR",
                    http_status=None,
                )
            )
            if retry_index + 1 < openrouter_retries:
                sleep(retry_delay_seconds * (2**retry_index))
                continue
            failure = GeminiJsonFirstProviderV1Error("OpenRouter pilot failed")
            failure.attempts = tuple(attempts)
            raise failure from None
        except _RetryableZeroUsageResponse:
            record_attempt(
                _attempt(
                    ordinal=len(attempts) + 1,
                    provider="OPENROUTER",
                    slot="OPENROUTER_SLOT_1",
                    elapsed=time.perf_counter() - started,
                    outcome="ZERO_USAGE_PROVIDER_ERROR",
                    http_status=200,
                )
            )
            if retry_index + 1 < openrouter_retries:
                sleep(retry_delay_seconds * (2**retry_index))
                continue
            failure = GeminiJsonFirstProviderV1Error(
                "OpenRouter pilot exhausted zero-usage retries"
            )
            failure.raw_response_bytes = raw
            failure.attempts = tuple(attempts)
            raise failure from None
        except _ProviderHttpError as exc:
            retryable = exc.status in {429, 500, 502, 503, 504}
            record_attempt(
                _attempt(
                    ordinal=len(attempts) + 1,
                    provider="OPENROUTER",
                    slot="OPENROUTER_SLOT_1",
                    elapsed=time.perf_counter() - started,
                    outcome="TRANSIENT_HTTP_ERROR" if retryable else "HTTP_ERROR",
                    http_status=exc.status,
                )
            )
            if retryable and retry_index + 1 < openrouter_retries:
                sleep(retry_delay_seconds * (2**retry_index))
                continue
            failure = GeminiJsonFirstProviderV1Error("OpenRouter pilot failed")
            failure.raw_response_bytes = raw
            failure.attempts = tuple(attempts)
            raise failure from exc
        except GeminiJsonFirstProviderV1Error as exc:
            record_attempt(
                _attempt(
                    ordinal=len(attempts) + 1,
                    provider="OPENROUTER",
                    slot="OPENROUTER_SLOT_1",
                    elapsed=time.perf_counter() - started,
                    outcome="INVALID_OR_UNVERIFIABLE_RESPONSE",
                    http_status=200,
                )
            )
            exc.raw_response_bytes = raw
            exc.attempts = tuple(attempts)
            raise
        record_attempt(
            _attempt(
                ordinal=len(attempts) + 1,
                provider="OPENROUTER",
                slot="OPENROUTER_SLOT_1",
                elapsed=time.perf_counter() - started,
                outcome="COMPLETED",
                http_status=200,
                usage=usage,
            )
        )
        return ProviderResultV1(
            output_text=text,
            raw_response_bytes=raw,
            provider_name=provider,
            provider_model=model,
            service_tier=OPENROUTER_SERVICE_TIER,
            attempts=tuple(attempts),
            usage=usage,
            response_id_sha256=sha256(response_id.encode("utf-8")).hexdigest(),
        )
    raise AssertionError("unreachable OpenRouter retry state")
