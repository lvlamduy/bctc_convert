from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_gemini_financial_page_json_v1 import _page

from bctc_ai.evaluation.gemini_json_first_batch_v1 import BatchSubmissionV1
from bctc_ai.evaluation.gemini_json_first_provider_v1 import ProviderResultV1
from bctc_ai.storage.gemini_financial_page_store_v1 import (
    GeminiFinancialPageStoreV1Error,
    batch_failed_page_requests_v1,
    batch_progress_v1,
    ingest_financial_page_extraction_v1,
    initialize_gemini_financial_page_store_v1,
    record_batch_poll_v1,
    record_batch_request_result_v1,
    register_batch_submission_v1,
)

DOCUMENT = {
    "source_logical_name": "report.pdf",
    "source_sha256": "b" * 64,
    "source_size_bytes": 123,
}
PAGE = {
    "physical_page": 7,
    "image_sha256": "c" * 64,
    "image_size_bytes": 456,
    "pixel_width": 2481,
    "pixel_height": 3508,
    "render_dpi": 300,
    "media_type": "image/png",
}


def _operation(*, state: str, done: bool) -> bytes:
    successful = "1" if done else "0"
    pending = "0" if done else "1"
    value: dict[str, object] = {
        "name": "batches/batch-1",
        "metadata": {
            "name": "batches/batch-1",
            "state": state,
            "batchStats": {
                "requestCount": "1",
                "successfulRequestCount": successful,
                "pendingRequestCount": pending,
            },
        },
    }
    if done:
        value["done"] = True
        value["response"] = {"inlinedResponses": {"inlinedResponses": []}}
    return json.dumps(value, sort_keys=True).encode()


def _batch_result() -> ProviderResultV1:
    usage = {
        "billing_disposition": "ESTIMATED_LIST_PRICE",
        "cached_input_tokens": 0,
        "estimated_cost_usd": "0.001000000000",
        "input_tokens": 1000,
        "output_tokens": 300,
        "thought_tokens": 20,
        "total_tokens": 1320,
    }
    return ProviderResultV1(
        output_text=json.dumps(_page(), ensure_ascii=False),
        raw_response_bytes=b'{"batch":"response"}',
        provider_name="GOOGLE_GEMINI_BATCH_API",
        provider_model="gemini-3.7-flash",
        service_tier="batch",
        attempts=(
            {
                "attempt_ordinal": 1,
                "credential_slot": "GOOGLE_SLOT_2",
                "elapsed_seconds": "180.000",
                "http_status": 200,
                "outcome": "COMPLETED_BATCH",
                "provider": "GOOGLE_GEMINI_BATCH_API",
                "usage": usage,
            },
        ),
        usage=usage,
        response_id_sha256="f" * 64,
    )


def _register(path: Path) -> str:
    raw = _operation(state="BATCH_STATE_RUNNING", done=False)
    submission = BatchSubmissionV1(
        batch_name="batches/batch-1",
        state="BATCH_STATE_RUNNING",
        raw_response_bytes=raw,
        elapsed_seconds="4.200",
        credential_slot="GOOGLE_SLOT_2",
    )
    return register_batch_submission_v1(
        path,
        submission=submission,
        display_name="pdf-pilot",
        requests=[{"request_id": "page-007", "document": DOCUMENT, "page": PAGE}],
        prompt_variant="balanced",
        output_contract_mode="JSON_SCHEMA",
        prompt_sha256="d" * 64,
        response_schema_sha256="e" * 64,
        requested_model="gemini-3.7-flash",
        thinking_level="low",
    )


def test_batch_progress_tracks_submitted_running_succeeded_and_ingested(tmp_path) -> None:
    path = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(path)
    batch_job_id = _register(path)
    progress = batch_progress_v1(path)
    assert progress == [
        {
            "batch_job_id": batch_job_id,
            "batch_name": "batches/batch-1",
            "credential_slot": "GOOGLE_SLOT_2",
            "documents": [
                {
                    "document_id": progress[0]["documents"][0]["document_id"],
                    "source_logical_name": "report.pdf",
                    "requested_pages": 1,
                    "ingested_pages": 0,
                    "failed_pages": 0,
                }
            ],
            "failed_pages": 0,
            "ingested_pages": 0,
            "provider": "GOOGLE_GEMINI_BATCH_API",
            "request_count": 1,
            "state": "BATCH_STATE_RUNNING",
            "unfinalized_pages": 1,
        }
    ]
    summary = record_batch_poll_v1(
        path,
        raw_operation_bytes=_operation(state="BATCH_STATE_SUCCEEDED", done=True),
    )
    assert summary["successful_request_count"] == 1
    assert batch_progress_v1(path)[0]["state"] == "BATCH_STATE_SUCCEEDED"

    ids = ingest_financial_page_extraction_v1(
        path,
        document=DOCUMENT,
        page=PAGE,
        prompt_variant="balanced",
        output_contract_mode="JSON_SCHEMA",
        prompt_sha256="d" * 64,
        response_schema_sha256="e" * 64,
        requested_model="gemini-3.7-flash",
        requested_service_tier="batch",
        thinking_level="low",
        provider_result=_batch_result(),
        page_json=_page(),
    )
    record_batch_request_result_v1(
        path,
        batch_name="batches/batch-1",
        request_id="page-007",
        disposition="INGESTED",
        extraction_run_id=ids["extraction_run_id"],
    )
    final = batch_progress_v1(path)[0]
    assert final["ingested_pages"] == 1
    assert final["unfinalized_pages"] == 0
    assert final["documents"][0]["ingested_pages"] == 1
    with pytest.raises(GeminiFinancialPageStoreV1Error, match="already"):
        record_batch_request_result_v1(
            path,
            batch_name="batches/batch-1",
            request_id="page-007",
            disposition="FAILED",
            error={"code": 500},
        )


def test_batch_result_cannot_bind_a_different_page_or_cache(tmp_path) -> None:
    path = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(path)
    _register(path)
    with pytest.raises(GeminiFinancialPageStoreV1Error, match="does not bind"):
        record_batch_request_result_v1(
            path,
            batch_name="batches/batch-1",
            request_id="page-007",
            disposition="INGESTED",
            extraction_run_id="gfpstorev1:run:" + "0" * 64,
        )


def test_failed_batch_page_retains_typed_provider_error_for_fallback(tmp_path) -> None:
    path = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(path)
    _register(path)
    error = {"provider_error": {"finish_reason": "RECITATION"}}
    record_batch_request_result_v1(
        path,
        batch_name="batches/batch-1",
        request_id="page-007",
        disposition="FAILED",
        error=error,
    )
    assert batch_failed_page_requests_v1(path, batch_name="batches/batch-1") == [
        {"error": error, "physical_page": 7, "request_id": "page-007"}
    ]
