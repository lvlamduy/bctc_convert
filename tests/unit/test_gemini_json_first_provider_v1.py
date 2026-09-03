from __future__ import annotations

import json

import pytest

import bctc_ai.evaluation.gemini_json_first_provider_v1 as provider
from bctc_ai.evaluation.gemini_json_first_provider_v1 import (
    GeminiJsonFirstProviderV1Error,
    call_gemini_json_first_v1,
    extract_completed_provider_response_text_v1,
    load_google_api_key_slots_v1,
    replay_google_standard_provider_result_v1,
    replay_openrouter_provider_result_v1,
)


def _google_response() -> bytes:
    return json.dumps(
        {
            "status": "completed",
            "model": "gemini-3.7-flash-001",
            "usage": {
                "total_input_tokens": 5000,
                "total_output_tokens": 1000,
                "total_thought_tokens": 100,
                "total_tokens": 6100,
            },
            "steps": [
                {
                    "type": "model_output",
                    "content": [
                        {
                            "type": "text",
                            "text": '{"status":"NO_RELEVANT_FINANCIAL_CONTENT","sections":[]}',
                        }
                    ],
                }
            ],
        }
    ).encode()


def _google_generate_content_response() -> bytes:
    return json.dumps(
        {
            "responseId": "google-response-id",
            "modelVersion": "gemini-3.7-flash",
            "candidates": [
                {
                    "finishReason": "STOP",
                    "content": {
                        "parts": [
                            {"text": '{"status":"NO_RELEVANT_FINANCIAL_CONTENT","sections":[]}'}
                        ]
                    },
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 5000,
                "candidatesTokenCount": 1000,
                "thoughtsTokenCount": 100,
                "totalTokenCount": 6100,
            },
        }
    ).encode()


def _openrouter_response(*, provider_name: str = "Google", service_tier: str = "flex") -> bytes:
    return json.dumps(
        {
            "id": "openrouter-response-id",
            "model": "google/gemini-3.7-flash",
            "provider": provider_name,
            "service_tier": service_tier,
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": '{"status":"NO_RELEVANT_FINANCIAL_CONTENT","sections":[]}'
                    },
                }
            ],
            "usage": {
                "prompt_tokens": 5000,
                "completion_tokens": 1000,
                "total_tokens": 6000,
                "cost": 0.00375,
                "completion_tokens_details": {"reasoning_tokens": 100},
            },
        }
    ).encode()


@pytest.mark.parametrize(
    "response",
    [_google_response, _google_generate_content_response, _openrouter_response],
)
def test_completed_provider_text_replays_without_an_api_call(response) -> None:
    assert extract_completed_provider_response_text_v1(response()) == (
        '{"status":"NO_RELEVANT_FINANCIAL_CONTENT","sections":[]}'
    )


def _openrouter_zero_usage_error() -> bytes:
    return json.dumps(
        {
            "id": "openrouter-response-id",
            "model": "google/gemini-3.7-flash",
            "provider": "Google",
            "choices": [
                {
                    "finish_reason": "error",
                    "message": {"content": '{"status":"INCOMPLETE"'},
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost": 0,
            },
        }
    ).encode()


def _openrouter_error_envelope() -> bytes:
    return b'{"error":{"message":"Provider returned error","code":429}}'


def test_google_standard_result_replays_without_a_provider_call() -> None:
    attempts = (
        {
            "attempt_ordinal": 1,
            "credential_slot": "GOOGLE_SLOT_2",
            "elapsed_seconds": "1.000",
            "http_status": 200,
            "outcome": "COMPLETED",
            "provider": "GOOGLE_GEMINI_API",
            "usage": {},
        },
    )
    result = replay_google_standard_provider_result_v1(
        _google_generate_content_response(),
        attempts=attempts,
    )
    assert result.provider_name == "GOOGLE_GEMINI_API"
    assert result.service_tier == provider.GOOGLE_STANDARD_SERVICE_TIER
    assert result.output_text == '{"status":"NO_RELEVANT_FINANCIAL_CONTENT","sections":[]}'
    assert result.usage["input_tokens"] == 5000
    assert result.attempts == attempts

    bad = ({**attempts[0], "provider": "OPENROUTER"},)
    with pytest.raises(GeminiJsonFirstProviderV1Error, match="attempts are invalid"):
        replay_google_standard_provider_result_v1(
            _google_generate_content_response(),
            attempts=bad,
        )


def test_google_keys_require_protected_file_and_preserve_file_order(tmp_path) -> None:
    path = tmp_path / "keys"
    path.write_text('GEMINI_API_KEY="' + "a" * 30 + '"\nGEMINI_API_KEY=' + "b" * 30 + "\n")
    path.chmod(0o600)
    assert load_google_api_key_slots_v1(path) == ["a" * 30, "b" * 30]
    path.chmod(0o644)
    with pytest.raises(GeminiJsonFirstProviderV1Error, match="0600"):
        load_google_api_key_slots_v1(path)


def test_google_slot_one_success_uses_flex_and_records_estimated_tokens() -> None:
    seen = []

    def transport(url, headers, body, timeout):
        seen.append((url, headers, body, timeout))
        return _google_response()

    result = call_gemini_json_first_v1(
        google_api_keys=["a" * 30, "b" * 30],
        openrouter_api_key="c" * 30,
        image=b"png",
        media_type="image/png",
        prompt="prompt",
        response_schema={"type": "object"},
        execution_policy="GOOGLE_DIRECT_DIAGNOSTIC",
        transport=transport,
        sleep=lambda _: None,
    )
    assert len(seen) == 1
    assert seen[0][2]["service_tier"] == "flex"
    assert seen[0][2]["store"] is False
    assert seen[0][2]["generation_config"] == {"thinking_level": "low"}
    assert seen[0][1]["x-goog-api-key"] == "a" * 30
    assert result.attempts[0]["credential_slot"] == "GOOGLE_SLOT_1"
    assert result.usage["input_tokens"] == 5000
    assert result.usage["output_tokens"] == 1000
    assert result.usage["thought_tokens"] == 100
    assert result.usage["estimated_cost_usd"] == "0.003937500000"
    assert result.response_id_sha256


def test_google_standard_is_explicit_omits_flex_tier_and_uses_standard_price() -> None:
    seen = []

    def transport(url, headers, body, timeout):
        seen.append((url, headers, body, timeout))
        return _google_generate_content_response()

    result = call_gemini_json_first_v1(
        google_api_keys=["a" * 30, "b" * 30],
        openrouter_api_key=None,
        image=b"png",
        media_type="image/png",
        prompt="prompt",
        response_schema={"type": "object"},
        execution_policy="GOOGLE_DIRECT_STANDARD",
        transport=transport,
        sleep=lambda _: None,
    )
    assert len(seen) == 1
    assert seen[0][0].endswith("/models/gemini-3.7-flash:generateContent")
    assert "service_tier" not in seen[0][2]
    assert "Api-Revision" not in seen[0][1]
    assert seen[0][2]["generationConfig"]["maxOutputTokens"] == 65536
    assert seen[0][2]["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "LOW"}
    assert seen[0][1]["x-goog-api-key"] == "a" * 30
    assert result.service_tier == "standard"
    assert result.usage["estimated_cost_usd"] == "0.007875000000"
    assert result.usage["pricing"]["service_tier"] == "standard"


def test_google_transport_timeout_records_attempts_and_advances_key_slots() -> None:
    calls = []

    def transport(url, headers, body, timeout):
        calls.append(headers["x-goog-api-key"])
        if len(calls) == 1:
            raise provider._ProviderConnectionError("timed out")
        return _google_generate_content_response()

    result = call_gemini_json_first_v1(
        google_api_keys=["a" * 30, "b" * 30],
        google_credential_slots=["GOOGLE_SLOT_2", "GOOGLE_SLOT_7"],
        openrouter_api_key=None,
        image=b"png",
        media_type="image/png",
        prompt="prompt",
        response_schema={"type": "object"},
        execution_policy="GOOGLE_DIRECT_STANDARD",
        flex_retries_per_slot=1,
        retry_delay_seconds=0,
        transport=transport,
        sleep=lambda _: None,
    )
    assert calls == ["a" * 30, "b" * 30]
    assert [attempt["outcome"] for attempt in result.attempts] == [
        "TRANSPORT_TIMEOUT_OR_CONNECTION_ERROR",
        "COMPLETED",
    ]
    assert result.attempts[-1]["credential_slot"] == "GOOGLE_SLOT_7"


def test_openrouter_pilot_skips_google_and_pins_google_vertex_flex() -> None:
    calls = []

    def transport(url, headers, body, timeout):
        calls.append((url, headers, body))
        return _openrouter_response()

    result = call_gemini_json_first_v1(
        google_api_keys=None,
        openrouter_api_key="c" * 30,
        image=b"png",
        media_type="image/png",
        prompt="prompt",
        response_schema={"type": "object"},
        transport=transport,
        sleep=lambda _: None,
    )
    assert [attempt["credential_slot"] for attempt in result.attempts] == ["OPENROUTER_SLOT_1"]
    assert result.usage["billing_disposition"] == "BILLED_ACTUAL"
    assert result.usage["actual_cost_usd"] == "0.003750000000"
    assert calls[-1][2]["provider"] == {
        "allow_fallbacks": False,
        "data_collection": "deny",
        "only": ["google-vertex/global/flex"],
        "order": ["google-vertex/global/flex"],
        "require_parameters": True,
    }
    assert calls[-1][2]["usage"] == {"include": True}
    assert calls[-1][2]["seed"] == 0
    assert calls[-1][2]["max_tokens"] == 65536
    assert calls[-1][2]["reasoning"] == {"effort": "low"}


def test_openrouter_can_fall_back_from_vertex_flex_to_cheapest_standard_route() -> None:
    calls = []

    def transport(url, headers, body, timeout):
        calls.append(body)
        return _openrouter_response(provider_name="Google AI Studio", service_tier="standard")

    result = call_gemini_json_first_v1(
        google_api_keys=None,
        openrouter_api_key="c" * 30,
        image=b"png",
        media_type="image/png",
        prompt="prompt",
        response_schema={"type": "object"},
        openrouter_route_policy="FLEX_THEN_STANDARD",
        transport=transport,
        sleep=lambda _: None,
    )

    assert calls[0]["provider"] == {
        "allow_fallbacks": True,
        "data_collection": "deny",
        "only": ["google-vertex/global/flex", "google-ai-studio"],
        "order": ["google-vertex/global/flex", "google-ai-studio"],
        "require_parameters": True,
    }
    assert result.provider_name == "Google AI Studio"
    assert result.service_tier == "standard"
    replayed = replay_openrouter_provider_result_v1(
        result.raw_response_bytes, attempts=result.attempts
    )
    assert replayed.provider_name == "Google AI Studio"
    assert replayed.service_tier == "standard"


def test_flex_only_rejects_an_unrequested_standard_route() -> None:
    with pytest.raises(GeminiJsonFirstProviderV1Error, match="outside the requested policy"):
        call_gemini_json_first_v1(
            google_api_keys=None,
            openrouter_api_key="c" * 30,
            image=b"png",
            media_type="image/png",
            prompt="prompt",
            response_schema={"type": "object"},
            transport=lambda *_args: _openrouter_response(
                provider_name="Google AI Studio", service_tier="standard"
            ),
            sleep=lambda _: None,
        )


@pytest.mark.parametrize("thinking_level", ["medium", "high"])
def test_openrouter_pilot_forwards_explicit_thinking_escalation(thinking_level: str) -> None:
    calls = []

    def transport(url, headers, body, timeout):
        calls.append(body)
        return _openrouter_response()

    call_gemini_json_first_v1(
        google_api_keys=None,
        openrouter_api_key="c" * 30,
        image=b"png",
        media_type="image/png",
        prompt="prompt",
        response_schema={"type": "object"},
        thinking_level=thinking_level,
        transport=transport,
        sleep=lambda _: None,
    )
    assert len(calls) == 1
    assert calls[0]["reasoning"] == {"effort": thinking_level}


def test_google_diagnostic_nonquota_error_never_triggers_openrouter() -> None:
    calls = []

    def transport(url, headers, body, timeout):
        calls.append(url)
        raise provider._ProviderHttpError(status=401, provider="GOOGLE")

    with pytest.raises(GeminiJsonFirstProviderV1Error, match="no fallback"):
        call_gemini_json_first_v1(
            google_api_keys=["a" * 30, "b" * 30],
            openrouter_api_key="c" * 30,
            image=b"png",
            media_type="image/png",
            prompt="prompt",
            response_schema={"type": "object"},
            execution_policy="GOOGLE_DIRECT_DIAGNOSTIC",
            transport=transport,
            sleep=lambda _: None,
        )
    assert len(calls) == 2


def test_google_500_retries_each_google_slot_then_stops_without_paid_fallback() -> None:
    calls = []

    def transport(url, headers, body, timeout):
        calls.append((url, headers.get("x-goog-api-key")))
        raise provider._ProviderHttpError(status=500, provider="GOOGLE")

    with pytest.raises(GeminiJsonFirstProviderV1Error, match="no fallback") as caught:
        call_gemini_json_first_v1(
            google_api_keys=["a" * 30, "b" * 30],
            openrouter_api_key="c" * 30,
            image=b"png",
            media_type="image/png",
            prompt="prompt",
            response_schema={"type": "object"},
            execution_policy="GOOGLE_DIRECT_DIAGNOSTIC",
            flex_retries_per_slot=2,
            retry_delay_seconds=0,
            transport=transport,
            sleep=lambda _: None,
        )
    assert calls == [
        ("https://generativelanguage.googleapis.com/v1beta/interactions", "a" * 30),
        ("https://generativelanguage.googleapis.com/v1beta/interactions", "a" * 30),
        ("https://generativelanguage.googleapis.com/v1beta/interactions", "b" * 30),
        ("https://generativelanguage.googleapis.com/v1beta/interactions", "b" * 30),
    ]
    assert [attempt["outcome"] for attempt in caught.value.attempts] == [
        "TRANSIENT_PROVIDER_ERROR",
        "TRANSIENT_PROVIDER_ERROR",
        "TRANSIENT_PROVIDER_ERROR",
        "TRANSIENT_PROVIDER_ERROR",
    ]


def test_second_google_slot_can_succeed_after_first_slot_transient_failure() -> None:
    calls = []

    def transport(url, headers, body, timeout):
        calls.append(headers.get("x-goog-api-key"))
        if headers.get("x-goog-api-key") == "a" * 30:
            raise provider._ProviderHttpError(status=500, provider="GOOGLE")
        return _google_response()

    result = call_gemini_json_first_v1(
        google_api_keys=["a" * 30, "b" * 30],
        openrouter_api_key="c" * 30,
        image=b"png",
        media_type="image/png",
        prompt="prompt",
        response_schema={"type": "object"},
        execution_policy="GOOGLE_DIRECT_DIAGNOSTIC",
        flex_retries_per_slot=1,
        retry_delay_seconds=0,
        transport=transport,
        sleep=lambda _: None,
    )
    assert calls == ["a" * 30, "b" * 30]
    assert result.attempts[-1]["credential_slot"] == "GOOGLE_SLOT_2"
    assert result.provider_name == "GOOGLE_GEMINI_API"


def test_invalid_google_success_response_never_routes_around_validation() -> None:
    calls = []

    def transport(url, headers, body, timeout):
        calls.append(url)
        return b'{"status":"completed","steps":[]}'

    with pytest.raises(GeminiJsonFirstProviderV1Error, match="model identity"):
        call_gemini_json_first_v1(
            google_api_keys=["a" * 30, "b" * 30],
            openrouter_api_key="c" * 30,
            image=b"png",
            media_type="image/png",
            prompt="prompt",
            response_schema={"type": "object"},
            execution_policy="GOOGLE_DIRECT_DIAGNOSTIC",
            transport=transport,
            sleep=lambda _: None,
        )
    assert len(calls) == 1


def test_prompt_json_mode_omits_provider_schema_but_retains_local_contract() -> None:
    seen = []

    def transport(url, headers, body, timeout):
        seen.append(body)
        return _openrouter_response()

    result = call_gemini_json_first_v1(
        google_api_keys=None,
        openrouter_api_key="c" * 30,
        image=b"png",
        media_type="image/png",
        prompt="prompt with exact JSON contract",
        response_schema={"type": "object"},
        output_contract_mode="PROMPT_JSON",
        transport=transport,
        sleep=lambda _: None,
    )
    assert "response_format" not in seen[0]
    assert result.provider_name == "Google"


def test_openrouter_pilot_rejects_direct_google_credentials() -> None:
    with pytest.raises(GeminiJsonFirstProviderV1Error, match="must not receive"):
        call_gemini_json_first_v1(
            google_api_keys=["a" * 30],
            openrouter_api_key="c" * 30,
            image=b"png",
            media_type="image/png",
            prompt="prompt",
            response_schema={"type": "object"},
        )


def test_openrouter_retries_only_unbilled_zero_usage_error_and_checkpoints_attempts() -> None:
    calls = 0
    checkpoints = []

    def transport(url, headers, body, timeout):
        nonlocal calls
        calls += 1
        return _openrouter_zero_usage_error() if calls == 1 else _openrouter_response()

    result = call_gemini_json_first_v1(
        google_api_keys=None,
        openrouter_api_key="c" * 30,
        image=b"png",
        media_type="image/png",
        prompt="prompt",
        response_schema={"type": "object"},
        openrouter_retries=2,
        retry_delay_seconds=0,
        transport=transport,
        sleep=lambda _: None,
        on_attempt=checkpoints.append,
    )
    assert [attempt["outcome"] for attempt in result.attempts] == [
        "ZERO_USAGE_PROVIDER_ERROR",
        "COMPLETED",
    ]
    assert checkpoints == list(result.attempts)


def test_openrouter_retries_http_200_error_envelope_without_switching_provider() -> None:
    calls = 0

    def transport(url, headers, body, timeout):
        nonlocal calls
        calls += 1
        return _openrouter_error_envelope() if calls == 1 else _openrouter_response()

    result = call_gemini_json_first_v1(
        google_api_keys=None,
        openrouter_api_key="c" * 30,
        image=b"png",
        media_type="image/png",
        prompt="prompt",
        response_schema={"type": "object"},
        openrouter_retries=2,
        retry_delay_seconds=0,
        transport=transport,
        sleep=lambda _: None,
    )
    assert [attempt["outcome"] for attempt in result.attempts] == [
        "TRANSIENT_HTTP_ERROR",
        "COMPLETED",
    ]
