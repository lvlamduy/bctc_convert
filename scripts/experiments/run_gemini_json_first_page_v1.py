#!/usr/bin/env python3
"""Extract one financial-report page through one explicit Gemini provider route."""

from __future__ import annotations

import argparse
import json
import os
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

import fitz
from PIL import Image

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
    GOOGLE_SERVICE_TIER,
    GOOGLE_STANDARD_SERVICE_TIER,
    OPENROUTER_SERVICE_TIER,
    GeminiJsonFirstProviderV1Error,
    call_gemini_json_first_v1,
    load_google_api_key_slots_v1,
    load_openrouter_api_key_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    extraction_cache_key_v1,
    ingest_financial_page_extraction_v1,
    initialize_gemini_financial_page_store_v1,
    lookup_cached_page_json_v1,
    usage_summary_v1,
)

_PNG = b"\x89PNG\r\n\x1a\n"


class RunGeminiJsonFirstPageV1Error(RuntimeError):
    pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--image", type=Path)
    source.add_argument("--pdf", type=Path)
    parser.add_argument("--physical-page", type=int)
    parser.add_argument(
        "--source-logical-name",
        help="Stable corpus-relative filing path; defaults to the input filename.",
    )
    parser.add_argument("--dpi", type=int, choices=(200, 300), default=300)
    parser.add_argument(
        "--prompt-variant",
        choices=("simple", "compact", "balanced"),
        default="simple",
    )
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument(
        "--execution-policy",
        choices=("openrouter-pilot", "google-direct-standard", "google-direct-flex"),
        default="openrouter-pilot",
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
    parser.add_argument(
        "--google-key-slot",
        type=int,
        help="Use one 1-based Google credential slot; default uses all slots in file order.",
    )
    parser.add_argument(
        "--output-contract-mode",
        choices=("json-schema", "prompt-json"),
        default="json-schema",
    )
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument(
        "--google-retries-per-slot",
        "--flex-retries-per-slot",
        dest="google_retries_per_slot",
        type=int,
        default=2,
    )
    parser.add_argument("--openrouter-retries", type=int, default=2)
    parser.add_argument("--retry-delay-seconds", type=float, default=5.0)
    return parser


def _image(args: argparse.Namespace) -> tuple[bytes, str, dict[str, Any], dict[str, Any]]:
    if args.image is not None:
        payload = args.image.read_bytes()
        if payload.startswith(_PNG):
            media_type = "image/png"
        elif payload.startswith(b"\xff\xd8"):
            media_type = "image/jpeg"
        else:
            raise RunGeminiJsonFirstPageV1Error("image must be PNG or JPEG")
        with Image.open(args.image) as image:
            width, height = image.size
        source_bytes = payload
        physical_page = args.physical_page or 1
        logical_name = args.source_logical_name or args.image.name
        input_kind = "IMAGE"
    else:
        if args.physical_page is None or args.physical_page <= 0:
            raise RunGeminiJsonFirstPageV1Error("--pdf requires positive --physical-page")
        if args.dpi not in {200, 300}:
            raise RunGeminiJsonFirstPageV1Error("DPI must be exactly 200 or 300")
        source_bytes = args.pdf.read_bytes()
        with fitz.open(args.pdf) as document:
            if args.physical_page > document.page_count:
                raise RunGeminiJsonFirstPageV1Error("physical page lies outside PDF")
            pixmap = document.load_page(args.physical_page - 1).get_pixmap(
                dpi=args.dpi, alpha=False
            )
            width, height = pixmap.width, pixmap.height
            payload = pixmap.tobytes("png")
        media_type = "image/png"
        physical_page = args.physical_page
        logical_name = args.source_logical_name or args.pdf.name
        input_kind = "PDF_PAGE_RENDER"
    document = {
        "source_logical_name": logical_name,
        "source_sha256": sha256(source_bytes).hexdigest(),
        "source_size_bytes": len(source_bytes),
    }
    page = {
        "image_sha256": sha256(payload).hexdigest(),
        "image_size_bytes": len(payload),
        "media_type": media_type,
        "physical_page": physical_page,
        "pixel_height": height,
        "pixel_width": width,
        "render_dpi": args.dpi,
    }
    return payload, media_type, document, {**page, "input_kind": input_kind}


def _write(path: Path, payload: bytes) -> None:
    if path.exists():
        raise RunGeminiJsonFirstPageV1Error(f"refusing to overwrite {path}")
    path.write_bytes(payload)


def _append_attempt(path: Path, attempt: dict[str, Any]) -> None:
    payload = canonical_json_bytes_v1(attempt) + b"\n"
    with path.open("ab", buffering=0) as stream:
        stream.write(payload)
        os.fsync(stream.fileno())


def main() -> int:
    args = _parser().parse_args()
    image, media_type, document, page_with_kind = _image(args)
    input_kind = page_with_kind.pop("input_kind")
    page = page_with_kind
    output_contract_mode = args.output_contract_mode.replace("-", "_").upper()
    execution_policy = {
        "openrouter-pilot": "OPENROUTER_PILOT",
        "google-direct-standard": "GOOGLE_DIRECT_STANDARD",
        "google-direct-flex": "GOOGLE_DIRECT_DIAGNOSTIC",
    }[args.execution_policy]
    requested_service_tier = {
        "OPENROUTER_PILOT": OPENROUTER_SERVICE_TIER,
        "GOOGLE_DIRECT_STANDARD": GOOGLE_STANDARD_SERVICE_TIER,
        "GOOGLE_DIRECT_DIAGNOSTIC": GOOGLE_SERVICE_TIER,
    }[execution_policy]
    prompt = build_financial_page_json_prompt_v1(
        variant=args.prompt_variant,
        include_contract_template=output_contract_mode == "PROMPT_JSON",
    )
    schema = financial_page_json_response_schema_v1()
    prompt_bytes = prompt.encode("utf-8")
    prompt_sha = sha256(prompt_bytes).hexdigest()
    schema_sha = canonical_json_sha256_v1(schema)
    if not args.database.exists():
        initialize_gemini_financial_page_store_v1(args.database)
    cache_key = extraction_cache_key_v1(
        source_sha256=document["source_sha256"],
        source_logical_name=document["source_logical_name"],
        image_sha256=page["image_sha256"],
        prompt_sha256=prompt_sha,
        response_schema_sha256=schema_sha,
        requested_model=GOOGLE_MODEL,
        requested_service_tier=requested_service_tier,
        thinking_level="low",
        prompt_variant=args.prompt_variant,
        output_contract_mode=output_contract_mode,
    )
    cached = lookup_cached_page_json_v1(args.database, cache_key)
    if cached is not None:
        print(
            json.dumps(
                {
                    "cache_key": cache_key,
                    "content_counts": count_financial_page_content_v1(cached),
                    "provider_call_count": 0,
                    "status": "CACHE_HIT",
                    "usage_summary": usage_summary_v1(args.database),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    if args.artifact_dir.exists():
        if any(args.artifact_dir.iterdir()):
            raise RunGeminiJsonFirstPageV1Error("artifact directory must be empty")
    else:
        args.artifact_dir.mkdir(parents=True)
    _write(args.artifact_dir / "prompt.txt", prompt_bytes)
    _write(args.artifact_dir / "response-schema.json", canonical_json_bytes_v1(schema) + b"\n")
    progress_path = args.artifact_dir / "attempts-progress.jsonl"
    _write(progress_path, b"")
    openrouter_key = (
        load_openrouter_api_key_v1(args.openrouter_key_file)
        if execution_policy == "OPENROUTER_PILOT"
        else None
    )
    google_keys = None
    google_credential_slots = None
    if execution_policy != "OPENROUTER_PILOT":
        google_keys = load_google_api_key_slots_v1(args.google_key_file)
        google_credential_slots = [
            f"GOOGLE_SLOT_{index}" for index in range(1, len(google_keys) + 1)
        ]
        if args.google_key_slot is not None:
            if args.google_key_slot <= 0 or args.google_key_slot > len(google_keys):
                raise RunGeminiJsonFirstPageV1Error(
                    "--google-key-slot lies outside the discovered credential slots"
                )
            google_keys = [google_keys[args.google_key_slot - 1]]
            google_credential_slots = [f"GOOGLE_SLOT_{args.google_key_slot}"]
    try:
        result = call_gemini_json_first_v1(
            google_api_keys=google_keys,
            google_credential_slots=google_credential_slots,
            openrouter_api_key=openrouter_key,
            image=image,
            media_type=media_type,
            prompt=prompt,
            response_schema=schema,
            output_contract_mode=output_contract_mode,
            execution_policy=execution_policy,
            timeout_seconds=args.timeout_seconds,
            flex_retries_per_slot=args.google_retries_per_slot,
            openrouter_retries=args.openrouter_retries,
            retry_delay_seconds=args.retry_delay_seconds,
            on_attempt=lambda attempt: _append_attempt(progress_path, attempt),
        )
    except GeminiJsonFirstProviderV1Error as exc:
        if exc.raw_response_bytes is not None:
            raw_failure = exc.raw_response_bytes
            if not raw_failure.endswith(b"\n"):
                raw_failure += b"\n"
            _write(args.artifact_dir / "raw-response-before-validation.json", raw_failure)
        _write(
            args.artifact_dir / "failed-attempts.json",
            canonical_json_bytes_v1(
                {
                    "attempts": list(exc.attempts),
                    "error_type": type(exc).__name__,
                    "input_image_sha256": page["image_sha256"],
                    "prompt_sha256": prompt_sha,
                    "response_schema_sha256": schema_sha,
                }
            )
            + b"\n",
        )
        raise
    raw_bytes = result.raw_response_bytes
    if not raw_bytes.endswith(b"\n"):
        raw_bytes += b"\n"
    _write(args.artifact_dir / "raw-response.json", raw_bytes)
    try:
        page_json = decode_financial_page_json_text_v1(result.output_text)
    except Exception as exc:
        _write(
            args.artifact_dir / "semantic-validation-failure.json",
            canonical_json_bytes_v1(
                {
                    "attempts": list(result.attempts),
                    "error_type": type(exc).__name__,
                    "input_image_sha256": page["image_sha256"],
                    "output_contract_mode": output_contract_mode,
                    "prompt_sha256": prompt_sha,
                    "raw_response_sha256": sha256(raw_bytes).hexdigest(),
                    "response_schema_sha256": schema_sha,
                    "usage": result.usage,
                }
            )
            + b"\n",
        )
        raise
    identities = ingest_financial_page_extraction_v1(
        args.database,
        document=document,
        page=page,
        prompt_variant=args.prompt_variant,
        output_contract_mode=output_contract_mode,
        prompt_sha256=prompt_sha,
        response_schema_sha256=schema_sha,
        requested_model=GOOGLE_MODEL,
        requested_service_tier=requested_service_tier,
        thinking_level="low",
        provider_result=result,
        page_json=page_json,
    )
    page_json_bytes = canonical_json_bytes_v1(page_json) + b"\n"
    observation = {
        "attempts": list(result.attempts),
        "content_counts": count_financial_page_content_v1(page_json),
        "database_identities": identities,
        "input": {
            "document": document,
            "input_kind": input_kind,
            "page": page,
            "prompt_sha256": prompt_sha,
            "prompt_variant": args.prompt_variant,
            "output_contract_mode": output_contract_mode,
            "response_schema_sha256": schema_sha,
        },
        "page_json_ref": {
            "sha256": sha256(page_json_bytes).hexdigest(),
            "size_bytes": len(page_json_bytes),
        },
        "provider": {
            "model": result.provider_model,
            "name": result.provider_name,
            "response_id_sha256": result.response_id_sha256,
            "service_tier": result.service_tier,
        },
        "raw_response_ref": {
            "sha256": sha256(raw_bytes).hexdigest(),
            "size_bytes": len(raw_bytes),
        },
        "usage": result.usage,
    }
    observation["observation_id"] = "gjfpv1:observation:" + canonical_json_sha256_v1(observation)
    _write(args.artifact_dir / "page.json", page_json_bytes)
    _write(
        args.artifact_dir / "observation.json",
        canonical_json_bytes_v1(observation) + b"\n",
    )
    summary = {
        "attempt_count": len(result.attempts),
        "content_counts": observation["content_counts"],
        "cost_usd": result.usage.get("actual_cost_usd", result.usage.get("estimated_cost_usd")),
        "input_tokens": result.usage["input_tokens"],
        "output_tokens": result.usage["output_tokens"],
        "provider": result.provider_name,
        "status": page_json["status"],
        "thought_tokens": result.usage["thought_tokens"],
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
