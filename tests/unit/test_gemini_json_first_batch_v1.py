from __future__ import annotations

import base64
import copy
import json
from hashlib import sha256

import pytest

from bctc_ai.evaluation.gemini_json_first_batch_v1 import (
    GOOGLE_BATCH_ENDPOINT,
    BatchSubmissionV1,
    GeminiJsonFirstBatchV1Error,
    InlinePageRequestV1,
    build_google_file_batch_body_v1,
    build_google_inline_batch_body_v1,
    decode_completed_google_file_batch_v1,
    decode_completed_google_inline_batch_v1,
    download_google_file_v1,
    google_batch_responses_file_v1,
    poll_google_batch_v1,
    submit_google_file_batch_v1,
    submit_google_inline_batch_v1,
    upload_google_file_v1,
)


def _request(request_id: str = "page-003") -> InlinePageRequestV1:
    return InlinePageRequestV1(
        request_id=request_id,
        image=b"png-image",
        media_type="image/png",
        prompt="Extract exact JSON",
        response_schema={"type": "object"},
    )


def _response() -> dict[str, object]:
    return {
        "responseId": "response-1",
        "modelVersion": "gemini-3.7-flash",
        "candidates": [
            {
                "finishReason": "STOP",
                "content": {
                    "parts": [
                        {
                            "text": '{"status":"NO_RELEVANT_FINANCIAL_CONTENT",'
                            '"sections":[],"completion":'
                            '{"all_relevant_content_transcribed":true,'
                            '"uncertainty_exact":[]}}'
                        }
                    ]
                },
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 1754,
            "candidatesTokenCount": 200,
            "thoughtsTokenCount": 20,
            "totalTokenCount": 1974,
        },
    }


def _running_operation() -> dict[str, object]:
    return {
        "name": "batches/batch-1",
        "metadata": {
            "name": "batches/batch-1",
            "state": "BATCH_STATE_RUNNING",
            "model": "models/gemini-3.7-flash",
        },
    }


def _completed_operation() -> dict[str, object]:
    return {
        "done": True,
        "name": "batches/batch-1",
        "response": {
            "name": "batches/batch-1",
            "state": "BATCH_STATE_SUCCEEDED",
            "model": "models/gemini-3.7-flash",
            "output": {
                "inlinedResponses": {
                    "inlinedResponses": [
                        {"metadata": {"request_id": "page-003"}, "response": _response()}
                    ]
                }
            },
        },
    }


def _completed_file_operation() -> dict[str, object]:
    return {
        "done": True,
        "name": "batches/batch-file-1",
        "response": {
            "name": "batches/batch-file-1",
            "state": "BATCH_STATE_SUCCEEDED",
            "model": "models/gemini-3.7-flash",
            "responsesFile": "files/result-file-1",
        },
    }


def test_inline_batch_body_binds_request_ids_and_generate_content_contract() -> None:
    body = build_google_inline_batch_body_v1(
        display_name="one-pdf-pilot", requests=[_request(), _request("page-004")]
    )
    batch = body["batch"]
    assert batch["model"] == "models/gemini-3.7-flash"
    requests = batch["inputConfig"]["requests"]["requests"]
    assert [item["metadata"]["request_id"] for item in requests] == [
        "page-003",
        "page-004",
    ]
    assert requests[0]["request"]["store"] is False
    assert requests[0]["request"]["generationConfig"]["maxOutputTokens"] == 65536
    assert requests[0]["request"]["model"] == "models/gemini-3.7-flash"
    assert "responseJsonSchema" in requests[0]["request"]["generationConfig"]

    with pytest.raises(GeminiJsonFirstBatchV1Error, match="unique"):
        build_google_inline_batch_body_v1(
            display_name="duplicate", requests=[_request(), _request()]
        )


def test_uploaded_file_is_byte_authenticated_and_referenced_without_inline_data() -> None:
    payload = b"png-image"
    calls = []

    def start(url, headers, body, timeout):
        calls.append(("start", url, headers, body))
        return b"", {"x-goog-upload-url": "https://upload.example/session"}

    def finalize(url, headers, body, timeout):
        calls.append(("finalize", url, headers, body))
        return json.dumps(
            {
                "file": {
                    "expirationTime": "2026-08-28T00:00:00Z",
                    "mimeType": "image/png",
                    "name": "files/file-1",
                    "sha256Hash": base64.b64encode(
                        sha256(payload).hexdigest().encode("ascii")
                    ).decode(),
                    "sizeBytes": str(len(payload)),
                    "state": "ACTIVE",
                    "uri": "https://generativelanguage.googleapis.com/v1beta/files/file-1",
                }
            }
        ).encode()

    uploaded = upload_google_file_v1(
        api_key="a" * 30,
        payload=payload,
        media_type="image/png",
        display_name="page-003.png",
        start_transport=start,
        finalize_transport=finalize,
    )
    assert uploaded.name == "files/file-1"
    assert calls[1][3] == payload
    request = _request()
    file_request = type(request)(
        request_id=request.request_id,
        media_type=request.media_type,
        prompt=request.prompt,
        response_schema=request.response_schema,
        file_uri=uploaded.uri,
    )
    body = build_google_inline_batch_body_v1(display_name="file-backed", requests=[file_request])
    media_part = body["batch"]["inputConfig"]["requests"]["requests"][0]["request"]["contents"][0][
        "parts"
    ][0]
    assert media_part == {"fileData": {"fileUri": uploaded.uri, "mimeType": "image/png"}}


def test_file_backed_batch_submission_download_and_jsonl_decode() -> None:
    assert build_google_file_batch_body_v1(
        display_name="multimodal-jsonl", input_file_name="files/input-1"
    ) == {
        "batch": {
            "displayName": "multimodal-jsonl",
            "inputConfig": {"fileName": "files/input-1"},
            "model": "models/gemini-3.7-flash",
        }
    }
    calls = []

    def post(url, headers, body, timeout):
        calls.append(body)
        return json.dumps(
            {
                "name": "batches/batch-file-1",
                "metadata": {
                    "name": "batches/batch-file-1",
                    "state": "BATCH_STATE_RUNNING",
                },
            }
        ).encode()

    submission = submit_google_file_batch_v1(
        api_key="a" * 30,
        credential_slot="GOOGLE_SLOT_2",
        display_name="multimodal-jsonl",
        input_file_name="files/input-1",
        transport=post,
    )
    assert submission.batch_name == "batches/batch-file-1"
    assert calls[0]["batch"]["inputConfig"] == {"fileName": "files/input-1"}
    operation_raw = json.dumps(_completed_file_operation()).encode()
    assert google_batch_responses_file_v1(operation_raw) == "files/result-file-1"

    def download(url, headers, timeout):
        assert url.endswith("/files/result-file-1:download?alt=media")
        return b"jsonl-result\n"

    assert (
        download_google_file_v1(
            api_key="a" * 30, file_name="files/result-file-1", transport=download
        )
        == b"jsonl-result\n"
    )
    results_raw = json.dumps({"key": "page-003", "response": _response()}).encode() + b"\n"
    completed = decode_completed_google_file_batch_v1(
        raw_operation_bytes=operation_raw,
        raw_results_bytes=results_raw,
        expected_request_ids=["page-003"],
        credential_slot="GOOGLE_SLOT_2",
        elapsed_seconds="42.500",
    )
    assert completed.failures == {}
    assert completed.provider_results["page-003"].usage["input_tokens"] == 1754


def test_submit_and_poll_preserve_exact_batch_identity() -> None:
    calls = []

    def post(url, headers, body, timeout):
        calls.append((url, headers, body, timeout))
        return json.dumps(_running_operation()).encode()

    submission = submit_google_inline_batch_v1(
        api_key="a" * 30,
        credential_slot="GOOGLE_SLOT_2",
        display_name="pilot",
        requests=[_request()],
        transport=post,
    )
    assert isinstance(submission, BatchSubmissionV1)
    assert submission.batch_name == "batches/batch-1"
    assert submission.state == "BATCH_STATE_RUNNING"
    assert calls[0][0] == GOOGLE_BATCH_ENDPOINT
    assert calls[0][1]["x-goog-api-key"] == "a" * 30

    def get(url, headers, timeout):
        assert url.endswith("/v1beta/batches/batch-1")
        return json.dumps(_completed_operation()).encode()

    raw = poll_google_batch_v1(api_key="a" * 30, batch_name="batches/batch-1", transport=get)
    assert json.loads(raw)["done"] is True


def test_completed_batch_decodes_per_page_usage_at_batch_price() -> None:
    raw = json.dumps(_completed_operation()).encode()
    completed = decode_completed_google_inline_batch_v1(
        raw_operation_bytes=raw,
        expected_request_ids=["page-003"],
        credential_slot="GOOGLE_SLOT_2",
        elapsed_seconds="42.500",
    )
    assert completed.state == "BATCH_STATE_SUCCEEDED"
    assert completed.failures == {}
    result = completed.provider_results["page-003"]
    assert result.provider_name == "GOOGLE_GEMINI_BATCH_API"
    assert result.service_tier == "batch"
    assert result.usage["input_tokens"] == 1754
    assert result.usage["output_tokens"] == 200
    assert result.usage["thought_tokens"] == 20
    assert result.usage["estimated_cost_usd"] == "0.001070250000"
    assert result.attempts[0]["credential_slot"] == "GOOGLE_SLOT_2"


def test_completed_batch_rejects_request_set_drift_and_preserves_failures() -> None:
    operation = _completed_operation()
    entry = operation["response"]["output"]["inlinedResponses"]["inlinedResponses"][0]
    entry.pop("response")
    entry["error"] = {"code": 503, "message": "capacity"}
    completed = decode_completed_google_inline_batch_v1(
        raw_operation_bytes=json.dumps(operation).encode(),
        expected_request_ids=["page-003"],
        credential_slot="GOOGLE_SLOT_1",
        elapsed_seconds="100.000",
    )
    assert completed.provider_results == {}
    assert completed.failures == {"page-003": {"code": 503, "message": "capacity"}}

    forged = copy.deepcopy(_completed_operation())
    forged["response"]["output"]["inlinedResponses"]["inlinedResponses"][0]["metadata"][
        "request_id"
    ] = "page-999"
    with pytest.raises(GeminiJsonFirstBatchV1Error, match="set drifted"):
        decode_completed_google_inline_batch_v1(
            raw_operation_bytes=json.dumps(forged).encode(),
            expected_request_ids=["page-003"],
            credential_slot="GOOGLE_SLOT_1",
            elapsed_seconds="1.000",
        )
