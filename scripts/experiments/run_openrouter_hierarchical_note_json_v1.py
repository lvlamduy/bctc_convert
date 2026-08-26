#!/usr/bin/env python3
"""Run a bounded OpenRouter image-to-hierarchical-note-JSON experiment."""

from __future__ import annotations

import argparse
import base64
import http.client
import json
import re
import sys
import time
import urllib.error
import urllib.request
from hashlib import sha256
from pathlib import Path
from typing import Any

import fitz

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.hosted_gemma4_hierarchical_note_json_v1 import (  # noqa: E402
    FORMAT_VERSION,
    build_hierarchical_note_json_prompt_v1,
    decode_hierarchical_note_json_text_v1,
    hierarchical_note_json_response_schema_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

_DEFAULT_MODEL = "google/gemma-4-31b-it"
_KEY = re.compile(
    r"^\s*OPENROUTER_API_KEY\s*=\s*[\"']?([^\"'\s]+)[\"']?\s*$",
    re.MULTILINE,
)
_PNG = b"\x89PNG\r\n\x1a\n"


class OpenRouterHierarchicalNoteJsonExperimentError(RuntimeError):
    pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--image", type=Path)
    source.add_argument("--pdf", type=Path)
    parser.add_argument("--physical-page", type=int)
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--api-key-file", type=Path, required=True)
    parser.add_argument("--model", default=_DEFAULT_MODEL)
    parser.add_argument("--provider", required=True)
    parser.add_argument(
        "--quantization",
        choices=("bf16", "fp16", "fp8", "fp4"),
    )
    parser.add_argument("--timeout-seconds", type=int, default=240)
    parser.add_argument("--max-output-tokens", type=int, default=8192)
    parser.add_argument(
        "--response-mode",
        choices=("json_schema", "json_object"),
        default="json_schema",
    )
    parser.add_argument("--omit-reasoning", action="store_true")
    parser.add_argument("--reasoning-effort", choices=("low", "medium", "high"))
    parser.add_argument("--omit-temperature", action="store_true")
    parser.add_argument("--seed", type=int)
    parser.add_argument(
        "--data-collection",
        choices=("allow", "deny"),
        default="deny",
    )
    return parser


def _key(path: Path) -> str:
    if not path.is_file():
        raise OpenRouterHierarchicalNoteJsonExperimentError("API key file is absent")
    values = _KEY.findall(path.read_text(encoding="utf-8"))
    if len(values) != 1 or len(values[0]) < 20:
        raise OpenRouterHierarchicalNoteJsonExperimentError(
            "API key file must contain exactly one OpenRouter key"
        )
    return values[0]


def _image(args: argparse.Namespace) -> tuple[bytes, str, dict[str, Any]]:
    if args.image is not None:
        payload = args.image.read_bytes()
        if payload.startswith(_PNG):
            media_type = "image/png"
        elif payload.startswith(b"\xff\xd8"):
            media_type = "image/jpeg"
        else:
            raise OpenRouterHierarchicalNoteJsonExperimentError("input image must be PNG or JPEG")
        return (
            payload,
            media_type,
            {
                "input_kind": "IMAGE",
                "logical_name": args.image.name,
                "physical_page": args.physical_page,
            },
        )
    if args.physical_page is None or args.physical_page <= 0:
        raise OpenRouterHierarchicalNoteJsonExperimentError(
            "--pdf requires one positive --physical-page"
        )
    if args.dpi < 72 or args.dpi > 400:
        raise OpenRouterHierarchicalNoteJsonExperimentError("render DPI must be between 72 and 400")
    with fitz.open(args.pdf) as document:
        if args.physical_page > document.page_count:
            raise OpenRouterHierarchicalNoteJsonExperimentError(
                "physical page lies outside the PDF"
            )
        page = document.load_page(args.physical_page - 1)
        payload = page.get_pixmap(dpi=args.dpi, alpha=False).tobytes("png")
    return (
        payload,
        "image/png",
        {
            "input_kind": "PDF_PAGE_RENDER",
            "logical_name": args.pdf.name,
            "physical_page": args.physical_page,
            "render_dpi": args.dpi,
        },
    )


def _call(
    *,
    api_key: str,
    image: bytes,
    media_type: str,
    model: str,
    prompt: str,
    response_schema: dict[str, Any],
    provider: str,
    quantization: str | None,
    response_mode: str,
    omit_reasoning: bool,
    reasoning_effort: str | None,
    omit_temperature: bool,
    seed: int | None,
    data_collection: str,
    max_output_tokens: int,
    timeout_seconds: int,
) -> tuple[bytes, float]:
    response_format: dict[str, Any]
    if response_mode == "json_schema":
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "hierarchical_note_tables",
                "strict": True,
                "schema": response_schema,
            },
        }
    else:
        response_format = {"type": "json_object"}
    body = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:"
                            + media_type
                            + ";base64,"
                            + base64.b64encode(image).decode("ascii")
                        },
                    },
                ],
            }
        ],
        "max_tokens": max_output_tokens,
        "response_format": response_format,
        "provider": {
            "allow_fallbacks": False,
            "data_collection": data_collection,
            "only": [provider],
            "require_parameters": True,
            **({"quantizations": [quantization]} if quantization is not None else {}),
        },
    }
    if not omit_temperature:
        body["temperature"] = 0
    if seed is not None:
        body["seed"] = seed
    if reasoning_effort is not None:
        body["reasoning"] = {"effort": reasoning_effort}
    elif not omit_reasoning:
        body["reasoning"] = {"enabled": False}
    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
            "X-OpenRouter-Title": "bctc-ai bounded hierarchical note JSON benchmark",
        },
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        try:
            error = json.loads(exc.read()).get("error", {})
            detail = f"{error.get('code')!r}:{error.get('message')!r}"
        except (json.JSONDecodeError, AttributeError, UnicodeDecodeError):
            detail = "unavailable"
        raise OpenRouterHierarchicalNoteJsonExperimentError(
            f"provider HTTP status {exc.code}; detail={detail}"
        ) from exc
    except (
        TimeoutError,
        urllib.error.URLError,
        ConnectionError,
        http.client.HTTPException,
    ) as exc:
        raise OpenRouterHierarchicalNoteJsonExperimentError(
            "provider request failed or timed out"
        ) from exc
    return raw, time.perf_counter() - started


def _response(value: Any) -> tuple[str, dict[str, Any]]:
    if type(value) is not dict or type(value.get("choices")) is not list:
        raise OpenRouterHierarchicalNoteJsonExperimentError("provider response has no choices")
    if len(value["choices"]) != 1 or type(value["choices"][0]) is not dict:
        raise OpenRouterHierarchicalNoteJsonExperimentError(
            "provider response must contain exactly one choice"
        )
    choice = value["choices"][0]
    if choice.get("finish_reason") != "stop":
        raise OpenRouterHierarchicalNoteJsonExperimentError(
            f"provider finish reason is {choice.get('finish_reason')!r}"
        )
    message = choice.get("message")
    if type(message) is not dict or type(message.get("content")) is not str:
        raise OpenRouterHierarchicalNoteJsonExperimentError("provider response has no text content")
    usage = value.get("usage")
    required = {"prompt_tokens", "completion_tokens", "total_tokens", "cost"}
    if type(usage) is not dict or not required.issubset(usage):
        raise OpenRouterHierarchicalNoteJsonExperimentError(
            "provider response has no complete usage accounting"
        )
    if any(type(usage[key]) is not int for key in required - {"cost"}):
        raise OpenRouterHierarchicalNoteJsonExperimentError("provider token accounting drifted")
    if type(usage["cost"]) not in {int, float}:
        raise OpenRouterHierarchicalNoteJsonExperimentError("provider cost accounting drifted")
    if usage["prompt_tokens"] + usage["completion_tokens"] != usage["total_tokens"]:
        raise OpenRouterHierarchicalNoteJsonExperimentError(
            "provider token accounting does not close"
        )
    provider = value.get("provider")
    model = value.get("model")
    if type(provider) is not str or type(model) is not str:
        raise OpenRouterHierarchicalNoteJsonExperimentError("provider or model identity is absent")
    return message["content"], usage


def _write(path: Path, payload: bytes) -> None:
    if path.exists():
        raise OpenRouterHierarchicalNoteJsonExperimentError(f"refusing to overwrite {path}")
    path.write_bytes(payload)


def main() -> int:
    args = _parser().parse_args()
    if args.omit_reasoning and args.reasoning_effort is not None:
        raise OpenRouterHierarchicalNoteJsonExperimentError(
            "--omit-reasoning and --reasoning-effort are mutually exclusive"
        )
    image, media_type, source = _image(args)
    prompt = build_hierarchical_note_json_prompt_v1()
    prompt_bytes = prompt.encode("utf-8")
    response_schema = hierarchical_note_json_response_schema_v1()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if any(args.output_dir.iterdir()):
        raise OpenRouterHierarchicalNoteJsonExperimentError("output directory must be empty")
    raw, elapsed = _call(
        api_key=_key(args.api_key_file),
        image=image,
        media_type=media_type,
        model=args.model,
        prompt=prompt,
        response_schema=response_schema,
        provider=args.provider,
        quantization=args.quantization,
        response_mode=args.response_mode,
        omit_reasoning=args.omit_reasoning,
        reasoning_effort=args.reasoning_effort,
        omit_temperature=args.omit_temperature,
        seed=args.seed,
        data_collection=args.data_collection,
        max_output_tokens=args.max_output_tokens,
        timeout_seconds=args.timeout_seconds,
    )
    try:
        response = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OpenRouterHierarchicalNoteJsonExperimentError(
            "provider response is not JSON"
        ) from exc
    raw_response_bytes = raw + (b"" if raw.endswith(b"\n") else b"\n")
    _write(args.output_dir / "raw-response.json", raw_response_bytes)
    text, usage = _response(response)
    output = decode_hierarchical_note_json_text_v1(text)
    output_bytes = canonical_json_bytes_v1(output) + b"\n"
    material = {
        "elapsed_seconds": format(elapsed, ".3f"),
        "format_version": FORMAT_VERSION,
        "input": {
            "image_ref": {
                "media_type": media_type,
                "sha256": sha256(image).hexdigest(),
                "size_bytes": len(image),
            },
            "generation_policy": {
                "max_output_tokens": args.max_output_tokens,
                "reasoning": (
                    "OMITTED"
                    if args.omit_reasoning
                    else (
                        "DISABLED"
                        if args.reasoning_effort is None
                        else "EFFORT_" + args.reasoning_effort.upper()
                    )
                ),
                "temperature": None if args.omit_temperature else 0,
                "seed": args.seed,
            },
            "model": args.model,
            "prompt_sha256": sha256(prompt_bytes).hexdigest(),
            "provider_policy": {
                "allow_fallbacks": False,
                "data_collection": args.data_collection,
                "only": [args.provider],
                "quantizations": ([args.quantization] if args.quantization is not None else None),
                "require_parameters": True,
            },
            "response_schema_sha256": canonical_json_sha256_v1(response_schema),
            "response_mode": args.response_mode,
            "source": source,
        },
        "model_output": output,
        "model_output_ref": {
            "sha256": sha256(output_bytes).hexdigest(),
            "size_bytes": len(output_bytes),
        },
        "provider": {
            "model": response["model"],
            "name": response["provider"],
            "response_id_sha256": sha256(response["id"].encode("utf-8")).hexdigest(),
        },
        "raw_response_ref": {
            "sha256": sha256(raw_response_bytes).hexdigest(),
            "size_bytes": len(raw_response_bytes),
        },
        "usage": usage,
    }
    observation = {
        **material,
        "observation_id": "orhnjv1:observation:" + canonical_json_sha256_v1(material),
    }
    _write(args.output_dir / "prompt.txt", prompt_bytes)
    _write(args.output_dir / "hierarchy.json", output_bytes)
    _write(
        args.output_dir / "observation.json",
        canonical_json_bytes_v1(observation) + b"\n",
    )
    print(
        json.dumps(
            {
                "cost_usd": usage["cost"],
                "elapsed_seconds": round(elapsed, 3),
                "input_tokens": usage["prompt_tokens"],
                "model": response["model"],
                "output_tokens": usage["completion_tokens"],
                "provider": response["provider"],
                "status": output["status"],
                "table_count": len(output["tables"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
