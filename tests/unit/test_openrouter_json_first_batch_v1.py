from __future__ import annotations

import json

import pytest

from bctc_ai.evaluation.gemini_json_first_batch_v1 import InlinePageRequestV1
from bctc_ai.evaluation.openrouter_json_first_batch_v1 import (
    OpenRouterJsonFirstBatchV1Error,
    build_openrouter_batch_body_v1,
    decode_completed_openrouter_batch_v1,
    poll_openrouter_batch_v1,
    submit_openrouter_batch_v1,
    summarize_openrouter_batch_v1,
)


def _request(request_id: str = "page-003") -> InlinePageRequestV1:
    return InlinePageRequestV1(
        request_id=request_id,
        image=b"png-image",
        media_type="image/png",
        prompt="Extract exact JSON",
        response_schema={"type": "object"},
    )


def _batch(*, status: str = "completed") -> dict[str, object]:
    done = status == "completed"
    value: dict[str, object] = {
        "completion_window": "24h",
        "endpoint": "/v1/chat/completions",
        "error": None,
        "id": "batch-1",
        "model": "google/gemini-3.7-flash-20260813",
        "object": "batch",
        "request_counts": {
            "completed": 1 if done else 0,
            "failed": 0,
            "total": 1,
        },
        "status": status,
    }
    if done:
        value["results"] = [
            {
                "custom_id": "page-003",
                "error": None,
                "id": "request-1",
                "response": {
                    "body": {
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {
                                    "content": '{"status":"NO_RELEVANT_FINANCIAL_CONTENT"}',
                                },
                            }
                        ],
                        "id": "generation-1",
                        "model": "google/gemini-3.7-flash",
                        "provider": "Google",
                        "usage": {
                            "completion_tokens": 5,
                            "completion_tokens_details": {"reasoning_tokens": 0},
                            "prompt_tokens": 56,
                            "total_tokens": 61,
                        },
                    },
                    "request_id": "request-1",
                    "status_code": 200,
                },
            }
        ]
        value["usage"] = {
            "completion_tokens": 5,
            "cost": 0.0000151875,
            "prompt_tokens": 56,
            "total_tokens": 61,
        }
    else:
        value["results"] = None
        value["usage"] = None
    return value


def test_openrouter_batch_body_pins_model_provider_and_full_image_schema() -> None:
    body = build_openrouter_batch_body_v1(requests=[_request()])
    assert body["endpoint"] == "/v1/chat/completions"
    assert body["model"] == "google/gemini-3.7-flash"
    request = body["requests"][0]
    assert request["custom_id"] == "page-003"
    assert request["body"]["provider"] == {
        "allow_fallbacks": False,
        "data_collection": "deny",
        "only": ["google-vertex"],
        "require_parameters": True,
    }
    assert request["body"]["max_tokens"] == 65536
    assert request["body"]["messages"][0]["content"][1]["image_url"]["url"].startswith(
        "data:image/png;base64,"
    )
    assert request["body"]["response_format"]["json_schema"]["strict"] is True

    url_request = InlinePageRequestV1(
        request_id="page-004",
        file_uri="https://media.example/immutable/page.png?signature=secret",
        media_type="image/png",
        prompt="Extract exact JSON",
        response_schema={"type": "object"},
    )
    url_body = build_openrouter_batch_body_v1(requests=[url_request])
    assert (
        url_body["requests"][0]["body"]["messages"][0]["content"][1]["image_url"]["url"]
        == url_request.file_uri
    )


def test_submit_poll_and_summary_preserve_openrouter_batch_identity() -> None:
    def post(url, headers, body, timeout):
        assert url.endswith("/api/beta/batches")
        assert headers["Authorization"] == "Bearer " + "a" * 30
        return json.dumps(_batch(status="validating")).encode()

    submission = submit_openrouter_batch_v1(api_key="a" * 30, requests=[_request()], transport=post)
    assert submission.batch_name == "batch-1"
    assert submission.state == "BATCH_STATE_PENDING"

    def get(url, headers, timeout):
        assert url.endswith("/api/beta/batches/batch-1")
        return json.dumps(_batch()).encode()

    raw = poll_openrouter_batch_v1(api_key="a" * 30, batch_name="batch-1", transport=get)
    assert summarize_openrouter_batch_v1(raw) == {
        "batch_name": "batch-1",
        "done": True,
        "failed_request_count": 0,
        "pending_request_count": 0,
        "request_count": 1,
        "state": "BATCH_STATE_SUCCEEDED",
        "successful_request_count": 1,
    }


def test_completed_openrouter_batch_binds_result_and_actual_allocated_cost() -> None:
    completed = decode_completed_openrouter_batch_v1(
        raw=json.dumps(_batch()).encode(),
        expected_request_ids=["page-003"],
        elapsed_seconds="390.000",
    )
    result = completed.provider_results["page-003"]
    assert completed.failures == {}
    assert result.provider_name == "OPENROUTER_BATCH"
    assert result.service_tier == "batch"
    assert result.usage["input_tokens"] == 56
    assert result.usage["output_tokens"] == 5
    assert result.usage["actual_cost_usd"] == "0.000015187500"
    assert result.usage["billing_disposition"] == "BILLED_ACTUAL_ALLOCATED_BATCH"


def test_openrouter_batch_rejects_cost_or_request_set_tamper() -> None:
    forged = _batch()
    forged["usage"]["cost"] = 1
    with pytest.raises(OpenRouterJsonFirstBatchV1Error, match="cost does not close"):
        decode_completed_openrouter_batch_v1(
            raw=json.dumps(forged).encode(),
            expected_request_ids=["page-003"],
            elapsed_seconds="1.000",
        )
    with pytest.raises(OpenRouterJsonFirstBatchV1Error, match="set drifted"):
        decode_completed_openrouter_batch_v1(
            raw=json.dumps(_batch()).encode(),
            expected_request_ids=["page-999"],
            elapsed_seconds="1.000",
        )
