from __future__ import annotations

import importlib.util
import json
import os
import sys
import threading
from hashlib import sha256
from pathlib import Path

import fitz
import pytest

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


def _google_result() -> ProviderResultV1:
    original = _result()
    attempt = {
        **original.attempts[0],
        "credential_slot": "GOOGLE_SLOT_2",
        "provider": "GOOGLE_GEMINI_API",
    }
    return ProviderResultV1(
        output_text=original.output_text,
        raw_response_bytes=b'{"google":"standard"}',
        provider_name="GOOGLE_GEMINI_API",
        provider_model="gemini-3.7-flash",
        service_tier="standard",
        attempts=(attempt,),
        usage={
            **original.usage,
            "actual_cost_usd": "0.000200000000",
            "billing_disposition": "ESTIMATED_LIST_PRICE",
        },
        response_id_sha256="2" * 64,
    )


def _unresolved_result() -> ProviderResultV1:
    original = _result()
    page = {
        "status": "UNRESOLVED_PAGE",
        "sections": [],
        "completion": {
            "all_relevant_content_transcribed": False,
            "uncertainty_exact": ["The page edge is cut and the table is incomplete."],
        },
    }
    return ProviderResultV1(
        output_text=json.dumps(page),
        raw_response_bytes=b'{"provider":"unresolved"}',
        provider_name=original.provider_name,
        provider_model=original.provider_model,
        service_tier=original.service_tier,
        attempts=original.attempts,
        usage=original.usage,
        response_id_sha256="3" * 64,
    )


def test_write_new_publishes_only_after_the_staged_payload_is_durable(
    monkeypatch, tmp_path
) -> None:
    destination = tmp_path / "receipt.json"
    payload = b'{"ok":true}\n'
    original_link = os.link
    observed = []

    def link(source, target_path):
        source_path = Path(source)
        observed.append((source_path, Path(target_path), source_path.read_bytes()))
        assert source_path != destination
        assert not destination.exists()
        return original_link(source, target_path)

    monkeypatch.setattr(target.os, "link", link)
    target._write_new(destination, payload)

    assert destination.read_bytes() == payload
    assert observed[0][1:] == (destination, payload)
    assert list(tmp_path.glob(".receipt.json.stage-*")) == []


def test_write_new_does_not_replace_an_existing_immutable_artifact(tmp_path) -> None:
    destination = tmp_path / "receipt.json"
    destination.write_bytes(b"existing")

    with pytest.raises(FileExistsError):
        target._write_new(destination, b"replacement")

    assert destination.read_bytes() == b"existing"
    assert list(tmp_path.glob(".receipt.json.stage-*")) == []


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
    assert [item["physical_page"] for item in first["page_image_sha256s"]] == [1, 2, 3]
    assert all(len(item["image_sha256"]) == 64 for item in first["page_image_sha256s"])
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


def test_parallel_document_persists_each_completed_future_before_slowest_finishes(
    monkeypatch, tmp_path
) -> None:
    pdf = tmp_path / "document.pdf"
    database = tmp_path / "store.sqlite3"
    artifacts = tmp_path / "artifacts"
    _pdf(pdf, 2)
    second_persisted = threading.Event()
    persistence_order = []

    def extract(**kwargs):
        page = kwargs["physical_page"]
        if page == 1:
            assert second_persisted.wait(timeout=1)
        return target._PageOutcome(
            physical_page=page,
            page={
                "image_sha256": str(page) * 64,
                "image_size_bytes": 1,
                "media_type": "image/png",
                "physical_page": page,
                "pixel_height": 1,
                "pixel_width": 1,
                "render_dpi": 300,
            },
            cached_json={"status": "NO_RELEVANT_FINANCIAL_CONTENT"},
        )

    original_persist = target._persist_page_outcome_v1

    def persist(**kwargs):
        result = original_persist(**kwargs)
        persistence_order.append(result.physical_page)
        if result.physical_page == 2:
            second_persisted.set()
        return result

    monkeypatch.setattr(target, "_extract_page", extract)
    monkeypatch.setattr(target, "_persist_page_outcome_v1", persist)
    monkeypatch.setattr(
        target,
        "build_financial_document_manifest_v1",
        lambda *_args, **_kwargs: {"document_manifest_id": "gfdmv1:manifest:" + "a" * 64},
    )
    monkeypatch.setattr(target, "usage_summary_v1", lambda _database: {"run_count": 2})
    result = target.run_openrouter_document_v1(
        pdf=pdf,
        database=database,
        artifact_dir=artifacts,
        api_key="x" * 32,
        workers=2,
    )
    assert result["disposition"] == "SUCCEEDED"
    assert persistence_order == [2, 1]


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


def test_unresolved_page_is_cached_but_never_seals_a_document_manifest(tmp_path) -> None:
    pdf = tmp_path / "document.pdf"
    database = tmp_path / "store.sqlite3"
    artifacts = tmp_path / "artifacts"
    _pdf(pdf, 1)
    calls = 0

    def provider(**_kwargs):
        nonlocal calls
        calls += 1
        return _unresolved_result()

    first = target.run_openrouter_document_v1(
        pdf=pdf,
        database=database,
        artifact_dir=artifacts,
        api_key="x" * 32,
        workers=1,
        provider_call=provider,
    )
    assert first["disposition"] == "NEEDS_RETRY"
    assert first["failed_pages"] == [1]
    assert first["unresolved_pages"] == [1]
    assert first["ingested_pages"] == [1]
    assert not (artifacts / "document-manifest.json").exists()

    replay = target.run_openrouter_document_v1(
        pdf=pdf,
        database=database,
        artifact_dir=artifacts,
        api_key="x" * 32,
        workers=1,
        provider_call=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("cached unresolved page must not trigger a paid provider call")
        ),
    )
    assert calls == 1
    assert replay["disposition"] == "NEEDS_RETRY"
    assert replay["failed_pages"] == [1]
    assert replay["unresolved_pages"] == [1]
    assert replay["cached_pages"] == []
    assert replay["ingested_pages"] == []
    assert not (artifacts / "document-manifest.json").exists()


def test_provider_failure_falls_back_one_page_to_google_and_builds_mixed_manifest(
    tmp_path,
) -> None:
    pdf = tmp_path / "document.pdf"
    database = tmp_path / "store.sqlite3"
    artifacts = tmp_path / "artifacts"
    _pdf(pdf, 2)
    policies = []

    def provider(**kwargs):
        policies.append(kwargs["execution_policy"])
        if kwargs["execution_policy"] == "OPENROUTER_PILOT" and len(policies) == 1:
            error = GeminiJsonFirstProviderV1Error("upstream rate limited")
            error.attempts = (
                {
                    "attempt_ordinal": 1,
                    "credential_slot": "OPENROUTER_SLOT_1",
                    "elapsed_seconds": "0.010",
                    "http_status": 200,
                    "outcome": "ZERO_USAGE_PROVIDER_ERROR",
                    "provider": "OPENROUTER",
                    "usage": None,
                },
            )
            error.raw_response_bytes = b'{"error":"rate-limit"}'
            raise error
        if kwargs["execution_policy"] == "GOOGLE_DIRECT_STANDARD":
            return _google_result()
        return _result()

    result = target.run_openrouter_document_v1(
        pdf=pdf,
        database=database,
        artifact_dir=artifacts,
        api_key="x" * 32,
        workers=1,
        provider_call=provider,
        google_api_keys=["g" * 32],
        google_credential_slots=["GOOGLE_SLOT_2"],
        google_standard_mode="on-provider-error",
    )
    assert result["disposition"] == "SUCCEEDED"
    assert result["failed_pages"] == []
    assert policies == ["OPENROUTER_PILOT", "GOOGLE_DIRECT_STANDARD", "OPENROUTER_PILOT"]
    manifest = json.loads((artifacts / "document-manifest.json").read_bytes())
    assert manifest["format_version"] == "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V4"
    assert {page["provider_route"]["gateway"] for page in manifest["pages"]} == {
        "GOOGLE_GEMINI_API",
        "OPENROUTER",
    }
    fallback = artifacts / "page-00001" / "attempt-0001" / "provider-fallback.json"
    assert json.loads(fallback.read_bytes())["fallback_gateway"] == "GOOGLE_GEMINI_API"


def test_provider_recitation_is_a_typed_retry_frontier(tmp_path) -> None:
    pdf = tmp_path / "document.pdf"
    database = tmp_path / "store.sqlite3"
    artifacts = tmp_path / "artifacts"
    _pdf(pdf, 1)

    def provider(**_kwargs):
        error = GeminiJsonFirstProviderV1Error("provider stopped for recitation")
        error.attempts = ()
        error.raw_response_bytes = b'{"candidates":[{"finishReason":"RECITATION"}]}'
        raise error

    result = target.run_openrouter_document_v1(
        pdf=pdf,
        database=database,
        artifact_dir=artifacts,
        api_key="x" * 32,
        workers=1,
        provider_call=provider,
    )
    assert result["disposition"] == "NEEDS_RETRY"
    assert result["failed_pages"] == [1]
    assert result["recitation_failed_pages"] == [1]
    failure = json.loads((artifacts / "page-00001" / "attempt-0001" / "failure.json").read_bytes())
    assert failure["provider_failure_kind"] == "RECITATION"


def test_recitation_detection_does_not_guess_from_errors_or_other_finish_reasons() -> None:
    for raw in (
        b'{"error":"recitation"}',
        b'{"candidates":[{"finishReason":"SAFETY"}]}',
        b'{"choices":[{"finish_reason":"stop"}]}',
        b"not-json",
    ):
        error = GeminiJsonFirstProviderV1Error("failed")
        error.raw_response_bytes = raw
        assert not target._provider_error_is_recitation_v1(error)


def test_bounded_page_frontier_runs_in_parallel_without_claiming_whole_document(tmp_path) -> None:
    pdf = tmp_path / "document.pdf"
    database = tmp_path / "store.sqlite3"
    artifacts = tmp_path / "artifacts"
    _pdf(pdf, 3)
    calls = []

    def provider(**kwargs):
        calls.append(kwargs["image"])
        return _result()

    result = target.run_openrouter_document_v1(
        pdf=pdf,
        database=database,
        artifact_dir=artifacts,
        api_key="x" * 32,
        workers=2,
        physical_pages=[3, 1],
        provider_call=provider,
    )
    assert result["disposition"] == "SUCCEEDED"
    assert result["document_page_count"] == 3
    assert result["physical_pages"] == [1, 3]
    assert result["ingested_pages"] == [1, 3]
    assert result["page_count"] == 2
    assert [item["physical_page"] for item in result["page_image_sha256s"]] == [1, 3]
    assert len(calls) == 2
    assert not (artifacts / "document-manifest.json").exists()
    contract = json.loads((artifacts / "document-contract.json").read_bytes())
    assert contract["format_version"] == "GEMINI_JSON_FIRST_OPENROUTER_PAGE_FRONTIER_V1"
    assert contract["selected_physical_pages"] == [1, 3]


def test_prior_semantic_response_replays_without_another_paid_provider_call(tmp_path) -> None:
    pdf = tmp_path / "document.pdf"
    database = tmp_path / "store.sqlite3"
    artifacts = tmp_path / "artifacts"
    _pdf(pdf, 1)
    rendered = target._render_page(pdf, 1, 300)
    page = {
        "status": "NO_RELEVANT_FINANCIAL_CONTENT",
        "sections": [],
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
    }
    usage = {
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
        "cost": 0.0001,
        "completion_tokens_details": {"reasoning_tokens": 0},
    }
    raw = (
        json.dumps(
            {
                "id": "response-replay",
                "object": "chat.completion",
                "created": 1,
                "model": "google/gemini-3.7-flash-20260813",
                "provider": "Google",
                "service_tier": "flex",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": json.dumps(page)},
                    }
                ],
                "usage": usage,
            },
            separators=(",", ":"),
        ).encode()
        + b"\n"
    )
    attempt = artifacts / "page-00001" / "attempt-0001"
    attempt.mkdir(parents=True)
    (attempt / "raw-response.json").write_bytes(raw)
    attempts = [
        {
            "attempt_ordinal": 1,
            "credential_slot": "OPENROUTER_SLOT_1",
            "elapsed_seconds": "0.010",
            "http_status": 200,
            "outcome": "COMPLETED",
            "provider": "OPENROUTER",
            "usage": {
                "actual_cost_usd": "0.000100000000",
                "billing_disposition": "BILLED_ACTUAL",
                "cached_input_tokens": 0,
                "input_tokens": 10,
                "output_tokens": 5,
                "thought_tokens": 0,
                "total_tokens": 15,
            },
        }
    ]
    (attempt / "semantic-validation-failure.json").write_text(
        json.dumps(
            {
                "attempts": attempts,
                "error_type": "GeminiFinancialPageJsonV1Error",
                "page": rendered.page,
                "raw_response_sha256": sha256(raw).hexdigest(),
                "usage": attempts[0]["usage"],
            }
        )
    )

    def provider(**kwargs):
        raise AssertionError("a paid provider call was not authorized")

    result = target.run_openrouter_document_v1(
        pdf=pdf,
        database=database,
        artifact_dir=artifacts,
        api_key="x" * 32,
        workers=1,
        provider_call=provider,
    )
    assert result["disposition"] == "SUCCEEDED"
    assert result["ingested_pages"] == [1]
    assert result["semantic_failed_pages"] == []
    assert (artifacts / "page-00001" / "attempt-0002" / "semantic-replay.json").is_file()
