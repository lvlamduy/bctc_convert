#!/usr/bin/env python3
"""Run the bounded hosted multimodal page-to-hierarchical-JSON experiment."""

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

_MODELS = (
    "gemini-2.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemma-4-26b-a4b-it",
    "gemma-4-31b-it",
)
_KEY = re.compile(
    r"^\s*GEMINI_API_KEY\s*=\s*[\"']([^\"'\r\n]+)[\"']\s*$",
    re.MULTILINE,
)
_PNG = b"\x89PNG\r\n\x1a\n"


class HostedGemma4ExperimentError(RuntimeError):
    pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--image", type=Path)
    source.add_argument("--pdf", type=Path)
    parser.add_argument("--physical-page", type=int)
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument("--model", action="append", choices=_MODELS)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--api-key-file", type=Path, default=ROOT / "docs/experiments/gemma.txt")
    parser.add_argument("--api-key-index", type=int, default=0)
    parser.add_argument("--timeout-seconds", type=int, default=240)
    parser.add_argument("--max-output-tokens", type=int, default=8192)
    parser.add_argument(
        "--response-schema",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    return parser


def _keys(path: Path) -> list[str]:
    if not path.is_file():
        raise HostedGemma4ExperimentError("API key file is absent")
    values: list[str] = []
    for value in _KEY.findall(path.read_text(encoding="utf-8")):
        if (
            len(value) >= 20
            and not any(character.isspace() for character in value)
            and value not in values
        ):
            values.append(value)
    if not values:
        raise HostedGemma4ExperimentError("API key file contains no Gemini API key")
    return values


def _image(args: argparse.Namespace) -> tuple[bytes, str, dict[str, Any]]:
    if args.image is not None:
        payload = args.image.read_bytes()
        if payload.startswith(_PNG):
            media_type = "image/png"
        elif payload.startswith(b"\xff\xd8"):
            media_type = "image/jpeg"
        else:
            raise HostedGemma4ExperimentError("input image must be PNG or JPEG")
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
        raise HostedGemma4ExperimentError("--pdf requires one positive --physical-page")
    if args.dpi < 72 or args.dpi > 400:
        raise HostedGemma4ExperimentError("render DPI must be between 72 and 400")
    with fitz.open(args.pdf) as document:
        if args.physical_page > document.page_count:
            raise HostedGemma4ExperimentError("physical page lies outside the PDF")
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


def _response_text(value: Any) -> tuple[str, str, str]:
    if type(value) is not dict or type(value.get("candidates")) is not list:
        raise HostedGemma4ExperimentError("provider response has no candidate array")
    if len(value["candidates"]) != 1 or type(value["candidates"][0]) is not dict:
        raise HostedGemma4ExperimentError("provider response must contain exactly one candidate")
    candidate = value["candidates"][0]
    finish_reason = candidate.get("finishReason")
    if finish_reason != "STOP":
        raise HostedGemma4ExperimentError(f"provider finish reason is {finish_reason!r}")
    content = candidate.get("content")
    if type(content) is not dict or type(content.get("parts")) is not list:
        raise HostedGemma4ExperimentError("provider candidate has no content parts")
    text_parts = [part.get("text") for part in content["parts"] if type(part) is dict]
    if not text_parts or any(type(part) is not str for part in text_parts):
        raise HostedGemma4ExperimentError("provider candidate contains no complete text output")
    response_id = value.get("responseId")
    model_version = value.get("modelVersion")
    if type(response_id) is not str or not response_id:
        raise HostedGemma4ExperimentError("provider response ID is absent")
    if type(model_version) is not str or not model_version:
        raise HostedGemma4ExperimentError("provider model version is absent")
    return "".join(text_parts), response_id, model_version


def _usage(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise HostedGemma4ExperimentError("provider usage metadata is absent")
    required = {"promptTokenCount", "candidatesTokenCount", "totalTokenCount"}
    if not required.issubset(value) or any(type(value[key]) is not int for key in required):
        raise HostedGemma4ExperimentError("provider usage token counts drifted")
    if value["promptTokenCount"] + value["candidatesTokenCount"] != value["totalTokenCount"]:
        raise HostedGemma4ExperimentError("provider usage token equation does not close")
    return value


def _call(
    *,
    api_key: str,
    model: str,
    image: bytes,
    media_type: str,
    prompt: str,
    response_schema: dict[str, Any] | None,
    max_output_tokens: int,
    timeout_seconds: int,
) -> tuple[bytes, float]:
    if model.startswith("gemini-2.5-"):
        thinking_config = {"thinkingBudget": 0}
    else:
        thinking_config = {"thinkingLevel": "MINIMAL"}
    generation_config: dict[str, Any] = {
        "maxOutputTokens": max_output_tokens,
        "responseMimeType": "application/json",
        "temperature": 0,
        "thinkingConfig": thinking_config,
    }
    if response_schema is not None:
        generation_config["responseJsonSchema"] = response_schema
    body = {
        "contents": [
            {
                "parts": [
                    {
                        "inlineData": {
                            "data": base64.b64encode(image).decode("ascii"),
                            "mimeType": media_type,
                        }
                    },
                    {"text": prompt},
                ],
                "role": "user",
            }
        ],
        "generationConfig": generation_config,
    }
    request = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        # Do not include response bodies: provider errors can echo request metadata.
        raise HostedGemma4ExperimentError(f"provider HTTP status {exc.code}") from exc
    except (TimeoutError, urllib.error.URLError, ConnectionError, http.client.HTTPException) as exc:
        raise HostedGemma4ExperimentError("provider request failed or timed out") from exc
    return raw, time.perf_counter() - started


def _write(path: Path, payload: bytes) -> None:
    if path.exists():
        raise HostedGemma4ExperimentError(f"refusing to overwrite {path}")
    path.write_bytes(payload)


def main() -> int:
    args = _parser().parse_args()
    models = args.model or ["gemini-2.5-flash-lite"]
    if args.api_key_index < 0:
        raise HostedGemma4ExperimentError("API key index must be nonnegative")
    keys = _keys(args.api_key_file)
    if args.api_key_index >= len(keys):
        raise HostedGemma4ExperimentError("API key index lies outside the discovered key slots")
    image, media_type, source = _image(args)
    prompt = build_hierarchical_note_json_prompt_v1()
    response_schema = hierarchical_note_json_response_schema_v1() if args.response_schema else None
    args.output_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = args.output_dir / "prompt.txt"
    prompt_bytes = prompt.encode("utf-8")
    if not prompt_path.exists():
        prompt_path.write_bytes(prompt_bytes)
    elif prompt_path.read_bytes() != prompt_bytes:
        raise HostedGemma4ExperimentError("output directory contains a different prompt")
    for model in models:
        thinking_config = (
            {"thinking_budget": 0}
            if model.startswith("gemini-2.5-")
            else {"thinking_level": "MINIMAL"}
        )
        settings = {
            "max_output_tokens": args.max_output_tokens,
            "response_mime_type": "application/json",
            "response_schema_sha256": (
                canonical_json_sha256_v1(response_schema) if response_schema is not None else None
            ),
            "temperature": 0,
            **thinking_config,
        }
        model_dir = args.output_dir / model
        observation_path = model_dir / "observation.json"
        if observation_path.exists():
            print(f"{model}: cached {observation_path}")
            continue
        if model_dir.exists() and any(model_dir.iterdir()):
            raise HostedGemma4ExperimentError(
                f"model output directory is nonempty; use a new directory: {model_dir}"
            )
        model_dir.mkdir(parents=True, exist_ok=True)
        raw, elapsed = _call(
            api_key=keys[args.api_key_index],
            model=model,
            image=image,
            media_type=media_type,
            prompt=prompt,
            response_schema=response_schema,
            max_output_tokens=args.max_output_tokens,
            timeout_seconds=args.timeout_seconds,
        )
        try:
            response = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise HostedGemma4ExperimentError("provider response is not JSON") from exc
        text, response_id, model_version = _response_text(response)
        output = decode_hierarchical_note_json_text_v1(text)
        usage = _usage(response.get("usageMetadata"))
        raw_response_bytes = raw + (b"" if raw.endswith(b"\n") else b"\n")
        output_bytes = canonical_json_bytes_v1(output) + b"\n"
        input_material = {
            "format_version": FORMAT_VERSION,
            "image_ref": {
                "media_type": media_type,
                "sha256": sha256(image).hexdigest(),
                "size_bytes": len(image),
            },
            "model": model,
            "prompt_sha256": sha256(prompt_bytes).hexdigest(),
            "settings": settings,
            "source": source,
        }
        material = {
            "elapsed_seconds": format(elapsed, ".3f"),
            "format_version": FORMAT_VERSION,
            "input": input_material,
            "model_output": output,
            "model_output_ref": {
                "sha256": sha256(output_bytes).hexdigest(),
                "size_bytes": len(output_bytes),
            },
            "provider": {
                "model_version": model_version,
                "response_id_sha256": sha256(response_id.encode("utf-8")).hexdigest(),
            },
            "raw_response_ref": {
                "sha256": sha256(raw_response_bytes).hexdigest(),
                "size_bytes": len(raw_response_bytes),
            },
            "usage": usage,
        }
        observation = {
            **material,
            "observation_id": "hgnjv1:observation:" + canonical_json_sha256_v1(material),
        }
        _write(model_dir / "raw-response.json", raw_response_bytes)
        _write(model_dir / "hierarchy.json", output_bytes)
        _write(observation_path, canonical_json_bytes_v1(observation) + b"\n")
        print(
            json.dumps(
                {
                    "elapsed_seconds": round(elapsed, 3),
                    "model": model,
                    "observation_id": observation["observation_id"],
                    "output_tokens": usage["candidatesTokenCount"],
                    "status": output["status"],
                    "table_count": len(output["tables"]),
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
