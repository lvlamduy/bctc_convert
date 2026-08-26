#!/usr/bin/env python3
"""Extract one complete PDF through bounded parallel OpenRouter Vertex Flex calls.

The provider requests run concurrently, but every immutable result is validated
and appended to the shared SQLite store by the parent thread.  A rerun consults
the exact image/prompt/model cache and calls the provider only for missing pages.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import fitz

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.gemini_financial_page_json_v1 import (  # noqa: E402
    build_financial_page_json_prompt_v1,
    count_financial_page_content_v1,
    decode_financial_page_json_text_v1,
    financial_page_json_response_schema_v1,
)
from bctc_ai.evaluation.gemini_json_first_provider_v1 import (  # noqa: E402
    GOOGLE_MODEL,
    GOOGLE_STANDARD_SERVICE_TIER,
    OPENROUTER_SERVICE_TIER,
    GeminiJsonFirstProviderV1Error,
    ProviderResultV1,
    call_gemini_json_first_v1,
    load_google_api_key_slots_v1,
    load_openrouter_api_key_v1,
    replay_openrouter_provider_result_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    build_financial_document_manifest_v1,
    extraction_cache_key_v1,
    ingest_financial_page_extraction_v1,
    initialize_gemini_financial_page_store_v1,
    lookup_cached_page_json_v1,
    usage_summary_v1,
)

OPENROUTER_SELECTED_PROVIDER = "Google"


class RunGeminiJsonFirstOpenRouterDocumentV1Error(RuntimeError):
    pass


@dataclass(frozen=True)
class _RenderedPage:
    image: bytes
    page: dict[str, Any]


@dataclass(frozen=True)
class _PageOutcome:
    physical_page: int
    page: dict[str, Any]
    cached_json: dict[str, Any] | None = None
    provider_result: ProviderResultV1 | None = None
    provider_error: GeminiJsonFirstProviderV1Error | None = None
    fallback_source_error: GeminiJsonFirstProviderV1Error | None = None
    semantic_failure_present: bool = False
    semantic_replay_source: str | None = None
    offline_missing: bool = False


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument(
        "--source-logical-name",
        help="Stable corpus-relative filing path; defaults to the PDF filename.",
    )
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument(
        "--physical-page",
        type=int,
        action="append",
        help="Process only this 1-based page; repeat for a bounded fallback frontier.",
    )
    parser.add_argument("--dpi", type=int, choices=(200, 300), default=300)
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument(
        "--prompt-variant",
        choices=("simple", "compact", "balanced"),
        default="simple",
    )
    parser.add_argument(
        "--output-contract-mode",
        choices=("json-schema", "prompt-json"),
        default="json-schema",
    )
    parser.add_argument(
        "--openrouter-key-file",
        type=Path,
        default=ROOT / "docs/experiments/openrouter",
    )
    parser.add_argument(
        "--google-key-file",
        type=Path,
        default=ROOT / "docs/experiments/gemma.txt",
    )
    parser.add_argument("--google-key-slot", type=int)
    parser.add_argument(
        "--google-standard-mode",
        choices=("disabled", "on-provider-error", "for-missing"),
        default="disabled",
        help="Use direct Google standard only after Flex fails, or for every cache miss.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--retry-delay-seconds", type=float, default=5.0)
    parser.add_argument(
        "--offline-replay-only",
        action="store_true",
        help="Use cached pages and immutable semantic raw responses; never call a provider.",
    )
    return parser


def _write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o444)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def _write_or_verify(path: Path, payload: bytes) -> None:
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
            raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
                f"resume artifact differs from its immutable content: {path.name}"
            )
        return
    _write_new(path, payload)


def _next_attempt_dir(root: Path, physical_page: int) -> Path:
    page_root = root / f"page-{physical_page:05d}"
    page_root.mkdir(parents=True, exist_ok=True)
    for ordinal in range(1, 10_000):
        candidate = page_root / f"attempt-{ordinal:04d}"
        try:
            candidate.mkdir(mode=0o700)
        except FileExistsError:
            continue
        return candidate
    raise RunGeminiJsonFirstOpenRouterDocumentV1Error("page attempt frontier is exhausted")


def _document(pdf: Path, source_logical_name: str | None = None) -> tuple[dict[str, Any], int]:
    if pdf.is_symlink() or not pdf.is_file():
        raise RunGeminiJsonFirstOpenRouterDocumentV1Error("PDF must be one regular file")
    source = pdf.read_bytes()
    if not source:
        raise RunGeminiJsonFirstOpenRouterDocumentV1Error("PDF is empty")
    with fitz.open(stream=source, filetype="pdf") as document:
        page_count = document.page_count
    if page_count <= 0:
        raise RunGeminiJsonFirstOpenRouterDocumentV1Error("PDF has no pages")
    return (
        {
            "source_logical_name": source_logical_name or pdf.name,
            "source_sha256": sha256(source).hexdigest(),
            "source_size_bytes": len(source),
        },
        page_count,
    )


def _render_page(pdf: Path, physical_page: int, dpi: int) -> _RenderedPage:
    with fitz.open(pdf) as document:
        pixmap = document.load_page(physical_page - 1).get_pixmap(dpi=dpi, alpha=False)
        image = pixmap.tobytes("png")
        width = pixmap.width
        height = pixmap.height
    return _RenderedPage(
        image=image,
        page={
            "physical_page": physical_page,
            "image_sha256": sha256(image).hexdigest(),
            "image_size_bytes": len(image),
            "pixel_width": width,
            "pixel_height": height,
            "render_dpi": dpi,
            "media_type": "image/png",
        },
    )


def _replay_prior_semantic_result_v1(
    *,
    artifact_dir: Path,
    physical_page: int,
    expected_page: dict[str, Any],
) -> tuple[ProviderResultV1 | None, str | None, bool]:
    """Try every immutable semantic failure before authorizing another paid call."""

    page_root = artifact_dir / f"page-{physical_page:05d}"
    failures = sorted(page_root.glob("attempt-*/semantic-validation-failure.json"))
    if not failures:
        return None, None, False
    for failure_path in failures:
        if failure_path.is_symlink() or not failure_path.is_file():
            raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
                "semantic replay failure receipt is not one regular file"
            )
        failure = json.loads(failure_path.read_bytes())
        if type(failure) is not dict or failure.get("page") != expected_page:
            raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
                "semantic replay page binding drifted"
            )
        attempts = failure.get("attempts")
        raw_path = failure_path.with_name("raw-response.json")
        if type(attempts) is not list or raw_path.is_symlink() or not raw_path.is_file():
            raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
                "semantic replay source receipt is incomplete"
            )
        raw = raw_path.read_bytes()
        if sha256(raw).hexdigest() != failure.get("raw_response_sha256"):
            raise RunGeminiJsonFirstOpenRouterDocumentV1Error("semantic replay source hash drifted")
        result = replay_openrouter_provider_result_v1(raw, attempts=tuple(attempts))
        try:
            decode_financial_page_json_text_v1(result.output_text)
        except Exception:
            continue
        return result, str(raw_path.relative_to(artifact_dir)), True
    return None, None, True


def _extract_page(
    *,
    pdf: Path,
    physical_page: int,
    dpi: int,
    database: Path,
    source_sha256: str,
    source_logical_name: str,
    prompt: str,
    prompt_variant: str,
    prompt_sha256: str,
    schema: dict[str, Any],
    response_schema_sha256: str,
    output_contract_mode: str,
    api_key: str,
    google_api_keys: list[str] | None,
    google_credential_slots: list[str] | None,
    google_standard_mode: str,
    timeout_seconds: int,
    retries: int,
    retry_delay_seconds: float,
    provider_call: Callable[..., ProviderResultV1],
    artifact_dir: Path,
    offline_replay_only: bool,
) -> _PageOutcome:
    rendered = _render_page(pdf, physical_page, dpi)
    cache_key = extraction_cache_key_v1(
        source_sha256=source_sha256,
        source_logical_name=source_logical_name,
        image_sha256=rendered.page["image_sha256"],
        prompt_sha256=prompt_sha256,
        response_schema_sha256=response_schema_sha256,
        requested_model=GOOGLE_MODEL,
        requested_service_tier=OPENROUTER_SERVICE_TIER,
        thinking_level="low",
        prompt_variant=prompt_variant,
        output_contract_mode=output_contract_mode,
    )
    cached = lookup_cached_page_json_v1(database, cache_key)
    if cached is not None:
        return _PageOutcome(physical_page=physical_page, page=rendered.page, cached_json=cached)
    if google_api_keys is not None:
        google_cache_key = extraction_cache_key_v1(
            source_sha256=source_sha256,
            source_logical_name=source_logical_name,
            image_sha256=rendered.page["image_sha256"],
            prompt_sha256=prompt_sha256,
            response_schema_sha256=response_schema_sha256,
            requested_model=GOOGLE_MODEL,
            requested_service_tier=GOOGLE_STANDARD_SERVICE_TIER,
            thinking_level="low",
            prompt_variant=prompt_variant,
            output_contract_mode=output_contract_mode,
        )
        cached = lookup_cached_page_json_v1(database, google_cache_key)
        if cached is not None:
            return _PageOutcome(
                physical_page=physical_page,
                page=rendered.page,
                cached_json=cached,
            )
    replayed, replay_source, semantic_failure_present = _replay_prior_semantic_result_v1(
        artifact_dir=artifact_dir,
        physical_page=physical_page,
        expected_page=rendered.page,
    )
    if replayed is not None:
        return _PageOutcome(
            physical_page=physical_page,
            page=rendered.page,
            provider_result=replayed,
            semantic_failure_present=True,
            semantic_replay_source=replay_source,
        )
    if semantic_failure_present:
        return _PageOutcome(
            physical_page=physical_page,
            page=rendered.page,
            semantic_failure_present=True,
        )
    if offline_replay_only:
        return _PageOutcome(
            physical_page=physical_page,
            page=rendered.page,
            offline_missing=True,
        )
    fallback_source_error = None
    try:
        result = provider_call(
            google_api_keys=(google_api_keys if google_standard_mode == "for-missing" else None),
            google_credential_slots=(
                google_credential_slots if google_standard_mode == "for-missing" else None
            ),
            openrouter_api_key=(None if google_standard_mode == "for-missing" else api_key),
            image=rendered.image,
            media_type="image/png",
            prompt=prompt,
            response_schema=schema,
            output_contract_mode=output_contract_mode,
            execution_policy=(
                "GOOGLE_DIRECT_STANDARD"
                if google_standard_mode == "for-missing"
                else "OPENROUTER_PILOT"
            ),
            timeout_seconds=timeout_seconds,
            openrouter_retries=retries,
            retry_delay_seconds=retry_delay_seconds,
        )
    except GeminiJsonFirstProviderV1Error as exc:
        if google_standard_mode != "on-provider-error" or google_api_keys is None:
            return _PageOutcome(
                physical_page=physical_page,
                page=rendered.page,
                provider_error=exc,
            )
        fallback_source_error = exc
        try:
            result = provider_call(
                google_api_keys=google_api_keys,
                google_credential_slots=google_credential_slots,
                openrouter_api_key=None,
                image=rendered.image,
                media_type="image/png",
                prompt=prompt,
                response_schema=schema,
                output_contract_mode=output_contract_mode,
                execution_policy="GOOGLE_DIRECT_STANDARD",
                timeout_seconds=timeout_seconds,
                flex_retries_per_slot=retries,
                retry_delay_seconds=retry_delay_seconds,
            )
        except GeminiJsonFirstProviderV1Error as fallback_exc:
            return _PageOutcome(
                physical_page=physical_page,
                page=rendered.page,
                provider_error=fallback_exc,
                fallback_source_error=fallback_source_error,
            )
    return _PageOutcome(
        physical_page=physical_page,
        page=rendered.page,
        provider_result=result,
        fallback_source_error=fallback_source_error,
    )


def run_openrouter_document_v1(
    *,
    pdf: Path,
    database: Path,
    artifact_dir: Path,
    api_key: str,
    source_logical_name: str | None = None,
    dpi: int = 300,
    workers: int = 5,
    prompt_variant: str = "simple",
    output_contract_mode: str = "JSON_SCHEMA",
    timeout_seconds: int = 900,
    retries: int = 2,
    retry_delay_seconds: float = 5.0,
    provider_call: Callable[..., ProviderResultV1] = call_gemini_json_first_v1,
    physical_pages: Sequence[int] | None = None,
    offline_replay_only: bool = False,
    google_api_keys: list[str] | None = None,
    google_credential_slots: list[str] | None = None,
    google_standard_mode: str = "disabled",
) -> dict[str, Any]:
    """Run or resume a whole document or one explicit bounded page frontier."""

    if dpi not in {200, 300} or type(workers) is not int or not 1 <= workers <= 32:
        raise RunGeminiJsonFirstOpenRouterDocumentV1Error("DPI or worker count is invalid")
    if output_contract_mode not in {"JSON_SCHEMA", "PROMPT_JSON"}:
        raise RunGeminiJsonFirstOpenRouterDocumentV1Error("output contract mode is invalid")
    if google_standard_mode not in {"disabled", "on-provider-error", "for-missing"}:
        raise RunGeminiJsonFirstOpenRouterDocumentV1Error("Google fallback mode is invalid")
    if (google_standard_mode == "disabled") != (google_api_keys is None):
        raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
            "Google fallback credentials and mode disagree"
        )
    if google_api_keys is not None and (
        not google_api_keys
        or google_credential_slots is None
        or len(google_api_keys) != len(google_credential_slots)
    ):
        raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
            "Google fallback credential slots are invalid"
        )
    document, page_count = _document(pdf, source_logical_name)
    selected_pages = (
        list(range(1, page_count + 1)) if physical_pages is None else sorted(set(physical_pages))
    )
    if (
        not selected_pages
        or len(selected_pages) != (page_count if physical_pages is None else len(physical_pages))
        or any(type(page) is not int or page <= 0 or page > page_count for page in selected_pages)
    ):
        raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
            "selected physical-page frontier is empty, duplicate, or out of range"
        )
    prompt = build_financial_page_json_prompt_v1(
        variant=prompt_variant,
        include_contract_template=output_contract_mode == "PROMPT_JSON",
    )
    schema = financial_page_json_response_schema_v1()
    prompt_bytes = prompt.encode("utf-8")
    schema_bytes = canonical_json_bytes_v1(schema)
    prompt_sha = sha256(prompt_bytes).hexdigest()
    schema_sha = canonical_json_sha256_v1(schema)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    _write_or_verify(artifact_dir / "prompt.txt", prompt_bytes)
    _write_or_verify(artifact_dir / "response-schema.json", schema_bytes)
    contract = {
        "document": document,
        "dpi": dpi,
        "format_version": "GEMINI_JSON_FIRST_OPENROUTER_DOCUMENT_V1",
        "output_contract_mode": output_contract_mode,
        "page_count": page_count,
        "prompt_sha256": prompt_sha,
        "prompt_variant": prompt_variant,
        "requested_model": GOOGLE_MODEL,
        "requested_service_tier": OPENROUTER_SERVICE_TIER,
        "response_schema_sha256": schema_sha,
        "selected_provider": OPENROUTER_SELECTED_PROVIDER,
    }
    if google_standard_mode != "disabled":
        contract["google_standard_mode"] = google_standard_mode
    if physical_pages is not None:
        contract["format_version"] = "GEMINI_JSON_FIRST_OPENROUTER_PAGE_FRONTIER_V1"
        contract["selected_physical_pages"] = selected_pages
    contract["document_run_id"] = "gjfporv1:document:" + canonical_json_sha256_v1(contract)
    _write_or_verify(artifact_dir / "document-contract.json", canonical_json_bytes_v1(contract))
    if not database.exists():
        initialize_gemini_financial_page_store_v1(database)

    outcomes: dict[int, _PageOutcome] = {}
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="gemini-page") as executor:
        futures = {
            executor.submit(
                _extract_page,
                pdf=pdf,
                physical_page=physical_page,
                dpi=dpi,
                database=database,
                source_sha256=document["source_sha256"],
                source_logical_name=document["source_logical_name"],
                prompt=prompt,
                prompt_variant=prompt_variant,
                prompt_sha256=prompt_sha,
                schema=schema,
                response_schema_sha256=schema_sha,
                output_contract_mode=output_contract_mode,
                api_key=api_key,
                google_api_keys=google_api_keys,
                google_credential_slots=google_credential_slots,
                google_standard_mode=google_standard_mode,
                timeout_seconds=timeout_seconds,
                retries=retries,
                retry_delay_seconds=retry_delay_seconds,
                provider_call=provider_call,
                artifact_dir=artifact_dir,
                offline_replay_only=offline_replay_only,
            ): physical_page
            for physical_page in selected_pages
        }
        for future in as_completed(futures):
            outcome = future.result()
            outcomes[outcome.physical_page] = outcome

    failed_pages: list[int] = []
    semantic_failed_pages: list[int] = []
    offline_missing_pages: list[int] = []
    cached_pages: list[int] = []
    ingested_pages: list[int] = []
    for physical_page in selected_pages:
        outcome = outcomes[physical_page]
        if outcome.cached_json is not None:
            cached_pages.append(physical_page)
            continue
        if outcome.semantic_failure_present and outcome.provider_result is None:
            failed_pages.append(physical_page)
            semantic_failed_pages.append(physical_page)
            continue
        if outcome.offline_missing:
            failed_pages.append(physical_page)
            offline_missing_pages.append(physical_page)
            continue
        attempt_dir = _next_attempt_dir(artifact_dir, physical_page)
        if outcome.provider_error is not None:
            error = outcome.provider_error
            if error.raw_response_bytes is not None:
                raw = error.raw_response_bytes
                _write_new(
                    attempt_dir / "raw-response-before-validation.json",
                    raw if raw.endswith(b"\n") else raw + b"\n",
                )
            _write_new(
                attempt_dir / "failure.json",
                canonical_json_bytes_v1(
                    {
                        "attempts": list(error.attempts),
                        "error_type": type(error).__name__,
                        "page": outcome.page,
                    }
                ),
            )
            failed_pages.append(physical_page)
            continue
        result = outcome.provider_result
        if result is None:
            raise AssertionError("page outcome has no terminal disposition")
        raw = result.raw_response_bytes
        raw_bytes = raw if raw.endswith(b"\n") else raw + b"\n"
        _write_new(attempt_dir / "raw-response.json", raw_bytes)
        if outcome.fallback_source_error is not None:
            source_error = outcome.fallback_source_error
            if source_error.raw_response_bytes is not None:
                source_raw = source_error.raw_response_bytes
                _write_new(
                    attempt_dir / "source-raw-response-before-fallback.json",
                    source_raw if source_raw.endswith(b"\n") else source_raw + b"\n",
                )
            _write_new(
                attempt_dir / "provider-fallback.json",
                canonical_json_bytes_v1(
                    {
                        "fallback_gateway": "GOOGLE_GEMINI_API",
                        "source_attempts": list(source_error.attempts),
                        "source_error_type": type(source_error).__name__,
                    }
                ),
            )
        if outcome.semantic_replay_source is not None:
            _write_new(
                attempt_dir / "semantic-replay.json",
                canonical_json_bytes_v1(
                    {
                        "raw_response_sha256": sha256(raw_bytes).hexdigest(),
                        "source_relative_path": outcome.semantic_replay_source,
                    }
                ),
            )
        try:
            page_json = decode_financial_page_json_text_v1(result.output_text)
        except Exception as exc:
            _write_new(
                attempt_dir / "semantic-validation-failure.json",
                canonical_json_bytes_v1(
                    {
                        "attempts": list(result.attempts),
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                        "page": outcome.page,
                        "raw_response_sha256": sha256(raw_bytes).hexdigest(),
                        "usage": result.usage,
                    }
                ),
            )
            failed_pages.append(physical_page)
            semantic_failed_pages.append(physical_page)
            continue
        if result.provider_name not in {OPENROUTER_SELECTED_PROVIDER, "GOOGLE_GEMINI_API"}:
            raise RunGeminiJsonFirstOpenRouterDocumentV1Error("selected provider identity drifted")
        requested_service_tier = (
            GOOGLE_STANDARD_SERVICE_TIER
            if result.provider_name == "GOOGLE_GEMINI_API"
            else OPENROUTER_SERVICE_TIER
        )
        identities = ingest_financial_page_extraction_v1(
            database,
            document=document,
            page=outcome.page,
            prompt_variant=prompt_variant,
            output_contract_mode=output_contract_mode,
            prompt_sha256=prompt_sha,
            response_schema_sha256=schema_sha,
            requested_model=GOOGLE_MODEL,
            requested_service_tier=requested_service_tier,
            thinking_level="low",
            provider_result=result,
            page_json=page_json,
        )
        page_bytes = canonical_json_bytes_v1(page_json)
        _write_new(attempt_dir / "page.json", page_bytes)
        _write_new(
            attempt_dir / "observation.json",
            canonical_json_bytes_v1(
                {
                    "attempts": list(result.attempts),
                    "content_counts": count_financial_page_content_v1(page_json),
                    "database_identities": identities,
                    "page": outcome.page,
                    "page_json_sha256": sha256(page_bytes).hexdigest(),
                    "provider_model": result.provider_model,
                    "provider_name": result.provider_name,
                    "raw_response_sha256": sha256(raw_bytes).hexdigest(),
                    "service_tier": result.service_tier,
                    "usage": result.usage,
                }
            ),
        )
        ingested_pages.append(physical_page)

    manifest = None
    if not failed_pages and physical_pages is None:
        manifest_kwargs = (
            {
                "allowed_gateway_service_tiers": [
                    {
                        "gateway": "GOOGLE_GEMINI_API",
                        "requested_service_tier": GOOGLE_STANDARD_SERVICE_TIER,
                    },
                    {
                        "gateway": "OPENROUTER",
                        "requested_service_tier": OPENROUTER_SERVICE_TIER,
                    },
                ]
            }
            if google_standard_mode != "disabled"
            else {
                "requested_service_tier": OPENROUTER_SERVICE_TIER,
                "selected_provider": OPENROUTER_SELECTED_PROVIDER,
            }
        )
        manifest = build_financial_document_manifest_v1(
            database,
            source_sha256=document["source_sha256"],
            source_logical_name=document["source_logical_name"],
            expected_physical_pages=range(1, page_count + 1),
            prompt_sha256=prompt_sha,
            response_schema_sha256=schema_sha,
            requested_model=GOOGLE_MODEL,
            **manifest_kwargs,
        )
        _write_or_verify(
            artifact_dir / "document-manifest.json",
            canonical_json_bytes_v1(manifest),
        )
    summary = {
        "cached_pages": cached_pages,
        "disposition": "SUCCEEDED" if not failed_pages else "NEEDS_RETRY",
        "document_run_id": contract["document_run_id"],
        "failed_pages": failed_pages,
        "ingested_pages": ingested_pages,
        "manifest_id": manifest["document_manifest_id"] if manifest is not None else None,
        "offline_missing_pages": offline_missing_pages,
        "page_count": len(selected_pages),
        "semantic_failed_pages": semantic_failed_pages,
        "usage": usage_summary_v1(database),
    }
    if physical_pages is not None:
        summary["document_page_count"] = page_count
        summary["physical_pages"] = selected_pages
    summary_bytes = canonical_json_bytes_v1(summary)
    _write_or_verify(
        artifact_dir / "run-receipts" / (sha256(summary_bytes).hexdigest() + ".json"),
        summary_bytes,
    )
    return summary


def main() -> int:
    args = _parser().parse_args()
    google_keys = None
    google_slots = None
    if args.google_standard_mode != "disabled":
        google_keys = load_google_api_key_slots_v1(args.google_key_file)
        google_slots = [f"GOOGLE_SLOT_{index}" for index in range(1, len(google_keys) + 1)]
        if args.google_key_slot is not None:
            if not 1 <= args.google_key_slot <= len(google_keys):
                raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
                    "Google fallback key slot lies outside the credential file"
                )
            google_keys = [google_keys[args.google_key_slot - 1]]
            google_slots = [f"GOOGLE_SLOT_{args.google_key_slot}"]
    result = run_openrouter_document_v1(
        pdf=args.pdf,
        database=args.database,
        artifact_dir=args.artifact_dir,
        api_key=(
            "" if args.offline_replay_only else load_openrouter_api_key_v1(args.openrouter_key_file)
        ),
        source_logical_name=args.source_logical_name,
        dpi=args.dpi,
        workers=args.workers,
        prompt_variant=args.prompt_variant,
        output_contract_mode=args.output_contract_mode.replace("-", "_").upper(),
        timeout_seconds=args.timeout_seconds,
        retries=args.retries,
        retry_delay_seconds=args.retry_delay_seconds,
        physical_pages=args.physical_page,
        offline_replay_only=args.offline_replay_only,
        google_api_keys=google_keys,
        google_credential_slots=google_slots,
        google_standard_mode=args.google_standard_mode,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["disposition"] == "SUCCEEDED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
