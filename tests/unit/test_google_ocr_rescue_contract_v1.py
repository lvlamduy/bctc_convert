from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256

import pytest

import bctc_ai.evaluation.google_ocr_rescue_contract_v1 as contract
from bctc_ai.evaluation.google_ocr_rescue_contract_v1 import (
    OUTPUT_AUTHORITY,
    AuthenticatedUnresolvedPageV1,
    ContentRefKindV1,
    ExactContentRefV1,
    GoogleOcrProfileV1,
    GoogleOcrReleaseChannelV1,
    GoogleOcrRescueContractV1Error,
    GoogleOcrRouteV1,
    PageAuthenticationStateV1,
    PageResolutionStateV1,
    build_google_ocr_rescue_plan_v1,
    normalize_google_ocr_response_v1,
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
    preview_global: bool = False,
    revision: str = "v1",
) -> GoogleOcrProfileV1:
    if route is GoogleOcrRouteV1.CLOUD_VISION_DOCUMENT_TEXT_DETECTION:
        processor = "DOCUMENT_TEXT_DETECTION"
        version = "vision-rest-v1"
    elif route is GoogleOcrRouteV1.DOCUMENT_AI_OCR_PROCESSOR:
        processor = "projects/redacted/locations/eu/processors/ocr"
        version = "pretrained-ocr-v2.1-2024-08-07"
    else:
        processor = "projects/redacted/locations/eu/processors/layout"
        version = (
            "pretrained-layout-parser-v1.5-pro-2025-08-25"
            if preview_global
            else "pretrained-layout-parser-v1.0-2024-06-03"
        )
    region = "global" if preview_global else "eu"
    return GoogleOcrProfileV1(
        route=route,
        provider_name="GOOGLE_CLOUD_REST",
        processor_name=processor,
        processor_version=version,
        region=region,
        release_channel=(
            GoogleOcrReleaseChannelV1.PREVIEW
            if preview_global
            else GoogleOcrReleaseChannelV1.STABLE
        ),
        uses_global_endpoint=preview_global,
        data_residency_compliant=False if preview_global else True,
        provider_ref=_ref(ContentRefKindV1.PROVIDER, "provider/google-cloud-rest", revision),
        processor_ref=_ref(ContentRefKindV1.PROCESSOR, processor, revision),
        processor_version_ref=_ref(ContentRefKindV1.PROCESSOR_VERSION, version, revision),
        region_ref=_ref(ContentRefKindV1.REGION, f"region/{region}", revision),
        prompt_ref=_ref(ContentRefKindV1.PROMPT, "prompt/source-structure-short-v1", revision),
        config_ref=_ref(ContentRefKindV1.CONFIG, f"config/{route.value.lower()}", revision),
    )


def _plan(
    page: AuthenticatedUnresolvedPageV1, route: GoogleOcrRouteV1
) -> contract.GoogleOcrRescuePlanV1:
    return build_google_ocr_rescue_plan_v1(page=page, profile=_profile(route))


def _json_bytes(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


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
        }
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
        "document": {
            "text": "Thuyết minh\nKhoản mục\nDư nợ\n",
            "mimeType": "image/png",
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
                ]
            },
        }
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
        plan.profile.processor_ref.kind,
        plan.profile.processor_version_ref.kind,
        plan.profile.region_ref.kind,
        plan.profile.prompt_ref.kind,
        plan.profile.config_ref.kind,
    } == {
        ContentRefKindV1.PROVIDER,
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


def test_preview_global_profile_has_explicit_data_residency_warning(
    unresolved_page: AuthenticatedUnresolvedPageV1,
) -> None:
    plan = build_google_ocr_rescue_plan_v1(
        page=unresolved_page,
        profile=_profile(
            GoogleOcrRouteV1.DOCUMENT_AI_LAYOUT_PARSER,
            preview_global=True,
        ),
    )
    assert plan.data_residency_warning == (
        "PREVIEW_GLOBAL_ENDPOINT_NOT_DATA_RESIDENCY_COMPLIANT_"
        "EXPLICIT_UPLOAD_AUTHORIZATION_REQUIRED"
    )
    with pytest.raises(GoogleOcrRescueContractV1Error, match="non-compliant"):
        build_google_ocr_rescue_plan_v1(
            page=unresolved_page,
            profile=replace(plan.profile, data_residency_compliant=True),
        )


def test_cloud_vision_preserves_vietnamese_hierarchy_confidence_and_response_sha(
    unresolved_page: AuthenticatedUnresolvedPageV1,
) -> None:
    plan = _plan(unresolved_page, GoogleOcrRouteV1.CLOUD_VISION_DOCUMENT_TEXT_DETECTION)
    raw = _json_bytes(_vision_response(normalized=True))

    result = normalize_google_ocr_response_v1(plan=plan, raw_response_bytes=raw)

    assert result["raw_text"] == "Công ty TNHH\nDư nợ 2025\n"
    assert result["raw_response"] == {"sha256": sha256(raw).hexdigest(), "size_bytes": len(raw)}
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
    pixel = normalize_google_ocr_response_v1(
        plan=plan, raw_response_bytes=_json_bytes(response_factory(normalized=False))
    )
    normalized = normalize_google_ocr_response_v1(
        plan=plan, raw_response_bytes=_json_bytes(response_factory(normalized=True))
    )

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
    result = normalize_google_ocr_response_v1(
        plan=plan,
        raw_response_bytes=_json_bytes(_document_ai_ocr_response(normalized=True)),
    )

    assert result["raw_text"] == "Công ty\t2025\n"
    structure = result["structure"]
    assert structure["kind"] == "DOCUMENT_AI_PAGE_LAYOUT"
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
    result = normalize_google_ocr_response_v1(plan=plan, raw_response_bytes=raw)

    assert result["raw_text"] == "Thuyết minh\nKhoản mục\nDư nợ\n"
    assert result["structure"]["kind"] == "DOCUMENT_AI_DOCUMENT_LAYOUT"
    title, table = result["structure"]["blocks"]
    assert title["kind"] == "TEXT"
    assert title["text"] == "Thuyết minh"
    assert title["text_type"] == "heading-2"
    assert table["kind"] == "TABLE"
    assert table["caption"] == "Dư nợ"
    assert table["annotations"] == {"description": "Bảng thuyết minh"}
    header = table["header_rows"][0]["cells"][0]
    assert header["col_span"] == 2
    assert header["blocks"][0]["text"] == "Khoản mục"
    assert table["body_rows"][0]["cells"][0]["blocks"][0]["text"] == "Dư nợ"
    assert result["structure"]["tables"] == [table]


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
        normalize_google_ocr_response_v1(plan=plan, raw_response_bytes=raw)


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
        normalize_google_ocr_response_v1(plan=plan, raw_response_bytes=_json_bytes(response))

    response = _vision_response(normalized=False)
    response["responses"][0]["fullTextAnnotation"]["pages"][0]["blocks"][0]["boundingBox"] = {
        "vertices": [{}, {"x": 10}, {"x": 10}, {}]
    }
    with pytest.raises(GoogleOcrRescueContractV1Error, match="positive polygon area"):
        normalize_google_ocr_response_v1(plan=plan, raw_response_bytes=_json_bytes(response))


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
    result = normalize_google_ocr_response_v1(plan=plan, raw_response_bytes=_json_bytes(response))
    assert result["structure"]["pages"][0]["blocks"][0]["geometry"]["pixel_vertices"][0] == {
        "x": 10,
        "y": 20,
    }

    response = _vision_response(normalized=True)
    response["responses"][0]["fullTextAnnotation"]["pages"][0]["blocks"][0]["boundingBox"] = {
        "normalizedVertices": [{}, {"x": 1}, {"x": 1, "y": 1}, {"y": 1}]
    }
    result = normalize_google_ocr_response_v1(plan=plan, raw_response_bytes=_json_bytes(response))
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
        normalize_google_ocr_response_v1(plan=plan, raw_response_bytes=_json_bytes(response))

    response = _document_ai_ocr_response(normalized=True)
    response["document"]["pages"][0]["paragraphs"][0]["layout"]["textAnchor"]["content"] = (
        "sửa chính tả"
    )
    with pytest.raises(GoogleOcrRescueContractV1Error, match="disagrees"):
        normalize_google_ocr_response_v1(plan=plan, raw_response_bytes=_json_bytes(response))

    layout_plan = _plan(unresolved_page, GoogleOcrRouteV1.DOCUMENT_AI_LAYOUT_PARSER)
    response = _layout_parser_response(normalized=True)
    response["document"]["pages"] = []
    with pytest.raises(GoogleOcrRescueContractV1Error, match="ambiguously mix"):
        normalize_google_ocr_response_v1(plan=layout_plan, raw_response_bytes=_json_bytes(response))


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
        normalize_google_ocr_response_v1(plan=plan, raw_response_bytes=_json_bytes(response))

    response = _layout_parser_response(normalized=True)
    response["document"]["documentLayout"]["blocks"][0]["pageSpan"]["pageEnd"] = 2
    with pytest.raises(GoogleOcrRescueContractV1Error, match="exactly"):
        normalize_google_ocr_response_v1(plan=plan, raw_response_bytes=_json_bytes(response))

    response = _layout_parser_response(normalized=True)
    response["document"]["documentLayout"]["blocks"][0]["tableBlock"] = {
        "headerRows": [],
        "bodyRows": [],
    }
    with pytest.raises(GoogleOcrRescueContractV1Error, match="exactly one"):
        normalize_google_ocr_response_v1(plan=plan, raw_response_bytes=_json_bytes(response))


def test_normalizer_has_no_executor_and_raw_byte_spelling_changes_only_response_receipt(
    unresolved_page: AuthenticatedUnresolvedPageV1,
) -> None:
    plan = _plan(unresolved_page, GoogleOcrRouteV1.CLOUD_VISION_DOCUMENT_TEXT_DETECTION)
    response = _vision_response(normalized=True)
    compact = _json_bytes(response)
    pretty = json.dumps(response, ensure_ascii=False, indent=2).encode()
    compact_result = normalize_google_ocr_response_v1(plan=plan, raw_response_bytes=compact)
    pretty_result = normalize_google_ocr_response_v1(plan=plan, raw_response_bytes=pretty)

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
