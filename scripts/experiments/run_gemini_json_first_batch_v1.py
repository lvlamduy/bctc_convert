#!/usr/bin/env python3
"""Submit, poll, ingest, and report resumable Gemini JSON-first Google batches."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import fitz

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.gemini_financial_page_json_v1 import (  # noqa: E402
    build_financial_page_json_prompt_v1,
    decode_financial_page_json_text_v1,
    financial_page_json_response_schema_v1,
)
from bctc_ai.evaluation.gemini_json_first_batch_v1 import (  # noqa: E402
    ACTIVE_BATCH_STATES,
    BatchSubmissionV1,
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
    summarize_google_batch_operation_v1,
    upload_google_file_v1,
)
from bctc_ai.evaluation.gemini_json_first_provider_v1 import (  # noqa: E402
    GOOGLE_BATCH_SERVICE_TIER,
    GOOGLE_MODEL,
    load_google_api_key_slots_v1,
    load_openrouter_api_key_v1,
)
from bctc_ai.evaluation.openrouter_batch_media_v1 import (  # noqa: E402
    materialize_openrouter_batch_media_v1,
)
from bctc_ai.evaluation.openrouter_json_first_batch_v1 import (  # noqa: E402
    build_openrouter_batch_body_v1,
    decode_completed_openrouter_batch_v1,
    poll_openrouter_batch_v1,
    submit_openrouter_batch_v1,
    summarize_openrouter_batch_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    batch_finalized_requests_v1,
    batch_progress_v1,
    build_financial_document_manifest_v1,
    ingest_financial_page_extraction_v1,
    initialize_gemini_financial_page_store_v1,
    record_batch_poll_v1,
    record_batch_request_result_v1,
    register_batch_submission_v1,
)

MAX_INLINE_BATCH_BODY_BYTES = 18_000_000


class RunGeminiJsonFirstBatchV1Error(RuntimeError):
    pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    submit = commands.add_parser("submit")
    submit.add_argument("--pdf", type=Path, required=True)
    submit.add_argument(
        "--source-logical-name",
        help="Stable corpus-relative filing path; defaults to the PDF filename.",
    )
    page_selection = submit.add_mutually_exclusive_group(required=True)
    page_selection.add_argument("--physical-page", type=int, action="append")
    page_selection.add_argument("--all-pages", action="store_true")
    submit.add_argument("--dpi", type=int, choices=(200, 300), default=300)
    submit.add_argument(
        "--prompt-variant",
        choices=("simple", "items", "compact", "balanced"),
        default="simple",
    )
    submit.add_argument(
        "--output-contract-mode",
        choices=("json-schema", "prompt-json"),
        default="json-schema",
    )
    submit.add_argument("--display-name", required=True)
    submit.add_argument("--provider", choices=("google", "openrouter"), default="google")
    submit.add_argument("--database", type=Path, required=True)
    submit.add_argument("--artifact-dir", type=Path, required=True)
    submit.add_argument(
        "--google-key-file",
        type=Path,
        default=ROOT / "docs/experiments/gemma.txt",
    )
    submit.add_argument("--google-key-slot", type=int)
    submit.add_argument(
        "--openrouter-key-file",
        type=Path,
        default=ROOT / "docs/experiments/openrouter",
    )
    submit.add_argument("--timeout-seconds", type=int, default=120)
    submit.add_argument(
        "--media-transfer", choices=("files", "inline", "s3-presigned"), default="files"
    )
    submit.add_argument(
        "--s3-config",
        type=Path,
        default=ROOT / "config/backup/s3-v1.toml",
    )

    poll = commands.add_parser("poll")
    poll.add_argument("--database", type=Path, required=True)
    poll.add_argument("--artifact-dir", type=Path, required=True)
    poll.add_argument(
        "--google-key-file",
        type=Path,
        default=ROOT / "docs/experiments/gemma.txt",
    )
    poll.add_argument(
        "--openrouter-key-file",
        type=Path,
        default=ROOT / "docs/experiments/openrouter",
    )
    poll.add_argument("--timeout-seconds", type=int, default=60)

    watch = commands.add_parser("watch")
    watch.add_argument("--database", type=Path, required=True)
    watch.add_argument("--artifact-dir", type=Path, required=True)
    watch.add_argument(
        "--google-key-file",
        type=Path,
        default=ROOT / "docs/experiments/gemma.txt",
    )
    watch.add_argument(
        "--openrouter-key-file",
        type=Path,
        default=ROOT / "docs/experiments/openrouter",
    )
    watch.add_argument("--timeout-seconds", type=int, default=60)
    watch.add_argument("--poll-interval-seconds", type=float, default=30.0)
    watch.add_argument("--max-wait-seconds", type=float, default=86_400.0)

    status = commands.add_parser("status")
    status.add_argument("--database", type=Path, required=True)

    register_existing = commands.add_parser("register-existing")
    register_existing.add_argument("--database", type=Path, required=True)
    register_existing.add_argument("--artifact-dir", type=Path, required=True)

    document_manifest = commands.add_parser("document-manifest")
    document_manifest.add_argument("--database", type=Path, required=True)
    document_manifest.add_argument(
        "--batch-artifact-dir", type=Path, action="append", required=True
    )
    document_manifest.add_argument("--expected-page-count", type=int, required=True)
    document_manifest.add_argument(
        "--allow-openrouter-fallback",
        action="store_true",
        help="Allow a unique OpenRouter Flex extraction only where Google Batch has no page.",
    )
    document_manifest.add_argument("--output", type=Path, required=True)
    return parser


def _write_new(path: Path, payload: bytes) -> None:
    if path.exists():
        raise RunGeminiJsonFirstBatchV1Error(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _write_same(path: Path, payload: bytes) -> None:
    if path.exists():
        if path.read_bytes() != payload:
            raise RunGeminiJsonFirstBatchV1Error(f"existing artifact differs: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _json_file(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes())
    if type(value) is not dict:
        raise RunGeminiJsonFirstBatchV1Error(f"artifact is not one JSON object: {path}")
    return value


def _selected_key(path: Path, slot: int) -> tuple[str, str]:
    keys = load_google_api_key_slots_v1(path)
    if slot <= 0 or slot > len(keys):
        raise RunGeminiJsonFirstBatchV1Error("Google key slot lies outside the credential file")
    return keys[slot - 1], f"GOOGLE_SLOT_{slot}"


def _render_pages(
    pdf_path: Path,
    pages: list[int],
    dpi: int,
    source_logical_name: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source = pdf_path.read_bytes()
    document = {
        "source_logical_name": source_logical_name or pdf_path.name,
        "source_sha256": sha256(source).hexdigest(),
        "source_size_bytes": len(source),
    }
    if len(set(pages)) != len(pages) or any(page <= 0 for page in pages):
        raise RunGeminiJsonFirstBatchV1Error("physical pages must be unique positive integers")
    rendered = []
    with fitz.open(pdf_path) as pdf:
        if any(page > pdf.page_count for page in pages):
            raise RunGeminiJsonFirstBatchV1Error("physical page lies outside the PDF")
        for physical_page in sorted(pages):
            pixmap = pdf[physical_page - 1].get_pixmap(dpi=dpi, alpha=False)
            image = pixmap.tobytes("png")
            rendered.append(
                {
                    "document": document,
                    "image": image,
                    "page": {
                        "image_sha256": sha256(image).hexdigest(),
                        "image_size_bytes": len(image),
                        "media_type": "image/png",
                        "physical_page": physical_page,
                        "pixel_height": pixmap.height,
                        "pixel_width": pixmap.width,
                        "render_dpi": dpi,
                    },
                    "request_id": f"{document['source_sha256'][:16]}-p{physical_page:05d}",
                }
            )
    return document, rendered


def _selected_pages(pdf_path: Path, pages: list[int] | None, all_pages: bool) -> list[int]:
    if all_pages:
        with fitz.open(pdf_path) as document:
            return list(range(1, document.page_count + 1))
    if not pages:
        raise RunGeminiJsonFirstBatchV1Error("no physical pages were selected")
    return pages


def _submit(args: argparse.Namespace) -> int:
    if args.provider == "openrouter":
        raise RunGeminiJsonFirstBatchV1Error(
            "OpenRouter Vertex Gemini Batch image transport is unsupported; "
            "use OpenRouter synchronous Vertex Flex or Google JSONL Batch"
        )
    if args.artifact_dir.exists() and any(args.artifact_dir.iterdir()):
        raise RunGeminiJsonFirstBatchV1Error("artifact directory must be empty")
    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    if not args.database.exists():
        initialize_gemini_financial_page_store_v1(args.database)
    output_contract_mode = args.output_contract_mode.replace("-", "_").upper()
    prompt = build_financial_page_json_prompt_v1(
        variant=args.prompt_variant,
        include_contract_template=output_contract_mode == "PROMPT_JSON",
    )
    schema = financial_page_json_response_schema_v1()
    prompt_sha = sha256(prompt.encode()).hexdigest()
    schema_sha = canonical_json_sha256_v1(schema)
    selected_pages = _selected_pages(args.pdf, args.physical_page, args.all_pages)
    _, rendered = _render_pages(
        args.pdf,
        selected_pages,
        args.dpi,
        args.source_logical_name,
    )
    if args.provider == "google":
        if args.google_key_slot is None:
            raise RunGeminiJsonFirstBatchV1Error(
                "Google batch submission requires --google-key-slot"
            )
        api_key, credential_slot = _selected_key(args.google_key_file, args.google_key_slot)
        selected_provider = "GOOGLE_GEMINI_BATCH_API"
    else:
        if args.google_key_slot is not None:
            raise RunGeminiJsonFirstBatchV1Error(
                "OpenRouter batch must not receive --google-key-slot"
            )
        api_key = load_openrouter_api_key_v1(args.openrouter_key_file)
        credential_slot = "OPENROUTER_SLOT_1"
        selected_provider = "OPENROUTER_BATCH"
    uploaded_by_request: dict[str, dict[str, Any]] = {}
    inline_requests = []
    for item in rendered:
        file_uri = None
        inline_image = item["image"]
        if args.provider == "google" and args.media_transfer == "s3-presigned":
            raise RunGeminiJsonFirstBatchV1Error(
                "Google batch does not use the S3 presigned transfer"
            )
        if args.provider == "openrouter" and args.media_transfer == "files":
            raise RunGeminiJsonFirstBatchV1Error(
                "OpenRouter batch requires inline or s3-presigned media"
            )
        if args.provider == "google" and args.media_transfer == "files":
            uploaded = upload_google_file_v1(
                api_key=api_key,
                payload=item["image"],
                media_type=item["page"]["media_type"],
                display_name=item["request_id"] + ".png",
                timeout_seconds=args.timeout_seconds,
            )
            uploaded_raw = uploaded.raw_response_bytes
            if not uploaded_raw.endswith(b"\n"):
                uploaded_raw += b"\n"
            _write_new(
                args.artifact_dir / "uploaded-files" / (item["request_id"] + ".json"),
                uploaded_raw,
            )
            uploaded_by_request[item["request_id"]] = {
                "expiration_time": uploaded.expiration_time,
                "media_type": uploaded.media_type,
                "name": uploaded.name,
                "sha256": uploaded.sha256,
                "size_bytes": uploaded.size_bytes,
                "uri": uploaded.uri,
            }
            file_uri = uploaded.uri
            inline_image = None
        elif args.provider == "openrouter" and args.media_transfer == "s3-presigned":
            materialized = materialize_openrouter_batch_media_v1(
                payload=item["image"],
                media_type=item["page"]["media_type"],
                s3_config_path=args.s3_config,
            )
            uploaded_by_request[item["request_id"]] = materialized.public_receipt()
            file_uri = materialized.url
            inline_image = None
        inline_requests.append(
            InlinePageRequestV1(
                request_id=item["request_id"],
                image=inline_image,
                file_uri=file_uri,
                media_type=item["page"]["media_type"],
                prompt=prompt,
                response_schema=schema,
                output_contract_mode=output_contract_mode,
            )
        )
    google_input_file = None
    if args.provider == "google" and args.media_transfer == "files":
        inlined = build_google_inline_batch_body_v1(
            display_name=args.display_name, requests=inline_requests
        )["batch"]["inputConfig"]["requests"]["requests"]
        jsonl_lines = []
        for item in inlined:
            request = json.loads(canonical_json_bytes_v1(item["request"]))
            # The job-level model is authoritative for file-backed Batch requests.
            request.pop("model", None)
            request.pop("store", None)
            jsonl_lines.append(
                canonical_json_bytes_v1({"key": item["metadata"]["request_id"], "request": request})
            )
        jsonl_bytes = b"\n".join(jsonl_lines) + b"\n"
        _write_new(args.artifact_dir / "batch-input.jsonl", jsonl_bytes)
        google_input_file = upload_google_file_v1(
            api_key=api_key,
            payload=jsonl_bytes,
            media_type="application/jsonl",
            display_name=args.display_name + ".jsonl",
            timeout_seconds=args.timeout_seconds,
        )
        input_raw = google_input_file.raw_response_bytes
        if not input_raw.endswith(b"\n"):
            input_raw += b"\n"
        _write_new(args.artifact_dir / "uploaded-files" / "batch-input.json", input_raw)
        body = build_google_file_batch_body_v1(
            display_name=args.display_name,
            input_file_name=google_input_file.name,
        )
    elif args.provider == "google":
        body = build_google_inline_batch_body_v1(
            display_name=args.display_name, requests=inline_requests
        )
    else:
        body = build_openrouter_batch_body_v1(requests=inline_requests)
    body_size = len(canonical_json_bytes_v1(body))
    if body_size > MAX_INLINE_BATCH_BODY_BYTES:
        raise RunGeminiJsonFirstBatchV1Error(
            "inline batch body exceeds 18 MB; split the physical-page list into smaller batches"
        )
    manifest = {
        "body_size_bytes": body_size,
        "display_name": args.display_name,
        "format_version": "GEMINI_JSON_FIRST_BATCH_RUN_V1",
        "media_transfer": args.media_transfer.upper(),
        "batch_input_file_ref": (
            None
            if google_input_file is None
            else {
                "expiration_time": google_input_file.expiration_time,
                "media_type": google_input_file.media_type,
                "name": google_input_file.name,
                "sha256": google_input_file.sha256,
                "size_bytes": google_input_file.size_bytes,
            }
        ),
        "provider": selected_provider,
        "output_contract_mode": output_contract_mode,
        "prompt_sha256": prompt_sha,
        "prompt_variant": args.prompt_variant,
        "requested_model": GOOGLE_MODEL,
        "requested_service_tier": GOOGLE_BATCH_SERVICE_TIER,
        "requests": [
            {
                "document": item["document"],
                "page": item["page"],
                "provider_file_ref": uploaded_by_request.get(item["request_id"]),
                "request_id": item["request_id"],
            }
            for item in rendered
        ],
        "response_schema_sha256": schema_sha,
        "thinking_level": "low",
    }
    manifest_bytes = canonical_json_bytes_v1(manifest) + b"\n"
    _write_new(args.artifact_dir / "manifest.json", manifest_bytes)
    _write_new(args.artifact_dir / "prompt.txt", prompt.encode())
    _write_new(args.artifact_dir / "response-schema.json", canonical_json_bytes_v1(schema) + b"\n")
    if args.provider == "google":
        submission = (
            submit_google_file_batch_v1(
                api_key=api_key,
                credential_slot=credential_slot,
                display_name=args.display_name,
                input_file_name=google_input_file.name,
                timeout_seconds=args.timeout_seconds,
            )
            if google_input_file is not None
            else submit_google_inline_batch_v1(
                api_key=api_key,
                credential_slot=credential_slot,
                display_name=args.display_name,
                requests=inline_requests,
                timeout_seconds=args.timeout_seconds,
            )
        )
        operation_summary = None
    else:
        submission = submit_openrouter_batch_v1(
            api_key=api_key,
            requests=inline_requests,
            timeout_seconds=args.timeout_seconds,
        )
        operation_summary = summarize_openrouter_batch_v1(submission.raw_response_bytes)
    submission_raw = submission.raw_response_bytes
    if not submission_raw.endswith(b"\n"):
        submission_raw += b"\n"
    _write_new(args.artifact_dir / "submission-response.json", submission_raw)
    receipt = {
        "batch_name": submission.batch_name,
        "credential_slot": credential_slot,
        "elapsed_seconds": submission.elapsed_seconds,
        "manifest_sha256": sha256(manifest_bytes).hexdigest(),
        "provider": selected_provider,
        "state": submission.state,
        "submission_response_sha256": sha256(submission_raw).hexdigest(),
    }
    _write_new(
        args.artifact_dir / "submission-receipt.json", canonical_json_bytes_v1(receipt) + b"\n"
    )
    batch_job_id = register_batch_submission_v1(
        args.database,
        submission=submission,
        display_name=args.display_name,
        requests=[
            {
                "document": item["document"],
                "page": item["page"],
                "request_id": item["request_id"],
            }
            for item in manifest["requests"]
        ],
        prompt_variant=args.prompt_variant,
        output_contract_mode=output_contract_mode,
        prompt_sha256=prompt_sha,
        response_schema_sha256=schema_sha,
        requested_model=GOOGLE_MODEL,
        thinking_level="low",
        provider=selected_provider,
        requested_service_tier=GOOGLE_BATCH_SERVICE_TIER,
        operation_summary=operation_summary,
    )
    print(
        json.dumps(
            {
                "batch_job_id": batch_job_id,
                "batch_name": submission.batch_name,
                "body_size_bytes": body_size,
                "credential_slot": credential_slot,
                "request_count": len(rendered),
                "state": submission.state,
            },
            sort_keys=True,
        )
    )
    return 0


def _elapsed_seconds(operation: dict[str, Any]) -> str:
    if type(operation.get("created_at")) is int and type(operation.get("finalized_at")) is int:
        return format(operation["finalized_at"] - operation["created_at"], ".3f")
    metadata = operation.get("metadata")
    if type(metadata) is not dict:
        return "0.000"
    start = metadata.get("createTime")
    end = metadata.get("endTime")
    if type(start) is not str or type(end) is not str:
        return "0.000"
    seconds = (
        datetime.fromisoformat(end.replace("Z", "+00:00"))
        - datetime.fromisoformat(start.replace("Z", "+00:00"))
    ).total_seconds()
    return format(seconds, ".3f")


def _register_existing(args: argparse.Namespace) -> int:
    """Idempotently bind an already-submitted provider batch to one store."""

    receipt = _json_file(args.artifact_dir / "submission-receipt.json")
    manifest_bytes = (args.artifact_dir / "manifest.json").read_bytes()
    submission_raw = (args.artifact_dir / "submission-response.json").read_bytes()
    if sha256(manifest_bytes).hexdigest() != receipt.get("manifest_sha256"):
        raise RunGeminiJsonFirstBatchV1Error("batch manifest hash drifted")
    if sha256(submission_raw).hexdigest() != receipt.get("submission_response_sha256"):
        raise RunGeminiJsonFirstBatchV1Error("batch submission response hash drifted")
    manifest = json.loads(manifest_bytes)
    provider = receipt.get("provider")
    if provider != manifest.get("provider") or provider not in {
        "GOOGLE_GEMINI_BATCH_API",
        "OPENROUTER_BATCH",
    }:
        raise RunGeminiJsonFirstBatchV1Error("batch provider identity drifted")
    required_receipt = {
        "batch_name",
        "credential_slot",
        "elapsed_seconds",
        "manifest_sha256",
        "provider",
        "state",
        "submission_response_sha256",
    }
    if set(receipt) != required_receipt:
        raise RunGeminiJsonFirstBatchV1Error("batch submission receipt fields drifted")
    if not args.database.exists():
        initialize_gemini_financial_page_store_v1(args.database)
    existing = [
        item
        for item in batch_progress_v1(args.database)
        if item["batch_name"] == receipt["batch_name"]
    ]
    if existing:
        item = existing[0]
        if (
            item["provider"] != provider
            or item["credential_slot"] != receipt["credential_slot"]
            or item["request_count"] != len(manifest.get("requests", []))
        ):
            raise RunGeminiJsonFirstBatchV1Error(
                "registered batch differs from the supplied immutable artifacts"
            )
        print(json.dumps({"disposition": "ALREADY_REGISTERED", **item}, sort_keys=True))
        return 0
    submission = BatchSubmissionV1(
        batch_name=receipt["batch_name"],
        state=receipt["state"],
        raw_response_bytes=submission_raw,
        elapsed_seconds=receipt["elapsed_seconds"],
        credential_slot=receipt["credential_slot"],
    )
    requests = [
        {
            "document": request["document"],
            "page": request["page"],
            "request_id": request["request_id"],
        }
        for request in manifest.get("requests", [])
    ]
    operation_summary = (
        summarize_openrouter_batch_v1(submission_raw) if provider == "OPENROUTER_BATCH" else None
    )
    batch_job_id = register_batch_submission_v1(
        args.database,
        submission=submission,
        display_name=manifest["display_name"],
        requests=requests,
        prompt_variant=manifest["prompt_variant"],
        output_contract_mode=manifest["output_contract_mode"],
        prompt_sha256=manifest["prompt_sha256"],
        response_schema_sha256=manifest["response_schema_sha256"],
        requested_model=manifest["requested_model"],
        thinking_level=manifest["thinking_level"],
        provider=provider,
        requested_service_tier=manifest["requested_service_tier"],
        operation_summary=operation_summary,
    )
    print(
        json.dumps(
            {
                "batch_job_id": batch_job_id,
                "batch_name": receipt["batch_name"],
                "disposition": "REGISTERED_EXISTING",
                "request_count": len(requests),
            },
            sort_keys=True,
        )
    )
    return 0


def _poll(args: argparse.Namespace) -> int:
    receipt = _json_file(args.artifact_dir / "submission-receipt.json")
    manifest_bytes = (args.artifact_dir / "manifest.json").read_bytes()
    if sha256(manifest_bytes).hexdigest() != receipt.get("manifest_sha256"):
        raise RunGeminiJsonFirstBatchV1Error("batch manifest hash drifted")
    manifest = json.loads(manifest_bytes)
    provider = receipt.get("provider")
    if provider is None:
        legacy_slot = receipt.get("credential_slot")
        provider = (
            "GOOGLE_GEMINI_BATCH_API"
            if type(legacy_slot) is str and legacy_slot.startswith("GOOGLE_SLOT_")
            else None
        )
    if provider != manifest.get("provider", provider) or provider not in {
        "GOOGLE_GEMINI_BATCH_API",
        "OPENROUTER_BATCH",
    }:
        raise RunGeminiJsonFirstBatchV1Error("batch provider identity drifted")
    slot_text = receipt.get("credential_slot")
    if provider == "GOOGLE_GEMINI_BATCH_API":
        if type(slot_text) is not str or not slot_text.startswith("GOOGLE_SLOT_"):
            raise RunGeminiJsonFirstBatchV1Error("batch credential slot drifted")
        slot = int(slot_text.removeprefix("GOOGLE_SLOT_"))
        api_key, credential_slot = _selected_key(args.google_key_file, slot)
        raw = poll_google_batch_v1(
            api_key=api_key,
            batch_name=receipt["batch_name"],
            timeout_seconds=args.timeout_seconds,
        )
        summary = summarize_google_batch_operation_v1(raw)
    else:
        if slot_text != "OPENROUTER_SLOT_1":
            raise RunGeminiJsonFirstBatchV1Error("OpenRouter credential slot drifted")
        api_key = load_openrouter_api_key_v1(args.openrouter_key_file)
        credential_slot = slot_text
        raw = poll_openrouter_batch_v1(
            api_key=api_key,
            batch_name=receipt["batch_name"],
            timeout_seconds=args.timeout_seconds,
        )
        summary = summarize_openrouter_batch_v1(raw)
    next_ordinal = 1 + len(list(args.artifact_dir.glob("poll-*.json")))
    poll_raw = raw + (b"" if raw.endswith(b"\n") else b"\n")
    _write_new(args.artifact_dir / f"poll-{next_ordinal:05d}.json", poll_raw)
    record_batch_poll_v1(
        args.database,
        raw_operation_bytes=raw,
        operation_summary=summary if provider == "OPENROUTER_BATCH" else None,
    )
    if summary["state"] in ACTIVE_BATCH_STATES:
        print(json.dumps({**summary, "progress": batch_progress_v1(args.database)}, sort_keys=True))
        return 0
    if summary["state"] != "BATCH_STATE_SUCCEEDED":
        finalized = batch_finalized_requests_v1(args.database, batch_name=summary["batch_name"])
        operation_error = json.loads(raw).get("error")
        for request in manifest["requests"]:
            if request["request_id"] not in finalized:
                record_batch_request_result_v1(
                    args.database,
                    batch_name=summary["batch_name"],
                    request_id=request["request_id"],
                    disposition="FAILED",
                    error={
                        "batch_state": summary["state"],
                        "provider_error": operation_error,
                    },
                )
        print(json.dumps({"progress": batch_progress_v1(args.database)}, sort_keys=True))
        return 0
    operation = json.loads(raw)
    expected_request_ids = [item["request_id"] for item in manifest["requests"]]
    result_bytes = None
    if provider == "GOOGLE_GEMINI_BATCH_API" and manifest.get("batch_input_file_ref") is not None:
        result_bytes = download_google_file_v1(
            api_key=api_key,
            file_name=google_batch_responses_file_v1(raw),
            timeout_seconds=args.timeout_seconds,
        )
        _write_same(args.artifact_dir / "batch-results.jsonl", result_bytes)
    completed = (
        (
            decode_completed_google_file_batch_v1(
                raw_operation_bytes=raw,
                raw_results_bytes=result_bytes,
                expected_request_ids=expected_request_ids,
                credential_slot=credential_slot,
                elapsed_seconds=_elapsed_seconds(operation),
            )
            if manifest.get("batch_input_file_ref") is not None
            else decode_completed_google_inline_batch_v1(
                raw_operation_bytes=raw,
                expected_request_ids=expected_request_ids,
                credential_slot=credential_slot,
                elapsed_seconds=_elapsed_seconds(operation),
            )
        )
        if provider == "GOOGLE_GEMINI_BATCH_API"
        else decode_completed_openrouter_batch_v1(
            raw=raw,
            expected_request_ids=expected_request_ids,
            elapsed_seconds=_elapsed_seconds(operation),
        )
    )
    finalized = batch_finalized_requests_v1(args.database, batch_name=completed.batch_name)
    by_id = {item["request_id"]: item for item in manifest["requests"]}
    for request_id, error in completed.failures.items():
        if request_id not in finalized:
            record_batch_request_result_v1(
                args.database,
                batch_name=completed.batch_name,
                request_id=request_id,
                disposition="FAILED",
                error={"provider_error": error},
            )
    for request_id, result in completed.provider_results.items():
        if request_id in finalized:
            continue
        result_dir = args.artifact_dir / "results" / request_id
        raw_result = result.raw_response_bytes
        if not raw_result.endswith(b"\n"):
            raw_result += b"\n"
        _write_same(result_dir / "raw-response.json", raw_result)
        try:
            page_json = decode_financial_page_json_text_v1(result.output_text)
        except Exception as exc:
            error = {
                "error_type": type(exc).__name__,
                "raw_response_sha256": sha256(raw_result).hexdigest(),
                "usage": result.usage,
            }
            _write_same(
                result_dir / "semantic-validation-failure.json",
                canonical_json_bytes_v1(error) + b"\n",
            )
            record_batch_request_result_v1(
                args.database,
                batch_name=completed.batch_name,
                request_id=request_id,
                disposition="FAILED",
                error=error,
            )
            continue
        item = by_id[request_id]
        identities = ingest_financial_page_extraction_v1(
            args.database,
            document=item["document"],
            page=item["page"],
            prompt_variant=manifest["prompt_variant"],
            output_contract_mode=manifest["output_contract_mode"],
            prompt_sha256=manifest["prompt_sha256"],
            response_schema_sha256=manifest["response_schema_sha256"],
            requested_model=manifest["requested_model"],
            requested_service_tier=manifest["requested_service_tier"],
            thinking_level=manifest["thinking_level"],
            provider_result=result,
            page_json=page_json,
        )
        _write_same(result_dir / "page.json", canonical_json_bytes_v1(page_json) + b"\n")
        _write_same(
            result_dir / "ingest-identities.json",
            canonical_json_bytes_v1(identities) + b"\n",
        )
        record_batch_request_result_v1(
            args.database,
            batch_name=completed.batch_name,
            request_id=request_id,
            disposition="INGESTED",
            extraction_run_id=identities["extraction_run_id"],
        )
    print(json.dumps({"progress": batch_progress_v1(args.database)}, sort_keys=True))
    return 0


def _watch(args: argparse.Namespace) -> int:
    """Resume-safe polling loop for one previously submitted batch."""

    if args.poll_interval_seconds <= 0 or args.poll_interval_seconds > 3_600:
        raise RunGeminiJsonFirstBatchV1Error("poll interval lies outside 0..3600 seconds")
    if args.max_wait_seconds <= 0 or args.max_wait_seconds > 7 * 86_400:
        raise RunGeminiJsonFirstBatchV1Error("maximum wait lies outside 0..7 days")
    receipt = _json_file(args.artifact_dir / "submission-receipt.json")
    started = time.monotonic()
    while True:
        _poll(args)
        matching = [
            item
            for item in batch_progress_v1(args.database)
            if item["batch_name"] == receipt.get("batch_name")
        ]
        if len(matching) != 1:
            raise RunGeminiJsonFirstBatchV1Error(
                "watched batch is not uniquely registered in the page store"
            )
        progress = matching[0]
        if progress["state"] not in ACTIVE_BATCH_STATES:
            disposition = "SUCCEEDED" if progress["failed_pages"] == 0 else "NEEDS_RETRY"
            print(json.dumps({"disposition": disposition, **progress}, sort_keys=True))
            return 0 if disposition == "SUCCEEDED" else 2
        if time.monotonic() - started >= args.max_wait_seconds:
            raise RunGeminiJsonFirstBatchV1Error(
                "watch reached its bounded wait before the batch became terminal"
            )
        time.sleep(args.poll_interval_seconds)


def _document_manifest(args: argparse.Namespace) -> int:
    if args.expected_page_count <= 0:
        raise RunGeminiJsonFirstBatchV1Error("expected page count must be positive")
    allow_openrouter_fallback = bool(getattr(args, "allow_openrouter_fallback", False))
    manifests = [
        _json_file(artifact_dir / "manifest.json") for artifact_dir in args.batch_artifact_dir
    ]
    contract_fields = (
        ("prompt_sha256", "requested_model", "response_schema_sha256")
        if allow_openrouter_fallback
        else (
            "prompt_sha256",
            "provider",
            "requested_model",
            "requested_service_tier",
            "response_schema_sha256",
        )
    )
    contracts = [
        {field: manifest.get(field) for field in contract_fields} for manifest in manifests
    ]
    if not contracts or any(contract != contracts[0] for contract in contracts[1:]):
        raise RunGeminiJsonFirstBatchV1Error(
            "batch artifact manifests do not share one extraction contract"
        )
    requests = [request for manifest in manifests for request in manifest.get("requests", [])]
    if not requests:
        raise RunGeminiJsonFirstBatchV1Error("batch artifact manifests contain no requests")
    document = requests[0].get("document")
    if type(document) is not dict or any(
        request.get("document") != document for request in requests[1:]
    ):
        raise RunGeminiJsonFirstBatchV1Error(
            "batch artifact manifests do not bind one exact document"
        )
    retry_page_bindings: dict[int, dict[str, Any]] = {}
    for request in requests:
        page = request.get("page")
        physical_page = page.get("physical_page") if type(page) is dict else None
        if type(physical_page) is not int or physical_page <= 0:
            raise RunGeminiJsonFirstBatchV1Error(
                "batch artifact manifest contains an invalid physical page"
            )
        prior = retry_page_bindings.get(physical_page)
        if prior is not None and prior != page:
            raise RunGeminiJsonFirstBatchV1Error(
                "batch artifact manifests disagree on one retried page binding"
            )
        retry_page_bindings[physical_page] = page
    expected_pages = list(range(1, args.expected_page_count + 1))
    if sorted(retry_page_bindings) != expected_pages:
        raise RunGeminiJsonFirstBatchV1Error(
            "batch artifact manifests do not cover the exact document page frontier"
        )
    contract = contracts[0]
    manifest_args: dict[str, Any] = {
        "source_sha256": document["source_sha256"],
        "source_logical_name": document["source_logical_name"],
        "expected_physical_pages": expected_pages,
        "prompt_sha256": contract["prompt_sha256"],
        "response_schema_sha256": contract["response_schema_sha256"],
        "requested_model": contract["requested_model"],
    }
    if allow_openrouter_fallback:
        manifest_args["allowed_gateway_service_tiers"] = [
            {
                "gateway": "GOOGLE_GEMINI_BATCH_API",
                "requested_service_tier": "batch",
            },
            {"gateway": "OPENROUTER", "requested_service_tier": "flex"},
        ]
    else:
        manifest_args["requested_service_tier"] = contract["requested_service_tier"]
        manifest_args["selected_provider"] = contract["provider"]
    output = build_financial_document_manifest_v1(args.database, **manifest_args)
    _write_same(args.output, canonical_json_bytes_v1(output) + b"\n")
    print(
        json.dumps(
            {
                "document_manifest_id": output["document_manifest_id"],
                "output": str(args.output),
                "page_count": output["page_count"],
                "status_counts": output["status_counts"],
                "totals": output["totals"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    args = _parser().parse_args()
    if args.command == "submit":
        return _submit(args)
    if args.command == "poll":
        return _poll(args)
    if args.command == "watch":
        return _watch(args)
    if args.command == "register-existing":
        return _register_existing(args)
    if args.command == "document-manifest":
        return _document_manifest(args)
    print(json.dumps({"progress": batch_progress_v1(args.database)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
