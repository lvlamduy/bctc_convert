"""Offline schema-blind challenger; content hashes bind bytes, never authority."""

from __future__ import annotations

import base64
import json
import re
import struct
import unicodedata
from collections.abc import Mapping
from hashlib import sha256
from types import MappingProxyType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FORMAT_VERSION = "MULTIMODAL_RESCUE_CHALLENGER_V1"
ATTEMPT_FORMAT_VERSION = "MULTIMODAL_RESCUE_CHALLENGER_ATTEMPT_V1"
_CLAIM_BOUNDARY = (
    "CALLER_AUTHENTICATED_REGION_STRUCTURE_CHALLENGER_ONLY_OFFLINE_CONTRACT_"
    "NO_PROVIDER_CALL_CREDENTIAL_UPLOAD_OR_SOURCE_MAPPING_VALUE_ABSENCE_AUTHORITY"
)
_PAGE_PROMPT = (
    "Read only source-visible text and page structure from the supplied authenticated image. "
    "Preserve every character exactly. Do not correct digits, infer missing content, calculate, "
    "map, classify against downstream taxonomies, or supply answers not visible there. Return the "
    "closed JSON shape supplied in output_contract. Coordinates are integer pixels in the "
    "supplied image."
)
_CROP_TEXT_PROMPT = (
    "Transcribe only the source-visible text in this authenticated crop. Preserve every "
    "character exactly; do not correct, infer, classify, map, or calculate. Return exactly "
    '{"text":"raw source surface"}.'
)
_CROP_NUMERIC_PROMPT = (
    "Transcribe only the source-visible numeric surface in this authenticated crop, including "
    "punctuation, parentheses, signs, dashes, and spacing. Do not parse, correct, infer, map, or "
    'calculate. Return exactly {"text":"raw source surface"}.'
)
_PAGE_OUTPUT_CONTRACT = {
    "blocks": {
        "fields": "bbox kind ordinal raw_text".split(),
        "kinds": "HEADING TABLE TEXT".split(),
        "ordinal": "ZERO_BASED_CONTIGUOUS",
    },
    "root_fields": ["blocks", "tables"],
    "tables": {
        "cell_fields": "bbox column_span column_start ordinal raw_text row_span row_start".split(),
        "fields": "bbox cells ordinal".split(),
        "ordinal": "ZERO_BASED_CONTIGUOUS",
    },
}
_CROP_OUTPUT_CONTRACT = {"root_fields": ["text"]}
_PROMPTS = {
    "CROP_NUMERIC": _CROP_NUMERIC_PROMPT,
    "CROP_TEXT": _CROP_TEXT_PROMPT,
    "PAGE_STRUCTURE": _PAGE_PROMPT,
}
_OUTPUT_CONTRACTS = {
    "CROP_NUMERIC": _CROP_OUTPUT_CONTRACT,
    "CROP_TEXT": _CROP_OUTPUT_CONTRACT,
    "PAGE_STRUCTURE": _PAGE_OUTPUT_CONTRACT,
}
_AUTHORITY = dict.fromkeys(
    "absence accounting export family geometry mapping numeric period schema source_text structure unit".split(),
    False,
)
_AUTHORITY = {f"{key}_authority": value for key, value in _AUTHORITY.items()}
OUTPUT_AUTHORITY: Mapping[str, bool] = MappingProxyType(_AUTHORITY)
_TRIGGERS = {"LAYOUT_SIGNATURE_NEW", "UNRESOLVED_AFTER_PRIMARY"}
_MODES = set(_PROMPTS)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ATTEMPT_ID = re.compile(r"^mmrcv1:attempt:[0-9a-f]{64}$")
_DECIMAL = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
_IDENTIFIER_LEAK = re.compile(
    r"(?i)(?:\breport[\s_-]*norm[\s_-]*id\b|"
    r"\b(?:family|schema)[\s_-]*(?:id|identifier)\b\s*[:=#])"
)
_REF_FIELDS = {"logical_id", "sha256", "size_bytes"}
_REGION_FIELDS = set(
    "authentication_receipt_ref authentication_state image_media_type image_pixel_height image_pixel_width image_ref mode primary_outcome_ref proposed_render_pixel_bbox recognition_render_pixel_bbox region_artifact_ref region_id render_dpi render_ref selection_reason source_region_format_version source_to_render_affine".split()
)
_MODEL_FIELDS = set("max_output_tokens model_ref name settings_ref temperature version".split())
_PLAN_FIELDS = set(
    "authority claim_boundary credentials_accessed external_upload_authorized format_version mode model network_call_performed output_contract_ref plan_id prompt_ref region request_body_ref state trigger".split()
)
_ATTEMPT_FIELDS = set(
    "attempt_id attempt_ordinal authority claim_boundary format_version lineage model_ref output output_ref plan_id raw_response_ref request_body_ref request_id response_id state".split()
)


class MultimodalRescueChallengerV1Error(ValueError):
    pass


def _error(message: str) -> MultimodalRescueChallengerV1Error:
    return MultimodalRescueChallengerV1Error(message)


def _exact_dict(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise _error(f"{label} fields drifted")
    return value


def _string(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or not value
        or "\r" in value
        or "\n" in value
        or value != unicodedata.normalize("NFC", value)
        or _IDENTIFIER_LEAK.search(value)
    ):
        raise _error(f"{label} must be one identifier-free NFC line")
    return value


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be one positive exact integer")
    return value


def _ref(value: Any, label: str) -> dict[str, Any]:
    _exact_dict(value, _REF_FIELDS, label)
    _string(value["logical_id"], f"{label}.logical_id")
    if type(value["sha256"]) is not str or _SHA256.fullmatch(value["sha256"]) is None:
        raise _error(f"{label}.sha256 must be lowercase SHA-256")
    _positive_int(value["size_bytes"], f"{label}.size_bytes")
    return canonical_clone_v1(value)


def _derived_ref(logical_id: str, payload: bytes) -> dict[str, Any]:
    return {
        "logical_id": logical_id,
        "sha256": sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _bbox(value: Any, *, width: int, height: int, label: str) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or not (0 <= value[0] < value[2] <= width and 0 <= value[1] < value[3] <= height)
    ):
        raise _error(f"{label} must be one positive integer bbox inside its image")
    return list(value)


def _region(value: Any) -> dict[str, Any]:
    _exact_dict(value, _REGION_FIELDS, "authenticated region binding")
    if value["authentication_state"] != "CALLER_AUTHENTICATED_CURRENT_REGION":
        raise _error("region is not caller-authenticated and current")
    if value["selection_reason"] not in _TRIGGERS:
        raise _error("rescue trigger must be unresolved-after-primary or new-layout only")
    if value["mode"] not in _MODES:
        raise _error("multimodal rescue mode drifted")
    for key in ("region_id", "source_region_format_version"):
        _string(value[key], f"region.{key}")
    if value["image_media_type"] != "image/png":
        raise _error("multimodal rescue image must be exact PNG")
    width = _positive_int(value["image_pixel_width"], "region image width")
    height = _positive_int(value["image_pixel_height"], "region image height")
    _positive_int(value["render_dpi"], "region render DPI")
    for key in (
        "authentication_receipt_ref",
        "image_ref",
        "primary_outcome_ref",
        "region_artifact_ref",
    ):
        _ref(value[key], f"region.{key}")
    render = _exact_dict(
        value["render_ref"], _REF_FIELDS | {"pixel_height", "pixel_width"}, "render ref"
    )
    _ref({key: render[key] for key in _REF_FIELDS}, "render ref")
    render_width = _positive_int(render["pixel_width"], "render width")
    render_height = _positive_int(render["pixel_height"], "render height")
    proposed = _bbox(
        value["proposed_render_pixel_bbox"],
        width=render_width,
        height=render_height,
        label="proposed render bbox",
    )
    recognition = _bbox(
        value["recognition_render_pixel_bbox"],
        width=render_width,
        height=render_height,
        label="recognition render bbox",
    )
    if not (
        proposed[0] <= recognition[0] < recognition[2] <= proposed[2]
        and proposed[1] <= recognition[1] < recognition[3] <= proposed[3]
    ):
        raise _error("recognition bbox lies outside the proposed authenticated region")
    affine = value["source_to_render_affine"]
    if (
        type(affine) is not list
        or len(affine) != 6
        or any(type(item) is not str or _DECIMAL.fullmatch(item) is None for item in affine)
    ):
        raise _error("source-to-render affine must contain six canonical decimal strings")
    if width > render_width or height > render_height:
        raise _error("region image dimensions exceed the authenticated render")
    return canonical_clone_v1(value)


def _image_bytes(region: Mapping[str, Any], payload: bytes) -> bytes:
    if (
        type(payload) is not bytes
        or len(payload) < 24
        or not payload.startswith(b"\x89PNG\r\n\x1a\n")
    ):
        raise _error("region image must be exact PNG bytes")
    reference = region["image_ref"]
    if (
        len(payload) != reference["size_bytes"]
        or sha256(payload).hexdigest() != reference["sha256"]
    ):
        raise _error("region image bytes differ from their exact content ref")
    dimensions = (region["image_pixel_width"], region["image_pixel_height"])
    if payload[12:16] != b"IHDR" or struct.unpack(">II", payload[16:24]) != dimensions:
        raise _error("region PNG dimensions drifted")
    return payload


def _model(value: Any, mode: str) -> dict[str, Any]:
    _exact_dict(value, _MODEL_FIELDS, "model profile")
    _string(value["name"], "model name")
    _string(value["version"], "model version")
    if type(value["temperature"]) is not int or value["temperature"] != 0:
        raise _error("model temperature must be exact integer zero")
    token_cap = 4_096 if mode == "PAGE_STRUCTURE" else 128
    if _positive_int(value["max_output_tokens"], "max output tokens") > token_cap:
        raise _error(f"max output tokens exceeds the {mode} bounded-cost gate")
    _ref(value["model_ref"], "model ref")
    settings_ref = _ref(value["settings_ref"], "settings ref")
    settings = {"max_output_tokens": value["max_output_tokens"], "temperature": 0}
    if settings_ref != _derived_ref("multimodal/settings-v1", canonical_json_bytes_v1(settings)):
        raise _error("settings ref does not bind the exact closed settings")
    return canonical_clone_v1(value)


def _request_payload(region: dict[str, Any], model: dict[str, Any], image: bytes) -> dict[str, Any]:
    mode = region["mode"]
    return {
        "format_version": FORMAT_VERSION,
        "geometry": {
            "proposed_render_pixel_bbox": region["proposed_render_pixel_bbox"],
            "recognition_render_pixel_bbox": region["recognition_render_pixel_bbox"],
            "render_dpi": region["render_dpi"],
            "render_ref": region["render_ref"],
            "source_to_render_affine": region["source_to_render_affine"],
        },
        "image": {
            "base64": base64.b64encode(image).decode("ascii"),
            "media_type": region["image_media_type"],
            "ref": region["image_ref"],
        },
        "mode": mode,
        "model": model,
        "output_contract": _OUTPUT_CONTRACTS[mode],
        "prompt": _PROMPTS[mode],
    }


def build_multimodal_rescue_plan_v1(
    *,
    region: Mapping[str, Any],
    region_image_bytes: bytes,
    trigger: str,
    model_name: str,
    model_version: str,
    model_ref: Mapping[str, Any],
    max_output_tokens: int,
) -> tuple[dict[str, Any], bytes]:
    checked_region = _region(region)
    image = _image_bytes(checked_region, region_image_bytes)
    settings = {"max_output_tokens": max_output_tokens, "temperature": 0}
    mode = checked_region["mode"]
    model = _model(
        {
            "max_output_tokens": max_output_tokens,
            "model_ref": canonical_clone_v1(model_ref),
            "name": model_name,
            "settings_ref": _derived_ref(
                "multimodal/settings-v1", canonical_json_bytes_v1(settings)
            ),
            "temperature": 0,
            "version": model_version,
        },
        mode,
    )
    if trigger != checked_region["selection_reason"] or trigger not in _TRIGGERS:
        raise _error("plan trigger does not bind the authenticated primary outcome")
    request_body = canonical_json_bytes_v1(_request_payload(checked_region, model, image))
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": _CLAIM_BOUNDARY,
        "credentials_accessed": False,
        "external_upload_authorized": False,
        "format_version": FORMAT_VERSION,
        "mode": mode,
        "model": model,
        "network_call_performed": False,
        "output_contract_ref": _derived_ref(
            f"multimodal/{mode.lower()}/output-contract-v1",
            canonical_json_bytes_v1(_OUTPUT_CONTRACTS[mode]),
        ),
        "prompt_ref": _derived_ref(f"multimodal/{mode.lower()}/prompt-v1", _PROMPTS[mode].encode()),
        "region": checked_region,
        "request_body_ref": _derived_ref("multimodal/request-body-v1", request_body),
        "state": "PLANNED_NOT_EXECUTED",
        "trigger": trigger,
    }
    plan = {**material, "plan_id": "mmrcv1:plan:" + canonical_json_sha256_v1(material)}
    validate_multimodal_rescue_plan_v1(
        plan, region_image_bytes=image, request_body_bytes=request_body
    )
    return plan, request_body


def validate_multimodal_rescue_plan_v1(
    value: Any, *, region_image_bytes: bytes, request_body_bytes: bytes
) -> dict[str, Any]:
    _exact_dict(value, _PLAN_FIELDS, "multimodal rescue plan")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != _CLAIM_BOUNDARY
        or value["state"] != "PLANNED_NOT_EXECUTED"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or value["network_call_performed"] is not False
        or value["credentials_accessed"] is not False
        or value["external_upload_authorized"] is not False
    ):
        raise _error("plan offline or authority boundary drifted")
    region = _region(value["region"])
    if value["mode"] not in _MODES or value["mode"] != region["mode"]:
        raise _error("plan mode does not bind the authenticated region mode")
    mode = value["mode"]
    model = _model(value["model"], mode)
    if value["trigger"] not in _TRIGGERS or value["trigger"] != region["selection_reason"]:
        raise _error("plan trigger is not an eligible authenticated primary outcome")
    image = _image_bytes(region, region_image_bytes)
    expected_body = canonical_json_bytes_v1(_request_payload(region, model, image))
    if type(request_body_bytes) is not bytes or request_body_bytes != expected_body:
        raise _error("request body is not the exact fixed schema-blind body")
    expected_refs = {
        "output_contract_ref": _derived_ref(
            f"multimodal/{mode.lower()}/output-contract-v1",
            canonical_json_bytes_v1(_OUTPUT_CONTRACTS[mode]),
        ),
        "prompt_ref": _derived_ref(f"multimodal/{mode.lower()}/prompt-v1", _PROMPTS[mode].encode()),
        "request_body_ref": _derived_ref("multimodal/request-body-v1", expected_body),
    }
    for key, expected in expected_refs.items():
        if _ref(value[key], key) != expected:
            raise _error(f"{key} does not bind its exact bytes")
    material = {key: canonical_clone_v1(item) for key, item in value.items() if key != "plan_id"}
    if value["plan_id"] != "mmrcv1:plan:" + canonical_json_sha256_v1(material):
        raise _error("plan ID does not bind the complete offline plan")
    return canonical_clone_v1(value)


def _strict_response(payload: bytes) -> dict[str, Any]:
    if type(payload) is not bytes or not payload or len(payload) > 16 * 1024 * 1024:
        raise _error("raw response must be nonempty bounded exact bytes")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in items:
            if key in result:
                raise _error(f"raw response contains duplicate key {key!r}")
            result[key] = item
        return result

    def nonfinite(token: str) -> None:
        raise _error(f"raw response contains non-finite number {token}")

    try:
        value = json.loads(
            payload.decode("utf-8"), object_pairs_hook=pairs, parse_constant=nonfinite
        )
    except MultimodalRescueChallengerV1Error:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("raw response is not strict UTF-8 JSON") from exc
    fields = {
        "finish_reason",
        "model",
        "output",
        "request_body_sha256",
        "request_id",
        "response_id",
    }
    return _exact_dict(value, fields, "raw response")


def _raw_text(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or value != unicodedata.normalize("NFC", value)
        or _IDENTIFIER_LEAK.search(value)
    ):
        raise _error(f"{label} is not one identifier-free NFC raw string")
    return value


def _page_output(value: Any, *, width: int, height: int) -> dict[str, Any]:
    _exact_dict(value, {"blocks", "tables"}, "challenger output")
    if type(value["blocks"]) is not list or type(value["tables"]) is not list:
        raise _error("challenger output blocks/tables must be arrays")
    for ordinal, block in enumerate(value["blocks"]):
        _exact_dict(block, {"bbox", "kind", "ordinal", "raw_text"}, "output block")
        if (
            type(block["ordinal"]) is not int
            or block["ordinal"] != ordinal
            or type(block["kind"]) is not str
            or block["kind"] not in {"HEADING", "TABLE", "TEXT"}
        ):
            raise _error("output block ordinal or kind drifted")
        _bbox(block["bbox"], width=width, height=height, label="output block bbox")
        _raw_text(block["raw_text"], "output block raw_text")
    for ordinal, table in enumerate(value["tables"]):
        _exact_dict(table, {"bbox", "cells", "ordinal"}, "output table")
        if (
            type(table["ordinal"]) is not int
            or table["ordinal"] != ordinal
            or type(table["cells"]) is not list
            or not table["cells"]
        ):
            raise _error("output table ordinal/cells drifted")
        _bbox(table["bbox"], width=width, height=height, label="output table bbox")
        for cell_ordinal, cell in enumerate(table["cells"]):
            fields = {
                "bbox",
                "column_span",
                "column_start",
                "ordinal",
                "raw_text",
                "row_span",
                "row_start",
            }
            _exact_dict(cell, fields, "output cell")
            if type(cell["ordinal"]) is not int or cell["ordinal"] != cell_ordinal:
                raise _error("output cell ordinal drifted")
            for key in ("column_start", "row_start"):
                if type(cell[key]) is not int or cell[key] < 0:
                    raise _error(f"output cell {key} drifted")
            for key in ("column_span", "row_span"):
                _positive_int(cell[key], f"output cell {key}")
            _bbox(cell["bbox"], width=width, height=height, label="output cell bbox")
            _raw_text(cell["raw_text"], "output cell raw_text")
    return canonical_clone_v1(value)


def _output(value: Any, *, mode: str, width: int, height: int) -> dict[str, Any]:
    if mode == "PAGE_STRUCTURE":
        return _page_output(value, width=width, height=height)
    _exact_dict(value, {"text"}, "crop challenger output")
    _raw_text(value["text"], "crop challenger raw text")
    return canonical_clone_v1(value)


def _response(payload: bytes, plan: Mapping[str, Any]) -> tuple[dict[str, Any], str, str]:
    response = _strict_response(payload)
    _exact_dict(response["model"], {"name", "version"}, "response model")
    if response["model"] != {"name": plan["model"]["name"], "version": plan["model"]["version"]}:
        raise _error("raw response model differs from the exact plan model")
    if response["finish_reason"] != "STOP":
        raise _error("raw response is not one complete STOP response")
    request_id = _string(response["request_id"], "response request ID")
    response_id = _string(response["response_id"], "response ID")
    if response["request_body_sha256"] != plan["request_body_ref"]["sha256"]:
        raise _error("raw response does not bind the exact request body")
    output = _output(
        response["output"],
        mode=plan["mode"],
        width=plan["region"]["image_pixel_width"],
        height=plan["region"]["image_pixel_height"],
    )
    return output, request_id, response_id


def _attempt_shape(value: Any, plan: Mapping[str, Any]) -> dict[str, Any]:
    _exact_dict(value, _ATTEMPT_FIELDS, "multimodal rescue attempt")
    if (
        value["format_version"] != ATTEMPT_FORMAT_VERSION
        or value["claim_boundary"] != _CLAIM_BOUNDARY
        or value["state"] != "CAPTURED_OFFLINE_CHALLENGER_ONLY"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or value["plan_id"] != plan["plan_id"]
        or not same_typed_json_v1(value["model_ref"], plan["model"]["model_ref"])
        or not same_typed_json_v1(value["request_body_ref"], plan["request_body_ref"])
    ):
        raise _error("attempt plan, state, model, request, or authority boundary drifted")
    ordinal = _positive_int(value["attempt_ordinal"], "attempt ordinal")
    if ordinal > 2:
        raise _error("multimodal rescue permits at most two attempts per plan")
    for key in ("model_ref", "output_ref", "raw_response_ref", "request_body_ref"):
        _ref(value[key], key)
    _string(value["request_id"], "attempt request ID")
    _string(value["response_id"], "attempt response ID")
    lineage_fields = {
        "independent_corroboration",
        "kind",
        "repeat_of_attempt_id",
        "same_model_repeat",
    }
    lineage = _exact_dict(value["lineage"], lineage_fields, "attempt lineage")
    if lineage["independent_corroboration"] is not False:
        raise _error("same-model output can never claim independent corroboration")
    initial = {
        "independent_corroboration": False,
        "kind": "INITIAL",
        "repeat_of_attempt_id": None,
        "same_model_repeat": False,
    }
    if ordinal == 1 and not same_typed_json_v1(lineage, initial):
        raise _error("initial attempt lineage drifted")
    if ordinal > 1 and (
        lineage["kind"] != "SAME_MODEL_REPEAT"
        or lineage["same_model_repeat"] is not True
        or type(lineage["repeat_of_attempt_id"]) is not str
        or _ATTEMPT_ID.fullmatch(lineage["repeat_of_attempt_id"]) is None
    ):
        raise _error("same-model repeat lineage drifted")
    material = {key: canonical_clone_v1(item) for key, item in value.items() if key != "attempt_id"}
    if value["attempt_id"] != "mmrcv1:attempt:" + canonical_json_sha256_v1(material):
        raise _error("attempt ID does not bind the complete capture")
    return canonical_clone_v1(value)


def _make_attempt(
    plan: dict[str, Any], raw_response_bytes: bytes, previous_attempt: Mapping[str, Any] | None
) -> dict[str, Any]:
    if previous_attempt is None:
        ordinal = 1
        previous = None
        lineage = {
            "independent_corroboration": False,
            "kind": "INITIAL",
            "repeat_of_attempt_id": None,
            "same_model_repeat": False,
        }
    else:
        previous = _attempt_shape(previous_attempt, plan)
        if previous["attempt_ordinal"] >= 2:
            raise _error("multimodal rescue permits only one same-model retry")
        ordinal = 2
        lineage = {
            "independent_corroboration": False,
            "kind": "SAME_MODEL_REPEAT",
            "repeat_of_attempt_id": previous["attempt_id"],
            "same_model_repeat": True,
        }
    output, request_id, response_id = _response(raw_response_bytes, plan)
    raw_ref = _derived_ref(f"multimodal/raw-response/{response_id}", raw_response_bytes)
    if previous is not None:
        if request_id == previous["request_id"] or response_id == previous["response_id"]:
            raise _error("same-model repeat must have fresh request and response IDs")
        if raw_ref == previous["raw_response_ref"]:
            raise _error("same-model repeat must bind a distinct raw response")
    material = {
        "attempt_ordinal": ordinal,
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": _CLAIM_BOUNDARY,
        "format_version": ATTEMPT_FORMAT_VERSION,
        "lineage": lineage,
        "model_ref": canonical_clone_v1(plan["model"]["model_ref"]),
        "output": output,
        "output_ref": _derived_ref("multimodal/closed-output-v1", canonical_json_bytes_v1(output)),
        "plan_id": plan["plan_id"],
        "raw_response_ref": raw_ref,
        "request_body_ref": canonical_clone_v1(plan["request_body_ref"]),
        "request_id": request_id,
        "response_id": response_id,
        "state": "CAPTURED_OFFLINE_CHALLENGER_ONLY",
    }
    return {**material, "attempt_id": "mmrcv1:attempt:" + canonical_json_sha256_v1(material)}


def build_multimodal_rescue_attempt_v1(
    *,
    plan: Mapping[str, Any],
    region_image_bytes: bytes,
    request_body_bytes: bytes,
    raw_response_bytes: bytes,
    previous_attempt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    checked_plan = validate_multimodal_rescue_plan_v1(
        plan, region_image_bytes=region_image_bytes, request_body_bytes=request_body_bytes
    )
    attempt = _make_attempt(checked_plan, raw_response_bytes, previous_attempt)
    _attempt_shape(attempt, checked_plan)
    return attempt


def validate_multimodal_rescue_attempt_v1(
    value: Any,
    *,
    plan: Mapping[str, Any],
    region_image_bytes: bytes,
    request_body_bytes: bytes,
    raw_response_bytes: bytes,
    previous_attempt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    checked_plan = validate_multimodal_rescue_plan_v1(
        plan, region_image_bytes=region_image_bytes, request_body_bytes=request_body_bytes
    )
    persisted = _attempt_shape(value, checked_plan)
    rebuilt = _make_attempt(checked_plan, raw_response_bytes, previous_attempt)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("multimodal rescue attempt does not replay exactly")
    return canonical_clone_v1(rebuilt)
