#!/usr/bin/env python3
"""Process one disjoint corpus document through Agy Gemini 3.7 Flash.

The worker reserves an OpenRouter-planned task as ``SUBMITTED`` before doing
any work, so the ordinary Vertex Flex supervisor cannot send the same PDF.  It
uses the exact production render, prompt and JSON Schema.  Each missing page is
attempted at low effort first, then medium and high only when the prior result
is unusable.  Existing authenticated page JSON is always reused.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
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
from bctc_ai.evaluation.gemini_json_first_corpus_ledger_v1 import (  # noqa: E402
    AGY_PROVIDER_JOB_PREFIX,
    claim_pending_openrouter_corpus_task_for_agy_v1,
    corpus_ledger_summary_v1,
    list_corpus_tasks_v1,
    seal_agy_corpus_task_v1,
    transition_corpus_task_v1,
    validate_gemini_json_first_corpus_plan_v1,
)
from bctc_ai.evaluation.gemini_json_first_page_render_v1 import (  # noqa: E402
    render_full_pdf_page_v1,
)
from bctc_ai.evaluation.gemini_json_first_provider_v1 import (  # noqa: E402
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

FORMAT_VERSION = "GEMINI_JSON_FIRST_AGY_DOCUMENT_RUNNER_V1"
AGY_GATEWAY = "AGY_CLI"
AGY_SELECTED_PROVIDER = "Agy"
AGY_BINARY_DEFAULT = Path("/root/.local/bin/agy")
EFFORT_ORDER = ("low", "medium", "high")
AGY_MODEL_BY_EFFORT = {effort: f"gemini-3.7-flash-{effort}" for effort in EFFORT_ORDER}


class RunGeminiJsonFirstAgyDocumentV1Error(RuntimeError):
    pass


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
    effort: str | None = None
    failure_kind: str | None = None


def _error(message: str) -> RunGeminiJsonFirstAgyDocumentV1Error:
    return RunGeminiJsonFirstAgyDocumentV1Error(message)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--task-id")
    parser.add_argument("--agy-binary", type=Path, default=AGY_BINARY_DEFAULT)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--timeout-seconds", type=int, default=600)
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
            raise _error(f"immutable Agy artifact drifted: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _source(task: dict[str, Any], source_root: Path) -> Path:
    root = source_root.resolve()
    path = (root / task["relative_path"]).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise _error("Agy source path escapes its source root") from exc
    if path.is_symlink() or not path.is_file():
        raise _error("Agy source PDF is absent or not regular")
    source = path.read_bytes()
    if (
        sha256(source).hexdigest() != task["source_sha256"]
        or len(source) != task["source_size_bytes"]
    ):
        raise _error("Agy source PDF identity drifted")
    with fitz.open(stream=source, filetype="pdf") as document:
        if document.page_count < task["last_physical_page"]:
            raise _error("Agy source PDF page frontier drifted")
    return path


def _routes() -> list[dict[str, str]]:
    return [
        {"gateway": AGY_GATEWAY, "requested_service_tier": f"agy-{effort}"}
        for effort in EFFORT_ORDER
    ] + [
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
        (AGY_GATEWAY, "agy-low"),
        (AGY_GATEWAY, "agy-medium"),
        (AGY_GATEWAY, "agy-high"),
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


def _checked_agy_envelope(raw: bytes) -> tuple[dict[str, Any], dict[str, int], str]:
    try:
        envelope = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise _error("Agy output is not one JSON envelope") from exc
    if type(envelope) is not dict or envelope.get("status") != "SUCCESS":
        raise _error("Agy did not return a successful envelope")
    structured = envelope.get("structured_output")
    usage = envelope.get("usage")
    conversation_id = envelope.get("conversation_id")
    if (
        type(structured) is not dict
        or type(usage) is not dict
        or type(conversation_id) is not str
        or not conversation_id
    ):
        raise _error("Agy successful envelope lacks structured output or usage")
    required_usage = {
        "input_tokens",
        "output_tokens",
        "thinking_tokens",
        "cache_read_tokens",
        "total_tokens",
    }
    normalized = {key: usage.get(key) for key in required_usage}
    if any(type(value) is not int or value < 0 for value in normalized.values()):
        raise _error("Agy usage is invalid")
    page_json = decode_financial_page_json_text_v1(
        json.dumps(structured, ensure_ascii=False, separators=(",", ":"))
    )
    return page_json, normalized, conversation_id


def _call_agy(
    *,
    agy_binary: Path,
    effort: str,
    image: bytes,
    prompt: str,
    schema_path: Path,
    timeout_seconds: int,
) -> tuple[bytes, bytes, float]:
    if effort not in EFFORT_ORDER:
        raise _error("Agy effort is invalid")
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="gemini-json-first-agy-") as temporary:
        image_path = Path(temporary) / "page.png"
        image_path.write_bytes(image)
        transport_prompt = prompt.rstrip() + "\nẢnh đầu vào duy nhất: @" + str(image_path)
        result = subprocess.run(
            [
                str(agy_binary),
                "--model",
                AGY_MODEL_BY_EFFORT[effort],
                "--effort",
                effort,
                "--json-schema",
                str(schema_path),
                "--output-format",
                "json",
                "--sandbox",
                "--disable-slash-commands",
                "--add-dir",
                temporary,
                "--print-timeout",
                f"{timeout_seconds}s",
                "--print",
                transport_prompt,
            ],
            cwd=ROOT,
            capture_output=True,
            timeout=timeout_seconds + 30,
            check=False,
        )
    elapsed = time.monotonic() - started
    if result.returncode != 0:
        raise _error("Agy subprocess failed with return code " + str(result.returncode))
    return result.stdout, result.stderr, elapsed


def _provider_result(
    *,
    raw: bytes,
    page_json: dict[str, Any],
    usage: dict[str, int],
    conversation_id: str,
    effort: str,
    elapsed: float,
) -> ProviderResultV1:
    normalized_usage = {
        "actual_cost_usd": "0.000000000000",
        "billing_disposition": "AGY_LOCAL_SUBSCRIPTION_NO_INCREMENTAL_API_CHARGE",
        "cached_input_tokens": usage["cache_read_tokens"],
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "thought_tokens": usage["thinking_tokens"],
        "total_tokens": usage["total_tokens"],
    }
    attempt = {
        "attempt_ordinal": 1,
        "credential_slot": "AGY_AUTHENTICATED_LOCAL_SESSION",
        "elapsed_seconds": format(elapsed, ".6f"),
        "http_status": None,
        "outcome": "COMPLETED",
        "provider": AGY_GATEWAY,
        "usage": normalized_usage,
    }
    return ProviderResultV1(
        output_text=canonical_json_bytes_v1(page_json).decode("utf-8"),
        raw_response_bytes=raw,
        provider_name=AGY_SELECTED_PROVIDER,
        provider_model=AGY_MODEL_BY_EFFORT[effort],
        service_tier=f"agy-{effort}",
        attempts=(attempt,),
        usage=normalized_usage,
        response_id_sha256=sha256(conversation_id.encode("utf-8")).hexdigest(),
    )


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
    agy_binary: Path,
    dpi: int,
    prompt: str,
    prompt_sha256: str,
    schema_path: Path,
    response_schema_sha256: str,
    timeout_seconds: int,
    physical_page: int,
) -> _PageResult:
    rendered = _render_page(
        source,
        physical_page=physical_page,
        dpi=dpi,
        source_sha256=task["source_sha256"],
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

    last_failure_kind = "AGY_PROVIDER_FAILED"
    for effort in EFFORT_ORDER:
        attempt_root = page_root / f"effort-{effort}"
        invocation = {
            "base_prompt_sha256": prompt_sha256,
            "effort": effort,
            "format_version": FORMAT_VERSION,
            "image_sha256": rendered.page["image_sha256"],
            "model": AGY_MODEL_BY_EFFORT[effort],
            "response_schema_sha256": response_schema_sha256,
        }
        _write_or_verify(attempt_root / "invocation.json", canonical_json_bytes_v1(invocation))
        raw_path = attempt_root / "agy-response.json"
        stderr_path = attempt_root / "agy-stderr.log"
        elapsed_path = attempt_root / "elapsed-seconds.txt"
        try:
            if raw_path.exists():
                raw = raw_path.read_bytes()
                stderr = stderr_path.read_bytes()
                elapsed = float(elapsed_path.read_text(encoding="utf-8").strip())
            else:
                raw, stderr, elapsed = _call_agy(
                    agy_binary=agy_binary,
                    effort=effort,
                    image=rendered.image,
                    prompt=prompt,
                    schema_path=schema_path,
                    timeout_seconds=timeout_seconds,
                )
                _write_or_verify(raw_path, raw)
                _write_or_verify(stderr_path, stderr)
                _write_or_verify(elapsed_path, (format(elapsed, ".6f") + "\n").encode("utf-8"))
            page_json, usage, conversation_id = _checked_agy_envelope(raw)
        except Exception as exc:
            last_failure_kind = "AGY_PROVIDER_OR_SCHEMA_FAILED"
            _write_or_verify(
                attempt_root / "failure.json",
                canonical_json_bytes_v1(
                    {
                        "error_message": str(exc),
                        "error_type": type(exc).__name__,
                        "failure_kind": last_failure_kind,
                    }
                ),
            )
            continue
        page_bytes = canonical_json_bytes_v1(page_json)
        _write_or_verify(attempt_root / "page.json", page_bytes)
        _write_or_verify(
            attempt_root / "observation.json",
            canonical_json_bytes_v1(
                {
                    "content_counts": count_financial_page_content_v1(page_json),
                    "effort": effort,
                    "page_json_sha256": sha256(page_bytes).hexdigest(),
                    "status": page_json["status"],
                    "usage": usage,
                }
            ),
        )
        if page_json["status"] == "UNRESOLVED_PAGE":
            last_failure_kind = "AGY_UNRESOLVED_PAGE"
            continue
        provider_result = _provider_result(
            raw=raw,
            page_json=page_json,
            usage=usage,
            conversation_id=conversation_id,
            effort=effort,
            elapsed=elapsed,
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
            requested_service_tier=f"agy-{effort}",
            thinking_level=effort,
            provider_result=provider_result,
            page_json=page_json,
        )
        _write_or_verify(attempt_root / "ingestion.json", canonical_json_bytes_v1(identities))
        return _PageResult(physical_page, "INGESTED", rendered.page, effort=effort)
    return _PageResult(
        physical_page,
        "FAILED",
        rendered.page,
        effort="high",
        failure_kind=last_failure_kind,
    )


def run_agy_document_v1(args: argparse.Namespace) -> dict[str, Any]:
    if not 1 <= args.workers <= 20:
        raise _error("Agy worker bound lies outside 1..20")
    if not 30 <= args.timeout_seconds <= 1_800:
        raise _error("Agy timeout lies outside 30..1800 seconds")
    if args.agy_binary.is_symlink() or not args.agy_binary.is_file():
        raise _error("Agy binary is absent or not regular")
    plan = validate_gemini_json_first_corpus_plan_v1(_json_file(args.plan))
    summary = corpus_ledger_summary_v1(args.ledger)
    if plan["corpus_plan_id"] != summary["corpus_plan_id"]:
        raise _error("Agy plan and corpus ledger disagree")
    if args.task_id is None:
        task = claim_pending_openrouter_corpus_task_for_agy_v1(args.ledger)
    else:
        matches = [
            task for task in list_corpus_tasks_v1(args.ledger) if task["task_id"] == args.task_id
        ]
        if len(matches) != 1:
            raise _error("Agy task ID is absent from the corpus ledger")
        task = matches[0]
        if task["state"] == "PENDING":
            task = claim_pending_openrouter_corpus_task_for_agy_v1(
                args.ledger, task_id=args.task_id
            )
        elif not (
            task["state"] == "SUBMITTED"
            and type(task["provider_job_ref"]) is str
            and task["provider_job_ref"].startswith(AGY_PROVIDER_JOB_PREFIX)
        ):
            raise _error("Agy task is not pending or reserved by Agy")
    source = _source(task, args.source_root)
    dpi = plan["policy"]["dpi"]
    prompt = build_financial_page_json_prompt_v1(variant="simple")
    prompt_bytes = prompt.encode("utf-8")
    schema = financial_page_json_response_schema_v1()
    schema_bytes = canonical_json_bytes_v1(schema)
    prompt_sha256 = sha256(prompt_bytes).hexdigest()
    response_schema_sha256 = canonical_json_sha256_v1(schema)
    task_root = args.artifact_root / task["artifact_relative_path"] / "agy"
    _write_or_verify(task_root / "prompt.txt", prompt_bytes)
    _write_or_verify(task_root / "response-schema.json", schema_bytes)
    expected_pages = list(range(task["first_physical_page"], task["last_physical_page"] + 1))
    outcomes: list[_PageResult] = []
    with ThreadPoolExecutor(max_workers=args.workers, thread_name_prefix="agy-page") as executor:
        futures = {
            executor.submit(
                _process_page,
                task=task,
                source=source,
                database=args.database,
                artifact_root=task_root,
                agy_binary=args.agy_binary,
                dpi=dpi,
                prompt=prompt,
                prompt_sha256=prompt_sha256,
                schema_path=task_root / "response-schema.json",
                response_schema_sha256=response_schema_sha256,
                timeout_seconds=args.timeout_seconds,
                physical_page=page,
            ): page
            for page in expected_pages
        }
        for future in as_completed(futures):
            outcomes.append(future.result())
    outcomes.sort(key=lambda item: item.physical_page)
    image_frontier = {item.physical_page: item.page["image_sha256"] for item in outcomes}
    failed = [item for item in outcomes if item.disposition == "FAILED"]
    result = {
        "effort_counts": {
            effort: sum(
                item.effort == effort and item.disposition == "INGESTED" for item in outcomes
            )
            for effort in EFFORT_ORDER
        },
        "failed_pages": [item.physical_page for item in failed],
        "format_version": FORMAT_VERSION,
        "provider_job_ref": task["provider_job_ref"],
        "reused_pages": [item.physical_page for item in outcomes if item.disposition == "REUSED"],
        "task_id": task["task_id"],
    }
    if failed:
        unresolved = [
            item.physical_page for item in failed if item.failure_kind == "AGY_UNRESOLVED_PAGE"
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
        _write_or_verify(task_root / "agy-run-result.json", canonical_json_bytes_v1(receipt))
        return {**receipt, "disposition": "NEEDS_VERTEX_FLEX_RETRY"}
    manifest = build_financial_document_manifest_v1(
        args.database,
        source_sha256=task["source_sha256"],
        source_logical_name=task["relative_path"],
        expected_physical_pages=expected_pages,
        page_image_sha256s=image_frontier,
        prompt_sha256=prompt_sha256,
        response_schema_sha256=response_schema_sha256,
        requested_model=GOOGLE_MODEL,
        allowed_gateway_service_tiers=_routes(),
        preferred_gateway_service_tiers=_preferred_routes(),
    )
    seal_agy_corpus_task_v1(
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
    _write_or_verify(task_root / "agy-document-manifest.json", canonical_json_bytes_v1(manifest))
    _write_or_verify(task_root / "agy-run-result.json", canonical_json_bytes_v1(complete))
    return complete


def main() -> int:
    try:
        result = run_agy_document_v1(_parser().parse_args())
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if result["disposition"] == "SUCCEEDED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
