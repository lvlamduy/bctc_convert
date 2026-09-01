from __future__ import annotations

import base64
import copy
import io
import json
from hashlib import sha256

import pytest
from PIL import Image

from bctc_ai.evaluation.multimodal_rescue_challenger_v1 import (
    FORMAT_VERSION,
    OUTPUT_AUTHORITY,
    MultimodalRescueChallengerV1Error,
    build_multimodal_rescue_attempt_v1,
    build_multimodal_rescue_plan_v1,
    validate_multimodal_rescue_attempt_v1,
    validate_multimodal_rescue_plan_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)


def _png() -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (32, 24), "white").save(stream, format="PNG")
    return stream.getvalue()


def _ref(logical_id: str, payload: bytes = b"bound") -> dict[str, object]:
    return {
        "logical_id": logical_id,
        "sha256": sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _region(
    image: bytes,
    reason: str = "UNRESOLVED_AFTER_PRIMARY",
    mode: str = "PAGE_STRUCTURE",
) -> dict[str, object]:
    return {
        "authentication_receipt_ref": _ref("auth/region"),
        "authentication_state": "CALLER_AUTHENTICATED_CURRENT_REGION",
        "image_media_type": "image/png",
        "image_pixel_height": 24,
        "image_pixel_width": 32,
        "image_ref": _ref("image/region.png", image),
        "mode": mode,
        "primary_outcome_ref": _ref("primary/outcome"),
        "proposed_render_pixel_bbox": [10, 12, 70, 50],
        "recognition_render_pixel_bbox": [12, 14, 68, 48],
        "region_artifact_ref": _ref("region/artifact"),
        "region_id": "ffaprv1:region:" + "1" * 64,
        "render_dpi": 200,
        "render_ref": {
            **_ref("render/page.png"),
            "pixel_height": 80,
            "pixel_width": 100,
        },
        "selection_reason": reason,
        "source_region_format_version": "FAMILY_FIRST_AUTHENTICATED_PAGE_REGION_V1",
        "source_to_render_affine": ["2.777777", "0", "0", "2.777777", "0", "0"],
    }


def _plan(
    reason: str = "UNRESOLVED_AFTER_PRIMARY",
    mode: str = "PAGE_STRUCTURE",
    max_output_tokens: int | None = None,
):
    image = _png()
    if max_output_tokens is None:
        max_output_tokens = 4096 if mode == "PAGE_STRUCTURE" else 128
    plan, body = build_multimodal_rescue_plan_v1(
        region=_region(image, reason, mode),
        region_image_bytes=image,
        trigger=reason,
        model_name="multimodal-model",
        model_version="model-v1-pinned",
        model_ref=_ref("model/model-v1-pinned"),
        max_output_tokens=max_output_tokens,
    )
    return image, plan, body


def _output(raw_text: str = "Nợ trung hạn 1.234") -> dict[str, object]:
    return {
        "blocks": [{"bbox": [1, 1, 30, 10], "kind": "TEXT", "ordinal": 0, "raw_text": raw_text}],
        "tables": [
            {
                "bbox": [1, 10, 31, 23],
                "cells": [
                    {
                        "bbox": [2, 11, 30, 22],
                        "column_span": 1,
                        "column_start": 0,
                        "ordinal": 0,
                        "raw_text": "1.234",
                        "row_span": 1,
                        "row_start": 0,
                    }
                ],
                "ordinal": 0,
            }
        ],
    }


def _raw(plan, request_id: str = "request-1", response_id: str = "response-1", *, output=None):
    if output is None:
        output = _output() if plan["mode"] == "PAGE_STRUCTURE" else {"text": "1.234"}
    return json.dumps(
        {
            "finish_reason": "STOP",
            "model": {"name": plan["model"]["name"], "version": plan["model"]["version"]},
            "output": output,
            "request_body_sha256": plan["request_body_ref"]["sha256"],
            "request_id": request_id,
            "response_id": response_id,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()


def _rehash_plan(value):
    material = {key: canonical_clone_v1(item) for key, item in value.items() if key != "plan_id"}
    value["plan_id"] = "mmrcv1:plan:" + canonical_json_sha256_v1(material)


def _rehash_attempt(value):
    material = {key: canonical_clone_v1(item) for key, item in value.items() if key != "attempt_id"}
    value["attempt_id"] = "mmrcv1:attempt:" + canonical_json_sha256_v1(material)


def test_plan_is_offline_schema_blind_and_binds_exact_image_geometry_and_body() -> None:
    image, plan, body = _plan()
    assert plan["format_version"] == FORMAT_VERSION
    assert plan["mode"] == plan["region"]["mode"] == "PAGE_STRUCTURE"
    assert plan["state"] == "PLANNED_NOT_EXECUTED"
    assert plan["network_call_performed"] is False
    assert plan["credentials_accessed"] is False
    assert plan["external_upload_authorized"] is False
    assert OUTPUT_AUTHORITY and not any(OUTPUT_AUTHORITY.values())
    assert (
        validate_multimodal_rescue_plan_v1(plan, region_image_bytes=image, request_body_bytes=body)
        == plan
    )

    request = json.loads(body)
    assert request["mode"] == "PAGE_STRUCTURE"
    assert base64.b64decode(request["image"]["base64"]) == image
    assert request["geometry"] == {
        "proposed_render_pixel_bbox": [10, 12, 70, 50],
        "recognition_render_pixel_bbox": [12, 14, 68, 48],
        "render_dpi": 200,
        "render_ref": plan["region"]["render_ref"],
        "source_to_render_affine": ["2.777777", "0", "0", "2.777777", "0", "0"],
    }
    rendered = body.decode().lower()
    assert "reportnormid" not in rendered
    assert "family_id" not in rendered
    assert "schema_id" not in rendered
    assert "expected value" not in rendered


@pytest.mark.parametrize("reason", ["NOT_OBSERVED", "PRIMARY_ALREADY_RESOLVED", "ABSENT"])
def test_plan_rejects_absence_and_resolved_triggers(reason: str) -> None:
    image = _png()
    with pytest.raises(MultimodalRescueChallengerV1Error, match="trigger"):
        build_multimodal_rescue_plan_v1(
            region=_region(image, reason),
            region_image_bytes=image,
            trigger=reason,
            model_name="model",
            model_version="v1",
            model_ref=_ref("model/v1"),
            max_output_tokens=1024,
        )


def test_plan_rejects_image_body_geometry_and_coherent_self_rehash_tamper() -> None:
    image, plan, body = _plan()
    with pytest.raises(MultimodalRescueChallengerV1Error, match="image bytes"):
        validate_multimodal_rescue_plan_v1(
            plan, region_image_bytes=image + b"x", request_body_bytes=body
        )

    request = json.loads(body)
    request["unexpected"] = True
    changed_body = canonical_json_bytes_v1(request)
    attacked = copy.deepcopy(plan)
    attacked["request_body_ref"] = _ref("multimodal/request-body-v1", changed_body)
    _rehash_plan(attacked)
    with pytest.raises(MultimodalRescueChallengerV1Error, match="request body"):
        validate_multimodal_rescue_plan_v1(
            attacked, region_image_bytes=image, request_body_bytes=changed_body
        )

    attacked = copy.deepcopy(plan)
    attacked["region"]["recognition_render_pixel_bbox"] = [0, 0, 99, 79]
    _rehash_plan(attacked)
    with pytest.raises(MultimodalRescueChallengerV1Error, match="outside"):
        validate_multimodal_rescue_plan_v1(
            attacked, region_image_bytes=image, request_body_bytes=body
        )


@pytest.mark.parametrize(
    ("mode", "limit", "too_many"),
    [("CROP_TEXT", 128, 129), ("CROP_NUMERIC", 128, 129), ("PAGE_STRUCTURE", 4096, 4097)],
)
def test_mode_is_exact_and_enforces_bounded_output_tokens(
    mode: str, limit: int, too_many: int
) -> None:
    image, plan, body = _plan(mode=mode, max_output_tokens=limit)
    request = json.loads(body)
    assert plan["mode"] == plan["region"]["mode"] == request["mode"] == mode
    if mode == "PAGE_STRUCTURE":
        assert request["output_contract"]["root_fields"] == ["blocks", "tables"]
    else:
        assert request["output_contract"] == {"root_fields": ["text"]}
    with pytest.raises(MultimodalRescueChallengerV1Error, match="bounded-cost"):
        _plan(mode=mode, max_output_tokens=too_many)

    attacked = copy.deepcopy(plan)
    attacked["mode"] = "CROP_TEXT" if mode == "PAGE_STRUCTURE" else "PAGE_STRUCTURE"
    _rehash_plan(attacked)
    with pytest.raises(MultimodalRescueChallengerV1Error, match="mode"):
        validate_multimodal_rescue_plan_v1(
            attacked, region_image_bytes=image, request_body_bytes=body
        )


@pytest.mark.parametrize("mode", ["CROP_TEXT", "CROP_NUMERIC"])
def test_crop_modes_accept_only_one_raw_text_surface(mode: str) -> None:
    image, plan, body = _plan(mode=mode)
    raw = _raw(plan)
    attempt = build_multimodal_rescue_attempt_v1(
        plan=plan,
        region_image_bytes=image,
        request_body_bytes=body,
        raw_response_bytes=raw,
    )
    assert attempt["output"] == {"text": "1.234"}
    for wrong in (_output(), {"text": "1.234", "unknown": False}):
        with pytest.raises(MultimodalRescueChallengerV1Error, match="fields"):
            build_multimodal_rescue_attempt_v1(
                plan=plan,
                region_image_bytes=image,
                request_body_bytes=body,
                raw_response_bytes=_raw(plan, output=wrong),
            )


def test_page_mode_rejects_crop_output_mode_swap() -> None:
    image, plan, body = _plan()
    with pytest.raises(MultimodalRescueChallengerV1Error, match="fields"):
        build_multimodal_rescue_attempt_v1(
            plan=plan,
            region_image_bytes=image,
            request_body_bytes=body,
            raw_response_bytes=_raw(plan, output={"text": "1.234"}),
        )


def test_attempt_pins_request_raw_response_and_closed_output() -> None:
    image, plan, body = _plan()
    raw = _raw(plan)
    attempt = build_multimodal_rescue_attempt_v1(
        plan=plan,
        region_image_bytes=image,
        request_body_bytes=body,
        raw_response_bytes=raw,
    )
    assert attempt["raw_response_ref"]["sha256"] == sha256(raw).hexdigest()
    assert attempt["request_body_ref"] == plan["request_body_ref"]
    assert attempt["output"] == _output()
    assert attempt["lineage"] == {
        "independent_corroboration": False,
        "kind": "INITIAL",
        "repeat_of_attempt_id": None,
        "same_model_repeat": False,
    }
    assert (
        validate_multimodal_rescue_attempt_v1(
            attempt,
            plan=plan,
            region_image_bytes=image,
            request_body_bytes=body,
            raw_response_bytes=raw,
        )
        == attempt
    )


@pytest.mark.parametrize("attack", ["duplicate", "nonfinite", "unknown_root", "unknown_output"])
def test_raw_response_strict_json_and_unknown_fields_fail_closed(attack: str) -> None:
    image, plan, body = _plan()
    value = json.loads(_raw(plan))
    if attack == "duplicate":
        raw = _raw(plan)[:-1] + b',"response_id":"response-duplicate"}'
    elif attack == "nonfinite":
        value["output"]["blocks"][0]["bbox"][2] = float("nan")
        raw = json.dumps(value, allow_nan=True, separators=(",", ":")).encode()
    elif attack == "unknown_root":
        value["credential"] = "forbidden"
        raw = json.dumps(value, separators=(",", ":")).encode()
    else:
        value["output"]["schema_id"] = "downstream-17"
        raw = json.dumps(value, separators=(",", ":")).encode()
    with pytest.raises(MultimodalRescueChallengerV1Error):
        build_multimodal_rescue_attempt_v1(
            plan=plan,
            region_image_bytes=image,
            request_body_bytes=body,
            raw_response_bytes=raw,
        )


@pytest.mark.parametrize("text", ["ReportNormId 6074", "family_id: 11", "schema identifier=#9"])
def test_model_output_rejects_downstream_identifier_leakage(text: str) -> None:
    image, plan, body = _plan()
    with pytest.raises(MultimodalRescueChallengerV1Error, match="identifier"):
        build_multimodal_rescue_attempt_v1(
            plan=plan,
            region_image_bytes=image,
            request_body_bytes=body,
            raw_response_bytes=_raw(plan, output=_output(text)),
        )


def test_output_ordinals_use_exact_integers_not_boolean_aliases() -> None:
    image, plan, body = _plan()
    output = _output()
    output["blocks"].append(
        {"bbox": [1, 11, 30, 20], "kind": "TEXT", "ordinal": True, "raw_text": "Khác"}
    )
    with pytest.raises(MultimodalRescueChallengerV1Error, match="ordinal"):
        build_multimodal_rescue_attempt_v1(
            plan=plan,
            region_image_bytes=image,
            request_body_bytes=body,
            raw_response_bytes=_raw(plan, output=output),
        )


def test_same_model_repeat_is_direct_lineage_never_independent_corroboration() -> None:
    image, plan, body = _plan()
    raw1 = _raw(plan)
    first = build_multimodal_rescue_attempt_v1(
        plan=plan, region_image_bytes=image, request_body_bytes=body, raw_response_bytes=raw1
    )
    raw2 = _raw(plan, "request-2", "response-2")
    second = build_multimodal_rescue_attempt_v1(
        plan=plan,
        region_image_bytes=image,
        request_body_bytes=body,
        raw_response_bytes=raw2,
        previous_attempt=first,
    )
    assert second["attempt_ordinal"] == 2
    assert second["raw_response_ref"] != first["raw_response_ref"]
    assert second["lineage"] == {
        "independent_corroboration": False,
        "kind": "SAME_MODEL_REPEAT",
        "repeat_of_attempt_id": first["attempt_id"],
        "same_model_repeat": True,
    }
    assert (
        validate_multimodal_rescue_attempt_v1(
            second,
            plan=plan,
            region_image_bytes=image,
            request_body_bytes=body,
            raw_response_bytes=raw2,
            previous_attempt=first,
        )
        == second
    )

    with pytest.raises(MultimodalRescueChallengerV1Error, match="replay"):
        validate_multimodal_rescue_attempt_v1(
            second,
            plan=plan,
            region_image_bytes=image,
            request_body_bytes=body,
            raw_response_bytes=raw2,
        )
    attacked = copy.deepcopy(second)
    attacked["lineage"]["independent_corroboration"] = True
    _rehash_attempt(attacked)
    with pytest.raises(MultimodalRescueChallengerV1Error, match="independent"):
        validate_multimodal_rescue_attempt_v1(
            attacked,
            plan=plan,
            region_image_bytes=image,
            request_body_bytes=body,
            raw_response_bytes=raw2,
            previous_attempt=first,
        )

    malformed_first = copy.deepcopy(first)
    malformed_first["lineage"]["kind"] = "SAME_MODEL_REPEAT"
    _rehash_attempt(malformed_first)
    with pytest.raises(MultimodalRescueChallengerV1Error, match="initial"):
        build_multimodal_rescue_attempt_v1(
            plan=plan,
            region_image_bytes=image,
            request_body_bytes=body,
            raw_response_bytes=raw2,
            previous_attempt=malformed_first,
        )

    with pytest.raises(MultimodalRescueChallengerV1Error, match="only one"):
        build_multimodal_rescue_attempt_v1(
            plan=plan,
            region_image_bytes=image,
            request_body_bytes=body,
            raw_response_bytes=b"not-even-parsed-for-a-third-attempt",
            previous_attempt=second,
        )


def test_repeat_requires_fresh_request_and_response_ids() -> None:
    image, plan, body = _plan()
    raw = _raw(plan)
    first = build_multimodal_rescue_attempt_v1(
        plan=plan, region_image_bytes=image, request_body_bytes=body, raw_response_bytes=raw
    )
    with pytest.raises(MultimodalRescueChallengerV1Error, match="fresh"):
        build_multimodal_rescue_attempt_v1(
            plan=plan,
            region_image_bytes=image,
            request_body_bytes=body,
            raw_response_bytes=_raw(plan, "request-1", "response-2"),
            previous_attempt=first,
        )
