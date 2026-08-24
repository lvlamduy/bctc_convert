from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256

import pytest

import bctc_ai.evaluation.google_ocr_rescue_contract_v1 as contract
from bctc_ai.evaluation.google_ocr_rescue_contract_v1 import (
    OUTPUT_AUTHORITY,
    QUARANTINED_GENERATED_AUTHORITY,
    AuthenticatedUnresolvedPageV1,
    ContentRefKindV1,
    ExactContentRefV1,
    GoogleOcrExecutionStatusV1,
    GoogleOcrImmutableGcsInputV1,
    GoogleOcrInlineInputV1,
    GoogleOcrInputBindingKindV1,
    GoogleOcrProfileV1,
    GoogleOcrReleaseChannelV1,
    GoogleOcrRescueContractV1Error,
    GoogleOcrResidencyAssuranceV1,
    GoogleOcrRouteV1,
    PageAuthenticationStateV1,
    PageResolutionStateV1,
    build_google_ocr_execution_receipt_v1,
    build_google_ocr_rescue_plan_v1,
    derive_google_ocr_profile_v1,
    normalize_google_ocr_response_v1,
    validate_google_ocr_execution_receipt_v1,
    validate_google_ocr_rescue_plan_v1,
)


def _digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def _ref(kind: ContentRefKindV1, logical_id: str, revision: str = "v1") -> ExactContentRefV1:
    return ExactContentRefV1(kind, logical_id, _digest(f"{logical_id}:{revision}"), len(revision))


@pytest.fixture
def unresolved_page() -> AuthenticatedUnresolvedPageV1:
    return AuthenticatedUnresolvedPageV1(
        document_id="bank-001-report-2025",
        page_id="bank-001-report-2025:p17",
        physical_page=17,
        pixel_width=100,
        pixel_height=200,
        mime_type="image/png",
        source_page_ref=_ref(ContentRefKindV1.SOURCE_PAGE, "source/page/17"),
        page_image_ref=_ref(ContentRefKindV1.PAGE_IMAGE, "render/page/17.png"),
        authentication_receipt_ref=_ref(ContentRefKindV1.AUTHENTICATION_RECEIPT, "auth/page/17"),
        unresolved_graph_ref=_ref(ContentRefKindV1.UNRESOLVED_GRAPH, "graph/page/17"),
        authentication_state=PageAuthenticationStateV1.CALLER_AUTHENTICATED_CURRENT_REFS,
        resolution_state=PageResolutionStateV1.UNRESOLVED_AFTER_DETERMINISTIC_GRAPH,
        unresolved_reason_codes=("COLUMN_SPLIT_AMBIGUOUS", "OCR_TEXT_DAMAGED"),
    )


def _profile(
    route: GoogleOcrRouteV1,
    *,
    location: str = "eu",
    endpoint_location: str | None = None,
    processor_version: str | None = None,
    revision: str = "v1",
) -> GoogleOcrProfileV1:
    if route is GoogleOcrRouteV1.CLOUD_VISION_DOCUMENT_TEXT_DETECTION:
        processor = "DOCUMENT_TEXT_DETECTION"
        version = processor_version or "builtin-document-text-detection"
        endpoint = (
            "vision.googleapis.com"
            if (endpoint_location or location) == "global"
            else f"{endpoint_location or location}-vision.googleapis.com"
        )
        resource = (
            "images:annotate"
            if location == "global"
            else f"projects/test-project/locations/{location}/images:annotate"
        )
    elif route is GoogleOcrRouteV1.DOCUMENT_AI_OCR_PROCESSOR:
        processor = "OCR_PROCESSOR"
        version = processor_version or "pretrained-ocr-v2.1-2024-08-07"
        endpoint = (
            "documentai.googleapis.com"
            if (endpoint_location or location) == "global"
            else f"{endpoint_location or location}-documentai.googleapis.com"
        )
        resource = (
            f"projects/test-project/locations/{location}/processors/ocr-processor/"
            f"processorVersions/{version}"
        )
    else:
        processor = "LAYOUT_PARSER_PROCESSOR"
        version = processor_version or "pretrained-layout-parser-v1.0-2024-06-03"
        endpoint = (
            "documentai.googleapis.com"
            if (endpoint_location or location) == "global"
            else f"{endpoint_location or location}-documentai.googleapis.com"
        )
        resource = (
            f"projects/test-project/locations/{location}/processors/layout-processor/"
            f"processorVersions/{version}"
        )
    return GoogleOcrProfileV1(
        route=route,
        provider_name="GOOGLE_CLOUD_REST",
        api_version="v1",
        endpoint_hostname=endpoint,
        processor_name=processor,
        processor_resource=resource,
        processor_version=version,
        provider_ref=_ref(ContentRefKindV1.PROVIDER, "provider/google-cloud-rest", revision),
        api_version_ref=_ref(ContentRefKindV1.API_VERSION, "google-api-version/v1", revision),
        endpoint_ref=_ref(ContentRefKindV1.ENDPOINT, f"google-endpoint/{endpoint}", revision),
        processor_ref=_ref(
            ContentRefKindV1.PROCESSOR, f"google-processor-resource/{resource}", revision
        ),
        processor_version_ref=_ref(
            ContentRefKindV1.PROCESSOR_VERSION,
            f"google-processor-version/{version}",
            revision,
        ),
        region_ref=_ref(ContentRefKindV1.REGION, f"google-location/{location}", revision),
        prompt_ref=_ref(ContentRefKindV1.PROMPT, "prompt/source-structure-short-v1", revision),
        config_ref=_ref(ContentRefKindV1.CONFIG, f"config/{route.value.lower()}", revision),
    )


def _plan(
    page: AuthenticatedUnresolvedPageV1, route: GoogleOcrRouteV1
) -> contract.GoogleOcrRescuePlanV1:
    return build_google_ocr_rescue_plan_v1(page=page, profile=_profile(route))


def _json_bytes(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


def _execution_receipt(plan, raw: bytes, *, input_binding=None):
    if input_binding is None:
        input_binding = GoogleOcrInlineInputV1(
            GoogleOcrInputBindingKindV1.INLINE,
            plan.page.page_image_ref.sha256,
            plan.page.page_image_ref.size_bytes,
        )
    return build_google_ocr_execution_receipt_v1(
        plan=plan,
        endpoint_hostname=plan.profile.endpoint_hostname,
        http_method="POST",
        api_version=plan.profile.api_version,
        processor_resource=plan.profile.processor_resource,
        request_body_sha256=_digest(f"request:{plan.plan_id}"),
        request_body_size_bytes=137,
        input_binding=input_binding,
        status=GoogleOcrExecutionStatusV1.SUCCEEDED,
        http_status_code=200,
        response_sha256=sha256(raw).hexdigest(),
        response_size_bytes=len(raw),
        transport_capture_ref=_ref(
            ContentRefKindV1.TRANSPORT_CAPTURE, f"transport/{plan.plan_id}", "capture"
        ),
        request_id="request-123",
    )


def _normalize(plan, raw: bytes):
    return normalize_google_ocr_response_v1(
        plan=plan,
        execution_receipt=_execution_receipt(plan, raw),
        raw_response_bytes=raw,
    )


def _bbox(*, normalized: bool) -> dict:
    if normalized:
        return {
            "normalizedVertices": [
                {"x": 0.1, "y": 0.1},
                {"x": 0.9, "y": 0.1},
                {"x": 0.9, "y": 0.2},
                {"x": 0.1, "y": 0.2},
            ]
        }
    return {
        "vertices": [
            {"x": 10, "y": 20},
            {"x": 90, "y": 20},
            {"x": 90, "y": 40},
            {"x": 10, "y": 40},
        ]
    }


def _vision_response(*, normalized: bool) -> dict:
    symbols = []
    for index, character in enumerate("Công"):
        symbol: dict = {
            "boundingBox": _bbox(normalized=normalized),
            "text": character,
            "confidence": 0.91 + index / 100,
        }
        if index == 3:
            symbol["property"] = {
                "detectedLanguages": [{"languageCode": "vi", "confidence": 0.99}],
                "detectedBreak": {"type": "LINE_BREAK"},
            }
        symbols.append(symbol)
    return {
        "responses": [
            {
                "fullTextAnnotation": {
                    "text": "Công ty TNHH\nDư nợ 2025\n",
                    "pages": [
                        {
                            "width": 100,
                            "height": 200,
                            "confidence": 0.88,
                            "property": {
                                "detectedLanguages": [{"languageCode": "vi", "confidence": 0.98}]
                            },
                            "blocks": [
                                {
                                    "boundingBox": _bbox(normalized=normalized),
                                    "blockType": "TEXT",
                                    "confidence": 0.89,
                                    "paragraphs": [
                                        {
                                            "boundingBox": _bbox(normalized=normalized),
                                            "confidence": 0.9,
                                            "words": [
                                                {
                                                    "boundingBox": _bbox(normalized=normalized),
                                                    "confidence": 0.92,
                                                    "symbols": symbols,
                                                }
                                            ],
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            }
        ]
    }


def _layout(start: int, end: int, *, normalized: bool, confidence: float = 0.93) -> dict:
    segment = {"endIndex": str(end)}
    if start:
        segment["startIndex"] = str(start)
    return {
        "textAnchor": {"textSegments": [segment]},
        "confidence": confidence,
        "boundingPoly": _bbox(normalized=normalized),
        "orientation": "PAGE_UP",
    }


def _document_ai_ocr_response(*, normalized: bool) -> dict:
    text = "Công ty\t2025\n"
    return {
        "humanReviewStatus": {"state": "SKIPPED", "stateMessage": ""},
        "document": {
            "text": text,
            "mimeType": "image/png",
            "pages": [
                {
                    "pageNumber": 1,
                    "dimension": {"width": 100, "height": 200, "unit": "pixels"},
                    "detectedLanguages": [{"languageCode": "vi", "confidence": 0.99}],
                    "blocks": [{"layout": _layout(0, 12, normalized=normalized)}],
                    "paragraphs": [{"layout": _layout(0, 7, normalized=normalized)}],
                    "lines": [{"layout": _layout(0, 7, normalized=normalized)}],
                    "tokens": [
                        {
                            "layout": _layout(0, 4, normalized=normalized),
                            "detectedBreak": {"type": "SPACE"},
                            "detectedLanguages": [{"languageCode": "vi", "confidence": 0.97}],
                        }
                    ],
                    "symbols": [{"layout": _layout(1, 2, normalized=normalized)}],
                    "tables": [
                        {
                            "layout": _layout(0, 12, normalized=normalized),
                            "headerRows": [
                                {
                                    "cells": [
                                        {
                                            "layout": _layout(0, 7, normalized=normalized),
                                            "rowSpan": 1,
                                            "colSpan": 2,
                                        }
                                    ]
                                }
                            ],
                            "bodyRows": [
                                {
                                    "cells": [
                                        {
                                            "layout": _layout(8, 12, normalized=normalized),
                                            "rowSpan": 1,
                                            "colSpan": 1,
                                        }
                                    ]
                                }
                            ],
                        }
                    ],
                }
            ],
        },
    }


def _layout_parser_text_block(
    block_id: str,
    text: str,
    *,
    normalized: bool,
    text_type: str = "paragraph",
) -> dict:
    return {
        "blockId": block_id,
        "pageSpan": {"pageStart": 1, "pageEnd": 1},
        "boundingBox": _bbox(normalized=normalized),
        "textBlock": {"text": text, "type": text_type},
    }


def _layout_parser_response(*, normalized: bool) -> dict:
    return {
        "humanReviewStatus": {"state": "SKIPPED", "stateMessage": ""},
        "document": {
            "text": "Thuyết minh\nKhoản mục\nDư nợ\n",
            "mimeType": "image/png",
            "blobAssets": [{"assetId": "asset-1", "content": "aW1hZ2U=", "mimeType": "image/png"}],
            "chunkedDocument": {
                "chunks": [
                    {
                        "chunkId": "chunk-1",
                        "sourceBlockIds": ["title", "table-1", "image-1"],
                        "content": "Thuyết minh\nKhoản mục\nDư nợ\n",
                        "pageSpan": {"pageStart": 1, "pageEnd": 1},
                        "pageHeaders": [
                            {
                                "text": "Thuyết minh",
                                "pageSpan": {"pageStart": 1, "pageEnd": 1},
                            }
                        ],
                        "chunkFields": [
                            {
                                "imageChunkField": {
                                    "blobAssetId": "asset-1",
                                    "annotations": {"description": "Ảnh minh hoạ"},
                                }
                            },
                            {"tableChunkField": {"annotations": {"description": "Bảng được sinh"}}},
                        ],
                    }
                ]
            },
            "documentLayout": {
                "blocks": [
                    _layout_parser_text_block(
                        "title", "Thuyết minh", normalized=normalized, text_type="heading-2"
                    ),
                    {
                        "blockId": "table-1",
                        "pageSpan": {"pageStart": 1, "pageEnd": 1},
                        "boundingBox": _bbox(normalized=normalized),
                        "tableBlock": {
                            "caption": "Dư nợ",
                            "annotations": {"description": "Bảng thuyết minh"},
                            "headerRows": [
                                {
                                    "cells": [
                                        {
                                            "blocks": [
                                                _layout_parser_text_block(
                                                    "header-1",
                                                    "Khoản mục",
                                                    normalized=normalized,
                                                )
                                            ],
                                            "rowSpan": 1,
                                            "colSpan": 2,
                                        }
                                    ]
                                }
                            ],
                            "bodyRows": [
                                {
                                    "cells": [
                                        {
                                            "blocks": [
                                                _layout_parser_text_block(
                                                    "body-1", "Dư nợ", normalized=normalized
                                                )
                                            ],
                                            "rowSpan": 1,
                                            "colSpan": 1,
                                        }
                                    ]
                                }
                            ],
                        },
                    },
                    {
                        "blockId": "image-1",
                        "pageSpan": {"pageStart": 1, "pageEnd": 1},
                        "boundingBox": _bbox(normalized=normalized),
                        "imageBlock": {
                            "mimeType": "image/png",
                            "imageText": "Số 999 do mô hình mô tả",
                            "annotations": {"description": "Mô tả do mô hình sinh"},
                            "blobAssetId": "asset-1",
                        },
                    },
                ]
            },
        },
    }


def test_request_plan_is_single_page_offline_and_binds_all_exact_refs(
    unresolved_page: AuthenticatedUnresolvedPageV1,
) -> None:
    plan = _plan(unresolved_page, GoogleOcrRouteV1.DOCUMENT_AI_OCR_PROCESSOR)

    assert plan.task.count(".") == 2
    assert len(plan.task) < 240
    assert plan.plan_id.startswith("gocrpv1:plan:")
    assert plan.page.page_image_ref.sha256 == unresolved_page.page_image_ref.sha256
    assert {
        plan.profile.provider_ref.kind,
        plan.profile.api_version_ref.kind,
        plan.profile.endpoint_ref.kind,
        plan.profile.processor_ref.kind,
        plan.profile.processor_version_ref.kind,
        plan.profile.region_ref.kind,
        plan.profile.prompt_ref.kind,
        plan.profile.config_ref.kind,
    } == {
        ContentRefKindV1.PROVIDER,
        ContentRefKindV1.API_VERSION,
        ContentRefKindV1.ENDPOINT,
        ContentRefKindV1.PROCESSOR,
        ContentRefKindV1.PROCESSOR_VERSION,
        ContentRefKindV1.REGION,
        ContentRefKindV1.PROMPT,
        ContentRefKindV1.CONFIG,
    }
    assert plan.external_upload_requires_explicit_authorization is True
    assert plan.external_upload_authorized_by_plan is False
    assert plan.network_call_performed is False
    assert plan.credentials_accessed is False
    assert plan.image_bytes_embedded is False
    assert plan.execution_state == "PLANNED_NOT_EXECUTED"
    assert plan.derived_location == "eu"
    assert plan.release_channel is GoogleOcrReleaseChannelV1.STABLE
    assert plan.residency_assurance is GoogleOcrResidencyAssuranceV1.COMPLIANT
    validate_google_ocr_rescue_plan_v1(plan)


def test_request_plan_rejects_noncurrent_resolved_or_unauthenticated_page(
    unresolved_page: AuthenticatedUnresolvedPageV1,
) -> None:
    with pytest.raises(GoogleOcrRescueContractV1Error, match="caller-current"):
        build_google_ocr_rescue_plan_v1(
            page=replace(unresolved_page, authentication_state="SELF_REPORTED"),
            profile=_profile(GoogleOcrRouteV1.DOCUMENT_AI_OCR_PROCESSOR),
        )
    with pytest.raises(GoogleOcrRescueContractV1Error, match="only after"):
        build_google_ocr_rescue_plan_v1(
            page=replace(unresolved_page, resolution_state="RESOLVED"),
            profile=_profile(GoogleOcrRouteV1.DOCUMENT_AI_OCR_PROCESSOR),
        )
    with pytest.raises(GoogleOcrRescueContractV1Error, match="PAGE_IMAGE"):
        build_google_ocr_rescue_plan_v1(
            page=replace(
                unresolved_page,
                page_image_ref=_ref(ContentRefKindV1.SOURCE_PAGE, "wrong-kind"),
            ),
            profile=_profile(GoogleOcrRouteV1.DOCUMENT_AI_OCR_PROCESSOR),
        )


def test_exact_profile_ref_change_changes_plan_and_tampered_plan_fails(
    unresolved_page: AuthenticatedUnresolvedPageV1,
) -> None:
    first = build_google_ocr_rescue_plan_v1(
        page=unresolved_page,
        profile=_profile(GoogleOcrRouteV1.DOCUMENT_AI_OCR_PROCESSOR, revision="v1"),
    )
    second = build_google_ocr_rescue_plan_v1(
        page=unresolved_page,
        profile=_profile(GoogleOcrRouteV1.DOCUMENT_AI_OCR_PROCESSOR, revision="v2"),
    )
    assert first.plan_id != second.plan_id
    with pytest.raises(GoogleOcrRescueContractV1Error, match="privacy"):
        validate_google_ocr_rescue_plan_v1(replace(first, external_upload_authorized_by_plan=True))
    with pytest.raises(GoogleOcrRescueContractV1Error, match="plan_id"):
        validate_google_ocr_rescue_plan_v1(replace(first, profile=second.profile))
    aws = replace(
        first.profile,
        provider_name="AWS_TEXTRACT",
        provider_ref=_ref(ContentRefKindV1.PROVIDER, "provider/aws"),
    )
    with pytest.raises(GoogleOcrRescueContractV1Error, match="GOOGLE_CLOUD_REST"):
        build_google_ocr_rescue_plan_v1(page=unresolved_page, profile=aws)


def test_release_geometry_and_residency_are_derived_from_exact_version_and_location(
    unresolved_page: AuthenticatedUnresolvedPageV1,
) -> None:
    stable = derive_google_ocr_profile_v1(
        _profile(GoogleOcrRouteV1.DOCUMENT_AI_LAYOUT_PARSER, location="eu")
    )
    assert stable.location == "eu"
    assert stable.release_channel is GoogleOcrReleaseChannelV1.STABLE
    assert stable.residency_assurance is GoogleOcrResidencyAssuranceV1.COMPLIANT
    assert stable.source_visible_geometry_supported is True

    for version, location in (
        ("pretrained-layout-parser-v1.6-2026-01-13", "eu"),
        ("pretrained-layout-parser-v1.6-pro-2025-12-01", "us"),
    ):
        profile = _profile(
            GoogleOcrRouteV1.DOCUMENT_AI_LAYOUT_PARSER,
            location=location,
            processor_version=version,
        )
        derived = derive_google_ocr_profile_v1(profile)
        assert derived.release_channel is GoogleOcrReleaseChannelV1.PREVIEW
        assert derived.residency_assurance is GoogleOcrResidencyAssuranceV1.NONCOMPLIANT
        assert derived.source_visible_geometry_supported is False
        with pytest.raises(GoogleOcrRescueContractV1Error, match="stable Layout Parser"):
            build_google_ocr_rescue_plan_v1(page=unresolved_page, profile=profile)

    unknown = _profile(
        GoogleOcrRouteV1.DOCUMENT_AI_LAYOUT_PARSER,
        processor_version="pretrained-layout-parser-v9-unknown",
    )
    derived = derive_google_ocr_profile_v1(unknown)
    assert derived.release_channel is GoogleOcrReleaseChannelV1.UNKNOWN
    assert derived.residency_assurance is GoogleOcrResidencyAssuranceV1.UNVERIFIED
    with pytest.raises(GoogleOcrRescueContractV1Error, match="preview/unknown"):
        build_google_ocr_rescue_plan_v1(page=unresolved_page, profile=unknown)


def test_cross_location_and_cloud_vision_file_route_profiles_fail_at_plan_time(
    unresolved_page: AuthenticatedUnresolvedPageV1,
) -> None:
    with pytest.raises(GoogleOcrRescueContractV1Error, match="documented exact hostname"):
        derive_google_ocr_profile_v1(
            _profile(GoogleOcrRouteV1.DOCUMENT_AI_OCR_PROCESSOR, location="mars")
        )
    with pytest.raises(GoogleOcrRescueContractV1Error, match="location.*disagree"):
        build_google_ocr_rescue_plan_v1(
            page=unresolved_page,
            profile=_profile(
                GoogleOcrRouteV1.DOCUMENT_AI_OCR_PROCESSOR,
                location="eu",
                endpoint_location="us",
            ),
        )
    for mime_type in ("application/pdf", "image/tiff"):
        with pytest.raises(GoogleOcrRescueContractV1Error, match="PDF/TIFF"):
            build_google_ocr_rescue_plan_v1(
                page=replace(unresolved_page, mime_type=mime_type),
                profile=_profile(GoogleOcrRouteV1.CLOUD_VISION_DOCUMENT_TEXT_DETECTION),
            )


def test_execution_receipt_binds_inline_or_immutable_gcs_input_to_page_sha(
    unresolved_page: AuthenticatedUnresolvedPageV1,
) -> None:
    plan = _plan(unresolved_page, GoogleOcrRouteV1.CLOUD_VISION_DOCUMENT_TEXT_DETECTION)
    raw = _json_bytes(_vision_response(normalized=True))
    inline = _execution_receipt(plan, raw)
    validate_google_ocr_execution_receipt_v1(inline, plan=plan)
    assert inline.self_hash_is_authority is False
    assert inline.external_upload_authorized_by_receipt is False

    gcs = GoogleOcrImmutableGcsInputV1(
        GoogleOcrInputBindingKindV1.IMMUTABLE_GCS,
        "private-bctc-source",
        "bank/report/page-17.png",
        "1735689600000000",
        plan.page.page_image_ref.sha256,
        plan.page.page_image_ref.size_bytes,
    )
    receipt = _execution_receipt(plan, raw, input_binding=gcs)
    validate_google_ocr_execution_receipt_v1(receipt, plan=plan)
    assert receipt.input_binding.generation == "1735689600000000"

    forged = replace(
        gcs,
        caller_verified_content_sha256="0" * 64,
    )
    with pytest.raises(GoogleOcrRescueContractV1Error, match="GCS content SHA"):
        _execution_receipt(plan, raw, input_binding=forged)


def test_normalizer_rejects_response_or_receipt_replayed_under_another_plan(
    unresolved_page: AuthenticatedUnresolvedPageV1,
) -> None:
    plan_a = _plan(unresolved_page, GoogleOcrRouteV1.CLOUD_VISION_DOCUMENT_TEXT_DETECTION)
    plan_b = build_google_ocr_rescue_plan_v1(
        page=unresolved_page,
        profile=_profile(
            GoogleOcrRouteV1.CLOUD_VISION_DOCUMENT_TEXT_DETECTION,
            revision="v2",
        ),
    )
    raw_a = _json_bytes(_vision_response(normalized=True))
    receipt_a = _execution_receipt(plan_a, raw_a)
    with pytest.raises(GoogleOcrRescueContractV1Error, match="different request plan"):
        normalize_google_ocr_response_v1(
            plan=plan_b,
            execution_receipt=receipt_a,
            raw_response_bytes=raw_a,
        )
    with pytest.raises(GoogleOcrRescueContractV1Error, match="raw response bytes"):
        normalize_google_ocr_response_v1(
            plan=plan_a,
            execution_receipt=receipt_a,
            raw_response_bytes=raw_a + b" ",
        )
    with pytest.raises(GoogleOcrRescueContractV1Error, match="self-hash"):
        validate_google_ocr_execution_receipt_v1(
            replace(receipt_a, self_hash_is_authority=True),
            plan=plan_a,
        )


def test_cloud_vision_preserves_vietnamese_hierarchy_confidence_and_response_sha(
    unresolved_page: AuthenticatedUnresolvedPageV1,
) -> None:
    plan = _plan(unresolved_page, GoogleOcrRouteV1.CLOUD_VISION_DOCUMENT_TEXT_DETECTION)
    raw = _json_bytes(_vision_response(normalized=True))

    result = _normalize(plan, raw)

    assert result["raw_text"] == "Công ty TNHH\nDư nợ 2025\n"
    assert result["raw_response"]["sha256"] == sha256(raw).hexdigest()
    assert result["raw_response"]["size_bytes"] == len(raw)
    assert result["raw_response"]["execution_receipt_id"].startswith("gocrpv1:execution:")
    page = result["structure"]["pages"][0]
    assert page["confidence"] == 0.88
    assert page["property"]["detected_languages"][0]["language_code"] == "vi"
    word = page["blocks"][0]["paragraphs"][0]["words"][0]
    assert word["text"] == "Công\n"
    assert [symbol["text"] for symbol in word["symbols"]] == ["C", "ô", "n", "g"]
    assert word["symbols"][-1]["confidence"] == pytest.approx(0.94)
    assert result["authority"] == OUTPUT_AUTHORITY
    assert result["authority"]["numeric_authority"] is False
    assert result["authority"]["mapping_authority"] is False
    assert result["authority"]["absence_authority"] is False
    assert result["authority"]["graph_validation_required"] is True


@pytest.mark.parametrize(
    "route,response_factory,geometry_path",
    [
        (
            GoogleOcrRouteV1.CLOUD_VISION_DOCUMENT_TEXT_DETECTION,
            _vision_response,
            ("pages", 0, "blocks", 0, "geometry"),
        ),
        (
            GoogleOcrRouteV1.DOCUMENT_AI_OCR_PROCESSOR,
            _document_ai_ocr_response,
            ("pages", 0, "blocks", 0, "layout", "geometry"),
        ),
    ],
)
def test_pixel_and_normalized_vertices_have_identical_canonical_geometry(
    unresolved_page: AuthenticatedUnresolvedPageV1,
    route: GoogleOcrRouteV1,
    response_factory,
    geometry_path: tuple,
) -> None:
    plan = _plan(unresolved_page, route)
    pixel = _normalize(plan, _json_bytes(response_factory(normalized=False)))
    normalized = _normalize(plan, _json_bytes(response_factory(normalized=True)))

    def at(value: dict, path: tuple):
        for key in path:
            value = value[key]
        return value

    assert at(pixel["structure"], geometry_path) == at(normalized["structure"], geometry_path)
    geometry = at(pixel["structure"], geometry_path)
    assert geometry["pixel_vertices"] == [
        {"x": 10, "y": 20},
        {"x": 90, "y": 20},
        {"x": 90, "y": 40},
        {"x": 10, "y": 40},
    ]
    assert geometry["normalized_vertices_ppm"][0] == {"x": 100_000, "y": 100_000}


def test_document_ai_ocr_preserves_text_anchors_and_table_structure(
    unresolved_page: AuthenticatedUnresolvedPageV1,
) -> None:
    plan = _plan(unresolved_page, GoogleOcrRouteV1.DOCUMENT_AI_OCR_PROCESSOR)
    result = _normalize(plan, _json_bytes(_document_ai_ocr_response(normalized=True)))

    assert result["raw_text"] == "Công ty\t2025\n"
    structure = result["structure"]
    assert structure["kind"] == "DOCUMENT_AI_PAGE_LAYOUT"
    assert structure["response_metadata"]["human_review_status"] == {
        "state": "SKIPPED",
        "state_message": "",
        "human_review_operation": None,
    }
    page = structure["pages"][0]
    assert page["paragraphs"][0]["layout"]["text"] == "Công ty"
    assert page["symbols"][0]["layout"]["text"] == "ô"
    assert page["tokens"][0]["detected_break"] == {"type": "SPACE", "is_prefix": False}
    table = structure["tables"][0]
    assert table["header_rows"][0]["cells"][0]["layout"]["text"] == "Công ty"
    assert table["header_rows"][0]["cells"][0]["col_span"] == 2
    assert table["body_rows"][0]["cells"][0]["layout"]["text"] == "2025"


def test_layout_parser_preserves_nested_text_and_table_blocks(
    unresolved_page: AuthenticatedUnresolvedPageV1,
) -> None:
    plan = _plan(unresolved_page, GoogleOcrRouteV1.DOCUMENT_AI_LAYOUT_PARSER)
    raw = _json_bytes(_layout_parser_response(normalized=True))
    result = _normalize(plan, raw)

    assert result["raw_text"] == "Thuyết minh\nKhoản mục\nDư nợ\n"
    assert result["structure"]["kind"] == "DOCUMENT_AI_DOCUMENT_LAYOUT"
    title, table, image = result["structure"]["blocks"]
    assert title["kind"] == "TEXT"
    assert title["text"] == "Thuyết minh"
    assert title["text_type"] == "heading-2"
    assert table["kind"] == "TABLE"
    assert table["caption"] == "Dư nợ"
    assert table["annotations"]["description"] == "Bảng thuyết minh"
    assert table["annotations"]["authority"] == QUARANTINED_GENERATED_AUTHORITY
    header = table["header_rows"][0]["cells"][0]
    assert header["col_span"] == 2
    assert header["blocks"][0]["text"] == "Khoản mục"
    assert table["body_rows"][0]["cells"][0]["blocks"][0]["text"] == "Dư nợ"
    assert result["structure"]["tables"] == [table]
    assert image["kind"] == "IMAGE_QUARANTINED"
    assert image["image_text"] == "Số 999 do mô hình mô tả"
    assert image["authority"] == QUARANTINED_GENERATED_AUTHORITY
    assert image["authority"]["numeric_authority"] is False
    assert image["image_source"] == {
        "kind": "BLOB_ASSET",
        "blob_asset_id": "asset-1",
        "authority": dict(QUARANTINED_GENERATED_AUTHORITY),
    }
    assert result["structure"]["blob_assets"][0]["content_sha256"] == sha256(b"image").hexdigest()
    assert result["structure"]["blob_assets"][0]["content_size_bytes"] == 5
    chunk = result["structure"]["chunked_document"]["chunks"][0]
    assert chunk["source_block_ids"] == ["title", "table-1", "image-1"]
    assert [field["kind"] for field in chunk["chunk_fields"]] == [
        "IMAGE_CHUNK_QUARANTINED",
        "TABLE_CHUNK_ANNOTATION_QUARANTINED",
    ]
    assert all(field["authority"]["numeric_authority"] is False for field in chunk["chunk_fields"])


@pytest.mark.parametrize(
    "raw,match",
    [
        (b'{"responses":[],"responses":[]}', "duplicate"),
        (_json_bytes({"fullTextAnnotation": {}}), "fields drifted"),
        (_json_bytes({"responses": [{"full_text_annotation": {}}]}), "fields drifted"),
        (_json_bytes({"responses": [{"error": {"message": "quota"}}]}), "fields drifted"),
        (_json_bytes({"responses": []}), "exactly one"),
        (b'{"responses":[NaN]}', "non-finite"),
    ],
)
def test_cloud_vision_unknown_or_flexible_response_variants_fail_closed(
    unresolved_page: AuthenticatedUnresolvedPageV1, raw: bytes, match: str
) -> None:
    plan = _plan(unresolved_page, GoogleOcrRouteV1.CLOUD_VISION_DOCUMENT_TEXT_DETECTION)
    with pytest.raises(GoogleOcrRescueContractV1Error, match=match):
        _normalize(plan, raw)


def test_ambiguous_or_inconsistent_coordinate_variants_fail_closed(
    unresolved_page: AuthenticatedUnresolvedPageV1,
) -> None:
    response = _vision_response(normalized=False)
    box = response["responses"][0]["fullTextAnnotation"]["pages"][0]["blocks"][0]["boundingBox"]
    box["normalizedVertices"] = [
        {"x": 0.5, "y": 0.5},
        {"x": 0.9, "y": 0.5},
        {"x": 0.9, "y": 0.8},
        {"x": 0.5, "y": 0.8},
    ]
    plan = _plan(unresolved_page, GoogleOcrRouteV1.CLOUD_VISION_DOCUMENT_TEXT_DETECTION)
    with pytest.raises(GoogleOcrRescueContractV1Error, match="disagree"):
        _normalize(plan, _json_bytes(response))

    response = _vision_response(normalized=False)
    response["responses"][0]["fullTextAnnotation"]["pages"][0]["blocks"][0]["boundingBox"] = {
        "vertices": [{}, {"x": 10}, {"x": 10}, {}]
    }
    with pytest.raises(GoogleOcrRescueContractV1Error, match="positive polygon area"):
        _normalize(plan, _json_bytes(response))


def test_documented_zero_coordinate_omission_and_consistent_dual_bbox_are_supported(
    unresolved_page: AuthenticatedUnresolvedPageV1,
) -> None:
    plan = _plan(unresolved_page, GoogleOcrRouteV1.CLOUD_VISION_DOCUMENT_TEXT_DETECTION)
    response = _vision_response(normalized=False)
    box = response["responses"][0]["fullTextAnnotation"]["pages"][0]["blocks"][0]["boundingBox"]
    box["normalizedVertices"] = [
        {"x": 0.1, "y": 0.1},
        {"x": 0.9, "y": 0.1},
        {"x": 0.9, "y": 0.2},
        {"x": 0.1, "y": 0.2},
    ]
    result = _normalize(plan, _json_bytes(response))
    assert result["structure"]["pages"][0]["blocks"][0]["geometry"]["pixel_vertices"][0] == {
        "x": 10,
        "y": 20,
    }

    response = _vision_response(normalized=True)
    response["responses"][0]["fullTextAnnotation"]["pages"][0]["blocks"][0]["boundingBox"] = {
        "normalizedVertices": [{}, {"x": 1}, {"x": 1, "y": 1}, {"y": 1}]
    }
    result = _normalize(plan, _json_bytes(response))
    assert result["structure"]["pages"][0]["blocks"][0]["geometry"]["pixel_vertices"] == [
        {"x": 0, "y": 0},
        {"x": 100, "y": 0},
        {"x": 100, "y": 200},
        {"x": 0, "y": 200},
    ]


def test_document_ai_text_anchor_and_union_drift_fail_closed(
    unresolved_page: AuthenticatedUnresolvedPageV1,
) -> None:
    plan = _plan(unresolved_page, GoogleOcrRouteV1.DOCUMENT_AI_OCR_PROCESSOR)
    response = _document_ai_ocr_response(normalized=True)
    response["document"]["pages"][0]["paragraphs"][0]["layout"]["textAnchor"] = {
        "textSegments": [{"startIndex": "7", "endIndex": "99"}]
    }
    with pytest.raises(GoogleOcrRescueContractV1Error, match="outside"):
        _normalize(plan, _json_bytes(response))

    response = _document_ai_ocr_response(normalized=True)
    response["document"]["pages"][0]["paragraphs"][0]["layout"]["textAnchor"]["content"] = (
        "sửa chính tả"
    )
    with pytest.raises(GoogleOcrRescueContractV1Error, match="disagrees"):
        _normalize(plan, _json_bytes(response))

    layout_plan = _plan(unresolved_page, GoogleOcrRouteV1.DOCUMENT_AI_LAYOUT_PARSER)
    response = _layout_parser_response(normalized=True)
    response["document"]["pages"] = []
    with pytest.raises(GoogleOcrRescueContractV1Error, match="ambiguously mix"):
        _normalize(layout_plan, _json_bytes(response))


def test_layout_parser_rejects_duplicate_ids_multi_page_spans_and_union_ambiguity(
    unresolved_page: AuthenticatedUnresolvedPageV1,
) -> None:
    plan = _plan(unresolved_page, GoogleOcrRouteV1.DOCUMENT_AI_LAYOUT_PARSER)
    response = _layout_parser_response(normalized=True)
    nested = response["document"]["documentLayout"]["blocks"][1]["tableBlock"]["headerRows"][0][
        "cells"
    ][0]["blocks"][0]
    nested["blockId"] = "title"
    with pytest.raises(GoogleOcrRescueContractV1Error, match="duplicated"):
        _normalize(plan, _json_bytes(response))

    response = _layout_parser_response(normalized=True)
    response["document"]["documentLayout"]["blocks"][0]["pageSpan"]["pageEnd"] = 2
    with pytest.raises(GoogleOcrRescueContractV1Error, match="exactly"):
        _normalize(plan, _json_bytes(response))

    response = _layout_parser_response(normalized=True)
    response["document"]["documentLayout"]["blocks"][0]["tableBlock"] = {
        "headerRows": [],
        "bodyRows": [],
    }
    with pytest.raises(GoogleOcrRescueContractV1Error, match="exactly one"):
        _normalize(plan, _json_bytes(response))


def test_normalizer_has_no_executor_and_raw_byte_spelling_changes_only_response_receipt(
    unresolved_page: AuthenticatedUnresolvedPageV1,
) -> None:
    plan = _plan(unresolved_page, GoogleOcrRouteV1.CLOUD_VISION_DOCUMENT_TEXT_DETECTION)
    response = _vision_response(normalized=True)
    compact = _json_bytes(response)
    pretty = json.dumps(response, ensure_ascii=False, indent=2).encode()
    compact_result = _normalize(plan, compact)
    pretty_result = _normalize(plan, pretty)

    assert compact_result["raw_response"]["sha256"] != pretty_result["raw_response"]["sha256"]
    assert compact_result["raw_text"] == pretty_result["raw_text"]
    assert compact_result["structure"] == pretty_result["structure"]
    with pytest.raises(TypeError):
        OUTPUT_AUTHORITY["numeric_authority"] = True
    assert not hasattr(contract, "execute_google_ocr_rescue_v1")
    source = open(contract.__file__, encoding="utf-8").read()
    assert "import requests" not in source
    assert "from google" not in source
    assert "google.cloud" not in source
