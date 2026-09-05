#!/usr/bin/env python3
"""Process one disjoint 2025+ corpus PDF through CKey Gemini 3.7 Flash.

The runner atomically reserves one pending OpenRouter-planned document before
making any CKey request.  It uses the production page render, prompt and JSON
Schema, accepts only direct JSON or one otherwise-empty ``json`` Markdown
fence, and validates every decoded page before appending it to the shared
store.  Existing authenticated OpenRouter/Agy/CKey pages are always reused.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import ssl
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
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
from bctc_ai.evaluation.gemini_json_first_corpus_ledger_v1 import (  # noqa: E402
    CKEY_PROVIDER_JOB_PREFIX,
    claim_pending_openrouter_corpus_task_for_ckey_v1,
    corpus_ledger_summary_v1,
    list_corpus_tasks_v1,
    seal_ckey_corpus_task_v1,
    transition_corpus_task_v1,
    validate_gemini_json_first_corpus_plan_v1,
)
from bctc_ai.evaluation.gemini_json_first_page_render_v1 import (  # noqa: E402
    render_full_pdf_page_v1,
)
from bctc_ai.evaluation.gemini_json_first_provider_v1 import (  # noqa: E402
    CKEY_GATEWAY,
    CKEY_SERVICE_TIER,
    GOOGLE_BATCH_SERVICE_TIER,
    GOOGLE_MODEL,
    GOOGLE_STANDARD_SERVICE_TIER,
    OPENROUTER_SERVICE_TIER,
    OPENROUTER_STANDARD_FALLBACK_SERVICE_TIER,
    ProviderResultV1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    GeminiFinancialPageStoreV1Error,
    build_financial_document_manifest_v1,
    ingest_financial_page_extraction_v1,
)

FORMAT_VERSION = "GEMINI_JSON_FIRST_CKEY_DOCUMENT_RUNNER_V1"
CKEY_SELECTED_PROVIDER = "CKEY"
CKEY_API_URL = "https://api.xah.io/v1/chat/completions"
CKEY_DEFAULT_MODELS: tuple[str, ...] = ()
CKEY_DEFAULT_KEY_FILE = Path("/root/.config/bctc-ai/ckey-api-key")
CKEY_DEFAULT_VND_PER_USD = Decimal("26000")
CKEY_DEFAULT_PAGE_COST_CAP_VND = Decimal("50")
_FENCE = re.compile(r"\A\s*```(?:json)?\s*\n(?P<body>[\s\S]*?)\n```\s*\Z", re.IGNORECASE)


class RunGeminiJsonFirstCkeyDocumentV1Error(RuntimeError):
    pass


class _CKeyHttpError(RunGeminiJsonFirstCkeyDocumentV1Error):
    def __init__(self, status: int, body: bytes) -> None:
        super().__init__(f"CKey returned HTTP {status}")
        self.status = status
        self.body = body


@dataclass(frozen=True)
class _RenderedPage:
    image: bytes
    page: dict[str, Any]
    receipt: dict[str, Any]


@dataclass(frozen=True)
class _PageResult:
    physical_page: int
    disposition: str
    page: dict[str, Any]
    failure_kind: str | None = None
    cost_vnd: str | None = None


def _error(message: str) -> RunGeminiJsonFirstCkeyDocumentV1Error:
    return RunGeminiJsonFirstCkeyDocumentV1Error(message)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--task-id")
    parser.add_argument("--ckey-key-file", type=Path, default=CKEY_DEFAULT_KEY_FILE)
    parser.add_argument(
        "--model",
        action="append",
        help=(
            "Required paid CKey Gemini 3.7 Flash provider model; repeat to define the "
            "ordered pool. Free routes are rejected."
        ),
    )
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--page-attempts", type=int, default=2)
    parser.add_argument("--retry-delay-seconds", type=float, default=5.0)
    parser.add_argument("--vnd-per-usd", type=Decimal, default=CKEY_DEFAULT_VND_PER_USD)
    parser.add_argument("--page-cost-cap-vnd", type=Decimal, default=CKEY_DEFAULT_PAGE_COST_CAP_VND)
    return parser


def _json_file(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise _error(f"required JSON file is absent: {path}")
    try:
        value = json.loads(path.read_bytes())
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise _error(f"required JSON file is invalid: {path}") from exc
    if type(value) is not dict:
        raise _error(f"required JSON file is not one object: {path}")
    return value


def _write_or_verify(path: Path, payload: bytes) -> None:
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
            raise _error(f"immutable CKey artifact drifted: {path}")
        return
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
    finally:
        stage.unlink(missing_ok=True)


def _read_key(path: Path) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
        raise _error("CKey API key file is absent, linked, or not private")
    key = path.read_text(encoding="utf-8").strip()
    if not key.startswith("sk-") or len(key) < 16 or any(character.isspace() for character in key):
        raise _error("CKey API key is invalid")
    return key


def _report_year(relative_path: str) -> int:
    years = [int(part) for part in Path(relative_path).parts if part.isdigit() and len(part) == 4]
    if len(years) != 1:
        raise _error("CKey source path has no unique report year")
    year = years[0]
    if not 2025 <= year <= datetime.now(UTC).year:
        raise _error("CKey source lies outside the locked 2025-current scope")
    return year


def _source(task: dict[str, Any], source_root: Path) -> Path:
    _report_year(task["relative_path"])
    root = source_root.resolve()
    path = (root / task["relative_path"]).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise _error("CKey source path escapes its source root") from exc
    if path.is_symlink() or not path.is_file():
        raise _error("CKey source PDF is absent or not regular")
    source = path.read_bytes()
    if (
        sha256(source).hexdigest() != task["source_sha256"]
        or len(source) != task["source_size_bytes"]
    ):
        raise _error("CKey source PDF identity drifted")
    with fitz.open(stream=source, filetype="pdf") as document:
        if document.page_count < task["last_physical_page"]:
            raise _error("CKey source PDF page frontier drifted")
    return path


def _routes() -> list[dict[str, str]]:
    return [
        {"gateway": "AGY_CLI", "requested_service_tier": tier}
        for tier in ("agy-low", "agy-medium", "agy-high")
    ] + [
        {"gateway": CKEY_GATEWAY, "requested_service_tier": CKEY_SERVICE_TIER},
        {"gateway": "GOOGLE_GEMINI_API", "requested_service_tier": GOOGLE_STANDARD_SERVICE_TIER},
        {"gateway": "GOOGLE_GEMINI_BATCH_API", "requested_service_tier": GOOGLE_BATCH_SERVICE_TIER},
        {"gateway": "OPENROUTER", "requested_service_tier": OPENROUTER_SERVICE_TIER},
        {
            "gateway": "OPENROUTER",
            "requested_service_tier": OPENROUTER_STANDARD_FALLBACK_SERVICE_TIER,
        },
    ]


def _preferred_routes() -> list[dict[str, str]]:
    allowed = _routes()
    keys = {(route["gateway"], route["requested_service_tier"]): route for route in allowed}
    order = [
        ("OPENROUTER", OPENROUTER_SERVICE_TIER),
        ("AGY_CLI", "agy-low"),
        ("AGY_CLI", "agy-medium"),
        ("AGY_CLI", "agy-high"),
        (CKEY_GATEWAY, CKEY_SERVICE_TIER),
        ("OPENROUTER", OPENROUTER_STANDARD_FALLBACK_SERVICE_TIER),
        ("GOOGLE_GEMINI_BATCH_API", GOOGLE_BATCH_SERVICE_TIER),
        ("GOOGLE_GEMINI_API", GOOGLE_STANDARD_SERVICE_TIER),
    ]
    return [keys[key] for key in order]


def _render_page(pdf: Path, *, physical_page: int, dpi: int, source_sha256: str) -> _RenderedPage:
    with fitz.open(pdf) as document:
        rendered = render_full_pdf_page_v1(
            document[physical_page - 1],
            physical_page=physical_page,
            dpi=dpi,
            source_sha256=source_sha256,
        )
    return _RenderedPage(rendered.image, rendered.page, rendered.receipt)


def _page_manifest(
    database: Path,
    *,
    task: dict[str, Any],
    rendered: _RenderedPage,
    prompt_sha256: str,
    response_schema_sha256: str,
) -> dict[str, Any] | None:
    try:
        return build_financial_document_manifest_v1(
            database,
            source_sha256=task["source_sha256"],
            source_logical_name=task["relative_path"],
            expected_physical_pages=[rendered.page["physical_page"]],
            page_image_sha256s={rendered.page["physical_page"]: rendered.page["image_sha256"]},
            prompt_sha256=prompt_sha256,
            response_schema_sha256=response_schema_sha256,
            requested_model=GOOGLE_MODEL,
            allowed_gateway_service_tiers=_routes(),
            preferred_gateway_service_tiers=_preferred_routes(),
        )
    except GeminiFinancialPageStoreV1Error as exc:
        if str(exc) in {
            "document manifest page frontier is incomplete",
            "document manifest source is not unique in the store",
        }:
            return None
        raise


def _decode_ckey_content(content: str) -> dict[str, Any]:
    if type(content) is not str or not content.strip():
        raise _error("CKey response content is empty")
    try:
        return decode_financial_page_json_text_v1(content)
    except Exception as direct_error:
        match = _FENCE.fullmatch(content)
        if match is None or "```" in match.group("body"):
            raise _error(
                "CKey response is neither direct JSON nor one bounded JSON fence"
            ) from direct_error
        try:
            return decode_financial_page_json_text_v1(match.group("body"))
        except Exception as exc:
            raise _error("CKey fenced response violates the financial-page schema") from exc


def _checked_nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise _error(f"CKey {label} token count is invalid")
    return value


def _ckey_cost_vnd(raw: bytes) -> Decimal:
    try:
        envelope = json.loads(raw)
        cost = envelope["usage"]["x_ckey"]["cost"]
        value = Decimal(str(cost))
    except (KeyError, TypeError, json.JSONDecodeError, UnicodeDecodeError, InvalidOperation) as exc:
        raise _error("CKey billed VND cost is invalid") from exc
    if not value.is_finite() or value < 0:
        raise _error("CKey billed VND cost is invalid")
    return value


def _checked_ckey_response(
    raw: bytes, *, vnd_per_usd: Decimal
) -> tuple[dict[str, Any], dict[str, Any], str, str]:
    try:
        envelope = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise _error("CKey response is not one JSON envelope") from exc
    choices = envelope.get("choices") if type(envelope) is dict else None
    usage = envelope.get("usage") if type(envelope) is dict else None
    response_id = envelope.get("id") if type(envelope) is dict else None
    model = envelope.get("model") if type(envelope) is dict else None
    if (
        type(choices) is not list
        or len(choices) != 1
        or type(choices[0]) is not dict
        or choices[0].get("finish_reason") != "stop"
        or type(choices[0].get("message")) is not dict
        or type(usage) is not dict
        or type(response_id) is not str
        or not response_id
        or type(model) is not str
        or not model
    ):
        raise _error("CKey response envelope is incomplete or nonterminal")
    page_json = _decode_ckey_content(choices[0]["message"].get("content"))
    input_tokens = _checked_nonnegative_int(usage.get("prompt_tokens"), "input")
    output_tokens = _checked_nonnegative_int(usage.get("completion_tokens"), "output")
    total_tokens = _checked_nonnegative_int(usage.get("total_tokens"), "total")
    if total_tokens != input_tokens + output_tokens:
        raise _error("CKey token equation does not close")
    ckey = usage.get("x_ckey")
    if type(ckey) is not dict or type(ckey.get("request_id")) is not str:
        raise _error("CKey billing receipt is absent")
    cost_vnd = _ckey_cost_vnd(raw)
    if not cost_vnd.is_finite() or cost_vnd < 0 or vnd_per_usd <= 0:
        raise _error("CKey billed cost or conversion rate is invalid")
    normalized = {
        "actual_cost_usd": format(cost_vnd / vnd_per_usd, ".12f"),
        "actual_cost_vnd": format(cost_vnd, "f"),
        "billing_disposition": "BILLED_ACTUAL_VND_WITH_CONFIGURED_USD_CONVERSION",
        "cached_input_tokens": 0,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "thought_tokens": 0,
        "total_tokens": total_tokens,
        "vnd_per_usd": format(vnd_per_usd, "f"),
    }
    return page_json, normalized, response_id, model


def _call_ckey(
    *,
    api_key: str,
    model: str,
    image: bytes,
    prompt: str,
    response_schema: dict[str, Any],
    timeout_seconds: int,
    max_tokens: int,
) -> tuple[bytes, float]:
    body = {
        "max_tokens": max_tokens,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/png;base64,"
                            + base64.b64encode(image).decode("ascii")
                        },
                    },
                ],
            }
        ],
        "model": model,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "financial_page_json_v1",
                "schema": response_schema,
                "strict": True,
            },
        },
        "stream": False,
        "temperature": 0,
    }
    request = urllib.request.Request(
        CKEY_API_URL,
        data=canonical_json_bytes_v1(body),
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(
            request, timeout=timeout_seconds, context=ssl.create_default_context()
        ) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raise _CKeyHttpError(exc.code, exc.read()) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise _error("CKey connection failed") from exc
    return raw, time.monotonic() - started


def _model_max_tokens(model: str) -> int:
    """Cap metered backup providers below the empirical Flex cost floor."""

    return 10_000


def _checked_paid_model_pool_v1(values: Sequence[str] | None) -> tuple[str, ...]:
    models = tuple(values or CKEY_DEFAULT_MODELS)
    if (
        len(models) != len(set(models))
        or not models
        or any("gemini" not in model.lower() or "3.7" not in model for model in models)
        or any("free" in model.lower() for model in models)
    ):
        raise _error("CKey model pool must contain unique paid Gemini 3.7 routes")
    return models


def _ingest_with_lock_retry(database: Path, **kwargs: Any) -> dict[str, str]:
    for attempt in range(1, 21):
        try:
            return ingest_financial_page_extraction_v1(database, **kwargs)
        except Exception as exc:
            if "database is locked" not in str(exc).lower() or attempt == 20:
                raise
            time.sleep(min(0.05 * attempt, 0.5))
    raise AssertionError("unreachable SQLite retry frontier")


def _process_page(
    *,
    task: dict[str, Any],
    source: Path,
    database: Path,
    artifact_root: Path,
    api_key: str,
    models: tuple[str, ...],
    dpi: int,
    prompt: str,
    prompt_sha256: str,
    schema: dict[str, Any],
    response_schema_sha256: str,
    timeout_seconds: int,
    page_attempts: int,
    retry_delay_seconds: float,
    vnd_per_usd: Decimal,
    page_cost_cap_vnd: Decimal,
    circuit_open: threading.Event,
    physical_page: int,
) -> _PageResult:
    rendered = _render_page(
        source, physical_page=physical_page, dpi=dpi, source_sha256=task["source_sha256"]
    )
    page_root = artifact_root / f"page-{physical_page:05d}"
    _write_or_verify(page_root / "render-receipt.json", canonical_json_bytes_v1(rendered.receipt))
    existing = _page_manifest(
        database,
        task=task,
        rendered=rendered,
        prompt_sha256=prompt_sha256,
        response_schema_sha256=response_schema_sha256,
    )
    if existing is not None:
        return _PageResult(physical_page, "REUSED", rendered.page)
    if circuit_open.is_set():
        return _PageResult(physical_page, "FAILED", rendered.page, "CKEY_CIRCUIT_OPEN")
    last_failure = "CKEY_PROVIDER_OR_SCHEMA_FAILED"
    billed_cost_vnd = Decimal(0)
    for ordinal in range(1, page_attempts + 1):
        model = models[(ordinal - 1) % len(models)]
        attempt_root = page_root / f"attempt-{ordinal:02d}"
        invocation = {
            "format_version": FORMAT_VERSION,
            "image_sha256": rendered.page["image_sha256"],
            "model": model,
            "prompt_sha256": prompt_sha256,
            "response_schema_sha256": response_schema_sha256,
        }
        _write_or_verify(attempt_root / "invocation.json", canonical_json_bytes_v1(invocation))
        try:
            raw, elapsed = _call_ckey(
                api_key=api_key,
                model=model,
                image=rendered.image,
                prompt=prompt,
                response_schema=schema,
                timeout_seconds=timeout_seconds,
                max_tokens=_model_max_tokens(model),
            )
            _write_or_verify(attempt_root / "ckey-response.json", raw)
            billed_cost_vnd += _ckey_cost_vnd(raw)
            if billed_cost_vnd >= page_cost_cap_vnd:
                circuit_open.set()
                last_failure = "CKEY_PAGE_COST_CAP_REACHED"
                raise _error("CKey page cost reached the strict cheaper-than-Flex cap")
            page_json, usage, response_id, selected_model = _checked_ckey_response(
                raw, vnd_per_usd=vnd_per_usd
            )
        except Exception as exc:
            status = exc.status if isinstance(exc, _CKeyHttpError) else None
            raw_error = exc.body if isinstance(exc, _CKeyHttpError) else b""
            if raw_error:
                _write_or_verify(attempt_root / "ckey-error-response.json", raw_error)
            _write_or_verify(
                attempt_root / "failure.json",
                canonical_json_bytes_v1(
                    {
                        "error_message": str(exc),
                        "error_type": type(exc).__name__,
                        "failure_kind": last_failure,
                        "http_status": status,
                    }
                ),
            )
            if status == 401 or circuit_open.is_set():
                circuit_open.set()
                last_failure = "CKEY_PROVIDER_CIRCUIT_OPEN"
                break
            if status in {402, 403, 429, 500, 502, 503, 504} and ordinal == page_attempts:
                circuit_open.set()
                last_failure = "CKEY_PROVIDER_CIRCUIT_OPEN"
                break
            if ordinal < page_attempts:
                time.sleep(retry_delay_seconds)
            continue
        page_bytes = canonical_json_bytes_v1(page_json)
        _write_or_verify(attempt_root / "page.json", page_bytes)
        _write_or_verify(
            attempt_root / "observation.json",
            canonical_json_bytes_v1(
                {
                    "content_counts": count_financial_page_content_v1(page_json),
                    "page_json_sha256": sha256(page_bytes).hexdigest(),
                    "status": page_json["status"],
                    "usage": usage,
                }
            ),
        )
        if page_json["status"] == "UNRESOLVED_PAGE":
            last_failure = "CKEY_UNRESOLVED_PAGE"
            if ordinal < page_attempts:
                time.sleep(retry_delay_seconds)
            continue
        attempt = {
            "attempt_ordinal": ordinal,
            "credential_slot": "CKEY_AUTHENTICATED_KEY",
            "elapsed_seconds": format(elapsed, ".6f"),
            "http_status": 200,
            "outcome": "COMPLETED",
            "provider": CKEY_GATEWAY,
            "usage": usage,
        }
        provider_result = ProviderResultV1(
            output_text=canonical_json_bytes_v1(page_json).decode("utf-8"),
            raw_response_bytes=raw,
            provider_name=CKEY_SELECTED_PROVIDER,
            provider_model=selected_model,
            service_tier=CKEY_SERVICE_TIER,
            attempts=(attempt,),
            usage=usage,
            response_id_sha256=sha256(response_id.encode("utf-8")).hexdigest(),
        )
        identities = _ingest_with_lock_retry(
            database,
            document={
                "source_logical_name": task["relative_path"],
                "source_sha256": task["source_sha256"],
                "source_size_bytes": task["source_size_bytes"],
            },
            page=rendered.page,
            prompt_variant="simple",
            output_contract_mode="JSON_SCHEMA",
            prompt_sha256=prompt_sha256,
            response_schema_sha256=response_schema_sha256,
            requested_model=GOOGLE_MODEL,
            requested_service_tier=CKEY_SERVICE_TIER,
            thinking_level="low",
            provider_result=provider_result,
            page_json=page_json,
        )
        _write_or_verify(attempt_root / "ingestion.json", canonical_json_bytes_v1(identities))
        return _PageResult(
            physical_page,
            "INGESTED",
            rendered.page,
            cost_vnd=format(billed_cost_vnd, "f"),
        )
    return _PageResult(
        physical_page,
        "FAILED",
        rendered.page,
        last_failure,
        cost_vnd=format(billed_cost_vnd, "f"),
    )


def run_ckey_document_v1(args: argparse.Namespace) -> dict[str, Any]:
    if not 1 <= args.workers <= 10:
        raise _error("CKey worker bound lies outside 1..10")
    if not 30 <= args.timeout_seconds <= 1_800:
        raise _error("CKey timeout lies outside 30..1800 seconds")
    if not 1 <= args.page_attempts <= 3 or not 0 <= args.retry_delay_seconds <= 60:
        raise _error("CKey page retry policy is invalid")
    models = _checked_paid_model_pool_v1(args.model)
    if (
        not args.page_cost_cap_vnd.is_finite()
        or not Decimal("0") < args.page_cost_cap_vnd <= Decimal("50")
    ):
        raise _error("CKey cheaper-than-Flex cost cap is invalid")
    api_key = _read_key(args.ckey_key_file)
    plan = validate_gemini_json_first_corpus_plan_v1(_json_file(args.plan))
    summary = corpus_ledger_summary_v1(args.ledger)
    if plan["corpus_plan_id"] != summary["corpus_plan_id"]:
        raise _error("CKey plan and corpus ledger disagree")
    if args.task_id is None:
        task = claim_pending_openrouter_corpus_task_for_ckey_v1(args.ledger)
    else:
        matches = [
            task for task in list_corpus_tasks_v1(args.ledger) if task["task_id"] == args.task_id
        ]
        if len(matches) != 1:
            raise _error("CKey task ID is absent from the corpus ledger")
        task = matches[0]
        if task["state"] == "PENDING":
            task = claim_pending_openrouter_corpus_task_for_ckey_v1(
                args.ledger, task_id=args.task_id
            )
        elif not (
            task["state"] == "SUBMITTED"
            and type(task["provider_job_ref"]) is str
            and task["provider_job_ref"].startswith(CKEY_PROVIDER_JOB_PREFIX)
        ):
            raise _error("CKey task is not pending or reserved by CKey")
    source = _source(task, args.source_root)
    prompt = build_financial_page_json_prompt_v1(variant="simple")
    schema = financial_page_json_response_schema_v1()
    prompt_sha256 = sha256(prompt.encode("utf-8")).hexdigest()
    response_schema_sha256 = canonical_json_sha256_v1(schema)
    task_root = args.artifact_root / task["artifact_relative_path"] / "ckey"
    _write_or_verify(task_root / "prompt.txt", prompt.encode("utf-8"))
    _write_or_verify(task_root / "response-schema.json", canonical_json_bytes_v1(schema))
    expected_pages = list(range(task["first_physical_page"], task["last_physical_page"] + 1))
    circuit_open = threading.Event()
    outcomes: list[_PageResult] = []
    with ThreadPoolExecutor(max_workers=args.workers, thread_name_prefix="ckey-page") as executor:
        futures = {
            executor.submit(
                _process_page,
                task=task,
                source=source,
                database=args.database,
                artifact_root=task_root,
                api_key=api_key,
                models=models,
                dpi=plan["policy"]["dpi"],
                prompt=prompt,
                prompt_sha256=prompt_sha256,
                schema=schema,
                response_schema_sha256=response_schema_sha256,
                timeout_seconds=args.timeout_seconds,
                page_attempts=args.page_attempts,
                retry_delay_seconds=args.retry_delay_seconds,
                vnd_per_usd=args.vnd_per_usd,
                page_cost_cap_vnd=args.page_cost_cap_vnd,
                circuit_open=circuit_open,
                physical_page=page,
            ): page
            for page in expected_pages
        }
        for future in as_completed(futures):
            outcomes.append(future.result())
    outcomes.sort(key=lambda item: item.physical_page)
    failed = [item for item in outcomes if item.disposition == "FAILED"]
    result = {
        "billed_cost_vnd": format(
            sum(
                (Decimal(item.cost_vnd) for item in outcomes if item.cost_vnd is not None),
                Decimal(0),
            ),
            "f",
        ),
        "circuit_open": circuit_open.is_set(),
        "failed_pages": [item.physical_page for item in failed],
        "format_version": FORMAT_VERSION,
        "ingested_pages": [
            item.physical_page for item in outcomes if item.disposition == "INGESTED"
        ],
        "models": list(models),
        "provider_job_ref": task["provider_job_ref"],
        "reused_pages": [item.physical_page for item in outcomes if item.disposition == "REUSED"],
        "task_id": task["task_id"],
    }
    if failed:
        unresolved = [
            item.physical_page for item in failed if item.failure_kind == "CKEY_UNRESOLVED_PAGE"
        ]
        receipt = {
            **result,
            "recitation_failed_pages": [],
            "semantic_failed_pages": unresolved,
            "unresolved_pages": unresolved,
        }
        transition_corpus_task_v1(
            args.ledger,
            task_id=task["task_id"],
            expected_state="SUBMITTED",
            next_state="NEEDS_RETRY",
            receipt=receipt,
            provider_job_ref=task["provider_job_ref"],
        )
        _write_or_verify(task_root / "ckey-run-result.json", canonical_json_bytes_v1(receipt))
        return {**receipt, "disposition": "NEEDS_VERTEX_FLEX_RETRY"}
    manifest = build_financial_document_manifest_v1(
        args.database,
        source_sha256=task["source_sha256"],
        source_logical_name=task["relative_path"],
        expected_physical_pages=expected_pages,
        page_image_sha256s={item.physical_page: item.page["image_sha256"] for item in outcomes},
        prompt_sha256=prompt_sha256,
        response_schema_sha256=response_schema_sha256,
        requested_model=GOOGLE_MODEL,
        allowed_gateway_service_tiers=_routes(),
        preferred_gateway_service_tiers=_preferred_routes(),
    )
    seal_ckey_corpus_task_v1(
        args.ledger,
        task_id=task["task_id"],
        provider_job_ref=task["provider_job_ref"],
        document_manifest=manifest,
    )
    complete = {
        **result,
        "disposition": "SUCCEEDED",
        "document_manifest_id": manifest["document_manifest_id"],
    }
    _write_or_verify(task_root / "ckey-document-manifest.json", canonical_json_bytes_v1(manifest))
    _write_or_verify(task_root / "ckey-run-result.json", canonical_json_bytes_v1(complete))
    return complete


def main() -> int:
    try:
        result = run_ckey_document_v1(_parser().parse_args())
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if result["disposition"] == "SUCCEEDED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
