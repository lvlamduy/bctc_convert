from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import fitz

from bctc_ai.evaluation.gemini_json_first_provider_v1 import (
    GeminiJsonFirstProviderV1Error,
    ProviderResultV1,
)

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "scripts/experiments/run_gemini_json_first_openrouter_document_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "run_gemini_json_first_openrouter_document_v1", _SCRIPT
)
assert _SPEC is not None and _SPEC.loader is not None
target = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = target
_SPEC.loader.exec_module(target)


def _pdf(path: Path, pages: int) -> None:
    document = fitz.open()
    for ordinal in range(1, pages + 1):
        page = document.new_page()
        page.insert_text((72, 72), f"page {ordinal}")
    document.save(path)
    document.close()


def _result() -> ProviderResultV1:
    page = {
        "status": "NO_RELEVANT_FINANCIAL_CONTENT",
        "sections": [],
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
    }
    raw = json.dumps(
        {
            "id": "response-1",
            "model": "google/gemini-3.7-flash-20260813",
            "provider": "Google",
        }
    ).encode()
    usage = {
        "actual_cost_usd": "0.000100000000",
        "billing_disposition": "BILLED_ACTUAL",
        "cached_input_tokens": 0,
        "input_tokens": 10,
        "output_tokens": 5,
        "thought_tokens": 0,
        "total_tokens": 15,
    }
    return ProviderResultV1(
        output_text=json.dumps(page),
        raw_response_bytes=raw,
        provider_name="Google",
        provider_model="google/gemini-3.7-flash-20260813",
        service_tier="flex",
        attempts=(
            {
                "attempt_ordinal": 1,
                "credential_slot": "OPENROUTER_SLOT_1",
                "elapsed_seconds": "0.010",
                "http_status": 200,
                "outcome": "COMPLETED",
                "provider": "OPENROUTER",
                "usage": usage,
            },
        ),
        usage=usage,
        response_id_sha256="1" * 64,
    )


def test_parallel_document_run_persists_in_parent_and_resumes_from_cache(tmp_path) -> None:
    pdf = tmp_path / "document.pdf"
    database = tmp_path / "store.sqlite3"
    artifacts = tmp_path / "artifacts"
    _pdf(pdf, 3)
    calls = []

    def provider(**kwargs):
        calls.append(kwargs["image"])
        return _result()

    first = target.run_openrouter_document_v1(
        pdf=pdf,
        database=database,
        artifact_dir=artifacts,
        api_key="x" * 32,
        workers=2,
        provider_call=provider,
    )
    assert first["disposition"] == "SUCCEEDED"
    assert first["ingested_pages"] == [1, 2, 3]
    assert first["cached_pages"] == []
    assert first["failed_pages"] == []
    assert len(calls) == 3
    assert (artifacts / "document-manifest.json").is_file()
    manifest = json.loads((artifacts / "document-manifest.json").read_bytes())
    assert manifest["page_count"] == 3
    assert manifest["status_counts"] == {"NO_RELEVANT_FINANCIAL_CONTENT": 3}

    calls.clear()
    replay = target.run_openrouter_document_v1(
        pdf=pdf,
        database=database,
        artifact_dir=artifacts,
        api_key="x" * 32,
        workers=3,
        provider_call=provider,
    )
    assert replay["disposition"] == "SUCCEEDED"
    assert replay["cached_pages"] == [1, 2, 3]
    assert replay["ingested_pages"] == []
    assert calls == []
    assert len(list((artifacts / "run-receipts").glob("*.json"))) == 2


def test_one_failed_page_does_not_abort_siblings_and_only_failure_retries(tmp_path) -> None:
    pdf = tmp_path / "document.pdf"
    database = tmp_path / "store.sqlite3"
    artifacts = tmp_path / "artifacts"
    _pdf(pdf, 3)
    calls = 0

    def first_provider(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            error = GeminiJsonFirstProviderV1Error("typed provider failure")
            error.attempts = (
                {
                    "attempt_ordinal": 1,
                    "credential_slot": "OPENROUTER_SLOT_1",
                    "elapsed_seconds": "0.010",
                    "http_status": 503,
                    "outcome": "TRANSIENT_HTTP_ERROR",
                    "provider": "OPENROUTER",
                    "usage": None,
                },
            )
            raise error
        return _result()

    first = target.run_openrouter_document_v1(
        pdf=pdf,
        database=database,
        artifact_dir=artifacts,
        api_key="x" * 32,
        workers=1,
        provider_call=first_provider,
    )
    assert first["disposition"] == "NEEDS_RETRY"
    assert first["failed_pages"] == [2]
    assert first["ingested_pages"] == [1, 3]
    assert not (artifacts / "document-manifest.json").exists()

    retried = []

    def retry_provider(**kwargs):
        retried.append(kwargs["image"])
        return _result()

    second = target.run_openrouter_document_v1(
        pdf=pdf,
        database=database,
        artifact_dir=artifacts,
        api_key="x" * 32,
        workers=2,
        provider_call=retry_provider,
    )
    assert second["disposition"] == "SUCCEEDED"
    assert second["cached_pages"] == [1, 3]
    assert second["ingested_pages"] == [2]
    assert len(retried) == 1
    assert (artifacts / "document-manifest.json").is_file()
