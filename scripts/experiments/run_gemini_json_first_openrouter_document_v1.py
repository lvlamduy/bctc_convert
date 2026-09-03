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
import tempfile
import time
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
from bctc_ai.evaluation.gemini_json_first_page_render_v1 import (  # noqa: E402
    render_full_pdf_page_v1,
)
from bctc_ai.evaluation.gemini_json_first_provider_v1 import (  # noqa: E402
    GOOGLE_MODEL,
    GOOGLE_STANDARD_SERVICE_TIER,
    OPENROUTER_PROVIDER,
    OPENROUTER_ROUTE_POLICIES,
    OPENROUTER_SERVICE_TIER,
    OPENROUTER_STANDARD_FALLBACK_PROVIDER,
    OPENROUTER_STANDARD_FALLBACK_SERVICE_TIER,
    GeminiJsonFirstProviderV1Error,
    ProviderResultV1,
    call_gemini_json_first_v1,
    load_google_api_key_slots_v1,
    load_openrouter_api_key_v1,
    replay_google_standard_provider_result_v1,
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
OPENROUTER_STANDARD_FALLBACK_SELECTED_PROVIDER = "Google AI Studio"


class RunGeminiJsonFirstOpenRouterDocumentV1Error(RuntimeError):
    pass


@dataclass(frozen=True)
class _RenderedPage:
    image: bytes
    page: dict[str, Any]
    receipt: dict[str, Any]


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


@dataclass(frozen=True)
class _PersistedPageOutcome:
    physical_page: int
    page: dict[str, Any]
    disposition: str
    semantic_replay_source: str | None = None
    provider_request_made: bool = False


def _provider_error_is_recitation_v1(error: GeminiJsonFirstProviderV1Error) -> bool:
    """Recognize the provider's explicit no-output recitation disposition."""

    raw = error.raw_response_bytes
    if type(raw) is not bytes or not raw:
        return False
    try:
        envelope = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False
    if type(envelope) is not dict:
        return False
    candidates = envelope.get("candidates")
    if type(candidates) is list and any(
        type(candidate) is dict and candidate.get("finishReason") == "RECITATION"
        for candidate in candidates
    ):
        return True
    choices = envelope.get("choices")
    return type(choices) is list and any(
        type(choice) is dict
        and choice.get("finish_reason", choice.get("finishReason")) == "RECITATION"
        for choice in choices
    )


def _provider_error_opens_circuit_v1(error: GeminiJsonFirstProviderV1Error) -> bool:
    """Recognize provider-wide failures for which another immediate page is unsafe."""

    return any(
        type(attempt) is dict
        and (
            attempt.get("outcome") in {"TRANSIENT_HTTP_ERROR", "ZERO_USAGE_PROVIDER_ERROR"}
            or attempt.get("http_status") in {429, 500, 502, 503, 504}
        )
        for attempt in error.attempts
    )


def _effective_provider_request_delay_seconds_v1(
    configured: float | None, *, stop_on_transient: bool
) -> float:
    if configured is None:
        return 60.0 if stop_on_transient else 0.0
    return configured


def _effective_provider_attempts_v1(configured: int | None, *, stop_on_transient: bool) -> int:
    if configured is None:
        return 1 if stop_on_transient else 2
    return configured


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
        choices=("simple", "items", "scope", "compact", "balanced"),
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
        "--openrouter-route-policy",
        choices=("flex-only", "flex-then-standard"),
        default="flex-only",
        help=(
            "Pin Vertex Flex, or try Vertex Flex first and then the cheapest "
            "compatible OpenRouter standard endpoint (Google AI Studio)."
        ),
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
    parser.add_argument("--retries", type=int)
    parser.add_argument("--retry-delay-seconds", type=float, default=5.0)
    parser.add_argument(
        "--stop-provider-frontier-on-transient-error",
        action="store_true",
        help=(
            "With one worker, stop further provider calls after a transient/zero-usage "
            "provider failure; remaining pages are checked only through cache/offline replay."
        ),
    )
    parser.add_argument(
        "--provider-request-delay-seconds",
        type=float,
        help=(
            "Pause after each successful single-worker provider request. When omitted, "
            "the transient circuit-breaker mode uses 60 seconds and other modes use zero."
        ),
    )
    parser.add_argument(
        "--offline-replay-only",
        action="store_true",
        help="Use cached pages and immutable semantic raw responses; never call a provider.",
    )
    parser.add_argument(
        "--semantic-replay-source-dir",
        type=Path,
        help=(
            "Read immutable semantic-failure responses from this artifact directory while "
            "writing the new replay receipt under --artifact-dir."
        ),
    )
    return parser


def _write_new(path: Path, payload: bytes) -> None:
    """Publish one immutable artifact without exposing a partial final file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, stage_name = tempfile.mkstemp(prefix=f".{path.name}.stage-", dir=path.parent)
    stage = Path(stage_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(stage, 0o444)
        os.link(stage, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        stage.unlink(missing_ok=True)


def _write_or_verify(path: Path, payload: bytes) -> None:
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
            raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
                f"resume artifact differs from its immutable content: {path.name}"
            )
        return
    _write_new(path, payload)


_SEMANTIC_REPLAY_CONTRACT_FIELDS = {
    "document",
    "dpi",
    "output_contract_mode",
    "prompt_sha256",
    "prompt_variant",
    "requested_model",
    "requested_service_tier",
    "response_schema_sha256",
    "selected_provider",
}
_SEMANTIC_REPLAY_SOURCE_ROOT_FIELDS = _SEMANTIC_REPLAY_CONTRACT_FIELDS - {
    "prompt_sha256",
    "prompt_variant",
}


def _canonical_semantic_replay_contract_v1(source_dir: Path) -> dict[str, Any]:
    contract_path = source_dir / "document-contract.json"
    if contract_path.is_symlink() or not contract_path.is_file():
        raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
            "semantic replay source lacks one immutable document contract"
        )
    raw = contract_path.read_bytes()
    try:
        contract = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
            "semantic replay source document contract is invalid"
        ) from exc
    if type(contract) is not dict or raw != canonical_json_bytes_v1(contract):
        raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
            "semantic replay source document contract is not canonical"
        )
    return contract


def _validate_external_semantic_replay_contract_v1(
    source_dir: Path,
    *,
    expected_contract: dict[str, Any],
) -> None:
    contract = _canonical_semantic_replay_contract_v1(source_dir)
    if any(
        contract.get(field) != expected_contract[field]
        for field in _SEMANTIC_REPLAY_SOURCE_ROOT_FIELDS
    ):
        raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
            "semantic replay source document contract drifted"
        )


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


def _render_page(
    pdf: Path,
    physical_page: int,
    dpi: int,
    source_sha256: str | None = None,
) -> _RenderedPage:
    if source_sha256 is None:
        source_sha256 = sha256(pdf.read_bytes()).hexdigest()
    with fitz.open(pdf) as document:
        rendered = render_full_pdf_page_v1(
            document.load_page(physical_page - 1),
            physical_page=physical_page,
            dpi=dpi,
            source_sha256=source_sha256,
        )
    return _RenderedPage(
        image=rendered.image,
        page=rendered.page,
        receipt=rendered.receipt,
    )


def _replay_prior_semantic_result_v1(
    *,
    artifact_dir: Path,
    physical_page: int,
    expected_page: dict[str, Any],
    expected_contract: dict[str, Any],
) -> tuple[ProviderResultV1 | None, str | None, bool]:
    """Try every immutable semantic failure before authorizing another paid call."""

    failures = sorted(
        artifact_dir.rglob(f"page-{physical_page:05d}/attempt-*/semantic-validation-failure.json")
    )
    if not failures:
        return None, None, False
    matching_failure = False
    for failure_path in failures:
        if failure_path.is_symlink() or not failure_path.is_file():
            raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
                "semantic replay failure receipt is not one regular file"
            )
        source_artifact_dir = failure_path.parents[2]
        source_contract = _canonical_semantic_replay_contract_v1(source_artifact_dir)
        if any(
            source_contract.get(field) != expected_contract[field]
            for field in _SEMANTIC_REPLAY_CONTRACT_FIELDS
        ):
            continue
        failure = json.loads(failure_path.read_bytes())
        prior_page = failure.get("page") if type(failure) is dict else None
        if type(prior_page) is not dict or any(
            prior_page.get(field) != expected_page[field]
            for field in ("media_type", "physical_page", "render_dpi")
        ):
            raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
                "semantic replay page binding drifted"
            )
        if prior_page != expected_page:
            continue
        matching_failure = True
        attempts = failure.get("attempts")
        raw_path = failure_path.with_name("raw-response.json")
        if type(attempts) is not list or raw_path.is_symlink() or not raw_path.is_file():
            raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
                "semantic replay source receipt is incomplete"
            )
        raw = raw_path.read_bytes()
        if sha256(raw).hexdigest() != failure.get("raw_response_sha256"):
            raise RunGeminiJsonFirstOpenRouterDocumentV1Error("semantic replay source hash drifted")
        try:
            envelope = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
                "semantic replay source is not JSON"
            ) from exc
        if type(envelope) is not dict:
            raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
                "semantic replay source is not one JSON object"
            )
        if "choices" in envelope:
            result = replay_openrouter_provider_result_v1(raw, attempts=tuple(attempts))
        elif "candidates" in envelope:
            result = replay_google_standard_provider_result_v1(raw, attempts=tuple(attempts))
        else:
            raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
                "semantic replay provider envelope is unknown"
            )
        try:
            decode_financial_page_json_text_v1(result.output_text)
        except Exception:
            continue
        return result, str(raw_path.relative_to(artifact_dir)), True
    return None, None, matching_failure


def _replay_prior_provider_validation_result_v1(
    *,
    artifact_dir: Path,
    physical_page: int,
    expected_page: dict[str, Any],
    expected_contract: dict[str, Any],
    openrouter_route_policy: str,
) -> tuple[ProviderResultV1 | None, str | None]:
    """Recover a complete response rejected only by an older route validator.

    Provider-validation failures predate the semantic receipt, so they do not
    carry a raw-response hash.  Replay is nevertheless safe because the source
    must be one immutable regular file bound to the same document contract and
    rendered page, and both the current provider validator and the complete
    financial-page decoder must accept its bytes.  The new attempt writes a
    hash-bound semantic replay receipt before ingestion.
    """

    failures = sorted(artifact_dir.rglob(f"page-{physical_page:05d}/attempt-*/failure.json"))
    for failure_path in failures:
        if failure_path.is_symlink() or not failure_path.is_file():
            raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
                "provider replay failure receipt is not one regular file"
            )
        raw_path = failure_path.with_name("raw-response-before-validation.json")
        if not raw_path.exists():
            continue
        if raw_path.is_symlink() or not raw_path.is_file():
            raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
                "provider replay source is not one regular file"
            )
        source_artifact_dir = failure_path.parents[2]
        source_contract = _canonical_semantic_replay_contract_v1(source_artifact_dir)
        if any(
            source_contract.get(field) != expected_contract[field]
            for field in _SEMANTIC_REPLAY_CONTRACT_FIELDS
        ):
            continue
        try:
            failure = json.loads(failure_path.read_bytes())
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
                "provider replay failure receipt is not JSON"
            ) from exc
        prior_page = failure.get("page") if type(failure) is dict else None
        if type(prior_page) is not dict or any(
            prior_page.get(field) != expected_page[field]
            for field in ("media_type", "physical_page", "render_dpi")
        ):
            raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
                "provider replay page binding drifted"
            )
        if prior_page != expected_page:
            continue
        attempts = failure.get("attempts")
        if (
            type(attempts) is not list
            or not attempts
            or any(type(attempt) is not dict for attempt in attempts)
        ):
            raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
                "provider replay attempts are invalid"
            )
        raw = raw_path.read_bytes()
        try:
            result = replay_openrouter_provider_result_v1(raw, attempts=tuple(attempts))
            decode_financial_page_json_text_v1(result.output_text)
        except Exception:
            continue
        if (
            result.provider_name == OPENROUTER_STANDARD_FALLBACK_SELECTED_PROVIDER
            and openrouter_route_policy != "FLEX_THEN_STANDARD"
        ):
            continue
        return result, str(raw_path.relative_to(artifact_dir))
    return None, None


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
    openrouter_route_policy: str,
    timeout_seconds: int,
    retries: int,
    retry_delay_seconds: float,
    provider_call: Callable[..., ProviderResultV1],
    artifact_dir: Path,
    semantic_replay_source_dir: Path | None,
    semantic_replay_expected_contract: dict[str, Any],
    offline_replay_only: bool,
) -> _PageOutcome:
    rendered = _render_page(pdf, physical_page, dpi, source_sha256)
    _write_or_verify(
        artifact_dir / f"page-{physical_page:05d}" / "render-receipt.json",
        canonical_json_bytes_v1(rendered.receipt),
    )
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
    if google_api_keys is not None or openrouter_route_policy == "FLEX_THEN_STANDARD":
        standard_cache_key = extraction_cache_key_v1(
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
        cached = lookup_cached_page_json_v1(database, standard_cache_key)
        if cached is not None:
            return _PageOutcome(
                physical_page=physical_page,
                page=rendered.page,
                cached_json=cached,
            )
    replayed, replay_source, semantic_failure_present = _replay_prior_semantic_result_v1(
        artifact_dir=semantic_replay_source_dir or artifact_dir,
        physical_page=physical_page,
        expected_page=rendered.page,
        expected_contract=semantic_replay_expected_contract,
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
    replayed, replay_source = _replay_prior_provider_validation_result_v1(
        artifact_dir=semantic_replay_source_dir or artifact_dir,
        physical_page=physical_page,
        expected_page=rendered.page,
        expected_contract=semantic_replay_expected_contract,
        openrouter_route_policy=openrouter_route_policy,
    )
    if replayed is not None:
        return _PageOutcome(
            physical_page=physical_page,
            page=rendered.page,
            provider_result=replayed,
            semantic_replay_source=replay_source,
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
            openrouter_route_policy=openrouter_route_policy,
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


def _persist_page_outcome_v1(
    *,
    outcome: _PageOutcome,
    artifact_dir: Path,
    database: Path,
    document: dict[str, Any],
    prompt_variant: str,
    output_contract_mode: str,
    prompt_sha256: str,
    response_schema_sha256: str,
) -> _PersistedPageOutcome:
    """Persist one completed future immediately and release its provider payload."""

    physical_page = outcome.physical_page
    if outcome.cached_json is not None:
        disposition = (
            "CACHED_UNRESOLVED" if outcome.cached_json["status"] == "UNRESOLVED_PAGE" else "CACHED"
        )
        return _PersistedPageOutcome(physical_page, outcome.page, disposition)
    if outcome.semantic_failure_present and outcome.provider_result is None:
        return _PersistedPageOutcome(physical_page, outcome.page, "SEMANTIC_FAILED")
    if outcome.offline_missing:
        return _PersistedPageOutcome(physical_page, outcome.page, "OFFLINE_MISSING")
    attempt_dir = _next_attempt_dir(artifact_dir, physical_page)
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
    if outcome.provider_error is not None:
        error = outcome.provider_error
        recitation = _provider_error_is_recitation_v1(error)
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
                    "provider_failure_kind": (
                        "RECITATION" if recitation else "OTHER_PROVIDER_FAILURE"
                    ),
                }
            ),
        )
        return _PersistedPageOutcome(
            physical_page,
            outcome.page,
            "PROVIDER_RECITATION_FAILED" if recitation else "PROVIDER_FAILED",
            provider_request_made=True,
        )
    result = outcome.provider_result
    if result is None:
        raise AssertionError("page outcome has no terminal disposition")
    raw = result.raw_response_bytes
    raw_bytes = raw if raw.endswith(b"\n") else raw + b"\n"
    _write_new(attempt_dir / "raw-response.json", raw_bytes)
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
        return _PersistedPageOutcome(
            physical_page,
            outcome.page,
            "SEMANTIC_FAILED",
            semantic_replay_source=outcome.semantic_replay_source,
            provider_request_made=outcome.semantic_replay_source is None,
        )
    if result.provider_name not in {
        OPENROUTER_SELECTED_PROVIDER,
        OPENROUTER_STANDARD_FALLBACK_SELECTED_PROVIDER,
        "GOOGLE_GEMINI_API",
    }:
        raise RunGeminiJsonFirstOpenRouterDocumentV1Error("selected provider identity drifted")
    if result.provider_name == "GOOGLE_GEMINI_API":
        requested_service_tier = GOOGLE_STANDARD_SERVICE_TIER
    elif result.provider_name == OPENROUTER_STANDARD_FALLBACK_SELECTED_PROVIDER:
        requested_service_tier = OPENROUTER_STANDARD_FALLBACK_SERVICE_TIER
    else:
        requested_service_tier = result.service_tier
    identities = ingest_financial_page_extraction_v1(
        database,
        document=document,
        page=outcome.page,
        prompt_variant=prompt_variant,
        output_contract_mode=output_contract_mode,
        prompt_sha256=prompt_sha256,
        response_schema_sha256=response_schema_sha256,
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
    disposition = "INGESTED_UNRESOLVED" if page_json["status"] == "UNRESOLVED_PAGE" else "INGESTED"
    return _PersistedPageOutcome(
        physical_page,
        outcome.page,
        disposition,
        outcome.semantic_replay_source,
        outcome.semantic_replay_source is None,
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
    semantic_replay_source_dir: Path | None = None,
    google_api_keys: list[str] | None = None,
    google_credential_slots: list[str] | None = None,
    google_standard_mode: str = "disabled",
    stop_provider_frontier_on_transient_error: bool = False,
    provider_request_delay_seconds: float = 0.0,
    openrouter_route_policy: str = "FLEX_ONLY",
) -> dict[str, Any]:
    """Run or resume a whole document or one explicit bounded page frontier."""

    if dpi not in {200, 300} or type(workers) is not int or not 1 <= workers <= 32:
        raise RunGeminiJsonFirstOpenRouterDocumentV1Error("DPI or worker count is invalid")
    if output_contract_mode not in {"JSON_SCHEMA", "PROMPT_JSON"}:
        raise RunGeminiJsonFirstOpenRouterDocumentV1Error("output contract mode is invalid")
    if google_standard_mode not in {"disabled", "on-provider-error", "for-missing"}:
        raise RunGeminiJsonFirstOpenRouterDocumentV1Error("Google fallback mode is invalid")
    if openrouter_route_policy not in OPENROUTER_ROUTE_POLICIES:
        raise RunGeminiJsonFirstOpenRouterDocumentV1Error("OpenRouter route policy is invalid")
    if type(stop_provider_frontier_on_transient_error) is not bool:
        raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
            "provider circuit-breaker policy is invalid"
        )
    if stop_provider_frontier_on_transient_error and workers != 1:
        raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
            "provider circuit breaker requires exactly one worker"
        )
    if (
        type(provider_request_delay_seconds) not in {int, float}
        or not 0 <= provider_request_delay_seconds <= 3_600
    ):
        raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
            "provider request delay lies outside 0..3600 seconds"
        )
    if provider_request_delay_seconds > 0 and not stop_provider_frontier_on_transient_error:
        raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
            "provider request delay requires the single-worker circuit breaker"
        )
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
    if semantic_replay_source_dir is not None and (
        semantic_replay_source_dir.is_symlink() or not semantic_replay_source_dir.is_dir()
    ):
        raise RunGeminiJsonFirstOpenRouterDocumentV1Error(
            "semantic replay source must be one existing regular directory"
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
        "execution_mode": "OFFLINE_REPLAY_ONLY" if offline_replay_only else "PROVIDER_OR_CACHE",
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
    if semantic_replay_source_dir is not None:
        _validate_external_semantic_replay_contract_v1(
            semantic_replay_source_dir,
            expected_contract=contract,
        )
    _write_or_verify(artifact_dir / "document-contract.json", canonical_json_bytes_v1(contract))
    routing_policy = {
        "format_version": "OPENROUTER_PROVIDER_ROUTING_POLICY_V1",
        "route_policy": openrouter_route_policy,
        "routes": [
            {
                "provider_slug": OPENROUTER_PROVIDER,
                "requested_service_tier": OPENROUTER_SERVICE_TIER,
                "selected_provider": OPENROUTER_SELECTED_PROVIDER,
            },
            *(
                [
                    {
                        "provider_slug": OPENROUTER_STANDARD_FALLBACK_PROVIDER,
                        "requested_service_tier": OPENROUTER_STANDARD_FALLBACK_SERVICE_TIER,
                        "selected_provider": OPENROUTER_STANDARD_FALLBACK_SELECTED_PROVIDER,
                    }
                ]
                if openrouter_route_policy == "FLEX_THEN_STANDARD"
                else []
            ),
        ],
    }
    _write_or_verify(
        artifact_dir / "provider-routing-policy.json",
        canonical_json_bytes_v1(routing_policy),
    )
    if not database.exists():
        initialize_gemini_financial_page_store_v1(database)

    outcomes: dict[int, _PersistedPageOutcome] = {}
    circuit_breaker_trigger_page = None

    def extract(physical_page: int, *, force_offline: bool = False) -> _PageOutcome:
        return _extract_page(
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
            openrouter_route_policy=openrouter_route_policy,
            timeout_seconds=timeout_seconds,
            retries=retries,
            retry_delay_seconds=retry_delay_seconds,
            provider_call=provider_call,
            artifact_dir=artifact_dir,
            semantic_replay_source_dir=semantic_replay_source_dir,
            semantic_replay_expected_contract=contract,
            offline_replay_only=offline_replay_only or force_offline,
        )

    def persist(outcome: _PageOutcome) -> _PersistedPageOutcome:
        return _persist_page_outcome_v1(
            outcome=outcome,
            artifact_dir=artifact_dir,
            database=database,
            document=document,
            prompt_variant=prompt_variant,
            output_contract_mode=output_contract_mode,
            prompt_sha256=prompt_sha,
            response_schema_sha256=schema_sha,
        )

    if stop_provider_frontier_on_transient_error:
        provider_circuit_open = False
        for page_index, physical_page in enumerate(selected_pages):
            page_outcome = extract(physical_page, force_offline=provider_circuit_open)
            outcome = persist(page_outcome)
            outcomes[outcome.physical_page] = outcome
            if (
                not provider_circuit_open
                and page_outcome.provider_error is not None
                and _provider_error_opens_circuit_v1(page_outcome.provider_error)
            ):
                provider_circuit_open = True
                circuit_breaker_trigger_page = physical_page
            elif (
                outcome.provider_request_made
                and provider_request_delay_seconds > 0
                and page_index + 1 < len(selected_pages)
            ):
                time.sleep(provider_request_delay_seconds)
    else:
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="gemini-page") as executor:
            futures = {
                executor.submit(extract, physical_page): physical_page
                for physical_page in selected_pages
            }
            for future in as_completed(futures):
                outcome = persist(future.result())
                outcomes[outcome.physical_page] = outcome

    failed_pages: list[int] = []
    semantic_failed_pages: list[int] = []
    recitation_failed_pages: list[int] = []
    unresolved_pages: list[int] = []
    offline_missing_pages: list[int] = []
    cached_pages: list[int] = []
    ingested_pages: list[int] = []
    for physical_page in selected_pages:
        outcome = outcomes[physical_page]
        if outcome.disposition == "CACHED":
            cached_pages.append(physical_page)
        elif outcome.disposition == "CACHED_UNRESOLVED":
            failed_pages.append(physical_page)
            unresolved_pages.append(physical_page)
        elif outcome.disposition == "SEMANTIC_FAILED":
            failed_pages.append(physical_page)
            semantic_failed_pages.append(physical_page)
        elif outcome.disposition == "OFFLINE_MISSING":
            failed_pages.append(physical_page)
            offline_missing_pages.append(physical_page)
        elif outcome.disposition == "PROVIDER_FAILED":
            failed_pages.append(physical_page)
        elif outcome.disposition == "PROVIDER_RECITATION_FAILED":
            failed_pages.append(physical_page)
            recitation_failed_pages.append(physical_page)
        elif outcome.disposition == "INGESTED_UNRESOLVED":
            ingested_pages.append(physical_page)
            failed_pages.append(physical_page)
            unresolved_pages.append(physical_page)
        elif outcome.disposition == "INGESTED":
            ingested_pages.append(physical_page)
        else:
            raise AssertionError("persisted page outcome disposition is unknown")

    manifest = None
    if not failed_pages and physical_pages is None:
        mixed_openrouter_routes = openrouter_route_policy == "FLEX_THEN_STANDARD"
        if not mixed_openrouter_routes and google_standard_mode == "disabled":
            manifest_kwargs = {
                "requested_service_tier": OPENROUTER_SERVICE_TIER,
                "selected_provider": OPENROUTER_SELECTED_PROVIDER,
            }
        else:
            allowed_routes = [
                {
                    "gateway": "OPENROUTER",
                    "requested_service_tier": OPENROUTER_SERVICE_TIER,
                }
            ]
            preferred_routes = list(allowed_routes)
            if mixed_openrouter_routes:
                standard_openrouter_route = {
                    "gateway": "OPENROUTER",
                    "requested_service_tier": OPENROUTER_STANDARD_FALLBACK_SERVICE_TIER,
                }
                allowed_routes.append(standard_openrouter_route)
                preferred_routes.append(standard_openrouter_route)
            if google_standard_mode != "disabled":
                google_standard_route = {
                    "gateway": "GOOGLE_GEMINI_API",
                    "requested_service_tier": GOOGLE_STANDARD_SERVICE_TIER,
                }
                allowed_routes.append(google_standard_route)
                preferred_routes.append(google_standard_route)
            manifest_kwargs = {"allowed_gateway_service_tiers": allowed_routes}
            if mixed_openrouter_routes:
                manifest_kwargs["preferred_gateway_service_tiers"] = preferred_routes
        manifest = build_financial_document_manifest_v1(
            database,
            source_sha256=document["source_sha256"],
            source_logical_name=document["source_logical_name"],
            expected_physical_pages=range(1, page_count + 1),
            page_image_sha256s={
                page: outcomes[page].page["image_sha256"] for page in range(1, page_count + 1)
            },
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
        "execution_mode": contract["execution_mode"],
        "failed_pages": failed_pages,
        "ingested_pages": ingested_pages,
        "manifest_id": manifest["document_manifest_id"] if manifest is not None else None,
        "offline_missing_pages": offline_missing_pages,
        "page_count": len(selected_pages),
        "page_image_sha256s": [
            {
                "image_sha256": outcomes[page].page["image_sha256"],
                "physical_page": page,
            }
            for page in selected_pages
        ],
        "provider_request_pages": [
            page for page in selected_pages if outcomes[page].provider_request_made
        ],
        "provider_circuit_breaker_trigger_page": circuit_breaker_trigger_page,
        "recitation_failed_pages": recitation_failed_pages,
        "semantic_failed_pages": semantic_failed_pages,
        "semantic_replay_sources": [
            {
                "physical_page": page,
                "source_relative_path": outcomes[page].semantic_replay_source,
            }
            for page in selected_pages
            if outcomes[page].semantic_replay_source is not None
        ],
        "unresolved_pages": unresolved_pages,
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
        retries=_effective_provider_attempts_v1(
            args.retries,
            stop_on_transient=args.stop_provider_frontier_on_transient_error,
        ),
        retry_delay_seconds=args.retry_delay_seconds,
        physical_pages=args.physical_page,
        offline_replay_only=args.offline_replay_only,
        semantic_replay_source_dir=args.semantic_replay_source_dir,
        google_api_keys=google_keys,
        google_credential_slots=google_slots,
        google_standard_mode=args.google_standard_mode,
        openrouter_route_policy=args.openrouter_route_policy.replace("-", "_").upper(),
        stop_provider_frontier_on_transient_error=(args.stop_provider_frontier_on_transient_error),
        provider_request_delay_seconds=_effective_provider_request_delay_seconds_v1(
            args.provider_request_delay_seconds,
            stop_on_transient=args.stop_provider_frontier_on_transient_error,
        ),
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["disposition"] == "SUCCEEDED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
